"""hand_test.py -- P12-2b: two candidate Warden hands, built and rendered side by side (Blender 5.2, headless, seeded).

    blender.exe -b --factory-startup --python Tools/blender/warden/hand_test.py -- [--samples 64] [--res 800] [--only v1|v2] [--rows 1 2 3 4]
                                                                                    [--tiles DIR] [--no-sheet]
    python Tools/blender/warden/hand_test.py --sheet [--tiles DIR]        (Pillow only: composes the sheet from rendered tiles)

Writes Docs/ArtTest/warden/p12_hands.png and prints triangle counts.  Cycles on the CPU only (D-053).

Both hands are a LEFT hand with a 40 cm forearm stub, 30 cm from the wrist crease to the tip of the middle finger.
Local frame (cm, the same for both): origin = wrist crease, +Y toward the fingertips, +Z = back of the hand, +X = thumb side,
forearm along -Y.

  Version 1 "base mesh": the left hand and forearm are cut out of the BlenderKit Human Base Mesh (read through Blender's glTF
      importer only), the wrist bend is straightened, then the mesh is warped: forearm x1.6 and palm + fingers x1.4 lengthwise
      with a smooth blend across the wrist, thickness x0.75, the forearm cut capped, then decimated to the triangle budget.
      Nothing derived from it (mesh, .blend, FBX) is written to disk, only renders.
  Version 2 "scripted": a Skin-modifier joint graph (wrist, 4 metacarpals 9 cm, 4 fingers with phalanges 8/7/6 cm, thumb, forearm),
      Subdivision, then knuckle swelling, tendon ridges and a flattened palm by vertex offsets.

Poses (a throwaway script skin, no armature is saved): straight, and curled ~45 deg at every finger joint.
"""
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time

try:
    import bpy
    import bmesh
    import numpy as np
    from mathutils import Vector
except ImportError:  # plain python: only the --sheet mode (Pillow) is available
    bpy = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SRC = os.path.join(ROOT, "ExternalAssets", "Incoming", "blenderkit-b881b381-b12a-4057-b018-6506331564df", "human-base-mesh-sculpting_gltf.glb")
OUT = os.path.join(ROOT, "Docs", "ArtTest", "warden", "p12_hands.png")
TILES = os.path.join(tempfile.gettempdir(), "lb_hand_test")

HAND_LEN = 30.0      # cm, wrist crease to the middle fingertip
STUB_LEN = 40.0      # cm, wrist crease to the forearm cut
TRI_BUDGET = 4000
SEED = 1207

# ----------------------------------------------------------------------------------------------
# sheet (Pillow, plain python)
# ----------------------------------------------------------------------------------------------
ROW_LABELS = ["back of hand, fingers straight", "palm side, fingers straight", "three-quarter, curled 45 deg per joint", "same view: warm 2700 K point from below + cold rim"]


def compose_sheet(tiles_dir, meta):
    from PIL import Image, ImageDraw, ImageFont
    names = [("v1", "1 base mesh"), ("v2", "2 scripted")]
    first = Image.open(os.path.join(tiles_dir, "v1_row1.png"))
    tw, th = first.size
    head = 40
    S = Image.new("RGB", (tw * 2, th * 4 + head), (0, 0, 0))
    try:
        font = ImageFont.truetype("arial.ttf", 22)
        small = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font = small = ImageFont.load_default()
    d = ImageDraw.Draw(S)
    for ci, (key, label) in enumerate(names):
        info = meta.get(key, {})
        d.text((ci * tw + 12, 8), "%s   (%s tris)" % (label, info.get("tris", "?")), fill=(255, 235, 120), font=font)
        for ri, rlabel in enumerate(ROW_LABELS):
            p = os.path.join(tiles_dir, "%s_row%d.png" % (key, ri + 1))
            im = Image.open(p).convert("RGB")
            S.paste(im, (ci * tw, head + ri * th))
            ImageDraw.Draw(S).text((ci * tw + 10, head + ri * th + th - 24), rlabel, fill=(190, 190, 190), font=small)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    S.save(OUT)
    print("wrote", OUT, S.size)



def _sheet_main():
    argv = sys.argv[1:]
    tiles = TILES
    if "--tiles" in argv:
        tiles = os.path.abspath(argv[argv.index("--tiles") + 1])
    mp = os.path.join(tiles, "meta.json")
    compose_sheet(tiles, json.load(open(mp)) if os.path.exists(mp) else {})


if bpy is None:   # plain python (Pillow only): compose the sheet and stop, before the Blender-only code below
    _sheet_main()
    sys.exit(0)

# ----------------------------------------------------------------------------------------------
# small maths
# ----------------------------------------------------------------------------------------------


def sstep(a):
    a = np.clip(a, 0.0, 1.0)
    return a * a * (3.0 - 2.0 * a)


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def rot_about(P, pivot, axis, deg):
    """Rotate points P (n,3) about the line (pivot, axis) by deg (Rodrigues)."""
    a = unit(axis)
    t = math.radians(deg)
    p = P - pivot
    return pivot + p * math.cos(t) + np.cross(a, p) * math.sin(t) + np.outer(p @ a, a) * (1.0 - math.cos(t))


# ----------------------------------------------------------------------------------------------
# chains + the script skin (linear blend, one chain per digit)
# ----------------------------------------------------------------------------------------------
# chain = dict(J=(4,3) joints [MCP/CMC, PIP/MCP, DIP/IP, tip], t=curl target direction, sigma=membership radius (cm), w=blend half widths)


def chain_coords(P, J):
    """For each point: (s = arc length of the nearest point on the chain, d = distance to the chain).  The first
    bone is extended backwards without limit so the palm side blends smoothly."""
    seg = [J[k + 1] - J[k] for k in range(3)]
    L = [np.linalg.norm(x) for x in seg]
    S = [0.0, L[0], L[0] + L[1]]
    best_d = np.full(len(P), 1e9)
    best_s = np.zeros(len(P))
    for k in range(3):
        e = seg[k] / L[k]
        u = (P - J[k]) @ e
        lo = -1e9 if k == 0 else 0.0
        u = np.clip(u, lo, L[k])
        d = np.linalg.norm(P - (J[k] + np.outer(u, e)), axis=1)
        m = d < best_d
        best_d[m] = d[m]
        best_s[m] = S[k] + u[m]
    return best_s, best_d, S, L


def pose_points(V, chains, angles):
    """angles: {chain: (a0, a1, a2)} degrees, positive = curl toward the chain's target direction."""
    out_delta = np.zeros_like(V)
    raws = {}
    for name, c in chains.items():
        _, d, _, _ = chain_coords(V, c["J"])
        raws[name] = np.exp(-(d / c["sigma"]) ** 2)
    tot = sum(raws.values())
    denom = np.maximum(tot, 0.5)
    for name, c in chains.items():
        ang = angles.get(name, (0, 0, 0))
        if not any(ang):
            continue
        J = c["J"]
        s, _, S, L = chain_coords(V, J)
        b = [sstep((s - S[k]) / (2.0 * c["w"][k]) + 0.5) for k in range(3)]
        axes = [unit(np.cross(unit(J[k + 1] - J[k]), c["t"])) for k in range(3)]

        def G(k, p):
            q = p
            for j in range(k, -1, -1):
                q = rot_about(q, J[j], axes[j], ang[j])
            return q
        w_ = [1.0 - b[0], b[0] - b[1], b[1] - b[2], b[2]]
        res = V * w_[0][:, None] + G(0, V) * w_[1][:, None] + G(1, V) * w_[2][:, None] + G(2, V) * w_[3][:, None]
        out_delta += (raws[name] / denom)[:, None] * (res - V)
    return V + out_delta


POSES = {
    "straight": {},
    "curl": {
        "index": (45, 45, 45), "middle": (45, 45, 45), "ring": (45, 45, 45), "pinky": (45, 45, 45),
        "thumb": (18, 30, 38),
    },
}

# ----------------------------------------------------------------------------------------------
# blender helpers
# ----------------------------------------------------------------------------------------------


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def faces_to_tris(F):
    n = 0
    for f in F:
        n += len(f) - 2
    return n


def mesh_object(name, V, F, mat=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in V], [], [tuple(int(i) for i in f) for f in F])
    me.update()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat is not None:
        me.materials.append(mat)
    return ob


def read_mesh(ob):
    """Evaluated mesh of ob -> (V (n,3), F list of tuples)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    V = np.array([v.co[:] for v in me.vertices], dtype=float)
    F = [tuple(p.vertices) for p in me.polygons]
    bpy.data.meshes.remove(me)
    return V, F


def mesh_to_np(me):
    return np.array([v.co[:] for v in me.vertices], dtype=float)


def bm_from_VF(V, F):
    bm = bmesh.new()
    vs = [bm.verts.new(tuple(map(float, v))) for v in V]
    for f in F:
        bm.faces.new([vs[i] for i in f])
    bm.verts.index_update()
    return bm


def bm_to_VF(bm):
    bm.verts.index_update()
    V = np.array([v.co[:] for v in bm.verts], dtype=float)
    F = [tuple(v.index for v in f.verts) for f in bm.faces]
    return V, F


def recalc_normals(V, F):
    bm = bm_from_VF(V, F)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    V2, F2 = bm_to_VF(bm)
    bm.free()
    return V2, F2


# ----------------------------------------------------------------------------------------------
# VERSION 1: base mesh
# ----------------------------------------------------------------------------------------------
# straightening constants (cm, source mesh space, found by slicing the arm; see the notes at the top of the file)
W_CREASE = np.array([50.6, 4.0, 110.8])           # wrist crease centre
DIR_FOREARM = unit([0.52248946, -0.10774872, -0.84581025])   # elbow -> wrist
TIP_MEAN = np.array([56.885, 2.173, 91.447])      # mean of the farthest fingertip vertices
HAND_SCALE = 1.40
FORE_SCALE = 1.60
THICK = 0.75
BLEND = 4.0                                        # half width of the stretch blend across the wrist (cm)

# rough finger lines in the straightened frame (cm, source scale): mcp (x, y), tip (x, y)
FINGER_LINES = {
    "index": ((2.9, 8.6), (3.4, 19.6)),
    "middle": ((-0.6, 8.8), (-1.2, 20.7)),
    "ring": ((-3.6, 8.2), (-5.0, 18.6)),
    "pinky": ((-7.2, 7.2), (-8.8, 14.8)),
}
THUMB_J = np.array([[3.6, 0.3, -1.2], [6.4, 6.2, -3.0], [7.5, 10.4, -4.4], [8.1, 13.5, -5.0]])
FRACS = (0.0, 0.46, 0.76, 1.0)                     # MCP, PIP, DIP, tip along the finger


def frame_rows(y):
    z = np.array([1.0, 0.0, 0.0])
    z = unit(z - (z @ y) * y)
    x = np.cross(y, z)
    return np.array([x, y, z])


def load_base_hand():
    """-> straightened source-scale hand + forearm, cm, wrist crease at the origin, fingers +Y, back +Z, thumb +X."""
    bpy.ops.import_scene.gltf(filepath=SRC)
    srcs = [o for o in bpy.data.objects if o.type == "MESH"]
    assert len(srcs) == 1, "expected one mesh in the base mesh glb"
    ob = srcs[0]
    me = ob.data
    mw = ob.matrix_world
    bm = bmesh.new()
    bm.from_mesh(me)
    for v in bm.verts:
        v.co = mw @ v.co
        v.co = v.co * 100.0
    n_soup = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-3)
    n_merged = len(bm.verts)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.x < 28.0], context="VERTS")
    V, F = bm_to_VF(bm)
    bm.free()
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    info = {"source_vertices_unmerged": n_soup, "source_vertices_merged": n_merged, "arm_vertices": len(V)}
    # straighten the wrist bend: forearm frame / hand frame, blended over the wrist
    dh = unit(TIP_MEAN - W_CREASE)
    Ff, Fh = frame_rows(DIR_FOREARM), frame_rows(dh)
    p = V - W_CREASE
    ya = p @ unit(DIR_FOREARM + dh)
    w = sstep((ya + 5.0) / 9.0)
    q = (p @ Ff.T) * (1 - w)[:, None] + (p @ Fh.T) * w[:, None]
    info["wrist_bend_deg"] = math.degrees(math.acos(float(DIR_FOREARM @ dh)))
    return q, F, info


def fit_chains(Q):
    """Finger and thumb chains from the straightened source-scale vertices Q."""
    chains = {}
    for name, ((mx, my), (tx, ty)) in FINGER_LINES.items():
        a, b = np.array([mx, my]), np.array([tx, ty])
        ab = b - a
        L = np.linalg.norm(ab)
        u = np.clip(((Q[:, :2] - a) @ ab) / (L * L), 0, 1.2)
        dist = np.linalg.norm(Q[:, :2] - (a + np.outer(u, ab)), axis=1)
        m = (dist < 2.0) & (Q[:, 1] > 9.6) & (Q[:, 1] < ty + 1.0)
        S = Q[m]
        # centre line x(y), z(y): quadratic fit of slice centroids
        ys = np.arange(math.floor(S[:, 1].min()), S[:, 1].max(), 0.8)
        cy, cx, cz = [], [], []
        for y0 in ys:
            mm = (S[:, 1] >= y0) & (S[:, 1] < y0 + 0.8)
            if mm.sum() >= 4:
                cy.append(S[mm, 1].mean()); cx.append(S[mm, 0].mean()); cz.append(S[mm, 2].mean())
        px = np.polyfit(cy, cx, 2)
        pz = np.polyfit(cy, cz, 2)
        tip_y = S[:, 1].max() - 0.45
        j_y = [my + f * (tip_y - my) for f in FRACS]
        J = np.array([[np.polyval(px, y), y, np.polyval(pz, y)] for y in j_y])
        chains[name] = {"J": J, "t": np.array([0.0, 0.0, -1.0]), "sigma": 1.5, "w": (0.9, 0.8, 0.8)}
    chains["thumb"] = {"J": THUMB_J.copy(), "t": unit([-0.55, 0.0, -0.8]), "sigma": 2.3, "w": (2.2, 1.0, 0.9)}
    return chains


def build_v1():
    info = {}
    Q, F, info = load_base_hand()
    mid = Q[(np.abs(Q[:, 0] + 1.0) < 2.0) & (Q[:, 1] > 0)]
    tip_y = float(mid[:, 1].max())
    info["source_hand_len_cm"] = tip_y
    chains_src = fit_chains(Q)

    # stretch function: y -> y', forearm FORE_SCALE, hand HAND_SCALE, smooth blend across the crease; Y0 chosen so the
    # middle finger ends exactly HAND_LEN from the crease
    grid = np.linspace(-80.0, 40.0, 24001)

    def G_table(y0):
        yy = grid - y0
        s = FORE_SCALE + (HAND_SCALE - FORE_SCALE) * sstep((yy + BLEND) / (2 * BLEND))
        cum = np.concatenate([[0.0], np.cumsum(0.5 * (s[1:] + s[:-1]) * np.diff(yy))])
        cum -= np.interp(0.0, yy, cum)
        return yy, cum
    lo, hi = -6.0, 6.0
    for _ in range(60):
        y0 = 0.5 * (lo + hi) + tip_y - 22.0
        yy, cum = G_table(y0)
        L = float(np.interp(tip_y - y0, yy, cum))
        if L > HAND_LEN:
            lo = 0.5 * (lo + hi)
        else:
            hi = 0.5 * (lo + hi)
    y0 = 0.5 * (lo + hi) + tip_y - 22.0
    yy, cum = G_table(y0)
    info["crease_shift_cm"] = -y0 + 0.0

    def warp(P):
        R = np.array(P, dtype=float)
        out = np.empty_like(R)
        out[:, 0] = R[:, 0] * THICK
        out[:, 2] = R[:, 2] * THICK
        out[:, 1] = np.interp(R[:, 1] - y0, yy, cum)
        return out

    # cut the forearm at STUB_LEN after the stretch: find source y with G(y) = -STUB_LEN
    y_cut = float(np.interp(-STUB_LEN, cum, yy)) + y0
    bm = bm_from_VF(Q, F)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, y_cut, 0), plane_no=(0, 1, 0), clear_inner=True)
    bm.edges.ensure_lookup_table()
    bound = [e for e in bm.edges if e.is_boundary]
    cap = bmesh.ops.contextual_create(bm, geom=bound)["faces"]
    cx = bmesh.ops.poke(bm, faces=cap, offset=-0.4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    Vc, Fc = bm_to_VF(bm)
    bm.free()
    info["cut_source_y"] = y_cut
    info["tris_before_decimate"] = faces_to_tris(Fc)
    Vw = warp(Vc)
    chains = {}
    for k, c in chains_src.items():
        cc = dict(c)
        cc["J"] = warp(c["J"])
        # sigma / blend widths scale with the thinner, longer hand
        cc["sigma"] = c["sigma"] * THICK
        chains[k] = cc
    # decimate (collapse), the forearm is allowed to lose more
    # extra slimming of the digits about their own centre lines (the global x0.75 closes the gaps; this keeps the fingers thin
    # without squeezing the palm): x0.88 from the knuckle, down to x0.78 at the fingertip, so the tips are not sausages
    for k, c in chains.items():
        s_, d_, S_, L_ = chain_coords(Vw, c["J"])
        tot = S_[2] + L_[2]
        inside = 1.0 - sstep((d_ - c["sigma"] * 1.1) / 0.6)
        ramp = sstep((s_ + 0.5) / 2.0)
        f = 1.0 - (0.12 + 0.10 * np.clip(s_ / tot, 0, 1)) * inside * ramp
        e0 = (c["J"][1] - c["J"][0]); e0 = e0 / np.linalg.norm(e0)
        # nearest axis point (piecewise)
        ax = np.zeros_like(Vw)
        seg_i = np.where(s_ < L_[0], 0, np.where(s_ < L_[0] + L_[1], 1, 2))
        for kk in range(3):
            e = (c["J"][kk + 1] - c["J"][kk]) / L_[kk]
            m = seg_i == kk
            u = np.clip((Vw[m] - c["J"][kk]) @ e, -1e9 if kk == 0 else 0.0, L_[kk])
            ax[m] = c["J"][kk] + np.outer(u, e)
        Vw = ax + (Vw - ax) * f[:, None]
    V, F = decimate(Vw, Fc, TRI_BUDGET - 60)
    info["tris"] = faces_to_tris(F)
    return V, F, chains, info


# ----------------------------------------------------------------------------------------------
# VERSION 2: scripted skin
# ----------------------------------------------------------------------------------------------
V2_FINGERS = {
    #          mcp x   MC len  splay deg  length k   shaft r
    "index": (3.15, 9.0, 5.0, 0.97, 0.54),
    "middle": (1.05, 9.0, 0.5, 1.00, 0.54),
    "ring": (-1.10, 8.5, -5.0, 0.94, 0.50),
    "pinky": (-3.15, 7.8, -11.0, 0.78, 0.44),
}
# radius profile along a finger as a multiple of the shaft radius: MCP knuckle, prox shaft, PIP, mid shaft, DIP, distal shaft, tip
FINGER_PROFILE = (1.85, 1.28, 1.42, 0.86, 1.28, 0.90, 0.92)
PHAL = (8.0, 7.0, 6.0)
CARPAL_X = {"index": 2.0, "middle": 0.7, "ring": -0.7, "pinky": -2.0}
TIP_PAD = 0.35
REST_CURL = (4.0, 9.0, 14.0)      # cumulative degrees toward the palm: a relaxed hand, not a ruler


def build_v2_graph():
    P, E, R, name = [], [], [], []

    def add(n, pos, r, parent=None):
        P.append(tuple(float(c) for c in pos)); R.append(r); name.append(n)
        i = len(P) - 1
        if parent is not None:
            E.append((parent, i))
        return i
    roots = []
    # forearm: its own chain, starting inside the palm pillow; thin, bony, a little thicker toward the elbow end
    wrist = add("wrist", (0, 0.4, 0), (2.05, 1.3))
    roots.append(wrist)
    prev = wrist
    for y, r in ((-6, (2.0, 1.3)), (-14, (2.3, 1.7)), (-27, (2.55, 2.15)), (-40, (2.9, 2.5))):
        prev = add("fore", (0, y, 0), r, prev)
    chains = {}
    for fname, (mx, mlen, splay, lk, rs) in V2_FINGERS.items():
        my = math.sqrt(max(mlen ** 2 - mx ** 2, 1.0))
        mcp_pos = np.array([mx, my, 0.0])
        xb = CARPAL_X[fname]
        pr = [rs * f for f in FINGER_PROFILE]
        carpal = add("carpal_" + fname, (xb, 0.8, 0.0), (0.7, 0.6))
        roots.append(carpal)
        mc_mid = add("mc_" + fname, ((xb + mx) * 0.5, (0.8 + my) * 0.5, 0.2), (0.95, 0.74), carpal)
        mcp = add(fname + "_mcp", mcp_pos, (pr[0], pr[0] * 0.8), mc_mid)
        a = math.radians(splay)
        d = np.array([math.sin(a), math.cos(a), 0.0])
        pos = mcp_pos.copy()
        J = [mcp_pos.copy()]
        prev = mcp
        for k in range(3):
            L = PHAL[k] * lk + (TIP_PAD if k == 2 else 0.0)
            th = math.radians(REST_CURL[k])
            dk = np.array([d[0] * math.cos(th), d[1] * math.cos(th), -math.sin(th)])
            mid = pos + dk * (L * 0.5)
            end = pos + dk * L
            rm, rj = pr[1 + 2 * k], pr[2 + 2 * k]
            prev = add("%s_m%d" % (fname, k), mid, (rm, rm), prev)
            if k < 2:
                prev = add("%s_j%d" % (fname, k + 1), end, (rj, rj), prev)
            else:   # bullet tip: a full-radius vertex just short of the end, then a smaller one at the end
                prev = add("%s_tipA" % fname, end - dk * 0.55, (rj, rj * 0.95), prev)
                prev = add("%s_tip" % fname, end, (rj * 0.5, rj * 0.45), prev)
            pos = end
            J.append(end.copy())
        chains[fname] = {"J": np.array(J), "t": np.array([0.0, 0.0, -1.0]), "sigma": 1.2 * (rs / 0.5 * 0.5 + 0.5), "w": (0.8, 0.7, 0.7)}
    # thumb: opposed, 36 deg out from the index line, 30 deg toward the palm
    ab, op = math.radians(36.0), math.radians(30.0)
    d = np.array([math.sin(ab) * math.cos(op), math.cos(ab) * math.cos(op), -math.sin(op)])
    t0 = np.array([1.5, 0.6, -0.7])
    tj = add("thumb_cmc", t0, (1.45, 1.15))
    roots.append(tj)
    prev = tj
    pos = t0.copy()
    J = [t0.copy()]
    for k, (L, rj, rm) in enumerate(((6.4, 0.78, 1.10), (4.6, 0.64, 0.62), (3.6, 0.52, 0.50))):
        dk = d.copy()
        if k >= 1:
            dk = unit(dk + np.array([-0.10 * k, 0.05, -0.10 * k]))
        mid = pos + dk * (L * 0.5)
        end = pos + dk * (L + (TIP_PAD if k == 2 else 0.0))
        prev = add("thumb_m%d" % k, mid, (rm, rm), prev)
        if k < 2:
            prev = add("thumb_j%d" % (k + 1), end, (rj, rj), prev)
        else:
            prev = add("thumb_tipA", end - dk * 0.55, (0.52, 0.48), prev)
            prev = add("thumb_tip", end, (0.27, 0.24), prev)
        pos = end
        J.append(end.copy())
    chains["thumb"] = {"J": np.array(J), "t": unit([-0.55, 0.0, -0.8]), "sigma": 1.6, "w": (2.0, 0.9, 0.8)}
    return P, E, R, name, chains, roots


def gauss(d2, s):
    return np.exp(-d2 / (2.0 * s * s))


def swell(V, chains, spec):
    """Radial swelling of the joints: push vertices near joint k of a chain away from the chain axis (all round, more on the back)."""
    V = V.copy()
    for name, c in chains.items():
        J = c["J"]
        s_, d_, S, L = chain_coords(V, J)
        seg_i = np.where(s_ < L[0], 0, np.where(s_ < L[0] + L[1], 1, 2))
        # nearest axis point for the radial direction
        ax = np.zeros_like(V)
        for k in range(3):
            e = (J[k + 1] - J[k]) / L[k]
            m = seg_i == k
            u = np.clip((V[m] - J[k]) @ e, -1e9 if k == 0 else 0.0, L[k])
            ax[m] = J[k] + np.outer(u, e)
        rad = V - ax
        rn = np.linalg.norm(rad, axis=1)
        rad = rad / np.maximum(rn, 1e-6)[:, None]
        for kj, (amp, sig) in spec.get(name, spec["default"]).items():
            sj = S[kj] if kj < 3 else L[0] + L[1] + L[2]
            g = gauss((s_ - sj) ** 2, sig) * (rn < 2.2)
            V += rad * (amp * g)[:, None]
    return V


def detail_v2(V, chains):
    """Knuckle swelling, tendon ridges on the back of the hand, a bony wrist: offsets of the high-res vertices."""
    V = V.copy()
    x, y, z = V[:, 0], V[:, 1], V[:, 2]
    back = sstep((z - 0.15) / 0.5)                       # only the back side of the hand / forearm
    dz = np.zeros(len(V))
    for fname, (mx, mlen, splay, lk, rs) in V2_FINGERS.items():
        J = chains[fname]["J"]
        my = J[0][1]
        # tendon ridge: a thin line from the wrist to the knuckle on the back of the hand, strongest mid-palm
        t = np.clip(y / my, 0, 1)
        xl = CARPAL_X[fname] + (mx - CARPAL_X[fname]) * t
        ridge = gauss((x - xl) ** 2, 0.28) * sstep((y - 1.0) / 2.0) * sstep((my - 0.3 - y) / 1.0)
        dz += 0.34 * ridge * back
        # knuckle knobs (MCP, PIP, DIP) on the back of each finger
        for k, (amp, sig) in enumerate(((0.34, 0.95), (0.26, 0.62), (0.18, 0.5))):
            c = J[k]
            d2 = (x - c[0]) ** 2 + (y - c[1]) ** 2 + (z - c[2]) ** 2
            dz += amp * gauss(d2, sig) * back
    # bony wrist: ulna head (little-finger side, back) and the radial styloid
    for cx, cy, a in ((-1.9, 0.6, 0.38), (2.0, 0.4, 0.26)):
        dz += a * gauss((x - cx) ** 2 + (y - cy) ** 2 + (z - 0.6) ** 2, 0.8) * back
    # forearm: the ulna ridge on the little-finger side of the back, and two extensor tendons running to the wrist
    fore = sstep((-y - 0.5) / 3.0) * sstep((40.0 + y) / 8.0)
    dz += 0.26 * gauss((x + 1.35) ** 2, 0.55) * back * fore
    for tx in (-0.3, 0.6):
        dz += 0.12 * gauss((x - tx) ** 2, 0.3) * back * sstep((-y - 0.5) / 2.0) * sstep((22.0 + y) / 8.0)
    V[:, 2] += dz
    return V


def decimate(V, F, target_tris, y_soft=-16.0):
    """Collapse decimation to the triangle budget; the forearm gives up more than the hand.  Very dense input is first brought
    down to 12k triangles with no weighting (the weighted pass can't reach a 1:50 ratio)."""
    if faces_to_tris(F) > 14000:
        ob = mesh_object("dec_pre0", V, F)
        md = ob.modifiers.new("dec0", "DECIMATE")
        md.decimate_type = "COLLAPSE"
        md.ratio = 12000.0 / faces_to_tris(F)
        md.use_collapse_triangulate = True
        V, F = read_mesh(ob)
        bpy.data.objects.remove(ob)
    for _ in range(8):                      # the weighted collapse may stop early: repeat until the budget is met
        n = faces_to_tris(F)
        if n <= target_tris:
            break
        ob = mesh_object("dec_pre", V, F)
        vg = ob.vertex_groups.new(name="keep")
        wts = 0.8 - sstep((V[:, 1] - y_soft) / 8.0) * 0.65    # high weight = collapses more (forearm); low = kept (hand)
        for i, wv in enumerate(wts):
            vg.add([i], float(wv), "REPLACE")
        md = ob.modifiers.new("dec", "DECIMATE")
        md.decimate_type = "COLLAPSE"
        md.ratio = max(0.05, min(0.97, target_tris / n * 0.985))
        md.use_collapse_triangulate = True
        md.vertex_group = "keep"
        md.vertex_group_factor = 1.2
        V, F = read_mesh(ob)
        bpy.data.objects.remove(ob)
    return V, F


def loft(profile, n_ring=20, p=2.2):
    """Closed lofted shell along +Y. profile = [(y, half width, half thickness, z centre)], rounded end caps."""
    rings = []
    for (y, w, h, zc) in profile:
        pts = []
        for i in range(n_ring):
            a = 2 * math.pi * i / n_ring
            c, sn = math.cos(a), math.sin(a)
            pts.append((w * math.copysign(abs(c) ** (2 / p), c), y, zc + h * math.copysign(abs(sn) ** (2 / p), sn)))
        rings.append(pts)
    V = [q for r in rings for q in r]
    F = []
    for r in range(len(rings) - 1):
        for i in range(n_ring):
            a, b = r * n_ring + i, r * n_ring + (i + 1) % n_ring
            F.append((a, b, b + n_ring, a + n_ring))
    y0 = profile[0][0] - 0.01
    y1 = profile[-1][0] + 0.01
    V.append((0.0, y0, profile[0][3])); c0 = len(V) - 1
    V.append((0.0, y1, profile[-1][3])); c1 = len(V) - 1
    for i in range(n_ring):
        F.append((c0, (i + 1) % n_ring, i))
        last = (len(rings) - 1) * n_ring
        F.append((c1, last + i, last + (i + 1) % n_ring))
    return np.array(V, dtype=float), F


def palm_pillow():
    """The palm and back of the hand: a lofted, slightly cupped slab (trapezoid, rounded edges) plus a thenar mound at the thumb
    root.  Closed shells that the finger and forearm shells overlap; the voxel remesh welds them into one surface."""
    prof = [(-1.2, 1.1, 0.55, 0.0), (-0.6, 2.2, 0.80, 0.0), (0.6, 2.75, 0.88, 0.0), (3.0, 3.35, 0.88, 0.0), (5.5, 3.95, 0.80, 0.0),
            (7.8, 4.05, 0.70, 0.0), (8.7, 3.7, 0.55, 0.0), (9.3, 2.9, 0.38, 0.0)]
    V, F = loft(prof)
    X, Y, Z = V[:, 0], V[:, 1], V[:, 2]
    Y = Y - 0.07 * (X + 0.4) ** 2 * sstep((Y - 3.0) / 5.0)    # knuckle arc: the pinky side ends lower
    Z = Z - 0.030 * X ** 2                                    # cupped across the palm
    V = np.stack([X, Y, Z], axis=1)
    V, F = recalc_normals(V, F)
    # thenar mound: an ellipsoid along the thumb metacarpal, on the palm side
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    Vt, Ft = bm_to_VF(bm)
    bm.free()
    d = unit([0.55, 0.85, -0.3])
    ax2 = unit(np.cross([0, 0, 1.0], d))
    ax3 = np.cross(d, ax2)
    Vt = (Vt[:, 0:1] * 1.55) * ax2 + (Vt[:, 1:2] * 3.6) * d + (Vt[:, 2:3] * 1.0) * ax3 + np.array([2.1, 2.8, -0.55])
    Vt, Ft = recalc_normals(Vt, Ft)
    n0 = len(V)
    V = np.vstack([V, Vt])
    F = list(F) + [tuple(i + n0 for i in f) for f in Ft]
    return V, F


def laplacian(V, F, weight, iters=12, lam=0.6):
    """Weighted umbrella smoothing on a triangle/quad mesh (numpy): weight (n,) in 0..1 per vertex."""
    pairs = []
    for f in F:
        n = len(f)
        for i in range(n):
            pairs.append((f[i], f[(i + 1) % n]))
    e = np.array(pairs)
    a = np.concatenate([e[:, 0], e[:, 1]])
    b = np.concatenate([e[:, 1], e[:, 0]])
    cnt = np.bincount(a, minlength=len(V)).astype(float)
    V = V.copy()
    for _ in range(iters):
        acc = np.stack([np.bincount(a, weights=V[b, k], minlength=len(V)) for k in range(3)], axis=1)
        avg = acc / np.maximum(cnt, 1)[:, None]
        V += (avg - V) * (lam * weight)[:, None]
    return V


def voxel_union(V, F, voxel):
    ob = mesh_object("union_pre", V, F)
    md = ob.modifiers.new("rm", "REMESH")
    md.mode = "VOXEL"
    md.voxel_size = voxel
    md.adaptivity = 0.0
    sm = ob.modifiers.new("sm", "SMOOTH")
    sm.factor = 0.5
    sm.iterations = 5
    V2, F2 = read_mesh(ob)
    bpy.data.objects.remove(ob)
    return V2, F2


def build_v2():
    P, E, R, names, chains, roots = build_v2_graph()
    me = bpy.data.meshes.new("v2_graph")
    me.from_pydata(P, E, [])
    ob = bpy.data.objects.new("v2_graph", me)
    bpy.context.scene.collection.objects.link(ob)
    sk = ob.modifiers.new("skin", "SKIN")
    sk.branch_smoothing = 0.9
    sk.use_smooth_shade = True
    layer = me.skin_vertices[0].data
    for i, r in enumerate(R):
        layer[i].radius = r
    for i in roots:
        layer[i].use_root = True
    sub = ob.modifiers.new("sub", "SUBSURF")
    sub.levels = 2
    sub.render_levels = 2
    V, F = read_mesh(ob)
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    info = {"tris_skin_subd2": faces_to_tris(F)}
    Vp, Fp = palm_pillow()
    V = np.vstack([V, Vp])
    F = list(F) + [tuple(i + len(V) - len(Vp) for i in f) for f in Fp]
    V, F = voxel_union(V, F, 0.11)
    info["tris_voxel_union"] = faces_to_tris(F)
    # smooth the palm, wrist and forearm hard (the shell joins), leave the digits alone
    wgt = np.ones(len(V))
    for name, c in chains.items():
        s_, d_, S_, L_ = chain_coords(V, c["J"])
        wgt = np.minimum(wgt, 1.0 - sstep((s_ + 0.3 - (3.5 if name == "thumb" else 0.0)) / 1.2) * (1.0 - sstep((d_ - 1.0) / 1.2)))
    V = laplacian(V, F, wgt, iters=110, lam=0.5)
    V = swell(V, chains, {"default": {1: (0.17, 0.55), 2: (0.12, 0.48)}, "thumb": {1: (0.12, 0.7), 2: (0.09, 0.55)}})
    V = detail_v2(V, chains)
    if not os.environ.get("HT_NODEC"):
        V, F = decimate(V, F, TRI_BUDGET - 60)
    info["tris"] = faces_to_tris(F)
    return V, F, chains, info


# ----------------------------------------------------------------------------------------------
# rendering
# ----------------------------------------------------------------------------------------------
def kelvin_rgb(k):
    t = k / 100.0
    r = 255.0 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255.0 if t >= 66 else (0.0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    return tuple(max(0.0, min(255.0, c)) / 255.0 for c in (r, g, b))


def srgb_to_lin(c):
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def clay_material():
    m = bpy.data.materials.new("clay")
    m.use_nodes = True
    n = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    n.inputs["Base Color"].default_value = (0.32, 0.29, 0.26, 1.0)
    n.inputs["Roughness"].default_value = 0.55
    return m


def aim(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def add_light(name, kind, loc, target, energy, color=(1, 1, 1), size=40.0, radius=2.0):
    li = bpy.data.lights.new(name, kind)
    li.energy = energy
    li.color = color
    if kind == "AREA":
        li.shape = "SQUARE"
        li.size = size
    elif kind == "POINT":
        li.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, li)
    ob.location = loc
    bpy.context.scene.collection.objects.link(ob)
    aim(ob, target)
    return ob


def setup_scene(res_x, res_y, samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    try:
        bpy.context.preferences.addons["cycles"].preferences.compute_device_type = "NONE"
    except Exception:
        pass
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = False
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    try:
        sc.cycles.denoising_use_gpu = False
    except Exception:
        pass
    sc.cycles.seed = SEED
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = res_x, res_y, 100
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    w = bpy.data.worlds.new("black")
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0, 0, 0, 1)
    bg.inputs["Strength"].default_value = 0.0
    sc.world = w
    return sc


# view tuple: (camera position, target, lens mm); all in the hand frame (cm)
VIEWS = {
    "back": ((0.0, 8.0, 112.0), (0.0, 8.0, 0.0), 90.0),
    "palm": ((0.0, 8.0, -112.0), (0.0, 8.0, 0.0), 90.0),
    "dbg_back": ((0.0, 14.0, 70.0), (0.0, 14.0, 0.0), 90.0),
    "dbg_palm": ((0.0, 14.0, -70.0), (0.0, 14.0, 0.0), 90.0),
    "dbg_curl": ((46.0, 52.0, -60.0), (0.0, 10.0, -3.0), 90.0),
    "tq": ((44.0, 64.0, -54.0), (-1.0, 12.0, 0.0), 100.0),
}


def build_rig(kind, cam_pos, target):
    """kind 'studio': neutral three light rig attached to the camera.  kind 'candle': warm point from below + cold rim."""
    cp, tg = Vector(cam_pos), Vector(target)
    fwd = (tg - cp).normalized()
    right = fwd.cross(Vector((0, 0, 1)))
    if right.length < 1e-3:
        right = fwd.cross(Vector((0, 1, 0)))
    right.normalize()
    up = right.cross(fwd).normalized()
    if kind == "studio":
        dist = (tg - cp).length
        k = (dist / 100.0) ** 2
        add_light("key", "AREA", cp + right * (-0.45 * dist) + up * (0.5 * dist), tg, 60000.0 * k, (1.0, 0.97, 0.92), size=0.5 * dist)
        add_light("fill", "AREA", cp + right * (0.55 * dist) + up * (0.1 * dist), tg, 14000.0 * k, (0.9, 0.95, 1.0), size=0.6 * dist)
        add_light("rim", "AREA", tg - fwd * (0.55 * dist) + up * (0.35 * dist) + right * (0.3 * dist), tg, 50000.0 * k, (1.0, 1.0, 1.0), size=0.4 * dist)
    else:
        warm = srgb_to_lin(kelvin_rgb(2700.0))
        add_light("candle", "POINT", (6.0, 22.0, -42.0), (0.0, 8.0, -2.0), 140000.0, warm, radius=1.5)
        add_light("rimcold", "AREA", (-34.0, -30.0, 44.0), (0.0, 6.0, 0.0), 220000.0, srgb_to_lin((0.55, 0.70, 1.0)), size=30.0)


def render_view(V, F, view, rig, path, mat):
    sc = bpy.context.scene
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    ob = mesh_object("hand", V, F, mat)
    cam_pos, target, lens = VIEWS[view]
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cd.clip_end = 1000.0
    co = bpy.data.objects.new("cam", cd)
    co.location = cam_pos
    bpy.context.scene.collection.objects.link(co)
    aim(co, target)
    sc.camera = co
    build_rig(rig, cam_pos, target)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(ob)


ROWS = [  # (row, view, pose, rig, label)
    (1, "back", "straight", "studio", "back of hand"),
    (2, "palm", "straight", "studio", "palm side"),
    (3, "tq", "curl", "studio", "three-quarter, curled"),
    (4, "tq", "curl", "candle", "candle from below + cold rim"),
]
DEBUG_ROWS = {  # --rows 11 12 13: close-ups for iterating
    11: ("dbg_back", "straight", "studio", "dbg back"),
    12: ("dbg_palm", "straight", "studio", "dbg palm"),
    13: ("dbg_curl", "curl", "studio", "dbg curl"),
}


# ----------------------------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------------------------
def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    a = {"samples": 64, "res": 800, "only": ["v1", "v2"], "rows": [1, 2, 3, 4], "tiles": TILES, "sheet": True, "sheet_only": False, "debug": False}
    i = 0
    while i < len(argv):
        k = argv[i]
        if k == "--samples":
            a["samples"] = int(argv[i + 1]); i += 2
        elif k == "--res":
            a["res"] = int(argv[i + 1]); i += 2
        elif k == "--only":
            a["only"] = [argv[i + 1]]; i += 2
        elif k == "--tiles":
            a["tiles"] = os.path.abspath(argv[i + 1]); i += 2
        elif k == "--rows":
            i += 1
            a["rows"] = []
            while i < len(argv) and not argv[i].startswith("--"):
                a["rows"].append(int(argv[i])); i += 1
        elif k == "--no-sheet":
            a["sheet"] = False; i += 1
        elif k == "--sheet":
            a["sheet_only"] = True; i += 1
        elif k == "--debug":
            a["debug"] = True; i += 1
        else:
            i += 1
    return a


def main():
    args = parse_args()
    os.makedirs(args["tiles"], exist_ok=True)
    if args["sheet_only"]:
        return
    t0 = time.time()
    meta = {}
    res_x, res_y = args["res"], int(args["res"] * 0.9875)
    for key in args["only"]:
        reset_scene()
        np.random.seed(SEED)
        sc = setup_scene(res_x, res_y, args["samples"])
        mat = clay_material()
        if key == "v1":
            V, F, chains, info = build_v1()
        else:
            V, F, chains, info = build_v2()
        info["tris"] = faces_to_tris(F)
        info["bounds_min"] = V.min(0).round(2).tolist()
        info["bounds_max"] = V.max(0).round(2).tolist()
        meta[key] = info
        print("[%s] %s" % (key, info))
        for (row, view, pose, rig, label) in ROWS + [(k,) + v for k, v in DEBUG_ROWS.items()]:
            if row not in args["rows"]:
                continue
            Vp = pose_points(V, chains, POSES[pose])
            tp = os.path.join(args["tiles"], "%s_row%d.png" % (key, row))
            t1 = time.time()
            render_view(Vp, F, view, rig, tp, mat)
            print("  row %d %s: %.1fs" % (row, label, time.time() - t1))
    print("total %.1fs" % (time.time() - t0))
    mp = os.path.join(args["tiles"], "meta.json")
    old = json.load(open(mp)) if os.path.exists(mp) else {}
    old.update(meta)
    json.dump(old, open(mp, "w"), indent=1)
    if args["sheet"]:
        py = shutil.which("python") or shutil.which("python3")
        subprocess.run([py, os.path.abspath(__file__), "--sheet", "--tiles", args["tiles"]], check=True)


main()
