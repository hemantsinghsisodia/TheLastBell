# P15 FX meshes (cloth + cards) -- Blender build scripts

Plan: `Docs/plans/P15_PARTICLES.md` section 7. Headless Blender 5.2, same conventions as the kit/props (1 BU = 1 cm, authoring space = Unreal
space, Y mirrored at export through `kit_lib.export_piece_fbx`).

```
set B="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
%B% -b --factory-startup --python Tools/blender/fx/build_fx_meshes.py        # 6 FBX + fx_meshes_report.json -> SourceArt/FX/
%B% -b --factory-startup --python Tools/blender/fx/verify_fx_meshes.py       # re-imports every FBX, exit code 1 on failure
%B% -b --factory-startup --python Tools/blender/fx/render_fx_meshes.py       # Docs/ArtTest/fx/p15_cloth_*.png (front + 3/4, checker on one view)
```

- UV0 as Unreal reads it: V = 0 at the pinned top edge, increasing downward. Unreal flips V on FBX import, so the file stores `v = 1 - V`.
- Pivot: cloth and BoltCard = top centre (hang / extend -Z); CurtainCard = bottom centre. Cloth front (normal) = +Y = into the room.
- Torn edges are seeded geometry (fixed seed per mesh), no opacity. Strip B has one hole, Banner A one side tear.
