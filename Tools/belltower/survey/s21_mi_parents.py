import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
O = "editor_toolset.toolsets.object.ObjectTools"
base = {"Env/MI_Env_TowerStone": "/Game/LastBell/Environments/Courtyard/Materials/MI_Env_TowerStone",
 "MI_LB_Bronze": "/Game/LastBell/Materials/Instances/MI_LB_Bronze", "MI_LB_Iron": "/Game/LastBell/Materials/Instances/MI_LB_Iron", "MI_LB_Stone": "/Game/LastBell/Materials/Instances/MI_LB_Stone",
 "MI_Kit_Masonry": "/Game/LastBell/Environments/Kit/Materials/MI_Kit_Masonry", "MI_Kit_Trim": "/Game/LastBell/Environments/Kit/Materials/MI_Kit_Trim", "MI_Kit_Rubble": "/Game/LastBell/Environments/Kit/Materials/MI_Kit_Rubble",
 "MI_Kit_Slate": "/Game/LastBell/Environments/Kit/Materials/MI_Kit_Slate", "MI_Crypt_StoneWA": "/Game/LastBell/Environments/Crypt/Materials/MI_Crypt_StoneWA",
 "MI_Prop_Rope": "/Game/LastBell/Environments/Courtyard/Materials/MI_Prop_Rope", "MI_Prop_Wood_Weathered": "/Game/LastBell/Environments/Courtyard/Materials/MI_Prop_Wood_Weathered",
 "MI_Chapel_Wood_Old": "/Game/LastBell/Environments/Chapel/Materials/MI_Chapel_Wood_Old", "MI_Crypt_Wood_Wet": "/Game/LastBell/Environments/Crypt/Materials/MI_Crypt_Wood_Wet",
 "MI_Chapel_Masonry_Interior": "/Game/LastBell/Environments/Chapel/Materials/MI_Chapel_Masonry_Interior", "MI_Env_Floor_Puddled": "/Game/LastBell/Environments/Courtyard/Materials/MI_Env_Floor_Puddled",
 "MI_Crypt_Iron": "/Game/LastBell/Environments/Crypt/Materials/MI_Crypt_Iron", "MI_Prop_Iron_Rusty": "/Game/LastBell/Environments/Courtyard/Materials/MI_Prop_Iron_Rusty"}
out = {}
for k, p in base.items():
    ref = {"refPath": p + "." + p.split("/")[-1]}
    try:
        r = ue.call(O, "get_properties", {"instance": ref, "properties": ["parent"]})
        out[k] = json.loads(r)["parent"] if isinstance(r, str) else r["parent"]
    except Exception as e:
        out[k] = "ERR " + str(e)[:100]
    print(k, out[k])
