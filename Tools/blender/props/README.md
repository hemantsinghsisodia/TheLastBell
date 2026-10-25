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
