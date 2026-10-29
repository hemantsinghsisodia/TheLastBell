"""P10-2 (read-only): floor art actors whose AABB reaches the passage / cloister / tower (X > 5800), from Courtyard/Floor and neighbouring folders."""
import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
S = "editor_toolset.toolsets.scene.SceneTools"
A = "editor_toolset.toolsets.actor.ActorTools"
O = "editor_toolset.toolsets.object.ObjectTools"
res = []
for f in ["Courtyard/Floor", "Courtyard/Walls/East", "Courtyard/Walls/East/Plinth", "Courtyard/Dressing/Decals", "Courtyard/Dressing/Overgrowth", "Courtyard/Ivy/East", "Perimeter"]:
    acts = ue.call(S, "get_actors_in_folder", {"folder_path": f, "recursive": False})
    print(f, len(acts), flush=True)
    for x in acts:
        b = ue.call(A, "get_actor_bounds", {"actor": x})
        if b["max"]["x"] < 5900: continue
        lab = ue.call(A, "get_label", {"actor": x})
        try:
            p = ue.call(O, "get_properties", {"instance": {"refPath": x["refPath"] + ".StaticMeshComponent0"}, "properties": ["staticMesh", "overrideMaterials", "bVisible"]})
            p = json.loads(p) if isinstance(p, str) else p
            mesh = (p.get("staticMesh") or {}).get("refPath", "?").split("/")[-1]; mats = [m.get("refPath", "").split("/")[-1] for m in p.get("overrideMaterials", [])]
        except Exception as e:
            mesh, mats = "?", []
        res.append({"folder": f, "label": lab, "min": [b["min"][k] for k in "xyz"], "max": [b["max"][k] for k in "xyz"], "mesh": mesh, "mats": mats})
        print(f, lab, [round(b["min"][k]) for k in "xyz"], [round(b["max"][k]) for k in "xyz"], mesh, mats, flush=True)
json.dump(res, open(r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\floor_east_p10.json", "w"), indent=1)
