# P7-FIX2 — Fab pick list (migrate from LB_FabStaging → TheLastBell)

Source project: `C:\Hemant\FabStaging\LB_FabStaging`. Select **only these meshes / systems** (Migrate pulls their materials and textures automatically) → right-click → **Asset Actions → Migrate…** → target folder `C:\Hemant\Prj\Learning\TheLastBell\Content`.

## Misc Props (UB) — `/Game/UnrealBucket/Library/...`
| Asset | Use in the courtyard |
|---|---|
| `Industrial/Anvil/SM_Anvil` | work area (KX_Anvil) |
| `Various/Chest/SM_Chest` | work area, against the north wall (KX_Chest) |
| `Various/Trunk/SM_Trunk_Closed` | work area, against the west wall (KX_Trunk) |
| `Tools/CarpenterTools/SM_HandSaw` | on the work table (KX_Tools) |
| `Tools/CarpenterTools/SM_WoodPlane` | on the work table |
| `Tools/CarpenterTools/SM_Chisel_A` | on the work table |
| `Tools/CarpenterTools/SM_HandDrill_A` | on the work table |

## Dungeon Environment — `/Game/Dungeon/...`
| Asset | Use in the courtyard |
|---|---|
| `Meshes/Props/SM_Torch` | wall torch on the west curtain (replaces the planned wall lantern; gives the work-area light a source) |
| `Fire/Particle_Systems/PS_Fire_00` | flame for the torch (and a tiny one for the key-ledge candle if it scales down well) |
| `Meshes/Props/SM_Torture_Devices_Cage` | empty iron cage hung from the gatehouse buttress |
| `Meshes/Props/SM_Dungeon_chain_holder` | wall ring the cage/chains hang from |
| `Meshes/Props/SM_Torture_Devices_Chains` | chains hanging on the north wall |
| `Meshes/Props/SM_Torture_Devices_Breaking_Wheel` | wooden wheel leaning on the north wall (replaces the planned cart wheel) |
| `Candles/Meshes/SM_Candle_Melted_03` | melted candle stubs on the key ledge |
| `Candles/Meshes/SM_Candle_Melted_07` | melted candle stubs on the key ledge |
| `Meshes/Props/SM_Skull_01` | one weathered skull at the edge of the fresh grave (sparing) |

Not migrated now (kept in staging for the crypt, Phase 9): skeleton piles/arms/legs, other skulls, shackles, bars, Judas cradle, iron belt, dungeon door/window/walls, tavern food props, weapons.

After migrating, the agent moves these into `/Game/LastBell/ThirdParty/Fab/MiscProps/` and `/Game/LastBell/ThirdParty/Fab/Dungeon/` (references fixed), adds registry rows (Misc Props: Fab Personal licence, free tier; Dungeon Environment: Fab Standard License, free) and places them per the plan (P7F-4b).
