#!/usr/bin/env python3
"""Remove the halftone screen from a scanned aerial with a steep frequency-domain low-pass.

usage: descreen.py in.jpg out.jpg
The CMAP scans carry a diagonal print screen (period ~1.9-2.25 px). Left in, it turns into a
checkerboard moire when the image is resampled for map tiles. The cut-off is set to 2/3 of the
measured screen frequency, which keeps everything finer than the screen can actually carry.
Processed in overlapping blocks to keep memory low.
"""
import sys
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
src, dst = sys.argv[1:3]
im = np.asarray(Image.open(src).convert('L')).astype(np.float32)
H, W = im.shape

# measure the screen frequency on a central block
c = im[H // 2 - 512:H // 2 + 512, W // 2 - 512:W // 2 + 512].astype(np.float64)
c -= c.mean()
F = np.abs(np.fft.fft2(c * np.outer(np.hanning(1024), np.hanning(1024))))
fy = np.fft.fftfreq(1024)[:, None]; fx = np.fft.fftfreq(1024)[None, :]
r = np.hypot(fy, fx)
F[r < 0.15] = 0
k = np.argmax(F)
f_screen = float(r.ravel()[k])
peak = float(F.ravel()[k] / np.median(F[F > 0]))
fc = f_screen * 2 / 3
print(f'{src}: screen period {1 / f_screen:.2f} px (peak/median {peak:.0f}), cut-off {fc:.3f} cycles/px')

B, O = 1024, 48
out = np.empty_like(im)
for y0 in range(0, H, B):
    for x0 in range(0, W, B):
        ya, xa = max(0, y0 - O), max(0, x0 - O)
        yb, xb = min(H, y0 + B + O), min(W, x0 + B + O)
        blk = im[ya:yb, xa:xb].astype(np.float64)
        # mirror-pad to limit edge effects
        blk = np.pad(blk, O, mode='reflect')
        h, w = blk.shape
        G = np.fft.rfft2(blk)
        ry = np.fft.fftfreq(h)[:, None]; rx = np.fft.rfftfreq(w)[None, :]
        Hf = np.exp(-(np.hypot(ry, rx) / fc) ** 4)
        res = np.fft.irfft2(G * Hf, s=(h, w))[O:-O, O:-O]
        out[y0:min(H, y0 + B), x0:min(W, x0 + B)] = res[y0 - ya:y0 - ya + min(B, H - y0), x0 - xa:x0 - xa + min(B, W - x0)]
Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8), 'L').save(dst, quality=92)
print('wrote', dst)
