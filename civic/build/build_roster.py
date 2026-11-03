#!/usr/bin/env python3
"""Build civic/data/roster.json: who currently holds each office the contact panel covers.

Sources (all public, all re-pulled on every run):
  - Illinois House and Senate members and the Chicago mayor: Open States people data
    https://github.com/openstates/people (data/il/legislature, data/il/municipalities)
  - U.S. House members from Illinois: @unitedstates congress-legislators
    https://github.com/unitedstates/congress-legislators (legislators-current.yaml)
  - Cook County Board and Amtrak/FRA decision-makers: hand-kept in civic/data/manual_offices.json
  - Chicago aldermen are NOT in this file: the page reads the City of Chicago "Ward Offices"
    dataset (htai-wnw4) live, so the city's own updates show up without a rebuild.

Usage:
  python3 civic/build/build_roster.py --openstates /path/to/openstates/people \
      --congress /path/to/legislators-current.yaml

Fetch the sources first, e.g.:
  git clone --depth 1 --filter=blob:none --sparse https://github.com/openstates/people.git op
  (cd op && git sparse-checkout set data/il)
  curl -o legislators-current.yaml https://raw.githubusercontent.com/unitedstates/congress-legislators/main/legislators-current.yaml
"""
import argparse, datetime, glob, json, os, subprocess
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def first(lst, key=None):
    for x in lst or []:
        if key is None or x.get(key):
            return x
    return None


def git_date(path):
    try:
        return subprocess.check_output(["git", "-C", path, "log", "-1", "--format=%cs"], text=True).strip()
    except Exception:
        return None


def il_legislature(op_root):
    out = []
    for f in sorted(glob.glob(os.path.join(op_root, "data/il/legislature/*.yml"))):
        p = yaml.safe_load(open(f))
        role = next((r for r in p.get("roles", []) if not r.get("end_date")), None) or p["roles"][-1]
        chamber = {"lower": "il-house", "upper": "il-senate"}[role["type"]]
        district_office = first([o for o in p.get("offices", []) if o.get("classification") == "district"], "voice")
        capitol = first([o for o in p.get("offices", []) if o.get("classification") == "capitol"], "voice")
        homepage = next((l["url"] for l in p.get("links", []) if l.get("note") == "homepage"), None) \
            or (p.get("links") or [{}])[0].get("url")
        out.append({
            "office_key": f"{chamber}-{int(role['district'])}",
            "office": ("State Representative" if chamber == "il-house" else "State Senator") + f", District {int(role['district'])}",
            "title": "Rep." if chamber == "il-house" else "Sen.",
            "name": p["name"],
            "party": (p.get("party") or [{}])[0].get("name"),
            "email": p.get("email"),
            "phone": (district_office or capitol or {}).get("voice"),
            "website": homepage,
            "source": "Open States",
        })
    return out


def chicago_mayor(op_root):
    for f in glob.glob(os.path.join(op_root, "data/il/municipalities/*.yml")):
        p = yaml.safe_load(open(f))
        for r in p.get("roles", []):
            if r.get("type") == "mayor" and "place:chicago/" in r.get("jurisdiction", ""):
                off = first(p.get("offices"), "voice") or {}
                form = next((l["url"] for l in p.get("links", []) if "contact" in l["url"].lower()), None)
                return {
                    "office_key": "chicago-mayor", "office": "Mayor of Chicago", "title": "Mayor",
                    "name": p["name"], "party": None, "email": p.get("email"), "phone": off.get("voice"),
                    "contact_form": form, "website": "https://www.chicago.gov/city/en/depts/mayor.html",
                    "term_ends": r.get("end_date"), "source": "Open States",
                }
    raise SystemExit("Chicago mayor not found in Open States data")


def us_house(path):
    out = []
    for p in yaml.safe_load(open(path)):
        t = p["terms"][-1]
        if t["type"] != "rep" or t["state"] != "IL":
            continue
        out.append({
            "office_key": f"us-house-{t['district']}",
            "office": f"U.S. Representative, Illinois District {t['district']}",
            "title": "Rep.",
            "name": p["name"].get("official_full") or f"{p['name']['first']} {p['name']['last']}",
            "party": t.get("party"),
            "email": None,  # Congress takes messages through web forms only
            "contact_form": t.get("contact_form") or (t.get("url", "").rstrip("/") + "/contact" if t.get("url") else None),
            "phone": t.get("phone"),
            "website": t.get("url"),
            "term_ends": t.get("end"),
            "source": "@unitedstates congress-legislators",
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--openstates", required=True)
    ap.add_argument("--congress", required=True)
    a = ap.parse_args()

    manual = json.load(open(os.path.join(DATA, "manual_offices.json")))
    officials = il_legislature(a.openstates) + [chicago_mayor(a.openstates)] + us_house(a.congress)
    for o in manual["cook_county_board"]:
        officials.append({**o, "source": "hand-kept (manual_offices.json)"})

    roster = {
        "built": datetime.date.today().isoformat(),
        "sources": {
            "openstates_people_commit_date": git_date(a.openstates),
            "congress_legislators": "legislators-current.yaml",
            "manual_offices_checked": manual.get("checked"),
        },
        "notes": manual.get("notes", []),
        "officials": sorted(officials, key=lambda o: o["office_key"]),
        "decision_makers": manual["decision_makers"],
    }
    path = os.path.join(DATA, "roster.json")
    json.dump(roster, open(path, "w"), indent=1, ensure_ascii=False)
    counts = {}
    for o in officials:
        k = o["office_key"].rsplit("-", 1)[0]
        counts[k] = counts.get(k, 0) + 1
    print("wrote", path, counts, "+", len(manual["decision_makers"]), "decision-makers")


if __name__ == "__main__":
    main()
