"""Recorded lightning cracks for Thunder_Near and Thunder_Strike (Phase 16, P16-5). Deterministic, numpy + ffmpeg only.

  python -I Tools/audio/prep/prep_cracks.py            # write the 4 crack layers (intermediates) + report the cut points
  python -I Tools/audio/prep/prep_cracks.py --diag     # print the level envelope around every detected onset (authoring aid)
  python -I Tools/audio/prep/prep_cracks.py --verify   # build everything twice in memory and compare SHA-256
  python -I Tools/audio/prep/prep_cracks.py --audition # edit the Near/Strike rows of Docs/ArtTest/audio/audition.md in place and add
                                                       # the "Thunder crack layers" section (run after build_all.py --group thunder)

What it does (recipes in `crack_recipes.json`):
  1. Finds the crack ONSET of each Freesound CC0 recording: the first 2 ms frame within the search window that rises above
     `peak + rel_db` (peak = loudest 2 ms frame of the window), then walks back to where that rise began
     (`back_db` below the crossing level, at most `back_max` s earlier).
  2. Cuts from `onset - pre` (10 ms of room tone) to `onset + len`; the end is moved to the quietest 10 ms frame within
     +-`valley` s of that point (a natural short decay, never mid-peak); fade in 3 ms, fade out `fade_out`.
  3. `layers`: the crack only (0.4-0.8 s), peak 1.0, written to SourceArt/Audio/Cracks/SFX_LB_Thunder_CrackLayer_0N.wav
     (-3 dBFS peak, 16-bit) for listening; NOT imported into Unreal.
  4. `strikes`: crack + its own early boom (about 2.8 s), fade out `fade_out`; the final Strike files are written by
     `Tools/audio/gen/thunder.py` (A.finish_oneshot, -3 dBFS peak, mono).
  5. `near`: the recorded crack layer at t = 0 (peak 1.0) over the generated rumble of the same seed (rumble peak 0.85, the
     ratio the synthetic version used); `thunder.py` normalises the mix to -3 dBFS and writes the final Near file.
Raw downloads are untrusted data: decoded by ffmpeg only, never executed.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np

import prep_lib as L
from prep_recorded import resolve_src

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RECIPES = os.path.join(HERE, "crack_recipes.json")
CRACK_DIR = os.path.join(ROOT, "SourceArt", "Audio", "Cracks")
SR = L.SR

_RECIPES = None


def recipes() -> dict:
    global _RECIPES
    if _RECIPES is None:
        _RECIPES = json.load(open(RECIPES, encoding="utf8"))
    return _RECIPES


def source_mono(alias: str) -> np.ndarray:
    """Mono, DC removed, 25 Hz high-passed (the infrasonic bulk of the recordings is of no use and eats headroom)."""
    x = L.to_mono(L.decode(resolve_src(alias)))
    x = x - x.mean(axis=0, keepdims=True)
    return L.fft_filter(x, "hp", 25.0, 2)[:, 0]


def frame_db(x: np.ndarray, hop: int) -> np.ndarray:
    """RMS in dBFS per `hop` samples (non-overlapping)."""
    n = len(x) // hop
    f = x[: n * hop].reshape(n, hop)
    return 20.0 * np.log10(np.maximum(np.sqrt((f ** 2).mean(axis=1)), 1e-9))


def find_onset(x: np.ndarray, rc: dict) -> dict:
    """Crack onset in seconds (see the module docstring), plus the numbers that justify it."""
    hop = SR // 500  # 2 ms
    env = frame_db(x, hop)
    a = int(rc.get("search_from", 0.0) * 500)
    b = int(rc.get("search_to", len(x) / SR) * 500)
    win = env[a:b]
    peak_db = float(win.max())
    cross = a + int(np.argmax(win > peak_db + rc.get("rel_db", -24.0)))
    lvl = env[cross]
    k = cross
    lim = max(a, cross - int(rc.get("back_max", 0.08) * 500))
    while k > lim and env[k - 1] > lvl - rc.get("back_db", 14.0):
        k -= 1
    return {"onset": k * hop / SR, "cross": cross * hop / SR, "peak_db": peak_db, "peak_at": (a + int(np.argmax(win))) * hop / SR,
            "floor_db": float(env[max(0, k - 25): max(1, k - 3)].mean()), "onset_db": float(env[k])}


def cut(x: np.ndarray, rc: dict, length: float, fade_out: float, info: dict) -> np.ndarray:
    """Cut [onset - pre, onset + length], the end moved to the quietest 10 ms frame within +-valley s; fades; DC removed."""
    pre = rc.get("pre", 0.010)
    t0 = max(0.0, info["onset"] - pre)
    end = info["onset"] + length
    v = rc.get("valley", 0.10)
    hop = SR // 100
    env = frame_db(x, hop)
    i0, i1 = int((end - v) * 100), int((end + v) * 100)
    i = i0 + int(np.argmin(env[i0:i1 + 1]))
    t1 = min(len(x) / SR, (i + 1) * hop / SR)
    info["cut_t0"], info["cut_t1"] = t0, t1
    seg = x[int(round(t0 * SR)): int(round(t1 * SR))].copy()
    seg = seg - seg.mean()
    seg = L.fade(seg[:, None], rc.get("fade_in", 0.003), fade_out)[:, 0]
    return seg


def crack_layer(rc: dict):
    """(float signal at peak 1.0, info) for one entry of `layers`."""
    x = source_mono(rc["src"])
    info = find_onset(x, rc)
    seg = cut(x, rc, rc["len"], rc.get("fade_out", 0.09), info)
    info["seconds"] = len(seg) / SR
    info["src"] = rc["src"]
    return seg / max(np.abs(seg).max(), 1e-9), info


def layer_by_name(name: str):
    for rc in recipes()["layers"]:
        if rc["name"] == name:
            return crack_layer(rc)
    raise KeyError(name)


def strike(name: str):
    """(float signal at peak 1.0, info): the crack and its own early boom, cut and faded; thunder.py finishes it."""
    for rc in recipes()["strikes"]:
        if rc["name"] == name:
            x = source_mono(rc["src"])
            info = find_onset(x, rc)
            seg = cut(x, rc, rc["len"], rc["fade_out"], info)
            info["seconds"] = len(seg) / SR
            info["src"] = rc["src"]
            return seg / max(np.abs(seg).max(), 1e-9), info
    raise KeyError(name)


def near_crack(name: str):
    """(crack layer signal at peak 1.0, layer name, seed, info) for one entry of `near`."""
    for rc in recipes()["near"]:
        if rc["name"] == name:
            sig, info = layer_by_name(rc["layer"])
            return sig, rc["layer"], rc["seed"], info
    raise KeyError(name)


def digest(x: np.ndarray) -> str:
    return hashlib.sha256(np.round(x * 32767.0).astype("<i2").tobytes()).hexdigest()[:16]


def build_layers(write: bool = True) -> dict:
    out = {}
    for rc in recipes()["layers"]:
        sig, info = crack_layer(rc)
        out[rc["name"]] = (sig, info)
        if write:
            L.write_wav(os.path.join(CRACK_DIR, rc["name"] + ".wav"), sig * L.undb(-3.0))
        print("  %-30s %-10s onset %.3f s (rose at %.3f, source peak %.1f dB at %.3f s, floor %.1f dB), cut %.3f..%.3f s = %.2f s" % (
            rc["name"], rc["src"], info["onset"], info["cross"], info["peak_db"], info["peak_at"], info["floor_db"],
            info["cut_t0"], info["cut_t1"], info["seconds"]))
    return out


def diag() -> None:
    for kind in ("layers", "strikes"):
        for rc in recipes()[kind]:
            x = source_mono(rc["src"])
            info = find_onset(x, rc)
            hop = SR // 500
            env = frame_db(x, hop)
            k = int(info["onset"] * 500)
            print("%s %s onset %.3f (peak %.1f dB at %.3f)" % (rc["name"], rc["src"], info["onset"], info["peak_db"], info["peak_at"]))
            print("   2 ms env from onset-40ms:", " ".join("%d" % v for v in env[max(0, k - 20): k + 60]))


def audition() -> None:
    """Edit audition.md in place: refresh the Thunder_Near / Thunder_Strike rows from the manifest, and (re)write the
    "Thunder crack layers" section (intermediates in SourceArt/Audio/Cracks, not imported) right after the Thunder table."""
    docs = os.path.join(ROOT, "Docs", "ArtTest", "audio", "audition.md")
    man = json.load(open(os.path.join(ROOT, "SourceArt", "Audio", "Generated", "manifest.json"), encoding="utf8"))
    lines = open(docs, encoding="utf8", newline="").read().splitlines()
    rel = "../../../SourceArt/Audio/Generated/"
    out, skip = [], False
    for ln in lines:
        if ln.startswith("## Thunder crack layers"):
            skip = True
            continue
        if skip and ln.startswith("## "):
            skip = False
        if skip:
            continue
        for name, e in man.items():
            if ("[%s](" % name) in ln and ("Thunder_Near" in name or "Thunder_Strike" in name):
                ln = "| [%s](%s%s) | %.2f s | %d | %.1f | %.1f | one-shot | 0 dB | %s | |" % (
                    name, rel, e["file"], e["seconds"], e["channels"], e["rms_db"], e["peak_db"], e["listen"].replace("|", "/"))
        out.append(ln)
    sec = ["## Thunder crack layers (P16-5)", "",
           "Intermediates (Freesound CC0 cracks cut by `Tools/audio/prep/prep_cracks.py`): the layer laid at t = 0 over the generated rumble of "
           "`SFX_LB_Thunder_Near_01..04`. They are **not imported** into Unreal; listen to them to judge the crack itself.", "",
           "| File | Length | Ch | RMS dBFS | Peak dBFS | Loop seam | Mix gain | What to listen for | Keep / redo / replace |",
           "|---|---|---|---|---|---|---|---|---|"]
    for rc in recipes()["layers"]:
        x = L.read_wav(os.path.join(CRACK_DIR, rc["name"] + ".wav"))
        _, info = crack_layer(rc)
        sec.append("| [%s](../../../SourceArt/Audio/Cracks/%s.wav) | %.2f s | 1 | %.1f | %.1f | one-shot | 0 dB | "
                   "Freesound %s, cut %.3f..%.3f s of the source (onset %.3f s): the tearing crack and a short decay, peak -3 dBFS before mixing. | |" % (
                       rc["name"], rc["name"], len(x) / SR, L.db(L.rms(x)), L.db(L.peak(x)), rc["src"][3:], info["cut_t0"], info["cut_t1"], info["onset"]))
    sec.append("")
    # insert before "## Bells"
    i = next(k for k, ln in enumerate(out) if ln.startswith("## Bells"))
    out[i:i] = sec
    open(docs, "w", encoding="utf8", newline="").write(chr(10).join(out) + chr(10))
    print("audition.md updated")


def main() -> None:
    args = sys.argv[1:]
    if "--audition" in args:
        audition()
        return
    if "--diag" in args:
        diag()
        return
    if "--verify" in args:
        hs = []
        for _ in range(2):
            L._CACHE.clear()
            r = build_layers(write=False)
            hs.append({k: digest(v[0]) for k, v in r.items()})
            hs[-1].update({rc["name"]: digest(strike(rc["name"])[0]) for rc in recipes()["strikes"]})
        print("VERIFY:", "identical" if hs[0] == hs[1] else "MISMATCH", len(hs[0]), "items")
        sys.exit(0 if hs[0] == hs[1] else 1)
    build_layers(write=True)
    for rc in recipes()["strikes"]:
        sig, info = strike(rc["name"])
        print("  %-30s %-10s onset %.3f s, cut %.3f..%.3f s = %.2f s" % (rc["name"], rc["src"], info["onset"], info["cut_t0"], info["cut_t1"], info["seconds"]))


if __name__ == "__main__":
    main()
