"""P11-3d: contact sheet of the joint test, 5 rows (bays) by 3 columns (face-on, grazing, 15 m), labelled.

    python Tools/materials/make_joint_sheet.py [--prefix p11_jt_] [--out Docs/ArtTest/materials/p11_joint_test.png]
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR = os.path.join(ROOT, "Docs", "ArtTest", "materials")
BAYS = [("today", "TODAY: grooves + painted joints"), ("a", "A: no grooves, painted joints"), ("b1", "B1: grooves, rock_surface"),
        ("b2", "B2: grooves, rock_01"), ("b3", "B3: grooves, plain tablet stone")]
VIEWS = [("face", "3 m, lantern"), ("graze", "grazing, lantern"), ("far", "15 m, moonlight only")]
W, H = 640, 389
LABEL = 150


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="p11_jt_")
    ap.add_argument("--out", default=os.path.join(DIR, "p11_joint_test.png"))
    args = ap.parse_args()
    font = ImageFont.truetype("arialbd.ttf", 16)
    sheet = Image.new("RGB", (LABEL + 3 * W, 28 + len(BAYS) * H), (16, 16, 16))
    d = ImageDraw.Draw(sheet)
    for c, (_, title) in enumerate(VIEWS):
        d.text((LABEL + c * W + 8, 5), title, fill=(255, 255, 255), font=font)
    for r, (bay, title) in enumerate(BAYS):
        y = 28 + r * H
        d.multiline_text((8, y + 12), title.replace(": ", ":\n").replace(", ", ",\n"), fill=(255, 220, 90), font=font, spacing=4)
        for c, (view, _) in enumerate(VIEWS):
            im = Image.open(os.path.join(DIR, f"{args.prefix}{bay}_{view}.png")).convert("RGB").resize((W, H), Image.LANCZOS)
            sheet.paste(im, (LABEL + c * W, y))
    sheet.save(args.out)
    print("wrote", args.out, sheet.size)


if __name__ == "__main__":
    main()
