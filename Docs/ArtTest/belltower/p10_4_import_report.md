# P10-4 import report (bell tower, cloister, Mech 3 props)

Branch `claude/phase-10-belltower`. Script: `Tools/belltower/import_p10.py` (textures, MIs, meshes, check, report). All values below were read back from the editor after saving. No level was touched; `L_Monastery` and the nine dirty survey Blueprints were never saved.

## Counts

| Folder | Assets |
|---|---|
| `/Game/LastBell/Environments/BellTower/Meshes/` | 33 meshes (31 `SM_LB_Tw_*`, `SM_LB_Prop_GreatBell_A`, `SM_LB_Prop_BellRope_2610`) |
| `/Game/LastBell/Environments/Cloister/Meshes/` | 40 meshes (36 `SM_LB_Cl_*`, `SM_LB_Prop_SmallBell_A`, `SM_LB_Prop_SmallBellBracket_A`, `SM_LB_Prop_BellPlaque_A`, `SM_LB_Prop_InscriptionTablet_A`) |
| `/Game/LastBell/Environments/BellTower/Textures/` | 7 textures |
| `/Game/LastBell/Environments/BellTower/Materials/` | 7 MIs |

Every mesh's bounds match the Blender report (`tower_report.json`, `cloister_report.json`) within 0.1 cm (73/73). Source triangle total 410,021; the Nanite fallback meshes total 146,935 (the render uses the full Nanite data for the 66 Nanite meshes).

## Import settings
- FBX CDO set before each import (in memory): `vertexColorImportOption = Replace`, `bBuildNanite` per mesh, `bAutoGenerateCollision = false`; `import_materials = false`, `import_textures = false`, `combine_meshes = true`. Names exactly as the FBX. No materials were auto-created (the Meshes, Textures and Materials folders contain only meshes, textures and the 7 new MIs), so nothing had to be deleted.
- **Nanite on (66):** every `SM_LB_Tw_*` and `SM_LB_Cl_*` except the two louvres, plus `SM_LB_Prop_GreatBell_A`. `SM_LB_Tw_BellFrame_A` and `SM_LB_Tw_BellHeadstock_A` are in the on set.
- **Nanite off (7):** `SM_LB_Tw_Louvre_130x450`, `SM_LB_Tw_Louvre_130x450_Broken`, `SM_LB_Prop_BellRope_2610`, `SM_LB_Prop_SmallBell_A`, `SM_LB_Prop_SmallBellBracket_A`, `SM_LB_Prop_BellPlaque_A`, `SM_LB_Prop_InscriptionTablet_A`.
- **Simple collision** (read from `BodySetup.AggGeom`): `SM_LB_Tw_BellFrame_A` 4 convex, `SM_LB_Prop_GreatBell_A` 1 convex, `SM_LB_Prop_SmallBell_A` 1 convex. The other 70 meshes: 0 shapes of any kind. `CollisionTraceFlag = CTF_UseDefault` on all 73.

## Textures (`/Game/LastBell/Environments/BellTower/Textures/`)

| Asset | Source | Size | Compression | sRGB | LOD group |
|---|---|---|---|---|---|
| `T_Metal058B_BC` | Metal058B Color | 2048x2048 | TC_Default | on | World |
| `T_Metal058B_N` | NormalDX | 2048x2048 | TC_Normalmap | off | WorldNormalMap |
| `T_Metal058B_R` | Roughness | 2048x2048 | TC_Alpha | off | WorldSpecular |
| `T_Metal058B_M` | Metalness | 2048x2048 | TC_Alpha | off | WorldSpecular |
| `T_Rope003_BC` | Color | 2048x1024 | TC_Default | on | World |
| `T_Rope003_N` | NormalDX | 2048x1024 | TC_Normalmap | off | WorldNormalMap |
| `T_Rope003_R` | Roughness | 2048x1024 | TC_Alpha | off | WorldSpecular |

**Deviation (compression):** D1.12 says roughness/metalness "as Masks". `M_LB_Surface`'s `RoughnessTex` and `MetalMaskTex` samplers are `SAMPLERTYPE_Alpha`, so the single-channel maps are `TC_Alpha` (linear), the same as the precedent `T_Rock_064_R` and `T_Leaking004_R`. `TC_Masks` would mismatch the sampler type. Normals are `TC_Normalmap`, linear, as in the precedent.

**Memory impact (estimate, full mip chain, nothing streamed out):** Metal058B BC1 2.8 MB + BC5 normal 5.6 MB + BC4 roughness 2.8 MB + BC4 metalness 2.8 MB = 14.0 MB; Rope003 (2048x1024) 1.4 + 2.8 + 1.4 = 5.6 MB. About 19.6 MB of texture memory in total, all streamable. Mesh `.uasset` size on disk: BellTower/Meshes 7.1 MB, Cloister/Meshes 4.8 MB (largest `SM_LB_Tw_Roof_BrokenSW` 1.6 MB). Texture `.uasset` on disk 17.4 MB (includes source data). The 2K Rope003 is generous for a 9 cm rope; if the budget needs it, a 1024 cap on `T_Rope003_*` is a one-line change.

## Material instances (`/Game/LastBell/Environments/BellTower/Materials/`, parent `/Game/LastBell/Materials/Master/M_LB_Surface`)
All values were read back after setting (floats are stored as 32-bit, so 0.9 reads 0.8999999761581421).

| MI | Parameters |
|---|---|
| `MI_LB_BellBronze` | BaseColorTex `T_Metal058B_BC`, NormalTex `T_Metal058B_N`, RoughnessTex `T_Metal058B_R`, MetalMaskTex `T_Metal058B_M`, bUseARM false, BrightnessMul 0.5, BaseColorTint (0.62, 0.45, 0.32, 1), Metallic 0.9, RoughnessMin 0.45, RoughnessMax 0.75 |
| `MI_LB_Rope` | BaseColorTex `T_Rope003_BC`, NormalTex `T_Rope003_N`, RoughnessTex `T_Rope003_R`, bUseARM false, BrightnessMul 1.5, BaseColorTint (1.0, 0.88, 0.70, 1), Metallic 0 |
| `MI_LB_Sally` | BaseColorTint (0.42, 0.14, 0.08, 1), RoughnessMin = RoughnessMax = 0.95, Metallic 0 |
| `MI_LB_BellBand_I` | BaseColorTint (0.32, 0.07, 0.05, 1), RoughnessMin = RoughnessMax = 0.8, Metallic 0 |
| `MI_LB_BellBand_II` | BaseColorTint (0.42, 0.30, 0.08, 1), roughness 0.8, Metallic 0 |
| `MI_LB_BellBand_III` | BaseColorTint (0.10, 0.22, 0.17, 1), roughness 0.8, Metallic 0 |
| `MI_LB_BellBand_IV` | BaseColorTint (0.66, 0.62, 0.52, 1), roughness 0.8, Metallic 0 |

Flat-tint MIs keep the master's default textures; "roughness 0.95 / 0.8" means RoughnessMin = RoughnessMax. `Metallic` is set to 0 explicitly on the non-metal MIs. `Metallic` is only ignored when `bUseARM` is true; here it is false, so `Metallic` applies together with `MetalMaskTex`.

Editor thumbnails use the default thumbnail lighting, not a lit scene. `p10_4_thumb_MI_BellBronze.png` reads as dark bronze with green patina but a little warm and coppery; `p10_4_thumb_MI_Rope.png` reads olive/green-brown, not golden. The lit-capture check that D1.5 asks for belongs to P10-5/P10-6; tune the tints there if needed.

## Slot assignment (mapping per D1.5; read back with `get_material`)
- Tower `MAT_Wood` (every `SM_LB_Tw_*`, including the roof, louvres, stair flights, shaft base/posts, bell frame and headstock) -> `MI_Chapel_Wood_Old`.
- Cloister roofs (`LeanTo`, `LeanTo_Hole`, `StairHouseRoof`) `MAT_Wood` and `SM_LB_Prop_SmallBellBracket_A` `MAT_Wood` -> `MI_Prop_Wood_Weathered`.
- **C15 `SM_LB_Cl_CellDoorFrame_150x270`: its `MAT_Rubble` slot -> `MI_Prop_Wood_Weathered`.** The mesh has no wood slot; the only `MAT_Rubble` geometry is the recessed back panel (`build_cloister.py` builds the panel with the rubble slot), so I applied the D1.12 instruction to that slot. Masonry and Trim slots use the kit MIs.
- `MAT_Masonry` -> `MI_Kit_Masonry`, `MAT_Trim` -> `MI_Kit_Trim`, `MAT_Rubble` -> `MI_Kit_Rubble` (all other meshes), `MAT_Slate` -> `MI_Kit_Slate`, `MAT_Iron` -> `MI_Crypt_Iron`, `MAT_Earth` -> `MI_Prop_Earth`, `MAT_Bronze` -> `MI_LB_BellBronze`, `MAT_Rope` -> `MI_LB_Rope`, `MAT_Sally` -> `MI_LB_Sally`, `MAT_Band` -> `MI_LB_BellBand_III`.
- UE drops slots no face uses, so a mesh can have fewer slots than the Blender report lists (for example `SM_LB_Cl_ArcadeArch_170x80` has no `MAT_Rubble`).

## Thumbnails
In `Docs/ArtTest/belltower/`: `p10_4_thumb_GreatBell.png`, `p10_4_thumb_SmallBell.png`, `p10_4_thumb_Roof_BrokenSW.png`, `p10_4_thumb_Wall_S2_N.png`, `p10_4_thumb_Vault_Groin_770x770.png`, `p10_4_thumb_MI_BellBronze.png`, `p10_4_thumb_MI_Rope.png`.

## Per mesh (path = folder above + name)

| Mesh | Nanite | Tris (source, Nanite fallback) | Slots -> MI | Simple collision |
|---|---|---|---|---|
| `SM_LB_Prop_BellRope_2610` | off | 3384 (3384) | MAT_Rope -> MI_LB_Rope, MAT_Sally -> MI_LB_Sally | none |
| `SM_LB_Prop_GreatBell_A` | on | 13931 (1616) | MAT_Bronze -> MI_LB_BellBronze, MAT_Iron -> MI_Crypt_Iron | 1 convex |
| `SM_LB_Tw_BelfryFloor` | on | 4048 (1108) | MAT_Wood -> MI_Chapel_Wood_Old, MAT_Iron -> MI_Crypt_Iron | none |
| `SM_LB_Tw_BellFrame_A` | on | 1104 (256) | MAT_Wood -> MI_Chapel_Wood_Old, MAT_Iron -> MI_Crypt_Iron | 4 convex |
| `SM_LB_Tw_BellHeadstock_A` | on | 3920 (818) | MAT_Wood -> MI_Chapel_Wood_Old, MAT_Iron -> MI_Crypt_Iron | none |
| `SM_LB_Tw_FlightRail_420` | on | 176 (176) | MAT_Wood -> MI_Chapel_Wood_Old | none |
| `SM_LB_Tw_Landing_250` | on | 856 (380) | MAT_Wood -> MI_Chapel_Wood_Old, MAT_Masonry -> MI_Kit_Masonry | none |
| `SM_LB_Tw_Louvre_130x450` | off | 484 (484) | MAT_Wood -> MI_Chapel_Wood_Old | none |
| `SM_LB_Tw_Louvre_130x450_Broken` | off | 396 (396) | MAT_Wood -> MI_Chapel_Wood_Old | none |
| `SM_LB_Tw_Partition_250x455` | on | 2344 (256) | MAT_Wood -> MI_Chapel_Wood_Old, MAT_Iron -> MI_Crypt_Iron | none |
| `SM_LB_Tw_Roof_BrokenSW` | on | 50516 (46500) | MAT_Slate -> MI_Kit_Slate, MAT_Wood -> MI_Chapel_Wood_Old, MAT_Iron -> MI_Crypt_Iron | none |
| `SM_LB_Tw_S1_E` | on | 7016 (1916) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Tw_S1_N` | on | 4825 (1309) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Tw_S1_S` | on | 4789 (1363) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Tw_S1_W` | on | 7451 (2107) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Tw_S2_E` | on | 16165 (4252) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Tw_S2_N` | on | 12298 (3174) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Tw_S2_S` | on | 11552 (2970) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Tw_S2_W` | on | 15729 (4091) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Tw_S3_E` | on | 10970 (2752) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Tw_S3_N` | on | 7319 (1842) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Tw_S3_S` | on | 7869 (1977) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Tw_S3_S_BrokenSW` | on | 8444 (1999) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Tw_S3_W` | on | 10728 (2701) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Tw_S3_W_BrokenSW` | on | 11274 (2818) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Tw_ShaftBase_420x420x450` | on | 6934 (1956) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble, MAT_Wood -> MI_Chapel_Wood_Old | none |
| `SM_LB_Tw_ShaftPost_20x20x2015` | on | 184 (184) | MAT_Wood -> MI_Chapel_Wood_Old, MAT_Iron -> MI_Crypt_Iron | none |
| `SM_LB_Tw_StairFlight_250x420` | on | 968 (274) | MAT_Wood -> MI_Chapel_Wood_Old, MAT_Iron -> MI_Crypt_Iron | none |
| `SM_LB_Tw_StairFlight_250x420_BrokenA` | on | 1196 (298) | MAT_Wood -> MI_Chapel_Wood_Old, MAT_Iron -> MI_Crypt_Iron | none |
| `SM_LB_Tw_StairFlight_250x420_BrokenB` | on | 1196 (298) | MAT_Wood -> MI_Chapel_Wood_Old, MAT_Iron -> MI_Crypt_Iron | none |
| `SM_LB_Tw_StairFlight_250x420_Closed` | on | 1320 (358) | MAT_Wood -> MI_Chapel_Wood_Old | none |
| `SM_LB_Tw_TopRail_420` | on | 308 (252) | MAT_Wood -> MI_Chapel_Wood_Old | none |
| `SM_LB_Tw_TopRail_670` | on | 396 (256) | MAT_Wood -> MI_Chapel_Wood_Old | none |
| `SM_LB_Cl_ArcadeArch_120x80` | on | 898 (434) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Cl_ArcadeArch_170x80` | on | 1146 (592) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim | none |
| `SM_LB_Cl_ArcadeArch_220x80` | on | 1370 (650) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Cl_ArcadeArch_270x80` | on | 1672 (738) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim | none |
| `SM_LB_Cl_Archway_300x40x1300` | on | 3479 (865) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Cl_Archway_500x40x1300` | on | 5156 (1241) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Cl_CellDoorFrame_150x270` | on | 656 (430) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Prop_Wood_Weathered | none |
| `SM_LB_Cl_GarthBed_1100x800` | on | 13280 (898) | MAT_Earth -> MI_Prop_Earth | none |
| `SM_LB_Cl_GarthCross_350` | on | 248 (248) | MAT_Trim -> MI_Kit_Trim | none |
| `SM_LB_Cl_GarthWall_1100x100` | on | 878 (424) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Cl_GarthWall_800x100` | on | 678 (390) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Cl_GraveCross_60` | on | 70 (70) | MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Cl_GraveSlab_200x80` | on | 152 (152) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Cl_LeanTo_1000x1050` | on | 21516 (14674) | MAT_Slate -> MI_Kit_Slate, MAT_Wood -> MI_Prop_Wood_Weathered | none |
| `SM_LB_Cl_LeanTo_1000x1050_Hole` | on | 12324 (8722) | MAT_Slate -> MI_Kit_Slate, MAT_Wood -> MI_Prop_Wood_Weathered | none |
| `SM_LB_Cl_PierCorner_130x80x640` | on | 898 (496) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Cl_Pier_80x80x640` | on | 788 (498) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim | none |
| `SM_LB_Cl_StairHouseGable_380x40x650` | on | 1896 (620) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Cl_StairHouseRoof_420x640` | on | 8336 (5944) | MAT_Slate -> MI_Kit_Slate, MAT_Wood -> MI_Prop_Wood_Weathered | none |
| `SM_LB_Cl_Vault_Barrel_570x980` | on | 3012 (376) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim | none |
| `SM_LB_Cl_Vault_Barrel_770x640` | on | 3012 (408) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim | none |
| `SM_LB_Cl_Vault_Barrel_770x640_Broken` | on | 3304 (598) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Cl_Vault_Barrel_770x980` | on | 3012 (394) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim | none |
| `SM_LB_Cl_Vault_Barrel_830x640` | on | 3012 (394) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim | none |
| `SM_LB_Cl_Vault_Groin_570x770` | on | 17864 (844) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim | none |
| `SM_LB_Cl_Vault_Groin_570x830` | on | 18288 (826) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim | none |
| `SM_LB_Cl_Vault_Groin_770x770` | on | 16516 (1018) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim | none |
| `SM_LB_Cl_Vault_Groin_770x830` | on | 17816 (874) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim | none |
| `SM_LB_Cl_Wall40_100x1300` | on | 918 (426) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim | none |
| `SM_LB_Cl_Wall40_100x450` | on | 280 (262) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim | none |
| `SM_LB_Cl_Wall40_100x800` | on | 512 (454) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim | none |
| `SM_LB_Cl_Wall40_400x1300_A` | on | 3880 (1152) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Cl_Wall40_400x1300_B` | on | 3706 (1060) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Cl_Wall40_400x450` | on | 1476 (686) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Cl_Wall40_400x800_A` | on | 2478 (782) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Cl_Wall40_400x800_B` | on | 2444 (814) | MAT_Masonry -> MI_Kit_Masonry, MAT_Trim -> MI_Kit_Trim, MAT_Rubble -> MI_Kit_Rubble | none |
| `SM_LB_Prop_BellPlaque_A` | off | 220 (220) | MAT_Trim -> MI_Kit_Trim | none |
| `SM_LB_Prop_InscriptionTablet_A` | off | 220 (220) | MAT_Trim -> MI_Kit_Trim | none |
| `SM_LB_Prop_SmallBellBracket_A` | off | 892 (892) | MAT_Iron -> MI_Crypt_Iron, MAT_Wood -> MI_Prop_Wood_Weathered | none |
| `SM_LB_Prop_SmallBell_A` | off | 1628 (1628) | MAT_Bronze -> MI_LB_BellBronze, MAT_Iron -> MI_Crypt_Iron, MAT_Band -> MI_LB_BellBand_III | 1 convex |

## Notes
- Every mesh package was saved one per `save_assets` call. After the first save of each new mesh the package turned dirty again (probably the asynchronous Nanite/derived-data build finishing). I re-saved all 71 affected packages one by one afterwards; `is_dirty` is false on all 73 meshes, 7 textures and 7 MIs.
- `git status` shows only new (untracked) packages; no pre-existing `.uasset` is modified.
- Regression gate: `Tools/mirror_build_and_test.ps1` built the mirror (exit 0) and ran 78 tests, 78 passed, 0 failures.
