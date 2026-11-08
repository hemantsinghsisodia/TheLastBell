"""S1: count rain-streak (white) and splash (orange) pixels inside roofed rects, rain-on vs off1 (lead, 2026-11-08)."""
import numpy as np
from PIL import Image
D = r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\fx\s1"
def L(p, s):
    return np.asarray(Image.open(rf"{D}\p15_{p}_{s}.png").convert("RGB"), dtype=np.float32) / 255
# roofed regions (x0, y0, x1, y1) in capture pixels (1331 x 808), judged from the onF/onS frames
R = {
 "s1_ch_hole_up": [(0, 0, 470, 808), (860, 0, 1331, 640)],
 "s1_ch_floor": [(0, 0, 330, 808), (950, 0, 1331, 808)],
 "s1_cl_s_walk": [(0, 560, 1331, 808), (0, 0, 240, 560), (530, 0, 650, 560)],
 "s1_tw_mid_stair": [(0, 0, 1331, 808)],
 "s1_tw_belfry": [(0, 0, 1331, 808)],
 "s1_cy_s_up": [],
}
def masks(on, off):
    lum_on = on.mean(2); lum_off = off.mean(2)
    white = (on.min(2) > 0.45) & (on[..., 2] >= on[..., 0] - 0.05) & (lum_on - lum_off > 0.25)
    orange = (on[..., 0] > 0.55) & (on[..., 0] - on[..., 2] > 0.35) & (on[..., 1] < 0.85 * on[..., 0]) & (on[..., 1] > 0.25 * on[..., 0]) & ((on[..., 0] - off[..., 0]) > 0.25)
    return white, orange
for p, regs in R.items():
    if not regs: continue
    off1 = L(p, "off1"); off2 = L(p, "off2")
    out = []
    for s in ("onF", "onS", "off2"):
        on = L(p, s)
        w, o = masks(on, off1)
        tw = sum(int(w[y0:y1, x0:x1].sum()) for x0, y0, x1, y1 in regs)
        to = sum(int(o[y0:y1, x0:x1].sum()) for x0, y0, x1, y1 in regs)
        aw = int(w.sum()); ao = int(o.sum())
        out.append(f"{s}: roofed white {tw:5d} orange {to:5d} | whole white {aw:6d} orange {ao:6d}")
    print(p); [print("   ", x) for x in out]
