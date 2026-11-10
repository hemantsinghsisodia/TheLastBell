"""P17-4: build the post-process material M_LB_PP_MaskView and its instance MI_LB_PP_MaskView over MCP (editor open, no PIE).

    python p17_4_maskview.py --apply     create or refresh the material graph, recompile, create the MI (parent set at creation) if missing
    python p17_4_maskview.py --check     read everything back (settings, parameters, graph, MI, recompile, dirty state); exit code 1 on any FAIL
    python p17_4_maskview.py --save      save the two new packages, one save_assets call each, each followed by is_dirty

Spec: Docs/plans/P17_CINEMATICS.md section 4.3 (parameter table and the "Exact formula" block).
Route: ONE MaterialExpressionCustom (HLSL) node. The scene colour, screen UV, view size, time and every parameter are separate named inputs of
the node, so the parameters are ordinary Scalar/VectorParameter nodes (tunable on the MI). No texture samples other than SceneTexture:PostProcessInput0.
Never calls MaterialInstanceTools.set_parent, read_graph_dsl or save-all. Never touches any other asset.
"""
import json, sys

sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\lighting")
from p14_lib import ue, ref, OBJ, AST, MAT, MI, setp, props, jl, dirty, exprs, objpath, inputs, short  # noqa: E402

FOLDER = "/Game/LastBell/Materials/PostProcess"
M_NAME, MI_NAME = "M_LB_PP_MaskView", "MI_LB_PP_MaskView"
M_PKG, MI_PKG = FOLDER + "/" + M_NAME, FOLDER + "/" + MI_NAME
M_OBJ, MI_OBJ = objpath(M_PKG), objpath(MI_PKG)
GROUP = "MaskView"

DOMAIN = "MD_PostProcess"
BLENDABLE = "BL_SceneColorAfterTonemapping"      # UE 5.8: the enum also keeps the legacy BL_AfterTonemapping; the plan names this one

# name -> default, exactly as in plan 4.3 "Exact formula"
SCALARS = [
    ("CenterLX", 0.40), ("CenterRX", 0.60), ("CenterY", 0.50),
    ("RadiusX", 0.17), ("RadiusY", 0.085),
    ("Feather", 0.06),
    ("NoseMinX", 0.485), ("NoseMaxX", 0.515), ("NoseAlpha", 0.35),
    ("Darkness", 0.97),
    ("EdgeTint", 0.15),
    ("Breath", 0.02), ("BreathHz", 0.25),
]
VECTORS = [("EdgeTintColor", (1.0, 0.55, 0.40, 1.0))]

# Custom-node input names. 'View' is avoided on purpose (it is the shader's view uniform buffer).
IN_SCENE, IN_UV, IN_VIEW, IN_TIME = "SceneColor", "ScreenUV", "ViewSizePx", "TimeSec"
CUSTOM_INPUTS = [IN_SCENE, IN_UV, IN_VIEW, IN_TIME] + [n for n, _ in SCALARS] + [n for n, _ in VECTORS]

CODE = """\
// Plan 4.3 exact formula. Lengths are in screen-width units (a vertical length in v is multiplied by A).
float A = ViewSizePx.x / max(ViewSizePx.y, 1.0);
float b = 1.0 + Breath * sin(6.28318530718 * BreathHz * TimeSec);
float rx = RadiusX * b;
float ry = RadiusY * b;
float eL = length(float2((ScreenUV.x - CenterLX) / rx, (ScreenUV.y - CenterY) / (ry * A)));
float eR = length(float2((ScreenUV.x - CenterRX) / rx, (ScreenUV.y - CenterY) / (ry * A)));
float sdL = (eL - 1.0) * ry;
float sdR = (eR - 1.0) * ry;
float hf = 0.5 * Feather;
float openL = 1.0 - smoothstep(-hf, hf, sdL);
float openR = 1.0 - smoothstep(-hf, hf, sdR);
float opn = max(openL, openR);
float band = smoothstep(NoseMinX - 0.01, NoseMinX, ScreenUV.x) * (1.0 - smoothstep(NoseMaxX, NoseMaxX + 0.01, ScreenUV.x));
opn = opn * (1.0 - NoseAlpha * band);
float edge = saturate(4.0 * opn * (1.0 - opn));
float3 tint = lerp(float3(1.0, 1.0, 1.0), EdgeTintColor.rgb, EdgeTint * edge);
return SceneColor.rgb * lerp(1.0 - Darkness, 1.0, opn) * tint;
"""

# every package that must stay clean (copy of p14_3_level.NEVER_SAVE + p15_level addition), plus the map
NEVER_SAVE = ["/Game/LastBell/Materials/Master/M_LB_Surface",
              "/Game/LastBell/Blueprints/Puzzles/BP_SmallBell", "/Game/LastBell/Blueprints/Puzzles/BP_SequencePuzzle",
              "/Game/LastBell/Blueprints/Puzzles/BP_Inscription", "/Game/LastBell/Blueprints/Interactables/BP_RitualMechanism",
              "/Game/LastBell/Blueprints/Interactables/BP_Door_Base", "/Game/LastBell/Blueprints/Interactables/BP_TagInteractable",
              "/Game/LastBell/Blueprints/Interactables/BP_TagTrigger", "/Game/LastBell/Blueprints/BP_EndingTrigger",
              "/Game/LastBell/Blueprints/Interactables/BP_Inspectable_Note", "/Game/LastBell/Blueprints/Interactables/BP_Door_Base_Dungeon",
              "/Game/LastBell/Blueprints/Interactables/BP_RitualMechanism_CryptWinch", "/Game/LastBell/Blueprints/Interactables/BP_WardenApparition",
              "/Game/LastBell/Blueprints/Puzzles/BP_PuzzleCandle"]
MAP_PKG = "/Game/LastBell/Maps/L_Monastery"
SPIKE_PKG = "/Game/LastBell/ArtTest/P17/LS_P17_Spike"      # dirty from the lead's in-memory edits: never touched, never saved

results = []


def rec(ok, msg):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + msg, flush=True)
    return bool(ok)


def info(msg):
    print("INFO  " + msg, flush=True)


def near(a, b, tol=1e-5):
    return abs(float(a) - float(b)) <= tol


# ------------------------------------------------------------------------------------------------------ apply
def add_expr(cls, x, y, **p):
    e = ue.call(MAT, "add_expression", {"material_or_function": ref(M_OBJ),
                                        "expression_class": ref("/Script/Engine.MaterialExpression" + cls), "x": x, "y": y})["refPath"]
    if p:
        setp(e, p)
    return e


def link(src, out, dst, pin):
    ue.call(MAT, "connect_expressions", {"from_expression": ref(src), "from_output_name": out, "to_expression": ref(dst), "to_input_name": pin})


def build_custom(x, y):
    """Custom node: grow the inputs array first (copies of the existing element), then rename them (MCP refuses grow+change in one call)."""
    c = add_expr("Custom", x, y)
    first = jl(props(c, ["inputs"]))["inputs"][0]
    setp(c, {"inputs": [first] * len(CUSTOM_INPUTS)})
    setp(c, {"inputs": [{"inputName": n} for n in CUSTOM_INPUTS]})
    setp(c, {"outputType": "CMOT_Float3", "code": CODE, "description": "MaskView: plan 4.3 exact formula"})
    return c


def apply():
    if not ue.call(AST, "exists", {"path": M_PKG}):
        info("create_material -> %s" % ue.call(MAT, "create_material", {"folder_path": FOLDER, "asset_name": M_NAME}))
    for e in exprs(M_OBJ):
        ue.call(MAT, "delete_expression", {"material_or_function": ref(M_OBJ), "expression": ref(e)})
    assert exprs(M_OBJ) == []
    setp(M_OBJ, {"materialDomain": DOMAIN, "blendableLocation": BLENDABLE, "bIsBlendable": True})

    cust = build_custom(1000, 0)
    nodes = {}
    st = add_expr("SceneTexture", 0, 0, sceneTextureId="PPI_PostProcessInput0")
    sp = add_expr("ScreenPosition", 0, 160)
    vs = add_expr("ViewSize", 0, 280)
    tm = add_expr("Time", 0, 360)
    link(st, "Color", cust, IN_SCENE)
    link(sp, "ViewportUV", cust, IN_UV)
    link(vs, "", cust, IN_VIEW)
    link(tm, "", cust, IN_TIME)
    y = 460
    for name, d in SCALARS:
        n = add_expr("ScalarParameter", 0, y, parameterName=name, defaultValue=float(d), group=GROUP)
        link(n, "", cust, name)
        y += 120
    for name, d in VECTORS:
        n = add_expr("VectorParameter", 0, y, parameterName=name, defaultValue={"r": d[0], "g": d[1], "b": d[2], "a": d[3]}, group=GROUP)
        link(n, "RGBA", cust, name)
        y += 120
    ue.call(MAT, "connect_to_output", {"expression": ref(cust), "output_name": "", "material_property": "MP_EmissiveColor"})
    try:
        ue.call(MAT, "layout_expressions", {"material_or_function": ref(M_OBJ)})
    except Exception as ex:
        info("layout failed (cosmetic): %s" % str(ex)[:100])
    info("recompile -> %r" % (ue.call(MAT, "recompile", {"material_or_function": ref(M_OBJ)}),))
    info("expressions: %d" % len(exprs(M_OBJ)))

    if not ue.call(AST, "exists", {"path": MI_PKG}):
        info("MI create (parent set at creation) -> %s" % ue.call(MI, "create", {"folder_path": FOLDER, "asset_name": MI_NAME, "parent": ref(M_OBJ)}))
    else:
        info("MI exists; left as is (never set_parent)")


# ------------------------------------------------------------------------------------------------------ check
def check():
    rec(ue.call(AST, "exists", {"path": M_PKG}), "%s exists" % M_PKG)
    rec(ue.call(AST, "exists", {"path": MI_PKG}), "%s exists" % MI_PKG)

    # --- material settings
    p = jl(props(M_OBJ, ["materialDomain", "blendableLocation", "bIsBlendable"]))
    rec(p.get("materialDomain") == DOMAIN, "Material Domain = %s (read: %s)" % (DOMAIN, p.get("materialDomain")))
    rec(p.get("blendableLocation") == BLENDABLE, "Blendable Location = %s (read: %s)" % (BLENDABLE, p.get("blendableLocation")))
    info("bIsBlendable = %s" % p.get("bIsBlendable"))

    # --- graph: nodes and links
    ex = exprs(M_OBJ)
    by = {}
    for e in ex:
        cls = short(e).rsplit("_", 1)[0]
        by.setdefault(cls, []).append(e)
    info("nodes: " + ", ".join("%s x%d" % (k, len(v)) for k, v in sorted(by.items())))
    rec(len(ex) == 4 + 1 + len(SCALARS) + len(VECTORS), "expression count %d == %d" % (len(ex), 4 + 1 + len(SCALARS) + len(VECTORS)))
    rec(len(by.get("Custom", [])) == 1, "exactly one Custom (HLSL) node")
    rec(len(by.get("TextureSample", [])) + len(by.get("TextureSampleParameter2D", [])) == 0, "no texture sample nodes (SceneTexture only)")

    cust = by["Custom"][0]
    cp = jl(props(cust, ["outputType", "code", "inputs"]))
    rec(cp["outputType"] == "CMOT_Float3", "Custom output type = CMOT_Float3")
    rec(cp["code"].strip() == CODE.strip(), "Custom HLSL code equals the script's formula (%d chars)" % len(cp["code"]))
    rec([i["inputName"] for i in cp["inputs"]] == CUSTOM_INPUTS, "Custom input names: %s" % [i["inputName"] for i in cp["inputs"]])

    st = jl(props(by["SceneTexture"][0], ["sceneTextureId"]))
    rec(st.get("sceneTextureId") == "PPI_PostProcessInput0", "SceneTexture id = PPI_PostProcessInput0 (read: %s)" % st.get("sceneTextureId"))

    wired = {}
    for i in inputs(M_OBJ, cust):
        wired[i["input_name"]] = (short(i["expression"]["refPath"]), i["output_name"], i["expression"]["refPath"]) if i["expression"] else None
    for k, v in wired.items():
        print("LINK  %-14s <- %s" % (k, ("%s%s" % (v[0], (":" + v[1]) if v[1] else "")) if v else "(unconnected)"))
    rec(all(wired.get(n) for n in CUSTOM_INPUTS), "every Custom input is connected (%d)" % len(CUSTOM_INPUTS))
    rec(wired[IN_SCENE] and wired[IN_SCENE][0].startswith("SceneTexture") and wired[IN_SCENE][1] == "Color", "%s <- SceneTexture:Color" % IN_SCENE)
    rec(wired[IN_UV] and wired[IN_UV][0].startswith("ScreenPosition") and wired[IN_UV][1] == "ViewportUV", "%s <- ScreenPosition:ViewportUV" % IN_UV)
    rec(wired[IN_VIEW] and wired[IN_VIEW][0].startswith("ViewSize"), "%s <- ViewSize" % IN_VIEW)
    rec(wired[IN_TIME] and wired[IN_TIME][0].startswith("Time"), "%s <- Time" % IN_TIME)

    # --- parameters: name and default read back from the parameter node that feeds the same-named input
    for name, d in SCALARS:
        w = wired.get(name)
        if not (w and w[0].startswith("ScalarParameter")):
            rec(False, "%s is fed by a ScalarParameter" % name)
            continue
        q = jl(props(w[2], ["parameterName", "defaultValue", "group"]))
        rec(q["parameterName"] == name and near(q["defaultValue"], d), "ScalarParameter %s default %s (read %s) group=%s" % (name, d, q["defaultValue"], q.get("group")))
    for name, d in VECTORS:
        w = wired.get(name)
        if not (w and w[0].startswith("VectorParameter")):
            rec(False, "%s is fed by a VectorParameter" % name)
            continue
        q = jl(props(w[2], ["parameterName", "defaultValue", "group"]))
        dv = q["defaultValue"]
        ok = q["parameterName"] == name and all(near(dv[k], d[i]) for i, k in enumerate("rgba"))
        rec(ok, "VectorParameter %s default %s (read %s)" % (name, d, [round(dv[k], 6) for k in "rgba"]))
    names = [jl(props(e, ["parameterName"]))["parameterName"] for k in ("ScalarParameter", "VectorParameter") for e in by.get(k, [])]
    rec(len(names) == len(set(names)) == len(SCALARS) + len(VECTORS), "%d unique parameter names (no extras)" % len(names))

    # --- output
    po = ue.call(MAT, "get_property_input", {"material": ref(M_OBJ), "material_property": "MP_EmissiveColor"})
    info("MP_EmissiveColor <- %s" % json.dumps(po)[:200])
    rec(cust.split(":")[-1] in json.dumps(po), "Emissive Color is driven by the Custom node")
    for prop in ("MP_BaseColor", "MP_Opacity", "MP_OpacityMask"):
        try:
            o = ue.call(MAT, "get_property_input", {"material": ref(M_OBJ), "material_property": prop})
            rec(not o or not json.dumps(o).count("Expression"), "%s unconnected (emissive only)" % prop)
        except Exception as e_:
            info("%s read skipped: %s" % (prop, str(e_)[:80]))

    # --- compile
    try:
        r = ue.call(MAT, "recompile", {"material_or_function": ref(M_OBJ)})
        rec(r in (None, "", True) or "rror" not in str(r), "recompile clean (returned %r)" % (r,))
    except Exception as e_:
        rec(False, "recompile raised: %s" % str(e_)[:600])

    # --- MI
    mp = jl(props(MI_OBJ, ["parent", "scalarParameterValues", "vectorParameterValues", "textureParameterValues"]))
    par = (mp.get("parent") or {}).get("refPath") if isinstance(mp.get("parent"), dict) else mp.get("parent")
    rec(par == M_OBJ, "MI parent = %s (read: %s)" % (M_OBJ, par))
    rec(not mp.get("scalarParameterValues") and not mp.get("vectorParameterValues") and not mp.get("textureParameterValues"),
        "MI has no overrides (scalar %d, vector %d, texture %d)" % tuple(len(mp.get(k) or []) for k in ("scalarParameterValues", "vectorParameterValues", "textureParameterValues")))
    try:
        lp = ue.call(MI, "list_parameters", {"material": ref(MI_OBJ)})
        info("MI.list_parameters -> %s" % json.dumps(lp)[:900])
    except Exception as e_:
        info("MI.list_parameters failed: %s" % str(e_)[:120])
    for name, d in SCALARS:                     # effective (inherited) values through the MI
        try:
            v = ue.call(MI, "get_scalar_parameter", {"instance": ref(MI_OBJ), "name": name})
            vv = v.get("value", v) if isinstance(v, dict) else v
            rec(near(vv, d), "MI effective %s = %s (expected %s)" % (name, vv, d))
        except Exception as e_:
            info("MI.get_scalar_parameter %s failed: %s" % (name, str(e_)[:100]))
            break

    # --- dirty state
    dirty_check()


def dirty_check():
    d = {p: dirty(p) for p in [MAP_PKG] + NEVER_SAVE}
    for p, v in d.items():
        rec(not v, "%s is not dirty" % p.rsplit("/", 1)[-1])
    info("%s dirty = %s (the lead's in-memory edits: expected, left alone)" % (SPIKE_PKG.rsplit("/", 1)[-1], dirty(SPIKE_PKG)))
    info("%s dirty = %s, %s dirty = %s" % (M_NAME, dirty(M_PKG), MI_NAME, dirty(MI_PKG)))


# ------------------------------------------------------------------------------------------------------ save
def save():
    for pkg in (M_PKG, MI_PKG):
        r = ue.call(AST, "save_assets", {"asset_paths": [pkg]})
        info("save_assets %s -> %r" % (pkg, r))
        rec(not dirty(pkg), "%s not dirty after save" % pkg.rsplit("/", 1)[-1])
    dirty_check()


if __name__ == "__main__":
    a = set(sys.argv[1:])
    if "--apply" in a:
        apply()
    if "--check" in a:
        check()
        print("\n%d PASS, %d FAIL" % (sum(results), len(results) - sum(results)))
    if "--save" in a:
        save()
    if not a & {"--apply", "--check", "--save"}:
        print(__doc__)
    sys.exit(0 if all(results) else 1)
