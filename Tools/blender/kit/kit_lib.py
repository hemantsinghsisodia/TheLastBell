"""kit_lib.py -- shared helpers for the THE LAST BELL modular kit (Blender 5.2, headless).

Conventions (see Docs/MODULAR_KIT.md and Tools/blender/kit/README.md):
  * Authoring space == the spec's Unreal space: 1 Blender unit = 1 cm, +X length, +Y thickness, +Z up,
    pivot = bottom-left-back corner (min X, min Y, min Z of the piece is (0, 0, 0)).
  * Export to FBX uses axis_forward='Y', axis_up='Z' (declares exactly Unreal's import axis system,
    identity node rotation, UnitScaleFactor = 1 (cm), vertices in cm). Unreal's importer negates Y when it
    converts the right-handed FBX to its left-handed world, so the export copy of every mesh is mirrored
    in Y (y -> -y) with the face winding reversed.  Net result in Unreal: Y in [0, thickness], outward faces.
  * Material slots: 0 MAT_Masonry, 1 MAT_Trim, 2 MAT_Rubble.  Vertex colour attribute "Color" = white.
"""
import math
import os
import random

import bpy
import bmesh
from mathutils import Vector, Matrix

SLOT_MASONRY, SLOT_TRIM, SLOT_RUBBLE = 0, 1, 2
MAT_NAMES = ("MAT_Masonry", "MAT_Trim", "MAT_Rubble")
MAT_COLORS = ((0.42, 0.41, 0.38, 1.0), (0.66, 0.63, 0.57, 1.0), (0.27, 0.255, 0.235, 1.0))
UV_CM_PER_UNIT = 100.0
UV_DIR_OFFSET = 20.0          # keeps the six projection directions in disjoint UV regions
UP = Vector((0.0, 0.0, 1.0))


# ----------------------------------------------------------------------------------------------
# scene / materials
# ----------------------------------------------------------------------------------------------
def setup_scene_units():
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 0.01          # 1 BU = 1 cm
    sc.unit_settings.length_unit = 'CENTIMETERS'
    return sc


def get_materials():
    mats = []
    for nm, col in zip(MAT_NAMES, MAT_COLORS):
        m = bpy.data.materials.get(nm)
        if m is None:
            m = bpy.data.materials.new(nm)
            m.diffuse_color = col
            m.roughness = 0.9
        mats.append(m)
    return mats


# ----------------------------------------------------------------------------------------------
# deterministic noise
# ----------------------------------------------------------------------------------------------
def _hash2(i, j, seed):
    s = math.sin(i * 127.1 + j * 311.7 + seed * 74.7) * 43758.5453123
    return s - math.floor(s)


def vnoise(x, y, seed=0):
    """Smooth 2D value noise in [0, 1] (lattice spacing 1)."""
    xi, yi = math.floor(x), math.floor(y)
    xf, yf = x - xi, y - yi
    u = xf * xf * (3 - 2 * xf)
    v = yf * yf * (3 - 2 * yf)
    a, b = _hash2(xi, yi, seed), _hash2(xi + 1, yi, seed)
    c, d = _hash2(xi, yi + 1, seed), _hash2(xi + 1, yi + 1, seed)
    return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v


def fbm(x, y, seed=0, octaves=3):
    amp, f, tot, norm = 1.0, 1.0, 0.0, 0.0
    for o in range(octaves):
        tot += amp * vnoise(x * f, y * f, seed + o * 17)
        norm += amp
        amp *= 0.5
        f *= 2.03
    return tot / norm


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# ----------------------------------------------------------------------------------------------
# bmesh basics
# ----------------------------------------------------------------------------------------------
def bm_append(dst, src, mat=None):
    """Copy src into dst (no welding).  mat overrides the material index when given."""
    vmap = {v: dst.verts.new(v.co) for v in src.verts}
    for f in src.faces:
        try:
            nf = dst.faces.new([vmap[v] for v in f.verts])
        except ValueError:
            continue
        nf.material_index = f.material_index if mat is None else mat
        nf.smooth = True
    return dst


def bm_set_mat(bm, mat):
    for f in bm.faces:
        f.material_index = mat
    return bm


def bm_translate(bm, dx=0.0, dy=0.0, dz=0.0):
    bmesh.ops.translate(bm, vec=(dx, dy, dz), verts=bm.verts)
    return bm


def bm_bounds(bm):
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    zs = [v.co.z for v in bm.verts]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def tri_count(bm):
    return sum(len(f.verts) - 2 for f in bm.faces)


def _outward(bm):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


def box(x0, x1, y0, y1, z0, z1, mat=SLOT_TRIM, bevel=0.0, edge_filter=None):
    """Closed box; optional chamfer (1 segment) on all edges or on those accepted by edge_filter(edge)."""
    b = bmesh.new()
    bmesh.ops.create_cube(b, size=1.0)
    for v in b.verts:
        v.co.x = x1 if v.co.x > 0 else x0
        v.co.y = y1 if v.co.y > 0 else y0
        v.co.z = z1 if v.co.z > 0 else z0
    if bevel > 0:
        edges = [e for e in b.edges if edge_filter is None or edge_filter(e)]
        bmesh.ops.bevel(b, geom=edges, offset=bevel, offset_type='OFFSET', profile=0.5, segments=1,
                        affect='EDGES', clamp_overlap=True, loop_slide=True)
    _outward(b)
    bm_set_mat(b, mat)
    return b


def prism(poly, axis, a0, a1, mat=SLOT_TRIM):
    """Closed prism.  poly = [(p, q), ...] (simple polygon) in the plane perpendicular to axis.
    axis 'x': (p,q)=(y,z); 'y': (p,q)=(x,z); 'z': (p,q)=(x,y).  Extruded from a0 to a1 along axis."""
    b = bmesh.new()

    def w(p, q, a):
        if axis == 'x':
            return (a, p, q)
        if axis == 'y':
            return (p, a, q)
        return (p, q, a)

    ring0 = [b.verts.new(w(p, q, a0)) for p, q in poly]
    ring1 = [b.verts.new(w(p, q, a1)) for p, q in poly]
    n = len(poly)
    b.faces.new(ring0)
    b.faces.new(ring1)
    for i in range(n):
        j = (i + 1) % n
        b.faces.new((ring0[i], ring0[j], ring1[j], ring1[i]))
    _outward(b)
    bm_set_mat(b, mat)
    return b


def hull_from_points(points, mat=SLOT_RUBBLE, merge_coplanar=True):
    """Convex hull solid of a point cloud."""
    b = bmesh.new()
    for p in points:
        b.verts.new(p)
    res = bmesh.ops.convex_hull(b, input=b.verts, use_existing_faces=False)
    dead = list(res.get('geom_interior', [])) + list(res.get('geom_unused', []))
    dead_verts = list({g for g in dead if isinstance(g, bmesh.types.BMVert)})
    if dead_verts:
        bmesh.ops.delete(b, geom=dead_verts, context='VERTS')
    stray = [v for v in b.verts if not v.link_faces]
    if stray:
        bmesh.ops.delete(b, geom=stray, context='VERTS')
    if merge_coplanar:
        bmesh.ops.dissolve_limit(b, angle_limit=math.radians(0.6), verts=b.verts, edges=b.edges)
    _outward(b)
    bm_set_mat(b, mat)
    return b


def bevel_all(bm, offset, angle_min_deg=20.0, segments=1):
    """Chamfer every sufficiently sharp convex edge of a closed solid."""
    edges = []
    for e in bm.edges:
        if len(e.link_faces) == 2:
            if e.calc_face_angle(0.0) >= math.radians(angle_min_deg) and e.is_convex:
                edges.append(e)
    if edges:
        bmesh.ops.bevel(bm, geom=edges, offset=offset, offset_type='OFFSET', profile=0.5,
                        segments=segments, affect='EDGES', clamp_overlap=True, loop_slide=True)
    return bm


def inflate(bm, d):
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * d
    return bm


def combine(*bms, mat=None):
    out = bmesh.new()
    for b in bms:
        if b is not None:
            bm_append(out, b, mat)
    return out


# ----------------------------------------------------------------------------------------------
# lattice box surface (used by cliffs): closed box surface on a lattice, vertices shared across faces
# ----------------------------------------------------------------------------------------------
def lattice_box(L, T, H, nx, ny, nz, mat=SLOT_MASONRY, flat_back_bottom=False):
    b = bmesh.new()
    vd = {}

    def vert(i, j, k):
        key = (i, j, k)
        if key not in vd:
            vd[key] = b.verts.new((L * i / nx, T * j / ny, H * k / nz))
        return vd[key]

    def quad(a, c, d, e):
        f = b.faces.new((a, c, d, e))
        f.material_index = mat
        return f

    for i in range(nx):
        for k in range(nz):
            quad(vert(i, 0, k), vert(i + 1, 0, k), vert(i + 1, 0, k + 1), vert(i, 0, k + 1))
            if not flat_back_bottom:
                quad(vert(i, ny, k), vert(i + 1, ny, k), vert(i + 1, ny, k + 1), vert(i, ny, k + 1))
    for i in range(nx):
        for j in range(ny):
            if not flat_back_bottom:
                quad(vert(i, j, 0), vert(i + 1, j, 0), vert(i + 1, j + 1, 0), vert(i, j + 1, 0))
            quad(vert(i, j, nz), vert(i + 1, j, nz), vert(i + 1, j + 1, nz), vert(i, j + 1, nz))
    if flat_back_bottom:
        # back (j = ny) and bottom (k = 0) are single n-gons on the perimeter loops (flat, hidden)
        loop = ([vert(i, ny, 0) for i in range(nx)] + [vert(nx, ny, k) for k in range(nz)]
                + [vert(i, ny, nz) for i in range(nx, 0, -1)] + [vert(0, ny, k) for k in range(nz, 0, -1)])
        f = b.faces.new(loop)
        f.material_index = mat
        loop = ([vert(i, 0, 0) for i in range(nx)] + [vert(nx, j, 0) for j in range(ny)]
                + [vert(i, ny, 0) for i in range(nx, 0, -1)] + [vert(0, j, 0) for j in range(ny, 0, -1)])
        f = b.faces.new(loop)
        f.material_index = mat
    for j in range(ny):
        for k in range(nz):
            quad(vert(0, j, k), vert(0, j + 1, k), vert(0, j + 1, k + 1), vert(0, j, k + 1))
            quad(vert(nx, j, k), vert(nx, j + 1, k), vert(nx, j + 1, k + 1), vert(nx, j, k + 1))
    _outward(b)
    return b


# ----------------------------------------------------------------------------------------------
# height-field cutter solid: surface c = f(a, b) over [a0,a1]x[b0,b1], flat back at c_back
# ----------------------------------------------------------------------------------------------
def hf_solid(a0, a1, b0, b1, f, c_back, na, nb, order=('x', 'y', 'z'), mat=SLOT_RUBBLE, rng=None):
    """Closed solid between the height field c=f(a,b) and the plane c=c_back.  `order` maps (a,b,c) to
    world axes.  Triangle diagonals are chosen at random (faceted look) when rng is given."""
    b = bmesh.new()

    def w(a, bb, c):
        d = {order[0]: a, order[1]: bb, order[2]: c}
        return (d['x'], d['y'], d['z'])

    g = [[None] * (nb + 1) for _ in range(na + 1)]
    for i in range(na + 1):
        for j in range(nb + 1):
            a = a0 + (a1 - a0) * i / na
            bb = b0 + (b1 - b0) * j / nb
            g[i][j] = b.verts.new(w(a, bb, f(a, bb)))
    for i in range(na):
        for j in range(nb):
            v00, v10, v11, v01 = g[i][j], g[i + 1][j], g[i + 1][j + 1], g[i][j + 1]
            if rng is not None and rng.random() < 0.5:
                b.faces.new((v00, v10, v01))
                b.faces.new((v10, v11, v01))
            else:
                b.faces.new((v00, v10, v11))
                b.faces.new((v00, v11, v01))
    # back ring
    ring = []
    for i in range(na):
        ring.append((i, 0))
    for j in range(nb):
        ring.append((na, j))
    for i in range(na, 0, -1):
        ring.append((i, nb))
    for j in range(nb, 0, -1):
        ring.append((0, j))
    backs = []
    for (i, j) in ring:
        a = a0 + (a1 - a0) * i / na
        bb = b0 + (b1 - b0) * j / nb
        backs.append(b.verts.new(w(a, bb, c_back)))
    n = len(ring)
    for k in range(n):
        k2 = (k + 1) % n
        i1, j1 = ring[k]
        i2, j2 = ring[k2]
        b.faces.new((g[i1][j1], g[i2][j2], backs[k2], backs[k]))
    b.faces.new(backs)
    _outward(b)
    bm_set_mat(b, mat)
    return b


# ----------------------------------------------------------------------------------------------
# boolean (exact) -- difference only
# ----------------------------------------------------------------------------------------------
def _tmp_obj(bm, name, mats):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def boolean_diff(target, cutter):
    """Return a new bmesh = target - cutter (exact solver, self-overlap tolerant).  Cutter face material
    indices are kept on the new (cut) faces."""
    mats = get_materials()
    dummy = bpy.data.materials.get("_HIDDEN") or bpy.data.materials.new("_HIDDEN")
    mats = list(mats) + [dummy]          # slot 3 = 'hidden cavity' tag (faces removed by the caller)
    ot = _tmp_obj(target, "_bt", mats)
    oc = _tmp_obj(cutter, "_bc", mats)
    md = ot.modifiers.new("bool", 'BOOLEAN')
    md.operation = 'DIFFERENCE'
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
    # tidy
    bmesh.ops.dissolve_degenerate(out, dist=1e-4, edges=out.edges)
    for f in out.faces:
        f.smooth = True
    return out


# ----------------------------------------------------------------------------------------------
# face frames and masonry relief cutters
# ----------------------------------------------------------------------------------------------
class FaceFrame:
    """A wall face in world space.  u = direction along the face, n = outward normal, q = depth into the
    wall (q > 0 inside), z = world height."""

    def __init__(self, origin, u, n_out):
        self.o = Vector(origin)
        self.u = Vector(u).normalized()
        self.n = Vector(n_out).normalized()

    def p(self, u, q, z):
        return self.o + self.u * u - self.n * q + UP * z


def _mk(frame, loops, mat=SLOT_MASONRY):
    """Build a closed convex-ish solid from loops given as lists of (u, q, z); loops share vertex counts
    and are connected in order (e.g. two rings -> prism, ring + ring -> frustum)."""
    b = bmesh.new()
    rings = [[b.verts.new(frame.p(*pt)) for pt in lp] for lp in loops]
    n = len(rings[0])
    b.faces.new(rings[0])
    b.faces.new(rings[-1])
    for r in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            b.faces.new((rings[r][i], rings[r][j], rings[r + 1][j], rings[r + 1][i]))
    _outward(b)
    bm_set_mat(b, mat)
    return b


def make_courses(total, seed, vary=False, unit=50):
    """Course heights summing exactly to `total` (multiples of 25)."""
    rng = random.Random(seed)
    if not vary:
        n = int(total // unit)
        rest = total - n * unit
        out = [unit] * n
        if rest > 0:
            out.append(rest)
        return out
    out, s = [], 0
    while s < total:
        rem = total - s
        opts = [h for h in (25, 50, 50, 50, 75) if h <= rem]
        h = rng.choice(opts)
        if rem - h in (0,) or rem - h >= 25:
            out.append(h)
            s += h
        else:
            out.append(rem)
            s += rem
    return out


def stagger_joints(L, courses, seed, wmin=60, wmax=140, min_off=18, edge_min=38):
    """Per-course interior vertical joint positions, staggered against the previous course."""
    rng = random.Random(seed)
    rows = []
    prev = []
    for _ in courses:
        for attempt in range(200):
            xs, x = [], 0.0
            while True:
                x += rng.uniform(wmin, wmax)
                if x > L - edge_min:
                    break
                xs.append(round(x, 1))
            if xs and (xs[-1] > L - edge_min or L - xs[-1] < edge_min):
                xs.pop()
            if not xs and L > 2 * edge_min and L > wmax:
                continue
            if all(abs(a - b) >= min_off for a in xs for b in prev):
                break
        rows.append(xs)
        prev = xs
    return rows


def relief_cutters(frame, u0, u1, z0, z1, courses, seed, *, joint_depth=1.5, joint_w=3.0,
                   vertical=True, recess_prob=0.2, chips=4, wmin=70, wmax=150, z_start=0.0,
                   end_open=True, groove_mat=SLOT_MASONRY, chip_mat=SLOT_RUBBLE, h_grooves=True):
    """Cutter solids that carve ashlar relief (V-grooves between courses and blocks, shallow weathered
    recesses, small chips) into the face at u in [u0,u1], z in [z0,z1]."""
    rng = random.Random(seed)
    cut = bmesh.new()
    d, hw = joint_depth, joint_w * 0.5
    ext = (d + 1.0) / d
    L = u1 - u0
    # course boundaries
    zb = [z_start]
    for h in courses:
        zb.append(zb[-1] + h)
    zb = [z for z in zb if z0 - 1e-6 <= z <= z1 + 1e-6]
    # horizontal grooves at interior boundaries
    ua = u0 - (1.0 if end_open else 0.0)
    ub = u1 + (1.0 if end_open else 0.0)
    if h_grooves:
        for z in zb[1:-1] if len(zb) > 2 else []:
            jd = d * rng.uniform(0.8, 1.2)
            e2 = (jd + 1.0) / jd
            tri = [(-1.0, z - hw * e2), (-1.0, z + hw * e2), (jd, z)]
            lps = [[(ua, q, zz) for q, zz in tri], [(ub, q, zz) for q, zz in tri]]
            bm_append(cut, _mk(frame, lps, groove_mat))
    # vertical joints per course
    rows = stagger_joints(L, courses, seed + 1, wmin, wmax)
    blocks = []
    for ci in range(len(zb) - 1):
        za, zc = zb[ci], zb[ci + 1]
        xs = [u0] + [u0 + x for x in rows[min(ci, len(rows) - 1)]] + [u1]
        for k in range(len(xs) - 1):
            blocks.append((xs[k], xs[k + 1], za, zc))
        if vertical:
            for x in xs[1:-1]:
                jd = d * rng.uniform(0.8, 1.2)
                e2 = (jd + 1.0) / jd
                tri = [(x - hw * e2, -1.0), (x + hw * e2, -1.0), (x, jd)]
                lps = [[(uu, q, za) for uu, q in tri], [(uu, q, zc) for uu, q in tri]]
                bm_append(cut, _mk(frame, lps, groove_mat))
    # weathered recesses
    for (ba, bb, za, zc) in blocks:
        if rng.random() < recess_prob and (bb - ba) > 30 and (zc - za) > 30:
            m = rng.uniform(4.0, 9.0)
            dd = rng.uniform(0.7, 1.6)
            x0, x1, y0, y1 = ba + m, bb - m, za + m, zc - m
            if x1 - x0 < 8 or y1 - y0 < 8:
                continue
            lo = [(x0 - 1.0, -1.0, y0 - 1.0), (x1 + 1.0, -1.0, y0 - 1.0), (x1 + 1.0, -1.0, y1 + 1.0), (x0 - 1.0, -1.0, y1 + 1.0)]
            hi = [(x0 + dd, dd, y0 + dd), (x1 - dd, dd, y0 + dd), (x1 - dd, dd, y1 - dd), (x0 + dd, dd, y1 - dd)]
            bm_append(cut, _mk(frame, [lo, hi], groove_mat))
    # chips at block corners
    corners = []
    for (ba, bb, za, zc) in blocks:
        for cu in (ba, bb):
            for cz in (za, zc):
                if u0 < cu < u1 or (end_open is False):
                    corners.append((cu, cz))
    for _ in range(chips):
        if not corners:
            break
        cu, cz = rng.choice(corners)
        r = rng.uniform(4.5, 9.0)
        depth = rng.uniform(1.4, 3.0)
        pts = []
        for _k in range(7):
            v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
            if v.length < 0.3:
                v = v.normalized() * 0.5
            v *= r
            pts.append(v)
        cq = depth - r * 0.9
        h = hull_from_points([frame.p(cu + v.x, cq + v.y, cz + v.z) for v in pts], chip_mat, merge_coplanar=False)
        # make the chip piece sit on the face: require hull valid
        if len(h.faces) >= 4:
            bm_append(cut, h)
    return cut


# ----------------------------------------------------------------------------------------------
# arches / openings
# ----------------------------------------------------------------------------------------------
def arch_apex_angle(half_w, R, t):
    """Angle (rad, measured from +X at the arc centre) where the left arc of radius R+t reaches x = cx."""
    c = (half_w - R) / (R + t)
    return math.acos(max(-1.0, min(1.0, c)))


def arch_point(cx, zs, half_w, R, t, alpha, side=-1):
    """Point on the arc of radius R+t at parameter alpha in [0,1] (0 = springline, 1 = apex).
    side -1 = left arc, +1 = right arc."""
    th0 = math.pi
    th1 = arch_apex_angle(half_w, R, t)
    th = th0 + (th1 - th0) * alpha
    ccx = cx - half_w + R            # centre of the left arc (on the right springpoint for R == w)
    x = ccx + (R + t) * math.cos(th)
    z = zs + (R + t) * math.sin(th)
    if side > 0:
        x = 2 * cx - x
    return x, z


def arch_polygon(cx, z_bot, zs, half_w, R, t, n_arc=14):
    """Outline (x, z) of a pointed opening (jambs + two-centred arch) offset radially by t."""
    left = [arch_point(cx, zs, half_w, R, t, i / n_arc, -1) for i in range(n_arc + 1)]
    right = [arch_point(cx, zs, half_w, R, t, i / n_arc, +1) for i in range(n_arc, -1, -1)]
    # left arc runs springpoint -> apex, so the polygon is: bottom-left, up to springline, arc to apex,
    # arc down, springline right, bottom-right
    poly = [(cx - half_w - t, z_bot)] + left + right[1:] + [(cx + half_w + t, z_bot)]
    # remove duplicate apex
    out = []
    for p in poly:
        if not out or (abs(p[0] - out[-1][0]) > 1e-6 or abs(p[1] - out[-1][1]) > 1e-6):
            out.append(p)
    if len(out) > 2 and abs(out[0][0] - out[-1][0]) < 1e-9 and abs(out[0][1] - out[-1][1]) < 1e-9:
        out.pop()
    return out


def arch_ring_stones(cx, zs, half_w, R, t0, t1, n, ya, yb, rng, alt=7.0, bevel=2.0, mat=SLOT_TRIM):
    """Voussoirs of one ring (both halves) between radial offsets t0..t1, extruded over Y in [ya, yb]."""
    out = bmesh.new()
    for side in (-1, 1):
        for k in range(n):
            a0, a1 = k / n, (k + 1) / n
            to = t1 + (alt if (k % 2 == 0 and k != n - 1) else 0.0)
            quad = [arch_point(cx, zs, half_w, R, t0, a0, side), arch_point(cx, zs, half_w, R, to, a0, side),
                    arch_point(cx, zs, half_w, R, to, a1, side), arch_point(cx, zs, half_w, R, t0, a1, side)]
            s = prism(quad, 'y', ya, yb, mat)
            bevel_all(s, bevel, 25.0)
            bm_append(out, s)
    return out


def jamb_stones(cx, z_bot, zs, half_w, t0, t1, ya, yb, rng, h_target=46.0, alt=8.0, bevel=2.0, mat=SLOT_TRIM):
    out = bmesh.new()
    total = zs - z_bot
    m = max(1, int(round(total / h_target)))
    hs = [rng.uniform(0.8, 1.2) for _ in range(m)]
    sc = total / sum(hs)
    hs = [h * sc for h in hs]
    for side in (-1, 1):
        z = z_bot
        for k, h in enumerate(hs):
            to = t1 + (alt if (k % 2 == 1) else 0.0)
            if side < 0:
                xa, xb = cx - half_w - to, cx - half_w - t0
            else:
                xa, xb = cx + half_w + t0, cx + half_w + to
            s = box(xa, xb, ya, yb, z, z + h, mat, bevel)
            bm_append(out, s)
            z += h
    return out


class Opening:
    """Pointed opening: ring orders of dressed stones + the cutters that carve the host wall."""

    def __init__(self, cx, z_bot, zs, w, R, orders, T, seed, dressed_depth=None, rough_extra=None,
                 blind_depth=None, n_vouss=6, bevel=2.0, z_stone_bot=None, jamb_h=46.0, alt=7.0):
        self.cx, self.z_bot, self.zs, self.w, self.R = cx, z_bot, zs, w, R
        self.half_w = w * 0.5
        self.orders, self.T = orders, T
        rng = random.Random(seed)
        stones = bmesh.new()
        carve = bmesh.new()
        zsb = z_bot if z_stone_bot is None else z_stone_bot
        t_max = max(o['t1'] for o in orders)
        self.t_max = t_max

        def yranges(o):
            r = o.get('recess', 0.0)
            if dressed_depth is None and blind_depth is None:      # through
                return [(r, T - r)]
            if blind_depth is not None:                            # blind recess, front only
                return [(r, blind_depth + o.get('lip', 6.0))]
            return [(r, dressed_depth), (T - dressed_depth, T - r)]

        for o in orders:
            for (ya, yb) in yranges(o):
                stones_o = arch_ring_stones(cx, zs, self.half_w, R, o['t0'], o['t1'], n_vouss, ya, yb, rng, alt=alt, bevel=bevel)
                bm_append(stones, stones_o)
                js = jamb_stones(cx, zsb, zs, self.half_w, o['t0'], o['t1'], ya, yb, rng, jamb_h, alt, bevel)
                bm_append(stones, js)
                # carve the whole region inside this order's extrados over its Y range
                poly = arch_polygon(cx, z_bot - 1.0 if z_bot <= 0 else z_bot, zs, self.half_w, R, o['t1'])
                bm_append(carve, prism(poly, 'y', ya - (1.0 if ya <= 0.01 else 0.0), yb + (1.0 if yb >= T - 0.01 else 0.0), SLOT_TRIM))
        if blind_depth is not None:
            poly = arch_polygon(cx, z_bot, zs, self.half_w, R, 0.0)
            bm_append(carve, prism(poly, 'y', -1.0, blind_depth, SLOT_TRIM))
        elif dressed_depth is not None:
            ex = rough_extra if rough_extra is not None else 3.0
            poly = arch_polygon(cx, z_bot - 1.0, zs, self.half_w, R, ex)
            bm_append(carve, prism(poly, 'y', dressed_depth - 4.0, T - dressed_depth + 4.0, SLOT_RUBBLE))
        # inflated copy of the stones so the quoin-like protrusions are carved too
        infl = stones.copy()
        inflate(infl, 0.35)
        bm_append(carve, infl)
        infl.free()
        self.stones = stones
        self.carve = carve


def quoin_stones(x_face0, x_face1, y_face0, y_face1, z0, z1, courses, corner, long_len=46.0, short_len=28.0,
                 bevel=2.2, mat=SLOT_TRIM):
    """Alternating long/short corner stones.  corner = (sx, sy) in {-1,+1}: which corner of the footprint
    (x_face0..x_face1) x (y_face0..y_face1) the quoins wrap around (sx=-1: min X side)."""
    out = bmesh.new()
    sx, sy = corner
    cx = x_face0 if sx < 0 else x_face1
    cy = y_face0 if sy < 0 else y_face1
    z = z0
    k = 0
    for h in courses:
        if z >= z1 - 1e-6:
            break
        zt = min(z1, z + h)
        lx, ly = (long_len, short_len) if k % 2 == 0 else (short_len, long_len)
        xa, xb = (cx, cx + lx) if sx < 0 else (cx - lx, cx)
        ya, yb = (cy, cy + ly) if sy < 0 else (cy - ly, cy)
        outer = (lambda e, cx=cx, cy=cy: all(abs(v.co.x - cx) < 1e-6 for v in e.verts) or all(abs(v.co.y - cy) < 1e-6 for v in e.verts))
        bm_append(out, box(xa, xb, ya, yb, z, zt, mat, bevel, edge_filter=outer))
        z = zt
        k += 1
    return out


# ----------------------------------------------------------------------------------------------
# finishing: UV0 (box projection), vertex colour, smoothing, collision
# ----------------------------------------------------------------------------------------------
def finalize(bm, smooth_deg=30.0, keep_uv=False):
    bm.normal_update()
    bm.faces.ensure_lookup_table()
    uv = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    col = bm.loops.layers.color.get("Color") or bm.loops.layers.color.new("Color")
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        pos = n[ax] >= 0
        d = ax * 2 + (0 if pos else 1)
        for l in f.loops:
            c = l.vert.co
            if ax == 0:
                u, v = (c.y, c.z) if pos else (-c.y, c.z)
            elif ax == 1:
                u, v = (-c.x, c.z) if pos else (c.x, c.z)
            else:
                u, v = (c.x, c.y) if pos else (c.x, -c.y)
            if not keep_uv:
                l[uv].uv = (u / UV_CM_PER_UNIT + d * UV_DIR_OFFSET, v / UV_CM_PER_UNIT)
            l[col] = (1.0, 1.0, 1.0, 1.0)
    lim = math.radians(smooth_deg)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        if len(e.link_faces) == 2:
            e.smooth = e.calc_face_angle(0.0) <= lim
        else:
            e.smooth = True
    return bm


def box_hull(x0, x1, y0, y1, z0, z1):
    """Collision box (convex, 12 tris merged to quads)."""
    return box(x0, x1, y0, y1, z0, z1, SLOT_MASONRY, 0.0)


def cylinder(r, h, segs, mat=SLOT_TRIM):
    """Capped cylinder along +Z: axis through the origin, z in [0, h], `segs` side quads (props helper)."""
    b = bmesh.new()
    lo = [b.verts.new((r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs), 0.0)) for i in range(segs)]
    hi = [b.verts.new((r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs), h)) for i in range(segs)]
    b.faces.new(lo)
    b.faces.new(hi)
    for i in range(segs):
        j = (i + 1) % segs
        b.faces.new((lo[i], lo[j], hi[j], hi[i]))
    _outward(b)
    bm_set_mat(b, mat)
    return b


def ring(r_out, r_in, h, segs, mat=SLOT_TRIM):
    """Annulus prism along +Z (outer radius r_out, hole radius r_in), z in [0, h] (props helper)."""
    b = bmesh.new()

    def circ(r, z):
        return [b.verts.new((r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs), z)) for i in range(segs)]

    oo0, oo1, ii0, ii1 = circ(r_out, 0.0), circ(r_out, h), circ(r_in, 0.0), circ(r_in, h)
    for i in range(segs):
        j = (i + 1) % segs
        b.faces.new((oo0[i], oo0[j], oo1[j], oo1[i]))      # outer wall
        b.faces.new((ii0[i], ii0[j], ii1[j], ii1[i]))      # inner wall
        b.faces.new((oo1[i], oo1[j], ii1[j], ii1[i]))      # top
        b.faces.new((oo0[i], oo0[j], ii0[j], ii0[i]))      # bottom
    _outward(b)
    bm_set_mat(b, mat)
    return b


# ----------------------------------------------------------------------------------------------
# export
# ----------------------------------------------------------------------------------------------
def _to_object(bm, name, mats, ue_y_flip, link=True, collection=None):
    b = bm.copy()
    if ue_y_flip:
        for v in b.verts:
            v.co.y = -v.co.y
        bmesh.ops.reverse_faces(b, faces=b.faces)
    me = bpy.data.meshes.new(name)
    b.to_mesh(me)
    b.free()
    if mats:
        for m in mats:
            me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


def export_piece_fbx(name, bm, ucx_bms, path, mats=None):
    """Export bm (+ UCX convex hull meshes) to FBX at `path` with Unreal-correct axes and units.
    mats = list of bpy materials for the slots (default: the three kit materials)."""
    mats = get_materials() if mats is None else mats
    objs = [_to_object(bm, name, mats, True)]
    for i, ub in enumerate(ucx_bms):
        objs.append(_to_object(ub, "UCX_%s_%02d" % (name, i), None, True))
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, use_visible=False, object_types={'MESH'},
        apply_unit_scale=True, global_scale=1.0, apply_scale_options='FBX_SCALE_NONE',
        axis_forward='Y', axis_up='Z', use_space_transform=True, bake_space_transform=False,
        use_mesh_modifiers=False, mesh_smooth_type='OFF', colors_type='SRGB', prioritize_active_color=True,
        use_tspace=False, use_triangles=False, use_custom_props=False, path_mode='AUTO', bake_anim=False,
        add_leaf_bones=False)
    for o in objs:
        me = o.data
        bpy.data.objects.remove(o)
        bpy.data.meshes.remove(me)


def add_to_layout(name, bm, ucx_bms, location, mats=None):
    """Un-mirrored copy for the review .blend (authoring space)."""
    mats = get_materials() if mats is None else mats
    ob = _to_object(bm, name, mats, False)
    ob.location = location
    for i, ub in enumerate(ucx_bms):
        u = _to_object(ub, "UCX_%s_%02d" % (name, i), None, False)
        u.display_type = 'WIRE'
        u.hide_render = True
        u.parent = ob
    return ob


# ----------------------------------------------------------------------------------------------
# P8 chapel helpers: lofts, 2D outlines (pointed / trefoil lights, quatrefoil, offset), lathe, densify
# ----------------------------------------------------------------------------------------------
def loft_y(poly_a, ya, poly_b, yb, mat=SLOT_TRIM, triangulate=True):
    """Closed solid between two (x, z) polygons with the same vertex count at y = ya and y = yb (ruled sides).
    Used for splayed reveals: the two profiles may differ in size."""
    b = bmesh.new()
    ra = [b.verts.new((x, ya, z)) for x, z in poly_a]
    rb = [b.verts.new((x, yb, z)) for x, z in poly_b]
    n = len(ra)
    b.faces.new(ra)
    b.faces.new(rb)
    for i in range(n):
        j = (i + 1) % n
        b.faces.new((ra[i], ra[j], rb[j], rb[i]))
    _outward(b)
    if triangulate:
        bmesh.ops.triangulate(b, faces=b.faces[:])
    bm_set_mat(b, mat)
    return b


def arch_dims(w, ratio):
    """(half width, radius, rise above the springing line) of a two-centred pointed arch of span w, R = ratio * w."""
    half = w * 0.5
    R = ratio * w
    return half, R, math.sqrt(R * R - (R - half) ** 2)


def arch_band(cx, zs, w, ratio, t0, t1, z_bot=None, n_arc=16):
    """Closed (x, z) outline of a band between the radial offsets t0 and t1 of a pointed arch, legs down to z_bot
    (default: the springing line, i.e. the legs have zero length)."""
    half, R, _ = arch_dims(w, ratio)
    zb = zs if z_bot is None else z_bot
    outer = arch_polygon(cx, zb, zs, half, R, t1, n_arc)
    inner = arch_polygon(cx, zb, zs, half, R, t0, n_arc)
    return outer + inner[::-1]


def pointed_light_poly(cx, z_bot, zs, w, R, cusp=0.0, cusp_u=0.55, cusp_du=0.045, n_arc=18):
    """Outline (x, z) of a pointed light: vertical jambs z_bot..zs, two-centred head of radius R.  cusp > 0 adds two
    inward-pointing tracery cusps (a trefoil head, cusp depth in cm)."""
    half = w * 0.5
    left = []
    for i in range(n_arc + 1):
        u = i / n_arc
        left.append(arch_point(cx, zs, half, R, 0.0, u, -1))
    if cusp > 0.0:
        ccx = cx - half + R
        new = []
        for i, p in enumerate(left):
            u = i / n_arc
            if abs(u - cusp_u) < 0.5 / n_arc + 1e-9:
                a = arch_point(cx, zs, half, R, 0.0, cusp_u - cusp_du, -1)
                c = arch_point(cx, zs, half, R, 0.0, cusp_u, -1)
                d = arch_point(cx, zs, half, R, 0.0, cusp_u + cusp_du, -1)
                vx, vz = ccx - c[0], zs - c[1]
                ln = math.hypot(vx, vz)
                tip = (c[0] + vx / ln * cusp, c[1] + vz / ln * cusp)
                new += [a, tip, d]
            else:
                new.append(p)
        left = new
    right = [(2 * cx - x, z) for (x, z) in left[::-1]]
    poly = [(cx - half, z_bot)] + left + right[1:] + [(cx + half, z_bot)]
    out = []
    for p in poly:
        if not out or abs(p[0] - out[-1][0]) > 1e-6 or abs(p[1] - out[-1][1]) > 1e-6:
            out.append(p)
    if len(out) > 2 and abs(out[0][0] - out[-1][0]) < 1e-9 and abs(out[0][1] - out[-1][1]) < 1e-9:
        out.pop()
    return out


def quatrefoil_poly(cx, cz, r_out, n=96, rot_deg=45.0):
    """Four overlapping circular lobes (union outline); r_out = radius of the circumscribed circle."""
    rho = 0.5333 * r_out
    d = r_out - rho
    pts = []
    for k in range(n):
        th = 2 * math.pi * k / n
        r = 0.0
        for q in range(4):
            phi = math.radians(rot_deg) + q * math.pi / 2
            dl = th - phi
            s = d * math.sin(dl)
            if abs(s) < rho:
                r = max(r, d * math.cos(dl) + math.sqrt(rho * rho - s * s))
        pts.append((cx + r * math.cos(th), cz + r * math.sin(th)))
    return pts


def poly_area(p):
    return 0.5 * sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))


def offset_poly(p, d):
    """Offset a simple closed (x, z) polygon outward by d (per-vertex mitre, clamped); d < 0 shrinks."""
    n = len(p)
    sgn = 1.0 if poly_area(p) > 0 else -1.0
    out = []
    for i in range(n):
        a, b, c = p[i - 1], p[i], p[(i + 1) % n]
        e1 = (b[0] - a[0], b[1] - a[1])
        e2 = (c[0] - b[0], c[1] - b[1])
        l1, l2 = math.hypot(*e1) or 1.0, math.hypot(*e2) or 1.0
        n1 = (e1[1] / l1 * sgn, -e1[0] / l1 * sgn)
        n2 = (e2[1] / l2 * sgn, -e2[0] / l2 * sgn)
        mx, mz = n1[0] + n2[0], n1[1] + n2[1]
        ml = math.hypot(mx, mz) or 1.0
        mx, mz = mx / ml, mz / ml
        cos_h = max(0.45, mx * n1[0] + mz * n1[1])
        out.append((b[0] + mx * d / cos_h, b[1] + mz * d / cos_h))
    return out


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


def lathe_z(profile, segs=16, mat=SLOT_TRIM, cap_bottom=True, cap_top=True):
    """Solid of revolution around +Z from [(r, z), ...]; r == 0 points become apexes (and are not capped)."""
    b = bmesh.new()
    rings = []
    for r, z in profile:
        if r <= 1e-9:
            rings.append(b.verts.new((0.0, 0.0, z)))
        else:
            rings.append([b.verts.new((r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs), z)) for i in range(segs)])
    if isinstance(rings[0], list) and cap_bottom:
        b.faces.new(rings[0])
    if isinstance(rings[-1], list) and cap_top:
        b.faces.new(rings[-1])
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
    _outward(b)
    bm_set_mat(b, mat)
    return b
