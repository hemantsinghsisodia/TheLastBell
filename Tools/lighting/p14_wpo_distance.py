"""P14-3 item 7: World Position Offset disable distance for the wind (Docs/plans/P14_LIGHTING_STORM.md section 7.7).

Sets WorldPositionOffsetDisableDistance = 4000 cm on
  (a) the static-mesh component of every StaticMeshActor whose EFFECTIVE material (override, else the mesh's default slot) is one of the
      nine foliage MIs: MI_Foliage_GrassMedium02, _NettlePlant, _WeedPlant02, _Fern02, _WildRooibos, _SearsiaLucida, _Moss01,
      MI_Ivy_Green, MI_Ivy_Dead (F0: 249 actors), and
  (b) every ISM component the PCG volumes (PCGV_*) generated (F0: 312).

    python -I Tools/lighting/p14_wpo_distance.py --apply   # live scan, prints the counts, STOPS unless they are 249 and 312, then writes
    python -I Tools/lighting/p14_wpo_distance.py --check   # every target must read 4000
    options: --resume (reuse the scan cache Saved/p14_wpo_scan.json), --rescan (--check: scan the level again instead of using the
             target list written by --apply), --expect-actors N, --expect-isms N, --force-counts (apply with other counts; never used in P14-3),
             --dry (with --apply: scan and print the counts only)

Regenerating a PCGV_* volume resets the ISM distance to 0: run --apply again afterwards (Tools/mcp/MCP_NOTES.md, Storm materials).
Nothing is saved by this script. A scan makes about 2500 read calls (10 to 15 minutes with the editor in the background).
"""
import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from p14_3_level import A, S, Ed, EditorStop, J, R, ROOT  # noqa: E402

SM = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
DISTANCE = 4000
FOLIAGE_MIS = {"MI_Foliage_GrassMedium02", "MI_Foliage_NettlePlant", "MI_Foliage_WeedPlant02", "MI_Foliage_Fern02", "MI_Foliage_WildRooibos",
               "MI_Foliage_SearsiaLucida", "MI_Foliage_Moss01", "MI_Ivy_Green", "MI_Ivy_Dead"}
EXPECT_ACTORS, EXPECT_ISMS = 249, 312
SCAN_CACHE = os.path.join(ROOT, "Saved", "p14_wpo_scan.json")
TARGETS = os.path.join(ROOT, "Saved", "p14_wpo_targets.json")
INVENTORY = os.path.join(ROOT, "Docs", "ArtTest", "lighting", "p14_f0_inventory.json")
PROP = "worldPositionOffsetDisableDistance"


def short(ref):
    return ref.rsplit(".", 1)[-1].rsplit("/", 1)[-1] if ref else None


def oname(ref):
    return ref.split("PersistentLevel.", 1)[1] if "PersistentLevel." in ref else ref.rsplit(".", 1)[-1]


def cls_of(ref):
    n = re.sub(r"_\d+$", "", oname(ref))
    return "PCGV" if n.startswith("PCGV_") else n


class Scan:
    def __init__(self, ed, resume):
        self.ed = ed
        self.cache = {}
        if resume and os.path.exists(SCAN_CACHE):
            self.cache = json.load(open(SCAN_CACHE, encoding="utf-8"))
        self.t0 = time.time()
        self.dirty = 0

    def save(self):
        os.makedirs(os.path.dirname(SCAN_CACHE), exist_ok=True)
        with open(SCAN_CACHE, "w", encoding="utf-8", newline="\n") as f:
            json.dump(self.cache, f)

    def step(self, key, fn):
        if key not in self.cache:
            self.cache[key] = fn()
            self.dirty += 1
            if self.dirty % 100 == 0:
                self.save()
        return self.cache[key]

    def log(self, msg):
        print("[%5.0fs, %5d calls] %s" % (time.time() - self.t0, self.ed.calls, msg), flush=True)

    def sma(self, ref):
        ed = self.ed

        def f():
            comp = ref + ".StaticMeshComponent0"
            try:
                p = ed.props(comp, ["staticMesh", "overrideMaterials", PROP])
            except RuntimeError:
                root = R(J(ed.call(A, "get_root_component", {"actor": {"refPath": ref}})))
                comp = root
                p = ed.props(root, ["staticMesh", "overrideMaterials", PROP])
            return {"comp": comp, "mesh": R(p.get("staticMesh")), "ov": [short(R(o)) for o in (p.get("overrideMaterials") or [])], "dist": p.get(PROP)}
        return self.step("sma:" + ref, f)

    def slots(self, mesh_ref):
        ed = self.ed

        def f():
            names = J(ed.call(SM, "get_material_slots", {"mesh": {"refPath": mesh_ref}})) or []
            names = [n if isinstance(n, str) else (n.get("slotName") or n.get("name")) for n in names]
            return [short(R(J(ed.call(SM, "get_material", {"mesh": {"refPath": mesh_ref}, "slot_name": n})))) for n in names]
        return self.step("slots:" + mesh_ref, f)

    def actors(self, refs):
        smas = [r for r in refs if cls_of(r) == "StaticMeshActor"]
        out, other_dist = [], 0
        for i, r in enumerate(smas):
            v = self.sma(r)
            if i % 250 == 0:
                self.log("static-mesh actors %d/%d" % (i, len(smas)))
            if not v["mesh"]:
                continue
            slots = self.slots(v["mesh"])
            eff = [(v["ov"][k] if k < len(v["ov"]) and v["ov"][k] else d) for k, d in enumerate(slots)]
            if any(e in FOLIAGE_MIS for e in eff):
                out.append({"ref": r, "comp": v["comp"], "mesh": short(v["mesh"]), "effective": eff, "dist": v["dist"]})
            elif v["dist"]:
                other_dist += 1
        self.log("static-mesh actors scanned: %d; non-target actors with a WPO distance already set: %d" % (len(smas), other_dist))
        return out, len(smas), other_dist

    def isms(self, refs):
        ed = self.ed
        out, vols = [], [r for r in refs if cls_of(r) == "PCGV"]
        for r in vols:
            def f(r=r):
                comps = J(ed.call(A, "get_components", {"actor": {"refPath": r}})) or []
                res = []
                for c in comps:
                    cr = R(c)
                    if not cr or not re.search(r"ISM|Instanced", cr.rsplit(".", 1)[-1]):
                        continue
                    p = ed.props(cr, ["staticMesh", PROP])
                    res.append({"comp": cr, "mesh": short(R(p.get("staticMesh"))), "dist": p.get(PROP)})
                return res
            out += self.step("pcg:" + r, f)
        self.log("PCG volumes: %d, ISM components: %d" % (len(vols), len(out)))
        return out, len(vols)


def live_scan(ed, resume):
    sc = Scan(ed, resume)
    refs = ed.find_all()
    sc.log("actors in the level: %d" % len(refs))
    actors, n_sma, other = sc.actors(refs)
    isms, n_vol = sc.isms(refs)
    sc.save()
    return {"actors": actors, "isms": isms, "static_mesh_actors": n_sma, "pcg_volumes": n_vol, "other_with_distance": other}


def cross_check_inventory(actors):
    if not os.path.exists(INVENTORY):
        print("INFO  F0 inventory not found; no cross-check")
        return
    inv = json.load(open(INVENTORY, encoding="utf-8"))
    f0 = {x["ref"] for x in inv["users"]["foliage_actors"]}
    live = {a["ref"] for a in actors}
    print("INFO  F0 inventory lists %d foliage actors; live scan %d; only in F0: %d; only live: %d" % (len(f0), len(live), len(f0 - live), len(live - f0)))
    if f0 != live:
        print("INFO  only in F0: %s ; only live: %s" % (sorted(f0 - live)[:5], sorted(live - f0)[:5]))
    f0_isms = sum(len(v["isms"]) for v in inv["pcg_volumes"])
    print("INFO  F0 inventory lists %d ISM components" % f0_isms)


def read_dist(ed, comp):
    return ed.props(comp, [PROP])[PROP]


def summarize(scan):
    a, i = scan["actors"], scan["isms"]
    from collections import Counter
    by_mi = Counter(m for x in a for m in x["effective"] if m in FOLIAGE_MIS)
    print("INFO  targets: %d static-mesh actors (of %d scanned) + %d ISM components (on %d PCG volumes)" % (len(a), scan["static_mesh_actors"], len(i), scan["pcg_volumes"]))
    print("INFO  actor slots by MI: %s" % dict(by_mi.most_common()))
    print("INFO  current distance values: actors %s, ISMs %s" % (dict(Counter(str(x["dist"]) for x in a)), dict(Counter(str(x["dist"]) for x in i))))


def do_apply(ed, a):
    scan = live_scan(ed, a.resume)
    summarize(scan)
    cross_check_inventory(scan["actors"])
    na, ni = len(scan["actors"]), len(scan["isms"])
    print("COUNTS: %d static-mesh actors (expected %d), %d ISM components (expected %d)" % (na, a.expect_actors, ni, a.expect_isms))
    if (na, ni) != (a.expect_actors, a.expect_isms) and not a.force_counts:
        print("STOP: the counts differ from the expectation. Nothing was written. Report the numbers; do not apply.")
        return 2
    if a.dry:
        print("DRY RUN: counts match; nothing was written.")
        return 0
    os.makedirs(os.path.dirname(TARGETS), exist_ok=True)
    with open(TARGETS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(scan, f)
    done = skipped = 0
    t0 = time.time()
    for kind in ("actors", "isms"):
        for k, t in enumerate(scan[kind]):
            if t["dist"] == DISTANCE:
                skipped += 1
                continue
            ed.setp(t["comp"], {PROP: DISTANCE})
            done += 1
            if done % 100 == 0:
                print("  wrote %d (%d skipped, already %d) [%.0fs]" % (done, skipped, DISTANCE, time.time() - t0), flush=True)
    print("wrote %d components, %d were already %d" % (done, skipped, DISTANCE))
    return do_check(ed, a, scan=scan)


def do_check(ed, a, scan=None):
    if scan is None:
        if a.rescan or not os.path.exists(TARGETS):
            scan = live_scan(ed, a.resume)
            summarize(scan)
        else:
            scan = json.load(open(TARGETS, encoding="utf-8"))
            print("INFO  using the target list written by --apply (%s); --rescan scans the level again" % TARGETS)
    na, ni = len(scan["actors"]), len(scan["isms"])
    results = [(na == a.expect_actors, "%d static-mesh actor targets (expected %d)" % (na, a.expect_actors)),
               (ni == a.expect_isms, "%d PCG ISM component targets (expected %d)" % (ni, a.expect_isms))]
    bad_a, bad_i, other_mi = [], [], []
    for kind, bad in (("actors", bad_a), ("isms", bad_i)):
        for k, t in enumerate(scan[kind]):
            try:
                d = read_dist(ed, t["comp"])
            except RuntimeError as e:
                bad.append((t["comp"], "read error " + str(e)[:80]))
                continue
            if d != DISTANCE:
                bad.append((t["comp"], d))
            if kind == "actors":
                # the effective material must still be a foliage MI (override read again)
                p = ed.props(t["comp"], ["overrideMaterials"])
                ov = [short(R(o)) for o in (p.get("overrideMaterials") or [])]
                if ov and not any(o in FOLIAGE_MIS for o in ov) and not any(e in FOLIAGE_MIS for e in t["effective"]):
                    other_mi.append(t["comp"])
            if (k + 1) % 150 == 0:
                print("  read %s %d/%d" % (kind, k + 1, len(scan[kind])), flush=True)
    results.append((not bad_a, "all %d actor components read %d (%d wrong: %s)" % (na, DISTANCE, len(bad_a), bad_a[:3])))
    results.append((not bad_i, "all %d ISM components read %d (%d wrong: %s)" % (ni, DISTANCE, len(bad_i), bad_i[:3])))
    results.append((scan.get("other_with_distance", 0) == 0, "no non-target static-mesh actor has a WPO distance (%s)" % scan.get("other_with_distance")))
    for ok, m in results:
        print(("PASS  " if ok else "FAIL  ") + m)
    fails = [m for ok, m in results if not ok]
    print("RESULT: %d PASS, %d FAIL" % (len(results) - len(fails), len(fails)))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--apply", action="store_true")
    g.add_argument("--check", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--rescan", action="store_true")
    ap.add_argument("--expect-actors", type=int, default=EXPECT_ACTORS)
    ap.add_argument("--expect-isms", type=int, default=EXPECT_ISMS)
    ap.add_argument("--force-counts", action="store_true")
    ap.add_argument("--dry", action="store_true", help="--apply: scan and print the counts, write nothing")
    a = ap.parse_args()
    try:
        ed = Ed()
        if ed.call("EditorToolset.EditorAppToolset", "IsPIERunning"):
            sys.exit("PIE is running: stop it first")
        lvl = str(ed.call(S, "get_current_level", {}))
        if not lvl.startswith("/Game/LastBell/Maps/L_Monastery"):
            sys.exit("the editor is on %s, not L_Monastery" % lvl)
        rc = do_apply(ed, a) if a.apply else do_check(ed, a)
    except EditorStop as e:
        print("STOP: editor problem (%s). Do NOT save. Restart the editor if it crashed, then run again (--resume reuses the scan)." % e)
        sys.exit(3)
    sys.exit(rc)


if __name__ == "__main__":
    main()
