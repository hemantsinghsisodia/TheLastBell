"""P14-2a: record the 'before' overrides of every MI the task touches (read-only)."""
import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\lighting")
from p14_lib import *

MIS = {
 "sky": ["/Game/LastBell/ArtTest/Sky/MI_NightStormSky", "/Game/LastBell/Environments/Courtyard/Materials/MI_Env_NightSky"],
 "glass": ["/Game/LastBell/Environments/Chapel/Materials/MI_Glass_Clue_Saints", "/Game/LastBell/Materials/Instances/MI_Glass_Lancet_A",
           "/Game/LastBell/Materials/Instances/MI_Glass_Lancet_B", "/Game/LastBell/Materials/Instances/MI_Glass_Broken", "/Game/LastBell/Materials/Instances/MI_Glass_East"],
 "shaft": ["/Game/LastBell/Materials/Instances/MI_LightShaft_Roof", "/Game/LastBell/Materials/Instances/MI_LightShaft_Window", "/Game/LastBell/Environments/Crypt/Materials/MI_LightShaft_Crypt"],
 "chalk": ["/Game/LastBell/Materials/Instances/MI_Decal_ChalkSigil", "/Game/LastBell/Materials/Instances/MI_Decal_ChalkTally",
           "/Game/LastBell/Materials/Instances/MI_Decal_ChalkCircle", "/Game/LastBell/Materials/Instances/MI_Decal_DragMarks"],
 "pool": [],
}
if __name__ == "__main__":
    out = {}
    for k, lst in MIS.items():
        for p in lst:
            out[p.rsplit("/", 1)[1]] = mi_compact(p)
    path = sys.argv[1]
    json.dump(out, open(path, "w"), indent=1, sort_keys=True)
    for n, v in out.items():
        print(n, json.dumps(v))
