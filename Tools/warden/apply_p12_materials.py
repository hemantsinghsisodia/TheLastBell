"""P12 Warden materials (round 1 values, reapplied on the owner's V5.5 build, D-091): scalar parameters on three parents,
four MIs, slot assignment, Cloth Brightness.

Spec: Docs/plans/P12_WARDEN_VISUAL.md, sections "P12-7 round 1: materials" and "Bringing in V5.5" step 4. Run with -I,
editor open on L_Monastery, no PIE.

V5.5 differences from V5: M_Warden_BellMetal, M_Warden_RustedIron and M_Warden_ChainIron are the owner's V5.1 materials
(no tuning parameters, so --parents adds BaseColorMul / MetallicMul / RoughnessMul, default 1). M_Warden_Skin is the V5.4
material and already has a `Skin Brightness` scalar (default 0.14): NO parameter is added to it; MI_Warden_Skin sets
Skin Brightness 0.12.
Exactly one mode per run:
    --snapshot FILE     read-only: each slot's material, MI_Warden_Wool parameters, parents' output wiring, mesh bounds/LODs,
                        which of the new assets exist, dirty state of the watch list, and every scalar of each existing
                        MI_Warden_* (so a run before a delete records the old tuned values)
    --parents [NAMES]   rewire the parents (default the three; or a comma list such as M_Warden_BellMetal): for each output named
                        in the plan, <old feeder> -> Multiply(A) x ScalarParameter(B, default 1) -> output; recompile; read the
                        wiring back. Idempotent (a parameter that already exists is not added again). Stops at the first failure.
    --apply             --parents (all three, BellMetal first), then create the four MIs, set the table values, assign the MIs
                        to the slots by slot name, set MI_Warden_Wool Cloth Brightness to 0.25; read everything back
    --check             read back everything; exit 1 on any mismatch (needs the snapshot, see --snap-file)
    --save              one package per save_assets call, 5 s apart: 3 parents, 4 new MIs, MI_Warden_Wool, SK_Warden.
                        Never M_LB_Surface, a map or a Blueprint.
    --restore           puts every slot back on the snapshot's material and Cloth Brightness back to the snapshot value; read back.
                        Saves nothing. The parameters added to the parents stay (default 1 = same look); the new MIs stay unused.
    --snap-file FILE    snapshot used by --apply / --check / --restore (default Docs/ArtTest/warden/p12_v5_5_new_before.json:
                        the state after the V5.5 move and before --apply; Docs/ArtTest/warden/p12_v5_5_before.json is the
                        record of the OLD V5 tuned values, taken before the delete)

Nothing saves unless --save is given. Exit codes: 0 ok, 1 mismatch or refused, 2 a tool call failed (state unknown:
run --check before anything else; never retry in a loop).
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE  # noqa: E402

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
MT = "editor_toolset.toolsets.material.MaterialTools"
MI = "editor_toolset.toolsets.material_instance.MaterialInstanceTools"
AS = "editor_toolset.toolsets.asset.AssetTools"
OB = "editor_toolset.toolsets.object.ObjectTools"
SK = "editor_toolset.toolsets.skeletal_mesh.SkeletalMeshTools"
APP = "EditorToolset.EditorAppToolset"

MAT_DIR = "/Game/LastBell/Characters/Warden/Materials"
MESH_PKG = "/Game/LastBell/Characters/Warden/Meshes/SK_Warden"
DEFAULT_SNAP = os.path.join(ROOT, "Docs", "ArtTest", "warden", "p12_v5_5_new_before.json")
PAUSE_S = 5
GROUP = "Warden Tuning"

# parent -> list of (parameter, material property it multiplies)
PARENT_PARAMS = {
    "M_Warden_BellMetal": [("BaseColorMul", "MP_BaseColor"), ("MetallicMul", "MP_Metallic"), ("RoughnessMul", "MP_Roughness")],
    "M_Warden_RustedIron": [("BaseColorMul", "MP_BaseColor")],
    "M_Warden_ChainIron": [("BaseColorMul", "MP_BaseColor")],
}
PARENT_ORDER = ["M_Warden_BellMetal", "M_Warden_RustedIron", "M_Warden_ChainIron"]
# V5.4 skin parent: already has its own brightness scalar; nothing is added to it, its wiring must stay as snapshotted
SKIN_PARENT = "M_Warden_Skin"
SKIN_PARAM = "Skin Brightness"
SKIN_DEFAULT = 0.14
SNAP_PARENT_PROPS = dict(PARENT_PARAMS, **{SKIN_PARENT: [(SKIN_PARAM, "MP_BaseColor")]})
OLD_MI_NAMES = ["MI_Warden_BellMetal", "MI_Warden_Skin", "MI_Warden_RustedIron", "MI_Warden_ChainIron", "MI_Warden_Wool"]

# new MI -> (parent, {parameter: value}); the table in the plan
NEW_MIS = {
    "MI_Warden_BellMetal": ("M_Warden_BellMetal", {"BaseColorMul": 1.6, "MetallicMul": 0.35, "RoughnessMul": 0.85}),
    "MI_Warden_Skin": ("M_Warden_Skin", {"Skin Brightness": 0.12}),
    "MI_Warden_RustedIron": ("M_Warden_RustedIron", {"BaseColorMul": 0.6}),
    "MI_Warden_ChainIron": ("M_Warden_ChainIron", {"BaseColorMul": 0.5}),
}
# mesh slot -> material the slot must hold after --apply
SLOT_TARGET = {
    "M_Warden_Wool": "MI_Warden_Wool",
    "M_Warden_BellMetal": "MI_Warden_BellMetal",
    "M_Warden_RustedIron": "MI_Warden_RustedIron",
    "M_Warden_Skin": "MI_Warden_Skin",
    "M_Warden_Leather": "M_Warden_Leather",
    "M_Warden_ChainIron": "MI_Warden_ChainIron",
}
WOOL_MI = "MI_Warden_Wool"
CLOTH = 0.25

NEVER_SAVE = ["/Game/LastBell/Materials/Master/M_LB_Surface"]
MAPS_DIR = "/Game/LastBell/Maps"
SAVE_ORDER = ([f"{MAT_DIR}/{p}" for p in PARENT_ORDER] + [f"{MAT_DIR}/{n}" for n in NEW_MIS] + [f"{MAT_DIR}/{WOOL_MI}", MESH_PKG])


def pkg(name):
    return f"{MAT_DIR}/{name}"


def ref(p):
    return {"refPath": f"{p}.{p.split('/')[-1]}"}


def close(a, b, tol=1e-4):
    return abs(float(a) - float(b)) <= tol


def as_json(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return v
    return v


def short(r):
    if isinstance(r, dict):
        r = r.get("refPath")
    return r.split("/")[-1].split(".")[0] if r else None


def full(r):
    return r.get("refPath") if isinstance(r, dict) else r


def expr_name(r):
    p = full(r)
    return p.split(":")[-1] if p and p != "None" else None


def is_dirty(ue, p):
    if not ue.call(AS, "exists", {"path": p}):
        return None
    return ue.call(AS, "is_dirty", {"asset_path": p})


def watch_list(ue):
    maps = list(ue.call(AS, "find_assets", {"folder_path": MAPS_DIR, "name": ""}))
    return NEVER_SAVE + maps


def refuse_if_pie(ue):
    if ue.call(APP, "IsPIERunning", {}):
        print("refused: PIE is running. Nothing was changed.")
        return True
    return False


# ------------------------------------------------------------------ reading
def slot_materials(ue):
    m = ref(MESH_PKG)
    slots = list(ue.call(SK, "get_material_slots", {"mesh": m}))
    return slots, {s: full(ue.call(SK, "get_material", {"mesh": m, "slot_name": s})) for s in slots}


def mesh_geometry(ue):
    m = ref(MESH_PKG)
    b = ue.call(SK, "get_bounds", {"mesh": m})
    lods = ue.call(SK, "get_lod_count", {"mesh": m})
    return {"bounds_origin": [b["origin"][k] for k in "xyz"], "bounds_extent": [b["boxExtent"][k] for k in "xyz"],
            "lod_count": lods, "lod_vertices": [ue.call(SK, "get_vertex_count", {"mesh": m, "lod_index": i}) for i in range(lods)]}


def param_names(ue, mat_name):
    return {p["name"] for p in ue.call(MI, "list_parameters", {"material": ref(pkg(mat_name))})}


def prop_input(ue, mat_name, prop):
    r = ue.call(MT, "get_property_input", {"material": ref(pkg(mat_name)), "material_property": prop})
    return expr_name(r["expression"]), r["output_name"]


def mi_scalar_state(ue, mi_name, param):
    """(value, explicitly overridden)."""
    v = ue.call(MI, "get_scalar_parameter", {"instance": ref(pkg(mi_name)), "name": param})
    r = as_json(ue.call(OB, "get_properties", {"instance": ref(pkg(mi_name)), "properties": ["scalarParameterValues"]}))
    ov = any(e["parameterInfo"]["name"] == param for e in r["scalarParameterValues"])
    return v, ov


def wiring_snapshot(ue):
    out = {}
    for mat, plist in SNAP_PARENT_PROPS.items():
        out[mat] = {prop: list(prop_input(ue, mat, prop)) for _, prop in plist}
        out[mat]["parameters"] = sorted(param_names(ue, mat))
    out["M_Warden_Leather"] = {"parameters": sorted(param_names(ue, "M_Warden_Leather"))}
    return out


def instance_values(ue):
    """Every existing MI_Warden_*: parent and each scalar parameter with its explicit-override flag."""
    out = {}
    for n in OLD_MI_NAMES:
        if not ue.call(AS, "exists", {"path": pkg(n)}):
            continue
        par = short(as_json(ue.call(OB, "get_properties", {"instance": ref(pkg(n)), "properties": ["parent"]}))["parent"])
        vals = {}
        for p in ue.call(MI, "list_parameters", {"material": ref(pkg(n))}):
            if "scalar" in str(p.get("type", "")).lower():
                vals[p["name"]] = list(mi_scalar_state(ue, n, p["name"]))
        out[n] = {"parent": par, "scalars": vals}
    return out


# ------------------------------------------------------------------ snapshot
def do_snapshot(ue, path):
    slots, mats = slot_materials(ue)
    wool = {}
    for k in ("Detail Strength", "Weave Scale", "Wetness", "Cloth Brightness"):
        wool[k] = list(mi_scalar_state(ue, WOOL_MI, k))
    snap = {"taken": time.strftime("%Y-%m-%d %H:%M:%S"), "note": "values read before P12-7 round 1 changed anything",
            "mesh": MESH_PKG, "slots": slots, "slot_materials": mats, "wool_before": wool,
            "cloth_brightness_before": wool["Cloth Brightness"][0], "geometry": mesh_geometry(ue),
            "parents_before": wiring_snapshot(ue), "instances_before": instance_values(ue),
            "new_assets_exist": {n: bool(ue.call(AS, "exists", {"path": pkg(n)})) for n in NEW_MIS}}
    wl = watch_list(ue) + SAVE_ORDER
    snap["dirty_before"] = {p: is_dirty(ue, p) for p in wl}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=1)
    print("snapshot written:", path)
    for s in slots:
        print(f"  slot {s} -> {short(mats[s])}")
    print("  Cloth Brightness:", snap["cloth_brightness_before"], "| geometry:", snap["geometry"])
    print("  parents before:", json.dumps(snap["parents_before"]))
    for n, d in snap["instances_before"].items():
        print(f"  existing {n} (parent {d['parent']}): {json.dumps(d['scalars'])}")
    print("  dirty before:", sorted(short(k) for k, v in snap["dirty_before"].items() if v) or "none")
    return 0


# ------------------------------------------------------------------ parents
def new_expr(ue, mat_ref, cls, x, y):
    r = ue.call(MT, "add_expression", {"material_or_function": mat_ref, "expression_class": {"refPath": f"/Script/Engine.{cls}"}, "x": x, "y": y})
    if isinstance(r, str):
        r = as_json(r)
    return r


def verify_parent_prop(ue, mat, param, prop, feeder):
    """feeder = (expression name, output name) read BEFORE the change. True when the new chain is
    feeder -> Multiply.A, ScalarParameter(param, default 1) -> Multiply.B, Multiply -> output."""
    m = ref(pkg(mat))
    mul, outn = prop_input(ue, mat, prop)
    if not mul or "Multiply" not in mul:
        print(f"    FAIL {mat} {prop}: output is fed by {mul}, not a Multiply")
        return False
    mref = {"refPath": f"{pkg(mat)}.{mat}:{mul}"}
    ins = {i["input_name"]: i for i in ue.call(MT, "get_expression_inputs", {"material_or_function": m, "expression": mref})}
    a, b = ins.get("A"), ins.get("B")
    a_ok = a and expr_name(a["expression"]) == feeder[0] and a["output_name"] == feeder[1]
    sp_name = expr_name(b["expression"]) if b else None
    sp_ok = False
    pv = None
    if sp_name and "ScalarParameter" in sp_name:
        sp = {"refPath": f"{pkg(mat)}.{mat}:{sp_name}"}
        pv = as_json(ue.call(OB, "get_properties", {"instance": sp, "properties": ["ParameterName", "DefaultValue"]}))
        sp_ok = pv["ParameterName"] == param and close(pv["DefaultValue"], 1.0)
    # the Multiply must not carry constants that change the value
    mp = as_json(ue.call(OB, "get_properties", {"instance": mref, "properties": ["ConstA", "ConstB"]}))
    ok = bool(a_ok and sp_ok)
    print(f"    {'ok  ' if ok else 'FAIL'} {mat} {prop}: {feeder[0]}.{feeder[1]} -> {mul}.A | {sp_name} ({pv['ParameterName'] if pv else None}, "
          f"default {pv['DefaultValue'] if pv else None}) -> {mul}.B | {mul} -> {prop}  (ConstA {mp.get('ConstA')}, ConstB {mp.get('ConstB')}, unused when pins wired)", flush=True)
    return ok


def do_parents(ue, names):
    for mat in names:
        m = ref(pkg(mat))
        changed = False
        for param, prop in PARENT_PARAMS[mat]:
            if param in param_names(ue, mat):
                print(f"  {mat}: {param} already exists, not added again", flush=True)
                continue
            feeder = prop_input(ue, mat, prop)
            if not feeder[0]:
                print(f"STOP: {mat} {prop} has no feeder.")
                return 1
            fref = {"refPath": f"{pkg(mat)}.{mat}:{feeder[0]}"}
            pos = as_json(ue.call(OB, "get_properties", {"instance": fref, "properties": ["MaterialExpressionEditorX", "MaterialExpressionEditorY"]}))
            x, y = int(pos["MaterialExpressionEditorX"]) + 300, int(pos["MaterialExpressionEditorY"])
            mul = new_expr(ue, m, "MaterialExpressionMultiply", x + 200, y)
            sp = new_expr(ue, m, "MaterialExpressionScalarParameter", x, y + 140)
            ue.call(OB, "set_properties", {"instance": sp, "values": json.dumps({"ParameterName": param, "DefaultValue": 1.0, "Group": GROUP})})
            ue.call(MT, "connect_expressions", {"from_expression": fref, "from_output_name": feeder[1], "to_expression": mul, "to_input_name": "A"})
            ue.call(MT, "connect_expressions", {"from_expression": sp, "from_output_name": "", "to_expression": mul, "to_input_name": "B"})
            ue.call(MT, "connect_to_output", {"expression": mul, "output_name": "", "material_property": prop})
            changed = True
            print(f"  {mat}: added {param} on {prop}", flush=True)
            if not verify_parent_prop(ue, mat, param, prop, feeder):
                print(f"STOP: {mat} {prop} did not verify. Run --check; nothing was recompiled or saved.")
                return 1
        if changed:
            ue.call(MT, "recompile", {"material_or_function": m})
            print(f"  {mat}: recompiled", flush=True)
    return 0


# ------------------------------------------------------------------ MIs
def set_scalar(ue, mi_name, param, want):
    inst = ref(pkg(mi_name))
    ue.call(MI, "set_scalar_parameter", {"instance": inst, "name": param, "value": want})
    v, ov = mi_scalar_state(ue, mi_name, param)
    if not ov:
        ue.call(MI, "set_parameter_override", {"instance": inst, "name": param, "override": True})
        ue.call(MI, "set_scalar_parameter", {"instance": inst, "name": param, "value": want})
        v, ov = mi_scalar_state(ue, mi_name, param)
    ok = close(v, want) and ov
    print(f"    {mi_name}.{param}: want {want} read {v:.6g} explicit override {ov} {'ok' if ok else 'MISMATCH'}", flush=True)
    return ok


def do_apply(ue, snap):
    problems = []
    for mat in PARENT_ORDER:
        if not ue.call(AS, "exists", {"path": pkg(mat)}):
            problems.append(f"parent {mat} missing")
    slots, mats = slot_materials(ue)
    for s in SLOT_TARGET:
        if s not in slots:
            problems.append(f"slot {s} missing: {slots}")
    if slots != snap["slots"]:
        problems.append(f"slots {slots} differ from snapshot {snap['slots']}")
    if problems:
        print("REFUSED, nothing was changed:")
        for p in problems:
            print("  -", p)
        return 1
    print("parents:")
    r = do_parents(ue, PARENT_ORDER)
    if r:
        return r
    print("instances:")
    ok = True
    for name, (parent, vals) in NEW_MIS.items():
        if not ue.call(AS, "exists", {"path": pkg(name)}):
            ue.call(MI, "create", {"folder_path": MAT_DIR, "asset_name": name, "parent": ref(pkg(parent))})
            if not ue.call(AS, "exists", {"path": pkg(name)}):
                print(f"STOP: {name} not created.")
                return 1
            print(f"  created {name}", flush=True)
        else:
            print(f"  {name} already exists, not recreated", flush=True)
        par = short(as_json(ue.call(OB, "get_properties", {"instance": ref(pkg(name)), "properties": ["parent"]}))["parent"])
        if par != parent:
            print(f"STOP: {name} parent reads {par}, wanted {parent}")
            return 1
        for p, v in vals.items():
            ok = set_scalar(ue, name, p, v) and ok
    print("wool:")
    ok = set_scalar(ue, WOOL_MI, "Cloth Brightness", CLOTH) and ok
    print("slots:")
    m = ref(MESH_PKG)
    for s, target in SLOT_TARGET.items():
        if short(mats[s]) != target:
            ue.call(SK, "set_material", {"mesh": m, "slot_name": s, "material": ref(pkg(target))})
    slots2, mats2 = slot_materials(ue)
    for s, target in SLOT_TARGET.items():
        good = short(mats2[s]) == target
        ok = ok and good
        print(f"    slot {s}: {short(mats[s])} -> {short(mats2[s])} {'ok' if good else 'MISMATCH'}")
    print("apply:", "OK" if ok else "MISMATCH")
    return 0 if ok else 1


def do_restore(ue, snap):
    m = ref(MESH_PKG)
    ok = True
    for s, old in snap["slot_materials"].items():
        ue.call(SK, "set_material", {"mesh": m, "slot_name": s, "material": {"refPath": old}})
    slots, mats = slot_materials(ue)
    for s, old in snap["slot_materials"].items():
        good = mats.get(s) == old
        ok = ok and good
        print(f"  slot {s}: {short(mats.get(s))} {'ok' if good else 'MISMATCH (want ' + str(short(old)) + ')'}")
    ok = set_scalar(ue, WOOL_MI, "Cloth Brightness", snap["cloth_brightness_before"]) and ok
    print("restore:", "OK (nothing saved)" if ok else "MISMATCH")
    return 0 if ok else 1


# ------------------------------------------------------------------ check
def do_check(ue, snap):
    bad, n_ok = [], 0

    def rec(ok, what, line):
        nonlocal n_ok
        if ok:
            n_ok += 1
        else:
            bad.append(what)
        print(("ok   " if ok else "FAIL ") + line, flush=True)

    # parents: wiring and defaults
    for mat in PARENT_ORDER:
        names = param_names(ue, mat)
        for param, prop in PARENT_PARAMS[mat]:
            before = snap["parents_before"][mat][prop]
            mul, _ = prop_input(ue, mat, prop)
            good = param in names and bool(mul) and "Multiply" in mul
            if good:
                m = ref(pkg(mat))
                mref = {"refPath": f"{pkg(mat)}.{mat}:{mul}"}
                ins = {i["input_name"]: i for i in ue.call(MT, "get_expression_inputs", {"material_or_function": m, "expression": mref})}
                a, b = ins.get("A"), ins.get("B")
                good = bool(a and b and expr_name(a["expression"]) == before[0] and a["output_name"] == before[1])
                sp = expr_name(b["expression"]) if b else None
                if good and sp and "ScalarParameter" in sp:
                    pv = as_json(ue.call(OB, "get_properties", {"instance": {"refPath": f"{pkg(mat)}.{mat}:{sp}"}, "properties": ["ParameterName", "DefaultValue"]}))
                    good = pv["ParameterName"] == param and close(pv["DefaultValue"], 1.0)
                else:
                    good = False
            rec(good, f"{mat} {param} wiring", f"{mat}: {prop} = old feeder {before[0]}.{before[1]} x {param} (default 1)")
    sk_names = param_names(ue, SKIN_PARENT)
    sk_before = snap["parents_before"][SKIN_PARENT]
    sk_feed = list(prop_input(ue, SKIN_PARENT, "MP_BaseColor"))
    rec("BaseColorMul" not in sk_names and SKIN_PARAM in sk_names and sk_feed == sk_before["MP_BaseColor"]
        and sorted(sk_names) == sk_before["parameters"], f"{SKIN_PARENT} changed",
        f"{SKIN_PARENT} untouched (no BaseColorMul added; {SKIN_PARAM} present; BaseColor feeder {sk_feed}; parameters {sorted(sk_names)})")
    leather = sorted(param_names(ue, "M_Warden_Leather"))
    rec(leather == snap["parents_before"]["M_Warden_Leather"]["parameters"], "leather changed", f"M_Warden_Leather untouched (parameters {leather})")
    # MIs
    for name, (parent, vals) in NEW_MIS.items():
        if not ue.call(AS, "exists", {"path": pkg(name)}):
            rec(False, f"{name} missing", f"{name} missing")
            continue
        par = short(as_json(ue.call(OB, "get_properties", {"instance": ref(pkg(name)), "properties": ["parent"]}))["parent"])
        rec(par == parent, f"{name} parent {par}", f"{name} parent = {par}")
        for p, want in vals.items():
            v, ov = mi_scalar_state(ue, name, p)
            rec(close(v, want) and ov, f"{name}.{p}={v} ov={ov}", f"{name}.{p} = {v:.6g} (want {want}, explicit override {ov})")
    v, ov = mi_scalar_state(ue, WOOL_MI, "Cloth Brightness")
    rec(close(v, CLOTH) and ov, f"wool cloth {v}", f"{WOOL_MI}.Cloth Brightness = {v:.6g} (want {CLOTH}, explicit override {ov})")
    for k in ("Detail Strength", "Weave Scale", "Wetness"):
        v, ov = mi_scalar_state(ue, WOOL_MI, k)
        was = snap["wool_before"][k]
        rec(close(v, was[0], 1e-5) and ov == was[1], f"wool {k} changed", f"{WOOL_MI}.{k} = {v:.6g} unchanged from snapshot {was[0]:.6g}")
    # slots
    slots, mats = slot_materials(ue)
    rec(slots == snap["slots"], f"slots {slots}", f"slots equal the snapshot {slots}")
    for s, target in SLOT_TARGET.items():
        rec(short(mats.get(s)) == target and full(mats.get(s)).startswith(MAT_DIR + "/"), f"slot {s} = {short(mats.get(s))}", f"slot {s} = {short(mats.get(s))} (want {target})")
    # geometry untouched
    g = mesh_geometry(ue)
    sg = snap["geometry"]
    same = (g["lod_count"] == sg["lod_count"] and g["lod_vertices"] == sg["lod_vertices"]
            and all(close(a, b, 1e-3) for a, b in zip(g["bounds_extent"] + g["bounds_origin"], sg["bounds_extent"] + sg["bounds_origin"])))
    rec(same, f"geometry {g}", f"geometry equals the snapshot (LODs {g['lod_count']}, vertices {g['lod_vertices']}, extent {[round(x, 2) for x in g['bounds_extent']]})")
    wl = watch_list(ue)
    d = {short(p): is_dirty(ue, p) for p in wl}
    rec(not any(d.values()), f"watch list dirty: {[k for k, v in d.items() if v]}", f"M_LB_Surface and every map not dirty ({len(wl) - 1} maps read): dirty now {[k for k, v in d.items() if v] or 'none'}")
    allp = {short(p): is_dirty(ue, p) for p in SAVE_ORDER}
    print("info  dirty (save list):", sorted(k for k, v in allp.items() if v) or "none")
    print(f"CHECK: {n_ok}/{n_ok + len(bad)} items ok" + ("" if not bad else f"; {len(bad)} MISMATCH: " + "; ".join(bad)))
    return 1 if bad else 0


# ------------------------------------------------------------------ save
def do_save(ue):
    wl = watch_list(ue)
    before = {p: is_dirty(ue, p) for p in SAVE_ORDER + wl}
    print("not saved on purpose (dirty):", {short(p): before[p] for p in wl})
    for i, p in enumerate(SAVE_ORDER):
        assert p not in wl and "/BP_" not in p
        if i:
            time.sleep(PAUSE_S)
        res = ue.call(AS, "save_assets", {"asset_paths": [p]})
        dirty = is_dirty(ue, p)
        print(f"  save {short(p)}: was dirty {before[p]}, returned {res}, is_dirty {dirty}", flush=True)
        if res is not True or dirty is not False:
            print(f"STOP: {p} did not save cleanly; later packages were not saved.")
            return 1
    after = {short(p): is_dirty(ue, p) for p in wl}
    print("dirty after save (watch list):", sorted(k for k, v in after.items() if v) or "none")
    return 0


def load_snap(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", metavar="FILE")
    g.add_argument("--parents", nargs="?", const="all", metavar="NAMES")
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
        if a.parents:
            names = PARENT_ORDER if a.parents == "all" else a.parents.split(",")
            if any(n not in PARENT_PARAMS for n in names):
                print(f"REFUSED: unknown parent in {names}")
                return 1
            return do_parents(ue, names)
        if a.apply:
            return do_apply(ue, load_snap(a.snap_file))
        if a.restore:
            return do_restore(ue, load_snap(a.snap_file))
        if a.check:
            return do_check(ue, load_snap(a.snap_file))
        return do_save(ue)
    except Exception as e:
        print(f"TOOL CALL FAILED: {str(e)[:600]}\nState unknown. Run --check before doing anything else; do not retry in a loop.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
