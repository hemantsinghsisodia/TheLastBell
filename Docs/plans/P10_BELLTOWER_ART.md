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

### D1.16 P10-5c / P10-5d review: structure pass complete (lead, 2026-10-30)
**P10-5c accepted** (291c4f5, 54b0326):
- **Generator:** 52/52 checks pass. The roof-vs-vault minimums match D1.15 exactly (SE groin 7.2 cm … E walk 38.8 cm), and the N-hole overlap is 387 cm.
- **Placement:** the roof `--check` is 15/15 with 0.00 cm deviation.
  - `Cloister/Art/Roofs` holds exactly the 13 new labels.
  - `Ground_1…6` all read `MI_Kit_Floor`.
  - `Perim_N/E/S/W` read `MI_Kit_Masonry`, with visibility and collision unchanged.
- **Map and traces:** the map is saved and not dirty; the 8 verify-greybox traces hit; the suite is 78/78.
- **Accepted:** `--cats roof` also respawned `SHA_Roof` and `TWA_Roof` (the same records, identical transforms, `--check` passes).

**P10-5d (lead with the owner, editor in the foreground)**
- **Run:** 35 roof- and perimeter-affected poses re-captured as `p10_5d_<pose>_ed.png`. The run needed two passes, because the circuit breaker tripped once while the editor was in the foreground.
- **Roofs pass:**
  - no timber or slate shows below or through any groin or walk vault (`cl_*_groin`, `mid_*`, `cl_*_along_*`, `ext_tower_from_cloister_nw`);
  - from the garth the eaves meet the arcade wall tops without a gap, and the valleys turn the corners (`garth_to_*`);
  - the broken N-E bay shows sky plus the accepted roof timbers (`collapse_up`, `collapse_along`).
- **Perimeter passes:** `Perim_N` reads as masonry (`ext_tower_from_north_of_cloister`).
- **Belfry poses:**
  - The three `belfry_out_*` poses (D1.14a) were badly specified by the lead: the cameras sat 40–60 cm from the walls, below the lancet sills (world Z 2700). They showed only wall, so those images were discarded.
  - In the belfry the player's eye (Z 2670) is below the sills, and the louvres slope outward-down, so the outside can be seen only through the broken SW corner. The perimeter walls are now masonry anyway.
  - The poses are replaced by one, `belfry_up_sw` (12500, 2150, 2670, pitch 25, yaw −135), for P10-7's PIE pass, which also judges the broken roof from the gate.
- **Result:** the P10-5 structure pass is complete. Next per D1.10: P10-6b (child BPs, D1.6), then P10-6a (dressing, D1.7), then P10-7 (lighting, D1.8).

### D1.17 P10-6b spec: child Blueprints and swaps (unreal-blueprint-engineer, [EDITOR]; commits "P10-6b: …")
This is the D1.6 design, made exact, plus the D1.11 errata. The P9 lessons apply: MCP_NOTES §5 (child-BP swaps), §10, §11 and §12 (saving).

**0. Rules for this task**
- **Parents:**
  - Never edit or save a parent Blueprint: `BP_SmallBell`, `BP_Inscription`, `BP_RitualMechanism`, `BP_Door_Base`, `BP_TagInteractable` and `BP_Inspectable_Note`.
  - `BP_SequencePuzzle`, `BP_TagTrigger` and `BP_EndingTrigger` are also off limits.
  - `read_graph_dsl` marks a Blueprint dirty in memory. That is expected; never save it.
- **Existing children:** `BP_Door_Base_Dungeon` and `BP_RitualMechanism_CryptWinch` are used as they are. Never edit them.
- **New children:** `/Game/LastBell/Blueprints/Puzzles/BP_SmallBell_Cloister`, `/Game/LastBell/Blueprints/Interactables/BP_Inscription_Cloister`, `/Game/LastBell/Blueprints/Interactables/BP_RitualMechanism_TowerCapstan` and `/Game/LastBell/Blueprints/Interactables/BP_TagInteractable_GreatBell`.
  - Each child's construction script first copies the parent's construction-script body; the DSL cannot call the parent's construction script. It then sets the art.
  - Compile each child with warnings as errors and read back that it compiles clean.
- **Materials.** After every `SetStaticMesh` in a child construction script, set **every** material slot explicitly with `SetMaterial(index, MI)`. Inherited component override materials, such as the parent's `MI_LB_Bronze` on `Bell`, would otherwise leak onto the new mesh. Slot MIs:

  | Slot | MI |
  |---|---|
  | MAT_Bronze | `MI_LB_BellBronze` |
  | MAT_Iron | `MI_Crypt_Iron` |
  | MAT_Wood (M2 bracket, capstan) | `MI_Prop_Wood_Weathered` |
  | MAT_Trim | `MI_Kit_Trim` |
  | MAT_Masonry | `MI_Kit_Masonry` |
  | MAT_Rubble | `MI_Kit_Rubble` |

  - Read each mesh's slot names with StaticMeshTools first; set the slots by index in that order.
  - The bell band slot (`MAT_Band`, index 2 of M1) takes the `BandMaterial` variable.
- **Swap procedure, per instance** (MCP_NOTES §5; D-051):
  1. Dump the old actor to `Docs/ArtTest/belltower/p10_6b/<label>_before.json`: class, label, folder, transform, every instance-editable variable, and every component (name, class, relative transform, mesh, materials, collision profile and enabled, visibility) including all `InteractComp`, `InspectableComp` and `SeqComp` properties.
  2. Spawn the child at the same transform (or the new transform where a step says so).
  3. Set the instance values listed in the step: copy them from the dump and read each one back.
  4. Delete the old actor, then apply the **same label** and **same folder**.
  5. Dump `<label>_after.json` and diff. Only the differences the step allows may appear; list every difference in the report.
  6. Write the dump/diff helper as a reusable script, `Tools/belltower/bp_swap.py` (`dump <label> <out.json>`, `diff <a> <b>`).
- **Copy rule.** Copy only the values each step lists, plus `InteractComp`, `InspectableComp` and the variables the parent's construction script reads.
  - **Never copy the old instance's component material overrides or meshes.** For example, `Door_Shortcut`'s planks material and `Bell`'s cylinder must not carry over.
- **Saving:** one package per `save_assets` call, then check `is_dirty` is false. Never save-all.
  - Save order: each new child BP, then `L_Monastery` last.
  - If any MCP call hangs over about 180 s, stop all editor calls and report.

**1. `BP_SmallBell_Cloister`** (parent `BP_SmallBell`; the instances have yaw 180, so local +x points into the walk and the wall plane is local x −17).
- **Before writing:**
  - read the parent's component tree and construction script;
  - confirm `Plate` and `Glyph` have a relative rotation whose front faces local +x;
  - confirm `Bell` is attached to `BellPivot`.
  If either is not so, stop and report.
- **New instance-editable variables:**
  - `BellScale` (float, default 1.0);
  - `BandMaterial` (MaterialInterface, default `MI_LB_BellBand_III`).
- **Construction script, after the copied parent body:**

  | Component | Mesh | Relative location | Rotation | Scale | Materials (slot order) | Collision | Visible |
  |---|---|---|---|---|---|---|---|
  | `Post` | `SM_LB_Prop_SmallBellBracket_A` (M2) | (−17, 0, 145) | 0 | 1 | Iron `MI_Crypt_Iron`, Wood `MI_Prop_Wood_Weathered` | NoCollision | yes |
  | `Arm` | unchanged | unchanged | — | — | — | NoCollision | **no** |
  | `BellPivot` | — | (8, 0, 140) | unchanged | — | — | — | — |
  | `Bell` | `SM_LB_Prop_SmallBell_A` (M1) | (0, 0, −2) relative to BellPivot | 0 | `BellScale` (uniform) | Bronze `MI_LB_BellBronze`, Iron `MI_Crypt_Iron`, Band = `BandMaterial` | unchanged (BlockAllDynamic; M1 has 1 hull) | yes |
  | `Clapper` | unchanged | unchanged | — | — | — | NoCollision | **no** |
  | `Plate` | `SM_LB_Prop_BellPlaque_A` (M3) | (−17, 0, 87) | 0 | 1 | Trim `MI_Kit_Trim` | NoCollision | yes |
  | `Glyph` | (TextRender) | (−12.8, 0, 87) | unchanged | — | — | — | yes |

  `Glyph` gets WorldSize 18 and TextRenderColor (26, 23, 20, 255).
- **Swaps:**
  - `Bell_1..4` keep their transforms and their `StruckTag`, `SymbolIndex`, `SwingDegrees`, `SwingDuration` and `InteractComp` values.
  - Per bell:

    | Bell | `BellScale` | `BandMaterial` |
    |---|---|---|
    | `Bell_1` | 1.30 | `MI_LB_BellBand_I` |
    | `Bell_2` | 1.15 | `MI_LB_BellBand_II` |
    | `Bell_3` | 1.00 | `MI_LB_BellBand_III` |
    | `Bell_4` | 0.85 | `MI_LB_BellBand_IV` |

  - Allowed diffs: class; the components and materials changed above; the two new variables.
- **Checks** (report the numbers):
  - each `Bell` component's world bounds, which should hang below Z ≈ 138, with Bell_1 the largest;
  - a trace from (11800, Y_bell, 160) to (12000, Y_bell, 120) hits that bell's `Bell` component or actor;
  - the four `Glyph` texts still read I, II, III, IV for `SymbolIndex` 0–3, as before.

**2. `BP_Inscription_Cloister`** (parent `BP_Inscription`).
- **Construction script, after the copied parent body:**
  - `Plaque` mesh `SM_LB_Prop_InscriptionTablet_A` (M4);
  - relative location **(−2, 0, 0)** (D1.11 erratum 3), rotation 0, scale 1, slot `MI_Kit_Trim`;
  - collision unchanged.
  - `Engraving` TextRenderColor (20, 18, 15, 255). Keep its relative location from the parent, then check that it sits in front of the tablet face, at actor-local x ≥ +2.1. If it does not, set its relative x to +2.2 and report.
- **Swap `Clue_Inscription`.** Keep the transform: (11995, 2380, 200), yaw 180, root scale 2.5. Keep `Text` = `STRIKE AS THE DEAD RECALL|III · I · IV · II`.
- **Check** the `Plaque` world bounds: X 11990–12000 (±1), Y 2230–2530, Z 162.5–237.5 (±1).

**3. `BP_RitualMechanism_TowerCapstan`** (parent `BP_RitualMechanism`).
- **Construction script.** Copy `BP_RitualMechanism_CryptWinch`'s construction script exactly, including the instance-editable `RequiredTags` variable that feeds `SetRequiredStateTags`. Then set the materials of `Pedestal` (`SM_LB_Crypt_Block_100_C`) and `Core` (`SM_LB_Crypt_CapstanDrum_80x50`, relative (0, 0, 75), scale 1) slot by slot with the table in §0. `CoreMarker` is hidden.
- **Swap `Mech_Ritual3`:**
  - keep `RitualTag` `State.Ritual.3`, `ExtraGrantedTags`, `TurnYaw`, `TurnDuration` and every `InteractComp` value;
  - set `RequiredTags` = {`State.Tower.BellsSolved`}.
  - **New transform: (11780, 1760, 50), yaw 0, scale 1** (D-081).
  - Allowed diffs: class, location X/Y, meshes, materials, `RequiredTags`.
- **Checks:**
  - read back the actor's world AABB;
  - the AABB's min X must be ≥ 11609 + 102 = 11711, the `Patrol_Cloister_04 → 05` clearance;
  - report the AABB, and the distance from its edge to the tower door leaf (Y 1950).

**4. Doors → `BP_Door_Base_Dungeon`** (existing child, unchanged).
- **`Door_Tower`:**
  - keep the location (12020, 1950, 0) and yaw 0;
  - **scale (1, 1, 1.036)**. The leaf apex reaches Z 228, the art opening's apex (D1.1: opening Y 1948–2052, jambs to Z 194, gabled head to Z 228).
- **`Door_Shortcut`:** keep the location (6020, 1941, 0), yaw 0 and scale (1, 1.18, 1.0818).
- **Copy:** `OpenStateTag`, `AutoOpenTag` (`State.Ritual.3`), `bInteractable` false, `OpenYaw`, `OpenDuration`, `OpenSign` and the `InteractComp` values. **Do not copy the old `DoorMesh` material override.**
- Allowed diffs: class, the door components and materials, and `Door_Tower`'s Z scale.

**5. `BP_TagInteractable_GreatBell`** (parent `BP_TagInteractable`).
- **Construction script, after the copied parent body:**
  - `Mesh` = `SM_LB_Prop_GreatBell_A` (T12), relative location (0, 0, 94), rotation 0, relative scale 0.4;
  - every slot set explicitly per its slot names (§0 table);
  - collision unchanged (T12 has 1 hull).
- **Swap `Bell`.** Keep the transform: (12420, 2000, 2625), yaw 0, root scale 2.5. Keep `UseStateTag` `State.Event.Finale`, `bHideOnUse`, `bInspectable` and every `InteractComp` / `InspectableComp` value.
- **Checks:**
  - world bounds ≈ X 12315–12525, Y 1895–2105, Z 2640–2860 (±5);
  - a trace from `WP_TowerStairs_24` eye (12165, 2000, 2660) to (12420, 2000, 2750) hits the bell.

**6. `Note_Cloister`.** Set the instance `BodyText`, exactly:

> The great bell rang again tonight, and no hand was on the rope. Brother Anselm says the four small bells beside the tower door still answer to the old order of the dead, and that the order is cut in the stone above them. Strike them as the dead recall, and the tower will open. I will not go up. God forgive whoever does.

- `DisplayName` stays "The Last Entry". Read both back, and dump before and after.

**7. Save, reload and re-dump, tests**
1. Save each new child BP, then `L_Monastery`, each in its own call; check `is_dirty` is false after each.
2. `load_level` `/Game/LastBell/Maps/L_Monastery`.
3. Re-dump the 10 swapped actors: `Bell_1..4`, `Clue_Inscription`, `Mech_Ritual3`, `Door_Tower`, `Door_Shortcut`, `Bell` and `Note_Cloister`. Diff them against the `_after` dumps; there must be **no** differences.
4. Run `Tools/mirror_build_and_test.ps1`: 78/78. Name in the report:
   - `RouteBot.Monastery` Success: it strikes the bells, turns the moved capstan, passes the tower door and rings the great bell;
   - `Puzzles.Blueprints`;
   - `WalkPath.Monastery`, including TowerStairs and CryptToCloister;
   - `Warden.MonasteryReachability` (the capstan moved, so the navmesh changes);
   - `Warden.Monastery.StagesRelocateTheWarden`;
   - the Save tests.
5. If anything fails, stop and report with the log lines; do not change gameplay.

**8. Poses for the lead's capture pass (P10-6c, with the owner; P10-6b takes no captures).** Write `Tools/belltower/poses/p10_6_poses.json` with these entries, `[x, y, z, pitch, yaw]`:

| Pose | Value |
|---|---|
| `m3_bells_2m` | [11800, 2380, 160, −5, 0] |
| `m3_bells_close` | [11850, 2250, 150, −10, 20] |
| `m3_inscription_2m` | [11800, 2380, 170, 5, 0] |
| `m3_capstan` | [11500, 1650, 170, −15, 21] |
| `m3_capstan_door` | [11400, 1950, 170, −5, 0] |
| `door_tower_out` | [11700, 2000, 170, 0, 0] |
| `door_tower_in` | [12200, 2000, 170, 0, 180] |
| `door_shortcut_court` | [5600, 2000, 170, 0, 0] |
| `door_shortcut_pass` | [6400, 2000, 170, 0, 180] |
| `greatbell_from_stairs` | [12165, 2000, 2660, 10, 0] |
| `greatbell_corner` | [12850, 1650, 2670, 15, 141] |
| `note_cloister` | [10750, 1600, 220, −34, −90] |

**End state:**
- map saved and not dirty;
- PIE stopped;
- no `TMP_` actors;
- the throttle untouched;
- no parent Blueprint saved;
- `git status` shows only the task's files (never stage `L_Throwaway_P9_4.umap`).

### D1.18 P10-6b review and decisions (lead, 2026-10-31)
**Accepted** (1ac66e2, b1be7c0, 30da957):
- **Child Blueprints:** four children, compiled clean and saved.
- **Swaps:** `Bell_1..4`, `Clue_Inscription`, `Mech_Ritual3`, `Door_Tower` (Z scale 1.036) and `Door_Shortcut`, each with only allowed diffs, plus the `Note_Cloister` text. The reload re-dump showed 0 differences.
- **Checks:**
  - bell bounds: Bell_1 is the largest, bodies hang below Z 138, and the eye traces hit;
  - the Plaque is exactly X 11990–12000 × Y 2230–2530 × Z 162.5–237.5;
  - Engraving x is 2.2.
- **Also accepted:**
  - `Clue_Inscription` Engraving WorldSize 7 (the instance value is kept; 10 would overflow the tablet);
  - capstan `MAT_Stone` → `MI_Kit_Masonry`;
  - the capstan child made by duplicating `BP_RitualMechanism_CryptWinch`, with its CDO tags reset.

**Decision 1: the great bell (Known Issue 1).** In `BP_TagInteractable`, `Mesh` is the **root** component, so D1.6/D1.17 §5's "relative (0, 0, 94), scale 0.4 under a 2.5 root" cannot apply.
- Swap `Bell` to `BP_TagInteractable_GreatBell` at **(12420, 2000, 2860), yaw 0, scale 1**. The T12 pivot is the crown top, so the bell occupies X 12315–12525, Y 1895–2105, Z 2640–2860.
- Allowed diffs: class, location Z, actor scale, mesh, materials.
- Checks as in D1.17 §5.

**Decision 2: the capstan (Known Issue 2, `RouteBot.Monastery` red).**
- **What happened:**
  - The RouteBot uses the target's forward direction as its first approach. The capstan has yaw 0, so the bot stood east at (11955, 1760).
  - `TickCheckpoints` then needs a clear line from that spot to `CP_TowerBase` (12200, 2000). That line hits the tower W wall at Y 1804, outside the doorway (Y 1948–2052).
  - So the checkpoint was skipped and the restore assertions failed.
- **This is a placement and bot-heuristic mismatch, not a gameplay bug.** The test code stays unchanged.
- **New `Mech_Ritual3` transform: (11790, 1780, 50), yaw 90.** This amends D-081's (11780, 1760).
  - The bot's front approach is then north at (11790, 1955).
  - Its line to the checkpoint crosses X 11920 at Y 1969, which clears the open leaf by about 13 cm (the leaf lies along X 11920–12020 at Y 1943–1957). It crosses X 12000–12040 at Y 1978–1982, inside the doorway.
  - The footprint (X 11735–11845, Y 1725–1835) stays about 112 cm from the `Patrol_Cloister_04 → 05` segment (≥ 102).
- **Generator:**
  - `MECH3_LOC` = (11790, 1780, 50);
  - `mech_ritual3_target` yaw 90;
  - the check text uses the constant;
  - the D1.7 chain start moves from the drum at (11810, 1760, 110) to (11820, 1780, 110).
  - Re-run: exit 0, with the Mech 3 lane check passing.

### D1.19 P10-6c capture review and P10-6d (lead, 2026-10-31)
**Capture run.** The lead captured all 12 `p10_6_poses.json` views in editor mode, with the editor in the foreground (`--editor --double --raise --timeout 4 --settle 1.5`).
- Output: `Docs/ArtTest/belltower/p10_6c_<pose>_ed.png`; 12 saved, 0 missing. The throttle was restored to true afterwards.
- Editor sprites, arrows and trigger outlines in the images exist only in the editor.
- The lighting is still the greybox set (`Light_Tower_*` and the courtyard lights), which P10-7 replaces.

**Verdicts (against D1.6 and D1.17):**

| Item | Pose(s) | Verdict |
|---|---|---|
| Small bells | `m3_bells_2m`, `m3_bells_close` | **Pass.** `Bell_1` is clearly the largest and the sizes step down. The bands read red, ochre, teal and pale. The plaque numerals I–IV are legible at 2 m. The bronze reads dark and warm, with patina. |
| Inscription | `m3_inscription_2m` | **Pass.** Both lines ("STRIKE AS THE DEAD RECALL", "III · I · IV · II") are legible at 2 m. The letters read as a dark inlay rather than cut stone, which is accepted. The white specks on the tablet frame are `MI_Kit_Masonry` highlights under the close greybox light; P10-7 re-judges them. |
| Capstan | `m3_capstan`, `m3_capstan_door` | **Pass as specified** (D1.4: the crypt capstan drum on the stone pedestal). It reads as a winch. The link to the tower door comes from P10-6a's chain and latch box, so P10-6a's `m3_capstan_door` capture re-judges whether it reads as the door mechanism. |
| `Door_Tower` | `door_tower_out`, `door_tower_in` | **Pass.** The leaf fills the gabled opening, and the jamb gaps are D1.1's 2 cm. Above Z ≈ 208, three slits about 1–2 cm wide between the plank tips show the over-bright greybox interior. That is at the limit; P10-7 re-judges it under the final lights. |
| `Door_Shortcut` | `door_shortcut_court`, `door_shortcut_pass` | **Fail.** There are two light wedges, each about 20 cm wide × 30 cm tall, between the leaf's top corners (Z ≈ 205) and the bottom of `KW_ShortcutTympanum` (Z 240). They show from both the courtyard and the passage. |
| Great bell | `greatbell_from_stairs`, `greatbell_corner` | **Pass for form.** The enormous cracked bell hangs in the oak frame with its wheel and rope. Under the close greybox point light in `greatbell_from_stairs`, the bronze reads pink-copper, which misses D1.5's target. P10-7's bronze tuning, already in its scope, re-judges it under the final lights. |
| `Note_Cloister` | `note_cloister` | **Pass.** The note reads as paper lying on the garth kerb. |

**Why `Door_Shortcut` leaks.**
- **The leaf:** `SM_Dungeon_door` has a stepped, pointed top. In the leaf's local frame (before the actor scale), its corners stop at Z ≈ 189.5 and the apex is at Z 220.
  - The P7 leaf was a box 238 tall, so it met the tympanum (bottom at Z 240) square.
  - At D1.17's actor scale Z 1.0818, the Dungeon leaf's corners stop at Z ≈ 205, which leaves two triangles under the tympanum.
  - The light shows through the triangles from both sides (measured on `p10_6c_door_shortcut_court/pass_ed.png`).
- **The opening** is the kit `Doorway_Pointed_400x60x400`:
  - clear Y 1940–2060, jambs to Z 240;
  - a two-centred arch (R 120) to an apex at Z ≈ 344;
  - an outer order 10 cm wider (span 140) over X 6000–6012.5;
  - the tympanum, a cube with `MI_Weathered_Planks_WA`, at X 6034–6046, Y 1940–2060, Z 240–340, filling the head behind the leaf.
- The leaf lies at X 6013.3–6026.7, Y 1941–2059.

**Decision: P10-6d raises the `Door_Shortcut` leaf.** The actor scale changes from (1, 1.18, 1.0818) to **(1, 1.18, 1.30)**. The location (6020, 1941, 0) and yaw 0 stay. This amends D1.17 §4.
- **Fit:** the leaf corners rise to Z ≈ 246, at least 6 cm above the tympanum's bottom, and the apex rises to Z 286. The leaf stays inside the arch:

  | Y | Arch soffit Z | Leaf top Z |
  |---|---|---|
  | 1941 | ≈ 255 | ≈ 246 |
  | 1950 | ≈ 288 | ≈ 259 |
  | 1967 | ≈ 316 | ≈ 281 |
  | 2000 | ≈ 344 | 286 |

  The Y 2059 side mirrors Y 1941.
- **No light:**
  - Everything of the leaf above Z 240 lies in front of the tympanum. That includes any slits between the plank tips, which only open above the backing's top at Z ≈ 244.
  - Below Z 240, the leaf's `backing` plane (local Z 2–188, world Z up to ≈ 244) closes the plank gaps.
- **Swing unchanged:**
  - The leaf turns toward the courtyard (−X), about the hinge at (6020, 1941).
  - Its top passes through the outer order (clear to Z ≈ 294 at Y 1941) and out past the wall face at X 6000.
- **Warden and navmesh unchanged:**
  - The clear head under the tympanum stays 240.
  - So the Warden's route through the passage is unchanged (D-038: agent 42/220, visual 2.9 m stooping), and so is the navmesh.
- **Texture stretch:** the leaf texture's vertical stretch, relative to its width, rises from 6 % to 27.5 %. The tower door is at 20 %. Accepted.
- **Rejected:**
  - lowering the tympanum or adding a lintel: a 196 cm head would clip the Warden, and collision there would change the navmesh;
  - a custom pointed leaf: its head would cut into the arch as it swings.

**P10-6d is done by the P10-6a implementer as its step 0, before any dressing.** It is a separate commit. It shares P10-6a's final suite run.
1. **Before you start.** Read `Tools/mcp/MCP_NOTES.md`. Confirm that `/Game/LastBell/Maps/L_Monastery` is loaded, PIE is stopped and the map is not dirty.
2. **Before dump.** Dump `Door_Shortcut` with `Tools/belltower/bp_swap.py` to `Docs/ArtTest/belltower/p10_6d/Door_Shortcut_before.json`.
   - Check that the transform is (6020, 1941, 0), yaw 0, scale (1, 1.18, 1.0818).
   - If it is not, stop and report.
3. **Set the transform.** Call `set_actor_transform` on `Door_Shortcut` with location (6020, 1941, 0), rotation (0, 0, 0) and scale (1, 1.18, 1.30). Pass all three. Read the transform back.
4. **After dump and diff.** Dump to `Door_Shortcut_after.json` and diff it against `_before`.
   - The only allowed difference is `transform.scale.z`, 1.0818 → 1.3.
   - Anything else: stop and report.
5. **Save.** Save `L_Monastery` in one `save_assets` call that contains only that package. Check that `is_dirty` is false.
   - Never save `BP_Door_Base_Dungeon` or any parent Blueprint.
6. **Reload check.** Run `load_level` on `L_Monastery`, dump to `Door_Shortcut_reload.json` and diff against `_after`. There must be 0 differences.
7. **Script.** In `Tools/belltower/p10_6b_swap.py`, line 139, set `Door_Shortcut`'s scale to `{"x": 1, "y": 1.18, "z": 1.30}` and add the comment `# P10-6d (D1.19)`, so that a re-run reproduces the map.
8. **Commit** on `claude/phase-10-belltower` only:
   - stage the three dumps, `p10_6b_swap.py` and `L_Monastery.umap`;
   - never stage `L_Throwaway_P9_4.umap`;
   - message `P10-6d: Door_Shortcut leaf Z scale 1.0818 -> 1.30 (D1.19)`, with the trailer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- **Tests:** P10-6a's final suite covers this step (78/78, including `WalkPath.Monastery`'s CourtyardShortcut path). If that suite fails, the report states which tests failed so the lead can tell the two changes apart.
- **No captures in P10-6d.** The lead re-captures `door_shortcut_court` and `door_shortcut_pass` with `--force`, as `p10_6d_<pose>_ed.png`, in the owner capture session that follows P10-6a.
  - Pass: seen from either side, no light wedge or slit above 2 cm between the leaf and the tympanum or the jambs.
- **Owner check in the P10-8 playtest:** after Ritual 3 the shortcut door swings open without visibly cutting into the arch, and the passage can be walked both ways.

**Note outside Phase 10:**
- `Door_ChapelMain` (P8) and `Door_Sacristy` (P9) use the same Dungeon leaf at the same scale Z 1.0818.
- The P8 capture `Docs/ArtTest/chapel/r2b2_door_chapelmain_outside_W.png` shows small dark notches at the leaf's top corners under the head.
- They were accepted in their phases and are not judged here. Re-checking them needs the owner's approval as a separate fix set.

### D1.20 P10-6a spec: dressing (environment-designer, [EDITOR]; commits "P10-6a: …"), with P10-6d as step 0 (lead, 2026-10-31)
The generator (P10-L) already holds the D1.7 dressing as 150 `dress` records in `Docs/plans/p10_d1_layout.json`. P10-6a corrects four things in the generator, teaches `place_tower.py` to place `dress` (including DecalActors), places everything, checks it, saves, runs the suite and writes the capture poses.

**Lead findings that drive the corrections:**
- **Chain start inside the pedestal.**
  - `CLA_Mech3_Chain_A` starts at (11820, 1780, 110) (D1.18). That point is inside `Mech_Ritual3`'s stone pedestal (Z 50–150).
  - The drum (`SM_LB_Crypt_CapstanDrum_80x50`: centre pivot, body r 34, iron bands at local z ±17…21, bars at local z 10.5…15.5) sits at world Z 150–200 around (11790, 1780).
- **Invisible vegetation at scale 1.** These sizes come from live `StaticMeshTools.get_bounds`, read 2026-10-31:

  | Mesh | Height at scale 1 |
  |---|---|
  | `SM_LB_CC0_WeedPlant02_*` | 3.9–7.2 cm |
  | `SM_LB_CC0_NettlePlant_*` | 2.2–19.3 cm |
  | `SM_LB_CC0_GrassMedium02_*` | 15.7–40.3 cm |

  This is the P7-FIX3 lesson ("plants are invisible by size"); the courtyard uses weeds ×5 and nettles ×4. The garth is meant to be overgrown (D-077), yet 60 plants with 50 cm clearances leave it mostly bare.
- **Estimated bounds that would fail the 3 cm bounds check:**

  | Mesh | Estimate | Live |
  |---|---|---|
  | `SM_LB_Prop_SlateShards_A` | z 8 | z 21.2 |
  | `SM_LB_Prop_Ivy_Creep_400x200_Dead` | y 25 | y 20.5 |
  | `SM_LB_CC0_GrassMedium02_*` | 50 × 50 × 35 | see the table in step 1 |

**Step 0: P10-6d** (D1.19, steps 1–8 there): the `Door_Shortcut` scale Z goes from 1.0818 to 1.30, with its own commit. Do it before anything else.

**Step 1: generator corrections (no editor).** All edits are in `Tools/belltower/gen_tower_layout.py`. Never hand-edit the JSON or the tables.
1. **Chain start** (the `chain_run("CLA_Mech3_Chain_A", …)` call, line ≈ 793):
   - Change the start to **(11824.0, 1783.0, 168.0)**.
   - Comment: `# D1.20: on the drum surface (r 34, facing the eyelet), between the lower iron band (Z 154-158) and the capstan bars (Z 185-190); the D1.18 start was inside the pedestal (Z 50-150)`.
   - Grep the file for `11820` and update every other use of the old start the same way (check text, notes, the MD tables).
   - Why this point: it is (11790, 1780) + 34 × the unit vector toward the eyelet (11995, 1800) = (11823.8, 1783.3).
   - The run toward the eyelet then crosses the pedestal's east face (X 11840) at Z ≈ 165, which is 15 above the pedestal top.
2. **Real bounds** (pass `mb=` and drop `est=True`):
   - `GRASS`: per mesh, `((-6.0, -6.0, 0.0), (6.0, 6.0, 15.7))`, `((-9.0, -10.0, 0.0), (9.0, 10.0, 18.0))`, `((-13.1, -12.5, 0.0), (13.1, 12.5, 23.2))`, `((-15.9, -18.1, 0.0), (15.9, 18.1, 26.0))`, `((-17.8, -21.7, 0.0), (17.8, 21.7, 40.3))` for `_01` … `_05`;
   - `IVY_C`: `((-200.0, 0.0, 0.0), (200.0, 20.5, 200.0))`;
   - `SLATES`: `((-60.0, -45.0, 0.0), (60.0, 45.0, 21.2))`;
   - `COBWEB`: keep its bounds and drop `est=True`.
3. **Passage weeds** (the `# ---- passage weeds` block):
   - count 20 → **32**;
   - per weed, draw in this order from `wrng`: `x = uniform(6120, 9400)`, `d = uniform(20.0, 35.0)`, `s = round(uniform(3.5, 5.0), 3)`, `yaw = uniform(0, 360)`;
   - scale `(s, s, s)`;
   - the mesh still cycles `_01` … `_05`, the side still alternates S/N, and the note includes `scale {s}`;
   - comment: `# D1.20: WeedPlant02 is 4-7 cm tall at scale 1; x3.5-5 as the P7-FIX3 courtyard ("Weed x5")`.
4. **Garth vegetation** (the `# ---- garth vegetation` block):
   - **Counts:** Grass **90**, Nettle **30**, Fern **20**.
   - **`NETTLE` pool:** `_01`, `_02`, `_03`, `_06`. Drop `_04` (2.2 cm tall); `_05` is not used.
   - **Scale:** right after picking the mesh, draw `s = round(grng.uniform(lo, hi), 3)`. Ranges: Grass 0.9–1.4, Nettle 2.8–4.4, Fern 0.8–1.1. Use `rad = 0.5 * max(footprint x, footprint y) * s`, and pass the scale `(s, s, s)` to `add()`.
   - **Clearances (edge to edge, minus `rad`):** the cross base ≥ **20** (was 50), the grave slabs ≥ **15** (was 50), the small crosses ≥ **15** (was 50), `Note_Cloister` ≥ **70** (unchanged).
   - **Tries:** 400 → **600** per plant. If a plant still finds no spot, the generator fails, as it does now: report it, do not loosen anything else.
   - **Text:** the note reads `garth vegetation (seed 1224), scale {s}`. Update the MD text (line ≈ 1859) to the new counts and clearances.
   - Comment: `# D1.20: visible and overgrown (P7-FIX3 lesson): nettles x2.8-4.4, grass up to 1.4, growth up to the slabs`.
5. **Latch box clear of the open tower door.**
   - When open, `Door_Tower`'s leaf lies along X 11920–12020 at Y 1943.3–1956.7 (D1.18). The latch box (Y 1925–1945, X 11991–11999, Z 105–135) would intersect it by 2 cm.
   - Move `CLA_Mech3_LatchBox` to **(11995.0, 1925.0, 120.0)**, so it spans Y 1915–1935.
   - Move the `CLA_Mech3_Chain_B` run end from (11995, 1935, 120) to **(11995.0, 1925.0, 120.0)**.
   - Comment: `# D1.20: 8 cm clear of the open Door_Tower leaf (Y >= 1943.3)`.
6. **Re-run** `python Tools/belltower/gen_tower_layout.py`.
   - It must exit 0 with every check passing.
   - Report the new `dress` count (expected 150 − 20 − 60 + 32 + 140 = **242**), the five lane worst cases and every check that changed.
   - Commit the generator and all of its outputs (`p10_d1_layout.json`, `p10_d1_tables.md`, `d1_layout_plan.png`): `P10-6a: generator - chain on the drum, real bounds, visible vegetation (D1.20)`.

**Step 2: `place_tower.py` places `dress`.**
1. Add `dress` to the allowed categories (append it to `ORDER`). Update the docstring: `dress` is placed by P10-6a; `light` stays P10-7.
2. **Decals:** a record whose `mesh` is `"Point"` and that has `extras.decal`.
   - Port `place_decal` and `verify_decal` from `Tools/crypt/place_crypt.py` (lines ≈ 219–265), with these changes:
     - resolve the MI from `layout["mi_paths"][mi]` (path + `.` + name) instead of searching folders;
     - use the record's rotation exactly as given (no yaw add);
     - leave the scale at 1.
   - Set `NewDecalComponent.decalMaterial` and `decalSize` = `extras.decal.size` (x = depth half, y = vertical half, z = horizontal half; P9 convention).
   - **Verify:**
     - the material name and `decalSize` (±0.01);
     - the location (±0.1) and rotation (±0.1°);
     - **orientation, by numbers:** the actor's forward vector (from its rotator) must point into its wall (`extras.decal.wall`: S (0, −1, 0), N (0, 1, 0), W (−1, 0, 0), E (1, 0, 0)), with a dot product ≥ 0.999;
     - **wall inside the box:** a `trace_world` from the decal centre − 30 × forward to the centre + 30 × forward must hit at a distance of 18–42 cm, so the wall face lies within ±12 of the decal centre.
   - Print one row per decal.
3. **Mesh records:** use the existing `place_one` and `verify` unchanged (one full transform call, label, folder, collision, material overrides, bounds TOL 3 cm, superset rule off-axis). The latch box (engine `Cube`) gets `MI_Crypt_Iron` on slot 0 through `expected_materials`.
   - A record that still carries `mbounds_estimated` (there should be none after step 1) is reported with its measured bounds instead of failing.
4. `--check` and `--only` work for `dress` like the other categories.
5. Commit: `P10-6a: place_tower places dress + DecalActors (D1.20)`.

**Step 3: place.**
1. Confirm `L_Monastery` is loaded, PIE is stopped and the map is not dirty.
2. Run `python Tools/belltower/place_tower.py --cats dress`, then `--cats dress --check`.
   - Every record passes.
   - `CLA_Collapse_Heap` is BlockAll with the mesh's own collision, read back.
   - Every other mesh record is NoCollision with `collisionEnabled` NoCollision, read back.
   - All 8 decals pass the step 2 checks.
3. If a group fails, fix the cause and re-run with `--only <prefix>`; the script is idempotent.
4. Do not move, change or save any gameplay actor or Blueprint.

**Step 4: numeric checks.** Write the read-only script `Tools/belltower/p10_6a_checks.py`, which prints PASS/FAIL per line:
1. **Chain on the drum.**
   - `CLA_Mech3_Chain_A_0`'s `extras.run_from` must satisfy 150 ≤ Z ≤ 200, with its XY distance from (11790, 1780) between 30 and 38.
   - `Mech_Ritual3`'s actor bounds must still be X 11735–11845, Y 1725–1835 (±1).
2. **Collapse heap:** world bounds within 3 cm of X 11050–11370, Y 2295–2505, Z 0–65, collision BlockAll / QueryAndPhysics.
3. **Vegetation read-back:**
   - per folder, the count of `CLA_GarthGrass_*` (90), `CLA_GarthNettle_*` (30), `CLA_GarthFern_*` (20) and `PSA_Weed_*` (32);
   - each actor's scale equals its record (±0.001);
   - the min and max world-bounds height per group (expected roughly: weeds 14–36, nettles 17–85, grass 14–56, ferns 17–47).
4. **No dress on the gameplay actors.**
   - No dress actor's world bounds may intersect the bounds of these actors, each grown by 10 cm: `Mech_Ritual3`, `Bell_1..4`, `Clue_Inscription`, `Note_Cloister`, `Bell`.
     - Exception: `CLA_Mech3_Chain_A_0` may touch `Mech_Ritual3`.
     - Use the component-level bounds that `p10_6b_checks.py` explains wherever the actor-level bounds include editor sprites; `get_actor_bounds` is fine for dress meshes.
   - **The doors' swing boxes, Z 0–300.** These boxes bound the swept quarter-disc plus the leaf thickness. No dress actor may intersect them:

     | Door | Hinge, swing direction | Swing box |
     |---|---|---|
     | `Door_Tower` | (12020, 1950), opens toward −X | X 11913–12027, Y 1943–2057 |
     | `Door_Shortcut` | (6020, 1941), opens toward −X | X 5895–6027, Y 1934–2066 |

   - Report every hit, with the two boxes' coordinates.

**Step 5: save, reload, re-check.**
1. Save `L_Monastery` in one `save_assets` call containing only that package, and check that `is_dirty` is false.
2. Run `load_level` on `/Game/LastBell/Maps/L_Monastery`, then `place_tower.py --cats dress --check` and `p10_6a_checks.py` again. Everything must pass.

**Step 6: tests.**
- Run the full suite with the command-line runner (`Tools/mcp/MCP_NOTES.md` line ≈ 66): **78/78**, including:
  - `WalkPath.Monastery`: TowerStairs, CryptToCloister and the four Courtyard paths;
  - `RouteBot.Monastery` Success;
  - `Puzzles.Blueprints`;
  - `Warden.MonasteryReachability` (the BlockAll heap changes the navmesh);
  - `Warden.Monastery.StagesRelocateTheWarden`;
  - the Save tests.
- If anything fails:
  - stop and report the log lines;
  - say whether the failure could come from P10-6d (the door scale) or from the dressing;
  - do not change gameplay.

**Step 7: capture poses** (no captures in P10-6a). Write `Tools/belltower/poses/p10_6a_poses.json`, values `[x, y, z, pitch, yaw]`:

| Pose | Value | Shows |
|---|---|---|
| `dress_collapse_along` | [10500, 2650, 170, −10, −19] | heap, chunks and rafter from the N walk |
| `dress_collapse_close` | [10900, 2750, 170, −17, −49] | the heap close |
| `dress_garth_from_s` | [10750, 1100, 200, −8, 85] | the garth vegetation through the S arcade |
| `dress_garth_from_e` | [11700, 1800, 200, −7, 180] | the garth from the E walk |
| `dress_garth_high` | [11300, 2150, 450, −32, −142] | the garth from above |
| `dress_note` | [10750, 1600, 220, −34, −90] | the note still reads among the plants |
| `dress_ivy_s` | [10900, 1900, 170, 25, −90] | ivy on the S arcade wall (garth face) |
| `dress_cells_w` | [9800, 2700, 170, −25, 180] | stool and bucket at the W cell door |
| `dress_passage_east` | [6300, 2000, 170, −12, 0] | passage weeds |
| `dress_passage_west` | [9300, 2000, 170, −12, 180] | passage weeds and lantern |
| `dress_mech3_chain` | [11650, 2050, 190, −7, −45] | capstan, chain and eyelet |
| `dress_mech3_latch` | [11850, 1960, 170, −13, −32] | eyelet, the chain along the wall, latch box |
| `dress_lantern_bells` | [11700, 2380, 200, 9, 0] | lantern above the inscription |
| `dress_tower_coil` | [12160, 2150, 700, −49, −46] | rope coil on the shaft-base rim |
| `dress_tower_lantern` | [12250, 2100, 190, 8, −131] | base lantern by the tower door |
| `dress_land10_slates` | [12700, 1700, 2433, −41, −31] | slates on landing 10 |
| `dress_cobweb_l5` | [12650, 2150, 1300, 18, 45] | cobweb in the NE corner above landing 5 |
| `dress_belfry_debris` | [12300, 2300, 2670, −33, 175] | debris on the belfry W slab |
| `dress_decal_s` | [10100, 1000, 150, −6, −90] | mould decal on the S wall |
| `dress_decal_e` | [11600, 800, 150, −7, 0] | mould decal on the E wall |

**Step 8: commit.**
- Message: `P10-6a: dressing placed (242 dress actors incl. 8 decals), checks, suite 78/78`.
- Include `L_Monastery.umap`, `p10_6a_checks.py` and its output saved as `Docs/ArtTest/belltower/p10_6a_checks.txt`, and the poses.
- Never stage `L_Throwaway_P9_4.umap`.

**End state:**
- the map is saved and not dirty;
- PIE is stopped;
- there are no `TMP_` actors;
- the throttle is untouched;
- no parent Blueprint was saved;
- `git status` shows only the untracked throwaway map.

**Lead review after P10-6a:** the lead and the owner run one capture session.
- `p10_6a_poses.json` (20 poses), prefix `p10_6a_`.
- The two D1.19 door poses (`door_shortcut_court`, `door_shortcut_pass` from `p10_6_poses.json`), prefix `p10_6d_`, with `--force`.

### D1.21 P10-6a / P10-6d capture review; P10-6e fix spec (lead, 2026-10-31)
**Accepted** (6e8b78b, 29dc26c, d69ffb3, c59e21a):
- 242 dress actors, all passing `place_tower.py --check`;
- `p10_6a_checks.py` 17/17;
- suite 78/78;
- the `expected_materials` slot-index fix.

**Capture run.** The lead and the owner captured 21 of 22 views, with the editor in the foreground.
- `Docs/ArtTest/belltower/p10_6a_<pose>_ed.png`: 18 of the 20 `p10_6a_poses.json` views. `dress_collapse_close` failed 3 × 6 attempts.
- `p10_6d_door_shortcut_court/pass_ed.png`: both door views.

**Verdicts:**

| Item | Pose(s) | Verdict |
|---|---|---|
| `Door_Shortcut` (P10-6d) | `p10_6d_door_shortcut_court`, `_pass` | **Pass.** The light wedges are gone: from the courtyard the leaf's top now stands in front of the dark tympanum. From the passage, a 2–3 cm bright slit runs along the hinge edge (Y ≈ 1938–1941). It was already present in P10-6c and is at the limit; P10-7 re-judges it under the final lights. |
| Collapse | `dress_collapse_along` | **Pass.** The heap, chunks and leaning rafter read as fallen vault. |
| Note | `dress_note` | **Pass.** It still reads clearly among the plants. |
| Ivy | `dress_ivy_s` | **Pass.** Dead leaves hang over the S arcade. |
| Cells | `dress_cells_w` | **Pass.** Stool and bucket at the W cell door. |
| Passage | `dress_passage_east`, `_west` | **Pass.** The weeds read along both wall bases. |
| Lanterns | `dress_lantern_bells`, `dress_tower_lantern`, `dress_mech3_chain` | **Pass.** They are unlit until P10-7. |
| Rope coil | `dress_tower_coil` | **Pass.** |
| Decals | `dress_decal_s`, `dress_decal_e` | **Pass.** The damp and mould read at the wall bases. |
| Chain B, eyelet, latch box | `dress_mech3_latch` | **Pass.** The box reads as a plain block, which is accepted. |
| Slates | `dress_land10_slates` | **Pass for placement.** They read pale under the greybox light; P10-7 re-judges. |
| Cobweb, landing 5 | `dress_cobweb_l5` | **Accepted.** The NE corner has a timber post, so the web reads as threads strung from the post to both walls. |
| **Chain A** | `dress_mech3_chain` | **Fail (lead error).** The chain starts in the air about 18 cm above the drum's top. |
| **Garth** | `dress_garth_from_s`, `_from_e`, `_high`, `dress_note` | **Fail: not overgrown.** The GrassMedium02 clumps at 0.9–1.4 are thin blades that barely show. The ferns read best. `MI_Prop_Earth` (`Wetness` 0.3) reads as glossy wet tar under the lights and dominates the bed. |
| **Belfry debris** | `dress_belfry_debris` | **Fail.** Four identical chunks stand in a neat row with the rafter flat beside them. They read as placed blocks, not fallen debris. |

**The lead's chain error (corrects D1.20).**
- D1.20 placed the drum at Z 150–200. That came from `p10_6b_checks.py`'s `world_box`, which adds the root component's `relativeLocation` on top of the actor transform. For a root component, `relativeLocation` *is* the world location, so the root is counted twice.
- Read live on 2026-10-31:
  - `Pedestal` is the root of `Mech_Ritual3`, with relativeLocation (11790, 1780, 50) = the actor location, and mesh z −50…50, so world Z **0–100**;
  - `Core` sits at relative (0, 0, 75), so the drum centre is at Z 125 and the drum at world Z **100–150**;
  - the bands are at Z 104–108 and 142–146, and the bars at Z 135.5–140.5.
- The D1.18 start, Z 110, was correct. **New start: (11824.0, 1783.0, 120.0).** It is on the drum surface, between the lower band and the bars, and the run crosses the pedestal's east face (X 11840) at Z ≈ 122, which is 22 above the pedestal top.

**P10-6e steps** (environment-designer, [EDITOR]; commits "P10-6e: …"):
0. **Fix `world_box`** in `Tools/belltower/p10_6b_checks.py`.
   - When the first name in `chain` is the actor's root component (read `rootComponent`), start from loc (0, 0, 0) and scale (1, 1, 1) and skip that component's relative transform, because the actor transform already holds it.
   - Run `p10_6b_checks.py capstan`. Expect Pedestal Z 0–100 and Core Z 100–150, with X/Y around (11790, 1780).
   - If the numbers differ, stop and report them.
   - Commit: `P10-6e: world_box no longer double-counts the root component`.
1. **Generator** (`gen_tower_layout.py`; never hand-edit the outputs):
   1. **Chain A start:** **(11824.0, 1783.0, 120.0)**. Comment: `# D1.21: drum is world Z 100-150 (Pedestal is the root, Z 0-100); between the lower band (104-108) and the bars (135.5-140.5)`. Update every other use of the old start, including the D1.20 comment.
   2. **Garth vegetation** (same seed 1224, and the same draw order per plant: mesh, then scale, then position tries, then Z jitter, then yaw):
      - **Grass:** 90 at scale **1.6–2.6**.
      - **Nettle:** unchanged, 30 at 2.8–4.4.
      - **Fern:** **35** at **0.9–1.3**.
      - **New kind `Rooibos`:** **18** at **1.0–1.6**. Meshes `SM_LB_CC0_WildRooibos_01..05` (folder `CC0 + "WildRooibos/"`). Real bounds by mesh: `((-34.8, -42.2, 0.0), (34.8, 42.2, 53.9))`, `((-26.2, -23.7, 0.0), (26.2, 23.7, 54.1))`, `((-21.3, -23.6, 0.0), (21.3, 23.6, 44.8))`, `((-16.4, -19.2, 0.0), (16.4, 19.2, 42.0))`, `((-13.9, -8.3, 0.0), (13.9, 8.3, 30.6))`. Slots: the mesh's own (`MI_Foliage_WildRooibos`), with no override. Labels `CLA_GarthRooibos_00..17`.
      - **Kind order:** Grass, Nettle, Fern, Rooibos.
      - **Clearance from the 4 small crosses:** **40** (was 15), so the 60 cm crosses stay visible. The others stay as in D1.20: cross base 20, slabs 15, note 70.
      - **Two shrubs at fixed spots**, placed after the random kinds and with no exclusion against them:

        | Label | Mesh | Location | Yaw | Scale |
        |---|---|---|---|---|
        | `CLA_GarthShrub_0` | `SM_LB_CC0_SearsiaLucida_06` | (10950, 1500, 100) | 35 | 1.1 |
        | `CLA_GarthShrub_1` | `SM_LB_CC0_SearsiaLucida_07` | (10750, 2100, 100) | 200 | 1.2 |

        Real bounds `((-32.9, -24.2, 0.0), (32.9, 24.2, 73.9))` and `((-19.1, -16.2, 0.0), (19.1, 16.2, 78.7))`; own slots (`MI_Foliage_SearsiaLucida`); NoCollision; folder `Cloister/Dressing/Garth`.
      - **Count:** the garth total is 90 + 30 + 35 + 18 + 2 = **175**.
      - **Garth bed material:** `CLA_GarthBed` uses `mi={"MAT_Earth": "MI_Cl_GarthEarth"}`, with the `mi_paths` entry `/Game/LastBell/Environments/Cloister/Materials/MI_Cl_GarthEarth`.
   3. **Belfry debris** (replaces `TWA_Debris_Chunk_0..3` and the rafter; seed `random.Random(1403)`).
      - **The strip:** the W slab next to the tower W wall, X 12041–12130, Y 2170–2450, floor Z 2500.
      - **Chunks:** five chunks `TWA_Debris_Chunk_0..4` with meshes `[Chunk_S, Chunk_M, Chunk_S, Chunk_S, Chunk_M]`.
        - Per chunk, in this draw order: `s = uniform(0.35, 0.6)` (uniform xyz), `yaw = uniform(0, 360)`, footprint centre `cx = uniform(12065, 12100)`, `cy = 2190 + 60 * k + uniform(-15, 15)`.
        - `loc` puts the rotated, scaled footprint centre at (cx, cy) and the bottom at Z 2500. The kit pivot is the min corner, so `loc = (cx, cy) − R(yaw) · (s · sx / 2, s · sy / 2)`.
        - Chunk `k = 3` also gets pitch 12, so it leans.
        - If the AABB min X is below 12041, shift +X by the difference. If the AABB max Y is above 2450, shift −Y.
        - NoCollision, `MI_Kit_Rubble`.
      - **`TWA_Debris_Rafter`** (`SM_LB_Prop_Rafter_Broken_15x10x260`, pivot at the bottom centre, long axis +Z). The wanted result:
        - the long axis runs within ±8° of +Y in plan;
        - its S end lies on the floor (bottom Z 2500–2502) at (12055 ± 5, 2185 ± 5);
        - its N end is raised 20–30 cm, as if resting on chunk 4;
        - its AABB is inside X 12041–12130, Y 2170–2450, Z 2500–2550.
        - Derive the rotator, then confirm it with the generator's `world_aabb`. Record the rotator you chose in a comment.
      - **Checks:** keep the `chamber debris` lane check passing (WP_TowerStairs clearance ≥ 60).
   4. **Re-run.** It must exit 0 with all checks passing.
      - The `dress` count is 242 + 35 (garth) + 1 (chunk) = **278**.
      - Commit the generator and its outputs: `P10-6e: generator - chain at the drum, denser garth (rooibos, shrubs, bigger grass), random belfry debris (D1.21)`.
2. **`MI_Cl_GarthEarth`.**
   - Create it at `/Game/LastBell/Environments/Cloister/Materials/MI_Cl_GarthEarth` as a child of `MI_Prop_Earth`, then set `Wetness` = **0.08**.
   - **Parent chain check.** Read `MI_Prop_Earth` → `MI_Brown_Mud_03_WA` → ….
     - **If the root is `M_LB_Surface` and the static switch `bGapGrowth` exists:** turn it on in `MI_Cl_GarthEarth`.
       - Copy `GrowthColorTex`, `GrowthNormalTex`, `GrowthRoughnessTex` and `GrowthTint` from `MI_Env_Floor_Puddled`.
       - Set `GrowthLevel` 0.55, `GrowthNoiseAmount` 0.45 and `WallGrowthDistCm` 120. Leave the rest at default.
     - **Otherwise:** set only `Wetness`, and report the chain.
   - Save the MI (one package), check that it compiles without errors in the log, and read back every parameter you set.
   - Commit: `P10-6e: MI_Cl_GarthEarth (matte, moss in the hollows)`.
3. **Place.**
   - `place_tower.py --cats garth --only CLA_GarthBed` (the material changes).
   - `place_tower.py --cats dress` (all; idempotent).
   - Then list every actor in the `dress` folders (`Cloister/Dressing/*`, `BellTower/Art/Dressing`, `BellTower/Art/Belfry`, `Cloister/Art/StairHouse`, `Courtyard/Passage`).
     - A label that starts with `CLA_Garth`, `TWA_Debris_`, `PSA_Weed_` or `CLA_Collapse_` and is not a record id is an orphan: remove it and report it.
     - Any other label that is not among the layout's record ids (all categories): report it and **never remove it**.
   - Run `--cats dress --check` and `--cats garth --only CLA_GarthBed --check`. Everything must pass.
4. **Update `p10_6a_checks.py`.**
   - **Chain:** its `run_from` lies within the Core's world AABB from the fixed `world_box`, grown by 2 cm, and is ≥ 30 from the drum axis. Do not hard-code Z.
   - **Counts:** grass 90, nettle 30, fern 35, rooibos 18, shrub 2, weeds 32.
   - **Belfry:** every `TWA_Debris_*` AABB is inside X 12041–12130, Y 2170–2450, Z 2499–2560, and the rafter meets the rules in step 1.3.
   - **Everything else** is unchanged (the gameplay overlap and the door swing boxes).
   - Save the output to `Docs/ArtTest/belltower/p10_6e_checks.txt`. It must be ALL PASS.
5. **Save, reload, re-check.** Save `L_Monastery` (one package), check `is_dirty` is false, run `load_level`, then re-run step 3's `--check` and the checks script.
6. **Suite** with the command-line runner: **78/78**, with the same named tests as D1.20 step 6. If anything fails, stop and report.
7. **Commit:** `P10-6e: dressing re-placed (278 dress), garth earth MI, checks, suite 78/78`, including `L_Monastery.umap`. Never stage `L_Throwaway_P9_4.umap`.

**End state:**
- the map is saved and not dirty;
- PIE is stopped;
- there are no `TMP_` actors;
- the throttle is untouched;
- no parent Blueprint was saved;
- nothing changed in the courtyard (`MI_Prop_Earth` itself is unchanged).

**Lead capture after P10-6e:** re-capture `dress_collapse_close`, `dress_garth_from_s`, `dress_garth_from_e`, `dress_garth_high`, `dress_note`, `dress_mech3_chain` and `dress_belfry_debris`, as `p10_6e_<pose>_ed.png`.

### D1.22 P10-6e review: dressing pass complete (lead, 2026-10-31)
**Accepted** (cacb196, c416405, ce8d6da, 0f4421c):
- 278 dress actors;
- `MI_Cl_GarthEarth`: child of `MI_Prop_Earth`, root `M_LB_Surface`, `Wetness` 0.08, `bGapGrowth` on with the Moss002 textures;
- `p10_6e_checks.txt` 29/29;
- suite 78/78 (`Saved/Logs/p10_6e_suite.log`);
- the two clamps added for the belfry chunks and the rafter's yaw of −5°.

**Captures** (`p10_6e_<pose>_ed.png`, all 7):
- **Chain A** (`dress_mech3_chain`): **pass**. It leaves the drum at mid-height and runs to the eyelet and on to the latch box beside the tower door, so the capstan now reads as the door mechanism.
- **Garth** (`dress_garth_from_s`, `_from_e`, `_high`, `dress_note`): **pass**. From the walks it reads as an overgrown bed around the cross and graves: tall grass tussocks, ferns, dark dry rooibos, nettles and two shrubs. The earth reads damp rather than tar-like.
  - Earth still shows between the plants from above, with a few specular patches under the greybox lights. P10-7 re-judges the sheen under the final lights. If it still reads glossy, lower `MI_Cl_GarthEarth` `Wetness` to 0, an instance-only change.
  - The note stays clear and readable.
- **Belfry debris** (`dress_belfry_debris`): **pass**. Varied chunks are scattered along the W wall, one leaning, with the broken rafter rising onto the last one.
- **Collapse** (`dress_collapse_close`): **pass**. The heap of mossy rubble and squared blocks, with the rafter leaning on the pier.

**Capture lessons (for MCP_NOTES in P10-8):**
- While the editor is not the foreground window, every viewport call resets after about 19 s, including `SetCameraTransform`. While it is throttled in the background, `CaptureEditorImage` returns a stale frame.
- The first views of new material permutations (the garth) need `--timeout 15 --settle 3`. Each took up to 60 s.
- The capture wrapper must wait for the foreground again before each attempt. If the owner touches the PC mid-run, the run then pauses instead of failing.
- Scratch wrapper: `p10_6e_run_slow.py`. P10-8 moves it into `Tools/` as a reusable capture script.

**Dressing pass complete.** Next is P10-7, lighting (D1.8). The lead writes its detailed spec first, and it needs the owner's go.

### D1.23 P10-7 spec: lighting (lighting-vfx, [EDITOR]; commits "P10-7: …") (lead, 2026-10-31)
This spec replaces D1.8's values with the courtyard's approved lantern style (P7-FIX3 G6). The lead read that style live on 2026-10-31:

| Light | Lumens | Radius | `lightColor` | Light function | Scattering | Other |
|---|---|---|---|---|---|---|
| `Light_Route_Lantern_1` | 400 | 500 | (1, 0.549, 0.2196) | `MI_LF_Lantern` | 1.5 | no shadows |
| `Light_Grave_Candle_A0` (candles) | 120 | 200 | (1, 0.576, 0.161) | `MI_LF_Candle` | 1.0 | `sourceRadius` 2 |

D1.8's 100–250 lm at 2200 K would leave the vaulted walks far darker than the courtyard at the same exposure.

**Current state, read live:**
- The moon is `DirectionalLight` (`DirectionalLight_1`): 0.9 lux, colour (0.745, 0.804, 0.922), shadows on, volumetric scattering 1, pitch −38, yaw 35.
- `Moon_Fill` 0.06; `SkyLight` 0.28 (specified cubemap).
- Height fog: density 0.035, volumetric fog on.
- **Post process:**
  - The cloister and tower currently sit only under the unbound `PostProcess_Exposure` (EV100 3).
  - `PP_Outdoor_Night` (EV100 1.15, `ColorSaturationShadows` 0.65, priority 1, blend 500) ends at X ≈ 5500.
  - `PP_Crypt` (EV100 0.2) covers Z −1150…−40 only.
- **Greybox lights:** `Light_Cloister_*` and `Light_Tower_*` are 3000 lm white, radius 900–1500; `Light_TowerTop_0` is 20000 lm.

**Step 0: before you start.**
- Read `CLAUDE.md`, `Tools/mcp/MCP_NOTES.md`, D1.8, D1.9 and this section.
- Confirm that `L_Monastery` is loaded, PIE is stopped and the map is not dirty.
- Read `Tools/crypt/place_lighting.py` (P9-7: greybox removal with a dump, the LFV and the PP) and the `light` category of `Tools/crypt/place_crypt.py` (light spawning and read-back). You port both.

**Step 1: generator** (`Tools/belltower/gen_tower_layout.py`; never hand-edit its outputs).
1. **The 13 light records.** Every light record's `extras.light` becomes `{"type": "PointLight", "lumens", "radius", "shadows": false, "color_linear", "light_function", "volumetric_scattering", "source_radius"}`, with no `temperature_K`.
   - Lantern colour = (1.0, 0.549, 0.2196) with `light_function` `MI_LF_Lantern`.
   - Candle colour = (1.0, 0.576, 0.161) with `MI_LF_Candle`.

   | Label | Location | lm | Radius | Colour | Light function | Scattering | Source radius |
   |---|---|---|---|---|---|---|---|
   | `L_Cl_Bells` | (11960, 2380, 320) | 400 | 600 | lantern | Lantern | 1.5 | 0 |
   | `L_Cl_Door` | (11960, 1880, 300) | 350 | 500 | lantern | Lantern | 1.5 | 0 |
   | `L_Cl_Entry` | (10520, 300, 300) | 300 | 500 | lantern | Lantern | 1.5 | 0 |
   | `L_Cl_West` | (9560, 2000, 320) | 300 | 500 | lantern | Lantern | 1.5 | 0 |
   | `L_Cl_Cell` | **(9812, 2972, 25)** | 120 | 250 | candle | Candle | 1.0 | 2 |
   | `L_Ps_Lantern` | (9380, 2240, 300) | 300 | 500 | lantern | Lantern | 1.5 | 0 |
   | **`L_Ps_West`** (new) | (6500, 2240, 300) | 300 | 500 | lantern | Lantern | 1.5 | 0 |
   | `L_Tw_Base` | (12060, 1880, 260) | 300 | 500 | lantern | Lantern | 1.5 | 0 |
   | `L_Tw_Land4` | unchanged | 200 | 400 | lantern | Lantern | 1.5 | 0 |
   | `L_Tw_Land7` | unchanged | 200 | 400 | lantern | Lantern | 1.5 | 0 |
   | `L_Tw_Land10` | unchanged | 200 | 400 | lantern | Lantern | 1.5 | 0 |
   | `L_Tw_Bell` | (12255, 1865, 2690) | 400 | 600 | lantern | Lantern | 1.5 | 0 |
   | `L_Tw_BellFill` | (12500, 2300, 3300) | 200 | 1000 | (0.75, 0.80, 0.92) | none | **0** | 0 |

   - `L_Ps_West` goes in folder `Lighting/Cloister`.
   - Comment: `# D1.23: courtyard lantern style (P7-FIX3 G6); L_Cl_Cell moved beside the N cell door with its candles; L_Ps_West added (passage W half was > 15 m from any warm pool)`.
2. **New `dress` records:**
   - **Passage W lantern**, mirroring `PSA_LanternBracket` / `PSA_Lantern` at X 6500:
     - `PSA_LanternBracket_W`: `SM_Dungeon_chain_holder` at (6500, 2300, 310), yaw −90;
     - `PSA_Lantern_W`: `SM_Wooden_Lantern_01` at (6500, 2240, 258), yaw 0;
     - both NoCollision, folder `Courtyard/Passage`.
   - **Cell candles** (folder `Cloister/Dressing/Cells`, NoCollision, the mesh's own materials), meshes from `/Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Meshes/`:
     - `CLA_Cell_Candle_0` `SM_Candle_Melted_03` at (9800, 2975, 0), yaw 0;
     - `CLA_Cell_Candle_1` `SM_Candle_Melted_07` at (9822, 2970, 0), yaw 40;
     - `CLA_Cell_Candle_2` `SM_Candle_Melted_09` at (9812, 2985, 0), yaw 110.
   - Read each candle mesh's bounds live (`StaticMeshTools.get_bounds`) and pass them as `mb`. Do not estimate.
   - Check that no candle's AABB reaches Y ≥ 2998. The N wall inner face is Y 3000.
3. **`lights_plan`:**
   - **`fog`** becomes a list of 4 Local Fog Volumes, `LFV_Tower_0..3`, folder `Lighting/BellTower`:
     - centres (12500, 2000, Z) for Z = 460, 1380, 2300, 3220, uniform scale 0.92 (radius 460);
     - `radialFogExtinction` 0.12, `heightFogExtinction` 0.0, `fogPhaseG` 0.3, `fogAlbedo` (0.86, 0.87, 0.90), `fogEmissive` (0, 0, 0).
   - **New `pp`:** `PP_Cloister`, a PostProcessVolume:
     - world box X 6000–13100, Y −450…3200, Z −40…4200;
     - `bUnbound` false, priority 1, `blendRadius` 300;
     - overrides `AutoExposureMinBrightness` = `AutoExposureMaxBrightness` = 1.15 (as `PP_Outdoor_Night`) and `ColorSaturationShadows` (0.65, 0.65, 0.65, 1).
   - **`delete`:** the same 17 labels.
   - **`keep_and_tune`:** `Light_TowerExt_0..2` stay at 300 lm (read back only).
4. **Re-run.** It must exit 0 with all checks passing.
   - Report the `dress` count (expected 278 + 5 = **283**) and the light count (**13**).
   - Commit the generator and its outputs: `P10-7: generator - courtyard-style lantern values, L_Ps_West, cell candles, LFV_Tower stack, PP_Cloister (D1.23)`.

**Step 2: `Tools/belltower/place_lighting_p10.py`.** It is a new script adapted from `Tools/crypt/place_lighting.py` (P9-7) and the `light` category of `place_crypt.py`. It reads `p10_d1_layout.json`, and every action is idempotent (it removes its own labels first) and reads back what it set.
1. **`greybox`:**
   - Dump the 17 `lights_plan.delete` lights (class, transform, `LightComponent0` intensity / units / radius / colour / shadows) to `Docs/ArtTest/belltower/greybox_lights_before.json`.
   - Then delete them and confirm that each label is gone.
   - Never delete any other light.
2. **`lights`:** spawn the 13 `cat == "light"` records as `/Script/Engine.PointLight`, with one full transform call, label = id and folder = record folder. Then set on `LightComponent0`:
   - `intensityUnits` Lumens, `intensity`, `attenuationRadius`;
   - `bUseTemperature` false, `lightColor` (the same 0–1 float form the component reads back);
   - `castShadows` false, `volumetricScatteringIntensity`, `sourceRadius`;
   - `lightFunctionMaterial` = `/Game/LastBell/Materials/Instances/<MI>.<MI>`, or none.
   - Read every value back.
3. **`lfv`:** spawn the 4 `LocalFogVolume` actors with the values in step 1.3 (port P9-7's `lfv`) and read them back.
4. **`pp`:** spawn `PP_Cloister` (port P9-7's `pp`; the default brush is ±100, so scale = half-extent / 100) and set the values in step 1.3.
   - Read back the actor bounds (±5 against the box), `bUnbound`, priority, `blendRadius` and every override.
5. **`check`:** read back everything above.
   - All 17 greybox lights are absent.
   - The 7 `L_Cl_*` / `L_Ps_*` lights are in `Lighting/Cloister` and the 6 `L_Tw_*` lights are in `Lighting/BellTower`.
   - Report any other light found in those two folders, and never delete it. `Light_TowerExt_0..2` may live there.
   - The 4 LFVs and `PP_Cloister` are present.
   - `Light_TowerExt_0..2` are untouched (300 lm).
   - It prints PASS/FAIL per line and exits 1 on any FAIL.

**Step 3: place.**
1. `place_tower.py --cats dress --only PSA_Lantern` and `--only CLA_Cell_Candle`, then `--check` for both.
2. `place_lighting_p10.py greybox`, then `lights`, then `lfv`, then `pp`, then `check`.
3. Do not change `DirectionalLight`, `Moon_Fill`, `SkyLight`, `ExponentialHeightFog`, `PostProcess_Exposure`, `PP_Outdoor_Night`, `PP_Crypt` or any courtyard, chapel or crypt light.
4. Do not change `MI_LB_BellBronze`: the lead judges the bronze in the P10-7 captures first.

**Step 4: save, reload, re-check.**
1. Save `L_Monastery` in one `save_assets` call and check that `is_dirty` is false.
2. Run `load_level`, then `place_lighting_p10.py check` and both `place_tower.py --check` runs again. Everything must pass.

**Step 5: tests.** Run the full suite with the command-line runner: **78/78**, with the named tests of D1.20 step 6. If anything fails, stop and report.

**Step 6: capture poses** (no captures). Write `Tools/belltower/poses/p10_7_poses.json`:

| Pose | Value | The lead checks |
|---|---|---|
| `lt_cl_s_entry` | [10650, 700, 170, 0, 90] | mean luma 0.04–0.08 |
| `lt_inscription` | [11800, 2380, 170, 5, 0] | `luma_report.py --plaque` contrast ≥ 2.5 |
| `lt_bells` | [11800, 2380, 160, −5, 0] | numerals I–IV legible |
| `lt_tower_mid` | [12835, 1665, 1534, 10, 180] | mean 0.02–0.06, slit moonbeams visible |
| `lt_tower_shaft_up` | [12150, 2000, 170, 70, 0] | light from the louvres and the broken roof |
| `lt_bell_top` | [12165, 2000, 2660, 10, 0] | bell centre-10 % median ≥ 0.08; bronze not pink |
| `lt_belfry_up_sw` | [12500, 2150, 2670, 25, −135] | moonlight through the broken SW roof corner |
| `lt_gate` | [300, 0, 170, 10.67, 9.31] | the belfry and broken roof read against the sky |
| `lt_garth` | [10750, 1100, 200, −8, 85] | garth earth sheen |
| `lt_cl_ne` | [11850, 2900, 170, 0, 180] | N walk readable but dark |
| `lt_door_tower_out` | [11700, 2000, 170, 0, 0] | the plank-slit light |
| `lt_door_shortcut_pass` | [6400, 2000, 170, 0, 180] | the hinge slit |
| `lt_passage_east` | [6300, 2000, 170, −12, 0] | passage readable (L_Ps_West pool) |
| `lt_cell_candles` | [9700, 2700, 170, −26, 68] | candle pool at the N cell door |

**Step 7: commit.**
- Message: `P10-7: lighting placed (13 lights, 4 LFV, PP_Cloister; 17 greybox lights removed), checks, suite 78/78`.
- Include `L_Monastery.umap`, the script, the before-dump and the poses.
- Never stage `L_Throwaway_P9_4.umap`.

**End state:**
- the map is saved and not dirty;
- PIE is stopped;
- there are no `TMP_` actors;
- the throttle is untouched;
- no parent Blueprint was saved.

**Lead review after P10-7** (with the owner):
- Capture `p10_7_poses.json` in **PIE Simulate**, which shows no editor sprites and gives the true exposure and animated light functions. Use `--timeout 15 --settle 3` and the foreground-resilient wrapper.
- Run `Tools/crypt/luma_report.py` against the targets above.
- Tune by instance-only changes within these ranges:
  - `PP_Cloister` EV100 0.2–2.0;
  - lantern lumens ×0.5–×2;
  - the LFV extinction;
  - `MI_LB_BellBronze` tint, if it reads pink.
- Each tuning round is a small Sonnet task followed by one more capture session.

### D1.24 P10-7 capture review; P10-7b tuning spec (lead, 2026-10-31)
**Accepted** (f58d697, 61b9f38):
- 13 lights, 4 LFVs, `PP_Cloister`;
- 17 greybox lights removed, with the dump at `Docs/ArtTest/belltower/greybox_lights_before.json`;
- `place_lighting_p10.py check` 40/40;
- suite 78/78;
- the agent's four small deviations (the script fix, the narrow `--only`, the lantern Z 258.1, and Movable lights like the courtyard's).

**Capture run.** All 14 `p10_7_poses.json` views were captured in **PIE Simulate** as `Docs/ArtTest/belltower/p10_7_<pose>.png`, with no editor sprites and the true exposure. B2 luma (`luma_report.py`):

| Pose | Measured | Target | Verdict |
|---|---|---|---|
| `lt_cl_s_entry` | mean **0.030**, 66 % < 0.02 | mean 0.04–0.08 | **Low.** The moonlit garth through the arcade reads well, but the walk floor is near black. |
| `lt_inscription` | plaque contrast **2.41** | ≥ 2.5 | **Just low.** The text is clearly legible, dark on lit stone. The lantern 40 cm from the wall over-lights it: the wall above the tablet glows saturated orange. |
| `lt_bells` | mean 0.18 | numerals legible | **Pass.** II and III read; I and IV sit partly behind their bells, as before. Same orange over-light. |
| `lt_tower_mid` | mean **0.027** | 0.02–0.06 | **Pass on luma.** A dark stair with one lantern pool. **No moonbeams** come through the slits. |
| `lt_tower_shaft_up` | mean 0.099 | louvre / roof light | **Fail (look).** The upper tower is black, with no moonlight from the louvres or the broken roof. |
| `lt_bell_top` | centre-10 % median **0.233** | ≥ 0.08 | **Luma pass, look fail.** The great bell reads as shiny orange copper, not old bronze (the D1.5 target). |
| `lt_belfry_up_sw` | mean 0.061 | moonlight through the SW collapse | **Fail (look).** No moonlit patch shows. |
| `lt_gate` | — | tower against the sky | **Pass.** The belfry and pyramid roof read as a moonlit silhouette above the chapel roofline. |
| `lt_garth` | mean 0.023 | sheen | **Pass.** No sheen is left. Dim and moonlit, the note faintly visible. |
| `lt_cl_ne` | mean 0.041 | dark but readable | **Pass.** The vaulted walk is dark, with the candle pool at the far end. |
| `lt_door_tower_out` | mean 0.217 | plank slits | **Pass for the slits:** none show now that the interior is dark. **Fail for the look:** the wall is over-lit orange by `L_Cl_Door` and `L_Cl_Bells`. |
| `lt_door_shortcut_pass` | mean 0.014 | hinge slit | **Pass.** A thin bright line along the hinge edge reads as light round an old door. A dry tussock stands at the threshold (P7 dressing). |
| `lt_passage_east` | mean 0.067 | readable | **Pass.** The `L_Ps_West` pool, with the cloister arch lantern at the far end. |
| `lt_cell_candles` | centre median 0.81 | candle pool | **Pass, a little hot.** |

**Outside Phase 10:** in `lt_gate`, four white specks hang in the sky above the courtyard. The lead traced them to the chapel's `Gobo_Moon_*` cards (P8), at (5300–7850, −1250…−1280, 1340–2820). This is not judged here; the owner decides whether to look at it.

**Decisions for P10-7b** (instance values only, except the new moon lights):
1. **Exposure:** `PP_Cloister` EV100 1.15 → **0.65** (+0.5 stop). This brings `lt_cl_s_entry` to about 0.042 and `lt_tower_mid` to about 0.038.
2. **Hot lanterns:** `L_Cl_Bells` 400 → **200** lm, `L_Cl_Door` 350 → **180**, `L_Tw_Bell` 400 → **250**, `L_Cl_Cell` 120 → **80**. All other lights stay.
3. **Bronze** (`MI_LB_BellBronze`, parent `M_LB_Surface`; this also changes the small bells, which should read older and browner):

   | Parameter | Old | New |
   |---|---|---|
   | `BaseColorTint` | (0.62, 0.45, 0.32) | **(0.46, 0.42, 0.34)** |
   | `BrightnessMul` | 0.5 | **0.42** |
   | `Metallic` | 0.9 | **0.75** |
   | `RoughnessMin` | 0.45 | **0.55** |
   | `RoughnessMax` | 0.75 | **0.85** |

4. **Tower moonbeams.** Follow the project's established pattern: a P8/P9 moon spot outside the opening, aimed along the moon, plus a P9 shaft card from the opening along the beam.
   - The moon travels along d = (0.6455, 0.4520, −0.6157), which is `DirectionalLight` pitch −38, yaw 35. Only the S and W faces and the SW roof collapse face the moon.
   - **New light records** in the generator (`cat` `light`, folder `Lighting/BellTower`, `extras.light.type` `SpotLight`):
     - rotation (−38, 35, 0); colour (0.745, 0.804, 0.922); no light function;
     - `castShadows` **true**, `bCastVolumetricShadow` true, `volumetricScatteringIntensity` 0.8, `sourceRadius` 0.
     - Each spot sits 150 cm (roof: 200) back along −d from the inner centre of its opening:

     | Label | Opening (inner centre) | Spot location | lm | Inner / outer cone | Radius |
     |---|---|---|---|---|---|
     | `L_Tw_MoonSlit_F03` | S slit F03 (12500, 1540, 718.1) | (12403.2, 1472.2, 810.4) | 600 | 4 / 8 | 1500 |
     | `L_Tw_MoonSlit_F07` | S slit F07 (12500, 1540, 1627.3) | (12403.2, 1472.2, 1719.6) | 600 | 4 / 8 | 1500 |
     | `L_Tw_MoonSlit_F08` | W slit F08 (12040, 2000, 1854.0) | (11943.2, 1932.2, 1946.3) | 600 | 4 / 8 | 1500 |
     | `L_Tw_MoonRoof` | SW roof collapse (12188, 1688, 4027) | (12058.9, 1597.6, 4150.1) | 1500 | 10 / 20 | 2500 |

     - Store the opening point in `extras.opening` and the card width in `extras.shaft_width_cm`: 40 for the slits, 200 for the roof.
   - **Shaft cards** `SA_Tower_F03`, `SA_Tower_F07`, `SA_Tower_F08`, `SA_Tower_Roof`: a new `shafts` action in `place_lighting_p10.py`, ported from `Tools/crypt/place_lighting.py` `shafts` with one change:
     - The card starts at the **opening point + 5·d**, not at the spot, because the spot is outside the wall.
     - Trace from that start along d up to 1500 cm. Length = 5 + hit distance (600 if nothing is hit).
     - Engine `Cylinder` centred on the segment, `cyl_rot(d)`, scale (w/100, w/100, length/100), `MI_LightShaft_Crypt`.
     - `castShadow` false, NoCollision (profile and `collisionEnabled`), folder `Lighting/BellTower`.
     - Read back and report each card's start, end, hit distance and bounds.
   - **`lights` spawns `SpotLight`** for these records (`/Script/Engine.SpotLight`). It sets `innerConeAngle`, `outerConeAngle`, `castShadows` and `bCastVolumetricShadow` from the record, plus everything it already sets.

**P10-7b steps** (lighting-vfx, [EDITOR]; commits "P10-7b: …"):
1. **Generator.**
   - Change the 4 lumens in decision 2. Add the 4 spot records in decision 4, plus a `lights_plan.pp` EV of 0.65.
   - Comment: `# D1.24: P10-7 capture review`.
   - Re-run: exit 0, all checks pass. The light count is **17**.
   - Commit the generator and its outputs.
2. **`place_lighting_p10.py`.**
   - Add SpotLight support to `lights` and a new `shafts` action.
   - `check` also verifies:
     - the 4 spots: type, cones, shadows and rotation within 0.1°;
     - the 4 cards: present, NoCollision, `MI_LightShaft_Crypt`;
     - the `PP_Cloister` EV.
   - Commit.
3. **Bronze.** Set the five `MI_LB_BellBronze` values in decision 3 and read them back.
   - Save that MI alone, then check that `is_dirty` is false and that the log shows no material errors.
   - This is the only material change allowed.
4. **Place.** Run `place_lighting_p10.py lights` (idempotent: it re-places all 17), then `pp`, then `shafts`, then `check`. Everything must pass.
5. **Save, reload, re-check.**
   - Save `L_Monastery` (one package) and check `is_dirty` is false.
   - Run `load_level`, then `check` again.
6. **Suite:** 78/78, with the named tests of D1.20 step 6.
7. **Commit:** `P10-7b: EV 0.65, cooler lanterns, old-bronze MI, tower moon spots + shaft cards, suite 78/78`, including `L_Monastery.umap` and `MI_LB_BellBronze.uasset`. Never stage `L_Throwaway_P9_4.umap`.

**End state:**
- the map is saved and not dirty;
- PIE is stopped;
- there are no `TMP_` actors;
- the throttle is untouched;
- no parent Blueprint was saved;
- the only material changed is `MI_LB_BellBronze`.

**Lead re-capture after P10-7b** (PIE Simulate, prefix `p10_7b_`): all 14 poses.
- `lt_cl_s_entry`: mean 0.04–0.08.
- `lt_inscription`: contrast ≥ 2.5.
- `lt_tower_mid` and `lt_tower_shaft_up`: moonbeams visible.
- `lt_bell_top`: median ≥ 0.08 and the bronze reads old, not copper.
- `lt_belfry_up_sw`: a moonlit patch.

### D1.25 P10-7b capture review (lead, 2026-11-01)
**Accepted** (12b47ba, b5fd53b, 44a5d19):
- `PP_Cloister` EV 0.65;
- the lanterns at 200 / 180 / 250 / 80 lm;
- `MI_LB_BellBronze` old-bronze values;
- `L_Tw_MoonSlit_F03/F07/F08` and `L_Tw_MoonRoof`, with the shaft cards `SA_Tower_*`;
- check 51/51 and suite 78/78;
- the agent's two notes: the lantern check now excludes the moon spots, and each card starts at its opening.

**Captures** (PIE Simulate, `p10_7b_<pose>.png`, all 14), B2 luma:

| Pose | P10-7 | P10-7b | Target | Verdict |
|---|---|---|---|---|
| `lt_cl_s_entry` | 0.030 | **0.038** | 0.04–0.08 | **Accepted at 0.002 under.** The arcade and the moonlit garth read, and the walk floor stays dark. |
| `lt_inscription` | 2.41 | **2.52** | ≥ 2.5 | **Pass.** |
| `lt_tower_mid` | 0.027 | **0.039** | 0.02–0.06 | **Pass on luma.** This pose looks away from the slit beams, so beam visibility is checked with the new poses below. |
| `lt_bell_top` | 0.233 | **0.233** | ≥ 0.08 | **Pass.** The roof moon spot now throws cool light and frame shadows across the E belfry wall behind the bell, the moonlight through the SW collapse. The great bell reads matte, warm, aged bronze with patina under the lantern; it no longer reads pink copper. The small bells read dark old bronze. |
| `lt_door_tower_out` | 0.217 | **0.194** | — | Warm pool at the tower door. Less hot, still strongly orange; accepted as the puzzle focal point. |
| `lt_cl_ne` | 0.041 | 0.054 | — | **Pass.** |
| `lt_passage_east` | 0.067 | 0.087 | — | **Pass.** |
| `lt_garth` | 0.023 | 0.029 | — | **Pass.** |

All other poses are as in D1.24.

**Beam check.** `lt_tower_mid` and `lt_belfry_up_sw` look away from the beam paths. The lead added `Tools/belltower/poses/p10_7c_poses.json`, captured in PIE Simulate as `p10_7c_*`:

| Pose | Value | Looks at |
|---|---|---|
| `lt_beam_south` | [12500, 2150, 900, −31, −75] | the F03 beam, from the shaft centre |
| `lt_beam_west` | [12500, 2000, 1700, 14, 175] | the F08 beam |
| `lt_beam_roof` | [12750, 2350, 2700, 20, −140] | the roof collapse beam |

**Beam check result** (`p10_7c_*`, PIE Simulate):
- `lt_beam_south`: **pass**. The S slit F03 glows, and a soft blue moon shaft crosses the dark shaft to the stair, with a cobweb lit beside it.
- `lt_beam_west`: the W slit F08 glows. Its beam is short (1.6 m to the flight) and mostly hidden behind the rails. Accepted.
- `lt_beam_roof`: the SW collapse reads clearly, with broken rafters against the night sky above the oak frame and bell. The roof beam lands on the E wall, as seen in `lt_bell_top`.

**P10-7 lighting pass complete.** Next is P10-8 (docs, QA, the owner's GPU check and playtest, the phase report), after the owner's go.

### D1.26 P10-8 plan: docs, capture tool, QA, owner review (lead, 2026-11-01)
The owner gave the go for P10-8 on 2026-11-01. It follows the P9-8 pattern (P9 D1.18):
- **P10-8a** (docs and the capture tool) and **P10-8b** (QA) run in parallel. 8a never touches the editor; 8b only reads from it.
- Then the lead reviews both and posts **"PHASE 10 READY FOR YOUR REVIEW"** with the owner checklist (**P10-8c**).
- Nothing merges until the owner says "approve and merge".

Both agents are spawned with `model: "sonnet", effort: "high"`.

**Shared rules for 8a and 8b:**
- Work on `claude/phase-10-belltower`. Check `git branch --show-current` first; never switch, merge or push.
- Stage only your own files by explicit path; never `git add -A` or `git add .`.
- Never stage `Content/LastBell/Maps/L_Throwaway_P9_4.umap`.
- If `.git/index.lock` exists or a commit fails on the lock, wait 5 s and retry, at most 12 times.
- Commit trailer: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Never save anything in Unreal and never edit `.uasset`/`.umap` files.
- Python: `C:\Users\heman\AppData\Local\Python\pythoncore-3.14-64\python.exe`.
- 8b re-runs the generator in parallel, so 8a reads the layout only through `git show HEAD:Docs/plans/p10_d1_layout.json`, never from the working file.

---

#### P10-8a: docs and the capture tool (general-purpose; no editor; commit "P10-8a: Phase 10 docs, capture_session.py")
**Read first:**
- `CLAUDE.md`;
- `Tools/mcp/MCP_NOTES.md` (all of it);
- this plan's sections D1.17–D1.26;
- the two lead scratch wrappers that the new tool replaces (read-only references, outside the repo):
  - `C:\Users\heman\AppData\Local\Temp\claude\C--Hemant-Prj-Learning-TheLastBell\be0022a0-87e7-4517-81e3-bd2aaebbbccb\scratchpad\p10_6e_run_slow.py` (editor-viewport captures);
  - `...\scratchpad\p10_7_run.py` (PIE Simulate captures plus luma);
- the docstring of `Tools/crypt/capture_poses.py`.

**1. New tool `Tools/crypt/capture_session.py`.** It goes next to `capture_poses.py` and `luma_report.py`, which it calls as subprocesses (never import them).

Module docstring: usage, flags, exit codes, and "P10-8a (D1.26): replaces the lead's scratch wrappers".

**CLI:**
```
python Tools/crypt/capture_session.py <poses.json> <out_dir> --prefix P [--suffix S] [--mode simulate|editor]
       [--only a,b] [--force] [--max-wait 3600] [--fg-wait 1800] [--attempts 5] [--timeout 15] [--settle 3]
       [--log-dir DIR] [--luma JSON_OUT] [--plaque POSE] [--dry-run]
```
- **Defaults:**
  - `--mode simulate`;
  - `--suffix ""`;
  - `--only`: every pose in the JSON, in file order;
  - `--max-wait 3600` (s to wait for the editor to come to the front before the session starts);
  - `--fg-wait 1800` (s to wait before each attempt);
  - `--attempts 5`, `--timeout 15`, `--settle 3`;
  - `--log-dir <project>\Saved\Logs\captures` (create it).
- Use `argparse`. The project root is two levels above the script: `os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`.
- For `capture_poses.py` and `luma_report.py`, use `sys.executable`.

**Behaviour, in this order:**
1. **Pose list.** Load `<poses.json>`. Unknown names in `--only` → exit 4 with the unknown names listed.
   - The output file of a pose is `<out_dir>\<prefix><pose><suffix>.png`.
   - Without `--force`, drop every pose whose file already exists and print `skipped (exists): <name>` for each.
   - If nothing is left, print that and exit 0.
2. **`--dry-run`.** Print:
   - the mode;
   - the remaining poses;
   - the exact `capture_poses.py` command line of attempt 0;
   - the luma command lines that would run.

   Exit 0. Dry-run must not import `ue` or contact the editor, so import `ue` lazily, after this step.
3. **Wait for the foreground.** Same `fg_title()` / `wait_fg(limit)` as the wrappers: the foreground window title ends with `Unreal Editor`, polled every 2 s.
   - If it isn't in front within `--max-wait`, print `Unreal Editor never became the foreground window (last: <title>); no captures taken` and exit 2.
   - Then sleep 3 s.
4. **Editor-mode PIE check.** In `editor` mode, if `EditorAppToolset.IsPIERunning` is true, print `PIE is running; stop it before an editor-mode session` and exit 3. Nothing has been changed at this point.
5. **Throttle.** Read the current `bThrottleCPUWhenNotForeground` from `/Script/UnrealEd.Default__EditorPerformanceSettings` (`get_properties`) and keep it as the original. Set it to false (`set_properties`, with `values` as a JSON string).
6. **Everything from here runs in `try` / `finally`.**
   - **Simulate mode:** if PIE isn't running, call `StartPIE {"options": {"bSimulate": true, "playMode": "PlayMode_InViewPort", "warmupSeconds": 5}}` and set `started = True`.
     - Poll `IsPIERunning` every 2 s, for at most 120 s, else raise `RuntimeError("PIE Simulate did not start")`.
     - Then sleep 8 s.
   - **Attempt loop** (`for attempt in range(attempts)`):
     1. `remaining` = the poses whose file does not exist or has an mtime earlier than the session start time (`time.time()` taken at step 1). Stop the loop when `remaining` is empty.
     2. `wait_fg(fg_wait)`. On a timeout, print `lost the foreground for <fg_wait> s; stopping` and stop the loop. Then sleep 3 s.
     3. Run `capture_poses.py <poses> <out_dir> --double --raise --force --timeout T --settle S --prefix P [--suffix S] --only <remaining joined by ,> --log <log_dir>\cap_<prefix><attempt>.log`, adding `--editor` in editor mode.
        - `--force` is safe because `--only` holds only the poses not captured in this session.
        - Use `cwd` = the project root and `capture_output=True, text=True`.
        - Print the stdout lines containing `saved`, `MISSING`, `finished` or `abort` (case-insensitive), at most the last 60. If none match, print the last 800 chars of stdout and stderr.
     4. **Circuit breaker** (MCP_NOTES "Crypt and Phase 9" §2 and the `capture_poses.py` docstring). If `capture_poses.py` exits with code 3:
        - print `breaker tripped; resting 60 s`;
        - sleep 60 s;
        - set a flag so the next attempt runs with `--only <the first remaining pose>` (a single-pose test).
        - If that single-pose attempt also leaves its pose missing, or exits 3 again, print `breaker tripped twice; stopping` and stop the loop.
        - If it succeeds, clear the flag and continue normally.
   - **`finally`:**
     1. If `started` and `IsPIERunning`: call `StopPIE` and print `PIE stopped`. Catch and print any exception.
     2. Restore the throttle to the **original value read in step 5**, not to a hard-coded true.
     3. Print the read-back.
7. **Luma.**
   - If `--luma` is given, run `luma_report.py --json <JSON_OUT> <every file written in this session>` and print the last 6000 chars.
   - If `--plaque POSE` is given and that pose's file exists, run `luma_report.py --plaque <file>` and print it.
8. **Exit code:**
   - 0: every pose was captured in this session;
   - 1: some are missing. Print `missing: a,b,...`.

   Codes 2, 3 and 4 are as above.

**Validation.** No live run; the lead runs the first live session with the owner. Paste every output in your report.
- `python -m py_compile Tools/crypt/capture_session.py`;
- `python Tools/crypt/capture_session.py --help`;
- `python Tools/crypt/capture_session.py Tools/belltower/poses/p10_7c_poses.json Docs/ArtTest/belltower --prefix p10_7c_ --dry-run` → all 3 poses are `skipped (exists)` and it exits 0;
- the same with `--force` → the 3 poses and a simulate-mode command line, exit 0;
- the same with `--force --mode editor --suffix _ed` → `--editor` and `--suffix _ed` appear in the command line;
- `--only lt_beam_south,nope --force --dry-run` → exit 4, naming `nope`.

**2. `Tools/mcp/MCP_NOTES.md`.** Append a section `## Bell tower and cloister (P10)`, in the numbered style of the "Crypt and Phase 9 fix sets" section. One fact per item and how to apply it.
1. **Foreground captures (D1.22).**
   - While the Unreal Editor is not the foreground window, every viewport call resets after about 19 s, including `SetCameraTransform`, not only `CaptureViewport`.
   - While the editor is throttled in the background, `CaptureEditorImage` returns a stale frame.
   - So a capture run needs the owner: they bring Unreal to the front and leave the PC alone.
   - Use `Tools/crypt/capture_session.py`. It waits for the foreground before each attempt and restores the throttle.
2. **Slow first frames (D1.22).** The first views of new material permutations took up to 60 s each. Use `--timeout 15 --settle 3` (the `capture_session.py` defaults).
3. **PIE Simulate for lighting judgement (D1.24).**
   - Simulate captures show no editor sprites and give the true exposure, so judge lighting and luma only on them.
   - Use `capture_session.py --mode simulate --luma <json> [--plaque <pose>]`.
   - Use editor-mode captures (`--mode editor --suffix _ed`) for geometry and dressing only.
4. **`capture_session.py` reference.**
   - The CLI and its exit codes (copy them from the docstring).
   - Status: "dry-run validated in P10-8a; first live session pending". The lead updates this line after the first live run.
5. **`set_properties` `values` is a JSON string** (`json.dumps({...})`), not an object. This applies to every `ObjectTools.set_properties` call.
6. **Root-component world box (D1.21).**
   - For an actor's root component, `relativeLocation` / `relativeRotation` / `relativeScale3D` already are the world transform.
   - When composing a component's world box from the parent chain, never apply the root's relative transform on top of the actor transform.
   - In P10-6a the double-counted root put the capstan chain start about 50 cm above the drum. The fix is in `Tools/belltower/p10_6b_checks.world_box`; reuse that function.
7. **Light component paths.** `<map>.<map>:PersistentLevel.<Actor>.LightComponent0` covers point, spot and directional lights. Sky light: `.SkyLightComponent0`; height fog: `.HeightFogComponent0`.
8. **No console or CVar setter over MCP** (only `SearchCVars`). `r.*` settings, `scalability` and `stat` commands are typed by the owner in a PIE window.
9. **`Tools/belltower` scripts** (editor on `L_Monastery`, no PIE, one editor-touching process at a time):
   - `gen_tower_layout.py`: the generator. It writes `Docs/plans/p10_d1_layout.json` and `p10_d1_tables.md` (never hand-edit them) and runs 54 checks, including the lane checks.
   - `place_tower.py`:
     - `--cats` (the order `block wall tower stair arcade vault roof floor garth door doorleaf dress`), `--only`, `--check`, `--fix-collision`;
     - `--hide-greybox` / `--verify-greybox`, `--ground`, `--perim`.
   - `place_lighting_p10.py`: `greybox | lights | lfv | pp | shafts | check`. `lights` places point and spot records; `check` gave 51/51 after P10-7b.
   - `bp_swap.py`: the dump and diff for child-BP swaps (D-071 procedure).
   - `p10_6a_checks.py` (dressing checks, 29 lines) and `p10_6b_checks.py` (the swap readouts and `world_box`).
   - `import_p10.py` (the P10-4 imports).
   - Pose files: `Tools/belltower/poses/`.
10. **Moon beams through openings (D1.24).**
    - The courtyard moon travels along d = (0.6455, 0.4520, −0.6157) (`DirectionalLight` pitch −38, yaw 35). Only openings that face it get a beam: here the S and W faces and the SW roof collapse.
    - **Pattern:** a shadowed `SpotLight` 150–200 cm back along −d from the opening's inner centre, rotation (−38, 35, 0), with `bCastVolumetricShadow` and scattering 0.8.
    - **Shaft card:** an engine `Cylinder` with `MI_LightShaft_Crypt`, NoCollision and no shadow. It runs from the opening + 5·d, traced along d.
    - Implementation: `place_lighting_p10.py shafts`.
11. **Door leaves in pointed or gabled openings (D1.19).** Check both faces for light wedges at the leaf's top corners. `Door_Shortcut` needed leaf scale Z 1.30.
12. **Lighting a dark interior (D1.24).** If a wall 40 cm from a lantern glows saturated orange, the lantern is too strong. Fix it in lumens, not in exposure. Raise exposure only for the walk floors (`PP_Cloister` EV100 0.65).

**3. `Docs/PERFORMANCE_BUDGET.md`.** Add one row to "Measurements":
- **Date:** 2026-11-01.
- **Build / where:** "Phase 10 cloister + bell tower (1a47a69, after P10-7b)".
- **GPU column:** "RTX 4050 6 GB, High, 1920×1080 window (owner)". **GPU total:** "**owner measurement pending (P10-8c)**". **Key passes:** "—".
- **Notes:**
  - the counts from `Docs/plans/p10_d1_layout.json` `counts`, read by script, in this form: `tower 32, floor 7, stair 32, gameplay 15, roof 15, block 8, wall 65, arcade 28, garth 16, vault 10, door 5, doorleaf 5, dress 283, light 17 (538 records)`. If the script disagrees with these numbers, write the script's numbers and report the difference;
  - the light makeup: 11 lanterns (shadowless, `MI_LF_Lantern`, scattering 1.5), 1 cell candle, 1 bell fill (r 1000, scattering 0), and 4 shadowed moon spots (3 slit spots at 600 lm and the roof spot at 1500 lm, scattering 0.8). `Light_TowerExt_0..2` (300 lm) are kept;
  - 4 shaft cards, 4 LFVs (`LFV_Tower_0..3`), `PP_Cloister` EV100 0.65;
  - "measure in the cloister S walk, the garth, the tower mid-stair and the belfry".
- Verify the light makeup by script from the `placements` records with `cat == "light"`: print id, `extras.light.type`, lumens and `castShadows`. Report any mismatch with the list above; don't change the generator.

**4. `Docs/ASSET_REGISTRY.md`.**
- **Rope 003** row: in the Unreal-path column, replace "not yet imported (P10-4)" with `/Game/LastBell/Environments/BellTower/Textures/T_Rope003_BC, _N, _R` → `MI_LB_Rope` (P10-4).
- **Metal 058 B** row: replace it with `/Game/LastBell/Environments/BellTower/Textures/T_Metal058B_BC, _N, _R, _M` → `MI_LB_BellBronze` (P10-4; old-bronze values P10-7b, D1.24).
- **Usage check by script:**
  - Collect every distinct `mesh` in `placements` that contains `/ThirdParty/` or `/Environments/Props/CC0/`.
  - For each, find the registry row that covers it (match by the asset or pack name).
  - Append `; P10 cloister/tower: <short use>` to that row's usage column, unless the row already mentions P10. Take `<short use>` from the record's `group`, e.g. "garth vegetation", "cell candles", "chains".
- **Missing rows:** list any mesh without a row in your report. Add a row only from the facts in `ExternalAssets/Incoming/<folder>/` and the existing download records, and never invent a licence. Fab assets added by the owner have no Incoming folder; report them instead of adding rows.

**5. `Docs/RISKS.md`** (edit the rows in place and keep the table format):
- **R-39:** add to the mitigation: "P10: viewport calls also reset when the editor is merely not the foreground window; `Tools/crypt/capture_session.py` waits for the foreground before each attempt; capture runs are scheduled with the owner at the PC". The status stays Open.
- **R-40:** add `BP_SmallBell_Cloister`, `BP_Inscription_Cloister`, `BP_RitualMechanism_TowerCapstan` and `BP_TagInteractable_GreatBell`, but only those whose construction script copies the parent's body.
  - Check each one in D1.17 ("P10-6b") and in `Docs/ArtTest/belltower/blueprints_dsl_p10.json` or the `Tools/belltower/p10_6b_dsl/` files.
  - Report the evidence for each (copied or not).
- **R-42:** status **Mitigated**, with the evidence: tread tops within 0.0009 cm of the greybox steps (D1.11), and WalkPath TowerStairs PASS plus RouteBot Success in every suite since P10-5. Add "Closed after the owner walks the stairs (P10-8c)".
- **R-43:** status **Mitigated**, with the evidence: the D-071 swaps had 0 differences on re-dump after reload (D1.18); `Door_Shortcut` 0 differences after P10-6d (D1.19); RouteBot, Puzzles.Blueprints and the Save tests in the suite at 78/78. Add "owner playtest confirms (P10-8c)".
- **R-44:** stays **Open**. Add "owner stat gpu pending (P10-8c)".
- **R-45:** status **Mitigated**, with the evidence:
  - numerals II and III legible in the captures, while I and IV sit partly behind their bells (D1.24);
  - inscription plaque contrast 2.52 (D1.25);
  - "owner judges at 2 m (P10-8c)".

**6. `Docs/DECISIONS.md`.** Append one row in the table's format:
- **ID:** **D-083**.
- **Date:** 2026-11-01.
- **Context:** "Cloister and bell-tower lighting outcome (P10-7, P10-7b; D1.23–D1.25)".
- **Decision:**
  - the courtyard lantern style (`MI_LF_Lantern`, scattering 1.5, shadowless) with the final lumens: `L_Cl_Bells` 200, `L_Cl_Door` 180, `L_Cl_Entry` 300, `L_Cl_West` 300, `L_Ps_Lantern` 300, `L_Ps_West` 300, `L_Tw_Base` 300, `L_Tw_Land4/7/10` 200, `L_Tw_Bell` 250;
  - `L_Cl_Cell` candle 80 lm; `L_Tw_BellFill` 200 lm, r 1000, moon colour, scattering 0;
  - the moon spots `L_Tw_MoonSlit_F03/F07/F08` (600 lm, cones 4/8) and `L_Tw_MoonRoof` (1500 lm, cones 10/20), rotation (−38, 35, 0), shadowed, scattering 0.8, with the shaft cards `SA_Tower_*`;
  - `LFV_Tower_0..3`;
  - `PP_Cloister` EV100 0.65, `ColorSaturationShadows` 0.65, blend 300;
  - `MI_LB_BellBronze` old bronze (tint (0.46, 0.42, 0.34), BrightnessMul 0.42, Metallic 0.75, Roughness 0.55–0.85);
  - the 17 greybox lights removed (dump `Docs/ArtTest/belltower/greybox_lights_before.json`).
- **Alternatives:** "D1.8's original values; raising exposure only".
- **Reasoning:** "Matches the approved courtyard style; walk floors readable at EV 0.65 without hot lantern walls; moonbeams only where the moon can enter".
- **Implications:**
  - accepted: `lt_cl_s_entry` mean 0.038 (target 0.04, 0.002 under);
  - accepted: the W slit beam is short and mostly hidden behind the rails;
  - owner stat gpu pending (P10-8c).

**7. `Docs/IMPLEMENTATION_PLAN.md`** (Phase 10 table):
- Replace the `P10-8` row with three rows:
  - `| P10-8a | Docs (MCP_NOTES P10 section, PERFORMANCE_BUDGET, ASSET_REGISTRY, RISKS, D-083) and Tools/crypt/capture_session.py (D1.26) | general-purpose (no editor) | P10-7b |`
  - `| P10-8b | QA: suite, live checks, logs, generator lane re-check, git/asset hygiene (D1.26) | qa-reviewer [EDITOR read-only] | P10-7b |`
  - `| P10-8c | Owner stat gpu + playtest; PHASE 10 READY FOR YOUR REVIEW | lead + owner | P10-8a, P10-8b |`
- In the status line, replace the final `Next: P10-8.` with `P10-8 started 2026-11-01 (D1.26): 8a docs and 8b QA in parallel, then the owner review (P10-8c).`

**8. Drift check, report only.** Grep `Docs/TECHNICAL_DESIGN.md` for `Tower`, `Cloister`, `Mechanism 3`, `SmallBell`, `Inscription`, `Door_Base_Dungeon` and `child`. List every statement that the P10 implementation contradicts (D1.17 child BPs, the doors on `BP_Door_Base_Dungeon`, D-078 visible-false greybox), with line numbers. **Do not edit TECHNICAL_DESIGN**; the lead decides.

**Commit:** stage exactly `Tools/crypt/capture_session.py`, `Tools/mcp/MCP_NOTES.md`, `Docs/PERFORMANCE_BUDGET.md`, `Docs/ASSET_REGISTRY.md`, `Docs/RISKS.md`, `Docs/DECISIONS.md` and `Docs/IMPLEMENTATION_PLAN.md`. Message: `P10-8a: Phase 10 docs, capture_session.py`.

**Report:**
- the validation outputs;
- the PERFORMANCE_BUDGET script output;
- the registry rows touched and any missing;
- the R-40 evidence;
- the drift list;
- the commit hash.

---

#### P10-8b: QA (qa-reviewer; editor read-only; commit "P10-8b: QA report")
**Read first:** `CLAUDE.md`, `Tools/mcp/MCP_NOTES.md`, and this plan's sections D1.20 step 6 and D1.25.

**Allowed in the editor** (via `Tools/mcp/ue.py`):
- reads only: `get_properties`, `find_actors`, `get_current_level`, `is_dirty`, `GetLogEntries`, `trace_world`, `get_actor_bounds`;
- the read-only check scripts named below, **one at a time**.

**Forbidden:** any `set_*`, spawn, remove, save, compile, PIE, and `load_level`. If the editor isn't on `L_Monastery`, stop and report; don't load it.

**Steps.** Record every command and its output in the report.
1. **Git.** Run:
   - `git branch --show-current` (must be `claude/phase-10-belltower`);
   - `git status --short` (only the throwaway umap untracked, plus 8a's work in progress if present);
   - `git log --oneline main..HEAD | wc -l` and `git log --oneline main..HEAD | head -5`.
2. **Editor state:**
   - `SceneTools.get_current_level` ends with `L_Monastery`;
   - `EditorAppToolset.IsPIERunning` is false;
   - `AssetTools.is_dirty` on `/Game/LastBell/Maps/L_Monastery` and `/Game/LastBell/Environments/BellTower/Materials/MI_LB_BellBronze` (expect false);
   - `SceneTools.find_actors {"name": "TMP_", "tag": "", "collision_channels": []}` (expect none).
3. **Live checks** (each writes to a file under `Docs/ArtTest/belltower/`):
   - `python Tools/belltower/place_tower.py --cats block wall tower stair arcade vault roof floor garth door doorleaf dress --check > Docs/ArtTest/belltower/p10_8_place_check.txt`: exit 0 and no FAIL lines; report the per-category summary.
   - `python Tools/belltower/place_tower.py --verify-greybox > Docs/ArtTest/belltower/p10_8_greybox_check.txt`: exit 0.
   - `python Tools/belltower/place_lighting_p10.py check > Docs/ArtTest/belltower/p10_8_lighting_check.txt`: expect 51/51 (D1.25).
   - `python Tools/belltower/p10_6a_checks.py > Docs/ArtTest/belltower/p10_8_6a_checks.txt`: expect every line PASS (29 in D1.22).
4. **Generator and lane re-check** (offline):
   - Run `python Tools/belltower/gen_tower_layout.py`. Exit 0; `all_checks_pass` true; 54 checks.
   - Report the lane-check lines (TowerStairs, the patrol route, search points, `WSpawn`, chamber debris) with their worst clearance. Each must be ≥ 60 cm.
   - Then `git status --short Docs/ Tools/` must show **no change** to `Docs/plans/p10_d1_layout.json`, `Docs/plans/p10_d1_tables.md` or any other file. If something changed:
     - report `git diff --stat`;
     - restore those files with `git restore <paths>`;
     - flag it as a determinism finding.
5. **Suite.** Use the command-line runner in `Tools/mcp/MCP_NOTES.md` ("Running tests"), with the log `C:\Hemant\Prj\Learning\TheLastBell\Saved\Logs\p10_8_suite.log`.
   - Report the totals: **78/78** expected.
   - Report each of these results:
     - `WalkPath.Monastery`, with its TowerStairs, CryptToCloister and the four Courtyard paths;
     - `RouteBot.Monastery`;
     - `Puzzles.Blueprints`;
     - `Warden.MonasteryReachability`;
     - `Warden.Monastery.StagesRelocateTheWarden`;
     - every `Save` test.
   - On any failure, quote the log lines; don't re-run more than once.
6. **Editor log.** `LogsToolset.GetLogEntries` must always be filtered: `{"category": "", "pattern": "Error", "maxEntries": 200}`, then `"Warning"` the same way.
   - Group by category; leave out the known benign `LogCrowdFollowing` RecastNavMesh warning.
   - List each distinct message once (first 160 chars) with its count.
   - Mark anything that names `L_Monastery`, `BellTower`, `Cloister`, a `BP_` asset, a material, or `MI_`.
7. **Asset hygiene** (git only):
   - **Content root:** `git diff --name-only main...HEAD -- Content | grep -v '^Content/LastBell/'` must be empty.
   - **Naming:** for `git diff --name-only --diff-filter=A main...HEAD -- Content/LastBell`, check each basename's prefix against CLAUDE.md's naming list. Kit and art meshes are `SM_`; textures `T_`. List any violations.
   - **Parent Blueprints:** `git diff --name-only main...HEAD` must contain none of `BP_SmallBell`, `BP_SequencePuzzle`, `BP_Inscription`, `BP_RitualMechanism`, `BP_Door_Base`, `BP_TagInteractable`, `BP_TagTrigger`, `BP_EndingTrigger`, `BP_Inspectable_Note`, `BP_Door_Base_Dungeon` and `BP_RitualMechanism_CryptWinch`, as exact `.uasset` basenames.
   - **In memory:** report `is_dirty` for those 11 parents. This is info only; some may be dirty in memory, which is known.
   - **Source:** report `git diff --stat main...HEAD -- Source Config`.
8. **Report file** `Docs/ArtTest/belltower/p10_8_qa.md`:
   - a verdict table (step, expected, actual, PASS/FAIL);
   - then the details;
   - then "Findings" (anything abnormal, with evidence; no fixes).

**Commit:** stage exactly `Docs/ArtTest/belltower/p10_8_qa.md` and the four `p10_8_*_check*.txt` files. Message: `P10-8b: QA report`.

**Report:** the verdict table, the findings and the commit hash.

---

#### P10-8c: owner review (in the "PHASE 10 READY FOR YOUR REVIEW" report)
The lead posts this after reviewing 8a and 8b.
1. **Performance.**
   - Play in a **New Editor Window (PIE)**. In the console, type `scalability 2`, `r.SetRes 1920x1080w`, `stat unit` and `stat gpu`.
   - Measure the GPU total at four places:
     1. the cloister S walk at the bells and inscription;
     2. the garth, seen from the E walk;
     3. the tower mid-stair (landing 6);
     4. the belfry beside the great bell.
   - Right-click → **Play From Here** is fine for these spots. The budget is **≤ 16.6 ms**.
   - **If over**, the lead cuts in this order:
     1. shadows off on `L_Tw_MoonSlit_F07/F08` (F03 and the roof spot keep theirs);
     2. `LFV_Tower` from 4 to 2;
     3. lantern volumetric scattering from 1.5 to 0.
2. **Playtest** (from the start, or from the crypt exit):
   1. Enter the cloister from the crypt stair and read `Note_Cloister`.
   2. Read the inscription at 2 m.
   3. Strike the four small bells in the right order. The capstan turns (Mechanism 3), and the tower door and the shortcut door open.
   4. Watch the shortcut door swing: it must not cut into the arch. Walk the passage both ways.
   5. Climb the tower stairs. Your feet should stay on the treads, with no floating or sinking.
   6. Ring the great bell. The ending plays.
3. **Judge:**
   - the darkness in the walks and the tower;
   - the moonbeams (the S slit; the roof collapse on the belfry wall);
   - the old-bronze bells;
   - the garth;
   - the `Door_Shortcut` hinge slit (accepted in D1.19/D1.24).
4. **Outside Phase 10**, for the owner to decide:
   - the `Gobo_Moon_*` sky specks (P8);
   - the `Door_ChapelMain` / `Door_Sacristy` top corners;
   - the Phase 9 dress bounds mismatches (118).
5. **Then** "approve and merge", or a fix list. A fix list becomes D1.27.

#### P10-8a / P10-8b review (lead, 2026-11-01)
**P10-8a accepted** (43490a1):
- **`Tools/crypt/capture_session.py`:** dry-run validated (help, skip-existing, `--force`, editor mode with suffix, luma/plaque lines, unknown pose → exit 4). The first live session is still pending; it needs the owner at the PC.
- **MCP_NOTES:** section "Bell tower and cloister (P10)", 12 items.
- **PERFORMANCE_BUDGET:** Phase 10 row. The counts (538) and the 17 light records were verified by script, with no mismatch. GPU pending (P10-8c).
- **ASSET_REGISTRY:** the Rope003 and Metal058B paths; P10 use added to 14 rows; no missing rows.
- **RISKS:** R-39 and R-40 updated (the 4 P10 children copy their parents' construction scripts, with evidence from the `p10_6b_dsl` files); R-42, R-43 and R-45 Mitigated; R-44 Open.
- **D-083:** the lighting outcome.

**Drift:** TECHNICAL_DESIGN §10 and §11 did not mention the art child Blueprints or the art over the invisible greybox. The lead fixed both (584af02).

**P10-8b accepted** (65992e5, `Docs/ArtTest/belltower/p10_8_qa.md`):

| Check | Result |
|---|---|
| Suite | 78/78: every WalkPath (TowerStairs, CryptToCloister, 4 Courtyard), RouteBot, Puzzles.Blueprints, the Warden tests and all 10 Save tests |
| `place_tower --check` | 538/538 |
| `--verify-greybox` | 280/280 hidden, BlockAll, 8/8 traces |
| Lighting check | 51/51 |
| Generator | 54/54, deterministic |
| Lanes | worst 70.3 cm (patrol), 77.0 (TowerStairs) |
| Asset hygiene | no Content-root or naming violations; no parent BP changed (none dirty in memory); no Source/Config changes |
| Logs | nothing project-related apart from F2 and F3 |

**Findings:**
- **F1:** `p10_6a_checks.py` had a hard-coded 278 (283 since P10-7's cell candles). The lead changed it to compare with the layout count. Re-run 29/29 (`p10_8_6a_checks_rerun.txt`).
- **F2:** an old log line from a lookup of `MI_LB_BellBronze` at a wrong path (no file uses that path). Info only.
- **F3:** the "staticMesh could not be read" log noise from `p10_6a_checks.py`. Noted in MCP_NOTES.

**Next: P10-8c**, the owner review. The checklist is in D1.26 and in the "PHASE 10 READY FOR YOUR REVIEW" report.
