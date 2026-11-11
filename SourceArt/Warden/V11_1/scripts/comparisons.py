from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
R=Path(__file__).resolve().parents[1]
V=R.parent/"warden_art_v11"/"previews"
P=R/"previews"
font=ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf",34)
def sheet(name,views):
    board=Image.new("RGB",(800*len(views),1028),(27,28,29))
    for i,(path,label) in enumerate(views):
        with Image.open(path) as im:
            board.paste(im.convert("RGB"),(i*800,0))
        ImageDraw.Draw(board).text((800*i+22,972),label,font=font,fill="white")
    board.save(P/name,quality=96,subsampling=0)
for key in ("hand","forearm","opposite-hand"):
    sheet(key+"-comparison.jpg",[(V/f"v11-neutral-{key}.png","V11"),(P/f"v11_1-neutral-{key}.png","V11.1")])
sheet("hands.jpg",[(P/"v11_1-neutral-hand.png","Left hand"),(P/"v11_1-neutral-opposite-hand.png","Right hand")])
