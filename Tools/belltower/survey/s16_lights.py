"""P10-2 (read-only): lights in Lighting/Cloister, Lighting/BellTower, Light_Courtyard_7 and Lighting/Environment (moon, sky, fog, PP)."""
import sys, json, re
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
S = "editor_toolset.toolsets.scene.SceneTools"
A = "editor_toolset.toolsets.actor.ActorTools"
O = "editor_toolset.toolsets.object.ObjectTools"
OUT = r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\lights_p10.json"
def jl(x): return json.loads(x) if isinstance(x, str) else x
def getp(ref, names):
    names = list(names)
    for _ in range(10):
        if not names: return {}
        try: return jl(ue.call(O, "get_properties", {"instance": {"refPath": ref}, "properties": names}))
        except RuntimeError as e:
            m = re.search(r"could not be read: (.*)$", str(e))
            if not m: return {"_error": str(e)[:200]}
            bad = [x.strip() for x in m.group(1).replace("'", "").split(",")]
            names = [x for x in names if x not in bad]
    return {}
WANT = ["intensity", "lightColor", "attenuationRadius", "sourceRadius", "castShadows", "castVolumetricShadow", "innerConeAngle", "outerConeAngle", "temperature",
        "bUseTemperature", "volumetricScatteringIntensity", "lightFunctionMaterial", "indirectLightingIntensity", "intensityUnits", "bVisible", "lightingChannels"]
out = {}
items = []
for f in ["Lighting/Cloister", "Lighting/BellTower", "Lighting/Environment"]:
    for x in ue.call(S, "get_actors_in_folder", {"folder_path": f, "recursive": False}):
        items.append((f, x))
for x in ue.call(S, "find_actors", {"name": "Light_Courtyard_7", "tag": "", "collision_channels": []}):
    items.append(("name", x))
for f, x in items:
    lab = ue.call(A, "get_label", {"actor": x})
    cls = ue.call(O, "get_class", {"instance": x})["refPath"].split(".")[-1]
    t = ue.call(A, "get_actor_transform", {"actor": x})
    comps = ue.call(A, "get_components", {"actor": x})
    rec = {"folder": f, "class": cls, "loc": [round(t["location"][k], 1) for k in "xyz"], "rot": [round(t["rotation"][k], 1) for k in ("pitch", "yaw", "roll")], "comps": []}
    for c in comps:
        cc = ue.call(O, "get_class", {"instance": c})["refPath"].split(".")[-1]
        if any(k in cc for k in ("Light", "Fog", "Sky", "Post")):
            rec["comps"].append({"name": c["refPath"].split(".")[-1], "class": cc, "props": getp(c["refPath"], WANT)})
    out[lab] = rec
    print(lab, cls, rec["loc"], flush=True)
json.dump(out, open(OUT, "w"), indent=1)
