import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
S = "editor_toolset.toolsets.scene.SceneTools"
O = "editor_toolset.toolsets.object.ObjectTools"
A = "editor_toolset.toolsets.actor.ActorTools"
d = json.load(open(r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\greybox_p10.json"))
ref = [x for x in d if x["label"] == "Tw_Roof"][0]["ref"]
print(ref)
for k in (["bHidden", "bIsEditorOnlyActor", "tags", "bHiddenEd"], ):
    try: print(ue.call(O, "get_properties", {"instance": {"refPath": ref}, "properties": ["bHidden", "bIsEditorOnlyActor"]}))
    except Exception as e: print("ERR", str(e)[:300])
print(ue.call(O, "get_properties", {"instance": {"refPath": ref + ".StaticMeshComponent0"}, "properties": ["bVisible", "bHiddenInGame", "bRenderInMainPass", "bOwnerNoSee", "castShadow", "scale", "relativeScale3D"]}))
print(ue.call(A, "get_actor_transform", {"actor": {"refPath": ref}}))
# the editor-only layer? find via layers
print(ue.call(O, "get_properties", {"instance": {"refPath": ref}, "properties": ["layers"]}))
