"""render_p11_rebuild.py -- P11-4b: old (grooved) and new (no masonry grooves) FBX side by side, Workbench, render_kit.py look.

Two steps (the second needs Pillow, which Blender's Python may not have, so it runs in the normal Python):

  1. panels (Blender):
     "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --factory-startup --python Tools/materials/render_p11_rebuild.py -- --tmp <dir> [--az 155] [--el 16] [--zoom 1.0] [--only NAME ...] [--size 1400 700]
     one PNG per piece, old on the left and new on the right.
  2. sheet (Python 3):
     python -I Tools/materials/render_p11_rebuild.py compose --tmp <dir> --out Docs/ArtTest/materials/p11_rebuild_render.png

The old FBX are read from Saved/p11_old_fbx (the copies taken before the rebuild), the new ones from the paths in
Tools/materials/p11_reimport_list.json.  Nothing is imported into Unreal.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
OLD_DIR = os.path.join(ROOT, "Saved", "p11_old_fbx")
LIST = os.path.join(HERE, "p11_reimport_list.json")

# panel order (the six asked for in the P11-4b brief, then the pieces added to look at the NEW-ONLY inset lines)
PIECES = [
    "SM_LB_Kit_Wall_400x60x800_B",
    "SM_LB_Kit_NaveBay_1000x60x1200",
    "SM_LB_Kit_NaveBay_1000x60x1200_Door",
    "SM_LB_Kit_Gate_Arch_1200x300x800",
    "SM_LB_Cl_Archway_500x40x1300",
    "SM_LB_Cl_Pier_80x80x640",
    "SM_LB_Tw_S1_N",
    "SM_LB_Tw_S1_W",
    "SM_LB_Kit_Gable_1620x60x1015",
    "SM_LB_Cl_ArcadeArch_270x80",
]


def args_after(flag, argv, n=1, default=None):
    if flag in argv:
        i = argv.index(flag)
        vals = argv[i + 1:i + 1 + n]
        return vals if n > 1 else vals[0]
    return default


def blender_main():
    import bpy
    from mathutils import Vector
    sys.path.insert(0, os.path.join(ROOT, "Tools", "blender", "kit"))
    import render_kit as R

    argv = sys.argv[sys.argv.index("--") + 1:]
    tmp = os.path.abspath(args_after("--tmp", argv))
    az = float(args_after("--az", argv, default=155.0))
    el = float(args_after("--el", argv, default=16.0))
    zoom = float(args_after("--zoom", argv, default=1.0))
    w, h = (int(v) for v in args_after("--size", argv, n=2, default=["1400", "700"]))
    only = []
    if "--only" in argv:
        for a in argv[argv.index("--only") + 1:]:
            if a.startswith("--"):
                break
            only.append(a)
    os.makedirs(tmp, exist_ok=True)
    fbx = {e["mesh"]: os.path.join(ROOT, e["fbx"]) for e in json.load(open(LIST))}

    def imp(path):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=path)
        new = [o for o in bpy.data.objects if o not in before]
        vis = [o for o in new if o.type == 'MESH' and not o.name.startswith("UCX_")]
        for o in new:
            if o not in vis:
                bpy.data.objects.remove(o)
        return vis[0]

    for name in PIECES:
        if only and not any(o in name for o in only):
            continue
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = bpy.context.scene
        old = imp(os.path.join(OLD_DIR, os.path.basename(fbx[name])))
        new = imp(fbx[name])
        gap = old.dimensions.x * 0.25 + 40.0 * old.scale.x
        # the camera looks at the front face from +Y of the imported frame, where +X runs to the LEFT of the picture,
        # so the old piece goes at the larger X to appear on the left
        old.location.x = new.location.x + new.dimensions.x + gap
        bpy.context.view_layer.update()
        R.setup_render(sc, w, h)
        sc.display.light_direction = Vector((0.45, 0.55, 0.7)).normalized()
        cam = R.make_camera(sc)
        cam.data.clip_end = 1e6
        mn, mx = R.world_bbox([old, new])
        R.frame(cam, sc, mn, mx, az, el, zoom)
        cam.data.clip_start = 0.01 * max((mx - mn).length, 1) * 0.1
        sc.render.filepath = os.path.join(tmp, name + ".png")
        bpy.ops.render.render(write_still=True)
        print("PANEL", name, "tris old/new", sum(len(p.vertices) - 2 for p in old.data.polygons), sum(len(p.vertices) - 2 for p in new.data.polygons))


def compose_main():
    from PIL import Image, ImageDraw
    argv = sys.argv[2:]
    tmp = os.path.abspath(args_after("--tmp", argv))
    out = os.path.abspath(args_after("--out", argv))
    ims = [(n, Image.open(os.path.join(tmp, n + ".png")).convert("RGB")) for n in PIECES if os.path.exists(os.path.join(tmp, n + ".png"))]
    if not ims:
        raise SystemExit("no panels in " + tmp)
    pw, ph = ims[0][1].size
    cols = 2
    rows = math.ceil(len(ims) / cols)
    cap = 34
    sheet = Image.new("RGB", (cols * pw, rows * (ph + cap)), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    for k, (n, im) in enumerate(ims):
        x, y = (k % cols) * pw, (k // cols) * (ph + cap)
        d.text((x + 10, y + 10), "%s    left: old (grooved)    right: new (no masonry grooves)" % n, fill=(235, 235, 235))
        sheet.paste(im, (x, y + cap))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sheet.save(out)
    print("SHEET", out, sheet.size)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "compose":
        compose_main()
    else:
        blender_main()
