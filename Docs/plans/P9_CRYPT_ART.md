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
