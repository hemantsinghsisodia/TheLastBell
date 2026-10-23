# THE LAST BELL modular kit (P0) -- Blender build scripts

Procedural, deterministic, headless. Spec: `Docs/MODULAR_KIT.md` (section 4.1 + section 8 decisions); decision D-044.
Requires Blender 5.2.x (`C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`). No GUI and no Blender MCP needed.

## Commands (run from the repo root)

```
set B="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"

# 1. build everything: 26 FBX + LB_Kit_P0.blend + kit_report.json  (about 20 s)
%B% -b --factory-startup --python Tools/blender/kit/build_kit.py -- --out SourceArt/Kit
#    optional: --only Gate Doorway      (substring filter; writes LB_Kit_partial.blend instead)

# 2. verify: re-imports every FBX in a clean Blender and checks it against the spec table (exit code 1 on failure)
%B% -b --factory-startup --python Tools/blender/kit/verify_kit.py

# 3. review renders (Workbench, grey studio light + UV checker view) -> Docs/ArtTest/kit/*.png
%B% -b --factory-startup --python Tools/blender/kit/render_kit.py
```

## Files
- `kit_lib.py` -- bmesh helpers: solids (chamfered boxes, prisms, hulls, height fields), exact-boolean wrapper, ashlar relief cutters
  (V-grooves, weathered recesses, chips), pointed-arch / voussoir / jamb / quoin generators, UV0, vertex colour, smoothing, FBX export.
- `build_kit.py` -- the piece table (mirrors the spec) and one builder per piece family; seeds are fixed, so output is reproducible.
- `verify_kit.py`, `render_kit.py` -- checks and review renders.

## Conventions (what Unreal import must assume)
- **Units:** authoring 1 Blender unit = 1 cm (scene unit scale 0.01). FBX: vertices in cm, `UnitScaleFactor = 1`, apply_unit_scale on,
  `FBX_SCALE_NONE`, no node scale. Unreal imports at real size (400 cm = 400 uu).
- **Axes:** pieces are authored in the spec's Unreal frame: +X length, +Y thickness, +Z up, **pivot = bottom-left-back corner** (bbox min = 0,0,0).
  Export uses `axis_forward='Y', axis_up='Z'` (this declares exactly Unreal's import axis system: Z up, front -Y, right-handed;
  identity node rotation). Unreal's importer negates Y when it converts to its left-handed world, so every exported mesh is
  **mirrored in Y (y -> -y) with the face winding reversed** at export time. Net result in Unreal: Y in [0, thickness], faces outward.
  The re-imported FBX in Blender therefore has Y in [-thickness, 0]; `verify_kit.py` accounts for this (`UE_Y = -Blender_Y`).
  The review `.blend` holds the un-mirrored authoring versions.
- **Material slots (always three, in this order):** 0 `MAT_Masonry` (world-aligned in Unreal; UV0 is a 1 UV = 100 cm box projection),
  1 `MAT_Trim` (dressed stone; UV0 box projection, six projection directions in disjoint UV regions, no mirroring),
  2 `MAT_Rubble` (fractures, chips, rough soffit, rubble). Some pieces do not use every slot (slots stay in the FBX regardless).
- **Vertex colour:** attribute `Color`, all white (R wet / G grime / B wear contract, D-044 section 8).
- **Normals:** smooth by angle 30 degrees (8 degrees for cliffs, so they stay faceted); exported as custom normals
  (`mesh_smooth_type='OFF'`). Unreal import: *Normal Import Method = Import Normals*.
- **Collision:** `UCX_<MeshName>_NN` convex hulls in the same FBX (boxes; stepped boxes for broken pieces; opening pieces leave the clear
  opening free; rubble chunks use their convex hull).
- **Masonry relief:** 3 cm V-grooves (about 1.5 cm deep) between 25-75 cm courses and staggered blocks, shallow weathered recesses and chips
  on slot 0 faces. These are modelled; if they fight the scanned material's own joints in Unreal, re-run with fewer or no joints
  (`relief_cutters(vertical=..., h_grooves=..., recess_prob=...)` in `kit_lib.py`).
