"""Retarget the PIE copy of Light_Approach_0 as the candle proxy TMP_CaptureLight (PIE world only)."""
from h import *
a = find_label("Light_Approach_0", world="pie")
assert len(a) == 1, a
a = a[0]
print("orig", tf(a))
call(A, "set_label", {"actor": a, "label": "TMP_CaptureLight"})
comp = {"refPath": a["refPath"] + ".LightComponent0"}
setp(comp, {"intensityUnits": "Candelas", "intensity": 10.0, "attenuationRadius": 600.0, "bUseTemperature": True, "temperature": 1900.0, "castShadows": False,
            "lightColor": {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}})
print(props(comp, ["intensityUnits", "intensity", "attenuationRadius", "bUseTemperature", "temperature", "castShadows", "lightColor", "volumetricScatteringIntensity", "mobility", "lightFunctionMaterial"]))
print([x["refPath"] for x in call(S, "find_actors", {"name": "TMP_CaptureLight", "tag": "", "collision_channels": []})])
