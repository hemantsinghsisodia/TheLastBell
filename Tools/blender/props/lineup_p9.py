"""lineup_p9.py -- composite lineup of the P9-3 crypt pieces (Pillow, plain python): Docs/ArtTest/crypt/p9_lineup.png

    python Tools/blender/props/lineup_p9.py      (run render_p9.py --set work first; tiles are the main Workbench view of each piece)
"""
import os
from PIL import Image, ImageDraw

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
D = os.path.join(ROOT, "Docs", "ArtTest", "crypt")
TILES = [("bay_3q", "A OssuaryBay"), ("capital", "B Capital_A"), ("stair_3q", "C Stair40"), ("sarcophagus_a", "D Sarcophagus_A"), ("sarcophagus_b", "D Sarcophagus_B"),
         ("bonebin", "E BoneBin"), ("blocks", "F Block_100 / _C"), ("corbel", "G Corbel_A"), ("beam", "H Beam"), ("boards", "I Boards"), ("boards_broken", "I Boards_Broken"),
         ("roots_a", "J RootsHang_A"), ("roots_b", "J RootsHang_B"), ("roots_c", "J RootsHang_C"), ("portcullis", "K Portcullis"), ("rubble_front", "L RubbleFill"),
         ("crank", "M Crank_A"), ("capstan", "N CapstanDrum"), ("plaqueframe_3q", "O PlaqueFrame"), ("winch_3q", "P WinchFrame")]
cols, w, h = 5, 480, 300
rows = (len(TILES) + cols - 1) // cols
S = Image.new("RGB", (cols * w, rows * h), (30, 30, 34))
for i, (n, label) in enumerate(TILES):
    im = Image.open(os.path.join(D, "p9_%s.png" % n)).convert("RGB")
    im = im.crop((0, 0, im.width, im.height)).resize((w, h), Image.LANCZOS)
    ImageDraw.Draw(im).text((8, 6), label, fill=(255, 255, 0))
    S.paste(im, ((i % cols) * w, (i // cols) * h))
S.save(os.path.join(D, "p9_lineup.png"))
print("wrote", os.path.join(D, "p9_lineup.png"))
