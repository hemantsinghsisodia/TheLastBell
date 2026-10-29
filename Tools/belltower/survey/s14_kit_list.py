import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
AS = "editor_toolset.toolsets.asset.AssetTools"
res = {}
for folder in ["/Game/LastBell/Environments", "/Game/LastBell/ThirdParty", "/Game/LastBell/Props", "/Game/LastBell/Meshes", "/Game/LastBell"]:
    try:
        r = ue.call(AS, "find_assets", {"folder_path": folder, "name": "SM_", "asset_type": {"refPath": "/Script/Engine.StaticMesh"}, "recursive": True})
    except Exception as e:
        print(folder, "ERR", str(e)[:200]); continue
    print(folder, len(r))
    res[folder] = r
allm = sorted(set(res.get("/Game/LastBell", [])))
json.dump(allm, open(r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\meshes_list_p10.json", "w"), indent=0)
import collections
c = collections.Counter("/".join(p.split("/")[:6]) for p in allm)
for k, v in sorted(c.items()): print(v, k)
