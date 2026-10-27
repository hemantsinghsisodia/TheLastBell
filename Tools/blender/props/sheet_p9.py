"""sheet_p9.py -- contact sheet helper (Pillow): python sheet_p9.py out.png name1 name2 ... (names without p9_ / .png, read from Docs/ArtTest/crypt)."""
import os, sys
from PIL import Image, ImageDraw
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
D = os.path.join(ROOT, "Docs", "ArtTest", "crypt")
out, names = sys.argv[1], sys.argv[2:]
cols = 2 if len(names) <= 4 else 3
w, h = 800, 450
rows = (len(names) + cols - 1) // cols
S = Image.new("RGB", (cols * w, rows * h))
for i, n in enumerate(names):
    im = Image.open(os.path.join(D, "p9_%s.png" % n)).convert("RGB").resize((w, h))
    ImageDraw.Draw(im).text((8, 6), n, fill=(255, 255, 0))
    S.paste(im, ((i % cols) * w, (i // cols) * h))
S.save(out)
