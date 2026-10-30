# Phase 10: Cloister and Bell Tower art (P10)

Branch `claude/phase-10-belltower`, from `main` fb5c3ba. The lead plans (D-048) and spawns every implementer with `model: "sonnet", effort: "high"`.

This file has two parts:
- this outline, with exact specs for P10-1 and P10-2;
- amendment **D1**, with the exact placements. The lead writes D1 after the P10-2 survey has measured the greybox, the gameplay Blueprints and the reusable kit.

## Owner choices (2026-10-29, D-077)
- **Scope: cloister and tower.** Phase 10 covers everything after the crypt exit:
  - the cloister walk and garth;
  - Mechanism 3 (the four small bells and the inscription);
  - the tower door;
  - the shortcut passage back to the courtyard;
  - the tower interior;
  - the bell chamber.
- **Tower climb: timber stairs around an open shaft.**
  - Wooden flights and landings sit on beams set into the stone walls.
  - They wind around an open central shaft, and the great bell's rope hangs down the middle.
  - A few broken treads and gaps show the drop. The walkable path stays solid.
- **Belfry: half-collapsed.**
  - Tall louvred openings on all four sides.
  - The roof has partly fallen in, so sky and moon show through one corner.
  - The enormous cracked bell hangs in a heavy timber frame.
- **Cloister: roofed vaulted walk.**
  - A covered walk with stone vaults around a small overgrown garth.
  - Part of the roof has fallen in, so moonlight comes through now and the storm phase's rain can come through later.
  - Monks' cell doors line the outer wall.
  - It must be darker and more enclosed than the courtyard.

**Out of scope** (deferred, not dropped):
- storm, rain and lightning VFX, and the cloth whipping in the wind: Phase 14–15, with the foliage wind (D-060);
- bell and puzzle audio: Phase 16;
- the finale's Warden and cinematic beats: Phases 12–13 and 17.

Phase 10 builds the static art and the base lighting (moon, lanterns and candles) that those phases will layer onto.

## Current greybox (`L_Monastery`; lead read-only survey, 2026-10-29)
World cm. Courtyard ground is Z 0. +X points away from the spawn.

### Cloister (folder `Cloister`)
- **Outer walls** (40 thick, 800 tall):

  | Wall | Actor | Extent |
  |---|---|---|
  | S | `Cl_S1` | X 9460–10500, Y 500–540 |
  | S | `Cl_S2` | X 10800–12040, Y 500–540 |
  | W | `Cl_W_S` | X 9460–9500, Y 540–1750 |
  | W | `Cl_W_N` | X 9460–9500, Y 2250–3040 |
  | W | `Cl_W_Lintel` | Y 1750–2250, Z 400–800 |
  | N | `Cl_N` | X 9460–12040, Y 3000–3040 |
  | E | `Cl_E_S` | X 12000–12040, Y 500–1500 |
  | E | `Cl_E_N` | X 12000–12040, Y 2500–3040 |

- **Openings in the outer walls:**
  - **S:** X 10500–10800. This is where the crypt exit stair arrives at Y 500.
  - **W:** Y 1750–2250, 400 high. This leads into the shortcut passage.
  - **E:** between `Cl_E_S` and `Cl_E_N`, where the tower's west wall forms the cloister's east side (X 12000, Y 1500–2500).
- **`Garth`:** a solid block X 10300–11400, Y 1400–2200, Z 0–100. It is 100 cm tall, so the player can't step onto it.
- **Arcade piers** (80 × 80 × 450):
  - S row `Arc_S0..4`, Y 1310–1390, at X 10300 / 10600 / 10900 / 11200 / 11400;
  - N row `Arc_N0..4`, Y 2210–2290, same X;
  - W `Arc_W0/1`, X 10210–10290, at Y 1700 / 2000;
  - E `Arc_E0/1`, X 11410–11490, at Y 1700 / 2000.
- **Walks** (outer wall to arcade):

  | Walk | Extent | Width |
  |---|---|---|
  | S | Y 540–1310 | 7.7 m |
  | N | Y 2290–3000 | 7.1 m |
  | W | X 9500–10210 | 7.1 m |
  | E | X 11490–12000 | 5.1 m |

  There is no roof.
- **Lights:** `Light_Cloister_0..7` (PointLight_43..50).

### Shortcut passage (folder `Courtyard`)
- `Passage_S` (X 6040–9460, Y 1660–1700) and `Passage_N` (Y 2300–2340), 800 tall, with no roof. The lane is 6 m wide.
- The west end is `Door_Shortcut` (BP_Door_Base, at X 6000, Y 1813–2069). It sits in the courtyard east wall's `KW_ShortcutDoorway`, which was dressed in P7.
- The east end is the cloister W opening.
- `Light_Courtyard_7` is in the lane.
- The chapel's north wall and buttresses lie to the south (Y 750–960).

### Bell Tower (folders `BellTower`, `BellTower/Stairs`, `BellTower/Railings`)
- **Shell:** X 12000–13000, Y 1500–2500 (10 × 10 m), walls 40 thick and 3500 tall.

  | Actor | Extent |
  |---|---|
  | `Tw_W_S` | Y 1500–1948 |
  | `Tw_W_N` | Y 2052–2500 |
  | `Tw_W_Lintel` | Y 1948–2052, Z 224–3500; above the 104 × 224 door |
  | `Tw_N` | — |
  | `Tw_S` | — |
  | `Tw_E` | — |
  | `Tw_Roof` | Z 3500–3540, flat |

- **`Tw_Core`:** X 12290–12710, Y 1790–2210, Z 0–2500. A solid 4.2 × 4.2 m stone core.
- **Stairs:** 11 flights × 14 steps (`Stair_F01_00 … Stair_F11_13`), with run 30 and rise 16.234.
  - They wind clockwise (seen from above) in the 250-wide ring between the core and the walls.
  - Corner landings `Tw_Landing_01..10` are 250 × 250, each 40 thick.
  - Every flight rises 227.27. The top is at Z 2500.
- **Railings** `Rail_F01_00 … Rail_F11_06` (77 pieces) are 10 thick and about 116 tall, along the core face.
- **Top:**
  - `Top_Slab_W` (X 12040–12290, Z 2460–2500) and `Top_Slab_N` (Y 2210–2460);
  - the core top (Z 2500) is the floor of the bell chamber;
  - `Top_Rail_E` and `Top_Rail_S` are 100 tall, on the core's east and south edges.
- **Bell supports:** `Bell_Beam` (X 12380–12460, Y 1900–2100, Z 3300–3400) and `Bell_Chain` (Z 2750–3300).
- **Lights:** `Light_Tower_0..5` (interior), `Light_TowerBell`, `Light_TowerExt_0..2`, `Light_TowerTop_0`.

### Gameplay (never moved or changed unless a step says so)
- **Cloister:**
  - `Trig_CloisterEntered` (BP_TagTrigger);
  - `CP_Cloister`;
  - `CP_TowerBase` (inside the tower base);
  - `Note_Cloister` (BP_Inspectable_Note, on the garth edge at (10750, 1425, 100)).
- **Mechanism 3** (D-035: bell sequence, 4 small bells, inscription clue):
  - `Puzzle_Bells` (BP_SequencePuzzle);
  - `Bell_1..4` (BP_SmallBell, at X ≈ 11983, Y 2200 / 2320 / 2440 / 2560, along the tower W wall);
  - `Clue_Inscription` (BP_Inscription, ≈ (11995, 2380, 200));
  - `Mech_Ritual3` (BP_RitualMechanism, (11750, 2000), in front of the tower door).
- **Doors:**
  - `Door_Tower` (BP_Door_Base, in the tower W wall opening, opens on Ritual.3);
  - `Door_Shortcut` (BP_Door_Base, in the courtyard east wall, opens on Ritual.3).
- **Tower:**
  - `Trig_TowerTop` (BP_TagTrigger, landing 10 → top);
  - `CP_TowerTop`;
  - `EndingTrigger` (BP_EndingTrigger);
  - `Bell` (BP_TagInteractable, the finale bell, on the core top at Z 2500–2750).
- **AI:**
  - `Patrol_Cloister_01..07`;
  - `Search_Cloister_02..14`;
  - `WSpawn_Cloister` (in the passage, (9240, 2000));
  - `WSpawn_Tower` (tower base).
- **WalkPaths:** `WP_TowerStairs_00..24` and `WP_CryptToCloister_00..10`. RouteBot drives the whole route: cloister → bells → Mech 3 → tower door → stairs → bell.

## Constraints
1. **Collision stays the greybox collision (the D-068 approach).**
   - The greybox actors keep their collision and become **not visible**: walls, core, steps, landings, railings, top slabs, garth, piers and passage walls.
   - The art is **NoCollision**, except for the pieces D1 lists by name.
   - So the navmesh, WalkPaths, RouteBot, the Warden routes and the stair step-up behaviour keep exactly what was tested.
   - The open shaft is visual only. The invisible `Tw_Core` keeps the player out of the shaft, and its face lies behind the visible inner railing (rails at X/Y 10 cm outside the core face).
2. **Stair fit:**
   - Every visible tread top is within **±1 cm** of its greybox step top (16.234 cm rises), and every visible landing top within ±1 cm of its greybox landing.
   - A tread may be visibly broken only where its greybox step stays (invisible) under the walk line. D1 lists the broken treads, and they never fall on a WalkPath point.
3. **The Warden paths the cloister and the passage** (D-038: nav agent 42 / 220; visual 2.9 m, stooping).
   - Clear width ≥ 180 everywhere it paths.
   - Clear height ≥ 300 under the vaults; the springing is ≥ 330 so the stooped Warden never clips.
   - The navmesh rebuilds valid, and the Warden cloister tests pass.
4. **Mechanism 3 readability:**
   - The four bells look different from each other (size and colour band) at 2 m by lantern light.
   - The inscription is legible at 2 m and opens its inspect text.
   - `Mech_Ritual3` reads as the tower-door mechanism.
5. **Tower silhouette:**
   - The tower is the game's landmark (LEVEL_DESIGN). From the spawn, the gate and the courtyard garth it must read as a tall stone bell tower with a louvred belfry and a broken roof against the sky.
   - The exterior is Nanite.
   - The moon shadow is kept (the courtyard's directional light).
6. **Performance:** GPU ≤ 16.6 ms at High in the cloister and at the top of the tower (owner measures). Interior lights are shadowless unless a step says otherwise.
7. **Tests:** suite 78/78, every WalkPath PASS, RouteBot Success, the Warden AI tests and the save tests.
8. Everything else as in P9:
   - explicit saves, **one package per `save_assets` call**;
   - the editor via `Tools/mcp/ue.py`;
   - captures via `capture_poses.py --raise`;
   - commits only on this branch;
   - never edit parent Blueprints (child BPs per D-071, with their construction scripts as MCP_NOTES describes).

## Tasks
| Task | Scope | Owner | Depends on |
|---|---|---|---|
| P10-0 | This outline, D-077, risks R-42…R-45, the plan table | lead | — |
| P10-1 | CC0 downloads: bell rope and a bronze patina | asset-curator | P10-0 |
| P10-2 | Read-only survey: exact greybox geometry, gameplay BPs, AI markers, reusable kit, sight lines, current-state captures | technical-artist [EDITOR read-only] | P10-0 |
| D1 | Exact layout (generator `Tools/belltower/gen_tower_layout.py`), D-078…, risks | lead | P10-1, P10-2 |
| P10-3 | Blender pieces: cloister vault bays, tower shell stages, timber stair set, belfry, bell frame, great bell, small-bell frame, cell door | technical-artist (no editor) | D1 |
| P10-4 | Materials and imports | technical-artist [EDITOR] | P10-3 |
| P10-5 | Structure: hide greybox, cloister, passage, tower shell, stairs, belfry, roof | environment-designer [EDITOR] | P10-4 |
| P10-6a | Dressing: garth, cells, rubble, timber debris, bell rope, lanterns, grime | environment-designer [EDITOR] | P10-5 |
| P10-6b | Child BPs: small bells, inscription, Mech 3, great bell, tower and shortcut doors | unreal-blueprint-engineer [EDITOR] | P10-4 |
| P10-7 | Lighting: moon through the collapsed roof and louvres, lanterns, candles, tower slit light; luma targets | lighting-vfx [EDITOR] | P10-6a, P10-6b |
| P10-8 | Docs, QA, owner GPU check and playtest; "PHASE 10 READY FOR YOUR REVIEW" | lead + qa + owner | all |

---

## P10-1 spec (asset-curator; no editor; commit "P10-1: …")
1. **Read first:** `CLAUDE.md`, `Docs/ASSET_REGISTRY.md` and `Docs/ASSET_PLAN.md` (rows 13 cloth/rope, 123 Mechanism 3 bells, 125 finale bell).
2. **Already present, do not re-download:**
   - `ambientcg-Metal017`;
   - `polyhaven-roof_slates_03`;
   - `polyhaven-weathered_planks`;
   - `polyhaven-medieval_blocks_03`;
   - `polyhaven-castle_wall_varriation`;
   - `ambientcg-Tiles139`;
   - `polyhaven-rusty_metal_04`.
3. **Download** with the `3d-assets-local` tools, CC0 only, 2K, JPG or PNG. Each goes in its own folder `ExternalAssets/Incoming/<provider>-<id>/`.
   1. **Rope** (bell ropes and the small bells' pull ropes): a coarse hemp or natural-fibre rope texture with Color, NormalGL and Roughness. Search ambientCG first (e.g. `Rope001`); otherwise Poly Haven.
   2. **Bronze patina** (the great bell and the small bells): an aged bronze or copper with green-brown verdigris, with Color, Normal, Roughness and Metalness if offered.
      - Search ambientCG (`Metal` sets with patina/verdigris) and Poly Haven (`green_metal_rust`, `rusty_metal`-like).
      - Pick the one whose colour reads as bronze with patches of green, not as iron rust.
   3. **Optional (only if a clear CC0 match exists):** a dark lichen-stained gravestone material for the garth grave slabs. Skip if nothing fits; the existing masonry MIs can serve.
4. **For each download:**
   - verify the files and resolution;
   - add an `ASSET_REGISTRY.md` row in the existing format (licence exactly as `get_asset` reports it; never invent one);
   - save one preview image to `Docs/ArtTest/belltower/p10_1_<id>.png` if the tool provides one.
5. **Report:** chosen IDs, why, licence, file lists. Commit only the registry and previews (`ExternalAssets/Incoming/` is git-ignored).
   - End the message with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
   - Never switch branches, merge or push.

## P10-2 spec (technical-artist; editor READ-ONLY; commit "P10-2: survey")
**Read first:**
- `CLAUDE.md`;
- `Tools/mcp/MCP_NOTES.md` (including the "Crypt and Phase 9 fix sets (P9)" section);
- this outline;
- `Docs/plans/P9_CRYPT_ART.md`, sections "P9-2" and D1.0 (the survey style and D-068).

**No mutation of any kind:** no set_properties, no transforms, no spawns, no saves, no PIE edits.
- Captures may run PIE Simulate. Set `bThrottleCPUWhenNotForeground=false` in memory only, restore it to true and read it back.
- Capture with `Tools/crypt/capture_poses.py <poses> <out> --raise` (editor mode `--editor` is allowed for the plan captures).
- Write the scripts in `Tools/belltower/survey/`.

**Output:** `Docs/ArtTest/belltower/survey_p10.md`, plus JSON dumps and captures in `Docs/ArtTest/belltower/`.

1. **Greybox geometry.** For every actor in the folders `Cloister`, `BellTower`, `BellTower/Stairs`, `BellTower/Railings`, plus `Passage_S`, `Passage_N`, `Ground_4`, `Ground_6` and the courtyard `KW_Shortcut*` pieces, record into `greybox_p10.json`:
   - label, mesh, world transform, world AABB;
   - collision profile, `bVisible`, materials.
   In the md, summarise:
   1. **Per stair flight** (F01…F11): direction, first and last step AABB, step run and rise as measured, the flight's lane extent, and the landing before and after it.
   2. **The railing** segment heights and planes per flight.
   3. **The exact top layout:** `Top_Slab_W/N`, the core top, `Top_Rail_E/S`, `Bell_Beam`, `Bell_Chain`.
   4. **What touches what:** gaps between the steps and the walls/core, and anything floating or intersecting.
2. **Gameplay Blueprints.** For each of these, record into `gameplay_p10.json`:
   - class, parent class, world transform;
   - components (name, class, mesh, relative transform, collision profile, visibility);
   - all instance-editable properties with their values, including InteractComp's tags, prompts and required/granted tags.

   The actors: `Puzzle_Bells`, `Bell_1..4`, `Clue_Inscription`, `Mech_Ritual3`, `Door_Tower`, `Door_Shortcut`, `Bell`, `EndingTrigger`, `Trig_TowerTop`, `Trig_CloisterEntered`, `CP_Cloister`, `CP_TowerBase`, `CP_TowerTop`, `Note_Cloister`.

   Also read the class defaults (CDO) of `BP_SmallBell`, `BP_SequencePuzzle`, `BP_Inscription`, `BP_RitualMechanism`, `BP_Door_Base` and `BP_TagInteractable`. Read their construction scripts with `read_graph_dsl`, read only.

   In the md, explain in plain words:
   - how Mechanism 3 works: which bell adds which tag, the order, the inscription text, what `Mech_Ritual3` requires and grants, what opens on Ritual.3;
   - how the finale `Bell` works (its tags, `EndingTrigger`).
3. **AI and navigation:**
   - list `Patrol_Cloister_*`, `Search_Cloister_*`, `WSpawn_Cloister` and `WSpawn_Tower` with world locations;
   - list the NavMeshBoundsVolume(s) covering the area and their bounds;
   - find which automation tests cover the cloister/tower (grep `Source/` for `Cloister`, `Tower`, `TowerStairs`, `Puzzle_Bells`, `Bell_`, `Ritual.3`, `Finale`) and list test names and what each checks.
4. **Reusable kit inventory.** List every project-made kit and prop mesh that could serve the cloister and tower, with bounds, pivot, material slots and UCX:
   - `/Game/LastBell/Environments/` kit pieces: walls, corners, buttresses, plinths, doorways, windows, the arcade twin-arch bay, cornice and string course;
   - the timber set: posts, purlins, rafters, planks;
   - the chapel truss and roof slabs;
   - the crypt pieces: vault bays, corbels, beams, boards;
   - `SM_LB_Prop_BellWheel_A`;
   - the Fab Dungeon door and the bars.
   Note which material instances each uses (masonry, trim, timber, slate). Use `Tools/blender/kit/build_kit.py` and `Tools/blender/props/build_props.py` as the index of what exists.
5. **Sight lines.** Using editor-mode captures, record what of the tower is visible from:
   - the spawn (−2800, 0, 170) looking +X;
   - the gate (300, 0, 170);
   - the courtyard garth (3400, 0, 170);
   - the courtyard shortcut door (5600, 2000, 170) looking +X;
   - the cloister S entry (10650, 700, 170) looking +Y;
   - the cloister NW corner (9700, 2900, 170) looking toward the tower.
   For each, note the tower's screen coverage and which faces are seen. Save `p10s_*.png` with poses in `Tools/belltower/poses/p10_survey_poses.json`.
6. **Current-state captures** (editor mode is fine):
   - the cloister from 4 corners;
   - the passage from both ends;
   - the tower base door;
   - Mechanism 3 at 2 m;
   - the tower interior looking up the shaft from the base (12150, 2000, 170, pitch 70);
   - landing 5;
   - the top (12160, 2330, 2670) looking at the bell.
7. **Report:**
   - the md, JSON and captures;
   - a list of anomalies (floating pieces, gaps, overlapping collision, mislabelled actors);
   - a confirmation that nothing was changed: map not dirty, no `TMP_`, throttle true.
   Commit the md, JSON, poses and captures (end the message with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`). Never switch branches, merge or push.

---

## Amendment D1 (2026-10-29, lead): exact layout, pieces, materials, Blueprints and lighting

**Inputs:**
- the P10-2 survey: `Docs/ArtTest/belltower/survey_p10.md`, `greybox_p10.json`, `gameplay_p10.json`, `kit_p10.json`;
- the P10-1 downloads: `ambientcg-Rope003` and `ambientcg-Metal058B`. Both are accepted. Rope003 is dark, so lift it in its MI. Metal058B is too pale and pink, so darken and warm it.

**Survey corrections to the outline above:**
1. The climb turns **left** (counter-clockwise seen from above). The lane headings are: N ring +X, E ring −Y, S ring −X, W ring +Y.
2. `Trig_TowerTop` sits at the SW corner of `Top_Slab_W`, where F11 arrives.
3. The inscription has no inspect component. Its acceptance check is "legible at 2 m"; no inspect is added (it would be a gameplay addition).
4. The doors cannot be opened by hand; they auto-open on `State.Ritual.3`.

**Units and conventions:**
- World cm. Rotators are `[pitch, yaw, roll]`.
- "Local" is the mesh frame.
- Every new Blender piece follows the kit conventions:
  - pivot at the bottom-left-back corner (bounds min = 0, 0, 0), with the "inner" face at local Y 0, unless the piece table says otherwise;
  - `MAT_*` slot names;
  - the seed listed in the table.
- Art is **NoCollision** unless D1.0 names it.

### D1.0 Decisions (DECISIONS D-078 … D-081)
1. **D-078: tower and cloister art over the invisible greybox collision (the D-068 approach).**
   - **Hidden:** every greybox actor in `Cloister`, `BellTower`, `BellTower/Stairs` and `BellTower/Railings`, plus `Passage_S`/`Passage_N`, gets `bVisible=false` with its collision unchanged:
     - walls, `Tw_Roof`, `Tw_Core`, steps, landings, rails, top slabs and top rails;
     - `Bell_Beam`, `Bell_Chain`, `Garth` and the 14 piers.
   - **Kept visible:** the courtyard `KW_Shortcut*` pieces, which P7 already dressed.
   - **The open shaft is visual only.**
     - The invisible `Tw_Core` keeps the player out of it.
     - At ground level the core's faces are covered by a visible stone **shaft base** (Z 0–450), so there is no invisible wall at the foot of the tower.
     - Above that, the core faces sit behind the visible inner balustrades, which stand on the rail planes 10 cm outside the core.
   - **Four timber shaft posts** stand on the core corners, inside the rail band.
   - **New collision (hidden BlockAll engine cubes), the only additions:**

     | Actor | Extent | Why |
     |---|---|---|
     | `Tw_Block_UnderStair` | X 12290–12300, Y 1540–1790, Z 0–454.5 | Closes the ground ring under F02/F03 (anomaly A2). The S and E ground rings become unreachable; `WSpawn_Tower` stays reachable in the W-ring south pocket. |
     | `Tw_Block_BrokenTread_F03` | X 12500–12530, Y 1540–1580, Z 568.2–768.2 | Over a visually missing tread end, so nobody walks on air |
     | `Tw_Block_BrokenTread_F06` | X 12920–12960, Y 2090–2120, Z 1201.3–1401.3 | Same |
     | `Tw_Block_BrokenTread_F09` | X 12470–12500, Y 2420–2460, Z 1931.8–2131.8 | Same |
     | `Cl_Block_PierSW` | X 10210–10260, Y 1310–1390, Z 0–330 | Corner-pier extension (the arcade has no corner piers; D1.3) |
     | `Cl_Block_PierSE` | X 11440–11490, Y 1310–1390, Z 0–330 | Same |
     | `Cl_Block_PierNW` | X 10210–10260, Y 2210–2290, Z 0–330 | Same |
     | `Cl_Block_PierNE` | X 11440–11490, Y 2210–2290, Z 0–330 | Same |

   - Art with simple collision (UCX, collision profile BlockAll):
     - the bell frame's 4 posts;
     - the great bell (convex hull, needed by the interaction trace);
     - the small bells' `Bell` meshes;
     - the Mech 3 pedestal and drum (through their Blueprints).
2. **D-079: tower silhouette and belfry.**
   - The tower is ashlar (`MI_Kit_Masonry`) in three stages:
     - S1: Z 0–800;
     - S2: Z 800–2500;
     - S3: the belfry, Z 2500–3540.
   - Exterior courses: plinth, drip, belfry sill and cornice.
   - Nine stair slits sit where they light a flight.
   - Each belfry face has two louvred lancets.
   - A steep pyramidal slate roof rises to the apex at Z 4740 (rise 1200, 66°) with an iron cross finial.
   - The **SW quarter of the roof and the top of the SW belfry corner have collapsed**, on the moon side. Moonlight enters there and runs down the open E-ring stairwell.
   - The tower reads as a landmark from the gate, the north half of the courtyard and the cloister. The chapel gable hides it from the courtyard garth; this is accepted.
3. **D-080: cloister and passage.**
   - **Outer walls:** visible walls 40 thick and 1300 tall, so the art is taller than the 800 collision. Each has a drip course where the lean-to roofs meet it.
   - **Arcade:** 14 piers plus 4 corner compound piers, with pointed arches (r = 0.8 × span) springing at Z 330 and an arcade wall to Z 620.
   - **Walk vaults:** four-centred **barrel vaults** with transverse ribs, springing at Z 560 (above every arcade arch) with the crown at Z 900. The corners get **groin vaults**.
   - **Roofs:** lean-to slate roofs from Z 640 at the arcade to Z 1200 at the outer walls.
   - **Collapsed bay:** the N walk's east bay (X 10850–11490), with a broken vault, a hole in the roof and rubble.
   - **Garth:** a raised burial garth, with a retaining wall flush with the `Garth` block, earth and grass, six grave slabs, four small crosses and a 3.5 m stone cross.
   - **Cells:** five cell doors.
   - **Passage:** walls dressed to 800, with a cobbled floor.
   - **Crypt exit:** a slate-roofed **stair-house** over the open stair trench south of the S opening.
4. **D-081: Mechanism 3 and the finale bell.**
   - **Small bells:**
     - Each hangs from a wall bracket at Z 120–160.
     - Four sizes: scale 1.30 / 1.15 / 1.00 / 0.85 for I / II / III / IV.
     - Four painted colour bands: red, ochre, green, bone.
     - Numeral plaques at Z 70–104.
   - **Inscription:** a pale stone tablet, unmoved.
   - **`Mech_Ritual3`:**
     - It becomes a capstan (the crypt winch meshes, dry materials).
     - It **moves to (11780, 1760, 50)**, beside the door instead of in front of it (anomaly A11).
     - A chain runs from it to the door.
   - **Doors:** both become `BP_Door_Base_Dungeon`.
   - **The finale bell:** a cracked bronze bell, 210 across the lip, in an oak frame with a headstock and wheel. Its rope runs through the floor and down the shaft.
   - **Note:** `Note_Cloister`'s text is rewritten for the bells (anomaly A7).
   - Bell motion and sound stay in Phases 16–17.

### D1.1 Tower: coordinates and face frames
- **Shell:** X 12000–13000, Y 1500–2500. Interior X 12040–12960, Y 1540–2460. Core X 12290–12710, Y 1790–2210. Flight rise 227.2727, tread rise 16.2338, run 30.
- **Face frames.** Every tower wall piece has local X along the face, local Y 0 = the inner face, local Y 40 = the outer face, local Z up. Place with:

  | Face | Location of local (0, 0, z0) | Yaw | Local x → world |
  |---|---|---|---|
  | W | (12040, 1500, z0) | 90 | x = Y − 1500 (length 1000) |
  | E | (12960, 2500, z0) | −90 | x = 2500 − Y (length 1000) |
  | N | (12040, 2460, z0) | 0 | x = X − 12040 (length 920) |
  | S | (12960, 1540, z0) | 180 | x = 12960 − X (length 920) |

  The W/E pieces cover the corners; the N/S pieces fit between them.
- **Stages:** S1 z0 = 0 (height 800), S2 z0 = 800 (height 1700), S3 z0 = 2500 (height 1040).
- **Exterior courses** (`MAT_Trim`, projecting outward from local Y 40; on every face, with their ends running past the piece ends by the projection, so they wrap the corners):

  | Course | World Z | Projection |
  |---|---|---|
  | Plinth | 0–60 | 10 (chamfered top); interrupted on the W face at the door, Y 1948–2052 |
  | Drip | 1210–1230 | 8 |
  | Belfry sill | 2470–2500 | 10 |
  | Cornice | 3480–3540 | 15 (cavetto profile); absent where the SW collapse breaks the wall top |

- **Openings.** Each slit is a pointed slit: 18 wide on the outer face, 100 tall (sill to apex, with the springing 18 below the apex). It splays to 50 wide × 120 tall at the inner face.

  | Piece | Opening | Local x (centre) | Local z (centre) |
  |---|---|---|---|
  | S1_W | **Door**: Y 1948–2052 = x 448–552, jambs z 0–194 with 8 cm chamfers; straight-sided pointed (gabled) head from z 194 at the jambs to the apex at z 228, x 500; a hood mould (`MAT_Trim`, 8 proud, 15 tall) 20 above the head | — | — |
  | S1_N | Slit F01 | 460 | 263.6 |
  | S1_E | Slit F02 | 500 | 490.9 |
  | S1_S | Slit F03 | 460 | 718.1 |
  | S2_W | Slit F08 | 500 | 1054.0 (world 1854) |
  | S2_N | Slits F05 / F09 | 460 / 460 | 372.7 / 1281.8 |
  | S2_E | Slits F06 / F10 | 500 / 500 | 600.0 / 1509.1 |
  | S2_S | Slit F07 | 460 | 827.3 |
  | S3, every face | **Two belfry lancets**: each 130 clear, sill z 200 (world 2700), jambs to z 650, equilateral pointed head (r 130) apex z 762.6 (world 3262.6); chamfered jambs, a 60 central mullion, a hood mould. W/E at x 340–470 and 530–660; N/S at x 300–430 and 490–620 | — | — |

- **SW collapse** (S3 pieces only):
  - **`S3_W_BrokenSW`:** over local x 0–320, the wall top is a jagged stepped break line. It runs from z 750 (world 3250) at x 0 up to z 1040 at x 320. Use `build_kit.stepped_profile` with seed 1003 and 6–9 steps, with fracture faces in `MAT_Rubble`.
  - **`S3_S_BrokenSW`:** the same over local x 600–920, from z 1040 at x 600 down to z 750 at x 920 (seed 1004).
  - No cornice over the broken spans.
- **Wall body:** use `build_kit.ashlar_body` with T = 40 and both faces dressed, following `build_wall`'s course logic with seeds 1001…1012 (one per piece in table order). Openings are carved with `carve_and_merge`. `MAT_Masonry` is ashlar on both faces.

### D1.2 Tower: interior pieces and placements
**Flight frame.** For a flight mesh, local x runs along the climb (0…420; tread i occupies x 30i…30i+30, i = 0…13). Local y runs from the core side (0) to the wall side (250). Local z = 0 is the flight's base. Tread i's top is at z = 16.2338 × (i + 1). Place flight k (k = 1…11) at base Z = (k − 1) × 227.2727 with:

| Ring | Flights | Location of local (0, 0, 0) | Yaw |
|---|---|---|---|
| N (+X) | F01, F05, F09 | (12290, 2210, base) | 0 |
| E (−Y) | F02, F06, F10 | (12710, 2210, base) | −90 |
| S (−X) | F03, F07, F11 | (12710, 1790, base) | 180 |
| W (+Y) | F04, F08 | (12290, 1790, base) | 90 |

| # | Piece | Spec | Slots | Pivot / placement |
|---|---|---|---|---|
| T1 | `SM_LB_Tw_StairFlight_250x420` | 14 oak treads, 6 thick, spanning y 1…249; nosing overhangs 2 at the front (−x); tread tops exactly as above. **Open risers.** Two inclined stringers, 8 wide × 28 deep, at y 0–8 and 242–250. Their top edge runs 8 above the nosing line, z = 16.2338 + (227.2727 / 420) × x + 8, for x −10…430. An iron wall bracket on the outer stringer at x 60, 210 and 360 (12 × 6 × 20, tucked 8 into the wall beyond y 250). Seed 1101. | MAT_Wood, MAT_Iron | Flight frame; flights F02, F04, F05, F07, F08, F10, F11 |
| T1c | `…_Closed` | T1 plus 2-thick riser boards and side panels (y 0–8 and 242–250) from the stringer down to z 0. | same | F01 |
| T1a | `…_BrokenA` | T1, but tread 6 lacks y 210–250 (splintered end, 3 jagged prongs), and tread 10 is split lengthwise at y 120 (both halves present, tops within 0.5). Seed 1102. | same | F03, F09 |
| T1b | `…_BrokenB` | T1, but tread 3 lacks y 210–250, and tread 9 is cracked at y 80. Seed 1103. | same | F06 |
| T2 | `SM_LB_Tw_FlightRail_420` | In the flight frame, on the rail band y 0…10: posts 8 × 8 at x 140 and 280, from the stringer top up to the handrail; an inclined handrail 8 wide × 6 tall with its top at z = 16.2338 × (x / 30 + 1) + 98 for x 0…420; a mid-rail with its top 50 lower. The handrail ends butt the shaft posts. Seed 1104. | MAT_Wood | Same transform as its flight, ×11 |
| T3 | `SM_LB_Tw_Landing_250` | Local x 0…250, y 0…250, pivot at the top-surface min corner (top z = 0). Boards 5 thick (z −5…0) along x; 4 joists 12 × 20 (z −25…−5) along x at y 30, 95, 160, 225; 2 stone corbels (`MAT_Masonry`, 30 wide × 40 deep × 35 tall, z −60…−25) under the x = 250 edge and 2 under the y = 250 edge (the wall sides). Seed 1105. | MAT_Wood, MAT_Masonry | See below |
| T4 | `SM_LB_Tw_ShaftBase_420x420x450` | Pivot at the bottom centre. A hollow square of 420 outer and 35-thick walls, Z 0–450, ashlar with a coping at z 430–450 projecting 3 **inward only** (the outer faces stay exactly on the core faces). Inside, a rubble floor (z 0–40, `MAT_Rubble`) with two broken treads lying on it. Seed 1106. | MAT_Masonry, MAT_Trim, MAT_Rubble, MAT_Wood | (12500, 2000, 0), yaw 0 |
| T5 | `SM_LB_Tw_ShaftPost_20x20x2015` | Pivot at the bottom centre. A 20 × 20 oak post, 2015 tall, with iron splice plates at z 670 and 1340 and an iron cap plate. Seed 1107. | MAT_Wood, MAT_Iron | Bottom Z 450; centres SW (12290, 1790), SE (12710, 1790), NE (12710, 2210), NW (12290, 2210) |
| T6 | `SM_LB_Tw_BelfryFloor` | Pivot at local (0, 0, 0) = world (12040, 1540, 2500). Boards 5 thick, top at z 0, covering three rectangles: x 0–250, y 0–920 (W slab); x 250–670, y 670–920 (N slab); x 250–670, y 250–670 (core top). Rope hole 30 × 30 at x 490–520, y 280–310 (world 12530–12560, 1820–1850). Under the core-top rectangle: 3 beams 25 × 30 (z −35…−5) along x from 240 to 680 at y 340, 450 and 560, plus edge trimmers along y 250 and x 670. Seed 1108. | MAT_Wood, MAT_Iron | (12040, 1540, 2500), yaw 0 |
| T7 | `SM_LB_Tw_TopRail_670` / `_420` | Pivot at the rail's start, on its centre line, at floor level. Local x runs along the rail (0…670 or 0…420), local y −5…+5. Posts 10 × 10 at the ends and every ≤ 120; a handrail with its top at z 98; a mid-rail with its top at 50. | MAT_Wood | `_670`: (12700, 1790, 2500), yaw 90 (runs Y 1790 → 2460); `_420`: (12290, 1800, 2500), yaw 0 (runs X 12290 → 12710) |
| T8 | `SM_LB_Tw_Partition_250x455` | Vertical boards 250 wide (local x) × 455 tall, 4 thick, with 2 rails; one board missing at x 150–170 (the dark behind shows). Seed 1109. | MAT_Wood, MAT_Iron | Origin (12290, 1790, 0), yaw −90: local x runs Y 1790 → 1540, local y (thickness 0…4) → X 12290–12294 |

**Landing transforms** (T3; tops at n × 227.2727):

| Corner | Landings | Location | Yaw |
|---|---|---|---|
| NE | 1, 5, 9 | (12710, 2210, top) | 0 |
| SE | 2, 6, 10 | (12710, 1790, top) | −90 |
| SW | 3, 7 | (12290, 1790, top) | 180 |
| NW | 4, 8 | (12290, 2210, top) | 90 |

- **Floor:** the tower floor is `SM_LB_Kit_Floor_Slab_1000x1000x40`, scale (0.96, 0.92, 1), at (12000, 1540, −38.5), `MI_Chapel_Floor_Dirty`. It also covers the door threshold.
- **Belfry** (pivots as listed):

| # | Piece | Spec | Slots | Placement |
|---|---|---|---|---|
| T9 | `SM_LB_Tw_Louvre_130x450` / `_Broken` | Pivot at the bottom centre of the opening on the inner face (local y 0). Nine boards, 130 long × 30 deep × 3 thick, sloping 40° (outer edge lower), spaced 50 vertically from z 25. Two side cleats. In `_Broken`, boards 3 and 4 are missing and board 5 hangs at 70°. | MAT_Wood | Each S3 lancet (8 in all): face frame, local (x_centre, 0, 200). `_Broken` on N x 365 and E x 595. |
| T10 | `SM_LB_Tw_BellFrame_A` | Pivot at the floor point under the bell axis.<br>• Four oak posts, 25 × 25, z 0–365, centred at (±140, ±135).<br>• Ground sills along x at y ±135: x −165…165, 25 wide × 20 tall.<br>• Head sills along x at y ±135: x −165…165, z 335–365.<br>• Cross-ties along y at x ±140: z 335–365.<br>• Four braces, 15 × 15, from each post at z 120 to the head sill at x ±60.<br>• Iron bearing blocks, 20 × 30 × 15, on the head sills at x 0.<br>• Iron bolts and straps.<br>UCX: 4 boxes, the posts only. Seed 1110. | MAT_Wood, MAT_Iron | (12420, 2000, 2500), yaw 0; **BlockAll** |
| T11 | `SM_LB_Tw_BellHeadstock_A` | Pivot at the axle centre.<br>• An oak headstock, 35 × 35, along y −150…150.<br>• Iron gudgeons at the ends.<br>• Iron straps down to the bell's canons.<br>• A **bell wheel**, Ø 260 (6 spokes, rim 12 × 10 with a rope groove), in the plane y −170.<br>Seed 1111. | MAT_Wood, MAT_Iron | (12420, 2000, 2880), yaw 0 |
| T12 | `SM_LB_Prop_GreatBell_A` | Pivot at the crown top centre; the bell hangs along −z.<br>**Lathe profile (outer):**<br>• canons (6 loops, iron-coloured bronze) z 0…−20;<br>• crown Ø 110 at z −20;<br>• shoulder Ø 130 at −35;<br>• waist Ø 150 at −120;<br>• sound bow Ø 196 at −200;<br>• lip Ø 210 at −220.<br>Wall thickness 6 at the waist and 14 at the sound bow.<br>**Details:**<br>• two raised mould rings at z −55 and −62;<br>• an iron clapper (shaft plus a Ø 22 ball at z −195);<br>• **a crack** on the −x side (local angle 180°), a 1.5-wide jagged groove from the lip up 90;<br>• a V-chip at the lip, 12 wide × 10 tall.<br>UCX: one convex hull of the outer profile. Nanite on; ≤ 20k tris. Seed 1112. | MAT_Bronze, MAT_Iron | Through the child BP (D1.6) |
| T13 | `SM_LB_Prop_BellRope_2610` | Pivot at the top. A Ø 3.5 rope from z 0 down to −2610, with 2 cm of sway over its length. A woollen **sally** (Ø 9, 100 long, red-ochre stripes) at z −2410…−2510. UVs run along the rope; Rope003 is 2:1, so v covers 1 per 140 cm. | MAT_Rope, MAT_Sally | (12550, 1830, 2750), yaw 0 (in the wheel plane, through the floor hole) |
| T14 | `SM_LB_Tw_Roof_BrokenSW` | Pivot at the bottom centre at the wall top: world (12500, 2000, 3540).<br>**Structure:**<br>• a pyramid from the eaves square (±525, z −10) to the apex (0, 0, 1200);<br>• slates (MAT_Slate) 6 thick on battens;<br>• a timber wall-plate ring;<br>• 4 hip rafters, 20 × 25;<br>• common rafters, 12 × 15 at 60 c/c, visible from inside;<br>• an iron cross finial, 90 tall, bent 20° toward +x.<br>**The SW quarter is missing:**<br>• on the −x face for y −525…−100, and on the −y face for x −525…−100, from the eaves up to z 860, with jagged slate edges;<br>• the SW hip snapped at z 600, with its stub hanging;<br>• 3 broken common rafters, one hanging down inside to z −300.<br>Seed 1113. | MAT_Slate, MAT_Wood, MAT_Iron | (12500, 2000, 3540), yaw 0 |

- **Chamber debris** (dressing, NoCollision, under 20 tall, within 35 of the W wall):
  - one `SM_LB_Prop_Rafter_Broken_15x10x260` lying along the W wall in the NW corner of the W slab, with target world AABB X 12045–12060, Y 2190–2450, Z 2500–2515 (the generator derives the rotator and location);
  - 4 kit rubble chunks at X 12045–12080, Y 2250–2450.
  - Nothing within 120 of `WP_TowerStairs_22/23/24`.

### D1.3 Cloister, passage and stair-house
**Wall pieces** (`MAT_Masonry` ashlar on both faces, a cap course at the top; T = 40; local Y 0 = the inner face):

| # | Piece | Notes | Seed |
|---|---|---|---|
| C1 | `SM_LB_Cl_Wall40_400x1300_A` / `_B`, `SM_LB_Cl_Wall40_100x1300` | Inner-face drip course (`MAT_Trim`) at z 1210–1230, projecting 6 | 1201 / 1202 / 1203 |
| C2 | `SM_LB_Cl_Wall40_400x800_A` / `_B`, `…_100x800` | Passage; no drip course | 1204–1206 |
| C3 | `SM_LB_Cl_Wall40_400x450`, `…_100x450` | Stair-house | 1207–1208 |
| C4 | `SM_LB_Cl_Archway_500x40x1300` | Local x 0–500. A four-centred arch over the full width: springing z 300 at x 0 and 500, apex z 420. A 40-deep voussoir ring (`MAT_Trim`), spandrel to z 1300, and the drip course on the cloister face only. **Place the piece in the W face frame with local Y 0 on the cloister side.** | 1209 |
| C5 | `SM_LB_Cl_Archway_300x40x1300` | Same, with springing 330 and apex 450 | 1210 |

**Arch construction for C4/C5:**
- The four-centred arch has lower arcs of radius span/4, centred on the springing line at span/4 from each side.
- The upper arcs are tangent to them and meet at the apex. Solve the upper radius numerically for the given apex.
- Write a `four_centred(span, rise)` helper.

**Wall runs.** Each run is filled left to right in its face frame with `n = round(L / 400)` 400-pieces scaled in X by `L / (400 n)`, alternating A/B. A 100-piece is used only when L < 300.

| Run | Face frame | Extent | Height piece |
|---|---|---|---|
| S wall west | S-type (yaw 180), local Y 0 at Y 540 | X 9460–10500 | 1300 |
| S wall east | S-type, Y 540 | X 10800–12040 | 1300 |
| N wall | N-type (yaw 0), Y 3000 | X 9460–12040 | 1300 |
| W wall south | W-type (yaw 90), X 9500 | Y 540–1750 | 1300 |
| W archway | W-type, X 9500 | Y 1750–2250, piece C4 | — |
| W wall north | W-type, X 9500 | Y 2250–3000 | 1300 |
| E wall south (`Cl_E_S`) | E-type (yaw −90), X 12000 | Y 540–1500 | 1300 |
| E wall north (`Cl_E_N`) | E-type, X 12000 | Y 2500–3000 | 1300 |
| S archway | S-type, Y 540 | X 10500–10800, piece C5 | — |
| Passage S (`Passage_S`) | S-type, local Y 0 at Y 1700 | X 6040–9460 | 800 |
| Passage N (`Passage_N`) | N-type, Y 2300 | X 6040–9460 | 800 |
| Stair-house W | W-type, X 10500 | Y −100…500 | 450 |
| Stair-house E | E-type, X 10800 | Y −100…500 | 450 |

- **Face-frame origins:**
  - **S-type:** local (0, 0, 0) is at (X_end, Y_face, 0), and local x runs −X.
  - **N-type:** at (X_start, Y_face, 0), and x runs +X.
  - **W-type:** at (X_face, Y_start, 0), and x runs +Y.
  - **E-type:** at (X_face, Y_end, 0), and x runs −Y.
  - The tower's own W wall carries the cloister's E side for Y 1500–2500.

**Arcade and garth:**

| # | Piece | Spec | Seed |
|---|---|---|---|
| C6 | `SM_LB_Cl_Pier_80x80x640` | Pivot at the bottom centre. A 6 cm-chamfered 80 × 80 shaft from z 25 to 300; base moulding z 0–25 projecting 4; a bell capital at z 300–330 projecting 8 (`MAT_Trim`); an 80 × 80 wall block at z 330–600; a coping at z 600–620 projecting 5 on both faces. | 1211 |
| C7 | `SM_LB_Cl_PierCorner_130x80x640` | The same profile on a 130 × 80 plan. Pivot at the bottom centre of the 130 × 80 rectangle. | 1212 |
| C8 | `SM_LB_Cl_ArcadeArch_{120,170,220,270}x80` | Pivot at local (0, 0, 0) = the left springing point on the pier line. Local x 0…span along the row, y −40…40, z 0…290 (world 330–620). A two-centred pointed arch with radius 0.8 × span (rise 0.742 × span): a 30-deep chamfered voussoir ring (`MAT_Trim`) and an ashlar spandrel to z 270, with the coping at z 270–290 projecting 5. | 1213–1216 |
| C9 | `SM_LB_Cl_GarthWall_1100x100` / `_800x100` | Local y 0 is the face toward the walk; the body runs to y +15 (into the garth). Ashlar 100 tall, with a coping (`MAT_Trim`) at z 88–100 reaching y −4…+30 (top exactly at z 100). | 1217–1218 |
| C10 | `SM_LB_Cl_GarthBed_1100x800` | Pivot at the min corner, z 0 = garth top. An earth surface (`MAT_Earth`) with 2–10 cm mounds, top ≤ 10. Six shallow grave hollows. | 1219 |
| C11 | `SM_LB_Cl_GraveSlab_200x80` | A slab 200 × 80 × 8, chamfered edges, a worn cross relief, lichen-ready UVs. | 1220 |
| C11 | `SM_LB_Cl_GraveCross_60` | A small stone cross, 60 tall, 8 thick. | 1221 |
| C11 | `SM_LB_Cl_GarthCross_350` | A stepped base 120 × 120 × 20 + 90 × 90 × 20, a chamfered shaft 24 × 24 to z 290, and a cross head 90 wide. | 1222 |

**Arcade placements** (`MI_Kit_Masonry` / `MI_Kit_Trim`):
- **Piers (C6):** 10 pieces, bottom Z 0, yaw 0, centred at:

  | Row | Centres |
  |---|---|
  | S | (10600, 1350), (10900, 1350), (11200, 1350) |
  | N | (10600, 2250), (10900, 2250), (11200, 2250) |
  | W | (10250, 1700), (10250, 2000) |
  | E | (11450, 1700), (11450, 2000) |

  The 4 row-end greybox piers (`Arc_S0`, `Arc_S4`, `Arc_N0`, `Arc_N4`) sit inside the corner piers.
- **Corner piers (C7):** centres (10275, 1350), (11425, 1350), (10275, 2250), (11425, 2250), yaw 0.
- **Arches (C8)**, each placed with its pivot at the left springing point, Z 330:
  - **S row** (yaw 0, from X−; pivot X, Y 1350): 220 at X 10340, 220 at 10640, 220 at 10940, 120 at 11240.
  - **N row:** the same X values at Y 2250, yaw 0.
  - **W column** (yaw 90; pivot (10250, Y)): 270 at Y 1390, 220 at 1740, 170 at 2040.
  - **E column:** the same Y values at X 11450.
- **Garth wall (C9):**

  | Face | Piece | Origin | Yaw |
  |---|---|---|---|
  | S | 1100 | (10300, 1400, 0) | 0 |
  | N | 1100 | (11400, 2200, 0) | 180 |
  | W | 800 | (10300, 2200, 0) | −90 |
  | E | 800 | (11400, 1400, 0) | 90 |

  `Note_Cloister` (10750, 1425, 100.25) lies on the S coping. Its top at z 100 is mandatory.
- **Garth bed (C10):** at (10300, 1400, 100).
- **Graves:**
  - slabs at (10500, 1600), (10500, 2000), (10700, 1650), (11000, 2000), (11200, 1600), (11200, 1950), with yaw 0 ± 4° jitter (seed 1223) and a 1–3° roll tilt;
  - small crosses at (10450, 1500), (11250, 1500), (10450, 2100), (11250, 2100);
  - the **garth cross** at (10850, 1800, 100), yaw 15.
- **Garth vegetation** (NoCollision, dressing P10-6a):
  - 40 grass clumps (`SM_LB_CC0_GrassMedium02_*`), 12 nettles, 8 ferns, scattered by a seeded script (seed 1224) inside X 10320–11380, Y 1420–2180, at Z 100–105;
  - keep 50 clear of the cross base, the slabs and `Note_Cloister`.

**Vaults** (`MI_Kit_Masonry` webbing, `MI_Kit_Trim` ribs):

| # | Piece | Spec | Seed |
|---|---|---|---|
| C12 | `SM_LB_Cl_Vault_Barrel_{830x640, 770x640, 770x640_Broken, 770x980, 570x980}` | Pivot at local (0, 0, 0) = the bay's min corner at the springing level. Local x runs along the walk (length), y across (span). A four-centred section (helper as for C4) with rise 340, apex at y = span/2, shell 25 thick. Transverse ribs (`MAT_Trim`, 30 wide × 25 deep below the shell) at both ends and at the mid-length. `_Broken`: over x 50–600 a jagged hole through the shell (seeded 1231), ragged course ends, the mid rib snapped with its two stubs. | 1225–1229 |
| C13 | `SM_LB_Cl_Vault_Groin_{770x830, 570x830, 770x770, 570x770}` | Pivot as for C12; local x span × local y span. A groin = the union of the two perpendicular four-centred barrels (rise 340) clipped to the square; diagonal ribs on the groin curves; wall ribs on the two outer sides. | 1232–1235 |

All vault bays are placed with springing Z **560**, yaw 0 (local x = world +X, local y = world +Y); the W/E barrels use yaw 90 (local x along +Y). The extents below already include the 30 cm tuck into the walls:

| Bay | Piece | Pivot location (min corner) | Notes |
|---|---|---|---|
| S walk west | Barrel_830x640 | (10210, 510, 560) | — |
| S walk east | Barrel_830x640 | (10850, 510, 560) | — |
| N walk west | Barrel_770x640 | (10210, 2260, 560) | — |
| N walk east | **Barrel_770x640_Broken** | (10850, 2260, 560) | the collapse |
| W walk | Barrel_770x980 | yaw 90; local origin at (10240, 1310, 560) | local x → +Y (1310–2290), local y → −X (10240 → 9470) |
| E walk | Barrel_570x980 | yaw 90; at (12030, 1310, 560) | local y → −X (12030 → 11460) |
| SW corner | Groin_770x830 | (9470, 510, 560) | x 770 along X, y 830 along Y |
| SE corner | Groin_570x830 | (11460, 510, 560) | — |
| NW corner | Groin_770x770 | (9470, 2260, 560) | — |
| NE corner | Groin_570x770 | (11460, 2260, 560) | — |

- **Corbels:** `SM_LB_Kit_Corbel_40x60x60`, `MI_Kit_Trim`, on the outer walls' inner faces under every rib end, top at Z 560. The P10-L generator lists them from the rib x positions.

**Roofs:**

| # | Piece | Spec | Seed |
|---|---|---|---|
| C14 | `SM_LB_Cl_LeanTo_1000x1050` / `_Hole` | A roof panel. Pivot at the eaves-line start. Local x along the eaves (0–1000), local y up the slope (0–1050) in the panel plane, local z the panel normal. Slates 6 (`MAT_Slate`) on battens, with rafters 12 × 15 at 60 c/c below (`MAT_Wood`). `_Hole`: over x 150–850, y 0–800 a jagged hole with broken battens and 3 rafters snapped (two stubs hanging 40–80 below). | 1236 / 1237 |

**Roof placement**, per walk:
- The eaves line is 30 beyond the arcade wall's garth face, at Z 640. The top line is the outer wall's inner face at Z 1200.
- The panel's y-scale = slope length / 1050, where the slope length = √(h² + 560²).
- Along the eaves, use 3 panels with x-scale = run / 3000.

| Walk | Eaves line | Top line | Run along the walk | h |
|---|---|---|---|---|
| S | Y 1420 | Y 540 | X 9500–12000 | 880 |
| N | Y 2180 | Y 3000 | X 9500–12000 | 820 |
| W | X 10320 | X 9500 | Y 540–3000 | 820 |
| E | X 11380 | X 12000 | Y 540–3000 | 620 |

- The N walk's **middle** panel (X 10833–11667) is `_Hole`. Its hole is local x 150–850 × 0.833, i.e. about X 10958–11541, over the broken vault (X 10900–11450).
- The P10-L generator computes each panel's rotator from its eaves line and top line, then checks that the transformed corners lie on those lines within 1 cm.
- At the corners the panels overlap and form the valleys.

**Floors** (`SM_LB_Kit_Floor_Slab_1000x1000x40`, Z −38.5, no overlaps):

| Label | Extent | MI |
|---|---|---|
| `CLA_Floor_S` | X 9500–12000, Y 540–1310 | `MI_Chapel_Floor_Dirty` |
| `CLA_Floor_W` | X 9500–10210, Y 1310–2290 | same |
| `CLA_Floor_E` | X 11490–12000, Y 1310–2290 | same |
| `CLA_Floor_N1` | X 9500–10850, Y 2290–3000 | same |
| `CLA_Floor_N2` | X 10850–11490, Y 2290–3000 | `MI_Chapel_Floor_Puddled` |
| `CLA_Floor_N3` | X 11490–12000, Y 2290–3000 | `MI_Chapel_Floor_Dirty` |

The ground slabs `Ground_1`, `Ground_2`, `Ground_4` and `Ground_6` (WorldGrid) get **`MI_Kit_Floor`** (cobbles, world-aligned), which covers the passage, the stair-house and the outside areas seen from the tower.

**Cell doors:**

| # | Piece | Spec | Seed |
|---|---|---|---|
| C15 | `SM_LB_Cl_CellDoorFrame_150x270` | Local y 0 = the wall face; the frame projects to y −8. A stone surround 150 wide × 270 tall, 20-wide jambs, and a straight-sided pointed head (shoulders at z 220, apex 250) around a 110 × 250 opening. A recessed back panel at y +2 (dark rubble) closes the opening. | 1238 |

- The leaf is `SM_Dungeon_door`, scale (0.5, 1.15, 1.2), set 1 cm in front of the back panel.
- **Placement**, centred on the wall face, with local y 0 on the face:
  - N wall at X 9900, 10500 and 11100, at Y 3000, **yaw 0** (local −y = world −Y, into the cloister);
  - W wall at Y 900 and 2700, at X 9500, **yaw 90** (local −y = world +X).
  - The door at X 11100 is under the collapse; its leaf hangs by one hinge (roll 4°, yaw +8°).

**Passage:** walls C2 on both sides as listed. Dressing: weeds along the wall bases, one wall lantern bracket (D1.7).

**Stair-house** (over the crypt-exit trench X 10500–10800, Y −100…500):
- **Side walls:** C3, as in the runs table, Z 0–450.
- **South gable:** C16 `SM_LB_Cl_StairHouseGable_380x40x650` (seed 1239): 380 wide, 40 thick, Z 0–650, with a triangular top from z 450 at the ends to 650 at the centre. Place it at X 10460–10840, Y −140…−100, with its inner face at Y −100.
- **Roof:** C17 `SM_LB_Cl_StairHouseRoof_420x640` (seed 1240): a pitched slate roof.
  - The ridge runs along local y at x 210, z 200.
  - The eaves are at x 0 and 420, z 0, with 20 cm overhangs.
  - The rafters are visible from below.
  - Place it at (10440, −140, 450), yaw 0, so the roof runs Y −140…500 and abuts the cloister S wall.
- **Lantern:** D1.7.
- **Hidden greybox:** inside the stair-house, the greybox railings `Rail_Up_W/E` are already lined from P9. Do not change them.
  - If any greybox white face is visible inside the stair-house, record it and line it as in P9 F1.
  - Never hide collision.

### D1.4 Mechanism 3 and cloister props (meshes for D1.6)

| # | Piece | Spec | Slots | Seed |
|---|---|---|---|---|
| M1 | `SM_LB_Prop_SmallBell_A` | Pivot at the crown top; the bell hangs along −z. Lathe: lip Ø 24 at z −28, sound bow Ø 22 at −25, waist Ø 16 at −14, crown Ø 10 at −3, and an iron hanging loop z 0…+4. An iron clapper ball, Ø 4, at z −24. A **painted band** ring on the shoulder (z −8…−5, slot `MAT_Band`). UCX: one convex hull. | MAT_Bronze, MAT_Iron, MAT_Band | 1301 |
| M2 | `SM_LB_Prop_SmallBellBracket_A` | Pivot at the back face of the wall plate, at the arm's axis height. The local +x axis points out of the wall. A wall plate 4 thick × 20 wide × 40 tall (z −25…+15), with 4 rivets. A cranked iron arm from the plate to x 30 at z 0, with a scroll. A hook at x 25. A small oak hood board above (x 0–34, z 18–22). | MAT_Iron, MAT_Wood | 1302 |
| M3 | `SM_LB_Prop_BellPlaque_A` | Pivot at the back centre; the front faces +x. A stone plaque 4 deep × 34 wide × 34 tall, with a 3 cm moulded border and a recessed field. | MAT_Trim | 1303 |
| M4 | `SM_LB_Prop_InscriptionTablet_A` | Pivot at the back centre; the front faces +x, matching the parent `Plaque` axis. A tablet 4 deep × 120 wide × 30 tall (× 2.5 root scale = 300 × 75 × 10 in world), with a moulded frame and a slightly recessed field. | MAT_Trim | 1304 |

- **The capstan** reuses `SM_LB_Crypt_CapstanDrum_80x50` and the stone pedestal that `BP_RitualMechanism_CryptWinch` uses.
- **The chain** reuses the Dungeon pack chain mesh used in the P9 chain chamber (same asset path).

### D1.5 Materials (P10-4)
- **`MI_LB_BellBronze`** (child of `M_LB_Surface`, Metal058B Color/NormalDX/Roughness/Metalness):
  - BrightnessMul 0.5;
  - tint (0.62, 0.45, 0.32), giving a dark warm bronze with darker green patches;
  - metallic from the map, × 0.9;
  - roughness range 0.45–0.75.
  - Target: it reads as dark bronze with green patina, not pink copper. Check with a lit capture.
- **`MI_LB_Rope`** (Rope003 Color/NormalDX/Roughness): BrightnessMul 1.5, tint (1.0, 0.88, 0.70).
- **`MI_LB_Sally`:** flat tint (0.42, 0.14, 0.08), roughness 0.95.
- **Band MIs** (flat tints on `M_LB_Surface`, roughness 0.8):

  | MI | Tint |
  |---|---|
  | `MI_LB_BellBand_I` | (0.32, 0.07, 0.05) |
  | `MI_LB_BellBand_II` | (0.42, 0.30, 0.08) |
  | `MI_LB_BellBand_III` | (0.10, 0.22, 0.17) |
  | `MI_LB_BellBand_IV` | (0.66, 0.62, 0.52) |

- **Slot mapping:**

  | Slot | MI |
  |---|---|
  | MAT_Masonry | `MI_Kit_Masonry` |
  | MAT_Trim | `MI_Kit_Trim` |
  | MAT_Rubble | `MI_Kit_Rubble` |
  | MAT_Wood (tower timber, bell frame, headstock) | `MI_Chapel_Wood_Old` |
  | MAT_Wood (cloister roofs, stair-house) | `MI_Prop_Wood_Weathered` |
  | MAT_Iron | `MI_Crypt_Iron` |
  | MAT_Slate | `MI_Kit_Slate` |
  | MAT_Earth | `MI_Prop_Earth` |
  | MAT_Bronze | `MI_LB_BellBronze` |
  | MAT_Rope | `MI_LB_Rope` |
  | MAT_Sally | `MI_LB_Sally` |
  | MAT_Band | `MI_LB_BellBand_III` (default) |

- **Nanite** on for every architecture piece, the roof, the vaults, the great bell and the bell frame. **Off** for the rope, the louvres, the small-bell set and the brackets.
- **Collision:** every piece imports with **no simple collision**, except T10 (its 4 post UCX), T12, M1 and the T4 shaft base. T4 gets **none**; the invisible core handles collision.

### D1.6 Child Blueprints (P10-6b)
Use the D-071 procedure for each child:
- copy the parent's construction-script body;
- set the meshes and values in the construction script;
- keep the parent's component and variable names;
- compile with warnings as errors;
- dump before and after, and diff;
- swap the placed instance keeping its label, folder, transform and every instance value.

The parent BPs are never edited. The `Puzzles.Blueprints` test spawns the parent `BP_SmallBell`, which stays untouched.

1. **`/Game/LastBell/Blueprints/Puzzles/BP_SmallBell_Cloister`** (parent `BP_SmallBell`).
   - **New variables** (instance-editable): `BellScale` (float, default 1.0) and `BandMaterial` (MaterialInterface, default `MI_LB_BellBand_III`).
   - **Construction script, after the parent body.** All locations are actor-local; the actor has yaw 180, so local +x points into the walk and the wall face is at local x −17.

     | Component | Mesh / material | Relative location | Relative scale | Collision | Visible |
     |---|---|---|---|---|---|
     | `Post` | M2 | (−17, 0, 145) | 1 | NoCollision | yes |
     | `Arm` | — | — | — | NoCollision | **hidden** |
     | `BellPivot` | — | (8, 0, 140) | — | — | — |
     | `Bell` | M1; slot 2 = `BandMaterial` | (0, 0, −2) relative to BellPivot | `BellScale` | BlockAllDynamic (unchanged) | yes |
     | `Clapper` | — | — | — | NoCollision | **hidden** |
     | `Plate` | M3 | (−17, 0, 87) | 1 | NoCollision | yes |
     | `Glyph` | — | (−12.8, 0, 87) | — | — | yes |

     - `Glyph` keeps its parent rotation; set WorldSize 18 and colour (0.10, 0.09, 0.08).
     - Before writing, check that the parent's `Plate` and `Glyph` rotations face local +x. If they don't, report it and rotate the new meshes to match.
   - **Swaps** `Bell_1..4` (same transforms):

     | Bell | `BellScale` | `BandMaterial` |
     |---|---|---|
     | `Bell_1` | 1.30 | `MI_LB_BellBand_I` |
     | `Bell_2` | 1.15 | `MI_LB_BellBand_II` |
     | `Bell_3` | 1.00 | `MI_LB_BellBand_III` |
     | `Bell_4` | 0.85 | `MI_LB_BellBand_IV` |

     Copy `StruckTag`, `SymbolIndex` and every `InteractComp` value.
   - **Checks:**
     - a 120 cm eye-height (160) trace from the walk hits each `Bell`;
     - each bell swings when struck in PIE;
     - the numerals are legible at 2 m.
2. **`/Game/LastBell/Blueprints/Interactables/BP_Inscription_Cloister`** (parent `BP_Inscription`).
   - `Plaque` uses M4 with the parent's relative transform. Check the result in world: 300 × 75 × 10, flush to X 12000.
   - `Engraving` colour (0.08, 0.07, 0.06). Keep `Text`.
   - Swap `Clue_Inscription` in place (Z 200 unchanged).
3. **`/Game/LastBell/Blueprints/Interactables/BP_RitualMechanism_TowerCapstan`** (parent `BP_RitualMechanism`).
   - Copy `BP_RitualMechanism_CryptWinch`'s construction script, meshes and `RequiredTags` variable pattern.
   - Material overrides: wood `MI_Prop_Wood_Weathered`, stone `MI_Kit_Masonry`, iron `MI_Crypt_Iron`.
   - Swap `Mech_Ritual3`, keeping every value: `RitualTag` `State.Ritual.3`, required `State.Tower.BellsSolved`.
   - **Then move it to (11780, 1760, 50), yaw 0** (D-081).
   - Only the BP's own pedestal and drum are used; no `SM_LB_Crypt_WinchFrame`.
   - Its world AABB must stay ≥ 60 + 42 cm (the Warden radius) from the `Patrol_Cloister_04 → 05` segment, which passes X ≈ 11609 at Y 1760. Read the bounds back and report them.
   - **Checks:**
     - the RouteBot interacts with it;
     - the Warden reachability test passes, including the `Patrol_Cloister_04 → 05` segment.
4. **Doors:** swap `Door_Tower` and `Door_Shortcut` to the existing **`BP_Door_Base_Dungeon`**.
   - Copy `OpenStateTag`, `AutoOpenTag` (`State.Ritual.3`), `bInteractable` false, `OpenYaw`, `OpenDuration`, `InteractComp` and the actor scale: 1 for `Door_Tower`; (1, 1.18, 1.0818) for `Door_Shortcut`.
   - Check that both leaves fill their openings with no light gaps above 2 cm, and that in PIE both swing open when `State.Ritual.3` is added.
5. **`/Game/LastBell/Blueprints/Interactables/BP_TagInteractable_GreatBell`** (parent `BP_TagInteractable`).
   - `Mesh` is T12, with relative location (0, 0, 94) and relative scale 0.4. The instance root scale 2.5 is kept, so the world scale is 1 and the crown top sits at Z 2860.
   - Swap `Bell`, keeping `UseStateTag` `State.Event.Finale` and all `InteractComp` / `InspectableComp` values.
   - **Checks:**
     - world bounds ≈ X 12315–12525, Y 1895–2105, Z 2640–2860;
     - an eye-height trace from `WP_TowerStairs_24` (12165, 2000, 2500 + 160) hits the bell;
     - RouteBot Success, including the finale.
6. **`Note_Cloister`** instance `BodyText` (owner may edit the wording; `DisplayName` stays "The Last Entry"):

   > The great bell rang again tonight, and no hand was on the rope. Brother Anselm says the four small bells beside the tower door still answer to the old order of the dead, and that the order is cut in the stone above them. Strike them as the dead recall, and the tower will open. I will not go up. God forgive whoever does.

### D1.7 Dressing (P10-6a; NoCollision unless stated)
- **Mech 3 chain:** from the capstan drum (11810, 1760, 110) to an iron wall eyelet at (11995, 1800, 140), then along the wall to a latch box (an iron box 20 × 8 × 30) at (11995, 1935, 120) beside the door.
- **Collapse rubble** (N walk east bay):
  - a `SM_LB_Kit_Rubble_Heap_400x300x130` scaled (0.8, 0.7, 0.5), yaw 0, with target world AABB X 11050–11370, Y 2295–2505, Z 0–65 (kit pivot = min corner, so it sits at (11050, 2295, 0));
  - 6 kit rubble chunks and 4 vault voussoir chunks (seeded, 1401) inside X 11000–11450, Y 2300–2500;
  - one `SM_LB_Prop_Rafter_Broken_15x10x260` leaning from the floor (11300, 2330) up to the arcade wall top.
  - **Keep 120 clear of `Search_Cloister_14` (10850, 2500), `Search_Cloister_12` (11350, 2850) and `Patrol_Cloister_03` (10850, 2750).**
  - The heap is **BlockAll**. Before saving, the lane check must show ≥ 60 clearance on the `Patrol_Cloister_03 → 04` segment.
- **Cells:** a stool and a bucket by the W-wall door at Y 2700 (within 40 of the wall).
- **Grime decals:** 8 damp/mould decals on the outer walls' inner faces at Z 0–200 (`MI_Decal_*`, as in P8 C5).
- **Ivy:** 4 `_Dead` ivy cards on the garth-facing arcade wall.
- **Lanterns:** `SM_Wooden_Lantern_01` on an iron bracket (`SM_Dungeon_chain_holder`) at every light position in D1.8 that says "lantern".
- **Tower:**
  - one coil of rope at the shaft base's top rim (dressing inside the shaft base);
  - 4 broken slates on landing 10 (within 30 of the walls);
  - cobweb cards (`M_LB_Cobweb`, as in P8) in 6 landing corners at Z top+150…+220.
- **Passage:** weeds (`SM_LB_CC0_Weed*`) along both wall bases (within 40), 20 pieces.

### D1.8 Lighting (P10-7; shadowless unless stated)
1. **Delete:**
   - `Light_Cloister_0..7`;
   - `Light_Tower_0..5`, `Light_TowerBell`, **`Light_TowerTop_0`** (20000 lm above the roof);
   - `Light_Courtyard_7`.
2. **Keep** `Light_TowerExt_0..2` (the W-face moon wash). Tune them 200–400 lm so the tower's W face reads against the sky from the gate.
3. **New lights:**

   | Label | Location | lm | Radius | Colour | Notes |
   |---|---|---|---|---|---|
   | `L_Cl_Bells` | (11960, 2380, 320) | 250 | 600 | 2200 K | Lantern above the inscription |
   | `L_Cl_Door` | (11960, 1880, 300) | 200 | 500 | 2200 K | Lantern beside the tower door |
   | `L_Cl_Entry` | (10520, 300, 300) | 150 | 450 | 2200 K | Stair-house lantern |
   | `L_Cl_West` | (9560, 2000, 320) | 150 | 450 | 2200 K | W walk, at the passage arch |
   | `L_Cl_Cell` | — | 60 | 200 | 1900 K | Candle cluster at the N-wall door at X 9900, Z 30 |
   | `L_Ps_Lantern` | (9380, 2240, 300) | 150 | 500 | 2200 K | Passage, cloister end |
   | `L_Tw_Base` | (12060, 1880, 260) | 150 | 450 | 2200 K | Tower base |
   | `L_Tw_Land4` | — | 100 | 350 | 2200 K | 30 above the NW landing-4 top |
   | `L_Tw_Land7` | — | 100 | 350 | 2200 K | 30 above the SW landing-7 top |
   | `L_Tw_Land10` | — | 100 | 350 | 2200 K | 30 above the SE landing-10 top |
   | `L_Tw_Bell` | (12290, 1865, 2700) | 150 | 500 | 2200 K | On the bell frame post |
   | `L_Tw_BellFill` | (12500, 2300, 3300) | 120 | 900 | (0.75, 0.80, 0.92) | Moon fill |

4. **Fog:** `LFV_Tower` covering X 12040–12960, Y 1540–2460, Z 0–3500, with extinction low enough that the slit and roof moonbeams read as shafts. P10-7 tunes it.
5. **Moon:** keep `DirectionalLight` (pitch −38, yaw 35). The art openings receive it because the greybox walls and roof are hidden and cast no shadow.
6. **Targets** (PIE Simulate captures; the luma method of P9):

   | View | Pose | Target |
   |---|---|---|
   | Cloister S-walk entry | (10650, 700, 170, 0, 90) | mean 0.04–0.08 |
   | Inscription | 2 m | text contrast ≥ 2.5 |
   | Numerals | 2 m | each legible |
   | Tower stairs | landing 5 | mean 0.02–0.06, with slit beams visible from the S/W slits |
   | Bell | top, from `WP_TowerStairs_24` | bell median ≥ 0.08 |
   | Tower from the gate | (300, 0, 170) | the belfry and the broken roof read against the sky |

### D1.9 Generator (P10-L) and placement (P10-5)
`Tools/belltower/gen_tower_layout.py` (written in P10-L) implements D1.1–D1.4 and D1.7 **exactly**. It writes:
- `Docs/plans/p10_d1_layout.json`, one record per actor:
  - `id` (label), `cat` (wall, tower, stair, vault, roof, arcade, garth, floor, door, dress, block, light);
  - `mesh`, `loc`, `rot` `[pitch, yaw, roll]`, `scale`;
  - `collision` (NoCollision, BlockAll, hidden-block);
  - `folder`;
  - `mbounds` (mesh-local bounds from the piece tables);
  - `aabb_min/max` (expected world AABB);
  - `mi_slots` (slot → MI);
  - `extras`;
- `Docs/plans/p10_d1_tables.md`;
- `Docs/ArtTest/belltower/d1_layout_plan.png` (top view, plus a tower section view).

**Never hand-edit the JSON or the tables.** If a value must change, change the generator, re-run it, and commit the generator and its outputs together.

**Labels:**

| Prefix | Use | Folder |
|---|---|---|
| `TWA_` | Tower art | `BellTower/Art/<Group>` |
| `CLA_` | Cloister art | `Cloister/Art/<Group>` |
| `PSA_` | Passage art | `Courtyard/Passage` |
| `SHA_` | Stair-house art | `Cloister/Art/StairHouse` |
| `L_Cl_`, `L_Tw_`, `L_Ps_` | Lights | `Lighting/Cloister`, `Lighting/BellTower` |

Never use `CP_`.

**Built-in checks** (the generator exits 0 only if all pass):
1. **Treads:** every T1 tread top (computed from the flight transform) is within 1.0 cm of `greybox_p10.json`'s step tops, for all 154. Every landing top is within 1.0 of its greybox top.
2. **Lanes:** no art record with NoCollision or BlockAll intrudes into the WalkPath lanes or AI points (`Tools/crypt/lane_check_crypt.py`'s method with this phase's segments). The clearance must be ≥ 60 cm from:
   - `WP_TowerStairs_00..24` segments (walk-line clearance only for records below head height 200 above the local floor);
   - `WP_CryptToCloister_09..10`;
   - the `Patrol_Cloister` route segments (including the wrap-around);
   - all `Search_Cloister` points;
   - the `WSpawn` points.

   Exempt: wall faces (inner face coincident with the greybox face), floors, the vaults and roofs above Z 300, and the balustrades on the rail planes.
3. **Faces:** every wall-piece inner face is within 0.5 cm of its greybox face. Every tower piece is inside the shell AABB, apart from the exterior courses and the roof.
4. **Rails:** the rail bands (T2) lie on the rail planes within 0.5. The shaft posts lie inside the 10 cm rail band plus the core.
5. **Overlaps:** no two vault bays overlap by more than their 30 cm tucks.
6. **Counts:**

   | Item | Count |
   |---|---|
   | Flights | 11 |
   | Landings | 10 |
   | Flight rails | 11 |
   | Louvres | 8 |
   | Piers | 10 + 4 |
   | Arches | 14 |
   | Vault bays | 10 |
   | Roof panels | 12 |
   | Hidden blocks | 8 |
   | Cell doors | 5 |

**P10-5** places from the JSON. Adapt `Tools/crypt/place_crypt.py` into `Tools/belltower/place_tower.py`, with the same `--cats`, `--only`, `--check` and `--fix-collision`, plus `--hide-greybox` / `--verify-greybox` for D1.0.

### D1.10 Task order and owners (all `model: "sonnet", effort: "high"`)

| Task | Owner | Depends on | Notes |
|---|---|---|---|
| **P10-3a** | technical-artist, Blender only | — | Tower pieces T1–T14 in `Tools/blender/belltower/build_tower.py` plus `verify_tower.py`; FBX in `SourceArt/BellTower/`; renders `Docs/ArtTest/belltower/p10_3a_*.png` |
| **P10-3b** | technical-artist, Blender only | — | Cloister and Mech 3 pieces C1–C17 and M1–M4 in `Tools/blender/belltower/build_cloister.py` plus `verify_cloister.py`; renders `p10_3b_*.png` |
| **P10-L** | environment-designer, no editor | — | The generator, its outputs and its checks |
| **P10-4** | technical-artist [EDITOR] | P10-3a, P10-3b | Imports to `/Game/LastBell/Environments/BellTower/Meshes/` and `/Cloister/Meshes/`, the MIs in D1.5, Nanite and collision per D1.5, thumbnails |
| **P10-5** | environment-designer [EDITOR] | P10-4, P10-L | Hide the greybox, add the hidden blocks, place everything structural, set the ground MIs, line any greybox seen in the stair-house; gap pass; suite |
| **P10-6b** | unreal-blueprint-engineer [EDITOR] | P10-5 | D1.6 |
| **P10-6a** | environment-designer [EDITOR] | P10-6b | D1.7 |
| **P10-7** | lighting-vfx [EDITOR] | — | D1.8 |
| **P10-8** | lead + owner | all | Docs, owner GPU check and playtest, "PHASE 10 READY FOR YOUR REVIEW" |

- **Parallel work:** P10-3a, P10-3b and P10-L run together. They touch separate files; commit only your own paths, and if the git index is locked, wait 5 s and retry.
- **Editor tasks never overlap.**
- **Every [EDITOR] task:**
  - saves one package per `save_assets` call;
  - stops all editor calls after a 180 s hang;
  - uses `capture_poses.py --raise` with the breaker;
  - runs the suite at 78/78;
  - commits with the prefix `P10-<task>: `.

### D1.11 P10-L review and D1 errata (lead, 2026-10-30)
**P10-L accepted** (4c2e379): 385 records, every D1.9 check passes.

| Check | Worst value |
|---|---|
| Tread tops (154) | 0.0009 cm |
| Landing tops (10) | 0.0045 cm |
| Wall faces | 0.000 cm |
| Rail bands | 0.000 cm |
| Vault overlaps | 30.0 cm (= the tuck) |
| Lanes: TowerStairs | 77.0 cm |
| Lanes: Patrol route | 63.6 cm (Mech 3) |
| Lanes: Search points | 65.9 cm |
| Lanes: WSpawn points | 83.0 cm |

The wrap-around patrol segment that crosses the garth is routed around it, which is accepted as the lane method.

**Errata** (the generator applies 1–6; the P10-3b and P10-6b agents take 3 and 7):
1. **N-walk roof panels.** D1.3's "3 equal panels, middle X 10833–11667" was arithmetically wrong; the equal split puts the middle panel at X 10333–11167. The N walk now uses:

   | Panel | X range | x-scale |
   |---|---|---|
   | W | 9500–10650 | 1.15 |
   | Hole | 10650–11650 | 1.00 (hole X 10800–11500, over the vault hole X 10900–11450) |
   | E | 11650–12000 | 0.35 (mostly under the E roof at the NE valley) |

2. **Bell rope:** Y 1835, so it clears the shaft base's S inner wall (Y 1825) and still passes through the floor hole.
3. **Inscription tablet (D1.6.2):** the child BP sets `Plaque` relative **X −2**, because M4's pivot is at its back. The tablet back is then at world X 12000.
4. **Lanterns:** every warm light except `L_Cl_Cell` (candles) and `L_Tw_BellFill` gets a lantern on a wall bracket. The landing lanterns hang at the landing's outer wall corner, Z = top + 180.
5. **`L_Tw_Bell`** moves to (12255, 1865, 2690), clear of the frame post.
6. **Cell-door leaves:** scale (0.5, 1.15, 1.37), so the leaf is 250 tall to match the frame.
7. **Garth bed (C10):** its outer 35 cm band sits flat at z −1, under the coping top. The mounds stay inside the band, so there is no z-fighting at `Note_Cloister`.

**Also accepted as implemented:**
- the collapse rafter leans against the arcade face at Z 258 (a 260 rafter cannot reach Z 620);
- the pier tops are at 620, and the name `…x640` is kept;
- C11 pieces use bottom-centre pivots;
- the latch box is 8 deep × 20 wide × 30 tall.

### D1.12 P10-3a / P10-3b review; generator sync; P10-4 spec (lead, 2026-10-30)
**P10-3a accepted** (ba1f0e6, 27ae1dc):
- 33 tower meshes; `verify_tower` 33/33.
- **Renders:**
  - `tower_SW_overview` reads as a tall ashlar bell tower with twin louvred lancets and a broken SW roof corner;
  - `belfry_interior_bell` shows the massive cracked bronze bell in its oak frame, with the wheel, chain and rope;
  - `stair_core_section_close` shows open-riser oak flights on corbelled landings around the stone shaft base, with shaft posts and the under-stair partition.
- **Deviations accepted:**
  - N/S courses run 40 past the piece ends, plus corner quoins;
  - every wall piece carries the third kit slot, `MAT_Rubble`;
  - an iron chain bridges the wheel rim (axle height) to the rope top at Z 2750;
  - the bell's canons use the iron slot;
  - the louvre `_Broken` keeps 7 of 9 boards;
  - stringer brackets reach 8 into the wall;
  - extra joists under the W/N slabs;
  - the bell-frame and top-rail bounds differ by 2.5.

**P10-3b accepted** (b22300f, 42307f1):
- 40 cloister and Mech 3 meshes; `verify_cloister` 40/40.
- **Renders:**
  - `cloister_corner_walk` reads as a dark ribbed barrel-vaulted walk with pointed arcade arches and a cell door;
  - `mech3_bells_inscription` shows four bells of different sizes with red/ochre/green/bone bands, I–IV plaques, and the carved tablet readable above them;
  - `collapse_ne_bay_walk` shows a fallen vault bay with sky and broken rafters.
- **Deviations accepted:**
  - `four_centred` is fixed with a 9° apex slope for the archways; C4 uses r1 = 87.5;
  - the vault sections use upper radius = span, and rise 340 is to the extrados apex;
  - the archways have no mesh below the springing;
  - the pier mouldings project on all faces (bounds 96 and 146);
  - C12 is named span × length;
  - C13's wall ribs sit 30–60 in;
  - C16 has a flush coping;
  - C14's hole is a jagged outline inside x 150–850 / y 0–800.

**Corrections for the generator** (the P10-L agent applies them; then re-run and commit "P10-L: D1.12 sync"):
1. **All 10 vault bays spring at Z 540** (was 560), and the corbel tops move to 540. Reason: the P10-3b section shows the S-walk vault extrados within the roof's rafter build-up near the arcade haunch (21 cm deep on S, 12 on N/W). Lowering 20 leaves ≤ 1 cm on S, and the slates stay untouched.
   - Side effect accepted: the top 20 cm of the 270-span arches' voussoir rings on the W/E walk faces sits behind the vault haunch.
2. **Pieces table synced to the built meshes:** read `SourceArt/BellTower/tower_report.json` and `SourceArt/Cloister/cloister_report.json`.
   - Use the measured bounds as `mbounds` for every new piece.
   - Use the real slot lists. All wall, arch, pier, garth-wall, vault, gable, frame and grave pieces have `MAT_Masonry`, `MAT_Trim` and `MAT_Rubble`; map `MAT_Rubble` → `MI_Kit_Rubble`.
   - Assert that every mesh named in a record exists in the reports.
   - Re-run every check with the real bounds.
3. **Cell-door leaves:** the C15 back panel's visible face is at local y −2. The leaf's back sits at y −3, 1 cm in front of it.
4. **Roof panels:** assert that each panel's local +z (the slate normal) has a world Z component > 0.5. Per P10-3b, the panel's local x must run −X (S walk), +X (N), +Y (W) and −Y (E) for that to hold. Fix the rotators if any panel fails.

**P10-4 spec** (technical-artist, [EDITOR]; commit "P10-4: …"):
1. **Import every FBX** (MCP_NOTES "Importing meshes (FBX)": the kit import settings, no auto collision, combine meshes):
   - `SourceArt/BellTower/*.fbx` → `/Game/LastBell/Environments/BellTower/Meshes/`;
   - `SourceArt/Cloister/*.fbx` → `/Game/LastBell/Environments/Cloister/Meshes/`.
   - Names exactly as the FBX.
   - **Simple collision:** only `SM_LB_Tw_BellFrame_A` (4 UCX boxes), `SM_LB_Prop_GreatBell_A` (1 hull) and `SM_LB_Prop_SmallBell_A` (1 hull). Read back the convex counts.
   - Every other mesh: no simple collision. Set the collision trace flag to default.
2. **Nanite** (D1.5):
   - **On:** every `SM_LB_Tw_*` and `SM_LB_Cl_*` (except the louvres), `SM_LB_Prop_GreatBell_A`, `SM_LB_Tw_BellFrame_A` and `SM_LB_Tw_BellHeadstock_A`.
   - **Off:** the louvres, the rope and the four Mech 3 props.
3. **New MIs** in `/Game/LastBell/Environments/BellTower/Materials/`, built exactly as D1.5 specifies:
   - `MI_LB_BellBronze`, `MI_LB_Rope` and `MI_LB_Sally`;
   - `MI_LB_BellBand_I..IV`.
   - Import the textures from `ExternalAssets/Incoming/ambientcg-Metal058B/` and `ambientcg-Rope003/` (2K JPG) into `/Game/LastBell/Environments/BellTower/Textures/` with the correct compression: normals as Normalmap, roughness/metalness as Masks, linear.
   - Read `M_LB_Surface`'s parameter names first (`MaterialInstanceTools`, full object paths). Set and read back every value.
4. **Slot assignment per mesh** (static-mesh material slots, so placed actors need no overrides), per the D1.5 mapping:
   - tower `MAT_Wood` → `MI_Chapel_Wood_Old`;
   - cloister roofs, stair-house roof, C15 back panel and M2 → `MI_Prop_Wood_Weathered`;
   - `MAT_Rubble` → `MI_Kit_Rubble`.
   - Read back every slot.
5. **Saves:** one package per `save_assets` call, and check `is_dirty` = false after each.
6. **Thumbnails:** generate them for the bell, small bell, roof, a wall piece and a vault. Write a short `Docs/ArtTest/belltower/p10_4_import_report.md` listing per mesh: path, Nanite, tris, slots → MIs, and collision.
7. **Suite:** 78/78. Imports cannot affect gameplay; run it anyway as the regression gate.
8. **Untouched:** no placement in any level (that is P10-5); no edits to `L_Monastery`.

### D1.13 P10-5 spec: structure placement (environment-designer, [EDITOR]; commits "P10-5: …")
**Inputs** (the P10-L generator, final at 0e621ec; never hand-edit):
- `Docs/plans/p10_d1_layout.json`, with keys `placements`, `hide_greybox`, `ground_materials` and `pieces`;
- `p10_d1_tables.md`.

**Placement script:** `Tools/belltower/place_tower.py`, adapted from `Tools/crypt/place_crypt.py`.
- **Options:** `--cats`, `--only`, `--check`, `--fix-collision`, plus:
  - `--hide-greybox` (set `bVisible=false` on every `hide_greybox` label's StaticMeshComponent; collision untouched);
  - `--verify-greybox` (read back `bVisible` and the collision profile, and run trace checks);
  - `--ground` (apply `ground_materials`).
- **Each record:**
  - spawn the mesh (or the engine cube for `cat: block`) with the record's label, folder, location, rotation and scale;
  - collision per the record:
    - `NoCollision`: set both `collisionProfileName` and `bodyInstance.collisionEnabled` (MCP_NOTES);
    - `BlockAll`;
    - `hidden-block`: BlockAll, then StaticMeshComponent visible = false;
  - material overrides **only** where the record's `mi_slots` differs from the mesh's own slot material set in P10-4 (e.g. floor slabs).
- **Skip** records with `extras.skip_place` (they are owned by the child BPs in P10-6b), `cat: dress` (P10-6a) and `cat: light` (P10-7).
- **`--check`:**
  - the world AABB is within 3 cm of `aabb_min/max`, using the P9 rule for off-axis rotations;
  - collision and materials match the record;
  - for `hidden-block`, the actor is not visible and its profile is BlockAll.

**Order:**
1. `--cats block`, then check.
2. `--hide-greybox`, then `--verify-greybox`.
   - Trace checks must still hit: a vertical trace on 3 steps (F01_05, F06_07, F11_13), landing 5, the core centre at Z 1200 (horizontal, from the W ring), the `Garth` top, one cloister wall and one passage wall.
3. `--ground`, and read back the 4 slab materials.
4. Structure categories, one category per run, then `--check` on each: `wall`, `tower`, `stair`, `arcade`, `vault`, `roof`, `floor`, `garth`, `door`, `doorleaf`.
5. **Save `L_Monastery` once after each step** (its own `save_assets` call; check `is_dirty` false). Commit after steps 2, 4-vaults and 4-end.

**Gap and look pass:**
- Captures: `Tools/crypt/capture_poses.py --raise`, poses in `Tools/belltower/poses/p10_5_poses.json`. Use PIE Simulate with a temporary 3000 lm shadowless light via `--light`, as in P9-5 (a PIE-only copy; never saved). Editor-mode captures are acceptable where PIE fails.
- **Spaces:**

  | Space | Views |
  |---|---|
  | Cloister | 4 corners looking along both walks and up into the groins; the 4 walk midpoints looking up (rib/wall/arcade junctions) |
  | Collapse bay | looking up |
  | Archways | the W archway from both sides; the S archway |
  | Stair-house | from the top of the crypt stair (10650, 0, −120) looking +Y |
  | Passage | both ends |
  | Tower | base inside the door; up the shaft from the W ring (12150, 2000, 170, pitch 70); landings 3, 6 and 9 looking along the next flight; the belfry from `WP_TowerStairs_24` (the bell is still the greybox cylinder until P10-6b) |
  | Exterior | tower from the gate (300, 0, 170) aimed at the tower; tower from the cloister NW corner |

- **Pass criteria:**
  - no greybox colour visible (white BasicShape, WorldGrid or checker) anywhere the art should be;
  - no black or sky slit wider than 2 cm at wall/vault/arcade/roof/stair junctions;
  - no z-fighting;
  - nothing floating;
  - on the S walk, no rafters or slates visible below or through the vault, and no gap between the arcade wall top and the eaves seen from the garth;
  - from the gate the belfry and the broken roof read against the sky.
- **Fixes:**
  - move or scale that record ±10 cm or ±2 %, but only by changing the generator (`gen_tower_layout.py`), re-running it (exit 0) and re-placing that record;
  - record every fix.
  - If a fix needs a mesh change, stop and report it (P10-3 owners).

**Tests:**
- `mirror_build_and_test.ps1` 78/78, with these named:
  - WalkPath.Monastery: TowerStairs and CryptToCloister PASS;
  - RouteBot.Monastery Success (cloister bells, Mech 3, doors, stairs, finale);
  - Warden.MonasteryReachability (the hidden blocks change the navmesh);
  - StagesRelocateTheWarden;
  - the Save tests.
- If any test fails, stop and report with the log lines. Do not "fix" gameplay.

**End state:**
- map saved and not dirty;
- no `TMP_` actors and no PIE proxies;
- throttle restored to true;
- the 9 dirty BPs from P10-2 never saved.
- Report the record counts placed per category, the check results, the captures (and what each shows) and the fixes made.

### D1.14 P10-5 review; cloister roof valleys; P10-5b / P10-5c specs (lead, 2026-10-30)
**P10-5 accepted in part** (4919443, 0244245, 692ad1b, 2e3a379):
- 222 records placed and every `--check` passes (worst bounds deviation 0.01 cm).
  - The 8 hidden blocks are BlockAll and invisible, and a trace across each one hits it.
  - All 280 greybox actors are hidden with their collision unchanged.
  - The 8 verify-greybox traces hit before hiding, after hiding and after all the art was placed.
- Suite 78/78, including WalkPath.Monastery (TowerStairs, CryptToCloister), RouteBot.Monastery, Warden.MonasteryReachability, StagesRelocateTheWarden and the Save tests.
- **Generator fix accepted:** the cell-door frame's `MAT_Rubble` slot maps to `MI_Prop_Wood_Weathered`, which matches P10-4.
- **Captures (8 of 44)** are clean except for the roofs:
  - the S and W walk barrel vaults with ribs;
  - the pointed arcade;
  - a cell door and its leaf;
  - the W archway into the passage;
  - the E arcade with the tower and the readable tablet behind it.

**Fail: the cloister roofs show through the vaults.**
- **Cause.** Each C14 run covers the full outer-wall length (X 9500–12000 or Y 540–3000). So every walk's roof continues through both corner squares, and its eaves strip (Z 640) crosses the neighbouring walk.
- **Lead numeric check:** rafter underside = plane − 15 / cos α, against the four-centred extrados (rise 340, R2 = span; a groin is the max of its two barrels, as in `build_groin`), on a 5 cm grid over all 10 bays. The lowest panel sits up to:
  - **258 cm** below the extrados where an eaves strip crosses a walk bay (the dark rafters in `mid_s_up_outer` and the "eave" across the far end of `cl_sw_along_s` / `cl_sw_along_w`);
  - **207 cm** below it in the groins (`cl_sw_groin`, `cl_ne_groin`).
- **Erratum to D1.3.** "At the corners the panels overlap and form the valleys" is wrong: two full planes do not make a valley, and the lower one stays visible from below.
- **The fix (D-082).** Over a corner the roof is a **valley**: the surface is the higher of the two walk planes, max(Z_a, Z_b).
  - Each walk's roof stops at the garth corners.
  - Two valley-cut triangular panels meet in each corner square along the valley line, from the garth eaves corner (Z 640) to the outer-wall corner (Z 1200).
- **Why it clears.**
  - Each walk plane clears its own barrel.
  - A groin's extrados is the max of the same two barrels.
  - So the valley roof clears every groin.
- **The same numeric check with the valley layout:**

  | Bay | Minimum clearance |
  |---|---|
  | SE groin | 7.2 cm |
  | S walk and SW groin | 9.3 cm |
  | NE groin | 17.2 cm |
  | N walk, W walk and NW groin | 18.3 cm |
  | E walk | 38.8 cm |

  No bay is negative.
- **Accepted consequence.** The N walk's hole panel must now end at the NE garth corner (X 11380).
  - Its hole covers X 10853–11287, which overlaps the broken vault's hole (X 10900–11450) by 387 cm.
  - The east 163 cm of the vault hole shows roof timbers from below, read as a partial roof collapse.
- **Also fixed in P10-5c:** `Ground_3` (X 10500–10800, Y −3600…−100) and `Ground_5` (X 7400–8000, Y −3600…−1300) still use `WorldGridMaterial` and can be seen from the belfry. Add both to `ground_materials` with `MI_Kit_Floor`.
- **Missing captures (36).** `CaptureViewport` timed out because the editor was covered by other windows (Claude, the floating Message Log) and minimised at the start (MCP_NOTES §6).
  - P10-5c captures all 44 poses again after the roof fix.
  - The owner keeps the Unreal Editor window visible and uncovered during that run.

**Roof layout** (replaces the D1.3 / D1.11 panel split):
- Same eaves and top lines, the same per-walk rotators (`rot_from_rows`, unchanged) and the same local frames as the current generator.
- The origin is on the walk's eaves line at Z 640, at run offset `off` from the run start `a` in the run direction:
  - S runs −X from 12000;
  - N runs +X from 9500;
  - W runs +Y from 540;
  - E runs −Y from 3000.
- **y-scale = Ls / 1050:**

  | Walk | y-scale | Ls (cm) |
  |---|---|---|
  | S | 0.993398 | 1043.07 |
  | N, W | 0.945690 | 992.97 |
  | E | 0.795682 | 835.46 |

| Label | Mesh | off | Width | x-scale | Origin (world) | Covers |
|---|---|---|---|---|---|---|
| `CLA_Roof_S_0` | `Valley_L` | 0 | 620 | 0.62 | (12000, 1420, 640) | SE corner, S side |
| `CLA_Roof_S_1` | `LeanTo` | 620 | 1060 | 1.06 | (11380, 1420, 640) | S walk X 11380 → 10320 |
| `CLA_Roof_S_2` | `Valley_R` | 1680 | 820 | 0.82 | (10320, 1420, 640) | SW corner, S side |
| `CLA_Roof_N_0` | `Valley_L` | 0 | 820 | 0.82 | (9500, 2180, 640) | NW corner, N side |
| `CLA_Roof_N_1` | `LeanTo` | 820 | 440 | 0.44 | (10320, 2180, 640) | N walk X 10320–10760 |
| `CLA_Roof_N_2` | `LeanTo_Hole` | 1260 | 620 | 0.62 | (10760, 2180, 640) | N walk X 10760–11380; hole X 10853–11287 |
| `CLA_Roof_N_3` | `Valley_R` | 1880 | 620 | 0.62 | (11380, 2180, 640) | NE corner, N side |
| `CLA_Roof_W_0` | `Valley_L` | 0 | 880 | 0.88 | (10320, 540, 640) | SW corner, W side |
| `CLA_Roof_W_1` | `LeanTo` | 880 | 760 | 0.76 | (10320, 1420, 640) | W walk Y 1420–2180 |
| `CLA_Roof_W_2` | `Valley_R` | 1640 | 820 | 0.82 | (10320, 2180, 640) | NW corner, W side |
| `CLA_Roof_E_0` | `Valley_L` | 0 | 820 | 0.82 | (11380, 3000, 640) | NE corner, E side |
| `CLA_Roof_E_1` | `LeanTo` | 820 | 760 | 0.76 | (11380, 2180, 640) | E walk Y 2180 → 1420 |
| `CLA_Roof_E_2` | `Valley_R` | 1580 | 880 | 0.88 | (11380, 1420, 640) | SE corner, E side |

- The widths add up to each run: S and N 2500, W and E 2460.
- In every corner, the `Valley_L` of one walk and the `Valley_R` of the other share both hypotenuse ends:
  - the garth corner (10320 or 11380, 1420 or 2180, 640);
  - the outer corner (9500 or 12000, 540 or 3000, 1200).
- In each corner square, the triangle kept is the one where its own plane is the higher one.
- All 12 old labels are in the new set, so `place_tower.py`'s `remove_existing` deletes them all. `CLA_Roof_N_3` is new.

**P10-5b spec** (technical-artist; Blender headless, then [EDITOR] for the import; commits "P10-5b: …"):
1. **C14V, two new pieces in `Tools/blender/belltower/build_cloister.py`** (seeds 1241 L and 1242 R):
   - Frame, layers and slots are exactly C14's:
     - the pivot is at the eaves-line start;
     - x 0..1000 along the eaves, y 0..1050 up the slope, z is the panel normal;
     - rafters 12 × 15 at 60 c/c (z −15..0), sarking 0..2.8, battens, and slates 2.8..8.8;
     - slots `["MAT_Slate", "MAT_Wood"]`.
   - **`SM_LB_Cl_LeanTo_Valley_L_1000x1050`** keeps the triangle (0, 1050)–(1000, 1050)–(1000, 0): the points with 1050·x + 1000·y ≥ 1 050 000. The eaves vertex is at (1000, 0).
   - **`SM_LB_Cl_LeanTo_Valley_R_1000x1050`** keeps the triangle (0, 0)–(0, 1050)–(1000, 1050): the points with 1000·y − 1050·x ≥ 0. The eaves vertex is at (0, 0).
   - **Method:**
     1. Build the full panel with `slate_panel(1000.0, 1050.0, seed)` (no hole, no snaps).
     2. `bmesh.ops.bisect_plane` with the vertical plane through the hypotenuse:
        - L: point (1000, 0, 0), normal ∝ (1050, 1000, 0);
        - R: point (0, 0, 0), normal ∝ (−1050, 1000, 0).
     3. Delete the geometry on the cut-away side.
     4. Cap the open cut loops with `bmesh.ops.holes_fill`. If some loops fail, report the count; open cut faces are acceptable because they lie inside the neighbouring triangle's slate layer.
   - **Valley rafter:** `MAT_Wood`, 12 wide × 15 deep (z −15..0), along the full hypotenuse. Its outer face lies on the cut line and its body is inside the kept triangle. The ends are cut square to the piece bounds, so it never pokes outside x 0..1000, y 0..1050.
   - **Bounds:** x 0..1000, y 0..1050, z −15..9 (±1). Nanite budget ≤ 30 000 tris each.
   - **`verify_cloister.py`:** add both pieces (bounds, slots, tris) and check:
     - every vertex has a signed distance to the hypotenuse ≥ −0.5 cm (nothing on the cut-away side);
     - L has a vertex within 2 cm of (1000, 0) and of (0, 1050); R has one within 2 cm of (0, 0) and of (1000, 1050).
2. **`render_cloister.py`:** switch the assembly's roofs to the 13-record table above (the old 3-panel loops at lines 317–334 go). Add two renders, and LOOK at them:
   - `cloister_sw_groin_up`: camera (9900, 1000, 170), pitch +80, looking up into the SW groin with walls, vaults and roofs. Pass: no timber or slate visible below or through the vault.
   - `cloister_roofs_top`: camera (12600, 0, 2600) aimed at (10850, 1800, 700). Pass: all four valleys read as clean diagonal creases, there is no gap or step along any valley, and the N-walk hole is visible.
   - Re-render `cloister_corner_walk` and `collapse_ne_bay_walk` and compare them with the P10-3b versions.
3. **Export** both FBX files to `SourceArt/Cloister/` and add both entries to `cloister_report.json`, with measured bounds, slots and tris.
4. **[EDITOR] Import** both into `/Game/LastBell/Environments/Cloister/Meshes/` with the P10-4 settings: combine meshes, no auto collision, collision trace flag default, Nanite on.
   - Slots: `MAT_Slate` → `MI_Kit_Slate`, `MAT_Wood` → `MI_Prop_Wood_Weathered`. Read every slot back.
   - Save one package per `save_assets` call, then check `is_dirty` is false.
   - Generate thumbnails.
   - Append both rows to `Docs/ArtTest/belltower/p10_4_import_report.md`.
5. **Untouched:** no placement, no level edits, no generator edits, and never save the 9 dirty P10-2 Blueprints.

**P10-5c spec** (environment-designer [EDITOR]; commits "P10-5c: …"):
1. **Generator** (`Tools/belltower/gen_tower_layout.py`):
   - **Pieces:** add `SM_LB_Cl_LeanTo_Valley_L_1000x1050` and `_R_` from `cloister_report.json` (mbounds, slots `["MAT_Slate", "MAT_Wood"]`, seeds 1241 / 1242).
   - **Roofs:** replace the three-equal-panel loop with the explicit 13-row table above. Keep `ROOF_WALKS`, the rotator code and the y-scale formula. Every record gets the extras:
     - `walk`, `eaves`, `top`, `slope_len`, `x_dir`, `y_dir`, `run_from`, `run_to`, `line_axis`;
     - `hole` (true only for `N_2`);
     - `valley`: "L", "R" or none.
   - **`ground_materials`:** add `Ground_3` and `Ground_5` → `MI_Kit_Floor`.
   - **Checks** (replace or add):
     - **Count:** 13 roof panels.
     - **Tiling:** the widths tile each run with no gap or overlap (S and N 2500, W and E 2460).
     - **Rectangles** stay out of the corner squares: S and N inside X 10320–11380; W and E inside Y 1420–2180.
     - **Corners on the lines:** the transformed corners of every rectangle lie on the eaves and top lines within 1 cm. For each triangle, its three vertices: the eaves vertex on the eaves line, and both top vertices on the top line.
     - **Valley lines:** in each corner the two triangles' hypotenuse ends coincide within 1 cm, at the garth corner (Z 640) and the outer corner (Z 1200).
     - **Roof vs vault:** on a 5 cm grid over every vault bay inside the walls (X 9500–12000, Y 540–3000):
       - the roof underside is the max over the covering panels of (plane Z − 15 / cos α);
       - it must be ≥ 5 cm above the vault extrados (four-centred, rise 340, R2 = span, as `build_cloister.four_centred`; groins are the max of their two barrels);
       - report the minimum per bay (expected about 7.2 cm in the SE groin).
     - **N hole:** the roof hole's X range overlaps the vault hole X 10900–11450 by ≥ 380 cm (expected 387). This replaces the old "covers" check.
   - **Re-run:** exit 0. The JSON diff may change only the roof records (12 → 13), `ground_materials` and the `pieces` entries.
2. **Place:**
   - `place_tower.py --cats roof`, then `--check` with 0 failures.
   - The folder `Cloister/Art/Roofs` must hold exactly the 13 new labels.
   - `--ground` (6 slabs), then read the 6 materials back.
   - Save `L_Monastery` (its own call) and check `is_dirty` is false. Commit.
3. **Captures:** all 44 poses of `Tools/belltower/poses/p10_5_poses.json` with `--force`, written to `Docs/ArtTest/belltower/p10_5c_*.png`.
   - **Before the run:**
     - close every floating editor window (Message Log, import dialogs) and un-minimise the editor;
     - set `bThrottleCPUWhenNotForeground` false in memory;
     - tell the lead the run is starting (the owner keeps the editor uncovered).
   - **Editor mode** for structure: `--editor --double --raise --timeout 4`. Helper icons are acceptable.
   - **PIE with `--light`** only for `cl_sw_along_s` and `cl_sw_along_w`, as in P10-5.
   - Follow the circuit-breaker rules in MCP_NOTES §6. A pose that still fails goes on the owner checklist; never fake it.
4. **Judge** every capture against the D1.13 pass criteria. Also check:
   - in every groin and walk-end view, no timber or slate below the vault;
   - from the garth, the four valleys and the eaves read cleanly;
   - from the gate and the cloister, the belfry and the broken tower roof read against the sky.
   - **Fixes** go only through the generator (±10 cm / ±2 %). Record every fix. If a mesh issue turns up, stop and report it.
5. **Suite** 78/78 with the D1.13 named tests. End state as D1.13; restore the throttle to true.

#### D1.14a Lead capture run and spec changes (2026-10-30)
**Lead capture run.** The 36 missing P10-5 poses were captured in editor mode (`--editor --double --raise --timeout 4 --settle 1.0`) as `p10_5_<pose>_ed.png`, so all 44 poses now exist.
- **How it worked:** `CaptureViewport` only succeeded once the owner put the editor in the foreground and minimised Claude, and even then only about one call in two.
- **What did not help:** with Claude maximised in front, every call reset after 19 s, even with `bThrottleCPUWhenNotForeground` false and the editor raised by `--raise`.
- `CaptureEditorImage` worked in 0.1 s in both cases.
- Lesson for MCP_NOTES (P10-8): viewport captures need the editor as the **foreground** window, so the owner sets that up for each capture run.

**Findings:**
- **Roofs.** The same roof intrusion shows in every corner and at every walk end: `cl_se_*`, `cl_ne_*`, `cl_nw_*`, `mid_*`, `collapse_up` and `collapse_along` (the E roof's eaves cross the broken N-E bay below the vault), and `ext_tower_from_cloister_nw`. All are fixed by D1.14.
- **Tower:**
  - the shaft looking up, landings 3, 6 and 9 and the base are clean: timber flights, rails, posts, slits and landings;
  - the belfry is clean: louvres, oak frame and balustrade. The bell is still the greybox cylinder until P10-6b.
  - From the gate, the tower reads above the chapel roofline with its louvred belfry and pyramid roof. The broken SW roof corner is too small to judge in an editor capture at that distance, so P10-7 judges it in its PIE captures.
- **Clean:** the passage (both ends), the stair-house (inside and out), the cell doors (the N-E one hangs askew as specified), the archways, and the garth with its cross and slabs.
- **`Perim_N` is white greybox.** It is the outer perimeter wall (X −3040…13440, Y 3600–3640, Z 0–800), visible in `ext_tower_from_north_of_cloister` (lead trace hits at Y 3600).
  - `Perim_E` (X 13400) and `Perim_S` (Y −3640) are probably also visible from the belfry louvres, the N/E stair slits and the SW collapse.
  - Fixed in P10-5c.
- **Close-up "double coursing" on the ashlar walls.** The world-aligned `MI_Kit_Masonry` texture courses do not line up with the modelled block joints. This is the established kit look (courtyard and cloister walls), and it is strongest under the bright greybox `Light_Tower_*` point lights that P10-7 deletes. No action.
- The garth earth (`MI_Prop_Earth`) reads very glossy under the editor lights. P10-6a covers most of it with vegetation; P10-7 judges what is left.

**Spec changes:**
1. **P10-5c additions:**
   - set the `StaticMeshComponent` override material, slot 0, to `MI_Kit_Masonry` (world-aligned) on `Perim_N`, `Perim_E`, `Perim_S` and `Perim_W`;
   - collision and visibility stay unchanged;
   - read back each material, plus the collision profile and `collisionEnabled`.
2. **P10-5c captures move to the lead** (step "P10-5d", lead with the owner). P10-5c does steps 1, 2 and 5 of D1.14, plus the Perim materials above, and **no captures**.
3. **P10-5d** (lead and owner, editor in the foreground with Claude minimised): with `--force`, re-capture every pose affected by the roofs or the perimeter as `p10_5d_<pose>_ed.png`:
   - every `cl_*`, `mid_*`, `garth_*`, `collapse_*`, `arch_*`, `cell_*`, `stairhouse_*` and `ext_*` pose;
   - three new belfry poses, added to `p10_5_poses.json` by P10-5c:

     | Pose | Location | Pitch | Yaw |
     |---|---|---|---|
     | `belfry_out_n` | (12500, 2400, 2670) | −20 | 90 |
     | `belfry_out_e` | (12900, 2000, 2670) | −20 | 0 |
     | `belfry_out_sw` | (12100, 1600, 2670) | −10 | −135 |

   - The lead judges these against the D1.13 criteria and D1.14 step 4.

### D1.15 P10-5b review; P10-5c details (lead, 2026-10-30)
**P10-5b accepted** (fda215d, 1b8d2f3):
- **Pieces:** `SM_LB_Cl_LeanTo_Valley_L/R_1000x1050`.
  - bounds 0,0,−15 .. 1000,1050,9.3;
  - 11 980 / 11 836 tris;
  - every cut loop capped (195 / 196 loops, 0 open edges).
- **Checks:**
  - `verify_cloister` 42/42;
  - the four valley lines coincide within 0.000 cm on Z 640 / 1200;
  - imported with Nanite on, no simple collision, `MI_Kit_Slate` / `MI_Prop_Wood_Weathered`, saved and not dirty.
- **Renders:**
  - `p10_5b_cloister_roofs_top`: four clean valley creases and the N-walk hole;
  - `p10_5b_cloister_sw_groin_up`: a clean groin; the magenta-roof probe counted 0 roof pixels;
  - `p10_5b_cloister_corner_walk`: the walk-end eaves strip is gone;
  - `p10_5b_collapse_ne_bay_walk`: sky plus the accepted roof timbers.
- **Accepted deviation:** the valley-rafter ends are clipped flush to the piece rectangle, so they cannot poke out at the eaves vertex.

**P10-5c details** (complete the D1.14 / D1.14a spec):
- **Perimeter materials.** The generator writes a new layout key `perimeter_materials`, the same format as `ground_materials`, mapping `Perim_N`, `Perim_E`, `Perim_S` and `Perim_W` to `/Game/LastBell/Environments/Kit/Materials/MI_Kit_Masonry` (world-aligned).
- **`place_tower.py --perim` (new option):**
  - finds each label with an exact label match (exactly one actor each);
  - sets `overrideMaterials` slot 0;
  - reads back the material, `bVisible`, `collisionProfileName` and `collisionEnabled`, which must be unchanged from before the edit.
- **Roof-vs-vault check.** Copy `_fc_solve`, `four_centred` (R2_target = span) and `FourCentred.z_at` from `build_cloister.py` into the generator as pure functions; `build_cloister.py` itself imports `bpy`.
  - Model: rafter underside = plane Z − 15 / cos α, roof = max over the covering panels; groin extrados = max of its two barrels.
  - The lead's reference run of this model: minimum 7.2 cm at the SE groin; 9.3 cm on the S walk and SW groin; 17.2 cm at the NE groin; 18.3 cm on the N walk, W walk and NW groin; 38.8 cm on the E walk.
