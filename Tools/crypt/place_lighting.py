"""P9-7 crypt lighting placement (Unreal MCP): fires, shaft cards, LFV_Crypt_Flood, PP_Crypt, greybox light removal.

Usage (editor open on L_Monastery, PIE STOPPED; spawning while PIE runs would put the actors in the PIE world):
    python place_lighting.py greybox            # delete Light_Crypt_0..13 (dump them first: Docs/ArtTest/crypt/greybox_lights_before.json)
    python place_lighting.py fires [--brazier-scale 0.5]
    python place_lighting.py shafts [--flip] [--width-override G1=70,...]
    python place_lighting.py lfv
    python place_lighting.py pp [--ev 1.0]
    python place_lighting.py check

Every action is idempotent (removes its own labels first), reads values back and prints them.
Lights themselves are placed by place_crypt.py --cats light.
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mcp"))
from ue import UE  # noqa: E402

S = "editor_toolset.toolsets.scene.SceneTools"
A = "editor_toolset.toolsets.actor.ActorTools"
O = "editor_toolset.toolsets.object.ObjectTools"
E = "EditorToolset.EditorAppToolset"
FOLDER = "Lighting/Crypt"
FIRE00 = "/Game/LastBell/ThirdParty/Fab/Dungeon/Fire/Particle_Systems/PS_Fire_00.PS_Fire_00"
FIRE01 = "/Game/LastBell/ThirdParty/Fab/Dungeon/Fire/Particle_Systems/PS_Fire_01.PS_Fire_01"
SHAFT_MI = "/Game/LastBell/Environments/Crypt/Materials/MI_LightShaft_Crypt.MI_LightShaft_Crypt"
CYL = "/Engine/BasicShapes/Cylinder.Cylinder"
UE_ = UE()


def call(ts, tool, args=None):
    return UE_.call(ts, tool, args)


def props(inst, names):
    r = call(O, "get_properties", {"instance": inst if isinstance(inst, dict) else {"refPath": inst}, "properties": names})
    return json.loads(r) if isinstance(r, str) else r


def setp(inst, vals):
    return call(O, "set_properties", {"instance": inst if isinstance(inst, dict) else {"refPath": inst}, "values": json.dumps(vals)})


def find_label(label, exact=True):
    out = []
    for a in call(S, "find_actors", {"name": label, "tag": "", "collision_channels": []}) or []:
        lbl = call(A, "get_label", {"actor": a})
        if (lbl == label) if exact else lbl.startswith(label):
            out.append(a)
    return out


def remove_label(label, exact=True):
    n = 0
    for a in find_label(label, exact):
        call(S, "remove_from_scene", {"actor": a})
        n += 1
    return n


def xf(loc, rot=(0, 0, 0), sc=(1, 1, 1)):
    return {"location": dict(zip("xyz", loc)), "rotation": {"pitch": rot[0], "yaw": rot[1], "roll": rot[2]}, "scale": dict(zip("xyz", sc))}


def tf(actor):
    t = call(A, "get_actor_transform", {"actor": actor, "worldspace": True})
    return [t["location"][k] for k in "xyz"], [t["rotation"][k] for k in ("pitch", "yaw", "roll")], [t["scale"][k] for k in "xyz"]


def bounds(actor):
    b = call(A, "get_actor_bounds", {"actor": actor})
    return [b["min"][k] for k in "xyz"], [b["max"][k] for k in "xyz"]


def finish(a, label, folder=FOLDER):
    call(A, "set_label", {"actor": a, "label": label})
    call(S, "set_actor_folder", {"actor": a, "folder_path": folder})


# ------------------------------------------------------------------ greybox
def greybox():
    n = 0
    for i in range(14):
        n += remove_label("Light_Crypt_%d" % i)
    left = find_label("Light_Crypt_", exact=False)
    print("removed %d greybox lights; Light_Crypt_* remaining: %d" % (n, len(left)))
    return not left


# ------------------------------------------------------------------ fires
def courtyard_offsets():
    kx = find_label("KX_Torch")[0]
    fx = find_label("FX_Torch_Fire")[0]
    (kl, kr, _), (fl, _, fs) = tf(kx), tf(fx)
    w = [fl[i] - kl[i] for i in range(3)]
    yaw = math.radians(kr[1])
    # local = R(-yaw) * world offset
    lx = w[0] * math.cos(yaw) + w[1] * math.sin(yaw)
    ly = -w[0] * math.sin(yaw) + w[1] * math.cos(yaw)
    return (lx, ly, w[2]), fs, kx, fx


def fires(brazier_scale):
    off, scale, kx, fx = courtyard_offsets()
    kb = bounds(kx)
    fl = tf(fx)[0]
    print("courtyard torch: bounds top z %.2f, +X end %.2f; fire at z %.2f x %.2f (%.2f below top, %.2f inside the +X end); fire scale %s; local offset (%.2f, %.2f, %.2f)"
          % (kb[1][2], kb[1][0], fl[2], fl[0], kb[1][2] - fl[2], kb[1][0] - fl[0], scale, off[0], off[1], off[2]))
    ok = True
    for i in (1, 2, 3):
        remove_label("FX_Crypt_Torch_T%d" % i)
        t = find_label("CD_Torch_T%d" % i)[0]
        tl, tr, _ = tf(t)
        yaw = math.radians(tr[1])
        loc = [tl[0] + off[0] * math.cos(yaw) - off[1] * math.sin(yaw), tl[1] + off[0] * math.sin(yaw) + off[1] * math.cos(yaw), tl[2] + off[2]]
        a = call(S, "add_to_scene_from_asset", {"asset_path": FIRE00, "name": "FX_Crypt_Torch_T%d" % i, "xform": xf(loc, (0, 0, 0), scale)})
        call(A, "set_actor_transform", {"actor": a, "xform": xf(loc, (0, 0, 0), scale), "worldspace": True})
        finish(a, "FX_Crypt_Torch_T%d" % i)
        got = tf(a)
        tb = bounds(t)
        print("  FX_Crypt_Torch_T%d at %s scale %s (torch bounds %s..%s)" % (i, [round(v, 1) for v in got[0]], [round(v, 2) for v in got[2]],
                                                                     [round(v, 1) for v in tb[0]], [round(v, 1) for v in tb[1]]))
        ok &= max(abs(got[0][k] - loc[k]) for k in range(3)) < 0.1 and abs(got[2][0] - scale[0]) < 1e-3
    remove_label("FX_Crypt_Brazier")
    ch = find_label("CD_Charcoal")[0]
    cb = bounds(ch)
    loc = [(cb[0][0] + cb[1][0]) / 2, (cb[0][1] + cb[1][1]) / 2, cb[1][2]]
    sc = (brazier_scale,) * 3
    a = call(S, "add_to_scene_from_asset", {"asset_path": FIRE01, "name": "FX_Crypt_Brazier", "xform": xf(loc, (0, 0, 0), sc)})
    call(A, "set_actor_transform", {"actor": a, "xform": xf(loc, (0, 0, 0), sc), "worldspace": True})
    finish(a, "FX_Crypt_Brazier")
    got = tf(a)
    print("  FX_Crypt_Brazier at %s scale %s (pot bounds %s..%s)" % ([round(v, 1) for v in got[0]], got[2], [round(v, 1) for v in cb[0]], [round(v, 1) for v in cb[1]]))
    for lbl in ["FX_Crypt_Torch_T1", "FX_Crypt_Torch_T2", "FX_Crypt_Torch_T3", "FX_Crypt_Brazier"]:
        a = find_label(lbl)[0]
        comps = call(A, "get_components", {"actor": a})
        pc = [c for c in comps if c["refPath"].endswith("ParticleSystemComponent0")]
        if pc:
            p = props(pc[0], ["template", "bAutoActivate"])
            print("  ", lbl, p)
    return ok


# ------------------------------------------------------------------ shaft cards
def unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return [c / n for c in v]


def aim_dir(rot):
    p, y = math.radians(rot[0]), math.radians(rot[1])
    return [math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p)]


def cyl_rot(d, flip=False):
    """rotator (pitch, yaw, roll) whose local +Z axis points along d (roll 180 flips it)."""
    h = math.hypot(d[0], d[1])
    pitch = math.degrees(math.atan2(-h, d[2]))
    yaw = math.degrees(math.atan2(d[1], d[0])) if h > 1e-9 else 0.0
    return [pitch, yaw, 180.0 if flip else 0.0]


def shafts(flip, widths, start_off=15.0):
    ok = True
    for n, w in (("G1", 70.0), ("G2", 70.0), ("G3", 200.0)):
        w = widths.get(n, w)
        lbl = "SA_Crypt_" + n
        remove_label(lbl)
        sp = find_label("L_Crypt_Moon_" + n)[0]
        loc, rot, _ = tf(sp)
        d = unit(aim_dir(rot))
        st = [loc[i] + d[i] * start_off for i in range(3)]
        far = [loc[i] + d[i] * 1200 for i in range(3)]
        dist = call(S, "trace_world", {"start": dict(zip("xyz", st)), "end": dict(zip("xyz", far))})
        if dist is None:
            print("  %s: trace found no hit within 1200 cm; using 600" % n)
            length = 600.0
        else:
            length = start_off + float(dist)
        ctr = [loc[i] + d[i] * length * 0.5 for i in range(3)]
        rr = cyl_rot(d, flip)
        sc = (w / 100.0, w / 100.0, length / 100.0)
        a = call(S, "add_to_scene_from_asset", {"asset_path": CYL, "name": lbl, "xform": xf(ctr, rr, sc)})
        call(A, "set_actor_transform", {"actor": a, "xform": xf(ctr, rr, sc), "worldspace": True})
        finish(a, lbl)
        comp = {"refPath": a["refPath"] + ".StaticMeshComponent0"}
        comps = call(A, "get_components", {"actor": a})
        comp = comps[0]
        setp(comp, {"castShadow": False, "bUseDefaultCollision": False,
                    "bodyInstance": {"collisionProfileName": "NoCollision", "collisionEnabled": "NoCollision"},
                    "overrideMaterials": [{"refPath": SHAFT_MI}]})
        st_ = props(comp, ["castShadow", "bodyInstance", "overrideMaterials", "bUseDefaultCollision"])
        mb = bounds(a)
        got = tf(a)
        good = (not st_["castShadow"] and st_["bodyInstance"]["collisionProfileName"] == "NoCollision" and st_["bodyInstance"]["collisionEnabled"] == "NoCollision"
                and st_["overrideMaterials"] and st_["overrideMaterials"][0]["refPath"].endswith("MI_LightShaft_Crypt"))
        ok &= bool(good)
        print("  %s: spot at %s dir %s, length %.1f (hit dist %s), width %.0f, centre %s rot %s scale %s -> read-back loc %s rot %s sc %s; bounds %s..%s; castShadow %s, collision %s/%s, mat %s %s"
              % (lbl, [round(v, 1) for v in loc], [round(v, 3) for v in d], length, dist, w, [round(v, 1) for v in ctr], [round(v, 2) for v in rr],
                 [round(v, 3) for v in sc], [round(v, 1) for v in got[0]], [round(v, 2) for v in got[1]], [round(v, 3) for v in got[2]],
                 [round(v, 1) for v in mb[0]], [round(v, 1) for v in mb[1]], st_["castShadow"], st_["bodyInstance"]["collisionProfileName"],
                 st_["bodyInstance"]["collisionEnabled"], [m["refPath"].split(".")[-1] for m in st_["overrideMaterials"]], "OK" if good else "CHECK"))
    return ok


# ------------------------------------------------------------------ LFV
LFV_VALUES = {"radialFogExtinction": 0.3, "heightFogExtinction": 0.6, "heightFogFalloff": 400.0, "heightFogOffset": 0.0,
              "fogEmissive": {"r": 0.0, "g": 0.0, "b": 0.0, "a": 1.0}}


def lfv(extra=None):
    remove_label("LFV_Crypt_Flood")
    loc, sc = (9500.0, -2280.0, -600.0), (0.9, 0.9, 0.9)
    a = call(S, "add_to_scene_from_class", {"actor_type": {"refPath": "/Script/Engine.LocalFogVolume"}, "name": "LFV_Crypt_Flood", "xform": xf(loc, (0, 0, 0), sc)})
    call(A, "set_actor_transform", {"actor": a, "xform": xf(loc, (0, 0, 0), sc), "worldspace": True})
    finish(a, "LFV_Crypt_Flood")
    comp = {"refPath": a["refPath"] + ".LocalFogVolumeComponent"}
    vals = dict(LFV_VALUES)
    vals.update(extra or {})
    setp(comp, vals)
    got = props(comp, list(vals))
    print("  LFV_Crypt_Flood at %s scale %s: %s" % (tf(a)[0], tf(a)[2], got))
    return True


# ------------------------------------------------------------------ PP_Crypt
def pp(ev):
    remove_label("PP_Crypt")
    base = find_label("PostProcess_Exposure")[0]
    prio = props(base, ["priority"])["priority"]
    loc = ((6150 + 11900) / 2.0, (-3300 + 800) / 2.0, (-1150 + -40) / 2.0)
    a = call(S, "add_to_scene_from_class", {"actor_type": {"refPath": "/Script/Engine.PostProcessVolume"}, "name": "PP_Crypt", "xform": xf(loc)})
    call(A, "set_actor_transform", {"actor": a, "xform": xf(loc), "worldspace": True})
    finish(a, "PP_Crypt")
    b0 = bounds(a)
    print("  default brush bounds %s..%s" % (b0[0], b0[1]))
    size = (11900 - 6150, 800 + 3300, -40 + 1150)
    ext = [b0[1][i] - b0[0][i] for i in range(3)]
    sc = tuple(size[i] / ext[i] for i in range(3))
    call(A, "set_actor_transform", {"actor": a, "xform": xf(loc, (0, 0, 0), sc), "worldspace": True})
    setp(a, {"bUnbound": False, "blendRadius": 300.0, "priority": prio + 1.0, "blendWeight": 1.0})
    set_ev(a, ev)
    b = bounds(a)
    g = props(a, ["bUnbound", "blendRadius", "priority", "blendWeight"])
    print("  PP_Crypt scale %s bounds %s..%s %s global priority %s" % ([round(v, 4) for v in sc], [round(v, 1) for v in b[0]], [round(v, 1) for v in b[1]], g, prio))
    return True


def set_ev(actor, ev):
    setp(actor, {"settings": {"bOverride_AutoExposureMethod": True, "autoExposureMethod": "AEM_Histogram",
                              "bOverride_AutoExposureMinBrightness": True, "bOverride_AutoExposureMaxBrightness": True,
                              "autoExposureMinBrightness": ev, "autoExposureMaxBrightness": ev}})
    s = props(actor, ["settings"])["settings"]
    print("  exposure: method %s min %s max %s (overrides %s %s %s)" % (s["autoExposureMethod"], s["autoExposureMinBrightness"], s["autoExposureMaxBrightness"],
          s["bOverride_AutoExposureMethod"], s["bOverride_AutoExposureMinBrightness"], s["bOverride_AutoExposureMaxBrightness"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["greybox", "fires", "shafts", "lfv", "pp"])
    ap.add_argument("--brazier-scale", type=float, default=0.5)
    ap.add_argument("--flip", action="store_true")
    ap.add_argument("--widths", default="")
    ap.add_argument("--ev", type=float, default=1.0)
    ap.add_argument("--lfv", default="", help="json overrides for the LFV values")
    a = ap.parse_args()
    if call(E, "IsPIERunning"):
        sys.exit("PIE is running: stop it first (spawned actors would go to the PIE world)")
    if not str(call(S, "get_current_level")).endswith("L_Monastery"):
        sys.exit("editor is not on L_Monastery")
    widths = {k: float(v) for k, v in (x.split("=") for x in a.widths.split(",") if x)}
    ok = {"greybox": greybox, "fires": lambda: fires(a.brazier_scale), "shafts": lambda: shafts(a.flip, widths),
          "lfv": lambda: lfv(json.loads(a.lfv) if a.lfv else None), "pp": lambda: pp(a.ev)}[a.what]()
    print("RESULT", a.what, "OK" if ok else "CHECK")


if __name__ == "__main__":
    main()
