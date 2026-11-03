# Phase 11: Materials (surface polish): plan

**Status:** approved by the owner on 2026-11-02. P11-0, P11-1 and P11-2 done; P11-3 done: the owner chose A (D-086). P11-0 to P11-4 done; P11-5 in progress. The door corners and `Gobo_Moon` specks stay out of scope.
**Branch:** `claude/phase-11-materials`, from `main` (6dfa29d).
**Rules:** D-048 applies. The lead plans in Opus 5.5 at xhigh effort; every implementer is spawned with `model: "sonnet", effort: "high"`.

## Goal
Make the stone, wood and metal of the whole monastery look aged, wet and less repetitive, without changing gameplay, layout or the approved lighting.

The exit condition in `Docs/IMPLEMENTATION_PLAN.md` is "Surface polish". For this phase it means:
1. No wall shows two conflicting joint patterns.
2. No visible repeat on tall walls at normal play distance (closes R-26).
3. Walls show grime at the base and damp streaks, as `Docs/ART_DIRECTION.md` asks.
4. Decals read as stains and cracks, not stickers or hair (closes D-046).
5. Lantern glass glows (closes R-32).
6. GPU ≤ 16.6 ms at High, measured by the owner before and after (closes R-44).
7. The suite stays green, and the owner approves.

## What the lead found (read-only, 2026-11-02)

### 1. Walls have two unrelated joint patterns (new, the biggest visual problem)
- **Evidence:** `Docs/ArtTest/belltower/p10_8d_lt_passage_lantern.png`, on the lit wall to the right of the lantern. Dark, straight, sharp lines run through the middle of the blocks.
- **Cause:** the kit meshes have **modelled** 3 cm V-grooves (`Tools/blender/kit/kit_lib.py` `relief_cutters`; render `Docs/ArtTest/kit/03_walls.png`). `MI_Kit_Masonry` also uses `T_Medieval_Blocks_03`, which has its own **painted** joints at a 200 cm world tile. The two patterns don't line up.
- `Tools/blender/kit/README.md` predicted this: "if they fight the scanned material's own joints in Unreal, re-run with fewer or no joints".
- It is most visible under lanterns, at grazing angles, so it has grown with each lit area.
- `MI_Kit_Trim` uses the same painted blocks through UV0, so painted joints also cross quoins, voussoirs and coping. The P10-8d tablet had to leave this material for the same reason.

### 2. The vertex-colour plan has no data behind it
- `Docs/MODULAR_KIT.md` §8 says `M_LB_Surface` reads vertex colours (R wet, G grime, B wear) in Phase 11. In practice:
  - the kit's vertex colours are all white (README: "attribute `Color`, all white");
  - `M_LB_Surface` has no `VertexColor` expression (164 expressions checked);
  - `SM_LB_Kit_Wall_400x60x800_A` has only 1268 vertices, too sparse for useful paint on a 4 × 8 m wall;
  - there is no vertex-paint tool over MCP (D-056).
- **Recommendation:** drop the vertex-colour contract and use a world-space weathering layer (P11-5). It covers every wall automatically, needs no mesh changes and matches how the moss and puddle layers already work.

### 3. What already exists
- **`M_LB_Surface`** has 59 parameters: macro variation (`MacroTex`, `MacroScaleCm`, `MacroStrength`), `Wetness` / `WetnessVariation`, `bTopDust`, `bPuddles`, `bGapGrowth`, `Desaturation`, `NormalStrength`, `bWorldAlignedUV`, `bUseARM`.
- **Decals:** `M_LB_Decal` (full PBR, opacity, normal, edge fade) and `M_LB_Decal_Grime`. Soot, mould, water stain, chalk, drag marks, wax and leaf litter MIs exist and are placed. No crack decal exists (`find_actors "Crack"`: 0). The label searches found Grime 82, Mould 28, Leak 15, Soot 11, Chalk 4; those labels can overlap, so P11-2 counts them properly.
- **Lantern glass:** `M_LB_UnlitEmissive` exists, with one `Color` parameter. The lantern mesh is `/Game/LastBell/ArtTest/Props/Wooden_Lantern_01/SM_Wooden_Lantern_01`, slots `wooden_lantern_01` and `wooden_lantern_01_glass`.

### 4. Limits on changing meshes
- `StaticMeshTools.import_file` refuses an existing path, and `AssetTools.delete` nulls in-memory references (MCP_NOTES P9 §10). There is no reimport tool over MCP.
- `SM_LB_Kit_Wall_400x60x800_A` does have `assetImportData`, so the Content Browser's **Reimport** should work. That is an owner step, and it is unproven here.

## Decision needed: how to fix the double joints
The lead proposes a side-by-side test (P11-3) so the owner chooses from real pictures.

| | **A: remove the modelled grooves** | **B: remove the painted joints** |
|---|---|---|
| **Change** | Rebuild the wall meshes without V-grooves; keep the block texture | Keep the meshes; swap masonry and trim to a joint-free stone |
| **Look** | Photographic blocks with natural colour differences, but flat walls that rely on the normal map | Real depth under lanterns, and no 200 cm repeat, but every block has a similar tone unless P11-5 breaks it up |
| **Repetition (R-26)** | The 200 cm repeat stays, so it depends on P11-5 | Joints stop repeating; only fine grain tiles |
| **Risk** | Higher: 57 placed meshes to rebuild (374 actors; P11-2 census) and an in-place reimport | Lower: material instances only, and easy to undo |
| **Owner work** | Probably a bulk Reimport | None beyond choosing |

**The lead's expectation:** B is the safer and probably the better answer, but it can only be judged in pictures. Trim needs a joint-free stone under either option.

## Tasks
| Task | Scope | Owner | Depends on |
|---|---|---|---|
| **P11-0** | Approve this plan; D-085 (vertex colours dropped), R-46, R-47, the plan table | lead + owner | — |
| **P11-1** | GPU baseline: `stat gpu` at the 6 spots below | owner | P11-0 |
| **P11-2** | Census (read-only) and 24 baseline captures | technical-artist [EDITOR read-only], lead + owner | P11-0 |
| **P11-3** | Joint test in a separate test map; the owner chooses A or B (D-086) | asset-curator, technical-artist [EDITOR], lead + owner | P11-2 |
| **P11-4** | Apply the owner's choice across the game | technical-artist [EDITOR] | P11-3 |
| **P11-5** | Weathering layer in `M_LB_Surface` and rollout | technical-artist [EDITOR] | P11-4 |
| **P11-6** | Decal retune; new crack decals and their placement | technical-artist, environment-designer [EDITOR] | P11-5 |
| **P11-7** | Glowing lantern glass | technical-artist [EDITOR] | P11-2 |
| **P11-8** | Brightness re-check, QA, docs, owner GPU and playtest; "PHASE 11 READY FOR YOUR REVIEW" | lead + qa-reviewer + owner | all |

Editor tasks never overlap. Each one saves one package per `save_assets` call, never saves a parent Blueprint, and runs the suite (79/79) before its commit.

---

### P11-1: GPU baseline (owner, about 10 minutes)
This is also the measurement missing from Phase 10 (R-44).
1. Play in a New Editor Window.
2. In the console: `scalability 2`, `r.SetRes 1920x1080w`, `stat unit`, `stat gpu`.
3. Note the GPU total at:
   1. the courtyard garth;
   2. the chapel, mid-nave;
   3. the crypt ossuary;
   4. the cloister walk by the bells;
   5. the tower mid-stair;
   6. the belfry.
4. The lead records them in `Docs/PERFORMANCE_BUDGET.md`.

If any spot is already over 16.6 ms, the lead reports it before material work adds cost.

**Result (owner, 2026-11-02), GPU time at High, render 1664x846:**

| Spot | GPU ms | Headroom to 16.6 |
|---|---|---|
| Courtyard garth | 13.95 | 2.65 |
| Chapel, mid-nave | **15.32** | **1.28** |
| Crypt ossuary | 14.22 | 2.38 |
| Cloister, by the bells | 12.95 | 3.65 |
| Tower mid-stair | 12.30 | 4.30 |
| Belfry | 12.72 | 3.88 |

All six pass. The chapel has the least room, so P11-5 adds one chapel reading (acceptance 5). R-44 stays Open until the P11-8 re-check.

### P11-2: census and baseline
1. **Census script** `Tools/materials/census_p11.py` (read-only; the full spec is in the agent's brief). It writes `Docs/ArtTest/materials/census_p11.json` and `census_p11.md`:
   - **Enumeration:** `find_actors` with an empty name (2943 actors on 2026-11-02), cross-checked by `GetVisibleActors` from a high top-down camera (restore the camera afterwards). Don't pass `actor_type` for StaticMeshActor: that call closed the connection twice. Tell classes apart by the object name in the path (`StaticMeshActor_12`).
   - **every StaticMeshActor:** label, mesh, override materials, effective material per slot, transform, area;
   - **every other actor with a mesh component** (Blueprints, ISM): the same per component;
   - **placed count per mesh**, and which meshes have relief grooves (from the `relief_cutters` callers in `Tools/blender/kit/build_kit.py` and `Tools/blender/belltower/build_cloister.py`);
   - **every material instance using `M_LB_Surface`**: parent chain, textures, static switches, slots it fills, and how many actors use it per area;
   - **every decal:** label, material, size, area, and counts per decal MI;
   - **every lantern actor** (mesh name contains `Lantern`, not `Bracket`): the nearest light and its distance to the lantern's bounds, flagged if over 60 cm, and the material on its glass slot.

   **Areas** (`Docs/LEVEL_DESIGN.md` has no ranges, so these are the rule; actor location in world cm, first match wins):

   | Area | Rule |
   |---|---|
   | `crypt` | X ≥ 6300, −2950 ≤ Y ≤ 520, Z < −45 |
   | `tower` | 11990 ≤ X ≤ 13010, 1490 ≤ Y ≤ 2510 |
   | `cloister` | 9460 ≤ X ≤ 12040, 500 ≤ Y ≤ 3040 |
   | `passage` | 6040 ≤ X < 9460, 1400 ≤ Y ≤ 2600 |
   | `chapel` | 6000 ≤ X ≤ 9100, −1500 ≤ Y ≤ 850 |
   | `courtyard` | 300 ≤ X < 6000, −2600 ≤ Y ≤ 2600 |
   | `approach` | X < 300 |
   | `other` | anything else; the report lists these |

2. **Baseline captures** (lead, `Tools/crypt/capture_session.py --mode simulate`, owner at the PC): 24 poses in `Tools/materials/poses/p11_poses.json`, 6 per area, each area with one tall wall at 15 m, one lantern-lit wall at 3 m and one grazing view. Prefix `p11_base_`. Save the luma report as the baseline for P11-8 (`Docs/ArtTest/materials/p11_base_luma.json`).

**Census result (`Docs/ArtTest/materials/census_p11.md`):**
- **Grooves:** 57 distinct grooved meshes are placed, on 374 actors (51 full, 5 vertical only, 1 horizontal only), not the 129 FBX first assumed. The mapping comes from reading the Blender scripts; nothing was rebuilt.
- **Painted joints:** `T_Medieval_Blocks_03_BC` is on 7 placed MIs: `MI_Kit_Trim` (490 actors), `MI_Kit_Masonry` (257), `MI_Crypt_StoneWA` (42), `MI_Chapel_Masonry_Interior` (17, child of Masonry), `MI_Chapel_Trim_Dusty` (8, child of Trim), `MI_Env_TowerStone` (7, child of Masonry), `MI_Cl_CarveDirt` (5, child of Trim). Other textures are not yet judged by eye.
- **Crypt:** its main walls are the Fab `SM_Wall_00/01` with `MI_Stone_00..03`, not grooved kit pieces, so the double-joint problem belongs to the courtyard, chapel, passage, cloister and tower. `MI_Crypt_StoneWA` is the exception to check.
- **Lanterns:** 18, all `SM_Wooden_Lantern_01`, and every one has a light within 17 cm, so P11-7 needs no actor-level overrides. The current glass, `MI_Wooden_Lantern_01_Glass`, is a dark surface MI on `M_LB_Surface`.
- **Hidden:** 414 StaticMeshActors are hidden stair and rail collision cubes on `WorldGridMaterial`; none needs stone work.
- **Known limit:** the tower rule overlaps the cloister rule in X 11990–12040, so 25 placements count as `tower` (including the memorial tablet). This only affects area counts.

**Baseline result:** 24 poses captured to `Docs/ArtTest/materials/p11_base_*.png`, luma in `p11_base_luma.json`. Three poses were re-aimed after the first review (`ch_graze_north`, `cl_graze_east`, `cl_tall_north_15m`) because the walls they were meant to show were in black shadow or blocked. The crypt poses read mostly black by design, so they serve as brightness checks, not joint evidence. The double joints show clearly in `cy_lantern_route1_3m`, `cy_lantern_gate_3m`, `cl_graze_east`, `cl_tall_north_15m` and `ps_lantern_joints`.

**Capture settings:** the baseline runs with the editor at High (`sg.*` = 2, read with `SearchCVars`; set by the owner's `scalability 2` in this editor session) and the Warden off. P11-8 must read `sg.*` first and match them, because a restarted editor can return to another level.

### P11-3: joint test (separate map; `L_Monastery` untouched)
**Order:** P11-3a (downloads) and P11-3b (Blender) run together, with no editor. Then P11-3c (editor). Then P11-3d (lead and owner: captures, sheet, choice).

Test assets live under `/Game/LastBell/ArtTest/P11/`. `MapsToCook` lists only `L_MainMenu` and `L_Monastery`, so the test map is never cooked.

#### P11-3a: downloads (asset-curator; CC0 only, 2K)
- **Candidates:** `polyhaven:rock_surface` (role B1), `polyhaven:worn_rock_natural_01` (role B2).
- **Accept only if**, tiled at 300 cm on a wall, there are no block lines, mortar lines or regular patterns, no feature larger than about 30 cm (big cracks would cross the modelled joints), and no moss or sand.
- **If one fails:** search `3d-assets-local` for CC0 Poly Haven or ambientCG stone or rock textures and replace it. Exactly two survive.
- **Colour match:** `Tools/materials/p11_candidate_params.py` computes, for each candidate, linear mean RGB of the colour map, then `raw_c = medieval_c / candidate_c` with `medieval` = (0.1869, 0.1470, 0.0991) (`T_Medieval_Blocks_03_BC`). `BrightnessMul = max(raw_c)`, clamped to 0.5–2.5; `BaseColorTint = raw_c / max(raw_c)`. Only surface structure should differ between bays. Output: `Tools/materials/p11_candidate_params.json`, also recording each candidate's real-world size if the source gives one.
- **Outputs:** `ExternalAssets/Incoming/<one folder each>/`; `Docs/ASSET_REGISTRY.md` rows; `Docs/ArtTest/materials/p11_candidates.png` (each colour map tiled 2 × 2).

**Result (e368f49):** B1 = `polyhaven:rock_surface` (CC0, 200 cm; soft darker patches that visibly repeat, so watch for this on long walls). B2 = `polyhaven:rock_01` (CC0, 150 cm, so the tile clamps to 200 cm; faint horizontal bands). `worn_rock_natural_01` failed review: saturated yellow, with lichen specks. It stays on disk, git-ignored.

#### P11-3b: no-groove test meshes (technical-artist, Blender only)
- **Script:** `Tools/materials/build_p11_test_walls.py`. It imports `Tools/blender/kit/kit_lib.py` and `build_kit.py`, and wraps `K.relief_cutters` so every call has `h_grooves=False, vertical=False, recess_prob=0.0`, chips kept. Neither kit file is edited.
- **Builds**, with the same seeds and builders as the originals, to `SourceArt/P11/`:

  | New mesh | Same as |
  |---|---|
  | `SM_LB_P11_NoGroove_Wall_400x60x800_A` | `Wall_400x60x800_A` |
  | `SM_LB_P11_NoGroove_Wall_400x60x800_B` | `Wall_400x60x800_B` |
  | `SM_LB_P11_NoGroove_Wall_100x60x800` | `Wall_100x60x800` |
  | `SM_LB_P11_NoGroove_Plinth_400x80x60` | `Trim_Plinth_400x80x60` |
  | `SM_LB_P11_NoGroove_Plinth_100x80x60` | `Trim_Plinth_100x80x60` |

- **Acceptance:** bounds, pivot, material slots and UCX match the originals; a render `Docs/ArtTest/materials/p11_nogroove_render.png` shows original beside no-groove, with no joints on the no-groove pieces. `SourceArt/Kit` is byte-identical (`git status`).

**Result (8d0d946):** all five built and verified. `Plinth_100x80x60` is identical to the original, because at 100 cm the original has no joints. Chip positions differ from the originals, because skipping the grooves uses fewer random numbers; count and size range are the same.

#### P11-3c: materials, imports, test map (technical-artist [EDITOR])
**Imports:**
- Textures to `/Game/LastBell/ArtTest/P11/Textures/`: `T_P11_B1_BC/_N/_ARM`, `T_P11_B2_BC/_N/_ARM`. Copy compression, sRGB and size settings from the matching `T_Medieval_Blocks_03_*`. Normal maps: the DirectX version.
- Meshes to `/Game/LastBell/ArtTest/P11/Meshes/`, with the FBX rules in MCP_NOTES (Nanite on). Mesh default slots: `MI_Kit_Masonry`, `MI_Kit_Trim`, `MI_Kit_Rubble`.

**Materials** in `/Game/LastBell/ArtTest/P11/Materials/`, parent `M_LB_Surface`:

| MI | Base and normal | Switches | Scalars and tint |
|---|---|---|---|
| `MI_P11_B1_Masonry`, `MI_P11_B2_Masonry` | candidate BC, N, ARM | `bWorldAlignedUV` on, `bUseARM` on | `WorldTileSizeCm` = source size clamped to 200–400, else 300; `MacroStrength` 0.4; `WorldBlendSharpness` 4; `BrightnessMul` and `BaseColorTint` from the JSON |
| `MI_P11_B1_Trim`, `MI_P11_B2_Trim` | candidate BC, N, ARM | `bWorldAlignedUV` off, `bUseARM` on | `UVScale` = 100 / tile size (UV0 is 1 unit per 100 cm); `MacroStrength` 0.4; `BrightnessMul` = masonry × 1.35; tint = masonry tint × (1, 0.95, 0.86) (the `MI_Kit_Trim` offsets) |
| `MI_P11_B3_Masonry` | duplicate of `MI_Cl_TabletStone` | unchanged | `NormalStrength` 0.60, everything else as the original |
| `MI_P11_B3_Trim` | duplicate of `MI_P11_B3_Masonry` | unchanged | `BrightnessMul` 1.35 |

**Map:** `/Game/LastBell/ArtTest/P11/L_Test_P11_Walls`. Duplicate the smallest `L_Test_*` map with `AssetTools.duplicate`, load it, and remove every actor except `WorldSettings`. If duplicating a map is refused, stop and report. Scripted in `Tools/materials/build_p11_test_map.py`, with a read-back `--check`.

**Light and post-process (values read from `L_Monastery` on 2026-11-02):**

| Actor | Values |
|---|---|
| `P11_Floor` | `/Engine/BasicShapes/Cube` at (11250, −1000, −20), scale (255, 40, 0.4), `MI_Kit_Floor`. Top at Z 0 |
| `P11_Moon` | DirectionalLight, pitch −38, yaw 35, intensity 0.9, colour (0.745098, 0.803922, 0.921569), shadows on, `forwardShadingPriority` 1 (as in `L_Monastery`; without it Unreal prints a warning across every capture) |
| `P11_MoonFill` | DirectionalLight, pitch −28, yaw −145, intensity 0.06, colour (0.72549, 0.784314, 0.882353), shadows off |
| `P11_Sky` | SkyLight at Z 600, `SLS_SpecifiedCubemap`, `/Game/LastBell/ArtTest/Sky/HDRI_MoonlessGolf`, intensity 0.28, colour (0.882353, 0.862745, 0.843137), lower hemisphere (0.015, 0.02, 0.035), not black |
| `P11_PP` | PostProcessVolume, unbound, `AutoExposureMinBrightness` and `MaxBrightness` 0.65, `ColorSaturationShadows` (0.65, 0.65, 0.65, 1), each with its override on |

No fog and no sky dome: only the walls are being compared.

**Bays.** A wall's front face is Y = 0, facing −Y, the side the moon lights. All yaw 0 unless stated. Slots are set per actor by slot name; `MAT_Rubble` is always `MI_Kit_Rubble`.

| Bay | Index i | Meshes | `MAT_Masonry` | `MAT_Trim` |
|---|---|---|---|---|
| `Today` | 0 | current kit | `MI_Kit_Masonry` | `MI_Kit_Trim` |
| `A` | 1 | no-groove | `MI_Kit_Masonry` | `MI_P11_B2_Trim` (changed from `B3_Trim` after the first captures: the B3 stone had already lost, and it made A's edge stone look wrong) |
| `B1` | 2 | current kit | `MI_P11_B1_Masonry` | `MI_P11_B1_Trim` |
| `B2` | 3 | current kit | `MI_P11_B2_Masonry` | `MI_P11_B2_Trim` |
| `B3` | 4 | current kit | `MI_P11_B3_Masonry` | `MI_P11_B3_Trim` |

- **Lantern row**, X0 = 1500 × i, labels `P11_<Bay>_*`:
  - walls: `400_A` at (X0, 0, 0), `100` at (X0 + 400, 0, 0), `400_B` at (X0 + 500, 0, 0);
  - plinths: `400` at (X0, −10, 0), `100` at (X0 + 400, −10, 0), `400` at (X0 + 500, −10, 0);
  - `SM_LB_Prop_LanternBracket_R40` at (X0 + 450, 0, 330), yaw −90;
  - `SM_Wooden_Lantern_01` at (X0 + 450, −40, 278.1);
  - PointLight at (X0 + 450, −40, 320): 200 lumens, radius 600, colour (1, 0.549020, 0.219608), shadows off, `MI_LF_Lantern`, scattering 1.5 (`L_Cl_Bells` values).
- **Moonlight row**, no lanterns, X1 = 10000 + 2500 × i, labels `P11_Far_<Bay>_*`:
  - walls `A, B, A, B, A` at (X1 + 400 × k, 0, 0), k = 0–4;
  - plinths `400` at (X1 + 400 × k, −10, 0).

**Finish:** save packages one at a time, then load `L_Monastery` back and confirm it is not dirty. Suite 79/79.

#### P11-3d: captures and choice (lead + owner)
Poses in `Tools/materials/poses/p11_joint_poses.json`, prefix `p11_jt_`, in PIE Simulate on the test map:

| View | Pose [x, y, z, pitch, yaw] |
|---|---|
| Face-on, 3 m under the lantern | [X0 + 450, −300, 170, 5, 90] |
| Grazing, 1.5 m off the wall | [X0 + 50, −150, 170, 3, 14] |
| 15 m, moonlight only | [X1 + 1000, −1500, 170, 14, 90] |

Contact sheet `Docs/ArtTest/materials/p11_joint_test.png`: 5 rows by 3 columns, labelled. If `B3` is far from `Today` in brightness, the lead corrects `MI_P11_B3_*` `BrightnessMul` once and re-captures that bay, so brightness doesn't decide the comparison. **The owner chooses.** D-086 records the choice. The editor returns to `L_Monastery` afterwards.

**Result (lead, 2026-11-02): `Docs/ArtTest/materials/p11_joint_test.png`.** Brightness at 3 m (`central40`, `p11_jt_luma.json`): `Today` 0.314, `A` 0.315, `B1` 0.324, `B2` 0.304, `B3` 0.346. The colour match worked, so brightness doesn't decide this; `B3` got no correction because it fails on structure.

| Bay | 3 m and grazing, lantern | 15 m, moonlight | Verdict |
|---|---|---|---|
| `Today` | Dark lines cut through painted blocks | Wallpaper repeat every 200 cm | The problem |
| `A` | Convincing rock-faced masonry with real-looking depth, and no conflict | The same wallpaper repeat as today | Best up close; needs a repeat fix |
| `B1` | Flat stone with thin cut lines | Soft dark patches repeat | Worse than `B2` |
| `B2` | Flat, smooth, like modern cladding; the recessed panels look artificial | Calm, no wallpaper repeat | Best at distance |
| `B3` | Large lumps from `T_Rock_064_N` cross the joints | Grey, off-colour | Out |

**New finding:** the modelled grooves don't line up where two wall pieces meet, because `Wall_400x60x800_B` uses different course heights (`vary=True`). `B1`, `B2` and `B3` expose this, since the grooves are their only joints. Fixing it would need a mesh rebuild too, which removes most of option B's advantage. `A` doesn't have this problem: its joints are world-aligned, so they run on across pieces.

**The lead's recommendation changes from B to A,** reversing the expectation above. Players mostly see these walls at 1–5 m by lantern. If the owner chooses A, the repeat fix is tested on the test map before any mesh is rebuilt, so `B2` stays available as a fallback until then.

**Limits of the test:** no fog, no weathering, no game geometry around the walls. The owner chooses (D-086).

### P11-4: apply the choice
**The owner chose A on 2026-11-02 (D-086).** The order protects the fallback: `B2` stays available until P11-4b rebuilds the first mesh.

| Step | Scope | Owner |
|---|---|---|
| **P11-4a** | Fix the 15 m repeat on the test map, with no game asset changed | technical-artist [EDITOR test map], lead + owner |
| **P11-4b** | Rebuild the masonry meshes without grooves | technical-artist (Blender) |
| **P11-4c** | Prove Reimport on one mesh without saving, then bulk Reimport | lead + owner |
| **P11-4d** | Game materials: flattened blocks on masonry, joint-free stone on trim; suite; captures | technical-artist [EDITOR] |

P11-4b to P11-4d are written below, after P11-4a.

#### P11-4a: repeat test
**Why:** the 15 m row of the sheet shows pale blocks repeating every 200 cm. A trial outside Unreal (lead) shows these come mostly from the tone of individual blocks in the colour map. Dividing out the low-frequency tone cut that variation from 0.123 to 0.038 and kept the blocks' look up close. Whether the normal map also repeats can only be seen in Unreal.

**Texture.** Script `Tools/materials/make_flat_blocks.py`:
- input `ExternalAssets/Incoming/polyhaven-medieval_blocks_03/polyhaven-medieval_blocks_03/medieval_blocks_03_diff_2k.jpg`, output `SourceArt/P11/T_P11_FlatBlocks_BC.png` (2048 × 2048, 8-bit sRGB);
- work in linear light. `grey` = mean of R, G, B. `low` = `grey` blurred with a Gaussian of sigma 100 pixels, wrapped at the edges so the tile stays seamless (FFT with numpy; scipy isn't installed). Multiply every channel by `grey.mean() / max(low, 0.001)`, then convert back to sRGB and clip;
- it prints the low-frequency figure: `grey` blurred with sigma 60, wrapped, then its standard deviation divided by its mean. Expect about 0.038 against 0.123 for the original.

Imported as `/Game/LastBell/ArtTest/P11/Textures/T_P11_FlatBlocks_BC`, with settings copied from `T_Medieval_Blocks_03_BC`. Registry row: own derivative of the CC0 `medieval_blocks_03`.

**Materials**, each a duplicate of `MI_Kit_Masonry` in `/Game/LastBell/ArtTest/P11/Materials/`, with `BaseColorTex` = `T_P11_FlatBlocks_BC`. Normal and ARM stay as they are:

| MI | Change on top of that | Tests |
|---|---|---|
| `MI_P11_A1_Masonry` | none | flattened tone alone |
| `MI_P11_A2_Masonry` | `MacroStrength` 0.8 (from 0.4) | plus stronger large-scale variation |
| `MI_P11_A3_Masonry` | `WorldTileSizeCm` 260 (from 200) | plus fewer repeats and larger blocks |

**Map:** the `B1`, `B2` and `B3` bays give way to `A1`, `A2` and `A3` at the same indices (2, 3, 4), with the no-groove meshes and `MI_P11_B2_Trim`. `Today` and `A` don't change. `git` history keeps the B bays and their sheet stays in the repo.

**Captures (lead + owner):** the three views of `A1`, `A2`, `A3`, prefix `p11_rp_`. Sheet `Docs/ArtTest/materials/p11_repeat_test.png`, rows `Today`, `A`, `A1`, `A2`, `A3`, reusing the `p11_jt_today_*` and `p11_jt_a_*` images.

**Pass:** from 15 m the rows of pale blocks are gone or close to it, and up close the blocks still read as `A` does. P11-5's weathering still comes on top. **If nothing passes,** the lead reports it and the owner decides between accepting the repeat for now or `B2`.

This step changes only test assets, so it needs no suite run.

**Result (lead, 2026-11-02): `Docs/ArtTest/materials/p11_repeat_test.png`. It passes.** Brightness at 3 m (`central40`, `p11_rp_luma.json`): `A` 0.315, `A1` 0.318, `A2` 0.302, `A3` 0.316.

| Bay | Up close | 15 m, moonlight | Verdict |
|---|---|---|---|
| `A1` | As good as `A` | The rows of pale blocks are gone; a faint regular pattern remains at full size, partly from the normal map | Passes |
| `A2` | As `A1`, about 5 % darker | The calmest wall on the sheet | Passes; best at distance |
| `A3` | Blocks are visibly larger | The pattern is larger and easier to read than in `A1` | Rejected |

**The owner chose `A2`, the lead's pick** (flattened tone, `MacroStrength` 0.8), with the 5 % corrected through `BrightnessMul` in P11-8. Normal-map shading still repeats faintly, so P11-5's weathering has to carry the rest. The rebuild starts only after the owner's "go", because that is the point where the `B2` fallback stops being free.

#### P11-4b: rebuild (technical-artist; Blender, plus one read-only snapshot from the editor)
**Which meshes (`Tools/materials/p11_reimport_list.json`, checked by the lead on 2026-11-02):** of the 57 grooved meshes placed, **51 are rebuilt** (22 kit, 16 cloister, 13 tower; 218 placements). All have grooves in `MAT_Masonry`. The other 6 (`Kerb` ×3, `Trim_Plinth` ×2, `Kit_Pier`) use `MAT_Trim` only, and trim becomes joint-free, so their grooves become their only joints. They stay as they are. Every mesh's import source exists, and its MD5 matches what Unreal imported, so a reimport brings in nothing except this change.

**Rule, in `Tools/blender/kit/kit_lib.py` `relief_cutters`:** a module constant `MASONRY_GROOVES = False` (comment: D-086, masonry carries its joints in the texture). `skip = groove_mat == SLOT_MASONRY and not MASONRY_GROOVES`. When `skip` is true, the groove and recess loops still run and still draw their random numbers, but don't append their cutters. Chips therefore stay exactly where they were. Calls with `groove_mat=S1` (caps, plinths, kerbs, piers) are untouched.

**Why not simply switch the grooves off:** the first version of this rule (`h_grooves = vertical = False`, `recess_prob = 0.0`) skipped those random draws, which moved every chip. The verifier stopped the task: `SM_LB_Cl_ArcadeArch_120x80` lost `MAT_Rubble`, and `_170x80` and `_270x80` gained it. Unreal drops unused slots, so that would have shifted their materials. Nothing was committed.

**Build only the 51,** with each builder's `--only`, into their current folders. Non-listed FBX files must stay byte-identical.

**Checks:** `verify_kit.py`, `verify_cloister.py`, `verify_tower.py` pass, and `Tools/materials/verify_p11_rebuild.py` compares every rebuilt FBX with a copy taken before the build: bounds within 0.1 cm, the same used material slots in the same order, the same UCX count and bounds, and no long groove line left on masonry faces. Any slot difference stops the task, because Unreal drops unused slots.

**Result (7eb0232):** 51 FBX rebuilt. `verify_kit` 46/46, `verify_cloister` 50/50, `verify_tower` 33/33, `verify_p11_rebuild` 51/51. Used slots, bounds and UCX are unchanged; triangles 270055 to 87422 (−67.6 %). Nothing is imported yet, so the game looks the same.

**The verifiers stopped this task three times:**
1. **Chips moved** (see the rule above).
2. **`chk_pier`** measured pier faces from vertices that only the grooves had put there. It now reads the band edges and is still proved non-vacuous.
3. **Shading wedges:** a plain wall face is a few huge triangles, so a chip rim's tilted normal shaded across the whole face. `kit_lib.finalize` gained `hard_flat_slot`; `build_kit`, `build_cloister` and `tw_common` pass `SLOT_MASONRY`, and `build_props` doesn't. `verify_p11_rebuild.py` now fails any mesh with over 1 % of flat masonry area tilted more than 3 degrees; all 51 read 0.0 %.

**Known limit:** `hard_flat_slot` means slot 0, and some kit and tower pieces (roof, timber) have another material in slot 0. None was rebuilt, so nothing changed, but a future rebuild of those pieces would hard-shade their large flat faces. Check this before rebuilding them.

#### P11-4c: Reimport (lead + owner)
`Tools/materials/check_reimport.py` snapshots each mesh's tags, slots and default materials before, then compares after, including `FileMD5` against the rebuilt FBX.
1. **Proof, nothing saved:** the lead selects `SM_LB_Kit_Wall_400x60x800_A` in the Content Browser, the owner right-clicks and chooses Reimport, and the lead runs the check for that one mesh and takes a capture. If it fails: stop and report. Unreal is closed with **Don't Save**, which restores the old mesh.
2. **Bulk:** the lead selects the meshes one folder at a time (3 folders), and the owner reimports each selection.
3. **Check all 51,** then save each mesh alone, explicitly.

**Result:** all 51 reimported, checked and saved one at a time; `L_Monastery` saved after a comparison with the census found 2943 actors and 2485 static mesh actors unchanged. Suite 79/79 on the mirror. R-48 closes.

**What the proof on one mesh could not show, and what else was learned (for MCP_NOTES):**
- **Reimport added collision.** The 29 cloister and tower meshes were imported through Interchange (`InterchangeAssetImportData`) with no collision by design. Reimport gave each a generated convex hull that fills arch and door openings. The kit meshes (`FbxStaticMeshImportData`, with UCX) don't have this problem. `StaticMeshTools.remove_collisions` clears it, and it must be run before saving. Any later reimport of these meshes needs the same step.
- **Reimport marks `L_Monastery` dirty,** even though no actor changes.
- **The `ApproxSize` tag isn't a size.** It reads larger than the mesh and varies between builds (435x77x802 for a 400x60x800 wall). `StaticMeshTools.get_bounds` is the real value; `check_reimport.py` now uses it.
- **`SelectAssets` doesn't work** for selecting in the Content Browser here (no effect, or a timeout). The search box takes `Name==A OR Name==B`, which worked for all three folders.

#### P11-4d: game materials (technical-artist [EDITOR])
**Textures,** new, in `/Game/LastBell/Environments/Kit/Textures/`. Compression, sRGB, group, size and virtual-texture settings are copied from the matching `/Game/LastBell/ArtTest/Materials/Medieval_Blocks_03/T_Medieval_Blocks_03_*`:

| New texture | Source |
|---|---|
| `T_Kit_BlocksFlat_BC` | `SourceArt/P11/T_P11_FlatBlocks_BC.png` |
| `T_Kit_TrimStone_BC` | `ExternalAssets/Incoming/polyhaven-rock_01/rock_01_diff_2k.jpg` |
| `T_Kit_TrimStone_N` | `ExternalAssets/Incoming/polyhaven-rock_01/rock_01_nor_dx_2k.jpg` |
| `T_Kit_TrimStone_ARM` | `ExternalAssets/Incoming/polyhaven-rock_01/rock_01_arm_2k.jpg` |

**Materials,** in place:

| MI | Change | Stays |
|---|---|---|
| `MI_Kit_Masonry` | `BaseColorTex` = `T_Kit_BlocksFlat_BC`; `MacroStrength` 0.8 | normal, ARM, `WorldTileSizeCm` 200, `WorldBlendSharpness` 4 |
| `MI_Kit_Trim` | `BaseColorTex`, `NormalTex`, `ARMTex` = `T_Kit_TrimStone_*`; `UVScale` 0.5; `BrightnessMul` 1.34829; `BaseColorTint` (1.0, 0.91311, 0.73639) | `MacroStrength` 0.4, `Wetness` 0, `bWorldAlignedUV` off |

**Children** (`MI_Chapel_Masonry_Interior`, `MI_Env_TowerStone`, `MI_Chapel_Trim_Dusty`, `MI_Cl_CarveDirt`) override no texture, so they inherit. They are not edited. Their effective textures are read back.

**`MI_Crypt_StoneWA` stays as it is:** its 42 actors are crypt pieces with no modelled grooves, so they have no double joints.

**Checks:** read-backs, suite 79/79. Then the lead captures all 24 baseline poses (`p11_a2_`) with the owner, and judges the memorial tablet at `cl_lantern_bells_3m`. Brightness corrections wait for P11-8.

**Result (6f3b899, 38bbc53):** applied; suite 79/79 before the roughness correction below, which only changes two values on one MI. 24 captures, prefix `p11_a2_`, luma in `p11_a2_luma.json`. Brightness against the baseline (mean): 0.91 to 1.01; lowest `cl_lantern_bells_3m` 0.91, then `tw_mid_stair`, `ch_sacristy_3m`, `ps_lantern_joints` and `cy_lantern_gate_3m` at 0.94. The crypt is unchanged. P11-8 corrects this through `BrightnessMul`.

**Added after review:** `MI_Kit_Trim` `RoughnessMin` 0.85, `RoughnessMax` 1.0. `rock_01` is far shinier than the stone it replaced (roughness mean 0.516 against 0.938), and the moon drew a thin bright line along a wall's cap (`cy_tall_south_15m`, max luma 0.152 before, 0.538 after, 0.173 with this fix). The memorial tablet stays legible at 3 m.

### P11-5: weathering layer (`bWeathering`)
**Started on the owner's "go", 2026-11-03,** with other GPU apps closed (R-47, D-053).

| Step | Scope | Owner |
|---|---|---|
| **P11-5a** | Add the layer to `M_LB_Surface`, switch off everywhere; one master recompile; suite | technical-artist [EDITOR] |
| **P11-5b** | Regression captures against `p11_a2_` | lead + owner |
| **P11-5c** | Rollout and tuning on the wall MIs; captures; owner's chapel GPU reading | lead + owner |

**Which MIs get it (from the census):** `MI_Kit_Masonry` and `MI_Kit_Trim`, so plinths and caps weather with their walls and no hard edge forms where they meet. Their children inherit, except `MI_Cl_CarveDirt`, which is set off so the memorial's lettering doesn't change.

**The crypt stays out of this layer:** its main walls use `MI_Stone_00..03` on a different master, not `M_LB_Surface`. It keeps its Phase 9 grime decals. `MI_Kit_Rubble` stays off to save cost.

**Where it goes:** straight after base colour and roughness, before growth, dust and puddles. `Multiply_9` is the finished base colour; `Clamp_0` is the finished roughness.

#### P11-5a: nodes
All parameters go in group `Weathering`.

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `bWeathering` | static switch (two nodes, same name) | false | Layer on or off |
| `WeatherFloorZ` | scalar | 0 | World Z of the local floor |
| `GrimeBaseHeightCm` | scalar | 220 | Height of the base grime band |
| `GrimeBaseAmount` | scalar | 0.45 | Band strength |
| `GrimeNoiseScaleCm` | scalar | 180 | Breaks up the band's top edge |
| `GrimeTint` | vector | (0.30, 0.27, 0.22) | Grime colour multiplier |
| `StreakScaleHCm` | scalar | 70 | Streak width |
| `StreakScaleVCm` | scalar | 900 | Streak length |
| `StreakThreshold` | scalar | 0.55 | Higher means fewer streaks |
| `StreakAmount` | scalar | 0.30 | Streak strength |
| `StreakRoughness` | scalar | 0.35 | Roughness in streaks (wet look) |
| `PatchScaleCm` | scalar | 1100 | Size of the large colour patches |
| `PatchAmount` | scalar | 0.30 | Patch strength |
| `PatchTint` | vector | (0.70, 0.74, 0.68) | Patch colour multiplier (stronger than first planned: at 0.82 a patch would change a wall by only about 3 %) |

**Custom node** `LB_WeatherMask`, output `CMOT_Float3`. Inputs in this order: `WorldPos` (`WorldPosition_0` XYZ, as the other masks), `NormalWS` (`VertexNormalWS_2`), then each scalar above except `StreakRoughness`, named exactly as the parameter. `StreakRoughness` is used only in the roughness lerp.

```hlsl
float wall = saturate((1.0 - abs(NormalWS.z)) * 2.0);
float u = WorldPos.x + WorldPos.y;
float2 pg = float2(u, WorldPos.z) / max(GrimeNoiseScaleCm, 1.0) + float2(23.7, 5.1);
float2 ig = floor(pg); float2 fg = frac(pg); float2 sg = fg * fg * (3.0 - 2.0 * fg);
float g1 = frac(sin(dot(ig, float2(127.1, 311.7))) * 43758.5453);
float g2 = frac(sin(dot(ig + float2(1.0, 0.0), float2(127.1, 311.7))) * 43758.5453);
float g3 = frac(sin(dot(ig + float2(0.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float g4 = frac(sin(dot(ig + float2(1.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float gEdge = lerp(lerp(g1, g2, sg.x), lerp(g3, g4, sg.x), sg.y);
float band = (1.0 - saturate((WorldPos.z - WeatherFloorZ) / max(GrimeBaseHeightCm, 1.0))) * lerp(0.6, 1.0, gEdge);
float2 p1 = float2(u / max(StreakScaleHCm, 1.0), WorldPos.z / max(StreakScaleVCm, 1.0)) + float2(71.3, 13.9);
float2 i1 = floor(p1); float2 f1 = frac(p1); float2 u1 = f1 * f1 * (3.0 - 2.0 * f1);
float a1 = frac(sin(dot(i1, float2(127.1, 311.7))) * 43758.5453);
float a2 = frac(sin(dot(i1 + float2(1.0, 0.0), float2(127.1, 311.7))) * 43758.5453);
float a3 = frac(sin(dot(i1 + float2(0.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float a4 = frac(sin(dot(i1 + float2(1.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float sa = lerp(lerp(a1, a2, u1.x), lerp(a3, a4, u1.x), u1.y);
float2 p2 = p1 * 2.37 + float2(0.37, 0.71);
float2 i2 = floor(p2); float2 f2 = frac(p2); float2 u2 = f2 * f2 * (3.0 - 2.0 * f2);
float b1 = frac(sin(dot(i2, float2(127.1, 311.7))) * 43758.5453);
float b2 = frac(sin(dot(i2 + float2(1.0, 0.0), float2(127.1, 311.7))) * 43758.5453);
float b3 = frac(sin(dot(i2 + float2(0.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float b4 = frac(sin(dot(i2 + float2(1.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float sb = lerp(lerp(b1, b2, u2.x), lerp(b3, b4, u2.x), u2.y);
float streak = smoothstep(StreakThreshold, StreakThreshold + 0.15, sa * 0.6 + sb * 0.4);
float2 pc = float2(u, WorldPos.z) / max(PatchScaleCm, 1.0) + float2(3.3, 57.7);
float2 ic = floor(pc); float2 fc = frac(pc); float2 sc = fc * fc * (3.0 - 2.0 * fc);
float c1 = frac(sin(dot(ic, float2(127.1, 311.7))) * 43758.5453);
float c2 = frac(sin(dot(ic + float2(1.0, 0.0), float2(127.1, 311.7))) * 43758.5453);
float c3 = frac(sin(dot(ic + float2(0.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float c4 = frac(sin(dot(ic + float2(1.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float blotch = lerp(lerp(c1, c2, sc.x), lerp(c3, c4, sc.x), sc.y);
return float3(wall * saturate(band * GrimeBaseAmount + streak * StreakAmount), wall * blotch * PatchAmount, wall * streak * StreakAmount);
```
(`noise`, `sample` and `patch` are reserved words in HLSL, so the code avoids them.)

**Wiring:**

| New node | Inputs |
|---|---|
| `ComponentMask` R, G, B | each from `LB_WeatherMask` |
| `Lerp_Grime` | A = `Constant3Vector` (1, 1, 1); B = `GrimeTint` RGB; Alpha = mask R |
| `Lerp_Patch` | A = the same constant; B = `PatchTint` RGB; Alpha = mask G |
| `Mul_1` | A = `Multiply_9`; B = `Lerp_Grime` |
| `Mul_2` | A = `Mul_1`; B = `Lerp_Patch` |
| `Switch_BaseColor` (`bWeathering`) | True = `Mul_2`; False = `Multiply_9` |
| `Lerp_Rough` | A = `Clamp_0`; B = `StreakRoughness`; Alpha = mask B |
| `Switch_Rough` (`bWeathering`) | True = `Lerp_Rough`; False = `Clamp_0` |

**Rewire, last and together:**
- `LinearInterpolate_12.A` and `StaticSwitchParameter_11.False` take `Switch_BaseColor` (they read `Multiply_9` today).
- `LinearInterpolate_13.A` and `StaticSwitchParameter_17.False` take `Switch_Rough` (they read `Clamp_0` today).

**Safety order:**
1. Compile the same Custom node first on a small throwaway material, `/Game/LastBell/ArtTest/P11/Materials/M_P11_WeatherTest`, so an HLSL error can't reach the master.
2. Only then edit the master, and recompile it **once**.
3. If the editor crashes or the compile fails: stop. Nothing is saved until the check passes, and the git copy is the rollback.

#### P11-5b: regression (lead + owner)
A thumbnail comparison needs two recompiles (MCP_NOTES), which is an extra GPU risk. Instead, with every switch still off, the lead re-captures `cy_tall_north_15m`, `cy_west_front_15m`, `cl_lantern_bells_3m`, `ch_candle_altar_3m` and compares them with `p11_a2_`: mean absolute difference at most 2/255 per image.

**Result (`p11_r5_*`, `Tools/materials/compare_captures.py`): three views pass; `cl_lantern_bells_3m` is over the literal limit at 3.61/255. Accepted by the lead as not a material change, for the reasons below.**

The editor viewport had changed size between the two sets (1331x808 for `p11_a2_`, 1335x862 for `p11_r5_`, after the editor was reopened), so the comparison has to scale one image, and scaling alone creates a difference on sharp detail. The horizontal field of view is fixed, so `compare_captures.py` scales to the same width and centre-crops; the best scale from a search was 1.0000 of that, so the two sets line up.

| View | Real difference | Control: the old image scaled only, no new render | 16x downsampled (area brightness only) |
|---|---|---|---|
| `cy_tall_north_15m` | 1.42 | 2.17 | 0.39 |
| `cy_west_front_15m` | 1.73 | 2.33 | 0.52 |
| `cl_lantern_bells_3m` | **3.61** | 5.19 | 0.53 |
| `ch_candle_altar_3m` | 1.96 | 2.89 | 0.54 |

In every view the real difference is below what scaling alone creates, the area brightness difference of the failing view matches the passing ones, and its difference picture lights up only at edges and fine stone detail, with no surface shifted. It is the highest because it is a close-up full of sharp, strongly lit texture.

**The limit of this evidence:** no same-size comparison exists, because that would need the old master back. A small change hidden below the scaling noise can't be ruled out by these pictures. The static switch compiles only its False branch, so none is expected.

#### P11-5c: rollout and tuning (lead + owner)
**Floor check:** `WeatherFloorZ` stays 0. Every wall piece that gets the layer starts at or above Z -30 (census), and the courtyard, chapel, cloister and passage floors are at about 0. Upper tower pieces are above the band, so they get streaks and patches only.

**Parents (census):** `MI_Chapel_Masonry_Interior` and `MI_Env_TowerStone` inherit from `MI_Kit_Masonry`; `MI_Chapel_Trim_Dusty` and `MI_Cl_CarveDirt` from `MI_Kit_Trim`. `MI_Crypt_StoneWA` is directly on `M_LB_Surface` and `MI_Kit_Rubble` is on `MI_Rock_064`, so neither is reached.

1. **Technical-artist [EDITOR]:** `Tools/materials/set_weathering.py`, then in this order: `bWeathering` off on `MI_Cl_CarveDirt` first, so the memorial never gets the layer; on for `MI_Kit_Masonry`; on for `MI_Kit_Trim`. **Nothing is saved yet.** A GPU crash on the first render of the new shaders then falls back to the switches being off, instead of a project that compiles them again on every load.
2. **Lead + owner:** the 24 poses, prefix `p11_w1_`, with luma. The 15 m views should show no wallpaper repeat; streaks and the grime band should read as weather, with no hard edge across wall pieces. The memorial stays legible.
3. **Tuning, values only,** same value on `MI_Kit_Masonry` and `MI_Kit_Trim` so no edge forms where they meet: `GrimeBaseAmount` 0.2–0.6, `StreakAmount` 0.15–0.45, `PatchAmount` 0.1–0.5. Re-capture only what is needed to judge the change.
4. **Save** once the look is accepted: each changed MI alone, one package per `save_assets` call, `is_dirty` checked after each.
5. **GPU (owner, 1 minute):** one reading at the chapel mid-nave spot. Budget ≤ 16.6 ms; baseline 15.32 ms. If over: the P11-8 cut list, before any decal work.
6. **Suite** on the mirror, and report. P11-6 waits for the owner's "go".

**Look result (`p11_w1_*` at the master's defaults, all 24 poses; `p11_w2_*` at the chosen values, 6 poses):** the first render of the new shaders ran with no GPU crash and no shader error in the log.

| | `GrimeBaseAmount` | `StreakAmount` | `PatchAmount` | Result at normal exposure |
|---|---|---|---|---|
| Defaults | 0.45 | 0.30 | 0.30 | Clear in the altar corner, barely visible on the north wall and the passage wall |
| **Chosen** | **0.55** | **0.42** | **0.40** | Soft vertical streaks read on the north wall; no hard edges; memorial legible |

Measured on same-size captures, the defaults change whole images by 2 to 5 % against the switch off (`p11_r5_`), and the bottom third of the bells view by 15 %. The chosen values take a further 0 to 1.6 % off whole images. **Brightness:** the crypt reads about 5 % lower in the 24-pose table although this layer doesn't reach it, so most of that table's shift is the taller viewport framing, not the material. P11-8 has to re-read brightness at one viewport size before correcting it.

**Not judged yet:** only 6 poses were captured at the chosen values; the other 18 are covered by the full re-capture in P11-8. Nobody has judged this in play.

**Saved:** `MI_Cl_CarveDirt`, `MI_Kit_Masonry`, `MI_Kit_Trim`, one at a time. `M_LB_Surface` shows as modified in the editor after the switch change (189 expressions and 73 parameters, as committed) and was not saved. Its file on disk is unchanged.

### P11-6: decals
1. **Retune** (instance values only). D-046: leak decals were "too strong, hair-like". For each decal MI in the census, check one capture per area. Lower `Opacity` and adjust `Roughness` until it reads as a stain.
2. **Crack decals** (none exist; the CC0 sources have no suitable decal). Generate `T_LB_Decal_Crack_A/B/C` procedurally with a Python script in `Tools/materials/` (opacity, normal, 2K, seeded). Three MIs on `M_LB_Decal`. Registry rows ("own work").
3. **Placement:** at most 40 across the game, where a crack makes structural sense: above arch crowns, near the broken bays and the collapse, at wall bases. The lead writes the exact list here after P11-4, using the census and the final walls.
4. Never on a puzzle clue, numeral or the memorial tablet.

### P11-7: lantern glass (closes R-32)
1. New MI `/Game/LastBell/Materials/Instances/MI_LB_LanternGlass_Lit`, parent `M_LB_UnlitEmissive`. `Color` = (1.0, 0.549, 0.2196) × 2.0.
2. Set it as the mesh default for slot `wooden_lantern_01_glass` on `SM_Wooden_Lantern_01`.
3. **Check first:** the census list of lanterns. Any lantern with no light within 60 cm keeps today's glass, through an actor-level override.
4. **Tune** `Color` multiplier between 1 and 4: the glass reads as lit at 10 m and doesn't clip (max luma ≤ 0.95) in the courtyard (EV 1.15) or the cloister (EV 0.65).

### P11-8: close
1. **Brightness:** re-capture the 24 baseline poses, plus the Phase 10 target poses (D1.25). New stone changes luma, so correct it through MI `BrightnessMul`, **never by changing lights**. The Phase 8–10 targets still apply.
2. **QA** (qa-reviewer): suite 79/79, the placement and lighting checks of each area, log review, naming and folders, no parent Blueprint changed.
3. **Docs:** MCP_NOTES lessons, PERFORMANCE_BUDGET, ASSET_REGISTRY, RISKS, DECISIONS, IMPLEMENTATION_PLAN. Update `ART_DIRECTION.md` and `MODULAR_KIT.md` to drop the vertex-colour contract (architecture drift).
4. **Owner:** `stat gpu` at the same 6 spots, then a playtest. **If over budget**, the cuts in order:
   1. `bWeathering` off on trim and low-visibility MIs;
   2. one streak octave;
   3. fewer decals.
5. **"PHASE 11 READY FOR YOUR REVIEW".** Merge only on "approve and merge".

## Proposed log entries (added in P11-0, on approval)
- **D-085:** vertex-colour contract dropped in favour of a world-space weathering layer.
- **D-086:** the owner's joint choice, after P11-3.
- **R-46** (Art, M/H): a game-wide stone change moves the approved luma of every area. Mitigation: baseline captures, MI-only corrections, the P11-8 re-check.
- **R-47** (Tooling, L/H): the master-material recompile can crash the GPU on the 6 GB card. Mitigation: one recompile, other GPU apps closed, saved work first.

## Out of scope
- New meshes, layout or lighting changes (other than what the owner's choice in P11-3 requires).
- The Warden's materials (Phases 12–13).
- Rain, storm wetness and foliage wind (Phases 14–15; see the Deferred section of `IMPLEMENTATION_PLAN.md`).
- The Phase 9 dress bounds mismatches (118), a tooling item.
- The chapel main and sacristy door corners and the `Gobo_Moon` specks, unless the owner adds them.

## What the owner is asked to do
1. Approve this plan.
2. GPU baseline, about 10 minutes (P11-1).
3. Keep Unreal in front during capture runs (P11-2, P11-3, P11-8).
4. Choose the wall look from the comparison sheet (P11-3).
5. Possibly one bulk Reimport, only if A wins (P11-4).
6. Final GPU check and playtest (P11-8).
