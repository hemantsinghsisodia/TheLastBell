# P15-6: data assets and level work (2026-11-08)
Script: `Tools/fx/p15_level.py` (`--apply [--resume] [--only ...]`, `--check`, `--save`). Branch `claude/phase-15-particles`. PIE never ran; no capture; no suite run (the suite needs Unreal closed, the lead runs it).

## Result summary
| Item | Result |
|---|---|
| Preflight | PIE off, `L_Monastery` not dirty, census **3015** at the start |
| data | PASS: `DA_StormFX` created, 4 soft refs set, the 18 scalar fields, 2 vectors and the `SkyBoltChance` map read back at the C++ defaults, `DebugBolt` -1; `DA_StormSettings.FXSettings` set, 2 strike target tags set, debug fields -1 |
| target | PASS: `FX_StrikeTarget_Tower` (TargetPoint, tag `LB_StrikeTarget_Tower`) at (12530.8, 2000, 4844.8) |
| dust | PASS: 11 `FX_Dust_<shaft>` |
| mist | PASS: `FX_WaterMist_W/E` |
| drips | PASS: 10 `FX_Drip_<tag>` |
| eaves | PASS: 7 `FX_EaveDrips_<id>` |
| fires | PASS: 6 `NS_LB_TorchFire` actors; 5 Cascade `Emitter` actors deleted after the read-back |
| flames | PASS: 22 StaticMeshActors, slot-0 override `MI_Flame_Candle` |
| bpflames | PASS: `Candle_P1..P4` instance overrides; `BP_LBCharacter.CandleFlame` template edited, compiled clean, saved |
| cloth | PASS: 10 `FX_Cloth_<id>` |
| curtains | PASS: 8 `FX_RainCurtain_<id>` |
| Census | **3065** (3015 + 50), as planned |
| `--check` | 100 PASS, 0 FAIL before the save; 118 PASS, 0 FAIL in the `--save` run (the run repeats the whole check, then the saves) |
| Saved | `DA_StormFX`, `DA_StormSettings`, `BP_LBCharacter`, `L_Monastery`, each followed by `is_dirty` = False. Nothing else. None of the 14 never-save packages (including `M_LB_Surface` and `BP_PuzzleCandle`) was dirty before or after. |
| After a reload | `load_level` on the saved map (returned None, map not dirty), then `--check --only data,target,mist,eaves,fires,flames,bpflames,curtains`: 54 PASS, 0 FAIL. This does not prove the call discarded the in-memory world, so the user-parameter and Blueprint-instance overrides are only proven to persist if the lead restarts the editor and runs `--check` again (about 8 minutes). |

## Data
- `DA_StormFX`: `/Script/LastBell.LBStormFXSettings` at `/Game/LastBell/Data/DA_StormFX`. `RainSystem` -> `NS_LB_Rain`, `StrikeSparksSystem` -> `NS_LB_StrikeSparks`, `BoltMesh` -> `SM_LB_FX_BoltCard`, `BoltMaterial` -> `MI_LB_Bolt` (read back). The 18 scalar fields, `RainFallSpeed` (1100, 1400), `SkyBoltLength` (16000, 26000) and `SkyBoltChance` (ambient 0.6, scripted 1, wardenReveal 0.5, apparition 0.5, debug 1) read back at the section 2.2 values. `DebugBolt` = -1.
- `DA_StormSettings`: `FXSettings` -> `DA_StormFX`; `DebugFreezeFlash` -1 and `DebugIntensityOverride` -1.
- `ScriptedStrikes`, the whole array read before and after (6 entries each). The diff is exactly two fields: `[0].strikeTargetTag` (trigger `State.Event.CourtyardEntered`) and `[4].strikeTargetTag` (trigger `State.Event.TowerTop`), both `None` -> `LB_StrikeTarget_Tower`. The before array is in `Saved/p15_6_scratch/strikes_before.json` (scratch, git-ignored); it is:
```
BEFORE (every entry has strikeTargetTag "None", every other field is untouched):
[0] State.Event.CourtyardEntered delay 0.4 count 2 spacing 1.6 brightness 1 Double, bLookGate true lookTarget (12500, 2000, 3800) cone 20 timeout 90
[1] State.Ritual.1               delay 1.2 count 1 spacing 0   brightness 1 Double, bLookGate false
[2] State.Ritual.2               delay 1.2 count 1 spacing 0   brightness 1 Double, bLookGate false
[3] State.Ritual.3               delay 1.2 count 1 spacing 0   brightness 1 Double, bLookGate false
[4] State.Event.TowerTop         delay 2   count 3 spacing 2.5 brightness 1 Double, overrides [Double, Triple, Double], bLookGate false
[5] State.Event.Finale           delay 0.3 count 2 spacing 0.8 brightness 1 Double, bLookGate false
AFTER: identical, except [0].strikeTargetTag = "LB_StrikeTarget_Tower" and [4].strikeTargetTag = "LB_StrikeTarget_Tower".
```

## Blueprint graph check (read-only: `list_graphs`, `find_nodes`, `get_node_infos`; no `read_graph_dsl`)
- `BP_PuzzleCandle` (5 graphs, 36 nodes): `UserConstructionScript` sets `bSingleUse`, `GrantedStateTags`, `ConsumedStateTag` and calls `TintBand`; `RefreshLit` calls `SetVisibility` on `Flame` and on `FlameLight` only; `TintBand` calls `SetVectorParameterValueOnMaterials` on `BandRing` only; `OnWorldStateChanged` and `EventGraph` bind the world-state delegate and call `RefreshLit`. **No node sets the mesh or a material of `Flame`.**
- `BP_LBCharacter` (2 graphs, 4 nodes): construction script empty; `EventGraph` has only BeginPlay, ActorBeginOverlap and Tick events, no flame logic. `Grep CandleFlame Source/` finds nothing in C++. **No setter.**
- So both rules apply ("if not": edit). `Saint1..4Flame` of `BP_StainedGlassClue_Saints` were not touched.

## Blueprint flames (before / after, sizes in cm)
Chapel flame actors: 13, median world bounds height 6.500 (all 13 are 6.500), flame mesh local Z 0..6.5, X +-1.5, Y +-1.4266.
| Flame | Before | After |
|---|---|---|
| `Candle_P1.Flame` (actor at 8800, -200, 30) | Sphere, `MI_LB_CandleFlame`, rel Z 50.5, rel scale (0.04, 0.04, 0.065); world box (8798, -202, 77.25)..(8802, -198, 83.75), h 6.5 | `SM_LB_Prop_CandleFlame_A`, `MI_Flame_Candle`, rel Z 47.25, rel scale (1, 1, 1); world box (8798.5, -201.43, 77.25)..(8801.5, -198.57, 83.75), h 6.5 |
| `Candle_P2.Flame` (8820, -67, 30) | box (8818, -69, 77.25)..(8822, -65, 83.75) | same edit; box (8818.5, -68.43, 77.25)..(8821.5, -65.57, 83.75) |
| `Candle_P3.Flame` (8820, 67, 30) | box (8818, 65, 77.25)..(8822, 69, 83.75) | box (8818.5, 65.57, 77.25)..(8821.5, 68.43, 83.75) |
| `Candle_P4.Flame` (8800, 200, 30) | box (8798, 198, 77.25)..(8802, 202, 83.75) | box (8798.5, 198.57, 77.25)..(8801.5, 201.43, 83.75) |
| `BP_LBCharacter.CandleFlame` (template; box in `Candle` component space, parent `CandleWax` at (0, 0, -7) scale (0.03, 0.03, 0.12)) | Sphere, `MI_LB_CandleFlame`, rel Z 59, rel scale (0.5, 0.5, 0.1667); box (-0.75, -0.75, -0.92)..(0.75, 0.75, 1.08), h 2.0 | `SM_LB_Prop_CandleFlame_A`, `MI_Flame_Candle`, rel Z 50.667, rel scale (33.333, 33.333, 8.333); box (-1.5, -1.427, -0.92)..(1.5, 1.427, 5.58), h 6.5 |
- The new min Z equals the old sphere's min Z (0.0 cm difference) on all five; the new height is 6.500 = the chapel median (ratio 1.000).
- **Deviation to confirm.** The brief says "a uniform relative scale". The puzzle candles got one (1, 1, 1). The player's candle sits under `CandleWax` (scale 0.03, 0.03, 0.12), so a uniform relative scale would give a flame 0.75 cm wide and 6.5 cm tall; I chose the relative scale that gives a uniform WORLD scale (33.33, 33.33, 8.33), the same shape as the chapel flames. This is a 3.25 times taller flame than before (2.0 -> 6.5 cm) and about 2 times wider, close to the camera: judge by eye in P15-7. The old values are in `Saved/p15_6_scratch/bpflames_before.json`.
- Mechanics: instance writes of a vector with `{x, y, z}` applied only one axis (first attempt left scale (1, 0.04, 0.065)); a partial struct per axis (`{"y": 1.0}`) works. `BP_LBCharacter` compiled clean before and after the template edit (`warnings_as_errors` true) and was saved as its own package. The placed instances of `BP_LBCharacter` (there is none in the level, the player spawns) do not matter.

## By-eye items (numbers for the lead and the owner, P15-7)
- **Strike target tip.** `TWA_Roof` bounds max Z 4824.76; the target is at Z 4844.80, so the gap is 20.04 cm (plan: 20 cm above the finial). `TWA_Roof` bounds XY centre (12492.3, 2001.2) against the target X 12530.8 (the finial's 20 degree bend explains +38.5 in X; bounds cannot confirm it). Move within +-15 cm if it looks off.
- **Crypt drips** (point Z -105; the plan puts the visible vault crown at Z -100, i.e. 5 cm above the point). The vault meshes are `SM_Roof` actors `CA_Vault_*` whose bounds are all Z -339.8..-41.6, so the bounds box includes the springing and the outer shell and cannot give the intrados height:
  | Point | Overhead mesh | Mesh XY | Point Z - mesh min Z | Mesh max Z - point Z |
  |---|---|---|---|---|
  | W_9050, W_9200, Pit_9400 | `CA_Vault_FP_0` | 9000..9520 x -2549..-2011 | 234.8 | 63.4 |
  | E_9900, E_10000 | `CA_Vault_FP_1` (E_10000 is on its edge X = 10000.0) | 9480..10000 x -2549..-2011 | 234.8 | 63.4 |
  | WC_a (6450, -1900) | `CA_Vault_WC_1` | 6211..6689 x -1977..-1400 | 234.8 | 63.4 |
  | SC_b (7250, -2350) | `CA_Vault_SC_1` | 7030..7500 x -2589..-2111 | 234.8 | 63.4 |
  | NC_a (10250, -900) | `CA_Vault_NC_0` | 9985..10515 x -1189..-611 | 234.8 | 63.4 |
  The pit point `Pit_9400` (FallHeight 545) lies under `CA_Vault_FP_0`. The two belfry points are under `TWA_Roof` (bounds Z 3246.0..4824.8): `Belfry_N_wall` is 454.9 above its min and 1123.9 below its max; `Belfry_NW_corner` 547.1 and 1031.7.
- **Cloister cloth top edges** (cloth top Z, arcade arch bounds from `CLA_Arch_*`; the arch ring spans Z 330..620, the intrados crown is estimated at about 585):
  | Cloth | Top Z | Arch actor | Arch bounds | Gap to ring top (620) | Gap to estimated intrados (585) |
  |---|---|---|---|---|---|
  | `Cloister_N_1` | 555 | `CLA_Arch_N_1` | (10640, 2205, 330)..(10860, 2295, 620) | 65 | 30 |
  | `Cloister_W_1` | 520 | `CLA_Arch_W_1` | (10205, 1740, 330)..(10295, 1960, 620) | 100 | 65 |
  | `Cloister_S_2` | 555 | `CLA_Arch_S_2` | (10940, 1305, 330)..(11160, 1395, 620) | 65 | 30 |
  Bounds cannot give the intrados, so these still need a look: the plan allows +-15 cm, and the F0.10 top edges (N/S 555, W 520) sit 30 to 65 cm below the estimated crown, so they may need to move up.

## Placement notes
- All 55 actors in `FX/Storm` are new: the target, 11 dust, 2 mist, 10 drips, 7 eaves, 6 fires, 10 cloth, 8 curtains. Fires: +6 new, -5 Cascade actors deleted (`FX_Torch_Fire` = `Emitter_0`, `FX_Crypt_Torch_T1/T2/T3` = `Emitter_1/2/3`, `FX_Crypt_Brazier` = `Emitter_4`), each deleted only after its replacement read back the right location and `User.Scale`. `FX_FirePit_Smoke`, `Light_FirePit_Ember` and the three `L_Crypt_Torch_T*` lights are untouched (checked).
- Niagara user parameters were set with `NiagaraToolset_Component.SetVariable` and read with `GetVariable` (MCP_NOTES, "Level work and data assets over MCP"). `User.Count`, `User.Scale`, `User.FallHeight` and `User.LineLength` are floats; `User.bWater` a bool; `User.BoxExtent` a `Vector3f`; `User.Extent` a `Vector2f`. `User.Interval` of the drips was left at the system default.
- Cloth: `StaticMeshActor`s, scale 1, `NoCollision` (profile and `collisionEnabled`, `bUseDefaultCollision` false), `worldPositionOffsetDisableDistance` 4000, mobility Static, cast shadow left at the default (on). Curtains: scale (30, 1, 25), NoCollision, cast shadow off, no override: `SM_LB_FX_CurtainCard` has one slot (`MAT_Curtain`) whose default is `MI_LB_RainCurtain` (confirmed with `get_material`).
- The 22 flame actors: only the component's slot-0 override was set; `SM_LB_Prop_CandleFlame_A` and `MI_LB_CandleFlame` (parent `EmissiveMeshMaterial`, Color (12, 5, 0.8)) are untouched (re-read after the change).
- The first target placement went to the folder `Lighting/Storm` because `p14_3_level.Ed.spawn` binds its own `FOLDER` default; it was moved to `FX/Storm` and the script now passes the folder (MCP_NOTES).

## Skipped / not verified
- Nothing was skipped. Not seen running: no PIE, so no particle, drip timing, cloth wave or flame look has been seen (P15-7).
- The persistence of the Niagara user-parameter overrides and the Blueprint-instance overrides after an editor restart is not proven (see "After a reload").
- Needs a human look in P15-7: the four by-eye items above; the player's candle flame size (3.25 times taller, 2 times wider); the cloister cloth heights against the arch intrados; the crypt drip points against the visible vault; the fire pit fire at scale 1.4; `User.Count` 80 on the thin tower and crypt boxes.
