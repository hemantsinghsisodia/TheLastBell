"""p13_reweight.py -- P13-4c: reweight the Warden's robe and sleeves in Blender (headless), export the 3 LODs, and measure the wool stretch.

    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --factory-startup --python Tools/blender/warden/p13_reweight.py -- --mode reweight|measure|summary [options]

  --mode reweight   open SourceArt/Warden/V5_5/Warden_Rigged.blend (the project's copy of the owner's V5.5 master; NEVER saved over), apply rules 1-3 of
                    Docs/plans/P13_WARDEN_ANIMATION.md P13-4c to SK_Warden_LOD0/1/2, check that only vertex-group weights changed, save as
                    <out-root>/Warden_Rigged.blend, re-open that file and export the 3 LOD FBX to <out-root>/exports with the owner's export settings
                    (C:\\Hemant\\Prj\\Learning\\Warden\\output\\warden_art_v5_5\\scripts\\export.py, read-only: its LOD part is reproduced below).
      --out-root DIR     default SourceArt/Warden/V5_5w
      --leg-max F        L max, the largest share of a lower-robe vertex given to the legs (default 0.5)
      --smooth N         Laplacian passes over the sleeve region (default 2)
      --round3 1         also apply P13-4c round 3: (A) feet, (B) turn flaps, (C) seam feather (options: --boot-core M, --feather-radius M, --feather-passes N, --flap-blend F, --band-passes N, --pin-leg SHARE)
      --tag NAME         key under which the numbers are stored in the report (default "reweight")
      --sleeve-near F    distance to the arm bones that also counts as sleeve (default 0.25 m)
  --mode measure    stretch metric: import --mesh (a mesh FBX) with each review clip (SourceArt/Warden/P13_review/AN_Warden_<Name>.fbx, the way
                    the contact sheet does) and compute, over every frame, deformed edge length / rest edge length on the wool edges.
      --mesh FBX         mesh to measure
      --tag NAME         key in the report ("before" / "after")
      --clips A,B,..     default MutantWalking,MutantRun,CrouchedWalking,ZombieAttack
  --report FILE     JSON report that both modes merge their section into (default Docs/ArtTest/warden/p13_reweight.json)

Coordinates of the rules are the master's frame in metres (the figure faces -Y, +x is the Warden's left). Only vertex-group weights change; weights are
normalised per vertex with at most 4 influences (Unreal's default; the master already had at most 4).
"""
import hashlib
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SRC_BLEND = os.path.join(ROOT, "SourceArt", "Warden", "V5_5", "Warden_Rigged.blend")
REVIEW = os.path.join(ROOT, "SourceArt", "Warden", "P13_review")
WOOL = "M_Warden_Wool"
LODS = ["SK_Warden_LOD0", "SK_Warden_LOD1", "SK_Warden_LOD2"]


def log(*a):
    print("RW| " + " ".join(str(x) for x in a), flush=True)


def parse():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = {"mode": "reweight", "out_root": os.path.join(ROOT, "SourceArt", "Warden", "V5_5w"), "leg_max": 0.5, "smooth": 2, "tag": None, "mesh": None,
         "clips": "MutantWalking,MutantRun,CrouchedWalking,ZombieAttack", "report": os.path.join(ROOT, "Docs", "ArtTest", "warden", "p13_reweight.json"),
         "sleeve_near": 0.25, "round3": "0", "boot_core": 0.0, "feather_radius": 0.10, "feather_passes": 60, "flap_blend": 0.30, "band_passes": 2, "pin_leg": 0.0}
    i = 0
    while i < len(a):
        k = a[i].lstrip("-").replace("-", "_")
        o[k] = a[i + 1]
        i += 2
    o["leg_max"], o["smooth"], o["sleeve_near"] = float(o["leg_max"]), int(o["smooth"]), float(o["sleeve_near"])
    o["round3"] = o["round3"] == "1"
    o["boot_core"], o["feather_radius"], o["flap_blend"] = float(o["boot_core"]), float(o["feather_radius"]), float(o["flap_blend"])
    o["feather_passes"], o["band_passes"], o["pin_leg"] = int(o["feather_passes"]), int(o["band_passes"]), float(o["pin_leg"])
    return o


def update_report(path, key, value):
    data = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    data[key] = value
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1)


# ------------------------------------------------------------------------------------------------ mesh data helpers
def read_mesh(ob):
    me = ob.data
    n = len(me.vertices)
    co = np.zeros(n * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    names = [g.name for g in ob.vertex_groups]
    W = np.zeros((n, len(names)))
    for v in me.vertices:
        for g in v.groups:
            W[v.index, g.group] = g.weight
    npoly = len(me.polygons)
    mi = np.zeros(npoly, int)
    me.polygons.foreach_get("material_index", mi)
    lv = np.zeros(len(me.loops), int)
    me.loops.foreach_get("vertex_index", lv)
    tot = np.zeros(npoly, int)
    me.polygons.foreach_get("loop_total", tot)
    slot_names = [m.name.split(".")[0] if m else None for m in me.materials]
    wool_slot = slot_names.index(WOOL)
    wool = np.zeros(n, bool)
    wool[lv[np.repeat(mi, tot) == wool_slot]] = True
    ed = np.zeros(len(me.edges) * 2, int)
    me.edges.foreach_get("vertices", ed)
    return co, W, wool, names, ed.reshape(-1, 2)


def seg_dist(P, a, b):
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(ab @ ab, 1e-12), 0.0, 1.0)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def prune_normalise(Wrows, max_inf=4):
    """Keep the max_inf largest weights per row, normalise the row to 1. Returns (new rows, lost mass per row)."""
    out = np.zeros_like(Wrows)
    idx = np.argsort(-Wrows, axis=1)[:, :max_inf]
    r = np.arange(Wrows.shape[0])[:, None]
    out[r, idx] = Wrows[r, idx]
    s = out.sum(1)
    lost = 1.0 - s / np.maximum(Wrows.sum(1), 1e-12)
    out = out / np.maximum(s, 1e-12)[:, None]
    return out, lost


def leg_blend(Wrows, zl, xl, gi, leg_max):
    """Rule 2: scale the rows by 1 - L(z) and give the legs L(z), split left/right by x and thigh/calf by z. Returns (rows, L)."""
    L = leg_max * smoothstep(0.0, 1.0, (1.57 - zl) / (1.57 - 0.60))
    f = np.clip(0.5 + xl / 0.60, 0.1, 0.9)
    c = smoothstep(0.0, 1.0, (0.84 - zl) / (0.84 - 0.40))
    Wl = Wrows * (1.0 - L)[:, None]
    for side, share in (("l", f), ("r", 1.0 - f)):
        Wl[:, gi["thigh_" + side]] += L * share * (1.0 - c)
        Wl[:, gi["calf_" + side]] += L * share * c
    return Wl, L


def smooth_rows(W, region, ed, passes, nbmask):
    """Laplacian passes: each region vertex becomes 0.5 * itself + 0.5 * the mean of its edge neighbours that are in nbmask (Jacobi, in place)."""
    n = len(W)
    a, b = ed[:, 0], ed[:, 1]
    m1, m2 = region[a] & nbmask[b], region[b] & nbmask[a]
    src = np.concatenate([a[m1], b[m2]])
    nbr = np.concatenate([b[m1], a[m2]])
    deg = np.bincount(src, minlength=n).astype(float)
    ri = np.where(region & (deg > 0))[0]
    if not len(ri):
        return W
    cols = np.where((np.abs(W[ri]).sum(0) > 0) | (np.abs(W[np.unique(nbr)]).sum(0) > 0))[0]
    for _ in range(passes):
        new = {}
        for g in cols:
            mean = np.bincount(src, weights=W[nbr, g], minlength=n)[ri] / deg[ri]
            new[g] = 0.5 * W[ri, g] + 0.5 * mean
        for g, v in new.items():
            W[ri, g] = v
    return W


def read_leather(ob):
    me = ob.data
    mi = np.zeros(len(me.polygons), int)
    me.polygons.foreach_get("material_index", mi)
    lv = np.zeros(len(me.loops), int)
    me.loops.foreach_get("vertex_index", lv)
    tot = np.zeros(len(me.polygons), int)
    me.polygons.foreach_get("loop_total", tot)
    slot = [m.name.split(".")[0] if m else None for m in me.materials].index("M_Warden_Leather")
    leather = np.zeros(len(me.vertices), bool)
    leather[lv[np.repeat(mi, tot) == slot]] = True
    return leather


def apply_round3(co, W0, W1, wool, leather, names, ed, bones, sleeve, lower, p, e_ref):
    """P13-4c round 3 on top of the rules-1-3 result W1: (A) feet, (B) turn flaps, (C) seam feather. W0 is the master. Returns (W3, stats)."""
    from mathutils import Vector, kdtree
    gi = {nm: i for i, nm in enumerate(names)}
    n = len(co)
    x, z = co[:, 0], co[:, 2]
    robe = [gi[nm] for nm in names if nm.startswith("robe_")]
    foot = [gi[nm] for nm in names if nm.startswith(("foot_", "ball_"))]
    arm_groups = [gi[nm] for nm in names if nm.startswith(("upperarm_", "lowerarm_", "hand_"))]
    has_arm = W0[:, arm_groups].sum(1) > 0.0
    W3 = W1.copy()
    stats = {}
    hem = wool | leather
    robe_share0 = W0[:, robe].sum(1)

    # ---- (A) feet: z < 0.30 wool and leather vertices with > 50 % on foot_* / ball_* take their nearest robe vertices' weights + the rule 2 blend
    dfoot = np.full(n, 9.0)
    for sd in ("l", "r"):
        for b in ("foot", "ball"):
            dfoot = np.minimum(dfoot, seg_dist(co, *bones["%s_%s" % (b, sd)]))
    legfam = [gi[nm] for nm in names if nm.startswith(("thigh_", "calf_", "foot_", "ball_"))]
    if p["pin_leg"] > 0:      # variation: any hem vertex with at least this share on thigh/calf/foot/ball (the strict rule misses vertices with exactly 0.5 foot + 0.5 calf)
        pin_test = W0[:, legfam].sum(1) >= p["pin_leg"]
    else:
        pin_test = W0[:, foot].sum(1) > 0.5
    pinned = hem & (z < 0.30) & pin_test & (dfoot > p["boot_core"])
    ref = hem & (z < 1.57) & ~sleeve & (robe_share0 > 0.5) & ~pinned
    ri = np.where(ref)[0]
    kd = kdtree.KDTree(len(ri))
    for k, v in enumerate(ri):
        kd.insert(Vector(co[v]), k)
    kd.balance()
    pi = np.where(pinned)[0]
    Wp = np.zeros((len(pi), W0.shape[1]))
    for k, v in enumerate(pi):
        hits = kd.find_n(Vector(co[v]), 4)
        wts = np.array([1.0 / (d + 1e-3) for (_, _, d) in hits])
        wts /= wts.sum()
        for (_, idx, _), w in zip(hits, wts):
            row = W0[ri[idx]][robe]
            Wp[k, robe] += w * row / max(row.sum(), 1e-9)
    Wp, _ = leg_blend(Wp, z[pi], x[pi], gi, p["leg_max"])
    Wp, lost_a = prune_normalise(Wp)
    W3[pi] = Wp
    stats["A_pinned_vertices"] = int(len(pi))
    stats["A_pinned_wool"] = int((pinned & wool).sum())
    stats["A_pinned_leather"] = int((pinned & leather).sum())
    stats["A_boot_core_excluded_m"] = p["boot_core"]
    stats["A_pin_rule"] = ("thigh/calf/foot/ball share >= %.2f" % p["pin_leg"]) if p["pin_leg"] > 0 else "foot/ball share > 0.5"
    stats["A_reference_vertices"] = int(len(ri))

    # ---- (B) turn flaps: the old robe-weighted sleeve flaps below the armpit (z < 1.57) return to the master's robe weights (+ the rule 2 blend, like the rest
    # of the lower robe), then 30 % towards spine_03 above z 1.2 or pelvis below
    flap = sleeve & ~has_arm & (z < 1.57)
    fi = np.where(flap)[0]
    Wf, _ = leg_blend(W0[fi], z[fi], x[fi], gi, p["leg_max"])
    tgt = np.where(z[fi] > 1.2, gi["spine_03"], gi["pelvis"])
    Wf = Wf * (1.0 - p["flap_blend"])
    Wf[np.arange(len(fi)), tgt] += p["flap_blend"]
    Wf, lost_b = prune_normalise(Wf)
    W3[fi] = Wf
    stats["B_flap_vertices"] = int(len(fi))

    # ---- band smoothing (A): passes over wool/leather robe vertices at z < 0.4 (the pinned ones included; a boot core kept out of A stays out)
    band = hem & (z < 0.4) & (pinned | (lower & wool) | (leather & (robe_share0 > 0.5)))
    smooth_rows(W3, band, ed, p["band_passes"], band)
    stats["A_band_vertices"] = int(band.sum())

    # ---- (C) feather: wool vertices within feather_radius of a seam are smoothed (neighbours = all wool), so the weights ramp across the seam.
    # seam = a wool edge with at least one changed end whose two weight vectors differ by more than 0.3 (L1).
    changed = np.any(np.abs(W3 - W0) > 1e-9, axis=1)
    wl = wool[ed[:, 0]] & wool[ed[:, 1]] & (changed[ed[:, 0]] | changed[ed[:, 1]])
    d1 = np.abs(W3[ed[:, 0]] - W3[ed[:, 1]]).sum(1)
    seam = wl & (d1 > 0.3)
    sv = np.unique(ed[seam].ravel())
    region = np.zeros(n, bool)
    if len(sv):
        kd2 = kdtree.KDTree(len(sv))
        for k, v in enumerate(sv):
            kd2.insert(Vector(co[v]), k)
        kd2.balance()
        for v in np.where(wool)[0]:
            if kd2.find_n(Vector(co[v]), 1)[0][2] <= p["feather_radius"]:
                region[v] = True
    passes = max(4, int(round(p["feather_passes"] * (e_ref / p["e_this"]) ** 2)))
    smooth_rows(W3, region, ed, passes, wool)
    stats.update({"C_seam_edges": int(seam.sum()), "C_seam_vertices": int(len(sv)), "C_feather_region_vertices": int(region.sum()), "C_feather_passes": passes,
                  "C_feather_radius_m": p["feather_radius"]})

    # ---- everything that moved in round 3: prune to 4, normalise
    moved = np.any(np.abs(W3 - W1) > 1e-12, axis=1)
    mi = np.where(moved)[0]
    Wm, lost = prune_normalise(W3[mi])
    W3[mi] = Wm
    stats["round3_moved_vertices"] = int(len(mi))
    stats["round3_pruned_mass_mean"] = float(lost.mean()) if len(mi) else 0.0
    stats["round3_pruned_mass_max"] = float(lost.max()) if len(mi) else 0.0
    return W3, stats


def apply_rules(co, W, wool, names, ed, bones, p):
    """Return (W2, sleeve_mask, lower_mask, stats). bones: name -> (head, tail) numpy arrays in the master's frame."""
    gi = {nm: i for i, nm in enumerate(names)}
    n = len(co)
    x, z = co[:, 0], co[:, 2]
    arm_groups = [gi[nm] for nm in names if nm.startswith(("upperarm_", "lowerarm_", "hand_"))]
    robe_groups = [gi[nm] for nm in names if nm.startswith("robe_")]
    has_arm = W[:, arm_groups].sum(1) > 0.0
    near = np.zeros(n, bool)
    for s in ("l", "r"):
        for b in ("upperarm", "lowerarm", "hand"):
            h, t = bones["%s_%s" % (b, s)]
            near |= seg_dist(co, h, t) <= p["sleeve_near"]
    sleeve = wool & (has_arm | near) & (z > 1.0) & (z < 2.3) & (np.abs(x) > 0.25)
    lower = wool & (z < 1.57) & ~sleeve
    stats = {"wool_vertices": int(wool.sum()), "sleeve_vertices": int(sleeve.sum()), "sleeve_by_arm_weight_only": int((wool & has_arm & (z > 1.0) & (z < 2.3) & (np.abs(x) > 0.25)).sum()),
             "lower_robe_vertices": int(lower.sum())}
    W2 = W.copy()

    # ---- rule 1: sleeves
    si = np.where(sleeve)[0]
    Wsl = np.zeros((len(si), W.shape[1]))
    for side, sign in (("l", 1.0), ("r", -1.0)):
        rows = np.where(np.sign(x[si]) == sign)[0]
        if not len(rows):
            continue
        P = co[si[rows]]
        chain = ["clavicle", "upperarm", "lowerarm", "hand"]
        d = np.stack([seg_dist(P, *bones["%s_%s" % (b, side)]) for b in chain], axis=1)
        w = 1.0 / (d * d + 1e-4)
        keep = np.argsort(-w, axis=1)[:, :2]
        wk = np.zeros_like(w)
        r = np.arange(len(rows))[:, None]
        wk[r, keep] = w[r, keep]
        wk /= wk.sum(1, keepdims=True)
        seam = 1.0 - smoothstep(0.25, 0.45, np.abs(x[si[rows]]))
        for k, b in enumerate(chain):
            Wsl[rows, gi["%s_%s" % (b, side)]] = wk[:, k] * (1.0 - seam)
        Wsl[rows, gi["spine_03"]] = seam
    # two (or N) Laplacian passes over the sleeve region only
    pos = -np.ones(n, int)
    pos[si] = np.arange(len(si))
    both = sleeve[ed[:, 0]] & sleeve[ed[:, 1]]
    ea, eb = pos[ed[both, 0]], pos[ed[both, 1]]
    deg = np.zeros(len(si))
    np.add.at(deg, ea, 1.0)
    np.add.at(deg, eb, 1.0)
    for _ in range(p["smooth"]):
        acc = np.zeros_like(Wsl)
        np.add.at(acc, ea, Wsl[eb])
        np.add.at(acc, eb, Wsl[ea])
        mean = acc / np.maximum(deg, 1.0)[:, None]
        Wsl = np.where(deg[:, None] > 0, 0.5 * Wsl + 0.5 * mean, Wsl)
    Wsl_p, lost_s = prune_normalise(Wsl)
    W2[si] = Wsl_p
    stats["sleeve_pruned_mass_mean"] = float(lost_s.mean()) if len(si) else 0.0
    stats["sleeve_pruned_mass_max"] = float(lost_s.max()) if len(si) else 0.0

    # ---- rule 2: lower robe
    li = np.where(lower)[0]
    zl, xl = z[li], x[li]
    Wl, L = leg_blend(W[li], zl, xl, gi, p["leg_max"])    # every existing weight scaled by 1 - L, so the legs get exactly L before pruning (the plan says "robe weights"; the other weights are tiny there)
    Wl_p, lost_l = prune_normalise(Wl)
    W2[li] = Wl_p
    leg_cols = [gi[nm] for nm in names if nm.startswith(("thigh_", "calf_"))]
    stats["lower_pruned_mass_mean"] = float(lost_l.mean()) if len(li) else 0.0
    stats["lower_pruned_mass_max"] = float(lost_l.max()) if len(li) else 0.0
    stats["lower_leg_share_designed_mean"] = float(L.mean()) if len(li) else 0.0
    stats["lower_leg_share_after_mean"] = float(Wl_p[:, leg_cols].sum(1).mean()) if len(li) else 0.0
    stats["lower_leg_share_before_mean"] = float(W[li][:, leg_cols].sum(1).mean()) if len(li) else 0.0
    stats["lower_robe_share_before_mean"] = float(W[li][:, robe_groups].sum(1).mean()) if len(li) else 0.0
    stats["lower_robe_share_after_mean"] = float(Wl_p[:, robe_groups].sum(1).mean()) if len(li) else 0.0
    stats["sleeve_arm_share_after_mean"] = float(Wsl_p[:, arm_groups].sum(1).mean()) if len(si) else 0.0
    stats["sleeve_robe_share_before_mean"] = float(W[si][:, robe_groups].sum(1).mean()) if len(si) else 0.0
    stats["sleeve_robe_share_after_mean"] = float(Wsl_p[:, robe_groups].sum(1).mean()) if len(si) else 0.0
    return W2, sleeve, lower, stats


def write_weights(ob, W_old, W_new, changed):
    """Replace the vertex-group weights of the changed vertices only."""
    vgs = ob.vertex_groups
    ci = np.where(changed)[0]
    # (a membership with weight exactly 0 exists in some files, so clear whatever memberships the vertex has)
    for v in ci:
        vert = ob.data.vertices[int(v)]
        for ge in list(vert.groups):
            vgs[ge.group].remove([int(v)])
    for v in ci:
        for g in np.where(W_new[v] > 0.0)[0]:
            vgs[int(g)].add([int(v)], float(W_new[v, g]), "REPLACE")


def verify_weights(ob, W_new, changed):
    co, W_now, _, names, _ = read_mesh(ob)
    ok_changed = np.allclose(W_now[changed], W_new[changed], atol=1e-6)
    return ok_changed, W_now


# ------------------------------------------------------------------------------------------------ before/after identity check
def digest(a):
    return hashlib.md5(np.ascontiguousarray(a).tobytes()).hexdigest()


def snapshot():
    snap = {"objects": sorted(o.name for o in bpy.data.objects)}
    for nm in LODS:
        ob = bpy.data.objects[nm]
        me = ob.data
        n = len(me.vertices)
        co = np.zeros(n * 3)
        me.vertices.foreach_get("co", co)
        pv = np.zeros(len(me.loops), int)
        me.loops.foreach_get("vertex_index", pv)
        mi = np.zeros(len(me.polygons), int)
        me.polygons.foreach_get("material_index", mi)
        uvs = {}
        for uv in me.uv_layers:
            a = np.zeros(len(me.loops) * 2)
            uv.data.foreach_get("uv", a)
            uvs[uv.name] = digest(a)
        snap[nm] = {"verts": n, "polys": len(me.polygons), "edges": len(me.edges), "co": digest(co), "loop_verts": digest(pv), "mat_index": digest(mi),
                    "uv": uvs, "slots": [m.name if m else None for m in me.materials], "groups": [g.name for g in ob.vertex_groups],
                    "parent": ob.parent.name if ob.parent else None, "modifiers": [(m.type, m.object.name if getattr(m, "object", None) else None) for m in ob.modifiers],
                    "matrix": digest(np.array([list(r) for r in ob.matrix_world]))}
    arm = bpy.data.objects["Warden_Rig"]
    bl = []
    for b in arm.data.bones:
        bl.append((b.name, b.parent.name if b.parent else None, [round(v, 6) for v in b.head_local], [round(v, 6) for v in b.tail_local],
                   [round(v, 6) for row in b.matrix_local for v in row]))
    snap["armature"] = {"bones": hashlib.md5(json.dumps(bl).encode()).hexdigest(), "count": len(bl),
                        "matrix": digest(np.array([list(r) for r in arm.matrix_world])), "actions": sorted(a.name for a in bpy.data.actions)}
    return snap


def compare(a, b):
    diffs = []
    for k in a:
        if a[k] != b.get(k):
            if isinstance(a[k], dict):
                for kk in a[k]:
                    if a[k][kk] != b[k].get(kk):
                        diffs.append("%s.%s: %r != %r" % (k, kk, a[k][kk], b[k].get(kk)))
            else:
                diffs.append(k)
    return diffs


# ------------------------------------------------------------------------------------------------ mode: reweight
def mode_reweight(o):
    tag = o["tag"] or "reweight"
    md5_before = hashlib.md5(open(SRC_BLEND, "rb").read()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=SRC_BLEND)
    snap_before = snapshot()
    arm = bpy.data.objects["Warden_Rig"]
    assert np.allclose(np.array([list(r) for r in arm.matrix_world]), np.eye(4)), "armature object is not at identity: the rules assume the master's frame"
    bones = {b.name: (np.array(b.head_local), np.array(b.tail_local)) for b in arm.data.bones}
    p = {"leg_max": o["leg_max"], "smooth": o["smooth"], "sleeve_near": o["sleeve_near"]}
    if o["round3"]:
        p.update({k: o[k] for k in ("boot_core", "feather_radius", "feather_passes", "flap_blend", "band_passes", "pin_leg")})
    e_ref = None
    report = {"params": p, "source": SRC_BLEND, "source_md5": md5_before, "lods": {}}
    for nm in LODS:
        ob = bpy.data.objects[nm]
        assert ob.matrix_world == Matrix.Identity(4)
        co, W, wool, names, ed = read_mesh(ob)
        nz = (W > 0).sum(1)
        W2, sleeve, lower, stats = apply_rules(co, W, wool, names, ed, bones, p)
        if o["round3"]:
            leather = read_leather(ob)
            ew = ed[wool[ed[:, 0]] & wool[ed[:, 1]]]
            elen = float(np.linalg.norm(co[ew[:, 0]] - co[ew[:, 1]], axis=1).mean())
            e_ref = e_ref or elen
            p["e_this"] = elen
            W2, st3 = apply_round3(co, W, W2, wool, leather, names, ed, bones, sleeve, lower, p, e_ref)
            stats.update(st3)
            stats["mean_wool_edge_m"] = elen
        changed = np.any(W2 != W, axis=1)
        # never touch what the rules leave alone: the rows outside `changed` are identical by construction; assert
        assert np.array_equal(W2[~changed], W[~changed])
        write_weights(ob, W, W2, changed)
        ok, W_now = verify_weights(ob, W2, changed)
        assert ok, "weights read back differ from the intended ones"
        assert np.array_equal(W_now[~changed], W[~changed]), "unchanged vertices were modified"
        nz2 = (W_now > 0).sum(1)
        sums = W_now.sum(1)
        stats.update({"vertices": len(co), "changed_vertices": int(changed.sum()), "max_influences_before": int(nz.max()), "max_influences_after": int(nz2.max()),
                      "weight_sum_min_after": float(sums.min()), "weight_sum_max_after": float(sums.max())})
        assert nz2.max() <= 4 and abs(sums.min() - 1) < 1e-4 and abs(sums.max() - 1) < 1e-4, stats
        report["lods"][nm] = stats
        log(nm, json.dumps(stats))
    # identity check against the source, in the same session (in-memory)
    snap_after = snapshot()
    diffs = compare(snap_before, snap_after)
    assert not diffs, diffs
    os.makedirs(o["out_root"], exist_ok=True)
    out_blend = os.path.join(o["out_root"], "Warden_Rigged.blend")
    bpy.context.preferences.filepaths.save_version = 0      # no .blend1 backup next to the output
    bpy.ops.wm.save_as_mainfile(filepath=out_blend, copy=False, compress=True)
    # re-open both files from disk and compare them (what was saved, not what was in memory)
    bpy.ops.wm.open_mainfile(filepath=SRC_BLEND)
    s_src = snapshot()
    bpy.ops.wm.open_mainfile(filepath=out_blend)
    s_new = snapshot()
    diffs = compare(s_src, s_new)
    report["identity_check"] = {"verts_per_lod": {k: s_new[k]["verts"] for k in LODS}, "differences": diffs,
                                "compared": "vertex positions (md5 of all coordinates), polygon loop vertex indices, material indices, UVs, material slots, vertex-group names and order, parent, modifiers, object matrices, armature bones (name/parent/head/tail/matrix) and actions"}
    assert not diffs, diffs
    log("identity check OK", json.dumps(report["identity_check"]))
    # the new file: export from it (the export mutates the scene, so it is never saved)
    export_lods(o["out_root"], report)
    md5_after = hashlib.md5(open(SRC_BLEND, "rb").read()).hexdigest()
    report["source_md5_after"] = md5_after
    report["source_unchanged"] = md5_after == md5_before
    assert md5_after == md5_before
    report["new_blend_bytes"] = os.path.getsize(out_blend)
    update_report(o["report"], tag, report)
    log("REWEIGHT_DONE", tag)


def export_lods(out_root, report):
    """The LOD part of the owner's scripts/export.py, unchanged except that it reads the open file: centimetres, FBX_SCALE_UNITS, -Y forward."""
    scene = bpy.context.scene
    arm = bpy.data.objects["Warden_Rig"]
    if arm.animation_data:
        arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.scale = (1, 1, 1)
    scene.frame_set(1)
    for i in range(3):
        obj = bpy.data.objects["SK_Warden_LOD%d" % i]
        for vertex in obj.data.vertices:
            vertex.co *= 100
        obj.data.update()
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for bone in arm.data.edit_bones:
        bone.head *= 100
        bone.tail *= 100
    bpy.ops.object.mode_set(mode="OBJECT")
    scene.unit_settings.scale_length = .01
    scene.frame_set(1)
    bpy.context.view_layer.update()
    arm.name = "Armature"
    settings = dict(use_selection=True, global_scale=1, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Y", axis_up="Z",
                    bake_space_transform=False, use_mesh_modifiers=True, mesh_smooth_type="FACE", use_tspace=True, add_leaf_bones=False,
                    use_armature_deform_only=True, armature_nodetype="NULL", path_mode="RELATIVE", embed_textures=False)
    exp = os.path.join(out_root, "exports")
    os.makedirs(exp, exist_ok=True)
    files = {}
    for i in range(3):
        bpy.ops.object.select_all(action="DESELECT")
        arm.select_set(True)
        obj = bpy.data.objects["SK_Warden_LOD%d" % i]
        obj.hide_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        fn = os.path.join(exp, "SK_Warden_LOD%d.fbx" % i)
        bpy.ops.export_scene.fbx(filepath=fn, object_types={"ARMATURE", "MESH"}, bake_anim=False, **settings)
        files[os.path.basename(fn)] = os.path.getsize(fn)
        log("exported", fn, files[os.path.basename(fn)])
    report["exports"] = files


# ------------------------------------------------------------------------------------------------ mode: measure
def mode_measure(o):
    tag = o["tag"] or "measure"
    mesh_fbx = o["mesh"]
    assert mesh_fbx and os.path.isfile(mesh_fbx), mesh_fbx
    res = {"mesh": mesh_fbx, "mesh_md5": hashlib.md5(open(mesh_fbx, "rb").read()).hexdigest(), "clips": {}}
    for clip in o["clips"].split(","):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = bpy.context.scene
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=mesh_fbx)
        new = set(bpy.data.objects) - before
        mesh = next(x for x in new if x.type == "MESH")
        old_arm = next(x for x in new if x.type == "ARMATURE")
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=os.path.join(REVIEW, "AN_Warden_%s.fbx" % clip))
        arm = next(x for x in set(bpy.data.objects) - before if x.type == "ARMATURE")
        mesh.parent = None
        mesh.parent = arm
        mesh.matrix_parent_inverse = Matrix.Identity(4)
        for m in mesh.modifiers:
            if m.type == "ARMATURE":
                m.object = arm
        bpy.data.objects.remove(old_arm, do_unlink=True)
        me = mesh.data
        n = len(me.vertices)
        rest = np.zeros(n * 3)
        me.vertices.foreach_get("co", rest)
        rest = rest.reshape(-1, 3)
        slot_names = [m.name.split(".")[0] if m else None for m in me.materials]
        wool_slot = slot_names.index(WOOL)
        mi = np.zeros(len(me.polygons), int)
        me.polygons.foreach_get("material_index", mi)
        tot = np.zeros(len(me.polygons), int)
        me.polygons.foreach_get("loop_total", tot)
        ls = np.zeros(len(me.polygons), int)
        me.polygons.foreach_get("loop_start", ls)
        loop_edge = np.zeros(len(me.loops), int)
        me.loops.foreach_get("edge_index", loop_edge)
        wool_poly = mi == wool_slot
        wool_loops = np.repeat(wool_poly, tot)
        eidx = np.unique(loop_edge[wool_loops])
        ed = np.zeros(len(me.edges) * 2, int)
        me.edges.foreach_get("vertices", ed)
        ed = ed.reshape(-1, 2)[eidx]
        rl = np.linalg.norm(rest[ed[:, 0]] - rest[ed[:, 1]], axis=1)
        ok = rl > 1e-9
        ed, rl = ed[ok], rl[ok]
        zmax = rest[:, 2].max()
        zm = (rest[ed[:, 0], 2] + rest[ed[:, 1], 2]) * 0.5 * (2.9 / zmax)     # edge mid height, normalised to the 2.9 m master
        bands = {"hem_z<0.6": zm < 0.6, "robe_0.6-1.57": (zm >= 0.6) & (zm < 1.57), "upper_z>=1.57": zm >= 1.57}
        act = arm.animation_data.action
        f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
        worst = {"ratio": 0.0}
        mx_frame, frac_frame, union = [], [], np.zeros(len(ed), bool)
        band_max = {k: 0.0 for k in bands}
        band_frac = {k: 0.0 for k in bands}
        all_ratio_max = np.zeros(len(ed))
        buf = np.zeros(n * 3)
        for fr in range(f0, f1 + 1):
            sc.frame_set(fr)
            dg = bpy.context.evaluated_depsgraph_get()
            ev = mesh.evaluated_get(dg)
            em = ev.to_mesh()
            em.vertices.foreach_get("co", buf)
            ev.to_mesh_clear()
            P = buf.reshape(-1, 3)
            r = np.linalg.norm(P[ed[:, 0]] - P[ed[:, 1]], axis=1) / rl
            all_ratio_max = np.maximum(all_ratio_max, r)
            m = float(r.max())
            mx_frame.append(m)
            frac_frame.append(float((r > 1.5).mean()))
            union |= r > 1.5
            for k, sel in bands.items():
                band_max[k] = max(band_max[k], float(r[sel].max()))
                band_frac[k] = max(band_frac[k], float((r[sel] > 1.5).mean()))
            if m > worst["ratio"]:
                j = int(r.argmax())
                worst = {"ratio": m, "frame": fr, "rest_length_cm": float(rl[j]), "mid_rest_xyz": [float(v) for v in (rest[ed[j, 0]] + rest[ed[j, 1]]) * 0.5],
                         "mid_height_m": float(zm[j])}
        res["clips"][clip] = {"frames": f1 - f0 + 1, "wool_edges": int(len(ed)), "vertices": n, "max_ratio": float(max(mx_frame)),
                              "worst_frame_share_gt_1.5": float(max(frac_frame)), "union_share_gt_1.5": float(union.mean()),
                              "edges_ever_gt_1.5": int(union.sum()), "p99.9_of_per_edge_max": float(np.percentile(all_ratio_max, 99.9)),
                              "p99_of_per_edge_max": float(np.percentile(all_ratio_max, 99)), "band_max_ratio": band_max, "band_worst_frame_share_gt_1.5": band_frac,
                              "worst": worst}
        log("measured", tag, clip, json.dumps(res["clips"][clip]))
    cl = res["clips"].values()
    res["overall"] = {"max_ratio": max(c["max_ratio"] for c in cl), "worst_frame_share_gt_1.5": max(c["worst_frame_share_gt_1.5"] for c in cl),
                      "union_share_gt_1.5": max(c["union_share_gt_1.5"] for c in cl)}
    res["pass"] = bool(res["overall"]["max_ratio"] <= 1.8 and res["overall"]["worst_frame_share_gt_1.5"] < 0.005)
    res["pass_strict_union"] = bool(res["overall"]["max_ratio"] <= 1.8 and res["overall"]["union_share_gt_1.5"] < 0.005)
    update_report(o["report"], tag, res)
    log("MEASURE_DONE", tag, json.dumps(res["overall"]), "pass", res["pass"], "pass_strict_union", res["pass_strict_union"])


def mode_summary(o):
    """Collect the per-clip numbers of every measured tag into one table (report key "summary")."""
    with open(o["report"], encoding="utf-8") as fh:
        data = json.load(fh)
    tags = [k for k in data if k == "before" or k.startswith("after_")]
    table = {}
    for t in tags:
        table[t] = {c: {"max_ratio": round(v["max_ratio"], 1), "worst_frame_share_gt_1.5_pct": round(100 * v["worst_frame_share_gt_1.5"], 2),
                        "edges_ever_gt_1.5_pct": round(100 * v["union_share_gt_1.5"], 2)} for c, v in data[t]["clips"].items()}
        table[t]["_pass"] = data[t]["pass"]
    update_report(o["report"], "summary", {"criteria": "largest wool-edge stretch ratio <= 1.8 and < 0.5 % of wool edges above 1.5 (judged on the worst single frame; the 'ever' share is also given)",
                                           "tags": tags, "table": table})
    log("SUMMARY_DONE", json.dumps(table))


def main():
    o = parse()
    if o["mode"] == "reweight":
        mode_reweight(o)
    elif o["mode"] == "measure":
        mode_measure(o)
    elif o["mode"] == "summary":
        mode_summary(o)
    else:
        raise SystemExit("unknown mode " + o["mode"])


main()
