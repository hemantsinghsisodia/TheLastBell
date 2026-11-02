"""P11-5a: add the world-space weathering layer (bWeathering) to M_LB_Surface.

Spec: Docs/plans/P11_MATERIALS.md, section "P11-5a". Run with -I, editor open on L_Monastery, no PIE.

Stages (each is a separate command, so nothing happens by accident):
    check            read-only: counts, the four connections, hlsl lint
    test             build + recompile the throwaway material M_P11_WeatherTest (never the master)
    master-add       add the new nodes to M_LB_Surface and wire them (existing connections untouched)
    master-verify    read back every new connection (read-only)
    master-rewire    the four rewires, last and together
    master-recompile ONE recompile of M_LB_Surface (long timeout)

Nothing here saves an asset and nothing turns bWeathering on anywhere.
"""
import json
import re
import sys
import urllib.request

sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE  # noqa: E402

_orig_urlopen = urllib.request.urlopen
urllib.request.urlopen = lambda *a, **k: _orig_urlopen(*a, **{**k, "timeout": 3600})

M = "editor_toolset.toolsets.material.MaterialTools"
O = "editor_toolset.toolsets.object.ObjectTools"
MI = "editor_toolset.toolsets.material_instance.MaterialInstanceTools"
AS = "editor_toolset.toolsets.asset.AssetTools"

MASTER = "/Game/LastBell/Materials/Master/M_LB_Surface.M_LB_Surface"
TEST_FOLDER = "/Game/LastBell/ArtTest/P11/Materials"
TEST_NAME = "M_P11_WeatherTest"
TEST = f"{TEST_FOLDER}/{TEST_NAME}.{TEST_NAME}"
GROUP = "Weathering"

# (name, default) in the plan's table order.
SCALARS = [
    ("WeatherFloorZ", 0.0),
    ("GrimeBaseHeightCm", 220.0),
    ("GrimeBaseAmount", 0.45),
    ("GrimeNoiseScaleCm", 180.0),
    ("StreakScaleHCm", 70.0),
    ("StreakScaleVCm", 900.0),
    ("StreakThreshold", 0.55),
    ("StreakAmount", 0.30),
    ("StreakRoughness", 0.35),
    ("PatchScaleCm", 1100.0),
    ("PatchAmount", 0.30),
]
VECTORS = [
    ("GrimeTint", (0.30, 0.27, 0.22)),
    ("PatchTint", (0.70, 0.74, 0.68)),
]
# Custom node inputs, in the plan's order: every scalar except StreakRoughness.
CUSTOM_INPUTS = ["WorldPos", "NormalWS"] + [n for n, _ in SCALARS if n != "StreakRoughness"]

# Copied exactly from Docs/plans/P11_MATERIALS.md (P11-5a). `noise`, `sample`, `patch` are reserved in HLSL.
HLSL = r'''float wall = saturate((1.0 - abs(NormalWS.z)) * 2.0);
float u = WorldPos.x + WorldPos.y;
float2 pg = float2(u, WorldPos.z) / max(GrimeNoiseScaleCm, 1.0) + float2(23.7, 5.1);
float2 ig = floor(pg); float2 fg = frac(pg); float2 sg = fg * fg * (3.0 - 2.0 * fg);
float g1 = frac(sin(dot(ig, float2(127.1, 311.7))) * 43758.5453);
float g2 = frac(sin(dot(ig + float2(1.0, 0.0), float2(127.1, 311.7))) * 43758.5453);
float g3 = frac(sin(dot(ig + float2(0.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float g4 = frac(sin(dot(ig + float2(1.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float gEdge = lerp(lerp(g1, g2, sg.x), lerp(g3, g4, sg.x), sg.y);
float band = (1.0 - saturate((WorldPos.z - WeatherFloorZ) / max(GrimeBaseHeightCm, 1.0))) * lerp(0.6, 1.0, gEdge);
float2 p1 = float2(u / max(StreakScaleHCm, 1.0), WorldPos.z / max(StreakScaleVCm, 1.0)) + float2(71.3, 13.9);
float2 i1 = floor(p1); float2 f1 = frac(p1); float2 u1 = f1 * f1 * (3.0 - 2.0 * f1);
float a1 = frac(sin(dot(i1, float2(127.1, 311.7))) * 43758.5453);
float a2 = frac(sin(dot(i1 + float2(1.0, 0.0), float2(127.1, 311.7))) * 43758.5453);
float a3 = frac(sin(dot(i1 + float2(0.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float a4 = frac(sin(dot(i1 + float2(1.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float sa = lerp(lerp(a1, a2, u1.x), lerp(a3, a4, u1.x), u1.y);
float2 p2 = p1 * 2.37 + float2(0.37, 0.71);
float2 i2 = floor(p2); float2 f2 = frac(p2); float2 u2 = f2 * f2 * (3.0 - 2.0 * f2);
float b1 = frac(sin(dot(i2, float2(127.1, 311.7))) * 43758.5453);
float b2 = frac(sin(dot(i2 + float2(1.0, 0.0), float2(127.1, 311.7))) * 43758.5453);
float b3 = frac(sin(dot(i2 + float2(0.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float b4 = frac(sin(dot(i2 + float2(1.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float sb = lerp(lerp(b1, b2, u2.x), lerp(b3, b4, u2.x), u2.y);
float streak = smoothstep(StreakThreshold, StreakThreshold + 0.15, sa * 0.6 + sb * 0.4);
float2 pc = float2(u, WorldPos.z) / max(PatchScaleCm, 1.0) + float2(3.3, 57.7);
float2 ic = floor(pc); float2 fc = frac(pc); float2 sc = fc * fc * (3.0 - 2.0 * fc);
float c1 = frac(sin(dot(ic, float2(127.1, 311.7))) * 43758.5453);
float c2 = frac(sin(dot(ic + float2(1.0, 0.0), float2(127.1, 311.7))) * 43758.5453);
float c3 = frac(sin(dot(ic + float2(0.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float c4 = frac(sin(dot(ic + float2(1.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float blotch = lerp(lerp(c1, c2, sc.x), lerp(c3, c4, sc.x), sc.y);
return float3(wall * saturate(band * GrimeBaseAmount + streak * StreakAmount), wall * blotch * PatchAmount, wall * streak * StreakAmount);'''

HLSL_RESERVED = {
    "noise", "sample", "patch", "line", "point", "triangle", "texture", "sampler", "half", "string",
    "vector", "matrix", "interface", "class", "struct", "register", "packoffset", "export", "shared",
    "static", "uniform", "volatile", "in", "out", "inout", "linear", "centroid", "precise", "snorm",
    "unorm", "output", "input", "decl", "pass", "technique", "buffer", "template", "this", "unsigned",
    "signed", "extern", "inline", "switch", "case", "default", "union", "typedef", "namespace",
}

EXPR = "/Script/Engine.MaterialExpression"


def ref(path):
    return {"refPath": path}


class Mat:
    def __init__(self, ue, path):
        self.ue, self.path = ue, path
        self.prefix = path + ":MaterialExpression"

    def node(self, name):
        return self.prefix + name

    def add(self, cls, x, y):
        r = self.ue.call(M, "add_expression", {
            "material_or_function": ref(self.path),
            "expression_class": ref(f"{EXPR}{cls}"), "x": x, "y": y})
        return r["refPath"] if isinstance(r, dict) else r

    def props(self, expr, values):
        ok = self.ue.call(O, "set_properties", {"instance": ref(expr), "values": json.dumps(values)})
        return ok

    def get(self, expr, names):
        r = self.ue.call(O, "get_properties", {"instance": ref(expr), "properties": names})
        return json.loads(r) if isinstance(r, str) else r

    def connect(self, src, out, dst, inp):
        r = self.ue.call(M, "connect_expressions", {
            "from_expression": ref(src), "from_output_name": out,
            "to_expression": ref(dst), "to_input_name": inp})
        if r is False:
            raise RuntimeError(f"connect failed {src} {out} -> {dst} {inp}")

    def inputs(self, expr):
        return self.ue.call(M, "get_expression_inputs", {
            "material_or_function": ref(self.path), "expression": ref(expr)})


def short(p):
    if isinstance(p, dict):
        p = p.get("refPath")
    if not isinstance(p, str):
        return p
    return p.split("MaterialExpression")[-1]


def lint():
    problems = []
    idents = set(re.findall(r"\b[A-Za-z_]\w*\b", HLSL))
    for r in sorted(idents & HLSL_RESERVED):
        problems.append(f"reserved word used: {r}")
    for name in CUSTOM_INPUTS + [n for n, _ in VECTORS]:
        if name in [n for n, _ in VECTORS]:
            continue  # vectors are used outside the Custom node
        if not re.search(rf"\b{name}\b", HLSL):
            problems.append(f"input never used in the code: {name}")
    if re.search(r"\bStreakRoughness\b", HLSL):
        problems.append("StreakRoughness must not be in the code")
    return problems


def add_params(m, x0, y0, scalars_out, vectors_out):
    y = y0
    for name, default in SCALARS:
        e = m.add("ScalarParameter", x0, y)
        m.props(e, {"parameterName": name, "defaultValue": default, "group": GROUP})
        scalars_out[name] = e
        y += 120
    for name, (r, g, b) in VECTORS:
        e = m.add("VectorParameter", x0, y)
        m.props(e, {"parameterName": name, "defaultValue": {"r": r, "g": g, "b": b, "a": 1.0}, "group": GROUP})
        vectors_out[name] = e
        y += 200


def add_custom(m, x, y, wpos, nrm, scalars):
    c = m.add("Custom", x, y)
    m.props(c, {"description": "LB_WeatherMask", "code": HLSL, "outputType": "CMOT_Float3"})
    # set_properties can't grow an array and change elements in one call: a new Custom node has one
    # input, so grow with copies of that element first, then rename them.
    first = json.loads(m.ue.call(O, "get_properties", {"instance": ref(c), "properties": ["inputs"]}))["inputs"][0]
    m.props(c, {"inputs": [first] * len(CUSTOM_INPUTS)})
    els = json.loads(m.ue.call(O, "get_properties", {"instance": ref(c), "properties": ["inputs"]}))["inputs"]
    for el, n in zip(els, CUSTOM_INPUTS):
        el["inputName"] = n
    m.props(c, {"inputs": els})
    m.connect(wpos, "XYZ", c, "WorldPos")
    m.connect(nrm, "", c, "NormalWS")
    for n in CUSTOM_INPUTS[2:]:
        m.connect(scalars[n], "", c, n)
    return c


def stage_check(ue):
    m = Mat(ue, MASTER)
    ex = ue.call(M, "get_expressions", {"material_or_function": ref(MASTER)})
    lp = ue.call(MI, "list_parameters", {"material": ref(MASTER)})
    print("expressions", len(ex), "parameters", len(lp))
    for n in ["LinearInterpolate_12", "StaticSwitchParameter_11", "LinearInterpolate_13", "StaticSwitchParameter_17"]:
        print(n, [(i["input_name"], short(i["expression"])) for i in m.inputs(m.node(n))])
    print("lint:", lint() or "clean")


def stage_test(ue):
    probs = lint()
    if probs:
        raise SystemExit("lint: " + "; ".join(probs))
    if ue.call(AS, "exists", {"path": TEST.rsplit(".", 1)[0]}):
        ue.call(AS, "delete", {"path": TEST.rsplit(".", 1)[0]})  # leftover of a failed earlier run (throwaway asset)
    ue.call(M, "create_material", {"folder_path": TEST_FOLDER, "asset_name": TEST_NAME})
    m = Mat(ue, TEST)
    scalars, vectors = {}, {}
    add_params(m, -1400, 0, scalars, vectors)
    wp = m.add("WorldPosition", -900, -300)
    vn = m.add("VertexNormalWS", -900, -150)
    c = add_custom(m, -300, 0, wp, vn, scalars)
    # BaseColor <- Custom (Float3). Roughness left default.
    ue.call(M, "connect_to_output", {"expression": ref(c), "output_name": "", "material_property": "MP_BaseColor"})
    print("custom:", c)
    print("inputs:", [(i["input_name"], short(i["expression"])) for i in m.inputs(c)])
    ue.call(M, "recompile", {"material_or_function": ref(TEST)})
    print("TEST RECOMPILE OK")


# Layout for the new master nodes (far right of the existing graph).
X0, Y0 = 9000, -3000


def find_existing(ue, m, names_by_class):
    """Resume support: map parameter name -> refPath for weathering nodes a half-finished run already added."""
    found = {}
    ex = ue.call(M, "get_expressions", {"material_or_function": ref(m.path)})
    for e in ex:
        path = e["refPath"]
        cls = path.split("MaterialExpression")[-1].rsplit("_", 1)[0]
        if cls in names_by_class:
            g = m.get(path, ["parameterName", "group"])
            if g.get("group") == GROUP and g.get("parameterName") in names_by_class[cls]:
                found[g["parameterName"]] = path
        elif cls == "Custom":
            if m.get(path, ["description"]).get("description") == "LB_WeatherMask":
                found["__custom__"] = path
    return found


def stage_master_add(ue):
    probs = lint()
    if probs:
        raise SystemExit("lint: " + "; ".join(probs))
    m = Mat(ue, MASTER)
    found = find_existing(ue, m, {"ScalarParameter": [n for n, _ in SCALARS], "VectorParameter": [n for n, _ in VECTORS]})
    ex = ue.call(M, "get_expressions", {"material_or_function": ref(MASTER)})
    if not found and len(ex) != 164:
        raise SystemExit(f"expected 164 expressions, found {len(ex)}; refusing to add")
    if any("StaticSwitchParameter" in e["refPath"] and m.get(e["refPath"], ["parameterName"])["parameterName"] == "bWeathering" for e in ex):
        raise SystemExit("bWeathering switches already exist; refusing to add them twice")
    scalars = {n: found[n] for n, _ in SCALARS if n in found}
    vectors = {n: found[n] for n, _ in VECTORS if n in found}
    if scalars or vectors:
        if len(scalars) != len(SCALARS) or len(vectors) != len(VECTORS):
            raise SystemExit(f"partial parameter set found ({len(scalars)}/{len(SCALARS)} scalars, {len(vectors)}/{len(VECTORS)} vectors); stop and inspect")
        print("resuming: parameters already present")
    else:
        add_params(m, X0, Y0, scalars, vectors)
    wp = m.node("WorldPosition_0")
    vn = m.node("VertexNormalWS_2")
    if "__custom__" in found:
        c = found["__custom__"]
        print("resuming: Custom node already present", short(c))
    else:
        c = add_custom(m, X0 + 600, Y0, wp, vn, scalars)
    masks = {}
    for i, ch in enumerate("rgb"):
        e = m.add("ComponentMask", X0 + 1000, Y0 + i * 150)
        m.props(e, {"r": ch == "r", "g": ch == "g", "b": ch == "b", "a": False})
        m.connect(c, "", e, "None")  # ComponentMask's input pin is called "None"
        masks[ch] = e
    one = m.add("Constant3Vector", X0 + 1000, Y0 + 500)
    m.props(one, {"constant": {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}})
    lg = m.add("LinearInterpolate", X0 + 1400, Y0)
    lp = m.add("LinearInterpolate", X0 + 1400, Y0 + 250)
    m.connect(one, "", lg, "A")
    m.connect(vectors["GrimeTint"], "", lg, "B")
    m.connect(masks["r"], "", lg, "Alpha")
    m.connect(one, "", lp, "A")
    m.connect(vectors["PatchTint"], "", lp, "B")
    m.connect(masks["g"], "", lp, "Alpha")
    mul1 = m.add("Multiply", X0 + 1800, Y0)
    mul2 = m.add("Multiply", X0 + 2000, Y0 + 100)
    m.connect(m.node("Multiply_9"), "", mul1, "A")
    m.connect(lg, "", mul1, "B")
    m.connect(mul1, "", mul2, "A")
    m.connect(lp, "", mul2, "B")
    sw_c = m.add("StaticSwitchParameter", X0 + 2300, Y0)
    m.props(sw_c, {"parameterName": "bWeathering", "defaultValue": False, "group": GROUP})
    m.connect(mul2, "", sw_c, "True")
    m.connect(m.node("Multiply_9"), "", sw_c, "False")
    lr = m.add("LinearInterpolate", X0 + 1400, Y0 + 600)
    m.connect(m.node("Clamp_0"), "", lr, "A")
    m.connect(scalars["StreakRoughness"], "", lr, "B")
    m.connect(masks["b"], "", lr, "Alpha")
    sw_r = m.add("StaticSwitchParameter", X0 + 2300, Y0 + 600)
    m.props(sw_r, {"parameterName": "bWeathering", "defaultValue": False, "group": GROUP})
    m.connect(lr, "", sw_r, "True")
    m.connect(m.node("Clamp_0"), "", sw_r, "False")
    names = {"custom": c, "mask_r": masks["r"], "mask_g": masks["g"], "mask_b": masks["b"], "one": one,
             "lerp_grime": lg, "lerp_patch": lp, "mul1": mul1, "mul2": mul2, "switch_base": sw_c,
             "lerp_rough": lr, "switch_rough": sw_r,
             "scalars": scalars, "vectors": vectors}
    json.dump(names, open(NODES_FILE, "w"), indent=1)
    print("added; nodes saved to", NODES_FILE)
    print(json.dumps({k: (short(v) if isinstance(v, str) else {a: short(b) for a, b in v.items()}) for k, v in names.items()}, indent=1))


NODES_FILE = r"C:\Hemant\Prj\Learning\TheLastBell\Saved\Logs\p11_5a_nodes.json"


def stage_master_verify(ue):
    n = json.load(open(NODES_FILE))
    m = Mat(ue, MASTER)
    for k in ["custom", "mask_r", "mask_g", "mask_b", "lerp_grime", "lerp_patch", "mul1", "mul2",
              "switch_base", "lerp_rough", "switch_rough"]:
        print(k, short(n[k]), [(i["input_name"], i["output_name"], short(i["expression"])) for i in m.inputs(n[k])])
    ex = ue.call(M, "get_expressions", {"material_or_function": ref(MASTER)})
    lp = ue.call(MI, "list_parameters", {"material": ref(MASTER)})
    print("expressions", len(ex), "parameters", len(lp))


def stage_master_rewire(ue):
    n = json.load(open(NODES_FILE))
    m = Mat(ue, MASTER)
    sb, sr = n["switch_base"], n["switch_rough"]
    pairs = [(sb, "LinearInterpolate_12", "A"), (sb, "StaticSwitchParameter_11", "False"),
             (sr, "LinearInterpolate_13", "A"), (sr, "StaticSwitchParameter_17", "False")]
    for src, dst, inp in pairs:
        m.connect(src, "", m.node(dst), inp)
    for dst in ["LinearInterpolate_12", "StaticSwitchParameter_11", "LinearInterpolate_13", "StaticSwitchParameter_17"]:
        print(dst, [(i["input_name"], short(i["expression"])) for i in m.inputs(m.node(dst))])
    print("Switch_BaseColor", [(i["input_name"], short(i["expression"])) for i in m.inputs(sb)])
    print("Switch_Rough", [(i["input_name"], short(i["expression"])) for i in m.inputs(sr)])
    for p in ["MP_BaseColor", "MP_Roughness"]:
        r = ue.call(M, "get_property_input", {"material": ref(MASTER), "material_property": p})
        print(p, short(r["expression"]))


def stage_master_recompile(ue):
    print("recompiling master (once)...", flush=True)
    ue.call(M, "recompile", {"material_or_function": ref(MASTER)})
    print("MASTER RECOMPILE OK")


STAGES = {"check": stage_check, "test": stage_test, "master-add": stage_master_add,
          "master-verify": stage_master_verify, "master-rewire": stage_master_rewire,
          "master-recompile": stage_master_recompile}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in STAGES:
        raise SystemExit("usage: add_weathering_layer.py {" + "|".join(STAGES) + "}")
    STAGES[sys.argv[1]](UE())
