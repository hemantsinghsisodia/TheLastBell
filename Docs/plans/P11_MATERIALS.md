# Phase 11: Materials (surface polish): plan

**Status:** approved by the owner on 2026-11-02. P11-0, P11-1 and P11-2 done; P11-3 done: the owner chose A (D-086). P11-0 to P11-7 done (suite 79/79); P11-8 in progress. The door corners and `Gobo_Moon` specks stay out of scope.
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

**GPU reading (owner, 2026-11-03, chapel mid-nave, High, Warden off): 15.00 ms** (graphics queue 14.80 avg, 15.73 max), against 15.32 ms at baseline and a budget of 16.6 ms. Within budget, so no cuts are needed before the decals.

**This isn't a measurement of the layer's cost.** The two readings aren't framed alike: 372.5K primitives now, 422.3K then, and render 1671x870 against 1664x846 (the editor window changed). `Nanite BasePass` and `Basepass`, where the layer's shader cost would land, read 1.15 and 0.89 now, 1.22 and 0.97 then. The P11-8 reading at all six spots is the real close of R-44.

**Game thread:** 14.84 ms now, 11.38 ms at baseline, with `Frame` at 16.75 ms against the 16.67 ms cap. A material change can't cost game-thread time, so this isn't from the layer, and it isn't explained yet. Check it again in the P11-8 readings.

### P11-6: decals

**Status: done 2026-11-03 (D-087). Written from 26 captures of the current decals (`p11_dc0_*`). Results in Step 3.**

#### What the captures and the data showed
| Decal | Finding | Cause | Fix |
|---|---|---|---|
| `Decal_Leak_N0..2, S0, S1, E0` (`MI_Decal_Leaking006_Wall`, courtyard) | Dark hair hanging in the middle of a wall, with a hard flat edge. **This is the D-046 "hair".** | **The actors have roll 0, not roll 90** (MCP_NOTES: this decal needs roll 90). The 512x2048 texture lies on its side and is squeezed, so its texels stretch into strands. The stain also starts mid-wall with no source. | Roll 90, new size, move up under the coping, softer values |
| `MI_Decal_Leaking004_Wall` (crypt 9, cloister 3) | Thin black vertical bars at close range | `OpacityStrength` 1.6 and `OpacityContrast` 1.5 clip the strands to solid. The texture's top border has mean alpha 0.41, so the top edge is hard. | Softer values, more edge fade |
| `MI_Chapel_DampStreak` (7) | Black, with jagged hair-like fringes against the lit reveal of the broken lancet | Inherits 1.6 and 1.5 | Softer values, more edge fade |
| `MI_Decal_Soot_A/_B` (13) | A dark bar ending in a hard square bottom edge: a sticker | **In the texture.** The plume is densest at its bottom edge and never fades (bottom border mean alpha 0.13 and 0.16). No value on `M_LB_Decal_Grime` can hide that, because it has no edge fade. | Fade the bottom in the generator, new textures, slightly lower `Opacity` |
| `MI_Decal_DustDrift` (12), `MI_Sa_Decal_DustDrift_Strong` (2) | Reads as earth, not hair, but heavy on the clean paving | Strength only | Lower `Opacity` |
| `MI_Decal_Mould` (33) | Soft band; every wall decal's bottom edge is on the floor (checked from the census) | None | No change |
| `WaterStain`, `WaxDrips`, `LeafLitter_A/B`, `DragMarks`, `MI_Sa_Decal_WaterStain_Strong`, `MI_Sa_Decal_WaxDrips_Strong` | Read as intended where they can be seen | None | No change |
| Chalk, `MI_Decal_LightPool_Lancet` | Puzzle clue; light | Out of scope | Never touch |

So the retune isn't "instance values only" as first planned: six actors and two textures change too, because values can't fix a rotated texture or a hard edge inside a texture. `cl_mould`, `cr_mould`, `cr_leaking004_wall` and `ch_chapel_dampstreak` are close to black in their views, so those four are judged with lifted views as well.

#### Step 1: textures, no editor (technical-artist)
**1a. Crack generator: new file `Tools/materials/gen_crack_textures.py`.** numpy and PIL only (no scipy), every random number from `numpy.random.default_rng(seed)`, the same result on every run.

`python -I Tools/materials/gen_crack_textures.py [--out ExternalAssets/Generated/materials] [--preview Docs/ArtTest/materials]`

| Set | Size (W x H) | Seed | Shape | Main stem | Branches `k` | `step` |
|---|---|---|---|---|---|---|
| A | 2048 x 2048 | 11101 | Long diagonal stepped crack | from (0.16, 0.10) toward (0.84, 0.90); 18 px at the start, 2 px at the end | 6 | 0.30 |
| B | 1024 x 2048 | 11102 | Vertical crack rising from an arch crown, **thickest at the bottom** | from (0.50, 0.97) toward (0.50 ± 0.12, 0.06); 20 px to 2 px | 5 | 0.12 |
| C | 2048 x 2048 | 11103 | Short fork | from (0.50, 0.93) straight up for 55 % of the height, 16 px to 6 px, then two prongs at ± 28–40° from it, each 35 % of the height, 6 px to 2 px | 3 | 0 |

Coordinates are (u, v), v down. Draw on a 2x canvas (`Image` mode `L`) and reduce to final size with `Image.LANCZOS`. Pixel widths are final-size pixels.

**The look that matters: a crack is angular, and hair is smooth.** Never smooth, spline or blur the path.
- **Walker.** Each segment's length is uniform 22–60 px. Its heading is the direction to the target (or the start heading, if there's no target) plus an independent uniform offset of ± 28°. Offsets don't accumulate, so the line zig-zags without curling.
- **Steps.** With probability `step`, a segment's heading is forced to horizontal ± 8° and its length is multiplied by 1.5, as if the crack ran along a bed joint for a moment.
- **Width.** `w(s) = (w0 + (w1 - w0) * s ** 0.8) * uniform(0.75, 1.25)` per segment, s = fraction along the line. Each segment is a filled trapezoid, with a filled circle at each joint.
- **Branches.** `k` stations uniform in s 0.15–0.85, at least 0.12 apart. Heading = local heading ± uniform(25, 55)°, sign random. Length uniform(0.15, 0.35) x main length. `w0` = 0.5 x `w(s)`, `w1` = 1.5 px. Offset ± 22° on branches. A branch longer than 0.22 x main gets one sub-branch: 0.35 x its length, `w0` = half the branch's width there.
- **Hairlines.** 6–10 extra twigs on stem or branches, 30–90 px, width 1.5 to 1 px, drawn at value 0.6.
- **Chips.** Along the main stem only, every uniform(120, 260) px: a polygon of 4–6 vertices, radius 4–14 px, on one side of the stem, drawn at value 0.7. These break the edge.

Maps at final size (`core` = the drawing, 0–1):
- `bleed = GaussianBlur(core, 14 px) * (0.45 + 0.9 * fbm)`, cell 90 px, 3 octaves.
- `opacity = max(core, 0.22 * clip(bleed, 0, 1))`, multiplied by a border fade of `smoothstep(0, 0.03, min(u, 1 - u))` and the same for v.
- `h = -GaussianBlur(core, 1.5 px) + 0.25 * GaussianBlur(core, 6 px)`.
- Normal, DirectX convention (+Y down the image, as `T_Leaking006_N`): `n = normalize(-dh/dx * K, -dh/dy * K, 1)`, K = 6, written as `n * 0.5 + 0.5`. Multiply `h` by the same border fade first, so the map is flat at the edges.

Writes `T_LB_Decal_Crack_{A,B,C}_Opacity.png` (8-bit `L`) and `T_LB_Decal_Crack_{A,B,C}_N.png` (RGB). Previews `Docs/ArtTest/materials/p11_crack_tex_{a,b,c}.png`, 1024 px on the long side: the crack (near-black, by opacity) over a mid-grey stone-like fbm, normal-lit from the upper left.

Checks the script prints and enforces (exit 1 on failure): fraction of pixels with opacity > 0.5 is 0.3–2.5 %; the outer 3 % band has max opacity < 0.01; flat normal at the border; two runs give the same MD5 (run it twice and compare).

**1b. Soot.** In `soot_texture()` of `Tools/textures/gen_chapel_textures.py`, after the line that applies `(1 - smoothstep(0.80, 1.0, t))`, add `a = a * smoothstep(0.0, 0.10, t)`. It uses no random numbers, so nothing else in the texture shifts. In `GRIME`, rename the two entries to `T_LB_Decal_SootSoft_A` and `T_LB_Decal_SootSoft_B` (same seeds and arguments). Run `--only` for those two. Check: bottom 4 rows mean alpha < 0.005; MD5 of every other PNG in `ExternalAssets/Generated/chapel/` unchanged.

**Stop here and report.** The lead looks at the previews before anything goes into the editor.

**Step 1 result (2026-11-03; commits b52928f, 79df30b).** The generator is the record; it differs from the text above in these ways. The first pass read as marker lines, and C as a sapling.
- Every stem's width is multiplied by `smoothstep(0, 0.10, s)`, floor 1.5 px, so the thick end has no round stub.
- Edges are roughened at final size: `core = smoothstep(0.38, 0.62, blur(raw, 1.2) + 1.2 * (fbm(cell 14) - 0.5) * clip(blur * 3, 0, 1))`. Thin branches break into dashes. The amplitude was first set at 0.30 and moved the edge by only about 0.15 px.
- Chips sit on the stem's edge, value 1.0, radius 5–16 px, spacing 160–320 px, stretched along the stem, none in the first 10 %.
- Branches: length 0.10–0.24 x main, ± 35–70° off the local heading, alternating sides, wander ± 34°.
- C has no fork: an oblique crack from (0.32, 0.90) toward (0.66, 0.10), 14 px to 2 px, wander ± 32°, `step` 0.18, `k` 3.
- B starts at v 0.94, not 0.97, because strokes stay inside a 0.055 inset so the border check can pass. No steps in the last 10 % of a stem.
- Coverage: A 0.90 %, B 1.27 %, C 0.53 %. Border checks pass, and two runs give the same MD5s. Soot: bottom 4 rows mean alpha 0.00013 and 0.00016 (were 0.133 and 0.164); the other PNGs are unchanged.

Lead review of `p11_crack_tex_{a,b,c,small}.png`: all three read as cracks at full size and at 256 px. Small crossings remain (C's closed triangle, a knot in A). They look like the islands real cracks form, so they stay unless they look wrong on a wall. These were judged on a fake stone, so the real test is Step 3.

#### Step 2: editor (technical-artist) [EDITOR]
New script `Tools/materials/apply_p11_decals.py`, in the style of `set_weathering.py`: `--snapshot FILE` (before-values of everything it changes), `--textures`, `--mis`, `--leaks`, `--cracks`, `--check` (read back everything; exit 1 on a mismatch), `--save`. Refuses to run while PIE runs (`IsPIERunning`). Idempotent by asset name and actor label. Spawn decals as `Tools/crypt/place_crypt.py` `place_decal` does (`add_to_scene_from_class` DecalActor, `set_actor_transform`, `set_label`, `set_actor_folder`, `NewDecalComponent`).

**Snapshot first:** `Docs/ArtTest/materials/p11_6_before.json`.

**Textures** (`--textures`, `TextureTools.import_file`):
| Assets | Folder | Copy compression, sRGB, LOD group, address, virtual-texture and size settings from |
|---|---|---|
| `T_LB_Decal_Crack_{A,B,C}_Opacity` | `/Game/LastBell/Materials/Textures/` | `/Game/LastBell/ArtTest/Decals/Leaking006/T_Leaking006_Opacity` |
| `T_LB_Decal_Crack_{A,B,C}_N` | same | `/Game/LastBell/ArtTest/Decals/Leaking006/T_Leaking006_N` |
| `T_LB_Decal_SootSoft_A`, `_B` | `/Game/LastBell/Environments/Chapel/Textures/` | `/Game/LastBell/Environments/Chapel/Textures/T_LB_Decal_Soot_A` |

These are new assets, so nothing overwrites an existing texture. `T_LB_Decal_Soot_A/_B` stay in place, unreferenced; clean-up is decided at phase end.

**New MIs** (`--mis`), `/Game/LastBell/Materials/Instances/MI_Decal_Crack_{A,B,C}`, parent `/Game/LastBell/Materials/Master/M_LB_Decal`, all with explicit overrides:
| Parameter | Value |
|---|---|
| `OpacityTex`, `NormalTex` | the set's two textures |
| `BaseColorTint` | (0.030, 0.027, 0.024, 1) |
| `OpacityStrength`, `OpacityContrast`, `NormalStrength` | 1.0, 1.0, 1.0 |
| `RoughnessScale`, `DarkenStrength`, `DepthFade` | 0.9, 0.35, 0.3 |
| `EdgeFadeU`, `EdgeFadeV` | 0.03, 0.03 |
| `DecalHalfDepthCm` | 12 |

`BaseColorTex` and `RoughnessTex` stay at the master's white defaults.

**Retune** (`--mis`; set each as an explicit override, read each back):
| MI | Parameter: old → new |
|---|---|
| `Environments/Courtyard/Materials/MI_Decal_Leaking006_Wall` | `OpacityStrength` 1.6 → 0.85; `OpacityContrast` 1.5 → 1.1; `DarkenStrength` 0.3 → 0.2; `EdgeFadeU` 0.12 → 0.22; `EdgeFadeV` 0.06 → 0.14 |
| `Environments/Crypt/Materials/MI_Decal_Leaking004_Wall` | `OpacityStrength` 1.6 → 0.75; `OpacityContrast` 1.5 → 1.0; `DarkenStrength` 0.3 → 0.2; `EdgeFadeU` 0.12 → 0.22; `EdgeFadeV` 0.06 → 0.16 |
| `Environments/Chapel/Materials/MI_Chapel_DampStreak` | `OpacityStrength` 1.6 → 0.6; `OpacityContrast` 1.5 → 1.0; `DarkenStrength` 0.3 → 0.18; `EdgeFadeU` 0.12 → 0.25; `EdgeFadeV` 0.06 → 0.14. `RoughnessScale` and the tint stay |
| `Materials/Instances/MI_Decal_Soot_A`, `MI_Decal_Soot_B` | `GrimeTex` → `T_LB_Decal_SootSoft_A`, `_B`; `Opacity` 1 → 0.8 |
| `Materials/Instances/MI_Decal_DustDrift` | `Opacity` 1 → 0.75 |
| `Environments/Chapel/Materials/MI_Sa_Decal_DustDrift_Strong` | `Opacity` 2 → 1.4 |

`MI_Chapel_DampStreak` is a child of `MI_Decal_Leaking006_Wall`, so set its overrides explicitly and check them after the parent's change. `MI_Leaking006` (ArtTest parent) doesn't change.

**The six courtyard leaks** (`--leaks`): same X and Y and yaw as now. Rotation (0, yaw, **90**), `decalSize` (12, 200, 50), Z **600**. The wall was traced at these spots: it's there at Z 400, 600 and 790 and gone by 830, so the stain starts under the coping. Pass location, rotation and scale to `set_actor_transform`.

**37 crack decals** (39 in round 1; see Step 3) (`--cracks`) from `Tools/materials/p11_crack_decals.json`, unchanged, as `DecalActor`, folder `Dressing/Decals/Cracks`, `sortOrder` 1 so they draw over stains, `fadeScreenSize` left at its default. No collision change. The table below is that file.

**Never:** a crack within 2 m of a clue, numeral or tablet (`make_crack_placements.py` enforces this and the no-go walls: chapel north wall X 8000–9000, cloister bell wall Y 1950–2800, crypt lever wall X 10600–11200). A label not in the file. Any change to `MI_Decal_Mould`, chalk or light-pool MIs.

**Save** (`--save`, one package per `save_assets`, 5 s apart): the 8 textures, 3 new MIs, the 6 retuned MIs and then `L_Monastery`. `M_LB_Surface` shows dirty and **must never be saved**. If anything else is dirty, report it and don't save it.

**Then:** `--check`; Output Log clean; suite (79/79); registry rows (crack textures "own work", `Tools/materials/gen_crack_textures.py`, seeds 11101–11103; the soot row gains the two SootSoft names); commit to the current branch only. **No captures:** those need the owner at the PC.

#### Step 3: review (lead, with the owner at the PC)
1. `capture_session.py Tools/materials/poses/p11_crack_poses.json Docs/ArtTest/materials --prefix p11_ck1_ --mode editor`: all 39, fast, to check placement. The entries marked "check in capture" (gate, south archway, two cloister arcade arches, all six crypt) have no trace behind them, so a miss shows here.
2. `capture_session.py Tools/materials/poses/p11_decal_poses.json Docs/ArtTest/materials --prefix p11_dc1_ --mode simulate`: the same 26 views as `p11_dc0_`, side by side.
3. **Pass:** each decal reads as a stain or crack from play distance: no hard rectangle edge, no strands, no crack on a clue. A crack that reads as a hair or a scratch fails. Tune within: leak `OpacityStrength` 0.5–1.1, soot `Opacity` 0.6–1.0; cracks `OpacityStrength` 0.7–1.0, `NormalStrength` 0.5–1.5. A crack still wrong after one round is deleted from the list, not forced.
4. Suite again, save only what changed, commit, close D-046, report, and ask for "go" before P11-7.

GPU: 126 decals become 165. Decals cost by screen area, and these are small. The P11-8 reading at six spots covers it; "fewer decals" is already the third cut.

#### Step 3, first round (lead, 2026-11-03; `p11_ck1_*`, `p11_dc1_*`)
**Step 2 went in as specified** (commit 9a38399; `--check` 65/65, suite 79/79). All 26 decal views were compared before and after, lifted the same amount.

| Decal | Result |
|---|---|
| Courtyard leaks | **Pass.** They now run down from under the coping as rain stains. No strands, no hard edge. This was the D-046 hair |
| Soot | **Pass.** The square bottom edge is gone, and a soft plume remains |
| Damp streaks | **Pass.** Soft, no black hair |
| `Leaking004`, dust | **Pass.** Softer, still read as stains |
| Others (no change) | Same as before, as expected |
| Large cracks (half-size ≥ 120) | **Pass.** `tw_n_mid`, `co_frontcrown`, `co_walln_05`, `co_walls_03` and `tw_sw_a` read as real structural cracks |
| Small cracks (half-size ≤ 70) | **Fail.** Hard to see or invisible. At these sizes the lines are under a centimetre wide and fade in the mips. `ch_s_base` and `ch_doorcrown` did land on the wall; they're just too thin |
| `Crack_Cl_ArcN_Crown`, `Crack_Cl_ArcS_Crown` | **Fail.** Completely behind the ivy |

**Not yet verifiable:** the crypt group and the arcade and gate crowns. Editor-mode shots show each decal's icon over its centre, and much of the crypt is black without the player's light.

**The jagged black fringe on the lit reveal of the broken lancet isn't a decal.** It's the same shape before and after the damp streak changed. It's left alone here; it stays out of scope unless the owner adds it.

**Changes for round 2** (the list below already includes them):
- Small cracks get bigger, not bolder only: wall bases half-size 90 at Z 95 (the box stops 5 cm above the floor, so nothing projects on the floor); arcade crowns 85; broken-bay stubs 130, with the plane taken from the bounds because the opening beside them can't be probed; door crown 90; gate 110 x 55; `Crack_Cr_NC_N` 100, moved 150 cm along the wall, off the torch.
- The two ivy-covered cracks are deleted: **37 cracks**, not 39.
- `MI_Decal_Crack_A` `OpacityStrength` 1.0 → 1.2; `MI_Decal_Crack_C` 1.0 → 1.5; B stays 1.0. Tune cracks within 0.7–1.8 from here. No re-import: the textures don't change.
- Review poses stand further back, so the steep arcade views become what a player sees from the garth.

Round 2 captures use PIE Simulate (no icons) for the entries that couldn't be judged: `co_arcn_crown, co_arcs_crown, co_arcn_brokena, co_arcn_brokenb, co_arcs_brokena, co_arcs_brokenb, co_gatecrown, cl_archs_crown, cr_cc_s, cr_fp_s, cr_fp_n, cr_sc_s, cr_wc_w, cr_nc_n, ch_e_base, ch_s_base, ch_doorcrown, sa_e_base, tw_e_base`.

#### Step 3, second round and close (lead, 2026-11-03; `p11_ck2_*`, 19 views, PIE Simulate)
Round 2 went in as listed (commit 569e991; `--check` 63/63, suite 79/79). Only `M_LB_Surface` is dirty, and it stays unsaved.

| Cracks | Result |
|---|---|
| Broken-bay stubs (`co_arcn_brokena`, `co_arcs_brokena` looked at closely) | **Pass.** The crack runs through the band and arch ring and reads as a real fracture, subtle from the garth |
| `ch_s_base`, `ch_doorcrown` | **Pass.** They rise from the plinth and the door like real cracks |
| `cr_nc_n` | **Pass.** It lands on the stones, so the crypt's "same plane as an existing decal" method works |
| `co_arcn_crown`, `co_gatecrown` | No fault, but too faint to see at this distance. Harmless; they may only read up close |
| `cr_cc_s`, `cr_fp_s` | **Not sure.** The stones are deeply carved and have dark slashes of their own, so I can't tell the crack from them here |
| `cr_sc_s`, `cr_wc_w`, `cr_fp_n`, `sa_e_base`, `tw_e_base` | **Not verified.** These walls are black without the player's light (mean luma 0 to 9 of 255) |

**Exit condition "decals read as stains and cracks, not stickers or hair": met in every view that can be seen.** Nothing in these captures reads as a sticker or hair, and no crack is near a clue (enforced by `make_crack_placements.py`: 2 m from every clue, numeral and tablet, plus the no-go walls). **Still needs the owner's playtest:** the five dark views above and the two unsure ones, with the player's light.

Left over, for phase end: `T_LB_Decal_Soot_A/_B` are unreferenced. Lessons for MCP_NOTES in P11-8: editor-mode captures draw each decal's icon over its centre, so use PIE Simulate to judge decals; small decals lose thin lines in the mips, so scale the decal rather than only raising opacity; `T_Leaking004` and `T_Leaking006` need roll 90 like every wall decal.

#### Crack list
| Label | MI | Location | Rotation (P, Y, R) | DecalSize | Where |
|---|---|---|---|---|---|
| `Crack_Co_ArcN_Crown` | C | 2500, 922, 615 | 0, 90, 90 | 12, 85, 85 | crown of the intact north bay, garth side |
| `Crack_Co_ArcS_Crown` | C | 4500, -922, 615 | 0, -90, 270 | 12, 85, 85 | crown of the intact south bay, garth side |
| `Crack_Co_ArcN_BrokenA` | A | 3170, 920, 565 | 0, 90, 90 | 12, 130, 130 | standing stub of the north bay 3000 (check in capture) |
| `Crack_Co_ArcN_BrokenB` | A | 4830, 920, 565 | 0, 90, 270 | 12, 130, 130 | standing stub of the north bay 4000 (check in capture) |
| `Crack_Co_ArcS_BrokenA` | A | 2170, -920, 565 | 0, -90, 75 | 12, 130, 130 | standing stub of the south bay 2000 (check in capture) |
| `Crack_Co_ArcS_BrokenB` | A | 3830, -920, 565 | 0, -90, 255 | 12, 130, 130 | standing stub of the south bay 3000 (check in capture) |
| `Crack_Co_WallN_05` | B | 2200, 2500, 400 | 0, 90, 90 | 12, 240, 120 | curtain wall west of the broken panel N_05 |
| `Crack_Co_WallN_10` | A | 4840, 2500, 430 | 0, 90, 110 | 12, 170, 170 | curtain wall east of the broken panel N_10 |
| `Crack_Co_WallS_03` | A | 2020, -2500, 430 | 0, -90, 75 | 12, 170, 170 | curtain wall east of the broken panel S_03 |
| `Crack_Co_WallS_08` | B | 3410, -2500, 400 | 0, -90, 90 | 12, 240, 120 | curtain wall west of the broken panel S_08 |
| `Crack_Co_GateCrown` | B | 300, 0, 690 | 0, 180, 90 | 12, 110, 55 | crown of the gate arch, courtyard side (check in capture) |
| `Crack_Co_FrontCrown` | B | 6000, 0, 490 | 0, 0, 90 | 12, 120, 60 | above the chapel door, outside |
| `Crack_Ch_S_HoleW` | A | 6210, -750, 620 | 0, -90, 80 | 12, 150, 150 | west of the broken lancet |
| `Crack_Ch_S_HoleE` | B | 6800, -750, 500 | 0, -90, 90 | 12, 210, 105 | east of the broken lancet |
| `Crack_Ch_DoorCrown` | C | 6060, -0, 470 | 0, 180, 90 | 12, 90, 90 | above the main door, inside |
| `Crack_Ch_N_Base` | C | 7000, 750, 95 | 0, 90, 270 | 12, 90, 90 | base of the north wall |
| `Crack_Ch_S_Base` | C | 8000, -750, 95 | 0, -90, 90 | 12, 90, 90 | base of the south wall |
| `Crack_Ch_E_Base` | C | 8960, -640, 95 | 0, 0, 90 | 12, 90, 90 | base of the east wall, south corner |
| `Crack_Ch_N_High` | A | 7000, 750, 830 | 0, 90, 100 | 12, 170, 170 | high on the north wall between the soot marks |
| `Crack_Sa_E_Base` | C | 8960, -1200, 95 | 0, 0, 270 | 12, 90, 90 | base of the sacristy east wall |
| `Crack_Cl_N_CollapseW` | A | 10640, 3000, 430 | 0, 90, 80 | 12, 170, 170 | north wall west of the vault collapse |
| `Crack_Cl_N_CollapseE` | B | 11260, 3000, 400 | 0, 90, 90 | 12, 230, 115 | north wall east of the vault collapse |
| `Crack_Cl_N_Base` | C | 10150, 3000, 95 | 0, 90, 90 | 12, 90, 90 | base of the north wall |
| `Crack_Cl_W_Base` | C | 9500, 1000, 95 | 0, 180, 270 | 12, 90, 90 | base of the west wall |
| `Crack_Cl_ArchW_Crown` | B | 9500, 2000, 560 | 0, 180, 90 | 12, 120, 60 | crown of the west archway, inside |
| `Crack_Cl_ArchS_Crown` | B | 10650, 546, 455 | 0, -90, 90 | 12, 120, 60 | crown of the south archway, inside (check in capture) |
| `Crack_Cr_WC_W` | A | 6300, -1750, -400 | 0, 180, 80 | 12, 120, 120 | west corridor, west wall (check in capture) |
| `Crack_Cr_SC_S` | A | 6900, -2500, -400 | 0, -90, 255 | 12, 120, 120 | south corridor, south wall (check in capture) |
| `Crack_Cr_FP_S` | B | 9360, -2460, -400 | 0, -90, 90 | 12, 170, 85 | flooded pit, south wall between the leaks (check in capture) |
| `Crack_Cr_FP_N` | A | 9625, -2100, -400 | 0, 90, 100 | 12, 110, 110 | flooded pit, north wall between the leaks (check in capture) |
| `Crack_Cr_CC_S` | A | 10700, -2500, -400 | 0, -90, 80 | 12, 130, 130 | winch chamber, south wall (check in capture) |
| `Crack_Cr_NC_N` | C | 11300, -700, -420 | 0, 90, 90 | 12, 100, 100 | north chamber, north wall (check in capture) |
| `Crack_Tw_SW_A` | A | 12300, 1540, 2900 | 0, -90, 80 | 12, 170, 170 | south wall beside the broken corner |
| `Crack_Tw_SW_B` | B | 12040, 1800, 2900 | 0, 180, 90 | 12, 230, 115 | west wall beside the broken corner |
| `Crack_Tw_E_Base` | C | 12960, 2000, 95 | 0, 0, 90 | 12, 90, 90 | base of the east wall |
| `Crack_Tw_E_Mid` | A | 12960, 2200, 850 | 0, 0, 100 | 12, 150, 150 | east wall, lower stair |
| `Crack_Tw_N_Mid` | B | 12500, 2460, 1550 | 0, 90, 270 | 12, 200, 100 | north wall, upper stair |

### P11-7: lantern glass (closes R-32)

**Checked (lead, 2026-11-03):**
- 18 lanterns, all `StaticMeshActor`s on `SM_Wooden_Lantern_01`. None overrides the glass slot, and no Blueprint component uses this mesh. Each has a light within 17 cm, so **no lantern needs an override** (step 3 of the first plan falls away).
- The mesh has two slots, `wooden_lantern_01` and `wooden_lantern_01_glass`. The glass slot's default is `MI_Wooden_Lantern_01_Glass`, on `M_LB_Surface`, which has no emissive.
- **The mesh isn't Nanite**, and `M_LB_UnlitEmissive` isn't flagged for Nanite (opaque, unlit, two-sided, one parameter `Color`). So this needs no master recompile. If anything asks to recompile `M_LB_UnlitEmissive`, stop and report it.

#### Step 1: editor (technical-artist) [EDITOR]
New script `Tools/materials/apply_p11_lantern.py`, same style as `apply_p11_decals.py`: `--snapshot FILE`, `--apply`, `--multiplier M`, `--check`, `--save`, `--restore`. Refuses to run while PIE runs.

1. `--snapshot Docs/ArtTest/materials/p11_7_before.json`: the glass slot's material, the mesh's slots, `get_bounds`, Nanite state, and its collision (read how `check_reimport.py` does this).
2. `--apply`:
   - Create `/Game/LastBell/Materials/Instances/MI_LB_LanternGlass_Lit`, parent `/Game/LastBell/Materials/Master/M_LB_UnlitEmissive`.
   - `Color` = (1.0, 0.549, 0.2196, 1) x **2.0** = (2.0, 1.098, 0.4392, 1). The base hue is the lanterns' light colour (255, 140, 56).
   - `StaticMeshTools.set_material {mesh, slot_name: "wooden_lantern_01_glass", material}` on `/Game/LastBell/ArtTest/Props/Wooden_Lantern_01/SM_Wooden_Lantern_01`. **Only that slot.**
3. `--multiplier M`: sets `Color` to base x M, 1 ≤ M ≤ 4; refuses anything else.
4. `--check`: MI parent and `Color`; glass slot = the new MI; the other slot still `MI_Wooden_Lantern_01`; slots, bounds, Nanite and collision match the snapshot; all 18 census actors have no override on the glass slot.
5. `--restore`: puts `MI_Wooden_Lantern_01_Glass` back on the slot. Written and read, but only run if the lead asks.

**Save** (`--save`, one package per `save_assets`, 5 s apart): the MI, then `SM_Wooden_Lantern_01`. `L_Monastery` shouldn't be dirty; if it is, report it and don't save it. `M_LB_Surface` stays unsaved. Don't reimport the mesh; `MI_Wooden_Lantern_01_Glass` stays on disk.

**Then:** `--check`, Output Log clean, suite (79/79), registry unchanged (no new external asset), commit to the current branch. **No captures.**

#### Step 2: review (lead, with the owner at the PC)
`capture_session.py Tools/materials/poses/p11_lantern_poses.json Docs/ArtTest/materials --prefix p11_lg1_ --mode simulate`, then `lantern_report.py p11_lg1_`.

The poses look straight at the glass from about 10 m where the line of sight allows (`co_chapeldoor`, `co_gate`, `co_route1`, `co_garden`, `cl_bells`, `ps_lantern`), closer in the west cloister (7 m) and tower (5 m), and at 3 m and closer for the shape. The courtyard exposure is EV 1.15 and the cloister's 0.65.

**Pass:**
- at 10 m the glass reads as a small lit source, in courtyard and cloister alike, and not as a dark box beside a light;
- maximum luma in the window ≤ 0.95 in every view (`lantern_report.py`), so it doesn't clip to white and keeps its colour;
- at 3 m the frame and glass read as separate parts, and it reads as glass with a flame's glow behind it, not as an orange plastic block.

**Tune** `--multiplier` between 1 and 4 by the result. Over the limit: lower it. Doesn't read at 10 m: raise it. **At most two rounds.** If one multiplier can't satisfy both the courtyard and the cloister (they differ by 0.5 EV), prefer no clipping, and report it. Never change a light for this.

The glass is a flat, constant glow, while the lights behind it flicker. Making the glass flicker too would be new work for Phase 15's VFX pass, so it's noted here rather than done.

#### Result (lead, 2026-11-03; commits 660212c, a5ca0f3; `p11_lg1_*`, `p11_lg2_*`)
**Final value: `Color` = (1.7, 0.765, 0.17), which is base (1.0, 0.45, 0.10) x 1.7.** This isn't the plan's hue:

| Round | `Color` | Glass, sRGB (`cl_bells_3m`) | Reading |
|---|---|---|---|
| 1 | (2.0, 1.098, 0.4392), the lights' hue x 2 | (246, 230, 199) | Reads as lit at 10 m, but as a pale flat panel |
| 2 | (1.7, 0.765, 0.17) | (248, 222, 146) | Warm gold; still stands out from the wall its light brightens |

Lowering the multiplier alone wasn't an option: the wall behind each lantern is lit nearly as bright, so a dimmer pane would stop reading as the source. The tonemapper desaturates bright colours, so the base hue has to be more saturated than the light's.

**Checks:**
- Maximum luma on the glass is 0.81–0.90 in the 10 views whose centre shows lit glass (limit 0.95), and nothing clips. At first `lantern_report.py` read a wider window and reported 7 views over the limit; those peaks came from the lit wall, not the glass (they didn't change between rounds). It now reads the glass only.
- `co_route1` is partly hidden by a column, so its centre pixels aren't a clean glass reading. The crops show its glass is fine.
- Courtyard (EV 1.15) and cloister (EV 0.65) both read well with the one value.
- Suite 79/79 on the final value; `--check` 9/9. Only `M_LB_Surface` is dirty, and it stays unsaved.

**Not verified:**
- **`tw_base_3m` shows no lantern.** Both tower camera positions came out black, probably inside the stair mesh, which has no collision for the trace to catch. The tower's 5 lanterns share this mesh and MI, so they have the same glass, but nobody has looked at one. The P11-8 tower captures and the owner's playtest cover it.
- `co_gate_close` failed its capture 3 times and is missing; `co_gate_3m` shows the same lantern.
- At 3 m the pane is still a flat colour, because the master has no gradient input. It reads as a lit pane of horn or oiled paper rather than as clear glass. Nobody has judged it in play.

**R-32 closed.**

### P11-8: close

**Plan as approved:**
1. **Brightness:** re-capture the 24 baseline poses, plus the Phase 10 target poses (D1.25). New stone changes luma, so correct it through MI `BrightnessMul`, **never by changing lights**. The Phase 8–10 targets still apply.
2. **QA** (qa-reviewer): suite 79/79, the placement and lighting checks of each area, log review, naming and folders, no parent Blueprint changed.
3. **Docs:** MCP_NOTES lessons, PERFORMANCE_BUDGET, ASSET_REGISTRY, RISKS, DECISIONS, IMPLEMENTATION_PLAN. Update `ART_DIRECTION.md` and `MODULAR_KIT.md` to drop the vertex-colour contract (architecture drift).
4. **Owner:** `stat gpu` at the same 6 spots, then a playtest. **If over budget**, the cuts in order:
   1. `bWeathering` off on trim and low-visibility MIs;
   2. one streak octave;
   3. fewer decals.
5. **"PHASE 11 READY FOR YOUR REVIEW".** Merge only on "approve and merge".

`sg.*` = 2 (High), `sg.ResolutionQuality` 87, Warden on. The viewport is 1331x808, the same as the baseline set, so this comparison is same-size.

#### Step 1 result: brightness (lead, 2026-11-03; `p11_f1_*` 24 views, `p11_t1_*` 33 views; `Tools/materials/brightness_report_p11.py`, written to `p11_8_brightness.md`)
**Against the Phase 11 baseline** (final mean / baseline mean): lowest 0.86, median 0.95, highest 1.01.

| Area | Ratio | Main stone MI |
|---|---|---|
| Crypt | 0.97–1.01 | not changed by this phase |
| Chapel | 0.90–0.98, median 0.96 | `MI_Chapel_Masonry_Interior` |
| Courtyard | 0.88–0.97 | `MI_Kit_Masonry` |
| Cloister, passage | 0.87–0.93 | `MI_Kit_Masonry` |
| Tower | 0.86, 0.94 | `MI_Env_TowerStone` |

**Against the earlier phases' targets: 11 numbers miss. None comes from this phase.** Each was checked against the Phase 11 baseline or older captures:

| View | Reading | Why it isn't Phase 11 |
|---|---|---|
| `t8_entrance`, `t8_midnave` | mean 0.20, 0.21 against 0.04–0.08; dark fraction 0.150, 0.065 against ≥ 0.15 | They were 0.10 on 2026-10-28. The chapel views measured by the baseline moved only 0.96–0.98, so the nave's fog already read this bright when Phase 11 began. Nobody has checked when it changed. **Flagged for the owner's playtest** |
| `t7_courtyard_to_chapel` | mean 0.082 against 0.04–0.07 | 0.063 in Phase 7, before the chapel, cloister and tower existed in that view. The courtyard views measured here went down, not up |
| `t10_lt_cl_s_entry` | mean 0.022 against 0.04–0.08 | 0.038 at P10-7b, but D-084 then removed moon lights (P10-8d). The nearest view with a Phase 11 baseline moved 0.88, which can't explain the drop to 0.57. **Flagged** |
| `t9_02_landing`, `t9_09_puzzle_wall`, `t9_05` (p99), `t9_10` | near their bands, except `t9_10` | `t9_02` 0.047 (0.052 before), `t9_09` 0.0356 (0.0347), `t9_05` same mean as before. `t9_10_NC_gate` is 0.005 against 0.012–0.035: the view is now nearly black up the exit stair, while it was 0.050 on 2026-10-28 with moonlight down the stair. The shaft was rebuilt in Phase 10; the crypt stone didn't change. **Flagged** |

**Not a fault:** the plaque contrast of 1.94 against ≥ 2.5 is the same as at P10-8e; P10 retired this metric for carved text. The memorial and the numerals II, III, I and IV read clearly in `t10_lt_bells`, and `t9_plaque_2m`, `t8_clue_window` and `t8_puzzle_candles` read. The white patch in `t10_lt_beam_west` is a moon pool.

#### Step 1b: one correction (technical-artist [EDITOR])
Only stone that lost brightness to this phase, and only as much as closes most of the gap. Display luma is roughly linear light to the power 1/2.2, so ×1.15 adds about 6.5 % on screen; a mean of 0.88 becomes about 0.94.

| MI | `BrightnessMul` | Why |
|---|---|---|
| `/Game/LastBell/Environments/Kit/Materials/MI_Kit_Masonry` | 1.0 → **1.15** | Courtyard, cloister, passage |
| `/Game/LastBell/Environments/Courtyard/Materials/MI_Env_TowerStone` | 0.35 → **0.40** | Tower (same factor) |

**Not changed:** `MI_Chapel_Masonry_Interior` (median 0.96), `MI_Kit_Trim`, crypt MIs, every light, every other value.

Both children of `MI_Kit_Masonry` have their own `BrightnessMul` override, so `MI_Env_TowerStone` and `MI_Chapel_Masonry_Interior` don't inherit this change. Read that back.

New script `Tools/materials/apply_p11_brightness.py`, same style as `apply_p11_lantern.py`: `--snapshot Docs/ArtTest/materials/p11_8_before.json`, `--apply`, `--check`, `--save` (one package per call, 5 s apart), `--restore`. No PIE. `--check` also reads back `bWeathering`, `GrimeBaseAmount`, `StreakAmount` and `PatchAmount` (unchanged). Commit.

**Lead, with the owner at the PC:** 11 views as `p11_f2_` (`cy_lantern_gate_3m, cy_lantern_route1_3m, cy_west_front_15m, cy_tall_north_15m, cy_graze_north, cl_lantern_bells_3m, cl_tall_north_15m, cl_graze_east, ps_lantern_joints, tw_mid_stair, tw_belfry`) and 3 as `p11_t2_` (`t10_lt_cl_s_entry, t10_lt_inscription, t10_lt_bell_top`), about 10 minutes. **Pass:** ratio 0.92–1.05 on these 11, memorial still legible, no new clipping on lantern-lit walls.

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
