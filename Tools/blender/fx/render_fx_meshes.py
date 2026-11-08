"""render_fx_meshes.py -- headless Workbench review renders of the P15 cloth meshes and FX cards.

    blender.exe -b --factory-startup --python Tools/blender/fx/render_fx_meshes.py -- [--out Docs/ArtTest/fx] [--only name ...]

One PNG per cloth mesh (p15_cloth_<Name>.png) and one for the two cards (p15_cloth_Cards.png); each image = front view (left)
and three-quarter view (right).  The linen-coloured material is plain on one view and carries the Blender COLOR_GRID
checker on the other (mapped at 40 cm per cell so the cells stay square); the labelled grid shows the UV orientation.
Geometry comes straight from build_fx_meshes.build_all() (authoring space, Y not mirrored): the cloth front faces +Y.
"""
import importlib.util
import math
import os
import sys

import bpy
import numpy as np
import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "kit")))
import render_kit as RK  # noqa: E402
import kit_lib as K  # noqa: E402

spec = importlib.util.spec_from_file_location("build_fx_meshes", os.path.join(HERE, "build_fx_meshes.py"))
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)

VW, VH = 1000, 1200


def args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.join(ROOT, "Docs", "ArtTest", "fx")
    only = []
    i = 0
    while i < len(argv):
        if argv[i] == "--out":
            out = os.path.abspath(argv[i + 1]); i += 2
        elif argv[i] == "--only":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                only.append(argv[i]); i += 1
        else:
            i += 1
    return out, only


def linen():
    m = bpy.data.materials.new("linen")
    m.diffuse_color = (0.66, 0.58, 0.44, 1.0)
    m.roughness = 0.95
    return m


def checker(scale):
    m = bpy.data.materials.new("checker")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    img = bpy.data.images.get("cgrid")
    if img is None:
        img = bpy.data.images.new("cgrid", 1024, 1024)
        img.generated_type = 'COLOR_GRID'
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale[0], scale[1], 1.0)
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = img
    tx.extension = 'REPEAT'
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], tx.inputs["Vector"])
    nt.links.new(tx.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    nt.nodes.active = tx
    return m


def to_object(bm, name, mat, loc=(0.0, 0.0, 0.0)):
    # preview the FBX as exported (Y mirrored, winding reversed): Unreal is left-handed, so a Blender view of the mirrored file
    # from -Y shows what Unreal shows from +Y (front face toward the viewer, U running left to right)
    for v in bm.verts:
        v.co.y = -v.co.y
    import bmesh as _bmesh
    _bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    return ob


def render_view(sc, cam, objs, az, el, path, dist=1.18, target_shift=Vector((0, 0, 0))):
    bpy.context.view_layer.update()
    mn, mx = RK.world_bbox(objs)
    RK.frame(cam, sc, mn, mx, az, el, dist)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def compose(left, right, out):
    ims = []
    for p in (left, right):
        im = bpy.data.images.load(p)
        w, h = im.size
        a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
        ims.append(a)
        bpy.data.images.remove(im)
    sep = np.full((ims[0].shape[0], 6, 4), 0.05, dtype=np.float32)
    a = np.concatenate([ims[0], sep, ims[1]], axis=1)
    h, w = a.shape[:2]
    res = bpy.data.images.new("composite", w, h, alpha=False)
    res.pixels = a.ravel().tolist()
    res.filepath_raw = out
    res.file_format = 'PNG'
    res.save()
    bpy.data.images.remove(res)


def main():
    out, only = args()
    os.makedirs(out, exist_ok=True)
    for o in list(bpy.data.objects):                    # the factory startup scene has a default cube, light and camera
        bpy.data.objects.remove(o)
    K.setup_scene_units()
    sc = bpy.context.scene
    RK.setup_render(sc, VW, VH)
    sc.display.shading.show_cavity = False
    sc.display.shading.show_shadows = False
    sc.display.shading.light = 'STUDIO'
    sc.world = sc.world or bpy.data.worlds.new("W")
    sc.world.color = (0.30, 0.31, 0.33)
    sc.display.light_direction = Vector((0.5, 0.6, 0.65)).normalized()
    cam = RK.make_camera(sc)
    meshes = B.build_all()
    tmp = os.path.join(out, "_tmp_view")
    lin = linen()
    red = bpy.data.materials.new("pivot_red")
    red.diffuse_color = (0.9, 0.05, 0.05, 1.0)

    jobs = [(nm, [nm]) for nm in B.CLOTH] + [("Cards", list(B.CARDS))]
    for label, names in jobs:
        short = label.replace("Prop_Cloth", "").replace("_", "")
        if only and not any(o in short or o in label for o in only):
            continue
        objs = []
        markers = []
        sc.render.resolution_x, sc.render.resolution_y = (1100, 900) if label == "Cards" else (VW, VH)
        for k, nm in enumerate(names):
            bm, _, _ = meshes[nm]
            if label == "Cards":
                loc = (-75.0, 0.0, 100.0) if nm == "FX_BoltCard" else (75.0, 0.0, 0.0)
                chk = checker((1.0 / 0.40, 1.0 / 0.40))
                mat_front = chk
                mat_34 = lin
            else:
                sp = B.CLOTH[nm]
                loc = (0.0, 0.0, 0.0)
                chk = checker((sp['w'] / 40.0, sp['h'] / 40.0))
                mat_front = lin
                mat_34 = chk
            ob = to_object(bm.copy(), nm, mat_front, loc)
            ob["mat_front"] = mat_front.name
            ob["mat_34"] = mat_34.name
            objs.append(ob)
            mk_me = bpy.data.meshes.new("pivot_marker")
            mk = bmesh.new()
            bmesh.ops.create_cube(mk, size=3.0)
            mk.to_mesh(mk_me)
            mk.free()
            mk_me.materials.append(red)
            mko = bpy.data.objects.new("pivot_marker", mk_me)
            sc.collection.objects.link(mko)
            mko.location = loc                                  # the pivot (mesh origin) of the piece
            markers.append(mko)
        sh = sc.display.shading
        # front: camera on -Y of the mirrored file == Unreal's +Y side, where the cloth front (normal +Y) faces
        for ob in objs:
            ob.data.materials[0] = bpy.data.materials[ob["mat_front"]]
        sh.color_type = 'TEXTURE' if label == "Cards" else 'MATERIAL'
        render_view(sc, cam, objs, 0.0, 4.0, tmp + "_a.png", 1.3)
        # three-quarter
        for ob in objs:
            ob.data.materials[0] = bpy.data.materials[ob["mat_34"]]
        sh.color_type = 'MATERIAL' if label == "Cards" else 'TEXTURE'
        render_view(sc, cam, objs, 38.0, 10.0, tmp + "_b.png", 1.3)
        name = "p15_cloth_%s.png" % short
        compose(tmp + "_a.png", tmp + "_b.png", os.path.join(out, name))
        print("wrote", name)
        for ob in objs + markers:
            me = ob.data
            bpy.data.objects.remove(ob)
            bpy.data.meshes.remove(me)
    for s in ("_a.png", "_b.png"):
        if os.path.exists(tmp + s):
            os.remove(tmp + s)


if __name__ == "__main__":
    main()
