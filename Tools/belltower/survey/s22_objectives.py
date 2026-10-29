import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
O = "editor_toolset.toolsets.object.ObjectTools"
ref = {"refPath": "/Game/LastBell/Data/DA_ObjectiveChain_Main.DA_ObjectiveChain_Main"}
r = ue.call(O, "get_properties", {"instance": ref, "properties": ["objectives"]})
d = json.loads(r) if isinstance(r, str) else r
json.dump(d, open(r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\objectives_p10.json", "w"), indent=1)
for o in d["objectives"]:
    print(json.dumps(o)[:420])
