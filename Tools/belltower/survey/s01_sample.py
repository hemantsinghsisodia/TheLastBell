import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
S = "editor_toolset.toolsets.scene.SceneTools"
O = "editor_toolset.toolsets.object.ObjectTools"
r = ue.call(S, "get_actors_in_folder", {"folder_path": "BellTower", "recursive": False})
c = {"refPath": r[0]["refPath"] + ".StaticMeshComponent0"}
x = ue.call(O, "get_properties", {"instance": c, "properties": ["staticMesh", "bVisible", "bodyInstance", "overrideMaterials", "bHiddenInGame", "castShadow", "mobility"]})
print(x if isinstance(x, str) else json.dumps(x)[:3000])
