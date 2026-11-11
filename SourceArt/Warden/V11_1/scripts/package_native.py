import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops
assert sys.version_info[:3]==(3,14,9)
R=Path(__file__).resolve().parents[1]
U=R.parent/"unreal_validation"
P=R/"previews/unreal"
P.mkdir(exist_ok=True)
files={}
for name in ("import","materials","cloth-update","saved","check","render","dependencies"):
    path=U/f"Reports/{name}-v11_1.json"
    data=json.loads(path.read_text())
    assert data["passed"],data
    files["Verification/"+path.name]=path
dep=json.loads((U/"Reports/dependencies-v11_1.json").read_text())
for pkg in dep["packages"]:
    stem=U/"Content"/pkg.removeprefix("/Game/")
    paths=list(stem.parent.glob(stem.name+".*"))
    assert len([p for p in paths if p.suffix in (".uasset",".umap")])==1,stem
    for p in paths:
        if p.suffix in (".uasset",".umap",".ubulk",".uexp",".uptnl"): files[p.relative_to(U).as_posix()]=p
render=json.loads((U/"Reports/render-v11_1.json").read_text())
assert len(render["images"])==6
font=ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf",32)
for key in ("forearm","hand","opposite-hand"):
    board=Image.new("RGB",(1600,1024),(27,28,29))
    captures=[]
    for i,(tag,label) in enumerate((("v11","V11"),("v11_1","V11.1"))):
        p=U/"Previews/V11_1"/(tag+"-"+key+".png")
        assert str(p) in render["images"]
        copy=P/p.name
        shutil.copy2(p,copy)
        files["Previews/"+copy.name]=copy
        with Image.open(copy) as im:
            frame=im.convert("RGB")
            assert frame.size==(800,960) and max(a[1]-a[0] for a in frame.getextrema())>50
            board.paste(frame,(800*i,0))
            captures.append(frame)
        ImageDraw.Draw(board).text((i*800+20,971),"Unreal   /   "+label,font=font,fill="white")
    assert ImageChops.difference(*captures).getbbox(),key
    result=P/(key+"-comparison.jpg")
    board.save(result,quality=95,subsampling=0)
    files["Previews/"+result.name]=result
readme=R/"Unreal-README.md"
readme.write_text("# Warden V11.1 for Unreal Engine 5.8.3\n\nCopy Content/WardenArtV11_1 into the destination project's Content folder. Keep the folder name. The mesh is WardenArtV11_1/Meshes/SK_Warden and the review map is WardenArtV11_1/Preview/L_Forearm_Review. Three mesh LODs, three animation clips and the revision's materials and textures are included.\n\nThe destination needs the existing shared packages listed below. Unreal Migrate from the isolated project can also collect them.\n\n"+"\n".join("- "+p for p in dep["external_game_packages"])+"\n",encoding="utf-8")
files["README.md"]=readme
def digest(p):
    with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
hashes={n:digest(p) for n,p in files.items()}
target=R/"Warden_V11_1_Unreal_Content.zip"
tmp=target.with_suffix(".partial")
with zipfile.ZipFile(tmp,"w",zipfile.ZIP_DEFLATED,compresslevel=5) as z:
    for n,p in sorted(files.items()): z.write(p,n)
    z.writestr("SHA256.json",json.dumps(hashes,indent=2))
with zipfile.ZipFile(tmp) as z:
    assert z.testzip() is None and json.loads(z.read("SHA256.json"))==hashes
    for name,h in hashes.items():
        with z.open(name) as f: assert hashlib.file_digest(f,"sha256").hexdigest()==h,name
tmp.replace(target)
checksum=digest(target)
target.with_suffix(".sha256").write_text(checksum+"  "+target.name+"\n")
print(target,target.stat().st_size,checksum,len(dep["packages"]))
