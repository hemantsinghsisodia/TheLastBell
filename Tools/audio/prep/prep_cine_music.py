"""Cinematic music prep (Phase 17, section 3.4 of Docs/plans/P17_CINEMATICS.md). Deterministic, numpy + ffmpeg only.

  python -I Tools/audio/prep/prep_cine_music.py            # write the three WAVs to SourceArt/Audio/Music/ and print duration and peak
  python -I Tools/audio/prep/prep_cine_music.py --verify   # build twice in memory and compare SHA-256 (writes nothing)

Sources (owner-downloaded Freesound CC0, git-ignored): ExternalAssets/Incoming/audio/p17_music/
  MUS_LB_Cine_IntroText  330599 Dasgoat "the sad piano" (MP3, stereo 44.1 kHz): 0:00-0:40, no baked fade (the sequence fades it), peak -3 dBFS
                         (P17 3.7 / 3.8 / 3.10: the intro music runs to the handover, now at 35.5 s; it was 0:00-0:30 until 3.10)
  MUS_LB_Cine_Finale     610534 szegvari "...surround" (WAV, 5.1, 96 kHz, 24-bit): down-mixed to stereo, resampled to 48 kHz,
                         first 0:55, peak -3 dBFS
  MUS_LB_Cine_Credits    839571 CVLTIV8R "contemplative string loop" (WAV, stereo 44.1 kHz, float): 48 kHz, whole 45 s, peak -3 dBFS
Output: 48 kHz, stereo, 16-bit PCM (prep_lib.write_wav: plain rounding, no dither). The folder is SourceArt/Audio/Music (not Recorded/,
whose report_recorded.py checks flag any WAV that is not in recipes.json); Tools/audio/p16_2_assets.py imports it as a third source.

5.1 down-mix. ffprobe reports the layout "5.1", which in ffmpeg means FL FR FC LFE BL BR (back pair, channels 0..5). The back pair is used as the
surrounds: L = FL + 0.707 FC + 0.707 BL, R = FR + 0.707 FC + 0.707 BR; the LFE (channel 3) is dropped. The 96 -> 48 kHz resample is ffmpeg's.
Raw downloads are untrusted data: decoded by ffmpeg only, never executed; paths are passed as arguments.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np

import prep_lib as L

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SRC = os.path.join(ROOT, "ExternalAssets", "Incoming", "audio", "p17_music")
OUT_DIR = os.path.join(ROOT, "SourceArt", "Audio", "Music")
SR = L.SR
PEAK_DB = -3.0
G = 0.70710678118654752  # 0.707

ITEMS = [
    dict(name="MUS_LB_Cine_IntroText", src="330599__dasgoat__the-sad-piano.mp3", t0=0.0, t1=40.0, fade_out=0.0, downmix=False),
    dict(name="MUS_LB_Cine_Finale", src="610534__szegvari__", t0=0.0, t1=55.0, fade_out=0.0, downmix=True),
    dict(name="MUS_LB_Cine_Credits", src="839571__cvltiv8r__", t0=0.0, t1=None, fade_out=0.0, downmix=False),
]


def resolve(prefix: str) -> str:
    hits = sorted(f for f in os.listdir(SRC) if f.startswith(prefix))
    if len(hits) != 1:
        raise SystemExit("source %s*: %d matches in %s" % (prefix, len(hits), SRC))
    return os.path.join(SRC, hits[0])


def layout(path: str) -> str:
    return subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=channel_layout", "-of", "csv=p=0", path],
                          capture_output=True, text=True, check=True).stdout.strip()


def build_one(it: dict) -> np.ndarray:
    path = resolve(it["src"])
    x = L.decode(path)                      # float64 (n, ch) at 48 kHz
    if it["downmix"]:
        assert x.shape[1] == 6, "expected 6 channels, got %d" % x.shape[1]
        lay = layout(path)
        assert lay.startswith("5.1"), "channel layout %r is not 5.1: choose the equivalent downmix by hand" % lay
        # ffmpeg 5.1 order: FL FR FC LFE BL BR (or SL SR for "5.1(side)"): the last pair is the surround pair either way
        left = x[:, 0] + G * x[:, 2] + G * x[:, 4]
        right = x[:, 1] + G * x[:, 2] + G * x[:, 5]
        x = np.stack([left, right], axis=1)
    elif x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    x = L.slice_s(x, it["t0"], it["t1"])
    if it["fade_out"] > 0:
        x = L.fade(x, 0.0, it["fade_out"])
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
        report[it["name"]] = dict(seconds=round(len(x) / SR, 3), channels=x.shape[1], peak_dbfs=round(L.db(float(np.max(np.abs(q))) / 32768.0), 3),
                                  sha256=hashlib.sha256(wav_bytes(x)).hexdigest())
        if verify:
            y = build_one(it)
            assert hashlib.sha256(wav_bytes(y)).hexdigest() == report[it["name"]]["sha256"], "not deterministic: " + it["name"]
        else:
            L.write_wav(os.path.join(OUT_DIR, it["name"] + ".wav"), x)
    for name, r in report.items():
        print("%-24s %7.3f s  %d ch  peak %.3f dBFS  sha256 %s" % (name, r["seconds"], r["channels"], r["peak_dbfs"], r["sha256"][:16]))
    if verify:
        print("deterministic: OK (nothing written)")
    else:
        with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf8") as fh:
            json.dump(report, fh, indent=1)
        print("wrote %s" % OUT_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
