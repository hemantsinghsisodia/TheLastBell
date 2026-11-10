"""Rebuild the recorded (K = Kenney, F = Freesound) cues of Phase 16 from recipes.json (task A3).

  python -I Tools/audio/prep/prep_recorded.py                    # build everything -> SourceArt/Audio/Recorded/*.wav + manifest.json
  python -I Tools/audio/prep/prep_recorded.py --only Step_Stone  # build the items whose name contains the text
  python -I Tools/audio/prep/prep_recorded.py --verify           # build twice into temp folders and compare SHA-256
  python -I Tools/audio/prep/prep_recorded.py --tune NAME        # loop-start search for one loop item (prints the best start)

Sources (git-ignored raw downloads) are read from ExternalAssets/Incoming/ and never executed. Every output is deterministic
(no unseeded randomness). Source aliases in recipes.json:
  fs:<id>   ExternalAssets/Incoming/freesound/<id>__*      ki:<name>  ExternalAssets/Incoming/kenney-impact-sounds/extracted/Audio/<name>.ogg
  kr:<name> ExternalAssets/Incoming/kenney-rpg-audio/extracted/Audio/<name>.ogg
"""
from __future__ import annotations

import glob
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np

import prep_lib as L

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
INCOMING = os.path.join(ROOT, "ExternalAssets", "Incoming")
OUT_DIR = os.path.join(ROOT, "SourceArt", "Audio", "Recorded")
RECIPES = os.path.join(HERE, "recipes.json")
SR = L.SR


def resolve_src(alias: str) -> str:
    kind, _, name = alias.partition(":")
    if kind == "fs":
        hits = sorted(glob.glob(os.path.join(INCOMING, "freesound", name + "__*")))
        if len(hits) != 1:
            raise FileNotFoundError(f"freesound id {name}: {len(hits)} matches")
        return hits[0]
    if kind == "ki":
        return os.path.join(INCOMING, "kenney-impact-sounds", "extracted", "Audio", name + ".ogg")
    if kind == "kr":
        return os.path.join(INCOMING, "kenney-rpg-audio", "extracted", "Audio", name + ".ogg")
    raise ValueError(alias)


def glide(x: np.ndarray, p0: float, p1: float) -> np.ndarray:
    """Variable-rate read: pitch factor glides linearly from p0 to p1 over the output (length ~ n / mean(p))."""
    x = L.ensure2d(x)
    n = len(x)
    up = 2
    xu = L.resample_ratio(x, 1.0 / up)  # 2x oversampled for cleaner linear interpolation
    pm = 0.5 * (p0 + p1)
    n_out = int(n / pm)
    p = np.linspace(p0, p1, n_out)
    pos = np.concatenate([[0.0], np.cumsum(p)[:-1]]) * up
    pos = np.clip(pos, 0, len(xu) - 1)
    out = np.empty((n_out, x.shape[1]))
    for c in range(x.shape[1]):
        out[:, c] = np.interp(pos, np.arange(len(xu)), xu[:, c])
    return out


def gain_env(n: int, pts) -> np.ndarray:
    t = np.arange(n) / SR
    tt = [p[0] for p in pts]
    dd = [p[1] for p in pts]
    return L.undb(np.interp(t, tt, dd))[:, None]


def build_layer(lay: dict, ch: int, info: dict) -> np.ndarray:
    if lay.get("synth") == "noise":  # filtered noise bed/hiss (seeded)
        n = int(lay["dur"] * SR)
        rng = np.random.default_rng(int(lay.get("seed", 1)))
        y = rng.standard_normal((n, 1))
        y = L.fft_filter(y, "bp", (lay.get("lo", 800.0), lay.get("hi", 6000.0)), 2)
        y = y / max(L.rms(y), 1e-9) * L.undb(lay.get("gain_db", -20.0))
        y = np.repeat(y, ch, axis=1)
        if lay.get("gain_env"):
            y = y * gain_env(len(y), lay["gain_env"])
        return L.fade(y, lay.get("fade_in", 0.01), lay.get("fade_out", 0.01))
    src = L.decode(resolve_src(lay["src"]))
    seg = L.slice_s(src, lay.get("t0", 0.0), lay.get("t1"))
    info["src_clipped"] = info.get("src_clipped", 0) + int((np.abs(seg) > 0.999).sum())
    if ch == 1:
        seg = L.to_mono(seg)
    elif seg.shape[1] == 1:
        seg = np.repeat(seg, 2, axis=1)
    seg = seg - seg.mean(axis=0, keepdims=True)  # DC
    if lay.get("denoise"):  # spectral-subtraction denoise of the slice (P16-6: tape hiss, field noise); keys of L.spectral_gate
        seg = L.spectral_gate(seg, **lay["denoise"])
    hp = lay.get("hp", 30.0)
    if hp:
        seg = L.fft_filter(seg, "hp", hp, 2)
    if lay.get("lp"):
        seg = L.fft_filter(seg, "lp", lay["lp"], 2)
    if lay.get("pitch", 1.0) != 1.0:
        seg = L.resample_ratio(seg, lay["pitch"])
    if lay.get("glide"):
        seg = glide(seg, *lay["glide"])
    if lay.get("reverse"):
        seg = seg[::-1].copy()
    if lay.get("norm") is not None:  # level the layer (RMS of its active part) before the relative gain_db
        seg = seg * (L.undb(lay["norm"]) / max(L.active_rms(seg), 1e-9))
    if lay.get("gain_env"):
        seg = seg * gain_env(len(seg), lay["gain_env"])
    seg = L.fade(seg, lay.get("fade_in", 0.004), lay.get("fade_out", 0.006))
    seg = seg * L.undb(lay.get("gain_db", 0.0))
    return seg


def render_item(item: dict):
    ch = int(item.get("channels", 1))
    info: dict = {}
    parts = [(float(l.get("delay", 0.0)), build_layer(l, ch, info)) for l in item["layers"]]
    n = max(int(round(d * SR)) + len(s) for d, s in parts)
    mix = np.zeros((n, ch))
    for d, s in parts:
        a = int(round(d * SR))
        mix[a: a + len(s)] += s
    post = item.get("post", {})
    if post.get("sub"):  # low sine sub following the low-passed envelope of the layered mix
        sb = post["sub"]
        env = np.abs(L.fft_filter(L.to_mono(mix), "lp", sb.get("env_lp", 40.0), 2))[:, 0]
        t = np.arange(n) / SR
        f0 = sb.get("freq", 55.0)
        sub = np.sin(2 * np.pi * f0 * t) * env
        sub = sub / max(L.rms(sub), 1e-9) * L.active_rms(mix) * L.undb(sb.get("gain_db", -12.0))
        mix = mix + sub[:, None]
    if post.get("lp"):
        mix = L.fft_filter(mix, "lp", post["lp"], 2)
    if post.get("hp"):
        mix = L.fft_filter(mix, "hp", post["hp"], 2)
    if post.get("level"):
        mix = L.leveller(mix, post["level"].get("win", 0.25), post["level"].get("alpha", 0.8))
    if post.get("gain_env"):
        mix = mix * gain_env(len(mix), post["gain_env"])
    if post.get("tail"):
        tl = post["tail"]
        mix = L.room_tail(mix, tl.get("rt60", 0.6), tl.get("wet_db", -15.0), tl.get("predelay", 0.012),
                          tl.get("lp", 3500.0), int(tl.get("seed", 7)), tl.get("tail_s"))
    tgt = item.get("target", {"mode": "peak", "db": -3.0})
    lp = item.get("loop")
    if lp:
        out = L.loop_crossfade(mix, lp["length"], lp["xf"])
        out = out * L.undb(tgt["db"] - L.db(L.rms(out)))
        for _ in range(2):  # keep peaks under -1 dBFS (soft knee), then restore the RMS target
            if L.peak(out) > 0.8:
                out = L.soft_limit(out)
                out = out * L.undb(tgt["db"] - L.db(L.rms(out)))
    else:
        # one-shot: normalise, trim silence at -50 dBFS (20 ms pads), fade in 5 ms / out 30 ms, normalise again
        out = mix * (L.undb(-3.0) / max(L.peak(mix), 1e-9))
        out = L.trim_silence(out, -50.0, 0.02)
        mx = item.get("max_len")
        if mx and len(out) > int(mx * SR):
            out = out[: int(mx * SR)]
        fi, fo = item.get("fade_in", 0.005), item.get("fade_out", 0.03)
        out = L.fade(out, fi, fo)
        # short transients can keep a small DC after trimming: subtract it through the fade window so the edges stay at zero
        win = L.fade(np.ones_like(out), fi, fo)
        out = out - win * (out.mean(axis=0, keepdims=True) / win.mean(axis=0, keepdims=True))
        out = out * (L.undb(tgt["db"]) / max(L.peak(out), 1e-9))
    return out, info


def tune_loop(item: dict, name: str):
    """Scan the first layer's t0 for the best seam (level step, then click ratio) and print the top candidates."""
    rng_s = item["tune"]
    li = int(rng_s.get("layer", 0))
    res = []
    t0 = rng_s["t0_min"]
    while t0 <= rng_s["t0_max"] + 1e-9:
        it = json.loads(json.dumps(item))
        it["layers"][li]["t0"] = round(t0, 3)
        it["layers"][li]["t1"] = round(t0 + rng_s["src_len"], 3)
        try:
            out, _ = render_item(it)
            step, click = L.seam_metrics(out)
            res.append((step + 0.05 * click, round(t0, 3), step, click))
        except AssertionError:
            pass
        t0 += rng_s.get("step", 0.1)
    res.sort()
    for r in res[:5]:
        print(f"{name}: t0={r[1]:.3f}  seam step {r[2]:.2f} dB  click {r[3]:.2f}")


def build(items, out_dir: str, only: str | None = None):
    os.makedirs(out_dir, exist_ok=True)
    man = {}
    for item in items:
        name = item["name"]
        if only and only not in name:
            continue
        out, info = render_item(item)
        path = os.path.join(out_dir, name + ".wav")
        L.write_wav(path, out)
        man[name] = {"group": item.get("group"), "src": sorted({l.get("src", "synth") for l in item["layers"]}),
                     "channels": int(out.shape[1]), "src_clipped_samples": info.get("src_clipped", 0)}
        print(f"  {name:36s} {len(out)/SR:6.2f}s ch={out.shape[1]}")
    return man


def sha_dir(d: str) -> dict:
    return {f: hashlib.sha256(open(os.path.join(d, f), "rb").read()).hexdigest() for f in sorted(os.listdir(d)) if f.endswith(".wav")}


def main() -> None:
    args = sys.argv[1:]
    items = json.load(open(RECIPES, encoding="utf8"))["items"]
    only = None
    if "--only" in args:
        only = args[args.index("--only") + 1]
    if "--tune" in args:
        nm = args[args.index("--tune") + 1]
        for it in items:
            if it["name"] == nm:
                tune_loop(it, nm)
        return
    if "--verify" in args:
        a, b = tempfile.mkdtemp(), tempfile.mkdtemp()
        try:
            build(items, a, only)
            L._CACHE.clear()
            build(items, b, only)
            ha, hb = sha_dir(a), sha_dir(b)
            bad = [k for k in ha if ha[k] != hb.get(k)]
            print("VERIFY:", "all files identical" if not bad else f"MISMATCH {bad}", f"({len(ha)} files)")
            sys.exit(1 if bad else 0)
        finally:
            shutil.rmtree(a, ignore_errors=True)
            shutil.rmtree(b, ignore_errors=True)
    old = {}
    mpath = os.path.join(OUT_DIR, "manifest.json")
    if os.path.exists(mpath):
        old = json.load(open(mpath, encoding="utf8"))
    man = build(items, OUT_DIR, only)
    old.update(man)
    with open(mpath, "w", encoding="utf8", newline="\n") as f:
        json.dump(old, f, indent=1, sort_keys=True)
    print(f"{len(man)} files written to {OUT_DIR}")


if __name__ == "__main__":
    main()
