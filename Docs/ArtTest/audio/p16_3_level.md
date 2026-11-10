# P16-3: audio level work in L_Monastery

Script: `Tools/audio/p16_level.py` (`--apply [--only zones,volumes,emitters,floors,water]`, `--check`, `--save`, `--reload-check`). Idempotent, exact-label finds, `--apply` never saves. Editor open on `L_Monastery`, PIE never started, no capture, no automation run.

## Result
- Census 3054 -> **3089** (+7 zones, +7 AudioVolumes, +18 emitters, +3 water pads), all 35 in the outliner folder `Audio`.
- `--check` (full): **78 PASS, 0 FAIL** before the save; `--save`: **97 PASS, 0 FAIL** (it repeats the full check, saves, then checks dirty state); `--reload-check` after the save: **79 PASS, 0 FAIL**.
- Saved: `/Game/LastBell/Maps/L_Monastery` only (one package); `is_dirty` false afterwards. The never-save list (17 packages incl. `M_LB_Surface`, `NS_LB_Rain`) and all 208 audio packages (`Audio/**` 200, `PM_LB_*` 6, `DA_Audio`, `DT_Footsteps`) were never dirty.

## 1. Zones (`AUD_Zone_<Name>`, `ALBAudioZone`, rotation 0, scale 1)
World box = location +- box extent; every value read back.

| Zone | Location | Half extent | Prio | RoofRain | InteriorWind | Howl | Darkness | Room tone (volume) |
|---|---|---|---|---|---|---|---|---|
| Chapel | (7550, -345, 1180) | (1550, 1205, 1220) | 1 | 0.90 | 0.25 | 0 | 0.3 | SFX_LB_Room_Chapel (0.6) |
| Crypt | (9150, -1215, -610) | (2850, 1735, 590) | 2 | 0.05 | 0.05 | 0 | 1.0 | SFX_LB_Room_Crypt (0.8) |
| Cloister | (10750, 1770, 730) | (1290, 1270, 770) | 1 | 0.70 | 0.50 | 0 | 0.2 | SFX_LB_Room_Cloister (0.5) |
| Garth | (10852.5, 1802.5, 730) | (607.5, 457.5, 770) | 2 | 0 | 1.0 | 0 | 0.1 | none (volume 0) |
| Passage | (7750, 2000, 430) | (1710, 340, 470) | 1 | 0 | 0.40 | 0 | 0.6 | SFX_LB_Room_Passage (0.7) |
| TowerStair | (12500, 2000, 1305) | (510, 510, 1345) | 3 | 0.60 | 0.60 | 0.35 | 0.6 | SFX_LB_Room_Tower (0.7) |
| Belfry | (12500, 2000, 3600) | (510, 510, 1200) | 4 | 0.80 | 1.0 | 1.0 | 0.3 | SFX_LB_Room_Belfry (0.5) |

`ZoneName` is the area name.

## 2. AudioVolumes (`AUD_Vol_<Name>`, `/Script/Engine.AudioVolume`)
- The spawned brush is a 200 cm cube (bounds +-100 at scale 1): scale = size / 200. Bounds read back from `get_actor_bounds` equal the zone boxes to the cm (e.g. Chapel [6000,-1550,-40]..[9100,860,2400]).
- `settings`: `bApplyReverb` true, `reverbEffect` `RVB_LB_<Area>`, `volume` 0.6, `fadeTime` 1.0. Garth: `bApplyReverb` false, no effect (volume 0.6 and fade 1.0 left set).
- `ambientZoneSettings` (`exteriorVolume` / `exteriorLPF` / `interiorVolume`): Chapel, Crypt, Passage, TowerStair 0.35 / 2500 / 1; Cloister, Belfry 0.7 / 6000 / 1; Garth 1.0 / 20000 / 1 (no muffling). Other fields (times, interior LPF 20000) stay at the engine defaults.
- `priority` = the zone's priority (1, 2, 1, 2, 1, 3, 4); `bEnabled` true.

| Volume | Location | Brush scale | Bounds read back |
|---|---|---|---|
| Chapel | (7550, -345, 1180) | (15.5, 12.05, 12.2) | [6000,-1550,-40]..[9100,860,2400] |
| Crypt | (9150, -1215, -610) | (28.5, 17.35, 5.9) | [6300,-2950,-1200]..[12000,520,-20] |
| Cloister | (10750, 1770, 730) | (12.9, 12.7, 7.7) | [9460,500,-40]..[12040,3040,1500] |
| Garth | (10852.5, 1802.5, 730) | (6.075, 4.575, 7.7) | [10245,1345,-40]..[11460,2260,1500] |
| Passage | (7750, 2000, 430) | (17.1, 3.4, 4.7) | [6040,1660,-40]..[9460,2340,900] |
| TowerStair | (12500, 2000, 1305) | (5.1, 5.1, 13.45) | [11990,1490,-40]..[13010,2510,2650] |
| Belfry | (12500, 2000, 3600) | (5.1, 5.1, 12.0) | [11990,1490,2400]..[13010,2510,4800] |

## 3. Emitters (`AUD_Emit_<Kind>_<id>`, `ALBAmbientEmitter`)
Default volume range (0.7, 1.0), pitch range (0.95, 1.05), no loop; variants in order 01..05 (chains 01..04).

| Kind | Id / location | Sounds | Interval (s) | ActiveRadius |
|---|---|---|---|---|
| Drip, water | W_9050 (9050,-2280,-105); W_9200 (9200,-2280,-105); Pit_9400 (9400,-2280,-105); E_9900 (9900,-2280,-105); E_10000 (10000,-2280,-105) | SFX_LB_Drip_Water_01..05 | 1.5..4 | 3000 |
| Drip, stone | WC_a (6450,-1900,-105); SC_b (7250,-2350,-105); NC_a (10250,-900,-105); Belfry_N_wall (12600,2440,3700.9); Belfry_NW_corner (12100,2400,3793.1) | SFX_LB_Drip_Stone_01..05 | 2..6 | 3000 |
| Creak, tower | T1 (12500,2000,650); T2 (12455,1960,1350); T3 (12545,2040,2050) | SFX_LB_Creak_Wood_01..05 | 8..20 | 3000 |
| Creak, belfry | B1 (12900,2400,3380); B2 (12100,1600,3380) | SFX_LB_Creak_Wood_01..05 | 8..20 | 3000 |
| Chain, distant | C1 (11450,-2450,-300); C2 (6370,-2450,-300); C3 (7550,-2850,-300) | SFX_LB_Chain_Distant_01..04 | 20..45 | 4000 |

The drip points are the ten P15 F0.8 points (5 over water, 5 stone/belfry).

**Why these creak and chain points** (clearances are computed live by `--check`, from the `WP_*` walk paths, the AI points, the shaft core and the bell):
- Tower creaks T1..T3 sit inside the solid shaft core (`Tw_Core`, x 12290..12710, y 1790..2210, z 0..2500) within 55 cm of its axis, at the heights of landings 3, 6 and 9. They are 302..341 cm from the stair ring (`WP_TowerStairs`, needs >= 150) and 165..210 cm from the nearest core face, so they sound as the timber of the shaft groaning through the wall and never from beside the player. The corner posts and landings are within about 125 cm of the lane, which is why the posts themselves were not used. `ATT_LB_Medium` has no occlusion, so a source inside the core is not muffled.
- Belfry creaks B1 (NE) and B2 (SW) sit at roof-beam height z 3380, 880 cm above the belfry floor: 887 and 812 cm from the bell, 1214 and 885 cm from the stair lane.
- Chains: C1 crypt SE corner of the east room (612 cm from the nearest walk lane, 981 cm from an AI point); C2 SW room west end (1395 / 345 cm); C3 south nook west end (1323 / 678 cm). Lane limit 300 cm, AI-point limit 150 cm. z -300 is mid-height under the vault crown (-100).

## 4. Floors (`bodyInstance.physMaterialOverride` on `StaticMeshComponent0`)
| Surface | Actors | Count | Read back |
|---|---|---|---|
| Wood (`PM_LB_Wood`) | `Tw_Landing_01..10`, `Stair_F01_00..Stair_F11_13` (the 11 tower flights, 14 steps each), `Top_Slab_N`, `Top_Slab_W` | 166 | 166 / 166 |
| Grass (`PM_LB_Grass`) | `Garth` | 1 | 1 / 1 |
| Earth (`PM_LB_Earth`) | `Garden_Earth_{NE,NW,SE,SW}_00..09` | 40 | 40 / 40 |

- Skipped: none. All three groups are plain `StaticMeshActor`s.
- F0 sampled `Stair_F02..F10` step 07, `Tw_Landing_01..10`, `Top_Slab_N/W`, `Garth` and two `Garden_Earth_*_00`; the override went on the whole group (every step of every flight, all 40 earth patches), because any step or patch can be the one under the foot.
- Not touched: `Stair_CryptUp_*` and `Stair_SacristyDown_*` (stone), `Tw_Core`, `Top_Rail_*`. Stone floors keep the default; read back None on `Ground_0`, `CryptFloor_0..2`, `Prop_Crypt_0`, `TWA_Landing_01`, `Ch_Floor_B1`.

## 5. Water pads
Cube (`/Engine/BasicShapes/Cube`) StaticMeshActors, mobility static, 2 cm thick, XY = the bounds of the pool plane, top = crypt floor shell top (-600, measured on `CryptFloor_0/1/2`) + 0.5 cm.

| Pad | Under | Centre | Scale | Bounds read back |
|---|---|---|---|---|
| AUD_Water_W | CA_Water_W | (9047.5, -2280, -600.5) | (4.95, 3.9, 0.02) | [8800,-2475,-601.5]..[9295,-2085,-599.5] |
| AUD_Water_E | CA_Water_E | (10002.5, -2280, -600.5) | (3.95, 3.9, 0.02) | [9805,-2475,-601.5]..[10200,-2085,-599.5] |
| AUD_Water_Ledge | CA_Water_Ledge | (9550, -2388.5, -600.5) | (5.1, 1.73, 0.02) | [9295,-2475,-601.5]..[9805,-2302,-599.5] |

- `bHiddenInGame` true, `castShadow` and `bCastDynamicShadow` false, `bCanEverAffectNavigation` false.
- Collision: `bUseDefaultCollision` false, profile `Custom`, `QueryOnly`, object type `ECC_WorldStatic`, `physMaterialOverride` `PM_LB_Water`. The saved response array holds all 10 channels by NAME: Visibility = Block; WorldStatic, WorldDynamic, Pawn, Camera, PhysicsBody, Vehicle, Destructible, Projectile and Interaction (`ECC_GameTraceChannel2`) = Ignore. The channel names were checked against `Engine/Config/BaseEngine.ini` and `Config/DefaultEngine.ini`.
- The pit (`CA_Water_Pit`, z -650) has no pad: it is not walkable.
- The footstep trace is Visibility and complex, so it hits the pad (top -599.5, above the shell at -600) and reads Water; the player capsule (Pawn) passes through.

## Not verifiable here, for the lead and the owner
- **Live responses of the pads.** `set_properties` writes the raw struct, so the live editor component does not rebuild its response container (`trace_world` still hit a probe cube after its Visibility response was set to Ignore). The saved array is what `FBodyInstance::FixupData` turns into the container at load (engine source `BodyInstance.cpp`, profile `Custom`). After the save, `--reload-check` called `load_level` and the full check passed again, but I could not prove from the log that the editor really reloaded from disk. The suite (loads from disk) and the first PIE will show it: the player must walk through the pads, and a footstep in the pools must be Water. If a pad blocks the player, delete the pads and re-run `--apply --only water` after a fresh editor start.
- **By ear (P16-4):** the three tower creaks (inside the core, heard across the shaft), the two belfry creaks (high beams), the three distant chains, and the Passage reverb/muffling (plan: the lane is open above, 0.35 / 2500 Hz may be too dull).
- All ambient values are the plan defaults; no sound was played.

## P16-5 owner choices applied
From the P16-4 listening session (the owner's choices), written to the editor level and expected by `Tools/audio/p16_level.py` (`--apply` sets them, `--check` checks them):
- `AUD_Zone_Chapel.RoomToneVolume` = 0.4 (the script's table said 0.6; the editor level held 1.0).
- `AUD_Emit_Chain_C1/C2/C3` `IntervalMin` 8, `IntervalMax` 18 (were 20, 45).
- Each float is written in its own `set_properties` call and read back. The map was saved with `--save` (only `/Game/LastBell/Maps/L_Monastery`).

## P16-6 creature emitters (D-112)
Step `creatures` of `Tools/audio/p16_level.py` (`--apply --resume --only creatures`; the census guard needs `--resume` because the map already holds the 3089 actors). 13 `ALBAmbientEmitter` actors in the outliner folder `Audio`, labels `AUD_Emit_<Kind>_<id>`, rotation 0, scale 1, default volume range (0.7, 1.0) and pitch range (0.95, 1.05), no loop, variants `/Game/LastBell/Audio/Room/<name>.<name>` in order. Each float (`intervalMin`, `intervalMax`, `activeRadius`) was written in its own `set_properties` call and read back. Coordinates are constants in the script, probed from the live level (bounds over MCP) and re-checked by `--check`.

| Emitter | Location | Sounds | Interval (s) | ActiveRadius | Why this point |
|---|---|---|---|---|---|
| AUD_Emit_Bat_B1 | (12250, 2250, 3430) | SFX_LB_Bat_01..06 | 6..15 | 2500 | belfry NW roof beam, 70 cm under the roof (Tw_Roof underside z 3500) |
| AUD_Emit_Bat_B2 | (12800, 1700, 3430) | SFX_LB_Bat_01..06 | 6..15 | 2500 | belfry SE roof beam, the opposite corner |
| AUD_Emit_Bat_B3 | (12480, 2000, 3430) | SFX_LB_Bat_01..06 | 6..15 | 2500 | over the bell's beam (Bell_Beam, z 3300..3400), 683 cm from the bell |
| AUD_Emit_Bat_T1 | (12440, 1970, 2440) | SFX_LB_Bat_01..06 | 6..15 | 2500 | inside the shaft core (Tw_Core), 60 cm under the belfry floor (z 2500), 67 cm from the axis |
| AUD_Emit_Owl_C1 | (4550, 550, 650) | SFX_LB_Owl_01..04 | 30..60 | 6000 | crown of the dead tree `Garden_DeadTree_A` (bounds x 4332..4768, y 310..790, z 0..700), mid-courtyard |
| AUD_Emit_Owl_C2 | (3000, 3620, 810) | SFX_LB_Owl_01..04 | 30..60 | 6000 | top of the north perimeter wall `Perim_N` (y 3600..3640, top z 800) |
| AUD_Emit_Owl_G1 | (10750, 2250, 640) | SFX_LB_Owl_01..04 | 30..60 | 6000 | top of the north garth arcade arch `CLA_Arch_N_1` (top z 620), garth side (inside the Garth zone, y <= 2260) |
| AUD_Emit_Howl_NE | (14800, 4900, 500) | SFX_LB_Howl_01..03 | 120..240 | 15000 | north-east, outside the walls |
| AUD_Emit_Howl_SW | (-4400, -4900, 500) | SFX_LB_Howl_01..03 | 120..240 | 15000 | south-west, outside the walls |
| AUD_Emit_Rat_R1 | (6325, -2000, -590) | SFX_LB_Rat_01..05 | 15..35 | 2000 | west hall, base of `CA_Wall_W6300` (face x 6302) |
| AUD_Emit_Rat_R2 | (7525, -1900, -590) | SFX_LB_Rat_01..05 | 15..35 | 2000 | ossuary hall, base of `CA_Wall_W_OS_N` (face x 7502) |
| AUD_Emit_Rat_R3 | (10750, -2475, -590) | SFX_LB_Rat_01..05 | 15..35 | 2000 | east crypt south row, base of `CA_Wall_S_CC_1` (face y -2498) |
| AUD_Emit_Rat_R4 | (9600, -2635, -590) | SFX_LB_Rat_01..05 | 15..35 | 2000 | south niche behind the flooded hall, base of `CA_Wall_S_FP_1` (face y -2612) |

Geometry used: belfry interior x 12040..12960, y 1540..2460 between the `Tw_*` walls, roof underside z 3500; great bell (12420, 2000, 2750); perimeter walls `Perim_W/E/S/N` hull x -3040..13440, y -3640..3640, top z 800; crypt floor top z -600.

**Clearances** (computed live by `--check`, 3D distances):
- Bats B1..B3: z within 3300..3600; bell 744 / 835 / 683 cm (>= 600); apart 340 cm at the least (>= 300); nearest existing emitter 421 cm (drip, belfry NW corner), 709 cm (creak B1) and 530 cm (drip, belfry N wall), all >= 400; inside the belfry walls.
- Bat T1: inside the `Tw_Core` footprint, z 2440 < 2500, 150 cm from the nearest core face; nearest existing emitter 410 cm (creak T3, needed >= 400).
- Owls: z 650 / 810 / 640 (600..900); apart 3443 cm at the least (>= 1500); nearest existing emitter 3191 / 6573 / 1768 cm.
- Howls: 1854 cm beyond the perimeter hull each (>= 1000), NE quadrant (x > 13440, y > 3640) and SW quadrant (x < -3040, y < -3640), z 500.
- Rats: z -590, inside the Crypt zone box; nearest walk lane (all 10 `WP_*` lanes, 80 points): R1 928 cm (`WP_SacristyToCrypt`), R2 862 cm (same), R3 509 cm (`WP_FloodedLedge`), R4 255 cm (`WP_FloodedLedge`), all >= 150; nearest crypt AI point (Patrol, Search, WSpawn): 325 (`Search_Crypt_09`), 372 (`_02`), 410 (`_13`), 561 (`_12`) cm, all >= 150; nearest existing emitter 511 / 716 / 758 / 633 cm, all >= 400; rats at least 1161 cm apart.
- A first R4 candidate on the east wall (11475, -1100) was dropped: it was 51 cm from the `WP_CryptToCloister` lane.

**Census:** 3089 -> **3102** (+13); 48 actors in the folder `Audio` (7 zones, 7 volumes, 31 emitters, 3 water pads).

**Checks:**
- `--apply --resume --only creatures`: 29 PASS, 0 FAIL (13 emitter reads, 16 clearance items), 411 editor calls.
- Full `--check` (before the save): **107 PASS, 0 FAIL** (1474 editor calls); census 3102, folder content, the never-save list and all audio packages not dirty.
- `--save` (repeats the full check first, then saves): **126 PASS, 0 FAIL** (1721 editor calls); `save_assets` saved only `/Game/LastBell/Maps/L_Monastery`, `is_dirty` false afterwards; the 17 never-save packages and 226 audio packages (`Audio/**`, `PM_LB_*`, `DA_Audio`, `DT_Footsteps`; the 18 creature waves included) were not dirty before or after.
- Not verifiable here: how each creature sounds in the space (the owner's listening check), the howls' level at the player's position (ActiveRadius 15000 puts them inside the active set across most of the level; the attenuation is `ATT_LB_Large`), and whether the belfry bats are masked by the wind. No sound was played, no PIE.
