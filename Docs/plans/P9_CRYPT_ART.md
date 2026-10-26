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
