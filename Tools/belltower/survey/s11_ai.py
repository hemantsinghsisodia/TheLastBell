"""P10-2 item 3 (read-only): AI markers (Patrol/Search/Spawn) and WalkPath points, with locations, route ids, tags."""
import sys, json, re
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
S = "editor_toolset.toolsets.scene.SceneTools"
A = "editor_toolset.toolsets.actor.ActorTools"
O = "editor_toolset.toolsets.object.ObjectTools"
OUT = r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\ai_p10.json"
def jl(x): return json.loads(x) if isinstance(x, str) else x
def getp(ref, names):
    names = list(names)
    for _ in range(8):
        if not names: return {}
        try:
            return jl(ue.call(O, "get_properties", {"instance": {"refPath": ref}, "properties": names}))
        except RuntimeError as e:
            m = re.search(r"could not be read: (.*)$", str(e))
            if not m: return {"_error": str(e)[:200]}
            bad = [x.strip() for x in m.group(1).replace("'", "").split(",")]
            names = [x for x in names if x not in bad]
    return {}
res = {}
for fold, wanted in [("AI/Patrol", "Cloister"), ("AI/Search", "Cloister"), ("AI/Spawn", ""), ("WalkPaths/TowerStairs", ""), ("WalkPaths/CryptToCloister", ""),
                     ("WalkPaths/SacristyToCrypt", None), ("WalkPaths/FloodedLedge", None), ("AI", "")]:
    items = []
    acts = ue.call(S, "get_actors_in_folder", {"folder_path": fold, "recursive": False})
    for x in acts:
        lab = ue.call(A, "get_label", {"actor": x})
        if wanted is None:
            items.append({"label": lab}); continue
        if wanted and wanted not in lab:
            continue
        t = ue.call(A, "get_actor_transform", {"actor": x})["location"]
        cls = ue.call(O, "get_class", {"instance": x})["refPath"].split(".")[-1]
        keys = list(jl(ue.call(O, "list_properties", {"instance": x})).keys())
        own = []
        for k in keys:
            if k in ("primaryActorTick",): break
            own.append(k)
        own = [k for k in own if not re.match(r"^on[A-Z]", k) and k.lower() not in ("rootcomponent",)]
        p = getp(x["refPath"], own + ["tags"])
        items.append({"label": lab, "class": cls, "loc": [round(t["x"], 1), round(t["y"], 1), round(t["z"], 1)], "props": p})
    res[fold] = items
    print(fold, len(items), flush=True)
json.dump(res, open(OUT, "w"), indent=1)
