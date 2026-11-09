# P16-2: audio assets (headless)

Script `Tools/audio/p16_2_assets.py`, run with Unreal closed (`UnrealEditor-Cmd -run=pythonscript`, route and property names in `Tools/mcp/MCP_NOTES.md` "Audio assets (headless)"). It is idempotent: the second `apply` run imported, set and saved nothing. The report of the fresh-process `verify` run is `p16_2_report.json` (1390 checks, 0 failures); every property the first run set is in `p16_2_setlog.txt` (527 lines).

## Part A: small-bell sounds only for the bell puzzle (code, commit ceb5fae)
- `ULBAudioSubsystem::IsBellStep(Step)` is true when the tag is a key of `DA_Audio.SmallBellPitch`; `IsBellPuzzle(Actor)` is true when a sequence puzzle component on the actor has such a step.
- Step accepted: the strike plays only for a bell step. The candle puzzle is silent per step.
- Failed: a bell step, or a puzzle that is a bell puzzle, plays `SmallBellFail`. Any other puzzle plays one `Player.CandleOut` variant (cue `Candle.Out`, no repeat with the player's own candle-out) at the puzzle actor.
- Solved: the chord plays only for a bell puzzle; the candle puzzle is silent.
- New functional test `LastBell.Functional.Audio.CandlePuzzleNotBells`: two accepted candle steps give no bell request and no candle-out; a wrong candle gives exactly one `Candle.Out` request at the puzzle's location and no bell request; the right order solves the puzzle with no bell and no candle-out request. `SequenceSmallBellPitch` still passes.
- Also fixed (build): `FindTag` in the anonymous namespace of `LBAudioSettings.cpp` collided with the one in `LBStormSettings.cpp` once the two were merged into one unity file; renamed `FindAudioTag`.

## Part B: counts
| Folder | Assets |
|---|---|
| `Audio/Weather` | 4 |
| `Audio/Thunder` | 15 |
| `Audio/Bell` | 8 |
| `Audio/Music` | 8 |
| `Audio/Room` | 25 |
| `Audio/Player` | 63 |
| `Audio/Interact` | 22 |
| `Audio/Warden` | 30 |
| **Sounds** | **175** (51 generated + 124 recorded) |
| `Audio/Mix` | 25: 6 `SCL_LB_*`, `SMX_LB_User`, 8 `ATT_LB_*`, 4 `CON_LB_*`, 6 `RVB_LB_*` |
| `Physics` | 6 `PM_LB_*` (SurfaceType1..6) |
| `Data/DA_Audio` | new, class `LBAudioSettings` |
| `Data/DT_Footsteps` | rows rebuilt: Default, Stone, Wood, Earth, Grass, Water, Metal, 6 variants each |

208 packages were saved by the first run (175 + 25 + 6 + DA_Audio + DT_Footsteps).

## What was set
- **SoundWave** (all 175): `looping` on 19 (4 weather beds, 6 room tones, 3 drones, tension, chase, 3 Warden breaths, the robe); `sound_class_object`; `attenuation_settings` on 130 (none for the weather beds, room tones, music, breath, candle, key and paper); `concurrency_set` on 77 (Steps 36 + 5 Warden steps, Thunder 15, Drips 10, Tells 11); `volume` = 10^(`mix_gain_db`/20): bell stages 1 to 4 (0.1259, 0.1995, 0.3162, 0.5012) and the four far thunders (0.3981), 1.0 for the rest.
- **Mix assets:** the SoundClass tree (Master with five children, both links), the attenuation, concurrency and reverb values of plan §6.2 to §6.4 (near distance = the sphere's inner radius, far = the falloff distance; reverb late delay 0.04 s, reflections delay 0.01 s).
- **DA_Audio:** all sound groups, 9 `InteractionCues` rows (F0 accepted table), 3 `SilentClasses`, `SmallBellPitch` (0.7692, 0.8696, 1.0, 1.1765), the three `SmallBell*` sounds, `BellLocation` (12420.1, 2000, 2750), the six `BellBeats` of plan 5.3 written as rows (`FillPlanDefaults` is not callable from Python), `UserMix`, `UserClasses` (Master, SFX, Ambience, Music, Voice, UI), `DebugForceMusicState` -1; every other field is the C++ default (checked for 23 of them). Every referenced sound and Blueprint class path was checked to exist.

## Decisions and open points
- Attenuation rows with a blank "Shape" column keep the engine default distance model (linear); only `ATT_LB_Warden` uses Natural Sound.
- "Non-spatialised radius" is `non_spatialized_radius_start` (3000 thunder, 2000 bell); the end radius stays 0.
- Cue sheet 2D cues (`Key_Pickup`, `Paper`, `Candle_*`, `Breath_*`) have no attenuation, as §3 says. The F0 interaction rows play `Key_Pickup`, `Paper` and `Candle_Light` positionally at the actor, so they will not fall off with distance; listen for it in P16-4 and give them `ATT_LB_Small` if they carry too far.
- `SFX_LB_Warden_Exhale_*` uses `ATT_LB_WardenTell` (tell family) but not the `CON_LB_Tells` limit, as the brief lists only Spotted, Roar, Windup and Caught.
- The first `apply` run printed one failed check, a false positive in the script's own class-path check (it took the sound `MUS_LB_Drone_C` for a Blueprint `_C` class); fixed, then `apply` again (nothing to change) and `verify` in a fresh process were clean.

## Suite
`Toolsuild_and_test.ps1` (a real rebuild: 14 files compiled, linked, `Result: Succeeded`; the stale `lb_build.log` was deleted first): **170 tests passed, 1 failed, 0 invalid tags.** The one failure is `LastBell.Functional.Audio.Monastery.AudioSetup`, and only on the two level-side checks that P16-3 fixes:
- `At least 6 ALBAudioZone actors (0)`
- `At least 6 AAudioVolume actors (0)`

Everything else in that test now passes: `DA_Audio` is linked and loads, the director is active (`Audio: active (111 sounds loaded, 0 zones, 29 bound actors)`), every sound reference is set and loads, `UserMix` and the six `UserClasses` load, the six beats and `BellLocation` are set, `DebugForceMusicState` is -1, all 12 interactable classes in L_Monastery are mapped or silent, and `DT_Footsteps` has a row per surface with at least 4 variants.
The new `CandlePuzzleNotBells` passes.
