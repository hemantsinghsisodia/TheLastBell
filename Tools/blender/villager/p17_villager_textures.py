"""p17_villager_textures.py -- P17-5a-2: the villager's textures (Pillow only: `python -I Tools/blender/villager/p17_villager_textures.py`).

Reads the CC0 Quaternius textures (ExternalAssets/Incoming/villager_quaternius_peasant/: the Male outfits' skin textures in extracted/, the Ranger textures from the
pack's zip, read member by member, never extracted to the repo) and writes SourceArt/Villager/textures/ as 2048 x 2048 PNGs (the 4K originals are far more than a figure
seen from 60 m needs; the project is public, so the repo gets the small ones):
  T_LB_Villager_Ranger_BaseColor.png   x 0.45 on RGB (the owner's "toned dark")      T_LB_Villager_Skin_BaseColor.png   x 0.45 on RGB
  T_LB_Villager_Ranger_Normal.png      T_LB_Villager_Ranger_ORM.png (R occlusion, G roughness, B metallic)
  T_LB_Villager_Skin_Normal.png        T_LB_Villager_Skin_Roughness.png
Deterministic. Raw downloads are untrusted data: decoded by Pillow only.
"""
import io
import json
import os
import sys
import zipfile

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
IN = os.path.join(ROOT, "ExternalAssets", "Incoming", "villager_quaternius_peasant")
ZIP = os.path.join(IN, "Modular Character Outfits - Fantasy[Standard].zip")
ZIP_DIR = "Modular Character Outfits - Fantasy[Standard]/Exports/glTF (Godot-Unreal)/Modular Parts/"
SKIN_DIR = os.path.join(IN, "extracted", "Modular Character Outfits - Fantasy[Standard]", "Exports", "glTF (Godot-Unreal)", "Outfits")
OUT = os.path.join(ROOT, "SourceArt", "Villager", "textures")
SIZE = 2048
DARKEN = 0.45

JOBS = [  # (output name, source ("zip", member) or ("file", name), darken)
    ("T_LB_Villager_Ranger_BaseColor.png", ("zip", "T_Ranger_BaseColor.png"), True),
    ("T_LB_Villager_Ranger_Normal.png", ("zip", "T_Ranger_Normal.png"), False),
    ("T_LB_Villager_Ranger_ORM.png", ("zip", "T_Ranger_ORM.png"), False),
    ("T_LB_Villager_Skin_BaseColor.png", ("file", "T_Regular_Male_Dark_BaseColor.png"), True),
    ("T_LB_Villager_Skin_Normal.png", ("file", "T_Regular_Male_Normal.png"), False),
    ("T_LB_Villager_Skin_Roughness.png", ("file", "T_Regular_Male_Roughness.png"), False),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    report = {}
    zf = zipfile.ZipFile(ZIP)
    for out_name, (kind, name), darken in JOBS:
        if kind == "zip":
            img = Image.open(io.BytesIO(zf.read(ZIP_DIR + name)))
        else:
            img = Image.open(os.path.join(SKIN_DIR, name))
        src_size, mode = img.size, img.mode
        img.load()
        if darken:
            lut = [int(round(i * DARKEN)) for i in range(256)]
            if img.mode in ("RGBA", "LA"):
                bands = img.split()
                keep = bands[-1]
                rgb = Image.merge("RGB", bands[:3]).point(lut * 3)
                img = Image.merge("RGBA", rgb.split() + (keep,))
            else:
                img = img.convert("RGB").point(lut * 3)
        img = img.resize((SIZE, SIZE), Image.LANCZOS)
        path = os.path.join(OUT, out_name)
        img.save(path, optimize=True)
        report[out_name] = {"source": name, "source_size": list(src_size), "mode": mode, "darkened": darken, "bytes": os.path.getsize(path)}
        print("%-38s <- %-36s %s %s -> %dx%d%s  %d bytes" % (out_name, name, src_size, mode, SIZE, SIZE, "  x0.45" if darken else "", report[out_name]["bytes"]))
    with open(os.path.join(OUT, "textures.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
