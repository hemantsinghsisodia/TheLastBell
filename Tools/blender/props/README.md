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
