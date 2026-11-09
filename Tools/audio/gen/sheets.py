"""Spectrogram contact sheets (numpy STFT -> PIL) and the audition page for the generated audio."""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import audio_lib as A  # noqa: E402

DOC_DIR = os.path.join(A.ROOT, "Docs", "ArtTest", "audio")
MANIFEST = os.path.join(A.OUT_DIR, "manifest.json")

_ANCHORS = [(0.00, (0, 0, 4)), (0.15, (30, 10, 80)), (0.35, (101, 21, 110)), (0.55, (190, 55, 80)),
            (0.75, (245, 125, 21)), (0.90, (250, 200, 50)), (1.00, (252, 255, 190))]


def _cmap(v):
    v = np.clip(v, 0.0, 1.0)
    xs = [a[0] for a in _ANCHORS]
    out = np.zeros(v.shape + (3,), dtype=np.uint8)
    for c in range(3):
        out[..., c] = np.interp(v, xs, [a[1][c] for a in _ANCHORS])
    return out


def _font(size):
    for p in ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def spectrogram_db(x, width, nfft=4096, fmin=30.0, fmax=20000.0, bands=170):
    """Log-frequency spectrogram, rows = bands (low -> high), cols = `width` time frames, values in dBFS."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 2:
        x = x.mean(axis=1)
    n = x.size
    nfft = min(nfft, A.next_pow2(max(256, n // 4)))
    win = np.hanning(nfft)
    starts = np.linspace(0, max(0, n - nfft), width).astype(int)
    xp = np.pad(x, (0, nfft))
    frames = xp[starts[:, None] + np.arange(nfft)[None, :]] * win[None, :]
    spec = np.abs(np.fft.rfft(frames, axis=1)) * 2.0 / win.sum()
    power = spec ** 2
    df = A.SR / nfft
    edges = np.geomspace(fmin, fmax, bands + 1)
    nb = power.shape[1]
    mat = np.zeros((bands, nb))
    for i in range(bands):
        lo, hi = edges[i] / df, edges[i + 1] / df
        if hi - lo < 1.0:  # sub-bin band: interpolate
            c = 0.5 * (lo + hi)
            k = int(math.floor(c))
            fr = c - k
            mat[i, min(k, nb - 1)] += 1 - fr
            mat[i, min(k + 1, nb - 1)] += fr
        else:
            k0, k1 = int(math.floor(lo)), int(math.ceil(hi))
            mat[i, k0:max(k1, k0 + 1)] = 1.0 / max(1, k1 - k0)
    p = power @ mat.T  # (frames, bands)
    return 10.0 * np.log10(p.T + 1e-14), edges


def panel(x, title, subtitle, w=600, h=210, nfft=4096, range_db=72.0):
    font, small = _font(13), _font(11)
    left, top, bottom, right = 46, 34, 18, 8
    pw, ph = w - left - right, h - top - bottom
    s_db, edges = spectrogram_db(x, pw, nfft=nfft, bands=ph)
    vmax = float(np.percentile(s_db, 99.7))
    img = _cmap((s_db - (vmax - range_db)) / range_db)[::-1]  # high freq at the top
    im = Image.new("RGB", (w, h), (18, 18, 22))
    im.paste(Image.fromarray(img), (left, top))
    d = ImageDraw.Draw(im)
    d.text((left, 3), title, fill=(235, 235, 235), font=font)
    d.text((left, 19), subtitle + "   [color range %.0f..%.0f dBFS/band]" % (vmax - range_db, vmax), fill=(150, 150, 160), font=small)
    fmin, fmax = edges[0], edges[-1]
    for f in (50, 100, 200, 500, 1000, 2000, 5000, 10000):
        if fmin < f < fmax:
            yy = top + ph - int(ph * math.log(f / fmin) / math.log(fmax / fmin))
            d.line([(left - 3, yy), (left, yy)], fill=(200, 200, 200))
            d.line([(left, yy), (left + pw, yy)], fill=(255, 255, 255, 40) if False else (60, 60, 70))
            d.text((2, yy - 6), ("%gk" % (f / 1000)) if f >= 1000 else str(f), fill=(200, 200, 200), font=small)
    dur = (x.shape[0]) / A.SR
    step = next(s for s in (0.5, 1, 2, 5, 10, 15, 20, 30) if dur / s <= 8)
    t = 0.0
    while t <= dur + 1e-6:
        xx = left + int(pw * t / dur)
        d.line([(xx, top + ph), (xx, top + ph + 3)], fill=(200, 200, 200))
        d.text((xx - 6, top + ph + 3), ("%gs" % t), fill=(200, 200, 200), font=small)
        t += step
    return im


def sheet(entries, out_png, cols=2, nfft=4096, out_dir=None):
    out_dir = out_dir or A.OUT_DIR
    pw, ph = 600, 210
    rows = math.ceil(len(entries) / cols)
    im = Image.new("RGB", (cols * pw, rows * ph), (18, 18, 22))
    for i, e in enumerate(entries):
        x = A.read_wav(os.path.join(out_dir, e["file"]))
        sub = "%.2f s  %dch  rms %.1f dBFS  peak %.1f dBFS" % (e["seconds"], e["channels"], e["rms_db"], e["peak_db"])
        nf = e.get("nfft", nfft)
        p = panel(x, e["name"], sub, w=pw, h=ph, nfft=nf)
        im.paste(p, ((i % cols) * pw, (i // cols) * ph))
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    im.save(out_png, optimize=True)


# --------------------------------------------------------------------------------------------------------------------
# manifest and audition page
# --------------------------------------------------------------------------------------------------------------------

GROUP_ORDER = ["rain", "wind", "thunder", "bells", "music", "rooms"]
GROUP_TITLES = {"rain": "Rain", "wind": "Wind", "thunder": "Thunder", "bells": "Bells", "music": "Music", "rooms": "Room tones and drips"}


def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf8") as f:
            return json.load(f)
    return {}


def save_manifest(man):
    with open(MANIFEST, "w", encoding="utf8", newline="\n") as f:
        json.dump(man, f, indent=1, sort_keys=True)
        f.write("\n")


def write_audition(man):
    rel = "../../../SourceArt/Audio/Generated/"
    L = []
    L.append("# Generated audio: audition page (A4)\n")
    L.append("Generated by `Tools/audio/gen/build_all.py` (`python -I Tools/audio/gen/build_all.py --group all`). "
             "Open each WAV on headphones. For every cue decide **keep**, **redo** (say what to change) or **replace** "
             "(with a Freesound CC0 sound). Spectrogram sheets: `gen_<group>.png` next to this page.\n")
    L.append("**How to read the columns.** *RMS* / *Peak* are measured on the written 16-bit file. *Seam* is the loop "
             "wrap: RMS of the first 0.5 s against the last 0.5 s (target under 0.5 dB); *click* is the sample jump at the "
             "wrap divided by the typical sample jump (about 1-3 is normal, above 8 would click). "
             "*Mix gain* is the intended in-game level relative to the file (section 4 'Level' values); every file is "
             "normalised the same way (beds -24 dBFS RMS, one-shots -3 dBFS peak, music -22 dBFS RMS), so "
             "play the bell stages with this offset in mind: stage 1 is meant to be 18 dB quieter than stage 5.\n")
    L.append("Note: dBFS here is digital level, not loudness; turn the volume down before the thunder, the strikes, "
             "the bell stages 4 and 5 and the stings.\n")
    for g in GROUP_ORDER:
        rows = [e for e in man.values() if e["group"] == g]
        if not rows:
            continue
        rows.sort(key=lambda e: e["name"])
        L.append("\n## %s\n" % GROUP_TITLES[g])
        L.append("![spectrograms](gen_%s.png)\n" % g)
        L.append("| File | Length | Ch | RMS dBFS | Peak dBFS | Loop seam | Mix gain | What to listen for | Keep / redo / replace |")
        L.append("|---|---|---|---|---|---|---|---|---|")
        for e in rows:
            seam = ("%+.2f dB, click %.1f" % (e["seam_step_db"], e["seam_click"])) if e["loop"] else "one-shot"
            mix = ("%+.0f dB" % e["mix_gain_db"]) if e.get("mix_gain_db") else "0 dB"
            L.append("| [%s](%s%s) | %.2f s | %d | %.1f | %.1f | %s | %s | %s | |" % (
                e["name"], rel, e["file"], e["seconds"], e["channels"], e["rms_db"], e["peak_db"], seam, mix,
                e["listen"].replace("|", "/"), ))
    with open(os.path.join(DOC_DIR, "audition.md"), "w", encoding="utf8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def build_sheets(group, entries, cols=2, nfft=4096):
    sheet(entries, os.path.join(DOC_DIR, "gen_%s.png" % group), cols=cols, nfft=nfft)
