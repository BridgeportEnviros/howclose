#!/usr/bin/env python3
"""Inline the logo, address data and school/day-care sites into the page template."""
t = open('template.html').read()
logo = open('logo_datauri.txt').read()
data = open('lookup_data.js').read() + "\nwindow.LOOKUP.sites=" + open('sites.json').read() + ";"
page = t.replace('__LOGO__', logo).replace('/*__DATA__*/', data)
import sys
OUT = sys.argv[1] if len(sys.argv) > 1 else '../index.html'   # writes the published page at the repo root

HEAD = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<meta name="description" content="6,741 people live within 500 feet of the railyard Amtrak wants to build at Canal Street Yard in Bridgeport. How close are you?">'
        '<meta property="og:title" content="How close do you live to the Amtrak railyard?">'
        '<meta property="og:description" content="6,741 people live within 500 feet of the railyard Amtrak wants to build at Canal Street Yard in Bridgeport, 1,101 of them children. Enter your address to see how close you are.">'
        '<meta property="og:type" content="website">'
        '</head><body>\n')
# in the standalone file, the title, font links and styles belong in <head>
i = page.index('<div class="wrap">')
open(OUT, 'w').write(HEAD.replace('</head>', page[:i] + '</head>') + page[i:] + '\n</body></html>\n')
