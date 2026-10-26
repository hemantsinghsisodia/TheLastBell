# Lane check P8-5 (ChapelNave, ChapelSacristy, SacristyToCrypt)

Run after the P8-5 structure was placed in `L_Monastery` (the greybox pews `Pew_*` (StaticMeshActor_114..121) and `Sac_Table` are still present and are included). Method: every segment is sampled every 2 cm; the clearance is the horizontal (XY) distance from the sample to the nearest blocking obstacle AABB. Required clearance: **>= 60 cm**.

Obstacles = every StaticMeshActor in X 5990..9030, Y -1620..830 (and Z -700..2400) whose collision profile blocks (101 actors/pieces after removing 49 NoCollision actors), plus the BP mechanism pedestal and the 4 puzzle candles. An obstacle counts at a sample only if it overlaps the capsule's height range [foot Z, foot Z + 176] and its top is above foot Z + 45 (`MaxStepHeight`), so floors, ground slabs and the 30 cm dais step are walkable, not obstacles (the `Stair_SacristyDown_*` treads are the walking surface and are excluded), and overhead pieces (corbels, gables, ceiling, lintels, railings above the stair shaft) are ignored. Wall pieces with an opening (`Ch_Wall_S3`, `Sa_Wall_W_Door`, `KC_MainDoorway`) are modelled as their two jambs, not their AABB. Doors (`BP_Door_Base_C_3/_4`) are opened by the test and excluded. The foot Z is interpolated along each segment.


## ChapelNave

| Segment | From | To | Min clearance (cm) | Nearest obstacle | Result |
|---|---|---|---|---|---|
| 00->01 | (6250, 0, 0) | (8350, 0, 0) | 100.1 | Ch_AltarRail | PASS |
| 01->02 | (8350, 0, 0) | (8380, 450, 0) | 79.9 | Ch_AltarRail | PASS |
| 02->03 | (8380, 450, 0) | (8700, 450, 0) | 150.1 | Ch_AltarRail | PASS |

## ChapelSacristy

| Segment | From | To | Min clearance (cm) | Nearest obstacle | Result |
|---|---|---|---|---|---|
| 00->01 | (6250, 0, 0) | (8350, 0, 0) | 100.1 | Ch_AltarRail | PASS |
| 01->02 | (8350, 0, 0) | (8380, -450, 0) | 79.9 | Ch_AltarRail | PASS |
| 02->03 | (8380, -450, 0) | (8500, -700, 0) | 78.1 | Ch_Wall_S3 (jamb 1) | PASS |
| 03->04 | (8500, -700, 0) | (8500, -1000, 0) | 60.0 | Ch_Wall_S3 (jamb 1) | PASS |

## SacristyToCrypt

| Segment | From | To | Min clearance (cm) | Nearest obstacle | Result |
|---|---|---|---|---|---|
| 00->01 | (8500, -1100, 0) | (8200, -1100, 0) | 170.9 | Sa_Wall_W_Door (jamb 1) | PASS |
| 01->02 | (8200, -1100, 0) | (7955, -1100, -15) | 60.0 | Sa_Wall_W_Door (jamb 1) | PASS |
| 02->03 | (7955, -1100, -15) | (7565, -1100, -210) | 65.0 | Sa_Wall_W_Door (jamb 1) | PASS |
| 03->04 | (7565, -1100, -210) | (7145, -1100, -420) | 155.0 | Ground_0 | PASS |
| 04->05 | (7145, -1100, -420) | (6905, -1100, -540) | 200.0 | Rock_007 | PASS |
| 05->06 | (6905, -1100, -540) | (6770, -1100, -600) | 200.0 | Rock_007 | PASS |
| 06->07 | (6770, -1100, -600) | (6550, -1100, -600) | 202.2 | Rock_007 | PASS |

**Overall: PASS**


## Notes

- `Ch_Wall_S3` jamb clearances of exactly 60.0 and the `Sa_Wall_W_Door` jamb clearances of 60.0 are the plan's doorway widths (clear 120 cm with the route on the centre line), not a measurement error.
- **Deviation from the plan (section 1.7):** `WalkPath.ChapelSacristy` point 02 is (8380, -450), not (8500, -450). The planned segment (8350, 0) -> (8500, -450) passes through the altar rail's south-west corner (8450, -300) (0 cm clearance, the rail is 100 cm tall, BlockAll). (8380, -450) is the mirror of the nave route's (8380, 450); the next leg (8380, -450) -> (8500, -700) clears the rail by more than 120 cm and arrives on the S3 doorway centre line (X 8500).
- The path legs inside the sacristy and on the stairs have no BlockAll geometry nearer than the jambs listed above; the P8-6 dressing must keep >= 60 cm from these lines.

---

# P8-6 lane check (after the dressing)

Same method as P8-5 (2 cm samples; clearance = horizontal distance to the nearest blocking AABB; obstacle counted only if it overlaps [foot Z, foot Z + 176] and its top is above foot Z + 45; stair treads and SkySphere excluded; `Ch_Wall_S3` and `Sa_Wall_W_Door` modelled as their two jambs; doors excluded). Run against the saved-state editor level with all P8-6 dressing in place (111 blocking StaticMeshActors in X 5990..9030, Y -1620..830, 181 NoCollision actors skipped). Required clearance: **>= 60 cm**. Routes unchanged from P8-5 (ChapelSacristy point 02 stays (8380, -450)).

## ChapelNave

| Segment | From | To | Min clearance (cm) | Nearest obstacle | Result |
|---|---|---|---|---|---|
| 00->01 | (6250, 0, 0) | (8350, 0, 0) | 100.1 | Ch_AltarRail | PASS |
| 01->02 | (8350, 0, 0) | (8380, 450, 0) | 79.9 | Ch_AltarRail | PASS |
| 02->03 | (8380, 450, 0) | (8700, 450, 0) | 150.1 | Ch_AltarRail | PASS |

## ChapelSacristy

| Segment | From | To | Min clearance (cm) | Nearest obstacle | Result |
|---|---|---|---|---|---|
| 00->01 | (6250, 0, 0) | (8350, 0, 0) | 100.1 | Ch_AltarRail | PASS |
| 01->02 | (8350, 0, 0) | (8380, -450, 0) | 79.9 | Ch_AltarRail | PASS |
| 02->03 | (8380, -450, 0) | (8500, -700, 0) | 78.1 | Ch_Wall_S3 (jamb 1) | PASS |
| 03->04 | (8500, -700, 0) | (8500, -1000, 0) | 60.0 | Ch_Wall_S3 (jamb 1) | PASS |

## SacristyToCrypt

| Segment | From | To | Min clearance (cm) | Nearest obstacle | Result |
|---|---|---|---|---|---|
| 00->01 | (8500, -1100, 0) | (8200, -1100, 0) | 170.9 | Sa_Wall_W_Door (jamb 1) | PASS |
| 01->02 | (8200, -1100, 0) | (7955, -1100, -15) | 60.0 | Sa_Wall_W_Door (jamb 1) | PASS |
| 02->03 | (7955, -1100, -15) | (7565, -1100, -210) | 65.0 | Sa_Wall_W_Door (jamb 1) | PASS |
| 03->04 | (7565, -1100, -210) | (7145, -1100, -420) | 155.0 | Ground_0 | PASS |
| 04->05 | (7145, -1100, -420) | (6905, -1100, -540) | 200.0 | Rock_007 | PASS |
| 05->06 | (6905, -1100, -540) | (6770, -1100, -600) | 200.0 | Rock_007 | PASS |
| 06->07 | (6770, -1100, -600) | (6550, -1100, -600) | 202.2 | Rock_007 | PASS |

**Overall: PASS**


Nearest P8-6 dressing blocker per route (separate measurement, BlockAll dressing only): ChapelNave 196.2 cm (`Ch_Lectern`), ChapelSacristy 200.1 cm (`Ch_Pew_N2`; the south pews sit at Y <= -201.9), SacristyToCrypt 150.5 cm (`Sa_Bench`). The minimum clearances above are therefore unchanged from P8-5: they are set by the rail and the doorway jambs, not by the dressing.

Other P8-6 geometry checks (bounds read back):
- Aisle rule (no BlockAll in Y -200..200, X 6060..8350): none; the nearest pew edges are at |Y| 200.1 (N2, N4) and 201.9 (S4).
- Puzzle zone (no dressing actor in X 8550..8830, |Y| <= 260): none; the nearest are the altar stands (X 8859..8901) and the open shackles (|Y| >= 338).

Update after the P8-6c fixes (`Sa_Chair` replaced by the tipped `Sa_Stool` at X 8409-8471, Y -1320..-1260, BlockAll): SacristyToCrypt (8500,-810)->(8500,-1100)->(7980,-1100) nearest dressing blockers are `Sa_Bench` 150.5 cm and `Sa_Stool` 159.5 cm; the route minimum is still 60.0 cm from the `Sa_Wall_W_Door` jambs (the P8-6 table above is unchanged).


---

# P8-10 lane check (after the grime pass: decals, debris, cobwebs, MI swaps)

Same method as P8-5/P8-6 (2 cm samples; clearance = horizontal distance to the nearest blocking AABB; obstacle counted only if it overlaps [foot Z, foot Z + 176] and its top is above foot Z + 45; stair treads and SkySphere excluded; `Ch_Wall_S3` and `Sa_Wall_W_Door` modelled as their two jambs; doors excluded). Run against the saved-state editor level with all P8-10b content in place (493 actors in X 5990..9030, Y -1620..830: **111 blocking StaticMeshActors (unchanged from P8-6)**, 212 NoCollision skipped, 59 DecalActors ignored, 22 new grime StaticMeshActors, all NoCollision). Required clearance: **>= 60 cm**. Routes unchanged (ChapelSacristy point 02 stays (8380, -450)).

The grime pass adds no blocking geometry, so the minimum clearances are identical to the P8-6 table: they are set by the altar rail and the doorway jambs.

## ChapelNave

| Segment | From | To | Min clearance (cm) | Nearest obstacle | Result |
|---|---|---|---|---|---|
| 00->01 | (6250, 0, 0) | (8350, 0, 0) | 100.1 | Ch_AltarRail | PASS |
| 01->02 | (8350, 0, 0) | (8380, 450, 0) | 79.9 | Ch_AltarRail | PASS |
| 02->03 | (8380, 450, 0) | (8700, 450, 0) | 150.1 | Ch_AltarRail | PASS |

## ChapelSacristy

| Segment | From | To | Min clearance (cm) | Nearest obstacle | Result |
|---|---|---|---|---|---|
| 00->01 | (6250, 0, 0) | (8350, 0, 0) | 100.1 | Ch_AltarRail | PASS |
| 01->02 | (8350, 0, 0) | (8380, -450, 0) | 79.9 | Ch_AltarRail | PASS |
| 02->03 | (8380, -450, 0) | (8500, -700, 0) | 78.1 | Ch_Wall_S3 (jamb 1) | PASS |
| 03->04 | (8500, -700, 0) | (8500, -1000, 0) | 60.0 | Ch_Wall_S3 (jamb 1) | PASS |

## SacristyToCrypt

| Segment | From | To | Min clearance (cm) | Nearest obstacle | Result |
|---|---|---|---|---|---|
| 00->01 | (8500, -1100, 0) | (8200, -1100, 0) | 170.9 | Sa_Wall_W_Door (jamb 1) | PASS |
| 01->02 | (8200, -1100, 0) | (7955, -1100, -15) | 60.0 | Sa_Wall_W_Door (jamb 1) | PASS |
| 02->03 | (7955, -1100, -15) | (7565, -1100, -210) | 65.0 | Sa_Wall_W_Door (jamb 1) | PASS |
| 03->04 | (7565, -1100, -210) | (7145, -1100, -420) | 155.0 | Ground_0 | PASS |
| 04->05 | (7145, -1100, -420) | (6905, -1100, -540) | 200.0 | Rock_007 | PASS |
| 05->06 | (6905, -1100, -540) | (6770, -1100, -600) | 200.0 | Rock_007 | PASS |
| 06->07 | (6770, -1100, -600) | (6550, -1100, -600) | 202.2 | Rock_007 | PASS |

### Grime debris and cobwebs: clearance to every WalkPath segment and the aisle rule

Per-actor world AABB (XY) distance to the nearest WalkPath segment (all three chapel lanes, 2 cm sampling), and whether the AABB intrudes into the central aisle (Y -200..200, X 6060..8350). Required: >= 60 cm and no intrusion for the floor debris (Branch, Grit, Slate); cobwebs (overhead or on furniture, NoCollision) are reported for information.

| Actor | AABB X | AABB Y | Z | Collision | Min dist to WalkPath (cm) | In aisle | Result |
|---|---|---|---|---|---|---|---|
| Ch_CobwebHang_1 | 6994..7006 | -255..-105 | 1635..1715 | NoCollision | 105.0 | yes | PASS |
| Ch_CobwebHang_2 | 7994..8006 | 75..225 | 1635..1715 | NoCollision | 75.0 | yes | PASS |
| Ch_CobwebHang_3 | 6994..7006 | 125..275 | 1635..1715 | NoCollision | 125.0 | yes | PASS |
| Ch_CobwebHang_4 | 6989..7011 | -130..-10 | 1648..1712 | NoCollision | 9.8 | yes | PASS |
| Ch_CobwebHang_5 | 6986..7014 | 5..155 | 1640..1720 | NoCollision | 4.8 | yes | PASS |
| Ch_CobwebHang_6 | 7989..8011 | -143..-7 | 1645..1717 | NoCollision | 7.3 | yes | PASS |
| Ch_CobwebHang_7 | 7987..8013 | 255..405 | 1640..1720 | NoCollision | 254.8 | no | PASS |
| Ch_Cobweb_Lectern | 8088..8136 | 636..684 | 12..60 | NoCollision | 306.8 | no | PASS |
| Ch_Cobweb_NE | 8840..8960 | 630..750 | 1000..1120 | NoCollision | 227.3 | no | PASS |
| Ch_Cobweb_NW | 6060..6180 | 630..750 | 1000..1120 | NoCollision | 633.3 | no | PASS |
| Ch_Cobweb_Pew_N3 | 7421..7469 | 662..710 | 45..93 | NoCollision | 662.0 | no | PASS |
| Ch_Cobweb_Pew_S3 | 7456..7504 | -714..-666 | 45..93 | NoCollision | 386.0 | no | PASS |
| Ch_Cobweb_Splay_N1 | 6410..6470 | 728..788 | 930..990 | NoCollision | 728.0 | no | PASS |
| Ch_Cobweb_Splay_N2 | 7410..7470 | 728..788 | 930..990 | NoCollision | 728.0 | no | PASS |
| Ch_Grime_Branch_1 | 6292..6388 | -490..-390 | 1..21 | NoCollision | 389.8 | no | PASS |
| Ch_Grime_Branch_2 | 6564..6636 | -285..-205 | 1..18 | NoCollision | 205.4 | no | PASS |
| Ch_Grime_Branch_3 | 6295..6405 | -350..-250 | 1..25 | NoCollision | 249.6 | no | PASS |
| Ch_Grime_Grit_1 | 6120..6142 | 683..706 | 1..13 | NoCollision | 691.4 | no | PASS |
| Ch_Grime_Grit_2 | 6200..6220 | 722..740 | 1..12 | NoCollision | 722.6 | no | PASS |
| Ch_Grime_Grit_3 | 8920..8937 | 698..714 | 1..10 | NoCollision | 331.7 | no | PASS |
| Ch_Grime_Grit_4 | 8883..8905 | -714..-690 | 1..15 | NoCollision | 383.3 | no | PASS |
| Ch_Grime_Grit_5 | 6095..6121 | -655..-630 | 1..14 | NoCollision | 617.9 | no | PASS |
| Ch_Grime_Grit_6 | 6655..6680 | -720..-694 | 1..15 | NoCollision | 379.8 | no | PASS |
| Ch_Grime_Grit_7 | 6829..6850 | -749..-729 | 1..12 | NoCollision | 350.9 | no | PASS |
| Ch_Grime_Grit_8 | 6552..6572 | -751..-730 | 1..12 | NoCollision | 348.6 | no | PASS |
| Ch_Grime_Slate_1 | 6838..6982 | -373..-247 | 0..22 | NoCollision | 247.2 | no | PASS |
| Ch_Grime_Slate_2 | 6855..7005 | -739..-597 | 0..22 | NoCollision | 360.7 | no | PASS |

**Debris overall: PASS**

**Lane overall: PASS**


Notes (P8-10b):
- The four new truss cobwebs (`Ch_CobwebHang_4..6`, and the three older hang cards) are at Z 1635..1720, far above the capsule (176 cm), so their XY overlap with the aisle/route lines is irrelevant and they are NoCollision; `Ch_CobwebHang_7`, the splay, pew and lectern cobwebs are off the lanes anyway.
- All 13 floor debris actors (3 `Ch_Grime_Branch`, 8 `Ch_Grime_Grit`, 2 `Ch_Grime_Slate`) are NoCollision (profile and `bUseDefaultCollision=false` read back), stand outside Y -200..200 for X 6060..8350, and are at least 205 cm from every WalkPath segment (>= 60 required).
- Decal exclusions (checked on each decal's rotated world AABB against: the puzzle zone X 8550..8830 / |Y| <= 260 / Z 0..250; the four `BP_PuzzleCandle` bounds; the clue plaque X 8688..8812 / Y 742..750 / Z 300..544; the altar X 8848..8952 / |Y| <= 150 / Z 30..131 and `Altar_Ritual1`): 0 intersections for all 59 decals. Floor decal boxes are 8 cm deep (Z -3.5..4.5), wall decal boxes 12 cm deep, 2 cm in front of the wall face and 10 cm into it.
