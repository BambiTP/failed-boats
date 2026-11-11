"""Build ~/failed-boats (the GitHub Pages site) from showboats.json: boats.json, replay copies, viewer copy."""
import sys, json, os, shutil, gzip, base64, csv, re
sys.path.insert(0, '/home/metjr/tagpro-analytics')
import replay_state as rs
OUT = '/home/metjr/failed-boats'
LEAD_MS, MAX_RUN_S = 2000, 10     # viewer opens 2 s before the part of the carry shown (the last 10 s at most)
rows = json.load(open('/home/metjr/tagpro-analytics/failed_boats/showboats.json'))
gid = {r['uuid']: r['game_id'] for r in json.load(open('/home/metjr/tagpro-archive/data/all.replay.json'))}
for r in csv.reader(open('/home/metjr/tagpro-analytics/data/comp_fetch.csv')):
    if len(r) > 3 and r[3] == 'done' and re.fullmatch('[0-9a-f]{24}', r[2]): gid.setdefault(r[1], r[2])
to_b64 = lambda h: base64.b64encode(bytes.fromhex(h)).decode().replace('+', '_')
os.makedirs(OUT + '/replays', exist_ok=True)
if not os.path.isdir(OUT + '/viewer'): shutil.copytree('/home/metjr/naltp-od-caps/viewer', OUT + '/viewer')
boats = []
for r in rows:
    S = rs.parse(r['file'])
    meta = json.loads(gzip.open(r['file'], 'rt').readline())[2]
    pid = int(S['ids'][r['slot']])
    start_ms = int(S['start_ms'])
    view_from = max(r['t_grab'], r['t_pop'] - MAX_RUN_S)
    t_ms = max(0, int(start_ms + view_from * 1000 - LEAD_MS))
    key = r['uuid'].replace('-', '')[:16]
    dst = f'{OUT}/replays/{key}.ndjson.gz'
    if not os.path.exists(dst): shutil.copyfile(r['file'], dst)
    user = next((p.get('userId', '') for p in meta.get('players', []) if p['id'] == pid), '')
    b = dict(player=r['name'], kind=r['kind'], map=r['map'].strip(), key=key, t_ms=t_ms, player_id=pid,
             pop_clock=r['t_pop'], dist_tiles=r['d_end'], played=meta.get('started'))
    if r['uuid'] in gid and re.fullmatch('[0-9a-f]{24}', user or ''):
        b['tagpro_url'] = f"https://tagpro.koalabeast.com/game?replay={to_b64(gid[r['uuid']] + user)}&t={t_ms}"
    if r['kind'] == 'comp':
        info = {}
        try:
            for l in open(os.path.join(os.path.dirname(r['file']), 'info.txt')):
                k, _, v = l.partition(': '); info[k] = v.strip()
        except OSError: pass
        season = info.get('Season', '').lstrip('S'); week = info.get('Week', '').replace('Week ', '')
        b['comp'] = f"Season {season} · Week {week} · {info.get('League', '')} · {info.get('Game', '')}: {info.get('Matchup', '')}"
    boats.append(b)
json.dump(boats, open(OUT + '/boats.json', 'w'), separators=(',', ':'))
print(len(boats), 'boats,', len(os.listdir(OUT + '/replays')), 'replay files,', sum('tagpro_url' in b for b in boats), 'with TagPro links')
