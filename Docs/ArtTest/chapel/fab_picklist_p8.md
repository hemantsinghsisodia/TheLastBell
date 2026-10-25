# Phase 8: Fab pick list (owner steps)

Two jobs:
- **A:** migrate Dungeon-pack items from the staging project into TheLastBell.
- **B:** re-add two Horror-pack items.

Do them any time before task P8-4. The agents relocate everything into `/Game/LastBell/ThirdParty/Fab/` afterwards, with references fixed, and merge duplicate shared materials.

## A. Dungeon Environment (from `C:\Hemant\FabStaging\LB_FabStaging`)
1. Open LB_FabStaging.
2. In the Content Browser, select **only the assets below**. Ctrl+click across folders, or do it folder by folder. Migrate pulls in their materials and textures automatically.
3. Right-click → **Asset Actions → Migrate…** → target folder `C:\Hemant\Prj\Learning\TheLastBell\Content`.
4. If it asks to overwrite files that already exist, choose **No / skip** (keep ours).

| Folder (`/Game/Dungeon/...`) | Assets | Use in the chapel |
|---|---|---|
| `Candles/Meshes` | `SM_Candle_01` … `SM_Candle_10` (all 10) | fresh and tall candles in the holders and clusters |
| `Candles/Meshes` | `SM_Candle_Melted_01`, `_02`, `_04`, `_05`, `_06`, `_08`, `_09`, `_10` (**not** 03 / 07, which are already in the game) | burnt-down candles on sills, plinths and the ritual circle |
| `Candles/Meshes` | `SM_Candles_Holder_00` … `SM_Candles_Holder_05` (all 6) | candelabra at the altar, statue and sacristy |
| `Candles/Blueprints` | `BP_Flame_00`, `BP_Flame_01` | real candle flames (instead of waiting for Phase 15) |
| `Meshes/Props` | `SM_Dungeon_shackles_00`, `SM_Dungeon_shackles_01`, `SM_Dungeon_shackles_03`, `SM_Torture_Devices_Shackles_01`, `SM_Torture_Devices_Rope_00` | shackles on the dais, statue plinth and sacristy; rope for the hanging body if its own rope is missing |
| `Meshes/Skeletons` | `SM_Skull_02`, `SM_Skeleton_Pile_00` … `SM_Skeleton_Pile_04`, `SM_Skeleton_Arm_00`, `SM_Skeleton_Arm_01`, `SM_Skeleton_Leg_00`, `SM_Skeleton_Leg_01`, `SM_Skeleton_Pelvis` (**not** Skull_00 / 01, already in the game; **not** Pile_05) | skull in the ritual circle, bone pile in the sacristy, scattered bones by the collapse |
| `Medieval_Tavern_Props/Meshes` | `SM_Bread`, `SM_Bread_Slice`, `SM_Jug`, `SM_Bowl`, `SM_Bowls`, `SM_Cup_01`, `SM_Cup_02`, `SM_Plate`, `SM_Pitcher_01`, `SM_Bottle_01`, `SM_Cutlery`, `SM_Pouch_01`, `SM_Mug_Empty` | the monks' abandoned last meal on the sacristy table |
| `Meshes/Props` | `SM_Scribe_Chair`, `SM_Dungeon_bench`, `SM_Dungeon_chest`, `SM_Dungeon_bowl`, `SM_Pot_00`, `SM_Plate_00` | sacristy furniture and offerings |
| `Materials` | `M_Cobweb` (pulls in `Textures/Cobweb/T_Cobweb`) | cobweb material for our cobweb cards |

Already in the game, so **don't migrate** them again: `SM_Torture_Devices_Chains`, `SM_Dungeon_chain_holder`, `SM_Candle_Melted_03/07`, `SM_Skull_00/01`, `PS_Fire_00`, `SM_Torch`, cage, breaking wheel.

When the migrate finishes, tell me "migrate done".

## B. Horror Props (Bugrimov Maksim): stretcher and body bag
These two were removed in Phase 7 before they were ever committed, so they have to come from Fab again.
1. In the Epic launcher, go to Fab Library → **Horror Props** → **Add to project** → choose **LB_FabStaging**. Use "Show all projects" / a lower engine version if needed, as last time. Don't add it to TheLastBell directly.
2. Open LB_FabStaging. Find the **stretcher** mesh and the **body bag** mesh (named something like `SM_Stretcher*` and `SM_Body_Bag*` / `SM_Bodybag*`).
3. Select only those two, then **Migrate…** to `C:\Hemant\Prj\Learning\TheLastBell\Content`. Skip overwrites.
4. Tell me the two asset names you migrated.
