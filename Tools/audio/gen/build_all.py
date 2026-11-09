"""Rebuild the generated audio.

    python -I Tools/audio/gen/build_all.py --group rain|wind|thunder|bells|music|rooms|all [--no-sheets] [--verify]

Writes SourceArt/Audio/Generated/<cue>.wav, manifest.json, the spectrogram sheets Docs/ArtTest/audio/gen_<group>.png and
the audition page Docs/ArtTest/audio/audition.md. `--verify` builds the group twice into scratch folders and compares
SHA-256 hashes of every WAV (the determinism proof); it writes nothing into the repo.
"""
import argparse
import hashlib
import importlib
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import audio_lib as A  # noqa: E402
import sheets  # noqa: E402

GROUPS = ["rain", "wind", "thunder", "bells", "music", "rooms"]
SHEET_LAYOUT = {  # group: (columns, fft size)
    "rain": (2, 4096), "wind": (2, 4096), "thunder": (3, 4096), "bells": (2, 8192), "music": (2, 4096), "rooms": (3, 2048),
}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def run_group(g, out_dir=None):
    mod = importlib.import_module(g)
    entries = []
    t0 = time.time()
    mod.build(entries, out_dir)
    print("  (%s: %d files, %.1f s)" % (g, len(entries), time.time() - t0))
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="all", help="|".join(GROUPS) + "|all")
    ap.add_argument("--no-sheets", action="store_true")
    ap.add_argument("--verify", action="store_true", help="build twice into scratch folders and compare hashes")
    a = ap.parse_args()
    groups = GROUPS if a.group == "all" else [a.group]
    for g in groups:
        if g not in GROUPS:
            ap.error("unknown group " + g)

    if a.verify:
        ok = True
        for g in groups:
            hashes = []
            for run in (1, 2):
                tmp = tempfile.mkdtemp(prefix="lbaudio_%s_%d_" % (g, run))
                ents = run_group(g, tmp)
                hashes.append({e["file"]: sha(os.path.join(tmp, e["file"])) for e in ents})
                shutil.rmtree(tmp, ignore_errors=True)
            same = hashes[0] == hashes[1]
            ok &= same
            print("VERIFY %-8s %d files: %s" % (g, len(hashes[0]), "IDENTICAL" if same else "DIFFERENT"))
            for k in hashes[0]:
                print("    %s  %s  %s" % (hashes[0][k][:16], hashes[1][k][:16], k))
        sys.exit(0 if ok else 1)

    man = sheets.load_manifest()
    for g in groups:
        entries = run_group(g)
        for k in [k for k, v in man.items() if v["group"] == g]:
            del man[k]
        for e in entries:
            man[e["name"]] = e
        if not a.no_sheets:
            cols, nfft = SHEET_LAYOUT[g]
            sheets.build_sheets(g, entries, cols, nfft)
    sheets.save_manifest(man)
    sheets.write_audition(man)
    print("manifest: %d files" % len(man))


if __name__ == "__main__":
    main()
