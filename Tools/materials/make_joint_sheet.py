"""P11-3d / P11-4a: contact sheets of the wall tests, one row per bay by 3 columns (face-on, grazing, 15 m), labelled.

    python Tools/materials/make_joint_sheet.py                 # Docs/ArtTest/materials/p11_joint_test.png
    python Tools/materials/make_joint_sheet.py --set repeat    # Docs/ArtTest/materials/p11_repeat_test.png
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR = os.path.join(ROOT, "Docs", "ArtTest", "materials")
# set name -> (output file, rows of (file prefix, bay, label))
SETS = {
    "joint": ("p11_joint_test.png", [("p11_jt_", "today", "TODAY: grooves + painted"), ("p11_jt_", "a", "A: no grooves, painted joints"),
                                     ("p11_jt_", "b1", "B1: grooves, rock_surface"), ("p11_jt_", "b2", "B2: grooves, rock_01"),
                                     ("p11_jt_", "b3", "B3: grooves, plain tablet stone")]),
    "repeat": ("p11_repeat_test.png", [("p11_jt_", "today", "TODAY: grooves + painted"), ("p11_jt_", "a", "A: no grooves, original blocks"),
                                       ("p11_rp_", "a1", "A1: even block tone"), ("p11_rp_", "a2", "A2: even tone, stronger macro"),
                                       ("p11_rp_", "a3", "A3: even tone, larger blocks")]),
}
VIEWS = [("face", "3 m, lantern"), ("graze", "grazing, lantern"), ("far", "15 m, moonlight only")]
W, H = 640, 389
LABEL = 150


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=sorted(SETS), default="joint")
    args = ap.parse_args()
    out, rows = SETS[args.set]
    font = ImageFont.truetype("arialbd.ttf", 16)
    sheet = Image.new("RGB", (LABEL + 3 * W, 28 + len(rows) * H), (16, 16, 16))
    d = ImageDraw.Draw(sheet)
    for c, (_, title) in enumerate(VIEWS):
        d.text((LABEL + c * W + 8, 5), title, fill=(255, 255, 255), font=font)
    for r, (prefix, bay, title) in enumerate(rows):
        y = 28 + r * H
        d.multiline_text((8, y + 12), title.replace(": ", ":\n").replace(", ", ",\n"), fill=(255, 220, 90), font=font, spacing=4)
        for c, (view, _) in enumerate(VIEWS):
            im = Image.open(os.path.join(DIR, f"{prefix}{bay}_{view}.png")).convert("RGB").resize((W, H), Image.LANCZOS)
            sheet.paste(im, (LABEL + c * W, y))
    path = os.path.join(DIR, out)
    sheet.save(path)
    print("wrote", path, sheet.size)


if __name__ == "__main__":
    main()
