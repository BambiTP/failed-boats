"""Classify scanned pops (<=3 tiles from own home flag) into showboat-style failed boats vs hesitation/pressure.
Thresholds (edit here):
  SLOW_FRAC   speed must fall below this fraction of the carrier's peak speed in the carry window
  MIN_SLOW_S  slow stretch must last at least this long right before the pop (a brief hesitation is not a boat)
  SAFE_ENEMY  nearest enemy must stay at least this many tiles away during the slow stretch (else the carrier may
              have just been scared or pressured, not showboating)"""
import json, glob, collections, sys
SLOW_FRAC, MIN_SLOW_S, SAFE_ENEMY, TICK = 0.5, 0.75, 4.0, 0.25
def classify(e):
    spd, en = e['spd'], e['enemy']
    if len(spd) < 6 or e['own_flag_out']: return 'not_applicable'
    peak = max(spd[:-1]) or 1
    k = 0
    for v in reversed(spd[:-1]):   # last sample is the death tick
        if v < SLOW_FRAC * peak: k += 1
        else: break
    if k * TICK < MIN_SLOW_S: return 'no_slowdown'
    ens = en[-1-k:-1]
    return 'showboat' if min(ens) >= SAFE_ENEMY else 'slowed_but_enemy_close'
res = collections.defaultdict(collections.Counter); games = collections.Counter(); rows = []
for f in glob.glob('out_*.jsonl'):
    for l in open(f):
        g = json.loads(l)
        if 'skip' in g: continue
        kind = g['set']
        games[kind] += 1; res[kind]['carries'] += g['ncarry']; res[kind]['caps'] += g['ncap']
        for e in g['eps']:
            c = classify(e); res[kind][c] += 1
            if c == 'showboat': rows.append(dict(kind=kind, uuid=g['uuid'], file=g['file'], map=g['map'], **{x: e[x] for x in ('slot', 'name', 'team', 't_grab', 't_pop', 'd_end')}))
for k in res: print(k, 'games', games[k], dict(res[k]))
json.dump(rows, open('showboats.json', 'w'), indent=1)
