# Tools/audio/prep: recorded audio prep (Phase 16, task A3)

Turns the CC0 downloads (Kenney Impact Sounds, Kenney RPG Audio, 58 Freesound files; all git-ignored under `ExternalAssets/Incoming/`) into the
**K / F** cues of `Docs/plans/P16_AUDIO.md` section 3: `SourceArt/Audio/Recorded/<cue>.wav` (48 kHz, 16-bit; 124 files). Every output is
described by one entry in `recipes.json`, so it can be rebuilt exactly (deterministic: the same inputs give byte-identical WAVs, `--verify` proves it).

## Requirements
Python 3.12+ with `numpy` and `Pillow` (**no scipy**, so isolated mode `-I` works), plus `ffmpeg`/`ffprobe` on PATH (decoding and the 48 kHz resample of the
raw files). Raw downloads are untrusted data: they are only decoded by ffmpeg, never executed, and paths are passed as arguments.

## Rebuild (run from the repo root)
```
python -I Tools/audio/prep/prep_recorded.py                     # all 124 files + SourceArt/Audio/Recorded/manifest.json (about 15 s)
python -I Tools/audio/prep/prep_recorded.py --only Warden_Roar  # only items whose name contains the text
python -I Tools/audio/prep/prep_recorded.py --verify            # build twice into temp folders, compare SHA-256 (writes nothing in the repo)
python -I Tools/audio/prep/report_recorded.py                   # objective checks + Docs/ArtTest/audio/rec_<group>.png + audition_recorded.md
python -I Tools/audio/prep/report_recorded.py --checks          # checks only (exit code 1 on any failure)
python -I Tools/audio/prep/prep_recorded.py --tune <loop name>  # scan the loop start offset for the best seam (how the breath loops were placed)
```

## Files
| File | What |
|---|---|
| `recipes.json` | The source of truth: one item per output file (layers with source alias, slice start/end in the source, gain, pitch factor, delay, hp/lp, fades, rising gain envelope, glide; post chain: sub, lp/hp, leveller, room tail; loop length and crossfade; target loudness; channels). |
| `prep_recorded.py` | The engine that executes `recipes.json`. |
| `prep_lib.py` | numpy DSP: ffmpeg decode, FFT filters, FFT resampling (pitch), room tail, equal-power loop crossfade, trim, fades, leveller, soft limiter, seam/DC/click metrics. |
| `build_recipes.py` | How the recipes were authored (slice times chosen with `survey.py`). Rewrites `recipes.json`; edit it, then rebuild. |
| `survey.py` | Authoring helper: per source prints duration, peak, noise floor and energy segments, and writes a spectrogram PNG: `python -I Tools/audio/prep/survey.py <out_dir> <file...> [--rel dB --gap s --band lo hi --pr dB]`. |
| `report_recorded.py` | Objective checks, contact sheets and the audition page (`Docs/ArtTest/audio/audition_recorded.md`). |

## Source aliases in `recipes.json`
`fs:<id>` = `ExternalAssets/Incoming/freesound/<id>__*` · `ki:<name>` = `ExternalAssets/Incoming/kenney-impact-sounds/extracted/Audio/<name>.ogg` ·
`kr:<name>` = `ExternalAssets/Incoming/kenney-rpg-audio/extracted/Audio/<name>.ogg`.

## Processing (plan section 5.4)
1. **Per layer:** slice, remove DC, high-pass (default 30 Hz; 50-90 Hz for steps, breath, voices), optional low-pass, pitch change by resampling (0.75 = 25 % lower AND longer, as asked for large creatures), optional glide, rising gain envelope, level (`norm`), fades.
2. **Mix** layers at their delays; optional **sub** (a 50 Hz sine following the low-passed envelope of the mix, -12 dB under the mix), leveller, **room tail** (seeded exponential-decay noise IR, low-passed).
3. **One-shots:** normalise, trim silence at -50 dBFS with 20 ms pads, cap at `max_len`, fade in 5 ms / out 30 ms (longer where set), remove residual DC, normalise to a **-3 dBFS peak**.
4. **Loops** (Warden breath Slow/Fast/Heavy, robe): equal-power crossfade of the head with the audio after the loop end (so the end flows into the start), normalise to **-24 dBFS RMS**, soft-limit so the peak stays under -1 dBFS.
5. **Channels:** mono for all 3D sounds and the player breath (mono-centred 2D); stereo only for `SFX_LB_Paper_01..03`.
6. 16-bit rounding, no dither.

## Objective checks (`report_recorded.py`)
48 kHz / 16-bit / expected channel count; no clipped samples; peak <= -1 dBFS; |DC| < 0.001; first and last sample < 0.003 (no boundary click);
largest sample jump versus the 99.9th-percentile jump (internal click detector); loudness within 1 dB of target; loop seam (first 0.5 s against last 0.5 s, < 0.5 dB, and a wrap click ratio < 8); variant counts equal the cue sheet.

## Sources not used
Freesound `669449` (stone scrape, only 0.6 s of sound) and `834029` (metal steps, quieter and thinner than `698697`, which already gave all six) are downloaded but unused. All other 56 Freesound files and 36 Kenney files are used; see `Docs/ASSET_REGISTRY.md`.

Output WAVs are LFS-tracked (`*.wav`). Listening notes and weak spots: `Docs/ArtTest/audio/audition_recorded.md`.
