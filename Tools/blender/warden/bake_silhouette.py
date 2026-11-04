"""bake_silhouette.py -- P12-5: the Warden's black silhouette mesh, baked from the owner's V5 master.

    blender.exe -b --factory-startup --python Tools/blender/warden/bake_silhouette.py -- [options]

Opens SourceArt/Warden/V5/Warden_Rigged.blend (a copy of the owner's master; NEVER saved by this script: it has no save
call, and everything it creates lives in memory), poses the armature `Warden_Rig` with the action `Warden_Idle` at frame 1,
takes the evaluated (armature-deformed) LOD2 mesh `SK_Warden_LOD2` (the same thing as applying the Armature modifier),
welds it, collapses it to ONE material slot, decimates it to <= 8000 triangles, scales it to centimetres exactly as the
owner's own export does (scripts/export_unreal_cm.py: vertex coordinates x100, scene unit scale 0.01, FBX export with
global_scale 1, apply_unit_scale, FBX_SCALE_UNITS, axis_forward -Y, axis_up Z, bake_space_transform False, mesh_smooth_type
FACE), keeps the origin at the skeleton root (0, 0, 0) = the ground point between the feet, and writes
SourceArt/Warden/SM_LB_Warden_Silhouette.fbx plus <out>.json (a report: triangles, bounds in Blender metres and in cm).

Orientation (measured, P12-5): with these axes and the project's default static-mesh FBX import (bConvertScene true,
bForceFrontXAxis false) the import maps Blender (x, y, z) to Unreal (x, -y, z), so the figure, which faces Blender -Y, faces
mesh +Y in Unreal. That is the same mapping the owner's ANIMATIONS evaluate to (see the P12-5 report), so --rotz 0 (default)
gives a silhouette that agrees with the playing Warden: both need actor/component yaw -90 to face world +X. (SK_Warden's
bind pose, imported by the owner with force_front_x_axis, faces +X instead.)

Options:
    --out PATH          FBX path (default SourceArt/Warden/SM_LB_Warden_Silhouette.fbx)
    --rotz DEG           rotate the baked mesh about Z (degrees, Blender frame) BEFORE export. 0 keeps the master's
                         orientation: the figure faces Blender -Y. Used to choose which way the imported static mesh faces.
    --axis-forward A     default -Y (the owner's value)
    --target-tris N      decimate to at most N triangles (default 7600; the hard limit is 8000)
    --weld M             weld distance in metres (default 0.003)

The owner's folder is not touched.  Read-only on the master.
"""
import json
import math
import os
import sys

import bpy
import bmesh
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
MASTER = os.path.join(ROOT, "SourceArt", "Warden", "V5", "Warden_Rigged.blend")


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = {"out": os.path.join(ROOT, "SourceArt", "Warden", "SM_LB_Warden_Silhouette.fbx"), "rotz": 0.0, "axis_forward": "-Y",
         "target": 7600, "weld": 0.003}
    i = 0
    while i < len(argv):
        k = argv[i]
        if k == "--out":
            a["out"] = argv[i + 1]; i += 1
        elif k == "--rotz":
            a["rotz"] = float(argv[i + 1]); i += 1
        elif k == "--axis-forward":
            a["axis_forward"] = argv[i + 1]; i += 1
        elif k == "--target-tris":
            a["target"] = int(argv[i + 1]); i += 1
        elif k == "--weld":
            a["weld"] = float(argv[i + 1]); i += 1
        i += 1
    return a


def tri_count(obj):
    me = obj.data
    me.calc_loop_triangles()
    return len(me.loop_triangles)


def bbox(obj):
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def main():
    a = parse_args()
    assert os.path.isfile(MASTER), MASTER
    bpy.ops.wm.open_mainfile(filepath=MASTER)           # read only: this script never saves
    scene = bpy.context.scene
    arm = bpy.data.objects["Warden_Rig"]
    src = bpy.data.objects["SK_Warden_LOD2"]
    action = bpy.data.actions["Warden_Idle"]

    # pose: Warden_Idle, frame 1
    arm.animation_data_create()
    arm.animation_data.action = action
    scene.frame_set(1)
    bpy.context.view_layer.update()
    src.hide_set(False)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = src.evaluated_get(dg)
    mesh = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=False, depsgraph=dg)   # armature applied
    mods = [m.type for m in src.modifiers]

    obj = bpy.data.objects.new("SM_LB_Warden_Silhouette", mesh)
    scene.collection.objects.link(obj)
    obj.matrix_world = Matrix.Identity(4)
    mesh.transform(src.matrix_world)                     # identity in this file; kept for safety

    # one material slot, no UVs, no custom normals (an unlit black shape needs none of them)
    mesh.materials.clear()
    for uv in list(mesh.uv_layers):
        mesh.uv_layers.remove(uv)
    if mesh.has_custom_normals:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    for attr in list(mesh.color_attributes):
        mesh.color_attributes.remove(attr)
    mat = bpy.data.materials.new("MAT_Silhouette")
    mesh.materials.append(mat)
    for p in mesh.polygons:
        p.material_index = 0
        p.use_smooth = True

    # weld, triangulate
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=a["weld"])
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    tris_welded = tri_count(obj)

    # decimate (collapse) to the target, re-check, tighten if needed
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    target = a["target"]
    for _ in range(6):
        cur = tri_count(obj)
        if cur <= target:
            break
        mod = obj.modifiers.new("Silhouette reduction", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = max(0.02, min(1.0, target / float(cur)))
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    tris = tri_count(obj)
    assert tris <= 8000, tris

    # optional orientation turn about Z (Blender frame), then to centimetres like export_unreal_cm.py
    if abs(a["rotz"]) > 1e-9:
        mesh.transform(Matrix.Rotation(math.radians(a["rotz"]), 4, "Z"))
    b_min, b_max = bbox(obj)                              # metres
    for v in mesh.vertices:
        v.co *= 100.0
    mesh.update()
    c_min, c_max = bbox(obj)                              # centimetres
    scene.unit_settings.scale_length = 0.01
    bpy.context.view_layer.update()

    settings = dict(use_selection=True, global_scale=1, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                    axis_forward=a["axis_forward"], axis_up="Z", bake_space_transform=False, use_mesh_modifiers=True,
                    mesh_smooth_type="FACE", use_tspace=False, add_leaf_bones=False, use_armature_deform_only=True,
                    armature_nodetype="NULL", path_mode="RELATIVE", embed_textures=False)
    out = a["out"]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=out, object_types={"MESH"}, bake_anim=False, **settings)
    rep = {"source": MASTER, "pose": "Warden_Idle frame 1", "lod": "SK_Warden_LOD2", "source_modifiers": mods,
           "triangles_after_weld": tris_welded, "triangles": tris, "vertices": len(mesh.vertices),
           "bounds_m_min": b_min, "bounds_m_max": b_max, "bounds_cm_min": c_min, "bounds_cm_max": c_max,
           "height_cm": c_max[2] - c_min[2], "rotz_deg": a["rotz"], "axis_forward": a["axis_forward"],
           "fbx": out, "fbx_bytes": os.path.getsize(out), "saved_master": False}
    with open(out + ".json", "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1)
    print("BAKE_SILHOUETTE " + json.dumps(rep))


main()
