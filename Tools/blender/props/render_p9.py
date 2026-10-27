"""render_p9.py -- headless review renders of the P9-3 crypt pieces.  Writes Docs/ArtTest/crypt/p9_*.png.

    blender.exe -b --factory-startup --python Tools/blender/props/render_p9.py -- [--blend SourceArt/Props/Procedural/Crypt/LB_Props_P9.blend]
                                                                                  [--set work|cycles|all] [--only name ...] [--out Docs/ArtTest/crypt]
    python Tools/blender/props/lineup_p9.py            # composite lineup (Pillow): Docs/ArtTest/crypt/p9_lineup.png

Workbench views of every piece (set 'work'), plus one Cycles view each of the ossuary bay, the portcullis and roots A (set 'cycles').
The review .blend holds the un-mirrored authoring versions (authoring space == Unreal space).  Each view lays the named pieces out in a row and
frames them.  View tuple: (file, [object names, '=' = exact short name], azimuth (0 = camera at -Y looking +Y, 90 = camera at +X, 180 = camera at +Y,
270 = camera at -X), elevation, dist factor, gap, lens, option).  option 'back' puts a light backdrop plane behind the pieces so openings read.
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "kit")))
import render_kit as RK  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(ROOT, "Docs", "ArtTest", "crypt")
LIGHT_ROT = float(os.environ.get("P9_LIGHT_ROT", "0"))
BLEND = os.path.join(ROOT, "SourceArt", "Props", "Procedural", "Crypt", "LB_Props_P9.blend")

# NOTE: OssuaryBay / PlaqueFrame / Corbel front faces point +Y (camera az 180 sees them); stair rises toward +X.
VIEWS = [
    ("p9_bay_front", ["=OssuaryBay_500x599"], 180, 6, 1.15, 60, 50, "back"),
    ("p9_bay_3q", ["=OssuaryBay_500x599"], 150, 14, 1.15, 60, 50, "back"),
    ("p9_bay_niche_close", ["=OssuaryBay_500x599"], 160, 12, 0.5, 60, 50, "back"),
    ("p9_capital", ["=Capital_A"], 30, 16, 1.1, 60, 50, ""),
    ("p9_capital_under", ["=Capital_A"], 30, -26, 1.1, 60, 50, ""),
    ("p9_stair_side", ["=Stair40_300"], 0, 3, 1.0, 60, 50, ""),
    ("p9_stair_3q", ["=Stair40_300"], 305, 26, 1.0, 60, 50, ""),
    ("p9_stair_close", ["=Stair40_300"], 300, 22, 0.28, 60, 50, ""),
    ("p9_sarcophagus_a", ["=Sarcophagus_A"], 30, 22, 1.0, 60, 50, ""),
    ("p9_sarcophagus_b", ["=Sarcophagus_B"], 30, 22, 1.0, 60, 50, ""),
    ("p9_sarcophagus_b_end", ["=Sarcophagus_B"], 285, 30, 0.9, 60, 50, ""),
    ("p9_sarcophagus_pair", ["=Sarcophagus_A", "=Sarcophagus_B"], 28, 24, 0.7, 40, 50, ""),
    ("p9_bonebin", ["=BoneBin_200x100x60"], 28, 28, 1.0, 60, 50, ""),
    ("p9_blocks", ["=Block_100", "=Block_100_C"], 25, 22, 1.0, 40, 50, ""),
    ("p9_corbel", ["=Corbel_A"], 40, 16, 1.4, 60, 50, ""),
    ("p9_corbel_side", ["=Corbel_A"], 90, 4, 1.4, 60, 50, ""),
    ("p9_beam", ["=Beam_35x45x1120"], 28, 28, 1.0, 60, 50, ""),
    ("p9_beam_close", ["=Beam_35x45x1120"], 28, 35, 0.35, 60, 50, ""),
    ("p9_boards", ["=Boards_300x250"], 20, 55, 1.0, 60, 50, ""),
    ("p9_boards_broken", ["=Boards_300x250_Broken"], 20, 50, 1.0, 60, 50, ""),
    ("p9_boards_broken_side", ["=Boards_300x250_Broken"], 0, 6, 1.0, 60, 50, ""),
    ("p9_roots_a", ["=RootsHang_A"], 20, 4, 1.3, 60, 50, ""),
    ("p9_roots_b", ["=RootsHang_B"], 20, 4, 1.3, 60, 50, ""),
    ("p9_roots_c", ["=RootsHang_C"], 20, 4, 1.3, 60, 50, ""),
    ("p9_roots_set", ["=RootsHang_A", "=RootsHang_B", "=RootsHang_C"], 15, 6, 1.3, 40, 50, ""),
    ("p9_portcullis", ["=Portcullis_300x60x560"], 20, 8, 1.3, 60, 50, "back"),
    ("p9_portcullis_close", ["=Portcullis_300x60x560"], 28, 12, 0.3, 60, 50, "back"),
    ("p9_portcullis_foot", ["=Portcullis_300x60x560"], 22, 6, 0.25, 60, 50, "back"),
    ("p9_rubble_front", ["=RubbleFill_100x400x560"], 270, 6, 1.15, 60, 50, ""),
    ("p9_rubble_3q", ["=RubbleFill_100x400x560"], 235, 20, 1.15, 60, 50, ""),
    ("p9_rubble_back", ["=RubbleFill_100x400x560"], 100, 14, 1.15, 60, 50, ""),
    ("p9_crank", ["=Crank_A"], 25, 30, 1.15, 60, 50, ""),
    ("p9_crank_top", ["=Crank_A"], 0, 75, 1.15, 60, 50, ""),
    ("p9_capstan", ["=CapstanDrum_80x50"], 30, 28, 1.15, 60, 50, ""),
    ("p9_capstan_top", ["=CapstanDrum_80x50"], 0, 70, 1.15, 60, 50, ""),
    ("p9_plaqueframe", ["=PlaqueFrame_270x195"], 180, 4, 1.15, 60, 50, "back"),
    ("p9_plaqueframe_3q", ["=PlaqueFrame_270x195"], 150, 14, 1.15, 60, 50, "back"),
    ("p9_winch", ["=WinchFrame"], 0, 8, 1.15, 60, 50, ""),
    ("p9_winch_3q", ["=WinchFrame"], 32, 20, 1.15, 60, 50, ""),
    ("p9_winch_end", ["=WinchFrame"], 90, 12, 1.15, 60, 50, ""),
]
CYCLES_VIEWS = [
    ("p9_cycles_ossuary_bay", "=OssuaryBay_500x599", 160, 10, 1.12),
    ("p9_cycles_portcullis", "=Portcullis_300x60x560", 25, 8, 1.3),
    ("p9_cycles_roots_a", "=RootsHang_A", 20, 4, 1.35),
]


def args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    blend, which, only, out = BLEND, "work", [], OUT
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
    return o.name.split("SM_LB_Crypt_")[-1].split("SM_LB_Prop_")[-1]


def pick(objs, subs):
    out = []
    for s in subs:
        if s.startswith("="):
            out += [o for o in objs if short(o) == s[1:]]
        else:
            out += [o for o in objs if s in o.name and o not in out]
    return out


def lay_out(sel, subs, gap):
    cur = 0.0
    for o in sorted(sel, key=lambda o: subs.index("=" + short(o)) if ("=" + short(o)) in subs else 0):
        bb = [Vector(c) for c in o.bound_box]
        xmin, xmax = min(c.x for c in bb), max(c.x for c in bb)
        o.location = (cur - xmin, 0.0, 0.0)
        cur += (xmax - xmin) + gap
    bpy.context.view_layer.update()


def add_back(mn, mx, az):
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
    return back


def run_work(meshes, only, out):
    sc = bpy.context.scene
    RK.setup_render(sc)
    sh = sc.display.shading
    sh.show_cavity = True
    sh.cavity_ridge_factor = 1.6
    sh.cavity_valley_factor = 1.8
    sh.shadow_intensity = 0.75
    sh.show_shadows = True
    cam = RK.make_camera(sc)
    back = None
    for name, subs, az, el, df, gap, lens, opt in VIEWS:
        if only and not any(k in name for k in only):
            continue
        sel = pick(meshes, subs)
        if not sel:
            print("no objects for", name)
            continue
        for o in bpy.data.objects:
            if o.type == 'MESH':
                o.hide_render = (o not in sel)
        lay_out(sel, subs, gap)
        if back is not None:
            bpy.data.objects.remove(back)
            back = None
        mn, mx = RK.world_bbox(sel)
        if "back" in opt:
            back = add_back(mn, mx, az)
        cam.data.lens = lens
        RK.frame(cam, sc, mn, mx, az, el, df)
        # the studio lights are locked to the world (not the view) and rotated with the camera azimuth, so a face looking at the camera is always lit
        sc.display.shading.use_world_space_lighting = True
        sc.display.shading.studiolight_rotate_z = math.radians(az + LIGHT_ROT)
        sc.display.light_direction = Matrix.Rotation(math.radians(az), 3, 'Z') @ Vector((-0.42, -0.62, 0.66)).normalized()
        sc.render.filepath = os.path.join(out, name + ".png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", sc.render.filepath)
    if back is not None:
        bpy.data.objects.remove(back)


def colour_materials():
    """Principled materials coloured like the viewport colours, so Cycles shows the same slots."""
    for m in bpy.data.materials:
        if not m.name.startswith("MAT_"):
            continue
        m.use_nodes = True
        nt = m.node_tree
        bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf is None:
            continue
        col = tuple(m.diffuse_color)
        # stone/wood/bark read a touch darker + rougher in Cycles than in the studio view
        bsdf.inputs['Base Color'].default_value = (col[0] * 0.9, col[1] * 0.9, col[2] * 0.9, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.35 if m.name == "MAT_Iron" else 0.85
        if m.name == "MAT_Iron":
            bsdf.inputs['Metallic'].default_value = 0.3
            bsdf.inputs['Base Color'].default_value = (col[0] * 2.2, col[1] * 2.2, col[2] * 2.2, 1.0)


def run_cycles(meshes, only, out):
    sc = bpy.context.scene
    colour_materials()
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    try:
        sc.cycles.device = 'CPU'
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.render.film_transparent = False
    world = sc.world or bpy.data.worlds.new("W")
    sc.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0.020, 0.024, 0.032, 1.0)
    bg.inputs['Strength'].default_value = 1.0
    cam = RK.make_camera(sc)
    cam.data.lens = 50
    for name, sub, az, el, df in CYCLES_VIEWS:
        if only and not any(k in name for k in only):
            continue
        sel = pick(meshes, [sub])
        if not sel:
            continue
        for o in bpy.data.objects:
            if o.type == 'MESH':
                o.hide_render = (o not in sel)
        for o in sel:
            o.location = (0, 0, 0)
        bpy.context.view_layer.update()
        mn, mx = RK.world_bbox(sel)
        centre = (mn + mx) * 0.5
        size = max((mx - mn).length, 1.0)
        # old lights out, a warm key (a candle-like point) + a cool moon spot from above, as the crypt will be lit
        for l in [o for o in bpy.data.objects if o.type == 'LIGHT']:
            bpy.data.objects.remove(l)
        a, e = math.radians(az), math.radians(el)
        view_dir = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        side = Vector((math.cos(a), math.sin(a), 0.0))
        key = bpy.data.lights.new("key", 'AREA')
        dist_m = size * 0.9 * 0.01
        key.energy = 90000.0 * dist_m * dist_m
        key.size = size * 0.6
        key.color = (1.0, 0.72, 0.45)
        ko = bpy.data.objects.new("key", key)
        sc.collection.objects.link(ko)
        ko.location = centre + view_dir * size * 0.9 + side * size * 0.7 + Vector((0, 0, size * 0.25))
        ko.rotation_euler = (centre - ko.location).to_track_quat('-Z', 'Y').to_euler()
        moon = bpy.data.lights.new("moon", 'SUN')
        moon.energy = 2.5
        moon.color = (0.6, 0.72, 1.0)
        mo = bpy.data.objects.new("moon", moon)
        sc.collection.objects.link(mo)
        mo.rotation_euler = (math.radians(55), 0, math.radians(az + 200))
        RK.frame(cam, sc, mn, mx, az, el, df)
        sc.render.filepath = os.path.join(out, name + ".png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", sc.render.filepath)


def main():
    blend, which, only, out = args()
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=blend)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("UCX_") and o.name.startswith("SM_LB_")]
    if which in ("work", "all"):
        run_work(meshes, only, out)
    if which in ("cycles", "all"):
        run_cycles(meshes, only, out)


if __name__ == "__main__":
    main()
