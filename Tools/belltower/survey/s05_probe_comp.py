import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
O = "editor_toolset.toolsets.object.ObjectTools"
base = "/Game/LastBell/Maps/L_Monastery.L_Monastery:PersistentLevel.BP_SmallBell_C_0"
for c in ["DefaultSceneRoot", "InteractComp", "Bell", "BellPivot"]:
    ref = {"refPath": base + "." + c}
    print("==", c, ue.call(O, "get_class", {"instance": ref}))
    try:
        r = ue.call(O, "get_properties", {"instance": ref, "properties": ["relativeLocation", "relativeRotation", "relativeScale3D", "bVisible", "staticMesh", "overrideMaterials", "nonexistentProp"]})
        print(str(r)[:800])
    except Exception as e:
        print("ERR", str(e)[:300])
lp = ue.call(O, "list_properties", {"instance": {"refPath": base + ".InteractComp"}})
d = json.loads(lp) if isinstance(lp, str) else lp
print(list(d.keys()))
