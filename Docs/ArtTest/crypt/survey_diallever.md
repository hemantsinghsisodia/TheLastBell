# BP_DialLever survey (P9-R2A, read only)

Source: `/Game/LastBell/Blueprints/Puzzles/BP_DialLever` (class `BP_DialLever_C`), read through the Unreal MCP in the live editor on 2026-10-28:
component templates (`ObjectTools.get_properties` on `<BP>_C:<Comp>_GEN_VARIABLE`, parents with `ActorTools.get_parent_component`), CDO variables, and `read_graph_dsl` on every graph.
Nothing was changed or saved. The engine basic shapes are all 100 cm (`StaticMeshTools.get_bounds`: Cube, Cylinder O100 x 100, Sphere O100, all centred on the origin).

## Variables (CDO defaults)
| variable | value |
|---|---|
| `notchPitch` | 35.0 (degrees) |
| `startPitch` | 0.0 (runtime: pitch at the start of a move) |
| `targetPitch` | 0.0 (runtime) |
| `moveDuration` | 0.4 s (smoothstep lerp of `handlePivot` relative rotation) |
| `labelText` | `A` (the placed Lever_A / B / C override it) |
| `lockTag` | None |

## Pitch logic (graphs)
- `PitchForIndex(Index) = (clamp(Index, 0, 2) - 1) * notchPitch` -> index 0 = **-35 deg (low)**, index 1 = **0 deg (mid)**, index 2 = **+35 deg (high)**.
- `SnapHandle`, `StartMove` and `StepMove` only call `SetRelativeRotation(handlePivot, MakeRotator(roll 0, pitch p, yaw 0))`; nothing else is rotated.
- The construction script only does `Label.SetText(labelText)`. There is no mesh assignment in the construction script (the meshes are template defaults).
- `RefreshLock` toggles `dialComp.bLocked` and `interactComp.bEnabled`; the other graphs bind the world-state and dial events. None of that is touched by R2-A.

## Component hierarchy and transforms (actor space, actor at the origin; placed levers: yaw -90, at (11040 / 10920 / 10800, -1503, -600))
```
DefaultSceneRoot (0,0,0)
 |- backplate    loc (0, 0, 45)        rot 0              scale (0.06, 0.3, 0.9)     Cube      MI_LB_DarkWood
 |- rail         loc (46, 12, 45)      rot 0              scale (0.03, 0.04, 0.6)    Cube      MI_LB_Iron
 |- notchHigh    loc (46, 12, 67.94)   rot 0              scale (0.06, 0.05, 0.025)  Cube      MI_LB_Bronze
 |- notchMid     loc (46, 12, 45)      rot 0              scale (0.06, 0.05, 0.025)  Cube      MI_LB_Bronze
 |- notchLow     loc (46, 12, 22.06)   rot 0              scale (0.06, 0.05, 0.025)  Cube      MI_LB_Bronze
 |- label        loc (3.6, 0, 82)      TextRender "A", size 16, centre / centre, colour (0.851, 0.780, 0.600)
 |- handlePivot  loc (6, 0, 45)        rot (pitch = animated)   no mesh
 |   |- arm      loc (22.5, 0, 0)      rot pitch 90       scale (0.03, 0.03, 0.45)   Cylinder  MI_LB_Iron
 |   `- weight   loc (47, 0, 0)        rot 0              scale (0.1, 0.1, 0.1)      Sphere    MI_LB_Bronze
 |- interactComp, dialComp (no transform)
```
- Notch heights: `45 +- 22.94` where `22.94 = 40 * sin(35 deg)` (the notch x is a flat 46, so they are heights only, not points on the arm's arc).
- **The arm hangs out horizontally from the pivot**, not down: at pitch 0 it points along +X (away from the board), at pitch p it is tilted up by p (UE pitch: local X -> world Z). The arm cylinder is rotated pitch 90, so its **mesh +Z points toward the pivot and mesh -Z toward the free end**: the grip must sit at mesh -Z.
- Arm tip (arm end at 45 along the arm, weight centre at 47): at -35 / 0 / +35 deg the weight centre is at (44.5, 0, 18.0) / (53, 0, 45) / (44.5, 0, 72.0) in actor space.
- The weight is a child of `handlePivot`, so it turns with the arm (rigid): a chain rising along mesh +Z leans back toward the board when the arm is raised.

## Local-space AABBs of the replaced components (mesh-local, pivot = primitive centre; scale 1 child BP)
| component | engine mesh x scale | local AABB (X, Y, Z) | size | actor-space / parent-space extent |
|---|---|---|---|---|
| `backplate` | Cube x (0.06, 0.3, 0.9) | +-3, +-15, +-45 | 6 x 30 x 90 | X +-3, Y +-15, Z 0..90 |
| `rail` | Cube x (0.03, 0.04, 0.6) | +-1.5, +-2, +-30 | 3 x 4 x 60 | X 44.5..47.5, Y 10..14, Z 15..75 |
| `notchHigh/Mid/Low` | Cube x (0.06, 0.05, 0.025) | +-3, +-2.5, +-1.25 | 6 x 5 x 2.5 | X 43..49, Y 9.5..14.5, Z centre +-1.25 |
| `arm` | Cylinder x (0.03, 0.03, 0.45) | +-1.5, +-1.5, +-22.5 (long axis mesh Z) | O3 x 45 | in handlePivot space: X 0..45, Y +-1.5, Z +-1.5 |
| `weight` | Sphere x 0.1 | +-5, +-5, +-5 | O10 | in handlePivot space: X 42..52, Y +-5, Z +-5 |

## R2-A meshes (final bounds, mesh-local; measured from the exported FBX by `verify_props.py`)
| mesh | min | max | size | vs the surveyed AABB |
|---|---|---|---|---|
| `SM_LB_Prop_DialLever_Backplate` | -3.0, -15.0, -45.0 | 3.8, 15.0, 45.0 | 6.8 x 30 x 90 | X +0.8 (rivet heads / bolt dome proud to x 3.8; board face at 3.0) |
| `SM_LB_Prop_DialLever_Quadrant` | -1.9, -2.0, -30.0 | 1.5, 2.0, 30.0 | 3.4 x 4 x 60 | X +0.4 (studs on the back face) |
| `SM_LB_Prop_DialLever_Arm` | -2.0, -1.95, -22.5 | 2.0, 1.95, 22.5 | 4.0 x 3.9 x 45 | cross-section +1.0 / +0.9 (grip O4 max; rod is O2.5) |
| `SM_LB_Prop_DialLever_Weight` | -5.0, -5.0, -7.0 | 5.0, 5.0, 46.84 | 10 x 10 x 53.84 | X/Y exact; Z extended upward: body -7..7, ring to 10.9, 12 links, terminal ring top 46.84 |
| `SM_LB_Prop_DialLever_NotchStop` | -2.5, -2.25, -1.5 | 2.5, 2.25, 1.5 | 5 x 4.5 x 3 | within 1 cm of both the survey (6 x 5 x 2.5) and the spec (4 x 4 x 3) |

Placement for the child BP (all scale 1, **same relative locations and rotations as the parent**): the pivots are the primitive centres, so nothing moves.
- Label plate (on the backplate): 18 x 18, y +-9, mesh z 26..44 (actor z 71..89), front face x 3.5. The TextRender at x 3.6, z 82 (mesh z 37) sits 0.1 cm in front of it; glyph size 16 fits (caps about 11.5 cm tall).
- Quadrant notch slots: mesh z -22.94 / 0 / +22.94 = the three notch heights; the three NotchStop meshes sit on them.
- Arm: grip at mesh z -22.5..-10.5 (free end), pivot knuckle at +21 with its pin along mesh Y (the swing axis).

## Observations for R2-B (not changed in R2-A)
- `rail` and the three `notch*` stops float 40 cm in front of the board (x 46, y 12) with nothing holding them, and the rail's bottom is 15 cm above the board's bottom. The greybox had the same layout; the child BP keeps it.
- The weight sits on the arm's end (x 47 vs arm end 45), so the chain rises from the weight and its upper end is free; a hanging weight (chain going down) would put the weight below the floor at the low and mid poses (45 - 47 = -2), which is why the chain rises.
- The arm swings in the actor XZ plane at y 0; the stops are 12 cm to the side (y 12).
