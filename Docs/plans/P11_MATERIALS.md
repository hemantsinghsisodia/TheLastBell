# Phase 11: Materials (surface polish): plan

**Status:** approved by the owner on 2026-11-02. P11-0, P11-1 and P11-2 done; P11-3 waits for the owner's "go". The door corners and `Gobo_Moon` specks stay out of scope.
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
1. **Downloads** (asset-curator, CC0 only, 2K, registry rows). Candidates found by the lead, unconfirmed as joint-free until the curator looks at them: `polyhaven:rock_surface` and `polyhaven:worn_rock_natural_01`. Reject any with block or mortar lines. A third candidate needs no download: the `MI_Cl_TabletStone` recipe (flat tint plus `T_Rock_064_N`).
2. **Test meshes** (technical-artist, Blender): a no-groove copy of `SM_LB_Kit_Wall_400x60x800_A` and `SM_LB_Kit_Wall_100x60x800`, via `relief_cutters(h_grooves=False, vertical=False, recess_prob=0.0)` with chips kept. Import to `/Game/LastBell/ArtTest/P11/`, with new names. Existing meshes are not changed.
3. **Test map** `/Game/LastBell/ArtTest/P11/L_Test_P11_Walls` (never cooked). The same conditions as the game:
   - floor slabs, a directional moon at 0.9 lux (pitch −38, yaw 35), a sky light at 0.45;
   - a post-process volume with EV100 0.65, `ColorSaturationShadows` 0.65;
   - five wall bays, 6 m apart, each with one lantern 40 cm off the wall (shadowless, 200 lm, radius 600, colour (1.0, 0.549, 0.2196), `MI_LF_Lantern`):

   | Bay | Mesh | Masonry and trim material |
   |---|---|---|
   | 1 (today) | current | `MI_Kit_Masonry` / `MI_Kit_Trim` |
   | 2 (A) | no-groove | `MI_Kit_Masonry` / joint-free trim |
   | 3 (B1) | current | `rock_surface` |
   | 4 (B2) | current | `worn_rock_natural_01` |
   | 5 (B3) | current | `MI_Cl_TabletStone` recipe, with a slightly stronger normal |

4. **Captures** (lead + owner): each bay face-on at 3 m under the lantern, at a grazing angle at 1.5 m, and at 15 m in moonlight only. Contact sheet: `Docs/ArtTest/materials/p11_joint_test.png`.
5. **Owner chooses.** D-086 records the choice.

### P11-4: apply the choice
The lead writes the exact steps after the choice, using the census numbers, in this file.
- **If B:** new master-derived MIs for masonry and trim, by changing the textures on the existing MIs (`MI_Kit_Masonry`, `MI_Kit_Trim` and their children), so no placed actor changes. Save each MI alone.
- **If A:**
  - rebuild the walls with `relief_cutters` grooves off (existing bounds, slots and UCX must not change; `verify_kit.py`, `verify_cloister.py`, `verify_tower.py` must pass);
  - prove Reimport on one mesh first (materials, Nanite, collision, placed actors unchanged);
  - then the owner bulk-reimports. If Reimport fails the check, stop and report.
- **Either way:** the suite, plus captures of the affected baseline poses.

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
