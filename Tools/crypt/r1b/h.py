import sys, json, math
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
U = UE()
S = "editor_toolset.toolsets.scene.SceneTools"
A = "editor_toolset.toolsets.actor.ActorTools"
O = "editor_toolset.toolsets.object.ObjectTools"
AS = "editor_toolset.toolsets.asset.AssetTools"
E = "EditorToolset.EditorAppToolset"
MI = "editor_toolset.toolsets.material_instance.MaterialInstanceTools"
LG = "EditorToolset.LogsToolset"
SCR = r"C:\Users\heman\AppData\Local\Temp\claude\C--Hemant-Prj-Learning-TheLastBell\be0022a0-87e7-4517-81e3-bd2aaebbbccb\scratchpad\r1b"


def call(ts, tool, args=None):
    return U.call(ts, tool, args)


def props(inst, names):
    r = call(O, "get_properties", {"instance": inst if isinstance(inst, dict) else {"refPath": inst}, "properties": names})
    return json.loads(r) if isinstance(r, str) else r


def setp(inst, vals):
    return call(O, "set_properties", {"instance": inst if isinstance(inst, dict) else {"refPath": inst}, "values": json.dumps(vals)})


def find_label(label, exact=True, world=None):
    out = []
    for a in call(S, "find_actors", {"name": label, "tag": "", "collision_channels": []}) or []:
        rp = a.get("refPath", "")
        if world == "editor" and "UEDPIE" in rp:
            continue
        if world == "pie" and "UEDPIE" not in rp:
            continue
        lbl = call(A, "get_label", {"actor": a})
        if (lbl == label) if exact else lbl.startswith(label):
            out.append(a)
    return out


def tf(actor):
    t = call(A, "get_actor_transform", {"actor": actor, "worldspace": True})
    return [t["location"][k] for k in "xyz"], [t["rotation"][k] for k in ("pitch", "yaw", "roll")], [t["scale"][k] for k in "xyz"]


def bounds(actor):
    b = call(A, "get_actor_bounds", {"actor": actor})
    return b


def xf(loc, rot=(0, 0, 0), sc=(1, 1, 1)):
    return {"location": dict(zip("xyz", loc)), "rotation": {"pitch": rot[0], "yaw": rot[1], "roll": rot[2]}, "scale": dict(zip("xyz", sc))}
