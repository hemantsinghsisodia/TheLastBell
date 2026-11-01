"""P11-3a: colour-match parameters for the two joint-free stone wall candidates.

Usage (run with -I):
    python -I Tools/materials/p11_candidate_params.py <B1_colour_map> <B2_colour_map>

For each colour map: load, convert sRGB -> linear, take the mean linear R, G, B,
then compare with the mean linear RGB of T_Medieval_Blocks_03_BC (measured by
the lead):
    raw_c          = medieval_c / candidate_c
    BrightnessMul  = max(raw_c), clamped to 0.5 .. 2.5 (flagged if clamped)
    BaseColorTint  = raw_c / max(raw_c)   (unclamped ratio, largest channel 1.0)

Writes Tools/materials/p11_candidate_params.json next to this script, and
Docs/ArtTest/materials/p11_candidates.png (both colour maps tiled 2x2, side by
side, labelled, at most 2048 px wide).

The folder is taken from the colour map's parent directory (expected name
<provider>-<id>); maps are found by swapping the "_diff_" token in the file name.
Real-world size comes from the Poly Haven info API ("dimensions", millimetres)
and is recorded in the KNOWN table below; unknown ids get null (never guessed).
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

MEDIEVAL = np.array([0.1869, 0.1470, 0.0991])
CLAMP_LO, CLAMP_HI = 0.5, 2.5

# Source metadata, taken from get_asset / https://api.polyhaven.com/info/<id>
# ("dimensions" are in mm there; stored here in cm).
KNOWN = {
    "rock_surface": {"license": "CC0", "real_world_size_cm": 200.0},
    "rock_01": {"license": "CC0", "real_world_size_cm": 150.0},
}

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def srgb_to_linear(a):
    a = a / 255.0
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def rel(p):
    return os.path.relpath(p, REPO).replace("\\", "/")


def describe(role, bc_path):
    bc_path = os.path.abspath(bc_path)
    folder = os.path.dirname(bc_path)
    folder_name = os.path.basename(folder)
    provider, _, asset_id = folder_name.partition("-")
    base = os.path.basename(bc_path)
    if "_diff_" not in base:
        raise SystemExit(f"{base}: expected a '_diff_' colour map name")
    maps = {"bc": bc_path}
    for key, token in (("n_dx", "_nor_dx_"), ("arm", "_arm_")):
        p = os.path.join(folder, base.replace("_diff_", token))
        if not os.path.isfile(p):
            raise SystemExit(f"missing {key} map: {p}")
        maps[key] = p

    img = np.asarray(Image.open(bc_path).convert("RGB"), dtype=np.float64)
    mean = srgb_to_linear(img).reshape(-1, 3).mean(axis=0)
    raw = MEDIEVAL / mean
    mx = float(raw.max())
    mul = min(max(mx, CLAMP_LO), CLAMP_HI)
    tint = raw / mx
    known = KNOWN.get(asset_id, {})
    return {
        "id": f"{provider}:{asset_id}",
        "source_url": f"https://polyhaven.com/a/{asset_id}" if provider == "polyhaven" else None,
        "license": known.get("license"),
        "folder": rel(folder) + "/",
        "maps": {k: rel(v) for k, v in maps.items()},
        "map_size_px": list(Image.open(bc_path).size),
        "mean_linear_rgb": [round(float(x), 5) for x in mean],
        "raw_ratio_medieval_over_candidate": [round(float(x), 5) for x in raw],
        "BrightnessMul": round(mul, 5),
        "BrightnessMul_unclamped": round(mx, 5),
        "BrightnessMul_clamped": bool(abs(mul - mx) > 1e-9),
        "BaseColorTint": [round(float(x), 5) for x in tint],
        "real_world_size_cm": known.get("real_world_size_cm"),
    }, img


def make_preview(entries, images, out_path):
    # Each panel: 2x2 tiling of the colour map. Two panels side by side, 2048 wide max.
    panel = 1000
    gap = 24
    label_h = 44
    W = panel * 2 + gap
    canvas = Image.new("RGB", (W, panel + label_h), (20, 20, 20))
    try:
        font = ImageFont.truetype("arial.ttf", 26)
    except OSError:
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(canvas)
    for i, (role, e, arr) in enumerate(zip(("B1", "B2"), entries, images)):
        im = Image.fromarray(arr.astype(np.uint8))
        w, h = im.size
        tiled = Image.new("RGB", (w * 2, h * 2))
        for x in range(2):
            for y in range(2):
                tiled.paste(im, (x * w, y * h))
        tiled = tiled.resize((panel, panel), Image.LANCZOS)
        x0 = i * (panel + gap)
        canvas.paste(tiled, (x0, label_h))
        draw.text((x0 + 8, 6), f"{role}  {e['id']}  (2x2 tile)", fill=(235, 235, 235), font=font)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    canvas.save(out_path)


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    entries, images = [], []
    for role, p in zip(("B1", "B2"), sys.argv[1:3]):
        e, img = describe(role, p)
        entries.append(e)
        images.append(img)
    out = {"B1": entries[0], "B2": entries[1]}
    json_path = os.path.join(REPO, "Tools", "materials", "p11_candidate_params.json")
    with open(json_path, "w", newline="\n") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    make_preview(entries, images, os.path.join(REPO, "Docs", "ArtTest", "materials", "p11_candidates.png"))
    for role in ("B1", "B2"):
        e = out[role]
        flag = "  (CLAMPED from %.4f)" % e["BrightnessMul_unclamped"] if e["BrightnessMul_clamped"] else ""
        print(role, e["id"], "mean", e["mean_linear_rgb"], "mul", e["BrightnessMul"], flag, "tint", e["BaseColorTint"])
    print("wrote", json_path)


if __name__ == "__main__":
    main()
