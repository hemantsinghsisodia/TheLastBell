"""Read-only headless probe (P13-6 follow-up): reference-pose local offsets of the Warden's chain bones, to size physics capsules.
Run: UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this> -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>
Writes Docs/ArtTest/warden/p13_bone_probe.json. Saves nothing."""
import json
import unreal

SKEL = "/Game/LastBell/Characters/Warden/Meshes/SK_Warden_Skeleton"
OUT = r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\warden\p13_bone_probe.json"

skel = unreal.load_asset(SKEL)
pose = unreal.AnimPoseExtensions.get_reference_pose(skel)
res = {}
bones = [f"chain_{s}_{i:02d}" for s in ("l", "r") for i in range(12)] + [f"chain_neck_{i:02d}" for i in range(17)]
for b in bones:
    loc = unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.LOCAL)
    wld = unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD)
    res[b] = {"local_t": [float(loc.translation.x), float(loc.translation.y), float(loc.translation.z)],
              "world_t": [float(wld.translation.x), float(wld.translation.y), float(wld.translation.z)]}
json.dump(res, open(OUT, "w"), indent=1)
unreal.log("P13 bone probe wrote %d bones" % len(res))
