"""Music: Drone A/B/C (60 s), Tension (32 s), Chase (8.000 s at 120 BPM) and the three stings (plan section 4.5).

Stereo. The tonal loops are built from sines/saws whose frequencies are snapped to a whole number of cycles per loop, so they
repeat sample-exactly (no crossfade, no level bump at the seam); the noise layers use the equal-power fold.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

import audio_lib as A  # noqa: E402
import bells  # noqa: E402

GROUP = "music"

SYN = 12000                      # tonal layers are synthesised at 12 kHz then FFT-upsampled (they hold nothing above 5.5 kHz)
DRONE_S = 60.0
TENSION_S = 32.0
CHASE_BPM = 120.0
CHASE_SECONDS = 8.0              # 4 bars of 4/4 at 120 BPM

# Values section 4.5 leaves open:
A_DRONE_ROOT_HZ = 55.0
A_DRONE_AIR_DB = -26.0           # filtered air noise vs the tonal drone RMS
A_DRONE_SWEEP = (200.0, 900.0)   # low-pass sweep; rises over 40 s, falls over the last 20 s so the loop is seamless
B_BELL_GAIN = 0.28               # the faint stage-2 bell strike's peak vs the drone peak
C_FORMANTS = ((300.0, 6.0, 1.0), (870.0, 8.0, 0.35), (2240.0, 12.0, 0.08))  # 'oo': (Hz, Q, gain)
C_PITCHED_DB = -9.0              # the faint pitched choir vs the breath
TENSION_CHORD = (110.0, 116.54, 155.56, 220.0, 233.08)  # A2, Bb2, Eb3, A3, Bb3: tritone and minor-second clashes
SHIMMER_DB = -27.0
# detune per saw in cents, fixed per voice so the beat rates are all different (no coherent pulse): chosen
TENSION_DETUNE_CENTS = ((-8.3, 0.0, 6.1), (-5.2, 1.0, 9.4), (-9.7, -1.5, 4.6), (-4.1, 2.2, 8.0), (-7.0, 0.6, 10.3))


# --------------------------------------------------------------------------------------------------------------------
# tonal helpers
# --------------------------------------------------------------------------------------------------------------------


def tsyn(seconds):
    return np.arange(int(round(seconds * SYN))) / SYN


def upsample_periodic(x, factor=A.SR // SYN):
    """Exact FFT upsampling of a band-limited periodic signal."""
    n = x.shape[0]
    X = np.fft.rfft(x, axis=0)
    out_n = n * factor
    shape = (out_n // 2 + 1,) + X.shape[1:]
    Xp = np.zeros(shape, dtype=complex)
    Xp[:X.shape[0]] = X
    return np.fft.irfft(Xp, out_n, axis=0) * factor


def lp_res(f, fc, q=1.0):
    """2nd-order low-pass magnitude with resonance q; f scalar or array, fc scalar or array."""
    x = f / fc
    return 1.0 / np.sqrt((1.0 - x * x) ** 2 + (x / q) ** 2)


def bp_mag(f, lo, hi):
    return (1.0 / np.sqrt(1.0 + (lo / f) ** 4)) / np.sqrt(1.0 + (f / hi) ** 4)


def saw(t, f, rng, mag_fn, hmax_hz=5500.0, h_pow=1.0):
    """Additive saw: harmonic h has amplitude mag_fn(h f) / h^h_pow (mag_fn may return an array over t). Random phases."""
    out = np.zeros_like(t)
    for h in range(1, int(hmax_hz // f) + 1):
        out += (mag_fn(h * f) / h ** h_pow) * np.sin(2 * np.pi * h * f * t + rng.uniform(0, 2 * np.pi))
    return out


def periodic_lfo(t, period, phase=0.0):
    return np.sin(2 * np.pi * t / period + phase)


def finish_loop(x, level_db):
    x = A.normalize_rms(A.remove_dc(x), level_db, -1.0)
    return x


# --------------------------------------------------------------------------------------------------------------------
# drones
# --------------------------------------------------------------------------------------------------------------------


def drone_a(seed=5001):
    rng = A.rng_for(seed)
    T = DRONE_S
    t = tsyn(T)
    # low-pass sweep 200 -> 900 over 40 s, back over 20 s, eased so the loop is smooth at the seam
    u = np.where(t < 40.0, t / 40.0, 1.0 - (t - 40.0) / 20.0)
    s = u * u * (3 - 2 * u)
    fc = A_DRONE_SWEEP[0] * (A_DRONE_SWEEP[1] / A_DRONE_SWEEP[0]) ** s
    chans = []
    for ch in range(2):
        sign = 1 if ch == 0 else -1
        y = np.zeros_like(t)
        mag = lambda f: lp_res(f, fc, 1.1)  # noqa: E731
        for d in (-0.31, 0.0, 0.23):  # root saw stack, detuned (different per ear)
            y += saw(t, A.snap(A_DRONE_ROOT_HZ + sign * d, T), rng, mag, 3500.0)
        y += 0.9 * np.sin(2 * np.pi * A.snap(55.0 + 0.05 * sign, T) * t)          # sine sub
        y += 0.5 * np.sin(2 * np.pi * A.snap(110.0 - 0.07 * sign, T) * t + rng.uniform(0, 6))
        m2 = A.snap(A_DRONE_ROOT_HZ * 2 ** (1 / 12), T)                              # minor second, swelling in and out
        y += (0.55 + 0.45 * periodic_lfo(t, 30.0, rng.uniform(0, 6.28))) * 0.55 * saw(t, m2, rng, mag, 2500.0)
        tt = A.snap(A_DRONE_ROOT_HZ * 2 ** (6 / 12), T)                              # tritone
        y += (0.55 + 0.45 * periodic_lfo(t, 20.0, rng.uniform(0, 6.28))) * 0.40 * saw(t, tt, rng, mag, 2500.0)
        chans.append(y)
    tonal = upsample_periodic(np.stack(chans, axis=1))
    n = tonal.shape[0]
    tonal /= A.rms(tonal)

    def air(sd, m):
        r = A.rng_for(sd)
        x = np.stack([A.bandpass(r.standard_normal(m), 1500.0, 6000.0, 2, pad=A.SR) for _ in range(2)], axis=1)
        return x / A.rms(x)

    noise = A.fold_loop(air(seed + 7, n + A.nsamp(2.0)), n)
    tn = A.tvec(n)[:, None]
    noise = noise * (0.65 + 0.35 * np.sin(2 * np.pi * tn / 20.0 + np.array([[0.0, 2.0]])))  # slow breathing, periodic
    return finish_loop(tonal + A.from_db(A_DRONE_AIR_DB) * noise, A.MUSIC_DB)


def swell_env(t, centre_start, T, attack=4.0, hold=6.0, release=10.0, wobble=0.0):
    """Circular swell envelope: raised-cosine attack (4 s), hold, raised-cosine release; wraps around the loop."""
    tau = np.mod(t - centre_start, T)
    e = np.zeros_like(t)
    a = tau < attack
    e[a] = 0.5 - 0.5 * np.cos(np.pi * tau[a] / attack)
    h = (tau >= attack) & (tau < attack + hold)
    e[h] = 1.0
    r = (tau >= attack + hold) & (tau < attack + hold + release)
    e[r] = 0.5 + 0.5 * np.cos(np.pi * (tau[r] - attack - hold) / release)
    return e


def drone_b(seed=5002):
    rng = A.rng_for(seed)
    T = DRONE_S
    t = tsyn(T)
    c = 0.75                                   # the stage-2 crack amount: partials split by +-1.5 Hz
    delta = 0.6 + 1.2 * c
    chans = []
    starts = (0.0, 15.0, 30.0, 45.0)
    for ch in range(2):
        y = np.zeros_like(t)
        for k, st in enumerate(starts):
            env = swell_env(t, st + 2.0 * ch, T)
            # hum (55 Hz) and tierce (132 Hz), each as a split pair; tierce level varies per swell
            for f, a in ((55.0, 1.0), (110.0 * 1.2, (0.55, 0.8, 0.65, 0.5)[k]), (110.0, 0.35 if k % 2 else 0.2)):
                ph = rng.uniform(0, 2 * np.pi)
                y += env * a * 0.5 * (np.sin(2 * np.pi * A.snap(f + delta, T) * t + ph)
                                      + np.sin(2 * np.pi * A.snap(f - delta, T) * t + ph + 0.3 * ch))
        chans.append(y)
    tonal = upsample_periodic(np.stack(chans, axis=1))
    n = tonal.shape[0]
    tonal /= np.max(np.abs(tonal))
    # a faint stage-2 bell strike, placed so its tail wraps cleanly (it dies out well before the loop end)
    bell, _ = bells.great_bell(2)
    bell = np.stack([bell, bell], axis=1)
    A.add_at(tonal, bell, A.nsamp(22.0), B_BELL_GAIN, circular=True)
    return finish_loop(tonal, A.MUSIC_DB)


def drone_c(seed=5003):
    rng = A.rng_for(seed)
    T = DRONE_S
    n = A.nsamp(T)
    # breath: white noise through the 'oo' formants (300 / 870 / 2240 Hz), folded for a seamless loop
    def breath(sd, m):
        r = A.rng_for(sd)
        out = []
        for _ in range(2):
            w = r.standard_normal(m)
            y = sum(g * A.resonant_bp(w, f, q, pad=A.SR) * math.sqrt(f / q) / math.sqrt(300 / 6) for f, q, g in C_FORMANTS)
            out.append(y)
        x = np.stack(out, axis=1)
        return x / A.rms(x)

    noise = A.fold_loop(breath(seed + 11, n + A.nsamp(2.0)), n)
    tn = A.tvec(n)[:, None]
    ph = np.array([[0.3, 2.4]])
    noise = noise * (0.55 + 0.30 * np.sin(2 * np.pi * tn / 20.0 + ph) + 0.15 * np.sin(2 * np.pi * tn / 15.0 + ph * 1.7))
    noise /= A.rms(noise)
    # faint pitched choir: A minor triad low, harmonics shaped by the same 'oo' formants
    t = tsyn(T)
    chans = []
    for ch in range(2):
        y = np.zeros_like(t)
        for vi, (f0, period) in enumerate(((82.41, 20.0), (110.0, 15.0), (130.81, 12.0))):
            env = 0.5 + 0.5 * periodic_lfo(t, period, 2.0 * vi + 1.3 * ch)
            v = np.zeros_like(t)
            for dd in (-0.18, 0.18):
                f = A.snap(f0 + dd, T)
                for h in range(1, int(4000 // f) + 1):
                    fh = f * h
                    form = sum(g / math.sqrt(1 + (q * (fh / ff - ff / fh)) ** 2) for ff, q, g in C_FORMANTS)
                    v += (form / h ** 0.7) * np.sin(2 * np.pi * fh * t + rng.uniform(0, 6.28))
            y += env * v
        chans.append(y)
    pitched = upsample_periodic(np.stack(chans, axis=1))
    pitched /= A.rms(pitched)
    return finish_loop(noise + A.from_db(C_PITCHED_DB) * pitched, A.MUSIC_DB)


# --------------------------------------------------------------------------------------------------------------------
# tension
# --------------------------------------------------------------------------------------------------------------------


def tension(seed=5101):
    rng = A.rng_for(seed)
    T = TENSION_S
    t = tsyn(T)
    mag = lambda f: bp_mag(f, 200.0, 2000.0)  # noqa: E731
    chans = []
    for ch in range(2):
        y = np.zeros_like(t)
        for vi, f0 in enumerate(TENSION_CHORD):
            for cents in TENSION_DETUNE_CENTS[vi]:  # three detuned saws per note = string ensemble (random cents: a sheen, not a throb)
                f = A.snap(f0 * 2.0 ** ((cents + (0.0 if ch == 0 else 1.3)) / 1200.0), T)
                trem = 1.0 - 0.20 * (0.5 - 0.5 * np.cos(2 * np.pi * 5.0 * t + 0.6 * vi + 0.3 * ch))  # 5 Hz, 20 % depth
                y += trem * saw(t, f, rng, mag, 4500.0, h_pow=0.9) / (1 + 0.15 * vi)
        y *= 0.88 + 0.12 * periodic_lfo(t, T / 2, 1.1 * ch)  # slow swell
        chans.append(y)
    tonal = upsample_periodic(np.stack(chans, axis=1))
    tonal /= A.rms(tonal)
    n = tonal.shape[0]
    tn = A.tvec(n)
    # high harmonic shimmer: beating sine pairs between 2.6 and 5.3 kHz, swelling on periodic LFOs
    sh = np.zeros((n, 2))
    for ch in range(2):
        for i, h in enumerate((24, 29, 33, 41, 47)):
            f = A.snap(110.0 * h * (1.0 + 0.002 * i), T)
            lfo = 0.5 + 0.5 * np.sin(2 * np.pi * tn / (T / (1 + (i % 3))) + rng.uniform(0, 6.28))
            sh[:, ch] += lfo * 0.5 * (np.sin(2 * np.pi * (f + 0.4) * tn + rng.uniform(0, 6.28))
                                      + np.sin(2 * np.pi * (f - 0.4) * tn + rng.uniform(0, 6.28)))
    sh /= A.rms(sh)
    return finish_loop(tonal + A.from_db(SHIMMER_DB) * sh, A.MUSIC_DB)


# --------------------------------------------------------------------------------------------------------------------
# chase
# --------------------------------------------------------------------------------------------------------------------


def thump(rng, n_s=1.2, f_start=85.0, f_end=48.0, tau=0.035, t60=0.30, click=0.35):
    """Heartbeat thump: a sine gliding f_start -> f_end plus a short noise click."""
    n = A.nsamp(n_s)
    t = A.tvec(n)
    phase = 2 * np.pi * (f_end * t + (f_start - f_end) * tau * (1.0 - np.exp(-t / tau)))
    y = np.sin(phase) * A.exp_decay(n, t60) * A.rise(n, 0.002)
    m = A.nsamp(0.012)
    c = A.bandpass(rng.standard_normal(m * 4), 200.0, 3500.0, 2, pad=m)[:m] * A.exp_decay(m, 0.012)
    y[:m] += click * c / (np.max(np.abs(c)) + 1e-12)
    return y


def saw48(f, seconds, fc, rng):
    n = A.nsamp(seconds)
    t = A.tvec(n)
    y = np.zeros(n)
    for h in range(1, int(4000 // f) + 1):
        y += (1.0 / h) / math.sqrt(1 + (h * f / fc) ** 4) * np.sin(2 * np.pi * h * f * t + rng.uniform(0, 6.28))
    return y


def chase(seed=5201):
    rng = A.rng_for(seed)
    n = A.nsamp(CHASE_SECONDS)
    assert n == 384000
    beat = 60.0 / CHASE_BPM          # 0.5 s
    bar = 4 * beat                   # 2 s
    eighth = beat / 2                # 0.25 s
    out = np.zeros((n, 2))
    heart = np.zeros(n)
    for b in range(4):  # double heartbeat: beat 1 and 1-and of every bar
        A.put(heart, thump(rng), b * bar, 1.0, circular=True)
        A.put(heart, thump(rng, f_start=75.0, t60=0.26), b * bar + eighth, 0.7, circular=True)
    amps = (1.0, 0.45, 0.75, 0.45, 0.9, 0.45, 0.75, 0.55)
    pitches = (55.0, 55.0, 58.27, 55.0, 55.0, 58.27, 55.0, 58.27)
    ost = np.zeros(n)
    for b in range(4):
        fc = 420.0 + 170.0 * b
        for k in range(8):
            f = pitches[k]
            note = saw48(f, eighth, fc, rng) + saw48(f * 1.004, eighth, fc, rng)
            e = A.exp_decay(note.shape[0], 0.22) * A.rise(note.shape[0], 0.004)
            e[-A.nsamp(0.012):] *= np.linspace(1, 0, A.nsamp(0.012))   # every note is silent by the next slot
            A.put(ost, note * e / np.max(np.abs(note)), b * bar + k * eighth, amps[k] * (0.85 + 0.05 * b), circular=True)
    # rising noise swell over the 4 bars: the low band opens first, the highs arrive last
    t = A.tvec(n)
    sw = np.zeros((n, 2))
    for ch in range(2):
        w = rng.standard_normal(n)
        for lo, hi, power, gain in ((300.0, 1000.0, 1.0, 0.55), (1000.0, 3000.0, 2.0, 0.60), (3000.0, 9000.0, 3.0, 0.50)):
            band = A.bandpass(w, lo, hi, 2, pad=A.SR // 2)
            sw[:, ch] += gain * band / A.rms(band) * (t / CHASE_SECONDS) ** power
    sw = A.fade_edges(sw, 0.0, 0.02)  # the swell is gone before the loop restarts on the downbeat thump
    out[:, 0] = 1.0 * heart + 0.55 * ost + 0.09 * sw[:, 0]
    out[:, 1] = 1.0 * heart + 0.55 * ost + 0.09 * sw[:, 1]
    return finish_loop(out, A.MUSIC_DB)


# --------------------------------------------------------------------------------------------------------------------
# stings
# --------------------------------------------------------------------------------------------------------------------

STING_SPOTTED_S = 2.6
STING_CAUGHT_S = 3.0
STING_APPARITION_S = 3.0


def sting_spotted(seed=5301):
    """2 s dissonant swell into a hit at t = 2.0 s (then a short tail)."""
    rng = A.rng_for(seed)
    n = A.nsamp(STING_SPOTTED_S)
    hit = A.nsamp(2.0)
    t = A.tvec(n)
    u = np.clip(t / 2.0, 0, 1)
    fc = 300.0 * (3600.0 / 300.0) ** (u * u)
    y = np.zeros(n)
    for f in (220.0, 233.08, 311.13, 329.63, 440.0):   # A, Bb, Eb, E, A: tritone + semitone clashes
        for d in (-0.5, 0.6):
            y += saw48_t(t, f + d, fc, rng)
    y *= (u ** 2.2) * (t < 2.0)
    nz = A.bandpass(rng.standard_normal(n), 1200.0, 7000.0, 2, pad=A.SR // 4)
    y2 = np.zeros(n)
    y2 += 3.0 * y / np.max(np.abs(y)) + 0.9 * (nz / A.rms(nz)) * (u ** 3) * (t < 2.0) * 0.5
    out = y2 * 1.0
    # the hit: low thump, noise burst and a dissonant chord stab that rings out
    m = n - hit
    th = thump(rng, n_s=m / A.SR, f_start=90.0, f_end=42.0, t60=0.8, click=0.5)
    A.add_at(out, th, hit, 3.6)
    tm = A.tvec(m)
    stab = np.zeros(m)
    for f in (110.0, 116.54, 155.56, 220.0, 233.08):
        stab += saw48_t(tm, f, 1800.0, rng)
    stab *= A.exp_decay(m, 0.7) * A.rise(m, 0.003)
    A.add_at(out, stab / np.max(np.abs(stab)), hit, 2.2)
    return A.finish_oneshot(out, A.ONESHOT_DB, 0.01, 0.3)


def saw48_t(t, f, fc_t, rng, hmax=4500.0):
    y = np.zeros_like(t)
    for h in range(1, int(hmax // f) + 1):
        y += (1.0 / h) * lp_res(h * f, fc_t, 0.9) * np.sin(2 * np.pi * h * f * t + rng.uniform(0, 6.28))
    return y


def sting_caught(seed=5302):
    """A heavy low hit at t = 0 and a reversed bell swelling to a sudden cut-off at 2.55 s."""
    rng = A.rng_for(seed)
    n = A.nsamp(STING_CAUGHT_S)
    out = np.zeros(n)
    A.add_at(out, thump(rng, n_s=STING_CAUGHT_S, f_start=95.0, f_end=36.0, tau=0.05, t60=1.6, click=0.6), 0, 3.0)
    t = A.tvec(n)
    boom = saw48_t(t, 41.0, 140.0, rng) + saw48_t(t, 41.6, 140.0, rng)
    out += 0.9 * boom / np.max(np.abs(boom)) * A.exp_decay(n, 2.2) * A.rise(n, 0.004)
    bn = A.nsamp(2.4)
    tonal, _ = bells.bell_tonal(rng, bn + A.nsamp(0.0), 146.8, 0.9, t60_scale=0.35)  # D3-based bell, cracked
    rev = A.lowpass(tonal[::-1], 3500.0, 2, pad=A.SR // 2)
    rev = rev / np.max(np.abs(rev)) * A.rise(bn, 2.0, 2.0)
    rev[-A.nsamp(0.02):] *= np.linspace(1, 0, A.nsamp(0.02))
    A.add_at(out, rev, A.nsamp(0.15), 1.5)
    return A.finish_oneshot(out, A.ONESHOT_DB, 0.001, 0.4)


def sting_apparition(seed=5303):
    """A 3 s whispering noise swell: syllabic breath bursts that rise and fade, drifting between the ears."""
    rng = A.rng_for(seed)
    n = A.nsamp(STING_APPARITION_S)
    t = A.tvec(n)
    swell = np.sin(np.pi * np.clip(t / STING_APPARITION_S, 0, 1) ** 1.3) ** 2
    out = np.zeros((n, 2))
    for ch in range(2):
        hiss = A.bandpass(rng.standard_normal(n), 1800.0, 7500.0, 3, pad=A.SR // 2)
        body = A.bandpass(rng.standard_normal(n), 500.0, 1300.0, 2, pad=A.SR // 2)
        syl = np.abs(A.lowband(rng, n, 2.0, 9.0)) ** 0.8 * 0.85 + 0.15       # syllable-like bursts
        pan = 0.5 + 0.35 * np.sin(2 * np.pi * (0.4 + 0.1 * ch) * t + 3.0 * ch)
        x = (hiss / A.rms(hiss) + 0.45 * body / A.rms(body)) * syl * swell
        out[:, ch] = x * (pan if ch == 0 else 1.0 - pan) * 2.0
    return A.finish_oneshot(out, A.ONESHOT_DB, 0.05, 0.25)


def gated(fn, base, tries=6, step=100):
    """Render with seeds base, base+100, ... and keep the first whose loop seam step is under 0.5 dB (else the best)."""
    best = None
    for k in range(tries):
        x = fn(base + step * k)
        st = abs(A.seam_step_db(x))
        if best is None or st < best[0]:
            best = (st, x, base + step * k)
        if st < 0.5:
            break
    return best[1], best[2]


def stereo_oneshot(x):
    return A.to_stereo(x)


def build(entries, out_dir=None):
    print("[music]")
    xa, sa = gated(drone_a, 5001)
    xb, sb = gated(drone_b, 5002)
    xc, sc = gated(drone_c, 5003)
    A.emit(entries, "MUS_LB_Drone_A", GROUP, xa, loop=True, seed=sa, out_dir=out_dir,
           listen="Very low (A1) detuned buzzing stack with a semitone and tritone clash swelling in and out; a dark filter "
                  "slowly opens over 40 s and closes over 20 s; a little air on top. Menacing, not melodic.")
    A.emit(entries, "MUS_LB_Drone_B", GROUP, xb, loop=True, seed=sb, out_dir=out_dir,
           listen="The bell's hum and tierce as slow swelling tones (4 s attack) that beat, plus one faint distant cracked bell strike "
                  "inside the drone (about 22 s in). Should feel like the bell 'breathing'.")
    A.emit(entries, "MUS_LB_Drone_C", GROUP, xc, loop=True, seed=sc, out_dir=out_dir,
           listen="A breathy low 'oo' choir: formant-filtered noise with slow swells and a faint low minor chord underneath. "
                  "Listen for anything that sounds like a synth pad rather than breath.")
    A.emit(entries, "MUS_LB_Tension", GROUP, tension(), loop=True, seed=5101, out_dir=out_dir,
           listen="No pulse. Thick, clashing string-like saws with a fast 5 Hz flutter and a faint glassy shimmer on top. "
                  "Uneasy, steady, loops every 32 s.")
    A.emit(entries, "MUS_LB_Chase", GROUP, chase(), loop=True, seed=5201, out_dir=out_dir,
           listen="120 BPM, 8.000 s: double heartbeat thump on beat 1 and the 'and' after it, a low growling saw ostinato in eighths, "
                  "and a quiet rising noise swell over 4 bars that drops out on the next downbeat. Loop it: the join must stay on the beat. (The listed seam step is the downbeat thump arriving after the swell peak, by design, not a fault.)")
    A.emit(entries, "MUS_LB_Sting_Spotted", GROUP, stereo_oneshot(sting_spotted()), loop=False, seed=5301, out_dir=out_dir,
           listen="2 s of rising dissonant saws and noise, then a hard hit at 2.0 s. (The hit lands ~1.4 s after the chase starts: "
                  "say if it should be shorter.)")
    A.emit(entries, "MUS_LB_Sting_Caught", GROUP, stereo_oneshot(sting_caught()), loop=False, seed=5302, out_dir=out_dir,
           listen="Immediate heavy low hit and boom, with a reversed cracked bell swelling underneath that cuts off at ~2.5 s.")
    A.emit(entries, "MUS_LB_Sting_Apparition", GROUP, sting_apparition(), loop=False, seed=5303, out_dir=out_dir,
           listen="3 s of whispering breath with syllable-like bursts swelling and fading, drifting between the ears. Should sound "
                  "like a voice almost making words.")
    return entries


if __name__ == "__main__":
    build([])
