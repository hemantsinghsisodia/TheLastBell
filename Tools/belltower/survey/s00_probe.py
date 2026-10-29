"""P10-2 probe (read-only): editor state, dirty flags, folder list, one actor sample."""
import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
S = "editor_toolset.toolsets.scene.SceneTools"
A = "editor_toolset.toolsets.actor.ActorTools"
O = "editor_toolset.toolsets.object.ObjectTools"
AS = "editor_toolset.toolsets.asset.AssetTools"
print("level", ue.call(S, "get_current_level", {}))
print("map dirty", ue.call(AS, "is_dirty", {"asset_path": "/Game/LastBell/Maps/L_Monastery"}))
f = ue.call(S, "get_folders", {})
print(json.dumps(f)[:6000])
for fold in ["Cloister", "BellTower", "BellTower/Stairs", "BellTower/Railings"]:
    r = ue.call(S, "get_actors_in_folder", {"folder_path": fold, "recursive": False})
    print(fold, type(r), len(r))
    print(json.dumps(r)[:600])
