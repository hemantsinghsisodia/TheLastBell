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
                ULBPlayerTuningData (DA_PlayerTuning), LBPlayerTypes (ELBGait + pure logic structs),
                ULBCameraFeelComponent, ULBFootstepComponent, ULBCandleComponent, ULBInspectionComponent (P3)
  Components/   ULBInteractorComponent, ULBInteractableComponent                 (P1)
                ULBInspectableComponent                                           (P3)
  Puzzles/      ULBSequencePuzzleComponent, ULBDialComponent, LBPuzzleLogic (pure logic)  (P4)
  Objectives/   ULBObjectiveChainData, ULBObjectiveSubsystem                     (P1)
  Save/         ULBSaveGame, FLBActorSaveRecord, FLBSaveIdRegistry, ULBSaveSubsystem, ULBSaveStateComponent, ALBCheckpoint (P1)
  AI/           ALBWarden, ALBWardenController, State Tree tasks/conditions      (P5)
  Systems/      ULBUserSettings (MouseSensitivity, bInvertY, bHeadBob; config=GameUserSettings) (P3)
Source/LastBellTests/   (Editor target only) unit tests, MicroSlice, RouteBot.*, WalkPath.*, PlayerFeel.*, test helpers
```
Runtime dependencies are Core, CoreUObject, Engine, InputCore, EnhancedInput, GameplayTags, UMG, DeveloperSettings (P2) and PhysicsCore (P3, footstep surfaces). `UnrealEd` is used only by `LastBellTests`. AIModule, NavigationSystem, StateTreeModule and GameplayStateTreeModule are added in Phase 5.
There is **no custom GameInstance**, because GameInstance subsystems don't need one. There's no static helper library until a real shared helper exists.

## 3. Framework
| Class | Base | Responsibility | Not responsible for |
|---|---|---|---|
| `ALBGameMode` | `AGameModeBase` | Sets default classes and holds the objective chain asset property. Spawns the player at the pending checkpoint transform (overrides `ChoosePlayerStart` and the spawn transform). On player death, calls `SaveSubsystem.LoadLastCheckpoint()` | Progression logic |
| `ALBPlayerController` | `APlayerController` | Adds Input Mapping Contexts, creates the HUD widget from a class property. `bMenuMode` / `SetMenuMode()` switches to UI-only input with the cursor (menus, ending); it's only applied when menu mode is on. Pause comes in Phase 3+ | Gameplay rules |
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

Input uses Enhanced Input. Phase 1 has `IA_Move`, `IA_Look` and `IA_Interact` in `IMC_LB_Gameplay`. Phase 3 adds `IA_Sprint` (hold), `IA_Crouch` (hold), `IA_Candle`, plus `IA_InspectRotate` and `IA_InspectExit` in `IMC_LB_Inspect`. The inspect context is pushed by `ALBPlayerController` during inspection. `IA_Pause` comes in Phase 18. Sensitivity and invert-Y (`ULBUserSettings`) are applied in the character's look handler.

## 5. Interaction
There is a single path, **`ULBInteractableComponent`**. Adding it to any actor makes that actor interactable, and it's the only thing the player knows about.
- Properties: `PromptText`, `DeniedPromptText` (shown when focused but not usable, P2), `bEnabled`, `RequiredStateTags` (all must be present), `GrantedStateTags` (added on interact, via `AddStates`), `bSingleUse`, `ConsumedStateTag` (persists single use as a tag), `bInspectOnInteract` (P3: interacting opens inspection; the grant happens on close if the inspectable is kept).
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
- **Death** is just `LoadLastCheckpoint()`. **New Game** is `DeleteSave`, then `ResetState`, then `OpenLevel`. A corrupt save or a `SaveVersion` mismatch is treated as no save: it's logged and Continue is hidden.
- **Not saved:** the Warden (rebuilt from stage tags and respawned at a designer point for each checkpoint), transient AI state and physics props.

Not built: multiple slots, free saving or whole-world serialization.

## 8. Warden AI (Phase 5, outline only)
- `ALBWarden : ACharacter` uses `BP_Warden` for the mesh, animation and audio, and is controlled by `ALBWardenController : AAIController`.
- It runs a **State Tree** via `UStateTreeAIComponent`, using the AI schema and starting logic on possess. The states are Dormant, Scripted, Patrol, Investigate (including a suspicious look-around), Search (including the lost-target case), Chase, Attack and Return. The controller forwards `OnTargetPerceptionUpdated` to the State Tree as events plus a context struct (last-known location and stimulus strength).
- **AI Perception** uses sight and hearing, with detect-neutrals on and the player registered as a source. Noise is raised with `UAISense_Hearing::ReportNoiseEvent(Instigator, Loudness, MaxRange, FName Tag)`, and world events use the mechanism actor as the instigator. The Warden knows only what it perceives. The Scripted state ignores perception.
- The **stage source of truth** is the `State.Warden.Stage.N` tags, added by story events. State Tree conditions read them directly, and a separate escalation component is only added if Phase 5 proves it's needed.
- There's no EQS at first. Search uses designer-placed `ALBSearchPoint` actors, nearest first. Debugging uses `lb.Warden.Debug` and the Gameplay Debugger.
- Stages 1–2 are scripted events and a non-AI silhouette. The AI pawn exists from stage 3.

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
  - Warden stand-ins (Phase 2): `BP_WardenSilhouette` (stages 1–3, no AI) and `BP_WardenPlaceholderKill` (stages 4–5).
  - All of these share the pattern: snap to state at BeginPlay, bind `OnStateChanged`, unbind at EndPlay. A shared base (`ALBTagReactiveActor`) was considered and deferred (D-032).
- `Puzzles/` has one Blueprint per puzzle. They communicate only through WorldState tags.
- Scripted beats live in small `BP_Event_*` actors, not in Level Blueprints.
- UI: `WBP_HUD` (prompt and objective) from P1. `WBP_MainMenu`, `WBP_Ending` and `BP_EndingTrigger` from P2. `WBP_Pause` and `WBP_Settings` come later.

**Blueprint rule:** a Blueprint never reaches into another Blueprint's internals. Communication goes through tags, components or delegates.

## 11. Maps
- `L_MainMenu` holds the menu (`BP_MenuGameMode`, `WBP_MainMenu`). It's the game's default map. Packaged builds cook exactly `L_MainMenu` and `L_Monastery` (`MapsToCook`), never the test maps.
- `L_Monastery` is a **non-World-Partition** persistent level. In Phase 2 it's ONE level with Outliner folders per area (D-023). A split into per-area sublevels or level instances (D-013) is decided in Phase 6/7, once streaming needs can be measured. The greybox layout is in `GREYBOX_SPEC.md`.
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
- **Regression maps and functional tests:** `L_Test_MicroSlice` (`LastBell.Functional.MicroSlice`, `RouteBot.MicroSlice`). `L_Monastery` is covered by `RouteBot.Monastery`, which plays the whole objective chain through the real interactor, death and restore at CP_TowerBase, then the ending's travel to the menu. **Rerun RouteBot after any gameplay or content change.**
- **Console commands** (development builds only): `lb.State.Add <Tag>`, `lb.State.Dump`, `lb.NewGame`, `lb.Checkpoint.Load`, `lb.Kill` (death path), `lb.Menu`, `lb.CompleteGame`, and later `lb.Warden.Debug`.
