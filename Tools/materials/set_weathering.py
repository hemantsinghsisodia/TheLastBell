"""P11-5c: roll the weathering layer out to the wall material instances, and tune it.

Spec: Docs/plans/P11_MATERIALS.md, section "P11-5c". Run with -I, editor open on L_Monastery, no PIE.

Modes (exactly one per run):
    --check [--expect on|off] [--snapshot FILE]
                        read-only table: bWeathering on the nine MIs, the three amounts on Masonry and Trim.
                        Exit 1 if a switch differs from the expected state (default: on).
    --on                CarveDirt false, Masonry true, Trim true (read back after each, 5 s apart), then --check --expect on
    --off               the undo, reverse order, then --check --expect off
    --values K=V ...    GrimeBaseAmount / StreakAmount / PatchAmount, same value on Masonry and Trim, read back
    --save              save CarveDirt, Masonry, Trim, one package per save_assets call, is_dirty checked after each

Nothing here saves unless --save is given. Exit codes: 0 ok, 1 mismatch or refused, 2 a tool call failed (state
unknown: run --check before anything else; never retry in a loop).
"""
import argparse
import json
import sys
import time

sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE  # noqa: E402

MI = "editor_toolset.toolsets.material_instance.MaterialInstanceTools"
AS = "editor_toolset.toolsets.asset.AssetTools"

ENV = "/Game/LastBell/Environments"
SWITCH = "bWeathering"
AMOUNTS = ["GrimeBaseAmount", "StreakAmount", "PatchAmount"]
RANGES = {"GrimeBaseAmount": (0.2, 0.6), "StreakAmount": (0.15, 0.45), "PatchAmount": (0.1, 0.5)}
PAUSE_S = 5

# name, package path, role. "set" = we write the switch; "inherits" = child of a set MI, never written;
# "control" = not touched, must stay false.
ASSETS = [
    ("MI_Kit_Masonry", f"{ENV}/Kit/Materials/MI_Kit_Masonry", "set"),
    ("MI_Kit_Trim", f"{ENV}/Kit/Materials/MI_Kit_Trim", "set"),
    ("MI_Cl_CarveDirt", f"{ENV}/Cloister/Materials/MI_Cl_CarveDirt", "set"),
    ("MI_Chapel_Masonry_Interior", f"{ENV}/Chapel/Materials/MI_Chapel_Masonry_Interior", "inherits"),
    ("MI_Env_TowerStone", f"{ENV}/Courtyard/Materials/MI_Env_TowerStone", "inherits"),
    ("MI_Chapel_Trim_Dusty", f"{ENV}/Chapel/Materials/MI_Chapel_Trim_Dusty", "inherits"),
    ("MI_Kit_Rubble", f"{ENV}/Kit/Materials/MI_Kit_Rubble", "control"),
    ("MI_Crypt_StoneWA", f"{ENV}/Crypt/Materials/MI_Crypt_StoneWA", "control"),
    ("MI_Kit_Floor", f"{ENV}/Kit/Materials/MI_Kit_Floor", "control"),
]
BY_NAME = {n: (p, r) for n, p, r in ASSETS}
AMOUNT_ASSETS = ["MI_Kit_Masonry", "MI_Kit_Trim"]

# Order of the three writes for --on; --off uses the reverse.
ON_ORDER = [("MI_Cl_CarveDirt", False), ("MI_Kit_Masonry", True), ("MI_Kit_Trim", True)]
# Expected effective bWeathering after --on. Everything not listed is false.
EXPECT_ON = {"MI_Kit_Masonry", "MI_Kit_Trim", "MI_Chapel_Masonry_Interior", "MI_Env_TowerStone",
             "MI_Chapel_Trim_Dusty"}
SAVE_ORDER = ["MI_Cl_CarveDirt", "MI_Kit_Masonry", "MI_Kit_Trim"]


def ref(name):
    p = BY_NAME[name][0]
    return {"refPath": f"{p}.{name}"}


def expected(name, state):
    return state == "on" and name in EXPECT_ON


def has_param(ue, name):
    """True/False whether the instance exposes bWeathering at all (an absent parameter reads as false)."""
    ps = ue.call(MI, "list_parameters", {"material": ref(name)})
    return any(p.get("name") == SWITCH and p.get("type") == "StaticSwitch" for p in ps)


def read_switch(ue, name):
    return bool(ue.call(MI, "get_static_switch_parameter", {"instance": ref(name), "name": SWITCH}))


def read_amount(ue, name, param):
    return float(ue.call(MI, "get_scalar_parameter", {"instance": ref(name), "name": param}))


def snapshot(ue):
    """Read the table data. Only values actually read are stored."""
    rows = []
    for name, path, role in ASSETS:
        row = {"name": name, "path": path, "role": role}
        row["has_bWeathering"] = has_param(ue, name)
        row["bWeathering"] = read_switch(ue, name) if row["has_bWeathering"] else None
        if name in AMOUNT_ASSETS:
            row["amounts"] = {a: read_amount(ue, name, a) for a in AMOUNTS}
        rows.append(row)
    return rows


def print_table(rows, state):
    hdr = f"{'MI':28} {'role':9} {'param':8} {'bWeathering':12} {'expected':9} {'Grime':>6} {'Streak':>6} {'Patch':>6}  note"
    print(hdr)
    print("-" * len(hdr))
    bad = []
    for r in rows:
        want = expected(r["name"], state)
        if not r["has_bWeathering"]:
            val, exp, note = "absent", "-", "no bWeathering parameter (not a failure)"
        else:
            val, exp = str(r["bWeathering"]).lower(), str(want).lower()
            note = ""
            if r["role"] == "inherits":
                note = "inherited value, read through get_static_switch_parameter"
            if r["bWeathering"] != want:
                note = ("MISMATCH " + note).strip()
                bad.append(r["name"])
        a = r.get("amounts")
        g, s, p = (f"{a[k]:.3f}" for k in AMOUNTS) if a else ("-", "-", "-")
        print(f"{r['name']:28} {r['role']:9} {'yes' if r['has_bWeathering'] else 'no':8} {val:12} {exp:9} {g:>6} {s:>6} {p:>6}  {note}")
    print(f"expected state: {state.upper()}  ->  " + ("OK" if not bad else "MISMATCH on " + ", ".join(bad)))
    return bad


def do_check(ue, state, snap_file=None):
    rows = snapshot(ue)
    bad = print_table(rows, state)
    if snap_file:
        with open(snap_file, "w", encoding="utf-8") as f:
            json.dump({"expected_state": state, "rows": rows}, f, indent=1)
        print("snapshot written:", snap_file)
    return 1 if bad else 0


def set_and_verify(ue, name, value):
    ue.call(MI, "set_static_switch_parameter", {"instance": ref(name), "name": SWITCH, "value": value})
    back = read_switch(ue, name)
    print(f"  {name}.{SWITCH} <- {str(value).lower()}, read back {str(back).lower()}", flush=True)
    return back == value


def do_switches(ue, order, state):
    for i, (name, value) in enumerate(order):
        if i:
            print(f"  waiting {PAUSE_S} s", flush=True)
            time.sleep(PAUSE_S)
        if not set_and_verify(ue, name, value):
            print(f"STOP: read-back mismatch on {name}; nothing further was changed. Run --check.")
            return 1
    print()
    return do_check(ue, state)


def parse_values(items):
    out = {}
    for it in items:
        k, sep, v = it.partition("=")
        if not sep or k not in RANGES:
            raise SystemExit(f"refused: '{it}' is not one of {', '.join(f'{a}=x' for a in AMOUNTS)}")
        try:
            out[k] = float(v)
        except ValueError:
            raise SystemExit(f"refused: '{it}' is not a number")
        lo, hi = RANGES[k]
        if not lo <= out[k] <= hi:
            raise SystemExit(f"refused: {k}={out[k]} is outside {lo}-{hi}; nothing was changed")
    return out


def do_values(ue, vals):
    ok = True
    for name in AMOUNT_ASSETS:
        for k, v in vals.items():
            ue.call(MI, "set_scalar_parameter", {"instance": ref(name), "name": k, "value": v})
            back = read_amount(ue, name, k)
            good = abs(back - v) < 1e-4
            ok &= good
            print(f"  {name}.{k} <- {v}, read back {back:.4f} {'' if good else 'MISMATCH'}")
    return 0 if ok else 1


def do_save(ue):
    for name in SAVE_ORDER:
        pkg = BY_NAME[name][0]
        res = ue.call(AS, "save_assets", {"asset_paths": [pkg]})
        dirty = ue.call(AS, "is_dirty", {"asset_path": pkg})
        print(f"  save {name}: returned {res}, is_dirty {dirty}", flush=True)
        if res is not True or dirty is not False:
            print(f"STOP: {name} did not save cleanly; later packages were not saved.")
            return 1
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--on", action="store_true")
    g.add_argument("--off", action="store_true")
    g.add_argument("--values", nargs="+", metavar="NAME=VALUE")
    g.add_argument("--save", action="store_true")
    ap.add_argument("--expect", choices=["on", "off"], default="on", help="with --check (default on)")
    ap.add_argument("--snapshot", metavar="FILE", help="with --check: also write the table data as JSON")
    a = ap.parse_args()
    vals = parse_values(a.values) if a.values else None  # validates before the editor is touched
    ue = UE()
    try:
        if a.check:
            return do_check(ue, a.expect, a.snapshot)
        if a.on:
            return do_switches(ue, ON_ORDER, "on")
        if a.off:
            return do_switches(ue, list(reversed([(n, False) for n, _ in ON_ORDER])), "off")
        if vals is not None:
            return do_values(ue, vals)
        return do_save(ue)
    except Exception as e:  # a tool call failed or timed out: state unknown
        print(f"TOOL CALL FAILED: {str(e)[:600]}\nState unknown. Run --check before doing anything else; do not retry in a loop.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
