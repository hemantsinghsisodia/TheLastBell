# P12 fix set 1: QA (qa-reviewer, 2026-11-06)

**Verdict: pass with caveats. No P1.** Reviewed against `Docs/plans/P12_FIX1_WARDEN_APPEARANCES.md`, commits after `115bc69`, in the editor session where the owner had just playtested. QA saved nothing, changed no asset and ran no PIE, capture or full suite.

## Checked live
- **`check_warden.py`:** default 61/61, `--bp` 43/43, `--disk` 15/15. `--disk` read both maps from disk, including both `BP_WardenApparition` instances, no placed `BP_WardenSilhouette`, and `TellLight` 5000 / 700 / (110, 0, 235) in `L_Monastery` and `L_Test_Warden`.
- **Both placed actors** match section 3 exactly: `Apparition_Courtyard` (`_C_0`) and `Apparition_Chapel` (`_C_1`), `LookPointHeight` 200, tick off at start, folder `Gameplay/Warden`.
- **`BP_WardenApparition` class defaults:** `Body` = `SM_LB_Warden_Apparition` (no overrides, so the mesh's MIs), NoCollision, no shadow. `Glow` = engine plane, `MI_Warden_ApparitionGlow`, (−150, 0, 150), pitch 90.
- **`BP_Warden`:**
  - Template and placed `TellLight` as above, `AttachTellLightToMask` gone.
  - `PlayStateFeedback`, `ShowWindupTell`, `EndWindupTell`, `SetupMaskGlow` and `SetMaskGlow` wired as section 7. `ELBWardenState` still has Chase 5 and Attack 6.
- **Materials and tuned MIs** as recorded in the F2 and F5 blocks: glow `Strength` 0.12, mask `Emissive` (0.05, 0.045, 0.038), `MI_Warden_BellMetal` `TellGlow` 0.
- **Map and editor state:** 2980 actors, no `P12_` or `P12F_` actors, nothing dirty.
- **Old assets:** `BP_WardenSilhouette` has no referencers, and `SM_LB_Warden_Silhouette` is used only by it, so they can go together. `M_LB_Silhouette` and `MI_LB_WardenSilhouette` stay, because `BP_WardenPlaceholderKill` uses them.

## Code review
No logic bug found in `LBApparitionLogic` or `ALBWardenApparition`. These edge cases behave as specified:
- zero durations
- no stations
- an invalid station index
- no player or camera
- the tag already present at BeginPlay
- `ReplaceState` mid-run (only `OnStateReplaced` fires, so there's no double trigger)
- Done is terminal and tick goes off
- the trace runs only after the cone test, ignoring the actor itself and the pawn
- an early fade-out starts from the current alpha

The unit and functional tests assert what their names claim.

## Findings
| # | Level | Finding | Action |
|---|---|---|---|
| 1 | P2 | Line of sight is never tested: nothing puts a blocker between camera and look point | Test added in the F6 follow-up |
| 2 | P3 | `BP_Warden` compares a byte to the literals 5 and 6; nothing guards the enum order | Unit test and enum comment added in the F6 follow-up |
| 3 | P3 | `FadeTiming` allows 2 ticks + 0.001 s; the spec said one tick | Kept: the extra tick is the zero-duration step that hands over to the next phase |
| 4 | P3 | The apparition logs nothing, so a playtest leaves no evidence of the beats | Log lines added in the F6 follow-up |
| 5 | P3 | `SourceArt/Warden/SM_LB_Warden_Silhouette.fbx` now holds the apparition bake | Renamed in the F6 follow-up |
| 6 | P3 | `MCP_NOTES.md` still listed `BP_WardenSilhouette` as a key Blueprint | Fixed by the lead |
| 7 | P3 | A death after the tag but before the beat ends, with a checkpoint that saved the tag, means the beat is never seen | Accepted: one-shot by design (section 3) |
| 8 | P3 | Too close on the very first fade-in tick spends `FadeOutSeconds` fading out from 0 | Accepted: invisible, negligible |

## Owner's playtest (2026-11-05, "all good"), from the editor log
- Checkpoints `CP_Approach`, `CP_Courtyard`, `CP_Chapel`, `CP_Chapel_After` and `CP_Crypt` saved.
- Sequence puzzle solved, so `State.Ritual.1` fired.
- The Warden went from Investigate to Attack, and the attack landed 0.6 s later, which is the unchanged windup.
- The player died, the world state was replaced, `CP_Crypt` reloaded, and PIE ran on cleanly.
- No Warden, apparition, `BP_Warden`, material or missing-asset errors, and no `Accessed None`. The only warning in the playtest is the existing `LogCrowdFollowing` one.

## Coverage
- **Only the owner's playtest covers:** the fades, the look gate and facing in play, the glow and mask look, the red light's strength in play, the reload not repeating the beats, and the dither (R-54).
- **Not seen in the playtest:** **the chase glow.** The log has no Chase state: Attack came straight from Investigate at stage 3. The F6 follow-up adds a functional test for the glow levels and the light, but nobody has seen it on screen.
