# Phase 9: Fab pick list (owner step)

Migrate these from the Dungeon Environment pack in `C:\Hemant\FabStaging\LB_FabStaging` into TheLastBell. It's the same procedure as Phase 8:
1. Open LB_FabStaging.
2. Select **only** the assets below.
3. Right-click → **Asset Actions → Migrate…** → `C:\Hemant\Prj\Learning\TheLastBell\Content`.
4. If it asks to overwrite, choose **No**.

Their materials and textures come along automatically. The agents then relocate everything into `/Game/LastBell/ThirdParty/Fab/Dungeon/`.

| Folder (`/Game/Dungeon/...`) | Assets | Use in the crypt |
|---|---|---|
| `Meshes/Props` | `SM_Wall_00`, `SM_Wall_01` | crypt walls |
| `Meshes/Props` | `SM_Arch`, `SM_Pillar` | arches between chambers and tunnels; pillars in the ossuary and chain chamber |
| `Meshes/Props` | `SM_Roof` | ceilings |
| `Meshes/Props` | `SM_Ground`, `SM_Ground_01` | floors |
| `Meshes/Props` | `SM_Bars`, `SM_Dungeon_door`, `SM_Dungeon_window`, `SM_Dungeon_toplock` | iron grates (moonlight from the ceiling), barred cells and niches, a crypt door |
| `Meshes/Props` | `SM_Dungeon_beam`, `SM_Dungeon_halfbeam`, `SM_Wooden_Beam` | timber shoring in the flooded passage and the chain chamber |
| `Meshes/Props` | `SM_Charcoal_Pit` | a brazier as a warm light source in the chain chamber |
| `Meshes/Props` | `SM_Torture_Devices_Cage_Open` | an open hanging cage (the closed one is already in the game) |
| `Meshes/Skeletons` | `SM_Skeleton_Pile_05` | extra bone pile for the ossuary |

**Don't migrate** these: they're already in the game. All candles and holders, `SM_Torch`, `PS_Fire_00/01`, the chains, chain holder, closed cage, breaking wheel, shackles, rope, `SM_Skull_00/01/02`, `SM_Skeleton_Pile_00..04`, the arms/legs/pelvis, the chest, bench, scribe chair, bowl, pot and plates.

When it's done, tell me "migrate done".
