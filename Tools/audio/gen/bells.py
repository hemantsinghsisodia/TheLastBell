"""Bells: the great bell stages 1-5, the small bell strike, the fail cluster and the solved flourish (plan section 4.4).

All mono one-shots. The great bell is additive synthesis of the section 4.4 partials (prime 110 Hz). The crack amount c splits
each partial into two detuned copies (+-(0.6 + 1.2c) Hz, so the bell beats), runs the sum through an asymmetric soft clip and adds an
amplitude-modulated rattle. Stage 1 is the farthest and most cracked-but-dull, stage 5 the clean finale.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

import audio_lib as A  # noqa: E402

GROUP = "bells"

# (name, ratio to prime, T60 seconds, amplitude): the section 4.4 table. The upper partials' T60 (0.5-2 s) and amplitude
# (0.15-0.3) are chosen here, falling with ratio.
GREAT_PARTIALS = [
    ("hum", 0.5, 25.0, 0.60), ("prime", 1.0, 15.0, 0.50), ("tierce", 1.2, 12.0, 0.45), ("quint", 1.5, 8.0, 0.25),
    ("nominal", 2.0, 10.0, 0.70), ("superquint", 3.0, 5.0, 0.30), ("octave_nominal", 4.0, 4.0, 0.25),
    ("u1", 5.3, 2.0, 0.22), ("u2", 6.2, 1.6, 0.20), ("u3", 7.1, 1.2, 0.18), ("u4", 8.9, 0.8, 0.15), ("u5", 11.3, 0.5, 0.15),
]
GREAT_PRIME_HZ = 110.0
LOW_PARTIALS = 5               # the first five partials beat at exactly the recipe rate; the uppers get a +-25 % spread
BEAT_SPREAD = 0.25
RATTLE_DB = -24.0              # rattle gain is c * RATTLE_DB (as amplitude: c * 10^(-24/20)) relative to the tonal RMS
STRIKE_NOISE = 0.45            # 15 ms strike noise burst peak relative to the tonal sum peak
CLEAN_SHIMMER_HZ = 0.12        # stage 5 (c = 0): a barely-there +-0.12 Hz doublet so the clean bell is not a dead sine stack

# stage: (crack c, low-pass Hz or None, reverb T60 s, wet dB, file seconds, seed)
STAGES = {
    1: (0.60, 900.0, 6.0, -1.0, 22.0, 4101),
    2: (0.75, 1500.0, 5.0, -3.0, 24.0, 4102),
    3: (0.90, 2500.0, 4.0, -4.0, 26.0, 4103),
    4: (1.00, None, 3.5, -5.0, 28.0, 4104),
    5: (0.00, None, 8.0, -4.0, 30.0, 4105),
}
STAGE_MIX_GAIN_DB = {1: -18.0, 2: -14.0, 3: -10.0, 4: -6.0, 5: 0.0}  # the recipe's Level column; applied in the mix
PREROLL_S = 1.2                # stage 4 reversed swell before the strike
SUB_HUM_HZ = 27.5              # stage 5 sub hum, 30 s


def bell_tonal(rng, n, prime_hz, c, t60_scale=1.0, vib_cents=0.0, vib_hz=0.3, bend_cents=0.0, bend_start=1.0,
               partials=GREAT_PARTIALS, shimmer=CLEAN_SHIMMER_HZ):
    """Sum of the bell's partials as split pairs. Returns (signal, beat_rate_hz)."""
    t = A.tvec(n)
    delta = (0.6 + 1.2 * c) if c > 0 else shimmer
    # pitch modulation: vibrato (stage 2) and the slow downward bend over the tail (stage 3)
    cents = np.zeros(n)
    if vib_cents:
        cents += vib_cents * np.sin(2 * np.pi * vib_hz * t)
    if bend_cents:
        u = np.clip((t - bend_start) / max(t[-1] - bend_start, 1e-6), 0.0, 1.0)
        cents += bend_cents * (u * u * (3 - 2 * u))
    mult = 2.0 ** (cents / 1200.0)
    cum = np.cumsum(mult) / A.SR
    out = np.zeros(n)
    for i, (_, ratio, t60, amp) in enumerate(partials):
        f = prime_hz * ratio
        d = delta if i < LOW_PARTIALS else delta * (1.0 + BEAT_SPREAD * rng.uniform(-1, 1))
        ph = rng.uniform(0, 2 * np.pi)
        env = amp * np.exp(-A.LN1000 * t / (t60 * t60_scale))
        if c > 0 or shimmer:
            a = np.sin(2 * np.pi * (f + d) * cum + ph)
            b = np.sin(2 * np.pi * (f - d) * cum + ph)
            out += env * 0.5 * (a + b)
        else:
            out += env * np.sin(2 * np.pi * f * cum + ph)
    return out, 2.0 * delta


def strike_burst(rng, n, scale=1.0):
    """15 ms noise burst, band-limited 600-6000 Hz (smaller bells strike shorter and higher)."""
    m = A.nsamp(0.015 * scale)
    y = A.bandpass(rng.standard_normal(m * 8), 600.0 / scale, 6000.0, 2, pad=m)[:m]
    y = y * (1.0 - np.arange(m) / m) ** 2
    out = np.zeros(n)
    out[:m] = y / (np.max(np.abs(y)) + 1e-12)
    return out


def rattle(rng, n, c, beat_hz, tonal_rms, decay_t60):
    """Band-passed (600-1800 Hz) noise, amplitude-modulated at the beat rate, at c * -24 dB re the tonal RMS."""
    if c <= 0:
        return np.zeros(n)
    y = A.bandpass(rng.standard_normal(n), 600.0, 1800.0, 2, pad=A.SR // 2)
    t = A.tvec(n)
    am = 0.5 * (1.0 + np.cos(2 * np.pi * beat_hz * t))
    y = y / A.rms(y) * am * A.exp_decay(n, decay_t60) * A.rise(n, 0.01)
    return y * tonal_rms * c * A.from_db(RATTLE_DB)


def great_bell(stage, seed=None):
    c, lp, rt60, wet_db, secs, default_seed = STAGES[stage]
    rng = A.rng_for(seed or default_seed)
    n = A.nsamp(secs)
    preroll = A.nsamp(PREROLL_S) if stage == 4 else 0
    body_n = n - preroll
    vib = 4.0 if stage == 2 else 0.0
    bend = -20.0 if stage == 3 else 0.0
    tonal, beat = bell_tonal(rng, body_n, GREAT_PRIME_HZ, c, vib_cents=vib, bend_cents=bend)
    ref = np.max(np.abs(tonal))
    # tonal RMS over the first 2 s is the reference for the rattle level
    tonal_rms = A.rms(tonal[:A.nsamp(2.0)])
    dry = tonal + STRIKE_NOISE * ref * strike_burst(rng, body_n)
    dry = dry + rattle(rng, body_n, c, beat, tonal_rms, 6.0)
    if c > 0:
        dry = A.soft_clip(dry, 1.0 + 1.5 * c, 0.1 * c)
    if stage == 5:  # the finale: a sub hum under everything, 30 s long
        t = A.tvec(body_n)
        sub = np.sin(2 * np.pi * SUB_HUM_HZ * t) * A.rise(body_n, 3.0) * A.exp_decay(body_n, 30.0)
        dry = dry / np.max(np.abs(dry)) + 0.45 * sub
    if lp:
        dry = A.lowpass(dry, lp, 4, pad=A.SR)
    if preroll:  # stage 4: a reversed swell of the tonal bell leading into the strike
        sw = A.lowpass(tonal[:preroll] / ref, 2500.0, 2, pad=A.SR // 4)[::-1]
        sw = sw * A.rise(preroll, 0.9, 2.0) * 0.55 * np.max(np.abs(dry))
        dry = np.concatenate([sw, dry])
    ir = A.synth_ir(rng, rt60)
    out = A.reverb(dry, ir, wet_db, 0.0, out_len=n)
    return A.finish_oneshot(out, A.ONESHOT_DB, 0.001, 2.5), beat


SMALL_PRIME_HZ = 523.0
SMALL_HUM_AMP = 0.2             # small bells only: the hum partial is 0.2 (great bell keeps 0.6) so they ring brighter
SMALL_PARTIALS = [(n, r, t, SMALL_HUM_AMP if n == "hum" else a) for n, r, t, a in GREAT_PARTIALS]
SMALL_T60_SCALE = 0.25          # T60 / 4
SMALL_C = 0.15
SMALL_SIZES = (1.30, 1.15, 1.00, 0.85)  # D-081; the play-time pitch multiplier is 1 / size


def small_bell_dry(rng, n, prime_hz, c=SMALL_C, level=1.0):
    tonal, beat = bell_tonal(rng, n, prime_hz, c, t60_scale=SMALL_T60_SCALE, partials=SMALL_PARTIALS)
    ref = np.max(np.abs(tonal))
    dry = tonal + 0.35 * ref * strike_burst(rng, n, scale=0.6)
    dry = dry + rattle(rng, n, c, beat, A.rms(tonal[:A.nsamp(0.8)]), 1.2)
    dry = A.soft_clip(dry, 1.0 + 1.5 * c, 0.1 * c)
    return level * dry / np.max(np.abs(dry))


def small_strike(seed=4201):
    rng = A.rng_for(seed)
    n = A.nsamp(4.0)
    return A.finish_oneshot(small_bell_dry(rng, n, SMALL_PRIME_HZ), A.ONESHOT_DB, 0.0005, 0.6)


def small_fail(seed=4202):
    """All four bells struck within 120 ms, each detuned 30-70 cents (random direction), c 0.8: a dissonant cluster."""
    rng = A.rng_for(seed)
    n = A.nsamp(3.0)
    out = np.zeros(n)
    offsets = np.array([0.0, 0.035, 0.080, 0.120])
    rng.shuffle(offsets)
    for size, off in zip(SMALL_SIZES, offsets):
        cents = rng.uniform(30.0, 70.0) * rng.choice([-1.0, 1.0])
        f = SMALL_PRIME_HZ / size * 2.0 ** (cents / 1200.0)
        A.add_at(out, small_bell_dry(rng, n, f, c=0.8), A.nsamp(off), 1.0)
    return A.finish_oneshot(out, A.ONESHOT_DB, 0.0005, 0.5)


def small_solved(seed=4203):
    """The four bells in order (rising pitch), then a low resonance swelling underneath and fading."""
    rng = A.rng_for(seed)
    n = A.nsamp(5.0)
    out = np.zeros(n)
    for k, size in enumerate(SMALL_SIZES):
        d = small_bell_dry(rng, n, SMALL_PRIME_HZ / size)
        A.add_at(out, d, A.nsamp(0.55 * k), 0.8)
    t = A.tvec(n)
    start = A.nsamp(2.1)
    m = n - start
    tm = A.tvec(m)
    res = np.zeros(m)
    for f, a in ((65.41, 1.0), (130.81, 0.8), (196.0, 0.35), (261.63, 0.3)):  # C2, C3, G3, C4
        res += a * 0.5 * (np.sin(2 * np.pi * (f + 0.35) * tm) + np.sin(2 * np.pi * (f - 0.35) * tm))
    res *= A.rise(m, 0.9) * A.exp_decay(m, 4.5)
    A.add_at(out, res, start, 0.9 / np.max(np.abs(res)) * 1.0)
    ir = A.synth_ir(rng, 2.0, damping=(1.0, 0.6, 0.3))
    out = A.reverb(out, ir, -9.0, 0.0, out_len=n)
    return A.finish_oneshot(out, A.ONESHOT_DB, 0.0005, 0.7)


def build(entries, out_dir=None):
    print("[bells]")
    notes = {
        1: "FARTHEST. Dull (low-passed 900 Hz), washed in 6 s of reverb, a slow wobbling beat on the hum/prime: cracked, "
           "distant. Intended 18 dB under stage 5.",
        2: "Closer: still dark (1.5 kHz) but the beating is faster and rougher; very slight wavering pitch (+-4 cents). -14 dB.",
        3: "Closer again (2.5 kHz), harsh distortion, and the pitch sags 20 cents over the tail. -10 dB.",
        4: "Close and brutal: full bandwidth, hardest crack, with a 1.2 s reversed swell before the strike. -6 dB.",
        5: "FINALE: clean, pure, no beating, huge 8 s reverb and a 27.5 Hz sub hum for 30 s. Full level (0 dB).",
    }
    for stage in range(1, 6):
        x, beat = great_bell(stage)
        A.emit(entries, "SFX_LB_Bell_Stage%d" % stage, GROUP, x, loop=False, seed=STAGES[stage][5],
               mix_gain_db=STAGE_MIX_GAIN_DB[stage], out_dir=out_dir, listen=notes[stage],
               note="beat rate %.2f Hz" % beat if STAGES[stage][0] > 0 else "no beating (c = 0)")
    A.emit(entries, "SFX_LB_SmallBell_Strike", GROUP, small_strike(), loop=False, seed=4201, out_dir=out_dir,
           listen="One bright small bell (C5, 523 Hz), 4 s ring, slight beat. In game it is pitched per bell (x1/size).")
    A.emit(entries, "SFX_LB_SmallBell_Fail", GROUP, small_fail(), loop=False, seed=4202, out_dir=out_dir,
           listen="All four bells at once, each out of tune, harsh and clashing: unmistakably WRONG.")
    A.emit(entries, "SFX_LB_SmallBell_Solved", GROUP, small_solved(), loop=False, seed=4203, out_dir=out_dir,
           listen="Four bells rising in order, then a low C resonance swelling under and fading: a reward, not a fanfare.")
    return entries


if __name__ == "__main__":
    build([])
