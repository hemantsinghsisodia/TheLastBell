"""P10-6a / P10-6e numeric checks (D1.20 step 4, updated by D1.21 step 4). Read-only; prints PASS / FAIL per line, a summary, and exits 1 on any FAIL.
Editor open on L_Monastery, no PIE, one editor-touching process at a time.

    python Tools/belltower/p10_6a_checks.py > Docs/ArtTest/belltower/p10_6e_checks.txt

1. chain on the drum (D1.21): CLA_Mech3_Chain_A_0 run_from lies inside the Core's world AABB (p10_6b_checks.world_box, root component no longer double-counted)
   grown by 2 cm and is >= 30 from the drum axis (11790, 1780); Mech_Ritual3 actor bounds X 11735-11845, Y 1725-1835 (+-1)
2. CLA_Collapse_Heap world bounds X 11050-11370, Y 2295-2505, Z 0-65 (+-3), collision BlockAll / QueryAndPhysics
3. vegetation: per-folder counts (90 grass, 30 nettle, 35 fern, 18 rooibos, 2 shrubs, 32 weeds), each actor's scale equals its record (+-0.001), min / max height per group
3b. belfry debris (D1.21): every TWA_Debris_* AABB inside X 12041-12130, Y 2170-2450, Z 2499-2560; the rafter's axis within 8 deg of +Y, S end on the floor
   at (12055, 2185) +-5, N end raised 20-30, AABB inside Z 2500-2550
4. no dress actor intersects the gameplay actors (grown 10 cm) nor the two door swing boxes (Z 0-300)
Gameplay component bounds are computed from the meshes' local bounds and the live component transforms (full parent chain), because the
actor-level bounds include editor sprites; dress meshes use get_actor_bounds.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "mcp"))
import bp_swap  # noqa: E402
import place_tower  # noqa: E402
import p10_6b_checks  # noqa: E402   (world_box: D1.21 root-component fix)

S, A, O = bp_swap.S, bp_swap.A, bp_swap.O
SM = place_tower.SM
P = place_tower.Placer()
ue = P.ue

RESULTS = []


def report(ok, name, detail=""):
    RESULTS.append(ok)
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("\n        " + detail) if detail else ""), flush=True)


def fmt(v):
    return "(" + ", ".join("%.1f" % x for x in v) + ")"


def props(obj, names):
    r = P.call(O, "get_properties", {"instance": obj, "properties": names})
    return json.loads(r) if isinstance(r, str) else r


def mat_of(loc, rot, sc):
    """4x4-ish: returns (R columns as 3x3, scale vector, location); world = R * (S * p) + loc"""
    rows = place_tower.rot_rows(*rot)          # row i = world image of local axis i
    R = [[rows[j][i] for j in range(3)] for i in range(3)]
    return R, list(sc), list(loc)


class Lin:
    """world = A * p + t, A a general 3x3 (handles parent scale + child rotation exactly)"""

    def __init__(self, A_, t):
        self.A, self.t = A_, t

    @staticmethod
    def from_trs(loc, rot, sc):
        R, S_, L = mat_of(loc, rot, sc)
        return Lin([[R[i][j] * S_[j] for j in range(3)] for i in range(3)], L)

    def then_under(self, parent):
        """self expressed in the parent's frame -> parent(self(p))"""
        Ap, tp = parent.A, parent.t
        A_ = [[sum(Ap[i][k] * self.A[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
        t_ = [sum(Ap[i][k] * self.t[k] for k in range(3)) + tp[i] for i in range(3)]
        return Lin(A_, t_)

    def box(self, lo, hi):
        pts = []
        for x in (lo[0], hi[0]):
            for y in (lo[1], hi[1]):
                for z in (lo[2], hi[2]):
                    pts.append([sum(self.A[i][k] * v for k, v in enumerate((x, y, z))) + self.t[i] for i in range(3)])
        return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


_mesh_bounds = {}


def mesh_bounds(path):
    if path not in _mesh_bounds:
        b = P.call(SM, "get_bounds", {"mesh": {"refPath": path}})
        _mesh_bounds[path] = ([b["min"][k] for k in "xyz"], [b["max"][k] for k in "xyz"])
    return _mesh_bounds[path]


def component_boxes(actor):
    """[(component name, min, max)] world boxes of every StaticMeshComponent (with a mesh) of a placed Blueprint actor"""
    xf = P.call(A, "get_actor_transform", {"actor": actor, "worldspace": True})
    actor_lin = Lin.from_trs([xf["location"][k] for k in "xyz"], [xf["rotation"][k] for k in ("pitch", "yaw", "roll")], [xf["scale"][k] for k in "xyz"])
    root = P.call(A, "get_root_component", {"actor": actor})["refPath"]
    out, cache = [], {}

    def lin_of(cref):
        if cref in cache:
            return cache[cref]
        if cref == root:
            cache[cref] = actor_lin           # the actor transform is the root component's world transform
            return actor_lin
        p = props({"refPath": cref}, ["relativeLocation", "relativeRotation", "relativeScale3D"])
        rl, rr, rs = p["relativeLocation"], p["relativeRotation"], p["relativeScale3D"]
        local = Lin.from_trs([rl[k] for k in "xyz"], [rr["pitch"], rr["yaw"], rr["roll"]], [rs[k] for k in "xyz"])
        par = P.call(A, "get_parent_component", {"component": {"refPath": cref}})
        parl = lin_of(par["refPath"]) if par else actor_lin
        cache[cref] = local.then_under(parl)
        return cache[cref]

    for c in P.call(A, "get_components", {"actor": actor}):
        cref = c["refPath"]
        try:      # non-mesh components (scene roots, billboards, text) raise here: no retries for those
            r_ = P.ue.call(O, "get_properties", {"instance": c, "properties": ["staticMesh"]})
            m = (json.loads(r_) if isinstance(r_, str) else r_)["staticMesh"]
        except Exception:
            continue
        if not m:
            continue
        try:
            lo, hi = mesh_bounds(m["refPath"])
            mn, mx = lin_of(cref).box(lo, hi)
        except Exception as e:
            print("  (skipped component %s: %s)" % (cref.split(".")[-1], str(e)[:100]))
            continue
        out.append((cref.split(".")[-1], mn, mx))
    return out


def intersects(a_min, a_max, b_min, b_max, grow=0.0):
    return all(a_min[i] - grow < b_max[i] and a_max[i] + grow > b_min[i] for i in range(3))


def main():
    lvl = P.call(S, "get_current_level")
    if not str(lvl).endswith("L_Monastery"):
        sys.exit("editor is not on L_Monastery: %s" % lvl)
    recs = {r["id"]: r for r in P.layout["placements"] if r["cat"] == "dress"}
    folders = sorted({r["folder"] for r in recs.values()})
    actors = {}
    for f in folders:
        for lbl, a in P.folder_actors(f, refresh=True).items():
            if lbl in recs:
                actors[lbl] = a
    report(len(actors) == len(recs) == 278, "all dress records are placed (278)", "%d actors found for %d records" % (len(actors), len(recs)))

    # ---- 1 chain on the drum
    print("\n== 1. Chain on the drum")
    r = recs["CLA_Mech3_Chain_A_0"]
    rf = r["extras"]["run_from"]
    dxy = math.hypot(rf[0] - 11790.0, rf[1] - 1780.0)
    mech = bp_swap.find_exact(ue, "Mech_Ritual3")
    core_lo, core_hi = p10_6b_checks.world_box(mech, ["Pedestal", "Core"])
    inside = all(core_lo[i] - 2.0 <= rf[i] <= core_hi[i] + 2.0 for i in range(3))
    report(inside and dxy >= 30.0, "CLA_Mech3_Chain_A_0 run_from %s lies within the Core's world AABB grown by 2 cm and is >= 30 from the drum axis (11790, 1780)" % rf,
           "Core AABB %s .. %s, XY distance from the axis %.2f" % (fmt(core_lo), fmt(core_hi), dxy))
    cl = actors.get("CLA_Mech3_Chain_A_0")
    if cl:
        t = P.call(A, "get_actor_transform", {"actor": cl, "worldspace": True})
        d = max(abs(t["location"][k] - rf[i]) for i, k in enumerate("xyz"))
        report(d <= 0.1, "placed CLA_Mech3_Chain_A_0 location equals run_from (+-0.1)", "max deviation %.3f" % d)
    b = P.call(A, "get_actor_bounds", {"actor": mech})
    mn, mx = [b["min"][k] for k in "xyz"], [b["max"][k] for k in "xyz"]
    want = ((11735, 1725), (11845, 1835))
    ok = all(abs(mn[i] - want[0][i]) <= 1 and abs(mx[i] - want[1][i]) <= 1 for i in range(2))
    report(ok, "Mech_Ritual3 actor bounds X 11735-11845, Y 1725-1835 (+-1)", "min %s max %s" % (fmt(mn), fmt(mx)))

    # ---- 2 collapse heap
    print("\n== 2. Collapse heap")
    h = actors.get("CLA_Collapse_Heap")
    if h is None:
        report(False, "CLA_Collapse_Heap exists")
    else:
        mn, mx = P.bounds(h)
        want_min, want_max = (11050, 2295, 0), (11370, 2505, 65)
        dev = max(max(abs(mn[i] - want_min[i]) for i in range(3)), max(abs(mx[i] - want_max[i]) for i in range(3)))
        report(dev <= 3.0, "CLA_Collapse_Heap world bounds within 3 cm of X 11050-11370, Y 2295-2505, Z 0-65", "min %s max %s, max deviation %.2f" % (fmt(mn), fmt(mx), dev))
        st = P.read_state(P.comp0(h))
        report(st["profile"] == "BlockAll" and "QueryAndPhysics" in str(st["enabled"]), "CLA_Collapse_Heap collision BlockAll / QueryAndPhysics (the mesh's own collision)",
               "profile %s, collisionEnabled %s, useDefault %s" % (st["profile"], st["enabled"], st["useDefault"]))

    # ---- 3 vegetation
    print("\n== 3. Vegetation read-back")
    groups = [("CLA_GarthGrass_", 90), ("CLA_GarthNettle_", 30), ("CLA_GarthFern_", 35), ("CLA_GarthRooibos_", 18), ("CLA_GarthShrub_", 2), ("PSA_Weed_", 32)]
    for pre, n in groups:
        ids = sorted(i for i in recs if i.startswith(pre))
        found = [i for i in ids if i in actors]
        folder_ok = len({recs[i]["folder"] for i in ids}) == 1
        report(len(ids) == n and len(found) == n and folder_ok, "%s*: %d actors in %s" % (pre, len(found), recs[ids[0]]["folder"] if ids else "-"),
               "records %d, placed %d" % (len(ids), len(found)))
        worst_s, hts, scl = 0.0, [], []
        for i in found:
            t = P.call(A, "get_actor_transform", {"actor": actors[i], "worldspace": True})
            worst_s = max(worst_s, max(abs(t["scale"][k] - recs[i]["scale"]["xyz".index(k)]) for k in "xyz"))
            bn, bx = P.bounds(actors[i])
            hts.append(bx[2] - bn[2])
            scl.append(recs[i]["scale"][0])
        report(worst_s <= 0.001, "%s* scale equals the record (+-0.001)" % pre, "worst deviation %.5f; scale range %.3f-%.3f" % (worst_s, min(scl), max(scl)) if scl else "")
        if hts:
            print("        world-bounds height: min %.1f max %.1f cm (%d actors)" % (min(hts), max(hts), len(hts)))

    # ---- 3b belfry debris
    print("\n== 3b. Belfry debris")
    deb = sorted(i for i in recs if i.startswith("TWA_Debris_"))
    report(len(deb) == 6 and all(i in actors for i in deb), "6 TWA_Debris_* actors placed (5 chunks + rafter)", "%d records, %d placed" % (len(deb), len([i for i in deb if i in actors])))
    for i in deb:
        if i not in actors:
            continue
        bn, bx = P.bounds(actors[i])
        ok = bn[0] >= 12041 - 0.3 and bx[0] <= 12130 + 0.3 and bn[1] >= 2170 - 0.3 and bx[1] <= 2450 + 0.3 and bn[2] >= 2499 and bx[2] <= 2560
        report(ok, "%s AABB inside X 12041-12130, Y 2170-2450, Z 2499-2560 (+-0.3 in plan)" % i, "%s .. %s" % (fmt(bn), fmt(bx)))
    if "TWA_Debris_Rafter" in actors:
        ra = actors["TWA_Debris_Rafter"]
        t = P.call(A, "get_actor_transform", {"actor": ra, "worldspace": True})
        rot = [t["rotation"][k] for k in ("pitch", "yaw", "roll")]
        zax = place_tower.rot_rows(*rot)[2]                 # local +Z (the long axis; pivot at the S end) in world
        plan = math.degrees(math.atan2(zax[0], zax[1]))
        sc = t["scale"]["z"]
        s_end = [t["location"][k] for k in "xyz"]
        n_end = [s_end[i] + zax[i] * 260.0 * sc for i in range(3)]
        bn, bx = P.bounds(ra)
        rise = n_end[2] - s_end[2]
        report(abs(plan) <= 8.0 and 2499.7 <= bn[2] <= 2502.3 and abs(s_end[0] - 12055) <= 5 and abs(s_end[1] - 2185) <= 5 and 20 <= rise <= 30
               and bn[0] >= 12040.7 and bx[0] <= 12130.3 and bn[1] >= 2169.7 and bx[1] <= 2450.3 and bx[2] <= 2550,
               "TWA_Debris_Rafter: axis within 8 deg of +Y, bottom Z 2500-2502, S end (12055, 2185) +-5, N end raised 20-30, AABB inside X 12041-12130, Y 2170-2450, Z <= 2550",
               "plan angle %.2f deg, S end %s, N end %s, rise %.1f, AABB %s .. %s, rotator %s" % (plan, fmt(s_end), fmt(n_end), rise, fmt(bn), fmt(bx), [round(v, 3) for v in rot]))

    # ---- 4 no dress on the gameplay actors / door swings
    print("\n== 4. Dress vs gameplay actors and door swing boxes")
    dress_box = {}
    for lbl, a in actors.items():
        dress_box[lbl] = P.bounds(a)
    gp = {}
    for lbl in ("Mech_Ritual3", "Bell_1", "Bell_2", "Bell_3", "Bell_4", "Clue_Inscription", "Note_Cloister", "Bell"):
        a = bp_swap.find_exact(ue, lbl)
        gp[lbl] = component_boxes(a)
        allmn = [min(c[1][i] for c in gp[lbl]) for i in range(3)] if gp[lbl] else None
        allmx = [max(c[2][i] for c in gp[lbl]) for i in range(3)] if gp[lbl] else None
        print("  %s: %d mesh components, union %s .. %s" % (lbl, len(gp[lbl]), fmt(allmn) if allmn else "-", fmt(allmx) if allmx else "-"))
        if not gp[lbl]:
            report(False, "%s has mesh components to test against" % lbl)
    hits = []
    for lbl, (dmn, dmx) in dress_box.items():
        for g, comps in gp.items():
            for cname, cmn, cmx in comps:
                if intersects(dmn, dmx, cmn, cmx, grow=10.0):
                    if lbl == "CLA_Mech3_Chain_A_0" and g == "Mech_Ritual3":
                        continue                      # allowed exception
                    hits.append("%s %s..%s  vs  %s.%s %s..%s (grown 10)" % (lbl, fmt(dmn), fmt(dmx), g, cname, fmt(cmn), fmt(cmx)))
    report(not hits, "no dress actor (bounds) intersects Mech_Ritual3, Bell_1..4, Clue_Inscription, Note_Cloister, Bell grown by 10 cm (except Chain_A_0 / Mech_Ritual3)",
           "\n        ".join(hits) if hits else "%d dress actors x %d gameplay mesh components" % (len(dress_box), sum(len(v) for v in gp.values())))
    a0 = dress_box.get("CLA_Mech3_Chain_A_0")
    if a0:
        touch = any(intersects(a0[0], a0[1], c[1], c[2], 10.0) for c in gp["Mech_Ritual3"])
        print("  (info) CLA_Mech3_Chain_A_0 %s..%s touches Mech_Ritual3 (grown 10): %s" % (fmt(a0[0]), fmt(a0[1]), touch))
    swings = (("Door_Tower", (11913, 1943, 0), (12027, 2057, 300)), ("Door_Shortcut", (5895, 1934, 0), (6027, 2066, 300)))
    for name, smn, smx in swings:
        sh = ["%s %s..%s vs swing %s..%s" % (lbl, fmt(b[0]), fmt(b[1]), smn, smx) for lbl, b in dress_box.items() if intersects(b[0], b[1], smn, smx)]
        report(not sh, "no dress actor intersects the %s swing box X %d-%d, Y %d-%d, Z 0-300" % (name, smn[0], smx[0], smn[1], smx[1]),
               "\n        ".join(sh) if sh else "%d dress actors tested" % len(dress_box))

    n_fail = RESULTS.count(False)
    print("\nSUMMARY: %d checks, %d PASS, %d FAIL -> %s" % (len(RESULTS), len(RESULTS) - n_fail, n_fail, "ALL PASS" if not n_fail else "FAILED"))
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
