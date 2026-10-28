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
        self.seat_mode = "centre"                 # "centre" = bottom-centre; "wall" = X centre, back plane at Y 0, min Z 0; "none" = as built
        self.smooth = 30.0
        self.subdir = ""
        self.textures = []                        # (ambientCG id, map name) copied next to the FBX

    def seat(self):
        """Pivot = bottom-centre: shift visual + collision so XY bounds centre = 0 and min Z = 0."""
        mn, mx = bounds(self.bm)
        s = (-(mn[0] + mx[0]) * 0.5, -(mn[1] + mx[1]) * 0.5, -mn[2])
        if self.seat_mode == "wall":
            s = (s[0], -mn[1], s[2])
        elif self.seat_mode == "none":                  # the builder already put the pivot where it belongs (light shafts)
            s = (0.0, 0.0, 0.0)
        elif self.seat_mode == "centre3":               # P9: XYZ bounds centre at the origin (Block_100_C, CapstanDrum)
            s = (s[0], s[1], -(mn[2] + mx[2]) * 0.5)
        elif self.seat_mode == "xy":                    # P9: XY bounds centre at 0, Z as built (Boards_Broken: z 0 = board undersides)
            s = (s[0], s[1], 0.0)
        elif self.seat_mode == "backcentre":            # P9: X centre, back plane at Y 0, Z centre (PlaqueFrame)
            s = (s[0], -mn[1], -(mn[2] + mx[2]) * 0.5)
        elif self.seat_mode == "top":                   # P9: design axis stays on the origin, Z max = 0 (hanging roots)
            s = (0.0, 0.0, -mx[2])
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
# P8-3 chapel props (plan Docs/plans/P8_CHAPEL_ART.md section 2 P8-3 + amendment C1).  Pivot = bottom-centre (props rule).
# ==============================================================================================
MAT_COLORS.update({
    "MAT_Slate": (0.16, 0.17, 0.19, 1.0),
    "MAT_Glass": (0.20, 0.30, 0.55, 1.0),
    "MAT_Cobweb": (0.80, 0.80, 0.78, 1.0),
    "MAT_Flame": (1.0, 0.62, 0.18, 1.0),
    "MAT_Backdrop": (0.06, 0.065, 0.08, 1.0),
})


def tri_ear(bm):
    """Triangulate with ear clipping (the default BEAUTY method can produce overlapping triangles on concave n-gons)."""
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='EAR_CLIP')
    return bm


def rot_about(bm, axis, deg, pivot):
    shift(bm, -pivot[0], -pivot[1], -pivot[2])
    rot(bm, axis, deg)
    shift(bm, pivot[0], pivot[1], pivot[2])
    return bm


def set_uv(bm, fn):
    """fn(face, vert_co) -> (u, v) for every loop (creates the UVMap layer; build the piece with keep_uv = True)."""
    uv = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    bm.normal_update()
    for f in bm.faces:
        for l in f.loops:
            l[uv].uv = fn(f, l.vert.co)
    return bm


def glass_slab(poly, thick, ref_min, ref_size, uv_rect=(0.0, 0.0, 1.0, 1.0), mat=0):
    """Thin closed slab of a (x, z) outline, Y -thick/2..thick/2.  UV: the two big faces map the reference box
    (ref_min, ref_size) onto uv_rect = (u0, v0, u1, v1); rims collapse to the rect centre."""
    s = K.prism(poly, 'y', -thick / 2, thick / 2, mat)
    s.normal_update()
    u0, v0, u1, v1 = uv_rect

    def fn(f, c):
        if abs(f.normal.y) > 0.9:
            return (u0 + (c.x - ref_min[0]) / ref_size[0] * (u1 - u0), v0 + (c.z - ref_min[1]) / ref_size[1] * (v1 - v0))
        return ((u0 + u1) * 0.5, (v0 + v1) * 0.5)

    return set_uv(s, fn)


# ---------------------------------------------------------------------------------------------- truss
def build_truss():
    TH = math.atan2(965.0, 810.0)
    vt = 40.0 / math.cos(TH)                                     # rafters 40 deep (perpendicular to the roof plane)

    def zt(y):
        return 1265.0 - (965.0 / 810.0) * abs(y)

    X0, X1 = -15.0, 15.0                                         # every member 30 wide (X)
    parts = []
    seed = [9101]

    def finish(b, amp=0.3):
        K.bevel_all(b, 0.8, 25.0)
        tri_ear(b)
        subdiv_long(b, 30.0)
        bmesh.ops.triangulate(b, faces=b.faces[:])
        weather(b, seed[0], amp, mask=lambda co, n: 0.0 if co.z <= 0.02 else 1.0, f1=1 / 70.0, f2=1 / 22.0)
        seed[0] += 7
        return b

    for sgn in (-1, 1):
        # principal rafter: top face on the roof plane, 40 deep (perpendicular, grows downward), clipped at Y 0 and at the wall face |Y| 750
        ya, yb = (0.0, 750.0) if sgn > 0 else (-750.0, 0.0)
        pts = [(0.0, 1265.0 - vt), (750.0, zt(750.0) - vt), (750.0, zt(750.0)), (0.0, 1265.0)]
        pts = [(sgn * y, z) for (y, z) in pts]
        parts.append(finish(K.prism(pts, 'x', X0, X1, 0)))
        # post 30 (X) x 35 (Y) at |Y| 715..750 (back face on the wall plane), top cut along the roof plane (buried 8 cm below the rafter top)
        pp = [(sgn * 715.0, 0.0), (sgn * 750.0, 0.0), (sgn * 750.0, zt(750.0) - 8.0), (sgn * 715.0, zt(715.0) - 8.0)]
        parts.append(finish(K.prism(pp, 'x', X0, X1, 0), 0.25))
        # arch brace 30 x 30: band between r 783.9 (intrados, unchanged) and 813.9 around the centre (-sgn 78.9, 50); outer edge clamped to the collar top Z 850
        cy = -sgn * 78.9
        n = 32
        ro, ri = 813.9, 783.9
        pol = []
        pho = math.acos(78.9 / ro)
        phi = math.acos(78.9 / ri)
        for i in range(n + 1):
            ph = pho * i / n
            pol.append((cy + sgn * ro * math.cos(ph), min(850.0, 50.0 + ro * math.sin(ph))))
        for i in range(n, -1, -1):
            ph = phi * i / n
            pol.append((cy + sgn * ri * math.cos(ph), 50.0 + ri * math.sin(ph)))
        parts.append(finish(K.prism(pol, 'x', X0, X1, 0), 0.25))
    # collar 30 x 35, top at Z 850 (grows downward), ends buried in the rafters
    col = K.box(X0, X1, -345.0, 345.0, 815.0, 850.0, 0, 0.0)
    parts.append(finish(col, 0.25))
    # pegs (O2.4, protruding 0.4 on each face -> X bounds 30.8)
    for sgn in (-1, 1):
        for (py, pz) in ((732.0, 352.0), (722.0, 90.0), (335.0, 832.0), (120.0, 832.0)):
            pg = K.cylinder(1.2, 30.8, 8, 0)
            rot(pg, 'Y', 90.0)
            shift(pg, -15.4, sgn * py, pz)
            parts.append(pg)
    bm = join(parts)
    return Piece(PREFIX + "Truss_ArchBraced_1500", bm, ["MAT_Wood"],
                 note="arch-braced truss: local Z 0 = post foot (world 900), Y across the nave (+-750), X 30 (pegs to 30.8); rafters 30x40 with top faces on the roof plane "
                      "(Y+-810,Z300)-(0,1265), posts 30x35 at |Y| 715..750, collar 30x35 top Z 850, pointed arch braces 30x30 (intrados r 783.9, springing (Y+-705,Z50)); no UCX")


# ---------------------------------------------------------------------------------------------- pews
def pew_panel(y0, y1, seed, rng, chips=True):
    n = 14
    pts = [(-27.5, 0.0), (27.5, 0.0), (27.5, 68.0)]
    for i in range(1, n + 1):
        x = 27.5 - 55.0 * i / n
        t = (27.5 - x) / 55.0
        pts.append((x, 68.0 + 27.0 * t * t * (3 - 2 * t)))
    p = K.prism(pts, 'y', y0, y1, 0)
    K.bevel_all(p, 0.8, 25.0)
    cut = K.prism(K.pointed_light_poly(3.0, 50.0, 58.0, 18.0, 18.0, cusp=1.0, n_arc=10), 'y', y0 - 1.0, y1 + 1.0, 0)
    p = bool_op(p, cut, 'DIFFERENCE', 1)
    cut.free()
    if chips:
        spots = [((rng.uniform(-20, 5), (y0 + y1) / 2, 89.0 + rng.uniform(-3, 2)), rng.uniform(2.0, 3.2)),
                 ((27.0, (y0 + y1) / 2, rng.uniform(62, 68)), rng.uniform(2.0, 2.8)),
                 ((rng.uniform(-20, 20), (y0 + y1) / 2, 0.0), 2.4)]
        p = cut_chips(p, rng, spots, 0)
    densify(p, 10.0)
    weather(p, seed, 0.45, mask=lambda co, n_: 0.0 if co.z < 0.02 else 1.0, f1=1 / 25.0, f2=1 / 7.0)
    return p


def build_pew(broken):
    rng = random.Random(9201 if not broken else 9211)
    sd = 9300 if not broken else 9400
    parts = []
    parts.append(pew_panel(-125.0, -120.0, sd + 1, rng))
    if not broken:
        parts.append(pew_panel(120.0, 125.0, sd + 2, rng))
    else:                                                            # the +Y end panel is gone: only a jagged stump is left (keeps the bounds symmetric)
        stump = K.prism([(-27.5, 0.0), (27.5, 0.0), (27.5, 17.0), (19.0, 24.0), (12.0, 15.0), (4.0, 27.0), (-6.0, 14.0), (-14.0, 22.0), (-27.5, 12.0)],
                        'y', 120.0, 125.0, 0)
        K.bevel_all(stump, 0.6, 25.0)
        tri_ear(stump)
        densify(stump, 10.0)
        weather(stump, sd + 3, 0.45, mask=lambda co, n_: 0.0 if co.z < 0.02 else 1.0, f1=1 / 25.0, f2=1 / 7.0)
        parts.append(stump)
    # seat: two planks across (X -22..2 and 2.6..27.5), top Z 45
    sp = lambda x0, x1, y0, y1, k: lbeam(x0, x1, y0, y1, 41.0, 45.0, sd + 10 + k, 0, 0.6, 24.0, 0.3)
    if not broken:
        parts += [sp(-22.0, 2.0, -120.0, 120.0, 0), sp(2.6, 27.5, -120.0, 120.0, 1)]
    else:
        back_a = sp(-22.0, 2.0, -120.0, 43.0, 0)
        back_b = sp(-22.0, 2.0, 47.0, 120.0, 1)
        rot_about(back_b, 'X', -5.0, (0.0, 47.0, 43.0))                 # right half of the back plank sags
        front = sp(2.6, 27.5, -120.0, -10.0, 2)
        parts += [back_a, back_b, front]
        for k, (x0, x1, yy) in enumerate(((5.0, 8.0, -10.0), (13.0, 16.0, -10.0), (21.0, 24.0, -10.0))):   # splinters of the missing plank
            parts.append(lbeam(x0, x1, yy, yy + rng.uniform(5.0, 11.0), 41.0, 44.0 + rng.uniform(-0.5, 0.5), sd + 30 + k, 0, 0.3, 24.0, 0.1))
    # apron under the seat front + rear stretcher
    parts.append(lbeam(24.0, 27.5, -120.0, 120.0 if not broken else 20.0, 9.0, 41.0, sd + 20, 0, 0.5, 24.0, 0.3))
    parts.append(lbeam(-20.0, -16.0, -120.0, 120.0, 22.0, 33.0, sd + 21, 0, 0.5, 24.0, 0.3))
    # back: lower board + two upper boards + top rail (X -27.5..-24, rail to -21.5)
    parts.append(lbeam(-27.5, -24.0, -120.0, 120.0, 52.0, 64.0, sd + 22, 0, 0.5, 24.0, 0.3))
    upper = [lbeam(-27.5, -24.0, 10.0 if broken else -120.0, 120.0, 66.0, 78.0, sd + 23, 0, 0.5, 24.0, 0.3),
             lbeam(-27.5, -24.0, 10.0 if broken else -120.0, 120.0, 80.0, 89.0, sd + 24, 0, 0.5, 24.0, 0.3),
             lbeam(-27.5, -21.5, 10.0 if broken else -120.0, 120.0, 89.0, 95.0, sd + 25, 0, 0.8, 24.0, 0.3)]
    if broken:
        for u in upper:
            rot_about(u, 'Y', 118.0, (-26.0, 0.0, 64.0))             # snapped at the lower board, hanging forward / down onto the seat
        parts += upper
        for k in range(3):                                           # left half keeps its upper boards / rail up to the break
            z0, z1 = ((66.0, 78.0), (80.0, 89.0), (89.0, 95.0))[k]
            x1 = (-24.0, -24.0, -21.5)[k]
            parts.append(lbeam(-27.5, x1, -120.0, 8.0 + 2.0 * k, z0, z1, sd + 40 + k, 0, 0.5, 24.0, 0.3))
    else:
        parts += upper
    bm = join(parts)
    if not broken:
        ucx = [K.box_hull(-27.5, 27.5, -125.0, 125.0, 0.0, 45.0), K.box_hull(-27.5, -21.5, -125.0, 125.0, 45.0, 95.0)]
        note = "monastic pew facing +X: end panels with pointed-trefoil cut-out, 2 seat planks (top Z 45, covers X -22..27.5), 3-board back + top rail (top Z 95); UCX seat box + back box"
    else:
        ucx = [K.box_hull(-27.5, 27.5, -125.0, -10.0, 0.0, 45.0), K.box_hull(-27.5, 2.0, -10.0, 125.0, 0.0, 45.0),
               K.box_hull(-27.5, -24.0, -125.0, 8.0, 45.0, 95.0)]
        note = "worn pew: +Y end panel missing, back snapped (upper boards hanging forward), seat split (front plank missing for Y > -10); 3 UCX"
    return Piece(PREFIX + ("Pew_Broken" if broken else "Pew_A"), bm, ["MAT_Wood"], ucx_design=ucx, note=note)


# ---------------------------------------------------------------------------------------------- altar rail
def build_altar_rail():
    parts = []
    sd = 9500
    parts.append(lbeam(-20.0, -6.0, -300.0, 300.0, 0.0, 9.0, sd, 0, 1.2, 25.0, 0.3))               # kneeler (nave side)
    parts.append(lbeam(-10.0, 10.0, -300.0, 300.0, 88.0, 100.0, sd + 1, 0, 2.5, 25.0, 0.3))          # top rail
    parts.append(lbeam(6.0, 20.0, -300.0, 300.0, 0.0, 6.0, sd + 9, 0, 1.0, 25.0, 0.3))                # base skirting on the altar side
    parts.append(lbeam(-6.0, 6.0, -286.0, 286.0, 8.0, 16.0, sd + 2, 0, 0.8, 25.0, 0.3))              # bottom rail
    for k, (y0, y1) in enumerate(((-300.0, -286.0), (286.0, 300.0))):
        parts.append(lbeam(-7.0, 7.0, y0, y1, 0.0, 100.0, sd + 3 + k, 0, 1.0, 25.0, 0.3))
    prof = [(2.3, 16.0), (2.5, 20.0), (3.6, 26.0), (2.2, 32.0), (2.2, 44.0), (3.2, 52.0), (3.9, 58.0), (3.2, 64.0), (2.2, 70.0),
            (2.2, 80.0), (2.9, 86.0), (2.9, 88.0)]
    pitch = 572.0 / 14.0
    for i in range(13):
        yc = -286.0 + (i + 1) * pitch
        if i in (3, 9):
            continue                                                  # two balusters missing
        p = prof
        if i == 6:                                                    # one snapped at z 40 (ragged tip)
            p = [(r, z) for (r, z) in prof if z < 40.0] + [(2.2, 40.0), (1.6, 41.5), (0.6, 44.0)]
        b = K.lathe_z(p, 10, 0)
        shift(b, 0.0, yc, 0.0)
        parts.append(b)
    bm = join(parts)
    return Piece(PREFIX + "AltarRail_600x40x100", bm, ["MAT_Wood"], ucx_design=[K.box_hull(-20.0, 20.0, -300.0, 300.0, 0.0, 100.0)],
                 note="rail along Y (600), 40 deep along X (kneeler on the -X/nave side), top rail Z 88..100, 13 balusters (2 missing, 1 snapped), 1 UCX box")


# ---------------------------------------------------------------------------------------------- lectern
def build_lectern():
    TR, WD = 0, 1                                                    # slots: MAT_Trim, MAT_Wood
    sd = 9600
    parts = []

    def octa(r_flat, z0, z1, bevel=1.5):
        rc = r_flat / math.cos(math.radians(22.5))
        pts = [(rc * math.cos(math.radians(45.0 * i + 22.5)), rc * math.sin(math.radians(45.0 * i + 22.5))) for i in range(8)]
        b = K.prism(pts, 'z', z0, z1, TR)
        K.bevel_all(b, bevel, 25.0)
        return b, pts

    foot, fpts = octa(28.0, 0.0, 7.0)
    foot2, _ = octa(19.0, 7.0, 16.0, 1.2)
    for b in (foot, foot2):
        densify(b, 6.0)
        weather(b, sd, 0.5, mask=lambda co, n_: 0.0 if co.z < 0.02 else 1.0)
    parts += [foot, foot2]
    prof = [(8.0, 16.0), (8.0, 19.0), (6.2, 22.0), (6.2, 60.0), (8.4, 63.0), (8.4, 67.0), (6.2, 70.0), (6.2, 92.0), (9.5, 96.0), (9.5, 100.0)]
    parts.append(K.lathe_z(prof, 8, WD))
    # slanted desk (Y -20..20): back edge high (z 125), front (+Y) low (z 109); 3 cm board + front lip + support wedge
    desk = K.prism([(-20.0, 121.0), (20.0, 105.0), (20.0, 108.0), (-20.0, 124.0)], 'x', -26.0, 26.0, WD)
    K.bevel_all(desk, 0.6, 25.0)
    lip = K.box(-26.0, 26.0, 17.0, 20.0, 108.0, 111.5, WD, 0.4)
    back = K.box(-26.0, 26.0, -20.0, -17.0, 121.0, 125.0, WD, 0.5)
    wedge = K.prism([(-12.0, 100.0), (12.0, 100.0), (14.0, 106.0), (-17.0, 122.0)], 'x', -9.0, 9.0, WD)
    for b in (desk, lip, back, wedge):
        parts.append(b)
    bm = join(parts)
    hull_a = K.hull_from_points([Vector((p[0], p[1], 0.0)) for p in fpts] + [Vector((9.0, 9.0, 100.0)), Vector((-9.0, 9.0, 100.0)), Vector((9.0, -9.0, 100.0)), Vector((-9.0, -9.0, 100.0))], 0)
    hull_b = K.hull_from_points([Vector((x, y, z)) for x in (-26.0, 26.0) for (y, z) in ((-20.0, 124.0), (-20.0, 100.0), (20.0, 100.0), (20.0, 111.5))], 0)
    return Piece(PREFIX + "Lectern_A", bm, ["MAT_Trim", "MAT_Wood"], ucx_design=[hull_a, hull_b],
                 note="octagonal stone foot (56 flat-to-flat) + octagonal wooden shaft + slanted book desk (reader at +Y); 2 UCX (foot+shaft hull, desk hull)")


# ---------------------------------------------------------------------------------------------- altar (C1-3)
def build_altar():
    rng = random.Random(9301)
    sd = 9700
    parts = []
    H = 101.0
    # wings (front recessed 4 cm behind the mensa lip), blind pointed niches in the fronts
    for sgn in (-1, 1):
        y0, y1 = (60.0, 150.0) if sgn > 0 else (-150.0, -60.0)
        w = K.box(-48.0, 52.0, y0, y1, 0.0, 91.0, 0, 1.0)
        niche = K.prism(K.pointed_light_poly(sgn * 105.0, 16.0, 44.0, 52.0, 41.6, cusp=0.0, n_arc=10), 'x', -49.0, -46.5, 0)
        # prism axis 'x': (p, q) = (y, z) -> the polygon above is (x, z) = (y, z) with centre y = +-105
        w = bool_op(w, niche, 'DIFFERENCE', 1)
        niche.free()
        densify(w, 12.0)
        weather(w, sd + sgn, 0.5, mask=lambda co, n_: 0.0 if co.z < 0.02 else 1.0, f1=1 / 25.0, f2=1 / 7.0)
        plinth = K.box(-50.0, 52.0, y0, y1, 0.0, 8.0, 0, 1.0)
        parts += [w, plinth]
    # centre block: raised front panel (front at the mensa lip), hollow core Y +-52 / X -51..51 open at the bottom
    blk = K.box(-52.0, 52.0, -60.0, 60.0, 0.0, 91.0, 0, 1.0)
    core = K.box(-51.0, 51.0, -52.0, 52.0, -1.0, 91.0, 0, 0.0)
    blk = bool_op(blk, core, 'DIFFERENCE', 1)
    core.free()
    parts.append(blk)
    # mensa: Z 91..101, O84 hole at the centre, 5 incised crosses
    men = K.box(-52.0, 52.0, -150.0, 150.0, 91.0, H, 0, 1.2)
    hole = K.cylinder(42.0, 14.0, 48, 0)
    shift(hole, 0.0, 0.0, 89.0)
    men = bool_op(men, hole, 'DIFFERENCE', 1)
    hole.free()
    cut = K.bmesh.new()
    for (cx_, cy_) in ((-34.0, -112.0), (-34.0, 112.0), (34.0, -112.0), (34.0, 112.0), (0.0, 128.0)):
        for (a0, a1, b0, b1) in ((-7.0, 7.0, -0.8, 0.8), (-0.8, 0.8, -7.0, 7.0)):
            K.bm_append(cut, K.box(cx_ + a0, cx_ + a1, cy_ + b0, cy_ + b1, H - 0.6, H + 1.0, 0, 0.0))
    men = bool_op(men, cut, 'DIFFERENCE', 1)
    cut.free()
    densify(men, 9.0, region=lambda p: p.z > 99.0)
    parts.append(men)
    bm = join(parts)
    ucx = [K.box_hull(-52.0, 52.0, 54.0, 150.0, 0.0, H), K.box_hull(-52.0, 52.0, -150.0, -54.0, 0.0, H)]
    return Piece(PREFIX + "Altar_A", bm, ["MAT_Trim"], ucx_design=ucx,
                 note="C1-3 shell: X -52..52 (104), Y +-150, Z 0..101 (world 30..131); front panel at X -52, wings recessed 4, mensa Z 91..101 O84 hole at centre, "
                      "hollow core Y +-52 X -51..51 open at the bottom, UCX only the two wings Y +-(54..150)")


def build_mech_shell_cyl():
    outer = K.lathe_z([(42.0, 0.0), (42.0, 49.4), (41.2, 51.0), (0.0, 51.0)], 32, 0)
    inner = K.cylinder(41.0, 51.0, 32, 0)
    shift(inner, 0.0, 0.0, -1.0)
    bm = bool_op(outer, inner, 'DIFFERENCE', 1)
    return Piece(PREFIX + "MechShell_Cyl", bm, ["MAT_Trim"], note="C1-3 fallback: O84 x 51 shell, open at the bottom, 1 cm wall; place Z 130..181 centred on the mechanism cylinder; NoCollision")


def build_mech_shell_cube():
    outer = K.box(-8.5, 8.5, -8.5, 8.5, 0.0, 17.0, 0, 0.8)
    inner = K.box(-7.7, 7.7, -7.7, 7.7, -1.0, 16.2, 0, 0.0)
    bm = bool_op(outer, inner, 'DIFFERENCE', 1)
    return Piece(PREFIX + "MechShell_Cube", bm, ["MAT_Trim"], note="C1-3 fallback: 17 cm cube shell around the 15 cm marker cube, open at the bottom; NoCollision")


# ---------------------------------------------------------------------------------------------- slate shards, finial, backdrop
def build_slate_shards():
    rng = random.Random(9801)
    parts = []
    n = 17
    for i in range(n):
        s = rng.uniform(11.0, 30.0)
        k = rng.choice((4, 5, 5, 6))
        ang0 = rng.uniform(0, 6.28)
        pts = []
        for j in range(k):
            a = ang0 + 2 * math.pi * j / k + rng.uniform(-0.3, 0.3)
            r = s * rng.uniform(0.55, 1.0)
            pts.append((r * math.cos(a) * rng.uniform(1.0, 1.5), r * math.sin(a)))
        b = K.prism(pts, 'z', 0.0, rng.uniform(0.7, 1.2), 0)
        rot(b, 'X', rng.uniform(-22.0, 22.0))
        rot(b, 'Y', rng.uniform(-22.0, 22.0))
        rot(b, 'Z', rng.uniform(0.0, 360.0))
        t = rng.random() ** 0.6
        a = rng.uniform(0, 6.28)
        shift(b, 50.0 * t * math.cos(a), 37.0 * t * math.sin(a), 0.5 + 1.5 * (1.0 - t) * rng.uniform(0.3, 1.8) + 0.8 * (i % 5))
        parts.append(b)
    bm = join(parts)
    mn, mx = bounds(bm)
    for v in bm.verts:
        v.co.x = (v.co.x - (mn[0] + mx[0]) / 2) * 120.0 / (mx[0] - mn[0])
        v.co.y = (v.co.y - (mn[1] + mx[1]) / 2) * 90.0 / (mx[1] - mn[1])
    return Piece(PREFIX + "SlateShards_A", bm, ["MAT_Slate"], note="17 slate fragments (11-30 cm, 0.7-1.2 cm thick) in a 120 x 90 heap; NoCollision")


def build_cross_finial():
    base = K.prism([(-20.0, 0.0), (20.0, 0.0), (20.0, 30.0), (17.0, 38.0), (15.0, 40.0), (-15.0, 40.0), (-17.0, 38.0), (-20.0, 30.0)], 'y', -12.5, 12.5, 0)
    K.bevel_all(base, 1.4, 25.0)
    shaft = K.box(-7.0, 7.0, -10.0, 10.0, 40.0, 130.0, 0, 1.2)           # three convex boxes: a concave 12-gon bevelled badly
    arms = K.box(-30.0, 30.0, -10.0, 10.0, 100.0, 114.0, 0, 1.2)
    cross = join([shaft, arms])
    rng = random.Random(9901)
    bm = join([base, cross])
    tri_ear(bm)
    densify(bm, 7.0)
    weather(bm, 9902, 0.6, mask=lambda co, n_: 0.0 if co.z < 0.02 else 1.0)
    return Piece(PREFIX + "CrossFinial_A", bm, ["MAT_Trim"],
                 note="stone gable cross: arms 60 wide, 25 deep (base) / 20 deep (cross), cross 90 tall on a 40 high base -> bounds 60 x 25 x 130")


def build_backdrop():
    b = bmesh.new()
    vs = [b.verts.new(p) for p in ((0.0, -400.0, 0.0), (0.0, -400.0, 850.0), (0.0, 400.0, 850.0), (0.0, 400.0, 0.0))]
    b.faces.new(vs)                                                  # normal -X
    set_uv(b, lambda f, c: ((c.y + 400.0) / 800.0, c.z / 850.0))
    pc = Piece(PREFIX + "Backdrop_Plane_800x850", b, ["MAT_Backdrop"], note="single quad facing -X (towards the window), UV 0..1")
    pc.keep_uv = True
    return pc


# ---------------------------------------------------------------------------------------------- glass
def lancet_poly(w, h, ratio=0.8, n_arc=18, cusp=0.0):
    half, R, rise = K.arch_dims(w, ratio)
    return K.pointed_light_poly(0.0, 0.0, h - rise, w, R, cusp=cusp, n_arc=n_arc)


def build_glass_lancet():
    poly = lancet_poly(140.0, 560.0)
    b = glass_slab(poly, 1.0, (-70.0, 0.0), (140.0, 560.0))
    pc = Piece(PREFIX + "Glass_Lancet_140x560", b, ["MAT_Glass"], note="lancet outline 140 x 560 (clear opening), 1 cm slab, UV 0..1 over the bounding box (front = -Y), NoCollision")
    pc.keep_uv = True
    return pc


def clip_halfplane(poly, p, d, off):
    """Keep the part of the convex polygon with (x - p) . d <= off  (d unit)."""
    out = []
    n = len(poly)
    f = lambda q: (q[0] - p[0]) * d[0] + (q[1] - p[1]) * d[1] - off
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        fa, fb = f(a), f(b)
        if fa <= 0:
            out.append(a)
        if (fa <= 0) != (fb <= 0):
            t = fa / (fa - fb)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def build_glass_broken():
    base = lancet_poly(140.0, 560.0)
    rng = random.Random(9951)
    for attempt in range(200):
        sites = [(rng.uniform(-70, 70), rng.uniform(0, 560)) for _ in range(16)]
        cells = []
        for i, s in enumerate(sites):
            poly = base
            for j, t in enumerate(sites):
                if i == j or not poly:
                    continue
                d = (t[0] - s[0], t[1] - s[1])
                ln = math.hypot(*d)
                d = (d[0] / ln, d[1] / ln)
                mid = ((s[0] + t[0]) / 2, (s[1] + t[1]) / 2)
                poly = clip_halfplane(poly, mid, d, -0.6)
            if len(poly) >= 3 and abs(K.poly_area(poly)) > 40.0:
                cells.append((s, poly))
        keep = [c for c in cells if c[0][1] < 215.0]
        xs = [p[0] for (_s, pl) in keep for p in pl]
        zs = [p[1] for (_s, pl) in keep for p in pl]
        if 5 <= len(keep) <= 7 and xs and min(xs) < -69.5 and max(xs) > 69.5 and min(zs) < 0.01:
            break
    parts = []
    for (_s, pl) in keep:
        parts.append(glass_slab(pl, 1.0, (-70.0, 0.0), (140.0, 560.0)))
    # one loose lead came: a thin curved strip hanging off the left jamb (0.9 wide)
    pts = [Vector((-66.0 + 5.0 * math.sin(t * 2.1), 0.0, 262.0 + 150.0 * t)) for t in [i / 10.0 for i in range(11)]]
    strip = bmesh.new()
    L_, R_ = [], []
    for p in pts:
        L_.append(strip.verts.new((p.x - 0.45, -0.5, p.z)))
        R_.append(strip.verts.new((p.x + 0.45, -0.5, p.z)))
    for i in range(10):
        strip.faces.new((L_[i], R_[i], R_[i + 1], L_[i + 1]))
    ex = bmesh.ops.extrude_face_region(strip, geom=strip.faces[:])
    bmesh.ops.translate(strip, vec=(0, 1.0, 0), verts=[e for e in ex['geom'] if isinstance(e, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(strip, faces=strip.faces)
    K.bm_set_mat(strip, 0)
    set_uv(strip, lambda f, c: ((c.x + 70.0) / 140.0, c.z / 560.0))
    parts.append(strip)
    bm = join(parts)
    set_uv(bm, lambda f, c: ((c.x + 70.0) / 140.0, c.z / 560.0) if abs(f.normal.y) > 0.9 else (0.5, 0.5))
    pc = Piece(PREFIX + "Glass_Lancet_Broken", bm, ["MAT_Glass"],
               note="%d shards remain in the lower part of the 140 x 560 lancet + a loose lead came; UV = the intact lancet's box; NoCollision" % len(keep))
    pc.keep_uv = True
    return pc


def build_glass_clue():
    half, R, rise = K.arch_dims(100.0, 0.8)
    h = 220.2
    poly = K.pointed_light_poly(0.0, 0.0, h - rise, 100.0, R, cusp=0.0, n_arc=14)
    b = glass_slab(poly, 1.0, (-50.0, 0.0), (100.0, h))
    pc = Piece(PREFIX + "Glass_Clue_Ext", b, ["MAT_Glass"], note="clue opening outline 100 x 220.2 (sill 312 .. apex 532.2), 1 cm slab, UV 0..1; NoCollision")
    pc.keep_uv = True
    return pc


def build_glass_east():
    sill = 310.0
    lights = [K.pointed_light_poly(s * 78.0, 0.0, 340.0, 144.0, 144.0, cusp=5.0) for s in (-1, 1)]
    quat = K.quatrefoil_poly(0.0, 790.0 - sill, 45.0)
    parts = []
    # atlas 1:2 (u 0..1, v 0..1): left light u 0..0.5 / v 0..0.75, right light u 0.5..1 / v 0..0.75, quatrefoil u .25..0.75 / v 0.75..1
    parts.append(glass_slab(lights[0], 1.0, (-150.0, 0.0), (144.0, 124.7 + 340.0), (0.0, 0.0, 0.5, 0.75)))
    parts.append(glass_slab(lights[1], 1.0, (6.0, 0.0), (144.0, 124.7 + 340.0), (0.5, 0.0, 1.0, 0.75)))
    qx = [p[0] for p in quat]
    qz = [p[1] for p in quat]
    parts.append(glass_slab(quat, 1.0, (min(qx), min(qz)), (max(qx) - min(qx), max(qz) - min(qz)), (0.25, 0.75, 0.75, 1.0)))
    bm = join(parts)                                                 # join drops the UVs: re-assign them per island
    qmin = (min(qx), min(qz))
    qsize = (max(qx) - min(qx), max(qz) - min(qz))

    def east_uv(f, c):
        if abs(f.normal.y) < 0.9:
            return (0.5, 0.5)
        cc = f.calc_center_median()
        if math.hypot(cc.x, cc.z - 480.0) < 48.0:
            return (0.25 + (c.x - qmin[0]) / qsize[0] * 0.5, 0.75 + (c.z - qmin[1]) / qsize[1] * 0.25)
        if cc.x < 0:
            return ((c.x + 150.0) / 144.0 * 0.5, c.z / (124.7 + 340.0) * 0.75)
        return (0.5 + (c.x - 6.0) / 144.0 * 0.5, c.z / (124.7 + 340.0) * 0.75)

    set_uv(bm, east_uv)
    pc = Piece(PREFIX + "Glass_East", bm, ["MAT_Glass"],
               note="C1-2 window: two cusped lights (144 wide, Z 0..465 = world 310..775) + quatrefoil O90 at Z 480 (world 790); 1:2 atlas UVs; NoCollision")
    pc.keep_uv = True
    return pc


# ---------------------------------------------------------------------------------------------- cobwebs
def grid_quad(p00, p10, p11, p01, nu, nv, sag=None, jit=None):
    b = bmesh.new()
    vs = []
    for j in range(nv + 1):
        row = []
        for i in range(nu + 1):
            u, v = i / nu, j / nv
            P = [(1 - u) * (1 - v) * p00[k] + u * (1 - v) * p10[k] + u * v * p11[k] + (1 - u) * v * p01[k] for k in range(3)]
            if sag:
                d = sag(u, v)
                P = [P[0] + d[0], P[1] + d[1], P[2] + d[2]]
            row.append(b.verts.new(P))
        vs.append(row)
    for j in range(nv):
        for i in range(nu):
            f = b.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    return b


def build_cobweb_corner():
    s = 120.0
    h = 120.0
    parts = []
    ba = grid_quad((-60, -60, 0), (60, -60, 0), (60, -60, h), (-60, -60, h), 6, 6, sag=lambda u, v: (0, 4.0 * math.sin(math.pi * u) * math.sin(math.pi * v), 0))
    bb = grid_quad((-60, -60, 0), (-60, 60, 0), (-60, 60, h), (-60, -60, h), 6, 6, sag=lambda u, v: (4.0 * math.sin(math.pi * u) * math.sin(math.pi * v), 0, 0))
    bc = grid_quad((-60, -60, h), (60, -60, h), (35, 35, h - 25.0), (-60, 60, h), 8, 8, sag=lambda u, v: (0, 0, -22.0 * math.sin(math.pi * u) * math.sin(math.pi * v)))
    for b in (ba, bb, bc):
        parts.append(b)
    bm = join(parts)
    uvs = {}
    # per-quad UV 0..1: derive from the original grid order (faces were created in grid order per quad)
    uv = bm.loops.layers.uv.new("UVMap")
    nf = [(36, 6, 6), (36, 6, 6), (64, 8, 8)]
    idx = 0
    bm.faces.ensure_lookup_table()
    for (cnt, nu, nv) in nf:
        for k in range(cnt):
            j, i = divmod(k, nu)
            f = bm.faces[idx + k]
            for l, (du, dv) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                l[uv].uv = ((i + du) / nu, (j + dv) / nv)
        idx += cnt
    pc = Piece(PREFIX + "Cobweb_Corner_A", bm, ["MAT_Cobweb"],
               note="two 120 x 120 quads meeting at 90 deg (wall planes Y -60 and X -60; the vertical corner edge is at local (-60,-60)) + a sagging third quad over the top edges; UV 0..1 per quad; two-sided material; NoCollision")
    pc.keep_uv = True
    return pc


def build_cobweb_hang():
    rng = random.Random(9961)
    W, Hh = 150.0, 80.0
    nu, nv = 10, 4
    b = bmesh.new()
    vs = []
    for j in range(nv + 1):
        row = []
        for i in range(nu + 1):
            u, v = i / nu, j / nv
            x = -W / 2 + W * u
            z = Hh * (1.0 - v)
            if j == nv:
                z = rng.choice((0.0, 4.0, 9.0, 14.0, 2.0))                      # ragged lower edge
            y = 12.0 * math.sin(math.pi * u) * (1.0 - 0.45 * v)
            row.append(b.verts.new((x, y, z)))
        vs.append(row)
    for j in range(nv):
        for i in range(nu):
            b.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    uv = b.loops.layers.uv.new("UVMap")
    b.faces.ensure_lookup_table()
    for k, f in enumerate(b.faces):
        j, i = divmod(k, nu)
        for l, (du, dv) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            l[uv].uv = ((i + du) / nu, 1.0 - (j + dv) / nv)
    zmin = min(v.co.z for v in b.verts)
    for v in b.verts:
        v.co.z -= zmin
    mx = max(v.co.z for v in b.verts)
    for v in b.verts:
        v.co.z *= Hh / mx
    pc = Piece(PREFIX + "Cobweb_Hang_A", b, ["MAT_Cobweb"], note="150 x 80 sagging sheet (hangs from its top edge, Y sag 12), ragged lower edge; UV 0..1; two-sided material; NoCollision")
    pc.keep_uv = True
    return pc


# ---------------------------------------------------------------------------------------------- pricket stands, flame
def build_pricket_small():
    prof = [(4.6, 0.0), (4.6, 0.9), (1.4, 1.4), (0.9, 2.2), (0.9, 8.0), (1.9, 9.0), (1.9, 10.0), (0.9, 11.0), (0.9, 20.0), (1.7, 21.5),
            (2.4, 23.5), (5.0, 27.4), (5.0, 28.4), (4.3, 28.7), (1.2, 27.8), (0.45, 28.0), (0.0, 30.0)]
    b = K.lathe_z(prof, 14, 0)
    return Piece(PREFIX + "PricketStand_Small_10x30", b, ["MAT_Iron"], ucx_design=[K.box_hull(-5.0, 5.0, -5.0, 5.0, 0.0, 30.0)],
                 note="C1-4: iron pricket for the puzzle candle Stand: 10 x 10 x 30 envelope (foot disc, stem with knops, drip dish, central pricket tip at Z 30); UCX box 10 x 10 x 30")


def build_pricket_150():
    parts = []
    shaft = K.lathe_z([(1.5, 18.0), (1.5, 40.0), (2.6, 41.5), (2.6, 43.5), (1.5, 45.0), (1.5, 78.0), (2.8, 80.0), (2.8, 83.0), (1.5, 85.0),
                       (1.5, 112.0), (2.6, 113.5), (2.6, 115.5), (1.5, 117.0), (1.5, 132.0), (0.0, 134.0)], 12, 0)
    parts.append(shaft)
    pan = K.lathe_z([(1.5, 132.0), (6.0, 133.4), (13.0, 134.6), (15.0, 135.2), (15.0, 137.0), (14.2, 137.0), (14.2, 136.0), (3.0, 135.8), (1.5, 135.8)], 24, 0,
                    cap_bottom=False, cap_top=False, closed=True)
    parts.append(pan)
    for k in range(3):
        a = math.radians(90.0 + 120.0 * k)
        rc = 22.0 / math.sqrt(3.0)
        pk = K.lathe_z([(1.7, 135.8), (1.7, 138.0), (0.8, 138.5), (0.5, 139.0), (0.0, 150.0)], 8, 0)
        shift(pk, rc * math.cos(a), rc * math.sin(a), 0.0)
        parts.append(pk)
    # tripod legs: curved tubes from the shaft (z 28) out to feet at radius 22.5, small foot pads
    for k in range(3):
        a = math.radians(90.0 + 120.0 * k)
        ca, sa = math.cos(a), math.sin(a)
        pts = []
        for i in range(9):
            t = i / 8.0
            r = 1.0 + 21.5 * (t ** 1.6)
            z = 1.0 + 29.0 * (1.0 - t) ** 1.35
            pts.append(Vector((r * ca, r * sa, z)))
        leg = bmesh.new()
        add_tube(leg, pts, [1.0] * 9, 6, 0, uvscale=50.0)
        parts.append(leg)
        pad = K.cylinder(1.5, 1.0, 8, 0)
        shift(pad, 22.5 * ca, 22.5 * sa, 0.0)
        parts.append(pad)
    bm = join(parts)
    return Piece(PREFIX + "PricketStand_150", bm, ["MAT_Iron"], ucx_fixed=(30.0, 30.0, 150.0),
                 note="C1-5: wrought-iron floor pricket: tripod feet at radius 22.5 (angles 90/210/330 deg; the shaft is 5.6 cm off the bbox centre in Y), shaft O3, drip pan O30 at Z 133..137, "
                      "3 prickets on a 22 cm triangle (radius 12.7, same angles) tips at Z 150; UCX 30 x 30 x 150")


def build_candle_flame():
    prof = [(0.0, 0.0), (0.55, 0.25), (1.0, 0.7), (1.38, 1.3), (1.5, 1.9), (1.38, 2.7), (1.05, 3.7), (0.65, 4.8), (0.28, 5.8), (0.0, 6.5)]
    b = K.lathe_z(prof, 10, 0)
    return Piece(PREFIX + "CandleFlame_A", b, ["MAT_Flame"], note="C1-6 teardrop 3 x 3 x 6.5 cm (matches the puzzle candles' flame look); NoCollision")


# ==============================================================================================
# P8-9a light-shaft cards (plan amendment C4).  Open tubes extruded OBLIQUELY along the moon direction d, from a window /
# roof-hole outline shrunk 5 % toward its centroid.  Pivot is NOT bottom-centre (seat_mode "none"), see each builder.
# UV0: U = 0..1 around the outline (arc length, seam duplicated by per-loop UVs), V = 0 at the opening -> 1 at the far end.
# ==============================================================================================
MAT_COLORS.update({"MAT_LightShaft": (0.75, 0.80, 0.95, 1.0)})

MOON_PITCH, MOON_YAW = -38.0, 35.0           # /Game/LastBell/Maps/L_Monastery DirectionalLight_1 (read from the editor, P8-9a)
ROOF_S1_LOC = (7000.0, 0.0, 2165.0)          # Ch_Roof_S1 (StaticMeshActor_766): world location ...
ROOF_S1_ROT = (0.0, 180.0, 50.0)             # ... and (pitch, yaw, roll) as read from the editor
ROOF_HOLE_SEED = 441                         # build_roof_slab default seed (hole_cutters(seed))
ROOF_HOLE_Z = 12.0                           # slab-local Z of the outline plane (the through-hole is cut Z -1..13, the slate skin 11..21)
SHAFT_SHRINK = 0.05


def moon_dir():
    p, y = math.radians(MOON_PITCH), math.radians(MOON_YAW)
    return Vector((math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p)))


def ue_axes(pitch, yaw, roll):
    """Unreal FRotationMatrix axes (local X, Y, Z in world) for a rotator in degrees."""
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    sy, cy = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    sr, cr = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    return (Vector((cp * cy, cp * sy, sp)),
            Vector((sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp)),
            Vector((-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp)))


def poly_centroid(p):
    a = cx = cy = 0.0
    for i in range(len(p)):
        x0, y0 = p[i]
        x1, y1 = p[(i + 1) % len(p)]
        c = x0 * y1 - x1 * y0
        a += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    return (cx / (3.0 * a), cy / (3.0 * a))


def shrink_poly(p, f=SHAFT_SHRINK):
    c = poly_centroid(p)
    return [(c[0] + (x - c[0]) * (1.0 - f), c[1] + (y - c[1]) * (1.0 - f)) for (x, y) in p]


def _dp_open(pts, tol):
    if len(pts) < 3:
        return pts[:]
    a, b = pts[0], pts[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    ln = math.hypot(dx, dy) or 1e-9
    k, dm = 0, -1.0
    for i in range(1, len(pts) - 1):
        d = abs((pts[i][0] - a[0]) * dy - (pts[i][1] - a[1]) * dx) / ln
        if d > dm:
            k, dm = i, d
    if dm <= tol:
        return [a, b]
    return _dp_open(pts[:k + 1], tol)[:-1] + _dp_open(pts[k:], tol)


def simplify_closed(poly, max_verts=16, min_verts=10):
    """Douglas-Peucker on a closed polygon; the tolerance is bisected to the largest vertex count <= max_verts."""
    n = len(poly)
    i0 = 0
    i1 = max(range(n), key=lambda i: math.hypot(poly[i][0] - poly[i0][0], poly[i][1] - poly[i0][1]))
    a, b = (i0, i1) if i0 < i1 else (i1, i0)

    def run(tol):
        h1 = _dp_open(poly[a:b + 1], tol)
        h2 = _dp_open(poly[b:] + poly[:a + 1], tol)
        return h1[:-1] + h2[:-1]

    lo, hi = 0.0, 200.0
    best = run(hi)
    for _ in range(40):
        mid = (lo + hi) * 0.5
        r = run(mid)
        if len(r) <= max_verts:
            best, hi = r, mid
        else:
            lo = mid
    assert min_verts <= len(best) <= max_verts, len(best)
    return best


def build_shaft(name, ring, d, length, segs, note):
    """Open single-sided tube: ring (closed outline, list of 3D Vectors, the section at t = 0) swept along d to t = length.
    Normals point away from the axis; UV0 as described above."""
    n = len(ring)
    nrm = Vector((0.0, 0.0, 0.0))
    for i in range(n):
        nrm += ring[i].cross(ring[(i + 1) % n])
    flip = nrm.dot(d) < 0.0                                    # face (a_i, a_j, b_j, b_i) has normal ~ edge x d
    per = [(ring[(i + 1) % n] - ring[i]).length for i in range(n)]
    tot = sum(per)
    ucum = [0.0]
    for s in per:
        ucum.append(ucum[-1] + s / tot)
    ucum[-1] = 1.0
    b = bmesh.new()
    rows = [[b.verts.new(p + d * (length * j / segs)) for p in ring] for j in range(segs + 1)]
    uv = b.loops.layers.uv.new("UVMap")
    for j in range(segs):
        v0, v1 = j / segs, (j + 1) / segs
        for i in range(n):
            k = (i + 1) % n
            vs = [rows[j][i], rows[j][k], rows[j + 1][k], rows[j + 1][i]]
            us = [(ucum[i], v0), (ucum[i + 1], v0), (ucum[i + 1], v1), (ucum[i], v1)]
            if flip:
                vs, us = vs[::-1], us[::-1]
            f = b.faces.new(vs)
            f.material_index = 0
            for l, t in zip(f.loops, us):
                l[uv].uv = t
    bmesh.ops.triangulate(b, faces=b.faces[:], quad_method='BEAUTY')
    pc = Piece(PREFIX + name, b, ["MAT_LightShaft"], note=note)
    pc.keep_uv = True
    pc.seat_mode = "none"
    pc.smooth = 60.0
    return pc


def build_lightshaft_lancet():
    d = moon_dir()
    poly = shrink_poly(lancet_poly(140.0, 560.0))
    ring = [Vector((x, 0.0, z)) for (x, z) in poly]            # window plane = local XZ at Y 0 (interior +Y), yaw 0 at the south windows
    return build_shaft("LightShaft_Lancet", ring, d, 1800.0, 12,
                       "C4: south lancet clear outline (140 x 560, shrunk 5 %% toward its centroid) swept obliquely along the moon direction d=(%.4f, %.4f, %.4f) "
                       "to t = 1800 (12 segments); open ends, single-sided, normals outward; UV U around / V 0 (window) -> 1; PIVOT = outline bottom-centre at the window plane; NoCollision" % tuple(d))


def roof_hole_outline():
    """Aperture of RoofSlab_Broken's hole in slab-local (x, y): the through-hole (boards) intersected with the slate-skin cut, via an exact boolean."""
    import build_kit as BK
    cut = BK.hole_cutters(ROOF_HOLE_SEED)
    p1 = [(v.co.x, v.co.y) for v in cut.verts if abs(v.co.z - 13.0) < 1e-4]
    p2 = [(v.co.x, v.co.y) for v in cut.verts if abs(v.co.z - 11.0) < 1e-4]
    cut.free()
    a = K.prism(p1, 'z', 0.0, 2.0, 1)
    c = K.prism(p2, 'z', 0.0, 2.0, 1)
    res = bool_op(a, c, 'INTERSECT')
    a.free()
    c.free()
    res.normal_update()
    res.verts.index_update()
    top = [f for f in res.faces if f.normal.z > 0.99 and abs(f.calc_center_median().z - 2.0) < 1e-3]
    tset = set(top)
    nxt = {}
    for e in res.edges:
        lf = [f for f in e.link_faces if f in tset]
        if len(lf) == 1:
            f = lf[0]
            for l in f.loops:
                if l.edge == e:
                    nxt.setdefault(l.vert.index, []).append(l.link_loop_next.vert.index)
    loops, used = [], set()
    for s in list(nxt):
        if s in used:
            continue
        loop, cur = [], s
        while cur not in used:
            used.add(cur)
            loop.append(cur)
            cur = nxt[cur][0]
        loops.append(loop)
    res.verts.ensure_lookup_table()
    polys = [[(res.verts[i].co.x, res.verts[i].co.y) for i in lp] for lp in loops]
    res.free()
    best = max(polys, key=lambda p: abs(K.poly_area(p)))
    if K.poly_area(best) < 0:
        best = best[::-1]
    return best, p1, p2


def build_lightshaft_roofhole():
    d = moon_dir()
    full, p1, p2 = roof_hole_outline()
    simp = simplify_closed(full, 16, 10)
    shr = shrink_poly(simp)
    cen = poly_centroid(simp)
    xa, ya, za = ue_axes(*ROOF_S1_ROT)
    loc = Vector(ROOF_S1_LOC)

    def to_world(x, y):
        return loc + xa * x + ya * y + za * ROOF_HOLE_Z

    pivot = to_world(cen[0], cen[1])
    ring = [to_world(x, y) - pivot for (x, y) in shr]
    print("ROOFHOLE slab-local outline: full %d verts area %.0f, simplified %d verts area %.0f, centroid (%.2f, %.2f); pivot world (%.2f, %.2f, %.2f)"
          % (len(full), abs(K.poly_area(full)), len(simp), abs(K.poly_area(simp)), cen[0], cen[1], pivot.x, pivot.y, pivot.z))
    pc = build_shaft("LightShaft_RoofHole", ring, d, 3000.0, 16,
                     "C4: RoofSlab_Broken hole aperture (boards cut and slate cut, %d verts, shrunk 5 %%) in WORLD orientation for Ch_Roof_S1 (loc %s, rot %s), swept along "
                     "d=(%.4f, %.4f, %.4f) to t = 3000 (16 segments); open ends, single-sided, normals outward; PIVOT = outline centroid = world (%.2f, %.2f, %.2f), place with ZERO rotation; NoCollision"
                     % (len(simp), ROOF_S1_LOC, ROOF_S1_ROT, d.x, d.y, d.z, pivot.x, pivot.y, pivot.z))
    pc.pivot_world = tuple(pivot)
    return pc


# ==============================================================================================
# P9-3 crypt pieces (plan Docs/plans/P9_CRYPT_ART.md amendment D1.3).  Prefix SM_LB_Crypt_ (the crank: SM_LB_Prop_).
# FBX go to <out>/Crypt/.  Pivots are stated per piece (see the notes in props_report_P9.json and the README).
# ==============================================================================================
CRYPT = "SM_LB_Crypt_"
CRYPT_SUB = "Crypt"


def crypt_piece(name, bm, slots, **kw):
    pc = Piece(name, bm, slots, **kw)
    pc.subdir = CRYPT_SUB
    return pc


def fit_box(bm, mn_t, mx_t):
    """Affine per-axis fit of the current bounds onto the target box (small corrections only: weathering shrinks the bounds)."""
    mn, mx = bounds(bm)
    sc = [(mx_t[i] - mn_t[i]) / (mx[i] - mn[i]) if (mx[i] - mn[i]) > 1e-9 else 1.0 for i in range(3)]
    for v in bm.verts:
        for i in range(3):
            v.co[i] = mn_t[i] + (v.co[i] - mn[i]) * sc[i]
    return sc


def top_edge(z_top, tol=0.01):
    return lambda e: all(v.co.z > z_top - tol for v in e.verts)


def bottom_edge(z_bot, tol=0.01):
    return lambda e: all(v.co.z < z_bot + tol for v in e.verts)


def chamfer(bm, edge_filter, off):
    edges = [e for e in bm.edges if edge_filter(e)]
    if edges:
        bmesh.ops.bevel(bm, geom=edges, offset=off, offset_type='OFFSET', profile=0.5, segments=1, affect='EDGES',
                        clamp_overlap=True, loop_slide=True)
    return bm


def rr_poly(x0, x1, z0, z1, r, n=3):
    """Rounded-rectangle outline (counter-clockwise) with corner radius r."""
    pts = []
    for (cx, cz, a0) in ((x1 - r, z1 - r, 0.0), (x0 + r, z1 - r, 90.0), (x0 + r, z0 + r, 180.0), (x1 - r, z0 + r, 270.0)):
        for k in range(n + 1):
            a = math.radians(a0 + 90.0 * k / n)
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def gbox(x0, x1, y0, y1, z0, z1, cell, mat=0):
    """Closed box whose six faces are a regular quad lattice of about `cell` cm (kit_lib.lattice_box): clean, sliver-free geometry for booleans and weathering."""
    nx, ny, nz = (max(1, int(round((hi - lo) / cell))) for lo, hi in ((x0, x1), (y0, y1), (z0, z1)))
    b = K.lattice_box(x1 - x0, y1 - y0, z1 - z0, nx, ny, nz, mat)
    shift(b, x0, y0, z0)
    return b


def dissolve_flat(bm, pred):
    """Merge every face whose vertices all satisfy pred(co) into single n-gons per connected patch (hidden flat faces: back, bottom)."""
    faces = [f for f in bm.faces if all(pred(v.co) for v in f.verts)]
    if faces:
        bmesh.ops.dissolve_faces(bm, faces=faces, use_verts=True)
    return bm


def stone_pass(bm, seed, dens, amp, wob, f1=1.0 / 18.0, f2=1.0 / 5.0, mask=bottom_mask, region=None):
    if dens:
        densify(bm, dens, region=region)
    weather(bm, seed, amp, mask, f1=f1, f2=f2)
    if wob > 0:
        warp(bm, seed + 3, wob)
    return bm


# ---------------------------------------------------------------------------------------------- A: ossuary bay
def build_c_bay():
    rng = random.Random(9301)
    body = gbox(-250.0, 250.0, -90.0, 0.0, 0.0, 599.0, 13.0)
    dissolve_flat(body, lambda c: c.y < -89.99)                                  # hidden back
    dissolve_flat(body, lambda c: c.z < 0.01)                                    # bottom
    niches = ((45.0, 135.0), (185.0, 275.0))
    cutters = []
    for (z0, z1) in niches:                                      # niche cutters: gridded boxes, the 4 Y-parallel corner lines rounded r 2
        c = gbox(-170.0, 170.0, -60.0, 10.0, z0, z1, 12.0)
        corner = lambda e, z0=z0, z1=z1: all(abs(abs(v.co.x) - 170.0) < 1e-3 and (abs(v.co.z - z0) < 1e-3 or abs(v.co.z - z1) < 1e-3) for v in e.verts)
        edges = [e for e in c.edges if corner(e)]
        bmesh.ops.bevel(c, geom=edges, offset=2.0, offset_type='OFFSET', profile=0.5, segments=2, affect='EDGES', clamp_overlap=True)
        cutters.append(c)
    cuts = join(cutters)
    body = bool_op(body, cuts, 'DIFFERENCE', 1)
    cuts.free()
    spots = []
    for (z0, z1) in niches:                                      # 3-5 chips on each niche rim
        for _ in range(rng.randint(3, 5)):
            e = rng.randint(0, 3)
            if e == 0:
                p = (-170.0, rng.uniform(z0 + 6, z1 - 6))
            elif e == 1:
                p = (170.0, rng.uniform(z0 + 6, z1 - 6))
            elif e == 2:
                p = (rng.uniform(-160.0, 160.0), z1)
            else:
                p = (rng.uniform(-160.0, 160.0), z0)
            spots.append(((p[0], 0.0, p[1]), rng.uniform(2.6, 4.6)))
    body = cut_chips(body, rng, spots, 0)

    def band(x0, x1, z0, z1, depth, off=1.5):
        b = gbox(x0, x1, -3.0, depth, z0, z1, 12.0)
        chamfer(b, top_edge(z1), off)
        return b

    parts = [body, band(-250.0, 250.0, 0.0, 40.0, 4.0)]                         # plinth band (proud 4)
    for z0 in (39.0, 179.0):
        parts.append(band(-185.0, 185.0, z0, z0 + 6.0, 6.0))                    # sill bands (proud 6)
    for z0 in (135.0, 275.0):
        parts.append(band(-190.0, 190.0, z0, z0 + 12.0, 6.0))                   # lintel bands (proud 6)
    bm = join(parts)
    for p in parts:
        p.free()
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    weather(bm, 9301, 1.2, lambda co, n: 0.0 if (co.z < 0.02 or co.z > 598.9 or co.y < -89.0 or abs(co.x) > 249.9) else 1.0, f1=1 / 30.0, f2=1 / 13.0)
    warp(bm, 9304, 0.5, f=1 / 60.0)
    fit_box(bm, (-250.0, -90.0, 0.0), (250.0, 6.0, 599.0))
    pc = crypt_piece(CRYPT + "OssuaryBay_500x599", bm, ["MAT_Stone"],
                     note="x centre, y 0 = the wall's front face (local +Y into the room), z 0 bottom; body y -90..0, bands proud to +6; two niches x +-170 "
                          "(tier 1 z 45..135, tier 2 z 185..275) recessed to y -60; chips 3-5 per niche rim")
    pc.seat_mode = "none"
    return pc


# ---------------------------------------------------------------------------------------------- B: capital
def build_c_capital():
    rng = random.Random(9302)
    zs = (0.0, 11.0, 22.0, 33.0)
    aps = (70.0, 71.6, 76.2, 84.0)                                   # apothem: concave flare 70 -> 84
    b = bmesh.new()
    rings = []
    for z, a in zip(zs, aps):
        R = a / math.cos(math.radians(22.5))
        rings.append([b.verts.new((R * math.cos(math.radians(22.5 + 45.0 * k)), R * math.sin(math.radians(22.5 + 45.0 * k)), z)) for k in range(8)])
    b.faces.new(rings[0][::-1])
    b.faces.new(rings[-1])
    for i in range(3):
        for k in range(8):
            k2 = (k + 1) % 8
            b.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    K.bm_set_mat(b, 0)
    aba = gbox(-85.0, 85.0, -85.0, 85.0, 33.0, 55.0, 21.0)
    chamfer(aba, bottom_edge(33.0), 4.0)
    chamfer(aba, top_edge(55.0), 1.5)
    spots = [((85.0, 85.0, 55.0), 5.0), ((-85.0, 85.0, 55.0), 4.0), ((85.0, -85.0, 55.0), 4.5), ((-85.0, -85.0, 33.0), 4.5)]
    spots += [((rng.uniform(-60, 60), 85.0, 55.0), 3.0), ((85.0, rng.uniform(-60, 60), 55.0), 3.2)]
    aba = cut_chips(aba, rng, spots, 0)
    bmesh.ops.triangulate(aba, faces=aba.faces[:])
    densify(b, 24.0)
    weather(aba, 9302, 0.9, lambda co, n: 0.0 if co.z < 0.02 else 1.0, f1=1 / 22.0, f2=1 / 9.0)
    weather(b, 9303, 0.9, lambda co, n: 0.0 if co.z < 0.02 else 1.0, f1=1 / 22.0, f2=1 / 9.0)
    bm = join([b, aba])
    b.free()
    aba.free()
    fit_box(bm, (-85.0, -85.0, 0.0), (85.0, 85.0, 55.0))
    return crypt_piece(CRYPT + "Capital_A", bm, ["MAT_Stone"],
                       note="bottom-centre; octagonal bell (flats to +-X/+-Y, apothem 70 -> 84 over z 0..33, 4 rings, concave) under a 170 x 170 abacus z 33..55 "
                            "(bottom chamfer 4, top 1.5); chips seed 9302")


# ---------------------------------------------------------------------------------------------- C: stair
def stair_profile():
    """Closed XZ outline of the 40-step flight: list of (x, z, kind, dip_xrel) -- kind 'T' = tread point (gets the wear dip)."""
    pts = [(0.0, 0.0, 'B', 0.0)]
    tread = (6.0, 10.0, 13.0, 15.0, 17.0, 20.0, 25.0, 30.0)
    for n in range(40):
        x0, zt = 30.0 * n, 15.0 * (n + 1)
        cx, cz = x0 + 2.5, zt - 2.5
        for ang in (180.0, 150.0, 120.0, 90.0):
            a = math.radians(ang)
            pts.append((cx + 2.5 * math.cos(a), cz + 2.5 * math.sin(a), 'N', 0.0))
        for t in tread:
            pts.append((x0 + t, zt, 'T', t / 30.0))
    pts.append((1200.0, 0.0, 'B', 0.0))
    return pts


def build_c_stair():
    rng = random.Random(9303)
    prof = stair_profile()
    ys = [-150.0 + 300.0 * j / 16.0 for j in range(17)]
    b = bmesh.new()
    grid = []
    for (x, z, kind, xr) in prof:
        row = []
        for y in ys:
            zz = z
            if kind == 'T':
                u = (xr - 1.0 / 3.0) * 3.0
                bump = math.sin(math.pi * u) ** 2 if 0.0 < u < 1.0 else 0.0
                yb = 1.0 - K.smoothstep(50.0, 130.0, abs(y))
                zz = z - 0.7 * bump * yb
            row.append(b.verts.new((x, y, zz)))
        grid.append(row)
    m = len(prof)
    for i in range(m):
        i2 = (i + 1) % m
        for j in range(16):
            b.faces.new((grid[i][j], grid[i][j + 1], grid[i2][j + 1], grid[i2][j]))
    b.faces.new([grid[i][0] for i in range(m)])
    b.faces.new([grid[i][16] for i in range(m)][::-1])
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    K.bm_set_mat(b, 0)
    # chipped nosings (25 % of 40 = 10): 6..14 wide, 2..3 deep; cut with small hulls at the nosing corner
    chips = rng.sample(range(40), 10)
    spots = []
    for n in sorted(chips):
        w = rng.uniform(6.0, 14.0)
        d = rng.uniform(2.0, 3.0)
        r = w / 2.0
        yc = rng.uniform(-135.0, 135.0)
        cx, cz = 30.0 * n + 0.7, 15.0 * (n + 1) - 0.7
        off = (r - d) * 0.9
        spots.append(((cx - 0.7071 * off, yc, cz + 0.7071 * off), r))
    b = cut_chips(b, rng, spots, 0)
    weather(b, 9303, 0.35, bottom_mask, f1=1 / 12.0, f2=1 / 4.0)
    fit_box(b, (0.0, -150.0, 0.0), (1200.0, 150.0, 600.0))
    return _stair_piece(b, sorted(chips))


def _stair_piece(b, chips):
    pc = crypt_piece(CRYPT + "Stair40_300", b, ["MAT_Stone"],
                     note="x 0 = riser face of step 0 (+X up the flight), y centre, z 0 floor; step n tread x 30n..30n+30, top z 15(n+1); wear dip 0.7 max at the "
                          "centre third (ray at x 30n+15 hits 15(n+1) - 0.5..1.1); nosing r 2.5; 10 of 40 nosings chipped (steps %s)" % chips)
    pc.seat_mode = "none"
    return pc


# ---------------------------------------------------------------------------------------------- D: sarcophagi
def sarco_panels():
    """Cutters for the 2 cm recessed round-headed panels (44 x 32; 5 per long side, 2 per short side)."""
    def head(w, h, z0, r):
        pts = [(-w / 2, z0), (w / 2, z0), (w / 2, z0 + h - r)]
        for k in range(1, 8):
            a = math.pi * k / 8.0
            pts.append(((w / 2) * math.cos(a), z0 + h - r + r * math.sin(a)))
        pts.append((-w / 2, z0 + h - r))
        return pts
    out = []
    pr = head(44.0, 32.0, 17.0, 22.0)
    for s in (-1, 1):
        for xc in (-116.0, -58.0, 0.0, 58.0, 116.0):
            pl = K.prism([(xc + p, z) for p, z in pr], 'y', (55.0 - 2.0) if s > 0 else -56.0, 56.0 if s > 0 else -(55.0 - 2.0), 0)
            out.append(pl)
        for yc in (-27.5, 27.5):
            pl = K.prism([(yc + p, z) for p, z in pr], 'x', (145.0 - 2.0) if s > 0 else -146.0, 146.0 if s > 0 else -(145.0 - 2.0), 0)
            out.append(pl)
    return join(out)


def build_c_sarcophagus(variant):
    rng = random.Random(9304)
    ajar = variant == "B"
    plinth = gbox(-150.0, 150.0, -60.0, 60.0, 0.0, 8.0, 12.0)
    chamfer(plinth, top_edge(8.0), 1.5)
    body = gbox(-145.0, 145.0, -55.0, 55.0, 6.0, 59.0, 12.0)
    cut = sarco_panels()
    body = bool_op(body, cut, 'DIFFERENCE', 2)
    cut.free()
    if ajar:
        cav = gbox(-135.0, 135.0, -45.0, 45.0, 20.0, 61.0, 12.0, 1)             # open at the top, Charred inside
        body = bool_op(body, cav, 'DIFFERENCE', 2)
        cav.free()
    # lid + raised cross
    LW, LL = (104.0, 280.0) if ajar else (120.0, 300.0)
    lid = gbox(-LL / 2, LL / 2, -LW / 2, LW / 2, 58.0, 70.0, 12.0)
    chamfer(lid, top_edge(70.0), 3.0)
    cross = [gbox(-95.0, 95.0, -7.0, 7.0, 69.0, 72.0, 10.0), gbox(43.0, 57.0, -35.0, 35.0, 69.0, 72.0, 10.0)]
    if ajar:                                                             # one lid corner broken off (+X,-Y) -- keep it in the chipped end
        lid = cut_chips(lid, rng, [((LL / 2, -LW / 2, 70.0), 6.0), ((-LL / 2, LW / 2, 70.0), 3.5)], 0)
    cr = join(cross)
    for c in cross:
        c.free()
    lidp = join([lid, cr])
    lid.free()
    cr.free()
    # weather each solid
    for bmx, sd in ((plinth, 9304), (body, 9314), (lidp, 9324)):
        bmesh.ops.triangulate(bmx, faces=bmx.faces[:])
        weather(bmx, sd, 0.9, bottom_mask, f1=1 / 24.0, f2=1 / 9.0)
    if ajar:
        sx, ang = 7.0, math.radians(3.0)
        rot(lidp, 'Z', 3.0)
        shift(lidp, sx, 0.0, 0.0)
    bm = join([plinth, body, lidp])
    for p in (plinth, body, lidp):
        p.free()
    if not ajar:
        fit_box(bm, (-150.0, -60.0, 0.0), (150.0, 60.0, 72.0))
    note = ("bottom-centre; plinth z 0..8 300 x 120, body z 8..58 290 x 110 with 14 recessed round-headed panels (5 per long side, 2 per short side), lid z 58..70 "
            "300 x 120 (top edges chamfer 3), raised cross z 70..72 (shaft 190 x 14 along X, arms 70 x 14 at x +50)")
    if ajar:
        note = ("bottom-centre; as _A but the lid is 280 x 104 (D1.3 says 280 x 120: a 3 deg rotation of 280 x 120 cannot stay inside y +-60), rotated 3 deg about Z and "
                "shifted +7 in X (D1.3 says +10: the rotated corner would exceed x 150); dark Charred cavity x +-135, y +-45, z 20..58 shows at the -X end; "
                "lid corners chipped (seed 9304)")
    pc = crypt_piece(CRYPT + "Sarcophagus_" + variant, bm, ["MAT_Stone", "MAT_Charred"] if ajar else ["MAT_Stone"], note=note)
    pc.seat_mode = "none"
    return pc


# ---------------------------------------------------------------------------------------------- E: bone bin
def build_c_bonebin():
    rng = random.Random(9305)
    b = gbox(-100.0, 100.0, -50.0, 50.0, 0.0, 60.0, 8.0)
    cut = gbox(-92.0, 92.0, -42.0, 42.0, 30.0, 61.0, 8.0)
    b = bool_op(b, cut, 'DIFFERENCE', 1)
    cut.free()
    chamfer(b, top_edge(60.0), 1.5)
    spots = [((-100.0, -50.0, 60.0), 5.0), ((100.0, 50.0, 60.0), 4.5), ((rng.uniform(-60, 60), 50.0, 60.0), 3.5), ((100.0, rng.uniform(-30, 30), 60.0), 3.5),
             ((-100.0, rng.uniform(-30, 30), 55.0), 3.0), ((rng.uniform(-60, 60), -50.0, 0.0), 4.0)]
    b = cut_chips(b, rng, spots, 0)
    bmesh.ops.triangulate(b, faces=b.faces[:])
    weather(b, 9305, 0.9, bottom_mask, f1=1 / 24.0, f2=1 / 9.0)
    warp(b, 9308, 0.5)
    fit_box(b, (-100.0, -50.0, 0.0), (100.0, 50.0, 60.0))
    return crypt_piece(CRYPT + "BoneBin_200x100x60", b, ["MAT_Stone"],
                       note="bottom-centre; open-top chest, walls 8 thick, solid to the inner floor at z 30, top edge chamfer 1.5, 6 chips (seed 9305)")


# ---------------------------------------------------------------------------------------------- F: block
def build_c_block(centre):
    rng = random.Random(9306)
    b = gbox(-50.0, 50.0, -50.0, 50.0, -50.0, 50.0, 7.0)
    chamfer(b, lambda e: e.calc_face_angle(0.0) > math.radians(60.0), 3.0)
    spots = [((50.0, 50.0, rng.uniform(-30, 30)), rng.uniform(5.0, 8.0)), ((rng.uniform(-30, 30), -50.0, 50.0), rng.uniform(5.0, 7.5)),
             ((-50.0, rng.uniform(-30, 30), -50.0), rng.uniform(5.0, 8.0))]
    b = cut_chips(b, rng, spots, 0)
    bmesh.ops.triangulate(b, faces=b.faces[:])
    weather(b, 9306, 1.0, lambda co, n: 1.0, f1=1 / 24.0, f2=1 / 8.0)
    fit_box(b, (-50.0, -50.0, -50.0), (50.0, 50.0, 50.0))
    pc = crypt_piece(CRYPT + ("Block_100_C" if centre else "Block_100"), b, ["MAT_Stone"], ucx_design=[ucx_box(-50.0, 50.0, -50.0, 50.0, -50.0, 50.0)],
                     note=("CENTRE pivot (bounds centre = origin)" if centre else "bottom-centre") + "; weathered 100 cm block, edge chamfer 3, face noise <= 1.0 inward, chips on 3 edges (seed 9306); UCX 1 box 100^3")
    pc.seat_mode = "centre3" if centre else "centre"
    return pc


# ---------------------------------------------------------------------------------------------- G: corbel
def build_c_corbel():
    rng = random.Random(9307)

    def course(z0, z1, depth):
        return gbox(-25.0, 25.0, 0.0, depth, z0, z1, 5.0)

    c1 = course(0.0, 16.5, 30.0)
    c2 = course(15.0, 31.5, 42.0)
    c3 = course(30.0, 45.0, 55.0)
    bm = bool_op(bool_op(c1, c2, 'UNION', 1), c3, 'UNION', 1)
    chamfer(bm, lambda e: not all(v.co.y < 0.01 for v in e.verts) and e.calc_face_angle(0.0) > math.radians(30), 1.5)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    weather(bm, 9307, 0.7, lambda co, n: 0.0 if (co.z < 0.02 or co.y < 0.02) else 1.0, f1=1 / 14.0, f2=1 / 6.0)
    fit_box(bm, (-25.0, 0.0, 0.0), (25.0, 55.0, 45.0))
    pc = crypt_piece(CRYPT + "Corbel_A", bm, ["MAT_Stone"],
                     note="back plane y 0, x centre, z 0 bottom, projects +Y; three stepped courses (z 0..15 depth 30, 15..30 depth 42, 30..45 depth 55), chamfer 1.5")
    pc.seat_mode = "wall"
    return pc


# ---------------------------------------------------------------------------------------------- H: beam
def build_c_beam():
    rng = random.Random(9307)
    b = K.box(-17.5, 17.5, -560.0, 560.0, 0.0, 45.0, 0, 0.8)
    grooves = []
    # 3 lengthwise checks (V grooves 1.4 wide, 2.4 deep): top face, +X face, -X face
    grooves.append(K.prism([(-4.7, 45.5), (-3.3, 45.5), (-4.0, 42.6)], 'y', -330.0, -120.0, 0))
    grooves.append(K.prism([(18.0, 24.3), (18.0, 25.7), (15.1, 25.0)], 'y', 60.0, 330.0, 0))
    grooves.append(K.prism([(-18.0, 16.3), (-18.0, 17.7), (-15.1, 17.0)], 'y', -90.0, 250.0, 0))
    g = join(grooves)
    b = bool_op(b, g, 'DIFFERENCE', 1)
    g.free()
    subdiv_long(b, 13.0)
    bmesh.ops.triangulate(b, faces=b.faces[:])
    weather(b, 9307, 0.6, lambda co, n: 0.0 if co.z <= 0.02 else 1.0, f1=1 / 26.0, f2=1 / 9.0)
    fit_box(b, (-17.5, -560.0, 0.0), (17.5, 560.0, 45.0))
    return crypt_piece(CRYPT + "Beam_35x45x1120", b, ["MAT_Wood"],
                       note="bottom-centre, length along Y; adzed faces (0.6 cm waviness), 3 lengthwise checks (top, +X, -X; seed 9307)")


# ---------------------------------------------------------------------------------------------- I: boards
def _board(xa, xb, y0, y1, rng, ragged_ends=(True, True), thick=5.0):
    """One board: XY outline with ragged ends (inset 0..2 cm), z 0..thick.  xa<xb along X, y0<y1 across."""
    n = 4
    left, right = [], []
    for k in range(n + 1):
        yy = y0 + (y1 - y0) * k / n
        left.append((xa + (rng.uniform(0.0, 2.0) if ragged_ends[0] else 0.0), yy))
        right.append((xb - (rng.uniform(0.0, 2.0) if ragged_ends[1] else 0.0), yy))
    poly = left + right[::-1]
    return poly


def build_c_boards(broken):
    rng = random.Random(9308 if not broken else 9308)
    n = 10
    gaps = [rng.uniform(1.0, 2.0) for _ in range(n - 1)]
    wsum = 250.0 - sum(gaps)
    raw = [rng.uniform(22.0, 27.0) for _ in range(n)]
    k = wsum / sum(raw)
    widths = [w * k for w in raw]
    bm = bmesh.new()
    ycur = -125.0
    boards = []
    for i in range(n):
        y0, y1 = ycur, ycur + widths[i]
        ycur = y1 + (gaps[i] if i < n - 1 else 0.0)
        boards.append((y0, y1))
    parts = []
    hinge_info = None
    for i, (y0, y1) in enumerate(boards):
        if broken and i in (2, 3):
            continue                                                       # boards 3 and 4 (1-based) missing
        sx0 = 1 if i == 0 or i == n - 1 else 0                              # outer boards reach the full +-150 / +-125
        a_bow = rng.uniform(0.0, 0.4)
        cup = rng.uniform(0.0, 0.2)
        ym = (y0 + y1) * 0.5
        hw = (y1 - y0) * 0.5

        def lift(co, a_bow=a_bow, cup=cup, ym=ym, hw=hw):
            return a_bow * (co.x / 150.0) ** 2 + cup * ((co.y - ym) / hw) ** 2

        if broken and i == 5:
            brk = 40.0
            polyL = _board(-150.0, brk, y0, y1, rng, (True, False))
            polyL = [(x, y) if j < 5 else (brk + rng.uniform(-2.0, 1.0), y) for j, (x, y) in enumerate(polyL)]
            polyR = _board(brk, 150.0, y0, y1, rng, (False, True))
            polyR = [(brk + rng.uniform(-1.0, 2.0), y) if j < 5 else (x, y) for j, (x, y) in enumerate(polyR)]
            bl = K.prism(polyL, 'z', 0.0, 5.0, 0)
            br = K.prism(polyR, 'z', 0.0, 5.0, 0)
            for bb in (bl, br):
                tri_ear(bb)
                subdiv_long(bb, 25.0)
                for v in bb.verts:
                    v.co.z += lift(v.co)
            rot_about(br, 'Y', 25.0, (brk, ym, 2.5))
            parts += [bl, br]
        else:
            poly = _board(-150.0, 150.0, y0, y1, rng)
            if i in (0, n - 1):                                           # make sure the full +-150 extent is reached
                poly[0] = (-150.0, poly[0][1])
                poly[-1] = (150.0, poly[-1][1])
                poly[5] = (150.0, poly[5][1])
                poly[4] = (-150.0, poly[4][1])
            bd = K.prism(poly, 'z', 0.0, 5.0, 0)
            tri_ear(bd)
            subdiv_long(bd, 25.0)
            for v in bd.verts:
                v.co.z += lift(v.co)
            K.bevel_all(bd, 0.35, 30.0)
            parts.append(bd)
    bm = join(parts)
    for p in parts:
        p.free()
    pc = crypt_piece(CRYPT + ("Boards_300x250_Broken" if broken else "Boards_300x250"), bm, ["MAT_Wood"],
                     note=("bottom-centre (z 0 = board undersides); 10 boards run along X (300 long) side by side along Y (widths 22-27, gaps 1-2, 250 total); "
                           "warp lift 0..0.6, ragged ends 0..2" + ("; boards 3 and 4 (1-based) missing, board 6 snapped at x +40 and its +X part hinged 25 deg down (lowest z about -47)" if broken else "")))
    pc.seat_mode = "xy" if broken else "centre"
    return pc


# ---------------------------------------------------------------------------------------------- J: hanging roots
def _root_tube(bm, uvl, pts, radii, sides, v0=0.0, cap_start=True, cap_end=True, vscale=60.0):
    """Tapered tube along a polyline; UV u = 0..1 around, v = arc length / 60 cm (1 bark tile per 60 cm)."""
    rings = []
    s_acc = [0.0]
    for i in range(1, len(pts)):
        s_acc.append(s_acc[-1] + (pts[i] - pts[i - 1]).length)
    prev = None
    for i, p in enumerate(pts):
        d = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        if d.length < 1e-6:
            d = Vector((0, 0, -1))
        d.normalize()
        ref = prev if prev is not None else (Vector((0, 1, 0)) if abs(d.y) < 0.9 else Vector((1, 0, 0)))
        x = ref - d * ref.dot(d)
        if x.length < 1e-6:
            x = d.orthogonal()
        x.normalize()
        y = d.cross(x)
        prev = x
        rings.append([bm.verts.new(p + (x * math.cos(2 * math.pi * k / sides) + y * math.sin(2 * math.pi * k / sides)) * radii[i]) for k in range(sides)])
    for i in range(len(pts) - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
            f.material_index = 0
            uvs = ((k / sides, (v0 + s_acc[i]) / vscale), ((k + 1) / sides, (v0 + s_acc[i]) / vscale),
                   ((k + 1) / sides, (v0 + s_acc[i + 1]) / vscale), (k / sides, (v0 + s_acc[i + 1]) / vscale))
            for l, uv in zip(f.loops, uvs):
                l[uvl].uv = uv
    for flag, ring, rev, vv in ((cap_start, rings[0], True, v0), (cap_end, rings[-1], False, v0 + s_acc[-1])):
        if flag:
            f = bm.faces.new(ring[::-1] if rev else ring)
            f.material_index = 0
            for l in f.loops:
                l[uvl].uv = (0.5, vv / vscale)
    return s_acc


def _walk(rng, p, d, length, step, jitter, grav):
    pts = [p.copy()]
    n = max(3, int(length / step))
    cur = d.normalized()
    for i in range(n):
        cur = (cur + Vector((rng.gauss(0, jitter), rng.gauss(0, jitter), rng.gauss(0, jitter * 0.5))) + Vector((0, 0, -grav))).normalized()
        pts.append(pts[-1] + cur * (length / n))
    return pts


def _gen_roots(seed, nstr, depth, drift_max, r0, sides, steps):
    rng = random.Random(seed)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    st1, st2, st3 = steps
    # knot: a 12 cm bulb hanging from z 0 (flat top = the attachment)
    kp = [Vector((0, 0, 0.0)), Vector((0, 0, -2.5)), Vector((0, 0, -6.0)), Vector((0, 0, -10.0)), Vector((0, 0, -14.0))]
    _root_tube(bm, uvl, kp, [6.4, 7.6, 7.4, 5.6, 3.4], max(14, sides), 0.0)
    az0 = rng.uniform(0, 2 * math.pi)
    for s in range(nstr):
        az = az0 + 2 * math.pi * (s + rng.uniform(-0.2, 0.2)) / nstr
        L = depth * (1.0 if s == 0 else rng.uniform(0.62, 0.96))
        drift = rng.uniform(0.5, 1.0) * drift_max
        sway = rng.uniform(3.0, 6.0)
        ph1, ph2 = rng.uniform(0, 2 * math.pi), rng.uniform(0, 2 * math.pi)
        fr = rng.uniform(0.8, 1.4)
        ex = Vector((math.cos(az), math.sin(az), 0))
        ey = Vector((-math.sin(az), math.cos(az), 0))
        n = max(8, int(L / st1))
        pts, radii = [], []
        rs = r0 * rng.uniform(0.85, 1.0)
        for i in range(n + 1):
            t = i / n
            lat = 3.2 * (1 - t) + drift * (t ** 1.15)
            sw = sway * math.sin(2 * math.pi * fr * t + ph1) * min(1.0, t * 2.5)
            sw2 = sway * 0.5 * math.sin(2 * math.pi * fr * 1.7 * t + ph2) * min(1.0, t * 2.5)
            pts.append(ex * (lat + sw2) + ey * sw + Vector((0, 0, -10.0 - (L - 10.0) * t)))
            radii.append(max(0.4, 0.4 + (rs - 0.4) * (1 - t) ** 1.25 * (1.0 + 0.1 * math.sin(11.0 * t + ph1))))
        radii[0] = rs * 1.1
        acc = _root_tube(bm, uvl, pts, radii, sides, rng.uniform(0, 1.0))
        # level 2: 2-4 branches 30-60 long, r 1.5 -> 0.3
        for b in range(rng.randint(2, 4)):
            i = int(rng.uniform(0.18, 0.8) * n)
            az2 = az + rng.uniform(-1.5, 1.5)
            d0 = Vector((math.cos(az2) * 0.85, math.sin(az2) * 0.85, -0.5))
            Lb = rng.uniform(30.0, 60.0)
            bp = _walk(rng, pts[i], d0, Lb, st2, 0.10, 0.10)
            m = len(bp) - 1
            r1 = min(1.5, max(0.7, radii[i] * 0.8))
            br = [max(0.3, 0.3 + (r1 - 0.3) * (1 - j / m) ** 1.1) for j in range(m + 1)]
            _root_tube(bm, uvl, bp, br, max(6, sides // 2), rng.uniform(0, 1.0))
            # level 3: rootlets 10-20 long, r 0.4 -> 0.15
            for q in range(rng.randint(0, 2)):
                j = int(rng.uniform(0.3, 0.9) * m)
                az3 = rng.uniform(0, 2 * math.pi)
                d3 = Vector((math.cos(az3) * 0.8, math.sin(az3) * 0.8, -0.6))
                Lr = rng.uniform(10.0, 20.0)
                rp = _walk(rng, bp[j], d3, Lr, st3, 0.08, 0.08)
                mm = len(rp) - 1
                rr_ = [0.15 + 0.25 * (1 - jj / mm) for jj in range(mm + 1)]
                _root_tube(bm, uvl, rp, rr_, 5, rng.uniform(0, 1.0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def build_c_roots(letter, seed, nstr, depth, xy_target, drift_max, r0, sides, steps):
    best = None
    for att in range(60):
        bm = _gen_roots(seed * 100 + att, nstr, depth, drift_max, r0, sides, steps)
        mn, mx = bounds(bm)
        sc = depth / (-mn[2])
        dx, dy = (mx[0] - mn[0]) * sc, (mx[1] - mn[1]) * sc
        off = math.hypot((mx[0] + mn[0]) * 0.5, (mx[1] + mn[1]) * 0.5) * sc
        score = abs(dx - xy_target) + abs(dy - xy_target) + off * 2.0
        if best is None or score < best[0]:
            if best is not None:
                best[1].free()
            best = (score, bm, sc, att)
        else:
            bm.free()
        if abs(dx - xy_target) < 8 and abs(dy - xy_target) < 8 and off < 5:
            break
    score, bm, sc, att = best
    for v in bm.verts:
        v.co *= sc
    pc = crypt_piece(CRYPT + "RootsHang_" + letter, bm, ["MAT_Bark"],
                     note="TOP-centre: z 0 = the attachment (flat top of the 12 cm knot), design axis on the origin, hangs to -%d; %d strands, seed %d attempt %d (scale %.3f); "
                          "UV u 0..1 around, v 1 tile / 60 cm along the length" % (depth, nstr, seed, att, sc))
    pc.seat_mode = "top"
    pc.keep_uv = True
    pc.smooth = 70.0
    return pc


# ---------------------------------------------------------------------------------------------- K: portcullis
def _spike_bar(xc, z_top, seed):
    b = bmesh.new()
    apex = b.verts.new((xc, 0.0, 0.0))
    r1 = [b.verts.new((xc + sx * 3.0, sy * 3.0, 12.0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    r2 = [b.verts.new((xc + sx * 3.0, sy * 3.0, z_top)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for i in range(4):
        j = (i + 1) % 4
        b.faces.new((apex, r1[j], r1[i]))
        b.faces.new((r1[i], r1[j], r2[j], r2[i]))
    b.faces.new(r2)
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    K.bm_set_mat(b, 0)
    subdiv_long(b, 22.0)
    bmesh.ops.triangulate(b, faces=b.faces[:])
    weather(b, seed, 0.22, bottom_mask, f1=1 / 26.0, f2=1 / 8.0)
    return b


def build_c_portcullis():
    parts = []
    for s in (-1, 1):                                              # side rails 8 x 8 (outer faces at x +-150)
        parts.append(lbeam(s * 146.0 - 4.0, s * 146.0 + 4.0, -4.0, 4.0, 0.0, 560.0, 9309 + s, 0, 0.7, 22.0, 0.22))
    bar_x = [-130.0 + 32.5 * k for k in range(9)]
    for k, xc in enumerate(bar_x):
        parts.append(_spike_bar(xc, 560.0, 9320 + k))
    flat_z = [60.0 + 70.0 * i for i in range(7)]
    for i, zc in enumerate(flat_z):
        parts.append(lbeam(-146.0, 146.0, -1.5, 1.5, zc - 4.0, zc + 4.0, 9340 + i, 0, 0.3, 22.0, 0.2))
    for s in (-1, 1):                                              # transverse guide pins: put the leaf in the 60 cm greybox footprint (y +-30)
        for zc in (70.0, 500.0):
            parts.append(lbeam(s * 146.0 - 3.0, s * 146.0 + 3.0, -30.0, 30.0, zc - 3.0, zc + 3.0, 9360 + int(zc), 0, 0.6, 22.0, 0.15))
    for xc in bar_x:                                               # rivet domes at the 63 crossings, front and back
        for zc in flat_z:
            for sgn in (1, -1):
                d = K.lathe_z([(2.2, 0.0), (1.7, 0.8), (0.0, 1.3)], 6, 0)
                rot(d, 'X', -90.0 if sgn > 0 else 90.0)
                shift(d, xc, 2.85 * sgn, zc)
                parts.append(d)
    bm = join(parts)
    for p in parts:
        p.free()
    pc = crypt_piece(CRYPT + "Portcullis_300x60x560", bm, ["MAT_Iron"], ucx_design=[ucx_box(-150.0, 150.0, -30.0, 30.0, 0.0, 560.0)],
                     note="bottom-centre; 9 square bars 6 x 6 at 32.5 spacing (x +-130) from 12 cm spike tips at z 0 to z 560, 7 flat bars 8 x 3 at z 60..480, 126 rivet "
                          "domes, side rails 8 x 8 centred at x +-146 (outer faces +-150); lattice within y +-4.5; 4 guide pins 6 x 60 x 6 at x +-146 (z 70, 500) bring "
                          "the visual to the 60 cm greybox depth (D1.3 gives 300 x 60 x 560); UCX 1 box x +-150, y +-30, z 0..560")
    return pc


# ---------------------------------------------------------------------------------------------- L: rubble fill
def _chip_block(rng, sx, sy, sz):
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    corners = [(a, b, c) for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)]
    cuts = set(rng.sample(range(8), rng.randint(1, 3)))
    pts = []
    for i, (a, b, c) in enumerate(corners):
        jx, jy, jz = (1.0 + rng.uniform(-0.1, 0.1) for _ in range(3))
        px, py, pz = a * hx * jx, b * hy * jy, c * hz * jz
        if i in cuts:
            k = rng.uniform(0.35, 0.8)
            pts += [Vector((px * (1 - k), py, pz)), Vector((px, py * (1 - k), pz)), Vector((px, py, pz * (1 - k)))]
        else:
            pts.append(Vector((px, py, pz)))
    h = K.hull_from_points(pts, 0)
    K.bevel_all(h, 1.3, 25.0)
    return h


def build_c_rubble():
    rng = random.Random(9313)
    blocks = []
    beam_a = Vector((-175.0, 110.0))                     # beam start (y, z) and unit direction in the YZ plane (elevation 38 deg)
    beam_d = Vector((math.cos(math.radians(38.0)), math.sin(math.radians(38.0))))

    def beam_dist(yc, zc):
        v = Vector((yc, zc)) - beam_a
        t = max(0.0, min(380.0, v.dot(beam_d)))
        return (v - beam_d * t).length

    def place(sx, sy, sz, xf, yc, zc, tilt=1.0):
        b = _chip_block(rng, sx, sy, sz)
        rot(b, 'X', rng.uniform(-22.0, 22.0) * tilt)
        rot(b, 'Y', rng.uniform(-14.0, 14.0) * tilt)
        rot(b, 'Z', rng.uniform(-14.0, 14.0) * tilt)
        hs = max(sy, sz) * 0.5 + 2.0
        yc = max(-210.0 + hs, min(210.0 - hs, yc))
        zc = max(hs, min(560.0 - hs, zc))
        shift(b, xf + sx / 2.0, yc, zc)
        blocks.append(b)
        return b

    cols, rows = 6, 8
    for r in range(rows):
        for c in range(cols):
            sx = rng.uniform(46.0, 70.0)
            sy, sz = rng.uniform(50.0, 70.0), rng.uniform(46.0, 70.0)
            yc = -175.0 + 70.0 * c + (22.0 if r % 2 else -22.0) + rng.uniform(-10.0, 10.0)
            zc = 35.0 + 70.0 * r + rng.uniform(-12.0, 12.0)
            if r == rows - 1:
                zc = 560.0 - sz / 2.0 - rng.uniform(0.0, 3.0)
            xf = -55.0 + rng.uniform(0.0, 20.0)
            if beam_dist(yc, zc) < 40.0:
                xf = -36.0 + rng.uniform(0.0, 5.0)             # recessed behind the beam lying across the face
            place(sx, sy, sz, xf, yc, zc)
    for _ in range(6):                                          # six small jammed fragments (25..45) in front / between
        s = [rng.uniform(25.0, 45.0) for _ in range(3)]
        yc, zc = rng.uniform(-190.0, 190.0), rng.uniform(40.0, 520.0)
        xf = -47.0 + rng.uniform(0.0, 6.0) if beam_dist(yc, zc) > 36.0 else -30.0
        place(s[0], s[1], s[2], xf, yc, zc, 1.6)
    for b in blocks:
        densify(b, 24.0)
        weather(b, 9313 + len(b.verts), 1.1, lambda co, n: 1.0, f1=1 / 15.0, f2=1 / 5.0)
    # backing mass: closes every gap behind the blocks (lumpy, never reaches the -X plane)
    core = K.box(-34.0, 52.0, -208.0, 208.0, 0.0, 558.0, 0, 0.0)
    densify(core, 30.0)
    for v in core.verts:
        v.co.x += (fbm3(v.co.y / 40.0, v.co.z / 40.0, 3.0, 9313, 3) - 0.5) * 12.0
    # the broken beam 35 x 30 x 380 (Wood): splintered upper end
    shaft = lbeam(-17.5, 17.5, -15.0, 15.0, 0.0, 345.0, 9399, 1, 0.9, 20.0, 0.35)
    parts = [shaft]
    xs = (-17.5, -8.5, 0.5, 9.0, 17.5)
    for i in range(4):
        z0 = 340.0
        ln = rng.uniform(14.0, 38.0) if i not in (1, 2) else rng.uniform(26.0, 38.0)
        x0, x1 = xs[i], xs[i + 1]
        pts = [Vector((x0, -15.0, z0)), Vector((x1, -15.0, z0)), Vector((x1, 15.0, z0)), Vector((x0, 15.0, z0)),
               Vector(((x0 + x1) / 2 + rng.uniform(-1.5, 1.5), rng.uniform(-9.0, 9.0), z0 + ln)), Vector(((x0 + x1) / 2 + rng.uniform(-1.5, 1.5), rng.uniform(-9.0, 9.0) + 1.5, z0 + ln))]
        sp = K.hull_from_points(pts, 1)
        parts.append(sp)
    bj = join(parts, None)
    for p in parts:
        p.free()
    rot(bj, 'X', -52.0)                                          # local +Z -> (0, cos 38, sin 38) in YZ
    shift(bj, -37.0, beam_a.x, beam_a.y)
    allp = blocks + [core, bj]
    bm = join(allp, None)
    for p in allp:
        p.free()
    # keep the material of the beam (slot 1) -- join(None) preserves indices
    mn, mx = bounds(bm)
    fit_box(bm, (-55.0, -210.0, 0.0), (55.0, 210.0, 560.0))
    pc = crypt_piece(CRYPT + "RubbleFill_100x400x560", bm, ["MAT_Stone", "MAT_Wood"], ucx_design=[ucx_box(-50.0, 50.0, -200.0, 200.0, 0.0, 560.0)],
                     note="bottom-centre; 54 chipped blocks (48 face blocks 46-70 on a 6 x 8 staggered grid + 6 fragments 25-45) over a lumpy backing mass, visual x +-55, y +-210, "
                          "z 0..560 (pre-fit bounds %s..%s); broken beam 35 x 30 x 380 (splintered end) diagonally across the -X face; UCX 1 box x +-50, y +-200, z 0..560"
                          % (tuple(round(v) for v in mn), tuple(round(v) for v in mx)))
    return pc


# ---------------------------------------------------------------------------------------------- M: crank
def build_c_crank():
    IR, WD = 0, 1
    boss = K.box(-4.0, 4.0, -4.0, 4.0, 0.0, 12.0, IR, 0.5)
    sock = K.box(-2.8, 2.8, -2.8, 2.8, 4.0, 12.5, IR, 0.0)
    boss = bool_op(boss, sock, 'DIFFERENCE', 2)
    sock.free()
    arm = K.box(0.0, 38.0, -2.0, 2.0, 0.0, 2.5, IR, 0.4)
    prof = [(1.9, 0.0), (2.1, 1.5), (2.4, 4.0), (2.5, 6.5), (2.2, 9.5), (1.9, 11.6), (1.2, 12.0)]
    hnd = K.lathe_z(prof, 10, WD)
    shift(hnd, 36.0, 0.0, 2.3)
    # the free end of the iron arm is rounded by the handle's boss: small collar
    col = K.cylinder(3.0, 1.2, 10, IR)
    shift(col, 36.0, 0.0, 2.3)
    bm = join([boss, arm, hnd, col], None)
    for p in (boss, arm, hnd, col):
        p.free()
    pc = crypt_piece("SM_LB_Prop_Crank_A", bm, ["MAT_Iron", "MAT_Wood"], ucx_fixed=(44.0, 16.0, 16.0),
                     note="bottom-centre, lies flat (arm on the plinth, socket boss and handle both pointing up): square socket boss 8 x 8 x 12 with a visible 5.6 x 5.6 socket, "
                          "flat iron arm 38 x 4 x 2.5 at 90 deg to the socket axis, wooden handle r ~2.2 x 12 at the arm end; UCX 1 box 44 x 16 x 16 (bottom-centre)")
    return pc


# ---------------------------------------------------------------------------------------------- N: capstan drum
def build_c_capstan():
    WD, IR = 0, 1
    drum = K.cylinder(34.0, 48.0, 16, WD)
    shift(drum, 0.0, 0.0, -25.0)
    K.bevel_all(drum, 1.2, 20.0)
    holes = join([K.box(-60.0, 60.0, -3.2, 3.2, 10.0, 16.4, WD, 0.0), K.box(-3.2, 3.2, -60.0, 60.0, 10.0, 16.4, WD, 0.0)])
    drum = bool_op(drum, holes, 'DIFFERENCE', 2)
    holes.free()
    densify(drum, 9.0)
    weather(drum, 9320, 0.5, lambda co, n: 1.0, f1=1 / 16.0, f2=1 / 5.0)
    parts = [drum]
    for zc in (-19.0, 19.0):                                            # iron bands r 35, z +-17..21
        r = K.ring(35.0, 32.5, 4.0, 16, IR)
        shift(r, 0.0, 0.0, zc - 2.0)
        parts.append(r)
    boss = K.lathe_z([(10.0, 0.0), (10.0, 0.8), (7.0, 1.9), (0.0, 2.4)], 12, IR)
    shift(boss, 0.0, 0.0, 22.6)
    parts.append(boss)
    b1 = lbeam(-55.0, 55.0, -2.5, 2.5, 10.5, 15.5, 9321, WD, 0.5, 20.0, 0.3)   # capstan bars 5 x 5 x 110 through the square holes at z +13
    b2 = lbeam(-2.5, 2.5, -55.0, 55.0, 10.5, 15.5, 9322, WD, 0.5, 20.0, 0.3)
    parts += [b1, b2]
    bm = join(parts, None)
    for p in parts:
        p.free()
    fit_box(bm, (-55.0, -55.0, -25.0), (55.0, 55.0, 25.0))
    pc = crypt_piece(CRYPT + "CapstanDrum_80x50", bm, ["MAT_Wood", "MAT_Iron"], ucx_design=[ucx_box(-35.0, 35.0, -35.0, 35.0, -25.0, 25.0)],
                     note="CENTRE pivot (z -25..25): 16-sided drum r 34 (body z -25..23, bevelled), iron bands r 35 at z -21..-17 and 17..21, domed top boss r 10 (to z 25), "
                          "two wooden bars 5 x 5 x 110 crosswise through 6.4 square holes at z 13; UCX 1 box x +-35, y +-35, z +-25")
    pc.seat_mode = "none"
    return pc


# ---------------------------------------------------------------------------------------------- O: plaque frame
def build_c_plaque():
    rng = random.Random(9314)
    hx, hz = 125.0, 87.5
    prof = [(0.0, 0.0), (0.0, 11.0)]
    for a in (22.5, 45.0, 67.5, 90.0):
        t = math.radians(a)
        prof.append((3.0 - 3.0 * math.cos(t), 11.0 + 3.0 * math.sin(t)))
    prof += [(3.0, 10.0), (7.0, 10.0), (7.0, 6.0), (10.0, 6.0), (10.0, 0.0)]
    b = bmesh.new()
    nx, nz = 34, 24                                                  # points per side (about 8 cm)
    loops = []
    for (o, y) in prof:
        X, Z = hx + o, hz + o
        ring = []
        for i in range(nx):
            ring.append((-X + 2 * X * i / nx, -Z))
        for i in range(nz):
            ring.append((X, -Z + 2 * Z * i / nz))
        for i in range(nx):
            ring.append((X - 2 * X * i / nx, Z))
        for i in range(nz):
            ring.append((-X, Z - 2 * Z * i / nz))
        loops.append([b.verts.new((px, y, pz)) for (px, pz) in ring])
    m, nr = len(prof), 2 * (nx + nz)
    for i in range(m):
        i2 = (i + 1) % m
        for s_ in range(nr):
            s2 = (s_ + 1) % nr
            b.faces.new((loops[i][s_], loops[i][s2], loops[i2][s2], loops[i2][s_]))
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    K.bm_set_mat(b, 0)
    spots = []
    for sx in (-1, 1):
        for sz in (-1, 1):
            spots.append(((sx * 133.0, 4.0, sz * 95.5), rng.uniform(5.5, 8.5)))
    b = cut_chips(b, rng, spots, 0)
    bmesh.ops.triangulate(b, faces=b.faces[:])
    weather(b, 9314, 0.8, lambda co, n: 0.0 if co.y < 0.02 else 1.0, f1=1 / 16.0, f2=1 / 6.0)
    fit_box(b, (-135.0, 0.0, -97.5), (135.0, 14.0, 97.5))
    pc = crypt_piece(CRYPT + "PlaqueFrame_270x195", b, ["MAT_Stone"],
                     note="back plane y 0, x centre, z centre; outer 270 x 195, opening 250 x 175, depth 14 (y 0..14), three steps toward the opening (y 6, 10, 14) with an "
                          "ovolo on the innermost, chipped outer corners (seed 9314)")
    pc.seat_mode = "backcentre"
    return pc


# ---------------------------------------------------------------------------------------------- P: winch frame
def _orient(bm, direction, origin):
    """Rotate a beam built along +Z onto `direction` and move it to `origin`."""
    q = Vector((0, 0, 1)).rotation_difference(Vector(direction).normalized())
    bm.transform(q.to_matrix().to_4x4())
    shift(bm, *origin)
    return bm


def build_c_winch():
    WD, IR = 0, 1
    parts = []
    for s in (-1, 1):
        x = 110.0 * s
        parts.append(lbeam(x - 10.0, x + 10.0, -10.0, 10.0, 10.0, 250.0, 9330 + s, WD, 0.8, 22.0, 0.3))        # post 20 x 20 x 240 on the plate
        parts.append(lbeam(x - 10.0, x + 10.0, -45.0, 45.0, 0.0, 10.0, 9332 + s, WD, 0.8, 22.0, 0.25))          # sole plate 20 x 90 x 10 (along Y)
        for sy in (-1, 1):                                                                                       # braces 12 x 12 from z 140 to the plate ends
            A = Vector((x, 0.0, 140.0))
            B = Vector((x, sy * 34.0, 11.0))
            dvec = B - A
            L = dvec.length
            br = lbeam(-6.0, 6.0, -6.0, 6.0, -5.0, L + 5.0, 9340 + s * 3 + sy, WD, 0.7, 22.0, 0.25)
            _orient(br, dvec, A)
            parts.append(br)
    parts.append(lbeam(-130.0, 130.0, -10.0, 10.0, 230.0, 250.0, 9350, WD, 0.8, 24.0, 0.3))                      # top beam 20 x 20 x 260
    drum = beam_cyl(22.0, 180.0, 9351, WD, 16, 22.0)
    rot(drum, 'Y', 90.0)
    shift(drum, -90.0, 0.0, 170.0)
    parts.append(drum)
    axle = K.cylinder(3.2, 250.0, 10, IR)
    rot(axle, 'Y', 90.0)
    shift(axle, -125.0, 0.0, 170.0)
    parts.append(axle)
    for xc in (-85.0, -51.0, -17.0, 17.0, 51.0, 85.0):                                                            # 6 iron bands
        r = K.ring(23.6, 20.5, 3.5, 16, IR)
        rot(r, 'Y', 90.0)
        shift(r, xc - 1.75, 0.0, 170.0)
        parts.append(r)
    # chain coil: torus links on a 5-turn helix over the +X half of the drum
    turns, x_a, x_b, rh = 5.0, 8.0, 88.0, 24.2
    pitch_ax = (x_b - x_a) / turns
    ds = 5.2
    helix_len_per_rad = math.hypot(rh, pitch_ax / (2 * math.pi))
    nlinks = int(turns * 2 * math.pi * helix_len_per_rad / ds)
    for i in range(nlinks):
        ph = 2 * math.pi * turns * i / nlinks
        xk = x_a + pitch_ax * ph / (2 * math.pi)
        rad = Vector((0.0, math.cos(ph), math.sin(ph)))
        cen = Vector((xk, rh * math.cos(ph), 170.0 + rh * math.sin(ph)))
        tan = Vector((pitch_ax / (2 * math.pi), -rh * math.sin(ph), rh * math.cos(ph))).normalized()
        axis = rad if i % 2 == 0 else tan.cross(rad).normalized()
        t = torus(3.0, 0.85, 8, 5, IR)
        t.transform(Vector((0, 0, 1)).rotation_difference(axis).to_matrix().to_4x4())
        shift(t, *cen)
        parts.append(t)
    for s, ang in ((-1, 35.0), (1, -145.0)):                                                                      # crank arms 30 long at both ends
        arm = K.box(-1.5, 1.5, -2.2, 2.2, -4.0, 30.0, IR, 0.4)
        knob = K.cylinder(2.3, 6.0, 8, IR)
        rot(knob, 'Y', 90.0)
        shift(knob, 0.0, 0.0, 28.0)
        kb = join([arm, knob], None)
        arm.free()
        knob.free()
        rot(kb, 'X', ang)
        shift(kb, s * 124.0, 0.0, 170.0)
        parts.append(kb)
    bm = join(parts, None)
    for p in parts:
        p.free()
    ucx = []
    for s in (-1, 1):
        ucx.append(ucx_box(s * 110.0 - 10.0, s * 110.0 + 10.0, -10.0, 10.0, 0.0, 250.0))
        ucx.append(ucx_box(s * 110.0 - 10.0, s * 110.0 + 10.0, -45.0, 45.0, 0.0, 10.0))
    pc = crypt_piece(CRYPT + "WinchFrame", bm, ["MAT_Wood", "MAT_Iron"], ucx_design=ucx,
                     note="bottom-centre; posts 20 x 20 x 240 at x +-110 on 20 x 90 x 10 sole plates, 4 braces 12 x 12 (z 140 to the plate ends), top beam 20 x 20 x 260 at z 230..250, "
                          "wooden drum r 22 x 180 on an iron axle at z 170 with 6 iron bands, 5-turn chain coil on the +X half (torus links), iron crank arms 30 long at both ends; "
                          "UCX 4 boxes (2 posts 20 x 20 x 250, 2 plates 20 x 90 x 10)")
    return pc


# ==============================================================================================
# P9-R2A (plan Docs/plans/P9_CRYPT_ART.md amendment D1.25, R2-A): bell wheel, dial-lever set, roof-hole gobo plate.
# FBX go to <out>/R2/.  Authoring space == Unreal space (Y is mirrored at export).  Names: SM_LB_Prop_BellWheel_A,
# SM_LB_Prop_DialLever_{Backplate,Quadrant,Arm,Weight,NotchStop}, SM_LB_Gobo_RoofHole.
# The lever parts replace the P4 greybox components of /Game/LastBell/Blueprints/Puzzles/BP_DialLever one for one:
# each is built to the AABB of the engine primitive it replaces (mesh-local, pivot = primitive centre), so a child Blueprint can use scale 1.
# Survey: Docs/ArtTest/crypt/survey_diallever.md.
# ==============================================================================================
R2_SUB = "R2"
MAT_COLORS.update({"MAT_Bronze": (0.55, 0.36, 0.15, 1.0), "MAT_Paint": (0.75, 0.72, 0.62, 1.0)})


def r2_piece(name, bm, slots, seat="centre", **kw):
    pc = Piece(name, bm, slots, **kw)
    pc.subdir = R2_SUB
    pc.seat_mode = seat                       # lever parts: "none" = pivot stays where it was built (the engine primitive's centre)
    return pc


def sphere_z(r, segs=12, rings=8, mat=0):
    prof = [(0.0, -r)] + [(r * math.sin(math.pi * k / rings), -r * math.cos(math.pi * k / rings)) for k in range(1, rings)] + [(0.0, r)]
    return K.lathe_z(prof, segs, mat)


def dome_z(r, h, segs=8, mat=0):
    """Rivet head: flat base at z 0, domed top at z h."""
    return K.lathe_z([(r, 0.0), (r * 0.94, h * 0.4), (r * 0.72, h * 0.78), (r * 0.32, h * 0.97), (0.0, h)], segs, mat)


def chain_link(R, r, stretch, mat, plane):
    """Stadium-ish chain link standing along Z: torus of major radius R stretched by `stretch`; plane 'xz' or 'yz'."""
    t = torus(R, r, 10, 5, mat)
    tf(t, Matrix.Diagonal((1.0, stretch, 1.0, 1.0)))
    rot(t, 'X', 90.0)                                         # ring plane XY -> XZ, long axis Y -> Z
    if plane == 'yz':
        rot(t, 'Z', 90.0)
    return t


# ---------------------------------------------------------------------------------------------- 1: bell wheel
def r2_bell(mat_bronze, mat_iron):
    """One bell, mouth (lip) at local z 0, crown at z 11 (crown flat O4), lip O9, hollow, with a knob on the crown and a clapper ball O2 on a wire."""
    outer = [(4.5, 0.0), (4.45, 0.6), (3.9, 1.6), (3.3, 3.2), (2.85, 5.0), (2.5, 7.0), (2.2, 9.0), (2.0, 10.5), (2.0, 11.0)]
    inner = [(3.9, 0.0), (3.5, 1.6), (2.9, 3.2), (2.45, 5.0), (2.1, 7.0), (1.8, 9.0), (1.55, 10.2)]
    prof = [(0.0, 10.2)] + inner[::-1] + outer + [(0.0, 11.0)]
    body = K.lathe_z(prof, 14, mat_bronze)
    knob = K.cylinder(0.8, 1.0, 8, mat_bronze)
    shift(knob, 0.0, 0.0, 11.0)
    wire = K.cylinder(0.18, 8.6, 6, mat_iron)
    shift(wire, 0.0, 0.0, 1.8)
    ball = sphere_z(1.0, 8, 4, mat_iron)
    shift(ball, 0.0, 0.0, 1.25)
    return [body, knob, wire, ball]


def build_r2_bellwheel():
    IR, BR = 0, 1
    rng = random.Random(9400)
    parts = []
    axle = K.cylinder(4.0, 50.0, 12, IR)
    K.bevel_all(axle, 0.3, 20.0)
    parts.append(axle)
    fin = sphere_z(4.0, 14, 8, IR)
    shift(fin, 0.0, 0.0, 54.0)                                             # ball finial O8, Z 50..58
    parts.append(fin)
    for z0, ro, h in ((48.6, 4.9, 1.4), (42.0, 5.4, 1.3), (32.7, 5.4, 1.3)):                 # forged collars: under the ball, on and under the hub
        c = K.ring(ro, 3.9, h, 12, IR)
        shift(c, 0.0, 0.0, z0)
        parts.append(c)
    hub = K.cylinder(8.0, 8.0, 16, IR)                                     # hub O16 x 8, Z 34..42
    K.bevel_all(hub, 0.4, 20.0)
    shift(hub, 0.0, 0.0, 34.0)
    parts.append(hub)
    rim = K.ring(42.0, 38.0, 3.0, 48, IR)                                  # rim: major r 40, section 4 x 3, centred Z 38 (Z 36.5..39.5)
    K.bevel_all(rim, 0.3, 20.0)
    shift(rim, 0.0, 0.0, 36.5)
    parts.append(rim)
    for k in range(6):                                                     # 6 spokes 3 x 2 at Z 38
        ang = 60.0 * k + rng.uniform(-1.2, 1.2)
        sp = K.box(7.0, 39.2, -1.5, 1.5, 37.0, 39.0, IR, 0.25)
        rot(sp, 'Z', ang)
        parts.append(sp)
        rv = K.cylinder(0.95, 0.55, 8, IR)                                 # rivet head where the spoke meets the rim
        shift(rv, 40.0, 0.0, 39.5)
        rot(rv, 'Z', ang)
        parts.append(rv)
    for k in range(8):                                                     # 8 bells every 45 deg at radius 40, hanging from an iron loop under the rim
        ang = 45.0 * k
        bell = r2_bell(BR, IR)
        for p in bell:
            shift(p, 40.0, 0.0, 22.0)                                      # bell mouth at Z 22
            rot(p, 'Z', ang)
            parts.append(p)
        lk = chain_link(0.95, 0.42, 1.85, IR, 'xz')                        # 2.6 cm wide loop, between the crown knob (Z 34) and the rim underside (Z 36.5)
        shift(lk, 40.0, 0.0, 35.0)
        rot(lk, 'Z', ang)
        parts.append(lk)
    bm = join(parts)
    for p in parts:
        p.free()
    return r2_piece(PREFIX + "BellWheel_A", bm, ["MAT_Iron", "MAT_Bronze"], ucx_design=[ucx_box(-42.0, 42.0, -42.0, 42.0, 0.0, 58.0)],
                    note="R2-A bottom-centre, vertical axle on Z: iron axle O8 Z 0..50 + ball finial O8 Z 50..58, hub O16 x 8 at Z 34..42, rim ring major r 40 (section 4 x 3, Z 36.5..39.5, outer O84), "
                         "6 spokes 3 x 2, 8 hollow bronze bells every 45 deg at r 40 (lip O9, height 11, crown O4, mouth at Z 22, clapper ball O2 on a wire) hung from iron loops; "
                         "visual X/Y reach 44.5 because the bell lips stick out past the rim; UCX 1 box 84 x 84 x 58")


# ---------------------------------------------------------------------------------------------- 2a: lever backplate
def build_r2_backplate():
    WD, IR = 0, 1
    parts = []
    for k, (y0, y1) in enumerate(((-15.0, -0.25), (0.25, 15.0))):         # oak board = two planks with a 0.5 seam down the middle (lattice boxes: clean quads, then chamfer + weathering)
        pl = gbox(-3.0, 3.0, y0, y1, -45.0, 45.0, 5.0, WD)
        K.bevel_all(pl, 0.3, 20.0)
        weather(pl, 9411 + k, 0.2, lambda co, n: 1.0, f1=1.0 / 14.0, f2=1.0 / 4.0)
        fit_box(pl, (-3.0, y0, -45.0), (3.0, y1, 45.0))
        parts.append(pl)
    for zc in (-34.0, 17.0):                                               # two iron straps across the width, 4 rivets each
        st = K.box(2.9, 3.35, -15.0, 15.0, zc - 2.25, zc + 2.25, IR, 0.18)
        parts.append(st)
        for y in (-10.5, -3.5, 3.5, 10.5):
            rv = dome_z(0.8, 0.45, 8, IR)
            rot(rv, 'Y', 90.0)                                             # +Z -> +X
            shift(rv, 3.35, y, zc)
            parts.append(rv)
    boss = K.cylinder(4.5, 0.6, 16, IR)                                    # pivot washer plate where handlePivot rides (actor x 6, z 45 = mesh z 0)
    K.bevel_all(boss, 0.2, 20.0)
    rot(boss, 'Y', 90.0)
    shift(boss, 2.9, 0.0, 0.0)
    parts.append(boss)
    bolt = dome_z(1.5, 0.3, 10, IR)
    rot(bolt, 'Y', 90.0)
    shift(bolt, 3.5, 0.0, 0.0)
    parts.append(bolt)
    plate = K.box(2.9, 3.5, -9.0, 9.0, 26.0, 44.0, IR, 0.2)               # label plate 18 x 18; the TextRender sits at x 3.6, mesh z 37, just in front of its face
    parts.append(plate)
    for y in (-7.2, 7.2):
        for z in (28.6, 41.4):
            rv = dome_z(0.55, 0.25, 8, IR)
            rot(rv, 'Y', 90.0)
            shift(rv, 3.5, y, z)
            parts.append(rv)
    # ---- R2-A2 (D1.26): pulley bracket at the board top, static chain up and back into a wall eyelet ----
    cap = K.box(-3.35, 3.35, -6.0, 6.0, 43.5, 46.5, IR, 0.25)              # iron cap wrapping the top end of the board
    parts.append(cap)
    PC = (7.0, 50.0)                                                        # pulley centre (x, z): O10 wheel, 4 cm in front of the board face, axle at local Z 50
    for sg in (-1, 1):                                                      # two cheek plates from the cap to the axle (hull of the base strip and a disc round the axle)
        pts = []
        for y in (sg * 2.6, sg * 3.3):
            pts += [Vector((-1.5, y, 45.5)), Vector((3.5, y, 45.5))]
            pts += [Vector((PC[0] + 2.3 * math.cos(2 * math.pi * i / 12), y, PC[1] + 2.3 * math.sin(2 * math.pi * i / 12))) for i in range(12)]
        parts.append(K.hull_from_points(pts, IR))
    axle = K.cylinder(0.9, 7.4, 10, IR)
    rot(axle, 'X', 90.0)                                                    # axis Z -> -Y
    shift(axle, PC[0], 3.7, PC[1])
    parts.append(axle)
    for sg in (-1, 1):
        hd = K.cylinder(1.4, 0.5, 10, IR)
        rot(hd, 'X', 90.0)
        shift(hd, PC[0], 3.8 if sg > 0 else -3.3, PC[1])
        parts.append(hd)
    wheel = K.lathe_z([(0.0, -1.5), (5.0, -1.5), (5.0, -0.9), (4.1, -0.35), (4.1, 0.35), (5.0, 0.9), (5.0, 1.5), (0.0, 1.5)], 24, IR)   # grooved pulley wheel O10 x 3
    rot(wheel, 'X', 90.0)
    shift(wheel, PC[0], 0.0, PC[1])
    parts.append(wheel)
    E = Vector((-0.9, 75.0))                                                # eyelet ring centre (x, z): 30 cm above the board top (z 45), base plate flush with the back plane x -3
    plate_e = K.box(-3.0, -2.4, -2.2, 2.2, 72.5, 77.5, IR, 0.12)
    parts.append(plate_e)
    ring_e = torus(1.2, 0.45, 12, 6, IR)
    rot(ring_e, 'X', 90.0)
    shift(ring_e, E.x, 0.0, E.y)
    parts.append(ring_e)
    for yy in (-1.4, 1.4):
        for zz in (73.5, 76.5):
            rv = dome_z(0.45, 0.2, 8, IR)
            rot(rv, 'Y', 90.0)
            shift(rv, -2.4, yy, zz)
            parts.append(rv)
    C = Vector(PC)                                                          # tangent from the eyelet to the groove circle (front side), chain centre-line radius 4.3
    dv = C - E
    dd = dv.length
    base = math.atan2(dv.y, dv.x)
    off = math.asin(4.3 / dd)
    ang = base + off                                                        # rotate the direction toward +x side of the wheel: tangent point on the front-top
    tl = math.sqrt(dd * dd - 4.3 * 4.3)
    T = E + Vector((math.cos(ang), math.sin(ang))) * tl
    ax = (T - E).normalized()
    lc = (T - E).length
    NL, r_w = 8, 0.42
    pitch = (lc - 4.0) / (NL - 1)
    stretch = (pitch / 2.0 + r_w) / 0.95
    tilt = math.degrees(math.atan2(ax.x, ax.y))                             # rotation about Y that takes Z onto the chain axis (x, z)
    for k in range(NL):
        ctr = E + ax * (2.0 + k * pitch)
        lk = chain_link(0.95, r_w, stretch, IR, 'yz' if k % 2 == 0 else 'xz')
        rot(lk, 'Y', tilt)
        shift(lk, ctr.x, 0.0, ctr.y)
        parts.append(lk)
    bm = join(parts)
    for p in parts:
        p.free()
    return r2_piece(PREFIX + "DialLever_Backplate", bm, ["MAT_Wood", "MAT_Iron"], seat="none",
                    note="R2-A replaces Backplate (engine Cube scale 0.06 x 0.3 x 0.9 = X +-3, Y +-15, Z +-45), pivot = centre: oak board with a V seam, two iron straps (z -34, +17) with 4 rivets each, "
                         "pivot washer plate at z 0, iron label plate 18 x 18 (y +-9, z 26..44 mesh-local = 71..89 actor) front face x 3.5 (text at 3.6); fronts proud to x 3.8. "
                         "R2-A2: iron cap + pulley bracket at the top (wheel O10 at x 7, z 50 = actor 95, axle along Y) and an 8-link static chain from the wheel up and back into an eyelet ring on a plate flush with the back plane "
                         "(x -3) at z 75 (actor 120); taller than the primitive: Z -45..76.7")


# ---------------------------------------------------------------------------------------------- 2b: quadrant (rail)
R2_NOTCH_Z = 40.0 * math.sin(math.radians(35.0))                          # 22.94: greybox notch height = 40 sin(notchPitch 35 deg)


def build_r2_quadrant():
    """R2-A3 (D1.27): SKELETAL quadrant, pivot = the sector centre (the lever's rotation axis), mesh XZ plane, -42..+42 deg about +X (R2-A2 pivot, orientation and Y slab kept).
    Open iron frame instead of the solid R48 sector plate: arc band R 42..48 (1.5 thick, mesh y 1.7..3.2) with a raised 2 x 2 rim (R 46..48, +Y side), three V-notches 2 deep through
    rim and band at -35 / 0 / +35 deg, two 3-wide edge struts along +-42 deg and a 2-wide centre strut along 0 deg (R 6..42), a hub ring O12 / O4 at the pivot, the mounting foot (x -6..2)
    behind it, and three bone-white pegs O2.5 x 2 on the -Y face (toward the arm) under the notches.  The child BP places the mesh at (6, 4, 45), rotation 0, scale 1."""
    IR, PT = 0, 1
    R_IN, R0, R1, Y0, Y1 = 42.0, 46.0, 48.0, 1.7, 3.2
    arc = [math.radians(a) for a in range(-42, 43, 6)]

    def pol(r, a):
        return (r * math.cos(a), r * math.sin(a))

    band = K.prism([pol(R1, a) for a in arc] + [pol(R_IN, a) for a in arc[::-1]], 'y', Y0, Y1, IR)
    rim = K.prism([pol(R1, a) for a in arc] + [pol(R0, a) for a in arc[::-1]], 'y', Y1 - 0.2, Y1 + 2.0, IR)

    def strut(deg, off0, off1, r0=5.0, r1=42.6):
        """Rectangle along the ray `deg` (mesh x/z plane), radial r0..r1, perpendicular offsets off0..off1 (t = +angle direction)."""
        a = math.radians(deg)
        u, t = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
        pts = [(r * u[0] + o * t[0], r * u[1] + o * t[1]) for r, o in ((r0, off0), (r1, off0), (r1, off1), (r0, off1))]
        return K.prism(pts, 'y', Y0, Y1, IR)

    s_lo = strut(-42.0, 0.0, 3.0)                                          # edge struts: outer face flush with the +-42 deg band end (no ear sticking out past the band)
    s_hi = strut(42.0, -3.0, 0.0)
    s_mid = strut(0.0, -1.0, 1.0)
    hub = K.ring(6.0, 2.0, Y1 - Y0, 20, IR)                                # hub ring O12 / O4, axis Z -> -Y, y 1.7..3.2
    rot(hub, 'X', 90.0)
    shift(hub, 0.0, Y1, 0.0)
    foot = K.box(-6.0, 2.0, Y0, Y1, -3.5, 3.5, IR, 0.0)                    # mounting foot at the narrow end, back to the board face (actual x 0..8; board face at 3)
    frame = union([band, s_lo, s_hi, s_mid, hub, foot, rim])
    for q in (band, s_lo, s_hi, s_mid, hub, foot, rim):
        if q is not frame:
            q.free()
    for deg in (-35.0, 0.0, 35.0):                                         # V-notches 2 deep through rim and band (apex at R 46, 4.2 wide at R 49)
        a = math.radians(deg)
        u, t = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
        tri = [(R0 * u[0], R0 * u[1]), (49.0 * u[0] + 2.1 * t[0], 49.0 * u[1] + 2.1 * t[1]), (49.0 * u[0] - 2.1 * t[0], 49.0 * u[1] - 2.1 * t[1])]
        cut = K.prism(tri, 'y', -1.0, 6.0, IR)
        res = bool_op(frame, cut, 'DIFFERENCE', 2)
        cut.free()
        frame.free()
        frame = res
    bore = K.cylinder(2.0, 8.0, 20, IR)                                    # keep the hub hole open through the foot behind it
    rot(bore, 'X', 90.0)
    shift(bore, 0.0, 5.0, 0.0)
    res = bool_op(frame, bore, 'DIFFERENCE', 2)
    bore.free()
    frame.free()
    frame = res
    parts = [frame]
    for deg in (-35.0, 0.0, 35.0):                                         # bone-white pegs O2.5 x 2 on the arm side of the band (y 1.7 down to -0.3), under the notch apex at R 43.8
        a = math.radians(deg)
        pg = K.cylinder(1.25, 2.0, 12, PT)
        rot(pg, 'X', 90.0)                                                 # axis Z -> -Y
        shift(pg, 43.8 * math.cos(a), Y0, 43.8 * math.sin(a))
        parts.append(pg)
    for zz in (-2.0, 2.0):                                                 # two rivet heads on the hub ring behind the pivot
        rv = dome_z(0.6, 0.3, 8, IR)
        rot(rv, 'X', -90.0)                                                # +Z -> +Y
        shift(rv, -4.0, Y1, zz * 1.2)
        parts.append(rv)
    bm = join(parts)
    for q in parts:
        q.free()
    return r2_piece(PREFIX + "DialLever_Quadrant", bm, ["MAT_Iron", "MAT_Paint"], seat="none",
                    note="R2-A3 skeletal quadrant (replaces the R2-A2 solid sector plate): pivot = sector centre (lever rotation axis) in the mesh XZ plane, -42..+42 deg about +X; arc band R 42..48 x 1.5 (mesh y 1.7..3.2), "
                         "raised rim 2 x 2 (R 46..48, +Y side), three V-notches 2 deep at -35 / 0 / +35 deg through rim and band, edge struts +-42 deg (3 wide, R 6..42, outer face flush with the band end), "
                         "centre strut 0 deg (2 wide), hub ring O12 / O4, mounting foot x -6..2, three bone-white pegs O2.5 x 2 (MAT_Paint) on the -Y face at R 43.8 (toward the arm). "
                         "Place at (6, 4, 45) relative to the actor, rotation 0, scale 1 (D1.26 / D1.27)")


# ---------------------------------------------------------------------------------------------- 2c: arm
def build_r2_arm():
    IR, WD = 0, 1
    parts = []
    rod = K.cylinder(1.25, 32.5, 10, IR)                                   # rod O2.5, mesh z -11..21.5 (the free end is mesh -Z: the component is rotated pitch 90)
    shift(rod, 0.0, 0.0, -11.0)
    parts.append(rod)
    kn = K.cylinder(1.5, 3.0, 12, IR)                                      # pivot knuckle: pin axis along mesh Y (= the swing axis)
    rot(kn, 'X', 90.0)
    shift(kn, 0.0, 1.5, 21.0)
    K.bevel_all(kn, 0.2, 20.0)
    parts.append(kn)
    for z0, ro in ((12.4, 1.75), (15.4, 1.75), (-10.7, 1.7)):             # forged collars, the last one is the ferrule under the grip
        c = K.ring(ro, 1.0, 0.7, 12, IR)
        shift(c, 0.0, 0.0, z0)
        parts.append(c)
    grip = K.lathe_z([(0.0, -22.5), (0.9, -22.4), (1.55, -21.7), (2.0, -20.5), (1.95, -19.8), (1.55, -18.6), (1.35, -17.0), (1.35, -15.8),
                      (1.65, -14.4), (1.95, -13.0), (1.85, -11.8), (1.45, -10.9), (1.3, -10.5), (0.0, -10.5)], 14, WD)   # turned wooden grip O4 x 12 at the free end
    parts.append(grip)
    bm = join(parts)
    for p in parts:
        p.free()
    return r2_piece(PREFIX + "DialLever_Arm", bm, ["MAT_Iron", "MAT_Wood"], seat="none",
                    note="R2-A replaces Arm (engine Cylinder scale 0.03 x 0.03 x 0.45 = X/Y +-1.5, Z +-22.5; the component is rotated pitch 90, so mesh -Z points away from the pivot), pivot = centre: "
                         "iron rod O2.5, turned wooden grip max O4 x 12 at mesh z -22.5..-10.5 (free end), pivot knuckle with a Y pin at z +21, three collars. "
                         "Grip O4 instead of the spec's O4.5 to stay within 1 cm of the surveyed O3")


# ---------------------------------------------------------------------------------------------- 2d: weight on a chain
def build_r2_weight():
    """R2-A2 (D1.26): squat cast-iron counterweight ball O11 (z scaled 0.9) centred on the arm tip, a cast collar ring on the pivot side where the arm enters, no chain."""
    IR = 0
    ball = sphere_z(5.5, 18, 10, IR)
    tf(ball, Matrix.Diagonal((1.0, 1.0, 0.9, 1.0)))
    collar = K.ring(3.9, 2.1, 1.5, 18, IR)
    K.bevel_all(collar, 0.2, 20.0)
    rot(collar, 'Y', 90.0)                                                 # axis Z -> +X
    shift(collar, -5.8, 0.0, 0.0)
    seam = K.ring(5.62, 5.0, 0.5, 18, IR)                                  # cast seam band round the equator
    shift(seam, 0.0, 0.0, -0.25)
    bm = join([ball, collar, seam])
    for q in (ball, collar, seam):
        q.free()
    return r2_piece(PREFIX + "DialLever_Weight", bm, ["MAT_Iron"], seat="none",
                    note="R2-A2 replaces Weight: squat cast-iron ball O11 x 9.9 centred on the arm tip (component placement unchanged), cast collar ring (x -5.8..-4.3, O7.8, bore O4.2 for the O4 grip) on the pivot side, seam band; no chain")


# ---------------------------------------------------------------------------------------------- 2e: notch stop
def build_r2_notchstop():
    IR, PT = 0, 1
    b = K.box(-2.5, 2.5, -2.25, 2.25, -1.5, 1.5, IR, 0.3)
    b.normal_update()
    for f in b.faces:
        if f.normal.x > 0.9 or f.normal.z > 0.9:                          # the front (+X, toward the player) and top faces are the bone-white painted ones
            f.material_index = PT
    return r2_piece(PREFIX + "DialLever_NotchStop", b, ["MAT_Iron", "MAT_Paint"], seat="none",
                    note="R2-A replaces NotchLow/Mid/High (engine Cube scale 0.06 x 0.05 x 0.025 = 6 x 5 x 2.5), pivot = centre: iron stop 5 x 4.5 x 3 (spec 4 x 4 x 3, survey 6 x 5 x 2.5: "
                         "5 x 4.5 x 3 is within 1 cm of both), chamfered, +X and top faces MAT_Paint (bone white)")


# ---------------------------------------------------------------------------------------------- 3: roof-hole gobo plate
GOBO_SPOT_LOC = (5205.4, -1324.3, 2914.1)       # Light_Chapel_Moon_Roof (SpotLight_7), read from the editor in R2-A
GOBO_SPOT_ROT = (-38.0, 35.0, 0.0)              # pitch, yaw, roll
GOBO_D = 150.0                                  # gobo plane distance along the spot's forward axis
GOBO_OFFSET = 0.7                               # outward offset of the cut-out, cm in the gobo plane
GOBO_PLANE_Z = 12.0                             # slab-local Z of the outline plane (= ROOF_HOLE_Z, the middle of the 0..21 slab: halves the parallax of the oblique beam)
GOBO_SIZE = 110.0
GOBO_THICK = 2.0
GOBO_RES = 0.1


def raster_poly(poly, half, res):
    """Even-odd scanline fill of a polygon [(y, z)] on a square grid (rows = z, cols = y), pixel centres at -half + (i + .5) res."""
    import numpy as np
    n = int(round(2 * half / res))
    m = np.zeros((n, n), dtype=bool)
    P = np.array(poly, dtype=float)
    a, b = P, np.roll(P, -1, axis=0)
    zc = -half + (np.arange(n) + 0.5) * res
    for i in range(n):
        c = (a[:, 1] > zc[i]) != (b[:, 1] > zc[i])
        if not c.any():
            continue
        a_, b_ = a[c], b[c]
        t = (zc[i] - a_[:, 1]) / (b_[:, 1] - a_[:, 1])
        xs = np.sort(a_[:, 0] + t * (b_[:, 0] - a_[:, 0]))
        for x0, x1 in zip(xs[0::2], xs[1::2]):
            j0 = int(math.ceil((x0 + half) / res - 0.5))
            j1 = int(math.floor((x1 + half) / res - 0.5))
            if j1 >= j0:
                m[i, max(j0, 0):min(j1, n - 1) + 1] = True
    return m


def dilate_disc(mask, rpx):
    """Binary dilation by a disc of radius rpx pixels (exact Minkowski sum on the grid)."""
    import numpy as np
    H, W = mask.shape
    out = np.zeros_like(mask)
    cache = {}
    mi = mask.astype(np.int32)
    for dy in range(-rpx, rpx + 1):
        w = int(math.floor(math.sqrt(rpx * rpx - dy * dy)))
        if w not in cache:
            padded = np.pad(mi, ((0, 0), (w, w)))
            cs = np.concatenate([np.zeros((H, 1), dtype=np.int32), np.cumsum(padded, axis=1)], axis=1)
            cache[w] = (cs[:, 2 * w + 1:] - cs[:, :-(2 * w + 1)]) > 0
        d = cache[w]
        if dy >= 0:
            out[dy:, :] |= d[:H - dy, :]
        else:
            out[:H + dy, :] |= d[-dy:, :]
    return out


def trace_outer(mask, half, res):
    """Outer boundary of a binary raster as a CCW polygon [(y, z)] (lattice corners, inside on the left)."""
    H, W = mask.shape
    pad = [[False] * (W + 2) for _ in range(H + 2)]
    ys, xs = mask.nonzero()
    for i, j in zip(ys.tolist(), xs.tolist()):
        pad[i + 1][j + 1] = True
    nxt = {}
    for i, j in zip(ys.tolist(), xs.tolist()):
        if not pad[i][j + 1]:
            nxt.setdefault((j, i), []).append((j + 1, i))
        if not pad[i + 1][j + 2]:
            nxt.setdefault((j + 1, i), []).append((j + 1, i + 1))
        if not pad[i + 2][j + 1]:
            nxt.setdefault((j + 1, i + 1), []).append((j, i + 1))
        if not pad[i + 1][j]:
            nxt.setdefault((j, i + 1), []).append((j, i))
    loops, used = [], set()
    for s in list(nxt):
        for e in nxt[s]:
            if (s, e) in used:
                continue
            loop, cur, prev = [], s, None
            nx = e
            while True:
                used.add((cur, nx))
                loop.append(cur)
                prev, cur = cur, nx
                if cur == s:
                    break
                outs = [o for o in nxt.get(cur, []) if (cur, o) not in used]
                if not outs:
                    break
                if len(outs) > 1:                                          # touching corner: take the right-most turn so loops stay simple
                    dx, dy = cur[0] - prev[0], cur[1] - prev[1]
                    outs.sort(key=lambda o: dx * (o[1] - cur[1]) - dy * (o[0] - cur[0]))
                nx = outs[0]
            loops.append(loop)
    best = max(loops, key=lambda lp: abs(K.poly_area(lp)))
    if K.poly_area(best) < 0:
        best = best[::-1]
    return [(-half + x * res, -half + y * res) for (x, y) in best]


def dp_closed(poly, tol):
    n = len(poly)
    i0 = 0
    i1 = max(range(n), key=lambda i: math.hypot(poly[i][0] - poly[i0][0], poly[i][1] - poly[i0][1]))
    a, b = (i0, i1) if i0 < i1 else (i1, i0)
    h1 = _dp_open(poly[a:b + 1], tol)
    h2 = _dp_open(poly[b:] + poly[:a + 1], tol)
    return h1[:-1] + h2[:-1]


def segs_intersect(p, q, r, s):
    def o(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2, d3, d4 = o(p, q, r), o(p, q, s), o(r, s, p), o(r, s, q)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def poly_is_simple(poly):
    n = len(poly)
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            if segs_intersect(poly[i], poly[(i + 1) % n], poly[j], poly[(j + 1) % n]):
                return False
    return True


def gobo_projection(plane_z=GOBO_PLANE_Z):
    """Roof-hole outline (slab-local, exact boolean of the board cut and the slate cut) -> gobo-plane (y, z) cm.
    World point C = slab loc + x*Xa + y*Ya + z*Za (Ch_Roof_S1: loc ROOF_S1_LOC, rot ROOF_S1_ROT); from the spot at L with forward d, right r, up u:
    v = C - L, p = L + v * (D / (v . d)); plane coordinates (y, z) = ((p - L) . r, (p - L) . u).  Same formula as Tools/crypt/r1b/s3_gobos.py (there on the bbox corners)."""
    full, _p1, _p2 = roof_hole_outline()
    xa, ya, za = ue_axes(*ROOF_S1_ROT)
    loc = Vector(ROOF_S1_LOC)
    d, r, u = ue_axes(*GOBO_SPOT_ROT)
    L = Vector(GOBO_SPOT_LOC)
    pts, dists = [], []
    for (x, y) in full:
        C = loc + xa * x + ya * y + za * plane_z
        v = C - L
        q = v * (GOBO_D / v.dot(d))
        pts.append((q.dot(r), q.dot(u)))
        dists.append(v.dot(d))
    return pts, len(full), sum(dists) / len(dists)


def build_gobo_roofhole():
    pts, nfull, dist = gobo_projection()
    half = GOBO_SIZE / 2.0
    m0 = raster_poly(pts, half, GOBO_RES)
    rpx = int(round(GOBO_OFFSET / GOBO_RES))
    m1 = dilate_disc(m0, rpx)
    outline = trace_outer(m1, half, GOBO_RES)
    outline = dp_closed(outline, 0.1)
    assert poly_is_simple(outline), "gobo cut-out outline self-intersects"
    ys = [p[0] for p in outline]
    zs = [p[1] for p in outline]
    area0 = float(m0.sum()) * GOBO_RES ** 2
    area1 = abs(K.poly_area(outline))
    plate = K.box(-GOBO_THICK / 2, GOBO_THICK / 2, -half, half, -half, half, 0, 0.0)
    cutter = K.prism(outline, 'x', -GOBO_THICK, GOBO_THICK, 0)
    bm = bool_op(plate, cutter, 'DIFFERENCE', 1)
    plate.free()
    cutter.free()
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='EAR_CLIP')
    scale = GOBO_D / dist
    pc = Piece("SM_LB_Gobo_RoofHole", bm, ["MAT_Iron"],
               note="R2-A aperture-mask plate 110 x 110 x 2 (pivot centre, local X = thickness along the spot's forward axis, local Y/Z = the spot's right/up). Cut-out = the RoofSlab_Broken hole outline "
                    "(exact boolean of build_kit.hole_cutters(441), %d verts) at slab-local Z %.0f, projected from Light_Chapel_Moon_Roof (loc %s, rot %s) onto the plane D = %.0f; "
                    "mean distance spot -> slab %.0f so scale %.4f (1 cm in the plane = %.1f cm at the slab); outward offset %.1f cm (true disc dilation); outline simplified to %d verts. "
                    "Cut-out bbox y %.1f..%.1f z %.1f..%.1f"
                    % (nfull, GOBO_PLANE_Z, GOBO_SPOT_LOC, GOBO_SPOT_ROT, GOBO_D, dist, scale, 1.0 / scale, GOBO_OFFSET, len(outline), min(ys), max(ys), min(zs), max(zs)))
    pc.subdir = R2_SUB
    pc.seat_mode = "none"
    pc.extra = dict(outline_verts=len(outline), source_outline_verts=nfull, area_before_offset=round(area0, 2), area_after_offset=round(area1, 2), scale=round(scale, 5),
                    mean_distance=round(dist, 1), bbox_y=[round(min(ys), 2), round(max(ys), 2)], bbox_z=[round(min(zs), 2), round(max(zs), 2)], plane_z=GOBO_PLANE_Z, offset_cm=GOBO_OFFSET)
    return pc


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
        # ---- P8-3 chapel ----
        ("Truss_ArchBraced_1500", build_truss),
        ("Pew_A", lambda: build_pew(False)),
        ("Pew_Broken", lambda: build_pew(True)),
        ("AltarRail_600x40x100", build_altar_rail),
        ("Lectern_A", build_lectern),
        ("Altar_A", build_altar),
        ("MechShell_Cyl", build_mech_shell_cyl),
        ("MechShell_Cube", build_mech_shell_cube),
        ("SlateShards_A", build_slate_shards),
        ("CrossFinial_A", build_cross_finial),
        ("Backdrop_Plane_800x850", build_backdrop),
        ("Glass_Lancet_140x560", build_glass_lancet),
        ("Glass_Lancet_Broken", build_glass_broken),
        ("Glass_East", build_glass_east),
        ("Glass_Clue_Ext", build_glass_clue),
        ("Cobweb_Corner_A", build_cobweb_corner),
        ("Cobweb_Hang_A", build_cobweb_hang),
        ("PricketStand_Small_10x30", build_pricket_small),
        ("PricketStand_150", build_pricket_150),
        ("CandleFlame_A", build_candle_flame),
        # ---- P8-9a light-shaft cards ----
        ("LightShaft_Lancet", build_lightshaft_lancet),
        ("LightShaft_RoofHole", build_lightshaft_roofhole),
        # ---- P9-3 crypt pieces ----
        ("Crypt_OssuaryBay_500x599", build_c_bay),
        ("Crypt_Capital_A", build_c_capital),
        ("Crypt_Stair40_300", build_c_stair),
        ("Crypt_Sarcophagus_A", lambda: build_c_sarcophagus("A")),
        ("Crypt_Sarcophagus_B", lambda: build_c_sarcophagus("B")),
        ("Crypt_BoneBin_200x100x60", build_c_bonebin),
        ("Crypt_Block_100", lambda: build_c_block(False)),
        ("Crypt_Block_100_C", lambda: build_c_block(True)),
        ("Crypt_Corbel_A", build_c_corbel),
        ("Crypt_Beam_35x45x1120", build_c_beam),
        ("Crypt_Boards_300x250", lambda: build_c_boards(False)),
        ("Crypt_Boards_300x250_Broken", lambda: build_c_boards(True)),
        ("Crypt_RootsHang_A", lambda: build_c_roots("A", 9310, 4, 180, 80, 22.0, 4.5, 16, (4.5, 3.5, 3.0))),
        ("Crypt_RootsHang_B", lambda: build_c_roots("B", 9311, 6, 240, 90, 24.0, 5.0, 14, (5.0, 4.0, 3.5))),
        ("Crypt_RootsHang_C", lambda: build_c_roots("C", 9312, 3, 120, 60, 16.0, 3.0, 18, (2.8, 2.4, 2.2))),
        ("Crypt_Portcullis_300x60x560", build_c_portcullis),
        ("Crypt_RubbleFill_100x400x560", build_c_rubble),
        ("Crank_A", build_c_crank),
        ("Crypt_CapstanDrum_80x50", build_c_capstan),
        ("Crypt_PlaqueFrame_270x195", build_c_plaque),
        ("Crypt_WinchFrame", build_c_winch),
        # ---- P9-R2A (D1.25) ----
        ("BellWheel_A", build_r2_bellwheel),
        ("DialLever_Backplate", build_r2_backplate),
        ("DialLever_Quadrant", build_r2_quadrant),
        ("DialLever_Arm", build_r2_arm),
        ("DialLever_Weight", build_r2_weight),
        ("DialLever_NotchStop", build_r2_notchstop),
        ("Gobo_RoofHole", build_gobo_roofhole),
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
        if hasattr(pc, 'pivot_world'):
            rec['pivot_world'] = [round(v, 3) for v in pc.pivot_world]
        if hasattr(pc, 'extra'):
            rec['extra'] = pc.extra
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
    subs = {pc.subdir for pc in pieces}
    rep_dir = out_dir                                                                                      # P9: blend + report next to the Crypt / R2 FBX
    if only and len(subs) == 1 and next(iter(subs)) in (CRYPT_SUB, R2_SUB):
        rep_dir = os.path.join(out_dir, next(iter(subs)))
    os.makedirs(rep_dir, exist_ok=True)
    suffix = ("_" + tag) if tag else "_partial"
    blend = os.path.join(rep_dir, "LB_Props.blend" if not only else "LB_Props%s.blend" % suffix)
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    with open(os.path.join(rep_dir, "props_report.json" if not only else "props_report%s.json" % suffix), "w") as fh:
        json.dump(report, fh, indent=1)
    print("DONE %d props in %.1fs -> %s" % (len(pieces), time.time() - t0, out_dir))


if __name__ == "__main__":
    run()
