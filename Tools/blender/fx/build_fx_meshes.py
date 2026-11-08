"""build_fx_meshes.py -- Phase 15 (P15-3) cloth meshes and FX cards for THE LAST BELL (Blender 5.2, headless).

    blender.exe -b --factory-startup --python Tools/blender/fx/build_fx_meshes.py -- [--out SourceArt/FX] [--only NAME ...]

Writes one FBX per mesh (SourceArt/FX/<MeshName>.fbx) plus fx_meshes_report.json.  Plan: Docs/plans/P15_PARTICLES.md section 7.
Deterministic: every torn edge uses a fixed per-mesh seed (random.Random + kit_lib.fbm).

Conventions (same as the kit/props, see Tools/blender/kit/README.md):
  * 1 Blender unit = 1 cm, authoring space == Unreal space; export mirrors Y (kit_lib.export_piece_fbx, axis_forward='Y',
    axis_up='Z').  No collision (no UCX_).
  * Cloth: ONE two-sided sheet.  Pivot = top centre (x centre 0, top edge z = 0, hangs down -Z).  The sheet lies in XZ with its
    FRONT (normal) toward +Y = into the room (F0.10: the yaw of the placement turns local Y to the wall normal).  The baked fold
    is a 3 cm sine in Y.  The torn / ragged bottoms and the hole / side tear are GEOMETRY (no opacity).
  * UV0 as Unreal sees it: U 0..1 left to right, V = 0 at the pinned top edge increasing downward (V = -z / height, so the
    torn bottom stops short of 1).  Unreal flips V on FBX import, so the FBX stores v_blender = 1 - V_unreal.
  * Material slots: cloth MAT_Cloth; BoltCard MAT_Bolt; CurtainCard MAT_Curtain.
  * Cards: 100 x 100 cm quad in XZ, normal +Y.  BoltCard pivot top centre (z 0 .. -100, section 2.4 SkyBoltTransform /
    StrikeBoltTransform scale it by (width / 100, 1, length / 100)); CurtainCard pivot bottom centre (z 0 .. 100).
"""
import json
import math
import os
import random
import sys

import bpy
import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "kit")))
import kit_lib as K  # noqa: E402

PREFIX = "SM_LB_"
FOLD_CM = 3.0          # amplitude of the baked sine fold in Y

# name: dict(w, h, nx, ny, seed, kind)
CLOTH = {
    "Prop_ClothStrip_A":  dict(w=35.0,  h=220.0, nx=8,  ny=44, seed=1101, kind="strip_a",  taper=0.10),
    "Prop_ClothStrip_B":  dict(w=25.0,  h=160.0, nx=6,  ny=32, seed=1202, kind="strip_b",  taper=0.08),
    "Prop_ClothBanner_A": dict(w=110.0, h=240.0, nx=22, ny=48, seed=1303, kind="banner",   taper=0.0),
    "Prop_ClothSheet_A":  dict(w=170.0, h=140.0, nx=34, ny=28, seed=1404, kind="sheet",    taper=0.0),
}
CARDS = {
    "FX_BoltCard":    dict(pivot="top",    mat="MAT_Bolt"),
    "FX_CurtainCard": dict(pivot="bottom", mat="MAT_Curtain"),
}
MAT_COLOR = {"MAT_Cloth": (0.62, 0.55, 0.42, 1.0), "MAT_Bolt": (0.75, 0.82, 1.0, 1.0), "MAT_Curtain": (0.45, 0.52, 0.62, 1.0)}


# ----------------------------------------------------------------------------------------------
# tear profiles: depth t_i (cm, >= 0) removed from the bottom of column vertex i
# ----------------------------------------------------------------------------------------------
def tear_profile(spec):
    w, nx, seed, kind = spec['w'], spec['nx'], spec['seed'], spec['kind']
    rnd = random.Random(seed)
    xs = [-w / 2 + w * i / nx for i in range(nx + 1)]
    t = []
    for i, x in enumerate(xs):
        s = x / w + 0.5                                   # 0 left .. 1 right
        n = K.fbm(i * 0.37, 0.5, seed)
        if kind == "strip_a":                             # slanted tear, jagged teeth
            v = 4.0 + 24.0 * s + 14.0 * (n - 0.5) + (rnd.uniform(3.0, 11.0) if i % 2 else rnd.uniform(0.0, 3.0))
        elif kind == "strip_b":                           # opposite slant, ragged
            v = 3.0 + 16.0 * (1.0 - s) + 12.0 * (n - 0.5) + (rnd.uniform(2.0, 8.0) if i % 2 == 0 else rnd.uniform(0.0, 2.5))
        elif kind == "banner":                            # swallow-tail (centre notched up) torn into rags
            notch = 46.0 * (1.0 - abs(2.0 * s - 1.0))
            v = 3.0 + notch + 5.0 * (n - 0.5) + rnd.uniform(-1.5, 3.5) + (4.0 if i % 4 == 1 else 0.0)
        elif kind == "sheet":                             # ragged bottom, bottom-left corner torn away (45 x 55 cm, jagged)
            corner = max(0.0, 58.0 * (1.0 - (x + w / 2) / 46.0))
            v = 3.0 + 12.0 * K.fbm(i * 0.23, 3.1, seed) + rnd.uniform(0.0, 5.0) + corner
            if corner > 0:
                v += rnd.uniform(-3.0, 3.0)
        else:
            v = 0.0
        t.append(max(0.0, v))
    m = min(t)
    return [v - m for v in t]                             # one column always reaches the full height


# ----------------------------------------------------------------------------------------------
# cloth
# ----------------------------------------------------------------------------------------------
def fold_y(x, v, w):
    """3 cm sine fold in Y; grows toward the free end, zero at the top-centre pivot."""
    lam = max(w / 2.2, 28.0)
    return FOLD_CM * math.sin(2.0 * math.pi * x / lam + 1.3 * v) * (0.3 + 0.7 * v)


def make_cloth(name, spec):
    w, h, nx, ny = spec['w'], spec['h'], spec['nx'], spec['ny']
    cell = h / ny
    t = tear_profile(spec)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()

    def vert(i, z):
        x = -w / 2 + w * i / nx
        v = min(max(-z / h, 0.0), 1.0)
        x *= 1.0 - spec['taper'] * v * v                   # strips narrow toward the torn end
        return bm.verts.new((x, fold_y(x, v, w), z))

    chains = []
    for i in range(nx + 1):
        zb = -(h - t[i])                                  # exact bottom of this column
        ch = [vert(i, -j * cell) for j in range(ny + 1) if -j * cell >= zb + 0.4 * cell]
        ch.append(vert(i, zb))
        chains.append(ch)

    # per-vertex (U, V_unreal)
    uvmap = {}
    for i, ch in enumerate(chains):
        for vt in ch:
            uvmap[vt] = (i / nx, min(max(-vt.co.z / h, 0.0), 1.0))

    def add(*vs):
        f = bm.faces.new(vs)
        f.smooth = True
        for l in f.loops:
            u, vv = uvmap[l.vert]
            l[uvl].uv = (u, 1.0 - vv)                      # Unreal flips V on import: blender v = 1 - V_unreal
        return f

    for i in range(nx):
        L, R = chains[i], chains[i + 1]
        a = b = 0
        while a < len(L) - 1 or b < len(R) - 1:
            la = L[a + 1].co.z if a < len(L) - 1 else None
            rb = R[b + 1].co.z if b < len(R) - 1 else None
            if la is not None and rb is not None and abs(la - rb) < 0.5 * cell and abs(L[a].co.z - R[b].co.z) < 0.5 * cell:
                add(L[a], R[b], R[b + 1], L[a + 1])
                a += 1
                b += 1
            elif rb is None or (la is not None and la >= rb):
                add(L[a], R[b], L[a + 1])
                a += 1
            else:
                add(L[a], R[b], R[b + 1])
                b += 1

    notes = []
    if spec['kind'] == "strip_b":
        notes.append(cut_hole(bm, spec, uvl))
    if spec['kind'] == "banner":
        notes.append(side_tear(bm, spec, cell))
    bm.verts.ensure_lookup_table()
    for f in bm.faces:                                       # V follows the final vertex heights (the hole rim / tear moved some)
        for l in f.loops:
            vv = min(max(-l.vert.co.z / h, 0.0), 1.0)
            l[uvl].uv = (l[uvl].uv[0], 1.0 - vv)
    bm.normal_update()
    fix_orientation(bm)
    return bm, notes


def fix_orientation(bm):
    """Every face normal must point to +Y (front = into the room); a sheet is built consistently, so flip all or none."""
    bm.normal_update()
    n_pos = sum(1 for f in bm.faces if f.normal.y > 0)
    if n_pos < len(bm.faces) - n_pos:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.normal_update()
    assert all(f.normal.y > 0 for f in bm.faces), "mixed face orientation"


def cut_hole(bm, spec, uvl):
    """One hole: delete the faces whose centre is inside a seeded wobbly ellipse, then rough up the rim."""
    rnd = random.Random(spec['seed'] + 7)
    w, h = spec['w'], spec['h']
    cx, cz = -0.12 * w, -0.52 * h
    rx, rz = 0.20 * w, 10.5
    doomed = []
    for f in bm.faces:
        c = f.calc_center_median()
        ang = math.atan2(c.z - cz, c.x - cx)
        wob = 1.0 + 0.25 * math.sin(3 * ang + 0.7) + rnd.uniform(-0.08, 0.08)
        if ((c.x - cx) / (rx * wob)) ** 2 + ((c.z - cz) / (rz * wob)) ** 2 <= 1.0:
            doomed.append(f)
    outer = set(v for e in bm.edges if e.is_boundary for v in e.verts)
    rim_all = set(v for f in doomed for v in f.verts) - outer
    bmesh.ops.delete(bm, geom=doomed, context='FACES_ONLY')
    moved = 0
    for vt in rim_all:
        if vt.is_valid and vt.link_faces:
            vt.co.x += rnd.uniform(-0.9, 0.9)
            vt.co.z += rnd.uniform(-1.2, 1.2)
            moved += 1
    stray = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=stray, context='VERTS')
    return "hole: %d faces removed at (%.1f, %.1f), rim verts roughened %d" % (len(doomed), cx, cz, moved)


def side_tear(bm, spec, cell):
    """One side tear: split the edges along a row from the right edge inward, then open it into a tapering gap."""
    rnd = random.Random(spec['seed'] + 11)
    w, h, nx = spec['w'], spec['h'], spec['nx']
    row = int(round(0.52 * spec['ny']))
    zrow = -row * cell
    depth_cols = 7                                           # about 35 cm inward
    x_tip = w / 2 - depth_cols * (w / nx)
    path = [e for e in bm.edges
            if all(abs(v.co.z - zrow) < 1e-3 for v in e.verts) and min(v.co.x for v in e.verts) >= x_tip - 1e-3 and len(e.link_faces) == 2]
    assert len(path) == depth_cols, "side tear path has %d edges" % len(path)
    bmesh.ops.split_edges(bm, edges=path)
    bm.verts.ensure_lookup_table()
    gap_max = 6.5
    opening = []                                              # (vertex, upper/lower sign) found before anything moves
    for vt in bm.verts:
        if abs(vt.co.z - zrow) < 1e-3 and vt.co.x >= x_tip + 1e-3:
            cz = sum(f.calc_center_median().z for f in vt.link_faces) / max(len(vt.link_faces), 1)
            opening.append((vt, 1.0 if cz > zrow else -1.0))
    for vt in bm.verts:                                       # angle the tear: the band around it droops up to 9 cm toward the edge, smoothly
        if vt.co.x > x_tip + 1e-3:
            k = (vt.co.x - x_tip) / (w / 2 - x_tip)
            wgt = max(0.0, 1.0 - abs(vt.co.z - zrow) / 70.0) ** 2
            vt.co.z -= 9.0 * k * k * wgt
    n = 0
    for vt, sgn in opening:
        k = (vt.co.x - x_tip) / (w / 2 - x_tip)            # 0 at the tip .. 1 at the edge
        g = gap_max * (k ** 1.2) * (0.75 + 0.5 * rnd.random())
        vt.co.z += sgn * 0.5 * g
        vt.co.y += (-1.2 if sgn < 0 else 0.0) * k          # the lower flap hangs slightly behind
        n += 1
    return "side tear: %d vertices opened along row %d (z %.1f), %d cm inward, gap up to %.1f cm" % (n, row, zrow, depth_cols * w / nx, gap_max)


# ----------------------------------------------------------------------------------------------
# cards
# ----------------------------------------------------------------------------------------------
def make_card(name, spec):
    z0, z1 = (-100.0, 0.0) if spec['pivot'] == "top" else (0.0, 100.0)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    p = [bm.verts.new((-50.0, 0.0, z0)), bm.verts.new((50.0, 0.0, z0)), bm.verts.new((50.0, 0.0, z1)), bm.verts.new((-50.0, 0.0, z1))]
    f = bm.faces.new(p)
    f.smooth = True
    for l in f.loops:
        # Unreal V: 0 at the top edge (z1), 1 at the bottom (z0); blender v = 1 - V
        l[uvl].uv = ((l.vert.co.x + 50.0) / 100.0, (l.vert.co.z - z0) / 100.0)
    fix_orientation(bm)
    return bm, ["100 x 100 cm quad, pivot %s centre, normal +Y" % spec['pivot']]


# ----------------------------------------------------------------------------------------------
def get_mat(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.diffuse_color = MAT_COLOR[name]
        m.roughness = 0.9
    return m


def build_all(only=None):
    """name -> (bmesh, [notes], material name).  Pure geometry; nothing is written."""
    out = {}
    for nm, sp in CLOTH.items():
        if only and not any(o in nm for o in only):
            continue
        bm, notes = make_cloth(nm, sp)
        out[nm] = (bm, notes, "MAT_Cloth")
    for nm, sp in CARDS.items():
        if only and not any(o in nm for o in only):
            continue
        bm, notes = make_card(nm, sp)
        out[nm] = (bm, notes, sp['mat'])
    return out


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.join(ROOT, "SourceArt", "FX")
    only = []
    i = 0
    while i < len(argv):
        if argv[i] == "--out":
            out = os.path.abspath(argv[i + 1]); i += 2
        elif argv[i] == "--only":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                only.append(argv[i]); i += 1
        else:
            i += 1
    K.setup_scene_units()
    os.makedirs(out, exist_ok=True)
    report = {}
    for nm, (bm, notes, matname) in build_all(only).items():
        full = PREFIX + nm
        bm.verts.ensure_lookup_table()
        co = [v.co for v in bm.verts]
        mn = [min(c[k] for c in co) for k in range(3)]
        mx = [max(c[k] for c in co) for k in range(3)]
        tris = sum(len(f.verts) - 2 for f in bm.faces)
        K.export_piece_fbx(full, bm, [], os.path.join(out, full + ".fbx"), [get_mat(matname)])
        report[full] = dict(bounds_min=[round(v, 2) for v in mn], bounds_max=[round(v, 2) for v in mx],
                            tris=tris, verts=len(co), slot=matname, notes=notes)
        print("%-34s tris %4d verts %4d  bounds %s .. %s  %s" % (full, tris, len(co), [round(v, 1) for v in mn], [round(v, 1) for v in mx], "; ".join(notes)))
        bm.free()
    if not only:
        with open(os.path.join(out, "fx_meshes_report.json"), "w") as fh:
            json.dump(report, fh, indent=1)


if __name__ == "__main__":
    main()
