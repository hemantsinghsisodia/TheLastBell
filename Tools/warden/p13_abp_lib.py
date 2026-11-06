"""Small helpers over Tools/mcp/ue.py for building the Warden Animation Blueprint (P13-6)."""
import json
import sys

sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE  # noqa: E402

BPT = "editor_toolset.toolsets.blueprint.BlueprintTools"
OBJ = "editor_toolset.toolsets.object.ObjectTools"
AST = "editor_toolset.toolsets.asset.AssetTools"

_ue = None


def ue():
    global _ue
    if _ue is None:
        _ue = UE()
    return _ue


def call(toolset, tool, args=None):
    return ue().call(toolset, tool, args or {})


def ref(path):
    return {"refPath": path}


def bp_call(tool, args=None):
    return call(BPT, tool, args)


def pin(node_path, direction, index):
    return {"node": ref(node_path), "direction": direction, "index_id": index}


def get_graph(bp_path, name):
    return bp_call("get_graph", {"blueprint": ref(bp_path), "graph_name": name})["refPath"]


def list_graphs(bp_path):
    return [g["refPath"] for g in bp_call("list_graphs", {"blueprint": ref(bp_path)})]


def find_nodes(graph_path, title="", node_class=None):
    a = {"graph": ref(graph_path), "title": title}
    if node_class:
        a["node_class"] = ref(node_class)
    return [n["refPath"] for n in bp_call("find_nodes", a)]


def infos(node_paths):
    return bp_call("get_node_infos", {"nodes": [ref(p) for p in node_paths]})


def create_node(graph_path, type_id, x, y, declaring_class=None):
    a = {"graph": ref(graph_path), "type_id": type_id, "pos": {"x": x, "y": y}}
    if declaring_class:
        a["declaring_class"] = ref(declaring_class)
    r = bp_call("create_node", a)
    return r["refPath"] if isinstance(r, dict) else r


def connect(out_node, out_idx, in_node, in_idx):
    return bp_call("connect_pins", {"output_pin": pin(out_node, "EGPD_Output", out_idx),
                                    "input_pin": pin(in_node, "EGPD_Input", in_idx)})


def set_pin(node, idx, value):
    return bp_call("set_pin_value", {"pin": pin(node, "EGPD_Input", idx), "value": value})


def compile_bp(bp_path, warnings_as_errors=False):
    return bp_call("compile_blueprint", {"blueprint": ref(bp_path), "warnings_as_errors": warnings_as_errors})


def get_props(path, props):
    return call(OBJ, "get_properties", {"instance": ref(path), "properties": props})


def set_props(path, values):
    return call(OBJ, "set_properties", {"instance": ref(path), "values": json.dumps(values)})


def show(x, n=3000):
    s = json.dumps(x, indent=1) if not isinstance(x, str) else x
    print(s[:n])
