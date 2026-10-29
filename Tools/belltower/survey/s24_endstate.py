"""P10-2 end-state check (read-only): map dirty, BP dirty flags, TMP_ actors, throttle setting, PIE running."""
import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
AS = "editor_toolset.toolsets.asset.AssetTools"
S = "editor_toolset.toolsets.scene.SceneTools"
O = "editor_toolset.toolsets.object.ObjectTools"
E = "EditorToolset.EditorAppToolset"
print("map dirty", ue.call(AS, "is_dirty", {"asset_path": "/Game/LastBell/Maps/L_Monastery"}))
bps = json.load(open(r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\blueprints_p10.json"))["bps"]
for n, r in bps.items():
    print(n, "dirty", ue.call(AS, "is_dirty", {"asset_path": r["path"]}))
print("TMP_ actors:", ue.call(S, "find_actors", {"name": "TMP_", "tag": "", "collision_channels": []}))
print("PIE running:", ue.call(E, "IsPIERunning", {}))
for p in ["/Script/UnrealEd.Default__EditorPerformanceSettings", "/Script/UnrealEd.EditorPerformanceSettings"]:
    try:
        print(p, ue.call(O, "get_properties", {"instance": {"refPath": p}, "properties": ["bThrottleCPUWhenNotForeground"]}))
        break
    except Exception as e:
        print(p, "ERR", str(e)[:150])
print("level", ue.call(S, "get_current_level", {}))
