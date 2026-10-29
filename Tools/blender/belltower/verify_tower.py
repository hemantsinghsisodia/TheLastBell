"""verify_tower.py -- re-imports every bell tower FBX (P10-3a) in a clean headless Blender and checks it against D1.1 / D1.2 / D1.5.

    blender.exe -b --factory-startup --python Tools/blender/belltower/verify_tower.py -- [--fbx SourceArt/BellTower] [--json out.json]

Per piece (Unreal space, UE_Y = -Blender_Y of the re-imported file, see Tools/blender/kit/README.md):
  bounds / pivot vs the D1 table (+-0.5 cm unless the SPEC says otherwise), node at the origin, exact material slot names and order,
  UCX presence / absence / names / convexity / inside the visual bounds (D1.5: only T10 = 4 post boxes and T12 = 1 convex hull),
  vertex colour white, UV layer, custom normals, positive volume, triangle budget (great bell <= 20k), and the geometric facts of the task:
  tread tops, open risers, broken treads, rail line, landing top and corbels, shaft base faces, belfry floor top + rope hole, door / slit / lancet openings,
  BrokenSW top lines, T12 lip / crown / crack at 180 deg, T11 wheel, T13 rope + sally, T14 missing SW quarter.
Exit code 1 if any check fails.
"""
import json
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "Tools", "blender", "props"))
sys.path.insert(0, os.path.join(ROOT, "Tools", "blender", "kit"))
import verify_props as VP  # noqa: E402  (helpers only; importing builds nothing)
import verify_kit as VK  # noqa: E402
import tw_walls as W  # noqa: E402  (tables only)
import tw_timber as T  # noqa: E402
import tw_bell as B  # noqa: E402

PX = "SM_LB_Tw_"
PP = "SM_LB_Prop_"
FR = T.FR
MASON3 = ["MAT_Masonry", "MAT_Trim", "MAT_Rubble"]
WI = ["MAT_Wood", "MAT_Iron"]
TOL = 0.5

SPEC = {}      # mesh name -> dict(min=(..), max=(..), tol, slots, ucx, [tris_max], [struct])
for _st, _h, _x0 in (("S1", 800.0, None), ("S2", 1700.0, None), ("S3", 1040.0, None)):
    for _f in ("W", "N", "E", "S"):
        L = W.FACE_L[_f]
        over = 40.0 if _f in ("N", "S") else (15.0 if _st == "S3" else 10.0)
        ymax = 55.0 if _st == "S3" else 50.0
        SPEC[PX + "%s_%s" % (_st, _f)] = dict(min=(-over, 0.0, 0.0), max=(L + over, ymax, _h), slots=MASON3, ucx=0, struct="wall", stage=_st, face=_f)
SPEC[PX + "S3_W_BrokenSW"] = dict(min=(0.0, 0.0, 0.0), max=(1015.0, 55.0, 1040.0), slots=MASON3, ucx=0, struct="wall", stage="S3", face="W", broken=True)
SPEC[PX + "S3_S_BrokenSW"] = dict(min=(-40.0, 0.0, 0.0), max=(920.0, 55.0, 1040.0), slots=MASON3, ucx=0, struct="wall", stage="S3", face="S", broken=True)
zt0, zt1 = T.stringer_top(-10.0) - 28.0, T.stringer_top(430.0)
SPEC.update({
    PX + "Roof_BrokenSW": dict(min=(-528.0, -528.0, -300.0), max=(528.0, 528.0, 1288.0), tol=8.0, slots=["MAT_Slate", "MAT_Wood", "MAT_Iron"], ucx=0, struct="roof"),
    PX + "Louvre_130x450": dict(min=(-65.0, 0.0, 0.0), max=(65.0, 30.0, 450.0), slots=["MAT_Wood"], ucx=0, struct="louvre", boards=9),
    PX + "Louvre_130x450_Broken": dict(min=(-65.0, 0.0, 0.0), max=(65.0, 30.0, 450.0), slots=["MAT_Wood"], ucx=0, struct="louvre", boards=7),
    PX + "ShaftBase_420x420x450": dict(min=(-210.0, -210.0, 0.0), max=(210.0, 210.0, 450.0), tol=0.3, slots=MASON3 + ["MAT_Wood"], ucx=0, struct="base"),
    PX + "ShaftPost_20x20x2015": dict(min=(-10.0, -10.0, 0.0), max=(10.0, 10.0, 2015.0), slots=WI, ucx=0),
    PX + "StairFlight_250x420": dict(min=(-10.0, 0.0, zt0), max=(430.0, 258.0, zt1), slots=WI, ucx=0, struct="flight", variant=""),
    PX + "StairFlight_250x420_Closed": dict(min=(-10.0, 0.0, 0.0), max=(430.0, 250.0, zt1), slots=["MAT_Wood"] + ["MAT_Iron"], ucx=0, struct="flight", variant="Closed"),
    PX + "StairFlight_250x420_BrokenA": dict(min=(-10.0, 0.0, zt0), max=(430.0, 258.0, zt1), slots=WI, ucx=0, struct="flight", variant="BrokenA"),
    PX + "StairFlight_250x420_BrokenB": dict(min=(-10.0, 0.0, zt0), max=(430.0, 258.0, zt1), slots=WI, ucx=0, struct="flight", variant="BrokenB"),
    PX + "FlightRail_420": dict(min=(0.0, 0.0, None), max=(420.0, 8.0, FR * 15 + 98.0), slots=["MAT_Wood"], ucx=0, struct="rail"),
    PX + "Landing_250": dict(min=(0.0, 0.0, -60.0), max=(250.0, 250.0, 0.0), slots=["MAT_Wood", "MAT_Masonry"], ucx=0, struct="landing"),
    PX + "BelfryFloor": dict(min=(0.0, 0.0, -35.0), max=(680.0, 920.0, 0.0), slots=WI, ucx=0, struct="floor"),
    PX + "TopRail_670": dict(min=(0.0, -5.0, 0.0), max=(670.0, 5.0, 98.0), slots=["MAT_Wood"], ucx=0, struct="toprail"),
    PX + "TopRail_420": dict(min=(0.0, -5.0, 0.0), max=(420.0, 5.0, 98.0), slots=["MAT_Wood"], ucx=0, struct="toprail"),
    PX + "Partition_250x455": dict(min=(0.0, 0.0, 0.0), max=(250.0, 4.0, 455.0), slots=WI, ucx=0, struct="partition"),
    PX + "BellFrame_A": dict(min=(-165.0, -150.0, 0.0), max=(165.0, 150.0, 380.0), slots=WI, ucx=4, struct="frame"),
    PX + "BellHeadstock_A": dict(min=(-130.0, -178.0, None), max=(134.0, 170.0, 130.0), tol=0.6, slots=WI, ucx=0, struct="head"),
    PP + "GreatBell_A": dict(min=(-105.0, -105.0, -220.0), max=(105.0, 105.0, 0.0), slots=["MAT_Bronze", "MAT_Iron"], ucx=1, tris_max=20000, struct="bell"),
    PP + "BellRope_2610": dict(min=(None, None, -2610.0), max=(None, None, 0.0), slots=["MAT_Rope", "MAT_Sally"], ucx=0, struct="rope"),
})


def parse():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    fbx = os.path.join(ROOT, "SourceArt", "BellTower")
    js = None
    for i, a in enumerate(argv):
        if a == "--fbx":
            fbx = os.path.abspath(argv[i + 1])
        if a == "--json":
            js = os.path.abspath(argv[i + 1])
    return fbx, js


class Ctx:
    def __init__(self, ob, fail, notes):
        self.ob, self.fail, self.notes = ob, fail, notes
        self.bvh, self.bm = VP._bvh(ob)
        self.pts = VK.ue_coords(ob)
        me = ob.data
        self.mat_of_vert = {}
        for p in me.polygons:
            for v in p.vertices:
                self.mat_of_vert.setdefault(v, set()).add(p.material_index)

    def ray(self, o, d):
        return VP._ray(self.bvh, o[0], o[1], o[2], d)

    def down(self, x, y, z0=5000.0):
        h = self.ray((x, y, z0), (0, 0, -1))
        return None if h is None else h[2]

    def ray_mat(self, o, d):
        """Hit position and material index of the first hit (UE space)."""
        sc = bpy.context.scene.unit_settings.scale_length * 100.0
        h = self.bvh.ray_cast(Vector((o[0] / sc, -o[1] / sc, o[2] / sc)), Vector((d[0], -d[1], d[2])))
        if h[0] is None:
            return None, None
        return (h[0].x * sc, -h[0].y * sc, h[0].z * sc), self.ob.data.polygons[h[2]].material_index

    def count_down(self, x, y, z0=5000.0, zmin=-1e9):
        n, z = 0, z0
        while True:
            h = self.ray((x, y, z), (0, 0, -1))
            if h is None or h[2] < zmin:
                return n
            n += 1
            z = h[2] - 0.01

    def verts(self, pred):
        return [p for p in self.pts if pred(p)]


def approx(a, b, t):
    return abs(a - b) <= t


# ---------------------------------------------------------------------------------------------- structural checks
def chk_wall(c, spec, fail, notes):
    stage, face, broken = spec['stage'], spec['face'], spec.get('broken', False)
    L = W.FACE_L[face]
    H = W.STAGE_H[stage]

    def clear(x, z):                     # ray along +y through the whole wall thickness
        return c.ray((x, -5.0, z), (0, 1, 0)) is None

    # slits
    for (nm, cx, cz) in W.SLITS.get((stage, face), []):
        ok = clear(cx, cz) and clear(cx, cz - 45.0) and clear(cx, cz + 45.0) and clear(cx - 7.0, cz) and clear(cx + 7.0, cz)
        blk = (not clear(cx, cz + 56.0)) and (not clear(cx, cz - 56.0)) and (not clear(cx - 14.0, cz)) and (not clear(cx + 14.0, cz))
        if not ok or not blk:
            fail("slit %s at x %g z %g: open=%s walls-around=%s" % (nm, cx, cz, ok, blk))
        notes.append("slit %s open" % nm)
    if stage == "S1" and face == "W":
        for x in (450.0, 470.0, 500.0, 530.0, 550.0):
            for z in (2.0, 100.0, 190.0):
                if not clear(x, z):
                    fail("door not clear at x %g z %g" % (x, z))
        if clear(446.5, 100.0) or clear(553.5, 100.0):
            fail("door jambs are not at x 448 / 552")
        z = 190.0
        while z < 260.0 and clear(500.0, z):
            z += 0.25
        notes.append("door apex at x 500: %.2f (D1: 228)" % z)
        if not approx(z, 228.0, 1.5):
            fail("door apex %.2f != 228" % z)
        z = 150.0
        while z < 260.0 and clear(449.0, z):
            z += 0.25
        notes.append("door head at the jamb (x 449): %.2f (D1: 194..)" % z)
        if z < 194.0:
            fail("door head at the jamb %.2f < 194" % z)
        n_pl = c.verts(lambda p: 448.5 < p.x < 551.5 and p.y > 40.5 and p.z < 60.0)
        if n_pl:
            fail("plinth not interrupted at the door (%d verts)" % len(n_pl))
    if stage == "S3":
        for cx in W.LANCET_X[face]:
            for x in (cx - 55.0, cx - 20.0, cx, cx + 20.0, cx + 55.0):
                for z in (205.0, 400.0, 640.0):
                    if not clear(x, z):
                        fail("lancet at %g not clear at x %g z %g" % (cx, x, z))
            z = 700.0
            while z < 800.0 and clear(cx, z):
                z += 0.25
            if not approx(z, 762.6, 2.0):
                fail("lancet apex at x %g is %.2f (D1: 762.6)" % (cx, z))
            notes.append("lancet x %g apex %.1f" % (cx, z))
        xs = W.LANCET_X[face]
        xm = (xs[0] + xs[1]) / 2.0
        if clear(xm, 400.0):
            fail("no 60 cm mullion between the lancets at x %g" % xm)
    if broken:
        br = W.BREAK[face]
        # top line: highest hit of a ray down at y = 20
        def top(x):
            return c.down(x, 20.0, 1200.0)
        xa_, xb_ = br['xa'], br['xb']
        xs = [min(max(xa_ + (xb_ - xa_) * k / 16.0, 1.0), L - 1.0) for k in range(17)]
        zs = [top(x) for x in xs]
        notes.append("top line z at x %s: %s" % (["%g" % x for x in xs[::4]], ["%s" % (None if z is None else round(z)) for z in zs[::4]]))
        if any(z is None for z in zs):
            fail("break span has holes (no hit on the top line)")
        else:
            za, zb = br['za'], br['zb']
            if abs(zs[0] - za) > 30.0:
                fail("top at the corner end %.1f vs D1 %g" % (zs[0], za))
            if zs[-1] < 1000.0 and zb >= 1040.0 or (zb < 1000.0 and abs(zs[-1] - zb) > 30.0):
                fail("top at the far end %.1f vs D1 %g" % (zs[-1], zb))
            lo = min(za, zb) - 40.0
            if min(zs) < lo or max(zs) > 1046.0:
                fail("top line outside z %.0f..1046: %.1f..%.1f" % (lo, min(zs), max(zs)))
            q = len(zs) // 4
            a, d = sum(zs[:q]) / q, sum(zs[-q:]) / q
            if (zb > za and d < a + 150.0) or (zb < za and a < d + 150.0):
                fail("top line is not %s: quarter means %.0f -> %.0f" % ("rising" if zb > za else "falling", a, d))
            steps = sum(1 for k in range(1, len(zs)) if abs(zs[k] - zs[k - 1]) > 15.0)
            notes.append("jagged steps (>15 cm between samples): %d" % steps)
            if steps < 3:
                fail("break line is not jagged/stepped (%d jumps)" % steps)
        rest = [top(x) for x in ((br['xb'] + 30.0, br['xb'] + 120.0) if br['xb'] < L / 2 else (br['xa'] - 30.0, br['xa'] - 120.0))]
        if any(z is None or abs(z - 1040.0) > 0.5 for z in rest):
            fail("intact part beside the break is not at 1040: %s" % rest)
        xa, xb = min(br['xa'], br['xb']), max(br['xa'], br['xb'])
        corn = c.verts(lambda p: xa + 10.0 <= p.x <= xb - 10.0 and p.y > 41.0 and p.z > 975.0)
        if corn:
            fail("cornice present over the broken span (%d verts)" % len(corn))
        rub = sum(1 for p in c.ob.data.polygons if p.material_index == 2)
        if rub < 20:
            fail("fracture faces (MAT_Rubble) missing: %d polys" % rub)
        notes.append("fracture faces in MAT_Rubble: %d polys" % rub)


def chk_flight(c, spec, fail, notes):
    var = spec['variant']
    # tread tops over the walk band
    worst = 0.0
    for i in range(14):
        tol = 0.1
        x = 30.0 * i + 14.0
        for y in (40.0, 125.0, 185.0):
            if var == "BrokenA" and i == 10 and y == 125.0:
                tol = 0.5
            if var == "BrokenB" and i == 9 and y in (125.0, 185.0):
                tol = 0.3
            z = c.down(x, y, 400.0)
            exp = FR * (i + 1)
            if z is None:
                fail("tread %d: no hit at y %g" % (i, y))
                continue
            worst = max(worst, abs(z - exp))
            if abs(z - exp) > tol + 1e-6:
                fail("tread %d top at (x %.0f, y %g) is %.3f, D1 %.3f" % (i, x, y, z, exp))
    notes.append("14 tread tops, worst error %.3f cm" % worst)
    # open risers: horizontal ray under each tread through the riser opening
    hits = 0
    for i in range(1, 14):
        for y in (25.0, 75.0, 125.0, 175.0, 225.0):
            h = c.ray((30.0 * i - 12.0, y, FR * i + 5.0), (1, 0, 0))
            if h is not None:
                hits += 1
    if var == "Closed":
        if hits < 13 * 5 - 5:
            fail("Closed flight has gaps between the treads (%d/65 rays blocked)" % hits)
        notes.append("riser rays blocked: %d/65 (closed)" % hits)
    else:
        if hits:
            fail("open risers are not open: %d/65 rays blocked" % hits)
        notes.append("riser rays blocked: %d/65 (open)" % hits)
    # broken treads
    if var in ("BrokenA", "BrokenB"):
        ib = 6 if var == "BrokenA" else 3
        x = 30.0 * ib + 8.0
        for xx in (x, x + 8.0, x + 14.0):
            for y in (212.0, 220.0, 230.0, 240.0):
                if c.down(xx, y, 400.0) is not None:
                    fail("tread %d has geometry at x %.0f y %g (should be gone y 210..250)" % (ib, xx, y))
        h = [c.down(x + dx, y, 400.0) for dx in (0.0, 14.0) for y in (150.0, 185.0)]
        if any(v is None for v in h):
            fail("tread %d lost its inner part" % ib)
        mx = max(p.y for p in c.pts if 30.0 * ib - 3.0 <= p.x <= 30.0 * ib + 31.0 and abs(p.z - FR * (ib + 1)) < 1.0 and p.y < 235.0)
        notes.append("tread %d max y %.2f" % (ib, mx))
        if mx > 210.0:
            fail("tread %d reaches y %.2f > 210" % (ib, mx))
        itb = 10 if var == "BrokenA" else 9
        ys = (60.0, 180.0) if var == "BrokenA" else (40.0, 125.0)
        zz = [c.down(30.0 * itb + 14.0, y, 400.0) for y in ys]
        notes.append("tread %d halves: %s" % (itb, zz))
        if any(z is None or abs(z - FR * (itb + 1)) > 0.5 for z in zz):
            fail("tread %d halves not within 0.5 of the tread top: %s" % (itb, zz))
        ysplit = 120.0 if var == "BrokenA" else 80.0
    # stringers: inclined, y 0..8 and 242..250
    for y in (4.0, 246.0):
        for x in (0.0, 200.0, 420.0):
            z = c.down(x, y, 600.0)
            if z is None or abs(z - T.stringer_top(x)) > 0.6:
                fail("stringer top at x %g y %g is %s, expected %.2f" % (x, y, z, T.stringer_top(x)))


def chk_rail(c, spec, fail, notes):
    worst = 0.0
    for x in range(10, 411, 20):
        z = c.down(float(x), 4.0, 2000.0)
        exp = FR * (x / 30.0 + 1.0) + 98.0
        if z is None:
            fail("rail: no handrail at x %d" % x)
            continue
        worst = max(worst, abs(z - exp))
        if abs(z - exp) > 0.5:
            fail("handrail top at x %d is %.2f, D1 %.2f" % (x, z, exp))
    notes.append("handrail top line worst error %.3f cm" % worst)
    mn = min(p.y for p in c.pts)
    mx = max(p.y for p in c.pts)
    if mn < -0.01 or mx > 10.0:
        fail("rail not inside y 0..10: %.2f..%.2f" % (mn, mx))
    # mid-rail top 50 below the handrail top
    for x in (60.0, 210.0, 350.0):
        top = FR * (x / 30.0 + 1.0) + 98.0
        h1 = c.ray((x, -10.0, top - 50.0 - 2.0), (0, 1, 0))
        h2 = c.ray((x, -10.0, top - 50.0 + 2.0), (0, 1, 0))
        if h1 is None or h2 is not None:
            fail("mid-rail top is not 50 below the handrail at x %g (hits %s / %s)" % (x, h1, h2))
    # posts at x 140 / 280
    for x in (140.0, 280.0):
        h = c.ray((x, -10.0, FR * (x / 30.0 + 1.0) + 98.0 - 25.0), (0, 1, 0))
        if h is None:
            fail("no post at x %g" % x)


def chk_landing(c, spec, fail, notes):
    worst = 0.0
    for k in range(10):
        for x in (10.0, 70.0, 130.0, 190.0, 240.0):
            y = 25.0 * k + 12.5
            z = c.down(x, y, 100.0)
            if z is None or abs(z) > 0.2:
                fail("landing top at (%g, %g) is %s" % (x, y, z))
            else:
                worst = max(worst, abs(z))
    notes.append("landing top worst error %.3f cm" % worst)
    # corbels: connected MAT_Masonry (slot 1) shells, only under the x = 250 and y = 250 edges
    me = c.ob.data
    parent = {}
    key = {i: (round(p.x, 1), round(p.y, 1), round(p.z, 1)) for i, p in enumerate(c.pts)}      # the importer splits vertices per normal: merge by position

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for p in me.polygons:
        if p.material_index == 1:
            ks = [key[v] for v in p.vertices]
            for k2 in ks[1:]:
                parent[find(ks[0])] = find(k2)
    comps = {}
    for p in me.polygons:
        if p.material_index == 1:
            comps.setdefault(find(key[p.vertices[0]]), set()).update(p.vertices)
    n_x = n_y = 0
    for vs in comps.values():
        xs = [c.pts[v].x for v in vs]
        ys = [c.pts[v].y for v in vs]
        zs = [c.pts[v].z for v in vs]
        if min(xs) >= 209.0 and max(xs) <= 250.5:
            n_x += 1
        elif min(ys) >= 209.0 and max(ys) <= 250.5:
            n_y += 1
        else:
            fail("a corbel is not under the x = 250 / y = 250 edge: x %.0f..%.0f y %.0f..%.0f" % (min(xs), max(xs), min(ys), max(ys)))
        if min(zs) < -60.5 or max(zs) > -24.5:
            fail("corbel z %.1f..%.1f (D1 -60..-25)" % (min(zs), max(zs)))
    notes.append("corbels: %d under x = 250, %d under y = 250" % (n_x, n_y))
    if n_x != 2 or n_y != 2:
        fail("corbel count %d + %d (D1: 2 + 2)" % (n_x, n_y))


def chk_base(c, spec, fail, notes):
    xs = [p.x for p in c.pts]
    ys = [p.y for p in c.pts]
    notes.append("outer faces x %.2f..%.2f y %.2f..%.2f" % (min(xs), max(xs), min(ys), max(ys)))
    if max(max(xs), max(ys)) > 210.3 or min(min(xs), min(ys)) < -210.3:
        fail("geometry outside +-210")
    # coping: z 430..450 inward only (outer faces stay at +-210, inner edge 172 = 3 inside the 175 wall face)
    cop = c.verts(lambda p: p.z > 431.0)
    outer = max(max(abs(p.x), abs(p.y)) for p in cop)
    rs = [c.ray((0.0, 0.0, 440.0), d) for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0))]
    inner = min(max(abs(h[0]), abs(h[1])) for h in rs if h is not None) if all(h is not None for h in rs) else 0.0
    notes.append("coping outer %.2f inner edge %.2f" % (outer, inner))
    if outer > 210.3:
        fail("coping projects outward (%.2f)" % outer)
    if not approx(inner, 172.0, 0.4):
        fail("coping inner edge %.2f (D1: 3 cm inward of the 175 wall face = 172)" % inner)
    h = c.ray((0.0, 0.0, 300.0), (1, 0, 0))
    if h is None or not (175.0 <= h[0] <= 177.0):
        fail("inner wall face at z 300 is %s (expected 175..177)" % (h,))
    h = c.ray((0.0, 0.0, 440.0), (1, 0, 0))
    if h is None or not approx(h[0], 172.0, 0.4):
        fail("coping inner face at z 440 is %s" % (h,))
    # rubble floor z 0..40, broken treads lying on it
    fl = [p.z for p in c.pts if abs(p.x) < 170 and abs(p.y) < 170 and p.z < 60.0]
    notes.append("rubble top %.1f" % max(fl))
    if max(fl) > 40.5:
        fail("rubble floor higher than 40 (%.1f)" % max(fl))
    tre = sum(1 for p in c.ob.data.polygons if p.material_index == 3)
    if tre < 12:
        fail("broken treads (MAT_Wood) missing")
    rub = sum(1 for p in c.ob.data.polygons if p.material_index == 2)
    if rub < 100:
        fail("rubble faces missing")


def chk_floor(c, spec, fail, notes):
    worst = 0.0
    rects = [(0.0, 250.0, 0.0, 920.0), (250.0, 670.0, 670.0, 920.0), (250.0, 670.0, 250.0, 670.0)]
    n = 0
    for (x0, x1, y0, y1) in rects:
        for k in range(8):
            for m in range(8):
                x = x0 + 4.0 + (x1 - x0 - 8.0) * k / 7.0
                y = y0 + 4.0 + (y1 - y0 - 8.0) * m / 7.0
                if 488.0 <= x <= 522.0 and 278.0 <= y <= 312.0:
                    continue
                z = c.down(x, y, 100.0)
                n += 1
                if z is None or abs(z) > 0.2:
                    fail("floor top at (%.0f, %.0f) is %s" % (x, y, z))
                else:
                    worst = max(worst, abs(z))
    notes.append("floor top: %d samples, worst %.3f cm" % (n, worst))
    for (x, y) in ((492.0, 283.0), (505.0, 295.0), (518.0, 307.0), (492.0, 307.0), (518.0, 283.0)):
        if c.down(x, y, 100.0) is not None:
            fail("rope hole blocked at (%g, %g)" % (x, y))
    for (x, y) in ((488.0, 295.0), (522.0, 295.0), (505.0, 278.5), (505.0, 311.5)):
        z = c.down(x, y, 100.0)
        if z is None or z < -0.3:
            fail("floor missing just outside the rope hole at (%g, %g)" % (x, y))
    for (x, y) in ((300.0, 100.0), (600.0, 150.0)):
        if c.down(x, y, 100.0) is not None:
            fail("floor present outside the 3 rectangles at (%g, %g)" % (x, y))
    # rectangle 2/3: beams under the core-top rectangle
    for y in (340.0, 450.0, 560.0):
        h = c.ray((400.0, y, -50.0), (0, 0, 1))
        if h is None or not (-36.0 <= h[2] <= -5.0):
            fail("no beam under the core top at y %g" % y)


def chk_toprail(c, spec, fail, notes):
    L = spec['max'][0]
    z = c.down(L / 2.0 + 30.0, 0.0, 300.0)
    if z is None or not approx(z, 98.0, 0.3):
        fail("handrail top %s (D1: 98)" % z)
    xm = L / 2.0 + 10.0
    h1 = c.ray((xm, -20.0, 49.0), (0, 1, 0))
    h2 = c.ray((xm, -20.0, 51.0), (0, 1, 0))
    if h1 is None or h2 is not None:
        fail("mid-rail top is not 50 (hits %s / %s)" % (h1, h2))
    n = int(math.ceil((L - 10.0) / 120.0)) + 1
    posts = 0
    prev = None
    for k in range(n):
        xc = 5.0 + (L - 10.0) * k / (n - 1)
        h = c.ray((xc, -20.0, 20.0), (0, 1, 0))
        if h is not None and abs(h[1] + 5.0) < 0.6:
            posts += 1
        if prev is not None and xc - prev > 120.01:
            fail("post spacing %.1f > 120" % (xc - prev))
        prev = xc
    if posts < n:
        fail("posts missing (%d/%d)" % (posts, n))
    notes.append("posts %d, spacing <= 120" % posts)


def chk_partition(c, spec, fail, notes):
    for z in (150.0, 250.0, 400.0):
        if c.ray((160.0, -10.0, z), (0, 1, 0)) is not None and not (90.0 < z < 100.0 or 335.0 < z < 365.0):
            fail("board at x 160 z %g should be missing" % z)
        if c.ray((100.0, -10.0, z), (0, 1, 0)) is None:
            fail("no board at x 100 z %g" % z)
    h = c.ray((160.0, -10.0, 250.0), (0, 1, 0))
    notes.append("x 160 / z 250 ray: %s (gap shows the dark behind)" % (h,))
    h = c.ray((160.0, -10.0, 95.0), (0, 1, 0))
    if h is None:
        fail("rail behind the missing board not found")
    if c.ray((160.0, -10.0, 250.0), (0, 1, 0)) is not None:
        fail("board x 150..170 not missing")


def chk_louvre(c, spec, fail, notes):
    n = c.count_down(0.0, 15.0, 600.0) // 2
    notes.append("boards crossed by a vertical line at y 15: %d" % n)
    if n != spec['boards']:
        fail("%d boards, expected %d" % (n, spec['boards']))
    if spec['boards'] == 9:
        z_in = c.down(0.0, 3.0, 600.0)
        z_out = c.down(0.0, 27.0, 600.0)
        notes.append("top board: z %.1f at y 3, %.1f at y 27" % (z_in, z_out))
        if not (z_out < z_in - 8.0):
            fail("boards do not slope with the outer edge lower")
        zs = []
        z = 600.0
        while True:
            h = c.ray((0.0, 15.0, z), (0, 0, -1))
            if h is None:
                break
            zs.append(h[2])
            z = h[2] - 0.01
        tops = zs[0::2]
        d = [tops[i] - tops[i + 1] for i in range(len(tops) - 1)]
        if any(abs(v - 50.0) > 0.5 for v in d):
            fail("board spacing %s != 50" % ["%.1f" % v for v in d])
    else:
        z = 600.0
        zs = []
        while True:
            h = c.ray((0.0, 15.0, z), (0, 0, -1))
            if h is None:
                break
            zs.append(h[2])
            z = h[2] - 0.01
        notes.append("hit heights %s" % ["%.0f" % v for v in zs])


def chk_frame(c, spec, fail, notes):
    want = [(sx * 140.0 - 12.5, sx * 140.0 + 12.5, sy * 135.0 - 12.5, sy * 135.0 + 12.5, 0.0, 365.0) for sx in (-1, 1) for sy in (-1, 1)]
    got = []
    for u in c.ucx:
        pts = VK.ue_coords(u)
        b0, b1 = VK.bounds(pts)
        got.append((b0.x, b1.x, b0.y, b1.y, b0.z, b1.z))
    for w in want:
        hit = next((g for g in got if all(abs(g[i] - w[i]) <= 1.0 for i in range(6))), None)
        if hit is None:
            fail("no UCX post box matches %s (got %s)" % (w, [tuple(round(v, 1) for v in g) for g in got]))
        else:
            got.remove(hit)
    h = c.ray((-165.0, 0.0, 350.0), (1, 0, 0))
    if h is None:
        fail("head sills / cross-ties missing")
    sills = c.ray((0.0, -200.0, 350.0), (0, 1, 0))
    if sills is None or not approx(sills[1], -147.5, 1.0):
        fail("head sill at y -147.5 not found: %s" % (sills,))
    blk = c.down(0.0, 135.0, 600.0)
    notes.append("bearing block top at y 135: z %.1f" % blk)
    if blk is None or not approx(blk, 380.0, 0.5):
        fail("bearing blocks 20 x 30 x 15 on the head sills: top %s (expected 380)" % blk)
    for sx in (-1, 1):
        z = c.down(sx * 140.0, 0.0, 600.0)
        if z is None or not approx(z, 365.0, 1.0):
            fail("cross-tie top at x %g is %s" % (sx * 140.0, z))
    if c.ray((0.0, 0.0, 200.0), (0, 0, 1)) is not None:
        fail("the frame must be open above the floor point under the bell axis")


def chk_head(c, spec, fail, notes):
    wheel = [p for p in c.pts if p.y < -160.0]
    rim = [p for p in wheel if abs(p.y + 170.0) < 7.0 and not (122.0 < p.x < 138.0 and p.z < 12.0)]      # the staple / chain at 3 o'clock is not rim
    r = max(math.hypot(p.x, p.z) for p in rim)
    notes.append("wheel max radius %.2f (D1: O260)" % r)
    if not approx(r, 130.0, 0.5):
        fail("wheel radius %.2f" % r)
    ys = [p.y for p in rim if math.hypot(p.x, p.z) > 118.0]
    notes.append("rim y %.1f..%.1f (plane y -170)" % (min(ys), max(ys)))
    if not (approx(min(ys), -176.0, 0.6) and approx(max(ys), -164.0, 0.6)):
        fail("rim not 12 wide centred on y -170: %.1f..%.1f" % (min(ys), max(ys)))
    beam = c.down(0.0, 0.0, 300.0)
    if beam is None or not approx(beam, 17.5, 1.5):
        fail("headstock top %s (35 x 35 centred on the axle)" % beam)
    hy = [p.y for p in c.pts if abs(p.x) < 18.0 and abs(p.z) < 18.0]
    if max(hy) < 150.0 or min(hy) > -150.0:
        fail("headstock does not span y -150..150")
    # 6 spokes: rays along y at radius 70 every 2 degrees, count the angular groups that hit
    hit = []
    for k in range(180):
        a = math.radians(2.0 * k)
        h = c.ray((70.0 * math.cos(a), -200.0, 70.0 * math.sin(a)), (0, 1, 0))
        hit.append(h is not None and h[1] < -160.0)
    groups = sum(1 for k in range(180) if hit[k] and not hit[k - 1])
    notes.append("spoke groups hit at radius 70: %d" % groups)
    if groups != 6:
        fail("expected 6 spokes, found %d" % groups)
    hub = c.ray((0.0, -200.0, 0.0), (0, 1, 0))
    if hub is None or hub[1] > -160.0:
        fail("wheel hub missing")


def chk_bell(c, spec, fail, notes):
    lip = c.verts(lambda p: p.z < -219.0)
    rl = max(math.hypot(p.x, p.y) for p in lip)
    notes.append("lip radius %.2f at z %.2f" % (rl, min(p.z for p in lip)))
    if not approx(rl, 105.0, 0.3) or not approx(min(p.z for p in lip), -220.0, 0.3):
        fail("lip O%.1f at z %.2f (D1: O210 at -220)" % (2 * rl, min(p.z for p in lip)))
    zmax = max(p.z for p in c.pts)
    if abs(zmax) > 0.5:
        fail("crown top at z %.2f (D1: 0)" % zmax)
    for z0, r0 in ((-35.0, 65.0), (-120.0, 75.0), (-200.0, 98.0)):
        rr = max(math.hypot(p.x, p.y) for p in c.pts if abs(p.z - z0) < 2.0 and math.hypot(p.x, p.y) < r0 + 6.0)
        notes.append("outer radius near z %g: %.1f (D1 %g)" % (z0, rr, r0))
        if not approx(rr, r0, 3.2):
            fail("outer radius near z %g is %.1f, D1 %g" % (z0, rr, r0))
    # wall thickness 6 at the waist, 14 at the sound bow (ray from the axis outwards at 90 deg: outer face minus inner face)
    for z0, tw in ((-120.0, 6.0), (-200.0, 14.0)):
        d = (math.cos(math.radians(90.0)), math.sin(math.radians(90.0)), 0)
        hs = []
        o = (0.0, 20.0, z0)
        for _ in range(6):
            h = c.ray(o, d)
            if h is None:
                break
            hs.append(h[1])
            o = (h[0], h[1] + 0.01, h[2])
        notes.append("wall at z %g: crossings y %s" % (z0, ["%.1f" % v for v in hs]))
        if len(hs) >= 2:
            t = hs[1] - hs[0]
            if abs(t - tw) > 1.2:
                fail("wall thickness at z %g is %.2f (D1 %g)" % (z0, t, tw))
        else:
            fail("could not measure the wall at z %g" % z0)

    def deep(angle_c, half=3.0, zr=(-215.0, -140.0)):
        n = 0
        for p in c.pts:
            if not (zr[0] <= p.z <= zr[1]):
                continue
            a = math.degrees(math.atan2(p.y, p.x)) % 360.0
            if min(abs(a - angle_c), 360.0 - abs(a - angle_c)) <= half and 3.5 <= (B.r_out(p.z) - math.hypot(p.x, p.y)) <= 6.0:
                n += 1
        return n
    n180, n0, n90, n270 = deep(180.0), deep(0.0), deep(90.0), deep(270.0)
    notes.append("groove vertices (depth >= 3.5): 180 deg %d, 0 deg %d, 90 deg %d, 270 deg %d" % (n180, n0, n90, n270))
    if n180 < 8 or n0 or n90 or n270:
        fail("crack groove not only at 180 deg (%d / %d / %d / %d)" % (n180, n0, n90, n270))
    zs = [p.z for p in c.pts if abs(((math.degrees(math.atan2(p.y, p.x)) % 360.0) - 180.0)) <= 3.0 and 3.5 <= (B.r_out(p.z) - math.hypot(p.x, p.y)) <= 6.0 and -215.0 < p.z < -140.0]
    if zs:
        notes.append("crack spans z %.1f..%.1f (from the lip up ~90)" % (min(zs), max(zs)))
        if max(zs) < -220.0 + 70.0:
            fail("crack shorter than ~90 (top at z %.1f)" % max(zs))
    chip = c.verts(lambda p: p.z < -208.0 and abs(p.y) < 6.5 and p.x < -90.0)
    notes.append("V-chip region verts: %d" % len(chip))
    # clapper ball O22 at z -195
    ball = c.verts(lambda p: abs(p.z + 195.0) < 11.5 and math.hypot(p.x, p.y) < 11.5 and (p.x * p.x + p.y * p.y + (p.z + 195.0) ** 2) ** 0.5 > 10.0)
    if len(ball) < 20:
        fail("clapper ball O22 at z -195 missing")
    canons = c.verts(lambda p: p.z > -19.0)
    if not canons or max(math.hypot(p.x, p.y) for p in canons) > 48.0:
        fail("canons not on the crown")
    iron = sum(1 for p in c.ob.data.polygons if p.material_index == 1)
    notes.append("iron polys (canons + clapper): %d" % iron)
    tris = sum(len(p.vertices) - 2 for p in c.ob.data.polygons)
    notes.append("tris %d (budget 20000)" % tris)


def chk_rope(c, spec, fail, notes):
    mid = c.verts(lambda p: abs(p.z + 1305.0) < 8.0)
    top = c.verts(lambda p: abs(p.z) < 8.0)
    xm = sum(p.x for p in mid) / len(mid)
    xt = sum(p.x for p in top) / len(top)
    rr = max(math.hypot(p.x - xm, p.y) for p in mid)
    notes.append("rope centre x: top %.2f, mid %.2f, radius %.2f" % (xt, xm, rr))
    if not approx(rr, 1.75, 0.15):
        fail("rope radius %.2f (D1: O3.5)" % rr)
    if abs(xt) > 0.3 or abs(sum(p.y for p in top) / len(top)) > 0.3:
        fail("top of the rope is not at the origin")
    if not (0.6 <= xm <= 2.2):
        fail("sway at mid length %.2f (D1: 2 cm over the length)" % xm)
    sal = c.verts(lambda p: math.hypot(p.x - B.sway(-p.z), p.y) > 2.6)
    zs = [p.z for p in sal]
    notes.append("sally z %.1f..%.1f, max radius %.2f" % (min(zs), max(zs), max(math.hypot(p.x - B.sway(-p.z), p.y) for p in sal)))
    if not (approx(min(zs), -2510.0, 0.6) and approx(max(zs), -2410.0, 0.6)):
        fail("sally spans z %.1f..%.1f (D1: -2410..-2510)" % (min(zs), max(zs)))
    rs = max(math.hypot(p.x - B.sway(-p.z), p.y) for p in sal)
    if not approx(rs, 4.5, 0.5):
        fail("sally radius %.2f (D1: O9)" % rs)
    uvs = c.ob.data.uv_layers.active.data
    vs = [d.uv[1] for d in uvs]
    notes.append("rope UV v %.2f..%.2f (1 per 140 cm: %.2f expected)" % (min(vs), max(vs), 2610.0 / 140.0))
    if not approx(max(vs) - min(vs), 2610.0 / 140.0, 0.1):
        fail("rope UV v span %.2f (expected %.2f)" % (max(vs) - min(vs), 2610.0 / 140.0))
    sm = sum(1 for p in c.ob.data.polygons if p.material_index == 1)
    if sm < 10:
        fail("sally faces (MAT_Sally) missing")


def chk_roof(c, spec, fail, notes):
    zmin = min(p.z for p in c.pts)
    notes.append("lowest point z %.1f (hanging rafter; D1: to -300)" % zmin)
    if not approx(zmin, -300.0, 12.0):
        fail("hanging rafter reaches z %.1f (D1: -300)" % zmin)
    # slate presence / absence: a horizontal ray from outside towards the roof axis
    def slate_hit(o, d):
        h, m = c.ray_mat(o, d)
        return h, m
    def first_x(y, z):
        h, m = slate_hit((-900.0, y, z), (1, 0, 0))
        return h, m
    h, m = first_x(250.0, 300.0)
    notes.append("W face intact side (y +250, z 300): first hit %s mat %s" % (None if h is None else tuple(round(v) for v in h), m))
    if h is None or m != 0:
        fail("W face should carry slates at y +250 z 300")
    h, m = first_x(-250.0, 300.0)
    notes.append("W face missing zone (y -250, z 300): first hit %s mat %s" % (None if h is None else tuple(round(v) for v in h), m))
    if h is not None and m == 0 and h[0] < -100.0:
        fail("W face still has slates at y -250 z 300 (SW quarter should be gone)")
    # S face from -y
    def first_y(x, z):
        return c.ray_mat((x, -900.0, z), (0, 1, 0))
    h, m = first_y(250.0, 300.0)
    if h is None or m != 0:
        fail("S face should carry slates at x +250 z 300")
    h, m = first_y(-250.0, 300.0)
    notes.append("S face missing zone (x -250, z 300): first hit %s mat %s" % (None if h is None else tuple(round(v) for v in h), m))
    if h is not None and m == 0 and h[1] < -100.0:
        fail("S face still has slates at x -250 z 300")
    # above z 860 the roof is closed on the SW side too
    h, m = first_x(-60.0, 1000.0)
    if h is None or m != 0:
        fail("roof above z 860 near the SW hip should be covered")
    # pyramid plane: E face surface at x 300 (y 0)
    z = c.down(300.0, 0.0, 2000.0)
    exp = -10.0 + 1210.0 * (225.0 / 525.0)
    notes.append("E face at x 300: z %.1f (pyramid plane %.1f)" % (z, exp))
    if z is None or abs(z - exp) > 14.0:
        fail("E face at x 300 is %s, pyramid plane %.1f" % (z, exp))
    # hips: a horizontal ray along the hip diagonal from outside hits the hip beam where it exists; where the SW hip is snapped it passes on to the far NE hip
    def diag(sx, z):
        h, m = c.ray_mat((sx * 900.0, sx * 900.0, z), (-sx, -sx, 0))
        return None if h is None else (round(h[0]), round(h[1]), round(h[2]), m)
    ne_lo, ne_hi = diag(1, 350.0), diag(1, 800.0)
    sw_lo, sw_hi = diag(-1, 350.0), diag(-1, 800.0)
    notes.append("diagonal rays: NE z 350 %s, NE z 800 %s, SW z 350 %s, SW z 800 %s" % (ne_lo, ne_hi, sw_lo, sw_hi))
    if ne_lo is None or ne_hi is None or ne_lo[0] < 0 or ne_hi[0] < 0:
        fail("NE hip not found")
    if sw_hi is None or sw_hi[0] > 0:
        fail("upper SW hip (z > 600) not found")
    if sw_lo is not None and sw_lo[0] < 0:
        fail("SW hip should be snapped at z 600 (it is still there at z 350: %s)" % (sw_lo,))
    # finial: bent 20 deg to +x
    fin = c.verts(lambda p: p.z > 1230.0)
    if not fin:
        fail("finial missing")
    else:
        dx = (max(p.x for p in fin) + min(p.x for p in fin)) / 2.0
        dz = max(p.z for p in fin) - 1200.0
        notes.append("finial top at x %.1f, z %.1f above the apex" % (max(p.x for p in fin), dz))
        if dx < 5.0:
            fail("finial is not bent toward +x")
    n_sl = sum(1 for p in c.ob.data.polygons if p.material_index == 0)
    notes.append("slate polys %d" % n_sl)


STRUCT = dict(wall=chk_wall, flight=chk_flight, rail=chk_rail, landing=chk_landing, base=chk_base, floor=chk_floor, toprail=chk_toprail,
              partition=chk_partition, louvre=chk_louvre, frame=chk_frame, head=chk_head, bell=chk_bell, rope=chk_rope, roof=chk_roof)


# ---------------------------------------------------------------------------------------------- per-piece driver
def check(path, name, spec):
    res = dict(name=name, ok=True, fails=[], struct=[])

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
    res['min'] = [round(v, 2) for v in mn]
    res['max'] = [round(v, 2) for v in mx]
    res['tris'] = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    tol = spec.get('tol', TOL)
    for i in range(3):
        for want, have, side in ((spec['min'][i], mn[i], "min"), (spec['max'][i], mx[i], "max")):
            if want is not None and abs(have - want) > tol:
                fail("bounds %s %s %.2f vs D1 %.2f (tol %.1f)" % (side, "XYZ"[i], have, want, tol))
    if ob.matrix_world.translation.length > 1e-4:
        fail("node not at the origin")
    names = [m.name.split(".")[0] if m else None for m in ob.data.materials]
    res['slots'] = names
    if names != spec['slots']:
        fail("slots %s expected %s" % (names, spec['slots']))
    if not ob.data.color_attributes:
        fail("no colour attribute")
    elif sum(1 for d in ob.data.color_attributes[0].data if min(d.color) < 0.99):
        fail("non-white vertex colours")
    if not ob.data.uv_layers:
        fail("no UV layer")
    if len(ob.data.corner_normals) == 0:
        fail("no normals")
    vol = VK.signed_volume(ob)
    res['volume_cm3'] = round(vol, 1)
    if vol <= 0:
        fail("non-positive volume (%.1f)" % vol)
    if 'tris_max' in spec and res['tris'] > spec['tris_max']:
        fail("tris %d > budget %d" % (res['tris'], spec['tris_max']))
    # collision: D1.5 -> only T10 (4 post boxes) and T12 (1 hull); everything else none
    res['ucx'] = len(ucx)
    if len(ucx) != spec['ucx']:
        fail("UCX count %d expected %d" % (len(ucx), spec['ucx']))
    for k, u in enumerate(ucx):
        if u.name != "UCX_%s_%02d" % (name, k):
            fail("UCX name %s" % u.name)
        if not VK.is_convex(u):
            fail("%s not convex" % u.name)
        b0, b1 = VK.bounds(VK.ue_coords(u))
        for i in range(3):
            if b0[i] < mn[i] - 1.0 or b1[i] > mx[i] + 1.0:
                fail("%s outside the visual bounds on %s" % (u.name, "XYZ"[i]))
        if name.endswith("GreatBell_A"):
            nv = len(u.data.vertices)
            res['ucx_verts'] = nv
            if nv > 255:
                fail("hull has %d verts (>255)" % nv)
    k = spec.get('struct')
    if k:
        c = Ctx(ob, fail, res['struct'])
        c.ucx = ucx
        STRUCT[k](c, spec, fail, res['struct'])
    return res


def main():
    fbx_dir, js = parse()
    rows = []
    for name, spec in SPEC.items():
        path = os.path.join(fbx_dir, name + ".fbx")
        if not os.path.exists(path):
            rows.append(dict(name=name, ok=False, fails=["missing FBX"]))
            continue
        rows.append(check(path, name, spec))
    print("\n==== VERIFY TOWER SUMMARY ====")
    print("%-38s %-34s %-34s %-7s %-4s %s" % ("piece", "min (UE cm)", "max (UE cm)", "tris", "UCX", "result"))
    for r in rows:
        if 'min' not in r:
            print("%-38s %s" % (r['name'], "; ".join(r['fails'])))
            continue
        print("%-38s %-34s %-34s %-7d %-4d %s" % (r['name'].replace("SM_LB_", ""), tuple(r['min']), tuple(r['max']), r['tris'], r['ucx'],
                                                   "PASS" if r['ok'] else "FAIL: " + "; ".join(r['fails'])))
    ok = all(r['ok'] for r in rows)
    print("pieces: %d  passed: %d  failed: %d  => %s" % (len(rows), sum(1 for r in rows if r['ok']), sum(1 for r in rows if not r['ok']), "ALL PASS" if ok else "FAILURES"))
    for r in rows:
        if r.get('struct'):
            print("  %s:" % r['name'].replace("SM_LB_", ""))
            for s in r['struct']:
                print("      " + s)
    if js:
        with open(js, "w") as fh:
            json.dump(rows, fh, indent=1)
    sys.stdout.flush()
    os._exit(0 if ok else 1)


if __name__ == "__main__":
    main()
