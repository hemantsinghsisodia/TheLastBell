"""DSP helpers for the recorded-audio prep (Phase 16, task A3).

numpy only (no scipy, so `python -I` works); decoding goes through ffmpeg. All signals are float64 arrays of shape
(n, ch) at SR = 48000 Hz. Input files are untrusted data: they are only read (decoded by ffmpeg), never executed.
"""
from __future__ import annotations

import math
import os
import subprocess
import wave

import numpy as np

SR = 48000
_CACHE: dict[str, np.ndarray] = {}


def db(x: float) -> float:
    return 20.0 * math.log10(max(float(x), 1e-12))


def undb(d: float) -> float:
    return 10.0 ** (d / 20.0)


# ---------------------------------------------------------------------------------------------------------------------
# decoding / writing
# ---------------------------------------------------------------------------------------------------------------------
def probe_channels(path: str) -> int:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=channels",
                          "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout.strip()
    return int(out.split(",")[0])


def decode(path: str) -> np.ndarray:
    """Decode any audio file to float (n, ch) at 48 kHz (ffmpeg resamples). Cached per process."""
    key = os.path.abspath(path)
    if key in _CACHE:
        return _CACHE[key]
    ch = probe_channels(path)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-f", "f32le", "-acodec", "pcm_f32le",
                          "-ar", str(SR), "-ac", str(ch), "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype="<f4").reshape(-1, ch).astype(np.float64)
    _CACHE[key] = x
    return x


def write_wav(path: str, x: np.ndarray) -> None:
    """16-bit PCM, 48 kHz. x is (n,) or (n, ch) in [-1, 1]; plain deterministic rounding, no dither."""
    if x.ndim == 1:
        x = x[:, None]
    q = np.clip(np.round(x * 32767.0), -32768, 32767).astype("<i2")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(q.shape[1])
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(q.tobytes())


def read_wav(path: str) -> np.ndarray:
    with wave.open(path, "rb") as w:
        n, ch = w.getnframes(), w.getnchannels()
        assert w.getsampwidth() == 2 and w.getframerate() == SR
        raw = w.readframes(n)
    return np.frombuffer(raw, dtype="<i2").reshape(-1, ch).astype(np.float64) / 32768.0


# ---------------------------------------------------------------------------------------------------------------------
# basics
# ---------------------------------------------------------------------------------------------------------------------
def to_mono(x: np.ndarray) -> np.ndarray:
    return x.mean(axis=1, keepdims=True) if x.shape[1] > 1 else x


def ensure2d(x: np.ndarray) -> np.ndarray:
    return x[:, None] if x.ndim == 1 else x


def peak(x: np.ndarray) -> float:
    return float(np.max(np.abs(x))) if x.size else 0.0


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x ** 2))) if x.size else 0.0


def slice_s(x: np.ndarray, t0: float, t1) -> np.ndarray:
    a = max(0, int(round(t0 * SR)))
    b = len(x) if t1 is None else min(len(x), int(round(t1 * SR)))
    return x[a:b]


def frame_env(x: np.ndarray, hop_s: float = 0.01) -> np.ndarray:
    """RMS per hop (mono-mixed), in dBFS."""
    m = to_mono(x)[:, 0]
    h = max(1, int(round(hop_s * SR)))
    n = len(m) // h
    if n == 0:
        return np.array([db(rms(m))])
    f = m[: n * h].reshape(n, h)
    return 20.0 * np.log10(np.maximum(np.sqrt((f ** 2).mean(axis=1)), 1e-9))


def fft_filter(x: np.ndarray, kind: str, fc, order: int = 4) -> np.ndarray:
    """Zero-phase Butterworth-magnitude filter in the FFT domain. kind: lp, hp, bp (fc=(lo, hi))."""
    x = ensure2d(x)
    n = len(x)
    nf = 1 << (n + int(SR * 0.05) - 1).bit_length()
    f = np.fft.rfftfreq(nf, 1.0 / SR)
    f[0] = 1e-6
    if kind == "lp":
        h = 1.0 / np.sqrt(1.0 + (f / fc) ** (2 * order))
    elif kind == "hp":
        h = 1.0 / np.sqrt(1.0 + (fc / f) ** (2 * order))
    elif kind == "bp":
        h = (1.0 / np.sqrt(1.0 + (f / fc[1]) ** (2 * order))) * (1.0 / np.sqrt(1.0 + (fc[0] / f) ** (2 * order)))
    else:
        raise ValueError(kind)
    out = np.empty_like(x)
    for c in range(x.shape[1]):
        X = np.fft.rfft(x[:, c], nf)
        out[:, c] = np.fft.irfft(X * h, nf)[:n]
    return out


def resample_ratio(x: np.ndarray, ratio: float) -> np.ndarray:
    """Resample so the length becomes n / ratio (ratio = pitch factor: 0.75 = 25 % lower pitch and 33 % longer).
    FFT resampling with zero padding at both ends (band-limited, no aliasing when ratio < 1)."""
    x = ensure2d(x)
    if abs(ratio - 1.0) < 1e-9:
        return x
    pad = 2048
    xp = np.concatenate([np.zeros((pad, x.shape[1])), x, np.zeros((pad, x.shape[1]))])
    n_in = len(xp)
    n_out = int(round(n_in / ratio))
    out = np.empty((n_out, x.shape[1]))
    for c in range(x.shape[1]):
        X = np.fft.rfft(xp[:, c])
        m = n_out // 2 + 1
        Y = np.zeros(m, dtype=complex)
        k = min(m, len(X))
        Y[:k] = X[:k]
        out[:, c] = np.fft.irfft(Y, n_out) * (n_out / n_in)
    p = int(round(pad / ratio))
    return out[p: len(out) - p]


def fade(x: np.ndarray, fin_s: float, fout_s: float) -> np.ndarray:
    x = x.copy()
    a = min(len(x), int(round(fin_s * SR)))
    b = min(len(x), int(round(fout_s * SR)))
    if a > 0:
        x[:a] *= (0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a))[:, None]
    if b > 0:
        x[len(x) - b:] *= (0.5 + 0.5 * np.cos(np.pi * np.arange(b) / b))[:, None]
    return x


def trim_silence(x: np.ndarray, thresh_db: float = -50.0, pad_s: float = 0.02) -> np.ndarray:
    """Trim leading/trailing samples below thresh_db (1 ms RMS frames), keep pad_s of lead/tail."""
    m = to_mono(x)[:, 0]
    h = SR // 1000
    n = len(m) // h
    if n < 2:
        return x
    env = 20 * np.log10(np.maximum(np.sqrt((m[: n * h].reshape(n, h) ** 2).mean(axis=1)), 1e-9))
    idx = np.nonzero(env > thresh_db)[0]
    if idx.size == 0:
        return x
    a = max(0, idx[0] * h - int(pad_s * SR))
    b = min(len(x), (idx[-1] + 1) * h + int(pad_s * SR))
    return x[a:b]


def room_tail(x: np.ndarray, rt60: float = 0.7, wet_db: float = -15.0, predelay_s: float = 0.012, lp_hz: float = 3500.0,
              seed: int = 7, tail_s=None) -> np.ndarray:
    """Synthetic room tail: exponentially decaying noise IR (unit energy), low-passed, scaled by wet_db relative to the
    dry signal and added to it. The output is longer than the input by tail_s (default rt60)."""
    rng = np.random.default_rng(seed)
    n_ir = int(rt60 * 1.2 * SR)
    t = np.arange(n_ir) / SR
    ir = rng.standard_normal(n_ir) * np.exp(-6.907755 * t / rt60)
    ir = fft_filter(ir, "lp", lp_hz, 2)[:, 0]
    ir = np.concatenate([np.zeros(int(predelay_s * SR)), ir])
    ir /= math.sqrt(np.sum(ir ** 2))
    x = ensure2d(x)
    extra = int(SR * (tail_s if tail_s is not None else rt60))
    n = len(x) + extra
    nf = 1 << (n + len(ir)).bit_length()
    out = np.zeros((n, x.shape[1]))
    H = np.fft.rfft(ir, nf)
    for c in range(x.shape[1]):
        wet = np.fft.irfft(np.fft.rfft(x[:, c], nf) * H, nf)[:n]
        out[: len(x), c] += x[:, c]
        out[:, c] += wet * undb(wet_db)
    return out


def loop_crossfade(seg: np.ndarray, length_s: float, xf_s: float) -> np.ndarray:
    """Seamless loop of `length_s` from seg (which must be at least length_s + xf_s long): equal-power crossfade of the
    head with the audio that follows the loop end, so out[-1] flows straight into out[0]."""
    L = int(round(length_s * SR))
    xf = int(round(xf_s * SR))
    assert len(seg) >= L + xf, f"segment too short: {len(seg)} < {L + xf}"
    w = np.arange(xf) / xf
    a = np.sin(0.5 * np.pi * w)[:, None]
    b = np.cos(0.5 * np.pi * w)[:, None]
    out = seg[:L].copy()
    out[:xf] = seg[:xf] * a + seg[L: L + xf] * b
    return out


def seam_metrics(x: np.ndarray, win_s: float = 0.5):
    """(level step in dB between the first and last `win_s` of the file, click ratio at the wrap)."""
    m = to_mono(x)[:, 0]
    w = int(win_s * SR)
    step = abs(db(rms(m[:w])) - db(rms(m[-w:])))
    jump = abs(m[0] - m[-1])
    typ = np.mean(np.abs(np.diff(m))) + 1e-9
    return step, jump / typ


def dc_offset(x: np.ndarray) -> float:
    return float(np.max(np.abs(x.mean(axis=0))))


def active_rms(x: np.ndarray, gate_db: float = -50.0) -> float:
    """RMS over 10 ms frames above the gate (so silent padding does not drag a one-shot's RMS)."""
    m = to_mono(x)[:, 0]
    h = SR // 100
    n = len(m) // h
    if n == 0:
        return rms(m)
    f = m[: n * h].reshape(n, h)
    e = np.sqrt((f ** 2).mean(axis=1))
    keep = 20 * np.log10(np.maximum(e, 1e-9)) > gate_db
    if not keep.any():
        return rms(m)
    return float(np.sqrt((f[keep] ** 2).mean()))


def max_step_ratio(x: np.ndarray) -> float:
    """Click detector: largest sample-to-sample jump divided by the 99.9th percentile jump (mono mix)."""
    m = to_mono(x)[:, 0]
    d = np.abs(np.diff(m))
    if d.size == 0:
        return 0.0
    return float(d.max() / (np.percentile(d, 99.9) + 1e-9))


# ---------------------------------------------------------------------------------------------------------------------
# segmentation helpers (used to author recipes)
# ---------------------------------------------------------------------------------------------------------------------
def find_segments(x: np.ndarray, rel_db: float = 18.0, min_gap_s: float = 0.15, min_len_s: float = 0.05,
                  hop_s: float = 0.005, floor_db=None, peak_range_db: float = 38.0):
    """Energy segments: frames more than `rel_db` above the noise floor (10th percentile of the frame levels).
    Returns ([(t0, t1, peak_db, mean_db)], floor_db); gaps shorter than min_gap_s are merged."""
    env = frame_env(x, hop_s)
    fl = float(np.percentile(env, 10)) if floor_db is None else floor_db
    on = env > max(fl + rel_db, float(env.max()) - peak_range_db)
    segs = []
    i, n = 0, len(on)
    max_gap = int(round(min_gap_s / hop_s))
    while i < n:
        if not on[i]:
            i += 1
            continue
        j, gap, k = i, 0, i
        while k < n:
            if on[k]:
                j, gap = k, 0
            else:
                gap += 1
                if gap > max_gap:
                    break
            k += 1
        if (j - i + 1) * hop_s >= min_len_s:
            segs.append((round(i * hop_s, 3), round((j + 1) * hop_s, 3), float(env[i: j + 1].max()),
                         float(env[i: j + 1].mean())))
        i = j + 1
    return segs, fl


# ---------------------------------------------------------------------------------------------------------------------
# dynamics
# ---------------------------------------------------------------------------------------------------------------------
def leveller(x: np.ndarray, win_s: float = 0.25, alpha: float = 0.8) -> np.ndarray:
    """Slow level evener: divide by the (box-smoothed RMS envelope) ** alpha, then restore the overall RMS."""
    x = ensure2d(x)
    w = max(1, int(win_s * SR))
    p = np.pad((x ** 2).mean(axis=1), (w, w), mode="edge")
    cs = np.concatenate([[0.0], np.cumsum(p)])
    env = np.sqrt((cs[2 * w + 1: 2 * w + 1 + len(x)] - cs[1: 1 + len(x)]) / (2 * w))[:, None] + 1e-6
    y = x / env ** alpha
    return y * (rms(x) / max(rms(y), 1e-12))


def soft_limit(x: np.ndarray, thr: float = 0.5, ceil: float = 0.89) -> np.ndarray:
    """Smooth ceiling (tanh knee above thr, asymptote ceil): peaks never reach full scale."""
    a = np.abs(x)
    over = a > thr
    y = x.copy()
    y[over] = np.sign(x[over]) * (thr + (ceil - thr) * np.tanh((a[over] - thr) / (ceil - thr)))
    return y
