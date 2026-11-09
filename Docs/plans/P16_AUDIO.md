# Phase 16: Audio (plan for owner approval)

Branch `claude/phase-16-audio`, created from `main` at 5927cd7. **The lead plans; every implementation agent is spawned with `model: "sonnet", effort: "high"`** (D-048).

Every task follows the standing rules:
- Commit on this branch only, staging by path; never switch, merge or push.
- Explicit saves only: one package per call, then `is_dirty`.
- Never save the never-save list (`p15_level.NEVER_SAVE`, including `M_LB_Surface`).
- Never `set_parent` or `read_graph_dsl`.
- Never start PIE or run captures without the owner.
- Before a long owner session, state its length.

## 0. Owner choices (2026-11-09)
| Topic | Choice |
|---|---|
| Sourcing | **Generated + Kenney + Freesound.** Rain, wind, thunder, the bells, drones, music and room tones are rendered offline by our own scripts. Footsteps and impacts come from Kenney.nl CC0 packs, downloaded by an agent. The Warden's voice and breath, chains, creaks, doors, mechanisms and water steps are Freesound **CC0** recordings: the lead's agent prepares an exact list and the owner downloads it. |
| Music | **Drones + tension + chase.** Low drones only at story beats. A tension layer rises when the Warden is near or searching; a pulsing chase layer plays only during a chase. Silence otherwise. |
| Bell | **Deep, cracked, distant.** A huge old bell with a beating, cracked tone, heard far off. It comes closer and more distorted with each ritual, and is clean and overwhelming only at the finale. |
| Additions at approval | **Occasional distant tolls** between the story beats. **Breathing also reacts to darkness and to the candle going out.** |
| 3D audio | **Built-in.** Unreal's standard panning and distance attenuation, reverb per area, and outdoor sound muffled indoors. HRTF is tried in Phase 20. |

## 1. Outcome and acceptance
1. Rain and wind are heard everywhere outdoors. Indoors the rain becomes a muffled roof sound where there is a roof above, and almost nothing in the crypt. Wind follows the storm's gusts.
2. Every lightning flash is followed by thunder after a delay that shrinks as the flash gets brighter. The two scripted tower strikes crack at once, from the tower.
3. The great bell tolls at the story beats (section 5.3). Each stage is closer and more cracked than the last. Between the beats, an occasional distant toll sounds every 4–7 minutes, never during a chase.
4. Music is silent by default:
   - story-beat drones;
   - tension that rises with the Warden's threat;
   - a chase layer only while it chases.
5. Every Warden action the player has to react to has an audio tell:
   - spotted, about 0.6 s before a chase;
   - chase start, attack wind-up and caught;
   - its breath, steps, chains and robe are audible before it is seen at close range.
6. **Player sounds:**
   - footsteps per surface (stone, wood, earth, grass, water, metal) with no repeated variant twice in a row;
   - breathing that grows with stress from the Warden, chases, sprinting, darkness (stronger with the candle out) and the candle going out (a sharp gasp);
   - the candle.
7. **Interaction sounds:** every interactable class in `L_Monastery` either has a sound or is listed as silent on purpose (`Monastery.AudioSetup` checks this). The four small bells are tuned by size. A failed bell sequence sounds wrong.
8. **Areas:** each area has its own reverb and room tone: chapel, crypt, cloister walk, shortcut passage, tower stair, belfry, plus outdoors with no reverb.
9. **Volumes:** five user volume groups (effects, ambience, music, Warden/voice, interface) under a master, with a C++ API ready for the Phase 18 settings menu.
10. **Owner sign-offs:** the WAV audition (A4), the listening session on headphones (P16-4) and the run-through (P16-6).
11. **Tests and performance:**
    - the suite passes, including the new `LastBell.Audio.*` tests;
    - no `Error:` lines;
    - performance (P16-6): at most 48 active voices and an audio-thread CPU of at most 2.0 ms at the six standard spots and in a chase, and the game thread rises by at most 0.3 ms with audio on against `lb.Audio.Enabled 0` (judged with the D-107 caveat on `stat unit` noise).

## 2. Architecture (C++, gameplay-programmer, Unreal closed)
Folder `Source/LastBell/Audio/`, prefix `LB`. Composition and subsystems; no hard asset references (soft pointers in `ULBAudioSettings`). Pure maths is in `LBAudioLogic` and unit tested.

### 2.1 What it listens to (all exist today)
| Source | Event | Used for |
|---|---|---|
| `ULBStormSubsystem` | `OnLightningFlash(Brightness, Reason)`, `OnLightningStrike(Info)`, `GetPlayerExposure()`, `GetWindStrength()`, `GetStormIntensity()`, `IsActive()` | thunder, rain and wind mix, activation |
| `ULBWorldStateSubsystem` | `OnStateChanged(Tag, bAdded)`; `OnStateReplaced` (a checkpoint load) | bell and drone beats, tag-added only |
| `ULBWardenBrainComponent` | `OnStateChanged(Old, New)`, `OnPlayerSpotted`, `OnPlayerLost`, `OnAttackWindup(Seconds)`, `OnPlayerCaught` | Warden tells, music, player stress |
| `ULBInteractableComponent` | `OnInteracted(Instigator)`, `OnInteractDenied(Instigator)` | interaction cues |
| `ULBDialComponent` | `OnDialChanged(NewIndex)` | dial and lever notches |
| `ULBSequencePuzzleComponent` | `OnStepAccepted(Index, Step)`, `OnPuzzleFailed(WrongStep)`, `OnPuzzleSolved` | the small bells and the puzzle results |
| `ULBCandleComponent` | `OnCandleStateChanged(bLit)`, `OnRelightStarted` | candle sounds |
| `ULBFootstepComponent` | its own `DT_Footsteps` lookup (extended, section 2.6) | footsteps |
| `ALBCharacter` movement | sprinting and velocity | stress |

### 2.2 `ULBAudioSettings` (`UPrimaryDataAsset`, asset `/Game/LastBell/Data/DA_Audio`)
- **Link:** linked from `ULBGameSettings::AudioSettings` (a new `TSoftObjectPtr<ULBAudioSettings>`, set in `Config/DefaultGame.ini` under `[/Script/LastBell.LBGameSettings]`).
- **Defaults:** the defaults below are the C++ constructor values. Every float has `ClampMin`/`ClampMax` and units in its tooltip. `DebugForceMusicState` is −1 and is **never saved other than −1**.

| Group | Fields (default) |
|---|---|
| Sounds | soft `USoundBase` refs for every cue in section 3 that the subsystem plays, grouped in structs: `FLBAudioWeather` (RainOut, RainIn, Wind, WindHowl), `FLBAudioThunder` (Near[4], Mid[4], Far[4], StrikeCrack[3]), `FLBAudioBell` (Stage[5]), `FLBAudioMusic` (Drones[3], Tension, Chase, StingSpotted, StingCaught, StingApparition), `FLBAudioPlayer` (BreathCalm[4], BreathHeavy[4], BreathPanic[4], BreathGasp[3], CandleLight[3], CandleOut[3], CandleRelight), `FLBAudioWarden` (section 2.5, including `ApparitionWhisper[3]`). Footsteps stay in `DT_Footsteps`; emitters hold their own sounds |
| Interaction map | `TArray<FLBInteractionCue>`. `FLBInteractionCue`: `TSoftClassPtr<AActor> ActorClass`, `bool bIncludeSubclasses` (true), `TArray<TSoftObjectPtr<USoundBase>> Interact`, `TArray<TSoftObjectPtr<USoundBase>> Denied`, `TArray<TSoftObjectPtr<USoundBase>> DialNotch`, `float Volume` (1), `FVector2D Pitch` (0.97, 1.03), `FName Note`. The most specific class match wins. `TArray<TSoftClassPtr<AActor>> SilentClasses` lists the classes that are silent on purpose. |
| Small bells | `TMap<FGameplayTag, float> SmallBellPitch` (step tag to pitch multiplier, filled from F0), `TSoftObjectPtr<USoundBase> SmallBellStrike`, `SmallBellFail`, `SmallBellSolved` |
| Mix | `RainOutGain` 0.8, `RainInGain` 0.55, `RainExposurePower` 0.7, `WindOutGain` 0.6, `WindMin` 0.3, `WindPitch` (0.92, 1.08), `MixFadeSeconds` 0.75 |
| Thunder | `ThunderDelay` (0.6, 4.5) s from brightness 1 to 0, `ThunderJitter` 0.4 s, `ThunderNearAt` 0.75, `ThunderFarBelow` 0.4, `ThunderDistance` 6000 cm (the emitter sits along the flash direction), `StrikeCrackDelay` 0.12 s |
| Bell | `TArray<FLBBellBeat> BellBeats` (`FGameplayTag Trigger`, `int32 Stage` 1–5, `int32 Strikes`, `float FirstDelay`, `float Spacing`; section 5.3), `bool bNewGameToll` (true), `float NewGameTollDelay` 6 s, `FVector BellLocation` (the tower bell, from F0), `float BellNearDistance` 2500 cm. **Ambient tolls:** `bAmbientTolls` (true), `AmbientTollInterval` (240, 420) s, `AmbientTollStrikes` (1, 2), `AmbientTollVolume` 0.5, `AmbientTollGapAfterBeat` 90 s, `AmbientTollMaxTension` 0.5 |
| Music | `DroneSeconds` 45, `DroneFade` (6, 8) s in/out, `TensionNearDistance` 2500 cm, `TensionLevels` (Patrol 0.25, Suspicious 0.5, Investigate 0.6, Search 0.8, Chase 0.4, Return 0.15), `ChaseLevel` 1.0, `ChaseFade` (0.8, 4.0) s, `TensionFade` (3, 10) s, `MusicMinStage` 3 (tension only from Warden stage 3) |
| Stress | `StressChase` 1.0, `StressNearSearch` 0.6, `StressSprintBonus` 0.3 for 3 s, `StressDecay` 0.25 /s, `DarknessLit` 0.15, `DarknessUnlit` 0.55, `CandleOutStress` 0.35, `BreathInterval` (2.4, 4.0) s, `BreathThresholds` (calm ≥ 0.3, heavy ≥ 0.55, panic ≥ 0.85) |
| Debug | `DebugForceMusicState` −1 |

### 2.3 `ULBAudioSubsystem` (`UTickableWorldSubsystem`, Game and PIE only)
- **Activation (mirrors `ULBStormFXSubsystem`, D-105):**
  - The subsystem is lazy: on the first tick where `ULBStormSubsystem::IsActive()` is true, it loads `DA_Audio` (or the test override) and binds the delegates in 2.1. `L_Monastery` is the only map with a storm, so the main menu and the test maps stay silent unless a test overrides the settings.
  - **`lb.Audio.Enabled 0|1`** (non-shipping CVar, default 1) deactivates the subsystem: it fades everything out over 0.5 s and unbinds.
  - The file that defines this CVar must **never be Live Coded** (MCP_NOTES "PIE Simulate captures and Live Coding" item 2).
- **Interactables:** at activation, and on each `OnActorSpawned`, the subsystem finds every `ULBInteractableComponent`, `ULBDialComponent` and `ULBSequencePuzzleComponent` in the world and binds them, keeping weak pointers. Cues play at the owning actor's location, with that sound's attenuation.
- **Weather bed:** four 2D looping `UAudioComponent`s are created at activation: RainOut, RainIn, Wind and WindHowl. Every tick:
  - `E` = `GetPlayerExposure()`, `W` = `GetWindStrength()`, `Z` = the current `ALBAudioZone` (section 2.4; outdoors by default);
  - RainOut = `RainOutGain` × E^`RainExposurePower`;
  - RainIn = `RainInGain` × (1 − E) × Z.`RoofRain`;
  - Wind = `WindOutGain` × lerp(`WindMin`, 1, W) × max(E, Z.`InteriorWind`), with pitch lerp(`WindPitch`, W);
  - WindHowl = Z.`Howl` × W;
  - each value is eased toward its target over `MixFadeSeconds`; a component is started on first use and stopped at 0.
- **Room tone:** a fifth 2D loop, crossfaded over 2 s when Z changes (Z.`RoomTone`, Z.`RoomToneVolume`).
- **Thunder (on `OnLightningFlash`):** `LBAudioLogic::PlanThunder(Brightness, Reason, Rand)` returns the variant set (Near if B ≥ `ThunderNearAt`, Far if B < `ThunderFarBelow`, else Mid), the delay `lerp(ThunderDelay.Y, ThunderDelay.X, B)` ± `ThunderJitter`, and a volume of 0.55 + 0.45 B.
  - The sound plays at listener + horizontal flash direction × `ThunderDistance`, with `ATT_LB_Thunder`, so it comes from the flash side.
  - For `OnLightningStrike` with `bHasTarget`, a StrikeCrack also plays at `TargetLocation` after `StrikeCrackDelay`; its normal thunder is Near.
  - The variant picker never repeats the last variant of a set.
- **Bell:** on a tag *added* that matches a `BellBeat`, the subsystem schedules that stage's sound `Strikes` times, `FirstDelay` then `Spacing` apart, at `BellLocation` with `ATT_LB_Bell`.
  - **Not on load:** `OnStateReplaced`, the checkpoint load, plays nothing.
  - **New game toll:** if `bNewGameToll` is set and no beat tag is present at activation, stage 1 plays 3 times after `NewGameTollDelay`.
  - **Ambient tolls:** between beats, the next toll is scheduled rand(`AmbientTollInterval`) s after the last toll of any kind.
    - It plays the current stage (the highest beat reached: none 1, Ritual 1 gives 2, Ritual 2 gives 3, Ritual 3 or TowerTop gives 4), rand(`AmbientTollStrikes`) strikes, at `AmbientTollVolume`.
    - It is skipped and rescheduled (rand 30–60 s) during a chase, while tension is above `AmbientTollMaxTension`, or within `AmbientTollGapAfterBeat` of a beat toll.
    - None after `State.Event.Finale`.
  - **Public API:** `PlayBell(int32 Stage, int32 Strikes)` for Phase 17.
- **Music:** three 2D loops (Drone, Tension, Chase) and one-shot stings.
  - **Drone:** a beat tag (5.3) starts its drone (fade in 6 s), holds it `DroneSeconds`, then fades it out over 8 s.
  - **Tension:** the target comes from the Warden state (`TensionLevels`), if the Warden stage is at least `MusicMinStage` and its distance to the player is at most `TensionNearDistance`; it is 0 otherwise. In Chase the target is `TensionLevels.Chase`.
  - **Chase:** the target is `ChaseLevel` only in Chase.
  - **Fades:** asymmetric (in, out) per layer.
  - **Stings:** `StingSpotted` on `OnPlayerSpotted`, `StingCaught` on `OnPlayerCaught`, and `StingApparition` when an `ALBWardenApparition` appears (an event added in 2.5).
  - **Debug:** `DebugForceMusicState` ≥ 0 forces a Warden state for tuning.
- **Player stress:** S rises to `StressChase` in a chase, and to `StressNearSearch` while the Warden is within 1500 cm and Investigating, Searching or Suspicious. A sprint adds `StressSprintBonus` for 3 s. S decays at `StressDecay` per second.
  - **Darkness:** the target S is at least Z.`Darkness` × (`DarknessLit` with the candle lit, `DarknessUnlit` with it out), using the current zone's `Darkness` (section 2.4).
  - **Candle out:** `OnCandleStateChanged(false)` adds `CandleOutStress` at once, decaying at `StressDecay`, and plays a `BreathGasp` one-shot straight away.
  - At S ≥ 0.3, a breath one-shot (Calm, Heavy or Panic by `BreathThresholds`) plays every rand(`BreathInterval`) s, 2D, in `SCL_LB_SFX`.
- **Candle:** `OnCandleStateChanged(true)` plays CandleLight, `false` plays CandleOut, and `OnRelightStarted` plays CandleRelight, attached to the player.
- **User volumes:** `ApplyUserVolumes()` reads `ULBUserSettings` (new floats `MasterVolume`, `SFXVolume`, `AmbienceVolume`, `MusicVolume`, `VoiceVolume`, `UIVolume`, default 1.0, saved per user) and pushes `SMX_LB_User` with a class override per `SCL_LB_*`. It runs at activation and from `lb.Audio.Volume <Class> <0..1>`.
- **Test sink:** in non-shipping builds, every play request (cue id, time, location) is appended to an inspectable log. The suite runs with `-nosound`, so tests check requests, not audio, as `LBStormFXTestSink` does.
- **Console** (non-shipping, `Systems/LBConsoleCommands.cpp`):
  - `lb.Audio.Enabled`;
  - `lb.Audio.Thunder 0|1|2` (far, mid, near);
  - `lb.Audio.Bell <stage> [strikes]`;
  - `lb.Audio.Music <state|-1>`;
  - `lb.Audio.Volume <Class> <v>`;
  - `lb.Audio.Debug 0|1`, an on-screen readout: E, W, the zone, each layer's level, S, the Warden state and distance, and the voice count.

### 2.4 `ALBAudioZone` (C++ actor, a box like `ALBStormZone`; placed in P16-3)
- **Fields:**
  - `Priority` (int);
  - `RoofRain` (0–1);
  - `InteriorWind` (0–1);
  - `Howl` (0–1);
  - `Darkness` (0–1), how frightening the place is to stand in without light (F0 proposes per area: crypt 1.0, passage and tower stair 0.6, chapel and belfry 0.3, cloister 0.2, outdoors 0.1 by default);
  - `TSoftObjectPtr<USoundBase> RoomTone`, `RoomToneVolume`;
  - `FName ZoneName`.
- **Which zone applies:** the subsystem checks the player position against the zones 4 times a second; the highest priority wins, and outdoors is the default.
- **Reverb is not in this actor.** It comes from engine `AAudioVolume` actors, each with an `RVB_` effect and interior settings, placed in P16-3 with the same bounds.

### 2.5 Warden and apparitions
- **`ULBWardenAudioComponent`,** created in `ALBWarden`'s C++ constructor, so `BP_Warden` inherits it without being saved. It is active only while the Warden is not dormant (visible and in stage 3 or higher):
  - **Breath:** a 3D loop that crossfades between three loops (Slow for Patrol and Return; Fast for Investigate, Suspicious and Search; Heavy for Chase and Attack), `ATT_LB_Warden`.
  - **Steps:** by distance, with a 150 cm stride. Each step plays a heavy step variant, plus a chain clink when the speed is over 150 cm/s.
  - **Robe drag:** a loop whose gain is the speed divided by the chase speed.
  - **Tells:**
    - `OnPlayerSpotted`: a Spotted vocal;
    - entering Chase: a Roar;
    - `OnAttackWindup`: a Windup vocal;
    - `OnPlayerLost`: an Exhale;
    - `OnPlayerCaught`: a Caught vocal.

    Each comes from a set of variants with no repeats.
  - **Sounds:** read from `DA_Audio.Warden` (`FLBAudioWarden`: BreathSlow, BreathFast, BreathHeavy, Steps[5], Chains[4], RobeLoop, Spotted[3], Roar[3], Windup[3], Exhale[3], Caught[2]).
- **`ALBWardenApparition`** (C++) gets a broadcast `OnAppeared` (a new dynamic delegate) and plays `ApparitionWhisper[3]` plus `Chains[1]` at its location. The audio subsystem listens for the sting. `BP_WardenApparition` (never-save) is not touched.

### 2.6 Footsteps and surfaces
- **`FLBFootstepRow` additions:**
  - `TArray<TObjectPtr<USoundBase>> Variants`;
  - `ULBFootstepComponent` picks a random variant that isn't the last one, falling back to `Sound`;
  - `float CrouchVolume` (0.5) and `float SprintVolume` (1.25) multiply by gait;
  - the existing `VolumeMin/Max` and `PitchMin/Max` stay.
- **Surface types** (`Config/DefaultEngine.ini`, `[/Script/Engine.PhysicsSettings]`):
  - `SurfaceType1` Stone, `SurfaceType2` Wood, `SurfaceType3` Earth, `SurfaceType4` Grass, `SurfaceType5` Water, `SurfaceType6` Metal;
  - Default plays as Stone.
- **Physical materials:** `PM_LB_Stone`, `PM_LB_Wood`, `PM_LB_Earth`, `PM_LB_Grass`, `PM_LB_Water`, `PM_LB_Metal` in `/Game/LastBell/Physics/`. Which floors get them is decided by F0 (section 7.4).

### 2.7 `LBAudioLogic` (pure functions, unit tested)
- `RainMix(E, RoofRain, Power, OutGain, InGain)` returns (out, in).
- `WindMix(E, W, InteriorWind, Howl, OutGain, Min)` returns (wind, howl).
- `PlanThunder(B, Reason, Rand)` returns (Set, Delay, Volume).
- `MusicTargets(State, Stage, Distance, Settings)` returns (tension, chase).
- `Stress(Prev, Inputs, Dt, Settings)` returns the new stress level. Inputs: Warden state and distance, sprinting, zone darkness, candle lit, a candle-out impulse.
- `AmbientTollPlan(Now, LastToll, LastBeat, Chase, Tension, Stage, Rand, Settings)` returns play now or not, the stage, strikes and the next time.
- `BellPlan(Tag, Beats)` returns (stage, strikes, delays).
- `PickVariant(Count, Last, Rand)` returns an index that is not `Last` when Count > 1.
- `Ease(Current, Target, InSec, OutSec, Dt)`.

### 2.8 Config
- **`Config/DefaultEngine.ini`:**
  - `[/Script/WindowsTargetPlatform.WindowsTargetSettings]`: `AudioMaxChannels=64` (the log shows 32 today);
  - the surface types.
- **`Config/DefaultGame.ini`:** `AudioSettings=/Game/LastBell/Data/DA_Audio.DA_Audio`.

No new plugin: `AudioModulation`, Soundscape and MetaSound graphs are not used. Volumes go through SoundClass and SoundMix, and the AUDIO_DESIGN submix plan is deferred (D-109).

### 2.9 `ALBAmbientEmitter` (C++ actor; part of P16-1)
- **What it plays:** either `TArray<TSoftObjectPtr<USoundBase>> Variants` one-shots, one every rand(`IntervalMin`, `IntervalMax`) s with the no-repeat picker, `VolumeRange` and `PitchRange`, or a single `Loop`.
- **Activation:** only while the player is within `ActiveRadius` (default 3000 cm), checked 4 times a second.
- **Where it's used:** drips at the 10 drip points (F0.8 of P15), creaks in the tower, distant chains in the crypt. Placed in P16-3.

## 3. Cue sheet
Formats: WAV, 48 kHz, 16-bit; mono for 3D sounds, stereo for 2D beds and music. Loudness targets are pre-gain (RMS over the active part, or peak): beds at −24 dBFS RMS, one-shots at a −3 dBFS peak, music at −22 dBFS RMS. Level balancing is done in the mix, not by re-rendering.

Each sound gets a name `SFX_LB_<Group>_<Name>_<NN>` or `MUS_LB_<Name>` and a class, an attenuation and a concurrency. **G** means generated by script (section 4), **K** Kenney CC0, **F** Freesound CC0 (section 5).

| Group | Asset(s) | Src | Var | Len | Loop | Class | Att | Notes |
|---|---|---|---|---|---|---|---|---|
| Weather | `SFX_LB_Rain_Out` | G | 1 | 60 s | yes | Ambience | 2D | stereo |
| | `SFX_LB_Rain_In` | G | 1 | 60 s | yes | Ambience | 2D | muffled roof patter |
| | `SFX_LB_Wind` | G | 1 | 60 s | yes | Ambience | 2D | stereo |
| | `SFX_LB_Wind_Howl` | G | 1 | 45 s | yes | Ambience | 2D | tower and belfry |
| Thunder | `SFX_LB_Thunder_Near_01..04` | G | 4 | 7–9 s | | Ambience | `ATT_LB_Thunder` | crack + rumble |
| | `SFX_LB_Thunder_Mid_01..04` | G | 4 | 6–7 s | | Ambience | `ATT_LB_Thunder` | |
| | `SFX_LB_Thunder_Far_01..04` | G | 4 | 5–6 s | | Ambience | `ATT_LB_Thunder` | |
| | `SFX_LB_Thunder_Strike_01..03` | G | 3 | 3 s | | Ambience | `ATT_LB_Thunder` | sharp tearing crack |
| Bell | `SFX_LB_Bell_Stage1..5` | G | 5 | 20–30 s | | Ambience | `ATT_LB_Bell` | section 4.4 |
| | `SFX_LB_SmallBell_Strike` | G | 1 | 4 s | | SFX | `ATT_LB_Small` | pitched per bell |
| | `SFX_LB_SmallBell_Fail` | G | 1 | 3 s | | SFX | `ATT_LB_Small` | dissonant cluster |
| | `SFX_LB_SmallBell_Solved` | G | 1 | 5 s | | SFX | `ATT_LB_Medium` | 4 bells in order, then a low resonance |
| Music | `MUS_LB_Drone_A/B/C` | G | 3 | 60 s | yes | Music | 2D | section 4.5 |
| | `MUS_LB_Tension` | G | 1 | 32 s | yes | Music | 2D | |
| | `MUS_LB_Chase` | G | 1 | 8.0 s | yes | Music | 2D | 120 BPM, 4 bars |
| | `MUS_LB_Sting_Spotted/Caught/Apparition` | G | 3 | 2–3 s | | Music | 2D | |
| Room | `SFX_LB_Room_Chapel/Crypt/Cloister/Passage/Tower/Belfry` | G | 6 | 45 s | yes | Ambience | 2D | section 4.6 |
| | `SFX_LB_Drip_Water_01..05`, `SFX_LB_Drip_Stone_01..05` | G | 10 | < 1 s | | Ambience | `ATT_LB_Small` | emitters (2.9) |
| | `SFX_LB_Creak_Wood_01..05` | F | 5 | 1–3 s | | Ambience | `ATT_LB_Medium` | tower stair and belfry emitters |
| | `SFX_LB_Chain_Distant_01..04` | F | 4 | 1–3 s | | Ambience | `ATT_LB_Large` | crypt emitters |
| Player | `SFX_LB_Step_Stone_01..06` | K | 6 | | | SFX | `ATT_LB_Step` | Kenney concrete |
| | `SFX_LB_Step_Wood_01..06` | K | 6 | | | SFX | `ATT_LB_Step` | |
| | `SFX_LB_Step_Earth_01..06` | K/F | 6 | | | SFX | `ATT_LB_Step` | Kenney grass or gravel; F if Kenney lacks it |
| | `SFX_LB_Step_Grass_01..06` | K | 6 | | | SFX | `ATT_LB_Step` | |
| | `SFX_LB_Step_Water_01..06` | F | 6 | | | SFX | `ATT_LB_Step` | puddle splashes |
| | `SFX_LB_Step_Metal_01..06` | K/F | 6 | | | SFX | `ATT_LB_Step` | grates and plates |
| | `SFX_LB_Breath_Calm/Heavy/Panic_01..04` | F | 12 | 1–3 s | | SFX | 2D | one gender-neutral voice set |
| | `SFX_LB_Breath_Gasp_01..03` | F | 3 | < 1.5 s | | SFX | 2D | the candle going out |
| | `SFX_LB_Candle_Light_01..03`, `_Out_01..03`, `_Relight` | F | 7 | | | SFX | 2D | match or flame whoosh, blow-out |
| Interact | `SFX_LB_Door_Wood_Open_01..03`, `_Stone_Open_01..03`, `_Locked_01..03` | F | 9 | 1.5–3 s | | SFX | `ATT_LB_Medium` | |
| | `SFX_LB_Lever_Notch_01..04` | F | 4 | | | SFX | `ATT_LB_Small` | dial levers |
| | `SFX_LB_Winch_01..03` | F | 3 | 2–4 s | | SFX | `ATT_LB_Medium` | ratchet and chain |
| | `SFX_LB_Stone_Grind_01..03` | F | 3 | 2–4 s | | SFX | `ATT_LB_Medium` | ritual mechanisms |
| | `SFX_LB_Key_Pickup_01..02`, `SFX_LB_Paper_01..03` | F | 5 | | | SFX | 2D | key; note read |
| | `SFX_LB_Generic_Use_01..03` | K | 3 | | | SFX | `ATT_LB_Small` | fallback |
| Warden | `SFX_LB_Warden_Breath_Slow/Fast/Heavy` | F | 3 | 8–15 s | yes | Voice | `ATT_LB_Warden` | low, pitched −20 to −30 % |
| | `SFX_LB_Warden_Step_01..05` | F/K | 5 | | | Voice | `ATT_LB_Warden` | heavy, pitched down |
| | `SFX_LB_Warden_Chain_01..04` | F | 4 | | | Voice | `ATT_LB_Warden` | |
| | `SFX_LB_Warden_Robe` | F | 1 | 10 s | yes | Voice | `ATT_LB_Warden` | cloth on stone |
| | `SFX_LB_Warden_Spotted/Roar/Windup/Exhale_01..03`, `_Caught_01..02` | F | 14 | 1–4 s | | Voice | `ATT_LB_WardenTell` | processed: pitched down, layered |
| | `SFX_LB_Apparition_Whisper_01..03` | F | 3 | 2–4 s | | Voice | `ATT_LB_Warden` | |

Tells use `ATT_LB_WardenTell`, which carries farther than the breath, so the player hears the tell before the danger.

## 4. Generated sounds (A2; `Tools/audio/gen/`, numpy + scipy, seeded, deterministic)
- **Pipeline:**
  - one script per group, plus a shared `audio_lib.py` (filters, envelopes, loop crossfade, normalisation, WAV writer);
  - output to `SourceArt/Audio/Generated/` (LFS);
  - a spectrogram contact sheet per group to `Docs/ArtTest/audio/`;
  - `python -I Tools/audio/gen/build_all.py --group <g>` rebuilds a group identically.
- **Loops:** render the length + 2 s, crossfade the last 2 s into the start (equal power), and check that the seam's RMS step is under 0.5 dB.

### 4.1 Rain
- **`Rain_Out`, three layers:**
  1. a pink-noise bed band-passed 400–9000 Hz (4th-order Butterworth), amplitude-modulated by a slow random walk (0.1–0.3 Hz, ±1.5 dB), decorrelated L and R;
  2. drop transients: a Poisson process at 900 /s per channel; each drop is a 2–6 ms exponentially decaying sine burst at 2–7 kHz with an exponential amplitude distribution (mean −30 dBFS);
  3. low splatter: noise band-passed 150–600 Hz at −34 dBFS.
- **`Rain_In`:**
  - a muffled roof: layer 1 low-passed at 1800 Hz, −8 dB;
  - heavier, slower drops: 220 /s, 1–3 kHz, 8–15 ms;
  - occasional big drips, 0.5 /s, 400–900 Hz plinks.

### 4.2 Wind
- **`Wind`:** white noise through two resonant band-passes (centres 250 Hz and 700 Hz, Q 2–4).
  - Each centre drifts on a random walk (±30 %, 0.05–0.2 Hz) and the amplitude drifts on its own walk (±6 dB).
  - Stereo comes from independent walks.
- **`Wind_Howl`:** a narrow band-pass (Q 12) that glides between 380 and 520 Hz (0.07 Hz), plus 20 % of `Wind`.

### 4.3 Thunder
- **Near:**
  - a 40 ms broadband crack, emphasised at 2–8 kHz;
  - then a rumble: brown noise low-passed at 120–300 Hz, with 3–6 decaying bursts at random times over 6–9 s.
- **Mid:** no crack, a 1.5 s rise, a 6 s rumble low-passed at 400 Hz.
- **Far:** a slow attack and a 5 s rumble low-passed at 180 Hz, −8 dB.
- **Strike:** two cracks 60 ms apart, each a 25 ms burst with 3–10 kHz emphasis, a 400 ms tearing noise tail and a short sub thump (50 Hz, 150 ms).
- **Seeds:** 1001–1004 for Near, 1101–1104 for Mid, 1201–1204 for Far, 1301–1303 for Strike.

### 4.4 Bells
- **The great bell's partials,** relative to a prime of 110 Hz:

  | Partial | Ratio | T60 |
  |---|---|---|
  | Hum | 0.5 | 25 s |
  | Prime | 1.0 | 15 s |
  | Tierce | 1.2 | 12 s |
  | Quint | 1.5 | 8 s |
  | Nominal | 2.0 | 10 s |
  | Superquint | 3.0 | 5 s |
  | Octave nominal | 4.0 | 4 s |
  | Upper | 5.3, 6.2, 7.1, 8.9, 11.3 | 0.5–2 s |

  - Amplitudes: hum 0.6, prime 0.5, tierce 0.45, quint 0.25, nominal 0.7, the others 0.15–0.3.
  - The strike is a 15 ms noise burst plus the upper partials.
- **Crack amount c:**
  - each partial splits into two detuned copies (±(0.6 + 1.2c) Hz), which makes beating;
  - the sum goes through an asymmetric soft clip (drive 1 + 1.5c, bias 0.1c);
  - plus a band-passed noise rattle (600–1800 Hz) amplitude-modulated at the beat rate, at c × −24 dB.
- **Stages:** 1 is the farthest and 5 the finale. The reverb is a synthetic exponential-decay noise impulse response.

  | Stage | c | Low-pass | Reverb | Level | Other |
  |---|---|---|---|---|---|
  | 1 | 0.6 | 900 Hz | 6 s | −18 dB | |
  | 2 | 0.75 | 1500 Hz | 5 s | −14 dB | ±4 cents vibrato at 0.3 Hz |
  | 3 | 0.9 | 2500 Hz | 4 s | −10 dB | a −20 cent bend over the tail |
  | 4 | 1.0 | full band | 3.5 s | −6 dB | plus a 1.2 s reversed-swell pre-roll |
  | 5 (finale) | 0 | full band | 8 s | 0 dB | plus a sub hum at 27.5 Hz, 30 s long |

- **Small bell:** prime 523 Hz with the same partial recipe, T60 values ÷ 4, c 0.15. Its pitch per bell is set at play time: the multiplier is 1 ÷ size, with sizes 1.30, 1.15, 1.00 and 0.85 (D-081).
- **`SmallBell_Fail`:** all four bells struck within 120 ms, each detuned 30–70 cents, c 0.8.

### 4.5 Music
- **`Drone_A`:** detuned sine and saw stacks on A1 (55 Hz) with a minor second and a tritone, a low-pass sweeping 200–900 Hz over 40 s, and filtered "air" noise.
- **`Drone_B`:** the great bell's hum and tierce resynthesised as slow, swelling tones (a 4 s attack), plus a faint stage-2 bell crack.
- **`Drone_C`:** vowel formants on noise ('oo': 300 / 870 / 2240 Hz) as a low "choir" breath, with slow amplitude swells.
- **`Tension`:** no pulse. Tremolo string-like detuned saws band-passed 200–2000 Hz, 5 Hz tremolo at 20 % depth, plus high harmonic shimmer.
- **`Chase`:** 120 BPM, exactly 8.000 s:
  - a double heartbeat thump (a 50 Hz sine with a pitch drop, plus a noise click) on beats 1 and 1-and;
  - a low ostinato (saw 55/58 Hz) in eighths;
  - a rising noise swell over the 4 bars.
- **Stings:**
  - Spotted: a 2 s dissonant swell into a hit;
  - Caught: a 3 s low hit plus a reverse bell;
  - Apparition: a 3 s whispering noise swell.

### 4.6 Room tones and drips
- **Room tones:**

  | Room | Recipe |
  |---|---|
  | Crypt | a 40 Hz rumble at −36 dB, distant water (rain-in drops at 30 /s, −30 dB), air |
  | Chapel | air plus faint wind through the roof hole (`Wind` −20 dB, high-passed at 300 Hz) |
  | Cloister | light air |
  | Passage | air plus a faint draught |
  | Tower | low air plus `Wind_Howl` −14 dB |
  | Belfry | `Wind` −8 dB plus `Wind_Howl` −10 dB |

- **Drips:**
  - water: a sine glide 800 to 1600 Hz over 30 ms plus a bubble (a 1.2 kHz damped sine);
  - stone: a 3 ms click band-passed 2–4 kHz.

## 5. Recorded sounds (A1, A3)

### 5.1 Kenney (CC0)
- **Packs:** the asset-curator downloads "Impact Sounds" and "RPG Audio" from kenney.nl (direct zip links on each pack's page) to `ExternalAssets/Incoming/kenney-<pack>/`. It records the file size and the licence text, which is CC0, in `ASSET_REGISTRY.md`.
- **If a pack is missing or has no CC0 licence text,** stop and report.

### 5.2 Freesound (CC0)
- **The list (asset-curator):** about 70–90 sounds in a table at `Docs/ArtTest/audio/freesound_list.md`, built from freesound.org search pages filtered to licence "Creative Commons 0" for every **F** row in section 3. Each row gives:
  - the sound id, title, author and URL;
  - the duration, sample rate and channels;
  - the CC0 licence as shown on the page;
  - which cue it feeds and why.

  It picks 2–3 candidates for each needed variant, so the owner can skip weak ones.
- **The owner downloads them,** with a free account, about 20–30 minutes, into `ExternalAssets/Incoming/freesound/` as `<id>_<originalname>`.
- **Rules:** never a CC-BY or CC-BY-NC sound; never "Sampling+". Every sound used gets an `ASSET_REGISTRY.md` row (id, author, URL, CC0).

### 5.3 Story beats (bell and drones; tag added only)
| Trigger | Bell | Drone |
|---|---|---|
| New game, no beat tag present at activation | stage 1 × 3 (6 s, then 4.5 s apart) | Drone A |
| `State.Ritual.1` | stage 2 × 3 (2 s, 4.5 s) | Drone B |
| `State.Event.CryptEntered` | none | Drone A |
| `State.Ritual.2` | stage 3 × 3 (2 s, 4.5 s) | Drone C |
| `State.Ritual.3` | stage 4 × 3 (2 s, 4.0 s) | Drone B |
| `State.Event.TowerTop` | stage 4 × 4 (1 s, 3.5 s) | Drone C |
| `State.Event.Finale` | stage 5 × 5 (0 s, 5.0 s); Phase 17 may replace this | none |
| Between beats (ambient) | the current stage × 1–2 at volume 0.5, every 240–420 s (section 2.3 rules) | none |

### 5.4 Processing (A3; `Tools/audio/prep/prep_recorded.py`)
- **Per item:**
  - trim silence at −50 dBFS with 20 ms pads, and fade in 5 ms and out 30 ms;
  - mono for 3D sounds;
  - resample to 48 kHz;
  - normalise to the section 3 targets;
  - write to `SourceArt/Audio/Recorded/<cue>.wav`.
- **Warden vocals** are pitch-shifted (−20 to −35 %), layered (two sources plus a low sub at −12 dB) and given a short room tail.
- **Recipe:** each item's processing is recorded in `Tools/audio/prep/recipes.json`, so it can be rebuilt.

## 6. Mix and acoustics (assets created in P16-2; folder `/Game/LastBell/Audio/Mix/`)

### 6.1 SoundClasses and the user mix
- **Classes:** `SCL_LB_Master`, with children `SCL_LB_SFX`, `SCL_LB_Ambience`, `SCL_LB_Music`, `SCL_LB_Voice` (the Warden) and `SCL_LB_UI`.
- **Mix:** `SMX_LB_User` holds one adjuster per class at volume 1.
- **Defaults:** class volume 1. Balancing is done in P16-4 by changing the class volumes and the `DA_Audio` gains.

### 6.2 Attenuation
The near and far distances are the inner radius and the falloff distance. All are spatialised.

| Asset | Near / falloff (cm) | Shape | Other |
|---|---|---|---|
| `ATT_LB_Step` | 200 / 1500 | | |
| `ATT_LB_Small` | 200 / 1500 | | |
| `ATT_LB_Medium` | 400 / 3000 | | air absorption low-pass from 1000 to 4000 cm down to 3000 Hz |
| `ATT_LB_Large` | 800 / 6000 | | |
| `ATT_LB_Warden` | 300 / 3500 | natural | occlusion on (Visibility trace, volume 0.4, low-pass 1200 Hz, interpolation 0.3 s) |
| `ATT_LB_WardenTell` | 500 / 5000 | | occlusion volume 0.6 |
| `ATT_LB_Thunder` | 20000 / 60000 | | non-spatialised radius 3000; spatialised for direction only |
| `ATT_LB_Bell` | 10000 / 120000 | | non-spatialised radius 2000 |

### 6.3 Concurrency
| Asset | Max | Resolution |
|---|---|---|
| `CON_LB_Steps` | 4 | stop oldest |
| `CON_LB_Thunder` | 2 | stop quietest |
| `CON_LB_Drips` | 6 | stop farthest |
| `CON_LB_Tells` | 1 | stop oldest |

### 6.4 Reverb (`ReverbEffect`, `RVB_LB_*`)
| Effect | Decay | Density | Diffusion | Gain | GainHF | Notes |
|---|---|---|---|---|---|---|
| `RVB_LB_Chapel` | 3.2 s | 1.0 | 0.9 | 0.32 | 0.6 | |
| `RVB_LB_Crypt` | 2.4 s | 1.0 | 1.0 | 0.35 | 0.4 | darker |
| `RVB_LB_Cloister` | 1.6 s | 0.8 | 0.8 | 0.25 | 0.7 | |
| `RVB_LB_Passage` | 1.2 s | 0.9 | 0.9 | 0.28 | 0.6 | |
| `RVB_LB_Tower` | 2.8 s | 0.9 | 0.8 | 0.30 | 0.5 | |
| `RVB_LB_Belfry` | 1.5 s | 0.7 | 0.7 | 0.22 | 0.7 | |

- Late delay 0.04 s and reflections delay 0.01 s throughout.
- Tuning ranges for P16-4: decay ±40 %, gain ±0.1.

### 6.5 AudioVolumes (P16-3)
- **One per area:** each has its `RVB_` effect, a volume of 0.6, a fade time of 1.0 s, and interior settings in this table.

  | Area | Exterior volume | Exterior low-pass (Hz) | Interior volume |
  |---|---|---|---|
  | Chapel, crypt, tower, passage | 0.35 | 2500 | 1 |
  | Cloister, belfry | 0.7 | 6000 | 1 |

- **Bounds** come from F0: each area's PP volume and its storm zones.

## 7. F0: read-only survey (environment-designer or lighting-vfx, Sonnet high; Unreal open, PIE off)
The script is `Tools/audio/p16_f0_survey.py`. It writes `Docs/ArtTest/audio/p16_f0.json` and `p16_f0_tables.md`, and never sets or saves anything.
1. **Interactables:**
   - every actor with a `ULBInteractableComponent`, `ULBDialComponent` or `ULBSequencePuzzleComponent`: label, class, parent classes, location, and the component fields (granted and required tags, single use);
   - grouped by class with counts;
   - the proposed cue row per class, or "silent" with a reason.
2. **Small bells:** the 4 cloister bells (`BP_SmallBell_Cloister`): their step tags, sizes and locations, giving the `SmallBellPitch` map.
3. **Areas:** the bounds of the PP volumes (`PP_Chapel`, `PP_Crypt`, `PP_Cloister`, `PP_Tower`, `PP_Outdoor_Night`) and the storm zones, to propose `ALBAudioZone` and `AudioVolume` boxes for chapel, crypt, cloister walk, passage, tower stair, belfry, and the gatehouse and well house, with `RoofRain`, `InteriorWind`, `Howl` and `Darkness` proposed per area.
4. **Floors:**
   - **Samples:** at least 120 floor points, about 15 per area plus the stair landings; each traces down from 100 cm above the floor on the footstep trace channel (`ULBFootstepComponent`'s query: same channel, `bReturnPhysicalMaterial`).
   - **Recorded per hit:** actor label and class, component, material and physical material.
   - **Method rule:**
     - if at least 80 % of the hits are on greybox or collision actors (D-068), surfaces are set as `BodyInstance.PhysMaterialOverride` on those placed actors, from an area-and-mesh table;
     - otherwise the physical material goes on the floor MIs (never on `M_LB_Surface`).
   - **Water:** puddle areas from P11 get Water only where the player can stand in water (crypt pools); cobble puddles stay Stone.
5. **Bell location:** the great bell's actor and its bounds centre.
6. **Warden:** its classes and spawn points, and every `ALBWardenApparition`.
7. **Audio config now:** `AudioMaxChannels`, existing AudioVolumes (expected none) and sound assets (expected none).
8. **MCP capability probe** (describe only, no creation): which tools can create or import a SoundWave from a WAV, `SoundClass`, `SoundMix`, `SoundAttenuation`, `SoundConcurrency`, `ReverbEffect`, `PhysicalMaterial` and `AudioVolume`, and set their properties. This feeds S1.

## 8. S1: spike, creating audio assets over MCP (audio-designer, Sonnet high; Unreal open)
1. Import one generated WAV (`Tools/audio/gen` test tone: 1 s, 440 Hz) to `/Game/LastBell/Audio/Spike/`. Try MCP first; if MCP can't, use headless Unreal Python (`AssetImportTask` with `SoundFactory`, Unreal closed).
2. Create one each of `SoundClass`, `SoundMix`, `SoundAttenuation`, `SoundConcurrency`, `ReverbEffect` and `PhysicalMaterial`, set three properties on each and read them back. Place one `AudioVolume` around the chapel nave with the reverb.
3. **Owner check (5 minutes):** in Play (the audio subsystem doesn't exist yet), with a placed `AmbientSound` of the tone in the nave. Does the reverb sound, and is it muffled outside?
4. **Record:** the method per asset type in `Tools/mcp/MCP_NOTES.md`, in a new section "Audio over MCP".
5. **Clean up:** delete the spike assets and actors; nothing is saved.

**Verdict:** for each asset type, MCP or headless. If WAV import works only headless, every import batch in P16-2 runs with Unreal closed.

## 9. Listening session (P16-4, owner on headphones, about 40 minutes; live tuning over MCP)
1. **Rain and wind outdoors:**
   - the RainOut and RainIn gains, the wind gain and `WindMin`;
   - the indoor crossfade at the chapel door and the cloister arches.
2. **Thunder:** delay range and loudness. `lb.Audio.Thunder 0/1/2`, and flashes via `lb.Storm.Flash`.
3. **The bell, stages 1–5:** `lb.Audio.Bell n`. Loudness, crack amount, and whether stage 1 is distant enough.
4. **Music:** forced states with `lb.Audio.Music`: tension levels, the chase level, fades; the stings.
5. **The Warden:** in the crypt or cloister with the Warden active: breath distance, steps and chains, the tells' readability, occlusion through walls.
6. **Footsteps on every surface** and the gait volumes. Breathing under stress: Warden, sprint, darkness with the candle lit and out, and the candle-out gasp.
6a. **Ambient tolls:** frequency and loudness (`AmbientTollInterval` shortened to 30–40 s for the session only, then put back).
7. **Interactions:** doors, levers, the winch, the small bells (pitches, the fail cluster), notes, the key, the candle.
8. **Rooms:** reverb per area and the room tones.
9. **Overall class balance:** SFX, ambience, music and voice.

The values chosen are applied in P16-5.

## 10. Run-through and performance (P16-6, owner, about 30 minutes)
- **Run-through:** a fresh Play from the start through the chapel, the crypt (with the Warden), the cloister and the tower. The owner judges dread, readability and silence.
- **Performance:** the six P14 section 11 spots plus a chase.
  - **Readings:** `stat audio` and `stat soundwaves` (voices), `au.Debug.Sounds 1` (top sounds), and `stat unit`.
  - **Pairs:** with `lb.Audio.Enabled` 1 and 0, read off first (D-107 lesson).
  - **Pass:**
    - at most 48 voices;
    - audio-thread time at most 2.0 ms;
    - game thread +0.3 ms with the D-107 noise caveat;
    - no audible dropouts.
- **If it fails, the ladder:**
  1. concurrency limits halved;
  2. `ALBAmbientEmitter` `ActiveRadius` 3000 to 2000;
  3. Warden occlusion traces off for the breath;
  4. RainIn and room tones merged.

## 11. Tests (P16-1; `Source/LastBellTests/Tests/LBAudioTests.cpp`, `LBAudioFunctionalTests.cpp`)
- **Unit tests (`LastBell.Audio.Logic.*`):**
  - `RainMix`: exposure 0, 0.5 and 1, roof 0 and 1;
  - `WindMix`;
  - `ThunderPlan`: the variant boundaries, delay monotonic in brightness, the jitter bounds;
  - `MusicTargets`: every Warden state, stage below the minimum gives 0, distance beyond `TensionNearDistance` gives 0, Chase;
  - `Stress`: rise, decay, the sprint bonus, darkness lit against unlit, the candle-out impulse;
  - `AmbientTollPlan`: interval bounds, skipped in a chase, above the tension limit and inside the gap after a beat, none after the finale, stage from the beats reached;
  - `BellPlan`: each beat tag, and an unknown tag gives nothing;
  - `PickVariant`: no repeat over 1000 draws when Count ≥ 2, and Count 1 returns 0;
  - `Ease`.
- **Functional tests (`LastBell.Functional.Audio.*`; test map with a tagged moon, as the P14/P15 tests):**
  - `ActivatesWithStorm` and `DisabledByCVar`;
  - `ThunderAfterFlash`: a debug flash gives one thunder request inside the planned delay window;
  - `TargetStrikeCrack`;
  - `BellOnRitualTag`: `State.Ritual.1` added gives 3 stage-2 requests;
  - `NoBellOnStateReplaced`;
  - `NewGameToll`;
  - `AmbientToll`: with a 2–3 s interval override, a toll request at the current stage, and none while a chase is forced;
  - `CandleOutGasp`: a candle going out gives a gasp request and a stress rise;
  - `MusicFollowsWarden`: a forced Chase gives a chase target of 1 and tension of 0.4;
  - `InteractionCue`: a spawned test actor whose class is mapped gives a request at its location;
  - `DeniedCue`;
  - `SequenceSmallBellPitch`;
  - `FootstepVariantNoRepeat`;
  - `UserVolumesApplied`;
  - `WardenTells`: a spawned Warden test double fires `OnPlayerSpotted`, giving a Spotted request.
- **On the real level, `Monastery.AudioSetup`:**
  - `DA_Audio` is linked and loads, and every soft reference loads;
  - every interactable class in `L_Monastery` is mapped or listed silent;
  - there are at least 6 `ALBAudioZone`s and 6 `AudioVolume`s;
  - `DebugForceMusicState` is −1;
  - `DT_Footsteps` has a row for each of the 6 surfaces, each with at least 4 variants.
- **The existing 141 tests still pass.**

## 12. Tasks
| Task | Scope | Owner | Needs | Depends on |
|---|---|---|---|---|
| P16-0 | Plan approval. D-108 (scope and owner choices), D-109 (architecture: C++ audio director, class-mapped cues, SoundClass mix, submixes deferred, activation with the storm), D-110 (asset prefixes `SCL_`, `SMX_`, `ATT_`, `CON_`, `RVB_`, `PM_` and the folders `/Game/LastBell/Audio/{Weather,Thunder,Bell,Music,Room,Player,Interact,Warden,Mix}`, `/Game/LastBell/Physics`), D-111 (sourcing pipeline). R-70…R-76. `IMPLEMENTATION_PLAN.md` Phase 16 table; the CLAUDE.md naming line; `AUDIO_DESIGN.md` drift notes | lead + owner | — | — |
| F0 | Section 7 | Sonnet agent [EDITOR read-only] | Unreal open | P16-0 |
| S1 | Section 8 | audio-designer [EDITOR] + owner 5 min | Unreal open | F0 |
| A1 | Kenney download; the Freesound list; the owner downloads; registry rows | asset-curator + **owner** (20–30 min) | — | P16-0 |
| A2 | Section 4: generated sounds, spectrogram sheets | audio-designer (no editor) | — | P16-0 |
| A3 | Section 5.4: prepare the recorded sounds | audio-designer (no editor) | — | A1 |
| A4 | **Owner audition** of the WAVs on headphones (about 20 min; a playlist page in `Docs/ArtTest/audio/audition.md`): keep, redo or replace per cue | lead + **owner** | — | A2, A3 |
| P16-1 | Section 2 code, config, console, tests | gameplay-programmer | **Unreal closed** | P16-0 (the F0 values go into data in P16-2) |
| P16-2 | Imports (per the S1 method), the section 6 mix assets, `PM_`, `DA_Audio` creation and fill, `DT_Footsteps` rows | audio-designer [EDITOR] | | S1, A4, P16-1 |
| P16-3 | Level work: `ALBAudioZone`s, `AudioVolume`s, `ALBAmbientEmitter`s, floor surfaces (F0 rule); `Tools/audio/p16_level.py --apply/--check/--save`; census; one map save | audio-designer [EDITOR] | | P16-2 |
| P16-4 | Listening session (section 9) | lead + **owner** | Unreal in front, headphones | P16-3 |
| P16-5 | Apply the choices, save | audio-designer [EDITOR] | | P16-4 |
| P16-6 | Run-through and performance (section 10) | **owner** + performance-engineer | | P16-5 |
| P16-7 | QA, docs (`TECHNICAL_DESIGN` "Audio", `AUDIO_DESIGN`, `MCP_NOTES`, `PERFORMANCE_BUDGET`, `RISKS`, `ASSET_REGISTRY`), the full suite with the editor closed, the Game target build; "PHASE 16 READY FOR YOUR REVIEW" | qa-reviewer, docs agent, lead | Unreal closed for the suite | all |

One editor agent at a time. A1, A2 and A3 run without the editor, in parallel with F0 and S1.

## 13. Risks (added to `RISKS.md` at P16-0)
| Id | Risk | Mitigation |
|---|---|---|
| R-70 | MCP can't import WAVs or create some audio asset types | S1 decides; fall back to headless Unreal Python with Unreal closed |
| R-71 | Generated sounds sound synthetic (above all thunder and the bell) | The owner auditions WAVs before import (A4); a Freesound CC0 replacement for any rejected cue; the recipes stay tweakable |
| R-72 | Freesound has too few good CC0 sounds for the Warden's voice | The curator lists 2–3 candidates per variant; processing (pitch and layering) makes a creature from human or animal CC0 sources; generated formant growls as a fallback |
| R-73 | The footstep trace hits greybox collision with no physical material, so every surface sounds the same | F0 measures the hits; the per-actor `PhysMaterialOverride` rule; `Monastery.AudioSetup` samples check the surface per area |
| R-74 | The suite runs with `-nosound`, so tests can't hear anything | The test sink checks requests; owner audition, listening session and run-through |
| R-75 | Voice count or audio-thread cost spikes (rain, emitters, the Warden in a chase) | Concurrency assets, emitter activation radius, 64 channels, the section 10 ladder |
| R-76 | The never-save Blueprints can't hold sound slots | Cues are mapped by class in `DA_Audio` and played by C++ (D-109); documented as drift in `AUDIO_DESIGN.md` |

## 14. Not in this phase
- HRTF or binaural (Phase 20).
- Main menu and UI sounds: the `SCL_LB_UI` class exists, and the sounds come in Phase 18.
- The finale sequence's timing, and the ending (Phase 17). Phase 16 provides bell stage 5 and `PlayBell`.
- Subtitles and voice acting.
- MetaSound graphs, Audio Modulation and Soundscape.
- Changes to gameplay or AI behaviour. The Warden's hearing is unchanged; sounds are not reported as AI noise beyond what already exists.
- Music during menus or the loading screen.

## Results
(Filled in as tasks complete.)

### A1–A4: sourcing, generated and recorded sounds, owner audition (2026-11-09)
- **A1** (c371daf, caaeeff):
  - Kenney "Impact Sounds" and "RPG Audio" downloaded; the `License.txt` in each zip says CC0.
  - A Freesound CC0 list of 127 candidates, every page checked, plus a minimum set of 58 that the owner downloaded in full.
- **A2** (90dc110, 7be3279):
  - 51 generated WAVs; 145 objective checks pass; rebuilds are byte-identical.
  - **Pre-audition fixes:** `Sting_Spotted` became an immediate hit with a 1.2 s tail, and the small bells' hum dropped from 0.6 to 0.2.
  - **Mix gains:** the per-cue `mix_gain_db` values in `manifest.json` (bell stages, far thunder) go into `DA_Audio` in P16-2, not into the files.
- **A3** (e4820fc):
  - 124 recorded WAVs from 56 Freesound and 36 Kenney sources; objective checks pass; deterministic; registry rows added.
  - **Substitutions for thin sources:** pitch copies for the 6th Kenney steps and for the gasp; Kenney clicks for two lever notches.
- **A4** (af9431a): the owner listened through `Docs/ArtTest/audio/audition.html` (175 sounds) on headphones and judged **everything keep**.

### F0: read-only survey (2026-11-09, fb5b47e)
- **Record:** `Tools/audio/p16_f0_survey.py`; data and tables in `Docs/ArtTest/audio/p16_f0.json` and `p16_f0_tables.md`. Nothing was set or saved, and the census is unchanged at 3054.
- **Interactables:** 29 actors in exactly the 12 unmapped classes. The cue proposals in the tables are **accepted by the lead**, including:
  - doors use wood cues, and Denied only on `Door_ChapelMain`;
  - the crank pickup uses `Key_Pickup` (pitch 0.85–0.95);
  - the capstan uses `Winch` (pitch 0.9–1.0);
  - `BP_SequencePuzzle`, `BP_SmallBell_Cloister` and `BP_TagInteractable_GreatBell` are silent; the great bell is covered by the `State.Event.Finale` beat.
- **`SmallBellPitch`:** `State.Tower.Bell.1` 0.7692, `.2` 0.8696, `.3` 1.0, `.4` 1.1765.
- **`BellLocation`:** (12420.1, 2000.0, 2750.0).
- **Zones:** the F0 table is accepted:
  - Chapel, priority 1;
  - Crypt, priority 2, z −1200…−20;
  - Cloister walk, priority 1;
  - Garth, priority 2: outdoor values, no room tone, no reverb;
  - Passage, priority 1;
  - TowerStair, priority 3;
  - Belfry, priority 4, from z 2400.

  Gatehouse and well house: none, they are open to the sky.
- **Floors:**
  - 168 floor hits; 81 % are on hidden or greybox collision, so the method is a **per-actor `PhysMaterialOverride`**.
  - Stone is the default. Wood: tower landings, stair flights and the belfry. Grass: the garth. Earth: `Garden_Earth_*`.
  - **Water:** the pool planes have no collision, so the footstep trace hits the crypt floor shell. P16-3 places a thin box under each pool (§8 brief).
- **MCP:** there is no tool to import a WAV or to create SoundClass, SoundMix, SoundAttenuation, SoundConcurrency, ReverbEffect or PhysicalMaterial assets. **Verdict, which replaces the S1 spike:**
  - all audio assets are created by **headless Unreal Python with Unreal closed** (the route in MCP_NOTES "Warden" item 1: `UnrealEditor-Cmd -run=pythonscript`);
  - level placement (zones, AudioVolumes, emitters, overrides) goes over MCP with Unreal open;
  - the owner's reverb check moves into the listening session (P16-4).
- **Lead decisions on the F0 questions:**
  1. **Small-bell sounds only for the bell puzzle.** The strike, fail and solved sounds play only when the step tag is a key of `SmallBellPitch`, or for Solved when the puzzle's steps are. The candle puzzle (`Puzzle_Candles`):
     - a step is silent, because the candle's own interact cue already plays;
     - a failure plays one `Player.CandleOut` variant at the puzzle actor;
     - solving is silent, because the ritual mechanism and the beat cover it.
  2. **The belfry box** from z 2400 with priority 4: accepted.
  3. **Passage exposure 0.3** (from P14) stays. The rain level there is judged in P16-4.

### P16-2 brief (audio-designer, Sonnet high; Unreal CLOSED)
**Part A, code:**
- the small-bell gating of the F0 decision 1, with a new functional test `LastBell.Functional.Audio.CandlePuzzleNotBells`;
- build and test with `Tools/build_and_test.ps1`.

**Part B, `Tools/audio/p16_2_assets.py`:** headless, idempotent; run with `UnrealEditor-Cmd <uproject> -run=pythonscript -script=<py> -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>`. It writes a JSON report.
1. **Import** all 175 WAVs from `SourceArt/Audio/Generated/` and `SourceArt/Audio/Recorded/` (an `AssetImportTask` with automated, replace-existing and save on). Folders under `/Game/LastBell/Audio/`:

   | Folder | Files |
   |---|---|
   | `Weather` | `SFX_LB_Rain_*`, `SFX_LB_Wind*` |
   | `Thunder` | `SFX_LB_Thunder_*` |
   | `Bell` | `SFX_LB_Bell_*`, `SFX_LB_SmallBell_*` |
   | `Music` | `MUS_LB_*` |
   | `Room` | `SFX_LB_Room_*`, `SFX_LB_Drip_*`, `SFX_LB_Creak_*`, `SFX_LB_Chain_Distant_*` |
   | `Player` | `SFX_LB_Step_*`, `SFX_LB_Breath_*`, `SFX_LB_Candle_*`, `SFX_LB_Key_*`, `SFX_LB_Paper_*` |
   | `Interact` | `SFX_LB_Door_*`, `SFX_LB_Lever_*`, `SFX_LB_Winch_*`, `SFX_LB_Stone_*`, `SFX_LB_Generic_*` |
   | `Warden` | `SFX_LB_Warden_*`, `SFX_LB_Apparition_*` |

2. **Per SoundWave** (from the cue sheet, §3):
   - `bLooping` true for the loops: the 4 weather beds, 6 room tones, 3 drones, tension, chase, the 3 Warden breath loops and the robe;
   - `SoundClassObject`;
   - `AttenuationSettings`; none for the 2D sounds;
   - `ConcurrencySet` (Steps, Thunder, Drips, Tells);
   - `Volume` = 10^(`mix_gain_db` / 20) from `SourceArt/Audio/Generated/manifest.json` (bell stages, far thunder), otherwise 1.0.
3. **Mix assets** (`/Game/LastBell/Audio/Mix/`):
   - `SCL_LB_Master` with children `SCL_LB_SFX`, `_Ambience`, `_Music`, `_Voice`, `_UI` (parent and child links set both ways);
   - `SMX_LB_User`, empty, since the C++ sets the overrides;
   - the 8 `ATT_LB_*` of §6.2, the 4 `CON_LB_*` of §6.3 and the 6 `RVB_LB_*` of §6.4, every value as in the tables.
4. **Physical materials** (`/Game/LastBell/Physics/`): `PM_LB_Stone`, `_Wood`, `_Earth`, `_Grass`, `_Water`, `_Metal` with `SurfaceType` 1–6.
5. **`DA_Audio`** (`/Game/LastBell/Data/`, class `LBAudioSettings`):
   - every sound group filled from the imports, with arrays in variant order;
   - `InteractionCues` and `SilentClasses` per F0 as accepted above, using soft class paths of the `_C` Blueprint classes;
   - `SmallBellPitch` and the `SmallBell*` sounds;
   - `BellLocation`;
   - `BellBeats` from `FillPlanDefaults()` (or the same rows written directly);
   - `UserMix` = `SMX_LB_User`, `UserClasses` (Master, SFX, Ambience, Music, Voice, UI);
   - every other field at the C++ default; `DebugForceMusicState` −1.
6. **`DT_Footsteps`:**
   - rows `Default` (Stone variants), `Stone`, `Wood`, `Earth`, `Grass`, `Water` and `Metal` with `SurfaceType` set and all 6 `Variants` each;
   - `VolumeMin`/`Max` 0.8/1.0, `PitchMin`/`Max` 0.95/1.05, `CrouchVolume` 0.5, `SprintVolume` 1.25.
7. **Save and verify:** save each package, then a verification pass loads every asset and prints the counts and every property it set.

**Then:**
- run the suite: `Monastery.AudioSetup` may still fail only on the zone and AudioVolume counts;
- record the method in MCP_NOTES "Audio assets (headless)";
- commit the scripts, the imported `.uasset`s, `DA_Audio`, `DT_Footsteps` and the report.

### P16-3 brief (audio-designer, Sonnet high; Unreal OPEN; `Tools/audio/p16_level.py --apply/--check/--save`, folder `Audio`)
1. **Seven `ALBAudioZone`s** per the F0 table (location, extent, priority, values, room tone).
2. **AudioVolumes** for Chapel, Crypt, Cloister walk, Passage, TowerStair and Belfry:
   - the same boxes, with brush scale = size ÷ 200;
   - `settings`: the `RVB_LB_*` effect, volume 0.6, fade 1.0;
   - `ambientZoneSettings` per §6.5;
   - priority as for the zone;
   - the Garth gets a no-reverb AudioVolume with priority 2, so the cloister reverb doesn't apply in the open garth.
3. **`ALBAmbientEmitter`s:**

   | Where | Emitters | Sounds |
   |---|---|---|
   | P15 F0.8 drip points (crypt and belfry) | 10 | crypt water points: `Drip_Water` variants, interval (1.5, 4) s; stone points: `Drip_Stone` variants, interval (2, 6) s |
   | Tower stair (3) and belfry (2), placed at beam joints from F0 | 5 | `Creak_Wood`, interval (8, 20) s |
   | Crypt, deep corners | 3 | `Chain_Distant`, interval (20, 45) s, `ActiveRadius` 4000 |

4. **Floors:** `BodyInstance.PhysMaterialOverride` on the placed actors in the F0 surface table:
   - Wood on the tower landings, stair flights and belfry floor;
   - Grass on the garth floor actor;
   - Earth on `Garden_Earth_*`.
5. **Water boxes:** three thin hidden boxes, `/Engine/BasicShapes/Cube`, `bHiddenInGame`, top 0.5 cm above the crypt floor shell, covering `CA_Water_W`, `CA_Water_E` and `CA_Water_Ledge`.
   - Collision: query only, Block Visibility, Ignore every other channel including Pawn and the interaction channel.
   - `PhysMaterialOverride` = `PM_LB_Water`, `CanEverAffectNavigation` false, cast shadow off.
   - Labels `AUD_Water_W`, `AUD_Water_E` and `AUD_Water_Ledge`.
6. **Census:** before 3054; after 3054 + 7 zones + 7 AudioVolumes + 18 emitters + 3 water boxes = **3089**.
7. **Close-out:** `--check` all PASS, then one map save; never save anything on the never-save list.
8. **Suite** with Unreal closed: all tests pass, including `Monastery.AudioSetup`.
