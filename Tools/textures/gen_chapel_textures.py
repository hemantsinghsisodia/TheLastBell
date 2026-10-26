"""gen_chapel_textures.py -- seeded, deterministic generator for the P8 chapel textures (Python + PIL + numpy, no other deps).

    python Tools/textures/gen_chapel_textures.py [--out ExternalAssets/Generated/chapel] [--preview Docs/ArtTest/chapel] [--only name ...]

Produces (PNG; RGBA where noted):
  T_LB_StainedGlass_Lancet_A / _B  512x2048 RGBA  A = lead mask (1 = lead).  Muted palette, ruby/amber border band, diamond quarries, central vesica medallion.
  T_LB_StainedGlass_East           1024x2048 RGBA 1:2 atlas: left light u 0..0.5 / v 0..0.75, right light u 0.5..1 / v 0..0.75, quatrefoil u 0.25..0.75 / v 0.75..1
                                   (matches SM_LB_Prop_Glass_East); two abstract hooded robed figures, quatrefoil with a bell motif.  No faces.
  T_LB_LightPool_Lancet            512x1024 RGB   Lancet_A, colour only, blurred, lead lines kept as faint dark lines.
  T_LB_Decal_ChalkCircle           2048x2048 RGBA scrawled ritual circle: rings O300 / O250 cm, 12 invented glyphs, a bell, 4 scuffed gaps, 2 smudge trails.
  T_LB_Decal_ChalkSigil            512x512   RGBA invented sigil with a bell.
  T_LB_Decal_ChalkTally            512x256   RGBA 4 groups of five.
  T_LB_Cobweb_A                    1024x1024 RGBA radial web (fallback; C0 uses the Dungeon pack's cobweb material).
  T_LB_RoofSlates_diff / _nor_dx / _rough / _arm  2048x1024 (_rough is the source rough map = constant 1.0; _arm = AO/rough/metal): roof_slates_03 with the ridge-cap strip removed and whole slate courses kept so it tiles vertically.
  T_LB_Decal_Soot_A / _B 512x1024, _Mould_Band 1024x256, _WaterStain 1024^2, _WaxDrips 512^2, _DragMarks 1024x512 (authored 600x120 cm, squeezed 2.5x in u),
                                   _LeafLitter_A / _B 1024^2 (LeafSet030 leaf cells), _DustDrift 1024^2 (dense corner = texture top-left)   -- all RGBA, A = opacity (P8-10a grime)
Previews: tex_*.png in the preview folder (2x2 tile preview for the slates).

Seeds are in SEEDS below (every random number comes from numpy default_rng(seed); nothing else is random).  The chalk glyphs are invented
(arcs, hooks, spirals, waves, diagonal tick groups, small loops); no real-world religious or hate symbols are used and the glyph generator never
makes right-angle crossings (no crosses, no swastika-like forms).  Stained glass: no faces (the figures' cowls are dark voids).
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SEEDS = {
    "lancet_a": 8101,
    "lancet_b": 8202,
    "east": 8303,
    "lightpool": 8404,
    "chalk_circle": 8505,
    "chalk_sigil": 8606,
    "chalk_tally": 8707,
    "cobweb": 8808,
    "slates": 8909,
    # P8-10a grime decals
    "soot_a": 9101,
    "soot_b": 9102,
    "mould": 9203,
    "waterstain": 9304,
    "wax": 9405,
    "drag": 9506,
    "leaf_a": 9607,
    "leaf_b": 9608,
    "dust": 9709,
}
# muted palette (plan P8-3)
BLUE = np.array((0.10, 0.16, 0.42), np.float32)
RUBY = np.array((0.45, 0.06, 0.08), np.float32)
AMBER = np.array((0.55, 0.36, 0.08), np.float32)
GREEN = np.array((0.10, 0.30, 0.14), np.float32)
VIOLET = np.array((0.25, 0.10, 0.35), np.float32)
PALE = np.array((0.55, 0.58, 0.60), np.float32)
BLUEGREY = (BLUE * 0.55 + PALE * 0.45).astype(np.float32)
LEAD = np.array((0.03, 0.03, 0.035), np.float32)


# ----------------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------------
def vnoise(h, w, cell_h, cell_w, rng):
    """Smooth value noise in [0, 1] (bicubic upsample of a random lattice)."""
    ch, cw = max(2, int(cell_h)), max(2, int(cell_w))
    gh, gw = int(math.ceil(h / ch)) + 3, int(math.ceil(w / cw)) + 3
    g = rng.random((gh, gw)).astype(np.float32)
    im = Image.fromarray(g).resize((gw * cw, gh * ch), Image.BICUBIC)
    a = np.asarray(im, dtype=np.float32)
    return np.clip(a[ch:ch + h, cw:cw + w], 0.0, 1.0)


def fbm(h, w, cell, octs, rng):
    tot = np.zeros((h, w), np.float32)
    amp, norm, c = 1.0, 0.0, float(cell)
    for _ in range(octs):
        tot += amp * vnoise(h, w, max(2.0, c), max(2.0, c), rng)
        norm += amp
        amp *= 0.5
        c *= 0.5
    return tot / norm


def hash01(a, b, seed):
    """Deterministic per-cell pseudo random in [0, 1) from integer-valued arrays."""
    x = (a.astype(np.int64) * 73856093) ^ (b.astype(np.int64) * 19349663) ^ (seed * 83492791)
    x = (x ^ (x >> 13)) * 1274126177
    x = x ^ (x >> 16)
    return ((x & 0xFFFFFF).astype(np.float64) / float(0x1000000)).astype(np.float32)


def save_img(arr, path):
    arr = np.clip(arr, 0.0, 1.0)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray((arr * 255.0 + 0.5).astype(np.uint8)).save(path)


def down(arr, ss):
    if ss == 1:
        return arr
    h, w = arr.shape[:2]
    return arr.reshape(h // ss, ss, w // ss, ss, *arr.shape[2:]).mean(axis=(1, 3))


def pick(r, table):
    out = np.zeros(r.shape + (3,), np.float32)
    done = np.zeros(r.shape, bool)
    for th, col in table:
        m = (r < th) & ~done
        out[m] = col
        done |= m
    return out


def as_mask(im):
    return np.asarray(im, np.float32) / 255.0


def shape_mask(h, w, fn):
    im = Image.new('L', (w, h), 0)
    fn(ImageDraw.Draw(im))
    return im


def outline(im, px):
    """Boolean band of about `px` pixels centred on the edge of a mask image."""
    k = int(px) | 1
    return (as_mask(im.filter(ImageFilter.MaxFilter(k))) - as_mask(im.filter(ImageFilter.MinFilter(k)))) > 0.5


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ----------------------------------------------------------------------------------------------
# stained glass: lancet
# ----------------------------------------------------------------------------------------------
def pointed_d(xc, zc, half, R, zs):
    """Distance (cm) to the outline inside a lancet shape (jambs up to zs, two-centred head of radius R); negative outside."""
    strip = half - np.abs(xc)
    cx = -half + R
    dl = R - np.hypot(xc - cx, zc - zs)
    dr = R - np.hypot(xc + cx, zc - zs)
    return np.where(zc > zs, np.minimum(strip, np.minimum(dl, dr)), np.minimum(strip, zc))


def border_s(xc, zc, half, R, zs):
    """Arc length (cm) along the outline from the bottom (left side mirrored onto both sides)."""
    cx = -half + R
    th = np.arctan2(zc - zs, -np.abs(xc) - cx)
    return np.where(zc > zs, zs + R * (math.pi - th), zc)


def diamond_field(fx, fy, cw, ch, lead_px, seed, table):
    u = fx / (cw / 2.0) + fy / (ch / 2.0)
    v = fx / (cw / 2.0) - fy / (ch / 2.0)
    iu, iv = np.floor(u), np.floor(v)
    fu, fv = u - iu, v - iv
    gm = float(np.hypot(1 / (cw / 2.0), 1 / (ch / 2.0)))
    dq = np.minimum(np.minimum(fu, 1 - fu), np.minimum(fv, 1 - fv)) / gm
    col = pick(hash01(iu, iv, seed), table)
    bright = 1.0 + (hash01(iu + 17, iv - 5, seed + 1) - 0.5) * 0.16          # +-8 % per cell
    shade = 1.0 + (fu - 0.5) * 0.06 + (fv - 0.5) * 0.04
    return col, bright * shade, dq < lead_px * 0.5


def lancet_texture(seed, variant):
    rng = np.random.default_rng(seed)
    SS = 2
    W, H = 512 * SS, 2048 * SS
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    pxcm = W / 140.0 / SS                                    # final px per cm
    xc = (xs + 0.5) / SS / pxcm - 70.0
    zc = (H - (ys + 0.5)) / SS / pxcm
    half, R = 70.0, 112.0
    zs = 560.0 - math.sqrt(R * R - (R - half) ** 2)
    d = pointed_d(xc, zc, half, R, zs) * pxcm                # inside distance, final px
    inside = d > 0
    fx, fy = xs / SS, ys / SS
    streak = vnoise(H, W, 220 * SS, 9 * SS, rng)             # vertical glass streaks
    streak2 = fbm(H, W, 40 * SS, 3, rng)
    gtex = (1.0 + (streak - 0.5) * 0.16 + (streak2 - 0.5) * 0.10)
    if variant == 'A':
        tab = [(0.66, BLUEGREY), (0.80, PALE), (0.90, VIOLET), (0.96, BLUE), (1.01, AMBER)]
        c_out, c_in, c_ros, c_pet, c_cen = RUBY, BLUE, RUBY, GREEN, PALE
    else:
        tab = [(0.60, BLUEGREY), (0.78, VIOLET), (0.88, PALE), (0.95, GREEN), (1.01, BLUE)]
        c_out, c_in, c_ros, c_pet, c_cen = AMBER, VIOLET, BLUE, RUBY, PALE
    col, bright, lead_q = diamond_field(fx, fy, 64.0, 96.0, 6.0, seed, tab)
    glass = col * (bright * gtex)[..., None]
    lead = lead_q.astype(np.float32)
    # border band 24 px: alternating ruby / amber squares
    band = inside & (d <= 24.0)
    s = border_s(xc, zc, half, R, zs) * pxcm / 24.0
    idx = np.floor(s)
    fs = s - idx
    bcol = np.where((idx % 2 == 0)[..., None], RUBY, AMBER).astype(np.float32)
    bb = 1.0 + (hash01(idx, np.zeros_like(idx), seed + 3) - 0.5) * 0.16
    glass[band] = (bcol * (bb * gtex)[..., None])[band]
    lead[band] = (np.minimum(fs, 1 - fs) * 24.0 < 3.0)[band]
    lead[inside & (np.abs(d - 24.0) < 3.0)] = 1.0
    lead[d < 3.0] = 1.0
    lead[~inside] = 1.0
    # medallion: vertical vesica at 55 % height (two circles r 275, centres +-165)
    mx, my = fx - 256.0, fy - 2048.0 * 0.45
    dves = np.minimum(275.0 - np.hypot(mx - 165.0, my), 275.0 - np.hypot(mx + 165.0, my))
    med = dves > 0
    glass[med] = (c_out * gtex[med][:, None])
    lead[med] = 0.0
    inner = dves > 34.0
    glass[inner] = (c_in * gtex[inner][:, None])
    lead[np.abs(dves) < 4.0] = 1.0
    lead[(np.abs(dves - 34.0) < 3.0) & med] = 1.0
    # inside the vesica: a central roundel (hexafoil rosette) and two small end roundels stacked on the long axis
    rr = np.hypot(mx, my)
    for (cy_, rad_, fillc) in ((0.0, 64.0, c_ros), (-128.0, 30.0, c_cen), (128.0, 30.0, c_cen)):
        rd = np.hypot(mx, my - cy_)
        sel = inner & (rd < rad_)
        glass[sel] = (fillc * gtex[sel][:, None])
        lead[inner & (np.abs(rd - rad_) < 3.0)] = 1.0
    ros = inner & (rr < 64.0)
    petal = np.zeros(rr.shape, bool)
    dpet = np.full(rr.shape, 1e9, np.float32)
    for k in range(6):                                       # hexafoil rosette: 6 petals r 20 at distance 34
        pa = math.radians(60.0 * k + 30.0)
        dk = np.hypot(mx - 34.0 * math.cos(pa), my - 34.0 * math.sin(pa))
        petal |= dk < 20.0
        dpet = np.minimum(dpet, np.abs(dk - 20.0))
    glass[petal & ros] = (c_pet * gtex[petal & ros][:, None])
    glass[(rr < 15.0) & ros] = c_cen
    lead[ros & (dpet < 3.0)] = 1.0
    lead[ros & (np.abs(rr - 15.0) < 3.0)] = 1.0
    out = np.where(lead[..., None] > 0.5, LEAD, glass).astype(np.float32)
    return np.dstack([down(out, SS), down(lead, SS)[..., None]])


# ----------------------------------------------------------------------------------------------
# stained glass: east window (atlas)
# ----------------------------------------------------------------------------------------------
def east_light(seed, robe, accent, staff):
    """One light, 512 x 1536 px (y = 0 at the apex).  Returns (rgb, lead)."""
    rng = np.random.default_rng(seed)
    SS = 2
    W, H = 512 * SS, 1536 * SS
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    fx, fy = xs / SS, ys / SS
    xc = (xs + 0.5) / SS / 512.0 * 144.0 - 72.0              # cm (144 x 464.7)
    zc = (H - (ys + 0.5)) / SS / 1536.0 * 464.7
    half, R, zs = 72.0, 144.0, 340.0
    d = pointed_d(xc, zc, half, R, zs) * 3.43
    inside = d > 0
    streak = vnoise(H, W, 200 * SS, 9 * SS, rng)
    streak2 = fbm(H, W, 40 * SS, 3, rng)
    gtex = (1.0 + (streak - 0.5) * 0.16 + (streak2 - 0.5) * 0.10)
    col, bright, lead_q = diamond_field(fx, fy, 80.0, 128.0, 6.0, seed,
                                        [(0.55, BLUEGREY * 1.2), (0.78, PALE * 0.95), (0.90, BLUE * 1.5), (1.01, VIOLET * 1.5)])
    glass = col * (bright * gtex)[..., None]
    lead = lead_q.astype(np.float32)
    band = inside & (d <= 22.0)
    s = border_s(xc, zc, half, R, zs) * 3.43 / 22.0
    idx = np.floor(s)
    fs = s - idx
    bcol = np.where((idx % 2 == 0)[..., None], RUBY, AMBER).astype(np.float32)
    glass[band] = (bcol * gtex[..., None])[band]
    lead[band] = (np.minimum(fs, 1 - fs) * 22.0 < 3.0)[band]
    lead[inside & (np.abs(d - 22.0) < 3.0)] = 1.0
    lead[d < 3.0] = 1.0
    lead[~inside] = 1.0
    S = lambda pts: [(x * SS, y * SS) for x, y in pts]
    cx0 = 256.0
    # plain sun disc behind the head (no halo, no rays)
    disc = shape_mask(H, W, lambda dr: dr.ellipse(S([(cx0 - 98, 420), (cx0 + 98, 616)]), fill=255))
    m = as_mask(disc) > 0.5
    glass[m] = (PALE * 1.3 * gtex[..., None])[m]
    lead[m] = 0.0
    lead[outline(disc, 6 * SS)] = 1.0
    # robe, shoulders, hood (dark void, no face), sash / hem
    robe_im = shape_mask(H, W, lambda dr: dr.polygon(S([(212, 585), (300, 585), (356, 628), (372, 790), (384, 1190), (412, 1470), (100, 1470), (128, 1190), (140, 790), (156, 628)]), fill=255))
    rm = as_mask(robe_im) > 0.5
    glass[rm] = (robe * (1.0 + (streak2 - 0.5) * 0.24)[..., None])[rm]
    lead[rm] = 0.0
    lead[outline(robe_im, 6 * SS)] = 1.0
    hood = shape_mask(H, W, lambda dr: dr.ellipse(S([(cx0 - 54, 452), (cx0 + 54, 588)]), fill=255))
    glass[as_mask(hood) > 0.5] = (robe * 0.75)
    lead[as_mask(hood) > 0.5] = 0.0
    lead[outline(hood, 6 * SS)] = 1.0
    face = shape_mask(H, W, lambda dr: dr.ellipse(S([(cx0 - 32, 486), (cx0 + 32, 574)]), fill=255))
    glass[as_mask(face) > 0.5] = np.array((0.02, 0.025, 0.06), np.float32)
    lead[as_mask(face) > 0.5] = 0.0
    lead[outline(face, 5 * SS)] = 1.0
    folds = shape_mask(H, W, lambda dr: [dr.line(S([(cx0 + o * 0.35, 700), (cx0 + o * 0.7, 1000), (cx0 + o * 1.0, 1450)]), fill=255, width=6 * SS) for o in (-120, -62, -14, 40, 98)]
                       + [dr.line(S([(188, 690), (cx0, 800)]), fill=255, width=6 * SS), dr.line(S([(324, 690), (cx0, 800)]), fill=255, width=6 * SS)])
    lead[(as_mask(folds) > 0.5) & rm] = 1.0
    sash = shape_mask(H, W, lambda dr: (dr.polygon(S([(176, 880), (336, 880), (340, 930), (172, 930)]), fill=255), dr.polygon(S([(98, 1410), (414, 1410), (418, 1470), (94, 1470)]), fill=255)))
    sm = (as_mask(sash) > 0.5) & rm
    glass[sm] = (accent * gtex[..., None])[sm]
    lead[sm] = 0.0
    lead[outline(sash, 6 * SS) & rm] = 1.0
    # staff in the figure's right hand
    sx = 372.0 if staff == 'ring' else 140.0
    stf = shape_mask(H, W, lambda dr: dr.rectangle(S([(sx - 7, 640), (sx + 7, 1470)]), fill=255))
    glass[as_mask(stf) > 0.5] = (accent * 1.2)
    lead[as_mask(stf) > 0.5] = 0.0
    lead[outline(stf, 5 * SS)] = 1.0
    if staff == 'ring':
        top = shape_mask(H, W, lambda dr: dr.ellipse(S([(sx - 30, 590), (sx + 30, 650)]), fill=255))
        glass[as_mask(top) > 0.5] = (PALE * 1.2)
        lead[as_mask(top) > 0.5] = 0.0
        lead[outline(top, 5 * SS)] = 1.0
    else:
        top = shape_mask(H, W, lambda dr: dr.arc(S([(sx - 34, 570), (sx + 34, 650)]), 180, 330, fill=255, width=9 * SS))
        glass[as_mask(top) > 0.5] = (accent * 1.2)
        lead[as_mask(top) > 0.5] = 0.0
        lead[outline(top, 5 * SS)] = 1.0
    lead[~inside] = 1.0
    lead[d < 3.0] = 1.0
    out = np.where(lead[..., None] > 0.5, LEAD, glass).astype(np.float32)
    return down(out, SS), down(lead, SS)


def quat_extent(r_out=45.0, rot=45.0):
    th = np.linspace(0, 2 * math.pi, 2000, endpoint=False)
    rho = 0.5333 * r_out
    dd = r_out - rho
    r = np.zeros_like(th)
    for q in range(4):
        dl = th - (math.radians(rot) + q * math.pi / 2)
        s = dd * np.sin(dl)
        ok = np.abs(s) < rho
        r = np.where(ok, np.maximum(r, dd * np.cos(dl) + np.sqrt(np.maximum(rho * rho - s * s, 0.0))), r)
    return float(np.max(r * np.cos(th))), float(np.max(r * np.sin(th)))


def quat_radius(theta, r_out=45.0, rot=45.0):
    rho = 0.5333 * r_out
    dd = r_out - rho
    r = np.zeros_like(theta)
    for q in range(4):
        dl = theta - (math.radians(rot) + q * math.pi / 2)
        s = dd * np.sin(dl)
        ok = np.abs(s) < rho
        r = np.where(ok, np.maximum(r, dd * np.cos(dl) + np.sqrt(np.maximum(rho * rho - s * s, 0.0))), r)
    return r


def east_quatrefoil(seed):
    """512 x 512: quatrefoil (circumscribed O90, lobes at 45 deg), bell motif."""
    rng = np.random.default_rng(seed)
    SS = 2
    N = 512 * SS
    ys, xs = np.mgrid[0:N, 0:N].astype(np.float32)
    fx, fy = xs / SS, ys / SS
    ex, ez = quat_extent()
    pxcm = 512.0 / (2 * ex)
    xcm = (fx - 256.0) / pxcm
    zcm = (256.0 - fy) / pxcm
    r = np.hypot(xcm, zcm)
    th = np.arctan2(zcm, xcm)
    d = (quat_radius(th) - r) * pxcm
    inside = d > 0
    streak2 = fbm(N, N, 40 * SS, 3, rng)
    gtex = 1.0 + (streak2 - 0.5) * 0.2
    col, bright, lead_q = diamond_field(fx, fy, 48.0, 72.0, 5.0, seed, [(0.5, BLUE * 1.5), (0.8, VIOLET * 1.6), (1.01, BLUEGREY * 1.1)])
    glass = col * (bright * gtex)[..., None]
    lead = lead_q.astype(np.float32)
    band = inside & (d <= 20.0)
    cell = np.floor((th + math.pi) / (2 * math.pi) * 28.0)
    fs = (th + math.pi) / (2 * math.pi) * 28.0 - cell
    glass[band] = (np.where((cell % 2 == 0)[..., None], RUBY, AMBER).astype(np.float32) * gtex[..., None])[band]
    lead[band] = (np.minimum(fs, 1 - fs) < 0.08)[band]
    lead[inside & (np.abs(d - 20.0) < 2.5)] = 1.0
    lead[d < 3.0] = 1.0
    lead[~inside] = 1.0
    S = lambda pts: [(x * SS, y * SS) for x, y in pts]
    # bell: right profile (rel x, rel y from the lip up), mirrored; height 250 px, lip width 190 px
    prof = [(1.0, 0.0), (0.96, 0.06), (0.82, 0.14), (0.64, 0.26), (0.58, 0.45), (0.5, 0.62), (0.36, 0.8), (0.16, 0.94), (0.0, 1.0)]
    bh, bw, bx, by = 250.0, 95.0, 256.0, 330.0                       # lip at y = 330, top at 80
    right = [(bx + bw * px_, by - bh * py_) for px_, py_ in prof]
    left = [(bx - bw * px_, by - bh * py_) for px_, py_ in prof[::-1]]
    bell = shape_mask(N, N, lambda dr: dr.polygon(S(right + left), fill=255))
    bm = as_mask(bell) > 0.5
    glass[bm] = (AMBER * 1.35 * gtex[..., None])[bm]
    lead[bm] = 0.0
    lead[outline(bell, 6 * SS)] = 1.0
    lip = shape_mask(N, N, lambda dr: dr.rectangle(S([(bx - bw - 6, by - 26), (bx + bw + 6, by)]), fill=255))
    lm = as_mask(lip) > 0.5
    glass[lm] = (AMBER * 0.8)
    lead[lm] = 0.0
    lead[outline(lip, 5 * SS)] = 1.0
    clap = shape_mask(N, N, lambda dr: dr.ellipse(S([(bx - 22, by + 6), (bx + 22, by + 50)]), fill=255))
    glass[as_mask(clap) > 0.5] = (PALE * 1.2)
    lead[as_mask(clap) > 0.5] = 0.0
    lead[outline(clap, 5 * SS)] = 1.0
    loop = shape_mask(N, N, lambda dr: dr.ellipse(S([(bx - 26, 46), (bx + 26, 98)]), outline=255, width=9 * SS))
    glass[as_mask(loop) > 0.5] = (AMBER * 1.1)
    lead[as_mask(loop) > 0.5] = 0.0
    lead[outline(loop, 5 * SS)] = 1.0
    # sound arcs left and right of the bell (3 each)
    arcs = shape_mask(N, N, lambda dr: [dr.arc(S([(bx - bw - 14 - k * 22, by - 160 - k * 8), (bx - bw + 70 - k * 22 + 40, by - 20 + k * 8)]), 120, 240, fill=255, width=5 * SS) for k in range(3)]
                      + [dr.arc(S([(bx + bw - 70 + k * 22 - 40, by - 160 - k * 8), (bx + bw + 14 + k * 22, by - 20 + k * 8)]), 300, 60, fill=255, width=5 * SS) for k in range(3)])
    lead[(as_mask(arcs) > 0.5) & inside & (d > 24.0)] = 1.0
    out = np.where(lead[..., None] > 0.5, LEAD, glass).astype(np.float32)
    return down(out, SS), down(lead, SS)


def east_texture(seed):
    atlas = np.zeros((2048, 1024, 4), np.float32)
    atlas[..., :3] = LEAD
    atlas[..., 3] = 1.0
    for k, (robe, accent, staff, xo) in enumerate(((RUBY, AMBER, 'ring', 0), (GREEN, PALE, 'crook', 512))):
        rgb, lead = east_light(seed + 1 + k, robe, accent, staff)
        atlas[512:2048, xo:xo + 512, :3] = rgb
        atlas[512:2048, xo:xo + 512, 3] = lead
    rgb, lead = east_quatrefoil(seed + 9)
    atlas[0:512, 256:768, :3] = rgb
    atlas[0:512, 256:768, 3] = lead
    return atlas


def lightpool_texture(lancet):
    """Lancet_A -> 512 x 1024, Gaussian blur 6 px, the lead lines kept as faint dark lines."""
    im = Image.fromarray((np.clip(lancet[..., :3], 0, 1) * 255).astype(np.uint8)).resize((512, 1024), Image.LANCZOS)
    lead = Image.fromarray((lancet[..., 3] * 255).astype(np.uint8)).resize((512, 1024), Image.LANCZOS)
    col = im.filter(ImageFilter.GaussianBlur(6))
    lead_b = np.asarray(lead.filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255.0
    c = np.asarray(col, np.float32) / 255.0
    # glass colour (lead pixels re-filled from the blurred neighbourhood) darkened faintly where the lead is
    out = c * (1.0 - 0.28 * lead_b)[..., None]
    return np.clip(out * 1.15, 0, 1)


# ----------------------------------------------------------------------------------------------
# chalk
# ----------------------------------------------------------------------------------------------
CHALK = np.array((0.88, 0.86, 0.82), np.float32)


def chalk_rgba(mask_im, rng, out_size, ss, soft=1.4, extra=None):
    """Chalk-grain alpha from a supersampled L mask image."""
    m = mask_im.filter(ImageFilter.GaussianBlur(soft * ss))
    m = m.resize((out_size[0], out_size[1]), Image.BOX)
    m = as_mask(m)
    h, w = m.shape
    g1 = fbm(h, w, 3, 3, rng)
    g2 = rng.random((h, w)).astype(np.float32)
    grain = 0.55 * g1 + 0.45 * g2
    thr = 0.10 + 0.55 * grain
    a = smoothstep(thr - 0.12, thr + 0.12, m * 1.15)
    a *= (0.72 + 0.28 * fbm(h, w, 9, 2, rng))
    if extra is not None:
        a = np.maximum(a, extra)
    rgb = CHALK[None, None, :] * (0.92 + 0.08 * g1)[..., None]
    return np.dstack([rgb, np.clip(a, 0, 1)[..., None]])


def poly_stroke(dr, pts, widths, fill=255):
    for i in range(len(pts) - 1):
        w = max(1, int(round(widths[i] if hasattr(widths, '__len__') else widths)))
        dr.line([pts[i], pts[i + 1]], fill=fill, width=w)
        r = w / 2.0
        dr.ellipse([pts[i + 1][0] - r, pts[i + 1][1] - r, pts[i + 1][0] + r, pts[i + 1][1] + r], fill=fill)


def wobble_curve(rng, n, amp, kmax=9, closed=True):
    """Smooth periodic wobble: sum of low harmonics."""
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    out = np.zeros(n)
    for k in range(2, kmax + 1):
        out += (amp / k) * np.sin(k * t + rng.uniform(0, 2 * math.pi)) * rng.uniform(0.5, 1.0)
    return out


# ---- invented glyph strokes (local frame: u across, v radial outward; units = cm, box about 10 x 14) ----
def arc_pts(cu, cv, r, a0, a1, n=18):
    return [(cu + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cv + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def spiral_pts(cu, cv, r_max, turns, rot, n=40):
    return [(cu + r_max * (i / n) * math.cos(rot + 2 * math.pi * turns * i / n), cv + r_max * (i / n) * math.sin(rot + 2 * math.pi * turns * i / n)) for i in range(n + 1)]


def wave_pts(u0, v0, u1, v1, amp, periods, n=24):
    dx, dy = u1 - u0, v1 - v0
    ln = math.hypot(dx, dy)
    nx, ny = -dy / ln, dx / ln
    return [(u0 + dx * t + nx * amp * math.sin(2 * math.pi * periods * t), v0 + dy * t + ny * amp * math.sin(2 * math.pi * periods * t)) for t in [i / n for i in range(n + 1)]]


def glyph_strokes(rng):
    """3 invented marks stacked along the radial direction; returns a list of polylines (list of (u, v))."""
    kinds = ['arc', 'hook', 'spiral', 'wave', 'ticks', 'loop', 'curl']
    strokes = []
    last = None
    for slot, vc in enumerate((-4.6, 0.0, 4.6)):
        k = rng.choice([x for x in kinds if x != last])
        last = k
        uc = rng.uniform(-1.2, 1.2)
        s = rng.uniform(0.75, 1.0)
        if k == 'arc':
            a0 = rng.uniform(0, 360)
            strokes.append(arc_pts(uc, vc, 3.0 * s, a0, a0 + rng.uniform(120, 220)))
        elif k == 'hook':
            a0 = rng.uniform(0, 360)
            pts = arc_pts(uc, vc, 2.4 * s, a0, a0 + 250)
            x, y = pts[-1]
            strokes.append(pts + [(x + 1.2 * math.cos(math.radians(a0 + 250 + 70)), y + 1.2 * math.sin(math.radians(a0 + 250 + 70))),
                                  (x + 3.0 * math.cos(math.radians(a0 + 250 + 70)), y + 3.0 * math.sin(math.radians(a0 + 250 + 70)))])
        elif k == 'spiral':
            strokes.append(spiral_pts(uc, vc, 2.9 * s, rng.uniform(1.2, 1.8), rng.uniform(0, 6.28)))
        elif k == 'wave':
            ang = rng.uniform(-30, 30)
            c, sn = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            strokes.append(wave_pts(uc - 4.2 * c, vc - 4.2 * sn, uc + 4.2 * c, vc + 4.2 * sn, 1.1 * s, rng.choice((1.5, 2.0, 2.5))))
        elif k == 'ticks':
            ang = math.radians(rng.choice((-1, 1)) * rng.uniform(28, 62))
            for j in range(rng.choice((2, 3, 3))):
                cu = uc + (j - 1) * 1.9
                strokes.append([(cu - 1.8 * math.sin(ang), vc - 1.8 * math.cos(ang)), (cu + 1.8 * math.sin(ang), vc + 1.8 * math.cos(ang))])
        elif k == 'loop':
            strokes.append(arc_pts(uc, vc + 0.8, 1.7 * s, 0, 360, 22))
            strokes.append([(uc + rng.uniform(-0.4, 0.4), vc - 0.9), (uc + rng.uniform(-1.5, 1.5), vc - 3.0)])
        else:  # curl: S shape
            strokes.append(arc_pts(uc - 1.4, vc + 1.4, 1.6 * s, 90, 270, 12) + arc_pts(uc + 1.4, vc - 1.4, 1.6 * s, 270, 450, 12)[1:])
    return strokes


def bell_strokes(h):
    """Scrawled bell outline (height h cm) with lip, clapper and handle loop, as polylines in cm; origin = centre of the lip."""
    prof = [(1.0, 0.0), (0.96, 0.06), (0.82, 0.14), (0.64, 0.26), (0.58, 0.45), (0.5, 0.62), (0.36, 0.8), (0.16, 0.94), (0.0, 1.0)]
    w = h * 0.36
    right = [(w * px_, h * py_) for px_, py_ in prof]
    left = [(-w * px_, h * py_) for px_, py_ in prof][::-1]
    out = [left + right]                                                                 # apex -> left lip -> (lip line) -> right lip -> apex
    out.append([(-w * 0.92, h * 0.1), (w * 0.92, h * 0.1)])                             # lip band
    out.append(arc_pts(0.0, -h * 0.1, h * 0.07, 0, 360, 16))                            # clapper
    out.append(arc_pts(0.0, h * 1.05, h * 0.08, 0, 360, 16))                            # handle loop
    out.append([(-w * 0.3, h * 0.62), (-w * 0.22, h * 0.3)])                              # two thin scratches on the body
    out.append([(-w * 0.12, h * 0.66), (-w * 0.04, h * 0.32)])
    return out


def draw_cm_strokes(dr, strokes, to_px, width_px, rng, jitter_cm=0.25, double=True):
    for st in strokes:
        pts = []
        for (u, v) in st:
            pts.append(to_px(u + rng.normal(0, jitter_cm * 0.3), v + rng.normal(0, jitter_cm * 0.3)))
        wv = [width_px * (0.8 + 0.4 * rng.random()) for _ in range(len(pts))]
        poly_stroke(dr, pts, wv)
        if double and rng.random() < 0.55:                                               # chalk re-trace
            pts2 = [(x + rng.normal(0, 2.0), y + rng.normal(0, 2.0)) for (x, y) in pts]
            poly_stroke(dr, pts2, [0.55 * width_px] * len(pts2))


def chalk_circle_texture(seed):
    rng = np.random.default_rng(seed)
    SS = 2
    N = 2048 * SS
    cpx = 2048.0 / 320.0 * SS                                  # px per cm (supersampled)
    cxy = N / 2.0
    mask = Image.new('L', (N, N), 0)
    dr = ImageDraw.Draw(mask)
    # rings: O300 and O250, 3-5 cm line, hand wobble, an overshoot where the stroke closes, a thinner re-trace on part of the circle
    for (rcm, wcm) in ((150.0, 4.2), (125.0, 4.0)):
        for pas in range(2):
            n = 900
            t = np.linspace(0, 2 * math.pi * 1.04, n)
            wob = wobble_curve(rng, n, 3.4)
            wob = np.interp(t, np.linspace(0, 2 * math.pi, n, endpoint=False), wob, period=2 * math.pi)
            drift = np.clip((t - 2 * math.pi) / 0.26, 0, 1) * rng.choice((-1.1, 1.1)) if pas == 0 else 0.0
            r_cm = rcm + wob + drift + (0.0 if pas == 0 else rng.uniform(-0.8, 0.8))
            wid = wcm * (1.0 + 0.28 * np.sin(3 * t + rng.uniform(0, 6)) + 0.15 * np.sin(7 * t + rng.uniform(0, 6)))
            if pas == 1:
                a0 = rng.uniform(0, 2 * math.pi)
                keep = (np.cos(t - a0) > -0.2)
                wid = wid * 0.55
            else:
                keep = np.ones(n, bool)
            pts = [(cxy + r * cpx * math.cos(a), cxy - r * cpx * math.sin(a)) for r, a in zip(r_cm, t)]
            for i in range(n - 1):
                if keep[i] and keep[i + 1]:
                    w = max(2, int(wid[i] * cpx))
                    dr.line([pts[i], pts[i + 1]], fill=255, width=w)
                    rr_ = w / 2.0
                    dr.ellipse([pts[i + 1][0] - rr_, pts[i + 1][1] - rr_, pts[i + 1][0] + rr_, pts[i + 1][1] + rr_], fill=255)
    # 12 invented glyphs between the rings (centre radius 137 cm), up = outward
    for g in range(12):
        ang = math.radians(15.0 + 30.0 * g + rng.uniform(-3, 3))
        rad = 137.5 + rng.uniform(-1.0, 1.0)
        c, s = math.cos(ang), math.sin(ang)
        strokes = glyph_strokes(rng)
        gscale = rng.uniform(1.2, 1.4)

        def to_px(u, v, c=c, s=s, rad=rad, gscale=gscale):
            rr_ = rad + v * gscale
            tt = u * gscale
            # tangent = (-s, c) ; radial = (c, s)
            x = rr_ * c - tt * s
            y = rr_ * s + tt * c
            return (cxy + x * cpx, cxy - y * cpx)

        draw_cm_strokes(dr, strokes, to_px, 1.5 * cpx, rng)
    # centre bell (55 cm)
    bell = bell_strokes(55.0)
    draw_cm_strokes(dr, bell, lambda u, v: (cxy + u * cpx, cxy - (v - 27.0) * cpx), 3.4 * cpx, rng, 0.35)
    # a few stray scribbles near the bell (wobbly ticks)
    for k in range(5):
        a0 = rng.uniform(0, 2 * math.pi)
        r0 = rng.uniform(40, 70)
        pts = [(cxy + (r0 + 6 * j) * cpx * math.cos(a0 + 0.06 * j), cxy - (r0 + 6 * j) * cpx * math.sin(a0 + 0.06 * j)) for j in range(3)]
        poly_stroke(dr, pts, [2.0 * cpx] * 3)
    # smudge trails (separate soft mask)
    sm = Image.new('L', (N, N), 0)
    sd = ImageDraw.Draw(sm)
    for (a0, drift) in ((rng.uniform(0.4, 1.2), 0.5), (rng.uniform(3.6, 4.6), -0.45)):
        pts = []
        for j in range(30):
            tt = j / 29.0
            r = 128.0 - 78.0 * tt
            a = a0 + drift * tt + 0.08 * math.sin(tt * 9)
            pts.append((cxy + r * cpx * math.cos(a), cxy - r * cpx * math.sin(a)))
        poly_stroke(sd, pts, [(9.0 - 4.0 * j / 29.0) * cpx for j in range(30)], fill=150)
    sm = sm.filter(ImageFilter.GaussianBlur(7 * cpx))
    smud = as_mask(sm.resize((2048, 2048), Image.BOX))
    out = chalk_rgba(mask, rng, (2048, 2048), SS, soft=1.3, extra=None)
    streaks = fbm(2048, 2048, 18, 3, rng)
    out[..., 3] = np.maximum(out[..., 3], np.clip(smud * 0.55 * (0.5 + streaks), 0, 0.5))
    # four scuffed gaps on the rings (angular erosion with ragged edges + a halo of rubbed chalk)
    ys, xs = np.mgrid[0:2048, 0:2048].astype(np.float32)
    px = 2048.0 / 320.0
    rad = np.hypot(xs - 1024.0, ys - 1024.0) / px
    ang = np.arctan2(-(ys - 1024.0), xs - 1024.0)
    rag = fbm(2048, 2048, 22, 3, rng)
    for (a0, which) in ((0.35, 'outer'), (2.0, 'inner'), (3.7, 'outer'), (5.2, 'both')):
        a0 += rng.uniform(-0.15, 0.15)
        hw = rng.uniform(0.06, 0.12)
        dang = np.abs(((ang - a0 + math.pi) % (2 * math.pi)) - math.pi)
        sel = np.zeros(rad.shape, bool)
        if which in ('outer', 'both'):
            sel |= np.abs(rad - 150.0) < 9.0
        if which in ('inner', 'both'):
            sel |= np.abs(rad - 125.0) < 9.0
        gap = (dang < hw * (0.55 + 0.9 * rag)) & sel
        rub = (dang < hw * 1.9 * (0.6 + rag)) & sel
        out[..., 3] = np.where(gap, 0.0, np.where(rub, out[..., 3] * (0.35 + 0.65 * rag), out[..., 3]))
    return out


def chalk_sigil_texture(seed):
    rng = np.random.default_rng(seed)
    SS = 2
    N = 512 * SS
    cpx = 512.0 / 80.0 * SS
    cxy = N / 2.0
    mask = Image.new('L', (N, N), 0)
    dr = ImageDraw.Draw(mask)
    n = 400
    t = np.linspace(0, 2 * math.pi * 1.05, n)
    wob = wobble_curve(rng, n, 1.8)
    wob = np.interp(t, np.linspace(0, 2 * math.pi, n, endpoint=False), wob, period=2 * math.pi)
    pts = [(cxy + (34.0 + w) * cpx * math.cos(a), cxy - (34.0 + w) * cpx * math.sin(a)) for w, a in zip(wob, t)]
    poly_stroke(dr, pts, [3.2 * cpx * (0.8 + 0.3 * math.sin(3 * a)) for a in t])
    # inner spiral (2.5 turns) around the bell, three curved sound arcs under it, 8 irregular ticks between the ring and the spiral
    sp = [(cxy + r * cpx * math.cos(a), cxy - r * cpx * math.sin(a)) for r, a in zip(np.linspace(8, 27, 120), np.linspace(0.3, 0.3 + 2 * math.pi * 2.5, 120))]
    poly_stroke(dr, sp, [2.1 * cpx] * len(sp))
    draw_cm_strokes(dr, bell_strokes(26.0), lambda u, v: (cxy + u * cpx, cxy - (v - 12.0) * cpx), 2.2 * cpx, rng, 0.3)
    for k in range(8):
        a = math.radians(45.0 * k + rng.uniform(-10, 10))
        r0, r1 = 29.0 + rng.uniform(0, 1.0), 32.5 + rng.uniform(-0.5, 0.8)
        poly_stroke(dr, [(cxy + r0 * cpx * math.cos(a), cxy - r0 * cpx * math.sin(a)), (cxy + r1 * cpx * math.cos(a + 0.05), cxy - r1 * cpx * math.sin(a + 0.05))], [1.8 * cpx] * 2)
    return chalk_rgba(mask, rng, (512, 512), SS, soft=1.1)


def chalk_tally_texture(seed):
    rng = np.random.default_rng(seed)
    SS = 2
    W, H = 512 * SS, 256 * SS
    mask = Image.new('L', (W, H), 0)
    dr = ImageDraw.Draw(mask)
    gw = 96.0 * SS
    x0 = 34.0 * SS
    for g in range(4):
        gx = x0 + g * (gw + 24.0 * SS)
        tilt = rng.uniform(-0.04, 0.04)
        for k in range(4):
            xx = gx + k * 18.0 * SS + rng.uniform(-2, 2) * SS
            ln = rng.uniform(150, 168) * SS
            top = (H - ln) / 2.0 + rng.uniform(-6, 6) * SS
            pts = [(xx + tilt * j * 5 * SS + rng.normal(0, 0.7 * SS), top + ln * j / 6.0) for j in range(7)]
            poly_stroke(dr, pts, [rng.uniform(8, 11) * SS] * 7)
            if rng.random() < 0.5:
                poly_stroke(dr, [(p[0] + 3 * SS, p[1]) for p in pts], [4 * SS] * 7)
        pts = [(gx - 12 * SS, H * 0.8 + rng.uniform(-4, 4) * SS), (gx + 36 * SS, H * 0.5), (gx + 84 * SS, H * 0.2 + rng.uniform(-4, 4) * SS)]
        poly_stroke(dr, pts, [rng.uniform(8, 11) * SS] * 3)
    return chalk_rgba(mask, rng, (512, 256), SS, soft=1.1)


# ----------------------------------------------------------------------------------------------
# cobweb
# ----------------------------------------------------------------------------------------------
def cobweb_texture(seed):
    rng = np.random.default_rng(seed)
    SS = 2
    N = 1024 * SS
    im = Image.new('L', (N, N), 0)
    dr = ImageDraw.Draw(im)
    cx, cy = N / 2 + rng.uniform(-40, 40), N / 2 + rng.uniform(-40, 40)
    ns = 19
    angs = np.sort(rng.uniform(0, 2 * math.pi, ns))
    angs = np.sort(2 * math.pi * (np.arange(ns) + rng.uniform(-0.3, 0.3, ns)) / ns)
    rmax = N * 0.72
    spokes = []
    for a in angs:
        rl = rmax * rng.uniform(0.85, 1.15)
        pts = [(cx + rl * t * math.cos(a) + rng.normal(0, 1.5), cy + rl * t * math.sin(a) + rng.normal(0, 1.5)) for t in np.linspace(0, 1, 12)]
        dr.line(pts, fill=int(255 * rng.uniform(0.75, 0.95)), width=int(3 * SS))
        spokes.append((a, rl))
    r = 70.0 * SS
    while r < N * 0.7:
        pts_r = []
        for i, (a, rl) in enumerate(spokes):
            rr = r * rng.uniform(0.93, 1.07)
            pts_r.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        for i in range(ns):
            if rng.random() < 0.10:
                continue                                              # torn gap
            p0, p1 = pts_r[i], pts_r[(i + 1) % ns]
            mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
            vx, vy = cx - mx, cy - my
            ln = math.hypot(vx, vy)
            sag = rng.uniform(0.04, 0.13) * math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            ctrl = (mx + vx / ln * sag * 2, my + vy / ln * sag * 2)
            curve = [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * ctrl[0] + t * t * p1[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * ctrl[1] + t * t * p1[1]) for t in np.linspace(0, 1, 9)]
            dr.line(curve, fill=int(255 * rng.uniform(0.35, 0.7)), width=int(rng.choice((1.5, 2.0, 2.5)) * SS))
        r += rng.uniform(34, 62) * SS * (1.0 + r / (N * 1.2))
    for k in range(7):                                                # stray anchor threads
        a = rng.uniform(0, 2 * math.pi)
        x0, y0 = N / 2 + rng.uniform(-300, 300), N / 2 + rng.uniform(-300, 300)
        dr.line([(x0, y0), (x0 + math.cos(a) * rng.uniform(300, 800), y0 + math.sin(a) * rng.uniform(300, 800))], fill=int(255 * rng.uniform(0.2, 0.4)), width=int(1.5 * SS))
    a = as_mask(im.resize((1024, 1024), Image.BOX))
    a = np.clip(a * 1.1, 0, 1)
    soft = fbm(1024, 1024, 90, 3, rng)
    a = a * (0.65 + 0.5 * soft)
    rgb = np.dstack([np.full((1024, 1024), 0.82, np.float32), np.full((1024, 1024), 0.82, np.float32), np.full((1024, 1024), 0.80, np.float32)])
    return np.dstack([rgb, np.clip(a, 0, 1)[..., None]])


# ----------------------------------------------------------------------------------------------
# roof slates: crop the ridge strip, keep whole courses, make the vertical wrap continuous
# ----------------------------------------------------------------------------------------------
def load_src(name):
    p = os.path.join(ROOT, "ExternalAssets", "Incoming", "polyhaven-roof_slates_03", "roof_slates_03_%s_2k.jpg" % name)
    return np.asarray(Image.open(p).convert('RGB'), np.float32) / 255.0


def slate_course_period(lum):
    """Course period (px) from the autocorrelation of the horizontal-edge profile below the ridge strip."""
    gy = np.abs(np.diff(lum, axis=0)).mean(axis=1)
    g = gy[220:]
    g = g - g.mean()
    n = len(g)
    f = np.fft.rfft(g, 2 * n)
    ac = np.fft.irfft(f * np.conj(f))[:n]
    lo, hi = 40, 100
    k = lo + int(np.argmax(ac[lo:hi]))
    # refine with a parabola
    y0, y1, y2 = ac[k - 1], ac[k], ac[k + 1]
    return k + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)


def slates_textures(seed, out_dir, prev_dir):
    rng = np.random.default_rng(seed)
    diff = load_src("diff")
    nor = load_src("nor_dx")
    rough = load_src("rough")
    arm = load_src("arm")            # the supplied rough map is a constant 1.0; the ARM map (R AO, G rough, B metal) carries the real variation: cropped too
    lum = diff.mean(axis=2)
    P = slate_course_period(lum)
    print("slate course period: %.2f px" % P)
    # ridge strip + the first partly covered course end near row ~165; start the crop on the first full course boundary after 170
    gy = np.abs(np.diff(lum, axis=0)).mean(axis=1)
    k_courses = 16
    Hc = int(round(k_courses * P))
    B = 24                                                    # cross-fade rows at the wrap
    best = None
    for r0 in range(170, 2048 - Hc - B - 1):
        # the wrap row must look like a normal next row: compare against rows that follow the same phase
        cost = np.abs(lum[r0 + Hc] - lum[r0]).mean() + 4.0 * abs(gy[r0 + Hc - 1] - gy[r0 - 1])
        if best is None or cost < best[0]:
            best = (cost, r0)
    r0 = best[1]
    print("slate crop rows %d..%d (courses %d, period %.2f), wrap cost %.4f" % (r0, r0 + Hc, k_courses, P, best[0]))
    res = {}
    for name, src in (("diff", diff), ("nor_dx", nor), ("rough", rough), ("arm", arm)):
        crop = src[r0:r0 + Hc].copy()
        tail = src[r0 + Hc:r0 + Hc + B]
        head = src[r0:r0 + B]
        w = np.linspace(0.0, 1.0, B)[:, None, None]
        crop[:B] = tail * (1 - w) + head * w                  # y=0 equals the true next row after the crop end, fading into the crop start
        if name == "nor_dx":
            v = crop * 2 - 1
            ln = np.sqrt((v ** 2).sum(axis=2, keepdims=True))
            crop = (v / np.maximum(ln, 1e-6)) * 0.5 + 0.5
        im = Image.fromarray((np.clip(crop, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((2048, 1024), Image.LANCZOS)
        res[name] = im
        im.save(os.path.join(out_dir, "T_LB_RoofSlates_%s.png" % name))
    # preview: 2x2 tile at 50 % + a 100 % seam strip across the wrap
    d = res["diff"]
    tile = Image.new('RGB', (4096, 2048))
    for ix in range(2):
        for iy in range(2):
            tile.paste(d, (ix * 2048, iy * 1024))
    tile.resize((2048, 1024), Image.LANCZOS).save(os.path.join(prev_dir, "tex_roofslates_tile.png"))
    tile.crop((1024, 1024 - 256, 1024 + 2048, 1024 + 256)).save(os.path.join(prev_dir, "tex_roofslates_seam.png"))
    nt = Image.new('RGB', (4096, 2048))
    for ix in range(2):
        for iy in range(2):
            nt.paste(res["nor_dx"], (ix * 2048, iy * 1024))
    nt.crop((1024, 1024 - 256, 1024 + 2048, 1024 + 256)).save(os.path.join(prev_dir, "tex_roofslates_nor_seam.png"))
    print("slates: course period %.2f px, crop %d rows -> 2048x1024 (%d courses x 20.x slates wide)" % (P, Hc, k_courses))


# ----------------------------------------------------------------------------------------------
# grime decals (P8-10a): soot, mould band, water stain, wax, drag marks, leaf litter, dust drift
# ----------------------------------------------------------------------------------------------
def rgba_const(rgb, a, jitter=None):
    """RGBA with a (nearly) constant colour everywhere (so mips never bleed a wrong colour) and the given alpha."""
    col = np.zeros(a.shape + (3,), np.float32) + np.asarray(rgb, np.float32)
    if jitter is not None:
        col = col * (1.0 + jitter)[..., None]
    return np.dstack([np.clip(col, 0, 1), np.clip(a, 0, 1)[..., None]]).astype(np.float32)


def soot_texture(seed, lean, width):
    """512 x 1024 sooty plume above a flame: dense at the bottom (alpha 0.85), widening and thinning upward with billowing turbulent edges,
    vertical deposit streaks and a fuzzy fringe.  lean = sideways drift of the plume centre (fraction of the width), width = plume width factor."""
    rng = np.random.default_rng(seed)
    W, H = 512, 1024
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    t = 1.0 - (ys + 0.5) / H                                   # 0 bottom -> 1 top
    u = (xs + 0.5) / W
    wx = (fbm(H, W, 170, 4, rng) - 0.5) * 2.0                  # turbulence grows with height (laminar at the flame, billowing higher up)
    turb = fbm(H, W, 90, 4, rng)
    sway = (vnoise(1, H, 2, 300, rng)[0] - 0.5) * 2.0
    cx = 0.5 + lean * t ** 1.2 + 0.06 * sway[:, None] * t
    hw = (0.075 + 0.27 * t ** 0.55) * width
    q = (u - cx + 0.13 * wx * t ** 0.7) / hw
    prof = np.exp(-q * q * 1.5)
    streak = vnoise(H, W, 340, 9, rng)                         # tall thin deposit streaks
    fine = vnoise(H, W, 3, 3, rng)
    f = prof * np.exp(-t * 2.1) * (0.50 + 0.95 * turb) * (0.78 + 0.45 * streak)
    a = 0.85 * np.clip(f * 1.55, 0, 1) ** 0.95
    a = a * (0.80 + 0.40 * fine) * (1 - smoothstep(0.80, 1.0, t))
    a = a * np.clip(np.minimum(u, 1 - u) / 0.05, 0, 1)
    return rgba_const((0.02, 0.02, 0.02), np.clip(a, 0, 0.85), (fine - 0.5) * 0.5)


def mould_band_texture(seed):
    """1024 x 256 rising-damp band: dark green-black at the bottom, wavering soft top edge with broad wicking bulges, blotchy alpha 0.4-0.8,
    clusters of darker mould and a speckle of spores above the tide line."""
    rng = np.random.default_rng(seed)
    W, H = 1024, 256
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    hgt = (H - (ys + 0.5))                                      # px above the bottom edge
    e1 = vnoise(1, W, 2, 170, rng)[0]
    e2 = vnoise(1, W, 2, 45, rng)[0]
    e3 = vnoise(1, W, 2, 11, rng)[0]
    edge = H * (0.50 + 0.26 * (e1 - 0.5) * 2 + 0.10 * (e2 - 0.5) * 2 + 0.025 * (e3 - 0.5) * 2)
    wick = vnoise(1, W, 2, 50, rng)[0]                           # broad bulges where damp wicks higher
    edge = edge + 26.0 * smoothstep(0.5, 1.0, wick) ** 1.5
    below = edge[None, :] - hgt                                  # > 0 inside the band
    blot = fbm(H, W, 80, 4, rng)
    bandw = 30.0 + 40.0 * fbm(H, W, 110, 2, rng)                # a wide, uneven fade: damp thins out upward
    inside = smoothstep(-0.15, 1.0, below / bandw) ** 1.3
    dens = 0.50 + 0.30 * (blot - 0.5) * 2.0
    dens = dens + 0.22 * (1 - smoothstep(0, 70.0, hgt))          # darker toward the ground
    clusters = smoothstep(0.52, 0.80, fbm(H, W, 34, 3, rng))     # darker mould clusters
    dens = dens + 0.25 * clusters
    dens = dens * (0.86 + 0.28 * vnoise(H, W, 140, 8, rng))     # faint vertical streaks
    a = inside * dens
    above = np.clip(-below, 0, None)                              # spores above the tide line, thinning with height
    sp = rng.random((H, W)).astype(np.float32)
    spk = (sp > 0.955 - 0.045 * np.exp(-above / 22.0)) & (above < 70) & (blot > 0.45)
    spk_a = Image.fromarray((spk * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.9))
    a = np.maximum(a, as_mask(spk_a) * 1.6 * (0.6 + 0.4 * blot))
    a = a * np.clip(np.minimum(xs, W - xs) / 24.0, 0, 1)         # fade the ends so adjacent decals blend
    a = np.clip(a, 0, 0.8)
    g = fbm(H, W, 40, 3, rng)
    col = np.zeros((H, W, 3), np.float32)
    col[..., 0] = 0.040 + 0.020 * g
    col[..., 1] = 0.052 + 0.024 * g
    col[..., 2] = 0.032 + 0.014 * g
    return np.dstack([col, a[..., None]]).astype(np.float32)


def water_stain_texture(seed):
    """1024^2 stain: irregular, darker brown at the margin (0.10, 0.08, 0.06) and lighter toward the centre, three tide-mark rings (sharp outer
    edge, soft feathering inward, broken here and there), alpha 0.3-0.7."""
    rng = np.random.default_rng(seed)
    N = 1024
    ys, xs = np.mgrid[0:N, 0:N].astype(np.float32)
    px, py = (xs + 0.5 - N / 2) / (N / 2), (ys + 0.5 - N / 2) / (N / 2)
    wx = (fbm(N, N, 180, 4, rng) - 0.5) * 0.30
    wy = (fbm(N, N, 180, 4, rng) - 0.5) * 0.30
    qx, qy = px + wx, py * 1.10 + wy
    d = np.hypot(qx, qy)
    th = np.arctan2(qy, qx)

    def radius(r0, amp, seed_off):
        r = np.random.default_rng(seed + seed_off)
        out = np.zeros_like(th) + r0
        for k in range(2, 8):
            out += (amp / k) * np.sin(k * th + r.uniform(0, 6.283)) * r.uniform(0.5, 1.0)
        return out

    ring_r = [radius(0.40, 0.14, 11), radius(0.60, 0.15, 12), radius(0.78, 0.13, 13)]
    outer = ring_r[-1] + 0.05
    inside = smoothstep(1.0, 0.0, (d - outer) / 0.035)
    inside = inside * (1 - 0.35 * fbm(N, N, 14, 3, rng) * smoothstep(0.7, 1.15, d / np.maximum(outer, 0.2)))   # ragged feathered margin
    s = np.clip(d / np.maximum(outer, 0.2), 0, 1.2)
    zone = sum(smoothstep(-0.012, 0.012, d - rr) for rr in ring_r)     # 0 in the centre .. 2 past the middle ring: each tide zone a step darker
    a = (0.20 + 0.075 * zone + 0.06 * smoothstep(0.3, 1.0, s)) * inside
    brk = fbm(N, N, 90, 3, rng)
    for k, rr in enumerate(ring_r):                               # tide marks: sharp outer edge, feathered inward, broken in places
        dd = d - rr
        band = smoothstep(0.007, -0.003, dd) * smoothstep(-0.055 - 0.02 * k, 0.0, dd) ** 1.5
        gap = smoothstep(0.38, 0.55, brk + 0.04 * k)
        a = np.maximum(a, band * gap * (0.60 + 0.07 * k) * (0.75 + 0.45 * fbm(N, N, 18, 3, rng)))
    a = a * (0.88 + 0.24 * fbm(N, N, 40, 3, rng))
    a = np.clip(a, 0.0, 0.7)
    a = a * (a > 0.012)
    tone = np.clip(s, 0, 1)
    light = np.array((0.19, 0.155, 0.115), np.float32)
    dark = np.array((0.10, 0.08, 0.06), np.float32)
    col = light[None, None, :] * (1 - tone[..., None]) + dark[None, None, :] * tone[..., None]
    for rr in ring_r:                                             # the tide marks are the darkest tone
        col = col * (1.0 - 0.22 * np.exp(-((d - rr) / 0.02) ** 2)[..., None])
    col = col * (0.92 + 0.16 * fbm(N, N, 30, 3, rng))[..., None]
    return np.dstack([np.clip(col, 0, 1), a[..., None]]).astype(np.float32)


def wax_texture(seed):
    """512^2: 6 creamy wax splats, each an irregular pool with run-drip fingers (rounded bulb ends) and satellite droplets, bevel-shaded."""
    rng = np.random.default_rng(seed)
    SS = 2
    N = 512 * SS
    mask = Image.new('L', (N, N), 0)
    dr = ImageDraw.Draw(mask)
    centres = []
    tries = 0
    while len(centres) < 6 and tries < 500:
        tries += 1
        c = (rng.uniform(80, 432), rng.uniform(80, 432))
        if all(math.hypot(c[0] - o[0], c[1] - o[1]) > 120 for o in centres):
            centres.append(c)
    for (cx, cy) in centres:
        cx, cy = cx * SS, cy * SS
        R = rng.uniform(14, 42) * SS
        n = 64
        th = np.linspace(0, 2 * math.pi, n, endpoint=False)
        r = np.full(n, R)
        for k in range(2, 6):
            r = r + (R * 0.34 / k) * np.sin(k * th + rng.uniform(0, 6.283))
        dr.polygon([(cx + ri * math.cos(a), cy + ri * math.sin(a)) for ri, a in zip(r, th)], fill=255)
        for _ in range(int(rng.choice((0, 1, 1, 2, 3)))):          # run-drips: wavering rivulets that taper, sometimes ending in a small bead
            ang = math.radians(90 + rng.uniform(-75, 75))
            ln = R * rng.uniform(1.0, 3.0)
            w0 = R * rng.uniform(0.18, 0.40)
            wob = rng.uniform(0, 6.28)
            for i in range(41):
                tt = i / 40.0
                lat = 0.10 * R * math.sin(wob + tt * 5.0)
                p = (cx + math.cos(ang) * (R * 0.45 + ln * tt) - math.sin(ang) * lat, cy + math.sin(ang) * (R * 0.45 + ln * tt) + math.cos(ang) * lat)
                wd = w0 * (1.0 - 0.75 * tt) * (0.85 + 0.3 * math.sin(tt * 9 + wob))
                if rng.random() < 0.5:
                    wd += w0 * 0.30 * math.exp(-((tt - 1.0) / 0.07) ** 2)
                wd = max(wd, 0.9 * SS)
                dr.ellipse([p[0] - wd, p[1] - wd, p[0] + wd, p[1] + wd], fill=255)
        for _ in range(int(rng.integers(3, 8))):                   # satellite droplets
            a = rng.uniform(0, 2 * math.pi)
            rd = R * rng.uniform(1.3, 2.4)
            rr = R * rng.uniform(0.07, 0.2)
            x, y = cx + rd * math.cos(a), cy + rd * math.sin(a)
            dr.ellipse([x - rr, y - rr, x + rr, y + rr], fill=255)
    m = as_mask(mask.filter(ImageFilter.GaussianBlur(1.2 * SS)).resize((512, 512), Image.BOX))
    hmap = as_mask(mask.filter(ImageFilter.GaussianBlur(5.0 * SS)).resize((512, 512), Image.BOX))
    gy, gx = np.gradient(hmap)
    light = np.clip(0.5 - (gx * 9.0 + gy * 9.0) * 1.3, 0, 1)           # light from the upper left
    rim = np.clip((m - hmap) * 2.2 + 0.15, 0, 1)
    n1 = fbm(512, 512, 24, 3, rng)
    base = np.array((0.80, 0.74, 0.60), np.float32)
    col = base[None, None, :] * (0.78 + 0.45 * light + 0.12 * (n1 - 0.5))[..., None]
    col = col * (1.0 - 0.12 * rim[..., None])
    return np.dstack([np.clip(col, 0, 1), np.clip(m * 0.9, 0, 0.9)[..., None]]).astype(np.float32)


def boot_sole_polys(length=30.0, side=1):
    """Invented boot-sole print facing +x (toe), local cm, origin = middle.  Returns (heel polygon, sole polygon, tread-notch polygons).
    side = +1 left, -1 right (mirrors y)."""
    x0 = -length / 2
    heel = [(x0, -3.6), (x0 + 1.5, -4.2), (x0 + 7.0, -4.0), (x0 + 7.4, 0.0), (x0 + 7.0, 4.0), (x0 + 1.5, 4.2), (x0, 3.6)]
    sole = [(x0 + 10.0, -3.4), (x0 + 15.0, -3.9), (x0 + 20.0, -5.2), (x0 + 25.0, -5.6), (x0 + 28.0, -4.2), (x0 + 30.0, -1.6), (x0 + 30.2, 0.8),
            (x0 + 28.6, 3.8), (x0 + 25.0, 5.6), (x0 + 20.0, 5.4), (x0 + 15.0, 4.2), (x0 + 10.0, 3.4)]
    notch = []
    for xn in (14.5, 17.5, 20.5, 23.5, 26.5):                              # tread bars cut across the sole
        notch.append([(x0 + xn, -4.2), (x0 + xn + 1.1, -4.4), (x0 + xn + 1.0, -0.8), (x0 + xn - 0.1, -0.8)])
        notch.append([(x0 + xn, 0.8), (x0 + xn + 1.1, 0.8), (x0 + xn + 1.1, 4.4), (x0 + xn, 4.2)])
    for xn in (2.2, 5.0):                                                  # heel tread
        notch.append([(x0 + xn, -3.0), (x0 + xn + 1.0, -3.0), (x0 + xn + 1.0, 3.0), (x0 + xn, 3.0)])
    if side < 0:
        heel = [(x, -y) for x, y in heel]
        sole = [(x, -y) for x, y in sole]
        notch = [[(x, -y) for x, y in nn] for nn in notch]
    return heel, sole, notch


def drag_marks_texture(seed):
    """1024 x 512.  Authored on a 2560 x 512 logical canvas (600 x 120 cm decal = half extents 300 x 60, 4.27 px/cm) and squeezed 2.5x in u, so the
    decal (texture u along the 600 cm axis) reproduces the real shapes: two parallel scuffed drag trails plus invented boot-sole prints."""
    rng = np.random.default_rng(seed)
    LW, LH = 2560, 512
    pxcm = 2560.0 / 600.0
    ys, xs = np.mgrid[0:LH, 0:LW].astype(np.float32)
    uc = (xs + 0.5) / pxcm                                                  # cm along the trail 0..600
    vc = (ys + 0.5) / pxcm - 60.0                                           # cm across -60..60
    alpha = np.zeros((LH, LW), np.float32)
    shared = (vnoise(1, LW, 2, 700, rng)[0] - 0.5) * 2.0 * 6.0              # both trails wander together
    for v0 in (-17.0, 17.0):
        own = (vnoise(1, LW, 2, 380, rng)[0] - 0.5) * 2.0 * 2.5
        centre = v0 + shared + own
        hw = 6.2 + 1.8 * (vnoise(1, LW, 2, 300, rng)[0] - 0.5) * 2.0
        dv = (vc - centre[None, :]) / hw[None, :]
        rag = fbm(LH, LW, 40, 3, rng)
        rag_l = vnoise(LH, LW, 8, 140, rng)                                   # streaks stretched along the trail
        edge = np.abs(dv) + 0.45 * (rag - 0.5) + 0.30 * (rag_l - 0.5)
        band = smoothstep(1.05, 0.55, edge)
        contact = smoothstep(0.12, 0.35, vnoise(1, LW, 2, 260, rng)[0])[None, :]     # the drag lifts now and then
        grain = 0.55 + 0.7 * vnoise(LH, LW, 3, 22, rng)
        a = band * (0.35 + 0.65 * contact) * grain * (0.75 + 0.45 * vnoise(LH, LW, 6, 90, rng))
        alpha = np.maximum(alpha, a)
        cl = (rng.random((LH, LW)) > 0.9992)                                  # flicked dirt clumps near the trail
        cl_img = Image.fromarray((cl * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(2.0))
        alpha = np.maximum(alpha, as_mask(cl_img) * np.exp(-(((vc - centre[None, :]) / 11.0) ** 2)) * 0.9)
    prints = []
    u, side = 28.0, 1
    while u < 585:
        prints.append((u + rng.uniform(-3, 3), side * rng.uniform(33, 40) + rng.uniform(-4, 4), side, rng.uniform(-9, 9) + side * 4.0, 1.0))
        u += rng.uniform(48, 58)
        side = -side
    for (pu, pv, sd) in ((rng.uniform(200, 260), -46.0, 1), (rng.uniform(300, 380), 47.0, -1), (rng.uniform(430, 500), -44.0, 1)):   # a few going back, lighter
        prints.append((pu, pv, sd, 180 + rng.uniform(-10, 10), 0.6))
    layer = np.zeros((LH, LW), np.float32)
    for (pu, pv, sd, yaw, pr) in prints:
        sm = Image.new('L', (LW, LH), 0)
        sdr = ImageDraw.Draw(sm)
        heel, sole, notch = boot_sole_polys(30.0, sd)
        ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        tp = lambda pts: [((pu + x * ca - y * sa) * pxcm, (pv + 60.0 + x * sa + y * ca) * pxcm) for x, y in pts]
        sdr.polygon(tp(heel), fill=255)
        sdr.polygon(tp(sole), fill=255)
        for nt in notch:
            sdr.polygon(tp(nt), fill=0)
        pm_ = as_mask(sm.filter(ImageFilter.GaussianBlur(1.6)))
        press = 0.75 + 0.5 * vnoise(LH, LW, 30, 30, rng)                      # uneven pressure, wiped / lifted parts, grit
        wipe = smoothstep(0.05, 0.4, vnoise(LH, LW, 90, 90, rng) + rng.uniform(-0.1, 0.15))
        gr = 0.65 + 0.5 * rng.random((LH, LW)).astype(np.float32)
        layer = np.maximum(layer, pm_ * press * wipe * gr * pr)
    alpha = np.maximum(alpha, np.clip(layer * 1.5, 0, 1))
    alpha = np.maximum(alpha, np.exp(-(((uc - 14.0) / 22.0) ** 2 + ((vc - 1.0) / 20.0) ** 2)) * 0.9 * (0.5 + 0.7 * fbm(LH, LW, 24, 3, rng)))   # smear where the load dropped
    alpha = np.clip(alpha, 0, 1) * 0.5
    alpha = alpha * np.clip(np.minimum(uc, 600 - uc) / 18.0, 0, 1) * np.clip((60.0 - np.abs(vc)) / 6.0, 0, 1)
    a = np.asarray(Image.fromarray(alpha, mode='F').resize((1024, 512), Image.BOX), np.float32)
    return rgba_const((0.12, 0.10, 0.08), a, (fbm(512, 1024, 20, 3, rng) - 0.5) * 0.3)


def find_leaf_cells(opacity):
    """Connected components of the leaf-atlas opacity map: 8-connected labelling on a 1/4-res mask opened (eroded) so the thin petioles that
    touch neighbouring leaves are removed, then every label grown back into the opaque area.  Returns ([(x0, y0, x1, y1, id)], full-res id map)."""
    m = Image.fromarray((opacity > 0.5).astype(np.uint8) * 255)
    quarter = m.resize((512, 512), Image.BOX)
    small = quarter.point(lambda v: 255 if v > 100 else 0).filter(ImageFilter.MinFilter(5))
    a = np.asarray(small) > 0
    lab = np.zeros(a.shape, np.int32)
    n = 0
    for y in range(a.shape[0]):
        for x in range(a.shape[1]):
            if a[y, x] and not lab[y, x]:
                n += 1
                lab[y, x] = n
                st = [(y, x)]
                while st:
                    cy, cx = st.pop()
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < 512 and 0 <= nx < 512 and a[ny, nx] and not lab[ny, nx]:
                                lab[ny, nx] = n
                                st.append((ny, nx))
    sm_op = np.asarray(quarter) > 20
    grown = lab.copy()
    for _ in range(14):                                                       # grow labels back into the opaque area
        nb = np.zeros_like(grown)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sh = np.roll(np.roll(grown, dy, 0), dx, 1)
            nb = np.where((nb == 0) & (sh > 0), sh, nb)
        grown = np.where((grown == 0) & (nb > 0) & sm_op, nb, grown)
    full = np.repeat(np.repeat(grown, 4, axis=0), 4, axis=1)
    cells = []
    for i in range(1, n + 1):
        ys, xs = np.where(grown == i)
        if len(ys) < 150:
            continue
        cells.append((int(xs.min()) * 4, int(ys.min()) * 4, int(xs.max()) * 4 + 4, int(ys.max()) * 4 + 4, i))
    cells.sort(key=lambda c: (c[1] // 400, c[0]))
    return cells, full


_LEAVES = {}


def load_leaves():
    """Cut every leaf out of the LeafSet030 atlas (Color + Opacity): list of RGBA float32 crops."""
    if 'v' in _LEAVES:
        return _LEAVES['v']
    base = os.path.join(ROOT, "ExternalAssets", "Incoming", "ambientcg-LeafSet030", "LeafSet030_2K-JPG", "LeafSet030_2K-JPG_")
    col = np.asarray(Image.open(base + "Color.jpg").convert('RGB'), np.float32) / 255.0
    op = np.asarray(Image.open(base + "Opacity.jpg").convert('L'), np.float32) / 255.0
    cells, full = find_leaf_cells(op)
    out = []
    for (x0, y0, x1, y1, lid) in cells:
        x0, y0, x1, y1 = max(0, x0 - 8), max(0, y0 - 8), min(2048, x1 + 8), min(2048, y1 + 8)
        mk = Image.fromarray(((full[y0:y1, x0:x1] == lid) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(15))
        a = op[y0:y1, x0:x1] * as_mask(mk)
        a = as_mask(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8)))
        out.append(np.dstack([col[y0:y1, x0:x1], a[..., None]]).astype(np.float32))
    _LEAVES['v'] = out
    return out


def leaf_litter_texture(seed, n_leaves, spread):
    """1024^2 scatter of dead oak leaves from LeafSet030 cells: random rotation, scale 0.6-1.2 of a 100 px base length, darkened x0.7, clumped
    into drifts, a faint contact shadow under each leaf, some leaves broken / partly buried."""
    rng = np.random.default_rng(seed)
    leaves = load_leaves()
    SS = 2
    N = 1024 * SS
    canvas = np.zeros((N, N, 4), np.float32)                                  # premultiplied
    shadow = np.zeros((N, N), np.float32)
    clumps = [(rng.uniform(250, 770), rng.uniform(250, 770), rng.uniform(150, 260) * spread) for _ in range(5)]
    items = []
    attempts = 0
    while len(items) < n_leaves and attempts < 4000:
        attempts += 1
        if rng.random() < 0.8:
            c = clumps[int(rng.integers(0, len(clumps)))]
            x, y = rng.normal(c[0], c[2]), rng.normal(c[1], c[2])
        else:
            x, y = rng.uniform(40, 984), rng.uniform(40, 984)
        if not (30 < x < 994 and 30 < y < 994):
            continue
        if rng.random() > smoothstep(30, 190, min(x, y, 1024 - x, 1024 - y)) ** 0.7:
            continue
        items.append((x, y, int(rng.integers(0, len(leaves))), rng.uniform(0, 360), rng.uniform(0.6, 1.2), rng.uniform(0.82, 1.12)))
    for (x, y, li, rot, sc, bright) in items:
        lf = leaves[li]
        h, w = lf.shape[:2]
        k = 100.0 * sc * SS / max(h, w)
        im = Image.fromarray((np.clip(lf, 0, 1) * 255).astype(np.uint8), 'RGBA')
        im = im.resize((max(2, int(w * k)), max(2, int(h * k))), Image.LANCZOS).rotate(rot, Image.BICUBIC, expand=True)
        arr = np.asarray(im, np.float32) / 255.0
        a = arr[..., 3]
        rgb = arr[..., :3] * 0.7 * bright                                   # darkened x0.7
        lum = rgb.mean(axis=2, keepdims=True)
        rgb = lum + (rgb - lum) * 0.85
        if rng.random() < 0.2:
            rgb = rgb * 0.62                                                # a few rotted dark leaves
        if rng.random() < 0.35:                                             # broken / partly buried edge
            hh, ww = a.shape
            yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
            ang = rng.uniform(0, 6.283)
            cut = (xx - ww / 2) * math.cos(ang) + (yy - hh / 2) * math.sin(ang)
            a = a * (cut < rng.uniform(0.1, 0.3) * max(hh, ww)).astype(np.float32)
        x0, y0 = int(x * SS - a.shape[1] / 2), int(y * SS - a.shape[0] / 2)
        sx0, sy0, sx1, sy1 = max(0, x0), max(0, y0), min(N, x0 + a.shape[1]), min(N, y0 + a.shape[0])
        if sx1 <= sx0 or sy1 <= sy0:
            continue
        ca = a[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0]
        cr = rgb[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0]
        o = 4 * SS
        yy1, xx1 = min(N, sy1 + o), min(N, sx1 + o)
        shadow[sy0 + o:yy1, sx0 + o:xx1] = np.maximum(shadow[sy0 + o:yy1, sx0 + o:xx1], ca[:yy1 - sy0 - o, :xx1 - sx0 - o])
        dst = canvas[sy0:sy1, sx0:sx1]
        oa = ca[..., None]
        dst[..., :3] = cr * oa + dst[..., :3] * (1 - oa)
        dst[..., 3:4] = oa + dst[..., 3:4] * (1 - oa)
    shadow = as_mask(Image.fromarray((shadow * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3.5 * SS))) * 0.45
    la = canvas[..., 3]
    sh_only = np.clip(shadow * (1 - la), 0, 1)
    sh_col = np.array((0.03, 0.025, 0.02), np.float32)
    out_a = la + sh_only * (1 - la)
    prem = canvas[..., :3] + sh_col[None, None, :] * sh_only[..., None]
    prem_d, a_d = down(prem, SS), down(out_a, SS)
    rgb = np.where(a_d[..., None] > 1e-3, prem_d / np.maximum(a_d, 1e-4)[..., None], sh_col[None, None, :])
    return np.dstack([np.clip(rgb, 0, 1), a_d[..., None]]).astype(np.float32)


def dust_drift_texture(seed):
    """1024^2 soft grey dust (0.38, 0.36, 0.33).  Dense corner = the top-left corner of the texture (u 0, v 0); alpha falls off radially with a
    lumpy, faintly rippled edge, a little thicker along the two edges that meet at that corner (the walls)."""
    rng = np.random.default_rng(seed)
    N = 1024
    ys, xs = np.mgrid[0:N, 0:N].astype(np.float32)
    x, y = (xs + 0.5) / N, (ys + 0.5) / N
    wx = (fbm(N, N, 200, 4, rng) - 0.5) * 0.22
    wy = (fbm(N, N, 200, 4, rng) - 0.5) * 0.22
    d = np.hypot(x + wx * 0.7, y + wy * 0.7)
    ripple = 0.5 + 0.5 * np.cos(d * 38.0 + 3.0 * (fbm(N, N, 90, 3, rng) - 0.5))      # wind-sorted ripples
    lump = fbm(N, N, 70, 4, rng)
    prof = (1.0 - smoothstep(0.08, 1.0, d)) ** 1.15
    wall = 0.18 * (np.exp(-x / 0.05) + np.exp(-y / 0.05))
    a = (prof * (0.78 + 0.34 * lump) + wall * prof) * (0.93 + 0.14 * ripple)
    a = a * (0.88 + 0.24 * rng.random((N, N)).astype(np.float32))
    a = a * (1 - smoothstep(0.80, 1.0, np.maximum(x, y)))                      # the far edges must be 0
    a = np.clip(a * 0.92, 0, 0.9)
    return rgba_const((0.38, 0.36, 0.33), a, (fbm(N, N, 50, 3, rng) - 0.5) * 0.16)


def stone_bg(h, w, seed=777):
    """Mid-grey stone-like preview backdrop: mottled noise plus slab joints."""
    rng = np.random.default_rng(seed)
    n = 0.55 * fbm(h, w, 90, 4, rng) + 0.13 * rng.random((h, w)).astype(np.float32) + 0.25 * fbm(h, w, 12, 3, rng)
    g = 0.27 + 0.13 * (n - 0.45)
    ys, xs = np.mgrid[0:h, 0:w]
    joint = ((ys % 256) < 3) | (((xs + (ys // 256 % 2) * 256) % 512) < 3)
    g = np.where(joint, g * 0.6, g)
    return np.dstack([g, g * 0.98, g * 0.94]).astype(np.float32)


def grime_preview(rgba, path, max_w=1024, bg_scales=(1.0,)):
    """Composite over the stone backdrop (several backdrop brightnesses side by side when bg_scales has more than one entry)."""
    h, w = rgba.shape[:2]
    a = rgba[..., 3:4]
    panels = [rgba[..., :3] * a + stone_bg(h, w) * bs * (1 - a) for bs in bg_scales]
    img = np.concatenate([p_ if i == 0 else np.concatenate([np.full((h, 8, 3), 0.9, np.float32), p_], axis=1) for i, p_ in enumerate(panels)], axis=1)
    w = img.shape[1]
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
    if w > max_w:
        im = im.resize((max_w, int(h * max_w / w)), Image.LANCZOS)
    im.save(path)


# name -> (seed key, generator call, preview file)
GRIME = [
    ("T_LB_Decal_Soot_A", "soot_a", lambda s: soot_texture(s, 0.03, 1.0)),
    ("T_LB_Decal_Soot_B", "soot_b", lambda s: soot_texture(s, -0.07, 1.25)),
    ("T_LB_Decal_Mould_Band", "mould", mould_band_texture),
    ("T_LB_Decal_WaterStain", "waterstain", water_stain_texture),
    ("T_LB_Decal_WaxDrips", "wax", wax_texture),
    ("T_LB_Decal_DragMarks", "drag", drag_marks_texture),
    ("T_LB_Decal_LeafLitter_A", "leaf_a", lambda s: leaf_litter_texture(s, 76, 1.0)),
    ("T_LB_Decal_LeafLitter_B", "leaf_b", lambda s: leaf_litter_texture(s, 54, 1.3)),
    ("T_LB_Decal_DustDrift", "dust", dust_drift_texture),
]


# ----------------------------------------------------------------------------------------------
# previews
# ----------------------------------------------------------------------------------------------
def over(rgba, bg):
    a = rgba[..., 3:4]
    return rgba[..., :3] * a + np.asarray(bg, np.float32)[None, None, :] * (1 - a)


def main():
    argv = sys.argv[1:]
    out_dir = os.path.join(ROOT, "ExternalAssets", "Generated", "chapel")
    prev_dir = os.path.join(ROOT, "Docs", "ArtTest", "chapel")
    only = []
    i = 0
    while i < len(argv):
        if argv[i] == "--out":
            out_dir = os.path.abspath(argv[i + 1]); i += 2
        elif argv[i] == "--preview":
            prev_dir = os.path.abspath(argv[i + 1]); i += 2
        elif argv[i] == "--only":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                only.append(argv[i]); i += 1
        else:
            i += 1
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(prev_dir, exist_ok=True)
    want = lambda k: (not only) or any(o in k for o in only)

    def lit(rgba):                                                # preview: the glass as the emissive material would show it
        return np.clip(rgba[..., :3] * 1.0, 0, 1)

    la = lb = None
    if want("lancet") or want("lightpool"):
        la = lancet_texture(SEEDS["lancet_a"], 'A')
        save_img(la, os.path.join(out_dir, "T_LB_StainedGlass_Lancet_A.png"))
        lb = lancet_texture(SEEDS["lancet_b"], 'B')
        save_img(lb, os.path.join(out_dir, "T_LB_StainedGlass_Lancet_B.png"))
        sheet = np.concatenate([lit(la), np.full((2048, 24, 3), 0.1, np.float32), lit(lb)], axis=1)
        Image.fromarray((sheet * 255).astype(np.uint8)).resize((sheet.shape[1] // 2, 1024), Image.LANCZOS).save(os.path.join(prev_dir, "tex_stainedglass_lancet.png"))
        Image.fromarray((lit(la) * 255).astype(np.uint8)).crop((0, 600, 512, 1300)).save(os.path.join(prev_dir, "tex_stainedglass_lancet_a_medallion.png"))
        print("lancet A/B done")
    if want("lightpool"):
        lp = lightpool_texture(la)
        save_img(lp, os.path.join(out_dir, "T_LB_LightPool_Lancet.png"))
        Image.fromarray((np.clip(lp, 0, 1) * 255).astype(np.uint8)).save(os.path.join(prev_dir, "tex_lightpool_lancet.png"))
        print("light pool done")
    if want("east"):
        ea = east_texture(SEEDS["east"])
        save_img(ea, os.path.join(out_dir, "T_LB_StainedGlass_East.png"))
        Image.fromarray((lit(ea) * 255).astype(np.uint8)).resize((512, 1024), Image.LANCZOS).save(os.path.join(prev_dir, "tex_stainedglass_east.png"))
        print("east done")
    if want("chalk_circle") or want("chalk"):
        cc = chalk_circle_texture(SEEDS["chalk_circle"])
        save_img(cc, os.path.join(out_dir, "T_LB_Decal_ChalkCircle.png"))
        pv = over(cc, (0.10, 0.10, 0.11))
        Image.fromarray((pv * 255).astype(np.uint8)).resize((1024, 1024), Image.LANCZOS).save(os.path.join(prev_dir, "tex_chalkcircle.png"))
        print("chalk circle done")
    if want("sigil") or want("chalk"):
        sg = chalk_sigil_texture(SEEDS["chalk_sigil"])
        save_img(sg, os.path.join(out_dir, "T_LB_Decal_ChalkSigil.png"))
        tl = chalk_tally_texture(SEEDS["chalk_tally"])
        save_img(tl, os.path.join(out_dir, "T_LB_Decal_ChalkTally.png"))
        sheet = np.zeros((512, 512 + 512 + 24, 3), np.float32) + 0.10
        sheet[:, :512] = over(sg, (0.10, 0.10, 0.11))
        sheet[128:384, 536:] = over(tl, (0.10, 0.10, 0.11))
        Image.fromarray((np.clip(sheet, 0, 1) * 255).astype(np.uint8)).save(os.path.join(prev_dir, "tex_chalk_sigil_tally.png"))
        print("sigil / tally done")
    if want("cobweb"):
        cw = cobweb_texture(SEEDS["cobweb"])
        save_img(cw, os.path.join(out_dir, "T_LB_Cobweb_A.png"))
        Image.fromarray((np.clip(over(cw, (0.08, 0.08, 0.09)), 0, 1) * 255).astype(np.uint8)).save(os.path.join(prev_dir, "tex_cobweb.png"))
        print("cobweb done")
    if want("slates"):
        slates_textures(SEEDS["slates"], out_dir, prev_dir)
    if want("grime") or any(want(g[0]) for g in GRIME):
        for (name, skey, fn) in GRIME:
            if not (want("grime") or want(name)):
                continue
            tex = fn(SEEDS[skey])
            save_img(tex, os.path.join(out_dir, name + ".png"))
            pv = tex
            if "DragMarks" in name:                                       # preview at the decal's true 600 x 120 cm aspect
                pv = np.asarray(Image.fromarray((tex * 255 + 0.5).astype(np.uint8), 'RGBA').resize((2560, 512), Image.BICUBIC), np.float32) / 255.0
            grime_preview(pv, os.path.join(prev_dir, "tex_grime_" + name.replace("T_LB_Decal_", "").lower() + ".png"), max_w=1536, bg_scales=((1.0, 0.4) if "Dust" in name else (1.0,)))
            print("%s done (%dx%d, seed %d)" % (name, tex.shape[1], tex.shape[0], SEEDS[skey]))


if __name__ == "__main__":
    main()
