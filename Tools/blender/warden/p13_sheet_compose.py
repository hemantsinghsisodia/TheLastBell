"""p13_sheet_compose.py -- assembles the P13-5 contact sheets from the panel PNGs rendered by p13_contact_sheet.py (needs Pillow).

    python -I p13_sheet_compose.py <meta.json> [--keep]
Draws on every panel: a label (clip, percentage and time, view) and the height lines (red 220 cm, blue 290 cm; exact because the cameras are
orthographic: row = res/2 - (h - zc)/scale * res). Writes p13_sheet_<Name>.png (4 columns x 2 rows) and p13_sheet_all.png (50 % frames of every clip,
front and side) into meta["out"]; deletes the panel folder unless --keep.
"""
import json
import os
import shutil
import sys

from PIL import Image, ImageDraw, ImageFont

RED, BLUE = (230, 40, 40), (50, 110, 255)


def font(sz):
    for f in (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, sz)
    return ImageFont.load_default()


def hrow(h_cm, meta, res):
    return res / 2 - (h_cm / 100.0 - meta["zc"]) / meta["scale"] * res


def decorate(img, meta, label):
    """Height lines + label on a copy of the panel (any size: positions scale with the image)."""
    img = img.convert("RGB")
    res = img.size[0]
    d = ImageDraw.Draw(img)
    lw = max(1, round(res / 400))
    fs = max(11, round(res / 38))
    f = font(fs)
    for h, c in ((220, RED), (290, BLUE)):
        y = hrow(h, meta, res)
        d.line([(0, y), (res, y)], fill=c, width=lw)
        d.text((res - fs * 2.3, y - fs - 1), "%d" % h, fill=c, font=f)
    bar = fs + 8
    d.rectangle([0, 0, res, bar], fill=(20, 20, 20))
    d.text((5, 3), label, fill=(255, 255, 255), font=f)
    return img


def main():
    mp = sys.argv[1]
    keep = "--keep" in sys.argv
    meta = json.load(open(mp, encoding="utf-8"))
    out, res = meta["out"], meta["res"]
    pcts = meta["pcts"]
    prefix = meta.get("prefix", "p13")
    hf = font(22)
    for clip in meta["clips"]:
        name = clip["name"]
        W = 4 * res + 5 * 8
        H = 2 * res + 3 * 8 + 38
        sheet = Image.new("RGB", (W, H), (12, 12, 12))
        d = ImageDraw.Draw(sheet)
        d.text((8, 7), "AN_Warden_%s   %.2f s   red line 220 cm, blue line 290 cm, grid 50 cm" % (name, clip["length_s"]), fill=(255, 255, 255), font=hf)
        for p in clip["panels"]:
            col = pcts.index(p["pct"])
            row = 0 if p["view"] == "FRONT" else 1
            im = Image.open(p["file"])
            im = decorate(im, meta, "%s  %d%% (%.2fs)  %s" % (name, p["pct"], p["t"], p["view"]))
            sheet.paste(im, (8 + col * (res + 8), 38 + 8 + row * (res + 8) - 8 + 8))
        fn = os.path.join(out, "%s_sheet_%s.png" % (prefix, name))
        sheet.save(fn)
        print("wrote %s %dx%d" % (fn, sheet.size[0], sheet.size[1]))
    # overview: 50 % frames, front then side, 6 clips per row pair
    clips = meta["clips"]
    cols = 6
    pw = 380
    rows_pairs = (len(clips) + cols - 1) // cols
    W = cols * pw + (cols + 1) * 6
    H = rows_pairs * 2 * pw + (rows_pairs * 2 + 1) * 6 + 34
    sheet = Image.new("RGB", (W, H), (12, 12, 12))
    d = ImageDraw.Draw(sheet)
    d.text((6, 6), "%s clips at 50%%: front (top) and side (below) per row; red line 220 cm, blue line 290 cm, grid 50 cm" % prefix, fill=(255, 255, 255), font=hf)
    for i, clip in enumerate(clips):
        r, c = divmod(i, cols)
        for view, vr in (("FRONT", 0), ("SIDE", 1)):
            p = next(q for q in clip["panels"] if q["view"] == view and q["pct"] == 50)
            im = Image.open(p["file"]).resize((pw, pw), Image.LANCZOS)
            im = decorate(im, meta, "%s %s" % (clip["name"], view))
            sheet.paste(im, (6 + c * (pw + 6), 34 + 6 + (r * 2 + vr) * (pw + 6)))
    fn = os.path.join(out, "%s_sheet_all.png" % prefix)
    sheet.save(fn)
    print("wrote %s %dx%d" % (fn, sheet.size[0], sheet.size[1]))
    if not keep:
        shutil.rmtree(os.path.dirname(mp), ignore_errors=True)


main()
