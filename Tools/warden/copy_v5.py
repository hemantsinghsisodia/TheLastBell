"""Copy the owner's Warden Art V5 assets into this project (D-090, P12-4), verifying every file.

Used instead of Unreal's Migrate: the isolated project has its engine plugins off, so it has no
asset list in the Content Browser and no plugin window. Migrate only copies the package files; the
set was checked first to be self-contained, from the same engine build.

Run only while TheLastBell is closed. The source is only read. Then, in the editor, move the assets
to /Game/LastBell/Characters/Warden/.
"""
import hashlib
import json
import os
import shutil
import sys

SRC = r"C:\Hemant\Prj\Learning\Warden\output\unreal_validation\Content\WardenArtV5"
REPO = r"C:\Hemant\Prj\Learning\TheLastBell"
DST = os.path.join(REPO, "Content", "WardenArtV5")
REPORT = os.path.join(REPO, "Docs", "ArtTest", "warden", "p12_v5_copy.json")
FOLDERS = ("Animations", "Materials", "Meshes", "Textures")  # not Preview: nothing here depends on it


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if os.path.exists(DST):
        sys.exit(f"Refusing: {DST} already exists")
    rows = []
    for folder in FOLDERS:
        src_dir = os.path.join(SRC, folder)
        dst_dir = os.path.join(DST, folder)
        os.makedirs(dst_dir)
        for name in sorted(os.listdir(src_dir)):
            s, d = os.path.join(src_dir, name), os.path.join(dst_dir, name)
            shutil.copy2(s, d)
            a, b = md5(s), md5(d)
            if a != b:
                sys.exit(f"MISMATCH {name}: {a} != {b}")
            rows.append({"file": f"{folder}/{name}", "bytes": os.path.getsize(d), "md5": b})
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump({"source": SRC, "count": len(rows), "files": rows}, f, indent=1)
    print(f"copied and verified {len(rows)} files, {sum(r['bytes'] for r in rows) / 1048576:.1f} MB")


if __name__ == "__main__":
    main()
