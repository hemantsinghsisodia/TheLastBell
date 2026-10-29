# Phase 9: Crypt art (P9)

Branch `claude/phase-09-crypt` (from `main` c1d63b0). The lead plans (D-048); every implementer is spawned with `model: "sonnet", effort: "high"`. Exact placements follow in amendment **D1**, written after the P9-2 survey has measured the Dungeon pack's architecture pieces.

## Owner choices (2026-10-27)
- **Architecture: the Dungeon pack's own pieces**: walls, arch, pillar, roof, ground, bars and door. The owner migrates them per `Docs/ArtTest/crypt/fab_picklist_p9.md`.
- **Ossuary: bone-lined niches.** Walls of stacked skulls and bones in burial niches, a few sarcophagi, bones spilling onto the floor.
- **Water: standing water plus a black pit.** Ankle-deep dark water with ripples along the flooded passage, black water in the pit, and wet, dripping walls.
- **Darkness: very dark, the player's candle leads.** Darker than the chapel, with a few torches and candle niches, and cold moonlight through iron ceiling grates.

## Current greybox (`L_Monastery`, folders `Crypt`, `Gameplay/Crypt`, `Lighting/Crypt`)
- **Coordinates:** world cm. The floor is Z −600 (slabs `CryptFloor_0..3` at Z −640…−600). The solid "rock" blocks `Rock_000..016` (`StaticMeshActor_125..141`) span Z −600…−40. Open space between them forms the crypt. The chapel floor sits above part of it (Z 0).
- **Spaces** (derived from the rock blocks):

  | Space | Extent | Notes |
  |---|---|---|
  | Sacristy stair | X 6800–8000, Y −1300…−900 | 40 steps `Stair_SacristyDown_00..39`; Z −600 at X 6800 up to 0 at X 8000 |
  | Landing | X 6300–6800, Y −1300…−900 | |
  | West corridor | X 6300–6600, Y −2500…−800 | widens to X 6800 at Y −1400…−1300 |
  | South corridor | X 6300–7500, Y −2500…−2200 | |
  | **Ossuary** | X 7500–9000, Y −2900…−2000 | |
  | **Flooded passage** | X 9000–10000, Y −2460…−2100 | the pit X 9300–9800, Y −2300…−2100, floor Z −900; the ledge Y −2460…−2300 |
  | **Chain chamber** | X 10000–11500, Y −2500…−1500 | |
  | Loop | around the pillar block `Rock_008` (X 10300–11200, Y −1500…−1100) | corridors X 10000–10300 and 11200–11500; north corridor Y −1100…−700 |
  | Exit stair | X 10500–10800, Y −700…500 | `Stair_CryptUp_00..39`; up to Z 0 at Y 500, the cloister |

- **Gameplay** (never moved or changed unless a step says so):
  - `Trig_CryptEntered`, `CP_Crypt`, `Kill_Pit` (BP_KillVolume), `CP_Crypt_Mech2`;
  - `Rubble_StairsBack` (BP_TagVisibility, appears on Ritual.2), `Gate_CryptExit` (BP_TagVisibility);
  - `Clue_Diagram` (BP_EngravedDiagram), `Lever_A/B/C` (BP_DialLever, on `Rock_008`'s south face Y −1500);
  - `Crank_Winch` (BP_TagInteractable on `Plinth_Crank` in the ossuary), `Winch_Ritual2` (BP_RitualMechanism at (10800, −2000));
  - the AI markers (`LBPatrolPoint_0..6`, `LBSearchPoint_*` and `LBWardenSpawnPoint_0` in the crypt);
  - the WalkPaths `SacristyToCrypt`, `FloodedLedge` and `CryptToCloister`;
  - the railings `Rail_Sac_*` and `Rail_Up_*` at ground level.
- **Greybox props:** `Prop_Crypt_0..5` and `Plinth_Crank`. **Lights:** `Light_Crypt_0..13` (PointLight_29..42).

## Constraints
- **The Warden paths through the crypt** (D-038: capsule radius 42 / half-height 110, nav agent 42/220; visual 2.9 m, stoops).
  - Every corridor keeps **≥ 180 cm clear width**. Keep the current widths (300–400 cm) by building walls on the rock faces.
  - The ceiling clear height is **≥ 260 cm** everywhere the Warden or player paths.
  - The navmesh must rebuild valid; the Warden reachability tests must pass.
- **The pit ledge stays a 1–1.6 m ledge.** `Kill_Pit`, the FloodedLedge WalkPath and the KillVolume behaviour stay exactly as they are.
- **Puzzle readability:** the engraved diagram and the three levers' position marks must stay readable at 2 m by candlelight.
- Gameplay and AI tests: the suite (78/78), all WalkPath PASS, RouteBot Success, and the Warden AI tests.
- GPU ≤ 16.6 ms at High in the crypt (owner measures). Interior lights are shadowless unless a step says otherwise.
- Everything else as in P8 §0: explicit saves, the editor via `Tools/mcp/ue.py`, captures in PIE Simulate, commits only on this branch.

## Tasks
1. **P9-0 (lead):** this plan, the pick list, decisions D-067…, the Phase 9 table, risks.
2. **P9-0b (owner):** migrate the pick list from LB_FabStaging.
3. **P9-1 (asset-curator):** CC0 downloads:
   - root clusters (Poly Haven `root_cluster_01` is already downloaded, plus `root_cluster_02`);
   - a water normal map (ambientCG);
   - wet stone or a drip decal if needed.
4. **P9-2 (technical-artist, editor read-only + relocation):** relocate the new Dungeon pieces into `/Game/LastBell/ThirdParty/Fab/Dungeon/` (merging duplicates), then **measure** every architecture piece: bounds, pivot, grid size, materials, collision. Also survey the crypt BPs (diagram, levers, winch, crank, TagVisibility rubble and gate, KillVolume) and the AI markers.
5. **D1 (lead amendment):**
   - exact placements of walls, roof and floor on the measured grid along every rock face;
   - arches at the chamber entries;
   - ossuary niches;
   - grates;
   - water planes;
   - the stair treatment;
   - roots;
   - the dressing and light lists.
6. **P9-3 (technical-artist):** our own pieces only where the pack has none:
   - ossuary niche units in the pack's stone material;
   - stair and step pieces matching the existing steps' collision;
   - the water surface mesh and `M_LB_Water`;
   - a sarcophagus;
   - root cards if needed.
7. **P9-4:** materials and imports. **P9-5:** structure. **P9-6:** dressing (ossuary bones as ISM rows, sarcophagi, chains, roots, water, debris, grime). **P9-7:** lighting (very dark; torches, candle niches, moon grates with shafts and cards; fog). **P9-8:** QA, docs, owner GPU and playtest. Then "PHASE 9 READY FOR YOUR REVIEW".

---

## Amendment D1 (2026-10-27, lead): exact crypt layout, pieces, materials, dressing, lighting

Inputs: the P9-2 measurements and survey (`Docs/ArtTest/crypt/survey_p9.md`, captures `kit_test_*`). Every placement below comes from **`Tools/crypt/gen_crypt_layout.py`**, which writes:
- `Docs/plans/p9_d1_layout.json`: the machine-readable list, one record per actor (label, mesh path, location, rotation `[pitch, yaw, roll]`, scale, collision, folder, expected AABB, extras);
- `Docs/plans/p9_d1_tables.md`: the same as tables;
- `Docs/ArtTest/crypt/d1_layout_plan.png` (and `.svg`): a top-down plan.

**Never hand-edit the JSON or the tables.** If a value must change, change the generator, re-run it (`python Tools/crypt/gen_crypt_layout.py`, exit 0 = no intrusion), and commit the generator and its outputs together. Placement scripts in P9-5/P9-6/P9-7 read the JSON. Label prefixes: `CA_` architecture, `CD_` dressing, `L_Crypt_` lights. (Never `CP_`: the checkpoints use it.)

### D1.0 Decisions (DECISIONS D-068 … D-071)

1. **D-068: visual shell over invisible greybox collision.**
   - The greybox shell stays as the collision:
     - `Rock_000..016`, `CryptFloor_0..3`;
     - `Pit_Floor`, `Pit_W/E/N/S`;
     - `Prop_Crypt_0..5`, `Plinth_Crank`;
     - the 80 stair blocks `Stair_SacristyDown_00..39` and `Stair_CryptUp_00..39`.
   - Its StaticMeshComponent becomes **not visible**, with collision unchanged. Navmesh, WalkPaths, RouteBot, Kill_Pit and the Warden routes therefore keep exactly the collision they were tested with.
   - All crypt art is **NoCollision**. There are only these exceptions:
     - the 6 ossuary pillars;
     - the skeleton stake;
     - the hanging open cage;
     - the winch frame;
     - the 4 restyled gameplay Blueprints (D-071).
   - A black, unlit **backdrop box** (5 slabs, open top) surrounds the crypt, so any gap shows black, not the sky dome.
   - Rule for the wall depth: the wall centre sits 75 cm into the rock. The stone face is then 0.5 cm proud to 11 cm behind the collision face, so the player never clips into stone.
2. **D-069: layout rules** (implemented in the generator).
   - **Walls:** wall runs on every rock face.
     - **Spacing:** pitch ≤ 626 with 15.2 cm overlap; X-scale chosen nearest to 1 (allowed 0.72–1.34). Short runs are anchored at scale 0.8 and extend hidden into the rock.
     - **Height:** Z-scale 1.194, so the top is at Z −1, inside the ground slab.
     - **Run ends:** +60 cm into inside corners; −30 cm at portals.
   - **Portals:** a pair of `SM_Arch` halves (one mirrored) at every junction between spaces (11 portals).
     - **Opening:** = the greybox corridor width (X-scale = width / 437.3).
     - **Height:** Z-scale 1.19 → clear crown Z −100, springing Z −255, top Z −1.5.
     - Portals close the gaps where vaults of different spaces meet.
   - **Vaults:** `SM_Roof` bays with the crown at Z −44 (shell top −41.6, under the slab).
     - **Corridor style:** across scale = (width + 178)/478.2, so the groins die into the walls as in the P9-2 test.
     - **Room style:** landing and ossuary; edges 15 cm into the walls.
   - **Ossuary:** a Romanesque crypt hall.
     - 3 × 2 bays; grid X 7485/8000/8500/9015 × Y −2915/−2510/−1985.
     - **2 free columns** at (8000, −2510) and (8500, −2510), plus 4 engaged columns on the niche walls.
     - Columns: `SM_Pillar` sunk to reach a new capital whose abacus top is at Z −330, with the vault corners (Z −339.8) buried in the abacus.
     - The interior node sits at Y −2510, so the end-wall nodes fall inside the J4/J5 portal legs.
   - **Chain chamber:** a **timber ceiling** (4 beams, boards, soil above, one iron moon grate) instead of a vault. The two interior columns a 3 × 2 vault needs would sit on `WalkPath CryptToCloister` (11100, −2000) and `Search_Crypt_13` (10500, −2150).
   - **Stairs:** visual 40-step flights over the invisible greybox steps. Flat ashlar soffits (`SM_Wall_00` laid face down) under the slab; stone lintels where the soffits meet the open stair shafts.
3. **D-070: custom pieces, water, grates, roots, decals.**
   - **Custom pieces (P9-3):** only where the pack has none (list in D1.3).
   - **Candle niches:** the pack's `SM_Wall_01` built-in niche, on 5 chosen wall pieces.
   - **Moon grates are faked; no hole in the world ground slab:**
     - in the vaults, the pack `SM_Dungeon_toplock` collar hangs upside down from the crown, with an unlit night-sky disc above the grating;
     - in the chain chamber, `SM_Bars` lies flat in a missing board cell, with a sky plane above.
   - **Water:** opaque **masked** planes (no translucency) with a dithered edge fade where water spreads into a room. The pit gets black still water.
   - **Roots:** procedural hanging roots using the bark of the existing `SM_LB_Prop_DeadTree_A` (tileable). The scanned Root Cluster 02 and Pine Roots are **not used**: their textures are chunk atlases, not tileable bark. Registry rows: "not used (D-070)".
   - **Wall wetness:** Leaking004 (has opacity) plus the existing Leaking006. **Leaking012C is not used** (registry: not used).
   - **Nanite:** turned **on** for the pack bones used in quantity (`SM_Skull_00/01/02`, `SM_Skeleton_Pile_00..05`, `Arm_00/01`, `Leg_00/01`, `Pelvis`). The ossuary places ~240 bone actors.
4. **D-071: puzzle props get art through child Blueprints** (precedent D-051, the chapel key).
   - `Crank_Winch` → `BP_TagInteractable_CryptCrank` (an iron crank).
   - `Gate_CryptExit` → `BP_TagVisibility_CryptGate` (a portcullis).
   - `Rubble_StairsBack` → `BP_TagVisibility_CryptRubble` (a jammed collapse).
   - `Winch_Ritual2` → `BP_RitualMechanism_CryptWinch` (stone pedestal + wooden capstan).
   - Each child keeps the parent logic, the label, the tags and **a UCX collision identical to the greybox block**.
   - The levers (`BP_DialLever`) and the clue plaque stay **unchanged** for readability. They get only a NoCollision stone frame around the plaque and candles beside the lever row.
   - The portcullis still vanishes instantly (no lift animation); that is a later polish item, not in Phase 9.

### D1.1 Spaces and portals (reference)

| Space | Greybox extent | Ceiling | Floor |
|---|---|---|---|
| L landing | X 6300–6800, Y −1400…−800 | 1 room-style vault bay | tiles |
| WC west corridor | X 6300–6600, Y −2500…−1400 | 2 corridor bays | tiles |
| SC south corridor | X 6600–7500, Y −2500…−2200 | 2 corridor bays | tiles |
| OS ossuary | X 7500–9000, Y −2900…−2000 | 6 room-style bays on 2 free + 4 engaged columns | tiles |
| FP flooded passage | X 9000–10000, Y −2460…−2100 | 2 corridor bays (across 360) | water planes (no tiles) |
| CC chain chamber | X 10000–11500, Y −2500…−1500 | timber: beams, boards, soil, grate G3 | tiles |
| LW / LE loop | X 10000–10300 / 11200–11500, Y −1500…−1100 | 1 corridor bay each | tiles |
| NC north corridor | X 10000–11500, Y −1100…−700 | 3 corridor bays (across 400) | tiles |
| SS sacristy stair | X 6800–8000, Y −1300…−900 | soffit X 6830–7400, shaft above X 7400–8000 | stair flight |
| ES exit stair | X 10500–10800, Y −700…500 | soffit Y −670…−100, shaft above Y −100…500 | stair flight |

Portals: J1 WC↔L, J2 L↔SS, J3 WC↔SC, J4 SC↔OS, J5 OS↔FP, J6 FP↔CC, J7/J8 CC↔LW/LE, J9/J10 LW/LE↔NC, J11 NC↔ES. `Gate_CryptExit` stands inside J11.

`R008`, the pillar block that carries the puzzle wall, gets walls on all four faces:
- each corner is covered by a portal leg;
- the puzzle-wall stone face (`CA_Wall_N_CC_0`) sits behind the plaque and lever backplates (Y −1500.5 … −1489).

### D1.2 Gameplay invariants (every task)
- No gameplay actor moves except the 4 Blueprint swaps in P9-6b, which keep the label, transform footprint, variables and collision box.
- Nothing with collision within 60 cm of a WalkPath segment or within 150 cm of an AI patrol, search or spawn point. The generator checks the free columns; P9-6a's lane check covers the rest.
- No art may block the `Interaction` or `Visibility` trace to a lever, the plaque, the crank, the winch, the gate, or a checkpoint. All dressing near them is NoCollision.
- The Kill_Pit box (X 9300–9800, Y −2300…−2100, Z −900…−620) stays untouched. The pit water at Z −650 is inside it.

### D1.3 P9-3: custom pieces (technical-artist, Blender headless, **no editor**)

**Pipeline**
- Add builders to `Tools/blender/props/build_props.py` with the prefix `SM_LB_Crypt_` (the crank uses `SM_LB_Prop_`).
- Run with `--only Crypt Crank --tag P9`. Outputs go to `SourceArt/Props/Procedural/Crypt/`: FBX, `LB_Props_P9.blend`, `props_report_P9.json`.
- Extend `verify_props.py`: expected dims ±1 cm, slot names, UCX count, and the ray checks below. The pass count rises from 49 to 49 + the number of new pieces.
- Render with a new `render_p9.py`: Workbench views of every piece, plus one Cycles view each of the ossuary bay, the portcullis and the roots. Output: `Docs/ArtTest/crypt/p9_*.png`.

**Conventions**
- 1 BU = 1 cm; kit UV of 1 UV = 100 cm unless stated; vertex colour white.
- Slots: `MAT_Stone`, `MAT_Wood`, `MAT_Iron`, `MAT_Charred`, `MAT_Bark`.
- Pivot = bottom-centre unless stated otherwise.
- Seeds as listed; seeded and reproducible.
- **LOOK pass:** iterate until each render reads as described; record each iteration in the report.

| # | Mesh | Size (x × y × z) | Pivot | Slots | UCX | Build |
|---|---|---|---|---|---|---|
| A | `SM_LB_Crypt_OssuaryBay_500x599` | 500 × 96 × 599 | x centre, **y 0 = front face** (local +Y = into the room), z 0 bottom | Stone | none | Body x ±250, y −90…0, z 0…599, closed on all sides. Two niches, each x −170…170, recessed to y −60: tier 1 z 45…135, tier 2 z 185…275; inner corners r 2. Sill bands x ±185, proud y 0…+6, z 39…45 and 179…185. Lintel bands x ±190, y 0…+6, z 135…147 and 275…287. Plinth band z 0…40, proud 4. Top edges of the bands chamfered 1.5. `stone_finish` ±1.2 on the front (seed 9301); 3–5 chips per niche edge. ≤ 12k tris |
| B | `SM_LB_Crypt_Capital_A` | 170 × 170 × 55 | bottom-centre | Stone | none | Bell: an octagonal frustum, flats facing ±X/±Y, apothem 70 at z 0 rising to 84 at z 33, concave profile from 4 rings. Abacus: 170 × 170, z 33…55, bottom edge chamfer 4, top edges 1.5. Chips seed 9302. ≤ 3k tris |
| C | `SM_LB_Crypt_Stair40_300` | 1200 × 300 × 600 | **x 0 = riser face of step 0**, y centre, z 0 floor | Stone | none | 40 steps along +X: step n covers x 30n…30n+30, tread top z = 15(n+1). Closed sawtooth prism down to z 0; sides closed; back face at x 1200. Wear: tread centre third dips ≤ 1.0 (smooth); nosing r 2.5; 25 % of nosings chipped 6–14 wide, 2–3 deep (seed 9303). Ray check: a downward ray at (30n+15, 0) hits 15(n+1) ±1.2 for all n. ≤ 25k tris |
| D | `SM_LB_Crypt_Sarcophagus_A`, `_B` | 300 × 120 × 72 | bottom-centre | Stone (+Charred in B) | none | Plinth z 0…8 (300 × 120). Body z 8…58 (290 × 110), with 2 cm recessed round-headed panels: 5 per long side (44 × 32), 2 per short side. Lid z 58…70 (300 × 120), top edges chamfered 3. Raised cross z 70…72: shaft 190 × 14 along X, arms 70 × 14 at x +50. **B:** lid 280 long, shifted +10 in X and rotated 3° about Z; dark cavity x ±135, y ±45, z 20…58 (Charred inside) shows at the −X end; one lid corner chipped (seed 9304). Bounds must stay within x ±150, y ±60, z 0…72 |
| E | `SM_LB_Crypt_BoneBin_200x100x60` | 200 × 100 × 60 | bottom-centre | Stone | none | Open-top chest: walls 8 thick, solid up to the inner floor at z 30; top edge chamfer 1.5; chips seed 9305 |
| F | `SM_LB_Crypt_Block_100` and `SM_LB_Crypt_Block_100_C` | 100 × 100 × 100 | `_100` bottom-centre; **`_C` centre** | Stone | 1 box 100³ (both) | Weathered block: edge chamfer 3, face noise ±0.8, chips on 3 edges (seed 9306). `_C` is identical geometry with the pivot at the centre (for the winch pedestal) |
| G | `SM_LB_Crypt_Corbel_A` | 50 × 55 × 45 | **back plane y 0**, x centre, z 0 bottom; projects +Y | Stone | none | Three stepped courses: z 0…15 depth 30, 15…30 depth 42, 30…45 depth 55; chamfer 1.5 |
| H | `SM_LB_Crypt_Beam_35x45x1120` | 35 × 1120 × 45 | bottom-centre, **length along Y** (authored horizontal) | Wood | none | Adzed faces (0.6 cm low-frequency waviness); 3 lengthwise checks on the visible faces (seed 9307) |
| I | `SM_LB_Crypt_Boards_300x250`, `_Broken` | 300 × 250 × 5 | bottom-centre (z 0 = board undersides) | Wood | none | 10 boards along X; widths 22–27 with 1–2 cm gaps (seed 9308); warp ±0.6; ragged ends ±2. **Broken:** boards 3 and 4 missing; board 6 snapped at x +40 with its +X part hinged 25° down (lowest point ≥ z −60) |
| J | `SM_LB_Crypt_RootsHang_A`, `_B`, `_C` | ~80 × 80 × 180 / ~90 × 90 × 240 / ~60 × 60 × 120 | **top-centre** (z 0 = attachment, hangs to −180/−240/−120) | Bark | none | Seeded bpy branching (9310/9311/9312): 4/6/3 strands from a 12 cm knot. Base radius 4.5/5/3 tapering to 0.4; S-curves with lateral drift ≤ 25. Level 2: 2–4 branches per strand, 30–60 long, r 1.5→0.3. Level 3: a few rootlets 10–20 long, r 0.4→0.15. UV: 1 tile per 60 cm along the length, 0…1 around. 6–12k tris each |
| K | `SM_LB_Crypt_Portcullis_300x60x560` | 300 × 60 × 560 | bottom-centre | Iron | **1 box x ±150, y ±30, z 0…560** (= the greybox gate) | 9 square bars 6 × 6 at 32.5 spacing across x ±130, from spike tips at z 0 (12 cm points) up to z 560. 7 flat bars 8 × 3 at z 60/130/200/270/340/410/480. Rivet domes at the crossings; side rails 8 × 8 at x ±145. Lattice within y ±4; pitting noise. ≤ 8k tris |
| L | `SM_LB_Crypt_RubbleFill_100x400x560` | 110 × 420 × 560 | bottom-centre | Stone, Wood | **1 box x ±50, y ±200, z 0…560** (= the greybox rubble) | 40–60 chipped blocks of 25–70 cm (seed 9313), jammed within x ±55, y ±210, z 0…560. A broken beam 35 × 30 × 380 lies diagonally across the −X face (splintered end). The −X face stays near-vertical (no scree beyond x −55). ≤ 40k tris |
| M | `SM_LB_Prop_Crank_A` | ~42 × 14 × 14 | bottom-centre, lies flat | Iron, Wood | **1 box 44 × 16 × 16** | Square socket boss 8 × 8 × 12; flat arm 38 × 4 × 2.5 at 90° to the socket; wooden handle r 2 × 12 perpendicular at the arm's end |
| N | `SM_LB_Crypt_CapstanDrum_80x50` | 110 × 110 × 50 | **centre** (z −25…25) | Wood, Iron | **1 box x ±35, y ±35, z ±25** | Drum: 16 sides, r 34, height 50, bevelled. Iron bands r 35 at z −21…−17 and 17…21; top boss r 10. Two capstan bars (wood 5 × 5 × 110) crosswise through square holes at z +13. They make the 90° turn visible |
| O | `SM_LB_Crypt_PlaqueFrame_270x195` | 270 × 14 × 195 | **back plane y 0**, x centre, **z centre** | Stone | none | Frame: outer 270 × 195, opening 250 × 175, depth 14 (y 0…14); 3-step ovolo moulding; chipped corners (seed 9314) |
| P | `SM_LB_Crypt_WinchFrame` | 260 × 90 × 250 | bottom-centre | Wood, Iron | **4 boxes:** posts 20 × 20 × 250 at x ±110; sole plates 20 × 90 × 10 | Posts 20 × 20 × 240 at x ±110, y 0, on sole plates 20 × 90 × 10 (along Y). Braces 12 × 12 from each post at z 140 down to the sole-plate ends. Top beam 20 × 20 × 260 at z 230…250. Drum r 22, length 180 (x ±90), axle z 170, 6 iron bands. Chain coil on the +X half: torus links, 5 turns. Iron crank arms 30 long at both ends. ≤ 25k tris |

**Texture**
- New `Tools/textures/gen_crypt_textures.py` (seeded 9320) writes `ExternalAssets/Generated/crypt/T_LB_Water_Ripple_N.png`, a 1024² tileable DirectX normal map:
  - 6 wave trains, wavelength 18–60 px, random directions, amplitude falling with frequency;
  - plus wraparound value noise.
- Seam check: edge rows/columns differ ≤ 2/255.
- Preview: `Docs/ArtTest/crypt/tex_water_ripple.png`.

**Report:** measured bounds and tris per piece; renders; verify count; commit "P9-3: crypt pieces".

### D1.4 P9-4: materials and imports (technical-artist, [EDITOR])

1. **Import.**
   - All P9-3 FBX go to `/Game/LastBell/Environments/Crypt/Meshes/`, with import settings per MCP_NOTES.
   - Nanite **on**: A, B, C, D, H, L, P, J.
   - Nanite **off**: E, F, G, I, K, M, N, O.
   - Keep only the UCX hulls.
   - The ripple texture goes to `/Game/LastBell/Environments/Crypt/Textures/` (normal map compression, sRGB off).
2. **Darken the pack MIs.**
   - First run `get_referencers` on `MI_Stone_00..03`, `MI_Stone_Wall_00` and `MI_Tiles`. They must be referenced only by the P9 meshes; report otherwise and stop.
   - Read the current values, then set:
     - `Brightness` × 0.5;
     - `Desaturation` + 0.25 (cap 0.6);
     - `Tint` × (0.86, 0.90, 0.86);
     - `Roughness` × 0.8 (damp).
   - On `MI_Tiles` (M_Tiles): `Brightness` × 0.5, `Roughness` × 0.8.
   - Record old → new.
   - Gate:
     - Setup: PIE Simulate in the `L_Test_ArtKit` throwaway area (never saved). Place `SM_Wall_00` beside a chapel kit wall (`MI_Chapel_Masonry_Interior`). Light both with one 2700 K, 300 lm shadowless point light at 150 cm.
     - Pass: the crypt wall's mean luma is 0.55–0.75 × the chapel wall's, and the crypt wall is less saturated.
3. **New MIs** in `/Game/LastBell/Environments/Crypt/Materials/`:
   - `MI_Crypt_StoneWA`: M_LB_Surface, `bWorldAlignedUV` on, `bUseARM` on.
     - **Textures:** the BC/N/AO_R_MT of the stone MI that covers the most area of `SM_Wall_00`. Check the per-slot triangle share and record it.
     - **Darkening:** match the darkened pack walls. In the same side-by-side capture, the mean luma must be within ±10 % of `SM_Wall_00`.
     - **`WorldTileSizeCm`:** tune from 250 so the block size matches the pack wall (capture side by side).
     - **Used by:** A, B, C, D, E, F, G, O and L's stone.
   - `MI_Crypt_Wood_Wet`: child of `MI_Prop_Wood_Weathered`. `BrightnessMul` × 0.6, `Wetness` 0.35, `RoughnessMin` 0.45. Used by: beams, boards, the winch frame, the capstan, the crank handle and the rubble beam.
   - `MI_Crypt_Iron`: child of `MI_Prop_Iron_Rusty`, `BrightnessMul` × 0.7.
   - `MI_Crypt_RootBark`: child of the MI on `SM_LB_Prop_DeadTree_A` slot 0, `BrightnessMul` 0.55, `Wetness` 0.3.
   - `MI_Crypt_Soil`: child of `MI_Prop_Earth`, `BrightnessMul` 0.5.
   - `MI_Crypt_Backdrop`: child of `M_LB_UnlitEmissive`, colour 0 (pure black).
   - `MI_Crypt_MoonSky`: child of `M_LB_UnlitEmissive`, colour (0.020, 0.028, 0.045). Tune the strength so the disc reads 0.06–0.12 luma in a capture.
   - `MI_LightShaft_Crypt`: child of `MI_LightShaft_Roof`, colour (0.62, 0.72, 1.0), intensity × 0.5.
   - `MI_Decal_Leaking004_Wall`: duplicate `MI_Decal_Leaking006_Wall` and swap in the Leaking004 textures (Color, Opacity, Roughness, NormalDX). Check the streak direction against `dl_Leaking004.png`.
4. **`M_LB_Water`** (`/Game/LastBell/Materials/Master/`): Masked, DefaultLit, one-sided, OpacityMaskClip 0.5.
   - **Surface:**
     - BaseColor = `WaterColor` (0.006, 0.008, 0.008);
     - Specular 0.5;
     - Roughness = `WaterRoughness` 0.04.
   - **Normal:** lerp(flat, blend of two panning samples of `RippleNormal` with their XY multiplied by `RippleNormalScale` (default 3, tune 2–5) and renormalized, `RippleStrength` 1.0). The generated map is subtle (max tilt 0.18, a limit of the seam requirement; P9-3). The samples use UV = WorldPos.xy / `RippleTileCm` (140):
     - sample 1 pans (0.010, 0.006)/s;
     - sample 2 uses UV × 0.43 and pans (−0.006, 0.009)/s.
   - **Edge fade:**
     - Parameters: `SizeXCm`, `SizeYCm`, `EdgeFadeXMinCm`, `EdgeFadeXMaxCm`, `EdgeFadeYMinCm`, `EdgeFadeYMaxCm` (0 = off).
     - Per side: dist = UV × size (or (1 − UV) × size), mask_side = saturate(dist / fade).
     - mask = product of the sides, then × (1 + `EdgeNoiseAmount` 0.45 × (noise(WorldPos.xy / `EdgeNoiseScaleCm` 90) − 0.5) × 2) where mask < 1.
     - OpacityMask = DitherTemporalAA(saturate(mask)).
   - **MIs:**

     | MI | Size (cm) | Settings |
     |---|---|---|
     | `MI_Crypt_Water_Flood_W` | 495 × 390 | `EdgeFadeXMinCm` 200 |
     | `MI_Crypt_Water_Flood_Ledge` | 510 × 173 | no fade |
     | `MI_Crypt_Water_Flood_E` | 395 × 390 | `EdgeFadeXMaxCm` 200 |
     | `MI_Crypt_Water_Pit` | 530 × 230 | `WaterColor` (0.002, 0.002, 0.003), `WaterRoughness` 0.02, `RippleStrength` 0.08, no fade |

   - **UV orientation check:** put `_Flood_W` on a test plane and confirm the fade is at its low-X end. If not, swap Min and Max in the MIs.
5. **Nanite** on for `SM_Skull_00/01/02`, `SM_Skeleton_Pile_00..05`, `SM_Skeleton_Arm_00/01`, `Leg_00/01` and `Pelvis` (D-070). Check that the courtyard and chapel uses still render (one capture each).
6. **Assign slot materials on the new meshes:** Stone → `MI_Crypt_StoneWA`, Wood → `MI_Crypt_Wood_Wet`, Iron → `MI_Crypt_Iron`, Charred → `MI_Prop_Charred`, Bark → `MI_Crypt_RootBark`.
7. **Wrap up:** thumbnails; registry rows (the P9-3 pieces; generated texture; Root Cluster 02 / Pine Roots / Leaking012C = not used); commit "P9-4".

### D1.5 P9-5: structure (environment-designer, [EDITOR])

1. **Placement script.**
   - Write `Tools/crypt/place_crypt.py` (uses `Tools/mcp/ue.py`):
     - it reads `Docs/plans/p9_d1_layout.json`;
     - it places every record of a chosen set of categories by `add_to_scene_from_asset`;
     - it sets location, rotation and scale in one call, then the label, folder, collision (`bodyInstance.collisionProfileName` + `bUseDefaultCollision=false`) and materials.
   - **Idempotent:** before placing a category, it deletes actors whose label starts with that category's prefix.
   - **Read-back:** after placing, read every actor's bounds and compare with `aabb_min/max` (tolerance 3 cm). For P9-3 pieces, first replace their design bounds in the generator with the P9-3 report's measured bounds, then re-run the generator.
   - **Mirrored halves:** for portals with a negative X-scale, confirm the bounds land as listed.
2. **Order:**
   1. **Backdrop.**
   2. **Hide the greybox:** `StaticMeshComponent.bVisible = false` on the actors listed in D-068.
      - Read back `bVisible` false and the collision profile unchanged.
      - `trace_world` straight down at (6550, −1100), (8250, −2450), (10750, −900), and at step 20 of each stair, must still hit at the greybox tops.
      - If `bVisible` does not persist, use actor `bHidden` (hidden in game) instead and record it.
   3. Walls, pit walls, portals, vaults, columns (pillars **BlockAll**, capitals NoCollision), ossuary bays, tiles, stairs, soffits and lintels, the chain-chamber ceiling, grates, water.
3. **Materials on placed actors:**

   | Actors | Material |
   |---|---|
   | `CA_Backdrop_*` | `MI_Crypt_Backdrop`; CastShadow off |
   | water planes | their MI from the record |
   | `CA_CC_Soil` | `MI_Crypt_Soil` |
   | sky disc / plane | `MI_Crypt_MoonSky`; CastShadow off |
   | pack meshes | keep their (darkened) slot MIs |
   | lintels and Block pieces | `MI_Crypt_StoneWA` |

4. **Gap pass:**
   - **Captures** (PIE Simulate, a temporary 3000 lm shadowless point light at the camera, removed after): in each of the 11 spaces, 4 views — up into the vault, along each wall line, and at each portal.
   - **Pass:** no black slit wider than 2 cm at vault/wall/portal junctions, and no backdrop or sky visible.
   - **Fixes:** move that vault ±10 cm or scale it +2 %, change the generator, and re-run. Record every fix.
5. **Checks:**
   - Save the map (explicit save).
   - Run the suite: 78/78, WalkPath.Monastery including SacristyToCrypt, FloodedLedge and CryptToCloister PASS, RouteBot.Monastery Success, the Warden crypt patrol and reachability tests.
   - Captures `p9s_01…10`, normal lighting with no temporary light: stair foot, landing, WC, SC, ossuary from J4, ossuary across, FP ledge, CC from J6, puzzle wall, NC toward the gate.
   - Commit.

### D1.6 P9-6a: dressing (environment-designer, [EDITOR]) · P9-6b: puzzle props (unreal-blueprint-engineer, [EDITOR])

**P9-6a**
1. Place categories `dress` and `decal` from the JSON:
   - collisions as recorded (BlockAll only on the stake, the cage and the winch frame);
   - materials: the pack meshes' own; P9-3 pieces per D1.4.
2. **Skulls:**
   - Capture one `SM_Skull_00`, `_01` and `_02` at yaw 0 to find the face direction. Set actor yaw = `face_yaw` + offset, with a separate offset per mesh. Record the offsets.
   - The front of every niche skull must look out of the niche (capture check per bay).
3. **Decals:** follow the MCP_NOTES conventions.
   - Verify one wall decal per orientation (±X, ±Y). If it doesn't show, add 180 to the yaw for that orientation and apply it to all of them.
   - No decal box may touch the clue plaque (X 10795–11045, Y −1515…−1500, Z −420…−240), a lever, or a candle niche's opening.
4. **Plaque frame** `CD_PlaqueFrame`:
   - Read the clue plaque's TextRender component bounds.
   - Place `SM_LB_Crypt_PlaqueFrame_270x195` at (10920, −1500, −330), yaw 180, so the back plane sits on the face line and the frame projects toward −Y.
   - Scale X and Z so the opening is at least the text bounds + 10 cm each side and at least the plaque (250 × 175).
   - NoCollision. Capture at 2 m: the text must stay fully visible.
5. **Lane check** (append a section to `Docs/ArtTest/crypt/lane_check_p9.md`):
   - Every collision-bearing piece (pillars, stake, cage, winch frame) must be ≥ 60 cm from every WalkPath segment and ≥ 150 cm from every crypt AI point.
   - The RouteBot approach points of the crank and winch (bounds + 120 cm, 4 sides) must not overlap WorldStatic.
6. **Wrap up:** save, run the suite (as D1.5), captures `p9d_01…12` (each niche bay pair, the sarcophagi, the bone bins, the chain chamber both ways, the winch, the cage, the flooded passage both ways, the puzzle wall at 2 m), commit.

**P9-6b** (follows the P7-FIX2 3h + P7F-4 procedure exactly)
1. **Create the 4 child Blueprints** in `/Game/LastBell/Blueprints/Interactables/`. Never edit the parents. The construction script sets the inherited mesh, materials and Interaction-channel Block (Mobility Movable where the parent's is):
   - **`BP_TagInteractable_CryptCrank`:** Mesh `SM_LB_Prop_Crank_A`. Instance at (8400, −2700, −530), yaw 30, scale 1.
     - Values from the survey: PromptText "Take crank", GrantedStateTags [State.Item.Crank], ConsumedStateTag State.Item.Crank, bSingleUse true, NoiseLoudness 0.2, UseStateTag State.Item.Crank, bHideOnUse true, bInspectable false, InspectableComp bKeepOnClose true.
   - **`BP_TagVisibility_CryptGate`:** Mesh `SM_LB_Crypt_Portcullis_300x60x560`. Instance at (10650, −670, −600), yaw 0.
     - triggerTag State.Ritual.2, bVisibleWhenTagPresent **false**, hideAfterSeconds 0.
     - Bounds check: X 10500…10800, Y −700…−640, Z −600…−40 (±2).
   - **`BP_TagVisibility_CryptRubble`:** Mesh `SM_LB_Crypt_RubbleFill_100x400x560`. Instance at (7050, −1100, −600), yaw 0.
     - triggerTag State.Ritual.2, bVisibleWhenTagPresent **true**, hideAfterSeconds 0.
     - Bounds check (UCX): X 7000…7100, Y −1300…−900, Z −600…−40.
   - **`BP_RitualMechanism_CryptWinch`:**
     - Pedestal mesh `SM_LB_Crypt_Block_100_C`.
     - Core mesh `SM_LB_Crypt_CapstanDrum_80x50` with Core's relative scale set to (1, 1, 1); Core keeps its relative location (0, 0, 75).
     - CoreMarker: visibility off (collision unchanged).
     - Instance at (10800, −2000, −550), yaw 0.
     - ritualTag State.Ritual.2, extraGrantedTags [State.Warden.Stage.4], turnYaw 90, turnDuration 1.5.
     - InteractComp: PromptText "Activate", DeniedPromptText "Something is missing", RequiredStateTags [Item.Crank, Dial.A.2, Dial.B.0, Dial.C.1], GrantedStateTags [Warden.Stage.4, Ritual.2], bSingleUse true, ConsumedStateTag State.Ritual.2, NoiseLoudness 1.
2. **For each swap:**
   - dump the old actor's properties to `Docs/ArtTest/crypt/<label>_before.json`;
   - spawn the child, set the values, delete the old actor, then apply the **same label** and folder;
   - dump `<label>_after.json` and diff. Only class, mesh, location Z / scale (crank, gate, rubble) and the Core scale may differ.
3. **Checks:**
   - compile every child with warnings as errors;
   - run the suite: 78/78, RouteBot.Monastery Success (it takes the crank, sets the dials, turns the winch), the puzzle functional tests and the save tests (crypt levers found);
   - captures: closed gate, crank on its plinth, the winch.
   - In PIE Simulate, toggle the rubble's and gate's visibility on the PIE-world instances only, never in the editor world, to capture the "after ritual" state.
4. Commit.

### D1.7 P9-7: lighting (lighting-vfx, [EDITOR])
1. **Remove the greybox lights:** delete `Light_Crypt_0..13`.
2. **Place the 16 lights** from the JSON (category `light`, folder `Lighting/Crypt`):
   - **Torch fires:** `PS_Fire_00` on the 3 torches. Copy the scale and offset from the courtyard wall torch; read its actor first.
   - **Brazier:** `PS_Fire_01` in the charcoal pit, scaled to fit.
   - **Moon spots G1/G2:** yaw = `DirectionalLight_1` yaw, pitch −78.
   - **Moon spot G3:** aimed at the plaque centre (rotation in the JSON).
   - **Shaft cards:** one per grate, using P8's `SM_LB_Prop_LightShaft_RoofHole` and `MI_LightShaft_Crypt`. 70 cm wide for G1/G2 and 200 cm for G3; from the grate along the spot axis to the floor or wall.
3. **`LFV_Crypt_Flood`:** Local Fog Volume at (9500, −2280, −600), scale 0.9 (radius 450), ground-hugging, low extinction (start radial 0.3, height 0.6), no emissive.
4. **`PP_Crypt`:**
   - Bounded PostProcessVolume X 6150–11900, Y −3300…800, Z −1150…−40, BlendRadius 300, priority above `PostProcess_Exposure`.
   - Exposure: histogram with min = max EV100; start 1.0, tune within 0.0–2.0.
5. **Targets** (B2 luma, PIE Simulate, second of two captures, poses `p9l_01…10` = the P9-5 poses):
   - **(a) No candle:**
     - mean 0.012–0.035;
     - ≥ 55 % of pixels < 0.02;
     - p99 ≥ 0.30 (a light source or pool in every pose).
   - **(b) With a candle proxy:**
     - Proxy: a temporary point light at the camera + (36, 14, −10); 10 cd, radius 600, 1900 K, no shadows (the player candle's tuning; read `DA_PlayerTuning` and use its values if they differ).
     - Pass: the wall 150 cm ahead has a central-40 % mean ≥ 0.10.
   - **(c) Clue text** readable at 2 m: owner and lead judge a capture.
   - **(d) Ledge:** visible end to end from the FP west portal.
   - **(e) Fog check:** with every crypt light off, the mean luma in pose 5 is ≤ 0.010; if not, report the global fog contribution (do not change the global fog).
6. **Drips (stretch; skip after 2 failed attempts):**
   - `NS_LB_CryptDrip`: falling drop sprites plus a flat expanding ring at the water surface (Z −592), at 3 points over the water at 0.3–0.6 drops/s each.
   - Positions: (9150, −2380), (9620, −2400), (9900, −2200).
7. **Wrap up:** save, run the suite, commit.

### D1.8 P9-8: QA and review
1. **Docs:**
   - `MCP_NOTES`: the visible-false shell, the placement script, water edge fade, child-BP swaps;
   - `PERFORMANCE_BUDGET` row;
   - `ASSET_REGISTRY` rows;
   - `RISKS`;
   - DECISIONS D-068…D-071;
   - the IMPLEMENTATION_PLAN Phase 9 table.
2. **qa-reviewer:** suite, logs, and a lane re-check.
3. **Owner:**
   - PIE in a new window, `scalability 2`, `r.SetRes 1920x1080w`, `stat unit` + `stat gpu` in the ossuary and the chain chamber. Budget ≤ 16.6 ms.
   - If over budget, cut in this order:
     1. G1–G3 shadows off;
     2. skull rows to every other skull;
     3. torch volumetric scattering off.
   - Walk the 3 crypt routes, solve the puzzle, watch the gate open and the rubble appear, and judge the darkness.
4. Then "PHASE 9 READY FOR YOUR REVIEW". Merge only on "approve and merge".

**Task order** (one [EDITOR] task at a time): P9-3 (no editor) → P9-4 → P9-5 → P9-6a → P9-6b → P9-7 → P9-8.

### D1.9 P9-3 outcome (lead review, 2026-10-27)
- **Built:** 21 meshes (46583c5); verify 72/72; renders `Docs/ArtTest/crypt/p9_*.png`, lineup `p9_lineup.png`. Bounds in `SourceArt/Props/Procedural/Crypt/props_report_P9.json` are in UE space. The generator now loads them, so the JSON/tables use the measured bounds.
- **Accepted deviations:**
  - Sarcophagus B: lid 280 × 104, rotated 3°, shifted +7, to stay within the 300 × 120 footprint.
  - Portcullis: rails at x ±146; four guide pins give the 60 cm depth while the lattice sits within y ±4.5.
  - Boards run along X, stacked along Y.
  - Crank: 43 × 8 × 14.3, with UCX 44 × 16 × 16 as specified.
  - Capstan: body z −25…23 with the boss reaching 25.
  - The capital is a plain flared bell (no cushion scallops).
- **Water:** the ripple normal is subtle by construction, so `M_LB_Water` gets `RippleNormalScale` (D1.4).
- **P9-4 import check:** after importing, read back every mesh's bounds and compare them with `props_report_P9.json` (±1 cm). Any Y-mirror or pivot difference is a stop-and-report.


### D1.10 P9-5 outcome and review fixes for P9-6a (lead review, 2026-10-27)
- **Built** (325bec8, abc167f):
  - 334 `CA_` actors, with 0 bounds/collision/material failures;
  - 113 greybox actors set `bVisible=false` (collision unchanged, traces verified);
  - review captures `p9s_01…10` and `p9s_01b…10b`.
- **Gap pass fixes (in the generator):**
  - vault bays overlap: ossuary 45 cm per shared edge, corridors 20 cm;
  - the chain-chamber soil plane faces down;
  - floor tiles reach 15 cm under the walls, none under the flood water;
  - `MI_Stone_Wall_00` Displacement/Offset 0 (its WPO pushed the crowns into the ground slab).
- **Tests:** 78/78; WalkPath.Monastery (SacristyToCrypt, FloodedLedge, CryptToCloister) PASS; RouteBot.Monastery Success; Warden crypt patrol 0 stuck.
- **Known, handled later:** the grey checker in J11 is the `Gate_CryptExit` greybox (P9-6b swaps it). The pedestal and plaque greybox go in P9-6a step 4 and P9-6b.

**Review fixes: P9-6a does these first, as R1–R5, before dressing.**
Each fix has a capture before and after, in PIE Simulate with no temporary light, one capture per pose (CaptureViewport fails about 2 of 3 calls: up to 6 bounded retries, then list the pose as missing).
Poses are the P9-5 pose files; the after captures go to `Docs/ArtTest/crypt/p9r_<fix>_<pose>.png`. Record old → new values in the report.

- **R1 Walls read as crumpled foil** (p9s_02, p9s_03, p9s_07).
  - **Cause:** `MI_Stone_00..03` Roughness is 0.381 / 0.579 / 0.427 / 0.389 after the P9-4 × 0.8.
  - **Step 1:** read the pack master that these MIs use (its parent material) and record how `Roughness` and `Flatness (S)` enter the graph (read-only).
  - **Step 2:** set `Roughness` = 0.85 on all four MIs. Capture p9s_02 and p9s_07.
  - **Pass:**
    - the 99th-percentile B2 luma of the wall area (left half of p9s_02) drops by ≥ 30 % against p9s_02;
    - the stone reads as damp stone, not metal (the lead judges the captures).
  - **If it fails:** try 1.0. If that still fails and the graph shows `Roughness` multiplies a texture channel, report the graph and stop R1 (leave 0.85).
  - **Save:** each MI explicitly.
- **R2 "Rail" lines on the floor** (p9s_02, p9s_05, p9s_08).
  - **Step A:** set `MI_Tiles` `Displacement` 12 → 0. Capture p9s_02 and p9s_08. If the lines are gone, keep it and stop R2.
  - **Step B, if the lines persist:**
    - in `Tools/crypt/gen_crypt_layout.py`, set every tile yaw to 0 (`TILE_SPACES` yaw lists → `[0]`);
    - regenerate (0 issues);
    - `place_crypt.py --cats tile`;
    - capture both poses again.
  - **If they still persist:** they are in the texture. Zoom-capture one line, report it and leave it (restore Displacement only if Step A made the cobbles look worse).
  - **Save:** `MI_Tiles` explicitly.
- **R3 White slivers at the top corners of p9s_09** (about pixels (150, 12) and (1170, 12)).
  - Recapture the pose and use `ScreenCoordsToWorld` at those pixels.
  - **No hit (sky through a gap):** find the two pieces that bound the gap. Close it by the smallest generator change: extend the adjoining ceiling, board, beam or wall piece by ≤ 20 cm, or add one `SM_LB_Crypt_Block_100` filler (`MI_Crypt_StoneWA`, NoCollision, category `lining`). Regenerate (0 issues), place, recapture.
  - **Hit on a greybox slab face:** treat it as R4.
- **R4 Lit greybox slab edges seen from the crypt.**
  - **Where:** SS1 and the top of the stair in p9s_01, the white strips. These are the 40 cm side faces of `Ground_5` (face Y −1300, X 7400…8000, Z −40…0) and `Ground_6` (face Y −900, same X and Z) at the sacristy-stair opening.
  - **Confirm** with `ScreenCoordsToWorld` on each white strip and list every greybox face hit, including any at the exit-stair opening (check pose NC4/ES1 too).
  - **Line every hit face:**
    - mesh `SM_LB_Crypt_Block_100` (100³, pivot bottom-centre), `MI_Crypt_StoneWA`, NoCollision, CastShadow on;
    - scale X = face length / 100 + 0.04, Y = 0.03, Z = (face height + 2) / 100;
    - placed so its back face lies on the slab face and it projects 3 cm into the opening, with its top at Z −0.5 (never above the floor art);
    - label `CA_Lining_<slab>_<face>`.
  - Add these as generator records (category `lining`, folder `Crypt/Art/Lining`) so `place_crypt.py --cats lining` places them idempotently.
  - **Pass:** no white strip in recaptured SS1 and p9s_01, and the SacristyToCrypt WalkPath still PASS (suite at the end).
- **R5 Small white rectangles** (p9s_05 about (925, 530) on the floor; p9s_06 about (1100, 508) at the pier base). Use `ScreenCoordsToWorld` on each.
  - **A floor tile:** it is a reflection. Identify its source by recapturing with the `CA_GrateSky_*` discs hidden on the PIE-world instances only. Report the source; no fix (P9-7 tunes `MI_Crypt_MoonSky`).
  - **An actor:** report its label and class; no fix unless it is a leftover temp actor (then delete it and say so).
- **Then** commit "P9-6a R-fixes" and continue with D1.6 P9-6a steps 1–6 (dressing).
  - `place_crypt.py` refuses `dress`, `decal` and `light` today. Extend it for `dress` and `decal`, but not `light` (P9-7):
    - **`dress`:** same as the structure categories. Each record carries `collision` and `folder`; P9-3 pieces keep their asset slot MIs.
    - **`decal`:** spawn a DecalActor. Set `decal.mi` as the DecalMaterial and `decal.size` as the DecalSize (a half-extent: use the record values as given, they are already half-extents in depth, vertical, horizontal order) with the record rotation. Follow the MCP_NOTES decal conventions and the D1.6 step 3 orientation check.

### D1.11 P9-6a outcome and fix set F1–F6 (lead review, 2026-10-28)
- **Built** (8fa049a, e066901): R-fixes; 336 `dress` + 35 `decal` records placed (0 spawn failures); skull offsets +90 (all three meshes); `CD_PlaqueFrame` at scale 1 (text clears the opening by ≥ 17 cm); suite 78/78, the 3 crypt WalkPaths PASS, RouteBot Success, Warden crypt patrol PASS.
- **Bug found and fixed:** `collisionProfileName=NoCollision` alone left `collisionEnabled=QueryAndPhysics`. `place_crypt.py` now sets and verifies both; `--fix-collision` re-applies them.
- **Environment finding:** PIE Simulate captures time out because the editor throttles to ~3 fps in the background (`EditorPerformanceSettings.bThrottleCPUWhenNotForeground`). The P9-6a captures are editor-viewport captures (`capture_poses.py --editor --double`): helper icons show, no particles.
- **Lead review:**
  - R1 stone: accepted (damp stone, wall p99 −42 %).
  - R2 floor lines: the pack cobble texture has a border band every repeat (`p9r_R2_zoom_floor_top.png`). It still reads as rails in p9d_04b/05b/06b. Fixed by F2.
  - R3: accepted for now. It is the greybox lights overexposing the CC beam undersides; recheck in P9-7 (added to D1.7).
  - R4: the slab-face linings are correct. The white strips are the railings `Rail_Sac_S/N` and `Rail_Up_W/E` (white greybox material, Z 0…100). Fixed by F1.
  - R5: `Note_Ossuary`; no fix.
  - Lane check: `CA_Pillar_Free_8000` to `Patrol_Crypt_01` is 124.8 cm (AABB), about 134 cm to the round hull; that leaves about 92 cm beyond the Warden capsule (r 42), and the Warden crypt loop passes with 0 stuck. **Accepted deviation** from the 150 cm rule; not moved.
  - The RouteBot approach overlaps are this tool's approximation; the real RouteBot passes. No change.
  - **New issues:**
    - p9d_07/07b and p9d_11/11b are stale frames of poses 06 and 10 (mean pixel difference 0.6 and 1.2; 11 "saved in 2 s");
    - the `Leaking006` streaks read as an opaque mustard band (`p9d_dec_wallPY_leak_SC_S.png`);
    - the charcoal-pit brazier `CD_Charcoal` reads as grey plastic (p9d_09, p9d_09b);
    - the clue plaque face is flat greybox grey inside the new frame (p9d_12).

**Fix set F1–F6** (environment-designer, [EDITOR], before P9-6b; one agent; explicit saves; commit "P9-6a fix set F1–F6").

**Captures for this fix set:**
- Before PIE, set `bThrottleCPUWhenNotForeground=false` on the `EditorPerformanceSettings` CDO, in memory only (never saved), and restore it to `true` at the end.
- Try one PIE Simulate capture. If it succeeds within 6 bounded retries, use PIE Simulate for this set; otherwise use `--editor --double` and say so.
- Captures go to `Docs/ArtTest/crypt/p9f_<fix>_<pose>.png`, with a `_before` capture where stated.

- **F1 Railing enclosures** (generator category `lining`, folder `Crypt/Art/Lining`; this is the one place art may rise above Z 0).
  - For each rail `R` in `Rail_Sac_S`, `Rail_Sac_N`, `Rail_Up_W`, `Rail_Up_E`:
    - Read R's world AABB and rotation. If the yaw is not a multiple of 90°, stop and report.
    - Add a record `CA_Parapet_<R>`:
      - mesh `SM_LB_Crypt_Block_100` (100³, pivot bottom-centre), `MI_Crypt_StoneWA`, NoCollision (profile and `collisionEnabled`), CastShadow on;
      - location ((minX+maxX)/2, (minY+maxY)/2, minZ − 1), yaw 0;
      - scale ((maxX−minX+4)/100, (maxY−minY+4)/100, (maxZ−minZ+3)/100).
    - The block encloses the rail by 2 cm on each side and 2 cm above, and sinks 1 cm into the floor. Rails are never moved or changed.
  - **Checks:**
    - read-back AABB ±1 cm;
    - `trace_world` through each rail still hits the `Rail_*` actor (collision intact);
    - list any existing non-greybox art actor whose AABB intersects an enclosure (report only).
  - **Captures:** `SS1_up`, `ES1_up` and P9-5 `01_stair_foot`, before and after. **Pass:** no white strip in either stair view.
- **F2 Crypt floor material** (replaces the pack cobble on the floor tiles).
  - Create `/Game/LastBell/Environments/Crypt/Materials/MI_Crypt_Floor` as a duplicate of `/Game/LastBell/Environments/Chapel/Materials/MI_Chapel_Floor_Puddled`; parent `M_LB_Surface`, `bWorldAlignedUV` true, `bPuddles` true (from the source).
  - Set and read back:

    | Parameter | Value |
    |---|---|
    | BrightnessMul | 0.35 |
    | Desaturation | 0.5 |
    | WorldTileSizeCm | 300 |
    | Wetness | 0.45 |
    | PuddleAmount | 0.12 |
    | PuddleNoiseScaleCm | 300 |
    | `bGapGrowth` | true |
    | GrowthTint | (0.22, 0.24, 0.16) |
    | GrowthLevel | 0.45 |
    | GrowthNoiseAmount | 0.30 |

    Everything else stays as in the source.
  - Read `SM_Ground`'s material slots. In `place_crypt.py` `material_for`, return `("MI_Crypt_Floor", None)` for `cat == "tile"` on every slot, then `place_crypt.py --cats tile` and `--check` (179 tiles: 0 bounds, collision or material failures).
  - Leave `MI_Tiles` as it is (Displacement 0).
  - **Captures:** p9d `03b`, `04b`, `05b`, `06b` and the R2 top-down zoom pose, before and after (`p9f_F2_*`).
  - **Pass:**
    - no continuous dark band across the floor;
    - no visible grid at the `SM_Ground` piece seams;
    - the floor reads as worn, damp flagstones.
    - If the seams show as a grid, report it with the capture and revert the tiles to the mesh's own material.
- **F3 Leak decals:** in `gen_crypt_layout.py` `LEAKS`, change `WC_W`, `SC_S` and `NC_S` from `MI_Decal_Leaking006_Wall` to `MI_Decal_Leaking004_Wall` (same size and rotation).
  - Regenerate (0 issues), then `place_crypt.py --cats decal --only CD_Decal_Leak_`.
  - Never edit `MI_Decal_Leaking006_Wall`; the courtyard uses it.
  - **Capture:** the `dec_wallPY_leak_SC_S` pose after. **Pass:** dark streaks, no mustard band.
- **F4 Brazier:** read `SM_Charcoal_Pit`'s material slots.
  - Give the `CD_Charcoal` record an `mi` override: `MI_Crypt_Iron` on the metal-basket slot(s). Keep the charcoal/ember slot's own MI; if there is only one slot, use `MI_Crypt_Iron` and say so.
  - Extend `material_for` to honour a per-slot `mi_slots` map on `dress` records. Place with `--only CD_Charcoal`.
  - **Capture:** p9d_09 before and after. **Pass:** dark rusty iron, no plastic sheen.
- **F5 Recapture** p9d_07, 07b, 11 and 11b with `--force --double` (07b and 11b use the moved temp light, as before).
  - **Pass:** the mean pixel difference against 06/06b and 10/10b is > 10.
- **F6 Wrap-up:**
  - save `L_Monastery` and `MI_Crypt_Floor` explicitly;
  - run the suite (78/78; the 3 crypt WalkPaths PASS, RouteBot.Monastery Success, the Warden crypt patrol);
  - check the editor is not dirty and no temp actors remain;
  - restore the throttle setting;
  - commit;
  - report old → new values, pass/fail per fix, and the capture list.

**P9-6b additions** (to D1.6 P9-6b; the unreal-blueprint-engineer does these after its step 1):
- **1e. Plaque face:** read the `Clue_Diagram` (BP_EngravedDiagram) instance's plaque mesh component and whether its construction script sets the material.
  - If it does not, set a level-instance override on slot 0 to `/Game/LastBell/Environments/Kit/Materials/MI_Kit_Slate`, then save and capture at 2 m (pose p9d_12).
  - **Pass:** the text stays fully readable and contrast is no worse than p9d_12 (lead and owner judge). Otherwise revert and report.
  - If the construction script sets the material, report it; never edit the parent.

**D1.7 additions (P9-7):**
- **Recheck R3:** the p9s_09 top corners, and the white flecks at the top corners of p9d_01, under the new lights.
- **Decal strength:** soot T3 and the NC mould were not visible. If they are still invisible under the new lights, raise opacity on new crypt-only duplicates (`MI_Crypt_Decal_*`), never on the shared chapel MIs.
- **Skull brightness:** if the niche skulls read as clean white under the candle proxy, darken them with a crypt-only MI.
- **Captures:** set `bThrottleCPUWhenNotForeground=false` in memory for the PIE Simulate captures and restore it at the end. Fires, fog and drips only show in PIE.

### D1.12 Fix set outcome and F2b (lead review, 2026-10-28)
- **Built** (b7f63c4): suite 78/78, the 3 crypt WalkPaths PASS, RouteBot Success, Warden crypt loop 0 stuck; greybox 113/113 verified.
  - F1, F3, F4 and F5 accepted.
  - The `p9d_10b` replacement is kept (the old file showed the pose-11 view).
  - The brazier's charcoal bed is gone, because the mesh has a single slot. The P9-7 brazier fire covers the pot interior.
  - The white grid through the exit shaft is `Cl_S2`, the cloister greybox. It belongs to the Bell Tower/cloister art phase (Phase 10), so it gets no crypt lining.
- **F2 not accepted:** `MI_Crypt_Floor` (Tiles139) reads as clean, modern square tiles with vivid green triangles.
  - It is about 2.2× brighter than the old floor. B2 luma, bottom third with the middle 60 % of the width:

    | Pose | Old floor | New floor |
    |---|---|---|
    | 04b | 0.217 | 0.469 |
    | 06b | 0.188 | 0.331 |
    | 05b | 0.192 | 0.379 |

**F2b** (environment-designer, [EDITOR]; same capture and safety rules as D1.11; commit "P9-6a F2b: crypt floor cobbles").
1. Read `/Game/LastBell/ArtTest/Materials/Cobblestone_Floor_08/MI_Cobblestone_Floor_08_WA` (parent, textures, WorldTileSizeCm, static switches). Record them in the report.
2. **Retexture `MI_Crypt_Floor` (candidate B, cobbles).** Keep the asset, its parent chain and its placement; change only these values, then read back:
   - **Textures:**
     - `BaseColorTex` `T_Cobblestone_Floor_08_BC`
     - `NormalTex` `T_Cobblestone_Floor_08_N`
     - `ARMTex` `T_Cobblestone_Floor_08_ARM`, with `bUseARM` true
     - `PuddleHeightTex` `T_Cobblestone_Floor_08_H` (all in the same folder)
   - **Tiling:** `WorldTileSizeCm` = the value from `MI_Cobblestone_Floor_08_WA`, or 250 if it has none.
   - **Colour:** `Desaturation` 0.55, `BaseColorTint` (1, 1, 1).
   - **Growth:** `GrowthTint` (0.10, 0.11, 0.07), `GrowthLevel` 0.40, `GrowthNoiseAmount` 0.20, `bGapGrowth` true.
   - **Puddles:** `Wetness` 0.45, `PuddleAmount` 0.12 (unchanged).
   - **`BrightnessMul`:** start at 0.35, then iterate (at most 4 times) on capture 04b with `BrightnessMul_new = BrightnessMul_old × 0.21 / measured`.
     - "Measured" is the mean B2 luma (Y = 0.2126R + 0.7152G + 0.0722B, on 0–1) of the box x 20–80 %, y 67–100 % of the image.
     - Stop when 04b is in 0.18–0.24. Then 06b must be in 0.15–0.22; report it either way.
3. **Captures B** (same method as the fix set; the b poses use the moved temp light), as `p9f_F2b_*`:
   - 03b, 04b, 05b, 06b and the top-down zoom;
   - plus 04 and 06 with no temp light.
4. **Candidate C, comparison only** (the blocks texture).
   - Temporarily set:
     - `BaseColorTex` `T_Medieval_Blocks_03_BC`, `NormalTex` `T_Medieval_Blocks_03_N`, `ARMTex` `T_Medieval_Blocks_03_ARM`;
     - `bGapGrowth` false;
     - `WorldTileSizeCm` 220.
   - Run the same `BrightnessMul` iteration.
   - Capture 04b, 06b and the zoom as `p9f_F2c_*`.
   - **Then restore candidate B exactly** (read it back) and save `MI_Crypt_Floor` and nothing else. B stays applied; the lead picks after viewing.
5. **Pass for B:**
   - 04b in 0.18–0.24;
   - no continuous dark band and no tile grid;
   - joints read as dark damp mould, not bright green.
   - The lead judges the captures.
6. **Wrap-up:**
   - no map change is needed (the tiles already use `MI_Crypt_Floor`), so do not save `L_Monastery` unless it is dirty; if it is dirty, report why before saving;
   - no suite run is needed for a material-only change;
   - no temp actors left, throttle restored, commit, report (values old → new, luma per iteration, capture names).

### D1.13 F2b outcome and P9-6b go (lead review, 2026-10-28)
- **F2b accepted (a2bc978):** candidate B, the Cobblestone_Floor_08 cobbles.
  - `MI_Crypt_Floor` `BrightnessMul` 0.1105, WorldTileSizeCm 150.
  - 04b 0.228, 06b 0.192.
  - Dark mould in the joints, no bands, no grid.
  - The wet sheen stays for now; P9-7 judges it under the real lights. Knobs: `Wetness`, `PuddleAmount`, `PuddleRoughness`.
  - Candidate C (blocks) is rejected: flat and featureless at gameplay distance.
- **Editor state:** `L_Monastery` is dirty in the editor only from the temp-light add/remove (no content change). P9-6b confirms `find_actors TMP_` is empty, then its own explicit map saves cover it.
- **P9-6b step 1e (plaque face):** MCP_NOTES warns that component edits on placed BP instances often don't persist. After the override and an explicit save, read the material back on the instance.
  - If it did not stick, report it; do not create a child Blueprint for `Clue_Diagram` without lead approval.

### D1.14 P9-6b outcome and P9-7 go notes (lead review, 2026-10-28)
- **Built** (621d02b, a50a573, 3a9b0de):
  - 4 child Blueprints in `/Game/LastBell/Blueprints/Interactables/`, compiled with warnings as errors.
  - 4 swaps: same label, same folder `Gameplay/Crypt`.
  - Before/after diffs show only the allowed differences. A re-dump after save and reload shows 0 differences.
  - Gate and rubble UCX bounds match D1.6.
  - Tests:
    - suite 78/78, the 3 crypt WalkPaths PASS;
    - RouteBot Success (it used the new crank and winch);
    - `Puzzles.*` and `Save.*` Success;
    - Warden crypt loop 67 s, 0 stuck.
- **Accepted:**
  - The closed gate, open gate, crank on its plinth and winch drum read correctly (`p9b_*`).
  - **Deviation: no material overrides.** The meshes' own slot MIs are already the crypt MIs.
  - **Deviation: `RequiredTags` variable on the winch child.**
    - It is an instance-editable variable that the construction script feeds to `SetRequiredStateTags`.
    - This is the only route that persists, because a child cannot override the InteractComp template.
    - P9-8 records it in MCP_NOTES with the child-BP swap notes.
  - **Deviation: the child construction scripts replace the parent's.**
    - The DSL cannot author a parent construction-script call, so the Crank and Winch children copy the parent body.
    - P9-8 adds a RISKS entry: if the construction script of `BP_TagInteractable` or `BP_RitualMechanism` changes, update the crypt children.
  - No winch-after (turned Core) capture. The owner sees the turn in the P9-8 playtest.
  - The retry cap was exceeded while the editor window was fully covered by other windows. The root cause is now known, and P9-7 step 0a fixes the capture method.
- **Not accepted: 1e plaque face** (`p9b_1e_12_puzzle_wall_2m.png`).
  - `MI_Kit_Slate` uses the roof-slate textures, UV-based, with UVScale 0.25, RoughnessMin 0 and RoughnessMax 1.
  - On the plaque, no slate texture shows, and the face carries a blurred mirror image of the chamber. It reads as frosted glass, not stone.
  - The darker face is right: contrast went from 1.81 to 2.34.
  - Fixed in P9-7 step 0b.
- **Watch: the rubble face** (`p9b_pie_rubble_after.png`) shows white slivers at chunk edges. Two possible causes:
  - chunk tops overexposed by the greybox lights (like R3);
  - the bright stair behind showing through gaps in the mesh.
  - P9-7 step 0c rechecks it under the new lights.

**P9-7 additions** (lighting-vfx; do 0a–0c before D1.7 step 1; then D1.7 with the D1.11 "D1.7 additions"):
- **0a. Capture reliability.** Add a `--raise` flag to `Tools/crypt/capture_poses.py`; reference implementation: the P9-6b helper `one2.py`.
  - **While each capture runs:**
    - A daemon thread runs every 0.2 s over the visible top-level windows whose title ends with `Unreal Editor`.
    - If a window is iconic, `ShowWindow(h, 4)` (`SW_SHOWNOACTIVATE`).
    - Then `SetWindowPos(h, 0, 0, 0, 0, 0, 0x13)` (`HWND_TOP`, `SWP_NOSIZE|SWP_NOMOVE|SWP_NOACTIVATE`).
    - Stop the thread when the pose finishes.
  - **Never activate or focus the editor window.** The owner may be typing elsewhere.
  - Use `--raise` for every P9-7 capture.
  - **Retry cap:** at most 6 tries per pose, in one pass. A pose still missing after that is reported, not retried.
  - Commit the script change with the first P9-7 commit.
- **0b. Plaque face.**
  - Create `/Game/LastBell/Environments/Crypt/Materials/MI_Crypt_PlaqueSlate` as a duplicate of `/Game/LastBell/Environments/Kit/Materials/MI_Kit_Slate`. Never edit `MI_Kit_Slate`; the chapel roof uses it.
  - Set the following, then read them back:

    | Parameter | Value |
    |---|---|
    | `RoughnessMin` | 0.70 |
    | `RoughnessMax` | 0.95 |
    | `bWorldAlignedUV` | true |
    | `WorldTileSizeCm` | 120 |
    | `BrightnessMul` | 0.55 |
    | `Desaturation` | 0.30 |

  - Set the `Clue_Diagram` instance's `Plaque` override, slot 0, to the new MI. Use the same instance-override path that persisted in P9-6b.
  - Save explicitly, then read the material back on the instance.
  - **Capture** `p9l_plaque_2m` at pose (10920, −1700, −330), pitch 0, yaw 90, under the final lights (after step 5), plus a second one with the candle proxy.
  - **Pass:**
    - no mirror image of the chamber on the face;
    - the slate grain is visible;
    - text contrast ≥ 2.0, where contrast is the text p98 luma divided by the median luma of the plaque band rows, measured as in the P9-6b 1e report.
  - If contrast is below 2.0, lower `BrightnessMul` in steps of 0.10, down to 0.35 (at most 3 tries), and report each value.
- **0c. Rubble recheck** (after step 5).
  - In PIE Simulate, set `bHidden=false` on the PIE-world `Rubble_StairsBack` only; never touch the editor world.
  - **Pose:**
    - Y −1100, Z −430, pitch −3.
    - Facing the rubble from its crypt side, which is the side where a down-trace 400 cm from the face hits the crypt floor (Z ≈ −600) and not the stair.
    - The camera is 400 cm from the face.
  - Capture `p9l_rubble_after`.
  - **Pass:** no white slivers.
  - If slivers remain, add a zoom capture `p9l_rubble_zoom` and report it. Do not change the mesh; the lead decides.
- **Floor sheen** (D1.13): report the floor-box p99 luma (x 20–80 %, y 67–100 %) for every `p9l_*` pose.
  - The lead judges the wet sheen.
  - The knobs are `Wetness`, `PuddleAmount` and `PuddleRoughness` on `MI_Crypt_Floor`. Change them only if the lead asks.
- **Known (do not fix):** the white `Cl_S2` cloister greybox seen at the top of the exit stair belongs to Phase 10.

### D1.15 P9-7 execution spec (lead, 2026-10-28)
This section makes D1.7 (with the D1.11 "D1.7 additions" and the D1.14 "P9-7 additions") executable. If it conflicts with them, D1.15 wins.

**Poses:** `Tools/crypt/poses/p9l_poses.json`, written as [x, y, z, pitch, yaw]. It holds:
- `01…10`, the P9-5 `p9s` poses;
- `d01`, `d03`, `d09` and `d11`, the matching `p9d` poses;
- `plaque_2m`.

**Capture method (all P9-7 captures):**
- PIE Simulate with `EditorPerformanceSettings.bThrottleCPUWhenNotForeground=false`, in memory only; restore it to `true` at the end.
- `capture_poses.py --double --raise`.
- File names are `Docs/ArtTest/crypt/p9l_<pose>.png`. Use `_c` for the candle-proxy variant and `_before` for the step-1 baseline.
- **Luma:** B2 (Y = 0.2126R + 0.7152G + 0.0722B) on the PNG's 8-bit values / 255, with no linearisation, as in every earlier P9 measurement.
- **Candle proxy:** `TMP_CaptureLight`, spawned in the **PIE world only**.
  - PointLight, intensity units Candelas, intensity 10, attenuation radius 600, `bUseTemperature` true, temperature 1900 K, no shadows.
  - These are `DA_PlayerTuning`'s `CandleIntensity`, `CandleAttenuationRadius` and `CandleTemperature`. Read them first; if they differ, use the asset's values and report.
  - Add `--light-offset F R U` to `capture_poses.py`: the light goes to camera + F·forward + R·right + U·up, using the camera's yaw and pitch. Use `--light-offset 36 14 -10`.

**Tuning workflow:**
- Iterate on the PIE-world copies only, for measuring.
- Then write the final values to the editor-world actors, stop PIE, save `L_Monastery` explicitly, and take the final capture set from a **fresh** PIE Simulate session.
- Values that exist only in PIE are lost, so never report them as done.

**Steps**
1. **Baseline:** capture `01…10` as `p9l_<pose>_before` with the greybox lights, no proxy.
2. **Greybox lights:**
   - dump `Light_Crypt_0..13` (label, class, transform, intensity, units, radius, colour, shadows) to `Docs/ArtTest/crypt/greybox_lights_before.json`;
   - delete them in the editor world;
   - confirm `find_actors Light_Crypt_` is empty.
3. **Place the 16 lights.** Extend `place_crypt.py` to accept `--cats light`; it currently refuses that category. Each `light` record becomes one actor:
   - class `/Script/Engine.PointLight` or `/Script/Engine.SpotLight` (from `light.type`), label = `id`, folder `Lighting/Crypt`, Mobility Movable;
   - location from `loc`; rotation from `rot`, which is [pitch, yaw, roll];
   - `intensityUnits` Lumens; `intensity`, `attenuationRadius`, `lightColor` (sRGB, from `color`), `castShadows`, `sourceRadius`;
   - `volumetricScatteringIntensity` if present, else leave the default;
   - SpotLight: `innerConeAngle` and `outerConeAngle`;
   - `lightFunctionMaterial` = `/Game/LastBell/Materials/Instances/<light_function>` if present;
   - moon spots: `bCastVolumetricShadow` true.
   - **G1/G2 yaw:** read `DirectionalLight_1`'s world yaw and use it for `L_Crypt_Moon_G1` and `_G2`, with pitch −78. G3 keeps the JSON rotation, which aims it at the plaque centre.
   - `--check` reads back every field (±0.5 %, angles ±0.1°).
4. **Fires:**
   - Read `KX_Torch` and `FX_Torch_Fire` in the courtyard. Record the fire's offset from the torch's world-bounds top and +X end, and its scale (P7 used 0.22).
   - **Torch fires:** for each `CD_Torch_T1..3`, spawn `/Game/LastBell/ThirdParty/Fab/Dungeon/Fire/Particle_Systems/PS_Fire_00` (an Emitter actor) as `FX_Crypt_Torch_T1..3`, folder `Lighting/Crypt`, with the same offset turned by the torch's yaw and the same scale.
   - **Brazier fire:** spawn `PS_Fire_01` as `FX_Crypt_Brazier`, centred on `CD_Charcoal`'s bounds top. Pick a scale so the flame base is ≤ 55 cm wide and the flame sits in the pot; report the scale.
   - Fires show only in PIE, so judge them on PIE captures `p9l_01` (T1), `p9l_06` (T2), `p9l_10` (T3) and `p9l_d09` (brazier).
   - **Pass:** each flame sits on its torch head or in the pot, not floating or buried.
5. **Shaft cards:** one per grate (G1, G2 and G3, the CC grate), `SA_Crypt_G1..3`, NoCollision, CastShadow off, `MI_LightShaft_Crypt`, folder `Lighting/Crypt`.
   - Try `SM_LB_Prop_LightShaft_RoofHole` first. Its extrusion is oblique in its own frame, so first read its bounds and check whether a rotation can make its axis run along the spot axis.
   - **If it can't, use `/Engine/BasicShapes/Cylinder`:**
     - pivot at the centre, axis = local Z;
     - rotate it so its axis lies along the spot direction;
     - scale (W/100, W/100, L/100), with W = 70 for G1/G2 and 200 for G3, and L = the distance from the grate to the floor or wall hit along the spot axis (`trace_world`);
     - centre it at grate + 0.5·L·dir.
     - If the bright end ends up at the floor, rotate it 180° about a horizontal axis.
   - Report which mesh was used. **Pass:** soft beam, no hard card edges, brightest at the grate.
6. **`LFV_Crypt_Flood`** and **`PP_Crypt`:** as D1.7 steps 3 and 4.
   - Read `PostProcess_Exposure`'s priority and set `PP_Crypt` to that + 1.
   - Exposure: method Manual or Histogram with `MinEV100 = MaxEV100`; start at 1.0. Higher EV100 makes the image darker.
7. **Plaque (D1.14 0b):** do the MI and override now. Its capture comes in step 8.
8. **Targets** (D1.7 step 5) on the fresh-session capture set:
   - **(a) No proxy:** `01…10`. Per pose: mean 0.012–0.035, ≥ 55 % of pixels < 0.02, p99 ≥ 0.30.
     - Tune in this order:
       1. `PP_Crypt` EV100 (0.0–2.0);
       2. moon spot intensity, so the pool centre luma is 0.25–0.45 (G1/G2 on the floor, G3 on the plaque);
       3. torch, brazier and candle intensities, within ±50 % of the JSON values.
     - Do not add, remove or move lights. A pose that still fails after this order is reported with its numbers, and the lead decides.
   - **(b) Candle proxy:**
     - `01…10` as `_c` (report the mean).
     - Three wall poses. For each of WC, the ossuary and NC, pick a camera at Z −430 facing a wall so that `trace_world` straight ahead hits the wall at 150 ± 10 cm. Record the poses in `p9l_poses.json` as `w_WC`, `w_OS` and `w_NC`, and capture them `_c`.
     - **Pass:** the central-40 % mean of each wall pose is ≥ 0.10.
   - **(c)** `plaque_2m` and `plaque_2m_c`: the D1.14 0b pass.
   - **(d)** `d11` (ledge from the FP west side): the lead judges.
   - **(e)** Pose 05 with every crypt light hidden (PIE world only): mean ≤ 0.010.
   - **D1.11 rechecks:**
     - R3 at the `p9s_09` top corners and the `d01` top corners;
     - skulls on `d03_c` (if they read clean white, make a crypt-only darker MI and report it);
     - decals (soot T3 and the NC mould) on the `_c` captures (if they are invisible, make crypt-only `MI_Crypt_Decal_*` duplicates with higher opacity; never edit the shared chapel MIs).
   - **D1.14 0c:** the rubble recheck.
   - Report the floor-box p99 luma for every pose.
9. **Drips** (D1.7 step 6; stretch): skip after 2 failed attempts and say so.
10. **Wrap up:**
    - explicit saves (the map and every new asset; never save-all);
    - suite 78/78, with the 3 crypt WalkPaths PASS, RouteBot.Monastery Success and the Warden crypt patrol;
    - no `TMP_` actors in either world, PIE stopped, throttle restored, editor not dirty;
    - commit in checkpoints `P9-7: …`;
    - report: old → new values; a luma table per pose (mean, % < 0.02, p99, floor p99); pass or fail per target; the capture list.

### D1.16 P9-7 partial outcome and finish set F7 (lead review, 2026-10-28)
- **Built** (c5bfc12, d8823cf, a25b9ef):
  - greybox lights dumped and removed;
  - 16 lights placed (`--check` 16/16);
  - fires `FX_Crypt_Torch_T1..3` (`PS_Fire_00`, scale 0.7, copied from the current courtyard torch; the 0.22 in P7_FIX2 is outdated) and `FX_Crypt_Brazier` (`PS_Fire_01`, 0.5);
  - shaft cards `SA_Crypt_G1..3` on `/Engine/BasicShapes/Cylinder` (the RoofHole mesh is chapel-specific: about 2370 × 1740 × 2300 cm, oblique);
  - `LFV_Crypt_Flood`;
  - `PP_Crypt` (priority 1, EV100 0.2);
  - `MI_Crypt_PlaqueSlate`;
  - tuned values saved.
  - The run stopped at the capture circuit breaker: `02_landing`, `pool_G1` and `pool_G2` hang CaptureViewport again and again. The editor stayed responsive.
- **Lead review:** the crypt now reads as intended (p9l_05, 06, 08, d11): very dark, warm torch and candle pools, cold moon shafts, the brazier glow through the chain chamber.
- **Accepted values:**
  - G1 560, G2 900, G3 100 lm (G3 is below the JSON range; the plaque pool is in range);
  - torches 250 and brazier 200 (the −50 % floor);
  - niche candles 90, sarcophagus candles 67.5, puzzle candles 40.
- **Accepted deviations:**
  - Pose 05 p99 0.278: the G1 shaft and the brazier are in view.
  - Pose 06 mean 0.0351: rounding.
  - The floor glints on wet cobbles (floor p99 up to 0.68) read as wet stone. The owner judges them in the playtest; `MI_Crypt_Floor` is unchanged.
  - LFV height falloff 400 and offset 0.
  - `pool_G1`/`pool_G2` are not recaptured: G1/G2 are unchanged since the tuning-run values (0.412 and 0.307, both in range).
  - **Drips (D1.7 step 6, stretch): deferred out of Phase 9.** They are not attempted, because of the crash risk; they get done only if the owner asks.
- **Not accepted:**
  - **Plaque shadow:** G3 throws a hard diagonal shadow across the plaque, which cuts off "BALA" and "A - HIGH" in the 2 m view.
  - **Plaque texture:** the roof-slate texture reads as shingles on a wall plaque.
  - **Poses 10 and 02:** the torch-lit walls push the mean to 0.058 and 0.074.

**Finish set F7** (lighting-vfx, [EDITOR]; same rules as D1.15. Do F7a–F7c, save explicitly and commit before any capture.)
- **F7a G3 shadow:** on `L_Crypt_Moon_G3`, set `castShadows` false and `bCastVolumetricShadow` false, then read back.
- **F7b Plaque stone** (`MI_Crypt_PlaqueSlate` only; never edit `MI_Kit_Slate` or `MI_Rock_064*`).
  - **Candidate A** (the `MI_Rock_064_WA` texture set):
    - textures: `BaseColorTex` `T_Rock_064_BC`, `NormalTex` `T_Rock_064_N`, `RoughnessTex` `T_Rock_064_R`, `AOTex` `T_Rock_064_AO`, all in `/Game/LastBell/ArtTest/Materials/Rock_064/`; `bUseARM` false;
    - mapping: `bWorldAlignedUV` true, `WorldTileSizeCm` 250;
    - colour: `Desaturation` 0.85 (removes the moss green), `BrightnessMul` 0.55;
    - roughness: keep `RoughnessMin` 0.70 and `RoughnessMax` 0.95.
  - **Candidate B** (fallback):
    - textures: `BaseColorTex` `/Game/LastBell/Materials/Textures/T_LB_White_Gray`, `NormalTex` `T_Rock_064_N`;
    - colour: `BaseColorTint` (0.16, 0.16, 0.17), `Desaturation` 0, `BrightnessMul` 1.0;
    - `NormalStrength` 0.4; everything else as in A.
  - Read back every value after each change.
- **F7c Torch pools:** on `L_Crypt_Torch_T1` and `_T3`, change `attenuationRadius` 700 → 450, and read it back. Lumens stay at 250; T2 is unchanged.
- **Captures** (fresh PIE Simulate session after the F7 save; `--double --raise`, with the breaker):
  1. **Plaque:**
     - `plaque_2m_A`, then switch to B in the PIE world only (or temporarily in the editor world, then restore) and capture `plaque_2m_B`.
     - **Pass:**
       - no hard shadow edge across the text;
       - G3 pool luma on the plaque 0.25–0.45 (tune G3 within 60–200 lm);
       - text contrast ≥ 2.0, measured as before;
       - the face reads as one dressed stone slab: no shingles, no block or mortar grid, no green.
     - Prefer A if it passes. Apply the chosen candidate in the editor world, save, read back, and report which one and why.
     - If A's contrast is below 2.0, lower `BrightnessMul` in steps of 0.10, down to 0.35.
  2. **Torch poses 02 and 10, no proxy.**
     - **Accepted torch-pose target:** mean ≤ 0.045 and ≥ 50 % of pixels < 0.02. The torch is the landmark.
     - If either still fails, set T1/T3 radius to 350 once, recapture, and report.
     - If 02 still trips the breaker after its one rest-and-retry, capture it in the editor viewport as `p9l_02_landing_editor`. Measure it and state that fires and fog are missing in that capture.
  3. **Recapture `06`, no proxy.** Pass: still within (a), since T2 is unchanged.
  4. **Then the D1.15 resume steps:**
     - the candle-proxy `_c` set: `01..10`, `w_WC`, `w_OS`, `w_NC`, `plaque_2m`, `d01`, `d03`. (b) passes when every wall pose's central-40 % mean is ≥ 0.10;
     - the fog check (e) at pose 05;
     - the rubble recheck (D1.14 0c);
     - R3: the top corners of `09` and `d01`;
     - skulls on `d03_c`;
     - decals on `10_c` (soot T3, NC mould).
     - Apply the D1.11 crypt-only MI rules if needed.
  5. **Wrap up:**
     - suite 78/78, with the 3 crypt WalkPaths, RouteBot.Monastery and the Warden crypt patrol;
     - PIE stopped, no `TMP_`, throttle `true`, editor not dirty;
     - commit `P9-7 F7: …`;
     - report in the D1.15 format.

### D1.17 F7 outcome and close-out set F8 (lead review, 2026-10-28)
- **Accepted** (598fb61, a489a9b, 1a1aa8c, 3cb1e2e, ee90ff3):
  - F7a: G3 has no shadow, so there is no hard edge across the text.
  - **F7b deviation, plaque B2:** candidate B with `Desaturation` 1.0, giving a flat blue-grey slab with soft relief; contrast 2.87, pool 0.317.
    - A read as a rubble wall with a mortar grid.
    - B as written rendered magenta, because `T_LB_White_Gray` is a TC_Alpha mask; B2 fixes that with `Desaturation` 1.0.
  - F7c: T1/T3 radius 350.
  - **Accepted deviations:**
    - **torch poses:** 02 mean 0.050 and 10 mean 0.049, with ≥ 50 % of pixels < 0.02. The torch is the landmark; the owner judges in the playtest.
    - **06 and 09 means:** 0.039 and 0.040, within the session-to-session flicker noise of ±10 %.
    - **Skulls:** they read warm cream-gold under the 1900 K candle (`d03_c`), so there is no skull MI.
    - **Candle proxy:** a PIE-only retargeted copy of `Light_Approach_0`, because SceneTools refuses to spawn actors during PIE. The editor-world light was read back unchanged.
- **Capture reliability:**
  - `CaptureViewport` resets at 21.3 s when the editor window is minimized. Most of those failures stop once the window is merely restored, but about one pose in three still fails while ordinary windows cover the editor. `HWND_TOP` without activation cannot go above the foreground app.
  - P9-8 adds this to MCP_NOTES: "keep the editor visible and uncovered during capture runs".
- **G3 leak risk:**
  - Shadowless, G3's cone (radius 750) continues about 400 cm past the plaque, into the wall mass toward NC.
  - **Fix:** `attenuationRadius` 750 → 450, and raise the lumens so the plaque pool stays at 0.25–0.45. The window falloff halves at 334 cm, so start at 190 lm, within 60–200.

**F8 close-out** (lighting-vfx, [EDITOR]; D1.15/D1.16 rules):
1. **Run the suite first** (no captures needed): 78/78, the 3 crypt WalkPaths, RouteBot.Monastery and the Warden crypt patrol.
2. **G3:** set `attenuationRadius` 450 and 190 lm, read both back, save, commit.
3. **One capture pass**, in this order, with `--raise` and the breaker:
   1. `plaque_2m`: pool 0.25–0.45, contrast ≥ 2.0;
   2. `w_WC_c`, `w_OS_c`, `w_NC_c`: target (b);
   3. `04_c`, `10_c`;
   4. the fog check (e) at pose 05, all crypt lights, FX and shaft cards hidden (PIE only): once with `LFV_Crypt_Flood` and once without;
   5. the rubble recheck.
   - Use the PNGs you already have for R3 (the top corners of `09` and `d01`) and for decals (`10_c` if captured).
4. **If the breaker trips:** do one 60 s rest and retry, then stop capturing. List the missing items; they go to the P9-8 owner playtest checklist. Do not loop.
5. **Wrap up:** throttle `true`, PIE stopped, no `TMP_`, editor clean, commit `P9-7 F8: …`, report.

### D1.18 P9-7 accepted; P9-8 plan (lead, 2026-10-28)
- **P9-7 accepted** (c5bfc12 … fe82dca).
  - Suite 78/78: SacristyToCrypt, FloodedLedge and CryptToCloister PASS; RouteBot.Monastery Success; Warden crypt loop 67 s, 0 stuck.
  - Plaque B2: contrast 2.81, pool 0.328.
  - G3 450 cm / 190 lm, shadowless.
  - (b) passes on `w_WC_c` 0.411 and `w_NC_c` 0.406.
  - (e) fog check: 0.0014 with and without the LFV.
  - R3 is clear.
  - F7 deviations stand (D1.17). Drips are deferred.
- **Moved to the P9-8 owner playtest checklist** (not captured, because of capture tooling):
  - the candle on the ossuary wall (`w_OS`);
  - the stair-chamber view (`04`) with the candle;
  - the rubble face under the candle (the only rubble capture is unlit);
  - the decals (soot near T3, NC mould).

**P9-8a: docs** (general-purpose, no editor; commit "P9-8a: Phase 9 docs").
1. **`Tools/mcp/MCP_NOTES.md`:** add a section "Crypt (P9) lessons". Each item states one fact and how to apply it; pull the details from P9_CRYPT_ART D1.9–D1.17 and the commit messages:
   1. **Visible-false shell (D-068).** Greybox actors are `bVisible=false` with their collision kept. Verify with `place_crypt.py --hide-greybox` / `--verify-greybox`.
   2. **`Tools/crypt` scripts.**
      - `place_crypt.py`: `--cats`, `--only`, `--check`, `--fix-collision`, the per-slot `mi_slots`, `--cats light`.
      - `place_lighting.py`, `luma_report.py`.
      - `capture_poses.py` flags: `--editor`, `--double`, `--raise`, `--light-offset`, `--suffix`, `--only`, `--settle`, `--timeout`, the breaker.
      - The pose file `Tools/crypt/poses/p9l_poses.json`.
   3. **NoCollision:** set both `collisionProfileName` and `bodyInstance.collisionEnabled`.
   4. **Water edge fade:** from the P9-4 report or commit.
   5. **Child-BP swaps (D-071):**
      - the construction script sets the mesh and the Interaction Block;
      - the DSL cannot call the parent construction script, so the children copy the parent body;
      - InteractComp defaults can't be overridden in a child, so values go through an instance-editable variable that the construction script feeds (the winch `RequiredTags`);
      - dump before and after, and keep the label and folder.
   6. **Captures:**
      - `CaptureViewport` resets at 21.3 s when the editor window is minimized, and fails often when ordinary windows cover it. Keep the editor visible and uncovered; use `--raise` and the breaker.
      - The PIE throttle is set in memory only.
      - Use `--double` against stale frames.
   7. **PIE:**
      - SceneTools refuses to spawn actors during PIE; retarget a PIE copy of an existing light instead.
      - `bHidden`/`bVisible` writes don't update the render state of lights in PIE; zero the intensity or move the actor.
      - Asset saves fail during PIE; save after `StopPIE`.
   8. **`T_LB_White_Gray`** is a TC_Alpha mask and renders magenta as a base colour. Use a tinted base colour with `Desaturation` 1.0 (plaque B2).
   9. **Material-instance toolset:** `editor_toolset.toolsets.material_instance.MaterialInstanceTools`, which needs full object paths (`/Game/...Name.Name`).
2. **`Docs/PERFORMANCE_BUDGET.md`:** add a Phase 9 crypt row.
   - Counts from `Docs/plans/p9_d1_layout.json` per category.
   - 16 lights: G1/G2 shadowed spots, G3 shadowless, 13 shadowless point lights with light functions.
   - 4 Cascade fires, 1 LFV, `PP_Crypt` EV100 0.2.
   - The GPU figures stay "owner measurement pending (P9-8c)".
3. **`Docs/ASSET_REGISTRY.md`:**
   - List every external asset referenced by `p9_d1_layout.json` and by the crypt MIs (`MI_Crypt_*`: Cobblestone_Floor_08, Rock_064, the Fab Dungeon pack, Poly Haven / ambientCG sets).
   - Check that each has a row, and add "used in crypt (P9)" to its usage column.
   - Report anything missing. Add a row only with the facts from `ExternalAssets/Incoming/` and the original download record; never invent a licence.
4. **`Docs/RISKS.md`:**
   - R-36 Closed (the P9-5 gap pass, captures).
   - R-37 Closed (P9-6b diffs, suite, RouteBot, puzzle and save tests).
   - R-38 stays Open until the owner's stat gpu.
   - Add R-39, "capture tooling reliability" (Tooling, likelihood M, impact L; the mitigations above).
   - Add R-40, "crypt child BPs duplicate parent construction scripts" (M, M; update the children when a parent changes).
5. **`Docs/DECISIONS.md`:** add D-072, "Crypt lighting outcome". It records:
   - the final light values (from D1.16–D1.18);
   - `PP_Crypt` EV100 0.2;
   - the accepted deviations (torch poses 02/10, plaque B2, skull MI not needed);
   - drips deferred.
   Also add an index line, matching the existing format.
6. **`Docs/IMPLEMENTATION_PLAN.md`:** Phase 9 status line: P9-0…P9-7 done with commits; P9-8 in progress.

**P9-8b: QA** (qa-reviewer, read-only plus the test script; runs in parallel with 8a).
1. **Suite:** `Tools\mirror_build_and_test.ps1`. Report 78/78 and the named crypt lines.
2. **Editor log:** `EditorToolset.LogsToolset.GetLogEntries`, always filtered. Report Error and Warning entries since the editor started, grouped by category, leaving out the known benign `LogCrowdFollowing` RecastNavMesh warning.
3. **Lane re-check:** run `Tools/crypt/lane_check_crypt.py` against the current level. The crank mesh grew in P9-6b. Report the WalkPath-segment and AI-point clearances, and whether any value is new versus `lane_check_p9.md`.
4. **Git state:** report `git status` and that `main..claude/phase-09-crypt` holds only P9 commits.
5. **Report only.** No fixes, no editor mutations, no saves.

**P9-8c: owner** (in the review; checklist given in the "PHASE 9 READY FOR YOUR REVIEW" report).
1. **Performance:** PIE in a new window, `scalability 2`, `r.SetRes 1920x1080w`, `stat unit` + `stat gpu`.
   - Measure in the ossuary (about X 8250, Y −2450) and the chain chamber (about X 10800, Y −2000). The budget is ≤ 16.6 ms.
   - If over, cut in this order:
     1. G1/G2 shadows off;
     2. half the skull rows;
     3. torch volumetric scattering off.
2. **Playtest:** walk the 3 crypt routes, solve the puzzle, watch the gate open and the rubble appear.
3. **Judge:**
   - darkness, torch views and floor glints;
   - plaque look;
   - fires and flicker in motion;
   - the checklist items above;
   - the open question on the hanging body's red stain.

### D1.19 Owner review 1: fix set R1 (lead, 2026-10-28)
**Owner findings** (screenshots from the playtest):
1. A "searchlight" on the chapel exterior: a lit ellipse on the roof around the roof hole, a lit disc around a lancet window, and a visible cone in the fog over the sacristy stair head.
2. The sacristy table and its props look clean and new.
3. At the stair head ("Descend into the crypt") a white greybox box is in view.
4. The clue plaque doesn't fit the scene. The owner asks to show the clue as a HUD message.

**Causes (lead survey):**
1. The four P8 moon spots, `Light_Chapel_Moon_S1/S2/S3` (Z 1469) and `Light_Chapel_Moon_Roof` (Z 2914), sit **outside** the chapel (pitch −38, yaw 35). They light the exterior around each opening, and their volumetric scattering shows the cone in the outdoor fog.
2. The sacristy props use the Fab Medieval_Tavern_Props materials, which are clean and saturated, and the table grime decals are too faint to see. `Note_Sacristy` is bright white paper. `Light_Sacristy_Table` is 400 lm at 115 cm over the table.
3. F1 enclosed only 4 of the 6 crypt rails. `Rail_Sac_W` (7395, −1100, 50) and `Rail_Up_S` (10650, −105, 50) are still white greybox.
4. `Clue_Diagram` (BP_EngravedDiagram) and `CD_PlaqueFrame`.
   - The game already shows text in the HUD through inspectable notes (`BP_Inspectable_Note`, with a per-instance `bodyText`; inspection displays it).
   - **Decision (D-073, owner direction):** the crypt clue becomes a readable note. The engraved plaque is removed.

**R1-A** (environment-designer, [EDITOR]; commit "P9-R1A: …")
1. **Rails.**
   - Add `Rail_Sac_W` and `Rail_Up_S` to `RAILS` in `gen_crypt_layout.py` with the F1 recipe:
     - mesh `SM_LB_Crypt_Block_100`, `MI_Crypt_StoneWA`, NoCollision (profile + `collisionEnabled`);
     - the rail AABB + 2 cm on each side and 2 cm on top, sunk 1 cm.
   - Regenerate (0 issues), then `place_crypt.py --cats lining --only CA_Parapet_Rail_Sac_W,CA_Parapet_Rail_Up_S` and `--check`.
   - `trace_world` through each rail must still hit the `Rail_*` actor.
2. **Clue swap.**
   1. Dump `Clue_Diagram` and `CD_PlaqueFrame` to `Docs/ArtTest/crypt/clue_swap_before.json`.
   2. Delete both actors. Remove the `CD_PlaqueFrame` record from the generator and regenerate. `--check` must still pass. Keep the `BP_EngravedDiagram` asset; delete no assets.
   3. Spawn `/Game/LastBell/Blueprints/Interactables/BP_Inspectable_Note` as `Note_Chains`, folder `Gameplay/Crypt`, pinned flat on the puzzle wall:
      - paper centre at (10920, −1507, −430), with its face normal pointing −Y into the room and its long edge horizontal;
      - its back 1–2 cm off the wall face (Y −1505);
      - find the rotation from the paper mesh's axes, then verify it with a capture.
   4. Set the instance `bodyText` to: "The chains must hang in balance before the winch will turn. A high. B low. C in the middle." Read it back after an explicit save.
   5. **Interaction check:** `trace_world` from (10920, −1650, −435) to (10920, −1490, −430) must hit `Note_Chains`. If the note's collision isn't hit, report it.
   6. The RouteBot and puzzle tests in the R1-B suite cover the puzzle; they don't need the clue.
3. **Props aging** (never edit Fab MIs or shared decal MIs).
   1. List every placed actor whose mesh is under `/Game/LastBell/ThirdParty/Fab/Dungeon/Medieval_Tavern_Props/`, plus `SM_Plate_00` and `SM_Dungeon_bench` (any area). Report the labels.
   2. For each distinct material on those meshes, read its parent and its texture parameters. Create `/Game/LastBell/Materials/Instances/Aged/MI_Aged_<OriginalName>` as an MI of `M_LB_Surface` with:
      - the original textures: base colour, normal, and roughness/AO/metal. Use `ARMTex` with `bUseARM` true only if the original is a packed R=AO, G=Rough, B=Metal; otherwise use the separate textures with `bUseARM` false;
      - `bWorldAlignedUV` false;
      - `BrightnessMul` 0.6, `Desaturation` 0.35, `BaseColorTint` (0.95, 0.92, 0.86);
      - `RoughnessMin` 0.55;
      - `bTopDust` true, `DustAmount` 0.55, `DustColor` (0.42, 0.40, 0.36).
      - Skip materials that are translucent, masked or emissive, and report them.
   3. Assign the aged MIs as instance overrides (`overrideMaterials` per slot) on every listed actor. Read them back after saving.
   4. **`MI_Sacristy_Table_Old`:** read its parent.
      - If it is `M_LB_Surface`: `BrightnessMul` × 0.75, `bTopDust` true, `DustAmount` 0.5.
      - Otherwise report it.
   5. **Table decals:**
      - Duplicate the decal MIs used by `Sa_Grime_Table_Stain_1/2`, `Sa_Grime_Table_Dust_L/R` and `Sa_Grime_Wax_Table` to `MI_Sa_Decal_<name>_Strong`, with the opacity parameter × 2 (capped at 1.0).
      - Assign them to those 5 decals only.
   6. **Note paper:** find the paper mesh component's material in `BP_Inspectable_Note` (read only).
      - If it is a project MI, tint it to aged parchment: `BaseColorTint` (0.80, 0.72, 0.56), or the closest available parameter. This ages all notes, which is intended.
      - If it is an engine material, report it and do not change it.
   7. **Disorder:**
      - `Sa_Cup` lies on its side (roll 90, resting on the tabletop: its bounds' min Z equals the table-top Z).
      - `Sa_BreadSlice` moves off the plate to (8330, −1470), on the tabletop.
4. **Wrap up:**
   - explicit saves;
   - no temp actors;
   - captures (editor viewport, `--raise`):
     - `r1_table`: camera (8150, −1600, 170) looking at (8300, −1430, 80);
     - `r1_stairhead`: (8050, −1100, 170) looking at (7395, −1100, 50);
     - `r1_note`: the `plaque_2m` pose;
   - commit and report.

**R1-B** (lighting-vfx, [EDITOR], after R1-A; commit "P9-R1B: …")
1. **Chapel moonlight moves inside** (D-074): replace each outside spot with an interior RectLight.
   1. Dump the 4 spots to `Docs/ArtTest/chapel/moon_spots_before.json`.
   2. For each lancet S1–S3:
      - Read the glass actor's bounds `Ch_Glass_S#` (the opening centre c and its 4 corners) and the south wall's inner-face Y (`Y_in`).
      - `d` = the spot's forward vector.
      - **Placement:** RectLight `Light_Chapel_MoonRect_S#` at c + t·d, with t = (Y_in + 10 − c.y) / d.y; rotation = the spot's.
      - **Size:**
        - `SourceWidth` = 0.95 × the extent of the 4 corners projected on the light's local Y;
        - `SourceHeight` = 0.95 × their extent on local Z.
      - **Light settings:**
        - `BarnDoorAngle` 15, `BarnDoorLength` 40;
        - colour (190, 205, 235); Movable; `castShadows` true;
        - `volumetricScatteringIntensity` 0.3; `attenuationRadius` 3000;
        - intensity units Lumens, starting at the spot's value.
   3. **Roof:** `Light_Chapel_MoonRect_Roof`, built the same way from the `Ch_Roof_S1` hole outline (the 4 bounding corners of the hole in the slab frame, taken to world space). It sits 10 cm below the slab's inner surface along d.
   4. **Tune and swap:**
      - Capture the P8 interior poses that show the S1–S3 and roof floor patches (the P8-9b pose list in `P8_CHAPEL_ART.md`), before and after.
      - Tune each rect light's lumens until its patch's central luma is within ±15 % of the before value.
      - The stained-glass pool decals must still sit on the patches; report any offset > 30 cm.
      - Then delete the 4 outside spots.
   5. **Pass:**
      - `r1_ext_chapel`: camera (4300, −2300, 250) looking at (6500, −780, 900);
      - `r1_stairhead`;
      - no lit ellipse or disc on the chapel roof or walls, and no exterior beam cone.
2. **G3 re-aim to the note:**
   - `L_Crypt_Moon_G3` rotation pitch −65.3, yaw 137.3 (aims at (10920, −1507, −430)), `attenuationRadius` 550.
   - Tune 60–250 lm until the note's pool luma is 0.25–0.45.
   - Re-orient `SA_Crypt_G3` along the new axis, length = the trace distance from the grate.
3. **Sacristy:**
   - `Light_Sacristy_Table` 400 → 250 lm.
   - Check the sacristy pose against the P8 sacristy luma target (`P8_CHAPEL_ART.md`); report it.
4. **Captures and checks:**
   - PIE Simulate, `--raise`, breaker armed:
     - `r1_table` and `r1_table_c` (candle proxy);
     - `r1_note` and `r1_note_c`;
     - `r1_ext_chapel`, `r1_stairhead`;
     - the P8 patch poses after;
     - `w_OS_c` and `04_c` (missing from P9-7).
   - Suite 78/78, with the named crypt lines and RouteBot.
   - Throttle `true`, editor clean, commit, report.

**Docs** (lead, in P9-8a):
- D-073: the crypt clue is a readable note; the plaque is removed (owner).
- D-074: chapel moonlight uses interior rect lights at the openings (supersedes the P8-9b outside spots).
- Update TECHNICAL_DESIGN/AI notes if they mention the engraved diagram.

**D1.19 addendum (owner GPU check, 2026-10-28):**
- **Ossuary, PIE new window, scalability 2:** GPU 14.72 ms, frame 16.67 ms (60 fps cap), game thread 11.38 ms, VRAM 3.79 / 5.03 GB, render resolution 87 % (1671 × 865).
  - That is within the 16.6 ms budget, with about 1.9 ms of headroom. R-38 stays open until the chain chamber is measured in the next playtest.
- **Added to R1-B: crypt candle bloom.** In the same screenshot, the player candle flame blooms into a large yellow ball. PP_Crypt EV100 0.2 overexposes the emissive flame.
  - On `PP_Crypt`, set `bOverride_BloomIntensity` true and `BloomIntensity` = the global post-process value × 0.4. Read the global value first.
  - The owner judges the result in the playtest; PIE Simulate has no player candle to capture.
- **Open owner question:** the hanging body `Ch_HangingBody` (`SK_Dead_Man`, one material `M_Dead_man`) has a bright red blood stain at the head end of the shroud. Keep it, or darken it to an old brown stain with a chapel-only MI (D-063: no gore)?
- **Owner decision (2026-10-28):** keep the hanging body's blood stain as it is. No change.

### D1.20 Owner review 1, item 5: candle-order clue as stained-glass saints, fix set R1-C (lead, 2026-10-28)
**Finding (owner):** the chapel's candle-order clue (`Clue_StainedGlass`, `BP_StainedGlassClue`) doesn't fit the scene. It is a flat panel of 12 engine primitives (cone body, sphere head and cone flame per saint) that reads as an infographic.

**Owner choice (D-075):** a real stained-glass panel: four robed saints, each holding a candle whose robe and flame halo carry the clue colour.
- The order, left to right as seen from the nave (looking +Y), stays **green, red, amber, blue** (Saint1..4; puzzle steps 3, 1, 4, 2).
- The puzzle candles, their BandRing colours, `BP_SequencePuzzle` and the Frame collision are unchanged.

**Task order:** R1-A (running) → **R1-C** → R1-B. R1-B's suite covers everything.

**R1-C** (technical-artist, [EDITOR] for steps 3–6; commit "P9-R1C: …")
1. **Texture `T_LB_StainedGlass_Clue`**, 512 × 1024 RGBA (A = lead mask, 1 = lead).
   - **Code:** add `clue_texture(seed)` to `Tools/textures/gen_chapel_textures.py`, with seed `"clue": 8999` in `SEEDS` and a `--only clue` target.
     - Copy the figure-drawing code from `east_light` into the new function rather than refactoring, so **no existing texture changes**.
     - Proof: run `--only clue`, and confirm `git status` shows no other generated file changed.
   - **Panel frame:** 112 × 232 cm (u = 0 at the left edge as seen from the nave, until step 4 says otherwise); 1 cm ≈ 4.5 px.
   - **Border:** 6 cm wide, alternating `PALE` and `BLUEGREY` segments, about 18 cm long, separated by lead.
     - No ruby, amber, green or blue in the border or background: those hues are reserved for the clue.
   - **Background:** diamond quarries (`diamond_field`, 60 × 96 px cells), with the table [(0.6, BLUEGREY × 0.7), (0.9, PALE × 0.55), (1.01, VIOLET × 0.6)], plus the same streak and fbm glass texture as the lancets.
   - **Top 40 cm:** a pointed-arch canopy line in lead, and a small bell motif (`PALE` × 1.2, about 22 cm tall) centred.
   - **Saints:** four columns, each 25 cm wide, inside the border (u from 6 cm to 106 cm). Each figure stands from z 14 cm to z 178 cm and has:
     - a robe in the clue colour × 0.85 (green (0.07, 0.65, 0.12), red (0.90, 0.05, 0.04), amber (0.95, 0.62, 0.05), blue (0.06, 0.18, 0.95)), with 3–4 lead fold lines;
     - a hood at robe × 0.6;
     - a **dark void face**, as in `east_light` (no faces);
     - a held candle at chest height: an ivory shaft (0.85, 0.80, 0.68), 3 × 14 cm;
     - a flame: a warm-white core (1.0, 0.95, 0.80), 3 × 6 cm;
     - a **halo disc** of radius 7 cm behind the flame, in the clue colour × 1.3, capped at 1.0.
   - **Lead lines:** 1.0–1.3 cm between every glass piece.
   - **Order:** columns 1–4 left to right are green, red, amber, blue.
   - Save a preview to `Docs/ArtTest/chapel/tex_stainedglass_clue.png`.
2. **Import:** `/Game/LastBell/Environments/Chapel/Textures/T_LB_StainedGlass_Clue`, with the same import settings as `T_LB_StainedGlass_Lancet_A`. Read those first and copy them (sRGB, compression, mips).
3. **Material:**
   - Read `MI_Glass_Lancet_A`: its parent and parameters.
   - Create `/Game/LastBell/Environments/Chapel/Materials/MI_Glass_Clue_Saints` with the same parent, the lancet values, and the texture parameter set to `T_LB_StainedGlass_Clue`.
   - Never edit `MI_Glass_Lancet_*`, `MI_LB_StainedGlass` or `MI_LB_ClueGlass`.
4. **Child Blueprint `/Game/LastBell/Blueprints/Puzzles/BP_StainedGlassClue_Saints`** (D-071 procedure, as P9-6b; never edit the parent).
   - The construction script sets `Glass` to `MI_Glass_Clue_Saints`, and `SetVisibility(false)` on `Saint1..4Body`, `Head` and `Flame` (12 components).
   - Don't call `ApplyOrder`.
   - Compile with warnings as errors.
   - **Swap:**
     - dump `Clue_StainedGlass` to `Docs/ArtTest/chapel/Clue_StainedGlass_before.json`;
     - spawn the child at the same transform (8750, 747, 300), yaw −90, and copy the instance `Order` and `Palette` values;
     - delete the old actor, apply the same label `Clue_StainedGlass` and the same folder;
     - dump `_after.json`, and diff it. Allowed differences: the class, the Glass material, and the 12 saint visibilities.
   - Save the map explicitly.
   - **UV orientation:** capture from (8750, 300, 170), pitch 29, yaw 90 (editor viewport, `--raise`).
     - If the order reads mirrored (blue on the left), regenerate with u flipped (a `--mirror` option on `clue_texture`), re-import, and recapture.
5. **Checks** (captures in `Docs/ArtTest/chapel/r1c_*`):
   - **(a) Order and hue**, on `r1c_clue_nave` from the pose above:
     - Split the glass rectangle into 4 vertical strips. Take the mean hue of the pixels with saturation > 0.35 in each strip.
     - Left to right they must read green, red, amber, blue, with adjacent hues ≥ 40° apart.
     - Each robe's mean luma must be ≥ 0.20.
   - **(b) From the puzzle:** capture `r1c_clue_candles` from the centroid of the 4 `BP_PuzzleCandle` actors at Z 170, looking at the panel centre (8750, 744, 422). The same order check must pass.
   - **(c) Look**, for the lead to judge: it reads as stained glass (lead lines, quarries, glow), the figures read as robed saints holding candles, there are no faces, and no flat cone shapes are left.
   - **(d)** `r1c_clue_close`, a 2 m view, for the owner.
6. **Wrap up:**
   - explicit saves;
   - editor clean, no temp actors;
   - commit with the generator change, the preview, the dumps and the captures;
   - report.

**Docs** (P9-8a): D-075, "candle-order clue as stained-glass saints (owner)", supersedes the P8 C1 "saints never changed" rule for visuals only.

### D1.21 R1-A outcome; additions to R1-C (lead, 2026-10-28)
- **R1-A accepted** (db20f3f).
  - Both rails are enclosed (`--check` 10/10).
  - `Clue_Diagram` and `CD_PlaqueFrame` are removed.
  - `Note_Chains`:
    - **Placement deviation:** centre at y −1504 rather than −1507, so it sits 1.5 cm off the proudest wall stone.
    - `bodyText` was read back.
    - `displayName` is "The Balance of the Chains".
    - The interaction trace hits the note.
  - 13 sacristy props carry `MI_Aged_*`.
  - **Table-dust deviation:** `DustAmount` was already 0.9 and is kept.
  - **Decal deviation:** the three `MI_Sa_Decal_*_Strong` MIs use Opacity 2.0. The graph saturates it, which strengthens faint areas; dial it back if it reads heavy.
  - `MI_LB_Paper` Color is now (0.80, 0.72, 0.56).
  - The cup lies on its side; the bread is off the plate.
- **Lead review of the captures:**
  - `r1_table`: the ware now reads dark and aged. The tabletop and walls still read as clean, hot-lit warm stone and wood; R1-B lowers the table light, then we judge again.
  - `r1_note_close`: the note reads as a flat lilac sticky-note rectangle, because `MI_LB_Paper` is a flat `BasicShapeMaterial` colour. Fixed in R1-C, step 7.
  - `r1_rail_up_s`: a white greybox band remains under the `Rail_Up_S` parapet: `Ground_3`'s shaft-side end face (y −100). Fixed in R1-C, step 8.
- **QA item, added to P9-8b:** `place_crypt.py --cats dress --check` reports 118 failures. Skulls and piles are 3.3–3.6 cm over the 3.0 tolerance; floor bones, bone-bin fills, `CD_SlabArm` and `CD_SkeletonStake` are off by up to 26.7 cm.
  - Find out whether this predates R1-A: run `--check` against the layout JSON at 8fa049a/e066901.
  - Compare actor transforms with the JSON (not only AABBs), and report whether anything actually moved.

**R1-C additions** (run after D1.20 steps 1–6, in the same session; commit "P9-R1C: …")
7. **Parchment for every note.**
   1. **Generator:** add `parchment_texture(seed)` to `gen_chapel_textures.py`, seed `"parchment": 9811`, `--only parchment`. It produces `T_LB_Parchment`, 512 × 512 RGB:
      - base (0.78, 0.70, 0.52), with fbm mottling of ±8 %;
      - 8–14 foxing spots (radius 4–18 px, colour × 0.75, soft edges);
      - edge darkening of 15 % within 30 px of the edges;
      - 9–11 lines of faint illegible script inside 40 px margins, line pitch 34 px, ink (0.18, 0.13, 0.09) at 55 % (small `wobble_curve` / `glyph_strokes` style; invented marks, no real letters or symbols).
      - Write a preview, `Docs/ArtTest/chapel/tex_parchment.png`.
      - No other generated texture may change.
   2. **Import** to `/Game/LastBell/Materials/Textures/T_LB_Parchment` (sRGB, default compression).
   3. **Material:**
      - **First try:** reparent `MI_LB_Paper` to `/Game/LastBell/Materials/Master/M_LB_Surface` via `ObjectTools.set_properties` on its `parent`. Then set:
        - `BaseColorTex` `T_LB_Parchment`;
        - `bWorldAlignedUV` false, `bUseARM` false;
        - `RoughnessMin` 0.8, `BrightnessMul` 1.0, `Desaturation` 0.
        - Read back, save explicitly, then confirm the parent in a fresh read.
      - **If the reparent is refused or doesn't persist:**
        - create `/Game/LastBell/Materials/Instances/MI_LB_Parchment` (parent `M_LB_Surface`, same values);
        - set it as an instance override on the paper component of each `BP_Inspectable_Note` instance (6 notes: Gatehouse, Nave, Sacristy, Ossuary, Cloister, Chains);
        - save, reload the level (`load_level`), and read back.
        - If the overrides don't persist, report it and leave them as they are.
   4. **Look:**
      - The script lines should run along the paper's long edge. If they run vertically on `Note_Chains`, regenerate with the texture rotated 90° (`--rotate`).
      - Check `MI_Chapel_PaperOld` (a child of `MI_LB_Paper`, used by `Ch_Paper_1..6`) still renders, with no default-grid or black. Its old `Color` override may be orphaned; report it.
   5. **Captures:** `r1c_note_close` (the `r1_note_close` pose) and `r1c_chapel_papers` (camera (8150, 300, 170) looking at (8150, 600, 0)).
8. **`Ground_3` end-face lining.**
   1. Read the AABBs of `Ground_3` and `CA_Lintel_Exit`.
   2. Add a `lining` record `CA_Lining_Ground3_End` to `gen_crypt_layout.py`:
      - `SM_LB_Crypt_Block_100`, `MI_Crypt_StoneWA`, NoCollision (profile + `collisionEnabled`), CastShadow on;
      - X from the shaft's X min to its X max (10500…10800, ±0; read them from `Ground_3`'s face extent);
      - Y −100…−96 (4 cm proud, on the shaft side);
      - Z from max(`Ground_3` min Z, `CA_Lintel_Exit` max Z) − 1 to `Ground_3` max Z + 1.
   3. Regenerate (0 issues), place with `--only CA_Lining_Ground3_End`, then `--cats lining --check`.
   4. Recapture `r1_rail_up_s`. **Pass:** no white band.
9. **Aged-prop polish:**
   - `MI_Aged_Cutlery` and `MI_Aged_Plate_00`: `Metallic` 1.0. First check in `M_LB_Surface` whether `Metallic` multiplies or replaces the ARM B channel; report it.
   - `MI_Aged_Bread` and `MI_Aged_Bread_Slice`: `BrightnessMul` 0.45.
   - Read back and save.

### D1.22 R1-C outcome; R1-B go (lead, 2026-10-28)
- **R1-C accepted** (5fbef54).
- **Stained-glass saints:** `T_LB_StainedGlass_Clue` → `MI_Glass_Clue_Saints` (EmissiveIntensity 5.5) on the child `BP_StainedGlassClue_Saints`. The swap diff is clean, and `Order`/`Palette` were kept.
  - From the nave the panel reads green, red, amber, blue. Robe hues are ≥ 44° apart and robe luma ≥ 0.249.
  - **Lead review:** it reads clearly as stained glass, with robed saints holding candles and no faces. The owner judges whether it is too bright or clean for the ruined chapel; an aging pass (grime, a cracked pane, lower emissive) is available if asked.
  - **Still unmeasured:** check (b), the pose from the puzzle candles. It moves to R1-B.
- **Parchment notes:** `MI_LB_Paper` was reparented to `M_LB_Surface`, and persists after reload.
  - **Asset-name deviation:** the shipped texture is `T_LB_Parchment_Rot90` (rotated so the script runs along the long edge). The unrotated `T_LB_Parchment` is unused.
  - `MI_Chapel_PaperOld` now renders brighter, because its `Color` override is orphaned.
- **`CA_Lining_Ground3_End`:** placed at Z −41…1. **Lead-approved deviation:** the formula assumed the lintel covered the face; it doesn't. The white band is gone.
- **Aged metal:** `Metallic` is ignored when `bUseARM` is true, and the Fab `AO_R_MT` B channel drives metal. **Accepted:** the cutlery and plate keep the Fab metal mask.

**R1-B additions** (lighting-vfx; run with D1.19 R1-B and the D1.19 addendum bloom item):
- **H1. Old-paper brightness:** `MI_Chapel_PaperOld`, set `BrightnessMul` 0.6 and read it back.
- **H2. Unused texture:** check `get_referencers` on `/Game/LastBell/Materials/Textures/T_LB_Parchment`.
  - If there are zero referencers, delete it with the editor's asset delete, and report the tool used.
  - Otherwise leave it and report.
- **H3. Puzzle-candle view of the clue:** capture `r1c_clue_candles` at (8810, 0, 170), pitch 18.66, yaw 94.61, and run the D1.20 step 5(a) strip-hue order check on it (green, red, amber, blue, adjacent hues ≥ 40°, robe luma ≥ 0.20).
- **H4. Captures:** the notes read dim on the wall (crypt) and hot on the table (sacristy). The R1-B G3 re-aim and the table-light change address both, so capture `r1_note` and `r1_table` after those changes.
  - For `r1_table`, use the R1-A replacement pose: (8190, −1290, 150), pitch −20.9, yaw −51.84.
  - For the stair head, use (7960, −1100, 170) looking at (7395, −1100, 50). The D1.19 pose sits inside the door wall.

### D1.23 R1-B step 1 redesigned: aperture masks (gobos) on the outside moon spots (lead, 2026-10-28)
**Why:** the interior RectLights (D1.19 R1-B step 1) flood the nave. With no opening to clip them, there are no window-shaped patches.
- At the matched lumens, the frame mean is 0.60 against the P8 target of 0.04–0.08.
- The barn doors made no visible difference.
- That approach is dropped (88092f8 WIP). **D-074 is revised:** keep the P8 outside spots, unchanged, and add a hidden, shadow-only aperture mask in front of each spot.

**What the mask does:** the spot's light passes only through a rectangle matching the projection of its window or roof hole. So:
- outside, only the opening itself is lit;
- inside, the window-shaped patches stay as they are.
- Volumetric scattering on these 4 spots goes to 0, which removes the beam in the outdoor fog. The interior shaft cards carry the beam look.

**R1-B step 1 (replaces D1.19 R1-B steps 1.2–1.5).** Lighting-vfx, [EDITOR]:
1. **Delete the 4 untuned `Light_Chapel_MoonRect_*`.** They were added in this fix set and are at intensity 0. Keep their `geom.json` and scripts for the record.
2. **Geometry**, for each spot `Light_Chapel_Moon_<K>` (K = S1, S2, S3, Roof):
   - L = the spot location; d, r, u = the spot's forward, right and up unit vectors (from its rotation).
   - **Opening corners** C1..C4, in world space:
     - lancets: the 4 corners of the `Ch_Glass_S#` opening face (from its bounds on the window plane);
     - roof: the 4 corners of the hole-aperture bounding box already computed in `Tools/crypt/r1b/geom.json`, in world space.
   - **Gobo plane:** distance D = 150 cm along d. For each corner, v = C − L and p = L + v·(D / (v·d)); its plane coordinates are (y, z) = ((p − L)·r, (p − L)·u).
   - **Aperture:** y from (min y − 1.5) to (max y + 1.5), z from (min z − 1.5) to (max z + 1.5), in cm.
   - **Outer frame:** half-size H = D·tan(outer cone) + 15 (14° gives H ≈ 52.4); round H up to the nearest 5 cm.
3. **Gobo pieces.** Four `StaticMeshActor`s per spot, `Gobo_Moon_<K>_T/B/L/R` in folder `Lighting/Chapel/Gobos`:
   - **Mesh:** `/Engine/BasicShapes/Cube` (100 cm, pivot centre); rotation = the spot's rotation, so local X is along d; thickness 2 cm along local X (scale X 0.02).
   - **Coverage:**
     - T covers y −H…H, z from the aperture's max z to H;
     - B covers y −H…H, z from −H to the aperture's min z;
     - L covers y from −H to the aperture's min y, z from the aperture's min z to its max z;
     - R covers y from the aperture's max y to H, z from the aperture's min z to its max z.
     - Each piece's centre is L + D·d + y_c·r + z_c·u. Scale its local Y and Z by its extent / 100.
   - **Render/shadow flags:**
     - `bHiddenInGame` true;
     - `CastShadow` true, `bCastHiddenShadow` true;
     - `bAffectDistanceFieldLighting` false, `bAffectDynamicIndirectLighting` false;
     - `bVisibleInRayTracing` false (if exposed);
     - NoCollision (profile + `collisionEnabled`).
   - **Lighting channels:** Channel0 false, Channel1 true. The gobo then shadows only lights on Channel1, so it never casts a moon or directional shadow on the world.
4. **The 4 spots:**
   - lighting channels Channel0 true **and** Channel1 true;
   - `volumetricScatteringIntensity` 0.1 → **0**;
   - everything else unchanged (location, rotation, lumens 9100/15000, cones, shadows, colour).
   - Read back all values. Save explicitly. Commit "P9-R1B: chapel moon gobos …".
5. **Verify** (PIE Simulate, fresh session, `--raise`, breaker):
   1. **Exterior:** `r1_ext_chapel`, camera (4300, −2300, 250) looking at (6500, −780, 900); `r1_stairhead`, (7960, −1100, 170) looking at (7395, −1100, 50).
      - **Pass:** no lit ellipse or disc on the roof or walls around the openings beyond the opening and its reveal; no beam cone in the outdoor fog; no new square or dark shadow anywhere in these views.
   2. **Interior:** the P8 patch poses (`r1b_patch_S1/S2/S3/Roof`) and `r1b_p8_*` against the committed `_before` captures.
      - **Pass:** each patch's central luma is within ±15 % of before; the patches stay window-shaped; the pool decals stay on them.
      - If an aperture clips a patch edge, widen that aperture by 2 cm per side, at most twice, and report it.
   3. **Shadow leak check:** with the gobos present, capture `r1b_courtyard_moon`, camera (5500, −2400, 400) looking at (5500, −1500, 0), and compare it with a capture taken with the gobos temporarily moved +10000 Z, in the PIE world only.
      - **Pass:** mean absolute pixel difference < 1.0, meaning the gobos cast no directional/moon shadow.
      - **If it fails:** lighting channels don't gate shadows in this setup. Report it, and set the gobo `CastShadow` false on the B piece first to locate the shadow. Don't touch `DirectionalLight_1`.
6. **If gobo shadows don't work at all** (the exterior patches are still lit; hidden-shadow casting not supported with this shadow method):
   - report it with captures, and leave the gobos placed but `CastShadow` false;
   - keep only the scattering-0 change, which still removes the outdoor beam;
   - the lead decides.

The rest of R1-B is unchanged (D1.19 R1-B steps 2–4, the D1.19 addendum bloom item, D1.22 H1–H4), now that the redesigned step 1 is done.

### D1.24 R1-B outcome; proposed follow-up set R2 (lead, 2026-10-28)
- **R1-B accepted** (88092f8, 2c9bcb1, 0aae5e9, 02a2e13, fa95078).
- **Suite:** 78/78; crypt WalkPaths SacristyToCrypt, FloodedLedge and CryptToCloister PASS; chapel WalkPaths PASS; RouteBot.Monastery Success; Warden crypt loop 67.1 s, 0 stuck.
- **Chapel moon (D1.23, gobos):** 16 hidden shadow-only cubes on Channel1; the 4 spots use channels 0+1 with scattering 0.
  - Interior patches are within 3 %: S1 0.973, S2 0.992, S3 1.024, Roof 1.000.
  - The moon-shadow leak check is 0.43 (pass).
  - The window disc and the stair-head lit wall are gone.
  - **Residual:** a lit parallelogram on the roof slab around the hole, because the aperture is the hole's bounding box.
  - Poses 04, 05 and 14 are 13–17 % darker without the spot scattering haze. The owner judges this in the playtest.
  - The stair-head haze is the global moon's scattering. Not changed.
  - **Owner check:** in PIE *Simulate* the gobos render as two bright blobs in the sky, because Simulate ignores `bHiddenInGame`. The owner checks that they are invisible in a normal Play session.
- **G3:** aimed at `Note_Chains`, 250 lm, radius 550, `SA_Crypt_G3` re-oriented.
  - The note is lit (pool median 0.357), but it sits at the lower edge of the pool, because the beam grazes the wall. The note is small (28 × 20 cm).
- **Sacristy:** table light 250 lm, P8 pose mean 0.0505 (target 0.03–0.08). The props read dark and aged; the table still reads warm under its candle. The owner judges.
- **Crypt:** `PP_Crypt` bloom 0.27.
- **Paper:** `MI_Chapel_PaperOld` `BrightnessMul` 0.6.
- **`r1c_clue_candles`:** order holds; red/amber gap 45.6°.
- **Candle views:** `w_OS_c` central-40 % is 0.394 (target (b) passes on all three walls). `04_c` captured.
- **Housekeeping:**
  - `T_LB_Parchment` was deleted in the editor (0 referencers), but the file is still on disk and the package is dirty. When closing the editor, choose **Don't Save**. Finish the deletion in the Content Browser in R2.
  - The layout JSON still has the old G3 rotation.
  - The stray empty `C:\c\…` folders from a capture run were removed by the lead.

**Proposed R2** (only with the owner's go):
1. **Roof gobo.** Replace the 4 `Gobo_Moon_Roof_*` cubes with one Blender-built plate `SM_LB_Gobo_RoofHole` (110 × 110 × 2 cm).
   - Its hole is the roof-hole outline polygon (`build_kit.hole_cutters`) projected onto the gobo plane, with a 1.5 cm margin.
   - Same flags (hidden, shadow-only, Channel1). Pass: no lit roof slab beyond the hole edge; the roof patch stays within ±15 %.
2. **Note readability.**
   - Scale `Note_Chains` × 1.5 (42 × 30 cm), keeping it on the wall.
   - Re-aim G3 so the note sits at the pool centre: the aim point is 40 cm below the note centre, to compensate for the grazing angle.
   - Pool on the note 0.30–0.45.
3. **Layout JSON:** update the G3 record (rotation, radius, lumens) in `gen_crypt_layout.py` and regenerate, so `place_crypt.py --cats light --check` passes.
4. **Finish deleting `T_LB_Parchment`** (Content Browser delete, then confirm the file is gone).
5. **P9-8:** docs (D-073 note clue, D-074 gobos, D-075 saints glass, MCP_NOTES additions) and QA (including the 118-failure dress `--check` investigation). Then the owner playtest and "approve and merge".

### D1.25 Owner review 2: fix set R2 (lead, 2026-10-28)
**Owner findings (playtest screenshots):**
1. The first puzzle item (chapel Mechanism 1 on the altar) doesn't fit.
2. The 3 crypt levers don't fit.
3. The crypt lights show a strong staircase effect in the beams.
4. The crypt door doesn't look right.
5. The note at the start of the game can't be picked up.

**Causes (lead survey):**
1. The altar's orange cylinder with studs is the P8 cosmetic shell `Mech_Shell_Cyl` (`SM_LB_Prop_MechShell_Cyl`, `MI_LB_Bronze`) plus `Mech_Shell_Cube`, `_2`, `_3` and `_4` (`MI_LB_Iron`), around `Altar_Ritual1` (`BP_RitualMechanism_C_1`, at (8900, 0, 80); Core is an engine Cylinder 80 × 80 × 50 at relative (0, 0, 75)). The turning Core is hidden inside the shell.
2. `Lever_A/B/C` (`BP_DialLever_C_0/1/2`, at (11040 / 10920 / 10800, −1503, −600), yaw −90) are the P4 greybox: components `backplate`, `rail`, `arm`, `handlePivot`, `weight`, `notchHigh/Mid/Low`, `label` (TextRender).
3. Crypt moon spots G1/G2 (scattering 1.5, `bCastVolumetricShadow` true) cast voxel shadows of the grate bars into the volumetric fog, which steps the beam edges.
4. `Door_Sacristy` (`BP_Door_Base_C_4`, the door from the sacristy to the crypt stair) has a `DoorMesh` that is an engine Cube (10 × 100 × 220, relative (0, 50, 110), actor scale (1, 1.18, 1.08)) with the default checker material. `Door_ChapelMain` (`C_3`) is the same cube with `MI_Weathered_Planks_WA`.
5. `Note_Gatehouse`'s bounds are Z 45.10–45.40, but its crate `KP_Crate_Note` tops out at Z 45.42, so the crate's collision covers the note and blocks the interaction trace.

**Owner choices (D-076):**
- Mechanism 1 becomes a **bell wheel**: a horizontal iron wheel with 8 small bronze bells, on an axle in the altar, which turns a quarter turn.
- **Both** doors get the Dungeon pack's iron-strapped wooden door (`SM_Dungeon_door`).

**Order:** R2-A (meshes) → R2-B (Blueprints and swaps) → R2-C (lighting). The D1.24 items are folded in.

#### R2-A (technical-artist; Blender headless, then [EDITOR] import; commit "P9-R2A: …")
Follow the props conventions in `Tools/blender/props/build_props.py`: seeded, MAT_* slots, UCX, `verify_props`, renders. Pivot is bottom-centre unless stated.

1. **`SM_LB_Prop_BellWheel_A`** (≤ 12k tris; Nanite on):
   - **Axle:** iron, Ø 8, Z 0…50, with a ball finial Ø 8 at Z 50…58.
   - **Hub:** Ø 16 × 8 at Z 34…42.
   - **Rim:** a ring of major radius 40 with a 4 × 3 cm section, centred at Z 38 (outer Ø 84).
   - **Spokes:** 6 iron spokes, 3 × 2 cm, at Z 38.
   - **Bells:** 8 bronze bells every 45° at radius 40, each hanging from a 2 cm iron loop under the rim. Lathe profile: lip Ø 9, height 11, crown Ø 4; a clapper ball Ø 2. The bell mouth is at about Z 22.
   - **Slots:** MAT_Iron, MAT_Bronze.
   - **UCX:** one box 84 × 84 × 58.
2. **Dial-lever set.**
   1. **Survey first** (editor, read only):
      - `BP_DialLever`'s template components: mesh, relative location/rotation/scale, and the resulting local-space AABB;
      - `notchPitch`, `startPitch`, and how `arm` hangs under `handlePivot`.
      - Write this to `Docs/ArtTest/crypt/survey_diallever.md`.
   2. **Build** each mesh to the surveyed AABB of the component it replaces (±1 cm), with the pivot where that component's mesh pivot is (engine Cube or Cylinder = centre), so the child BP uses scale 1:
      - **`SM_LB_Prop_DialLever_Backplate`:**
        - an oak board with two iron straps and 4 rivets per strap;
        - an iron label plate, 18 × 18 cm, riveted at the top centre where the `label` text sits, flush behind the text;
        - MAT_Wood and MAT_Iron.
      - **`SM_LB_Prop_DialLever_Quadrant`** (replaces `rail`): an iron quadrant plate with three notch slots at the high, mid and low arm angles derived from `notchPitch`. MAT_Iron.
      - **`SM_LB_Prop_DialLever_Arm`:** an iron rod Ø 2.5 with a turned wooden grip (Ø 4.5 × 12) at the free end. MAT_Iron and MAT_Wood.
      - **`SM_LB_Prop_DialLever_Weight`:** an iron counterweight (Ø 10 × 14) with a top ring, plus 40 cm of chain links rising from it. The chain sits inside the old `weight` AABB extended upward; record the final AABB. MAT_Iron.
      - **`SM_LB_Prop_DialLever_NotchStop`:** an iron stop (4 × 4 × 3) with a bone-white painted face (MAT_Paint, (0.75, 0.72, 0.62)).
3. **`SM_LB_Gobo_RoofHole`:**
   - a 110 × 110 × 2 cm plate (pivot centre, local X = thickness), no UCX, Nanite off;
   - its cut-out is the roof-hole outline polygon (`build_kit.hole_cutters(441)`, the same frame as `Tools/crypt/r1b/geom.json`), projected onto the `Light_Chapel_Moon_Roof` gobo plane at D = 150, as `s3_gobos.py` does with the bbox corners, plus a 1.5 cm outward offset;
   - local Y and Z are the light's right and up.
4. **Import:**
   - destination `/Game/LastBell/Environments/Props/Procedural/Chapel/` (bell wheel, gobo) and `/Game/LastBell/Environments/Crypt/Meshes/` (lever set);
   - MAT_Iron → `MI_LB_Iron`, MAT_Bronze → `MI_LB_Bronze`, MAT_Wood → `MI_Prop_Wood_Weathered`, MAT_Paint → a new `MI_LB_PaintBone` (child of `M_LB_Surface`, flat tint (0.75, 0.72, 0.62), Desaturation 0.2);
   - the gobo gets `MI_LB_Iron`.
   - `verify_props` all pass.
   - Renders in `Docs/ArtTest/props/r2_*.png`. LOOK, and iterate until the wheel reads as an iron wheel with hanging bells and the lever as a forged iron lever on an oak board with a hanging counterweight.

#### R2-B (unreal-blueprint-engineer, [EDITOR]; the P9-6b child-BP procedure; commit "P9-R2B: …")
1. **Bell wheel:**
   - **Child BP** `/Game/LastBell/Blueprints/Interactables/BP_RitualMechanism_ChapelBells`. Follow the `BP_RitualMechanism_CryptWinch` pattern (copy the parent construction body; a `RequiredTags` variable feeds `SetRequiredStateTags`).
     - Core: `SM_LB_Prop_BellWheel_A`, relative (0, 0, 50), scale 1, with the Interaction channel set to Block.
     - CoreMarker: hidden.
     - Pedestal: hidden, collision unchanged.
   - **Swap `Altar_Ritual1`:** dump before and after, copy every instance value (including the InteractComp tags), same label and folder.
   - **Remove the shell:** dump and delete the 5 `Mech_Shell_*` actors.
   - **Checks:**
     - the wheel's base sits on the altar top within 1 cm (read the altar bounds);
     - an interaction trace from the nave side at eye height hits the Core.
2. **Levers:**
   - **Child BP** `/Game/LastBell/Blueprints/Puzzles/BP_DialLever_Crypt`.
     - First read the parent construction script. Copy its body, then set the R2-A meshes (scale 1) on `backplate`, `rail`, `arm`, `weight` and the three `notch*`.
     - `label` TextRender colour (0.78, 0.74, 0.62); size unchanged.
   - **Swap `Lever_A/B/C`:** copy `dialComp` settings, `labelText`, `lockTag` and tags; same labels and folder; dump and diff each.
   - **Check:** in PIE, each lever's arm reaches the high, mid and low notch stops visually (one capture per lever at the high position).
3. **Doors:**
   - **Child BP** `/Game/LastBell/Blueprints/Interactables/BP_Door_Base_Dungeon`. The construction script sets `doorMesh` to `SM_Dungeon_door` (bounds X 2.4…15.8, Y −43.3…52.6, Z 0.45…182.7), with relative transform and scale chosen so its AABB fills the old slab's local extents: X −5…5 (thickness can stay 13.4, centred), Y 0…100, Z 0…220.
   - **Hinge side:** if the mesh's iron hinges end up on the side away from the `hinge` pivot (Y 0), mirror with a negative Y scale and recompute.
   - **Collision:** if `SM_Dungeon_door` has no simple collision, report it and add a box simple collision to the mesh (StaticMeshTools). Never use complex as simple on a moving door.
   - **Swap `Door_Sacristy` and `Door_ChapelMain`:** copy `openStateTag`, `autoOpenTag`, `openYaw`, `openSign`, `bInteractable`, the InteractComp values and the actor scale (1, 1.18, 1.08); dump and diff.
4. **Notes:**
   - `Note_Gatehouse`: raise it so its min Z is the crate's max Z + 0.4 (about Z 45.72).
   - **For all 6 notes:**
     - a vertical trace from note centre +50 to −50 must first hit within 0.5 cm of the note's top;
     - a trace from 120 cm away, at eye height 160 cm above the note's floor, toward the note centre must hit the note.
     - Fix any failure by raising the note by ≤ 1 cm.
   - `Note_Chains`: scale × 2 (56 × 40 cm; owner, 2026-10-28), back still 1.5 cm off the proudest wall stone. Keep the centre at Z −430 unless the bottom edge would go below Z −455; if so, raise it so the bottom is at Z −455.
5. **`T_LB_Parchment`:** finish the delete with an editor tool that removes the file. If none works, report it; never delete the file outside the editor.
6. **Suite:** 78/78 (ChapelNave and ChapelSacristy pass through both doors; RouteBot uses the bell wheel and the levers), plus captures. Commit.

#### R2-C (lighting-vfx, [EDITOR]; commit "P9-R2C: …")
1. **Staircase fix:**
   - `L_Crypt_Moon_G1/G2`: `bCastVolumetricShadow` false, `volumetricScatteringIntensity` 1.5 → 0.5.
   - `L_Crypt_Torch_T1..3`: scattering 1.0 → 0.5.
   - **Captures** (PIE): `05`, `07`, `08`, `d11`, plus the owner's flooded-passage view, about (9250, −2380, −440) looking +X.
   - **Pass:**
     - no stepped beam edges (lead and owner judge);
     - the means of 05, 07 and 08 within ±15 % of the F7 values.
2. **Roof gobo:**
   - Replace the 4 `Gobo_Moon_Roof_*` cubes with one `SM_LB_Gobo_RoofHole` actor `Gobo_Moon_Roof`: centre at L + 150·d, the spot's rotation, the same flags and Channel1-only.
   - **Pass** (`r1b_ext_chapel` pose):
     - no lit roof slab beyond the hole edge;
     - the roof patch within ±15 % (`r1b_patch_Roof`);
     - the moon leak check < 1.0.
3. **G3 re-aim** to the scaled `Note_Chains`: aim point 40 cm below the note centre (it compensates for the grazing angle).
   - Note pool 0.30–0.45, with the note inside the brightest third of the pool. Tune 150–300 lm.
   - Re-orient `SA_Crypt_G3`.
4. **Layout JSON:**
   - Update the G1/G2/G3/torch records in `gen_crypt_layout.py`: G3 rotation, radius and lumens; the scattering and volumetric-shadow flags. Extend `place_crypt.py --cats light --check` to read them.
   - Regenerate, then run `--check` (16/16).
5. **Wrap up:** suite 78/78, captures, commit.

**Then P9-8** (docs + QA, D1.18), the owner playtest, and "PHASE 9 READY FOR YOUR REVIEW".

### D1.26 R2-A review: lever rework R2-A2 (lead, 2026-10-28)
- **Accepted** (0bf92d9, 76b443a):
  - `SM_LB_Prop_BellWheel_A` reads as an iron wheel with 8 hanging bronze bells (`r2_cycles_bellwheel.png`). Its 89 cm visual width (the bell lips) is accepted.
  - `MI_LB_PaintBone` is accepted, with roughness 0.65–0.85.
  - The backplate and arm are accepted.
- **Not accepted (lever):** the greybox layout carried over literally does not read as one mechanism (`r2_cycles_lever_high.png`, `r2_lever_mid_side.png`):
  - the notch rail and stops float 40 cm in front of the board with nothing holding them;
  - the weight's chain rises from the arm tip and ends in mid-air.
- **Gobo:** a 1.5 cm offset in the plane is about 20 cm at the slab. Use **0.7** (about 9 cm at the slab, enough to cover the 0.6 cm parallax).

**R2-A2** (same agent; Blender plus re-import over the same asset names, or new names if re-import over an existing asset is impossible; report which; commit "P9-R2A2: …"):
1. **`SM_LB_Prop_DialLever_Quadrant` becomes a lever-frame sector plate:**
   - an iron sector in the mesh XZ plane, with its pivot at the sector centre (the lever's rotation axis);
   - radius 48, spanning −42°…+42° about +X; 1.5 cm thick in Y;
   - a raised outer arc rim, 2 × 2 cm;
   - three V-notches, 2 cm deep, cut into the rim at −35°, 0° and +35°;
   - a bone-white painted peg (MAT_Paint, Ø 2.5 × 2 cm, protruding +Y) beside each notch;
   - an iron mounting foot at the narrow end that reaches back to the board face, local X −6…0 (the pivot is 6 cm in front of the board);
   - slots MAT_Iron and MAT_Paint.
   - In R2-B the child BP puts `rail` at the `handlePivot` location (6, **+4**, 45), rotation 0, scale 1, so the sector sits just beside the arm's swing plane. All three `notch*` components are **hidden**; the pegs are now part of the quadrant.
2. **`SM_LB_Prop_DialLever_Weight`:**
   - remove the rising chain;
   - make it a squat cast-iron counterweight ball, Ø 11, with a cast collar ring where it meets the arm;
   - keep it rigid at the arm tip (same component placement).
3. **`SM_LB_Prop_DialLever_Backplate`:**
   - add an iron pulley bracket centred at the board top: a wheel Ø 10 at local Z +50, 4 cm in front of the board;
   - add a static chain (6–8 links) running from the pulley up and back into an iron wall eyelet 30 cm above the board top, flush with the board's back plane (it reads as the chain going into the wall);
   - the label plate stays below the pulley; check the `label` TextRender at (3.6, 0, 82) still sits on the plate, and move the plate if needed;
   - record the new AABB (taller than 90).
4. **Gobo:** set `GOBO_OFFSET` to 0.7, rebuild, re-import `SM_LB_Gobo_RoofHole`, and report the new open area.
5. **Verify:**
   - `verify_props` passes;
   - renders of the assembled lever at −35, 0 and +35 (3/4 and side), with the quadrant placed at (6, 4, 45) relative to the pivot setup;
   - **LOOK:** the stops sit at the notches where the arm's grip passes, nothing floats, and the chain visibly enters the wall.
   - Commit and report.

**R2-B update** (D1.25 R2-B step 2, levers): the child construction script also sets `rail` relative location (6, 4, 45), rotation (0, 0, 0), scale 1, and `SetVisibility(false)` on `notchHigh`, `notchMid` and `notchLow`.

### D1.27 R2-B review; editor hang; proposed R2-A3 + R2-B2 (lead, 2026-10-29)
**R2-B gameplay work is accepted** (73e1f16, f2b3a20):
- Suite 78/78. WalkPaths pass (ChapelNave, ChapelSacristy, SacristyToCrypt, FloodedLedge, CryptToCloister). RouteBot.Monastery uses the bell wheel, both doors and the levers. Warden crypt loop 67.0 s, 0 stuck.
- Before/after dumps of the 6 swapped actors differ only where the spec allows. `InteractComp` has 0 differences on every swap.
- Notes:
  - `Note_Gatehouse` raised 0.719 cm; its vertical trace hits the note top.
  - All 6 notes pass the vertical trace and the 120 cm eye-height trace from every clear direction.
  - `Note_Chains` is 2× (56 × 40 cm) and reads well at 2 m (`r2b_note_chains_2m_pie.png`).
- `T_LB_Parchment` is fully deleted (file gone, git `D`).
- Real bug found and fixed: the R2-A lever meshes had no simple collision, so the interaction trace missed them. A 1-hull convex was added.

**Editor hang (open):**
- The editor's game thread deadlocked inside `save_assets` for `SM_LB_Prop_DialLever_Arm`. The log stops at `InternalPromptForCheckoutAndSave started...` (19:22 UTC); CPU is idle and both editor windows report hung. The file is not read-only.
- On disk: Backplate and Quadrant have their convex collision. **Arm and Weight do not** (their collision exists only in the hung editor's memory).
- Nothing else in editor memory is wanted. The map is saved. The parent BPs `BP_RitualMechanism`, `BP_Door_Base` and `BP_DialLever` are dirty in memory and must NOT be saved.
- The R2-B agent was stopped. Its queued save client is gone.
- **Recovery (owner):** end the editor (Task Manager → UnrealEditor → End task; equivalent to Don't Save). On the next start, skip any autosave restore. The first step of the next run re-does the Arm/Weight collision (R2-A3 step 5).

**Visual review of the R2-B captures:**
1. **Bell wheel: accepted** (`r2b_bellwheel_close_pie.png`, `r2b_bellwheel_nave_pie.png`). It reads as an iron wheel with hanging bronze bells.
   - **Defect:** `Ch_Altar` has a Ø≈84 cm opening in its top. The removed shell used to hide it, so the wheel now stands in a dark round pit. → R2-B2 step 1.
2. **Levers: not accepted as they stand** (`r2b_pie_lever_A_high_sector_side.png`, `r2b_lever_B_2m_mid_all_levers.png`).
   - The arm swings in the actor's XZ plane, at right angles to the wall, so the solid R48 sector plate sticks 48 cm out of the wall.
   - From any oblique view each lever reads as a large flat black fan or shield, and the three fans dominate the wall.
   - Nothing is wrong with the mechanism logic; the problem is the solid plate's visual mass. → R2-A3.
3. **Doors: the mirror is accepted** (handle on the free edge). Hinge sense is confirmed in the owner playtest by opening each door.
   - **Defect:** `SM_Dungeon_door` has 1–2 cm gaps between its planks. The sky (sacristy door) or the lit interior (chapel main door from outside) shows through, so the doors read as fence gates. → R2-B2 step 2.
   - The chapel main door's outside face has no straps. That is the mesh's back face (battens); accepted.
4. **Notes: accepted.**

#### R2-A3 (technical-artist; Blender headless, then [EDITOR] re-import; commit "P9-R2A3: …")
Start only after the editor is restarted and `L_Monastery` is loaded clean.
1. **`SM_LB_Prop_DialLever_Quadrant` becomes a skeletal quadrant.** Rebuild in `Tools/blender/props/build_props.py` (same function, same seed, same pivot and orientation as R2-A2: sector in the mesh XZ plane, pivot at the sector centre, span −42°…+42° about +X).
   - Remove the filled sector plate and replace it with:
     - **Arc band:** radial R 42…48 (6 cm deep), 1.5 cm thick in Y (same Y position as the old plate), spanning −42°…+42°.
     - **Rim:** the raised outer rim on the band, 2 × 2 cm, as in R2-A2.
     - **Notches:** three V-notches, 2 cm deep, through rim and band at −35°, 0° and +35°, as in R2-A2.
     - **Pegs:** three bone-white pegs (MAT_Paint, Ø 2.5 × 2 cm, protruding +Y) beside the notches, at the same places as R2-A2.
     - **Two edge struts:** along −42° and +42°, from R 6 to R 42, 3 cm wide, 1.5 cm thick in Y.
     - **One centre strut:** along 0°, from R 6 to R 42, 2 cm wide, 1.5 cm thick.
     - **Hub ring:** at the pivot, outer Ø 12, inner Ø 4, 1.5 cm thick in Y.
     - **Mounting foot:** unchanged (local X −6…0, from the hub back to the board face).
   - Slots MAT_Iron and MAT_Paint. Triangle count ≤ the R2-A2 quadrant's.
   - AABB must equal R2-A2's within ±1 cm, so `rail` at (6, 4, 45) in `BP_DialLever_Crypt` needs no change.
2. **Re-import** over the same asset `/Game/LastBell/Environments/Crypt/Meshes/SM_LB_Prop_DialLever_Quadrant`, with the same material slots (`MI_LB_Iron`, `MI_LB_PaintBone`).
3. **Collision:** add one 1-hull convex simple collision to the quadrant (StaticMeshTools, as R2-B did). It may fill the open frame, which is fine.
4. **`verify_props`:** all pass.
   - Blender renders `Docs/ArtTest/props/r2a3_lever_{high,mid,low}_3q.png` and `_side.png`, with the assembly placed as in R2-A2.
   - **LOOK:** the quadrant reads as an open iron arc with three pegged notches; through the open frame the board and the wall behind can be seen. Iterate until it does.
5. **Arm and Weight collision (re-do lost work):** add one 1-hull convex simple collision to `SM_LB_Prop_DialLever_Arm` and `SM_LB_Prop_DialLever_Weight`.
   - Save each mesh package on its own `save_assets` call (one package per call) and check `is_dirty` = false after each.
   - Check that Backplate's collision survived the restart (read the body setup: 1 convex element).
6. **Editor captures** (PIE, `capture_poses.py --raise`, the R2-B poses): `r2a3_pie_lever_A_high_sector_side.png`, `r2a3_lever_B_2m_mid_all_levers.png`.
   - **LOOK:** no fan or shield silhouette; the arm reads as moving along a notched arc.
7. Suite 78/78. Commit.

#### R2-B2 (unreal-blueprint-engineer, [EDITOR]; after R2-A3; commit "P9-R2B2: …")
1. **Altar bearing plate.** New StaticMeshActor `Ch_Altar_BearingPlate`, folder `Gameplay/Chapel`, covering the altar-top opening:
   - mesh `/Engine/BasicShapes/Cylinder` (100 × 100 × 100, pivot centre); scale (0.94, 0.94, 0.04) → Ø 94 × 4 cm;
   - location (8900, 0, 132) → Z 130…134, so it rests on the altar top (Z 131) and covers the Ø 84 opening with 5 cm overlap; rotation 0;
   - material `MI_LB_Iron`; collision profile `NoCollision` (the interaction trace must still reach the Core); cast shadow on.
   - **Check:**
     - the vertical trace on the wheel top still hits Z 188.5;
     - the eye-height trace from the nave still hits the Core;
     - capture `r2b2_bellwheel_close_pie.png` (the R2-B pose). **LOOK:** no dark pit; the axle rises from an iron plate.
2. **Door backing** in `BP_Door_Base_Dungeon` (child only; never edit `BP_Door_Base`).
   - First read the parent component tree and note the parent of `doorMesh` (the hinge component).
   - Add two StaticMeshComponents to the child, both attached to that same parent (not to `doorMesh`, whose scale is non-uniform and mirrored):
     - **`backing`:** `/Engine/BasicShapes/Cube`, relative location (0, 50, 95), rotation 0, scale (0.02, 0.96, 1.86) → local X −1…1, Y 2…98, Z 2…188.
     - **`backingTop`:** `/Engine/BasicShapes/Cube`, relative location (0, 50, 200), scale (0.02, 0.5, 0.24) → Y 25…75, Z 188…212.
     - Both: material `MI_Prop_Wood_Weathered`, collision `NoCollision`, cast shadow on.
   - **Fit check:** neither piece may show outside the plank silhouette from either side.
     - Capture `Door_Sacristy` from E and W and `Door_ChapelMain` from outside W and inside E (the R2-B poses).
     - If a piece shows beyond the planks (most likely `backingTop` at the pointed head), shrink its Y or Z extent in 5 cm steps until it does not, and record the final values.
   - **LOOK:** no sky or interior visible through the planks.
   - Compile with warnings as errors; before/after dumps of `Door_Sacristy` and `Door_ChapelMain` (only the two new components may differ).
3. **Reload re-dump.** `load_level` `L_Monastery`, then dump the 6 R2-B actors (`Altar_Ritual1`, `Lever_A/B/C`, `Door_Sacristy`, `Door_ChapelMain`) and diff against the R2-B `*_after.json`. The only allowed differences are the 2 door components.
4. **End state:**
   - `bThrottleCPUWhenNotForeground` read back true;
   - map not dirty; no `TMP_` actors;
   - parent BPs `BP_RitualMechanism`, `BP_Door_Base` and `BP_DialLever` not dirty and unchanged in git.
5. Suite 78/78. Commit.

**Then R2-C** (D1.25, unchanged).

### D1.28 R2-A3 review (lead, 2026-10-29)
- **Accepted** (fe11ba4). The skeletal quadrant reads as an open iron lever quadrant: arc band with rim, three pegged notches, struts and hub. The wall and board show through the frame, and the fan/shield silhouette is gone (`r2a3_pie_lever_A_high_sector_side.png`, `r2a3_lever_B_2m_mid_all_levers.png`, `Docs/ArtTest/props/r2a3_cycles_lever_high_3q.png`).
- **Numbers:**
  - Quadrant AABB X −6…47.93, Y −0.3…5.2, Z ±32.12; within 0.1 cm of R2-A2.
  - 1239 tris (R2-A2: 1416).
  - `verify_props` 79/79.
  - Suite 78/78; RouteBot pulls Lever_A, B and C.
- **Deviations accepted:**
  - pegs on the −Y face, beside the arm, because +Y would break the ±1 cm AABB rule;
  - edge struts flush with the band ends;
  - no bevel (tri budget);
  - foot X −6…2, as built in R2-A2.
- **Collision:** 1-hull convex on Quadrant, Arm and Weight, each saved on its own call with no hang. Backplate's convex survived the restart. This closes the D1.27 lost-work item.
- **Lesson for MCP_NOTES (P9-8):**
  - `import_file` refuses an existing path, and `AssetTools.delete` nulls in-memory references.
  - Replace a mesh referenced by a BP like this: point the BP's `SetStaticMesh` pin at a placeholder and compile, delete, import at the same path, point the pin back and compile.
- **Housekeeping:** `BP_DialLever_Crypt` is dirty in memory; its content equals disk after the pin round trip. R2-B2 step 0 saves it on its own call so editor and disk agree.

### D1.29 R2-B2 review (lead, 2026-10-29)
- **Accepted** (a0e5f34).
- **Suite:** 78/78.
- **Reload re-dump against the R2-B `_after.json`:** `Altar_Ritual1` and `Lever_A/B/C` 0 diffs. The two doors differ only by the 2 new components and their 2 actor refs.
- **End state:** parents not dirty; map clean; throttle true. Saves were one package per call, with no hang.
- **Doors** (`r2b2_door_sacristy_E.png`, `r2b2_door_chapelmain_outside_W.png`): the plank gaps now show wood from both sides; the straps and handle are visible again.
  - **Deviation accepted:** the backing sits at relative X −5.4, scale X 0.01, inside the plank layer. At X 0 it covered the straps on the E face.
  - **Deviation accepted:** `backingTop` is Y 15…85, Z 188…201. Larger versions showed a block above the sloped outer planks.
  - **Residual accepted:** thin slivers between the plank tops above Z ≈ 201 (top 10–20 cm of the pointed head). They read as plank-end gaps.
- **Altar** (`r2b2_bellwheel_close_pie.png`): the pit is gone and the axle rises from a plate. In the low chapel light the `MI_LB_Iron` disc reads as a near-black plate.
  - **Owner check:** if it reads as a hole in play, the one-property fix is material → `MI_LB_Bronze` (warm, matching the bells).
- **Lessons for MCP_NOTES (P9-8):**
  - Components added to a child BP need their values set in the construction script; placed instances do not pick up template values.
  - Instance `set_properties` on `relativeLocation`/`relativeScale3D` applies only one axis when the other two match the template, so set one axis per call.
- **Owner playtest:** open both doors and confirm the backing swings with them and does not clip the jamb.
- **Next: R2-C** (D1.25, unchanged; `Note_Chains` is 2×, centre (10920, −1504.15, −430), 56 × 40 cm).

### D1.30 R2-C review; R2 complete (lead, 2026-10-29)
- **Accepted** (d3a7e19).
- **Staircase:** `L_Crypt_Moon_G1/G2` `bCastVolumetricShadow` false, scattering 1.5 → **0.8**; torches T1–T3 scattering 1.0 → 0.5.
  - The stepped slabs in the beams came from the volumetric shadow. The beam is now one smooth cone (`r2c_flooded_passage_oldref.png` vs `r2c_flooded_passage_r2c.png`).
  - **Deviation accepted:** 0.8 instead of 0.5, because 0.5 failed the ±15 % mean test.
  - Means vs a same-session F7 baseline:

    | Pose | Change |
    |---|---|
    | 05 | −6.4 % |
    | 07 | −4.6 % |
    | 08 | −4.2 % |
    | d11 | −5.0 % |
- **Roof gobo:** the 4 cubes are replaced by one `Gobo_Moon_Roof` (`SM_LB_Gobo_RoofHole`) with the same flags and Channel1 only.
  - The lit parallelogram on the roof slab is gone (`r2c_ext_chapel_before.png` vs `_after.png`). A thin rim of about 9 cm stays lit along the hole edge (the 0.7 offset).
  - Roof patch 1.001 vs R1-B; moon leak check 0.403 (< 1.0).
- **G3:** aimed at (10920, −1504, −470), 250 lm, radius 550.
  - **Deviation accepted:** cones 12/26 → **6/16**. At about 15° grazing, a wide cone's brightest region is always the upper wall, whatever the lumens.
  - The note's wall sits at the 73rd percentile of the pool (brightest third), with a pool median of 0.413 at 2 m (target 0.30–0.45).
  - `SA_Crypt_G3` re-oriented. The note reads as clearly lit in a defined moon pool (`r2c_09_puzzle_wall_final.png`).
- **Layout JSON:** all 16 crypt light records were stale and are now synced to the accepted scene values.
  - `place_crypt.py` now reads `volumetric_shadow` from the record instead of hard-coding it.
  - `--check` 16/16, 0.00 cm deviation.
- **Suite:** 78/78. End state clean: map not dirty, no `TMP_` actors, throttle true.
- **Lesson for MCP_NOTES (P9-8):** Static actors ignore `set_actor_transform` in PIE. To A/B a gobo in PIE, toggle `castShadow` on its components instead.

**R2 is complete:** R2-A, R2-A2, R2-A3, R2-B, R2-B2 and R2-C. **Next: P9-8** (D1.18: 8a docs, 8b QA, 8c owner playtest), only on the owner's go.

**Owner playtest checklist (consolidated):**
1. In normal Play (not Simulate), the chapel gobo plates and lancet cubes are invisible: no bright blobs in the sky.
2. From the courtyard, the roof hole shows no lit slab. Judge the thin lit rim.
3. Crypt moon beams are smooth (flooded passage, J4 shaft).
4. `Note_Chains`: lit, readable, pickable. `Note_Gatehouse`: pickable.
5. Bell wheel: look and quarter turn. Altar plate: if it reads as a hole, switch it to `MI_LB_Bronze`.
6. Levers A/B/C: look, and high/mid/low through real interaction.
7. Both doors: they swing with their backing, do not clip the jamb, and hinge on the correct side.
8. GPU at High (`stat gpu`) in the chain chamber and the ossuary (≤ 16.6 ms).
9. Carried over:
   - candle bloom;
   - sacristy table warmth;
   - interior poses 04/05/14 darkness.

### D1.31 Owner sign-off of R2; P9-8 execution spec (lead, 2026-10-29)
- **Owner, 2026-10-29:** "I have reviewed and its fine". This covers the R2 results and the D1.30 playtest checklist, so P9-8c's playtest and judgement items are done. Nothing is outstanding from the owner apart from the final "approve and merge".
- **GPU:**
  - The owner measured 14.72 ms at High in the ossuary (D1.19 addendum).
  - The chain chamber was not reported as a separate number; the owner accepted the playtest.
  - Record R-38 as **Mitigated**, stating exactly that.
- **P9-8a and P9-8b** run as specified in D1.18, with the additions below. They run in parallel: 8a has no editor access, 8b is read-only.

**P9-8a additions (docs; general-purpose; commit "P9-8a: Phase 9 docs").**
1. **`Tools/mcp/MCP_NOTES.md`**, new section `## Crypt and Phase 9 fix sets (P9)`. It holds D1.18 items 1–9; in item 8, note that the plaque was later replaced by a note (D-073) but the texture fact stands. Then add:
   10. **Replacing a mesh referenced by a BP** (D1.28):
       - `StaticMeshTools.import_file` refuses an existing path, and `AssetTools.delete` nulls the in-memory references.
       - Procedure: point the BP's `SetStaticMesh` pin at `/Engine/BasicShapes/Cube` and compile; delete; import at the same path; restore the slot MIs; point the pin back and compile; save one package per call.
   11. **Components added to a child BP** (D1.29):
       - Placed instances don't pick up template values, so the construction script must set mesh, transform, material and collision.
       - Instance `set_properties` on `relativeLocation`/`relativeScale3D` applies only one axis when the others equal the template, so set one axis per call.
   12. **Saving** (D1.27):
       - Save exactly one package per `save_assets` call and check `is_dirty` after each. An editor deadlocked inside a multi-package save (game thread stuck in `InternalPromptForCheckoutAndSave`, CPU idle, the window not responding).
       - If an MCP call hangs for more than about 180 s, stop all editor calls.
       - Recovery: End task (equivalent to Don't Save), then skip the autosave restore.
   13. **Simple collision on imported Blender props** (D1.27): meshes without UCX get no simple collision, so the interaction trace misses them. Add a 1-hull convex (`StaticMeshTools`); never use complex as simple on moving parts.
   14. **Gobos and lighting channels** (D1.23, D1.30):
       - The light is masked by hidden actors (`bHiddenInGame`, `bCastHiddenShadow`, lighting Channel1 only, on spots that use channels 0+1).
       - Simulate ignores `bHiddenInGame`, so gobos show there as bright shapes; judge them in normal Play.
       - Static actors ignore `set_actor_transform` in PIE; to A/B a gobo, toggle `castShadow`.
   15. **Volumetric fog stepping** (D1.30): stepped slabs along spot-light beams come from `bCastVolumetricShadow`, not from the scattering amount. Turn it off on beam lights that pass bars or grates.
2. **`Docs/DECISIONS.md`:** add these rows in the existing table format (columns: ID | Date | Context | Decision | Alternatives | Why | Consequences). Take the facts from the D-sections named.
   - **D-072 Crypt lighting outcome (final)** (D1.16–D1.19, D1.24, D1.30):
     - G1 560 lm, G2 900 lm, cones 8/20, shadowed, `bCastVolumetricShadow` false, scattering 0.8;
     - G3 250 lm, radius 550, cones 6/16, shadowless, scattering 1.5, aimed 40 cm below the note centre;
     - torches 250 lm (T1/T3 radius 350, T2 700), scattering 0.5;
     - candles: niche 90, sarcophagus 67.5, puzzle 40 lm; brazier 200 lm;
     - `PP_Crypt` EV100 0.2, bloom 0.27;
     - `LFV_Crypt_Flood`;
     - accepted deviations (torch poses 02/10, flicker noise 06/09); drips deferred.
   - **D-073 Crypt chain clue is a readable note** (D1.19, D1.25, 2× by the owner):
     - `Note_Chains` (`BP_Inspectable_Note`, 2× = 56 × 40 cm) on the puzzle wall, with its body text;
     - it replaces the plaque and the `CD_PlaqueFrame`;
     - G3 pool on the note.
   - **D-074 Chapel moon gobos** (D1.23, D1.26, D1.30):
     - 12 hidden shadow-only lancet cubes plus one Blender gobo plate `SM_LB_Gobo_RoofHole` (offset 0.7);
     - the 4 outside moon spots on channels 0+1 with scattering 0;
     - replaces the interior rect lights (rejected: flooded the nave);
     - residual: a thin lit rim of about 9 cm at the roof hole.
   - **D-075 Candle-order clue as stained-glass saints** (D1.20, D1.22): `BP_StainedGlassClue_Saints`, `MI_Glass_Clue_Saints`, `T_LB_StainedGlass_Clue`; it replaces the wall pattern (owner: "not fitting").
   - **D-076 Owner review 2 replacements** (D1.25–D1.29):
     - Mechanism 1 is a bell wheel (`BP_RitualMechanism_ChapelBells`, `SM_LB_Prop_BellWheel_A`, `Ch_Altar_BearingPlate`), and the 5 `Mech_Shell_*` actors were removed;
     - crypt levers are `BP_DialLever_Crypt` with the oak board, pulley chain, skeletal quadrant, arm and counterweight meshes;
     - both doors are `BP_Door_Base_Dungeon` (`SM_Dungeon_door`, mirrored in Y, plank backing);
     - alternatives: keeping the P8 shells, or the greybox levers;
     - consequence: three more child BPs duplicate their parents' construction (R-40).
   - Add index lines if the file has an index, matching its format.
3. **`Docs/RISKS.md`:**
   - **R-36:** Closed (P9-5 gap pass).
   - **R-37:** Closed (P9-6b and R2-B dumps/diffs, suite 78/78, RouteBot).
   - **R-38:** Mitigated (ossuary 14.72 ms at High; owner playtest accepted 2026-10-29; chain chamber not measured separately; fallbacks unchanged).
   - **New rows:**

     | ID | Area | Risk | L | I | Mitigation | Status |
     |---|---|---|---|---|---|---|
     | R-39 | Tooling | Capture tooling reliability | M | L | `--raise`, the breaker, ≤ 6 tries, owner checklist for missing poses | Open |
     | R-40 | Architecture | Child BPs duplicate parent construction scripts: CryptWinch, CryptCrank, StainedGlassClue_Saints, ChapelBells, DialLever_Crypt, Door_Base_Dungeon | M | M | Update the children whenever a parent construction script changes; listed in MCP_NOTES | Open |
     | R-41 | Tooling | The editor can deadlock inside a multi-package save | L | M | One package per save; the 180 s stop rule; End-task recovery | Mitigated |
4. **`Docs/PERFORMANCE_BUDGET.md`:**
   - Phase 9 crypt row as in D1.18 item 2, with the final light values from D-072.
   - GPU: "ossuary 14.72 ms at High (owner, 2026-10-28); chain chamber not separately measured; owner playtest accepted 2026-10-29".
5. **`Docs/ASSET_REGISTRY.md`:**
   - As D1.18 item 3. Also check rows for `SM_Dungeon_door` / `MI_Dungeon_door` (Fab Dungeon pack) and the Poly Haven/ambientCG sources used by `MI_Crypt_*` and `MI_Aged_*`.
   - If the file has a section for project-made (Blender procedural) assets, add the R2 meshes: `SM_LB_Prop_BellWheel_A`, `SM_LB_Prop_DialLever_{Backplate,Quadrant,Arm,Weight,NotchStop}`, `SM_LB_Gobo_RoofHole`. If not, list them only in the report.
   - Never invent a licence.
6. **`Docs/IMPLEMENTATION_PLAN.md`:** set the Phase 9 status line to: P9-0…P9-7, R1 and R2 done (key commits); P9-8 docs and QA done; awaiting owner "approve and merge".
7. **`Docs/TECHNICAL_DESIGN.md`:** check whether it names the puzzle/door Blueprints placed in `L_Monastery`. If it lists placed classes, add the six child BPs (R-40); otherwise make no change, and say so in the report.

**P9-8b additions (QA; qa-reviewer; report only, no fixes, no editor mutations, no saves, no commits).**
1. D1.18 items 1–5.
2. **Lane re-check:** also report the clearance at the levers (the quadrant protrudes up to 48 cm from the wall at the high/low positions), and at both doors with the backing (closed and fully open, if the script supports doors; otherwise say it doesn't).
3. **Dress check investigation:** `python Tools/crypt/place_crypt.py --cats dress --check` reported 118 failures earlier. Run it read-only (confirm `--check` makes no edits by reading the code first).
   - Classify the failures by cause: stale JSON vs a real displacement; which fields fail (mesh, transform, bounds, materials, collision); which categories or prefixes.
   - Give 3 concrete examples with values.
   - Recommend a fix (regenerate the JSON from the scene, or fix the actors). Do not apply it.
4. **Light check:** `python Tools/crypt/place_crypt.py --cats light --check` must report 16/16.
5. **Doc consistency:** grep `Docs/` for stale statements that contradict the final state, and list the file:line of each. Examples:
   - "plaque" described as the current crypt clue;
   - "Mech_Shell" described as current;
   - G1/G2 `bCastVolumetricShadow` true.
   Do not edit.

### D1.32 P9-8 close; Phase 9 ready for review (lead, 2026-10-29)
- **P9-8a docs: accepted** (196a06e).
  - MCP_NOTES: P9 section, items 1–15.
  - DECISIONS: D-072 to D-076.
  - RISKS: R-36 and R-37 closed; R-38 mitigated; R-39, R-40 and R-41 added. The lead corrected the R-38 text: 2 shadowed moon spots, G3 shadowless.
  - PERFORMANCE_BUDGET: Phase 9 row.
  - ASSET_REGISTRY: 17 usage cells now read "used in crypt (P9)", including `SM_Dungeon_door`.
  - IMPLEMENTATION_PLAN: status line updated.
  - TECHNICAL_DESIGN: no change needed (it lists only base classes).
- **P9-8b QA: skipped by the owner** (2026-10-29: "final qa pass is not needed, wrap phase 9"). The last suite run was 78/78 after R2-C (d3a7e19), with the light `--check` at 16/16.
- **Known documentation gaps (not blocking):**
  - Earlier project-made procedural props used in the crypt (e.g. `SM_LB_Prop_Rafter_Broken_15x10x260`, `SM_LB_Prop_RoofPlanks_Broken_200x100x4`) have no registry rows.
  - The external sources behind `MI_Prop_*`, the parents of the crypt MIs, are not traced in the registry.
  - The P9-4 water edge-fade outcome is not recorded (MCP_NOTES item 4 describes the intended behaviour).
- **Open item carried to a later phase:** the dress `--check` reports 118 failures. Not investigated, since the owner skipped QA.
- **Housekeeping:** delete the untracked `Content/LastBell/Maps/L_Throwaway_P9_4.umap` once Unreal is closed. It is never committed.
- **Phase 9 is ready for the owner's review.** Merge only on "approve and merge".
