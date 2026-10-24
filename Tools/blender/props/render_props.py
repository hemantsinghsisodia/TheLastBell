"""render_props.py -- headless Workbench review renders of the procedural props (P7F-2).

    blender.exe -b --factory-startup --python Tools/blender/props/render_props.py -- [--blend SourceArt/Props/Procedural/LB_Props.blend] [--out Docs/ArtTest/props] [--only name ...]

Views: 01 overview, 02 key macro, 03 key at arm's length on the ledge, 04 ledge, 05 graveyard (stones, crosses, mounds),
06 hand-cart (3/4), 07 fire pit.  Authoring space; the review .blend holds the un-mirrored pieces.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "kit")))
import render_kit as RK  # noqa: E402

PREFIX = "SM_LB_Prop_"


def args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    root = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
    blend = os.path.join(root, "SourceArt", "Props", "Procedural", "LB_Props.blend")
    out = os.path.join(root, "Docs", "ArtTest", "props")
    only = []
    i = 0
    while i < len(argv):
        if argv[i] == "--blend":
            blend = os.path.abspath(argv[i + 1]); i += 2
        elif argv[i] == "--out":
            out = os.path.abspath(argv[i + 1]); i += 2
        elif argv[i] == "--only":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                only.append(argv[i]); i += 1
        else:
            i += 1
    return blend, out, only


def main():
    blend, out, only = args()
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
    RK.setup_render(sc)
    sc.display.shading.show_cavity = True
    cam = RK.make_camera(sc)
    src = {o.name[len(PREFIX):]: o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(PREFIX)}
    for o in bpy.data.objects:
        if o.type == 'MESH':
            o.hide_render = True
    made = []

    def put(name, loc, yaw=0.0, pitch=0.0, roll=0.0, scale=(1, 1, 1)):
        o = src[name].copy()
        o.data = src[name].data
        o.parent = None
        o.location = loc
        o.rotation_euler = (math.radians(pitch), math.radians(roll), math.radians(yaw))
        o.scale = scale
        o.hide_render = False
        sc.collection.objects.link(o)
        made.append(o)
        return o

    def clear():
        for o in made:
            bpy.data.objects.remove(o)
        made.clear()

    def shot(name, objs, az, el, df, lens=50.0, target=None):
        if only and not any(k in name for k in only):
            return
        bpy.context.view_layer.update()
        cam.data.lens = lens
        mn, mx = RK.world_bbox(objs)
        RK.frame(cam, sc, mn, mx, az, el, df)
        sc.render.filepath = os.path.join(out, name + ".png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", sc.render.filepath)

    def look(name, eye, tgt, lens):
        if only and not any(k in name for k in only):
            return
        cam.data.lens = lens
        cam.location = Vector(eye)
        cam.rotation_euler = (Vector(tgt) - Vector(eye)).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(out, name + ".png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", sc.render.filepath)

    # 01 overview: the whole set in a row
    x = 0.0
    row = []
    for nm in ["Key_Chapel", "KeyLedge_50x50x70", "Gravestone_A", "Gravestone_B", "Gravestone_C", "Gravestone_C_Frag",
               "Gravestone_D", "StoneCross_A", "WoodCross_A", "GraveMound_A", "FirePit_A", "HandCart_A"]:
        o = src[nm]
        w = o.dimensions.x if nm not in ("HandCart_A",) else o.dimensions.x
        row.append(put(nm, (x + w / 2, 0, 0)))
        x += w + 40
    shot("01_overview", row, 0, 22, 1.0)
    clear()

    # 02 key macro (lying flat, camera above 3/4) and key alone from low angle
    k = put("Key_Chapel", (0, 0, 0), yaw=0)
    shot("02_key_macro", [k], 8, 52, 1.0)
    shot("02b_key_macro_top", [k], 0, 88, 1.0)
    shot("02c_key_macro_side", [k], 25, 14, 1.0)
    clear()

    # 03 key on ledge at arm's length, 04 ledge
    led = put("KeyLedge_50x50x70", (0, 0, 0))
    k = put("Key_Chapel", (0, 0, 70.0), yaw=65.0)
    look("03_key_armslength", (35, -80, 150), (0, 0, 72), 28.0)
    look("03b_key_armslength_close", (22, -45, 120), (0, 0, 71), 28.0)
    shot("04_ledge", [led, k], 28, 20, 1.0)
    clear()

    # 05 graveyard: stones face +Y in authoring space -> camera from +Y side (az ~ 190)
    objs = []
    xs = [("Gravestone_A", 0, 0), ("StoneCross_A", 90, 0), ("Gravestone_B", 190, 0), ("Gravestone_C", 280, 0),
          ("Gravestone_D", 360, 40), ("WoodCross_A", 430, 0)]
    for nm, x, y in xs:
        objs.append(put(nm, (x, y, 0), yaw=0.0))
        if nm not in ("Gravestone_D",):
            objs.append(put("GraveMound_A", (x, y + 125, 0), yaw=90.0, scale=(0.5, 1, 1)))
    objs.append(put("Gravestone_C_Frag", (320, 70, 0), yaw=35.0, pitch=80.0))
    # re-seat the fallen fragment on the ground
    fr = objs[-1]
    bpy.context.view_layer.update()
    mn, mx = RK.world_bbox([fr])
    fr.location.z -= mn.z
    shot("05_graveyard", objs, 196, 14, 0.9)
    shot("05b_graveyard_close_stones", objs[:1] + objs[2:4] + objs[6:8], 196, 8, 0.9)
    clear()
    # stones alone, bigger
    a = put("Gravestone_A", (0, 0, 0)); b = put("Gravestone_B", (80, 0, 0)); c = put("Gravestone_C", (160, 0, 0))
    d = put("Gravestone_D", (230, 0, 0)); cr = put("StoneCross_A", (300, 0, 0))
    shot("05c_stones_front", [a, b, c, d, cr], 180 + 12, 10, 0.95)
    clear()

    # 06 cart 3/4
    ct = put("HandCart_A", (0, 0, 0))
    shot("06_cart_3q", [ct], 35, 20, 1.0)
    shot("06b_cart_side", [ct], 90, 8, 1.0)
    shot("06c_cart_worn_side", [ct], 215, 28, 1.0)
    shot("06d_cart_top", [ct], 0, 80, 1.0)
    clear()

    # 07 fire pit
    fp = put("FirePit_A", (0, 0, 0))
    shot("07_firepit", [fp], 25, 32, 1.0)
    clear()


if __name__ == "__main__":
    main()
