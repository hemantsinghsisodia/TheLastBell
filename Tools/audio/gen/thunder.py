"""Thunder one-shots, mono: Near x4, Mid x4, Far x4, Strike x3 (plan section 4.3). Seeds 1001-1004, 1101-1104, 1201-1204,
1301-1303.

P16-5: the owner rejected the synthetic cracks. With CRACKS = "recorded" (the default):
  * Near = the generated rumble (same seeds 1001-1004, NO synthetic crack and NO synthetic tearing) with a recorded Freesound CC0
    crack layer laid at t = 0 (crack peak 1.0, rumble peak RUMBLE_PEAK = 0.85 on the same scale, as before), then -3 dBFS peak;
  * Strike = a recorded crack with its own early boom (about 2.6-2.9 s), -3 dBFS peak.
Both come from Tools/audio/prep/prep_cracks.py (recipes in Tools/audio/prep/crack_recipes.json; needs ffmpeg and the raw downloads
in ExternalAssets/Incoming/freesound). CRACKS = "synthetic" restores the old all-generated Near and Strike.
Mid and Far are untouched.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "prep"))

import numpy as np  # noqa: E402

import audio_lib as A  # noqa: E402

GROUP = "thunder"
CRACKS = "recorded"            # "recorded" (P16-5) or "synthetic" (the rejected P16-A2 version)

# Values section 4.3 leaves open:
NEAR_SECONDS = (7.0, 9.0)      # file length range, drawn per seed (cue sheet: 7-9 s)
MID_SECONDS = (6.0, 7.0)       # cue sheet: 6-7 s
FAR_SECONDS = (5.0, 6.0)       # cue sheet: 5-6 s
STRIKE_SECONDS = 3.0           # cue sheet: 3 s
RUMBLE_HP = 28.0               # high-pass on every rumble, removes the sub-audible brown-noise bulk
CRACK_PEAK = 1.0               # crack peak, in the same units as the rumble below
RUMBLE_PEAK = 0.85             # peak of the (compressed) Near rumble relative to the crack peak of 1.0
FAR_MIX_GAIN_DB = -8.0         # given in the recipe: Far is 8 dB under the others in the mix


def rumble(rng, n, fc):
    """Brown noise low-passed at fc, high-passed at RUMBLE_HP, unit RMS."""
    y = A.brown(rng, n)
    y = A.lowpass(y, fc, 4, pad=n // 4)
    y = A.highpass(y, RUMBLE_HP, 4, pad=n // 4)
    return y / A.rms(y)


def burst_env(n, attack, t60):
    return A.rise(n, attack) * A.exp_decay(n, t60)


def crack(rng, n, dur=0.040, lo=2000.0, hi=8000.0, broadband=0.35):
    """A sharp broadband crack emphasised at lo-hi: attack under 1 ms, 60 dB decay in `dur`."""
    m = A.nsamp(dur * 4)
    noise = rng.standard_normal(m)
    y = A.bandpass(noise, lo, hi, 2, pad=m) + broadband * noise
    env = A.exp_decay(m, dur) * (1.0 - np.exp(-A.tvec(m) / 0.0003))
    y = y * env
    return y / (np.max(np.abs(y)) + 1e-12)  # peak 1


def squash(y, k=2.0):
    """Gentle tanh compression to peak 1: keeps long rumbles from being 25 dB quieter than their peaks."""
    y = y / (np.max(np.abs(y)) + 1e-12)
    return np.tanh(k * y) / np.tanh(k)


def near_rumble(seed):
    """The generated Near rumble WITHOUT any crack: (signal at peak RUMBLE_PEAK, rng after the rumble). The draws before the
    synthetic crack are the same as ever, so seeds 1001-1004 give the rumble the owner kept."""
    rng = A.rng_for(seed)
    dur = rng.uniform(*NEAR_SECONDS)
    n = A.nsamp(dur)
    rum = np.zeros(n)
    # rumble: a main swell plus 3-6 decaying bursts at random times over the length
    count = int(rng.integers(3, 7))
    times = np.sort(np.concatenate([[rng.uniform(0.03, 0.25)], rng.uniform(0.6, dur - 2.2, count - 1)]))
    for i, t0 in enumerate(times):
        amp = 1.0 if i == 0 else rng.uniform(0.35, 0.8) * (1.0 - 0.45 * t0 / dur)
        fc = rng.uniform(120.0, 300.0)
        seg = A.nsamp(min(dur - t0, 4.5))
        y = rumble(rng, seg, fc) * burst_env(seg, rng.uniform(0.05, 0.25) if i else 0.12, rng.uniform(1.6, 3.4))
        A.add_at(rum, y, A.nsamp(t0), amp)
    # the main swell underneath so the tail never drops out between bursts
    rum += 0.6 * rumble(rng, n, rng.uniform(120.0, 220.0)) * burst_env(n, 0.2, 6.5)
    return RUMBLE_PEAK * squash(rum), rng


def render_near(seed, crack_layer=True):
    """Near thunder. crack_layer: True = the synthetic crack (rejected by the owner), False/None = the rumble only, or a float
    array = a recorded crack (peak 1.0) laid at t = 0 over the rumble. Returns the finished one-shot (-3 dBFS peak)."""
    out, rng = near_rumble(seed)
    n = len(out)
    if crack_layer is True:
        A.add_at(out, crack(rng, n), 0, CRACK_PEAK)  # 40 ms crack, then ragged mid-band tearing for 0.6 s
        tear = A.bandpass(rng.standard_normal(n), 150.0, 1400.0, 2, pad=n // 4) * A.exp_decay(n, 0.6) * A.rise(n, 0.006)
        out += 0.25 * tear / (np.max(np.abs(tear)) + 1e-12)
    elif crack_layer is not False and crack_layer is not None:
        A.add_at(out, np.asarray(crack_layer, dtype=np.float64), 0, CRACK_PEAK)
    out = A.highpass(out, RUMBLE_HP, 2, pad=n // 4)
    return A.finish_oneshot(out, A.ONESHOT_DB, 0.0005, 0.8)


def render_strike_recorded(name):
    """A recorded crack with its own early boom, already cut and faded (prep_cracks); only the level is set here."""
    import prep_cracks
    sig, info = prep_cracks.strike(name)
    return A.finish_oneshot(sig, A.ONESHOT_DB, 0.0, 0.0), info


def render_mid(seed):
    rng = A.rng_for(seed)
    dur = rng.uniform(*MID_SECONDS)
    n = A.nsamp(dur)
    out = np.zeros(n)
    base = rumble(rng, n, 400.0) * A.rise(n, 1.5, 1.5) * A.exp_decay(n, 5.0)  # a 1.5 s rise, then a 6 s rumble
    out += base
    for _ in range(int(rng.integers(2, 5))):  # a little rolling inside the rumble
        t0 = rng.uniform(1.4, dur - 2.0)
        seg = A.nsamp(min(dur - t0, 3.0))
        y = rumble(rng, seg, rng.uniform(250.0, 400.0)) * burst_env(seg, rng.uniform(0.3, 0.8), rng.uniform(1.0, 2.0))
        A.add_at(out, y, A.nsamp(t0), rng.uniform(0.25, 0.55))
    out = A.highpass(out, RUMBLE_HP, 2, pad=n // 4)
    return A.finish_oneshot(out, A.ONESHOT_DB, 0.05, 0.9)


def render_far(seed):
    rng = A.rng_for(seed)
    dur = rng.uniform(*FAR_SECONDS)
    n = A.nsamp(dur)
    out = rumble(rng, n, 180.0) * A.rise(n, 2.2, 1.5) * A.exp_decay(n, 4.2)  # slow attack, ~5 s rumble
    for _ in range(int(rng.integers(1, 3))):
        t0 = rng.uniform(1.8, dur - 1.8)
        seg = A.nsamp(min(dur - t0, 2.5))
        y = rumble(rng, seg, rng.uniform(100.0, 180.0)) * burst_env(seg, rng.uniform(0.5, 1.0), rng.uniform(0.9, 1.6))
        A.add_at(out, y, A.nsamp(t0), rng.uniform(0.2, 0.4))
    out = A.highpass(out, RUMBLE_HP, 2, pad=n // 4)
    return A.finish_oneshot(out, A.ONESHOT_DB, 0.1, 0.9)  # mix gain -8 dB is recorded in the manifest


def render_strike(seed):
    rng = A.rng_for(seed)
    n = A.nsamp(STRIKE_SECONDS)
    out = np.zeros(n)
    # two cracks 60 ms apart, each a 25 ms burst with 3-10 kHz emphasis
    A.add_at(out, crack(rng, n, 0.045, 3000.0, 10000.0, 0.25), 0, 1.0)
    A.add_at(out, crack(rng, n, 0.045, 3000.0, 10000.0, 0.25), A.nsamp(0.060), 0.9)
    # 400 ms tearing noise tail: band-limited noise with a fast irregular amplitude flutter
    m = A.nsamp(0.5)
    tear = A.bandpass(rng.standard_normal(m), 800.0, 6500.0, 2, pad=m)
    flutter = np.abs(A.lowband(rng, m, 40.0, 220.0)) * 0.8 + 0.2
    tear = tear * flutter * A.exp_decay(m, 0.4) * A.rise(m, 0.004)
    A.add_at(out, tear / A.rms(tear[:A.nsamp(0.2)]), A.nsamp(0.012), 0.08)
    # short sub thump: 50 Hz, 150 ms
    k = A.nsamp(0.15)
    thump = np.sin(2 * np.pi * 50.0 * A.tvec(k)) * A.exp_decay(k, 0.15) * A.rise(k, 0.004)
    A.add_at(out, thump, 0, 0.75)
    # a short rumble tail so the strike dies away naturally inside the 3 s
    tail = rumble(rng, n, 220.0) * A.exp_decay(n, 1.5) * A.rise(n, 0.05)
    out += 0.20 * tail
    out = A.highpass(out, RUMBLE_HP, 2, pad=n // 4)
    return A.finish_oneshot(out, A.ONESHOT_DB, 0.0003, 0.4)


def _source_note(info):
    return "cut %.3f..%.3f s of the source (crack onset %.3f s)" % (info["cut_t0"], info["cut_t1"], info["onset"])


def build(entries, out_dir=None):
    print("[thunder]")
    recorded = CRACKS == "recorded"
    if recorded:
        import prep_cracks
    for i, seed in enumerate(range(1001, 1005), 1):
        name = "SFX_LB_Thunder_Near_%02d" % i
        if recorded:
            layer_sig, layer, rseed, info = prep_cracks.near_crack(name)
            assert rseed == seed, (name, rseed, seed)
            e = A.emit(entries, name, GROUP, render_near(seed, layer_sig), loop=False, seed=seed, out_dir=out_dir,
                       note="generated rumble (seed %d, no synthetic crack) + recorded crack layer %s" % (seed, layer),
                       listen="A recorded close lightning crack (Freesound %s) at t = 0 over a deep generated rolling rumble with 3-6 surges over 7-9 s. Close and big." % info["src"][3:])
            e["composition"] = {"generated_rumble_seed": seed, "recorded_crack_layer": layer, "crack_source": info["src"],
                                "crack_onset_s": round(info["onset"], 3), "crack_cut_s": [round(info["cut_t0"], 3), round(info["cut_t1"], 3)],
                                "crack_peak_re_rumble_db": round(20 * np.log10(CRACK_PEAK / RUMBLE_PEAK), 2)}
        else:
            A.emit(entries, name, GROUP, render_near(seed), loop=False, seed=seed, out_dir=out_dir,
                   listen="Sharp crack in the first 40 ms, then a deep rolling rumble with 3-6 surges over 7-9 s. Close and big.")
    for i, seed in enumerate(range(1101, 1105), 1):
        A.emit(entries, "SFX_LB_Thunder_Mid_%02d" % i, GROUP, render_mid(seed), loop=False, seed=seed, out_dir=out_dir,
               listen="No crack: a 1.5 s rise into a ~6 s rolling rumble. Medium distance.")
    for i, seed in enumerate(range(1201, 1205), 1):
        A.emit(entries, "SFX_LB_Thunder_Far_%02d" % i, GROUP, render_far(seed), loop=False, seed=seed, out_dir=out_dir,
               mix_gain_db=FAR_MIX_GAIN_DB,
               listen="Slow swell, dull low grumble (nothing above ~200 Hz), ~5 s. Far away; meant to sit 8 dB under the others.")
    for i, seed in enumerate(range(1301, 1304), 1):
        name = "SFX_LB_Thunder_Strike_%02d" % i
        if recorded:
            x, info = render_strike_recorded(name)
            e = A.emit(entries, name, GROUP, x, loop=False, seed=None, out_dir=out_dir,
                       note="recorded close lightning strike, Freesound %s, %s" % (info["src"], _source_note(info)),
                       listen="A recorded close lightning strike (Freesound %s): sharp tearing crack, then its own short boom, fading out by about 2.6-2.9 s. LOUD: the tower strike." % info["src"][3:])
            e["composition"] = {"crack_source": info["src"], "crack_onset_s": round(info["onset"], 3), "crack_cut_s": [round(info["cut_t0"], 3), round(info["cut_t1"], 3)]}
        else:
            A.emit(entries, name, GROUP, render_strike(seed), loop=False, seed=seed, out_dir=out_dir,
                   listen="Double crack 60 ms apart, 400 ms of tearing, low thump, then a short rumble. LOUD and sharp: the tower strike.")
    return entries


if __name__ == "__main__":
    build([])
