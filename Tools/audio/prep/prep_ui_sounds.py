"""UI sound prep (Phase 18, task P18-2). Deterministic, numpy + ffmpeg only (the same standard as the P16 recorded audio).

  python -I Tools/audio/prep/prep_ui_sounds.py            # write the four WAVs to SourceArt/Audio/UI/ and print duration and peak
  python -I Tools/audio/prep/prep_ui_sounds.py --verify   # build twice in memory and compare SHA-256 (writes nothing)

Sources (Kenney "Interface Sounds", CC0, via the Calinou GitHub repackaging; git-ignored): ExternalAssets/Incoming/kenney-ui-audio/
The picks are the A1 first choices (docs/ArtTest/ui/p18_a1_assets.md), chosen by measurement, not yet by ear:
  SFX_LB_UI_Hover   click_001   soft thump, 0.11 s
  SFX_LB_UI_Select  select_005  dull, short tail, 0.38 s
  SFX_LB_UI_Back    back_002    dullest of the four back sounds, 0.09 s
  SFX_LB_UI_Tick    tick_004    slider tick, 0.06 s
Processing (P16 standard, section 5.4 of Docs/plans/P16_AUDIO.md): decode and resample to 48 kHz (ffmpeg), mono (channel average), remove DC,
trim silence at -50 dBFS with 5 ms pads, fade in 2 ms and out 20 ms (at most a fifth of the clip), normalise to a -6 dBFS peak (UI sounds sit under the world's -3 dBFS cues),
16-bit rounding, no dither. Output: SourceArt/Audio/UI/SFX_LB_UI_*.wav (LFS), imported by Tools/audio/p16_2_assets.py (rule ^SFX_LB_UI_ -> SCL_LB_UI, 2D).
Raw downloads are untrusted data: decoded by ffmpeg only, never executed; paths are passed as arguments.
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

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SRC = os.path.join(ROOT, "ExternalAssets", "Incoming", "kenney-ui-audio", "extracted_kenney-interface-sounds",
                   "kenney-interface-sounds-master", "addons", "kenney_interface_sounds")
OUT_DIR = os.path.join(ROOT, "SourceArt", "Audio", "UI")
PEAK_DB = -6.0

ITEMS = [
    dict(name="SFX_LB_UI_Hover", src="click_001.wav"),
    dict(name="SFX_LB_UI_Select", src="select_005.wav"),
    dict(name="SFX_LB_UI_Back", src="back_002.wav"),
    dict(name="SFX_LB_UI_Tick", src="tick_004.wav"),
]


def build_one(it: dict) -> np.ndarray:
    x = L.decode(os.path.join(SRC, it["src"]))   # float64 (n, ch) at 48 kHz
    x = L.to_mono(x)
    x = x - float(np.mean(x))                    # DC
    x = L.trim_silence(x, thresh_db=-50.0, pad_s=0.005)
    x = L.fade(x, 0.002, min(0.020, 0.2 * len(x) / L.SR))   # 20 ms out, but at most a fifth of a very short click
    pk = L.peak(x)
    return x * (L.undb(PEAK_DB) / pk)


def wav_bytes(x: np.ndarray) -> bytes:
    return np.clip(np.round(x * 32767.0), -32768, 32767).astype("<i2").tobytes()


def main() -> int:
    verify = "--verify" in sys.argv
    report = {}
    for it in ITEMS:
        x = build_one(it)
        q = np.clip(np.round(x * 32767.0), -32768, 32767)
        report[it["name"]] = dict(source=it["src"], seconds=round(len(x) / L.SR, 3), channels=x.shape[1],
                                  peak_dbfs=round(L.db(float(np.max(np.abs(q))) / 32768.0), 3), sha256=hashlib.sha256(wav_bytes(x)).hexdigest())
        if verify:
            y = build_one(it)
            assert hashlib.sha256(wav_bytes(y)).hexdigest() == report[it["name"]]["sha256"], "not deterministic: " + it["name"]
        else:
            L.write_wav(os.path.join(OUT_DIR, it["name"] + ".wav"), x)
    for name, r in report.items():
        print("%-18s %-14s %6.3f s  %d ch  peak %.3f dBFS  sha256 %s" % (name, r["source"], r["seconds"], r["channels"], r["peak_dbfs"], r["sha256"][:16]))
    if verify:
        print("deterministic: OK (nothing written)")
    else:
        with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf8") as fh:
            json.dump(report, fh, indent=1)
        print("wrote %s" % OUT_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
