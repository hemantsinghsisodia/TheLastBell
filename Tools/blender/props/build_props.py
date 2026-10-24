"""build_props.py -- procedural courtyard props for THE LAST BELL (Blender 5.2, headless).  Plan: P7F-2b.

    blender.exe -b --factory-startup --python Tools/blender/props/build_props.py -- [--out SourceArt/Props/Procedural] [--only NAME ...]

Writes one FBX per mesh (SourceArt/Props/Procedural/<MeshName>.fbx, UCX_ collision in the same file), the review
file LB_Props.blend (un-mirrored authoring versions) and props_report.json (bounds / tris / slots / UCX count).
Everything is seeded (fixed seeds) and reproducible.

Conventions (same as the kit, see Tools/blender/kit/README.md):
  * 1 Blender unit = 1 cm, authoring space == Unreal space (+X, +Y, +Z up); export mirrors Y (ue_y_flip) so the
    result in Unreal is exactly the authored shape.  FBX settings come from kit_lib.export_piece_fbx.
  * PIVOT = BOTTOM-CENTRE for every prop: XY centre of the visual-mesh bounds at the origin, min Z = 0.
  * Vertex colour "Color" = white, UV0 = 1 UV per 100 cm box projection (kit_lib.finalize).
  * Slots are named exactly as in the plan (MAT_Iron, MAT_Stone, MAT_Trim, MAT_Wood, MAT_Rope, MAT_Earth,
    MAT_Charred); only slots that are used are exported.
  * Authoring orientation: gravestone/cross FRONT (relief) faces +Y in Unreal space; the level yaws them.
"""
import json
import math
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "kit")))

import bpy
import bmesh
from mathutils import Vector, Matrix

import kit_lib as K

PREFIX = "SM_LB_Prop_"

# slot name -> viewport colour (review renders only; the real materials are Unreal MIs)
MAT_COLORS = {
    "MAT_Iron": (0.20, 0.17, 0.15, 1.0),
    "MAT_Stone": (0.55, 0.54, 0.51, 1.0),
    "MAT_Trim": (0.60, 0.57, 0.50, 1.0),
    "MAT_Wood": (0.34, 0.24, 0.15, 1.0),
    "MAT_Rope": (0.55, 0.46, 0.30, 1.0),
    "MAT_Earth": (0.24, 0.18, 0.12, 1.0),
    "MAT_Charred": (0.06, 0.055, 0.05, 1.0),
}


def prop_mats(names):
    out = []
    for n in names:
        m = bpy.data.materials.get(n)
        if m is None:
            m = bpy.data.materials.new(n)
            m.diffuse_color = MAT_COLORS[n]
            m.roughness = 0.9
        out.append(m)
    return out


# ----------------------------------------------------------------------------------------------
# 3D value noise (deterministic)
# ----------------------------------------------------------------------------------------------
def _h3(i, j, k, seed):
    s = math.sin(i * 127.1 + j * 311.7 + k * 74.7 + seed * 19.19) * 43758.5453123
    return s - math.floor(s)


def vnoise3(x, y, z, seed=0):
    xi, yi, zi = math.floor(x), math.floor(y), math.floor(z)
    xf, yf, zf = x - xi, y - yi, z - zi
    u, v, w = (t * t * (3 - 2 * t) for t in (xf, yf, zf))
    out = 0.0
    for dx, wx in ((0, 1 - u), (1, u)):
        for dy, wy in ((0, 1 - v), (1, v)):
            for dz, wz in ((0, 1 - w), (1, w)):
                out += _h3(xi + dx, yi + dy, zi + dz, seed) * wx * wy * wz
    return out


def fbm3(x, y, z, seed=0, octaves=3):
    amp, f, tot, norm = 1.0, 1.0, 0.0, 0.0
    for o in range(octaves):
        tot += amp * vnoise3(x * f, y * f, z * f, seed + o * 31)
        norm += amp
        amp *= 0.5
        f *= 2.03
    return tot / norm


# ----------------------------------------------------------------------------------------------
# bmesh utilities
# ----------------------------------------------------------------------------------------------
def tf(bm, m):
    bm.transform(m)
    return bm


def shift(bm, dx=0.0, dy=0.0, dz=0.0):
    return tf(bm, Matrix.Translation((dx, dy, dz)))


def rot(bm, axis, deg):
    return tf(bm, Matrix.Rotation(math.radians(deg), 4, axis))


def join(parts, mat=None):
    out = bmesh.new()
    for p in parts:
        K.bm_append(out, p, mat)
    return out


def bounds(bm):
    return K.bm_bounds(bm)


def densify(bm, max_len, region=None, max_iter=9):
    """Split every edge longer than max_len (optionally only where region(mid_point) is true) until none is."""
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    for _ in range(max_iter):
        edges = []
        for e in bm.edges:
            if e.calc_length() > max_len:
                if region is None or region((e.verts[0].co + e.verts[1].co) * 0.5):
                    edges.append(e)
        if not edges:
            break
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=False)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
    return bm


def bottom_mask(co, n):
    return 0.0 if co.z < 0.02 else 1.0


def weather(bm, seed, amp, mask=bottom_mask, f1=1.0 / 18.0, f2=1.0 / 5.0):
    """Inward displacement along vertex normals by 0..amp cm of two-octave 3D noise (never outward, so the
    nominal dimensions are upper bounds).  mask(co, normal) in 0..1 scales it per vertex."""
    bm.normal_update()
    moves = []
    for v in bm.verts:
        c = v.co
        n = fbm3(c.x * f1, c.y * f1, c.z * f1, seed, 3) * 0.7 + vnoise3(c.x * f2, c.y * f2, c.z * f2, seed + 5) * 0.3
        w = mask(c, v.normal) if mask else 1.0
        moves.append(-v.normal * (amp * n * w))
    for v, d in zip(bm.verts, moves):
        v.co += d
    return bm


def warp(bm, seed, amp, f=1.0 / 22.0, axes=(0, 1, 2)):
    """Low-frequency in-plane wobble (+-amp cm) so silhouettes are not ruler-straight.  Bottom vertices keep z."""
    for v in bm.verts:
        c = v.co
        d = [(fbm3(c.x * f + 11.0 * a, c.y * f + 3.0 * a, c.z * f + 7.0 * a, seed + a, 2) - 0.5) * 2.0 * amp for a in range(3)]
        if 0 in axes:
            c.x += d[0]
        if 1 in axes:
            c.y += d[1] * 0.5
        if 2 in axes and c.z > 0.02:
            c.z += d[2]
    return bm


def fit_bounds(bm, dims):
    """Scale about the XY centre / Z=min so the bounds are exactly dims (only used for small corrections)."""
    mn, mx = bounds(bm)
    cx, cy = (mn[0] + mx[0]) * 0.5, (mn[1] + mx[1]) * 0.5
    sx, sy, sz = dims[0] / (mx[0] - mn[0]), dims[1] / (mx[1] - mn[1]), dims[2] / (mx[2] - mn[2])
    for v in bm.verts:
        v.co.x = cx + (v.co.x - cx) * sx
        v.co.y = cy + (v.co.y - cy) * sy
        v.co.z = mn[2] + (v.co.z - mn[2]) * sz
    return bm


_dummy_mats = []


def _dummy(n):
    while len(_dummy_mats) < n:
        _dummy_mats.append(bpy.data.materials.new("_bm%d" % len(_dummy_mats)))
    return _dummy_mats[:n]


def bool_op(target, other, op, nmat=4):
    """Exact boolean (op = 'DIFFERENCE' | 'UNION') on bmeshes, material indices kept."""
    mats = _dummy(nmat)
    ot = K._tmp_obj(target, "_bt", mats)
    oc = K._tmp_obj(other, "_bc", mats)
    md = ot.modifiers.new("bool", 'BOOLEAN')
    md.operation = op
    md.operand_type = 'OBJECT'
    md.object = oc
    md.solver = 'EXACT'
    md.use_self = True
    md.material_mode = 'INDEX'
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ot.evaluated_get(dg)
    me2 = bpy.data.meshes.new_from_object(ev, depsgraph=dg)
    out = bmesh.new()
    out.from_mesh(me2)
    for ob in (ot, oc):
        me = ob.data
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(me)
    bpy.data.meshes.remove(me2)
    bmesh.ops.dissolve_degenerate(out, dist=1e-4, edges=out.edges)
    return out


def union(parts):
    acc = parts[0]
    for p in parts[1:]:
        acc = bool_op(acc, p, 'UNION')
    return acc


def cut_chips(bm, rng, spots, mat=0):
    """Subtract a small random convex hull ('chip') at every (centre, radius) in spots."""
    for centre, r in spots:
        pts = []
        for _ in range(8):
            v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
            if v.length < 0.35:
                v = v.normalized() * 0.5
            pts.append(Vector(centre) + v * r)
        h = K.hull_from_points(pts, mat, merge_coplanar=False)
        if len(h.faces) >= 4:
            bm = bool_op(bm, h, 'DIFFERENCE')
        else:
            h.free()
    return bm


def torus(R, r, segs_major=24, segs_minor=8, mat=0):
    """Torus around the Z axis (major radius R, tube radius r)."""
    b = bmesh.new()
    rows = []
    for i in range(segs_major):
        a = 2 * math.pi * i / segs_major
        row = []
        for j in range(segs_minor):
            t = 2 * math.pi * j / segs_minor
            rr = R + r * math.cos(t)
            row.append(b.verts.new((rr * math.cos(a), rr * math.sin(a), r * math.sin(t))))
        rows.append(row)
    for i in range(segs_major):
        i2 = (i + 1) % segs_major
        for j in range(segs_minor):
            j2 = (j + 1) % segs_minor
            b.faces.new((rows[i][j], rows[i2][j], rows[i2][j2], rows[i][j2]))
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    K.bm_set_mat(b, mat)
    return b


def revolve_x(profile, segs=16, mat=0):
    """Closed solid of revolution around the X axis from [(x, r), ...]; r == 0 ends become apex points."""
    b = bmesh.new()
    rings = []
    for x, r in profile:
        if r <= 1e-9:
            rings.append(b.verts.new((x, 0.0, 0.0)))
        else:
            rings.append([b.verts.new((x, r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs))) for i in range(segs)])
    first, last = rings[0], rings[-1]
    if isinstance(first, list):
        b.faces.new(first)
    if isinstance(last, list):
        b.faces.new(last)
    for k in range(len(rings) - 1):
        a, c = rings[k], rings[k + 1]
        for i in range(segs):
            j = (i + 1) % segs
            if isinstance(a, list) and isinstance(c, list):
                b.faces.new((a[i], a[j], c[j], c[i]))
            elif isinstance(a, list):
                b.faces.new((a[i], a[j], c))
            else:
                b.faces.new((a, c[j], c[i]))
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    K.bm_set_mat(b, mat)
    return b


def ucx_box(x0, x1, y0, y1, z0, z1):
    return K.box_hull(x0, x1, y0, y1, z0, z1)


# ----------------------------------------------------------------------------------------------
# piece record
# ----------------------------------------------------------------------------------------------
class Piece:
    def __init__(self, name, bm, slots, ucx_design=None, ucx_from_bounds=False, ucx_fixed=None, note=""):
        self.name, self.bm, self.slots = name, bm, slots
        self.ucx_design = ucx_design or []        # boxes/hulls in design coordinates (shifted with the mesh)
        self.ucx_from_bounds = ucx_from_bounds    # one box = final visual bounds
        self.ucx_fixed = ucx_fixed                # (dx, dy, dz): box centred on XY, z 0..dz
        self.note = note
        self.shift = (0.0, 0.0, 0.0)
        self.ucx = []

    def seat(self):
        """Pivot = bottom-centre: shift visual + collision so XY bounds centre = 0 and min Z = 0."""
        mn, mx = bounds(self.bm)
        s = (-(mn[0] + mx[0]) * 0.5, -(mn[1] + mx[1]) * 0.5, -mn[2])
        shift(self.bm, *s)
        for u in self.ucx_design:
            shift(u, *s)
        self.shift = s
        self.ucx = list(self.ucx_design)
        mn, mx = bounds(self.bm)
        if self.ucx_from_bounds:
            self.ucx.append(ucx_box(mn[0], mx[0], mn[1], mx[1], mn[2], mx[2]))
        if self.ucx_fixed:
            dx, dy, dz = self.ucx_fixed
            self.ucx.append(ucx_box(-dx / 2, dx / 2, -dy / 2, dy / 2, 0.0, dz))
        return self


# ==============================================================================================
# KEY
# ==============================================================================================
def build_key():
    """Medieval iron key lying flat, length along X (15.6 cm).  Built with the bow ring plane at z 0..0.7."""
    mat = 0
    parts = []
    BX = -5.4
    zc = 0.35                              # centre height of the bow = shaft axis
    # bow: ring + cross inside
    bow = K.ring(2.6, 1.5, 0.7, 40, mat)
    shift(bow, BX, 0, 0)
    parts.append(bow)
    for ang in (0.0, 90.0):
        bar = K.box(-1.7, 1.7, -0.2, 0.2, 0.1, 0.6, mat, 0.0)
        rot(bar, 'Z', ang)
        shift(bar, BX, 0, 0)
        parts.append(bar)
    # shaft with hemispherical tip (X from -3.2 (embedded in the bow) to 7.6)
    r = 0.42
    prof = [(-3.2, r), (7.6 - r, r)]
    for k in range(1, 5):
        a = math.radians(90.0 * k / 4)
        prof.append((7.6 - r + r * math.sin(a), r * math.cos(a)))
    shaft = revolve_x(prof, 16, mat)
    shift(shaft, 0, 0, zc)
    parts.append(shaft)
    # collars (cylinders along X, r 0.75, len 0.5)
    for x0 in (-2.6, -1.6):
        c = K.cylinder(0.75, 0.5, 16, mat)
        rot(c, 'Y', 90.0)                  # +Z -> +X
        shift(c, x0, 0, zc)
        parts.append(c)
    # bit: block X 4.6..6.8, Y -0.3..-2.2, thickness 0.55 centred on the shaft axis, 2 ward notches cut from the outer edge
    half = 0.275
    nw, nd = 0.35, 0.9
    yo = -2.2
    poly = [(4.6, -0.3), (4.6, yo)]
    for xn in (5.3, 6.1):
        poly += [(xn - nw / 2, yo), (xn - nw / 2, yo + nd), (xn + nw / 2, yo + nd), (xn + nw / 2, yo)]
    poly += [(6.8, yo), (6.8, -0.3)]
    bit = K.prism(poly, 'z', zc - half, zc + half, mat)
    parts.append(bit)
    for p in parts:
        K.bevel_all(p, 0.08, 20.0)
    bm = join(parts)
    shift(bm, 0, 0, 0)
    return Piece(PREFIX + "Key_Chapel", bm, ["MAT_Iron"], ucx_fixed=(17.0, 7.0, 12.0),
                 note="tall UCX 17x7x12 (Z 0..12) deliberately taller than the visual; lies flat, bow at -X, bit toward -Y")


# ==============================================================================================
# KEY LEDGE
# ==============================================================================================
def build_keyledge():
    rng = random.Random(7001)
    mat = 0
    base = K.box(-27, 27, -27, 27, 0, 10, mat, 2.0)
    shaft = K.box(-23, 23, -23, 23, 9.0, 63.0, mat, 0.8)
    slab = K.box(-26, 26, -26, 26, 62.0, 70.0, mat, 1.5)
    bm = union([base, shaft, slab])
    # chipped shaft corners (3..6 cm), plus a few on base and slab
    spots = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for _ in range(2 if (sx, sy) != (1, 1) else 1):
                spots.append(((sx * 23.0, sy * 23.0, rng.uniform(15.0, 55.0)), rng.uniform(3.0, 6.0)))
    spots += [((27 * rng.choice((-1, 1)), 27 * rng.choice((-1, 1)), 4.0), 3.5), ((-26.0, 26.0, 69.0), 3.5), ((26.0, -26.0, 69.0), 3.0)]
    bm = cut_chips(bm, rng, spots, mat)
    densify(bm, 4.0)
    densify(bm, 2.2, region=lambda p: p.z > 60.0)

    def top_flat(co, n):
        return 0.0 if (co.z < 0.02 or (co.z > 69.9 and n.z > 0.5)) else 1.0

    weather(bm, 71, 1.3, top_flat)
    warp(bm, 74, 0.9, axes=(0, 1))
    # worn dip: top face displaced -0.5..-1.0 cm outside the flat 22 x 22 centre (stays exactly at Z 70)
    for v in bm.verts:
        c = v.co
        if c.z > 69.9:
            sdf = max(abs(c.x), abs(c.y)) - 11.0
            if sdf > 0.0:
                w = K.smoothstep(0.0, 5.0, sdf)
                n = fbm3(c.x / 9.0, c.y / 9.0, 3.3, 72, 3)
                c.z -= (0.5 + 0.5 * n) * w
    fit_bounds(bm, (54.0, 54.0, 70.0))
    return Piece(PREFIX + "KeyLedge_50x50x70", bm, ["MAT_Trim"], ucx_fixed=(50.0, 50.0, 70.0),
                 note="flat 22x22 centre exactly at Z 70; UCX 50x50x70 inside the 54x54 base")


# ==============================================================================================
# GRAVESTONES / CROSSES
# ==============================================================================================
def stone_finish(bm, seed, dims=None, dens=4.0, amp=1.0, wob=0.9):
    densify(bm, dens)
    weather(bm, seed, amp)
    warp(bm, seed + 3, wob)
    if dims:
        fit_bounds(bm, dims)
    return bm


def build_gravestone_A():
    rng = random.Random(1101)
    W, D, H, b = 60.0, 14.0, 95.0, 22.0
    N = 28
    pts = [(-30.0, 0.0), (30.0, 0.0), (30.0, H - b)]
    for i in range(1, N):
        t = math.pi * i / N
        pts.append((30.0 * math.cos(t), H - b + b * math.sin(t)))
    pts.append((-30.0, H - b))
    bm = K.prism(pts, 'y', -D / 2, D / 2, 0)
    K.bevel_all(bm, 1.5, 20.0)
    spots = []
    for k, t in enumerate((0.22, 0.55, 0.83)):
        a = math.pi * t
        spots.append(((30.0 * math.cos(a) * 1.0, (D / 2) * (1 if k % 2 == 0 else -1), H - b + b * math.sin(a)), rng.uniform(3.0, 5.5)))
    spots.append(((30.0, -D / 2 * 1.0, 50.0), 3.5))
    spots.append(((-30.0, D / 2, 4.0), 3.5))
    bm = cut_chips(bm, rng, spots, 0)
    stone_finish(bm, 1111, (W, D, H))
    return Piece(PREFIX + "Gravestone_A", bm, ["MAT_Stone"], ucx_from_bounds=True,
                 note="round-top slab, front +Y / back -Y (symmetric)")


def build_gravestone_B():
    rng = random.Random(1202)
    W, D, H = 55.0, 14.0, 85.0
    pts = [(-27.5, 0.0), (27.5, 0.0), (27.5, 65.0), (0.0, H), (-27.5, 65.0)]
    bm = K.prism(pts, 'y', -D / 2, D / 2, 0)
    K.bevel_all(bm, 1.5, 20.0)
    # incised latin cross on the +Y face: 1 cm deep, arms 4 cm wide, 40 tall
    v = K.box(-2.0, 2.0, D / 2 - 1.0, D / 2 + 1.5, 27.0, 67.0, 0, 0.0)
    h = K.box(-13.0, 13.0, D / 2 - 1.0, D / 2 + 1.5, 52.0, 56.0, 0, 0.0)
    cross = bool_op(v, h, 'UNION')
    bm = bool_op(bm, cross, 'DIFFERENCE')
    spots = [((-27.5, D / 2, 65.0), 4.0), ((8.0, -D / 2, 80.0), 3.0), ((27.5, D / 2, 6.0), 3.5), ((-27.5, -D / 2, 40.0), 3.2)]
    bm = cut_chips(bm, rng, spots, 0)
    stone_finish(bm, 1212, (W, D, H), dens=3.0, amp=0.8)
    return Piece(PREFIX + "Gravestone_B", bm, ["MAT_Stone"], ucx_from_bounds=True,
                 note="gabled slab; incised cross relief (1 cm deep) on the +Y face")


def build_gravestone_C():
    rng = random.Random(1303)
    W, D, H = 60.0, 14.0, 45.0
    na, nb = 12, 3
    zs = []
    drop = 0.0
    for i in range(na + 1):
        if rng.random() < 0.28:
            drop += rng.choice((-1, 1)) * rng.uniform(4.0, 9.0)
        drop = max(0.0, min(15.0, drop + rng.uniform(-1.5, 1.5) + (0.9 if i > na * 0.5 else -0.2)))
        col = []
        for j in range(nb + 1):
            tilt = (j / nb) * rng.uniform(1.0, 6.0)          # fracture plane tilts through the thickness
            col.append(H - drop - tilt - rng.uniform(0.0, 1.5))
        zs.append(col)
    zs[2][0] = H                                              # one untouched tooth at full height

    def f(a, bb):
        i = int(round((a + W / 2) / W * na))
        j = int(round((bb + D / 2) / D * nb))
        return zs[i][j]

    bm = K.hf_solid(-W / 2, W / 2, -D / 2, D / 2, f, 0.0, na, nb, ('x', 'y', 'z'), 0, rng)
    K.bevel_all(bm, 0.8, 30.0)
    spots = [((W / 2, D / 2, 0.0), 3.5), ((-W / 2, -D / 2, 12.0), 3.0)]
    bm = cut_chips(bm, rng, spots, 0)
    stone_finish(bm, 1313, (W, D, H))
    return Piece(PREFIX + "Gravestone_C", bm, ["MAT_Stone"], ucx_from_bounds=True,
                 note="broken slab with a faceted fractured top")


def build_gravestone_C_frag():
    rng = random.Random(1304)
    pts = [(-25.0, 6.0), (-14.0, 0.0), (-3.0, 4.0), (8.0, 0.0), (20.0, 3.0), (25.0, 9.0),
           (24.0, 17.0), (17.0, 22.0), (9.0, 30.0), (1.0, 24.0), (-8.0, 28.0), (-17.0, 21.0), (-25.0, 14.0)]
    pts = [(x + (rng.uniform(-0.6, 0.6) if abs(x) < 24.5 else 0.0), max(0.0, z + (rng.uniform(-0.6, 0.6) if 0.5 < z < 29.5 else 0.0))) for x, z in pts]
    bm = K.prism(pts, 'y', -7.0, 7.0, 0)
    K.bevel_all(bm, 0.9, 20.0)
    stone_finish(bm, 1314, (50.0, 14.0, 30.0), dens=3.5, amp=1.1)
    return Piece(PREFIX + "Gravestone_C_Frag", bm, ["MAT_Stone"], ucx_from_bounds=True,
                 note="fallen fragment of Gravestone_C")


def build_gravestone_D():
    rng = random.Random(1405)
    W, D, H = 35.0, 20.0, 45.0
    pts = []
    for k in range(6):                                           # bottom footprint
        a = 2 * math.pi * k / 6 + rng.uniform(-0.25, 0.25)
        pts.append((17.5 * math.cos(a) * rng.uniform(0.85, 1.0), 10.0 * math.sin(a) * rng.uniform(0.85, 1.0), 0.0))
    for k in range(7):                                           # belly
        a = 2 * math.pi * k / 7 + rng.uniform(-0.3, 0.3)
        pts.append((17.5 * math.cos(a) * rng.uniform(0.8, 1.0), 10.0 * math.sin(a) * rng.uniform(0.8, 1.0), rng.uniform(16.0, 24.0)))
    for k in range(4):                                           # lumpy, tapering top
        a = 2 * math.pi * k / 4 + rng.uniform(-0.5, 0.5)
        pts.append((10.0 * math.cos(a) * rng.uniform(0.5, 1.0) + rng.uniform(-3, 3), 6.0 * math.sin(a) * rng.uniform(0.5, 1.0), rng.uniform(38.0, 45.0)))
    pts.append((rng.uniform(-3, 3), rng.uniform(-2, 2), 45.0))
    hull = K.hull_from_points([Vector(p) for p in pts], 0)
    fit_bounds(hull, (W, D, H))
    ucx = hull.copy()                                            # convex collision = the hull itself
    bm = hull
    K.bevel_all(bm, 1.0, 20.0)
    stone_finish(bm, 1415, (W, D, H), dens=3.5, amp=0.8, wob=0.6)
    return Piece(PREFIX + "Gravestone_D", bm, ["MAT_Stone"], ucx_design=[ucx],
                 note="rough irregular hull marker; UCX = the convex hull")


def build_stonecross():
    rng = random.Random(1501)
    base = K.box(-20, 20, -15, 15, 0, 20, 0, 1.5)
    upright = K.box(-9, 9, -9, 9, 19.0, 150.0, 0, 1.5)
    arm = K.box(-27.5, 27.5, -8, 8, 100.0, 116.0, 0, 1.5)
    bm = union([base, upright, arm])
    spots = [((27.5, -8.0, 116.0), 4.5), ((-27.5, 8.0, 100.0), 4.0), ((9.0, 9.0, 150.0), 4.0), ((-9.0, -9.0, 150.0), 3.5),
             ((20.0, 15.0, 20.0), 4.0), ((-20.0, -15.0, 0.0), 3.5), ((9.0, -9.0, 60.0), 3.0)]
    bm = cut_chips(bm, rng, spots, 0)
    stone_finish(bm, 1511, (55.0, 30.0, 150.0), dens=4.0, amp=0.9, wob=0.7)
    ucx = [ucx_box(-20, 20, -15, 15, 0, 20), ucx_box(-9, 9, -9, 9, 20, 150), ucx_box(-27.5, 27.5, -8, 8, 100, 116)]
    return Piece(PREFIX + "StoneCross_A", bm, ["MAT_Stone"], ucx_design=ucx,
                 note="latin cross 55 wide, upright 18x18, base block 40x30x20 (so total Y = 30)")


def beam(x0, x1, y0, y1, z0, z1, seed, mat=0, bevel=0.4, dens=8.0, amp=0.35):
    b = K.box(x0, x1, y0, y1, z0, z1, mat, bevel)
    densify(b, dens)
    weather(b, seed, amp, mask=lambda co, n: 0.0 if (co.z <= z0 + 0.02 and z0 < 1.0) else 1.0, f1=1 / 9.0, f2=1 / 3.0)
    return b


def build_woodcross():
    upright = beam(-4, 4, -3, 3, 0, 120, 1601)
    arm = beam(-27.5, 27.5, -3, 3, 80, 88, 1602)
    wood = join([upright, arm], 0)
    ropes = []
    for z in (78.4, 89.6):                      # rings around the upright, above and below the arm
        t = torus(5.0, 0.6, 24, 8, 1)
        rot(t, 'X', 3.0)
        shift(t, 0, 0, z)
        ropes.append(t)
    t = torus(5.0, 0.6, 24, 8, 1)               # ring around the arm (axis X)
    rot(t, 'Y', 90.0)
    shift(t, 8.0, 0, 84.0)
    ropes.append(t)
    bm = join([wood] + ropes)
    fit_bounds(bm, (55.0, 11.2, 120.0))
    ucx = [ucx_box(-4, 4, -3, 3, 0, 120), ucx_box(-27.5, 27.5, -3, 3, 80, 88)]
    return Piece(PREFIX + "WoodCross_A", bm, ["MAT_Wood", "MAT_Rope"], ucx_design=ucx,
                 note="upright 120, arm 55 at Z 80..88, 3 rope rings (r 5, tube 1.2 cm)")


# ==============================================================================================
# GRAVE MOUND
# ==============================================================================================
def build_mound():
    nth, nr = 56, 14
    H = 22.0
    b = bmesh.new()
    apex = b.verts.new((0, 0, H))
    rows = []
    for k in range(1, nr + 1):
        rho = k / nr
        row = []
        for i in range(nth):
            th = 2 * math.pi * i / nth
            n = fbm3(math.cos(th) * 1.4 + 5, math.sin(th) * 1.4 + 9, 0.5, 21, 3)
            re = rho * (1.0 + 0.10 * (n - 0.5) * (rho ** 2))
            x, y = 100.0 * re * math.cos(th), 45.0 * re * math.sin(th)
            z = 0.0 if k == nr else H * (1 - rho ** 2) ** 1.35 * (0.75 + 0.5 * fbm3(x / 55.0, y / 55.0, 1.7, 22, 3))
            row.append(b.verts.new((x, y, z)))
        rows.append(row)
    for i in range(nth):
        j = (i + 1) % nth
        b.faces.new((apex, rows[0][i], rows[0][j]))
    for k in range(nr - 1):
        for i in range(nth):
            j = (i + 1) % nth
            b.faces.new((rows[k][i], rows[k + 1][i], rows[k + 1][j], rows[k][j]))
    b.faces.new(rows[-1])
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    K.bm_set_mat(b, 0)
    fit_bounds(b, (200.0, 90.0, 22.0))
    return Piece(PREFIX + "GraveMound_A", b, ["MAT_Earth"],
                 note="no collision (walkable); dome with noisy outline and surface")


# ==============================================================================================
# HAND CART  (A2: worn / abandoned)
# ==============================================================================================
def rounded_box(x0, x1, y0, y1, z0, z1, mat, r):
    b = K.box(x0, x1, y0, y1, z0, z1, mat, 0.0)
    if r > 0:
        K.bevel_all(b, r, 20.0, segments=2)
    return b


def sag(bm, amount, x_half=85.0):
    """Bed boards droop by `amount` cm in the middle of the bed (parabola along X)."""
    for v in bm.verts:
        t = 1.0 - (v.co.x / x_half) ** 2
        if t > 0:
            v.co.z -= amount * t
    return bm


def build_cart():
    rng = random.Random(3301)
    wood, iron = 0, 1
    wp = []
    for s in (-1, 1):                                       # shafts (also the side rails of the bed frame)
        wp.append(rounded_box(-85, 195, s * 46 - 4, s * 46 + 4, 65, 72, wood, 1.5))
    for xc in (-81.0, -27.0, 27.0, 81.0):                   # cross beams 8 x 8
        wp.append(rounded_box(xc - 4, xc + 4, -46, 46, 64, 72, wood, 1.5))
    MISSING = 2                                             # one floor plank is gone
    for k in range(6):                                      # 6 planks 15 x 3 with 2 cm gaps, bed top Z 75 (before sag)
        if k == MISSING:
            continue
        y0 = -50.0 + k * 17.0
        xa, xb = -85.0 + rng.uniform(0.0, 3.0), 85.0 - rng.uniform(0.0, 3.0)
        p = K.box(xa, xb, y0, y0 + 15.0, 72, 75, wood, 0.0)
        lng = [e for e in p.edges if e.calc_length() > 100.0]
        bmesh.ops.subdivide_edges(p, edges=lng, cuts=16, use_grid_fill=True)
        K.bevel_all(p, 1.5, 20.0, segments=2)
        sag(p, rng.uniform(1.0, 2.0))
        wp.append(p)
    # side boards 25 high x 2.5 thick: -Y board intact; +Y board cracked in two and missing its rear 40 cm
    wp.append(rounded_box(-85, 85, -50.0, -47.5, 75, 100, wood, 1.5))
    rear = [(-45.0, 75.0), (-39.0, 83.0), (-46.0, 91.0), (-37.0, 100.0), (20.0, 100.0), (15.0, 90.0), (20.5, 80.0), (19.0, 75.0)]
    front = [(22.0, 75.0), (21.0, 88.0), (24.5, 95.0), (21.0, 100.0), (85.0, 100.0), (85.0, 75.0)]
    for poly in (rear, front):
        piece = K.prism(poly, 'y', 47.5, 50.0, wood)
        K.bevel_all(piece, 1.0, 25.0, segments=2)
        wp.append(piece)
    for s in (-1, 1):                                       # axle saddles
        y0, y1 = (42.0, 50.0) if s > 0 else (-50.0, -42.0)
        wp.append(rounded_box(-6, 6, y0, y1, 54, 64.5, wood, 1.0))
    axle = K.cylinder(4.0, 140.0, 12, wood)
    rot(axle, 'X', 90.0)                                    # z -> -y
    shift(axle, 0, 70.0, 50.0)
    wp.append(axle)
    wheels = []
    for s in (-1, 1):
        parts = []
        rim = K.ring(48.8, 42.8, 5.0, 40, wood)
        shift(rim, 0, 0, -2.5)
        tyre = K.ring(50.0, 48.8, 6.0, 40, iron)
        shift(tyre, 0, 0, -3.0)
        hub = K.cylinder(8.0, 20.0, 14, wood)
        shift(hub, 0, 0, -10.0)
        parts += [rim, tyre, hub]
        for k in range(10):
            sp = K.box(6.0, 44.0, -2.0, 2.0, -2.0, 2.0, wood, 0.0)
            rot(sp, 'Z', 36.0 * k + 4.0)
            parts.append(sp)
        w = join(parts)
        rot(w, 'X', 90.0)                                   # wheel axis Z -> Y
        if s > 0:
            rot(w, 'Y', 3.0)                                # loose wheel: tilted 3 degrees on the axle (about the bed's X axis)
        shift(w, 0, s * 60.0, 50.0)
        wheels.append(w)
    bm = join(wp + wheels)
    ucx = [ucx_box(-85, 195, -50, 50, 64, 100), ucx_box(-50, 50, 52, 68, 0, 100), ucx_box(-50, 50, -68, -52, 0, 100)]
    return Piece(PREFIX + "HandCart_A", bm, ["MAT_Wood", "MAT_Iron"], ucx_design=ucx,
                 note="shafts toward +X; axle at design X 0 (bed centre) Z 50; bed top Z 75 when level; +Y side board cracked and missing its rear 40 cm, one plank missing, bed sags 1-2 cm, +Y wheel tilted 3 deg")


# ==============================================================================================
# FIRE PIT  (A2: 13 overlapping flat stones, lumpy ash bed, split / broken logs)
# ==============================================================================================
def log_mesh(rng, length, r_root, r_tip, segs=16, rings=12, mat=1, broken_end=1):
    """Charred log along X: tapered, rough, with longitudinal cracks; one end split/ragged."""
    b = bmesh.new()
    vr = []
    crack = set(rng.sample(range(segs), 3))
    for k in range(rings):
        t = k / (rings - 1)
        x = -length / 2 + length * t
        r = r_root + (r_tip - r_root) * t
        row = []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            rr = r * (0.88 + 0.22 * rng.random())
            if i in crack:
                rr *= 0.82
            rr *= 1.0 + 0.05 * math.sin(t * 9.0 + i)
            xx = x
            if k in (0, rings - 1):
                end_dir = -1 if k == 0 else 1
                if end_dir == broken_end:
                    # ragged / split end: some verts pulled back a lot, others stick out as splinters
                    xx += -end_dir * rng.choice((0.5, 1.5, 3.0, 6.0, 9.0)) * (1.0 if i % 3 else 0.4)
                    rr *= rng.uniform(0.55, 0.95)
                else:
                    xx += -end_dir * rng.uniform(0.0, 1.6)
                    rr *= 0.9
            row.append(b.verts.new((xx, rr * math.cos(a), rr * math.sin(a))))
        vr.append(row)
    for k in range(rings - 1):
        for i in range(segs):
            j = (i + 1) % segs
            b.faces.new((vr[k][i], vr[k][j], vr[k + 1][j], vr[k + 1][i]))
    for row, sgn in ((vr[0], -1), (vr[-1], 1)):             # ragged caps: fan to an off-centre apex
        cx = sum(v.co.x for v in row) / segs + (-sgn * 1.5 if sgn == broken_end else 0.0)
        c = b.verts.new((cx, rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8)))
        for i in range(segs):
            j = (i + 1) % segs
            b.faces.new((row[i], row[j], c))
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    K.bm_set_mat(b, mat)
    return b


def ash_bed(rng, radius=42.5, base=-5.0, mat=1):
    """Irregular lumpy ash mound: flat bottom at `base`, top 3-5 cm above the ground plane (z 0), noisy outline."""
    nth, nr = 40, 8
    b = bmesh.new()
    apex_z = rng.uniform(4.0, 5.0)
    rows = []

    def top_z(x, y, rho):
        return (apex_z * (1 - rho ** 2) ** 0.9 + 0.3) * (0.55 + 0.9 * fbm3(x / 14.0 + 3, y / 14.0 + 8, 0.7, 61, 3)) - 0.5

    apex = b.verts.new((0, 0, top_z(0, 0, 0)))
    for k in range(1, nr + 1):
        rho = k / nr
        row = []
        for i in range(nth):
            th = 2 * math.pi * i / nth
            n = fbm3(math.cos(th) * 1.6 + 7, math.sin(th) * 1.6 + 2, 0.4, 62, 3)
            re = rho * (1.0 + 0.16 * (n - 0.5))
            x, y = radius * re * math.cos(th), radius * re * math.sin(th)
            row.append(b.verts.new((x, y, top_z(x, y, rho) if k < nr else 0.2 * n)))
        rows.append(row)
    for i in range(nth):
        j = (i + 1) % nth
        b.faces.new((apex, rows[0][i], rows[0][j]))
    for k in range(nr - 1):
        for i in range(nth):
            j = (i + 1) % nth
            b.faces.new((rows[k][i], rows[k + 1][i], rows[k + 1][j], rows[k][j]))
    bottom = [b.verts.new((v.co.x, v.co.y, base)) for v in rows[-1]]
    for i in range(nth):
        j = (i + 1) % nth
        b.faces.new((rows[-1][i], rows[-1][j], bottom[j], bottom[i]))
    b.faces.new(bottom)
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    K.bm_set_mat(b, mat)
    return b


def build_firepit():
    rng = random.Random(4402)
    stone, char = 0, 1
    N = 13
    R = 52.0
    stones = []
    for k in range(N):
        ang = 2 * math.pi * k / N + rng.uniform(-0.04, 0.04)
        L = rng.uniform(29.0, 38.0)                           # along the circle
        Wd = rng.uniform(21.0, 28.0)                          # radial width
        Hs = Wd * rng.uniform(0.55, 0.75)                     # flat-ish
        pts = []
        for i in range(6):                                    # footprint, irregular
            a = 2 * math.pi * i / 6 + rng.uniform(-0.35, 0.35)
            pts.append((L / 2 * math.cos(a) * rng.uniform(0.8, 1.0), Wd / 2 * math.sin(a) * rng.uniform(0.8, 1.0), 0.0))
        for i in range(7):                                    # belly
            a = 2 * math.pi * i / 7 + rng.uniform(-0.3, 0.3)
            pts.append((L / 2 * math.cos(a) * rng.uniform(0.92, 1.08), Wd / 2 * math.sin(a) * rng.uniform(0.92, 1.1), Hs * rng.uniform(0.35, 0.65)))
        for i in range(6):                                    # lumpy, rounded top
            a = 2 * math.pi * i / 6 + rng.uniform(-0.5, 0.5)
            pts.append((L / 2 * 0.65 * math.cos(a) * rng.uniform(0.4, 1.0), Wd / 2 * 0.65 * math.sin(a) * rng.uniform(0.4, 1.0), Hs * rng.uniform(0.85, 1.0)))
        s = K.hull_from_points([Vector(p) for p in pts], stone)
        K.bevel_all(s, 1.4, 20.0)
        densify(s, 4.5)
        weather(s, 4420 + k, 1.4, mask=lambda co, n: 1.0)
        warp(s, 4430 + k, 0.8, axes=(0, 1, 2))
        rot(s, 'Z', math.degrees(ang) + 90.0 + rng.uniform(-12.0, 12.0))
        sink = rng.uniform(3.0, 5.0)                          # sunk into the ground (ground plane = design z 0)
        shift(s, R * math.cos(ang), R * math.sin(ang), -sink)
        stones.append(s)
    ring_bm = join(stones)
    ash = ash_bed(rng)
    logs = []
    a0 = rng.uniform(5.0, 25.0)
    # (angle, centre z above the ground plane, offset, tilt, length, root r, tip r)
    specs = [(a0, 4.0 + 6.5, (-2.0, -3.0), 0.0, 62.0, 7.0, 5.8),
             (a0 + 66.0, 16.0, (3.0, 4.0), 8.0, 58.0, 6.8, 5.5),
             (a0 + 126.0, 4.0 + 6.0, (-5.0, 12.0), -3.0, 55.0, 6.4, 5.2)]
    for n, (ang, zc, (ox, oy), tilt, ln, r0, r1) in enumerate(specs):
        lg = log_mesh(rng, ln, r0, r1, broken_end=1 if n != 1 else -1)
        rot(lg, 'Y', tilt)
        rot(lg, 'Z', ang)
        shift(lg, ox, oy, zc)
        logs.append(lg)
    chunks = []
    for _ in range(5):                                        # small charred chunks / embers on the ash
        r = rng.uniform(2.0, 3.6)
        pts = [Vector((rng.uniform(-1, 1) * r, rng.uniform(-1, 1) * r, rng.uniform(0, 1) * r * 0.9)) for _ in range(9)]
        c = K.hull_from_points(pts, char)
        a = rng.uniform(0, 2 * math.pi)
        d = rng.uniform(8.0, 30.0)
        shift(c, d * math.cos(a), d * math.sin(a), 2.0)
        chunks.append(c)
    bm = join([ring_bm, ash] + logs + chunks)
    mn, mx = bounds(ring_bm)
    ucx = [ucx_box(mn[0], mx[0], mn[1], mx[1], mn[2], mx[2])]
    return Piece(PREFIX + "FirePit_A", bm, ["MAT_Stone", "MAT_Charred"], ucx_design=ucx,
                 note="13 overlapping flat stones sunk 3-5 cm below the design ground plane (the plane sits ~5 cm above pivot Z 0 after seating: sink the actor ~4 cm in the level), lumpy ash bed O85, 3 split charred logs + chunks; UCX = box around the stone ring")


# ==============================================================================================
# table
# ==============================================================================================
def table():
    """(mesh name, builder).  Expected values live in verify_props.py."""
    return [
        ("Key_Chapel", build_key),
        ("KeyLedge_50x50x70", build_keyledge),
        ("Gravestone_A", build_gravestone_A),
        ("Gravestone_B", build_gravestone_B),
        ("Gravestone_C", build_gravestone_C),
        ("Gravestone_C_Frag", build_gravestone_C_frag),
        ("Gravestone_D", build_gravestone_D),
        ("StoneCross_A", build_stonecross),
        ("WoodCross_A", build_woodcross),
        ("GraveMound_A", build_mound),
        ("HandCart_A", build_cart),
        ("FirePit_A", build_firepit),
    ]


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SourceArt", "Props", "Procedural"))
    only = []
    i = 0
    while i < len(argv):
        if argv[i] == "--out":
            out = os.path.abspath(argv[i + 1])
            i += 2
        elif argv[i] == "--only":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                only.append(argv[i])
                i += 1
        else:
            i += 1
    return out, only


def run():
    out_dir, only = parse_args()
    K.setup_scene_units()
    report = []
    pieces = []
    t0 = time.time()
    for nm, fn in table():
        if only and not any(o in nm for o in only):
            continue
        t = time.time()
        pc = fn()
        pc.seat()
        mn, mx = bounds(pc.bm)
        used = sorted({f.material_index for f in pc.bm.faces})
        K.finalize(pc.bm, smooth_deg=30.0)
        mats = prop_mats(pc.slots)
        K.export_piece_fbx(pc.name, pc.bm, pc.ucx, os.path.join(out_dir, pc.name + ".fbx"), mats)
        rec = dict(name=pc.name, min=[round(v, 2) for v in mn], max=[round(v, 2) for v in mx],
                   dims=[round(mx[i] - mn[i], 2) for i in range(3)], tris=K.tri_count(pc.bm), slots=pc.slots,
                   slots_used=used, ucx=len(pc.ucx), pivot_shift_applied=[round(v, 3) for v in pc.shift],
                   note=pc.note, seconds=round(time.time() - t, 1))
        report.append(rec)
        print("PIECE", json.dumps(rec))
        pieces.append(pc)
    # review layout (un-mirrored authoring versions)
    x = 0.0
    for pc in pieces:
        mn, mx = bounds(pc.bm)
        w = mx[0] - mn[0]
        K.add_to_layout(pc.name, pc.bm, pc.ucx, (x + w / 2, 0.0, 0.0), prop_mats(pc.slots))
        x += w + 60.0
    os.makedirs(out_dir, exist_ok=True)
    blend = os.path.join(out_dir, "LB_Props.blend" if not only else "LB_Props_partial.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    with open(os.path.join(out_dir, "props_report.json" if not only else "props_report_partial.json"), "w") as fh:
        json.dump(report, fh, indent=1)
    print("DONE %d props in %.1fs -> %s" % (len(pieces), time.time() - t0, out_dir))


if __name__ == "__main__":
    run()
