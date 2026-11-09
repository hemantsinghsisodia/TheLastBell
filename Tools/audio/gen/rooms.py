"""Room tones (6 x 45 s stereo loops) and drips (5 water + 5 stone mono one-shots), plan section 4.6."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

import audio_lib as A  # noqa: E402
import wind  # noqa: E402

GROUP = "rooms"
ROOM_S = 45.0
FOLD_S = 2.0

# Levels in dBFS RMS before the final -24 dBFS normalisation. Section 4.6 gives the wind/howl/rumble/drop levels; the 'air'
# beds (not specified) are chosen here. Wind and Wind_Howl figures are relative to their own -24 dBFS bed level.
BED_REF_DB = -24.0
AIR_DB = {"crypt": -38.0, "chapel": -34.0, "cloister": -34.0, "passage": -34.0, "tower": -44.0, "belfry": -46.0}
CRYPT_RUMBLE_DB = -36.0         # given
CRYPT_DROPS_MEAN_DB = -30.0     # given (rain-in style drops at 30 /s)
CHAPEL_WIND_DB = -20.0          # given, high-passed 300 Hz
TOWER_HOWL_DB = -14.0           # given
BELFRY_WIND_DB = -8.0           # given
BELFRY_HOWL_DB = -10.0          # given
PASSAGE_DRAUGHT_DB = -40.0      # chosen: faint draught, a 180 Hz drifting resonance


def air(rng, n, lo, hi, level_db, walk_depth_db=1.5):
    chans = []
    for _ in range(2):
        x = A.bandpass(A.pink(rng, n), lo, hi, 2, pad=A.SR)
        x = x * A.walk_db(rng, n, 0.05, 0.2, walk_depth_db)
        chans.append(x / A.rms(x) * A.from_db(level_db))
    return A.stereo(*chans)


def scaled(x, level_db):
    return x / A.rms(x) * A.from_db(level_db)


def room_noise(room, seed, n):
    """Non-periodic part of a room tone (n samples, to be folded)."""
    rng = A.rng_for(seed)
    if room == "crypt":
        x = air(rng, n, 50.0, 1200.0, AIR_DB["crypt"])
        # a deep brown rumble under the 40 Hz tone
        rum = A.lowpass(A.brown(rng, n), 70.0, 4, pad=A.SR)
        x += scaled(A.stereo(rum, A.lowpass(A.brown(rng, n), 70.0, 4, pad=A.SR)), CRYPT_RUMBLE_DB - 6.0)
        # distant water: rain-in style drops, 30 /s, darkened and given a damp tail so they sound far away
        ir = A.synth_ir(rng, 2.0, damping=(1.0, 0.6, 0.3))
        for ch in range(2):
            d = A.poisson_bursts(rng, n, 30.0, (1000.0, 3000.0), (0.008, 0.015), A.from_db(CRYPT_DROPS_MEAN_DB))
            d = A.lowpass(d, 3000.0, 2, pad=A.SR)
            x[:, ch] += A.reverb(d, ir, -4.0, -3.0)
        return x
    if room == "chapel":
        x = air(rng, n, 80.0, 3000.0, AIR_DB["chapel"])
        w = A.highpass(wind.wind_raw(rng, n), 300.0, 4, pad=A.SR)  # faint wind through the roof hole
        return x + scaled(w, BED_REF_DB + CHAPEL_WIND_DB)
    if room == "cloister":
        return air(rng, n, 100.0, 5000.0, AIR_DB["cloister"], 2.0)
    if room == "passage":
        x = air(rng, n, 60.0, 2500.0, AIR_DB["passage"])
        dr = []
        for _ in range(2):
            fc = 180.0 * A.walk_frac(rng, n, 0.05, 0.2, 0.3)
            dr.append(A.tv_resonant_bp(A.white(rng, n), fc, 1.2))
        return x + scaled(A.stereo(*dr), PASSAGE_DRAUGHT_DB)
    if room == "tower":
        x = air(rng, n, 50.0, 900.0, AIR_DB["tower"])
        return x + scaled(wind.howl_raw(rng, n), BED_REF_DB + TOWER_HOWL_DB)
    if room == "belfry":
        x = air(rng, n, 80.0, 4000.0, AIR_DB["belfry"])
        x += scaled(wind.wind_raw(rng, n), BED_REF_DB + BELFRY_WIND_DB)
        return x + scaled(wind.howl_raw(rng, n), BED_REF_DB + BELFRY_HOWL_DB)
    raise ValueError(room)


def room_periodic(room, seed, L):
    """Sample-exact periodic additions (added after the fold so the crossfade cannot bump them)."""
    out = np.zeros((L, 2))
    if room == "crypt":
        t = A.tvec(L)
        f = A.snap(40.0, ROOM_S)
        for ch, ph in enumerate((0.0, 1.1)):
            am = 0.7 + 0.3 * np.sin(2 * np.pi * t / (ROOM_S / 3) + ph)
            out[:, ch] = A.from_db(CRYPT_RUMBLE_DB) * 1.41 * np.sin(2 * np.pi * f * t + ph) * am
    return out


def render_room(room, seed, L):
    x = A.fold_loop(room_noise(room, seed, L + A.nsamp(FOLD_S)), L)
    return A.remove_dc(x + room_periodic(room, seed, L))


def make_room(room, base_seed):
    L = A.nsamp(ROOM_S)
    best = None
    for k in range(6):
        seed = base_seed + 100 * k
        x = A.normalize_rms(render_room(room, seed, L), A.BED_DB, -1.0)
        st = abs(A.seam_step_db(x))
        if best is None or st < best[0]:
            best = (st, x, seed)
        if st < 0.5:
            break
    return best[1], best[2]


# --------------------------------------------------------------------------------------------------------------------
# drips
# --------------------------------------------------------------------------------------------------------------------

def drip_water(seed):
    """Sine glide 800 -> 1600 Hz over 30 ms plus a 1.2 kHz damped-sine bubble; per-variant pitch/glide/ring differences."""
    rng = A.rng_for(seed)
    n = A.nsamp(0.7)
    t = A.tvec(n)
    scale = rng.uniform(0.85, 1.22)
    glide = rng.uniform(0.024, 0.038)
    f0, f1 = 800.0 * scale, 1600.0 * scale
    u = np.clip(t / glide, 0, 1)
    freq = f0 + (f1 - f0) * u
    phase = 2 * np.pi * np.cumsum(freq) / A.SR
    g = np.sin(phase) * np.where(t < glide * 1.6, np.sin(np.pi * np.clip(t / (glide * 1.6), 0, 1)) ** 0.7, 0.0)
    fb = 1200.0 * rng.uniform(0.85, 1.2)
    bubble = np.sin(2 * np.pi * fb * t + rng.uniform(0, 6)) * A.exp_decay(n, rng.uniform(0.15, 0.35)) * A.rise(n, 0.004)
    y = 0.9 * g + 0.45 * bubble
    y = A.lowpass(y, 7000.0, 2, pad=A.SR // 4)
    return A.finish_oneshot(y, A.ONESHOT_DB, 0.001, 0.15)


def drip_stone(seed):
    """A 3 ms click band-passed 2-4 kHz, plus a faint stone-body tick, so it reads as a drop on stone."""
    rng = A.rng_for(seed)
    n = A.nsamp(0.4)
    centre = rng.uniform(2200.0, 3600.0)
    m = A.nsamp(0.003)
    click = A.bandpass(rng.standard_normal(m * 16), centre * 0.75, centre * 1.2, 2, pad=m)[:m * 8]
    click = click[:A.nsamp(0.006)]
    click = click * np.exp(-np.arange(click.size) / (0.0010 * A.SR))
    y = np.zeros(n)
    y[:click.size] = click / (np.max(np.abs(click)) + 1e-12)
    t = A.tvec(n)
    body = np.sin(2 * np.pi * rng.uniform(700.0, 1500.0) * t) * A.exp_decay(n, rng.uniform(0.03, 0.07))
    y += 0.25 * body
    return A.finish_oneshot(y, A.ONESHOT_DB, 0.0003, 0.05)


def build(entries, out_dir=None):
    print("[rooms]")
    notes = {
        "Crypt": "Very dark: a 40 Hz throb, dull air and far-off dripping water with a damp tail. Oppressive, should be felt more than heard.",
        "Chapel": "Quiet air with a faint hollow wind through the roof hole (nothing below 300 Hz in the wind part).",
        "Cloister": "Light open air, almost nothing. The calmest of the six.",
        "Passage": "Tight air with a faint low draught drifting around 180 Hz.",
        "Tower": "Low hollow air plus a distant howl gliding around 450 Hz.",
        "Belfry": "Open and windy: audible wind and howl, almost no air bed. The most exposed of the six.",
    }
    base = {"crypt": 6001, "chapel": 6002, "cloister": 6003, "passage": 6004, "tower": 6005, "belfry": 6006}
    for room in ("crypt", "chapel", "cloister", "passage", "tower", "belfry"):
        x, seed = make_room(room, base[room])
        A.emit(entries, "SFX_LB_Room_" + room.capitalize(), GROUP, x, loop=True, seed=seed, out_dir=out_dir,
               listen=notes[room.capitalize()])
    for i, seed in enumerate(range(6101, 6106), 1):
        A.emit(entries, "SFX_LB_Drip_Water_%02d" % i, GROUP, drip_water(seed), loop=False, seed=seed, out_dir=out_dir,
               listen="A single water drip: a quick rising 'bloop' then a short bubble ring. Compare the 5: each pitch/length differs.")
    for i, seed in enumerate(range(6201, 6206), 1):
        A.emit(entries, "SFX_LB_Drip_Stone_%02d" % i, GROUP, drip_stone(seed), loop=False, seed=seed, out_dir=out_dir,
               listen="A tiny hard 'tick' of water on stone with a faint body. Dry and short; should not sound like a click track.")
    return entries


if __name__ == "__main__":
    build([])
