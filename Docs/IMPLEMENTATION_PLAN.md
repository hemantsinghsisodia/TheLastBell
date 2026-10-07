# THE LAST BELL — Implementation Plan

Every phase ends with a human review gate: **no phase starts without explicit user approval.** Each phase gets a Git checkpoint branch or tag named `phase/NN-name` once approved.

| Phase | Name | Exit condition |
|---|---|---|
| 0 | Inspection, architecture, tooling | Docs, agents and MCP connected; user approval |
| 1 | Micro vertical slice | Door → room → mechanism → objective → checkpoint → reload proven |
| 2 | Full greybox | Whole route playable start to finish |
| 3 | Player feel and interaction | Movement and interaction close to production |
| 4 | Objectives, puzzles, save | Three real ritual mechanisms; robust save/load |
| 5 | Warden AI | Threatening but understandable |
| 6 | Art-kit discovery | Asset families and test scenes approved |
| 7–10 | Courtyard, Chapel, Crypt, Bell Tower art | Per-area visual approval |
| 11 | Materials | Surface polish |
| 12–13 | Warden visual and animation | Unique creature, polished animation |
| 14–15 | Lighting, VFX | Viewpoint approvals and FPS checks |
| 16 | Audio | Headphone review |
| 17 | Cinematics | Narrative flow |
| 18 | UI and settings | Menus and graphics options |
| 19 | Full QA | No P0/P1 bugs |
| 20 | Performance | Measured budgets met |
| 21 | Final polish | Store-page screenshots |
| 22 | Shipping build | Packaged build approved |

## Phase 1 — Micro vertical slice: task breakdown
Map `L_Test_MicroSlice` uses primitive geometry only: spawn corridor → door → small room → mechanism (lever) → a second door that opens on progression. The flow is spawn, walk, open the door, use the mechanism, objective update, checkpoint save, progression event (the second door opens), then a reload restores that state.

| Task | Objective | Owner | Depends on | Risk |
|---|---|---|---|---|
| CORE-000 | Housekeeping: set the project name in `DefaultGame.ini`, de-duplicate renderer CVars, create the `Content/LastBell/` folder tree, reference-check and remove `/Game/DemoTemplate` (each item user-approved) | lead + unreal-blueprint-engineer | — | LOW |
| CORE-001 | Add the `LastBell` C++ module (Build.cs, targets, `LBLog`, native tags), generate project files and compile (choose the VS toolchain explicitly) | gameplay-programmer | CORE-000 | MED (first C++ conversion) |
| CORE-002 | `ALBGameMode` (checkpoint spawn, death hook), `ALBPlayerController` (IMC and HUD class), `ULBWorldStateSubsystem` (reset/replace/bulk delegates), and the `lb.State.*`, `lb.NewGame` and `lb.Kill` commands | gameplay-programmer | CORE-001 | LOW |
| INPUT-001 | `IA_Move`, `IA_Look`, `IA_Interact` and `IMC_LB_Gameplay` in `Content/LastBell/Input/` | unreal-blueprint-engineer | CORE-000 (parallel with CORE-002) | LOW |
| PLAYER-001 | `ALBCharacter` (camera, walking) plus data-only `BP_LBCharacter`, `BP_LBPlayerController` and `BP_LBGameMode` | gameplay-programmer | CORE-002, INPUT-001 | LOW |
| INT-001 | `ULBInteractorComponent` (timer trace) and `ULBInteractableComponent`, plus the `Interaction` trace channel | gameplay-programmer | PLAYER-001 | MED (core contract) |
| OBJ-001 | `ULBObjectiveChainData` and `ULBObjectiveSubsystem` (derived active objective) | gameplay-programmer | CORE-002 | LOW |
| SAVE-001 | `ULBSaveGame`, `FLBActorSaveRecord`, `ULBSaveSubsystem`, `ULBSaveStateComponent` (pull restore, duplicate-id check), `ALBCheckpoint`, and the restore flow from TECHNICAL_DESIGN §7 | gameplay-programmer | CORE-002, OBJ-001, PLAYER-001 | MED |
| TEST-001 | Automation tests listed in TECHNICAL_DESIGN §13 | gameplay-programmer | SAVE-001, INT-001 | LOW |
| OBJ-DATA-001 | `DA_ObjectiveChain_MicroSlice` (3 objectives) and the micro-slice `State.Test.*` ini tags | unreal-blueprint-engineer | OBJ-001 | LOW |
| BP-001 | `BP_Door_Base` (lockable, open state as a tag, instant snap on restore) and `BP_Lever` (grants `State.Test.LeverPulled`) | unreal-blueprint-engineer | INT-001, SAVE-001 | LOW |
| UI-001 | Minimal `WBP_HUD`: interaction prompt and objective text bound to the delegates | ui-engineer | INT-001, OBJ-001 | LOW |
| LVL-001 | `L_Test_MicroSlice` built from primitives: GameMode override, doors, lever, checkpoint, a test kill volume; set as the editor and game startup map | environment-designer | BP-001, UI-001, OBJ-DATA-001 | LOW |
| REV-001 | Architecture review of the Phase 1 code against TECHNICAL_DESIGN | architecture-reviewer | all | — |
| QA-001 | Acceptance script: slice flow; death reload; `lb.NewGame` resets the state; on reload the door states, lever state, objective and player transform are coherent; no retrigger; logs clean | qa-reviewer | all | — |

Order: CORE-000 → CORE-001 → (CORE-002 ∥ INPUT-001) → (PLAYER-001 ∥ OBJ-001) → INT-001 → SAVE-001 → (TEST-001 ∥ OBJ-DATA-001 ∥ BP-001 ∥ UI-001) → LVL-001 → (REV-001 ∥ QA-001).
The gameplay-programmer has sole ownership of the C++ through TEST-001. Content tasks run in parallel only when they touch different assets.
A Main Menu isn't part of Phase 1. New Game and Continue are exercised through console commands until Phase 2.

## Phase 2 — Complete greybox: task breakdown
Spec: `Docs/GREYBOX_SPEC.md`. One map, `L_Monastery` (D-023), plus `L_MainMenu`.

| Task | Objective | Owner | Depends on | Risk |
|---|---|---|---|---|
| P2-SYS-001 | C++: `ULBGameSettings` (DeveloperSettings: MainMenuMap, NewGameMap soft refs); invert objective chain wiring (GameMode → `ULBObjectiveSubsystem::SetChain`, R-16); `ULBSaveSubsystem::StartNewGame()` / `ContinueGame()` / `CompleteGame()` / `ReturnToMainMenu()` using settings; `ALBPlayerController` `bMenuMode` (UI input, cursor); cook `/Game/LastBell/Maps` (R-15) | gameplay-programmer | — | LOW |
| P2-TAGS-001 | Author all Phase 2 tags in `Config/Tags/LBGameplayTags.ini` as text while the editor is closed (D-024) | lead | — | LOW |
| P2-BP-001 | `BP_TagInteractable` (generic: mesh + interactable, optional hide-on-use / show-when-tag), `BP_TagVisibility` (shows/hides target components when a tag is added/present), `BP_WardenSilhouette` (tall placeholder; appears on a tag for N s, optional move A→B), `BP_WardenPlaceholderKill` (silhouette + kill overlap, active while a tag is present), `BP_RitualMechanism` (lever variant with a visual state change), `DA_ObjectiveChain_Main`, unbind `OnStateChanged` on EndPlay in door/lever (R-17) | unreal-blueprint-engineer | P2-SYS-001, P2-TAGS-001 | LOW |
| P2-UI-001 | `L_MainMenu` + `BP_MenuGameMode` + `WBP_MainMenu` (New Game / Continue if a save exists / Quit); `WBP_Ending`; `BP_EndingTrigger` (on `State.Event.Finale` → ending → `CompleteGame`) | ui-engineer | P2-SYS-001, P2-TAGS-001 | LOW |
| P2-LVL-001 | Build `L_Monastery` per GREYBOX_SPEC: all areas, route, stand-ins, checkpoints, hazards, lights | environment-designer | P2-BP-001, P2-UI-001 | MED (size) |
| P2-TEST-001 | `LastBell.Functional.RouteBot.Monastery` (+ `RouteBot.MicroSlice`): an objective-driven bot that, for each active objective, finds an interactable/trigger granting the missing tag, teleports there, interacts or overlaps, and asserts progress through Finale → menu; plus death at the crypt pit → restore | gameplay-programmer | P2-LVL-001 | MED |
| P2-REV / P2-QA | Architecture review and QA of the full route, checkpoints, death and transitions | architecture-reviewer, qa-reviewer | all | — |

## Phase 3 — carry-over from REV-002
- **P3-000:** introduce the `ALBTagReactiveActor` base (snap, bind, unbind) and migrate the 5 tag-reactive BPs before adding interaction feedback (REV-002 M5).
- Rerun `RouteBot.*` after every movement or interaction change. The bot assumes standing capsule height and interact range (REV-002 L12).
