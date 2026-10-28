"""P9-7 B2 luma report for capture PNGs.

    python luma_report.py [--json out.json] [--plaque] file1.png file2.png ...

B2: Y = 0.2126 R + 0.7152 G + 0.0722 B on the PNG's 8-bit sRGB values / 255 (no linearisation), full frame.
Per file: mean, fraction of pixels < 0.02, p99, max, floor box p99 (x 20-80 %, y 67-100 %), floor box mean,
central-40 % mean (x 30-70 %, y 30-70 % of the frame, the wall-pose pass metric), centre-10 % median (x/y 45-55 %: the pool-centre
luma on the pool_G1/pool_G2/plaque poses, which are aimed so the pool centre is the image centre; the grate bars cast a dark cross over the G1/G2 pools, so the pool brightness is
reported as pool_lit_median = median of the central-40 % box pixels brighter than 0.1 (the lit tiles / lit plaque), centre40_p90 also given), and with --plaque the plaque text contrast
(text band = rows y 40-58 % of the frame, x 20-80 %; contrast = p98 luma of the band / median luma of the band; calibrated on
p9b_1e_12_puzzle_wall_2m.png, which gives 2.3-2.4 like the P9-6b 1e report's 2.34).
"""
import json
import sys

import numpy as np
from PIL import Image


def luma(path):
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64) / 255.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def box(y, x0, x1, y0, y1):
    h, w = y.shape
    return y[int(h * y0):int(h * y1), int(w * x0):int(w * x1)]


def report(path, plaque=False):
    y = luma(path)
    f = box(y, 0.2, 0.8, 0.67, 1.0)
    c = box(y, 0.3, 0.7, 0.3, 0.7)
    r = {"file": path.replace("\\", "/").split("/")[-1], "mean": float(y.mean()), "lt002": float((y < 0.02).mean()),
         "p99": float(np.percentile(y, 99)), "max": float(y.max()), "floor_p99": float(np.percentile(f, 99)),
         "floor_mean": float(f.mean()), "central40_mean": float(c.mean()),
         "centre10_median": float(np.median(box(y, 0.45, 0.55, 0.45, 0.55))),
         "centre40_p90": float(np.percentile(c, 90)),
         "pool_lit_median": float(np.median(c[c > 0.1])) if (c > 0.1).any() else 0.0}
    if plaque:
        b = box(y, 0.2, 0.8, 0.40, 0.58)
        r["plaque_band_median"] = float(np.median(b))
        r["plaque_text_p98"] = float(np.percentile(b, 98))
        r["plaque_contrast"] = r["plaque_text_p98"] / max(r["plaque_band_median"], 1e-6)
    return r


def main():
    args = sys.argv[1:]
    out = None
    plaque = False
    if "--json" in args:
        i = args.index("--json")
        out = args[i + 1]
        del args[i:i + 2]
    if "--plaque" in args:
        plaque = True
        args.remove("--plaque")
    rows = [report(p, plaque) for p in args]
    for r in rows:
        s = "%-44s mean %.4f  <0.02 %5.1f%%  p99 %.3f  max %.3f  floor p99 %.3f  central40 %.3f  centre10 %.3f  c40p90 %.3f  poolLit %.3f" % (
            r["file"], r["mean"], 100 * r["lt002"], r["p99"], r["max"], r["floor_p99"], r["central40_mean"], r["centre10_median"], r["centre40_p90"], r["pool_lit_median"])
        if plaque:
            s += "  plaque contrast %.2f (p98 %.3f / median %.3f)" % (r["plaque_contrast"], r["plaque_text_p98"], r["plaque_band_median"])
        print(s)
    if out:
        json.dump(rows, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
