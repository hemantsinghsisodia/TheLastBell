"""P14-5 Part B: exposure targets per area (Docs/plans/P14_5_APPLY.md, parent plan section 9.3).

    python -I Tools/lighting/area_targets.py <dir> <prefix> [--suffix S] [--chapel-target MEAN] [--json out.json]

Per pose: mean luma and central-40 % mean (x and y 30-70 % of the frame), Y = 0.2126 R + 0.7152 G + 0.0722 B on 8-bit / 255
(the B2 metric of luma_report.py). Per area: the mean over its WIDE poses (owner, 2026-11-08) against the mean target, and every
pose (close-ups too) against the floor.
The chapel's mean target is the chapel mean of the first P14-5 B1 capture +/- 20 %: pass it with --chapel-target.
"""
import argparse
import json
import os

import numpy as np
from PIL import Image

AREAS = {
    "Courtyard": (["cy_west_front_15m", "cy_tall_north_15m", "cy_lantern_gate_3m", "p14_cy_tower_reveal"], (0.04, 0.07), 0.025, "PP_Outdoor_Night"),
    "Chapel": (["ch_tall_east_15m", "ch_candle_altar_3m", "ch_sacristy_3m"], None, 0.030, "PP_Chapel"),
    "Crypt": (["cr_tall_ossuary_15m", "cr_chain_chamber", "cr_torch_t1_3m"], (0.025, 0.05), 0.020, "PP_Crypt"),
    "Cloister": (["cl_tall_north_15m", "cl_lantern_bells_3m", "ps_lantern_joints"], (0.04, 0.07), 0.025, "PP_Cloister"),
    "Tower": (["tw_mid_stair", "tw_belfry", "tw_base"], (0.035, 0.06), 0.025, "PP_Tower"),
}
# Owner's decision (2026-11-08): the mean target is measured on the WIDE views only; the lantern close-ups only need the floor.
WIDE = {
    "Courtyard": ["cy_west_front_15m", "cy_tall_north_15m", "p14_cy_tower_reveal"],
    "Chapel": ["ch_tall_east_15m"],
    "Crypt": ["cr_tall_ossuary_15m"],
    "Cloister": ["cl_tall_north_15m"],
    "Tower": ["tw_mid_stair", "tw_belfry"],
}


def metrics(path):
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    y = a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722
    h, w = y.shape
    c = y[int(h * 0.3):int(h * 0.7), int(w * 0.3):int(w * 0.7)]
    return float(y.mean()), float(c.mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("prefix")
    ap.add_argument("--suffix", default="")
    ap.add_argument("--chapel-target", type=float, default=None)
    ap.add_argument("--json")
    args = ap.parse_args()
    out = {}
    for area, (poses, band, floor, vol) in AREAS.items():
        rows = []
        for p in poses:
            f = os.path.join(args.dir, args.prefix + p + args.suffix + ".png")
            if os.path.exists(f):
                m, c = metrics(f)
                rows.append((p, m, c))
        if not rows:
            continue
        wide = [r for r in rows if r[0] in WIDE[area]]
        if not wide:
            continue
        am = sum(r[1] for r in wide) / len(wide)
        if band is None and args.chapel_target:
            band = (args.chapel_target * 0.8, args.chapel_target * 1.2)
        mean_ok = None if band is None else (band[0] <= am <= band[1])
        tag = "INFO" if mean_ok is None else ("PASS" if mean_ok else ("LOW " if am < band[0] else "HIGH"))
        print(f"{tag} {area:9s} ({vol}) wide-view mean {am:.4f}  target {'-' if band is None else f'{band[0]:.3f}-{band[1]:.3f}'}  "
              f"(wide: {', '.join(r[0] for r in wide)})")
        for p, m, c in rows:
            print(f"     {'ok  ' if c >= floor else 'FLOOR'} {p:22s} mean {m:.4f}  central40 {c:.4f}  (floor {floor})")
        out[area] = {"volume": vol, "mean": am, "band": band, "mean_ok": mean_ok,
                     "poses": {p: {"mean": m, "central40": c, "floor_ok": c >= floor} for p, m, c in rows}}
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
