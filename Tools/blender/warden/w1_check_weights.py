"""w1_check_weights.py -- P17 W1 acceptance checks on a Warden blend (read-only; never saves).

    blender -b --factory-startup <blend> --python Tools/blender/warden/w1_check_weights.py -- --out <json>

Per LOD: wool vertices with more than 50 % of their weight on leg bones (thigh/calf/foot/ball), the largest leg share, mask (BellMetal slot) vertices
that are not 100 % on `head`, vertices with more than 4 influences, vertices whose weights do not sum to 1.
"""
import json
import sys

import bpy

a = sys.argv[sys.argv.index("--") + 1:]
out = a[a.index("--out") + 1]
res = {"blend": bpy.data.filepath}
for i in range(3):
    o = bpy.data.objects["SK_Warden_LOD%d" % i]
    me = o.data
    names = {g.index: g.name for g in o.vertex_groups}
    slot = {j: (m.name.split(".")[0] if m else None) for j, m in enumerate(me.materials)}
    wool, mask = set(), set()
    for p in me.polygons:
        if slot[p.material_index] == "M_Warden_Wool":
            wool.update(p.vertices)
        elif slot[p.material_index] == "M_Warden_BellMetal":
            mask.update(p.vertices)
    leg = lambda v: sum(g.weight for g in v.groups if names[g.group].startswith(("thigh", "calf", "foot", "ball")))
    shares = [leg(me.vertices[v]) for v in wool]
    bad_mask = 0
    for v in mask:
        gs = me.vertices[v].groups
        tot = sum(g.weight for g in gs)
        h = sum(g.weight for g in gs if names[g.group] == "head")
        if tot <= 0 or h / tot < 0.9999:
            bad_mask += 1
    infl = max(len(v.groups) for v in me.vertices)
    sums = [sum(g.weight for g in v.groups) for v in me.vertices if len(v.groups)]
    res["LOD%d" % i] = {"wool_vertices": len(wool), "wool_leg_share_gt_0.5": sum(1 for s in shares if s > 0.5), "wool_max_leg_share": round(max(shares), 4),
                        "mask_vertices": len(mask), "mask_vertices_not_100pct_head": bad_mask, "max_influences": infl,
                        "weight_sum_min": round(min(sums), 5), "weight_sum_max": round(max(sums), 5)}
    print("W1CHK|", i, json.dumps(res["LOD%d" % i]))
json.dump(res, open(out, "w"), indent=1)
