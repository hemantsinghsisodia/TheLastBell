# Recorded audio: audition (A3)

Built by `Tools/audio/prep/prep_recorded.py` from `Tools/audio/prep/recipes.json` (CC0 Freesound and Kenney sources, see `Docs/ASSET_REGISTRY.md`); objective checks by `Tools/audio/prep/report_recorded.py`. WAVs are 48 kHz 16-bit in `SourceArt/Audio/Recorded/`: mono for 3D sounds (player breath is mono-centred 2D, paper is stereo 2D). One-shots are normalised to a -3 dBFS peak, loops to -24 dBFS RMS; level balance is the mix's job.

Turn the volume down before the Warden roars, spotted, caught and windup files. For each cue decide **keep**, **redo** (say what to change) or **replace**.

**Columns.** *Src* = Freesound id (plain number) or Kenney file (`ki:` Impact, `kr:` RPG). *Peak* / *RMS* are measured on the written file. *Seam* (loops) = level step between the first and last 0.5 s (target < 0.5 dB).


## Player footsteps (36)

![spectrograms](rec_steps.png)

| File | Len | Ch | Peak | RMS | Src | What to listen for | Weak / note | Keep / redo / replace |
|---|---|---|---|---|---|---|---|---|
| [SFX_LB_Step_Stone_01](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Stone_01.wav) | 0.10 s | 1 | -3.0 | -19.6 | ki:footstep_concrete_000 | Dull, short concrete thud (Kenney is very bass-heavy; may feel muffled on speakers). Six should not sound like a machine gun. 06 is a -5 % copy of 03. | Kenney concrete: very short and bass-heavy; originals near-identical (spread +-3 % pitch) (applies to the whole set) | |
| [SFX_LB_Step_Stone_02](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Stone_02.wav) | 0.11 s | 1 | -3.0 | -20.1 | ki:footstep_concrete_001 | as above |  | |
| [SFX_LB_Step_Stone_03](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Stone_03.wav) | 0.11 s | 1 | -3.0 | -20.5 | ki:footstep_concrete_002 | as above |  | |
| [SFX_LB_Step_Stone_04](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Stone_04.wav) | 0.11 s | 1 | -3.0 | -20.3 | ki:footstep_concrete_003 | as above |  | |
| [SFX_LB_Step_Stone_05](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Stone_05.wav) | 0.11 s | 1 | -3.0 | -20.4 | ki:footstep_concrete_004 | as above |  | |
| [SFX_LB_Step_Stone_06](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Stone_06.wav) | 0.12 s | 1 | -3.0 | -20.3 | ki:footstep_concrete_002 | as above | -5 % pitch copy of 03 (Kenney has 5) | |
| [SFX_LB_Step_Wood_01](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Wood_01.wav) | 0.08 s | 1 | -3.0 | -16.9 | ki:footstep_wood_000 | Hollow wood tap, very short. 06 is a -5 % pitched copy of 02. | weakest set: Kenney wood steps are only ~0.08 s of low thump with almost no top end, and the 5 originals are near-identical (spread +-3 % pitch) (applies to the whole set) | |
| [SFX_LB_Step_Wood_02](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Wood_02.wav) | 0.08 s | 1 | -3.0 | -16.6 | ki:footstep_wood_001 | as above |  | |
| [SFX_LB_Step_Wood_03](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Wood_03.wav) | 0.08 s | 1 | -3.0 | -16.4 | ki:footstep_wood_002 | as above |  | |
| [SFX_LB_Step_Wood_04](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Wood_04.wav) | 0.07 s | 1 | -3.0 | -16.5 | ki:footstep_wood_003 | as above |  | |
| [SFX_LB_Step_Wood_05](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Wood_05.wav) | 0.08 s | 1 | -3.0 | -16.0 | ki:footstep_wood_004 | as above |  | |
| [SFX_LB_Step_Wood_06](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Wood_06.wav) | 0.08 s | 1 | -3.0 | -16.4 | ki:footstep_wood_001 | as above | -5 % pitch copy of 02 (Kenney has 5) | |
| [SFX_LB_Step_Grass_01](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Grass_01.wav) | 0.18 s | 1 | -3.0 | -21.0 | ki:footstep_grass_000 | Soft crunch/brush, about 0.15 s. 06 is a -5 % pitched copy of 03. | Kenney grass: originals near-identical (spread +-3 % pitch) (applies to the whole set) | |
| [SFX_LB_Step_Grass_02](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Grass_02.wav) | 0.17 s | 1 | -3.0 | -20.4 | ki:footstep_grass_001 | as above |  | |
| [SFX_LB_Step_Grass_03](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Grass_03.wav) | 0.17 s | 1 | -3.0 | -21.2 | ki:footstep_grass_002 | as above |  | |
| [SFX_LB_Step_Grass_04](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Grass_04.wav) | 0.16 s | 1 | -3.0 | -21.1 | ki:footstep_grass_003 | as above |  | |
| [SFX_LB_Step_Grass_05](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Grass_05.wav) | 0.14 s | 1 | -3.0 | -21.8 | ki:footstep_grass_004 | as above |  | |
| [SFX_LB_Step_Grass_06](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Grass_06.wav) | 0.18 s | 1 | -3.0 | -21.1 | ki:footstep_grass_002 | as above | -5 % pitch copy of 03 (Kenney has 5) | |
| [SFX_LB_Step_Earth_01](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Earth_01.wav) | 0.22 s | 1 | -3.0 | -20.5 | kr:footstep09 | Dirt/gravel-ish boot step. Chosen by spectrum from RPG footstep00..09: confirm it reads as earth, not wood. | surface not labelled in the pack: picked by spectrum, needs an ear check (applies to the whole set) | |
| [SFX_LB_Step_Earth_02](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Earth_02.wav) | 0.28 s | 1 | -3.0 | -22.9 | kr:footstep04 | as above |  | |
| [SFX_LB_Step_Earth_03](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Earth_03.wav) | 0.23 s | 1 | -3.0 | -24.2 | kr:footstep02 | as above |  | |
| [SFX_LB_Step_Earth_04](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Earth_04.wav) | 0.24 s | 1 | -3.0 | -23.4 | kr:footstep00 | as above | source has 5 clipped samples in the slice | |
| [SFX_LB_Step_Earth_05](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Earth_05.wav) | 0.26 s | 1 | -3.0 | -22.4 | kr:footstep01 | as above | source has 17 clipped samples in the slice | |
| [SFX_LB_Step_Earth_06](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Earth_06.wav) | 0.23 s | 1 | -3.0 | -22.4 | kr:footstep06 | as above |  | |
| [SFX_LB_Step_Water_01](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Water_01.wav) | 0.50 s | 1 | -3.0 | -32.4 | 531566 | Splashy puddle step. 06 (849638) is a single drier step; check the six sit together. | source has 3 clipped samples in the slice | |
| [SFX_LB_Step_Water_02](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Water_02.wav) | 0.50 s | 1 | -3.0 | -30.0 | 531566 | as above |  | |
| [SFX_LB_Step_Water_03](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Water_03.wav) | 0.50 s | 1 | -3.0 | -31.4 | 531566 | as above | source has 3 clipped samples in the slice | |
| [SFX_LB_Step_Water_04](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Water_04.wav) | 0.48 s | 1 | -3.0 | -29.5 | 531566 | as above | source has 4 clipped samples in the slice | |
| [SFX_LB_Step_Water_05](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Water_05.wav) | 0.50 s | 1 | -3.0 | -24.0 | 531566 | as above |  | |
| [SFX_LB_Step_Water_06](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Water_06.wav) | 0.29 s | 1 | -3.0 | -29.9 | 849638 | as above |  | |
| [SFX_LB_Step_Metal_01](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Metal_01.wav) | 0.48 s | 1 | -3.0 | -24.9 | 698697 | Boot on a grate: ringing clank, 0.5 s. All six from one recording; check the ring does not smear at sprint cadence. |  | |
| [SFX_LB_Step_Metal_02](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Metal_02.wav) | 0.50 s | 1 | -3.0 | -24.6 | 698697 | as above |  | |
| [SFX_LB_Step_Metal_03](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Metal_03.wav) | 0.50 s | 1 | -3.0 | -25.7 | 698697 | as above |  | |
| [SFX_LB_Step_Metal_04](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Metal_04.wav) | 0.50 s | 1 | -3.0 | -24.8 | 698697 | as above |  | |
| [SFX_LB_Step_Metal_05](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Metal_05.wav) | 0.50 s | 1 | -3.0 | -24.3 | 698697 | as above |  | |
| [SFX_LB_Step_Metal_06](../../../SourceArt/Audio/Recorded/SFX_LB_Step_Metal_06.wav) | 0.50 s | 1 | -3.0 | -24.0 | 698697 | as above |  | |

## Player breath, candle, key, paper (33)

![spectrograms](rec_player.png)

| File | Len | Ch | Peak | RMS | Src | What to listen for | Weak / note | Keep / redo / replace |
|---|---|---|---|---|---|---|---|---|
| [SFX_LB_Breath_Calm_01](../../../SourceArt/Audio/Recorded/SFX_LB_Breath_Calm_01.wav) | 2.25 s | 1 | -3.0 | -20.6 | 336532 | Quiet slow breath through the nose/mouth, noise floor is audible when boosted: listen for hiss. One voice for all four. | very quiet source, noise floor boosted about 25 dB (applies to the whole set) | |
| [SFX_LB_Breath_Calm_02](../../../SourceArt/Audio/Recorded/SFX_LB_Breath_Calm_02.wav) | 1.80 s | 1 | -3.0 | -20.6 | 336532 | as above |  | |
| [SFX_LB_Breath_Calm_03](../../../SourceArt/Audio/Recorded/SFX_LB_Breath_Calm_03.wav) | 1.55 s | 1 | -3.0 | -19.5 | 336532 | as above |  | |
| [SFX_LB_Breath_Calm_04](../../../SourceArt/Audio/Recorded/SFX_LB_Breath_Calm_04.wav) | 1.60 s | 1 | -3.0 | -19.7 | 336532 | as above |  | |
| [SFX_LB_Breath_Heavy_01](../../../SourceArt/Audio/Recorded/SFX_LB_Breath_Heavy_01.wav) | 1.59 s | 1 | -3.0 | -21.9 | 386573 | Fast panting, 4 pulses each. Should feel like exertion, not comedy. | four slices of one panting loop: pulses are similar (applies to the whole set) | |
| [SFX_LB_Breath_Heavy_02](../../../SourceArt/Audio/Recorded/SFX_LB_Breath_Heavy_02.wav) | 1.50 s | 1 | -3.0 | -18.3 | 386573 | as above |  | |
| [SFX_LB_Breath_Heavy_03](../../../SourceArt/Audio/Recorded/SFX_LB_Breath_Heavy_03.wav) | 1.57 s | 1 | -3.0 | -18.2 | 386573 | as above |  | |
| [SFX_LB_Breath_Heavy_04](../../../SourceArt/Audio/Recorded/SFX_LB_Breath_Heavy_04.wav) | 1.36 s | 1 | -3.0 | -20.9 | 386573 | as above |  | |
| [SFX_LB_Breath_Panic_01](../../../SourceArt/Audio/Recorded/SFX_LB_Breath_Panic_01.wav) | 1.70 s | 1 | -3.0 | -22.8 | 831389 | Exhausted, ragged gasps. Distinct from Heavy by raggedness, not volume. |  | |
| [SFX_LB_Breath_Panic_02](../../../SourceArt/Audio/Recorded/SFX_LB_Breath_Panic_02.wav) | 1.80 s | 1 | -3.0 | -22.0 | 831389 | as above |  | |
| [SFX_LB_Breath_Panic_03](../../../SourceArt/Audio/Recorded/SFX_LB_Breath_Panic_03.wav) | 1.77 s | 1 | -3.0 | -23.9 | 831389 | as above |  | |
| [SFX_LB_Breath_Panic_04](../../../SourceArt/Audio/Recorded/SFX_LB_Breath_Panic_04.wav) | 1.90 s | 1 | -3.0 | -24.8 | 831389 | as above |  | |
| [SFX_LB_Breath_Gasp_01](../../../SourceArt/Audio/Recorded/SFX_LB_Breath_Gasp_01.wav) | 0.58 s | 1 | -3.0 | -19.7 | 271245 | Sharp inhale (candle going out). 02/03 are +-7 % pitch copies of 01: only one source recording. |  | |
| [SFX_LB_Breath_Gasp_02](../../../SourceArt/Audio/Recorded/SFX_LB_Breath_Gasp_02.wav) | 0.62 s | 1 | -3.0 | -19.7 | 271245 | as above | pitch copy (only one gasp recording) | |
| [SFX_LB_Breath_Gasp_03](../../../SourceArt/Audio/Recorded/SFX_LB_Breath_Gasp_03.wav) | 0.54 s | 1 | -3.0 | -19.7 | 271245 | as above | pitch copy (only one gasp recording) | |
| [SFX_LB_Candle_Light_01](../../../SourceArt/Audio/Recorded/SFX_LB_Candle_Light_01.wav) | 0.99 s | 1 | -3.0 | -29.3 | 423811 | Match strike / ignite: dry scrape then a small flame. Short. |  | |
| [SFX_LB_Candle_Light_02](../../../SourceArt/Audio/Recorded/SFX_LB_Candle_Light_02.wav) | 0.31 s | 1 | -3.0 | -24.9 | 237390, 386385 | as above | strike source is only 0.3 s long; flame whoosh layered on | |
| [SFX_LB_Candle_Light_03](../../../SourceArt/Audio/Recorded/SFX_LB_Candle_Light_03.wav) | 0.75 s | 1 | -3.0 | -26.0 | 398448 | as above |  | |
| [SFX_LB_Candle_Out_01](../../../SourceArt/Audio/Recorded/SFX_LB_Candle_Out_01.wav) | 0.33 s | 1 | -3.0 | -21.2 | 242867 | Soft blow and a puff: airy, not a spit. 02 is a very quiet source boosted 40 dB. |  | |
| [SFX_LB_Candle_Out_02](../../../SourceArt/Audio/Recorded/SFX_LB_Candle_Out_02.wav) | 0.56 s | 1 | -3.0 | -20.7 | 406648 | as above |  | |
| [SFX_LB_Candle_Out_03](../../../SourceArt/Audio/Recorded/SFX_LB_Candle_Out_03.wav) | 0.64 s | 1 | -3.0 | -17.8 | 656818 | as above |  | |
| [SFX_LB_Candle_Relight](../../../SourceArt/Audio/Recorded/SFX_LB_Candle_Relight.wav) | 0.38 s | 1 | -3.0 | -19.2 | 386385 | Soft flame whoosh. |  | |
| [SFX_LB_Key_Pickup_01](../../../SourceArt/Audio/Recorded/SFX_LB_Key_Pickup_01.wav) | 0.47 s | 1 | -3.0 | -24.8 | 788310 | Jingle of keys, bright. 2D. |  | |
| [SFX_LB_Key_Pickup_02](../../../SourceArt/Audio/Recorded/SFX_LB_Key_Pickup_02.wav) | 0.41 s | 1 | -3.0 | -24.8 | 248037 | as above |  | |
| [SFX_LB_Paper_01](../../../SourceArt/Audio/Recorded/SFX_LB_Paper_01.wav) | 0.38 s | 2 | -3.0 | -31.4 | 353125 | Rustle of a note, stereo, 2D. P16-6 re-slice: the crumple starts at once (first -10 dB at 0.07 s, peak at 0.15 s); check it lands with the pick-up and the put-down. |  | |
| [SFX_LB_Paper_02](../../../SourceArt/Audio/Recorded/SFX_LB_Paper_02.wav) | 1.18 s | 2 | -3.0 | -30.6 | 181774 | as above; starts at the first crackle (-10 dB at 0.03 s, peak at 0.12 s). |  | |
| [SFX_LB_Paper_03](../../../SourceArt/Audio/Recorded/SFX_LB_Paper_03.wav) | 0.47 s | 2 | -3.0 | -34.3 | 449127 | as above; sharp onset (-10 dB at 0.09 s, peak at 0.11 s). |  | |

## Doors, levers, winch, stone grind, generic use (28)

![spectrograms](rec_interact.png)

| File | Len | Ch | Peak | RMS | Src | What to listen for | Weak / note | Keep / redo / replace |
|---|---|---|---|---|---|---|---|---|
| [SFX_LB_Door_Wood_Open_01](../../../SourceArt/Audio/Recorded/SFX_LB_Door_Wood_Open_01.wav) | 2.80 s | 1 | -3.0 | -24.0 | 402464 | Heavy wooden door creaking open, 2.8-3 s. 03 is the same recording as 02 shifted +5 %. |  | |
| [SFX_LB_Door_Wood_Open_02](../../../SourceArt/Audio/Recorded/SFX_LB_Door_Wood_Open_02.wav) | 3.00 s | 1 | -3.0 | -23.8 | 273466 | as above |  | |
| [SFX_LB_Door_Wood_Open_03](../../../SourceArt/Audio/Recorded/SFX_LB_Door_Wood_Open_03.wav) | 2.90 s | 1 | -3.0 | -25.9 | 273466 | as above | pitch copy of another slice of the same recording | |
| [SFX_LB_Door_Stone_Open_01](../../../SourceArt/Audio/Recorded/SFX_LB_Door_Stone_Open_01.wav) | 3.00 s | 1 | -3.0 | -16.8 | 578491 | Continuous heavy stone grinding with rumble. Fade-out is 0.2 s: check the ending is not abrupt. |  | |
| [SFX_LB_Door_Stone_Open_02](../../../SourceArt/Audio/Recorded/SFX_LB_Door_Stone_Open_02.wav) | 2.95 s | 1 | -3.0 | -17.1 | 578491 | as above |  | |
| [SFX_LB_Door_Stone_Open_03](../../../SourceArt/Audio/Recorded/SFX_LB_Door_Stone_Open_03.wav) | 3.00 s | 1 | -3.0 | -17.2 | 833925 | as above |  | |
| [SFX_LB_Door_Locked_01](../../../SourceArt/Audio/Recorded/SFX_LB_Door_Locked_01.wav) | 1.10 s | 1 | -3.0 | -30.2 | 341303 | Handle rattle / lock refusal. 01 single short rattle, 02-03 multi-rattle. |  | |
| [SFX_LB_Door_Locked_02](../../../SourceArt/Audio/Recorded/SFX_LB_Door_Locked_02.wav) | 1.05 s | 1 | -3.0 | -24.0 | 235473 | as above |  | |
| [SFX_LB_Door_Locked_03](../../../SourceArt/Audio/Recorded/SFX_LB_Door_Locked_03.wav) | 1.20 s | 1 | -3.0 | -31.7 | 235473 | as above |  | |
| [SFX_LB_Lever_Notch_01](../../../SourceArt/Audio/Recorded/SFX_LB_Lever_Notch_01.wav) | 0.56 s | 1 | -3.0 | -21.0 | 696746 | Mechanical click/clunk. 03/04 are Kenney metal click/latch (04 layered with a lever). |  | |
| [SFX_LB_Lever_Notch_02](../../../SourceArt/Audio/Recorded/SFX_LB_Lever_Notch_02.wav) | 0.91 s | 1 | -3.0 | -19.2 | 835550 | as above |  | |
| [SFX_LB_Lever_Notch_03](../../../SourceArt/Audio/Recorded/SFX_LB_Lever_Notch_03.wav) | 0.36 s | 1 | -3.0 | -29.0 | kr:metalClick | as above |  | |
| [SFX_LB_Lever_Notch_04](../../../SourceArt/Audio/Recorded/SFX_LB_Lever_Notch_04.wav) | 0.47 s | 1 | -3.0 | -26.8 | 696746, kr:metalLatch | as above | source has 15 clipped samples in the slice | |
| [SFX_LB_Winch_01](../../../SourceArt/Audio/Recorded/SFX_LB_Winch_01.wav) | 2.24 s | 1 | -3.0 | -25.3 | 454148 | Ratchet / rope crank. 01 is metal ratchet, 02-03 are wooden crank takes. |  | |
| [SFX_LB_Winch_02](../../../SourceArt/Audio/Recorded/SFX_LB_Winch_02.wav) | 3.20 s | 1 | -3.0 | -21.1 | 491705 | as above |  | |
| [SFX_LB_Winch_03](../../../SourceArt/Audio/Recorded/SFX_LB_Winch_03.wav) | 3.20 s | 1 | -3.0 | -21.5 | 491705 | as above |  | |
| [SFX_LB_Stone_Grind_01](../../../SourceArt/Audio/Recorded/SFX_LB_Stone_Grind_01.wav) | 3.20 s | 1 | -3.0 | -24.0 | 844329 | Slab scrape: continuous rough grind, 3 s. |  | |
| [SFX_LB_Stone_Grind_02](../../../SourceArt/Audio/Recorded/SFX_LB_Stone_Grind_02.wav) | 3.35 s | 1 | -3.0 | -22.6 | 844329 | as above |  | |
| [SFX_LB_Stone_Grind_03](../../../SourceArt/Audio/Recorded/SFX_LB_Stone_Grind_03.wav) | 3.20 s | 1 | -3.0 | -18.3 | 844329 | as above |  | |
| [SFX_LB_Generic_Use_01](../../../SourceArt/Audio/Recorded/SFX_LB_Generic_Use_01.wav) | 0.22 s | 1 | -3.0 | -24.8 | kr:handleSmallLeather | Short leather/belt handling tick (fallback interaction). |  | |
| [SFX_LB_Generic_Use_02](../../../SourceArt/Audio/Recorded/SFX_LB_Generic_Use_02.wav) | 0.24 s | 1 | -3.0 | -25.1 | kr:handleSmallLeather2 | as above |  | |
| [SFX_LB_Generic_Use_03](../../../SourceArt/Audio/Recorded/SFX_LB_Generic_Use_03.wav) | 0.23 s | 1 | -3.0 | -26.5 | kr:beltHandle1 | as above |  | |

## Room emitters: wood creaks, distant chains (9)

![spectrograms](rec_room.png)

| File | Len | Ch | Peak | RMS | Src | What to listen for | Weak / note | Keep / redo / replace |
|---|---|---|---|---|---|---|---|---|
| [SFX_LB_Creak_Wood_01](../../../SourceArt/Audio/Recorded/SFX_LB_Creak_Wood_01.wav) | 0.79 s | 1 | -3.0 | -22.0 | 506665 | Single wood creak. 05 is cut from a door recording, 03 is a pitch -6 % tail. |  | |
| [SFX_LB_Creak_Wood_02](../../../SourceArt/Audio/Recorded/SFX_LB_Creak_Wood_02.wav) | 2.45 s | 1 | -3.0 | -22.4 | 802595 | as above |  | |
| [SFX_LB_Creak_Wood_03](../../../SourceArt/Audio/Recorded/SFX_LB_Creak_Wood_03.wav) | 0.76 s | 1 | -3.0 | -20.4 | kr:creak2 | as above | pitch copy of the tail of 02's recording | |
| [SFX_LB_Creak_Wood_04](../../../SourceArt/Audio/Recorded/SFX_LB_Creak_Wood_04.wav) | 1.95 s | 1 | -3.0 | -24.3 | 590171 | as above |  | |
| [SFX_LB_Creak_Wood_05](../../../SourceArt/Audio/Recorded/SFX_LB_Creak_Wood_05.wav) | 1.40 s | 1 | -3.0 | -25.0 | 402464 | as above |  | |
| [SFX_LB_Chain_Distant_01](../../../SourceArt/Audio/Recorded/SFX_LB_Chain_Distant_01.wav) | 1.50 s | 1 | -3.0 | -22.7 | 167912 | 01-02 original reverberant chain drags; 03-04 are darkened and given a long tail to read as far away. | 03/04 reuse the Warden chain recordings with a darkened, long-tail treatment (applies to the whole set) | |
| [SFX_LB_Chain_Distant_02](../../../SourceArt/Audio/Recorded/SFX_LB_Chain_Distant_02.wav) | 1.24 s | 1 | -3.0 | -26.5 | 167914 | as above |  | |
| [SFX_LB_Chain_Distant_03](../../../SourceArt/Audio/Recorded/SFX_LB_Chain_Distant_03.wav) | 1.50 s | 1 | -3.0 | -27.0 | 455078 | as above |  | |
| [SFX_LB_Chain_Distant_04](../../../SourceArt/Audio/Recorded/SFX_LB_Chain_Distant_04.wav) | 2.43 s | 1 | -3.0 | -18.5 | 199282 | as above |  | |

## Warden: steps, chains, robe, breath loops (13)

![spectrograms](rec_warden.png)

| File | Len | Ch | Peak | RMS | Src | What to listen for | Weak / note | Keep / redo / replace |
|---|---|---|---|---|---|---|---|---|
| [SFX_LB_Warden_Step_01](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Step_01.wav) | 0.65 s | 1 | -3.0 | -21.2 | 741627, ki:impactSoft_heavy_000 | Heavy boot + thump + 50 Hz sub, pitched down 30 %. Should feel big but not slap-like. |  | |
| [SFX_LB_Warden_Step_02](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Step_02.wav) | 0.73 s | 1 | -3.0 | -19.5 | 741627, ki:impactPunch_heavy_001 | as above |  | |
| [SFX_LB_Warden_Step_03](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Step_03.wav) | 0.76 s | 1 | -3.0 | -20.5 | 531725, 741627, ki:impactWood_heavy_003 | as above |  | |
| [SFX_LB_Warden_Step_04](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Step_04.wav) | 0.76 s | 1 | -3.0 | -13.5 | 339439, 741627, ki:impactPunch_heavy_003 | as above | source has 260 clipped samples in the slice | |
| [SFX_LB_Warden_Step_05](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Step_05.wav) | 0.77 s | 1 | -3.0 | -18.9 | 339439, 741627, ki:impactSoft_heavy_002 | as above |  | |
| [SFX_LB_Warden_Chain_01](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Chain_01.wav) | 1.41 s | 1 | -3.0 | -28.3 | 455078 | Heavy chain drag clank, pitched down 8-12 %. | chain drags can sound rhythmic (pulses about every 0.25 s in 03/04) (applies to the whole set) | |
| [SFX_LB_Warden_Chain_02](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Chain_02.wav) | 1.54 s | 1 | -3.0 | -24.6 | 455078 | as above |  | |
| [SFX_LB_Warden_Chain_03](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Chain_03.wav) | 1.41 s | 1 | -3.0 | -15.6 | 199282 | as above |  | |
| [SFX_LB_Warden_Chain_04](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Chain_04.wav) | 1.53 s | 1 | -3.0 | -15.4 | 199282 | as above |  | |
| [SFX_LB_Warden_Robe](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Robe.wav) | 10.00 s loop, seam 0.04 dB | 1 | -2.0 | -24.0 | 19291, kr:cloth1, kr:cloth2, kr:cloth3, kr:cloth4, noise bed (synth) | 10 s loop of dull cloth rubbing, no obvious repeat; check the loop wrap near 10 s. |  | |
| [SFX_LB_Warden_Breath_Slow](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Breath_Slow.wav) | 10.00 s loop, seam 0.13 dB | 1 | -2.3 | -24.0 | 574208 | Loop wrap (seam): listen across the end-to-start join. Slow = patrol, Fast = investigate, Heavy = chase. | check the loop wrap and that it reads as a creature, not a person (applies to the whole set) | |
| [SFX_LB_Warden_Breath_Fast](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Breath_Fast.wav) | 8.00 s loop, seam 0.15 dB | 1 | -3.6 | -24.0 | 689240 | as above |  | |
| [SFX_LB_Warden_Breath_Heavy](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Breath_Heavy.wav) | 10.00 s loop, seam 0.00 dB | 1 | -3.9 | -24.0 | 470900, 689240 | as above |  | |

## Warden voice tells and apparition whispers (17)

![spectrograms](rec_voice.png)

| File | Len | Ch | Peak | RMS | Src | What to listen for | Weak / note | Keep / redo / replace |
|---|---|---|---|---|---|---|---|---|
| [SFX_LB_Warden_Spotted_01](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Spotted_01.wav) | 1.34 s | 1 | -3.0 | -15.4 | 132874, 487513 | Short (under 1.5 s), sharp, readable roar bark: the tell. Should be unmistakable but not cartoonish. | source has 6 clipped samples in the slice | |
| [SFX_LB_Warden_Spotted_02](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Spotted_02.wav) | 1.45 s | 1 | -3.0 | -18.0 | 204912, 487513 | as above | source has 639 clipped samples in the slice | |
| [SFX_LB_Warden_Spotted_03](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Spotted_03.wav) | 1.43 s | 1 | -3.0 | -18.2 | 132874, 497056 | as above |  | |
| [SFX_LB_Warden_Roar_01](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Roar_01.wav) | 2.92 s | 1 | -3.0 | -16.1 | 204912, 497056 | 2.9-3 s low roar (cut at 3 s with a fade). Layered, sub, room tail. | source has 942 clipped samples in the slice | |
| [SFX_LB_Warden_Roar_02](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Roar_02.wav) | 3.00 s | 1 | -3.0 | -14.9 | 204912, 487513 | as above | source has 957 clipped samples in the slice | |
| [SFX_LB_Warden_Roar_03](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Roar_03.wav) | 2.86 s | 1 | -3.0 | -18.0 | 170454, 497056 | as above |  | |
| [SFX_LB_Warden_Windup_01](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Windup_01.wav) | 1.35 s | 1 | -3.0 | -21.2 | 444445, noise bed (synth) | Rising growl and hiss, 1.2-1.5 s: should say 'attack is coming'. |  | |
| [SFX_LB_Warden_Windup_02](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Windup_02.wav) | 1.25 s | 1 | -3.0 | -20.2 | 389653, 444445 | as above |  | |
| [SFX_LB_Warden_Windup_03](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Windup_03.wav) | 1.50 s | 1 | -3.0 | -21.2 | 389653, 763026, noise bed (synth) | as above |  | |
| [SFX_LB_Warden_Exhale_01](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Exhale_01.wav) | 1.21 s | 1 | -3.0 | -16.2 | 345730 | Soft, long exhale: relief/loss of the player. Quiet and low. |  | |
| [SFX_LB_Warden_Exhale_02](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Exhale_02.wav) | 2.04 s | 1 | -3.0 | -17.7 | 615047 | as above |  | |
| [SFX_LB_Warden_Exhale_03](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Exhale_03.wav) | 1.42 s | 1 | -3.0 | -17.6 | 345730, 615047 | as above |  | |
| [SFX_LB_Warden_Caught_01](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Caught_01.wav) | 2.65 s | 1 | -3.0 | -18.3 | 170454, 763026 | Brutal 2.3-2.8 s growl/roar. |  | |
| [SFX_LB_Warden_Caught_02](../../../SourceArt/Audio/Recorded/SFX_LB_Warden_Caught_02.wav) | 2.16 s | 1 | -3.0 | -18.2 | 170454, 497056 | as above |  | |
| [SFX_LB_Apparition_Whisper_01](../../../SourceArt/Audio/Recorded/SFX_LB_Apparition_Whisper_01.wav) | 3.84 s | 1 | -3.0 | -22.2 | 316797 | Ghostly whispers with a tail; check they are not intelligible words. |  | |
| [SFX_LB_Apparition_Whisper_02](../../../SourceArt/Audio/Recorded/SFX_LB_Apparition_Whisper_02.wav) | 3.38 s | 1 | -3.0 | -19.2 | 339827 | as above |  | |
| [SFX_LB_Apparition_Whisper_03](../../../SourceArt/Audio/Recorded/SFX_LB_Apparition_Whisper_03.wav) | 3.27 s | 1 | -3.0 | -22.6 | 316797 | as above |  | |

## Creatures: bats, owls, far howls, rats (18; P16-6, D-112)

![spectrograms](rec_creatures.png)

| File | Len | Ch | Peak | RMS | Src | What to listen for | Weak / note | Keep / redo / replace |
|---|---|---|---|---|---|---|---|---|
| [SFX_LB_Bat_01](../../../SourceArt/Audio/Recorded/SFX_LB_Bat_01.wav) | 0.58 s | 1 | -3.0 | -24.4 | 455593 | 01-03 squeaks (chirp trains from one close-up recording, 03 pitched down 15 %), 04-05 startled flurries (wing flutter plus chirps or colony swarm, at most 2.4 s), 06 a wing-flutter burst. Very high and quick: they should read as small and far up in the roof beams, never as a shriek. | the three squeaks are one recording (a bat in a duct) so they share a voice; flurry sources are caves and a vintage tape transfer, not a belfry; 05 has the tape hiss spectrally gated (can sound slightly watery) (applies to the whole set) | |
| [SFX_LB_Bat_02](../../../SourceArt/Audio/Recorded/SFX_LB_Bat_02.wav) | 0.70 s | 1 | -3.0 | -25.2 | 455593 | as above |  | |
| [SFX_LB_Bat_03](../../../SourceArt/Audio/Recorded/SFX_LB_Bat_03.wav) | 0.65 s | 1 | -3.0 | -26.5 | 455593 | as above |  | |
| [SFX_LB_Bat_04](../../../SourceArt/Audio/Recorded/SFX_LB_Bat_04.wav) | 1.43 s | 1 | -3.0 | -31.9 | 455593, 546823 | as above |  | |
| [SFX_LB_Bat_05](../../../SourceArt/Audio/Recorded/SFX_LB_Bat_05.wav) | 1.80 s | 1 | -3.0 | -26.0 | 437935, 806573 | as above |  | |
| [SFX_LB_Bat_06](../../../SourceArt/Audio/Recorded/SFX_LB_Bat_06.wav) | 1.33 s | 1 | -3.0 | -33.0 | 546823 | as above |  | |
| [SFX_LB_Owl_01](../../../SourceArt/Audio/Recorded/SFX_LB_Owl_01.wav) | 1.42 s | 1 | -3.0 | -15.4 | 864872 | Distant hoots (low-passed at 5 kHz, short tail). 01 single hoot, 02 a short-then-long phrase, 03-04 the second owl. Check the hoot is soft and far, not a bird in the room. | 03/04 come from a field recording with its noise spectrally gated (can sound slightly watery); 867131 was rejected (ke-wick sweeps, not hoots) (applies to the whole set) | |
| [SFX_LB_Owl_02](../../../SourceArt/Audio/Recorded/SFX_LB_Owl_02.wav) | 2.40 s | 1 | -3.0 | -16.5 | 864872 | as above |  | |
| [SFX_LB_Owl_03](../../../SourceArt/Audio/Recorded/SFX_LB_Owl_03.wav) | 1.72 s | 1 | -3.0 | -15.1 | 688869 | as above |  | |
| [SFX_LB_Owl_04](../../../SourceArt/Audio/Recorded/SFX_LB_Owl_04.wav) | 1.80 s | 1 | -3.0 | -14.4 | 688869 | as above |  | |
| [SFX_LB_Howl_01](../../../SourceArt/Audio/Recorded/SFX_LB_Howl_01.wav) | 10.52 s | 1 | -3.0 | -16.8 | 500646 | Far-off howls (low-passed at 3 kHz, 3 s synthetic tail, slow fades). 01 and 03 solitary wolf, 02 coyote. They must sound like something beyond the walls, not a dog next door. | howls are 7-10 s long; 02 is a coyote, not a wolf; the tail is synthetic (applies to the whole set) | |
| [SFX_LB_Howl_02](../../../SourceArt/Audio/Recorded/SFX_LB_Howl_02.wav) | 7.47 s | 1 | -3.0 | -19.3 | 640060 | as above |  | |
| [SFX_LB_Howl_03](../../../SourceArt/Audio/Recorded/SFX_LB_Howl_03.wav) | 9.78 s | 1 | -3.0 | -15.1 | 500646 | as above |  | |
| [SFX_LB_Rat_01](../../../SourceArt/Audio/Recorded/SFX_LB_Rat_01.wav) | 0.27 s | 1 | -3.0 | -23.6 | 143125 | 01-03 squeaks (one, two, three baby), 04 a scurry of claw taps, 05 scratching. Small and dry; listen for hiss in 03 and 05. | no clean recording of a rat running on stone exists in the CC0 set: 04 is a creature scurry (not a rat), 05 is a rat gnawing wood (applies to the whole set) | |
| [SFX_LB_Rat_02](../../../SourceArt/Audio/Recorded/SFX_LB_Rat_02.wav) | 0.76 s | 1 | -3.0 | -19.1 | 143125 | as above |  | |
| [SFX_LB_Rat_03](../../../SourceArt/Audio/Recorded/SFX_LB_Rat_03.wav) | 0.95 s | 1 | -3.0 | -19.1 | 841571 | as above |  | |
| [SFX_LB_Rat_04](../../../SourceArt/Audio/Recorded/SFX_LB_Rat_04.wav) | 1.28 s | 1 | -3.0 | -32.0 | 872940 | as above |  | |
| [SFX_LB_Rat_05](../../../SourceArt/Audio/Recorded/SFX_LB_Rat_05.wav) | 0.99 s | 1 | -3.0 | -31.1 | 333094 | as above |  | |
