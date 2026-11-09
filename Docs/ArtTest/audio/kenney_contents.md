# Kenney CC0 audio: relevant contents (Phase 16, task A1)

Both packs are downloaded and unzipped under `ExternalAssets/Incoming/` (git-ignored). Only the licence text and the file names were read; nothing from the packs was executed.

| Pack | Page | Zip | Local path | Files | Licence line |
|---|---|---|---|---|---|
| Impact Sounds 1.0 | https://kenney.nl/assets/impact-sounds | 800,850 bytes, sha256 `029d734af158...de77f8` | `ExternalAssets/Incoming/kenney-impact-sounds/` (zip + `extracted/`) | 130 `.ogg` + `License.txt` + 2 `.url` | `License: (Creative Commons Zero, CC0)` with `http://creativecommons.org/publicdomain/zero/1.0/` |
| RPG Audio | https://kenney.nl/assets/rpg-audio | 964,837 bytes, sha256 `6dbeaf8544da...75f38b` | `ExternalAssets/Incoming/kenney-rpg-audio/` (zip + `extracted/`) | 52 `.ogg` (incl. `Preview.ogg`) + `License.txt` + 2 `.url` | `License (Creative Commons Zero, CC0)` with `http://creativecommons.org/publicdomain/zero/1.0/` |

Download note: kenney.nl serves the zip through a one-time signed link (`https://kenney.nl/download-link/<hex of "assets/<slug>">`, then `https://kenney.nl/download/<id>/<token>?expires=...`), so a permanent direct `.zip` URL does not exist; the pack page above is the stable source.

Format note: **both packs are OGG Vorbis, stereo, 44.1 kHz (Impact Sounds) or 48 kHz (RPG Audio).** There are no WAV files. A3 must convert them to 48 kHz 16-bit WAV (mono for 3D sounds) with the prep script (ffmpeg is available). Paths below are relative to each pack's `extracted/Audio/` folder.

## K mapping to the cue sheet

| Cue | Pack | Files (variants) | Notes |
|---|---|---|---|
| `SFX_LB_Step_Stone_01..06` | Impact | `footstep_concrete_000..004` (5), 0.11 s | Only 5 variants. 6th: pitch one 0.97 / 1.04 or use a `impactGeneric_light_00x` layered at low gain. |
| `SFX_LB_Step_Wood_01..06` | Impact | `footstep_wood_000..004` (5), 0.25 s | 5 variants; 6th by pitch shift. |
| `SFX_LB_Step_Grass_01..06` | Impact | `footstep_grass_000..004` (5), 0.6 to 0.8 s | 5 variants; 6th by pitch shift. |
| `SFX_LB_Step_Earth_01..06` (K/F) | RPG Audio | `footstep00..09` (10), 0.22 to 0.32 s | Boot-on-ground steps; the surface is not labelled in the pack. **To confirm by ear in A4.** If too dry or too bright for earth, use grass pitched down or the Freesound gravel fallback (352870, 505831). |
| `SFX_LB_Step_Metal_01..06` (K/F) | Impact | no metal footsteps. Stopgap: `impactPlate_light_000..004` (0.54 s), `impactMetal_light_000..004` (0.35 s) shortened | Prefer Freesound 834029 / 698697 (see `freesound_list.md`). |
| `SFX_LB_Step_Water` | none | no water sounds in either pack | Freesound only. |
| `SFX_LB_Generic_Use_01..03` | RPG Audio | `handleSmallLeather`, `handleSmallLeather2`, `beltHandle1`, `beltHandle2`, `metalClick`, `metalLatch` | Short tactile hand sounds, 0.26 to 0.45 s; choose three in A4. Impact `impactGeneric_light_000..004` (0.14 s) as a 4th option. |
| `SFX_LB_Warden_Step_01..05` (F/K) | Impact | `impactWood_heavy_000..004` (0.31 s), `impactSoft_heavy_000..004` (0.5 s), `impactPunch_heavy_000..004` (0.65 s), `impactMining_000..004` (0.94 s) | Pitch down 25 to 35 percent and layer a stone hit (`footstep_concrete`) plus a low sub; best as the thump layer of the Freesound monster steps. |

## Extra helpers (stand-ins if a Freesound row is skipped)

| Cue | Pack | Files |
|---|---|---|
| `SFX_LB_Lever_Notch`, ratchet tick | RPG | `metalClick` (0.45 s), `metalLatch` (0.26 s) |
| `SFX_LB_Creak_Wood` | RPG | `creak1` (0.66 s), `creak2` (0.83 s), `creak3` (0.34 s) |
| `SFX_LB_Door_Wood_Open`, closing | RPG | `doorOpen_1` (0.92 s), `doorOpen_2` (1.41 s), `doorClose_1..4` |
| `SFX_LB_Paper` | RPG | `bookFlip1..3`, `bookOpen`, `bookClose`, `bookPlace1..3` |
| `SFX_LB_Warden_Robe` | RPG | `cloth1..4` (0.38 to 0.66 s), `clothBelt`, `clothBelt2` (short; a looping robe bed needs the Freesound rustle) |
| `SFX_LB_Key_Pickup` | RPG | `handleCoins`, `handleCoins2` (coin-like; Freesound keys preferred) |
| Bell-like metal hits | Impact | `impactBell_heavy_000..004` (1.48 s): test material only, the bells are generated (plan section 4.4) |

Not usable for this project's tone: `impactGlass_*`, `impactTin_*`, `impactPunch_medium_*`, `drawKnife*`, `knifeSlice*`, `chop`, `handleCoins`.

## File lists

Impact Sounds (`Audio/`): `footstep_{carpet,concrete,grass,snow,wood}_000..004`; `impactBell_heavy_000..004`; `impactGeneric_light_000..004`; `impactGlass_{heavy,light,medium}_000..004`; `impactMetal_{heavy,light,medium}_000..004`; `impactMining_000..004`; `impactPlank_medium_000..004`; `impactPlate_{heavy,light,medium}_000..004`; `impactPunch_{heavy,medium}_000..004`; `impactSoft_{heavy,medium}_000..004`; `impactTin_medium_000..004`; `impactWood_{heavy,light,medium}_000..004` (130 files).

RPG Audio (`Audio/`): `beltHandle1..2`, `bookClose`, `bookFlip1..3`, `bookOpen`, `bookPlace1..3`, `chop`, `cloth1..4`, `clothBelt`, `clothBelt2`, `creak1..3`, `doorClose_1..4`, `doorOpen_1..2`, `drawKnife1..3`, `dropLeather`, `footstep00..09`, `handleCoins`, `handleCoins2`, `handleSmallLeather`, `handleSmallLeather2`, `knifeSlice`, `knifeSlice2`, `metalClick`, `metalLatch`, `metalPot1..3`, `Preview` (52 files, the `Preview.ogg` is not a game sound).
