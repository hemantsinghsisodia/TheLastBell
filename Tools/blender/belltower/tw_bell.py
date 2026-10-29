"""tw_bell.py -- the great bell (T12) and the bell rope with sally (T13).

T12 SM_LB_Prop_GreatBell_A: pivot at the crown top centre, the bell hangs along -z; slots MAT_Bronze, MAT_Iron.
T13 SM_LB_Prop_BellRope_2610: pivot at the top, hangs along -z; slots MAT_Rope, MAT_Sally.
"""
import math
import random

from tw_common import *  # noqa: F401,F403
from tw_common import K, BK, BP, bmesh, Vector, Matrix, math, random

BR, IR = 0, 1

# outer profile key points (z, r): crown O110 at -20, shoulder O130 at -35, waist O150 at -120, sound bow O196 at -200, lip O210 at -220
KEYS = [(-20.0, 55.0), (-35.0, 65.0), (-75.0, 70.0), (-120.0, 75.0), (-160.0, 82.5), (-200.0, 98.0), (-214.0, 103.5), (-220.0, 105.0)]
# wall thickness at (z, t): 6 at the waist, 14 at the sound bow and the lip
THICK = [(-35.0, 7.0), (-75.0, 6.4), (-120.0, 6.0), (-160.0, 9.5), (-200.0, 14.0), (-220.0, 14.0)]
RING_Z = (-55.0, -62.0)                     # raised mould rings
CRACK_LEN = 90.0


def _lerp_table(tab, z):
    if z >= tab[0][0]:
        return tab[0][1]
    for (za, va), (zb, vb) in zip(tab, tab[1:]):
        if z >= zb:
            t = (z - za) / (zb - za)
            return va + (vb - va) * t
    return tab[-1][1]


def r_out(z):
    """Smooth outer radius (Catmull-Rom through KEYS)."""
    ks = KEYS
    if z >= ks[0][0]:
        return ks[0][1]
    for i in range(len(ks) - 1):
        if z >= ks[i + 1][0]:
            z0, r0 = ks[i]
            z1, r1 = ks[i + 1]
            pm = ks[i - 1] if i > 0 else (z0 + (z0 - z1), r0 - (r1 - r0))
            pp = ks[i + 2] if i + 2 < len(ks) else (z1 + (z1 - z0), r1 + (r1 - r0))
            t = (z - z0) / (z1 - z0)
            m0 = (r1 - pm[1]) / (z1 - pm[0]) * (z1 - z0)
            m1 = (pp[1] - r0) / (pp[0] - z0) * (z1 - z0)
            h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
            return h00 * r0 + h10 * m0 + h01 * r1 + h11 * m1
    return ks[-1][1]


def outer_z_list():
    zs = [-20.0, -26.0, -35.0]
    z = -35.0
    while z > -214.0:
        z -= 8.0
        zs.append(z)
    zs += [-214.0, -218.0, -220.0] + [k[0] for k in KEYS]
    out = sorted(set(round(v, 3) for v in zs), reverse=True)
    for rz in RING_Z:                         # bump rows
        out += [rz + 1.8, rz + 1.0, rz, rz - 1.0, rz - 1.8]
    return sorted(set(round(v, 3) for v in out), reverse=True)


def outer_profile():
    pts = []
    for z in outer_z_list():
        r = r_out(z)
        for rz in RING_Z:                     # raised ring 1.6 high, 3.6 wide, rounded
            d = abs(z - rz)
            if d < 1.9:
                r += 1.6 * (1.0 - (d / 1.9) ** 2) ** 0.5
        pts.append((r, z))
    return pts


def build_bell():
    rng = random.Random(1112)
    out_p = outer_profile()
    # inner wall: thickness table, crown inner roof 8 thick; lip is a flat annulus with a small bevel
    inner = []
    for (r, z) in out_p:
        if z > -33.0:
            continue
        t = _lerp_table(THICK, z)
        inner.append((r_out(z) - t, z))
    inner.sort(key=lambda p: -p[1])
    zin_top = -28.0
    inner = [(inner[0][0] - 4.0, zin_top)] + inner          # inside of the crown
    # profile loop: axis (inner crown) -> inner down to the lip -> outer up to the crown -> axis (outer crown)
    prof = [(0.0, zin_top)] + inner + out_p[::-1] + [(0.0, -20.0)]
    body = K.lathe_z(prof, 72, BR)
    parts = [body]
    # canons: 6 loops on the crown, iron-coloured (slot MAT_Iron)
    for k in range(6):
        a = 60.0 * k
        pts = []
        for j in range(13):
            th = math.pi * j / 12.0
            pts.append((30.0 + 12.0 * math.cos(th), 0.0, -22.0 + 18.8 * math.sin(th)))
        t = tube(pts, 3.2, 8, IR)
        rot(t, 'Z', a)
        parts.append(t)
    # clapper: shaft + O22 ball at z -195 (iron)
    cl = K.cylinder(2.6, 150.0, 10, IR)
    shift(cl, 0.0, 0.0, -180.0)
    parts.append(cl)
    ball = BP.sphere_z(11.0, 14, 8, IR)
    shift(ball, 0.0, 0.0, -195.0)
    parts.append(ball)
    cb = K.cylinder(6.0, 6.0, 12, IR)
    shift(cb, 0.0, 0.0, -34.0)
    parts.append(cb)
    bm = join(parts)
    free_all(*parts)
    # crack on the -x side (local angle 180): 1.5 wide jagged groove from the lip up 90, depth 5; V-chip 12 wide x 10 tall at the lip
    cut = bmesh.new()
    ty, z = 0.0, -210.0
    path = [(ty, z)]
    while z < -220.0 + CRACK_LEN:
        z += rng.uniform(7.0, 11.0)
        ty += rng.uniform(-3.2, 3.2)
        ty = max(-5.0, min(5.0, ty))
        path.append((ty, min(z, -220.0 + CRACK_LEN)))
    for (a, b) in zip(path, path[1:]):
        zm = (a[1] + b[1]) * 0.5
        rr = r_out(zm)
        poly = []
        for (ty_, z_) in (a, b):
            poly.append((ty_ - 0.75, z_ + 0.4))
        for (ty_, z_) in (b, a):
            poly.append((ty_ + 0.75, z_ - 0.4))
        poly = [poly[0], poly[1], poly[2], poly[3]]
        seg = K.prism(poly, 'x', rr - 5.0, rr + 12.0, BR)
        K.bm_append(cut, seg)
        seg.free()
    chip = K.prism([(-6.0, -221.0), (6.0, -221.0), (0.0, -210.0)], 'x', 60.0, 125.0, BR)
    K.bm_append(cut, chip)
    chip.free()
    rot(cut, 'Z', 180.0)
    bm2 = BP.bool_op(bm, cut, 'DIFFERENCE', 2)
    bm.free()
    cut.free()
    # collision: one convex hull of the outer profile (16 sides, 8 levels)
    pts = []
    for z in (-20.0, -35.0, -75.0, -120.0, -160.0, -200.0, -214.0, -220.0):
        for k in range(16):
            a = 2 * math.pi * k / 16.0
            r = r_out(z)
            pts.append(Vector((r * math.cos(a), r * math.sin(a), z)))
    hull = K.hull_from_points(pts, 0)
    note = ("pivot crown top centre, hangs along -z; lathe 72 sides: crown O110 (-20), shoulder O130 (-35), waist O150 (-120, wall 6), sound bow O196 (-200, wall 14), lip O210 (-220); "
            "mould rings at z -55 / -62; 6 canons (MAT_Iron); iron clapper, ball O22 at z -195; crack on the -x side (angle 180) from the lip up 90 + V-chip 12 x 10; UCX = 1 convex hull")
    tp = TP(PROP_PREFIX + "GreatBell_A", bm2, ["MAT_Bronze", "MAT_Iron"], ucx=[hull], note=note, keep_uv=True)
    uv_cylinder(tp.bm, circ_cm=100.0, v_cm=100.0)
    return tp


# ============================================================================================== T13 rope + sally
ROPE_LEN = 2610.0
SALLY_Z0, SALLY_Z1 = 2410.0, 2510.0


def sway(depth):
    return 2.0 * math.sin(math.pi * depth / ROPE_LEN)          # 2 cm peak sway in +x over the length


def build_rope():
    rng = random.Random(1114)
    pts = []
    n = int(ROPE_LEN / 15.0)
    for i in range(n + 1):
        d = ROPE_LEN * i / n
        pts.append((sway(d), 0.0, -d))
    rope = tube(pts, 1.75, 8, 0)
    # sally: woollen grip O9, 100 long at z -2410..-2510, with a bulge and 5 raised stripe bands
    prof = []
    for k in range(21):
        d = SALLY_Z0 + (SALLY_Z1 - SALLY_Z0) * k / 20.0
        t = k / 20.0
        r = 3.6 + 0.9 * math.sin(math.pi * t) ** 0.6
        if k % 4 in (1, 2):
            r += 0.25                                                  # stripe bands
        if k in (0, 20):
            r = 3.6
        prof.append((r, -d))
    prof = [(0.0, -SALLY_Z0)] + prof + [(0.0, -SALLY_Z1)]
    sal = K.lathe_z(prof, 14, 1)
    # lathe_z axis is z=0: move it onto the swaying rope axis at the sally's mid-depth
    shift(sal, sway((SALLY_Z0 + SALLY_Z1) / 2.0), 0.0, 0.0)
    bm = join([rope, sal])
    free_all(rope, sal)
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for l in f.loops:
            c = l.vert.co
            xc = sway(-c.z)
            a = math.atan2(c.y, c.x - xc)
            fa = math.atan2(sum(v.co.y for v in f.verts), sum(v.co.x - sway(-v.co.z) for v in f.verts))
            d = a - fa
            while d > math.pi:
                d -= 2 * math.pi
            while d < -math.pi:
                d += 2 * math.pi
            u = (fa + d) / (2 * math.pi)
            l[uvl].uv = (u, -c.z / 140.0)
    return TP(PROP_PREFIX + "BellRope_2610", bm, ["MAT_Rope", "MAT_Sally"], keep_uv=True,
              note="pivot at the top; O3.5 rope z 0..-2610 (2 cm sway in +x), woollen sally O9 x 100 at z -2410..-2510 (MAT_Sally); UV: u around, v = depth / 140")
