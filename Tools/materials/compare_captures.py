"""P11-5b: mean absolute pixel difference between two capture sets, per pose, in 8-bit units.

    python Tools/materials/compare_captures.py <prefix_a> <prefix_b> [--limit 2.0] pose1 pose2 ...

Reads Docs/ArtTest/materials/<prefix><pose>.png. Exit code 1 if any pose is over the limit.

The editor viewport changes size with the window layout. The horizontal field of view is fixed, so when sizes differ the second image
is scaled to the first one's width and both are centre-cropped to the shorter height ("fit" in the output). Scaling softens the image
a little, so a fitted comparison reads slightly higher than a same-size one.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Docs", "ArtTest", "materials")


def load(prefix, pose):
    return Image.open(os.path.join(DIR, prefix + pose + ".png")).convert("RGB")


def fit(a, b):
    if a.size == b.size:
        return a, b, False
    b = b.resize((a.width, round(b.height * a.width / b.width)), Image.LANCZOS)
    h = min(a.height, b.height)
    a = a.crop((0, (a.height - h) // 2, a.width, (a.height - h) // 2 + h))
    b = b.crop((0, (b.height - h) // 2, b.width, (b.height - h) // 2 + h))
    return a, b, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prefix_a")
    ap.add_argument("prefix_b")
    ap.add_argument("poses", nargs="+")
    ap.add_argument("--limit", type=float, default=2.0)
    args = ap.parse_args()
    bad = 0
    for pose in args.poses:
        a, b, fitted = fit(load(args.prefix_a, pose), load(args.prefix_b, pose))
        d = np.abs(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64))
        mean = d.mean()
        over = mean > args.limit
        bad += over
        print("%-4s %-26s mean diff %.3f/255  p99 %.1f  max %.0f%s" % ("FAIL" if over else "PASS", pose, mean, np.percentile(d, 99), d.max(), "  fit" if fitted else ""))
    print("%d poses, %d over %.1f/255" % (len(args.poses), bad, args.limit))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
