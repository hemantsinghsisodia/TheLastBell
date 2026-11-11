"""P17-5b: the Phase 17 level edits in L_Monastery (Docs/plans/P17_CINEMATICS.md section 5).

Run with the editor open on L_Monastery, PIE off (Windows Python; from Git Bash prefix MSYS_NO_PATHCONV=1):
    python -I Tools/cine/p17_level.py --check [--out FILE]      (read only; writes the check JSON)
    python -I Tools/cine/p17_level.py --apply                   (idempotent; never saves)
    python -I Tools/cine/p17_level.py --save                    (full check first; ONE save of the map only)

What --apply does (7 items, nothing else; census 3102 -> 3103):
  1. spawns CINE_FinaleMark  (TargetPoint, (12165, 2300, 2500), yaw -90, tag LB_Cine_FinaleMark, folder Cinematics)
  2. spawns CINE_StairTop    (TargetPoint, (12165, 1665, 2730), yaw 0,   tag LB_Cine_StairTop,   folder Cinematics)
  3. adds the tag LB_Cine_Bell to the placed actor "Bell" (BP_TagInteractable_GreatBell_C); its Mesh is already Movable, so mobility is not touched
  4. TWA_Headstock (StaticMeshActor_1498): StaticMeshComponent0 mobility -> Movable, tag LB_Cine_BellHeadstock
  5. TWA_BellRope  (StaticMeshActor_1499): StaticMeshComponent0 mobility -> Movable, tag LB_Cine_BellRope
  6. Note_Gatehouse: bodyText on the actor AND on its InspectableComp -> the section 5 text (displayName unchanged)
  7. deletes the actor EndingTrigger (BP_EndingTrigger_C); the Blueprint asset and WBP_Ending are not touched

--check (read only) prints PASS / FAIL per item, writes Docs/ArtTest/cine/p17_5b_check.json (or --out) and exits 1 on any FAIL.
The lane check uses the helper-aware Tracer of Tools/cine/p17_f0_survey.py (BP_TagTrigger / Kill_Pit boxes block trace_world); the blocking
helper boxes come from Saved/p17_f0_scratch/helpers.json (computed live and cached when that file is missing).
--save runs the full check, requires the census 3103 and every never-save package clean, then saves ONLY /Game/LastBell/Maps/L_Monastery
(one save_assets call) and reads is_dirty afterwards. Never save-all; no Blueprint, level sequence or data asset is ever saved here.

If the editor crashes or a call hangs for more than 180 s the script stops ("STOP", exit code 3). Do not save and do not retry blindly.
"""
import argparse
import json
import math
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Tools", "lighting"))
sys.path.insert(0, os.path.join(ROOT, "Tools", "fx"))
sys.path.insert(0, os.path.join(ROOT, "Tools", "mcp"))
sys.path.insert(0, os.path.join(ROOT, "Tools", "cine"))
import p14_3_level as L  # noqa: E402  (the Ed client, helpers)
import p15_level as P15  # noqa: E402  (NEVER_SAVE_P158)
import p17_f0_survey as F0  # noqa: E402  (Tracer, lane_check, read-only Ed)
from p14_3_level import EditorStop, J, R, v3, near, same_rot  # noqa: E402

S, A, O, AS, E = L.S, L.A, L.O, L.AS, L.E
MAP_PKG = L.MAP_PKG
MAPPFX = MAP_PKG + ".L_Monastery:PersistentLevel."
FOLDER = "Cinematics"
CENSUS_BEFORE = 3102
CENSUS_AFTER = 3103          # +2 TargetPoints, -1 EndingTrigger
TARGET_CLASS = "/Script/Engine.TargetPoint"
BELL_CLASS = "/Game/LastBell/Blueprints/Interactables/BP_TagInteractable_GreatBell.BP_TagInteractable_GreatBell_C"
ENDING_CLASS = "/Game/LastBell/Blueprints/BP_EndingTrigger.BP_EndingTrigger_C"
NOTE_CLASS = "/Game/LastBell/Blueprints/Interactables/BP_Inspectable_Note.BP_Inspectable_Note_C"
HELPERS_JSON = os.path.join(F0.SCRATCH, "helpers.json")
DEFAULT_OUT = os.path.join(ROOT, "Docs", "ArtTest", "cine", "p17_5b_check.json")

# packages that must never be saved here (and must not be dirty when the map is saved)
NEVER_SAVE = list(P15.NEVER_SAVE_P158) + [
    "/Game/LastBell/ArtTest/P17/LS_P17_Spike",
    "/Game/LastBell/Cinematics/LS_LB_Intro",
    "/Game/LastBell/Cinematics/LS_LB_Finale",
    "/Game/LastBell/Data/DA_Cinematics",
    "/Game/LastBell/Blueprints/Interactables/BP_TagInteractable_GreatBell",
    "/Game/LastBell/Blueprints/Interactables/BP_Inspectable_Note",
]
NEVER_SAVE = list(dict.fromkeys(NEVER_SAVE))

# the owner-approved note text (plan section 5; only "has no rope and no clapper" -> "no living hand has rung")
NOTE_BODY = ("I came up the cliff path at dusk and heard it before I saw the tower. One toll, slow, from a bell the villagers swear no living hand has rung. "
             "They say it rings only for the one who is meant to hear it. I wrote this by the gate, and I am no longer sure I will leave by it.")
NOTE_NAME = "A Traveller's Note"

# the two new TargetPoints: label, location, rotation (pitch, yaw, roll), tag
POINTS = [
    ("CINE_FinaleMark", (12165.0, 2300.0, 2500.0), (0.0, -90.0, 0.0), "LB_Cine_FinaleMark"),
    ("CINE_StairTop", (12165.0, 1665.0, 2730.0), (0.0, 0.0, 0.0), "LB_Cine_StairTop"),
]
# existing actors that get a tag: tag, exact label, object name (None = look up by label only), class path, mobility target (component, "Movable") or None
TAGGED = [
    ("LB_Cine_Bell", "Bell", "BP_TagInteractable_GreatBell_C_0", BELL_CLASS, None),
    ("LB_Cine_BellHeadstock", "TWA_Headstock", "StaticMeshActor_1498", "/Script/Engine.StaticMeshActor", "StaticMeshComponent0"),
    ("LB_Cine_BellRope", "TWA_BellRope", "StaticMeshActor_1499", "/Script/Engine.StaticMeshActor", "StaticMeshComponent0"),
]
# transforms that must stay unchanged (from the F0 survey): label -> (location, rotation, scale)
UNCHANGED = {
    "Bell": ((12420.0, 2000.0, 2860.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
    "TWA_Headstock": ((12420.0, 2000.0, 2880.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
    "TWA_BellRope": ((12550.0, 1835.0, 2750.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
    "Note_Gatehouse": ((230.0, -145.0, 45.97), (0.0, 20.0, 0.0), (1.0, 1.0, 1.0)),
}
STRIKE_TAG = "LB_StrikeTarget_Tower"
STRIKE_LABEL = "FX_StrikeTarget_Tower"
ALL_TAGS = [p[3] for p in POINTS] + [t[0] for t in TAGGED] + [STRIKE_TAG]
LANE_A = (12165.0, 1665.0)      # CINE_StairTop's floor point (XY)
LANE_B = (12165.0, 2200.0)      # the stop point
LANE_FLOOR = 2500.0
MARK_FLOOR = 2500.0

results = []
detail = {}


def rec(ok, msg):
    results.append((bool(ok), msg))
    print(("PASS  " if ok else "FAIL  ") + msg, flush=True)
    return bool(ok)


def info(msg):
    print("INFO  " + msg, flush=True)


def rnd(v, n=2):
    return [round(float(x), n) for x in v]


class Ed(F0.Ed):
    """F0's read-only-retrying Ed plus the few mutating helpers this script needs."""

    def add_tag(self, ref, tag):
        cur = list(self.props(ref, ["tags"]).get("tags") or [])
        if tag in cur:
            return cur, False
        self.setp(ref, {"tags": cur + [tag]})
        return list(self.props(ref, ["tags"]).get("tags") or []), True

    def tags(self, ref):
        return list(self.props(ref, ["tags"]).get("tags") or [])

    def set_folder(self, ref, folder):
        self.call(S, "set_actor_folder", {"actor": {"refPath": ref}, "folder_path": folder})

    def folder_actors(self, folder):
        try:
            return set(R(x) for x in self.call(S, "get_actors_in_folder", {"folder_path": folder}) or [])
        except RuntimeError:
            return set()

    def census(self):
        return len(self.find_all())


def comp_ref(ref, name):
    return ref + "." + name


def mobility(ed, ref, comp):
    return str(ed.props(comp_ref(ref, comp), ["mobility"]).get("mobility"))


def find_exact(ed, label, cls=None):
    ref = ed.find_one(label)
    if ref and cls and ed.cls(ref) != cls:
        raise RuntimeError("actor %r has class %s, expected %s" % (label, ed.cls(ref), cls))
    return ref


# ---------------------------------------------------------------------------------------------- apply
def apply_points(ed):
    for label, loc, rot, tag in POINTS:
        ref, created = ed.get_or_create(TARGET_CLASS, label, loc, rot, (1, 1, 1), FOLDER)
        ed.set_xform(ref, loc, rot, (1, 1, 1))
        ed.set_folder(ref, FOLDER)
        tags, changed = ed.add_tag(ref, tag)
        l, r, s = ed.xform(ref)
        info("1/2 %s %s at %s rot %s tags %s%s" % (label, "created" if created else "already existed (updated)", rnd(l), rnd(r), tags, "" if tag in tags else "  (TAG READ-BACK MISMATCH)"))


def apply_tags_and_mobility(ed):
    for tag, label, obj, cls, mob_comp in TAGGED:
        ref = find_exact(ed, label, cls)
        if not ref:
            raise RuntimeError("actor %r not found" % label)
        if obj and not ref.endswith("." + obj):
            raise RuntimeError("actor %r is %s, expected object %s" % (label, ref.rsplit(".", 1)[-1], obj))
        tags, changed = ed.add_tag(ref, tag)
        info("3-5 %s tags %s (%s)" % (label, tags, "added " + tag if changed else tag + " already present"))
        if mob_comp:
            before = mobility(ed, ref, mob_comp)
            if before != "Movable":
                ed.setp(comp_ref(ref, mob_comp), {"mobility": "Movable"})
            after = mobility(ed, ref, mob_comp)
            info("3-5 %s.%s mobility %s -> %s" % (label, mob_comp, before, after))
        else:
            info("3-5 %s: mobility untouched; Mesh reads %s" % (label, mobility(ed, ref, "Mesh")))


def apply_note(ed):
    ref = find_exact(ed, "Note_Gatehouse", NOTE_CLASS)
    if not ref:
        raise RuntimeError("Note_Gatehouse not found")
    cref = comp_ref(ref, "InspectableComp")
    for tgt, name in ((ref, "actor"), (cref, "InspectableComp")):
        cur = ed.props(tgt, ["bodyText"])["bodyText"]
        if cur != NOTE_BODY:
            ed.setp(tgt, {"bodyText": NOTE_BODY})
        got = ed.props(tgt, ["bodyText"])["bodyText"]
        info("6 Note_Gatehouse %s bodyText %s (read back %s)" % (name, "set" if cur != NOTE_BODY else "already equal", "EXACT" if got == NOTE_BODY else "MISMATCH: %r" % got))


def apply_delete(ed):
    ref = find_exact(ed, "EndingTrigger")
    if not ref:
        info("7 EndingTrigger already absent")
        return
    cls = ed.cls(ref)
    if cls != ENDING_CLASS:
        raise RuntimeError("EndingTrigger has class %s, expected %s: not deleting" % (cls, ENDING_CLASS))
    r = ed.call(S, "remove_from_scene", {"actor": {"refPath": ref}})
    info("7 EndingTrigger (%s) removed -> %r; still found: %s" % (ref.rsplit(".", 1)[-1], r, bool(ed.find_one("EndingTrigger"))))


# ---------------------------------------------------------------------------------------------- check
def tracer_for(ed):
    if os.path.exists(HELPERS_JSON):
        helpers = json.load(open(HELPERS_JSON, encoding="utf-8"))
        info("helper volumes from %s (%d blocking: %s)" % (HELPERS_JSON, len(helpers["blocking"]), helpers["blocking"]))
    else:
        info("helpers.json missing: computing the blocking helper volumes live")
        helpers = F0.stage_helpers(ed)
        os.makedirs(F0.SCRATCH, exist_ok=True)
        json.dump(helpers, open(HELPERS_JSON, "w", encoding="utf-8"), indent=1)
    return F0.make_tracer(ed, helpers)


def check_census(ed):
    n = ed.census()
    detail["census"] = n
    rec(n == CENSUS_AFTER, "census: actor count %d (expected %d = %d + 2 - 1)" % (n, CENSUS_AFTER, CENSUS_BEFORE))
    fs = ed.folder_actors(FOLDER)
    labels = sorted(ed.label(r) for r in fs)
    rec(labels == sorted(p[0] for p in POINTS), "outliner folder %s holds exactly %s (found %s)" % (FOLDER, [p[0] for p in POINTS], labels))
    return n


def check_points(ed):
    fs = ed.folder_actors(FOLDER)
    for label, loc, rot, tag in POINTS:
        ref = ed.find_one(label)
        if not ref:
            rec(False, "%s exists" % label)
            continue
        l, r, s = ed.xform(ref)
        tags = ed.tags(ref)
        cls = ed.cls(ref)
        ok = near(l, loc, 0.01) and same_rot(r, rot) and near(s, (1, 1, 1), 1e-6) and tags == [tag] and cls == TARGET_CLASS and ref in fs
        rec(ok, "%s: %s at %s rot %s scale %s tags %s folder %s" % (label, cls.rsplit(".", 1)[-1], rnd(l), rnd(r), rnd(s), tags, FOLDER if ref in fs else "NOT-IN-FOLDER"))


def check_tags(ed):
    detail["tags"] = {}
    expect = {p[3]: p[0] for p in POINTS}
    expect.update({t[0]: t[1] for t in TAGGED})
    expect[STRIKE_TAG] = STRIKE_LABEL
    for tag in ALL_TAGS:
        hits = ed.find_all(tag=tag)
        labels = [ed.label(r) for r in hits]
        detail["tags"][tag] = labels
        rec(labels == [expect[tag]], "tag %s is on exactly one actor: %s (expected [%s])" % (tag, labels, expect[tag]))
    for tag, label, obj, cls, mob in TAGGED:
        ref = ed.find_one(label)
        if ref:
            rec(ed.cls(ref) == cls and ref.endswith("." + obj), "%s is %s of class %s" % (label, ref.rsplit(".", 1)[-1], ed.cls(ref).rsplit(".", 1)[-1]))


def check_mark_floor(ed, tr):
    mark = [p for p in POINTS if p[0] == "CINE_FinaleMark"][0][1]
    z = tr.down(mark[0], mark[1], mark[2] + 100.0, depth=300.0)
    detail["mark_floor"] = {"from": [mark[0], mark[1], mark[2] + 100.0], "floor_z": None if z is None else round(z, 2)}
    rec(z is not None and abs(z - MARK_FLOOR) <= 2.0,
        "the mark is on the floor: downward trace from Z %.0f at (%.0f, %.0f) hits at Z %s (floor %.0f, tolerance 2 cm)" % (mark[2] + 100.0, mark[0], mark[1], "none" if z is None else "%.2f" % z, MARK_FLOOR))


def check_lane(ed, tr):
    lane = F0.lane_check(ed, tr, LANE_A, LANE_B, LANE_FLOOR)
    detail["lane"] = {"from": [LANE_A[0], LANE_A[1], LANE_FLOOR], "to": [LANE_B[0], LANE_B[1], LANE_FLOOR], "radius_cm": 42, "traces": lane,
                      "tracer_raw_calls": tr.n_raw, "tracer_helper_volume_steps": tr.n_skip}
    for t in lane:
        print("      trace side %+4.0f cm  height %3.0f cm  length %6.1f  hit %s  -> %s%s" % (
            t["side_cm"], t["height_above_floor"], t["length"], "none" if t["hit_distance"] is None else "%.1f" % t["hit_distance"],
            "clear" if t["clear"] else "BLOCKED", "" if t["clear"] else "  at %s by %s" % (t.get("hit_point"), t.get("hit_actors"))), flush=True)
    bad = [t for t in lane if not t["clear"]]
    rec(len(lane) == 9 and not bad,
        "lane (12165, 1665, 2500) -> (12165, 2200, 2500), Warden radius 42: %d of 9 traces clear (lateral -42/0/+42, heights 20/110/200)" % (len(lane) - len(bad)))


def check_mobility(ed):
    detail["mobility"] = {}
    ref = ed.find_one("Bell")
    pairs = [("Bell.Mesh", ref, "Mesh")]
    for tag, label, obj, cls, mob in TAGGED[1:]:
        pairs.append(("%s.%s" % (label, mob), ed.find_one(label), mob))
    for name, r, comp in pairs:
        if not r:
            rec(False, "%s is Movable (actor missing)" % name)
            continue
        m = mobility(ed, r, comp)
        detail["mobility"][name] = m
        rec(m == "Movable", "%s mobility reads %s" % (name, m))


def check_ending_absent(ed):
    hits = ed.find(label="EndingTrigger")
    cls = [r for r in ed.find_cls(ENDING_CLASS)]
    rec(not hits and not cls, "EndingTrigger is absent (label matches %d, BP_EndingTrigger_C actors %d)" % (len(hits), len(cls)))


def check_note(ed):
    ref = ed.find_one("Note_Gatehouse")
    if not ref:
        rec(False, "Note_Gatehouse exists")
        return
    detail["note"] = {}
    for tgt, name in ((ref, "actor"), (comp_ref(ref, "InspectableComp"), "InspectableComp")):
        p = ed.props(tgt, ["displayName", "bodyText"])
        detail["note"][name] = {"displayName": p["displayName"], "bodyText": p["bodyText"]}
        rec(p["bodyText"] == NOTE_BODY, "Note_Gatehouse %s bodyText equals the section 5 text exactly (%d chars)%s" % (
            name, len(p["bodyText"]), "" if p["bodyText"] == NOTE_BODY else ": %r" % p["bodyText"]))
        rec(p["displayName"] == NOTE_NAME, "Note_Gatehouse %s displayName unchanged: %r" % (name, p["displayName"]))


def check_unchanged(ed):
    for label, (loc, rot, sc) in UNCHANGED.items():
        ref = ed.find_one(label)
        if not ref:
            rec(False, "%s exists" % label)
            continue
        l, r, s = ed.xform(ref)
        rec(near(l, loc, 0.05) and same_rot(r, rot) and near(s, sc, 1e-6), "%s transform unchanged: %s rot %s scale %s" % (label, rnd(l), rnd(r), rnd(s)))


def packages_dirty(ed):
    out = {}
    for pkg in NEVER_SAVE:
        try:
            out[pkg] = ed.is_dirty(pkg)
        except RuntimeError as e:
            out[pkg] = "unreadable: %s" % str(e)[:80]
    return out


def check_dirty(ed):
    d = ed.is_dirty(MAP_PKG)
    detail["map_dirty"] = d
    info("%s is_dirty = %s" % (MAP_PKG, d))
    pk = packages_dirty(ed)
    detail["never_save_dirty"] = pk
    for pkg, v in pk.items():
        rec(v is False, "%s is not dirty (never-save list)%s" % (pkg.rsplit("/", 1)[-1], "" if v is False else ": %s" % v))
    return d


def run_checks(ed):
    tr = tracer_for(ed)
    print("=== census", flush=True)
    check_census(ed)
    print("=== new TargetPoints", flush=True)
    check_points(ed)
    print("=== tags", flush=True)
    check_tags(ed)
    print("=== mark on the floor", flush=True)
    check_mark_floor(ed, tr)
    print("=== lane", flush=True)
    check_lane(ed, tr)
    print("=== mobility", flush=True)
    check_mobility(ed)
    print("=== EndingTrigger", flush=True)
    check_ending_absent(ed)
    print("=== Note_Gatehouse", flush=True)
    check_note(ed)
    print("=== untouched transforms", flush=True)
    check_unchanged(ed)
    print("=== dirty state", flush=True)
    check_dirty(ed)


def write_json(path, stage):
    fails = [m for ok, m in results if not ok]
    out = {"script": "Tools/cine/p17_level.py", "stage": stage, "generated": time.strftime("%Y-%m-%d %H:%M"), "level": MAP_PKG,
           "pass": len(results) - len(fails), "fail": len(fails), "results": [{"ok": ok, "msg": m} for ok, m in results], "detail": detail}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1)
    info("wrote %s" % path)


def do_save(ed):
    print("=== save: full check first", flush=True)
    run_checks(ed)
    fails = [m for ok, m in results if not ok]
    if fails:
        print("REFUSED: the check is not all PASS; nothing saved")
        return False
    pk = packages_dirty(ed)
    dirty = [p for p, v in pk.items() if v is not False]
    if dirty:
        print("STOP: these packages are dirty or unreadable, nothing saved: %s" % dirty)
        return False
    if not ed.is_dirty(MAP_PKG):
        info("the map is not dirty: nothing to save")
        return True
    r = ed.call(AS, "save_assets", {"asset_paths": [MAP_PKG]})
    d = ed.is_dirty(MAP_PKG)
    detail["save"] = {"save_assets_result": r, "map_dirty_after": d}
    rec(d is False, "saved %s (save_assets -> %s); is_dirty after = %s" % (MAP_PKG, r, d))
    pk = packages_dirty(ed)
    detail["never_save_dirty_after_save"] = pk
    for pkg, v in pk.items():
        rec(v is False, "%s still not dirty after the save" % pkg.rsplit("/", 1)[-1])
    return True


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--apply", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--save", action="store_true")
    ap.add_argument("--out", default=DEFAULT_OUT, help="--check / --save: where to write the check JSON")
    ap.add_argument("--stage", default="", help="label stored in the JSON")
    a = ap.parse_args()
    try:
        ed = Ed()
        if ed.call(E, "IsPIERunning"):
            sys.exit("PIE is running: stop it first")
        lvl = str(ed.call(S, "get_current_level", {}))
        if not lvl.startswith(MAP_PKG):
            sys.exit("the editor is on %s, not L_Monastery" % lvl)
        n0 = ed.census()
        info("preflight: PIE off; %s is_dirty = %s; actor census = %d" % (MAP_PKG, ed.is_dirty(MAP_PKG), n0))
        detail["census_at_start"] = n0
        if a.apply:
            for name, fn in (("points", apply_points), ("tags and mobility", apply_tags_and_mobility), ("note", apply_note), ("delete", apply_delete)):
                print("=== apply %s" % name, flush=True)
                fn(ed)
            info("census after apply: %d (expected %d); map is_dirty: %s" % (ed.census(), CENSUS_AFTER, ed.is_dirty(MAP_PKG)))
            print("=== verifying (check)", flush=True)
            run_checks(ed)
        elif a.check:
            run_checks(ed)
            write_json(a.out, a.stage or "check")
        else:
            ok = do_save(ed)
            write_json(a.out, a.stage or "save")
            if not ok:
                sys.exit(2)
        info("%d editor calls" % ed.calls)
    except EditorStop as e:
        print("STOP: editor problem (%s). Do NOT save." % e)
        sys.exit(3)
    fails = [m for ok, m in results if not ok]
    print("\nRESULT: %d PASS, %d FAIL" % (len(results) - len(fails), len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
