"""p17_sheet_compose.py -- assembles the P17-3 mask-lift contact sheet from the panels rendered by p17_masklift.py (needs Pillow).

    python -I p17_sheet_compose.py <sheet_meta.json>

Layout: one column per key frame, front view on the top row and side view below (the Warden faces image-right in the side view).
Orthographic, so the guide lines are exact: green = eye height 152 cm, red = 220 cm (the usual door/ceiling reference), blue = 290 cm (Warden height).
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont


def font(sz):
    for f in (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, sz)
    return ImageFont.load_default()


def main():
    meta = json.load(open(sys.argv[1], encoding="utf-8"))
    res, zc, scale = meta["panel"], meta["zc"], meta["scale"]
    panels = meta["panels"]
    labels = []
    for p in panels:
        if p["label"] not in labels:
            labels.append(p["label"])
    pad, head = 8, 40
    W = len(labels) * res + (len(labels) + 1) * pad
    H = 2 * res + 3 * pad + head
    sheet = Image.new("RGB", (W, H), (12, 12, 12))
    d = ImageDraw.Draw(sheet)
    hf, sf = font(22), font(15)
    d.text((pad, 8), meta.get("title", "AN_Warden_MaskLift: key frames, front (top) and side (bottom). Green 152 cm, red 220 cm, blue 290 cm."), fill=(235, 235, 235), font=hf)
    for p in panels:
        col = labels.index(p["label"])
        row = 0 if p["view"] == "front" else 1
        img = Image.open(p["path"]).convert("RGB")
        dd = ImageDraw.Draw(img)
        for hcm, c in ((152, (60, 220, 90)), (220, (230, 60, 60)), (290, (70, 120, 255))):
            y = res / 2 - (hcm / 100.0 - zc) / scale * res
            dd.line([(0, y), (res, y)], fill=c, width=1)
        dd.rectangle([0, 0, res, 22], fill=(20, 20, 20))
        dd.text((5, 3), "%s  frame %d  t=%.2f s  %s" % (p["label"], p["frame"], p["t"], p["view"]), fill=(255, 255, 255), font=sf)
        sheet.paste(img, (pad + col * (res + pad), head + pad + row * (res + pad)))
    os.makedirs(os.path.dirname(meta["out"]), exist_ok=True)
    sheet.save(meta["out"], optimize=True)
    print("wrote", meta["out"], sheet.size)


main()
