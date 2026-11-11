"""w0_survey_fbx.py -- P17 W0: read-only survey of Warden FBX files (mesh LODs: slots, counts, bounds; clips: frame range and sampled bone positions).

    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --factory-startup --python Tools/blender/warden/w0_survey_fbx.py -- --out <json> --files <label>=<path> [<label>=<path> ...]

Each file is imported with the Blender defaults into an empty scene (so two files are comparable with each other, not an absolute truth about Unreal's frame).
Meshes: material slots in order, verts, triangles, per-slot triangles, bounds. Clips: action frame range, fcurve count, armature-space bone head positions (cm)
at 5 frames. Never writes anything but the JSON.
"""
import json
import sys

import bpy
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = a[a.index("--out") + 1]
files = [x.split("=", 1) for x in a[a.index("--files") + 1:]]
res = {}


def r(x, n=4):
    return round(float(x), n)


for label, path in files:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    sc = bpy.context.scene
    d = {"path": path, "objects": [(o.name, o.type) for o in bpy.data.objects]}
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if arms:
        arm = arms[0]
        d["armature"] = {"name": arm.name, "bones": len(arm.data.bones), "scale": [r(x, 6) for x in arm.scale], "rotation_euler_deg": [r(x * 57.29578, 3) for x in arm.rotation_euler],
                         "bone_names_first5": [b.name for b in arm.data.bones][:5]}
    dg = bpy.context.evaluated_depsgraph_get()
    if meshes:
        d["meshes"] = []
        for o in meshes:
            oe = o.evaluated_get(dg)
            me = oe.to_mesh()
            me.calc_loop_triangles()
            pos = [oe.matrix_world @ v.co for v in me.vertices]
            lo = [min(p[i] for p in pos) for i in range(3)]
            hi = [max(p[i] for p in pos) for i in range(3)]
            k = 100.0 if (hi[2] - lo[2]) < 10 else 1.0       # metres -> cm when the importer applied the 0.01 unit scale
            tps = {}
            for t in me.loop_triangles:
                tps[t.material_index] = tps.get(t.material_index, 0) + 1
            d["meshes"].append({
                "name": o.name, "verts": len(o.data.vertices), "tris": len(me.loop_triangles), "unit_factor_to_cm": k,
                "slots": [{"index": i, "slot": s.name, "material": s.material.name if s.material else None, "tris": tps.get(i, 0)} for i, s in enumerate(o.material_slots)],
                "bounds_min_cm": [r(x * k) for x in lo], "bounds_max_cm": [r(x * k) for x in hi],
                "bounds_centre_xy_cm": [r((lo[0] + hi[0]) / 2 * k), r((lo[1] + hi[1]) / 2 * k)], "height_cm": r((hi[2] - lo[2]) * k),
                "vertex_groups": len(o.vertex_groups)})
            oe.to_mesh_clear()
    acts = list(bpy.data.actions)
    if acts and arms:
        act = acts[0]
        arm.animation_data_create()
        arm.animation_data.action = act
        if hasattr(arm.animation_data, "action_slot") and len(act.slots):
            arm.animation_data.action_slot = act.slots[0]       # Blender 5: slotted actions
        f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
        d["rest_heads_local_units"] = {b.name: [r(x, 3) for x in b.head_local] for b in arm.data.bones}
        d["action"] = {"name": act.name, "frame_range": [f0, f1], "frames": f1 - f0 + 1, "scene_fps": sc.render.fps,
                       "fcurves": sum(len(cb.fcurves) for l in act.layers for s in l.strips for cb in s.channelbags) if hasattr(act, "layers") else len(act.fcurves)}
        samples = {}
        for fr in sorted({f0, f0 + (f1 - f0) // 4, f0 + (f1 - f0) // 2, f0 + 3 * (f1 - f0) // 4, f1}):
            sc.frame_set(fr)
            bpy.context.view_layer.update()
            k = 100.0                                                            # world matrix carries the 0.01 unit scale: metres -> cm
            ae = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())       # the evaluated copy carries the animated pose
            samples[str(fr)] = {pb.name: [r((ae.matrix_world @ pb.head)[i] * k, 3) for i in range(3)] for pb in ae.pose.bones}
        d["samples_cm"] = samples
    res[label] = d
    print("W0FBX|", label, "ok")

with open(out, "w") as f:
    json.dump(res, f, indent=1)
print("W0FBX| wrote", out)
