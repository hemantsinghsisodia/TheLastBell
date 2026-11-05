"""bake_silhouette.py -- P12-5 (V5), re-baked for V5.5 (D-091): the Warden's black silhouette mesh, from the owner's master.

    blender.exe -b --factory-startup --python Tools/blender/warden/bake_silhouette.py -- [options]

Opens SourceArt/Warden/V5_5/Warden_Rigged.blend (a copy of the owner's V5.5 master, md5 4445c23d...; NEVER saved by this script: it has no save
call, and everything it creates lives in memory), poses the armature `Warden_Rig` with the action `Warden_Idle` at frame 1,
takes the evaluated (armature-deformed) LOD2 mesh `SK_Warden_LOD2` (the same thing as applying the Armature modifier),
welds it, collapses its six materials to TWO slots (P12 fix set 1, F2): MAT_Body (everything) and MAT_Mask (the faces of the bell metal
material M_Warden_BellMetal that form the head mask; measured: that material is ONE connected island of 337 triangles on the
head, nothing else, so the whole material is the mask; any other bell metal island away from the head would stay in MAT_Body),
decimates it to <= 8000 triangles with the mask protected (see --mask-mode), scales it to centimetres exactly as the
owner's own export does (scripts/export_unreal_cm.py: vertex coordinates x100, scene unit scale 0.01, FBX export with
global_scale 1, apply_unit_scale, FBX_SCALE_UNITS, axis_forward -Y, axis_up Z, bake_space_transform False, mesh_smooth_type
FACE), keeps the origin at the skeleton root (0, 0, 0) = the ground point between the feet, and writes
SourceArt/Warden/SM_LB_Warden_Apparition.fbx plus <out>.json (a report: triangles, bounds in Blender metres and in cm).

Orientation (measured): the master's figure faces Blender -Y. With these axes and the project's default static-mesh FBX import
(bConvertScene true, bForceFrontXAxis false) the import maps Blender (x, y, z) to Unreal (x, -y, z). So with --rotz 0 the figure
faces mesh +Y in Unreal and needs yaw D - 90 to face world direction D, while SK_Warden (V5.5, faces mesh +X) needs D.
**--rotz 90 is the documented way for this mesh** (P12 fix set 1, F2): it turns the baked figure from Blender -Y to Blender +X,
which the import maps to mesh +X, so the static silhouette faces +X like SK_Warden and yaw means the same on both.

Options:
    --out PATH          FBX path (default SourceArt/Warden/SM_LB_Warden_Apparition.fbx)
    --rotz DEG           rotate the baked mesh about Z (degrees, Blender frame) BEFORE export. 0 keeps the master's
                         orientation: the figure faces Blender -Y. Use 90 for this mesh (faces mesh +X in Unreal).
    --mask-mode M        protect (default): the mask's faces are not decimated at all (the body is decimated with its
                         boundary vertices held); plain: decimate everything together (the mask can be eaten)
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
BELL_METAL = "M_Warden_BellMetal"
MASTER = os.path.join(ROOT, "SourceArt", "Warden", "V5_5", "Warden_Rigged.blend")


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = {"mask_mode": "protect", "out": os.path.join(ROOT, "SourceArt", "Warden", "SM_LB_Warden_Apparition.fbx"), "rotz": 0.0, "axis_forward": "-Y",
         "target": 7600, "weld": 0.003}
    i = 0
    while i < len(argv):
        k = argv[i]
        if k == "--out":
            a["out"] = argv[i + 1]; i += 1
        elif k == "--rotz":
            a["rotz"] = float(argv[i + 1]); i += 1
        elif k == "--mask-mode":
            a["mask_mode"] = argv[i + 1]; i += 1
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


def slot_tris(obj):
    me = obj.data
    me.calc_loop_triangles()
    out = [0] * max(1, len(me.materials))
    for t in me.loop_triangles:
        out[me.polygons[t.polygon_index].material_index] += 1
    return out


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

    # find the mask: the faces of M_Warden_BellMetal, split into connected islands; an island is the mask if it is on the head
    # (its centre is in the top quarter of the figure); other islands (buckles, small bells) would stay in MAT_Body.
    src_names = [m.name if m else None for m in mesh.materials]
    assert BELL_METAL in src_names, src_names
    bell_idx = src_names.index(BELL_METAL)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    zs = [v.co.z for v in bm.verts]
    z_lo, z_hi = min(zs), max(zs)
    head_z = z_lo + 0.75 * (z_hi - z_lo)
    bell_faces = [f for f in bm.faces if f.material_index == bell_idx]
    seen, islands = set(), []
    for f in bell_faces:
        if f in seen:
            continue
        stack, comp = [f], []
        seen.add(f)
        while stack:
            x = stack.pop(); comp.append(x)
            for e in x.edges:
                for g in e.link_faces:
                    if g.material_index == bell_idx and g not in seen:
                        seen.add(g); stack.append(g)
        islands.append(comp)
    mask_face_idx = set()
    isl_report = []
    for comp in islands:
        zc = sum(v.co.z for f in comp for v in f.verts) / (3.0 * len(comp))
        on_head = zc >= head_z
        isl_report.append({"faces": len(comp), "centre_z_m": zc, "mask": on_head})
        if on_head:
            mask_face_idx.update(f.index for f in comp)
    bm.free()
    assert mask_face_idx, "no bell metal island on the head"

    # two material slots (MAT_Body 0, MAT_Mask 1), no UVs, no custom normals (flat shaded colours need none of them)
    flags = [p.index in mask_face_idx for p in mesh.polygons]
    mesh.materials.clear()
    for uv in list(mesh.uv_layers):
        mesh.uv_layers.remove(uv)
    if mesh.has_custom_normals:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    for attr in list(mesh.color_attributes):
        mesh.color_attributes.remove(attr)
    mesh.materials.append(bpy.data.materials.new("MAT_Body"))
    mesh.materials.append(bpy.data.materials.new("MAT_Mask"))
    for p, is_mask in zip(mesh.polygons, flags):
        p.material_index = 1 if is_mask else 0
        p.use_smooth = True

    # weld, triangulate
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=a["weld"])
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    tris_welded = tri_count(obj)
    slots_welded = slot_tris(obj)

    # decimate (collapse) to the target, re-check, tighten if needed
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    target = a["target"]
    vg = None
    if a["mask_mode"] == "protect":
        # vertex group = every vertex of a mask face (so its rim too); weight 1 protects it (inverted below)
        vg = obj.vertex_groups.new(name="mask_keep")
        keep = sorted({v for p in mesh.polygons if p.material_index == 1 for v in p.vertices})
        vg.add(keep, 1.0, "REPLACE")
    for _ in range(8):
        cur = tri_count(obj)
        if cur <= target:
            break
        mask_now = slot_tris(obj)[1] if a["mask_mode"] == "protect" else 0
        mod = obj.modifiers.new("Silhouette reduction", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = max(0.02, min(1.0, (target - mask_now) / float(max(1, cur - mask_now)) if mask_now else target / float(cur)))
        mod.use_collapse_triangulate = True
        if vg:
            mod.vertex_group = "mask_keep"
            mod.invert_vertex_group = True       # measured: Collapse spends the group's weight as 'decimate here', so invert it to protect
            mod.vertex_group_factor = 1.0
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if vg:
        obj.vertex_groups.remove(obj.vertex_groups["mask_keep"])      # (the Python reference is stale after a modifier apply)
    tris = tri_count(obj)
    slots_final = slot_tris(obj)
    assert tris <= 8000, tris
    assert len(slots_final) == 2 and slots_final[1] > 0, slots_final

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
           "triangles_after_weld": tris_welded, "triangles": tris, "slots": ["MAT_Body", "MAT_Mask"], "triangles_per_slot_after_weld": slots_welded,
           "triangles_per_slot": slots_final, "mask_mode": a["mask_mode"], "bell_metal_islands": isl_report, "vertices": len(mesh.vertices),
           "bounds_m_min": b_min, "bounds_m_max": b_max, "bounds_cm_min": c_min, "bounds_cm_max": c_max,
           "height_cm": c_max[2] - c_min[2], "rotz_deg": a["rotz"], "axis_forward": a["axis_forward"],
           "fbx": out, "fbx_bytes": os.path.getsize(out), "saved_master": False}
    with open(out + ".json", "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1)
    print("BAKE_SILHOUETTE " + json.dumps(rep))


main()
