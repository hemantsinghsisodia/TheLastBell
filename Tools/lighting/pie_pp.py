"""P14-4 look session: change post-process values on the PIE-WORLD copies only (they vanish when PIE stops; nothing is saved).

    python -I Tools/lighting/pie_pp.py start            start PIE Simulate (if not running) and wait for it
    python -I Tools/lighting/pie_pp.py stop             stop PIE
    python -I Tools/lighting/pie_pp.py read             print the PIE-world volumes' exposure and grade fields
    python -I Tools/lighting/pie_pp.py ev <EV100>       PIE-world PP_Chapel: min = max EV100
    python -I Tools/lighting/pie_pp.py grade A|B|C      PIE-world PostProcess_Exposure grade (plan section 9.1 step 3);
                                                        B and C also clear the per-area satShadows overrides, A puts them back

Every write is read back. The script refuses to touch anything whose refPath lacks "UEDPIE" (the editor world).
The originals are recorded on the first grade call in Saved/p14_4_pie_pp_originals.json (per PIE session: delete it after StopPIE).
"""
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Tools", "mcp"))
from ue import UE  # noqa: E402

S = "editor_toolset.toolsets.scene.SceneTools"
O = "editor_toolset.toolsets.object.ObjectTools"
A = "editor_toolset.toolsets.actor.ActorTools"
E = "EditorToolset.EditorAppToolset"
ORIG = os.path.join(ROOT, "Saved", "p14_4_pie_pp_originals.json")
AREA = ["PP_Outdoor_Night", "PP_Crypt", "PP_Cloister", "PP_Chapel", "PP_Tower"]
GRADE_FIELDS = ["colorSaturation", "colorContrast", "colorGammaShadows", "colorGainHighlights", "filmGrainIntensity", "vignetteIntensity"]
OVR = {f: "bOverride_" + f[0].upper() + f[1:] for f in GRADE_FIELDS}
V4 = lambda x, y, z, w: {"x": x, "y": y, "z": z, "w": w}  # noqa: E731
GRADES = {
    "B": {"colorSaturation": V4(0.92, 0.95, 1.0, 0.85), "colorContrast": V4(1, 1, 1, 1.06),
          "colorGammaShadows": V4(0.97, 1.0, 1.06, 1), "colorGainHighlights": V4(1.04, 1.0, 0.94, 1),
          "filmGrainIntensity": 0.18, "vignetteIntensity": 0.45},
    "C": {"colorSaturation": V4(1, 1, 1, 0.70), "colorContrast": V4(1, 1, 1, 1.10),
          "colorGammaShadows": V4(0.98, 1.0, 1.03, 1), "colorGainHighlights": V4(1.06, 1.0, 0.92, 1),
          "filmGrainIntensity": 0.25, "vignetteIntensity": 0.55},
}

ue = UE()


def js(r):
    if isinstance(r, (dict, list, bool, int, float)) or r is None:
        return r
    try:
        return json.loads(r)
    except (TypeError, ValueError):
        return r


def pie_actor(label):
    found = js(ue.call(S, "find_actors", {"name": label, "tag": "", "collision_channels": []}) or "[]")
    hits = []
    for a in found:
        ref = a.get("refPath", "")
        if "UEDPIE" not in ref:
            continue
        lab = js(ue.call(A, "get_label", {"actor": {"refPath": ref}}))
        lab = lab.get("label", lab) if isinstance(lab, dict) else lab
        if str(lab).strip('"') == label:
            hits.append(ref)
    if len(hits) != 1:
        raise SystemExit(f"STOP: {len(hits)} PIE-world actors labelled {label}: {hits}")
    return {"refPath": hits[0]}


def settings(ref):
    return js(ue.call(O, "get_properties", {"instance": ref, "properties": ["settings"]}))["settings"]


def setp(ref, values):
    if "UEDPIE" not in ref["refPath"]:
        raise SystemExit("STOP: refusing to write an editor-world actor")
    r = ue.call(O, "set_properties", {"instance": ref, "values": json.dumps(values)})
    if r is not True and str(r).lower() != "true":
        print("set_properties returned:", r)


def summary(st):
    out = {"ev": (st["autoExposureMinBrightness"], st["autoExposureMaxBrightness"]) if st.get("bOverride_AutoExposureMinBrightness") else None,
           "satShadows": st["colorSaturationShadows"] if st.get("bOverride_ColorSaturationShadows") else None}
    for f in GRADE_FIELDS:
        if st.get(OVR[f]):
            out[f] = st[f]
    return out


def read():
    for label in ["PostProcess_Exposure"] + AREA:
        print(f"{label:22s}", json.dumps(summary(settings(pie_actor(label)))))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "read"
    if cmd == "start":
        if not js(ue.call(E, "IsPIERunning")):
            ue.call(E, "StartPIE", {"options": {"bSimulate": True, "playMode": "PlayMode_InViewPort", "warmupSeconds": 5}})
            t = time.time()
            while not js(ue.call(E, "IsPIERunning")):
                if time.time() - t > 120:
                    raise SystemExit("STOP: PIE Simulate did not start")
                time.sleep(2)
        print("PIE running")
        if os.path.exists(ORIG):
            os.remove(ORIG)
        return
    if cmd == "stop":
        if js(ue.call(E, "IsPIERunning")):
            ue.call(E, "StopPIE")
        if os.path.exists(ORIG):
            os.remove(ORIG)
        print("PIE stopped")
        return
    if not js(ue.call(E, "IsPIERunning")):
        raise SystemExit("STOP: PIE is not running (these edits are for the PIE world only)")
    if cmd == "read":
        read()
    elif cmd == "ev":
        v = float(sys.argv[2])
        ref = pie_actor("PP_Chapel")
        setp(ref, {"settings": {"bOverride_AutoExposureMinBrightness": True, "bOverride_AutoExposureMaxBrightness": True,
                                "autoExposureMinBrightness": v, "autoExposureMaxBrightness": v}})
        st = settings(ref)
        ok = abs(st["autoExposureMinBrightness"] - v) < 1e-4 and abs(st["autoExposureMaxBrightness"] - v) < 1e-4
        print(("PASS" if ok else "FAIL"), "PP_Chapel (PIE) EV", st["autoExposureMinBrightness"], st["autoExposureMaxBrightness"])
    elif cmd == "grade":
        g = sys.argv[2].upper()
        glob = pie_actor("PostProcess_Exposure")
        if not os.path.exists(ORIG):
            orig = {"PostProcess_Exposure": {k: v for k, v in settings(glob).items() if k in GRADE_FIELDS or k in OVR.values()}}
            for label in AREA:
                st = settings(pie_actor(label))
                orig[label] = {"bOverride_ColorSaturationShadows": st["bOverride_ColorSaturationShadows"],
                               "colorSaturationShadows": st["colorSaturationShadows"]}
            with open(ORIG, "w") as fh:
                json.dump(orig, fh, indent=1)
        with open(ORIG) as fh:
            orig = json.load(fh)
        if g == "A":
            setp(glob, {"settings": orig["PostProcess_Exposure"]})
            for label in AREA:
                setp(pie_actor(label), {"settings": orig[label]})
        else:
            vals = dict(GRADES[g])
            vals.update({OVR[f]: True for f in GRADE_FIELDS})
            setp(glob, {"settings": vals})
            for label in AREA:
                setp(pie_actor(label), {"settings": {"bOverride_ColorSaturationShadows": False}})
        read()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
