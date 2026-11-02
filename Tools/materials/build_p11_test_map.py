"""P11-3c: builds the wall joint test map content (Unreal MCP). Section "P11-3c" of Docs/plans/P11_MATERIALS.md is the spec.

Usage (editor open with /Game/LastBell/ArtTest/P11/L_Test_P11_Walls as the current level, PIE STOPPED):
    python build_p11_test_map.py            # place or update everything (idempotent), then run the read-back check
    python build_p11_test_map.py --check    # read-only: labels, transforms, slot overrides by slot NAME, lights, sky, post-process, bounds, traces
The script refuses to run on any other level, so L_Monastery can never be touched. It never saves anything.
P11-4a (Docs/plans/P11_MATERIALS.md, section "P11-4a"): bays B1-B3 were replaced by A1-A3 (flattened block texture; same indices 2-4).
The MI_P11_B1_*, MI_P11_B2_Masonry and MI_P11_B3_* assets stay on disk as the fallback.

Actors, all labelled and found by label (a re-run updates the existing actors instead of adding new ones):
    P11_Floor, P11_Moon, P11_MoonFill, P11_Sky, P11_PP
    P11_<Bay>_<Part>        lantern row (X0 = 1500 * i)
    P11_Far_<Bay>_<Part>    moonlight row (X1 = 10000 + 2500 * i)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mcp"))
from ue import UE  # noqa: E402

S = "editor_toolset.toolsets.scene.SceneTools"
A = "editor_toolset.toolsets.actor.ActorTools"
O = "editor_toolset.toolsets.object.ObjectTools"
SM = "editor_toolset.toolsets.static_mesh.StaticMeshTools"

MAP = "/Game/LastBell/ArtTest/P11/L_Test_P11_Walls"
KIT = "/Game/LastBell/Environments/Kit/"
KITMI = KIT + "Materials/"
P11 = "/Game/LastBell/ArtTest/P11/"
LANTERN = "/Game/LastBell/ArtTest/Props/Wooden_Lantern_01/SM_Wooden_Lantern_01"
BRACKET = "/Game/LastBell/Environments/Cloister/Meshes/SM_LB_Prop_LanternBracket_R40"
FLOOR_MI = KITMI + "MI_Kit_Floor"
HDRI = "/Game/LastBell/ArtTest/Sky/HDRI_MoonlessGolf"
LF = "/Game/LastBell/Materials/Instances/MI_LF_Lantern"
CUBE = "/Engine/BasicShapes/Cube"
RUBBLE = KITMI + "MI_Kit_Rubble"

KIT_SET = {"W400A": KIT + "SM_LB_Kit_Wall_400x60x800_A", "W400B": KIT + "SM_LB_Kit_Wall_400x60x800_B", "W100": KIT + "SM_LB_Kit_Wall_100x60x800",
           "P400": KIT + "SM_LB_Kit_Trim_Plinth_400x80x60", "P100": KIT + "SM_LB_Kit_Trim_Plinth_100x80x60"}
NG_SET = {"W400A": P11 + "Meshes/SM_LB_P11_NoGroove_Wall_400x60x800_A", "W400B": P11 + "Meshes/SM_LB_P11_NoGroove_Wall_400x60x800_B",
          "W100": P11 + "Meshes/SM_LB_P11_NoGroove_Wall_100x60x800",
          "P400": P11 + "Meshes/SM_LB_P11_NoGroove_Plinth_400x80x60", "P100": P11 + "Meshes/SM_LB_P11_NoGroove_Plinth_100x80x60"}
# (bay, index, mesh set, MAT_Masonry, MAT_Trim)
BAYS = [
    ("Today", 0, KIT_SET, KITMI + "MI_Kit_Masonry", KITMI + "MI_Kit_Trim"),
    ("A", 1, NG_SET, KITMI + "MI_Kit_Masonry", P11 + "Materials/MI_P11_B2_Trim"),
    ("A1", 2, NG_SET, P11 + "Materials/MI_P11_A1_Masonry", P11 + "Materials/MI_P11_B2_Trim"),
    ("A2", 3, NG_SET, P11 + "Materials/MI_P11_A2_Masonry", P11 + "Materials/MI_P11_B2_Trim"),
    ("A3", 4, NG_SET, P11 + "Materials/MI_P11_A3_Masonry", P11 + "Materials/MI_P11_B2_Trim"),
]

FLOOR = {"label": "P11_Floor", "mesh": CUBE, "loc": (11250, -1000, -20), "rot": (0, 0, 0), "scale": (255, 40, 0.4), "folder": "P11/Setup",
         "slots_by_index": [FLOOR_MI]}
MOON = {"label": "P11_Moon", "cls": "/Script/Engine.DirectionalLight", "loc": (11250, -1000, 2000), "rot": (-38, 35, 0), "folder": "P11/Setup",
        "vals": {"intensity": 0.9, "lightColor": (0.745098, 0.803922, 0.921569), "castShadows": True, "forwardShadingPriority": 1}}
FILL = {"label": "P11_MoonFill", "cls": "/Script/Engine.DirectionalLight", "loc": (11250, -1000, 2100), "rot": (-28, -145, 0), "folder": "P11/Setup",
        "vals": {"intensity": 0.06, "lightColor": (0.72549, 0.784314, 0.882353), "castShadows": False}}
SKY = {"label": "P11_Sky", "cls": "/Script/Engine.SkyLight", "loc": (11250, -1000, 600), "rot": (0, 0, 0), "folder": "P11/Setup"}
SKY_VALS = {"sourceType": "SLS_SpecifiedCubemap", "intensity": 0.28, "lightColor": (0.882353, 0.862745, 0.843137),
            "lowerHemisphereColor": (0.015, 0.02, 0.035), "bLowerHemisphereIsBlack": False}
PP = {"label": "P11_PP", "cls": "/Script/Engine.PostProcessVolume", "loc": (11250, -1000, 400), "rot": (0, 0, 0), "folder": "P11/Setup"}
LANTERN_LIGHT = {"intensityUnits": "Lumens", "intensity": 200, "attenuationRadius": 600, "lightColor": (1.0, 0.549020, 0.219608), "castShadows": False,
                 "volumetricScatteringIntensity": 1.5, "sourceRadius": 0}   # L_Cl_Bells values (sourceRadius 0 as in the P10 layout)

TOL_LOC = 0.05
TOL_COL = 1.0 / 255 + 1e-4
UE_ = None
RES = []


def call(ts, tool, args=None):
    r = UE_.call(ts, tool, args)
    if isinstance(r, str):
        try:
            return json.loads(r)
        except ValueError:
            return r
    return r


def props(inst, names):
    return call(O, "get_properties", {"instance": inst if isinstance(inst, dict) else {"refPath": inst}, "properties": names})


def setp(inst, vals):
    return call(O, "set_properties", {"instance": inst if isinstance(inst, dict) else {"refPath": inst}, "values": json.dumps(vals)})


def xf(loc, rot=(0, 0, 0), sc=(1, 1, 1)):
    return {"location": dict(zip("xyz", loc)), "rotation": {"pitch": rot[0], "yaw": rot[1], "roll": rot[2]}, "scale": dict(zip("xyz", sc))}


def tf(actor):
    t = call(A, "get_actor_transform", {"actor": actor, "worldspace": True})
    return [t["location"][k] for k in "xyz"], [t["rotation"][k] for k in ("pitch", "yaw", "roll")], [t["scale"][k] for k in "xyz"]


def bounds(actor):
    b = call(A, "get_actor_bounds", {"actor": actor})
    return [b["min"][k] for k in "xyz"], [b["max"][k] for k in "xyz"]


def ref(p):
    return {"refPath": p if "." in p.split("/")[-1] else p + "." + p.split("/")[-1]}


def short(r):
    p = r.get("refPath", "") if isinstance(r, dict) else (r or "")
    return p.split("/")[-1].split(".")[-1] if p and str(p).lower() != "none" else None


def full(r):
    p = r.get("refPath", "") if isinstance(r, dict) else (r or "")
    return p.split(".")[0] if p and str(p).lower() != "none" else None


def rgb(c):
    if isinstance(c, dict):
        return [c["r"], c["g"], c["b"]]
    return list(c)[:3]


def col_close(a, b):
    return all(abs(x - y) <= TOL_COL for x, y in zip(rgb(a), rgb(b)))


def close(a, b, tol=1e-4):
    return abs(a - b) <= tol


def ang_diff(a, b):
    return (a - b + 180.0) % 360.0 - 180.0


def rec(ok, text):
    RES.append((bool(ok), text))
    print(("PASS  " if ok else "FAIL  ") + text, flush=True)


# ---------------------------------------------------------------- spec -> records
def slot_names(mesh):
    return call(SM, "get_material_slots", {"mesh": ref(mesh)})


def mesh_rec(label, mesh, loc, rot=(0, 0, 0), folder="", slots=None):
    return {"label": label, "mesh": mesh, "loc": loc, "rot": rot, "scale": (1, 1, 1), "folder": folder, "slots": slots}


def records():
    out = []
    for bay, i, ms, mas, trim in BAYS:
        slots = {"MAT_Masonry": mas, "MAT_Trim": trim, "MAT_Rubble": RUBBLE}
        X0 = 1500 * i
        X1 = 10000 + 2500 * i
        f = "P11/" + bay
        P = "P11_%s_" % bay
        out += [mesh_rec(P + "Wall400A", ms["W400A"], (X0, 0, 0), folder=f, slots=slots),
                mesh_rec(P + "Wall100", ms["W100"], (X0 + 400, 0, 0), folder=f, slots=slots),
                mesh_rec(P + "Wall400B", ms["W400B"], (X0 + 500, 0, 0), folder=f, slots=slots),
                mesh_rec(P + "Plinth400A", ms["P400"], (X0, -10, 0), folder=f, slots=slots),
                mesh_rec(P + "Plinth100", ms["P100"], (X0 + 400, -10, 0), folder=f, slots=slots),
                mesh_rec(P + "Plinth400B", ms["P400"], (X0 + 500, -10, 0), folder=f, slots=slots),
                mesh_rec(P + "Bracket", BRACKET, (X0 + 450, 0, 330), (0, -90, 0), folder=f),
                mesh_rec(P + "Lantern", LANTERN, (X0 + 450, -40, 278.1), folder=f)]
        out.append({"label": P + "Light", "cls": "/Script/Engine.PointLight", "loc": (X0 + 450, -40, 320), "rot": (0, 0, 0), "folder": f, "vals": LANTERN_LIGHT,
                    "lf": LF})
        ff = "P11/Far/" + bay
        PF = "P11_Far_%s_" % bay
        for k in range(5):
            w = ms["W400A"] if k % 2 == 0 else ms["W400B"]
            out.append(mesh_rec(PF + "Wall%d%s" % (k, "A" if k % 2 == 0 else "B"), w, (X1 + 400 * k, 0, 0), folder=ff, slots=slots))
            out.append(mesh_rec(PF + "Plinth%d" % k, ms["P400"], (X1 + 400 * k, -10, 0), folder=ff, slots=slots))
    return out


def expected_overrides(r):
    """per-slot-index override list for a mesh record, built from the mesh's own slot order (None keeps the default)"""
    if r.get("slots_by_index") is not None:
        return list(r["slots_by_index"]), None
    if not r.get("slots"):
        return None, None
    names = slot_names(r["mesh"])
    return [r["slots"].get(n) for n in names], names


# ---------------------------------------------------------------- actor lookup
def label_map():
    m = {}
    for a in call(S, "find_actors", {"name": "P11_", "tag": "", "collision_channels": []}) or []:
        m.setdefault(call(A, "get_label", {"actor": a}), []).append(a)
    return m


def get_unique(lm, label):
    found = lm.get(label, [])
    for extra in found[1:]:      # duplicates from an interrupted run
        call(S, "remove_from_scene", {"actor": extra})
    return found[0] if found else None


def comp_of(actor, name):
    return {"refPath": actor["refPath"] + "." + name}


def mesh_comp_state(actor):
    c = comp_of(actor, "StaticMeshComponent0")
    return props(c, ["staticMesh", "overrideMaterials"])


# ---------------------------------------------------------------- place
def place_mesh(r, lm):
    a = get_unique(lm, r["label"])
    if a:
        try:
            if full(mesh_comp_state(a)["staticMesh"]) != r["mesh"]:
                call(S, "remove_from_scene", {"actor": a})
                a = None
        except Exception:
            call(S, "remove_from_scene", {"actor": a})
            a = None
    t = xf(r["loc"], r["rot"], r["scale"])
    if not a:
        a = call(S, "add_to_scene_from_asset", {"asset_path": r["mesh"], "name": r["label"], "xform": t})
        if not a:
            raise RuntimeError("spawn failed for " + r["label"])
    call(A, "set_actor_transform", {"actor": a, "xform": t, "worldspace": True})    # location AND rotation AND scale
    call(A, "set_label", {"actor": a, "label": r["label"]})
    call(S, "set_actor_folder", {"actor": a, "folder_path": r["folder"]})
    ov, _ = expected_overrides(r)
    if ov is not None:
        setp(comp_of(a, "StaticMeshComponent0"), {"overrideMaterials": [ref(m) if m else None for m in ov]})
    return a


def set_light_vals(comp, vals):
    v = {"mobility": "Movable"}
    for k, x in vals.items():
        if k in ("lightColor", "lowerHemisphereColor"):
            v[k] = {"r": x[0], "g": x[1], "b": x[2], "a": 1.0}
        else:
            v[k] = x
    setp(comp, v)


def place_class(r, lm, comp_name="LightComponent0"):
    a = get_unique(lm, r["label"])
    t = xf(r["loc"], r["rot"])
    if not a:
        a = call(S, "add_to_scene_from_class", {"actor_type": {"refPath": r["cls"]}, "name": r["label"], "xform": t})
        if not a:
            raise RuntimeError("spawn failed for " + r["label"])
    call(A, "set_actor_transform", {"actor": a, "xform": t, "worldspace": True})
    call(A, "set_label", {"actor": a, "label": r["label"]})
    call(S, "set_actor_folder", {"actor": a, "folder_path": r["folder"]})
    return a


def build():
    lm = label_map()
    n = 0
    # floor
    a = place_mesh(dict(FLOOR, rot=FLOOR["rot"]), lm)
    n += 1
    # lights
    for r in (MOON, FILL):
        a = place_class(r, lm)
        set_light_vals(comp_of(a, "LightComponent0"), r["vals"])
        n += 1
    a = place_class(SKY, lm)
    c = comp_of(a, "SkyLightComponent0")
    setp(c, {"mobility": "Movable"})
    setp(c, {"sourceType": SKY_VALS["sourceType"], "cubemap": ref(HDRI), "intensity": SKY_VALS["intensity"],
             "lightColor": {"r": SKY_VALS["lightColor"][0], "g": SKY_VALS["lightColor"][1], "b": SKY_VALS["lightColor"][2], "a": 1.0},
             "lowerHemisphereColor": {"r": SKY_VALS["lowerHemisphereColor"][0], "g": SKY_VALS["lowerHemisphereColor"][1], "b": SKY_VALS["lowerHemisphereColor"][2], "a": 1.0},
             "bLowerHemisphereIsBlack": SKY_VALS["bLowerHemisphereIsBlack"]})
    n += 1
    a = place_class(PP, lm)
    setp(a, {"bUnbound": True})
    setp(a, {"settings": {"bOverride_AutoExposureMinBrightness": True, "bOverride_AutoExposureMaxBrightness": True,
                          "autoExposureMinBrightness": 0.65, "autoExposureMaxBrightness": 0.65,
                          "bOverride_ColorSaturationShadows": True, "colorSaturationShadows": {"x": 0.65, "y": 0.65, "z": 0.65, "w": 1.0}}})
    n += 1
    # bays
    for r in records():
        if "mesh" in r:
            place_mesh(r, lm)
        else:
            a = place_class(r, lm)
            set_light_vals(comp_of(a, "LightComponent0"), r["vals"])
            setp(comp_of(a, "LightComponent0"), {"lightFunctionMaterial": ref(r["lf"])})
        n += 1
        if n % 20 == 0:
            print("  placed %d" % n, flush=True)
    print("placed/updated %d actors" % n)


# ---------------------------------------------------------------- check
def check_transform(a, loc, rot, sc):
    gl, gr, gs = tf(a)
    dl = max(abs(g - e) for g, e in zip(gl, loc))
    dr = max(abs(ang_diff(g, e)) for g, e in zip(gr, rot))
    ds = max(abs(g - e) for g, e in zip(gs, sc))
    return dl <= TOL_LOC and dr <= 0.05 and ds <= 1e-3, "loc dev %.3f rot dev %.3f scale dev %.4f" % (dl, dr, ds)


def check_mesh(r, lm):
    a = lm.get(r["label"], [])
    if len(a) != 1:
        rec(False, "%s: %d actors with this label" % (r["label"], len(a)))
        return None
    a = a[0]
    ok, msg = check_transform(a, r["loc"], r["rot"], r["scale"])
    st = mesh_comp_state(a)
    issues = []
    if full(st["staticMesh"]) != r["mesh"]:
        issues.append("mesh %s != %s" % (full(st["staticMesh"]), r["mesh"]))
    shown = ""
    ov, names = expected_overrides(r)
    if ov is not None:
        got = [full(m) for m in (st["overrideMaterials"] or [])]
        got += [None] * (len(ov) - len(got))
        default_names = names or ["slot%d" % i for i in range(len(ov))]
        if len(got) != len(ov):
            issues.append("override count %d != %d slots" % (len(got), len(ov)))
        parts = []
        for i, nm in enumerate(default_names):
            if got[i] != ov[i]:
                issues.append("%s: %s != %s" % (nm, got[i], ov[i]))
            parts.append("%s=%s" % (nm, (got[i] or "default").split("/")[-1]))
        shown = " [" + ", ".join(parts) + "]"
    rec(ok and not issues, "%s %s%s%s" % (r["label"], msg, shown, "" if not issues else " :: " + "; ".join(issues)))
    return a


def check_light(r, lm, comp_name="LightComponent0"):
    a = lm.get(r["label"], [])
    if len(a) != 1:
        rec(False, "%s: %d actors with this label" % (r["label"], len(a)))
        return
    a = a[0]
    ok, msg = check_transform(a, r["loc"], r["rot"], (1, 1, 1))
    names = list(r["vals"]) + ["mobility"] + (["lightFunctionMaterial"] if r.get("lf") else [])
    g = props(comp_of(a, comp_name), names)
    issues = []
    for k, e in r["vals"].items():
        x = g[k]
        if k == "lightColor":
            if not col_close(x, e):
                issues.append("lightColor %s != %s" % (rgb(x), e))
        elif isinstance(e, (bool, str)):
            if x != e:
                issues.append("%s %s != %s" % (k, x, e))
        elif not close(x, e, 1e-4):
            issues.append("%s %s != %s" % (k, x, e))
    if r.get("lf") and full(g["lightFunctionMaterial"]) != r["lf"]:
        issues.append("lightFunctionMaterial %s" % g["lightFunctionMaterial"])
    shown = {k: (rgb(v) if isinstance(v, dict) and "r" in v else (short(v) if isinstance(v, dict) else v)) for k, v in g.items()}
    rec(ok and not issues, "%s %s %s%s" % (r["label"], msg, json.dumps(shown, default=str), "" if not issues else " :: " + "; ".join(issues)))


def check_sky(lm):
    a = lm.get(SKY["label"], [])
    if len(a) != 1:
        rec(False, "P11_Sky: %d actors" % len(a))
        return
    a = a[0]
    ok, msg = check_transform(a, SKY["loc"], SKY["rot"], (1, 1, 1))
    g = props(comp_of(a, "SkyLightComponent0"), ["sourceType", "cubemap", "intensity", "lightColor", "lowerHemisphereColor", "bLowerHemisphereIsBlack", "mobility"])
    issues = []
    if g["sourceType"] != "SLS_SpecifiedCubemap":
        issues.append("sourceType %s" % g["sourceType"])
    if full(g["cubemap"]) != HDRI:
        issues.append("cubemap %s" % g["cubemap"])
    if not close(g["intensity"], 0.28):
        issues.append("intensity %s" % g["intensity"])
    if not col_close(g["lightColor"], SKY_VALS["lightColor"]):
        issues.append("lightColor %s" % rgb(g["lightColor"]))
    if max(abs(x - y) for x, y in zip(rgb(g["lowerHemisphereColor"]), SKY_VALS["lowerHemisphereColor"])) > 1e-4:
        issues.append("lowerHemisphereColor %s" % rgb(g["lowerHemisphereColor"]))
    if g["bLowerHemisphereIsBlack"]:
        issues.append("bLowerHemisphereIsBlack true")
    rec(ok and not issues, "P11_Sky %s %s%s" % (msg, json.dumps({k: (rgb(v) if isinstance(v, dict) and "r" in v else (short(v) if isinstance(v, dict) else v)) for k, v in g.items()}, default=str),
                                                 "" if not issues else " :: " + "; ".join(issues)))


def check_pp(lm):
    a = lm.get(PP["label"], [])
    if len(a) != 1:
        rec(False, "P11_PP: %d actors" % len(a))
        return
    a = a[0]
    g = props(a, ["bUnbound", "settings"])
    st = g["settings"]
    issues = []
    if not g["bUnbound"]:
        issues.append("bUnbound false")
    for k in ("AutoExposureMinBrightness", "AutoExposureMaxBrightness"):
        v = st[k[0].lower() + k[1:]]
        if not st["bOverride_" + k] or not close(v, 0.65):
            issues.append("%s override %s value %s" % (k, st["bOverride_" + k], v))
    cs = st["colorSaturationShadows"]
    cs = [cs[k] for k in ("x", "y", "z", "w")] if "x" in cs else [cs["r"], cs["g"], cs["b"], cs["a"]]
    if not st["bOverride_ColorSaturationShadows"] or max(abs(x - y) for x, y in zip(cs, (0.65, 0.65, 0.65, 1.0))) > 1e-4:
        issues.append("ColorSaturationShadows override %s value %s" % (st["bOverride_ColorSaturationShadows"], cs))
    rec(not issues, "P11_PP bUnbound %s exposure min/max %s/%s (overrides %s/%s) satShadows %s (override %s)%s" % (
        g["bUnbound"], st["autoExposureMinBrightness"], st["autoExposureMaxBrightness"], st["bOverride_AutoExposureMinBrightness"],
        st["bOverride_AutoExposureMaxBrightness"], cs, st["bOverride_ColorSaturationShadows"], "" if not issues else " :: " + "; ".join(issues)))


def check_geometry(lm, recs):
    """wall bounds (mesh-local bounds + location) and the front-face traces"""
    cache = {}
    for r in recs:
        if "mesh" not in r or "Wall" not in r["label"]:
            continue
        a = lm.get(r["label"], [])
        if len(a) != 1:
            continue
        if r["mesh"] not in cache:
            b = call(SM, "get_bounds", {"mesh": ref(r["mesh"])})
            cache[r["mesh"]] = ([b["min"][k] for k in "xyz"], [b["max"][k] for k in "xyz"])
        lo, hi = cache[r["mesh"]]
        want = ([l + o for l, o in zip(r["loc"], lo)], [l + o for l, o in zip(r["loc"], hi)])
        got = bounds(a[0])
        dev = max(abs(g - w) for g, w in zip(got[0] + got[1], want[0] + want[1]))
        rec(dev <= 0.5, "%s bounds %s..%s want %s..%s (dev %.2f)" % (r["label"], [round(v, 2) for v in got[0]], [round(v, 2) for v in got[1]],
                                                                   [round(v, 2) for v in want[0]], [round(v, 2) for v in want[1]], dev))
    for bay, i, *_ in BAYS:
        for lab, X in (("lantern row", 1500 * i), ("moonlight row", 10000 + 2500 * i)):
            x = X + 200
            d = call(S, "trace_world", {"start": {"x": x, "y": -500, "z": 170}, "end": {"x": x, "y": 500, "z": 170}})
            rec(d is not None and abs(float(d) - 500.0) <= 3.0, "trace %s %s: x=%s y -500 -> 500 at z 170 hits at distance %s (want 500 +-3)" % (bay, lab, x, d))


def check():
    lm = label_map()
    recs = records()
    check_mesh(dict(FLOOR), lm)
    check_light(dict(MOON, rot=MOON["rot"]), lm)
    check_light(dict(FILL, rot=FILL["rot"]), lm)
    check_sky(lm)
    check_pp(lm)
    for r in recs:
        if "mesh" in r:
            check_mesh(r, lm)
        else:
            check_light(r, lm)
    # no stray P11_ actors
    want = {FLOOR["label"], MOON["label"], FILL["label"], SKY["label"], PP["label"]} | {r["label"] for r in recs}
    stray = sorted(set(lm) - want)
    dup = sorted(k for k, v in lm.items() if len(v) > 1)
    rec(not stray and not dup, "%d expected P11_ actors; stray labels %s; duplicate labels %s; found %d" % (len(want), stray, dup, len(lm)))
    check_geometry(lm, recs)
    allactors = call(S, "find_actors", {"name": "", "tag": "", "collision_channels": []}) or []
    print("INFO  total actors in level: %d" % len(allactors))
    bad = [x for x in RES if not x[0]]
    print("\n%d/%d checks passed" % (len(RES) - len(bad), len(RES)))
    return not bad


def main():
    global UE_
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="read-only verification")
    args = ap.parse_args()
    UE_ = UE()
    cur = call(S, "get_current_level")
    cur = cur.get("refPath", cur) if isinstance(cur, dict) else cur
    if str(cur).split(".")[0] != MAP:
        print("current level is %s, not %s: refusing to touch it" % (cur, MAP))
        sys.exit(2)
    if not args.check:
        build()
    sys.exit(0 if check() else 1)


if __name__ == "__main__":
    main()
