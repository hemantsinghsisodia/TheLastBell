# Phase 13 (Warden animation): independent QA report (P13-9)

Reviewer: qa-reviewer (Sonnet 5.5). Branch `claude/phase-13-warden-animation`, head `5316c15`. Unreal was closed; no MCP; read-only except this file.
Date of the run: 2026-11-07 (log timestamps are UTC, 18:50 to 19:05).

## 1. Verdict: PASS WITH CAVEATS

- The build succeeds and the Mixamo licence cleanup (D-094) is verified from git and the filesystem.
- The full suite on the final tree ran 112 tests: **111 passed, 1 failed**. The failure is `LastBell.Functional.Warden.Apparition.StateReplacedMidRunStops`. It is a **timing race in a P12-era test assertion, not a Phase 13 product defect**: it passed in 3 of 3 isolated re-runs, and it passed in the pre-wrap-up 112/112 run (P2, section C, finding C1).
- No P0 or P1 defect was found. Several exit conditions rest only on the owner statement because no automated test covers them (section D).
- Stale statements in the docs are listed in section E (P3).

## A. Full test suite on the final tree

Command: `powershell -ExecutionPolicy Bypass -File Tools\build_and_test.ps1` (started by me, run once to completion; the script returned by itself, no stray `UnrealEditor-Cmd` process left).

| Item | Result |
|---|---|
| Build (TheLastBellEditor Win64 Development) | `build exit=0`, `Result: Succeeded` (17.5 s: the binaries were already up to date with the tree) |
| `Result={Success}` lines | **111** |
| `Result={Fail...}` lines | **1** (112 `Test Completed` lines in total) |
| "Invalid GameplayTag" lines | **0** |
| "very large delta" lines | **1**: `Ignoring very large delta of 3.79 seconds in calls to FAutomationControllerManager::Tick()`, during `MenuToGameInput` (a level load, log line 2758; harmless) |
| `: Error:` lines | 2, both from the one failure below |
| Ensure lines | 0 |
| `LogLBWarden: Error` lines | 0 |
| `: Warning:` lines | 206, of which 200 are one message (100 raw plus 100 echoed by `LogAutomationController`): `LogCrowdFollowing: Unable to find RecastNavMesh instance while trying to create UCrowdManager instance` (test maps without a navmesh). Other distinct warnings: the `LogModelContextProtocol` licence notice, a `LogLayoutService` layout key, `LogLB: Dial on StaticMeshActor_N had several positions set (corrupt state)` and `LogLB: Cannot inspect StaticMeshActor_N: its root component is not Movable` (the last two come from tests that build deliberately bad setups) |

The failing test (log `Saved\Logs\LBTests_All.log` lines 5716 to 5740):

```
LogLB: Display: [Apparition] STEP 3 FAIL: Tag added, looking at the station: reaches Hold
LogAutomationController: Error: Test Completed. Result={Fail} Name={StateReplacedMidRunStops} Path={LastBell.Functional.Warden.Apparition.StateReplacedMidRunStops}
LogAutomationController: Error: Expected "In Hold" to be true. [...\Source\LastBellTests\Tests\LBApparitionTests.cpp(1244)]
```

Re-runs of that test alone (`UnrealEditor-Cmd ... -ExecCmds="Automation RunTests LastBell.Functional.Warden.Apparition.StateReplacedMidRunStops; Quit"`): runs 1, 2 and 3 all `Result={Success}`.

Other results of interest in the run: `LocomotionMovesTheFeet`, `CatchKillsAfterWindupAndReloads`, `CatchTurnsTheViewToTheMaskBeforeTheReload`, `ZoneQueryUsesRotatedBoxesAndTheHighestAmount`, `FigureAnimatesOnlyWhenRendered`, `WalkPathThenFade`, `WalkCutShortByPlayer`, `SkeletalFigureReplacesBody`, `Monastery.StagesRelocateTheWarden` and all `LastBell.Warden.Anim.*` unit tests passed.

## B. Mixamo licence cleanup (D-094): all verified

1. `git rev-list main..HEAD` has **39 commits**. For each, `git ls-tree -r --name-only` contains **0 paths** under `Content/LastBell/Characters/Warden/Retarget/` or `SourceArt/Warden/P13_review/`. A wider check (`*.fbx`, `mixamo`, `YBot`, `MX_` in every tree) finds only pre-existing, unrelated names (`SourceArt/BellTower/*.fbx`, `Docs/ArtTest/crypt/p9d_dec_wallMX_soot_T2.png`) and `Tools/warden/p13_reimport_ybot.py`.
2. `git check-ignore -v`: both folders are ignored by `.gitignore:26` and `.gitignore:27` (the folder form and a file inside each).
3. `Config/DefaultGame.ini` line 19: `+DirectoriesToNeverCook=(Path="/Game/LastBell/Characters/Warden/Retarget")`, under `[/Script/UnrealEd.ProjectPackagingSettings]` (line 16).
4. `git lfs ls-files` lists nothing under either folder (0 matches).
5. On disk: **18** `.uasset` in `Retarget/`, **12** `.fbx` in `SourceArt/Warden/P13_review/`.
6. `Content/LastBell/Characters/Warden/ABP_P13_Spike.uasset` is gone from disk, and 0 matches in `git ls-tree HEAD`.
7. `grep` of `Source/` and `Config/` for `SK_LB_YBot|AN_YBot_|IK_LB_|RTG_LB_|Retarget/`: **0 hits** (the `DirectoriesToNeverCook` line has no `Retarget/` with a trailing slash). I also grepped all `.uasset` and `.umap` outside `Retarget/` for `Warden/Retarget`, `SK_LB_YBot` and `AN_YBot_`: 0 files (the shipped clips, blend spaces, `ABP_Warden`, `DA_WardenAnimSet`, `SK_Warden` and the map do not reference the folder).

Observations (P3, not defects):
- B-1. `refs/original/refs/heads/claude/phase-13-warden-animation` (the pre-rewrite head, local) still holds **30 Mixamo-path files** in its tree, and the reflog keeps the old commits. `origin` has only `main`, so nothing is exposed today. Push only named branches (never `--all` or `--mirror`), and delete `refs/original`, expire the reflog and gc once the owner no longer needs the rollback, as D-094 already implies (until the merge).
- B-2. The 12 retargeted `AN_Warden_*` uassets are Mixamo-derived and sit in the public repo. D-094 and R-55 record this as accepted by the owner. It is a legal reading of the Adobe terms, not a code defect (R-55 stays Open).
- B-3. `AN_Warden_ZombieWalk`, `AN_Warden_ZombieRunning` and `AN_Warden_MutantSwiping` are committed but unused (the picks are MutantWalking, MutantRun and ZombieAttack). They are not cooked unless referenced, but they add public Mixamo-derived content for nothing.

## C. Code review of `git diff main..HEAD -- Source/`

Files read in full: `LBWardenAnimInstance.h/.cpp`, `LBWardenAnim.h/.cpp`, `LBWardenAnimSet.h`, `LBWardenStoopZone.*`, `LBWardenStoopSubsystem.*`. Diffs read: `LBWardenApparition.*`, `LBApparitionLogic.*`, `LBWardenBrainComponent.*`, `LBWarden.cpp`, `LBWardenTuningData.h`, `LBCharacter.*`, `LBPlayerTuningData.h`, `LastBell.Build.cs`. Tests read: the Warden anim unit tests, the catch, stoop and locomotion functional tests, and the apparition walk tests.

No P0 or P1 found. Hard asset references: none in `Source/LastBell` (no `ConstructorHelpers`, `LoadObject`, `/Game/` paths; the only `/Game/` strings in the diff are a comment and the test that loads the two blend spaces). Montages sit in `ULBWardenAnimSet` (`TObjectPtr`, assigned in the data asset), which is the data-driven pattern of the project.

Checked and found fine: thread safety of `NativeThreadSafeUpdateAnimation` (it touches only plain members and the variables the graph reads; the world, subsystem and traces are all in `NativeUpdateAnimation`); division by zero and NaN (`DeltaSeconds <= 0` guard, `Delta / Distance` only when `Distance > Budget > 0`, `CatchLookSeconds` floored, interpolation speeds clamped at 0.1 in the data asset); null checks on the owner, mesh, camera, subsystem and capsule.

**Kill / catch soft-lock analysis** (`LBCharacter.cpp:312-404`, `LBGameMode.cpp:40-58`, `LBSaveSubsystem.cpp:236-266`): no soft-lock or skipped reload found.
- No controller: `TickCatch` ends the stage and calls `FinishDeath`. `Kill(Killer)` without a player controller calls `FinishDeath` at once.
- No `PlayerCameraManager`: the fade is skipped, the reload still comes after `CatchFadeSeconds`.
- Killer destroyed: the `TWeakObjectPtr` keeps the last target.
- Second `Kill`: ignored by `bIsDead`. The brain broadcasts `OnPlayerCaught` only when the player is not already dead.
- `HandlePlayerDeath` ignores its controller argument, so passing `GetController()` (possibly null) is safe. `LoadLastCheckpoint` and `NewGame` both call `OpenLevel`, so the held black fade is discarded with the level.
- A checkpoint cannot save in the 1.55 s window (`ALBCheckpoint::TrySave` returns when `Character->IsDead()`).
- Residual (unchanged by this phase): with no save subsystem, `HandlePlayerDeath` only logs an error. The player would now be left on the held black screen (before P13, standing). Low, unreachable in a normal build.

### Findings

| # | File:line | Severity | Finding | Sure? |
|---|---|---|---|---|
| C1 | `Source/LastBellTests/Tests/LBApparitionTests.cpp:1243-1244` (test `StateReplacedMidRunStops`, step 3; the same assertion is in `main`) | **P2 (test flake, medium)** | The step passes when `A->GetAlpha() >= 0.999f` and then asserts the phase is `Hold`. `LBApparitionLogic::Step` computes the fade-in alpha with `SmoothStep` (`LBApparitionLogic.cpp:5-9`, `:106`), which already reads 0.999 at about 99 % of the 0.2 s fade, while the phase only becomes `Hold` when `PhaseTime >= FadeInSeconds`. A frame that lands in the last 1 to 2 ms of the fade (roughly 1 frame in 8 at 60 fps) sees alpha >= 0.999 and phase `FadeIn`. It failed once in the full run above, and passed 3 of 3 alone. Repro: run `Tools\build_and_test.ps1` repeatedly, or the single test in a loop; the failure shows as `Expected In Hold to be true` at line 1244. Fix idea (not applied): wait for `GetPhase() == Hold` (or `GetAlpha() >= 1.f`) instead of `>= 0.999f`, in this test and any copy of the pattern. | Sure of the mechanism (read from the code); the failure rate is an estimate |
| C2 | `LBWardenAnim.cpp:97-99, :114-120`; `LBWardenAnimTests.cpp:252-281, :305-316`; `Docs/TECHNICAL_DESIGN.md` Warden animation | P3 (medium) | `LBWardenAnim::FootTarget` and `LBWardenAnim::AttackPlayRate` are never called from production code (grep: only the definitions and the tests). `FootTargetKeepsTheSwing` is partly about `FootTarget`, but the real path is `FootCorrection` plus `UnrotateVector` in `UpdateFootTargets` (`LBWardenAnimInstance.cpp:386-390`), whose rotation maths has no test. The attack timing is a stored constant (`AttackPlayRate` 1.7778 and `AttackHitTime` 1.0667 in `DA_WardenAnimSet`), so the lunge stays correct only while `AttackWindupSeconds` is 0.6 s. Changing it in `DA_WardenTuning` silently desyncs the reach, although TECHNICAL_DESIGN says the attack montage is scaled so its hit lands at the end of `AttackWindupSeconds`. | Sure |
| C3 | `LBWardenAnimInstance.cpp` (whole class), tests | P3 (medium) | No automated test exercises the behaviour of the anim instance: stoop easing against a zone (no test checks that the real `StoopAlpha` reaches 1 inside a zone), foot IK targets, pelvis offset, turn montage start, look-around, `PlayAttack` and the `HoldCatchPose` freeze, the 12 placed `SZ_*` zones in `L_Monastery`, or the apparition walk on the real chapel actor. Only the pure helpers, the zone query on spawned zones, `LocomotionMovesTheFeet`, the catch view test and the generic apparition walk tests cover Phase 13. The header comment of `LBWardenAnimTests.cpp:9-10` (arrive in later P13 tasks) is stale. | Sure |
| C4 | `LBWardenFunctionalTests.cpp:2050-2170` | P3 | `LocomotionMovesTheFeet` can pass with any non-reference pose (foot moves at least 15 cm, hand at least 5 cm). It cannot see foot sliding, a wrong rate scale or a missing stoop. It also forces the mesh to `AlwaysTickPoseAndRefreshBones`, so the shipped `OnlyTickMontagesWhenNotRendered` setting is not exercised. It does catch the empty-blend-space regression it was written for. | Sure |
| C5 | `LBWardenAnimInstance.cpp:207-248, :455-467` | P3 (low) | **Plausible, not verified (needs the engine source or a PIE check):** with `OnlyTickMontagesWhenNotRendered` I expect an unrendered Warden to tick montages only, i.e. neither `NativeUpdateAnimation` nor the thread-safe easing runs. If so, `StoopAlpha`, `FootIK*` and `GroundSpeed` are stale on the first rendered frame (a Warden that walks out of sight through a door, then comes into view mid-doorway, would ease from the old stoop at 3 per second, a pop of up to 0.33 s), and `UpdateCatchHold` and `UpdateTurn` do not run while unrendered. For the catch itself it does not matter, because the view is on the mask. | Plausible |
| C6 | `LBWardenAnimInstance.cpp:414-431` | P3 (low) | **Plausible:** the actor turns at `RotationRate` 120 / `TurnRate` 90 deg/s while the turn montages also rotate the mesh, and `TurnTriggerDegrees` 45 is within what a search look-around turns through, so a turn montage may play on top of an actor turn and double the visible rotation. The owner playtest said all good, so this is cosmetic if it happens. | Plausible |
| C7 | `LBWarden.cpp:28` | P3 (low) | `RotationRate` 120 is set in the C++ constructor and tested on the class default only. If `BP_Warden` saved an explicit value (it was 360 before), the Blueprint wins and nothing tests it. `check_warden.py` has no check for it (grep found no `RotationRate`). The owner said turning was fine after the change, so it probably took effect. | Plausible |
| C8 | `LBWardenApparition.cpp:263-267, :284` | P3 (cosmetic) | When the walk is cut short (player within `MinPlayerDistance`) the phase becomes `FadeOut` and `AdvanceWalk` stops, so the figure stops where it was (speed 0, blends to idle) while it fades. | Sure |
| C9 | `LBWardenAnimInstance.cpp:250-335`, `LastBell.Build.cs` | P3 (low) | The debug dump (`lb.Warden.AnimDebug`) pulls `AnimGraphRuntime` into the game module and is not compiled out of Shipping. It is off by default and reads one cvar per frame; no functional risk. | Sure |

Nothing else found in: `LBWardenStoopSubsystem` (weak pointers, swap-remove, register and unregister match), `ALBWardenStoopZone` (no collision, hidden in game), `ResolveLookTarget` (null killer handled, socket fallback), the brain change (`OnPlayerCaught` fires before `Kill`, once), the apparition `Figure` (constructor sets `OnlyTickPoseWhenRendered`; `Body` and `Figure` visibility set in `BeginPlay`; fade instances created for the active figure only).

### Architecture drift check (`Docs/TECHNICAL_DESIGN.md`)
- Section 8 Warden animation matches the code in: class names, `GroundSpeed` source, stoop query without ceiling traces, easing in the thread-safe update, the three BlueprintCallable calls, `ULBWardenAnimSet` contents, catch-camera stages and tuning, `OnPlayerCaught`.
- Differences: (a) the attack-rate sentence (C2); (b) the section 8 class bullet still says socket `mask` on bone `head` stays for Phase 13, which is now in use (stale, E); (c) the 22 tests functional count is stale (the log has 33 `LastBell.Functional.Warden.*` tests and 33 `LastBell.Warden.*` unit tests).
- The section 10 apparition line matches `LBWardenApparition` (`WalkPath`, `WalkSpeed` 110, `bUseSkeletalFigure`, `Figure` with `OnlyTickPoseWhenRendered`; the chapel walks, the courtyard stays static).
- No architecture break found (composition, a subsystem rather than a manager actor, no hard asset refs).

## D. Exit-condition audit

| # | Exit condition | Evidence and source | Mark |
|---|---|---|---|
| 1 | Walk, run, no visible foot sliding, stalker feel | Test `Warden.Anim.LocomotionMovesTheFeet`: pass (limbs move; 15 cm and 5 cm thresholds, so not a sliding test). Blend space rate scales come from the measured natural speeds (walk 196.5 cm/s gives 0.7125 at 140; run 270.1 gives 1.555 at 420; plan P13-4b). Owner: "legs and arms move now, all good now" and "all good, proceed now" (plan, second look and owner playtest). No slide measurement; 170 and 190 cm/s sit in the blend between samples and nothing measures them | **Owner-verified** (movement verified by test) |
| 2 | Stoops through every door and low stair | Zone query tests (`Warden.Anim.StoopBoxRotated`, `StoopTarget`, `Functional.Warden.Stoop.ZoneQueryUsesRotatedBoxesAndTheHighestAmount`): pass. 12 zones placed (plan P13-7), no test counts them in `L_Monastery`. Head clearance only by arithmetic in the plan (about 256 minus 40 x amount against 224 to 240 openings); the per-zone check of the highest head Z at that zone amount was never recorded. Owner playtest "all good" (doors and stairs were on the checklist) | **Owner-verified** |
| 3 | Attack lunge at the end of the 0.6 s windup; turns on the spot; look-around at search points | Windup timing unchanged and tested (`Attack.CatchKillsAfterWindupAndReloads`: pass). The lunge timing is arithmetic (`AttackHitTime` 1.0667 / `AttackPlayRate` 1.7778 = 0.6 s; plan P13-4b, "provisional until seen in motion"). Owner: "up close, it lunges with its arms" (first look), later "all good". Turn and look-around: no test; the owner reported "turns too fast", which led to the 120/90/45 change; later "all good" | **Owner-verified** |
| 4 | Robe and chains swing, settle, no jitter | No test. P13-8 shows `RigidBody_Eval` 0.39 to 0.50 ms on worker threads (image `p13_8_perf_1.png` read: 0.50 ms, 2 calls), so it runs; quality is the owner playtest only | **Owner-verified** |
| 5 | Feet on stair treads, nothing pops on flat | No test of the foot targets, the pelvis offset or pops on flat floor (C3). Pure helpers are tested (`PelvisAndFeet`, `FootTargetKeepsTheSwing`, `StoopPelvis`). Owner playtest "all good" | **Owner-verified** |
| 6 | Catch camera: view to the mask, hold, fade, reload; the Warden holds its grab pose | Test `Warden.Attack.CatchTurnsTheViewToTheMaskBeforeTheReload`: pass (view within 10 deg of the mask socket at 0.9 s, still in the old world, then the reload). `CatchKillsAfterWindupAndReloads`: pass. The fade and the held pose have no assertion; owner playtest "the attack and the catch camera" on the checklist, "all good" | **Verified** for look, hold and delayed reload; **owner-verified** for the fade and the pose |
| 7 | Chapel: forms at the rail, walks into the sacristy, stoops at the door, fades | Tests `Apparition.WalkPathThenFade`, `WalkCutShortByPlayer`, `SkeletalFigureReplacesBody` and the unit `Warden.Apparition.Walk*`: pass, but on spawned apparitions, not the chapel actor with its real path and zone. Owner playtest "the chapel walk" on the checklist, "all good" | **Owner-verified** (mechanism verified by tests) |
| 8a | Suite passes, new tests for everything in the plan | Run in A: 111 of 112; the one failure is the C1 flake, not a P13 feature. Not everything in the plan has a test (C3) | **Partly verified** |
| 8b | Animation adds at most 1.0 ms of game thread | P13-8 `stat anim`: `AnimGameThreadTime` average 0.20, 0.18, 0.18 ms (image 1 shows a max of 0.87 ms; the limit is 1.0, so the peak is close). Measured as the absolute animation cost, not against the single-clip view (the A/B was dropped and recorded as a method change). Taken before the apparition tick fix `369f3cd`; not re-measured since | **Verified** (owner screenshots) |
| 8c | GPU at most 16.6 ms at High | P13-8: 14.23, 13.61, 14.18 ms (image 1: GPU Time 14.23 ms) | **Verified** (owner screenshots) |
| 9 | The owner approves | The owner said "all good, proceed now" after the playtest (plan, 2026-11-07). That covers the playtest. The phase approval comes after the PHASE 13 READY FOR YOUR REVIEW report (CLAUDE.md) and has not been given | **Owner-verified for the playtest; phase approval pending** |

Not yet seen in game (stated in the plan): whether `stat anim` drops to one evaluation when no Warden is on screen (apparition fix `369f3cd`, tests only).

## E. Docs consistency

Hash check: every commit hash cited in the P13 plan, DECISIONS, RISKS, TECHNICAL_DESIGN, IMPLEMENTATION_PLAN and PERFORMANCE_BUDGET resolves to a commit that is an ancestor of HEAD (no stale pre-rewrite hashes found).

Stale or contradicting statements (all P3):
1. `Docs/ASSET_REGISTRY.md` rows 120 to 131 (the 12 clips), column Modifications: "None yet; will be retargeted to `SK_Warden` (110 bones) in Phase 13 and may be hand-fixed in Blender". They were retargeted (12 `AN_Warden_*`, P13-4 and 4b) and not hand-fixed. The Y Bot row (119) says "None yet" too, although it was re-imported with a facing rotation (P13-4b).
2. Registry Use column for Zombie Walk, Zombie Running and Mutant Swiping still says second choice, compared, one is kept. The plan decided: ZombieWalk dropped, Walk = MutantWalking, Run = MutantRun, Attack = ZombieAttack, so these three are unused but still committed (B-3). The registry also says only retargeted Warden clips ship, while unused clips remain in `Content/`.
3. `Docs/plans/P13_WARDEN_ANIMATION.md` line 3 status banner (P13-5 sheet shows the retarget is wrong; skin weights need fixing; P13-6 can go ahead in parallel) is stale: everything through P13-8 is done and wrapped up.
4. Same plan, sections 3 and 8 still list the old numbers (RotationRate 360, TurnRate 180, `TurnTriggerDegrees` 60); the code and the First look section say 120, 90 and 45. Exit condition 8 and section 12 still describe the A/B against the single clip of Phase 12 and the Insights trace, which P13-8 replaced with `stat anim` (recorded there as a method change).
5. `Docs/TECHNICAL_DESIGN.md` section 8: "Socket `mask` on bone `head` stays for Phase 13" (stale: it is now used by the catch camera and its test); "22 tests" for the functional Warden tests (now 33); the attack-scaling sentence (see C2).
6. `Docs/IMPLEMENTATION_PLAN.md` Phase 13 block: "Real-project suite 112/112 before the wrap-up" is accurate, but the final run (this report) is 111 of 112 with the C1 flake, so the QA and final suite run line needs the result.
7. `Docs/DECISIONS.md` D-094 says all 37 commits were kept; the branch now has 39 (two later docs commits). Not a contradiction, but the number will read wrong later.
8. `Docs/RISKS.md`: R-55 is Open (watch: retargeted clips in a public repo), consistent with D-094. R-56, R-57 and R-58 are Closed and match the plan. R-54 is Closed (P12). No contradiction found.
9. `Docs/PERFORMANCE_BUDGET.md` last row matches the screenshots (image 1 checked: Game 10.67, GPU Time 14.23, `AnimGameThreadTime` 0.20, `RigidBody_Eval` 0.50, RenderRes 87.0 % 1671x853). The plan setup line says `r.SetRes 1920x1080w` while the screenshot reads 1671x853 at 87 %; the budget row uses the screenshot values, so only the setup text of the plan is loose.

## Needs the owner / human testing

- Final in-game look at the items no test covers: foot placement on the real stair treads, head clearance at each `SZ_*` zone (especially the 224 cm tower door and the sacristy stair at 0.7), robe and chain swing and settle, turn montages against the 90 deg/s AI turn (C6), look-around at search points, and the chapel walk with its sacristy stoop on the real map.
- Re-run `stat anim` with the Warden off screen to confirm the hidden chapel `Figure` no longer evaluates (apparition fix `369f3cd`; the plan says it was not re-measured).
- Fix or accept the flaky `StateReplacedMidRunStops` assertion (C1) before relying on a 112/112 gate.
- Decide whether to keep the three unused retargeted clips (B-3) and the local rollback ref `refs/original` (B-1), and give the phase approval after the lead report PHASE 13 READY FOR YOUR REVIEW.
- Confirm that the saved `RotationRate` of `BP_Warden` is 120 (C7) with a one-line PIE read or an MCP property read (Unreal was closed for this review).
