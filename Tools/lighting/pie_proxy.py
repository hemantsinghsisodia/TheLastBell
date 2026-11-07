"""P14-5: make the player-candle proxy for captures, in the PIE WORLD ONLY (it vanishes when PIE stops; nothing is saved).

    python -I Tools/lighting/pie_proxy.py          retarget the PIE copy of Light_Approach_0 as TMP_CaptureLight

Same method as Tools/crypt/r1b/pie_proxy.py (MCP_NOTES "PIE": SceneTools can't spawn during PIE, so a PIE-world copy of an
existing light is retargeted; the editor-world light is never touched). The values come from DA_PlayerTuning
(CandleIntensity, CandleAttenuationRadius, CandleTemperature), in Candelas, no shadows, white light colour, no light function.
capture_poses.py --light then moves it with the camera (capture_session.py --light-offset 36 14 -10).
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Tools", "mcp"))
from ue import UE  # noqa: E402

S = "editor_toolset.toolsets.scene.SceneTools"
O = "editor_toolset.toolsets.object.ObjectTools"
A = "editor_toolset.toolsets.actor.ActorTools"
E = "EditorToolset.EditorAppToolset"
TUNING = {"refPath": "/Game/LastBell/Data/DA_PlayerTuning.DA_PlayerTuning"}
ue = UE()


def js(r):
    if isinstance(r, (dict, list, bool, int, float)) or r is None:
        return r
    try:
        return json.loads(r)
    except (TypeError, ValueError):
        return r


def pie_by_label(label):
    found = js(ue.call(S, "find_actors", {"name": label, "tag": "", "collision_channels": []})) or []
    out = []
    for a in found:
        if "UEDPIE" not in a.get("refPath", ""):
            continue
        lab = js(ue.call(A, "get_label", {"actor": {"refPath": a["refPath"]}}))
        lab = lab.get("label", lab) if isinstance(lab, dict) else lab
        if str(lab).strip('"') == label:
            out.append(a)
    return out


if not js(ue.call(E, "IsPIERunning")):
    raise SystemExit("STOP: PIE is not running (the proxy is a PIE-world copy)")
existing = pie_by_label("TMP_CaptureLight")
if existing:
    print("TMP_CaptureLight already in the PIE world:", [a["refPath"] for a in existing])
    a = existing[0]
else:
    src = pie_by_label("Light_Approach_0")
    if len(src) != 1:
        raise SystemExit(f"STOP: {len(src)} PIE-world Light_Approach_0")
    a = src[0]
    ue.call(A, "set_label", {"actor": {"refPath": a["refPath"]}, "label": "TMP_CaptureLight"})
t = js(ue.call(O, "get_properties", {"instance": TUNING, "properties": ["candleIntensity", "candleAttenuationRadius", "candleTemperature"]}))
print("DA_PlayerTuning:", t)
comp = {"refPath": a["refPath"] + ".LightComponent0"}
vals = {"intensityUnits": "Candelas", "intensity": float(t["candleIntensity"]), "attenuationRadius": float(t["candleAttenuationRadius"]),
        "bUseTemperature": True, "temperature": float(t["candleTemperature"]), "castShadows": False,
        "lightColor": {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}, "lightFunctionMaterial": None}
if "UEDPIE" not in comp["refPath"]:
    raise SystemExit("STOP: refusing to write an editor-world light")
print("set:", ue.call(O, "set_properties", {"instance": comp, "values": json.dumps(vals)}))
print("now:", ue.call(O, "get_properties", {"instance": comp, "properties": ["intensityUnits", "intensity", "attenuationRadius", "bUseTemperature",
                                                                             "temperature", "castShadows", "lightColor", "lightFunctionMaterial"]}))
print("PIE TMP_CaptureLight:", [x["refPath"] for x in pie_by_label("TMP_CaptureLight")])
