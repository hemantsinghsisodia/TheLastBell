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

## P7-FIX3 G2a additions (7 pieces: arcade bays + garden kerbs)
```
# build ONLY the new pieces (the 28 existing FBX stay byte-identical; kit_report.json gets the new records merged in; LB_Kit_P0.blend is untouched)
%B% -b --factory-startup --python Tools/blender/kit/build_kit.py -- --out SourceArt/Kit --only ArcadeBay Kerb --blend LB_Kit_Fix3.blend
%B% -b --factory-startup --python Tools/blender/kit/verify_kit.py            # 35/35 (28 + 7)
%B% -b --factory-startup --python Tools/blender/props/render_fix3.py -- --blend SourceArt/Kit/LB_Kit_Fix3.blend --set kit   # Docs/ArtTest/props/fix3_arcade_*.png, fix3_kerbs.png
```
- `SM_LB_Kit_ArcadeBay_1000x60x400`: four-centred pointed arch (lower arcs R150, junction 57 deg, upper arcs R~1700, opening X 50..950, springing Z 0, apex Z 300; the
  geometry is a depressed Tudor-type arch because 900 span / 300 rise cannot be more pointed), voussoir ring 60 radial (slot 1, 1.5 cm chamfer, every other stone bites 5 cm
  into the band, ring clipped at the slab ends), masonry band Z 0..370 recessed 2 cm behind ring + coping (slot 0 with relief), coping Z 370..400 (slot 1).
  UCX: 3 boxes (X 0..50, X 950..1000, Z 300..400 across); the opening below the ring is clear in collision.
- `_BrokenA` keeps X 0..350, `_BrokenB` is its mirror (X 650..1000). **Both stay in the 1000 cm bay frame (pivot = left pier centre)**, so place them at the left pier X exactly like the intact bay
  (BrokenB's mesh bounds start at X 650). 2 UCX each (end band + a box over the ring stub that stays above the intrados). Fracture = seeded, stepped per course, collapsed top, fracture faces in slot 2.
- `Kerb_200x30x40`, `Kerb_100x30x40`, `Kerb_Broken_200x30x40` (broken top, missing chunk, 1 UCX only 11 cm high so the gap can be stepped over) and `KerbCorner_30x30x45`: slot 1 (+ chips in slot 2), 1 UCX each.
- `verify_kit.py`: CLEAR entries for the three arcade pieces (collision rectangle must be free) + `ARCH_RAYS` (visual ray test only through the real arch intrados, because a Tudor arch cannot contain the full X 50..950 x Z 0..250 rectangle); `ORIGIN` in build_kit.py declares the BrokenB mesh origin (650, 0, 0).

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
