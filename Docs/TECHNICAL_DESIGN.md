# THE LAST BELL — Technical Design

Status: Phase 0 draft (architecture only, nothing implemented). Engine: UE 5.8.3 launcher build, Win64, DX12 SM6.
Source of truth for architecture. Any deviation must be recorded in `DECISIONS.md` (see rule 66 of the directive).

## 1. Principles
- **Composition over inheritance.** Actors get behavior from components and interfaces, not deep class trees.
- **C++ owns systems, Blueprint owns content.** C++ for framework, reusable components, persistent state, AI foundation. Blueprint for puzzles, level scripting, designer tuning, VFX/cinematic hooks.
- **State is tags.** World progression is a set of Gameplay Tags; systems react to tag changes rather than to each other.
- **No god classes, no manager actors.** Global services are Subsystems with narrow APIs.
- **No hard asset references in C++.** Assets come through `UPROPERTY` defaults on Blueprint subclasses, Data Assets, or `TSoftObjectPtr`.
- **Simplest thing that satisfies the design.** Every system below names what it deliberately does *not* do.

## 2. Module layout
One runtime module, added in Phase 1: `Source/LastBell/` (prefix `LB`). No editor module until a real editor-only need appears.

```
Source/LastBell/
  LastBell.Build.cs  LastBell.h/.cpp  LBGameplayTags.h/.cpp  LBLog.h
  Systems/      ALBGameMode, ULBGameInstance, ULBWorldStateSubsystem
  Character/    ALBCharacter, ALBPlayerController
  Components/   ULBInteractorComponent, ULBInteractableComponent, ULBFootstepComponent, ULBLightSourceComponent
  Interaction/  ILBInteractable, FLBInteractionContext
  Objectives/   ULBObjectiveSubsystem, ULBObjectiveData (UPrimaryDataAsset)
  Save/         ULBSaveGame, ULBSaveSubsystem, ILBSaveable, ALBCheckpoint, ULBSaveIdComponent
  AI/           ALBWardenController, ULBWardenEscalationComponent, StateTree tasks/conditions
  Utility/      ULBStatics (small Blueprint function library), debug CVars
```

Build dependencies: Core, CoreUObject, Engine, InputCore, EnhancedInput, GameplayTags, AIModule, NavigationSystem, StateTreeModule, GameplayStateTreeModule, UMG (prompt widget base only).

## 3. Framework
| Class | Base | Responsibility | Not responsible for |
|---|---|---|---|
| `ALBGameMode` | `AGameModeBase` | Default classes; on player death asks SaveSubsystem to reload last checkpoint | Progression logic, objectives |
| `ALBPlayerController` | `APlayerController` | Adds Input Mapping Contexts, owns HUD widget, pause | Gameplay rules |
| `ULBGameInstance` | `UGameInstance` | Lifetime host for GI subsystems; holds active save slot name | Game state (lives in subsystems) |
| `ULBWorldStateSubsystem` | `UGameInstanceSubsystem` | Canonical `FGameplayTagContainer` of world state (`State.*`); `AddState/RemoveState/HasState`; `OnStateChanged` delegate | Deciding *why* states change |

`ULBWorldStateSubsystem` is the progression backbone: rituals, doors unlocked, Warden stage are all tags. It lives on the GameInstance so it survives map travel (Main Menu → gameplay map).

## 4. Player
`ALBCharacter : ACharacter` — first-person camera on a spring-less `UCameraComponent` attached to capsule; **no full-body mesh** in Phase 1 (arms/hands deferred until justified).
Components (all `UActorComponent`, reusable, individually testable):
- `ULBInteractorComponent` — camera-forward sphere trace on a dedicated `Interaction` trace channel at ~10 Hz plus on input; tracks focused target; calls `ILBInteractable`. Broadcasts `OnFocusChanged(Target, PromptText)` for the HUD.
- `ULBFootstepComponent` — distance-based step cadence (walk/sprint/crouch), physical-surface lookup → sound (data table `DT_Footsteps`), and `UAISense_Hearing::ReportNoiseEvent` with loudness by gait.
- `ULBLightSourceComponent` — lantern on/off, intensity curve, optional flicker profile. Placed on the character, reusable on any actor.
- Movement tuning (walk/sprint/crouch speed, accel, decel, camera smoothing) lives in `UCharacterMovementComponent` defaults on `BP_LBCharacter` — no custom movement component unless Phase 3 proves it necessary.
- Stamina: **not built** until Phase 3 playtest justifies it.

Input: Enhanced Input. Actions `IA_Move, IA_Look, IA_Interact, IA_Sprint, IA_Crouch, IA_Lantern, IA_Pause` in `IMC_LB_Gameplay`. Sensitivity is a user setting applied as an input modifier scalar.

## 5. Interaction
```
ILBInteractable (UInterface, BlueprintNativeEvent)
  bool  CanInteract(const FLBInteractionContext&)
  void  Interact(const FLBInteractionContext&)
  FText GetPromptText()
  void  OnFocusBegin() / OnFocusEnd()
FLBInteractionContext { AActor* Instigator; FGameplayTag InteractionType; }
```
`ULBInteractableComponent` implements the interface on behalf of any actor: exposes `PromptText`, `bEnabled`, `RequiredStateTags` (tags in WorldState needed), `GrantedStateTags` (tags added on interact), `bSingleUse`, and Blueprint delegates `OnInteracted`, `OnFocusBegin/End`. The interactor finds the interface on either the hit actor or its component.

Result: a door, lever, note, valve or ritual mechanism is a Blueprint actor = mesh + `ULBInteractableComponent` + its own timeline/logic. The player knows nothing about any of them.

Deliberately not built: inventory, generic "use item on object" matrix. Keys are WorldState tags (`State.Item.CryptKey`) checked via `RequiredStateTags`.

## 6. Objectives
- `ULBObjectiveData : UPrimaryDataAsset` — `ObjectiveTag`, `DisplayText`, `CompletionStateTags` (all required), `NextObjective` (soft ref, optional).
- `ULBObjectiveSubsystem : UWorldSubsystem` — holds the active objective, listens to `WorldStateSubsystem.OnStateChanged`, completes the objective when its tags are present, advances, broadcasts `OnObjectiveChanged`. Objective *chain* is linear — matches the game's linear progression.
- Active objective tag is itself stored in WorldState (`Objective.Active.*` is derived, not stored) — on load, the subsystem recomputes the active objective from completed states. No separate objective save data.

Not built: branching quests, parallel quest log, quest graph editor.

## 7. Save / Checkpoint
- `ULBSaveGame : USaveGame` — `SaveVersion`, `CheckpointId (FName)`, `MapName`, `WorldState (FGameplayTagContainer)`, `TMap<FGuid, FLBActorSaveRecord>` (small struct: bool flags + float + transform optional), `PlayTimeSeconds`.
- `ULBSaveSubsystem : UGameInstanceSubsystem` — `SaveCheckpoint(Id)`, `LoadLastCheckpoint()`, `HasSave()`, `DeleteSave()`. Single slot `LB_Slot0` + settings in `GameUserSettings` (not in the save).
- `ILBSaveable` — `WriteSaveRecord(FLBActorSaveRecord&)`, `ReadSaveRecord(const FLBActorSaveRecord&)`. Actors opt in and carry a `ULBSaveIdComponent` holding a stable editor-assigned `FGuid`.
- `ALBCheckpoint` — trigger volume + `CheckpointId` + spawn transform; on overlap (once) calls `SaveCheckpoint`.
- Restore order on load: open map → WorldState restored → saveable actors read records → objective subsystem recomputes → player spawned at checkpoint transform. Death = `LoadLastCheckpoint()` (same path; no separate death state).
- Corrupt/mismatched `SaveVersion` → log + treat as no save (Main Menu hides Continue).

Not built: multiple slots, mid-room free saving, whole-world serialization.

## 8. Warden AI
- `ALBWarden : ACharacter` (Blueprint child `BP_Warden` owns mesh/anim/audio) controlled by `ALBWardenController : AAIController`.
- **State Tree** (`ST_Warden`) on the controller via `UStateTreeAIComponent`. States: `Dormant`, `Scripted`, `Patrol`, `Investigate`, `Search`, `Chase`, `Attack`, `Return`. ("Suspicious" and "LostTarget" are transitions/sub-states of Investigate and Search, not separate top-level states.)
- **AI Perception**: Sight (cone, LoS) + Hearing. Stimuli come from footsteps, sprint, doors, dropped objects, ritual activations — all via `ReportNoiseEvent` with loudness/tag. The Warden only ever knows what perception tells it (no omniscience); scripted moves use explicit `Scripted` state with designer-placed targets.
- `ULBWardenEscalationComponent` — maps WorldState tags (`State.Ritual.1..3`, scripted beats) to escalation stage 1–6; stage gates which State Tree branches are enabled and perception ranges.
- EQS: **not used** initially; search points are designer-placed `ALBSearchPoint` actors near the last stimulus, picked nearest-first. Adopt EQS only if this proves inadequate.
- Debug: `lb.Warden.Debug 1` draws state name, perception cones, last-known location; Gameplay Debugger AI category.

Stage 1–2 (Presence, Partial Sightings) are **not AI** — they are scripted level events (sequencer, audio emitters, a non-AI silhouette actor). The AI pawn only spawns from Stage 3.

## 9. Gameplay Tags (initial set, `Config/Tags/LBGameplayTags.ini` + native declarations)
```
State.Ritual.1 / .2 / .3              State.Door.<Name>.Unlocked
State.Item.<Name>                     State.Event.<Name>
Objective.<Area>.<Name>               Interaction.Type.(Use|Pickup|Inspect|Read)
AI.Stimulus.(Footstep|Sprint|Door|Drop|Ritual)
Warden.Stage.(1..6)
```

## 10. Blueprint layer
`Content/LastBell/Blueprints/`:
- `BP_LBCharacter`, `BP_LBPlayerController`, `BP_LBGameMode` — data-only children configuring C++ classes.
- `Interactables/` — `BP_Door_Base` (rotating, lockable via RequiredStateTags), `BP_Lever`, `BP_Note`, `BP_RitualMechanism_Base`.
- `Puzzles/` — one Blueprint per puzzle, communicating only through WorldState tags.
- Level Blueprints: minimal; scripted beats live in small `BP_Event_*` actors so they are reusable and saveable.
- UI: `WBP_HUD` (prompt + objective toast), `WBP_MainMenu`, `WBP_Pause`, `WBP_Settings`.

Blueprint rule: no Blueprint reaches into another Blueprint's internals; communication is WorldState tags, interfaces, or delegates.

## 11. Maps
- `L_MainMenu` — menu only.
- `L_Monastery` — single World Partition map (or plain persistent map with Level Instances per area if WP proves heavy for a small map; decided in Phase 2). Areas: Courtyard, Chapel, Crypt, BellTower.
- `L_Test_MicroSlice` — Phase 1 proof map; kept as a regression test map.

## 12. Rendering baseline (to be measured, not assumed)
Lumen GI + reflections, Virtual Shadow Maps, Nanite for static geometry, TSR (DLSS evaluated later), volumetric fog + local fog volumes, Substrate **off** (current project setting; revisit only with a reason). Hardware ray tracing is currently on in project settings; Lumen HWRT vs software is decided by Phase 7 measurement on the dev GPU. See `PERFORMANCE_BUDGET.md`.

## 13. Testing hooks
- Automation tests (`LastBell.*`) for WorldState, objectives recompute, save round-trip, interaction routing — run via the AutomationTest toolset / `-ExecCmds="Automation RunTests LastBell"`.
- `L_Test_MicroSlice` as a functional regression map.
- Console commands: `lb.State.Add <Tag>`, `lb.State.Dump`, `lb.Checkpoint.Load`, `lb.Warden.Debug`.
