"""P14-5 Part A: apply the owner's P14-4 choices (Docs/plans/P14_5_APPLY.md).

Run with the editor open on L_Monastery, PIE off (Windows python -I):
    python -I Tools/lighting/p14_5_apply.py --apply [--only da,mis,map]
    python -I Tools/lighting/p14_5_apply.py --check [--only da,mis,map] [--no-census]

--apply is idempotent and NEVER saves (the saves are separate, explicit, one package per call, by hand):
  da   A1  DA_StormSettings: phaseSpeedHigh 6.5, windBaseHigh 0.8, gustHigh 0.5, gustFrequency 0.2 (plus the preset B / debug asserts)
  mis  A2  WindAmplitudeCm on the 8 foliage / ivy MIs (set_scalar_parameter only; never set_parent, never a static switch)
  map  A3  PP_Chapel EV 1.6, grade B on PostProcess_Exposure, shadow-saturation override cleared on 4 volumes, 2 reveal decals moved
--check only reads and prints PASS / FAIL per item (exit code 1 on any FAIL).
On a hang over 180 s or a crash the script stops ("STOP", exit code 3): do not save, do not retry a mutation.

Part C updates the EV table below (CHAPEL_EV etc.) when the final exposure values are known.
"""
import argparse
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Tools", "lighting"))
sys.path.insert(0, os.path.join(ROOT, "Tools", "mcp"))
import p14_3_level as L  # noqa: E402
from p14_3_level import EditorStop, J, R, near, v3  # noqa: E402

MI_TS = "editor_toolset.toolsets.material_instance.MaterialInstanceTools"
DA_PKG = "/Game/LastBell/Data/DA_StormSettings"
DA = DA_PKG + ".DA_StormSettings"
MI_DIR = "/Game/LastBell/Environments/Courtyard/Materials/"
TOL = 1e-5

# ---------------------------------------------------------------------------------------------- A1 (preset B and the wind)
DA_SET = {"phaseSpeedHigh": 6.5, "windBaseHigh": 0.8, "gustHigh": 0.5, "gustFrequency": 0.2}          # saved before: 2.4 / 0.65 / 0.4 / 0.12
DA_ASSERT = {"flashLux": 8, "spotFlashGain": 3, "fillFlashGain": 1.5, "skyFlashGain": 0.6, "domeFlashGain": 6, "domeFlashAdd": 0.05,
             "glassFlashGain": 2.5, "shaftFlashGain": 3, "poolFlashGain": 2.5, "revealGain": 4, "revealEmissive": 3,
             "debugFreezeFlash": -1, "debugIntensityOverride": -1, "phaseSpeedLow": 1.2, "windBaseLow": 0.2, "gustLow": 0.15}

# ---------------------------------------------------------------------------------------------- A2
# name: (WindAmplitudeCm, WindRefHeightCm or None = no override). Saved in f9261e6: 30/18/12/18/14/12/4/4.
MIS = {
    "MI_Foliage_GrassMedium02": (38.0, 60.0),
    "MI_Foliage_NettlePlant": (24.0, 45.0),
    "MI_Foliage_WeedPlant02": (16.0, 30.0),
    "MI_Foliage_Fern02": (24.0, 45.0),
    "MI_Foliage_WildRooibos": (18.0, 60.0),
    "MI_Foliage_SearsiaLucida": (16.0, 150.0),
    "MI_Ivy_Green": (5.0, None),
    "MI_Ivy_Dead": (5.0, None),
}

# ---------------------------------------------------------------------------------------------- A3
CHAPEL_EV = 1.6                       # PP_Chapel, min = max (Part C may change it)
GRADE_B = {                            # PostProcess_Exposure: Property -> value (Vectors are x, y, z, w)
    "ColorSaturation": (0.92, 0.95, 1.0, 0.85),
    "ColorContrast": (1.0, 1.0, 1.0, 1.06),
    "ColorGammaShadows": (0.97, 1.0, 1.06, 1.0),
    "ColorGainHighlights": (1.04, 1.0, 0.94, 1.0),
    "FilmGrainIntensity": 0.18,
    "VignetteIntensity": 0.45,
}
SHADOW_SAT_OFF = ["PP_Outdoor_Night", "PP_Cloister", "PP_Chapel", "PP_Tower"]
SHADOW_SAT_ALREADY_FALSE = ["PP_Crypt", "PostProcess_Exposure"]
AREA_VOLUMES = {"PP_Outdoor_Night": 1.40,  # P14-5c: 1.15 -> 1.40
                  "PP_Cloister": 0.65, "PP_Chapel": CHAPEL_EV, "PP_Tower": 0.65, "PP_Crypt": 0.2}
ALL_VOLUMES = ["PostProcess_Exposure", "PP_Outdoor_Night", "PP_Cloister", "PP_Chapel", "PP_Tower", "PP_Crypt"]
DECAL_LABELS = ["RV_WellHouse_Tally", "RV_Chapel_Circle"]   # the new locations are the DECALS rows of p14_3_level.py
CENSUS = 3015

results = L.results
rec = L.rec
info = L.info


def lc(name):
    return name[0].lower() + name[1:]


def vec4(v):
    return {"x": v[0], "y": v[1], "z": v[2], "w": v[3]}


def get4(d):
    return [float(d[c]) for c in "xyzw"] if "x" in d else [float(d[c]) for c in "rgba"]


def feq(a, b):
    return abs(float(a) - float(b)) < TOL


# ---------------------------------------------------------------------------------------------- A1
def da_all(ed):
    names = list(J(ed.call(L.O, "list_properties", {"instance": {"refPath": DA}})).keys())
    return J(ed.call(L.O, "get_properties", {"instance": {"refPath": DA}, "properties": names}))


def apply_da(ed):
    before = da_all(ed)
    info("DA_StormSettings in memory before: " + json.dumps({k: before[k] for k in list(DA_SET) + list(DA_ASSERT)}))
    for k, want in list(DA_SET.items()) + list(DA_ASSERT.items()):
        if not feq(before[k], want):
            info("  %s differs in memory (%r), set to %r" % (k, before[k], want))
    # write every target explicitly, even when the memory value already equals it
    ed.setp(DA, dict(DA_SET))
    odd = {k: v for k, v in DA_ASSERT.items() if not feq(before[k], v)}
    if odd:
        ed.setp(DA, odd)
    after = da_all(ed)
    other = [k for k in before if k not in DA_SET and k not in odd and json.dumps(before[k], sort_keys=True) != json.dumps(after[k], sort_keys=True)]
    info("DA_StormSettings after: " + json.dumps({k: after[k] for k in list(DA_SET) + list(DA_ASSERT)}))
    info("fields changed other than the targets: %s" % other)


def check_da(ed):
    a = da_all(ed)
    for k, want in DA_SET.items():
        rec(feq(a[k], want), "DA_StormSettings.%s = %r (want %r)" % (k, a[k], want))
    for k, want in DA_ASSERT.items():
        rec(feq(a[k], want), "DA_StormSettings.%s = %r (want %r)" % (k, a[k], want))
    rec(len(a["storyIntensity"]) == 8 and len(a["scriptedStrikes"]) == 6, "DA_StormSettings arrays intact (storyIntensity %d, scriptedStrikes %d)" % (
        len(a["storyIntensity"]), len(a["scriptedStrikes"])))


# ---------------------------------------------------------------------------------------------- A2
def mi_obj(n):
    return MI_DIR + n + "." + n


def mi_static(ed, n, sw):
    try:
        return ed.call(MI_TS, "get_static_switch_parameter", {"instance": {"refPath": mi_obj(n)}, "name": sw})
    except RuntimeError as e:
        return "ERR " + str(e)[:80]


def mi_snap(ed, n):
    r = ed.props(mi_obj(n), ["parent", "scalarParameterValues", "vectorParameterValues", "textureParameterValues"])
    return {
        "parent": (r.get("parent") or {}).get("refPath"),
        "scalars": {e["parameterInfo"]["name"]: e["parameterValue"] for e in r.get("scalarParameterValues", [])},
        "vectors": {e["parameterInfo"]["name"]: [round(e["parameterValue"][k], 6) for k in "rgba"] for e in r.get("vectorParameterValues", [])},
        "textures": {e["parameterInfo"]["name"]: (e["parameterValue"] or {}).get("refPath") if isinstance(e["parameterValue"], dict) else e["parameterValue"]
                     for e in r.get("textureParameterValues", [])},
        "statics": {"bUseARM": mi_static(ed, n, "bUseARM"), "bWind": mi_static(ed, n, "bWind")},
    }


def apply_mis(ed):
    for n, (amp, refh) in MIS.items():
        b = mi_snap(ed, n)
        info("MI %s in memory before: WindAmplitudeCm %s WindRefHeightCm %s" % (n, b["scalars"].get("WindAmplitudeCm"), b["scalars"].get("WindRefHeightCm")))
        ed.call(MI_TS, "set_scalar_parameter", {"instance": {"refPath": mi_obj(n)}, "name": "WindAmplitudeCm", "value": amp})
        a = mi_snap(ed, n)
        for k in ("parent", "textures", "vectors", "statics"):
            if a[k] != b[k]:
                raise RuntimeError("%s: %s changed %r -> %r" % (n, k, b[k], a[k]))
        ds = {k: (b["scalars"].get(k), a["scalars"].get(k)) for k in set(a["scalars"]) | set(b["scalars"]) if a["scalars"].get(k) != b["scalars"].get(k)}
        if not set(ds) <= {"WindAmplitudeCm"}:
            raise RuntimeError("%s: unexpected scalar change %r" % (n, ds))
        info("MI %s after: WindAmplitudeCm %s; scalar diff vs memory-before %s; scalars %s; parent/textures/vectors/bUseARM/bWind unchanged %s" % (
            n, a["scalars"].get("WindAmplitudeCm"), ds, json.dumps(a["scalars"], sort_keys=True), json.dumps(a["statics"])))


def check_mis(ed):
    for n, (amp, refh) in MIS.items():
        s = mi_snap(ed, n)
        sc = s["scalars"]
        rec(sc.get("WindAmplitudeCm") is not None and feq(sc["WindAmplitudeCm"], amp), "%s WindAmplitudeCm = %s (want %s)" % (n, sc.get("WindAmplitudeCm"), amp))
        if refh is not None:
            rec(sc.get("WindRefHeightCm") is not None and feq(sc["WindRefHeightCm"], refh), "%s WindRefHeightCm = %s (want %s)" % (n, sc.get("WindRefHeightCm"), refh))
        else:
            rec("WindRefHeightCm" not in sc, "%s WindRefHeightCm has no override (%s)" % (n, sc.get("WindRefHeightCm")))
        bw = s["statics"]["bWind"]
        rec(bw is True or isinstance(bw, dict), "%s bWind true (%s)" % (n, bw))


# ---------------------------------------------------------------------------------------------- A3
def volume(ed, label):
    return ed.find_one(label, must=True)


def settings(ed, ref):
    return ed.props(ref, ["settings"])["settings"]


def apply_map(ed):
    n0 = len(ed.find_all())
    info("census before: %d (expect %d)" % (n0, CENSUS))
    # 1. PP_Chapel EV
    ref = volume(ed, "PP_Chapel")
    ed.setp(ref, {"settings": {"bOverride_AutoExposureMinBrightness": True, "bOverride_AutoExposureMaxBrightness": True,
                               "autoExposureMinBrightness": CHAPEL_EV, "autoExposureMaxBrightness": CHAPEL_EV}})
    # 2. grade B on PostProcess_Exposure
    ref = volume(ed, "PostProcess_Exposure")
    st = {}
    for k, v in GRADE_B.items():
        st["bOverride_" + k] = True
        st[lc(k)] = vec4(v) if isinstance(v, tuple) else v
    ed.setp(ref, {"settings": st})
    # 3. clear the shadow-saturation override on the four area volumes
    for lab in SHADOW_SAT_OFF:
        ed.setp(volume(ed, lab), {"settings": {"bOverride_ColorSaturationShadows": False}})
    # 4, 5. the two reveal decals (location only; rotation and DecalSize unchanged, taken from the DECALS rows)
    for label, loc, rot, size, mi in L.DECALS:
        if label not in DECAL_LABELS:
            continue
        ref = ed.find_one(label, must=True)
        l0, r0, s0 = ed.xform(ref)
        ed.set_xform(ref, loc, rot, (1, 1, 1))
        info("%s moved %s -> %s" % (label, [round(x, 3) for x in l0], list(loc)))


def check_map(ed, census=True):
    # PP_Chapel
    s = settings(ed, volume(ed, "PP_Chapel"))
    rec(s["bOverride_AutoExposureMinBrightness"] and s["bOverride_AutoExposureMaxBrightness"] and feq(s["autoExposureMinBrightness"], CHAPEL_EV)
        and feq(s["autoExposureMaxBrightness"], CHAPEL_EV), "PP_Chapel EV min/max = %s / %s, overrides %s / %s (want %s)" % (
            s["autoExposureMinBrightness"], s["autoExposureMaxBrightness"], s["bOverride_AutoExposureMinBrightness"], s["bOverride_AutoExposureMaxBrightness"], CHAPEL_EV))
    # grade B
    s = settings(ed, volume(ed, "PostProcess_Exposure"))
    for k, v in GRADE_B.items():
        got = s[lc(k)]
        ok = s["bOverride_" + k] is True and (near(get4(got), v, TOL) if isinstance(v, tuple) else feq(got, v))
        rec(ok, "PostProcess_Exposure %s override %s value %s (want %s)" % (k, s["bOverride_" + k], got if not isinstance(got, dict) else get4(got), v))
    rec(s["bOverride_AutoExposureMinBrightness"] and s["bOverride_AutoExposureMaxBrightness"] and feq(s["autoExposureMinBrightness"], 3.0)
        and feq(s["autoExposureMaxBrightness"], 3.0), "PostProcess_Exposure EV stays 3 (%s / %s)" % (s["autoExposureMinBrightness"], s["autoExposureMaxBrightness"]))
    # shadow saturation override
    for lab in SHADOW_SAT_OFF + SHADOW_SAT_ALREADY_FALSE:
        s = settings(ed, volume(ed, lab))
        rec(s["bOverride_ColorSaturationShadows"] is False, "%s bOverride_ColorSaturationShadows = %s (want False)" % (lab, s["bOverride_ColorSaturationShadows"]))
    # every volume's EV, priority, blend, override set
    for lab in ALL_VOLUMES:
        ref = volume(ed, lab)
        p = ed.props(ref, ["priority", "blendRadius", "bUnbound", "bEnabled"])
        s = settings(ed, ref)
        on = sorted(k[len("bOverride_"):] for k, v in s.items() if k.startswith("bOverride_") and v)
        ev = 3.0 if lab == "PostProcess_Exposure" else AREA_VOLUMES[lab]
        rec(feq(s["autoExposureMinBrightness"], ev) and feq(s["autoExposureMaxBrightness"], ev),
            "%s EV %s/%s (want %s) prio %s blend %s unbound %s enabled %s overrides %s" % (
                lab, s["autoExposureMinBrightness"], s["autoExposureMaxBrightness"], ev, p["priority"], p["blendRadius"], p["bUnbound"], p["bEnabled"], on))
    # decals
    for label, loc, rot, size, mi in L.DECALS:
        if label not in DECAL_LABELS:
            continue
        ref = ed.find_one(label)
        if not ref:
            rec(False, "%s exists" % label)
            continue
        l, r, sc = ed.xform(ref)
        p = ed.props(ref + ".NewDecalComponent", ["decalMaterial", "decalSize"])
        mat = (R(p["decalMaterial"]) or "").rsplit(".", 1)[-1]
        sz = v3(p["decalSize"])
        rec(near(l, loc, 0.01) and L.same_rot(r, rot) and near(sc, (1, 1, 1), 1e-6) and near(sz, size, 0.01) and mat == mi,
            "%s loc %s rot %s scale %s DecalSize %s material %s (want loc %s rot %s size %s %s)" % (
                label, [round(x, 3) for x in l], [round(x, 3) for x in r], sc, [round(x, 3) for x in sz], mat, list(loc), list(rot), list(size), mi))
    if census:
        n = len(ed.find_all())
        rec(n == CENSUS, "actor census %d (want %d)" % (n, CENSUS))
    # nothing else dirty
    for pkg in L.NEVER_SAVE:
        rec(not ed.is_dirty(pkg), "%s is not dirty" % pkg.rsplit("/", 1)[-1])


STEPS = ["da", "mis", "map"]
APPLY = {"da": apply_da, "mis": apply_mis, "map": apply_map}


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--apply", action="store_true")
    g.add_argument("--check", action="store_true")
    ap.add_argument("--only", default="", help="comma list of: " + ",".join(STEPS))
    ap.add_argument("--no-census", action="store_true")
    a = ap.parse_args()
    steps = [s for s in STEPS if not a.only or s in a.only.split(",")]
    try:
        ed = L.Ed()
        if ed.call(L.E, "IsPIERunning"):
            sys.exit("PIE is running: stop it first")
        lvl = str(ed.call(L.S, "get_current_level", {}))
        if not lvl.startswith(L.MAP_PKG):
            sys.exit("the editor is on %s, not L_Monastery" % lvl)
        for pkg in L.NEVER_SAVE:
            if ed.is_dirty(pkg):
                sys.exit("STOP: %s is dirty" % pkg)
        if a.apply:
            for s in steps:
                print("=== apply %s" % s, flush=True)
                APPLY[s](ed)
            print("=== verifying", flush=True)
        checks = {"da": check_da, "mis": check_mis, "map": lambda e: check_map(e, census=not a.no_census)}
        for s in steps:
            print("=== check %s" % s, flush=True)
            checks[s](ed)
        info("dirty: DA %s, map %s" % (ed.is_dirty(DA_PKG), ed.is_dirty(L.MAP_PKG)))
        info("%d editor calls" % ed.calls)
    except EditorStop as e:
        print("STOP: editor problem (%s). Do NOT save and do NOT retry a mutation." % e)
        sys.exit(3)
    fails = [m for ok, m in results if not ok]
    print("\nRESULT: %d PASS, %d FAIL" % (len(results) - len(fails), len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
