"""patch_cmp.py <before.png> <after.png> : cold-patch luma comparison on a pixel mask taken from the before image.
mask = (B > R + 4/255) & luma_before > 0.20 (the cold moonlit pixels). Reports before/after mean+median luma on that mask, ratio, centroid shift."""
import sys
import numpy as np
from PIL import Image


def luma_rgb(p):
    a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float64) / 255.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2], a


def main():
    yb, ab = luma_rgb(sys.argv[1])
    ya, aa = luma_rgb(sys.argv[2])
    thr = float(sys.argv[3]) if len(sys.argv) > 3 else 0.20
    m = (ab[..., 2] > ab[..., 0] + 4 / 255.0) & (yb > thr)
    n = int(m.sum())
    if n < 50:
        print("mask too small", n)
        return
    h, w = yb.shape
    yy, xx = np.mgrid[0:h, 0:w]

    def cen(y):
        wgt = y * m
        return (float((xx * wgt).sum() / wgt.sum()), float((yy * wgt).sum() / wgt.sum()))

    mb, ma = yb[m], ya[m]
    cb, ca = cen(yb), cen(ya)
    # also the mask taken from the after image
    m2 = (aa[..., 2] > aa[..., 0] + 4 / 255.0) & (ya > thr)
    print("mask px %d (after-mask %d) | before mean %.3f med %.3f p90 %.3f | after mean %.3f med %.3f p90 %.3f | ratio mean %.3f med %.3f | centroid shift px (%.1f, %.1f) | full-frame mean before %.4f after %.4f"
          % (n, int(m2.sum()), mb.mean(), np.median(mb), np.percentile(mb, 90), ma.mean(), np.median(ma), np.percentile(ma, 90),
             ma.mean() / mb.mean(), np.median(ma) / np.median(mb), ca[0] - cb[0], ca[1] - cb[1], yb.mean(), ya.mean()))


main()
