"""P10-2 item 1 (read-only): dump the greybox actors to Docs/ArtTest/belltower/greybox_p10.json."""
import sys, json, time
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
S = "editor_toolset.toolsets.scene.SceneTools"
A = "editor_toolset.toolsets.actor.ActorTools"
O = "editor_toolset.toolsets.object.ObjectTools"
OUT = r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\greybox_p10.json"
FOLDERS = ["Cloister", "BellTower", "BellTower/Stairs", "BellTower/Railings"]
NAMES = ["Passage_S", "Passage_N", "Ground_4", "Ground_6", "KW_Shortcut"]

def refs_in_folder(f):
    return [x["refPath"] for x in ue.call(S, "get_actors_in_folder", {"folder_path": f, "recursive": False})]

def refs_by_name(n):
    r = ue.call(S, "find_actors", {"name": n, "tag": "", "collision_channels": []})
    return [x["refPath"] for x in r]

def rec(ref, folder_hint):
    d = {"ref": ref, "folder_query": folder_hint}
    d["label"] = ue.call(A, "get_label", {"actor": {"refPath": ref}})
    d["bounds"] = ue.call(A, "get_actor_bounds", {"actor": {"refPath": ref}})
    d["transform"] = ue.call(A, "get_actor_transform", {"actor": {"refPath": ref}})
    comp = {"refPath": ref + ".StaticMeshComponent0"}
    try:
        p = ue.call(O, "get_properties", {"instance": comp, "properties": ["staticMesh", "bVisible", "bodyInstance", "overrideMaterials", "bHiddenInGame", "castShadow", "mobility"]})
        if isinstance(p, str):
            p = json.loads(p)
        bi = p.get("bodyInstance", {})
        d["mesh"] = (p.get("staticMesh") or {}).get("refPath")
        d["bVisible"] = p.get("bVisible")
        d["bHiddenInGame"] = p.get("bHiddenInGame")
        d["collisionProfile"] = bi.get("collisionProfileName")
        d["collisionEnabled"] = bi.get("collisionEnabled")
        d["materials"] = [m.get("refPath") if isinstance(m, dict) else m for m in p.get("overrideMaterials", [])]
        d["castShadow"] = p.get("castShadow")
        d["mobility"] = p.get("mobility")
    except Exception as e:
        d["error"] = str(e)[:300]
    return d

t0 = time.time()
seen = {}
for f in FOLDERS:
    for r in refs_in_folder(f):
        if r not in seen:
            seen[r] = f
for n in NAMES:
    for r in refs_by_name(n):
        if r not in seen:
            seen[r] = "name:" + n
print("actors to dump", len(seen), flush=True)
out = []
for i, (r, f) in enumerate(seen.items()):
    out.append(rec(r, f))
    if i % 40 == 0:
        print(i, time.time() - t0, flush=True)
out.sort(key=lambda d: (d["folder_query"], d.get("label", "")))
json.dump(out, open(OUT, "w"), indent=1)
print("wrote", OUT, len(out), time.time() - t0)
