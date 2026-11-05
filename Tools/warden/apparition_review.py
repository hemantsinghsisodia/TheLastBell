"""P12 fix set 1 look test (section 8 of Docs/plans/P12_FIX1_WARDEN_APPEARANCES.md): stand every apparition candidate and the
Warden's new attack light in the editor world, for captures. Model: Tools/warden/read_review.py.

    python -I Tools/warden/apparition_review.py --poses    # writes Tools/warden/poses/p12f_look_poses.json (no editor needed)
    python -I Tools/warden/apparition_review.py --place    # every temporary actor at once (17), each read back OK / FAILED
    python -I Tools/warden/apparition_review.py --status   # lists the P12F_ actors and the actor count
    python -I Tools/warden/apparition_review.py --remove   # removes every P12F_ actor; the census must return to 2980

NEVER SAVE L_Monastery (or any map) WHILE THESE P12F_ ACTORS EXIST. PIE must be off to place or remove (both refuse if it is on).
Everything here is temporary and labelled P12F_ (read_review.py uses P12_; the two prefixes don't overlap).

Actors (all labelled P12F_*; one --place stands all of them):
  roof_all   3 figures at (6020, Y, 800), Y 1300 / 1800 / 2300, each with a glow plane (BasicShapes/Plane, MI_Warden_ApparitionGlow,
             scale 10, 150 cm behind the figure seen from the camera and 150 cm up, turned to face the camera)
  rail_all   3 figures at (8380, Y, 0), Y -250 / -120 / 0, and a candle proxy at the camera
  sac        1 figure at (8500, -930, 0) for sac_a and sac_b
  light_*    2 SK_Warden figures (ossuary, bells) playing AN_Warden_Idle (read_review.py's method), each with a red point light
             (5000, Unitless, radius 700, colour (1, 0.078, 0.039), no shadows) at the figure + 110 cm forward (towards the camera)
             + 235 cm up, and a candle proxy at the 3 m camera
Figures are StaticMeshActors with SM_LB_Warden_Apparition (faces +X at yaw 0, so actor yaw = the direction it faces), its default
materials, castShadow off, NoCollision. Each faces its view's first camera. The candle proxy copies the player's candle with
read_review.py's formula: 10 cd, 1900 K, radius 600, no shadows, camera + (36 forward, 14 right, -10 up).
Camera yaw/pitch come from camera and look-at point (Unreal: pitch positive looks up); the two light_ cameras are read_review.py's
`ossuary` and `bells` 3m views (SPOTS), so they match.
"""
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "mcp"))
from ue import UE  # noqa: E402

SC = "editor_toolset.toolsets.scene.SceneTools"
AC = "editor_toolset.toolsets.actor.ActorTools"
OB = "editor_toolset.toolsets.object.ObjectTools"
APP = "EditorToolset.EditorAppToolset"

PREFIX = "P12F_"
EXPECTED_ACTORS = 2980
EYE = 165.0
APPARITION = "/Game/LastBell/Characters/Warden/Meshes/SM_LB_Warden_Apparition"
WARDEN = "/Game/LastBell/Characters/Warden/Meshes/SK_Warden"
CLIP = "/Game/LastBell/Characters/Warden/Anims/AN_Warden_Idle"
PLANE = "/Engine/BasicShapes/Plane"
GLOW_MI = "/Game/LastBell/Characters/Warden/Materials/MI_Warden_ApparitionGlow"
GLOW_SCALE = 10.0
GLOW_BEHIND, GLOW_UP = 150.0, 150.0

# red attack light (section 7): at figure + 110 forward + 235 up
RED = {"intensity": 5000.0, "intensityUnits": "Unitless", "attenuationRadius": 700.0, "castShadows": False}
RED_COLOR = (1.0, 0.078, 0.039)
RED_OFFSET = (110.0, 235.0)

# cameras: name -> (x, y, z, look-at x, y, z); light_ cameras are read_review.py's 3m views (figure pos, camera x, y, pitch)
ROOF_CAM, ROOF_AT = (500.0, 0.0, 170.0), (6020.0, 1800.0, 900.0)
RAIL_CAM, RAIL_AT = (8720.0, 0.0, 195.0), (8380.0, -120.0, 150.0)
SAC_A, SAC_B, SAC_AT = (8650.0, -300.0, 165.0), (8350.0, -300.0, 165.0), (8500.0, -930.0, 150.0)
READ_SPOTS = {   # figure XYZ, 3m camera x, y, pitch (read_review.py SPOTS["ossuary"][...]["3m"] and ["bells"]["3m"])
    "ossuary": ((8850.0, -2250.0, -600.0), 8550.0, -2250.0, 8.0),
    "bells": ((11750.0, 2650.0, 0.0), 11750.0, 2350.0, 8.0),
}
ROOF_FIGURES = [(6020.0, y, 800.0) for y in (1300.0, 1800.0, 2300.0)]
RAIL_FIGURES = [(8380.0, y, 0.0) for y in (-250.0, -120.0, 0.0)]
SAC_FIGURE = (8500.0, -930.0, 0.0)


def yaw_to(ax, ay, bx, by):
    return math.degrees(math.atan2(by - ay, bx - ax))


def look(cam, at):
    """[x, y, z, pitch, yaw] of a camera at `cam` looking at `at` (Unreal pitch: positive looks up)."""
    dx, dy, dz = at[0] - cam[0], at[1] - cam[1], at[2] - cam[2]
    return [cam[0], cam[1], cam[2], round(math.degrees(math.atan2(dz, math.hypot(dx, dy))), 2), round(math.degrees(math.atan2(dy, dx)), 2)]


def poses():
    out = {"roof_all": look(ROOF_CAM, ROOF_AT), "rail_all": look(RAIL_CAM, RAIL_AT),
           "sac_a": look(SAC_A, SAC_AT), "sac_b": look(SAC_B, SAC_AT)}
    for spot in ("ossuary", "bells"):                      # as read_review.py: camera z = floor + 165, yaw towards the figure
        (fx, fy, fz), cx, cy, pitch = READ_SPOTS[spot]
        out["light_" + spot] = [cx, cy, fz + EYE, pitch, round(yaw_to(cx, cy, fx, fy), 2)]
    return out


def write_poses():
    out = poses()
    with open(os.path.join(HERE, "poses", "p12f_look_poses.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    for k, v in out.items():
        print("%-14s x %8.1f y %8.1f z %7.1f  pitch %6.2f  yaw %7.2f" % (k, *v))
    print("wrote %d poses" % len(out))
    return 0


# ------------------------------------------------------------------ editor helpers
def labelled(ue):
    found = []
    for a in ue.call(SC, "find_actors", {"name": PREFIX, "tag": "", "collision_channels": []}):
        p = a["refPath"] if isinstance(a, dict) else a
        if str(ue.call(AC, "get_label", {"actor": {"refPath": p}})).startswith(PREFIX):
            found.append(p)
    return found


def count(ue):
    # this large reply sometimes drops the connection straight after a spawn; a second try is enough
    for attempt in range(3):
        try:
            return len(ue.call(SC, "find_actors", {"name": "", "tag": "", "collision_channels": []}))
        except ConnectionResetError:
            if attempt == 2:
                raise
            time.sleep(2)


def xform(x, y, z, yaw, pitch=0.0, scale=1.0):
    return {"location": {"x": x, "y": y, "z": z}, "rotation": {"pitch": pitch, "yaw": yaw, "roll": 0},
            "scale": {"x": scale, "y": scale, "z": scale}}


def pie_off(ue):
    if ue.call(APP, "IsPIERunning", {}) is True:
        print("PIE/Simulate is running: stop it first.")
        return False
    return True


def js(v):
    return json.loads(v) if isinstance(v, str) else v


def spawn(ue, how, what, label, xf):
    r = ue.call(SC, "add_to_scene_from_" + how, {("asset_path" if how == "asset" else "actor_type"): what if how == "asset" else {"refPath": what},
                                                  "name": label, "xform": xf})
    actor = r["refPath"] if isinstance(r, dict) else r
    ue.call(AC, "set_label", {"actor": {"refPath": actor}, "label": label})
    return actor


def placed_at(ue, actor, x, y, z, yaw, pitch=0.0):
    """True when the actor's world transform reads back as asked (location within 1 cm, rotation within 0.1 degree)."""
    t = js(ue.call(AC, "get_actor_transform", {"actor": {"refPath": actor}}))
    t = t.get("transform", t) if isinstance(t, dict) else t
    loc, rot = t["location"], t["rotation"]
    d = lambda a, b: abs((a - b + 180.0) % 360.0 - 180.0)
    return math.dist((loc["x"], loc["y"], loc["z"]), (x, y, z)) < 1.0 and d(rot["yaw"], yaw) < 0.1 and d(rot["pitch"], pitch) < 0.1, t


def static_figure(ue, mesh, label, x, y, z, yaw, pitch=0.0, scale=1.0, material=None):
    """StaticMeshActor with NoCollision and no shadow; optional material override. Returns (ok, message)."""
    xf = xform(x, y, z, yaw, pitch, scale)
    actor = spawn(ue, "asset", mesh, label, xf)
    ue.call(AC, "set_actor_transform", {"actor": {"refPath": actor}, "worldspace": True, "xform": xf})
    comp = ue.call(AC, "get_components", {"actor": {"refPath": actor}})[0]
    vals = {"castShadow": False, "bUseDefaultCollision": False,
            "bodyInstance": {"collisionProfileName": "NoCollision", "collisionEnabled": "NoCollision"}}
    if material:
        vals["overrideMaterials"] = [{"refPath": material + "." + material.rsplit("/", 1)[1]}]
    ue.call(OB, "set_properties", {"instance": comp, "values": json.dumps(vals)})
    p = js(ue.call(OB, "get_properties", {"instance": comp, "properties": ["staticMesh", "castShadow", "bodyInstance", "overrideMaterials"]}))
    at_ok, t = placed_at(ue, actor, x, y, z, yaw, pitch)
    sm = (p["staticMesh"] or {}).get("refPath", "") if isinstance(p["staticMesh"], dict) else str(p["staticMesh"])
    mats = [m.get("refPath", "") if isinstance(m, dict) else str(m) for m in p["overrideMaterials"]]
    ok = (at_ok and sm.endswith(mesh.rsplit("/", 1)[1] + "." + mesh.rsplit("/", 1)[1]) and p["castShadow"] is False
          and p["bodyInstance"].get("collisionProfileName") == "NoCollision"
          and (mats == [] if not material else len(mats) == 1 and mats[0].endswith(material.rsplit("/", 1)[1] + "." + material.rsplit("/", 1)[1])))
    return ok, "%s (%.0f, %.0f, %.0f) yaw %.2f%s" % (label, x, y, z, yaw, "" if ok else " FAILED: %s %s" % (json.dumps(p)[:260], json.dumps(t)[:200]))


def candle(ue, label, pose):
    """read_review.py's candle proxy at pose = [x, y, z, pitch, yaw]: camera + 36 forward + 14 right - 10 up."""
    cx, cy, cz, pitch, yawd = pose
    yaw, p = math.radians(yawd), math.radians(pitch)
    x = cx + 36 * math.cos(p) * math.cos(yaw) - 14 * math.sin(yaw) + 10 * math.sin(p) * math.cos(yaw)
    y = cy + 36 * math.cos(p) * math.sin(yaw) + 14 * math.cos(yaw) + 10 * math.sin(p) * math.sin(yaw)
    z = cz + 36 * math.sin(p) - 10 * math.cos(p)
    actor = spawn(ue, "class", "/Script/Engine.PointLight", label, xform(x, y, z, 0))
    comp = {"refPath": actor + ".LightComponent0"}
    for values in ({"mobility": "Movable"}, {"intensityUnits": "Candelas"}, {"intensity": 10.0}, {"attenuationRadius": 600.0},
                   {"bUseTemperature": True}, {"temperature": 1900.0}, {"castShadows": False}):
        ue.call(OB, "set_properties", {"instance": comp, "values": json.dumps(values)})
    v = js(ue.call(OB, "get_properties", {"instance": comp, "properties": ["intensity", "intensityUnits", "attenuationRadius", "bUseTemperature", "temperature", "castShadows"]}))
    ok = (abs(v["intensity"] - 10) < 1e-3 and abs(v["attenuationRadius"] - 600) < 1e-3 and v["bUseTemperature"] is True
          and abs(v["temperature"] - 1900) < 1e-3 and v["castShadows"] is False and "Candelas" in str(v["intensityUnits"]))
    return ok, "%s (%.0f, %.0f, %.0f)%s" % (label, x, y, z, "" if ok else " FAILED: %s" % json.dumps(v))


def red_light(ue, label, x, y, z):
    actor = spawn(ue, "class", "/Script/Engine.PointLight", label, xform(x, y, z, 0))
    comp = {"refPath": actor + ".LightComponent0"}
    for values in ({"mobility": "Movable"}, {"intensityUnits": RED["intensityUnits"]}, {"intensity": RED["intensity"]},
                   {"attenuationRadius": RED["attenuationRadius"]}, {"bUseTemperature": False},
                   {"lightColor": {"r": RED_COLOR[0], "g": RED_COLOR[1], "b": RED_COLOR[2], "a": 1.0}}, {"castShadows": False}):
        ue.call(OB, "set_properties", {"instance": comp, "values": json.dumps(values)})
    v = js(ue.call(OB, "get_properties", {"instance": comp, "properties": ["intensity", "intensityUnits", "attenuationRadius", "bUseTemperature", "lightColor", "castShadows"]}))
    c = v["lightColor"]
    col = [c["r"], c["g"], c["b"]]
    if max(col) > 1.5:                                  # an 8-bit colour: compare on the 0-255 scale
        col = [k / 255.0 for k in col]
    at_ok, t = placed_at(ue, actor, x, y, z, 0.0)
    ok = (at_ok and abs(v["intensity"] - RED["intensity"]) < 1e-3 and abs(v["attenuationRadius"] - RED["attenuationRadius"]) < 1e-3
          and "Unitless" in str(v["intensityUnits"]) and v["castShadows"] is False and v["bUseTemperature"] is False
          and all(abs(a - b) < 0.02 for a, b in zip(col, RED_COLOR)))
    return ok, "%s (%.0f, %.0f, %.0f)%s" % (label, x, y, z, "" if ok else " FAILED: %s %s" % (json.dumps(v)[:300], json.dumps(t)[:200]))


def warden_figure(ue, label, x, y, z, yaw):
    """SK_Warden playing AN_Warden_Idle, read_review.py's method."""
    xf = xform(x, y, z, yaw)
    actor = spawn(ue, "asset", WARDEN, label, xf)
    comp = {"refPath": actor + ".SkeletalMeshComponent0"}
    ue.call(OB, "set_properties", {"instance": comp, "values": json.dumps({"animationMode": "AnimationSingleNode"})})
    ue.call(OB, "set_properties", {"instance": comp, "values": json.dumps({"animationData": {
        "animToPlay": CLIP + "." + CLIP.rsplit("/", 1)[1], "bSavedLooping": True, "bSavedPlaying": True,
        "savedPosition": 0.0, "savedPlayRate": 1.0}})})
    ue.call(AC, "set_actor_transform", {"actor": {"refPath": actor}, "worldspace": True, "xform": xf})
    p = js(ue.call(OB, "get_properties", {"instance": comp, "properties": ["skeletalMeshAsset", "animationMode", "animationData"]}))
    at_ok, t = placed_at(ue, actor, x, y, z, yaw)
    ok = (at_ok and p["animationMode"] == "AnimationSingleNode" and p["animationData"]["bSavedPlaying"] is True
          and p["animationData"]["animToPlay"]["refPath"].endswith("AN_Warden_Idle.AN_Warden_Idle")
          and p["skeletalMeshAsset"]["refPath"].endswith("SK_Warden.SK_Warden"))
    return ok, "%s (%.0f, %.0f, %.0f) yaw %.2f%s" % (label, x, y, z, yaw, "" if ok else " FAILED: %s %s" % (json.dumps(p)[:300], json.dumps(t)[:200]))


def tag(v):
    return ("m%d" % -v) if v < 0 else "%d" % v


# ------------------------------------------------------------------ the modes
def plan():
    """Every temporary actor as (kind, label, args); kinds: figure, glow, warden, red, candle."""
    items = []
    p = poses()
    cam = ROOF_CAM
    for fx, fy, fz in ROOF_FIGURES:
        yaw = round(yaw_to(fx, fy, cam[0], cam[1]), 2)
        items.append(("figure", PREFIX + "Roof_" + tag(fy), (fx, fy, fz, yaw)))
        # glow: 150 cm behind the figure seen from the camera (horizontal), 150 up; plane turned to face the camera:
        # pitch 90 stands the plane up with its normal on -X at yaw 0, so yaw = camera -> figure direction puts it towards the camera
        d = math.atan2(fy - cam[1], fx - cam[0])
        items.append(("glow", PREFIX + "RoofGlow_" + tag(fy),
                      (fx + GLOW_BEHIND * math.cos(d), fy + GLOW_BEHIND * math.sin(d), fz + GLOW_UP, round(math.degrees(d), 2))))
    for fx, fy, fz in RAIL_FIGURES:
        items.append(("figure", PREFIX + "Rail_" + tag(fy), (fx, fy, fz, round(yaw_to(fx, fy, RAIL_CAM[0], RAIL_CAM[1]), 2))))
    fx, fy, fz = SAC_FIGURE
    items.append(("figure", PREFIX + "Sacristy", (fx, fy, fz, round(yaw_to(fx, fy, SAC_A[0], SAC_A[1]), 2))))
    for spot in ("ossuary", "bells"):
        (fx, fy, fz), cx, cy, _ = READ_SPOTS[spot]
        yaw = round(yaw_to(fx, fy, cx, cy), 2)
        items.append(("warden", PREFIX + "Warden_" + spot, (fx, fy, fz, yaw)))
        r = math.radians(yaw)
        items.append(("red", PREFIX + "RedLight_" + spot, (fx + RED_OFFSET[0] * math.cos(r), fy + RED_OFFSET[0] * math.sin(r), fz + RED_OFFSET[1])))
    items.append(("candle", PREFIX + "CandleProxy_rail_all", tuple(p["rail_all"])))
    for spot in ("ossuary", "bells"):
        items.append(("candle", PREFIX + "CandleProxy_light_" + spot, tuple(p["light_" + spot])))
    return items


def place(ue):
    if not pie_off(ue):
        return 2
    if labelled(ue):
        print("P12F_ actors already exist: run --remove first.")
        return 2
    items = plan()
    n0 = count(ue)
    if n0 != EXPECTED_ACTORS:
        print("actor count is %d, expected %d: refusing to place." % (n0, EXPECTED_ACTORS))
        return 2
    good = True
    for kind, label, a in items:
        try:
            if kind == "figure":
                ok, msg = static_figure(ue, APPARITION, label, *a)
            elif kind == "glow":
                ok, msg = static_figure(ue, PLANE, label, a[0], a[1], a[2], a[3], pitch=90.0, scale=GLOW_SCALE, material=GLOW_MI)
            elif kind == "warden":
                ok, msg = warden_figure(ue, label, *a)
            elif kind == "red":
                ok, msg = red_light(ue, label, *a)
            else:
                ok, msg = candle(ue, label, list(a))
        except Exception as e:      # keep going so the final count and --status show what exists; --remove cleans up
            ok, msg = False, "%s raised %s" % (label, str(e)[:300])
        good = good and ok
        print("OK    " if ok else "FAILED ", msg, flush=True)
    n = count(ue)
    want = EXPECTED_ACTORS + len(items)
    print("actor count", n, "(expected %d)" % want)
    good = good and n == want
    print("PLACE", "OK" if good else "FAILED", "-- never save the map while these exist")
    return 0 if good else 1


def status(ue):
    found = labelled(ue)
    print("%s actors:" % PREFIX, [ue.call(AC, "get_label", {"actor": {"refPath": p}}) for p in found], "labelled", len(found), "census", count(ue))
    return 0


def remove(ue):
    if not pie_off(ue):
        return 2
    for p in labelled(ue):
        ue.call(SC, "remove_from_scene", {"actor": {"refPath": p}})
    left = labelled(ue)
    n = count(ue)
    print("left:", len(left), "actor count", n, "(expected %d)" % EXPECTED_ACTORS)
    good = not left and n == EXPECTED_ACTORS
    print("REMOVE", "OK" if good else "FAILED")
    return 0 if good else 1


if __name__ == "__main__":
    modes = {"--poses": None, "--place": place, "--status": status, "--remove": remove}
    args = [a for a in sys.argv[1:] if a in modes]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    if args[0] == "--poses":
        sys.exit(write_poses())
    sys.exit(modes[args[0]](UE()))
