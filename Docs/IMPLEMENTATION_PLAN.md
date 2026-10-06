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
| CORE-001 | Add the `LastBell` C++ module (Build.cs, target files, `LBLog`, native Gameplay Tags), generate the project files and compile from the editor via Live Coding/UBT | gameplay-programmer | — | MED (first C++ conversion of a BP project) |
| CORE-002 | `ALBGameMode`, `ALBPlayerController`, `ULBGameInstance`, `ULBWorldStateSubsystem` plus `lb.State.*` console commands | gameplay-programmer | CORE-001 | LOW |
| PLAYER-001 | `ALBCharacter` (camera, walk only, Enhanced Input `IMC_LB_Gameplay`: Move, Look, Interact) plus the data-only `BP_LBCharacter` | gameplay-programmer | CORE-002 | LOW |
| INT-001 | `ILBInteractable`, `FLBInteractionContext`, `ULBInteractorComponent`, `ULBInteractableComponent`, `Interaction` trace channel | gameplay-programmer | PLAYER-001 | MED (core contract) |
| OBJ-001 | `ULBObjectiveData`, `ULBObjectiveSubsystem` with recompute-from-state | gameplay-programmer | CORE-002 | LOW |
| SAVE-001 | `ULBSaveGame`, `ULBSaveSubsystem`, `ILBSaveable`, `ULBSaveIdComponent`, `ALBCheckpoint`, death/restart path | gameplay-programmer | CORE-002, OBJ-001 | MED |
| BP-001 | `BP_Door_Base` (rotating, lockable via RequiredStateTags, saveable) and `BP_Lever` (grants `State.Test.LeverPulled`) | unreal-blueprint-engineer | INT-001, SAVE-001 | LOW |
| UI-001 | Minimal `WBP_HUD`: interaction prompt and objective text | ui-engineer | INT-001, OBJ-001 | LOW |
| LVL-001 | Build `L_Test_MicroSlice` with primitive geometry and place the actors and checkpoint | environment-designer | BP-001 | LOW |
| TEST-001 | Automation tests: WorldState add/remove, objective recompute, save round-trip, interactable routing | gameplay-programmer | SAVE-001 | LOW |
| REV-001 | Architecture review of the Phase 1 code against TECHNICAL_DESIGN | architecture-reviewer | all | — |
| QA-001 | Run the slice flow, the reload and death paths, and check the logs | qa-reviewer | all | — |

Order: CORE-001 → CORE-002 → (PLAYER-001 ∥ OBJ-001) → INT-001 → SAVE-001 → (BP-001 ∥ UI-001 ∥ TEST-001) → LVL-001 → REV-001 ∥ QA-001.
The gameplay-programmer has sole ownership of the C++ through SAVE-001, so there are no concurrent edits to the core sources.

Also proposed for Phase 1, if you approve: set the project name in `DefaultGame.ini`, de-duplicate renderer CVars, point GameDefaultMap and EditorStartupMap at `L_Test_MicroSlice`, and remove `/Game/DemoTemplate` after a reference check.
