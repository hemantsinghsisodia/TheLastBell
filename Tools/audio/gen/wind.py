"""Wind beds: SFX_LB_Wind (60 s) and SFX_LB_Wind_Howl (45 s), stereo loops (plan section 4.2)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

import audio_lib as A  # noqa: E402

GROUP = "wind"

# Values section 4.2 leaves open:
WIND_BANDS = ((250.0, 1.0), (700.0, 0.6))  # (centre Hz, relative weight) of the two resonant band-passes
WIND_Q = (2.0, 4.0)                        # Q drifts between these on its own slow walk
HOWL_AMP_DB = 4.0                          # the howl breathes +-4 dB on a 0.05-0.2 Hz walk
HOWL_PHASE_OFFSET = 0.9                    # radians between the L and R glides (stereo width)
WIND_LOOP_S = 60.0
HOWL_LOOP_S = 45.0


def wind_raw(rng, n):
    """Stereo wind, unit RMS, no loop handling. White noise -> two resonant band-passes whose centres drift +-30 %
    (0.05-0.2 Hz walk) with their own +-6 dB amplitude walks. Each channel has independent noise and walks."""
    chans = []
    for _ in range(2):
        total = np.zeros(n)
        for centre, weight in WIND_BANDS:
            fc = centre * A.walk_frac(rng, n, 0.05, 0.2, 0.30)
            q = 0.5 * (WIND_Q[0] + WIND_Q[1]) + 0.5 * (WIND_Q[1] - WIND_Q[0]) * A.lowband(rng, n, 0.05, 0.2)
            y = A.tv_resonant_bp(A.white(rng, n), fc, q)
            y = y / A.rms(y) * A.walk_db(rng, n, 0.05, 0.2, 6.0)
            total += weight * y
        chans.append(total / A.rms(total))
    return A.stereo(*chans)


def howl_raw(rng, n, wind=None):
    """Stereo howl, unit RMS: Q 12 band-pass gliding 380-520 Hz at 0.07 Hz, plus 20 % of the wind."""
    t = A.tvec(n)
    chans = []
    for ch in range(2):
        fc = 450.0 + 70.0 * np.sin(2 * np.pi * 0.07 * t + HOWL_PHASE_OFFSET * ch + rng.uniform(0, 6.28))
        y = A.tv_resonant_bp(A.white(rng, n), fc, 12.0)
        y = y / A.rms(y) * A.walk_db(rng, n, 0.05, 0.2, HOWL_AMP_DB)
        chans.append(y / A.rms(y))
    howl = A.stereo(*chans)
    if wind is None:
        wind = wind_raw(rng, n)
    out = howl + 0.2 * wind
    return out / A.rms(out)


def render_wind(seed, n):
    return wind_raw(A.rng_for(seed), n)


def render_howl(seed, n):
    return howl_raw(A.rng_for(seed), n)


def build(entries, out_dir=None):
    print("[wind]")
    x, info = A.make_loop(render_wind, [3001 + 100 * k for k in range(8)], WIND_LOOP_S, A.BED_DB)
    A.emit(entries, "SFX_LB_Wind", GROUP, x, loop=True, seed=info["seed"], out_dir=out_dir,
           listen="Slow breathing wind: two drifting hollow bands (low ~250 Hz, mid ~700 Hz), gusts swelling and fading, "
                  "L and R not identical. No whistling, no repeat.")
    x, info = A.make_loop(render_howl, [3002 + 100 * k for k in range(8)], HOWL_LOOP_S, A.BED_DB)
    A.emit(entries, "SFX_LB_Wind_Howl", GROUP, x, loop=True, seed=info["seed"], out_dir=out_dir,
           listen="Narrow eerie tone gliding between ~380 and ~520 Hz (about every 14 s) over a little wind. "
                  "Tower / belfry howl: should be unsettling but not a pure whistle.")
    return entries


if __name__ == "__main__":
    build([])
