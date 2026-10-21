# How close? — Canal Street Yard address lookup

**Live page:** https://bridgeportenviros.github.io/howclose/

A one-page tool for Bridgeport Environmentalists. Enter an address to see how far it is from the railyard Amtrak has proposed at Canal Street Yard, and share the result as an image for Instagram, Facebook, email or text.

Addresses are matched inside the browser against a built-in address list, so nothing a visitor types is sent anywhere. There are no API keys or outside services.

Companion to the neighborhood dashboard: https://bridgeportenviros.github.io/canal-street-yard/

Also in this repo: **The Railyard Across the Street** (`across/`), which places the proposed maintenance building across the street from any Illinois address in 3D: https://bridgeportenviros.github.io/howclose/across/ — see `across/README.md`.

## What's in the repo
- `index.html` — the published page. Everything (data, logo, map) is built in.
- `share.png` — the 1200×630 link-preview image (the 500 ft numbers and the site map) that Messages, Facebook and others show when someone shares the page link. Remake it by running `window.__makeLinkCard()` in the browser console on the page, if the numbers or address change.
- `build/` — the source used to make `index.html`:
  - `template.html` — page markup, styles and code. Edit this, not `index.html`.
  - `assemble.py` — run `python assemble.py` from `build/` to rebuild `../index.html` from the template and data.
  - `lookup_data.js` — address points within 2 miles, yard outline, people/children-by-distance curves, basemap.
  - `build_lookup.py` — rebuilds `lookup_data.js`: `python build_lookup.py "<path to the dashboard folder>"`, the folder holding the dashboard's `site/data.js` and `data/blocks_2020_area.geojson`. Needs Python with numpy.
  - `addrpoints.tsv` — Cook County Address Points for a box about 2 miles around the yard, retrieved 2026-10-13.
  - `sites.json` — schools and licensed day-care centers within a mile of the yard (copied from the dashboard).
  - `landmarks.json` — outlines of Rate Field, Armour Square Park, and Palmisano and McGuane parks merged into one outline (they are separated only by a street), from the dashboard's OpenStreetMap basemap, drawn as muted reference points.
  - `logo_datauri.txt` — the Bridgeport Environmentalists logo.

The share images end with "Learn more" and the group's project page (`CONFIG.learnMoreUrl`); share messages end with "How close do you live?" and this tool's address (`CONFIG.shareUrl`), which links to Learn more. To change the page address (for example to howclose.bridgeportenviros.org): edit `CONFIG` near the top of the script in `build/template.html` and `SITE_URL` in `build/assemble.py`, run `assemble.py`, and remake `share.png`.

## What the page shows
- **Opening view:** 6,741 people live within 500 feet of the proposed yard; 1,101 are children. Map of the whole site and its 500 ft zone.
- **Within 500 ft:** "I live N feet from the Amtrak railyard" and "1,101 children live as close as me."
- **500 ft to 2 miles:** "I live N feet…" and, out to a mile, "N children live closer than me."
- **Outside 2 miles, or an address it can't place:** the 500 ft numbers and "I wouldn't want it in my neighborhood either."
- **Your location on the map:** a 250 ft circle whose center is shifted up to 125 ft from the address (the same shift every time for a given address), so the map shows the area rather than the house. The dotted line runs from the circle to the nearest part of the yard; the distance figure is still measured from the address itself.
- **Show my location on the map** (on by default): turned off, the map and share images leave out the dotted line and the ME marker and show the whole site instead of the visitor's block.
- **Sharing:** Story (1080×1920) or Post (1080×1350) images. Instagram, Facebook, Email, Text, Save image, plus a copy icon for the message. On phones, every option opens the share sheet with the image: Instagram, Facebook and Save send the image alone (adding text can drop Instagram from the iPhone share sheet); Text and Email send the image plus the message. Tapping the preview image also shares it; the iPhone long-press menu is turned off on it because its "Share" sends a temporary blob: link that only works in that browser tab. On desktops, Instagram saves the image, Facebook opens Facebook's link-share page, and Text/Email open with the message only.

## Method and sources
- **Distance:** straight line from the address point to the nearest edge of the Union Pacific Canal Street Yard outline (OpenStreetMap way 56246278, the same outline the dashboard uses). House numbers missing from the address file are placed between neighboring addresses on the same side of the street.
- **Addresses:** Cook County Address Points, Cook County Open Data dataset 78yw-iddh, retrieved 2026-10-13. About 37,700 address points within 2 miles of the yard.
- **People and children:** the dashboard's resident-weighted method, so the numbers match those already shared with the press. Each census tract's ACS 2020–2024 count (total, and under 18) times the share of the tract's 2020 Census block population within the distance. 500 ft: 6,741 residents, 1,101 children. These are estimates, not counts.
- **Street matching:** exact street names first. Typos are corrected only to a close variant of a street within 2 miles (same first letter; one letter off, or two for names of 8+ letters; same direction and street type when typed). A direction the street doesn't have counts as somewhere else.
- **Schools and day cares:** the dashboard's lists of district, charter, private and parochial schools and City of Chicago–licensed day-care centers within a mile of the yard. After-school-only centers and home day cares are not shown.
