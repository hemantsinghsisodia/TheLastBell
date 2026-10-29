import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
S = "editor_toolset.toolsets.scene.SceneTools"
O = "editor_toolset.toolsets.object.ObjectTools"
A = "editor_toolset.toolsets.actor.ActorTools"
for nm in ["Nav", "Recast", "Modifier", "Link"]:
    r = ue.call(S, "find_actors", {"name": nm, "tag": "", "collision_channels": []})
    print(nm, [(ue.call(A, "get_label", {"actor": x}), x["refPath"].split(":")[-1]) for x in r][:20])
# Project nav settings via ConfigSettings? just try the supported agents
