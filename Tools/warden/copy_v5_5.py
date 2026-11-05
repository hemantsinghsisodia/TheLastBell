"""Copy the owner's Warden V5.5 assets into this project (D-091), verifying every file.

V5.5's native assets sit in four version folders of the isolated project: the mesh and clips in
WardenArtV5_5, the skin in WardenArtV5_4, the other materials and textures in WardenArtV5_1, and the
skeleton and physics asset in WardenArtV5. This follows the references from the mesh and clips and copies
exactly what they need. It stops at the skeleton and physics asset, whose only further reference is a preview
mesh (the old V5 mesh), which isn't needed.

Run only while TheLastBell is closed. The source is only read. The files land at their original
/Game/WardenArtV5* paths, so their references stay valid; then, in the editor, delete the old assets
and move these to /Game/LastBell/Characters/Warden/.
"""
import hashlib
import json
import os
import re
import shutil
import sys

SRC = r"C:\Hemant\Prj\Learning\Warden\output\unreal_validation\Content"
REPO = r"C:\Hemant\Prj\Learning\TheLastBell"
DST = os.path.join(REPO, "Content")
REPORT = os.path.join(REPO, "Docs", "ArtTest", "warden", "p12_v5_5_copy.json")
ROOTS = ("WardenArtV5_5/Meshes/SK_Warden", "WardenArtV5_5/Animations/AN_Warden_Idle",
         "WardenArtV5_5/Animations/AN_Warden_Walk", "WardenArtV5_5/Animations/AN_Warden_DoorwayStoop")
STOP = {"WardenArtV5/Meshes/SK_Warden_Skeleton", "WardenArtV5/Meshes/SK_Warden_PhysicsAsset"}
PAT = re.compile(rb"/Game/([A-Za-z0-9_/\-]+)")


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def closure():
    seen, todo = set(), list(ROOTS)
    while todo:
        rel = todo.pop()
        if rel in seen:
            continue
        path = os.path.join(SRC, rel + ".uasset")
        if not os.path.exists(path):
            sys.exit("Missing dependency: " + rel)
        seen.add(rel)
        if rel in STOP:
            continue
        with open(path, "rb") as f:
            head = f.read(600000)
        for m in set(PAT.findall(head)):
            ref = m.decode()
            if ref.startswith("WardenArtV5") and "/Preview/" not in ref:
                todo.append(ref)
    return sorted(seen)


def main():
    files = closure()
    tops = sorted({f.split("/")[0] for f in files})
    wrong = [f for f in files if f.startswith("WardenArtV5/") and f not in STOP]
    if wrong:
        sys.exit("Unexpected old V5 dependencies: %s" % wrong)
    for top in tops:
        if os.path.exists(os.path.join(DST, top)):
            sys.exit("Refusing: Content/%s already exists" % top)
    if "--dry" in sys.argv:
        print(len(files), "files;", {t: sum(f.startswith(t + "/") for f in files) for t in tops})
        print(round(sum(os.path.getsize(os.path.join(SRC, f + ".uasset")) for f in files) / 1048576, 1), "MB")
        return
    rows = []
    for rel in files:
        s, d = os.path.join(SRC, rel + ".uasset"), os.path.join(DST, rel + ".uasset")
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(s, d)
        a, b = md5(s), md5(d)
        if a != b:
            sys.exit(f"MISMATCH {rel}: {a} != {b}")
        rows.append({"file": rel + ".uasset", "bytes": os.path.getsize(d), "md5": b})
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump({"source": SRC, "count": len(rows), "files": rows}, f, indent=1)
    print(f"copied and verified {len(rows)} files, {sum(r['bytes'] for r in rows) / 1048576:.1f} MB")


if __name__ == "__main__":
    main()
