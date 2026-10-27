#!/usr/bin/env python3
"""Inline the logo, address data and school/day-care sites into the page template."""
t = open('template.html').read()
logo = open('logo_datauri.txt').read()
data = (open('lookup_data.js').read() + "\nwindow.LOOKUP.sites=" + open('sites.json').read() + ";"
        + "\nwindow.LOOKUP.landmarks=" + open('landmarks.json').read() + ";")   # Rate Field and the two parks, from the dashboard's OSM basemap
page = t.replace('__LOGO__', logo).replace('/*__DATA__*/', data)
import sys
OUT = sys.argv[1] if len(sys.argv) > 1 else '../index.html'   # writes the published page at the repo root

SITE_URL = 'https://bridgeportenviros.github.io/howclose/'   # change to https://howclose.bridgeportenviros.org/ once the subdomain is set up
import re
LEAD = re.search(r'lead:\s*"(\w+)"', t).group(1)   # CONFIG.lead in template.html: which number the link preview leads with
if LEAD == "children":
    DESC = "1,101 children live within 500 feet of the railyard Amtrak wants to build at Canal Street Yard in Bridgeport. How close are you?"
    OG_DESC = "1,101 children live within 500 feet of the railyard Amtrak wants to build at Canal Street Yard in Bridgeport. None live by its current site at 14th Street. Enter your address to see how close you are."
    OG_ALT = "1,101 children live within 500 feet of the proposed 24/7 Amtrak facility; none live by its current site. Map of Canal Street Yard in Bridgeport."
else:
    DESC = "6,741 people live within 500 feet of the railyard Amtrak wants to build at Canal Street Yard in Bridgeport. How close are you?"
    OG_DESC = "6,741 people live within 500 feet of the railyard Amtrak wants to build at Canal Street Yard in Bridgeport, 1,101 of them children. Enter your address to see how close you are."
    OG_ALT = "6,741 people live within 500 feet of the proposed 24/7 Amtrak facility; 1,101 are children. Map of Canal Street Yard in Bridgeport."
HEAD = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        f'<meta name="description" content="{DESC}">'
        '<meta property="og:title" content="How close do you live to the 24/7 Amtrak facility?">'
        f'<meta property="og:description" content="{OG_DESC}">'
        '<meta property="og:type" content="website">'
        f'<meta property="og:url" content="{SITE_URL}">'
        f'<meta property="og:image" content="{SITE_URL}share.png">'
        '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
        f'<meta property="og:image:alt" content="{OG_ALT}">'
        '<meta name="twitter:card" content="summary_large_image">'
        '</head><body>\n')
# in the standalone file, the title, font links and styles belong in <head>
i = page.index('<div class="wrap">')
open(OUT, 'w').write(HEAD.replace('</head>', page[:i] + '</head>') + page[i:] + '\n</body></html>\n')
