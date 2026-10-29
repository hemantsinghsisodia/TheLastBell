"""P10-2: read the 'Ground' folder (floor slabs) + Navigation volume; read-only."""
import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
S = "editor_toolset.toolsets.scene.SceneTools"
A = "editor_toolset.toolsets.actor.ActorTools"
O = "editor_toolset.toolsets.object.ObjectTools"
OUT = r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\ground_nav_p10.json"
res = {"ground": [], "nav": []}
for x in ue.call(S, "get_actors_in_folder", {"folder_path": "Ground", "recursive": False}):
    lab = ue.call(A, "get_label", {"actor": x})
    b = ue.call(A, "get_actor_bounds", {"actor": x})
    p = ue.call(O, "get_properties", {"instance": {"refPath": x["refPath"] + ".StaticMeshComponent0"}, "properties": ["staticMesh", "bVisible", "bodyInstance", "overrideMaterials"]})
    p = json.loads(p) if isinstance(p, str) else p
    res["ground"].append({"label": lab, "bounds": b, "mesh": (p.get("staticMesh") or {}).get("refPath"), "bVisible": p.get("bVisible"),
                          "collisionProfile": p.get("bodyInstance", {}).get("collisionProfileName"),
                          "materials": [m.get("refPath") for m in p.get("overrideMaterials", [])]})
for x in ue.call(S, "get_actors_in_folder", {"folder_path": "Navigation", "recursive": False}):
    lab = ue.call(A, "get_label", {"actor": x})
    b = ue.call(A, "get_actor_bounds", {"actor": x})
    t = ue.call(A, "get_actor_transform", {"actor": x})
    cls = ue.call(O, "get_class", {"instance": x})
    res["nav"].append({"label": lab, "class": cls, "bounds": b, "transform": t})
json.dump(res, open(OUT, "w"), indent=1)
for g in res["ground"]:
    bb = g["bounds"]
    print(g["label"], "X %g..%g Y %g..%g Z %g..%g" % (bb["min"]["x"], bb["max"]["x"], bb["min"]["y"], bb["max"]["y"], bb["min"]["z"], bb["max"]["z"]), g["collisionProfile"], g["bVisible"], g["mesh"].split("/")[-1])
print(res["nav"])
