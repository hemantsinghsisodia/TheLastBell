import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
S = "editor_toolset.toolsets.scene.SceneTools"
A = "editor_toolset.toolsets.actor.ActorTools"
O = "editor_toolset.toolsets.object.ObjectTools"
for f in ["Gameplay/Cloister", "Gameplay/BellTower", "Gameplay/Notes", "Gameplay", "AI", "AI/Patrol", "AI/Search", "AI/Spawn", "Navigation", "WalkPaths/TowerStairs", "WalkPaths/CryptToCloister"]:
    r = ue.call(S, "get_actors_in_folder", {"folder_path": f, "recursive": False})
    print("==", f, len(r))
    if len(r) < 40:
        for x in r:
            lab = ue.call(A, "get_label", {"actor": x})
            print("  ", lab, x["refPath"].split(":")[-1])
