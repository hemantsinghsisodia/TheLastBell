"""render_tower.py -- assembles the P10-3a tower pieces with the D1.1 / D1.2 placement tables (world transforms) and renders review images (Cycles).

    blender.exe -b --factory-startup --python Tools/blender/belltower/render_tower.py -- [--set all|faces|section|flights|belfry|bell] [--only name ...] [--samples 64] [--out Docs/ArtTest/belltower]

Reads SourceArt/BellTower/LB_BellTower.blend (the un-mirrored authoring versions; run build_tower.py first).  Authoring space == Unreal space (a left-handed world), so the
assembly is mirrored in Y (world = diag(1, -1, 1) @ T(loc) @ Rz(yaw)) to show the tower the way it looks in the game.  Output: Docs/ArtTest/belltower/p10_3a_*.png.
Review lighting only (moon-side key light from the SW, sky fill, warm fills inside the belfry); the real lighting is P10-7.
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
BLEND = os.path.join(ROOT, "SourceArt", "BellTower", "LB_BellTower.blend")
OUT = os.path.join(ROOT, "Docs", "ArtTest", "belltower")
PX = "SM_LB_Tw_"

FLIGHT_RISE = 227.27272727272727
FACE_FRAME = {"W": ((12040.0, 1500.0), 90.0), "E": ((12960.0, 2500.0), -90.0), "N": ((12040.0, 2460.0), 0.0), "S": ((12960.0, 1540.0), 180.0)}
STAGE_Z0 = {"S1": 0.0, "S2": 800.0, "S3": 2500.0}
LANCET_X = {"W": (405.0, 595.0), "E": (405.0, 595.0), "N": (365.0, 555.0), "S": (365.0, 555.0)}
RING = {"N": ((12290.0, 2210.0), 0.0), "E": ((12710.0, 2210.0), -90.0), "S": ((12710.0, 1790.0), 180.0), "W": ((12290.0, 1790.0), 90.0)}
FLIGHT_RING = {1: "N", 2: "E", 3: "S", 4: "W", 5: "N", 6: "E", 7: "S", 8: "W", 9: "N", 10: "E", 11: "S"}
FLIGHT_VARIANT = {1: "_Closed", 3: "_BrokenA", 9: "_BrokenA", 6: "_BrokenB"}
LANDING = {"NE": ((12710.0, 2210.0), 0.0), "SE": ((12710.0, 1790.0), -90.0), "SW": ((12290.0, 1790.0), 180.0), "NW": ((12290.0, 2210.0), 90.0)}
LANDING_CORNER = {1: "NE", 2: "SE", 3: "SW", 4: "NW", 5: "NE", 6: "SE", 7: "SW", 8: "NW", 9: "NE", 10: "SE"}
MOON_DIR = Vector((0.6455, 0.4520, -0.6157))          # UE direction the moon light travels (pitch -38, yaw 35)


def args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    o = dict(set="all", only=[], samples=64, out=OUT, res=(1600, 900))
    i = 0
    while i < len(argv):
        if argv[i] == "--set":
            o["set"] = argv[i + 1]
            i += 2
        elif argv[i] == "--samples":
            o["samples"] = int(argv[i + 1])
            i += 2
        elif argv[i] == "--out":
            o["out"] = os.path.abspath(argv[i + 1])
            i += 2
        elif argv[i] == "--res":
            o["res"] = (int(argv[i + 1]), int(argv[i + 2]))
            i += 3
        elif argv[i] == "--only":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                o["only"].append(argv[i])
                i += 1
        else:
            i += 1
    return o


def U(p):
    """Unreal (x, y, z) -> Blender world (the assembly is mirrored in Y)."""
    return Vector((p[0], -p[1], p[2]))


def mat_ue(loc, yaw=0.0):
    return Matrix.Diagonal((1.0, -1.0, 1.0, 1.0)) @ Matrix.Translation(loc) @ Matrix.Rotation(math.radians(yaw), 4, 'Z')


def rot2(v, yaw):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)


# ---------------------------------------------------------------------------------------------- materials
def shade_materials():
    spec = {
        "MAT_Masonry": ((0.25, 0.245, 0.225), 0.92, 0.0, 0.05, 0.22),
        "MAT_Trim": ((0.34, 0.33, 0.30), 0.9, 0.0, 0.05, 0.18),
        "MAT_Rubble": ((0.24, 0.23, 0.21), 0.95, 0.0, 0.08, 0.3),
        "MAT_Wood": ((0.20, 0.13, 0.075), 0.85, 0.0, 0.5, 0.35),
        "MAT_Iron": ((0.07, 0.065, 0.06), 0.55, 0.85, 0.3, 0.2),
        "MAT_Slate": ((0.10, 0.115, 0.14), 0.55, 0.05, 0.25, 0.2),
        "MAT_Bronze": ((0.30, 0.20, 0.09), 0.5, 0.9, 0.2, 0.3),
        "MAT_Rope": ((0.40, 0.31, 0.18), 0.95, 0.0, 0.4, 0.25),
        "MAT_Sally": ((0.34, 0.09, 0.05), 0.95, 0.0, 0.4, 0.3),
    }
    for m in bpy.data.materials:
        if m.name.split(".")[0] not in spec:
            continue
        col, rough, metal, nscale, var = spec[m.name.split(".")[0]]
        m.use_nodes = True
        nt = m.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bs.inputs["Roughness"].default_value = rough
        bs.inputs["Metallic"].default_value = metal
        tc = nt.nodes.new("ShaderNodeTexCoord")
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 0.06 / max(nscale, 0.02) * 0.2
        noise.inputs["Detail"].default_value = 6.0
        nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeMix")
        ramp.data_type = 'RGBA'
        ramp.blend_type = 'MULTIPLY'
        ramp.inputs[0].default_value = 1.0
        ramp.inputs[6].default_value = (col[0], col[1], col[2], 1.0)
        # noise factor -> colour multiplier in [1-var, 1+var]
        mp = nt.nodes.new("ShaderNodeMapRange")
        mp.inputs["From Min"].default_value = 0.3
        mp.inputs["From Max"].default_value = 0.7
        mp.inputs["To Min"].default_value = 1.0 - var
        mp.inputs["To Max"].default_value = 1.0 + var
        nt.links.new(noise.outputs["Fac"], mp.inputs["Value"])
        comb = nt.nodes.new("ShaderNodeCombineColor")
        for k in range(3):
            nt.links.new(mp.outputs["Result"], comb.inputs[k])
        nt.links.new(comb.outputs["Color"], ramp.inputs[7])
        nt.links.new(ramp.outputs["Result"], bs.inputs["Base Color"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.35
        bump.inputs["Distance"].default_value = 1.0
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bs.inputs["Normal"])
        nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])


# ---------------------------------------------------------------------------------------------- assembly
class Assembly:
    def __init__(self):
        self.src = {o.name: o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("SM_LB_")}
        self.items = []                                 # (tag, object)
        self.col = bpy.data.collections.new("TowerAssembly")
        bpy.context.scene.collection.children.link(self.col)
        for o in self.src.values():
            o.hide_render = True
            o.hide_viewport = True
        for o in [o for o in bpy.data.objects if o.name.startswith("UCX_")]:
            o.hide_render = True

    def add(self, tag, name, loc, yaw=0.0):
        s = self.src[name]
        o = bpy.data.objects.new(tag, s.data)
        o.matrix_world = mat_ue(loc, yaw)
        o.parent = None
        self.col.objects.link(o)
        self.items.append((tag, o))
        return o

    def objs(self, pred):
        return [o for t, o in self.items if pred(t)]


def build_assembly():
    A = Assembly()
    # ground (a plain slab so the base of the tower has something to stand on)
    me = bpy.data.meshes.new("ground")
    import bmesh
    b = bmesh.new()
    bmesh.ops.create_cube(b, size=1.0)
    for v in b.verts:
        v.co = (11000.0 + (v.co.x + 0.5) * 4000.0, -(1000.0 + (v.co.y + 0.5) * 2000.0), -40.0 + (v.co.z + 0.5) * 40.0)
    b.to_mesh(me)
    b.free()
    g = bpy.data.objects.new("ground", me)
    mg = bpy.data.materials.get("MAT_Rubble")
    me.materials.append(mg)
    A.col.objects.link(g)
    A.items.append(("ground", g))
    # walls
    for stage in ("S1", "S2", "S3"):
        for face in ("W", "N", "E", "S"):
            (ox, oy), yaw = FACE_FRAME[face]
            nm = PX + "%s_%s" % (stage, face)
            if stage == "S3" and face in ("W", "S"):
                nm += "_BrokenSW"
            A.add("wall:%s:%s" % (stage, face), nm, (ox, oy, STAGE_Z0[stage]), yaw)
    for face in ("W", "N", "E", "S"):
        (ox, oy), yaw = FACE_FRAME[face]
        for k, xc in enumerate(LANCET_X[face]):
            loc2 = rot2((xc, 0.0), yaw)
            broken = (face == "N" and xc == 365.0) or (face == "E" and xc == 595.0)
            A.add("louvre:%s:%d" % (face, k), PX + "Louvre_130x450" + ("_Broken" if broken else ""), (ox + loc2[0], oy + loc2[1], 2700.0), yaw)
    A.add("roof", PX + "Roof_BrokenSW", (12500.0, 2000.0, 3540.0))
    # stairs
    for k in range(1, 12):
        ring = FLIGHT_RING[k]
        (ox, oy), yaw = RING[ring]
        z = (k - 1) * FLIGHT_RISE
        A.add("flight:%d" % k, PX + "StairFlight_250x420" + FLIGHT_VARIANT.get(k, ""), (ox, oy, z), yaw)
        A.add("rail:%d" % k, PX + "FlightRail_420", (ox, oy, z), yaw)
    for k in range(1, 11):
        (ox, oy), yaw = LANDING[LANDING_CORNER[k]]
        A.add("landing:%d" % k, PX + "Landing_250", (ox, oy, k * FLIGHT_RISE), yaw)
    A.add("base", PX + "ShaftBase_420x420x450", (12500.0, 2000.0, 0.0))
    for nm, (x, y) in (("SW", (12290.0, 1790.0)), ("SE", (12710.0, 1790.0)), ("NE", (12710.0, 2210.0)), ("NW", (12290.0, 2210.0))):
        A.add("post:" + nm, PX + "ShaftPost_20x20x2015", (x, y, 450.0))
    A.add("floor", PX + "BelfryFloor", (12040.0, 1540.0, 2500.0))
    A.add("toprail:670", PX + "TopRail_670", (12700.0, 1790.0, 2500.0), 90.0)
    A.add("toprail:420", PX + "TopRail_420", (12290.0, 1800.0, 2500.0), 0.0)
    A.add("partition", PX + "Partition_250x455", (12290.0, 1790.0, 0.0), -90.0)
    A.add("frame", PX + "BellFrame_A", (12420.0, 2000.0, 2500.0))
    A.add("head", PX + "BellHeadstock_A", (12420.0, 2000.0, 2880.0))
    A.add("bell", "SM_LB_Prop_GreatBell_A", (12420.0, 2000.0, 2860.0))
    A.add("rope", "SM_LB_Prop_BellRope_2610", (12550.0, 1830.0, 2750.0))
    bpy.context.view_layer.update()
    return A


# ---------------------------------------------------------------------------------------------- lighting / camera
def setup_world(sc, sky=(0.20, 0.25, 0.36), strength=0.9):
    w = sc.world or bpy.data.worlds.new("W")
    sc.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs["Color"].default_value = (sky[0], sky[1], sky[2], 1.0)
    bg.inputs["Strength"].default_value = strength


def clear_lights():
    for o in [o for o in bpy.data.objects if o.type == 'LIGHT']:
        bpy.data.objects.remove(o)


def add_sun(strength=3.2, colour=(0.82, 0.88, 1.0), angle=2.0, direction=MOON_DIR):
    d = bpy.data.lights.new("moon", 'SUN')
    d.energy = strength
    d.color = colour
    d.angle = math.radians(angle)
    o = bpy.data.objects.new("moon", d)
    bpy.context.scene.collection.objects.link(o)
    v = Vector((direction.x, -direction.y, direction.z))
    o.rotation_euler = v.to_track_quat('-Z', 'Y').to_euler()
    return o


def add_point(loc, watt, colour=(1.0, 0.68, 0.38), radius=12.0):
    d = bpy.data.lights.new("fill", 'POINT')
    d.energy = watt
    d.color = colour
    d.shadow_soft_size = radius
    o = bpy.data.objects.new("fill", d)
    o.location = U(loc)
    bpy.context.scene.collection.objects.link(o)
    return o


def add_area(loc, target, watt, size, colour=(1.0, 0.85, 0.7)):
    d = bpy.data.lights.new("area", 'AREA')
    d.energy = watt
    d.size = size
    d.color = colour
    o = bpy.data.objects.new("area", d)
    o.location = U(loc)
    o.rotation_euler = (U(target) - U(loc)).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.collection.objects.link(o)
    return o


def make_cam(sc, loc, target, lens=35.0, clip=(5.0, 200000.0), shift_y=0.0):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cd.clip_start, cd.clip_end = clip
    cd.shift_y = shift_y
    co = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(co)
    co.location = U(loc)
    co.rotation_euler = (U(target) - U(loc)).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = co
    return co


def render(sc, path):
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDERED", path)


def setup_cycles(sc, samples, res):
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    try:
        pr = bpy.context.preferences.addons['cycles'].preferences
        for dt in ('OPTIX', 'CUDA', 'HIP'):
            try:
                pr.compute_device_type = dt
                pr.get_devices()
                if any(d.type == dt for d in pr.devices):
                    for d in pr.devices:
                        d.use = (d.type == dt)
                    sc.cycles.device = 'GPU'
                    break
            except Exception:
                continue
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = 'PNG'
    try:
        sc.view_settings.view_transform = 'AgX'
    except Exception:
        pass
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass


def show(A, pred):
    for t, o in A.items:
        o.hide_render = not pred(t)
        o.hide_viewport = o.hide_render


# ---------------------------------------------------------------------------------------------- views
CX, CY = 12500.0, 2000.0


def exterior_view(A, sc, name, cam_loc, target, lens=28.0, pred=None, out=OUT):
    clear_lights()
    setup_world(sc, (0.26, 0.32, 0.46), 0.38)
    add_sun(3.2, direction=Vector((0.72, 0.30, -0.50)))
    show(A, pred or (lambda t: True))
    make_cam(sc, cam_loc, target, lens)
    render(sc, os.path.join(out, name))
    bpy.data.objects.remove(sc.camera)


def run_faces(A, sc, only, out):
    # outside views of each face at the gate-like angle (low, slightly below the plinth line, off-axis), plus the SW overview
    views = [
        ("p10_3a_tower_W.png", (CX - 6200.0, CY - 2800.0, 250.0), (CX, CY, 2250.0), 28.0),
        ("p10_3a_tower_N.png", (CX - 2800.0, CY + 6200.0, 250.0), (CX, CY, 2250.0), 28.0),
        ("p10_3a_tower_E.png", (CX + 6200.0, CY + 2800.0, 250.0), (CX, CY, 2250.0), 28.0),
        ("p10_3a_tower_S.png", (CX + 2800.0, CY - 6200.0, 250.0), (CX, CY, 2250.0), 28.0),
        ("p10_3a_tower_SW_overview.png", (CX - 4900.0, CY - 4900.0, 250.0), (CX, CY, 2250.0), 28.0),
        ("p10_3a_tower_SW_belfry.png", (CX - 2300.0, CY - 2300.0, 1900.0), (CX - 150.0, CY - 150.0, 3500.0), 30.0),
    ]
    for nm, cam, tgt, lens in views:
        if only and not any(k in nm for k in only):
            continue
        exterior_view(A, sc, nm, cam, tgt, lens, out=out)


def run_section(A, sc, only, out):
    """Cutaway of the stair core: the S and W walls removed, flights F01-F05 + landings + rails + shaft base + shaft posts, N and E walls kept."""
    if only and not any(k in "p10_3a_stair_core_section" for k in only):
        return
    clear_lights()
    setup_world(sc, (0.30, 0.34, 0.46), 0.8)
    add_sun(2.2)
    add_area((CX - 1800.0, CY - 1800.0, 2400.0), (CX, CY, 600.0), 2.2e6, 900.0, (1.0, 0.9, 0.8))

    def pred(t):
        if t == "ground":
            return True
        if t.startswith(("wall:S1:N", "wall:S1:E", "wall:S2:N", "wall:S2:E")):
            return True
        if t.startswith(("flight:", "rail:")):
            return int(t.split(":")[1]) <= 7
        if t.startswith("landing:"):
            return int(t.split(":")[1]) <= 7
        if t == "base" or t == "partition":
            return True
        if t.startswith("post:"):
            return True
        return False
    show(A, pred)
    # trim the posts visually at the section height: hide nothing, but frame the camera on z 0..1300
    make_cam(sc, (CX - 1900.0, CY - 2100.0, 1500.0), (CX + 30.0, CY, 900.0), 26.0)
    render(sc, os.path.join(out, "p10_3a_stair_core_section.png"))
    bpy.data.objects.remove(sc.camera)
    make_cam(sc, (CX - 1200.0, CY - 700.0, 700.0), (CX + 160.0, CY + 150.0, 470.0), 24.0)
    render(sc, os.path.join(out, "p10_3a_stair_core_section_close.png"))
    bpy.data.objects.remove(sc.camera)
    # looking up the shaft from the shaft base (rails, posts, landings above)
    clear_lights()
    setup_world(sc, (0.30, 0.36, 0.52), 1.6)
    add_area((CX + 100.0, CY, 470.0), (CX + 20.0, CY + 20.0, 1800.0), 3.0e6, 400.0, (1.0, 0.82, 0.62))
    add_sun(2.0)
    show(A, lambda t: t.startswith(("flight:", "rail:", "landing:", "post:", "wall:S1:N", "wall:S1:E", "wall:S1:S", "wall:S2")) or t in ("ground", "base"))
    make_cam(sc, (CX - 120.0, CY - 120.0, 460.0), (CX + 150.0, CY + 130.0, 1900.0), 20.0)
    render(sc, os.path.join(out, "p10_3a_stair_core_up.png"))
    bpy.data.objects.remove(sc.camera)


STUDIO = (20000.0, 0.0)


def run_flights(A, sc, only, out):
    """One close-up per flight variant, each in the same studio frame (flight frame = world, yaw 0) in front of a wall backdrop."""
    sx, sy = STUDIO
    variants = (("flight_base", "", True), ("flight_closed", "_Closed", False), ("flight_brokenA", "_BrokenA", False), ("flight_brokenB", "_BrokenB", False))
    for nm, var, with_rail in variants:
        fn = "p10_3a_%s.png" % nm
        if only and not any(o in fn for o in only):
            continue
        objs = [A.add("studio:flight", PX + "StairFlight_250x420" + var, (sx, sy, 0.0)),
                A.add("studio:wall", PX + "S1_N", (sx - 300.0, sy + 250.0, 0.0)),
                A.add("studio:floor", "SM_LB_Tw_Landing_250", (sx - 250.0, sy, 0.0))]
        objs[2].hide_render = True
        if with_rail:
            objs.append(A.add("studio:rail", PX + "FlightRail_420", (sx, sy, 0.0)))
        clear_lights()
        setup_world(sc, (0.26, 0.31, 0.44), 0.7)
        add_sun(2.6)
        add_area((sx - 300.0, sy - 500.0, 520.0), (sx + 200.0, sy + 120.0, 120.0), 1.6e6, 450.0, (1.0, 0.9, 0.78))
        show(A, lambda t: t.startswith("studio") or t == "ground")
        objs[2].hide_render = True
        # the ground slab of the assembly sits far away: a studio floor
        fl = A.add("studio:ground", "SM_LB_Tw_ShaftBase_420x420x450", (0, 0, 0))
        fl.hide_render = True
        for o in A.objs(lambda t: t == "ground"):
            o.hide_render = True
        gm = bpy.data.meshes.new("sgrd")
        import bmesh
        bb = bmesh.new()
        bmesh.ops.create_cube(bb, size=1.0)
        for v in bb.verts:
            v.co = (sx - 900.0 + (v.co.x + 0.5) * 2200.0, -(sy - 700.0 + (v.co.y + 0.5) * 1000.0), -20.0 + (v.co.z + 0.5) * 20.0)
        bb.to_mesh(gm)
        bb.free()
        gm.materials.append(bpy.data.materials.get("MAT_Rubble"))
        go = bpy.data.objects.new("sgrd", gm)
        sc.collection.objects.link(go)
        cam = {"_BrokenA": (sx - 250.0, sy - 250.0, 290.0), "_BrokenB": (sx - 330.0, sy - 270.0, 240.0)}.get(var, (sx - 520.0, sy - 330.0, 330.0))
        tgt = {"_BrokenA": (sx + 190.0, sy + 175.0, 100.0), "_BrokenB": (sx + 130.0, sy + 175.0, 60.0)}.get(var, (sx + 205.0, sy + 125.0, 105.0))
        make_cam(sc, cam, tgt, 32.0)
        render(sc, os.path.join(out, fn))
        bpy.data.objects.remove(sc.camera)
        bpy.data.objects.remove(go)
        for o in objs + [fl]:
            A.items = [(t, x) for t, x in A.items if x is not o]
            bpy.data.objects.remove(o)


def belfry_lights(include_moon=True):
    clear_lights()
    setup_world(sc_global, (0.16, 0.20, 0.30), 0.7)
    if include_moon:
        add_sun(3.4)
    add_point((12150.0, 1800.0, 2800.0), 600000.0, (1.0, 0.72, 0.45), 14.0)         # lantern-ish warm fill on the stair arrival
    add_point((12640.0, 2300.0, 2900.0), 500000.0, (1.0, 0.72, 0.45), 14.0)
    add_area((12420.0, 2000.0, 3350.0), (12420.0, 2000.0, 2600.0), 1.2e6, 500.0, (0.6, 0.7, 1.0))


sc_global = None


def run_belfry(A, sc, only, out):
    global sc_global
    sc_global = sc
    views = [
        ("p10_3a_belfry_interior_SW.png", (12880.0, 2420.0, 2850.0), (12290.0, 1840.0, 3050.0), 20.0),
        ("p10_3a_belfry_interior_bell.png", (12165.0, 1960.0, 2670.0), (12430.0, 2000.0, 2740.0), 22.0),
        ("p10_3a_belfry_interior_rope.png", (12600.0, 1700.0, 2660.0), (12545.0, 1835.0, 2480.0), 24.0),
        ("p10_3a_belfry_interior_up.png", (12420.0, 2250.0, 2520.0), (12320.0, 1800.0, 3560.0), 20.0),
    ]
    belfry_vis = lambda t: t.startswith(("wall:S3", "louvre", "roof", "floor", "toprail", "frame", "head", "bell", "rope", "flight:11", "landing:10", "post")) or t in ("ground",)
    for nm, cam, tgt, lens in views:
        if only and not any(o in nm for o in only):
            continue
        belfry_lights(True)
        show(A, belfry_vis)
        make_cam(sc, cam, tgt, lens)
        render(sc, os.path.join(out, nm))
        bpy.data.objects.remove(sc.camera)
    # the rope through the floor and down the shaft: from the shaft base looking up the rope
    nm = "p10_3a_rope_shaft.png"
    if not only or any(o in nm for o in only):
        clear_lights()
        setup_world(sc, (0.16, 0.20, 0.30), 0.8)
        add_area((12500.0, 1930.0, 520.0), (12550.0, 1830.0, 1500.0), 2.0e6, 300.0, (1.0, 0.8, 0.6))
        add_point((12540.0, 1900.0, 2650.0), 600000.0, (1.0, 0.72, 0.45), 14.0)
        add_sun(3.0)
        show(A, lambda t: t.startswith(("base", "post", "rope", "floor", "bell", "frame", "head")) or t in ("ground",))
        make_cam(sc, (12430.0, 2050.0, 470.0), (12550.0, 1830.0, 1400.0), 18.0)
        render(sc, os.path.join(out, nm))
        bpy.data.objects.remove(sc.camera)


def run_bell(A, sc, only, out):
    views = [
        ("p10_3a_great_bell_crack.png", (12420.0 - 520.0, 2000.0 + 40.0, 2780.0), (12420.0 - 95.0, 2000.0, 2735.0), 40.0, "crack"),
        ("p10_3a_great_bell_frame.png", (12420.0 - 700.0, 2000.0 - 650.0, 2640.0), (12420.0, 2000.0, 2720.0), 30.0, "frame"),
    ]
    for nm, cam, tgt, lens, what in views:
        if only and not any(o in nm for o in only):
            continue
        clear_lights()
        setup_world(sc, (0.22, 0.26, 0.36), 0.8)
        add_sun(2.4, direction=Vector((0.8, 0.2, -0.5)))
        add_area((cam[0] - 150.0, cam[1] - 300.0, cam[2] + 250.0), tgt, 1.2e6, 350.0, (1.0, 0.88, 0.75))
        if what == "crack":
            show(A, lambda t: t in ("bell",))
        else:
            show(A, lambda t: t in ("bell", "frame", "head", "rope", "floor", "ground"))
        make_cam(sc, cam, tgt, lens)
        render(sc, os.path.join(out, nm))
        bpy.data.objects.remove(sc.camera)


def main():
    o = args()
    os.makedirs(o["out"], exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    sc = bpy.context.scene
    setup_cycles(sc, o["samples"], o["res"])
    shade_materials()
    A = build_assembly()
    w = o["set"]
    if w in ("faces", "all"):
        run_faces(A, sc, o["only"], o["out"])
    if w in ("section", "all"):
        run_section(A, sc, o["only"], o["out"])
    if w in ("flights", "all"):
        run_flights(A, sc, o["only"], o["out"])
    if w in ("belfry", "all"):
        run_belfry(A, sc, o["only"], o["out"])
    if w in ("bell", "all"):
        run_bell(A, sc, o["only"], o["out"])


if __name__ == "__main__":
    main()
