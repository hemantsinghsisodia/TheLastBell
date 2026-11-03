"""P11-6 step 1a: crack decal textures (angular fractures in stone, not hair).

    python -I Tools/materials/gen_crack_textures.py [--out ExternalAssets/Generated/materials] [--preview Docs/ArtTest/materials] [--debug-crops DIR]

Writes, for each of the three sets A / B / C:
    T_LB_Decal_Crack_<X>_Opacity.png   8-bit L
    T_LB_Decal_Crack_<X>_N.png         RGB, DirectX normal (+Y down the image)
and the previews p11_crack_tex_<x>.png (1024 px on the long side).

numpy + PIL only.  Every random number comes from numpy.random.default_rng(seed), so every run gives the same files.
The crack path is never smoothed, splined or blurred: it is a zig-zag of straight segments (heading = direction to the target
+ an independent random offset, so the offsets never accumulate).  Only the *maps derived from the drawing* are blurred.
Exit 1 if a check fails.  Coordinates (u, v): v runs down the image.
"""
import argparse
import hashlib
import io
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SS = 2                                                             # drawing canvas scale

# set -> parameters.  All lengths/widths are final-size pixels.
SETS = {
    "A": dict(W=2048, H=2048, seed=11101, k=6, step=0.30, kind="diag",
              start=(0.16, 0.10), end=(0.84, 0.90), w0=18.0, w1=2.0),
    "B": dict(W=1024, H=2048, seed=11102, k=5, step=0.12, kind="arch",
              start=(0.50, 0.94), end_v=0.06, end_du=0.12, w0=20.0, w1=2.0),
    "C": dict(W=2048, H=2048, seed=11103, k=3, step=0.0, kind="fork",
              start=(0.50, 0.93), stem_frac=0.55, w0=16.0, w1=6.0, prong_frac=0.35, prong_w0=6.0, prong_w1=2.0),
}

# look parameters (spec values, except BRANCH_OFF, SAFE_INSET and the B start v: see the notes at each)
SEG_LO, SEG_HI = 22.0, 60.0                                        # segment length, px
MAIN_OFF = 28.0                                                    # +- degrees, main stem
BRANCH_OFF = 34.0                                                  # +- degrees, branches (spec said 22; raised to 34 so thin branches zig-zag instead of reading as smooth lines)
STEP_HEAD_JITTER = 8.0                                             # +- degrees around horizontal on a "bed joint" step
STEP_LEN_MUL = 1.5
BRANCH_ANGLE = (25.0, 55.0)
BRANCH_LEN = (0.15, 0.35)
SUB_LEN_FRAC = 0.35
SUB_THRESHOLD = 0.22


# ----------------------------------------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------------------------------------
def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def vnoise(h, w, cell, rng):
    """Smooth value noise in [0, 1] (bicubic upsample of a random lattice)."""
    c = max(2, int(cell))
    gh, gw = int(math.ceil(h / c)) + 3, int(math.ceil(w / c)) + 3
    g = rng.random((gh, gw)).astype(np.float32)
    im = Image.fromarray(g).resize((gw * c, gh * c), Image.BICUBIC)
    a = np.asarray(im, dtype=np.float32)
    return np.clip(a[c:c + h, c:c + w], 0.0, 1.0)


def fbm(h, w, cell, octs, rng):
    tot = np.zeros((h, w), np.float32)
    amp, norm, c = 1.0, 0.0, float(cell)
    for _ in range(octs):
        tot += amp * vnoise(h, w, max(2.0, c), rng)
        norm += amp
        amp *= 0.5
        c *= 0.5
    return tot / norm


def gblur(a, sigma):
    """Gaussian blur (sigma in px) by FFT, numpy only."""
    h, w = a.shape
    f = np.fft.rfft2(a.astype(np.float32))
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    g = np.exp(-2.0 * math.pi ** 2 * sigma ** 2 * (fx ** 2 + fy ** 2))
    return np.fft.irfft2(f * g, s=a.shape).astype(np.float32)


def rad(deg):
    return deg * math.pi / 180.0


# ----------------------------------------------------------------------------------------------------------
# the walker: straight segments, heading = base + independent offset (never accumulated), never smoothed
# ----------------------------------------------------------------------------------------------------------
class Path:
    def __init__(self, pts, w0, w1):
        self.pts = np.asarray(pts, np.float64)                      # (n, 2) px
        d = np.diff(self.pts, axis=0)
        self.seg_len = np.hypot(d[:, 0], d[:, 1])
        self.seg_head = np.arctan2(d[:, 1], d[:, 0])
        self.cum = np.concatenate([[0.0], np.cumsum(self.seg_len)])
        self.total = float(self.cum[-1])
        self.w0, self.w1 = w0, w1

    def width_at(self, s):
        return self.w0 + (self.w1 - self.w0) * (min(max(s, 0.0), 1.0) ** 0.8)

    def at(self, s):
        """(point, heading, base width) at fraction s of the arc length."""
        L = s * self.total
        i = int(np.searchsorted(self.cum, L, side="right") - 1)
        i = min(max(i, 0), len(self.seg_len) - 1)
        t = (L - self.cum[i]) / max(self.seg_len[i], 1e-9)
        p = self.pts[i] + (self.pts[i + 1] - self.pts[i]) * t
        return p, float(self.seg_head[i]), self.width_at(s)


SAFE_INSET = 0.055                                                 # strokes stay this fraction of the size from every edge, so the 3 % fade band is empty (the spec border check needs it)
_SAFE = [0.0, 0.0, 1e9, 1e9]


def _inside(q):
    return _SAFE[0] <= q[0] <= _SAFE[2] and _SAFE[1] <= q[1] <= _SAFE[3]


def walk(rng, p0, heading, target, length, offs, step, lo=SEG_LO, hi=SEG_HI):
    """Straight segments from p0.  With a target: heading = direction to the target + offset, until the target is reached.
    Without: heading = `heading` + offset, until `length` px have been walked.  `step`: probability of a horizontal
    (+-8 deg) segment, 1.5x longer, as if the crack ran along a bed joint."""
    pts = [np.asarray(p0, np.float64)]
    total = 0.0
    for _ in range(4000):
        p = pts[-1]
        if target is not None:
            d = target - p
            dist = float(np.hypot(d[0], d[1]))
            if dist < lo * 0.5:
                break
            base = math.atan2(d[1], d[0])
            remaining = dist
        else:
            remaining = length - total
            if remaining < lo * 0.35:
                break
            base = heading
        h = base + rad(rng.uniform(-offs, offs))
        seg = rng.uniform(lo, hi)
        if step > 0.0 and rng.random() < step:
            c = math.cos(base)
            hz = 0.0 if c > 0.3 else (math.pi if c < -0.3 else (0.0 if rng.random() < 0.5 else math.pi))
            h = hz + rad(rng.uniform(-STEP_HEAD_JITTER, STEP_HEAD_JITTER))
            seg *= STEP_LEN_MUL
        if target is None:
            seg = min(seg, remaining)
        q = p + seg * np.array([math.cos(h), math.sin(h)])
        if not _inside(q):                                           # keep clear of the fade band: a crack ends rather than leaves
            if target is None:
                break
            q = p + seg * np.array([math.cos(base), math.sin(base)])
            if not _inside(q):
                break
        pts.append(q)
        total += seg
        if target is not None and float(np.dot(target - p, target - q)) < 0.0:
            break                                                    # passed the target
    return pts


def stations(rng, k, lo=0.15, hi=0.85, gap=0.12):
    """k stations in [lo, hi], sorted, at least `gap` apart (stick-breaking, so it cannot fail)."""
    slack = (hi - lo) - (k - 1) * gap
    base = np.sort(rng.uniform(0.0, max(slack, 0.0), k))
    return [lo + b + i * gap for i, b in enumerate(base)]


def grow_branches(rng, parent, k, paths, lo_hi=(0.15, 0.85), parent_len=None):
    """k branches off `parent` (and a sub-branch on the long ones).  Appends Path objects to `paths`."""
    plen = parent.total if parent_len is None else parent_len
    for s in stations(rng, k, *lo_hi):
        p, hd, w = parent.at(s)
        sign = 1.0 if rng.random() < 0.5 else -1.0
        h0 = hd + sign * rad(rng.uniform(*BRANCH_ANGLE))
        length = rng.uniform(*BRANCH_LEN) * plen
        pts = walk(rng, p, h0, None, length, BRANCH_OFF, 0.0)
        if len(pts) < 2:
            continue
        br = Path(pts, 0.5 * w, 1.5)
        paths.append(br)
        if br.total > SUB_THRESHOLD * plen:
            s2 = rng.uniform(0.3, 0.8)
            p2, hd2, w2 = br.at(s2)
            sign2 = 1.0 if rng.random() < 0.5 else -1.0
            h2 = hd2 + sign2 * rad(rng.uniform(*BRANCH_ANGLE))
            pts2 = walk(rng, p2, h2, None, SUB_LEN_FRAC * br.total, BRANCH_OFF, 0.0)
            if len(pts2) >= 2:
                paths.append(Path(pts2, 0.5 * w2, 1.5))


# ----------------------------------------------------------------------------------------------------------
# geometry -> primitives (final-size px), drawn low value first so a faint twig never overwrites a solid stroke
# ----------------------------------------------------------------------------------------------------------
def stroke_prims(rng, path, circles=True):
    """Filled trapezoid per segment (width jittered per segment 0.75-1.25), a filled circle at each joint."""
    quads, discs = [], []
    n = len(path.seg_len)
    jit = rng.uniform(0.75, 1.25, n)
    wa = [(path.width_at(path.cum[i] / path.total)) * jit[i] for i in range(n)]
    wb = [(path.width_at(path.cum[i + 1] / path.total)) * jit[i] for i in range(n)]
    for i in range(n):
        a, b = path.pts[i], path.pts[i + 1]
        nx, ny = -math.sin(path.seg_head[i]), math.cos(path.seg_head[i])
        ha, hb = wa[i] * 0.5, wb[i] * 0.5
        quads.append([(a[0] + nx * ha, a[1] + ny * ha), (b[0] + nx * hb, b[1] + ny * hb),
                      (b[0] - nx * hb, b[1] - ny * hb), (a[0] - nx * ha, a[1] - ny * ha)])
    if circles:
        for i in range(n + 1):
            r = max(wa[i] if i < n else 0.0, wb[i - 1] if i > 0 else 0.0) * 0.5
            discs.append((path.pts[i][0], path.pts[i][1], r))
    return quads, discs


def chip_prims(rng, path):
    """Spall polygons along the main stem, one side each, every 120-260 px."""
    polys = []
    d = rng.uniform(120.0, 260.0)
    while d < path.total:
        s = d / path.total
        p, hd, w = path.at(s)
        side = 1.0 if rng.random() < 0.5 else -1.0
        r = rng.uniform(4.0, 14.0)
        nx, ny = -math.sin(hd), math.cos(hd)
        off = w * 0.5 + r * 0.35
        c = p + side * off * np.array([nx, ny])
        nv = int(rng.integers(4, 7))
        ang = np.sort(rng.uniform(0.0, 2.0 * math.pi, nv))
        rr = r * rng.uniform(0.6, 1.0, nv)
        polys.append([(c[0] + rr[j] * math.cos(ang[j]), c[1] + rr[j] * math.sin(ang[j])) for j in range(nv)])
        d += rng.uniform(120.0, 260.0)
    return polys


def twig_prims(rng, paths, n_tw):
    """Hairline twigs (30-90 px, 1.5 -> 1 px) off the stem or branches."""
    quads, discs = [], []
    for _ in range(n_tw):
        par = paths[int(rng.integers(0, len(paths)))]
        s = rng.uniform(0.05, 0.95)
        p, hd, _w = par.at(s)
        sign = 1.0 if rng.random() < 0.5 else -1.0
        h0 = hd + sign * rad(rng.uniform(30.0, 70.0))
        pts = walk(rng, p, h0, None, rng.uniform(30.0, 90.0), BRANCH_OFF, 0.0, lo=10.0, hi=25.0)
        if len(pts) < 2:
            continue
        tw = Path(pts, 1.5, 1.0)
        q, dd = stroke_prims(rng, tw)
        quads += q
        discs += dd
    return quads, discs


def draw_all(layers, W, H):
    """layers: list of (value 0..1, quads, discs, polys), drawn in the order given (ascending value)."""
    im = Image.new("L", (W * SS, H * SS), 0)
    dr = ImageDraw.Draw(im)
    for value, quads, discs, polys in layers:
        v = int(round(value * 255))
        for q in quads:
            dr.polygon([(x * SS, y * SS) for x, y in q], fill=v)
        for (x, y, r) in discs:
            dr.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], fill=v)
        for pl in polys:
            dr.polygon([(x * SS, y * SS) for x, y in pl], fill=v)
    return im.resize((W, H), Image.LANCZOS)


def build_geometry(name):
    P = SETS[name]
    W, H = P["W"], P["H"]
    rng = np.random.default_rng(P["seed"])
    _SAFE[:] = [SAFE_INSET * W, SAFE_INSET * H, (1.0 - SAFE_INSET) * W, (1.0 - SAFE_INSET) * H]
    p0 =np.array([P["start"][0] * W, P["start"][1] * H])
    paths = []                                                       # every drawn stroke
    if P["kind"] == "diag":
        target = np.array([P["end"][0] * W, P["end"][1] * H])
        main = Path(walk(rng, p0, 0.0, target, 0.0, MAIN_OFF, P["step"]), P["w0"], P["w1"])
        paths.append(main)
        grow_branches(rng, main, P["k"], paths)
        stem_paths = [main]
    elif P["kind"] == "arch":
        sgn = 1.0 if rng.random() < 0.5 else -1.0
        target = np.array([(0.5 + sgn * P["end_du"]) * W, P["end_v"] * H])
        main = Path(walk(rng, p0, 0.0, target, 0.0, MAIN_OFF, P["step"]), P["w0"], P["w1"])
        paths.append(main)
        grow_branches(rng, main, P["k"], paths)
        stem_paths = [main]
    else:                                                            # fork
        target = np.array([p0[0], p0[1] - P["stem_frac"] * H])
        main = Path(walk(rng, p0, 0.0, target, 0.0, MAIN_OFF, P["step"]), P["w0"], P["w1"])
        paths.append(main)
        grow_branches(rng, main, P["k"], paths)
        tip = main.pts[-1]
        up = -math.pi / 2.0
        for sg in (-1.0, 1.0):
            h0 = up + sg * rad(rng.uniform(28.0, 40.0))
            pr = Path(walk(rng, tip, h0, None, P["prong_frac"] * H, MAIN_OFF, 0.0), P["prong_w0"], P["prong_w1"])
            paths.append(pr)
        stem_paths = [main] + paths[-2:]
    # strokes
    q_all, d_all = [], []
    for p in paths:
        q, d = stroke_prims(rng, p)
        q_all += q
        d_all += d
    # twigs and chips
    tq, td = twig_prims(rng, paths, int(rng.integers(6, 11)))
    chips = chip_prims(rng, main)
    layers = [(0.6, tq, td, []), (0.7, [], [], chips), (1.0, q_all, d_all, [])]
    return layers, paths


# ----------------------------------------------------------------------------------------------------------
# maps
# ----------------------------------------------------------------------------------------------------------
def border_fade(W, H):
    u = (np.arange(W, dtype=np.float32) + 0.5) / W
    v = (np.arange(H, dtype=np.float32) + 0.5) / H
    fu = smoothstep(0.0, 0.03, np.minimum(u, 1.0 - u))[None, :]
    fv = smoothstep(0.0, 0.03, np.minimum(v, 1.0 - v))[:, None]
    return (fu * fv).astype(np.float32)


def build_maps(name):
    P = SETS[name]
    W, H = P["W"], P["H"]
    layers, paths = build_geometry(name)
    core = np.clip(np.asarray(draw_all(layers, W, H), np.float32) / 255.0, 0.0, 1.0)
    rng = np.random.default_rng(P["seed"] + 500000)                  # independent stream for the noise
    noise = fbm(H, W, 90, 3, rng)
    bleed = gblur(core, 14.0) * (0.45 + 0.9 * noise)
    fade = border_fade(W, H)
    opacity = np.maximum(core, 0.22 * np.clip(bleed, 0.0, 1.0)) * fade
    h = (-gblur(core, 1.5) + 0.25 * gblur(core, 6.0)) * fade
    dhdy, dhdx = np.gradient(h)
    K = 6.0
    n = np.dstack([-dhdx * K, -dhdy * K, np.ones_like(h)])
    n = n / np.linalg.norm(n, axis=2, keepdims=True)
    opacity8 = np.clip(opacity * 255.0 + 0.5, 0, 255).astype(np.uint8)
    normal8 = np.clip((n * 0.5 + 0.5) * 255.0 + 0.5, 0, 255).astype(np.uint8)
    return core, opacity, opacity8, normal8, n.astype(np.float32), paths


def png_bytes(arr8, mode):
    b = io.BytesIO()
    Image.fromarray(arr8, mode).save(b, format="PNG")
    return b.getvalue()


# ----------------------------------------------------------------------------------------------------------
# preview
# ----------------------------------------------------------------------------------------------------------
def make_preview(name, opacity, n):
    P = SETS[name]
    W, H = P["W"], P["H"]
    rng = np.random.default_rng(P["seed"] + 900000)
    stone = 0.40 + 0.22 * fbm(H, W, 160, 4, rng) + 0.06 * (vnoise(H, W, 3, rng) - 0.5)
    L = np.array([-0.5, -0.5, 0.7], np.float32)
    L = L / np.linalg.norm(L)
    flat = float(L[2])
    shade = np.clip((n[..., 0] * L[0] + n[..., 1] * L[1] + n[..., 2] * L[2]) / flat, 0.0, 2.0)
    col = stone * shade * (1.0 - opacity) + 0.025 * opacity
    img = Image.fromarray((np.clip(col, 0, 1) * 255 + 0.5).astype(np.uint8), "L")
    return img


# ----------------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "ExternalAssets", "Generated", "materials"))
    ap.add_argument("--preview", default=os.path.join(ROOT, "Docs", "ArtTest", "materials"))
    ap.add_argument("--debug-crops", default=None, help="also write full-resolution crops of the preview here (not part of the pipeline)")
    ap.add_argument("--only", nargs="*", default=None)
    a = ap.parse_args()
    out_dir, prev_dir = os.path.abspath(a.out), os.path.abspath(a.preview)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(prev_dir, exist_ok=True)
    if a.debug_crops:
        os.makedirs(a.debug_crops, exist_ok=True)
    ok = True
    for name in ("A", "B", "C"):
        if a.only and name not in a.only:
            continue
        P = SETS[name]
        W, H = P["W"], P["H"]
        core, opacity, op8, nr8, n, paths = build_maps(name)
        # ---- determinism: rebuild and compare byte-for-byte
        _c2, _o2, op8b, nr8b, _n2, _p2 = build_maps(name)
        b_op, b_nr = png_bytes(op8, "L"), png_bytes(nr8, "RGB")
        md_op, md_nr = hashlib.md5(b_op).hexdigest(), hashlib.md5(b_nr).hexdigest()
        same = (hashlib.md5(png_bytes(op8b, "L")).hexdigest() == md_op) and (hashlib.md5(png_bytes(nr8b, "RGB")).hexdigest() == md_nr)
        # ---- checks
        cov = float((opacity > 0.5).mean()) * 100.0
        u = (np.arange(W, dtype=np.float32) + 0.5) / W
        v = (np.arange(H, dtype=np.float32) + 0.5) / H
        d = np.minimum(np.minimum(u, 1 - u)[None, :], np.minimum(v, 1 - v)[:, None])
        band = d < 0.03
        bmax = float(opacity[band].max())
        nflat = float(np.abs(n[band][:, :2]).max())
        nvar = float(np.abs(n[..., :2]).max())
        c_cov = 0.3 <= cov <= 2.5
        c_bmax = bmax < 0.01
        c_flat = nflat < 0.02
        c_same = bool(same)
        print("[%s] %dx%d seed %d  paths %d (stroke length %.0f px)" % (name, W, H, P["seed"], len(paths), sum(p.total for p in paths)))
        print("    coverage opacity>0.5      : %.3f %%   (0.3-2.5)  %s" % (cov, "ok" if c_cov else "FAIL"))
        print("    border band max opacity   : %.5f     (<0.01)    %s" % (bmax, "ok" if c_bmax else "FAIL"))
        print("    border band max |n.xy|    : %.5f     (<0.02)    %s   (whole map max %.3f)" % (nflat, "ok" if c_flat else "FAIL", nvar))
        print("    in-process rebuild identical                      %s" % ("ok" if c_same else "FAIL"))
        print("    MD5 T_LB_Decal_Crack_%s_Opacity.png %s" % (name, md_op))
        print("    MD5 T_LB_Decal_Crack_%s_N.png       %s" % (name, md_nr))
        ok = ok and c_cov and c_bmax and c_flat and c_same
        with open(os.path.join(out_dir, "T_LB_Decal_Crack_%s_Opacity.png" % name), "wb") as f:
            f.write(b_op)
        with open(os.path.join(out_dir, "T_LB_Decal_Crack_%s_N.png" % name), "wb") as f:
            f.write(b_nr)
        pv = make_preview(name, opacity, n)
        if a.debug_crops:
            pv.save(os.path.join(a.debug_crops, "full_%s.png" % name))
        s = 1024.0 / max(W, H)
        pv.resize((max(1, int(round(W * s))), max(1, int(round(H * s)))), Image.LANCZOS).save(os.path.join(prev_dir, "p11_crack_tex_%s.png" % name.lower()))
    print("ALL CHECKS PASSED" if ok else "CHECKS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
