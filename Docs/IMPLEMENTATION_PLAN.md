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
- ~~P3-000 `ALBTagReactiveActor` base~~: deferred (D-032).
- Rerun `RouteBot.*` after every movement or interaction change. The bot assumes standing capsule height and interact range (REV-002 L12).

## Phase 3 — Player feel and interaction: task breakdown
Branch: `claude/phase-03-player-feel`. Decisions: D-029 (candle), D-030 (inspection), D-031 (no stamina), D-032 (tag-reactive base deferred).

**Feel targets.** All of these are tunable in `DA_PlayerTuning`, with no magic numbers in code:
- Walk 260 cm/s, sprint 480, crouch 140. Acceleration about 1400, braking about 1600. These are deliberate and grounded, not floaty.
- Crouch: capsule half-height 92 → 58, and the camera interpolates over about 0.2 s.
- Head bob: subtle and on by default. Vertical amplitude 0.6 cm walking / 1.4 cm sprinting, with a setting to turn it off. No roll and no camera shake.
- Sprint FOV +4° eased in. A small landing dip.
- Mouse sensitivity and invert-Y settings, stored in a settings object (UI comes in Phase 18).

| Task | Objective | Owner | Depends on | Risk |
|---|---|---|---|---|
| P3-001 | C++: `ULBPlayerTuningData` (DataAsset); sprint and crouch on `ALBCharacter`; `ULBCameraFeelComponent` (bob, crouch interp, sprint FOV, landing dip); `ULBFootstepComponent` (distance cadence by gait, surface → `DT_Footsteps` sound, `OnFootstep(Loudness, Location, Surface)` delegate for the Phase 5 noise hook); `ULBCandleComponent` (point light, flicker, guttering while sprinting, snuff/relight with a delay, `IsLit()`); `ULBInspectableComponent` plus inspection mode on the character (pick up → hold in front of the camera → rotate → optional text → put back or keep); `ULBUserSettings` (sensitivity, invert Y, head bob) | gameplay-programmer | — | MED |
| P3-002 | Input: `IA_Sprint` (Shift / L3), `IA_Crouch` (C or Ctrl hold / B), `IA_Candle` (F / Y), `IA_InspectRotate` (mouse drag / right stick), `IA_InspectExit` (E or RMB / B); `IMC_LB_Inspect` | unreal-blueprint-engineer | — | LOW |
| P3-003 | Content wiring: `DA_PlayerTuning`; `BP_LBCharacter` uses it plus a placeholder held-candle mesh with a sway; `BP_Inspectable_Note` (inspectable with text) and inspectable key and crank; door swings away from the player; HUD crosshair focus state; `WBP_Inspect` overlay (note text and controls hint) | blueprint-engineer + ui-engineer | P3-001, P3-002 | LOW |
| P3-004 | Place 4–6 placeholder notes in L_Monastery (lore stubs) | environment-designer | P3-003 | LOW |
| P3-005 | Tests: tuning and footstep cadence unit tests; candle state tests; inspection enter/exit test; RouteBot and WalkPath rerun (gait changes); a crouch-walk path | gameplay-programmer | P3-003 | LOW |
| P3-006 | Packaged Development build smoke test (R-20): cook, launch, menu → New Game → walk → quit | performance-engineer / lead | P3-005 | MED |
| P3-REV / P3-QA | Architecture review and QA | reviewers | all | — |

## Phase 4 — Objectives, puzzles and save: task breakdown
Branch: `claude/phase-04-puzzles-save`. Owner's puzzle choices (D-035): Chapel = candle order, Crypt = chain counterweights, Tower base = bell sequence.

**Puzzle framework (progress is tags, so it's saved at checkpoints automatically; no per-puzzle save code):**
- `ULBInteractableComponent`: single-use availability is **derived from `ConsumedStateTag`** (no permanent `bEnabled=false`), so a puzzle reset (removing the tag) makes the step usable again (REV-003 M6).
- `ULBSequencePuzzleComponent` (on a `BP_SequencePuzzle` actor): ordered `Steps` (tags). It listens to WorldState. A step tag added out of order → `RemoveStates(all step tags)` + `OnPuzzleFailed`. All steps in order → `AddStates(SolvedTags)` + `OnPuzzleSolved`. Already solved at BeginPlay → no-op.
- `ULBDialComponent` (on a lever/dial actor): `PositionTags` (one tag per position). Interact cycles the position: remove the old tag, add the new one. The initial position is authored. Combination puzzles need **no controller**: the target interactable's `RequiredStateTags` lists the wanted position tags.
- Route bot: learns "sequence puzzle" providers (perform steps in order) and "dial" providers (cycle to the required position).

| Task | Objective | Owner | Depends on | Risk |
|---|---|---|---|---|
| P4-TAGS | New tags: `State.Chapel.Candle.4`, `State.Chapel.CandlesSolved`, `State.Crypt.Dial.{A,B,C}.{0,1,2}`, `State.Tower.Bell.{1..4}`, `State.Tower.BellsSolved` (text, editor closed, D-024) | lead | — | LOW |
| P4-001 | C++: derived single-use availability; `ULBSequencePuzzleComponent`; `ULBDialComponent`; unit and functional tests (order, fail reset, solved snap, save mid-puzzle → load); route bot support | gameplay-programmer | — | MED |
| P4-002 | BPs: `BP_SequencePuzzle`, `BP_PuzzleCandle` (lit/unlit both ways with flame and light), `BP_SmallBell` (strike swing), `BP_DialLever` (3 positions, visible notches), clue props (`BP_StainedGlassClue`, `BP_EngravedDiagram`, `BP_Inscription`: simple planes with readable symbols/text) | unreal-blueprint-engineer | P4-001 | LOW |
| P4-003 | Level: replace the chapel candles, the crypt stand-in and the cloister levers with the real puzzles plus clues; update `DA_ObjectiveChain_Main` (Light the candles in order → CandlesSolved; Balance the chains → dial tags; Ring the bells in order → BellsSolved) | environment-designer + blueprint-engineer | P4-002 | MED |
| P4-004 | Save hardening tests: corrupt or truncated save file → no Continue and no crash; quit to menu mid-puzzle → Continue restores the partial puzzle; death mid-puzzle; revisiting solved puzzles stays solved | gameplay-programmer | P4-001 | LOW |
| P4-REV/QA | Architecture review; full RouteBot and WalkPath runs; human playtest of each puzzle | reviewers + owner | all | — |

## Phase 5 — Warden AI: task breakdown
Branch: `claude/phase-05-warden-ai`. Spec: `Docs/AI_DESIGN.md`. The brain is a **C++ state machine** (D-037, supersedes the State Tree part of D-007/D-018): the MCP tools can't author State Tree or BT assets, and C++ is fully testable by agents.

**Architecture:**
- `ALBWarden : ACharacter` (placeholder body in `BP_Warden`).
- `ALBWardenController : AAIController` with `UAIPerceptionComponent` (sight + hearing, detects neutrals).
- `ULBWardenBrainComponent`: the states Dormant, Patrol, Investigate (with a "suspicious" look-around), Search, Chase, Attack and Return.
- `ULBWardenTuningData` (`DA_WardenTuning`): every speed, range, timer and stage gate.
- **Stage gating** from the `State.Warden.Stage.N` tags (D-018):
  - Stage ≤2: no AI pawn (scripted silhouettes stay as they are).
  - Stage 3: Investigate noises only; a catch at close range still kills.
  - Stage 4: adds Patrol and Search.
  - Stage 5+: adds Chase (Hunt).
- **Level markers:** `ALBWardenSpawnPoint` (stage + route), `ALBPatrolPoint` (route, order), `ALBSearchPoint`.
- **Noise:** `ULBFootstepComponent` reports a noise per step (loudness by gait). `ULBInteractableComponent.NoiseLoudness` covers doors and mechanisms.
- **Candle:** `IsLit()` scales how far the Warden can see you. The Warden only knows what perception reports (no omniscience).
- **Not saved:** rebuilt from the stage tags at a spawn point (D-012). Checkpoints refuse to save while it is in Chase or Attack (D-019).
- **Debug:** `lb.Warden.Debug 1` (on-screen state, last-known location, cones), plus the Visual Logger.

| Task | Objective | Owner | Depends on | Risk |
|---|---|---|---|---|
| P5-001 | C++: the Warden classes above, perception and noise wiring, the brain state machine, tuning data, the markers, checkpoint refusal, debug drawing; `AIModule`/`NavigationSystem` dependencies | warden-ai | — | HIGH |
| P5-002 | Content: project navigation set to runtime **Dynamic**, so doors change the navmesh; NavMeshBoundsVolume(s) in `L_Monastery`; a `L_Test_Warden` map (corridor loop, occluding pillars, a sound-test room, an unreachable ledge, a door, NavMesh) | environment-designer | — | MED |
| P5-003 | `BP_Warden` (tall dark placeholder body, capsule about 55×145) and `DA_WardenTuning`; replace the crypt `BP_WardenPlaceholderKill` with the real Warden flow (spawn, patrol and search points in the crypt and cloister) | blueprint-engineer + environment-designer | P5-001, P5-002 | MED |
| P5-004 | AI tests in `L_Test_Warden`: sight vs blocked sight; hearing walk vs sprint vs crouch; investigate the noise location; lose the target → search → return; an unreachable player; stuck recovery; repeated chases; chase speed below player sprint; a catch kills; checkpoint refused during a chase; RouteBot and WalkPath still green | warden-ai | P5-001..003 | MED |
| P5-REV/QA | Architecture review; the owner plays against the Warden repeatedly (difficulty, intelligence, predictability, fairness, chase speed, search time, atmosphere) | reviewers + owner | all | — |

## Phase 6 — Art-kit discovery: task breakdown
Branch: `claude/phase-06-art-kit`. Owner choices: **grounded photoreal** look; **free assets only** (D-040). The greybox (`L_Monastery`) is **not touched**. Samples live in a separate art-test map, so the area art phases (7–10) start from approved families rather than from guesses.

**Sources, in priority order:** existing project content (nothing photoreal: only the template, `LevelPrototyping` and the greybox) → free Fab listings (including any free Megascans; the owner claims them, never an agent) → CC0 libraries through the local `3d-assets-local` MCP (Poly Haven, ambientCG, TextureCan and others; D-041) → 3d.shep.bot / Blender for custom assets only.

| Task | Objective | Owner | Depends on | Risk |
|---|---|---|---|---|
| P6-001 | Discovery: per-area asset families (architecture kit, floors and ground, walls and masonry, roofs and wood, props, vegetation and roots, decals, sky/HDRI) for the Courtyard, Chapel, Crypt and Bell Tower; 1–3 candidates per family with source, licence, price, download method and the reason it fits; the custom-asset list (Warden, mask, three mechanisms, symbols, finale bell) with a production route; the list of free Fab items the owner must claim. Output `Docs/ASSET_PLAN.md` | asset-curator | — | MED |
| P6-002 | Download a representative CC0 sample set (about 12–20 items at 2K: hero masonry, flagstone, plaster, wood, iron, roots/moss, ground, a night HDRI, a few scanned props) into `ExternalAssets/Incoming/`; one `ASSET_REGISTRY.md` row per item | asset-curator | P6-001 | LOW |
| P6-003 | Import the samples into `Content/LastBell/ArtTest/` with correct texture settings (sRGB off for packed/normal maps, BC5 normals, 2K max); a first `M_LB_Surface` master (base PBR, texel-density UV scale, world-aligned macro variation, wetness scalar) with one MI per material; Nanite on scanned meshes | technical-artist | P6-002 | MED |
| P6-004 | `L_Test_ArtKit`: four small bays (Courtyard, Chapel, Crypt, Bell Tower) dressed only with the samples, plus a night/moon light rig, height fog and the HDRI; the `CaptureViewport` screenshots for review in `Docs/ArtTest/` | environment-designer | P6-003 | MED |
| P6-REV/QA | No new errors in the logs; texture/Nanite settings checked; 78 tests still green; `L_Monastery` unchanged (`git diff`); registry complete; owner review of families and screenshots | qa-reviewer + owner | all | — |
