"""make_fx_textures.py -- seeded, deterministic generator for the P15 storm / fire FX textures (Python + PIL + numpy, no network).

    python -I Tools/textures/fx/make_fx_textures.py [--out SourceArt/FX] [--sheet Docs/ArtTest/fx/p15_textures_sheet.png] [--only name ...] [--no-sheet]

Writes (PNG, 8 bit; spec: Docs/plans/P15_PARTICLES.md section 4) to SourceArt/FX/:
  T_LB_FX_RainStreak.png  64 x 512    RGBA  RGB white, A = soft vertical streak (Gaussian across, tapered at both ends, brighter toward the bottom).  Import: TC_Default, sRGB off, keep alpha.
  T_LB_FX_Splash.png      1024 x 1024 RGBA  4 x 4 SubUV, frame = row * 4 + col (row 0 = top), frame 0 small -> frame 15 faded.  RGB cool white (straight alpha), A = shape.  sRGB on, keep alpha.
  T_LB_FX_Ripple.png      256 x 256   RGBA  thin ring (radius 0.42, sigma 0.015) + faint inner ring; RGB = ring luminance lit from the upper left, A = ring mask.  sRGB off, keep alpha.
  T_LB_FX_Bolts.png       2048 x 1024 RGBA  4 x 2 cells of 512 px, cell k = col k % 4, row k // 4 (AtlasIndex = k, row 0 = top), seed 101 + k.
                                            RGB = glow colour x intensity (premultiplied, for the additive material), A = intensity.  sRGB on, keep alpha.
  T_LB_FX_Noise.png       512 x 512   RGB   tileable: R = fbm Perlin (4 octaves), G = the same field rolled by (173, 311), B = Voronoi F1.  TC_Masks, sRGB off.
  T_LB_FX_SoftDot.png     64 x 64     L     Gaussian dot (zero at the border).  TC_Alpha.
  T_LB_FX_MistPuff.png    256 x 256   L     soft fbm blob with a radial falloff (zero at the border).  TC_Alpha.

Every random number comes from numpy default_rng(seed) with the seeds in SEEDS below, so two runs give identical bytes.  The contact sheet
(Docs/ArtTest/fx/p15_textures_sheet.png) shows each texture on mid-grey and black, with the alpha, and the atlas grids outlined.
The script also self-checks: tileable textures (opposite edges), atlas cell margins (>= 2 px of zero alpha, we keep 3 px) and determinism-relevant ranges.
"""
import argparse
import hashlib
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))

SEEDS = {
    "splash": 15201,
    "noise_r": 15301,
    "noise_vor": 15303,
    "mist": 15401,
    "bolts_first": 101,  # cell k uses 101 + k  (101..108)
}
CELL_MARGIN = 3  # px of exactly zero alpha at every atlas cell border (spec: at least 2)

NAMES = ["rain", "splash", "ripple", "bolts", "noise", "dot", "mist"]
FILES = {
    "rain": "T_LB_FX_RainStreak.png",
    "splash": "T_LB_FX_Splash.png",
    "ripple": "T_LB_FX_Ripple.png",
    "bolts": "T_LB_FX_Bolts.png",
    "noise": "T_LB_FX_Noise.png",
    "dot": "T_LB_FX_SoftDot.png",
    "mist": "T_LB_FX_MistPuff.png",
}


# ----------------------------------------------------------------------------- helpers
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def to_u8(a):
    return np.clip(np.rint(np.asarray(a, dtype=np.float64) * 255.0), 0, 255).astype(np.uint8)


def edge_window(h, w, zero_px, ramp_px):
    """1 in the interior, exactly 0 within zero_px of the border, smooth ramp over ramp_px."""
    y = np.arange(h)
    x = np.arange(w)
    dy = np.minimum(y, h - 1 - y)[:, None]
    dx = np.minimum(x, w - 1 - x)[None, :]
    d = np.minimum(dy, dx).astype(np.float64)
    return smoothstep(zero_px - 0.5, zero_px + ramp_px, d)


def perlin_periodic(h, w, cells_y, cells_x, rng):
    """Gradient noise that tiles exactly with period (cells_y, cells_x) lattice cells over the image.  Range roughly [-0.7, 0.7]."""
    ang = rng.uniform(0.0, 2.0 * math.pi, size=(cells_y, cells_x))
    gx, gy = np.cos(ang), np.sin(ang)
    ys = np.arange(h) * (cells_y / h)
    xs = np.arange(w) * (cells_x / w)
    iy = np.floor(ys).astype(int)
    ix = np.floor(xs).astype(int)
    fy = (ys - iy)[:, None]
    fx = (xs - ix)[None, :]
    iy0 = (iy % cells_y)[:, None]
    iy1 = ((iy + 1) % cells_y)[:, None]
    ix0 = (ix % cells_x)[None, :]
    ix1 = ((ix + 1) % cells_x)[None, :]

    def dot(jy, jx, ox, oy):
        return gx[jy, jx] * (fx - ox) + gy[jy, jx] * (fy - oy)

    n00 = dot(iy0, ix0, 0.0, 0.0)
    n10 = dot(iy0, ix1, 1.0, 0.0)
    n01 = dot(iy1, ix0, 0.0, 1.0)
    n11 = dot(iy1, ix1, 1.0, 1.0)
    u = fx * fx * fx * (fx * (fx * 6 - 15) + 10)
    v = fy * fy * fy * (fy * (fy * 6 - 15) + 10)
    return (n00 * (1 - u) + n10 * u) * (1 - v) + (n01 * (1 - u) + n11 * u) * v


def fbm_periodic(h, w, base_cells, octaves, rng, persistence=0.5):
    total = np.zeros((h, w))
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        c = base_cells * (2 ** o)
        total += amp * perlin_periodic(h, w, c, c, rng)
        norm += amp
        amp *= persistence
    total /= norm
    lo, hi = total.min(), total.max()
    return (total - lo) / (hi - lo)


def voronoi_periodic(size, cells, rng):
    """F1 distance of a jittered-grid Voronoi that tiles with period `cells`; normalised to 0..1."""
    pts = rng.uniform(0.1, 0.9, size=(cells, cells, 2))  # (y, x) jitter inside each lattice cell
    p = (np.arange(size) + 0.5) * (cells / size)
    py = p[:, None]
    px = p[None, :]
    cy = np.floor(py).astype(int)
    cx = np.floor(px).astype(int)
    best = np.full((size, size), 1e9)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            jy = (cy + oy) % cells
            jx = (cx + ox) % cells
            fy = (cy + oy) + pts[jy, jx, 0]
            fx = (cx + ox) + pts[jy, jx, 1]
            d = np.sqrt((py - fy) ** 2 + (px - fx) ** 2)
            best = np.minimum(best, d)
    return np.clip(best / best.max(), 0.0, 1.0)


def stamp_gauss(arr, cx, cy, sx, sy, amp):
    """Screen-blend an anisotropic Gaussian blob into arr (float, 0..1)."""
    h, w = arr.shape
    rx, ry = int(math.ceil(4.0 * sx)), int(math.ceil(4.0 * sy))
    x0, x1 = max(0, int(cx) - rx), min(w, int(cx) + rx + 1)
    y0, y1 = max(0, int(cy) - ry), min(h, int(cy) + ry + 1)
    if x0 >= x1 or y0 >= y1:
        return
    xs = np.arange(x0, x1)[None, :] + 0.5 - cx - 0.5
    ys = np.arange(y0, y1)[:, None] + 0.5 - cy - 0.5
    g = amp * np.exp(-0.5 * ((xs / sx) ** 2 + (ys / sy) ** 2))
    arr[y0:y1, x0:x1] = 1.0 - (1.0 - arr[y0:y1, x0:x1]) * (1.0 - g)


def screen(a, b):
    return 1.0 - (1.0 - a) * (1.0 - b)


# ----------------------------------------------------------------------------- textures
def make_rain():
    h, w = 512, 64
    x = np.arange(w)[None, :] + 0.5
    y = (np.arange(h)[:, None] + 0.5) / h
    across = np.exp(-0.5 * ((x - w / 2) / 4.5) ** 2)
    taper = smoothstep(0.0, 0.32, y) * smoothstep(0.0, 0.18, 1.0 - y)
    bright = 0.62 + 0.38 * y  # leading (lower) end brighter
    a = across * taper * bright
    a = a / a.max()
    a[:, :3] = 0.0
    a[:, -3:] = 0.0
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[..., :3] = 255
    rgba[..., 3] = to_u8(a)
    return Image.fromarray(rgba, "RGBA")


def splash_cell(f, rng_params, C=256):
    """One 256 px splash frame, float intensity 0..1.  rng_params: per-droplet fixed random launch data (same in every frame)."""
    t = f / 15.0
    cx, gy = C * 0.5, C * 0.74
    asp = 0.28  # ground-plane squash for the slightly raised camera
    e = 1.0 - (1.0 - t) ** 2
    R = (0.03 + 0.27 * e) * C
    fade = 1.0 - 0.96 * smoothstep(0.42, 1.0, t)
    s = min(t / 0.88, 1.0)  # flight phase 0..1
    arc = 4.0 * s * (1.0 - s)
    arr = np.zeros((C, C))
    yy, xx = np.mgrid[0:C, 0:C]
    xx = xx + 0.5
    yy = yy + 0.5

    # ground ring (the impact ripple under the crown), a squashed ellipse
    d = np.sqrt((xx - cx) ** 2 + ((yy - gy) / asp) ** 2)
    ring = 0.55 * fade * np.exp(-0.5 * ((d - R * 1.1) / (2.0 + 1.5 * t * 2.0)) ** 2)
    arr = screen(arr, ring)

    # crown film: a thin ellipse floating above the ground at the droplet height, fading out early
    film_h = 0.10 * C * arc
    d2 = np.sqrt((xx - cx) ** 2 + ((yy - (gy - film_h)) / asp) ** 2)
    film = 0.55 * fade * (1.0 - smoothstep(0.1, 0.7, t)) * np.exp(-0.5 * ((d2 - R * 0.92) / 1.7) ** 2)
    arr = screen(arr, film)

    # central jet (Worthington): a column rising from the middle with a droplet on top
    js = float(np.clip((t - 0.08) / 0.8, 0.0, 1.0))
    jarc = 4.0 * js * (1.0 - js)
    if jarc > 0.02:
        jh = 0.30 * C * jarc
        col_y = np.arange(C)[:, None] + 0.5
        col = np.exp(-0.5 * ((xx - cx) / 1.5) ** 2) * ((col_y <= gy) & (col_y >= gy - jh * 0.8))
        arr = screen(arr, 0.38 * fade * col * (1.0 - js))
        stamp_gauss(arr, cx, gy - jh, 2.6, 2.6 + 3.0 * abs(1 - 2 * js), 0.9 * fade)

    # crown droplets
    for (theta, rscale, peak, size) in rng_params:
        h = peak * C * arc
        depth = R * rscale * math.sin(theta) * asp
        px = cx + R * rscale * math.cos(theta)
        py = gy + depth - h
        near = 1.0 + 0.25 * math.sin(theta)  # nearer droplets a little bigger and brighter
        rd = C * (0.0105 + 0.005 * (1.0 - t)) * (0.55 + 0.45 * min(1.0, t * 4.0)) * near * (0.75 + 0.25 * min(1.0, (t + 0.2)))
        stretch = 1.0 + 1.7 * abs(1.0 - 2.0 * s) * (1.0 if s < 1.0 else 0.0)  # fast at launch and at impact, slow at the top
        # thin liquid tail from the rim up to the droplet: this is what makes the ring of dots read as a crown
        tail_a = 0.5 * fade * (1.0 - smoothstep(0.2, 0.7, s)) * min(1.0, h / (0.03 * C))  # mostly while rising
        if tail_a > 0.01:
            ty0, ty1 = int(py), int(gy + depth)
            for ty in range(max(0, ty0), min(C, ty1 + 1), 1):
                k = (ty - ty0) / max(1, ty1 - ty0)  # 0 at the droplet, 1 at the rim: the tail thins toward the droplet
                stamp_gauss(arr, px, ty + 0.5, 0.9 + 0.7 * k, 0.9, tail_a * (0.35 + 0.65 * k))
        stamp_gauss(arr, px, py, rd, rd * stretch, min(1.0, 0.95 * fade * (0.88 + 0.12 * math.sin(theta))))
        # a tiny splash dot where the droplet lands (late frames)
        if t > 0.85:
            stamp_gauss(arr, px, gy + depth, rd * 1.2, rd * 0.5, 0.5 * fade)
    return arr


def make_splash():
    C = 256
    rng = np.random.default_rng(SEEDS["splash"])
    n = 10  # 8..12 droplets
    params = []
    for i in range(n):
        theta = 2.0 * math.pi * (i + rng.uniform(-0.18, 0.18)) / n
        params.append((theta, rng.uniform(0.85, 1.15), rng.uniform(0.15, 0.27), 1.0))
    out = np.zeros((4 * C, 4 * C))
    win = edge_window(C, C, CELL_MARGIN, 8)
    for f in range(16):
        r, c = divmod(f, 4)
        cell = splash_cell(f, params, C) * win
        out[r * C:(r + 1) * C, c * C:(c + 1) * C] = cell
    rgba = np.zeros((4 * C, 4 * C, 4), dtype=np.uint8)
    cool = np.array([0.62, 0.72, 0.86])
    white = np.array([1.0, 1.0, 1.0])
    rgb = cool[None, None, :] * (1 - out[..., None]) + white[None, None, :] * out[..., None]
    rgba[..., :3] = to_u8(rgb)
    rgba[..., 3] = to_u8(out)
    return Image.fromarray(rgba, "RGBA")


def make_ripple():
    n = 256
    ys, xs = np.mgrid[0:n, 0:n]
    dx = (xs + 0.5 - n / 2) / n
    dy = (ys + 0.5 - n / 2) / n
    r = np.sqrt(dx * dx + dy * dy)
    sig = 0.015
    main = np.exp(-0.5 * ((r - 0.42) / sig) ** 2)
    inner = 0.28 * np.exp(-0.5 * ((r - 0.27) / sig) ** 2)
    prof = np.clip(main + inner, 0.0, 1.0)
    prof *= edge_window(n, n, 3, 8)
    # normal-like luminance: the ring is a little brighter on the upper-left side, darker on the lower-right
    light = (-dx - dy) / np.maximum(r, 1e-6) / math.sqrt(2.0)  # -1..1
    lum = np.clip(prof * (0.78 + 0.22 * light), 0.0, 1.0)
    rgba = np.zeros((n, n, 4), dtype=np.uint8)
    rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = to_u8(lum)
    rgba[..., 3] = to_u8(prof)
    return Image.fromarray(rgba, "RGBA")


def _midpoint(p0, p1, rng, rough, levels):
    """Midpoint-displacement polyline between p0 and p1 (x, y) in px.  Displacement is perpendicular, halved (x0.55) per level."""
    pts = [np.array(p0, float), np.array(p1, float)]
    disp = rough
    for _ in range(levels):
        new = []
        for a, b in zip(pts[:-1], pts[1:]):
            m = 0.5 * (a + b)
            d = b - a
            ln = np.hypot(d[0], d[1])
            nrm = np.array([-d[1], d[0]]) / max(ln, 1e-6)
            m = m + nrm * rng.normal(0.0, disp) * min(1.0, ln / 60.0 + 0.3)
            new.extend([a, m])
        new.append(pts[-1])
        pts = new
        disp *= 0.55
    return np.array(pts)


def _dist_to_polyline(xx, yy, pts, chunk=16):
    """Min distance from each pixel to a polyline (vectorised over segments)."""
    best = np.full(xx.shape, 1e9)
    a = pts[:-1]
    b = pts[1:]
    for i in range(0, len(a), chunk):
        ai, bi = a[i:i + chunk], b[i:i + chunk]
        ab = bi - ai
        l2 = np.maximum((ab ** 2).sum(1), 1e-9)
        px = xx[..., None] - ai[:, 0]
        py = yy[..., None] - ai[:, 1]
        t = np.clip((px * ab[:, 0] + py * ab[:, 1]) / l2, 0.0, 1.0)
        dx = px - t * ab[:, 0]
        dy = py - t * ab[:, 1]
        best = np.minimum(best, np.sqrt(dx * dx + dy * dy).min(axis=-1))
    return best


def bolt_cell(seed, C=512):
    rng = np.random.default_rng(seed)
    top, bot = 26.0, C - 26.0
    xmin, xmax = 52.0, C - 52.0
    cx = C / 2.0
    # main channel: top centre -> bottom (end point wanders a little around the centre so the bolts differ)
    end = (cx + rng.uniform(-28, 28), bot)
    main = _midpoint((cx, top), end, rng, rough=rng.uniform(46, 62), levels=6)
    main[:, 0] = np.clip(main[:, 0], xmin, xmax)
    branches = []
    nb = int(rng.integers(2, 6))  # 2..5
    for _ in range(nb):
        k = int(rng.integers(int(len(main) * 0.12), int(len(main) * 0.72)))
        start = main[k]
        side = rng.choice([-1.0, 1.0])
        ang = math.radians(rng.uniform(18, 50))
        length = rng.uniform(0.20, 0.42) * C
        stop = start + np.array([side * math.sin(ang), math.cos(ang)]) * length
        stop[0] = np.clip(stop[0], xmin, xmax)
        stop[1] = min(stop[1], bot - 10)
        br = _midpoint(start, stop, rng, rough=rng.uniform(16, 26), levels=5)
        br[:, 0] = np.clip(br[:, 0], xmin, xmax)
        branches.append(br)
        # an occasional sub-branch
        if rng.random() < 0.35:
            j = int(rng.integers(len(br) // 3, 2 * len(br) // 3))
            s0 = br[j]
            s1 = s0 + np.array([-side * math.sin(math.radians(25)), math.cos(math.radians(25))]) * length * 0.45
            s1[0] = np.clip(s1[0], xmin, xmax)
            s1[1] = min(s1[1], bot - 10)
            branches.append(_midpoint(s0, s1, rng, rough=10, levels=4))
    yy, xx = np.mgrid[0:C, 0:C]
    xx = xx + 0.5
    yy = yy + 0.5
    dm = _dist_to_polyline(xx, yy, main)
    db = np.full((C, C), 1e9)
    for br in branches:
        db = np.minimum(db, _dist_to_polyline(xx, yy, br))

    def layers(d, k):
        core = np.exp(-0.5 * (d / (1.25 * k)) ** 2)
        inner = np.exp(-0.5 * (d / (4.5 * k)) ** 2)
        outer = np.exp(-0.5 * (d / (13.0 * k)) ** 2)
        return core, inner, outer

    mc, mi, mo = layers(dm, 1.0)
    bc, bi, bo = layers(db, 0.62)
    core = np.maximum(mc, 0.85 * bc)
    inner = np.maximum(mi, 0.6 * bi)
    outer = np.maximum(mo, 0.5 * bo)
    inten = np.clip(core + 0.55 * inner + 0.22 * outer, 0.0, 1.0)
    inten *= edge_window(C, C, CELL_MARGIN, 10)
    # glow colour: blue-violet halo -> blue-white -> white core
    halo = np.array([0.50, 0.58, 1.00])
    mid = np.array([0.78, 0.86, 1.00])
    white = np.array([1.0, 1.0, 1.0])
    wc = core[..., None]
    wi = np.clip(inner * 1.2, 0, 1)[..., None]
    col = halo[None, None, :] * (1 - wi) + mid[None, None, :] * wi
    col = col * (1 - wc) + white[None, None, :] * wc
    rgb = col * inten[..., None]  # premultiplied for the additive material
    return rgb, inten


def make_bolts():
    C = 512
    rgba = np.zeros((2 * C, 4 * C, 4), dtype=np.uint8)
    for k in range(8):
        r, c = divmod(k, 4)
        rgb, a = bolt_cell(SEEDS["bolts_first"] + k, C)
        rgba[r * C:(r + 1) * C, c * C:(c + 1) * C, :3] = to_u8(rgb)
        rgba[r * C:(r + 1) * C, c * C:(c + 1) * C, 3] = to_u8(a)
    return Image.fromarray(rgba, "RGBA")


def make_noise():
    n = 512
    r = fbm_periodic(n, n, 4, 4, np.random.default_rng(SEEDS["noise_r"]))
    g = np.roll(r, shift=(173, 311), axis=(0, 1))
    b = voronoi_periodic(n, 8, np.random.default_rng(SEEDS["noise_vor"]))
    rgb = np.stack([r, g, b], axis=-1)
    return Image.fromarray(to_u8(rgb), "RGB")


def make_dot():
    n = 64
    ys, xs = np.mgrid[0:n, 0:n]
    r = np.sqrt((xs + 0.5 - n / 2) ** 2 + (ys + 0.5 - n / 2) ** 2)
    g = np.exp(-0.5 * (r / 9.2) ** 2) * (1.0 - smoothstep(26.0, 31.0, r))
    g /= g.max()
    return Image.fromarray(to_u8(g), "L")


def make_mist():
    n = 256
    rng = np.random.default_rng(SEEDS["mist"])
    f = fbm_periodic(n, n, 3, 4, rng, persistence=0.55)
    ys, xs = np.mgrid[0:n, 0:n]
    r = np.sqrt((xs + 0.5 - n / 2) ** 2 + (ys + 0.5 - n / 2) ** 2) / (n / 2)
    radial = np.exp(-0.5 * (r / 0.36) ** 2)
    v = radial * (0.25 + 1.0 * f ** 1.5)
    v *= 1.0 - smoothstep(0.80, 0.97, r)
    v = v / v.max()
    v = v * (2.0 - v)  # lift the mid tones a little, keep the peak at 1
    return Image.fromarray(to_u8(v), "L")


MAKERS = {"rain": make_rain, "splash": make_splash, "ripple": make_ripple, "bolts": make_bolts,
          "noise": make_noise, "dot": make_dot, "mist": make_mist}


# ----------------------------------------------------------------------------- checks
def check_tiling(img):
    a = np.asarray(img).astype(np.float64)
    # difference across the wrap seam vs the typical difference between neighbouring columns / rows
    seam_x = np.abs(a[:, 0] - a[:, -1]).mean()
    seam_y = np.abs(a[0] - a[-1]).mean()
    typ_x = np.abs(a[:, 1:] - a[:, :-1]).mean()
    typ_y = np.abs(a[1:] - a[:-1]).mean()
    return seam_x, typ_x, seam_y, typ_y


def check_cells(img, ncols, nrows):
    a = np.asarray(img)[..., 3]
    h, w = a.shape
    ch, cw = h // nrows, w // ncols
    worst = 0
    for r in range(nrows):
        for c in range(ncols):
            cell = a[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw]
            m = CELL_MARGIN
            inner = np.zeros_like(cell, dtype=bool)
            inner[m:-m, m:-m] = True
            border_max = int(cell[~inner].max())
            worst = max(worst, border_max)
    return worst


def run_checks(imgs):
    ok = True
    print("--- checks ---")
    if "noise" in imgs:
        sx, tx, sy, ty = check_tiling(imgs["noise"])
        good = sx <= 2.0 * tx and sy <= 2.0 * ty
        print("noise tiling: seam mean|d| x %.3f (neighbour %.3f), y %.3f (neighbour %.3f) -> %s" % (sx, tx, sy, ty, "OK" if good else "FAIL"))
        ok &= good
    for key, (nc, nr) in (("splash", (4, 4)), ("bolts", (4, 2))):
        if key in imgs:
            worst = check_cells(imgs[key], nc, nr)
            good = worst == 0
            print("%s %dx%d cells: max alpha in the %d px cell border = %d -> %s" % (key, nc, nr, CELL_MARGIN, worst, "OK" if good else "FAIL"))
            ok &= good
    if "splash" in imgs:
        a = np.asarray(imgs["splash"])[..., 3]
        peaks = [int(a[(f // 4) * 256:(f // 4 + 1) * 256, (f % 4) * 256:(f % 4 + 1) * 256].max()) for f in range(16)]
        cover = [float((a[(f // 4) * 256:(f // 4 + 1) * 256, (f % 4) * 256:(f % 4 + 1) * 256] > 20).mean()) for f in range(16)]
        print("splash per-frame max alpha:", peaks)
        print("splash per-frame covered fraction (>20): ", ["%.3f" % c for c in cover])
    if "bolts" in imgs:
        a = np.asarray(imgs["bolts"])[..., 3]
        print("bolt cell coverage (>40):", ["%.3f" % (a[(k // 4) * 512:(k // 4 + 1) * 512, (k % 4) * 512:(k % 4 + 1) * 512] > 40).mean() for k in range(8)])
    for key, img in imgs.items():
        arr = np.asarray(img)
        print("%-7s %s %s min %d max %d" % (key, img.size, img.mode, arr.min(), arr.max()))
    return ok


# ----------------------------------------------------------------------------- contact sheet
def load_font(size):
    for p in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def composite(img, bg, mode):
    """Return an RGB PIL image of `img` shown on a flat background (bg 0..255).  mode: 'over' (straight alpha), 'add' (premultiplied/additive), 'lum' (L as white-with-alpha)."""
    if img.mode == "L":
        a = np.asarray(img).astype(np.float64) / 255.0
        rgb = np.ones(a.shape + (3,))
    elif img.mode == "RGB":
        a = np.ones(img.size[::-1])
        rgb = np.asarray(img).astype(np.float64) / 255.0
    else:
        arr = np.asarray(img).astype(np.float64) / 255.0
        rgb, a = arr[..., :3], arr[..., 3]
    b = bg / 255.0
    if mode == "add":
        out = np.clip(b + rgb, 0, 1)
    else:
        out = rgb * a[..., None] + b * (1 - a[..., None])
    return Image.fromarray(to_u8(out), "RGB")


def alpha_view(img):
    if img.mode == "L":
        return img.convert("RGB")
    if img.mode == "RGB":
        return img.copy()
    return Image.merge("RGB", [img.getchannel("A")] * 3)


def outline_grid(im, ncols, nrows, scale, colour=(255, 60, 60)):
    d = ImageDraw.Draw(im)
    w, h = im.size
    for c in range(ncols + 1):
        x = min(w - 1, int(round(c * w / ncols)))
        d.line([(x, 0), (x, h)], fill=colour, width=1)
    for r in range(nrows + 1):
        y = min(h - 1, int(round(r * h / nrows)))
        d.line([(0, y), (w, y)], fill=colour, width=1)


def fit(im, maxw, maxh, resample=Image.LANCZOS):
    s = min(maxw / im.width, maxh / im.height)
    if s >= 1.0:
        s = max(1.0, math.floor(s))  # integer upscale for tiny sources
        return im.resize((int(im.width * s), int(im.height * s)), Image.NEAREST)
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), resample)


def build_sheet(imgs, path):
    font = load_font(18)
    small = load_font(14)
    PAD = 16
    rows = []  # each row: (title, [PIL panels], [panel captions])

    def panels_for(key, img, mode, grid=None, maxw=600, maxh=520):
        ps = []
        for bg, cap in ((128, "on grey 128"), (0, "on black")):
            p = fit(composite(img, bg, mode), maxw, maxh)
            ps.append((p, cap))
        a = fit(alpha_view(img), maxw, maxh)
        ps.append((a, "alpha" if img.mode != "RGB" else "RGB"))
        if grid:
            for p, _ in ps:
                outline_grid(p, grid[0], grid[1], 1)
        return ps

    if "rain" in imgs:
        rows.append(("T_LB_FX_RainStreak 64x512 (1:1, upscaled x1)", panels_for("rain", imgs["rain"], "over", maxw=300, maxh=512)))
    if "ripple" in imgs:
        rows.append(("T_LB_FX_Ripple 256x256 (x2)", panels_for("ripple", imgs["ripple"], "over", maxw=512, maxh=512)))
    if "noise" in imgs:
        n = imgs["noise"]
        chans = [(Image.merge("RGB", [n.getchannel(i)] * 3), nm) for i, nm in enumerate(("R fbm", "G offset fbm", "B voronoi"))]
        tile = Image.new("RGB", (n.width * 2, n.height * 2))
        for yy in range(2):
            for xx in range(2):
                tile.paste(n.getchannel(0).convert("RGB"), (xx * n.width, yy * n.height))
        chans = [(fit(c, 360, 360), nm) for c, nm in chans] + [(fit(tile, 360, 360), "R tiled 2x2 (seams)")]
        rows.append(("T_LB_FX_Noise 512x512 (no alpha)", chans))
    if "dot" in imgs:
        d = imgs["dot"]
        rows.append(("T_LB_FX_SoftDot 64x64 (x5)", panels_for("dot", d, "over", maxw=320, maxh=320)))
    if "mist" in imgs:
        rows.append(("T_LB_FX_MistPuff 256x256 (x2)", panels_for("mist", imgs["mist"], "over", maxw=512, maxh=512)))
    if "splash" in imgs:
        rows.append(("T_LB_FX_Splash 1024x1024, 4x4 SubUV (x0.5; red = cell grid)", panels_for("splash", imgs["splash"], "over", grid=(4, 4), maxw=512, maxh=512)))
        s = imgs["splash"]
        frames = []
        for f in range(16):
            r, c = divmod(f, 4)
            cell = s.crop((c * 256, r * 256, (c + 1) * 256, (r + 1) * 256))
            frames.append((composite(cell, 0, "over"), "frame %d" % f))
        # 16 frames as two rows of 8 at 1:1
        for part in (0, 1):
            rows.append(("splash frames %d..%d at 1:1 on black" % (part * 8, part * 8 + 7), frames[part * 8:(part + 1) * 8]))
    if "bolts" in imgs:
        rows.append(("T_LB_FX_Bolts 2048x1024, 4x2 atlas (x0.25, additive over bg; red = cell grid; cell k = row*4+col)", panels_for("bolts", imgs["bolts"], "add", grid=(4, 2), maxw=640, maxh=320)))
        b = imgs["bolts"]
        for part in (0, 1):
            fr = []
            for k in range(part * 4, part * 4 + 4):
                r, c = divmod(k, 4)
                cell = b.crop((c * 512, r * 512, (c + 1) * 512, (r + 1) * 512))
                fr.append((fit(composite(cell, 0, "add"), 512, 512), "cell %d (seed %d)" % (k, 101 + k)))
            rows.append(("bolt cells %d..%d at 1:1 on black (additive)" % (part * 4, part * 4 + 3), fr))
        # grey bg of the first cell group, to see the glow on a lighter backdrop
        fr = []
        for k in (0, 5):
            r, c = divmod(k, 4)
            cell = b.crop((c * 512, r * 512, (c + 1) * 512, (r + 1) * 512))
            fr.append((fit(composite(cell, 60, "add"), 512, 512), "cell %d on dark grey 60" % k))
            fr.append((fit(alpha_view(cell), 512, 512), "cell %d alpha" % k))
        rows.append(("bolt cells on dark grey, and alpha", fr))

    W = 0
    layout = []
    for title, ps in rows:
        w = PAD + sum(p.width + PAD for p, _ in ps)
        h = max(p.height for p, _ in ps) + 28 + 22
        layout.append((title, ps, w, h))
        W = max(W, w)
    H = PAD + sum(h + PAD for _, _, _, h in layout)
    sheet = Image.new("RGB", (W, H), (24, 24, 28))
    d = ImageDraw.Draw(sheet)
    y = PAD
    for title, ps, w, h in layout:
        d.text((PAD, y), title, font=font, fill=(235, 235, 235))
        x = PAD
        for p, cap in ps:
            sheet.paste(p, (x, y + 28))
            d.text((x, y + 28 + p.height + 3), cap, font=small, fill=(170, 170, 170))
            x += p.width + PAD
        y += h + PAD
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sheet.save(path, optimize=False, compress_level=6)
    return sheet.size


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "SourceArt", "FX"))
    ap.add_argument("--sheet", default=os.path.join(ROOT, "Docs", "ArtTest", "fx", "p15_textures_sheet.png"))
    ap.add_argument("--only", nargs="*", choices=NAMES)
    ap.add_argument("--no-sheet", action="store_true")
    args = ap.parse_args()
    names = args.only or NAMES
    os.makedirs(args.out, exist_ok=True)
    imgs = {}
    for nm in names:
        img = MAKERS[nm]()
        imgs[nm] = img
        p = os.path.join(args.out, FILES[nm])
        img.save(p, optimize=False, compress_level=6)
        data = open(p, "rb").read()
        print("wrote %-24s %-10s %-4s %8d bytes  sha1 %s" % (FILES[nm], "%dx%d" % img.size, img.mode, len(data), hashlib.sha1(data).hexdigest()[:12]))
    ok = run_checks(imgs)
    if not args.no_sheet and len(names) == len(NAMES):
        size = build_sheet(imgs, args.sheet)
        print("sheet %s %dx%d" % (args.sheet, size[0], size[1]))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
