"""tw_common.py -- shared helpers for the P10-3a bell tower pieces (Blender 5.2, headless).

Re-uses Tools/blender/kit/kit_lib.py (K), build_kit.py (BK) and build_props.py (BP) by import; neither is modified.
Authoring space == Unreal space (1 BU = 1 cm, +X, +Y, +Z up); K.export_piece_fbx mirrors Y on export.
Unlike the kit/props pieces, the tower pieces are built directly in their D1 placement frame (flight frame, face frame, ...)
so there is no automatic re-seating: the pivot is whatever the D1 table says.
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Tools", "blender", "kit"))
sys.path.insert(0, os.path.join(ROOT, "Tools", "blender", "props"))

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402

import kit_lib as K  # noqa: E402
import build_kit as BK  # noqa: E402
import build_props as BP  # noqa: E402

PREFIX = "SM_LB_Tw_"
PROP_PREFIX = "SM_LB_Prop_"

# slot name -> review colour (the real materials are Unreal MIs, D1.5)
COLORS = {
    "MAT_Masonry": (0.42, 0.41, 0.38, 1.0),
    "MAT_Trim": (0.66, 0.63, 0.57, 1.0),
    "MAT_Rubble": (0.27, 0.255, 0.235, 1.0),
    "MAT_Wood": (0.34, 0.24, 0.15, 1.0),
    "MAT_Iron": (0.20, 0.17, 0.15, 1.0),
    "MAT_Slate": (0.16, 0.17, 0.19, 1.0),
    "MAT_Bronze": (0.50, 0.33, 0.16, 1.0),
    "MAT_Rope": (0.55, 0.46, 0.30, 1.0),
    "MAT_Sally": (0.42, 0.14, 0.08, 1.0),
}


def mats(names):
    out = []
    for n in names:
        m = bpy.data.materials.get(n)
        if m is None:
            m = bpy.data.materials.new(n)
            m.diffuse_color = COLORS[n]
            m.roughness = 0.9
        out.append(m)
    return out


class TP:
    """One tower piece: name, bmesh in its D1 frame, slot names, UCX bmeshes, free-text note."""

    def __init__(self, name, bm, slots, ucx=None, note="", keep_uv=False, smooth=30.0, extra=None):
        self.name, self.bm, self.slots = name, bm, slots
        self.ucx = ucx or []
        self.note, self.keep_uv, self.smooth = note, keep_uv, smooth
        self.extra = extra or {}


# ---------------------------------------------------------------------------------------------- bmesh helpers
def join(parts, mat=None):
    out = bmesh.new()
    for p in parts:
        if p is not None:
            K.bm_append(out, p, mat)
    return out


def free_all(*bms):
    for b in bms:
        try:
            b.free()
        except Exception:
            pass


def tf(bm, m):
    bm.transform(m)
    return bm


def shift(bm, dx=0.0, dy=0.0, dz=0.0):
    return tf(bm, Matrix.Translation((dx, dy, dz)))


def rot(bm, axis, deg):
    return tf(bm, Matrix.Rotation(math.radians(deg), 4, axis))


def box(x0, x1, y0, y1, z0, z1, mat, bevel=0.0):
    return K.box(x0, x1, y0, y1, z0, z1, mat, bevel)


def timber(x0, x1, y0, y1, z0, z1, mat=0, bevel=0.5):
    return K.box(x0, x1, y0, y1, z0, z1, mat, bevel)


def prism_xz(poly, y0, y1, mat, bevel=0.0):
    """Prism of an (x, z) polygon extruded along y (poly counter-clockwise or not: normals are recomputed)."""
    p = K.prism(poly, 'y', y0, y1, mat)
    if bevel > 0:
        K.bevel_all(p, bevel, 25.0)
        K.bm_set_mat(p, mat)                      # bmesh bevel gives the chamfer faces slot 0
    return p


def prism_xy(poly, z0, z1, mat, bevel=0.0):
    p = K.prism(poly, 'z', z0, z1, mat)
    if bevel > 0:
        K.bevel_all(p, bevel, 25.0)
        K.bm_set_mat(p, mat)
    return p


def bounds(bm):
    return K.bm_bounds(bm)


def tube(points, radii, sides, mat, cap_start=True, cap_end=True, uv=None):
    """Tube through a polyline (parallel-transported circular frames).  radii: float or list per point.
    uv=(u_scale_around, v_per_cm): writes UV0 (u around 0..1, v = path length / v_len) when given as (1.0, v_len_cm)."""
    pts = [Vector(p) for p in points]
    n = len(pts)
    if not isinstance(radii, (list, tuple)):
        radii = [radii] * n
    b = bmesh.new()
    tang = []
    for i in range(n):
        a = pts[max(i - 1, 0)]
        c = pts[min(i + 1, n - 1)]
        t = (c - a)
        tang.append(t.normalized() if t.length > 1e-9 else Vector((0, 0, 1)))
    ref = Vector((1, 0, 0)) if abs(tang[0].x) < 0.9 else Vector((0, 1, 0))
    nrm = tang[0].cross(ref).normalized()
    rings = []
    for i in range(n):
        if i > 0:
            axis = tang[i - 1].cross(tang[i])
            if axis.length > 1e-9:
                ang = math.asin(min(1.0, axis.length))
                nrm = (Matrix.Rotation(ang, 3, axis.normalized()) @ nrm)
            nrm = (nrm - tang[i] * nrm.dot(tang[i])).normalized()
        bn = tang[i].cross(nrm)
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            ring.append(b.verts.new(pts[i] + (nrm * math.cos(a) + bn * math.sin(a)) * radii[i]))
        rings.append(ring)
    for i in range(n - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            b.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
    if cap_start:
        b.faces.new(rings[0][::-1])
    if cap_end:
        b.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    K.bm_set_mat(b, mat)
    if uv is not None:
        v_len = uv[1]
        layer = b.loops.layers.uv.new("UVMap")
        # path length per ring
        acc = [0.0]
        for i in range(1, n):
            acc.append(acc[-1] + (pts[i] - pts[i - 1]).length)
        ring_of = {}
        for i, ring in enumerate(rings):
            for k, v in enumerate(ring):
                ring_of[v] = (i, k)
        for f in b.faces:
            for l in f.loops:
                if l.vert in ring_of:
                    i, k = ring_of[l.vert]
                    u = k / sides
                    # wrap the seam inside each quad
                    ks = [ring_of[x][1] for x in f.verts if x in ring_of]
                    if ks and max(ks) - min(ks) > sides // 2 and k < sides // 2:
                        u = (k + sides) / sides
                    l[layer].uv = (u, acc[i] / v_len)
    return b


def rod(p0, p1, r, sides, mat, caps=True):
    return tube([p0, p1], r, sides, mat, caps, caps)


def oriented_box(centre, size, rot_euler_deg, mat, bevel=0.0):
    """Box of full size (sx, sy, sz) centred at `centre`, rotated by Euler XYZ degrees about its centre."""
    sx, sy, sz = size
    b = K.box(-sx / 2, sx / 2, -sy / 2, sy / 2, -sz / 2, sz / 2, mat, bevel)
    m = Matrix.Translation(centre) @ Matrix.Rotation(math.radians(rot_euler_deg[2]), 4, 'Z') @ \
        Matrix.Rotation(math.radians(rot_euler_deg[1]), 4, 'Y') @ Matrix.Rotation(math.radians(rot_euler_deg[0]), 4, 'X')
    tf(b, m)
    return b


def beam_between(p0, p1, w, h, mat, up=(0, 0, 1), bevel=0.4):
    """Rectangular timber from p0 to p1 (centre line), cross-section w (horizontal-ish) x h (along `up`)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    ln = d.length
    zax = d.normalized()
    upv = Vector(up)
    xax = upv.cross(zax)
    if xax.length < 1e-6:
        xax = Vector((1, 0, 0)).cross(zax)
    xax.normalize()
    yax = zax.cross(xax)
    b = K.box(-w / 2, w / 2, -h / 2, h / 2, 0.0, ln, mat, bevel)
    m = Matrix((xax, yax, zax)).transposed().to_4x4()
    m.translation = p0
    tf(b, m)
    return b


def finish(tp, smooth=None):
    K.finalize(tp.bm, smooth_deg=tp.smooth if smooth is None else smooth, keep_uv=tp.keep_uv)
    return tp


def uv_cylinder(bm, axis_z=True, circ_cm=100.0, v_cm=100.0):
    """Cylindrical UV0 around the Z axis: u = angle * r / circ_cm style (u = angle/2pi * (2 pi r_ref)/circ_cm), v = z / v_cm."""
    uvl = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        cx = sum(v.co.x for v in f.verts) / len(f.verts)
        cy = sum(v.co.y for v in f.verts) / len(f.verts)
        ac = math.atan2(cy, cx)
        for l in f.loops:
            c = l.vert.co
            a = math.atan2(c.y, c.x)
            d = a - ac
            while d > math.pi:
                d -= 2 * math.pi
            while d < -math.pi:
                d += 2 * math.pi
            a = ac + d
            r_ref = 105.0
            l[uvl].uv = (a * r_ref / circ_cm, c.z / v_cm)
    return bm


def tri_count(bm):
    return K.tri_count(bm)
