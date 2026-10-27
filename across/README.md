# The Railyard Across the Street

**Live page:** https://bridgeportenviros.github.io/howclose/across/

Enter any Illinois address to see Amtrak's proposed 1,209-foot maintenance building placed directly across the street, its long wall facing the home, in a 3D view. Before any search, the page shows the building at its proposed site in Canal Street Yard on the flat street map. A direct link can carry an address: `https://bridgeportenviros.github.io/howclose/across/?address=3300 S Normal Ave, Chicago`. A link can also carry coordinates instead of an address, so no address is shown: `?at=LAT,LON&street=STREET NAME&label=WHAT TO CALL IT` (the street name picks the right street for the building; the label is shown in place of an address). The "View from a Billionaire's mansion" link under the search box works this way. Views: **From above** (the default; flies in, then circles the building slowly) and **From your home**. Add `&view=home` to a link to start From your home; `&view=above` and `&view=circle` both start From above.

Removed Oct 27, 2026: the three fact cards (wall height, length, distance from the address) and the Google Earth download button (its code is still in the template, unlinked). The fixed "From above" view is commented out in `build/template.html`; to bring it back, uncomment its button and add `"vAir"` to `VIEW_IDS`.

## What's in this folder
- `index.html` — the published page. The 3D viewer (CesiumJS), the map, street data and address search all load from the internet; the building's shape is built in.
- `build/template.html` — page markup, styles and code. Edit this, not `index.html`.
- `build/building.json` — the building's footprint, heights, windows and doors, from Amtrak/WSP schematic drawings (Feb 27, 2026) and the WSP site plan.
- `build/assemble.py` — rebuilds `index.html`: `python assemble.py` (test mode) or `python assemble.py YOUR_KEY`. Rebuilding without the key removes it from the page.

## Modes

The page works in two modes:

- **Test mode (no key):** OpenStreetMap address search and a flat street map. Free, for trying it out; OpenStreetMap's servers aren't meant for a busy public page.
- **Google mode (with a key):** Google address search and Google's photo-real 3D city. This is the version to share.

In Google mode the page opens on a free flat street map (OpenStreetMap) and loads Google's 3D city only when someone places the building (a search or an example link), so visitors who look and leave start no billed 3D session. Searches after that reuse the same session. Fallbacks, so the page keeps working if a daily quota cap is reached or the key has a problem:

- 3D city refused or unreachable: the building is placed on the flat street map, with a note in the results; the next search tries the 3D city again.
- Google address search refused (anything but "address not found"): the page uses OpenStreetMap's address search instead.

A small button at the bottom right of the map (Google mode only) switches between the flat street map and the 3D city. The flat map takes the same path as the quota fallback (same note in the results), so the fallback can be checked while the 3D city still works. Switching to 3D starts a billed session only if none has started on that visit. After a refused 3D city it reads "Try the 3D city again."

## 1. Get a Google Maps Platform key (about 15 minutes)

1. Go to console.cloud.google.com, sign in, and create a project (e.g. "Railyard across the street").
2. Set up billing for the project (a card is required even for the free tier).
3. Under **APIs & Services → Library**, enable these three:
   - **Map Tiles API** (the 3D city)
   - **Maps JavaScript API** (loads the address search)
   - **Geocoding API** (finds the address)
4. Under **APIs & Services → Credentials**, create an **API key**.
5. Restrict the key (important, because the key is visible in the page's code):
   - **Application restrictions → Websites:** add `https://bridgeportenviros.github.io/*`.
   - **API restrictions:** select only the three APIs above.
6. Under **Billing → Budgets & alerts**, set a monthly budget (e.g. $25) with email alerts.

## 2. Put the key in the page

Open `across/index.html` in a text editor (or GitHub's editor), find this line near the top of the script:

    googleApiKey: "",

and paste the key between the quotes. Save.

## 3. Publish

The page is already published from this repo (GitHub Pages, `main` branch). Committing a changed `across/index.html` updates the live page within a minute or two. The key restriction in step 1 should allow `https://bridgeportenviros.github.io/*`.

## Cost (Google Maps Platform price list, read Oct 21, 2026)

| What | Free each month | After that |
|---|---|---|
| 3D city tiles (one per visit; covers up to 3 hours) | 1,000 | $6.00 per 1,000 |
| Address searches | 10,000 | $5.00 per 1,000 |

The 3D tiles are the limit: roughly 1,000 visits a month free; 5,000 visits about $24; 20,000 about $114. Searching several addresses in one visit adds only address-search charges, which stay free at this scale.

## How it places the building

1. Finds the address (Google or OpenStreetMap).
2. Gets nearby street centerlines from the U.S. Census TIGERweb service (free, no key) and picks the one with the address's street name.
3. Measures the street's direction 25 m either side of the address, and which side the home is on.
4. Puts the building's long straight wall (its east wall at the real site) on the opposite side, parallel to the street, centered across from the address, 32 ft from the street's center: half of a 34-ft street plus 15 ft from curb to the inside of the sidewalk (City of Chicago CDOT *Street and Site Plan Design Standards*, 2007: 66-ft right-of-way, 34-ft roadway with parking both sides, 16-ft parkway with the sidewalk 1 ft from the property line).
5. Stands it on a 13 ft 7 in wall (the raised yard at the real site), at the street's ground level.

If the address point is off, the building can land on the wrong side; **Switch sides** fixes that.
