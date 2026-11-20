#!/usr/bin/env python3
"""Build tracts.json for the comment helper: census tract outlines near the yard, each with adult asthma
(CDC PLACES) and, for the 28 tracts in the EA's own study area, the CEJST 2.0 flags.

Usage: python build_tracts.py "<path to the dashboard's data.js>"
  (the canal-street-yard repo's data.js; same projection as lookup_data.js)
Reads cejst_ea_tracts.csv in this folder: the EA's Table 3-2 tracts (2020) with CEJST 2.0 'disadvantaged'
and diesel particulate percentile, taken from the 2010 tract holding most of each 2020 tract's land.
"""
import csv, json, sys

src = open(sys.argv[1]).read()
D = json.loads(src[src.index('{'):src.rindex('}') + 1])
assert D['proj']['lat0'] == 41.8375 and D['proj']['lon0'] == -87.6375, 'projection differs from lookup_data.js'
cej = {r['ea_tract']: r for r in csv.DictReader(open('cejst_ea_tracts.csv'))}

def simplify(pts, tol):
    if len(pts) < 4: return pts
    def rdp(a, b):
        (x1, y1), (x2, y2) = pts[a], pts[b]
        dx, dy = x2 - x1, y2 - y1; L = (dx * dx + dy * dy) ** .5 or 1
        best, idx = 0, None
        for i in range(a + 1, b):
            x, y = pts[i]; d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / L
            if d > best: best, idx = d, i
        if best > tol: return rdp(a, idx)[:-1] + rdp(idx, b)
        return [pts[a], pts[b]]
    return rdp(0, len(pts) - 1)

out = []
for t in D['tracts']:
    if t['dist'] > 12000 or not t['polys']: continue                    # the lookup only places addresses within 2 miles
    name = t['name'].replace('Census Tract ', '')
    rings = []
    for poly in (t['polys'] or []):
        pts = [tuple(p) for p in poly[0]]
        if len(pts) > 1 and pts[0] == pts[-1]: pts = pts[:-1]          # closed ring: split at the farthest vertex
        far = max(range(len(pts)), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
        ring = simplify(pts[:far + 1], 15)[:-1] + simplify(pts[far:] + [pts[0]], 15)[:-1]
        rings.append([v for p in ring for v in p])
    row = {'n': name, 'r': rings}
    a = (t.get('places') or {}).get('CASTHMA')
    if a: row['a'] = a[0]
    if name in cej:
        row['ea'] = 1
        row['dis'] = 1 if cej[name]['disadvantaged'] == 'True' else 0
        row['dpm'] = int(cej[name]['diesel_pm_pctile'])
    out.append(row)

b = D['meta']['bin_ft']
def within(ft, key):
    tot = 0
    for t in D['tracts']:
        cdf = t[key]; w = cdf[max(0, min(round(ft / b) - 1, len(cdf) - 1))] / t['pop2020'] if t['pop2020'] else 0
        tot += w * (t['acs']['pop'][0] or 0)
    return round(tot)

meta = {'city_asthma': D['chicago']['places']['CASTHMA'][0],
        'pop500_existing': within(500, 'pop_cdf_b'),
        'ea_tracts': len(cej), 'ea_disadvantaged': sum(r['disadvantaged'] == 'True' for r in cej.values()),
        'source': 'Dashboard data.js built ' + D['meta']['built'] + '; CDC PLACES crude adult asthma; CEJST 2.0 via cejst_ea_tracts.csv'}
missing = set(cej) - {r['n'] for r in out}
assert not missing, f'EA tracts missing from the dashboard data: {missing}'
json.dump({'meta': meta, 'tracts': out}, open('tracts.json', 'w'), separators=(',', ':'))
print(len(out), 'tracts;', meta)
