"""P11-8 step 1b: one brightness correction. BrightnessMul on two material instances, nothing else.

Spec: Docs/plans/P11_MATERIALS.md, section "P11-8: close", "Step 1b: one correction". Run with -I, editor open on
L_Monastery, no PIE (every mode refuses while PIE runs). Exactly one mode per run:
    --snapshot FILE   read-only: BrightnessMul (value and whether the MI overrides it) on the targets and
                      MI_Chapel_Masonry_Interior, bWeathering on the nine MIs of set_weathering.py, the three weathering
                      amounts wherever the MI exposes them, dirty state of the watched packages
    --apply           MI_Kit_Masonry BrightnessMul 1.0 -> 1.15, MI_Env_TowerStone 0.35 -> 0.40; read back. Refuses (changes
                      nothing) if a current value is not the plan's old value (or already the new one)
    --check           read back everything; exit 1 on any mismatch (needs the snapshot, see --snap-file)
    --save            one package per save_assets call, 5 s apart: MI_Kit_Masonry, then MI_Env_TowerStone
                      (never M_LB_Surface, never a master, never a Blueprint)
    --restore         puts the snapshot's old values back (clears the override on an MI that had none). Saves nothing.
    --snap-file FILE  snapshot used by --check / --restore (default Docs/ArtTest/materials/p11_8_before.json)

Nothing saves unless --save is given. Exit codes: 0 ok, 1 mismatch or refused, 2 a tool call failed (state unknown:
run --check before anything else; never retry in a loop).
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\materials")
from ue import UE  # noqa: E402
import set_weathering as sw  # noqa: E402  (its ASSETS list: the nine wall MIs; main() is guarded)

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
MI = "editor_toolset.toolsets.material_instance.MaterialInstanceTools"
AS = "editor_toolset.toolsets.asset.AssetTools"
OB = "editor_toolset.toolsets.object.ObjectTools"
APP = "EditorToolset.EditorAppToolset"

PARAM = "BrightnessMul"
# name -> (old value from the plan, new value)
TARGETS = {"MI_Kit_Masonry": (1.0, 1.15), "MI_Env_TowerStone": (0.35, 0.40)}
UNCHANGED = {"MI_Chapel_Masonry_Interior": 0.6}   # must still read this
SAVE_ORDER = ["MI_Kit_Masonry", "MI_Env_TowerStone"]
DEFAULT_SNAP = os.path.join(ROOT, "Docs", "ArtTest", "materials", "p11_8_before.json")
PAUSE_S = 5
TOL = 1e-4

NEVER_SAVE = ["/Game/LastBell/Materials/Master/M_LB_Surface"]
EXTRA_WATCH = ["/Game/LastBell/Materials/Master/M_LB_Surface", "/Game/LastBell/Materials/Master/M_LB_Decal",
               "/Game/LastBell/Materials/Master/M_LB_Decal_Grime", "/Game/LastBell/Maps/L_Monastery"]


def pkg(name):
    return sw.BY_NAME[name][0]


def ref(name):
    return sw.ref(name)


def close(a, b, tol=TOL):
    return abs(float(a) - float(b)) <= tol


def as_json(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return v
    return v


def is_dirty(ue, p):
    if not ue.call(AS, "exists", {"path": p}):
        return None
    return ue.call(AS, "is_dirty", {"asset_path": p})


def watch_list():
    return [p for _, p, _ in sw.ASSETS] + EXTRA_WATCH


def refuse_if_pie(ue):
    if ue.call(APP, "IsPIERunning", {}):
        print("refused: PIE is running. Nothing was changed.")
        return True
    return False


def read_bm(ue, name):
    return float(ue.call(MI, "get_scalar_parameter", {"instance": ref(name), "name": PARAM}))


def bm_overridden(ue, name):
    r = as_json(ue.call(OB, "get_properties", {"instance": ref(name), "properties": ["scalarParameterValues"]}))
    return any(e["parameterInfo"]["name"] == PARAM for e in r["scalarParameterValues"])


def weathering_rows(ue):
    """set_weathering.snapshot(): bWeathering on the nine MIs, the amounts on Masonry and Trim."""
    rows = sw.snapshot(ue)
    # also the amounts on every other MI that exposes them (read-only), so a change on a child would show
    for r in rows:
        if "amounts" not in r and r["has_bWeathering"]:
            params = {p["name"] for p in ue.call(MI, "list_parameters", {"material": ref(r["name"])})}
            if all(a in params for a in sw.AMOUNTS):
                r["amounts"] = {a: sw.read_amount(ue, r["name"], a) for a in sw.AMOUNTS}
    return rows


def brightness_state(ue):
    names = list(TARGETS) + list(UNCHANGED)
    return {n: {"value": read_bm(ue, n), "overridden": bm_overridden(ue, n)} for n in names}


# ------------------------------------------------------------------ snapshot
def do_snapshot(ue, path):
    bs = brightness_state(ue)
    rows = weathering_rows(ue)
    snap = {"taken": time.strftime("%Y-%m-%d %H:%M:%S"), "note": "values read before P11-8 step 1b changed anything",
            "brightness": bs, "weathering": rows, "dirty_before": {p: is_dirty(ue, p) for p in watch_list()}}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=1)
    print("snapshot written:", path)
    for n, s in bs.items():
        print(f"  {n}.{PARAM} = {s['value']:.4f} (explicit override {s['overridden']})")
    for r in rows:
        a = r.get("amounts")
        print(f"  {r['name']:28} bWeathering {r['bWeathering']}" + (f"  amounts {a}" if a else ""))
    print("dirty before:", sorted(k.split("/")[-1] for k, v in snap["dirty_before"].items() if v) or "none")
    return 0


# ------------------------------------------------------------------ apply
def do_apply(ue):
    problems = []
    cur = {}
    for n, (old, new) in TARGETS.items():
        cur[n] = read_bm(ue, n)
        if not (close(cur[n], old) or close(cur[n], new)):
            problems.append(f"{n}.{PARAM} reads {cur[n]}, plan says {old} (or already {new})")
    for n, v in UNCHANGED.items():
        c = read_bm(ue, n)
        if not close(c, v):
            problems.append(f"{n}.{PARAM} reads {c}, expected {v} (not ours to change, but the plan's premise differs)")
    if problems:
        print("REFUSED, nothing was changed:")
        for p in problems:
            print("  -", p)
        return 1
    ok = True
    for n, (old, new) in TARGETS.items():
        ue.call(MI, "set_scalar_parameter", {"instance": ref(n), "name": PARAM, "value": new})
        back = read_bm(ue, n)
        ov = bm_overridden(ue, n)
        good = close(back, new) and ov
        ok &= good
        print(f"  {n}.{PARAM}: {cur[n]:.4f} -> want {new}, read back {back:.4f}, explicit override {ov} "
              f"{'ok' if good else 'MISMATCH'}", flush=True)
    print("apply:", "OK" if ok else "MISMATCH")
    return 0 if ok else 1


# ------------------------------------------------------------------ restore
def do_restore(ue, snap_path):
    with open(snap_path, encoding="utf-8") as f:
        snap = json.load(f)
    ok = True
    for n in TARGETS:
        s = snap["brightness"][n]
        if s["overridden"]:
            ue.call(MI, "set_scalar_parameter", {"instance": ref(n), "name": PARAM, "value": s["value"]})
        else:
            ue.call(MI, "set_parameter_override", {"instance": ref(n), "name": PARAM, "override": False})
        back = read_bm(ue, n)
        ov = bm_overridden(ue, n)
        good = close(back, s["value"]) and ov == s["overridden"]
        ok &= good
        print(f"  {n}.{PARAM}: restored to {s['value']}, read back {back:.4f}, override {ov} (was {s['overridden']}) "
              f"{'ok' if good else 'MISMATCH'}", flush=True)
    print("restore:", "OK" if ok else "MISMATCH", "(nothing saved)")
    return 0 if ok else 1


# ------------------------------------------------------------------ check
def do_check(ue, snap_path):
    with open(snap_path, encoding="utf-8") as f:
        snap = json.load(f)
    bad, n_ok = [], 0

    def rec(ok, what, line):
        nonlocal n_ok
        if ok:
            n_ok += 1
        else:
            bad.append(what)
        print(("ok   " if ok else "FAIL ") + line, flush=True)

    for n, (old, new) in TARGETS.items():
        v, ov = read_bm(ue, n), bm_overridden(ue, n)
        rec(close(v, new) and ov, f"{n}.{PARAM} {v} (want {new}, override {ov})",
            f"{n}.{PARAM} = {v:.4f} (want {new}; snapshot {snap['brightness'][n]['value']}; explicit override {ov})")
    for n, want in UNCHANGED.items():
        v, ov = read_bm(ue, n), bm_overridden(ue, n)
        so = snap["brightness"][n]
        rec(close(v, want) and close(v, so["value"]) and ov == so["overridden"],
            f"{n}.{PARAM} {v} (want {want})",
            f"{n}.{PARAM} = {v:.4f} (want {want}; snapshot {so['value']}; override {ov}, snapshot {so['overridden']})")
    now = {r["name"]: r for r in weathering_rows(ue)}
    for r0 in snap["weathering"]:
        r1 = now[r0["name"]]
        same_sw = r1["bWeathering"] == r0["bWeathering"] and r1["has_bWeathering"] == r0["has_bWeathering"]
        a0, a1 = r0.get("amounts"), r1.get("amounts")
        same_a = (a0 is None and a1 is None) or (a0 is not None and a1 is not None and
                                                  all(close(a0[k], a1[k]) for k in sw.AMOUNTS))
        txt = f"{r0['name']}: bWeathering {r1['bWeathering']} (snapshot {r0['bWeathering']})"
        if a1:
            txt += ", amounts " + "/".join(f"{a1[k]:.3f}" for k in sw.AMOUNTS) + \
                   (" (= snapshot)" if same_a else f" (snapshot {a0})")
        rec(same_sw and same_a, txt, txt)
    watch = watch_list() + [pkg(n) for n in SAVE_ORDER]
    dirty = {p.split("/")[-1]: is_dirty(ue, p) for p in dict.fromkeys(watch)}
    print("dirty now:", sorted(k for k, v in dirty.items() if v) or "none")
    print(f"CHECK: {n_ok}/{n_ok + len(bad)} items ok" + ("" if not bad else f"; {len(bad)} MISMATCH: " + "; ".join(bad)))
    return 1 if bad else 0


# ------------------------------------------------------------------ save
def do_save(ue):
    dirty_before = {p: is_dirty(ue, p) for p in [pkg(n) for n in SAVE_ORDER] + NEVER_SAVE}
    print("not saved on purpose:", {p.split("/")[-1]: dirty_before[p] for p in NEVER_SAVE})
    for i, n in enumerate(SAVE_ORDER):
        p = pkg(n)
        assert p not in NEVER_SAVE and "/BP_" not in p and "/Master/" not in p
        if i:
            time.sleep(PAUSE_S)
        res = ue.call(AS, "save_assets", {"asset_paths": [p]})
        dirty = is_dirty(ue, p)
        print(f"  save {n}: was dirty {dirty_before[p]}, returned {res}, is_dirty {dirty}", flush=True)
        if res is not True or dirty is not False:
            print(f"STOP: {n} did not save cleanly; later packages were not saved.")
            return 1
    after = {p.split("/")[-1]: is_dirty(ue, p) for p in dict.fromkeys(watch_list())}
    print("dirty after save (watch list):", sorted(k for k, v in after.items() if v) or "none")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", metavar="FILE")
    for m in ("apply", "check", "save", "restore"):
        g.add_argument("--" + m, action="store_true")
    ap.add_argument("--snap-file", default=DEFAULT_SNAP)
    a = ap.parse_args()
    ue = UE()
    try:
        if refuse_if_pie(ue):
            return 1
        if a.snapshot:
            return do_snapshot(ue, a.snapshot)
        if a.apply:
            return do_apply(ue)
        if a.restore:
            return do_restore(ue, a.snap_file)
        if a.check:
            return do_check(ue, a.snap_file)
        return do_save(ue)
    except Exception as e:
        print(f"TOOL CALL FAILED: {str(e)[:600]}\nState unknown. Run --check before doing anything else; do not retry in a loop.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
