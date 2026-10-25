"""render_fix3.py -- headless Workbench review renders of the P7-FIX3 G2a pieces (arcade bays, kerbs, well-head, timber,
earth patch, ivy cards, dead tree, CC0 plants).  Writes Docs/ArtTest/props/fix3_*.png.

    blender.exe -b --factory-startup --python Tools/blender/props/render_fix3.py -- --blend SourceArt/Kit/LB_Kit_Fix3.blend --set kit [--only name ...]
    blender.exe -b --factory-startup --python Tools/blender/props/render_fix3.py -- --blend SourceArt/Props/Procedural/LB_Props_Fix3.blend --set props [--only name ...]

The review .blend files hold the un-mirrored authoring versions.  Each view lays the named pieces out in a row (gap 60 cm)
and frames them.  `--set cc0` renders the converted CC0 FBX files (SourceArt/Props/CC0/<Name>/*.fbx) instead of a .blend.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "kit")))
import render_kit as RK  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(ROOT, "Docs", "ArtTest", "props")

# (file name, [object-name substrings, exact match when it starts with '='], azimuth, elevation, dist factor, gap, lens)
KIT_VIEWS = [
    ("fix3_arcade_intact_front", ["=ArcadeBay_1000x60x400"], 0, 6, 1.0, 60, 50),
    ("fix3_arcade_intact_3q", ["=ArcadeBay_1000x60x400"], 32, 16, 1.0, 60, 50),
    ("fix3_arcade_intact_back_3q", ["=ArcadeBay_1000x60x400"], 205, 12, 1.0, 60, 50),
    ("fix3_arcade_under", ["=ArcadeBay_1000x60x400"], 10, -3, 0.85, 60, 40),
    ("fix3_arcade_broken_row", ["=ArcadeBay_1000x60x400_BrokenA", "=ArcadeBay_1000x60x400", "=ArcadeBay_1000x60x400_BrokenB"], 0, 8, 1.0, 40, 50),
    ("fix3_arcade_broken_A_3q", ["=ArcadeBay_1000x60x400_BrokenA"], 28, 18, 1.0, 60, 50),
    ("fix3_arcade_broken_B_3q", ["=ArcadeBay_1000x60x400_BrokenB"], -28, 18, 1.0, 60, 50),
    ("fix3_arcade_broken_AB_back", ["=ArcadeBay_1000x60x400_BrokenA", "=ArcadeBay_1000x60x400_BrokenB"], 200, 20, 1.0, 60, 50),
    ("fix3_kerbs", ["Kerb"], 22, 28, 1.0, 40, 50),
]
PROP_VIEWS = [
    ("fix3_wellhead_3q", ["WellHead_A"], 30, 24, 1.0, 60, 50),
    ("fix3_wellhead_top", ["WellHead_A"], 0, 80, 1.0, 60, 50),
    ("fix3_wellhead_side", ["WellHead_A"], 90, 8, 1.0, 60, 50),
    ("fix3_wellhead_winch", ["WellHead_A"], 60, 12, 0.7, 60, 50),
    ("fix3_timber_set", ["TimberPost", "Rafter", "RoofPlanks"], 20, 18, 1.0, 40, 50),
    ("fix3_timber_purlin", ["Purlin"], 20, 12, 1.0, 40, 50),
    ("fix3_timber_planks_top", ["RoofPlanks"], 0, 75, 1.0, 40, 50),
    ("fix3_earthpatch", ["EarthPatch"], 25, 30, 1.0, 40, 50),
    ("fix3_deadtree", ["DeadTree"], 25, 8, 1.0, 40, 50),
    ("fix3_deadtree_side", ["DeadTree"], 115, 4, 1.0, 40, 50),
    ("fix3_deadtree_top", ["DeadTree"], 0, 60, 1.0, 40, 50),
    ("fix3_ivy_cards", ["Ivy_"], 180, 4, 1.0, 40, 50),
    ("fix3_ivy_dead_cards", ["Ivy_"], 180, 4, 1.0, 40, 50),
    ("fix3_ivy_green_3q", ["Ivy_Climb_300x450_Green", "Ivy_Creep_400x200_Green"], 150, 8, 0.8, 60, 50),
    ("fix3_ivy_dead_3q", ["Ivy_Climb_300x450_Dead", "Ivy_Creep_400x200_Dead"], 150, 8, 0.8, 60, 50),
    ("fix3_ivy_green_close", ["Ivy_Patch_200x300_Green"], 165, 6, 0.8, 60, 50),
]


CC0_VIEWS = [
    # name, folder, azimuth, elevation, dist factor, gap
    ("fix3_cc0_grass", "GrassMedium02", 20, 18, 1.0, 10),
    ("fix3_cc0_rooibos", "WildRooibos", 20, 18, 1.0, 15),
    ("fix3_cc0_searsia", "SearsiaLucida", 20, 14, 1.0, 40),
    ("fix3_cc0_trunk02", "DeadTreeTrunk02", 30, 8, 1.0, 40),
]


def render_cc0(only, out):
    sc = bpy.context.scene
    RK.setup_render(sc)
    sc.display.shading.color_type = 'TEXTURE'
    sc.display.shading.light = 'STUDIO'
    cam = RK.make_camera(sc)
    for name, folder, az, el, df, gap in CC0_VIEWS:
        if only and not any(k in name for k in only):
            continue
        d = os.path.join(ROOT, "SourceArt", "Props", "CC0", folder)
        for o in list(bpy.data.objects):
            if o.type == 'MESH':
                bpy.data.objects.remove(o)
        objs = []
        diff = [f for f in os.listdir(d) if "_diff_" in f]
        mat = bpy.data.materials.new("rv_" + folder)
        mat.use_nodes = True
        if diff:
            tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
            tex.image = bpy.data.images.load(os.path.join(d, diff[0]))
            mat.node_tree.links.new(tex.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
        for f in sorted(x for x in os.listdir(d) if x.endswith(".fbx")):
            before = set(bpy.data.objects)
            bpy.ops.import_scene.fbx(filepath=os.path.join(d, f))
            for o in set(bpy.data.objects) - before:
                if o.type == 'MESH' and not o.name.startswith("UCX_"):
                    o.data.materials.clear()
                    o.data.materials.append(mat)
                    o.scale = (1.0, 1.0, 1.0)              # the importer scales cm meshes by 0.01; keep 1 BU = 1 cm
                    objs.append(o)
                elif o.type == 'MESH':
                    o.hide_render = True
        cur = 0.0
        for o in objs:
            bb = [Vector(c) for c in o.bound_box]
            xmin, xmax = min(c.x for c in bb), max(c.x for c in bb)
            o.location = (cur - xmin, 0.0, 0.0)
            cur += (xmax - xmin) + gap
        bpy.context.view_layer.update()
        cam.data.lens = 50.0
        mn, mx = RK.world_bbox(objs)
        RK.frame(cam, sc, mn, mx, az, el, df)
        sc.render.filepath = os.path.join(out, name + ".png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", sc.render.filepath)


def args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    blend, which, only, out = None, "kit", [], OUT
    i = 0
    while i < len(argv):
        if argv[i] == "--blend":
            blend = os.path.abspath(argv[i + 1]); i += 2
        elif argv[i] == "--out":
            out = os.path.abspath(argv[i + 1]); i += 2
        elif argv[i] == "--set":
            which = argv[i + 1]; i += 2
        elif argv[i] == "--only":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                only.append(argv[i]); i += 1
        else:
            i += 1
    return blend, which, only, out


def pick(objs, subs):
    out = []
    for s in subs:
        if s.startswith("="):
            out += [o for o in objs if o.name.split("SM_LB_Kit_")[-1].split("SM_LB_Prop_")[-1] == s[1:]]
        else:
            out += [o for o in objs if s in o.name and o not in out]
    return out


def leaf_texture(src_id):
    """RGBA image = ambientCG Color + Opacity (alpha) for the Cycles review of the ivy cards."""
    import numpy as np
    base = os.path.join(ROOT, "ExternalAssets", "Incoming", "ambientcg-" + src_id, src_id + "_2K-JPG", src_id + "_2K-JPG_")
    c = bpy.data.images.load(base + "Color.jpg")
    o = bpy.data.images.load(base + "Opacity.jpg")
    w, h = c.size
    ca = np.array(c.pixels[:], dtype=np.float32).reshape(h, w, 4)
    oa = np.array(o.pixels[:], dtype=np.float32).reshape(h, w, 4)
    ca[:, :, 3] = (oa[:, :, 0] > 0.5).astype(np.float32)
    im = bpy.data.images.new("leaf_" + src_id, w, h, alpha=True)
    im.pixels = ca.ravel().tolist()
    im.alpha_mode = 'STRAIGHT'
    return im


def cycles_ivy_setup(sc, objs):
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 24
    try:
        sc.cycles.use_denoising = True
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    imgs = {}
    stem = bpy.data.materials.new("rv_stem")
    stem.use_nodes = True
    stem.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.12, 0.085, 0.05, 1)
    for o in objs:
        kind = "LeafSet030" if o.name.endswith("_Dead") else "LeafSet017"
        if kind not in imgs:
            im = leaf_texture(kind)
            m = bpy.data.materials.new("rv_leaf_" + kind)
            m.use_nodes = True
            nt = m.node_tree
            bsdf = nt.nodes["Principled BSDF"]
            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = im
            tex.interpolation = 'Linear'
            nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
            nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
            bsdf.inputs["Roughness"].default_value = 0.55
            imgs[kind] = m
        o.data.materials.clear()
        o.data.materials.append(imgs[kind])
        o.data.materials.append(stem)
        for p in o.data.polygons:
            pass
    # wall + lights
    bpy.ops.mesh.primitive_plane_add(size=4000, location=(0, -0.5, 300), rotation=(math.radians(90), 0, 0))
    wall = bpy.context.object
    wm = bpy.data.materials.new("rv_wall")
    wm.use_nodes = True
    wm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.35, 0.33, 0.30, 1)
    wall.data.materials.append(wm)
    wall.name = "RV_wall"
    sun = bpy.data.lights.new("sun", 'SUN')
    sun.energy = 3.0
    so = bpy.data.objects.new("sun", sun)
    sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(55), math.radians(15), math.radians(200))
    sc.world = sc.world or bpy.data.worlds.new("W")
    sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.5, 0.55, 0.65, 1)
    sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
    return wall


def main():
    blend, which, only, OUT = args()
    os.makedirs(OUT, exist_ok=True)
    if which == "cc0":
        render_cc0(only, OUT)
        return
    if blend:
        bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
    RK.setup_render(sc)
    sc.display.shading.show_cavity = True
    cam = RK.make_camera(sc)
    views = KIT_VIEWS if which == "kit" else PROP_VIEWS
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("UCX_") and o.name.startswith("SM_LB_")]
    ivy_dead = [o for o in meshes if "Ivy_" in o.name and o.name.endswith("_Dead")]
    for name, subs, az, el, df, gap, lens in views:
        if only and not any(k in name for k in only):
            continue
        sel = pick(meshes, subs)
        if name.endswith("ivy_cards"):
            sel = [o for o in sel if o.name.endswith("_Green")]
        if name.endswith("ivy_dead_cards"):
            sel = ivy_dead
        if not sel:
            print("no objects for", name)
            continue
        for o in bpy.data.objects:
            if o.type == 'MESH' and o.name != "RV_wall":
                o.hide_render = (o not in sel)
        if "ivy" in name and not getattr(main, "cyc", False):
            main.cyc = True
            main.wall = cycles_ivy_setup(sc, [o for o in meshes if "Ivy_" in o.name])
        cur = 0.0
        for o in sorted(sel, key=lambda o: o.name):
            bb = [Vector(c) for c in o.bound_box]
            xmin, xmax = min(c.x for c in bb), max(c.x for c in bb)
            o.location = (cur - xmin, 0.0, 0.0)
            cur += (xmax - xmin) + gap
        bpy.context.view_layer.update()
        cam.data.lens = lens
        mn, mx = RK.world_bbox(sel)
        RK.frame(cam, sc, mn, mx, az, el, df)
        sc.render.filepath = os.path.join(OUT, name + ".png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", sc.render.filepath)


if __name__ == "__main__":
    main()
