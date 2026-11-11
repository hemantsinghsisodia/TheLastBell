# Tools/audio/prep: recorded audio prep (Phase 16, task A3)

Turns the CC0 downloads (Kenney Impact Sounds, Kenney RPG Audio, 58 Freesound files; all git-ignored under `ExternalAssets/Incoming/`) into the
**K / F** cues of `Docs/plans/P16_AUDIO.md` section 3: `SourceArt/Audio/Recorded/<cue>.wav` (48 kHz, 16-bit; 142 files: 124 + the 18 creature cues of P16-6). Every output is
described by one entry in `recipes.json`, so it can be rebuilt exactly (deterministic: the same inputs give byte-identical WAVs, `--verify` proves it).

## Requirements
Python 3.12+ with `numpy` and `Pillow` (**no scipy**, so isolated mode `-I` works), plus `ffmpeg`/`ffprobe` on PATH (decoding and the 48 kHz resample of the
raw files). Raw downloads are untrusted data: they are only decoded by ffmpeg, never executed, and paths are passed as arguments.

## Rebuild (run from the repo root)
```
python -I Tools/audio/prep/prep_recorded.py                     # all 142 files + SourceArt/Audio/Recorded/manifest.json (about 15 s)
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

## Thunder cracks (P16-5: `prep_cracks.py`, `crack_recipes.json`)
The owner rejected the synthetic cracks of `SFX_LB_Thunder_Near_*` and `SFX_LB_Thunder_Strike_*`. `prep_cracks.py` finds the crack onset of five Freesound CC0 recordings
(first 2 ms frame above `peak + rel_db`, then back to where the rise began), cuts `onset - 10 ms` .. `onset + len` (the end moved to the quietest 10 ms frame nearby, fade-out 90-100 ms) and
produces: `SFX_LB_Thunder_CrackLayer_01..04` (intermediates in `SourceArt/Audio/Cracks/`, **not imported**), and the cut Strike signals. The final `Thunder_Near_*` (recorded crack layer at t = 0
over the generated rumble of the same seed, rumble peak 0.85 against the crack's 1.0, -3 dBFS peak) and `Thunder_Strike_*` are written by `Tools/audio/gen/thunder.py` (`CRACKS = "recorded"`), so
`python -I Tools/audio/gen/build_all.py --group thunder --no-audition` reproduces them (manifest entries carry a `composition` record). `--audition` edits the Near/Strike rows of
`Docs/ArtTest/audio/audition.md` and adds the crack-layer section; then `python -I Tools/audio/make_audition_page.py`. `--diag` prints the envelope around each onset; `--verify` proves determinism.

## Creature ambience (P16-6, D-112; recipe group `creatures`)
`SFX_LB_Bat_01..06`, `Owl_01..04`, `Howl_01..03`, `Rat_01..05` (18 mono files, -3 dBFS peak) are items of `recipes.json` written by `build_recipes.py` (section "creature ambience"); nothing else in the recipes changed (the 124 older files are byte-identical).
Two additions to the engine: a layer key `denoise` (a dict for `prep_lib.spectral_gate`: spectral subtraction, the noise profile being the 15th percentile of each bin's power over the slice, `reduce_db` = depth of the floor, `oversub` = how hard) used on the noisy sources (437935 tape hiss, 688869 / 640060 / 333094 / 841571 field noise, 500646 lightly), and the existing `lp` / `tail` post chain used for distance (owls: 5 kHz low-pass and a 0.7 s tail; howls: 3 kHz and a 3 s tail with slow fades).
Slice choices come from per-source surveys (band-limited envelope events plus spectrograms); the picks are in each item's `note`. Sources rejected or kept as spares are in `Docs/ASSET_REGISTRY.md` (404152, 867131, 503516).

## Cinematic music (P17, `prep_cine_music.py`)
The owner's three Freesound CC0 tracks (git-ignored in `ExternalAssets/Incoming/audio/p17_music/`) become `SourceArt/Audio/Music/MUS_LB_Cine_IntroText.wav` (Dasgoat 330599, 0:00-0:40, no baked fade; 3.10), `MUS_LB_Cine_Finale.wav` (szegvari 610534, 5.1 down-mixed, 96 -> 48 kHz, first 0:55) and `MUS_LB_Cine_Credits.wav` (CVLTIV8R 839571, 45.013 s), all 48 kHz stereo 16-bit at a -3 dBFS peak (`python -I Tools/audio/prep/prep_cine_music.py [--verify]`; deterministic). They live in their own folder, not in `Recorded/`, because `report_recorded.py` flags any WAV that is not in `recipes.json`; `Tools/audio/p16_2_assets.py` imports the folder as a third source. The 5.1 down-mix is L = FL + 0.707 FC + 0.707 BL, R = FR + 0.707 FC + 0.707 BR with the LFE dropped (ffprobe reports the layout "5.1", i.e. FL FR FC LFE BL BR; the back pair serves as the surround pair).

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
Creatures (P16-6): `404152` (noise-gated cave blocks, one harmonic scream), `867131` (ke-wick sweeps, not hoots) and the spare `503516` (a pitch-shifted dog, f0 about 430 Hz).
Freesound `669449` (stone scrape, only 0.6 s of sound) and `834029` (metal steps, quieter and thinner than `698697`, which already gave all six) are downloaded but unused. All other 56 Freesound files and 36 Kenney files are used; see `Docs/ASSET_REGISTRY.md`.

Output WAVs are LFS-tracked (`*.wav`). Listening notes and weak spots: `Docs/ArtTest/audio/audition_recorded.md`.
