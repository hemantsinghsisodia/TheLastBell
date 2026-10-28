# Courtyard props (P7F-2) -- Blender build scripts

Procedural (own models) + Poly Haven CC0 conversions. Headless Blender 5.2, no GUI, no Blender MCP. Plan: `Docs/plans/P7_FIX2_COURTYARD_POLISH.md` section P7F-2.
Shared helpers: `Tools/blender/kit/kit_lib.py` (`cylinder`, `ring` were added for this; the kit itself is unchanged and still passes 28/28).

## Commands (run from the repo root)

```
set B="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"

# 2b. procedural props: 12 FBX + LB_Props.blend + props_report.json   (about 5 s, seeded/reproducible)
%B% -b --factory-startup --python Tools/blender/props/build_props.py -- --out SourceArt/Props/Procedural
#    optional: --only Key Gravestone      (substring filter; writes *_partial files)

# verify (re-imports every FBX; exit code 1 on failure)
%B% -b --factory-startup --python Tools/blender/props/verify_props.py

# review renders (Workbench) -> Docs/ArtTest/props/*.png
%B% -b --factory-startup --python Tools/blender/props/render_props.py

# 2a. CC0 conversion of the 16 Poly Haven glTF downloads -> SourceArt/Props/CC0/<CamelName>/ (FBX + textures + cc0_report.json)
%B% -b --factory-startup --python Tools/blender/props/convert_cc0.py -- --src ExternalAssets/Incoming --out SourceArt/Props/CC0
#    optional: --only wine_barrel_01 moss_01      (ids; the report keeps the other records)
#    optional: --split-all                        (also split the joined multi-variant models: weed, nettle, moss, branches, barrel parts -> _01.._NN)

# kit regression (must stay 28/28 after any kit_lib change)
%B% -b --factory-startup --python Tools/blender/kit/verify_kit.py
```

## Conventions (same as the kit)
- 1 Blender unit = 1 cm; authoring space == Unreal space. FBX via `kit_lib.export_piece_fbx` (`axis_forward='Y'`, `axis_up='Z'`, cm,
  Y mirrored at export = `ue_y_flip`, `mesh_smooth_type='OFF'`). `verify_props.py` accounts for the mirror (`UE_Y = -Blender_Y`).
- **Pivot = bottom-centre** for every prop: XY centre of the visual bounds at the origin, min Z = 0 (`pivot_shift_applied` in the reports
  says how far the design origin moved, e.g. the hand-cart axle sits at X -55 after seating).
- Vertex colour `Color` = white. UV0: procedural props use the kit 1 UV = 100 cm box projection; CC0 props keep their original UVs.
- Procedural slot names: `MAT_Iron`, `MAT_Stone`, `MAT_Trim`, `MAT_Wood`, `MAT_Rope`, `MAT_Earth`, `MAT_Charred` (only used slots are exported).
  CC0 slot names = the original glTF material names (e.g. `wine_barrel_01`). Collision: `UCX_<Mesh>_NN` boxes in the same FBX.
- Props face +Y in authoring space (gravestone relief, cross); the level yaws them. Key lies flat: bow at -X, bit toward -Y, bit teeth point -Y.
- Outputs: `SourceArt/Props/Procedural/` (FBX, `LB_Props.blend`, `props_report.json`), `SourceArt/Props/CC0/<Name>/` (FBX, textures, `../cc0_report.json`).

## P7-FIX3 G2a additions

```
set B="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"

# new procedural props only (17 pieces; the 12 existing FBX are not rewritten). Ivy FBX + atlas textures go to SourceArt/Props/Procedural/Ivy/
%B% -b --factory-startup --python Tools/blender/props/build_props.py -- --only WellHead TimberPost Purlin Rafter RoofPlanks EarthPatch DeadTree Ivy --tag Fix3
#    -> LB_Props_Fix3.blend + props_report_Fix3.json ; verify (29/29 incl. the 12 old ones):
%B% -b --factory-startup --python Tools/blender/props/verify_props.py

# CC0 conversions: grass_medium_02 (5 clumps), wild_rooibos_bush (5), searsia_lucida (7), dead_tree_trunk_02 (1, converted UPRIGHT, thick end down)
%B% -b --factory-startup --python Tools/blender/props/convert_cc0.py -- --only grass_medium_02 wild_rooibos_bush searsia_lucida dead_tree_trunk_02

# review renders -> Docs/ArtTest/props/fix3_*.png (kit pieces, props incl. Cycles ivy with the real atlas + opacity, CC0 plants)
%B% -b --factory-startup --python Tools/blender/props/render_fix3.py -- --blend SourceArt/Kit/LB_Kit_Fix3.blend --set kit
%B% -b --factory-startup --python Tools/blender/props/render_fix3.py -- --blend SourceArt/Props/Procedural/LB_Props_Fix3.blend --set props
%B% -b --factory-startup --python Tools/blender/props/render_fix3.py -- --set cc0
```
- `WellHead_A` (slots Stone, Wood, Rope, Iron, Water; UCX 8 convex ring sides + 2 post boxes), timber set (`TimberPost` 1 UCX, `Purlin`/`Rafter*`/`RoofPlanks*` no UCX; **timber is authored upright, length along Z**; the level lays it down),
  `EarthPatch_400x400x15` (UCX 400x400x8).
- `DeadTree_A`: seeded bpy branching tree (the BlenderKit tree is a single 1.7 m pole with no limbs and a 4K colour-only texture, so it was rejected); slot `MAT_Bark`, UV 1 tile / 150 cm (use the DeadTreeTrunk bark textures); built to exactly 700 cm tall.
- `Ivy_{Climb_300x450,Patch_200x300,Hang_150x600,Creep_400x200}_{Green,Dead}`: pivot = X centre, back plane at **Y 0 (wall side)**, min Z 0 (not bottom-centre in Y); slots `MAT_Leaf`, `MAT_Stem`; UV0 = atlas leaf cells
  (cell rects in `IVY_ATLAS` in build_props.py; Green = LeafSet017 (6 cells, tip up), Dead = LeafSet030 (12 oak cells, petiole right -> mapped rotated)); Color/Opacity/Roughness/NormalGL copied next to the FBX. Leaves face +Y. No UCX.
- `build_props.py` options: `--tag NAME` names the partial blend/report (default `partial`). `kit_lib.finalize(keep_uv=True)` keeps the custom UVs (ivy, tree).

## P8-3 chapel props (20 pieces)
```
%B% -b --factory-startup --python Tools/blender/props/build_props.py -- --only Truss Pew AltarRail Lectern Altar MechShell SlateShards CrossFinial Backdrop Glass_ Cobweb PricketStand CandleFlame --tag P8
%B% -b --factory-startup --python Tools/blender/props/verify_props.py                  # 49/49 (29 + 20), incl. structural ray checks (truss roof plane / arch brace, pew seat, altar core + hole)
%B% -b --factory-startup --python Tools/blender/props/render_p8.py -- --blend SourceArt/Props/Procedural/LB_Props_P8.blend --set props   # Docs/ArtTest/props/p8_*.png (views in render_p8_props.py)
python Tools/textures/gen_chapel_textures.py                                           # ExternalAssets/Generated/chapel/*.png + Docs/ArtTest/chapel/tex_*.png
```
Pivot = bottom-centre of the bounds (props rule): `Cobweb_Hang_A` (Y sag 12) and `PricketStand_150` (tripod, shaft 4.5 cm off the bbox centre in Y) are the two pieces whose design axis is not the bbox centre; see the per-piece notes in `SourceArt/Props/Procedural/props_report_P8.json`.

## P9-3 crypt pieces (21 meshes, plan `Docs/plans/P9_CRYPT_ART.md` amendment D1.3)
```
set B="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
%B% -b --factory-startup --python Tools/blender/props/build_props.py -- --only Crypt Crank --tag P9    # ~25 s -> SourceArt/Props/Procedural/Crypt/ (FBX + LB_Props_P9.blend + props_report_P9.json)
%B% -b --factory-startup --python Tools/blender/props/verify_props.py                                  # 72/72: the 51 older pieces + the 21 new ones (exit 1 on failure)
%B% -b --factory-startup --python Tools/blender/props/render_p9.py -- --set work                        # Workbench views of every piece -> Docs/ArtTest/crypt/p9_*.png
%B% -b --factory-startup --python Tools/blender/props/render_p9.py -- --set cycles                      # Cycles: ossuary bay, portcullis, roots A (about 30 s)
python Tools/blender/props/lineup_p9.py                                                                 # composite Docs/ArtTest/crypt/p9_lineup.png (Pillow)
python Tools/textures/gen_crypt_textures.py                                                             # T_LB_Water_Ripple_N.png (seed 9320) -> ExternalAssets/Generated/crypt/ + preview Docs/ArtTest/crypt/tex_water_ripple.png
```
- Prefix `SM_LB_Crypt_` (the crank is `SM_LB_Prop_Crank_A`); FBX, the review blend and the report all sit in `Crypt/` when a run builds only crypt pieces. Slots: `MAT_Stone`, `MAT_Wood`, `MAT_Iron`, `MAT_Charred`, `MAT_Bark` (in the order stated per piece in the report / verify SPEC).
- **Pivots are not all bottom-centre** (new `Piece.seat_mode` values `centre3`, `xy`, `backcentre`, `top`; `wall` and `none` already existed):
  OssuaryBay = x centre, y 0 = the wall front face (body y -90..0, bands to +6, local +Y into the room), z 0; Stair40 = x 0 at the riser face of step 0, y centre, z 0; Corbel_A and PlaqueFrame = back plane y 0 (frame: z centre as well);
  RootsHang = top-centre (the knot axis on the origin, z 0 = the flat attachment, hangs to -180/-240/-120); Block_100_C and CapstanDrum = bounds centre; Boards_Broken = XY centre, z as built (lowest point about -46).
- Stone pieces are built on `gbox` (kit `lattice_box`, a regular quad grid) before booleans/weathering: never use `subdiv_long` for this (it makes strips, which shade as streaks) and never `densify` after a boolean (slivers explode the triangle count).
- Collision (UCX boxes match D1.3 exactly, verified as a set): Block_100 and _C (100^3), Portcullis (x +-150, y +-30, z 0..560), RubbleFill (x +-50, y +-200, z 0..560), Crank (44 x 16 x 16, bottom-centre), CapstanDrum (x +-35, y +-35, z +-25), WinchFrame (2 posts 20 x 20 x 250, 2 plates 20 x 90 x 10).
- Deviations from D1.3 (also in the per-piece notes): Sarcophagus_B lid 280 x 104 rotated 3 deg, shifted +7 (280 x 120 rotated 3 deg cannot stay inside y +-60 / x +-150); Portcullis rails centred at x +-146 and four 6 x 60 x 6 guide pins give the 60 cm depth the table lists (lattice itself is within y +-4.5); Crank is 43 x 8 x 14.3 (socket boss and handle both point up, arm flat on the plinth); Boards: 10 boards run along X (300 long) stacked along Y (250), which is the only reading under which widths 22-27 sum to 250.

## P9-R2A bell wheel, dial-lever set, roof-hole gobo (7 meshes, plan amendment D1.25)
```
set B="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
%B% -b --factory-startup --python Tools/blender/props/build_props.py -- --only BellWheel DialLever Gobo_RoofHole --tag R2   # ~1 s -> SourceArt/Props/Procedural/R2/ (FBX + LB_Props_R2.blend + props_report_R2.json)
%B% -b --factory-startup --python Tools/blender/props/verify_props.py                                                       # 79/79: the 72 older pieces + the 7 new ones
%B% -b --factory-startup --python Tools/blender/props/render_r2.py -- --set all                                              # Docs/ArtTest/props/r2_*.png (single pieces, the lever assembled at -35 / 0 / +35, Cycles views)
```
- Names: `SM_LB_Prop_BellWheel_A`, `SM_LB_Prop_DialLever_{Backplate,Quadrant,Arm,Weight,NotchStop}`, `SM_LB_Gobo_RoofHole`. New slots: `MAT_Bronze`, `MAT_Paint` (bone white, NotchStop faces).
- **BellWheel_A**: bottom-centre, axle on Z; visual 89 x 89 x 58 (bell lips reach r 44.5), UCX 1 box 84 x 84 x 58; 7.2k tris.
- **Lever parts** replace the P4 greybox engine-primitive components of `BP_DialLever` one for one: **pivot = the primitive's centre** (`seat_mode "none"`), each built to that primitive's AABB (+-1 cm), so a child Blueprint uses scale 1.
  Survey, AABBs and the arm/notch geometry: `Docs/ArtTest/crypt/survey_diallever.md`. The arm's free end (grip) is mesh -Z (the component is rotated pitch 90).
- **Gobo_RoofHole**: 110 x 110 x 2, pivot centre, local X = thickness, local Y / Z = the moon spot's right / up (place with the spot's rotation, at L + 150 d). The cut-out is the RoofSlab_Broken hole outline
  (`roof_hole_outline()`, the exact boolean of `build_kit.hole_cutters(441)`) at slab-local Z 12, projected from `Light_Chapel_Moon_Roof` onto the plane D = 150 with `p = L + v * D / (v.d)` (as `Tools/crypt/r1b/s3_gobos.py`, there on the bbox corners),
  dilated by a true 1.5 cm disc (raster at 0.1 cm, traced, Douglas-Peucker 0.1) and cut from the plate with an exact boolean. Constants (`GOBO_SPOT_LOC/ROT`, `GOBO_D`, `GOBO_OFFSET`, `GOBO_PLANE_Z`) are at the top of that section of `build_props.py`.
  The projection overlay is `Docs/ArtTest/props/r2_gobo_projection.png`.
- **R2-A2 (D1.26)**: `DialLever_Quadrant` is a sector plate (R 48, -42..+42 deg, pivot = sector centre, placed at (6, 4, 45); slots Iron + Paint pegs), `DialLever_Weight` a squat O11 ball with a collar and no chain,
  `DialLever_Backplate` gained a pulley bracket and an 8-link chain into a wall eyelet (Z to 77.5); `DialLever_NotchStop` is built but unused. Gobo `GOBO_OFFSET` is now 0.7 (open area 907 cm2). Placement and bounds: `Docs/ArtTest/crypt/survey_diallever.md`.
  `render_r2.py --set cycles|lever` assembles the lever with the quadrant at (6, 4, 45) and a review wall at x -3.05.
