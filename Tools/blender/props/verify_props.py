"""verify_props.py -- re-imports every procedural prop FBX in a clean headless Blender and checks it (P7F-2b).

    blender.exe -b --factory-startup --python Tools/blender/props/verify_props.py -- [--fbx SourceArt/Props/Procedural] [--json out.json]

Checks per piece (Unreal space: UE_Y = -Blender_Y of the re-imported file, see Tools/blender/kit/README.md):
  pivot bottom-centre (XY bounds centre at 0, min Z at 0, +-1 cm, node at the origin), dimensions vs the plan table
  (+-1 cm unless a tolerance is given), exact slot names/order, UCX count / naming UCX_<Mesh>_NN / convex / inside the
  visual bounds (+-1 cm; the key UCX is the one deliberate exception and must be exactly 17 x 7 x 12 cm, Z 0..12),
  vertex colour attribute present and white, UV layer, normals, positive volume, key-ledge flat centre at Z 70.
Exit code 1 if any check fails.
"""
import json
import os
import sys

import math

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "kit")))
import verify_kit as VK  # noqa: E402  (helpers only; importing builds nothing)

TOL = 1.0
P = "SM_LB_Prop_"
# name: dict(dims=(x, y, z) with None = unchecked, tol, slots, ucx)
SPEC = {
    "Key_Chapel": dict(dims=(15.6, 5.2, None), zmax=3.0, slots=["MAT_Iron"], ucx=1, ucx_env=(17.0, 7.0, 12.0)),
    "KeyLedge_50x50x70": dict(dims=(54.0, 54.0, 70.0), slots=["MAT_Trim"], ucx=1, ucx_env=(50.0, 50.0, 70.0)),
    "Gravestone_A": dict(dims=(60.0, 14.0, 95.0), slots=["MAT_Stone"], ucx=1),
    "Gravestone_B": dict(dims=(55.0, 14.0, 85.0), slots=["MAT_Stone"], ucx=1),
    "Gravestone_C": dict(dims=(60.0, 14.0, 45.0), slots=["MAT_Stone"], ucx=1),
    "Gravestone_C_Frag": dict(dims=(50.0, 14.0, 30.0), slots=["MAT_Stone"], ucx=1),
    "Gravestone_D": dict(dims=(35.0, 20.0, 45.0), slots=["MAT_Stone"], ucx=1),
    "StoneCross_A": dict(dims=(55.0, 30.0, 150.0), slots=["MAT_Stone"], ucx=3),     # Y 30 = base block; the cross itself is 18 deep
    "WoodCross_A": dict(dims=(55.0, 11.2, 120.0), slots=["MAT_Wood", "MAT_Rope"], ucx=2),   # Y 11.2 = rope rings (r 5 + tube)
    "GraveMound_A": dict(dims=(200.0, 90.0, 22.0), slots=["MAT_Earth"], ucx=0),
    "HandCart_A": dict(dims=(280.0, 140.0, 100.0), slots=["MAT_Wood", "MAT_Iron"], ucx=3),  # 170 bed + 110 shafts; wheels/axle set the width
    "FirePit_A": dict(dims=(125.0, 125.0, 31.0), tol=5.0, slots=["MAT_Stone", "MAT_Charred"], ucx=1),  # O110 stone-centre circle + 25-35 cm stones
    # ---- P7-FIX3 G2a ----
    "WellHead_A": dict(dims=(358.0, 258.0, 230.0), tol=2.5, slots=["MAT_Stone", "MAT_Wood", "MAT_Rope", "MAT_Iron", "MAT_Water"], ucx=10),  # ring O260, posts at +-152, cranks to +-179
    "TimberPost_20x20x420": dict(dims=(20.0, 20.0, 420.0), slots=["MAT_Wood"], ucx=1),
    "Purlin_15x15x1000": dict(dims=(15.0, 15.0, 1000.0), slots=["MAT_Wood"], ucx=0),
    "Rafter_15x10x420": dict(dims=(15.0, 10.0, 420.0), slots=["MAT_Wood"], ucx=0),
    "Rafter_Broken_15x10x260": dict(dims=(15.0, 10.0, 260.0), slots=["MAT_Wood"], ucx=0),
    "RoofPlanks_200x100x4": dict(dims=(200.0, 100.0, 4.0), slots=["MAT_Wood"], ucx=0),
    "RoofPlanks_Broken_200x100x4": dict(dims=(200.0, 100.0, 4.0), slots=["MAT_Wood"], ucx=0),
    "EarthPatch_400x400x15": dict(dims=(400.0, 400.0, 15.0), slots=["MAT_Earth"], ucx=1),
    "DeadTree_A": dict(dims=(None, None, 700.0), slots=["MAT_Bark"], ucx=1),              # 650-750 cm target, built to 700
}
# ---- P8-3 chapel props (plan section 2 P8-3 + amendment C1) ----
SPEC.update({
    "Truss_ArchBraced_1500": dict(dims=(30.8, 1500.0, 1265.0), tol=1.5, slots=["MAT_Wood"], ucx=0, struct="truss"),          # members 30 wide + pegs (0.4 each side), +-750 across, apex 1265 (world 2165)
    "Pew_A": dict(dims=(55.0, 250.0, 95.0), slots=["MAT_Wood"], ucx=2, struct="pew"),
    "Pew_Broken": dict(dims=(55.0, 250.0, 95.0), slots=["MAT_Wood"], ucx=3),
    "AltarRail_600x40x100": dict(dims=(40.0, 600.0, 100.0), slots=["MAT_Wood"], ucx=1),
    "Lectern_A": dict(dims=(56.0, 56.0, 125.0), slots=["MAT_Trim", "MAT_Wood"], ucx=2),
    "Altar_A": dict(dims=(104.0, 300.0, 101.0), slots=["MAT_Trim"], ucx=2, struct="altar"),
    "MechShell_Cyl": dict(dims=(84.0, 84.0, 51.0), slots=["MAT_Trim"], ucx=0, struct="shell_cyl"),
    "MechShell_Cube": dict(dims=(17.0, 17.0, 17.0), slots=["MAT_Trim"], ucx=0),
    "SlateShards_A": dict(dims=(120.0, 90.0, None), slots=["MAT_Slate"], ucx=0),
    "CrossFinial_A": dict(dims=(60.0, 25.0, 130.0), slots=["MAT_Trim"], ucx=0),
    "Backdrop_Plane_800x850": dict(dims=(0.0, 800.0, 850.0), slots=["MAT_Backdrop"], ucx=0, open_mesh=True, struct="backdrop"),
    "Glass_Lancet_140x560": dict(dims=(140.0, 1.0, 560.0), slots=["MAT_Glass"], ucx=0, uv01=True),
    "Glass_Lancet_Broken": dict(dims=(140.0, 1.0, None), zmax=450.0, slots=["MAT_Glass"], ucx=0, uv01=True),
    "Glass_East": dict(dims=(300.0, 1.0, None), zmax=540.0, slots=["MAT_Glass"], ucx=0, uv01=True),
    "Glass_Clue_Ext": dict(dims=(100.0, 1.0, 220.2), slots=["MAT_Glass"], ucx=0, uv01=True),
    "Cobweb_Corner_A": dict(dims=(120.0, 120.0, 120.0), slots=["MAT_Cobweb"], ucx=0, open_mesh=True, uv01=True),
    "Cobweb_Hang_A": dict(dims=(150.0, 12.0, 80.0), slots=["MAT_Cobweb"], ucx=0, open_mesh=True, uv01=True),
    "PricketStand_Small_10x30": dict(dims=(10.0, 10.0, 30.0), tol=0.5, slots=["MAT_Iron"], ucx=1, ucx_env=(10.0, 10.0, 30.0)),
    "PricketStand_150": dict(dims=(42.0, 39.0, 150.0), slots=["MAT_Iron"], ucx=1),
    "CandleFlame_A": dict(dims=(3.0, 3.0, 6.5), tol=0.5, slots=["MAT_Flame"], ucx=0),
})
# ---- P8-9a light-shaft cards (amendment C4): open oblique tubes along the moon direction d, free pivot (see struct == "shaft") ----
SHAFT_D = (math.cos(math.radians(-38.0)) * math.cos(math.radians(35.0)), math.cos(math.radians(-38.0)) * math.sin(math.radians(35.0)),
           math.sin(math.radians(-38.0)))   # DirectionalLight_1 forward (pitch -38, yaw 35) = (0.6455, 0.4520, -0.6157)
SPEC.update({
    "LightShaft_Lancet": dict(dims=(1294.9, 813.6, 1640.2), bmin=(-66.5, 0.0, -1094.9), slots=["MAT_LightShaft"], ucx=0, open_mesh=True, uv01=True,
                              free_pivot=True, struct="shaft", length=1800.0, segs=12),
    "LightShaft_RoofHole": dict(dims=(2367.0, 1743.6, 2309.0), bmin=(-220.1, -177.5, -2058.5), slots=["MAT_LightShaft"], ucx=0, open_mesh=True, uv01=True,
                                free_pivot=True, struct="shaft", length=3000.0, segs=16),
})
for _shape, _w, _h in (("Climb", 300.0, 450.0), ("Patch", 200.0, 300.0), ("Hang", 150.0, 600.0), ("Creep", 400.0, 200.0)):
    for _kind in ("Green", "Dead"):
        SPEC["Ivy_%s_%gx%g_%s" % (_shape, _w, _h, _kind)] = dict(dims=(_w, None, _h), ymax=25.0, slots=["MAT_Leaf", "MAT_Stem"], ucx=0,
                                                                 wall_pivot=True, open_mesh=True, subdir="Ivy")

# ---- P9-3 crypt pieces (plan Docs/plans/P9_CRYPT_ART.md amendment D1.3) ----
CP = "SM_LB_"
_STONE = ["MAT_Stone"]
SPEC.update({
    "Crypt_OssuaryBay_500x599": dict(prefix=CP, dims=(500.0, 96.0, 599.0), slots=_STONE, ucx=0, pivot="bay", tris_max=12000, struct="bay"),
    "Crypt_Capital_A": dict(prefix=CP, dims=(170.0, 170.0, 55.0), slots=_STONE, ucx=0, tris_max=3000),
    "Crypt_Stair40_300": dict(prefix=CP, dims=(1200.0, 300.0, 600.0), slots=_STONE, ucx=0, pivot="riser", tris_max=25000, struct="stair"),
    "Crypt_Sarcophagus_A": dict(prefix=CP, dims=(300.0, 120.0, 72.0), slots=_STONE, ucx=0, bounds_le=(150.0, 60.0, 72.0)),
    "Crypt_Sarcophagus_B": dict(prefix=CP, dims=(300.0, 120.0, 72.0), slots=["MAT_Stone", "MAT_Charred"], ucx=0, bounds_le=(150.0, 60.0, 72.0), struct="sarco_b"),
    "Crypt_BoneBin_200x100x60": dict(prefix=CP, dims=(200.0, 100.0, 60.0), slots=_STONE, ucx=0, struct="bonebin"),
    "Crypt_Block_100": dict(prefix=CP, dims=(100.0, 100.0, 100.0), slots=_STONE, ucx=1, ucx_boxes=[(-50, 50, -50, 50, 0, 100)]),
    "Crypt_Block_100_C": dict(prefix=CP, dims=(100.0, 100.0, 100.0), slots=_STONE, ucx=1, pivot="centre", ucx_boxes=[(-50, 50, -50, 50, -50, 50)]),
    "Crypt_Corbel_A": dict(prefix=CP, dims=(50.0, 55.0, 45.0), slots=_STONE, ucx=0, wall_pivot=True, ymax=56.0, struct="corbel"),
    "Crypt_Beam_35x45x1120": dict(prefix=CP, dims=(35.0, 1120.0, 45.0), slots=["MAT_Wood"], ucx=0),
    "Crypt_Boards_300x250": dict(prefix=CP, dims=(300.0, 250.0, 5.0), tol=1.0, slots=["MAT_Wood"], ucx=0, struct="boards", n_boards=10),
    "Crypt_Boards_300x250_Broken": dict(prefix=CP, dims=(300.0, 250.0, None), slots=["MAT_Wood"], ucx=0, pivot="xyfree", zmin_ge=-60.0, struct="boards", n_boards=8),
    "Crypt_RootsHang_A": dict(prefix=CP, dims=(80.0, 80.0, 180.0), tol=12.0, ztol=1.0, slots=["MAT_Bark"], ucx=0, pivot="top", tris_min=6000, tris_max=12000, struct="roots"),
    "Crypt_RootsHang_B": dict(prefix=CP, dims=(90.0, 90.0, 240.0), tol=12.0, ztol=1.0, slots=["MAT_Bark"], ucx=0, pivot="top", tris_min=6000, tris_max=12000, struct="roots"),
    "Crypt_RootsHang_C": dict(prefix=CP, dims=(60.0, 60.0, 120.0), tol=12.0, ztol=1.0, slots=["MAT_Bark"], ucx=0, pivot="top", tris_min=6000, tris_max=12000, struct="roots"),
    "Crypt_Portcullis_300x60x560": dict(prefix=CP, dims=(300.0, 60.0, 560.0), slots=["MAT_Iron"], ucx=1, tris_max=8000, ucx_boxes=[(-150, 150, -30, 30, 0, 560)], struct="portcullis"),
    "Crypt_RubbleFill_100x400x560": dict(prefix=CP, dims=(110.0, 420.0, 560.0), slots=["MAT_Stone", "MAT_Wood"], ucx=1, tris_max=40000, ucx_boxes=[(-50, 50, -200, 200, 0, 560)], struct="rubble"),
    "Crank_A": dict(dims=(42.0, 8.0, 14.5), tol=1.5, slots=["MAT_Iron", "MAT_Wood"], ucx=1, ucx_env=(44.0, 16.0, 16.0), struct="crank"),
    "Crypt_CapstanDrum_80x50": dict(prefix=CP, dims=(110.0, 110.0, 50.0), slots=["MAT_Wood", "MAT_Iron"], ucx=1, pivot="centre", ucx_boxes=[(-35, 35, -35, 35, -25, 25)], struct="capstan"),
    "Crypt_PlaqueFrame_270x195": dict(prefix=CP, dims=(270.0, 14.0, 195.0), slots=_STONE, ucx=0, pivot="backcentre", struct="plaque"),
    "Crypt_WinchFrame": dict(prefix=CP, dims=(260.0, 90.0, 250.0), slots=["MAT_Wood", "MAT_Iron"], ucx=4, tris_max=25000, struct="winch",
                             ucx_boxes=[(-120, -100, -10, 10, 0, 250), (100, 120, -10, 10, 0, 250), (-120, -100, -45, 45, 0, 10), (100, 120, -45, 45, 0, 10)]),
})
for _k in list(SPEC):
    if _k.startswith("Crypt_") or _k == "Crank_A":
        SPEC[_k]["subdir"] = "Crypt"

# ---- P9-R2A (plan amendment D1.25): bell wheel, dial-lever set (free pivot = centre of the engine primitive each part replaces; 'survey' = that primitive's AABB), roof-hole gobo ----
SPEC.update({
    "BellWheel_A": dict(dims=(89.0, 89.0, 58.0), slots=["MAT_Iron", "MAT_Bronze"], ucx=1, ucx_boxes=[(-42, 42, -42, 42, 0, 58)], tris_max=12000, struct="bellwheel"),
    "DialLever_Backplate": dict(dims=(15.35, 30.0, 122.5), bmin=(-3.35, -15.0, -45.0), slots=["MAT_Wood", "MAT_Iron"], ucx=0, free_pivot=True, struct="dl_backplate"),   # R2-A2: + pulley bracket and eyelet chain, Z to 77.5
    "DialLever_Quadrant": dict(dims=(53.98, 5.5, 64.04), bmin=(-6.0, -0.3, -32.02), slots=["MAT_Iron", "MAT_Paint"], ucx=0, free_pivot=True, struct="dl_quadrant"),   # R2-A2: sector plate R 48, pivot = sector centre
    "DialLever_Arm": dict(dims=(4.0, 3.9, 45.0), bmin=(-2.0, -1.95, -22.5), survey=(3.0, 3.0, 45.0), slots=["MAT_Iron", "MAT_Wood"], ucx=0, free_pivot=True, struct="dl_arm"),
    "DialLever_Weight": dict(dims=(11.42, 11.07, 9.9), bmin=(-5.8, -5.53, -4.95), slots=["MAT_Iron"], ucx=0, free_pivot=True, struct="dl_weight"),   # R2-A2: squat O11 ball, collar, no chain
    "DialLever_NotchStop": dict(dims=(5.0, 4.5, 3.0), bmin=(-2.5, -2.25, -1.5), survey=(6.0, 5.0, 2.5), slots=["MAT_Iron", "MAT_Paint"], ucx=0, free_pivot=True, struct="dl_notchstop"),
    "Gobo_RoofHole": dict(prefix=CP, dims=(2.0, 110.0, 110.0), slots=["MAT_Iron"], ucx=0, pivot="centre", struct="gobo"),
})
for _k in ("BellWheel_A", "DialLever_Backplate", "DialLever_Quadrant", "DialLever_Arm", "DialLever_Weight", "DialLever_NotchStop", "Gobo_RoofHole"):
    SPEC[_k]["subdir"] = "R2"


def parse():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    fbx = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SourceArt", "Props", "Procedural"))
    js = None
    for i, a in enumerate(argv):
        if a == "--fbx":
            fbx = os.path.abspath(argv[i + 1])
        if a == "--json":
            js = os.path.abspath(argv[i + 1])
    return fbx, js


def _bvh(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.transform(ob.matrix_world)
    return BVHTree.FromBMesh(bm), bm


def _ray(bvh, x, y, z, d):
    """Ray in Unreal-space cm (file y = -ue y); d = (dx, dy, dz) in UE space.  Returns the hit (x, y, z) in UE cm or None."""
    sc = bpy.context.scene.unit_settings.scale_length * 100.0
    h = bvh.ray_cast(Vector((x / sc, -y / sc, z / sc)), Vector((d[0], -d[1], d[2])))
    if h[0] is None:
        return None
    return (h[0].x * sc, -h[0].y * sc, h[0].z * sc)


def shaft_checks(spec, ob, fail, res):
    """Light-shaft cards: open ends only (boundary = the two end rings), every side face parallel to d, normals outward
    (even-odd test of a point just off the face against the t = 0 outline projected along d), UV U/V span exactly 0..1 and V = t / length."""
    me = ob.data
    d = Vector(SHAFT_D).normalized()
    notes = []
    pts = VK.ue_coords(ob)
    sc = bpy.context.scene.unit_settings.scale_length * 100.0
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    uvl = bm.loops.layers.uv.active
    # direction check: the edges between the two end rings follow d
    L, S = spec['length'], spec['segs']
    bnd = [e for e in bm.edges if len(e.link_faces) == 1]
    rings = {0: [], 1: []}
    for e in bnd:
        vs = [e.verts[0], e.verts[1]]
        vv = []
        for v in vs:
            lv = [l[uvl].uv[1] for l in v.link_loops]
            vv.append(round(min(lv), 3) if min(lv) < 0.5 else round(max(lv), 3))
        if vv[0] == vv[1] and vv[0] in (0.0, 1.0):
            rings[int(vv[0])].append(e)
        else:
            fail("boundary edge off the end rings (uv.v %s)" % vv)
    n0, n1 = len(rings[0]), len(rings[1])
    notes.append("boundary edges: ring V0 %d, ring V1 %d (total %d, mesh edges %d)" % (n0, n1, len(bnd), len(bm.edges)))
    if n0 != n1 or n0 < 8:
        fail("open ends: ring edge counts %d / %d" % (n0, n1))
    # edge directions along the length: connect corresponding ring verts -> direction must be d
    vmin, vmax = {}, {}
    for v in bm.verts:
        pu = pts[v.index]
        vl = [l[uvl].uv[1] for l in v.link_loops]
        vmin[v.index] = min(vl)
    # section polygon segments (UE space, projected along d) from ring 0
    e1 = Vector((1.0, 0.0, 0.0)) - d * d.x
    e1.normalize()
    e2 = d.cross(e1)
    proj = lambda p: (p.dot(e1), p.dot(e2))
    segs = []
    for e in rings[0]:
        a, b_ = pts[e.verts[0].index], pts[e.verts[1].index]
        segs.append((proj(a), proj(b_)))
    # the ring-1 points must be ring-0 points + L * d
    r0 = sorted({tuple(round(c, 1) for c in pts[v.index]) for e in rings[0] for v in e.verts})
    r1 = sorted({tuple(round(c, 1) for c in pts[v.index]) for e in rings[1] for v in e.verts})
    r0d = sorted(tuple(round(c, 1) for c in (Vector(p) + d * L)) for p in r0)
    off = max((Vector(a) - Vector(b)).length for a, b in zip(r0d, r1)) if len(r0d) == len(r1) else 1e9
    notes.append("far ring = near ring + %g d: max deviation %.2f cm " % (L, off))
    if off > 2.0:
        fail("far ring is not the near ring swept along d (deviation %.2f cm)" % off)

    def inside(q):
        x, y = q
        c = 0
        for (a, b_) in segs:
            if (a[1] > y) != (b_[1] > y):
                t = (y - a[1]) / (b_[1] - a[1])
                if a[0] + t * (b_[0] - a[0]) > x:
                    c += 1
        return c % 2 == 1

    bad_par = bad_out = 0
    for p in me.polygons:
        wn = (ob.matrix_world.to_3x3() @ p.normal).normalized()
        wc = ob.matrix_world @ p.center
        nrm = Vector((wn.x, -wn.y, wn.z))                                    # file -> UE
        c = Vector((wc.x, -wc.y, wc.z)) * sc
        if abs(nrm.dot(d)) > 0.02:
            bad_par += 1
        if inside(proj(c + nrm * 0.05)):
            bad_out += 1
    notes.append("faces %d: not parallel to d %d, normals pointing inward %d" % (len(me.polygons), bad_par, bad_out))
    if bad_par:
        fail("%d faces are not parallel to d" % bad_par)
    if bad_out:
        fail("%d face normals point inward" % bad_out)
    us = [dd.uv[0] for dd in me.uv_layers.active.data]
    vs = [dd.uv[1] for dd in me.uv_layers.active.data]
    notes.append("UV U %.3f..%.3f V %.3f..%.3f" % (min(us), max(us), min(vs), max(vs)))
    if min(us) > 0.001 or max(us) < 0.999 or min(vs) > 0.001 or max(vs) < 0.999:
        fail("UV does not span exactly 0..1: U %.3f..%.3f V %.3f..%.3f" % (min(us), max(us), min(vs), max(vs)))
    # V = distance along d / L for every vertex
    q0 = pts[rings[0][0].verts[0].index]                     # a point of the t = 0 ring; the ring plane has the Newell normal N
    ring0 = [pts[v.index] for v in {v for e in rings[0] for v in e.verts}]
    nN = Vector((0.0, 0.0, 0.0))
    cc = sum(ring0, Vector()) / len(ring0)
    for e in rings[0]:
        nN += (pts[e.verts[0].index] - cc).cross(pts[e.verts[1].index] - cc)
    nN.normalize()
    worst = 0.0
    for v in bm.verts:
        for l in v.link_loops:
            t = (pts[v.index] - q0).dot(nN) / d.dot(nN)
            worst = max(worst, abs(l[uvl].uv[1] - t / L))
    notes.append("V vs t/length max error %.4f" % worst)
    if worst > 0.01:
        fail("V is not t / length (max error %.3f)" % worst)
    if len(me.materials) != 1:
        fail("expected 1 material slot")
    bm.free()
    res['struct'] = notes


def _scan_runs(vals):
    """[(start_index, end_index)] of consecutive True entries."""
    runs, st = [], None
    for i, v in enumerate(vals):
        if v and st is None:
            st = i
        if not v and st is not None:
            runs.append((st, i - 1))
            st = None
    if st is not None:
        runs.append((st, len(vals) - 1))
    return runs


def _expect(notes, fail, label, got, want, tol):
    notes.append("%s: %s (want %s +-%g)" % (label, "None" if got is None else "%.2f" % got, want, tol))
    if got is None or abs(got - want) > tol:
        fail("%s: got %s, expected %s +-%g" % (label, got, want, tol))


def chk_bellwheel(bvh, ob, spec, notes, fail):
    h = _ray(bvh, 0.0, 0.0, 80.0, (0, 0, -1))
    _expect(notes, fail, "finial top z", h and h[2], 58.0, 0.6)
    h = _ray(bvh, 0.0, 0.0, -10.0, (0, 0, 1))
    _expect(notes, fail, "axle bottom z", h and h[2], 0.0, 0.3)
    h = _ray(bvh, 6.0, 0.0, 80.0, (0, 0, -1))
    _expect(notes, fail, "hub top z (x 6)", h and h[2], 42.0, 0.6)
    h = _ray(bvh, 0.0, 40.0, 80.0, (0, 0, -1))
    _expect(notes, fail, "rim top z (angle 90)", h and h[2], 39.5, 0.6)
    h = _ray(bvh, 20.0, 0.0, 80.0, (0, 0, -1))
    _expect(notes, fail, "spoke top z (angle 0, r 20)", h and h[2], 39.0, 0.6)
    nb = 0
    for k in range(8):                                                     # 8 bells every 45 deg at r 40: lip bottom (r 3.9..4.5) at z 22
        a = math.radians(45.0 * k)
        rr = 40.0 + 4.2
        h = _ray(bvh, rr * math.cos(a), rr * math.sin(a), -10.0, (0, 0, 1))
        if h is not None and abs(h[2] - 22.0) < 0.6:
            nb += 1
    notes.append("bell lips found at z 22: %d of 8" % nb)
    if nb != 8:
        fail("%d of 8 bell lips at z 22" % nb)
    for k in range(8):                                                     # between the bells: nothing under the rim (first hit = rim underside 36.5)
        a = math.radians(45.0 * k + 22.5)
        h = _ray(bvh, 40.0 * math.cos(a), 40.0 * math.sin(a), 10.0, (0, 0, 1))
        if h is None or abs(h[2] - 36.5) > 0.6:
            fail("between bells at %g deg: first hit %s (rim underside 36.5)" % (45.0 * k + 22.5, h and round(h[2], 2)))
    n_br = sum(1 for p in ob.data.polygons if p.material_index == 1)
    notes.append("Bronze faces %d" % n_br)
    if n_br < 8 * 60:
        fail("too few Bronze faces (%d)" % n_br)


def chk_backplate(bvh, ob, spec, notes, fail):
    def front(y, z):
        return _ray(bvh, 10.0, y, z, (-1, 0, 0))
    h = front(8.0, 5.0)
    _expect(notes, fail, "board front x (y 8, z 5)", h and h[0], 2.9, 0.2)
    h = front(8.0, -34.0)
    _expect(notes, fail, "lower strap x (z -34)", h and h[0], 3.35, 0.2)
    h = front(3.0, 35.0)
    _expect(notes, fail, "label plate x (z 35)", h and h[0], 3.5, 0.2)
    h = front(0.0, 0.0)
    _expect(notes, fail, "pivot bolt x (y 0, z 0)", h and h[0], 3.8, 0.2)
    h = front(0.0, -10.0)
    notes.append("seam gap (y 0, z -10): %s" % ("open" if h is None else "blocked at x %.2f" % h[0]))
    if h is not None:
        fail("the 0.5 seam is closed at z -10 (hit x %.2f)" % h[0])
    for zc in (-34.0, 17.0):
        hits = [(_ray(bvh, 10.0, -14.0 + 0.1 * i, zc, (-1, 0, 0)) or (0.0,))[0] >= 3.6 for i in range(281)]
        n = len(_scan_runs(hits))
        notes.append("rivet heads along the strap at z %g: %d (4)" % (zc, n))
        if n != 4:
            fail("%d rivets on the strap at z %g, expected 4" % (n, zc))
    h = _ray(bvh, 7.0, 0.0, 30.0, (0, 0, 1))
    _expect(notes, fail, "pulley wheel groove bottom z (O10 at z 50, groove r 4.1)", h and h[2], 45.9, 0.3)
    h = _ray(bvh, -10.0, 1.5, 75.0, (1, 0, 0))
    _expect(notes, fail, "eyelet base plate back face x (flush with the back plane)", h and h[0], -3.0, 0.15)
    h = _ray(bvh, -10.0, 8.0, 0.0, (1, 0, 0))
    _expect(notes, fail, "board back plane x", h and h[0], -3.0, 0.25)
    sc = bpy.context.scene.unit_settings.scale_length * 100.0
    n_up = sum(1 for q in ob.data.polygons if (ob.matrix_world @ q.center).z * sc > 52.0 and q.material_index == 1)
    notes.append("iron faces above z 52 (wheel top, chain, eyelet): %d" % n_up)
    if n_up < 500:
        fail("chain / eyelet faces %d" % n_up)
    n_w = sum(1 for p in ob.data.polygons if p.material_index == 0)
    n_i = sum(1 for p in ob.data.polygons if p.material_index == 1)
    notes.append("Wood faces %d, Iron faces %d" % (n_w, n_i))
    if n_w < 100 or n_i < 100:
        fail("Wood / Iron face counts %d / %d too low" % (n_w, n_i))


def chk_quadrant(bvh, ob, spec, notes, fail):
    """R2-A2 sector plate (pivot = sector centre, XZ plane, R 48, +-42 deg): 3 V-notches through the rim, 3 pegs on the -Y face at R 39, foot at x -6."""
    n = 1641
    angs = [-41.0 + 0.05 * i for i in range(n)]
    hits = [_ray(bvh, 47.6 * math.cos(math.radians(a)), 10.0, 47.6 * math.sin(math.radians(a)), (0, -1, 0)) is None for a in angs]
    runs = _scan_runs(hits)
    cen = [(angs[a] + angs[b]) / 2.0 for a, b in runs]
    notes.append("rim notches (R 47.6) at %s deg" % [round(c, 2) for c in cen])
    if len(runs) != 3 or any(abs(c - w) > 0.4 for c, w in zip(cen, (-35.0, 0.0, 35.0))):
        fail("notches found at %s deg, expected -35 / 0 / 35" % cen)
    for deg in (-35.0, 0.0, 35.0):
        a = math.radians(deg)
        h = _ray(bvh, 39.0 * math.cos(a), -10.0, 39.0 * math.sin(a), (0, 1, 0))
        _expect(notes, fail, "peg tip y at %g deg" % deg, h and h[1], -0.3, 0.2)
    a = math.radians(-17.5)
    h = _ray(bvh, 39.0 * math.cos(a), -10.0, 39.0 * math.sin(a), (0, 1, 0))
    _expect(notes, fail, "plate -Y face between pegs y", h and h[1], 1.7, 0.2)
    a = math.radians(-17.0)
    h = _ray(bvh, 47.0 * math.cos(a), 10.0, 47.0 * math.sin(a), (0, -1, 0))
    _expect(notes, fail, "rim top y", h and h[1], 5.2, 0.25)
    h = _ray(bvh, -20.0, 2.4, 0.0, (1, 0, 0))
    _expect(notes, fail, "mounting foot back x", h and h[0], -6.0, 0.2)
    for deg, want in ((40.0, True), (44.0, False)):
        a = math.radians(deg)
        h = _ray(bvh, 30.0 * math.cos(a), 10.0, 30.0 * math.sin(a), (0, -1, 0))
        notes.append("sector edge probe at %g deg R 30: %s" % (deg, "plate" if h else "empty"))
        if (h is not None) != want:
            fail("sector edge probe at %g deg: %s" % (deg, "plate" if h else "empty"))
    n_p = sum(1 for q in ob.data.polygons if q.material_index == 1)
    notes.append("Paint faces %d" % n_p)
    if n_p < 3 * 12:
        fail("paint (peg) faces %d" % n_p)


def chk_arm(bvh, ob, spec, notes, fail):
    def side(z):
        return _ray(bvh, 10.0, 0.0, z, (-1, 0, 0))
    _expect(notes, fail, "rod radius (z 5)", (side(5.0) or (None,))[0], 1.25, 0.12)
    _expect(notes, fail, "grip bulb radius (z -20.5)", (side(-20.5) or (None,))[0], 2.0, 0.15)
    _expect(notes, fail, "grip waist radius (z -16.4)", (side(-16.4) or (None,))[0], 1.35, 0.15)
    h = _ray(bvh, 0.0, -10.0, 21.0, (0, 1, 0))
    _expect(notes, fail, "pivot knuckle face y (z 21)", h and h[1], -1.5, 0.15)
    n_w = sum(1 for p in ob.data.polygons if p.material_index == 1)
    notes.append("Wood (grip) faces %d" % n_w)
    if n_w < 60:
        fail("grip faces %d" % n_w)
    zw = [(ob.matrix_world @ p.center).z for p in ob.data.polygons if p.material_index == 1]
    # the grip is at mesh -Z (the arm component is rotated pitch 90, so -Z is the free end): all wood below the iron rod's centre height
    sc = bpy.context.scene.unit_settings.scale_length * 100.0
    zw_ue = [c * sc for c in zw]
    notes.append("wooden grip z range %.1f..%.1f" % (min(zw_ue), max(zw_ue)))
    if max(zw_ue) > -10.0 or min(zw_ue) < -22.6:
        fail("the grip must sit at mesh z -22.5..-10.5, found %.1f..%.1f" % (min(zw_ue), max(zw_ue)))


def chk_weight(bvh, ob, spec, notes, fail):
    """R2-A2 squat cast-iron ball O11 (z 9.9), seam band, collar ring on the -X side, no chain."""
    h = _ray(bvh, 15.0, 0.0, 0.0, (-1, 0, 0))
    _expect(notes, fail, "ball + seam radius x (z 0)", h and h[0], 5.62, 0.15)
    h = _ray(bvh, 15.0, 0.0, 2.0, (-1, 0, 0))
    _expect(notes, fail, "ball radius x (z 2)", h and h[0], 5.03, 0.2)
    h = _ray(bvh, 0.0, 0.0, -20.0, (0, 0, 1))
    _expect(notes, fail, "ball bottom z (squat)", h and h[2], -4.95, 0.2)
    h = _ray(bvh, 0.0, 0.0, 20.0, (0, 0, -1))
    _expect(notes, fail, "ball top z (no chain)", h and h[2], 4.95, 0.2)
    h = _ray(bvh, -15.0, 3.0, 0.0, (1, 0, 0))
    _expect(notes, fail, "collar face x (y 3)", h and h[0], -5.8, 0.2)
    h = _ray(bvh, -15.0, 0.0, 0.0, (1, 0, 0))
    _expect(notes, fail, "through the collar bore to the ball x", h and h[0], -5.62, 0.25)


def chk_notchstop(bvh, ob, spec, notes, fail):
    n_p = [p for p in ob.data.polygons if p.material_index == 1]
    nrm = [(ob.matrix_world.to_3x3() @ p.normal).normalized() for p in n_p]
    notes.append("Paint faces: %d" % len(n_p))
    if len(n_p) < 2:
        fail("paint faces missing")
    # file x = UE x, file y mirrored: paint faces must point +X (front) or +Z (top) only
    if any(not (n.x > 0.9 or n.z > 0.9) for n in nrm):
        fail("a paint face does not point +X / +Z")
    if not any(n.x > 0.9 for n in nrm):
        fail("no paint face on the +X (front) side")


def chk_gobo(bvh, ob, spec, notes, fail):
    rp = os.path.join(HERE, "..", "..", "..", "SourceArt", "Props", "Procedural", "R2", "props_report_R2.json")
    want_area = None
    bb = None
    try:
        for r in json.load(open(rp)):
            if r["name"] == "SM_LB_Gobo_RoofHole":
                want_area = r["extra"]["area_after_offset"]
                bb = (r["extra"]["bbox_y"], r["extra"]["bbox_z"])
    except Exception as e:                                                  # report missing: size checks only
        notes.append("no report (%s)" % e)
    step = 0.5
    n = 0
    open_pts = []
    for iy in range(-108, 109):
        for iz in range(-108, 109):
            y, z = iy * step, iz * step
            if _ray(bvh, 5.0, y, z, (-1, 0, 0)) is None:
                open_pts.append((y, z))
    area = len(open_pts) * step * step
    notes.append("open area %.1f cm2 (report %s)" % (area, want_area))
    if want_area is not None and abs(area - want_area) > 0.03 * want_area:
        fail("open area %.1f differs from the outline area %.1f by more than 3 %%" % (area, want_area))
    if not 600.0 < area < 2000.0:
        fail("open area %.1f outside 600..2000" % area)
    ys = [p[0] for p in open_pts]
    zs = [p[1] for p in open_pts]
    notes.append("open bbox y %.1f..%.1f z %.1f..%.1f" % (min(ys), max(ys), min(zs), max(zs)))
    if bb is not None and (abs(min(ys) - bb[0][0]) > 0.6 or abs(max(ys) - bb[0][1]) > 0.6 or abs(min(zs) - bb[1][0]) > 0.6 or abs(max(zs) - bb[1][1]) > 0.6):
        fail("open bbox differs from the report bbox")
    h = _ray(bvh, 5.0, 50.0, 50.0, (-1, 0, 0))
    _expect(notes, fail, "plate face x (corner)", h and h[0], 1.0, 0.05)


R2_CHECKS = {"bellwheel": chk_bellwheel, "dl_backplate": chk_backplate, "dl_quadrant": chk_quadrant, "dl_arm": chk_arm, "dl_weight": chk_weight,
             "dl_notchstop": chk_notchstop, "gobo": chk_gobo}


def structural(short, spec, ob, ucx, fail, res):
    """Geometry checks that the bounds cannot show (arch brace, roof plane, seat height, altar core and hole...)."""
    kind = spec.get('struct')
    if not kind:
        return
    if kind == "shaft":
        shaft_checks(spec, ob, fail, res)
        return
    bvh, bm = _bvh(ob)
    notes = []
    if kind == "truss":
        zt = lambda y: 1265.0 - (965.0 / 810.0) * abs(y)
        for y in (-600.0, -400.0, 400.0, 600.0):                       # rafter top faces on the roof plane (through (+-810, 300) and (0, 1265))
            h = _ray(bvh, 0.0, y, 1400.0, (0, 0, -1))
            ok = h is not None and abs(h[2] - zt(y)) < 1.6
            notes.append("rafter top Y%+d: %s (plane %.1f)" % (y, "%.1f" % h[2] if h else None, zt(y)))
            if not ok:
                fail("rafter top at Y %g is %s, roof plane %.1f" % (y, h and round(h[2], 1), zt(y)))
        for sg in (-1, 1):                                              # arch brace intrados: circle r 783.9 around (-sg 78.9, 50)
            for y in (300.0, 500.0):
                yy = sg * y
                h = _ray(bvh, 0.0, yy, 0.0, (0, 0, 1))
                zi = 50.0 + math.sqrt(783.9 ** 2 - (yy + sg * 78.9) ** 2)
                ok = h is not None and abs(h[2] - zi) < 1.6
                notes.append("brace intrados Y%+d: %s (r=783.9 circle %.1f)" % (yy, "%.1f" % h[2] if h else None, zi))
                if not ok:
                    fail("arch brace intrados at Y %g is %s, expected %.1f" % (yy, h and round(h[2], 1), zi))
        h = _ray(bvh, 0.0, 200.0, 940.0, (0, 0, -1))                    # collar top (start below the rafter underside)
        notes.append("collar top: %s (850)" % (("%.1f" % h[2]) if h else None))
        if h is None or abs(h[2] - 850.0) > 1.0:
            fail("collar top %s expected 850" % (h and round(h[2], 1)))
    elif kind == "pew":
        for x in (-20.0, -10.0, 0.0, 10.0, 20.0):                     # seat top Z 45 over X -20..20 (note sits on it)
            h = _ray(bvh, x, -87.0, 200.0, (0, 0, -1))
            notes.append("seat top X%+d: %s" % (x, ("%.2f" % h[2]) if h else None))
            if h is None or not (44.4 <= h[2] <= 45.05):
                fail("seat top at X %g is %s (expected 45)" % (x, h and round(h[2], 2)))
        h = _ray(bvh, -24.5, 0.0, 200.0, (0, 0, -1))
        notes.append("back top: %s (95)" % (("%.2f" % h[2]) if h else None))
        if h is None or h[2] < 94.4:
            fail("back top %s expected 95" % (h and round(h[2], 2)))
    elif kind == "altar":
        # hollow core + O84 hole: a vertical ray through the centre must pass the whole altar; the wings carry the only collision
        for (x, y) in ((0.0, 0.0), (30.0, 0.0), (-30.0, 20.0), (0.0, -35.0)):
            h = _ray(bvh, x, y, 150.0, (0, 0, -1))
            notes.append("centre ray (%g,%g): %s" % (x, y, h))
            if h is not None:
                fail("vertical ray at (%g, %g) hits the altar at Z %.1f (hole / core must be open)" % (x, y, h[2]))
        h = _ray(bvh, -49.0, 0.0, 50.0, (0, 0, 1))                      # inside the core, looking up: mensa underside at Z 91
        notes.append("core ceiling: %s (91)" % (("%.1f" % h[2]) if h else None))
        if h is None or abs(h[2] - 91.0) > 1.5:
            fail("core ceiling %s expected 91" % (h and round(h[2], 1)))
        h = _ray(bvh, -200.0, 0.0, 60.0, (1, 0, 0))                     # front face of the centre panel at X -52
        notes.append("front panel face: %s (-52)" % (("%.1f" % h[0]) if h else None))
        if h is None or abs(h[0] + 52.0) > 1.0:
            fail("centre front face %s expected -52" % (h and round(h[0], 1)))
        for u in ucx:                                                   # UCX only on the wings: |Y| >= 53.5
            ys = [p.y for p in VK.ue_coords(u)]
            if min(abs(v) for v in ys) < 53.5 or min(ys) * max(ys) > 0 and False:
                fail("%s reaches the centre (Y %.1f..%.1f)" % (u.name, min(ys), max(ys)))
            if min(ys) < 0 < max(ys):
                fail("%s spans Y = 0" % u.name)
    elif kind == "bay":
        def rayhit(x, z, want, label, tol=1.6):
            h = _ray(bvh, x, 60.0, z, (0, -1, 0))
            notes.append("%s: %s (want %.1f)" % (label, ("%.2f" % h[1]) if h else None, want))
            if h is None or abs(h[1] - want) > tol:
                fail("%s hit y %s, expected %.1f" % (label, h and round(h[1], 2), want))
        rayhit(0.0, 160.0, 0.0, "front face between the tiers (z 160)", 1.6)
        rayhit(0.0, 400.0, 0.0, "front face above the niches (z 400)", 1.6)
        rayhit(0.0, 90.0, -60.0, "tier 1 niche back", 1.6)
        rayhit(150.0, 230.0, -60.0, "tier 2 niche back (x 150)", 1.6)
        rayhit(-160.0, 90.0, -60.0, "tier 1 niche back (x -160)", 1.6)
        rayhit(180.0, 90.0, 0.0, "wall beside the niche (x 180, z 90)", 1.6)
        rayhit(0.0, 42.0, 6.0, "sill band 1 (z 42) proud 6", 1.4)
        rayhit(0.0, 181.0, 6.0, "sill band 2 (z 181) proud 6", 1.4)
        rayhit(0.0, 141.0, 6.0, "lintel band 1 proud 6", 1.4)
        rayhit(0.0, 20.0, 4.0, "plinth band proud 4", 1.4)
    elif kind == "stair":
        worst = 0.0
        for n in range(40):
            h = _ray(bvh, 30.0 * n + 15.0, 0.0, 700.0, (0, 0, -1))
            want = 15.0 * (n + 1)
            if h is None or abs(h[2] - want) > 1.2:
                fail("step %d ray hits %s, expected %.1f +-1.2" % (n, h and round(h[2], 2), want))
            else:
                worst = max(worst, abs(h[2] - want))
        notes.append("40 downward rays at (30n+15, 0): max deviation from 15(n+1) = %.2f (limit 1.2)" % worst)
        h = _ray(bvh, -50.0, 0.0, 7.0, (1, 0, 0))
        notes.append("riser face of step 0 at x %s (0)" % (("%.2f" % h[0]) if h else None))
        if h is None or abs(h[0]) > 1.0:
            fail("riser face of step 0 at x %s expected 0" % (h and round(h[0], 2)))
    elif kind == "sarco_b":
        h = _ray(bvh, -134.0, 0.0, 120.0, (0, 0, -1))
        notes.append("cavity visible at the -X end: floor hit z %s (20)" % (("%.1f" % h[2]) if h else None))
        if h is None or abs(h[2] - 20.0) > 1.5:
            fail("cavity floor at the -X end z %s expected 20 (lid must leave the end open)" % (h and round(h[2], 1)))
        n_ch = sum(1 for p in ob.data.polygons if p.material_index == 1)
        notes.append("Charred faces: %d" % n_ch)
        if n_ch < 20:
            fail("too few Charred faces (%d)" % n_ch)
    elif kind == "bonebin":
        h = _ray(bvh, 0.0, 0.0, 100.0, (0, 0, -1))
        notes.append("inner floor z %s (30)" % (("%.1f" % h[2]) if h else None))
        if h is None or abs(h[2] - 30.0) > 1.3:
            fail("bone-bin inner floor %s expected 30" % (h and round(h[2], 1)))
    elif kind == "corbel":
        for z, want in ((7.0, 30.0), (22.0, 42.0), (38.0, 55.0)):
            h = _ray(bvh, 0.0, 90.0, z, (0, -1, 0))
            notes.append("course z %g projects to y %s (%g)" % (z, ("%.1f" % h[1]) if h else None, want))
            if h is None or abs(h[1] - want) > 1.4:
                fail("corbel course z %g projects to %s expected %g" % (z, h and round(h[1], 1), want))
    elif kind == "boards":
        cnt, prev = 0, False
        for i in range(0, 501):
            y = -125.0 + i * 0.5
            hit = _ray(bvh, -100.0, y, 20.0, (0, 0, -1)) is not None
            if hit and not prev:
                cnt += 1
            prev = hit
        notes.append("boards crossed along Y at x -100: %d (expected %d)" % (cnt, spec['n_boards']))
        if cnt != spec['n_boards']:
            fail("%d boards at x -100, expected %d" % (cnt, spec['n_boards']))
    elif kind == "roots":
        notes.append("tris %d, bounds z %.1f..%.1f" % (res['tris'], ob.bound_box[0][2], ob.bound_box[6][2]))
    elif kind == "portcullis":
        def count(scan):
            c, prev = 0, False
            for h in scan:
                if h and not prev:
                    c += 1
                prev = h
            return c
        n_x = count(_ray(bvh, -155.0 + i * 0.5, 40.0, 300.0, (0, -1, 0)) is not None for i in range(0, 621))
        n_z = count(_ray(bvh, 16.0, 40.0, 20.0 + i * 0.5, (0, -1, 0)) is not None for i in range(0, 1041))
        notes.append("vertical members crossed at z 300: %d (9 bars + 2 rails = 11); flat bars crossed at x 16: %d (7)" % (n_x, n_z))
        if n_x != 11:
            fail("%d vertical members at z 300, expected 11" % n_x)
        if n_z != 7:
            fail("%d flat bars at x 16, expected 7" % n_z)
        tip = _ray(bvh, 0.0, 0.0, -5.0, (0, 0, 1))
        notes.append("spike tip z %s (0)" % (("%.2f" % tip[2]) if tip else None))
        if tip is None or abs(tip[2]) > 0.6:
            fail("spike tip at z %s expected 0" % (tip and round(tip[2], 2)))
    elif kind == "rubble":
        miss = 0
        tot = 0
        xmin = 1e9
        for y in (-180.0, -120.0, -60.0, 0.0, 60.0, 120.0, 180.0):
            for z in (40.0, 120.0, 200.0, 280.0, 360.0, 440.0, 520.0):
                h = _ray(bvh, -200.0, y, z, (1, 0, 0))
                tot += 1
                if h is None:
                    miss += 1
                else:
                    xmin = min(xmin, h[0])
        notes.append("%d/%d horizontal rays from -X hit the mass (no see-through), first hit x >= %.1f" % (tot - miss, tot, xmin))
        if miss:
            fail("%d of %d rays pass through the rubble" % (miss, tot))
        if xmin < -55.5:
            fail("a face reaches x %.1f (< -55)" % xmin)
        n_w = sum(1 for p in ob.data.polygons if p.material_index == 1)
        notes.append("Wood faces (beam): %d" % n_w)
        if n_w < 50:
            fail("broken beam (Wood slot) missing")
    elif kind == "crank":
        h = _ray(bvh, -17.5, 3.5, 40.0, (0, 0, -1))
        notes.append("boss rim z %s (12)" % (("%.1f" % h[2]) if h else None))
        if h is None or abs(h[2] - 12.0) > 1.2:
            fail("boss rim z %s expected 12" % (h and round(h[2], 1)))
        n_w = sum(1 for p in ob.data.polygons if p.material_index == 1)
        if n_w < 10:
            fail("wooden handle (slot 1) missing")
    elif kind == "capstan":
        for (x, y, z, want, lab) in ((0.0, 0.0, 60.0, 25.0, "top boss"), (50.0, 0.0, 60.0, 15.5, "bar X top"), (0.0, 50.0, 60.0, 15.5, "bar Y top"), (20.0, 20.0, 60.0, 23.0, "drum top")):
            h = _ray(bvh, x, y, z, (0, 0, -1))
            notes.append("%s z %s (%.1f)" % (lab, ("%.1f" % h[2]) if h else None, want))
            if h is None or abs(h[2] - want) > 1.5:
                fail("%s z %s expected %.1f" % (lab, h and round(h[2], 1), want))
    elif kind == "plaque":
        h = _ray(bvh, 0.0, 60.0, 0.0, (0, -1, 0))
        notes.append("opening clear: %s" % ("blocked at y %.1f" % h[1] if h else "yes"))
        if h is not None:
            fail("the opening 250 x 175 is blocked (hit y %.1f)" % h[1])
        for x, want in ((130.0, 10.0), (133.5, 6.0)):
            h = _ray(bvh, x, 60.0, 0.0, (0, -1, 0))
            notes.append("frame step at x %g: y %s (%g)" % (x, ("%.1f" % h[1]) if h else None, want))
            if h is None or abs(h[1] - want) > 1.3:
                fail("frame step at x %g y %s expected %g" % (x, h and round(h[1], 1), want))
    elif kind == "winch":
        for x, lab in ((0.0, "top beam top"), (110.0, "post/beam top")):
            h = _ray(bvh, x, 0.0, 300.0, (0, 0, -1))
            notes.append("%s z %s (250)" % (lab, ("%.1f" % h[2]) if h else None))
            if h is None or abs(h[2] - 250.0) > 1.2:
                fail("%s z %s expected 250" % (lab, h and round(h[2], 1)))
        h = _ray(bvh, 0.0, -80.0, 170.0, (0, 1, 0))
        notes.append("drum side at y %s (-22)" % (("%.1f" % h[1]) if h else None))
        if h is None or abs(h[1] + 22.0) > 2.5:
            fail("drum side y %s expected about -22" % (h and round(h[1], 1)))
    elif kind in R2_CHECKS:
        R2_CHECKS[kind](bvh, ob, spec, notes, fail)
    elif kind == "shell_cyl":
        h = _ray(bvh, 0.0, 0.0, -10.0, (0, 0, 1))                        # open bottom: first hit is the cap underside at Z 50
        notes.append("cap underside: %s" % (("%.1f" % h[2]) if h else None))
        if h is None or abs(h[2] - 50.0) > 1.0:
            fail("shell cap underside %s expected 50 (open bottom, 1 cm wall)" % (h and round(h[2], 1)))
    elif kind == "backdrop":
        n = ob.data.polygons[0].normal
        notes.append("normal %.2f %.2f %.2f" % (n.x, n.y, n.z))
        if n.x > -0.9:
            fail("backdrop normal %s should face -X" % (tuple(round(v, 2) for v in n),))
    bm.free()
    res['struct'] = notes


def uv_in_unit(ob, fail, res):
    uvs = ob.data.uv_layers.active.data
    us = [d.uv[0] for d in uvs]
    vs = [d.uv[1] for d in uvs]
    res['uv'] = [round(min(us), 3), round(max(us), 3), round(min(vs), 3), round(max(vs), 3)]
    if min(us) < -0.001 or max(us) > 1.001 or min(vs) < -0.001 or max(vs) > 1.001:
        fail("UVs outside 0..1: %s" % res['uv'])
    if max(us) - min(us) < 0.45 or max(vs) - min(vs) < 0.45:
        fail("UV span too small: %s" % res['uv'])


def check(path, short, spec):
    name = spec.get('prefix', P) + short
    res = dict(name=name, ok=True, fails=[])

    def fail(m):
        res['ok'] = False
        res['fails'].append(m)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    ucx = sorted([o for o in obs if o.name.startswith("UCX_")], key=lambda o: o.name)
    vis = [o for o in obs if not o.name.startswith("UCX_")]
    if len(vis) != 1:
        fail("expected 1 visual mesh, found %d" % len(vis))
        return res
    ob = vis[0]
    pts = VK.ue_coords(ob)
    mn, mx = VK.bounds(pts)
    dims = mx - mn
    res['dims'] = [round(v, 2) for v in dims]
    res['bounds_min'] = [round(v, 2) for v in mn]
    res['tris'] = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    # pivot: XY centre at 0, min Z at 0 (ivy cards: X centre at 0, back plane at Y 0); P9 variants via spec['pivot']
    pv = spec.get('pivot')
    if pv == "bay":                                   # x centre, y 0 = front face (body -90..0, bands to +6), z 0 bottom
        if abs((mn.x + mx.x) * 0.5) > TOL:
            fail("pivot: X centre %.2f" % ((mn.x + mx.x) * 0.5))
        if abs(mn.y + 90.0) > TOL or abs(mx.y - 6.0) > TOL:
            fail("pivot: y range %.2f..%.2f (expected -90..6)" % (mn.y, mx.y))
    elif pv == "riser":                               # x 0 = riser face of step 0, y centre, z 0 floor
        if abs(mn.x) > TOL:
            fail("pivot: min X %.2f (riser face should be at 0)" % mn.x)
        if abs((mn.y + mx.y) * 0.5) > TOL:
            fail("pivot: Y centre %.2f" % ((mn.y + mx.y) * 0.5))
    elif pv == "centre":                              # bounds centre at the origin on all three axes
        for i, ax in enumerate("XYZ"):
            if abs((mn[i] + mx[i]) * 0.5) > TOL:
                fail("pivot: %s centre %.2f (should be 0)" % (ax, (mn[i] + mx[i]) * 0.5))
    elif pv == "backcentre":                          # x centre, back plane y 0, z centre
        if abs((mn.x + mx.x) * 0.5) > TOL or abs(mn.y) > TOL or abs((mn.z + mx.z) * 0.5) > TOL:
            fail("pivot: back-centre expected (xc, ymin, zc) = 0, got (%.2f, %.2f, %.2f)" % ((mn.x + mx.x) * 0.5, mn.y, (mn.z + mx.z) * 0.5))
    elif pv == "top":                                 # design axis on the origin (XY bounds centre within 8), z max = 0
        if abs(mx.z) > TOL:
            fail("pivot: max Z %.2f (attachment should be 0)" % mx.z)
        for i, ax in enumerate("XY"):
            if abs((mn[i] + mx[i]) * 0.5) > 8.0:
                fail("pivot: %s centre %.2f (design axis should be within 8 of 0)" % (ax, (mn[i] + mx[i]) * 0.5))
    elif pv == "xyfree":                              # XY bounds centre 0, z as built
        for i, ax in enumerate("XY"):
            if abs((mn[i] + mx[i]) * 0.5) > TOL:
                fail("pivot: %s centre %.2f (should be 0)" % (ax, (mn[i] + mx[i]) * 0.5))
    elif spec.get('free_pivot'):
        bm_ = spec['bmin']
        for i, ax in enumerate("XYZ"):
            if abs(mn[i] - bm_[i]) > TOL:
                fail("bounds min %s %.2f vs expected %.2f (pivot placement)" % (ax, mn[i], bm_[i]))
    elif spec.get('wall_pivot'):
        if abs((mn[0] + mx[0]) * 0.5) > TOL:
            fail("pivot: X centre %.2f (should be 0)" % ((mn[0] + mx[0]) * 0.5))
        if abs(mn.y) > TOL:
            fail("pivot: back plane Y min %.2f (should be 0)" % mn.y)
        if dims.y > spec['ymax'] + 0.01:
            fail("depth Y %.2f > %.1f" % (dims.y, spec['ymax']))
    else:
        for i, ax in enumerate("XY"):
            c = (mn[i] + mx[i]) * 0.5
            if abs(c) > TOL:
                fail("pivot: %s centre %.2f (should be 0)" % (ax, c))
    if abs(mn.z) > TOL and not (spec.get('free_pivot') or pv in ("centre", "backcentre", "top", "xyfree")):
        fail("pivot: min Z %.2f (should be 0)" % mn.z)
    if 'zmin_ge' in spec and mn.z < spec['zmin_ge']:
        fail("lowest point Z %.2f below the limit %.1f" % (mn.z, spec['zmin_ge']))
    if 'bounds_le' in spec:
        bl = spec['bounds_le']
        if max(abs(mn.x), abs(mx.x)) > bl[0] + 0.01 or max(abs(mn.y), abs(mx.y)) > bl[1] + 0.01 or mx.z > bl[2] + 0.01:
            fail("bounds exceed the limit x +-%g, y +-%g, z <= %g: %s..%s" % (bl[0], bl[1], bl[2], tuple(round(v, 2) for v in mn), tuple(round(v, 2) for v in mx)))
    n_tr = res['tris']
    if 'tris_max' in spec and n_tr > spec['tris_max']:
        fail("tris %d > cap %d" % (n_tr, spec['tris_max']))
    if 'tris_min' in spec and n_tr < spec['tris_min']:
        fail("tris %d < minimum %d" % (n_tr, spec['tris_min']))
    if ob.matrix_world.translation.length > 1e-4:
        fail("node not at the origin")
    # dimensions
    tol = spec.get('tol', TOL)
    for i, v in enumerate(spec['dims']):
        if v is not None and abs(dims[i] - v) > (spec.get('ztol', tol) if i == 2 else tol):
            fail("dim %s %.2f vs %.2f" % ("XYZ"[i], dims[i], v))
    if 'survey' in spec:                                    # R2-A: within 1 cm of the AABB of the engine primitive the part replaces
        for i, v in enumerate(spec['survey']):
            if v is not None and abs(dims[i] - v) > 1.001:
                fail("dim %s %.2f differs from the surveyed primitive AABB %.2f by more than 1 cm" % ("XYZ"[i], dims[i], v))
    if 'zmax' in spec and dims.z > spec['zmax']:
        fail("dim Z %.2f > %.2f" % (dims.z, spec['zmax']))
    # slots
    names = [m.name.split(".")[0] if m else None for m in ob.data.materials]
    res['slots'] = names
    if names != spec['slots']:
        fail("slots %s expected %s" % (names, spec['slots']))
    # vertex colour / uv / normals
    ca = [a.name for a in ob.data.color_attributes]
    if not ca:
        fail("no colour attribute")
    else:
        bad = sum(1 for d in ob.data.color_attributes[0].data if min(d.color) < 0.99)
        if bad:
            fail("%d non-white vertex colours" % bad)
    if not ob.data.uv_layers:
        fail("no UV layer")
    if len(ob.data.corner_normals) == 0:
        fail("no normals")
    vol = VK.signed_volume(ob)
    res['volume_cm3'] = round(vol, 1)
    if vol <= 0 and not spec.get('open_mesh'):
        fail("non-positive volume (%.1f)" % vol)
    # collision
    res['ucx'] = len(ucx)
    if len(ucx) != spec['ucx']:
        fail("UCX count %d expected %d" % (len(ucx), spec['ucx']))
    for k, u in enumerate(ucx):
        if u.name != "UCX_%s_%02d" % (name, k):
            fail("UCX name %s" % u.name)
        rep = []
        if not VK.is_convex(u, report=rep):
            fail("%s not convex" % u.name)
        b0, b1 = VK.bounds(VK.ue_coords(u))
        env = spec.get('ucx_env')
        if spec.get('ucx_boxes'):
            pass                                                   # compared as a set after the loop
        elif env:
            ex = (env[0] / 2, env[1] / 2)
            want0 = Vector((-ex[0], -ex[1], 0.0))
            want1 = Vector((ex[0], ex[1], env[2]))
            if any(abs(b0[i] - want0[i]) > TOL or abs(b1[i] - want1[i]) > TOL for i in range(3)):
                fail("%s bounds %s..%s differ from the required envelope %s" % (u.name, tuple(round(v, 2) for v in b0), tuple(round(v, 2) for v in b1), env))
        else:
            for i in range(3):
                if b0[i] < mn[i] - TOL or b1[i] > mx[i] + TOL:
                    fail("%s outside the visual bounds on %s" % (u.name, "XYZ"[i]))
    if spec.get('ucx_boxes'):
        want = list(spec['ucx_boxes'])
        got = []
        for u in ucx:
            b0, b1 = VK.bounds(VK.ue_coords(u))
            got.append((b0.x, b1.x, b0.y, b1.y, b0.z, b1.z))
        res['ucx_boxes'] = [tuple(round(v, 2) for v in g) for g in got]
        for w in want:
            hit = next((g for g in got if all(abs(g[i] - w[i]) <= TOL for i in range(6))), None)
            if hit is None:
                fail("no UCX box matches the required %s (got %s)" % (w, res['ucx_boxes']))
            else:
                got.remove(hit)
    structural(short, spec, ob, ucx, fail, res)
    if spec.get('uv01'):
        uv_in_unit(ob, fail, res)
    # ledge: flat 22 x 22 centre exactly at Z 70
    if short.startswith("KeyLedge"):
        zs = [p.z for p in pts if abs(p.x) <= 10.5 and abs(p.y) <= 10.5 and p.z > 60.0]
        res['flat_centre_z'] = [round(min(zs), 3), round(max(zs), 3)] if zs else None
        if not zs or min(zs) < 69.98 or max(zs) > 70.02:
            fail("flat centre not at Z 70: %s" % res['flat_centre_z'])
    return res


def main():
    fbx_dir, js = parse()
    rows = []
    for short, spec in SPEC.items():
        path = os.path.join(fbx_dir, spec.get('subdir', ''), spec.get('prefix', P) + short + ".fbx")
        if not os.path.exists(path):
            rows.append(dict(name=spec.get('prefix', P) + short, ok=False, fails=["missing FBX"]))
            continue
        rows.append(check(path, short, spec))
    print("\n==== VERIFY PROPS SUMMARY ====")
    nm = lambda n: n.replace("SM_LB_Prop_", "").replace("SM_LB_", "")
    print("%-34s %-22s %-7s %-22s %-4s %s" % ("piece", "dims cm (UE)", "tris", "slots", "UCX", "result"))
    for r in rows:
        if 'dims' not in r:
            print("%-34s %s" % (nm(r['name']), "; ".join(r['fails'])))
            continue
        print("%-34s %-22s %-7d %-22s %-4d %s" % (nm(r['name']), "x".join("%g" % d for d in r['dims']), r['tris'],
                                                  ",".join(s.replace("MAT_", "") for s in r['slots']), r['ucx'],
                                                  "PASS" if r['ok'] else "FAIL: " + "; ".join(r['fails'])))
    ok = all(r['ok'] for r in rows)
    print("pieces: %d  passed: %d  failed: %d  => %s" % (len(rows), sum(1 for r in rows if r['ok']), sum(1 for r in rows if not r['ok']), "ALL PASS" if ok else "FAILURES"))
    for r in rows:
        if r.get('struct'):
            print("  %s: %s" % (nm(r['name']), "; ".join(r['struct'])))
    for r in rows:
        if 'flat_centre_z' in r:
            print("  key ledge flat centre Z range: %s" % r['flat_centre_z'])
    if js:
        with open(js, "w") as fh:
            json.dump(rows, fh, indent=1)
    sys.stdout.flush()
    os._exit(0 if ok else 1)


if __name__ == "__main__":
    main()
