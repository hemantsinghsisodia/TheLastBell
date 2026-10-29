import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
SM = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
O = "editor_toolset.toolsets.object.ObjectTools"
p = "/Game/LastBell/Environments/Kit/SM_LB_Kit_ArcadeBay_1000x60x400.SM_LB_Kit_ArcadeBay_1000x60x400"
m = {"refPath": p}
print(ue.call(SM, "get_bounds", {"mesh": m}))
slots = ue.call(SM, "get_material_slots", {"mesh": m}); print(slots)
for s in slots:
    print(s, ue.call(SM, "get_material", {"mesh": m, "slot_name": s}))
print(ue.call(SM, "is_nanite_enabled", {"mesh": m}))
print(ue.call(SM, "get_triangle_count", {"mesh": m, "lod_index": 0}))
r = ue.call(O, "get_properties", {"instance": m, "properties": ["bodySetup"]})
print(r)
bs = json.loads(r)["bodySetup"] if isinstance(r, str) else r["bodySetup"]
print(bs)
r2 = ue.call(O, "get_properties", {"instance": bs, "properties": ["aggGeom", "collisionTraceFlag"]})
print(str(r2)[:1500])
