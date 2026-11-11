# THE LAST BELL Ã¢â‚¬â€ Implementation Plan

Every phase ends with a human review gate: **no phase starts without explicit user approval.** Each phase gets a Git checkpoint branch or tag named `phase/NN-name` once approved.

| Phase | Name | Exit condition |
|---|---|---|
| 0 | Inspection, architecture, tooling | Docs, agents and MCP connected; user approval |
| 1 | Micro vertical slice | Door Ã¢â€ â€™ room Ã¢â€ â€™ mechanism Ã¢â€ â€™ objective Ã¢â€ â€™ checkpoint Ã¢â€ â€™ reload proven |
| 2 | Full greybox | Whole route playable start to finish |
| 3 | Player feel and interaction | Movement and interaction close to production |
| 4 | Objectives, puzzles, save | Three real ritual mechanisms; robust save/load |
| 5 | Warden AI | Threatening but understandable |
| 6 | Art-kit discovery | Asset families and test scenes approved (**approved 2026-10-23**) |
| 7Ã¢â‚¬â€œ10 | Courtyard, Chapel, Crypt, Bell Tower art | Per-area visual approval |
| 11 | Materials | Surface polish |
| 12Ã¢â‚¬â€œ13 | Warden visual and animation | Unique creature, polished animation |
| 14Ã¢â‚¬â€œ15 | Lighting, VFX | Viewpoint approvals and FPS checks |
| 16 | Audio | Headphone review |
| 17 | Cinematics | Narrative flow |
| 18 | UI and settings | Menus and graphics options |
| 19 | Full QA | No P0/P1 bugs |
| 20 | Performance | Measured budgets met |
| 21 | Final polish | Store-page screenshots |
| 22 | Shipping build | Packaged build approved |

## Phase 1 Ã¢â‚¬â€ Micro vertical slice: task breakdown
Map `L_Test_MicroSlice` uses primitive geometry only: spawn corridor Ã¢â€ â€™ door Ã¢â€ â€™ small room Ã¢â€ â€™ mechanism (lever) Ã¢â€ â€™ a second door that opens on progression. The flow is spawn, walk, open the door, use the mechanism, objective update, checkpoint save, progression event (the second door opens), then a reload restores that state.

| Task | Objective | Owner | Depends on | Risk |
|---|---|---|---|---|
| CORE-000 | Housekeeping: set the project name in `DefaultGame.ini`, de-duplicate renderer CVars, create the `Content/LastBell/` folder tree, reference-check and remove `/Game/DemoTemplate` (each item user-approved) | lead + unreal-blueprint-engineer | Ã¢â‚¬â€ | LOW |
| CORE-001 | Add the `LastBell` C++ module (Build.cs, targets, `LBLog`, native tags), generate project files and compile (choose the VS toolchain explicitly) | gameplay-programmer | CORE-000 | MED (first C++ conversion) |
| CORE-002 | `ALBGameMode` (checkpoint spawn, death hook), `ALBPlayerController` (IMC and HUD class), `ULBWorldStateSubsystem` (reset/replace/bulk delegates), and the `lb.State.*`, `lb.NewGame` and `lb.Kill` commands | gameplay-programmer | CORE-001 | LOW |
| INPUT-001 | `IA_Move`, `IA_Look`, `IA_Interact` and `IMC_LB_Gameplay` in `Content/LastBell/Input/` | unreal-blueprint-engineer | CORE-000 (parallel with CORE-002) | LOW |
| PLAYER-001 | `ALBCharacter` (camera, walking) plus data-only `BP_LBCharacter`, `BP_LBPlayerController` and `BP_LBGameMode` | gameplay-programmer | CORE-002, INPUT-001 | LOW |
| INT-001 | `ULBInteractorComponent` (timer trace) and `ULBInteractableComponent`, plus the `Interaction` trace channel | gameplay-programmer | PLAYER-001 | MED (core contract) |
| OBJ-001 | `ULBObjectiveChainData` and `ULBObjectiveSubsystem` (derived active objective) | gameplay-programmer | CORE-002 | LOW |
| SAVE-001 | `ULBSaveGame`, `FLBActorSaveRecord`, `ULBSaveSubsystem`, `ULBSaveStateComponent` (pull restore, duplicate-id check), `ALBCheckpoint`, and the restore flow from TECHNICAL_DESIGN Ã‚Â§7 | gameplay-programmer | CORE-002, OBJ-001, PLAYER-001 | MED |
| TEST-001 | Automation tests listed in TECHNICAL_DESIGN Ã‚Â§13 | gameplay-programmer | SAVE-001, INT-001 | LOW |
| OBJ-DATA-001 | `DA_ObjectiveChain_MicroSlice` (3 objectives) and the micro-slice `State.Test.*` ini tags | unreal-blueprint-engineer | OBJ-001 | LOW |
| BP-001 | `BP_Door_Base` (lockable, open state as a tag, instant snap on restore) and `BP_Lever` (grants `State.Test.LeverPulled`) | unreal-blueprint-engineer | INT-001, SAVE-001 | LOW |
| UI-001 | Minimal `WBP_HUD`: interaction prompt and objective text bound to the delegates | ui-engineer | INT-001, OBJ-001 | LOW |
| LVL-001 | `L_Test_MicroSlice` built from primitives: GameMode override, doors, lever, checkpoint, a test kill volume; set as the editor and game startup map | environment-designer | BP-001, UI-001, OBJ-DATA-001 | LOW |
| REV-001 | Architecture review of the Phase 1 code against TECHNICAL_DESIGN | architecture-reviewer | all | Ã¢â‚¬â€ |
| QA-001 | Acceptance script: slice flow; death reload; `lb.NewGame` resets the state; on reload the door states, lever state, objective and player transform are coherent; no retrigger; logs clean | qa-reviewer | all | Ã¢â‚¬â€ |

Order: CORE-000 Ã¢â€ â€™ CORE-001 Ã¢â€ â€™ (CORE-002 Ã¢Ë†Â¥ INPUT-001) Ã¢â€ â€™ (PLAYER-001 Ã¢Ë†Â¥ OBJ-001) Ã¢â€ â€™ INT-001 Ã¢â€ â€™ SAVE-001 Ã¢â€ â€™ (TEST-001 Ã¢Ë†Â¥ OBJ-DATA-001 Ã¢Ë†Â¥ BP-001 Ã¢Ë†Â¥ UI-001) Ã¢â€ â€™ LVL-001 Ã¢â€ â€™ (REV-001 Ã¢Ë†Â¥ QA-001).
The gameplay-programmer has sole ownership of the C++ through TEST-001. Content tasks run in parallel only when they touch different assets.
A Main Menu isn't part of Phase 1. New Game and Continue are exercised through console commands until Phase 2.

## Phase 2 Ã¢â‚¬â€ Complete greybox: task breakdown
Spec: `Docs/GREYBOX_SPEC.md`. One map, `L_Monastery` (D-023), plus `L_MainMenu`.

| Task | Objective | Owner | Depends on | Risk |
|---|---|---|---|---|
| P2-SYS-001 | C++: `ULBGameSettings` (DeveloperSettings: MainMenuMap, NewGameMap soft refs); invert objective chain wiring (GameMode Ã¢â€ â€™ `ULBObjectiveSubsystem::SetChain`, R-16); `ULBSaveSubsystem::StartNewGame()` / `ContinueGame()` / `CompleteGame()` / `ReturnToMainMenu()` using settings; `ALBPlayerController` `bMenuMode` (UI input, cursor); cook `/Game/LastBell/Maps` (R-15) | gameplay-programmer | Ã¢â‚¬â€ | LOW |
| P2-TAGS-001 | Author all Phase 2 tags in `Config/Tags/LBGameplayTags.ini` as text while the editor is closed (D-024) | lead | Ã¢â‚¬â€ | LOW |
| P2-BP-001 | `BP_TagInteractable` (generic: mesh + interactable, optional hide-on-use / show-when-tag), `BP_TagVisibility` (shows/hides target components when a tag is added/present), `BP_WardenSilhouette` (tall placeholder; appears on a tag for N s, optional move AÃ¢â€ â€™B), `BP_WardenPlaceholderKill` (silhouette + kill overlap, active while a tag is present), `BP_RitualMechanism` (lever variant with a visual state change), `DA_ObjectiveChain_Main`, unbind `OnStateChanged` on EndPlay in door/lever (R-17) | unreal-blueprint-engineer | P2-SYS-001, P2-TAGS-001 | LOW |
| P2-UI-001 | `L_MainMenu` + `BP_MenuGameMode` + `WBP_MainMenu` (New Game / Continue if a save exists / Quit); `WBP_Ending`; `BP_EndingTrigger` (on `State.Event.Finale` Ã¢â€ â€™ ending Ã¢â€ â€™ `CompleteGame`) | ui-engineer | P2-SYS-001, P2-TAGS-001 | LOW |
| P2-LVL-001 | Build `L_Monastery` per GREYBOX_SPEC: all areas, route, stand-ins, checkpoints, hazards, lights | environment-designer | P2-BP-001, P2-UI-001 | MED (size) |
| P2-TEST-001 | `LastBell.Functional.RouteBot.Monastery` (+ `RouteBot.MicroSlice`): an objective-driven bot that, for each active objective, finds an interactable/trigger granting the missing tag, teleports there, interacts or overlaps, and asserts progress through Finale Ã¢â€ â€™ menu; plus death at the crypt pit Ã¢â€ â€™ restore | gameplay-programmer | P2-LVL-001 | MED |
| P2-REV / P2-QA | Architecture review and QA of the full route, checkpoints, death and transitions | architecture-reviewer, qa-reviewer | all | Ã¢â‚¬â€ |

## Phase 3 Ã¢â‚¬â€ carry-over from REV-002
- ~~P3-000 `ALBTagReactiveActor` base~~: deferred (D-032).
- Rerun `RouteBot.*` after every movement or interaction change. The bot assumes standing capsule height and interact range (REV-002 L12).

## Phase 3 Ã¢â‚¬â€ Player feel and interaction: task breakdown
Branch: `claude/phase-03-player-feel`. Decisions: D-029 (candle), D-030 (inspection), D-031 (no stamina), D-032 (tag-reactive base deferred).

**Feel targets.** All of these are tunable in `DA_PlayerTuning`, with no magic numbers in code:
- Walk 260 cm/s, sprint 480, crouch 140. Acceleration about 1400, braking about 1600. These are deliberate and grounded, not floaty.
- Crouch: capsule half-height 92 Ã¢â€ â€™ 58, and the camera interpolates over about 0.2 s.
- Head bob: subtle and on by default. Vertical amplitude 0.6 cm walking / 1.4 cm sprinting, with a setting to turn it off. No roll and no camera shake.
- Sprint FOV +4Ã‚Â° eased in. A small landing dip.
- Mouse sensitivity and invert-Y settings, stored in a settings object (UI comes in Phase 18).

| Task | Objective | Owner | Depends on | Risk |
|---|---|---|---|---|
| P3-001 | C++: `ULBPlayerTuningData` (DataAsset); sprint and crouch on `ALBCharacter`; `ULBCameraFeelComponent` (bob, crouch interp, sprint FOV, landing dip); `ULBFootstepComponent` (distance cadence by gait, surface Ã¢â€ â€™ `DT_Footsteps` sound, `OnFootstep(Loudness, Location, Surface)` delegate for the Phase 5 noise hook); `ULBCandleComponent` (point light, flicker, guttering while sprinting, snuff/relight with a delay, `IsLit()`); `ULBInspectableComponent` plus inspection mode on the character (pick up Ã¢â€ â€™ hold in front of the camera Ã¢â€ â€™ rotate Ã¢â€ â€™ optional text Ã¢â€ â€™ put back or keep); `ULBUserSettings` (sensitivity, invert Y, head bob) | gameplay-programmer | Ã¢â‚¬â€ | MED |
| P3-002 | Input: `IA_Sprint` (Shift / L3), `IA_Crouch` (C or Ctrl hold / B), `IA_Candle` (F / Y), `IA_InspectRotate` (mouse drag / right stick), `IA_InspectExit` (E or RMB / B); `IMC_LB_Inspect` | unreal-blueprint-engineer | Ã¢â‚¬â€ | LOW |
| P3-003 | Content wiring: `DA_PlayerTuning`; `BP_LBCharacter` uses it plus a placeholder held-candle mesh with a sway; `BP_Inspectable_Note` (inspectable with text) and inspectable key and crank; door swings away from the player; HUD crosshair focus state; `WBP_Inspect` overlay (note text and controls hint) | blueprint-engineer + ui-engineer | P3-001, P3-002 | LOW |
| P3-004 | Place 4Ã¢â‚¬â€œ6 placeholder notes in L_Monastery (lore stubs) | environment-designer | P3-003 | LOW |
| P3-005 | Tests: tuning and footstep cadence unit tests; candle state tests; inspection enter/exit test; RouteBot and WalkPath rerun (gait changes); a crouch-walk path | gameplay-programmer | P3-003 | LOW |
| P3-006 | Packaged Development build smoke test (R-20): cook, launch, menu Ã¢â€ â€™ New Game Ã¢â€ â€™ walk Ã¢â€ â€™ quit | performance-engineer / lead | P3-005 | MED |
| P3-REV / P3-QA | Architecture review and QA | reviewers | all | Ã¢â‚¬â€ |

## Phase 4 Ã¢â‚¬â€ Objectives, puzzles and save: task breakdown
Branch: `claude/phase-04-puzzles-save`. Owner's puzzle choices (D-035): Chapel = candle order, Crypt = chain counterweights, Tower base = bell sequence.

**Puzzle framework (progress is tags, so it's saved at checkpoints automatically; no per-puzzle save code):**
- `ULBInteractableComponent`: single-use availability is **derived from `ConsumedStateTag`** (no permanent `bEnabled=false`), so a puzzle reset (removing the tag) makes the step usable again (REV-003 M6).
- `ULBSequencePuzzleComponent` (on a `BP_SequencePuzzle` actor): ordered `Steps` (tags). It listens to WorldState. A step tag added out of order Ã¢â€ â€™ `RemoveStates(all step tags)` + `OnPuzzleFailed`. All steps in order Ã¢â€ â€™ `AddStates(SolvedTags)` + `OnPuzzleSolved`. Already solved at BeginPlay Ã¢â€ â€™ no-op.
- `ULBDialComponent` (on a lever/dial actor): `PositionTags` (one tag per position). Interact cycles the position: remove the old tag, add the new one. The initial position is authored. Combination puzzles need **no controller**: the target interactable's `RequiredStateTags` lists the wanted position tags.
- Route bot: learns "sequence puzzle" providers (perform steps in order) and "dial" providers (cycle to the required position).

| Task | Objective | Owner | Depends on | Risk |
|---|---|---|---|---|
| P4-TAGS | New tags: `State.Chapel.Candle.4`, `State.Chapel.CandlesSolved`, `State.Crypt.Dial.{A,B,C}.{0,1,2}`, `State.Tower.Bell.{1..4}`, `State.Tower.BellsSolved` (text, editor closed, D-024) | lead | Ã¢â‚¬â€ | LOW |
| P4-001 | C++: derived single-use availability; `ULBSequencePuzzleComponent`; `ULBDialComponent`; unit and functional tests (order, fail reset, solved snap, save mid-puzzle Ã¢â€ â€™ load); route bot support | gameplay-programmer | Ã¢â‚¬â€ | MED |
| P4-002 | BPs: `BP_SequencePuzzle`, `BP_PuzzleCandle` (lit/unlit both ways with flame and light), `BP_SmallBell` (strike swing), `BP_DialLever` (3 positions, visible notches), clue props (`BP_StainedGlassClue`, `BP_EngravedDiagram`, `BP_Inscription`: simple planes with readable symbols/text) | unreal-blueprint-engineer | P4-001 | LOW |
| P4-003 | Level: replace the chapel candles, the crypt stand-in and the cloister levers with the real puzzles plus clues; update `DA_ObjectiveChain_Main` (Light the candles in order Ã¢â€ â€™ CandlesSolved; Balance the chains Ã¢â€ â€™ dial tags; Ring the bells in order Ã¢â€ â€™ BellsSolved) | environment-designer + blueprint-engineer | P4-002 | MED |
| P4-004 | Save hardening tests: corrupt or truncated save file Ã¢â€ â€™ no Continue and no crash; quit to menu mid-puzzle Ã¢â€ â€™ Continue restores the partial puzzle; death mid-puzzle; revisiting solved puzzles stays solved | gameplay-programmer | P4-001 | LOW |
| P4-REV/QA | Architecture review; full RouteBot and WalkPath runs; human playtest of each puzzle | reviewers + owner | all | Ã¢â‚¬â€ |

## Phase 5 Ã¢â‚¬â€ Warden AI: task breakdown
Branch: `claude/phase-05-warden-ai`. Spec: `Docs/AI_DESIGN.md`. The brain is a **C++ state machine** (D-037, supersedes the State Tree part of D-007/D-018): the MCP tools can't author State Tree or BT assets, and C++ is fully testable by agents.

**Architecture:**
- `ALBWarden : ACharacter` (placeholder body in `BP_Warden`).
- `ALBWardenController : AAIController` with `UAIPerceptionComponent` (sight + hearing, detects neutrals).
- `ULBWardenBrainComponent`: the states Dormant, Patrol, Investigate (with a "suspicious" look-around), Search, Chase, Attack and Return.
- `ULBWardenTuningData` (`DA_WardenTuning`): every speed, range, timer and stage gate.
- **Stage gating** from the `State.Warden.Stage.N` tags (D-018):
  - Stage Ã¢â€°Â¤2: no AI pawn (scripted silhouettes stay as they are).
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
| P5-001 | C++: the Warden classes above, perception and noise wiring, the brain state machine, tuning data, the markers, checkpoint refusal, debug drawing; `AIModule`/`NavigationSystem` dependencies | warden-ai | Ã¢â‚¬â€ | HIGH |
| P5-002 | Content: project navigation set to runtime **Dynamic**, so doors change the navmesh; NavMeshBoundsVolume(s) in `L_Monastery`; a `L_Test_Warden` map (corridor loop, occluding pillars, a sound-test room, an unreachable ledge, a door, NavMesh) | environment-designer | Ã¢â‚¬â€ | MED |
| P5-003 | `BP_Warden` (tall dark placeholder body, capsule about 55Ãƒâ€”145) and `DA_WardenTuning`; replace the crypt `BP_WardenPlaceholderKill` with the real Warden flow (spawn, patrol and search points in the crypt and cloister) | blueprint-engineer + environment-designer | P5-001, P5-002 | MED |
| P5-004 | AI tests in `L_Test_Warden`: sight vs blocked sight; hearing walk vs sprint vs crouch; investigate the noise location; lose the target Ã¢â€ â€™ search Ã¢â€ â€™ return; an unreachable player; stuck recovery; repeated chases; chase speed below player sprint; a catch kills; checkpoint refused during a chase; RouteBot and WalkPath still green | warden-ai | P5-001..003 | MED |
| P5-REV/QA | Architecture review; the owner plays against the Warden repeatedly (difficulty, intelligence, predictability, fairness, chase speed, search time, atmosphere) | reviewers + owner | all | Ã¢â‚¬â€ |

## Phase 6 Ã¢â‚¬â€ Art-kit discovery: task breakdown
Branch: `claude/phase-06-art-kit`. Owner choices: **grounded photoreal** look; **free assets only** (D-040). The greybox (`L_Monastery`) is **not touched**. Samples live in a separate art-test map, so the area art phases (7Ã¢â‚¬â€œ10) start from approved families rather than from guesses.

**Sources, in priority order:** existing project content (nothing photoreal: only the template, `LevelPrototyping` and the greybox) Ã¢â€ â€™ free Fab listings (including any free Megascans; the owner claims them, never an agent) Ã¢â€ â€™ CC0 libraries through the local `3d-assets-local` MCP (Poly Haven, ambientCG, TextureCan and others; D-041) Ã¢â€ â€™ 3d.shep.bot / Blender for custom assets only.

| Task | Objective | Owner | Depends on | Risk |
|---|---|---|---|---|
| P6-001 | Discovery: per-area asset families (architecture kit, floors and ground, walls and masonry, roofs and wood, props, vegetation and roots, decals, sky/HDRI) for the Courtyard, Chapel, Crypt and Bell Tower; 1Ã¢â‚¬â€œ3 candidates per family with source, licence, price, download method and the reason it fits; the custom-asset list (Warden, mask, three mechanisms, symbols, finale bell) with a production route; the list of free Fab items the owner must claim. Output `Docs/ASSET_PLAN.md` | asset-curator | Ã¢â‚¬â€ | MED |
| P6-002 | Download a representative CC0 sample set (about 12Ã¢â‚¬â€œ20 items at 2K: hero masonry, flagstone, plaster, wood, iron, roots/moss, ground, a night HDRI, a few scanned props) into `ExternalAssets/Incoming/`; one `ASSET_REGISTRY.md` row per item | asset-curator | P6-001 | LOW |
| P6-003 | Import the samples into `Content/LastBell/ArtTest/` with correct texture settings (sRGB off for packed/normal maps, BC5 normals, 2K max); a first `M_LB_Surface` master (base PBR, texel-density UV scale, world-aligned macro variation, wetness scalar) with one MI per material; Nanite on scanned meshes | technical-artist | P6-002 | MED |
| P6-004 | `L_Test_ArtKit`: four small bays (Courtyard, Chapel, Crypt, Bell Tower) dressed only with the samples, plus a night/moon light rig, height fog and the HDRI; the `CaptureViewport` screenshots for review in `Docs/ArtTest/` | environment-designer | P6-003 | MED |
| P6-REV/QA | No new errors in the logs; texture/Nanite settings checked; 78 tests still green; `L_Monastery` unchanged (`git diff`); registry complete; owner review of families and screenshots | qa-reviewer + owner | all | Ã¢â‚¬â€ |

## Phase 7 â€” Courtyard art: task breakdown
Branch: `claude/phase-07-courtyard`. Scope: the **Approach** path and the **Courtyard** (X -3000..6000; GREYBOX_SPEC) plus the exterior faces of the gatehouse, the chapel west front and the distant tower silhouette as seen from the courtyard. Interiors and the other areas are untouched. Gameplay actors (doors, key, checkpoints, triggers, Warden markers) keep their positions, tags and labels.

**Kit approach (D-044):** a custom modular kit authored **procedurally in Blender 5.2 headless** (Python/bmesh scripts in `Tools/blender/kit/`, reproducible from git; `.blend` and FBX outputs in `SourceArt/Kit/` under LFS). Pieces are snapped to a 50 cm grid, pivots at the bottom-left-back corner, real-world scale, UV0 at about 1 texel unit per cm for trims plus world-aligned materials (`M_LB_Surface` bWorldAlignedUV) for large faces. Bevelled edges so the light catches them. Nanite on, simple collision.

| Task | Objective | Owner | Depends on | Risk |
|---|---|---|---|---|
| P7-001 | Kit spec `Docs/MODULAR_KIT.md`: the piece list for the courtyard and approach and reusable later (wall 400/200/100 Ã— 800 tall Ã— 60 thick, broken-top wall variants, wall end/corner, buttress, plinth/base course, cornice/coping trim, pointed-arch doorway 120Ã—240 clear (Warden stoops; D-038), gate arch, window frame, column/pier, stair step block, flagstone tile/slab, rubble chunks), dimensions, pivot, naming `SM_LB_Kit_*`, material slots | environment-designer | â€” | LOW |
| P7-002 | Build the kit in Blender headless from scripts; export FBX; import to `/Game/LastBell/Environments/Kit/` with world-aligned MIs; a kit review row in `L_Test_ArtKit`; screenshots to the owner (mid-phase look check, not a gate) | technical-artist | P7-001 | MED |
| P7-003 | Dress the Approach and Courtyard in `L_Monastery`: replace the greybox primitives with kit pieces at the same footprint; cliff walls from rock materials/meshes; wet flagstone ground; gatehouse, well house (key location), collapsed wall rubble (still blocks the direct line), puddles, props; keep every gameplay actor and the navmesh valid | environment-designer | P7-002 | HIGH |
| P7-004 | Minimum courtyard look for review: sky sphere (D-046), moon, height fog, warm accent at the gatehouse; a light pass only (Phase 14 owns final lighting); review screenshots from fixed viewpoints | environment-designer | P7-003 | MED |
| P7-QA | RouteBot + WalkPath + Warden reachability green on `L_Monastery`; no new log errors; collision walk-test of the courtyard; texture/triangle sanity; owner playtest of the courtyard | qa-reviewer + owner | all | â€” |

## Phase 7 fix set 2 — Courtyard polish (P7-FIX2)
Branch `claude/p7-courtyard-polish`. Full, explicit spec: `Docs/plans/P7_FIX2_COURTYARD_POLISH.md` (owner-approved 2026-10-24). Decisions D-048..D-053.

| Task | Objective | Owner | Depends on |
|---|---|---|---|
| P7F-0 | Branch, plan, decisions, model/effort rule | lead | — |
| P7F-1 | 16 Poly Haven CC0 models + 2 ambientCG decals downloaded (glTF 2K), registry rows | asset-curator | P7F-0 |
| P7F-2 | Blender: CC0 conversion (bottom-centre pivots, UCX) + procedural key, ledge, gravestones, crosses, mound, hand-cart, fire pit; verify + renders | technical-artist | P7F-1 (2a), — (2b) |
| P7F-3 | Puddle + Desaturation layers in M_LB_Surface, M_LB_Foliage, M_LB_Mist, MIs, imports, Fab relocation, key child BP | technical-artist [EDITOR] | P7F-2, owner Fab steps |
| P7F-4 | L_Monastery: remove discs, puddled floors, new key + ledge, work area, graveyard, cart of the dead, overgrowth, decals, 3 courtyard WalkPaths | environment-designer [EDITOR] | P7F-3 |
| P7F-5 | Moon/fill/skylight fixes, height + volumetric fog, Local Fog Volumes, fog sheets, Niagara smoke wisp, exposure | lighting-vfx [EDITOR] | P7F-4 |
| P7F-6 | 78/78 + new WalkPaths, lane check, 12 clean captures, owner playtest + stat gpu, docs | qa-reviewer + lead + owner | all |

## Phase 7 fix set 3 — Courtyard restructure (P7-FIX3)
Branch `claude/p7-courtyard-polish` (continues P7-FIX2). Full spec: `Docs/plans/P7_FIX3_COURTYARD_RESTRUCTURE.md` (owner-approved 2026-10-25). Decisions D-055..D-058.

| Task | Objective | Owner | Depends on |
|---|---|---|---|
| G0 | Spec, decisions, plan table | lead | — |
| G1 | CC0 downloads: tall grass, dry bush, shrub, dead trunk, CC0 dead tree, ivy/dead-leaf atlases, moss texture | asset-curator | G0 |
| G2a | Blender: arcade bays (intact + 2 broken), kerbs, well-head, timber roof set, earth patch, ivy cards, dead tree, CC0 conversions | technical-artist | G0 (ivy/tree/conversions after G1) |
| G3 | Floor growth layer in M_LB_Surface, M_LB_FoliageMasked, light-function flicker material, imports, MIs | technical-artist [EDITOR] | G2a |
| G4 | L_Monastery: remove fountain + tiny plants, arcade, roofed walks, beds, well-head, trees, ivy, new WalkPaths, lane check, tests | environment-designer [EDITOR] | G3 |
| G5 | Vegetation scatter (PCG, fallbacks ISM/actors) | environment-designer / technical-artist [EDITOR] | G4 |
| G6 | Darkness, contrast and flicker pass; luma targets | lighting-vfx [EDITOR] | G5 |
| G6b/G6c | Storm sky (SkyAtmosphere hidden, fog cutoff), colour grading, centrepiece pool, third route lantern, tower fills (amendment B3, D-059) | lighting-vfx [EDITOR] | G6 |
| G7 | QA, docs, owner stat gpu + playtest | qa + lead + owner | all |

Status 2026-10-25: G0–G6c done (latest fefe4f7; suite 78/78 after each editor task). G7: independent QA passed with no blocking defects (doc fixes 9829e48); owner `stat gpu` at High 13.1 ms (≤ 16.6). Awaiting the owner's playtest and review.

## Phase 8 — Chapel art: task breakdown
Branch `claude/phase-08-chapel`. Full spec: `Docs/plans/P8_CHAPEL_ART.md`. Owner choices 2026-10-25: timber roof with one fallen bay, glowing glass + coloured floor light, desecrated-but-restrained dressing, interior as dark as the courtyard (D-061…D-064).

| Task | Objective | Owner | Depends on |
|---|---|---|---|
| P8-0 | Spec, plan table, decisions, risks | lead | — |
| P8-1 | CC0 downloads: limestone floor (Tiles139), roof slates (roof_slates_03); registry | asset-curator | P8-0 |
| P8-2 | Read-only survey: clue window, puzzle candles, mechanism, silhouette, misc actors, decal/glass materials, step height | technical-artist [EDITOR read-only] | P8-0 |
| C1 | Lead amendment: clue-window opening, clue re-skin, altar fit, candle stand, silhouette capture | lead | P8-2 |
| P8-3 | Blender: nave bays (lancet/door/clue), east wall + tracery, gables, corbels, dais, roof slabs (+broken), ridge, truss, pews, rail, lectern, altar, shards, finial, glass, cobwebs; generated glass/chalk/cobweb textures | technical-artist | C1 |
| P8-4 | Materials (floor, interior masonry, slate, old wood, stained glass opaque/translucent, light-pool and chalk decals, cobweb, backdrop) and imports; statue/candleholder relocation | technical-artist [EDITOR] | P8-1, P8-3 |
| P8-5 | Structure: walls, sacristy, roof, trusses, floors, choir, glass, crypt-door leaf, greybox removal, chapel WalkPaths, lane check, tests | environment-designer [EDITOR] | P8-4 |
| P8-6 | Dressing: pews, ritual circle, statues, lectern, candles, collapse debris, cobwebs, sacristy, clue re-skin | environment-designer [EDITOR] | P8-5 |
| P8-6b | Puzzle prop re-skin by BP template edits with verification and revert (clue frame, candle stand/wax, mechanism cylinder/marker); amendment C1 | unreal-blueprint-engineer [EDITOR] | P8-6 |
| P8-7 | Lighting: greybox lights out, candle clusters, moon shafts, roof-hole shaft, coloured pools, glass emissive, nave mist; luma targets and readability gates | lighting-vfx [EDITOR] | P8-6 |
| P8-9a/b | Owner feedback C4: moon-consistent shadowed window light, soft shaft cards, roof-hole shaft, doorway fog overlap fix | technical-artist, lighting-vfx [EDITOR] | P8-7b |
| P8-10 | Owner note C5: grime pass (floor dust in joints, soot/damp/mould decals, leaves and debris, dust on surfaces, more cobwebs) | technical-artist + environment-designer [EDITOR] | P8-9b |
| P8-8 | QA, docs, owner stat gpu + playtest; PHASE 8 READY FOR YOUR REVIEW | qa + lead + owner | all |

Status 2026-10-27: P8-0…P8-10d done (latest 01b29d9; suite 78/78 incl. ChapelNave, ChapelSacristy, SacristyToCrypt, RouteBot). QA (P8-8) passed with no blocking defects; owner playtest feedback handled (C4 window light + doorway exposure, statues facing front, C5 grime + aged altar/table); owner stat gpu 14.99 ms. Awaiting owner review.

## Phase 9 — Crypt art: task breakdown
Branch `claude/phase-09-crypt`. Spec: `Docs/plans/P9_CRYPT_ART.md` (D-067). P9-0 plan → P9-0b owner migrate → P9-1 CC0 downloads ∥ P9-2 relocation + survey → D1 amendment → P9-3 custom pieces → P9-4 materials/imports → P9-5 structure → P9-6 dressing → P9-7 lighting → P9-8 QA + owner review.

| Task | Scope | Owner | Depends on |
|---|---|---|---|
| P9-0 | Spec outline, pick list, D-067, risks | lead | — |
| P9-0b | Migrate the Dungeon architecture pick list | owner | P9-0 |
| P9-1 | CC0 downloads (roots, leak decals) | asset-curator | P9-0 |
| P9-2 | Relocate + measure the Dungeon pieces, test assembly, crypt survey | technical-artist [EDITOR] | P9-0b |
| D1 | Exact layout (generator `Tools/crypt/gen_crypt_layout.py`), D-068…D-071, R-36…R-38 | lead | P9-2 |
| P9-3 | 17 custom Blender pieces + water ripple normal | technical-artist (no editor) | D1 |
| P9-4 | Imports, darkened pack MIs, crypt MIs, M_LB_Water, Nanite on bones | technical-artist [EDITOR] | P9-3 |
| P9-5 | Structure: hide greybox, backdrop, walls, portals, vaults, columns, ossuary bays, floor, stairs, ceilings, water; gap pass | environment-designer [EDITOR] | P9-4 |
| P9-6a | Dressing + decals + plaque frame; lane check | environment-designer [EDITOR] | P9-5 |
| P9-6b | Puzzle-prop child Blueprints (crank, gate, rubble, winch) | unreal-blueprint-engineer [EDITOR] | P9-4 |
| P9-7 | Lighting: torches, candles, brazier, moon grates + shafts, LFV, PP_Crypt; luma targets | lighting-vfx [EDITOR] | P9-6a, P9-6b |
| P9-8 | QA, docs, owner stat gpu + playtest; PHASE 9 READY FOR YOUR REVIEW | qa + lead + owner | all |

Status 2026-10-29: P9-0…P9-7 done (P9-5 325bec8, abc167f; P9-6a e066901 and fix sets 8fa049a, b7f63c4, a2bc978; P9-6b 621d02b, a50a573, 3a9b0de; P9-7 c5bfc12 … fe82dca; suite 78/78, crypt WalkPaths, RouteBot, Puzzles/Save tests and Warden crypt patrol pass). Owner review fix set R1 done (R1-A db20f3f, R1-C 5fbef54, R1-B 88092f8 … fa95078: rail enclosures, note clue, aged props, stained-glass saints, chapel moon gobos). Owner review fix set R2 done (R2-A 0bf92d9, 76b443a, R2-A2 71d2ac9, R2-A3 fe11ba4, R2-B 73e1f16, f2b3a20, R2-B2 a0e5f34, R2-C d3a7e19: bell wheel, dial levers, dungeon doors, beam fix, roof gobo, note aim). P9-8a docs done (D-072…D-076, R-36…R-41, MCP_NOTES crypt section, PERFORMANCE_BUDGET and ASSET_REGISTRY). P9-8b QA skipped by the owner. Owner playtest signed off 2026-10-29 ("I have reviewed and its fine"); owner GPU 14.72 ms at High in the ossuary. Owner approved and merged into `main` 2026-10-29 (fb5c3ba).

## Phase 10 — Cloister and Bell Tower art: task breakdown
Branch `claude/phase-10-belltower`. Spec: `Docs/plans/P10_BELLTOWER_ART.md` (D-077). Owner choices 2026-10-29: cloister and tower in one phase; timber stairs around an open shaft; half-collapsed louvred belfry with the great cracked bell; roofed vaulted cloister walk with a fallen bay and cell doors. Collision stays the greybox collision (D-068 approach).

| Task | Scope | Owner | Depends on |
|---|---|---|---|
| P10-0 | Outline, D-077, R-42…R-45, plan table | lead | — |
| P10-1 | CC0 downloads: bell rope, bronze patina | asset-curator | P10-0 |
| P10-2 | Read-only survey: greybox geometry, gameplay BPs, AI markers, reusable kit, sight lines, captures | technical-artist [EDITOR read-only] | P10-0 |
| D1 | Exact layout (generator `Tools/belltower/gen_tower_layout.py`), D-078…, risks | lead | P10-1, P10-2 |
| P10-3 | Blender pieces: vault bays, tower shell stages, timber stair set, belfry, bell frame, great bell, small-bell frame, cell door | technical-artist (no editor) | D1 |
| P10-4 | Materials and imports | technical-artist [EDITOR] | P10-3 |
| P10-5 | Structure: hide greybox, cloister, passage, tower shell, stairs, belfry, roof | environment-designer [EDITOR] | P10-4 |
| P10-5b | Roof valley pieces C14V L/R (Blender, verify, renders, import) (D1.14, D-082) | technical-artist [EDITOR for import] | P10-5 |
| P10-5c | Re-place the 13 roof records, Ground_3/5, Perim_* masonry, 3 belfry poses, suite (no captures) | environment-designer [EDITOR] | P10-5b |
| P10-5d | Re-capture the roof/perimeter-affected poses with the editor in the foreground; review | lead + owner [EDITOR] | P10-5c |
| P10-6a | Dressing: garth, cells, rubble, timber debris, bell rope, lanterns, grime; generator corrections and dress/decal placement (D1.20) | environment-designer [EDITOR] | P10-6d |
| P10-6e | Fix set after the P10-6a capture review: chain at the drum (lead error), denser garth (rooibos, shrubs, bigger grass, matte mossy earth MI), random belfry debris (D1.21) | environment-designer [EDITOR] | P10-6a |
| P10-6b | Child BPs: small bells, inscription, Mech 3, great bell, tower and shortcut doors | unreal-blueprint-engineer [EDITOR] | P10-4 |
| P10-6c | Capture the 12 Mech 3 / door / great bell / note views with the editor in the foreground; review (D1.19) | lead + owner [EDITOR] | P10-6b |
| P10-6d | `Door_Shortcut` leaf Z scale 1.0818 → 1.30 to close the light wedges under the tympanum (D1.19); step 0 of P10-6a | environment-designer [EDITOR] | P10-6c |
| P10-7 | Lighting: moon through the fallen roof and louvres, lanterns, candles, tower slit light; luma targets (spec D1.23: courtyard lantern style, L_Ps_West, cell candles, LFV_Tower stack, PP_Cloister) | lighting-vfx [EDITOR] | P10-6e |
| P10-7b | Lighting tuning after the PIE Simulate review: EV 0.65, cooler hot lanterns, old-bronze MI, tower moon spots + shaft cards (D1.24) | lighting-vfx [EDITOR] | P10-7 |
| P10-8a | Docs (MCP_NOTES P10 section, PERFORMANCE_BUDGET, ASSET_REGISTRY, RISKS, D-083) and Tools/crypt/capture_session.py (D1.26) | general-purpose (no editor) | P10-7b |
| P10-8b | QA: suite, live checks, logs, generator lane re-check, git/asset hygiene (D1.26) | qa-reviewer [EDITOR read-only] | P10-7b |
| P10-8c | Owner stat gpu + playtest; PHASE 10 READY FOR YOUR REVIEW | lead + owner | P10-8a, P10-8b |
| P10-8d | Fix set from the owner review: lantern brackets, plumb arch lantern, carved memorial tablet (option B) and named graves, moon lights inside the slits, roof spot and outside tower lights removed, chapel west-front backing, no prompt on a used mechanism (D1.27, D-084) | technical-artist, gameplay-programmer, environment-designer, unreal-blueprint-engineer, lighting-vfx + lead + owner | P10-8c |

Status 2026-10-30: P10-0…P10-4 done (P10-3a ba1f0e6/27ae1dc, P10-3b b22300f/42307f1, P10-L final 0e621ec, P10-4 8733d97). P10-5 structure (4919443…2e3a379) plus the roof-valley fix set (D1.14–D1.16, D-082): P10-5b fda215d/1b8d2f3, P10-5c 291c4f5/54b0326, P10-5d captures (lead + owner); suite 78/78. Structure pass complete. P10-6b child BPs (1ac66e2…6a22bf7, D1.17/D1.18; suite 78/78). P10-6c captures and review (D1.19): everything passes except the `Door_Shortcut` light wedges, fixed by P10-6d. P10-6d + P10-6a done (6e8b78b…c59e21a; 242 dress, suite 78/78); capture review D1.21: door fixed, chain/garth/belfry debris fail. P10-6e done (cacb196…0f4421c; 278 dress, suite 78/78; captures accepted, D1.22). Dressing pass complete. P10-7 placed (f58d697, 61b9f38; suite 78/78); PIE Simulate review D1.24. P10-7b done (12b47ba…44a5d19; suite 78/78); captures D1.25 accepted (luma on target, tower moonbeams visible). Lighting pass complete. P10-8 (D1.26): 8a docs 43490a1 + TECHNICAL_DESIGN drift fix 584af02; 8b QA 65992e5 (suite 78/78, 538/538 placements, lighting 51/51, greybox 280/280, generator 54/54, lanes >= 70.3 cm; F1 stale count fixed, re-run 29/29). P10-8c owner review: findings fixed in P10-8d (D1.27; F1 9de5059, F2 5827489, F3 1943ba7, F4/F6 c1a6cc4…1997daa, F5 c00e0ae, F7b f7e2b14; real build 79/79). **Phase 10 approved by the owner 2026-11-01** and merged to main. Open: stat gpu figure (R-44).

## Phase 11 — Materials: task breakdown
Branch `claude/phase-11-materials`. Spec: `Docs/plans/P11_MATERIALS.md` (D-085). Owner approved the plan on 2026-11-02; the chapel and sacristy door corners and the `Gobo_Moon` specks stay out of scope.

| Task | Scope | Owner | Depends on |
|---|---|---|---|
| P11-0 | Plan approval; D-085, R-46, R-47, plan table | lead + owner | — |
| P11-1 | GPU baseline: `stat gpu` at 6 spots | owner | P11-0 |
| P11-2 | Census (read-only) and 24 baseline captures | technical-artist [EDITOR read-only], lead + owner | P11-0 |
| P11-3 | Joint test in a separate test map; the owner chooses A or B (D-086) | asset-curator, technical-artist [EDITOR], lead + owner | P11-2 |
| P11-4 | Apply the owner's choice across the game | technical-artist [EDITOR] | P11-3 |
| P11-5 | Weathering layer `bWeathering` in `M_LB_Surface` and rollout | technical-artist [EDITOR] | P11-4 |
| P11-6 | Decal retune; new crack decals and their placement | technical-artist, environment-designer [EDITOR] | P11-5 |
| P11-7 | Glowing lantern glass | technical-artist [EDITOR] | P11-2 |
| P11-8 | Brightness re-check, QA, docs, owner GPU and playtest; PHASE 11 READY FOR YOUR REVIEW | lead + qa-reviewer + owner | all |

Status 2026-11-02: P11-0…P11-2 done (GPU baseline: all 6 spots under budget, chapel 15.32 ms; census 7b5941b; 24 baseline captures). P11-3 waits for the owner's go.

Status 2026-11-04: P11-0…P11-7 done (D-086, D-087). P11-8: brightness re-check and one MI correction done (D-088), independent QA passed with caveats (`Docs/ArtTest/materials/p11_8_qa.md`, suite 79/79), docs done. Owner's six-spot `stat gpu`: all under 16.6 ms, highest chapel 14.96 ms (R-44 closed). Owner said "approve and merge" on 2026-11-04: Phase 11 merged to `main`. R-26 and R-46 closed; R-47 stays open until the first run after a cold start. Phase 12 waits for the owner's approval.

## Phase 12 — Warden visual: task breakdown
Branch `claude/phase-12-warden-visual`. Spec: `Docs/plans/P12_WARDEN_VISUAL.md` (D-089). Owner approved the plan on 2026-11-04. Animation is Phase 13.

| Task | Scope | Owner | Depends on |
|---|---|---|---|
| P12-0 | Plan approval; D-089, R-49…R-52, plan table | lead + owner | — |
| P12-1 | Pipeline spike: a test figure through Blender, FBX and Unreal | technical-artist [EDITOR], lead for captures | P12-0 |
| P12-2 | Downloads; hand comparison | asset-curator, technical-artist | P12-0 |
| P12-3 | Three concept blockouts; the owner supplied their own build instead (D-090) | technical-artist, owner | P12-1 |
| P12-4 | Copy V5 into the project, move it under `Characters/Warden`, check it | lead, technical-artist [EDITOR] | P12-3 |
| P12-5 | Clearance on the Warden's routes; silhouette mesh | technical-artist [EDITOR] | P12-4 |
| P12-6 | Read review in the game's real lighting | lead + owner | P12-5 |
| P12-7 | Fixes the review calls for | technical-artist | P12-6 |
| P12-8 | `BP_Warden` and `BP_WardenSilhouette` swap | unreal-blueprint-engineer [EDITOR] | P12-7 |
| P12-9 | QA, docs, GPU readings, playtest; PHASE 12 READY FOR YOUR REVIEW | qa-reviewer + lead + owner | all |

Status 2026-11-04: P12-0…P12-3 done; the owner chose their own Warden Art V5 (D-090), so the scripted build is dropped. P12-4 to P12-8 done on V5.5 (D-091): read review passed, wired into `BP_Warden` and both silhouettes, suite 79/79, QA passed with caveats. GPU readings passed (highest 15.33 ms). The owner's playtest led to fix set 1 (`Docs/plans/P12_FIX1_WARDEN_APPEARANCES.md`, D-092): done on 2026-11-06, owner's playtest "all good", QA passed with caveats, suite 92/92. **Approved and merged by the owner on 2026-11-06** after the leftovers were deleted. Next: Phase 13 (animation), not started until the owner approves its plan.

## Phase 13 — Warden animation: task breakdown

Branch `claude/phase-13-warden-animation`. Spec: `Docs/plans/P13_WARDEN_ANIMATION.md` (D-093). Owner approved the plan on 2026-11-06: Mixamo motion capture, slow heavy stalker, all four extras.

| Task | Scope | Owner | Depends on |
|---|---|---|---|
| P13-0 | Plan approval; D-093, R-55…R-58 | lead + owner | — |
| P13-1 | Mixamo downloads | owner | P13-0 |
| P13-2 | Anim instance, anim set, stoop zones, catch camera, apparition walk, tests | gameplay-programmer | P13-0 |
| F0 | Physics bodies, door and stair transforms | lead [EDITOR read-only] | P13-0 |
| P13-3 | Import Y Bot and clips; registry rows | animation-specialist [EDITOR], asset-curator | P13-1 |
| P13-4 | Retarget, measure, blend spaces, montages | animation-specialist (headless) | P13-3 |
| P13-5 | Contact sheet and clip choices | lead + owner | P13-4 |
| P13-6 | `ABP_Warden` and its graph | animation-specialist, owner if needed | P13-5 |
| P13-7 | Physics and hookup | animation-specialist, unreal-blueprint-engineer [EDITOR] | P13-6 |
| P13-8 | Performance readings, Insights trace | owner + performance-engineer | P13-7 |
| P13-9 | QA, docs, playtest; PHASE 13 READY FOR YOUR REVIEW | qa-reviewer + lead + owner | all |

**Status, 2026-11-07:** P13-0 to P13-8 are done. In-game look and fixes:
- **Turns:** turn speeds slowed at the owner's request (RotationRate 120, TurnRate 90, trigger 45°).
- **Frozen limbs:** the blend spaces lacked runtime data. The owner re-saved them in the Blend Space editor, and the limbs move.
- **Second look:** "legs and arms move now, all good now".

P13-8, `stat anim`:
- animation about 0.2 ms on the game thread; GPU 13.6–14.2 ms;
- the hidden chapel apparition no longer animates every frame.

Owner playtest: "all good". Wrap-up:
- **Mixamo files (D-094):** the Y Bot, its raw clips and the review FBX are kept out of the public repo (git-ignored; branch history rewritten before any push) and are never cooked.
- **Leftovers:** `ABP_P13_Spike` deleted.
- **Docs:** updated.

**QA (P13-9, `Docs/ArtTest/warden/p13_qa.md`): PASS WITH CAVEATS, no high-severity findings.**
- **C1, a flaky apparition wait from Phase 12:** fixed in 5fab227. The test now waits for `Hold`, then checks the alpha.
- **Doc flags:** fixed.

**Final real-project suite: 112/112.** The apparition functional tests passed 3 more runs, 7/7 each.

**Editor read-back (2026-11-07):**
- `check_warden.py`: 61/61; `--bp` 56/56; `--disk` 32/32. The checker now expects `turnRate` 90 and reads an empty byte default as 0 (4335df4).
- `BP_Warden` `RotationRate` yaw is 120, on the class default and the placed instance (QA C7).
- Both placed apparitions' `Figure`: `OnlyTickPoseWhenRendered`.

**Open items, for the owner's review:**
- coverage gaps: no automated test for foot IK, turn montages, look-around or foot sliding (owner-verified in play);
- three unused retargeted clips, which stay in the project unreferenced.

**Owner review (D-095):** the 12 retargeted Mixamo clips are now kept out of the public repo as well (git-ignored, history rewritten again). A fresh clone has an unanimated Warden; the owner keeps a private copy of `ExternalAssets/Incoming/mixamo/`.

**Approved and merged by the owner on 2026-11-07** ("approve and merge"). Next: Phase 14, which doesn't start until the owner approves its plan.

## Phase 14 — Lighting and the storm's light: task breakdown

Branch `claude/phase-14-lighting-storm`. Spec: `Docs/plans/P14_LIGHTING_STORM.md` (D-096, D-097, D-098). Owner approved the plan on 2026-11-07: lighting plus the storm's light and motion; the storm builds with the story; lightning for atmosphere, scripted beats and reveals; a small set of story-driven light changes. **Phase 15 = particles** (rain, splashes, drips, dust and mist, visible bolts, candle-flame effects, cloth).

| Task | Scope | Owner | Depends on |
|---|---|---|---|
| P14-0 | Plan approval; D-096…D-098, R-59…R-63 | lead + owner | — |
| F0 | Read-only survey (lights, PP, sky MIs, glass, shafts, pools, foliage MIs, ISMs, garth bounds, decal points) | lead [EDITOR read-only] | P14-0 |
| P14-B | Baseline readings at the six BugItGo spots; "before" captures | owner + lead | P14-0 |
| P14-1 | Storm C++ (subsystem, settings, zones, light groups, logic, console, apparition flag) and tests | gameplay-programmer (Unreal closed) | P14-0 |
| P14-1b | Glow actors on `ALBStateLightGroup`: lantern glass follows its light (D-099, plan section 8.1) and tests | gameplay-programmer (Unreal closed) | F0 |
| P14-2 | Materials and assets (MPC, DA, storm sky, glass/shaft/pool flash, reveal decals, wind sway) | technical-artist [EDITOR] | P14-1, F0 |
| P14-3 | Level work (tags, zones, PP restructure, light groups with glow actors, decals, apparition flags, WPO distance) | lighting-vfx [EDITOR] | P14-1b, P14-2 |
| P14-4 | Look session: flash preset, chapel EV, grade, wind, R-31 | lead + owner | P14-3 |
| P14-4 wind fix | Scale-aware sway height in `MF_LB_WindSway` and storm-strength amplitudes on 8 MIs (D-100, `Docs/plans/P14_4_WIND_FIX.md`); the owner then tuned the wind live | technical-artist [EDITOR] | P14-4 live check |
| P14-5 | Apply choices, exposure targets, readability after story changes, R-09 | lighting-vfx; captures with the owner | P14-4 |
| P14-5a | Apply and save the owner's P14-4 choices: wind values in `DA_StormSettings` and 8 MIs, `PP_Chapel` EV 1.6, grade B, two reveal decals moved (`Docs/plans/P14_5_APPLY.md` Part A) | lighting-vfx [EDITOR] | P14-4 |
| P14-5b | Part B: area exposure against the targets on the wide views, readability after the five story changes, R-09 (32 Simulate captures with the candle proxy); D-102 | lead + owner | P14-5a |
| P14-5c | Part C: `PP_Outdoor_Night` EV100 1.15 → 1.40 written to the editor world and saved | lighting-vfx [EDITOR] | P14-5b |
| P14-6 | Viewpoint approval and storm run-through | owner | P14-5 |
| P14-7 | Performance and report | owner + performance-engineer | P14-6 |
| P14-8 | QA, docs, suite, playtest; PHASE 14 READY FOR YOUR REVIEW | qa-reviewer + lead + owner | all |

**Status 2026-11-08:** P14-0 to P14-8 are done; PHASE 14 READY FOR YOUR REVIEW (QA: no blocking defects, `Docs/ArtTest/lighting/p14_8_qa.md`). Key commits (`git log --oneline main..HEAD`):
- **P14-0 and F0:** plan approved (d4cbf48); read-only survey (0c711b8).
- **P14-B:** baseline readings (1584042, ea182be) and the "before" capture set (a38e0b6).
- **P14-1 and P14-1b:** storm code (da7d195); glow actors, D-099 (spec c626dd7, code b42c69c).
- **P14-2:** storm MPC, flash function, `DA_StormSettings`, flash-driven materials (2572b3a); wind sway materials (ac57277, ac7cbad).
- **P14-3:** level work (5595f7e); decal check under a frozen flash (821563c).
- **P14-4:** wind fix, D-100 (f9261e6); look-session captures and results (45ae203, 91c385e); the owner's choices, D-101 (6154914).
- **P14-5:** plan (79ba774); apply and save (4e2a3e8); Part B tools and captures (3b1503e, 9a164d2); courtyard EV 1.40, D-102 (59fc468).
- **P14-6:** approval captures (a58b9d9); owner approved the viewpoints and the storm run-through (105d146).
- **P14-7:** readings (b6621bc); game-thread re-read (313c5cc); closed as passed on Phase 14's own cost (03826ed).
- **Outcome:** GPU passes at all six spots; the storm's game-thread cost is +0.16 ms and the rise against P14-B is story state, so the new R-64 goes to the Phase 18 optimisation pass. R-09, R-31 and R-59…R-63 are closed; D-101 and D-102 are logged.
- **Suite:** final run with the editor closed (`Tools/build_and_test.ps1`, 2026-11-08): build succeeded, **128 passed, 0 failed**, 0 errors, 0 invalid tags.

## Phase 15 — Particles: task breakdown

Branch `claude/phase-15-particles`. Spec and plan: `Docs/plans/P15_PARTICLES.md` (D-103, D-104, D-105). The owner approved the plan on 2026-11-08:
- constant heavy rain outdoors;
- sky bolts plus scripted tower strikes;
- animated candle flames, and Niagara torches;
- wind-driven cloth (material);
- rain occlusion by distance-field collision, with a spike first (fallbacks: baked roof map, then hand-placed rain boxes).

| Task | Scope | Owner | Depends on |
|---|---|---|---|
| P15-0 | Plan approval; D-103…D-105, R-65…R-69 | lead + owner | — |
| F0 | Read-only survey: flames and their owners, fire actors, roofs and openings, tower top, shafts, crypt water, ceilings, eaves, cloth points, curtain spots, sky radius, Niagara toolset, global distance field | lead [EDITOR read-only] | P15-0 |
| S1 | Rain occlusion spike (distance-field collision, thin roofs, MCP Niagara capability); verdict before P15-5 | lighting-vfx [EDITOR]; captures lead + owner | F0 |
| P15-1 | `ULBStormFXSubsystem`, `ULBStormFXSettings`, `ALBLightningBolt`, `LBStormFXLogic`, strike targets and `OnLightningStrike`, console, tests | gameplay-programmer (Unreal closed for the build) | P15-0 |
| P15-2 | Procedural FX textures; CC0 fabric | technical-artist + asset-curator | P15-0 |
| P15-3 | Cloth and FX card meshes (Blender) | technical-artist | P15-0 |
| P15-4 | FX materials and `MF_LB_ClothWave` | technical-artist [EDITOR] | P15-2 |
| P15-5 | Niagara systems | lighting-vfx [EDITOR] | S1, P15-4 |
| P15-6 | Data assets and level work | lighting-vfx [EDITOR] | P15-1, P15-3, P15-5 |
| P15-7 | Look session | lead + owner | P15-6 |
| P15-8 | Apply the choices | lighting-vfx [EDITOR] | P15-7 |
| P15-9 | Viewpoints, occlusion checks, storm run-through | lead + owner | P15-8 |
| P15-10 | Performance (FX on/off at a matched story state) | owner + performance-engineer | P15-9 |
| P15-11 | QA, docs, full suite; PHASE 15 READY FOR YOUR REVIEW | qa-reviewer, docs agent, lead | all |

**Outcome** (results in `Docs/plans/P15_PARTICLES.md`, "Results"; commits from `git log --oneline main..HEAD`):
- **P15-0 and F0:** plan (7087248); the Phase 15 table, D-103…D-105 and R-65…R-69 (09e8cd6). Read-only survey of `L_Monastery` (e92b465) and its values in the plan (f46ddc4): 22 flame actors, 5 Cascade fires, roof openings, the strike target, 11 shafts, drips, eaves, cloth points. Nothing was set or saved.
- **S1 (rain occlusion spike):** build (e289330); round 1 captures (6d6dc1d) showed distance-field collision works, but splashes slid off the sloped roofs, and the hollow tower roof sealed the belfry. Round 2 (build 6db0702, captures and verdict 8c80abf): splashes pinned at first contact, 0 rain and 0 splash pixels under the chapel, cloister walk and tower stair. **Approach A passes (D-106).** The owner set "Two-Sided Distance Field Generation" on `SM_LB_Tw_Roof_BrokenSW` by hand (MCP cannot reach it; 5a2bfe9, 6406eac). The spike assets were deleted. R-65 and R-66 closed.
- **P15-1 (code):** `OnLightningStrike`, `StrikeTargetTag`, `ULBStormFXSubsystem`, `ULBStormFXSettings`, `ALBLightningBolt`, `LBStormFXLogic`, console commands and 13 tests (f13b09f). The suite found that `SpawnSystemAtLocation` returns null under `-nullrhi`, so the rain component is created directly (53a6b67). A Game-target compile error that predates Phase 15 (`AI/LBWardenAnimInstance.cpp`, editor-only `GetBlendSpaceData`, P13) was flagged to the owner as a separate task.
- **P15-2 and P15-3:** 7 procedural FX textures and the CC0 Hessian 230 fabric (9c41155); 4 cloth meshes and 2 cards from Blender, 6/6 checks (3a7b300); 17 assets imported under `/Game/LastBell/FX/` (2be75aa).
- **P15-4 (materials):** 9 masters, `MF_LB_ClothWave` and 13 MIs, all compile clean (56d9ce0). The rain, splash, ripple and curtain masters were made Additive so they only add light (9c89dd7).
- **P15-5 (Niagara):** 7 systems, each UpToDate with 0 errors, 467 checks PASS (5d58555). The splash collision radius is 6. MCP has no event-handler tool, so the drips use a one-particle latch.
- **P15-6 (data and level):** `DA_StormFX`, the `DA_StormSettings` link and both target strikes, then the level work: census 3015 → 3065, `--check` 118 PASS (f3fe33b). The player's flame uses a world scale of 1, not a uniform relative scale (lead decision). Suite 141/141 with the editor closed (5429d86).
- **P15-7 (look session, owner in Play):** rain at rest was invisible, bolts sat behind the walls, rain curtains read as pillars, the player's flame vibrated and the drips were faint. Owner choices: rain 50000 /s, rest brightness raised, bolts at 30000 / 30000 with Ambient chance 0.9, torches smaller, curtains and 6 cloth pieces dropped; new work: rain columns, bigger drips, a fixed flame seed (75ab13c).
- **P15-8 (apply):** every P15-7 value saved; `M_LB_Flame` with `UseFixedSeed`/`FixedSeed` and `MI_Flame_Candle_Player` (4.55 cm); drips edited in place; `NS_LB_RainColumn` and 3 columns; 8 curtains and 6 cloth pieces deleted; census 3054; `--check` 157 PASS, and 126 PASS after an editor restart; 14 packages saved one by one (spec 2cf098d, apply bbd7a04, results 0f4d2f8). Suite 141/141.
- **P15-9 (viewpoints, occlusion, run-through):** captures in PIE Simulate with the owner (c9c9384). **Simulate fix:** the camera rain stayed at the player start because Simulate keeps a pawnless, parked `PlayerController_0`; `GetViewLocation` now uses the rendered view in that case (694bac1; suite 141/141 after). **Live Coding crash:** a first Live Coding patch of `LBStormFXSubsystem.cpp` crashed the editor at PIE start (the patched copy of the static CVar was not registered); nothing was lost; never Live Code that file (MCP_NOTES). Occlusion difference test ≤ 1/255 in all four roofed rects (0.09…0.87). The `NS_LB_Rain` compile-state timeout is a tool artefact: it renders in Play and Simulate. Owner run-through "all good"; **P15-9 approved.**
- **P15-10 (performance):** GPU passes at all six spots (13.81–15.67 ms, added +0.09…+1.39 ms within budget). The game-thread rule could not be resolved with `stat unit` (repeats vary by up to 2 ms); **D-107:** accepted on the GPU result, with the storm FX game-thread trace added to R-64 for the Phase 18 Insights pass (8f2ce99, e1f96f5, 4537498). R-67 mitigated; R-69 (moving-camera distance field cost) stays open for Phase 20.
- **Suite:** 141/141 with the editor closed (128 from Phase 14 plus 13 new), 0 invalid tags, 0 `Error:` lines.

**Status 2026-11-09:** Phase 15 is complete on `claude/phase-15-particles`: P15-0, F0, S1 and P15-1 to P15-11 are done (final suite 141/141, Game target builds, QA no P0/P1). Approved and merged to `main` by the owner on 2026-11-09 (5927cd7).

## Phase 16 — Audio: task breakdown

Branch `claude/phase-16-audio`. Spec and plan: `Docs/plans/P16_AUDIO.md` (D-108…D-113). The owner approved the plan on 2026-11-09:
- sounds generated by our own scripts, plus Kenney and Freesound CC0 recordings (the owner downloads the Freesound list);
- drones, tension and chase music;
- a deep, cracked, distant great bell, with occasional distant tolls between the story beats;
- player breathing that also reacts to darkness and to the candle going out;
- built-in 3D audio with reverb per area (HRTF in Phase 20).

| Task | Scope | Owner | Depends on |
|---|---|---|---|
| P16-0 | Plan approval; D-108…D-111, R-70…R-76; naming; `AUDIO_DESIGN` drift notes | lead + owner | — |
| F0 | Read-only survey: interactables, small bells, areas, floors (footstep hits), bell location, Warden, audio config, MCP audio capability | Sonnet agent [EDITOR read-only] | P16-0 |
| S1 | Spike: WAV import and audio asset creation over MCP, AudioVolume reverb check (owner 5 min) | audio-designer [EDITOR] + owner | F0 |
| A1 | Kenney CC0 packs; Freesound CC0 list; owner downloads; registry rows | asset-curator + owner | P16-0 |
| A2 | Generated sounds (`Tools/audio/gen/`), spectrogram sheets | audio-designer | P16-0 |
| A3 | Recorded sound preparation (`Tools/audio/prep/`) | audio-designer | A1 |
| A4 | Owner audition of the WAVs on headphones | lead + owner | A2, A3 |
| P16-1 | C++: `ULBAudioSettings`, `ULBAudioSubsystem`, `ALBAudioZone`, `ALBAmbientEmitter`, `ULBWardenAudioComponent`, apparition event, footstep variants, surfaces, user volumes, console, config, tests | gameplay-programmer | P16-0 |
| P16-2 | Imports, mix assets (classes, mix, attenuation, concurrency, reverb), physical materials, `DA_Audio`, `DT_Footsteps` rows | audio-designer [EDITOR] | S1, A4, P16-1 |
| P16-3 | Level: audio zones, AudioVolumes, ambient emitters, floor surfaces; one map save | audio-designer [EDITOR] | P16-2 |
| P16-4 | Listening session on headphones | lead + owner | P16-3 |
| P16-5 | Apply the choices | audio-designer [EDITOR] | P16-4 |
| P16-6 | Run-through and performance | owner + performance-engineer | P16-5 |
| P16-7 | QA, docs, full suite, Game build; PHASE 16 READY FOR YOUR REVIEW | qa-reviewer, docs agent, lead | all |

**Outcome** (results in `Docs/plans/P16_AUDIO.md`, "Results"; commits from `git log --oneline main..HEAD`; D-108…D-113, R-70…R-76):
- **P16-0:** plan for approval (1f6482a); approved with occasional distant tolls and darkness/candle-out breathing; D-108…D-111, R-70…R-76, this table, the naming line (c753ebc).
- **F0 (and S1):** read-only survey of `L_Monastery` (fb5b47e); data in `Docs/ArtTest/audio/p16_f0.json` and `p16_f0_tables.md`; nothing set or saved. 29 interactables in 12 unmapped classes; 168 floor hits, 81 % on greybox collision (so per-actor `PhysMaterialOverride`); no MCP tool can import a WAV or create a SoundClass, mix, attenuation, concurrency, reverb or physical material. **Verdict: all audio assets are made by headless Unreal Python with the editor closed, which replaces the S1 spike** (S1 was not run). Lead decisions: small-bell sounds only for the bell puzzle; belfry box from z 2400 with priority 4 (e1ad68b). R-70 closed.
- **A1 (sourcing):** Kenney "Impact Sounds" and "RPG Audio" downloaded, CC0 (c371daf); 127 Freesound CC0 candidates, a 58-file minimum set downloaded by the owner (caaeeff). R-72 mitigated.
- **A2 (generated sounds):** 51 WAVs (rain, wind, thunder, bells, music, rooms, drips), 145 objective checks, byte-identical rebuilds (90dc110); `Sting_Spotted` made an immediate hit, small-bell hum 0.6 → 0.2 (7be3279).
- **A3 (recorded sounds):** 124 WAVs from 56 Freesound and 36 Kenney sources, recipes, checks, registry rows (e4820fc).
- **A4 (owner audition):** local audition page (af9431a); the owner judged all 175 sounds keep (af6013c).
- **P16-1 (code):** `ULBAudioSubsystem`, `ULBAudioSettings`, `ALBAudioZone`, `ALBAmbientEmitter`, `ULBWardenAudioComponent`, apparition event, footstep variants and gait volumes, surface types, user volumes, console, config and `LastBell.Audio.*` tests (df45a81).
- **P16-2 (assets):** the small-bell gating and `CandlePuzzleNotBells` (ceb5fae); a unity-build name clash fixed (fcf6041); 175 SoundWaves imported headless, 25 mix assets, 6 `PM_LB_*`, `DA_Audio`, `DT_Footsteps` (7 rows × 6 variants), fresh verify 1390 checks, 0 failures (2b782d7). Suite 170/171, the failure being the zone count (75030b8).
- **P16-3 (level):** 7 zones, 7 AudioVolumes, 18 emitters, floor overrides on 207 actors, 3 water pads; census 3054 → 3089, `--check` 97 PASS, one map save (6b39939). Suite 171/171 (0850688).
- **P16-4 (listening session, owner on headphones):** outdoor rain 0.8 → 0.22, wind 0.08 / 0.2, roof rain 0.03, exposure power 1.5, master 0.7, steps 0.6, bell stages 1–4 and far thunder at 1.0, Warden roar 2.0; the synthetic cracks were rejected (b644d97, 2ade8f4, 1dcf4be). Candle-flame bug found.
- **P16-5:** the owner's level values (chapel tone 0.4, crypt chains 8–18 s) (90f0dda); the candle flame hides on snuff (7851031); the five recorded cracks replace the synthetic ones (c9a7d97, 6d4ade3); `OWNER_CHOICES` in the asset script, headless re-import, fresh verify 1565 checks, 0 failures (b850aac). Suite 172/172 (7b78386). R-71 mitigated.
- **P16-6 (play-through, owner in Play):**
  - Fixes: wooden steps 0.6 → 2.0; the paper rustle on pick-up and put-down, with re-sliced paper files; the finale bell's first strike at once and kept sounding under the ending pause (917b0c6, 8d40b06, 83733ed, a2b1bbe). The owner set the finale spacing to 2.0 s and stage 5 to volume 2.0 (5ad0ab0).
  - **D-112, creature ambience:** 18 recorded cues from 12 Freesound CC0 sources (ad4be97), imported headless (279b472), 13 emitters (4 bats, 3 owls, 2 howls, 4 rats); census 3089 → 3102, `--check` 107 PASS, map saved (ab59951). Owner: owls 0.4, howls on `ATT_LB_Thunder` at 0.5, belfry howl 0.25 and tone 0.4 (5d2fa55). R-72 mitigated.
  - **D-113:** the owner skipped the audio performance readings; the cost moves to the Phase 20 performance pass and R-75 stays open (5e802a1).
  - Records: d440a3b, 79fdcaf, badfddf.
- **Suite:** 175/175 with the editor closed (141 from Phase 15 plus 34 new: 9 unit, 24 audio functional including `Monastery.AudioSetup`, and the candle flame test), 0 invalid tags, 0 `Error:` lines.

**Status 2026-11-10:** Phase 16 is complete on `claude/phase-16-audio`: P16-0, F0, A1–A4 and P16-1 to P16-7 are done. Owner listening session, play-through and creature check; QA has no P0/P1 findings; final suite 175/175; the Game target builds. The performance readings were waived by the owner (D-113; Phase 20). The owner approved it, and it was merged to `main` on 2026-11-10 (88e164e).

## Phase 17 — Cinematics: task breakdown

Branch `claude/phase-17-cinematics`. Spec and plan: `Docs/plans/P17_CINEMATICS.md` (D-114…D-118, R-78…R-84). The owner approved the plan on 2026-11-10:
- finale "trapped in the belfry", look-only after the ring; the Warden climbs while the bell tolls and swings by itself;
- ending "you become the Warden": a shown mask lift, darkness under the hood, the last view through the mask from the courtyard wall top as a lantern comes through the gate;
- a short skippable intro on New Game only; the player is a villager from below;
- end cards, then skippable credits, then the menu;
- built with Sequencer (visuals) plus labelled markers carried out by `ULBCinematicSubsystem`.

| Task | Scope | Owner | Depends on |
|---|---|---|---|
| P17-0 | Plan approval; D-114…D-118, R-78…R-84, R-77 update; this table; `GAME_DESIGN` ending resolved | lead + owner | — |
| F0 | Read-only survey: spawn and eye, gatehouse passage, wall top, bell and swing axis, tower top, sight lines for the mark and glimpses, Warden slots and bones, note texts, MCP toolsets | environment-designer [EDITOR read-only] | P17-0 |
| F0b | Blender read-only: mask faces, weights, bounds; mask on/off renders | technical-artist | P17-0 |
| A1 | Mixamo mask-lift candidates (owner downloads) | owner | P17-0 |
| S1a | Sequencer authoring spike, headless | animation-specialist | F0 |
| P17-1 | C++: cinematic subsystem, settings, logic, widget, input lock, HUD hide, checkpoint rule, stage 6 dormant, bell strike delegate and Arrival beat, CVars and commands, tests; the Arrival tag | gameplay-programmer | P17-0 |
| P17-2 | `DA_Audio` (Arrival row, no new-game toll), `DA_Cinematics`, `SMX_LB_CineFade`, credits, config | gameplay-programmer + audio-designer | P17-1, F0 |
| P17-3 | `SM_LB_WardenMask`, hood void (if needed), `AN_Warden_MaskLift` (Mixamo or Blender-keyed), imports | technical-artist + animation-specialist | F0b, A1, S1a |
| P17-4 | `M_LB_PP_MaskView` and its MI | technical-artist | F0 |
| P17-5a | `LS_LB_Intro`, `LS_LB_Finale` by script; `--check` | animation-specialist | S1a, P17-2, P17-3, P17-4 |
| S1b | Spike playback in PIE (owner 5 min) | lead + owner | P17-1 |
| P17-5b | Level: finale mark, stair top, the bell, headstock and rope tags; headstock and rope set Movable; the `Note_Gatehouse` text; `EndingTrigger` removed; one map save; suite | environment-designer [EDITOR] | P17-5a, S1b |
| P17-6 | Owner intro review | lead + owner | P17-5b |
| P17-7 | Owner finale review | lead + owner | P17-6 |
| P17-8 | QA and owner play-through | qa-reviewer + owner | P17-7 |
| P17-9 | Docs, final suite, Game build; PHASE 17 READY FOR YOUR REVIEW | lead + docs agent | all |

**Outcome** (results in `Docs/plans/P17_CINEMATICS.md`, "Results" and the revisions 3.2b and 3.4–3.9; commits from `git log --oneline main..HEAD`; D-114…D-125, R-78…R-87; the architecture is in `TECHNICAL_DESIGN.md` section 17):
- **F0 (2026-11-10):** done (6596144) and reviewed. The values are in the plan; the lead's changes:
  - a crane-down intro camera;
  - sound-only glimpses, since no lower flight is in sight from the mark;
  - climb timing kept to an arrival at about 64.1 s;
  - a longer lantern path;
  - the headstock and rope swing with the bell.
  
  The owner accepted both story changes (2026-11-10): the new Intro_1 text, and the `Note_Gatehouse` rope line, changed by P17-5b.
- **S1a (2026-11-10):** done (5ac14db). Everything scripts headless except the camera cut track's `bCanBlend`; a C++ authoring helper in P17-1 sets it, and S1a is re-run after the build.
- **P17-1 (2026-11-10):** built (e24a3ef…5f981b8). After an independent review and its fix set (cfec379), the suite gives 193 passed and 5 failed; the failures are the content tests expected until P17-5b. `RouteBot.Monastery` passes.
- **P17-4 (2026-11-10):** `M_LB_PP_MaskView` and its MI built (a9e8055); the look is reviewed in P17-7.
- **P17-2 (2026-11-10):** `DA_Cinematics`, `SMX_LB_CineFade` and `DA_Audio` (Arrival beat, no new-game toll) done (ee0fb76). A1 found no Mixamo fit, so the mask lift will be Blender-keyed after the new Warden asset.
- **P17-5a-1 (2026-11-11):** both sequences built (2eab748; the finale without the mask moment), and cinematics are live. The suite gives 196 passed and 3 failed; the failures are expected until P17-5b. 
- **P17-5b (2026-11-11):** level edits done (fe631f8, check 49/49). The suite gives **199 passed, 0 failed**. Next is the P17-6 intro review.
- **A1 (2026-11-10):** the owner found no Mixamo clip with the hands at the face (b01f129), so `AN_Warden_MaskLift` is Blender-keyed and committed; R-79, R-80 closed.
- **S1b (2026-11-10, b3400b4):** the owner's PIE check passed the blends, the markers, the slot animation, the attach and the skip, and failed the skip's fade-up (the engine's fade restore cancelled it); fixed in P17-1 (6826cec: hold black, destroy the sequence, fade up on the next tick) and tested (`SkipFadesUp`, `SkipClearsFade`). R-78 closed.
- **P17-6 (2026-11-11, e1a3943):** the owner's intro review passed with no changes; a skip at 5.02 s fired the two must markers. The finale preview before the mask moment passed too (2ef742f).
- **Finale revision 3.2b and the music (2026-11-11, D-120):** the Warden in sight about 3.5 s after the ring, a 97.5 s finale, no intro or outro drones (e37e01c, 9ad5211; check 214/214, suite 199/199); the owner's three cinematic music tracks, `SCL_LB_CineMusic` (3934c8a; check 232/232, suite 199/199).
- **Warden V11.1 swap, W0–W5 (2026-11-11, D-121):** the survey (7097824); the robe reweight, with the stretch gate passed at 16.2 / 17.6 / 30.7 / 33.1 (d9fc23e); exports (43e30e1); in-place reimport with 8 slots, check 26/26 (619aae0); the apparition re-baked, 7,363 triangles (8be7b99); checks and suite 199/199 (b6088cc).
- **P17-3 and 5a-2 (2026-11-11, D-122, D-123):**
  - **Blender (5f02d8c):** `SM_LB_WardenMask` (9 islands, head-local pivot) and the hand-keyed `AN_Warden_MaskLift` (grip 2.2 s, lifted 3.4 s, extended 4.6 s, reach 100 cm, `StopDistance` 80); the contact sheet was accepted.
  - **Villager (b533bd4, 48e2503):** the CC0 Quaternius `Male_Ranger` with the UAL walk and idle, textures ×0.45.
  - **Assets, headless (5d0bcbd, cd63def):** `M_Warden_BellMetal` with `Fade` (Masked), the mask with its measured import rotation (roll 90, yaw −90), the clip, the villager, the intro music re-cut; verify 82/82.
  - **Sequences rebuilt (53041b0):** the mask moment, the push-in, the 70 mm wall top; check 339/339.
- **P17-7 and the candle (2026-11-11, 52cc6b2, 9a5ea29, 11f8330; D-123 to D-125):** the owner's finale review passed ("rest is fine"); the bell swing is kept at every great-bell strike. The villager carries the player's candle instead of a lantern: a Blender contact sheet and the hybrid `Walk_Candle` clip (9a5ea29), then `LS_LB_Finale` rebuilt with the candle parts; check 366/366 (11f8330).
- **P17-9 (docs):** `TECHNICAL_DESIGN` section 17, `GAME_DESIGN` (beat 0, the finale, the ending), `AI_DESIGN`, `AUDIO_DESIGN`, `GREYBOX_SPEC` rows 17 and 18, `MCP_NOTES` (Sequencer scripting, P17-4 MCP, W3 Interchange, the mask import rotation), `PERFORMANCE_BUDGET`, `RISKS` (R-78, R-79, R-80 and R-83 closed; R-81, R-82, R-84 updated; R-85 to R-87 added), `DECISIONS` D-120 to D-125.

**Summary.** New Game plays a 29 s skippable intro (four text cards, a crane-down camera, lightning, the Arrival tolls, a piano). Ringing the great bell plays a 97.5 s finale: the player is locked to look-only, the bell swings, the scripted Warden climbs into sight within about 3.5 s, lifts its mask, and the picture goes black. The last view is through the mask from the courtyard wall top at 70 mm as a villager comes in with the player's candle. End cards, 40 s of skippable credits, then the menu with the save deleted. The cinematics are Level Sequences (`LS_LB_Intro`, `LS_LB_Finale`) with labelled markers carried out by `ULBCinematicSubsystem`; the sequences are built headless by `Tools/cine/p17_sequences.py`. The Warden is now V11.1. Phase 17 adds 24 tests to the earlier 175 (suite 199/199 at the last recorded full run).

**Open, for the owner and the final gates:**
- **Not validated yet:** the final full suite with Unreal closed (the last recorded run, 199/199, is from b6088cc, before the mask moment, the villager and the candle were built), the Game target build, the P17-8 QA pass and the owner's play-through.
- **Needs the owner's eyes:** the mask-view look, the villager's colour (R-86) and the credits list.
- **Carried to later phases:** the GPU cost of the cinematic shots (Phase 20, `PERFORMANCE_BUDGET`), the skip prompt's key glyphs and the restyled cards and credits (Phase 18), R-77 part 2 (the pause menu and the bell, Phase 18).
- **Deleted in P17-9 (owner-approved):** `BP_EndingTrigger`, `WBP_Ending`, the old V5.5 `M_Warden_*`/`MI_Warden_*` materials and `T_Warden_*` textures (33 assets), `WSpawn_Tower` (census 3103 → 3102), `Tools/warden/check_warden.py` (R-87) and the local spike `LS_P17_Spike`.

**Status 2026-11-11: PHASE 17 READY FOR YOUR REVIEW**, pending the final suite and the Game build. Work stops here until the owner reviews and approves; Phase 18 is not started.

- **Final verification (2026-11-11, after the QA fixes):** the suite gives **201 passed, 0 failed**, with 0 invalid tags (including `CheckpointSavesAfterCinematic` and `FinaleCreditsRunOut`). The Game target (`TheLastBell Win64 Development`) builds. **PHASE 17 READY FOR YOUR REVIEW.**

## Deferred to Phase 14–15 (Lighting, VFX: storm work)
Items the owner asked to fold into the storm pass. **Foliage wind is now in Phase 14** (P14 section 6, D-096: `MPC_LB_Storm` replaces the planned `MPC_LB_Wind`).

| Item | Scope | Notes |
|---|---|---|
| Foliage wind (owner, 2026-10-25, D-060) | One wind control `MPC_LB_Wind` (direction, strength, gust speed) driven by the storm; a sway material function in `M_LB_Foliage` (grass/shrubs/ferns bend by height above the pivot, roots fixed) and `M_LB_FoliageMasked` (ivy leaf flutter, wall side fixed); per-family strength in the MIs; WPO evaluation and a WPO disable distance (≈ 3000–5000 cm) on the 312 PCG ISM components (script); optional twig sway for `SM_LB_Prop_DeadTree_A` via its own bark material (never add WPO to `M_LB_Surface`) | Estimated one technical-artist task (~half a day of agent time) plus the owner's PIE check. Risk: GPU +0.3–1.5 ms, mainly VSM invalidation from shadow-casting grass (mitigate with the disable distance or the shadow-cache invalidation setting); masked ivy WPO is costlier. Owner re-runs `stat gpu` (P7-FIX3 baseline 13.1 ms at High, budget 16.6). Stills can't show motion: needs a PIE review |

## Phase 18 — UI and settings: task breakdown

Branch `claude/phase-18-ui`. Spec and plan: `Docs/plans/P18_UI_SETTINGS.md` (D-126…D-128, R-91…R-95). The owner approved the plan on 2026-11-11. R-64 (the game-thread trace) moved to Phase 20.

| Task | Scope | Owner | Depends on |
|---|---|---|---|
| P18-0 | Plan approval; decisions, risks, this table | lead + owner | — |
| A1 | Fonts (EB Garamond, OFL), Kenney input prompts and UI audio (CC0); registry | asset-curator | P18-0 |
| S1 | Menu-video spike (MRQ render, MP4, media playback) | animation-specialist | P18-0 |
| P18-1 | C++ UI framework, screens, settings backend, pause, rebinding; tests | gameplay-programmer | P18-0 |
| P18-2 | Assets and hookup (`DA_UIStyle`, fonts, icons, sounds, `IA_Pause`, IMC, menu game mode, video) | technical-artist + ui-engineer | A1, S1, P18-1 |
| P18-3 | HUD and cinematic restyle, key icons | ui-engineer | P18-1, P18-2 |
| P18-4 | Owner session (about 20 min) | lead + owner | P18-3 |
| P18-5 | Fixes; QA (Opus) | gameplay-programmer, qa-reviewer | P18-4 |
| P18-6 | Docs, final suite, Game build, PHASE 18 READY FOR YOUR REVIEW | lead + docs agent | P18-5 |

