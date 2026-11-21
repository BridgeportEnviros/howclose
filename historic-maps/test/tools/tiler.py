#!/usr/bin/env python3
"""Cut georeferenced scans into a Web Mercator XYZ tile pyramid (512-px "@2x" WebP tiles).

Each period is a list of source images in draw order (later on top). Every source has
the same geometry the web page uses: w, h, gcps = [[u, v, lon, lat], ...] with (0,0) at the
image's top-left corner, and a mask polygon in pixel coords. The pixel -> Web Mercator
affine is the same least-squares fit the page does, so tiles land where the page used to
draw the image.

Tiles: at zoom z a tile covers the standard XYZ tile (x, y, z) but is 512 px, i.e. the
resolution of 256-px tiles at z+1. Leaflet shows them with tileSize 256, so phones get
sharp tiles and desktops downsample. The pyramid stops at the zoom nearest the scan's
own resolution (never more than ~1.5x upsampled); Leaflet enlarges past that.

usage: tiler.py manifest.json out_dir [--quality 80] [--only id,id]
manifest: {"periods": [{"id": "1929", "quality": 80, "zmax": null,
                        "sources": [{"path": ..., "w":..., "h":..., "gcps": [...], "mask": [...]}]}]}
"""
import json, math, os, sys, argparse
import numpy as np
import cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
R = 6378137.0
HALF = math.pi * R
TILE = 512
ZMIN = 13


def merc(lon, lat):
    return R * lon * math.pi / 180, R * math.log(math.tan(math.pi / 4 + lat * math.pi / 360))


def unmerc(x, y):
    return x / R * 180 / math.pi, (2 * math.atan(math.exp(y / R)) - math.pi / 2) * 180 / math.pi


def fit_affine(gcps):
    """pixel (u,v) corner convention -> mercator (X,Y); same least squares as the page."""
    A = np.array([[g[0], g[1], 1.0] for g in gcps])
    XY = np.array([merc(g[2], g[3]) for g in gcps])
    sol, *_ = np.linalg.lstsq(A, XY, rcond=None)  # 3x2
    a, b, c = sol[:, 0]
    d, e, f = sol[:, 1]
    return np.array([[a, b, c], [d, e, f]])


def tile_span(z):
    return 2 * HALF / (2 ** z)


def native_zoom(res_merc):
    f = math.log2(2 * HALF / (TILE * res_merc))
    return int(math.floor(f + 0.6))


def load_rgb(path):
    im = Image.open(path)
    if im.mode not in ('RGB', 'L'):
        im = im.convert('RGB')
    a = np.asarray(im)
    if a.ndim == 2:
        a = np.repeat(a[:, :, None], 3, axis=2)
    return np.ascontiguousarray(a)


def render_level(srcs, zmax):
    """Warp all sources into one RGBA float32 premultiplied raster on the zmax tile grid."""
    T = tile_span(zmax)
    res = T / TILE
    # footprint bounds (mercator) from masks
    xs, ys = [], []
    for s in srcs:
        A = s['A']
        for u, v in s['mask']:
            X = A[0, 0] * u + A[0, 1] * v + A[0, 2]
            Y = A[1, 0] * u + A[1, 1] * v + A[1, 2]
            xs.append(X); ys.append(Y)
    minX, maxX, minY, maxY = min(xs), max(xs), min(ys), max(ys)
    tx0 = int(math.floor((minX + HALF) / T)); tx1 = int(math.floor((maxX + HALF) / T - 1e-9))
    ty0 = int(math.floor((HALF - maxY) / T)); ty1 = int(math.floor((HALF - minY) / T - 1e-9))
    W, H = (tx1 - tx0 + 1) * TILE, (ty1 - ty0 + 1) * TILE
    X0, Y0 = -HALF + tx0 * T, HALF - ty0 * T  # top-left corner of the raster
    print(f'  z{zmax}: tiles x {tx0}..{tx1}, y {ty0}..{ty1} -> {W}x{H} px, {res:.3f} merc m/px', flush=True)
    rgb = np.zeros((H, W, 3), np.float32)
    alpha = np.zeros((H, W), np.float32)
    for s in srcs:
        A = s['A']
        # dest corner coords (dx,dy) -> merc: X = X0 + res*dx, Y = Y0 - res*dy
        # merc -> src corner coords: inverse of A
        M = np.vstack([A, [0, 0, 1]])
        Minv = np.linalg.inv(M)
        D = np.array([[res, 0, X0], [0, -res, Y0], [0, 0, 1]])
        S = Minv @ D  # dest corner -> src corner
        # convert to pixel-center convention for OpenCV: src_c = S*(dst_c) ; src_center = src_c - .5, dst_c = dst_center + .5
        Sc = S.copy()
        Sc[:2, 2] = S[:2, :2] @ np.array([0.5, 0.5]) + S[:2, 2] - 0.5
        src = load_rgb(s['path'])
        h, w = src.shape[:2]
        if (w, h) != (s['w'], s['h']):
            raise SystemExit(f"{s['path']}: size {w}x{h} != manifest {s['w']}x{s['h']}")
        # scale between dest and source pixels (source px per dest px)
        scale = math.sqrt(abs(np.linalg.det(S[:2, :2])))
        if scale > 1.6:  # source much finer than the grid: pre-shrink to avoid aliasing
            k = scale / 1.2
            nw, nh = int(round(w / k)), int(round(h / k))
            src = cv2.resize(src, (nw, nh), interpolation=cv2.INTER_AREA)
            P = np.array([[w / nw, 0, 0], [0, h / nh, 0], [0, 0, 1]])  # small corner -> big corner
            S2 = np.linalg.inv(P) @ S
            Sc = S2.copy(); Sc[:2, 2] = S2[:2, :2] @ np.array([0.5, 0.5]) + S2[:2, 2] - 0.5
            print(f'    pre-shrunk {s["path"].split("/")[-1]} by {k:.2f}', flush=True)
        warped = cv2.warpAffine(src, Sc[:2], (W, H), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP,
                                borderMode=cv2.BORDER_REPLICATE)
        del src
        # mask polygon -> dest pixel coords, anti-aliased fill (8 fractional bits)
        Dinv = np.linalg.inv(D)
        pts = []
        for u, v in s['mask']:
            X = A[0, 0] * u + A[0, 1] * v + A[0, 2]
            Y = A[1, 0] * u + A[1, 1] * v + A[1, 2]
            dx, dy, _ = Dinv @ np.array([X, Y, 1.0])
            pts.append([dx - 0.5, dy - 0.5])  # corner -> center coords for cv2
        m = np.zeros((H, W), np.uint8)
        cv2.fillPoly(m, [np.round(np.array(pts) * 256).astype(np.int32)], 255, lineType=cv2.LINE_AA, shift=8)
        a = m.astype(np.float32) / 255.0
        del m
        wf = np.clip(warped.astype(np.float32), 0, 255)
        del warped
        # "over" compositing, premultiplied
        inv = 1.0 - a
        rgb *= inv[:, :, None]
        rgb += wf * a[:, :, None]
        alpha *= inv
        alpha += a
        del wf, a, inv
    return {'rgb': rgb, 'alpha': alpha, 'tx0': tx0, 'ty0': ty0, 'tx1': tx1, 'ty1': ty1, 'z': zmax,
            'bounds_merc': (minX, minY, maxX, maxY)}


def write_tiles(level, out_dir, quality, stats):
    rgb, alpha, z = level['rgb'], level['alpha'], level['z']
    for j, ty in enumerate(range(level['ty0'], level['ty1'] + 1)):
        for i, tx in enumerate(range(level['tx0'], level['tx1'] + 1)):
            a = alpha[j * TILE:(j + 1) * TILE, i * TILE:(i + 1) * TILE]
            p = rgb[j * TILE:(j + 1) * TILE, i * TILE:(i + 1) * TILE]
            d = os.path.join(out_dir, str(z), str(tx)); os.makedirs(d, exist_ok=True)
            fn = os.path.join(d, f'{ty}.webp')
            amax = float(a.max())
            if amax <= 1 / 255:
                Image.new('RGBA', (TILE, TILE), (0, 0, 0, 0)).save(fn, 'WEBP', lossless=True)
                stats['empty'] += 1
            else:
                with np.errstate(divide='ignore', invalid='ignore'):
                    c = np.where(a[:, :, None] > 1e-6, p / np.maximum(a[:, :, None], 1e-6), 0)
                c8 = np.clip(np.round(c), 0, 255).astype(np.uint8)
                a8 = np.clip(np.round(a * 255), 0, 255).astype(np.uint8)
                if a8.min() == 255:
                    Image.fromarray(c8, 'RGB').save(fn, 'WEBP', quality=quality, method=5)
                else:
                    im = Image.fromarray(np.dstack([c8, a8]), 'RGBA')
                    im.save(fn, 'WEBP', quality=quality, alpha_quality=100, method=5)
            stats['n'] += 1
            stats['bytes'] += os.path.getsize(fn)


def downsample(level):
    """2x box downsample of a premultiplied level onto the z-1 grid."""
    rgb, alpha = level['rgb'], level['alpha']
    tx0, ty0, tx1, ty1 = level['tx0'], level['ty0'], level['tx1'], level['ty1']
    padL = TILE if tx0 % 2 else 0
    padT = TILE if ty0 % 2 else 0
    padR = TILE if tx1 % 2 == 0 else 0
    padB = TILE if ty1 % 2 == 0 else 0
    if padL or padT or padR or padB:
        rgb = np.pad(rgb, ((padT, padB), (padL, padR), (0, 0)))
        alpha = np.pad(alpha, ((padT, padB), (padL, padR)))
    H, W = alpha.shape
    nrgb = np.empty((H // 2, W // 2, 3), np.float32)
    nal = np.empty((H // 2, W // 2), np.float32)
    step = 2048
    for r0 in range(0, H, step):
        blk = rgb[r0:r0 + step]
        nrgb[r0 // 2:(r0 + blk.shape[0]) // 2] = cv2.resize(blk, (W // 2, blk.shape[0] // 2), interpolation=cv2.INTER_AREA)
        ab = alpha[r0:r0 + step]
        nal[r0 // 2:(r0 + ab.shape[0]) // 2] = cv2.resize(ab, (W // 2, ab.shape[0] // 2), interpolation=cv2.INTER_AREA)
    return {'rgb': nrgb, 'alpha': nal, 'tx0': tx0 // 2, 'ty0': ty0 // 2, 'tx1': tx1 // 2, 'ty1': ty1 // 2,
            'z': level['z'] - 1, 'bounds_merc': level['bounds_merc']}


def build(period, out_root, default_q):
    pid = period['id']
    srcs = []
    for s in period['sources']:
        s = dict(s)
        s['A'] = fit_affine(s['gcps'])
        s['res'] = math.sqrt(abs(s['A'][0, 0] * s['A'][1, 1] - s['A'][0, 1] * s['A'][1, 0]))
        srcs.append(s)
    res = min(s['res'] for s in srcs)
    zmax = period.get('zmax') or native_zoom(res)
    lat_c = unmerc(0, sum(merc(0, g[3])[1] for g in srcs[0]['gcps']) / len(srcs[0]['gcps']))[1]
    k = math.cos(math.radians(lat_c))
    print(f'{pid}: source {res * k:.3f} m/px on the ground -> max zoom {zmax} ({tile_span(zmax) / TILE * k:.3f} m/px)', flush=True)
    out_dir = os.path.join(out_root, pid)
    q = period.get('quality') or default_q
    stats = {'n': 0, 'bytes': 0, 'empty': 0}
    level = render_level(srcs, zmax)
    bm = level['bounds_merc']
    while True:
        write_tiles(level, out_dir, q, stats)
        if level['z'] <= ZMIN:
            break
        level = downsample(level)
    w, s_ = unmerc(bm[0], bm[1]); e, n = unmerc(bm[2], bm[3])
    meta = {'id': pid, 'minzoom': ZMIN, 'maxzoom': zmax, 'tile': TILE,
            'bounds': [[round(s_, 6), round(w, 6)], [round(n, 6), round(e, 6)]],
            'src_m_per_px': round(res * k, 3), 'tile_m_per_px': round(tile_span(zmax) / TILE * k, 3),
            'tiles': stats['n'], 'empty': stats['empty'], 'bytes': stats['bytes']}
    with open(os.path.join(out_dir, 'tileset.json'), 'w') as fh:
        json.dump(meta, fh)
    print(f'  -> {stats["n"]} tiles ({stats["empty"]} empty), {stats["bytes"] / 1e6:.2f} MB', flush=True)
    return meta


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('manifest'); ap.add_argument('out')
    ap.add_argument('--quality', type=int, default=80)
    ap.add_argument('--only', default='')
    a = ap.parse_args()
    man = json.load(open(a.manifest))
    only = set(x for x in a.only.split(',') if x)
    metas = []
    for p in man['periods']:
        if only and p['id'] not in only:
            continue
        metas.append(build(p, a.out, a.quality))
    print(json.dumps(metas, indent=1))
