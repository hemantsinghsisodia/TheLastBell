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
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "kit")))

import bpy
import bmesh
from mathutils import Vector, Matrix

import kit_lib as K

PREFIX = "SM_LB_Prop_"
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))

# slot name -> viewport colour (review renders only; the real materials are Unreal MIs)
MAT_COLORS = {
    "MAT_Iron": (0.20, 0.17, 0.15, 1.0),
    "MAT_Stone": (0.55, 0.54, 0.51, 1.0),
    "MAT_Trim": (0.60, 0.57, 0.50, 1.0),
    "MAT_Wood": (0.34, 0.24, 0.15, 1.0),
    "MAT_Rope": (0.55, 0.46, 0.30, 1.0),
    "MAT_Earth": (0.24, 0.18, 0.12, 1.0),
    "MAT_Charred": (0.06, 0.055, 0.05, 1.0),
    "MAT_Water": (0.015, 0.025, 0.03, 1.0),
    "MAT_Bark": (0.30, 0.27, 0.23, 1.0),
    "MAT_Leaf": (0.20, 0.34, 0.12, 1.0),
    "MAT_Stem": (0.20, 0.15, 0.10, 1.0),
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
        self.keep_uv = False                      # custom UV0 (ivy atlas cells, tree bark): finalize must not overwrite it
        self.seat_mode = "centre"                 # "centre" = bottom-centre; "wall" = X centre, back plane at Y 0, min Z 0
        self.smooth = 30.0
        self.subdir = ""
        self.textures = []                        # (ambientCG id, map name) copied next to the FBX

    def seat(self):
        """Pivot = bottom-centre: shift visual + collision so XY bounds centre = 0 and min Z = 0."""
        mn, mx = bounds(self.bm)
        s = (-(mn[0] + mx[0]) * 0.5, -(mn[1] + mx[1]) * 0.5, -mn[2])
        if self.seat_mode == "wall":
            s = (s[0], -mn[1], s[2])
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
# P7-FIX3 G2a -- well-head, timber set, earth patch
# ==============================================================================================
def oct_pt(rho, t):
    """Point on the regular octagon (corners on the +X/+Y axes, circumradius rho) at side parameter t (corner k at t = k)."""
    i = int(math.floor(t))
    f = t - i
    a0, a1 = math.radians(45.0 * (i % 8)), math.radians(45.0 * ((i + 1) % 8))
    return ((1 - f) * rho * math.cos(a0) + f * rho * math.cos(a1), (1 - f) * rho * math.sin(a0) + f * rho * math.sin(a1))


def oct_block(r_in, r_out, t0, t1, z0, z1, mat=0, bevel=1.5):
    """Stone block of the octagonal ring between side parameters t0..t1 (may bend around corners), z0..z1."""
    ks = [k for k in range(int(math.floor(t0)) + 1, int(math.ceil(t1))) if t0 + 1e-6 < k < t1 - 1e-6]
    outer = [oct_pt(r_out, t0)] + [oct_pt(r_out, k) for k in ks] + [oct_pt(r_out, t1)]
    inner = [oct_pt(r_in, t0)] + [oct_pt(r_in, k) for k in ks] + [oct_pt(r_in, t1)]
    b = K.prism(outer + inner[::-1], 'z', z0, z1, mat)
    K.bevel_all(b, bevel, 25.0)
    return b


def subdiv_long(bm, seg, min_len=None):
    """Cut every edge longer than 1.5 x seg into pieces of about `seg` (quad strips along long beams, no sliver triangles)."""
    min_len = seg * 1.5 if min_len is None else min_len
    groups = {}
    for e in bm.edges:
        ln = e.calc_length()
        if ln > min_len:
            groups.setdefault(int(round(ln / seg)) - 1, []).append(e)
    for cuts, edges in groups.items():
        live = [e for e in edges if e.is_valid]
        if live and cuts > 0:
            bmesh.ops.subdivide_edges(bm, edges=live, cuts=cuts, use_grid_fill=True)
    return bm


def lbeam(x0, x1, y0, y1, z0, z1, seed, mat=0, bevel=0.5, seg=25.0, amp=0.35):
    """Weathered long timber with a low vertex count: chamfered box, long edges cut into ~seg strips, inward wobble."""
    b = K.box(x0, x1, y0, y1, z0, z1, mat, bevel)
    subdiv_long(b, seg)
    bmesh.ops.triangulate(b, faces=b.faces[:])
    weather(b, seed, amp, mask=lambda co, n: 0.0 if (co.z <= z0 + 0.02 and z0 < 1.0) else 1.0, f1=1 / 70.0, f2=1 / 22.0)
    return b


def beam_cyl(r, length, seed, mat=0, segs=14, seg=25.0):
    """Weathered cylinder along +Z, z in [0, length]."""
    c = K.cylinder(r, length, segs, mat)
    subdiv_long(c, seg)
    bmesh.ops.triangulate(c, faces=c.faces[:])
    weather(c, seed, 0.3, mask=lambda co, n: 1.0, f1=1 / 70.0, f2=1 / 22.0)
    return c


def build_wellhead():
    rng = random.Random(5101)
    ST, WD, RP, IR, WT = 0, 1, 2, 3, 4                       # slot indices: Stone, Wood, Rope, Iron, Water
    R_COP_OUT, R_COP_IN, R_BODY_OUT, R_BODY_IN = 130.0, 90.0, 124.0, 96.0
    H_BODY, H_TOT, ZM = 73.0, 85.0, 36.5
    parts = []

    def chip(bm, n, r_out, z_top):
        spots = []
        for _ in range(n):
            px, py = oct_pt(r_out, rng.uniform(0, 8))
            spots.append(((px, py, z_top - rng.uniform(0.0, 2.0)), rng.uniform(5.5, 11.0)))
        return cut_chips(bm, rng, spots, ST)

    # two courses of stone blocks: lower = one block per side, upper = blocks centred on the corners (staggered joints)
    for i in range(8):
        b = oct_block(R_BODY_IN, R_BODY_OUT, i, i + 1, 0.0, ZM, ST)
        if i in (0, 3, 5):
            b = chip(b, 2, R_BODY_OUT, ZM)
        parts.append(b)
    for i in range(8):
        b = oct_block(R_BODY_IN, R_BODY_OUT, i - 0.5, i + 0.5, ZM, H_BODY, ST)
        if i in (1, 4, 6, 7):
            b = chip(b, 2, R_BODY_OUT, ZM)
        if i == 3:                                           # one big bite out of the upper course (inner top edge)
            px, py = oct_pt(R_BODY_IN + 4.0, 3.0)
            b = cut_chips(b, rng, [((px, py, H_BODY), 15.0)], ST)
        parts.append(b)
    # coping: one slab per side, two segments missing (sides 2 and 6), chips on the others
    for i in range(8):
        if i in (2, 6):
            continue
        b = oct_block(R_COP_IN, R_COP_OUT, i, i + 1, H_BODY, H_TOT, ST, 1.4)
        if i in (0, 3, 5, 7):
            b = chip(b, 3, R_COP_OUT, H_TOT)
        parts.append(b)
    for k, p_ in enumerate(parts):                           # weather every block (inward only) and settle it a little
        densify(p_, 16.0)
        weather(p_, 5200 + k, 1.8, mask=lambda co, n: 0.0 if co.z < 0.02 else 1.0, f1=1 / 34.0, f2=1 / 10.0)
        rot(p_, 'Z', rng.uniform(-0.9, 0.9))
        shift(p_, rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), 0.0)
        bmesh.ops.triangulate(p_, faces=p_.faces[:])
    # dark water slab inside the ring, top at Z 20
    parts.append(K.prism([oct_pt(95.5, k) for k in range(8)], 'z', 18.0, 20.0, WT))
    # timber winch: two posts outside the ring (X +-152), drum O20 x 200 over the well at Z 210, iron axle + 2 cranks, rope
    PX = 152.0
    for sgn, sd in ((1, 5111), (-1, 5112)):
        parts.append(lbeam(sgn * PX - 9, sgn * PX + 9, -9, 9, 0, 230.0, sd, WD, 0.7, 30.0, 0.4))
    drum = beam_cyl(10.0, 200.0, 5113, WD)
    rot(drum, 'Y', 90.0)                                    # +Z -> +X
    shift(drum, -100.0, 0.0, 210.0)
    parts.append(drum)
    axle = K.cylinder(3.2, 332.0, 10, IR)
    rot(axle, 'Y', 90.0)
    shift(axle, -166.0, 0.0, 210.0)
    parts.append(axle)
    for x in (-62.0, -56.0, -50.0, -44.0, -38.0, -32.0):    # rope turns on the drum
        t = torus(11.4, 1.2, 14, 5, RP)
        rot(t, 'Y', 90.0)
        shift(t, x, 0.0, 210.0)
        parts.append(t)
    for side, ang in ((1, -22.0), (-1, 22.0)):              # cranks outside the posts, both ends, opposite phase
        arm = K.box(0.0, 4.0, -2.5, 30.0, -2.0, 2.0, IR, 0.5)
        hdl = K.cylinder(2.2, 17.0, 8, IR)
        rot(hdl, 'Y', 90.0)
        shift(hdl, 0.0, 28.0, 0.0)
        grp = join([arm, hdl])
        shift(grp, 162.0, 0.0, 0.0)
        rot(grp, 'X', ang)
        if side < 0:
            tf(grp, Matrix.Scale(-1.0, 4, (1, 0, 0)))        # mirror to -X ...
            bmesh.ops.reverse_faces(grp, faces=grp.faces)
            rot(grp, 'X', 180.0)                             # ... then 180 deg about X (arm toward -Y)
        shift(grp, 0.0, 0.0, 210.0)
        parts.append(grp)
    rope = K.cylinder(1.2, 192.0, 6, RP)                    # hangs from the drum front into the water
    shift(rope, -18.0, 11.4, 18.0)
    parts.append(rope)
    bm = join(parts)
    ucx = []
    for i in range(8):                                      # 8 convex hulls, one per ring side
        pts = []
        for (rho, t) in ((R_COP_OUT - 3.0, i), (R_COP_OUT - 3.0, i + 1), (R_COP_IN + 1.0, i + 1), (R_COP_IN + 1.0, i)):
            x, y = oct_pt(rho, t)
            pts += [Vector((x, y, 0.0)), Vector((x, y, H_TOT))]
        ucx.append(K.hull_from_points(pts, 0))
    ucx.append(ucx_box(PX - 9, PX + 9, -9, 9, 0.0, 230.0))
    ucx.append(ucx_box(-PX - 9, -PX + 9, -9, 9, 0.0, 230.0))
    return Piece(PREFIX + "WellHead_A", bm, ["MAT_Stone", "MAT_Wood", "MAT_Rope", "MAT_Iron", "MAT_Water"], ucx_design=ucx,
                 note="octagonal well curb O260 (corners on the axes), 2 courses + coping (2 segments missing), dark water slab Z 18..20; "
                      "timber winch posts at X +-152 (outside the ring), drum O20 x 200 at Z 210, iron axle + 2 cranks, rope; UCX 8 ring sides + 2 posts")


def build_timber_post():
    raw = K.box(-10, 10, -10, 10, 0, 420, 0, 0.0)
    notch = K.box(-11, 11, -7.6, 7.6, 413.0, 421.0, 0, 0.0)
    b = bool_op(raw, notch, 'DIFFERENCE', 1)
    K.bevel_all(b, 0.8, 25.0)
    subdiv_long(b, 30.0)
    bmesh.ops.triangulate(b, faces=b.faces[:])
    weather(b, 8101, 0.5, mask=lambda co, n: 0.0 if co.z <= 0.02 else 1.0, f1=1 / 70.0, f2=1 / 22.0)
    fit_bounds(b, (20.0, 20.0, 420.0))
    return Piece(PREFIX + "TimberPost_20x20x420", b, ["MAT_Wood"], ucx_from_bounds=True,
                 note="weathered square post, saddle notch 15 wide x 7 deep at the top for the purlin; UCX = bounds")


def build_purlin():
    b = lbeam(-7.5, 7.5, -7.5, 7.5, 0, 1000.0, 8201, 0, 0.6, 28.0, 0.45)
    for v in b.verts:                                       # slight bow so it is not ruler straight
        v.co.x += 1.8 * math.sin(math.pi * v.co.z / 1000.0)
    fit_bounds(b, (15.0, 15.0, 1000.0))
    return Piece(PREFIX + "Purlin_15x15x1000", b, ["MAT_Wood"], note="authored upright (length along Z); the level lays it horizontal; no collision")


def build_rafter():
    b = lbeam(-7.5, 7.5, -5.0, 5.0, 0, 420.0, 8301, 0, 0.5, 30.0, 0.4)
    fit_bounds(b, (15.0, 10.0, 420.0))
    return Piece(PREFIX + "Rafter_15x10x420", b, ["MAT_Wood"], note="authored upright (length along Z); no collision")


def build_rafter_broken():
    rng = random.Random(8401)
    main = K.prism([(-7.5, 0.0), (7.5, 0.0), (7.5, 226.0), (-7.5, 238.0)], 'y', -5.0, 5.0, 0)
    K.bevel_all(main, 0.5, 25.0)
    subdiv_long(main, 30.0)
    bmesh.ops.triangulate(main, faces=main.faces[:])
    weather(main, 8402, 0.4, mask=lambda co, n: 0.0 if co.z <= 0.02 else 1.0, f1=1 / 70.0, f2=1 / 22.0)
    parts = [main]
    tops = [247.0, 238.0, 260.0, 243.0, 252.0]
    for k in range(5):                                      # splinters: thin slivers with slanted tips
        x0, x1 = -7.5 + 3.0 * k, -7.5 + 3.0 * (k + 1)
        poly = [(x0 + 0.1, 224.0 + 2.0 * k), (x1 - 0.1, 224.0 + 2.0 * k), (x1 - 0.1, tops[k] + rng.uniform(-6, 2)), (x0 + 0.1, tops[k])]
        parts.append(K.prism(poly, 'y', -5.0 + rng.uniform(0.0, 2.5), 5.0 - rng.uniform(0.0, 2.5), 0))
    bm = join(parts)
    fit_bounds(bm, (15.0, 10.0, 260.0))
    return Piece(PREFIX + "Rafter_Broken_15x10x260", bm, ["MAT_Wood"], note="snapped rafter: slanted break + 5 splinters; no collision")


def plank_board(y0, y1, xa, xb, thick, rng, ragged_l, ragged_r):
    """One board (XY outline with jagged ends) extruded to `thick`."""
    ww = y1 - y0
    lx = [xa + (rng.uniform(0.0, 7.0) if ragged_l else 0.0) for _ in range(4)]
    rx = [xb - (rng.uniform(0.0, 7.0) if ragged_r else 0.0) for _ in range(4)]
    poly = [(lx[0], y0), (rx[0], y0), (rx[1], y0 + ww * 0.33), (rx[2], y0 + ww * 0.66), (rx[3], y1),
            (lx[3], y1), (lx[2], y0 + ww * 0.66), (lx[1], y0 + ww * 0.33)]
    b = K.prism(poly, 'z', 0.0, thick, 0)
    K.bevel_all(b, 0.4, 25.0)
    return b


def build_planks(broken):
    rng = random.Random(8601 if broken else 8501)
    n = 6
    gaps = [rng.uniform(1.0, 2.0) for _ in range(n - 1)]
    avail = 100.0 - sum(gaps)
    ws = [rng.uniform(0.9, 1.1) for _ in range(n)]
    ws = [w * avail / sum(ws) for w in ws]
    y = 0.0
    parts = []
    for i in range(n):
        y0, y1 = y, y + ws[i]
        y = y1 + (gaps[i] if i < n - 1 else 0.0)
        xa, xb = 0.0, 200.0
        rl, rr = (rng.random() < 0.6 and i not in (0, 5)), (rng.random() < 0.6 and i not in (0, 5))
        if broken:
            if i in (1, 4):
                continue                                    # whole boards gone
            if i == 2:
                xb, rr = rng.uniform(95.0, 120.0), True     # snapped short
            if i == 3:
                xa, rl = rng.uniform(60.0, 85.0), True
        thick = 4.0 if i in (0, 3) else rng.uniform(3.4, 3.9)
        b = plank_board(y0, y1, xa, xb, thick, rng, rl, rr)
        tilt = rng.uniform(-0.7, 0.7)
        for v in b.verts:                                   # warped boards
            v.co.z += tilt * (v.co.x - 100.0) / 100.0 * 0.5 + 0.25 * math.sin(v.co.x / 31.0 + i)
        parts.append(b)
    bm = join(parts)
    zmin = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= zmin
    fit_bounds(bm, (200.0, 100.0, 4.0))
    nm = "RoofPlanks_Broken_200x100x4" if broken else "RoofPlanks_200x100x4"
    return Piece(PREFIX + nm, bm, ["MAT_Wood"],
                 note="boards 1-2 cm apart, ragged ends, %s; no collision" % ("2 boards gone, 2 snapped short" if broken else "6 boards"))


def build_earthpatch():
    N, S = 40, 400.0
    b = bmesh.new()
    raw = {(i, j): fbm3(S * i / N / 70.0 + 3.0, S * j / N / 70.0 + 9.0, 1.3, 87, 3) for i in range(N + 1) for j in range(N + 1)}
    lo, hi = min(raw.values()), max(raw.values())
    g = {}
    for i in range(N + 1):
        for j in range(N + 1):
            x, y = S * i / N, S * j / N
            h = 8.0 + 7.0 * (raw[(i, j)] - lo) / (hi - lo)
            h *= K.smoothstep(0.0, 40.0, min(x, y, S - x, S - y))
            g[(i, j)] = b.verts.new((x, y, h))
    for i in range(N):
        for j in range(N):
            a, c, d, e = g[(i, j)], g[(i + 1, j)], g[(i + 1, j + 1)], g[(i, j + 1)]
            if (i + j) % 2 == 0:
                b.faces.new((a, c, d))
                b.faces.new((a, d, e))
            else:
                b.faces.new((a, c, e))
                b.faces.new((c, d, e))
    loop = [g[(i, 0)] for i in range(N)] + [g[(N, j)] for j in range(N)] + [g[(i, N)] for i in range(N, 0, -1)] + [g[(0, j)] for j in range(N, 0, -1)]
    bottom = b.faces.new(loop[::-1])
    bmesh.ops.triangulate(b, faces=[bottom])
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    K.bm_set_mat(b, 0)
    return Piece(PREFIX + "EarthPatch_400x400x15", b, ["MAT_Earth"], ucx_design=[ucx_box(0, S, 0, S, 0, 8.0)],
                 note="noisy earth top 8-15 cm (edges taper to 0 over 40 cm), flat bottom; UCX 400x400x8")




# ==============================================================================================
# P7-FIX3 G2a -- ivy cards (atlas UVs) and the procedural dead tree
# ==============================================================================================
# leaf cells of the ambientCG atlases (pixel rects x0, y0, x1, y1, origin top-left, 2048 x 2048), found from the Opacity maps
IVY_ATLAS = {
    "Green": dict(src="LeafSet017", orient="up", cells=[(103, 33, 779, 669), (1271, 109, 1788, 648), (130, 756, 830, 1389),
                                                      (1283, 809, 1863, 1305), (92, 1420, 882, 2023), (1211, 1415, 1841, 2001)]),
    # oak leaves lie horizontally (petiole to the right) -> the quad's up axis maps to atlas-left
    "Dead": dict(src="LeafSet030", orient="left", cells=[(31, 92, 503, 380), (530, 125, 1011, 412), (1055, 120, 1517, 431),
                                                         (1550, 111, 2015, 416), (50, 1162, 481, 1407), (517, 1151, 1010, 1407),
                                                         (1037, 1137, 1527, 1399), (1571, 1178, 1994, 1399), (41, 1688, 465, 1910),
                                                         (580, 1667, 968, 1903), (1054, 1671, 1523, 1904), (1550, 1675, 2020, 1919)]),
}
IVY_TEX = {"LeafSet017": ["Color", "Opacity", "Roughness", "NormalGL"], "LeafSet030": ["Color", "Opacity", "Roughness", "NormalGL"]}


def _uvl(bm):
    return bm.loops.layers.uv.verify()


def add_tube(bm, pts, radii, sides, mat, uvscale=50.0, cap_start=True, cap_end=True, uvoff=(0.0, 0.0)):
    """Tapered tube along a polyline (Vector list); UV = (around / uvscale, along / uvscale)."""
    uv = _uvl(bm)
    rings = []
    s_acc = [0.0]
    for i in range(1, len(pts)):
        s_acc.append(s_acc[-1] + (pts[i] - pts[i - 1]).length)
    prev_x = None
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])
        if d.length < 1e-6:
            d = Vector((0, 0, 1))
        d.normalize()
        ref = Vector((0, 1, 0)) if abs(d.y) < 0.9 else Vector((1, 0, 0))
        if prev_x is not None:                       # parallel transport
            ref = prev_x
        x = (ref - d * ref.dot(d))
        if x.length < 1e-6:
            x = d.orthogonal()
        x.normalize()
        y = d.cross(x)
        prev_x = x
        rr = radii[i]
        rings.append([bm.verts.new(p + (x * math.cos(2 * math.pi * k / sides) + y * math.sin(2 * math.pi * k / sides)) * rr) for k in range(sides)])
    for i in range(len(pts) - 1):
        r_ = max(radii[i], radii[i + 1])
        cu = 2 * math.pi * r_ / uvscale
        for k in range(sides):
            k2 = (k + 1) % sides
            quad = (rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k])
            f = bm.faces.new(quad)
            f.material_index = mat
            uvs = ((cu * k / sides, s_acc[i]), (cu * (k + 1) / sides, s_acc[i]), (cu * (k + 1) / sides, s_acc[i + 1]), (cu * k / sides, s_acc[i + 1]))
            for l, (uu, vv) in zip(f.loops, uvs):
                l[uv].uv = (uvoff[0] + uu, uvoff[1] + vv / uvscale)
    for flag, ring, rev in ((cap_start, rings[0], True), (cap_end, rings[-1], False)):
        if flag:
            f = bm.faces.new(ring[::-1] if rev else ring)
            f.material_index = mat
            for l in f.loops:
                l[uv].uv = (uvoff[0], uvoff[1])
    return bm


def add_leaf(bm, base, phi, size, cell, orient, pitch, rng, atlas_px=2048.0, mat=0):
    """3x3 grid leaf (folded along the midrib) at `base`, tip direction angle phi in the XZ plane (0 = +Z, + toward +X)."""
    uv = _uvl(bm)
    x0, y0, x1, y1 = cell
    cw, ch = x1 - x0, y1 - y0
    aspect = (cw / ch) if orient == "up" else (ch / cw)           # width / length of the quad
    if aspect >= 1.0:
        w, L = size, size / aspect
    else:
        L, w = size, size * aspect
    U2 = Vector((math.sin(phi), 0.0, math.cos(phi)))
    R2 = Vector((math.cos(phi), 0.0, -math.sin(phi)))
    N = Vector((0.0, 1.0, 0.0))
    ca, sa = math.cos(pitch), math.sin(pitch)
    Ua = U2 * ca + N * sa
    Nl = N * ca - U2 * sa
    droop = rng.uniform(0.0, 0.18)
    grid = []
    for j in range(3):
        t = j / 2.0
        row = []
        for i in range(3):
            s = (i / 2.0) - 0.5
            p = base + Ua * (t * L) + R2 * (s * w) + Nl * (0.14 * w * (1.0 - abs(2 * s)) - droop * L * t * t)
            row.append(bm.verts.new(p))
        grid.append(row)

    def uv_of(t, s):
        if orient == "up":
            px, py = x0 + (s + 0.5) * cw, y1 - t * ch                  # t 0 = petiole (bottom of the cell)
        else:
            px, py = x1 - t * cw, y1 - (s + 0.5) * ch                  # petiole at the right; quad right = atlas top
        return (px / atlas_px, 1.0 - py / atlas_px)

    for j in range(2):
        for i in range(2):
            # winding (i,j) (i,j+1) (i+1,j+1) (i+1,j): normal = +Y side (outward from the wall)
            f = bm.faces.new((grid[j][i], grid[j + 1][i], grid[j + 1][i + 1], grid[j][i + 1]))
            f.material_index = mat
            corners = ((j, i), (j + 1, i), (j + 1, i + 1), (j, i + 1))
            for l, (jj, ii) in zip(f.loops, corners):
                l[uv].uv = uv_of(jj / 2.0, ii / 2.0 - 0.5)
    return bm


def build_ivy(name, W, H, kind, shape, seed):
    """Ivy card.  shape: climb | patch | hang | creep.  kind: Green | Dead.  Back at Y 0 (wall side), leaves up to ~25 cm out."""
    rng = random.Random(seed)
    atlas = IVY_ATLAS[kind]
    bm = bmesh.new()
    _uvl(bm)
    LEAF, STEM = 0, 1
    cfg = dict(climb=dict(step=12.0, gap=12.5, depth=2, pb=0.17, margin=(12.0, 12.0), wander=0.12),
               patch=dict(step=9.0, gap=10.0, depth=2, pb=0.20, margin=(12.0, 12.0), wander=0.30),
               hang=dict(step=14.0, gap=15.0, depth=1, pb=0.07, margin=(12.0, 8.0), wander=0.05),
               creep=dict(step=10.0, gap=10.5, depth=2, pb=0.2, margin=(12.0, 12.0), wander=0.10))[shape]
    hx, hz = W / 2.0 - cfg['margin'][0], H - cfg['margin'][1]

    def inside(x, z):
        if shape == "patch":
            return ((x / hx) ** 2 + ((z - H / 2.0) / (H / 2.0 - cfg['margin'][1])) ** 2) <= 1.0
        return abs(x) <= hx and 2.0 <= z <= hz

    polylines = []                         # (points 3D, depth)
    leaves = []                            # (base, phi, size, depth)

    def grow(p, a, length, depth, target, pull):
        pts = [Vector((p[0], 1.8 + rng.uniform(0.0, 1.2), p[1]))]
        n = max(2, int(length / cfg['step']))
        x, z = p
        since = rng.uniform(0.0, cfg['gap'])
        for _ in range(n):
            a += rng.gauss(0.0, cfg['wander']) + pull * math.sin(target - a)
            x2, z2 = x + math.sin(a) * cfg['step'], z + math.cos(a) * cfg['step']
            if not inside(x2, z2):
                break
            x, z = x2, z2
            y = 1.8 + rng.uniform(0.0, 2.4)
            pts.append(Vector((x, y, z)))
            since += cfg['step']
            if since >= cfg['gap']:
                since = 0.0
                for sgn in (-1, 1):
                    if rng.random() < 0.8:
                        ph = a + sgn * rng.uniform(0.35, 1.15) + rng.uniform(-0.4, 0.4)
                        leaves.append((Vector((x, y, z)), ph, rng.uniform(9.0, 16.0) * (1.0 - 0.12 * depth), depth))
            if depth < cfg['depth'] and rng.random() < cfg['pb']:
                da = rng.choice((-1, 1)) * rng.uniform(0.6, 1.2)
                tgt = target if shape in ("climb", "creep", "hang") else a + da
                grow((x, z), a + da, length * rng.uniform(0.3, 0.6), depth + 1, tgt, pull)
        if len(pts) >= 2:
            leaves.append((pts[-1].copy(), a + rng.uniform(-0.3, 0.3), rng.uniform(9.0, 14.0), depth))
            polylines.append((pts, depth))

    if shape == "climb":
        for k in range(6):
            x = -W * 0.4 + W * 0.8 * k / 5.0 + rng.uniform(-12, 12)
            grow((x, 2.0), rng.uniform(-0.2, 0.2), H * rng.uniform(0.95, 1.4), 0, 0.0, 0.07)
    elif shape == "patch":
        for k in range(16):
            ang = rng.uniform(0, 2 * math.pi)
            rad = rng.uniform(0.0, 0.55)
            x, z = rad * hx * math.cos(ang), H / 2.0 + rad * (H / 2.0) * math.sin(ang)
            a0 = rng.uniform(0, 2 * math.pi)
            grow((x, z), a0, rng.uniform(90, 190), 0, a0, 0.0)
    elif shape == "hang":
        for k in range(9):
            x = -W * 0.43 + W * 0.86 * k / 8.0 + rng.uniform(-5, 5)
            ln = H * (0.97 if k == 4 else rng.uniform(0.35, 0.92))
            grow((x, H - 3.0), math.pi + rng.uniform(-0.1, 0.1), ln, 0, math.pi, 0.08)
    else:                                  # creep
        for zz, ang in ((6.0, math.pi / 2), (16.0, math.pi / 2 + 0.1), (30.0, math.pi / 2 - 0.1)):
            grow((-W * 0.46, zz), ang, W * 1.0, 0, 0.0 if zz > 20 else math.pi / 2, 0.02)
            grow((W * 0.46, zz), -ang, W * 1.0, 0, 0.0 if zz > 20 else -math.pi / 2, 0.02)
        for k in range(8):
            x = -W * 0.4 + W * 0.8 * k / 7.0 + rng.uniform(-10, 10)
            grow((x, 4.0), rng.uniform(-0.35, 0.35), H * rng.uniform(0.5, 1.0), 1, 0.0, 0.12)
    for pts, depth in polylines:
        n = len(pts)
        r0 = (1.5, 1.1, 0.8)[min(depth, 2)] * (1.3 if kind == "Dead" else 1.0)
        radii = [max(0.6, r0 * (1.0 - 0.45 * i / max(1, n - 1))) for i in range(n)]
        add_tube(bm, pts, radii, 5, STEM, 40.0, True, True, (rng.random(), rng.random()))
    cells = atlas['cells']
    for base, ph, size, depth in leaves:
        pitch = math.radians(rng.uniform(10.0, 38.0) if kind == "Dead" else rng.uniform(12.0, 50.0))
        b2 = base.copy()
        b2.y += rng.uniform(0.0, 5.0)
        add_leaf(bm, b2, ph, size * (1.45 if kind == "Dead" else 1.0), rng.choice(cells), atlas['orient'], pitch, rng, 2048.0, LEAF)
    # fit: X centred and exactly W wide, Z 0..H, Y back at 0
    xs = [v.co.x for v in bm.verts]
    zs = [v.co.z for v in bm.verts]
    sx = W / (max(xs) - min(xs))
    sz = H / (max(zs) - min(zs))
    cx = (max(xs) + min(xs)) / 2.0
    zmin = min(zs)
    for v in bm.verts:
        v.co.x = (v.co.x - cx) * sx
        v.co.z = (v.co.z - zmin) * sz
    ymin = min(v.co.y for v in bm.verts)
    for v in bm.verts:
        v.co.y -= ymin
    p = Piece(PREFIX + name, bm, ["MAT_Leaf", "MAT_Stem"],
              note="ivy %s %s card %gx%g: %d leaves on %d vines, atlas %s, %d cells; back at Y 0, no collision" % (shape, kind, W, H, len(leaves), len(polylines), atlas['src'], len(cells)))
    p.keep_uv = True
    p.seat_mode = "wall"
    p.smooth = 75.0
    p.subdir = "Ivy"
    p.textures = [(atlas['src'], t) for t in IVY_TEX[atlas['src']]]
    return p


def _gen_tree(seed):
    rng = random.Random(seed)
    bm = bmesh.new()
    _uvl(bm)
    BARK = 0
    seg_len = (40.0, 34.0, 22.0, 17.0)
    sides = (12, 8, 6, 5)
    info = dict(fork_z=0.0, trunk_r=0.0)

    def perp_rot(d, ang):
        ax = d.orthogonal()
        ax = Matrix.Rotation(rng.uniform(0, 2 * math.pi), 3, d) @ ax
        return (Matrix.Rotation(ang, 3, ax) @ d).normalized()

    def branch(p, d, length, r0, r1, level, bend, up_bias, droop=0.0):
        n = max(3, int(length / seg_len[level]))
        pts = [p.copy()]
        cur = d.copy()
        for i in range(n):
            jitter = Vector((rng.gauss(0, bend), rng.gauss(0, bend), rng.gauss(0, bend * 0.6)))
            cur = (cur + jitter + Vector((0, 0, up_bias - droop * (i / n)))).normalized()
            pts.append(pts[-1] + cur * (length / n))
        radii = []
        for i in range(n + 1):
            t = i / n
            r = r0 + (r1 - r0) * t
            if level == 0:
                r *= 1.0 + 0.4 * max(0.0, 1.0 - pts[i].z / 55.0) ** 2
            radii.append(max(0.5, r))
        add_tube(bm, pts, radii, sides[level], BARK, 150.0, level == 0, True, (rng.random(), rng.random()))
        return pts, radii

    # trunk: O45 at the base, slightly leaning and wobbling, forks at ~260 cm
    tp, tr = branch(Vector((0, 0, 0)), Vector((rng.uniform(-0.06, 0.06), rng.uniform(-0.06, 0.06), 1.0)).normalized(), 260.0, 22.5, 14.5, 0, 0.03, 0.0)
    top = tp[-1]
    info['fork_z'] = top.z
    info['trunk_r'] = 22.5
    for k in range(4):                                   # root flares
        az = k * math.pi / 2 + rng.uniform(-0.4, 0.4)
        branch(Vector((math.cos(az) * 12, math.sin(az) * 12, 28.0)), Vector((math.cos(az), math.sin(az), -0.3)).normalized(), 62.0, 12.0, 4.5, 1, 0.02, 0.0)
    az0 = rng.uniform(0, 2 * math.pi)
    limbs = []
    for k in range(3):                                   # three main limbs
        az = az0 + k * 2 * math.pi / 3 + rng.uniform(-0.3, 0.3)
        el = math.radians(rng.uniform(30, 55))
        d = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)))
        ln = rng.uniform(330, 420)
        r1 = 6.0 if k == 2 else 2.4                      # one limb snapped off short and blunt
        if k == 2:
            ln *= 0.6
        pts, radii = branch(top - Vector((0, 0, 8.0)), d, ln, 13.5, r1, 1, 0.09, 0.05, 0.0)
        limbs.append((pts, radii, ln))
    az = az0 + rng.uniform(0, 2 * math.pi)               # fourth, lower limb for an asymmetric crown
    d = Vector((math.cos(az) * 0.9, math.sin(az) * 0.9, 0.45)).normalized()
    pts, radii = branch(tp[int(0.7 * (len(tp) - 1))], d, 230.0, 8.5, 2.0, 1, 0.09, 0.05, 0.0)
    limbs.append((pts, radii, 230.0))
    for zf, ln in ((0.42, 80.0), (0.58, 55.0)):          # snapped stubs lower on the trunk
        i = int(zf * (len(tp) - 1))
        az = rng.uniform(0, 2 * math.pi)
        d = Vector((math.cos(az) * 0.9, math.sin(az) * 0.9, 0.3)).normalized()
        branch(tp[i], d, ln, 5.5, 3.5, 1, 0.03, 0.0)
    for pts, radii, ln in limbs:                         # level 2 and 3 on each limb
        n = len(pts) - 1
        for i in range(max(1, n // 8), n):
            if rng.random() > 0.78:
                continue
            d0 = (pts[min(i + 1, n)] - pts[i]).normalized()
            d1 = perp_rot(d0, math.radians(rng.uniform(30, 68)))
            if d1.z < -0.15:
                d1.z = -0.15
                d1.normalize()
            l2 = ln * rng.uniform(0.2, 0.5) * (1.0 - 0.45 * i / n)
            p2, r2 = branch(pts[i], d1, max(45.0, l2), max(1.4, radii[i] * 0.5), 1.0, 2, 0.12, 0.025, 0.0)
            m = len(p2) - 1
            for j in range(1, m):
                if rng.random() < 0.8:
                    dd = (p2[min(j + 1, m)] - p2[j]).normalized()
                    d3 = perp_rot(dd, math.radians(rng.uniform(28, 75)))
                    branch(p2[j], d3, rng.uniform(25, 70), max(0.9, r2[j] * 0.6), 0.5, 3, 0.18, 0.0, 0.25)
        if radii[-1] < 3.0:
            branch(pts[-1], (pts[-1] - pts[-2]).normalized(), 45.0, 2.0, 0.5, 3, 0.15, 0.0)   # limb tip twig
    return bm, info


def build_deadtree():
    best = None
    for seed in range(7000, 7400):
        bm, info = _gen_tree(seed)
        mn, mx = bounds(bm)
        s = 700.0 / (mx[2] - mn[2])
        cx, cy = (mn[0] + mx[0]) * 0.5 * s, (mn[1] + mx[1]) * 0.5 * s
        spread = max(mx[0] - mn[0], mx[1] - mn[1]) * s
        off = math.hypot(cx, cy)
        score = off + abs(spread - 520.0) * 0.1
        if best is None or score < best[0]:
            if best is not None:
                best[1].free()
            best = (score, bm, info, s, seed)
        else:
            bm.free()
        if off < 12.0 and 420.0 < spread < 620.0:
            break
    score, bm, info, s, seed = best
    for v in bm.verts:
        v.co *= s
    tr = info['trunk_r'] * s
    ucx_h = info['fork_z'] * s * 0.9
    p = Piece(PREFIX + "DeadTree_A", bm, ["MAT_Bark"], ucx_design=[ucx_box(-tr * 0.85, tr * 0.85, -tr * 0.85, tr * 0.85, 0.0, ucx_h)],
              note="seeded bpy branching tree (seed %d, scale %.3f): trunk O%.0f at the base, 3 main limbs + 2 snapped stubs, 3 levels, twig tips O1; "
                   "bark UV 1 tile / 150 cm, use the DeadTreeTrunk bark textures; UCX = trunk box only" % (seed, s, 2 * tr))
    p.keep_uv = True
    p.smooth = 70.0
    return p


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
        # ---- P7-FIX3 G2a ----
        ("WellHead_A", build_wellhead),
        ("TimberPost_20x20x420", build_timber_post),
        ("Purlin_15x15x1000", build_purlin),
        ("Rafter_15x10x420", build_rafter),
        ("Rafter_Broken_15x10x260", build_rafter_broken),
        ("RoofPlanks_200x100x4", lambda: build_planks(False)),
        ("RoofPlanks_Broken_200x100x4", lambda: build_planks(True)),
        ("EarthPatch_400x400x15", build_earthpatch),
        ("DeadTree_A", build_deadtree),
        ("Ivy_Climb_300x450_Green", lambda: build_ivy("Ivy_Climb_300x450_Green", 300.0, 450.0, "Green", "climb", 9101)),
        ("Ivy_Patch_200x300_Green", lambda: build_ivy("Ivy_Patch_200x300_Green", 200.0, 300.0, "Green", "patch", 9102)),
        ("Ivy_Hang_150x600_Green", lambda: build_ivy("Ivy_Hang_150x600_Green", 150.0, 600.0, "Green", "hang", 9103)),
        ("Ivy_Creep_400x200_Green", lambda: build_ivy("Ivy_Creep_400x200_Green", 400.0, 200.0, "Green", "creep", 9104)),
        ("Ivy_Climb_300x450_Dead", lambda: build_ivy("Ivy_Climb_300x450_Dead", 300.0, 450.0, "Dead", "climb", 9111)),
        ("Ivy_Patch_200x300_Dead", lambda: build_ivy("Ivy_Patch_200x300_Dead", 200.0, 300.0, "Dead", "patch", 9112)),
        ("Ivy_Hang_150x600_Dead", lambda: build_ivy("Ivy_Hang_150x600_Dead", 150.0, 600.0, "Dead", "hang", 9113)),
        ("Ivy_Creep_400x200_Dead", lambda: build_ivy("Ivy_Creep_400x200_Dead", 400.0, 200.0, "Dead", "creep", 9114)),
    ]


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SourceArt", "Props", "Procedural"))
    only = []
    tag = None
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


def run():
    out_dir, only, tag = parse_args()
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
        K.finalize(pc.bm, smooth_deg=pc.smooth, keep_uv=pc.keep_uv)
        mats = prop_mats(pc.slots)
        K.export_piece_fbx(pc.name, pc.bm, pc.ucx, os.path.join(out_dir, pc.subdir, pc.name + ".fbx"), mats)
        for src_id, mapname in pc.textures:                                  # atlas textures next to the FBX
            srcp = os.path.join(ROOT, "ExternalAssets", "Incoming", "ambientcg-" + src_id, src_id + "_2K-JPG", "%s_2K-JPG_%s.jpg" % (src_id, mapname))
            if os.path.exists(srcp):
                shutil.copy2(srcp, os.path.join(out_dir, pc.subdir, os.path.basename(srcp)))
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
    suffix = ("_" + tag) if tag else "_partial"
    blend = os.path.join(out_dir, "LB_Props.blend" if not only else "LB_Props%s.blend" % suffix)
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    with open(os.path.join(out_dir, "props_report.json" if not only else "props_report%s.json" % suffix), "w") as fh:
        json.dump(report, fh, indent=1)
    print("DONE %d props in %.1fs -> %s" % (len(pieces), time.time() - t0, out_dir))


if __name__ == "__main__":
    run()
