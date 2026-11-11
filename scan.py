"""Scan ranked replays for 'failed boats': a flag carrier close to their own (home) flag who slows down and is then popped.
Usage: scan.py WORKER NWORKERS  -> writes failed_boats/out_WORKER.jsonl (one line per CTF game, with every carrier episode that
ended in a pop within 2 tiles of the carrier's own flag while it was home)."""
import sys, json, glob, os, gzip
sys.path.insert(0, '/home/metjr/tagpro-analytics')
import numpy as np
import replay_state as rs

w, n, SET = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]   # SET: ranked | comp
PAT = {'ranked': '/home/metjr/nte/data/replays/*/*/*.ndjson.gz', 'comp': '/home/metjr/naltp/eu_archive/**/*.ndjson.gz'}[SET]
files = sorted(glob.glob(PAT, recursive=True))[w::n]
out = open(f'/home/metjr/tagpro-analytics/failed_boats/out_{SET}_{w}.jsonl', 'w')
TICK = rs.TICK
for k, f in enumerate(files):
    try:
        with gzip.open(f, 'rt') as fh:
            m = json.loads(fh.readline())[2]
        if m.get('mapType') != 'ctf':
            out.write(json.dumps(dict(file=f, skip='notctf', ranked=m.get('ranked'), private=m.get('private'), mode=m.get('gameMode'))) + '\n'); continue
        S = rs.parse(f)
        if S is None:
            out.write(json.dumps(dict(file=f, skip='parse')) + '\n'); continue
        T = len(S['t']); P = len(S['team']); homes = S['homes']
        ep = []; ncarry = 0; ncap = 0
        for i in range(P):
            team = int(S['team'][i]); h = homes.get(team)
            if h is None: continue
            fl = S['flag'][i]; al = S['alive'][i] & S['present'][i]
            carrying = (fl > 0) & al
            t = 0
            while t < T:
                if not carrying[t]: t += 1; continue
                a = t
                while t < T and carrying[t]: t += 1
                b = t  # first tick not carrying
                ncarry += 1
                # score change right after => capture
                sr0, sb0 = S['score_red'][b-1], S['score_blue'][b-1]
                e = min(T-1, b + 6)
                cap = (S['score_red'][e] != sr0) or (S['score_blue'][e] != sb0)
                if cap: ncap += 1; continue
                if b >= T - 1: continue  # game ended while carrying
                last = b - 1
                # popped? carrier dead at b (or left)
                if not S['alive'][i, min(b, T-1)]: pass
                else: continue  # dropped flag without dying (not a pop)
                x = S['x'][i]; y = S['y'][i]
                if np.isnan(x[last]): continue
                d = float(np.hypot(x[last]-h[0], y[last]-h[1]))
                if d > 3: continue  # scan keeps 3; analyze.py narrows to 2
                # own flag at home at that moment? (no enemy carrying our flag)
                out_flag = False
                for j in range(P):
                    if S['team'][j] != team and S['flag'][j][last] == team and S['alive'][j][last]: out_flag = True
                spd = np.hypot(S['vx'][i], S['vy'][i])
                # distances to own flag over carry
                dist = np.hypot(x-h[0], y-h[1])
                # enemy distances
                en = [j for j in range(P) if S['team'][j] != team]
                def nearest(tt):
                    best = 99.0
                    for j in en:
                        if S['alive'][j][tt] and not np.isnan(S['x'][j][tt]):
                            best = min(best, float(np.hypot(S['x'][j][tt]-x[tt], S['y'][j][tt]-y[tt])))
                    return best
                # carry-end window: last 4 s
                lo = max(a, last - int(4/TICK))
                seg = [round(float(v), 2) for v in spd[lo:last+1]]
                dseg = [round(float(v), 2) for v in dist[lo:last+1]]
                eseg = [round(nearest(tt), 2) for tt in range(lo, last+1)]
                ep.append(dict(slot=i, name=str(S['names'][i]), team=team, t_grab=float(S['t'][a]), t_pop=float(S['t'][last]),
                               d_end=round(d, 2), own_flag_out=out_flag, spd=seg, dist=dseg, enemy=eseg,
                               tp=bool(S['tagpro'][i][last]), bomb=bool(S['bomb'][i][last])))
        out.write(json.dumps(dict(set=SET, file=f, uuid=m.get('uuid'), map=m.get('mapName'), started=m.get('started'), ranked=m.get('ranked'),
                                  private=m.get('private'), mode=m.get('gameMode'), ncarry=ncarry, ncap=ncap, eps=ep)) + '\n')
    except Exception as ex:
        out.write(json.dumps(dict(file=f, skip='error', err=str(ex)[:200])) + '\n')
    if k % 200 == 0: out.flush()
out.close()
