# Phase 11: Materials (surface polish): plan

**Status:** approved by the owner on 2026-11-02. P11-0, P11-1 and P11-2 done; P11-3 done: the owner chose A (D-086). P11-4a passed; P11-4b in progress (owner's "go": A2). The door corners and `Gobo_Moon` specks stay out of scope.
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

#### P11-4c: Reimport (lead + owner)
`Tools/materials/check_reimport.py` snapshots each mesh's tags, slots and default materials before, then compares after, including `FileMD5` against the rebuilt FBX.
1. **Proof, nothing saved:** the lead selects `SM_LB_Kit_Wall_400x60x800_A` in the Content Browser, the owner right-clicks and chooses Reimport, and the lead runs the check for that one mesh and takes a capture. If it fails: stop and report. Unreal is closed with **Don't Save**, which restores the old mesh.
2. **Bulk:** the lead selects the meshes one folder at a time (3 folders), and the owner reimports each selection.
3. **Check all 51,** then save each mesh alone, explicitly.

#### P11-4d: game materials (technical-artist [EDITOR])
Written in full after P11-4c, using the census. In outline:
- production textures in `/Game/LastBell/Environments/Kit/Textures/` (flattened blocks; `rock_01` for trim);
- `MI_Kit_Masonry`: `BaseColorTex` flattened, `MacroStrength` 0.8; `MI_Kit_Trim`: `rock_01` with the `MI_P11_B2_Trim` values;
- check the children (`MI_Chapel_Masonry_Interior`, `MI_Env_TowerStone`, `MI_Chapel_Trim_Dusty`, `MI_Cl_CarveDirt`) and `MI_Crypt_StoneWA`;
- the memorial tablet stays legible; suite; affected baseline captures.

### P11-5: weathering layer (`bWeathering`)
Added to `M_LB_Surface` in **one** recompile (D-053: a GPU-crash risk on the 6 GB card, so close other GPU apps first).

**Static switch** `bWeathering`, default false. **Group** `Weathering`. **Defaults:**

| Parameter | Default | Meaning |
|---|---|---|
| `WeatherFloorZ` | 0 | World Z of the local floor; set per MI where the floor differs (crypt) |
| `GrimeBaseHeightCm` | 220 | Height of the base grime band |
| `GrimeBaseAmount` | 0.45 | Band strength |
| `GrimeNoiseScaleCm` | 180 | Breaks up the band's top edge |
| `GrimeTint` (vector) | (0.30, 0.27, 0.22) | Grime colour multiplier |
| `StreakScaleHCm` / `StreakScaleVCm` | 70 / 900 | Streak size across and down the wall |
| `StreakThreshold` / `StreakAmount` | 0.55 / 0.30 | How many streaks, and how dark |
| `StreakRoughness` | 0.35 | Roughness in streaks (wet look) |
| `PatchScaleCm` / `PatchAmount` | 1100 / 0.18 | Large colour patches that hide repeats |
| `PatchTint` (vector) | (0.82, 0.86, 0.80) | Patch colour |

**Mask, in one Custom node:** reuse the value-noise function from `LB_PuddleMask`.
```
wall   = saturate((1 - abs(N.z)) * 2)                         // N = vertex normal, world
u      = WS.x + WS.y                                          // along the wall; walls here are axis-aligned
band   = (1 - saturate((WS.z - WeatherFloorZ) / GrimeBaseHeightCm))
         * lerp(0.6, 1.0, noise(WS.xy + WS.z, GrimeNoiseScaleCm))
streak = smoothstep(StreakThreshold, StreakThreshold + 0.15,
                    fbm2(float2(u / StreakScaleHCm, WS.z / StreakScaleVCm)))
patch  = noise(float2(u, WS.z), PatchScaleCm)
```
**Apply** after macro variation and before TopDust, Growth, Puddles and Wetness:
```
BaseColor *= lerp(1, GrimeTint, wall * saturate(band * GrimeBaseAmount + streak * StreakAmount))
BaseColor *= lerp(1, PatchTint, wall * patch * PatchAmount)
Roughness  = lerp(Roughness, StreakRoughness, wall * streak * StreakAmount)
```
**Acceptance:**
1. **Regression with the switch off:** ≤ 2/255 on `MI_Kit_Floor`, `MI_Kit_Masonry`, `MI_Kit_Cliff` and `MI_Medieval_Blocks_03`, comparing two recompiles in the same session (MCP_NOTES).
2. **Rollout:** `bWeathering` on for wall MIs only (the list comes from the census). Crypt MIs get their floor Z.
3. **Tuning:** only `GrimeBaseAmount` 0.2–0.6, `StreakAmount` 0.15–0.45, `PatchAmount` 0.1–0.3.
4. **Captures:** the 15 m tall-wall baseline poses show no visible repeat; streaks and the grime band read as weather, with no hard edges across wall pieces.
5. **GPU (owner, 1 minute):** one reading at the chapel mid-nave spot after the rollout. Budget ≤ 16.6 ms. If it is over, use the P11-8 cut list before any decal work.

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
