"""Rain beds: SFX_LB_Rain_Out and SFX_LB_Rain_In (plan P16_AUDIO section 4.1). 60 s stereo loops, seeded."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

import audio_lib as A  # noqa: E402

GROUP = "rain"

# Values section 4.1 leaves open (chosen here, tune on the audition):
BED_LEVEL_DB = -30.0        # layer 1 RMS before the final loudness normalisation; the drops sit ~6 dB under it
SPLATTER_DB = -34.0         # layer 3 RMS, given in the recipe
DROP_MEAN_DB = -30.0        # layer 2 mean drop amplitude, given in the recipe
RAIN_IN_DROP_MEAN_DB = -30.0  # Rain_In small roof drops mean amplitude
RAIN_IN_BIG_DRIP_DB = -22.0   # Rain_In big drip (plink) mean amplitude
LOOP_SECONDS = 60.0


def rain_bed(rng, n):
    """Layer 1, stereo: pink noise band-passed 400-9000 Hz (4th order), slow +-1.5 dB walk (0.1-0.3 Hz), L/R independent."""
    chans = []
    for _ in range(2):
        x = A.pink(rng, n)
        x = A.bandpass(x, 400.0, 9000.0, 4)
        x = x * A.walk_db(rng, n, 0.1, 0.3, 1.5)
        chans.append(x / A.rms(x) * A.from_db(BED_LEVEL_DB))
    return A.stereo(*chans)


def render_rain_out(seed, n):
    rng = A.rng_for(seed)
    out = rain_bed(rng, n)
    for ch in range(2):
        # layer 2: drop transients, 900/s per channel, 2-6 ms bursts at 2-7 kHz, exponential amplitudes
        out[:, ch] += A.poisson_bursts(rng, n, 900.0, (2000.0, 7000.0), (0.002, 0.006), A.from_db(DROP_MEAN_DB))
        # layer 3: low splatter, noise 150-600 Hz
        sp = A.bandpass(A.white(rng, n), 150.0, 600.0, 4)
        out[:, ch] += sp / A.rms(sp) * A.from_db(SPLATTER_DB)
    return out


def render_rain_in(seed, n):
    rng = A.rng_for(seed)
    bed = rain_bed(rng, n)
    out = A.lowpass(bed, 1800.0, 4) * A.from_db(-8.0)  # muffled roof: layer 1 low-passed at 1800 Hz, -8 dB
    for ch in range(2):
        # heavier, slower drops: 220/s, 1-3 kHz, 8-15 ms
        out[:, ch] += A.poisson_bursts(rng, n, 220.0, (1000.0, 3000.0), (0.008, 0.015), A.from_db(RAIN_IN_DROP_MEAN_DB))
        # occasional big drips: 0.5/s, 400-900 Hz plinks (60-140 ms ring)
        out[:, ch] += A.poisson_bursts(rng, n, 0.5, (400.0, 900.0), (0.06, 0.14), A.from_db(RAIN_IN_BIG_DRIP_DB),
                                       amp_cap=2.0)
    return out


def build(entries, out_dir=None):
    print("[rain]")
    x, info = A.make_loop(render_rain_out, [2001 + 100 * k for k in range(6)], LOOP_SECONDS, A.BED_DB)
    A.emit(entries, "SFX_LB_Rain_Out", GROUP, x, loop=True, seed=info["seed"], out_dir=out_dir,
           listen="Steady wide hiss with fine sizzle and low splatter, no obvious repeat or pumping. Bright, close.")
    x, info = A.make_loop(render_rain_in, [2002 + 100 * k for k in range(6)], LOOP_SECONDS, A.BED_DB)
    A.emit(entries, "SFX_LB_Rain_In", GROUP, x, loop=True, seed=info["seed"], out_dir=out_dir,
           listen="Same rain heard through a roof: dull, slower patter plus a few big drips (plinks). Should read as 'under cover'.")
    return entries


if __name__ == "__main__":
    build([])
