"""gen_crypt_textures.py -- seeded, deterministic generator for the P9 crypt textures (Python + PIL + numpy).

    python Tools/textures/gen_crypt_textures.py [--out ExternalAssets/Generated/crypt] [--preview Docs/ArtTest/crypt]

Produces:
  T_LB_Water_Ripple_N   1024x1024 RGB, tileable DirectX normal map (green = -dh/dy with y down the image; import with sRGB off, normal-map compression).
                        6 plane-wave trains (integer wave vectors, so they wrap exactly; wavelength 18-60 px, random directions, amplitude falling with
                        frequency) + wraparound value noise (periodic lattice).  The strength is the largest one whose seam (row 0 vs row 1023, column 0
                        vs column 1023) differs by <= 2/255 in every channel; the seam numbers are printed.
Preview: tex_water_ripple.png (the tile rolled by half in both axes, native resolution: the seams cross in the middle of the image).

Seed 9320 (numpy default_rng).  Nothing else is random.
"""
import math
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SEED = 9320
N = 1024
MAX_SEAM = 2.0


def periodic_noise(rng, n, cell):
    """Smooth value noise that wraps exactly (periodic lattice of n/cell cells, cubic interpolation via smoothstep)."""
    g = n // cell
    lat = rng.random((g, g)).astype(np.float64)
    xs = (np.arange(n) / cell)
    i0 = np.floor(xs).astype(int) % g
    i1 = (i0 + 1) % g
    f = xs - np.floor(xs)
    f = f * f * (3 - 2 * f)
    a = lat[np.ix_(i0, i0)] * (1 - f)[None, :] + lat[np.ix_(i0, i1)] * f[None, :]
    b = lat[np.ix_(i1, i0)] * (1 - f)[None, :] + lat[np.ix_(i1, i1)] * f[None, :]
    return a * (1 - f)[:, None] + b * f[:, None]


def height_field(strength_scale=1.0):
    rng = np.random.default_rng(SEED)
    y, x = np.mgrid[0:N, 0:N].astype(np.float64)
    h = np.zeros((N, N))
    trains = []
    # periodic domain warp (breaks the regular lattice look; still wraps because the warp noise is periodic)
    wx = 14.0 * (periodic_noise(rng, N, 128) - 0.5) * 2 + 6.0 * (periodic_noise(rng, N, 64) - 0.5) * 2
    wy = 14.0 * (periodic_noise(rng, N, 128) - 0.5) * 2 + 6.0 * (periodic_noise(rng, N, 64) - 0.5) * 2
    x = x + wx
    y = y + wy
    # 6 wave trains: wavelength 18..60 px (|k| = N / wavelength cycles per tile), random directions, integer k so the field wraps
    wl = np.linspace(58.0, 19.0, 6) + rng.uniform(-2.0, 2.0, 6)           # spread over 18..60 px
    for i in range(6):
        mag = N / wl[i]
        ang = rng.uniform(0, 2 * math.pi)
        kx, ky = int(round(mag * math.cos(ang))), int(round(mag * math.sin(ang)))
        if kx == 0 and ky == 0:
            kx = 1
        lam = N / math.hypot(kx, ky)
        ph = rng.uniform(0, 2 * math.pi)
        amp = lam ** 2.0 * (1.0 + rng.uniform(-0.15, 0.15))          # slope amplitude ~ lam falls with frequency (height ~ lam^2)
        h += amp * np.sin(2 * math.pi * (kx * x + ky * y) / N + ph) * (0.65 + 0.7 * periodic_noise(rng, N, 256))   # slow amplitude variation
        trains.append((kx, ky, round(lam, 1), round(amp, 1)))
    for cell, a in ((256, 1.0), (128, 0.5), (64, 0.25)):            # wraparound value noise
        h += a * 900.0 * (periodic_noise(rng, N, cell) - 0.5)
    return h, trains


def normal_dx(h, scale):
    """DirectX normal from a height field with np.roll gradients (wrap-around): n = normalize(-dh/dx, -dh/dy_img, 1)."""
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5 * scale
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5 * scale
    nz = np.ones_like(dx)
    nrm = np.sqrt(dx * dx + dy * dy + nz * nz)
    n = np.stack([-dx / nrm, -dy / nrm, nz / nrm], axis=-1)
    return np.clip(np.rint((n * 0.5 + 0.5) * 255.0), 0, 255).astype(np.uint8)


def seam(img):
    a = img.astype(np.int32)
    row = np.abs(a[0] - a[-1])
    col = np.abs(a[:, 0] - a[:, -1])
    inner_r = np.abs(a[1:] - a[:-1]).max(axis=(1, 2))        # neighbour differences inside the tile, for reference
    return int(row.max()), float(row.mean()), int(col.max()), float(col.mean()), int(inner_r.max())


def main():
    argv = sys.argv[1:]
    out = os.path.join(ROOT, "ExternalAssets", "Generated", "crypt")
    prev = os.path.join(ROOT, "Docs", "ArtTest", "crypt")
    for i, a in enumerate(argv):
        if a == "--out":
            out = os.path.abspath(argv[i + 1])
        if a == "--preview":
            prev = os.path.abspath(argv[i + 1])
    os.makedirs(out, exist_ok=True)
    os.makedirs(prev, exist_ok=True)
    h, trains = height_field()
    # largest normal strength whose seam passes (bisection on the gradient scale)
    lo, hi = 0.0, 0.2
    best = None
    for _ in range(24):
        mid = (lo + hi) * 0.5
        img = normal_dx(h, mid)
        rmax, rmean, cmax, cmean, _ = seam(img)
        if max(rmax, cmax) <= MAX_SEAM:
            lo, best = mid, img
        else:
            hi = mid
    img = best
    scale = lo
    rmax, rmean, cmax, cmean, inner = seam(img)
    xy = (img[..., :2].astype(np.float64) / 255.0 * 2 - 1)
    slope = np.hypot(xy[..., 0], xy[..., 1])
    path = os.path.join(out, "T_LB_Water_Ripple_N.png")
    Image.fromarray(img, "RGB").save(path)
    # preview: the tile rolled by half so the wrap seams cross in the middle (native resolution)
    Image.fromarray(np.roll(img, (N // 2, N // 2), axis=(0, 1)), "RGB").save(os.path.join(prev, "tex_water_ripple.png"))
    print("wave trains (kx, ky, wavelength px, amplitude):", trains)
    print("normal gradient scale %.5f; max tilt (xy length) %.3f, mean %.3f" % (scale, slope.max(), slope.mean()))
    print("SEAM row0 vs row1023: max %d/255 mean %.3f; col0 vs col1023: max %d/255 mean %.3f (limit %d); largest inside-tile row neighbour diff %d" % (
        rmax, rmean, cmax, cmean, MAX_SEAM, inner))
    ok = max(rmax, cmax) <= MAX_SEAM
    print("SEAM CHECK", "PASS" if ok else "FAIL")
    print("wrote", path)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
