"""render_cloister.py -- P10-3b review renders (Cycles) of the assembled cloister, placed with the D1.3 / D1.6 world transforms.

    blender.exe -b --factory-startup --python Tools/blender/belltower/render_cloister.py -- [--set corner_in corner_garth collapse archway garth cell stairhouse bells|all]
                                                                                           [--quick] [--samples N] [--out Docs/ArtTest/belltower]

Opens SourceArt/Cloister/LB_Cloister.blend (authoring space == Unreal space numerically; the authoring space is the Y-mirror of Unreal's, so renders show the mirror image
of what Unreal shows), instances every piece with the D1 transform and renders p10_3b_*.png.  Render-only dressing (stand-in floors, door leaves, rubble, grass, text,
lights) is created here and is not part of the deliverable meshes.
"""
import math
import os
import random
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "Tools", "blender", "kit"))
import kit_lib as K  # noqa: E402

BLEND = os.path.join(REPO, "SourceArt", "Cloister", "LB_Cloister.blend")
OUT = os.path.join(REPO, "Docs", "ArtTest", "belltower")
PC = "SM_LB_Cl_"
PR = "SM_LB_Prop_"


# ----------------------------------------------------------------------------------------------
# args
# ----------------------------------------------------------------------------------------------
PROBE = False
ONLY = []


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sets, quick, samples, out = [], False, None, OUT
    global PROBE
    i = 0
    while i < len(argv):
        if argv[i] == "--set":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                sets.append(argv[i])
                i += 1
        elif argv[i] == "--only":                    # P10-8d: substring filter on the image name
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                ONLY.append(argv[i])
                i += 1
        elif argv[i] == "--quick":
            quick = True
            i += 1
        elif argv[i] == "--probe":                  # after each view, re-render with the roofs magenta and count the magenta pixels (roof visible through the vault?)
            PROBE = True
            i += 1
        elif argv[i] == "--samples":
            samples = int(argv[i + 1])
            i += 2
        elif argv[i] == "--out":
            out = os.path.abspath(argv[i + 1])
            i += 2
        else:
            i += 1
    return sets or ["all"], quick, samples, out


# ----------------------------------------------------------------------------------------------
# materials (procedural, so the slot colours read as stone / slate / wood in Cycles)
# ----------------------------------------------------------------------------------------------
def _clear(m):
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bs.outputs['BSDF'], out.inputs['Surface'])
    return nt, bs


def _noise_ramp(nt, scale, c0, c1, detail=6.0, seed=0.0, obj=True):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs['Location'].default_value = (seed, seed * 0.7, seed * 1.3)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs['Scale'].default_value = scale
    nz.inputs['Detail'].default_value = detail
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.35
    cr.color_ramp.elements[0].color = c0
    cr.color_ramp.elements[1].position = 0.7
    cr.color_ramp.elements[1].color = c1
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], nz.inputs['Vector'])
    nt.links.new(nz.outputs['Fac'], cr.inputs['Fac'])
    return cr, nz, mp


def _bump(nt, bs, mp, scale, strength):
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs['Scale'].default_value = scale
    nz.inputs['Detail'].default_value = 8.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs['Strength'].default_value = strength
    bp.inputs['Distance'].default_value = 0.2
    nt.links.new(mp.outputs['Vector'], nz.inputs['Vector'])
    nt.links.new(nz.outputs['Fac'], bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], bs.inputs['Normal'])


def mk_stone(name, c0, c1, rough=0.9, scale=0.012, bump=0.45):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, bs = _clear(m)
    cr, nz, mp = _noise_ramp(nt, scale * 40, c0, c1, seed=2.0)
    nt.links.new(cr.outputs['Color'], bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = rough
    _bump(nt, bs, mp, scale * 400, bump)
    return m


def setup_materials():
    mk_stone("MAT_Masonry", (0.05, 0.05, 0.048, 1), (0.135, 0.13, 0.12, 1), 0.92, 0.02, 0.5)
    mk_stone("MAT_Trim", (0.09, 0.088, 0.082, 1), (0.21, 0.2, 0.18, 1), 0.88, 0.03, 0.35)
    mk_stone("MAT_Rubble", (0.045, 0.043, 0.04, 1), (0.13, 0.12, 0.105, 1), 0.95, 0.05, 0.7)
    mk_stone("MAT_Slate", (0.025, 0.028, 0.034, 1), (0.075, 0.082, 0.095, 1), 0.55, 0.03, 0.25)
    mk_stone("MAT_Wood", (0.05, 0.032, 0.018, 1), (0.16, 0.10, 0.055, 1), 0.85, 0.01, 0.3)
    mk_stone("MAT_Earth", (0.018, 0.012, 0.008, 1), (0.06, 0.042, 0.026, 1), 1.0, 0.03, 0.8)
    m = mk_stone("MAT_Iron", (0.02, 0.02, 0.022, 1), (0.07, 0.07, 0.075, 1), 0.5, 0.05, 0.2)
    m.node_tree.nodes[[n.type for n in m.node_tree.nodes].index('BSDF_PRINCIPLED')].inputs['Metallic'].default_value = 0.85
    # bronze with verdigris
    b = bpy.data.materials.get("MAT_Bronze") or bpy.data.materials.new("MAT_Bronze")
    nt, bs = _clear(b)
    cr, nz, mp = _noise_ramp(nt, 14.0 * 3, (0.16, 0.09, 0.04, 1), (0.05, 0.16, 0.12, 1), seed=5.0)
    nt.links.new(cr.outputs['Color'], bs.inputs['Base Color'])
    bs.inputs['Metallic'].default_value = 0.85
    bs.inputs['Roughness'].default_value = 0.42
    _bump(nt, bs, mp, 90.0, 0.15)
    band = bpy.data.materials.get("MAT_Band") or bpy.data.materials.new("MAT_Band")
    nt, bs = _clear(band)
    bs.inputs['Base Color'].default_value = (0.32, 0.07, 0.05, 1)
    bs.inputs['Roughness'].default_value = 0.8


def flat_mat(name, col, rough=0.8, metal=0.0, emission=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, bs = _clear(m)
    bs.inputs['Base Color'].default_value = col
    bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = metal
    if emission:
        bs.inputs['Emission Color'].default_value = emission
        bs.inputs['Emission Strength'].default_value = 4.0
    return m


# ----------------------------------------------------------------------------------------------
# placement helpers
# ----------------------------------------------------------------------------------------------
SRC = {}
PLACED = []


VALLEY_BLEND = os.path.join(REPO, "SourceArt", "Cloister", "LB_Cloister_valley.blend")


def append_valley_pieces():
    """The C14V pieces live in LB_Cloister_valley.blend until a full rebuild merges them into LB_Cloister.blend: append them (and bind them to the existing MAT_ datablocks)."""
    names = ["SM_LB_Cl_LeanTo_Valley_L_1000x1050", "SM_LB_Cl_LeanTo_Valley_R_1000x1050"]
    if all(n in bpy.data.objects for n in names) or not os.path.exists(VALLEY_BLEND):
        return
    with bpy.data.libraries.load(VALLEY_BLEND, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in names]
    for o in dst.objects:
        for i, m in enumerate(o.data.materials):
            base = bpy.data.materials.get(m.name.split(".")[0])
            if base is not None and base is not m:
                o.data.materials[i] = base


def collect_sources():
    append_valley_pieces()
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name.startswith("SM_LB_") and not o.name.startswith("UCX_"):
            SRC[o.name] = o
            o.hide_render = True
            o.hide_viewport = True
        elif o.name.startswith("UCX_"):
            o.hide_render = True


def rz(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'Z')


def basis4(ex, ey, ez):
    ex, ey, ez = Vector(ex).normalized(), Vector(ey).normalized(), Vector(ez).normalized()
    m = Matrix.Identity(4)
    for i in range(3):
        m[i][0], m[i][1], m[i][2] = ex[i], ey[i], ez[i]
    return m


def place(name, loc, yaw=0.0, scale=(1.0, 1.0, 1.0), rot=None, group="x", roll=0.0, pitch=0.0):
    src = SRC[name if name.startswith("SM_LB_") else PC + name]
    o = src.copy()
    o.data = src.data
    o.hide_render = False
    o.hide_viewport = False
    R = rot if rot is not None else (rz(yaw) @ Matrix.Rotation(math.radians(pitch), 4, 'Y') @ Matrix.Rotation(math.radians(roll), 4, 'X'))
    S = Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0))
    o.matrix_world = Matrix.Translation(Vector(loc)) @ R @ S
    bpy.context.scene.collection.objects.link(o)
    o["grp"] = group
    PLACED.append(o)
    return o


def new_mesh_obj(name, bm, mats, loc=(0, 0, 0), grp="dress"):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    o.location = loc
    bpy.context.scene.collection.objects.link(o)
    o["grp"] = grp
    PLACED.append(o)
    return o


def box_obj(name, x0, x1, y0, y1, z0, z1, mat, grp="floor"):
    b = K.box(x0, x1, y0, y1, z0, z1, 0, 0.0)
    return new_mesh_obj(name, b, [mat], grp=grp)


# ----------------------------------------------------------------------------------------------
# D1.3 assembly
# ----------------------------------------------------------------------------------------------
def wall_run(kind, face, a0, a1, height, groupname):
    """Wall run in a face frame (S/N/W/E), n = round(L/400) 400-pieces scaled in X, alternating A/B; a 100-piece only when L < 300."""
    L = a1 - a0
    suffix = {1300: "Wall40_%sx1300", 800: "Wall40_%sx800", 450: "Wall40_%sx450"}[height]
    if L < 300:
        n, pl = max(1, round(L / 100.0)), [suffix % "100"]
        unit = 100.0
    else:
        n = round(L / 400.0)
        pl = [(suffix % "400") + ("_A" if height != 450 else ""), (suffix % "400") + ("_B" if height != 450 else "")]
        unit = 400.0
    sx = L / (unit * n)
    for i in range(n):
        nm = pl[i % len(pl)]
        t = a0 + i * L / n          # start of piece i along the run (in +axis)
        if kind == 'S':             # local x runs -X from the end
            place(nm, (a1 - i * L / n, face, 0), 180, (sx, 1, 1), group=groupname)
        elif kind == 'N':
            place(nm, (t, face, 0), 0, (sx, 1, 1), group=groupname)
        elif kind == 'W':
            place(nm, (face, t, 0), 90, (sx, 1, 1), group=groupname)
        else:                       # E: runs -Y from the end
            place(nm, (face, a1 - i * L / n, 0), -90, (sx, 1, 1), group=groupname)


def build_cloister_walls():
    wall_run('S', 540, 9460, 10500, 1300, "walls")
    wall_run('S', 540, 10800, 12040, 1300, "walls")
    wall_run('N', 3000, 9460, 12040, 1300, "walls")
    wall_run('W', 9500, 540, 1750, 1300, "walls")
    place("Archway_500x40x1300", (9500, 1750, 0), 90, group="walls")
    wall_run('W', 9500, 2250, 3000, 1300, "walls")
    wall_run('E', 12000, 540, 1500, 1300, "walls")
    wall_run('E', 12000, 2500, 3000, 1300, "walls")
    place("Archway_300x40x1300", (10800, 540, 0), 180, group="walls")


def build_passage():
    wall_run('S', 1700, 6040, 9460, 800, "passage")
    wall_run('N', 2300, 6040, 9460, 800, "passage")


def build_stair_house():
    wall_run('W', 10500, -100, 500, 450, "stairhouse")
    wall_run('E', 10800, -100, 500, 450, "stairhouse")
    place("StairHouseGable_380x40x650", (10840, -100, 0), 180, group="stairhouse")
    place("StairHouseRoof_420x640", (10440, -140, 450), 0, group="stairhouse")


def build_arcade():
    for (x, y) in ((10600, 1350), (10900, 1350), (11200, 1350), (10600, 2250), (10900, 2250), (11200, 2250), (10250, 1700), (10250, 2000), (11450, 1700), (11450, 2000)):
        place("Pier_80x80x640", (x, y, 0), 0, group="arcade")
    for (x, y) in ((10275, 1350), (11425, 1350), (10275, 2250), (11425, 2250)):
        place("PierCorner_130x80x640", (x, y, 0), 0, group="arcade")
    for y in (1350, 2250):
        for (x, sp) in ((10340, 220), (10640, 220), (10940, 220), (11240, 120)):
            place("ArcadeArch_%dx80" % sp, (x, y, 330), 0, group="arcade")
    for x in (10250, 11450):
        for (y, sp) in ((1390, 270), (1740, 220), (2040, 170)):
            place("ArcadeArch_%dx80" % sp, (x, y, 330), 90, group="arcade")


def build_garth():
    place("GarthWall_1100x100", (10300, 1400, 0), 0, group="garth")
    place("GarthWall_1100x100", (11400, 2200, 0), 180, group="garth")
    place("GarthWall_800x100", (10300, 2200, 0), -90, group="garth")
    place("GarthWall_800x100", (11400, 1400, 0), 90, group="garth")
    place("GarthBed_1100x800", (10300, 1400, 100), 0, group="garth")
    rng = random.Random(1223)
    for (x, y) in ((10500, 1600), (10500, 2000), (10700, 1650), (11000, 2000), (11200, 1600), (11200, 1950)):
        place("GraveSlab_200x80", (x, y, 98.5), rng.uniform(-4, 4), roll=rng.uniform(1, 3), pitch=rng.uniform(-1, 1), group="garth")
    for (x, y) in ((10450, 1500), (11250, 1500), (10450, 2100), (11250, 2100)):
        place("GraveCross_60", (x, y, 99), rng.uniform(-30, 30), roll=rng.uniform(-6, 6), group="garth")
    place("GarthCross_350", (10850, 1800, 100), 15, group="garth")


def build_vaults():
    Z = 560
    place("Vault_Barrel_830x640", (10210, 510, Z), group="vault")
    place("Vault_Barrel_830x640", (10850, 510, Z), group="vault")
    place("Vault_Barrel_770x640", (10210, 2260, Z), group="vault")
    place("Vault_Barrel_770x640_Broken", (10850, 2260, Z), group="vault")
    place("Vault_Barrel_770x980", (10240, 1310, Z), 90, group="vault")
    place("Vault_Barrel_570x980", (12030, 1310, Z), 90, group="vault")
    place("Vault_Groin_770x830", (9470, 510, Z), group="vault")
    place("Vault_Groin_570x830", (11460, 510, Z), group="vault")
    place("Vault_Groin_770x770", (9470, 2260, Z), group="vault")
    place("Vault_Groin_570x770", (11460, 2260, Z), group="vault")


def roof_panel(name, origin, ex, slope_dir, sx, sy):
    ex = Vector(ex).normalized()
    ey = Vector(slope_dir).normalized()
    ez = ex.cross(ey)
    assert ez.z > 0, "roof panel normal must point up"
    return place(name, origin, rot=basis4(ex, ey, ez), scale=(sx, sy, 1.0), group="roof")


# D1.14 roof layout (valley roofs, D-082): 13 records, (label, mesh, walk, offset along the run, width).  x-scale = width / 1000, y-scale = slope length / 1050 per walk.
ROOF_WALKS = {   # walk: (run start a, run axis, eaves line coordinate, run direction (local x), slope direction (local y, up the slope))
    'S': (12000.0, 'x', 1420.0, (-1, 0, 0), (0, -880, 560)),
    'N': (9500.0, 'x', 2180.0, (1, 0, 0), (0, 820, 560)),
    'W': (540.0, 'y', 10320.0, (0, 1, 0), (-820, 0, 560)),
    'E': (3000.0, 'y', 11380.0, (0, -1, 0), (620, 0, 560)),
}
ROOF_RECORDS = [
    ("CLA_Roof_S_0", "LeanTo_Valley_L_1000x1050", 'S', 0, 620), ("CLA_Roof_S_1", "LeanTo_1000x1050", 'S', 620, 1060), ("CLA_Roof_S_2", "LeanTo_Valley_R_1000x1050", 'S', 1680, 820),
    ("CLA_Roof_N_0", "LeanTo_Valley_L_1000x1050", 'N', 0, 820), ("CLA_Roof_N_1", "LeanTo_1000x1050", 'N', 820, 440), ("CLA_Roof_N_2", "LeanTo_1000x1050_Hole", 'N', 1260, 620),
    ("CLA_Roof_N_3", "LeanTo_Valley_R_1000x1050", 'N', 1880, 620),
    ("CLA_Roof_W_0", "LeanTo_Valley_L_1000x1050", 'W', 0, 880), ("CLA_Roof_W_1", "LeanTo_1000x1050", 'W', 880, 760), ("CLA_Roof_W_2", "LeanTo_Valley_R_1000x1050", 'W', 1640, 820),
    ("CLA_Roof_E_0", "LeanTo_Valley_L_1000x1050", 'E', 0, 820), ("CLA_Roof_E_1", "LeanTo_1000x1050", 'E', 820, 760), ("CLA_Roof_E_2", "LeanTo_Valley_R_1000x1050", 'E', 1580, 880),
]
ROOF_OBJ = {}     # label -> placed object


def roof_origin(walk, off):
    a, axis, line, ex, _d = ROOF_WALKS[walk]
    if axis == 'x':
        return (a + ex[0] * off, line, 640.0)
    return (line, a + ex[1] * off, 640.0)


def build_roofs(aligned_hole=True):
    """Lean-to roofs, D1.14 layout: 13 records, valley triangles over the corner squares.  Eaves Z 640 -> top line Z 1200.  Frames: S x -X from X 12000, N x +X from 9500,
    W x +Y from 540, E x -Y from 3000 (the rotator that keeps the panel normal up)."""
    for (label, mesh, walk, off, width) in ROOF_RECORDS:
        _a, _axis, _line, ex, d = ROOF_WALKS[walk]
        ln = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2)          # slope length Ls: S 1043.07, N/W 992.97, E 835.46
        o = roof_panel(mesh, roof_origin(walk, off), ex, d, width / 1000.0, ln / 1050.0)
        o.name = label
        ROOF_OBJ[label] = o


def check_valleys():
    """Numeric check of the four valley corners: transform the two triangles' mesh vertices with the D1.14 table and print where the hypotenuse ends land."""
    corners = {"SE": ("CLA_Roof_S_0", "CLA_Roof_E_2", (11380.0, 1420.0, 640.0), (12000.0, 540.0, 1200.0)),
               "SW": ("CLA_Roof_W_0", "CLA_Roof_S_2", (10320.0, 1420.0, 640.0), (9500.0, 540.0, 1200.0)),
               "NW": ("CLA_Roof_N_0", "CLA_Roof_W_2", (10320.0, 2180.0, 640.0), (9500.0, 3000.0, 1200.0)),
               "NE": ("CLA_Roof_E_0", "CLA_Roof_N_3", (11380.0, 2180.0, 640.0), (12000.0, 3000.0, 1200.0))}

    def vert(o, lx, ly):
        me = o.data
        cand = [v.co for v in me.vertices if abs(v.co.z) < 0.01]
        c = min(cand, key=lambda p: (p.x - lx) ** 2 + (p.y - ly) ** 2)
        return o.matrix_world @ Vector((c.x, c.y, 0.0)), math.hypot(c.x - lx, c.y - ly)
    worst = 0.0
    print("VALLEY CHECK  (world coordinates of the hypotenuse ends, cm)")
    for nm, (lab_l, lab_r, garth, outer) in corners.items():
        # which label is the L and which the R triangle: by mesh name
        pair = {}
        for lab in (lab_l, lab_r):
            o = ROOF_OBJ[lab]
            pair['L' if 'Valley_L' in o.data.name else 'R'] = (lab, o)
        (labL, oL), (labR, oR) = pair['L'], pair['R']
        eL, dL1 = vert(oL, 1000.0, 0.0)
        tL, dL2 = vert(oL, 0.0, 1050.0)
        uL, dL3 = vert(oL, 1000.0, 1050.0)
        eR, dR1 = vert(oR, 0.0, 0.0)
        tR, dR2 = vert(oR, 1000.0, 1050.0)
        uR, dR3 = vert(oR, 0.0, 1050.0)
        g = (eL - eR).length
        t = (tL - tR).length
        ge = max((eL - Vector(garth)).length, (eR - Vector(garth)).length)
        oe = max((tL - Vector(outer)).length, (tR - Vector(outer)).length)
        worst = max(worst, g, t)
        print("  %s  %s(L) + %s(R)" % (nm, labL, labR))
        print("      garth end : L (%.2f, %.2f, %.2f)  R (%.2f, %.2f, %.2f)  gap %.3f  max off table %.3f  [mesh vertex off ideal %.3f / %.3f]" % (*eL, *eR, g, ge, dL1, dR1))
        print("      outer end : L (%.2f, %.2f, %.2f)  R (%.2f, %.2f, %.2f)  gap %.3f  max off table %.3f  [mesh vertex off ideal %.3f / %.3f]" % (*tL, *tR, t, oe, dL2, dR2))
        print("      other top vertices (must be Z 1200): L (%.2f, %.2f, %.2f)  R (%.2f, %.2f, %.2f)" % (*uL, *uR))
        print("      eaves Z (640): %.3f / %.3f   top Z (1200): %.3f %.3f %.3f %.3f" % (eL.z, eR.z, tL.z, tR.z, uL.z, uR.z))
    print("VALLEY CHECK worst hypotenuse-end gap %.3f cm (limit 1.0)" % worst)


def build_cells(stand_in_leaves=True):
    leaf_mat = bpy.data.materials["MAT_Wood"]
    for x in (9900, 10500, 11100):
        place("CellDoorFrame_150x270", (x, 3000, 0), 0, group="cells")
        if stand_in_leaves:
            door_leaf((x, 3000 - 3.5, 0), 0, hang=(x == 11100))
    for y in (900, 2700):
        place("CellDoorFrame_150x270", (9500, y, 0), 90, group="cells")
        if stand_in_leaves:
            door_leaf((9500 + 3.5, y, 0), 90)


def door_leaf(loc, yaw, hang=False):
    """Render-only stand-in for SM_Dungeon_door: oak planks 104 x 5 x 236 (frame opening 110 x 250), 1 cm in front of the back panel."""
    b = bmesh.new()
    n = 5
    for i in range(n):
        bx = K.box(-52 + i * 20.8 + 0.3, -52 + (i + 1) * 20.8 - 0.3, -2.5, 2.5, 4, 249, 0, 0.5)
        K.bm_append(b, bx)
        bx.free()
    for z in (40, 200):
        K.bm_append(b, K.box(-52, 52, 2.5, 4.5, z, z + 12, 0, 0.4))
    iron = flat_mat("R_Iron", (0.02, 0.02, 0.022, 1), 0.5, 0.9)
    o = new_mesh_obj("door_leaf", b, [bpy.data.materials["MAT_Wood"]], grp="cells")
    R = rz(yaw)
    if hang:
        R = R @ rz(8) @ Matrix.Rotation(math.radians(4), 4, 'Y')
        o.matrix_world = Matrix.Translation(Vector(loc)) @ R @ Matrix.Translation((-52, 0, 0)) @ Matrix.Translation((52, 0, 0))
    else:
        o.matrix_world = Matrix.Translation(Vector(loc)) @ R
    return o


# ----------------------------------------------------------------------------------------------
# render-only dressing
# ----------------------------------------------------------------------------------------------
def build_floors():
    floor = flat_mat("R_Floor", (0.035, 0.034, 0.032, 1), 0.7)
    flag = mk_stone("R_Flag", (0.03, 0.03, 0.028, 1), (0.09, 0.085, 0.075, 1), 0.75, 0.05, 0.6)
    wet = mk_stone("R_Wet", (0.018, 0.02, 0.022, 1), (0.05, 0.055, 0.06, 1), 0.25, 0.05, 0.3)
    for (nm, x0, x1, y0, y1, m) in (("S", 9500, 12000, 540, 1310, flag), ("W", 9500, 10210, 1310, 2290, flag), ("E", 11490, 12000, 1310, 2290, flag),
                                      ("N1", 9500, 10850, 2290, 3000, flag), ("N2", 10850, 11490, 2290, 3000, wet), ("N3", 11490, 12000, 2290, 3000, flag)):
        box_obj("CLA_Floor_" + nm, x0, x1, y0, y1, -38.5, 0.0, m)
    cob = mk_stone("R_Cobble", (0.03, 0.028, 0.026, 1), (0.085, 0.08, 0.07, 1), 0.85, 0.07, 0.9)
    box_obj("ground_passage", 6040, 9500, 1700, 2300, -40, 0.0, cob)
    box_obj("ground_outer", 4000, 13400, -3600, 540, -40, -0.5, cob)
    # garth block (greybox stand-in) and the stair-house trench
    box_obj("garth_block", 10300, 11400, 1400, 2200, 0, 99.5, mk_stone("R_GarthStone", (0.06, 0.058, 0.05, 1), (0.14, 0.13, 0.11, 1), 0.9, 0.04, 0.5))
    box_obj("trench", 10500, 10800, -100, 500, -400, -300, flat_mat("R_Dark", (0.004, 0.004, 0.004, 1), 1.0))
    box_obj("tower_mass", 12040, 13000, 1500, 2500, 0, 3500, mk_stone("R_Tower", (0.06, 0.058, 0.05, 1), (0.14, 0.13, 0.11, 1), 0.9, 0.02, 0.5))


def build_collapse_rubble():
    """Render-only: fallen vault stones + slates under the N-east bay (the P10-6a dressing does the real one)."""
    rng = random.Random(1401)
    mat = bpy.data.materials["MAT_Rubble"]
    mat2 = bpy.data.materials["MAT_Masonry"]
    slate = bpy.data.materials["MAT_Slate"]
    b = bmesh.new()
    for _ in range(46):
        sx, sy, sz = rng.uniform(14, 62), rng.uniform(12, 50), rng.uniform(8, 34)
        x, y = rng.uniform(10980, 11420), rng.uniform(2310, 2520)
        pts = [Vector((x + rng.uniform(-sx, sx) * 0.5, y + rng.uniform(-sy, sy) * 0.5, rng.uniform(0, sz))) for _ in range(9)]
        pts += [Vector((x + rng.uniform(-sx, sx) * 0.5, y + rng.uniform(-sy, sy) * 0.5, 0.0)) for _ in range(3)]
        h = K.hull_from_points(pts, 0, merge_coplanar=False)
        K.bm_append(b, h)
        h.free()
    heap = K.hull_from_points([Vector((p[0], p[1], p[2])) for p in
                               [(11050, 2300, 0), (11370, 2300, 0), (11370, 2500, 0), (11050, 2500, 0), (11200, 2400, 62), (11120, 2380, 48), (11290, 2420, 58), (11220, 2330, 40), (11210, 2480, 44)]], 0, merge_coplanar=False)
    K.bm_append(b, heap)
    new_mesh_obj("rubble", b, [mat], grp="dress")
    # voussoir blocks (masonry) and slates
    b2 = bmesh.new()
    for _ in range(14):
        x, y = rng.uniform(11000, 11400), rng.uniform(2320, 2480)
        blk = K.box(-18, 18, -12, 12, 0, 22, 0, 2.0)
        for v in blk.verts:
            v.co += Vector((x, y, rng.uniform(5, 40)))
        K.bm_append(b2, blk)
        blk.free()
    o = new_mesh_obj("fallen_blocks", b2, [mat2], grp="dress")
    for i, ob in enumerate([o]):
        ob.rotation_euler = (0, 0, 0)
    b3 = bmesh.new()
    for _ in range(40):
        x, y = rng.uniform(10980, 11450), rng.uniform(2300, 2520)
        sl = K.box(-14, 14, -10, 10, 0, 1.5, 0, 0.3)
        rot = Matrix.Rotation(rng.uniform(0, 6.28), 4, 'Z') @ Matrix.Rotation(rng.uniform(-0.5, 0.5), 4, 'X')
        for v in sl.verts:
            v.co = rot @ v.co + Vector((x, y, rng.uniform(2, 50)))
        K.bm_append(b3, sl)
        sl.free()
    new_mesh_obj("fallen_slates", b3, [slate], grp="dress")
    # a broken rafter
    rf = K.box(-130, 130, -6, 6, -7, 7, 0, 0.5)
    rot = Matrix.Translation((11300, 2340, 90)) @ rz(70) @ Matrix.Rotation(math.radians(-38), 4, 'Y')
    for v in rf.verts:
        v.co = rot @ v.co
    new_mesh_obj("fallen_rafter", rf, [bpy.data.materials["MAT_Wood"]], grp="dress")


def build_grass(count=140, seed=1224):
    rng = random.Random(seed)
    green = flat_mat("R_Grass", (0.035, 0.07, 0.02, 1), 0.9)
    dry = flat_mat("R_Weed", (0.07, 0.06, 0.02, 1), 0.9)
    bm = bmesh.new()
    bm2 = bmesh.new()
    keep = [(10850, 1800, 90), (10750, 1425, 40)] + [(x, y, 70) for (x, y) in ((10500, 1600), (10500, 2000), (10700, 1650), (11000, 2000), (11200, 1600), (11200, 1950))]
    n = 0
    while n < count:
        x, y = rng.uniform(10320, 11380), rng.uniform(1420, 2180)
        if any(math.hypot(x - kx, y - ky) < kr for kx, ky, kr in keep):
            continue
        n += 1
        tgt = bm if rng.random() < 0.8 else bm2
        h0 = rng.uniform(18, 48)
        for _ in range(rng.randint(6, 11)):
            a = rng.uniform(0, 6.283)
            lean = rng.uniform(0.15, 0.7)
            hh = h0 * rng.uniform(0.6, 1.1)
            base = Vector((x + rng.uniform(-4, 4), y + rng.uniform(-4, 4), 101.0))
            tip = base + Vector((math.cos(a) * lean * hh * 0.6, math.sin(a) * lean * hh * 0.6, hh))
            side = Vector((-math.sin(a), math.cos(a), 0.0)) * 1.1
            v0, v1, v2 = tgt.verts.new(base - side), tgt.verts.new(base + side), tgt.verts.new(tip)
            tgt.faces.new((v0, v1, v2))
    new_mesh_obj("grass", bm, [green], grp="dress")
    new_mesh_obj("weeds", bm2, [dry], grp="dress")


def make_text(txt, size, loc, rot_euler, mat, extrude=0.3, align='CENTER', name="txt"):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = txt
    cu.size = size
    cu.extrude = extrude
    cu.align_x = align
    cu.align_y = 'CENTER'
    o = bpy.data.objects.new(name, cu)
    o.data.materials.append(mat)
    o.location = loc
    o.rotation_euler = rot_euler
    o.scale = (-1.0, 1.0, 1.0)                  # pre-mirrored: the camera below is mirrored too (authoring space = Y-mirror of Unreal)
    bpy.context.scene.collection.objects.link(o)
    o["grp"] = "bells"
    PLACED.append(o)
    return o


BAND = [("MI_LB_BellBand_I", (0.32, 0.07, 0.05, 1)), ("MI_LB_BellBand_II", (0.42, 0.30, 0.08, 1)), ("MI_LB_BellBand_III", (0.10, 0.22, 0.17, 1)), ("MI_LB_BellBand_IV", (0.66, 0.62, 0.52, 1))]
SCALES = (1.30, 1.15, 1.00, 0.85)
NUMERAL = ("I", "II", "III", "IV")


def build_bells():
    """D1.6: Bell_1..4 actors at (11983, Y, 0) yaw 180; Post (bracket) at local (-17,0,145), BellPivot (8,0,140), Bell (0,0,-2) x BellScale, Plate (-17,0,87), Glyph (-12.8,0,87) WorldSize 18;
    inscription tablet at (11995, 2380, 200) x 2.5, back flush to X 12000.  Stand-in wall behind (E-frame C1 pieces) because the tower wall pieces are another task."""
    # stand-in wall at X 12000, Y 1500..3000
    L = 1500.0
    n = 4
    for i in range(n):
        place("Wall40_400x1300_%s" % ("A" if i % 2 == 0 else "B"), (12000, 3000 - i * L / n, 0), -90, (L / (400.0 * n), 1, 1), group="bells")
    glyph = flat_mat("R_Glyph", (0.025, 0.022, 0.02, 1), 0.7)
    for i, (y, sc, nm) in enumerate(zip((2200, 2320, 2440, 2560), SCALES, NUMERAL)):
        ax, ay = 11983.0, float(y)
        place(PR + "SmallBellBracket_A", (ax + 17.0, ay, 145.0), 180, group="bells")
        bell = place(PR + "SmallBell_A", (ax - 8.0, ay, 138.0), 180, scale=(sc, sc, sc), group="bells")
        mname, mcol = BAND[i]
        bm_ = bpy.data.materials.new(mname)
        nt, bs = _clear(bm_)
        bs.inputs['Base Color'].default_value = mcol
        bs.inputs['Roughness'].default_value = 0.8
        bell.material_slots[2].link = 'OBJECT'
        bell.material_slots[2].material = bm_
        place(PR + "BellPlaque_A", (ax + 17.0, ay, 87.0), 180, group="bells")
        make_text(nm, 18.0 * 0.62, (ax + 12.8 - 0.1, ay, 87.0), (math.radians(90), 0, math.radians(-90)), glyph, 0.25, name="glyph%d" % i)
    place(PR + "InscriptionTablet_A", (12000.0, 2380.0, 200.0), 180, (2.5, 2.5, 2.5), group="bells")
    tx = 11990.0 - 0.2
    make_text("STRIKE AS THE DEAD RECALL", 8.5, (tx, 2380.0, 213.0), (math.radians(90), 0, math.radians(-90)), glyph, 0.3, name="tab1")
    make_text("III  ·  I  ·  IV  ·  II", 15.0, (tx, 2380.0, 186.0), (math.radians(90), 0, math.radians(-90)), glyph, 0.3, name="tab2")


# ----------------------------------------------------------------------------------------------
# lights / camera / render
# ----------------------------------------------------------------------------------------------
def clear_lights():
    for o in [o for o in bpy.data.objects if o.type == 'LIGHT']:
        bpy.data.objects.remove(o)


def add_sun(name, rot_deg, strength, color=(0.62, 0.72, 1.0)):
    l = bpy.data.lights.new(name, 'SUN')
    l.energy = strength
    l.color = color
    l.angle = math.radians(1.2)
    o = bpy.data.objects.new(name, l)
    bpy.context.scene.collection.objects.link(o)
    o.rotation_euler = [math.radians(v) for v in rot_deg]
    return o


LANTERN_SCALE = 0.35


def add_point(name, loc, watts, color=(1.0, 0.55, 0.26), radius=6.0):
    l = bpy.data.lights.new(name, 'POINT')
    l.energy = watts * LANTERN_SCALE
    l.color = color
    l.shadow_soft_size = radius
    o = bpy.data.objects.new(name, l)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    return o


def add_spot(name, loc, target, watts, cone_deg, color=(1.0, 0.6, 0.3), radius=8.0):
    l = bpy.data.lights.new(name, 'SPOT')
    l.energy = watts
    l.color = color
    l.spot_size = math.radians(cone_deg)
    l.spot_blend = 0.5
    l.shadow_soft_size = radius
    o = bpy.data.objects.new(name, l)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o


def setup_render(quick, samples, w=1440, h=810):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = samples or (24 if quick else 80)
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.cycles.use_adaptive_sampling = True
    try:
        sc.cycles.device = 'CPU'
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = (w // 2, h // 2) if quick else (w, h)
    sc.render.image_settings.file_format = 'PNG'
    sc.render.film_transparent = False
    try:
        sc.view_settings.view_transform = 'AgX'
    except Exception:
        pass
    sc.view_settings.exposure = 0.0
    world = sc.world or bpy.data.worlds.new("W")
    sc.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0.020, 0.030, 0.055, 1.0)
    bg.inputs['Strength'].default_value = 1.0
    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return sc, cam


def aim(cam, loc, target, lens=24.0):
    cam.scale = (-1.0, 1.0, 1.0)
    cam.location = loc
    cam.data.lens = lens
    cam.data.clip_start = 5.0
    cam.data.clip_end = 100000.0
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()


def show_groups(groups, extra_names=()):
    for o in PLACED:
        o.hide_render = not (o.get("grp") in groups or o.name in extra_names)


# Each view: name, groups visible, camera loc, target, lens, lights fn, exposure
def lights_section():
    add_sun("moon", (70, 0, 250), 2.0)
    add_point("fill", (11500, 925, 400), 8.0e6, radius=20)


def lights_corner_in():
    add_sun("moon", (58, 0, 205), 0.45)
    for (x, y) in ((10560, 760), (11500, 900), (9900, 780)):
        add_point("lantern_%d" % x, (x, y, 235), 7.0e6, radius=6)
    add_point("lantern_far", (9780, 2650, 235), 4.0e6, radius=6)


def lights_garth():
    add_sun("moon", (52, 0, 200), 1.4)
    for (x, y) in ((10560, 760), (11500, 900)):
        add_point("lantern_%d" % x, (x, y, 235), 4.0e6, radius=6)


def lights_collapse():
    add_sun("moon", (22, 0, 180), 3.0)
    add_point("lantern_a", (10700, 2600, 235), 4.0e6, radius=6)
    add_point("lantern_b", (11700, 2550, 235), 3.0e6, radius=6)


def lights_roofs_top():
    add_sun("moon", (50, 0, 215), 3.2)
    add_sun("fill", (35, 0, 20), 0.6)


def lights_bells():
    add_point("lantern_l", (11720, 2250, 190), 9.0e6, radius=5)
    add_point("lantern_r", (11720, 2520, 190), 5.0e6, radius=5)
    add_sun("moon", (70, 0, 250), 0.1)


def lights_archway():
    add_sun("moon", (50, 0, 130), 0.9)
    add_point("wall_lantern", (9000, 1760, 260), 5.0e6, radius=5)


def lights_cell():
    add_sun("moon", (55, 0, 190), 0.35)
    add_point("lantern", (10150, 2740, 230), 8.0e6, radius=5)


def lights_stair():
    add_sun("moon", (40, 0, 10), 1.5)
    add_point("stair_lantern", (10650, 120, 360), 6.0e6, radius=5)


ALL = {"walls", "arcade", "garth", "vault", "roof", "cells", "floor", "dress", "passage", "stairhouse", "bells"}
VIEWS = {
    "corner_in": dict(file="p10_5b_cloister_corner_walk", groups=ALL - {"bells"}, loc=(11380, 850, 175), tgt=(9900, 1000, 330), lens=20, lights=lights_corner_in, exp=0.9),
    "corner_garth": dict(file="p10_3b_cloister_corner_garth", groups=ALL - {"bells"}, loc=(11200, 1700, 190), tgt=(9900, 2650, 520), lens=18, lights=lights_garth, exp=1.8),
    "ceiling": dict(file="p10_3b_groin_ceiling_up", groups=ALL - {"bells"}, loc=(10300, 925, 150), tgt=(9900, 925, 700), lens=18, lights=lights_corner_in, exp=0.9),
    "section": dict(file="p10_3b_section_s_bay_roof_clearance", groups={"vault", "roof", "walls", "arcade"}, loc=(11500, 925, 760), tgt=(10000, 925, 760), lens=24, lights=lights_section, exp=2.2, xr=(10300, 10800), ortho=1700),
    "collapse": dict(file="p10_3b_collapse_ne_bay", groups=ALL - {"bells"}, loc=(11300, 1000, 1150), tgt=(11200, 2450, 760), lens=24, lights=lights_collapse, exp=1.0),
    "collapse_hi": dict(file="p10_5b_collapse_ne_bay_walk", groups=ALL - {"bells"}, loc=(10050, 2450, 165), tgt=(11200, 2480, 520), lens=22, lights=lights_collapse, exp=1.2),
    "archway": dict(file="p10_3b_w_archway_from_passage", groups=ALL - {"bells"}, loc=(8300, 2000, 165), tgt=(9800, 2000, 330), lens=24, lights=lights_archway, exp=0.5),
    "garth": dict(file="p10_3b_garth_graves_cross", groups=ALL - {"bells"}, loc=(10300, 1500, 220), tgt=(10950, 1900, 130), lens=24, lights=lights_garth, exp=1.8),
    "garth_hi": dict(file="p10_3b_garth_cross_close", groups=ALL - {"bells"}, loc=(10330, 1520, 175), tgt=(10850, 1800, 190), lens=26, lights=lights_garth, exp=2.6),
    "cell": dict(file="p10_3b_cell_door", groups=ALL - {"bells"}, loc=(10500, 2560, 150), tgt=(10500, 3000, 135), lens=30, lights=lights_cell, exp=0.9),
    "stairhouse": dict(file="p10_3b_stairhouse", groups=ALL - {"bells"}, loc=(10050, -950, 640), tgt=(10650, 80, 330), lens=26, lights=lights_stair, exp=1.0),
    # P10-5b: the valley roofs (D1.14)
    "sw_groin_up": dict(file="p10_5b_cloister_sw_groin_up", groups=ALL - {"bells"}, loc=(9900, 1000, 170), tgt=(9786, 869, 1155), lens=18, lights=lights_corner_in, exp=2.2),
    "roofs_top": dict(file="p10_5b_cloister_roofs_top", groups=ALL - {"bells"}, loc=(12600, 0, 2600), tgt=(10850, 1800, 700), lens=24, lights=lights_roofs_top, exp=1.0),
    "bells": dict(file="p10_3b_mech3_bells_inscription", groups={"bells", "floor"}, loc=(11520, 2380, 150), tgt=(12000, 2380, 150), lens=26, lights=lights_bells, exp=1.1),
    "bells_close": dict(file="p10_3b_mech3_bells_close", groups={"bells", "floor"}, loc=(11760, 2300, 135), tgt=(12000, 2330, 125), lens=30, lights=lights_bells, exp=1.1),
}


def probe_roofs(sc, out, name):
    """Render the same view with every roof object magenta (emission) and count magenta pixels: any roof timber/slate that is visible shows up."""
    import numpy as np
    mg = bpy.data.materials.get("R_Probe") or bpy.data.materials.new("R_Probe")
    nt, bs = _clear(mg)
    bs.inputs['Base Color'].default_value = (1.0, 0.0, 1.0, 1)
    bs.inputs['Emission Color'].default_value = (1.0, 0.0, 1.0, 1)
    bs.inputs['Emission Strength'].default_value = 1.0
    roofs = [o for o in PLACED if o.get("grp") == "roof" and not o.hide_render]
    for o in roofs:
        for sl in o.material_slots:
            sl.link = 'OBJECT'
            sl.material = mg
    old = sc.render.filepath
    old_vt, old_exp = sc.view_settings.view_transform, sc.view_settings.exposure
    sc.view_settings.view_transform, sc.view_settings.exposure = 'Standard', 0.0      # emission (1,0,1) -> pixel (1,0,1)
    sc.render.filepath = os.path.join(out, name + "_probe.png")
    bpy.ops.render.render(write_still=True)
    sc.view_settings.view_transform, sc.view_settings.exposure = old_vt, old_exp
    img = bpy.data.images.load(sc.render.filepath)
    px = np.array(img.pixels[:]).reshape(-1, 4)
    mag = (px[:, 0] > 0.35) & (px[:, 2] > 0.35) & (px[:, 1] < 0.4 * np.minimum(px[:, 0], px[:, 2]))
    print("PROBE %s: %d of %d pixels show a roof (%.3f %%)" % (name, int(mag.sum()), len(px), 100.0 * mag.sum() / len(px)))
    bpy.data.images.remove(img)
    for o in roofs:
        for sl in o.material_slots:
            sl.link = 'DATA'
    sc.render.filepath = old


# ----------------------------------------------------------------------------------------------
# P10-8d (D1.27 F1): the 8 new pieces on their own (lantern brackets, memorial tablet, named grave slabs)
#   blender -b --factory-startup --python render_cloister.py -- --set p10_8d [--quick] [--only SUBSTR]
# Reads SourceArt/Cloister/LB_Cloister_p10_8d.blend (build_cloister.py --only LanternBracket Tablet_Memorial 200x80_ --tag p10_8d) and writes
# Docs/ArtTest/belltower/p10_8d_<name>.png.  Every view uses the usual mirrored camera, so the images show the IN-GAME (Unreal-handed) picture; the *_native
# image is the same tablet seen by an un-mirrored camera (what Blender's own viewport shows: its lettering is mirrored by design, see UE_VIEW in build_cloister.py).
# ----------------------------------------------------------------------------------------------
BLEND_8D = os.path.join(REPO, "SourceArt", "Cloister", "LB_Cloister_p10_8d.blend")


def add_sun_dir(name, to_light, strength, color=(1.0, 1.0, 1.0), angle_deg=2.0):
    """Sun whose light arrives from the direction `to_light` (a vector from the subject toward the light)."""
    l = bpy.data.lights.new(name, 'SUN')
    l.energy = strength
    l.color = color
    l.angle = math.radians(angle_deg)
    o = bpy.data.objects.new(name, l)
    bpy.context.scene.collection.objects.link(o)
    o.rotation_euler = (-Vector(to_light)).to_track_quat('-Z', 'Y').to_euler()
    return o


WARM = (1.0, 0.62, 0.32)


def render_8d(out, quick, samples, only):
    bpy.ops.wm.open_mainfile(filepath=BLEND_8D)
    K.setup_scene_units()
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name.startswith("SM_LB_"):
            SRC[o.name] = o
            o.hide_render = True
            o.hide_viewport = True
    setup_materials()
    mk_stone("MAT_Carve", (0.012, 0.012, 0.011, 1), (0.035, 0.034, 0.03, 1), 0.95, 0.05, 0.3)
    dark = flat_mat("R_LanternProxy", (0.05, 0.035, 0.02, 1), 0.45, 0.6)
    sc, cam = setup_render(quick, samples)
    floor_m = bpy.data.materials["MAT_Earth"]

    def clear_scene():
        for o in list(PLACED):
            bpy.data.objects.remove(o)
        PLACED.clear()
        clear_lights()

    def shoot(name, w, h, loc, tgt, lens, exp, ortho=None, native=False):
        if only and not any(s in name for s in only):
            return
        sc.render.resolution_x, sc.render.resolution_y = (w // 2, h // 2) if quick else (w, h)
        if ortho:
            cam.data.type = 'ORTHO'
            cam.data.ortho_scale = ortho
        else:
            cam.data.type = 'PERSP'
        sc.view_settings.exposure = exp
        aim(cam, loc, tgt, lens)
        if native:
            cam.scale = (1.0, 1.0, 1.0)
        sc.render.filepath = os.path.join(out, "p10_8d_" + name + ".png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", sc.render.filepath)
        sys.stdout.flush()

    # --- the tablet (root scale 2.5, as placed in game) -------------------------------------------------------------
    TB = "SM_LB_Prop_InscriptionTablet_Memorial"
    clear_scene()
    place(TB, (0, 0, 0), 0, (2.5, 2.5, 2.5), group="p")
    add_sun_dir("key", (0.78, 0.50, 0.62), 4.0, WARM)
    add_sun_dir("fill", (1.0, -0.4, 0.3), 0.5, (0.6, 0.7, 1.0))
    shoot("InscriptionTablet_Memorial_face", 1920, 540, (600, 0, 0), (0, 0, 0), 50, 0.8, ortho=304)
    shoot("InscriptionTablet_Memorial_face_native", 1920, 540, (600, 0, 0), (0, 0, 0), 50, 0.8, ortho=304, native=True)
    # 35 deg to the surface plane, one warm light above-left (in the picture) of the viewer
    for o in list(bpy.data.objects):
        if o.type == 'LIGHT':
            bpy.data.objects.remove(o)
    ang = math.radians(35.0)
    dirv = Vector((math.sin(ang), math.cos(ang), 0.0))                  # tablet -> camera
    camloc = dirv * 420.0 + Vector((0, 0, -10))
    # picture-left in the mirrored camera = the +y side when the camera sits at +y looking toward -y... resolved by looking at the render
    add_sun_dir("warm", (0.9, 0.9 * 0.0 + 0.55, 0.7), 4.5, WARM)
    shoot("InscriptionTablet_Memorial_grazing", 1920, 1080, tuple(camloc), (0, 0, 0), 40, 0.9)

    # --- the grave slabs, from above the foot (-x) end ---------------------------------------------------------------
    for nm in ("Anselm", "Tomas", "Edwin", "Osric"):
        clear_scene()
        place("SM_LB_Cl_GraveSlab_200x80_" + nm, (0, 0, 0), 0, group="p")
        box_obj("ground", -170, 170, -110, 110, -8, -0.01, floor_m, grp="p")
        add_sun_dir("key", (-0.45, -0.75, 0.50), 4.0, WARM)
        add_sun_dir("fill", (-0.6, 0.6, 0.6), 0.6, (0.6, 0.7, 1.0))
        shoot("GraveSlab_" + nm, 1440, 810, (-150, 0, 150), (-32, 0, 6), 38, 0.8)

    # --- the lantern brackets, from the side, with the lantern proxy hanging from the ring -----------------------------
    for R in (20, 40, 60):
        clear_scene()
        place("SM_LB_Prop_LanternBracket_R%d" % R, (0, 0, 0), 0, group="p")
        box_obj("wall", -40, 0, -70, 70, -100, 100, bpy.data.materials["MAT_Masonry"], grp="p")
        box_obj("lantern_proxy", R - 11, R + 11, -11, 11, -53, 0, dark, grp="p")
        add_sun_dir("key", (0.6, 0.8, 0.55), 4.0, WARM)
        add_sun_dir("fill", (0.5, -0.7, 0.4), 1.0, (0.6, 0.7, 1.0))
        shoot("LanternBracket_R%d" % R, 1440, 810, (R / 2.0 + 15.0, 400, -17), (R / 2.0 + 15.0, 0, -17), 50, 1.0, ortho=150)
    sc.cycles.samples = sc.cycles.samples


def main():
    sets, quick, samples, out = parse()
    os.makedirs(out, exist_ok=True)
    if "p10_8d" in sets:
        render_8d(out, quick, samples, ONLY)
        return
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    K.setup_scene_units()
    collect_sources()
    setup_materials()
    sc, cam = setup_render(quick, samples)
    # assembly
    build_cloister_walls()
    build_passage()
    build_stair_house()
    build_arcade()
    build_garth()
    build_vaults()
    build_roofs(aligned_hole=True)
    check_valleys()
    build_cells()
    build_floors()
    build_collapse_rubble()
    build_grass()
    build_bells()
    names = list(VIEWS) if "all" in sets else [n for n in sets if n in VIEWS]
    for nm in names:
        v = VIEWS[nm]
        clear_lights()
        show_groups(v["groups"])
        if v.get("xr"):
            for o in PLACED:
                if o.hide_render:
                    continue
                bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
                x0, x1 = min(b.x for b in bb), max(b.x for b in bb)
                if x1 < v["xr"][0] or x0 > v["xr"][1]:
                    o.hide_render = True
        if v.get("ortho"):
            cam.data.type = 'ORTHO'
            cam.data.ortho_scale = v["ortho"]
        else:
            cam.data.type = 'PERSP'
        v["lights"]()
        sc.view_settings.exposure = v["exp"]
        aim(cam, v["loc"], v["tgt"], v["lens"])
        sc.render.filepath = os.path.join(out, v["file"] + ".png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", sc.render.filepath)
        if PROBE:
            probe_roofs(sc, out, v["file"])
    sys.stdout.flush()


if __name__ == "__main__":
    main()
