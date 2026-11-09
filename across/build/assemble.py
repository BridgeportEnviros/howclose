"""Rebuild ../index.html from template.html and building.json.

    python assemble.py              # test mode (no Google key)
    python assemble.py YOUR_KEY     # Google 3D city + Google address search
    python assemble.py YOUR_KEY test   # same, written to ../test/index.html with noindex (unlinked test copy)
"""
import pathlib, sys
here = pathlib.Path(__file__).resolve().parent
key = sys.argv[1] if len(sys.argv) > 1 else ""
test = len(sys.argv) > 2 and sys.argv[2] == "test"
t = (here / "template.html").read_text(encoding="utf-8")
b = (here / "building.json").read_text(encoding="utf-8")
base = "https://cdn.jsdelivr.net/npm/cesium@1.121.0/Build/Cesium/"
logo = (here.parent.parent / "build" / "logo_datauri.txt").read_text(encoding="utf-8").strip()
t = t.replace("__LOGO__", logo).replace("__BUILDING__", b).replace("__CESIUM_BASE__", base).replace("__GOOGLE_KEY__", key)
if test:
    t = t.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta name="robots" content="noindex">', 1)
    out = here.parent / "test" / "index.html"; out.parent.mkdir(exist_ok=True)
else:
    out = here.parent / "index.html"
out.write_text(t, encoding="utf-8")
print("wrote", out, "with key" if key else "(test mode, no key)")
