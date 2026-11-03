"""concepts.py -- P12-3: three blockout concepts of the Warden (A Penitent, B Bell-Bearer, C Veiled Saint).

    blender.exe -b --factory-startup --python Tools/blender/warden/concepts.py -- [--only a|b|c ...] [--out SourceArt/Warden/concepts]

Writes one review .blend per concept (concept_a.blend ...; NOT committed) and Docs/ArtTest/warden/p12_concepts_report.json
(measured height / mask Z / width in the held pose, the joint angles used).  Seeded: a rerun gives the same geometry.
render_concepts.py renders the .blends and builds the comparison sheets.

Conventions: 1 Blender unit = 1 cm, authoring space == Unreal space (+Z up); the figure faces -Y, its left is +X.
The held pose is computed with forward kinematics on the P12-5 joint table (cm), see class Pose.  The body is a
lofted irregular robe (no cloth simulation), thin bare forearms and hands built from finger chains, and each
concept adds its own head and upper garment.  Flat colours only.
"""
import json
import math
import os
import random
import sys
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
OUT_DIR = os.path.join(ROOT, "SourceArt", "Warden", "concepts")
REPORT = os.path.join(ROOT, "Docs", "ArtTest", "warden", "p12_concepts_report.json")

# ----------------------------------------------------------------------------------------------------------------------
# colours (linear RGB, metallic, roughness) -- flat tints only
COL = {
    "robe": ((0.035, 0.028, 0.022), 0.0, 0.85),
    "skin": ((0.22, 0.19, 0.17), 0.0, 0.65),
    "bone": ((0.62, 0.56, 0.44), 0.0, 0.6),
    "bronze": ((0.38, 0.24, 0.12), 1.0, 0.45),
    "verdigris": ((0.17, 0.32, 0.27), 0.0, 0.7),
    "iron": ((0.09, 0.08, 0.07), 1.0, 0.6),
    "linen": ((0.5, 0.46, 0.38), 0.0, 0.5),
    "rope": ((0.22, 0.17, 0.10), 0.0, 0.9),
    "dark": ((0.003, 0.003, 0.003), 0.0, 0.9),
    "linen_old": ((0.30, 0.27, 0.21), 0.0, 0.7),
}

# ----------------------------------------------------------------------------------------------------------------------
# held pose (degrees).  Plan values: spine 6,7,8,8,9 (38 total), neck 10, head -14, pelvis 12 cm back, knees 6.
# Each may move +-5.  The values below are the final ones (see the report).
ANG = {
    "back": 12.0,                           # pelvis shifted back (+Y), cm
    "spine": [3.0, 8.0, 13.0, 13.0, 14.0],  # spine_01..05 pitch forward
    "neck": [8.0, 5.0],                     # neck_01, neck_02
    "head": -19.0,                          # head pitch (negative = back up)
    "knee": 6.0,
    "arm_abd": [7.0, 4.0, 3.0],             # upper arm / forearm / hand: outward from vertical
    "arm_fwd": [8.0, 17.0, 24.0],           # forward from vertical
    "finger_curl": 15.0,
}
UPPER_LEN = 58.0
FORE_LEN = 58.0

REST = [  # (name, y, z) of the spine chain, from the P12-5 joint table
    ("pelvis", 0, 128), ("spine_01", 0, 140), ("spine_02", -1, 155), ("spine_03", -2, 172), ("spine_04", -3, 190),
    ("spine_05", -4, 208), ("neck_01", -6, 226), ("neck_02", -8, 240), ("head", -10, 254),
]


def rot2(dy, dz, deg):
    a = math.radians(deg)
    return dy * math.cos(a) - dz * math.sin(a), dy * math.sin(a) + dz * math.cos(a)


def smooth1(a, sigma):
    k = int(sigma * 3) + 1
    x = np.arange(-k, k + 1)
    w = np.exp(-0.5 * (x / sigma) ** 2)
    w /= w.sum()
    return np.convolve(np.pad(a, (k, k), mode="edge"), w, mode="valid")


def norm(v, axis=-1):
    n = np.linalg.norm(v, axis=axis, keepdims=True)
    return v / np.maximum(n, 1e-9)


# ----------------------------------------------------------------------------------------------------------------------
class Pose:
    """Forward kinematics of the spine / neck / head and the arm chains."""

    def __init__(self, ang=ANG):
        self.ang = ang
        angs = [0.0] + list(ang["spine"]) + list(ang["neck"]) + [ang["head"]]
        pos = [(REST[0][1] + ang["back"], REST[0][2])]
        cum = 0.0
        self.seg_tilt = []
        self.cum_after = {}
        for i in range(len(REST) - 1):
            cum += angs[i]
            self.cum_after[REST[i][0]] = cum
            dy = REST[i + 1][1] - REST[i][1]
            dz = REST[i + 1][2] - REST[i][2]
            ry, rz = rot2(dy, dz, cum)
            pos.append((pos[-1][0] + ry, pos[-1][1] + rz))
            self.seg_tilt.append(cum)
        self.pos = pos                      # (y, z) per joint
        self.net_head = cum + angs[-1]      # head pitch (deg, forward positive)
        self.cum_after["head"] = self.net_head
        # dense evaluation tables indexed by rest height (0.5 cm steps)
        node_h = [r[2] for r in REST]
        node_y = [p[0] for p in pos]
        node_z = [p[1] for p in pos]
        node_t = self.seg_tilt + [self.net_head]
        top_h = node_h[-1] + 90.0
        ty, tz = rot2(0, 90.0, self.net_head)
        node_h.append(top_h)
        node_y.append(node_y[-2] + 0 + ty if False else pos[-1][0] + ty)
        node_z.append(pos[-1][1] + tz)
        node_t.append(self.net_head)
        H = np.arange(0.0, 400.01, 0.5)
        self.H = H
        Y = np.where(H <= node_h[0], pos[0][0], np.interp(H, node_h, node_y))
        Z = np.where(H <= node_h[0], H, np.interp(H, node_h, node_z))
        T = np.where(H <= node_h[0], 0.0, np.interp(H, node_h, node_t))
        # beyond the last node: continue straight along the head axis
        over = H > top_h
        Y = np.where(over, node_y[-1] + (H - top_h) * -math.sin(math.radians(self.net_head)), Y)
        Z = np.where(over, node_z[-1] + (H - top_h) * math.cos(math.radians(self.net_head)), Z)
        s = 9.0
        self.Y = smooth1(Y, s)
        self.Z = smooth1(Z, s)
        self.T = smooth1(T, s)

    def eval(self, h):
        h = np.asarray(h, dtype=float)
        return (np.interp(h, self.H, self.Y), np.interp(h, self.H, self.Z), np.interp(h, self.H, self.T))

    def frame(self, h):
        y, z, t = self.eval(h)
        return y, z, t

    def head_matrix(self):
        """local head frame (origin at the head joint, +Z up the head, face towards -Y) -> world"""
        y, z = self.pos[-1]
        m = Matrix.Translation((0, y, z)) @ Matrix.Rotation(math.radians(self.net_head), 4, "X")
        return m

    def chest_origin(self, name="spine_05"):
        i = [r[0] for r in REST].index(name)
        return self.pos[i]

    # ---- arms (world-space directions are derived from the abduction / forward-flexion angles of each segment)
    def arm(self, side):
        s = 1.0 if side == "l" else -1.0
        a5 = self.cum_after["spine_05"]
        sy, sz = self.pos[[r[0] for r in REST].index("spine_05")]
        oy, oz = rot2(2.0, 8.0, a5)             # upperarm_l is (28, -2, 216): offset (28, 2, 8) from spine_05
        sh = np.array([28.0 * s, sy + oy, sz + oz])
        d = []
        for ab, fw in zip(self.ang["arm_abd"], self.ang["arm_fwd"]):
            a, f = math.radians(ab), math.radians(fw)
            d.append(norm(np.array([s * math.sin(a), -math.sin(f), -math.cos(a) * math.cos(f)])))
        elbow = sh + d[0] * UPPER_LEN
        wrist = elbow + d[1] * FORE_LEN
        return dict(side=s, shoulder=sh, elbow=elbow, wrist=wrist, d=d)


# ----------------------------------------------------------------------------------------------------------------------
class MB:
    """mesh builder: accumulates grids / tubes into one mesh with per-face material index"""

    def __init__(self):
        self.V = []
        self.F = []
        self.M = []
        self.n = 0

    def add_grid(self, P, wrap_c=False, wrap_r=False, mat=0, skip=None, flip=False):
        P = np.asarray(P, dtype=float)
        R, C, _ = P.shape
        base = self.n
        self.V.append(P.reshape(-1, 3))
        self.n += R * C
        rn = R if wrap_r else R - 1
        cn = C if wrap_c else C - 1
        rr, cc = np.meshgrid(np.arange(rn), np.arange(cn), indexing="ij")
        r1 = (rr + 1) % R
        c1 = (cc + 1) % C
        q = np.stack([base + rr * C + cc, base + rr * C + c1, base + r1 * C + c1, base + r1 * C + cc], axis=-1)
        if flip:
            q = q[..., ::-1]
        m = np.broadcast_to(np.asarray(mat), (rn, cn)).copy()
        if skip is not None:
            keep = ~np.asarray(skip, dtype=bool)
            q = q[keep]
            m = m[keep]
        else:
            q = q.reshape(-1, 4)
            m = m.reshape(-1)
        self.F.append(q)
        self.M.append(m)
        return base

    def add_tris(self, tris, mat=0):
        self.F.append(np.asarray(tris))
        self.M.append(np.full(len(tris), mat))

    def add_verts(self, P):
        base = self.n
        P = np.asarray(P, dtype=float).reshape(-1, 3)
        self.V.append(P)
        self.n += len(P)
        return base

    def to_object(self, name, mats, solid=None, smooth=True):
        V = np.concatenate(self.V) if self.V else np.zeros((0, 3))
        faces = []
        mi = []
        for f, m in zip(self.F, self.M):
            faces.extend(f.tolist())
            mi.extend(m.tolist())
        me = bpy.data.meshes.new(name)
        me.from_pydata(V.tolist(), [], faces)
        me.update()
        me.polygons.foreach_set("use_smooth", [smooth] * len(me.polygons))
        me.polygons.foreach_set("material_index", mi)
        for m in mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        if solid:
            md = ob.modifiers.new("Solid", "SOLIDIFY")
            md.thickness = solid
            md.offset = -1.0
            md.use_even_offset = False
        return ob


_MATS = {}


def mat(name):
    if name in _MATS and _MATS[name].name in bpy.data.materials:
        return _MATS[name]
    c, metal, rough = COL[name]
    m = bpy.data.materials.new("MAT_" + name)
    if not m.use_nodes:
        m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (c[0], c[1], c[2], 1.0)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    m.diffuse_color = (c[0], c[1], c[2], 1.0)
    _MATS[name] = m
    return m


# ----------------------------------------------------------------------------------------------------------------------
# geometry helpers
def catmull(pts, sub=4, closed=False):
    pts = np.asarray(pts, dtype=float)
    n = len(pts)
    out = []
    for i in range(n - 1 if not closed else n):
        p0 = pts[(i - 1) % n] if (closed or i > 0) else pts[0] * 2 - pts[1]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if (closed or i + 2 < n) else pts[-1] * 2 - pts[-2]
        for k in range(sub):
            t = k / sub
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    if not closed:
        out.append(pts[-1])
    return np.array(out)


def resample(path, step):
    path = np.asarray(path, dtype=float)
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    n = max(2, int(s[-1] / step) + 1)
    u = np.linspace(0, s[-1], n)
    return np.stack([np.interp(u, s, path[:, i]) for i in range(3)], axis=1)


def tube_grid(path, rx, ry=None, sides=12, ref=None, wobble=None, phase0=0.0):
    """Ring grid around a path.  rx / ry: scalar or per-point.  ref: keeps the ellipse axis N close to ref
    (otherwise parallel transport).  wobble(k, phi) -> radius multiplier (N, sides)."""
    path = np.asarray(path, dtype=float)
    N = len(path)
    rx = np.broadcast_to(np.asarray(rx, dtype=float), (N,)).copy()
    ry = rx.copy() if ry is None else np.broadcast_to(np.asarray(ry, dtype=float), (N,)).copy()
    T = np.gradient(path, axis=0)
    T = norm(T)
    Nn = np.zeros_like(T)
    if ref is not None:
        refa = np.asarray(ref, dtype=float)
        for k in range(N):
            r = refa if refa.ndim == 1 else refa[k]
            v = r - np.dot(r, T[k]) * T[k]
            Nn[k] = v / max(np.linalg.norm(v), 1e-9)
    else:
        a = np.array([1.0, 0, 0]) if abs(T[0][0]) < 0.9 else np.array([0, 1.0, 0])
        v = a - np.dot(a, T[0]) * T[0]
        Nn[0] = v / np.linalg.norm(v)
        for k in range(1, N):
            v = Nn[k - 1] - np.dot(Nn[k - 1], T[k]) * T[k]
            Nn[k] = v / max(np.linalg.norm(v), 1e-9)
    B = np.cross(T, Nn)
    phi = phase0 + np.linspace(0, 2 * math.pi, sides, endpoint=False)
    c, s = np.cos(phi), np.sin(phi)
    mul = np.ones((N, sides)) if wobble is None else wobble(np.arange(N), phi)
    P = (path[:, None, :] + (rx[:, None, None] * mul[..., None]) * c[None, :, None] * Nn[:, None, :]
         + (ry[:, None, None] * mul[..., None]) * s[None, :, None] * B[:, None, :])
    return P


def add_tube(mb, path, rx, ry=None, sides=12, ref=None, wobble=None, mat_i=0, cap0=True, cap1=True, phase0=0.0, skip=None):
    P = tube_grid(path, rx, ry, sides, ref, wobble, phase0)
    base = mb.add_grid(P, wrap_c=True, mat=mat_i, skip=skip)
    N = len(path)
    if cap0:
        c = mb.add_verts(np.asarray(path)[0])
        ring0 = base + np.arange(sides)
        mb.add_tris([[c, ring0[(i + 1) % sides], ring0[i]] for i in range(sides)], mat_i)
    if cap1:
        c = mb.add_verts(np.asarray(path)[-1])
        ringN = base + (N - 1) * sides + np.arange(sides)
        mb.add_tris([[c, ringN[i], ringN[(i + 1) % sides]] for i in range(sides)], mat_i)


def xf(P, M):
    """transform an (..., 3) numpy array by a mathutils Matrix"""
    A = np.array(M)[:3, :3]
    t = np.array(M)[:3, 3]
    return np.asarray(P) @ A.T + t


def add_dome(mb, centre, normal, radius, height=None, sides=8, rings=3, mat_i=0):
    """small rivet: half ellipsoid on a surface"""
    n = norm(np.asarray(normal, dtype=float))
    a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
    u = norm(np.cross(n, a))
    v = np.cross(n, u)
    h = radius * 0.8 if height is None else height
    phi = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    G = []
    for k in range(rings + 1):
        t = k / rings * (math.pi / 2)
        r = radius * math.cos(t)
        z = h * math.sin(t)
        if k == rings:
            r = 1e-4
        G.append(np.asarray(centre) + n * z + r * (np.cos(phi)[:, None] * u + np.sin(phi)[:, None] * v))
    mb.add_grid(np.array(G), wrap_c=True, mat=mat_i)


def link_template(length=3.4, width=2.3, wire=0.42, nu=14, nv=6):
    """elongated torus link, long axis along +X, plane XY (flat in Z)"""
    u = np.linspace(0, 2 * math.pi, nu, endpoint=False)
    v = np.linspace(0, 2 * math.pi, nv, endpoint=False)
    a, b = length / 2 - wire, width / 2 - wire
    G = np.zeros((nu, nv, 3))
    for i, ui in enumerate(u):
        # stadium-ish ellipse centre line
        cx, cy = a * math.cos(ui), b * math.sin(ui)
        tx, ty = -a * math.sin(ui), b * math.cos(ui)
        tl = math.hypot(tx, ty)
        nx, ny = ty / tl, -tx / tl          # outward in plane
        for j, vj in enumerate(v):
            G[i, j] = (cx + wire * math.cos(vj) * nx, cy + wire * math.cos(vj) * ny, wire * math.sin(vj))
    return G


def add_chain(mb, path, link_len=3.4, link_w=2.3, wire=0.42, gap_last=False, mat_i=0, ref=None, twist0=0.0):
    """chain along a polyline: links alternate 90 degrees about the tangent"""
    path = resample(path, 0.05)
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    pitch = link_len * 0.74
    nL = int(s[-1] / pitch)
    tmpl = link_template(link_len, link_w, wire)
    for i in range(nL):
        d = i * pitch + link_len / 2
        p = np.array([np.interp(d, s, path[:, k]) for k in range(3)])
        p2 = np.array([np.interp(d + 0.4, s, path[:, k]) for k in range(3)])
        p1 = np.array([np.interp(max(d - 0.4, 0), s, path[:, k]) for k in range(3)])
        t = norm(p2 - p1)
        a = np.array([1.0, 0, 0]) if ref is None else np.asarray(ref, dtype=float)
        if abs(np.dot(a, t)) > 0.95:
            a = np.array([0, 1.0, 0])
        n = norm(a - np.dot(a, t) * t)
        b = np.cross(t, n)
        ang = twist0 + (math.pi / 2) * (i % 2)
        n2 = n * math.cos(ang) + b * math.sin(ang)
        b2 = np.cross(t, n2)
        Rm = np.stack([t, n2, b2], axis=1)           # columns: long axis, in-plane, out-of-plane
        P = tmpl @ Rm.T + p
        skip = None
        if gap_last and i == nL - 1:
            skip = np.zeros((14, 6), dtype=bool)
            skip[0:3, :] = True
        mb.add_grid(P, wrap_c=True, wrap_r=True, mat=mat_i, skip=skip)


def hang_curve(p0, p1, sag, n=24):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1 = np.asarray(p0, dtype=float), np.asarray(p1, dtype=float)
    P = p0 + (p1 - p0) * t
    P[:, 2] -= sag * 4 * t[:, 0] * (1 - t[:, 0])
    return P


# ----------------------------------------------------------------------------------------------------------------------
class RingLoft:
    """Irregular lofted surface around the posed spine path.  P(h, theta): theta 0 = +X, 90 = +Y (back), 270 = front (-Y).
    h is the REST height of the ring (the pose bends the spine, so rings above the pelvis follow it)."""

    def __init__(self, pose, prof, seed, fold_amp=(0.012, 0.12), fold_h=(190.0, 10.0), nfold=10, shift=None, post=None,
                 pleat=0.0, pleat_h=(128.0, 0.0), sigma=3.0):
        self.pose = pose
        prof = np.asarray(prof, dtype=float)
        hh = np.arange(prof[0, 0], prof[-1, 0] + 0.01, 0.5)
        self.hh = hh
        self.rx = smooth1(np.interp(hh, prof[:, 0], prof[:, 1]), sigma * 2)
        self.ry = smooth1(np.interp(hh, prof[:, 0], prof[:, 2]), sigma * 2)
        rng = random.Random(seed)
        self.n = np.array([rng.choice([3, 4, 5, 6, 7, 8, 9, 11, 13, 16, 19]) for _ in range(nfold)], dtype=float)
        self.a = np.array([rng.uniform(0.35, 1.0) for _ in range(nfold)]) / np.sqrt(self.n)
        self.ph = np.array([rng.uniform(0, 2 * math.pi) for _ in range(nfold)])
        self.dr = np.array([rng.uniform(-0.8, 0.8) for _ in range(nfold)])
        self.a /= self.a.sum()
        self.fold_amp = fold_amp
        self.fold_h = fold_h
        self.shift = shift
        self.post = post
        self.pleat = pleat
        self.pleat_h = pleat_h
        self.m = rng.choice([7, 9, 11])
        self.mph = rng.uniform(0, 6.28)
        self.mdr = rng.uniform(-0.5, 0.5)
        self.hand = []     # hand-placed folds (theta0 deg, width deg at top, width deg at bottom, depth, h_top, h_bot)

    def fold(self, H, TH):
        t = np.clip((self.fold_h[0] - H) / (self.fold_h[0] - self.fold_h[1]), 0, 1)
        t = t * t * (3 - 2 * t)
        amp = self.fold_amp[0] + (self.fold_amp[1] - self.fold_amp[0]) * t
        f = np.zeros_like(H, dtype=float)
        for n, a, ph, dr in zip(self.n, self.a, self.ph, self.dr):
            f = f + a * np.sin(n * TH + ph + dr * H / 10.0)
        f = f * amp * 2.0
        if self.pleat:
            pt = np.clip((self.pleat_h[0] - H) / max(self.pleat_h[0] - self.pleat_h[1], 1e-3), 0, 1)
            pl = 1.0 - 2.0 * np.abs(np.sin(self.m * TH / 2 + self.mph + self.mdr * H / 10)) ** 0.8
            f = f + self.pleat * pt * pl
        for (th0, w_top, w_bot, depth, h_top, h_bot) in self.hand:
            u = np.clip((h_top - H) / max(h_top - h_bot, 1e-3), 0, 1)
            w = np.radians(w_top + (w_bot - w_top) * u)
            d = (TH - math.radians(th0) + math.pi) % (2 * math.pi) - math.pi
            env = np.clip((h_top + 6 - H) / 10, 0, 1) * np.clip((H - (h_bot - 6)) / 10, 0, 1)
            f = f + depth * env * np.exp(-(d / w) ** 2) * (0.35 + 0.65 * u)
        return f

    def pts(self, H, TH, off=0.0, folds=True, post=True, rscale=1.0):
        H = np.asarray(H, dtype=float)
        TH = np.asarray(TH, dtype=float)
        Hc = np.clip(H, self.hh[0], self.hh[-1])
        rx = np.interp(Hc, self.hh, self.rx) * rscale
        ry = np.interp(Hc, self.hh, self.ry) * rscale
        if folds:
            m = 1.0 + self.fold(H, TH)
            rx = rx * m
            ry = ry * m
        rx = rx + off
        ry = ry + off
        y, z, t = self.pose.eval(H)
        sh = 0.0 if self.shift is None else self.shift(H)
        ct, st = np.cos(np.radians(t)), np.sin(np.radians(t))
        lat = rx * np.cos(TH)
        yy = ry * np.sin(TH) + sh
        P = np.stack([lat, y + yy * ct, z + yy * st], axis=-1)
        if self.post is not None and post:
            P = self.post(P, H, TH)
        return P

    def centre(self, H):
        y, z, t = self.pose.eval(H)
        sh = 0.0 if self.shift is None else self.shift(np.asarray(H, dtype=float))
        ct, st = np.cos(np.radians(t)), np.sin(np.radians(t))
        return np.stack([np.zeros_like(y), y + sh * ct, z + sh * st], axis=-1)


# ----------------------------------------------------------------------------------------------------------------------
def make_robe(pose, seed=1201):
    prof = [
        # h    rx    ry
        (0, 50.0, 42.0), (20, 43.0, 37.0), (45, 36.0, 31.0), (75, 29.0, 25.0), (105, 24.5, 20.0), (128, 20.0, 14.5),
        (145, 19.5, 13.5), (165, 21.0, 15.0), (185, 24.0, 16.5), (200, 26.0, 17.0), (208, 31.0, 17.5),
        (214, 33.0, 16.5), (219, 28.0, 14.0), (223, 16.0, 11.0), (226, 9.5, 9.5), (228.5, 8.0, 8.0),
    ]

    def shift(H):
        hump = 4.0 * np.exp(-((H - 205.0) / 24.0) ** 2)
        sk = -5.0 * np.clip((128.0 - H) / 128.0, 0, 1)
        return hump + sk

    def post(P, H, TH):
        # dragging tail behind (+Y) and a wide pooled hem
        P = P.copy()
        w = np.exp(-(((TH - math.radians(88)) + math.pi) % (2 * math.pi) - math.pi) ** 2 / (2 * math.radians(30) ** 2))
        k = np.clip(1.0 - H / 80.0, 0, 1) ** 1.6
        P[..., 1] += 34.0 * w * k
        P[..., 0] += 6.0 * w * k * np.sin(H / 7.0)
        # hem pooling: slight outward flare in the last few cm
        pool = np.clip(1.0 - H / 14.0, 0, 1) ** 2
        c = P[..., 0:2].copy()
        P[..., 0] = c[..., 0] * (1 + 0.05 * pool)
        return P

    L = RingLoft(pose, prof, seed, shift=shift, post=post, pleat=0.045)
    L.hand = [
        (252, 6, 12, -0.15, 125, 0), (302, 7, 13, -0.11, 120, 0), (205, 6, 10, -0.09, 110, 0),
        (140, 8, 14, 0.07, 100, 0), (335, 5, 9, 0.06, 130, 5), (95, 10, 16, 0.08, 90, 0),
    ]
    return L


def hem_raise(th, seed=77, ntongue=9):
    """height by which the hem is lifted per column (torn, tongue shaped).  th in radians"""
    rng = random.Random(seed)
    cuts = sorted(rng.uniform(0, 2 * math.pi) for _ in range(ntongue))
    # keep tongues from being too narrow
    cuts = [c for i, c in enumerate(cuts)]
    cuts.append(cuts[0] + 2 * math.pi)
    depth = [rng.uniform(10, 34) for _ in range(ntongue)]
    out = np.zeros_like(th, dtype=float)
    t = np.mod(th - cuts[0], 2 * math.pi)
    for i in range(ntongue):
        a, b = cuts[i] - cuts[0], cuts[i + 1] - cuts[0]
        m = (t >= a) & (t < b)
        u = (t[m] - a) / max(b - a, 1e-6)
        skew = 0.35 + 0.3 * rng.random()
        v = np.where(u < skew, u / skew, (1 - u) / (1 - skew))     # 0 at the notches... 1 at the apex
        out[m] = depth[i] * (1 - v) ** 1.25 + 1.2 * v
    back = np.exp(-(((th - math.radians(90)) + math.pi) % (2 * math.pi) - math.pi) ** 2 / (2 * math.radians(42) ** 2))
    out = out * (1 - 0.9 * back)
    for c in (253, 287):                                  # lift the hem over the feet so the toes show
        d = ((th - math.radians(c)) + math.pi) % (2 * math.pi) - math.pi
        out = np.maximum(out, 17 * np.exp(-(d / math.radians(11)) ** 2))
    return out


def build_robe(mb, robe, ncol=176, nring=112, hole_seed=5):
    th = np.linspace(0, 2 * math.pi, ncol, endpoint=False)
    hb = hem_raise(th)
    s = np.linspace(0, 1, nring) ** 1.0
    htop = 228.0
    H = hb[None, :] + (htop - hb[None, :]) * s[:, None]
    TH = np.broadcast_to(th[None, :], H.shape)
    P = robe.pts(H, TH)
    P[..., 2] = np.maximum(P[..., 2], 0.0)
    rng = random.Random(hole_seed)
    skip = np.zeros((nring - 1, ncol), dtype=bool)
    for _ in range(4):                                    # small torn holes in the lower skirt
        r0 = rng.randint(4, int(nring * 0.38))
        c0 = rng.randint(0, ncol - 1)
        if abs(((c0 / ncol) * 360 - 90 + 180) % 360 - 180) < 30:
            continue
        for dr in range(rng.randint(2, 3)):
            for dc in range(rng.randint(2, 4)):
                skip[(r0 + dr) % (nring - 1), (c0 + dc) % ncol] = True
    mb.add_grid(P, wrap_c=True, mat=0, skip=skip)
    return P


# ----------------------------------------------------------------------------------------------------------------------
def fold_wobble(seed, amp, n_axial=(2, 3, 5, 7)):
    rng = random.Random(seed)
    ph = [rng.uniform(0, 6.28) for _ in n_axial]
    dr = [rng.uniform(-0.2, 0.2) for _ in n_axial]

    def f(k, phi):
        out = np.ones((len(k), len(phi)))
        for n, p, d in zip(n_axial, ph, dr):
            out += amp * np.sin(n * phi[None, :] + p + d * k[:, None]) / len(n_axial)
        return out
    return f


def build_arms_and_sleeves(pose, parts, curl=15.0):
    """returns dict of arm info; adds sleeves (robe material) and skin forearms/hands"""
    mb_s = MB()          # sleeves
    mb_k = MB()          # skin
    info = {}
    for side in ("l", "r"):
        A = pose.arm(side)
        s = A["side"]
        sh, el, wr = A["shoulder"], A["elbow"], A["wrist"]
        d1, d2, d3 = A["d"]
        info[side] = A
        # sleeve: from inside the shoulder, along the upper arm, to mid forearm, ragged cuff
        mid = el + d2 * 31.0
        p = [sh - d1 * 7.0, sh, sh + d1 * 20, el, el + d2 * 14.0, mid, mid + d2 * 12.0]
        path = resample(catmull(p, 5), 1.1)
        n = len(path)
        sleeve_len = np.linalg.norm(np.diff(path, axis=0), axis=1).sum()
        u = np.linspace(0, 1, n)
        rad = np.interp(u, [0, 0.12, 0.45, 0.62, 0.8, 0.93, 1.0], [5.6, 6.4, 5.8, 6.0, 6.4, 7.4, 8.2])
        sides = 28
        rngs = random.Random(31 if side == "l" else 32)
        # torn cuff: each column ends at its own row
        rc = np.array([n - 1 - int(round(rngs.uniform(0, 1) ** 1.3 * 9)) for _ in range(sides)])
        skip = np.zeros((n - 1, sides), dtype=bool)
        for c in range(sides):
            lim = min(rc[c], rc[(c + 1) % sides])
            skip[lim:, c] = True
        wob_a = fold_wobble(40 + (side == "r"), 0.20)

        def wob(k, phi, wob_a=wob_a, u=u):
            return wob_a(k, phi) * (0.7 + 0.5 * u[k][:, None])
        ref = np.array([0.0, -1.0, 0.0])
        P = tube_grid(path, rad, rad * 0.92, sides=sides, ref=ref, wobble=wob)
        mb_s.add_grid(P, wrap_c=True, mat=0, skip=skip)
        # forearm skin: elbow-ish to wrist, thin
        fp = np.array([el + d2 * 20.0, el + d2 * 40.0, wr])
        fpath = resample(catmull(fp, 6), 1.0)
        add_tube(mb_k, fpath, np.interp(np.linspace(0, 1, len(fpath)), [0, 0.4, 0.8, 1], [2.9, 2.55, 2.0, 1.85]),
                 np.interp(np.linspace(0, 1, len(fpath)), [0, 0.4, 0.8, 1], [2.6, 2.3, 1.7, 1.55]), sides=10,
                 ref=np.array([0, -1.0, 0]), cap0=False, cap1=False)
        build_hand(mb_k, A, curl)
    return mb_s, mb_k, info


def build_hand(mb, A, curl):
    s = A["side"]
    a = A["d"][2].copy()
    wr = A["wrist"]
    lat0 = np.array([0.0, -1.0, 0.0])
    lat = norm(lat0 - np.dot(lat0, a) * a)
    pnorm = -s * np.cross(lat, a)                # palm normal points to the body
    pnorm = norm(pnorm)
    # palm
    pp = np.array([wr - a * 1.0, wr + a * 4.5, wr + a * 8.6])
    ppath = resample(catmull(pp, 5), 0.7)
    uu = np.linspace(0, 1, len(ppath))
    wd = np.interp(uu, [0, 0.5, 1], [2.1, 3.0, 4.0])
    th = np.interp(uu, [0, 0.5, 1], [1.45, 1.35, 1.45])
    add_tube(mb, ppath, wd, th, sides=10, ref=lat, cap0=False, cap1=True)
    flen = {"index": 0.95, "middle": 1.0, "ring": 0.93, "pinky": 0.78}
    lat_off = {"index": -2.85, "middle": -0.95, "ring": 0.95, "pinky": 2.75}
    base_d = {"index": 8.4, "middle": 8.9, "ring": 8.4, "pinky": 7.4}
    seg = [8.0, 7.0, 6.0]
    for fi, name in enumerate(("index", "middle", "ring", "pinky")):
        k0 = wr + a * base_d[name] + lat * lat_off[name]
        dirn = norm(a + lat * 0.05 * (fi - 1.5))
        pf = [k0]
        p_cur = k0
        pn = pnorm.copy()
        d_cur = dirn
        for j in range(3):
            phi = math.radians(curl + (4 if name in ("pinky",) else 0) + (j * 2) + (fi - 1.5) * 1.5)
            d_cur, pn = norm(d_cur * math.cos(phi) + pn * math.sin(phi)), norm(pn * math.cos(phi) - d_cur * math.sin(phi))
            p_cur = p_cur + d_cur * seg[j] * flen[name]
            pf.append(p_cur)
        path = resample(catmull(np.array(pf), 4), 0.6)
        uu = np.linspace(0, 1, len(path))
        rr = np.interp(uu, [0, 0.33, 0.66, 1.0], [0.9, 0.78, 0.62, 0.42])
        add_tube(mb, path, rr, rr * 0.9, sides=8, ref=lat, cap0=False, cap1=True)
    # thumb
    t0 = wr + a * 2.6 + lat * -2.3 + pnorm * 0.1
    d_cur = norm(a * math.cos(math.radians(28)) + lat * -math.sin(math.radians(28)))
    pn = pnorm.copy()
    pf = [t0]
    p_cur = t0
    for L in (4.6, 4.4, 3.6):
        phi = math.radians(curl)
        d_cur, pn = norm(d_cur * math.cos(phi) + pn * math.sin(phi)), norm(pn * math.cos(phi) - d_cur * math.sin(phi))
        p_cur = p_cur + d_cur * L
        pf.append(p_cur)
    path = resample(catmull(np.array(pf), 4), 0.6)
    uu = np.linspace(0, 1, len(path))
    rr = np.interp(uu, [0, 0.5, 1.0], [1.15, 0.82, 0.5])
    add_tube(mb, path, rr, rr * 0.9, sides=8, ref=lat, cap0=False, cap1=True)


def build_feet(mb):
    for s in (1.0, -1.0):
        ankle = np.array([15.0 * s, 3.0, 13.0])
        ball = np.array([15.0 * s, -13.0, 2.6])
        path = resample(catmull([ankle + (0, 1.5, 6), ankle, (15.0 * s, -4.0, 8.0), ball], 5), 0.8)
        uu = np.linspace(0, 1, len(path))
        add_tube(mb, path, np.interp(uu, [0, 0.4, 1], [3.1, 2.8, 2.6]), np.interp(uu, [0, 0.4, 1], [3.0, 2.0, 1.2]), sides=10,
                 ref=np.array([1.0, 0, 0]), cap0=False, cap1=True)
        offs = [-3.7, -1.9, 0.0, 1.8, 3.4]
        lens = [10.5, 9.0, 8.5, 7.5, 6.0]
        for o, ln in zip(offs, lens):
            ox = 15.0 * s + o * s
            p0 = np.array([ox, -12.5, 1.5])
            p1 = np.array([ox + 0.35 * s * o / 4, -12.5 - ln * 0.55, 1.35])
            p2 = np.array([ox + 0.5 * s * o / 4, -12.5 - ln, 1.05])
            path = resample(catmull([p0, p1, p2], 5), 0.6)
            uu = np.linspace(0, 1, len(path))
            add_tube(mb, path, np.interp(uu, [0, 1], [1.05, 0.65]), np.interp(uu, [0, 1], [0.85, 0.5]), sides=7, cap0=False,
                     cap1=True, ref=np.array([0, 0, 1.0]))


def build_neck(mb, pose):
    H = np.linspace(214.0, 258.0, 30)
    y, z, t = pose.eval(H)
    path = np.stack([np.zeros_like(y), y, z], axis=1)
    add_tube(mb, path, 4.3, 4.1, sides=12, cap0=False, cap1=False)


# ----------------------------------------------------------------------------------------------------------------------
def rope_belt(mb, robe, pose, h0=131.0, seed=5, tail=True, off=1.4):
    rng = random.Random(seed)
    nsamp = 360
    t = np.linspace(0, 1, nsamp, endpoint=False)
    TH = 2 * math.pi * t
    wob = 1.5 * np.sin(TH * 3 + 0.4) + 1.0 * np.sin(TH * 5 + 2.0)
    H = h0 + wob + 0 * TH
    base = robe.pts(H, TH, off=off)
    cen = robe.centre(H)
    radial = norm(base - cen - np.array([0, 0, 0]))
    ctr = np.cross(radial, np.array([0, 0, 1.0]))
    up = norm(np.cross(ctr, radial))
    for j in range(3):
        phi = 2 * math.pi * 44 * t + 2 * math.pi * j / 3
        P = base + 0.8 * (np.cos(phi)[:, None] * radial + np.sin(phi)[:, None] * up)
        g = tube_grid(P, 0.78, 0.78, sides=7, ref=radial)
        mb.add_grid(g, wrap_r=True, wrap_c=True, mat=0)
    if tail:
        # rope end hanging down the front-left, 3 strands fraying
        th0 = math.radians(300)
        hs = np.linspace(h0, 66.0, 40)
        sway = 0.02 * np.sin(hs / 9.0)
        TH2 = th0 + sway + 0.0 * hs
        Pb = robe.pts(hs, TH2, off=off + 0.9)
        rad = norm(Pb - robe.centre(hs))
        upv = np.array([0, 0, 1.0])
        for j in range(3):
            phi = (hs * 0.9) + 2 * math.pi * j / 3
            spread = np.clip((90.0 - hs) / 25.0, 0, 1)[:, None] * (j - 1) * 1.1
            P = Pb + 0.7 * (np.cos(phi)[:, None] * rad + np.sin(phi)[:, None] * np.cross(rad, upv)) + spread * np.cross(rad, upv)
            g = tube_grid(P, np.interp(hs, [66, 75, 130], [0.45, 0.6, 0.78]), sides=7, ref=rad)
            mb.add_grid(g, wrap_c=True, mat=0)


# ----------------------------------------------------------------------------------------------------------------------
# face surface used by concept A's mask: local coords x (lateral), z (up), depth along -Y
def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def gauss2(x, z, cx, cz, sx, sz, rot=0.0):
    dx, dz = x - cx, z - cz
    if rot:
        c, s = math.cos(rot), math.sin(rot)
        dx, dz = c * dx + s * dz, -s * dx + c * dz
    return np.exp(-0.5 * ((dx / sx) ** 2 + (dz / sz) ** 2))


def seg_dist(x, z, poly):
    """distance from points to a polyline, plus signed side"""
    best = np.full(x.shape, 1e9)
    side = np.zeros(x.shape)
    for (x0, z0), (x1, z1) in zip(poly[:-1], poly[1:]):
        vx, vz = x1 - x0, z1 - z0
        L2 = vx * vx + vz * vz
        t = np.clip(((x - x0) * vx + (z - z0) * vz) / L2, 0, 1)
        px, pz = x0 + t * vx, z0 + t * vz
        d = np.hypot(x - px, z - pz)
        sg = np.sign((x - x0) * vz - (z - z0) * vx)
        upd = d < best
        best = np.where(upd, d, best)
        side = np.where(upd, sg, side)
    return best, side


# ----------------------------------------------------------------------------------------------------------------------
# CONCEPT A: THE PENITENT
A_ZC = 16.0           # mask centre, head-local z
A_Y0 = -3.6           # mask rim plane, head-local y


def mask_a_surface(nu=104, nv=160):
    H = 38.0
    z0 = A_ZC - H / 2
    zc = A_ZC
    v = np.linspace(0, 1, nv)
    zz = z0 + H * v
    t = (zz - zc) / (H / 2)
    Wt = np.interp(t, [-1, -0.85, -0.6, -0.3, 0, 0.3, 0.6, 0.85, 1.0], [0.0, 2.4, 4.8, 8.0, 10.2, 10.8, 10.0, 6.6, 0.0])
    Wt = smooth1(Wt, 3.0)
    Wt[0] = 0.0
    Wt[-1] = 0.0
    u = np.linspace(-1, 1, nu)
    X = u[None, :] * Wt[:, None]
    Z = np.broadcast_to(zz[:, None], X.shape)
    D = 5.6 * np.clip(1 - t ** 2, 0, 1) ** 0.45
    uu = np.broadcast_to(u[None, :], X.shape)
    F = D[:, None] * np.clip(1 - uu ** 2, 0, 1) ** 0.75             # forward depth of the plate (positive = towards -Y)
    # features (positive = forward)
    brow = 1.5 * np.exp(-(((Z - (zc + 8.8)) / 1.7) ** 2)) * np.clip(1 - (np.abs(X) / 10.6) ** 2, 0, 1)
    sock = -2.1 * (gauss2(np.abs(X), Z, 4.5, zc + 6.1, 2.8, 1.7))
    # nose
    zn = Z - zc
    hn = np.where(zn > -5.4, 3.0 * smoothstep(8.5, 0.5, zn), 0.0)
    hn = hn + 1.0 * np.exp(-(((zn + 3.2) / 1.5) ** 2))
    hn = hn * smoothstep(-5.6, -3.0, zn)
    sgm = np.interp(zn, [-6, -3, 0, 6, 9], [1.9, 1.7, 1.2, 0.95, 1.1])
    nose = hn * np.exp(-0.5 * (X / sgm) ** 2)
    hollow = -1.7 * gauss2(np.abs(X), Z, 6.5, zc - 5.0, 2.5, 3.4)
    bone = 1.0 * gauss2(np.abs(X), Z, 7.0, zc + 0.6, 2.2, 1.7)
    chin = 1.2 * gauss2(X, Z, 0.0, z0 + 4.2, 2.6, 2.4)
    temple = -0.9 * gauss2(np.abs(X), Z, 9.0, zc + 7.5, 2.0, 3.0)
    Fh = F + brow + sock + nose + hollow + bone + chin + temple
    # crack
    poly = [(-7.0, 34.2), (-5.2, 30.2), (-4.6, 27.4), (-2.6, 23.6), (-1.5, 20.4), (0.4, 17.4), (1.6, 13.0), (2.5, 9.6), (3.9, 6.5), (3.3, 2.9), (4.3, -0.4)]
    d, sd = seg_dist(X, Z, poly)
    wk = 0.30 + 0.18 * np.sin(Z * 1.7) ** 2
    crack_core = d < wk
    Fh = Fh - 0.65 * np.exp(-(d / 0.55) ** 2) + 0.38 * sd * smoothstep(-0.5, 0.5, d * sd) * smoothstep(5.0, 1.5, d)
    # slits (dark)
    slit = np.zeros(X.shape, dtype=bool)
    for sx in (1.0, -1.0):
        cx, cz = 4.5 * sx, zc + 6.1
        rot = math.radians(14.0) * sx
        dx, dz = X - cx, Z - cz
        c, s_ = math.cos(rot), math.sin(rot)
        px, pz = c * dx + s_ * dz, -s_ * dx + c * dz
        slit |= ((px / 3.2) ** 2 + (pz / 0.62) ** 2) < 1.0
    Fh = Fh - 1.2 * slit
    Fh = Fh - 0.95 * np.clip(Z - (zc + 9.5), 0, None)
    Y = A_Y0 - Fh
    dark = crack_core | slit
    cell_dark = dark[:-1, :-1] | dark[1:, :-1] | dark[:-1, 1:] | dark[1:, 1:]
    P = np.stack([X, Y, Z], axis=-1)
    return P, cell_dark.astype(int)


def band_ring(a, b, ycen, zc_, n=96):
    phi = np.linspace(0, 2 * math.pi, n, endpoint=False)
    P = np.stack([a * np.cos(phi), ycen + b * np.sin(phi), np.full(n, zc_)], axis=1)
    R = np.stack([np.cos(phi), np.sin(phi) * (b / a), np.zeros(n)], axis=1)
    return P, norm(R)


def add_top_cap(mb, base, shape, wrap):
    """close the pointed top of a lofted grid with a triangle fan"""
    R, C = shape[0], shape[1]
    ring = base + (R - 1) * C + np.arange(C)
    top = mb.V[-1].reshape(R, C, 3)[R - 1] if len(mb.V[-1]) == R * C else None
    ctr = mb.add_verts(np.mean(top, axis=0))
    n = C if wrap else C - 1
    mb.add_tris([[ctr, ring[(i + 1) % C], ring[i]] for i in range(n)], 0)


def build_cowl(pose, robe):
    prof = [(206, 35.0, 18.0), (212, 34.0, 18.0), (218, 30.0, 17.5), (224, 21.0, 15.5), (232, 15.2, 14.0), (247, 13.6, 13.9),
            (256, 13.8, 15.0), (268, 14.0, 14.8), (278, 13.2, 12.8), (285, 9.4, 9.4), (289.5, 4.2, 5.2), (292.5, 1.6, 2.0), (294.0, 0.04, 0.05)]

    def shift(H):
        hump = 4.0 * np.exp(-((H - 205.0) / 24.0) ** 2)
        droop = 6.0 * np.clip((H - 268.0) / 26.0, 0, 1) ** 2
        return hump + droop

    L = RingLoft(pose, prof, 2203, fold_amp=(0.03, 0.05), fold_h=(300.0, 206.0), shift=shift, nfold=8)
    L.hand = [(300, 10, 10, -0.05, 232, 214), (240, 12, 12, -0.05, 232, 214)]
    nring, ncol = 150, 130
    hs = np.concatenate([np.linspace(206, 246, 40, endpoint=False), np.linspace(246, 294.0, nring - 40)])
    phi0 = 52.0
    hc, hh_ = 267.5, 17.0
    phi = phi0 * np.sqrt(np.clip(1 - ((hs - hc) / hh_) ** 2, 0, 1))
    u = np.linspace(0, 1, ncol)
    TH = np.radians(270 + phi)[:, None] + np.radians(360 - 2 * phi)[:, None] * u[None, :]
    H = np.broadcast_to(hs[:, None], TH.shape)
    P = L.pts(H, TH)
    # flare the opening edges forward, like a deep hood tunnel
    y, z, t = pose.eval(H)
    ct, st = np.cos(np.radians(t)), np.sin(np.radians(t))
    edge = np.minimum(u, 1 - u)[None, :]
    flare = 3.4 * np.clip(1 - edge / 0.16, 0, 1) ** 2 * np.clip(phi / phi0, 0, 1)[:, None] ** 0.6
    P[..., 1] += -flare * ct
    P[..., 2] += -flare * st
    P[..., 0] += flare * 0.7 * np.sign(np.cos(TH))
    return P, L


def build_shackles(info):
    mb = MB()
    for side in ("l", "r"):
        A = info[side]
        s = A["side"]
        wr, d2 = A["wrist"], A["d"][1]
        yref = np.array([0, -1.0, 0])
        add_tube(mb, resample(np.array([wr - d2 * 3.6, wr + d2 * 0.4]), 0.6), 3.25, 3.25, sides=18, ref=yref, cap0=False, cap1=False)
        add_tube(mb, resample(np.array([wr - d2 * 3.9, wr - d2 * 3.3]), 0.3), 3.75, 3.75, sides=18, ref=yref)
        add_tube(mb, resample(np.array([wr + d2 * 0.4, wr + d2 * 1.0]), 0.3), 3.75, 3.75, sides=18, ref=yref)
        # eyelet on the outer-back of the cuff, then the chain
        eye = wr - d2 * 1.6 + np.array([s * 3.9, 1.8, 0])
        tmpl = link_template(3.6, 2.6, 0.5, 16, 6)
        ax = np.array([s * 0.6, 0.8, 0]) / np.linalg.norm([0.6, 0.8])
        Rm = np.stack([ax, np.array([0, 0, 1.0]), np.cross(ax, np.array([0, 0, 1.0]))], axis=1)
        mb.add_grid(tmpl @ Rm.T + eye, wrap_c=True, wrap_r=True, mat=0)
        tt = np.linspace(0, 1, 40)
        chain_path = np.stack([eye[0] + s * (1.5 + 4.0 * tt ** 0.8), eye[1] + 2.0 + 9.0 * tt + 2.0 * np.sin(tt * 5.0), eye[2] - 2.0 - 87.0 * tt], axis=1)
        add_chain(mb, chain_path, 3.5, 2.4, 0.44, gap_last=True, ref=np.array([1.0, 0, 0]))
    return mb


def build_a(pose, robe, info, objs):
    Mh = pose.head_matrix() @ Matrix.Translation((0, 0, HEAD_DZ["a"]))
    rep = {}
    # --- mask
    P, cd = mask_a_surface()
    mb = MB()
    mb.add_grid(xf(P, Mh), mat=cd)
    objs["mask"] = mb.to_object("A_mask", [mat("bone"), mat("dark")], solid=0.75)
    rep["mask_centre_local"] = [0.0, A_Y0 - 3.4, A_ZC + HEAD_DZ["a"]]
    # --- iron band + rivets (iron)
    mi = MB()
    a_, b_, yc = 10.5, 9.5, 0.8
    zb = A_ZC + 10.4
    Pb, Rb = band_ring(a_, b_, yc, zb)
    pathb = xf(Pb, Mh)
    refb = Rb @ np.array(Mh)[:3, :3].T
    g = tube_grid(pathb, 0.4, 1.7, sides=8, ref=refb)
    mi.add_grid(g, wrap_r=True, wrap_c=True, mat=0)
    for deg in (-62, -31, 0, 31, 62, 100, 138, -100, -138):
        ph = math.radians(270 + deg)
        pt = np.array([a_ * math.cos(ph), yc + b_ * math.sin(ph), zb])
        nl = norm(np.array([math.cos(ph), math.sin(ph) * (b_ / a_), 0.0]))
        add_dome(mi, xf(pt + nl * 0.35, Mh), np.array(Mh)[:3, :3] @ nl, 0.62, 0.55, sides=8, rings=3)
    objs["band"] = mi.to_object("A_band", [mat("iron")])
    # --- cowl
    Pc, L = build_cowl(pose, robe)
    mc = MB()
    base = mc.add_grid(Pc, mat=0)
    add_top_cap(mc, base, Pc.shape, False)
    objs["cowl"] = mc.to_object("A_cowl", [mat("robe")], solid=0.7)
    # --- rope belt
    mr = MB()
    rope_belt(mr, robe, pose)
    objs["rope"] = mr.to_object("A_rope", [mat("rope")])
    # --- shackles + chains
    objs["shackles"] = build_shackles(info).to_object("A_shackles", [mat("iron")])
    return rep


# ----------------------------------------------------------------------------------------------------------------------
def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for me in list(bpy.data.meshes):
        bpy.data.meshes.remove(me)
    for m in list(bpy.data.materials):
        bpy.data.materials.remove(m)
    _MATS.clear()


def eval_bounds(objs, exclude=()):
    dg = bpy.context.evaluated_depsgraph_get()
    lo = np.full(3, 1e9)
    hi = np.full(3, -1e9)
    for k, o in objs.items():
        if k in exclude:
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        n = len(me.vertices)
        co = np.empty(n * 3)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        ev.to_mesh_clear()
        if n:
            lo = np.minimum(lo, co.min(axis=0))
            hi = np.maximum(hi, co.max(axis=0))
    return lo, hi


def build_common(pose, objs):
    robe = make_robe(pose)
    mr = MB()
    build_robe(mr, robe)
    objs["robe"] = mr.to_object("body_robe", [mat("robe")], solid=0.7)
    ms, mk, info = build_arms_and_sleeves(pose, objs)
    objs["sleeves"] = ms.to_object("body_sleeves", [mat("robe")], solid=0.5)
    build_feet(mk)
    build_neck(mk, pose)
    objs["skin"] = mk.to_object("body_skin", [mat("skin")])
    return robe, info


BUILDERS = {"a": build_a}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = []
    out = OUT_DIR
    i = 0
    while i < len(argv):
        if argv[i] == "--only":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                only.append(argv[i].lower())
                i += 1
            continue
        if argv[i] == "--out":
            out = os.path.abspath(argv[i + 1])
            i += 2
            continue
        i += 1
    keys = only or ["a", "b", "c"]
    os.makedirs(out, exist_ok=True)
    report = {}
    if os.path.exists(REPORT) and only:
        try:
            report = json.load(open(REPORT))
        except Exception:
            report = {}
    for key in keys:
        t0 = time.time()
        clear_scene()
        pose = Pose(ANG)
        objs = {}
        robe, info = build_common(pose, objs)
        extra = BUILDERS[key](pose, robe, info, objs)
        lo, hi = eval_bounds(objs)
        report[key] = dict(height=round(float(hi[2]), 1), width=round(float(hi[0] - lo[0]), 1), min=[round(float(v), 1) for v in lo],
                           max=[round(float(v), 1) for v in hi], **(extra or {}))
        mcl = extra.get("mask_centre_local") if extra else None
        if mcl:
            w = pose.head_matrix() @ Vector(mcl)
            report[key]["mask_centre_world"] = [round(w.x, 1), round(w.y, 1), round(w.z, 1)]
        report[key]["build_s"] = round(time.time() - t0, 1)
        path = os.path.join(out, "concept_%s.blend" % key)
        bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
        print("CONCEPT", key, json.dumps(report[key]))
    p = Pose(ANG)
    report["pose"] = dict(angles=ANG, net_head_pitch=round(p.net_head, 1),
                          joints={n: [round(q[0], 1), round(q[1], 1)] for (n, _, _), q in zip(REST, p.pos)})
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    json.dump(report, open(REPORT, "w"), indent=1)




# ----------------------------------------------------------------------------------------------------------------------
# CONCEPT B: THE BELL-BEARER
B_Z0 = -9.0          # bell mouth, head-local z
B_KEYS = [(0, 20.0), (1.0, 20.5), (2.5, 19.6), (5, 17.9), (9, 15.9), (15, 13.9), (22, 12.7), (32, 11.9), (39, 11.2),
          (42, 10.3), (44.3, 8.0), (45.6, 4.5), (46.0, 0.05)]
_BZ = np.arange(0, 46.01, 0.1)
_BR = smooth1(np.interp(_BZ, [k[0] for k in B_KEYS], [k[1] for k in B_KEYS]), 4.0)
_BR[0] = 20.0
_BR[-1] = 0.05


def bell_r(z):
    return np.interp(z, _BZ, _BR)


def bell_slope(z):
    return np.interp(z, _BZ[:-1] + 0.05, np.diff(_BR) / 0.1)


def bell_mod(TH, z):
    dent = -0.055 * np.exp(-((((TH - math.radians(205) + math.pi) % (2 * math.pi) - math.pi) / 0.40) ** 2 + ((z - 30.0) / 6.0) ** 2))
    return 1.0 + 0.016 * np.sin(3 * TH + 1.3 + z / 12.0) + 0.011 * np.sin(5 * TH + 0.2 - z / 9.0) + dent


def bell_point(zb, th, off=0.0):
    r = bell_r(zb) * bell_mod(th, zb) + off
    return np.stack([r * np.cos(th), r * np.sin(th), zb + B_Z0], axis=-1)


def bell_normal(zb, th):
    sl = bell_slope(zb)
    n = np.stack([np.cos(th), np.sin(th), -sl], axis=-1)
    return norm(n)


def build_bell(Mh):
    rng = random.Random(4402)
    zs = np.concatenate([np.arange(0, 41.0, 0.45), np.linspace(41.0, 46.0, 22)])
    nc = 260
    th = np.linspace(0, 2 * math.pi, nc, endpoint=False)
    Z, TH = np.meshgrid(zs, th, indexing="ij")
    P = bell_point(Z, TH)
    zc = 0.5 * (zs[:-1] + zs[1:])
    thc = th + (th[1] - th[0]) * 0.5
    ZC, THC = np.meshgrid(zc, thc, indexing="ij")
    rc = bell_r(ZC)
    # crack down the front (theta 270), wandering
    def crack_th(z):
        return math.radians(272) + 0.045 * np.sin(z / 5.0) + 0.02 * np.sin(z * 1.3) + 0.0012 * z

    d_arc = np.abs(((THC - crack_th(ZC) + math.pi) % (2 * math.pi)) - math.pi) * rc
    gapw = np.where(ZC < 34, 1.15 * np.clip(1 - ZC / 34.0, 0, 1) ** 1.1 + 0.15, 0.0)
    skip = (d_arc < gapw * 0.5) & (ZC < 34.5)
    dark = (d_arc < np.maximum(gapw * 0.5, 0.25) + 0.22) & (ZC < 42.0)
    # verdigris streaks and patches (flat second colour)
    verd = np.zeros(ZC.shape, dtype=bool)
    for _ in range(20):
        t0 = rng.uniform(0, 2 * math.pi)
        zs0 = rng.uniform(24, 45)
        ln = rng.uniform(7, 26)
        w = rng.uniform(0.8, 2.3)
        dth = np.abs(((THC - t0 + math.pi) % (2 * math.pi)) - math.pi) * rc
        u = np.clip((zs0 - ZC) / ln, 0, 1)
        verd |= (ZC <= zs0) & (ZC >= zs0 - ln) & (dth < w * 0.5 * (1.0 - 0.92 * u ** 0.8))
    lipn = 1.6 + 1.6 * (np.sin(THC * 7 + 1.0) * 0.5 + 0.5) * (np.sin(THC * 13) * 0.5 + 0.5)
    verd |= ZC < lipn
    verd |= (ZC > 43.5) & (np.sin(THC * 5 + 2) + np.sin(THC * 9) > 0.4)
    m = np.where(dark, 2, np.where(verd, 1, 0))
    mb = MB()
    mb.add_grid(xf(P, Mh), wrap_c=True, mat=m, skip=skip)
    # dark interior plug so the mouth reads as a cavity
    rr = np.linspace(0.05, 1, 6)[:, None] * (bell_r(13.0) * 0.97)
    plug = np.stack([rr * np.cos(th)[None, :], rr * np.sin(th)[None, :], np.full((6, nc), 13.0 + B_Z0)], axis=-1)
    mb2 = MB()
    mb2.add_grid(xf(plug, Mh), wrap_c=True, mat=0)
    # raised seams (plates) and rivets
    mseam = MB()
    mrv = MB()
    seam_th = [math.radians(a) for a in (28, 118, 208, 298)]
    for t0 in seam_th:
        zz = np.linspace(2.0, 41.0, 60)
        half = 1.15
        cols = []
        for sgn in (-1, 0, 1):
            tt = t0 + sgn * half / bell_r(zz)
            cols.append(bell_point(zz, tt, off=0.35 if sgn == 0 else 0.1))
        G = np.stack(cols, axis=1)
        mseam.add_grid(xf(G, Mh), mat=0)
        for zr in np.arange(4.0, 40.0, 4.6):
            p = bell_point(np.array(zr), np.array(t0), off=0.3)
            nn = bell_normal(np.array(zr), np.array(t0))
            add_dome(mrv, xf(p, Mh), np.array(Mh)[:3, :3] @ nn, 0.78, 0.6, sides=8, rings=3)
    for zr, step in ((3.2, 4.4), (26.0, 5.2), (14.0, 5.6)):
        nrv = int(2 * math.pi * bell_r(zr) / step)
        ringp = np.linspace(0, 2 * math.pi, 96, endpoint=False)
        Gr = np.stack([bell_point(np.full(96, zr - 0.9), ringp, off=0.2), bell_point(np.full(96, zr + 0.9), ringp, off=0.2)], axis=0)
        mseam.add_grid(xf(Gr, Mh), wrap_c=True, mat=0, flip=True)
        for k in range(nrv):
            t_ = 2 * math.pi * (k + 0.5) / nrv
            if abs(((t_ - math.radians(272) + math.pi) % (2 * math.pi)) - math.pi) < 0.1:
                continue
            p = bell_point(np.array(zr), np.array(t_), off=0.3)
            nn = bell_normal(np.array(zr), np.array(t_))
            add_dome(mrv, xf(p, Mh), np.array(Mh)[:3, :3] @ nn, 0.72, 0.55, sides=8, rings=3)
    return mb, mb2, mseam, mrv


def build_funnel(pose, seed=4410):
    """cloth collar that climbs the bell: the bell looks half swallowed / grown into"""
    def prof_r(h):
        zb = h - 254.0 - B_Z0
        return np.where(zb > 0, bell_r(np.clip(zb, 0, 46)) + 0.95, 0.0)
    hs0 = np.array([212, 220, 230, 238, 245], dtype=float)
    prof = [(212, 34.0, 18.0), (220, 23.0, 15.5), (230, 14.0, 13.0), (238, 14.5, 14.0), (244.0, 21.0, 21.0), (247, 21.4, 21.4)]
    for h in np.arange(248, 280, 2.0):
        r = float(prof_r(np.array(h)))
        prof.append((h, r, r))
    L = RingLoft(pose, prof, seed, fold_amp=(0.025, 0.05), fold_h=(280, 215), nfold=10)
    nc, nr = 200, 120
    th = np.linspace(0, 2 * math.pi, nc, endpoint=False)
    top = 249.0 + 0.55 * hem_raise(th, seed=33, ntongue=8)
    top = np.clip(top, 249.0, 276.0)
    s = np.linspace(0, 1, nr)
    H = 212.0 + (top[None, :] - 212.0) * s[:, None]
    TH = np.broadcast_to(th[None, :], H.shape)
    P = L.pts(H, TH)
    return P


def build_mantle(pose, seed=4411):
    prof = [(130, 45.0, 27.0), (165, 44.0, 26.0), (195, 43.5, 24.0), (208, 42.0, 22.0), (214, 38.0, 20.0), (219, 30.0, 17.0),
            (223, 20.0, 13.8), (226, 12.5, 11.0), (230, 11.0, 10.4)]

    def shift(H):
        return 4.0 * np.exp(-((H - 205.0) / 24.0) ** 2)
    L = RingLoft(pose, prof, seed, fold_amp=(0.05, 0.11), fold_h=(215, 150), nfold=12, shift=shift)
    L.hand = [(250, 6, 10, -0.10, 200, 150), (300, 6, 10, -0.08, 200, 150), (200, 8, 12, -0.12, 195, 150), (120, 8, 12, 0.07, 190, 150)]
    nc, nr = 190, 90
    th = np.linspace(0, 2 * math.pi, nc, endpoint=False)
    back = np.exp(-((((th - math.radians(90)) + math.pi) % (2 * math.pi) - math.pi) / math.radians(60)) ** 2)
    hb = 168.0 - 26.0 * back + 0.5 * np.clip(hem_raise(th, seed=91, ntongue=10), 0, 22)
    s = np.linspace(0, 1, nr)
    H = hb[None, :] + (230.0 - hb[None, :]) * s[:, None]
    TH = np.broadcast_to(th[None, :], H.shape)
    return L.pts(H, TH), L


def build_b(pose, robe, info, objs):
    Mh = pose.head_matrix() @ Matrix.Translation((0, 0, HEAD_DZ["b"]))
    rep = {}
    mb, mplug, mseam, mrv = build_bell(Mh)
    objs["bell"] = mb.to_object("B_bell", [mat("bronze"), mat("verdigris"), mat("dark")], solid=2.0)
    objs["bell_plug"] = mplug.to_object("B_plug", [mat("dark")])
    objs["bell_seams"] = mseam.to_object("B_seams", [mat("bronze")])
    objs["bell_rivets"] = mrv.to_object("B_rivets", [mat("bronze")])
    # iron: broken yoke stub on the crown + lug + neck chain + broken ring
    mi = MB()
    top = np.array([0.0, 0.0, 46.0 + B_Z0])
    path = np.array([[-5.0, 0, top[2] - 1.5], [-5.4, 0, top[2] + 1.8], [-3.2, 0, top[2] + 3.4], [-0.6, 0, top[2] + 2.2]])
    add_tube(mi, xf(resample(catmull(path, 6), 0.4), Mh), 1.2, 1.2, sides=8, cap0=False, cap1=True)
    lug = np.array([0.0, -(bell_r(1.5) + 0.7), 1.5 + B_Z0])
    tmpl = link_template(3.4, 2.5, 0.5, 14, 6)
    Rm = np.stack([np.array([0, 0, -1.0]), np.array([1.0, 0, 0]), np.array([0, -1.0, 0])], axis=1)
    mi.add_grid(xf(tmpl @ Rm.T + lug, Mh), wrap_c=True, wrap_r=True, mat=0)
    mant_P, mant = build_mantle(pose)
    ring_c = mant.pts(np.array([192.0]), np.array([math.radians(270)]), off=1.6)[0]
    p0 = xf(lug + np.array([0, 0, -1.5]), Mh)
    # broken ring (open torus) at the chest
    rr = 3.7
    ring = link_template(rr * 2, rr * 2, 0.75, 20, 6)
    nrm = np.array([0, -0.35, 0.0])
    Rm2 = np.stack([np.array([1.0, 0, 0]), np.array([0, 0.5, 0.86]), np.array([0, -0.86, 0.5])], axis=1)
    skp = np.zeros((20, 6), dtype=bool)
    skp[0:3, :] = True
    mi.add_grid(ring @ Rm2.T + ring_c, wrap_c=True, wrap_r=True, mat=0, skip=skp)
    p1 = ring_c + np.array([0, -0.4, 2.0 + rr * 0.9])
    path = hang_curve(p0, p1, 9.0, 40)
    add_chain(mi, path, 3.3, 2.2, 0.42)
    objs["bell_iron"] = mi.to_object("B_iron", [mat("iron")])
    # taut sinew cords from the lip into the mantle: the head and the body are one thing
    msk = MB()
    for k, dg in enumerate((-58, -30, -4, 22, 50, 126, 210)):
        t_ = math.radians(270 + dg)
        lip = xf(bell_point(np.array(2.2), np.array(t_), off=-0.4), Mh)
        tgt = mant.pts(np.array([221.0]), np.array([t_]), off=-1.0)[0]
        mid = (lip + tgt) / 2 + np.array([0.0, 0.0, -2.0]) + norm(np.array([math.cos(t_), math.sin(t_), 0.0])) * 1.6
        pth = resample(catmull([lip, mid, tgt], 8), 0.6)
        uu = np.linspace(0, 1, len(pth))
        r_ = np.interp(uu, [0, 0.15, 1], [1.0, 0.75, 1.1]) * (0.62 + 0.1 * (k % 3))
        add_tube(msk, pth, r_, r_, sides=7, cap0=False, cap1=False)
    objs["bell_sinew"] = msk.to_object("B_sinew", [mat("skin")])
    # cloth: funnel + mantle + belt
    Pf = build_funnel(pose)
    mf = MB()
    mf.add_grid(Pf, wrap_c=True, mat=0)
    objs["funnel"] = mf.to_object("B_funnel", [mat("robe")], solid=0.7)
    mm = MB()
    mm.add_grid(mant_P, wrap_c=True, mat=0)
    objs["mantle"] = mm.to_object("B_mantle", [mat("robe")], solid=1.1)
    mr = MB()
    rope_belt(mr, robe, pose)
    objs["rope"] = mr.to_object("B_rope", [mat("rope")])
    rep["mask_centre_local"] = [0.0, 0.0, 23.0 + B_Z0 + HEAD_DZ["b"]]
    return rep


# ----------------------------------------------------------------------------------------------------------------------
# CONCEPT C: THE VEILED SAINT
C_H0 = 257.0         # rest height of the face origin (zl = h - C_H0)


def face_delta(x, zl):
    """relief of the carved face under the cloth, cm, positive = out of the head (towards -Y).  zl: height above the chin - 1"""
    g = gauss2
    d = np.zeros_like(x)
    ax = np.abs(x)
    d += 1.6 * g(x, zl, 0, -0.5, 3.0, 1.9)                     # chin
    mouth_r2 = (x / 3.1) ** 2 + ((zl - 3.9) / 2.5) ** 2
    d += -4.4 * np.exp(-mouth_r2 ** 1.6)                      # open mouth: the cloth is sucked in
    d += 0.9 * np.exp(-((mouth_r2 - 2.2) / 0.9) ** 2) * (mouth_r2 > 1.0)  # lips
    d += 0.9 * g(x, zl, 0, 7.3, 2.6, 1.0)                     # philtrum / upper lip
    # nose
    hn = np.where(zl > 8.2, 3.6 * smoothstep(19.5, 9.5, zl), 0.0) * smoothstep(8.2, 10.4, zl)
    hn = hn + 1.0 * np.exp(-(((zl - 10.2) / 1.2) ** 2))
    sg = np.interp(zl, [8, 10, 14, 19], [1.6, 1.5, 1.0, 1.2])
    d += hn * np.exp(-0.5 * (x / sg) ** 2)
    d += 0.9 * g(ax, zl, 2.0, 10.2, 0.9, 0.9)                 # nostril wings
    d += 1.2 * g(ax, zl, 6.2, 12.6, 2.2, 1.9)                 # cheekbones
    d += -1.3 * g(ax, zl, 6.4, 5.4, 2.5, 3.0)                 # cheek hollows
    d += -2.3 * g(ax, zl, 4.3, 17.0, 2.3, 1.2)                # closed eye sockets
    d += 0.6 * g(ax, zl, 4.3, 18.4, 2.4, 0.6)                 # lid
    d += 1.7 * g(x, zl, 0, 19.4, 7.0, 1.2) * np.clip(1 - (ax / 9.0) ** 2, 0, 1)   # brow ridge
    d += -0.9 * g(ax, zl, 8.6, 20.0, 1.8, 3.0)                # temples
    return d


def blur2(A, sr, sc):
    def conv(a, sigma, axis):
        if sigma < 0.3:
            return a
        k = int(sigma * 3) + 1
        x = np.arange(-k, k + 1)
        w = np.exp(-0.5 * (x / sigma) ** 2)
        w /= w.sum()
        pad = [(0, 0)] * a.ndim
        pad[axis] = (k, k)
        ap = np.pad(a, pad, mode="edge")
        out = np.zeros_like(a)
        for i, wi in enumerate(w):
            sl = [slice(None)] * a.ndim
            sl[axis] = slice(i, i + a.shape[axis])
            out += wi * ap[tuple(sl)]
        return out
    return conv(conv(A, sr, 0), sc, 1)


def build_veil(pose, robe):
    prof = []
    for h in (126, 140, 160, 180, 200, 214, 222):
        rxr = float(np.interp(h, robe.hh, robe.rx))
        ryr = float(np.interp(h, robe.hh, robe.ry))
        prof.append((h, float(np.clip(0.62 * rxr, 9.5, 15.5)), ryr + 1.7))
    prof += [(228, 9.2, 10.8), (236, 7.9, 9.6), (243, 7.6, 9.4)]
    for zl, rx, ry in ((-3, 7.8, 9.2), (-1, 8.4, 10.0), (2, 8.9, 10.8), (8, 9.4, 11.4), (14, 9.7, 11.8), (22, 9.9, 12.0), (28, 9.6, 11.7),
                       (31.5, 8.4, 10.4), (34, 5.6, 7.2), (35.8, 2.2, 3.0), (36.6, 0.05, 0.05)):
        prof.append((C_H0 + zl, rx, ry))

    def shift(H):
        return 4.0 * np.exp(-((H - 205.0) / 24.0) ** 2)
    L = RingLoft(pose, prof, 4501, fold_amp=(0.02, 0.07), fold_h=(240, 130), nfold=9, shift=shift)
    hs = np.concatenate([np.arange(126, 244, 1.6), np.arange(244, C_H0 + 36.3, 0.30), [C_H0 + 36.6]])
    nc = 240
    th = np.linspace(0, 2 * math.pi, nc, endpoint=False)
    # ragged hem of the long veil
    hem = 126.0 + 9.0 * np.abs(np.sin(th * 3.5 + 1.0)) + 6.0 * np.abs(np.sin(th * 7.3)) + 0.0 * th
    Hs = np.broadcast_to(hs[:, None], (len(hs), nc)).copy()
    # squeeze the lower rings column by column so each column starts at its own hem height
    lowmask = hs < 244
    for j in range(nc):
        Hs[lowmask, j] = hem[j] + (244.0 - hem[j]) * (hs[lowmask] - 126.0) / (244.0 - 126.0)
    TH = np.broadcast_to(th[None, :], Hs.shape)
    P = L.pts(Hs, TH)
    # face relief on the front columns
    zl = Hs - C_H0
    x = P[..., 0]
    D = face_delta(x, zl) * 1.35
    wf = np.clip(-np.sin(TH), 0, 1) ** 0.7
    D = D * wf * smoothstep(-4.5, -1.0, zl) * smoothstep(32.0, 27.0, zl)
    D = blur2(D, 1.6, 1.6)
    y, z, t = pose.eval(Hs)
    ct, st = np.cos(np.radians(t)), np.sin(np.radians(t))
    nrm = np.stack([np.cos(TH) * 0.8, np.sin(TH) * ct, np.sin(TH) * st], axis=-1)
    nrm = norm(nrm)
    P = P + nrm * D[..., None]
    # cells inside the mouth read darker (cloth stretched into a void)
    def cell(A):
        Ar = np.roll(A, -1, axis=1)
        return 0.25 * (A[:-1] + A[1:] + Ar[:-1] + Ar[1:])
    xc, zc, thc = cell(x), cell(zl), cell(TH)
    mouth = ((xc / 2.6) ** 2 + ((zc - 3.9) / 2.0) ** 2 < 1.0) & (np.sin(thc) < -0.2)
    return P, mouth.astype(int)


def helical_strip(robe, th0, turns, h_a, h_b, width, off, seed, n=420, taper=True):
    rng = random.Random(seed)
    t = np.linspace(0, 1, n)
    TH = th0 + 2 * math.pi * turns * t + 0.04 * np.sin(t * 25 + seed)
    Hc = h_a + (h_b - h_a) * t
    w = width * (0.5 + 0.5 * np.clip(np.minimum(t, 1 - t) * 12, 0, 1)) if taper else np.full(n, width)
    w = w * (1 + 0.12 * np.sin(t * 60 + seed))
    G = np.stack([robe.pts(Hc - w / 2, TH, off=off), robe.pts(Hc + w / 2, TH, off=off + 0.15)], axis=1)
    return G, TH, Hc


def build_c(pose, robe, info, objs):
    Mh = pose.head_matrix() @ Matrix.Translation((0, 0, HEAD_DZ["c"]))
    rep = {}
    Pv, mouth = build_veil(pose, robe)
    mv = MB()
    base = mv.add_grid(Pv, wrap_c=True, mat=mouth)
    add_top_cap(mv, base, Pv.shape, True)
    objs["veil"] = mv.to_object("C_veil", [mat("linen"), mat("robe")], solid=0.5)
    # --- iron spike crown, 7 spikes 22 tall, riding the brow
    mi = MB()
    zc_ = 20.0 - 4.0 + 0.0                                    # head-local z of the band (face origin is 4 cm below the head joint)
    a_, b_, yc = 10.6, 12.5, 0.3
    zb = C_H0 - 254.0 + 20.2
    Pb, Rb = band_ring(a_, b_, yc, zb)
    pathb = xf(Pb, Mh)
    refb = Rb @ np.array(Mh)[:3, :3].T
    mi.add_grid(tube_grid(pathb, 0.55, 1.5, sides=8, ref=refb), wrap_r=True, wrap_c=True, mat=0)
    rng = random.Random(77)
    for k in range(7):
        phi = math.radians(270 + (k - 3) * 33.0)
        base = np.array([a_ * math.cos(phi), yc + b_ * math.sin(phi), zb + 0.5])
        rad = norm(np.array([math.cos(phi), math.sin(phi) * (b_ / a_), 0.0]))
        lean = 0.30 + 0.28 * abs(k - 3) / 3.0 + rng.uniform(-0.04, 0.04)
        tt = np.linspace(0, 1, 14)
        vz = 22.0 / math.sqrt(1 + lean * lean)
        path = base + rad[None, :] * (vz * lean * tt ** 1.3)[:, None] + np.stack([np.zeros_like(tt), np.zeros_like(tt), vz * tt], axis=1)
        rr = np.interp(tt, [0, 0.15, 1], [1.5, 1.25, 0.06])
        add_tube(mi, xf(path, Mh), rr, rr, sides=8, cap0=False, cap1=True, ref=np.array(Mh)[:3, :3] @ rad)
        # rivet at each spike root
        add_dome(mi, xf(base + rad * 1.0, Mh), np.array(Mh)[:3, :3] @ rad, 0.7, 0.5, sides=8, rings=3)
    objs["crown"] = mi.to_object("C_crown", [mat("iron")])
    # --- burial wrappings over the habit (linen strips) + loose ends
    mw = MB()
    specs = [(math.radians(210), 2.6, 128.0, 214.0, 4.0, 11), (math.radians(20), -2.4, 214.0, 130.0, 3.6, 12), (math.radians(95), 1.4, 90.0, 126.0, 4.0, 13), (math.radians(300), 3.1, 150.0, 206.0, 3.4, 14), (math.radians(120), -1.7, 200.0, 168.0, 3.8, 15)]
    for th0, turns, ha, hb, wd, sd in specs:
        G, TH, Hc = helical_strip(robe, th0, turns, ha, hb, wd, 0.7, sd)
        mw.add_grid(G, mat=0)
    # loose ends hanging from the torso
    for k, (th0, hh) in enumerate(((math.radians(330), 168.0), (math.radians(188), 150.0), (math.radians(60), 196.0))):
        p0 = robe.pts(np.array([hh]), np.array([th0]), off=1.4)[0]
        tt = np.linspace(0, 1, 18)
        sway = np.sin(tt * 3 + k)[:, None] * np.array([1.6, 1.0, 0.0])
        path = p0 + np.stack([np.zeros_like(tt), sway[:, 1], -tt * (34.0 + 6 * k)], axis=1)
        wd = (3.6 - 1.4 * tt)[:, None]
        G = np.stack([path - np.array([1, 0, 0]) * wd / 2, path + np.array([1, 0, 0]) * wd / 2], axis=1)
        mw.add_grid(G, mat=0)
    objs["wraps"] = mw.to_object("C_wraps", [mat("linen_old")], solid=0.25, smooth=False)
    # --- chain wound around the torso, then trailing
    mc = MB()
    t = np.linspace(0, 1, 260)
    TH = math.radians(300) + 2 * math.pi * 2.3 * t
    Hc = 140.0 + 62.0 * t + 1.2 * np.sin(t * 20)
    P = robe.pts(Hc, TH, off=3.0)
    tail0 = P[-1]
    tt = np.linspace(0, 1, 30)[1:, None]
    tail = tail0 + np.concatenate([np.zeros((29, 1)), 2.0 * np.sin(tt * 4), -tt * 38.0], axis=1)
    path = np.vstack([P, tail])
    add_chain(mc, path, 3.4, 2.3, 0.42, gap_last=True)
    objs["chain"] = mc.to_object("C_chain", [mat("iron")])
    rep["mask_centre_local"] = [0.0, -11.4, 14.0 + C_H0 - 254.0]
    return rep


HEAD_DZ = {"a": 0.0, "b": 0.0, "c": 0.0}
BUILDERS.update({"b": build_b, "c": build_c})


if __name__ == "__main__":
    main()
