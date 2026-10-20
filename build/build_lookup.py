#!/usr/bin/env python3
"""Build data for the address lookup page.

Inputs
- addrpoints.tsv: Cook County Address Points (datacatalog.cookcountyil.gov 78yw-iddh), pulled 2026-10-13
  for a box ~2 mi around the Canal St Yard; one line per street "DIR|NAME|TYPE<TAB>num,x,y num,x,y ..."
  with x/y in feet on the dashboard's local projection.
- data.js (dashboard bundle): yard polygon (UP Canal Street Yard, OSM way 56246278) and per-tract ACS.
- blocks_2020_area.geojson: 2020 Census blocks with POP100.

Children estimate per block = 2020 block POP100 x tract ACS 2020-2024 share under 18.
Each block's children are spread evenly over the address points inside that block
(block internal point if it has none), then binned by distance to the yard edge.
"""
import json, math, os, sys, numpy as np
# Folder holding the dashboard's site/data.js and data/blocks_2020_area.geojson (the "2026.09 - Railyard Tool" folder).
# Usage: python build_lookup.py "C:/Users/you/Documents/Amtrak Research/2026.09 - Railyard Tool"
U = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DASHBOARD_DIR", "../../2026.09 - Railyard Tool")).rstrip("/\\") + "/"
HERE = os.path.dirname(os.path.abspath(__file__))
s = open(U + "site/data.js").read(); D = json.loads(s[s.index("=") + 1:-1])
P = D["proj"]
def proj(lon, lat): return ((lon - P["lon0"]) * P["ft_per_deg_lon"], (lat - P["lat0"]) * P["ft_per_deg_lat"])
yard = np.array(D["yard"], float)
A = yard; B = np.roll(yard, -1, 0); AB = B - A; ab2 = (AB ** 2).sum(1)

def pip(pts, ring):
    x, y = pts[:, 0], pts[:, 1]; inside = np.zeros(len(pts), bool)
    xs, ys = ring[:, 0], ring[:, 1]; xj, yj = np.roll(xs, 1), np.roll(ys, 1)
    for i in range(len(xs)):
        c = ((ys[i] > y) != (yj[i] > y)) & (x < (xj[i] - xs[i]) * (y - ys[i]) / ((yj[i] - ys[i]) + 1e-18) + xs[i])
        inside ^= c
    return inside

def dist(pts):
    out = np.empty(len(pts))
    for i in range(0, len(pts), 3000):
        p = pts[i:i + 3000]
        AP = p[:, None, :] - A[None]
        t = np.clip((AP * AB[None]).sum(2) / ab2[None], 0, 1)
        C = A[None] + t[..., None] * AB[None]
        out[i:i + 3000] = np.sqrt(((p[:, None] - C) ** 2).sum(2)).min(1)
    out[pip(pts, yard)] = 0
    return out

MAXD = 10560  # 2 miles
# ---------- address points ----------
streets = {}
allpts = []; owners = []
for line in open(os.path.join(HERE, "addrpoints.tsv")).read().split("\n"):
    key, rows = line.split("\t")
    if key == "||": continue
    for r in rows.split(" "):
        if "null" in r or "NaN" in r: continue
        n, x, y = map(int, r.split(","))
        allpts.append((x, y)); owners.append((key, n))
allpts = np.array(allpts, float)
ad = dist(allpts)
keep = ad <= MAXD
print("address points", len(allpts), "within 2 mi", keep.sum())

# ---------- children by block ----------
tr = {t["geoid"]: t for t in D["tracts"]}
def child_share(t):
    a = t.get("acs") if t else None
    if not a: return None
    kids = sum((a[k][0] or 0) for k in ("m_u5","m_5_9","m_10_14","m_15_17","f_u5","f_5_9","f_10_14","f_15_17"))
    tot = a["age_total"][0]
    return kids / tot if tot else None
bl = json.load(open(U + "data/blocks_2020_area.geojson"))
blk_pts = np.zeros(len(allpts), int) - 1
bl_rows = []
missing_share = 0
for bi, f in enumerate(bl["features"]):
    p = f["properties"]; pop = int(p["POP100"] or 0)
    if pop <= 0: continue
    ring = np.array([proj(*c) for c in f["geometry"]["coordinates"][0]])
    cx, cy = proj(float(p["INTPTLON"]), float(p["INTPTLAT"]))
    sh = child_share(tr.get(p["GEOID"][:11]))
    if sh is None: missing_share += 1; continue
    bl_rows.append((bi, ring, (cx, cy), pop * sh, pop))
print("blocks with pop", len(bl_rows), "missing tract share", missing_share)
# assign address points to blocks (bbox prefilter)
for bi, ring, c, kids, pop in bl_rows:
    xmin, ymin = ring.min(0); xmax, ymax = ring.max(0)
    m = (allpts[:, 0] >= xmin) & (allpts[:, 0] <= xmax) & (allpts[:, 1] >= ymin) & (allpts[:, 1] <= ymax)
    idx = np.where(m)[0]
    if len(idx):
        ins = pip(allpts[idx], ring); blk_pts[idx[ins]] = bi
BIN = 25; NB = MAXD // BIN + 1
hist = np.zeros(NB); hist_pop = np.zeros(NB)
by_block = {}
for i, bi in enumerate(blk_pts):
    if bi >= 0: by_block.setdefault(bi, []).append(i)
cover_kids = 0
for bi, ring, c, kids, pop in bl_rows:
    ids = by_block.get(bi)
    if ids:
        d = ad[ids]; w = kids / len(ids); wp = pop / len(ids)
    else:
        d = dist(np.array([c])); w = kids; wp = pop
    for dd in np.atleast_1d(d):
        b = int(dd // BIN)
        if b < NB: hist[b] += w; hist_pop[b] += wp
kids_cdf = np.cumsum(hist)   # kids_cdf[i] = children with distance < (i+1)*BIN
pop_cdf = np.cumsum(hist_pop)
def kids_within(ft): return float(kids_cdf[min(int(ft // BIN), NB - 1)]) if ft >= BIN else float(np.interp(ft, [0, BIN], [0, kids_cdf[0]]))
print("children within 500 ft:", round(kids_within(500)), " 1000:", round(kids_within(1000)), " 1 mi:", round(kids_within(5280)), " 2 mi:", round(kids_within(10559)))
print("residents within 500 ft:", round(pop_cdf[19]), " 1 mi:", round(pop_cdf[5280 // BIN - 1]))
# sanity: block extent covers 2 mi?
allb = np.vstack([r for _, r, _, _, _ in bl_rows]); print("block extent ft", allb.min(0), allb.max(0))

# ---------- output ----------
out_streets = {}
for i in np.where(keep)[0]:
    key, n = owners[i]
    out_streets.setdefault(key, []).append([n, int(allpts[i, 0]), int(allpts[i, 1]), int(round(ad[i]))])
for k in out_streets: out_streets[k].sort()
# compact: per street flat array n,x,y,d,...
S = {k: [v for row in rows for v in row] for k, rows in out_streets.items()}
bundle = dict(
    meta=dict(built="2026-10-13", bin_ft=BIN, max_ft=MAXD,
              sources=dict(addresses="Cook County Address Points (Cook County Open Data, dataset 78yw-iddh), retrieved 2026-10-13",
                           yard="UP Canal Street Yard outline, OpenStreetMap way 56246278 (same outline as the dashboard)",
                           children="2020 Census block population (PL 94-171) x share under 18 in the tract (ACS 5-year 2020-2024)")),
    proj=P, yard=D["yard"],
    kids=[round(float(v), 1) for v in kids_cdf],
    streets=S,
)
open(os.path.join(HERE, "lookup_data.js"), "w").write("window.LOOKUP=" + json.dumps(bundle, separators=(",", ":")) + ";")
print("lookup_data.js KB", os.path.getsize(os.path.join(HERE, "lookup_data.js")) // 1024, "streets", len(S))

# ---------- small basemap for the map and share card ----------
def thin(c, tol=40):
    out = [c[0]]
    for p in c[1:]:
        if abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1]) >= tol: out.append(p)
    if out[-1] != c[-1]: out.append(c[-1])
    return out
bm = D["basemap"]
roads = [{"k": r["k"], "c": [v for p in thin(r["c"], 30 if r["k"] != "minor" else 50) for v in p]} for r in bm["roads"]]
rails = [[v for p in thin(r["c"], 60) for v in p] for r in bm["rails"] if r["k"] == "rail" and not r.get("s")]
water = [{"p": 1 if w["poly"] else 0, "c": [v for p in thin(w["c"], 150 if w["poly"] else 60) for v in p]} for w in bm["water"] if len(w["c"]) < 5000]
bundle["base"] = dict(roads=roads, rails=rails, water=water)
bundle["kids"] = bundle["kids"][:5280 // BIN + 40]   # 1 mile + margin; beyond that tract coverage is incomplete
open(os.path.join(HERE, "lookup_data.js"), "w").write("window.LOOKUP=" + json.dumps(bundle, separators=(",", ":")) + ";")
print("with basemap KB", os.path.getsize(os.path.join(HERE, "lookup_data.js")) // 1024, {k: len(json.dumps(v)) // 1024 for k, v in bundle["base"].items()})

# ---------- match the dashboard exactly (Oct 14, 2026) ----------
# Dashboard "resident-weighted" method: each tract's ACS count x (2020 block population within d / tract 2020 population),
# using the dashboard's own per-tract 25-ft pop_cdf. These are the figures already shared with the press
# (500 ft: 6,741 residents, 1,101 children under 18).
U18 = ("m_u5","m_5_9","m_10_14","m_15_17","f_u5","f_5_9","f_10_14","f_15_17")
nb = min(len(t["pop_cdf"]) for t in D["tracts"])
kids_d = [0.0] * nb; pop_d = [0.0] * nb
for t in D["tracts"]:
    if not t.get("pop2020") or not t.get("acs"): continue
    a = t["acs"]; kids = sum((a[k][0] or 0) for k in U18); pop = a["pop"][0] or 0
    for i in range(nb):
        sh = t["pop_cdf"][i] / t["pop2020"]
        kids_d[i] += sh * kids; pop_d[i] += sh * pop
bundle["kids"] = [round(v, 2) for v in kids_d]
bundle["pop"] = [round(v, 2) for v in pop_d]
bundle["meta"]["sources"]["children"] = "Same method as the neighborhood dashboard: ACS 2020-2024 tract counts (under 18 / total) x share of the tract's 2020 block population within each distance"
open(os.path.join(HERE, "lookup_data.js"), "w").write("window.LOOKUP=" + json.dumps(bundle, separators=(",", ":")) + ";")
print("dashboard method: 500 ft pop", round(pop_d[19]), "kids", round(kids_d[19]), "| 1000 ft kids", round(kids_d[39]), "| 2500 ft kids", round(kids_d[99]), "| bins", nb)
