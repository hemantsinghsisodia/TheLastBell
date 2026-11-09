"""Survey helper used to author recipes.json: for each source prints duration, peak, noise floor, energy segments and writes
a PNG (level envelope on top, spectrogram below, time ticks) so slices can be picked by eye and ear-less metrics.

  python -I Tools/audio/prep/survey.py <out_dir> <file> [<file> ...] [--rel 18] [--gap 0.15]
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from PIL import Image, ImageDraw

import prep_lib as L


def spectrogram_img(x: np.ndarray, w_px: int, h_px: int, fmax: float = 12000.0) -> Image.Image:
    m = L.to_mono(x)[:, 0]
    n = len(m)
    nfft = 1024
    hop = max(64, n // w_px)
    win = np.hanning(nfft)
    cols = []
    for i in range(w_px):
        s = i * n // w_px
        fr = m[s: s + nfft]
        if len(fr) < nfft:
            fr = np.pad(fr, (0, nfft - len(fr)))
        sp = np.abs(np.fft.rfft(fr * win))
        cols.append(20 * np.log10(sp + 1e-9))
    S = np.array(cols).T
    kmax = int(fmax / (L.SR / 2) * S.shape[0])
    S = S[:kmax][::-1]
    S = np.clip((S - (S.max() - 80)) / 80.0, 0, 1)
    img = Image.fromarray((S * 255).astype(np.uint8), "L").resize((w_px, h_px), Image.BILINEAR)
    return img


def make_png(path: str, x: np.ndarray, segs, title: str, w_px: int = 1400) -> None:
    dur = len(x) / L.SR
    env = L.frame_env(x, 0.01)
    H1, H2, M = 110, 160, 24
    img = Image.new("RGB", (w_px, H1 + H2 + M + 20), (20, 20, 24))
    d = ImageDraw.Draw(img)
    # envelope
    xs = np.linspace(0, len(env) - 1, w_px).astype(int)
    for i, k in enumerate(xs):
        v = np.clip((env[k] + 80) / 80.0, 0, 1)
        d.line([(i, H1), (i, H1 - int(v * (H1 - 4)))], fill=(90, 160, 220))
    d.text((4, 2), f"{title}  {dur:.2f}s", fill=(255, 255, 255))
    for (t0, t1, pk, mn) in segs:
        d.rectangle([t0 / dur * w_px, H1 + 2, t1 / dur * w_px, H1 + 8], fill=(240, 180, 40))
    img.paste(spectrogram_img(x, w_px, H2).convert("RGB"), (0, H1 + 10))
    step = 0.5 if dur < 6 else 1.0 if dur < 14 else 2.0 if dur < 40 else 5.0
    t = 0.0
    while t <= dur:
        px = t / dur * w_px
        d.line([(px, H1 + H2 + 10), (px, H1 + H2 + 16)], fill=(255, 255, 255))
        d.text((px + 2, H1 + H2 + 12), f"{t:g}", fill=(255, 255, 255))
        t += step
    img.save(path)


def main() -> None:
    args = sys.argv[1:]
    rel, gap, band, pr = 18.0, 0.15, None, 38.0
    if "--rel" in args:
        i = args.index("--rel"); rel = float(args[i + 1]); del args[i:i + 2]
    if "--gap" in args:
        i = args.index("--gap"); gap = float(args[i + 1]); del args[i:i + 2]
    if "--band" in args:
        i = args.index("--band"); band = (float(args[i + 1]), float(args[i + 2])); del args[i:i + 3]
    if "--pr" in args:
        i = args.index("--pr"); pr = float(args[i + 1]); del args[i:i + 2]
    out_dir, files = args[0], args[1:]
    os.makedirs(out_dir, exist_ok=True)
    for f in files:
        x = L.decode(f)
        xa = L.fft_filter(x, "bp", band, 2) if band else x
        segs, fl = L.find_segments(xa, rel, gap, peak_range_db=pr)
        pk = L.peak(x)
        clip = int((np.abs(x) > 0.999).sum())
        print(f"== {os.path.basename(f)}  {len(x)/L.SR:.2f}s ch={x.shape[1]} peak={L.db(pk):.1f}dB clipped={clip} floor={fl:.1f}dB segs={len(segs)}")
        for (t0, t1, p, m) in segs[:60]:
            print(f"   {t0:7.3f} - {t1:7.3f}  ({t1-t0:5.2f}s)  peak {p:6.1f}  mean {m:6.1f}")
        make_png(os.path.join(out_dir, os.path.splitext(os.path.basename(f))[0][:60] + ".png"), x, segs,
                 os.path.basename(f)[:70])


if __name__ == "__main__":
    main()
