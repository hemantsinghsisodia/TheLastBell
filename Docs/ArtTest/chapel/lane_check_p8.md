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
