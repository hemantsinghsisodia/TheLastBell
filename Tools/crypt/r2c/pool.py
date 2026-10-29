"""pool.py <with_note.png> <bare.png> : pool luma on the note region, from the bare-wall capture.
note bbox = pixels where |with - bare| luma > 0.08 (largest blob bbox). Pool = bare pixels with luma > 0.10 (cold-lit: B > R).
Reports: note-region median bare luma (pool luma at the note), pool P33/P67/max, note percentile inside the pool, paper luma."""
import sys
import numpy as np
from PIL import Image
def L(p):
    a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float64) / 255.0
    return 0.2126*a[...,0] + 0.7152*a[...,1] + 0.0722*a[...,2], a
yw, aw = L(sys.argv[1]); yb, ab = L(sys.argv[2])
diff = np.abs(yw - yb) > 0.08
ys, xs = np.where(diff)
sel = (np.abs(ys - np.median(ys)) < 60) & (np.abs(xs - np.median(xs)) < 80)
ys, xs = ys[sel], xs[sel]
y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
print("note bbox px x %d..%d y %d..%d (%dx%d), blob px %d" % (x0, x1, y0, y1, x1-x0+1, y1-y0+1, len(ys)))
pool = (yb > 0.10) & (ab[...,2] > ab[...,0])
reg = yb[y0:y1+1, x0:x1+1]
note_pool = np.median(reg)
pv = yb[pool]
p33, p67 = np.percentile(pv, 33), np.percentile(pv, 67)
pct = (pv < note_pool).mean() * 100
print("pool px %d  pool luma P33 %.3f P67 %.3f P95 %.3f max %.3f | pool-median %.3f" % (pool.sum(), p33, p67, np.percentile(pv, 95), pv.max(), np.median(pv)))
print("bare-wall luma behind the note: median %.3f mean %.3f p10 %.3f p90 %.3f -> percentile within the pool %.0f%% (brightest third = >=67%%)" % (note_pool, reg.mean(), np.percentile(reg, 10), np.percentile(reg, 90), pct))
print("paper luma (with note): median %.3f" % np.median(yw[y0+5:y1-5, x0+5:x1-5]))
# local pool luma around the note: 15 px ring
r = 25
ring = np.zeros_like(pool); ring[max(0,y0-r):y1+r, max(0,x0-r):x1+r] = True; ring[y0:y1+1, x0:x1+1] = False
print("bare ring (25px around the note) median %.3f" % np.median(yb[ring]))
