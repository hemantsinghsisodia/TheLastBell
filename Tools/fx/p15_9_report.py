"""P15-9: leak test (rain on vs off inside roofed rects) and contact sheets for the viewpoint captures. Reads PNGs only; never touches Unreal.

    python -I Tools/fx/p15_9_report.py [--dir Docs/ArtTest/fx/p15_9]

Inputs in --dir: p15_9_<pose>_rest.png (the 16 P14 viewpoints, rain on, flash frozen at 0), p15_9_<pose>_on.png / _off.png (the 10 rain
poses, camera rain on / bRain off; the placed rain columns run in both), p15_9_<pose>_storm.png (flash 0.8 with a held bolt).
Writes: p15_9_leak.md (per roofed pose: white streak pixels in the roofed rects on vs off, and the mean absolute difference in /255;
the plan's test is MAD <= 1/255), p15_9_sheet_rest.png, p15_9_sheet_rain.png (on | off | |on-off| x 8 per pose), p15_9_sheet_storm.png.
The roofed rects are the S1 ones (Tools/fx/s1_leak.py, capture pixels 1331 x 808), judged from the S1 frames.
"""
import argparse
import glob
import json
import os

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ROOFED = {
    "s1_ch_hole_up": [(0, 0, 470, 808), (860, 0, 1331, 640)],
    "s1_ch_floor": [(0, 0, 330, 808), (950, 0, 1331, 808)],
    "s1_cl_s_walk": [(0, 560, 1331, 808), (0, 0, 240, 560), (530, 0, 650, 560)],
    "s1_tw_mid_stair": [(0, 0, 1331, 808)],
}
CELL_W = 440
LABEL_H = 18


def load(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0


def white_mask(on, off):
    return (on.min(2) > 0.45) & (on[..., 2] >= on[..., 0] - 0.05) & (on.mean(2) - off.mean(2) > 0.25)


def cell(img, label):
    w, h = img.size
    im = img.resize((CELL_W, int(h * CELL_W / w)))
    c = Image.new("RGB", (CELL_W, im.size[1] + LABEL_H), (20, 20, 20))
    c.paste(im, (0, LABEL_H))
    ImageDraw.Draw(c).text((4, 3), label, fill=(230, 230, 230))
    return c


def sheet(cells, cols, path):
    if not cells:
        return
    ch = max(c.size[1] for c in cells)
    rows = (len(cells) + cols - 1) // cols
    s = Image.new("RGB", (cols * CELL_W, rows * ch), (0, 0, 0))
    for i, c in enumerate(cells):
        s.paste(c, ((i % cols) * CELL_W, (i // cols) * ch))
    s.save(path)
    print("wrote", os.path.relpath(path, ROOT), s.size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "Docs", "ArtTest", "fx", "p15_9"))
    a = ap.parse_args()
    d = a.dir
    poses_rest = json.load(open(os.path.join(ROOT, "Tools", "lighting", "poses", "p14_viewpoints.json"), encoding="utf-8"))
    poses_rain = json.load(open(os.path.join(ROOT, "Tools", "fx", "poses", "p15_rain.json"), encoding="utf-8"))

    # leak test
    lines = ["# P15-9 leak test (camera rain on vs bRain off; rain columns run in both)", "",
             "| Pose | Roofed rects | White pixels in rects (on) | Whole-frame white (on) | MAD in rects (/255) | Test MAD <= 1 |", "|---|---|---|---|---|---|"]
    for p in poses_rain:
        on_p, off_p = os.path.join(d, "p15_9_%s_on.png" % p), os.path.join(d, "p15_9_%s_off.png" % p)
        if not (os.path.exists(on_p) and os.path.exists(off_p)):
            lines.append("| %s | - | missing capture | | | |" % p)
            continue
        on, off = load(on_p), load(off_p)
        wm = white_mask(on, off)
        regs = ROOFED.get(p, [])
        if regs:
            tw = sum(int(wm[y0:y1, x0:x1].sum()) for x0, y0, x1, y1 in regs)
            diff = np.abs(on - off).mean(2) * 255.0
            n = sum((y1 - y0) * (x1 - x0) for x0, y0, x1, y1 in regs)
            mad = sum(float(diff[y0:y1, x0:x1].sum()) for x0, y0, x1, y1 in regs) / max(n, 1)
            lines.append("| %s | %d | %d | %d | %.3f | %s |" % (p, len(regs), tw, int(wm.sum()), mad, "PASS" if mad <= 1.0 else "FAIL"))
        else:
            lines.append("| %s | none (judged by eye) | - | %d | - | by eye |" % (p, int(wm.sum())))
    md = os.path.join(d, "p15_9_leak.md")
    open(md, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))

    # sheets
    rest = [cell(Image.open(os.path.join(d, "p15_9_%s_rest.png" % p)), p) for p in poses_rest if os.path.exists(os.path.join(d, "p15_9_%s_rest.png" % p))]
    sheet(rest, 4, os.path.join(d, "p15_9_sheet_rest.png"))
    rain = []
    for p in poses_rain:
        on_p, off_p = os.path.join(d, "p15_9_%s_on.png" % p), os.path.join(d, "p15_9_%s_off.png" % p)
        if os.path.exists(on_p) and os.path.exists(off_p):
            on, off = Image.open(on_p).convert("RGB"), Image.open(off_p).convert("RGB")
            dif = Image.fromarray(np.clip(np.abs(load(on_p) - load(off_p)) * 8 * 255, 0, 255).astype(np.uint8))
            rain += [cell(on, p + "  rain on"), cell(off, p + "  rain off"), cell(dif, p + "  |on-off| x8")]
    sheet(rain, 3, os.path.join(d, "p15_9_sheet_rain.png"))
    storm = [cell(Image.open(f), os.path.basename(f)[6:-4]) for f in sorted(glob.glob(os.path.join(d, "p15_9_*_storm.png")))]
    sheet(storm, 3, os.path.join(d, "p15_9_sheet_storm.png"))


if __name__ == "__main__":
    main()
