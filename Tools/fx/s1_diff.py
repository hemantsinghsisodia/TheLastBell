"""P15 S1: diff images, contact sheet and per-region MAD for the rain occlusion captures. Reads only PNGs (and an optional log); never touches Unreal.

    python -I Tools/fx/s1_diff.py [--dir Docs/ArtTest/fx/s1] [--prefix p15_] [--poses Tools/fx/poses/p15_rain.json]
                                  [--regions Tools/fx/poses/p15_s1_regions.json] [--out-dir DIR] [--log Saved/Logs/TheLastBell.log]

Inputs, per pose of the poses file: <dir>/<prefix><pose>_off1.png, _onF.png, _onS.png, _off2.png (same size).
Writes to --out-dir (default: --dir):
  <prefix><pose>_dF.png   |onF  - off1| x 8, clamped
  <prefix><pose>_dS.png   |onS  - off1| x 8, clamped
  <prefix><pose>_dN.png   |off2 - off1| x 8, clamped (the noise floor)
  s1_sheet.png            one row per pose: off1, onF, onS, dF, dS, dN, each labelled
  s1_mad.md               only if the regions file exists: mean absolute difference (in /255) per region and pair, with the section 5 test
The regions file is {pose: {"roofed": [[x0, y0, x1, y1], ...], "open": [...]}} in pixel rects at the capture resolution.
--log greps the log for ProfileGPU lines that contain GlobalDistanceField and adds their times to s1_mad.md (Q6).
"""
import argparse
import json
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SUFFIXES = ["_off1", "_onF", "_onS", "_off2"]
GAIN = 8
CELL_W = 320
LABEL_H = 16


def load(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)


def amp(a, b):
    """|a - b| x GAIN, clamped to 0..255, as uint8 RGB."""
    return np.clip(np.abs(a - b) * GAIN, 0, 255).astype(np.uint8)


def mad(a, b, rect):
    x0, y0, x1, y1 = [int(v) for v in rect]
    h, w = a.shape[:2]
    x0, x1, y0, y1 = max(0, x0), min(w, x1), max(0, y0), min(h, y1)
    if x1 <= x0 or y1 <= y0:
        return None
    return float(np.abs(a[y0:y1, x0:x1] - b[y0:y1, x0:x1]).mean() / 255.0)


def cell(img, label):
    """A labelled thumbnail: LABEL_H strip on top, image scaled to CELL_W wide."""
    im = Image.fromarray(img) if isinstance(img, np.ndarray) else img
    h = max(1, round(im.height * CELL_W / im.width))
    out = Image.new("RGB", (CELL_W, h + LABEL_H), (24, 24, 24))
    out.paste(im.resize((CELL_W, h), Image.LANCZOS), (0, LABEL_H))
    ImageDraw.Draw(out).text((3, 2), label, fill=(255, 255, 255))
    return out


def gpu_lines(log_path):
    """ProfileGPU lines that contain GlobalDistanceField -> [(ms or None, text)]."""
    out = []
    with open(log_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if "GlobalDistanceField" in line:
                m = re.search(r"([0-9]+\.[0-9]+)\s*ms", line)
                out.append((float(m.group(1)) if m else None, line.strip()[:220]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=os.path.join(ROOT, "Docs", "ArtTest", "fx", "s1"))
    ap.add_argument("--prefix", default="p15_")
    ap.add_argument("--poses", default=os.path.join(ROOT, "Tools", "fx", "poses", "p15_rain.json"))
    ap.add_argument("--regions", default=os.path.join(ROOT, "Tools", "fx", "poses", "p15_s1_regions.json"))
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--log", default=None)
    a = ap.parse_args()
    out_dir = a.out_dir or a.dir
    os.makedirs(out_dir, exist_ok=True)

    poses = list(json.load(open(a.poses, encoding="utf-8")).keys())
    regions = json.load(open(a.regions, encoding="utf-8")) if os.path.exists(a.regions) else None
    print("poses:", len(poses), "| regions file:", "yes" if regions is not None else "no (%s)" % a.regions)

    rows, mad_rows, skipped = [], [], []
    for pose in poses:
        paths = {s: os.path.join(a.dir, a.prefix + pose + s + ".png") for s in SUFFIXES}
        missing = [os.path.basename(p) for p in paths.values() if not os.path.exists(p)]
        if missing:
            skipped.append((pose, "missing " + ", ".join(missing)))
            continue
        im = {s: load(p) for s, p in paths.items()}
        sizes = {s: im[s].shape for s in SUFFIXES}
        if len(set(sizes.values())) != 1:
            skipped.append((pose, "sizes differ: %s" % {k: v[:2] for k, v in sizes.items()}))
            continue
        d = {"dF": amp(im["_onF"], im["_off1"]), "dS": amp(im["_onS"], im["_off1"]), "dN": amp(im["_off2"], im["_off1"])}
        for k, arr in d.items():
            Image.fromarray(arr).save(os.path.join(out_dir, a.prefix + pose + "_" + k + ".png"))
        rows.append([cell(Image.open(paths["_off1"]).convert("RGB"), pose + " off1"), cell(Image.open(paths["_onF"]).convert("RGB"), "onF (fall 20000)"),
                     cell(Image.open(paths["_onS"]).convert("RGB"), "onS (fall 3000)"), cell(d["dF"], "|onF-off1| x8"), cell(d["dS"], "|onS-off1| x8"), cell(d["dN"], "|off2-off1| x8 (noise)")])
        whole = (0, 0, im["_off1"].shape[1], im["_off1"].shape[0])
        print("%-18s whole-frame MAD /255: onF %.4f  onS %.4f  noise %.4f" % (pose, mad(im["_onF"], im["_off1"], whole), mad(im["_onS"], im["_off1"], whole), mad(im["_off2"], im["_off1"], whole)))
        if regions and pose in regions:
            for kind in ("roofed", "open"):
                for i, rect in enumerate(regions[pose].get(kind, [])):
                    mf, ms, mn = mad(im["_onF"], im["_off1"], rect), mad(im["_onS"], im["_off1"], rect), mad(im["_off2"], im["_off1"], rect)
                    if None in (mf, ms, mn):
                        skipped.append((pose, "%s region %d is empty or outside the image: %s" % (kind, i, rect)))
                        continue
                    lim = mn + 1.0 / 255.0
                    mad_rows.append((pose, kind, i, rect, mf, ms, mn, mf <= lim, ms <= lim))

    for pose, why in skipped:
        print("SKIPPED", pose, "-", why)
    if rows:
        wcol = CELL_W
        hrows = [max(c.height for c in r) for r in rows]
        sheet = Image.new("RGB", (wcol * 6, sum(hrows)), (0, 0, 0))
        y = 0
        for r, h in zip(rows, hrows):
            for j, c in enumerate(r):
                sheet.paste(c, (j * wcol, y))
            y += h
        sheet_path = os.path.join(out_dir, "s1_sheet.png")
        sheet.save(sheet_path)
        print("wrote", sheet_path, sheet.size)
    else:
        print("no complete pose (needs _off1, _onF, _onS, _off2 of the same size): no sheet written")

    gpu = gpu_lines(a.log) if a.log else None
    if regions is not None or gpu is not None:
        md = ["# S1 region MAD", "", "Mean absolute difference per region, in /255 (8-bit units divided by 255). Section 5 test: roofed regions pass when MAD(onF vs off1) and MAD(onS vs off1) are <= MAD(off2 vs off1) + 1/255.", ""]
        if regions is not None:
            md += ["| pose | kind | # | rect | MAD onF | MAD onS | MAD noise (off2) | onF <= noise + 1/255 | onS <= noise + 1/255 |", "|---|---|---|---|---|---|---|---|---|"]
            for pose, kind, i, rect, mf, ms, mn, okf, oks in mad_rows:
                tf, ts = ("yes" if okf else "NO", "yes" if oks else "NO") if kind == "roofed" else ("n/a (open: rain expected)",) * 2
                md.append("| %s | %s | %d | %s | %.4f | %.4f | %.4f | %s | %s |" % (pose, kind, i, rect, mf, ms, mn, tf, ts))
            roofed = [r for r in mad_rows if r[1] == "roofed"]
            md += ["", "Roofed regions: %d, onF within the noise limit: %d, onS within the noise limit: %d." % (len(roofed), sum(r[7] for r in roofed), sum(r[8] for r in roofed))]
        if gpu is not None:
            md += ["", "## GlobalDistanceField in the ProfileGPU log (Q6)", ""]
            if gpu:
                md += ["| ms | line |", "|---|---|"] + ["| %s | `%s` |" % ("%.3f" % ms if ms is not None else "?", txt.replace("|", "/")) for ms, txt in gpu]
            else:
                md.append("No ProfileGPU line with GlobalDistanceField in %s." % a.log)
        md_path = os.path.join(out_dir, "s1_mad.md")
        open(md_path, "w", encoding="utf-8", newline="\n").write("\n".join(md) + "\n")
        print("wrote", md_path, "(%d region rows, %d GlobalDistanceField lines)" % (len(mad_rows), len(gpu or [])))
        for pose, kind, i, rect, mf, ms, mn, okf, oks in mad_rows:
            verdict = ("within noise" if okf and oks else "ABOVE NOISE") if kind == "roofed" else "open (rain expected)"
            print("  %-18s %-6s %d  onF %.4f  onS %.4f  noise %.4f  %s" % (pose, kind, i, mf, ms, mn, verdict))
    return 0


if __name__ == "__main__":
    sys.exit(main())
