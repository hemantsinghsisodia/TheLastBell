"""Shared helpers for the procedural audio generators (Phase 16, task A2).

Everything here is numpy-only and deterministic: the same seeds give byte-identical WAVs.
All signals are float64 arrays, shape (n,) for mono or (n, 2) for stereo, at SR = 48000 Hz.
Filters are zero-phase FFT-domain filters (Butterworth or resonant magnitude shapes), so no scipy is needed.
"""
from __future__ import annotations

import math
import os
import wave
import zlib

import numpy as np

SR = 48000
LN1000 = 6.907755278982137  # ln(1000): exp(-LN1000 * t / T60) falls 60 dB in T60 seconds

# --------------------------------------------------------------------------------------------------------------------
# basics
# --------------------------------------------------------------------------------------------------------------------


def rng_for(seed: int) -> np.random.Generator:
    return np.random.default_rng(int(seed))


def db(x: float) -> float:
    return 20.0 * math.log10(max(float(x), 1e-12))


def from_db(d: float) -> float:
    return 10.0 ** (d / 20.0)


def rms(x) -> float:
    x = np.asarray(x, dtype=np.float64)
    return float(np.sqrt(np.mean(np.square(x)))) if x.size else 0.0


def peak(x) -> float:
    x = np.asarray(x, dtype=np.float64)
    return float(np.max(np.abs(x))) if x.size else 0.0


def tvec(n: int) -> np.ndarray:
    return np.arange(n, dtype=np.float64) / SR


def nsamp(seconds: float) -> int:
    return int(round(seconds * SR))


def snap(f: float, period_s: float) -> float:
    """Snap a frequency to a whole number of cycles per `period_s` so a tone loops without a seam."""
    return round(f * period_s) / period_s


def next_pow2(n: int) -> int:
    return 1 << max(int(n - 1).bit_length(), 4)


def stereo(left, right) -> np.ndarray:
    return np.stack([np.asarray(left), np.asarray(right)], axis=1)


def to_stereo(x) -> np.ndarray:
    x = np.asarray(x)
    return x if x.ndim == 2 else np.stack([x, x], axis=1)


# --------------------------------------------------------------------------------------------------------------------
# noise
# --------------------------------------------------------------------------------------------------------------------


def white(rng, n: int) -> np.ndarray:
    return rng.standard_normal(n)


def colored(rng, n: int, beta: float) -> np.ndarray:
    """Noise with a 1/f^beta power spectrum, unit standard deviation. beta 1 = pink, 2 = brown."""
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1.0 / SR)
    f[0] = f[1]
    spec *= f ** (-beta / 2.0)
    spec[0] = 0.0
    y = np.fft.irfft(spec, n)
    return y / (y.std() + 1e-20)


def pink(rng, n: int) -> np.ndarray:
    return colored(rng, n, 1.0)


def brown(rng, n: int) -> np.ndarray:
    return colored(rng, n, 2.0)


def lowband(rng, n: int, flo: float, fhi: float) -> np.ndarray:
    """Slow smooth random curve with energy only in [flo, fhi] Hz, scaled so its peak is exactly +-1."""
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1.0 / SR)
    spec[(f < flo) | (f > fhi)] = 0.0
    y = np.fft.irfft(spec, n)
    return y / (np.max(np.abs(y)) + 1e-20)


def walk_db(rng, n: int, flo: float, fhi: float, depth_db: float) -> np.ndarray:
    """Linear gain curve drifting +-depth_db on a band-limited random walk."""
    return 10.0 ** (depth_db * lowband(rng, n, flo, fhi) / 20.0)


def walk_frac(rng, n: int, flo: float, fhi: float, frac: float) -> np.ndarray:
    """Multiplier curve drifting +-frac around 1 (e.g. frac 0.3 = +-30 %)."""
    return 1.0 + frac * lowband(rng, n, flo, fhi)


# --------------------------------------------------------------------------------------------------------------------
# filters (zero phase, FFT domain)
# --------------------------------------------------------------------------------------------------------------------


def _apply_mag(x, mag_fn, pad: int = SR) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    n = x.shape[0]
    big = next_pow2(n + pad)
    spec = np.fft.rfft(x, big, axis=0)
    f = np.fft.rfftfreq(big, 1.0 / SR)
    m = mag_fn(f)
    if x.ndim == 2:
        m = m[:, None]
    return np.fft.irfft(spec * m, big, axis=0)[:n]


def _lp_mag(f, fc, order):
    return 1.0 / np.sqrt(1.0 + (f / fc) ** (2 * order))


def _hp_mag(f, fc, order):
    with np.errstate(divide="ignore"):
        r = np.where(f > 0, (fc / np.maximum(f, 1e-9)) ** (2 * order), np.inf)
    return 1.0 / np.sqrt(1.0 + r)


def lowpass(x, fc: float, order: int = 4, pad: int = SR):
    return _apply_mag(x, lambda f: _lp_mag(f, fc, order), pad)


def highpass(x, fc: float, order: int = 4, pad: int = SR):
    return _apply_mag(x, lambda f: _hp_mag(f, fc, order), pad)


def bandpass(x, lo: float, hi: float, order: int = 4, pad: int = SR):
    """Butterworth-shaped band-pass (high-pass at lo times low-pass at hi), `order` per side."""
    return _apply_mag(x, lambda f: _hp_mag(f, lo, order) * _lp_mag(f, hi, order), pad)


def resonant_bp(x, fc: float, q: float, pad: int = SR):
    """Fixed resonant band-pass, 2nd-order magnitude, -3 dB bandwidth fc / q, unity gain at fc."""

    def m(f):
        ff = np.maximum(f, 1e-6)
        return 1.0 / np.sqrt(1.0 + (q * (ff / fc - fc / ff)) ** 2)

    return _apply_mag(x, m, pad)


def tv_resonant_bp(x, fc, q, block: int = 4096, hop: int = 1024) -> np.ndarray:
    """Time-varying resonant band-pass for a 1-D signal. `fc` and `q` are scalars or per-sample arrays.

    Overlap-add of Hann-windowed frames, each filtered by the resonant magnitude at that frame's centre. Zero phase.
    """
    x = np.asarray(x, dtype=np.float64)
    n = x.size
    fc = np.broadcast_to(np.asarray(fc, dtype=np.float64), (n,))
    q = np.broadcast_to(np.asarray(q, dtype=np.float64), (n,))
    lead = block - hop
    nframes = (n + lead) // hop + 1
    xp = np.zeros(lead + n + block + hop)
    xp[lead:lead + n] = x
    win = 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(block) / block)
    f = np.maximum(np.fft.rfftfreq(block, 1.0 / SR), 1e-6)
    out = np.zeros_like(xp)
    chunk = 128
    for k0 in range(0, nframes, chunk):
        ks = np.arange(k0, min(k0 + chunk, nframes))
        starts = ks * hop
        frames = xp[starts[:, None] + np.arange(block)[None, :]] * win[None, :]
        spec = np.fft.rfft(frames, axis=1)
        centre = np.clip(starts + block // 2 - lead, 0, n - 1)
        f0 = fc[centre][:, None]
        qq = q[centre][:, None]
        spec *= 1.0 / np.sqrt(1.0 + (qq * (f[None, :] / f0 - f0 / f[None, :])) ** 2)
        back = np.fft.irfft(spec, block, axis=1)
        for i, s in enumerate(starts):
            out[s:s + block] += back[i]
    return out[lead:lead + n] / 2.0  # Hann at 75 % overlap sums to 2


# --------------------------------------------------------------------------------------------------------------------
# envelopes and shaping
# --------------------------------------------------------------------------------------------------------------------


def exp_decay(n: int, t60: float) -> np.ndarray:
    return np.exp(-LN1000 * tvec(n) / t60)


def rise(n: int, seconds: float, power: float = 1.0) -> np.ndarray:
    """0 -> 1 raised-cosine attack over `seconds`, then 1."""
    m = max(1, nsamp(seconds))
    e = np.ones(n)
    k = min(m, n)
    e[:k] = (0.5 - 0.5 * np.cos(np.pi * np.arange(k) / m)) ** power
    return e


def fade_edges(x, fade_in_s: float, fade_out_s: float) -> np.ndarray:
    x = np.array(x, dtype=np.float64)
    n = x.shape[0]
    a = min(nsamp(fade_in_s), n)
    b = min(nsamp(fade_out_s), n)
    if a > 0:
        w = 0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a)
        x[:a] *= w[:, None] if x.ndim == 2 else w
    if b > 0:
        w = 0.5 + 0.5 * np.cos(np.pi * np.arange(b) / b)
        x[n - b:] *= w[:, None] if x.ndim == 2 else w
    return x


def soft_clip(x, drive: float = 1.0, bias: float = 0.0) -> np.ndarray:
    """Asymmetric tanh soft clip. The input is peak-normalised first so `drive` means the same at every level."""
    x = np.asarray(x, dtype=np.float64)
    xn = x / (np.max(np.abs(x)) + 1e-20)
    y = np.tanh(drive * xn + bias) - np.tanh(bias)
    return y - np.mean(y)


def add_at(dest: np.ndarray, src: np.ndarray, start: int, gain: float = 1.0, circular: bool = False) -> None:
    """dest[start:start+len(src)] += gain * src, truncated at the end, or wrapped around when circular."""
    n = dest.shape[0]
    m = src.shape[0]
    if circular:
        idx = (start + np.arange(m)) % n
        if m <= n:
            dest[idx] += gain * src
        else:
            np.add.at(dest, idx, gain * src)
        return
    if start >= n or start + m <= 0:
        return
    s0 = max(0, -start)
    s1 = min(m, n - start)
    dest[start + s0:start + s1] += gain * src[s0:s1]


def put(dest: np.ndarray, src: np.ndarray, seconds: float, gain: float = 1.0, circular: bool = False) -> None:
    add_at(dest, src, nsamp(seconds), gain, circular)


# --------------------------------------------------------------------------------------------------------------------
# synthetic reverb
# --------------------------------------------------------------------------------------------------------------------


def synth_ir(rng, t60: float, predelay: float = 0.02, damping=(1.0, 0.7, 0.4), xover=(600.0, 2500.0)) -> np.ndarray:
    """Exponential-decay noise impulse response with frequency-dependent decay (low / mid / high band T60 multipliers).

    Unit energy, so convolving noise with it keeps the RMS about the same.
    """
    n = nsamp(t60 * 1.15)
    noise = rng.standard_normal(n)
    lo = lowpass(noise, xover[0], 2, pad=n)
    mid = bandpass(noise, xover[0], xover[1], 2, pad=n)
    hi = highpass(noise, xover[1], 2, pad=n)
    ir = np.zeros(n)
    for band, mult in zip((lo, mid, hi), damping):
        ir += band * exp_decay(n, t60 * mult)
    ir *= rise(n, 0.004)
    ir = np.concatenate([np.zeros(nsamp(predelay)), ir])
    return ir / math.sqrt(float(np.sum(ir * ir)) + 1e-20)


def convolve(x: np.ndarray, ir: np.ndarray) -> np.ndarray:
    """Full FFT convolution of a 1-D signal; the result is len(x) + len(ir) - 1 long."""
    big = next_pow2(x.shape[0] + ir.shape[0])
    y = np.fft.irfft(np.fft.rfft(x, big) * np.fft.rfft(ir, big), big)
    return y[:x.shape[0] + ir.shape[0] - 1]


def reverb(x, ir, wet_db: float, dry_db: float = 0.0, out_len: int | None = None) -> np.ndarray:
    """dry + wet reverb of a 1-D signal; `out_len` (default len(x)) lets the tail ring past the end of the input."""
    x = np.asarray(x, dtype=np.float64)
    n = out_len or x.shape[0]
    wet = convolve(x, ir)
    out = np.zeros(n)
    m = min(n, wet.shape[0])
    out[:m] += from_db(wet_db) * wet[:m]
    k = min(n, x.shape[0])
    out[:k] += from_db(dry_db) * x[:k]
    return out


# --------------------------------------------------------------------------------------------------------------------
# bursts / transients
# --------------------------------------------------------------------------------------------------------------------


def poisson_bursts(rng, n: int, rate: float, f_range, dur_range, mean_amp: float, amp_cap: float = 6.0,
                   freq_log: bool = True) -> np.ndarray:
    """Poisson train of exponentially decaying sine bursts (a drop / patter texture).

    rate: events per second; f_range / dur_range: (lo, hi) uniform; burst amplitude ~ Exponential(mean_amp), capped.
    The burst length is the 60 dB decay time, so `dur` of 2-6 ms means a 2-6 ms T60.
    """
    out = np.zeros(n)
    count = int(rng.poisson(rate * n / SR))
    pos = rng.integers(0, n, count)
    if freq_log:
        freqs = np.exp(rng.uniform(math.log(f_range[0]), math.log(f_range[1]), count))
    else:
        freqs = rng.uniform(f_range[0], f_range[1], count)
    durs = rng.uniform(dur_range[0], dur_range[1], count)
    amps = np.minimum(rng.exponential(mean_amp, count), amp_cap * mean_amp)
    sign = rng.choice([-1.0, 1.0], count)
    phase = rng.uniform(0, 2 * np.pi, count)
    for p, f, d, a, s, ph in zip(pos, freqs, durs, amps, sign, phase):
        m = int(d * SR)
        if m < 2:
            continue
        t = np.arange(m) / SR
        burst = np.sin(2 * np.pi * f * t + ph) * np.exp(-LN1000 * t / d) * (1.0 - np.exp(-t / 0.0002))
        end = min(n, p + m)
        out[p:end] += s * a * burst[:end - p]
    return out


def stft_stats_ok(x) -> bool:
    return bool(np.all(np.isfinite(x)))


# --------------------------------------------------------------------------------------------------------------------
# loops
# --------------------------------------------------------------------------------------------------------------------


def fold_loop(x: np.ndarray, length: int) -> np.ndarray:
    """Equal-power loop crossfade: x is `length + X` samples long; the extra X-sample tail is folded into the start.

    out[i] = x[i] sin(theta) + x[length + i] cos(theta), theta rising 0 -> pi/2 over X. At the seam out[0] == x[length],
    the true continuation of x[length - 1], so the loop is sample-continuous.
    """
    x = np.asarray(x, dtype=np.float64)
    extra = x.shape[0] - length
    assert extra > 0
    th = (np.arange(extra) / extra) * (np.pi / 2.0)
    s, c = np.sin(th), np.cos(th)
    if x.ndim == 2:
        s, c = s[:, None], c[:, None]
    out = x[:length].copy()
    out[:extra] = x[:extra] * s + x[length:length + extra] * c
    return out


def seam_step_db(x, win_s: float = 0.5) -> float:
    """RMS of the first `win_s` of the loop against the last `win_s` (what the player hears across the wrap), in dB."""
    w = nsamp(win_s)
    a = rms(x[-w:])
    b = rms(x[:w])
    return db(b) - db(a)


def seam_interior_stats(x, win_s: float = 0.5, points: int = 64):
    """Same one-sided window step at interior points, for context: (median |step|, max |step|) in dB."""
    w = nsamp(win_s)
    n = x.shape[0]
    pos = np.linspace(w, n - w, points).astype(int)
    steps = [abs(db(rms(x[p:p + w])) - db(rms(x[p - w:p]))) for p in pos]
    return float(np.median(steps)), float(np.max(steps))


def seam_click_ratio(x) -> float:
    """Sample jump across the wrap divided by the typical sample-to-sample jump. About 1-3 is normal; > 8 is a click."""
    x = np.asarray(x)
    if x.ndim == 1:
        x = x[:, None]
    jump = np.max(np.abs(x[0] - x[-1]))
    typ = np.sqrt(np.mean(np.square(np.diff(x, axis=0)))) + 1e-12
    return float(jump / typ)


def make_loop(render, seeds, length_s: float, level_db: float, extra_s: float = 2.0, max_step_db: float = 0.5,
              ceiling_db: float = -1.0):
    """Render `length + extra_s`, fold, normalise to `level_db` RMS and gate on the seam check.

    `render(seed, n)` must return a signal of n samples. Tries each seed in order and keeps the first whose seam step is
    below max_step_db (else the best). Returns (signal, info dict).
    """
    length = nsamp(length_s)
    best = None
    for seed in seeds:
        x = fold_loop(render(seed, length + nsamp(extra_s)), length)
        x = remove_dc(x)
        x = normalize_rms(x, level_db, ceiling_db)
        step = seam_step_db(x)
        if best is None or abs(step) < abs(best[1]):
            best = (x, step, seed)
        if abs(step) < max_step_db:
            break
    x, step, seed = best
    med, mx = seam_interior_stats(x)
    return x, {"seed": int(seed), "seam_step_db": step, "seam_click": seam_click_ratio(x),
               "interior_median_db": med, "interior_max_db": mx}


# --------------------------------------------------------------------------------------------------------------------
# normalisation and file output
# --------------------------------------------------------------------------------------------------------------------


def remove_dc(x):
    return x - np.mean(x, axis=0, keepdims=True)


def normalize_peak(x, target_db: float = -3.0):
    return x * (from_db(target_db) / (peak(x) + 1e-20))


def normalize_rms(x, target_db: float, ceiling_db: float = -1.0):
    """Scale to `target_db` RMS (over the whole signal). If that would exceed the peak ceiling, soft-limit and retry."""
    x = np.asarray(x, dtype=np.float64)
    ceil = from_db(ceiling_db)
    for _ in range(6):
        x = x * (from_db(target_db) / (rms(x) + 1e-20))
        if peak(x) <= ceil:
            return x
        x = ceil * np.tanh(x / ceil)
    return x


def finish_oneshot(x, peak_db: float = -3.0, fade_in_s: float = 0.002, fade_out_s: float = 0.05):
    """Remove DC with a 10 Hz zero-phase high-pass (a mean subtraction would add a step to sparse one-shots), fade the
    edges to zero and normalise to the one-shot peak target."""
    x = highpass(np.asarray(x, dtype=np.float64), 10.0, 2, pad=SR)
    x = fade_edges(x, fade_in_s, fade_out_s)
    return normalize_peak(x, peak_db)


def write_wav(path: str, x, name: str | None = None) -> None:
    """16-bit PCM WAV at 48 kHz with seeded TPDF dither (so a rebuild is byte-identical)."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = x[:, None]
    gen = np.random.default_rng(zlib.crc32((name or os.path.basename(path)).encode()))
    dither = gen.random(x.shape) - gen.random(x.shape)
    y = np.clip(np.rint(x * 32767.0 + dither), -32768, 32767).astype("<i2")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(x.shape[1])
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(y.tobytes())


def read_wav(path: str) -> np.ndarray:
    with wave.open(path, "rb") as w:
        ch = w.getnchannels()
        raw = w.readframes(w.getnframes())
        assert w.getsampwidth() == 2 and w.getframerate() == SR
    y = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32767.0
    return y.reshape(-1, ch)


def analyse_file(path: str) -> dict:
    """Measure the written WAV (not the float signal): length, channels, RMS, peak, DC, clipping."""
    y = read_wav(path)
    return {
        "seconds": y.shape[0] / SR,
        "channels": y.shape[1],
        "rms_db": db(rms(y)),
        "peak_db": db(peak(y)),
        "dc": float(np.max(np.abs(np.mean(y, axis=0)))),
        "clipped": bool(np.any(np.abs(y) >= 32767.0 / 32767.0)),
    }


# --------------------------------------------------------------------------------------------------------------------
# output registry
# --------------------------------------------------------------------------------------------------------------------

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
OUT_DIR = os.path.join(ROOT, "SourceArt", "Audio", "Generated")

BED_DB = -24.0     # loops / beds: RMS dBFS (section 3)
ONESHOT_DB = -3.0  # one-shots: peak dBFS (section 3)
MUSIC_DB = -22.0   # music loops: RMS dBFS (section 3)


def emit(entries: list, name: str, group: str, x, *, loop: bool, listen: str, mix_gain_db: float = 0.0,
         seed=None, note: str = "", out_dir: str | None = None) -> dict:
    """Write <name>.wav, measure the written file, and append a manifest entry."""
    path = os.path.join(out_dir or OUT_DIR, name + ".wav")
    write_wav(path, x, name)
    info = analyse_file(path)
    entry = {"name": name, "group": group, "file": name + ".wav", "loop": bool(loop), "listen": listen,
             "mix_gain_db": mix_gain_db, "seed": seed, "note": note}
    entry.update(info)
    if loop:
        y = read_wav(path)
        entry["seam_step_db"] = seam_step_db(y)
        entry["seam_click"] = seam_click_ratio(y)
    entries.append(entry)
    print("  %-34s %6.2fs %dch  rms %6.1f  peak %5.1f  dc %.5f%s" % (
        name, entry["seconds"], entry["channels"], entry["rms_db"], entry["peak_db"], entry["dc"],
        ("  seam %+.2f dB click %.1f" % (entry["seam_step_db"], entry["seam_click"])) if loop else ""))
    return entry
