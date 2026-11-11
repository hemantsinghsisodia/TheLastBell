"""p17_villager_candle_compose.py -- assembles the contact sheet of p17_villager_candle.py (needs Pillow): python -I p17_villager_candle_compose.py <sheet_meta.json>
One column per frame (4 walk frames and the end idle), rows: front, side, right hand front, right hand side."""
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
    res = meta["panel"]
    panels = meta["panels"]
    cols, rows = [], []
    for p in panels:
        if p["label"] not in cols:
            cols.append(p["label"])
        if p["view"] not in rows:
            rows.append(p["view"])
    pad, head = 6, 36
    W = len(cols) * res + (len(cols) + 1) * pad
    H = len(rows) * res + (len(rows) + 1) * pad + head
    sheet = Image.new("RGB", (W, H), (12, 12, 12))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 8), meta["title"], fill=(235, 235, 235), font=font(18))
    sf = font(14)
    for p in panels:
        c, r = cols.index(p["label"]), rows.index(p["view"])
        img = Image.open(p["path"]).convert("RGB")
        dd = ImageDraw.Draw(img)
        dd.rectangle([0, 0, res, 20], fill=(20, 20, 20))
        dd.text((5, 3), "%s | %s | frame %d | %s" % (p["label"], p["action"], p["frame"], p["view"]), fill=(255, 255, 255), font=sf)
        sheet.paste(img, (pad + c * (res + pad), head + pad + r * (res + pad)))
    os.makedirs(os.path.dirname(meta["out"]), exist_ok=True)
    sheet.save(meta["out"], optimize=True)
    print("wrote", meta["out"], sheet.size)


main()
