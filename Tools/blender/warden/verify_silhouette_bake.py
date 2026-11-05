"""verify_silhouette_bake.py -- P12 fix set 1 (F2): read-only check of the baked Warden silhouette FBX.

    blender.exe -b --factory-startup --python Tools/blender/warden/verify_silhouette_bake.py -- [--fbx PATH] [--png PATH]

Imports the FBX into an EMPTY scene (never opens or saves the master), prints the material slot names, triangles per slot, bounds
and the direction the figure faces (from where the mask sits relative to the body), and renders one contact sheet:
front (camera on +X, the way the figure should face), side, three-quarter and a head close-up. MAT_Body is dark grey, MAT_Mask pale.
The imported Blender coordinates are the baked ones; the static import in Unreal maps Blender (x, y, z) to Unreal (x, -y, z), so a
figure facing Blender +X faces Unreal +X.
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = {"fbx": os.path.join(ROOT, "SourceArt", "Warden", "SM_LB_Warden_Apparition.fbx"),
         "png": os.path.join(ROOT, "Docs", "ArtTest", "warden", "p12f_silhouette_bake.png")}
    for i, k in enumerate(argv):
        if k == "--fbx":
            a["fbx"] = argv[i + 1]
        elif k == "--png":
            a["png"] = argv[i + 1]
    return a


def main():
    a = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=a["fbx"])
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    assert len(objs) == 1, objs
    o = objs[0]
    me = o.data
    me.calc_loop_triangles()
    names = [m.name if m else None for m in me.materials]
    per = [0] * len(names)
    for t in me.loop_triangles:
        per[me.polygons[t.polygon_index].material_index] += 1
    pts = [o.matrix_world @ v.co for v in me.vertices]
    mn = Vector([min(p[i] for p in pts) for i in range(3)])
    mx = Vector([max(p[i] for p in pts) for i in range(3)])
    # the importer may or may not apply the cm unit: bring the size to cm by the height (the figure is ~2.85 m tall)
    k = 100.0 if (mx.z - mn.z) < 50.0 else 1.0
    # facing: direction from the body's centroid (xy) to the mask's centroid (xy), in imported Blender coordinates
    def centroid(slot):
        c, n = Vector((0, 0, 0)), 0
        for p in me.polygons:
            if p.material_index == slot:
                for vi in p.vertices:
                    c += pts[vi]; n += 1
        return c / max(1, n)
    cb, cm = centroid(names.index("MAT_Body")) if "MAT_Body" in names else None, centroid(names.index("MAT_Mask")) if "MAT_Mask" in names else None
    d = Vector((cm.x - cb.x, cm.y - cb.y))
    face_blender = d.normalized()
    rep = {"slots": names, "triangles_per_slot": per, "triangles": sum(per), "bounds_cm_min": [x * k for x in mn],
           "bounds_cm_max": [x * k for x in mx], "size_cm": [(mx[i] - mn[i]) * k for i in range(3)],
           "mask_centroid_cm": [x * k for x in cm], "body_centroid_cm": [x * k for x in cb],
           "facing_blender_xy": [face_blender.x, face_blender.y],
           "facing_unreal_xy_(x,-y)": [face_blender.x, -face_blender.y]}
    print("VERIFY_SILHOUETTE " + json.dumps(rep))

    # materials: body dark grey, mask pale (flat colours, workbench)
    for m in me.materials:
        col = (0.07, 0.07, 0.075, 1) if m.name.startswith("MAT_Body") else (0.88, 0.80, 0.62, 1)
        m.diffuse_color = col
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_cavity = False
    sc.world = bpy.data.worlds.new("w")
    sc.world.color = (0.42, 0.42, 0.44)
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"
    sc.render.image_settings.file_format = "PNG"
    sc.render.resolution_x, sc.render.resolution_y = 560, 760
    sc.render.resolution_percentage = 100
    cam_d = bpy.data.cameras.new("c")
    cam_d.type = "ORTHO"
    cam = bpy.data.objects.new("c", cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cen = (mn + mx) / 2.0
    views = [("front (camera on +X)", Vector((1, 0, 0.05)), cen, 1.0, k),
             ("side (camera on -Y)", Vector((0, -1, 0.05)), cen, 1.0, k),
             ("three-quarter", Vector((1, -1, 0.25)), cen, 1.0, k),
             ("head close-up", Vector((1, -0.35, 0.1)), Vector((cm.x, cm.y, cm.z)), 0.2, k)]
    tiles = []
    full = max(mx.z - mn.z, 1e-6) * 1.12
    for i, (label, direction, target, zoom, _k) in enumerate(views):
        direction = direction.normalized()
        cam.location = target + direction * 20.0
        cam.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
        cam_d.ortho_scale = full * zoom       # the larger render dimension (the height) fits the figure
        sc.render.filepath = os.path.join(os.path.dirname(a["png"]), "_tile%d.png" % i)
        os.makedirs(os.path.dirname(a["png"]), exist_ok=True)
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(sc.render.filepath)
        w, h = img.size
        arr = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
        tiles.append(arr)
        bpy.data.images.remove(img)
        os.remove(sc.render.filepath)
    sheet = np.concatenate(tiles, axis=1)
    out = bpy.data.images.new("sheet", sheet.shape[1], sheet.shape[0], alpha=True)
    out.pixels = sheet.reshape(-1).tolist()
    out.filepath_raw = a["png"]
    out.file_format = "PNG"
    out.save()
    print("VERIFY_SHEET " + a["png"])


main()
