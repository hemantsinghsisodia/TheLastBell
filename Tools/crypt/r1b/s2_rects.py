"""Spawn the 4 interior RectLights (editor world, PIE stopped). Idempotent: removes its own labels first."""
from h import *
g = json.load(open(SCR + r"\geom.json"))
P = "/Game/LastBell/Maps/L_Monastery.L_Monastery:PersistentLevel."
LIGHT = {"S1": 9100.0, "S2": 9100.0, "S3": 9100.0, "Roof": 15000.0}
if len(sys.argv) > 1:
    LIGHT = json.loads(sys.argv[1])
rot = (-38.0, 35.0, 0.0)
made = {}
for key in ["S1", "S2", "S3", "Roof"]:
    lbl = "Light_Chapel_MoonRect_" + key
    for a in find_label(lbl, world="editor"):
        call(S, "remove_from_scene", {"actor": a})
    d = g[key]
    a = call(S, "add_to_scene_from_class", {"actor_type": {"refPath": "/Script/Engine.RectLight"}, "name": lbl, "xform": xf(d["pos"], rot)})
    call(A, "set_label", {"actor": a, "label": lbl})
    call(S, "set_actor_folder", {"actor": a, "folder_path": "Lighting/Chapel"})
    comp = {"refPath": a["refPath"] + ".LightComponent0"}
    vals = {"sourceWidth": round(d["w"], 2), "sourceHeight": round(d["h"], 2), "barnDoorAngle": 15.0, "barnDoorLength": 40.0,
            "lightColor": {"r": 190 / 255, "g": 205 / 255, "b": 235 / 255, "a": 1.0}, "mobility": "Movable", "castShadows": True,
            "volumetricScatteringIntensity": 0.3, "attenuationRadius": 3000.0,
            "intensityUnits": "Lumens", "intensity": LIGHT[key]}
    setp(comp, vals)
    back = props(comp, list(vals.keys()))
    print(lbl, a["refPath"].split(":")[-1], tf(a))
    print("  ", back)
    made[key] = a["refPath"]
json.dump(made, open(SCR + r"\rects.json", "w"))
