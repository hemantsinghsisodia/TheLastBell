import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
AS = "editor_toolset.toolsets.asset.AssetTools"
out = {}
for cls in ["/Script/Engine.MaterialInstanceConstant", "/Script/Engine.Material"]:
    r = ue.call(AS, "find_assets", {"folder_path": "/Game/LastBell", "name": "", "asset_type": {"refPath": cls}, "recursive": True})
    out[cls] = r
    print(cls, len(r))
json.dump(out, open(r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\materials_list_p10.json", "w"), indent=0)
for p in out["/Script/Engine.Material"]: print(p)
import collections
for p in out["/Script/Engine.MaterialInstanceConstant"]:
    if any(k in p for k in ("/Kit/", "/Chapel", "/Courtyard/Materials", "Materials/Instances", "/Crypt/Materials", "Prop")) and "/ThirdParty/" not in p:
        print("MI", p)
