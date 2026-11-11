"""w0_survey_blend.py -- P17 W0: read-only survey of a Warden_Rigged.blend (armature, LOD meshes, slots, mask weights, what is under the mask).

    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --factory-startup <blend> --python Tools/blender/warden/w0_survey_blend.py -- --out <json>

Never saves the blend (only reads it; pose and visibility changes stay in memory). Output JSON: objects, bones (rest, armature space, cm), per-LOD slots and
triangle counts, rest-pose bounds, per-slot islands/weights/bounds, the mask (slot named *BellMetal) weights and bounds in `head` bone space, and a ray
grid through the mask outline with the mask removed (first-hit slot histogram).
"""
import json
import math
import sys
from collections import Counter, defaultdict

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = {a[i].lstrip("-"): a[i + 1] for i in range(0, len(a) - 1, 2)}
OUT = opt["out"]
CM = 100.0


def r(x, n=4):
    return round(float(x), n)


def v3(v, k=CM):
    return [r(v[0] * k), r(v[1] * k), r(v[2] * k)]


res = {"blend": bpy.data.filepath}
scene = bpy.context.scene
arm = bpy.data.objects["Warden_Rig"]
res["unit_scale_length"] = scene.unit_settings.scale_length
res["fps"] = scene.render.fps
res["actions"] = {x.name: [x.frame_range[0], x.frame_range[1]] for x in bpy.data.actions}

# ---- objects
objs = []
for o in bpy.data.objects:
    d = {"name": o.name, "type": o.type, "parent": o.parent.name if o.parent else None, "hide_render": o.hide_render,
         "hide_viewport": o.hide_viewport, "collections": [c.name for c in o.users_collection]}
    if o.type == "MESH":
        d["verts"] = len(o.data.vertices)
        d["polys"] = len(o.data.polygons)
        o.data.calc_loop_triangles()
        d["tris"] = len(o.data.loop_triangles)
        d["slots"] = [{"index": i, "slot": s.name, "material": s.material.name if s.material else None} for i, s in enumerate(o.material_slots)]
    if o.type == "ARMATURE":
        d["bones"] = len(o.data.bones)
    objs.append(d)
res["objects"] = objs

# ---- armature: rest pose, armature space (matrix_world of the rig is identity, scale 1; checked below)
res["rig_matrix_world_identity"] = bool(all(abs(arm.matrix_world[i][j] - (1 if i == j else 0)) < 1e-6 for i in range(4) for j in range(4)))
bones = []
for b in arm.data.bones:
    m = b.matrix_local
    q = m.to_quaternion()
    bones.append({"name": b.name, "parent": b.parent.name if b.parent else None, "head_cm": v3(m.translation),
                  "tail_cm": v3(b.tail_local), "length_cm": r(b.length * CM), "quat_wxyz": [r(q.w, 6), r(q.x, 6), r(q.y, 6), r(q.z, 6)],
                  "deform": b.use_deform})
res["bones"] = bones

# ---- put the rig at the exact rest pose (in memory only)
if arm.animation_data:
    arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.location = (0, 0, 0)
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = (1, 0, 0, 0)
    pb.scale = (1, 1, 1)
scene.frame_set(1)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()


def eval_mesh(o):
    """World-space vertex positions and the evaluated mesh (armature modifier applied at the current pose)."""
    oe = o.evaluated_get(dg)
    me = oe.to_mesh()
    me.calc_loop_triangles()
    mw = oe.matrix_world
    pos = [mw @ v.co for v in me.vertices]
    return oe, me, pos


head_b = arm.data.bones["head"]
head_world = arm.matrix_world @ head_b.matrix_local          # rest, world
head_inv = head_world.inverted()
res["head_bone_world_axes"] = {"x": v3(head_world.to_3x3() @ Vector((1, 0, 0)), 1), "y": v3(head_world.to_3x3() @ Vector((0, 1, 0)), 1),
                               "z": v3(head_world.to_3x3() @ Vector((0, 0, 1)), 1), "head_cm": v3(head_world.translation)}

lods = {}
mask_info = {}
for li in range(3):
    o = bpy.data.objects["SK_Warden_LOD%d" % li]
    oe, me, pos = eval_mesh(o)
    zs = [p.z for p in pos]
    xs = [p.x for p in pos]
    ys = [p.y for p in pos]
    d = {"object": o.name, "verts": len(o.data.vertices), "polys": len(o.data.polygons), "tris": len(me.loop_triangles),
         "slots": [{"index": i, "slot": s.name, "material": s.material.name if s.material else None} for i, s in enumerate(o.material_slots)],
         "rest_bounds_cm": {"min": [r(min(xs) * CM), r(min(ys) * CM), r(min(zs) * CM)], "max": [r(max(xs) * CM), r(max(ys) * CM), r(max(zs) * CM)]},
         "rest_height_cm": r((max(zs) - min(zs)) * CM),
         "rest_bounds_centre_cm": [r((max(xs) + min(xs)) / 2 * CM), r((max(ys) + min(ys)) / 2 * CM), r((max(zs) + min(zs)) / 2 * CM)]}
    # triangles per slot
    tc = Counter(me.polygons[t.polygon_index].material_index for t in me.loop_triangles)
    d["tris_per_slot"] = {str(k): v for k, v in sorted(tc.items())}
    pc = Counter(p.material_index for p in o.data.polygons)
    d["polys_per_slot"] = {str(k): v for k, v in sorted(pc.items())}
    # per slot detail on the ORIGINAL mesh (weights are on the original)
    vg_names = {g.index: g.name for g in o.vertex_groups}
    me0 = o.data
    # islands per slot by union-find on vertices used by faces of the slot
    per_slot = {}
    for si, s in enumerate(o.material_slots):
        polys = [p for p in me0.polygons if p.material_index == si]
        if not polys:
            continue
        parent = {}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for p in polys:
            for vi in p.vertices:
                parent.setdefault(vi, vi)
        for p in polys:
            vs = list(p.vertices)
            for vi in vs[1:]:
                ra, rb = find(vs[0]), find(vi)
                if ra != rb:
                    parent[ra] = rb
        vset = set(parent)
        comp = defaultdict(list)
        for vi in vset:
            comp[find(vi)].append(vi)
        wsum = Counter()
        wtot = 0.0
        for vi in vset:
            for g in me0.vertices[vi].groups:
                wsum[vg_names[g.group]] += g.weight
                wtot += g.weight
        pw = [pos[vi] for vi in vset]
        hp = [head_inv @ p for p in pw]
        isl = []
        for k, vs in sorted(comp.items(), key=lambda kv: -len(kv[1]))[:8]:
            isl.append({"verts": len(vs), "centre_cm": v3(sum((pos[i] for i in vs), Vector()) / len(vs))})
        per_slot[str(si)] = {
            "slot": s.name, "polys": len(polys), "verts": len(vset), "islands": len(comp), "largest_islands": isl,
            "bounds_cm": {"min": v3(Vector((min(p.x for p in pw), min(p.y for p in pw), min(p.z for p in pw)))),
                          "max": v3(Vector((max(p.x for p in pw), max(p.y for p in pw), max(p.z for p in pw))))},
            "bounds_head_space_cm": {"min": v3(Vector((min(p.x for p in hp), min(p.y for p in hp), min(p.z for p in hp)))),
                                     "max": v3(Vector((max(p.x for p in hp), max(p.y for p in hp), max(p.z for p in hp))))},
            "weight_share": {k: r(v / wtot, 5) for k, v in wsum.most_common(6)} if wtot else {}}
    d["per_slot"] = per_slot
    lods[str(li)] = d

    # ---- the mask: the BellMetal slot
    mi = next(i for i, s in enumerate(o.material_slots) if "BellMetal" in s.name)
    mpolys = [p for p in me0.polygons if p.material_index == mi]
    mverts = sorted({vi for p in mpolys for vi in p.vertices})
    wsum = Counter()
    nweights = Counter()
    head100 = 0
    maxother = Counter()
    for vi in mverts:
        gs = {vg_names[g.group]: g.weight for g in me0.vertices[vi].groups if g.weight > 1e-6}
        tot = sum(gs.values())
        for k, w in gs.items():
            wsum[k] += w
        nweights[len(gs)] += 1
        if tot > 0 and gs.get("head", 0) / tot > 0.9999:
            head100 += 1
        for k, w in gs.items():
            if k != "head":
                maxother[k] = max(maxother[k], w / tot)
    tot = sum(wsum.values())
    hp = [head_inv @ pos[vi] for vi in mverts]
    pw = [pos[vi] for vi in mverts]
    # area-weighted outward normal (world)
    nrm = Vector()
    area = 0.0
    for p in mpolys:
        nrm += (o.matrix_world.to_3x3() @ p.normal) * p.area
        area += p.area
    nrm.normalize()
    mask_info[str(li)] = {
        "slot_index": mi, "slot": o.material_slots[mi].name, "polys": len(mpolys), "tris": tc.get(mi, 0), "verts": len(mverts), "area_cm2": r(area * CM * CM, 1),
        "weight_share_by_bone": {k: r(v / tot, 5) for k, v in wsum.most_common()},
        "verts_100pct_head": head100, "verts_100pct_head_fraction": r(head100 / len(mverts), 5),
        "largest_non_head_weight_on_any_vertex": {k: r(v, 4) for k, v in maxother.most_common(5)},
        "influences_per_vertex": {str(k): v for k, v in sorted(nweights.items())},
        "bounds_head_space_cm_blender_axes": {"min": v3(Vector((min(p.x for p in hp), min(p.y for p in hp), min(p.z for p in hp)))),
                                              "max": v3(Vector((max(p.x for p in hp), max(p.y for p in hp), max(p.z for p in hp))))},
        "bounds_world_cm": {"min": v3(Vector((min(p.x for p in pw), min(p.y for p in pw), min(p.z for p in pw)))),
                            "max": v3(Vector((max(p.x for p in pw), max(p.y for p in pw), max(p.z for p in pw))))},
        "centroid_world_cm": v3(sum(pw, Vector()) / len(pw)),
        "centroid_head_space_cm": v3(sum(hp, Vector()) / len(hp)),
        "area_weighted_normal_world": [r(x, 4) for x in nrm],
    }
res["lods"] = lods
res["mask"] = mask_info

# ---- what is behind the mask? Ray grid on LOD0 at rest, mask faces removed
o = bpy.data.objects["SK_Warden_LOD0"]
oe, me, pos = eval_mesh(o)
mi = mask_info["0"]["slot_index"]
nrm = Vector(mask_info["0"]["area_weighted_normal_world"])
up = Vector((0, 0, 1))
side = nrm.cross(up).normalized()
upv = side.cross(nrm).normalized()
mpos = [pos[vi] for p in o.data.polygons if p.material_index == mi for vi in p.vertices]
c0 = sum(mpos, Vector()) / len(mpos)
us = [(p - c0).dot(side) for p in mpos]
vs = [(p - c0).dot(upv) for p in mpos]
ds = [(p - c0).dot(nrm) for p in mpos]
tris_all = [(t.vertices[0], t.vertices[1], t.vertices[2], me.polygons[t.polygon_index].material_index) for t in me.loop_triangles]
bv_all = BVHTree.FromPolygons([tuple(p) for p in pos], [t[:3] for t in tris_all], all_triangles=True)
nm = [t for t in tris_all if t[3] != mi]
bv_nm = BVHTree.FromPolygons([tuple(p) for p in pos], [t[:3] for t in nm], all_triangles=True)
mask_front = max(ds)
mask_back = min(ds)
hist = Counter()
depth = defaultdict(list)
total_hit = 0
N = 40
for iu in range(N):
    for iv in range(N):
        u = min(us) + (max(us) - min(us)) * (iu + .5) / N
        v = min(vs) + (max(vs) - min(vs)) * (iv + .5) / N
        org = c0 + side * u + upv * v + nrm * 1.0
        h_all = bv_all.ray_cast(org, -nrm, 3.0)
        if h_all[0] is None:
            continue
        # only rays whose first hit with everything is a mask face (this is the region the mask covers)
        if tris_all[h_all[2]][3] != mi:
            continue
        total_hit += 1
        h = bv_nm.ray_cast(org, -nrm, 3.0)
        if h[0] is None:
            hist["none (void: nothing behind the mask)"] += 1
            continue
        t = nm[h[2]]
        key = "slot %d %s" % (t[3], o.material_slots[t[3]].name)
        hist[key] += 1
        depth[key].append((h[0] - c0).dot(nrm) * CM)      # cm relative to the mask centroid plane; negative = behind
res["behind_mask"] = {
    "rays_covered_by_mask": total_hit, "grid": N, "mask_extent_cm": {"width": r((max(us) - min(us)) * CM), "height": r((max(vs) - min(vs)) * CM),
                                                                      "depth_front_to_back": r((mask_front - mask_back) * CM)},
    "first_hit_after_removing_mask": dict(hist),
    "hit_depth_cm_relative_to_mask_centroid_plane": {k: {"min": r(min(x), 2), "mean": r(sum(x) / len(x), 2), "max": r(max(x), 2)} for k, x in depth.items()},
    "mask_front_plane_cm_from_centroid": r(mask_front * CM, 2), "mask_back_plane_cm_from_centroid": r(mask_back * CM, 2),
}

with open(OUT, "w") as f:
    json.dump(res, f, indent=1)
print("W0SURVEY| wrote", OUT)
