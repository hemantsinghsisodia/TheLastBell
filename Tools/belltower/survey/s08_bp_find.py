import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
AS = "editor_toolset.toolsets.asset.AssetTools"
B = "editor_toolset.toolsets.blueprint.BlueprintTools"
names = ["BP_SmallBell", "BP_SequencePuzzle", "BP_Inscription", "BP_RitualMechanism", "BP_Door_Base", "BP_TagInteractable", "BP_TagTrigger", "BP_EndingTrigger", "BP_Inspectable_Note"]
out = {}
for n in names:
    r = ue.call(AS, "find_assets", {"folder_path": "/Game/LastBell/Blueprints", "name": n})
    print(n, r)
    out[n] = r
