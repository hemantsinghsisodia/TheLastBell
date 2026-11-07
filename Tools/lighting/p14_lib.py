"""Shared helpers for the P14-2a material tasks (editor open, MCP)."""
import json, sys
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE

ue = UE()
OBJ = "editor_toolset.toolsets.object.ObjectTools"
AST = "editor_toolset.toolsets.asset.AssetTools"
MAT = "editor_toolset.toolsets.material.MaterialTools"
MI = "editor_toolset.toolsets.material_instance.MaterialInstanceTools"


def ref(p):
    return {"refPath": p}


def objpath(pkg):
    return pkg + "." + pkg.rsplit("/", 1)[1]


def props(p, names):
    return ue.call(OBJ, "get_properties", {"instance": ref(p), "properties": names})


def setp(p, values):
    return ue.call(OBJ, "set_properties", {"instance": ref(p), "values": json.dumps(values)})


def dirty(pkg):
    return ue.call(AST, "is_dirty", {"asset_path": pkg})


def exprs(m):
    return [e["refPath"] for e in ue.call(MAT, "get_expressions", {"material_or_function": ref(m)})]


def mi_overrides(pkg):
    p = objpath(pkg)
    r = props(p, ["parent", "scalarParameterValues", "vectorParameterValues", "textureParameterValues"])
    return r


def jl(x):
    return json.loads(x) if isinstance(x, str) else x


def mi_compact(pkg):
    """Parent plus every override as {name: value}."""
    r = jl(props(objpath(pkg), ["parent", "scalarParameterValues", "vectorParameterValues", "textureParameterValues"]))
    out = {"parent": (r.get("parent") or {}).get("refPath")}
    out["scalars"] = {e["parameterInfo"]["name"]: e["parameterValue"] for e in r.get("scalarParameterValues", [])}
    out["vectors"] = {e["parameterInfo"]["name"]: [round(e["parameterValue"][k], 6) for k in "rgba"] for e in r.get("vectorParameterValues", [])}
    out["textures"] = {e["parameterInfo"]["name"]: (e["parameterValue"] or {}).get("refPath") if isinstance(e["parameterValue"], dict) else e["parameterValue"] for e in r.get("textureParameterValues", [])}
    out["static"] = None
    return out


def add(m, cls, x=0, y=0, **p):
    """Add MaterialExpression<cls> and set properties; returns its refPath."""
    e = ue.call(MAT, "add_expression", {"material_or_function": ref(m), "expression_class": ref("/Script/Engine.MaterialExpression" + cls), "x": x, "y": y})["refPath"]
    if p:
        setp(e, p)
    return e


def conn(src, dst, to_input, out=""):
    ue.call(MAT, "connect_expressions", {"from_expression": ref(src), "from_output_name": out, "to_expression": ref(dst), "to_input_name": to_input})


def inputs(m, e):
    return ue.call(MAT, "get_expression_inputs", {"material_or_function": ref(m), "expression": ref(e)})


def input_names(e):
    return ue.call(MAT, "get_expression_input_names", {"expression": ref(e)})


def recompile(m):
    return ue.call(MAT, "recompile", {"material_or_function": ref(m)})


def short(e):
    return e.split(":")[-1].replace("MaterialExpression", "")


def dump_graph(m, extra_keys=("parameterName", "defaultValue", "r", "g", "b", "a", "value", "code", "desc", "texture", "material", "function", "collection",
                              "inputName", "outputName", "constA", "constB", "constant", "mask", "maskR", "maskG", "maskB", "maskA", "exponent", "constExponent", "sRGB", "samplerType", "input", "constB")):
    out = {}
    for e in exprs(m):
        try:
            pr = jl(ue.call(OBJ, "list_properties", {"instance": ref(e)}))
            keys = [k for k in extra_keys if k in pr]
            vals = jl(props(e, keys)) if keys else {}
        except Exception as ex:
            vals = {"err": str(ex)[:60]}
        try:
            ins = [(i["input_name"], short(i["expression"]["refPath"]) + (":" + i["output_name"] if i["output_name"] else "")) for i in inputs(m, e) if i["expression"]]
        except Exception as ex:
            ins = str(ex)[:60]
        out[short(e)] = (vals, ins)
        print(short(e), json.dumps(vals), "<-", ins)
    return out


MPC_REF = ref("/Game/LastBell/Materials/MPC_LB_Storm.MPC_LB_Storm")
MF_FLASH = ref("/Game/LastBell/Materials/Functions/MF_LB_StormFlash.MF_LB_StormFlash")


def flash_node(m, gain_name, x, y, response_param=None, response_const=1.0, fc=None):
    """Create MF_LB_StormFlash(Gain = MPC <gain_name>, Response = scalar param <response_param> or a constant). Returns the call node."""
    fc = fc or add(m, "MaterialFunctionCall", x, y)
    setp(fc, {"materialFunction": MF_FLASH})
    g = add(m, "CollectionParameter", x - 300, y, collection=MPC_REF, parameterName=gain_name)
    conn(g, fc, "Gain")
    if response_param:
        r = add(m, "ScalarParameter", x - 300, y + 120, parameterName=response_param, defaultValue=1.0, group="Storm")
    else:
        r = add(m, "Constant", x - 300, y + 120, r=response_const)
    conn(r, fc, "Response")
    return fc
