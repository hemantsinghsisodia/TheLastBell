"""build_kit.py -- procedurally builds the P0 modular kit for THE LAST BELL (Blender 5.2, headless).

    blender.exe -b --factory-startup --python Tools/blender/kit/build_kit.py -- [--out SourceArt/Kit] [--only NAME ...]

Writes one FBX per piece (SourceArt/Kit/FBX/<MeshName>.fbx, UCX_ collision in the same file), the combined
review file SourceArt/Kit/LB_Kit_P0.blend and Docs/ArtTest/kit/kit_report.json (bounds / tris / slots).
Everything is deterministic (fixed seeds).  The PIECES table below mirrors Docs/MODULAR_KIT.md section 4.1
(+ the promoted blind lancet window, section 8).
"""
import json
import math
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy
import bmesh
from mathutils import Vector

import kit_lib as K
from kit_lib import SLOT_MASONRY as S0, SLOT_TRIM as S1, SLOT_RUBBLE as S2

PREFIX = "SM_LB_Kit_"
CAP_H = 25.0          # integrated wall cap course height (slot 1)
GRID = 500.0          # layout spacing helper


# ==============================================================================================
# piece record
# ==============================================================================================
class Piece:
    def __init__(self, name, bm, ucx, dims, clear=None, note=""):
        self.name, self.bm, self.ucx, self.dims, self.clear, self.note = name, bm, ucx, dims, clear, note


# ==============================================================================================
# shared sub-builders
# ==============================================================================================
def cap_profile(T, z0, z1, ctop=4.0, cbot=2.5):
    """(y, z) outline of a chamfered cap course (chamfer on the long edges only)."""
    return [(0, z0 + cbot), (cbot, z0), (T - cbot, z0), (T, z0 + cbot), (T, z1 - ctop), (T - ctop, z1), (ctop, z1), (0, z1 - ctop)]


def face_frames(L, T):
    """Front (y=0, outward -Y) and back (y=T, outward +Y) wall faces."""
    front = K.FaceFrame((0, 0, 0), (1, 0, 0), (0, -1, 0))
    back = K.FaceFrame((L, T, 0), (-1, 0, 0), (0, 1, 0))
    return front, back


def relief_both(L, T, z0, z1, courses, seed, **kw):
    f, b = face_frames(L, T)
    cut = K.relief_cutters(f, 0, L, z0, z1, courses, seed, **kw)
    cut2 = K.relief_cutters(b, 0, L, z0, z1, courses, seed + 101, **kw)
    K.bm_append(cut, cut2)
    return cut


def ashlar_body(L, T, z0, z1, seed, vary=False, **kw):
    """Masonry slab with relief on both long faces (slot 0)."""
    body = K.box(0, L, 0, T, z0, z1, S0)
    courses = K.make_courses(z1 - z0, seed, vary)
    cut = relief_both(L, T, z0, z1, courses, seed, z_start=z0, **kw)
    out = K.boolean_diff(body, cut)
    cut.free()
    body.free()
    return out, courses


def cap_course(L, T, z0, z1, seed, ctop=4.0, cbot=2.5, joints=True):
    c = K.prism(cap_profile(T, z0, z1, ctop, cbot), 'x', 0, L, S1)
    if not joints:
        return c
    f, b = face_frames(L, T)
    cut = K.relief_cutters(f, 0, L, z0, z1, [z1 - z0], seed + 7, h_grooves=False, recess_prob=0.0, chips=1,
                           wmin=90, wmax=190, z_start=z0, groove_mat=S1, chip_mat=S2)
    cut2 = K.relief_cutters(b, 0, L, z0, z1, [z1 - z0], seed + 8, h_grooves=False, recess_prob=0.0, chips=1,
                            wmin=90, wmax=190, z_start=z0, groove_mat=S1, chip_mat=S2)
    K.bm_append(cut, cut2)
    out = K.boolean_diff(c, cut)
    cut.free()
    c.free()
    return out


def stepped_profile(L, H, zmin, seed, tooth_at=None, seg=(35, 85)):
    """Irregular broken-top profile h(x): plateaus of random height and tilt joined by breaks that range from
    near-vertical to 45 degree slopes, with one untouched 'tooth' reaching H.  Returns (h, (xs, h_min per segment))."""
    rng = random.Random(seed)
    xs = [0.0]
    x = 0.0
    while x < L:
        x = min(L, x + rng.uniform(*seg))
        xs.append(x)
    n = len(xs) - 1
    hs = [rng.uniform(zmin, H * 0.9) for _ in range(n)]
    k = rng.randrange(n) if tooth_at is None else tooth_at
    hs[k] = H + 6.0                                   # untouched tooth
    if k + 1 < n:
        hs[k + 1] = max(hs[k + 1], zmin + 0.5 * (H - zmin))
    ramps = [rng.choice((5.0, 9.0, 16.0, 28.0, 42.0)) for _ in range(n + 1)]
    slopes = [rng.uniform(-30.0, 30.0) for _ in range(n)]
    floor = zmin * 0.85
    nodes, hmin = [], []
    prev_end = hs[0]
    for i in range(n):
        x0, x1 = xs[i], xs[i + 1]
        r = min(ramps[i], 0.45 * (x1 - x0)) if i > 0 else 0.0
        h0 = hs[i]
        h1 = h0 if i == k else max(floor, min(H * 0.95, h0 + slopes[i]))
        nodes.append((x0 + r, h0))
        nodes.append((x1, h1))
        hmin.append(min(h0, h1, prev_end if i > 0 else h0))
        prev_end = h1
    nodes.sort()

    def h(x):
        if x <= nodes[0][0]:
            return nodes[0][1]
        for (xa, za), (xb, zb) in zip(nodes, nodes[1:]):
            if x <= xb:
                t = 0.0 if xb - xa < 1e-6 else (x - xa) / (xb - xa)
                return za * (1 - t) + zb * t
        return nodes[-1][1]

    return h, (xs, hmin)


def fracture_cutters(L, T, H, zmin, seed, *, ends=True, end_from=0.45, na_step=8.0, tooth_at=None, seg=(35, 85), y_amp=16.0):
    """Cutters that break the top (and ends) of a wall piece.  Returns (cutter_bm, profile)."""
    rng = random.Random(seed + 500)
    h, prof = stepped_profile(L, H, zmin, seed, tooth_at, seg)
    ytop = H + 40.0

    def f(x, y):
        yn = (K.vnoise(y / 22.0 + 3.1, x / 70.0, seed) - 0.5) * y_amp
        jit = (K.vnoise(x / 6.0, y / 6.0, seed + 5) - 0.5) * 5.0
        v = h(min(max(x, 0.0), L)) + yn + jit
        return min(v, H + 12.0)

    na = max(4, int((L + 12) / na_step))
    cut = K.hf_solid(-6, L + 6, -6, T + 6, f, ytop, na, 7, ('x', 'y', 'z'), S2, rng)
    if ends:
        zs0 = end_from * H
        for side in (0, 1):
            def e(y, z, side=side):
                t = K.smoothstep(zs0, H, z + (K.vnoise(y / 15.0, z / 40.0, seed + 31 + side) - 0.5) * 120.0)
                return 0.5 + (4.0 + 26.0 * K.vnoise(y / 30.0, z / 55.0, seed + 41 + side)) * t

            if side == 0:
                fn = lambda y, z: e(y, z)
                cb = -14.0
            else:
                fn = lambda y, z: L - e(y, z)
                cb = L + 14.0
            nbz = max(4, int((H + 6 - zs0) / 14.0))
            end = K.hf_solid(-6, T + 6, zs0, H + 8, fn, cb, 6, nbz, ('y', 'z', 'x'), S2, rng)
            K.bm_append(cut, end)
            end.free()
    return cut, prof


def stepped_boxes(L, T, prof, n_boxes=3, margin=8.0, ymin=0.0, ymax=None):
    """Collision boxes following the lowest part of the broken profile in each X span."""
    xs, hs = prof
    out = []
    ymax = T if ymax is None else ymax
    for i in range(n_boxes):
        a, b = L * i / n_boxes, L * (i + 1) / n_boxes
        lo = min(hs[j] for j in range(len(hs)) if xs[j + 1] >= a and xs[j] <= b)
        out.append(K.box_hull(a, b, ymin, ymax, 0, max(20.0, min(lo, 1e9) - margin)))
    return out


# ==============================================================================================
# piece builders
# ==============================================================================================
def build_wall(name, L, H, seed, vary=False, broken=None, T=60.0, cap=CAP_H, joints=True):
    z_body = H - cap
    body, courses = ashlar_body(L, T, 0, z_body, seed, vary)
    capm = cap_course(L, T, z_body, H, seed) if cap > 0 else K.bmesh.new()
    prof = None
    if broken is not None:
        fc, prof = fracture_cutters(L, T, H, broken['zmin'], seed, ends=True, end_from=broken.get('end_from', 0.45),
                                    tooth_at=broken.get('tooth_at'), seg=broken.get('seg', (35, 85)))
        body2 = K.boolean_diff(body, fc)
        cap2 = K.boolean_diff(capm, fc) if cap > 0 else K.bmesh.new()
        fc.free()
        body.free()
        capm.free()
        body, capm = body2, cap2
    out = K.combine(body, capm)
    body.free()
    capm.free()
    if broken is None:
        ucx = [K.box_hull(0, L, 0, T, 0, H)]
    else:
        ucx = stepped_boxes(L, T, prof, broken.get('boxes', 3))
    return Piece(name, out, ucx, (L, T, H))


def build_corner(name, seed=3):
    S, H = 60.0, 800.0
    out = __import__('bmesh').new()
    rng = random.Random(seed)
    z = 0.0
    hs = []
    tot = H - CAP_H
    k = 0
    while z < tot - 1e-6:
        h = 60.0 if k % 2 == 0 else 40.0
        h = min(h, tot - z)
        hs.append(h)
        z += h
        k += 1
    z = 0.0
    for k, h in enumerate(hs):
        ins = 0.0 if k % 2 == 0 else 1.4
        s = K.box(ins, S - ins, ins, S - ins, z, z + h, S1, 2.4)
        K.bm_append(out, s)
        z += h
    capm = K.box(0, S, 0, S, tot, H, S1, 3.5)
    K.bm_append(out, capm)
    return Piece(name, out, [K.box_hull(0, S, 0, S, 0, H)], (S, S, H))


def build_buttress(name, seed=5):
    W, D, H = 100.0, 150.0, 800.0
    # stage 1 and 2 profiles in (y, z)
    p1 = [(0, 0), (D, 0), (D, 462), (100, 500), (0, 500)]
    p2 = [(0, 495), (100, 495), (100, 758), (55, H), (0, H)]
    s1 = K.prism(p1, 'x', 0, W, S0)
    s2 = K.prism(p2, 'x', 10, W - 10, S0)
    # slot 1 for sloped weathering / top faces
    for s in (s1, s2):
        for f in s.faces:
            n = f.normal
            if n.z > 0.35:
                f.material_index = S1
    cut = K.bmesh.new()
    # courses on the stage-1 front and sides, stage-2 front and sides
    c1 = K.make_courses(462, seed, False)
    frames1 = [
        (K.FaceFrame((0, D, 0), (1, 0, 0), (0, 1, 0)), 0, W, 0, 462),
        (K.FaceFrame((0, 0, 0), (0, 1, 0), (-1, 0, 0)), 0, D, 0, 462),
        (K.FaceFrame((W, D, 0), (0, -1, 0), (1, 0, 0)), 0, D, 0, 462),
    ]
    for i, (fr, a, b, z0, z1) in enumerate(frames1):
        K.bm_append(cut, K.relief_cutters(fr, a, b, z0, z1, c1, seed + i, recess_prob=0.2, chips=2, wmin=70, wmax=110, z_start=z0))
    out1 = K.boolean_diff(s1, cut)
    cut.free()
    cut = K.bmesh.new()
    c2 = K.make_courses(758 - 500, seed + 9, False)
    frames2 = [
        (K.FaceFrame((10, 100, 0), (1, 0, 0), (0, 1, 0)), 0, W - 20, 500, 758),
        (K.FaceFrame((10, 0, 0), (0, 1, 0), (-1, 0, 0)), 0, 100, 500, 758),
        (K.FaceFrame((W - 10, 100, 0), (0, -1, 0), (1, 0, 0)), 0, 100, 500, 758),
    ]
    for i, (fr, a, b, z0, z1) in enumerate(frames2):
        K.bm_append(cut, K.relief_cutters(fr, a, b, z0, z1, c2, seed + 20 + i, recess_prob=0.15, chips=1, wmin=70, wmax=110, z_start=z0))
    out2 = K.boolean_diff(s2, cut)
    cut.free()
    out = K.combine(out1, out2)
    for b in (out1, out2, s1, s2):
        b.free()
    return Piece(name, out, [K.box_hull(0, W, 0, D, 0, 500), K.box_hull(10, W - 10, 0, 100, 500, H)], (W, D, H))


def build_plinth(name, L, seed):
    T, H = 80.0, 60.0
    prof = [(0, 0), (T, 0), (T, 54), (T - 6, H), (6, H), (0, 54)]
    p = K.prism(prof, 'x', 0, L, S1)
    f, b = face_frames(L, T)
    cut = K.relief_cutters(f, 0, L, 0, 54, [54], seed, h_grooves=False, recess_prob=0.0, chips=2, wmin=95, wmax=170,
                           z_start=0.0, groove_mat=S1, chip_mat=S2)
    K.bm_append(cut, K.relief_cutters(b, 0, L, 0, 54, [54], seed + 3, h_grooves=False, recess_prob=0.0, chips=2,
                                      wmin=95, wmax=170, z_start=0.0, groove_mat=S1, chip_mat=S2))
    out = K.boolean_diff(p, cut)
    p.free()
    cut.free()
    return Piece(name, out, [K.box_hull(0, L, 0, T, 0, H)], (L, T, H))


def pier_cutters(z0, z1, seed):
    """Drum-joint grooves around the 84x84 shaft (x,y 8..92)."""
    n = max(1, int(round((z1 - z0) / 65.0)))
    courses = [(z1 - z0) / n] * n
    frames = [K.FaceFrame((8, 8, 0), (1, 0, 0), (0, -1, 0)), K.FaceFrame((92, 92, 0), (-1, 0, 0), (0, 1, 0)),
              K.FaceFrame((8, 92, 0), (0, -1, 0), (-1, 0, 0)), K.FaceFrame((92, 8, 0), (0, 1, 0), (1, 0, 0))]
    cut = K.bmesh.new()
    for i, fr in enumerate(frames):
        K.bm_append(cut, K.relief_cutters(fr, 0, 84, z0, z1, courses, seed + i, vertical=False, recess_prob=0.0, chips=1,
                                          z_start=z0, groove_mat=S1, chip_mat=S2, joint_depth=1.6, joint_w=3.2))
    return cut


def pier_base_cap(seed, with_cap=True):
    out = K.bmesh.new()
    K.bm_append(out, K.box(0, 100, 0, 100, 0, 37, S1, 2.2))
    fr = K.hull_from_points([(0, 0, 37), (100, 0, 37), (100, 100, 37), (0, 100, 37),
                             (7, 7, 47), (93, 7, 47), (93, 93, 47), (7, 93, 47)], S1)
    K.bm_append(out, fr)
    if with_cap:
        fl = K.hull_from_points([(8, 8, 440), (92, 8, 440), (92, 92, 440), (8, 92, 440),
                                 (0, 0, 468), (100, 0, 468), (100, 100, 468), (0, 100, 468)], S1)
        K.bm_append(out, fl)
        K.bm_append(out, K.box(0, 100, 0, 100, 468, 500, S1, 3.0))
    return out


def _vertical_edge(e):
    return abs(e.verts[0].co.z - e.verts[1].co.z) > 1.0


def build_pier(name, seed=29):
    shaft = K.box(8, 92, 8, 92, 44, 445, S1, 4.0, edge_filter=_vertical_edge)
    cut = pier_cutters(47, 438, seed)
    sh = K.boolean_diff(shaft, cut)
    cut.free()
    shaft.free()
    out = pier_base_cap(seed)
    K.bm_append(out, sh)
    sh.free()
    return Piece(name, out, [K.box_hull(0, 100, 0, 100, 0, 500)], (100, 100, 500))


def build_pier_broken(name, seed=31):
    H = 350.0
    shaft = K.box(8, 92, 8, 92, 44, H, S1, 4.0, edge_filter=_vertical_edge)
    cut = pier_cutters(47, H - 20, seed)
    sh = K.boolean_diff(shaft, cut)
    cut.free()
    shaft.free()

    def f(x, y):
        tilt = 78.0 * (x * 0.8 + (100 - y) * 0.45) / 125.0
        n = (K.fbm(x / 28.0 + 1.7, y / 28.0 + 4.3, seed, 3) - 0.5) * 56.0
        dip = max(0.0, tilt + n)
        return min(H + 12.0 - dip, H + 12.0)

    rng = random.Random(seed)
    fc = K.hf_solid(-6, 106, -6, 106, f, H + 60.0, 14, 14, ('x', 'y', 'z'), S2, rng)
    sh2 = K.boolean_diff(sh, fc)
    fc.free()
    sh.free()
    out = pier_base_cap(seed, with_cap=False)
    K.bm_append(out, sh2)
    sh2.free()
    return Piece(name, out, [K.box_hull(0, 100, 0, 100, 0, 260)], (100, 100, 350))


def build_floor(name, seed=37):
    N, S, H = 40, 1000.0, 40.0
    b = K.bmesh.new()
    two = 2 * math.pi

    def relief(x, y):
        u, v = x / S, y / S
        r = (0.40 * math.sin(two * (3 * u + 2 * v) + 0.7) + 0.28 * math.sin(two * (5 * u - 7 * v) + 2.1)
             + 0.22 * math.sin(two * (9 * u + 4 * v) + 4.0) + 0.18 * math.sin(two * (13 * u - 11 * v) + 1.3))
        return -0.75 + r * 0.75          # about [-1.5, 0], periodic over the slab so neighbours tile exactly

    g = [[None] * (N + 1) for _ in range(N + 1)]
    for i in range(N + 1):
        for j in range(N + 1):
            x, y = S * i / N, S * j / N
            z = H + min(0.0, max(-1.5, relief(x, y)))
            g[i][j] = b.verts.new((x, y, z))
    for i in range(N):
        for j in range(N):
            a, c, d, e = g[i][j], g[i + 1][j], g[i + 1][j + 1], g[i][j + 1]
            if (i + j) % 2 == 0:
                b.faces.new((a, c, d))
                b.faces.new((a, d, e))
            else:
                b.faces.new((a, c, e))
                b.faces.new((c, d, e))
    c00, c10, c11, c01 = (b.verts.new(c) for c in ((0, 0, 0), (S, 0, 0), (S, S, 0), (0, S, 0)))
    b.faces.new((c00, c01, c11, c10))
    b.faces.new([c00, c10] + [g[i][0] for i in range(N, -1, -1)][::-1][::-1][:0] + [g[i][0] for i in range(N, -1, -1)])
    b.faces.new([c10, c11] + [g[N][j] for j in range(N, -1, -1)])
    b.faces.new([c11, c01] + [g[i][N] for i in range(0, N + 1)])
    b.faces.new([c01, c00] + [g[0][j] for j in range(0, N + 1)])
    K._outward(b)
    K.bm_set_mat(b, S0)
    return Piece(name, b, [K.box_hull(0, S, 0, S, 0, H)], (S, S, H))


def stone_points(rng, sx, sy, sz, jitter=0.14, extra=5, top_flat=False, clip_corners=0):
    """Points of a jittered box (centred on the origin) scaled to roughly sx*sy*sz."""
    pts = []
    for ix in (-1, 1):
        for iy in (-1, 1):
            for iz in (-1, 1):
                p = Vector((ix * sx / 2, iy * sy / 2, iz * sz / 2))
                jz = jitter * (0.2 if (top_flat and iz > 0) else 1.0)
                p += Vector((rng.uniform(-1, 1) * sx * jitter, rng.uniform(-1, 1) * sy * jitter, rng.uniform(-1, 1) * sz * jz))
                pts.append(p)
    for _ in range(extra):
        p = Vector((rng.uniform(-0.55, 0.55) * sx, rng.uniform(-0.55, 0.55) * sy, rng.uniform(-0.55, 0.55) * sz))
        ax = rng.randrange(3)
        sgn = rng.choice((-1, 1))
        p[ax] = sgn * (0.5 + rng.uniform(0.0, 0.05)) * (sx, sy, sz)[ax]
        pts.append(p)
    if top_flat:
        for p in pts:
            if p.z > sz * 0.3:
                p.z = sz / 2
    for _k in range(clip_corners):
        ix, iy, iz = rng.choice((-1, 1)), rng.choice((-1, 1)), rng.choice((-1, 1))
        c = Vector((ix * sx / 2, iy * sy / 2, iz * sz / 2))
        pts = [p for p in pts if (p - c).length > 1e-3 + max(sx, sy, sz) * jitter * 1.8]
        d = min(sx, sy, sz) * rng.uniform(0.18, 0.32)
        pts.append(c + Vector((-ix * d, 0, 0)))
        pts.append(c + Vector((0, -iy * d, 0)))
        pts.append(c + Vector((0, 0, -iz * d)))
    return pts


def rock_points(rng, sx, sy, sz, n=26, expo=3.2, noise=0.2, flat_top=None):
    """Random irregular rock: points on a super-ellipsoid with radial noise (hull gives many irregular facets)."""
    pts = []
    for _ in range(n):
        v = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1)))
        if v.length < 1e-6:
            continue
        v.normalize()
        r = 1.0 / ((abs(v.x) ** expo + abs(v.y) ** expo + abs(v.z) ** expo) ** (1.0 / expo))
        r *= 1.0 + noise * rng.uniform(-1.0, 1.0)
        p = v * r
        pts.append(Vector((p.x * sx / 2, p.y * sy / 2, p.z * sz / 2)))
    if flat_top is not None:
        for p in pts:
            p.z = min(p.z, flat_top * sz / 2)
    return pts


def fit_points(pts, size):
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    sc = Vector((size[0] / max(mx.x - mn.x, 1e-6), size[1] / max(mx.y - mn.y, 1e-6), size[2] / max(mx.z - mn.z, 1e-6)))
    return [Vector(((p.x - mn.x) * sc.x, (p.y - mn.y) * sc.y, (p.z - mn.z) * sc.z)) for p in pts]


def slot_rubble(bm, dressed_axes=True, top_slot=None):
    bm.normal_update()
    for f in bm.faces:
        n = f.normal
        if dressed_axes and max(abs(n.x), abs(n.y), abs(n.z)) > 0.985:
            f.material_index = S1
        else:
            f.material_index = S2
        if top_slot is not None and n.z > 0.97:
            f.material_index = top_slot


def build_rubble(name, size, seed, kind):
    rng = random.Random(seed)
    if kind == 'S':
        pts = stone_points(rng, *size, jitter=0.05, extra=0, clip_corners=3)
    elif kind == 'M':
        pts = rock_points(rng, *size, n=28, expo=3.0, noise=0.22)
    else:
        pts = rock_points(rng, *size, n=30, expo=3.6, noise=0.14, flat_top=0.8)
    pts = fit_points(pts, size)
    hull = K.hull_from_points(pts, S2)
    col = K.hull_from_points(pts, S2, merge_coplanar=False)
    K.bevel_all(hull, 2.4, 15.0)
    mn, mx = K.bm_bounds(hull)
    for v in hull.verts:
        v.co = Vector(((v.co.x - mn[0]) * size[0] / (mx[0] - mn[0]), (v.co.y - mn[1]) * size[1] / (mx[1] - mn[1]),
                       (v.co.z - mn[2]) * size[2] / (mx[2] - mn[2])))
    slot_rubble(hull, dressed_axes=(kind in 'SL'), top_slot=(S1 if kind == 'L' else None))
    return Piece(name, hull, [col], size)


def build_heap(name, seed=53):
    from mathutils import Euler
    rng = random.Random(seed)
    out = K.bmesh.new()
    placed = []
    for _i in range(48):
        ang = rng.uniform(0, 2 * math.pi)
        r = (rng.random() ** 0.7) * 0.92
        x, y = 200 + math.cos(ang) * r * 190, 150 + math.sin(ang) * r * 135
        h = 130.0 * max(0.0, 1 - r * r) ** 0.7
        sz = rng.uniform(28, 80) * (1.0 - 0.3 * r)
        sx, sy, sz2 = sz * rng.uniform(0.8, 1.4), sz * rng.uniform(0.7, 1.2), sz * rng.uniform(0.45, 0.9)
        zc = max(sz2 * 0.5, h * rng.uniform(0.35, 0.8) - sz2 * 0.15)
        placed.append((x, y, zc, sx, sy, sz2))
    placed.sort(key=lambda t: t[2])
    for (x, y, zc, sx, sy, sz) in placed:
        pts = rock_points(rng, sx, sy, sz, n=18, expo=3.0, noise=0.22)
        rot = Euler((rng.uniform(-0.35, 0.35), rng.uniform(-0.35, 0.35), rng.uniform(0, 6.28))).to_matrix()
        pts = [rot @ p + Vector((x, y, zc)) for p in pts]
        hl = K.hull_from_points(pts, S2)
        K.bevel_all(hl, 2.0, 15.0)
        K.bm_append(out, hl)
        hl.free()
    mn, mx = K.bm_bounds(out)
    sc = (400.0 / (mx[0] - mn[0]), 300.0 / (mx[1] - mn[1]), 130.0 / (mx[2] - mn[2]))
    for v in out.verts:
        v.co = Vector(((v.co.x - mn[0]) * sc[0], (v.co.y - mn[1]) * sc[1], (v.co.z - mn[2]) * sc[2]))
    slot_rubble(out, dressed_axes=False)
    ucx = [K.box_hull(30, 370, 20, 280, 0, 60), K.box_hull(110, 300, 70, 235, 0, 118)]
    return Piece(name, out, ucx, (400, 300, 130))


def facet_field(rng, u0, u1, v0, v1, cell, amp, gu, gv, aniso=1.0):
    """Voronoi-plane field f(u, v): one randomly tilted plane per cell -> crisp facets and creases."""
    seeds = []
    for i in range(-1, int((u1 - u0) / cell) + 3):
        for j in range(-1, int((v1 - v0) / cell) + 3):
            seeds.append((u0 + (i + rng.uniform(0.15, 0.85)) * cell, v0 + (j + rng.uniform(0.15, 0.85)) * cell,
                          rng.uniform(-0.5, 0.5) * amp, rng.uniform(-gu, gu), rng.uniform(-gv, gv)))

    def f(u, v):
        s = min(seeds, key=lambda t: (t[0] - u) ** 2 + ((t[1] - v) * aniso) ** 2)
        return s[2] + s[3] * (u - s[0]) + s[4] * (v - s[1])

    return f


def build_cliff(name, seed, variant, L=500.0, H=600.0, end=False):
    """Rock cliff piece.  Front (y=0, the path side), top and both ends are faceted/displaced rock; the back (y=T) and
    the bottom are flat.  End planes are rough and set back 0..30 cm (the nose of an end piece up to ~70 cm), so slabs
    in a run must overlap by ~60 cm (pitch 440 for a 500 slab) -- see MODULAR_KIT.md."""
    T = 300.0
    nx, ny, nz = int(L / 17), 10, int(H / 17)
    b = K.lattice_box(L, T, H, nx, ny, nz, S0, flat_back_bottom=True)
    rng = random.Random(seed)
    cell = (95.0, 80.0, 70.0)[('A', 'B', 'C').index(variant)]
    ph = rng.uniform(0, 6.28)
    # multi-scale breakup: a few big planar cleavage faces, medium blocks and small facets whose weight varies across
    # the face (low-frequency mask), plus fine noise; depths are limited so creases do not become dark pockets
    ff1 = facet_field(rng, 0, L, 0, H, cell * 2.4, 30.0, 0.22, 0.30, 0.6)      # large tall planes
    ff2 = facet_field(rng, 0, L, 0, H, cell * 1.0, 15.0, 0.25, 0.30, 0.75)     # medium blocks
    ff3 = facet_field(rng, 0, L, 0, H, cell * 0.42, 8.0, 0.30, 0.30, 0.9)      # small facets
    mask_seed = seed + 77

    def ff(x, z):
        m = K.smoothstep(0.30, 0.70, K.fbm(x / 240.0 + 3.3, z / 280.0 + 1.1, mask_seed, 2))   # 1 = busy, 0 = calm
        v = ff1(x, z) + ff2(x, z) * (0.45 + 0.9 * m) + ff3(x, z) * (0.2 + 1.3 * m)
        v += 6.0 * (K.vnoise(x / 11.0, z / 11.0, seed + 21) - 0.5) + 3.0 * (K.vnoise(x / 5.0, z / 5.0, seed + 22) - 0.5)
        return v

    dmax = 80.0 if H > 400 else 55.0
    ft = facet_field(rng, 0, L, 0, T, cell * 1.1, dmax * 1.1, 0.30, 0.25)
    fe_a = facet_field(rng, 0, T, 0, H, 120.0, 30.0, 0.3, 0.3, 0.6)
    fe_b = facet_field(rng, 0, T, 0, H, 120.0, 30.0, 0.3, 0.3, 0.6)
    fe = lambda y, z: fe_a(y, z) + 10.0 * (K.vnoise(y / 12.0, z / 12.0, seed + 31) - 0.5)
    fe2 = lambda y, z: fe_b(y, z) + 10.0 * (K.vnoise(y / 12.0, z / 12.0, seed + 33) - 0.5)

    def nose(x):
        return K.smoothstep(0.3, 1.0, x / L) if end else 0.0

    def recess(x, z):
        v = 18.0 + ff(x, z)
        v += 22.0 * math.exp(-((z - 0.42 * H) / (0.22 * H)) ** 2)            # ledge: mid heights set back -> overhang above
        v += 5.0 * math.sin(z / 47.0 + ph + K.vnoise(x / 130.0, 1.0, seed + 9) * 4.0)
        v = max(0.0, min(62.0, v))                                             # crease depth clamp
        v += 150.0 * nose(x) ** 1.5
        return v * K.smoothstep(0.0, 40.0, z)

    def top_drop(x, y):
        v = dmax * 0.42 + ft(x, y)
        v += (240.0 if H > 400 else 130.0) * nose(x) ** 1.2
        return max(0.0, v)

    def end0(y, z):
        return max(0.0, min(30.0, 12.0 + fe(y, z)))

    def end1(y, z):
        e = max(0.0, min(30.0, 12.0 + fe2(y, z)))
        if end:
            e = 22.0 + 50.0 * (1.0 - y / T) ** 1.4 + 1.1 * fe2(y, z)
        return max(0.0, e)

    for v in b.verts:
        x, y, z = v.co.x, v.co.y, v.co.z
        on_front, on_top = y < 0.01, z > H - 0.01
        on0, on1 = x < 0.01, x > L - 0.01
        nx_, nz_ = x, z
        if on_front:
            nx_ = x + (rng.uniform(-5, 5) if (1 < x < L - 1) else 0.0)
            nz_ = z + (rng.uniform(-5, 5) if (1 < z < H - 1) else 0.0)
            v.co.y = recess(nx_, nz_)
            v.co.z = nz_
        else:
            # remap the depth interval [0, T] onto [recess, T] so interior rows never fold behind the front row
            rc = recess(x, z)
            v.co.y = rc + y * (T - rc) / T
        if on_top:
            v.co.z = H - top_drop(x, y)
        if on0:
            v.co.x = end0(y, z)
        elif on1:
            v.co.x = L - end1(y, z)
        elif on_front:
            v.co.x = nx_
    # exact envelope: x in [0, L], top reaches H, y in [0, T]
    xs = [v.co.x for v in b.verts]
    x0, x1 = min(xs), max(xs)
    for v in b.verts:
        v.co.x = (v.co.x - x0) * L / (x1 - x0)
    zmax = max(v.co.z for v in b.verts)
    for v in b.verts:
        if v.co.z > H - 1e-3 or v.co.z > zmax - 1e-3:
            pass
    if zmax < H - 1e-4:
        top = [v for v in b.verts if v.co.z > zmax - 1e-4]
        for v in top:
            v.co.z += H - zmax
    pts_by = [v.co.copy() for v in b.verts]
    K.bmesh.ops.triangulate(b, faces=b.faces[:], quad_method='SHORT_EDGE')
    b.normal_update()
    for f in b.faces:
        n = f.normal
        f.material_index = S2 if (n.y > 0.9 or n.z < -0.9) else S0
    # collision: one convex hull per X section, built from the displaced surface points (front/top/ends)
    secs = 16 if end else 8
    bands = 6 if end else (5 if H > 400 else 3)
    ucx = []
    for s_ in range(secs):
        a, c = L * s_ / secs, L * (s_ + 1) / secs
        # the rounded nose of an end piece also needs splitting in depth (Y) to stay close to the visual
        yr = [(-1e9, 1e9)]
        for k_ in range(bands):
            z0, z1 = H * k_ / bands, H * (k_ + 1) / bands
            for (ya, yb) in yr:
                pts = [p for p in pts_by if a - 16 <= p.x <= c + 16 and z0 - 16 <= p.z <= z1 + 16 and ya <= p.y <= yb]
                if len(pts) < 8:
                    continue
                ucx.append(K.hull_from_points([Vector(p) for p in pts], S2, merge_coplanar=False))
    pc = Piece(name, b, ucx, (L, T, H))
    pc.smooth = 22.0
    return pc


def carve_and_merge(body, cutters, extra_solids=()):
    """body - (all cutters + inflated extra_solids); returns body with the extra solids appended (merged)."""
    cut = K.bmesh.new()
    for c in cutters:
        K.bm_append(cut, c)
    for s in extra_solids:
        t = s.copy()
        K.inflate(t, 0.35)
        K.bm_set_mat(t, 3)                 # cavity behind the stones: tagged, then deleted (hidden geometry)
        K.bm_append(cut, t)
        t.free()
    res = K.boolean_diff(body, cut)
    cut.free()
    hidden = [f for f in res.faces if f.material_index == 3]
    if hidden:
        K.bmesh.ops.delete(res, geom=hidden, context='FACES_ONLY')
        K.bmesh.ops.delete(res, geom=[e for e in res.edges if not e.link_faces], context='EDGES')
        K.bmesh.ops.delete(res, geom=[v for v in res.verts if not v.link_edges], context='VERTS')
    for s in extra_solids:
        K.bm_append(res, s)
    return res


def build_doorway(name, seed=13):
    L, T, H = 400.0, 60.0, 400.0
    cx, zs = 200.0, 240.0
    z_body = H - CAP_H
    body = K.box(0, L, 0, T, 0, z_body, S0)
    courses = K.make_courses(z_body, seed, False)
    relief = relief_both(L, T, 0, z_body, courses, seed, z_start=0.0)
    op = K.Opening(cx, 0.0, zs, 120.0, 120.0,
                   orders=[dict(t0=0.0, t1=12.5, recess=10.0), dict(t0=12.5, t1=25.0, recess=0.0)],
                   T=T, seed=seed, n_vouss=6, bevel=1.8, jamb_h=44.0, alt=7.0)
    shell = carve_and_merge(body, [relief, op.carve], [op.stones])
    capm = cap_course(L, T, z_body, H, seed)
    out = K.combine(shell, capm)
    for b in (body, relief, shell, capm, op.carve, op.stones):
        b.free()
    ucx = [K.box_hull(0, 140, 0, T, 0, H), K.box_hull(260, 400, 0, T, 0, H), K.box_hull(140, 260, 0, T, zs, H)]
    return Piece(name, out, ucx, (L, T, H), clear=(140, 260, 0, T, 0, zs))


def build_gate(name, seed=17):
    L, T, H = 1200.0, 300.0, 800.0
    zs = 300.0
    z_body = H - CAP_H
    body = K.box(0, L, 0, T, 0, z_body, S0)
    courses = K.make_courses(z_body, seed, False)
    f, b = face_frames(L, T)
    relief = K.relief_cutters(f, 0, L, 0, z_body, courses, seed, z_start=0.0, wmin=100, wmax=210, chips=8, recess_prob=0.15)
    K.bm_append(relief, K.relief_cutters(b, 0, L, 0, z_body, courses, seed + 101, z_start=0.0, wmin=100, wmax=210, chips=8, recess_prob=0.15))
    fe0 = K.FaceFrame((0, 0, 0), (0, 1, 0), (-1, 0, 0))
    fe1 = K.FaceFrame((L, T, 0), (0, -1, 0), (1, 0, 0))
    K.bm_append(relief, K.relief_cutters(fe0, 0, T, 0, z_body, courses, seed + 5, z_start=0.0, wmin=90, wmax=170, chips=3, recess_prob=0.12))
    K.bm_append(relief, K.relief_cutters(fe1, 0, T, 0, z_body, courses, seed + 6, z_start=0.0, wmin=90, wmax=170, chips=3, recess_prob=0.12))
    op = K.Opening(L / 2, 0.0, zs, 400.0, 400.0,
                   orders=[dict(t0=0.0, t1=44.0, recess=16.0), dict(t0=44.0, t1=84.0, recess=0.0)],
                   T=T, seed=seed, dressed_depth=46.0, rough_extra=3.5, n_vouss=6, bevel=2.4, jamb_h=60.0, alt=9.0)
    quoins = K.bmesh.new()
    for corner in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        K.bm_append(quoins, K.quoin_stones(0, L, 0, T, 0, z_body, courses, corner, 50.0, 30.0, 2.6))
    shell = carve_and_merge(body, [relief, op.carve], [op.stones, quoins])
    capm = cap_course(L, T, z_body, H, seed, ctop=5.0, cbot=3.0)
    out = K.combine(shell, capm)
    for bb in (body, relief, shell, capm, op.carve, op.stones, quoins):
        bb.free()
    ucx = [K.box_hull(0, 400, 0, T, 0, H), K.box_hull(800, L, 0, T, 0, H), K.box_hull(400, 800, 0, T, zs, H)]
    return Piece(name, out, ucx, (L, T, H), clear=(400, 800, 0, T, 0, zs))


def build_window_blind(name, seed=19):
    L, T, H = 200.0, 60.0, 400.0
    cx = 100.0
    z_body = H - CAP_H
    body = K.box(0, L, 0, T, 0, z_body, S0)
    courses = K.make_courses(z_body, seed, False)
    relief = relief_both(L, T, 0, z_body, courses, seed, z_start=0.0, wmin=55, wmax=100)
    zb, zs = 112.0, 240.0
    op = K.Opening(cx, zb, zs, 70.0, 95.0, orders=[dict(t0=0.0, t1=18.0, recess=0.0, lip=7.0)],
                   T=T, seed=seed, blind_depth=14.0, n_vouss=5, bevel=1.6, z_stone_bot=zb, jamb_h=40.0, alt=5.0)
    sill = K.box(cx - 62, cx + 62, 0, 26, zb - 12, zb, S1, 2.0)
    shell = carve_and_merge(body, [relief, op.carve], [op.stones, sill])
    capm = cap_course(L, T, z_body, H, seed)
    out = K.combine(shell, capm)
    for bb in (body, relief, shell, capm, op.carve, op.stones, sill):
        bb.free()
    return Piece(name, out, [K.box_hull(0, L, 0, T, 0, H)], (L, T, H))


# ==============================================================================================
# P7-FIX3 G2a: cloister arcade bay (four-centred pointed arch) and garden kerbs
# ==============================================================================================
ARC_L, ARC_T, ARC_H = 1000.0, 60.0, 400.0
ARC_X0, ARC_X1, ARC_RISE = 50.0, 950.0, 300.0       # opening X 50..950, springing Z 0, apex Z 300
ARC_R_LOW, ARC_PHI = 150.0, 57.0                    # lower (corner) arc radius cm, junction angle deg
ARC_RING = 60.0                                     # voussoir ring width (radial)
ARC_BAND_TOP = 370.0                                # masonry band top; coping 370..400
ARC_RECESS = 2.0                                    # band face recessed behind ring + coping
ARC_COURSES = [50.0] * 6 + [35.0, 35.0]


class FourCentre:
    """Four-centred (Tudor) pointed arch: two lower arcs of radius r centred on the springing line and two upper arcs
    of radius R (centres below the springing line) that meet in a point on the axis.  Offset curves (extrados)
    are concentric, so radial joints stay radial."""

    def __init__(self, x0=ARC_X0, x1=ARC_X1, rise=ARC_RISE, r=ARC_R_LOW, phi_deg=ARC_PHI):
        self.cx = (x0 + x1) * 0.5
        a = (x1 - x0) * 0.5
        p = math.radians(phi_deg)
        A = a - r
        d = (A * A + rise * rise - r * r) / (2 * A * math.cos(p) - 2 * rise * math.sin(p) + 2 * r)
        self.x0, self.r, self.R, self.phi = x0, r, r + d, p
        self.C1 = (x0 + r, 0.0)
        self.C2 = (x0 + r + d * math.cos(p), -d * math.sin(p))
        self.th_a0 = self.theta_apex(0.0)
        L1, L2 = r * p, self.R * (self.th_a0 - p)
        self.u_junction = L1 / (L1 + L2)
        self.length = L1 + L2

    def theta_apex(self, t):
        return math.acos((self.C2[0] - self.cx) / (self.R + t))

    def pt(self, u, t):
        """Left-half point at parameter u (0 springing .. 1 apex), radial offset t (outside positive)."""
        uj = self.u_junction
        if u <= uj + 1e-12:
            th = self.phi * (u / uj)
            return (self.C1[0] - (self.r + t) * math.cos(th), (self.r + t) * math.sin(th))
        f = (u - uj) / (1.0 - uj)
        th = self.phi + (self.theta_apex(t) - self.phi) * f
        return (self.C2[0] - (self.R + t) * math.cos(th), self.C2[1] + (self.R + t) * math.sin(th))

    def curve_left(self, t, n_low=10, n_up=24):
        uj = self.u_junction
        us = [uj * i / n_low for i in range(n_low)] + [uj + (1 - uj) * i / n_up for i in range(n_up + 1)]
        return [self.pt(u, t) for u in us]

    def mirror(self, p):
        return (2 * self.cx - p[0], p[1])

    def intrados_z(self, x):
        """Intrados height at X (None outside the opening)."""
        if x < self.x0 or x > 2 * self.cx - self.x0:
            return None
        if x > self.cx:
            x = 2 * self.cx - x
        lo, hi = 0.0, 1.0
        for _ in range(48):
            mid = (lo + hi) * 0.5
            if self.pt(mid, 0.0)[0] < x:
                lo = mid
            else:
                hi = mid
        return self.pt(lo, 0.0)[1]

    def extrados_z(self, x, t=ARC_RING):
        pts = self.curve_left(t, 40, 80)
        if x > self.cx:
            x = 2 * self.cx - x
        best = None
        for (xa, za), (xb, zb) in zip(pts, pts[1:]):
            if xa <= x <= xb and xb > xa:
                best = za + (zb - za) * (x - xa) / (xb - xa)
        return best if best is not None else 0.0


ARCH = FourCentre()


def arch_intrados_z(x):
    return ARCH.intrados_z(x)


def clip_x(poly, xmin, xmax):
    """Sutherland-Hodgman clip of a (x, z) polygon against xmin <= x <= xmax."""
    def clip(pl, inside, inter):
        out = []
        for i in range(len(pl)):
            a, b = pl[i], pl[(i + 1) % len(pl)]
            ia, ib = inside(a), inside(b)
            if ia:
                out.append(a)
            if ia != ib:
                out.append(inter(a, b))
        return out

    def ix(xv):
        return lambda a, b: (xv, a[1] + (b[1] - a[1]) * (xv - a[0]) / (b[0] - a[0]))

    pl = clip(poly, lambda p: p[0] >= xmin, ix(xmin))
    if pl:
        pl = clip(pl, lambda p: p[0] <= xmax, ix(xmax))
    out = []
    for p in pl:
        if not out or abs(p[0] - out[-1][0]) > 1e-6 or abs(p[1] - out[-1][1]) > 1e-6:
            out.append(p)
    if len(out) > 2 and abs(out[0][0] - out[-1][0]) < 1e-6 and abs(out[0][1] - out[-1][1]) < 1e-6:
        out.pop()
    return out


def arcade_ring_stones(seed, bevel=1.5):
    """Voussoir stones of the ring (both halves), slot 1, full thickness Y 0..60, chamfered; clipped to the slab X 0..1000.
    Every other stone is a 'long' stone that bites 5 cm into the band (keystone halves are not)."""
    rng = random.Random(seed)
    n = int(round(ARCH.length / 58.0))
    stones = []
    for side in (-1, 1):
        for k in range(n):
            u0, u1 = k / n, (k + 1) / n
            alt = 5.0 if (k % 2 == 1 and k != n - 1 and k != 0) else 0.0
            if rng.random() < 0.15 and k not in (0, n - 1):
                alt = 5.0 - alt
            uu = [u0 + (u1 - u0) * i / 3.0 for i in range(4)]
            if u0 < ARCH.u_junction < u1:
                uu = sorted(set(uu + [ARCH.u_junction]))
            inner = [ARCH.pt(u, 0.0) for u in uu]
            outer = [ARCH.pt(u, ARC_RING + alt) for u in uu]
            poly = inner + outer[::-1]
            if side > 0:
                poly = [ARCH.mirror(p) for p in poly][::-1]
            poly = clip_x(poly, 0.0, ARC_L)
            if len(poly) < 3:
                continue
            s = K.prism(poly, 'y', 0.0, ARC_T, S1)
            K.bevel_all(s, bevel, 25.0)
            stones.append(s)
    return stones


def arcade_carve_polygon():
    left = ARCH.curve_left(ARC_RING, 20, 60)
    right = [ARCH.mirror(p) for p in left][::-1]
    poly = [(left[0][0] - 1.0, -1.0)] + left + right[1:] + [(right[0][0] + 1.0, -1.0)]
    return poly


def build_arcade_intact(seed=151):
    """Returns (shell_pieces, stones): masonry body (slot 0, relief, arch carved) + coping; stones are the ring."""
    body = K.box(0, ARC_L, ARC_RECESS, ARC_T - ARC_RECESS, 0, ARC_BAND_TOP, S0)
    f = K.FaceFrame((0, ARC_RECESS, 0), (1, 0, 0), (0, -1, 0))
    b = K.FaceFrame((ARC_L, ARC_T - ARC_RECESS, 0), (-1, 0, 0), (0, 1, 0))
    relief = K.relief_cutters(f, 0, ARC_L, 0, ARC_BAND_TOP, ARC_COURSES, seed, z_start=0.0, wmin=80, wmax=160, chips=6, recess_prob=0.15)
    K.bm_append(relief, K.relief_cutters(b, 0, ARC_L, 0, ARC_BAND_TOP, ARC_COURSES, seed + 101, z_start=0.0, wmin=80, wmax=160, chips=6, recess_prob=0.15))
    carve = K.prism(arcade_carve_polygon(), 'y', -1.0, ARC_T + 1.0, S1)
    stones = arcade_ring_stones(seed + 3)
    return body, relief, carve, stones


def arcade_cutters(seed):
    """Fracture cutters for BrokenA (material remains for X < 350): ragged end plane stepped per course + collapsed top."""
    rng = random.Random(seed + 900)
    X_END = 350.0
    zb = [0.0]
    for h in ARC_COURSES:
        zb.append(zb[-1] + h)
    c_ring = None
    z_mid = 0.5 * (ARCH.intrados_z(X_END - 8.0) + ARCH.extrados_z(X_END - 8.0))
    for i in range(len(zb) - 1):
        if zb[i] <= z_mid < zb[i + 1]:
            c_ring = i
    offs = [rng.choice((20.0, 35.0, 55.0, 75.0)) for _ in ARC_COURSES]
    offs[c_ring] = 0.0                                   # this course reaches X 350 exactly (envelope)
    if c_ring + 1 < len(offs):
        offs[c_ring + 1] = rng.choice((25.0, 45.0))

    def e(y, z):
        zz = z + (K.vnoise(y / 14.0 + 2.0, z / 30.0, seed + 31) - 0.5) * 18.0
        i = 0
        for k in range(len(zb) - 1):
            if zb[k] <= zz:
                i = k
        i = min(i, len(offs) - 1)
        # soften the course steps over 10 cm so the cutter stays a height field
        t = (zz - zb[i]) / 10.0
        o = offs[i]
        if t < 1.0 and i > 0:
            o = offs[i - 1] + (offs[i] - offs[i - 1]) * max(0.0, t)
        v = o + (K.vnoise(y / 11.0 + 9.0, z / 17.0, seed + 41) - 0.5) * 20.0 + 0.18 * (y - ARC_T * 0.5) * (1.0 if o > 10 else 0.0)
        return max(0.0, v)

    cut = K.hf_solid(-6, ARC_T + 6, -6, ARC_H + 8, lambda y, z: X_END - e(y, z), 1100.0, 6, 70, ('y', 'z', 'x'), S2, rng)
    # collapsed top: stair of course tops that falls toward the break
    blocks, x = [], 110.0
    while x < 1010.0:
        w = rng.uniform(34.0, 66.0)
        blocks.append((x, x + w))
        x += w
    tops = []
    zcands = zb[1:]                                       # 50 .. 370
    for (xa, xb) in blocks:
        xc = 0.5 * (xa + xb)
        need = ARCH.extrados_z(min(xb, 940.0)) + 6.0 if xb < 940.0 else 0.0
        target = 400.0 - 92.0 * K.smoothstep(130.0, 350.0, xc)
        target = max(target, need)
        if xc < 150.0:
            tops.append(460.0)
            continue
        z = min([c for c in zcands if c >= target] or [400.0])
        if rng.random() < 0.3 and z - 50.0 >= need:
            z -= 50.0 if z > 100.0 else 0.0
        tops.append(max(z, need) if z < 400.0 else 460.0)

    import bisect
    edges_ = [bb[1] for bb in blocks]

    def ztop(xv, yv):
        i = min(bisect.bisect_left(edges_, xv), len(tops) - 1)
        zt = tops[i]
        if zt >= 459.0:
            return zt
        return zt + (K.vnoise(xv / 7.0, yv / 7.0, seed + 61) - 0.5) * 7.0 + 0.12 * (yv - ARC_T * 0.5)

    top = K.hf_solid(100.0, 1010.0, -6, ARC_T + 6, ztop, 520.0, int(910 / 6), 6, ('x', 'y', 'z'), S2, rng)
    K.bm_append(cut, top)
    top.free()
    return cut


def _bm_mirror_x(bm, cx=ARC_L * 0.5):
    for v in bm.verts:
        v.co.x = 2 * cx - v.co.x
    K.bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return bm


def _top_heights(bm, xs, y=ARC_T * 0.5):
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromBMesh(bm)
    out = []
    for x in xs:
        h = bvh.ray_cast(Vector((x, y, 800.0)), Vector((0, 0, -1)))
        out.append(h[0].z if h[0] is not None else None)
    return out


def build_arcade(name, broken=None, seed=151):
    """broken: None | 'A' | 'B'.  A keeps X 0..350 (seeded fractured edge, ring stub springing from X 50), B is its mirror (X 650..1000)."""
    body, relief, carve, stones = build_arcade_intact(seed)
    coping = cap_course(ARC_L, ARC_T, ARC_BAND_TOP, ARC_H, seed)
    cutters = [relief, carve]
    fc = None
    if broken:
        fc = arcade_cutters(seed if broken == 'A' else seed + 77)
        bc = K.boolean_diff(body, fc)             # fracture first (closed solid), then the arch carve + ring stones
        body.free()
        body = bc
        kept = []
        for s in stones:
            r = K.boolean_diff(s, fc)
            if len(r.faces) >= 4:
                kept.append(r)
            s.free()
        stones = kept
        cp = K.boolean_diff(coping, fc)
        coping.free()
        coping = cp
    shell = carve_and_merge(body, cutters, stones)
    out = K.combine(shell, coping)
    for bb in (body, shell, coping, relief, carve):
        bb.free()
    if fc is not None:
        fc.free()
    if not broken:
        ucx = [K.box_hull(0, 50, 0, ARC_T, 0, ARC_H), K.box_hull(950, 1000, 0, ARC_T, 0, ARC_H),
               K.box_hull(0, ARC_L, 0, ARC_T, 300, ARC_H)]
        return Piece(name, out, ucx, (ARC_L, ARC_T, ARC_H), clear=(50, 950, 0, ARC_T, 0, 250))
    # broken stub: end band box + one box over the ring stub (kept above the intrados so the opening stays clear)
    x_hi = 320.0
    xs = [60.0 + 10.0 * i for i in range(int((x_hi - 60.0) / 10.0) + 1)]
    tops = [t for t in _top_heights(out, xs) if t is not None]
    z_lo = ARCH.intrados_z(x_hi) + 2.0
    z_hi = (min(tops) - 4.0) if tops else 0.0
    ucx = [K.box_hull(0, 50, 0, ARC_T, 0, ARC_H)]
    if z_hi - z_lo > 12.0:
        ucx.append(K.box_hull(50, x_hi, 4, ARC_T - 4, z_lo, z_hi))
    if broken == 'B':
        _bm_mirror_x(out)
        for u in ucx:
            _bm_mirror_x(u)
    pc = Piece(name, out, ucx, (350.0, ARC_T, ARC_H))
    pc.clear = (50, 350, 0, ARC_T, 0, 200) if broken == 'A' else (650, 950, 0, ARC_T, 0, 200)
    return pc


def build_kerb(name, L, seed, broken=False):
    T, H = 30.0, 40.0
    body = K.box(0, L, 0, T, 0, H, S1, 2.0)
    f = K.FaceFrame((0, 0, 0), (1, 0, 0), (0, -1, 0))
    b = K.FaceFrame((L, T, 0), (-1, 0, 0), (0, 1, 0))
    chips = 3 if broken else 2
    cut = K.relief_cutters(f, 0, L, 0, H, [H], seed, h_grooves=False, recess_prob=0.0, chips=chips, wmin=98, wmax=102,
                           z_start=0.0, groove_mat=S1, chip_mat=S2, joint_depth=1.2, joint_w=2.4)
    K.bm_append(cut, K.relief_cutters(b, 0, L, 0, H, [H], seed + 5, h_grooves=False, recess_prob=0.0, chips=chips, wmin=98, wmax=102,
                                      z_start=0.0, groove_mat=S1, chip_mat=S2, joint_depth=1.2, joint_w=2.4))
    ucx_h = H
    if broken:
        rng = random.Random(seed + 11)
        h, prof = stepped_profile(L, H, 22.0, seed + 13, tooth_at=0, seg=(30, 55))
        xc = rng.uniform(95.0, 135.0)

        def f2(x, y):
            v = h(min(max(x, 0.0), L)) + (K.vnoise(y / 9.0 + 3.1, x / 30.0, seed) - 0.5) * 5.0
            xs_ = xc + 6.0 * (y - T / 2) / (T / 2)
            dx = abs(x - xs_)
            chunk = 13.0 + max(0.0, dx - 22.0) * 1.35 + (K.vnoise(x / 6.0, y / 6.0, seed + 5) - 0.5) * 4.0
            return min(v, chunk, H + 12.0)

        fr = K.hf_solid(-6, L + 6, -6, T + 6, f2, H + 40.0, int((L + 12) / 5.0), 8, ('x', 'y', 'z'), S2, rng)
        cut_all = K.bmesh.new()
        K.bm_append(cut_all, cut)
        K.bm_append(cut_all, fr)
        fr.free()
        cut.free()
        cut = cut_all
        ucx_h = 11.0
    out = K.boolean_diff(body, cut)
    body.free()
    cut.free()
    return Piece(name, out, [K.box_hull(0, L, 0, T, 0, ucx_h)], (L, T, H))


def build_kerb_corner(name, seed=181):
    pts = []
    for z, ins in ((0.0, 0.0), (38.0, 0.0), (45.0, 4.5)):
        for sx in (0, 1):
            for sy in (0, 1):
                pts.append((ins + sx * (30 - 2 * ins), ins + sy * (30 - 2 * ins), z))
    out = K.hull_from_points([Vector(p) for p in pts], S1)
    K.bevel_all(out, 1.6, 20.0)
    return Piece(name, out, [K.box_hull(0, 30, 0, 30, 0, 45)], (30, 30, 45))


# ==============================================================================================
# registry (table mirrors Docs/MODULAR_KIT.md 4.1)
# ==============================================================================================
# pieces whose mesh does not start at the local origin (arcade BrokenB lives in the bay frame: X 650..1000)
ORIGIN = {"ArcadeBay_1000x60x400_BrokenB": (650.0, 0.0, 0.0)}
def table():
    W = lambda nm, L, H, seed, **kw: (nm, (lambda nm=nm, L=L, H=H, seed=seed, kw=kw: build_wall(PREFIX + nm, L, H, seed, **kw)), (L, kw.get('T', 60), H))
    return [
        W("Wall_400x60x800_A", 400, 800, 11),
        W("Wall_400x60x800_B", 400, 800, 23, vary=True),
        W("Wall_100x60x800", 100, 800, 35),
        W("Wall_400x60x400", 400, 400, 47),
        W("Wall_100x60x400", 100, 400, 59),
        W("Wall_400x60x800_Broken", 400, 800, 71, broken=dict(zmin=450, boxes=3, tooth_at=0)),
        W("Wall_400x60x400_Broken", 400, 400, 83, broken=dict(zmin=150, boxes=3, tooth_at=3)),
        ("Wall_Corner_60x60x800", lambda: build_corner(PREFIX + "Wall_Corner_60x60x800"), (60, 60, 800)),
        ("Buttress_100x150x800", lambda: build_buttress(PREFIX + "Buttress_100x150x800"), (100, 150, 800)),
        ("Doorway_Pointed_400x60x400", lambda: build_doorway(PREFIX + "Doorway_Pointed_400x60x400"), (400, 60, 400)),
        ("Gate_Arch_1200x300x800", lambda: build_gate(PREFIX + "Gate_Arch_1200x300x800"), (1200, 300, 800)),
        ("Window_Lancet_200x60x400_Blind", lambda: build_window_blind(PREFIX + "Window_Lancet_200x60x400_Blind"), (200, 60, 400)),
        ("Trim_Plinth_400x80x60", lambda: build_plinth(PREFIX + "Trim_Plinth_400x80x60", 400, 61), (400, 80, 60)),
        ("Trim_Plinth_100x80x60", lambda: build_plinth(PREFIX + "Trim_Plinth_100x80x60", 100, 67), (100, 80, 60)),
        ("Pier_100x100x500", lambda: build_pier(PREFIX + "Pier_100x100x500"), (100, 100, 500)),
        ("Pier_Broken_100x100x350", lambda: build_pier_broken(PREFIX + "Pier_Broken_100x100x350"), (100, 100, 350)),
        ("Floor_Slab_1000x1000x40", lambda: build_floor(PREFIX + "Floor_Slab_1000x1000x40"), (1000, 1000, 40)),
        ("Rubble_Chunk_S", lambda: build_rubble(PREFIX + "Rubble_Chunk_S", (60, 50, 40), 101, 'S'), (60, 50, 40)),
        ("Rubble_Chunk_M", lambda: build_rubble(PREFIX + "Rubble_Chunk_M", (120, 100, 70), 103, 'M'), (120, 100, 70)),
        ("Rubble_Chunk_L", lambda: build_rubble(PREFIX + "Rubble_Chunk_L", (170, 150, 110), 107, 'L'), (170, 150, 110)),
        ("Rubble_Heap_400x300x130", lambda: build_heap(PREFIX + "Rubble_Heap_400x300x130"), (400, 300, 130)),
        ("Cliff_Slab_500x300x600_A", lambda: build_cliff(PREFIX + "Cliff_Slab_500x300x600_A", 211, 'A'), (500, 300, 600)),
        ("Cliff_Slab_500x300x600_B", lambda: build_cliff(PREFIX + "Cliff_Slab_500x300x600_B", 317, 'B'), (500, 300, 600)),
        ("Cliff_Slab_500x300x300", lambda: build_cliff(PREFIX + "Cliff_Slab_500x300x300", 419, 'C', 500.0, 300.0), (500, 300, 300)),
        ("Cliff_End_200x300x600", lambda: build_cliff(PREFIX + "Cliff_End_200x300x600", 523, 'B', 200.0, 600.0, True), (200, 300, 600)),
        W("Well_Wall_450x50x250", 450, 250, 131, T=50.0, cap=0, broken=dict(zmin=110, boxes=3, tooth_at=1, end_from=0.35, seg=(30, 75))),
        W("Well_Wall_350x50x250", 350, 250, 137, T=50.0, cap=0, broken=dict(zmin=100, boxes=3, tooth_at=3, end_from=0.35, seg=(30, 70))),
        W("Well_Wall_100x50x250", 100, 250, 149, T=50.0, cap=0, broken=dict(zmin=120, boxes=1, tooth_at=0, end_from=0.4, seg=(25, 50))),
        # ---- P7-FIX3 G2a ----
        ("ArcadeBay_1000x60x400", lambda: build_arcade(PREFIX + "ArcadeBay_1000x60x400", None), (1000, 60, 400)),
        ("ArcadeBay_1000x60x400_BrokenA", lambda: build_arcade(PREFIX + "ArcadeBay_1000x60x400_BrokenA", 'A'), (350, 60, 400)),
        ("ArcadeBay_1000x60x400_BrokenB", lambda: build_arcade(PREFIX + "ArcadeBay_1000x60x400_BrokenB", 'B'), (350, 60, 400)),
        ("Kerb_200x30x40", lambda: build_kerb(PREFIX + "Kerb_200x30x40", 200.0, 201), (200, 30, 40)),
        ("Kerb_100x30x40", lambda: build_kerb(PREFIX + "Kerb_100x30x40", 100.0, 207), (100, 30, 40)),
        ("Kerb_Broken_200x30x40", lambda: build_kerb(PREFIX + "Kerb_Broken_200x30x40", 200.0, 211, broken=True), (200, 30, 40)),
        ("KerbCorner_30x30x45", lambda: build_kerb_corner(PREFIX + "KerbCorner_30x30x45"), (30, 30, 45)),
    ]


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SourceArt", "Kit"))
    only = []
    blend_name = None
    i = 0
    while i < len(argv):
        if argv[i] == "--out":
            out = os.path.abspath(argv[i + 1])
            i += 2
        elif argv[i] == "--blend":
            blend_name = argv[i + 1]
            i += 2
        elif argv[i] == "--only":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                only.append(argv[i])
                i += 1
        else:
            i += 1
    return out, only, blend_name


def run():
    out_dir, only, blend_name = parse_args()
    K.setup_scene_units()
    K.get_materials()
    report = []
    pieces = []
    t0 = time.time()
    for nm, fn, dims in table():
        if only and not any(o in nm for o in only):
            continue
        t = time.time()
        pc = fn()
        mn, mx = K.bm_bounds(pc.bm)
        K.finalize(pc.bm, smooth_deg=getattr(pc, 'smooth', 30.0))
        for u in pc.ucx:
            pass
        K.export_piece_fbx(pc.name, pc.bm, pc.ucx, os.path.join(out_dir, "FBX", pc.name + ".fbx"))
        used = sorted({f.material_index for f in pc.bm.faces})
        rec = dict(name=pc.name, min=[round(v, 2) for v in mn], max=[round(v, 2) for v in mx],
                   dims=[round(mx[i] - mn[i], 2) for i in range(3)], spec=list(pc.dims), tris=K.tri_count(pc.bm),
                   slots_used=used, ucx=len(pc.ucx), seconds=round(time.time() - t, 1))
        report.append(rec)
        print("PIECE", json.dumps(rec))
        pieces.append(pc)
    # layout
    x = 0.0
    row_y, row_h = 0.0, 0.0
    for pc in pieces:
        mn, mx = K.bm_bounds(pc.bm)
        w, d = mx[0] - mn[0], mx[1] - mn[1]
        if x + w > 4500.0:
            x, row_y = 0.0, row_y + row_h + 300.0
            row_h = 0.0
        K.add_to_layout(pc.name, pc.bm, pc.ucx, (x - mn[0], row_y - mn[1], 0.0))
        x += w + 150.0
        row_h = max(row_h, d + 400.0)
    os.makedirs(out_dir, exist_ok=True)
    blend = os.path.join(out_dir, blend_name or ("LB_Kit_P0.blend" if not only else "LB_Kit_partial.blend"))
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    rp = os.path.join(out_dir, "kit_report.json")
    if only and os.path.exists(rp):                      # partial rebuild: keep the records of the pieces that were not rebuilt
        with open(rp) as fh:
            old = [r for r in json.load(fh) if r["name"] not in {x["name"] for x in report}]
        report = old + report
        order = [PREFIX + n for n, _f, _d in table()]
        report.sort(key=lambda r: order.index(r["name"]) if r["name"] in order else 999)
    with open(rp, "w") as fh:
        json.dump(report, fh, indent=1)
    print("DONE %d pieces in %.1fs -> %s" % (len(pieces), time.time() - t0, out_dir))


if __name__ == "__main__":
    run()
