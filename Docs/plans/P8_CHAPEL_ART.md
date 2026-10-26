# Phase 8: Chapel art (P8)

Branch `claude/phase-08-chapel` (from `main` acb822a). The lead plans (D-048); every implementer is spawned with `model: "sonnet", effort: "high"`.

The owner's choices (2026-10-25):
- **Timber roof with one fallen bay.**
- **Glowing stained glass plus coloured light on the floor.**
- **Desecrated but restrained** dressing.
- **Interior as dark as the courtyard** (R-30).

## Context

The chapel is still the Phase 2 greybox:
- white 40 cm box walls, open to the sky;
- white boxes as pews;
- six white 3000 lm point lights (interior mean luma 0.40 against 0.065 in the courtyard);
- greybox cobble ground.

The kit west front (Phase 7) is the only finished part.

Gameplay inside is complete and tested and must not change:
- the candle-order puzzle (Mechanism 1, D-035): 4 `BP_PuzzleCandle`, `BP_SequencePuzzle`, `BP_RitualMechanism`, and the `BP_StainedGlassClue` window with 4 saints;
- the Warden silhouette behind the east window;
- the main door and the crypt door;
- checkpoints `CP_Chapel` / `CP_Chapel_After`;
- `WalkPath.SacristyToCrypt`.

There is no Warden patrol inside the chapel.

## Outcome
A dark, desecrated single-cell gothic chapel:
- **Walls:** 60 cm ashlar walls in three 10 m bays, with tall lancets.
- **East wall:** a traceried east window with translucent glass, through which the silhouette shows.
- **North wall:** the clue window, set in a real opening.
- **Roof:**
  - an open timber roof on arch-braced trusses and stone corbels;
  - a fallen first bay with a moon shaft through the hole into the mist, and a puddle and debris below;
  - a steep slate roof with parapet gables, visible from the courtyard.
- **Floor:** limestone flagstones and a stone choir dais with an altar.
- **Furniture:** pews that are broken, shoved aside and overturned.
- **Ritual:** a chalk ritual circle with burnt-down candles; a toppled saint.
- **Sacristy:** furnished, with one wrapped body.
- **Light:** warm candle clusters against cold window light; coloured stained-glass pools on the floor.
- **Constraints:** routes walkable and tested; GPU ≤ 16.6 ms at High.

---

## 0. Ground rules (all tasks)
- Same as P7-FIX3 §0:
  - drive the editor only via `Tools/mcp/ue.py`, and read `Tools/mcp/MCP_NOTES.md` first;
  - check every result and read it back;
  - one editor-mutating agent at a time;
  - save after each block;
  - never edit .uasset/.umap outside the editor;
  - FBX import defaults per MCP_NOTES;
  - full xform on `set_actor_transform`;
  - capture FX and fog in PIE Simulate;
  - never save with helpers hidden;
  - commit only on `claude/phase-08-chapel` (check `git branch --show-current`); never merge, push or switch branches;
  - no `Source/**` changes;
  - report honestly.
- **Gameplay actors are never moved, deleted or re-parented** except where a step says so: `BP_Door_Base_C_3` (main door), `BP_Door_Base_C_4` (crypt door), `BP_SequencePuzzle_C_0`, `BP_PuzzleCandle_C_0..3`, `BP_RitualMechanism_C_1`, `BP_StainedGlassClue_C_1`, `BP_WardenSilhouette_C_2`, `LBCheckpoint_6`, `LBCheckpoint_7`, every `TargetPoint` WalkPath and every gameplay note.
- **Collision:**
  - BlockAll: walls, dais, altar, pews, rail, lectern, statue plinths, chest, table, rubble heaps and large chunks.
  - NoCollision (via `collisionProfileName`): trusses, purlins, rafters overhead, glass, decals, candles, cobwebs, papers, slate shards, small chunks, ivy, the backdrop, any helper volume.
- **Placement convention:**
  - "bounds X a..b, Y c..d, Z e..f" means the actor's world bounds after placement (±2 cm).
  - "at (x, y)" means the world-bounds centre XY, with bounds min Z = 0 unless a Z is given.
- **Coordinates:** world cm. +X is east (towards the altar); +Y is north. Nave interior faces: X 6060 (west front) / X 8960 (east), Y ±750. Floor Z 0.
- **Outliner folders:** `Chapel/Walls`, `Chapel/Roof`, `Chapel/Windows`, `Chapel/Floor`, `Chapel/Choir`, `Chapel/Sacristy`, `Chapel/Dressing`, `Chapel/Dressing/Ritual`, `Chapel/Dressing/Collapse`, `Lighting/Chapel`. Labels as given.

## 1. Layout (authoritative)

### 1.1 Remove (after the replacements are placed, in P8-5)
- **Greybox chapel pieces in folder `Chapel`:**
  - `StaticMeshActor_97` (north wall);
  - `_98`, `_99`, `_100` (south wall with the 400×300 sacristy opening);
  - `_101`, `_102`, `_103`, `_104` (east wall with the window);
  - `_106` (dais) and `_113` (rail);
  - `_114`…`_121` (8 pews);
  - `_107`…`_111` (sacristy walls) and `_112` (sacristy table).
- **Keep:** the kit west front `StaticMeshActor_654…681` and `StaticMeshActor_812` (small item above the main door; identify it in P8-2).
- **Lights:** `PointLight_23…28` (white 3000 lm) are deleted in P8-7.
- `Ground_0` stays underneath.

### 1.2 Walls (60 thick, interior faces unchanged)
Three bays: B1 X 6000–7000, B2 X 7000–8000, B3 X 8000–9000. Truss lines are at X 7000 and 8000.

| Label | Piece | Bounds | Opening (world) |
|---|---|---|---|
| `Ch_Wall_N1` | `NaveBay` | X 6000–7000, Y 750–810, Z 0–1200 | lancet centred X 6500 |
| `Ch_Wall_N2` | `NaveBay` | X 7000–8000, Y 750–810 | lancet centred X 7500 |
| `Ch_Wall_N3` | `NaveBay_Clue` | X 8000–9000, Y 750–810 | clue window; exact size in amendment C1 (default: clear 260 × 400, sill Z 160, centred X 8750) |
| `Ch_Wall_S1` | `NaveBay` | X 6000–7000, Y −810…−750 | lancet centred X 6500 (broken glass) |
| `Ch_Wall_S2` | `NaveBay` | X 7000–8000, Y −810…−750 | lancet centred X 7500 |
| `Ch_Wall_S3` | `NaveBay_Door` | X 8000–9000, Y −810…−750 | sacristy doorway clear X 8440–8560 (springline Z 240, apex Z 340: the `Doorway_Pointed_400x60x400` profile), plus a lancet centred X 8500 above it |
| `Ch_Wall_E` | `EastWall` | X 8960–9020, Y −810…810, Z 0–1200 | east window clear Y −150…150, sill Z 250, apex Z 880 |
| `Ch_Gable_W` | `Gable` | X 6000–6060, Y −810…810, Z 1200–2215 | on top of the kit west front |
| `Ch_Gable_E` | `Gable` | X 8960–9020, Y −810…810, Z 1200–2215 | on top of `Ch_Wall_E` |
| `Ch_Buttress_N_7000` / `_8000` | `SM_LB_Kit_Buttress_100x150x800` | X 6950–7050 / 7950–8050, Y 810–960, Z 0–800 | exterior, north |

Notes:
- The sacristy opening narrows from 400 × 300 to a 120 × 240 doorway. That's enough for the player; the Warden doesn't path here, and D-038's 84 cm minimum is met.
- Wall ends overlapping the west front (X 6000–6060) and the east wall (X 8960–9020) are hidden inside them, which is intended.

### 1.3 Sacristy (inner faces unchanged: X 8040 west, Y −1500 south, X 8960 east; walls 400 tall)

| Label | Piece | Bounds |
|---|---|---|
| `Sa_Wall_W_Door` | `SM_LB_Kit_Doorway_Pointed_400x60x400` | X 7980–8040, Y −1300…−900 (clear Y −1160…−1040, centred −1100) |
| `Sa_Wall_W_S` / `_N` | `SM_LB_Kit_Wall_400x60x400`, length-scaled | Y −1560…−1300 / −900…−810, X 7980–8040 |
| `Sa_Wall_S_1/2/3` | `Wall_400x60x400` (3rd length-scaled to 240) | X 7980–9020, Y −1560…−1500 |
| `Sa_Wall_E_1/2` | `Wall_400x60x400` (2nd length-scaled to 350) | X 8960–9020, Y −1560…−810 |
| `Sa_Ceiling` | `SM_LB_Kit_Floor_Slab_1000x1000x40`, scaled to fit | X 7980–9020, Y −1560…−810, Z 400–440, `MI_Kit_Trim` |
| `Sa_Joist_1..4` | `SM_LB_Prop_Purlin_15x15x1000` rotated to run along Y, length-scaled 0.69 | X 8200 / 8400 / 8600 / 8800, Y −1500…−810, Z 385–400, NoCollision |

- Length-scaling kit walls is allowed: their materials are world-aligned.
- The stair top step ends at X 7970, so the 20 cm the west wall grows (X 7980–8000) stays clear. Verify this with a bounds query.
- **Crypt door `BP_Door_Base_C_4`:**
  - The kit doorway is 120 × 240. Apply the same treatment as the main door in P7-003 (MODULAR_KIT §"Door leaves"): actor scale (1, 1.18, 1.0818) and shift −9 cm along the hinge axis, so the leaf is about 118 × 238 and centred.
  - Read it back.
  - Its door logic and tags are unchanged.

### 1.4 Roof (pitch 50°)
- **Roof planes.** Slab underside plane per side passes through (Y ±810, Z 1200) and (Y 0, Z 2165). The slab is 20 thick (slate on top, boards underneath) and overhangs 40 cm horizontally at the eaves (to Y ±850).
- **Slabs.** `SM_LB_Kit_RoofSlab_1000x1322x20` × 3 per side:
  - `Ch_Roof_N1..3` and `Ch_Roof_S1..3`, on X 6000–7000 / 7000–8000 / 8000–9000.
  - **`Ch_Roof_S1` is `_Broken`** (the hole; §1.6).
- **Ridge.** `SM_LB_Kit_RidgeCap_1000x40x30` × 3 (`Ch_Ridge_1..3`) along Y 0 on the ridge.
- **Gables** are parapets: their rake top runs 50 above the roof plane (slab 20 + 30 coping), from Z 1250 at Y ±810 to Z 2215 at Y 0. `SM_LB_Prop_CrossFinial_A` sits on each gable apex (`Ch_Finial_W` / `_E`).
- **Corbels.** `SM_LB_Kit_Corbel_40x60x60` (`Ch_Corbel_{N,S}_{7000,8000}`): X 6980–7020 / 7980–8020; Y 690–750 (N) / −750…−690 (S); Z 840–900.
- **Trusses.** `SM_LB_Prop_Truss_ArchBraced_1500` (`Ch_Truss_7000`, `Ch_Truss_8000`), centred on X 7000 / 8000. Geometry in §2 P8-3.
  - The post feet stand on the corbel tops (Z 900).
  - The principal rafters' top faces lie on the roof planes.
  - Apex Z 2165.
- **Purlins.** `SM_LB_Prop_Purlin_15x15x1000` (`Ch_Purlin_{N,S}{1,2}_{B1..B3}`).
  - Two per side per bay, at horizontal Y ±500 (lower) and ±250 (upper), rolled to the roof slope.
  - Their outer top edge sits on the slab underside plane.
  - X spans are the bay spans; the ends are buried in the gables/trusses.
- **Ridge beam.** Purlin pieces at Y 0 under the ridge (`Ch_RidgeBeam_B1..3`).
- **Wall plates.** Purlin pieces on the wall tops' inner edge: Y 735–750 / −750…−735, Z 1200–1215 (`Ch_WallPlate_{N,S}_B1..3`).
- **Bay B1 damage.**
  - `Ch_Purlin_S1_B1` (lower south) is replaced by two `SM_LB_Prop_Rafter_Broken_15x10x260` hanging from the truss/gable ends at 35–50° down.
  - One more `Rafter_Broken` lies on the floor (§1.6).

### 1.5 Floor, choir, windows
- **Nave floor.** `SM_LB_Kit_Floor_Slab_1000x1000x40` ×3, scale (1, 1.5, 1), Z −38.5 (tops 0…+1.5). Bounds X 6000–7000 / 7000–8000 / 8000–9000, Y −750…750.
  - Labels `Ch_Floor_B1..3`.
  - B1 uses `MI_Chapel_Floor_Puddled`; B2 and B3 use `MI_Chapel_Floor`.
- **Sacristy floor.** `Sa_Floor`: the same slab scaled to X 8040–8960, Y −1500…−750 (covers the doorway threshold), Z −38.5, `MI_Chapel_Floor`.
- **Dais.** `SM_LB_Kit_Dais_460x1000x30` (`Ch_Dais`): X 8500–8960, Y −500…500, Z 0–30 (the greybox footprint).
- **Altar rail.** `SM_LB_Prop_AltarRail_600x40x100` (`Ch_AltarRail`): X 8450–8490, Y −300…300, Z 0–100. Same blocking footprint as the greybox rail, so the dais is reached around its ends at |Y| > 300.
- **Altar.** `SM_LB_Prop_Altar_A` (`Ch_Altar`): size and position set by amendment C1 after the P8-2 survey of `BP_RitualMechanism_C_1`. It must not cover or block the mechanism's interaction.
- **Glass meshes** (NoCollision), seated in each opening's glazing groove:
  - `Ch_Glass_N1`, `_N2`, `_S2`, `_S3`: `SM_LB_Prop_Glass_Lancet_140x560`;
  - `Ch_Glass_S1`: `SM_LB_Prop_Glass_Lancet_Broken`;
  - `Ch_Glass_E`: `SM_LB_Prop_Glass_East`;
  - the clue window per C1.
- **Moon backdrop.** `SM_LB_Prop_Backdrop_Plane_800x850` (`Ch_MoonBackdrop`), outside behind the east window: bounds X 9440–9445, Y −400…400, Z 150–1000, `MI_LB_MoonBackdrop`, NoCollision.
  - The silhouette (X 9022–9278) sits between the glass and the backdrop and reads as a dark figure behind coloured glass.
  - `StaticMeshActor_105` (the silhouette's plinth) gets `MI_Kit_Masonry`.

### 1.6 Dressing (desecrated, restrained)
**Keep clear:** the central aisle Y −200…200 from X 6060 to 8350 has no collision objects (decals and NoCollision candles are allowed).

**Pews** (`SM_LB_Prop_Pew_A` / `_Broken`, 250 long along Y, 55 deep along X, facing +X):

| Label | Mesh | At (x, y) | Rotation | Note |
|---|---|---|---|---|
| `Ch_Pew_N1` | Pew_A | (6700, 330) | yaw 4 | |
| `Ch_Pew_S1` | Pew_Broken | (6700, −330) | yaw −6 | a `Rafter_Broken` lies across it |
| `Ch_Pew_N2` | Pew_A | (7100, 325) | yaw 0 | |
| `Ch_Pew_S2` | Pew_A | footprint X 6980–7140, Y −470…−200 | tipped over backwards, back on the floor, bounds Z ≤ 60 | overturned |
| `Ch_Pew_N3` | Pew_A | (7480, 570) | yaw 12, bounds Y ≤ 745 | shoved aside for the circle |
| `Ch_Pew_S3` | Pew_A | (7520, −570) | yaw −10, bounds Y ≥ −745 | shoved aside |
| `Ch_Pew_N4` | Pew_A | (7900, 325) | yaw 0 | |
| `Ch_Pew_S4` | Pew_A | (7900, −325) | yaw −3 | |

**Ritual:**
- `Ch_ChalkCircle` decal (`MI_Decal_ChalkCircle`): centred (7500, 0), 320 × 320 footprint, decal box depth 20.
- `Ch_ChalkSigil_E` (`MI_Decal_ChalkSigil`): on the east wall's inner face below the window, centred Y 0, Z 120, 120 × 120.
- `Sa_ChalkTally` (`MI_Decal_ChalkTally`): on the sacristy south wall inner face at (8700, −1500), Z 140, 80 × 50.
- 5 Fab melted candles (`SM_Candle_Melted_03/07` alternating; `Ch_RitualCandle_1..5`) on the floor at radius 165 from (7500, 0), at angles 18°, 90°, 162°, 234° and 306° (0° = +X). Random yaw, NoCollision.

**Saints:**
- **Standing statue.** `Ch_Statue_Standing`: Poly Haven gothic statue on `Ch_Plinth_Statue` (`SM_LB_Kit_Trim_Plinth_100x80x60`) at (6200, −710), so the plinth spans Y −750…−670 against the south wall. Statue on the plinth top, facing +Y (towards the aisle).
- **Toppled statue.** `Ch_Statue_Toppled`: the same mesh lying on its side at X 6300–6560, Y 480–660, head towards +X. Its empty plinth `Ch_Plinth_Empty` stands at (6500, 710), spanning Y 670–750 against the north wall. A Fab candle stub (unlit) sits on the empty plinth.

**Lectern.** `Ch_Lectern`: `SM_LB_Prop_Lectern_A` toppled on its side at (8150, 600), at least 150 cm from the ChapelNave route. 6 paper sheets (`MI_LB_Paper` quads, NoCollision) are scattered around it within 150 cm.

**Altar candles.** Two `brass_candleholders` stands (`Ch_AltarStand_N` / `_S`) at (8880, ±430) on the dais (Z 30), each with 3 Fab melted candles on the prickets.

**Collapse (bay B1, south):**
- `Ch_Debris_Heap`: `SM_LB_Kit_Rubble_Heap_400x300x130` scaled 0.6, bounds within X 6250–6650, Y −700…−420.
- 4 `SM_LB_Kit_Rubble_Chunk_S/M` (small ones NoCollision).
- `SM_LB_Prop_SlateShards_A` ×3.
- 2 `SM_LB_Prop_RoofPlanks_Broken_200x100x4`.
- 1 `Rafter_Broken` across `Ch_Pew_S1`.
- Everything stays inside X 6250–6950, Y −740…−230.
- 2 dead ivy `_Hang` cards hang from the roof-hole edge (`SM_LB_Prop_Ivy_Hang_150x600_Dead`, top at the slab underside).

**Cobwebs.** `SM_LB_Prop_Cobweb_Corner_A` ×4 in the corners: nave NW/NE at Z 900–1150, sacristy SW/SE at Z 300–400. `SM_LB_Prop_Cobweb_Hang_A` ×3 hang from the trusses' collar beams.

**Sacristy:**
- `Sa_Table`: Poly Haven `wooden_table_02` at (8300, −1430), on the old table footprint.
- `Sa_Chest`: Fab `SM_Trunk_Closed` against the east wall at (8900, −1300), yaw 90.
- `Sa_Stool`: Poly Haven `wooden_stool_01`, tipped over at (8450, −1250).
- `Sa_Body`: Fab `SM_Man_under_cloth` lying along the south wall at (8650, −1440), head towards +X.
- 2 Fab candles on the table.

All of these keep the line (8500, −810) → (8500, −1100) → (7980, −1100) clear by at least 60 cm (SacristyToCrypt WalkPath).

### 1.7 Routes (new WalkPaths; floor-level TargetPoints in `Gameplay/WalkPaths`)
- `WalkPath.ChapelNave`: (6250, 0) (8350, 0) (8380, 450) (8700, 450). This reaches the dais around the rail's north end.
- `WalkPath.ChapelSacristy`: (6250, 0) (8350, 0) (8500, −450) (8500, −700) (8500, −1000).

Lane check: the existing segments of these routes plus `SacristyToCrypt`, clearance ≥ 60 cm. Write it to `Docs/ArtTest/chapel/lane_check_p8.md`.

## 2. Tasks
Order: P8-0 → (P8-1 ∥ P8-2) → **C1** (lead amendment) → P8-3 → P8-4 → P8-5 → P8-6 → P8-7 → P8-8. [EDITOR] tasks never overlap.

### P8-0 — Lead
This spec, the IMPLEMENTATION_PLAN Phase 8 table, DECISIONS D-061…D-064, RISKS R-33…R-35, then commit.

### P8-1 — Downloads (asset-curator; no editor)
Use `3d-assets-local`. One folder each in `ExternalAssets/Incoming/`. Verify, then add registry rows (CC0):
- `ambientcg:Tiles139` (2K-JPG: Color, NormalDX, Roughness, AmbientOcclusion, Displacement; the limestone floor; if Tiles139 isn't cream/grey slabs, use `Tiles143` and report);
- `polyhaven:roof_slates_03` (2K: diff, nor_dx, rough, arm if offered).

Check that the registry already has rows for `gothic_statue`, `brass_candleholders`, `wooden_table_02` and `wooden_stool_01` (downloaded in Phase 6). Add any that are missing.

### P8-2 — Survey (technical-artist; editor READ-ONLY, no saves)
Write `Docs/ArtTest/chapel/survey_p8.md` with:
- (a) `BP_StainedGlassClue`: every component's mesh, material(s), relative transform and world bounds (especially `Glass` and `Frame`); each saint's flame colour (material/param values); how the order is encoded.
- (b) `BP_PuzzleCandle`: component meshes, materials, `BandRing` colours per instance, `FlameLight` intensity/radius/colour, and how lit/unlit toggles.
- (c) `BP_RitualMechanism_C_1`: components, meshes, bounds, interaction component location/extent.
- (d) `BP_WardenSilhouette_C_2`: how it is shown/hidden (hidden in game? which property), and how to make it visible for a capture without saving.
- (e) What `StaticMeshActor_105` and `_812` are (mesh, material).
- (f) `MI_LB_StainedGlass`: parent and parameters.
- (g) `M_LB_Decal` parameters.
- (h) Player `CharacterMovement.MaxStepHeight` and capsule size.
- (i) Notes or other gameplay actors inside X 6000–9020, Y −1560…810.
- (j) Labels of the chapel greybox actors (via any scene tool that returns labels).

Commit the survey file only.

### C1 — Lead amendment (after P8-2)
Fixes:
- the clue-window opening (fitted to the `Glass` component bounds + 10 cm margin);
- the clue re-skin approach: template materials on the BP if they persist, otherwise a dressing frame around it;
- the altar size/position around the mechanism;
- whether the puzzle candles' `Stand` gets the brass pricket mesh (template edit) or stays;
- capture instructions for the silhouette.

### P8-3 — Blender kit, props, textures (technical-artist; headless)
**Kit** (`Tools/blender/kit/build_kit.py`; pivot bottom-left-back; slots MAT_Masonry / MAT_Trim / MAT_Rubble, plus new slots MAT_Slate and MAT_Wood for the roof; UCX; add verify_kit expectations):
- `SM_LB_Kit_NaveBay_1000x60x1200`:
  - Ashlar wall X 0…1000, Y 0…60, Z 0…1200.
  - Lancet: clear 140 wide, sill Z 450, two-centred pointed head (radius 0.8 × span), apex Z 1010.
  - Inner reveal splayed to 220 wide at the inner face (inner face = local Y 0; the south-wall pieces are placed rotated 180°).
  - Outer hood mould (MAT_Trim) following the arch, 8 × 8.
  - Glazing groove 4 deep at Y 40.
  - Sill sloped outward.
  - String course Z 430…450 on the inner face (MAT_Trim).
  - Plinth course Z 0…60 on the outer face (MAT_Trim, projecting 5).
  - UCX: boxes around the opening (left and right of X 430…570, below Z 450, above the apex). The opening is clear.
- `…_Door`:
  - Adds a pointed doorway, clear 120 wide, springline Z 240, apex Z 340, centred X 500, with the same arch profile and voussoirs as `Doorway_Pointed_400x60x400`.
  - The lancet stays.
  - UCX keeps the doorway clear.
- `…_Clue`:
  - A low window, default clear 260 × 400 (sill Z 160), centred X 750 per C1; no lancet.
  - Splayed reveal; groove at Y 10 (the clue glass sits near the inner face).
- `SM_LB_Kit_EastWall_1620x60x1200`:
  - Wall X 0…1620, Y 0…60 (local; placed with yaw 90; inner face = local Y 0).
  - East window centred local X 810: clear 300 wide, sill Z 250, springing Z 620, apex Z 880.
  - Central mullion 12 wide, splitting it into two lights 144 wide, each with a trefoil head (cusps 5 deep); a quatrefoil (Ø 90) in the apex spandrel.
  - Tracery, sill and hood mould in MAT_Trim; glazing groove at local Y 40.
  - UCX around the opening.
- `SM_LB_Kit_Gable_1620x60x1015`:
  - Triangle on Z 0: base width 1620, rakes from Z 50 at the ends to Z 1015 at the centre (world: base on Z 1200).
  - Coping 30 high along the rakes, projecting 5 on both faces (MAT_Trim); kneelers at the base ends.
  - UCX: 5 stepped boxes.
- `SM_LB_Kit_Corbel_40x60x60` (MAT_Trim, ogee underside, 1 UCX).
- `SM_LB_Kit_Dais_460x1000x30` (MAT_Trim slab top with 2 cm bevel on the front (−X) edge, worn top; 1 UCX).
- `SM_LB_Kit_RoofSlab_1000x1322x20`:
  - Flat slab in the slope's local frame: X 0…1000, slope 0…1322, thickness 20.
  - Top: overlapping slate courses (MAT_Slate, 3–4 mm relief).
  - Underside: boards 20 wide with 1 cm gaps (MAT_Wood); eaves edge at slope 1322.
  - No UCX: NoCollision overhead; the player can't reach it.
- `…_Broken`: a ragged hole about X 250…750 × slope 300…1000, with snapped board ends and 4 batten stubs.
- `SM_LB_Kit_RidgeCap_1000x40x30` (MAT_Slate, rounded).

**Props** (`Tools/blender/props/build_props.py`; pivot bottom-centre):
- `SM_LB_Prop_Truss_ArchBraced_1500` (MAT_Wood; no UCX):
  - Local frame: Z 0 = post foot (world 900); Y across the nave; centred Y 0.
  - Posts 25 × 25 at Y ±737.5, Z 0…(up to the rafter underside).
  - Principal rafters 25 wide × 20 deep. Their top faces lie on the plane through (Y ±810, Z 300) and (Y 0, Z 1265) (world 1200 → 2165), clipped at the wall faces Y ±750.
  - Collar 25 × 20, top at Z 850 (world 1750), between the rafters.
  - Two curved arch braces, 20 × 25: a two-centred pointed arch springing at (Y ±725, Z 50), apex at the collar underside (Y 0, Z 830); centres at Y ∓78.9 on the springing line, radius 803.9.
  - Pegs and chamfers.
- `SM_LB_Prop_Pew_A` (250 × 55 × 95; seat Z 45; back of 3 boards with a top rail; end panels with a pointed-trefoil cut-out; MAT_Wood; UCX: seat box + back box).
- `SM_LB_Prop_Pew_Broken` (back snapped at mid-height and hanging, seat split with one plank missing, one end panel missing; UCX).
- `SM_LB_Prop_AltarRail_600x40x100` (top rail, 13 balusters, 2 missing and 1 snapped; MAT_Wood; 1 UCX).
- `SM_LB_Prop_Lectern_A` (octagonal stone foot + wooden shaft + slanted book desk, MAT_Trim + MAT_Wood; 2 UCX).
- `SM_LB_Prop_Altar_A`: stone altar, mensa slab with 5 incised crosses and chamfers (MAT_Trim). Size per C1; default 100 deep × 220 wide × 100 high. UCX.
- `SM_LB_Prop_SlateShards_A` (14–20 slate fragments in a 120 × 90 heap, MAT_Slate).
- `SM_LB_Prop_CrossFinial_A` (stone gable cross 60 × 25 × 90 on a 40-high base, MAT_Trim).
- `SM_LB_Prop_Backdrop_Plane_800x850` (a single quad facing −X).
- Glass meshes (slot MAT_Glass; NoCollision):
  - `SM_LB_Prop_Glass_Lancet_140x560`: the lancet outline, UV 0…1 over its bounding box;
  - `…_Broken`: only 5–7 shards remaining in the frame's lower half, plus a lead fragment;
  - `SM_LB_Prop_Glass_East`: the two trefoiled lights and the quatrefoil, UV-packed to a 1:2 atlas.
- Cobwebs (MAT_Cobweb; NoCollision):
  - `SM_LB_Prop_Cobweb_Corner_A`: two 120 × 120 quads meeting at 90°, with a sagging third quad;
  - `SM_LB_Prop_Cobweb_Hang_A`: a 150 × 80 sagging sheet.

**Textures**, generated by a new seeded script `Tools/textures/gen_chapel_textures.py` (Python + PIL/numpy) into `ExternalAssets/Generated/chapel/`. Record the seeds.
- `T_LB_StainedGlass_Lancet_A` (512×2048 RGBA; A = lead mask 1 = lead):
  - border band 24 px of alternating ruby/amber squares;
  - field of diamond quarries (lead 6 px) in blue-grey with a central vesica medallion (deep blue, crimson, green) at 55 % height.
  - Palette, muted: blue (0.10, 0.16, 0.42), ruby (0.45, 0.06, 0.08), amber (0.55, 0.36, 0.08), green (0.10, 0.30, 0.14), violet (0.25, 0.10, 0.35), pale (0.55, 0.58, 0.60).
  - Per-cell ±8 % brightness noise and subtle "glass streak" noise.
- `T_LB_StainedGlass_Lancet_B`: the same rules, different seed and medallion colours.
- `T_LB_StainedGlass_East` (1024×2048): two lights with a standing robed figure each, abstract (no faces); quatrefoil with a bell motif. It must stay readable with the silhouette behind it.
- `T_LB_LightPool_Lancet` (512×1024): Lancet_A, colour only, Gaussian-blurred 6 px, with lead lines kept as faint dark lines.
- `T_LB_Decal_ChalkCircle` (2048² RGBA):
  - outer ring Ø 300 and inner ring Ø 250 (line 3–5 cm with chalk grain);
  - 12 invented glyphs between the rings (no real-world religious or hate symbols);
  - a bell symbol in the centre;
  - 4 scuffed gaps;
  - 2 smudge trails.
- `T_LB_Decal_ChalkSigil` (512²), `T_LB_Decal_ChalkTally` (512×256, 4 groups of five).
- `T_LB_Cobweb_A` (1024² RGBA, radial web, alpha).

**Finish:**
- verify_kit and verify_props all pass;
- renders of every new piece to `Docs/ArtTest/props/p8_*.png` and texture previews to `Docs/ArtTest/chapel/tex_*.png`;
- LOOK, and iterate until the lancets read as gothic, the truss as an arch-braced truss, the pews as worn monastic pews and the glass as stained glass;
- commit.

### P8-4 — Materials and imports (technical-artist) [EDITOR]
**Material instances:**
- `MI_Chapel_Floor`:
  - Tiles139 on `M_LB_Surface`, world-aligned 200 cm, bWorldAlignedUV.
  - Desaturation 0.35, BrightnessMul 0.55; macro variation as `MI_Kit_Floor`; bPuddles off.
- `MI_Chapel_Floor_Puddled`: child of the above, bPuddles on, PuddleAmount 0.30, same puddle params as `MI_Env_Floor_Puddled` otherwise.
- `MI_Chapel_Masonry_Interior`: child of `MI_Kit_Masonry`, BrightnessMul 0.6, Desaturation 0.25. Use it on the nave and sacristy walls and gables.
- `MI_Kit_Slate`: roof_slates_03 on `M_LB_Surface`, BrightnessMul 0.7.
- `MI_Chapel_Wood_Old`: child of `MI_Prop_Wood_Weathered`, BrightnessMul 0.55, for pews, trusses, rail and lectern.

**New masters:**
- `M_LB_StainedGlass` (opaque, Default Lit):
  - BaseColor = GlassTex.rgb × 0.04, lerped to (0.02, 0.02, 0.02) on lead.
  - Emissive = GlassTex.rgb × (1 − A) × `EmissiveIntensity` × `Tint`.
  - Roughness 0.12 on glass, 0.6 on lead.
  - Params: `GlassTex`, `EmissiveIntensity` (default 2.0), `Tint`.
- `M_LB_StainedGlass_Translucent` (Translucent, Unlit):
  - Emissive = GlassTex.rgb × `EmissiveIntensity` × (1 − A).
  - Opacity = lerp(`GlassOpacity` 0.45, 1.0, A).
  - Two-sided off.
- `M_LB_Decal_LightPool` (Deferred Decal, Translucent, emissive only): Emissive = PoolTex.rgb × `Color` × `Intensity` × `Mask`, where Mask is a radial falloff from UV centre with soft edges `EdgeSoftness` 0.25.
- `M_LB_Decal_Chalk` (DBuffer ColorNormalRoughness): BaseColor (0.82, 0.80, 0.75), Roughness 0.95, Opacity = Tex.a × `Opacity` (0.9).
- `M_LB_Cobweb` (Masked, two-sided, Default Lit): BaseColor 0.6 grey, OpacityMask = Tex.a, clip 0.3.

**Instances of the new masters:**
- `MI_Glass_Lancet_A` / `_B` (Tint (0.85, 0.9, 1.0));
- `MI_Glass_East` (translucent);
- `MI_Glass_Broken` (A);
- `MI_Decal_LightPool_Lancet`, `MI_Decal_ChalkCircle`, `MI_Decal_ChalkSigil`, `MI_Decal_ChalkTally`;
- `MI_Cobweb_A`;
- `MI_LB_MoonBackdrop` (Unlit emissive (0.06, 0.065, 0.08) × 1.0 on `M_LB_Mist` or a new tiny unlit master, recorded).

**Imports:**
- all P8-3 meshes into `/Game/LastBell/Environments/Kit/` (kit) and `/Game/LastBell/Environments/Props/Procedural/Chapel/` (props);
- textures into `/Game/LastBell/Environments/Chapel/Textures/`;
- Nanite on for walls, gables, roof, truss and pews; off for glass, cobwebs, candles, shards, backdrop and papers; record.

**Relocation:** move `ArtTest/Props/Gothic_Statue` and `ArtTest/Props/Brass_Candleholders` to `/Game/LastBell/Environments/Props/CC0/` with references fixed. If files remain on disk, list them and stop.

**Finish:** thumbnails to `Docs/ArtTest/chapel/thumb_*.png`, then commit.

### P8-5 — Structure (environment-designer) [EDITOR]
Per §1.2–1.5:
1. Place the walls, sacristy, roof, trusses, purlins, wall plates, ridge, gables, finials, corbels, buttresses, floors, dais, rail, altar (C1) and glass.
2. Adjust the crypt door leaf; place the backdrop; set the plinth MI.
3. Then remove the greybox pieces (§1.1). Keep the 6 greybox lights for now: P8-7 removes them, so the editor isn't pitch-black while placing.
4. Add the WalkPath points (§1.7) and run the lane check.
5. Save, then run the suite with the map saved: 78/78 plus `WalkPath.Monastery` with ChapelNave, ChapelSacristy, SacristyToCrypt and the 4 Courtyard paths PASS, and `RouteBot.Monastery` Success.
6. Clean editor captures `g8s_*` (structure only): nave from the entrance, the nave looking back, trusses and roof, east window, sacristy, exterior north, and the courtyard view with the new gable (pose (500, 0, 170)).
7. Commit.

### P8-6 — Dressing (environment-designer) [EDITOR]
Per §1.6, with the C1 clue re-skin and puzzle-candle stand if approved:
1. Place everything; check NoCollision and the aisle rule; re-run the lane check.
2. Save, run the suite, take captures `g8d_*`, commit.

### P8-7 — Lighting, glass and atmosphere (lighting-vfx) [EDITOR]
- **Delete** `PointLight_23…28`.
- **Warm lights.** All PointLight, Movable, shadowless, colour (255, 147, 41), VolumetricScatteringIntensity 1.0, `MI_LF_Candle`:

  | Label | Position | Intensity | Radius |
  |---|---|---|---|
  | `Light_Chapel_Altar_N` / `_S` | (8880, ±430, 140) | 250 lm | 320 |
  | `Light_Chapel_Ritual` | (7500, 0, 25) | 300 lm | 380 |
  | `Light_Chapel_Statue` | (6230, −640, 95) | 150 lm | 250 |
  | `Light_Sacristy_Table` | (8300, −1430, 115) | 150 lm | 260 |

- **Moon shafts.** Interior SpotLights at the south lancets' inner reveal: `Light_Chapel_Shaft_S1/S2/S3` at (6500 / 7500 / 8500, −700, 950), aimed at (X + 150, −120, 0).
  - Colour (190, 205, 235), 1500 lm (tune 500–3000), radius 1600, inner/outer cone 6°/14°.
  - Shadowless, VolumetricScatteringIntensity 3.0, no light function.
- **Roof-hole shaft.** `Light_Chapel_Shaft_Roof` at (6500, −350, 1650), aimed at (6950, 220, 0). Cone 10°/18°, 3000 lm (tune 1500–6000), scattering 4.0, shadowless.
- **Pools.** `Ch_Pool_S1/S2/S3/Roof`: `MI_Decal_LightPool_Lancet` decals, 260 × 130 (roof 300 × 220), at each shaft's floor landing point, long axis along the shaft's horizontal direction. Intensity tuned so the pool's max luma is 0.35–0.6 and its colours read.
- **Glass emissive.** Tune `EmissiveIntensity` so the lancet glass luma is 0.2–0.45 from the nave centre. Clue window per C1.
- **Mist.** `LFV_Chapel_Nave`: Local Fog Volume at (7400, 0, 0), scale 3.0 (radius 1500), emissive (0.028, 0.030, 0.036), albedo (0.86, 0.87, 0.90), as the courtyard LFVs. Tune density until the shafts read without greying the whole nave.
- **Targets** (PIE Simulate; B2 luma definition from P7-FIX3):
  - Entrance view (6200, 0, 170, yaw 0) and mid-nave view (7300, 0, 170, yaw 0): mean 0.04–0.08, fraction < 0.02 ≥ 0.15, p99 ≥ 0.25, max ≥ 0.9.
  - Sacristy (8250, −900, 170, yaw −45): mean 0.03–0.08.
- **Readability gates:**
  - (a) Clue window from (8750, 300, 170) facing +Y: the 4 saint flames have distinct hues (record their RGB) with luma ≥ 0.2.
  - (b) Puzzle candles from (8300, 420, 180) looking at the dais: each candle's band colour is distinguishable (unlit) and the crop luma is ≥ 0.08. Record their lit-state FlameLight look in one capture with all 4 lit (via PIE world-state if possible; otherwise say so).
  - (c) From the door (6200, 0, 170): the altar region's max luma ≥ 0.6.
  - (d) Every point of ChapelNave, ChapelSacristy and SacristyToCrypt (sacristy part) is within 800 cm of a warm light or shaft.
  - (e) East window with the silhouette visible (per C1): the silhouette area is ≥ 0.05 luma darker than the surrounding glass.
- **Courtyard regression.** Re-capture g6_04 and g6_14: the luma numbers stay within ±0.01 mean of fefe4f7's values. The chapel roof and gable are now visible on the skyline.
- **Captures** `g8_01…g8_13`:
  1. courtyard→chapel (500, 0, 170);
  2. entrance;
  3. mid-nave;
  4. back towards the door from (8700, 0, 200, yaw 180);
  5. roof-hole shaft from (6400, 300, 170) looking at (6600, −400, 900);
  6. clue window;
  7. dais and candles;
  8. east window (8400, 0, 170, pitch 10);
  9. sacristy;
  10. ritual circle (7500, −300, 400, pitch −50, yaw 90);
  11. trusses (7500, 0, 170, pitch 45);
  12. exterior north (7500, 1600, 170, yaw −90);
  13. garth from the gate (350, 0, 170).
- **Finish:** suite, then commit.

### P8-8 — QA and review
- **QA reviewer** (read-only): git hygiene, content layout and naming, registry, editor log, collision/NoCollision rules, the aisle rule, lights and LF assignments, tests, docs, spot-checks against §1.
- **Docs:** MCP_NOTES (stained-glass/decal pool approach, door-leaf scaling repeated), PERFORMANCE_BUDGET row, ASSET_REGISTRY, RISKS (close R-30 if met).
- **Owner:**
  - PIE in a new window: `scalability 2`, `r.SetRes 1920x1080w`, `stat unit` + `stat gpu` mid-nave → ≤ 16.6 ms. If over, cut in this order: LFV off, then shaft scattering halved, then the roof-hole spot off.
  - Playtest: enter, solve the candle puzzle, see the silhouette, go to the sacristy and into the crypt.
- Then the report "PHASE 8 READY FOR YOUR REVIEW". Merge only on approval.

## 3. Verification
- Suite: 78/78 plus WalkPath.Monastery (incl. the 2 new chapel paths) plus RouteBot.
- verify_kit / verify_props all pass.
- Lane check ≥ 60 cm.
- Luma targets and readability gates.
- Lead review of the captures.
- Owner `stat gpu` and playtest.

---

## Amendments (lead)

**C0 (2026-10-25, owner request): more Dungeon- and Horror-pack items.**

The owner chose:
- **Dungeon pack:** candles, candelabra and flames; chains and shackles; bones and skulls; sacristy life and cobwebs.
- **Horror pack:** hanging body from a truss; the cloth body in the sacristy; the burlap body among the pews. (The stretcher and body bag were dropped by the owner the same day: they don't suit a chapel.)

The tone moves from "restrained" to **desecrated, heavier** (D-063 updated): bodies and bones are deliberate, but there is still no gore or blood pools.

The owner migrates the assets per `Docs/ArtTest/chapel/fab_picklist_p8.md`. **P8-4** relocates them:
- `/Game/Dungeon/**` → `/Game/LastBell/ThirdParty/Fab/Dungeon/` (same sub-folders as the P7 relocation);
- references fixed;
- duplicate shared materials merged into the existing relocated copies (as P7F-3g);
- `MaxTextureSize` 1024 for candles, bones, tavern props and shackles, 2048 for bodies, chest, bench and chair;
- the registry rows for both packs updated with the added items.

**P8-2 survey additions:**
- (k) After the migrate: `BP_Flame_00/01` components, i.e. whether they contain a light, which particle system or mesh they use, and their size.
- (l) `SK_Dead_Man` with `Anim_Dead_Man_Idle` / `_other`: does the mesh include a rope? Its height and pivot.
- (m) Sizes and pivots of `SM_Candles_Holder_00…05` and the skeleton piles.

**Flames.** Use the pack flames as provided, but **no flame may carry its own light**.
- If `BP_Flame_00/01` contain a light component, create a child `BP_LB_CandleFlame` (in `/Game/LastBell/Blueprints/Props/`) with that light disabled (child defaults, or the child's construction script if the inherited component can't be overridden).
- Place only the child.
- The cluster lights stay the planned P8-7 point lights.
- Cap: **at most 16 lit flames** in the chapel and sacristy. Every other candle is snuffed (no flame).

**Placement changes to §1.6.** All NoCollision unless noted. The aisle rule and route clearance (≥ 60 cm) still hold.

- **Altar candelabra.**
  - Replace the two `brass_candleholders` with the tallest floor-standing `SM_Candles_Holder_0x` (from survey (m)) at (8880, ±430), labels `Ch_AltarStand_N/S`.
  - Fill the holders' sockets with `SM_Candle_0x` (fresh).
  - 3 lit flames per stand.
  - `brass_candleholders` moves to the statue plinth (below).
- **Ritual circle.**
  - The 5 candles become `SM_Candle_Melted_01/04/08/05/09` at the same 5 points, with 3 lit flames (angles 90°, 234° and 18°).
  - `Ch_RitualSkull`: `SM_Skull_02` at the centre (7500, 0), yaw 180 (facing the entrance).
  - 2 `SM_Dungeon_bowl` / `SM_Pot_00` offerings at radius 120 (angles 135° and 315°).
- **Statue plinth (standing saint, (6200, −710)).**
  - `brass_candleholders` on the floor beside the plinth at (6310, −690), with 2 lit flames.
  - `SM_Torture_Devices_Shackles_01` wrapped around the plinth foot.
- **Toppled saint.**
  - 3 `SM_Candle_Melted_02/06/10` knocked over (lying) around the empty plinth.
  - 1 upright `SM_Candle_Melted_03`, unlit.
- **Window sills.** On the interior sills (Z 450) of N1, N2, S2 and S3: 4–6 burnt-down melted candles each, mixed sizes, unlit; on S2, 1 lit flame.
- **Chains.**
  - Two `SM_Dungeon_chain_holder` rings on the east wall's inner face at Y ±260, Z 260, with `SM_Torture_Devices_Chains` hanging from each down to the dais, the last 40 cm pooled on the floor (`Ch_EastChain_N/S`).
  - Two chains hang from `Ch_Truss_8000`'s collar at Y ±320 down to Z ≈ 1000.
  - `SM_Dungeon_shackles_00` lies open on the dais floor at (8700, −380).
- **Hanging body.**
  - `Ch_HangingBody`: `SK_Dead_Man` as a SkeletalMeshActor, looping `Anim_Dead_Man_Idle`, NoCollision, CastShadow on.
  - It hangs from `Ch_Truss_7000`'s collar beam over the north side aisle at (7000, 580). The rope's top is at the collar underside (Z ≈ 1730), the feet at Z 110–140, and it must never be over Y < 300.
  - If the mesh has no rope, use `SM_Torture_Devices_Rope_00` stretched from the collar to the neck.
- **Burlap body.** `Ch_BurlapBody`: `SM_Dead_Man` lying half under the fallen `Rafter_Broken` in bay B1, centre (6880, −560), yaw 80, inside the collapse footprint (X 6250–6950, Y −740…−230).
- **Bones.**
  - `SM_Skull_00` half under `Ch_Pew_S1`.
  - `SM_Skeleton_Arm_00` and `SM_Skeleton_Leg_01` among the collapse debris.
  - `SM_Skeleton_Pile_02` (or the smallest pile per survey (m)) in the sacristy's SW corner at (8120, −1440).
  - No bones in the central aisle except the ritual skull.
- **Sacristy** (replaces the §1.6 sacristy list):
  - `Sa_Table`: `wooden_table_02` at (8300, −1430). On the table:
    - `SM_Bread` + `SM_Bread_Slice`, `SM_Jug`, 2 × `SM_Bowl`, `SM_Cup_01`, `SM_Plate` + `SM_Cutlery`, `SM_Pitcher_01`;
    - `SM_Mug_Empty` tipped over;
    - a small `SM_Candles_Holder_0x` with 2 `SM_Candle_0x`, 1 lit flame.
  - `Sa_Chair`: `SM_Scribe_Chair`, pulled back askew at (8300, −1330), yaw 200.
  - `Sa_Bench`: `SM_Dungeon_bench` along the west wall, bounds Y −1490…−1250, X 8045–8110, BlockAll.
  - `Sa_Chest`: `SM_Dungeon_chest` against the east wall at (8900, −1300), yaw 90, BlockAll, with `SM_Pouch_01` on top. This replaces the Fab trunk.
  - `SM_Pot_00` and `SM_Plate_00` on the floor by the chest.
  - Wall ring: `SM_Dungeon_chain_holder` on the south wall at (8500, −1500, 140) with `SM_Dungeon_shackles_01` hanging.
  - `Sa_Body`: `SM_Man_under_cloth` along the south wall at (8650, −1440), head +X, as before.
  - Bone pile per the bones list above.
  - Keep ≥ 60 cm from the line (8500, −810) → (8500, −1100) → (7980, −1100).
- **Cobwebs.** The cobweb cards use an MI of the pack's `M_Cobweb` (`MI_Cobweb_Dungeon`) instead of the generated `T_LB_Cobweb_A`. P8-3 still builds the card meshes; the generated texture is optional (fallback).
- **Lights (P8-7).** No change to the planned light list. The extra lit flames sit inside the existing warm pools (altar, ritual, statue, sacristy table). The S2 sill flame gets no light of its own.

**Readability.** The clue view (P8-7 gate (a)) and the dais view (gate (b)) must stay uncluttered:
- no chains, bodies or candles between the camera poses and the clue window or the 4 puzzle candles;
- the east chains hang beside the window, not in front of it.

**C1 (2026-10-25, after the P8-1 downloads and the P8-2 survey `Docs/ArtTest/chapel/survey_p8.md`).** Where C1 conflicts with §1, §2 or C0, C1 wins.

1. **Clue window (north bay B3).** The clue is a free-standing plaque against the wall's inner face, not an object in a window:
   - Frame X 8688–8812, Y 744–750, Z 300–544, BlockAllDynamic;
   - Glass 112 × 232 at X 8694–8806, Z 306–538;
   - saints at Y 739–744;
   - left to right from the nave: green, red, amber, blue (Saint1 at X 8792 … Saint4 at X 8708). This matches the puzzle steps 3, 1, 4, 2.

   It stays exactly where it is.

   `SM_LB_Kit_NaveBay_1000x60x1200_Clue` replaces the §2 default:
   - **Real opening** behind the plaque: clear X 8700–8800 (100 wide), sill Z 312, springing Z 458, two-centred head (radius 80), apex Z 532.
     - Piece-local, with the piece spanning X 8000–9000: centred local X 750.
     - Glazing groove at local Y 40 (outer side).
     - The plaque's Frame (124 × 244) hides the opening's edges from inside.
   - **Inner face:**
     - a pointed hood moulding framing the plaque (MAT_Trim, 10 × 8): springing at Z 470, inner width 150 (X 8675–8825), apex Z 575, label stops at the springing;
     - a stone sill ledge Z 288–300, X 8670–8830, projecting 8 cm from the inner face (Y 742–750; its collision may touch the Frame).
   - **No lancet** in this bay.
   - UCX keeps the opening clear.
   - **Exterior glass:** `SM_LB_Prop_Glass_Clue_Ext` (opening outline, UV 0…1, NoCollision) in the groove, with `MI_Glass_Lancet_B`.

   **Template re-skin:** `Frame` material → `MI_Kit_Trim` only (P8-6b). The Glass, the four saints' materials and colours, their positions and every collision setting are **never changed**.

2. **East window and the silhouette ledge.**
   - `Window_Ledge` (`StaticMeshActor_105`, X 9000–9300, Y ±300, Z 0–300, BlockAll) holds `Silh_ChapelWindow` (`BP_WardenSilhouette`, centre (9150, 0, 300)). It stays and gets `MI_Kit_Masonry`.
   - The east window moves up so the ledge's top isn't seen as a block in the window: **sill Z 310, springing Z 650, apex Z 900** (clear 300 wide; the rest per §2).
   - The silhouette is visible in the **editor viewport** (it is hidden only at BeginPlay in game and shown for 3 s on `State.Ritual.1`). Do gate (e) as an editor-viewport capture, with no PIE and nothing to change.
3. **Altar** (`SM_LB_Prop_Altar_A`, P8-3), designed as a shell around the mechanism.
   - **Mechanism:** `Altar_Ritual1` = `BP_RitualMechanism_C_1`, bounds X 8850–8950, Y ±50, Z 30–195, made of:
     - a 100 cm WorldGrid cube pedestal Z 30–130;
     - a cylinder Ø 80 at Z 130–180, centred (8900, 0);
     - a 15 cm marker cube at Z 180–195 at the cylinder's edge.
   - **Altar extent:** X 8848–8952 (104 deep), Y −150…150 (300 wide), Z 30–131. Hollow core Y −52…52 / X 8849–8951, open at the bottom, so the pedestal sits inside it.
   - **Mensa:** top slab Z 121–131 over the full 300 width, chamfered and overhanging 4 cm on −X, with a **circular hole Ø 84 at (8900, 0)** for the cylinder.
   - **Front face** at X 8848 (2 cm in front of the pedestal), so the WorldGrid cube is fully hidden.
   - **UCX only on the two wings:** Y −150…−54 and 54…150 (X 8848–8952, Z 30–131). The centre has **no collision**, so the player's interaction sweep (200 cm reach, 8 cm sphere, Interaction channel) passes the altar front and hits the pedestal as it does today.
   - Detail: chalk-scrawled front panel (the chalk sigil decal moves here, see 10); 5 incised crosses on the mensa.
   - Placed with bounds exactly as above; label `Ch_Altar`; `MI_Kit_Trim`.
   - The visible cylinder and marker get a template material re-skin in P8-6b: cylinder → `MI_LB_Bronze`, marker → `MI_LB_Iron`.
     - If the template edit doesn't persist, use NoCollision shells instead: `SM_LB_Prop_MechShell_Cyl` Ø 84 × 51 open at the bottom (Z 130–181, centred (8900, 0)) and `SM_LB_Prop_MechShell_Cube` 17³ around the marker. Both are built in P8-3 just in case.
4. **Puzzle candles** (`Candle_P1…P4`): bands red, blue, green, amber at Y −200 / −67 / 67 / 200; X 8800 (P1, P4) / 8820 (P2, P3); on the dais at Z 30.
   - Components: Stand (cylinder 10 Ø × 30, Z 30–60, `MI_LB_DarkWood`, BlockAllDynamic), BandRing (13 Ø × 4 at Z 50–54, MID of `MI_LB_StainedGlass`, BlockAllDynamic), Wax, Flame (emissive sphere at Z 77–84), FlameLight (8 cd, radius 300, (1, 0.6, 0.3)).
   - Lit/unlit toggles visibility of Flame and FlameLight only.
   - **P8-6b template re-skin**, all optional with verification and revert on failure:
     - `Stand` mesh → new `SM_LB_Prop_PricketStand_Small_10x30` (iron, same 10 × 30 envelope, a UCX box 10 × 10 × 30), material `MI_LB_Iron`;
     - `Wax` material → `MI_LB_CandleWax` (mesh unchanged).
   - **Never changed:** BandRing (colour = clue), Flame, FlameLight, InteractComp, any collision profile or transform.
   - No dressing actor may stand between X 8550 and 8830 within |Y| ≤ 260 on the dais, apart from the existing BPs.
5. **Altar candles.**
   - The Dungeon pack has **no floor candelabrum** (holders 01–04 are 27 cm table-top pieces; 00 is a plate). **Holder 05, a 9-branch menorah, is not used anywhere** (religious-symbol sensitivity).
   - New procedural `SM_LB_Prop_PricketStand_150`: wrought-iron floor pricket, tripod feet 45 cm spread, shaft Ø 3, drip pan Ø 30 at Z 135, 3 prickets in a 22 cm triangle at Z 138–150; `MI_LB_Iron`; UCX: one box 30 × 30 × 150.
   - Two of them, `Ch_AltarStand_N/S`, at (8880, ±430) on the dais, each with 3 `SM_Candle_0x` on the prickets.
   - Table-top `SM_Candles_Holder_03` / `_04` stand on the altar wings' top (Z 131) at (8900, ±110), with candles, NoCollision.
6. **Flames (C0).** `BP_Flame_00/01` have **no light** and are Cascade (`PS_Fire_00/01` at component scale 0.25); their size is unknown, and `PS_Fire_00` at tiny scale was rejected as a candle flame in P7.
   - P8-6 first places one `BP_Flame_00` on a candle and captures it in PIE Simulate at actor scales 1.0 / 0.5 / 0.25 / 0.12.
   - Use it only if one scale gives a flame **4–8 cm tall** that reads as a candle flame. Record the scale.
   - Otherwise use the puzzle candles' own flame look: a new `SM_LB_Prop_CandleFlame_A` (teardrop 3 × 3 × 6.5 cm, NoCollision) with `MI_LB_CandleFlame`, which is consistent with the puzzle.
   - The cap of 16 lit flames still applies.
7. **Hanging body.** `SK_Dead_Man` **includes its rope** (one material slot). It is 233 cm tall: bounds Z 33.6–266.8 above its pivot, rope top at +266.8. Anim lengths: Idle 4.0 s, other 3.3 s.
   - The truss collar is at Z 1750, far too high, so it hangs from the **north arch brace** of `Ch_Truss_7000` instead. At Y 580 the brace's underside is at Z ≈ 1410 (brace circle centre (Y −78.9, Z 950), radius 803.9).
   - **Feet at Z 200**, above the player's capsule top (176), so it is NoCollision without being walkable-through at head height. That puts the pivot at Z 166.4 and the mesh rope top at Z 433.2.
   - `SM_Torture_Devices_Rope_00` is stretched (scaled along its length) from the mesh rope top (Z 433) to the brace underside (Z 1410), at (7000, 580). A knot or loop over the brace is optional.
   - Looping `Anim_Dead_Man_Idle`, CastShadow on, NoCollision.
8. **Notes ride on furniture** (they are gameplay actors; this is the only allowed move, Z only, same XY and yaw):
   - `Note_Nave` (`BP_Inspectable_Note_C_6`, (7100, 238, 90.3), yaw −12) was on greybox `Pew_N1`, now `Ch_Pew_N2`. Set its Z to `Ch_Pew_N2`'s seat top + 0.3 at the same XY.
     - Build `Pew_A` so its seat spans at least X −20…+20 around the pew centre.
     - Place `Ch_Pew_N2` exactly at (7100, 325) yaw 0, so the note lies on the seat.
   - `Note_Sacristy` (`BP_Inspectable_Note_C_7`, (8300, −1450, 90.3), yaw 8): set its Z to `Sa_Table`'s top + 0.3. The table's top must cover (8300, −1450).
   - Keep a 25 cm radius around both notes free of other props (e.g. the meal props).
9. **Textures.**
   - **Floor:** Tiles139 is warm beige square limestone, 6 × 6 slabs per texture, no AO map. `MI_Chapel_Floor` uses world-aligned tile size **360 cm** (60 cm slabs), Desaturation 0.45, BrightnessMul 0.5, and a slight cool tint (0.92, 0.95, 1.0) if the master has a tint parameter (record it).
   - **Roof:** `roof_slates_03`'s top rows are a ridge-cap strip. `Tools/textures/gen_chapel_textures.py` also writes cropped `T_LB_RoofSlates_*` maps (diff, nor_dx, rough), removing the strip plus whole slate courses so they tile vertically. Check the seam with a 2×2 tiled preview `Docs/ArtTest/chapel/tex_roofslates_tile.png`.
   - The roof slab's top uses slope-aligned UVs (not world-aligned), so slate courses run along X and a slate is about 25 × 40 cm. `MI_Kit_Slate` has bWorldAlignedUV off.
10. **Chalk sigil.** `Ch_ChalkSigil_E` moves from the east wall onto the altar's front panel: centred (8848, 0, 80), 80 × 80, projecting +X. The east wall below the window gets `Ch_ChalkSigil_E2` (second sigil) at Y 0, Z 180.
11. **Dirty Blueprints.** The survey's `read_graph_dsl` left `BP_StainedGlassClue`, `BP_PuzzleCandle`, `BP_RitualMechanism` and `BP_WardenSilhouette` dirty in memory, unsaved. The owner restarts the editor with **Don't Save** before P8-4. No agent saves these packages unless P8-6b edits them on purpose.
12. **New task P8-6b: puzzle prop re-skin (unreal-blueprint-engineer) [EDITOR], after P8-6 and before P8-7.**
    - Template edits only, on `BP_StainedGlassClue` (Frame material), `BP_PuzzleCandle` (Stand mesh and material, Wax material) and `BP_RitualMechanism` (cylinder → `MI_LB_Bronze`, marker → `MI_LB_Iron`).
    - For each BP:
      1. Read the current value.
      2. Write the template.
      3. Compile with warnings as errors off; errors must be 0.
      4. Save only that BP.
      5. Read back the template and **the placed instance's component** to confirm the instance uses the new mesh/material.
      6. Capture.
    - Then run the full suite: puzzle tests, RouteBot and WalkPaths.
    - Any failure or non-persistence: restore the old value, recompile, save, and use the fallback (shells for the mechanism; leave the candles and clue as they are).
    - Report a table of old → new → instance read-back.
13. **Also:**
    - `KC_DoorTympanum` (`StaticMeshActor_812`, plank panel in the main door's tympanum) and `PointLight_2` (chapel-door warm light) stay.
    - Pew seat height 45 and back top 95 are fine for `MaxStepHeight` 45: pews are BlockAll and are not meant to be climbed.

**C2 (2026-10-26, after the P8-3 review, commits abe0728…296fbd0).** P8-3 is accepted, with these decisions:
- **Accepted deviations:**
  - Wall details stand 3 cm proud (not 5/8), so the 60 cm envelope and the §1.2 bounds stay exact.
  - The `_Clue` bay spans local Y −8…60: the hood and sill ledge project 8 cm into the nave, and its world bounds read Y 742–810. Place it exactly like the other bays.
  - `CrossFinial_A` is 130 tall.
  - The backdrop is a zero-thickness quad: place it at X 9440, facing −X.
  - The truss is now 30 wide; rafters 40, collar 35, braces 30, posts 30 × 35.
- **Textures** come from `ExternalAssets/Generated/chapel/`, which is git-ignored. If they're missing, regenerate with `python Tools/textures/gen_chapel_textures.py` (deterministic).
- **Slates:** `MI_Kit_Slate` uses `bUseARM` with `T_LB_RoofSlates_arm` (the source roughness map is constant 1.0), plus `T_LB_RoofSlates_diff` / `_nor_dx`, with UV mode (not world-aligned). Start the UV scale at U 0.2, V 0.3 per 100 cm (≈ 25 × 20 cm slates) and tune by eye on the roof capture.
- **Placement references from the P8-3 report:**
  - `Altar_A` local Z 0 = world 30.
  - `Glass_East` local Z 0 = world 310 (lights to 464.7, quatrefoil at 480).
  - `Glass_Lancet*` / `Glass_Clue_Ext` local Z 0 = sill.
  - The glass slabs are 1 cm thick and centred in Y: place them in the groove at wall-local Y 39–42.
  - `PricketStand_150`'s shaft is 4.5 cm off the bbox centre.
  - `Cobweb_Corner_A`'s corner edge is at local (−60, −60).

**C3 (2026-10-26, after the P8-6 review; commits d5443eb…e949875).**
- **P8-6 accepted**, with these as-built choices:
  - flame mesh `SM_LB_Prop_CandleFlame_A` (BP_Flame rejected: an ember column), 13 lit flames;
  - `MI_Cobweb_Dungeon`;
  - the stool instead of the scribe chair;
  - `MI_Chapel_Rubble`, `MI_Sacristy_Table_Old`;
  - the hanging body from the arch brace at Z 1376 (traced).
- **Clue glass (amends C1-1):** in P8-6b, the plaque's `Glass` may also be re-skinned. It's additive lilac (0.35, 0.40, 0.60), which washes the saints out.
  - Create `MI_LB_ClueGlass` (child of `MI_LB_StainedGlass`, Color (0.10, 0.12, 0.22)) and set it on the `Glass` template.
  - Accept it only if readability improves. Measure the mean RGB of each saint body and of the glass background in a capture from (8750, 300, 170) facing +Y, before and after. The four saint hues must stay distinct, and the saint-vs-background luma contrast must rise. Otherwise revert.
  - The saints' materials, colours and positions are still never changed.
- **P8-7 additions:**
  - B1 floor puddles currently read as large black blobs (they reflect the dark roof). Tune `MI_Chapel_Floor_Puddled` (PuddleAmount 0.08–0.15, smaller NoiseScale) so standing water is confined to small pools mostly under the roof hole (X 6250–6750, Y −700…−100). No dark patch wider than about 1.5 m outside that area in `g8_02`. If that can't be reached, switch `Ch_Floor_B1` to `MI_Chapel_Floor` and note it.
  - The silhouette must read through the east glass (gate (e)): raise `MI_LB_MoonBackdrop` Color up to (0.25, 0.27, 0.32) and/or lower `MI_Glass_East` GlassOpacity down to 0.30.

**C4 (2026-10-26, owner playtest feedback).** The owner reported three problems:
1. "light sources not matching the windows";
2. "dense fog at the chapel door that disappears when I step inside";
3. "the light from the windows looks pixelated".

Diagnosis (lead):
- **(1)** The shafts are interior shadowless spots at (X, −700, 950) aimed at (X + 150, −120, 0), so they don't come *through* the windows. The S1 spot even sits above its broken glass (top Z 862).
- **(2)** `LFV_ChapelFront` (courtyard, centre (5500, 0, 0), radius 636, reaching X 6136) and `LFV_Chapel_Nave` (centre (7400, 0, 0), radius 1500, reaching back to X 5900) overlap across the doorway, so the fog is doubled exactly at the threshold.
- **(3)** Narrow, high-scattering beams inside the volumetric-fog voxel grid (High uses a 16 px grid, Z 64; D-054) render blocky.

**Fix, two new tasks, P8-9a then P8-9b.**

**P8-9a: light-shaft meshes and material (technical-artist).** Blender headless (props pipeline), then import [EDITOR].
- **Moon direction:** read `DirectionalLight_1`'s rotation in the editor (expected pitch −38, yaw 35). Forward vector **d** ≈ (0.645, 0.452, −0.616). Use the read value everywhere below.
- **`SM_LB_Prop_LightShaft_Lancet`:**
  - The south lancet's clear outline (140 wide, sill Z 0 to apex Z 560, two-centred head as built in `NaveBay`), shrunk 5 % inward.
  - Extruded **obliquely along d** expressed in the window's local frame: the window plane is local XZ, the interior is local +Y.
  - Length t = 0…1800 cm along d. It may pass through the floor; depth fade hides that.
  - Open ends, single-sided, normals outward.
  - UV0: U = 0…1 around the outline, V = 0 at the window → 1 at t = 1800.
  - Pivot: the outline's bottom-centre at the window plane.
- **`SM_LB_Prop_LightShaft_RoofHole`:**
  - The `RoofSlab_Broken` hole outline (from `build_kit.py`; about X 250…750 × slope 294…987, in the slab's local frame), placed in world orientation for `Ch_Roof_S1` (roll 50, yaw 180, origin per the P8-5 report), shrunk 5 %.
  - Extruded along d to t = 3000.
  - Same UV and normal rules.
  - Pivot at the outline's centroid; record its world position.
- **`M_LB_LightShaft`** (Translucent, Additive, Unlit, two-sided, no depth test change):
  - Emissive = `Color` × `Intensity` × along-fade × edge-fade × DepthFade(`DepthFadeDist` 60) × CameraDepthFade(start 30, length 200) × (1 + `DustAmount` × (panning noise − 0.5)).
  - Along-fade = (1 − V)^`FadePower`.
  - Edge-fade = |dot(N, V_cam)|^`EdgePower`, so the beam is soft at its silhouette.
  - Params: `Color` (0.75, 0.80, 0.95), `Intensity` 0.15, `FadePower` 1.6, `EdgePower` 1.5, `DustAmount` 0.25, `DustScale` 0.004, `DustSpeed` 0.02. Use an engine noise texture (`/Engine/EngineMaterials/...` perlin) for the panning noise; record which.
  - MIs `MI_LightShaft_Window` and `MI_LightShaft_Roof`.
- Nanite off, NoCollision, CastShadow off.
- Renders, verify, import, commit.

**P8-9b: shafts that match the windows, and the fog fix (lighting-vfx) [EDITOR].**
1. **Delete** `Light_Chapel_Shaft_S1/S2/S3` and `Light_Chapel_Shaft_Roof` (the interior spots).
2. **Moonlight through the windows** (real shadows, so the light enters only through the openings).
   - For each south lancet S1/S2/S3 (window centre (X, −780, 730), X = 6500 / 7500 / 8500), place a SpotLight `Light_Chapel_Moon_S1/S2/S3` **outside**, at window centre − 1200·d (≈ (X − 774, −1322, 1469)), pointing along d.
   - Settings:
     - colour (190, 205, 235), Movable;
     - **CastShadows true** and **Cast Volumetric Shadow true**;
     - VolumetricScatteringIntensity **0.3**, low, to avoid blocky voxels; the beam look comes from the cards;
     - outer cone just covering the window (≈ 18°), inner ≈ 12°;
     - attenuation radius 3000;
     - intensity tuned so the floor patch reads (start 4000 lm, range 1000–15000).
   - **Every glass mesh** (`Ch_Glass_*`): CastShadow **false**, so the opaque glass doesn't block its own light. Read it back.
   - The lit patch on the floor and dais must be the window's shape and fall where the geometry says. For S1 it falls around (X + 471…1058, −460…−49).
   - **Move the 3 pool decals** onto those patches (rectangle about 720 × 160, yaw = heading of d ≈ 35°, centred on the patch) so the stained-glass colours sit on the real moonlight.
3. **Roof hole.**
   - `Light_Chapel_Moon_Roof`: a spot outside above `Ch_Roof_S1`'s hole, hole centroid − 2000·d, pointing along d, shadowed (+ volumetric shadow), scattering 0.3, cone covering the hole.
   - Its patch falls on the north side (around X 8200, low on the north wall) per the geometry. Move `Ch_Pool_Roof` to that patch.
4. **Shaft cards.**
   - `SM_LB_Prop_LightShaft_Lancet` at each south lancet: pivot at the window's inner glass plane (Y −789), bottom-centre at the sill (X, Z 450). `MI_LightShaft_Window`.
   - `SM_LB_Prop_LightShaft_RoofHole` at its recorded pivot, with `MI_LightShaft_Roof`.
   - All NoCollision.
   - Tune `Intensity` so the beams read softly (no hard edges, no blockiness) and the nave mean targets still hold.
5. **Fog at the doorway.**
   - `LFV_ChapelFront`: shrink and move it so it ends at least 50 cm outside the front wall: centre (5450, 0, 0), radius ≤ 500 (scale ≤ 1.0).
   - `LFV_Chapel_Nave`: keep it entirely inside: centre (7500, 0, 0), radius ≤ 1440 (scale 2.88). Lower its density so the interior haze matches what the player sees from the doorway.
   - **Measure the transition.** PIE Simulate captures looking +X from (5700, 0, 170), (5950, 0, 170), (6100, 0, 170), (6400, 0, 170) and (6800, 0, 170). For each, record mean luma and the luma of a 120 × 120 crop on the altar region.
   - Adjacent steps must not jump by more than 30 % in "fogginess", meaning crop contrast between the altar and its surroundings. Report the table, before and after.
   - If the jump persists, toggle each fog element (both LFVs, height-fog volumetric) to find the culprit and report.
6. **Re-check:**
   - the P8-7 luma targets (entrance, mid-nave, sacristy);
   - gates (a) clue, (b) bands, (d) coverage, (e) silhouette;
   - the courtyard regression (g6_04 / g6_14 means ±0.01).
7. **Recapture** `g8_02`, `g8_03`, `g8_04`, `g8_05`, `g8_10`, `g8_11`, plus a new `g8_14_window_shafts` from (7000, 300, 170) looking at (7300, −600, 600).
8. Save, run the suite (78/78), commit.
9. **The owner then re-measures `stat gpu` mid-nave.** Four shadowed spots add cost; budget 16.6 ms, last 11.79. Fallback if over: S2 and S3 spots shadowless with cards only.

**C5 (2026-10-26, owner note, to implement after P8-9 when the owner says resume): grime pass.** The owner: "everything is looking so clean and dirt-free in the chapel; based on the scene it should look dirty". The chapel has been abandoned for decades, its roof has partly fallen in, and it has been used for a ritual. It should read as dusty, damp, sooty and littered. The lead will expand this into exact values (as for C1–C4) before it starts. Planned scope:

1. **Floor dust and dirt in the joints.**
   - Reuse `M_LB_Surface`'s growth layer (`bGapGrowth`) with a **dust/dirt tint** instead of moss, in a new `MI_Chapel_Floor_Dirty`.
   - Dust gathers in the slab joints and at the edges; the aisle is less dirty (walked).
   - Add a grime macro-noise darkening.
   - Optionally the chapel walls go into `MPC_LB_GrowthObstacles` so the dust thickens along the wall bases (check the 48-box budget).
2. **Grime decals.** Generated deterministic textures (as for the chalk) or ambientCG CC0, with a registry row:
   - **soot plumes** above every candle cluster and the altar stands;
   - **damp streaks** under each lancet and below the roof hole, using the existing `Leaking006` set;
   - **mould and dark rising damp** along the wall bases;
   - **water staining and moss** under the broken S1 lancet and the roof hole;
   - **wax drips and pools** under candles;
   - **dirt drag marks and footprints** around the ritual circle;
   - **broken-glass glints** under S1.
3. **Debris scatter.** Dead leaves blown in under the roof hole and the broken lancet (the `LeafSet030` dead-leaf atlas as small cards or decals), straw and twigs, stone grit and dust piles in the corners, plaster fragments, and a few more slate chips. All NoCollision, and kept out of the puzzle zone and the aisle-route lanes.
4. **Surfaces.**
   - Dust on horizontal surfaces: pew seats, the altar mensa, the sills, the lectern. This is a world-up dust blend, as a new static switch on `M_LB_Surface` or a dust MI variant. Measure the recompile cost.
   - Darker, dirtier pew wood.
   - The clue plaque, puzzle candles and puzzle BPs stay untouched (R-33).
5. **More cobwebs** (the pack's `M_Cobweb`) on the trusses, window splays, pews and the lectern.
6. **Checks:**
   - lane check, suite, captures;
   - darkness targets re-measured (grime darkens the floor; keep the means in range);
   - readability gates (a) and (b) unchanged;
   - the owner re-checks GPU if many decals are added.

**C5-detail (2026-10-26, lead expansion of C5): grime pass, as two tasks.**

The GPU after P8-9b was 15.27 ms; P8-9c trims the moon spots first. The grime pass must stay within budget: about 45 decals, cheap material switches, and the owner re-measures at the end.

**P8-10a: grime materials and textures (technical-artist) [EDITOR].**

1. **Generated decal textures.** Extend `Tools/textures/gen_chapel_textures.py` (seeded; record the seeds), output to `ExternalAssets/Generated/chapel/`. All RGBA, A = opacity.

   | Texture | Size | Content |
   |---|---|---|
   | `T_LB_Decal_Soot_A`, `_B` | 512x1024 | Vertical soot plume, densest at the bottom (alpha 0.85), fading and widening upward with turbulent noise; colour (0.02, 0.02, 0.02) |
   | `T_LB_Decal_Mould_Band` | 1024x256 | Rising-damp band: dark green-black (0.05, 0.06, 0.04) at the bottom, an irregular noisy top edge, blotchy alpha 0.4-0.8 |
   | `T_LB_Decal_WaterStain` | 1024^2 | Irregular stain with 2-3 tide-mark rings: edges darker brown (0.10, 0.08, 0.06), centre lighter, alpha 0.3-0.7 |
   | `T_LB_Decal_WaxDrips` | 512^2 | 5-8 creamy (0.80, 0.74, 0.60) splats and run-drips, alpha 0.9 |
   | `T_LB_Decal_DragMarks` | 1024x512 | Two parallel scuffed drag trails plus scattered simple boot-sole prints (invented shapes): darker dirt (0.12, 0.10, 0.08), alpha 0.5 |
   | `T_LB_Decal_LeafLitter_A`, `_B` | 1024^2 | 40-80 leaf cells sampled from `ExternalAssets/Incoming/ambientcg-LeafSet030/` (Color + Opacity), random rotation and scale 0.6-1.2, darkened x0.7 |
   | `T_LB_Decal_DustDrift` | 1024^2 | Soft grey dust drift for corners and wall bases: (0.38, 0.36, 0.33), alpha falling off radially from one corner of the texture |

   Previews go to `Docs/ArtTest/chapel/tex_grime_*.png`.
2. **Import and decal MIs.**
   - Import into `/Game/LastBell/Environments/Chapel/Textures/` (sRGB colour, alpha kept).
   - Decal MIs on the existing `M_LB_Decal` (read its params first): `MI_Decal_Soot_A/B`, `MI_Decal_Mould`, `MI_Decal_WaterStain`, `MI_Decal_WaxDrips`, `MI_Decal_DragMarks`, `MI_Decal_LeafLitter_A/B`, `MI_Decal_DustDrift`.
   - Reuse the existing `MI_Decal_Leaking006_Wall` for damp streaks.
   - Thumbnails.
3. **`M_LB_Surface`: new static switch `bTopDust`** (default **false**, group "TopDust").
   - Params: `DustColor` (0.40, 0.38, 0.34), `DustAmount` 0.6, `DustUpThreshold` 0.65, `DustUpSharpness` 5, `DustNoiseScaleCm` 80, `DustNoiseContrast` 1.5, `DustRoughness` 0.95.
   - Mask = saturate((WorldNormal.z - DustUpThreshold) x DustUpSharpness) x noise term (world-space value noise, as the puddle mask uses, at `DustNoiseScaleCm`, contrast-shaped) x DustAmount.
   - Apply after the base and growth layers, **before** the puddles:
     - BaseColor -> lerp to DustColor;
     - Roughness -> lerp to DustRoughness;
     - Normal -> lerp toward (0, 0, 1) by 0.5 x mask.
   - **One recompile.** Regression with the switch off: same-session A/B (MCP_NOTES) on `MI_Kit_Floor`, `MI_Kit_Masonry`, `MI_Kit_Cliff` and `MI_Medieval_Blocks_03`, <= 2/255 mean difference.
4. **Material instances.**
   - `MI_Chapel_Floor_Dirty`: child of `MI_Chapel_Floor`, with `bGapGrowth` on and `GrowthColorTex` / `GrowthNormalTex` = `T_Brown_Mud_03_BC` / `_N` (in `/Game/LastBell/ArtTest/Materials/Brown_Mud_03/`).
     - Use the roughness input the master expects. If it needs a plain roughness map and only ARM exists, use the master default and record it.
     - `GrowthTint` (0.55, 0.50, 0.44), `GrowthLevel` 0.50, `GrowthSharpness` 10, `GrowthNoiseScaleCm` 250, `GrowthNoiseContrast` 1.4, `GrowthNoiseAmount` 0.45, `WallGrowthWeight` **0**. The chapel walls are not in `MPC_LB_GrowthObstacles`; corners and wall bases get DustDrift decals instead.
     - Also `bTopDust` on, with DustAmount 0.35, so the slab tops get a light dusting.
   - `bTopDust` on, with the defaults, in:
     - `MI_Chapel_Wood_Old` (pews, trusses, rail, lectern, purlins, rafters);
     - `MI_Chapel_Masonry_Interior` (sills, string course, plinth tops; vertical faces are unaffected);
     - `MI_Sacristy_Table_Old`.
   - New `MI_Chapel_Trim_Dusty`: child of `MI_Kit_Trim`, `bTopDust` on. **`MI_Kit_Trim` itself is shared with the courtyard and must not change.**
   - LOOK and capture (PIE Simulate): pews, altar, sills and floor. Dust must read on the up-facing surfaces only.
5. Commit after each block (textures, master, MIs).

**P8-10b: grime placement (environment-designer) [EDITOR].**

1. **Swap MIs:**
   - `Ch_Floor_B1..B3` and `Sa_Floor` -> `MI_Chapel_Floor_Dirty`;
   - `Ch_Altar`, `Ch_Dais`, the 4 corbels and the 2 statue plinths -> `MI_Chapel_Trim_Dusty` (read the slot first).
2. **Decals.** DecalActors. Decal size = half-extent; depth <= 20 on floors, <= 15 on walls, so they don't paint props.
   - **Soot** (`MI_Decal_Soot_A/B`, alternating), on walls above lit clusters:
     - east wall inner face (X 8960) above the altar stands: centre (8960, +-430, 420), size 130 x 320;
     - south wall above the statue holder: (6300, -750, 330), 110 x 260;
     - sacristy south wall above the table: (8300, -1500, 300), 100 x 220;
     - each lancet reveal top N1/N2/S2/S3 above the sill candles: centre (X, +-760, 560), 70 x 160.
   - **Damp streaks** (`MI_Decal_Leaking006_Wall`), under each lancet on the inner face, from Z 440 down to Z 60:
     - N1, N2 at Y 750; S1, S2, S3 at Y -750;
     - centre X = the window centre, size 150 x 380;
     - plus two on the south inner face under the roof hole: (6350 / 6650, -750, 700), 200 x 600.
   - **Rising damp** (`MI_Decal_Mould`), along every interior wall base, Z 0-90:
     - nave north (X 6060-8960) as three 1000-long decals;
     - nave south (skipping the door X 8440-8560);
     - west front inner face (skipping the door Y -60..60);
     - east wall (skipping Y -150..150 under the altar);
     - sacristy walls (skipping its doors).
   - **Water stain** (`MI_Decal_WaterStain`):
     - floor under the roof hole: (6500, -420), 500 x 400;
     - under S1: (6500, -690), 260 x 140.
   - **Wax drips** (`MI_Decal_WaxDrips`), 30 x 30:
     - at each of the 5 ritual candles;
     - 60 x 60 at each altar stand foot;
     - 40 x 40 at the statue holder;
     - 20 x 20 on the sacristy table under its holder (top-down, depth 5).
   - **Drag marks** (`MI_Decal_DragMarks`): (6550, 0) and (7050, 0), yaw 0, each 300 x 60 half-extents, i.e. from the door to the ritual circle.
   - **Leaf litter** (`MI_Decal_LeafLitter_A/B`):
     - 3 under the roof hole within X 6300-6900, Y -650..-150, each 150 x 150 half-extents;
     - 1 under S1 at (6550, -620);
     - 1 inside the door at (6150, 0), 120 x 100.
   - **Dust drifts** (`MI_Decal_DustDrift`): nave corners NW (6060, 750), NE (8960, 750), SW (6060, -750), SE (8960, -750), and the 4 sacristy corners; each 120 x 120, rotated so the dense corner of the texture sits in the room corner.
3. **Debris** (NoCollision; outside the aisle-route lanes):
   - 3 x `SM_LB_CC0_DryBranchesMedium01` at scale 0.5-0.8 under the roof hole;
   - 8 x `SM_LB_Kit_Rubble_Chunk_S` at scale 0.2-0.35 with `MI_Chapel_Rubble` at wall bases near the corners and under the hole;
   - 2 more `SM_LB_Prop_SlateShards_A`.
4. **Cobwebs.** 8 more pack cobweb cards (`MI_Cobweb_Dungeon`):
   - 2 per truss at the collar/brace junction;
   - the tops of the N1 and N2 window splays;
   - between the back and end panel of `Ch_Pew_N3` and `Ch_Pew_S3` (scale 0.4);
   - one on the lectern.
5. **Exclusions:**
   - **No decal box may intersect the puzzle zone** (X 8550-8830, |Y| <= 260, Z 0-250), the clue plaque (X 8688-8812, Y 742-750, Z 300-544), or any `BP_PuzzleCandle`.
   - No decal on the altar's top or front, except the existing chalk sigil.
   - Debris stays out of the aisle (Y -200..200, X 6060-8350) and at least 60 cm from all WalkPath segments.
6. **Checks:**
   - lane check (append a section);
   - collision read-back on the debris;
   - the suite with the map saved;
   - captures `g8g_01..08` (entrance, mid-nave, roof-hole floor, sacristy, pews close, altar close, a south lancet wall close, a corner close);
   - the B2 luma on entrance, mid-nave and sacristy, where a darker floor is expected. Accept an entrance mean >= 0.03; otherwise raise `Light_Chapel_Statue` or the S1 moon patch slightly and report;
   - gates (a) and (b) unchanged.
7. Commit.
8. **The owner re-measures GPU.** If it's over 16.6 ms, halve the decal count (drop the mould band on the north wall first).
