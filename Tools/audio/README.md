# Tools/audio: procedural audio generators (Phase 16, task A2)

`Tools/audio/gen/` renders the **G** (generated) cues of `Docs/plans/P16_AUDIO.md` section 3/4 offline: rain, wind, thunder,
bells, music and room tones/drips. Seeded and deterministic: the same code and the same numpy give byte-identical WAVs.

## Requirements
- Python 3.12+ (developed on 3.14: `C:\Users\heman\AppData\Local\Python\pythoncore-3.14-64\python.exe`).
- `numpy` (2.x) and `Pillow` (spectrogram sheets). **No scipy is needed**: all filters are zero-phase FFT filters in `audio_lib.py`.

## Rebuild
Run from the repo root. `-I` (isolated mode) is fine; every script adds its own folder to `sys.path`.

```
python -I Tools/audio/gen/build_all.py --group all          # everything: about 3 minutes
python -I Tools/audio/gen/build_all.py --group bells        # one group: rain | wind | thunder | bells | music | rooms
python -I Tools/audio/gen/build_all.py --group all --verify # build twice into temp folders and compare SHA-256 (writes nothing in the repo)
python -I Tools/audio/gen/checks.py                         # objective checks on the written WAVs (145 checks)
```

## Outputs
| What | Where |
|---|---|
| WAVs, 48 kHz 16-bit PCM (LFS-tracked), named by the cue sheet | `SourceArt/Audio/Generated/<cue>.wav` |
| Per-file measurements (length, channels, RMS, peak, DC, loop seam, chosen seed) | `SourceArt/Audio/Generated/manifest.json` |
| Spectrogram contact sheet per group | `Docs/ArtTest/audio/gen_<group>.png` |
| Owner audition page (table per group, links to the WAVs) | `Docs/ArtTest/audio/audition.md` |

`audition.md` and the manifest are regenerated from `manifest.json` on every build, so building one group keeps the others.

## Files
- `audio_lib.py`: WAV writer (seeded TPDF dither), white/pink/brown noise, band/low/high-pass and resonant filters, a time-varying
  resonant band-pass (wind), envelopes, random walks, soft clip, synthetic exponential-noise reverb (FFT convolution),
  equal-power loop fold, seam checks, loudness normalisation.
- `rain.py`, `wind.py`, `thunder.py`, `bells.py`, `music.py`, `rooms.py`: one script per group (each also runs alone).
- `build_all.py`: driver. `sheets.py`: spectrograms and the audition page. `checks.py`: the objective checks.

## Rules the generators follow
- Loops: render length + 2 s and fold the tail into the start with an equal-power crossfade; tonal loops use frequencies snapped to a
  whole number of cycles per loop, so they repeat sample-exactly. The seam step (RMS of the first 0.5 s against the last 0.5 s)
  is gated at under 0.5 dB by trying up to 6-8 seeds (the seed that was used is in the manifest). `MUS_LB_Chase` is the one
  exception by design (see audition notes): it loops on the beat at exactly 384000 samples.
- Loudness (section 3): beds -24 dBFS RMS, music loops -22 dBFS RMS, one-shots (including the stings) -3 dBFS peak.
  "Level" values from section 4 (bell stages -18/-14/-10/-6/0 dB, Far thunder -8 dB) are **not** baked in: they are recorded as
  `mix_gain_db` in the manifest and shown on the audition page, to be applied in the mix (section 3: balancing is done in the mix).
- Mono for 3D one-shots (thunder, bells, drips), stereo for beds and music (including stings).

## Changing a sound
Every tunable value sits in a named constant at the top of its script with a comment (values the plan leaves open are marked
"chosen"). Edit, rebuild that group, run `checks.py`, listen. Rebuilding changes only that group's WAVs.
