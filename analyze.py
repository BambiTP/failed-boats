"""Classify scanned pops (<=3 tiles from own home flag) into showboat-style failed boats vs hesitation/pressure.
Thresholds (edit here):
  SLOW_FRAC   speed must fall below this fraction of the carrier's peak speed in the carry window
  MIN_SLOW_S  slow stretch must last at least this long right before the pop (a brief hesitation is not a boat)
  SAFE_ENEMY  nearest enemy must stay at least this many tiles away during the slow stretch (else the carrier may
              have just been scared or pressured, not showboating)"""
import json, glob, collections, sys
STOP_SPEED, SAFE_ENEMY, TICK, MAX_TILES, MIN_TILES = 0.8, 3.0, 0.25, 2.0, 1.0   # speed is in tiles/s (a normal run is about 5)
def classify(e):
    """Strict: popped within MAX_TILES of own home flag, completely stopped (speed under STOP_SPEED) for more than
    half a second right up to the pop, with no enemy within SAFE_ENEMY tiles when the stop began."""
    spd, en = e['spd'], e['enemy']
    if len(spd) < 6 or e['own_flag_out'] or not (MIN_TILES < e['d_end'] < MAX_TILES): return 'not_applicable'
    k = 0
    for v in reversed(spd[:-1]):   # last sample is the death tick
        if v < STOP_SPEED: k += 1
        else: break
    if k * TICK < 0.75: return 'no_full_stop'
    if not (MIN_TILES < e['dist'][-1-k] < MAX_TILES): return 'not_applicable'   # stopped 1 to 2 tiles out, not on the flag tile
    return 'showboat' if en[-1-k] >= SAFE_ENEMY else 'stopped_but_enemy_close'
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
# Second check: the carrier's own flag must have been at home for the whole stop (and the second before it). Otherwise
# they were just waiting on their flag tile for it to return and the enemy arrived the moment it did: a mistime, not a boat.
sys.path.insert(0, '/home/metjr/tagpro-analytics')
import replay_state as rs
kept = []
for r in rows:
    S = rs.parse(r['file']); i = r['slot']; team = int(S['team'][i])
    last = int(round(r['t_pop'] / TICK))
    k = 0
    for ti in range(last - 1, 0, -1):
        if (S['vx'][i][ti] ** 2 + S['vy'][i][ti] ** 2) ** .5 < STOP_SPEED: k += 1
        else: break
    first = max(0, last - k - int(1 / TICK))
    out_ticks = [ti for ti in range(first, last + 1)
                 if any(S['team'][j] != team and S['flag'][j][ti] == team and S['alive'][j][ti] for j in range(len(S['team'])))]
    r['flag_out_ticks'] = len(out_ticks)
    if not out_ticks: kept.append(r)
print('after own-flag-home-throughout check:', len(rows), '->', len(kept))
for kd in ('ranked', 'comp'): print(kd, sum(1 for r in kept if r['kind'] == kd))
rows = kept
json.dump(rows, open('showboats.json', 'w'), indent=1)
