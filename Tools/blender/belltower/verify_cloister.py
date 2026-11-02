"""verify_cloister.py -- re-imports every P10-3b FBX in a clean headless Blender and checks it against Docs/plans/P10_BELLTOWER_ART.md D1.3 / D1.4.

    blender.exe -b --factory-startup --python Tools/blender/belltower/verify_cloister.py -- [--fbx SourceArt/Cloister] [--json out.json] [--only SUBSTR ...]

All checks are in Unreal space (UE_Y = -Blender_Y of the re-imported file, see Tools/blender/kit/README.md).  Per piece: bounds / pivot (+-0.5 cm unless a
piece says otherwise), slot names and order, UCX (only SM_LB_Prop_SmallBell_A has one: a single convex hull), triangle cap, closed positive volume, white vertex
colour, UVs, custom normals, plus the structural checks listed in the task (drip course, arch curves, pier shaft faces, vault shell / ribs / holes, roof hole ...).
Exit code 1 if any check fails.
"""
import json
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "Tools", "blender", "kit"))
sys.path.insert(0, HERE)
import verify_kit as VK  # noqa: E402  (importing does not run anything)
import build_cloister as C  # noqa: E402  (importing does not build anything)

TOL = 0.5
KIT = ["MAT_Masonry", "MAT_Trim", "MAT_Rubble"]
ROOF = ["MAT_Slate", "MAT_Wood"]
P = "SM_LB_Cl_"
PP = "SM_LB_Prop_"


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    fbx = os.path.join(REPO, "SourceArt", "Cloister")
    js, only = None, []
    i = 0
    while i < len(argv):
        if argv[i] == "--fbx":
            fbx = os.path.abspath(argv[i + 1])
            i += 2
        elif argv[i] == "--json":
            js = os.path.abspath(argv[i + 1])
            i += 2
        elif argv[i] == "--only":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                only.append(argv[i])
                i += 1
        else:
            i += 1
    return fbx, js, only


class Ctx:
    """One re-imported piece in UE space with a BVH for ray tests."""

    def __init__(self, ob):
        self.ob = ob
        self.pts = VK.ue_coords(ob)
        self.mn, self.mx = VK.bounds(self.pts)
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.transform(ob.matrix_world)
        sc = bpy.context.scene.unit_settings.scale_length * 100.0
        for v in bm.verts:
            v.co = Vector((v.co.x * sc, -v.co.y * sc, v.co.z * sc))
        self.bm = bm
        bm.faces.ensure_lookup_table()
        self.bvh = BVHTree.FromBMesh(bm)
        self.fails = []
        self.notes = []

    def fail(self, m):
        self.fails.append(m)

    def hits(self, o, d, maxn=40):
        """All ray hits (UE space) along d from o, nearest first."""
        o = Vector(o)
        d = Vector(d).normalized()
        out = []
        cur = o
        for _ in range(maxn):
            h = self.bvh.ray_cast(cur, d)
            if h[0] is None:
                break
            out.append(h[0].copy())
            cur = h[0] + d * 1e-3
        return out

    def first(self, o, d):
        h = self.hits(o, d, 1)
        return h[0] if h else None

    def expect(self, label, got, want, tol):
        if got is None or abs(got - want) > tol:
            self.fail("%s %s vs %.3f (tol %.2f)" % (label, "None" if got is None else "%.3f" % got, want, tol))


# ----------------------------------------------------------------------------------------------
# structural checks
# ----------------------------------------------------------------------------------------------
def chk_wall(c, tall, drip):
    ys = [p.y for p in c.pts]
    inner = [p for p in c.pts if p.y < -0.01]
    if max(ys) > 40.01:
        c.fail("vertices beyond the outer face y 40: max %.3f" % max(ys))
    if drip:
        if not inner:
            c.fail("no drip course on the inner face")
        else:
            lo, hi = min(p.z for p in inner), max(p.z for p in inner)
            if lo < 1210 - 0.05 or hi > 1230 + 0.05:
                c.fail("inner-face projections outside z 1210..1230: %.2f..%.2f" % (lo, hi))
            c.expect("drip projection y", c.mn.y, -6.0, 0.05)
            c.notes.append("drip z %.1f..%.1f proj %.1f" % (lo, hi, -c.mn.y))
    elif inner:
        c.fail("unexpected projection on the inner face (%d verts)" % len(inner))
    c.expect("top z", c.mx.z, tall, 0.05)


def chk_archway(c, span, spring, apex):
    fc = C.four_centred(span, apex - spring, gamma_deg=9.0)
    c.expect("min z (springing)", c.mn.z, spring, 0.5)
    bad = 0
    worst = 0.0
    for i in range(1, 40):
        x = span * i / 40.0
        h = c.first((x, 20.0, spring - 5.0), (0, 0, 1))
        zc = spring + fc.z_at(x, 0.0)
        if h is None or h.z < zc - 0.6:
            bad += 1
        elif h.z > zc + 8.0:
            bad += 1
        worst = max(worst, abs(h.z - zc) if h else 99.0)
    if bad:
        c.fail("opening not clear below / off the arch curve at %d of 39 samples" % bad)
    h = c.first((span / 2 + 0.4, 20.0, spring - 5.0), (0, 0, 1))
    c.expect("intrados apex z", h.z if h else None, apex, 1.0)
    inner = [p for p in c.pts if p.y < -0.01]
    if inner and (min(p.z for p in inner) < 1210 - 0.05 or max(p.z for p in inner) > 1230 + 0.05):
        c.fail("drip course outside z 1210..1230")
    if max(p.y for p in c.pts) > 40.01:
        c.fail("projection on the outer face (no drip there)")
    c.notes.append("r1 %.1f R2 %.1f spring %g apex %g curve dev %.2f" % (fc.r1, fc.R2, spring, apex, worst))


def chk_pier(c, hx, hy):
    pts = c.pts
    # D-086: masonry grooves are gone, so a plain face has vertices only at its band edges, not inside the band.
    shaft = [p for p in pts if 24.95 <= p.z <= 300.05]
    block = [p for p in pts if 329.95 <= p.z <= 600.05]

    def nearest(sel, axis, target):
        return min((abs(getattr(p, axis)) for p in sel), key=lambda v: abs(v - target))

    c.expect("shaft face x", nearest(shaft, "x", hx), hx, 0.05)
    c.expect("shaft face y", nearest(shaft, "y", hy), hy, 0.05)
    c.expect("block face x", nearest(block, "x", hx), hx, 0.05)
    c.expect("block face y", nearest(block, "y", hy), hy, 0.05)
    for lab, lo, hi, pr in (("base", 1, 24, 4.0), ("capital", 301, 330.05, 8.0), ("coping", 601, 619, 5.0)):
        sel = [p for p in pts if lo <= p.z <= hi]
        c.expect(lab + " proud x", max(abs(p.x) for p in sel) - hx, pr, 0.05)
    # proud parts only below 25 and at 300..330 / 600..620
    for p in pts:
        if (abs(p.x) > hx + 0.06 or abs(p.y) > hy + 0.06) and not (p.z <= 25.05 or 299.95 <= p.z <= 330.05 or 599.95 <= p.z <= 620.05):
            c.fail("proud vertex outside the allowed z bands at z %.2f" % p.z)
            break
    # chamfered shaft corners
    cor = [p for p in shaft if abs(abs(p.x) - hx) < 0.05 and abs(p.y) > hy - 5.9]
    xface = [p for p in shaft if abs(abs(p.x) - hx) < 0.05]
    c.notes.append("chamfer check examined %d shaft vertices on the x face; widest |y| there %.2f (an unchamfered corner would be %.1f)" % (
        len(xface), max((abs(p.y) for p in xface), default=0.0), hy))
    if cor:
        c.fail("shaft corners not chamfered 6 cm (%d verts)" % len(cor))
    c.expect("top z (D1.11: tops at 620)", c.mx.z, 620.0, 0.05)


def chk_arcade_arch(c, span):
    R = 0.8 * span
    apex = math.sqrt(R * R - (R - span / 2) ** 2)
    h = c.first((span / 2 + 0.4, 0.0, -5.0), (0, 0, 1))
    c.expect("intrados apex z (0.742 span)", h.z if h else None, 0.742 * span, 1.0)
    c.expect("analytic apex", apex, 0.742 * span, 1.0)
    # opening clear below the curve
    bad = 0
    for i in range(1, 30):
        x = span * i / 30.0
        hh = c.first((x, 0.0, -5.0), (0, 0, 1))
        xx = x if x <= span / 2 else span - x
        zc = math.sqrt(max(0.0, R * R - (xx - R) ** 2))
        if hh is None or hh.z < zc - 0.6:
            bad += 1
    if bad:
        c.fail("arch opening not clear / not on the curve at %d samples" % bad)
    cop = [p for p in c.pts if abs(p.y) > 40.5]
    c.expect("coping bottom z", min(p.z for p in cop), 270.0, 0.05)
    c.expect("coping top z", max(p.z for p in cop), 290.0, 0.05)
    c.expect("coping proud y", max(abs(p.y) for p in cop), 45.0, 0.05)
    spand = [p for p in c.pts if 39.5 < abs(p.y) < 40.5]
    c.expect("spandrel top z", max(p.z for p in spand), 270.0, 0.05)
    c.notes.append("apex %.2f (0.742 x %d = %.2f)" % (h.z if h else -1, span, 0.742 * span))


def chk_garth_wall(c):
    c.expect("top z", c.mx.z, 100.0, 0.01)
    c.expect("coping min y", c.mn.y, -4.0, 0.05)
    c.expect("coping max y", c.mx.y, 30.0, 0.05)
    for p in c.pts:
        if (p.y < -0.01 or p.y > 15.01) and p.z < 88 - 0.05:
            c.fail("coping vertex below z 88 at y %.2f z %.2f" % (p.y, p.z))
            break
    top = [p for p in c.pts if p.z > 99.99]
    if not top:
        c.fail("no vertex at z 100")


def chk_bed(c):
    c.expect("max z (mounds <= 10)", min(c.mx.z, 10.0), c.mx.z, 1e-6)
    if c.mx.z < 2.0:
        c.fail("mounds missing (max z %.2f)" % c.mx.z)
    low = 0
    for (gx, gy) in C.GRAVES_LOCAL:
        h = c.first((gx, gy, 50.0), (0, 0, -1))
        if h is None or h.z > -1.0:
            low += 1
    if low:
        c.fail("%d of 6 grave hollows not below z -1" % low)
    band_max, bn = -99.0, 0
    for i in range(0, 221):
        for j in range(0, 161):
            x, y = 5.0 * i, 5.0 * j
            if min(x, 1100.0 - x, y, 800.0 - y) <= 34.0:
                hb = c.first((x, y, 50.0), (0, 0, -1))
                bn += 1
                if hb is not None:
                    band_max = max(band_max, hb.z)
    if band_max > -0.5:
        c.fail("D1.11: max z within 34 cm of an edge is %.2f (must be <= -0.5)" % band_max)
    c.notes.append("edge band max z %.2f (%d rays)" % (band_max, bn))
    h = c.first((C.CROSS_LOCAL[0], C.CROSS_LOCAL[1], 50.0), (0, 0, -1))
    c.notes.append("surface z %.1f..%.1f, cross apron z %.2f" % (c.mn.z + 0, c.mx.z, h.z if h else -99))
    if h is None or h.z > 2.0:
        c.fail("cross apron not flat/low")


def chk_slab(c):
    c.expect("top z", c.mx.z, 8.0, 0.05)


def chk_barrel(c, span, L, broken):
    fc = C.vault_fc(span)
    T = C.SHELL_T
    ze_apex = fc.z_at(span / 2, 0.0)
    zi_apex = fc.z_at(span / 2, T)
    c.expect("min z (springing)", c.mn.z, 0.0, 0.01)
    c.expect("apex z (extrados)", c.mx.z, 340.0, 1.0)
    sp = [p for p in c.pts if p.z < 0.01]
    if not sp or min(p.y for p in sp) > 0.05 or max(p.y for p in sp) < span - 0.05:
        c.fail("springing edges at y 0 and y %g are not at z 0" % span)
    # shell thickness (horizontal at z 2 near the springing)
    hs = c.hits((25.0, -10.0, 2.0), (0, 1, 0))
    if len(hs) >= 2:
        c.expect("shell thickness at the springing", hs[1].y - hs[0].y, T, 0.3)
    else:
        c.fail("springing thickness ray found %d hits" % len(hs))
    xm = 25.0
    ht = c.first((xm, span / 2 + 0.4, 600.0), (0, 0, -1))
    hb = c.first((xm, span / 2 + 0.4, -5.0), (0, 0, 1))
    if not broken or True:
        c.expect("extrados apex (ray)", ht.z if ht else None, ze_apex, 0.6)
        c.expect("intrados apex (ray)", hb.z if hb else None, zi_apex, 0.6)
    rib_z = fc.z_at(span / 2, T + C.RIB_D)
    ribs = []
    prev = None
    for xi in range(0, int(L) + 1):
        h = c.first((xi + 0.5, span / 2 + 0.4, -5.0), (0, 0, 1))
        isr = h is not None and h.z < zi_apex - 10.0
        if broken and 50 <= xi <= 600:
            if h is not None:
                c.fail("hole not open at x %d (hit z %.1f)" % (xi, h.z))
                break
        if isr and prev is None:
            prev = xi
        if (not isr) and prev is not None:
            ribs.append((prev, xi))
            prev = None
    if prev is not None:
        ribs.append((prev, int(L) + 1))
    want = [(0, 15), (L / 2 - 15, L / 2 + 15), (L - 15, L)]
    if not broken:
        if len(ribs) != 3 or any(abs(a - w[0]) > 1.6 or abs(b - w[1]) > 1.6 for (a, b), w in zip(ribs, want)):
            c.fail("rib x ranges %s vs %s" % (ribs, [tuple(round(v, 1) for v in w) for w in want]))
        h = c.first((L / 2, span / 2 + 0.4, -5.0), (0, 0, 1))
        c.expect("rib soffit z at the mid rib", h.z if h else None, rib_z, 0.8)
    else:
        for y in (span / 2 - 60, span / 2, span / 2 + 60):
            for xi in range(50, 601, 10):
                h = c.first((xi, y, 600.0), (0, 0, -1))
                if h is not None:
                    c.fail("hole not open through the shell at (%d, %.0f): hit z %.1f" % (xi, y, h.z))
                    break
        # end ribs intact, mid rib stubs on both haunches
        for xe in (7.0, L - 7.0):
            h = c.first((xe, span / 2 + 0.4, -5.0), (0, 0, 1))
            c.expect("end rib soffit z at x %.0f" % xe, h.z if h else None, rib_z, 0.8)
        stubs = 0
        for y in (70.0, span - 70.0):
            hm = c.first((L / 2, y, -5.0), (0, 0, 1))
            hn = c.first((L / 2 + 80.0, y, -5.0), (0, 0, 1))
            if hm is not None and hn is not None and hm.z < hn.z - 10.0:
                stubs += 1
        if stubs != 2:
            c.fail("mid rib stubs found on %d of 2 haunches" % stubs)
        c.notes.append("hole open x 50..600 (3 rows), 2 mid-rib stubs, end ribs intact")
    c.notes.append("r1 %.1f R2 %.1f gamma %.1f apex ext %.1f int %.1f" % (fc.r1, fc.R2, fc.gamma, ze_apex, zi_apex))


def chk_groin(c, Sx, Sy, outer):
    fcx, fcy = C.vault_fc(Sx), C.vault_fc(Sy)
    T = C.SHELL_T
    ze = lambda fc, y: fc.z_at(y, 0.0) or 0.0
    zi = lambda fc, y: fc.z_at(y, T) or 0.0
    c.expect("min z (springing)", c.mn.z, 0.0, 0.01)
    c.expect("apex z", c.mx.z, 340.0, 1.0)
    # surface samples away from the creases
    bad_t = bad_b = n = 0
    for i in range(1, 12):
        for j in range(1, 12):
            x, y = Sx * i / 12.0 + 0.37, Sy * j / 12.0 + 0.21
            dxc = abs(x - Sx / 2) / (Sx / 2)
            dyc = abs(y - Sy / 2) / (Sy / 2)
            if abs(dxc - dyc) < 0.12 or x < 65 or x > Sx - 65 or y < 65 or y > Sy - 65:       # near a groin or a wall rib
                continue
            n += 1
            h = c.first((x, y, 600.0), (0, 0, -1))
            if h is None or abs(h.z - max(ze(fcx, x), ze(fcy, y))) > 0.8:
                bad_t += 1
            hb = c.first((x, y, -5.0), (0, 0, 1))
            zb = max(zi(fcx, x), zi(fcy, y))
            if hb is None or abs(hb.z - zb) > 0.8:
                bad_b += 1
    if bad_t or bad_b:
        c.fail("surface mismatch at %d top / %d bottom of %d samples" % (bad_t, bad_b, n))
    # shell thickness at the springing (horizontal, away from the diagonal and wall ribs)
    hs = c.hits((2.0, -10.0, 2.0), (0, 1, 0))
    if len(hs) >= 2:
        c.expect("shell thickness at the y 0 springing", hs[1].y - hs[0].y, T, 0.3)
    else:
        c.fail("springing thickness ray found %d hits" % len(hs))
    # diagonal ribs: on the groin curve the soffit is ~25 below the intrados, 70 cm off it the intrados is clean
    on_ok = off_ok = 0
    cnt = 0
    for fy in (0.22, 0.3, 0.38):
        y = Sy * fy
        xs = C._solve_crease(fcx, zi(fcy, y), T)
        h_on = c.first((xs, y, -5.0), (0, 0, 1))
        zint = max(zi(fcx, xs), zi(fcy, y))
        cnt += 1
        if h_on is not None and zint - h_on.z > 15.0:
            on_ok += 1
        xo = xs - 70.0
        h_off = c.first((xo, y, -5.0), (0, 0, 1))
        if h_off is not None and abs(h_off.z - max(zi(fcx, xo), zi(fcy, y))) < 0.8:
            off_ok += 1
        else:
            c.notes.append("off-crease miss y %.0f xo %.0f hit %s want %.1f" % (y, xo, None if h_off is None else "%.1f" % h_off.z, max(zi(fcx, xo), zi(fcy, y))))
    if on_ok != cnt:
        c.fail("diagonal rib not found on the groin curve at %d of %d samples" % (cnt - on_ok, cnt))
    if off_ok != cnt:
        c.fail("clean intrados expected 70 cm off the groin at %d of %d samples" % (cnt - off_ok, cnt))
    # wall ribs on the two outer sides only
    for side in ('x0', 'x1', 'y0', 'y1'):
        if side == 'x0':
            o, fcs, zint = (45.0, Sy / 2 + 0.3, -5.0), fcy, None
            pos, mid = 45.0, fcy.z_at(Sy / 2, T + C.RIB_D)
        elif side == 'x1':
            o, fcs = (Sx - 45.0, Sy / 2 + 0.3, -5.0), fcy
            mid = fcy.z_at(Sy / 2, T + C.RIB_D)
        elif side == 'y0':
            o, fcs = (Sx / 2 + 0.3, 45.0, -5.0), fcx
            mid = fcx.z_at(Sx / 2, T + C.RIB_D)
        else:
            o, fcs = (Sx / 2 + 0.3, Sy - 45.0, -5.0), fcx
            mid = fcx.z_at(Sx / 2, T + C.RIB_D)
        h = c.first(o, (0, 0, 1))
        has = h is not None and abs(h.z - mid) < 1.0
        if (side in outer) != has:
            c.fail("wall rib on %s: present %s, expected %s (hit %s, soffit %.1f)" % (side, has, side in outer, None if h is None else "%.1f" % h.z, mid))
    c.notes.append("outer wall ribs %s; x r1 %.1f R2 %.1f, y r1 %.1f R2 %.1f" % ("+".join(outer), fcx.r1, fcx.R2, fcy.r1, fcy.R2))


def chk_leanto(c, hole):
    pts = c.pts
    c.expect("min x", c.mn.x, 0.0, 0.01)
    c.expect("max x", c.mx.x, 1000.0, 0.01)
    c.expect("max y", c.mx.y, 1050.0, 0.01)
    c.expect("rafter underside z", min(p.z for p in pts if p.z > -20), -15.0, 0.01)
    if not hole:
        miss = n = 0
        for xi in range(40, 961, 40):
            for yi in range(40, 1011, 40):
                n += 1
                h = c.first((xi, yi, 50.0), (0, 0, -1))
                if h is None or not (4.5 <= h.z <= 9.8):
                    miss += 1
        if miss > 0.06 * n:
            c.fail("slate coverage: %d of %d samples without a slate" % (miss, n))
        c.notes.append("slate coverage %d/%d" % (n - miss, n))
    else:
        bad = 0
        n = 0
        for xi in range(190, 811, 20):
            for yi in range(40, 761, 20):
                n += 1
                hs = c.hits((xi, yi, 50.0), (0, 0, -1))
                if any(h.z > 0.1 for h in hs):
                    bad += 1
        if bad:
            c.fail("hole not open in x 190..810 y 40..760: %d of %d rays hit slate/board/batten" % (bad, n))
        # rafters: outside the hole they are full length; 3 snapped ones hang below
        stubs = [p for p in pts if p.z < -30]
        if not stubs:
            c.fail("no snapped rafter stubs hanging below the plane")
        else:
            c.notes.append("hole open (%d rays), lowest z %.1f" % (n, c.mn.z))
        if c.mn.z < -100:
            c.fail("stub hangs more than 85 below the rafters (z %.1f)" % c.mn.z)
        outside = c.first((100.0, 500.0, 50.0), (0, 0, -1))
        if outside is None or outside.z < 4.0:
            c.fail("slates missing outside the hole")


def chk_leanto_valley(c, side):
    """C14V: triangle kept, nothing past the hypotenuse, both hypotenuse ends present, valley rafter, slates still cover the triangle."""
    pts = c.pts
    c.expect("min x", c.mn.x, 0.0, 0.01)
    c.expect("max x", c.mx.x, 1000.0, 0.01)
    c.expect("min y", c.mn.y, 0.0, 0.01)
    c.expect("max y", c.mx.y, 1050.0, 0.01)
    c.expect("rafter underside z", min(p.z for p in pts if p.z > -20), -15.0, 0.01)
    if side == 'L':
        n = Vector((1050.0, 1000.0, 0.0)).normalized()
        o = Vector((1000.0, 0.0, 0.0))
        ends = ((1000.0, 0.0), (0.0, 1050.0))
    else:
        n = Vector((-1050.0, 1000.0, 0.0)).normalized()
        o = Vector((0.0, 0.0, 0.0))
        ends = ((0.0, 0.0), (1000.0, 1050.0))
    dmin = min((p - o).dot(n) for p in pts)
    if dmin < -0.5:
        c.fail("vertex on the cut-away side: signed distance to the hypotenuse %.3f < -0.5" % dmin)
    for (ex, ey) in ends:
        d = min(math.hypot(p.x - ex, p.y - ey) for p in pts)
        if d > 2.0:
            c.fail("no vertex within 2 cm of (%g, %g) (nearest %.2f)" % (ex, ey, d))
    # the cut is a real cut: the far corner of the cut-away triangle is empty, and the kept corner is full
    far = (0.0, 0.0) if side == 'L' else (1000.0, 0.0)
    if any(math.hypot(p.x - far[0], p.y - far[1]) < 30.0 for p in pts):
        c.fail("geometry left in the cut-away corner (%g, %g)" % far)
    # valley rafter: wood, 12 wide, along the hypotenuse -> a vertex row at z -15 and 0 on both rafter faces
    zs = [p for p in pts if abs(p.z + 15.0) < 0.01]
    inner = [p for p in zs if 11.0 < (p - o).dot(n) < 13.0]
    if len(inner) < 2:
        c.fail("no valley rafter inner face (offset 12) found at z -15")
    # slates cover the kept triangle (cells whose centre is well inside the triangle)
    miss = tot = 0
    for xi in range(40, 961, 40):
        for yi in range(40, 1011, 40):
            if (Vector((xi, yi, 0.0)) - o).dot(n) < 40.0:
                continue
            tot += 1
            h = c.first((xi, yi, 50.0), (0, 0, -1))
            if h is None or not (4.5 <= h.z <= 9.8):
                miss += 1
    if tot == 0 or miss > 0.06 * tot:
        c.fail("slate coverage: %d of %d samples without a slate" % (miss, tot))
    # the cut-away side has no slate
    out = 0
    for xi in range(40, 961, 40):
        for yi in range(40, 1011, 40):
            if (Vector((xi, yi, 0.0)) - o).dot(n) < -20.0:
                h = c.first((xi, yi, 50.0), (0, 0, -1))
                if h is not None:
                    out += 1
    if out:
        c.fail("%d rays hit geometry on the cut-away side" % out)
    # open boundary edges (the caps)
    bnd = sum(1 for e in c.bm.edges if e.is_boundary)
    c.notes.append("signed distance min %.3f, slate coverage %d/%d, boundary edges %d, volume checked by the generic test" % (dmin, tot - miss, tot, bnd))


def chk_cell(c):
    c.expect("frame projects to y", c.mn.y, -8.0, 0.05)
    if max(p.y for p in c.pts) > 2.05:
        c.fail("geometry beyond y +2")
    h = c.first((0.0, -20.0, 100.0), (0, 1, 0))
    c.expect("back panel front face y", h.y if h else None, -2.0, 0.1)
    h = c.first((65.0, -20.0, 100.0), (0, 1, 0))
    c.expect("jamb front face y", h.y if h else None, -8.0, 0.05)
    hs = c.hits((-100.0, -5.0, 100.0), (1, 0, 0))
    if len(hs) >= 2:
        c.expect("jamb outer x", hs[0].x, -75.0, 0.3)
        c.expect("opening left x", hs[1].x, -55.0, 0.3)
    else:
        c.fail("jamb rays found %d hits" % len(hs))
    hh = c.first((0.3, -5.0, 100.0), (0, 0, 1))
    c.expect("opening apex z", hh.z if hh else None, 250.0, 0.6)
    hh = c.first((54.7, -5.0, 100.0), (0, 0, 1))
    c.expect("shoulder z (inner line, 1 cm chamfer)", hh.z if hh else None, 250.0 - (30.0 / 55.0) * 54.7, 1.0)
    c.expect("top z", c.mx.z, 270.0, 0.5)
    c.notes.append("opening 110 x 250, surround 150 x 270, back panel y -2..+2 (visible front face -2)")


def chk_gable(c):
    h0 = c.first((0.3, 20.0, 800.0), (0, 0, -1))
    h1 = c.first((190.0, 20.0, 800.0), (0, 0, -1))
    c.expect("rake z at the end", h0.z if h0 else None, 450.3, 0.6)
    c.expect("apex z", h1.z if h1 else None, 650.0, 0.6)
    c.expect("thickness", c.mx.y - c.mn.y, 40.0, 0.05)


def chk_stair_roof(c):
    h = c.first((210.0, 300.0, 400.0), (0, 0, -1))
    c.expect("ridge top z", h.z if h else None, 200.0, 0.6)
    h = c.first((0.5, 300.0, 400.0), (0, 0, -1))
    c.expect("eaves z at x 0.5", h.z if h else None, 0.5 * 196.0 / 210.0, 1.2)
    h = c.first((419.5, 300.0, 400.0), (0, 0, -1))
    c.expect("eaves z at x 419.5", h.z if h else None, 0.5 * 196.0 / 210.0, 1.2)
    c.expect("min x", c.mn.x, 0.0, 0.5)
    c.expect("max x", c.mx.x, 420.0, 0.5)


def chk_bell(c):
    c.expect("lip z", c.mn.z, -28.0, 0.05)
    lip = [p for p in c.pts if p.z < -27.95]
    c.expect("lip diameter", 2 * max(math.hypot(p.x, p.y) for p in lip), 24.0, 0.1)
    bow = [p for p in c.pts if abs(p.z + 25.0) < 0.3]
    c.expect("sound bow diameter at z -25", 2 * max(math.hypot(p.x, p.y) for p in bow if math.hypot(p.x, p.y) > 5), 22.0, 0.6)
    waist = [p for p in c.pts if abs(p.z + 14.0) < 0.3]
    c.expect("waist diameter at z -14", 2 * max(math.hypot(p.x, p.y) for p in waist), 16.0, 0.4)
    crown = [p for p in c.pts if abs(p.z + 3.0) < 0.3]
    c.expect("crown diameter at z -3", 2 * max(math.hypot(p.x, p.y) for p in crown), 10.0, 0.4)
    me = c.ob.data
    me.calc_loop_triangles()
    bz = [c.pts[v].z for poly in me.polygons if poly.material_index == 0 for v in poly.vertices]
    c.expect("bronze crown top z", max(bz), 0.0, 0.05)
    iron = [c.pts[v] for poly in me.polygons if poly.material_index == 1 for v in poly.vertices]
    c.expect("loop top z", max(p.z for p in iron), 4.0, 0.05)
    ball = [p for p in iron if abs(p.x) < 2.5 and abs(p.y) < 2.5 and -26.5 < p.z < -21.5]
    c.expect("clapper ball diameter", max(p.z for p in ball) - min(p.z for p in ball) if ball else None, 4.0, 0.3)
    band = [c.pts[v] for poly in me.polygons if poly.material_index == 2 for v in poly.vertices]
    if not band:
        c.fail("no MAT_Band faces")
    else:
        if min(p.z for p in band) < -8.05 or max(p.z for p in band) > -4.95:
            c.fail("band z range %.2f..%.2f outside -8..-5" % (min(p.z for p in band), max(p.z for p in band)))
        c.notes.append("band z %.2f..%.2f" % (min(p.z for p in band), max(p.z for p in band)))


def chk_bracket(c):
    me = c.ob.data
    wood = [c.pts[v] for poly in me.polygons if poly.material_index == 1 for v in poly.vertices]
    c.expect("hood board z min", min(p.z for p in wood), 18.0, 0.05)
    c.expect("hood board z max", max(p.z for p in wood), 22.0, 0.05)
    c.expect("hood board x max", max(p.x for p in wood), 34.0, 0.05)
    iron = [c.pts[v] for poly in me.polygons if poly.material_index == 0 for v in poly.vertices]
    plate = [p for p in iron if p.x < 4.05 and p.z < 16.0 and p.z > -26.0]
    c.expect("plate z min", min(p.z for p in plate), -25.0, 0.05)
    c.expect("plate half width", max(abs(p.y) for p in plate), 10.0, 0.05)
    c.expect("arm tip x", max(p.x for p in iron), 30.0, 0.3)
    hook = [p for p in iron if 24.4 < p.x < 25.6]
    c.expect("hook x", sum(p.x for p in hook) / len(hook) if hook else None, 25.0, 0.7)


def chk_plaque(c, depth, step):
    f = c.first((10.0, 0.0, 0.0), (-1, 0, 0))
    c.expect("field face x", f.x if f else None, depth - step, 0.1)
    b = c.first((10.0, 0.0, c.mx.z - 1.5), (-1, 0, 0))
    c.expect("border face x", b.x if b else None, depth, 0.05)
    c.expect("back plane x", c.mn.x, 0.0, 0.01)
    c.notes.append("front faces +x (field %.1f, border %.1f)" % (depth - step, depth))


# ---- P10-8d (D1.27 F1) -------------------------------------------------------------------------------------------
def carve_pts(c, slot):
    """Vertices (UE space) of every polygon in material slot `slot`."""
    me = c.ob.data
    return [c.pts[v] for poly in me.polygons if poly.material_index == slot for v in poly.vertices]


def chk_lantern(c, R):
    c.expect("ring lowest point z (= lantern top)", min(p.z for p in c.pts if abs(p.x - R) < 3.2), 0.0, 0.1)
    c.expect("finial x max", c.mx.x, R + 3.9, 0.1)
    tip = [p.z for p in c.pts if abs(p.x - (R + 2.0)) < 0.01 and abs(p.y) < 1.01]          # the arm bar's end face (z 13..15)
    c.expect("arm end z top", max(tip) if tip else None, 15.0, 0.1)
    c.expect("arm end z bottom", min(tip) if tip else None, 13.0, 0.1)
    plate = [p for p in c.pts if p.x < 2.2]
    c.expect("plate back x", min(p.x for p in plate), 0.0, 0.01)
    c.expect("plate z min", min(p.z for p in plate), -14.0, 0.05)
    c.expect("plate z max", max(p.z for p in plate), 18.0, 0.05)
    c.notes.append("ring bottom z %.2f, R %g" % (min(p.z for p in c.pts if abs(p.x - R) < 3.2), R))


def chk_memorial(c):
    f = c.first((10.0, 0.0, 11.2), (-1, 0, 0))                       # field between row 1 and the top border
    c.expect("field face x", f.x if f else None, 2.8, 0.05)
    b = c.first((10.0, 0.0, c.mx.z - 1.5), (-1, 0, 0))
    c.expect("border face x", b.x if b else None, 4.0, 0.05)
    c.expect("back plane x", c.mn.x, 0.0, 0.01)
    ink = carve_pts(c, 1)
    if not ink:
        c.fail("no MAT_Carve faces")
        return
    c.expect("groove floor x", min(p.x for p in ink), 2.8 - 0.48, 0.1)
    c.expect("groove rim x", max(p.x for p in ink), 2.8, 0.05)
    if max(abs(p.y) for p in ink) > 57.0 or max(abs(p.z) for p in ink) > 12.0:
        c.fail("lettering outside the field (|y| %.2f, |z| %.2f)" % (max(abs(p.y) for p in ink), max(abs(p.z) for p in ink)))
    # row 4 numerals: III under ANSELM, II under OSRIC.  In game ANSELM is at the viewer's LEFT; Unreal's viewer at +x facing -x has -y on the right, so ANSELM is at +y.
    def inkcount(y0, y1, z0, z1):
        return sum(1 for p in ink if y0 <= p.y <= y1 and z0 <= p.z <= z1)
    left, right = inkcount(28, 57, -5.5, -1.5), inkcount(-57, -28, -5.5, -1.5)
    if not left > right > 0:
        c.fail("row 4 ink: III side (+y) %d vs II side (-y) %d" % (left, right))
    # handedness: the last glyph in game is the L of FELL (rightmost = most negative y); its foot points to the viewer's right (-y), the stem is on the +y side
    y_end = min(p.y for p in ink if -10.4 <= p.z <= -8.2)
    foot = min(p.y for p in ink if -10.4 <= p.z <= -10.05 and p.y < y_end + 2.5)
    top = min(p.y for p in ink if -8.6 <= p.z <= -8.25 and p.y < y_end + 2.5)
    if not (top - foot > 0.5):
        c.fail("text looks mirrored for the in-game view: foot of the final L reaches y %.2f, its stem top y %.2f" % (foot, top))
    c.notes.append("%d groove faces, floor x %.2f; III side ink %d / II side ink %d; final-L foot %.2f stem %.2f (in-game reading: ANSELM at +y)" % (
        sum(1 for poly in c.ob.data.polygons if poly.material_index == 1), min(p.x for p in ink), left, right, foot, top))


def chk_named_slab(c, name, year):
    c.expect("top z", c.mx.z, 8.0, 0.05)
    ink = carve_pts(c, 3)
    if not ink:
        c.fail("no MAT_Carve faces")
        return
    c.expect("groove floor z", min(p.z for p in ink), 8.0 - 0.8, 0.1)
    c.expect("groove rim z", max(p.z for p in ink), 8.0, 0.05)
    xs = sorted(p.x for p in ink)
    l2 = [p for p in ink if p.x < -33.0]
    l1 = [p for p in ink if p.x >= -33.0]
    if not l1 or not l2:
        c.fail("expected two carved lines (x -23.5..-16.5 and -47.5..-42.5)")
        return
    c.expect("line 1 centre x", 0.5 * (min(p.x for p in l1) + max(p.x for p in l1)), -20.0, 0.6)
    c.expect("line 2 centre x", 0.5 * (min(p.x for p in l2) + max(p.x for p in l2)), -45.0, 0.6)
    c.expect("line 1 cap height", max(p.x for p in l1) - min(p.x for p in l1), 7.0, 0.8)
    c.expect("line 2 cap height", max(p.x for p in l2) - min(p.x for p in l2), 5.0, 0.8)
    wid = max(abs(p.y) for p in ink)
    if wid > 36.0:
        c.fail("lettering reaches |y| %.2f (> 36, too close to the slab edge)" % wid)
    c.notes.append("%s %d: line 1 x %.1f..%.1f, line 2 x %.1f..%.1f, |y| max %.1f, groove floor z %.2f" % (
        name, year, min(p.x for p in l1), max(p.x for p in l1), min(p.x for p in l2), max(p.x for p in l2), wid, min(p.z for p in ink)))


# ----------------------------------------------------------------------------------------------
# spec table
# ----------------------------------------------------------------------------------------------
def spec():
    S = {}

    def add(name, mn, mx, slots, tris, ucx=0, check=None, tol=TOL):
        S[name] = dict(min=mn, max=mx, slots=slots, tris=tris, ucx=ucx, check=check, tol=tol)

    for sfx, seed in (("400x1300_A", 0), ("400x1300_B", 0), ("100x1300", 0)):
        L = 400 if sfx.startswith("400") else 100
        add(P + "Wall40_" + sfx, (0, -6, 0), (L, 40, 1300), KIT, 6000, check=lambda c: chk_wall(c, 1300, True))
    for sfx in ("400x800_A", "400x800_B", "100x800"):
        L = 400 if sfx.startswith("400") else 100
        add(P + "Wall40_" + sfx, (0, 0, 0), (L, 40, 800), KIT, 4000, check=lambda c: chk_wall(c, 800, False))
    for sfx in ("400x450", "100x450"):
        L = 400 if sfx.startswith("400") else 100
        add(P + "Wall40_" + sfx, (0, 0, 0), (L, 40, 450), KIT, 2500, check=lambda c: chk_wall(c, 450, False))
    add(P + "Archway_500x40x1300", (0, -6, 300), (500, 40, 1300), KIT, 8000, check=lambda c: chk_archway(c, 500.0, 300.0, 420.0))
    add(P + "Archway_300x40x1300", (0, -6, 330), (300, 40, 1300), KIT, 6000, check=lambda c: chk_archway(c, 300.0, 330.0, 450.0))
    add(P + "Pier_80x80x640", (-48, -48, 0), (48, 48, 620), KIT, 1500, check=lambda c: chk_pier(c, 40.0, 40.0))
    add(P + "PierCorner_130x80x640", (-73, -48, 0), (73, 48, 620), KIT, 1500, check=lambda c: chk_pier(c, 65.0, 40.0))
    for sp in (120, 170, 220, 270):
        add(P + "ArcadeArch_%dx80" % sp, (0, -45, 0), (sp, 45, 290), KIT, 3000, check=lambda c, sp=sp: chk_arcade_arch(c, sp))
    add(P + "GarthWall_1100x100", (0, -4, 0), (1100, 30, 100), KIT, 1500, check=chk_garth_wall)
    add(P + "GarthWall_800x100", (0, -4, 0), (800, 30, 100), KIT, 1200, check=chk_garth_wall)
    add(P + "GarthBed_1100x800", (0, 0, -8), (1100, 800, None), ["MAT_Earth"], 20000, check=chk_bed)
    add(P + "GraveSlab_200x80", (-100, -40, 0), (100, 40, 8), KIT, 400, check=chk_slab)
    add(P + "GraveCross_60", (-17, -4, 0), (17, 4, 60), KIT, 300)
    add(P + "GarthCross_350", (-60, -60, 0), (60, 60, 350), KIT, 600)
    for (nm, sp, L, br) in (("830x640", 830, 640, False), ("770x640", 770, 640, False), ("770x640_Broken", 770, 640, True), ("770x980", 770, 980, False), ("570x980", 570, 980, False)):
        add(P + "Vault_Barrel_" + nm, (0, 0, 0), (L, sp, 340), KIT, 6000, check=lambda c, sp=sp, L=L, br=br: chk_barrel(c, float(sp), float(L), br))
    for (nm, sx, sy, outer) in (("770x830", 770, 830, ('x0', 'y0')), ("570x830", 570, 830, ('x1', 'y0')), ("770x770", 770, 770, ('x0', 'y1')), ("570x770", 570, 770, ('x1', 'y1'))):
        add(P + "Vault_Groin_" + nm, (0, 0, 0), (sx, sy, 340), KIT, 26000, check=lambda c, sx=sx, sy=sy, outer=outer: chk_groin(c, float(sx), float(sy), outer))
    add(P + "LeanTo_1000x1050", (0, 0, -15), (1000, 1050, None), ROOF, 30000, check=lambda c: chk_leanto(c, False))
    add(P + "LeanTo_1000x1050_Hole", (0, 0, None), (1000, 1050, None), ROOF, 30000, check=lambda c: chk_leanto(c, True))
    add(P + "LeanTo_Valley_L_1000x1050", (0, 0, -15), (1000, 1050, 9.3), ROOF, 30000, tol=1.0, check=lambda c: chk_leanto_valley(c, 'L'))
    add(P + "LeanTo_Valley_R_1000x1050", (0, 0, -15), (1000, 1050, 9.3), ROOF, 30000, tol=1.0, check=lambda c: chk_leanto_valley(c, 'R'))
    add(P + "CellDoorFrame_150x270", (-75, -8, 0), (75, 2, 270), KIT, 1500, check=chk_cell)
    add(P + "StairHouseGable_380x40x650", (0, 0, 0), (380, 40, 650), KIT, 3000, check=chk_gable)
    add(P + "StairHouseRoof_420x640", (0, 0, None), (420, 640, 200), ROOF, 12000, check=chk_stair_roof)
    add(PP + "SmallBell_A", (-12, -12, -28), (12, 12, 4), ["MAT_Bronze", "MAT_Iron", "MAT_Band"], 2500, ucx=1, check=chk_bell)
    add(PP + "SmallBellBracket_A", (0, -11, -25), (34, 11, 22), ["MAT_Iron", "MAT_Wood"], 1500, check=chk_bracket)
    add(PP + "BellPlaque_A", (0, -17, -17), (4, 17, 17), ["MAT_Trim"], 400, check=lambda c: chk_plaque(c, 4.0, 1.0))
    add(PP + "InscriptionTablet_A", (0, -60, -15), (4, 60, 15), ["MAT_Trim"], 400, check=lambda c: chk_plaque(c, 4.0, 1.2))
    # P10-8d (D1.27 F1)
    for R in (20, 40, 60):
        add(PP + "LanternBracket_R%d" % R, (0, -4, -14), (R + 3.9, 4, 18), ["MAT_Iron"], 3000, check=lambda c, R=R: chk_lantern(c, float(R)))
    add(PP + "InscriptionTablet_Memorial", (0, -60, -15), (4, 60, 15), ["MAT_Trim", "MAT_Carve"], 60000, tol=0.1, check=chk_memorial)
    for nm, yr in (("Anselm", 1341), ("Tomas", 1344), ("Edwin", 1348), ("Osric", 1351)):
        add(P + "GraveSlab_200x80_" + nm, (-100, -40, 0), (100, 40, 8), KIT + ["MAT_Carve"], 20000, tol=0.1, check=lambda c, nm=nm, yr=yr: chk_named_slab(c, nm, yr))
    return S


def check_piece(path, name, sp):
    res = dict(name=name, ok=True, fails=[], notes=[])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    ucx = sorted([o for o in obs if o.name.startswith("UCX_")], key=lambda o: o.name)
    vis = [o for o in obs if not o.name.startswith("UCX_")]
    if len(vis) != 1:
        res.update(ok=False, fails=["expected 1 visual mesh, found %d" % len(vis)])
        return res
    ob = vis[0]
    c = Ctx(ob)
    if ob.name.split(".")[0] != name:
        c.fail("mesh name %s" % ob.name)
    mn, mx = c.mn, c.mx
    res['min'] = [round(v, 2) for v in mn]
    res['max'] = [round(v, 2) for v in mx]
    res['tris'] = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    for i, ax in enumerate("XYZ"):
        if sp['min'][i] is not None and abs(mn[i] - sp['min'][i]) > sp['tol']:
            c.fail("bounds min %s %.2f vs %.2f" % (ax, mn[i], sp['min'][i]))
        if sp['max'][i] is not None and abs(mx[i] - sp['max'][i]) > sp['tol']:
            c.fail("bounds max %s %.2f vs %.2f" % (ax, mx[i], sp['max'][i]))
    if res['tris'] > sp['tris']:
        c.fail("tris %d > cap %d" % (res['tris'], sp['tris']))
    if ob.matrix_world.translation.length > 1e-4:
        c.fail("node not at the origin")
    names = [m.name.split(".")[0] if m else None for m in ob.data.materials]
    res['slots'] = names
    if names != sp['slots']:
        c.fail("slots %s expected %s" % (names, sp['slots']))
    ca = [a.name for a in ob.data.color_attributes]
    if not ca:
        c.fail("no colour attribute")
    elif sum(1 for d in ob.data.color_attributes[0].data if min(d.color) < 0.99):
        c.fail("non-white vertex colour")
    if not ob.data.uv_layers:
        c.fail("no UV layer")
    if len(ob.data.corner_normals) == 0:
        c.fail("no normals")
    vol = VK.signed_volume(ob)
    res['volume_cm3'] = round(vol, 1)
    if vol <= 0:
        c.fail("non-positive volume (%.1f)" % vol)
    res['ucx'] = len(ucx)
    if len(ucx) != sp['ucx']:
        c.fail("UCX count %d expected %d (UCX only on M1)" % (len(ucx), sp['ucx']))
    for k, u in enumerate(ucx):
        if u.name.split(".")[0] != "UCX_%s_%02d" % (name, k):
            c.fail("UCX name %s" % u.name)
        if not VK.is_convex(u):
            c.fail("%s not convex" % u.name)
        b0, b1 = VK.bounds(VK.ue_coords(u))
        for i in range(3):
            if b0[i] < mn[i] - 1.0 or b1[i] > mx[i] + 1.0:
                c.fail("%s outside the visual bounds" % u.name)
                break
    if sp['check'] is not None:
        try:
            sp['check'](c)
        except Exception as e:  # a crashing check is a failure, never a silent pass
            c.fail("check raised %s: %s" % (type(e).__name__, e))
    res['fails'] = c.fails
    res['notes'] = c.notes
    res['ok'] = not c.fails
    c.bm.free()
    return res


def main():
    fbx, js, only = parse()
    S = spec()
    rows = []
    for name, sp in S.items():
        if only and not any(o in name for o in only):
            continue
        path = os.path.join(fbx, name + ".fbx")
        if not os.path.exists(path):
            rows.append(dict(name=name, ok=False, fails=["missing FBX"], notes=[]))
            continue
        rows.append(check_piece(path, name, sp))
    print("\n==== VERIFY CLOISTER SUMMARY ====")
    nm = lambda n: n.replace("SM_LB_Cl_", "").replace("SM_LB_Prop_", "P:")
    for r in rows:
        if 'min' not in r:
            print("%-34s %s" % (nm(r['name']), "; ".join(r['fails'])))
            continue
        dims = "%gx%gx%g" % tuple(round(r['max'][i] - r['min'][i], 2) for i in range(3))
        print("%-34s %-22s tris %-6d slots %-22s UCX %d  %s" % (nm(r['name']), dims, r['tris'], ",".join(s.replace("MAT_", "") for s in r['slots']), r['ucx'], "PASS" if r['ok'] else "FAIL: " + "; ".join(r['fails'])))
        if r['notes']:
            print("      " + " | ".join(r['notes']))
    ok = all(r['ok'] for r in rows)
    print("pieces: %d  passed: %d  failed: %d  => %s" % (len(rows), sum(1 for r in rows if r['ok']), sum(1 for r in rows if not r['ok']), "ALL PASS" if ok else "FAILURES"))
    if js:
        with open(js, "w") as fh:
            json.dump(rows, fh, indent=1)
    sys.stdout.flush()
    os._exit(0 if ok else 1)


if __name__ == "__main__":
    main()
