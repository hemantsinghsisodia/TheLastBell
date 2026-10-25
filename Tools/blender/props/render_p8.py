"""render_p8.py -- headless Workbench review renders of the P8-3 chapel kit pieces and props.  Writes Docs/ArtTest/props/p8_*.png.

    blender.exe -b --factory-startup --python Tools/blender/props/render_p8.py -- --blend SourceArt/Kit/LB_Kit_P8.blend --set kit [--only name ...]
    blender.exe -b --factory-startup --python Tools/blender/props/render_p8.py -- --blend SourceArt/Props/Procedural/LB_Props_P8.blend --set props [--only name ...]

The review .blend files hold the un-mirrored authoring versions.  Each view lays the named pieces out in a row and frames them.
View tuple: (file, [object names: '=' = exact short name, otherwise substring], azimuth (0 = looking from -Y), elevation, dist factor,
gap, lens, option).  option 'back' puts a light backdrop plane behind the pieces so openings read.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "kit")))
sys.path.insert(0, HERE)
import render_kit as RK  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(ROOT, "Docs", "ArtTest", "props")

KIT_VIEWS = [
    ("p8_kit_navebay_inner", ["=NaveBay_1000x60x1200"], 0, 4, 1.0, 60, 50, "back"),
    ("p8_kit_navebay_outer", ["=NaveBay_1000x60x1200"], 180, 6, 1.0, 60, 50, "back"),
    ("p8_kit_navebay_3q", ["=NaveBay_1000x60x1200"], 28, 10, 1.0, 60, 50, "back"),
    ("p8_kit_navebay_lancet_close", ["=NaveBay_1000x60x1200"], 22, 12, 0.5, 60, 50, "back"),
    ("p8_kit_navebay_door_inner", ["=NaveBay_1000x60x1200_Door"], 0, 4, 1.0, 60, 50, "back"),
    ("p8_kit_navebay_door_outer", ["=NaveBay_1000x60x1200_Door"], 180, 6, 1.0, 60, 50, "back"),
    ("p8_kit_navebay_door_3q", ["=NaveBay_1000x60x1200_Door"], 30, 8, 1.0, 60, 50, "back"),
    ("p8_kit_navebay_clue_inner", ["=NaveBay_1000x60x1200_Clue"], 0, 4, 1.0, 60, 50, "back"),
    ("p8_kit_navebay_clue_close", ["=NaveBay_1000x60x1200_Clue"], 18, 6, 0.4, 60, 50, "back"),
    ("p8_kit_navebay_clue_outer", ["=NaveBay_1000x60x1200_Clue"], 180, 6, 1.0, 60, 50, "back"),
    ("p8_kit_eastwall_inner", ["=EastWall_1620x60x1200"], 0, 4, 1.0, 60, 50, "back"),
    ("p8_kit_eastwall_window_close", ["=EastWall_1620x60x1200"], 14, 8, 0.45, 60, 50, "back"),
    ("p8_kit_eastwall_outer", ["=EastWall_1620x60x1200"], 180, 6, 1.0, 60, 50, "back"),
    ("p8_kit_gable", ["=Gable_1620x60x1015"], 0, 4, 1.0, 60, 50, ""),
    ("p8_kit_gable_3q", ["=Gable_1620x60x1015"], 150, 14, 1.0, 60, 50, ""),
    ("p8_kit_corbel_dais_ridge", ["=Corbel_40x60x60", "=Dais_460x1000x30", "=RidgeCap_1000x40x30"], 28, 22, 1.0, 60, 50, ""),
    ("p8_kit_corbel", ["=Corbel_40x60x60"], 42, 12, 1.0, 20, 50, ""),
    ("p8_kit_dais", ["=Dais_460x1000x30"], 28, 28, 1.0, 20, 50, ""),
    ("p8_kit_roofslab", ["=RoofSlab_1000x1322x20", "=RoofSlab_1000x1322x20_Broken"], 20, 52, 1.0, 120, 50, ""),
    ("p8_kit_roofslab_under", ["=RoofSlab_1000x1322x20", "=RoofSlab_1000x1322x20_Broken"], 20, -52, 1.0, 120, 50, ""),
    ("p8_kit_roofslab_broken_close", ["=RoofSlab_1000x1322x20_Broken"], 25, 40, 0.8, 120, 50, ""),
    ("p8_kit_ridgecap", ["=RidgeCap_1000x40x30"], 18, 20, 0.6, 20, 50, ""),
]
PROP_VIEWS = []        # filled in from render_p8_props.py when --set props


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


def short(o):
    return o.name.split("SM_LB_Kit_")[-1].split("SM_LB_Prop_")[-1]


def pick(objs, subs):
    out = []
    for s in subs:
        if s.startswith("="):
            out += [o for o in objs if short(o) == s[1:]]
        else:
            out += [o for o in objs if s in o.name and o not in out]
    return out


def main():
    blend, which, only, out = args()
    os.makedirs(out, exist_ok=True)
    if blend:
        bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
    RK.setup_render(sc)
    sc.display.shading.show_cavity = True
    cam = RK.make_camera(sc)
    if which == "kit":
        views = KIT_VIEWS
    else:
        import render_p8_props as RP
        views = RP.PROP_VIEWS
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("UCX_") and o.name.startswith("SM_LB_")]
    back = None
    for name, subs, az, el, df, gap, lens, opt in views:
        if only and not any(k in name for k in only):
            continue
        sel = pick(meshes, subs)
        if not sel:
            print("no objects for", name)
            continue
        for o in bpy.data.objects:
            if o.type == 'MESH':
                o.hide_render = (o not in sel)
        cur = 0.0
        order = {("=" + short(o)): i for i, o in enumerate(sel)}
        for o in sorted(sel, key=lambda o: subs.index("=" + short(o)) if ("=" + short(o)) in subs else 0):
            bb = [Vector(c) for c in o.bound_box]
            xmin, xmax = min(c.x for c in bb), max(c.x for c in bb)
            o.location = (cur - xmin, 0.0, 0.0)
            cur += (xmax - xmin) + gap
        bpy.context.view_layer.update()
        if back is not None:
            bpy.data.objects.remove(back)
            back = None
        mn, mx = RK.world_bbox(sel)
        if "back" in opt:
            bpy.ops.mesh.primitive_plane_add(size=1.0)
            back = bpy.context.object
            back.name = "RV_back"
            back.scale = (mx.x - mn.x + 3000, 1.0, mx.z - mn.z + 3000)
            back.rotation_euler = (math.radians(90), 0, 0)
            front = (az % 360) < 90 or (az % 360) > 270
            back.location = ((mn.x + mx.x) / 2, (mx.y + 2200.0) if front else (mn.y - 2200.0), (mn.z + mx.z) / 2)
            mat = bpy.data.materials.new("rv_back")
            mat.diffuse_color = (0.55, 0.62, 0.75, 1.0)
            back.data.materials.append(mat)
        cam.data.lens = lens
        RK.frame(cam, sc, mn, mx, az, el, df)
        sc.render.filepath = os.path.join(out, name + ".png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", sc.render.filepath)


if __name__ == "__main__":
    main()
