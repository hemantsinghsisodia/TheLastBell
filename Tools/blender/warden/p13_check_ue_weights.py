"""p13_check_ue_weights.py -- P13-4c: compare the skin weights Unreal holds for SK_Warden with the Blender masters.

    blender.exe -b --factory-startup --python Tools/blender/warden/p13_check_ue_weights.py -- <dump.json> [<dump2.json> ...]

A dump is written by Tools/warden/p13_reimport_warden.py (P13W_DUMP): per LOD, vertex positions (cm, Unreal mesh space) and bone weights by bone index.
For every Unreal vertex the Blender vertices of SourceArt/Warden/V5_5 (old) and V5_5w2 (new) at the same place (Force Front X turns the master
(x, y, z) m into (-y, -x, z) * 100 cm) are found and the L1 distance between the weight vectors is taken (best match among the vertices at that position).
Prints per LOD: how many Unreal vertices have a match, and how many agree with the NEW and with the OLD weights (L1 < 0.05); and, among the vertices whose
old and new weights differ (L1 > 0.1 in Blender), how many Unreal holds as new. Writes <dump>.check.json next to each dump. Read-only.
"""
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector, kdtree

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
OLD = os.path.join(ROOT, "SourceArt", "Warden", "V5_5", "Warden_Rigged.blend")
NEW = os.path.join(ROOT, "SourceArt", "Warden", "V5_5w2", "Warden_Rigged.blend")


def read(path):
    bpy.ops.wm.open_mainfile(filepath=path)
    out = []
    for i in range(3):
        ob = bpy.data.objects["SK_Warden_LOD%d" % i]
        me = ob.data
        n = len(me.vertices)
        co = np.zeros(n * 3)
        me.vertices.foreach_get("co", co)
        names = [g.name for g in ob.vertex_groups]
        W = np.zeros((n, len(names)))
        for v in me.vertices:
            for g in v.groups:
                W[v.index, g.group] = g.weight
        out.append((co.reshape(-1, 3), names, W))
    return out


def main():
    dumps = sys.argv[sys.argv.index("--") + 1:]
    old, new = read(OLD), read(NEW)
    for dpath in dumps:
        d = json.load(open(dpath, encoding="utf-8"))
        rep = {"dump": dpath, "lods": []}
        for i, L in enumerate(d["lods"]):
            co, names, Wold = old[i]
            _, _, Wnew = new[i]
            ue = np.stack([-co[:, 1], -co[:, 0], co[:, 2]], axis=1) * 100.0
            kd = kdtree.KDTree(len(ue))
            for k, p in enumerate(ue):
                kd.insert(Vector(p), k)
            kd.balance()
            gi = {n: j for j, n in enumerate(names)}
            changed = np.abs(Wold - Wnew).sum(1) > 0.1
            tot = match = ag_new = ag_old = 0
            ch_total = ch_new = ch_old = 0
            far = 0
            l1n, l1o = [], []
            for p, w in zip(L["positions"], L["weights"]):
                if p is None:
                    continue
                tot += 1
                cands = [c[1] for c in kd.find_range(Vector(p), 0.01)]
                if not cands:
                    far += 1
                    continue
                match += 1
                v = np.zeros(len(names))
                for bi, wt in w:
                    v[gi[L["bones"][bi]]] += wt
                dn = min(np.abs(Wnew[c] - v).sum() for c in cands)
                do = min(np.abs(Wold[c] - v).sum() for c in cands)
                l1n.append(dn)
                l1o.append(do)
                ag_new += dn < 0.05
                ag_old += do < 0.05
                if any(changed[c] for c in cands):
                    ch_total += 1
                    ch_new += dn < 0.05 <= do
                    ch_old += do < 0.05 <= dn
            r = {"lod": i, "unreal_vertices": tot, "matched_in_position": match, "no_match": far, "agree_with_new": int(ag_new), "agree_with_old": int(ag_old),
                 "mean_L1_to_new": float(np.mean(l1n)), "mean_L1_to_old": float(np.mean(l1o)),
                 "at_changed_vertices": {"unreal_vertices": ch_total, "equal_to_new_only": int(ch_new), "equal_to_old_only": int(ch_old)}}
            rep["lods"].append(r)
            print("UEW| %s" % json.dumps(r))
        json.dump(rep, open(dpath + ".check.json", "w"), indent=1)


main()
