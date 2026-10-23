# THE LAST BELL — Modular Kit Specification (P7-001)

Spec only. Authoring (Blender, `Tools/blender/kit/`), import and level use are P7-002 and P7-003. Decision reference: D-044 (custom Blender modular kit), D-038 (door and Warden sizes), D-045/D-046 (material and sky notes). The greybox (`L_Monastery`) was **read, not modified**.

## 1. Style brief
Romanesque-to-early-Gothic mountain monastery, built and ruined over centuries: thick rough ashlar walls with deep reveals, pointed arches (equilateral or slightly lancet), chamfered edges, weathered coping and a projecting base course. Grounded and weathered, never fantasy: no ornament beyond stepped mouldings, quoins and a plain hood over openings. Silhouettes are broken and uneven; the surfaces get their age from the shared CC0 scanned materials plus the master-material wetness and grime layers.

## 2. Survey of the greybox (L_Monastery; cm; +X away from spawn; courtyard ground Z=0)
Source: a read-only dump of every actor's transform and bounds from `/Game/LastBell/Maps/L_Monastery` (loaded headless, nothing saved; `git status` unchanged by the survey). All greybox elements are axis-aligned engine cubes unless noted, with the Z=0 baseline.

### 2.1 Approach (X -3000..0)
| Element | Actor(s) | Surveyed size |
|---|---|---|
| Path | corridor between the cliffs | **400 wide** (Y ±200), 3000 long (X -3000..0), flat at Z=0 |
| Cliff walls | `Cliff_S` / `Cliff_N` | X -3000..0 (3000 long) × **60 thick** (Y ±200..±260) × **600 tall** |
| Boulders | `Boulder_0..2` | cube blocks 300 / 260 / 340 at X -2200, -1200, -500 (Y +330, -340, +300). They overlap the cliff bases and intrude into the path by about 20 / 27 / **140** (`Boulder_2` narrows the path to about 260 at X -740..-260) |
| Spawn / checkpoint | `PlayerStart` (-2800,0,100); `CP_Approach` (-2700,0,92) | unchanged by the art pass |
| Lights | `Light_Approach_0..2` at X -2400, -1500, -600, Y0, Z350 | greybox lights only |
| Ground | `Ground_0` (shared slab) | X -3000..7400, Y ±3600, Z -40..0 (40 thick) |
| Outer perimeter | `Perim_W/E/S/N` | 40 thick, 800 tall, at X -3040..-3000 and Y ±3600..±3640 (and X 13400, beyond the area) |

### 2.2 Gatehouse (X 0..300)
| Element | Actor(s) | Surveyed size |
|---|---|---|
| Gate walls | `GateWall_S` / `GateWall_N` | X 0..300 (**300 thick**) × Y ±200..±2540 × **800 tall** (a solid 300-thick curtain across the whole west side) |
| Gate lintel | `GateLintel` | X 0..300, Y ±200, **Z 300..600**: the opening is **400 wide × 300 clear**, with an open notch from Z 600 to 800 above the lintel |
| Trigger / note | `Trig_CourtyardEntered` (X100..200, Y ±200, Z0..300); `Crate_Note_Gatehouse` (X205..255, Y -170..-120, 45 tall) | inside the passage; effective free width past the crate is about 320 |
| Checkpoint | `CP_Courtyard` (350,0,92) | unchanged |

### 2.3 Courtyard enclosure
| Element | Actor(s) | Surveyed size |
|---|---|---|
| North / south walls | `Wall_N` / `Wall_S` | X 300..6040 (5740 long) × **40 thick** (Y 2500..2540 / -2540..-2500) × **800 tall** |
| East wall | `Wall_E_S` (Y -2540..-790), `Wall_E_Mid` (790..1948), `Wall_E_N` (2052..2540) | X 6000..6040 (**40 thick**) × **800 tall**; gaps at Y ±790 (the chapel front) and at Y 1948..2052 (shortcut gate) |
| Shortcut gate opening | `Wall_E_GateLintel` + `Door_Shortcut` (leaf Y 1950..2050, 220 tall, 10 deep) | opening **104 wide × 230 clear** (lintel Z 230..800) |
| Passage behind the shortcut gate | `Passage_S` / `Passage_N` | X 6040..9460, walls 40 thick × 800 tall at Y 1660..1700 and 2300..2340: a **600-wide** corridor to the cloister (outside the Phase 7 scope) |
| Chapel west front (exterior face) | `Chapel_W_S` / `Chapel_W_N` / `Chapel_W_Lintel`; `Door_ChapelMain` (leaf Y -50..50, 220 tall) | X 6000..6040, **40 thick × 1200 tall**, Y ±790 (**1580 wide**); opening **104 wide × 224 clear**, centred on Y=0; chapel nave wall tops are also 1200 and run on to X 9000 |
| Silhouette | `Silh_CourtyardWall` (6020, 2300, **Z 800**) | stands on top of the east wall (wall top must stay at Z=800) |
| Courtyard clear size | | X 300..6000 (5700) × Y ±2500 (5000), flat |

### 2.4 Courtyard interior
| Element | Actor(s) | Surveyed size |
|---|---|---|
| Well house | `Well_W/E/S/N1/N2`, `Plinth_Key`, `Key_Chapel`, `Light_Courtyard_6` | footprint **400 × 400** (X 1300..1700, Y -2200..-1800), walls **30 thick**, heights W 250, E 200, S 250, N1 250, N2 150 (ragged, **no roof**); **entrance 120 wide** (X 1440..1560) on the north side; key plinth 50×50×70 at (1500,-2050); key at Z 70..90 |
| Collapsed wall | `Ruin_Wall` + `Rubble_0..4` | wall X 800..860 (60 thick) × Y -1500..-700 (**800 long**) × **400 tall**; rubble blocks 1.0–1.6 m wide and 0.7–1.1 m high at (760,-1650), (900,-1580), (1000,-1480), (640,-1550) at the south end and (700,-720) at the north end. The straight line from the gate (150,0) to the key (1500,-2050) crosses the wall at X≈830, Y≈-1030, so it is blocked; the south route stays 760+ wide (Y -1736..-2500) |
| Colonnade posts | `Col_N0..3`, `Col_S0..3` | **100 × 100 × 500**, at X 2000/3000/4000/5000, Y ±950 (centre-to-centre aisle 1800 clear) |
| Fountain | `Fountain` (X 2800..3200, Y ±200, **60 tall**) + `FountainPost` (100×100, Z 60..350) | centrepiece at (3000,0) |
| Lights | `Light_Courtyard_0..7` | greybox, Z 300..500 |

### 2.5 Seen from the courtyard
| Element | Surveyed |
|---|---|
| Bell tower (greybox shell `Tw_*`) | X 12000..13000, Y 1500..2500, **3500 tall**, walls 40 thick, roof slab at Z 3500; the door is a 104 × 224 opening at Y 2000 |
| Chapel nave walls | 1200 tall, X 6040..9000, Y ±750..790 (roofless in the greybox) |

### 2.6 Opening sizes the Warden must pass (D-038: capsule radius 42, nav agent 42/220, height reads 290 but stoops)
| Opening | Surveyed clear size |
|---|---|
| Courtyard gate | 400 × 300 |
| Chapel main door | 104 × 224 |
| Shortcut gate | 104 × 230 |
| Sacristy door / tower door (outside P7) | 104 × 224 |
| Well-house entrance | 120 wide, open top |
| Ramps / stairs in the Approach and Courtyard | **none**: everything is flat at Z=0 |

### 2.7 Sightlines (computed from greybox geometry, not traced in-engine)
- From the spawn (eye about 170) the gate wall top (Z 800 at X 0) sits at 12.7° and the tower top (Z 3500 at X 12000) at 12.7°: the tower is **marginally** visible in the greybox, and from the path it appears mainly **through the gate opening** once the player is within a few metres of the gate. A taller or heavier gate crown (kit coping, merlons, a pointed arch whose narrow apex clips the view) can hide it. The arch spec below keeps clear width and height at least as large as the greybox; verify with a trace in P7-003.
- From `CP_Courtyard` (X 350) the courtyard east wall top is at about 6.3° and the tower top at 15.9°, so the upper **20 m of the tower** shows over the east wall.

## 3. Grid and conventions
- **Units cm, 50 cm grid.** Piece envelope sizes are multiples of 50 (a few trims use 10 cm overhangs). The surveyed greybox sizes that are not on the grid (104, 224, 230, 40, 30, 790, 1580...) are reconciled in section 6.
- **Axes.** +X = length, +Y = thickness (or depth), +Z = up. Name size = `X×Y×Z` in cm.
- **Pivot: bottom-left-back corner**, i.e. the minimum X, Y, Z corner of the piece's bounding box, on the grid (a piece's origin is its corner, so placing is just "corner + yaw"). Variants of one piece share the same envelope and pivot.
- **Yaw 90 rule (walls running along world Y):** local +X maps to world +Y and local +Y maps to world **-X**. So the instance location is the min-Y end at the **max-X face** of the wall, e.g. the east wall (X 6000..6060) uses location X=6060.
- **Naming:** `SM_LB_Kit_<Piece>_<X>x<Y>x<Z>[_<Variant>]`, e.g. `SM_LB_Kit_Wall_400x60x800_A`. Folder `/Game/LastBell/Environments/Kit/` (meshes), `/Game/LastBell/Environments/Kit/Materials/` (MIs).
- **Faces:** both long faces are dressed unless stated. Mirroring an instance (scale -1 on Y or yaw 180) must give an acceptable result: world-aligned UVs make that safe, so `_A` plus its mirror counts as two looks.
- **Material slots**
  - **Slot 0** main masonry face. World-aligned MI of `M_LB_Surface` (candidates: `MI_Medieval_Blocks_03_WA`, `MI_Castle_Wall_Variation_WA`). Floor slab: flagstone (`MI_Cobblestone_Floor_08_WA` family); cliff slab: `MI_Rock_064_WA`.
  - **Slot 1** dressed stone trim: arch voussoirs and hoods, quoins, cap course, plinth, piers. UV0 (see below), a separate MI (cleaner, lighter ashlar).
  - **Slot 2** rubble / mortar / rough core: fractured tops, broken edges, exposed core of broken pieces. A coarse, darker MI.
- **UV0:** non-overlapping, planar-projected at a fixed world scale (1 UV unit = 100 cm), no mirroring; used for trim (slot 1) and as the fallback for slots 0 and 2. Large faces (slot 0) read through the world-aligned MIs, so wall segments tile without visible UV seams.
- **Vertex colour (proposal; the technical-artist confirms against `M_LB_Surface` inputs):** R = wetness / puddle bias (floor and low plinths painted, walls 0), G = moss/grime bias, B = baked edge/crevice wear, A unused. Every piece ships with at least a default paint (floor slab: R by height).
- **Edges:** every convex edge of slot 1 (trim, quoins, arch reveals, piers) has a **2–3 cm chamfer or bevel** (5 cm on cap/coping and plinth tops) so the moon and lightning catch it. Slot 0 faces carry modelled macro relief only (course steps and chips of ±1–3 cm); fine detail comes from the normal map.
- **Pointed arch rule:** equilateral or slightly lancet; the springline is at the clear height listed per piece, the clear rectangle below the springline is never obstructed.
- **Nanite and LOD:** Nanite on for every piece, no hand LODs. Triangle budgets (ceiling per piece): wall segment 2.5k; broken wall 4k; doorway 6k; gate arch 12k; pier 1.5k; floor slab 3.2k (25 cm vertex grid for vertex paint and ±1.5 cm relief); rubble 2k; heap 6k; cliff slab 8k; well wall 2k.
- **Collision:** custom simple collision (`UCX_` boxes) exported with the FBX; collision trace response `Block`; Complexity "Use Simple as Complex" is **off**. Straight pieces: one box per segment (stepped boxes following the broken profile for broken pieces). Opening pieces: several boxes leaving the clear opening completely free (see the table). The floor slab collides as a single box (top flat at Z=40 in the piece = Z 0 when placed at Z=-40). Collision stays walkable-flat for the Warden navmesh; rubble blocks (no walkable slope).
- **Gameplay safety:** no kit piece has its own blueprint behaviour; doors stay `BP_Door_Base` leaves placed in the opening; nothing in the kit overlaps a trigger or checkpoint volume.

## 4. Piece table
Sizes are `X×Y×Z` cm. "Clear" is the unobstructed opening at ground level. P0 = needed for the Approach and Courtyard (P7-003); P1 = needed later (Chapel, Cloister, Crypt, Tower) or an optional upgrade. **P0 count: 25** (`Wall_400x60x800_B` is droppable: 24). **P1 count: 14.**

### 4.1 P0 (Approach and Courtyard)
| # | Mesh (`SM_LB_Kit_...`) | Size | Opening / notes | Replaces (greybox) | Pri |
|---|---|---|---|---|---|
| 1 | `Wall_400x60x800_A` | 400×60×800 | Straight ashlar wall; integrated chamfered cap course (slot 1) and no coping needed, so the wall top is exactly Z=800; coursing aligned to 50 cm | `Wall_N/S`, `Wall_E_*`, west curtain, chapel front lower storey | P0 |
| 2 | `Wall_400x60x800_B` | 400×60×800 | Same envelope, different coursing and chips (anti-repetition, R-26); droppable | same | P0 |
| 3 | `Wall_100x60x800` | 100×60×800 | Filler to hit 100 cm multiples | same | P0 |
| 4 | `Wall_400x60x400` | 400×60×400 | Upper course or half-height wall (capped top) | chapel front upper storey (Z 800..1200), `Ruin_Wall` (400), over doorway modules | P0 |
| 5 | `Wall_100x60x400` | 100×60×400 | Filler for the upper course | chapel front uppers | P0 |
| 6 | `Wall_400x60x800_Broken` | 400×60×800 | Broken top from about Z 450 to 800 (stepped profile, slot 2 on the fracture), ragged ends; 3 stepped collision boxes | spots on `Wall_N/S` (silhouette breakers), `Ruin_Wall` backdrop | P0 |
| 7 | `Wall_400x60x400_Broken` | 400×60×400 | Broken top from about Z 150 to 400, ragged ends | `Ruin_Wall` (2 of them in a row, one mirrored) | P0 |
| 8 | `Wall_Corner_60x60x800` | 60×60×800 | Corner post with quoins (slot 1) and the same cap | the 4 enclosure corners | P0 |
| 9 | `Buttress_100x150x800` | 100×150×800 | Two set-offs, sloped weathering at Z 500 and 800 | chapel front shoulders, gate shoulders, optional inner face of `Wall_N/S` every 1200 | P0 |
| 10 | `Doorway_Pointed_400x60x400` | 400×60×400 | **Clear 120 × 240** (springline Z 240, apex Z about 340), centred (jambs 140 each side); hood and voussoirs slot 1; 3 collision boxes: jambs X 0..140 and 260..400 (Z 0..400) and a header X 140..260 × Z 240..400 | the chapel and shortcut door openings; later the sacristy and tower doors | P0 |
| 11 | `Gate_Arch_1200x300x800` | 1200×300×800 | **Clear 400 wide × 300 to the springline**, equilateral pointed arch, apex about Z 646; barrel-vaulted soffit (slot 1 voussoirs, slot 2 rough soffit); 3 collision boxes: X 0..400, X 800..1200 (full height) and a header X 400..800 × Z 300..800 (keeps the clear 400×300 rectangle) | `GateWall_S/N` (inner 1200), `GateLintel` | P0 |
| 12 | `Trim_Plinth_400x80x60` | 400×80×60 | Base course: 10 cm projection each side of a 60 wall, 5 cm chamfered top; collides as a box | foot of all P0 walls (new dressing) | P0 |
| 13 | `Trim_Plinth_100x80x60` | 100×80×60 | Filler | same | P0 |
| 14 | `Pier_100x100x500` | 100×100×500 | Square pier with base, chamfered shaft, simple capital (slot 1); collides as one box | `Col_N0..3`, `Col_S0..3` | P0 |
| 15 | `Pier_Broken_100x100x350` | 100×100×350 | Broken top at about 350 (slot 2), ragged | `FountainPost` (Z 60..350 on the basin), two or three of the `Col_*` for ruin | P0 |
| 16 | `Floor_Slab_1000x1000x40` | 1000×1000×40 | Flagstone slab with a 25 cm vertex grid (R = puddle bias painted low in dips); top flat to ±1.5 cm; place at Z=-40 so the top is Z=0; slot 0 is flagstone | `Ground_0` in the playable area | P0 |
| 17 | `Rubble_Chunk_S` | about 60×50×40 | Dressed stone block, broken corners | scatter around `Ruin_Wall`, well | P0 |
| 18 | `Rubble_Chunk_M` | about 120×100×70 | Rough stone chunk | `Rubble_0..4` | P0 |
| 19 | `Rubble_Chunk_L` | about 170×150×110 | Large fallen block, one flat top | `Rubble_0..4`; also the `Plinth_Key` slab (use a flat-topped chunk) | P0 |
| 20 | `Rubble_Heap_400x300x130` | 400×300×130 | Collapsed-wall heap, 6k tris, 2 boxes of collision (blocking, no walkable slope) | `Ruin_Wall` ends (south route partial blockers) | P0 |
| 21 | `Cliff_Slab_500x300x600_A` | 500×300×600 | Faceted rock face on -Y (the player side), flat back, ragged top; slots 0 (rock, world-aligned) and 2 (fracture); 2 hull boxes | `Cliff_S` / `Cliff_N` (6 modules per side, X -3000..0) | P0 |
| 22 | `Cliff_Slab_500x300x600_B` | 500×300×600 | Alternate face and top profile, same envelope | same | P0 |
| 23 | `Well_Wall_450x50x250` | 450×50×250 | Ragged-top low wall (ruin) | `Well_W`, `Well_E` | P0 |
| 24 | `Well_Wall_350x50x250` | 350×50×250 | Ragged-top low wall | `Well_S` | P0 |
| 25 | `Well_Wall_100x50x250` | 100×50×250 | Ragged-top low wall; two flank the 150 entrance | `Well_N1`, `Well_N2` | P0 |

### 4.2 P1 (later areas or optional upgrades)
| # | Mesh | Size | Notes | Use |
|---|---|---|---|---|
| 26 | `Wall_400x60x200` | 400×60×200 | Half course, filler for non-800 heights (the tower is 3500, interior walls 400) | tower, interiors |
| 27 | `Wall_EndCap_100x60x800` | 100×60×800 | Finished (quoined) wall end, visible at openings | cloister, chapel |
| 28 | `Wall_CornerInner_100x100x800` | 100×100×800 | Inside corner L | cloister, chapel |
| 29 | `Trim_Coping_400x80x40` (+ `_100`) | 400×80×40 | Weathered coping with a drip edge for low or broken walls | low walls, well |
| 30 | `Window_Lancet_200x60x400` (open and blind) | 200×60×400 | Narrow pointed lancet in a dressed frame; the blind variant is a recess with no hole | chapel west front (flat facade), nave, tower |
| 31 | `Arch_Span_Pointed_400x60x400` | 400×60×400 | Pointed arch on two 100-wide piers' height, for the cloister arcade and crypt | cloister, crypt |
| 32 | `Column_Round_60x60x400` | 60×60×400 | Round Romanesque column with base and capital | cloister, crypt |
| 33 | `Vault_Rib_Span_400x400x150` | 400×400×150 | Groin vault bay with ribs | crypt, nave |
| 34 | `Stair_Run_400x150x100` | 400×150×100 | 5 steps, rise 20, tread 30 (about 34°), full step collision | chapel steps, tower landings |
| 35 | `Flag_Path_400x200x15` | 400×200×15 | Raised worn paving strip over the floor slabs | gate to chapel path |
| 36 | `Well_Curb_Round_150x150x80` + `Well_Roof_Frame_450x450x150` | | Low round curb and a small timber frame | well house upgrade (greybox has neither) |
| 37 | `Block_Dressed_50x50x70` | 50×50×70 | Key plinth block | `Plinth_Key` (a flat-topped `Rubble_Chunk_L` stands in) |
| 38 | `Fountain_Basin_400x400x60` | 400×400×60 | Hero: low octagonal basin, ruined | `Fountain` (the post is `Pier_Broken`) |
| 39 | `Tower_Shell_*` (belfry louvre, corbel, ruined roof) | custom | Phase 10; for the courtyard view see the open question on the tower proxy | bell tower |

## 5. Courtyard rebuild map
Coordinates cm. "Run" lists the instances in X or Y order; **all yaws and origins follow section 3**.

```
 Y+2560  NW post ┌───────────── North wall: 14×Wall_400 + Wall_100 (X 300..6000) ─────────┐ NE post
                 │                                                                         │
 west curtain    │  Col N0-3 (X2000-5000, Y+950)                                           │ E wall north
 (60 thick,      │                                                                         │ 800..2500, shortcut
  X 240..300,    │                       Fountain (3000,0)                                  │ door module Y 1800..2200
  7 pcs/side)    │                                                                         │ 
 gate block ───► │   gate (X0..300, Y±600)    Ruin_Wall                                    │ CHAPEL FRONT (1200 tall)
 Y -600..600     │   (clear 400×300)          X 800..860                                    │ Y -800..800, door Y±60
                 │                            Y -1500..-700      Well house                 │ 
 Y-2560  SW post └──────── South wall: 14×Wall_400 + Wall_100 ──────────────────┘ SE post
   X: 0 ........ 300 ............ 1500 ........................ 6000/6060
   Approach: cliffs Y ±200..±500 (inner face ±200), X -3000..0, with Cliff_Slab A/B ×6 per side
```

| Greybox | Kit replacement | Instances / transforms | Gameplay constraint |
|---|---|---|---|
| `Cliff_S/N` (6 m, X -3000..0) | `Cliff_Slab_500x300x600_A/_B` alternating, mirrored on the north side | 6 per side; slab X cells -3000, -2500, ... -500; the faceted face (local -Y) must face the path: north cliff origin (x0, 200, 0) yaw 0; south cliff origin (x0+500, -200, 0) yaw 180; inner face Y=±200; top Z 600 | the corridor stays **400 wide**; the cliff back sits inside the old unreachable ground band |
| `Boulder_0..2` | library rocks (`Rock_Moss_Set_01` etc.) or `Rubble_Chunk_L` plus the heap | 3, same positions | keep at least 200 free path width (the greybox `Boulder_2` leaves about 260); pure dressing |
| `Ground_0` (playable zone) | `Floor_Slab_1000x1000x40` | Z=-40; Approach: X -3000..0 × Y -500..500 (3 slabs, beyond the cliff bases); Courtyard: X 0..6000 × Y -3000..3000 (6 × 6 = 36, the outer ring is hidden behind the walls); the greybox slab stays as an underlay | top Z=0 so navmesh, key height and doors do not shift |
| `GateWall_S/N` + `GateLintel` | `Gate_Arch_1200x300x800` + west curtain of `Wall_*x60x800` | gate: yaw 90, origin (300, -600, 0); curtain (yaw 90, origin X=300, Y 600..2500 and -2500..-600): 4×Wall_400 + 3×Wall_100 per side; buttresses at the gate shoulders on the courtyard side | opening **≥ 400×300** (kit 400×300 clear, higher arch), `Trig_CourtyardEntered` (X100..200) and `Crate_Note_Gatehouse` unchanged; the new gate is 1200 wide vs the old 5080 wide solid wall: only the unreachable rear changes |
| `Wall_N` / `Wall_S` | `Wall_400x60x800_A/_B` ×14 + `Wall_100x60x800`, with 2–3 `Wall_400x60x800_Broken` mixed in; plinth along the foot; optional buttress every 1200 | north: yaw 0, origin (300+400k, 2500, 0); south: origin (300+400k, -2560, 0); inner face Y=±2500 kept, thickness 60 grows outward | nav width unaffected; keep the north wall top at 800 (the silhouette stands on the east wall) |
| corners | `Wall_Corner_60x60x800` | NW (240,2500), NE (6000,2500), SE (6000,-2560), SW (240,-2560) | |
| `Wall_E_S`, `Wall_E_Mid`, `Wall_E_N` | east wall: yaw 90, location X=6060: south Y -2500..-800 = 4×Wall_400 + Wall_100 (origin Y -2500, -2100, -1700, -1300, -900); north Y 800..1800 = 2×400 + 2×100, door module Y 1800..2200 (+ `Wall_400x60x400` above at Z 400), Y 2200..2500 = 3×Wall_100 | | the shortcut opening stays centred at Y=2000; `Door_Shortcut` leaf and `Silh_CourtyardWall` (Z 800) stay |
| `Wall_E_GateLintel` | `Doorway_Pointed_400x60x400` at Y 1800..2200 | clear 120×240 (was 104×230) | see open question 2 |
| Chapel west front (`Chapel_W_*`) | `Doorway_Pointed_400x60x400` at Y -200..200 (+ `Wall_400x60x800_A` at Z 400..1200 above it), then per side Y 200..800 (mirror): lower storey Z 0..800 = Wall_400 + 2×Wall_100, upper storey Z 800..1200 = `Wall_400x60x400` + 2×`Wall_100x60x400` | yaw 90, X=6060 | door centred on Y=0, **door 120×240 clear**; buttresses at Y ±800 on the courtyard side; the front is 20 cm wider than the greybox (Y ±800 vs ±790): the extra hides in the chapel side walls |
| `Passage_S/N`, nave, cloister | **unchanged** (greybox) | | out of scope |
| `Ruin_Wall` (800 long, 400 tall) + `Rubble_0..4` | 2×`Wall_400x60x400_Broken` (one mirrored) at X 800..860, Y -1500..-700, rubble chunks S/M/L in the same 5 places, 2 heaps at the south end | wall origin (800,-1500,0) and (800,-1100,0), yaw 90, location X=860 | **must still block the straight gate-to-key line** and leave the south route (Y -1736..-2500) and the north route open; keep the wall 400 tall and unbroken in the middle; `Rubble_Heap` blocks only, no new walkable ramps |
| Well house (`Well_*`, `Plinth_Key`, `Key_Chapel`, `Light_Courtyard_6`) | `Well_Wall_450x50x250` (W, E), `Well_Wall_350x50x250` (S), 2×`Well_Wall_100x50x250` (N, 150 entrance in the middle), key slab from `Rubble_Chunk_L` | footprint X 1275..1725, Y -2225..-1775 (grows from 400 to 450); entrance centred on X=1500 | **key location unchanged** (1500,-2050) and the `Key_Chapel` trigger/interaction; entrance 150 (was 120); no roof in P0 |
| `Col_N0..3`, `Col_S0..3` | `Pier_100x100x500` (6) + `Pier_Broken_100x100x350` (2) | same footprints (corner at X-50, Y-50 from the old centres) | Y ±950 gap (1800) unchanged |
| `Fountain` + `FountainPost` | greybox basin stays for P0, `Pier_Broken_100x100x350` as the post | | P1 hero basin |
| Perimeter / tower | untouched | | the greybox tower stays (see open question 6) |

**Checkpoints, triggers and Warden markers keep their positions, tags and labels:** `CP_Approach`, `CP_Courtyard`, `Trig_CourtyardEntered`, `Door_ChapelMain`, `Door_Shortcut`, `Key_Chapel`, `Silh_CourtyardWall`, `Note_Gatehouse`, `PlayerStart`, the navmesh bounds. After P7-003 re-run the navmesh build and the RouteBot/WalkPath tests.

## 6. Reconciling the surveyed sizes with the grid
| Surveyed | Kit | Effect |
|---|---|---|
| Walls 40 thick (courtyard, chapel front); 60 in the plan | **60** thick; the inner (courtyard) face stays on the greybox line | N/S walls grow outward 20; east wall grows toward the chapel interior 20 (X 6040..6060), the `Chapel_N/S` walls and nave interior are unaffected apart from the front |
| Chapel front Y ±790 (1580) | Y ±800 (1600) | +10 per side, hidden in the nave walls |
| Door openings 104 × 224/230 | **120 × 240** (task rule, ≥120×240) | the `BP_Door_Base` leaf (100 × 220) must be re-scaled to about 118 × 238 in P7-003, or a frame insert added |
| Gate opening 400 × 300 (rectangular) | 400 × 300 to the springline, apex about 646 | strictly larger; frames the tower |
| Gate wall 300 thick, 5080 wide | 1200-wide gate block, curtain 60 thick | the areas behind it were unreachable |
| Well house 400 × 400, 30 thick, entrance 120 | 450 × 450, 50 thick, entrance 150 | grid; key and light positions unchanged |
| Courtyard ground Z -40..0 | slabs 1000 × 1000, placed at Z=-40 | |

## 7. Risks and open questions for the lead
1. **Wall thickness 60 vs the greybox 40.** Confirm that growing the east wall by 20 cm into the chapel interior side (inner face kept) is acceptable, or accept 40 for the courtyard and use 60 only for the gate.
2. **Door leaf and frame size.** The kit opening is 120 × 240 while the leaves (`Door_ChapelMain`, `Door_Shortcut`) are 100 × 220 in 104 × 224/230 openings. Rescale the leaves in P7-003 (no gameplay change) or keep 104 × 230 by narrowing the piece (the lead decides; D-038 only requires ≥ 84 for the nav agent).
3. **Tower sightline from the spawn** (section 2.7) is marginal; the kit arch is taller than the greybox lintel, but the gate shoulders and cap may still hide the tower. Trace before and after P7-003; a lower gate crown or a notch is the fix.
4. **Cliffs and boulders.** No CC0 cliff mesh was verified (ASSET_PLAN), so cliff modules are custom kit pieces (2 variants × mirror). A rock-mesh pass (Poly Haven `rock_moss_set`, `boulder_01`) can replace them for boulders only. Approve or move cliffs out of the kit.
5. **Floor slab count and ground outside the walls.** About 36 courtyard + 3 approach Nanite slabs; keep `Ground_0` as the underlay and the hidden outer ring (Y beyond ±2560, 1000 wide, unreachable) un-slabbed. Puddles and the wet look are the master-material job, not a mesh.
6. **Tower proxy.** The greybox tower stays for P7. If the lead wants a dressed silhouette from the courtyard (belfry openings, ruined crown), a single proxy `Tower_Proxy_1000x1000x3500` is needed (P1 item 39). Decision needed before P7-004.
7. **Chapel front reads flat** (a 16 m × 12 m wall with one door). A blind lancet pair or rose recess (P1 item 30, blind variant) would help; they could be promoted to P0. Doing this is purely visual and does not change gameplay.
8. **Repetition (R-26).** The wall family has only one plain variant pair (A/B) plus broken ones; expect to need vertex-paint breakup and decals (Phase 11). If the lead wants more, add `_C`.
9. **Vertex-colour channel contract** (section 3) is a proposal; the technical-artist must confirm `M_LB_Surface` reads R/G/B as wet / grime / wear (or change the table).
10. **Pivot/yaw tooling.** The "bottom-left-back, yaw 90 shifts the origin to the max-X face" rule makes placement errors easy; P7-003 should place by script from the run table above and verify with a bounds check.
11. **Collision and Nanite.** Verify in P7-002 that the `UCX_` collision imports with each FBX, that the Nanite fallback keeps the vertex-painted slab colours, and that the doorway and gate collision leaves the clear opening free (a trace test).
12. **Interiors** (the chapel nave, crypt, cloister) are out of the Phase 7 scope. The kit lists the P1 pieces they will need, but their dimensions (nave 1200 tall, crypt corridors ≥ 200 wide, tower 3500) are unchanged and may need `Wall_400x60x200` fillers to reach the tower height.

## 8. Lead decisions on the open questions (2026-10-23)
1. **60 cm walls:** accepted. The inner courtyard face stays on the greybox line; the east wall's extra 20 cm on the chapel side is unreachable space.
2. **Doorways:** keep the 120×240 clear opening (more room for the Warden's 84 cm capsule and the stoop). P7-003 rescales the door leaves to fit (about 118×238) and re-validates door collision, the Warden reachability test and WalkPath.
3. **Tower sightline:** P7-003 traces it in-engine from the spawn and from `CP_Courtyard`, before and after the rebuild. If the gate crown hides the tower from the spawn, lower the gate crown or the approach-side cliff tops, not the tower.
4. **Cliffs:** kit cliff slabs wearing the Rock_064 / rock-wall world-aligned materials, with `SM_Rock_Moss_Set_01` boulders at the base for breakup. No library cliff meshes (none are photoreal and free).
5. **Tower proxy:** no. The greybox tower stays and only gets the world-aligned ashlar MI for the silhouette; tower art is Phase 10.
6. **Blind lancet windows:** promoted to P0 (the flat chapel front is otherwise a weak spot). P0 = 26 pieces.
7. **Wall_400x60x800_B:** keep (repetition, R-26).
8. **Vertex colours:** the R wet / G grime / B wear contract is adopted. Kit meshes export vertex colours (default white = no effect); `M_LB_Surface` reads them in Phase 11.
