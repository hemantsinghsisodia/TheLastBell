# THE LAST BELL — Test Plan

## Levels of testing
1. **Compile gate:** C++ compiles (Live Coding or UBT) with zero errors. Changed Blueprints compile with zero errors and warnings are reviewed.
2. **Automation tests** (`LastBell.*`, run via the AutomationTest toolset or `UnrealEditor-Cmd ... -ExecCmds="Automation RunTests LastBell; Quit"`):
   - WorldState: add, remove and query; the delegate fires once per change.
   - Objectives: complete on tags, advance, recompute after load.
   - Save: round-trip of WorldState, actor records and checkpoint ID; a version mismatch counts as no save.
   - Interaction: an interface on the actor or its component is found; RequiredStateTags blocks interaction; a single-use interactable disables itself.
3. **Functional maps:** `L_Test_MicroSlice` (Phase 1) and later per-area test maps.
4. **Log check:** after every PIE session, review the Output Log for Error and Warning lines in the `LogLB*`, `LogBlueprint` and `LogScript` categories.
5. **Human playtest:** the checklist at each phase gate. This is the final authority.

## Bug severity
P0 means a crash, data corruption or a run that can't be completed. P1 is a major gameplay failure. P2 is a significant defect. P3 is polish. P0 and P1 bugs block a phase gate.

## Regression set (grows each phase)
- New Game → finish the current route.
- Die at every checkpoint, reload and check the state.
- Quit to the menu → Continue → check the state.
- Interactables can't be double-triggered or retriggered after a reload.

## Performance camera bookmarks
Defined in Phase 2 per area: Courtyard storm, Chapel nave, Crypt fog plus Warden, chase corridor, Bell Tower finale. These are reused for every measurement in PERFORMANCE_BUDGET.md.
