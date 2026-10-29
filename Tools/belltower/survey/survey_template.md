# P10-2: greybox, gameplay, AI and kit survey for the cloister and bell tower

Phase 10, task P10-2 (technical-artist; the editor was used strictly read-only). Every value is cm in Unreal world units (courtyard ground is Z 0; +X points away from the spawn; +Y is to the player's right when facing +X). Surveyed on `L_Monastery` at branch `claude/phase-10-belltower` (`main` fb5c3ba plus the P10-0/P10-1 commits).

**How this was produced.** Python scripts in `Tools/belltower/survey/` (`s02_greybox.py`, `s06_gameplay.py`, `s09/s10` for the Blueprints, `s11_ai.py`, `s15_kit_measure.py`, `s16_lights.py` and so on) call the MCP read tools only. Raw dumps are next to this file: `greybox_p10.json` (286 actors), `gameplay_p10.json` (17 actors, with components and instance values), `blueprints_p10.json` and `blueprints_dsl_p10.json` (class defaults, variables, graph DSL of the 9 Blueprint classes), `ai_p10.json`, `ground_nav_p10.json`, `kit_p10.json` (165 meshes), `lights_p10.json`, `triggers_p10.json`, `objectives_p10.json`, `floor_east_p10.json`, `materials_list_p10.json`, `stairs_analysis_p10.txt`. Captures are `p10s_*.png` (poses in `Tools/belltower/poses/p10_survey_poses.json`, log in `capture_p10s.log`).

**Contents:** 0 summary | 1 greybox geometry | 2 gameplay Blueprints and the two mechanisms | 3 AI, navigation and tests | 4 reusable kit | 5 sight lines | 6 current-state captures | 7 anomalies | 8 end-state | 9 constraints that D1 must respect.

---

## 0. Summary of the findings that matter for D1

- **The tower is a closed greybox box.** Shell 10 x 10 m, 35 m walls, flat 40 cm roof at Z 3500..3540, one 104 x 224 door in the W wall, **no other opening**. Inside is a **solid 4.2 x 4.2 x 25 m core**; there is no shaft in the collision (the "open shaft" is purely a visual job for D1).
- **Stairs:** 11 flights x 14 treads (154 treads), run 30, rise 16.234, lane 250 wide, flights rise 227.273 each, top at Z 2500. Flights turn **left** at every landing (counter-clockwise seen from above): the lanes are N ring heading +X, E ring heading -Y, S ring heading -X, W ring heading +Y (table in 1.5). The lead's pre-survey said clockwise; the measured order is counter-clockwise.
- **Every tread is a full solid block from the flight's base Z up to its tread top, every landing is a 40 cm slab that floats** (nothing under it). Flights 2..11 float too. The ground ring around the core is therefore a **walk-in cavity under the stairs, 187..454 cm of headroom**, reachable from the tower door (anomaly A2).
- **Rails** are 77 flat boxes (7 per flight), 10 thick x 60 long x 116.234 tall, on the lane side of the core face (10 cm outside it); the outer side has none.
- **Bell chamber (top):** floor Z 2500 = core top + `Top_Slab_W` + `Top_Slab_N`; the great bell is a 250 x 250 cylinder at (12420, 2000), **80 cm off the core centre and 5 cm from the core's west edge**; the beam and chain float; the NE/E corner above landing 9/10 is open air.
- **Cloister:** 25.0 x 24.6 m interior, no roof, walks 770 / 710 / 710 / 510 wide, arcade of 14 piers (80 x 80 x 450), a 100 cm solid garth. No floor art anywhere east of X 7400 (WorldGrid slabs).
- **Mechanism 3** = four identical bells + a plaque that says `III · I · IV · II`; the sequence puzzle component grants `State.Tower.BellsSolved`; `Mech_Ritual3` needs that tag and grants `State.Ritual.3`, which opens both the tower door and the courtyard shortcut door by auto-open. **The finale bell** grants `State.Event.Finale`; `EndingTrigger` shows `WBP_Ending` for 8 s and completes the game.
- **Sight lines:** the tower is **not** a landmark yet: from the spawn it is hidden, from the garth it is hidden behind the chapel's west gable, from the shortcut door it is behind the 8 m east wall; it is only visible from the gate (a flat-topped dark block beside the chapel gable, 4.8 % of the frame wide) and from inside the cloister.
- **Nine Blueprint assets became dirty** by `read_graph_dsl` (listed in 8). Not saved.

---

## 1. Greybox geometry

All 286 surveyed actors are `StaticMeshActor`s with the engine cube (`/Engine/BasicShapes/Cube`) unless noted, collision profile `BlockAll`, `bVisible` true, Static mobility. Dimensions below come from `get_actor_bounds` (world AABB); the dump has the transforms and materials.

### 1.1 Floor and navigation volume
The floor is a set of 40 cm slabs with the top at Z 0 (`ground_nav_p10.json`):

| Slab | AABB | Material |
|---|---|---|
| `Ground_0` | X -3000..7400, Y -3600..3600 | `MI_Kit_Floor` (cobbles; the only slab with floor art) |
| `Ground_1` | X 8000..10500, Y -3600..3600 | `WorldGridMaterial` |
| `Ground_2` | X 10800..13400, Y -3600..3600 | `WorldGridMaterial` |
| `Ground_3` / `Ground_4` | X 10500..10800, Y -3600..-100 / Y 500..3600 | `WorldGridMaterial` |
| `Ground_5` / `Ground_6` | X 7400..8000, Y -3600..-1300 / Y -900..3600 | `WorldGridMaterial` |

So the passage floor is cobbles for X 6040..7400, then flat WorldGrid; the cloister and tower floors are WorldGrid slabs. The courtyard floor art (`KE_Floor_*`) ends at X 6000 (`floor_east_p10.json`). The gaps Y -100..500 (X 10500..10800) and Y -1300..-900 (X 7400..8000) are the crypt stair openings. `Perim_E` is at X 13400..13440 (800 tall), `Perim_N` at Y 3600..3640. Nav volume: see 3.2.

### 1.2 Cloister (folder `Cloister`, 23 actors)
Outer rectangle X 9460..12040, Y 500..3040; interior (wall inner faces) X 9500..12000, Y 540..3000 = **25.0 x 24.6 m**. Walls are 40 thick, 800 tall (`BasicShapeMaterial`, white in the captures).

{{cloister.md}}
**Openings.**
- **S:** X 10500..10800 (300 wide, no lintel, open to the sky); the crypt-exit stair arrives at Y 500 here (`WP_CryptToCloister_09/10` at (10650, 485/700)).
- **W:** Y 1750..2250 (500 wide), clear height 400 under `Cl_W_Lintel` (Z 400..800). It leads into the passage.
- **E side:** `Cl_E_S` (Y 500..1500), the tower's west wall (`Tw_W_S` 1500..1948, door 1948..2052, `Tw_W_N` 2052..2500) and `Cl_E_N` (Y 2500..3040) form one continuous line at X 12000..12040.

**Walks (wall inner face to arcade pier face).**

| Walk | Extent | Clear width |
|---|---|---|
| S | Y 540..1310 | 770 |
| N | Y 2290..3000 | 710 |
| W | X 9500..10210 | 710 |
| E | X 11490..12000 | 510 (holds the tower door, `Mech_Ritual3` at X 11700..11800, the plaque and the four bells) |

All are above the 180 cm clear width the Warden needs. The walk ring is continuous around the arcade. Corner squares are 710 x 770 (SW), 710 x 710 (NW), 510 x 770 (SE), 510 x 710 (NE).

**Arcade.** 14 piers 80 x 80 x 450 (BlockAll), centred: S row Y 1350 and N row Y 2250 at X 10300 / 10600 / 10900 / 11200 / **11400**; W column X 10250 at Y 1700 / 2000; E column X 11450 at Y 1700 / 2000. Gaps between pier faces: 220 (three per row), **120** between the last two of each row (X 11240..11360), 220 between the two W (and the two E) piers, and a diagonal corner opening of 270 at the two S corners (`Arc_S0` N face Y 1390 to `Arc_W0` S face Y 1660) and **170** at the two N corners (`Arc_W1` N face Y 2040 to `Arc_N0` S face Y 2210), because the W/E piers are at Y 1700 / 2000, not symmetric about the garth. The row piers sit at X 10300 while the column piers sit at X 10250 (the rectangle is not closed: the corner has no pier). Pier tops Z 450.

**Garth.** `Garth` is a solid block X 10300..11400, Y 1400..2200, Z 0..100 (11 x 8 m, BlockAll). Its edge is 10 cm inside the pier faces on all four sides. `Note_Cloister` lies on it at (10750, 1425, 100.25): the S edge, exactly in the 220 gap between `Arc_S1` and `Arc_S2` (X 10640..10860), so the player reads it from the S walk across the pier line.

**Lights (greybox).** `Light_Cloister_0..7`: 8 point lights, 3000 lm, white, radius 1500, no shadows, at Z 500 (6 of them), Z 200 (`_6`, at (10650, 300), **outside** the S wall in front of the crypt exit) and Z 400 (`_7`, (9900, 2000)). Locations in `lights_p10.json`.

### 1.3 Shortcut passage (courtyard east wall to the cloister)

{{passage.md}}
- Lane: Y 1700..2300 = **600 wide**, X 6040..9460 = 3420 long, walls 800 tall, **no roof**. The cloister W opening (500 wide, Y 1750..2250) is 50 narrower on each side than the lane.
- West end: the courtyard east wall (kit pieces `KW_*`, dressed in P7). `KW_ShortcutDoorway` is the kit `Doorway_Pointed_400x60x400` yawed -90 at (6000, 2200), occupying X 6000..6060, Y 1800..2200, Z 0..400; `KW_ShortcutUpper` the kit `Wall_400x60x400` above it (Z 400..800); `KW_ShortcutTympanum` a 12 x 120 x 100 cube (planks) at Y 1940..2060, Z 240..340 closing the pointed arch above the door. `Door_Shortcut` (the leaf) is at (6020, 1941): a 10 cm thick, 118 wide, 238 tall box (root scale 1 x 1.18 x 1.0818 on a 100 x 100 x 220 leaf), `MI_Weathered_Planks_WA`.
- The chapel's north wall and buttresses lie to the south (Y 750..960), the lane's south face is at Y 1660..1700. `Light_Courtyard_7` (3000 lm, r 1500, shadowless) is at (7700, 2000, 400) in the lane.
- Ground_6's name also matches a crypt lining actor (`CA_Lining_Ground_6_Ym900`, NoCollision, Y -900); it is not part of this area.

### 1.4 Bell tower shell and top (folder `BellTower`, 24 actors)
Shell X 12000..13000, Y 1500..2500; walls 40 thick, 3500 tall; interior X 12040..12960, Y 1540..2460 = **920 x 920**.

{{tower_shell.md}}
- The tower materials: `Tw_*` walls and roof use `MI_Env_TowerStone` (a child of `MI_Kit_Masonry`, dark brick). `Tw_Core` and the top slabs and rails use `BasicShapeMaterial` (white); landings, steps use `WorldGridMaterial`; rails `BasicShapeMaterial`.
- Door opening: Y 1948..2052 (104), Z 0..224; the leaf is 100 x 220 (2 cm side gaps, 4 cm head gap). `Tw_W_Lintel` runs Z 224..3500 above it.
- Interior ring around the core: 250 wide on all four sides (W X 12040..12290, E X 12710..12960, S Y 1540..1790, N Y 2210..2460). Ground inside is the `Ground_2` slab (Z 0). The shell has no windows, louvres or openings of any kind, and the roof is a flat closed slab.
- Lights: `Light_Tower_0..5` at (12165, 2000) and Z 300 / 900 / 1500 / 2100 / 2750 / 3200 (3000 lm, r 900, shadowless, white), `Light_TowerBell` (12600, 2300, 2900), `Light_TowerExt_0..2` at (11500, 2000) Z 1200 / 2400 / 3300 (300 lm, blue-grey 0.75/0.8/0.92, r 3500: the exterior wash on the W face), `Light_TowerTop_0` (12500, 2000, 3700) 20000 lm, r 3000, white, **above the roof**. The moon is `DirectionalLight` (pitch -38, yaw 35, intensity 0.9, cast shadows, colour 0.75/0.8/0.92) plus `Moon_Fill` (0.06, no shadows) and a sky light 0.28.

### 1.5 Stair flights (folder `BellTower/Stairs`, 154 actors `Stair_Fxx_yy`)
Measured per flight over all 14 treads: **run 30 (every tread), rise 16.234 (= 227.273 / 14, every tread), lane width 250, flight rise 227.273**. The block of each tread runs from the flight's **base Z** to its tread top, so tread `i` has top = base + 16.234 x (i + 1) and the last tread's top equals the next landing's top (it is flush: no extra rise between the last tread and the landing). Every flight spans the full 250 between the core and the outer wall.

{{flights.md}}
- Climbing order of the lanes: N ring (Y 2210..2460) heading **+X**, E ring (X 12710..12960) heading **-Y**, S ring (Y 1540..1790) heading **-X**, W ring (X 12040..12290) heading **+Y**, then it repeats; the player turns left at each landing = counter-clockwise seen from above. F11 ends at Z 2500 on the S ring at X 12290..12320 and steps onto `Top_Slab_W`.
- **Entry.** The door (W wall, Y 1948..2052) opens on the W ring at Z 0. The path goes N to the NW pad (X 12040..12290, Y 2210..2460, Z 0: this pad has no landing slab, it is the ground), then turns onto F01 at X 12290.
- F01 is solid from Z 0 (a 227-tall wedge under the flight); F02..F11 start at the previous landing's top, with nothing below them.

**Landings** (40 thick, 250 x 250, one per corner, rotating NE, SE, SW, NW):

{{landings.md}}
Each landing is flush with the top of the last tread of the flight before it and with the base of the first tread of the flight after it. No landing touches anything underneath (nothing has its top at the landing's underside); they are held only by the walls and the core (adjacent faces).

### 1.6 Railings (folder `BellTower/Railings`, 77 actors)

{{rails.md}}
- Each piece's bottom equals the tread top of tread `2i` (verified for all 77), its length (60) spans two treads, and it is 116.234 tall (about 1.17 m). So the rail is a **staircase of flat boxes**, not a slope; each piece overlaps the second tread of its pair by 16.234 (77 benign overlaps).
- The rails sit on the **lane side of the core face**: F01/F05/F09 rail Y 2210..2220 (core N face is Y 2210), F02/F06/F10 X 12710..12720 (core E face X 12710), F03/F07/F11 Y 1780..1790 (core S face Y 1790), F04/F08 X 12280..12290 (core W face X 12290). That leaves 240 of the 250 lane for the player. There is no rail on the wall side and none on the landings.
- Because there is no shaft in the collision, the rails guard nothing in the greybox; the core face is directly behind them. For D1 the visible inner rail can stand on these same planes.

### 1.7 Exact top layout (the bell chamber)

| Actor | AABB | Notes |
|---|---|---|
| core top | X 12290..12710, Y 1790..2210, **Z 2500** | the chamber floor (the `Tw_Core` top face) |
| `Top_Slab_W` | X 12040..12290, **Y 1540..2460**, Z 2460..2500 | the whole W ring, floor at Z 2500 |
| `Top_Slab_N` | X 12290..12710, Y 2210..2460, Z 2460..2500 | the N ring; joins the core top and `Top_Slab_W` |
| `Top_Rail_E` | X 12690..12710, **Y 1790..2460**, Z 2500..2600 | 20 x 670 x 100; on the core's E edge and the N slab's E edge |
| `Top_Rail_S` | X 12290..12710, Y 1790..1810, Z 2500..2600 | 420 x 20 x 100; on the core's S edge, above the F11 lane |
| `Bell_Beam` | X 12380..12460, Y 1900..2100, **Z 3300..3400** | 80 x 200 x 100; **floating**: touches nothing; 100 below the roof, 800 above the floor |
| `Bell_Chain` | X 12415..12425, Y 1995..2005, **Z 2750..3300** | 10 x 10 x 550; hangs from the beam bottom to the great bell's top |
| great bell (`Bell`, gameplay) | X 12295..12545, Y 1875..2125, Z 2500..2750 | cylinder 250 x 250 x 250 on the core top, centre (12420, 2000) |

- Floor layout: an L-shaped U (W slab, N slab, core top). The **NE corner (X 12710..12960, Y 2210..2460) and the whole E and S rings are open air** at Z 2500 (the shaft); only `Top_Rail_E` / `Top_Rail_S` stop the player there. The F11 lane runs below the S edge up to Z 2500 at X 12290.
- Clear height of the chamber: floor 2500 to roof underside 3500 = **1000**. The beam is centred at X 12420, 80 cm west of the core / shell centre (12500, 2000); the bell and chain share that off-centre axis (X 12420).
- The bell is 5 cm from the core's W edge (X 12290 vs 12295) and its Y extent 1875..2125 leaves 85 cm on the N side and (after `Top_Rail_S`) 65 cm on the S side of the core top: the N side is passable, the S side is not for a default 34 cm radius capsule (the project capsule size was not read).
- Gameplay at the top: `CP_TowerTop` (12165, 1950, 2592), `Trig_TowerTop` box centre (12165, 1700, 2650) extent 125 x 125 x 150 = X 12040..12290, Y 1575..1825, Z 2500..2800 (the SW corner of `Top_Slab_W`, where F11 arrives; **not** "landing 10"), `EndingTrigger` actor at (12165, 2300, 2600) (no volume).

### 1.8 What touches what, floating and intersecting pieces
- **Steps vs walls/core:** all 154 treads touch the core face and the outer wall with a **0 cm gap**; the closest non-touching wall is 250 or more away. No gaps, no overlaps between treads of different flights, none between landings and treads (checked pairwise, volume > 0.01).
- **Landings:** touch two walls and the core corner; **nothing beneath them** (10 floating slabs). Flights 2..11 float too; only F01 stands on the ground.
- **Under the stairs at ground level:** the ground ring E and S of the core is open: ceiling 187.273 under `Tw_Landing_01`, 227.273 under F02, 414.545 under `Tw_Landing_02`, 454.545 under F03, 641.818 under `Tw_Landing_03`, 681.818 under F04 (the W ring, where the door opens). The player can walk there. The Warden agent (height 220, radius 42) cannot pass under landing 1 (187 < 220).
- **Rails vs treads:** 77 overlaps of 30 x 10 x 16.234.
- **Beam/chain:** the beam touches nothing; the chain touches the beam bottom and the bell top.
- **Roof:** `Tw_Roof` bottom Z 3500 sits on the wall tops; 100 above the beam.
- No other intersections between the surveyed collision pieces.

---

## 2. Gameplay Blueprints

All of them are children of `Actor` directly (no Blueprint inheritance in this set). Raw component data and instance values are in `gameplay_p10.json`; class defaults, variables and graph DSL in `blueprints_p10.json` / `blueprints_dsl_p10.json`.

{{gameplay_actors.md}}
### 2.1 Class defaults and construction scripts (read with `read_graph_dsl`)

| Class | Variables (editable) and class defaults | Construction script |
|---|---|---|
| `BP_SmallBell` | `StruckTag` (default `State.Tower.Bell.1`), `SymbolIndex` 0, `SwingDegrees` 12, `SwingDuration` 0.6, `Alpha`, `bAnimating`. Components: DefaultSceneRoot, `Post`, `Arm`, `BellPivot` (scene), `Bell`, `Clapper`, `Plate`, `Glyph` (TextRender), `InteractComp`. | Sets `bSingleUse` true; if `StruckTag` is valid: granted tags = {StruckTag}, consumed tag = StruckTag. A switch on `SymbolIndex` sets the Glyph text: 0 `I`, 1 `II`, 2 `III`, default (3) `IV`. |
| `BP_SequencePuzzle` | `FailMessage`, `SolvedMessage` (CDO still the chapel text "A cold draught snuffs the flames" / "The candles burn steady. Something unlocks."); component `SeqComp` (`LBSequencePuzzleComponent`: `Steps`, `SolvedTags`). | Empty. `PlayFailFeedback` and `PlaySolvedFeedback` are **empty functions** (hooks). On failed/solved the graph prints the message with `PrintString` (dev only) and calls the hook. |
| `BP_Inscription` | `Text` (CDO `III · I · IV · II`); components `Plaque`, `Engraving` (TextRender). | Sets the Engraving text from `Text`, replacing `|` with a line break. No interaction component. |
| `BP_RitualMechanism` | `RitualTag`, `ExtraGrantedTags`, `CombinedTags`, `TurnYaw` 90, `TurnDuration` 1.5; components `Pedestal`, `Core`, `CoreMarker`, `InteractComp`. | Prompt "Activate", denied prompt "Something is missing"; if `RitualTag` is valid: granted = ExtraGranted + RitualTag, consumed = RitualTag, single use. Tick: after the tag appears, `Core` turns `TurnYaw` (smoothstep) over `TurnDuration` and `InteractComp` is disabled; at BeginPlay with the tag already present it snaps to the end pose. |
| `BP_Door_Base` | `OpenStateTag`, `AutoOpenTag`, `OpenYaw` 90, `OpenDuration` 1, `bInteractable` (CDO true), `OpenSign`; components `Hinge`, `DoorMesh`, `InteractComp`. | Granted = {OpenStateTag}, consumed = OpenStateTag, single use. If `AutoOpenTag` is present (or arrives), it adds `OpenStateTag`; the hinge then swings `OpenYaw` x `OpenSign` (smoothstep, 1 s). `OpenSign` is computed from the instigator's side only on a manual interaction, so an auto-opened door always uses sign +1. If `bInteractable` is false the prompt becomes "Locked" and the component is disabled. |
| `BP_TagInteractable` | `UseStateTag`, `bHideOnUse`, `bInspectable`; components `Mesh`, `InteractComp`, `InspectableComp`. | Granted = {UseStateTag}, consumed = UseStateTag, single use; applies inspect settings; after use disables the interaction (and hides or re-enables collision). |
| `BP_EndingTrigger` | `EndingSeconds` 8; scene root only. | Empty. `StartEnding`: creates and shows `/Game/LastBell/UI/WBP_Ending`, sets a timer `EndingSeconds` and enters menu mode; `FinishEnding`: `LBSaveSubsystem.CompleteGame`. |
| `BP_TagTrigger` | `GrantedStateTags`, `bOnce` (true); `Trigger` box. | On pawn overlap adds the tags; if `bOnce` it then switches its collision off. |
| `BP_Inspectable_Note` | `DisplayName`, `BodyText`; `Paper`, `Root`, `InteractComp`, `InspectableComp`. | Copies the two texts to the inspectable component. |

Every placed instance matches its class defaults except: `Puzzle_Bells` (fail/solved messages are the bell texts, `SeqComp.Steps` / `SolvedTags` set), the four bells (`StruckTag`, `SymbolIndex`), `Clue_Inscription` (`Text` = `STRIKE AS THE DEAD RECALL|III · I · IV · II`, root scale 2.5), `Mech_Ritual3` (`RitualTag` = `State.Ritual.3`, `InteractComp.RequiredStateTags` = {`State.Tower.BellsSolved`}), the doors (`OpenStateTag`, `AutoOpenTag` = `State.Ritual.3`, `bInteractable` false, `Door_Shortcut` also scale + planks material), `Bell` (`UseStateTag` = `State.Event.Finale`, root scale 2.5, `Mesh` = engine Cylinder).

**InteractComp values on the placed actors** (`ULBInteractableComponent`):

| Actor | Prompt | Denied prompt | Required tags | Granted tags | Single use / consumed tag | Noise |
|---|---|---|---|---|---|---|
| `Bell_1..4` | Strike bell | (none) | none | `State.Tower.Bell.1..4` | yes / the same tag | 0.9 |
| `Mech_Ritual3` | Activate | Something is missing | `State.Tower.BellsSolved` | `State.Ritual.3` | yes / `State.Ritual.3` | 1.0 |
| `Door_Tower` | Open ("Locked" shown, component disabled at BeginPlay) | Locked | none | `State.Door.TowerBase.Open` | yes / same | 0.6 |
| `Door_Shortcut` | Open (same) | Locked | none | `State.Door.Shortcut.Open` | yes / same | 0.6 |
| `Bell` (finale) | Ring the bell | (none) | none | `State.Event.Finale` | yes / `State.Event.Finale` | 0.2 |
| `Note_Cloister` | Read | none | none | none | no | 0 (inspect on interact) |

Components of the placed small bell (all `BlockAllDynamic` static meshes unless noted; engine primitives with `MI_LB_Iron` / `MI_LB_Bronze` / `MI_LB_Stone`, i.e. `BasicShapeMaterial` instances): `Post` cube 6 x 6 x 80 at local (-14, 0, 40); `Arm` cube 18 x 4 x 4 at (-6, 0, 78); `BellPivot` scene at (0, 0, 76); `Bell` **cone 18 x 18 x 25** at pivot + (0, 0, -14) (world Z about 50..75); `Clapper` sphere 5 at (0, 0, -27); `Plate` cube 2 x 26 x 16 at (-10.5, 0, 38); `Glyph` text at (-9.3, 0, 38). The actor yaw is 180, so local -X is world +X: the post is centred at X 11997 (flush on the wall plane X 12000) and the arm and bell project -X into the walk. **All four bells are identical in size and colour** (only the numeral differs). Components of `Door_Tower`: `Hinge` at the actor origin (12020, 1950), `DoorMesh` cube 10 x 100 x 220 at hinge-local (0, 50, 110), no material override (default checker).

### 2.2 How Mechanism 3 works, in plain words
1. **The four bells.** `Bell_1..4` stand along the cloister side of the tower's west wall, 120 cm apart (Y 2200, 2320, 2440, 2560), 17 cm from the wall, each a knee-high 80 cm post with a small cone bell and a stone plate showing a numeral (I, II, III, IV). The player "strikes" a bell by pressing the interact key. That adds the world-state tag `State.Tower.Bell.N` for that bell and consumes it (the bell cannot be struck again while its tag is present), makes a loud noise (0.9) and starts a 0.6 s, 12-degree damped swing.
2. **The order.** `Puzzle_Bells` is an invisible actor (11900, 2380, 0) holding a sequence-puzzle component with the steps **`State.Tower.Bell.3`, `.1`, `.4`, `.2`**. It reads progress from the tags, so a save in the middle works. Striking the next correct bell accepts it. Striking a wrong bell makes the component remove all four bell tags on the next tick (the bells become strikable again) and fires `OnPuzzleFailed` (the BP prints "The bells clash and fall silent." in development builds). When the fourth correct bell is struck the component adds **`State.Tower.BellsSolved`** and fires `OnPuzzleSolved` (prints "The last note hangs in the air. The tower mechanism unlocks."). The two feedback functions (for audio and light in Phase 16) are empty.
3. **The clue.** `Clue_Inscription` is a 300 x 10 x 75 plaque (root scale 2.5) at (11995, 2380, 200) flush on the tower wall above the bells, with the text **`STRIKE AS THE DEAD RECALL`** over **`III · I · IV · II`**: strike the bell marked III, then I, then IV, then II. It is legible at 2 m (see `p10s_m3_bells_2m.png`). It is **not interactive**: it has no interactable or inspectable component, only a text-render, so it cannot "open inspect text".
4. **The mechanism.** `Mech_Ritual3` (11750, 2000, 50) is a 100 cm pedestal with a 80 cm drum (and a small marker cube) in front of the tower door, 2.2 m from it, on the door's axis. Its prompt is "Activate"; it requires `State.Tower.BellsSolved` (otherwise it says "Something is missing"), grants **`State.Ritual.3`**, can be used once, makes noise 1.0 and turns the drum 90 degrees over 1.5 s.
5. **What opens on `State.Ritual.3`.** `Door_Tower` (hinge at (12020, 1950), leaf Y 1950..2050) and `Door_Shortcut` (courtyard east wall, (6020, 1941)) are `BP_Door_Base` with `AutoOpenTag = State.Ritual.3` and `bInteractable = false`: when the tag appears each adds its own open tag (`State.Door.TowerBase.Open`, `State.Door.Shortcut.Open`) and swings 90 degrees over 1 s. Neither can be opened by hand. The leaf swings to -X (out into the cloister for the tower door).
6. **Objective chain** (`DA_ObjectiveChain_Main`): Escape the crypt (`State.Event.CloisterEntered`) -> "Strike the bells in the inscribed order" (`BellsSolved`) -> "Release the tower mechanism" (`State.Ritual.3`) -> "Climb the bell tower" (`State.Event.TowerTop`) -> "Ring the bell" (`State.Event.Finale`). `Trig_CloisterEntered` (box X 10400..10900, Y 600..800) sets `State.Event.CloisterEntered` **and `State.Warden.Stage.5`**. `CP_Cloister` (10650, 780) and `CP_TowerBase` (12200, 2000) save.
7. **Stale text:** `Note_Cloister` ("The Last Entry") still says "The counterweights hang in the three corners of the cloister. When all three are set true, the tower will open." That is the old three-counterweight design; the puzzle is now the bells (anomaly A7).

### 2.3 How the finale bell works, in plain words
`Bell` (BP_TagInteractable, `UseStateTag` = `State.Event.Finale`) is a 250 x 250 cylinder (Z 2500..2750) on the core top. Its prompt is "Ring the bell"; there is no requirement (the player is already at the top). Pressing it adds `State.Event.Finale`, once, with noise 0.2 (very quiet), and disables the interaction; the bell is not hidden and plays no animation or sound yet. `EndingTrigger` (BP_EndingTrigger, no volume) listens to the world state: when `State.Event.Finale` appears it creates and shows `WBP_Ending`, switches the controller to menu mode, waits `EndingSeconds` (8 s) and calls `LBSaveSubsystem.CompleteGame` (the RouteBot test then expects the main menu and a wiped save within 8 + 5 s). If `Finale` is already present at BeginPlay it completes immediately. The Warden's finale behaviour and the cinematic beats are later phases (12, 13, 17); the bell's visual swing and sound are Phase 16.

---

## 3. AI, navigation and tests

### 3.1 Markers

{{ai.md}}
- All patrol and search points are in the cloister walks (none in the garth, none in the tower, none in the passage); `Patrol_Cloister_01..07` form route `Cloister`; `Search_Cloister_01..14` are search points. There are **no patrol points for route `Tower`** although `WSpawn_Tower` (min stage 6) names it.
- `WSpawn_Cloister` (9000, 2000) is in the passage (X 6040..9460); `WSpawn_Tower` (12165, 1665, 0) is in the SW corner of the tower base at ground level, under `Tw_Landing_03`.
- `Patrol_Cloister_04 -> 05` crosses the E walk through X about 11647 at Y 2000, 53 cm west of `Mech_Ritual3`'s pedestal edge (X 11700).
- Warden navigation agent (`Config/DefaultEngine.ini`, `RecastNavMesh-Warden`): radius 42, height 220, step height default, `bCanCrouch` false. Player crouched half height 58 (`LBPlayerTuningData`).

**WalkPath `TowerStairs`** (physically walked by the test; `Requires.State.Ritual.3` on point 00, so the test restores that state first):

{{walkpath_tower.md}}
The walk line is the lane centre: F01 at Y 2335, F02 at X 12835, F03 at Y 1665, F04 at X 12165, repeating; each flight's end point sits on tread 13 (the last tread) and the landing points on the landing top. Every tread is solid greybox collision, so a visually broken tread is safe as long as the invisible greybox step stays under it; keep the visible tops within the walk line's tread +- 1 cm. `WalkPath.CryptToCloister` (00..10) ends at (10650, 485/700, 0) in the cloister S opening.

### 3.2 Navigation volumes
- `NavBounds_Monastery` (`NavMeshBoundsVolume_0`): X -3300..13300, Y -3700..3700, Z -1000..3600. It covers the whole cloister, the passage and the tower including the top (Z 2500) and the roof (3540); the Z top (3600) is only 60 above the roof. It is the only nav volume; `RecastNavMesh-Warden` and `AbstractNavData-Default` exist, no nav modifiers or links.

### 3.3 Automation tests that cover this area (78 tests in `Source/LastBellTests`)

| Test | What it exercises here |
|---|---|
| `LastBell.Functional.WalkPath.Monastery` (L_Monastery) | Physically walks every `WalkPath.*` set with `AddMovementInput` (no teleporting): `TowerStairs` (25 points, the whole climb, requires Ritual.3 and the doors open) and `CryptToCloister`. Fails on stuck (< 10 cm progress in 3 s), fell below the path by 150, falling > 1 s, drift > 30, 120 s timeout. Reach radius 60 horizontal / 80 vertical. |
| `LastBell.Functional.RouteBot.Monastery` (L_Monastery) | The route bot runs the whole objective chain: cloister bells -> Mech 3 -> tower door -> stairs; checks that `CP_TowerBase` is saved and, after death and restore, `Ritual.1/2/3` are present and the pawn is within 100 cm of `CP_TowerBase`; then routes through `State.Event.Finale` and expects the main menu within `EndingSeconds` + 5. It teleports next to each target (`PlaceForInteractable`: from the target's **actor bounds**, in front, then each side, then behind, at extent + 120, on a floor with a clear line), so the bounds and collision of the bells, the pedestal and the great bell matter. It resolves doors by reflection on the class name containing `Door` and the properties `OpenStateTag`/`AutoOpenTag`, triggers by `TagTrigger` and `GrantedStateTags`, and puzzles through `ULBSequencePuzzleComponent` / `ULBInteractableComponent`. |
| `LastBell.Functional.Warden.MonasteryReachability` | After the runtime navmesh builds, every patrol segment of every route (including all 7 `Cloister` points and the wrap-around) and the spawn-to-route-start path of each spawn must be a complete, non-partial path for the Warden agent. Includes `WSpawn_Cloister` -> `Patrol_Cloister_01`. |
| `LastBell.Functional.Warden.Monastery.StagesRelocateTheWarden` | Stage 5 relocates the Warden to `WSpawn_Cloister` (within 150 cm, not in `Return`). |
| `LastBell.Functional.Puzzles.Blueprints` (L_Test_Puzzles) | Spawns `BP_SmallBell` from `/Game/LastBell/Blueprints/Puzzles/BP_SmallBell.BP_SmallBell_C`, sets `StruckTag` = `State.Tower.Bell.1`, expects a swing component named `BellPivot` (or `Pivot`/`Swing`), a `ULBInteractableComponent`, the struck tag after the press, a swing of more than 1 degree and rest within 1.5 s (reads `SwingDuration`, `SwingDegrees`). **Any change to `BP_SmallBell` (or its parent class) must keep these names and variables.** |
| `LastBell.Functional.Puzzles.Sequence/Dial/RouteBotProviders/SaveMidPuzzle` (L_Test_MicroSlice) | Generic sequence/dial logic on a test rig (candles + `State.Cloister.Weight.1..3` dials); no cloister actors. |
| `LastBell.Functional.Save.QuitMidPuzzle_Continue / DeathMidPuzzle / RevisitSolved / NewGameClears` (L_Monastery), `LastBell.Functional.Flow.MenuToGameInput` (L_MainMenu -> L_Monastery) | Load L_Monastery and use the chapel/crypt puzzle state; `NewGameClears` checks that no `State.Tower.*` / `State.Cloister.*` tag survives a new game. They do not touch the cloister actors but require the map to load and its checkpoints to work. (`LastBell.Save.FileIntegrity` only writes a save record naming L_Monastery.) |

Nothing in the test sources names `Door_Tower`, `Door_Shortcut`, `Bell_1..4`, `Puzzle_Bells` or `Mech_Ritual3` by label; they are found by class/properties/tags. The tests do not check visuals.

---

## 4. Reusable kit inventory

All measurements come from `kit_p10.json` (165 meshes; `StaticMeshTools.get_bounds`, material slots, Nanite, LOD0 triangle count from the Nanite fallback, collision elements from the `BodySetup`). Pivot conventions follow the build scripts (`Tools/blender/kit/build_kit.py`, `Tools/blender/props/build_props.py`): **kit pieces: bottom-left-back corner (bounds min = 0, 0, 0), inner face at local Y 0**; **props: bottom-centre** (exceptions in the table); the Dungeon pack uses its own pivots (see the P9-2 survey). "UCX" is the number of convex/box collision elements; the trace flag is `UseDefault` unless stated (`UseComplexAsSimple`: arch, roof, ground).

**Materials in use (instances of `M_LB_Surface` unless noted):**
- Masonry `MI_Kit_Masonry` (world aligned; parent `M_LB_Surface`), trim `MI_Kit_Trim`, rubble `MI_Kit_Rubble` (parent `MI_Rock_064`), floor `MI_Kit_Floor`, slate `MI_Kit_Slate`; **tower greybox stone `MI_Env_TowerStone` is a child of `MI_Kit_Masonry`**; chapel interior `MI_Chapel_Masonry_Interior` (child of `MI_Kit_Masonry`), `MI_Chapel_Wood_Old` and `MI_Crypt_Wood_Wet` (children of `MI_Prop_Wood_Weathered`, parent `MI_Weathered_Planks`), `MI_Crypt_StoneWA` (crypt stone), `MI_Crypt_Iron` (child of `MI_Prop_Iron_Rusty`, parent `MI_Rusty_Metal_04`), `MI_Prop_Rope` (**parent `MI_Weathered_Planks`: a plank stand-in, not rope**), and the puzzle-prop materials `MI_LB_Iron`, `MI_LB_Bronze`, `MI_LB_Stone` (all three are plain `BasicShapeMaterial` instances: greybox quality). The Dungeon pack uses `MI_Stone_00..03`, `MI_Tiles`, `MI_Dungeon_*`, `MI_Torch`. P10-1 downloaded `ambientcg-Rope003` and `ambientcg-Metal058B` (previews `p10_1_*.png`; not yet imported).
- Full lists: `materials_list_p10.json` (238 MIs, 33 masters; masters in `/Game/LastBell/Materials/Master`: `M_LB_Surface`, `M_LB_Decal*`, `M_LB_Water`, `M_LB_LightShaft`, `M_LB_Mist`, `M_LB_Foliage*`, `M_LB_Cobweb`, `M_LB_StainedGlass*`, `M_LB_UnlitEmissive`, `M_LB_Silhouette`, `M_LB_LightFunction_Flicker`).

**What fits the cloister and tower (summary).**
- **Cloister walls and walks:** `Wall_400x60x800_A/_B/_Broken`, `Wall_100x60x800`, `Wall_Corner_60x60x800`, `Buttress_100x150x800`, `Doorway_Pointed_400x60x400` (the only door-frame piece; 400 wide, 3 UCX that leave the opening free), `Window_Lancet_200x60x400_Blind`, `Trim_Plinth_*`, `Corbel_40x60x60`, `Pier_100x100x500`, `Pier_Broken_100x100x350`, `ArcadeColumn_30x30x300`. The 1000-wide **twin-arch `ArcadeBay_1000x60x400`** (openings X 50..475 and 525..950, apex Z 300, springing 0, coping Z 370..400, UCX 4 with both openings clear) exists in intact and BrokenA/B versions; a bay placed on the arcade rows needs its Z at the column tops (kit README: bay at Z 300 over `ArcadeColumn_30x30x300`). **No cornice or string-course piece exists** except the plinth/corbel trim and the `NaveBay` string course baked into the chapel bays.
- **Vaults:** the only vault is the Dungeon pack's `SM_Roof` (478 x 478 x 298, **pivot at the crown**, shell hangs 296 below, groin vault, 256 Nanite tris, `ComplexAsSimple`) with `SM_Arch` (half arch 311 x 155 x 503, inner face at x -3.4), `SM_Pillar` (150 x 146 x 464, axis 13 cm off the origin), `SM_Wall_00/01`, `SM_Ground`, `SM_Ground_01` (P9 crypt vault bays). Crypt pieces `SM_LB_Crypt_Capital_A` (170 x 170 x 55, bottom-centre), `Corbel_A`, `Beam_35x45x1120`, `Boards_300x250`, `Stair40_300` (40 steps, 1200 x 300 x 600) and `OssuaryBay_500x599` are available; the crypt versions use `MI_Crypt_StoneWA` / `MI_Crypt_Wood_Wet`.
- **Roof timber (for the broken cloister roof and the belfry frame):** `Prop_TimberPost_20x20x420`, `Purlin_15x15x1000`, `Rafter_15x10x420`, `Rafter_Broken_15x10x260`, `RoofPlanks_200x100x4` (+Broken), all **authored upright (length along Z)** with `MI_Prop_Wood_Weathered`; the chapel truss `Prop_Truss_ArchBraced_1500` (31 x 1500 x 1264, `MI_Chapel_Wood_Old`), `Kit_RoofSlab_1000x1322x20` (+Broken, slate + wood) and `RidgeCap_1000x40x30`; `SM_Dungeon_beam` (35 x 150 x 20, Nanite) and `SM_Dungeon_halfbeam`.
- **Doors and bars:** Dungeon `SM_Dungeon_door` (13 x 96 x 182, leaf in the YZ plane, 814 tris, `MI_Dungeon_door`), `SM_Bars` (233 x 9 x 236), `SM_Dungeon_window`, `SM_Dungeon_toplock`, chain/shackle pieces; an existing child `BP_Door_Base_Dungeon` (the crypt sacristy door) is the precedent.
- **Bells:** `SM_LB_Prop_BellWheel_A` (89 x 89 x 58, bottom-centre, axle on Z, slots `MAT_Iron`/`MAT_Bronze`, UCX 1, 2504 tris); no great-bell or small-bell mesh exists. The bell dressing materials are `MI_LB_Bronze` / `MI_LB_Iron`.
- **Props for cells and the garth:** `SM_Wooden_Lantern_01`, `Crate_01`, `Stool_01`, `WoodenTable02`, `Bucket_01/02`, `WineBarrel01`, Dungeon `bench`, `chest`, `Chest`/`Trunk`, candle holders (`SM_Candles_Holder_00..05` are heavy: 8k..64k tris, not Nanite), `SM_Candle_01..10`, `Candle_Melted_*`, `Brass_Candleholders`, `Gothic_Statue`, `Torch`, `Cage`, `Anvil`; kerbs, rubble chunks/heap for debris; `PricketStand_150`.

### 4.1 Full tables (all measured pieces)
Frame: UE axes, mesh-local, before actor scale.

{{kit_tables}}

---

## 5. Sight lines (editor-viewport captures, 1334 x 812, horizontal FOV 90)

Coverage is projected analytically from the tower's AABB (X 12000..13000, Y 1500..2500, Z 0..3540) into each pose (`Tools/belltower/survey/s19_project.py`); "visible" is read from the capture.

| Pose | Camera (X, Y, Z, pitch, yaw) | Tower if nothing stood in front (width x height of its bbox, % of the frame) | What the capture shows |
|---|---|---|---|
| spawn, looking +X | (-2800, 0, 170, 0, 0) | 3.7 % x 19.6 % | **Capture missing** (6 failed attempts: the editor window was covered; not retried). |
| spawn, aimed at the tower | (-2800, 0, 170, 0, yaw 7.2) | 3.6 % x 19.6 % | `p10s_sl_spawn_aim.png`: the narrow cliff-walled approach lane and the gatehouse arch; the sky above shows **no tower**. The tower (148 m away, top 13 degrees up) is hidden behind the gate and the cliff. |
| gate | (300, 0, 170, 0, 0) | 4.8 % x 24.9 % | `p10s_sl_gate.png`: **visible**, a flat-topped dark block to the right of the chapel's west gable (screen x 745..809, top at y 213; about 65 x 117 px = 4.9 % x 14.4 % of the frame; the lower half hides behind the chapel and the arcade). Faces seen: **W (its 10 m wide face) and a sliver of S**; a plain unbroken rectangle: no louvres, no belfry, no broken roof. |
| gate, aimed | (300, 0, 170, 4, yaw 9.1) | 4.7 % x 24.3 % | **Capture missing** (6 failed attempts). |
| courtyard garth | (3400, 0, 170, 0, 0) | 6.7 % x 33.8 % | `p10s_sl_garth.png`: **hidden**. The chapel's west gable fills that part of the sky (the tower would sit at x 771..860, behind the gable); a timber post prop is in the camera's face. Same for `p10s_sl_garth_aim.png` (pitch 8, yaw 12.4): still behind the gable. |
| shortcut door | (5600, 2000, 170, 0, 0) | 7.8 % x 45.4 % | `p10s_sl_shortcut.png`: the pointed doorway with its dark planked door, 8 m wall, dead weeds; **no tower** (walls 800 tall hide it up to a 57 degree elevation, the tower top is at 28). `p10s_sl_shortcut_up.png` (pitch 25) shows only the wall face. |
| cloister S entry, looking +Y | (10650, 700, 170, 0, 90) | 12.5 % x 67.5 % (at the left edge) | `p10s_sl_cloister_s_entry.png`: the four near piers of the S row, the garth and the N row beyond, the W wall at the right with the 500 x 400 passage opening at its foot; only a dark strip of the tower at the left edge. Aimed at the tower (`..._s_entry_tower.png`, pitch 8, yaw 44): the tower's W face is a dark brick slab about 20 % of the frame wide (projected bbox 32 %) rising out of the top, to the right of the E wall. |
| cloister NW corner | (9700, 2900, 170, 0, yaw -21.4) | 21.7 % x 56.1 % | `p10s_sl_cloister_nw.png`: the W face of the tower, dark brick, with the plaque and the four bells at its foot, beyond the arcade; `p10s_sl_cloister_nw_up.png` (pitch 25): the face rises out of the frame (95 % of the height), a plain 35 m wall with no feature, the roof never seen. |

**Findings.**
- From the courtyard the tower is currently only seen from the gate, a small featureless dark block beside the chapel gable; from the spawn, the garth and the shortcut door it is not visible (hidden by the cliffs and gate, the chapel gable and the 8 m east wall).
- To be a landmark it must rise clearly over the chapel roof line from the gate and the courtyard: the tower top is 3540, the chapel gable apex is in front of it from the garth. From the gate pose the tower's left third sits behind the chapel's roof shoulder (x 745..765) and only the upper 117 px are visible against the sky, so D1 needs the new belfry and broken roof to show above the chapel roof line from that pose; from the garth it needs to be taller or the view needs another solution, since the gable fully hides it.
- From inside the cloister only the W face (and from the S entry a little of the S face) is ever seen; the N and E faces and the roof are seen from nowhere in the game outside the tower itself.

---

## 6. Current-state captures (editor viewport, greybox; editor helper icons and volume wireframes show)

| File | Pose (X, Y, Z, pitch, yaw) | What it shows |
|---|---|---|
| `p10s_cl_sw.png` | (9650, 650, 170, -3, 45) | SW corner looking NE: white S wall (left) and W wall (right), the white 10 cm-gapped garth with its 14 piers in the middle, grey WorldGrid floor with noise, red Warden patrol arrows; the tower's dark brick W face rises behind the garth top-left. |
| `p10s_cl_se.png` | (11850, 650, 170, -3, 135) | SE corner looking NW: same geometry; the dark pedestal and drum of `Mech_Ritual3` at the left edge. |
| `p10s_cl_nw.png` | (9650, 2900, 170, -3, -45) | NW corner looking SE: garth and piers at left, the white W wall at left, the white N wall at right running to the tower's dark W face, which carries the plaque and the four small bells on its foot. |
| cl_ne | (11850, 2900, 170, -3, -135) | **Missing** (6 failed attempts, not retried). |
| `p10s_pass_west_end.png` | (6100, 2000, 170, 0, 0) | The passage from the courtyard end: a 6 m lane of wet cobbles between two 8 m grey walls under black sky, the cloister W opening at the far end showing a white frame and a dark gap. |
| `p10s_pass_east_end.png` | (9400, 2000, 170, 0, 180) | The passage from the cloister end looking west: the lane with the flat grey WorldGrid floor (`Ground_1`/`Ground_6`), a red arrow at the bottom (the Warden spawn marker `WSpawn_Cloister`), and the far courtyard end nearly black. |
| `p10s_tower_base_door.png` | (11500, 2000, 170, 0, 0) | The tower's W face: dark brick. In front, the pedestal and drum of `Mech_Ritual3` (default checker material) hides the closed door leaf behind it; the plaque (right) reads `STRIKE AS THE DEAD RECALL / III · I · IV · II` and three of the four bells at its foot. |
| `p10s_m3_mech_2m.png` | (11550, 2000, 150, -8, 0) | Mechanism 3 at 2 m: a checker-grey cube, an 80 cm drum and a small marker cube, the door leaf (checker) and its white frame behind; plaque and bells at the right. |
| `p10s_m3_bells_2m.png` | (11783, 2380, 140, 0, 0) | The four bells at 2 m: identical gold cones on black posts with numeral plates I..IV, knee-high; the plaque above is fully legible; the E wall's white greybox cuts in at the right. |
| `p10s_tower_shaft_up.png` | (12150, 2000, 170, 70, 0) | Standing in the tower W ring at ground level looking up: the underside of F04 (a flat white soffit at Z 681.8), the core's W face (striped grey) and the dark brick wall; **no shaft is visible** because the core is solid. |
| `p10s_tower_landing5.png` | (12830, 2330, 1306, -10, -90) | On landing 5 looking down F06: the 250 wide flight rising toward the far landing, the left-hand stepped rails (white boxes) on the core side, the wall at right; everything is nearly black (the 3000 lm shadowless lights barely reach); two half-dome WalkPath target-point icons at the far landing. |
| `p10s_tower_top_bell.png` | (12160, 2330, 2670, -6, -51.8) | The top: the great bell as a checker-grey cylinder on the white core top, the white 10 cm chain rod above it, the dark brick walls closing the chamber on all sides, a low white rail at the right, the `CP_TowerTop` wireframe and WalkPath icons at the left; there is no louvre, roof opening, beam or frame visible. |
| `p10s_overview_top.png` | (11000, 1900, 4500, -90, 0) | A plan view of the cloister from above (X up, Y right): the white wall ring, the garth block with its 14 piers, the red patrol/search arrows in the walks, the passage mouth at the left edge and the dark W face of the tower at the top. |

Also saved as sight-line evidence: `p10s_sl_gate`, `sl_garth`, `sl_garth_aim`, `sl_shortcut`, `sl_shortcut_up`, `sl_spawn_aim`, `sl_cloister_s_entry`, `sl_cloister_s_entry_tower`, `sl_cloister_nw`, `sl_cloister_nw_up` (section 5). **Missing after 6 attempts each:** `sl_spawn`, `sl_gate_aim`, `cl_ne`. Cause: the Unreal Editor window was behind two other windows (the desktop apps) and `CaptureViewport` closed the connection after about 19 s; later poses captured in 1-2 s once the window was reachable. No capture was faked or retried beyond the cap.

---

## 7. Anomalies

| # | Finding |
|---|---|
| A1 | The stair flights turn left (counter-clockwise seen from above): headings +X, -Y, -X, +Y; the pre-survey said clockwise. |
| A2 | The ground ring E and S of the core is a walk-in cavity under the floating flights (headroom 187.273 under landing 1, 227.273 under F02, 414.545 / 454.545 / 641.818 / 681.818 further round). The player can enter it; the Warden agent (220 tall) cannot go under landing 1. `WSpawn_Tower` lies in this ground ring. |
| A3 | All 10 landings and flights F02..F11 float; the core is a solid 4.2 x 4.2 x 25 m block (no shaft); the shell and the flat roof are fully closed. |
| A4 | The great bell, its chain and beam are 80 cm off the tower axis (X 12420 vs 12500) and the bell is 5 cm from the core W edge; the beam floats 100 below the roof and touches nothing; the bell's actor bounds feed the RouteBot's approach points (extent + 120 on each side), so a new bell with other bounds can make those approaches invalid. |
| A5 | For the record: `Top_Rail_E` runs Y 1790..2460 (past the core, along `Top_Slab_N`'s east edge); `Top_Slab_W` covers the whole W ring Y 1540..2460; `Trig_TowerTop` is at the SW corner of the top slab, where F11 arrives, not at landing 10 as the pre-survey said. |
| A6 | 77 benign rail/tread overlaps (each rail piece is embedded 16.234 into the second tread of its pair). |
| A7 | `Note_Cloister` text still describes three counterweights; the puzzle is the bells. |
| A8 | `BP_Inscription` has no interactable/inspectable component, so the P10 constraint "inscription opens its inspect text" is not true today; it is a 300 x 75 plaque with a text-render only. |
| A9 | `BP_SequencePuzzle`'s `PlayFailFeedback` / `PlaySolvedFeedback` are empty and the messages are `PrintString` (development only; nothing for the player in a shipping build). Its CDO messages are still the chapel candle texts. |
| A10 | The four small bells are identical in size and colour and only 25 cm tall / 18 cm wide (cone) on 80 cm posts; `Mech_Ritual3`, `Door_Tower` and the bells are engine primitives on `BasicShapeMaterial`/default checker; `MI_Prop_Rope` is a plank material. |
| A11 | `Door_Tower` and `Door_Shortcut` cannot be opened by hand (`bInteractable` false, prompt "Locked"); they open only when `State.Ritual.3` appears; the leaf swings +90 yaw (out into the cloister / into the courtyard). `Mech_Ritual3`'s pedestal stands on the door's axis 2.2 m in front of the leaf and hides it from the walk approach (`p10s_tower_base_door.png`). |
| A12 | No floor art exists east of X 7400 (passage east half, cloister, tower base); `Ground_1/2/4/6` are `WorldGridMaterial`. `Ground_4` extends to Y 3600 and `Ground_6` to Y 3600 (past the N wall). |
| A13 | `Light_Cloister_6` (10650, 300, 200) is outside the S wall; the cloister and tower greybox lights are white 3000 lm shadowless (not the night look); `Light_TowerTop_0` (20000 lm) is above the roof. |
| A14 | Arcade irregularities: the row piers are at X 10300..11400 (spacing 300/300/300/**200**, a 120 cm gap between the last two) while the W/E columns are at X 10250 / 11450 and have only 2 piers each, so the arcade has no corner piers and a 270 gap at each corner. |
| A15 | `WSpawn_Tower` (min stage 6) names route `Tower`, which has no patrol points. |
| A16 | Mislabelled actors: none found in the surveyed folders. `Door_Shortcut` lives in `Gameplay/Courtyard` (not `Gameplay/Cloister`) and `Note_Cloister` in `Gameplay/Notes`. |
| A17 | The tower greybox is exactly 10 x 10 m with 40 cm walls; the 104 cm door opening is 4 cm wider than the 100 leaf (2 cm each side). |

---

## 8. End-state (nothing was changed)

- Tools used: `get_*`, `list_*`, `find_*`, `read_graph_dsl`, `trace`-free; captures only moved the editor viewport camera (`SetCameraTransform`) and read the viewport. No `set_*`, transform, spawn, delete, compile, save, material, PIE or throttle calls.
- `L_Monastery` is **not dirty** (`AssetTools.is_dirty` False before the first read and at the end); the editor is still on `L_Monastery`; no `TMP_` actor exists; PIE was never started; `bThrottleCPUWhenNotForeground` reads **true** (never touched).
- **Dirty Blueprints after `read_graph_dsl` (MCP_NOTES warns about this): `BP_SmallBell`, `BP_SequencePuzzle`, `BP_Inscription`, `BP_RitualMechanism`, `BP_Door_Base`, `BP_TagInteractable`, `BP_TagTrigger`, `BP_EndingTrigger`, `BP_Inspectable_Note`** (all clean before the reads, all dirty after). They were **not saved**, compiled or cleaned; the owner should choose Don't Save for them when closing the editor. The map and all other packages were not dirtied by this task.
- `git status` after the commit shows no `.uasset` / `.umap` changes from this work; `Content/LastBell/Maps/L_Throwaway_P9_4.umap` (a pre-existing untracked file) was not added.

---

## 9. Constraints for D1 collected from this survey

1. Keep `BP_SmallBell`'s `BellPivot`, `InteractComp`, `StruckTag`, `SwingDuration`, `SwingDegrees` (the `Puzzles.Blueprints` test) and the class path of the base asset; do child BPs per D-071 (the construction script must copy the parent's body; component defaults do not override in a child).
2. Keep door class names containing `Door` with `OpenStateTag` / `AutoOpenTag`; keep `GrantedStateTags` on trigger classes; keep `Hinge`.
3. The great bell and the three Mech 3 interactables must keep colliding components so the interaction trace hits them, and bounds that give the RouteBot valid approach points (front/side/back at extent + 120 on a floor); the area around the bell on the core top is only 420 x 420.
4. Visible tread tops within +-1 cm of `base + 16.234 x (i + 1)`, landings within +-1 of the table; the walk line is the lane centre; the inner rail plane is 10 cm outside the core face; the lane is 240 clear.
5. The ground ring under the flights is reachable: the art underside needs a soffit (or the cavity must be dressed), at 187..454 cm.
6. Cloister numbers for the vaults: walk clear widths 770 / 710 / 710 / 510, wall inner faces at X 9500, X 12000, Y 540, Y 3000 (wall top Z 800), pier tops at Z 450, W opening 500 x 400, S opening 300, E tower wall continuous. Clear height >= 300 and springing >= 330 means the vault crown must be above Z 330 + 296 = 626 for the Dungeon `SM_Roof` (crown at its pivot).
7. Passage: lane 600 x 800 high x 3420 long, wall faces at Y 1700 / 2300; the cloister W opening is 500 wide.
8. The inscription needs an inspect component if the inspect behaviour is to stay in the acceptance criteria; the cloister note text needs fixing (counterweights).
