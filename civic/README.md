# Contact your officials (test)

A standalone test of the "where do your officials stand" panel. It is built as one shared module so How Close and The Railyard Across the Street can load the same file later. Changing a rating or the code here will then update every tool at once.

- Test page: `civic/test/` (live at `https://bridgeportenviros.github.io/howclose/civic/test/` once pushed; marked noindex and "Test version").
- Testing shortcut: add `?lat=41.8306&lng=-87.6466&label=Anything` to skip the address search.

## Files

| File | What it is | Who changes it |
|---|---|---|
| `cta.js` | The panel: district lookup, grouping, cards, email sheet | Code changes |
| `cta.css` | Panel styles (uses the tools' color and font variables) | Code changes |
| `data/ratings.csv` | **Bridgeport Environmentalists' ratings and candidate list.** One row per person per office | BE |
| `data/messages.json` | Group names, explainers, and the call-to-action text for each group (placeholders for now) | BE |
| `data/roster.json` | Who holds each office (generated, don't edit by hand) | `build/build_roster.py` |
| `data/manual_offices.json` | Cook County Board and Amtrak/FRA contacts (not in any open dataset) | By hand |

Chicago aldermen aren't in the roster. The page reads the City of Chicago's Ward Offices dataset live (`data.cityofchicago.org`, `htai-wnw4`).

## Updating a rating (ratings.csv)

Edit `data/ratings.csv` on GitHub (pencil icon) and commit. The change is live in a few minutes.

Columns:
- `person`: name as it appears in the roster (last name and first initial are what's matched).
- `office_key`: `chicago-ward-11`, `chicago-mayor`, `il-house-24`, `il-senate-12`, `us-house-7`, `cook-board-11`.
- `role`: `officeholder` or `candidate`.
- `election`: for candidates, e.g. `Chicago municipal election, Feb. 23, 2027`.
- `category`: one of `opposes`, `boilerplate`, `no_statement`, `supports`. Leave blank if not yet reviewed.
- `reason`: one sentence shown to visitors.
- `source_url`, `source_date`: a news article or the official's own post (BE's evidence rule).
- `reviewed`: the date BE confirmed the rating. Until it's filled in, the card says "Draft rating: BE to confirm".
- `ask`: optional call to action for this one person. It replaces the group's text.
- `email`, `contact_form`, `phone`, `website`: for candidates (officeholders' contacts come from the roster).

If an officeholder changes (for example, after an election), their old rating stops matching the new person's name, so the new person shows as "Not yet reviewed" rather than inheriting it.

Candidates appear under the incumbent's card only when the incumbent isn't rated `opposes`.

Later, `ratings.csv` can be replaced by a Google Sheet. Publish the sheet as CSV, then set `CTA.config.ratingsUrl` to that link. Or have a scheduled GitHub Action copy it into the repo, which keeps a review step and a history.

## Rebuilding the roster

Run this after elections and swearing-in dates. State legislators are seated in January 2027, the U.S. House on Jan. 3, 2027, and the Cook County Board in December.

```
git clone --depth 1 --filter=blob:none --sparse https://github.com/openstates/people.git op && (cd op && git sparse-checkout set data/il)
curl -o legislators-current.yaml https://raw.githubusercontent.com/unitedstates/congress-legislators/main/legislators-current.yaml
python3 civic/build/build_roster.py --openstates op --congress legislators-current.yaml
```

## How districts are found

The page sends only the map point (never the typed address) to:
- U.S. Census TIGERweb Legislative service: U.S. House (119th Congress) and Illinois House and Senate (2024 districts), layers 4–6.
- City of Chicago ward boundaries (`p293-wvbd`), plus the Ward Offices dataset for the alderperson.
- Cook County GIS, Commissioner Districts effective Dec. 5, 2022 (`politicalBoundary` layer 9).

If one lookup fails, the panel says which official is missing and shows the rest.

## Email and the image

- **Email:** opens a draft in the visitor's mail app, Gmail or Outlook, with the address, subject and message filled in.
- **Image (phones):** "Send with the image" copies the address, then opens the phone's share sheet with the image and message. Web pages can't pre-fill recipients there.
- **Image (desktop):** email drafts can't carry attachments, so the visitor saves the image and attaches it.
- **Offices without email** (Congress, Amtrak, FRA leadership): contact-form or phone buttons, plus "Copy message".
