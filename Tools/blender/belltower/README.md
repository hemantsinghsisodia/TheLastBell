# Bell tower pieces T1-T14 (P10-3a) -- Blender build scripts

Procedural, seeded, headless (Blender 5.2, no GUI, no Blender MCP, no Unreal Editor). Spec: `Docs/plans/P10_BELLTOWER_ART.md` amendment D1.0 / D1.1 / D1.2 / D1.5.
The cloister and Mechanism 3 pieces (C*, M*) are built by the other P10 agent (`build_cloister.py`); this section is the tower only.
The kit helpers are imported, never modified: `Tools/blender/kit/kit_lib.py`, `build_kit.py` (`ashlar_body`, `carve_and_merge`, `hood_mould`, `sloped_sill`), `Tools/blender/props/build_props.py` (`bool_op`, `chain_link`, `sphere_z`).

## Commands (run from the repo root)
```
set B="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"

# build all 33 meshes: FBX + LB_BellTower.blend + tower_report.json -> SourceArt/BellTower/   (about 35 s)
%B% -b --factory-startup --python Tools/blender/belltower/build_tower.py -- --out SourceArt/BellTower
#    optional: --only GreatBell Roof S3_      (substring filter; writes LB_BellTower_partial.blend, merges the report)   --tag NAME  (names the partial blend)

# verify: re-imports every FBX in a clean Blender, checks it against D1 (exit code 1 on failure)
%B% -b --factory-startup --python Tools/blender/belltower/verify_tower.py

# review renders (Cycles, the real D1 placement tables, assembly mirrored in Y to show the in-game handedness) -> Docs/ArtTest/belltower/p10_3a_*.png
%B% -b --factory-startup --python Tools/blender/belltower/render_tower.py -- --set all --samples 96
#    --set faces | section | flights | belfry | bell    --only <name part>    --res W H    --out DIR
```

## Files
- `tw_common.py` shared helpers (slot materials, `TP` piece record, tubes, oriented beams, cylindrical UV), `tw_walls.py` (S1/S2/S3 x W/N/E/S + the two `_BrokenSW`), `tw_timber.py` (T1-T11 except the bell),
  `tw_bell.py` (T12 great bell, T13 rope + sally), `tw_roof.py` (T14). `build_tower.py` holds the piece table and the export.
- `verify_tower.py`, `render_tower.py` (also contains the assembly: the D1.1 face frames, D1.2 flight / landing / belfry transforms).

## Conventions
- Authoring space == Unreal space, 1 BU = 1 cm; FBX through `kit_lib.export_piece_fbx` (Y mirrored at export, as for every kit / prop piece).
- **Each piece is built directly in its D1 frame and is NOT re-seated** (face frame: local Y 0 = inner face, Y 40 = outer face, stage base z 0; flight frame; landing top-min-corner; ...).
  Bounds therefore are not "min = 0" for the courses that run past the piece ends; the exact bounds of every piece are in `tower_report.json` and in the SPEC table of `verify_tower.py`.
- Slot names / order as D1: wall pieces `MAT_Masonry, MAT_Trim, MAT_Rubble`; T1 / T2... `MAT_Wood, MAT_Iron`; T3 `MAT_Wood, MAT_Masonry`; T4 `MAT_Masonry, MAT_Trim, MAT_Rubble, MAT_Wood`; T12 `MAT_Bronze, MAT_Iron`;
  T13 `MAT_Rope, MAT_Sally`; T14 `MAT_Slate, MAT_Wood, MAT_Iron`.
- Collision (D1.5): only `BellFrame_A` (4 post boxes) and `GreatBell_A` (1 convex hull of the outer profile, 128 verts); every other mesh has no UCX (the shaft base gets none).
- Vertex colour `Color` white; UV0 = kit box projection 1 UV / 100 cm, except the great bell (cylindrical) and the rope (u around, v = depth / 140).
- Seeds: walls 1001-1012 (table order S1 W N E S, S2 ..., S3 ...; the BrokenSW pieces reuse their intact piece's seed, break profiles 1003 / 1004), T1 1101 (Closed same), 1102, 1103, T2 1104, T3 1105, T4 1106, T5 1107, T6 1108, T8 1109, T9 1119 / 1120, T10 1110, T11 (no randomness), T12 1112, T13 1114, T14 1113.

## Piece names (`SM_LB_Tw_*`, props `SM_LB_Prop_*`)
Walls: `S1_W S1_N S1_E S1_S S2_W S2_N S2_E S2_S S3_W S3_N S3_E S3_S S3_W_BrokenSW S3_S_BrokenSW` (the D1 table names; no size suffix). `Roof_BrokenSW`, `Louvre_130x450`, `Louvre_130x450_Broken`, `ShaftBase_420x420x450`, `ShaftPost_20x20x2015`,
`StairFlight_250x420` (+ `_Closed`, `_BrokenA`, `_BrokenB`), `FlightRail_420`, `Landing_250`, `BelfryFloor`, `TopRail_670`, `TopRail_420`, `Partition_250x455`, `BellFrame_A`, `BellHeadstock_A`; `SM_LB_Prop_GreatBell_A`, `SM_LB_Prop_BellRope_2610`.

## Deviations from / clarifications of D1 (also in the task report)
- **N / S exterior courses run 40 past the piece ends (W / E: by the projection, as D1.1).** "By the projection" leaves a 30 cm notch at every outer corner (the W / E piece's wall face is 40 wide and carries no course there); 40 lets the N / S course butt the W / E course.
  N / S wall bounds are therefore x -40 .. L + 40.
- Corner quoins (alternating 52 x 24 / 30 x 40) on the W / E pieces' outer corners (not in D1; trim slot).
- `BellHeadstock_A` carries a short iron staple + 130 cm chain at the wheel rim's 3 o'clock: D1 puts the rope top 130 below the axle (z 2750) while the wheel's tangent point for a vertical rope is at axle height (z 2880); the chain closes that gap.
- Great-bell canons are in `MAT_Iron` ("iron-coloured bronze"). The roof's slates are tilted 5 cm (lower end up) so the outer surface lies 0..5 cm below the ideal pyramid plane; bounds +-525.6.
- `BelfryFloor` has extra joists under the W and N slabs (visible from the W-ring flights) and its core-top beams run x 240..680 as D1 (bounds x 0..680).
- `Closed` flight has no iron brackets (hidden). `_Broken` louvre keeps 7 of 9 boards (boards 3 and 4 missing, board 5 at 70 degrees).
