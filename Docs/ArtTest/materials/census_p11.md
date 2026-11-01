# P11-2a census of `L_Monastery`

Generated 2026-11-02T04:22:58 by `Tools/materials/census_p11.py` (read-only). Areas: actor location, first match wins.

## 1. Counts

find_actors **2943**, visible (top-down camera) **2943**, union **2943**; only in the visible set: 0. Actors read in detail: 2741 (classes in the skip list are counted only, so `by area` excludes them). Editor calls in the final pass: 19 (cached results reused; the first full pass took 12475).

| Class | Count | Skipped (count only) |
|---|---|---|
| StaticMeshActor | 2485 |  |
| DecalActor | 126 |  |
| TargetPoint | 80 | yes |
| PointLight | 47 |  |
| TriggerVolume | 36 | yes |
| LBSearchPoint | 29 | yes |
| PCGV | 19 |  |
| LBPatrolPoint | 14 | yes |
| LocalFogVolume | 14 | yes |
| SpotLight | 10 |  |
| LBCheckpoint | 9 | yes |
| BP_Inspectable_Note_C | 6 |  |
| Emitter | 5 | yes |
| PostProcessVolume | 4 | yes |
| BP_PuzzleCandle_C | 4 |  |
| BP_Door_Base_Dungeon_C | 4 |  |
| BP_TagTrigger_C | 4 |  |
| BP_SmallBell_Cloister_C | 4 |  |
| LBWardenSpawnPoint | 3 | yes |
| BP_DialLever_Crypt_C | 3 |  |
| DirectionalLight | 2 | yes |
| BP_WardenSilhouette_C | 2 |  |
| RectLight | 2 |  |
| BP_SequencePuzzle_C | 2 |  |
| WorldSettings | 1 | yes |
| Brush | 1 | yes |
| PlayerStart | 1 | yes |
| SkyAtmosphere | 1 | yes |
| SkyLight | 1 | yes |
| ExponentialHeightFog | 1 | yes |
| BP_KillVolume_C | 1 |  |
| NavMeshBoundsVolume | 1 |  |
| RecastNavMesh-Warden | 1 |  |
| NiagaraActor | 1 |  |
| PCGWorldActor | 1 |  |
| SkeletalMeshActor | 1 |  |
| BP_TagVisibility_CryptGate_C | 1 |  |
| BP_TagVisibility_CryptRubble_C | 1 |  |
| BP_StainedGlassClue_Saints_C | 1 |  |
| BP_EndingTrigger_C | 1 |  |
| BP_RitualMechanism_ChapelBells_C | 1 |  |
| BP_RitualMechanism_CryptWinch_C | 1 |  |
| BP_TagInteractable_ChapelKey_C | 1 |  |
| BP_TagInteractable_CryptCrank_C | 1 |  |
| BP_RitualMechanism_TowerCapstan_C | 1 |  |
| BP_TagInteractable_GreatBell_C | 1 |  |
| BP_Inscription_Cloister_C | 1 |  |
| BP_Warden_C | 1 |  |
| BuoyancyManager | 1 |  |
| DefaultPhysicsVolume | 1 |  |
| GameplayDebuggerPlayerManager | 1 |  |
| ChaosDebugDrawActor | 1 |  |
| AbstractNavData-Default | 1 |  |

| Area | Actors read |
|---|---|
| approach | 69 |
| courtyard | 530 |
| chapel | 421 |
| passage | 69 |
| cloister | 377 |
| tower | 377 |
| crypt | 804 |
| other | 94 |

`other` area: 94 actors. Labels: Ground_1, Ground_2, Ground_3, Ground_5, Ground_6, Perim_E, Perim_S, Perim_N, Window_Ledge, Rock_000, Rock_011, Silh_ChapelWindow, Silh_CourtyardWall, Rail_Up_W, Rail_Up_E, Rail_Up_S, KW_Corner_NE, KW_Corner_SE, KW_ES_00, KW_ES_01, KW_PlES_00, KW_PlES_01, KW_PlES_02, KW_ButtES_0, KW_EN_00, KW_EN_01, KW_PlEN_01, KW_ShortcutDoorway, KW_ShortcutUpper, KW_EN2_02, KW_ButtShortcutS, KW_ButtShortcutN, KW_ButtEN, KE_Floor_1_0, KE_Floor_2_0, KE_Floor_3_0, KE_Floor_4_0, KE_Floor_5_0, Decal_Leak_E0, Ivy_East_Patch_Green_13, Ch_MoonBackdrop, Sa_Wall_W_S, Sa_Ceiling, Sa_Grime_Soot_S_Table, Sa_Grime_Mould_S, CA_Backdrop_South, CA_Wall_W6300_0, CA_Wall_W6300_1, CA_Soffit_Exit, CA_Lintel_Exit, CA_CC_GrateSky, CA_Grate_G1, CA_GrateSky_G1, CA_Grate_G2, CA_GrateSky_G2, CA_Vault_WC_0, CA_Vault_WC_1, CA_Vault_SC_0, CA_Vault_SC_1, CA_Vault_FP_0, CA_Vault_FP_1, CA_Vault_LW_0, CA_Vault_LE_0, CA_Vault_NC_0, CA_Vault_NC_1, CA_Vault_NC_2, CA_Vault_OS_00, CA_Vault_OS_01, CA_Vault_OS_02, CA_Vault_OS_10, CA_Vault_OS_11, CA_Vault_OS_12, CA_CC_Soil, CA_Lining_Ground_1_X10500, CA_Lining_Ground_2_X10800, CD_Roots_CC_0, CD_Roots_CC_1, CD_Roots_CC_2, CD_Roots_FP_0, CD_Roots_FP_1 ...

## 2. Grooved meshes (from `Tools/materials/grooved_meshes.json`)

| Mesh | Groove | Placed | Actors | Hidden | Per area | Source |
|---|---|---|---|---|---|---|
| SM_LB_Kit_Kerb_200x30x40 | vertical_only | 52 | 52 | 0 | courtyard 52 | Tools/blender/kit/build_kit.py:1033-1036 relief_cutters(h_grooves=False, single course) |
| SM_LB_Kit_Trim_Plinth_400x80x60 | vertical_only | 46 | 46 | 0 | courtyard 38, chapel 4, other 4 | Tools/blender/kit/build_kit.py:279-282 relief_cutters(h_grooves=False, single course) |
| SM_LB_Kit_Trim_Plinth_100x80x60 | vertical_only | 24 | 24 | 0 | courtyard 8, chapel 9, passage 7 | Tools/blender/kit/build_kit.py:279-282 relief_cutters(h_grooves=False, single course) |
| SM_LB_Kit_Buttress_100x150x800 | full | 23 | 23 | 0 | courtyard 12, chapel 7, other 4 | Tools/blender/kit/build_kit.py:254 and :265 relief_cutters(defaults) on 3 faces per stage |
| SM_LB_Kit_Wall_400x60x800_A | full | 21 | 21 | 0 | approach 1, courtyard 15, chapel 3, other 2 | Tools/blender/kit/build_kit.py:185 build_wall -> ashlar_body:68 -> relief_both:58-59 -> Tools/blende |
| SM_LB_Kit_Wall_400x60x800_B | full | 20 | 20 | 0 | approach 2, courtyard 14, chapel 2, other 2 | Tools/blender/kit/build_kit.py:185 build_wall -> ashlar_body:68 -> relief_both:58-59 -> Tools/blende |
| SM_LB_Kit_Wall_100x60x800 | full | 18 | 18 | 0 | approach 3, courtyard 5, chapel 5, passage 4, other 1 | Tools/blender/kit/build_kit.py:185 build_wall -> ashlar_body:68 -> relief_both:58-59 -> Tools/blende |
| SM_LB_Kit_Kerb_100x30x40 | vertical_only | 14 | 14 | 0 | courtyard 14 | Tools/blender/kit/build_kit.py:1033-1036 relief_cutters(h_grooves=False, single course) |
| SM_LB_Kit_Kerb_Broken_200x30x40 | vertical_only | 14 | 14 | 0 | courtyard 14 | Tools/blender/kit/build_kit.py:1033-1036 relief_cutters(h_grooves=False, single course) |
| SM_LB_Cl_Wall40_400x1300_A | full | 12 | 12 | 0 | cloister 11, tower 1 | Tools/blender/belltower/build_cloister.py:307 build_wall40 -> Tools/blender/kit/build_kit.py:185 bui |
| SM_LB_Cl_Wall40_400x800_A | full | 10 | 10 | 0 | passage 9, cloister 1 | Tools/blender/belltower/build_cloister.py:307 build_wall40 -> Tools/blender/kit/build_kit.py:185 bui |
| SM_LB_Cl_Pier_80x80x640 | full | 10 | 10 | 0 | cloister 10 | Tools/blender/belltower/build_cloister.py:433 face_relief_xy (called :450 and :467, no vertical/h_gr |
| SM_LB_Kit_Wall_400x60x400 | full | 8 | 8 | 0 | chapel 6, other 2 | Tools/blender/kit/build_kit.py:185 build_wall -> ashlar_body:68 -> relief_both:58-59 -> Tools/blende |
| SM_LB_Cl_Wall40_400x1300_B | full | 8 | 8 | 0 | cloister 8 | Tools/blender/belltower/build_cloister.py:307 build_wall40 -> Tools/blender/kit/build_kit.py:185 bui |
| SM_LB_Cl_Wall40_400x800_B | full | 8 | 8 | 0 | passage 8 | Tools/blender/belltower/build_cloister.py:307 build_wall40 -> Tools/blender/kit/build_kit.py:185 bui |
| SM_LB_Cl_ArcadeArch_220x80 | full | 8 | 8 | 0 | cloister 8 | Tools/blender/belltower/build_cloister.py:489-490 relief_cutters(defaults) |
| SM_LB_Kit_Pier_100x100x500 | horizontal_only | 6 | 6 | 0 | courtyard 6 | Tools/blender/kit/build_kit.py:297 pier_cutters relief_cutters(vertical=False), called build_pier:32 |
| SM_LB_Kit_Wall_400x60x800_Broken | full | 4 | 4 | 0 | courtyard 4 | Tools/blender/kit/build_kit.py:185 build_wall -> ashlar_body:68 -> relief_both:58-59 -> Tools/blende |
| SM_LB_Kit_Window_Lancet_200x60x400_Blind | full | 4 | 4 | 0 | chapel 4 | Tools/blender/kit/build_kit.py:721 relief_both(wmin=55,wmax=100); cap cap_course:727 |
| SM_LB_Kit_Wall_100x60x400 | full | 4 | 4 | 0 | chapel 4 | Tools/blender/kit/build_kit.py:185 build_wall -> ashlar_body:68 -> relief_both:58-59 -> Tools/blende |
| SM_LB_Kit_NaveBay_1000x60x1200 | full | 4 | 4 | 0 | chapel 4 | Tools/blender/kit/build_kit.py:1161 ashlar_body(vary=True) -> relief_both:58-59 -> Tools/blender/kit |
| SM_LB_Cl_Wall40_400x450 | full | 4 | 4 | 0 | cloister 1, other 3 | Tools/blender/belltower/build_cloister.py:307 build_wall40 -> Tools/blender/kit/build_kit.py:185 bui |
| SM_LB_Cl_PierCorner_130x80x640 | full | 4 | 4 | 0 | cloister 4 | Tools/blender/belltower/build_cloister.py:433 face_relief_xy (called :450 and :467, no vertical/h_gr |
| SM_LB_Kit_Doorway_Pointed_400x60x400 | full | 3 | 3 | 0 | chapel 2, other 1 | Tools/blender/kit/build_kit.py:674 relief_both(defaults); cap cap_course:679 |
| SM_LB_Kit_Well_Wall_450x50x250 | full | 2 | 2 | 0 | courtyard 2 | Tools/blender/kit/build_kit.py:185 build_wall(cap=0) -> ashlar_body:68 -> relief_both:58-59 -> Tools |
| SM_LB_Kit_Well_Wall_100x50x250 | full | 2 | 2 | 0 | courtyard 2 | Tools/blender/kit/build_kit.py:185 build_wall(cap=0) -> ashlar_body:68 -> relief_both:58-59 -> Tools |
| SM_LB_Kit_Wall_400x60x400_Broken | full | 2 | 2 | 0 | courtyard 2 | Tools/blender/kit/build_kit.py:185 build_wall -> ashlar_body:68 -> relief_both:58-59 -> Tools/blende |
| SM_LB_Kit_ArcadeBay_1000x60x400 | full | 2 | 2 | 0 | courtyard 2 | Tools/blender/kit/build_kit.py:870-871 relief_cutters(ARC_COURSES, defaults) via build_arcade_intact |
| SM_LB_Kit_ArcadeBay_1000x60x400_BrokenA | full | 2 | 2 | 0 | courtyard 2 | Tools/blender/kit/build_kit.py:870-871 relief_cutters(ARC_COURSES, defaults) via build_arcade_intact |
| SM_LB_Kit_ArcadeBay_1000x60x400_BrokenB | full | 2 | 2 | 0 | courtyard 2 | Tools/blender/kit/build_kit.py:870-871 relief_cutters(ARC_COURSES, defaults) via build_arcade_intact |
| SM_LB_Kit_Gable_1620x60x1015 | full | 2 | 2 | 0 | chapel 2 | Tools/blender/kit/build_kit.py:1268-1269 relief_cutters(defaults) |
| SM_LB_Cl_ArcadeArch_120x80 | full | 2 | 2 | 0 | cloister 2 | Tools/blender/belltower/build_cloister.py:489-490 relief_cutters(defaults) |
| SM_LB_Cl_ArcadeArch_270x80 | full | 2 | 2 | 0 | cloister 2 | Tools/blender/belltower/build_cloister.py:489-490 relief_cutters(defaults) |
| SM_LB_Cl_ArcadeArch_170x80 | full | 2 | 2 | 0 | cloister 2 | Tools/blender/belltower/build_cloister.py:489-490 relief_cutters(defaults) |
| SM_LB_Cl_GarthWall_1100x100 | full | 2 | 2 | 0 | cloister 2 | Tools/blender/belltower/build_cloister.py:534 relief_cutters(defaults, courses unit=22); coping Tool |
| SM_LB_Cl_GarthWall_800x100 | full | 2 | 2 | 0 | cloister 2 | Tools/blender/belltower/build_cloister.py:534 relief_cutters(defaults, courses unit=22); coping Tool |
| SM_LB_Kit_Gate_Arch_1200x300x800 | full | 1 | 1 | 0 | courtyard 1 | Tools/blender/kit/build_kit.py:694-699 relief_cutters(defaults, chips=8); cap cap_course:707 |
| SM_LB_Kit_Well_Wall_350x50x250 | full | 1 | 1 | 0 | courtyard 1 | Tools/blender/kit/build_kit.py:185 build_wall(cap=0) -> ashlar_body:68 -> relief_both:58-59 -> Tools |
| SM_LB_Kit_NaveBay_1000x60x1200_Clue | full | 1 | 1 | 0 | chapel 1 | Tools/blender/kit/build_kit.py:1161 ashlar_body(vary=True) -> relief_both:58-59 -> Tools/blender/kit |
| SM_LB_Kit_NaveBay_1000x60x1200_Door | full | 1 | 1 | 0 | chapel 1 | Tools/blender/kit/build_kit.py:1161 ashlar_body(vary=True) -> relief_both:58-59 -> Tools/blender/kit |
| SM_LB_Kit_EastWall_1620x60x1200 | full | 1 | 1 | 0 | chapel 1 | Tools/blender/kit/build_kit.py:1225 ashlar_body(vary=True) -> relief_both (defaults); cap cap_course |
| SM_LB_Cl_Archway_500x40x1300 | full | 1 | 1 | 0 | cloister 1 | Tools/blender/belltower/build_cloister.py:372 BK.relief_both(defaults); cap Tools/blender/belltower/ |
| SM_LB_Cl_Archway_300x40x1300 | full | 1 | 1 | 0 | cloister 1 | Tools/blender/belltower/build_cloister.py:372 BK.relief_both(defaults); cap Tools/blender/belltower/ |
| SM_LB_Cl_StairHouseGable_380x40x650 | full | 1 | 1 | 0 | other 1 | Tools/blender/belltower/build_cloister.py:1164 BK.relief_both(wmin=70,wmax=150) |
| SM_LB_Tw_S1_W | full | 1 | 1 | 0 | tower 1 | Tools/blender/belltower/tw_walls.py:256 BK.ashlar_body(vary=True) -> relief_both -> Tools/blender/ki |
| SM_LB_Tw_S1_N | full | 1 | 1 | 0 | tower 1 | Tools/blender/belltower/tw_walls.py:256 BK.ashlar_body(vary=True) -> relief_both -> Tools/blender/ki |
| SM_LB_Tw_S1_E | full | 1 | 1 | 0 | tower 1 | Tools/blender/belltower/tw_walls.py:256 BK.ashlar_body(vary=True) -> relief_both -> Tools/blender/ki |
| SM_LB_Tw_S1_S | full | 1 | 1 | 0 | tower 1 | Tools/blender/belltower/tw_walls.py:256 BK.ashlar_body(vary=True) -> relief_both -> Tools/blender/ki |
| SM_LB_Tw_S2_W | full | 1 | 1 | 0 | tower 1 | Tools/blender/belltower/tw_walls.py:256 BK.ashlar_body(vary=True) -> relief_both -> Tools/blender/ki |
| SM_LB_Tw_S2_N | full | 1 | 1 | 0 | tower 1 | Tools/blender/belltower/tw_walls.py:256 BK.ashlar_body(vary=True) -> relief_both -> Tools/blender/ki |
| SM_LB_Tw_S2_E | full | 1 | 1 | 0 | tower 1 | Tools/blender/belltower/tw_walls.py:256 BK.ashlar_body(vary=True) -> relief_both -> Tools/blender/ki |
| SM_LB_Tw_S2_S | full | 1 | 1 | 0 | tower 1 | Tools/blender/belltower/tw_walls.py:256 BK.ashlar_body(vary=True) -> relief_both -> Tools/blender/ki |
| SM_LB_Tw_S3_W_BrokenSW | full | 1 | 1 | 0 | tower 1 | Tools/blender/belltower/tw_walls.py:256 BK.ashlar_body(vary=True) -> relief_both -> Tools/blender/ki |
| SM_LB_Tw_S3_N | full | 1 | 1 | 0 | tower 1 | Tools/blender/belltower/tw_walls.py:256 BK.ashlar_body(vary=True) -> relief_both -> Tools/blender/ki |
| SM_LB_Tw_S3_E | full | 1 | 1 | 0 | tower 1 | Tools/blender/belltower/tw_walls.py:256 BK.ashlar_body(vary=True) -> relief_both -> Tools/blender/ki |
| SM_LB_Tw_S3_S_BrokenSW | full | 1 | 1 | 0 | tower 1 | Tools/blender/belltower/tw_walls.py:256 BK.ashlar_body(vary=True) -> relief_both -> Tools/blender/ki |
| SM_LB_Tw_ShaftBase_420x420x450 | full | 1 | 1 | 0 | tower 1 | Tools/blender/belltower/tw_timber.py:158-159 BK.ashlar_body(vary=True) -> relief_both -> Tools/blend |

Distinct meshes by groove type: full 51 (218 actors, summed over meshes), horizontal_only 1 (6 actors, summed over meshes), none 276 (2505 actors, summed over meshes), vertical_only 5 (150 actors, summed over meshes).
**Grooved (full / vertical_only / horizontal_only): 57 distinct meshes placed, 374 placements, 374 distinct actors.** Full-length source text for every mesh is in `grooved_meshes.json` (`parts` lists body vs cap where they differ; caps and copings are vertical_only).

## 3. `M_LB_Surface` material instances (placed)

| MI | Parent | BaseColorTex | bWorldAlignedUV | WorldTileSizeCm | Slots | Actors | of them hidden | Per area |
|---|---|---|---|---|---|---|---|---|
| MI_Kit_Trim | M_LB_Surface | T_Medieval_Blocks_03_BC | False | 200 | MAT_Masonry, MAT_Trim | 490 | 0 | approach 8, courtyard 235, chapel 67, passage 28, cloister 112, tower 17, other 23 |
| MI_Kit_Rubble | MI_Rock_064 | T_Rock_064_BC | True | 200 | MAT_Rubble, MAT_Stone | 379 | 0 | approach 20, courtyard 204, chapel 37, passage 17, cloister 63, tower 19, other 19 |
| MI_Kit_Masonry | M_LB_Surface | T_Medieval_Blocks_03_BC | True | 200 | MAT_Masonry, MAT_Stone, WorldGridMaterial | 257 | 0 | approach 7, courtyard 80, chapel 29, passage 21, cloister 77, tower 24, other 19 |
| MI_Crypt_Floor | MI_Chapel_Floor | T_Cobblestone_Floor_08_BC | True | 150 | WorldGridMaterial | 179 | 0 | crypt 179 |
| MI_Chapel_Wood_Old | MI_Prop_Wood_Weathered | T_Weathered_Planks_BC | False | 200 | MAT_Wood | 97 | 0 | chapel 44, tower 53 |
| MI_Prop_Wood_Weathered | MI_Weathered_Planks | T_Weathered_Planks_BC | False | 200 | MAT_Rubble, MAT_Wood, WorldGridMaterial | 83 | 0 | courtyard 45, chapel 6, cloister 24, tower 1, crypt 5, other 2 |
| MI_Prop_Earth | MI_Brown_Mud_03_WA | T_Brown_Mud_03_BC | True | 200 | MAT_Earth | 47 | 0 | courtyard 47 |
| MI_Crypt_StoneWA | M_LB_Surface | T_Medieval_Blocks_03_BC | True | 220 | MAT_Stone | 42 | 0 | chapel 6, crypt 29, other 7 |
| MI_Crypt_Iron | MI_Prop_Iron_Rusty | T_Rusty_Metal_04_BC | False | 200 | MAT_Iron, MI_Torch, WorldGridMaterial | 37 | 0 | passage 2, cloister 5, tower 24, crypt 5, other 1 |
| MI_Env_Floor_Puddled | MI_Kit_Floor | T_Cobblestone_Floor_08_BC | True | 150 | MAT_Masonry | 36 | 0 | approach 6, courtyard 25, other 5 |
| MI_Kit_Slate | M_LB_Surface | T_LB_RoofSlates_diff | False | 200 | MAT_Slate | 33 | 0 | chapel 14, cloister 13, tower 5, other 1 |
| MI_Ivy_Stem | MI_Prop_Wood_Weathered | T_Weathered_Planks_BC | False | 200 | MAT_Stem | 32 | 0 | courtyard 22, chapel 5, cloister 4, other 1 |
| MI_Crypt_Wood_Wet | MI_Prop_Wood_Weathered | T_Weathered_Planks_BC | False | 200 | MAT_Wood | 27 | 0 | crypt 27 |
| MI_Wooden_Lantern_01 | M_LB_Surface | T_Wooden_Lantern_01_BC | False | 200 | wooden_lantern_01 | 18 | 0 | courtyard 7, passage 2, cloister 3, tower 5, other 1 |
| MI_Wooden_Lantern_01_Glass | M_LB_Surface | WhiteSquareTexture | False | 200 | wooden_lantern_01_glass | 18 | 0 | courtyard 7, passage 2, cloister 3, tower 5, other 1 |
| MI_Chapel_Masonry_Interior | MI_Kit_Masonry | T_Medieval_Blocks_03_BC | True | 200 | MAT_Masonry | 17 | 0 | chapel 16, other 1 |
| MI_Env_Boulder | MI_Rock_Moss_Set_01 | T_Rock_Moss_Set_01_BC | False | 200 | rock_moss_set_01 | 17 | 0 | approach 17 |
| MI_Kit_Cliff | MI_Rock_064 | T_Rock_064_BC | True | 400 | MAT_Masonry | 17 | 0 | approach 17 |
| MI_Chapel_Rubble | MI_Kit_Rubble | T_Rock_064_BC | True | 200 | MAT_Rubble | 15 | 0 | chapel 15 |
| MI_Chapel_Floor_Dirty | MI_Chapel_Floor | T_Tiles139_BC | True | 360 | MAT_Masonry | 10 | 0 | chapel 4, cloister 5, tower 1 |
| MI_Prop_Stone_Grave | MI_Rock_064_WA | T_Rock_064_BC | True | 120 | MAT_Stone | 9 | 0 | courtyard 9 |
| MI_CC0_DryBranchesMedium01 | M_LB_Surface | T_CC0_DryBranchesMedium01_BC | False | 200 | dry_branches_medium_01 | 8 | 0 | courtyard 5, chapel 3 |
| MI_Chapel_Trim_Dusty | MI_Kit_Trim | T_Medieval_Blocks_03_BC | False | 200 | MAT_Trim | 8 | 0 | chapel 8 |
| MI_Env_TowerStone | MI_Kit_Masonry | T_Medieval_Blocks_03_BC | True | 200 | WorldGridMaterial | 7 | 7 | tower 7 |
| MI_Kit_Floor | MI_Cobblestone_Floor_08 | T_Cobblestone_Floor_08_BC | True | 150 | WorldGridMaterial | 7 | 0 | courtyard 1, cloister 1, other 5 |
| MI_Chapel_PaperOld | MI_LB_Paper | T_LB_Parchment_Rot90 | False | 200 | lambert1 | 6 | 0 | chapel 6 |
| MI_Crypt_RootBark | MI_CC0_DeadTreeTrunk | T_CC0_DeadTreeTrunk_BC | False | 200 | MAT_Bark | 6 | 0 | other 6 |
| MI_LB_Paper | M_LB_Surface | T_LB_Parchment_Rot90 | False | 200 | WorldGridMaterial | 6 | 0 | approach 1, chapel 2, cloister 1, crypt 2 |
| MI_Cl_CarveDirt | MI_Kit_Trim | T_Medieval_Blocks_03_BC | False | 200 | MAT_Carve | 5 | 0 | cloister 4, tower 1 |
| MI_LB_BellBronze | M_LB_Surface | T_Metal058B_BC | False | 200 | MAT_Bronze | 5 | 0 | cloister 4, tower 1 |
| MI_Wooden_Crate_01 | M_LB_Surface | T_Wooden_Crate_01_BC | False | 200 | wooden_crate_01 | 4 | 0 | approach 1, courtyard 3 |
| MI_CC0_RockMossSet02 | M_LB_Surface | T_CC0_RockMossSet02_BC | False | 200 | rock_moss_set_02 | 3 | 0 | courtyard 3 |
| MI_CC0_WineBarrel01 | M_LB_Surface | T_CC0_WineBarrel01_BC | False | 200 | wine_barrel_01 | 3 | 0 | courtyard 3 |
| MI_CC0_WoodenBucket01 | M_LB_Surface | T_CC0_WoodenBucket01_BC | False | 200 | wooden_bucket_01 | 3 | 0 | courtyard 2, cloister 1 |
| MI_Env_Floor_Puddled_Approach | MI_Env_Floor_Puddled | T_Cobblestone_Floor_08_BC | True | 150 | MAT_Masonry | 3 | 0 | approach 3 |
| MI_Gothic_Statue | M_LB_Surface | T_Gothic_Statue_BC | False | 200 | gothic_statue | 3 | 0 | courtyard 1, chapel 2 |
| MI_LB_PaintBone | M_LB_Surface | WhiteSquareTexture | False | 200 | MAT_Paint | 3 | 0 | crypt 3 |
| MI_Wooden_Stool_01 | M_LB_Surface | T_Wooden_Stool_01_BC | False | 200 | wooden_stool_01 | 3 | 0 | courtyard 1, chapel 1, cloister 1 |
| MI_Aged_Bowl | M_LB_Surface | T_Bowl_BC | False | 200 | bowl | 2 | 0 | chapel 2 |
| MI_CC0_DeadTreeTrunk | M_LB_Surface | T_CC0_DeadTreeTrunk_BC | False | 200 | MAT_Bark, dead_tree_trunk | 2 | 0 | courtyard 2 |
| MI_Prop_Charred | MI_Weathered_Planks | T_Weathered_Planks_BC | False | 200 | MAT_Charred | 2 | 0 | courtyard 1, crypt 1 |
| MI_Prop_Iron_Rusty | MI_Rusty_Metal_04 | T_Rusty_Metal_04_BC | False | 200 | MAT_Iron | 2 | 0 | courtyard 2 |
| MI_Prop_Rope | MI_Weathered_Planks | T_Weathered_Planks_BC | False | 200 | MAT_Rope | 2 | 0 | courtyard 2 |
| MI_Weathered_Planks_WA | MI_Weathered_Planks | T_Weathered_Planks_BC | True | 150 | WorldGridMaterial | 2 | 0 | chapel 1, passage 1 |
| MI_Aged_Bread | M_LB_Surface | T_Bread_BC | False | 200 | bread | 1 | 0 | chapel 1 |
| MI_Aged_Bread_Slice | M_LB_Surface | T_Bread_Slice_BC | False | 200 | bread slice | 1 | 0 | chapel 1 |
| MI_Aged_Cup_01 | M_LB_Surface | T_Cup_01_BC | False | 200 | MI_Cup_01 | 1 | 0 | chapel 1 |
| MI_Aged_Cutlery | M_LB_Surface | T_Cutlery_BC | False | 200 | cutlery | 1 | 0 | chapel 1 |
| MI_Aged_Dungeon_bench | M_LB_Surface | T_Dungeon_bench_BC | False | 200 | WorldGridMaterial | 1 | 0 | chapel 1 |
| MI_Aged_Jug | M_LB_Surface | T_Jug_BC | False | 200 | jug | 1 | 0 | chapel 1 |
| MI_Aged_Mug | M_LB_Surface | T_Mug_BC | False | 200 | mug | 1 | 0 | chapel 1 |
| MI_Aged_Pitcher_01 | M_LB_Surface | T_Pitcher_01_BC | False | 200 | MI_Pitcher_01_001 | 1 | 0 | chapel 1 |
| MI_Aged_Plate | M_LB_Surface | T_Plate_BC | False | 200 | plate | 1 | 0 | chapel 1 |
| MI_Aged_Plate_00 | M_LB_Surface | T_Plate_00_BC | False | 200 | Material_010 | 1 | 0 | chapel 1 |
| MI_Aged_Pouch_01 | M_LB_Surface | T_Pouch_01_BC | False | 200 | MI_Pouch_01 | 1 | 0 | chapel 1 |
| MI_Brass_Candleholders_01 | M_LB_Surface | T_Brass_Candleholders_01_BC | False | 200 | brass_candleholders_01 | 1 | 0 | chapel 1 |
| MI_Brass_Candleholders_02 | M_LB_Surface | T_Brass_Candleholders_02_BC | False | 200 | brass_candleholders_02 | 1 | 0 | chapel 1 |
| MI_Brass_Candleholders_03 | M_LB_Surface | T_Brass_Candleholders_03_BC | False | 200 | brass_candleholders_03 | 1 | 0 | chapel 1 |
| MI_Brass_Candleholders_Candles | M_LB_Surface | T_Brass_Candleholders_Candles_BC | False | 200 | brass_candleholders_candles | 1 | 0 | chapel 1 |
| MI_Brass_Candleholders_Flame | M_LB_Surface | T_Brass_Candleholders_Flame_BC | False | 200 | brass_candleholders_flame | 1 | 0 | chapel 1 |
| MI_CC0_DeadTreeTrunk02 | M_LB_Surface | T_CC0_DeadTreeTrunk02_BC | False | 200 | dead_tree_trunk_02 | 1 | 0 | courtyard 1 |
| MI_CC0_PickeDirty01 | M_LB_Surface | T_CC0_PickeDirty01_BC | False | 200 | picke_dirty_01 | 1 | 0 | courtyard 1 |
| MI_CC0_RustedSpade01 | M_LB_Surface | T_CC0_RustedSpade01_BC | False | 200 | rusted_spade_01 | 1 | 0 | courtyard 1 |
| MI_CC0_TreeStump01 | M_LB_Surface | T_CC0_TreeStump01_BC | False | 200 | tree_stump_01 | 1 | 0 | courtyard 1 |
| MI_CC0_WoodenAxe | M_LB_Surface | T_CC0_WoodenAxe_BC | False | 200 | wooden_axe | 1 | 0 | courtyard 1 |
| MI_CC0_WoodenBucket02 | M_LB_Surface | T_CC0_WoodenBucket02_BC | False | 200 | wooden_bucket_02 | 1 | 0 | courtyard 1 |
| MI_CC0_WoodenCandlestick | M_LB_Surface | T_CC0_WoodenCandlestick_BC | False | 200 | wooden_candlestick | 1 | 0 | courtyard 1 |
| MI_CC0_WoodenTable02 | M_LB_Surface | T_CC0_WoodenTable02_BC | False | 200 | wooden_table_02 | 1 | 0 | courtyard 1 |
| MI_Chapel_Floor_Puddled | MI_Chapel_Floor | T_Tiles139_BC | True | 360 | MAT_Masonry | 1 | 0 | cloister 1 |
| MI_Cl_GarthEarth | MI_Prop_Earth | T_Brown_Mud_03_BC | True | 200 | MAT_Earth | 1 | 0 | cloister 1 |
| MI_Cl_TabletStone | M_LB_Surface | T_LB_White_Gray | True | 250 | MAT_Trim | 1 | 0 | tower 1 |
| MI_Crypt_Soil | MI_Prop_Earth | T_Brown_Mud_03_BC | True | 200 | lambert1 | 1 | 0 | other 1 |
| MI_LB_BellBand_I | M_LB_Surface | WhiteSquareTexture | False | 200 | MAT_Band | 1 | 0 | cloister 1 |
| MI_LB_BellBand_II | M_LB_Surface | WhiteSquareTexture | False | 200 | MAT_Band | 1 | 0 | cloister 1 |
| MI_LB_BellBand_III | M_LB_Surface | WhiteSquareTexture | False | 200 | MAT_Band | 1 | 0 | cloister 1 |
| MI_LB_BellBand_IV | M_LB_Surface | WhiteSquareTexture | False | 200 | MAT_Band | 1 | 0 | cloister 1 |
| MI_LB_Rope | M_LB_Surface | T_Rope003_BC | False | 200 | MAT_Rope | 1 | 0 | tower 1 |
| MI_LB_Sally | M_LB_Surface | WhiteSquareTexture | False | 200 | MAT_Sally | 1 | 0 | tower 1 |
| MI_Prop_Key_Iron | MI_Rusty_Metal_04 | T_Rusty_Metal_04_BC | False | 200 | MAT_Iron | 1 | 0 | courtyard 1 |
| MI_Prop_Water | M_LB_Surface | WhiteSquareTexture | False | 200 | MAT_Water | 1 | 0 | courtyard 1 |
| MI_Sacristy_Table_Old | MI_CC0_WoodenTable02 | T_CC0_WoodenTable02_BC | False | 200 | wooden_table_02 | 1 | 0 | chapel 1 |

106 surface MIs exist, 81 are placed (actors counted once per MI). Other placed MIs (root is not M_LB_Surface):

| MI | Root | Mesh actors | of them hidden | Decal actors |
|---|---|---|---|---|
| WorldGridMaterial | /Engine/EngineMaterials/WorldGridMaterial | 252 | 249 | 0 |
| MI_Skeleton_Pile_05 | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Base | 224 | 0 | 0 |
| BasicShapeMaterial | /Engine/BasicShapes/BasicShapeMaterial | 163 | 157 | 0 |
| MI_Foliage_GrassMedium02 | /Game/LastBell/Materials/Master/M_LB_Foliage | 108 | 0 | 0 |
| MI_Stone_01 | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Base | 76 | 0 | 0 |
| MI_Stone_02 | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Base | 76 | 0 | 0 |
| MI_Stone_03 | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Base | 76 | 0 | 0 |
| MI_Stone_00 | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Base | 70 | 0 | 0 |
| MI_Foliage_Fern02 | /Game/LastBell/Materials/Master/M_LB_Foliage | 52 | 0 | 0 |
| MI_Foliage_WeedPlant02 | /Game/LastBell/Materials/Master/M_LB_Foliage | 51 | 0 | 0 |
| MI_Foliage_NettlePlant | /Game/LastBell/Materials/Master/M_LB_Foliage | 49 | 0 | 0 |
| MI_Torture_Devices_Chains | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Base | 35 | 0 | 0 |
| MI_Decal_Mould | /Game/LastBell/Materials/Master/M_LB_Decal_Grime | 0 | 0 | 33 |
| MI_LB_CandleFlame | /Engine/EngineMaterials/EmissiveMeshMaterial | 27 | 0 | 0 |
| MI_Cobweb_Dungeon | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Cobweb | 24 | 0 | 0 |
| MI_Foliage_WildRooibos | /Game/LastBell/Materials/Master/M_LB_Foliage | 22 | 0 | 0 |
| MI_Ivy_Dead | /Game/LastBell/Materials/Master/M_LB_FoliageMasked | 22 | 0 | 0 |
| MI_Stone_Wall_00 | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Tiles | 18 | 0 | 0 |
| MI_Decal_WaxDrips | /Game/LastBell/Materials/Master/M_LB_Decal_Grime | 0 | 0 | 14 |
| MI_Skeleton_Pile_03 | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Base | 14 | 0 | 0 |
| MI_Skeleton_Pile_04 | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Base | 14 | 0 | 0 |
| MI_Decal_Leaking004_Wall | /Game/LastBell/Materials/Master/M_LB_Decal | 0 | 0 | 12 |
| MI_Decal_DustDrift | /Game/LastBell/Materials/Master/M_LB_Decal_Grime | 0 | 0 | 12 |
| MI_LB_Iron | /Engine/BasicShapes/BasicShapeMaterial | 12 | 1 | 0 |
| MI_Candle_Melted_02 | /Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Materials/M_Wax_Base | 12 | 0 | 0 |
| MI_Candle_Melted_05 | /Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Materials/M_Wax_Base | 12 | 0 | 0 |
| MI_Candle_Melted_06 | /Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Materials/M_Wax_Base | 12 | 0 | 0 |
| MI_Candle_Melted_08 | /Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Materials/M_Wax_Base | 12 | 0 | 0 |
| MI_Glass | /Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Materials/M_Glass | 12 | 0 | 0 |
| M_Metal | /Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Materials/M_Metal | 12 | 0 | 0 |
| MI_Skeleton_Pile_01 | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Base | 12 | 0 | 0 |
| MI_Dungeon_chain_holder | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Props | 11 | 0 | 0 |
| MI_Ivy_Green | /Game/LastBell/Materials/Master/M_LB_FoliageMasked | 10 | 0 | 0 |
| MI_Dungeon_door | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Props | 9 | 0 | 0 |
| MI_Decal_WaterStain | /Game/LastBell/Materials/Master/M_LB_Decal_Grime | 0 | 0 | 8 |
| MI_Chapel_DampStreak | /Game/LastBell/Materials/Master/M_LB_Decal | 0 | 0 | 7 |
| MI_LightShaft_Crypt | /Game/LastBell/Materials/Master/M_LB_LightShaft | 7 | 0 | 0 |
| MI_Decal_Soot_B | /Game/LastBell/Materials/Master/M_LB_Decal_Grime | 0 | 0 | 7 |
| MI_Decal_Leaking006_Wall | /Game/LastBell/Materials/Master/M_LB_Decal | 0 | 0 | 6 |
| MI_Foliage_SearsiaLucida | /Game/LastBell/Materials/Master/M_LB_Foliage | 6 | 0 | 0 |
| MI_FX_FogSheet_Ground | /Engine/EngineVolumetrics/Fogsheet/Materials/M_EV_FogSheet_Master_01 | 6 | 0 | 0 |
| MI_Decal_Soot_A | /Game/LastBell/Materials/Master/M_LB_Decal_Grime | 0 | 0 | 6 |
| MI_Crypt_Backdrop | /Game/LastBell/Materials/Master/M_LB_UnlitEmissive | 5 | 0 | 0 |
| MI_LB_DarkWood | /Engine/BasicShapes/BasicShapeMaterial | 5 | 0 | 0 |
| MI_Candle_03 | /Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Materials/M_Wax_Base | 5 | 0 | 0 |
| MI_Candle_Melted_03 | /Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Materials/M_Wax_Base | 5 | 0 | 0 |
| MI_Candle_Melted_07 | /Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Materials/M_Wax_Base | 5 | 0 | 0 |
| MI_Decal_LightPool_Lancet | /Game/LastBell/Materials/Master/M_LB_Decal_LightPool | 0 | 0 | 4 |
| MI_Glass_Lancet_A | /Game/LastBell/Materials/Master/M_LB_StainedGlass | 4 | 0 | 0 |
| MI_LB_Bronze | /Engine/BasicShapes/BasicShapeMaterial | 4 | 0 | 0 |
| MI_LB_CandleWax | /Engine/BasicShapes/BasicShapeMaterial | 4 | 0 | 0 |
| MI_Candle_02 | /Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Materials/M_Wax_Base | 4 | 0 | 0 |
| MI_Candle_Melted_09 | /Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Materials/M_Wax_Base | 4 | 0 | 0 |
| MI_Torch | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Base | 4 | 0 | 0 |
| MI_CarpenterTools | /Game/LastBell/ThirdParty/Fab/MiscProps/Materials/M_Master_PBR | 4 | 0 | 0 |
| MI_Crypt_MoonSky | /Game/LastBell/Materials/Master/M_LB_UnlitEmissive | 3 | 0 | 0 |
| MI_FX_FogSheet_Approach | /Engine/EngineVolumetrics/Fogsheet/Materials/M_EV_FogSheet_Master_01 | 3 | 0 | 0 |
| MI_Decal_LeafLitter_A | /Game/LastBell/Materials/Master/M_LB_Decal_Grime | 0 | 0 | 3 |
| MI_Decal_LeafLitter_B | /Game/LastBell/Materials/Master/M_LB_Decal_Grime | 0 | 0 | 3 |
| MI_LB_WardenSilhouette | /Game/LastBell/Materials/Master/M_LB_Silhouette | 3 | 0 | 0 |
| MI_LightShaft_Window | /Game/LastBell/Materials/Master/M_LB_LightShaft | 3 | 0 | 0 |
| MI_Candle_09 | /Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Materials/M_Wax_Base | 3 | 0 | 0 |
| MI_Candle_Melted_01 | /Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Materials/M_Wax_Base | 3 | 0 | 0 |
| MI_Candle_Melted_04 | /Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Materials/M_Wax_Base | 3 | 0 | 0 |
| MI_Candle_Melted_10 | /Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Materials/M_Wax_Base | 3 | 0 | 0 |
| MI_Pillar_001 | /Game/LastBell/ThirdParty/Fab/OldBrokenPillar/BaseMaterials/M_Base_WallElements | 3 | 0 | 0 |
| MI_Sa_Decal_DustDrift_Strong | /Game/LastBell/Materials/Master/M_LB_Decal_Grime | 0 | 0 | 2 |
| MI_Sa_Decal_WaterStain_Strong | /Game/LastBell/Materials/Master/M_LB_Decal_Grime | 0 | 0 | 2 |
| MI_Decal_ChalkSigil | /Game/LastBell/Materials/Master/M_LB_Decal_Chalk | 0 | 0 | 2 |
| MI_Decal_DragMarks | /Game/LastBell/Materials/Master/M_LB_Decal_Grime | 0 | 0 | 2 |
| MI_Candle_01 | /Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Materials/M_Wax_Base | 2 | 0 | 0 |
| MI_Dungeon_toplock | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Props | 2 | 0 | 0 |
| MI_Pot_00 | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Base_01 | 2 | 0 | 0 |
| MI_Torture_Devices_Cage | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Base | 2 | 0 | 0 |
| MI_Torture_Devices_Rope_00 | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Base | 2 | 0 | 0 |
| MI_Torture_Devices_Shackles_01 | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Base | 2 | 0 | 0 |
| M_Dead_man | /Game/LastBell/ThirdParty/Fab/HorrorProps/Materials/M_Dead_man | 2 | 0 | 0 |
| M_Man_under_cloth | /Game/LastBell/ThirdParty/Fab/HorrorProps/Materials/M_Man_under_cloth | 2 | 0 | 0 |
| MI_Glass_Clue_Saints | /Game/LastBell/Materials/Master/M_LB_StainedGlass | 1 | 0 | 0 |
| MI_Sa_Decal_WaxDrips_Strong | /Game/LastBell/Materials/Master/M_LB_Decal_Grime | 0 | 0 | 1 |
| MI_Env_NightSky | /Engine/EngineSky/M_Sky_Panning_Clouds2 | 1 | 0 | 0 |
| MI_Crypt_Water_Flood_E | /Game/LastBell/Materials/Master/M_LB_Water | 1 | 0 | 0 |
| MI_Crypt_Water_Flood_Ledge | /Game/LastBell/Materials/Master/M_LB_Water | 1 | 0 | 0 |
| MI_Crypt_Water_Flood_W | /Game/LastBell/Materials/Master/M_LB_Water | 1 | 0 | 0 |
| MI_Crypt_Water_Pit | /Game/LastBell/Materials/Master/M_LB_Water | 1 | 0 | 0 |
| MID_MI_LB_StainedGlass_0 | /Engine/EngineMaterials/EmissiveMeshMaterial | 1 | 0 | 0 |
| MID_MI_LB_StainedGlass_0 | /Engine/EngineMaterials/EmissiveMeshMaterial | 1 | 0 | 0 |
| MID_MI_LB_StainedGlass_0 | /Engine/EngineMaterials/EmissiveMeshMaterial | 1 | 0 | 0 |
| MID_MI_LB_StainedGlass_0 | /Engine/EngineMaterials/EmissiveMeshMaterial | 1 | 0 | 0 |
| MI_Decal_ChalkCircle | /Game/LastBell/Materials/Master/M_LB_Decal_Chalk | 0 | 0 | 1 |
| MI_Decal_ChalkTally | /Game/LastBell/Materials/Master/M_LB_Decal_Chalk | 0 | 0 | 1 |
| MI_Glass_Broken | /Game/LastBell/Materials/Master/M_LB_StainedGlass | 1 | 0 | 0 |
| MI_Glass_East | /Game/LastBell/Materials/Master/M_LB_StainedGlass_Translucent | 1 | 0 | 0 |
| MI_Glass_Lancet_B | /Game/LastBell/Materials/Master/M_LB_StainedGlass | 1 | 0 | 0 |
| MI_LB_MoonBackdrop | /Game/LastBell/Materials/Master/M_LB_UnlitEmissive | 1 | 0 | 0 |
| MI_LB_StainedGlass | /Engine/EngineMaterials/EmissiveMeshMaterial | 1 | 0 | 0 |
| MI_LB_WardenMask | /Engine/BasicShapes/BasicShapeMaterial | 1 | 0 | 0 |
| MI_LightShaft_Roof | /Game/LastBell/Materials/Master/M_LB_LightShaft | 1 | 0 | 0 |
| MI_Candles_Holder_02 | /Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Materials/M_Base | 1 | 0 | 0 |
| MI_Candles_Holder_03 | /Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Materials/M_Base | 1 | 0 | 0 |
| MI_Candles_Holder_04 | /Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Materials/M_Base | 1 | 0 | 0 |
| MI_Dungeon_bowl | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Props | 1 | 0 | 0 |
| MI_Dungeon_chest | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Props | 1 | 0 | 0 |
| MI_Dungeon_shackles_00 | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Props | 1 | 0 | 0 |
| MI_Dungeon_shackles_01 | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Props | 1 | 0 | 0 |
| MI_Metal_Bars | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Base | 1 | 0 | 0 |
| MI_Skeleton_Pile_00 | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Base | 1 | 0 | 0 |
| MI_Skeleton_Pile_05_Pole | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Base | 1 | 0 | 0 |
| MI_Torture_Devices_Breaking_Wheel | /Game/LastBell/ThirdParty/Fab/Dungeon/Materials/M_Base | 1 | 0 | 0 |
| MI_Anvil | /Game/LastBell/ThirdParty/Fab/MiscProps/Materials/M_Master_PBR | 1 | 0 | 0 |
| MI_Chest | /Game/LastBell/ThirdParty/Fab/MiscProps/Materials/M_Master_PBR | 1 | 0 | 0 |
| MI_Trunk | /Game/LastBell/ThirdParty/Fab/MiscProps/Materials/M_Master_PBR | 1 | 0 | 0 |

## 4. Textures per placed surface MI

| Texture | Param | MIs | MIs (actors) | Painted joints? |
|---|---|---|---|---|
| WhiteSquareTexture | BaseColorTex | 8 | MI_Wooden_Lantern_01_Glass (18), MI_LB_PaintBone (3), MI_LB_BellBand_I (1), MI_LB_BellBand_II (1), MI_LB_BellBand_III (1), MI_LB_BellBand_IV (1), MI_LB_Sally (1), MI_Prop_Water (1) | check by eye |
| T_Medieval_Blocks_03_ARM | ARMTex | 7 | MI_Kit_Trim (490), MI_Kit_Masonry (257), MI_Crypt_StoneWA (42), MI_Chapel_Masonry_Interior (17), MI_Chapel_Trim_Dusty (8), MI_Env_TowerStone (7), MI_Cl_CarveDirt (5) | same set as T_Medieval_Blocks_03, check by eye |
| T_Medieval_Blocks_03_BC | BaseColorTex | 7 | MI_Kit_Trim (490), MI_Kit_Masonry (257), MI_Crypt_StoneWA (42), MI_Chapel_Masonry_Interior (17), MI_Chapel_Trim_Dusty (8), MI_Env_TowerStone (7), MI_Cl_CarveDirt (5) | painted block joints (stated in the plan) |
| T_Medieval_Blocks_03_N | NormalTex | 7 | MI_Kit_Trim (490), MI_Kit_Masonry (257), MI_Crypt_StoneWA (42), MI_Chapel_Masonry_Interior (17), MI_Chapel_Trim_Dusty (8), MI_Env_TowerStone (7), MI_Cl_CarveDirt (5) | same set as T_Medieval_Blocks_03, check by eye |
| T_Weathered_Planks_BC | BaseColorTex | 7 | MI_Chapel_Wood_Old (97), MI_Prop_Wood_Weathered (83), MI_Ivy_Stem (32), MI_Crypt_Wood_Wet (27), MI_Prop_Charred (2), MI_Prop_Rope (2), MI_Weathered_Planks_WA (2) | check by eye |
| T_Rock_064_BC | BaseColorTex | 4 | MI_Kit_Rubble (379), MI_Kit_Cliff (17), MI_Chapel_Rubble (15), MI_Prop_Stone_Grave (9) | check by eye |
| T_Cobblestone_Floor_08_BC | BaseColorTex | 4 | MI_Crypt_Floor (179), MI_Env_Floor_Puddled (36), MI_Kit_Floor (7), MI_Env_Floor_Puddled_Approach (3) | check by eye |
| T_Brown_Mud_03_BC | BaseColorTex | 3 | MI_Prop_Earth (47), MI_Cl_GarthEarth (1), MI_Crypt_Soil (1) | check by eye |
| T_Rusty_Metal_04_BC | BaseColorTex | 3 | MI_Crypt_Iron (37), MI_Prop_Iron_Rusty (2), MI_Prop_Key_Iron (1) | check by eye |
| T_Tiles139_BC | BaseColorTex | 2 | MI_Chapel_Floor_Dirty (10), MI_Chapel_Floor_Puddled (1) | check by eye |
| T_LB_Parchment_Rot90 | BaseColorTex | 2 | MI_Chapel_PaperOld (6), MI_LB_Paper (6) | check by eye |
| T_CC0_DeadTreeTrunk_BC | BaseColorTex | 2 | MI_Crypt_RootBark (6), MI_CC0_DeadTreeTrunk (2) | check by eye |
| T_CC0_WoodenTable02_BC | BaseColorTex | 2 | MI_CC0_WoodenTable02 (1), MI_Sacristy_Table_Old (1) | check by eye |
| T_LB_RoofSlates_diff | BaseColorTex | 1 | MI_Kit_Slate (33) | check by eye |
| T_Wooden_Lantern_01_BC | BaseColorTex | 1 | MI_Wooden_Lantern_01 (18) | check by eye |
| T_Rock_Moss_Set_01_BC | BaseColorTex | 1 | MI_Env_Boulder (17) | check by eye |
| T_CC0_DryBranchesMedium01_BC | BaseColorTex | 1 | MI_CC0_DryBranchesMedium01 (8) | check by eye |
| T_Metal058B_BC | BaseColorTex | 1 | MI_LB_BellBronze (5) | check by eye |
| T_Wooden_Crate_01_BC | BaseColorTex | 1 | MI_Wooden_Crate_01 (4) | check by eye |
| T_CC0_RockMossSet02_BC | BaseColorTex | 1 | MI_CC0_RockMossSet02 (3) | check by eye |
| T_CC0_WineBarrel01_BC | BaseColorTex | 1 | MI_CC0_WineBarrel01 (3) | check by eye |
| T_CC0_WoodenBucket01_BC | BaseColorTex | 1 | MI_CC0_WoodenBucket01 (3) | check by eye |
| T_Gothic_Statue_BC | BaseColorTex | 1 | MI_Gothic_Statue (3) | check by eye |
| T_Wooden_Stool_01_BC | BaseColorTex | 1 | MI_Wooden_Stool_01 (3) | check by eye |
| T_Bowl_BC | BaseColorTex | 1 | MI_Aged_Bowl (2) | check by eye |
| T_Bread_BC | BaseColorTex | 1 | MI_Aged_Bread (1) | check by eye |
| T_Bread_Slice_BC | BaseColorTex | 1 | MI_Aged_Bread_Slice (1) | check by eye |
| T_Cup_01_BC | BaseColorTex | 1 | MI_Aged_Cup_01 (1) | check by eye |
| T_Cutlery_BC | BaseColorTex | 1 | MI_Aged_Cutlery (1) | check by eye |
| T_Dungeon_bench_BC | BaseColorTex | 1 | MI_Aged_Dungeon_bench (1) | check by eye |
| T_Jug_BC | BaseColorTex | 1 | MI_Aged_Jug (1) | check by eye |
| T_Mug_BC | BaseColorTex | 1 | MI_Aged_Mug (1) | check by eye |
| T_Pitcher_01_BC | BaseColorTex | 1 | MI_Aged_Pitcher_01 (1) | check by eye |
| T_Plate_BC | BaseColorTex | 1 | MI_Aged_Plate (1) | check by eye |
| T_Plate_00_BC | BaseColorTex | 1 | MI_Aged_Plate_00 (1) | check by eye |
| T_Pouch_01_BC | BaseColorTex | 1 | MI_Aged_Pouch_01 (1) | check by eye |
| T_Brass_Candleholders_01_BC | BaseColorTex | 1 | MI_Brass_Candleholders_01 (1) | check by eye |
| T_Brass_Candleholders_02_BC | BaseColorTex | 1 | MI_Brass_Candleholders_02 (1) | check by eye |
| T_Brass_Candleholders_03_BC | BaseColorTex | 1 | MI_Brass_Candleholders_03 (1) | check by eye |
| T_Brass_Candleholders_Candles_BC | BaseColorTex | 1 | MI_Brass_Candleholders_Candles (1) | check by eye |
| T_Brass_Candleholders_Flame_BC | BaseColorTex | 1 | MI_Brass_Candleholders_Flame (1) | check by eye |
| T_CC0_DeadTreeTrunk02_BC | BaseColorTex | 1 | MI_CC0_DeadTreeTrunk02 (1) | check by eye |
| T_CC0_PickeDirty01_BC | BaseColorTex | 1 | MI_CC0_PickeDirty01 (1) | check by eye |
| T_CC0_RustedSpade01_BC | BaseColorTex | 1 | MI_CC0_RustedSpade01 (1) | check by eye |
| T_CC0_TreeStump01_BC | BaseColorTex | 1 | MI_CC0_TreeStump01 (1) | check by eye |
| T_CC0_WoodenAxe_BC | BaseColorTex | 1 | MI_CC0_WoodenAxe (1) | check by eye |
| T_CC0_WoodenBucket02_BC | BaseColorTex | 1 | MI_CC0_WoodenBucket02 (1) | check by eye |
| T_CC0_WoodenCandlestick_BC | BaseColorTex | 1 | MI_CC0_WoodenCandlestick (1) | check by eye |
| T_LB_White_Gray | BaseColorTex | 1 | MI_Cl_TabletStone (1) | check by eye |
| T_Rope003_BC | BaseColorTex | 1 | MI_LB_Rope (1) | check by eye |

## 5. Decals

Total decal actors: **126**.

| Decal MI | Count | Per area |
|---|---|---|
| MI_Decal_Mould | 33 | chapel 16, cloister 5, crypt 11, other 1 |
| MI_Decal_WaxDrips | 14 | chapel 10, crypt 4 |
| MI_Decal_DustDrift | 12 | chapel 8, crypt 4 |
| MI_Decal_Leaking004_Wall | 12 | cloister 3, crypt 9 |
| MI_Decal_WaterStain | 8 | chapel 4, crypt 4 |
| MI_Decal_Soot_B | 7 | chapel 5, crypt 1, other 1 |
| MI_Chapel_DampStreak | 7 | chapel 7 |
| MI_Decal_Leaking006_Wall | 6 | courtyard 5, other 1 |
| MI_Decal_Soot_A | 6 | chapel 4, crypt 2 |
| MI_Decal_LightPool_Lancet | 4 | chapel 4 |
| MI_Decal_LeafLitter_A | 3 | chapel 3 |
| MI_Decal_LeafLitter_B | 3 | chapel 3 |
| MI_Decal_ChalkSigil | 2 | chapel 2 |
| MI_Decal_DragMarks | 2 | chapel 2 |
| MI_Sa_Decal_WaterStain_Strong | 2 | chapel 2 |
| MI_Sa_Decal_DustDrift_Strong | 2 | chapel 2 |
| MI_Decal_ChalkCircle | 1 | chapel 1 |
| MI_Decal_ChalkTally | 1 | chapel 1 |
| MI_Sa_Decal_WaxDrips_Strong | 1 | chapel 1 |

## 6. Lanterns

Lantern placements: **18**; with no light within 60 cm: **0**. Distance is light location to the closest point of the lantern actor's bounds (0 if inside).

Glass material `MI_Wooden_Lantern_01_Glass`: chain MI_Wooden_Lantern_01_Glass > M_LB_Surface; root M_LB_Surface; BaseColorTex WhiteSquareTexture; own overrides: {"scalars": {"MacroStrength": 0, "RoughnessMin": 0.05000000074505806, "RoughnessMax": 0.05000000074505806}, "textures": {}, "vectors": {"BaseColorTint": [0.05999999865889549, 0.07999999821186066, 0.09000000357627869, 1]}}.

| Label | Area | Mesh | Glass material (slot) | Nearest light | Distance cm | Flag |
|---|---|---|---|---|---|---|
| KP_Lantern_Gate | courtyard | SM_Wooden_Lantern_01 | MI_Wooden_Lantern_01_Glass (wooden_lantern_01_glass) | Light_Gatehouse_Warm | 6.9 |  |
| KP_Lantern_Well | courtyard | SM_Wooden_Lantern_01 | MI_Wooden_Lantern_01_Glass (wooden_lantern_01_glass) | Light_Well_Warm | 0.0 |  |
| KP_Lantern_ChapelDoor | courtyard | SM_Wooden_Lantern_01 | MI_Wooden_Lantern_01_Glass (wooden_lantern_01_glass) | Light_ChapelDoor_Warm | 1.4 |  |
| Garden_Lantern | courtyard | SM_Wooden_Lantern_01 | MI_Wooden_Lantern_01_Glass (wooden_lantern_01_glass) | Light_WellHead_Warm | 16.9 |  |
| KP_Lantern_Route_1 | courtyard | SM_Wooden_Lantern_01 | MI_Wooden_Lantern_01_Glass (wooden_lantern_01_glass) | Light_Route_Lantern_1 | 13.3 |  |
| KP_Lantern_Route_2 | courtyard | SM_Wooden_Lantern_01 | MI_Wooden_Lantern_01_Glass (wooden_lantern_01_glass) | Light_Route_Lantern_2 | 0.0 |  |
| KP_Lantern_Route_3 | courtyard | SM_Wooden_Lantern_01 | MI_Wooden_Lantern_01_Glass (wooden_lantern_01_glass) | Light_Route_Lantern_3 | 0.0 |  |
| CLA_Lantern_Bells | cloister | SM_Wooden_Lantern_01 | MI_Wooden_Lantern_01_Glass (wooden_lantern_01_glass) | L_Cl_Bells | 0.0 |  |
| CLA_Lantern_Door | cloister | SM_Wooden_Lantern_01 | MI_Wooden_Lantern_01_Glass (wooden_lantern_01_glass) | L_Cl_Door | 0.0 |  |
| SHA_Lantern_Entry | other | SM_Wooden_Lantern_01 | MI_Wooden_Lantern_01_Glass (wooden_lantern_01_glass) | L_Cl_Entry | 0.0 |  |
| PSA_Lantern | passage | SM_Wooden_Lantern_01 | MI_Wooden_Lantern_01_Glass (wooden_lantern_01_glass) | L_Ps_Lantern | 0.0 |  |
| PSA_Lantern_W | passage | SM_Wooden_Lantern_01 | MI_Wooden_Lantern_01_Glass (wooden_lantern_01_glass) | L_Ps_West | 0.0 |  |
| CLA_Lantern_West | cloister | SM_Wooden_Lantern_01 | MI_Wooden_Lantern_01_Glass (wooden_lantern_01_glass) | L_Cl_West | 0.0 |  |
| TWA_Lantern_Base | tower | SM_Wooden_Lantern_01 | MI_Wooden_Lantern_01_Glass (wooden_lantern_01_glass) | L_Tw_Base | 0.0 |  |
| TWA_Lantern_Land4 | tower | SM_Wooden_Lantern_01 | MI_Wooden_Lantern_01_Glass (wooden_lantern_01_glass) | L_Tw_Land4 | 0.0 |  |
| TWA_Lantern_Land7 | tower | SM_Wooden_Lantern_01 | MI_Wooden_Lantern_01_Glass (wooden_lantern_01_glass) | L_Tw_Land7 | 0.0 |  |
| TWA_Lantern_Land10 | tower | SM_Wooden_Lantern_01 | MI_Wooden_Lantern_01_Glass (wooden_lantern_01_glass) | L_Tw_Land10 | 0.0 |  |
| TWA_Lantern_Bell | tower | SM_Wooden_Lantern_01 | MI_Wooden_Lantern_01_Glass (wooden_lantern_01_glass) | L_Tw_Bell | 0.0 |  |

## 7. Errors and surprises

Errors: **0** (0.00 % of 2741 actors read).

- Map dirty before / after: False / False. PIE running after: False. Camera:  camera restore: moved 0.0000 cm, rotation delta 0.0000 deg
- Area rules overlap: 25 placements sit at X 11990-12040, Y 1490-2510, which matches both `tower` and `cloister`; first match gives `tower` (e.g. the BP_Inscription_Cloister tablet at X 11995). Labels: CLA_LanternBracket_Bells, CLA_LanternBracket_Door, CLA_Mech3_Chain_B_0, CLA_Mech3_Chain_B_1, CLA_Mech3_Eyelet, CLA_Mech3_LatchBox, CLA_Wall_E_S_0, Clue_Inscription, Door_Tower, TWA_BelfryFloor, TWA_Floor, TWA_LanternBracket_Base, TWA_Louvre_W1, TWA_Louvre_W2, TWA_S1_N, TWA_S1_W, TWA_S2_N, TWA_S2_W, TWA_S3_N, TWA_S3_W, Tw_W_Lintel, Tw_W_N, Tw_W_S
- StaticMeshActors hidden in game (bVisible false or bHiddenInGame): **414** of 2485. Largest groups: Stair_F (Cube, tower) x154; Rail_F (Cube, tower) x77; Stair_SacristyDown (Cube, crypt) x40; Stair_CryptUp (Cube, crypt) x40; Rock (Cube, crypt) x14; Tw_Landing (Cube, tower) x10; Prop_Crypt (Cube, crypt) x6; Arc_S (Cube, cloister) x5; Arc_N (Cube, cloister) x5; CryptFloor (Cube, crypt) x4; Tw_Block_BrokenTread_F (Cube, tower) x3; Rock (Cube, other) x2
- Of those, 249 use the engine `WorldGridMaterial`; visible StaticMeshActors on `WorldGridMaterial`: 0.
- Dynamic / non-asset materials found in level overrides: MID_MI_LB_StainedGlass_0, MID_MI_LB_StainedGlass_0, MID_MI_LB_StainedGlass_0, MID_MI_LB_StainedGlass_0
