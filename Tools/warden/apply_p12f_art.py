"""P12 fix set 1, F2 (editor part): the Warden apparition mesh, the apparition and glow materials, and the attack-light parameters.

Spec: Docs/plans/P12_FIX1_WARDEN_APPEARANCES.md sections 5 and 7 (material only). Run with -I, editor open on L_Monastery, no PIE:
    python -I Tools/warden/apply_p12f_art.py --apply | --check | --save

    --apply   preflight (connected, PIE off, L_Monastery and M_LB_Surface not dirty, actor count 2980), then:
              1. import SourceArt/Warden/SM_LB_Warden_Silhouette.fbx as a NEW static mesh
                 /Game/LastBell/Characters/Warden/Meshes/SM_LB_Warden_Apparition (SM_LB_Warden_Silhouette is NOT touched: the old
                 Blueprint and the map still reference it). Nanite off, no collision, one LOD; reads back slots, triangles, bounds.
              2. creates, in /Game/LastBell/Characters/Warden/Materials/: M_Warden_Apparition, MI_Warden_Apparition_Body,
                 MI_Warden_Apparition_Mask, M_Warden_ApparitionGlow, MI_Warden_ApparitionGlow, with the section 5 values.
                 A material that exists but does not verify is cleared and rebuilt (they are new assets of this task).
              3. assigns the two apparition MIs to the mesh's slots MAT_Body / MAT_Mask by slot name.
              4. M_Warden_BellMetal: adds TellGlow (scalar 0) and TellGlowColor (vector 1, 0.06, 0.02) with
                 Emissive = TellGlowColor x TellGlow x 8 (an existing Emissive feeder is added to, not replaced).
              Every material is recompiled (raises on a shader error). Nothing is saved.
    --check   read back everything, exit 1 on any mismatch (also checks the actor count and that nothing unwanted is dirty).
    --save    one package per save_assets call, 5 s apart (mesh, 2 materials, 3 instances, M_Warden_BellMetal). Never save-all,
              never a map, never M_LB_Surface.

Exit codes: 0 ok, 1 mismatch or refused, 2 a tool call failed (state unknown: run --check, don't retry in a loop).
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
ST = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
SC = "editor_toolset.toolsets.scene.SceneTools"
APP = "EditorToolset.EditorAppToolset"
LOGS = "EditorToolset.LogsToolset"

FBX = os.path.join(ROOT, "SourceArt", "Warden", "SM_LB_Warden_Silhouette.fbx")
MESH_DIR = "/Game/LastBell/Characters/Warden/Meshes"
MESH_NAME = "SM_LB_Warden_Apparition"
MESH_PKG = f"{MESH_DIR}/{MESH_NAME}"
OLD_MESH_PKG = f"{MESH_DIR}/SM_LB_Warden_Silhouette"
MAT_DIR = "/Game/LastBell/Characters/Warden/Materials"
MAPS_DIR = "/Game/LastBell/Maps"
NEVER_SAVE = ["/Game/LastBell/Materials/Master/M_LB_Surface"]
ACTORS = 2980
GROUP = "Apparition"
FUNC_DITHER = "/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA.DitherTemporalAA"
FUNC_RADIAL = "/Engine/Functions/Engine_MaterialFunctions01/Gradient/RadialGradientExponential.RadialGradientExponential"

# mesh read-back expected from the Blender re-import (verify_silhouette_bake.py), Y mirrored by the static import
SLOTS = ["MAT_Body", "MAT_Mask"]
BOUNDS_MIN = [-83.81, -109.55, 0.25]
BOUNDS_MAX = [60.88, 66.26, 284.22]
TRIS_MAX = 8000

# parent materials and the parameters they hold: (type, name, default)
APPARITION = "M_Warden_Apparition"
GLOW = "M_Warden_ApparitionGlow"
APP_PARAMS = [("vector", "Color", (0.012, 0.012, 0.014)), ("scalar", "Rough", 0.85), ("scalar", "Metal", 0.0),
              ("vector", "Emissive", (0.0, 0.0, 0.0)), ("scalar", "Fade", 1.0)]
GLOW_PARAMS = [("vector", "Color", (0.55, 0.62, 0.80)), ("scalar", "Strength", 0.25), ("scalar", "Fade", 1.0)]
# instance -> (parent, {param: value}); a vector is an (r, g, b) tuple
MIS = {
    "MI_Warden_Apparition_Body": (APPARITION, {"Color": (0.012, 0.012, 0.014), "Emissive": (0.0, 0.0, 0.0)}),
    "MI_Warden_Apparition_Mask": (APPARITION, {"Color": (0.30, 0.22, 0.12), "Rough": 0.6, "Metal": 0.3,
                                               "Emissive": (0.05, 0.045, 0.038)}),
    "MI_Warden_ApparitionGlow": (GLOW, {"Color": (0.55, 0.62, 0.80), "Strength": 0.12}),
}
SLOT_MI = {"MAT_Body": "MI_Warden_Apparition_Body", "MAT_Mask": "MI_Warden_Apparition_Mask"}
NEW_MATS = [APPARITION, GLOW]

BELL = "M_Warden_BellMetal"
BELL_MI = "MI_Warden_BellMetal"
BELL_MI_VALUES = {"BaseColorMul": 1.6, "MetallicMul": 0.35, "RoughnessMul": 0.85}
TELL = {"TellGlow": 0.0, "TellGlowColor": (1.0, 0.06, 0.02)}
TELL_BRIGHTNESS = 8.0

SAVE_ORDER = [MESH_PKG] + [f"{MAT_DIR}/{n}" for n in [APPARITION] + [m for m in MIS if m.startswith("MI_Warden_Apparition_")] +
                           [GLOW, "MI_Warden_ApparitionGlow", BELL]]


# ------------------------------------------------------------------ helpers
def pkg(name):
    return f"{MAT_DIR}/{name}"


def ref(p):
    return {"refPath": f"{p}.{p.split('/')[-1]}"}


def eref(mat_name, expr):
    return {"refPath": f"{pkg(mat_name)}.{mat_name}:{expr}"}


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


def lc(v):
    """LinearColor dict (any key case) -> (r, g, b)."""
    g = {k.lower(): x for k, x in v.items()}
    return (g["r"], g["g"], g["b"])


def vclose(a, b, tol=1e-4):
    return all(close(x, y, tol) for x, y in zip(a, b))


def is_dirty(ue, p):
    if not ue.call(AS, "exists", {"path": p}):
        return None
    return ue.call(AS, "is_dirty", {"asset_path": p})


def actor_count(ue):
    last = None
    for _ in range(4):
        try:
            return len(ue.call(SC, "find_actors", {"name": "", "tag": "", "collision_channels": []}))
        except ConnectionResetError as e:       # the 2980-actor reply sometimes drops the connection
            last = e
            time.sleep(2)
            ue.__init__()
    raise last


def watch_list(ue):
    return NEVER_SAVE + list(ue.call(AS, "find_assets", {"folder_path": MAPS_DIR, "name": ""}))


def preflight(ue):
    if ue.call(APP, "IsPIERunning", {}):
        print("refused: PIE is running. Nothing was changed.")
        return None
    lvl = ue.call(SC, "get_current_level", {})
    n = actor_count(ue)
    dirty = {short(p): is_dirty(ue, p) for p in watch_list(ue)}
    print(f"preflight: level {lvl}, PIE off, actors {n}, dirty watch list: {[k for k, v in dirty.items() if v] or 'none'}")
    if any(dirty.values()) or n != ACTORS or "L_Monastery" not in str(lvl):
        print(f"refused: expected L_Monastery, {ACTORS} actors and nothing dirty.")
        return None
    return n


# ------------------------------------------------------------------ material graph helpers
def exprs(ue, mat_name):
    return [expr_name(e) for e in ue.call(MT, "get_expressions", {"material_or_function": ref(pkg(mat_name))})]


def add(ue, mat_name, cls, x, y, props=None):
    r = as_json(ue.call(MT, "add_expression", {"material_or_function": ref(pkg(mat_name)),
                                               "expression_class": {"refPath": f"/Script/Engine.{cls}"}, "x": x, "y": y}))
    if props:
        ue.call(OB, "set_properties", {"instance": r, "values": json.dumps(props)})
    return r


def add_param(ue, mat_name, kind, name, default, x, y):
    if kind == "scalar":
        return add(ue, mat_name, "MaterialExpressionScalarParameter", x, y,
                   {"ParameterName": name, "DefaultValue": float(default), "Group": GROUP})
    d = {"r": default[0], "g": default[1], "b": default[2], "a": 1.0}
    return add(ue, mat_name, "MaterialExpressionVectorParameter", x, y,
               {"ParameterName": name, "DefaultValue": d, "Group": GROUP})


def conn(ue, mat_name, src, to, inp, out=""):
    ue.call(MT, "connect_expressions", {"from_expression": src, "from_output_name": out, "to_expression": to, "to_input_name": inp})


def to_output(ue, mat_name, src, prop, out=""):
    ue.call(MT, "connect_to_output", {"expression": src, "output_name": out, "material_property": prop})


def clear_material(ue, mat_name):
    for e in exprs(ue, mat_name):
        ue.call(MT, "delete_expression", {"material_or_function": ref(pkg(mat_name)), "expression": eref(mat_name, e)})


def find_param(ue, mat_name, name):
    """Expression ref of the Scalar/VectorParameter with this ParameterName, or None."""
    for e in exprs(ue, mat_name):
        if "ScalarParameter" in e or "VectorParameter" in e:
            p = as_json(ue.call(OB, "get_properties", {"instance": eref(mat_name, e), "properties": ["ParameterName", "DefaultValue"]}))
            if p["ParameterName"] == name:
                return eref(mat_name, e), p["DefaultValue"]
    return None, None


def prop_input(ue, mat_name, prop):
    r = ue.call(MT, "get_property_input", {"material": ref(pkg(mat_name)), "material_property": prop})
    return expr_name(r["expression"]), r["output_name"]


def inputs(ue, mat_name, expr):
    return {i["input_name"]: i for i in ue.call(MT, "get_expression_inputs", {"material_or_function": ref(pkg(mat_name)), "expression": eref(mat_name, expr)})}


def param_of(ue, mat_name, expr):
    """ParameterName of a parameter expression, else None."""
    if not expr or not ("ScalarParameter" in expr or "VectorParameter" in expr):
        return None
    return as_json(ue.call(OB, "get_properties", {"instance": eref(mat_name, expr), "properties": ["ParameterName"]}))["ParameterName"]


def set_mat_props(ue, mat_name, props):
    ue.call(OB, "set_properties", {"instance": ref(pkg(mat_name)), "values": json.dumps(props)})


def mat_props(ue, mat_name, names):
    return as_json(ue.call(OB, "get_properties", {"instance": ref(pkg(mat_name)), "properties": names}))


# ------------------------------------------------------------------ the two new materials
def build_apparition(ue):
    m = APPARITION
    P = {}
    for i, (k, n, d) in enumerate(APP_PARAMS):
        P[n], _ = add_param(ue, m, k, n, d, -600, i * 160), None
    dith = add(ue, m, "MaterialExpressionMaterialFunctionCall", -300, 640, {"MaterialFunction": {"refPath": FUNC_DITHER}})
    mul = add(ue, m, "MaterialExpressionMultiply", -300, 480)
    conn(ue, m, P["Fade"], dith, "Alpha Threshold")
    conn(ue, m, P["Emissive"], mul, "A")
    conn(ue, m, P["Fade"], mul, "B")
    to_output(ue, m, dith, "MP_OpacityMask", "Result")
    to_output(ue, m, mul, "MP_EmissiveColor")
    to_output(ue, m, P["Color"], "MP_BaseColor")
    to_output(ue, m, P["Rough"], "MP_Roughness")
    to_output(ue, m, P["Metal"], "MP_Metallic")
    set_mat_props(ue, m, {"blendMode": "BLEND_Masked", "twoSided": True, "shadingModel": "MSM_DefaultLit"})


def build_glow(ue):
    m = GLOW
    P = {}
    for i, (k, n, d) in enumerate(GLOW_PARAMS):
        P[n], _ = add_param(ue, m, k, n, d, -700, 300 + i * 160), None
    grad = add(ue, m, "MaterialExpressionMaterialFunctionCall", -700, 0, {"MaterialFunction": {"refPath": FUNC_RADIAL}})
    names = ue.call(MT, "get_expression_input_names", {"material_or_function": ref(pkg(m)), "expression": grad})
    radius = next(n for n in names if n.lower().startswith("radius"))
    density = next(n for n in names if n.lower() == "density")
    c_r = add(ue, m, "MaterialExpressionConstant", -900, 0, {"R": 0.5})
    c_d = add(ue, m, "MaterialExpressionConstant", -900, 80, {"R": 2.0})
    conn(ue, m, c_r, grad, radius)
    conn(ue, m, c_d, grad, density)
    m1 = add(ue, m, "MaterialExpressionMultiply", -350, 0)      # gradient x Color
    m2 = add(ue, m, "MaterialExpressionMultiply", -200, 0)      # x Strength
    m3 = add(ue, m, "MaterialExpressionMultiply", -50, 0)       # x Fade
    out_name = ue.call(MT, "get_expression_output_names", {"material_or_function": ref(pkg(m)), "expression": grad})[0]
    conn(ue, m, grad, m1, "A", out_name)
    conn(ue, m, P["Color"], m1, "B")
    conn(ue, m, m1, m2, "A")
    conn(ue, m, P["Strength"], m2, "B")
    conn(ue, m, m2, m3, "A")
    conn(ue, m, P["Fade"], m3, "B")
    to_output(ue, m, m3, "MP_EmissiveColor")
    set_mat_props(ue, m, {"blendMode": "BLEND_Additive", "twoSided": True, "shadingModel": "MSM_Unlit"})


def verify_params(ue, m, plist, bad):
    for k, n, d in plist:
        e, dv = find_param(ue, m, n)
        if not e:
            bad.append(f"{m}: parameter {n} missing")
            continue
        ok = vclose(lc(dv), d) if k == "vector" else close(dv, d)
        if not ok:
            bad.append(f"{m}: {n} default {dv}, want {d}")


def verify_apparition(ue, bad):
    m = APPARITION
    if not ue.call(AS, "exists", {"path": pkg(m)}):
        bad.append(f"{m} missing")
        return
    n0 = len(bad)
    verify_params(ue, m, APP_PARAMS, bad)
    p = mat_props(ue, m, ["blendMode", "twoSided", "shadingModel"])
    if p["blendMode"] != "BLEND_Masked" or p["twoSided"] is not True or p["shadingModel"] != "MSM_DefaultLit":
        bad.append(f"{m}: blend/two-sided/shading read {p}")
    for prop, want in (("MP_BaseColor", "Color"), ("MP_Roughness", "Rough"), ("MP_Metallic", "Metal")):
        e, o = prop_input(ue, m, prop)
        if param_of(ue, m, e) != want:
            bad.append(f"{m}: {prop} fed by {e} ({param_of(ue, m, e)}), want {want}")
    e, o = prop_input(ue, m, "MP_OpacityMask")
    if not e or "MaterialFunctionCall" not in e:
        bad.append(f"{m}: OpacityMask fed by {e}")
    else:
        fn = short(as_json(ue.call(OB, "get_properties", {"instance": eref(m, e), "properties": ["MaterialFunction"]}))["MaterialFunction"])
        a = inputs(ue, m, e).get("Alpha Threshold")
        if fn != "DitherTemporalAA" or not a or param_of(ue, m, expr_name(a["expression"])) != "Fade":
            bad.append(f"{m}: OpacityMask function {fn}, Alpha Threshold fed by {a and a['expression']}")
    e, o = prop_input(ue, m, "MP_EmissiveColor")
    if not e or "Multiply" not in e:
        bad.append(f"{m}: Emissive fed by {e}")
    else:
        ins = inputs(ue, m, e)
        if param_of(ue, m, expr_name(ins["A"]["expression"])) != "Emissive" or param_of(ue, m, expr_name(ins["B"]["expression"])) != "Fade":
            bad.append(f"{m}: Emissive multiply inputs {ins['A']['expression']}, {ins['B']['expression']}")
    return len(bad) == n0


def verify_glow(ue, bad):
    m = GLOW
    if not ue.call(AS, "exists", {"path": pkg(m)}):
        bad.append(f"{m} missing")
        return
    n0 = len(bad)
    verify_params(ue, m, GLOW_PARAMS, bad)
    p = mat_props(ue, m, ["blendMode", "twoSided", "shadingModel"])
    if p["blendMode"] != "BLEND_Additive" or p["twoSided"] is not True or p["shadingModel"] != "MSM_Unlit":
        bad.append(f"{m}: blend/two-sided/shading read {p}")
    # Emissive = RadialGradientExponential(radius 0.5, density 2) x Color x Strength x Fade
    seen = []
    e, _ = prop_input(ue, m, "MP_EmissiveColor")
    for _ in range(3):
        if not e or "Multiply" not in e:
            bad.append(f"{m}: emissive chain broken at {e}")
            return False
        ins = inputs(ue, m, e)
        seen.append(param_of(ue, m, expr_name(ins["B"]["expression"])))
        e = expr_name(ins["A"]["expression"])
    # the last A is the gradient x Color multiply's A (m1); m1's B is Color
    if seen[:2] != ["Fade", "Strength"] or seen[2] != "Color":
        bad.append(f"{m}: multiply chain parameters {seen}, want ['Fade', 'Strength', 'Color']")
    # e is now the gradient call
    if not e or "MaterialFunctionCall" not in e:
        bad.append(f"{m}: gradient node is {e}")
    else:
        fn = short(as_json(ue.call(OB, "get_properties", {"instance": eref(m, e), "properties": ["MaterialFunction"]}))["MaterialFunction"])
        if fn != "RadialGradientExponential":
            bad.append(f"{m}: gradient function {fn}")
        for nm, want in (("radius", 0.5), ("density", 2.0)):
            names = [n for n in inputs(ue, m, e) if n.lower().startswith(nm) and "invert" not in n.lower()]
            src = inputs(ue, m, e)[names[0]]["expression"] if names else None
            val = as_json(ue.call(OB, "get_properties", {"instance": eref(m, expr_name(src)), "properties": ["R"]}))["R"] if src and expr_name(src) else None
            if val is None or not close(val, want):
                bad.append(f"{m}: gradient {nm} input reads {val}, want {want}")
    return len(bad) == n0


def ensure_material(ue, name, builder, verifier):
    """Create if missing; if it exists but does not verify, clear and rebuild (these are new assets of this task)."""
    if not ue.call(AS, "exists", {"path": pkg(name)}):
        ue.call(MT, "create_material", {"folder_path": MAT_DIR, "asset_name": name})
        print(f"  created {name}", flush=True)
        clear_material(ue, name)
        builder(ue)
    else:
        bad = []
        verifier(ue, bad)
        if bad:
            print(f"  {name} exists but does not verify ({bad[0]}); clearing and rebuilding", flush=True)
            clear_material(ue, name)
            builder(ue)
        else:
            print(f"  {name} already built and verified", flush=True)
    ue.call(MT, "recompile", {"material_or_function": ref(pkg(name))})      # raises when a shader fails
    print(f"  {name}: recompiled", flush=True)


# ------------------------------------------------------------------ instances
def mi_state(ue, name):
    return as_json(ue.call(OB, "get_properties", {"instance": ref(pkg(name)), "properties": ["parent", "scalarParameterValues", "vectorParameterValues"]}))


def overridden(ue, name, kind, param):
    r = mi_state(ue, name)
    return any(e["parameterInfo"]["name"] == param for e in r["scalarParameterValues" if kind == "scalar" else "vectorParameterValues"])


def set_param(ue, mi_name, param, want):
    inst = ref(pkg(mi_name))
    vec = isinstance(want, tuple)
    for attempt in range(2):
        if vec:
            ue.call(MI, "set_vector_parameter", {"instance": inst, "name": param, "value": {"r": want[0], "g": want[1], "b": want[2], "a": 1.0}})
            got = lc(ue.call(MI, "get_vector_parameter", {"instance": inst, "name": param}))
            ok = vclose(got, want)
        else:
            ue.call(MI, "set_scalar_parameter", {"instance": inst, "name": param, "value": want})
            got = ue.call(MI, "get_scalar_parameter", {"instance": inst, "name": param})
            ok = close(got, want)
        ov = overridden(ue, mi_name, "vector" if vec else "scalar", param)
        if ov:
            break
        ue.call(MI, "set_parameter_override", {"instance": inst, "name": param, "override": True})
    print(f"    {mi_name}.{param}: want {want} read {got} explicit override {ov} {'ok' if ok and ov else 'MISMATCH'}", flush=True)
    return ok and ov


def ensure_instance(ue, name, parent, vals):
    ok = True
    if not ue.call(AS, "exists", {"path": pkg(name)}):
        ue.call(MI, "create", {"folder_path": MAT_DIR, "asset_name": name, "parent": ref(pkg(parent))})
        if not ue.call(AS, "exists", {"path": pkg(name)}):
            raise RuntimeError(f"{name} not created")
        print(f"  created {name}", flush=True)
    par = short(mi_state(ue, name)["parent"])
    if par != parent:
        raise RuntimeError(f"{name} parent reads {par}, wanted {parent}")
    for p, v in vals.items():
        ok = set_param(ue, name, p, v) and ok
    return ok


# ------------------------------------------------------------------ mesh
def mesh_state(ue):
    m = ref(MESH_PKG)
    b = ue.call(ST, "get_bounds", {"mesh": m})
    slots = list(ue.call(ST, "get_material_slots", {"mesh": m}))
    return {"slots": slots, "slot_materials": {s: short(ue.call(ST, "get_material", {"mesh": m, "slot_name": s})) for s in slots},
            "triangles": ue.call(ST, "get_triangle_count", {"mesh": m, "lod_index": 0}),
            "vertices": ue.call(ST, "get_vertex_count", {"mesh": m, "lod_index": 0}),
            "lods": ue.call(ST, "get_lod_count", {"mesh": m}), "nanite": ue.call(ST, "is_nanite_enabled", {"mesh": m}),
            "bounds_min": [b["min"][k] for k in "xyz"], "bounds_max": [b["max"][k] for k in "xyz"]}


def import_mesh(ue):
    if ue.call(AS, "exists", {"path": MESH_PKG}):
        print(f"  {MESH_NAME} already exists, not re-imported", flush=True)
        return
    cdo = {"refPath": "/Script/UnrealEd.Default__FbxStaticMeshImportData"}
    keys = ["bBuildNanite", "bAutoGenerateCollision"]
    before = as_json(ue.call(OB, "get_properties", {"instance": cdo, "properties": keys}))
    ue.call(OB, "set_properties", {"instance": cdo, "values": json.dumps({"bBuildNanite": False, "bAutoGenerateCollision": False})})
    try:
        ue.call(ST, "import_file", {"folder_path": MESH_DIR, "asset_name": MESH_NAME, "source_file": FBX,
                                    "import_materials": False, "import_textures": False, "combine_meshes": True})
    finally:                                                    # the import options are in memory only: put them back
        ue.call(OB, "set_properties", {"instance": cdo, "values": json.dumps(before)})
    if not ue.call(AS, "exists", {"path": MESH_PKG}):
        raise RuntimeError("import produced no asset")
    m = ref(MESH_PKG)
    ue.call(ST, "remove_collisions", {"mesh": m})
    if ue.call(ST, "is_nanite_enabled", {"mesh": m}):
        ue.call(ST, "set_nanite_enabled", {"mesh": m, "enabled": False})
    print(f"  imported {MESH_NAME} from {FBX}", flush=True)


def verify_mesh(ue, bad):
    if not ue.call(AS, "exists", {"path": MESH_PKG}):
        bad.append("mesh missing")
        return None
    s = mesh_state(ue)
    if s["slots"] != SLOTS:
        bad.append(f"slots {s['slots']}, want {SLOTS}")
    if not (0 < s["triangles"] <= TRIS_MAX):
        bad.append(f"triangles {s['triangles']}")
    if s["lods"] != 1:
        bad.append(f"LOD count {s['lods']}")
    if s["nanite"]:
        bad.append("Nanite is on")
    if not all(abs(a - b) <= 0.1 for a, b in zip(s["bounds_min"] + s["bounds_max"], BOUNDS_MIN + BOUNDS_MAX)):
        bad.append(f"bounds {s['bounds_min']} {s['bounds_max']}, want {BOUNDS_MIN} {BOUNDS_MAX}")
    return s


# ------------------------------------------------------------------ M_Warden_BellMetal
def bell_has_tell(ue):
    return all(find_param(ue, BELL, n)[0] for n in TELL)


def do_bell(ue):
    m = BELL
    if bell_has_tell(ue):
        print(f"  {m}: TellGlow / TellGlowColor already exist, not added again", flush=True)
        return
    old, old_out = prop_input(ue, m, "MP_EmissiveColor")
    print(f"  {m}: Emissive before = {old or 'not connected'}", flush=True)
    pos = (-1200, 900)
    tg, _ = add_param(ue, m, "scalar", "TellGlow", TELL["TellGlow"], pos[0], pos[1] + 160), None
    tc, _ = add_param(ue, m, "vector", "TellGlowColor", TELL["TellGlowColor"], pos[0], pos[1]), None
    ue.call(OB, "set_properties", {"instance": tg, "values": json.dumps({"Group": "Warden Tuning"})})
    ue.call(OB, "set_properties", {"instance": tc, "values": json.dumps({"Group": "Warden Tuning"})})
    m1 = add(ue, m, "MaterialExpressionMultiply", pos[0] + 300, pos[1])            # color x TellGlow
    m2 = add(ue, m, "MaterialExpressionMultiply", pos[0] + 450, pos[1], {"ConstB": TELL_BRIGHTNESS})   # x 8 (B left unwired)
    conn(ue, m, tc, m1, "A")
    conn(ue, m, tg, m1, "B")
    conn(ue, m, m1, m2, "A")
    final = m2
    if old:
        add_node = add(ue, m, "MaterialExpressionAdd", pos[0] + 600, pos[1])
        conn(ue, m, eref(m, old), add_node, "A", old_out)
        conn(ue, m, m2, add_node, "B")
        final = add_node
    to_output(ue, m, final, "MP_EmissiveColor")
    ue.call(MT, "recompile", {"material_or_function": ref(pkg(m))})
    print(f"  {m}: added TellGlow, TellGlowColor; recompiled", flush=True)


def verify_bell(ue, bad):
    m = BELL
    for n, d in TELL.items():
        e, dv = find_param(ue, m, n)
        if not e:
            bad.append(f"{m}: {n} missing")
        elif not (vclose(lc(dv), d) if isinstance(d, tuple) else close(dv, d)):
            bad.append(f"{m}: {n} default {dv}, want {d}")
    e, _ = prop_input(ue, m, "MP_EmissiveColor")
    if not e:
        bad.append(f"{m}: Emissive not connected")
        return
    if "Add" in e:                                  # an old feeder was added to
        e = expr_name(inputs(ue, m, e)["B"]["expression"])
    ins = inputs(ue, m, e) if e and "Multiply" in e else {}
    cb = as_json(ue.call(OB, "get_properties", {"instance": eref(m, e), "properties": ["ConstB"]}))["ConstB"] if ins else None
    b_wired = ins.get("B") and expr_name(ins["B"]["expression"])
    if not ins or b_wired or cb is None or not close(cb, TELL_BRIGHTNESS):
        bad.append(f"{m}: Emissive final multiply is {e} (B wired {b_wired}, ConstB {cb}), want x{TELL_BRIGHTNESS}")
        return
    e1 = expr_name(ins["A"]["expression"])
    i1 = inputs(ue, m, e1) if e1 and "Multiply" in e1 else {}
    if not i1 or param_of(ue, m, expr_name(i1["A"]["expression"])) != "TellGlowColor" or param_of(ue, m, expr_name(i1["B"]["expression"])) != "TellGlow":
        bad.append(f"{m}: Emissive inner multiply {e1} is not TellGlowColor x TellGlow")


# ------------------------------------------------------------------ modes
def log_scan(ue):
    try:
        r = ue.call(LOGS, "GetLogEntries", {"category": "", "pattern": "(?i)(error|fail).*(Apparition|ApparitionGlow|BellMetal|shader)|(Apparition|ApparitionGlow|BellMetal).*(error|fail)", "maxEntries": 40})
        return r
    except Exception as e:
        return f"(log read failed: {str(e)[:200]})"


def do_apply(ue):
    n0 = preflight(ue)
    if n0 is None:
        return 1
    print("mesh:")
    import_mesh(ue)
    print("materials:")
    ensure_material(ue, APPARITION, build_apparition, verify_apparition)
    ensure_material(ue, GLOW, build_glow, verify_glow)
    print("instances:")
    ok = True
    for name, (parent, vals) in MIS.items():
        ok = ensure_instance(ue, name, parent, vals) and ok
    print("slots:")
    m = ref(MESH_PKG)
    for s, mi in SLOT_MI.items():
        ue.call(ST, "set_material", {"mesh": m, "slot_name": s, "material": ref(pkg(mi))})
        got = short(ue.call(ST, "get_material", {"mesh": m, "slot_name": s}))
        print(f"    slot {s} -> {got} {'ok' if got == mi else 'MISMATCH'}")
        ok = ok and got == mi
    print("bell metal:")
    do_bell(ue)
    n1 = actor_count(ue)
    print(f"actors: {n0} -> {n1} {'ok' if n0 == n1 else 'CHANGED'}")
    print("apply:", "OK, run --check next; nothing saved" if ok and n0 == n1 else "PROBLEM, run --check")
    return 0 if ok and n0 == n1 else 1


def do_check(ue):
    bad = []
    s = verify_mesh(ue, bad)
    if s:
        print("mesh:", json.dumps(s))
        for sl, mi in SLOT_MI.items():
            if s["slot_materials"].get(sl) != mi:
                bad.append(f"slot {sl} = {s['slot_materials'].get(sl)}, want {mi}")
    verify_apparition(ue, bad)
    verify_glow(ue, bad)
    for name, (parent, vals) in MIS.items():
        if not ue.call(AS, "exists", {"path": pkg(name)}):
            bad.append(f"{name} missing")
            continue
        st = mi_state(ue, name)
        if short(st["parent"]) != parent:
            bad.append(f"{name} parent {short(st['parent'])}")
        for p, v in vals.items():
            inst = ref(pkg(name))
            if isinstance(v, tuple):
                got = lc(ue.call(MI, "get_vector_parameter", {"instance": inst, "name": p}))
                ok = vclose(got, v) and overridden(ue, name, "vector", p)
            else:
                got = ue.call(MI, "get_scalar_parameter", {"instance": inst, "name": p})
                ok = close(got, v) and overridden(ue, name, "scalar", p)
            print(f"  {name}.{p} = {got} (want {v}) {'ok' if ok else 'MISMATCH'}")
            if not ok:
                bad.append(f"{name}.{p} = {got}, want {v}")
    verify_bell(ue, bad)
    e, _ = prop_input(ue, BELL, "MP_EmissiveColor")
    print(f"  {BELL}: Emissive final node {e}")
    for p, v in BELL_MI_VALUES.items():
        got = ue.call(MI, "get_scalar_parameter", {"instance": ref(pkg(BELL_MI)), "name": p})
        ov = overridden(ue, BELL_MI, "scalar", p)
        print(f"  {BELL_MI}.{p} = {got} override {ov} (want {v})")
        if not (close(got, v) and ov):
            bad.append(f"{BELL_MI}.{p} = {got}, override {ov}")
    tg = ue.call(MI, "get_scalar_parameter", {"instance": ref(pkg(BELL_MI)), "name": "TellGlow"})
    print(f"  {BELL_MI}.TellGlow (inherited) = {tg}")
    n = actor_count(ue)
    print(f"  actors {n} (want {ACTORS})")
    if n != ACTORS:
        bad.append(f"actor count {n}")
    d = {short(p): is_dirty(ue, p) for p in watch_list(ue)}
    print("  watch list dirty:", [k for k, v in d.items() if v] or "none")
    if any(d.values()):
        bad.append(f"watch list dirty: {[k for k, v in d.items() if v]}")
    allp = {short(p): is_dirty(ue, p) for p in SAVE_ORDER + [OLD_MESH_PKG]}
    print("  dirty (save list + old silhouette mesh):", sorted(k for k, v in allp.items() if v) or "none")
    print("  log scan:", log_scan(ue))
    print("CHECK:", "all ok" if not bad else f"{len(bad)} MISMATCH: " + "; ".join(bad))
    return 1 if bad else 0


def do_save(ue):
    wl = watch_list(ue)
    for i, p in enumerate(SAVE_ORDER):
        assert p not in wl and "/BP_" not in p and "M_LB_Surface" not in p
        if i:
            time.sleep(5)
        was = is_dirty(ue, p)
        res = ue.call(AS, "save_assets", {"asset_paths": [p]})
        now = is_dirty(ue, p)
        print(f"  save {short(p)}: was dirty {was}, returned {res}, is_dirty {now}", flush=True)
        if res is not True or now is not False:
            print(f"STOP: {p} did not save cleanly; later packages were not saved.")
            return 1
    print("dirty after save (watch list):", [short(p) for p in wl if is_dirty(ue, p)] or "none")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    for m in ("apply", "check", "save"):
        g.add_argument("--" + m, action="store_true")
    a = ap.parse_args()
    ue = UE()
    try:
        return do_apply(ue) if a.apply else do_check(ue) if a.check else do_save(ue)
    except Exception as e:
        print(f"TOOL CALL FAILED: {str(e)[:800]}\nState unknown. Run --check before doing anything else; do not retry in a loop.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
