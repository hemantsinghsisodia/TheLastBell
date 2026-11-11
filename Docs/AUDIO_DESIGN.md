# THE LAST BELL — Audio Design

Audio is a first-class system. Silence is designed.

## Layers
| Layer | Content | Tech |
|---|---|---|
| Weather bed | Rain (exterior and interior-muffled), wind gusts, thunder linked to lightning | MetaSound with a per-area interior/exterior mix, through Audio Gameplay Volumes |
| Room tone | Drips, creaks, resonance per area | Ambient emitters plus reverb via submix effects or Audio Gameplay Volumes |
| Player | Footsteps per physical surface and gait, cloth, breathing under stress | `ULBFootstepComponent` → `DT_Footsteps` → MetaSound with random variants |
| Interactions | Doors, levers, chains, mechanisms, notes | Per-interactable sound slots on the Blueprint |
| Warden | Breath, chain rattle, heavy steps, robe drag, vocal tells | Spatialized, with attenuation tuned for readability (tells audible before danger) |
| Bell | Distant bell motif, distorted variants | One MetaSound with pitch and distortion parameters per story beat |
| Music | Sparse drones, a tension layer, chase music | A tension parameter driven by Warden state through Audio Modulation / Quartz, not running constantly |

## Rules
- No constant horror music. Default to weather and room tone, with drones only at story beats or under threat.
- Every Warden action the player has to react to gets an audio tell.
- At least 3–5 variants per repeated one-shot, plus pitch and volume randomization, so loops don't sound obvious.
- Mixing uses submixes: SFX, Ambience, Music, Voice/Warden and UI, each with a user volume setting.
- Spatialization: HRTF tested on headphones (Phase 16).

## Sourcing
CC0 or properly licensed libraries only, recorded in `ASSET_REGISTRY.md`. Unlicensed audio is never used.

## As built in Phase 16 (D-108…D-113, `Docs/plans/P16_AUDIO.md`, `TECHNICAL_DESIGN.md` section 16)
This differs from the layer table above as follows.
- **Interactions:** cues are mapped by actor class in `DA_Audio` (9 rows, 3 silent classes) and played by the C++ `ULBAudioSubsystem`, not stored as sound slots on each Blueprint, because several interaction Blueprints are on the never-save list (R-76). Notes rustle on pick-up and on every put-down. The small-bell sounds play only for the bell puzzle.
- **Mix:** user volumes go through SoundClasses (`SCL_LB_SFX`, `_Ambience`, `_Music`, `_Voice`, `_UI` under `_Master`) and one SoundMix (`SMX_LB_User`). Per-group submixes are deferred until an effect needs them. Owner mix values: master 0.7, rain 0.22 outdoors and 0.03 under a roof, wind 0.08, steps 0.6 (wood 2.0), Warden roars 2.0, great bell stages at full volume (the finale at 2.0).
- **Weather bed:** pre-rendered loops crossfaded by the storm's sky exposure and an `ALBAudioZone`'s roof-rain value. Reverb and indoor muffling come from engine AudioVolumes, not Audio Gameplay Volumes. Thunder follows each flash after a delay that shrinks with brightness; the cracks (near thunder, tower strikes) are recorded Freesound CC0 sounds over a generated rumble.
- **Music:** pre-rendered loops (drones, tension, chase) faded by C++ from the Warden's state; no Quartz or Audio Modulation.
- **Bell:** five pre-rendered stages of one cracked bell, at story beats plus occasional distant tolls. The finale's strikes (stage 5, 2.0 s apart) sound from the tag at the start of the finale cinematic; the ending no longer pauses the game (D-117).
- **Creatures (D-112):** occasional, mostly distant bats, owls, far howls and rats from 13 ambient emitters. Silence stays the default.
- **Breathing:** reacts to the Warden, sprinting, darkness and the candle going out.
- **Spatialization:** built-in panning; HRTF is tried in Phase 20.
- **Not yet measured:** the audio cost (voices, audio thread, game thread) is read in the Phase 20 performance pass (D-113, R-75).

## As built in Phase 17 (D-117, D-120, D-124; `TECHNICAL_DESIGN.md` section 17)
- **The Arrival beat (intro).** The first toll moved from a timer after the game starts to the intro's `State.Event.Arrival` tag: stage 1 × 3, the first strike at once (17.4 s into the intro, right after the lightning strike on the tower), 4.5 s apart, and **no drone** (owner: no music from the Arrival beat; music begins at Ritual 1, in line with "drones only at story beats"). The old new-game toll is **off** (`DA_Audio.bNewGameToll` false; the code and its test stay). `State.Event.Arrival` is added by the intro or by its skip, so Continue and checkpoint loads never repeat it.
- **The cinematic music** is three owner-picked Freesound CC0 tracks, 2D, not looping, peak −3 dBFS, in the sound class `SCL_LB_CineMusic` (a child of `SCL_LB_Music`, so the user's music volume applies): `MUS_LB_Cine_IntroText` (a sad piano, 0–27.5 s of the intro, fading in over 0.5 s and out over the last 2.5 s), `MUS_LB_Cine_Finale` (dark strings and drone, 3.6–54.5 s of the finale) and `MUS_LB_Cine_Credits` (a violin and cello loop, 53.5–94.5 s under the credits). They are the exception to "no constant music", limited to the two cinematics.
- **`SMX_LB_CineFade`** (pushed by the finale's `mix:on` at 37.5 s): **Ambience, SFX, Voice and Music at 0**, fade in 4.0 s, fade out 1.0 s, so the world sound and the TowerTop drone fall away under the end cards. Every adjuster has `bApplyToChildren` false, so the cinematic music in `SCL_LB_CineMusic` is **excluded** and keeps playing. The mix is not popped before the travel to the menu (no world sound returns over the black screen); world teardown pops it.
- **The finale beat** sounds from the `State.Event.Finale` tag (stage 5 × 5, 2.0 s apart, first strike at once) with the storm's two Finale strikes at 0.3 s and 1.1 s. The sequence adds one more stage-5 strike at 33.5 s, heard from the tower while the villager walks in. Under the Warden's climb the figure carries its own stride, chain and heavy-breath sounds (3D). The **mask sound** at the moment of black is 2D: `SFX_LB_Step_Metal_02` at pitch 0.55 with `SFX_LB_Warden_Chain_02` at 0.7, then `SFX_LB_Warden_Breath_Slow` as the player's own breath until 39.5 s. The first plan's sound-only climb (3D stride sounds climbing the tower over about a minute) was dropped when the Warden was brought into sight within about 3.5 s of the ring (3.2b).
- **The bell swings on every great-bell strike** (`ULBAudioSubsystem::OnGreatBellStrike`): at the tower-top beat, the ambient tolls, `PlayBell` and the finale, not only in the finale. The owner kept this in the finale review (D-124).
- **Not measured:** the cinematic audio (three streamed music cues and the mix) is part of the Phase 20 audio performance reading (R-75).
