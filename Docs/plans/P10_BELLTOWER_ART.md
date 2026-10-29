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
