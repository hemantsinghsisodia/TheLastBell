"""render_r2.py -- headless review renders of the P9-R2A pieces (bell wheel, dial-lever set, roof-hole gobo).  Writes Docs/ArtTest/props/r2_*.png.

    blender.exe -b --factory-startup --python Tools/blender/props/render_r2.py -- [--blend SourceArt/Props/Procedural/R2/LB_Props_R2.blend]
                                                                                   [--set work|cycles|lever|all] [--only name ...] [--out Docs/ArtTest/props]

Sets: 'work' = Workbench views of the single pieces; 'lever' = the five lever parts assembled the way BP_DialLever places its components (arm at the high / mid / low notch,
Workbench), including a Blender text object for the label; 'cycles' = Cycles views of the wheel and the assembled lever (metal + bronze read better).
The review blend holds the un-mirrored authoring versions (authoring space == Unreal space); a UE pitch of p degrees is a Blender rotation of -p about Y.
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "kit")))
import render_kit as RK  # noqa: E402
import render_p9 as R9  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(ROOT, "Docs", "ArtTest", "props")
BLEND = os.path.join(ROOT, "SourceArt", "Props", "Procedural", "R2", "LB_Props_R2.blend")

# (file, [object names, '=' = exact short name], azimuth (0 = camera at -Y, 90 = camera at +X), elevation, dist factor, gap, lens, option)
VIEWS = [
    ("r2_bellwheel_3q", ["=BellWheel_A"], 30, 24, 0.8, 60, 50, ""),
    ("r2_bellwheel_3q_b", ["=BellWheel_A"], 215, 18, 0.8, 60, 50, ""),
    ("r2_bellwheel_side", ["=BellWheel_A"], 0, 4, 0.8, 60, 50, ""),
    ("r2_bellwheel_top", ["=BellWheel_A"], 0, 82, 0.8, 60, 50, ""),
    ("r2_bellwheel_under", ["=BellWheel_A"], 20, -38, 0.8, 60, 50, ""),
    ("r2_bellwheel_bells_close", ["=BellWheel_A"], 25, -12, 0.45, 60, 50, ""),
    ("r2_backplate_front", ["=DialLever_Backplate"], 90, 4, 1.6, 60, 50, ""),
    ("r2_backplate_3q", ["=DialLever_Backplate"], 55, 18, 1.6, 60, 50, ""),
    ("r2_quadrant", ["=DialLever_Quadrant"], 70, 10, 1.6, 60, 50, ""),
    ("r2_quadrant_front", ["=DialLever_Quadrant"], 90, 0, 1.6, 60, 50, ""),
    ("r2_arm", ["=DialLever_Arm"], 0, 0, 1.6, 60, 50, ""),
    ("r2_arm_grip", ["=DialLever_Arm"], 20, 10, 0.7, 60, 50, ""),
    ("r2_weight", ["=DialLever_Weight"], 25, 8, 1.6, 60, 50, ""),
    ("r2_weight_body", ["=DialLever_Weight"], 25, 10, 0.7, 60, 50, ""),
    ("r2_notchstop", ["=DialLever_NotchStop"], 60, 24, 1.1, 60, 50, ""),
    ("r2_gobo_front", ["=SM_LB_Gobo_RoofHole"], 90, 0, 1.0, 60, 50, "backx"),
    ("r2_gobo_close", ["=SM_LB_Gobo_RoofHole"], 90, 0, 0.55, 60, 50, "backx"),
]
LEVER_VIEWS = [
    # name, pitch (UE degrees, + = arm up), azimuth, elevation, dist factor
    ("r2_lever_mid_3q", 0.0, 58, 14, 1.1),
    ("r2_lever_high_3q", 35.0, 58, 14, 0.8),
    ("r2_lever_low_3q", -35.0, 58, 14, 0.8),
    ("r2_lever_high_side", 35.0, 0, 0, 0.8),
    ("r2_lever_mid_side", 0.0, 0, 0, 0.8),
    ("r2_lever_low_side", -35.0, 0, 0, 0.8),
    ("r2_lever_mid_top", 0.0, 0, 82, 0.8),
    ("r2_lever_high_back3q", 35.0, 125, 14, 0.8),
    ("r2_lever_side", 35.0, 0, 0, 0.8),                                      # R2-A3: face-on to the sector (camera at -Y), arm at the high notch
]
CYCLES_VIEWS = [
    ("r2_cycles_bellwheel", "wheel", 28, 22, 1.1),
    ("r2_cycles_bellwheel_under", "wheel", 18, -30, 1.1),
    ("r2_cycles_lever_mid_3q", "lever0", 58, 14, 1.3),
    ("r2_cycles_lever_high_3q", "lever35", 58, 14, 1.3),
    ("r2_cycles_lever_low_3q", "lever-35", 58, 14, 1.3),
    ("r2_cycles_lever_mid_side", "lever0", 0, 0, 1.3),
    ("r2_cycles_lever_high_side", "lever35", 0, 0, 1.3),
    ("r2_cycles_lever_low_side", "lever-35", 0, 0, 1.3),
    ("r2_cycles_lever_chain_top", "lever0", 40, 20, 1.0),
    ("r2_cycles_lever_chain_top_side", "lever0", 0, 0, 1.0),
    ("r2_cycles_lever_high_back3q", "lever35", 125, 14, 1.3),
]


PREFIX = "r2"                                                                # --prefix r2a3 renames every output r2_* -> r2a3_*


def outname(name):
    return PREFIX + name[2:] if name.startswith("r2") else name


def args():
    global PREFIX
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    blend, which, only, out = BLEND, "work", [], OUT
    i = 0
    while i < len(argv):
        if argv[i] == "--blend":
            blend = os.path.abspath(argv[i + 1])
            i += 2
        elif argv[i] == "--out":
            out = os.path.abspath(argv[i + 1])
            i += 2
        elif argv[i] == "--set":
            which = argv[i + 1]
            i += 2
        elif argv[i] == "--prefix":
            PREFIX = argv[i + 1]
            i += 2
        elif argv[i] == "--only":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                only.append(argv[i])
                i += 1
        else:
            i += 1
    return blend, which, only, out


def add_back_x(mn, mx):
    """Light backdrop plane perpendicular to X behind the piece (camera at +X)."""
    bpy.ops.mesh.primitive_plane_add(size=1.0)
    back = bpy.context.object
    back.name = "RV_back"
    back.scale = (mx.z - mn.z + 3000, mx.y - mn.y + 3000, 1.0)
    back.rotation_euler = (0, math.radians(90), 0)
    back.location = (mn.x - 2200.0, (mn.y + mx.y) / 2, (mn.z + mx.z) / 2)
    mat = bpy.data.materials.new("rv_back")
    mat.diffuse_color = (0.55, 0.62, 0.75, 1.0)
    back.data.materials.append(mat)
    return back


def studio(sc, az):
    sc.display.shading.use_world_space_lighting = True
    sc.display.shading.studiolight_rotate_z = math.radians(az)
    sc.display.light_direction = Matrix.Rotation(math.radians(az), 3, 'Z') @ Vector((-0.42, -0.62, 0.66)).normalized()


def setup_work(sc):
    RK.setup_render(sc)
    sh = sc.display.shading
    sh.show_cavity = True
    sh.cavity_ridge_factor = 1.6
    sh.cavity_valley_factor = 1.8
    sh.shadow_intensity = 0.75
    sh.show_shadows = True


def run_work(meshes, only, out):
    sc = bpy.context.scene
    setup_work(sc)
    cam = RK.make_camera(sc)
    back = None
    for name, subs, az, el, df, gap, lens, opt in VIEWS:
        if only and not any(k in name for k in only):
            continue
        sel = R9.pick(meshes, subs)
        if not sel:
            print("no objects for", name)
            continue
        for o in bpy.data.objects:
            if o.type == 'MESH':
                o.hide_render = (o not in sel)
        R9.lay_out(sel, subs, gap)
        if back is not None:
            bpy.data.objects.remove(back)
            back = None
        mn, mx = RK.world_bbox(sel)
        if opt == "backx":
            back = add_back_x(mn, mx)
        cam.data.lens = lens
        RK.frame(cam, sc, mn, mx, az, el, df)
        studio(sc, az)
        sc.render.filepath = os.path.join(out, outname(name) + ".png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", sc.render.filepath)
    if back is not None:
        bpy.data.objects.remove(back)


def by_short(meshes):
    d = {}
    for o in meshes:
        d[R9.short(o)] = o
    return d


def assemble_lever(meshes, pitch, with_text=True):
    """Copies of the five lever parts placed like BP_DialLever's components (actor space, actor at the origin).  Returns the list of new objects."""
    src = by_short(meshes)
    objs = []

    def put(key, loc, rot_y_deg):
        o = src[key].copy()
        o.data = src[key].data
        o.location = Vector(loc)
        o.rotation_euler = (0.0, math.radians(rot_y_deg), 0.0)
        bpy.context.scene.collection.objects.link(o)
        o.hide_render = False
        objs.append(o)
        return o

    p = math.radians(pitch)
    pivot = Vector((6.0, 0.0, 45.0))
    put("DialLever_Backplate", (0.0, 0.0, 45.0), 0.0)
    put("DialLever_Quadrant", (6.0, 4.0, 45.0), 0.0)                       # D1.26: rail at the handlePivot location + (0, 4, 0); notch stops hidden
    put("DialLever_Arm", tuple(pivot + Vector((22.5 * math.cos(p), 0.0, 22.5 * math.sin(p)))), -(pitch + 90.0))
    put("DialLever_Weight", tuple(pivot + Vector((47.0 * math.cos(p), 0.0, 47.0 * math.sin(p)))), -pitch)
    bpy.ops.mesh.primitive_plane_add(size=1.0)                              # review-only wall behind the board (back plane x -3) so the chain can be seen entering it
    wall = bpy.context.object
    wall.name = "RV_wall"
    wall.scale = (300.0, 300.0, 1.0)
    wall.rotation_euler = (0.0, math.radians(90), 0.0)
    wall.location = (-3.05, 0.0, 60.0)
    wm = bpy.data.materials.get("rv_wall") or bpy.data.materials.new("rv_wall")
    wm.diffuse_color = (0.42, 0.40, 0.38, 1.0)
    wm.use_nodes = True
    bs = next((n for n in wm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bs is not None:
        bs.inputs['Base Color'].default_value = (0.30, 0.28, 0.26, 1.0)
        bs.inputs['Roughness'].default_value = 0.95
    wall.data.materials.append(wm)
    objs.append(wall)
    if with_text:
        cu = bpy.data.curves.new("lbl", 'FONT')
        cu.body = "A"
        cu.size = 12.0
        cu.align_x = 'CENTER'
        cu.align_y = 'CENTER'
        cu.extrude = 0.05
        to = bpy.data.objects.new("lbl", cu)
        bpy.context.scene.collection.objects.link(to)
        to.location = (3.6, 0.0, 82.0)
        to.rotation_euler = (math.radians(90), 0.0, math.radians(90))
        m = bpy.data.materials.get("lbl_mat") or bpy.data.materials.new("lbl_mat")
        m.diffuse_color = (0.85, 0.78, 0.60, 1.0)
        to.data.materials.append(m)
        objs.append(to)
    bpy.context.view_layer.update()
    return objs


def run_lever(meshes, only, out):
    sc = bpy.context.scene
    setup_work(sc)
    cam = RK.make_camera(sc)
    cam.data.lens = 50
    for name, pitch, az, el, df in LEVER_VIEWS:
        if only and not any(k in name for k in only):
            continue
        for o in bpy.data.objects:
            if o.type in ('MESH', 'FONT'):
                o.hide_render = True
        objs = assemble_lever(meshes, pitch)
        for o in objs:
            o.hide_render = False
        mn, mx = RK.world_bbox([o for o in objs if o.type == 'MESH' and o.name != 'RV_wall'])
        RK.frame(cam, sc, mn, mx, az, el, df)
        studio(sc, az)
        sc.render.filepath = os.path.join(out, outname(name) + ".png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", sc.render.filepath)
        for o in objs:
            if o.type == 'FONT':
                bpy.data.objects.remove(o)
            else:
                bpy.data.objects.remove(o)


def colour_materials():
    cols = {"MAT_Iron": ((0.16, 0.16, 0.17), 0.45, 0.85), "MAT_Bronze": ((0.62, 0.40, 0.16), 0.30, 0.95), "MAT_Wood": ((0.30, 0.20, 0.11), 0.80, 0.0),
            "MAT_Paint": ((0.75, 0.72, 0.62), 0.7, 0.0)}
    for m in bpy.data.materials:
        if not m.name.startswith("MAT_"):
            continue
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf is None:
            continue
        c, rough, metal = cols.get(m.name, (tuple(m.diffuse_color)[:3], 0.8, 0.0))
        bsdf.inputs['Base Color'].default_value = (c[0], c[1], c[2], 1.0)
        bsdf.inputs['Roughness'].default_value = rough
        bsdf.inputs['Metallic'].default_value = metal


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
    bg.inputs['Color'].default_value = (0.30, 0.32, 0.36, 1.0)
    bg.inputs['Strength'].default_value = 1.0
    cam = RK.make_camera(sc)
    cam.data.lens = 50
    for name, what, az, el, df in CYCLES_VIEWS:
        if only and not any(k in name for k in only):
            continue
        for o in bpy.data.objects:
            if o.type in ('MESH', 'FONT'):
                o.hide_render = True
        if what == "wheel":
            sel = R9.pick(meshes, ["=BellWheel_A"])
            for o in sel:
                o.location = (0, 0, 0)
                o.hide_render = False
            objs = []
        else:
            objs = assemble_lever(meshes, float(what[5:]), with_text=False)
            sel = [o for o in objs if o.type == 'MESH' and o.name != 'RV_wall']
        bpy.context.view_layer.update()
        mn, mx = RK.world_bbox(sel)
        if name.endswith('chain_top') or name.endswith('chain_top_side'):
            mn, mx = Vector((-6.0, -14.0, 95.0)), Vector((14.0, 14.0, 125.0))
        centre = (mn + mx) * 0.5
        size = max((mx - mn).length, 1.0)
        for l in [o for o in bpy.data.objects if o.type == 'LIGHT']:
            bpy.data.objects.remove(l)
        a, e = math.radians(az), math.radians(el)
        view_dir = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        side = Vector((math.cos(a), math.sin(a), 0.0))
        key = bpy.data.lights.new("key", 'AREA')
        dist_m = size * 0.9 * 0.01
        key.energy = 90000.0 * dist_m * dist_m
        key.size = size * 0.6
        key.color = (1.0, 0.88, 0.74)
        ko = bpy.data.objects.new("key", key)
        sc.collection.objects.link(ko)
        ko.location = centre + view_dir * size * 0.9 + side * size * 0.7 + Vector((0, 0, size * 0.25))
        ko.rotation_euler = (centre - ko.location).to_track_quat('-Z', 'Y').to_euler()
        fill = bpy.data.lights.new("fill", 'AREA')
        fill.energy = 30000.0 * dist_m * dist_m
        fill.size = size * 0.8
        fill.color = (0.6, 0.72, 1.0)
        fo = bpy.data.objects.new("fill", fill)
        sc.collection.objects.link(fo)
        fo.location = centre + view_dir * size * 0.8 - side * size * 0.9 + Vector((0, 0, size * 0.1))
        fo.rotation_euler = (centre - fo.location).to_track_quat('-Z', 'Y').to_euler()
        RK.frame(cam, sc, mn, mx, az, el, df)
        sc.render.filepath = os.path.join(out, outname(name) + ".png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", sc.render.filepath)
        for o in objs:
            bpy.data.objects.remove(o)


def main():
    blend, which, only, out = args()
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=blend)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("UCX_") and o.name.startswith("SM_LB_")]
    if which in ("work", "all"):
        run_work(meshes, only, out)
    if which in ("lever", "all"):
        run_lever(meshes, only, out)
    if which in ("cycles", "all"):
        run_cycles(meshes, only, out)


if __name__ == "__main__":
    main()
