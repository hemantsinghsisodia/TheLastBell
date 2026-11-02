"""build_cloister.py -- P10-3b: cloister pieces C1..C17 and Mechanism 3 pieces M1..M4 (Docs/plans/P10_BELLTOWER_ART.md amendment D1.3 / D1.4).

    blender.exe -b --factory-startup --python Tools/blender/belltower/build_cloister.py -- [--out SourceArt/Cloister] [--only SUBSTR ...] [--tag NAME]

Writes one FBX per piece (flat in --out), one review .blend (LB_Cloister.blend, or LB_Cloister_<tag>.blend with --only/--tag) and
cloister_report.json (bounds / tris / slots / ucx).  Deterministic: every piece has the seed D1 lists.  Reuses build_kit / kit_lib by import
(neither is modified).  Authoring space == Unreal space (1 BU = 1 cm), FBX via kit_lib.export_piece_fbx (Y mirrored at export, see the kit README).

Deviations from D1 (also in README_cloister.md): see DEVIATIONS at the bottom of this docstring block / the README.
"""
import json
import math
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "Tools", "blender", "kit"))

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

import kit_lib as K  # noqa: E402
import build_kit as BK  # noqa: E402

S0, S1, S2 = K.SLOT_MASONRY, K.SLOT_TRIM, K.SLOT_RUBBLE
KIT_SLOTS = list(K.MAT_NAMES)
P = "SM_LB_Cl_"
P_PROP = "SM_LB_Prop_"

EXTRA_COLORS = {
    "MAT_Slate": (0.16, 0.17, 0.19, 1.0), "MAT_Wood": (0.34, 0.24, 0.15, 1.0), "MAT_Earth": (0.17, 0.12, 0.08, 1.0),
    "MAT_Iron": (0.10, 0.10, 0.11, 1.0), "MAT_Bronze": (0.42, 0.30, 0.17, 1.0), "MAT_Band": (0.55, 0.10, 0.08, 1.0),
    "MAT_Carve": (0.13, 0.125, 0.115, 1.0),     # P10-8d: carved lettering (grooves in the tablet field / grave slab tops)
}


# ==============================================================================================
# piece record + materials
# ==============================================================================================
class CP:
    """A cloister piece.  slots=None -> the three kit slots (MAT_Masonry, MAT_Trim, MAT_Rubble)."""

    def __init__(self, name, bm, slots=None, ucx=None, note="", smooth=30.0):
        self.name, self.bm, self.slots, self.ucx, self.note, self.smooth = name, bm, slots, ucx or [], note, smooth


def mats_for(slots):
    if slots is None:
        return K.get_materials()
    out = []
    base = dict(zip(K.MAT_NAMES, K.MAT_COLORS))
    for n in slots:
        m = bpy.data.materials.get(n)
        if m is None:
            m = bpy.data.materials.new(n)
            m.diffuse_color = base.get(n) or EXTRA_COLORS[n]
            m.roughness = 0.9
        out.append(m)
    return out


def free(*bms):
    for b in bms:
        if b is not None:
            b.free()


def smooth01(k):
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


def poly_dedupe(pts, eps=1e-6):
    out = []
    for p in pts:
        if not out or abs(p[0] - out[-1][0]) > eps or abs(p[1] - out[-1][1]) > eps:
            out.append(p)
    if len(out) > 2 and abs(out[0][0] - out[-1][0]) < eps and abs(out[0][1] - out[-1][1]) < eps:
        out.pop()
    return out


def translate(bm, dx=0.0, dy=0.0, dz=0.0):
    bmesh.ops.translate(bm, vec=(dx, dy, dz), verts=bm.verts)
    return bm


def mirror_x(bm, cx):
    for v in bm.verts:
        v.co.x = 2 * cx - v.co.x
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return bm


def sweep(path, prof, mat=S1, up=(0.0, 0.0, 1.0), caps=True, horizontal_side=False):
    """Sweep a convex 2D profile [(a, b), ...] (a along `side`, b along `upv`) along a polyline of Vectors."""
    bm = bmesh.new()
    n = len(path)
    rings = []
    for i in range(n):
        if i == 0:
            t = path[1] - path[0]
        elif i == n - 1:
            t = path[-1] - path[-2]
        else:
            t = path[i + 1] - path[i - 1]
        t = t.normalized()
        if horizontal_side:                          # side stays horizontal even where the path turns near-vertical; b points up
            side = Vector((-t.y, t.x, 0.0)).normalized()
            upv = t.cross(side).normalized()
        else:
            u = Vector(up)
            if abs(t.dot(u)) > 0.98:
                u = Vector((1.0, 0.0, 0.0))
            side = t.cross(u).normalized()
            upv = side.cross(t).normalized()
        rings.append([bm.verts.new(path[i] + side * a + upv * b) for a, b in prof])
    m = len(prof)
    for i in range(n - 1):
        for j in range(m):
            j2 = (j + 1) % m
            try:
                bm.faces.new((rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]))
            except ValueError:
                pass
    if caps:
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])
    K._outward(bm)
    K.bm_set_mat(bm, mat)
    return bm


def circle_prof(r, segs=8):
    return [(r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs)) for i in range(segs)]


def rect_prof(w, h):
    return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]


def uvsphere(r, centre, mat, segs=12, rings=8):
    b = bmesh.new()
    bmesh.ops.create_uvsphere(b, u_segments=segs, v_segments=rings, radius=r)
    for v in b.verts:
        v.co += Vector(centre)
    K._outward(b)
    K.bm_set_mat(b, mat)
    return b


def torus_xz(R, r, centre, mat, segs_major=16, segs_minor=6):
    """Torus lying in the XZ plane (axis along Y) centred at `centre`."""
    cx, cy, cz = centre
    path = []
    for i in range(segs_major):
        a = 2 * math.pi * i / segs_major
        path.append(Vector((cx + R * math.cos(a), cy, cz + R * math.sin(a))))
    bm = bmesh.new()
    rings = []
    for i in range(segs_major):
        a = 2 * math.pi * i / segs_major
        radial = Vector((math.cos(a), 0.0, math.sin(a)))
        ring = []
        for j in range(segs_minor):
            t = 2 * math.pi * j / segs_minor
            p = path[i] + radial * (r * math.cos(t)) + Vector((0.0, 1.0, 0.0)) * (r * math.sin(t))
            ring.append(bm.verts.new(p))
        rings.append(ring)
    for i in range(segs_major):
        i2 = (i + 1) % segs_major
        for j in range(segs_minor):
            j2 = (j + 1) % segs_minor
            bm.faces.new((rings[i][j], rings[i][j2], rings[i2][j2], rings[i2][j]))
    K._outward(bm)
    K.bm_set_mat(bm, mat)
    return bm


# ==============================================================================================
# four-centred section (D1.3): lower arcs radius r1 centred on the springing line at r1 from each side,
# upper arcs tangent to them and meeting at the apex.  Section frame: y across (0..span), z up (springing z = 0).
# ==============================================================================================
def _fc_solve(s, h, r1, beta_deg):
    b = math.radians(beta_deg)
    n = (-math.sin(b), math.cos(b))                     # unit vector C1 -> tangent point T
    ax, az = s / 2 - r1, h                              # A - C1
    na = n[0] * ax + n[1] * az
    den = 2.0 * (r1 - na)
    if abs(den) < 1e-9:
        return None
    D = (ax * ax + az * az - r1 * r1) / den
    if D <= 0:
        return None
    C2 = (r1 - D * n[0], -D * n[1])
    R2 = D + r1
    gam = math.degrees(math.atan2(C2[0] - s / 2, h - C2[1]))
    return dict(beta=beta_deg, D=D, R2=R2, C2=C2, gamma=gam)


def four_centred(span, rise, r1=None, gamma_deg=None, R2_target=None):
    """Solve the four-centred section.  r1 defaults to span/4 (D1); the free tangent angle beta is solved numerically so that either the upper
    radius equals R2_target or the apex tangent slope equals gamma_deg.  If span/4 admits no pointed solution (flat arches), r1 is reduced.
    Returns a FourCentred (check .r1 against span/4 for the deviation note)."""
    cand = [r1] if r1 else [span / 4.0 * f for f in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.25, 0.2, 0.15)]
    for rr in cand:
        betas = [0.25 * i for i in range(1, 359)]
        prev = None
        for bd in betas:
            sol = _fc_solve(span, rise, rr, bd)
            ok = sol is not None and sol['C2'][0] >= span / 2 + 1e-6
            if not ok:
                prev = None
                continue
            val = (sol['R2'] - R2_target) if R2_target else (sol['gamma'] - gamma_deg)
            if prev is not None and (val == 0 or (val > 0) != (prev[1] > 0)):
                lo, hi = prev[0], bd
                flo = prev[1]
                for _ in range(60):
                    mid = 0.5 * (lo + hi)
                    sm = _fc_solve(span, rise, rr, mid)
                    if sm is None:
                        break
                    fm = (sm['R2'] - R2_target) if R2_target else (sm['gamma'] - gamma_deg)
                    if (fm > 0) == (flo > 0):
                        lo, flo = mid, fm
                    else:
                        hi = mid
                sol = _fc_solve(span, rise, rr, 0.5 * (lo + hi))
                return FourCentred(span, rise, rr, sol)
            prev = (bd, val)
    raise RuntimeError("no four-centred solution for span %g rise %g" % (span, rise))


class FourCentred:
    def __init__(self, s, h, r1, sol):
        self.s, self.h, self.r1 = s, h, r1
        self.beta = sol['beta']
        self.R2, self.C2, self.gamma = sol['R2'], sol['C2'], sol['gamma']
        self.C1 = (r1, 0.0)
        b = math.radians(self.beta)
        self.phi = math.pi / 2 + b                        # lower arc angle at T (from +y axis of the section frame, counter-clockwise)
        self.th_T = math.pi / 2 - b                       # upper arc angle at T measured on the left-hand arc

    # offset t > 0 is inward (smaller radius), t < 0 outward
    def th_A(self, t):
        return math.acos(max(-1.0, min(1.0, (self.C2[0] - self.s / 2) / (self.R2 - t))))

    def lower(self, t, k):
        a = math.pi + (self.phi - math.pi) * k
        rho = self.r1 - t
        return (self.C1[0] + rho * math.cos(a), rho * math.sin(a))

    def upper(self, t, k, th_end=None):
        th1 = self.th_A(t) if th_end is None else th_end
        th = self.th_T + (th1 - self.th_T) * k
        rho = self.R2 - t
        return (self.C2[0] - rho * math.cos(th), self.C2[1] + rho * math.sin(th))

    def left(self, t, nl=8, nu=12):
        pts = [self.lower(t, i / nl) for i in range(nl)]
        pts += [self.upper(t, i / nu) for i in range(nu + 1)]
        return pts

    def full(self, t, nl=8, nu=12):
        lp = self.left(t, nl, nu)
        rp = [(self.s - y, z) for (y, z) in lp[::-1]]
        return poly_dedupe(lp + rp[1:] if abs(lp[-1][0] - self.s / 2) < 1e-6 else lp + rp)

    def z_at(self, y, t=0.0):
        """Height of the offset curve at y (None outside)."""
        if y > self.s / 2:
            y = self.s - y
        rho1 = self.r1 - t
        yT = self.C1[0] + rho1 * math.cos(self.phi)
        if y < self.C1[0] - rho1 - 1e-9:
            return None
        if y <= yT:
            d = rho1 * rho1 - (y - self.C1[0]) ** 2
            return math.sqrt(max(0.0, d))
        rho2 = self.R2 - t
        d = rho2 * rho2 - (self.C2[0] - y) ** 2
        return self.C2[1] + math.sqrt(max(0.0, d))

    def sample_ys(self, t, nl=10, nu=14):
        """Section sample positions (left half, then mirrored) for grid building."""
        ys = [p[0] for p in self.left(t, nl, nu)]
        ys = sorted(set([round(y, 4) for y in ys] + [round(self.s - y, 4) for y in ys]))
        return ys


# ==============================================================================================
# C1..C3 plain walls (kit build_wall at T = 40) with the C1 inner-face drip course
# ==============================================================================================
def drip_course(L, z0=1210.0, z1=1230.0, proj=6.0):
    poly = [(0.0, z0), (-proj, z0 + 3.0), (-proj, z1 - 6.0), (0.0, z1)]       # (y, z)
    d = K.prism(poly, 'x', 0.0, L, S1)
    K.bevel_all(d, 0.8, 25.0)
    return d


def build_wall40(short, L, H, seed, vary=False, drip=False):
    pc = BK.build_wall(P + short, L, H, seed, vary=vary, T=40.0)
    bm = pc.bm
    if drip:
        d = drip_course(L)
        K.bm_append(bm, d)
        d.free()
    free(*pc.ucx)
    return CP(P + short, bm, None, note="T 40, inner face y 0%s" % ("; drip course y -6..0 at z 1210..1230 (inner face only)" if drip else ""))


# ==============================================================================================
# C4 / C5 archways: tympanum of the full-width four-centred opening
# ==============================================================================================
def ring_stones_fc(fc, w_ring, n_low, n_up, ya, yb, seed, x_clip, alt=6.0, z_off=0.0, bevel=1.5):
    """Voussoirs of the four-centred ring (outside the intrados, radial width w_ring), both halves, extruded over y in [ya, yb] and clipped to x_clip."""
    rng = random.Random(seed)
    out = bmesh.new()
    s = fc.s
    nsub = 3
    stones = []
    for arc, n in (('l', n_low), ('u', n_up)):
        for i in range(n):
            k0, k1 = i / n, (i + 1) / n
            last = (arc == 'u' and i == n - 1)
            odd = (len(stones) % 2 == 1)
            tout = -(w_ring + (alt if odd and not last else 0.0))
            if rng.random() < 0.12 and not last and len(stones) > 0:
                tout = -(w_ring + (alt if not odd else 0.0))
            ks = [k0 + (k1 - k0) * j / nsub for j in range(nsub + 1)]
            if arc == 'l':
                inner = [fc.lower(0.0, k) for k in ks]
                outer = [fc.lower(tout, k) for k in ks]
            else:
                th_in = fc.th_A(0.0)
                inner = [fc.upper(0.0, k, th_in) for k in ks]
                outer = [fc.upper(tout, k, th_in) for k in ks]
                if last:                                 # final voussoir runs to the axis of symmetry
                    ap = fc.upper(tout, 1.0)
                    outer = outer[:-1] + [ap]
            poly = inner + outer[::-1]
            stones.append(poly)
    for side in (0, 1):
        for poly in stones:
            pl = [(x, z + z_off) for (x, z) in poly]
            if side == 1:
                pl = [(s - x, z) for (x, z) in pl][::-1]
            pl = BK.clip_x(poly_dedupe(pl), x_clip[0], x_clip[1])
            if len(pl) < 3:
                continue
            st = K.prism(pl, 'y', ya, yb, S1)
            if min(p[1] for p in pl) > z_off + 3.0:                      # springers keep a sharp bottom edge (springing line exact)
                K.bevel_all(st, 0.3 if poly is stones[-1] else bevel, 25.0)   # keystones: tiny chamfer so the apex height stays exact
            K.bm_append(out, st)
            st.free()
    return out


def build_archway(short, span, spring_z, apex_z, seed):
    H, T = 1300.0, 40.0
    rise = apex_z - spring_z
    fc = four_centred(span, rise, gamma_deg=9.0)
    z_body = H - BK.CAP_H
    body = K.box(0, span, 0, T, spring_z, z_body, S0)
    courses = K.make_courses(z_body, seed, False)
    z_rel0 = math.floor(spring_z / 50.0) * 50.0
    relief = BK.relief_both(span, T, z_rel0, z_body, courses, seed, z_start=0.0, wmin=70, wmax=150)
    w_ring = 40.0
    n_low, n_up = 3, 6
    stones = ring_stones_fc(fc, w_ring, n_low, n_up, 0.0, T, seed + 3, (0.0, span), alt=6.0, z_off=spring_z)
    # carve polygon: everything inside the ring's outer outline
    ext = fc.full(-w_ring, 8, 16)
    carve_poly = [(ext[0][0], spring_z - 1.0)] + [(x, z + spring_z) for (x, z) in ext] + [(ext[-1][0], spring_z - 1.0)]
    carve = K.prism(poly_dedupe(carve_poly), 'y', -1.0, T + 1.0, S1)
    shell = BK.carve_and_merge(body, [relief, carve], [stones])
    capm = BK.cap_course(span, T, z_body, H, seed)
    drp = drip_course(span)
    out = K.combine(shell, capm, drp)
    free(body, relief, carve, shell, capm, stones, drp)
    note = "tympanum of a full-width four-centred opening: springing z %g at x 0 and %g, apex z %g; lower radius %.1f (span/4 = %.1f), upper radius %.1f, apex slope %.1f deg; ring radial width %g; drip y -6..0 at z 1210..1230 (cloister face only); no mesh below the springing line" % (
        spring_z, span, apex_z, fc.r1, span / 4.0, fc.R2, fc.gamma, w_ring)
    pc = CP(P + short, out, None, note=note)
    pc.fc = fc
    pc.spring_z, pc.apex_z = spring_z, apex_z
    return pc


# ==============================================================================================
# C6 / C7 piers (bottom-centre pivot) and C8 arcade arches
# ==============================================================================================
def rect_oct(hx, hy, c):
    """Rectangle (half sizes hx, hy) with corners cut by c, counter-clockwise."""
    if c <= 0:
        return [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    return [(-hx + c, -hy), (hx - c, -hy), (hx, -hy + c), (hx, hy - c), (hx - c, hy), (-hx + c, hy), (-hx, hy - c), (-hx, -hy + c)]


def loft_rings(rings, z_list, mat=S1):
    """Closed solid lofted through XY rings (same vertex count) at the given z levels."""
    b = bmesh.new()
    vr = [[b.verts.new((x, y, z)) for (x, y) in r] for r, z in zip(rings, z_list)]
    n = len(rings[0])
    b.faces.new(vr[0][::-1])
    b.faces.new(vr[-1])
    for k in range(len(vr) - 1):
        for i in range(n):
            j = (i + 1) % n
            b.faces.new((vr[k][i], vr[k][j], vr[k + 1][j], vr[k + 1][i]))
    K._outward(b)
    K.bm_set_mat(b, mat)
    return b


def prism_z(poly, z0, z1, mat):
    return K.prism(poly, 'z', z0, z1, mat)


def face_relief_xy(hx, hy, z0, z1, courses, seed, u_inset, **kw):
    """Relief cutters on the four faces of a pier body: x = +-hx faces (u along y) and y = +-hy faces (u along x)."""
    cut = bmesh.new()
    frames = [
        (K.FaceFrame((hx, -hy + u_inset, 0), (0, 1, 0), (1, 0, 0)), 2 * (hy - u_inset)),
        (K.FaceFrame((-hx, hy - u_inset, 0), (0, -1, 0), (-1, 0, 0)), 2 * (hy - u_inset)),
        (K.FaceFrame((hx - u_inset, hy, 0), (-1, 0, 0), (0, 1, 0)), 2 * (hx - u_inset)),
        (K.FaceFrame((-hx + u_inset, -hy, 0), (1, 0, 0), (0, -1, 0)), 2 * (hx - u_inset)),
    ]
    for i, (fr, ln) in enumerate(frames):
        c = K.relief_cutters(fr, 0.0, ln, z0, z1, courses, seed + 11 * i, z_start=0.0, wmin=70, wmax=150, chips=2, recess_prob=0.15, **kw)
        K.bm_append(cut, c)
        c.free()
    return cut


def build_pier(short, hx, hy, seed):
    """Pivot bottom centre.  base 0-25 (+4), chamfered shaft 25-300 (faces at +-hx, +-hy), bell capital 300-330 (+8), wall block 330-600,
    coping 600-620 (+5) -- D1.3 C6/C7.  Top at z 620 (D1.11: the name x640 is kept, tops are at 620)."""
    parts = []
    # base moulding z 0..25 projecting 4 (chamfered top)
    base = K.box(-hx - 4, hx + 4, -hy - 4, hy + 4, 0, 25, S1, 0.0)
    K.bevel_all(base, 3.0, 20.0)
    parts.append(base)
    # shaft z 25..300, 6 cm chamfered corners, ashlar relief
    shaft = prism_z(rect_oct(hx, hy, 6.0), 25.0, 300.0, S0)
    courses = K.make_courses(640.0, seed, False)
    rel = face_relief_xy(hx, hy, 25.0, 300.0, courses, seed, 6.0)
    sh = K.boolean_diff(shaft, rel)
    free(shaft, rel)
    parts.append(sh)
    # bell capital z 300..330 projecting 8: ogee flare of an octagon-cornered rectangle
    rings, zs = [], []
    nk = 7
    for i in range(nk + 1):
        k = i / nk
        f = smooth01(k)
        e = 8.0 * (f * f * 0.35 + f * 0.65)
        rings.append(rect_oct(hx + e, hy + e, 6.0 + 2.0 * f))
        zs.append(300.0 + 30.0 * k)
    cap = loft_rings(rings, zs, S1)
    parts.append(cap)
    # wall block z 330..600 (80 x 80, relief on the faces)
    blk = K.box(-hx, hx, -hy, hy, 330.0, 600.0, S0)
    rel2 = face_relief_xy(hx, hy, 330.0, 600.0, courses, seed + 5, 0.0)
    bl = K.boolean_diff(blk, rel2)
    free(blk, rel2)
    parts.append(bl)
    # coping z 600..620 projecting 5 on all faces
    cop = K.box(-hx - 5, hx + 5, -hy - 5, hy + 5, 600.0, 620.0, S1, 0.0)
    K.bevel_all(cop, 2.5, 20.0)
    parts.append(cop)
    out = K.combine(*parts)
    free(*parts)
    return CP(P + short, out, None, note="pivot bottom centre; base +4, shaft faces at +-%g/+-%g z 25..300, capital +8, block z 330..600, coping +5 z 600..620, top z 620 (name keeps x640, D1.11)" % (hx, hy))


def build_arcade_arch(short, span, seed):
    """Pivot = left springing point on the pier line; x 0..span, y -40..40, z 0..290.  Two-centred pointed arch R = 0.8 span."""
    T0, T1 = -40.0, 40.0
    arch = BK.DropArch(0.0, float(span), R=0.8 * span)
    z_sp = 270.0
    body = K.box(0, span, T0, T1, 0, z_sp, S0)
    courses = K.make_courses(z_sp, seed, False)
    f = K.FaceFrame((0, T0, 0), (1, 0, 0), (0, -1, 0))
    b = K.FaceFrame((span, T1, 0), (-1, 0, 0), (0, 1, 0))
    relief = K.relief_cutters(f, 0, span, 0, z_sp, courses, seed, z_start=0.0, wmin=70, wmax=150, chips=2)
    K.bm_append(relief, K.relief_cutters(b, 0, span, 0, z_sp, courses, seed + 101, z_start=0.0, wmin=70, wmax=150, chips=2))
    w_ring = 30.0
    rng = random.Random(seed + 3)
    n = max(4, int(round(arch.length / 34.0)))
    stones = bmesh.new()
    for ai, side in enumerate((-1, 1)):
        for k in range(n):
            u0, u1 = k / n, (k + 1) / n
            alt = 5.0 if (k % 2 == 1 and k != n - 1) else 0.0
            if rng.random() < 0.15 and k not in (0, n - 1):
                alt = 5.0 - alt
            uu = [u0 + (u1 - u0) * i / 3.0 for i in range(4)]
            inner = [arch.pt(u, 0.0) for u in uu]
            outer = [arch.pt(u, w_ring + alt) for u in uu]
            poly = inner + outer[::-1]
            if side > 0:
                poly = [arch.mirror(p) for p in poly][::-1]
            poly = BK.clip_x(poly, 0.0, float(span))
            if len(poly) < 3:
                continue
            s = K.prism(poly_dedupe(poly), 'y', T0, T1, S1)
            if min(p[1] for p in poly) > 3.0:
                K.bevel_all(s, 0.3 if k == n - 1 else 1.5, 25.0)
            K.bm_append(stones, s)
            s.free()
    left = arch.curve_left(w_ring, 30)
    right = [arch.mirror(p) for p in left][::-1]
    cp = [(left[0][0] - 1.0, -1.0)] + left + right[1:] + [(right[0][0] + 1.0, -1.0)]
    carve = K.prism(poly_dedupe(cp), 'y', T0 - 1.0, T1 + 1.0, S1)
    shell = BK.carve_and_merge(body, [relief, carve], [stones])
    cop = K.box(0, span, T0 - 5.0, T1 + 5.0, 270.0, 290.0, S1, 0.0)
    K.bevel_all(cop, 2.0, 20.0)
    out = K.combine(shell, cop)
    free(body, relief, carve, shell, cop, stones)
    return CP(P + short, out, None, note="pivot = left springing point, x 0..%d, two-centred R %.1f, intrados apex z %.2f, spandrel top 270, coping 270..290 (+5)" % (span, 0.8 * span, arch.z_at(span / 2.0, 0.0)))


# ==============================================================================================
# C9 garth walls, C10 garth bed, C11 grave furniture
# ==============================================================================================
def build_garth_wall(short, L, seed):
    body = K.box(0, L, 0, 15, 0, 88, S0)
    courses = K.make_courses(88.0, seed, False, unit=22)
    fr = K.FaceFrame((0, 0, 0), (1, 0, 0), (0, -1, 0))
    rel = K.relief_cutters(fr, 0, L, 0, 88, courses, seed, z_start=0.0, wmin=70, wmax=150, chips=3, recess_prob=0.15)
    shell = K.boolean_diff(body, rel)
    cop = BK.cap_course(L, 34.0, 88.0, 100.0, seed, ctop=2.5, cbot=1.5)
    translate(cop, dy=-4.0)
    out = K.combine(shell, cop)
    free(body, rel, shell, cop)
    return CP(P + short, out, None, note="y 0 = walk-facing face, body to y +15, coping y -4..+30 at z 88..100 (top exactly 100)")


GRAVES_LOCAL = [(200, 200), (200, 600), (400, 250), (700, 600), (900, 200), (900, 550)]       # slab centres in the bed frame (world - (10300, 1400))
CROSS_LOCAL = (550.0, 400.0)


def build_garth_bed(short, seed):
    L, W = 1100.0, 800.0
    rng = random.Random(seed)
    jit = [(rng.uniform(-4, 4), rng.uniform(-1, 1)) for _ in GRAVES_LOCAL]

    def f(x, y):
        edge = min(x, L - x, y, W - y)
        if edge <= 35.0:                                  # D1.11: outer 35 cm band flat at z -1 (just under the C9 coping, top = bed z 0)
            return -1.0
        mask = smooth01((edge - 35.0) / 25.0)
        n1 = K.fbm(x / 70.0 + 3.0, y / 70.0 + 7.0, seed, 3)
        n2 = K.vnoise(x / 18.0, y / 18.0, seed + 5)
        h = 2.0 + 8.0 * smooth01((n1 - 0.30) / 0.5) * (0.85 + 0.3 * n2)
        h = min(h, 9.8)
        h = -1.0 + (h + 1.0) * mask
        # grave hollows (shallow)
        for (gx, gy), (jy, _) in zip(GRAVES_LOCAL, jit):
            a = math.radians(jy)
            dx, dy = x - gx, y - gy
            u = dx * math.cos(a) + dy * math.sin(a)
            v = -dx * math.sin(a) + dy * math.cos(a)
            q = max(abs(u) / 108.0, abs(v) / 48.0)
            hol = 1.0 - smooth01((q - 0.85) / 0.35)
            h = h * (1.0 - hol) + (-2.5 + 0.8 * n2) * hol
        # flat apron around the cross base
        dc = math.hypot(x - CROSS_LOCAL[0], y - CROSS_LOCAL[1])
        flat = 1.0 - smooth01((dc - 70.0) / 40.0)
        h = h * (1.0 - flat) + 1.0 * flat
        return h

    na, nb = 92, 67
    bm = K.hf_solid(0.0, L, 0.0, W, f, -8.0, na, nb, ('x', 'y', 'z'), S0, rng)
    return CP(P + short, bm, ["MAT_Earth"], note="earth bed over the garth block: z -8 (back plane) .. surface -2.5..+9.8; outer 35 cm band flat at z -1 (D1.11); six hollows under the slabs; flat apron around the cross", smooth=40.0)


def chamfer_slab(hx, hy, z0, z1, c, mat):
    s = K.box(-hx, hx, -hy, hy, z0, z1, mat, c)
    return s


def build_grave_slab(short, seed):
    s = K.box(-100, 100, -40, 40, 0, 8, S1, 0.0)
    K.bevel_all(s, 1.6, 20.0)
    # worn cross relief on the top face
    cut = bmesh.new()
    for (x0, x1, y0, y1) in ((-6, 6, -30, 28), (-20, 20, 8, 17)):
        c = K.box(x0 + 40, x1 + 40, y0, y1, 6.6, 9.0, S2, 0.0)       # cross sits towards the head (+x)
        K.bm_append(cut, c)
        c.free()
    # worn chips on two corners
    rng = random.Random(seed)
    for (cx, cy) in ((-100, -40), (100, 40)):
        pts = [Vector((cx + rng.uniform(-6, 6), cy + rng.uniform(-5, 5), 8 + rng.uniform(-0.5, 2))) for _ in range(6)]
        pts += [Vector((cx - math.copysign(5, cx) + rng.uniform(-3, 3), cy - math.copysign(5, cy), 6.0)) for _ in range(2)]
        h = K.hull_from_points(pts, S2, merge_coplanar=False)
        K.bm_append(cut, h)
        h.free()
    out = K.boolean_diff(s, cut)
    free(s, cut)
    return CP(P + short, out, None, note="pivot bottom centre; 200 x 80 x 8, chamfered, worn cross relief on the top; box-projected UVs (lichen-ready, 1 UV = 100 cm)")


def build_grave_cross(short, seed):
    parts = [K.box(-4, 4, -4, 4, 0, 60, S1, 0.0), K.box(-17, 17, -4, 4, 36, 46, S1, 0.0)]
    out = K.combine(*parts)
    free(*parts)
    K.bevel_all(out, 0.9, 20.0)
    rng = random.Random(seed)
    # a chipped arm end
    cut = K.hull_from_points([Vector((17 + rng.uniform(-1, 3), rng.uniform(-6, 6), 46 + rng.uniform(-1, 2))) for _ in range(6)], S2, merge_coplanar=False)
    res = K.boolean_diff(out, cut)
    free(out, cut)
    return CP(P + short, res, None, note="pivot bottom centre; 60 tall, 8 thick, arms 34 wide at z 36..46")


def build_garth_cross(short, seed):
    parts = []
    parts.append(K.box(-60, 60, -60, 60, 0, 20, S1, 2.0))
    parts.append(K.box(-45, 45, -45, 45, 20, 40, S1, 2.0))
    shaft = K.prism([(-12 + 3, -12), (12 - 3, -12), (12, -12 + 3), (12, 12 - 3), (12 - 3, 12), (-12 + 3, 12), (-12, 12 - 3), (-12, -12 + 3)], 'z', 40, 290, S1)
    parts.append(shaft)
    parts.append(K.box(-17, 17, -17, 17, 290, 302, S1, 2.0))            # collar
    parts.append(K.box(-12, 12, -12, 12, 300, 350, S1, 1.6))            # head post
    parts.append(K.box(-45, 45, -12, 12, 312, 336, S1, 1.6))            # arms (90 wide)
    out = K.combine(*parts)
    free(*parts)
    return CP(P + short, out, None, note="pivot bottom centre; base 120 x 120 x 20 + 90 x 90 x 20, chamfered shaft 24 x 24 to z 290, collar, head 90 wide, top z 350")


# ==============================================================================================
# C12 barrel vaults / C13 groin vaults.  Pivot = the bay's min corner at the springing level; local x along the walk (length), y across (span).
# Four-centred section, rise 340 measured to the EXTRADOS apex (bounds top z 340), shell 25 thick, ribs 30 wide x 25 deep below the intrados.
# ==============================================================================================
VAULT_RISE = 340.0
SHELL_T = 25.0
RIB_W = 30.0
RIB_D = 25.0


def vault_fc(span):
    return four_centred(span, VAULT_RISE, R2_target=float(span))


def ring_poly(fc, t0, t1):
    """(y, z) outline of the band between the inward offsets t0 < t1 of the section (closed by the springing line z = 0)."""
    a = fc.full(t0, 10, 16)
    b = fc.full(t1, 10, 16)
    return poly_dedupe(a + b[::-1])


def pip(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            if x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                inside = not inside
    return inside


def build_barrel(short, span, L, seed, broken=False):
    fc = vault_fc(span)
    shell = K.prism(ring_poly(fc, 0.0, SHELL_T), 'x', 0.0, L, S0)
    parts = [shell]
    rib_poly = ring_poly(fc, SHELL_T - 3.0, SHELL_T + RIB_D)
    for (xa, xb) in ((0.0, 15.0), (L / 2 - RIB_W / 2, L / 2 + RIB_W / 2), (L - 15.0, L)):
        rb = K.prism(rib_poly, 'x', xa, xb, S1)
        K.bevel_all(rb, 1.2, 25.0)
        parts.append(rb)
    out = K.combine(*parts)
    free(*parts)
    note = ("x = length %g along the walk, y = span %g across; four-centred section: lower radius %.1f, upper radius %.1f, apex slope %.1f deg, "
            "extrados apex z %g; shell 25; ribs 30 wide x 25 deep at x 0..15, %g..%g, %g..%g (end ribs are 15 wide so two bays make one 30 rib)") % (
        L, span, fc.r1, fc.R2, fc.gamma, VAULT_RISE, L / 2 - 15, L / 2 + 15, L - 15, L)
    if broken:
        rng = random.Random(1231)
        mid = span / 2.0
        # ragged plan outline of the hole: steps of 40-60 cm along x, small jags on the ends; always contains x 50..600 x (mid +- 70)
        xs = [50.0]
        while xs[-1] < 600.0:
            xs.append(min(600.0, xs[-1] + rng.uniform(38.0, 62.0)))
        hw = [rng.uniform(0.20, 0.36) * span for _ in xs[:-1]]
        hl = [rng.uniform(0.18, 0.34) * span for _ in xs[:-1]]
        xl = rng.uniform(36.0, 49.0)
        poly = [(xl, mid - 80.0), (xl, mid + 80.0)]
        for i, w in enumerate(hw):
            poly += [(xs[i] if i else xl, mid + w), (xs[i + 1], mid + w)]
        xr = 600.0 + rng.uniform(1.0, 12.0)
        poly += [(xr, mid + hw[-1]), (xr, mid + 60.0), (xr + rng.uniform(0, 4), mid + 20.0), (xr, mid - 70.0), (xr, mid - hl[-1])]
        for i in range(len(hl) - 1, -1, -1):
            poly += [(xs[i + 1], mid - hl[i]), (xs[i] if i else xl, mid - hl[i])]
        poly = poly_dedupe(poly)
        cut = K.prism(poly, 'z', -5.0, VAULT_RISE + 40.0, S2)
        res = K.boolean_diff(out, cut)
        free(out, cut)
        out = res
        note += "; ragged hole through the shell and ribs (plan polygon x %.0f..%.0f), mid rib snapped leaving two stubs on the haunches, fracture faces MAT_Rubble" % (xl, xr)
    return CP(P + short, out, None, note=note)


def _solve_crease(fc, v, t):
    """y in [start, s/2] where the offset-t curve has height v (the curve is monotone on the left half)."""
    s = fc.s
    start = 0.0 if t == 0.0 else t
    if v <= 1e-6:
        return start
    top = fc.z_at(s / 2, t)
    if v >= top - 1e-9:
        return s / 2
    lo, hi = start, s / 2
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        zz = fc.z_at(mid, t) or 0.0
        if zz < v:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def zip_strip(bm, VA, XA, VB, XB, flip=False):
    """Triangulate between two vertex rows (left to right).  VA lower row, VB upper row."""
    i = j = 0
    na, nb = len(VA), len(VB)
    while i < na - 1 or j < nb - 1:
        if i == na - 1:
            tri = (VA[i], VB[j + 1], VB[j])
            j += 1
        elif j == nb - 1:
            tri = (VA[i], VA[i + 1], VB[j])
            i += 1
        elif XA[i + 1] <= XB[j + 1]:
            tri = (VA[i], VA[i + 1], VB[j])
            i += 1
        else:
            tri = (VA[i], VB[j + 1], VB[j])
            j += 1
        if flip:
            tri = tri[::-1]
        try:
            bm.faces.new(tri)
        except ValueError:
            pass


def build_groin(short, Sx, Sy, outer, seed):
    """Union of two perpendicular four-centred barrels clipped to the Sx x Sy rectangle: intrados z = max(zA(x), zB(y)), extrados likewise (+shell)."""
    fcx, fcy = vault_fc(Sx), vault_fc(Sy)

    def ze(fc, y):
        return fc.z_at(y, 0.0) or 0.0

    def zi(fc, y):
        return fc.z_at(y, SHELL_T) or 0.0

    def row_xs(fc):
        return sorted(set(fc.sample_ys(0.0, 6, 9) + fc.sample_ys(SHELL_T, 6, 9)))

    xs0, ys0 = row_xs(fcx), row_xs(fcy)
    ys = sorted(set([round(v, 3) for v in ys0] + [0.0, round(Sy / 2, 3), round(Sy, 3)]))
    bm = bmesh.new()
    rows = []
    for y in ys:
        vt, vb = ze(fcy, y), zi(fcy, y)
        xt1 = _solve_crease(fcx, vt, 0.0)
        xb1 = _solve_crease(fcx, vb, SHELL_T)
        xl = list(xs0) + [xt1, Sx - xt1, xb1, Sx - xb1]
        xl = sorted(set([round(v, 4) for v in xl if -1e-9 <= v <= Sx + 1e-9]))
        merged = []
        for v in xl:
            if merged and v - merged[-1] < 0.04:
                continue
            merged.append(v)
        xl = merged

        def idx(val, xl=xl):
            return min(range(len(xl)), key=lambda k: abs(xl[k] - val))

        top = [bm.verts.new((x, y, max(ze(fcx, x), vt))) for x in xl]
        bot = [bm.verts.new((x, y, max(zi(fcx, x), vb))) for x in xl]
        rows.append(dict(y=y, xs=xl, top=top, bot=bot, ct=(idx(xt1), idx(Sx - xt1)), cb=(idx(xb1), idx(Sx - xb1)), xt1=xt1, xb1=xb1))
    for r0, r1 in zip(rows[:-1], rows[1:]):
        for surf, cr, flip in (('top', 'ct', True), ('bot', 'cb', False)):
            a0, a1 = r0[cr]
            b0, b1 = r1[cr]
            segs = [((0, a0), (0, b0)), ((a0, a1), (b0, b1)), ((a1, len(r0['xs']) - 1), (b1, len(r1['xs']) - 1))]
            for (sa, sb) in segs:
                if sa[1] < sa[0] or sb[1] < sb[0]:
                    continue
                VA, XA = r0[surf][sa[0]:sa[1] + 1], r0['xs'][sa[0]:sa[1] + 1]
                VB, XB = r1[surf][sb[0]:sb[1] + 1], r1['xs'][sb[0]:sb[1] + 1]
                if len(VA) == 1 and len(VB) == 1:
                    continue
                zip_strip(bm, VA, XA, VB, XB, flip)
    # side walls: x = 0 and x = Sx between rows, y = 0 and y = Sy along the first / last row
    for k in range(len(rows) - 1):
        a, b = rows[k], rows[k + 1]
        for side in (0, -1):
            ia = 0 if side == 0 else len(a['xs']) - 1
            ib = 0 if side == 0 else len(b['xs']) - 1
            quad = (a['top'][ia], b['top'][ib], b['bot'][ib], a['bot'][ia])
            try:
                bm.faces.new(quad if side == 0 else quad[::-1])
            except ValueError:
                pass
    for rr in (rows[0], rows[-1]):
        for k in range(len(rr['xs']) - 1):
            quad = (rr['top'][k], rr['top'][k + 1], rr['bot'][k + 1], rr['bot'][k])
            try:
                bm.faces.new(quad if rr is rows[0] else quad[::-1])
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.002)
    bmesh.ops.dissolve_degenerate(bm, dist=0.002, edges=bm.edges)
    K._outward(bm)
    K.bm_set_mat(bm, S0)
    parts = [bm]
    # diagonal ribs on the intrados groin curves (sampled from the rows)
    half = []
    for r in rows:
        if SHELL_T - 1e-6 <= r['y'] <= Sy / 2 + 1e-6:
            half.append((r['xb1'], r['y'], max(zi(fcx, r['xb1']), zi(fcy, r['y']))))
    path1 = [Vector(p) for p in half]
    rot = [Vector((Sx - x, Sy - y, z)) for (x, y, z) in half[::-1]]
    diag1 = path1 + rot[1:]                                   # SW corner -> NE corner
    diag2 = [Vector((Sx - p.x, p.y, p.z)) for p in diag1]    # SE corner -> NW corner
    prof = [(-RIB_W / 2, -RIB_D), (RIB_W / 2, -RIB_D), (RIB_W / 2, 3.0), (-RIB_W / 2, 3.0)]
    for dg in (diag1, diag2):
        rb = sweep(dg, prof, S1, horizontal_side=True)
        for v in rb.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0
        parts.append(rb)
    # wall ribs on the two outer sides, against the wall faces (the walls are 30 in from the piece edge)
    rib_y = ring_poly(fcy, SHELL_T - 3.0, SHELL_T + RIB_D)
    rib_x = ring_poly(fcx, SHELL_T - 3.0, SHELL_T + RIB_D)
    for side in outer:
        if side == 'x0':
            rb = K.prism(rib_y, 'x', 30.0, 30.0 + RIB_W, S1)
        elif side == 'x1':
            rb = K.prism(rib_y, 'x', Sx - 30.0 - RIB_W, Sx - 30.0, S1)
        elif side == 'y0':
            rb = K.prism(rib_x, 'y', 30.0, 30.0 + RIB_W, S1)
        else:
            rb = K.prism(rib_x, 'y', Sy - 30.0 - RIB_W, Sy - 30.0, S1)
        K.bevel_all(rb, 1.2, 25.0)
        parts.append(rb)
    out = K.combine(*parts)
    free(*parts)
    note = ("x span %g, y span %g; intrados = max(zA(x), zB(y)); diagonal ribs on the groin curves; wall ribs on %s; "
            "four-centred sections: x r1 %.1f R2 %.1f, y r1 %.1f R2 %.1f") % (Sx, Sy, "+".join(outer), fcx.r1, fcx.R2, fcy.r1, fcy.R2)
    return CP(P + short, out, None, note=note)


# ==============================================================================================
# C14 lean-to roof panels, C17 stair-house roof (slate courses on sarking, battens, rafters 12 x 15 at 60 c/c)
# Panel frame: local x along the eaves, local y up the slope (in the panel plane), local z the panel normal.
# Layers (z): rafters -15..0, sarking boards 0..2.8, battens 2.8..5.8, slates 2.8..8.8 (thick lower edge 6, tapering to 2 at the head).
# ==============================================================================================
COURSE = 21.0
SLATE_TOP = 8.8
ROOF_SLOTS = ["MAT_Slate", "MAT_Wood"]


def hole_polygon_c14(seed):
    """Ragged hole inside x 150..850, y 0..800, containing x 170..830 x y 30..780."""
    rng = random.Random(seed)
    poly = []
    ys = [-5.0, 70.0, 150.0, 220.0, 300.0, 380.0, 450.0, 530.0, 610.0, 690.0, 760.0]
    # left side going up
    for i, y in enumerate(ys):
        xl = rng.uniform(150.0, 170.0)
        y1 = ys[i + 1] if i + 1 < len(ys) else 780.0
        poly += [(xl, y), (xl, y1)]
    # top going right
    xs = [150.0, 230.0, 320.0, 410.0, 500.0, 590.0, 680.0, 770.0, 850.0]
    ytop = [rng.uniform(780.0, 800.0) for _ in range(len(xs) - 1)]
    poly = poly[:-1]
    for i in range(len(xs) - 1):
        poly += [(max(xs[i], poly[-1][0]) if i == 0 else xs[i], ytop[i]), (xs[i + 1], ytop[i])]
    # right side going down
    yr = list(reversed(ys))
    for i, y in enumerate(yr):
        xr = rng.uniform(830.0, 850.0)
        y0 = 780.0 if i == 0 else yr[i - 1]
        poly += [(xr, y0), (xr, y)]
    return poly_dedupe(poly)


def x_free_intervals(y, L, hole, step=4.0):
    """x intervals at height y that are not inside the hole polygon."""
    if not hole:
        return [(0.0, L)]
    out, cur = [], None
    x = 0.0
    while x <= L + 1e-6:
        inside = pip((x, y), hole)
        if not inside and cur is None:
            cur = x
        if inside and cur is not None:
            out.append((cur, x - step))
            cur = None
        x += step
    if cur is not None:
        out.append((cur, L))
    return [(a, b) for (a, b) in out if b - a > 2.0]


def slate_panel(L, S, seed, hole=None, snaps=(), rafter_len=None):
    """Roof panel in its own frame (x 0..L along the eaves, y 0..S up the slope).  Slots: 0 MAT_Slate, 1 MAT_Wood."""
    rng = random.Random(seed)
    bm = bmesh.new()
    nc = int(math.ceil(S / COURSE - 1e-6))
    for k in range(nc):
        y0 = k * COURSE
        y1 = min(S, y0 + COURSE)
        ym = 0.5 * (y0 + y1)
        # sarking boards + battens (split around the hole)
        for (xa, xb) in x_free_intervals(ym, L, hole):
            bm_add = K.box(xa, xb, y0, y1, 0.0, 2.8, S1, 0.0)
            K.bm_append(bm, bm_add)
            bm_add.free()
            bt = K.box(xa, xb, y0 + 8.0, y0 + 12.0, 2.5, 5.8, S1, 0.0)
            K.bm_append(bm, bt)
            bt.free()
        # slates
        x = -rng.uniform(0.0, 30.0)
        while x < L:
            w = rng.uniform(26.0, 34.0)
            xa, xb = max(0.0, x), min(L, x + w - 1.0)
            x += w
            if xb - xa < 4.0:
                continue
            if hole and pip((0.5 * (xa + xb), ym), hole):
                continue
            if rng.random() < 0.015:                    # a missing slate
                continue
            j = rng.uniform(-0.5, 0.5)
            lo = 2.8
            prof = [(y0, lo), (y0, SLATE_TOP + j), (y1, 4.8 + 0.4 * j), (y1, lo)]
            sl = K.prism(prof, 'x', xa, xb, S0)
            K.bm_append(bm, sl)
            sl.free()
    # rafters 12 x 15 at 60 c/c below the plane
    rl = S if rafter_len is None else rafter_len
    nraf = int((L - 60.0) // 60.0) + 1
    rafter_x = [30.0 + 60.0 * i for i in range(nraf + 1) if 30.0 + 60.0 * i <= L - 20.0]
    snap_x = {}
    for sx in snaps:
        xr = min(rafter_x, key=lambda v: abs(v - sx[0]))
        snap_x[xr] = sx
    for xr in rafter_x:
        y_cut = 0.0
        if hole:
            yy = 0.0
            while yy <= S:
                if pip((xr, yy), hole):
                    y_cut = yy
                yy += 2.0
            if y_cut > 0.0:
                y_cut += 2.0
        if xr in snap_x:
            _, back, droop = snap_x[xr]
            y_s = max(10.0, y_cut - back)
            path = [Vector((xr, y_s, -7.5 - droop)), Vector((xr, 0.5 * (y_s + y_cut), -7.5 - 0.35 * droop)), Vector((xr, y_cut, -7.5)), Vector((xr, rl, -7.5))]
            rb = sweep(path, [(-7.5, -6.0), (7.5, -6.0), (7.5, 6.0), (-7.5, 6.0)], S1, up=(1.0, 0.0, 0.0))
            K.bm_append(bm, rb)
            rb.free()
        elif y_cut < rl - 10.0:
            rb = K.box(xr - 6.0, xr + 6.0, y_cut, rl, -15.0, 0.0, S1, 0.0)
            K.bm_append(bm, rb)
            rb.free()
    return bm


def build_leanto(short, seed, hole):
    L, S = 1000.0, 1050.0
    hp = hole_polygon_c14(seed) if hole else None
    bm = slate_panel(L, S, seed, hp, snaps=((330.0, 220.0, 40.0), (570.0, 140.0, 80.0), (750.0, 260.0, 0.0)) if hole else ())
    note = "pivot at the eaves-line start; x 0..1000 along the eaves, y 0..1050 up the slope, z the panel normal; slates 6 on sarking + battens, rafters 12 x 15 at 60 c/c (z -15..0)"
    if hole:
        note += "; ragged hole inside x 150..850 y 0..800 (contains x 170..830, y 30..780): slates/boards/battens removed, rafters cut, 3 rafters snapped (droop 40 / 80 / 0)"
    return CP(P + short, bm, ROOF_SLOTS, note=note, smooth=25.0)


def clip_poly_rect(poly, x0, x1, y0, y1):
    """Sutherland-Hodgman: clip a convex 2D polygon to the rectangle x0..x1, y0..y1."""
    def clip(pts, inside, inter):
        out = []
        for i, p in enumerate(pts):
            q = pts[(i + 1) % len(pts)]
            pi, qi = inside(p), inside(q)
            if pi:
                out.append(p)
            if pi != qi:
                out.append(inter(p, q))
        return out
    pts = list(poly)
    pts = clip(pts, lambda p: p[0] >= x0, lambda p, q: (x0, p[1] + (q[1] - p[1]) * (x0 - p[0]) / (q[0] - p[0])))
    if pts:
        pts = clip(pts, lambda p: p[0] <= x1, lambda p, q: (x1, p[1] + (q[1] - p[1]) * (x1 - p[0]) / (q[0] - p[0])))
    if pts:
        pts = clip(pts, lambda p: p[1] >= y0, lambda p, q: (p[0] + (q[0] - p[0]) * (y0 - p[1]) / (q[1] - p[1]), y0))
    if pts:
        pts = clip(pts, lambda p: p[1] <= y1, lambda p, q: (p[0] + (q[0] - p[0]) * (y1 - p[1]) / (q[1] - p[1]), y1))
    return poly_dedupe(pts)


VALLEY_REPORT = {}      # piece name -> dict(loops=, filled=, open_edges=, non_contiguous=)


def build_leanto_valley(short, seed, side):
    """C14V (D1.14 / P10-5b): the C14 panel cut along its diagonal by a vertical plane (bisect_plane), capped (holes_fill), plus a valley rafter.
    L keeps the triangle (0,1050)-(1000,1050)-(1000,0), eaves vertex (1000,0); R keeps (0,0)-(0,1050)-(1000,1050), eaves vertex (0,0)."""
    L, S = 1000.0, 1050.0
    bm = slate_panel(L, S, seed)
    if side == 'L':
        a, b = Vector((L, 0.0, 0.0)), Vector((0.0, S, 0.0))          # hypotenuse ends (eaves vertex, outer-corner vertex)
        no = Vector((S, L, 0.0)).normalized()                         # points into the kept triangle
    else:
        a, b = Vector((0.0, 0.0, 0.0)), Vector((L, S, 0.0))
        no = Vector((-S, L, 0.0)).normalized()
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-4, plane_co=a, plane_no=no, clear_inner=True, clear_outer=False)
    # drop loose leftovers, then cap the cut loops
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bedges = [e for e in bm.edges if e.is_boundary]
    # count the boundary loops (connected components of boundary edges)
    parent = {}

    def find(v):
        while parent.setdefault(v, v) != v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v
    for e in bedges:
        parent[find(e.verts[0])] = find(e.verts[1])
    loops = len({find(v) for e in bedges for v in e.verts})
    before_faces = set(bm.faces)
    res = bmesh.ops.holes_fill(bm, edges=bedges, sides=0)
    new_faces = [f for f in bm.faces if f not in before_faces]
    for f in new_faces:               # the cap takes the material of the shell it closes (slate / wood)
        for e in f.edges:
            nb = [g for g in e.link_faces if g is not f and g in before_faces]
            if nb:
                f.material_index = nb[0].material_index
                break
    bm.normal_update()
    open_edges = sum(1 for e in bm.edges if e.is_boundary)
    non_contig = sum(1 for e in bm.edges if len(e.link_faces) == 2 and not e.is_contiguous)
    VALLEY_REPORT[P + short] = dict(loops=loops, filled=len(new_faces), open_edges=open_edges, non_contiguous=non_contig)
    print("VALLEY", P + short, json.dumps(VALLEY_REPORT[P + short]))
    # valley rafter 12 x 15 (z -15..0), outer face on the cut line, body inside the kept triangle, clipped to the piece rectangle
    t = (b - a).normalized()
    ext = 40.0
    p0, p1 = a - t * ext, b + t * ext
    q0, q1 = p0 + no * 12.0, p1 + no * 12.0
    poly = clip_poly_rect([(p0.x, p0.y), (p1.x, p1.y), (q1.x, q1.y), (q0.x, q0.y)], 0.0, L, 0.0, S)
    vr = K.prism(poly, 'z', -15.0, 0.0, S1)
    K.bm_append(bm, vr)
    vr.free()
    note = ("C14V valley piece %s: the C14 panel (x 0..1000 along the eaves, y 0..1050 up the slope, z the panel normal) cut by the vertical plane through the hypotenuse "
            "(%s), keeping the triangle with eaves vertex (%g, 0); bisect_plane + holes_fill (%d loops, %d caps, %d open edges left); "
            "valley rafter 12 x 15 (z -15..0) along the hypotenuse, outer face on the cut line, clipped to x 0..1000 y 0..1050; slates 6 on sarking + battens, rafters 12 x 15 at 60 c/c"
            % (side, "1050x + 1000y = 1 050 000" if side == 'L' else "1000y = 1050x", L if side == 'L' else 0.0, loops, len(new_faces), open_edges))
    return CP(P + short, bm, ROOF_SLOTS, note=note, smooth=25.0)


def xform_basis(bm, o, ex, ey, ez):
    """Map panel coords (x, y, z) -> o + x ex + y ey + z ez; reverse the faces if the basis is a reflection."""
    o, ex, ey, ez = Vector(o), Vector(ex), Vector(ey), Vector(ez)
    for v in bm.verts:
        c = v.co.copy()
        v.co = o + ex * c.x + ey * c.y + ez * c.z
    if ex.cross(ey).dot(ez) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return bm


def build_stair_roof(short, seed):
    W, Ln = 420.0, 640.0
    rise = 196.0
    run = 210.0
    th = math.atan2(rise, run)
    S = math.hypot(run, rise)
    c, s = math.cos(th), math.sin(th)
    parts = []
    el = Vector((-s, 0.0, c))
    er = Vector((s, 0.0, c))
    for i, side in enumerate((0, 1)):
        pn = slate_panel(Ln, S, seed + i, None, rafter_len=S - 12.0)
        if side == 0:        # left plane: eaves at x 0, rising towards +x; the slate top (panel z = 8.8) lies on the plane
            xform_basis(pn, -SLATE_TOP * el, (0, 1, 0), (c, 0, s), el)
        else:
            xform_basis(pn, Vector((W, 0.0, 0.0)) - SLATE_TOP * er, (0, 1, 0), (-c, 0, s), er)
        parts.append(pn)
    rc = K.prism([(192.0, 179.2), (210.0, 200.0), (228.0, 179.2), (224.0, 176.0), (210.0, 195.0), (196.0, 176.0)], 'y', 0.0, Ln, S0)
    parts.append(rc)
    for yy in (40.0, 220.0, 420.0, 600.0):
        parts.append(K.box(100.0, 320.0, yy - 6.0, yy + 6.0, 52.0, 68.0, S1, 0.0))
    out = K.combine(*parts)
    free(*parts)
    return CP(P + short, out, ROOF_SLOTS, note="pitched slate roof: eaves x 0 and 420 (slate top plane at z 0), slate planes rise 196 to the ridge at x 210, ridge cap top z 200; ridge along local y 0..640; rafters + 4 tie beams visible from below", smooth=25.0)


# ==============================================================================================
# C15 cell door frame, C16 stair-house gable
# ==============================================================================================
def build_cell_frame(short, seed):
    """Pivot bottom centre of the wall face: x -75..75, y -8..+2 (frame y -8..0, back panel y -2..+2), z 0..270."""
    hw_in, z_sh, z_ap = 55.0, 220.0, 250.0
    slope = (z_ap - z_sh) / hw_in

    def zin(x):
        return z_ap - slope * abs(x)

    parts = []
    zb = [0.0, 62.0, 118.0, 176.0]
    for side in (-1, 1):
        for k in range(len(zb) - 1):
            xa, xb = (hw_in, hw_in + 20.0) if side > 0 else (-hw_in - 20.0, -hw_in)
            parts.append(K.box(xa, xb, -8.0, 0.0, zb[k] + (0.0 if k == 0 else 0.3), zb[k + 1] - 0.3, S1, 1.0))
        top = [(side * hw_in, zb[-1]), (side * (hw_in + 20.0), zb[-1]), (side * (hw_in + 20.0), zin(hw_in + 20.0) + 20.0), (side * hw_in, zin(hw_in) + 20.0)]
        if side < 0:
            top = top[::-1]
        tb = K.prism(poly_dedupe(top), 'y', -8.0, 0.0, S1)
        K.bevel_all(tb, 1.0, 25.0)
        parts.append(tb)
        xs = [0.0, 14.0, 28.0, 42.0, hw_in]
        for k in range(4):
            xa, xb = xs[k], xs[k + 1]
            quad = [(side * xa, zin(xa)), (side * xb, zin(xb)), (side * xb, zin(xb) + 20.0), (side * xa, zin(xa) + 20.0)]
            if side < 0:
                quad = quad[::-1]
            pb = K.prism(poly_dedupe(quad), 'y', -8.0, 0.0, S1)
            if k > 0:
                K.bevel_all(pb, 1.0, 25.0)
            parts.append(pb)
    opening = [(-hw_in, 0.0), (-hw_in, z_sh), (0.0, z_ap), (hw_in, z_sh), (hw_in, 0.0)]
    parts.append(K.prism(opening, 'y', -2.0, 2.0, S2))
    out = K.combine(*parts)
    free(*parts)
    return CP(P + short, out, None, note="pivot bottom centre of the wall face (x centre, y 0 = wall face, z 0 = floor); frame projects to y -8, back panel y -2..+2 (D1 says +2: see README deviation), opening 110 x 250 straight-sided pointed head, shoulders z 220, apex 250, surround 150 x 270")


def build_stair_gable(short, seed):
    L, T, H = 380.0, 40.0, 650.0
    z_end, z_mid = 450.0, 650.0
    half = L / 2.0
    cop_t = 13.0                                         # coping thickness along the rake (measured vertically)
    body = K.box(0, L, 0, T, 0, H, S0)
    courses = K.make_courses(H, seed, False)
    relief = BK.relief_both(L, T, 0.0, H, courses, seed, z_start=0.0, wmin=70, wmax=150)

    def rake(x):
        return z_end + (z_mid - z_end) * (1.0 - abs(x - half) / half)

    allcut = bmesh.new()
    K.bm_append(allcut, relief)
    for side in (0, 1):
        edge = -1.0 if side == 0 else L + 1.0
        tri = [(edge, z_end - cop_t), (half, z_mid - cop_t), (half, H + 50.0), (edge, H + 50.0)]
        c = K.prism(poly_dedupe(tri), 'y', -2.0, T + 2.0, S2)
        K.bm_append(allcut, c)
        c.free()
    shell = K.boolean_diff(body, allcut)
    parts = [shell]
    for side in (0, 1):
        xa, xb = (0.0, half) if side == 0 else (L, half)
        quad = [(xa, rake(xa) - cop_t), (xb, rake(xb) - cop_t), (xb, rake(xb)), (xa, rake(xa))]
        cp = K.prism(poly_dedupe(quad), 'y', 0.0, T, S1)
        parts.append(cp)
    out = K.combine(*parts)
    free(body, relief, allcut, *parts)
    return CP(P + short, out, None, note="380 x 40 x 650 gable: ashlar to a rake from z 450 at the ends to 650 at the centre, 13 cm trim coping along the rake (flush, chamfered); inner face y 0")
# ==============================================================================================
# M1..M4 Mechanism 3 props (D1.4).  Material indices follow each piece's own slot list.
# ==============================================================================================
BELL_OUTER = [(1.8, 0.0), (3.6, -1.0), (5.0, -3.0), (6.2, -5.0), (7.0, -8.0), (7.6, -11.0), (8.0, -14.0), (8.6, -18.0), (9.6, -21.5),
              (10.7, -24.0), (11.0, -25.0), (11.7, -27.0), (12.0, -28.0)]
BELL_INNER = [(10.4, -28.0), (10.0, -26.0), (9.0, -22.0), (7.2, -17.0), (6.6, -14.0), (5.8, -10.0), (4.4, -7.0), (3.0, -4.5), (1.8, -3.2)]


def bell_r(z):
    for (r0, z0), (r1, z1) in zip(BELL_OUTER[:-1], BELL_OUTER[1:]):
        if z1 <= z <= z0:
            t = (z0 - z) / (z0 - z1)
            return r0 + (r1 - r0) * t
    return BELL_OUTER[-1][0]


def build_small_bell(short, seed):
    """Pivot at the crown top (z 0); the bell hangs along -z.  Slots MAT_Bronze 0, MAT_Iron 1, MAT_Band 2."""
    segs = 24
    shell = K.lathe_z(BELL_OUTER + BELL_INNER, segs=segs, mat=0, cap_bottom=False, cap_top=False, closed=True)
    parts = [shell]
    zb0, zb1 = -5.0, -8.0
    band = K.lathe_z([(bell_r(zb0) + 0.3, zb0), (bell_r(zb1) + 0.3, zb1), (bell_r(zb1) - 0.4, zb1), (bell_r(zb0) - 0.4, zb0)], segs=segs, mat=2,
                     cap_bottom=False, cap_top=False, closed=True)
    parts.append(band)
    parts.append(torus_xz(1.5, 0.5, (0.0, 0.0, 2.0), 1, 16, 6))                       # iron hanging loop, z 0..4
    parts.append(uvsphere(2.0, (0.0, 0.0, -24.0), 1, 12, 8))                         # clapper ball O4
    rod = K.cylinder(0.35, 19.0, 6, 1)
    translate(rod, dz=-23.0)
    parts.append(rod)
    out = K.combine(*parts)
    free(*parts)
    pts = []
    for r, z in BELL_OUTER[1:]:
        for i in range(12):
            a = 2 * math.pi * i / 12
            pts.append(Vector((r * math.cos(a), r * math.sin(a), z)))
    pts += [Vector((1.8 * math.cos(2 * math.pi * i / 12), 1.8 * math.sin(2 * math.pi * i / 12), 0.0)) for i in range(12)]
    hull = K.hull_from_points(pts, 0, merge_coplanar=True)
    return CP(P_PROP + short, out, ["MAT_Bronze", "MAT_Iron", "MAT_Band"], ucx=[hull],
              note="pivot at the crown top z 0, hangs along -z: lip O24 at z -28, bow O22 at -25, waist O16 at -14, crown O10 at -3; loop z 0..+4; clapper O4 at z -24; band ring z -8..-5 (MAT_Band); 1 UCX convex hull of the bell body")


def build_bracket(short, seed):
    """Pivot at the back face of the wall plate at the arm axis height; +x points out of the wall.  Slots MAT_Iron 0, MAT_Wood 1."""
    parts = [K.box(0.0, 4.0, -10.0, 10.0, -25.0, 15.0, 0, 0.0)]
    K.bevel_all(parts[0], 0.5, 20.0)
    for (y, z) in ((-6.5, -20.0), (6.5, -20.0), (-6.5, 9.0), (6.5, 9.0)):          # 4 rivets
        rv = uvsphere(1.1, (4.0, y, z), 0, 8, 6)
        parts.append(rv)
    arm = [Vector(p) for p in ((3.0, 0, 0), (12.0, 0, 0), (16.0, 0, 3.5), (23.0, 0, 3.5), (26.5, 0, 0.6), (30.0, 0, 0))]
    parts.append(sweep(arm, circle_prof(1.1, 6), 0, up=(0.0, 1.0, 0.0)))
    # scroll under the arm
    sc = []
    n = 26
    for i in range(n + 1):
        th = 1.85 * 2 * math.pi * i / n
        r = 6.0 * (1.0 - 0.80 * i / n)
        sc.append(Vector((14.0 - r * math.sin(th) * 0.0 + (-r * math.sin(th)), 0.0, -6.0 + r * math.cos(th))))
    sc[0] = Vector((14.0, 0.0, 0.0))
    parts.append(sweep(sc, circle_prof(0.7, 6), 0, up=(0.0, 1.0, 0.0)))
    # hook at x 25
    hook = [Vector(p) for p in ((25.0, 0.0, 1.0), (25.0, -2.2, -1.0), (25.0, -2.2, -4.4), (25.0, -1.6, -5.0), (25.0, 1.8, -5.0))]
    parts.append(sweep(hook, circle_prof(0.5, 6), 0, up=(1.0, 0.0, 0.0)))
    # oak hood board above, held by two pins
    hood = K.box(0.0, 34.0, -11.0, 11.0, 18.0, 22.0, 1, 0.5)
    parts.append(hood)
    for y in (-8.0, 8.0):
        pin = K.cylinder(0.8, 4.0, 6, 0)
        translate(pin, dx=2.0, dy=y, dz=14.5)
        parts.append(pin)
    out = K.combine(*parts)
    free(*parts)
    return CP(P_PROP + short, out, ["MAT_Iron", "MAT_Wood"],
              note="pivot at the back face of the plate (x 0), arm axis z 0, +x out of the wall; plate 4 x 20 x 40 (z -25..15), 4 rivets, cranked arm to x 30 with a scroll, hook at x 25 (tip z -5, bell loop hangs on it), oak hood x 0..34 z 18..22")


def build_plaque(short, W, H, D, border, step, seed, field_wear=False):
    """Stone plaque / tablet: pivot back centre, front faces +x.  Slot MAT_Trim (index 0)."""
    parts = [K.box(0.0, D - step, -W / 2, W / 2, -H / 2, H / 2, 0, 0.0)]
    K.bevel_all(parts[0], 0.5, 20.0)
    parts.append(K.box(D - step - 0.2, D, -W / 2, W / 2, H / 2 - border, H / 2, 0, 0.0))
    parts.append(K.box(D - step - 0.2, D, -W / 2, W / 2, -H / 2, -H / 2 + border, 0, 0.0))
    parts.append(K.box(D - step - 0.2, D, -W / 2, -W / 2 + border, -H / 2 + border - 0.01, H / 2 - border + 0.01, 0, 0.0))
    parts.append(K.box(D - step - 0.2, D, W / 2 - border, W / 2, -H / 2 + border - 0.01, H / 2 - border + 0.01, 0, 0.0))
    for pbox in parts[1:]:
        K.bevel_all(pbox, 0.4, 25.0)
    out = K.combine(*parts)
    free(*parts)
    return CP(P_PROP + short, out, ["MAT_Trim"],
              note="pivot back centre, front faces +x: %g x %g x %g, %g cm moulded border (x %g..%g), field recessed %g" % (D, W, H, border, D - step, D, step))


# ==============================================================================================
# P10-8d (D1.27 F1): lantern brackets, memorial tablet with carved text, named grave slabs
# ==============================================================================================
ROBOTO_BOLD = r"C:\Program Files\Epic Games\UE_5.8\Engine\Content\Slate\Fonts\Roboto-Bold.ttf"     # Apache 2.0, engine install; loaded from here, not copied
CAP_PER_SIZE = 0.5339          # Roboto Bold cap height of a Blender text object per unit of `size` (measured on "H", Blender 5.2)
# Handedness.  The FBX leaves Blender's Y mirrored once (kit_lib.export_piece_fbx) and Unreal's importer negates Y again, so the numbers in Unreal equal the
# numbers here but Unreal is left-handed: the in-game picture is the MIRROR of the Blender-native picture (render_cloister.py mirrors its camera for the same
# reason).  Text that reads correctly in game therefore has to be built y-mirrored.  Set to False for text that reads correctly in the native Blender view.
UE_VIEW = True


def cyl_x(r, x0, x1, y, z, segs=8, mat=0):
    """Cylinder along +x from x0 to x1 (axis through y, z)."""
    c = K.cylinder(r, x1 - x0, segs, mat)
    for v in c.verts:
        v.co = Vector((v.co.z + x0, v.co.x + y, v.co.y + z))
    K._outward(c)
    return c


def build_lantern_bracket(short, R, seed):
    """Wall bracket for a hanging lantern (D1.27 F1.1).  Pivot (0,0,0) on the wall face at the lantern's hook height, +x out of the wall; the hanger ring's
    lowest point is z 0.0 (the top of the lantern).  Slot MAT_Iron only, no UCX."""
    plate = K.box(0.0, 1.5, -4.0, 4.0, -14.0, 18.0, 0, 0.0)
    K.bevel_all(plate, 0.3, 20.0)
    parts = [plate, cyl_x(0.9, 1.5, 2.1, 0.0, -10.0), cyl_x(0.9, 1.5, 2.1, 0.0, 14.0)]            # bolt heads
    parts.append(K.box(1.5, R + 2.0, -1.0, 1.0, 13.0, 15.0, 0, 0.0))                              # arm 2 x 2
    parts.append(uvsphere(1.4, (R + 2.5, 0.0, 14.0), 0, 12, 8))                                   # finial
    a, b = Vector((1.5, 0.0, -10.0)), Vector((0.6 * R, 0.0, 13.25))
    parts.append(sweep([a, b], rect_prof(1.5, 1.5), 0, up=(0.0, 1.0, 0.0)))                        # brace 1.5 x 1.5
    pt = a + (b - a) / 3.0                                                                         # C-scroll at the brace's lower third
    cen = pt - Vector((0.0, 0.0, 3.0))
    arc = [cen + Vector((3.0 * math.cos(math.radians(90.0 + 90.0 * i / 8.0)), 0.0, 3.0 * math.sin(math.radians(90.0 + 90.0 * i / 8.0)))) for i in range(9)]
    parts.append(sweep(arc, circle_prof(0.5, 6), 0, up=(0.0, 1.0, 0.0)))
    link = K.cylinder(0.5, 7.0, 6, 0)                                                              # hanger link z 6..13
    translate(link, dx=R, dy=0.0, dz=6.0)
    parts.append(link)
    parts.append(torus_xz(2.6, 0.5, (R, 0.0, 3.1), 0, 16, 6))                                      # ring, lowest point z 0.0
    out = K.combine(*parts)
    free(*parts)
    return CP(P_PROP + short, out, ["MAT_Iron"],
              note="pivot on the wall face (x 0) at the lantern hook height, +x out of the wall; plate x 0..1.5 y +-4 z -14..18 with 2 bolt heads, arm 2x2 to x %g, finial r1.4, "
                   "brace 1.5x1.5 to (%g, 13.25), C-scroll, link + ring (lowest point z 0.0 = lantern top); reach R = %g" % (R + 2, 0.6 * R, R))


def text_cutter(items, depth, ext, bev, res, spacing=1.15, mat=1, resu=3, trim=0.0):
    """Cutter solid for lines of Roboto Bold text, in text-plane coordinates: u = reading direction, v = up, w = out of the face (the face is w 0).
    items = [(text, cap_height, centre_u, centre_v)].  The solid spans w -depth .. -depth + 2*(ext+bev).  Text curves get offset -bev so the bevel
    does not fatten the strokes (stroke width = the glyph's outline at mid height)."""
    font = bpy.data.fonts.load(ROBOTO_BOLD, check_existing=True)
    out = bmesh.new()
    for (txt, cap, cu_, cv_) in items:
        cu = bpy.data.curves.new("_txt", 'FONT')
        cu.font = font
        cu.body = txt
        cu.size = cap / CAP_PER_SIZE
        cu.align_x = 'LEFT'
        cu.extrude, cu.bevel_depth, cu.bevel_resolution, cu.offset = ext, bev, res, -bev - trim * cap
        cu.space_character = spacing
        cu.resolution_u = resu
        ob = bpy.data.objects.new("_txt", cu)
        bpy.context.scene.collection.objects.link(ob)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
        b = bmesh.new()
        b.from_mesh(me)
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(me)
        bpy.data.curves.remove(cu)
        mn, mx = K.bm_bounds(b)
        du = cu_ - 0.5 * (mn[0] + mx[0])
        dv = cv_ - cap / 2.0                         # baseline is v 0 in the curve, so the cap band is centred on cv_
        dw = -depth + (ext + bev)
        bmesh.ops.translate(b, vec=(du, dv, dw), verts=b.verts)
        K.bm_set_mat(b, mat)
        K.bm_append(out, b)
        b.free()
    return out


def orient_cutter(bm, native_map, face_pos):
    """Map text-plane (u, v, w) -> piece space with `native_map(u, v, w)` (reads correctly in the native Blender view) and, when UE_VIEW, mirror y (the in-game
    picture is the mirror of the native one).  face_pos is added afterwards.  The face winding is reversed when the map flips handedness; bmesh's
    recalc_face_normals is NOT used here: on text solids with counters (A, B, O, ...) it flips some inner walls depending on where the glyph sits, which makes the
    exact boolean fill the counters (found in P10-8d)."""
    def mp(u, v, w):
        x, y, z = native_map(u, v, w)
        return Vector((x, -y if UE_VIEW else y, z))
    e = [mp(1, 0, 0) - mp(0, 0, 0), mp(0, 1, 0) - mp(0, 0, 0), mp(0, 0, 1) - mp(0, 0, 0)]
    flip = e[0].cross(e[1]).dot(e[2]) < 0
    for vv in bm.verts:
        vv.co = mp(vv.co.x, vv.co.y, vv.co.z) + Vector(face_pos)
    if flip:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return bm


MEMORIAL_COLS = (-42.75, -14.25, 14.25, 42.75)
MEMORIAL_NAMES = (("ANSELM", 1341, "III"), ("TOMAS", 1344, "I"), ("EDWIN", 1348, "IV"), ("OSRIC", 1351, "II"))


def build_memorial_tablet(short, seed):
    """InscriptionTablet_A geometry (build_plaque 120 x 30 x 4, seed 1308) with the memorial roll carved into the field face (x 2.8) -- D1.27 F1.2.
    Slots MAT_Trim 0, MAT_Carve 1 (the groove faces).  Local units: the tablet is placed at root scale 2.5 (local = world / 2.5)."""
    base = build_plaque(short, 120.0, 30.0, 4.0, 3.0, 1.2, seed)
    items = [("HERE REST THE BROTHERS OF THE BELL", 2.40, 0.0, 9.0), ("RING FOR THEM AS THEY FELL", 2.00, 0.0, -9.3)]
    for col, (nm, yr, num) in zip(MEMORIAL_COLS, MEMORIAL_NAMES):
        items.append(("BR. " + nm, 2.20, col, 4.6))
        items.append(("OB. %d" % yr, 1.60, col, 1.3))
        items.append((num, 3.60, col, -3.4))
    cut = text_cutter(items, 0.48, 0.24, 0.10, 2, 1.15, mat=1)
    # native: viewer at +x looking -x sees +y on the right (u -> +y), up is +z, w -> +x
    orient_cutter(cut, lambda u, v, w: (w, u, v), (2.8, 0.0, 0.0))
    out = K.boolean_diff(base.bm, cut)
    free(base.bm, cut)
    return CP(P_PROP + short, out, ["MAT_Trim", "MAT_Carve"],
              note="build_plaque(120 x 30 x 4, border 3, step 1.2) + memorial roll carved 0.48 into the field face (x 2.8), Roboto Bold, spacing 1.15; rows 1/5 centred, rows 2-4 in "
                   "four columns (ANSELM TOMAS EDWIN OSRIC, left to right as seen in game; ANSELM at +y); groove faces = MAT_Carve (slot 1); placed at root scale 2.5")


GRAVE_NAMES = (("Anselm", 1341), ("Tomas", 1344), ("Edwin", 1348), ("Osric", 1351))


def build_named_grave_slab(short, name, year, seed):
    """build_grave_slab(..., 1220) plus two carved lines on the top face (z 8): 'BR. NAME' cap 7 at x -20 and 'OB. YEAR' cap 5 at x -45 (D1.27 F1.3).
    Text up is +x (toward the cross), reading direction is the viewer's right when standing at the foot (-x end).  Slots: kit slots + MAT_Carve (3)."""
    base = build_grave_slab(short, seed)
    cut = bmesh.new()
    for (txt, cap, cx) in (("BR. " + name.upper(), 7.0, -20.0), ("OB. %d" % year, 5.0, -45.0)):
        c = text_cutter([(txt, cap, 0.0, 0.0)], 0.8, 0.4, 0.12, 2, 1.15, mat=3)
        # native: viewer at the foot (-x) looking +x from above: up = +x, right = -y (u -> -y), w -> +z
        orient_cutter(c, lambda u, v, w: (v, -u, w), (cx, 0.0, 8.0))
        K.bm_append(cut, c)
        c.free()
    out = K.boolean_diff(base.bm, cut)
    free(base.bm, cut)
    return CP(P + short, out, KIT_SLOTS + ["MAT_Carve"],
              note="build_grave_slab(..., 1220) + 'BR. %s' (cap 7, centre x -20) and 'OB. %d' (cap 5, centre x -45) carved 0.8 into the top face, Roboto Bold; text up = +x, "
                   "reads from the foot (-x) end; groove faces = MAT_Carve (slot 3)" % (name.upper(), year))


# stair-house, cell frame etc. are above; props use the SM_LB_Prop_ prefix
# ==============================================================================================
# registry
# ==============================================================================================
def table():
    """(short name, seed, builder).  Seeds are the D1.3 / D1.4 seeds."""
    T = []
    A = T.append
    # C1 / C2 / C3 walls
    A(("Wall40_400x1300_A", 1201, lambda: build_wall40("Wall40_400x1300_A", 400, 1300, 1201, False, True)))
    A(("Wall40_400x1300_B", 1202, lambda: build_wall40("Wall40_400x1300_B", 400, 1300, 1202, True, True)))
    A(("Wall40_100x1300", 1203, lambda: build_wall40("Wall40_100x1300", 100, 1300, 1203, False, True)))
    A(("Wall40_400x800_A", 1204, lambda: build_wall40("Wall40_400x800_A", 400, 800, 1204)))
    A(("Wall40_400x800_B", 1205, lambda: build_wall40("Wall40_400x800_B", 400, 800, 1205, True)))
    A(("Wall40_100x800", 1206, lambda: build_wall40("Wall40_100x800", 100, 800, 1206)))
    A(("Wall40_400x450", 1207, lambda: build_wall40("Wall40_400x450", 400, 450, 1207)))
    A(("Wall40_100x450", 1208, lambda: build_wall40("Wall40_100x450", 100, 450, 1208)))
    # C4 / C5 archways
    A(("Archway_500x40x1300", 1209, lambda: build_archway("Archway_500x40x1300", 500.0, 300.0, 420.0, 1209)))
    A(("Archway_300x40x1300", 1210, lambda: build_archway("Archway_300x40x1300", 300.0, 330.0, 450.0, 1210)))
    # C6 / C7 piers
    A(("Pier_80x80x640", 1211, lambda: build_pier("Pier_80x80x640", 40.0, 40.0, 1211)))
    A(("PierCorner_130x80x640", 1212, lambda: build_pier("PierCorner_130x80x640", 65.0, 40.0, 1212)))
    # C8 arcade arches
    for sp, sd in ((120, 1213), (170, 1214), (220, 1215), (270, 1216)):
        A(("ArcadeArch_%dx80" % sp, sd, (lambda sp=sp, sd=sd: build_arcade_arch("ArcadeArch_%dx80" % sp, sp, sd))))
    # C9..C11 garth
    A(("GarthWall_1100x100", 1217, lambda: build_garth_wall("GarthWall_1100x100", 1100.0, 1217)))
    A(("GarthWall_800x100", 1218, lambda: build_garth_wall("GarthWall_800x100", 800.0, 1218)))
    A(("GarthBed_1100x800", 1219, lambda: build_garth_bed("GarthBed_1100x800", 1219)))
    A(("GraveSlab_200x80", 1220, lambda: build_grave_slab("GraveSlab_200x80", 1220)))
    A(("GraveCross_60", 1221, lambda: build_grave_cross("GraveCross_60", 1221)))
    A(("GarthCross_350", 1222, lambda: build_garth_cross("GarthCross_350", 1222)))
    # C12 barrel vaults ({span}x{length}: local y = span, local x = length)
    A(("Vault_Barrel_830x640", 1225, lambda: build_barrel("Vault_Barrel_830x640", 830.0, 640.0, 1225)))
    A(("Vault_Barrel_770x640", 1226, lambda: build_barrel("Vault_Barrel_770x640", 770.0, 640.0, 1226)))
    A(("Vault_Barrel_770x640_Broken", 1227, lambda: build_barrel("Vault_Barrel_770x640_Broken", 770.0, 640.0, 1227, True)))
    A(("Vault_Barrel_770x980", 1228, lambda: build_barrel("Vault_Barrel_770x980", 770.0, 980.0, 1228)))
    A(("Vault_Barrel_570x980", 1229, lambda: build_barrel("Vault_Barrel_570x980", 570.0, 980.0, 1229)))
    # C13 groin vaults (x span x y span)
    A(("Vault_Groin_770x830", 1232, lambda: build_groin("Vault_Groin_770x830", 770.0, 830.0, ('x0', 'y0'), 1232)))
    A(("Vault_Groin_570x830", 1233, lambda: build_groin("Vault_Groin_570x830", 570.0, 830.0, ('x1', 'y0'), 1233)))
    A(("Vault_Groin_770x770", 1234, lambda: build_groin("Vault_Groin_770x770", 770.0, 770.0, ('x0', 'y1'), 1234)))
    A(("Vault_Groin_570x770", 1235, lambda: build_groin("Vault_Groin_570x770", 570.0, 770.0, ('x1', 'y1'), 1235)))
    # C14 roof panels, C15 cell door frame, C16 / C17 stair-house
    A(("LeanTo_1000x1050", 1236, lambda: build_leanto("LeanTo_1000x1050", 1236, False)))
    A(("LeanTo_1000x1050_Hole", 1237, lambda: build_leanto("LeanTo_1000x1050_Hole", 1237, True)))
    A(("LeanTo_Valley_L_1000x1050", 1241, lambda: build_leanto_valley("LeanTo_Valley_L_1000x1050", 1241, 'L')))
    A(("LeanTo_Valley_R_1000x1050", 1242, lambda: build_leanto_valley("LeanTo_Valley_R_1000x1050", 1242, 'R')))
    A(("CellDoorFrame_150x270", 1238, lambda: build_cell_frame("CellDoorFrame_150x270", 1238)))
    A(("StairHouseGable_380x40x650", 1239, lambda: build_stair_gable("StairHouseGable_380x40x650", 1239)))
    A(("StairHouseRoof_420x640", 1240, lambda: build_stair_roof("StairHouseRoof_420x640", 1240)))
    # M1..M4 Mechanism 3
    A(("SM_LB_Prop_SmallBell_A", 1301, lambda: build_small_bell("SmallBell_A", 1301)))
    A(("SM_LB_Prop_SmallBellBracket_A", 1302, lambda: build_bracket("SmallBellBracket_A", 1302)))
    A(("SM_LB_Prop_BellPlaque_A", 1303, lambda: build_plaque("BellPlaque_A", 34.0, 34.0, 4.0, 3.0, 1.0, 1303)))
    A(("SM_LB_Prop_InscriptionTablet_A", 1304, lambda: build_plaque("InscriptionTablet_A", 120.0, 30.0, 4.0, 3.0, 1.2, 1304)))
    return T


TABLE_EXTRA = []        # appended by later sections
# P10-8d (D1.27 F1)
for _R, _sd in ((20, 1305), (40, 1306), (60, 1307)):
    TABLE_EXTRA.append(("SM_LB_Prop_LanternBracket_R%d" % _R, _sd, (lambda _R=_R, _sd=_sd: build_lantern_bracket("LanternBracket_R%d" % _R, float(_R), _sd))))
TABLE_EXTRA.append(("SM_LB_Prop_InscriptionTablet_Memorial", 1308, lambda: build_memorial_tablet("InscriptionTablet_Memorial", 1308)))
for _nm, _yr in GRAVE_NAMES:
    TABLE_EXTRA.append(("GraveSlab_200x80_" + _nm, 1220, (lambda _nm=_nm, _yr=_yr: build_named_grave_slab("GraveSlab_200x80_" + _nm, _nm, _yr, 1220))))


def full_name(short):
    return short if short.startswith("SM_") else P + short


def full_table():
    return table() + [(a, b, c) for (a, b, c) in TABLE_EXTRA]


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.join(REPO, "SourceArt", "Cloister")
    only, tag = [], None
    i = 0
    while i < len(argv):
        if argv[i] == "--out":
            out = os.path.abspath(argv[i + 1])
            i += 2
        elif argv[i] == "--tag":
            tag = argv[i + 1]
            i += 2
        elif argv[i] == "--only":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                only.append(argv[i])
                i += 1
        else:
            i += 1
    return out, only, tag


def piece_report(pc, seed, seconds):
    mn, mx = K.bm_bounds(pc.bm)
    used = sorted({f.material_index for f in pc.bm.faces})
    return dict(name=pc.name, seed=seed, min=[round(v, 2) for v in mn], max=[round(v, 2) for v in mx],
                dims=[round(mx[i] - mn[i], 2) for i in range(3)], tris=K.tri_count(pc.bm),
                slots=pc.slots if pc.slots else KIT_SLOTS, slots_used=used, ucx=len(pc.ucx), seconds=round(seconds, 1), note=pc.note)


def run():
    out_dir, only, tag = parse_args()
    K.setup_scene_units()
    K.get_materials()
    os.makedirs(out_dir, exist_ok=True)
    report, pieces = [], []
    t0 = time.time()
    for short, seed, fn in full_table():
        nm = full_name(short)
        if only and not any(o in nm for o in only):
            continue
        t = time.time()
        pc = fn()
        K.finalize(pc.bm, smooth_deg=pc.smooth, hard_flat_slot=K.SLOT_MASONRY)
        rec = piece_report(pc, seed, 0.0)
        K.export_piece_fbx(pc.name, pc.bm, pc.ucx, os.path.join(out_dir, pc.name + ".fbx"), mats_for(pc.slots))
        rec['seconds'] = round(time.time() - t, 1)
        report.append(rec)
        print("PIECE", json.dumps({k: v for k, v in rec.items() if k != 'note'}))
        pieces.append(pc)
    # review layout
    x, row_y, row_h = 0.0, 0.0, 0.0
    for pc in pieces:
        mn, mx = K.bm_bounds(pc.bm)
        w, d = mx[0] - mn[0], mx[1] - mn[1]
        if x + w > 9000.0:
            x, row_y = 0.0, row_y + row_h + 300.0
            row_h = 0.0
        K.add_to_layout(pc.name, pc.bm, pc.ucx, (x - mn[0], row_y - mn[1], 0.0), mats_for(pc.slots))
        x += w + 150.0
        row_h = max(row_h, d + 300.0)
    blend_name = "LB_Cloister.blend" if not only else "LB_Cloister_%s.blend" % (tag or "partial")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, blend_name))
    rp = os.path.join(out_dir, "cloister_report.json")
    if only and os.path.exists(rp):
        with open(rp) as fh:
            old = [r for r in json.load(fh) if r["name"] not in {x_["name"] for x_ in report}]
        report = old + report
        order = [full_name(n) for n, _s, _f in full_table()]
        report.sort(key=lambda r: order.index(r["name"]) if r["name"] in order else 999)
    with open(rp, "w") as fh:
        json.dump(report, fh, indent=1)
    print("DONE %d pieces in %.1fs -> %s" % (len(pieces), time.time() - t0, out_dir))
    sys.stdout.flush()


if __name__ == "__main__":
    run()
