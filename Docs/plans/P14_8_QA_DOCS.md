# P14-8: QA, docs, suite, then "PHASE 14 READY FOR YOUR REVIEW"

Owner approval: "go", 2026-11-08. Branch `claude/phase-14-lighting-storm`.

Two agents run in parallel, Sonnet with high effort; they touch different files:
- **D (docs):** the docs below.
- **Q (QA):** read-only review.

After both, the lead:
- reviews the docs against the code;
- asks the owner to close Unreal, then runs `Tools/build_and_test.ps1` (build plus the full suite, editor closed);
- writes the phase report.

## D. Docs (general-purpose agent)
Sources of truth: the code in `Source/LastBell/Storm/` (headers first) and `Source/LastBell/Systems/LBConsoleCommands.cpp`; the plan `Docs/plans/P14_LIGHTING_STORM.md`, including every "result" subsection at its end; `Docs/plans/P14_4_WIND_FIX.md`; `Docs/plans/P14_5_APPLY.md`. If the plan and the code disagree, the code wins: write what the code does and list the difference in your report.

Every doc here is UTF-8. Keep each file's BOM state and line endings exactly; check them before and after (`MCP_NOTES.md` and `Config/*.ini` are CRLF; check the others). Use the Edit tool for changes. Do not rewrite whole files.

1. **`Docs/TECHNICAL_DESIGN.md`: new section `## 14. Storm and light (Phase 14, D-096…D-102)`**, inserted after section 13 or before it if 13 must stay last (say which). Keep it 120–220 lines, in the same terse style as section 8. Content:
   - **`ULBStormSubsystem`**: world types, activation (an actor tagged `LB_StormMoon`), settings from `ULBGameSettings` / `DefaultGame.ini` → `DA_StormSettings`, what it does per tick and at what rates, `OnLightningFlash` (the Phase 16 audio hook).
   - **`MPC_LB_Storm`**: every parameter name and who writes or reads it.
   - **Linked lights**: the four tags and how each is scaled.
   - **Story intensity**: the steps, scripted strikes, the look gate.
   - **Flash shapes and the preset**: preset B is in use; A and C are kept for reference.
   - **Wind**: the formula and the owner-tuned values (`PhaseSpeedHigh` 6.5, `WindBaseHigh` 0.8, `GustHigh` 0.5, `GustFrequency` 0.2).
   - **`ALBStormZone`** and `GetExposureAt`.
   - **The Warden reveal rule** and `bRevealEnabled`.
   - **`BP_WardenApparition` `bLightningOnHold`**.
   - **`ALBStateLightGroup`**: modes, rules, fade, glow actors (D-099), the section 8 groups.
   - **Materials consuming the storm**:
     - sky (`M_LB_StormSky`);
     - glass `FlashResponse`;
     - shafts and pools;
     - `M_LB_Decal_LightningReveal` + the 5 `RV_*` decals, with final placements;
     - `MF_LB_WindSway`: scale-aware height (D-100), bend and flutter;
     - the foliage masters `bWind`, and the MI amplitudes 38 / 24 / 16 / 24 / 18 / 16 / ivy 5.
   - **Post-process structure**:
     - each volume with its EV: `PostProcess_Exposure` 3 + grade B, `PP_Outdoor_Night` 1.40, `PP_Crypt` 0.2 histogram, `PP_Cloister` 0.65, `PP_Chapel` 1.6, `PP_Tower` 0.65;
     - priorities and blends;
     - no per-area shadow-saturation override.
   - **WPO disable distance**: 4000 on 249 actors + 312 PCG ISMs. **Rerun `Tools/lighting/p14_wpo_distance.py --apply` after any PCG regeneration.**
   - **Console commands**: `lb.Storm.*` and what each does.
   - **The never-save rule**: debug fields at −1.
   - **Tests**: list the Storm automation tests by name from `Source/LastBell/Tests`.
   - **Tools**: `Tools/lighting/` scripts, one line each.
2. **`Docs/DECISIONS.md`**: append, in the table format, after D-100:
   - **D-101**, the owner's P14-4 look choices, 2026-11-08:
     - flash preset B;
     - chapel EV100 1.6 on `PP_Chapel`;
     - grade B (storm teal) on `PostProcess_Exposure`, with the per-area shadow-saturation overrides cleared;
     - tower kept as lit stone on arrival (R-31 accepted);
     - wind tuned live;
     - `RV_WellHouse_Tally` lowered to Z 115;
     - `RV_Chapel_Circle` moved beside the S2 pool to (8150, −91);
     - `RV_Garth_Drag` kept.
   - **D-102**, the P14-5 exposure method (owner, 2026-11-08):
     - mean targets measured on the wide views only, with readability floors on every view;
     - courtyard EV 1.15 → 1.40;
     - tower and crypt kept outside their mean targets (the candle dominates the tower views; the crypt keeps the Phase 9 look);
     - P14-7 closed on Phase 14's own cost: storm game-thread cost +0.16 ms mean; the rise against P14-B is story state.
3. **`Docs/RISKS.md`**: set the Status of these risks, citing the plan results:
   - **R-09:** closed 2026-11-08, nothing blocking in the P14-5b/P14-6 captures; the owner approved the viewpoints.
   - **R-31:** closed 2026-11-08, accepted by the owner (tower 0.122 against sky 0.099).
   - **R-59:** closed 2026-11-08, no smear seen in P14-4; `SkyFlashGain` stays 0.6.
   - **R-60:** closed 2026-11-08, courtyard GPU 13.25 against a limit of 13.72 with the stronger wind.
   - **R-61:** closed 2026-11-08, every floor holds after all story changes (P14-5b).
   - **R-62:** closed 2026-11-08, judged in the owner's P14-6 storm run-through ("storm feels good"); `bRevealEnabled` remains the switch.
   - **R-63:** closed 2026-11-08, the owner chose chapel EV 1.6 in P14-4.
   - **New R-64:**
     - Category: Performance.
     - Risk: the game thread is about 11 ms at every spot at the start story state, against about 8 ms at the late indoor states (P14-7). The cause is outside Phase 14 and not yet determined.
     - Mitigation: Unreal Insights trace at the game start in the Phase 18 optimisation pass. The frame is still capped at 16.67 ms.
     - Status: Open.
4. **`Docs/IMPLEMENTATION_PLAN.md`**, Phase 14 section: add rows for the wind fix (P14-4 wind fix, D-100) and P14-5a/b/c if the table has no such rows. Then add a "Status 2026-11-08" line in the style of the other phases, listing:
   - P14-0…P14-7 done with key commits (`git log --oneline main..HEAD`);
   - the suite at 128 (the lead adds the final suite count later: leave "suite: pending final run");
   - P14-8 in progress.
5. **`Tools/mcp/MCP_NOTES.md`**: a new section `## Lighting sessions (Phase 14)` at the end (CRLF), with these items:
   1. `capture_session.py --light-offset F R U` (the candle proxy; PIE must already be running, with `Tools/lighting/pie_proxy.py` run first).
   2. `Tools/lighting/pie_pp.py` (`start`, `stop`, `read`, `ev [volume] EV`, `grade A|B|C`): it edits only PIE-world copies.
   3. `Tools/lighting/area_targets.py` (wide-view means, floors) and `compare_sets.py` (before/after MAD and sheets).
   4. Live tuning in PIE works:
      - `MaterialInstanceTools.set_scalar_parameter` and `DA_StormSettings` field writes over MCP take effect immediately, with no crash (P14-4);
      - they leave the assets dirty in memory, so either save them deliberately or choose Don't Save on close.
   5. `lb.Warden.Enabled` is a global CVar: it persists across PIE sessions until it is changed.
   6. Owner console commands during Simulate go to the PIE world. A script can wait for a marker such as `Cmd: lb.State.Dump` in `Saved/Logs/TheLastBell.log` before capturing.
   7. Performance readings must be taken at a matched story state. The game thread depends on it (P14-7).
6. **`Docs/PERFORMANCE_BUDGET.md`**: one row for the P14-7 re-read: ossuary on/off 11.41/11.56 game, belfry off/on 11.25/11.79, storm game cost within noise, P14-7 passed (owner). Match the existing row format.
7. Commit by path on the current branch; never switch, merge or push; the trailer is `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Report the files, the section line range, and any code-versus-plan difference you found.

## Q. QA review (qa-reviewer agent, read-only)
Do not change any file or asset. The editor is open on `L_Monastery` with PIE stopped; read-only MCP calls are allowed. Never start PIE, never capture, never save.

1. **Level and asset checks** (read-only scripts, Python `C:\Users\heman\AppData\Local\Python\pythoncore-3.14-64\python.exe -I`). Each must be all PASS:
   - `Tools/lighting/p14_5_apply.py --check`
   - `Tools/lighting/p14_3_level.py --check --map-dirty false`
   - `Tools/lighting/p14_4_wind_fix.py check`
   - `Tools/lighting/p14_wpo_distance.py --check` (cached list).
2. **Code review of `Source/LastBell/Storm/`** and the storm parts of `Systems/LBConsoleCommands.cpp`. Look for:
   - null and weak-pointer safety;
   - GC (UPROPERTY on UObject members);
   - per-frame cost;
   - debug and console paths guarded for shipping;
   - the MPC parameter names matching the asset;
   - the tests in `Source/LastBell/Tests` covering the logic.
   Report findings ranked by severity, with file:line.
3. **Git hygiene for `git log main..HEAD`:**
   - every binary is in LFS (`git lfs ls-files`);
   - no file under `ExternalAssets/` or any licensed asset was committed (D-094, D-095);
   - none of the never-save packages changed in `git diff --stat main..HEAD`: `M_LB_Surface`, `BP_SmallBell`, `BP_SequencePuzzle`, `BP_Inscription`, `BP_RitualMechanism`, `BP_Door_Base`, `BP_TagInteractable`, `BP_TagTrigger`, `BP_EndingTrigger`, `BP_Inspectable_Note`, `BP_Door_Base_Dungeon`, `BP_RitualMechanism_CryptWinch`, `BP_WardenApparition`;
   - every commit has a Co-Authored-By trailer.
4. **Logs:** in `Saved/Logs/TheLastBell.log` (this session) and `Saved/Logs/LBTests_P14_5c.log`, list every `Error` and `Warning` from `LogLB*`, materials, shaders, `LogBlueprint`, `LogScript` and `LogStreaming`, apart from known noise (the HttpListener port, the MCP probe lines). Say which are new in Phase 14.
5. **Plan completeness:**
   - every task in the P14 plan section 13 has a result subsection;
   - every "Not validated" item from earlier results was later validated, or is still open: list them;
   - the acceptance items of sections 8 and 8.1 are met (cite the evidence).
6. Write the report to `Docs/ArtTest/lighting/p14_8_qa.md` (the only file you create), with a verdict: "no blocking defects" or a list of blockers. Do not commit; the lead commits it.
