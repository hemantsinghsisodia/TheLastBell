import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
S = "editor_toolset.toolsets.scene.SceneTools"
A = "editor_toolset.toolsets.actor.ActorTools"
O = "editor_toolset.toolsets.object.ObjectTools"
for name in ["Puzzle_Bells", "Bell_1"]:
    r = ue.call(S, "find_actors", {"name": name, "tag": "", "collision_channels": []})
    print(name, r)
a = ue.call(S, "find_actors", {"name": "Bell_1", "tag": "", "collision_channels": []})[0]
print(ue.call(A, "get_label", {"actor": a}))
print(ue.call(O, "get_class", {"instance": a}))
lp = ue.call(O, "list_properties", {"instance": a})
print(type(lp), len(lp))
if isinstance(lp, str):
    d = json.loads(lp)
else:
    d = lp
print(list(d.keys()) if isinstance(d, dict) else d[:5])
print(ue.call(A, "get_components", {"actor": a}))
