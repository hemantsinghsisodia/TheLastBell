"""P10-2 item 2 (read-only): read_graph_dsl for every graph of the gameplay Blueprints. Checks is_dirty after each Blueprint.
Does NOT delete the _Event_N orphans read_graph_dsl may spawn, does NOT save. Writes Docs/ArtTest/belltower/blueprints_dsl_p10.json"""
import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
AS = "editor_toolset.toolsets.asset.AssetTools"
B = "editor_toolset.toolsets.blueprint.BlueprintTools"
bpdata = json.load(open(r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\blueprints_p10.json"))
OUT = r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\blueprints_dsl_p10.json"
only = sys.argv[1:]
try:
    res = json.load(open(OUT))
except Exception:
    res = {"dsl": {}, "dirty_after_read": {}}
for n, r in bpdata["bps"].items():
    if only and n not in only:
        continue
    res["dsl"][n] = {}
    for g in r["graphs"]:
        gname = g["refPath"].split(":")[-1]
        try:
            res["dsl"][n][gname] = ue.call(B, "read_graph_dsl", {"graph": g})
        except Exception as e:
            res["dsl"][n][gname] = "ERR " + str(e)[:300]
    d = ue.call(AS, "is_dirty", {"asset_path": r["path"]})
    res["dirty_after_read"][n] = d
    print(n, "dirty after read:", d, flush=True)
    json.dump(res, open(OUT, "w"), indent=1)
mapd = ue.call(AS, "is_dirty", {"asset_path": "/Game/LastBell/Maps/L_Monastery"})
res["dirty_after_read"]["MAP"] = mapd
print("MAP dirty", mapd)
json.dump(res, open(OUT, "w"), indent=1)
