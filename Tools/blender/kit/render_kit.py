"""render_kit.py -- headless review renders of the laid-out kit (Workbench, grey studio look, optional UV checker).

    blender.exe -b --factory-startup --python Tools/blender/kit/render_kit.py -- --blend SourceArt/Kit/LB_Kit_P0.blend --out Docs/ArtTest/kit [--only name ...]
"""
import math
import os
import sys

import bpy
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
PREFIX = "SM_LB_Kit_"

# name, [piece name substrings], azimuth deg (0 = looking from -Y towards +Y), elevation deg, distance factor, checker?
VIEWS = [
    ("01_overview", ["*"], 28, 38, 1.05, False),
    ("02_overview_back", ["*"], 205, 34, 1.05, False),
    ("03_walls", ["Wall_400x60x800_A", "Wall_400x60x800_B", "Wall_100x60x800", "Wall_400x60x400", "Wall_100x60x400", "Wall_Corner", "Buttress"], 24, 20, 1.0, False),
    ("04_doorway", ["Doorway_Pointed"], 18, 10, 1.15, False),
    ("05_gate_arch", ["Gate_Arch"], 22, 14, 1.0, False),
    ("06_gate_arch_inside", ["Gate_Arch"], 4, 4, 0.75, False),
    ("07_broken_walls", ["Wall_400x60x800_Broken", "Wall_400x60x400_Broken", "Well_Wall"], 20, 22, 1.0, False),
    ("08_lancet_window", ["Window_Lancet"], 16, 8, 1.25, False),
    ("09_rubble", ["Rubble_"], 30, 30, 1.0, False),
    ("10_cliff_slabs", ["Cliff_Slab"], 24, 16, 1.0, False),
    ("11_piers_trims_floor", ["Pier_", "Trim_Plinth", "Floor_Slab"], 30, 34, 1.0, False),
    ("12_checker_walls_door", ["Wall_400x60x800_A", "Doorway_Pointed", "Window_Lancet", "Buttress"], 20, 14, 1.0, True),
]


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    blend = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SourceArt", "Kit", "LB_Kit_P0.blend"))
    out = os.path.normpath(os.path.join(HERE, "..", "..", "..", "Docs", "ArtTest", "kit"))
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


def world_bbox(obs):
    mn = Vector((1e9, 1e9, 1e9))
    mx = Vector((-1e9, -1e9, -1e9))
    for o in obs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], w[i])
                mx[i] = max(mx[i], w[i])
    return mn, mx


def setup_render(sc, w=1600, h=900):
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = 'PNG'
    sc.display.render_aa = '32'
    sh = sc.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'MATERIAL'
    sh.show_cavity = True
    sh.cavity_type = 'BOTH'
    sh.cavity_ridge_factor = 1.2
    sh.cavity_valley_factor = 1.2
    sh.show_shadows = True
    sh.shadow_intensity = 0.55
    sh.show_object_outline = False
    sh.show_specular_highlight = False
    sh.background_type = 'WORLD'
    if sc.world is None:
        sc.world = bpy.data.worlds.new("W")
    sc.world.color = (0.16, 0.17, 0.19)
    sc.display.light_direction = Vector((0.45, -0.55, 0.7)).normalized()


def make_camera(sc, lens=50.0):
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = lens
    cam_data.clip_start = 5.0
    cam_data.clip_end = 100000.0
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


def frame(cam, sc, mn, mx, az, el, dist_factor):
    centre = (mn + mx) * 0.5
    size = mx - mn
    radius = max(size.length * 0.5, 1.0)
    fov = 2 * math.atan(18.0 / cam.data.lens) if cam.data.sensor_fit != 'VERTICAL' else 1.0
    aspect = sc.render.resolution_x / sc.render.resolution_y
    hfov = 2 * math.atan(math.tan(fov / 2))
    # fit sphere into the narrower fov
    vfov = 2 * math.atan(math.tan(hfov / 2) / aspect)
    d = radius / math.sin(min(hfov, vfov) / 2) * dist_factor * 0.82
    a, e = math.radians(az), math.radians(el)
    off = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * d
    cam.location = centre + off
    direction = centre - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


def main():
    blend, out, only = parse_args()
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
    setup_render(sc)
    cam = make_camera(sc)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(PREFIX)]
    # checker material for slot 0
    img = bpy.data.images.new("chk", 1024, 1024)
    img.generated_type = 'COLOR_GRID'
    mat0 = bpy.data.materials["MAT_Masonry"]
    mat0.use_nodes = True
    nt = mat0.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf is not None:
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    for name, subs, az, el, df, checker in VIEWS:
        if only and not any(o in name for o in only):
            continue
        sel = meshes if subs == ["*"] else [o for o in meshes if any(s in o.name for s in subs)]
        if not sel:
            print("no objects for", name)
            continue
        for o in bpy.data.objects:
            if o.type == 'MESH':
                o.hide_render = (o not in sel) and not o.name.startswith("UCX_")
                if o.name.startswith("UCX_"):
                    o.hide_render = True
        if subs != ["*"]:
            # compact row so the camera can frame just these pieces
            cur = 0.0
            for o in sorted(sel, key=lambda o: o.name):
                bb = [Vector(c) for c in o.bound_box]
                w = max(c.x for c in bb) - min(c.x for c in bb)
                o.location = (cur, 0.0, 0.0)
                cur += w + max(60.0, w * 0.15)
            bpy.context.view_layer.update()
        mn, mx = world_bbox(sel)
        frame(cam, sc, mn, mx, az, el, df)
        sc.display.shading.color_type = 'TEXTURE' if checker else 'MATERIAL'
        sc.render.filepath = os.path.join(out, name + ".png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", sc.render.filepath)


if __name__ == "__main__":
    main()
