"""P14-4: compare two capture sets pose by pose (mean absolute difference in 8-bit units).

    python -I Tools/lighting/compare_sets.py <before_dir> <before_prefix> <after_dir> <after_prefix> [--sheet out.png] [--json out.json]
        [--limit 2.0] [--mask pose:x0,y0,x1,y1 ...]

For every <before_prefix><pose>.png that has a matching <after_prefix><pose>.png:
- the after image is resized to the before image's size if they differ (the viewport size changes between sessions);
- MAD = mean over pixels and RGB of |after - before|, in 0..255 units; also the 99th percentile of the per-pixel RGB mean difference
  and the share of pixels whose difference is over 8/255;
- the mean luma (Rec.709 on sRGB / 255) of each image.
PASS when MAD <= --limit (default 2.0, plan section 7.3). --mask pose:x0,y0,x1,y1 also reports the MAD inside that box (before-image pixels).
--sheet writes one row per pose: before | after | difference x8.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw


def load(path, size=None):
    im = Image.open(path).convert("RGB")
    if size and im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return im


def luma(a):
    return float((a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722).mean() / 255.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("before_dir")
    ap.add_argument("before_prefix")
    ap.add_argument("after_dir")
    ap.add_argument("after_prefix")
    ap.add_argument("--sheet")
    ap.add_argument("--json")
    ap.add_argument("--limit", type=float, default=2.0)
    ap.add_argument("--mask", nargs="*", default=[])
    args = ap.parse_args()

    masks = {}
    for m in args.mask:
        pose, box = m.split(":")
        masks[pose] = [int(v) for v in box.split(",")]

    rows, out = [], []
    names = sorted(f for f in os.listdir(args.before_dir) if f.startswith(args.before_prefix) and f.endswith(".png"))
    for f in names:
        pose = f[len(args.before_prefix):-4]
        after = os.path.join(args.after_dir, args.after_prefix + pose + ".png")
        if not os.path.exists(after):
            print(f"MISSING {pose}")
            continue
        b = load(os.path.join(args.before_dir, f))
        a_raw = Image.open(after)
        a = load(after, b.size)
        ba = np.asarray(b, dtype=np.float32)
        aa = np.asarray(a, dtype=np.float32)
        d = np.abs(aa - ba)
        per_px = d.mean(axis=2)
        r = {
            "pose": pose,
            "mad": round(float(d.mean()), 2),
            "p99": round(float(np.percentile(per_px, 99)), 1),
            "over8": round(float((per_px > 8).mean()), 4),
            "luma_before": round(luma(ba), 4),
            "luma_after": round(luma(aa), 4),
            "size_before": list(b.size),
            "size_after": list(a_raw.size),
        }
        if pose in masks:
            x0, y0, x1, y1 = masks[pose]
            r["mad_mask"] = round(float(d[y0:y1, x0:x1].mean()), 2)
        r["pass"] = r["mad"] <= args.limit
        out.append(r)
        print(f"{'PASS' if r['pass'] else 'DIFF'}  {pose:22s} MAD {r['mad']:6.2f}  p99 {r['p99']:6.1f}  >8: {r['over8']*100:5.1f}%  "
              f"luma {r['luma_before']:.4f} -> {r['luma_after']:.4f}"
              + (f"  mask MAD {r['mad_mask']:.2f}" if "mad_mask" in r else "")
              + ("" if r["size_before"] == r["size_after"] else f"  (resized {r['size_after']} -> {r['size_before']})"))
        if args.sheet:
            diff = Image.fromarray(np.clip(per_px * 8, 0, 255).astype(np.uint8)).convert("RGB")
            rows.append((pose, b, a, diff))

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(out, fh, indent=1)
    if args.sheet and rows:
        w = 420
        h = int(w * rows[0][1].size[1] / rows[0][1].size[0])
        sheet = Image.new("RGB", (w * 3, (h + 18) * len(rows)), (20, 20, 20))
        dr = ImageDraw.Draw(sheet)
        for i, (pose, b, a, diff) in enumerate(rows):
            y = i * (h + 18)
            r = next(x for x in out if x["pose"] == pose)
            dr.text((4, y + 2), f"{pose}   MAD {r['mad']:.2f}   before | after | diff x8", fill=(230, 230, 230))
            for j, im in enumerate((b, a, diff)):
                sheet.paste(im.resize((w, h), Image.LANCZOS), (j * w, y + 18))
        sheet.save(args.sheet)
        print("sheet:", args.sheet)
    print(f"{sum(r['pass'] for r in out)}/{len(out)} within {args.limit}")


if __name__ == "__main__":
    sys.exit(main())
