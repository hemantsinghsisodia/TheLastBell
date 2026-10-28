"""hue_strips.py <png> : D1.20 5(a) strip-hue order check. Glass rect = bounding box of saturated bright pixels in the loose window below."""
import sys, colorsys
import numpy as np
from PIL import Image
a = np.asarray(Image.open(sys.argv[1]).convert("RGB"), float) / 255.0
x0, y0, x1, y1 = [int(v) for v in sys.argv[2:6]]
w = a[y0:y1, x0:x1]
mx, mn = w.max(2), w.min(2)
sat = (mx - mn) / np.maximum(mx, 1e-6)
lum = .2126 * w[..., 0] + .7152 * w[..., 1] + .0722 * w[..., 2]
m = (sat > 0.35) & (lum > 0.15)
ys, xs = np.nonzero(m)
bx0, bx1, by0, by1 = xs.min(), xs.max(), ys.min(), ys.max()
print("glass rect (window coords) x %d..%d y %d..%d -> image x %d..%d y %d..%d" % (bx0, bx1, by0, by1, bx0 + x0, bx1 + x0, by0 + y0, by1 + y0))
W = bx1 - bx0 + 1
hues, lumas = [], []
for k in range(4):
    sx0, sx1 = bx0 + int(W * k / 4), bx0 + int(W * (k + 1) / 4)
    sub = w[by0:by1 + 1, sx0:sx1]
    s_ = sat[by0:by1 + 1, sx0:sx1]; l_ = lum[by0:by1 + 1, sx0:sx1]
    mm = s_ > 0.35
    # circular mean hue of saturated pixels
    hh = np.array([colorsys.rgb_to_hsv(*p)[0] for p in sub[mm]]) * 2 * np.pi
    hue = (np.degrees(np.arctan2(np.sin(hh).mean(), np.cos(hh).mean())) % 360)
    hues.append(hue)
    lumas.append(float(l_[mm].mean()))
    print("strip %d: hue %.1f deg, mean luma of saturated px %.3f, n=%d" % (k + 1, hue, lumas[-1], int(mm.sum())))
d = [min(abs(hues[i] - hues[i + 1]), 360 - abs(hues[i] - hues[i + 1])) for i in range(3)]
print("adjacent hue gaps", [round(x, 1) for x in d], "| order green(120) red(0) amber(~40) blue(~230):", [round(h) for h in hues])
