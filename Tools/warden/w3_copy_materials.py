"""w3_copy_materials.py -- P17 W3: file-copy the V11.1 native materials and textures into Content/WardenArtV11_1/ (Unreal CLOSED).

    python -I Tools/warden/w3_copy_materials.py

Source: ExternalAssets/Incoming/warden_v11_1/Content/WardenArtV11_1/{Materials,Textures} (extracted and SHA-256-verified in W0).
Left out on purpose: Preview, Meshes, Animations (the plan reimports the mesh and clips in place). The copied packages only reference each other:
this checks that every /Game/ reference inside them points at /Game/WardenArtV11_1/{Materials,Textures}. Every copied file is hashed against its source.
"""
import hashlib
import json
import os
import re
import shutil
import sys

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
SRC = os.path.join(ROOT, "ExternalAssets", "Incoming", "warden_v11_1", "Content", "WardenArtV11_1")
DST = os.path.join(ROOT, "Content", "WardenArtV11_1")
PAT = re.compile(rb"/Game/[A-Za-z0-9_/\-]+")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    rows, bad, foreign = [], [], set()
    for sub in ("Materials", "Textures"):
        os.makedirs(os.path.join(DST, sub), exist_ok=True)
        for fn in sorted(os.listdir(os.path.join(SRC, sub))):
            s, d = os.path.join(SRC, sub, fn), os.path.join(DST, sub, fn)
            shutil.copyfile(s, d)
            hs, hd = sha(s), sha(d)
            if hs != hd:
                bad.append(fn)
            for m in PAT.finditer(open(s, "rb").read()):
                p = m.group().decode()
                if not (p.startswith("/Game/WardenArtV11_1/Materials/") or p.startswith("/Game/WardenArtV11_1/Textures/")):
                    foreign.add((fn, p))
            rows.append({"file": sub + "/" + fn, "bytes": os.path.getsize(d), "sha256": hd})
    rep = {"copied": len(rows), "hash_mismatch": bad, "foreign_references": sorted(foreign), "files": rows}
    out = os.path.join(ROOT, "Docs", "ArtTest", "warden", "w3_copy_materials.json")
    json.dump(rep, open(out, "w"), indent=1)
    print("copied", len(rows), "files; hash mismatches", bad, "; references outside Materials/Textures:", sorted(foreign))
    return 1 if bad or foreign else 0


sys.exit(main())
