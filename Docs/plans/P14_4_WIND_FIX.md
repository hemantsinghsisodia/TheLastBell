# P14-4 wind fix: scale-aware sway height and storm-strength amplitudes

Owner approval: "go", 2026-11-07, after the P14-4 live check ("plants were not moving as they should in storm").
Branch: `claude/phase-14-lighting-storm`. Implementer: technical-artist (Sonnet, high effort). Lead: Opus.

## 1. Root cause (measured by the lead, 2026-11-07)
- The pipeline works: the storm subsystem is active in PIE, `lb.Storm.Intensity` is applied, and the foliage components have `bEvaluateWorldPositionOffset` true, distance 4000, Nanite meshes, and `M_LB_Foliage` has `maxWorldPositionOffsetDisplacement` 40. Three Simulate captures of the NE bed at intensity 1 differ only by 1 to 2 px along the blade edges.
- `MF_LB_WindSway` (bend) computes h = saturate(`PreSkinnedPosition`.z / `WindRefHeightCm`). `PreSkinnedPosition` is the **unscaled** mesh-local position, but the plants are placed scaled up, and the plan's `WindRefHeightCm` values assumed the final (scaled) heights:

| Mesh | Placed scale Z | Local height (cm) | `WindRefHeightCm` | Tip h | Tip lean at full storm (amp × h²) |
|---|---|---|---|---|---|
| `SM_LB_CC0_WeedPlant02` | 3.5 – 4.8 | 7.2 | 30 | 0.24 | 0.3 cm |
| `SM_LB_CC0_NettlePlant` | 2.9 – 4.3 | 6 – 19 | 70 | 0.09 – 0.28 | 0.1 – 0.7 cm |
| `SM_LB_CC0_GrassMedium02` | 1.7 – 2.4 | 16 – 40 | 90 | 0.17 – 0.45 | 0.5 – 3.2 cm |
| `SM_LB_CC0_Fern02` | 1.0 – 1.25 | 29 – 43 | 60 | 0.48 – 0.71 | 2.3 – 5.1 cm |
| `SM_LB_CC0_WildRooibos` | 1.0 – 1.5 | 31 – 54 | 80 | 0.38 – 0.67 | 1.0 – 3.2 cm |
| `SM_LB_CC0_SearsiaLucida` | 1.0 – 1.2 | 74 – 199 | 200 | 0.37 – 1.0 | 0.7 – 5.0 cm |

- Even with h = 1 the plan's amplitudes (grass 16 cm, weeds 6 cm) are a breeze, not a storm. The owner asked for storm motion.

## 2. Change 1: scale-aware height in `MF_LB_WindSway` (bend branch only)
Asset: `/Game/LastBell/Materials/Functions/MF_LB_WindSway`. The graph was built by `Tools/lighting/p14_2b_wind.py` `build_function()`; node names below are that script's local names, find the real expressions by class, position and wiring (read the graph first and print it).

New formula: **h = saturate(`PreSkinnedPosition`.z × S / `WindRefHeightCm`)**, where S = length(TransformVector(Instance → World, (0, 0, 1))) is the instance's world Z scale. `WindRefHeightCm` becomes a **world** height in cm (after the actor or instance scale), which is what the plan meant.

Add exactly these four expressions (positions are for readability):
1. `MaterialExpressionConstant3Vector` at (300, 1000): `constant` = {r 0, g 0, b 1, a 1}.
2. `MaterialExpressionTransform` at (450, 1000): `transformSourceType` = `TRANSFORMSOURCE_Instance`, `transformType` = `TRANSFORM_World`; input ← (1). Read both enum fields back; if the names are refused, list the enum values from the error and pick Instance → World (never Local → World: the ISMs need the instance transform).
3. `MaterialExpressionLength` at (600, 1000); input ← (2).
4. `MaterialExpressionMultiply` at (500, 950): A ← the existing `b_z` ComponentMask (B channel of `PreSkinnedPosition`), B ← (3).

Then rewire the existing `b_div` Divide: its **A** input ← (4) (it was `b_z`). B stays `WindRefHeightCm`. Nothing else in the graph changes; the flutter branch (ivy) stays exactly as it is. Update the `WindRefHeightCm` function input's description to "World height in cm (after the actor or instance scale) at which the bend is full".

Read back: the Divide's inputs (A = the new Multiply, B = the `WindRefHeightCm` input), the Multiply's inputs, the Transform's input and enums, and the node count (before + 4). Then `MaterialTools.recompile` the function, then recompile `M_LB_Foliage` and `M_LB_FoliageMasked`. Each must return without error. Check the editor log for new `Error` or `Warning` lines mentioning these assets.

## 3. Change 2: storm-strength values on the 8 MIs
Folder `/Game/LastBell/Environments/Courtyard/Materials/`. Use `MaterialInstanceTools.set_scalar_parameter` only. **Never call `set_parent`.** Do not touch any static switch.

| MI | `WindAmplitudeCm` old → new | `WindRefHeightCm` (world cm) old → new |
|---|---|---|
| `MI_Foliage_GrassMedium02` | 16 → **30** | 90 → **60** |
| `MI_Foliage_NettlePlant` | 9 → **18** | 70 → **45** |
| `MI_Foliage_WeedPlant02` | 6 → **12** | 30 → **30** (unchanged) |
| `MI_Foliage_Fern02` | 10 → **18** | 60 → **45** |
| `MI_Foliage_WildRooibos` | 7 → **14** | 80 → **60** |
| `MI_Foliage_SearsiaLucida` | 5 → **12** | 200 → **150** |
| `MI_Ivy_Green` | 2 → **4** | (no override; leave it) |
| `MI_Ivy_Dead` | 2 → **4** | (no override; leave it) |

`MI_Foliage_Moss01` is not touched. The largest offset is grass: 30 cm lean + 0.25 × 30 sag ≈ 31 cm, under `M_LB_Foliage`'s 40 cm cap; ivy 4 cm is under `M_LB_FoliageMasked`'s 6 cm cap, so neither cap changes.

For every MI, before and after: parent, every texture, vector and scalar override, and the static switches `bUseARM` and `bWind` (`get_static_switch_parameter`). Only the two scalars above may differ.

`DA_StormSettings` is **not** changed here: the sway speed (`PhaseSpeedLow/High`) is tuned live by the lead with the owner and saved in P14-5 with the other P14-4 choices.

## 4. Saving (one package per call, explicit, never save-all)
Before and after every save: `L_Monastery`, `M_LB_Surface` and `DA_StormSettings` must not be saved by you (`DA_StormSettings` may already be dirty in memory from the lead's live session: leave it alone, do not save it). `L_Monastery` and `M_LB_Surface` must not be dirty; if either is dirty, STOP and report.
Save in this order and check `is_dirty` false after each: `MF_LB_WindSway`, `M_LB_Foliage` (only if dirty), `M_LB_FoliageMasked` (only if dirty), then the 8 MIs.
Never save the parent Blueprints listed in `CLAUDE.md`/the brief, `BP_Door_Base_Dungeon`, `BP_RitualMechanism_CryptWinch`, or `M_LB_Surface`.

## 5. Not allowed
PIE, Simulate, captures (`capture_session.py`, `capture_poses.py`, `CaptureViewport`), synthetic input, any level edit, `set_parent`, `read_graph_dsl`, `BlueprintTools.create`, any C++ change.

## 6. Records and commit
- `Tools/lighting/p14_4_wind_fix.py`: the script you ran (`fn`, `mis`, `check` subcommands); `check` prints PASS/FAIL for the graph wiring and the 8 MI values.
- `Tools/mcp/MCP_NOTES.md`, section "Storm materials (Phase 14)", new item 11: `MaterialExpressionTransform` property names and enum values as they worked; "`PreSkinnedPosition` is unscaled: multiply by the instance Z scale for world heights".
- `Docs/plans/P14_LIGHTING_STORM.md`:
  - section 6.6 Bend: replace `h = saturate(PreSkinnedLocalPosition.z / WindRefHeightCm)` with the new formula and say `WindRefHeightCm` is a world height (P14-4 wind fix, D-100);
  - section 6.8 table: new amplitudes and reference heights, marked "P14-4 wind fix";
  - a results subsection "### P14-4 wind fix result (2026-11-07)" at the end: what changed, all read-backs, compile results, saves, and "Not validated: the sway itself (lead's captures and the owner's live check)".
- `Docs/DECISIONS.md`: append **D-100** in the existing table format: "Wind sway height is scale-aware: h = saturate(PreSkinnedPosition.z × instance Z scale / WindRefHeightCm), WindRefHeightCm in world cm; storm-strength amplitudes (grass 30, nettle 18, weed 12, fern 18, rooibos 14, searsia 12, ivy 4). Why: plants are placed scaled 1–4.8×, so the unscaled local height left the tips at h 0.1–0.5 and the lean at 0.1–5 cm (measured 2026-11-07); the owner asked for storm motion."
- Commit on the current branch only, staging by path (never `-A`), trailer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Never switch branches, merge or push.

## 7. After the agent (lead + owner)
1. Lead: the 3-capture wind probe of the NE bed (pose [4200, 0, 140, −12, 90], `DebugIntensityOverride` 1, `DebugFreezeFlash` 0, in memory only). Expect the blade tips to shift clearly (tens of pixels between captures), not 1–2 px.
2. Owner, live in Play: `lb.Storm.Intensity 0.6` and `1` at the courtyard and the garth; the lead adjusts `PhaseSpeedHigh` (start 4.5) and, if asked, the MI amplitudes in memory. The chosen values are saved in P14-5.
