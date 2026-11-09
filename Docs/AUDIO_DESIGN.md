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

## As planned for Phase 16 (D-108…D-111, `Docs/plans/P16_AUDIO.md`)
- **Interactions:** cues are mapped by actor class in `DA_Audio` and played by the C++ `ULBAudioSubsystem`, not stored as sound slots on each Blueprint, because several interaction Blueprints are on the never-save list (R-76).
- **Mix:** user volumes go through SoundClasses (`SCL_LB_SFX`, `_Ambience`, `_Music`, `_Voice`, `_UI` under `_Master`) and one SoundMix. Per-group submixes are deferred until an effect needs them.
- **Weather bed:** pre-rendered loops crossfaded by the storm's sky exposure and an `ALBAudioZone`'s roof-rain value. Reverb and indoor muffling come from engine AudioVolumes, not Audio Gameplay Volumes.
- **Music:** pre-rendered loops (drones, tension, chase) faded by C++ from the Warden's state; no Quartz or Audio Modulation.
- **Bell:** five pre-rendered stages of one cracked bell, at story beats plus occasional distant tolls.
- **Breathing:** reacts to the Warden, sprinting, darkness and the candle going out.
- **Spatialization:** built-in panning; HRTF is tried in Phase 20.

