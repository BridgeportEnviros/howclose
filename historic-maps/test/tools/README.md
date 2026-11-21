# Map tiles for the historic maps page

`../tiles/<period>/{z}/{x}/{y}.webp` holds a Web Mercator tile pyramid for each period that used to be a single stretched image (1849–1900, 1929–1963 and the 1970–1995 aerials). Sanborn and Robinson still load from the University of Illinois and Newberry image servers, and the 1938 and 1998–2007 aerials still load live from the state and county servers.

- **Tiles.** 512 × 512 WebP. A tile at zoom z covers the standard XYZ tile (x, y, z) at double resolution, so the page shows it in a 256-px slot and it stays sharp on phones. Edges outside a map are transparent.
- **Zoom range.** Tiles run from zoom 13 up to the zoom closest to the scan's own resolution (`maxzoom` in each `tileset.json`). Past that, the page draws each tile on a canvas from the deepest tiles, so the enlargement is smooth and doesn't show the tile grid.
- **Placement.** Same as before: a least-squares affine from each image's corner control points to Web Mercator, the fit the page already used. `sources.json` lists every source image with its control points, mask, URL and how it was registered.

## Sources

| Periods | Source | Detail at the site |
|---|---|---|
| 1889, 1900 | USGS Chicago 1:62,500, raster inside the GeoPDF (records 309341, 309343) | 2.3 m/px (the GeoTIFFs used before were 5.3 m/px) |
| 1929, 1953, 1963 | USGS Englewood 1:24,000, raster inside the GeoPDF (records 307533, 307535, 307536) | 0.89 m/px (GeoTIFFs: 2.0 m/px) |
| 1970, 1980, 1990, 1995 | CMAP scans of NIPC photos, frame T39N R14E 08, native pixels | 0.41–0.49 m/px pixels. The print screen (period 1.9–2.3 px) is removed with `descreen.py`, leaving about 0.7 m of usable detail. The old crops were 0.6 m/px. |
| 1849, 1870, 1875 | The same cut images as before (Wikimedia, Library of Congress, University of Illinois) | 2.0, 4.4 and 5.1 m/px |
| 1861, 1879 | Amtrak's figure crops, as before. No better scan was reachable. | about 3.2 m/px |

The GeoPDF and CMAP images were registered to the previous image of the same period using SIFT and a RANSAC affine, so they keep its checked placement, including the Nov 19 field-house shifts for 1970 and 1980. RMS was 0.07–0.09 m for the aerials, 0.45–0.55 m for 1929–1963 and 1.3–1.4 m for 1889/1900.

AI upscaling (Real-ESRGAN ×4) was tried on 1861 and 1879 and not used: it turned lot numbers into blobs and rail lines into window-like textures.

## Rebuilding

```
python3 tiler.py manifest.json ../tiles    # manifest: {"periods": [{"id", "quality", "zmax"?, "sources": [{"path","w","h","gcps","mask"}]}]}
python3 descreen.py in.jpg out.jpg         # aerial scans only, before tiling
```

`sources.json` has everything a manifest needs except local file paths. Then set each period's `tiles` entry in `index.html` (`url`, `minZoom`, `maxNativeZoom` = the tileset's `maxzoom`, and `bounds`).
