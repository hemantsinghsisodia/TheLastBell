# THE LAST BELL — Technical Design

Status: Phase 0, revised after the independent architecture review (findings in DECISIONS D-011 to D-020). Nothing is implemented yet. Engine: UE 5.8.3 launcher build, Win64, DX12 SM6.
This document is the source of truth for the architecture. Any deviation must be recorded in `DECISIONS.md`.

## 1. Principles
- **Composition over inheritance.** Actors get their behavior from components, not deep class trees.
- **C++ owns systems, Blueprint owns content.** C++ handles the framework, reusable components, persistent state and the AI foundation. Blueprint handles puzzles, level scripting, designer tuning and VFX/cinematic hooks.
- **Progress is tags.** World progression is one set of Gameplay Tags. Systems react to tag changes, not to each other.
- **No god classes, no manager actors.** Global services are subsystems with narrow APIs.
- **No hard asset references in C++.** Assets come through `UPROPERTY` defaults on Blueprint subclasses, Data Assets or `TSoftObjectPtr`.
- **Build only what the current phase needs.** Each system lists what it deliberately does *not* do.

## 2. Module layout
There is one runtime module, `Source/LastBell/` (prefix `LB`), added in Phase 1, plus (from Phase 3, REV-003 M6) a **`LastBellTests`** module that holds all automation tests and test helpers. It's built for the Editor target only and never ships. Classes are created only in the phase that needs them.

```
Source/LastBell/
  LastBell.Build.cs  LastBell.h/.cpp  LBGameplayTags.h/.cpp  LBLog.h
  Systems/      ALBGameMode, ALBPlayerController, ULBWorldStateSubsystem, FLBWorldState, console commands (P1)
                ULBGameSettings (DeveloperSettings: MainMenuMap, NewGameMap)     (P2)
  Character/    ALBCharacter                                                     (P1)
                ULBPlayerTuningData (DA_PlayerTuning), LBPlayerTypes (ELBGait, ELBInputLock (P17) + pure logic structs),
                ULBCameraFeelComponent, ULBFootstepComponent, ULBCandleComponent, ULBInspectionComponent (P3)
  Components/   ULBInteractorComponent, ULBInteractableComponent                 (P1)
                ULBInspectableComponent                                           (P3)
  Puzzles/      ULBSequencePuzzleComponent, ULBDialComponent, LBPuzzleLogic (pure logic)  (P4)
  Objectives/   ULBObjectiveChainData, ULBObjectiveSubsystem                     (P1)
  Save/         ULBSaveGame, FLBActorSaveRecord, FLBSaveIdRegistry, ULBSaveSubsystem, ULBSaveStateComponent, ALBCheckpoint (P1)
  AI/           ALBWarden, ALBWardenController, ULBWardenBrainComponent, ULBWardenTuningData, LBWardenLogic (pure), markers (P5)
  Storm/        ULBStormSubsystem, ULBStormSettings (DA_StormSettings), ALBStormZone, ALBStateLightGroup, LBStormLogic (pure), LBStormTypes (P14, section 14)
  Systems/      ULBUserSettings (MouseSensitivity, bInvertY, bHeadBob; config=GameUserSettings) (P3)
  Audio/        ULBAudioSubsystem, ULBAudioSettings (DA_Audio), ALBAudioZone, ALBAmbientEmitter, ULBWardenAudioComponent, LBAudioLogic (pure), LBAudioTypes (P16, section 16)
  Cinematics/   ULBCinematicSubsystem, ULBCinematicSettings (DA_Cinematics), ULBCinematicWidget, ULBCineAuthoringLibrary, LBCinematicLogic (pure), LBCinematicTypes (P17, section 17)
  UI/           ULBUISubsystem, ULBUIStyle (DA_UIStyle), ULBMenuWidgetBase and the C++ screens (main menu, pause, settings, credits, brightness, confirm), ULBKeyIconWidget, ULBHUDWidget, FLBGraphicsSettings, LBKeyBindings, LBLoadingScreen, LBUILogic (pure), LBUITypes (P18, section 18)
  Systems/      ULBGameInstance (gamma at startup, the loading screen's hand-back), ULBUserSettings additions (P18)
Source/LastBellTests/   (Editor target only) unit tests, MicroSlice, RouteBot.*, WalkPath.*, PlayerFeel.*, UI.*, test helpers (bUseUnity false since P18)
```
Runtime dependencies are Core, CoreUObject, Engine, InputCore, EnhancedInput, GameplayTags, UMG, DeveloperSettings (P2) and PhysicsCore (P3, footstep surfaces). `UnrealEd` is used only by `LastBellTests`. AIModule, NavigationSystem and GameplayTasks were added in Phase 5 (no State Tree modules, D-037); Slate, SlateCore, Niagara and the level-sequence modules came with Phases 15 and 17, and MoviePlayer and MediaAssets with Phase 18.
There was **no custom GameInstance** until Phase 18, because GameInstance subsystems don't need one; `ULBGameInstance` (D-133) exists only to apply the saved gamma at startup and to take the loading screen back after a map has loaded. There's no static helper library until a real shared helper exists.

## 3. Framework
| Class | Base | Responsibility | Not responsible for |
|---|---|---|---|
| `ALBGameMode` | `AGameModeBase` | Sets default classes and holds the objective chain asset property. Spawns the player at the pending checkpoint transform (overrides `ChoosePlayerStart` and the spawn transform). On player death, calls `SaveSubsystem.LoadLastCheckpoint()` | Progression logic |
| `ALBPlayerController` | `APlayerController` | Adds Input Mapping Contexts, creates the HUD widget from a class property. `bMenuMode` / `SetMenuMode()` switches to UI-only input with the cursor (menus; the ending no longer uses it, D-117); it's only applied when menu mode is on. `SetHUDHidden(bool)` (P17) collapses or restores the HUD for cinematics. P18: binds `PauseAction` (`IA_Pause`) to `ULBUISubsystem::HandleBack`, forwards `SetMenuMode` to the UI subsystem, and pushes the main menu on a menu map (section 18) | Gameplay rules |
| `ULBWorldStateSubsystem` | `UGameInstanceSubsystem` | Owns the canonical `FGameplayTagContainer` of `State.*` tags. API: `AddState`, `RemoveState`, `HasState`, `ResetState()`, `ReplaceState(Container)`. Delegates: `OnStateChanged(Tag, bAdded)` per tag and `OnStateReplaced` once after a reset or replace. Per-tag events are suppressed during bulk operations | Deciding *why* states change |

**Game flow (P2, `ULBSaveSubsystem`):** `StartNewGame()`, `ContinueGame()`, `CompleteGame()` (deletes the save and opens the menu) and `ReturnToMainMenu()` (keeps the save). Maps come from `ULBGameSettings`. Every travel sets `bTravelPending`, which blocks re-entry and checkpoint saves until the next world initialises. The target map is validated before any destructive step. Invariant: New Game and Continue always overwrite the in-memory WorldState and records, so returning to the menu doesn't need to clear them.

**Lifecycle rule:** New Game calls `ResetState()` **before** opening the map. Continue and death reload call `ReplaceState(SavedState)` **before** opening the map. WorldState is never merged with a save.

## 4. Player
`ALBCharacter : ACharacter` has a first-person `UCameraComponent` on the capsule and **no full-body mesh**; arms or hands are deferred until there's a reason for them. From Phase 5 it carries a `UAIPerceptionStimuliSourceComponent` so the Warden can see it.
Components:
- `ULBInteractorComponent` (P1) does a camera-forward sphere trace on a dedicated `Interaction` trace channel. It runs **from a timer at about 10 Hz**, not Tick, plus on input. It tracks the focused `ULBInteractableComponent` and broadcasts `OnFocusChanged(Component, PromptText)` for the HUD.
- **Tuning:** every feel value (speeds, acceleration, crouch height, head bob, sprint FOV, landing dip, stride and loudness per gait, candle, inspection) lives in `ULBPlayerTuningData` (`DA_PlayerTuning`, assigned on `BP_LBCharacter`), with a CDO fallback. The gait (`ELBGait`: Idle, Walk, Sprint, Crouch) is computed once per frame; walk, sprint and crouch speeds are applied when the state changes.
- `ULBCameraFeelComponent` (P3) handles the crouch eye blend, a subtle vertical bob (`bHeadBob` setting), the sprint FOV ease and the landing dip. There's **no roll and no shake**.
- `ULBFootstepComponent` (P3) fires steps by distance per gait, looks up the surface sound in `DT_Footsteps` (sounds come in Phase 16), and broadcasts `OnFootstep(Loudness, Location, Surface)`. In Phase 5 this component calls `ReportNoiseEvent` itself.
- `ULBCandleComponent` (P3, D-029) is the handheld candle: a warm point light with flicker; it gutters while sprinting; snuff and relight with a delay; `IsLit()` feeds Warden sight in Phase 5; a held placeholder mesh sways with look input.
- `ULBInspectionComponent` (P3, D-030) holds an item in front of the camera, rotates it, and restores it on close. Kept items grant through their interactable. `CancelInspect` (death, EndPlay, destroyed item) always cleans up and grants nothing.
- **Stamina:** none (D-031). Sprint is unlimited but loud.

Input uses Enhanced Input. Phase 1 has `IA_Move`, `IA_Look` and `IA_Interact` in `IMC_LB_Gameplay`. Phase 3 adds `IA_Sprint` (hold), `IA_Crouch` (hold), `IA_Candle`, plus `IA_InspectRotate` and `IA_InspectExit` in `IMC_LB_Inspect`. The inspect context is pushed by `ALBPlayerController` during inspection. `IA_Pause` (Escape, `trigger_when_paused`) was added in Phase 18 (section 18), and `IMC_LB_Gameplay` carries player-mappable names for rebinding. Sensitivity and invert-Y (`ULBUserSettings`) are applied in the character's look handler.

## 5. Interaction
There is a single path, **`ULBInteractableComponent`**. Adding it to any actor makes that actor interactable, and it's the only thing the player knows about.
- Properties: `PromptText`, `DeniedPromptText` (shown when focused but not usable, P2; a used single-use component shows no prompt and ignores presses, `IsConsumed`, D-084), `bEnabled`, `RequiredStateTags` (all must be present), `GrantedStateTags` (added on interact, via `AddStates`), `bSingleUse`, `ConsumedStateTag` (persists single use as a tag), `bInspectOnInteract` (P3: interacting opens inspection; the grant happens on close if the inspectable is kept).
- `ULBInspectableComponent` (P3): `DisplayName`, `BodyText`, `bKeepOnClose`, `InitialInspectRotation`. The interactable's grant is the single grant path.
- API: `CanInteract(Instigator)` (BlueprintNativeEvent) and `Interact(Instigator)`.
- Delegates: `OnInteracted`, `OnInteractDenied`, `OnFocusBegin`, `OnFocusEnd`.

A door, lever, note or ritual mechanism is a Blueprint actor built from a mesh, this component and its own timeline.
Not built: an inventory, `Interaction.Type.*` tags (deferred until a second kind of interaction exists), or a use-item-on-object matrix. Keys are `State.Item.*` tags checked through `RequiredStateTags`.

### Puzzles (P4, `Source/LastBell/Puzzles/`)
Puzzle progress is tags, so it is saved at checkpoints with no per-puzzle save code. Everything below is derived from the tags on BeginPlay, so a mid-puzzle save or load just works.
- **Derived single-use availability.** A single-use `ULBInteractableComponent` with a valid `ConsumedStateTag` is available if and only if that tag is absent. Using it no longer sets `bEnabled=false`; `bEnabled` stays the designer/Blueprint "locked" switch. Removing the consumed tag (a puzzle reset) makes it usable again with no Blueprint work. Single-use without a consumed tag still disables itself and warns on BeginPlay. A Blueprint that sets `bEnabled=false` from a tag at BeginPlay (doors, levers) is fine as long as the tag is never removed; a reversible Blueprint must not do that.
- **`ULBSequencePuzzleComponent`** (`Steps`, `SolvedTags`; `OnStepAccepted(Index, Step)`, `OnPuzzleFailed(WrongStep)`, `OnPuzzleSolved`). Listens to WorldState. Progress is the longest present prefix of `Steps`. A step added in order is accepted. A step added out of order removes every step tag (`RemoveStates`, on the next tick, never inside the broadcast) and fires `OnPuzzleFailed`. The last step adds `SolvedTags`, fires `OnPuzzleSolved` and stops listening. On BeginPlay and `OnStateReplaced`, step tags that are not a valid prefix are reset silently. If all `SolvedTags` are already present on BeginPlay the component is inert. No delegates fire for state that was present at BeginPlay, so Blueprints snap their visuals from the tags. The pure logic is `FLBSequenceLogic`.
- **`ULBDialComponent`** (`PositionTags`, `InitialIndex`, `bLocked`; `CycleNext()`, `GetCurrentIndex()`, `OnDialChanged(NewIndex)`). One tag per position, exactly one present. BeginPlay adds `PositionTags[InitialIndex]` if none is present and removes all but the lowest index if several are. `CycleNext` removes the current tag and adds the next, wrapping. If the owner has a `ULBInteractableComponent`, the dial binds its `OnInteracted`, so the interactable stays unaware of puzzles and keeps its normal gating. A combination puzzle needs no controller: the target interactable's `RequiredStateTags` lists the wanted position tags. The pure logic is `FLBDialLogic`.
- `ULBWorldStateSubsystem::RemoveStates(Container)` removes all tags first, then broadcasts `OnStateChanged(Tag, false)` once per tag that was present (mirrors `AddStates`).

## 6. Objectives
- `ULBObjectiveChainData : UPrimaryDataAsset` holds an **ordered array** of `FLBObjective { FGameplayTag Id; FText Text; FGameplayTagContainer CompletionStateTags; }`. There's one chain for the game and a test chain for the micro slice. It's assigned on `ALBGameMode`.
- `ULBObjectiveSubsystem : UWorldSubsystem` **derives** the active objective: it's the first entry whose completion tags aren't all present. It recomputes on `OnStateChanged`, and only once on `OnStateReplaced`. It broadcasts `OnObjectiveChanged(Index, Text)` only when the active objective changes.
- No separate objective save data is needed. Reordering the chain after saves exist means bumping `SaveVersion`.

Not built: branching quests, a quest log or a quest graph.

## 7. Save and checkpoints
**Rule 1: progress is tags.** Doors unlocked or opened, levers, notes, items, rituals and the Warden stage are all `State.*` tags. (Reached checkpoints are the one exception: they are a `TSet<FName>` in the save, because tag names can't be created at runtime; see D-021.) Saveable actors are **never destroyed**. A consumed actor hides and disables itself when its tag is present.
**Rule 2: few actor records.** Only state that can't be expressed as a tag, such as a statue's rotation angle, uses a record.

- `FLBActorSaveRecord` is a fixed struct and part of the save-version contract: `bool bState; float Value; int32 Index;`.
- `ULBSaveStateComponent` has a **hand-authored `FName SaveId`** (required) and an `OnRestore(Record)` event. A Blueprint provides the record it writes. On BeginPlay it **pulls** its own record from the save subsystem when a restore is pending, so there's no ordering race. It registers its SaveId, and a **duplicate SaveId logs an error** and fails an automation check. FName IDs survive duplication and Level Instances once they're validated, and there will be fewer than about 50 such actors.
- `ULBSaveGame : USaveGame` stores `SaveVersion` (a constant), `CheckpointId`, `CheckpointTransform`, `MapName`, `ReachedCheckpoints`, `WorldState`, `TMap<FName, FLBActorSaveRecord> ActorRecords` and `PlayTimeSeconds`.
- `ULBSaveSubsystem : UGameInstanceSubsystem` provides `NewGame(Map)`, `SaveCheckpoint(Id, Transform)`, `LoadLastCheckpoint()`, `HasValidSave()` and `DeleteSave()`. There's one slot, `LB_Slot0`. Loading always reads from disk. Settings go in `GameUserSettings`, not the save.
- `ALBCheckpoint` is a trigger box with a `CheckpointId` and a spawn arrow. It fires once; its id is added to the save's `ReachedCheckpoints` set. It **refuses to save while the Warden is in Chase or Attack**, which is a Phase 5 hook.
- **Restore flow:**
  1. Read the slot.
  2. `ReplaceState`.
  3. Set the pending restore (the records and the checkpoint transform).
  4. `OpenLevel`.
  5. Each actor's BeginPlay reads its tags and records and **snaps instantly** to the final state, with no timelines or sounds.
  6. The GameMode spawns the player at the checkpoint.
  7. Objectives recompute once.
  8. The pending restore is cleared one tick after world begin play.
- **Slot-file integrity (P4-004, D-036):** the slot file is the serialized save plus a 12-byte footer (magic 'LBSV', payload length, CRC32), written via EncodeSave and checked by DecodeSave BEFORE the engine parser runs. A truncated, damaged or footer-less file is treated as no save, with a warning, and never crashes; the engine parser crashed on truncated files.
- **Death** is just `LoadLastCheckpoint()`. **New Game** is `DeleteSave`, then `ResetState`, then `OpenLevel`. A corrupt save or a `SaveVersion` mismatch is treated as no save: it's logged and Continue is hidden.
- **Not saved:** the Warden (rebuilt from stage tags and respawned at a designer point for each checkpoint), transient AI state and physics props.

Not built: multiple slots, free saving or whole-world serialization.

## 8. Warden AI (Phase 5, `Source/LastBell/AI/`, D-037)
The brain is a **C++ state machine**, not a State Tree (D-037). The decisions are pure and unit tested; the component only gathers facts and acts.

**Classes**
- `ALBWarden : ACharacter`: collision capsule radius 42, half height 110 (D-038: it must fit the 104 x 230 cm doorways; the taller visual body lives in `BP_Warden`: `SK_Warden` from `/Game/LastBell/Characters/Warden/`, D-091, on `CharacterMesh0` at yaw 0, Z −110, `NoCollision`, animated by `ABP_Warden` since Phase 13, see "Warden animation" below; `OnlyTickMontagesWhenNotRendered`, update-rate optimisation on). `TellLight` (no shadows, 5000 unitless, radius 700) sits about 40 cm in front of the mask, a child of `PlaceholderBody` at (110, 0, 235); it shows during the attack windup. The mask glows red through a dynamic instance of the slot `M_Warden_BellMetal` (`TellGlow`: 0.25 while chasing, 1 in the windup, otherwise 0), set from `PlayStateFeedback`, `ShowWindupTell` and `EndWindupTell` (D-092). Socket `mask` on bone `head` is the catch camera's look target (`LBCatchCamera::ResolveLookTarget`; without it, the actor location plus a fallback height). Capsule size and eye height come from the tuning asset. No mesh in C++. It starts hidden and without collision (dormant presentation) and is placed once in the persistent level. **Never saved** (D-012): it is rebuilt from the stage tags.
- `ALBWardenController : AAIController`: `UAIPerceptionComponent` with Sight and Hearing (enemies, neutrals and friendlies all detected, because the player is neutral), plus `ULBWardenBrainComponent`. It forwards `OnTargetPerceptionUpdated` and `OnMoveCompleted` to the brain and holds no decision logic. The sight sense is configured for the largest effective radius (stage radius x candle multiplier) and narrowed per target by the brain.
- `ULBWardenBrainComponent` lives on the **controller**: it already owns perception and path following, and the checkpoint rule finds it through `UWorld::GetControllerIterator()`, so there is no manager actor and no registry.
- `ULBWardenTuningData` (`DA_WardenTuning`): every number (see the file; defaults are the Phase 5 starting values and the fallback when no asset is assigned).
- Pure logic in `LBWardenLogic.h/.cpp` (`LBWardenLogic::Evaluate`, `HighestStage`, `CapsForStage`, `EffectiveSightRadius`, `SelectSpawnIndex`, `FLBSightConfirm`, `FLBStuckDetector`, `FLBSearchPlan`).

**States** (`ELBWardenState`): Dormant, Patrol, Investigate, Suspicious (stop and look around), Search, Chase, Attack, Return. Each has Enter/Tick/Exit in the brain. `Patrol` is also "hold the post" below stage 4 or when the spawn's route has no points (`IsHoldingPost()`).

**Stage gating** (highest present `State.Warden.Stage.N` tag, re-read on `OnStateChanged` and `OnStateReplaced`):
| Stage | Allowed |
|---|---|
| 1-2 | Dormant: hidden, no collision, ignores perception |
| 3 | Patrol (holding the post), Investigate, Suspicious, Return, Attack |
| 4 | + Patrol route, Search |
| 5 | + Chase |
| 6 | Dormant again (P17, D-116): the finale is scripted, so only the sequence's figure exists |
A state that a lowered stage forbids (a reload) is left through Return. Any active stage: the player seen within `AttackRange` with line of sight and the attack off cooldown gives Attack.

**Transitions** (priority order in `Evaluate`): stage gate; Attack resolution (after `AttackWindupSeconds` the range and line of sight are re-checked: still valid then `Kill()` and Return, otherwise Chase, or Investigate when chase is not allowed; a resolved attack starts `AttackCooldownSeconds`); attack start; confirmed sight (Chase at stage 5+, otherwise Investigate; an unreachable player gives Search); a loud enough noise (Investigate, re-targeted by newer noises; Chase only updates the last-known location); then per state: Investigate arrives, Suspicious `SuspiciousSeconds`, then Search (stage 4+) or Return; Search ends when its points are visited or `SearchDurationSeconds` passes, then Return; Chase becomes Search after `LastKnownMemorySeconds` without sight; Return arrives, then Patrol.

**Perception only, no omniscience.** Sight is polled from the perception component's stimulus (refreshed location) and accepted only inside the effective radius: stage radius (1500 / 2000 / 2500) times `CandleLitSightMultiplier` (1.25) while the target's candle is lit, with `LoseSightExtraRadius` hysteresis. It must be continuous for `SightConfirmTime` (0.6 s, which is also the audible-tell lead) before it counts. After sight is lost only the remembered last-known location is used (`GetLastKnownLocation()`); chase goals are locations, never `MoveToActor`. Attack range and line of sight use the Warden's own body and eyes.

**Noise sources** (`UAISense_Hearing::ReportNoiseEvent`, tags in `AI/LBNoiseTags.h`): `ULBFootstepComponent` per step (loudness by gait, capped by `ULBPlayerTuningData::NoiseMaxRange`) and on landing; `ULBInteractableComponent::NoiseLoudness` (default 0 = silent) on a successful interaction, with the interactable's actor as the instigator. The engine scales hearing range by loudness (walk 0.3 is heard at 750 cm, sprint 0.8 at 2000 cm); `HearingLoudnessThreshold` drops very quiet noises.

**Movement.** `AAIController::MoveTo` with `FAIMoveRequest` (partial paths allowed); completion is matched to the request id. A partial or failed path (player off the navmesh) goes to the closest reachable point (partial path end, else a nav projection within `UnreachableFallbackRadius`), then Search, and the player counts as unreachable for `UnreachableRecheckSeconds`. **Stuck:** no progress of `StuckMinProgress` within `StuckSeconds` (or a blocked move) re-paths once; a second failure gives the target up (next patrol or search point; Investigate and Return count as arrived; Chase counts as unreachable). Travelling `StuckForgiveDistance` forgives a failure.

**Markers** (place on the floor): `ALBWardenSpawnPoint` (`MinStage`, `RouteId`), `ALBPatrolPoint` (`RouteId`, `Order`, `WaitSeconds`), `ALBSearchPoint`. The spawn with the highest `MinStage` not above the stage is used. A dormant Warden appears only when the player's view (a cone wider than the FOV, with line of sight) cannot see the spawn point; a stage change that picks a new spawn teleports only when neither the Warden nor the destination is in view, otherwise the Warden walks there (Return). Search uses up to `SearchPointCount` search points within `SearchPointRadius` of the last-known location, nearest unvisited first, with a pause at each; with none in range it uses random reachable points (a nav query, not EQS).

**Checkpoints (D-019).** `ALBCheckpoint::CanSaveNow()` is false while any `ALBWardenController`'s brain is in Chase or Attack. A refused checkpoint retries every 0.5 s while the player is still inside the trigger and saves once the chase ends.

**Player side.** `ALBCharacter` carries a `UAIPerceptionStimuliSourceComponent`, registered for Sight in BeginPlay (the component's own sense list is protected, so it is registered explicitly).

**Blueprint hooks.** `OnStateChanged(OldState, NewState)`, `OnPlayerSpotted()` (first sight, before the confirm time: the early audio tell, measured 0.58 s before Chase), `OnPlayerLost()`, `OnAttackWindup(WindupSeconds)` (play the tell), `GetState()`, `GetLastKnownLocation()`, `HasLastKnownLocation()`, `GetStage()`, `IsChasingOrAttacking()`, `IsHoldingPost()`.

**Debug.** `lb.Warden.Debug 1` (non-shipping) draws the state name, stage and sight timer above the head, the sight cone (unlit solid, candle-lit orange), the last-known location, the current move target and the last noise. State changes log at Log verbosity in `LogLBWarden`; the Visual Logger records transitions, noises and stuck events. No Behavior Trees, EQS, Smart Objects or Mass AI.

**Perception details (P5-004 fixes, D-039).** The controller does not tick, so the brain copies the pawn yaw into the control rotation every tick; without this the sight cone stayed on world +X. The sight origin is pulled back by `SightCloseRangeBackOffset` (150 cm) so a player right in front, below eye level, is inside the 3D cone (there was a blind spot at attack range). At stages 3–4, Suspicious no longer re-enters Investigate on sight (hysteresis); at stage 5+ sight still gives Chase.

**Switch.** `lb.Warden.Enabled 0` (and BlueprintCallable `SetWardenSystemEnabled`) forces every brain Dormant and hidden; completability tests (RouteBot, WalkPath) run with it off.

**Known limitation.** A partial patrol path counts as arrived, so a broken route truncates silently. `Warden.MonasteryReachability` guards against this by checking every patrol and spawn segment is a complete nav path.
**Tests.** `LastBell.Warden.*` (pure logic: stage gating, the full transition table plus an exhaustive invariant sweep, attack windup, sight confirm timing, candle multiplier, search point selection, stuck detector, spawn selection, tuning defaults). Functional: `LastBell.Functional.Warden.*` (33 tests since Phase 13, in `L_Test_Warden` and `L_Monastery`, including animation and apparition tests: gating, sight, candle, hearing, lose target, unreachable, stuck, chase speed, catch and escape, checkpoint refusal, repeated chases, flip-flop, stage relocation, reachability).

### Warden animation (Phase 13, D-093, `Docs/plans/P13_WARDEN_ANIMATION.md`)
- **Clips.** Mixamo motion capture retargeted onto `SK_Warden`: `AN_Warden_*` in `/Game/LastBell/Characters/Warden/Anims/`.
  - **The 12 Mixamo clips are local only** (git-ignored, D-095, because the repo is public). The blend spaces, montages, `ABP_Warden`, `DA_WardenAnimSet` and the owner's own `AN_Warden_Idle`/`Walk`/`DoorwayStoop` are committed.
  - A fresh clone therefore has an unanimated Warden, and the clip-dependent tests fail there. Copy the clips from the owner's private backup (`ExternalAssets/Incoming/mixamo/_p13_local_backup/Anims/`).
  - The retarget source, the Y Bot, its raw clips, the IK Rigs and `RTG_LB_YBot_To_Warden`, lives in `Retarget/`. That folder is **local only**: git-ignored and never cooked (R-55, D-094).
  - It is rebuilt from the raw FBX with `Tools/warden/p13_import.py`, `p13_reimport_ybot.py` and `p13_retarget.py`.
- **`ULBWardenAnimInstance`** (`AI/LBWardenAnimInstance`), the parent of `ABP_Warden`. In `NativeUpdateAnimation` it computes:
  - `GroundSpeed`: from `CharacterMovement` velocity, or from the location delta for a non-character such as the apparition;
  - the stoop target, from `ULBWardenStoopSubsystem`;
  - foot traces, giving bone-space deltas for two Two Bone IK nodes and a pelvis drop;
  - `PhysicsAlpha`: 1 within `PhysicsMaxDistance` of the camera;
  - turn-on-the-spot detection, from a yaw history, which plays `TurnLeft90` or `TurnRight90`.

  The easing runs in `NativeThreadSafeUpdateAnimation`. BlueprintCallable: `PlayAttack`, `PlayLookAround`, `HoldCatchPose`. Pure helpers live in `LBWardenAnim` (stoop, easing, turn decision, foot and pelvis maths, attack play rate). Debug: `lb.Warden.AnimDebug 1`.
- **`ULBWardenAnimSet`** (`DA_WardenAnimSet`): the montages (Attack, TurnLeft90, TurnRight90, LookAround) and every animation number (turn trigger and cooldown, stoop ease, foot trace and IK speed, pelvis limits, physics distance, attack timing).
  - `AttackPlayRate` 1.7778 and `AttackHitTime` 1.0667 are **stored values**, set at P13-4 so the montage's hit lands at the end of the 0.6 s `AttackWindupSeconds`. If the windup changes, recompute `AttackPlayRate` (`LBWardenAnim::AttackPlayRate(HitTime, Windup)`, a tested helper that production code doesn't call), or the lunge desyncs (QA C2).
- **`ABP_Warden` graph:**
  1. `BS_Warden_Locomotion` and `BS_Warden_Stoop`, blended by `StoopAlpha`;
  2. Slot `DefaultSlot`;
  3. pelvis offset;
  4. two Two Bone IK nodes;
  5. `RigidBody` (robe and chain bodies of `SK_Warden_PhysicsAsset`, LOD threshold 1), weighted by `PhysicsAlpha`.

  A blend space whose samples are set by script needs one open-and-save in the Blend Space editor, because `ResampleData` runs only there (`MCP_NOTES.md`).
- **Stooping.** `ALBWardenStoopZone` boxes (`StoopAmount` 0–1) are placed at the low doors and stair ends of L_Monastery (`SZ_*`, 12) and registered with `ULBWardenStoopSubsystem`, a world subsystem. The anim instance queries `GetStoopAmount(Location)`, with no ceiling traces.
- **`BP_Warden` hooks:** `PlayAttackAnim` (in the windup), `UpdateAnimState` (Search sets look-around; Dormant stops the montages), `CheckSearchPause` (0.25 s timer: still for 0.5 s in Search plays `PlayLookAround`), and `HandlePlayerCaught` (stop moving, `HoldCatchPose`).
- **Catch camera.** `ALBCharacter::Kill(AActor* Killer)`:
  - with a Warden killer, the view turns to its mask over `CatchLookSeconds`, holds for `CatchHoldSeconds` and fades over `CatchFadeSeconds` (all in `ULBPlayerTuningData`); then the normal death and reload follow;
  - without a killer (pits), death stays immediate;
  - the brain broadcasts `OnPlayerCaught` and passes the Warden.
- **Cost (P13-8):** about 0.2 ms on the game thread for the animation. The graph and physics run on worker threads (`a.ParallelAnimUpdate`).

## 9. Gameplay Tags
- **Native** (referenced from C++): `State.Warden.Stage.1..6`, and `AI.Stimulus.*` from Phase 5.
- **Ini** (`Config/Tags/LBGameplayTags.ini`, edited as text **only while the editor is closed**, D-024): `State.Ritual.1..3`, `State.Door.<Name>.Open`, `State.Item.<Name>`, `State.Event.<Name>`, `State.Test.*`, `Objective.<Area>.<Name>`.
- Each tag has exactly one source. It's never declared both natively and in ini.

## 10. Blueprint layer
These live in `Content/LastBell/Blueprints/`:
- `BP_LBCharacter`, `BP_LBPlayerController` and `BP_LBGameMode` are data-only children that configure the C++ classes.
- `Interactables/` contains:
  - `BP_Door_Base`: rotates, locks via `RequiredStateTags`, stores its open state as a tag and snaps instantly on restore.
  - `BP_Lever`, `BP_RitualMechanism`, `BP_TagInteractable` (pickups, candles, bell), `BP_TagTrigger`, `BP_TagVisibility`, `BP_KillVolume`.
  - Warden stand-ins: `ALBWardenApparition` / `BP_WardenApparition` (`AI/LBWardenApparition`, logic in `LBApparitionLogic`, D-092; replaced the Phase 2 `BP_WardenSilhouette`). A one-shot scripted appearance, not the AI: a world-state tag starts it, and at each station it waits until the player looks, faces them, fades in (dithered, parameter `Fade` on every slot), holds and fades out; it never repeats after a reload. Placed as `Apparition_Courtyard` and `Apparition_Chapel`. Phase 13: a station can carry a `WalkPath` (`WalkSpeed` 110), and with `bUseSkeletalFigure` the figure is the `Figure` skeletal component running `ABP_Warden`. The chapel walks from the altar rail into the sacristy; the courtyard stays a static `Body`. `Figure` ticks only while rendered (`OnlyTickPoseWhenRendered`), so the hidden apparition costs nothing (P13-8). The Phase 2 `BP_WardenPlaceholderKill`, unused since the AI pawn arrived, was removed at the end of Phase 12 with its `M_LB_Silhouette` material.
  - All of these share the pattern: snap to state at BeginPlay, bind `OnStateChanged`, unbind at EndPlay. A shared base (`ALBTagReactiveActor`) was considered and deferred (D-032).
  - **Art children (D-071, D-076, D-081; Phases 8–10).** An area's art lives in child Blueprints: each child sets the art mesh, the collision and its per-instance values in its construction script, and the gameplay logic stays in the parent.
    - Doors: `BP_Door_Base_Dungeon` (chapel main, sacristy, `Door_Tower`, `Door_Shortcut`).
    - Mechanisms: `BP_RitualMechanism_ChapelBells`, `_CryptWinch` and `_TowerCapstan`.
    - Others: `BP_TagInteractable_ChapelKey`, `_CryptCrank` and `_GreatBell`; `BP_TagVisibility_CryptGate` and `_CryptRubble`; `BP_DialLever_Crypt`; `BP_StainedGlassClue_Saints`; `BP_Inscription_Cloister`; `BP_SmallBell_Cloister`.
    - The graph DSL can't call a parent's construction script, so most children copy the parent's body. If a parent's construction script changes, update its children (R-40 lists them).
    - Placed instances don't pick up template edits; per-instance differences go in a child (`Tools/mcp/MCP_NOTES.md`).
- `Puzzles/` has one Blueprint per puzzle. It also holds the puzzle props and their art children: `BP_SmallBell` → `_Cloister`, `BP_DialLever` → `_Crypt`, `BP_StainedGlassClue` → `_Saints`, `BP_Inscription` (whose child `BP_Inscription_Cloister` is in `Interactables/`), and `BP_PuzzleCandle`. They communicate only through WorldState tags.
- Scripted beats live in small `BP_Event_*` actors, not in Level Blueprints.
- UI: the P1 `WBP_HUD` (prompt and objective) and the P2 `WBP_MainMenu` were replaced in Phase 18 by C++ widget trees (`ULBHUDWidget`, `ULBMainMenuWidget`; section 18, D-127, D-132); both, and `WBP_Inspect`, remain in the Content folder, unused, until the owner approves deleting them. `WBP_Ending` and `BP_EndingTrigger` (P2) were replaced in Phase 17 (D-117): the placed `EndingTrigger` was removed from `L_Monastery`, the cinematic widget is built in C++ (section 17), and both assets were deleted in P17-9. The pause and settings screens were never WBPs: they are C++ too (section 18).

**Blueprint rule:** a Blueprint never reaches into another Blueprint's internals. Communication goes through tags, components or delegates.

## 11. Maps
- `L_MainMenu` holds the menu (`BP_MenuGameMode` with `BP_MenuPlayerController`, whose `HUDWidgetClass` is the C++ `ULBMainMenuWidget` since P18; the menu video plays behind it). It's the game's default map. Packaged builds cook exactly `L_MainMenu` and `L_Monastery` (`MapsToCook`), never the test maps.
- `L_Monastery` is a **non-World-Partition** persistent level. In Phase 2 it's ONE level with Outliner folders per area (D-023). A split into per-area sublevels or level instances (D-013) is decided in Phase 6/7, once streaming needs can be measured.
- **Greybox layout:** `GREYBOX_SPEC.md`.
- **Art over the greybox (D-068, D-078):** from Phase 9, the greybox actors of an art-passed area keep their collision but are made not visible. This keeps navmesh, WalkPaths, RouteBot and the Warden routes on the tested collision.
  - The visible art is a NoCollision layer, apart from the exceptions listed in those decisions.
  - It is placed from generated layouts: `Docs/plans/p9_d1_layout.json` (crypt) and `p10_d1_layout.json` (cloister and bell tower), via `Tools/crypt/place_crypt.py` and `Tools/belltower/place_tower.py`.
- `L_Test_MicroSlice` is the Phase 1 proof map, kept afterwards as a regression map.

## 12. Rendering baseline (to be measured, not assumed)
Lumen GI and reflections, Virtual Shadow Maps, Nanite for static geometry, TSR (DLSS evaluated later), and volumetric fog with local fog volumes. Substrate stays **off**, which is the current setting. Lumen hardware ray tracing versus software will be decided by measurement in Phase 7. See `PERFORMANCE_BUDGET.md`.

## 13. Testing hooks
- **Automation tests** (`LastBell.*`):
  - WorldState reset, replace and delegates
  - Objective recompute
  - Save round-trip and version mismatch
  - Duplicate SaveId detection
  - Interaction gating
  - The UI (P18): `LastBell.UI.*` and `LastBell.Functional.UI.*` (section 18). Run a prefix with `Tools/build_and_test.ps1 -Filter <prefix>`; the full suite is the default.
- **Regression maps and functional tests:** `L_Test_MicroSlice` (`LastBell.Functional.MicroSlice`, `RouteBot.MicroSlice`). `L_Monastery` is covered by `RouteBot.Monastery`, which plays the whole objective chain through the real interactor, death and restore at CP_TowerBase, then the intro and the finale (played at 8× by `lb.Cine.Rate`, the credits skipped) and the travel to the menu (P17). **Rerun RouteBot after any gameplay or content change.**
- **Console commands** (development builds only): `lb.State.Add <Tag>`, `lb.State.Dump`, `lb.NewGame`, `lb.Checkpoint.Load`, `lb.Kill` (death path), `lb.Menu`, `lb.CompleteGame`, and later `lb.Warden.Debug`.

## 14. Storm and light (Phase 14, D-096…D-102)
Spec and results: `Docs/plans/P14_LIGHTING_STORM.md` (every "result" subsection), `P14_4_WIND_FIX.md` and `P14_5_APPLY.md`. Code: `Source/LastBell/Storm/`. The maths is in `LBStormLogic` (pure functions, unit tested); the subsystem and the actors gather the facts and apply the results. Types (`LBStormTypes.h`): `ELBFlashProfile` {Sheet, Double, Triple, Auto}, `ELBFlashReason` {Ambient, Scripted, WardenReveal, Apparition, Debug}, `ELBLightStateMode` {On, Dim, Off, Flicker}, `FLBStormStoryStep`, `FLBStormStrike`, `FLBLightStateRule`. No hard asset references: assets come through `DA_StormSettings` and its soft pointer to the MPC. Not in this phase: rain and other particles (Phase 15), thunder and audio (Phase 16).

**`ULBStormSubsystem` (D-096)**
- A `UTickableWorldSubsystem` for **Game and PIE worlds only** (`DoesSupportWorldType`). It ticks only while active (`IsTickable()`).
- **Settings:** `ULBStormSettings` (`UPrimaryDataAsset`) is `/Game/LastBell/Data/DA_StormSettings`, found through `ULBGameSettings::StormSettings` (a soft pointer; `Config/DefaultGame.ini`, `[/Script/LastBell.LBGameSettings]`, `StormSettings=/Game/LastBell/Data/DA_StormSettings.DA_StormSettings`). It holds every number and is read through its pointer **every frame**, so an edit in the Details panel or over MCP during PIE shows at once.
- **Activation:** `OnWorldBeginPlay` calls `RefreshLinkedLights()` (BlueprintCallable; a test that spawns a tagged moon later calls it again). The storm is active only when the level has an `ADirectionalLight` with the actor tag `LB_StormMoon` (several: one Warning, the first is used) **and** the settings load. A level without a tagged moon never loads the settings and never ticks or writes, so `L_MainMenu` and the test maps are unaffected. A moon without settings logs one Warning and stays inactive.
- **Each tick (every frame):** story intensity moves toward its target; wind strength and phase advance; due flashes start, running ones are evaluated (F is the maximum over the running flashes); the ambient timer runs; the lights are written (only while a flash runs, plus once when it ends); the MPC is written. The Warden reveal rule runs at `RevealCheckHz` (5 Hz) and the player's exposure is sampled every `ExposureSampleSeconds` (0.25 s) at the camera.
- **Intensity:** the target is the story intensity (below); the live value moves at `IntensityRatePerSecond` 0.02 (0.5 to 1.0 takes 25 s). BeginPlay, `OnStateReplaced` (a checkpoint load) and the debug overrides **snap** to the target.
- **Ambient schedule:** interval to the next flash uniform in [lerp(`MinIntervalLow` 30, `MinIntervalHigh` 6, I), lerp(`MaxIntervalLow` 60, `MaxIntervalHigh` 14, I)] s, where I is the live intensity; the first after BeginPlay waits × `FirstFlashScale` 0.5. Profile weights Sheet 0.5, Double 0.35, Triple 0.15. Brightness lerp(`BrightnessMin` 0.55, 1, random) × lerp(`BrightnessFloorLow` 0.7, 1, I). Direction: random azimuth 0–360°, elevation uniform `ElevationMin` 15 – `ElevationMax` 35°. `FRandomStream` seeded by `RandomSeed` (0 = from the time; tests use 1401). `bAmbientFlashes` turns the random flashes off.
- **Gap rule:** a flash of any source starts at least `MinGapSeconds` 2.5 after the previous one ends; a request inside the gap waits. The strikes of one scripted sequence follow their own `Spacing`, start to start: the gap applies only before the first. Ambient flashes are not scheduled while any flash is running, pending or waiting for a look.
- **`RequestFlash(Brightness, DelaySeconds, Reason, Profile = Auto)`** (BlueprintCallable) and `RequestFlashDirected(..., Direction)` queue a flash. Queries (BlueprintPure): `IsActive`, `GetStormIntensity`, `GetTargetIntensity`, `GetExposureAt(FVector)`, `GetPlayerExposure`, `GetLightningFlash`, `GetWindStrength`, `IsFlashBusy`.
- **`OnLightningFlash(float Brightness, ELBFlashReason Reason)`:** a dynamic multicast delegate broadcast when a flash starts (its first pulse). It was planned as the Phase 16 audio hook (thunder can treat the reasons differently); as built, Phase 16 binds `OnLightningStrike` instead (fired with every flash, carrying brightness, reason, direction and target; section 16 has the details).
- **`lb.Storm.Enabled 0`:** no flashes (pending, running and look waits are dropped), wind 0, F 0. The MPC is still written.

**Flash shapes and the preset**
- Each pulse has start s, peak p, attack A, hold H and decay τ. For u = t − s: v = 0 before the start, u/A in the attack, 1 in the hold, then exp(−(u − A − H)/τ). **F(t) = min(1, Brightness × max over pulses of p × v).** The flash ends at the last pulse's start + A + H + 5.3 τ (v < 0.005).

| Profile | Pulses (start, peak) | A / H / τ (s) |
|---|---|---|
| Sheet | (0, 1.0) | 0.08 / 0.10 / 0.25 |
| Double | (0, 0.55), (g, 1.0) | 0.03 / 0.04 / 0.12 |
| Triple | (0, 0.5), (g1, 1.0), (g1 + g2, 0.7) | 0.03 / 0.04 / 0.12 |

- The gaps g, g1, g2 are uniform in [`GapMin` 0.07, `GapMax` 0.16] s.
- **Flash output, preset B (strong) is the saved asset and the default in code (D-101).** A and C were shown in the P14-4 look session and are kept here for reference only; they are not in any asset:

| Field | A, subtle | **B, in use** | C, blinding |
|---|---|---|---|
| `FlashLux` (moon + lux) | 4 | **8** | 16 |
| `SpotFlashGain` / `FillFlashGain` / `SkyFlashGain` | 1.5 / 0.75 / 0.3 | **3 / 1.5 / 0.6** | 6 / 3 / 1.0 |
| `DomeFlashGain` / `DomeFlashAdd` | 3 / 0.03 | **6 / 0.05** | 10 / 0.08 |
| `GlassFlashGain` / `ShaftFlashGain` / `PoolFlashGain` | 1.2 / 1.5 / 1.2 | **2.5 / 3 / 2.5** | 4 / 5 / 4 |
| `RevealGain` / `RevealEmissive` | 4 / 2 | **4 / 3** | 4 / 4 |

- `FlashTint` (0.75, 0.82, 1, 1). R-59 fallback (not needed: no smear seen): `SkyFlashGain` 0.

**Linked lights.** Found by actor tag at BeginPlay, base intensity recorded, weak pointers (a light that disappears is skipped). Written only while a flash runs and once when it ends; `RefreshLinkedLights` restores the bases first. The sky light is handled as a `USkyLightComponent`. All 62 placed lights are Movable (`SetIntensity` does nothing on a Static light).

| Tag | Level actors | Intensity while F > 0 |
|---|---|---|
| `LB_StormMoon` | `DirectionalLight` (`DirectionalLight_1`) | base + `FlashLux` × F |
| `LB_StormMoonSpot` | `Light_Chapel_Moon_S1/S2/S3/_Roof`, `L_Crypt_Moon_G1/G2/G3`, `L_Tw_MoonSlit_F03/F07/F08` (10) | base × (1 + `SpotFlashGain` × F) |
| `LB_StormFill` | `L_Tw_BellFill` | base × (1 + `FillFlashGain` × F) |
| `LB_StormSky` | `SkyLight` | base × (1 + `SkyFlashGain` × F) |

`Moon_Fill` has no tag (it would light the interiors). The player candle is never touched (`ULBCandleComponent` rewrites its light every tick).

**Story intensity and scripted strikes.** The target is the `Intensity` of the **last** `StoryIntensity` step whose tag is present (exact match); with none, `DefaultIntensity` 0.55.

| Tag | Intensity | Scripted strike (delay s, count, spacing s) |
|---|---|---|
| `State.Event.CourtyardEntered` | 0.60 | 0.4 after the look, 2, 1.6, **look gate** |
| `State.Ritual.1` | 0.55 | 1.2, 1, – |
| `State.Event.CryptEntered` | 0.50 | – |
| `State.Ritual.2` | 0.65 | 1.2, 1, – |
| `State.Event.CloisterEntered` | 0.80 | – |
| `State.Ritual.3` | 0.90 | 1.2, 1, – |
| `State.Event.TowerTop` | 1.00 | 2.0, 3, 2.5 (profiles Double, Triple, Double) |
| `State.Event.Finale` | 1.00 | 0.3, 2, 0.8 |

- Strikes have brightness 1.0 and profile Double unless overridden. They fire **only when the tag is added** (`OnStateChanged`), never at BeginPlay or after `OnStateReplaced` (which clears the look waits), so a reload does not repeat them.
- **Look gate (arrival):** `LookTarget` (12500, 2000, 3800) (the tower top), `LookConeDegrees` 20, `LookTimeout` 90 s. A view-cone check only, with no trace. When the camera forward is within the cone, the strike starts after its delay, with the flash direction toward the target; if the player never looks within the timeout, nothing fires.
- The two arrays in `DA_StormSettings` were filled by hand over MCP (no tool calls a UFUNCTION); `FillPlanTagDefaults()` (CallInEditor) holds the same tables. Eight steps, six strikes.

**`MPC_LB_Storm`** (`/Game/LastBell/Materials/`; replaces the planned `MPC_LB_Wind`). The subsystem writes every parameter every frame; the asset defaults are 0 (`WindDirection` (0.87, 0.5, 0, 0), `FlashDirection` (0, 0, 1, 0), `FlashTint` (0.75, 0.82, 1, 1)). A missing name logs one Warning ("lacks one or more storm parameters"). While the subsystem is inactive, F is 0 and every flash term in the materials is exactly 1.

| Parameter | Value | Read by |
|---|---|---|
| `StormIntensity` | live intensity, 0–1 | no Phase 14 material (reserved) |
| `LightningFlash` | F, 0–1 | `MF_LB_StormFlash` (glass, shafts, pools), `M_LB_StormSky`, `M_LB_Decal_LightningReveal` |
| `WindStrength`, `WindPhase`, `WindDirection` | see Wind | `MF_LB_WindSway` |
| `PlayerExposure` | 0–1 at the camera | no material yet (Phase 15) |
| `DomeFlashGain`, `DomeFlashAdd` | copied from the settings | `M_LB_StormSky` |
| `GlassFlashGain` | copied | `M_LB_StainedGlass`, `_Translucent` |
| `ShaftFlashGain` | copied | `M_LB_LightShaft` |
| `PoolFlashGain` | copied | `M_LB_Decal_LightPool` |
| `RevealGain`, `RevealEmissive` | copied | `M_LB_Decal_LightningReveal` |
| `FlashDirection` | unit vector toward the bright patch in the clouds | `M_LB_StormSky` |
| `FlashTint` | colour of lightning | `M_LB_StormSky`, `M_LB_Decal_LightningReveal` |

**Wind (D-096, D-100, D-101).** I is the live intensity, t the game time.
- Base = lerp(`WindBaseLow` 0.2, `WindBaseHigh`, I). Gust = lerp(`GustLow` 0.15, `GustHigh`, I) × max(0, 2 × `FMath::PerlinNoise1D`(t × `GustFrequency`)). **`WindStrength` = clamp(Base + Gust, 0, 1).**
- `WindPhase` += dt × lerp(`PhaseSpeedLow` 1.2, `PhaseSpeedHigh`, `WindStrength`), wrapped at 100 × 2π (the material only uses whole multiples). `WindDirection` = the normalised `WindDirection` field, default (0.87, 0.5, 0) (the plan calls it wind from the west-south-west).
- **Owner-tuned values in the saved asset (P14-4, saved in P14-5a):** `PhaseSpeedHigh` **6.5**, `WindBaseHigh` **0.8**, `GustHigh` **0.5**, `GustFrequency` **0.2**. The code defaults are the plan's (2.4, 0.65, 0.4, 0.12); the asset overrides them.
- **`MF_LB_WindSway`** (`/Game/LastBell/Materials/Functions/`), a static bool `bFlutter` picks the mode. **Bend** (grass, weeds, ferns, shrubs): h = saturate(`PreSkinnedPosition`.z × S / `WindRefHeightCm`), where S is the instance's world Z scale, `Length(Transform(Instance → World, (0, 0, 1)))`, so `WindRefHeightCm` is a **world** height (D-100: `PreSkinnedPosition` is unscaled and the plants are placed 1 to 4.8× scaled). Pivot = the instance origin in world space; φ = `WindPhase` + dot(Pivot.xy, (0.0031, 0.0047)); s = 0.6 sin φ + 0.4 sin(2φ + 1.3); d = `WindDirection` × `WindStrength` × (0.55 + 0.45 s) × h² × `WindAmplitudeCm`; WPO = d + (0, 0, −0.25 |d| h). **Flutter** (ivy): a = saturate(`PreSkinnedPosition`.y / 20) (the wall side is at local Y 0); φ = 3 × `WindPhase` + dot(world position, (0.05, 0.07, 0.03)); WPO = `VertexNormalWS` × `WindStrength` × sin φ × a × `WindAmplitudeCm`.
- **Foliage masters:** `M_LB_Foliage` and `M_LB_FoliageMasked` have a static switch `bWind` (default false) feeding the function into WPO (`bFlutter` false in `M_LB_Foliage`, true in the masked master), scalars `WindAmplitudeCm` and `WindRefHeightCm` (group Wind), and a max WPO displacement of 40 cm and 6 cm.
- **MIs (`bWind` on, owner-tuned amplitudes, `WindRefHeightCm` in world cm):** `MI_Foliage_GrassMedium02` 38 / 60, `_NettlePlant` 24 / 45, `_WeedPlant02` 16 / 30, `_Fern02` 24 / 45, `_WildRooibos` 18 / 60, `_SearsiaLucida` 16 / 150; `MI_Ivy_Green` and `MI_Ivy_Dead` (flutter) 5. `MI_Foliage_Moss01` stays off. The dead tree stays static (its bark is on `M_LB_Surface`, D-060). Grass at 38 (+9.5 sag) sits just under the 40 cm cap, ivy 5 under 6.
- **WPO disable distance 4000** (`WorldPositionOffsetDisableDistance`) is set on the 249 foliage `StaticMeshActor`s (effective material is one of the nine foliage MIs: the `CLA_Garth*` plants, `PSA_Weed_*`, `Garden_Searsia_*` and 32 ivy cards) and the 312 PCG ISM components. **Regenerating a `PCGV_*` volume resets it: rerun `Tools/lighting/p14_wpo_distance.py --apply` after any PCG regeneration.**

**`ALBStormZone` and `GetExposureAt`.** An actor with a `UBoxComponent` (no collision, hidden in game, half extents in cm), `Exposure` 0–1 and `Priority`. It registers with the subsystem at BeginPlay. **Exposure at a point** is that of the highest-`Priority` zone containing it (`ContainsPoint` honours rotation and scale); on a tie the lowest `Exposure` wins; with no zone, `DefaultExposure` 1.0 (open sky). The player's `PlayerExposure` and the Warden reveal rule use it.

| Zone | Bounds X / Y / Z (cm) | Exposure | Priority |
|---|---|---|---|
| `SZN_Chapel` | 6000…9100 / −1550…860 / −40…2400 | 0.35 | 1 |
| `SZN_Crypt` | 6300…12000 / −2950…520 / −1200…−45 | 0 | 2 |
| `SZN_Passage` | 6040…9460 / 900…2600 / −40…1200 | 0.3 | 1 |
| `SZN_Cloister` | 9460…12040 / 500…3040 / −40…1500 | 0.6 | 1 |
| `SZN_Garth` | 10245…11460 / 1345…2260 / −40…1500 | 1.0 | 2 |
| `SZN_TowerShaft` | 11990…13010 / 1490…2510 / −40…2650 | 0.25 | 3 |
| `SZN_Belfry` | 11990…13010 / 1490…2510 / 2650…4800 | 0.85 | 3 |

**The Warden reveal rule (R-62).** Checked at 5 Hz by `LBStormLogic::ShouldReveal`. All of these must hold, and the visibility trace (`ECC_Visibility`, camera to head point, ignoring the pawn and the Warden) runs only when the cheap ones do:
- `bRevealEnabled` (the switch, default true) and intensity ≥ `RevealMinIntensity` 0.4;
- an `ALBWarden` exists and is not `IsDormantPresentation()`;
- the head point (Warden location + `WardenHeadOffsetZ` 140 on Z) is between `RevealMinDistance` 800 and `RevealMaxDistance` 4000 cm from the camera and within `RevealConeDegrees` 30 of the camera forward, with a clear trace;
- `GetExposureAt(Warden location)` ≥ `RevealMinExposure` 0.5 (only the cloister walk 0.6 and the garth 1.0 pass);
- `RevealCooldownSeconds` 30 since the last reveal, and no flash running, pending or waiting for a look.

The result is a `WardenReveal` flash, brightness `RevealBrightness` 1, profile Double, after a delay uniform in [`RevealDelayMin` 0.3, `RevealDelayMax` 0.9] s, its `FlashDirection` the camera-to-Warden direction flattened and raised `RevealRaiseDegrees` 20°. `lb.Storm.Debug` shows the first failing condition (Disabled, LowIntensity, NoWarden, Dormant, TooClose, TooFar, OutOfCone, Blocked, LowExposure, Cooldown, Busy).

**Apparitions: `bLightningOnHold`.** `FLBApparitionStation::bLightningOnHold` (default false). When a station enters Hold, `ALBWardenApparition` calls `RequestFlash(1.0, 0.15, Apparition, Double)` on the storm if it is active. Set in the level (placed instances only; `BP_WardenApparition` itself is never saved) on the one station of each of `Apparition_Courtyard` and `Apparition_Chapel`.

**`ALBStateLightGroup` (D-097, D-099).** Dims, kills or flickers a set of placed lights from the story tags.
- **Rules:** `Rules` in story order, **the last rule whose `RequiredTag` is present wins**; with none present: On at scale 1. Modes: On (1), Off (0), Dim (`IntensityScale`), Flicker (`IntensityScale` × (1 − `FlickerAmount` × (0.5 + 0.5 × Perlin(t × `FlickerSpeed` + seed))), seed from the light's name hash, so the lights do not flicker in step).
- **Apply:** base intensities are recorded at BeginPlay. BeginPlay and `OnStateReplaced` apply the rule **instantly** (a checkpoint load is right on the first frame). A live change through `OnStateChanged` fades over `FadeSeconds` 1.5: the straight blend times a gutter (`GutterNoise` = 0.6 + 0.4 × Perlin(t × 9)) weighted 4α(1 − α), so it neither starts nor ends with a pop. The actor ticks **only while fading or in Flicker**.
- **Lights:** placed `ALight` actors only. Never a Blueprint light, a puzzle candle's `FlameLight`, the Warden's `TellLight` or the player's candle. A light or glow actor listed in two groups logs a Warning at BeginPlay and fails the setup test.
- **`EmissiveActors`:** flame or glow meshes, hidden when the mode is Off (after the fade) and shown at once in any other mode.
- **`GlowActors` and `GlowParameter` ("Color"), D-099:** at BeginPlay every `UMeshComponent` slot of a glow actor whose material has that vector parameter gets a dynamic instance, and the actor is paired with the nearest light of the group (measured once). The slot value is base × clamp(current intensity ÷ base intensity, 0, 1), written whenever the group writes the light (instant, fade, flicker). So a lantern's glass dims, flickers and goes dark with its light. A glow actor with no slot or no light logs a Warning and is skipped.

| Group | Lights (glow / emissive actors) | Rule (tag → mode) |
|---|---|---|
| `SLG_Chapel_Altar` | `Light_Chapel_Altar_N`, `_S` | `State.Ritual.1` → Flicker 0.25 / 0.45 / 7 |
| `SLG_Chapel_Dais` | `Light_Chapel_Statue`, `Light_Chapel_DaisFill` | `State.Ritual.1` → Off |
| `SLG_Crypt_Torches` | `L_Crypt_Torch_T1/T2/T3` | `State.Ritual.2` → Flicker 0.6 / 0.45 / 9 |
| `SLG_Crypt_Niches` | the 5 `L_Crypt_Candle_Niche_*` (emissive: the 5 `CD_Candles_Niche_*_Flame`) | `State.Ritual.2` → Off |
| `SLG_Cloister_Bells` | `L_Cl_Bells` (glow `CLA_Lantern_Bells`) | `State.Event.CloisterEntered` → Flicker 0.85 / 0.3 / 5 |
| `SLG_Cloister_West` | `L_Cl_West` (glow `CLA_Lantern_West`) | `CloisterEntered` → Flicker 0.85 / 0.3 / 5; `State.Ritual.3` → Off |
| `SLG_Cloister_Entry` | `L_Cl_Entry` (glow `SHA_Lantern_Entry`) | `State.Ritual.3` → Off |
| `SLG_Tower_Landings` | `L_Tw_Land4/7/10` (glow `TWA_Lantern_Land4/7/10`) | `State.Ritual.3` → Flicker 0.9 / 0.2 / 4 |
| `SLG_Tower_Bell` | `L_Tw_Bell` (glow `TWA_Lantern_Bell`) | `State.Event.TowerTop` → Flicker 0.8 / 0.5 / 8 |

Flicker is (scale / amount / speed). Every critical-path viewpoint kept its readability floor after all five story changes (P14-5b), so the Dim 0.3 fallback was not used (R-61).

**Materials consuming the storm.** `MF_LB_StormFlash` (`/Game/LastBell/Materials/Functions/`): `Mul` = 1 + `Gain` × `LightningFlash` × `Response`. At F = 0 each edit below is neutral by construction (the sky was also compared by capture in P14-4).
- **Sky `M_LB_StormSky`** (`/Game/LastBell/Environments/Sky/`, a copy of the engine's `M_Sky_Panning_Clouds2`): emissive = original × (1 + `DomeFlashGain` × F × Hot) + `FlashTint` × F × Hot × `DomeFlashAdd`, with Hot = 0.3 + 0.7 × saturate(dot(−CameraVector, `FlashDirection`))⁶, so the bright patch moves from flash to flash. `MI_NightStormSky` is parented to it (done headless with the editor closed: never `set_parent` an MI that is on screen).
- **Glass:** `M_LB_StainedGlass` and `_Translucent` multiply the emissive by `MF_LB_StormFlash(GlassFlashGain, FlashResponse)`. `FlashResponse` is 0 on `MI_Glass_Clue_Saints` (the puzzle clue stays stable) and `MI_Glass_Lancet_B` (it faces the passage building); 1 on `MI_Glass_Lancet_A`, `_Broken` and `_East`.
- **Shafts and pools:** `M_LB_LightShaft` `Intensity` × `MF_LB_StormFlash(ShaftFlashGain, FlashResponse)` (`FlashResponse` 1 on `MI_LightShaft_Window/_Roof/_Crypt`); `M_LB_Decal_LightPool` emissive × `MF_LB_StormFlash(PoolFlashGain, 1)`.
- **Lightning-only chalk, `M_LB_Decal_LightningReveal`** (a copy of `M_LB_Decal_Chalk`): opacity = chalk alpha × `Opacity` 0.9 × saturate(F × `RevealGain`); emissive = chalk colour (0.82, 0.80, 0.75) × `FlashTint` × F × `RevealEmissive`; invisible at F = 0. Four MIs (`MI_Reveal_Sigil/_Tally/_Circle/_Drag`, existing chalk textures). **Atmosphere only: no puzzle information may depend on them.** Final placements (`DecalSize` is a half-extent: depth, vertical, horizontal):

| Actor | Location | Rotation | `DecalSize` | MI |
|---|---|---|---|---|
| `RV_Gate_Sigil` | (300, 500, 260) | (0, 180, 90) | (10, 110, 110) | Sigil |
| `RV_WellHouse_Tally` | (1350, −1775, **115**) | (0, −90, 90) | (10, 40, 60) | Tally |
| `RV_Chapel_Circle` | (**8150, −91**, 0.5) | (−90, 0, 0) | (10, 90, 90) | Circle |
| `RV_Garth_Drag` | (10750, 3000, 270) | (0, 90, 90) | (20, 30, 110) | Drag |
| `RV_Belfry_Tally` | (12200, 1540, 2850) | (0, −90, 90) | (15, 50, 50) | Tally |

Bold values are the owner's P14-4 changes (D-101). `RV_Garth_Drag` stays on the unlit walk wall and glows alone. From the `tw_belfry` pose the bell hides `RV_Belfry_Tally`; it shows once the player walks round the bell.

**Post-process structure (D-098, D-101, D-102).** Every volume uses a fixed exposure (min = max EV100). The area volumes override only that pair; the grade lives on the global volume only, so there is **no per-area shadow-saturation override** (`bOverride_ColorSaturationShadows` is false on all six; the stored 0.65 is left).

| Volume | EV100 | Priority | Blend (cm) | Bounds / notes |
|---|---|---|---|---|
| `PostProcess_Exposure` | 3, plus grade B | 0 | 100 | unbound |
| `PP_Outdoor_Night` | **1.40** (D-102; was 1.15) | 1 | 500 | to X 5500 |
| `PP_Crypt` | 0.2, histogram method, bloom override | 1 | 300 | as in Phase 9 |
| `PP_Cloister` | 0.65 | 1 | 300 | X 6040…12040, Y 900…3200, Z −40…4200 (shrunk: it used to cover the nave) |
| `PP_Chapel` (new) | **1.6** | 2 | 200 | X 6000…9100, Y −1550…860, Z −40…2400 |
| `PP_Tower` (new) | 0.65 | 3 | 200 | X 11990…13010, Y 1490…2510, Z −40…5000 |

Grade B (storm teal) on `PostProcess_Exposure`: `colorSaturation` (0.92, 0.95, 1.0, 0.85), `colorContrast` (1, 1, 1, 1.06), `colorGammaShadows` (0.97, 1.0, 1.06, 1), `colorGainHighlights` (1.04, 1.0, 0.94, 1), film grain 0.18, vignette 0.45. Exposure is judged on the wide views (mean luma) with a central-40 % floor on every view (`Tools/lighting/area_targets.py`); the tower (0.22) and the crypt (0.011) stay outside their mean targets by decision (D-102).

**Console and CVars** (non-shipping; commands in `Systems/LBConsoleCommands.cpp`, CVars in the subsystem). The commands warn and do nothing when the storm is not active in the world.
- `lb.Storm.Flash [brightness=1] [profile=-1]`: a flash now, reason Debug; profile −1 random, 0 sheet, 1 double, 2 triple.
- `lb.Storm.Intensity <0..1 | -1>`: overrides the story intensity (and snaps); −1 clears.
- `lb.Storm.Freeze <0..1 | -1>`: holds F at the value and pauses the ambient schedule and the reveal rule; −1 clears.
- `lb.Storm.Enabled` (default 1): 0 stops the storm as above. `lb.Storm.Debug` (default 0): 1 puts the intensity, target, seconds to the next ambient flash, wind, player exposure, pending and running flashes and the last reveal decision on screen.
- `lb.Warden.Enabled` is a global CVar; every performance reading starts with it at 0.

**The never-save rule.** `DA_StormSettings.DebugFreezeFlash` and `DebugIntensityOverride` do what the two commands do and are used for captures over MCP. **Never save the asset with either one other than −1** (`Monastery.StormSetup` fails on it). `M_LB_Surface` is never opened for writing or saved by storm work.

**Tests.** Unit (`Source/LastBellTests/Tests/LBStormTests.cpp`): `LastBell.Storm.Logic.StoryIntensity`, `.FlashEnvelope`, `.Schedule`, `.Wind`, `.Exposure`, `.RevealRule`, `.LightRules`, `.ScaleGlow`. Functional (`LBStormFunctionalTests.cpp`, PIE): `LastBell.Functional.Storm.FlashDrivesLightsAndMPC`, `.IntensityFollowsStory`, `.ScriptedStrikeOnTagOnly`, `.WardenRevealFlash`, `.StateLightGroupFollowsTags`, `.ApparitionHoldRequestsFlash`, `.StateLightGroupDrivesGlow`, `.Monastery.StormSetup` (one moon, 10 spots, 1 fill, 1 sky, 7 zones, 9 groups with valid lights and glow slots, settings with the debug fields at −1, 8 steps and 6 strikes, 2 apparitions with `bLightningOnHold`, the subsystem active with 7 zones).

**Tools** (`Tools/lighting/`, Windows `python -I`; MCP, editor open unless noted):
- `p14_lib.py`: shared helpers for the material tasks. `p14_f0_survey.py` and `p14_f0_tables.py`: the read-only F0 survey and its tables (`Docs/ArtTest/lighting/`).
- `p14_2a_before.py` records MI overrides; `p14_2a_sky_reparent.py` reparents `MI_NightStormSky` headless (editor closed); `p14_2b_wind.py` builds `MF_LB_WindSway` and the master inputs.
- `p14_3_level.py`: the storm's level work (`--apply [--only ...]`, `--check`; idempotent, never saves). `p14_5_apply.py`: the owner's P14-4 choices (`--apply [--only da,mis,map]`, `--check`; never saves). `p14_4_wind_fix.py`: the D-100 fix (`pre`, `fn`, `savefn`, `mis`, `savemis`, `check`).
- `p14_wpo_distance.py`: WPO disable distance 4000 (`--apply`, `--check [--rescan]`).
- `pie_pp.py`, `pie_proxy.py`, `area_targets.py`, `compare_sets.py`: look-session and exposure tools (see `Tools/mcp/MCP_NOTES.md`, "Lighting sessions"). `poses/p14_viewpoints.json` (16 poses) and `poses/p14_3_decals.json`.

## 15. Particles (Phase 15, D-103…D-107)
Spec and results: `Docs/plans/P15_PARTICLES.md` ("Results": F0, S1 rounds 1 and 2, P15-1…P15-10) and `P15_8_APPLY.md`; build records `Docs/ArtTest/fx/p15_5_build.md`, `p15_6_level.md`, `p15_8_apply.md`. Code: `Source/LastBell/Storm/` (`LBStormFXSubsystem`, `LBStormFXSettings`, `LBStormFXLogic`, `LBLightningBolt`, plus the `OnLightningStrike` part of `ULBStormSubsystem`).
- **Purpose:** draw the storm: a constant downpour that follows the camera and dies under roofs, splashes and ripples, branching bolts (sky bolts and scripted tower strikes), and flame, dust, mist, drip and cloth effects.
- **Boundaries:** the FX subsystem reads the storm and draws; it changes nothing in it. `OnLightningFlash` is untouched (it was the planned thunder hook; Phase 16 binds `OnLightningStrike` instead, fired with every flash and carrying brightness, reason, direction and target; see section 16). No thunder or audio (Phase 16), no gameplay, AI or save change, no change to `M_LB_Surface` (ripples are particles). No hard asset references: the assets come through soft pointers in `DA_StormFX`.

**Storm hooks (P15-1, D-105)**
- `FLBStormStrike::StrikeTargetTag` (FName). `FireStrike` resolves it once per strike index (the first actor with that tag, via `TActorIterator`, cached in a `TMap<int32, TWeakObjectPtr<AActor>>`; a tag that finds nothing logs one Warning per index). With a target, the flash direction points at it.
- `FLBLightningStrikeInfo` {`Brightness`, `Reason`, `Profile` (resolved, never Auto), `Direction`, `bHasTarget`, `TargetLocation`}. `OnLightningStrike` is broadcast in `StartDueFlashes` right after `OnLightningFlash`, for the same flash.
- Also added: `RequestFlashAtTarget(Brightness, Delay, Reason, Profile, Target)` (used by `lb.StormFX.Bolt 1`), `IsFlashRunning()`, and `ULBStormSettings::FXSettings` (a soft pointer to `DA_StormFX`, set by hand).
- **Strike target:** a `TargetPoint` labelled `FX_StrikeTarget_Tower`, actor tag `LB_StrikeTarget_Tower`, at (12530.8, 2000, 4844.8), 20 cm above the finial tip of `TWA_Roof` (bounds max Z 4824.8). `StrikeTargetTag` is set on two scripted strikes only: `State.Event.CourtyardEntered` (`ScriptedStrikes[0]`, 2 strikes) and `State.Event.TowerTop` (`[4]`, 3 strikes). `FillPlanTagDefaults()` sets the same.

**`ULBStormFXSubsystem` (D-105)**
- A `UTickableWorldSubsystem` for Game and PIE worlds only; `Initialize` depends on `ULBStormSubsystem`.
- **Activation is lazy, in `Tick`.** On the first tick (after BeginPlay) where the storm is active, it loads `Storm->GetSettings()->FXSettings`, seeds its `FRandomStream` from the storm's `RandomSeed` (0 = from the time), makes the rain, spawns the bolt pool and binds `OnLightningStrike`. It is active only when the settings load **and** `lb.StormFX.Enabled` is 1 (non-shipping CVar, default 1; Shipping is always on).
- **Give-up rule:** if the world has begun play and the storm is inactive, `bGaveUp` stops `IsTickable()` for good (the main menu, the test maps). Settings that are not linked or do not load also give up (one Log if `FXSettings` is unset, one Warning if it is set but does not load). `Rearm()` lets a test that adds the moon later start it again. Once it has been active it keeps ticking, and deactivates (rain destroyed, bolts hidden) when the storm goes inactive or the CVar goes to 0.
- **The rain component is created directly,** not with `UNiagaraFunctionLibrary::SpawnSystemAtLocation`: that function returns null under `-nullrhi` (`FApp::CanEverRender()`), where the suite needs the component. `CreateRainComponent` mirrors it without the guard: transient, absolute transform, not pooled, no auto-destroy. The strike sparks keep `SpawnSystemAtLocation`.
- **`GetViewLocation` (P15-9, 694bac1):** the player camera's location when the controller has a pawn, or when no view was rendered last frame; otherwise `World->ViewLocationsRenderedLastFrame[0]`. PIE Simulate keeps a pawnless `PlayerController_0` whose camera manager is parked at the start, so the rain follows the rendered view there. Real Play is unchanged.
- **Each tick** the rain moves to that location and writes only the user parameters that changed: `User.RainRate` (0 when `bRain` is false), `BoxHalf`, `SpawnHeight`, `FallMin`, `FallMax`, `Wind` = `RainWind(WindDirection, GetWindStrength(), RainWindLean)`, `SplashRate` (0 when `bRain` is false), `SplashRadius`, and `Mist` = `MistAmount(GetPlayerExposure(), MistMinExposure)` moved toward its goal at 1 per second.
- **Bolts.** A pool of `BoltPool` `ALBLightningBolt` actors (transient). `AcquireBolt` takes a hidden one, else the oldest. **On `OnLightningStrike`** every flash makes the same three draws (roll, length, atlas cell), so a seeded storm replays the same bolts. With `bHasTarget`, `StrikeSparksSystem` is spawned at the target and a strike bolt is placed with `StrikeBoltTransform` (start = target + (0, 0, `StrikeSkyHeight`) − horizontal flash direction × `StrikeSkyOffset`); a strike always draws its bolt. Otherwise `RollBolt(SkyBoltChance[Reason], roll)` decides (a reason missing from the map never draws) and `SkyBoltTransform` places it. No bolt is placed when there is no view location.
- **Bolt brightness is not written by C++:** `M_LB_Bolt` reads `MPC_LB_Storm.LightningFlash`, so the bolt flickers with the pulses and is 0 at rest. A bolt is hidden when no flash is running and F < 0.01, or after `BoltMaxSeconds`.
- **Debug (non-shipping).** `DebugBolt` ≥ 0 keeps one extra bolt shown every tick: 0 a sky bolt in front of the camera (`GetViewDirection`, mean `SkyBoltLength`), 1 a strike to the tagged target (searched every 2 s). `lb.StormFX.Bolt [0|1]` requests a Debug flash (brightness 1, profile Double; 1 goes through `RequestFlashAtTarget`) and warns when the FX are not active.

**`ULBStormFXSettings` / `DA_StormFX`** (`/Game/LastBell/Data/`, a `UPrimaryDataAsset`, read through its pointer every frame; the pool size and the assets are read at activation). It holds four soft asset pointers (`RainSystem` = `NS_LB_Rain`, `StrikeSparksSystem`, `BoltMesh` = `SM_LB_FX_BoltCard`, `BoltMaterial` = `MI_LB_Bolt`) and the numbers. **The saved asset overrides some code defaults (the plan's); the look session chose the values (P15-7) and P15-8 saved them:**

| Field | Saved value | Code default |
|---|---|---|
| `RainSpawnRate` | **50000** /s | 35000 |
| `SplashRate` | **1600** /s | 2500 |
| `SkyBoltDistance` / `SkyBoltTopHeight` | **30000 / 30000** cm (a bolt spans about 17–45° of elevation) | 60000 / 22000 |
| `SkyBoltChance` | Ambient **0.9**; Scripted 1.0, WardenReveal 0.5, Apparition 0.5, Debug 1.0 | Ambient 0.6 |
| `DebugBolt` | **−1; never save it otherwise** (`Monastery.FXSetup` fails on it) | −1 |

Unchanged from the defaults: `bRain` true, `RainBoxHalfXY` 1800, `RainSpawnHeight` 2500, `RainFallSpeed` (1100, 1400), `RainWindLean` 500, `SplashRadius` 1200, `MistMinExposure` 0.6, `SkyBoltLength` (16000, 26000), `BoltAspect` 0.35, `StrikeSkyHeight` 12000, `StrikeSkyOffset` 2500, `StrikeWidth` 1400, `BoltAtlasCount` 8, `BoltMaxSeconds` 2.5, `BoltPool` 4. The never-save rule for `DA_StormSettings.DebugFreezeFlash` and `DebugIntensityOverride` (section 14) still applies.

**`ALBLightningBolt`.** An actor whose root is a `UStaticMeshComponent` (movable, `NoCollision`, no shadows, no custom depth, no decals; actor tick off). `SetAssets` takes the mesh and material; `SetBolt(Transform, AtlasIndex)` makes the dynamic material instance once and sets the scalar `AtlasIndex`; `ShowBolt(Now)` and `HideBolt()` toggle hidden-in-game; `GetBoltBottom()` is the card's local (0, 0, −100).

**`LBStormFXLogic`** (pure functions, unit tested):
- `SkyBoltTransform(Camera, Direction, Distance, TopHeight, Length, Aspect)`: top = camera + the horizontal direction (+X when it is zero) × distance + (0, 0, top height); the card faces the camera; scale (Length × Aspect ÷ 100, 1, Length ÷ 100) for the 100 cm card.
- `StrikeBoltTransform(Start, End, Camera, Width)`: the card spans Start → End with its pivot at Start and turns about its axis to face the camera.
- `RainWind` = `WindDirection.GetSafeNormal2D()` × strength × lean. `MistAmount` = smoothstep(Min − 0.1, Min + 0.1, Exposure). `RollBolt(Chance, Roll)` = Roll < Chance.

**Niagara systems** (`/Game/LastBell/FX/Niagara/`; built over MCP by `Tools/fx/p15_5_niagara.py`; each UpToDate with 0 errors). MCP has no event-handler tool, so no system uses events.
- **`NS_LB_Rain`** (camera-following; nine user parameters, named as the C++ writes them).
  - **`Rain`** (GPU, fixed bounds ±4000 cm in XY, Z −1000…+3000): a box of 2 × `BoxHalf` at `SpawnHeight` (±200 jitter); velocity = `User.Wind` + a `RandomRangeVector` fall; lifetime 3.5 s; velocity-aligned sprite `MI_LB_Rain`, 0.7 × 28–42 cm. **Collision** is the placed module's static switch `GPU Collision Type` = "GPU Distance Fields", kill on collision, `Radius Calculation Type` Custom, radius **20** cm. Also killed below camera Z − 800.
  - **`Splash`** (GPU): spawned in a disc of `SplashRadius` at `SpawnHeight`, falls at the rain speed, collision radius **6** cm with kill off. **The pin chain** runs after `Collision` and `Solve Forces and Velocity`, one SetParameters module each: `LandPos` = `Landed ? LandPos : Position`; `Landed` = `Landed || HasCollided`; `Position` = `Landed ? LandPos : Position` and `Velocity` = `Landed ? 0 : Velocity`; `LandAge` = `Landed ? LandAge + DeltaTime : 0`; colours, sizes and SubUV index (alpha 0 until landed); `DataInstance.Alive` = `LandAge <= 0.45` (and `Age < Lifetime`, and above camera Z − 800). Renderer 1 is a camera-facing crown (`MI_LB_Splash`, SubUV 4 × 4); renderer 2 is a flat ring with custom facing (0, 0, 1) (`MI_LB_Ripple`).
  - **`GroundMist`** (CPU): rate 5 × `User.Mist` /s in a ring of 600–2200 cm around the camera at Z −120 ± 40; lifetime 6 s; drift `User.Wind` × 0.15; size 250–450 cm; `MI_LB_Mist`.
- **`NS_LB_RainColumn`** (P15-8): the same `Rain` and `Splash`, no `GroundMist`, rain sprite (1.4, 36–54) cm; defaults `RainRate` 6000, `BoxHalf` 300, `SpawnHeight` 2000, `SplashRate` 400, `SplashRadius` 270. Three actors in `FX/Storm`, each a local column of about 5 × the open-rain density under a roof opening. The subsystem and `lb.StormFX.Enabled` do not control them, and nothing writes their `User.Wind`:

| Actor (opening) | Location | `RainRate` / `BoxHalf` / `SpawnHeight` | `SplashRate` / `SplashRadius` |
|---|---|---|---|
| `FX_RainColumn_Chapel` (`Ch_Roof_S1` hole) | (6500, −418, 0) | 7000 / 300 / 2050 | 400 / 270 |
| `FX_RainColumn_Cloister` (north walk hole) | (11085, 2517.5, 0) | 7400 / 310 / 1150 | 420 / 280 |
| `FX_RainColumn_Belfry` (collapse in `TWA_Roof`) | (12187.5, 1687.5, 2500) | 5200 / 260 / 2000 | 300 / 235 |

- **`NS_LB_StrikeSparks`** (CPU burst): 70 sparks with `MI_Flame_Torch`, system Once for 1.5 s; the light renderer is on for every 20th particle (4 of 70).
- **`NS_LB_TorchFire`** (CPU; `User.Scale`): `Flames` (upright billboards), `Embers`, `Smoke` (`MI_LB_Mist`). **`NS_LB_ShaftDust`** (GPU, local space; `User.BoxExtent` = half-extent, `User.Count`). **`NS_LB_WaterMist`** (CPU; `User.Extent` = full plane size).
- **`NS_LB_Drip` and `NS_LB_EaveDrips`** (CPU, local space; `User.FallHeight`, `User.bWater`; the eaves also `User.LineLength`) use the single-particle fallback: one particle is the drop, pinned at −`FallHeight` by a latch, and a visibility tag switches it from the drop renderer to the crown and the ring (the ring only with `bWater`). Final values (P15-8, edited in place): drop sprite (1, 14) cm with alpha 1; crown 10 cm; ring 3 → 26 cm; `NS_LB_Drip` `User.Interval` default (0.8, 2.5) s; eave spawn rate `User.LineLength * 0.04` /s (4 drops per metre per second).

**Materials** (`/Game/LastBell/Materials/FX/`, MIs in `Instances/FX/`; `Tools/fx/p15_4_materials.py`).
- **Additive rain family** (lead decision, P15-4): `M_LB_Rain`, `M_LB_Splash`, `M_LB_Ripple` and `M_LB_RainCurtain` are Additive with every mask in Emissive and Opacity unconnected, so they only add light (a dim Translucent base would darken lit backgrounds). Each is `Base + Flash × LightningFlash` (`MPC_LB_Storm`). Saved rest brightness: `MI_LB_Rain.RainBase` 0.25, `MI_LB_Splash.SplashBase` 0.18, `MI_LB_Ripple.RippleBase` 0.2 (they were 0.035, 0.08 and 0.05, and the rain was invisible at rest). `M_LB_Bolt` (additive, fogging off) = `FlashTint` × `BoltGain` 40 × `LightningFlash`, from an atlas cell. `M_LB_DustMote` (additive) and `M_LB_Mist` (translucent) also read `LightningFlash`. `MI_LB_WaterMist`: `MistBase` 0.28, `MistOpacity` 0.26.
- **`M_LB_Flame`** (additive; sprite or mesh by the static switch `bSprite`): `MI_Flame_Candle` (mesh), `MI_Flame_Torch` (sprite, `EmissiveStrength` 7). The mesh random hashed `ObjectPositionWS`, so a moving flame got a new phase every frame and vibrated. Fix (P15-8): scalars `UseFixedSeed` (0) and `FixedSeed` (0.37), `rnd = lerp(rnd, FixedSeed, UseFixedSeed)`. `MI_Flame_Candle_Player` (`UseFixedSeed` 1) is used only by `BP_LBCharacter.CandleFlame`.
- **Cloth:** `M_LB_Cloth` (opaque, two-sided, the CC0 Hessian 230 fabric) takes its WPO from `MF_LB_ClothWave` (`/Game/LastBell/Materials/Functions/`): a travelling wave pinned at the top edge (pin = v^1.5, v = UV0.y) plus a whip along the vertex normal, driven by `WindStrength`, `WindPhase` and `WindDirection`; the offset is exactly 0 at `WindStrength` 0. `MI_Cloth_Linen_Dark.AmplitudeCm` is 18 (saved).
- **`MPC_LB_Storm` inputs used by Phase 15:** `LightningFlash` (rain family, bolt, dust, mist), `FlashTint` (bolt), `WindStrength`, `WindPhase`, `WindDirection` (cloth). `WindStrength`, `WindDirection` and `PlayerExposure` also reach the rain through the C++. No new MPC parameter.

**Level placement** (`Tools/fx/p15_level.py --apply/--check/--save`; idempotent, `--apply` never saves; new actors in the folder `FX/Storm`). **Census 3015 → 3054** (+39: target 1, dust 11, water mist 2, drips 10, eave drips 7, cloth 4, fires +1 net, rain columns 3).
- 11 `FX_Dust_*` (count 120 in the 4 chapel shafts, 80 in the 7 crypt and tower shafts), 2 `FX_WaterMist_W/E`, 10 `FX_Drip_*` (8 crypt, 2 belfry), 7 `FX_EaveDrips_*`.
- **Fires:** 6 `NS_LB_TorchFire` actors replaced the 5 Cascade `Emitter` actors and added the courtyard fire pit. `User.Scale` is 0.7 (5 torches), 1.3 (`FX_Crypt_Brazier_NS`), 1.4 (`FX_FirePit_Fire`). The point lights, their light functions and `FX_FirePit_Smoke` are unchanged. The `PS_Fire_*` assets stay in the project, no longer placed.
- **Flames:** `MI_Flame_Candle` is the slot-0 override on 22 level flame actors. The 4 puzzle candles have per-instance overrides (mesh `SM_LB_Prop_CandleFlame_A`, `MI_Flame_Candle`, 6.5 cm tall). The player's flame is 4.55 cm (relative scale (23.3333, 23.3333, 5.83333) under the scaled `CandleWax`). No graph sets those components' mesh or material. The saints' cones are unchanged.
- **Cloth:** 4 strips stay (`Slit_F03`, `Slit_F07`, `Cloister_S_2`, `Gate_Inner`). Removed after the look session: 6 cloth pieces (4 in the belfry, the cloister banner and the cloister sheet) and all 8 rain curtains (a tiled streak card read as glowing pillars or sheets). The curtain, banner and sheet assets stay in the project, unused; `MI_LB_RainCurtain` was never saved.

**Rain occlusion, approach A (D-104, D-106).** The rain dies where the global distance field has a surface, so a roof stops it and a hole lets it through; splashes are pinned at first contact. S1 measured 0 rain and 0 splash pixels under the chapel, the cloister south walk and the tower stair, and no rain under the 4 cm walk planks.
- Roof meshes need their distance field (project switch `r.GenerateMeshDistanceFields`, 5 cm voxels). A hollow mesh builds a solid field that seals its holes, so `SM_LB_Tw_Roof_BrokenSW` has "Two-Sided Distance Field Generation" on (set by hand and saved; MCP cannot reach the mesh build settings).
- The rain radius is 20 cm because a low frame rate (Simulate) lets a drop step past a thin surface. The splash radius is 6 cm so a pinned splash sits on the floor, not 20 cm above it.
- P15-9 difference test (camera rain on against `bRain` off, inside the roofed rects): mean absolute difference ≤ 1/255 in all four measured poses (0.09…0.87). The courtyard planks, the cloister hole and the belfry were judged by eye.
- Fallbacks C (a baked roof map) and B (hand-placed rain boxes) were not needed.

**Tests** (suite **141/141**, up from 128; last run with the editor closed, after 694bac1). Unit (`LBStormFXTests.cpp`): `LastBell.StormFX.Logic.SkyBoltTransform`, `.StrikeBoltTransform`, `.RainWind`, `.MistAmount`, `.RollBolt`. Functional (`LBStormFXFunctionalTests.cpp`, PIE): `LastBell.Functional.StormFX.ActivatesWithStorm`, `.RainFollowsCamera`, `.TargetedStrikeDrawsBoltToTarget`, `.SkyBoltOnAmbientFlash`, `.BoltHidesAfterFlash`, `.DisabledByCVar`, `.StrikeInfoMatchesFlash`, `.Monastery.FXSetup`. `FXSetup`, on the real level, checks:
- `DA_StormSettings.FXSettings` is linked, `DA_StormFX` loads, and `RainSystem`, `BoltMesh` and `BoltMaterial` are set;
- `DA_StormFX.DebugBolt` and the two `DA_StormSettings` debug fields are −1;
- exactly one actor is labelled `FX_StrikeTarget_Tower` and exactly one carries `LB_StrikeTarget_Tower`;
- two strikes have a `StrikeTargetTag` (`CourtyardEntered` and `TowerTop`), and both resolve;
- the FX are active and the rain component exists after BeginPlay (it exists under `-nullrhi` because it is created directly).

**Performance** (P15-10, D-107; `PERFORMANCE_BUDGET.md`, rows of 2026-11-09). The GPU rule passes at all six spots: with the FX on, 13.81–15.67 ms; added +0.09…+1.39 ms, each within its budget; the least headroom is the chapel, 0.93 ms under 16.6.

**Known limits and open items**
- **R-64:** the game-thread rule (≤ +0.3 ms with the FX on) could not be resolved with `stat unit` (repeats vary by up to 2 ms). Trace the storm FX with Unreal Insights in the Phase 20 pass (moved from Phase 18, D-127) (`ULBStormFXSubsystem::Tick`, the rain component tick, the bolt updates).
- **R-69:** the cost of the global distance field update with a moving camera is not measured (about 0 ms standing still). Phase 20.
- **White flecks in the sky** were seen in 2–3 courtyard Simulate frames, probably splashes pinned where the coarse far distance field reports a surface. The owner did not report them in Play.
- **`GetViewDirection` still reads the parked camera in Simulate:** a held `DebugBolt 0` always points toward world +X there. Captures use poses that look east (`cy_gate_east_sky`, `cl_garth_east_sky`).
- **Never Live Code `LBStormFXSubsystem.cpp`** (or any .cpp with a file-static `TAutoConsoleVariable`): the patched CVar is not registered, and the editor crashed at PIE start. Close Unreal and use `Tools/build_and_test.ps1`.
- `GetSystemCompileState` on `NS_LB_Rain` can time out in the editor (a tool artefact; the system compiles in 0.55 s at PIE start). Do not rebuild or re-save it. `AssetTools.exists` and `is_dirty` report `DA_StormFX` wrongly while PIE runs.
- `p15_5_niagara.py build` refuses `NS_LB_Rain`, `NS_LB_Drip` and `NS_LB_EaveDrips`: a rebuild can drop the placed actors' overrides. Edit them in place.
- The rain columns do not lean with the wind and do not stop with `lb.StormFX.Enabled 0`.
- **Tools:** `Tools/fx/` (`p15_4_materials.py`, `p15_5_niagara.py`, `p15_level.py`, `p15_7_live.py`, `p15_9_capture.py`, `p15_9_report.py`, `s1_*.py`), `Tools/textures/fx/make_fx_textures.py`, `Tools/blender/fx/`. The MCP method is in `Tools/mcp/MCP_NOTES.md`, the Phase 15 sections.

## 16. Audio (Phase 16, D-108…D-113)
Spec and results: `Docs/plans/P16_AUDIO.md` (spec §0–§14, then "Results" for A1–A4, F0, P16-2…P16-6). Code: `Source/LastBell/Audio/` (`LBAudioSettings`, `LBAudioSubsystem`, `LBAudioLogic`, `LBAudioZone`, `LBAmbientEmitter`, `LBWardenAudioComponent`, `LBAudioTypes`), `Character/LBFootstepComponent.*`, `Character/LBCandleComponent.*`. Records: `Docs/ArtTest/audio/` (`p16_2_assets.md`, `p16_2_report.json`, `p16_3_level.md`, `audition*.md`). Tools: `Tools/audio/` (`gen/`, `prep/`, `p16_2_assets.py`, `p16_level.py`, `p16_4_live.py`, `p16_f0_survey.py`).
- **Purpose:** weather, thunder, the great bell, music, the player's breath, the Warden's voice, interaction cues, footsteps and room acoustics, all heard in `L_Monastery`.
- **Boundaries:** the audio director listens and plays; it changes nothing in the storm, world state, Warden AI or interactables. The Warden's hearing is unchanged (`ULBFootstepComponent` reports the same noise events; the gait volume scales the sound only). No hard asset references: sounds are soft pointers in `DA_Audio`. No MetaSound graphs, Audio Modulation, Soundscape or submixes (D-109). No Blueprint is edited: cues are mapped by actor class because several interaction Blueprints are on the never-save list (R-76). HRTF is Phase 20; menu and UI sounds are Phase 18; the finale's timing is Phase 17.

**`ULBAudioSubsystem`** (`UTickableWorldSubsystem`, Game and PIE worlds only; D-109)
- **Activation** mirrors `ULBStormFXSubsystem` (D-105): lazy, in `Tick`, on the first tick after BeginPlay where `ULBStormSubsystem::IsActive()` is true. It loads `ULBGameSettings::AudioSettings` (`DA_Audio`, linked in `Config/DefaultGame.ini`) or the test override (`OverrideSettings` plus `Rearm`), preloads the sounds, binds the delegates and logs "Audio: active (111 sounds loaded, 7 zones, 29 bound actors)". The main menu and the test maps have no storm, so `bGaveUp` stops the tick for good. `lb.Audio.Enabled 0|1` (non-shipping CVar, default 1) fades everything out over 0.5 s and unbinds, or brings it back. `LBAudioSubsystem.cpp` defines that CVar: never Live Code it.
- **Bindings:** the storm (`OnLightningStrike` only; it carries the brightness, reason, direction and target of the same flash that `OnLightningFlash` announces), the world state (`OnStateChanged`, `OnStateReplaced`), the Warden brain (`OnPlayerSpotted`, `OnPlayerCaught`), the player's candle (`OnCandleStateChanged`, `OnRelightStarted`) and inspection component (`OnInspectBegin`, `OnInspectEnd`, rebound when the pawn changes), and every `ULBInteractableComponent`, `ULBDialComponent` and `ULBSequencePuzzleComponent` through one `ULBAudioProxy` per actor (found at activation and on `OnActorSpawned`). `ALBWardenApparition::OnAppeared(Apparition, StationIndex)` is a new delegate.
- **Weather bed:** four 2D loops (RainOut, RainIn, Wind, WindHowl) plus two room-tone slots. Per tick: E = `GetPlayerExposure()`, W = `GetWindStrength()`, Z = the current zone.
  - RainOut = `RainOutGain` × E^`RainExposurePower`; RainIn = `RainInGain` × (1 − E) × Z.`RoofRain`.
  - Wind = `WindOutGain` × lerp(`WindMin`, 1, W) × max(E, Z.`InteriorWind`), pitch lerp(`WindPitch`, W); WindHowl = Z.`Howl` × W.
  - Each level eases over `MixFadeSeconds` (0.75 s); a loop starts when its level first rises above 0.003 and stops at 0. **Final values (owner):** `RainOutGain` 0.22, `RainInGain` 0.03, `RainExposurePower` 1.5, `WindOutGain` 0.08, `WindMin` 0.2.
- **Room tone:** the zone is re-checked 4 times a second (highest `Priority` wins, outdoors is the default); the tone crossfades over `RoomToneFadeSeconds` (2 s) between two loop slots.
- **Thunder:** `LBAudioLogic::PlanThunder`: Near at brightness ≥ 0.75, Far below 0.4, Mid between; delay lerp(4.5, 0.6, B) ± 0.4 s; volume 0.55 + 0.45 B. The sound plays at the listener + the flash's horizontal direction × `ThunderDistance` (6000 cm) with `ATT_LB_Thunder`, so it comes from the flash side. A strike with a target also plays a `Thunder_Strike_*` crack at the target after `StrikeCrackDelay` (0.12 s), and its thunder is Near. **The cracks are recordings:** `Thunder_Strike_01..03` and a crack layer at the start of `Thunder_Near_01..04` come from five Freesound CC0 sources; the rumble under them is generated (the owner rejected the synthetic cracks in P16-4). No variant repeats within a set.
- **Bell beats (tag added only):** `State.Ritual.1` stage 2 × 3 (2 s, then 4.5 s apart; Drone B); `State.Event.CryptEntered` Drone A only; `State.Ritual.2` stage 3 × 3 (2 s, 4.5 s; Drone C); `State.Ritual.3` stage 4 × 3 (2 s, 4.0 s; Drone B); `State.Event.TowerTop` stage 4 × 4 (1 s, 3.5 s; Drone C); `State.Event.Finale` stage 5 × 5. Nothing plays on `OnStateReplaced` (a checkpoint load).
  - **New-game toll (code kept, off since P17):** with no beat tag present at activation, stage 1 × 3 after 6 s (4.5 s apart) and Drone A. `DA_Audio.bNewGameToll` is **false** since P17-2: the intro's `State.Event.Arrival` beat (first row of `BellBeats`: stage 1 × 3, the first strike at once, 4.5 s apart, **no drone**, `Drone` −1) replaces it (D-117, D-120). **Ambient tolls:** every 240–420 s after the last toll of any kind, the highest stage reached, 1–2 strikes at volume 0.5, spaced 4.5 s; skipped and retried after 30–60 s in a chase, while the tension layer is above 0.5, or within 90 s of a beat; none after the finale. `PlayBell(Stage, Strikes)` is the public API (Phase 17; `lb.Audio.Bell`).
  - **Finale under the ending pause (P16-6, 917b0c6; the pause itself is gone since P17, D-117, and the workaround was reverted in Phase 18, D-128):** the audio director was tickable when paused, and the great bell's strikes ran on the unpaused clock as UI sounds. That is gone: `IsTickableWhenPaused()` is false, so the whole schedule freezes with the world, and the bell is an ordinary game sound (section 18, "Pause"). A beat with `FirstDelay` ≤ 0 still plays its first strike inside `HandleStateChanged`, before `AddState` returns. **Owner values:** the finale spacing is 2.0 s (code default, cue sheet and script agree since P16-7) and `SFX_LB_Bell_Stage5` `Volume` is 2.0; bell stages 1–4 and far thunder are at 1.0.
- **Music:** three 2D loops (Drone, Tension, Chase) and stings. A drone starts with its beat (fade in 6 s, hold `DroneSeconds` 45 s, out 8 s; a new drone waits for the old one to fade). Tension comes from the Warden state (`TensionLevels`: Patrol 0.25, Suspicious 0.5, Investigate 0.6, Search 0.8, Chase 0.4, Return 0.15), only when the Warden stage is ≥ 3 and it is within 2500 cm; in Chase and Attack tension is 0.4 and the chase layer 1.0 whatever the stage. Fades: tension in 3 s / out 10 s, chase in 0.8 s / out 4 s. Stings: `StingSpotted` on `OnPlayerSpotted`, `StingCaught` on `OnPlayerCaught`, `StingApparition` on `OnAppeared`. `DebugForceMusicState` and `lb.Audio.Music` force a Warden state.
- **Stress and breath:** target = the Warden's share (Chase 1.0; 0.6 within 1500 cm while Investigating, Suspicious or Searching), raised to the darkness floor (zone `Darkness` × 0.15 with the candle lit, × 0.55 with it out; outdoors 0.1), plus 0.3 for 3 s after a sprint; rise 0.6 /s, decay 0.25 /s. The candle going out adds 0.35 at once and plays a `BreathGasp` straight away. At stress ≥ 0.3 a 2D breath (Calm ≥ 0.3, Heavy ≥ 0.55, Panic ≥ 0.85) plays every 2.4–4.0 s.
- **Candle cues:** lit plays `CandleLight`, out plays `CandleOut`, relight start plays `CandleRelight`, attached to the candle. A failed candle puzzle plays one `CandleOut` at the puzzle actor.
- **Interaction cues:** `DA_Audio.InteractionCues` (9 rows; the most specific class wins; `bIncludeSubclasses`) and `SilentClasses` (3). Rows: `BP_Door_Base` (wood open; locked as Denied), `BP_DialLever` (notch sounds; the Interact sound is suppressed for a dial), `BP_PuzzleCandle` (candle light), `BP_Inspectable_Note` (paper), `BP_RitualMechanism_ChapelBells` (stone grind), `_CryptWinch` and `_TowerCapstan` (winch; the capstan pitched 0.9–1.0), `BP_TagInteractable_ChapelKey` and `_CryptCrank` (key pick-up; the crank pitched 0.85–0.95). Silent on purpose: `BP_SequencePuzzle`, `BP_SmallBell_Cloister`, `BP_TagInteractable_GreatBell` (the finale beat covers it).
  - **Notes (917b0c6, 8d40b06):** the rustle plays on pick-up (`OnInspectBegin`) and on every put-down (`OnInspectEnd`, including `CancelInspect`, which never fires `OnInteracted`). On a keep, `OnInteracted` runs before `OnInspectEnd`, so a same-frame check (`GFrameCounter`) keeps a kept item to one rustle at put-down.
  - **Small bells only for the bell puzzle:** the strike, fail and solved sounds play only when the step tag is a key of `SmallBellPitch` (`State.Tower.Bell.1..4` = 0.7692, 0.8696, 1.0, 1.1765). The chapel candle puzzle is silent per step, plays one `CandleOut` on a failure and is silent when solved.
- **User volumes:** `ULBUserSettings` holds `MasterVolume`, `SFXVolume`, `AmbienceVolume`, `MusicVolume`, `VoiceVolume` and `UIVolume` (default 1, saved per user). `ApplyUserVolumes()` pushes `SMX_LB_User` with one class override per `SCL_LB_*` (at activation, on a settings change and from `lb.Audio.Volume`); the Master override applies to its children. Ready for the Phase 18 menu.
- **Request sink (non-shipping):** every play request (cue, world time, location, volume, pitch, variant, aux) goes to `GetRequests()`; footsteps, the Warden component and the emitters record through `RecordRequest`. The suite runs with `-nosound`, so tests read requests, not audio (R-74).
- **Console** (`Systems/LBConsoleCommands.cpp`): `lb.Audio.Enabled`, `lb.Audio.Thunder 0|1|2` (far, mid, near), `lb.Audio.Bell <stage> [strikes]`, `lb.Audio.Music <state|-1>`, `lb.Audio.Volume <group> <0..1>`, `lb.Audio.Debug 0|1` (on-screen readout).

**`ULBAudioSettings` / `DA_Audio`** (`/Game/LastBell/Data/DA_Audio`, a `UPrimaryDataAsset`)
- Sound groups `Weather`, `Thunder`, `Bell`, `Music`, `Player`, `Warden` (soft refs); `InteractionCues`, `SilentClasses`; `SmallBellPitch` and `SmallBellStrike/Fail/Solved`; `BellBeats`; `BellLocation` (12420.1, 2000, 2750); `UserMix` and `UserClasses`. Every float is clamped, with units in its tooltip. The numbers are the plan's, except the owner's values above. Additions to the plan: `NewGameTollStrikes`/`Spacing`/`Drone`, `AmbientTollSpacing`, `PlayBellSpacing`, `StressRise`, `RoomToneFadeSeconds`, `OutdoorsDarkness`. `BellNearDistance` is reserved and not read.
- `CollectSounds` lists every soft ref; `FindCueRow` resolves a class. `DebugForceMusicState` is −1 and is never saved otherwise (`Monastery.AudioSetup` checks it).

**`ALBAudioZone`** (box, no collision; `Priority`, `RoofRain`, `InteriorWind`, `Howl`, `Darkness`, `RoomTone`, `RoomToneVolume`, `ZoneName`). Seven are placed in `L_Monastery` (`AUD_Zone_*`; final values after P16-4…P16-6):

| Zone | Prio | RoofRain | InteriorWind | Howl | Darkness | Room tone (volume) |
|---|---|---|---|---|---|---|
| Chapel | 1 | 0.90 | 0.25 | 0 | 0.3 | Chapel (**0.4**) |
| Crypt | 2 | 0.05 | 0.05 | 0 | 1.0 | Crypt (0.8) |
| Cloister | 1 | 0.70 | 0.50 | 0 | 0.2 | Cloister (0.5) |
| Garth | 2 | 0 | 1.0 | 0 | 0.1 | none |
| Passage | 1 | 0 | 0.40 | 0 | 0.6 | Passage (0.7) |
| TowerStair | 3 | 0.60 | 0.60 | 0.35 | 0.6 | Tower (0.7) |
| Belfry (from z 2400) | 4 | 0.80 | 1.0 | **0.25** | 0.3 | Belfry (**0.4**) |

- Boxes are in `Docs/ArtTest/audio/p16_3_level.md`. Reverb comes from 7 engine `AAudioVolume` actors (`AUD_Vol_*`, the same bounds): `RVB_LB_<Area>`, volume 0.6, fade 1.0; exterior volume and low-pass 0.35 / 2500 Hz (chapel, crypt, passage, tower) and 0.7 / 6000 Hz (cloister, belfry); the garth has no reverb and no muffling.

**`ALBAmbientEmitter`** (31 placed in the outliner folder `Audio`; census 3054 → 3089 → 3102). One-shots (a random variant every `IntervalMin..Max` s, no repeat, volume 0.7–1.0, pitch 0.95–1.05) or one loop. It plays only while the player is within `ActiveRadius` (checked 4 times a second) and the director runs.

| Kind | Count | Sounds | Interval (s) | ActiveRadius (cm) |
|---|---|---|---|---|
| Water drips (crypt) | 5 | `Drip_Water_01..05` | 1.5–4 | 3000 |
| Stone drips (crypt 3, belfry 2) | 5 | `Drip_Stone_01..05` | 2–6 | 3000 |
| Creaks (3 in the tower core, 2 at belfry beam height) | 5 | `Creak_Wood_01..05` | 8–20 | 3000 |
| Distant chains (crypt corners) | 3 | `Chain_Distant_01..04` | **8–18** (owner) | 4000 |
| Bats (3 belfry beams, 1 at the top of the shaft; D-112) | 4 | `Bat_01..06` | 6–15 | 2500 |
| Owls (courtyard 2, garth 1) | 3 | `Owl_01..04` | 30–60 | 6000 |
| Howls (outside the perimeter walls, NE and SW) | 2 | `Howl_01..03` | 120–240 | 15000 |
| Rats (crypt wall bases) | 4 | `Rat_01..05` | 15–35 | 2000 |

**`ULBWardenAudioComponent`** (created in `ALBWarden`'s C++ constructor, so `BP_Warden` has it unsaved). Active only while the Warden is on stage (not dormant). Breath: three 3D loops (Slow for Patrol/Return, Fast for Investigate/Suspicious/Search, Heavy for Chase/Attack) crossfaded over 1 s, `ATT_LB_Warden`. Steps by distance (150 cm stride) plus a chain clink above 150 cm/s; a robe loop with gain = speed ÷ 420 cm/s. Tells attach to the Warden with `ATT_LB_WardenTell`: Spotted (`OnPlayerSpotted`), Roar (entering Chase), Windup (`OnAttackWindup`), Exhale (`OnPlayerLost`), Caught (`OnPlayerCaught`), each a no-repeat variant. Owner: Roar `Volume` 2.0 (it was inaudible under the chase music); "the other Warden sounds are fine".

**Footsteps** (`ULBFootstepComponent`, `DT_Footsteps`). `FLBFootstepRow` gained `Variants`, `CrouchVolume` 0.5 and `SprintVolume` 1.25; a step picks a random variant that is not the last for that surface, falling back to `Sound`. Seven rows (Default plays Stone, Stone, Wood, Earth, Grass, Water, Metal), six variants each, volume 0.8–1.0, pitch 0.95–1.05. Surface types in `Config/DefaultEngine.ini`: `SurfaceType1..6` = Stone, Wood, Earth, Grass, Water, Metal; `PM_LB_*` in `/Game/LastBell/Physics/`.
- **Floors:** the floors are greybox collision with no material (81 % of 168 sampled hits), so the surface is a per-actor `BodyInstance.PhysMaterialOverride` on 207 actors: Wood on 154 tower steps, 10 landings and 2 belfry slabs; Grass on the garth floor; Earth on 40 garden patches. Stone is the default.
- **Crypt water:** the pool planes have no collision, so 3 hidden query-only boxes (`AUD_Water_W/E/Ledge`, block Visibility only, `PM_LB_Water`) sit 0.5 cm above the crypt floor shell.
- **Owner:** step `Volume` 0.6 (the six wooden steps 2.0); the footsteps, including the wood stairs, are confirmed by ear (R-73).

**Candle flame fix (P16-5, 7851031).** `ULBCandleComponent` finds the owner's flame visuals at BeginPlay (components tagged `FlameComponentTag`, default `CandleFlame`, else a component named `CandleFlame`), hides them on a snuff and shows them when `LitAlpha` rises on the relight. No Blueprint graph is touched. Test `LastBell.Functional.Candle.FlameHidesWhenSnuffed`.

**The mix** (`/Game/LastBell/Audio/Mix/`, built headless; D-110)
- **SoundClasses:** `SCL_LB_Master` (volume **0.7**) with children `SCL_LB_SFX`, `_Ambience`, `_Music`, `_Voice`, `_UI`; mix `SMX_LB_User`.
- **Attenuation (inner / falloff, cm):** `ATT_LB_Step` and `_Small` 200 / 1500; `_Medium` 400 / 3000 (air absorption); `_Large` 800 / 6000; `_Warden` 300 / 3500 (occlusion 0.4, low-pass 1200 Hz); `_WardenTell` 500 / 5000 (occlusion 0.6); `_Thunder` 20000 / 60000 (omni radius 3000); `_Bell` 10000 / 120000 (omni radius 2000). The howls use `ATT_LB_Thunder` (owner: `_Large` falls silent at 68 m, and the howl emitters are 95–120 m away).
- **Concurrency:** `CON_LB_Steps` 4 (stop oldest), `_Thunder` 2 (quietest), `_Drips` 6 (farthest), `_Tells` 1 (oldest).
- **Reverb:** `RVB_LB_Chapel` decay 3.2 s, `_Crypt` 2.4, `_Cloister` 1.6, `_Passage` 1.2, `_Tower` 2.8, `_Belfry` 1.5 (gain 0.22–0.35). `AudioMaxChannels=64` in `Config/DefaultEngine.ini` (it was 32).
- **Owner `SoundWave` volumes:** bell stages 1–4 at 1.0 and stage 5 at 2.0, far thunder 1.0, steps 0.6 (wood 2.0), Warden roars 2.0, owls 0.4, howls 0.5.

**Asset pipeline (D-111).** 193 sounds = 51 generated + 142 recorded.
- **Generated** (`Tools/audio/gen/`, numpy and Pillow, seeded; `build_all.py --group <g> [--verify]`) to `SourceArt/Audio/Generated/`. **Recorded** (`Tools/audio/prep/`, recipes in `recipes.json`) from Kenney CC0 and 73 Freesound CC0 sources (5 of them the crack recordings, via `prep_cracks.py`) to `SourceArt/Audio/Recorded/`. Rebuilds are byte-identical; objective checks: 145 for the generated set, 0 problems in the 142 recorded files. The owner auditioned every cue (`audition.html`; A4 judged everything keep); later changes were the cracks (recorded) and the creature set (D-112).
- **Import and assets are headless:** no MCP tool imports a WAV or creates a SoundClass, mix, attenuation, concurrency, reverb or physical material (F0), so `Tools/audio/p16_2_assets.py` runs with the editor closed (`UnrealEditor-Cmd -run=pythonscript`). It is idempotent, has `LB_MODE=apply|verify` and `LB_REIMPORT` (all, or a regex), and keeps the owner's values in `OWNER_CHOICES` so a re-run reproduces them (fresh verify: 1691 checks, 0 failures). Level work (zones, volumes, emitters, overrides, water pads) goes over MCP with the editor open: `Tools/audio/p16_level.py --apply/--check/--save`. Method: `Tools/mcp/MCP_NOTES.md`, "Audio assets (headless)", "Audio level work over MCP" and the P16-5 and P16-6 notes.

**Tests** (suite **175/175**, up from 141; last run with the editor closed).
- Unit, `LastBell.Audio.Logic.*`: `RainMix`, `WindMix`, `ThunderPlan`, `MusicTargets`, `Stress`, `AmbientTollPlan`, `BellPlan`, `PickVariant`, `Ease`.
- Functional, `LastBell.Functional.Audio.*` (24): `ActivatesWithStorm`, `DisabledByCVar`, `ZoneSelection`, `ThunderAfterFlash`, `TargetStrikeCrack`, `BellOnRitualTag`, `NoBellOnStateReplaced`, `NewGameToll`, `AmbientToll`, `FinaleBellImmediate`, `CandleOutGasp`, `MusicFollowsWarden`, `InteractionCue`, `DeniedCue`, `NotePickupCue`, `NotePutDownCue`, `SequenceSmallBellPitch`, `CandlePuzzleNotBells`, `FootstepVariantNoRepeat`, `UserVolumesApplied`, `WardenTells`, `ApparitionSting`, `AmbientEmitter`, and `Monastery.AudioSetup` on the real level. Also `LastBell.Functional.Candle.FlameHidesWhenSnuffed`.
- `Monastery.AudioSetup` checks that `DA_Audio` is linked and every soft ref loads, every interactable class is mapped or silent, at least 6 zones and 6 AudioVolumes exist, `DebugForceMusicState` is −1, and `DT_Footsteps` has a row per surface with at least 4 variants. `NewGameToll` is timing-sensitive: it failed once while CPU-heavy audio jobs ran beside the suite.

**Known limits and open items**
- **Performance is not measured (D-113, R-75).** The owner skipped the P16-6 audio readings (voices, audio thread, game thread; audio on against off at the six spots and in a chase). The cost is measured in the Phase 20 performance pass. The fallback ladder is in the plan, section 10.
- **HRTF** is Phase 20. **The finale's timing** was done in Phase 17 (section 17): the ending no longer pauses and the game runs to the end of the credits.
- **`OWNER_CHOICES` bookkeeping (closed in P16-7):** `SFX_LB_Bell_Stage5` 2.0 and the finale beat spacing 2.0 are in the script and in `FillPlanDefaults()`; `apply` changes nothing and `verify` compares every beat in full.
- `p16_level.py --check` has not been run since the Belfry row changed (Howl 0.25, tone volume 0.4); it needs the editor.
- The audio tools need the Python 3.14 interpreter with numpy and Pillow (the `python` on PATH lacks numpy): `Tools/audio/README.md`.
- Never Live Code `LBAudioSubsystem.cpp` (file-static CVar). Close Unreal and use `Tools/build_and_test.ps1`.

## 17. Cinematics (Phase 17, D-114…D-125)
Spec and results: `Docs/plans/P17_CINEMATICS.md` (spec sections 0–13, then the revisions 3.2b and 3.4–3.9, then "Results"). Code: `Source/LastBell/Cinematics/` (`LBCinematicSubsystem`, `LBCinematicSettings`, `LBCinematicLogic`, `LBCinematicWidget`, `LBCineAuthoringLibrary`, `LBCinematicTypes`). Records: `Docs/ArtTest/cine/` (survey, check outputs, contact sheets, `credits_preview.md`). Tools: `Tools/cine/` (`p17_sequences.py`, `p17_assets.py`, `p17_5a2_assets.py`, `p17_level.py`, `p17_4_maskview.py`, `make_credits.py`, the S1 spike and the F0 survey), and `Tools/blender/warden/` (`p13_reweight.py`, `p17_*`) for the Warden work.
- **Purpose:** the New Game intro, the finale after the great bell is rung (the mask lift, the last view through the mask, the end cards, the credits) and the swing of the great bell. Level Sequences hold the pictures; C++ carries out the story actions and always puts the player back.
- **Boundaries:** it adds to the world state only what its markers name (`State.Event.Arrival` and, through `GrantOnStart`, `State.Warden.Stage.6`); it never edits an interactable, the Warden AI or the storm (it calls their public APIs: `AddState`, `PlayBell`, `RequestFlash*`, `CompleteGame`). No hard asset references: the sequences, the mix and the settings are soft pointers. No Blueprint is edited, and the widget has no WBP asset (D-117).

**`ULBCinematicSubsystem`** (`UTickableWorldSubsystem`, Game and PIE worlds only; D-115)
- **Activation.** `OnWorldBeginPlay` loads `ULBGameSettings::CinematicSettings` (`DA_Cinematics`, linked in `Config/DefaultGame.ini`) or the test override (`OverrideSettings` plus `Rearm`). With neither, it does nothing for that world (the main menu and the test maps). It binds `ULBWorldStateSubsystem::OnStateChanged`, finds the bell pieces (see "The bell swing") and binds `ULBAudioSubsystem::OnGreatBellStrike`. The tick is Conditional: it runs only while a start is pending, a cinematic plays, the credits roll or the bell swings.
- **`DA_Cinematics`** (`ULBCinematicSettings`, `/Game/LastBell/Data/DA_Cinematics`, a `UPrimaryDataAsset`; every float is clamped, with units in its tooltip). It holds `Cinematics` (`FLBCinematicDef`: `Id`, `Sequence`, `Trigger` `NewGame` or `TagAdded` with `TriggerTag`, `BlockingTag`, `InitialLock`, `bStartBlack`, `bSkippableAtStart`, `GrantOnStart`, `FailSafeMarkers`), `Cards` (`TMap<FName, FLBCineCard>`: text, `Line` or `Title` style, hold and fade seconds), `Credits` (44 lines, generated), `CreditsSeconds` 40, `SkipHoldSeconds` 1.0, `SkipPromptText` "Hold E to skip" (key glyphs are Phase 18), `MarkSeconds` and `LookAssistSeconds` 1.5, the bell tags and swing numbers, and `CineFadeMix`.

  | Id | Sequence | Trigger | BlockingTag | InitialLock | bStartBlack | bSkippableAtStart | GrantOnStart | FailSafeMarkers |
  |---|---|---|---|---|---|---|---|---|
  | `Intro` | `/Game/LastBell/Cinematics/LS_LB_Intro` | `NewGame` | `State.Event.Arrival` | Full | true | true | none | `!tag:State.Event.Arrival` |
  | `Finale` | `/Game/LastBell/Cinematics/LS_LB_Finale` | `TagAdded` `State.Event.Finale` | none | Full | false | false | `State.Warden.Stage.6` | `!end` |

  Seven cards: `Intro_1..4` (hold 3.6 s, fade 0.5 s since the 3.10 retime, D-134), `Title` (3.5 / 0.8), `End_1` "The bell rings for you." (3.5 / 0.8) and `End_2` "THE LAST BELL" (4.0 / 0.8).

**Marker grammar.** Every action the sequence needs from the game is a Sequencer *marked frame* whose label is `[!]kind[:arg[,arg]]` (case-sensitive, no spaces). `UMovieScene::MarkedFrames` is runtime data, so markers ship in cooked builds, and moving a marker in Sequencer retimes its action. A leading `!` makes a **must** marker: a skip fires it if it has not fired yet. An unparsable label logs one Error at load, is ignored at run time and fails `Monastery.CinematicSetup`. `LBCinematicLogic::ParseMarker` parses; `MarkersToFire` returns the markers crossed in (previous, current] in order, each once (a backward jump fires nothing). Everything is scaled by `lb.Cine.Rate`, so tests at 8× see the same order.

| Label | Action |
|---|---|
| `card:<CardId>` | The widget shows the card (fade in, hold, fade out) |
| `tag:<Tag>` | `ULBWorldStateSubsystem::AddState` |
| `bell:<Stage>x<Strikes>` | `ULBAudioSubsystem::PlayBell` (`PlayBellSpacing` 4.5 s apart) |
| `strike:<ActorTag>[,<Brightness>]` | `ULBStormSubsystem::RequestFlashAtTarget` (Scripted) at the first actor with the tag; no such actor is a Warning and a plain `flash:` |
| `flash:<Brightness>` | `ULBStormSubsystem::RequestFlash` (Scripted) |
| `look:<ActorTag>[,<Seconds>]` | Look assist: the control rotation eases to face the actor (for `LB_Cine_Warden`, its `head` bone). Input is held at `Full` during the blend, then the previous lock returns |
| `mark:<ActorTag>[,<Seconds>]` | Moves the pawn to the tagged actor: XY, Z = actor Z + capsule half height, yaw, pitch 0 (smoothstep, movement mode `MOVE_None`, so no footsteps); `MOVE_Walking` again on restore |
| `lock:<None\|Look\|Full>` | The player's input lock |
| `skip:<0\|1>` | Skippable from here, or not |
| `mix:<on\|off>` | Pushes or pops `DA_Cinematics.CineFadeMix` |
| `credits[:<Seconds>]` | Starts the credits roll (default 40) |
| `end` | Waits for the roll to finish or be skipped, then `ULBSaveSubsystem::CompleteGame()`. The mix is **not** popped before the travel, so world sound doesn't return over the black screen; `Deinitialize` pops it |

**Starting.**
- **The NewGame rule** (decided in `OnWorldBeginPlay`, before the pending restore is cleared one tick later): a `NewGame` def starts when the world's package (PIE prefix removed) is `ULBGameSettings::NewGameMap`, `ULBSaveSubsystem::HasPendingRestore()` is false (so not Continue, a death reload or a checkpoint load), the world state lacks `BlockingTag` and `lb.Cine.Enabled` is 1. If chosen and `bStartBlack`, the camera is set to black at once (`SetManualCameraFade(1, Black)`), before the first frame, and the cinematic starts on the first tick.
- **The `TagAdded` trigger:** `OnStateChanged(Tag, bAdded = true)` matching a def's `TriggerTag` plays it. `OnStateReplaced` never triggers anything, so a load never replays the finale. A trigger dropped because a cinematic is already playing logs a Warning. `Play(Id)` (also `lb.Cine.Play`) ignores the trigger and the blocking tag.
- **`Play`:** adds `GrantOnStart`, loads the sequence synchronously, parses the markers into seconds (frame minus the playback start, over the tick resolution), creates a `ULevelSequencePlayer` (`bAutoPlay` false, `PlayRate` = `lb.Cine.Rate`; the player's own movement, look, hide-player and hide-HUD options are all off, since the subsystem does those), sets the lock to `InitialLock`, hides the HUD, creates the widget, then plays.

**Skip.**
- Holding Interact while locked calls `BeginSkipHold` / `EndSkipHold`; after `SkipHoldSeconds` (1.0 s) while skippable, `RequestSkip()` runs. The widget shows the prompt and a progress bar. Skipping during the credits stops the roll, so the pending `end` completes at once.
- **`RequestSkip`:** fire every must marker not yet fired, in order; set the camera to black at once; jump to the end, stop and `FinishRun`, which destroys the sequence actor; **on the next tick** (`SetTimerForNextTick`, a weak lambda, skipped if a new run started or a travel is pending) `StartCameraFade(1, 0, 0.5 s, Black)`; a clear timer (0.5 s + 0.2 s) then removes the fade.
- **The fade fix (S1b, 6826cec).** The first version called `StartCameraFade` before stopping the player. When a sequence player stops or its actor is destroyed, the engine's fade system (`MovieSceneFadeSystem`) restores the pre-animated fade with `SetManualCameraFade(saved value)`, which overrode the fade-up (in the owner's S1b run the view popped straight to the player's eyes). The black phase and the next-tick start fix this; `SkipFadesUp` and `SkipClearsFade` test it. **Both sequences' fade sections use completion mode Keep State**, so Sequencer never restores the fade and the subsystem owns it after the sequence (this also avoids a one-frame black flash at the intro's natural end).

**Restore and the fail-safe (R-84).**
- **Restore** (finish, skip, stop or failure): lock `None`, HUD shown, the sequence actor and the widget destroyed, `StopCameraFade()`, the mix popped if pushed, a mark move cut short completed (finish and skip only), and "Cine: <Id> finished (<reason>)" logged. `Deinitialize` restores the same when a world ends mid-run. A sequence that ends while the credits still roll holds the screen black until the roll ends, then runs `end` (`EndWaitsForCreditsPastSequenceEnd`).
- **The travel-pending restore.** When `end` has called `CompleteGame` and the travel is pending, the lock, HUD, fade, widget and mix are left exactly as they are, so the HUD doesn't flash over the black screen while the world is torn down. The `lb.Cine.NoEnd` path and a failed `CompleteGame` do the full restore.
- **The fail-safe.** If the sequence can't be loaded or the player can't be created, the subsystem logs an Error, fires the def's **`FailSafeMarkers`** in order (every one a must marker, because a missing sequence has no markers of its own to read) and restores. Intro: `!tag:State.Event.Arrival`, so the first toll and the world state are right. Finale: `!end`, so the game still ends. `MissingSequenceFailsSafe` tests it; `lb.Cine.Stop` is the manual way out.

**Player and controller** (`ALBCharacter`, `ALBPlayerController`)
- **`ELBInputLock`** { `None`, `Look`, `Full` } (`Character/LBPlayerTypes.h`); `ALBCharacter::SetInputLock` / `GetInputLock`. A lock other than `None` clears the move input, stops movement, uncrouches, turns sprint off and cancels an open inspection.

  | Handler | `Look` | `Full` |
  |---|---|---|
  | Move, Sprint, Crouch, Candle | ignored | ignored |
  | Look | allowed | ignored |
  | Interact | broadcasts `OnLockedInteractPressed` and returns | same |

- **The locked-interact poll.** `IA_Interact` has a Pressed trigger, so `Completed` fires one frame after the press and cannot mean "released". `OnLockedInteractReleased` is therefore broadcast only when no key bound to Interact is still down, checked on `Completed`/`Canceled` and on every tick while a locked press is held. Both delegates are non-dynamic multicast; the subsystem binds them only while it plays, so the character never includes the cinematic headers.
- **HUD hide:** `ALBPlayerController::SetHUDHidden(bool)` sets the HUD widget `Collapsed` or `SelfHitTestInvisible`. Cinematics never use `SetMenuMode`: the input mode stays game-only, so mouse look works under `Look`.
- **The checkpoint rule:** `ALBCheckpoint::CanSaveNow()` is also false while `ULBCinematicSubsystem::IsPlaying()`. The refusal is logged as "Checkpoint '%s' refused (%s). Retrying while the player stays inside.", with the reason "the Warden is chasing" or "a cinematic is playing". So nothing is saved while a cinematic plays. A checkpoint refused because a cinematic is playing saves once when that cinematic finishes, even if the player has left its box (`OnCinematicFinished`, QA M1, 740edc9; test `CheckpointSavesAfterCinematic`). So `CP_Approach`, reached while the intro still runs, saves the moment the intro ends, with `State.Event.Arrival` already set; and quitting during the finale leaves the save at `CP_TowerTop`.

**Warden stage 6 (D-116).** `LBWardenLogic::CapsForStage`: `bActive = Stage >= 3 && Stage <= 5`. At stage 6 the AI pawn goes Dormant (hidden, no collision, perception ignored) through the existing stage-gate path, so only the sequence's figure exists. `State.Warden.Stage.6`'s only source is the Finale def's `GrantOnStart`. `WSpawn_Tower` (MinStage 6) stays in the level, unused. Test: `Warden.Stage6IsDormant`.

**The bell swing** (every great-bell strike on the map; kept by the owner, D-124)
- `ULBAudioSubsystem::OnGreatBellStrike(Stage, Volume)` fires the moment any great-bell strike starts (beats, tolls, `PlayBell`), never for small bells. The subsystem kicks `LBCinematicLogic::FBellPendulum`: angle(t) = A·e^(−d·t)·sin(2πt/P); each kick adds `BellSwingKickDegrees` (6°) to A, clamped to `BellSwingMaxDegrees` (16°); P is 2.6 s and d 0.25 per second; below 0.05° it stops and the tick goes idle.
- **The headstock and the rope swing about the axle.** The bell's origin (z 2860, the crown) is 20 cm below the axle, and the headstock wraps the crown, so a bell turning under a still headstock would clip through it. At BeginPlay the subsystem finds the bell actor (`LB_Cine_Bell`, component `Mesh`, its root), the headstock actor (`LB_Cine_BellHeadstock`, `TWA_Headstock`) and the rope actor (`LB_Cine_BellRope`, `TWA_BellRope`) and stores their rest transforms. The pivot P is the headstock's rest location (12420, 2000, 2880); the axis is its rest rotation applied to local Y (`BellSwingAxis` Pitch; Roll uses X). Each tick, with Q = FQuat(axis, angle): the bell component and the headstock each get location P + Q·(rest − P) and rotation Q·rest; the rope keeps its rest X and Y and takes the Z of P + Q·(rope rest − P), so it hangs vertically while its top follows the wheel rim (−30.9 / +40.9 cm at ±16°, because its top is 130 cm below the axle). All moves are `TeleportPhysics`, no sweep; at rest every piece gets its exact rest transform back (`SwingAboutAxle`, `RopeZAboutAxle`; tests `BellAxle`, `BellPendulum`, `BellSwingPieces`, `BellSwingsOnStrike`).
- A missing headstock or rope logs one Warning and the swing still runs (about the bell's own rest location; the rope step skipped). **All three must be Movable:** the bell's `Mesh` already was, and P17-5b set the headstock and rope to Movable. The owner judged the swing in P17-7 and kept it at every strike.

**`ULBCineAuthoringLibrary`** (authoring only, not used at run time). `UMovieSceneCameraCutTrack::bCanBlend` is a public member with a bare `UPROPERTY()`, so Python's `set_editor_property` and MCP can't set it, and without it `SupportsEasing` is false and the engine strips the cut's eases, so the cut back to the player's camera would be hard. `SetCameraCutTrackCanBlend` / `GetCameraCutTrackCanBlend` fix that: `unreal.LBCineAuthoringLibrary.set_camera_cut_track_can_blend(track, True)`, called right after the track is created and **before** its sections and eases (test `CameraCutCanBlendHelper`; S1a re-run 88/88).

**CVars and console** (non-shipping; the CVars are file statics in `LBCinematicSubsystem.cpp`)
- `lb.Cine.Enabled` (1; 0 stops a running cinematic at once with a restore and no must markers, and nothing starts afterwards), `lb.Cine.Rate` (1.0, clamped 0.25–16), `lb.Cine.NoEnd` (0; 1 makes `end` only restore and log "Cine: end suppressed (lb.Cine.NoEnd)", for review sessions) and `lb.Cine.Debug` (1 shows the sequence time, the next marker, the lock and the skip state on screen).
- Commands (`LBConsoleCommands.cpp`): `lb.Cine.Play <Id>` (Intro or Finale), `lb.Cine.Skip` (skips even when not skippable), `lb.Cine.Stop`, `lb.Cine.PlayAsset <LevelSequence path>` (plays any sequence through a temporary def, locked and skippable; for spikes and reviews).
- Log lines (`LogLB`): "Cine: play <Id> (…, N markers)", "Cine: marker '<label>' at <t> s", "Cine: skip at <t> s (N must markers fired)", "Cine: end -> CompleteGame". **Never Live Code `LBCinematicSubsystem.cpp`** (file-static CVars, like the storm FX and audio subsystems): close Unreal and use `Tools/build_and_test.ps1`.

**Audio roles** (`/Game/LastBell/Audio/Mix/`; built headless by `p17_assets.py` and `p16_2_assets.py`)
- **`SCL_LB_CineMusic`** is a child of `SCL_LB_Music`, so the user's music slider applies to the three cinematic cues (`MUS_LB_Cine_IntroText`, `MUS_LB_Cine_Finale`, `MUS_LB_Cine_Credits`: 2D, not looping, no attenuation, peak −3 dBFS; the owner's Freesound CC0 picks, D-120). `SMX_LB_User`'s Music adjuster must apply to children, so the slider reaches them.
- **`SMX_LB_CineFade`** is pushed by `mix:on`: Ambience, SFX, Voice **and Music** at volume 0 (fade in 4.0 s, fade out 1.0 s, duration −1, EQ off), with `bApplyToChildren` **false** on every adjuster. The Music adjuster therefore silences the game's drones (the TowerTop drone) but never the cinematic music, which sits in the child class `SCL_LB_CineMusic`.

**How the sequences are built** (`Tools/cine/p17_sequences.py`; D-115, R-78)
- **Headless Unreal Python with the editor closed** (`UnrealEditor-Cmd … -run=pythonscript`; environment variables `P17_MODE` `build|check`, `P17_REBUILD`, `P17_ONLY` `Intro|Finale`), because Sequencer authoring works from Python (the recipes are in `Tools/mcp/MCP_NOTES.md`, "Sequencer scripting"). It builds `LS_LB_Intro` and `LS_LB_Finale` from a spec in the script and saves only those two packages. **A build refuses to touch an existing sequence unless `--rebuild` (`P17_REBUILD=1`) is given**, so an owner's edit is never overwritten by accident; `check` reads everything back in a fresh process (366/366 at 11f8330) and writes `Docs/ArtTest/cine/p17_5a_check.json`. Every actor in the sequences is a spawnable, so they replay anywhere.
- **`LS_LB_Intro`** (30 fps, 0–37.0 s; retimed in 3.10: the four text cards hold 3.6 s with 0.5 s fades, 4.6 s each): `skip:1` at 0; cards at 0.8, 5.8, 10.8 and 15.8 s; black to 21.0 s, then the camera cuts to `Cam_Intro` (21.0–35.0 s, ease-out 1.5 s into the player's view) and the fade eases clear by 23.5 s; `strike:LB_StrikeTarget_Tower,1.0` at 25.0; `!tag:State.Event.Arrival` at 25.4 (stage 1 × 3, no drone); `card:Title` at 27.0; `!lock:None` at 35.5. `Cam_Intro` ends exactly at the player's eye at spawn (−2800, 0, 152.79), yaw 0; it starts as a crane-down 500 cm straight above it (pitch +6°, 30 mm easing to 28 mm), because the F0 survey showed that a camera 350 cm back would be inside the west cliff. The 2D music `MUS_LB_Cine_IntroText` plays 0–35.5 s (volume 0, 1 at 0.5 s, 1 at 33.0 s, 0 at 35.5 s).
- **`LS_LB_Finale`** (30 fps, 0–97.5 s; revision 3.2b, then 3.8 and 3.9): `mark:LB_Cine_FinaleMark,1.2`; `lock:Look` at 1.3; `look:LB_Cine_StairTop,1.0` at 1.5; `flash:1.0` at 3.6; `look:LB_Cine_Warden,1.0` at 9.5; `lock:Full` at 12.0; `bell:5x1` at 33.5; `mix:on` at 37.5; `card:End_1` at 41.5; `card:End_2` at 47.5; `skip:1` at 53.5 and `credits:40` one frame later; `!end` at 94.5. The Finale beat (stage 5 × 5, 2.0 s apart) and the storm's two Finale strikes come from the tag, not from markers.
  - **`WardenFigure`** (spawnable `SkeletalMeshActor`: `SK_Warden`, `ABP_Warden_C`, NoCollision, tag `LB_Cine_Warden`, `AlwaysTickPose`): hidden at `WP_TowerStairs_21`, walking from 1.0 s at 110 cm/s, visible from `Stair_F11_00` at 1.351 s (in sight about 3.5 s after the ring: the owner's rule that the Warden appears in under 5 s), arriving at the stop (12165, 2220, 2500) at 11.70 s facing +Y (`StopDistance` 80 cm in front of the player's eye). The ABP supplies locomotion; the stride sounds and the heavy breath loop are on the figure.
  - **The mask moment:** `AN_Warden_MaskLift` (slot `DefaultSlot`, 6.0 s) starts at 14.6 s; grip at 16.8 s, lifted 18.0 s, extended 19.2 s. At the grip the figure's mask slot `Fade` (`M_Warden_BellMetal`, Masked, `OpacityMask` = 1 − `Fade`) goes 0 → 1 on the same frame that `MaskProp` (`SM_LB_WardenMask`, `MI_Warden_BellMetal`) becomes visible and its attach moves from `head` (zero offset) to `hand_r` (Keep World); its `TellGlow` ramps 0 → 0.6 from lifted to extended. `Cam_Mask` (35 mm) cuts in at 12.5 s (ease-in 0.8 s) from (12165, 2440, 2720), holds on the mask centre, then pushes in from 17.0 to 19.2 s to the player's eye (12165, 2300, 2652), with the manual focus at 230, 210, then 25 cm. The picture goes black at 19.5–19.8 s as the mask meets the face (`SFX_LB_Step_Metal_02` at pitch 0.55 with `SFX_LB_Warden_Chain_02` at 0.7, then `SFX_LB_Warden_Breath_Slow` as the player's own breath, to 39.5 s) and returns at 24.5 s.
  - **The last view:** `Cam_WallTop` cuts in at 22.5 s at (6020, 1300, 1032), the `Apparition_Courtyard` station on the wall top (Z 800 + 232), aimed at the gate passage (yaw −167.51°, pitch −7.88°), at **70 mm**, with the post-process `MI_LB_PP_MaskView` (the eye slits: `M_LB_PP_MaskView`, one Custom HLSL node, 14 parameters, After Tonemapping, no overrides). The `Villager` (spawnable `SkeletalMeshActor`, CC0 Quaternius, hidden until 23.5 s) walks the gate axis from X −600 to 204 (at 36.0 s) and 250 (at 37.5 s) in `Walk_Candle` at the matched rate, then `Idle_Lantern_Loop`. It carries **the player's candle** (D-123): `CandleWax` and `CandleFlame` (the player's meshes and materials) and `CandleLight` (a PointLight, 10 cd at 1900 K, radius 600, no shadows, intensity keyed 12 times a second with a seeded 12 % flicker from 23.5 to 40.5 s), all attached to the villager's `hand_r`.
  - **Then:** `bell:5x1` at 33.5 s (heard from the tower), the world sound fading under the cards from 37.5 s, black at 38.5–40.5 s, `MUS_LB_Cine_Finale` 3.6–54.5 s, `MUS_LB_Cine_Credits` 53.5–94.5 s, the credits (40 s, skippable) and `!end` at 94.5 s.
- **Assets and sources.** `SM_LB_WardenMask` (`/Game/LastBell/Characters/Warden/Cine/`; all slot-1 faces, 9 islands, pivot at the `head` bind transform; imported with **import rotation roll 90, yaw −90**, set on the asset's import data and measured so a zero-offset attach to `head` lands on the skinned mask to 0.002 cm; Force Front X off, no Nanite, no collision) and `AN_Warden_MaskLift` (Blender-keyed on the V11.1 rig, because no Mixamo clip fit: R-79 and R-80 do not arise) come from `SourceArt/Warden/P17/`. The villager (`/Game/LastBell/Characters/Villager/`: `SK_LB_Villager` on its own skeleton, `AN_LB_Villager_WalkCandle` (the `Walk_Loop` with the right arm of `Idle_Lantern_Loop` frame 0, so the hand holds the candle), `AN_LB_Villager_IdleLantern`, two materials, textures darkened ×0.45 at 2048) comes from `SourceArt/Villager/` (CC0, committed). `DA_Cinematics` and `SMX_LB_CineFade` come from `p17_assets.py`, the credits from `make_credits.py` (`Docs/plans/p17_credits.json`), the level edits from `p17_level.py`.
- **Level edits** (P17-5b, Outliner folder `Cinematics`): `CINE_FinaleMark` at (12165, 2300, 2500), yaw −90, and `CINE_StairTop` at (12165, 1665, 2730), both `TargetPoint`; the tags `LB_Cine_Bell`, `LB_Cine_BellHeadstock` and `LB_Cine_BellRope`, with the headstock and rope set Movable; the `Note_Gatehouse` text changed; `EndingTrigger` deleted (census 3102 → 3103).

**Warden V11.1 (D-121).** The owner's new Warden replaces V5.5 in place: `SK_Warden` (8 slots; the skeleton, the 110 bones, the reference pose and the `mask` socket are unchanged), the three clips, the apparition mesh (`SM_LB_Warden_Apparition`, re-baked from the reweighted blend, 7,363 triangles) and the materials and textures, moved to `/Game/LastBell/Characters/Warden/V11_1/` (QA m5, 9f42465), with the project's tuning. The V11.1 robe is reweighted with the P13-4c round-3 parameters (`Tools/blender/warden/p13_reweight.py --src`), which keeps the wool-edge stretch at 16.2 / 17.6 / 30.7 / 33.1 against V5_5w2's 23.7 / 29.6 / 43.3 / 44.2 (the unweighted V11.1 gave 117 / 180 / 92 / 233). Steps W0–W5 are in plan section 3.6; the Interchange and `import_lod` notes are in `Tools/mcp/MCP_NOTES.md`.

**Tests** (suite **199/199** at the last full run recorded, after the V11.1 swap; the final run for the phase is in the plan's Results and `IMPLEMENTATION_PLAN`).
- Unit, `LastBell.Cine.*` (8): `ParseMarkers`, `MarkersCrossing`, `SkipFiresMustOnce`, `EaseAndYaw`, `CreditsSpeed`, `BellPendulum`, `BellAxle`, `CameraCutCanBlendHelper`. Also `LastBell.Warden.Stage6IsDormant`.
- Functional, `LastBell.Functional.Cine.*` (13): `IntroOnNewGame`, `NoIntroOnContinue`, `IntroSkip`, `FinaleOnBell`, `NoCheckpointDuringCinematic`, `BellSwingsOnStrike`, `BellSwingPieces`, `DisabledByCVar`, `MissingSequenceFailsSafe`, `SkipFadesUp`, `SkipClearsFade`, `EndWaitsForCreditsPastSequenceEnd`, and `Monastery.CinematicSetup` on the real level (the tagged actors exist once each, the last three Movable, `EndingTrigger` absent, `DA_Cinematics` and both sequences load, every marker parses, the must markers are present). Audio: `Audio.ArrivalBeat` and `Audio.GreatBellStrikeDelegate`.
- `RouteBot.Monastery` plays the intro and the finale at 8×, waits for the intro before driving, skips once the credits are skippable and expects `L_MainMenu` within 60 s of the ring. Every other functional test that opens `L_Monastery` constructs `LBPie::FCineSwitch(false)` (beside `FWardenSwitch` in `LBRouteBot.h`) so the intro doesn't lock the test's input (R-82); `MenuFlow` decides per test.

**Known limits and open items**
- **The GPU cost of the cinematic shots is not measured** (the finale close-up, the wall-top shot at 70 mm, the villager, the mask-view post-process; no instruction count was available): Phase 20 (`PERFORMANCE_BUDGET.md`).
- **Only the owner's eyes have judged the look:** the intro (P17-6) and the finale (P17-7, "rest is fine"), both in PIE. The mask-view post-process and the villager's colour are the likeliest to need a tweak: the owner's shot showed a pale villager, and plan 3.9 asked for the darkened textures' assignment to be confirmed in Unreal.
- **The cards, the credits roll and the skip prompt** used the engine font and no key glyphs in Phase 17. **Phase 18 restyled them** (EB Garamond and the `DA_UIStyle` colours; the prompt is "Hold [key] to skip" with the Interact key icon), and the pause menu and its effect on the bell were done there too (R-77 part 2, closed; section 18).
- **`Tools/warden/check_warden.py` was deleted in P17-9** (it expected the V5.5 numbers; R-87 closed). For V11.1 use `w3_swap_v11_1.py` `check` (`Docs/ArtTest/warden/w5_check.json`).
- **Getting control back on the tower** exists only with `lb.Cine.NoEnd 1`. In play, `!end` always goes to `CompleteGame` and the menu.
- **`BP_EndingTrigger` and `WBP_Ending` are deleted** (P17-9, owner-approved), as are the old V5.5 `M_Warden_*`/`MI_Warden_*` materials, the 20 `T_Warden_*` textures under `Characters/Warden/Textures/` and `WSpawn_Tower` (census 3103 → 3102). `Characters/Warden/Materials/` keeps only the apparition materials.

## 18. UI and settings (Phase 18, D-126…D-134; as built)
Spec and results: `Docs/plans/P18_UI_SETTINGS.md` (sections 0–10, then "Results"). Code: `Source/LastBell/UI/` (`LBUITypes`, `LBUILogic`, `LBUIStyle`, `LBUISubsystem`, `LBMenuWidgetBase`, `LBMainMenuWidget`, `LBPauseWidget`, `LBSettingsWidget`, `LBCreditsWidget`, `LBCreditsLayout`, `LBBrightnessWidget`, `LBConfirmWidget`, `LBKeyIconWidget`, `LBHUDWidget`, `LBGraphicsSettings`, `LBKeyBindings`, `LBLoadingScreen`, `LBUIBuild`), `Systems/LBGameInstance.*`, `Systems/LBUserSettings.*`, and the changes to `Audio/`, `Cinematics/LBCinematicWidget.*`, `Character/LBCameraFeelComponent.*`, `Save/LBSaveSubsystem.cpp` and `Systems/LBPlayerController.*`. Records: `Docs/ArtTest/ui/p18_a1_assets.md` (the downloads), `Docs/ArtTest/cine/p18_menu_drift.md` (the menu video). Tools: `Tools/ui/` (`p18_2_assets.py`, `p18_3_assets.py`), `Tools/cine/p18_*`, `Tools/audio/prep/prep_ui_sounds.py`.
- **Purpose:** the main menu, the pause menu, the settings, the credits, the brightness screen, the loading screen and the HUD, all keyboard and mouse (D-126).
- **Boundaries:** the UI reads and writes settings and calls the save subsystem's flows (`StartNewGame`, `ContinueGame`, `ReturnToMainMenu`); it never edits the world state, the Warden or the storm. Every widget is a C++ tree built in `NativeOnInitialized` (no WBP asset, D-127, D-132), styled from one data asset. Not built: gamepad and controller icons, subtitles and localisation, save slots (D-126; plan section 10).

**`ULBUISubsystem`** (`ULocalPlayerSubsystem`; `ULBUISubsystem::Get(World)` finds the first local player's)
- **The screen stack.** `PushScreen(ELBScreen, ClassOverride)` creates the widget (`DefaultClassFor` maps `MainMenu`, `Pause`, `Settings`, `Credits`, `Brightness` and `Confirm` to their C++ classes), adds it to the viewport at Z order 500 + 10 per screen and makes it the top. A `Confirm` overlays the screen below (which stays visible and stops taking hits); any other screen collapses the one below. `PopScreen`, `PopToAndIncluding` and `ClearScreens` restore the one below, or, when none is left, unpause (if the UI paused) and restore the input mode. A level travel destroys the viewport widgets, so every query first drops the stale entries (`PruneStale`). **Never Live Code `LBUISubsystem.cpp`:** it holds file-static state.
- **Back and Escape.** `HandleBack()` always returns true, so Escape never leaks into gameplay. The top screen handles Back; with no screen open an inspection closes first (`ULBInspectionComponent::RequestClose`), and otherwise the pause menu opens when `CanOpenPause` allows it. In game input `IA_Pause` (bound in `ALBPlayerController::SetupInputComponent` to `PauseAction`, `Started`) calls `HandleBack`; while a screen is up the input mode is UI-only, and the widget's own `NativeOnKeyDown` handles Escape. The main menu's Back does nothing; the first-launch brightness screen ignores Back.
- **Input mode.** The top screen means a visible cursor and UI-only input with the screen focused (no mouse lock). With no screen: a menu map (`ALBPlayerController::bMenuMode`, forwarded through `SetMenuMode`) gets UI-only with a cursor, anything else game-only. `ALBPlayerController::BeginPlay` pushes the main menu when `HUDWidgetClass` is a `ULBMenuWidgetBase` (`BP_MenuPlayerController.HUDWidgetClass` is `ULBMainMenuWidget`), and creates `ULBHUDWidget` otherwise.
- **The brightness gate.** Pushing the main menu calls `ApplyBrightnessGate()`: when `ULBUserSettings::bBrightnessCalibrated` is false, the brightness screen goes on top (`OpenBrightness(true)`, first-launch mode).
- **UI sounds.** `PlaySound(ELBUISound)` loads the style's sound (hover, select, back, slider tick: `SFX_LB_UI_Hover`, `_Select`, `_Back`, `_Tick` in `/Game/LastBell/Audio/UI/`, class `SCL_LB_UI`) and plays it with `PlaySound2D(..., bIsUISound = true)`, so it plays while paused. Requests are counted for the tests whether or not a device or asset exists.
- **Focus loss.** The subsystem listens to `FSlateApplication::OnApplicationActivationStateChanged`. When the window loses focus the skip hold is cancelled, and during play (no screen open, `CanOpenPause`) the pause menu opens. The editor never pauses on focus loss unless the test hook `bPauseOnFocusLossInEditor` is set (R-98).
- **Flows.** `StartNewGameFlow` (a confirm "This will erase your progress." when `HasValidSave()`), `ContinueFlow`, `ReturnToMainMenuFlow` (confirm "Unsaved progress since the last checkpoint will be lost."; on confirm the world unpauses first, then `ReturnToMainMenu()`, which keeps the save), `QuitGameFlow` (confirm), `OpenSettings`, `OpenCredits`. `OnPauseChanged` broadcasts when the UI pauses or unpauses.

**The widgets** (all `ULBMenuWidgetBase` unless noted; the base builds a root overlay, a dimming backdrop and the item list)
- **`ULBMenuWidgetBase`:** rows are `Button`, `Toggle`, `Choice`, `Slider` and `KeyBinding` (`AddButtonItem` and the others). Up/Down select (wrapping, skipping disabled rows), Left/Right adjust, Enter or Space activates, Escape goes back. A row's mouse hover and click go through a transparent, non-focusable `ULBMenuButton` so the keyboard focus stays on the screen. The selected row shows the candle flicker (`LBUILogic::CandleFlicker`, speed and amplitude from the style, driven by the widget's real-time tick, so it runs while paused). A slider reports a transient value while dragged and a final one on release. A `Choice` row can have `SelectableCount` below its option count, so a display-only option (the preset row's "Custom") is shown but never stepped to.
- **`ULBMainMenuWidget`:** the title and Continue (only when a save exists), New Game, Settings, Credits, Quit, over the menu video: `MS_LB_MenuDrift` on a `UMediaPlayer` (looping) and `UMediaTexture` in a full-screen image under a 45 % dark plate. With no video or if it cannot open, `T_LB_MenuStill` with a 60 s Ken-Burns drift; with neither, a plain dark background (logged).
- **`ULBPauseWidget`:** "Paused", Resume, Settings, Return to main menu, Quit to desktop, over a `UBackgroundBlur` (strength 6) and a 60 % dim.
- **`ULBSettingsWidget`:** five tabs (Tab or Shift+Tab, Q and E, PageUp and PageDown switch them).
  - Graphics: the quality preset, the ten groups and the resolution scale. Display: window mode, resolution, VSync, the frame-rate limit, the Show FPS toggle and "Brightness...". Graphics and Display end in Apply and Revert; Back discards unapplied changes.
  - Audio: six sliders (Master, Effects, Ambience, Music, Voice, Interface) that apply live, through the `ULBUserSettings` volumes (section 16).
  - Controls: mouse sensitivity, invert Y, head bob, one key row per action and "Reset to defaults".
  - Accessibility: field of view, motion blur, film grain, high-contrast prompts and "Show brightness screen at next launch". Audio, Controls and Accessibility save at once.
- **`ULBBrightnessWidget`:** a symbol barely visible on a dark field and a gamma slider that applies live; Confirm saves the gamma and sets `bBrightnessCalibrated`. Opened from Display, Back restores the gamma it had on opening.
- **`ULBConfirmWidget`:** a title, a message, a countdown and two buttons, from an `FLBConfirmRequest` (`bDanger` draws Confirm in the danger colour and starts on Cancel; `TimeoutSeconds` counts down in real time and then answers Cancel, or Confirm when `bTimeoutConfirms`; Back answers Cancel). It answers exactly once and is removed before its callback runs.
- **`ULBCreditsWidget`** plays the same roll as the ending from `DA_Cinematics.Credits`, through `FLBCreditsRoll` in `LBCreditsLayout` (the layout code `ULBCinematicWidget` used to hold; the two share it).
- **`ULBKeyIconWidget`:** one key as the style's icon (`T_Key_<Key>`, 53 keys) or, with no icon, a rounded key-cap with the key's name. It shows a fixed key or follows an action (`SetBoundAction`, `SetBoundInputAction`) and refreshes on `LBKeyBindings::OnBindingsChanged` and on settings changes; it binds in `NativeOnInitialized`, because `NativeConstruct` never runs for a widget outside the viewport.
- **`ULBHUDWidget`** (not a menu screen; D-132): the crosshair dot (brighter and larger over something usable), the interact prompt (a key icon bound to Interact plus the interactable's text; a denied text such as "Locked" shows without the key), the objective at the top left, "Lighting..." while the candle relights, the inspection overlay (name, body, the close hint) and the **FPS counter** (`bShowFPS`; "60 FPS" at the top right in the small font and the dim colour, smoothed over 0.5 s, refreshed four times a second from Slate's real frame time, hidden while a screen is open). It binds the pawn's interactor, candle and inspection (retrying until the pawn exists, and again on possession) and the objective subsystem itself. High-contrast prompts draw the prompt white on `HighContrastPlate` with an outline (`ULBUIStyle::GetPromptLook`).
- **`ULBCinematicWidget`** (P17, restyled): the cards, the credits and the skip prompt read the style's fonts and colours; the prompt is "Hold [key] to skip" with the current Interact key icon (`SetSkipPromptText` is kept for the settings and the tests only).

**`ULBUIStyle` and `DA_UIStyle`** (`/Game/LastBell/UI/DA_UIStyle`, linked in `Config/DefaultGame.ini` as `ULBGameSettings::UIStyle`)
- **Contents:** four `UFont` soft references (EB Garamond Regular, Italic, SemiBold, Bold: `F_LB_EBGaramond_<Weight>`, each a composite font holding one `FF_LB_EBGaramond_<Weight>` face, with `OFL.txt` beside them); the colours Ink, Dim, Accent (candle amber), Plate, Danger and `HighContrastPlate`; sizes at 1080p (title 96, heading 40, item 34, body 24, small 18; the viewport's DPI scale does the rest); the flicker (1.6 cycles a second, amplitude 0.3); the title text; `KeyIcons` (`TMap<FKey, TSoftObjectPtr<UTexture2D>>`); the four UI sounds; the menu video (`MS_LB_MenuDrift`), the still (`T_LB_MenuStill`) and the brightness symbol (`T_LB_BrightnessSymbol`).
- **`ULBUIStyle::Resolve()` never returns null:** with no style linked or loaded it returns the class defaults (the engine's default font, no icons, no sounds) and logs once, so a missing asset degrades and never crashes.
- **The loading screen does not use the style** (it is Slate-only; see "Startup and loading").

**Settings and input**
- **`FLBGraphicsSettings`** (a wrapper over `UGameUserSettings`): the overall preset 0 to 3 (Low, Medium, High, Epic), ten groups (`ELBGraphicsGroup`: view distance, anti-aliasing, shadows, global illumination, reflections, post-processing, textures, effects, foliage, shading), the resolution scale (50 to 100 %), window mode, resolution, VSync and the frame cap (30, 60, 90, 120, 144 or Unlimited). **Custom** is shown when the groups differ (`LBUILogic::DetectPreset` returns −1; the engine's Cinematic level 4 also reads as Custom); the preset row steps only Low to Epic (`SelectableCount` 4), so Epic wraps to Low. Resolutions come from `GetSupportedFullscreenResolutions`, clamped to the desktop for the windowed modes, with the current one always listed.
- **Apply, Revert and the keep dialog.** The tab opens with a snapshot (`FLBGraphicsSnapshot`). Setters change the pending user settings only. `Apply(Before)` runs `ApplySettings(false)` and returns whether the window mode or the resolution differs from `Before`. If not, the video mode is confirmed. If so, the settings widget shows a confirm "Keep these display settings?" with `TimeoutSeconds` 15 (`LBUILogic::KeepDialogSeconds`): Keep calls `Confirm()` (confirms and saves); Revert, Back or the timeout calls `Revert(Before)` and rebuilds the tab. `Revert` writes the snapshot back and applies it. The Revert button and Back (while no key is being captured) only write the baseline snapshot back into the pending settings (`Restore`), discarding what was not applied.
- **`ULBUserSettings` additions** (`config=GameUserSettings`, so the file is `GameUserSettings.ini`): `Gamma` (1.8 to 2.6, default 2.2, pushed into `GEngine->DisplayGamma`), `FieldOfView` (70 to 110, default 90: the camera's value before Phase 18), `bMotionBlur` (false), `bFilmGrain` (true), `bHighContrastPrompts` (false), `bShowFPS` (false) and `bBrightnessCalibrated` (false). Each setter clamps, saves and broadcasts the static `OnUserSettingsChanged()`. Sliders use `Set…Transient` while dragged (applied, not saved) and the screen saves on release. `ResetControlsToDefaults()` resets sensitivity, invert Y and head bob. `ULBCameraFeelComponent` applies the field of view (the user's value plus the sprint widening) and, as overrides on the player camera's own post-process settings, motion blur (0.5 on, 0 off) and film grain (the override only when off, forcing 0); the level volumes are not touched.
- **Rebinding** (`LBKeyBindings`, Enhanced Input user settings, R-92). Config: `DefaultInput.ini` `[/Script/EnhancedInput.EnhancedInputDeveloperSettings]` sets `bEnableUserSettings=True` and **`+DefaultMappingContexts=(InputMappingContext=IMC_LB_Gameplay, ..., bRegisterWithUserSettings=True)`**: without the registration the user settings do not know the context and `FindCurrentMappingForSlot` finds nothing (the controller still adds the IMC itself). `IMC_LB_Gameplay` carries player-mappable names with display names: `LB_Move_Forward`, `LB_Move_Back`, `LB_Move_Left`, `LB_Move_Right`, `LB_Sprint`, `LB_Crouch`, `LB_Interact`, `LB_Candle`, `LB_Pause` (`LBUILogic::MappingNameFor`; Move is four separate keys). `Rebind` refuses a bad key (gamepad, touch, axes, the wheel, the console key; the mouse buttons for Pause), checks the other actions for a conflict (the engine accepts duplicates; Pause counts), calls `MapPlayerKey` on the first slot, then `ApplySettings` and `SaveSettings`. The settings screen captures the next key press; Escape cancels, except on the Pause row. "Reset to defaults" resets the key profile and the controls.
  - **The Crouch rule:** C is the rebindable key. Ctrl is a second, **fixed** key mapped in `IMC_LB_Gameplay` without a mapping name, so the Controls tab never lists or changes it and rebinding Crouch never removes it.
  - **`IA_Pause`** (Boolean, a Pressed trigger, Escape) has `trigger_when_paused` on: without it an Enhanced Input action does not fire while the game is paused and Escape could not resume.
  - **`IMC_LB_Inspect` keeps its fixed keys.** Prompts follow the live mapping (`GetKeyForInputAction` takes the first non-gamepad key of the action).

**Pause (D-128)**
- **What pauses.** `OpenPause()` cancels the cinematic skip hold, calls `SetGamePaused(true)` and pushes the Pause screen; `ClosePause()` pops every screen and unpauses. The world, the Warden, the storm, `ULBAudioSubsystem`'s schedule (thunder, tolls, the great bell) and the cinematics freeze with the world: the level-sequence actor ticks with the world, and `ULBCinematicSubsystem` and the audio subsystem are not tickable when paused. Only UI sounds play.
- **When it is refused** (`CanOpenPause`): no game world or controller, already paused by the UI, paused by something else, on a menu map or with the main menu open, a level travel pending, a checkpoint restore pending, no player character, or the player dead (the death fade). It is allowed during cinematics, inspection (Escape closes the note first, then the next press pauses) and chases.
- **The P16-6 revert (R-77 part 2, R-94).** P17 removed the ending's pause, so the workaround is gone: `IsTickableWhenPaused()` is false, `FScheduled::bUnpausedClock` and the unpaused-clock scheduling are removed, and great-bell strikes are ordinary game sounds. The finale still plays from the tag: a beat with `FirstDelay` ≤ 0 plays its first strike inside `HandleStateChanged`.
- **The `bIsUISound` rules.** An audio component marked as a UI sound keeps playing while the world is paused, and `UGameplayStatics::SpawnSound2D` and `CreateSound2D` **default to a UI sound**. So every game 2D sound the audio director makes (`Play2D` and the weather and music loops of `FLBAudioLoop`) calls `SetUISound(false)` right after creation and pauses with the world. Only `ULBUISubsystem::PlaySound` and the sounds of `SCL_LB_UI` (the only sound class with `bIsUISound` true) play under a pause. Any new 2D sound must follow the same rule.

**Startup and loading**
- **`ULBGameInstance`** (`GameInstanceClass` in `DefaultEngine.ini`; the first custom game instance): `Init` applies the saved gamma before anything is drawn and before the brightness gate is decided, and subscribes to `PostLoadMapWithWorld`.
- **The loading screen** (`LBLoadingScreen`, D-133) is **armed by the save subsystem**: `NewGame`, `ContinueGame` (not the death reload) and `OpenMainMenuMap` call `ArmForTravel()` before `OpenLevel`, and `ULBGameInstance` calls `OnTravelFinished()` after the map loads. It gives the engine's movie player attributes with a minimum display of 1.0 s, auto-complete when loading completes and no skip: a Slate widget with a black field, the title and a small flickering candle (the engine font, because the movie player draws it on its own thread). The editor does not play loading screens, so there `ArmForTravel` builds the attributes and reports false.
- **True fullscreen by default** (D-130): `Config/DefaultGameUserSettings.ini` sets the three fullscreen-mode keys to 0, `bUseDesktopResolution` and a 0×0 resolution, with **`Version=5`**, because the engine ignores the window keys unless the version equals `UE_GAMEUSERSETTINGS_VERSION`. A saved `GameUserSettings.ini` overrides every key.

**The menu video** (S1, D-129; the full record is `Docs/ArtTest/cine/p18_menu_drift.md`)
- **The shot:** `LS_LB_MenuDrift` (`Tools/cine/p18_menu_drift.py`, built headless like the P17 sequences, check 102/102): 40.0 s at 30 fps, one spawnable CineCamera, a courtyard view from (700, −300, 300) to (1100, −300, 300), yaw 4.5 → 9.5°, pitch 6.5°, a ping-pong with zero tangents at 0, 20 and 40 s so the loop has no camera seam.
- **The render:** `Tools/cine/p18_render_menu_drift.ps1` writes a Movie Render Queue manifest (`p18_mrq_manifest.py`: a PNG sequence at 1920×1080, 30 fps, 150 warm-up frames) and runs `UnrealEditor-Cmd -game` with `-EnablePlugins=MovieRenderPipeline` (the project file does not enable the plugin) and the `MoviePipelineGameMode` (no pawn and no gameplay). It **opens a game window, so the owner must be present**. **`lb.Cine.Enabled 0` (`-dpcvars` and `-ExecCmds`) is required**, or `ULBCinematicSubsystem` takes the load for a New Game and the intro's black fade covers every frame (the first test render was black). **The render process crashes on the GPU thread at shutdown** (an access violation in the RHI under a Niagara GPU dispatch) after every frame is written; the script counts the frames and treats the crash as a warning (R-91).
- **The encode:** `p18_encode_menu_drift.ps1` runs ffmpeg (libx264, preset slow, CRF 18, High profile, yuv420p, BT.709, 30 fps, no audio) and refuses a gap or blank frames. The result is `Content/Movies/LB_MenuDrift.mp4` (68.7 MB, Git LFS). The frames stay under `Saved/` (git-ignored).
- **In the game:** `MS_LB_MenuDrift` is a `UFileMediaSource` with the path `./Content/Movies/LB_MenuDrift.mp4` (a leading `./` is relative to the project directory); `DefaultGame.ini` stages `Movies` and `LastBell/UI/Fonts` as non-UFS (`DirectoriesToAlwaysStageAsNonUFS`). Playback in a packaged build is unverified (R-96).

**Housekeeping**
- **Module layout:** `Source/LastBell/UI/` is new (the files above). `LastBell.Build.cs` adds `MoviePlayer` and `MediaAssets` (UMG, Slate and SlateCore were there). `Systems/` gains `ULBGameInstance`. `LastBellTests.Build.cs` sets **`bUseUnity = false`** (the older test files keep helpers with the same names in anonymous namespaces, and a unity chunk that merges two of them fails to compile; which files share a chunk changes whenever a file is added) and adds UMG, Slate and SlateCore.
- **`Tools/build_and_test.ps1 -Filter <prefix>`** (D-131) runs only the matching tests (for example `-Filter LastBell.UI`) while a task is iterated; with no filter it runs the whole suite, which is what a milestone report uses.
- **Retired:** `WBP_HUD`, `WBP_Inspect` and `WBP_MainMenu` are no longer used; they stay in `Content/LastBell/UI/` until the owner approves their deletion at the phase review.

**Tests** (suite **234 passed, 0 failed** at the last recorded full run, 2026-11-11 22:39, after c7296fd; the final run for the phase is in `IMPLEMENTATION_PLAN`)
- **Unit and content, `LastBell.UI.*` (16):** `Logic.Clamps`, `Logic.PresetDetection`, `Logic.FrameLimitOptions`, `Logic.ResolutionsClampedToDesktop`, `Logic.KeepTimer`, `Logic.CandleFlicker`, `Keys.IconLookup`, `Keys.RebindConflicts`, `Settings.ClampsAndPersistence`, `Settings.BrightnessFirstLaunchFlag`, `Settings.GraphicsPresetAndCustom`, `Settings.GraphicsApplyPersists`, `Style.PromptLook`, `Loading.Attributes`, `Content.KeyIconsForEveryGameplayKey` and `Config.DefaultGameUserSettingsIsTrueFullscreen`.
- **Functional, `LastBell.Functional.UI.*` (17):** `MainMenu.ContinueHiddenWithoutSave`, `MainMenu.NewGameConfirmsWhenSave`, `Pause.FreezesWorld`, `Pause.FreezesCinematic`, `Pause.BellStopsAndResumes`, `Pause.BlockedDuringTravelAndDeath`, `Pause.EscapeClosesInspectionFirst`, `Rebind.InteractChangesPromptAndSkip`, `Settings.FOVApplies`, `Settings.TabsApplyAndPersist`, `Settings.PresetCyclesFromEpicToLow`, `Brightness.FirstLaunchGate`, `Confirm.KeepDialogRevertsOnTimeout`, `Credits.RollsFromCinematicCredits`, `HUD.PromptKeyAndObjective`, `HUD.ShowFPSToggle` and `Loading.ScreenShownOnTravel`. `Flow.MenuFlow` and `Flow.MenuToGameInput` run against the C++ menu (`MenuToGameInput` sets `bBrightnessCalibrated` for its session). `RouteBot` does not press Escape.

**Known limits and open items**
- **Unmeasured cost:** the menu video's decode and the UI (the pause blur, the HUD counter) have no readings: Phase 20 (`PERFORMANCE_BUDGET.md`, R-97).
- **Packaged behaviour is unverified:** the loading screen, the video, the non-UFS staging, true fullscreen (R-96). The alt-tab pause acts only in a standalone game (R-98).
- **Needs the owner's eyes and hands:** the menu's look and its video loop, the pause blur, key rebinding in a session and across a restart, the first-launch brightness screen, Escape during the intro and the finale (R-92, R-90).
- **No hard asset references:** the UI reaches its assets through the `DA_UIStyle` soft references and the `UIStyle` project setting; the main menu class is set on `BP_MenuPlayerController`.
