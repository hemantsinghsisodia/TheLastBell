"""P11-7: how bright the lantern glass reads, from captures taken with poses/p11_lantern_poses.json. No editor needed.

    python -I Tools/materials/lantern_report.py <prefix> [--dir Docs/ArtTest/materials] [--limit 0.95] [--half 40]

Reads <dir>/<prefix><pose>.png. Each pose looks straight at the glass, so the window of +-half pixels around the image centre holds the lantern
(the close view uses twice that). Prints per view: maximum luma in the window, 99th percentile, fraction of window pixels at or above 0.95, and the
scene's median luma as a reference. Luma = 0.2126 R + 0.7152 G + 0.0722 B on the 0-1 display values of the PNG. Exit 1 if any maximum is over the limit.
"""
import argparse
import glob
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prefix")
    ap.add_argument("--dir", default=os.path.join(ROOT, "Docs", "ArtTest", "materials"))
    ap.add_argument("--limit", type=float, default=0.95)
    ap.add_argument("--half", type=int, default=40)
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.dir, a.prefix + "*.png")))
    if not files:
        print("no files for", a.prefix)
        return 2
    over = 0
    print("%-22s %6s %6s %8s %7s" % ("view", "max", "p99", "clipped", "median"))
    for f in files:
        im = np.asarray(Image.open(f).convert("RGB")).astype(np.float32) / 255.0
        y = 0.2126 * im[..., 0] + 0.7152 * im[..., 1] + 0.0722 * im[..., 2]
        h, w = y.shape
        name = os.path.basename(f)[len(a.prefix):-4]
        half = a.half * (4 if "close" in name else 2 if "_3m" in name else 1)
        win = y[max(0, h // 2 - half):h // 2 + half, max(0, w // 2 - half):w // 2 + half]
        peak = float(win.max())
        over += peak > a.limit
        print("%-22s %6.3f %6.3f %7.1f%% %7.3f%s" % (name, peak, float(np.percentile(win, 99)), 100.0 * float((win >= 0.95).mean()), float(np.median(y)), "  OVER" if peak > a.limit else ""))
    print("%d views, %d over %.2f" % (len(files), over, a.limit))
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
