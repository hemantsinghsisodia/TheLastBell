"""R2-C step 2: replace the 4 Gobo_Moon_Roof_* cubes with the SM_LB_Gobo_RoofHole plate (editor world, PIE stopped)."""
import sys
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\crypt\r1b")
from h import *
D = 150.0
MESH = "/Game/LastBell/Environments/Props/Procedural/Chapel/SM_LB_Gobo_RoofHole.SM_LB_Gobo_RoofHole"
MAT = "/Game/LastBell/Materials/Instances/MI_LB_Iron.MI_LB_Iron"
FOLDER = "Lighting/Chapel/Gobos"
LBL = "Gobo_Moon_Roof"
def axes(pitch, yaw):
    cp, sp, cy, sy = math.cos(math.radians(pitch)), math.sin(math.radians(pitch)), math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return (cp*cy, cp*sy, sp)
sp = find_label("Light_Chapel_Moon_Roof", world="editor"); assert len(sp)==1
L, rot, _ = tf(sp[0]); d = axes(rot[0], rot[1])
ctr = [L[i] + D*d[i] for i in range(3)]
print("spot", L, rot, "-> centre", ctr)
# record old flags (printed earlier in s0_dump): hidden, castShadow, hiddenShadow, DFLighting false, DynIndirect false, RT false, ch1 only, NoCollision
for a in find_label(LBL, world="editor"):
    call(S, "remove_from_scene", {"actor": a}); print("removed old", LBL)
for k in "TBLR":
    for a in find_label("Gobo_Moon_Roof_" + k, world="editor"):
        call(S, "remove_from_scene", {"actor": a}); print("deleted Gobo_Moon_Roof_" + k)
a = call(S, "add_to_scene_from_asset", {"asset_path": MESH, "name": LBL, "xform": xf(ctr, rot, (1,1,1))})
call(A, "set_actor_transform", {"actor": a, "xform": xf(ctr, rot, (1,1,1)), "worldspace": True})
call(A, "set_label", {"actor": a, "label": LBL})
call(S, "set_actor_folder", {"actor": a, "folder_path": FOLDER})
comp = {"refPath": a["refPath"] + ".StaticMeshComponent0"}
setp(comp, {"bHiddenInGame": True, "castShadow": True, "bCastHiddenShadow": True, "bAffectDistanceFieldLighting": False,
            "bAffectDynamicIndirectLighting": False, "bVisibleInRayTracing": False, "bUseDefaultCollision": False,
            "lightingChannels": {"bChannel0": False, "bChannel1": True, "bChannel2": False},
            "bodyInstance": {"collisionProfileName": "NoCollision", "collisionEnabled": "NoCollision"},
            "overrideMaterials": [{"refPath": MAT}]})
st = props(comp, ["bHiddenInGame","castShadow","bCastHiddenShadow","bAffectDistanceFieldLighting","bAffectDynamicIndirectLighting","bVisibleInRayTracing","lightingChannels","bUseDefaultCollision","overrideMaterials","staticMesh"])
bi = props(comp, ["bodyInstance"])["bodyInstance"]
print(json.dumps(st)); print("collision", bi["collisionProfileName"], bi["collisionEnabled"])
print("transform", tf(a)); print("bounds", bounds(a))
