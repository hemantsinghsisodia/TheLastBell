"""P12-6 read review: stand the Warden in the game's real lighting, in the editor world, for captures.

    python Tools/warden/read_review.py --poses     # writes Tools/warden/poses/p12_read_poses.json and p12_read_candle_poses.json
    python Tools/warden/read_review.py --place     # 4 temporary figures playing Idle, each facing its cameras
    python Tools/warden/read_review.py --candles   # adds the 4 candle proxies (for the second capture session only)
    python Tools/warden/read_review.py --trace     # greybox traces from each camera to its figure (art has no collision)
    python Tools/warden/read_review.py --status
    python Tools/warden/read_review.py --remove    # removes every P12_* actor and confirms the census count

Everything here is temporary: NEVER save L_Monastery while a P12_* actor exists. PIE must be off to place or remove.

Since V5.5 (D-091) the mesh AND the clips face mesh +X (owner's Reports/facing-corrected-v5_5.json), so a figure
facing world direction D has actor yaw D, with the mesh at yaw 0. (V5's clips faced +Y, which needed D - 90.)
The candle proxy copies the player's candle: 10 cd, 1900 K, radius 600, no shadows, camera + (36, 14, -10). Its radius
means it can't reach a figure at 8 m, so only the 3 m views get a candle variant.
"""
import json
import math
import os
import sys
import time

HERE =os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "mcp"))
from ue import UE  # noqa: E402

SC = "editor_toolset.toolsets.scene.SceneTools"
AC = "editor_toolset.toolsets.actor.ActorTools"
OB = "editor_toolset.toolsets.object.ObjectTools"
APP = "EditorToolset.EditorAppToolset"

MESH = "/Game/LastBell/Characters/Warden/Meshes/SK_Warden"
CLIP = "/Game/LastBell/Characters/Warden/Anims/AN_Warden_Idle"
EXPECTED_ACTORS = 2980
EYE = 165.0

# figure XYZ, then cameras (name, x, y, pitch). Camera Z is floor + eye height. Each figure faces its first camera.
SPOTS = {
    "ossuary": ((8850.0, -2250.0, -600.0), [("3m", 8550.0, -2250.0, 8.0), ("8m", 8050.0, -2250.0, 2.0), ("15m", 7400.0, -2350.0, 2.0)]),
    "chain": ((10800.0, -1780.0, -600.0), [("3m", 10573.0, -1977.0, 8.0), ("8m", 10195.0, -2304.0, 2.0), ("side6m", 11200.0, -2200.0, 4.0)]),
    "bells": ((11750.0, 2650.0, 0.0), [("3m", 11750.0, 2350.0, 8.0), ("8m", 11750.0, 1850.0, 2.0), ("18m", 11750.0, 850.0, 1.0)]),
    "west": ((9850.0, 2000.0, 0.0), [("3m", 9850.0, 1700.0, 8.0), ("8m", 9850.0, 1200.0, 2.0), ("12m", 9850.0, 800.0, 1.0)]),
}


def yaw_to(ax, ay, bx, by):
    return math.degrees(math.atan2(by - ay, bx - ax))


def poses():
    out, candle = {}, {}
    for spot, ((fx, fy, fz), cams) in SPOTS.items():
        for name, cx, cy, pitch in cams:
            pose = [cx, cy, fz + EYE, pitch, round(yaw_to(cx, cy, fx, fy), 2)]
            out["p12r_%s_%s" % (spot, name)] = pose
            if name == "3m":
                candle["p12r_%s_%s" % (spot, name)] = pose
    return out, candle


def write_poses():
    out, candle = poses()
    d = os.path.join(HERE, "poses")
    with open(os.path.join(d, "p12_read_poses.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    with open(os.path.join(d, "p12_read_candle_poses.json"), "w", encoding="utf-8") as f:
        json.dump(candle, f, indent=1)
    print("wrote %d + %d poses" % (len(out), len(candle)))
    return 0


def labelled(ue):
    found = []
    for a in ue.call(SC, "find_actors", {"name": "P12_", "tag": "", "collision_channels": []}):
        p = a["refPath"] if isinstance(a, dict) else a
        if str(ue.call(AC, "get_label", {"actor": {"refPath": p}})).startswith("P12_"):
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


def xform(x, y, z, yaw):
    return {"location": {"x": x, "y": y, "z": z}, "rotation": {"pitch": 0, "yaw": yaw, "roll": 0}, "scale": {"x": 1, "y": 1, "z": 1}}


def pie_off(ue):
    if ue.call(APP, "IsPIERunning", {}) is True:
        print("PIE/Simulate is running: stop it first.")
        return False
    return True


def place(ue):
    if not pie_off(ue):
        return 2
    good = True
    for spot, ((fx, fy, fz), cams) in SPOTS.items():
        label = "P12_Review_" + spot
        _, cx, cy, _ = cams[0]
        yaw = round(yaw_to(fx, fy, cx, cy), 2)   # V5.5: mesh and clips face +X, so actor yaw = D
        r = ue.call(SC, "add_to_scene_from_asset", {"asset_path": MESH, "name": label, "xform": xform(fx, fy, fz, yaw)})
        actor = r["refPath"] if isinstance(r, dict) else r
        ue.call(AC, "set_label", {"actor": {"refPath": actor}, "label": label})
        comp = {"refPath": actor + ".SkeletalMeshComponent0"}
        ue.call(OB, "set_properties", {"instance": comp, "values": json.dumps({"animationMode": "AnimationSingleNode"})})
        ue.call(OB, "set_properties", {"instance": comp, "values": json.dumps({"animationData": {
            "animToPlay": CLIP + "." + CLIP.rsplit("/", 1)[1], "bSavedLooping": True, "bSavedPlaying": True,
            "savedPosition": 0.0, "savedPlayRate": 1.0}})})
        ue.call(AC, "set_actor_transform", {"actor": {"refPath": actor}, "worldspace": True, "xform": xform(fx, fy, fz, yaw)})
        p = ue.call(OB, "get_properties", {"instance": comp, "properties": ["skeletalMeshAsset", "animationMode", "animationData"]})
        p = json.loads(p) if isinstance(p, str) else p
        ok = p["animationMode"] == "AnimationSingleNode" and p["animationData"]["bSavedPlaying"] is True \
            and p["animationData"]["animToPlay"]["refPath"].endswith("AN_Warden_Idle.AN_Warden_Idle") \
            and p["skeletalMeshAsset"]["refPath"].endswith("SK_Warden.SK_Warden")
        good = good and ok
        print(label, "yaw", yaw, "OK" if ok else "FAILED: %s" % json.dumps(p)[:300])
    n = count(ue)
    print("actor count", n, "(expected %d)" % (EXPECTED_ACTORS + len(SPOTS)))
    print("PLACE", "OK" if good and n == EXPECTED_ACTORS + len(SPOTS) else "FAILED")
    return 0 if good else 1


def candles(ue):
    if not pie_off(ue):
        return 2
    good = True
    for spot, ((fx, fy, fz), cams) in SPOTS.items():
        _, cx, cy, pitch = cams[0]
        yaw = math.radians(yaw_to(cx, cy, fx, fy))
        p = math.radians(pitch)
        cz = fz + EYE
        # camera + 36 forward + 14 right - 10 up
        x = cx + 36 * math.cos(p) * math.cos(yaw) - 14 * math.sin(yaw) + 10 * math.sin(p) * math.cos(yaw)
        y = cy + 36 * math.cos(p) * math.sin(yaw) + 14 * math.cos(yaw) + 10 * math.sin(p) * math.sin(yaw)
        z = cz + 36 * math.sin(p) - 10 * math.cos(p)
        label = "P12_CandleProxy_" + spot
        r = ue.call(SC, "add_to_scene_from_class", {"actor_type": {"refPath": "/Script/Engine.PointLight"}, "name": label, "xform": xform(x, y, z, 0)})
        actor = r["refPath"] if isinstance(r, dict) else r
        ue.call(AC, "set_label", {"actor": {"refPath": actor}, "label": label})
        comp = {"refPath": actor + ".LightComponent0"}
        for values in ({"mobility": "Movable"}, {"intensityUnits": "Candelas"}, {"intensity": 10.0}, {"attenuationRadius": 600.0},
                       {"bUseTemperature": True}, {"temperature": 1900.0}, {"castShadows": False}):
            ue.call(OB, "set_properties", {"instance": comp, "values": json.dumps(values)})
        v = ue.call(OB, "get_properties", {"instance": comp, "properties": ["intensity", "intensityUnits", "attenuationRadius", "bUseTemperature", "temperature", "castShadows"]})
        v = json.loads(v) if isinstance(v, str) else v
        ok = abs(v["intensity"] - 10) < 1e-3 and abs(v["attenuationRadius"] - 600) < 1e-3 and v["bUseTemperature"] is True \
            and abs(v["temperature"] - 1900) < 1e-3 and v["castShadows"] is False and "Candelas" in str(v["intensityUnits"])
        good = good and ok
        print(label, (round(x), round(y), round(z)), "OK" if ok else "FAILED: %s" % json.dumps(v))
    print("CANDLES", "OK" if good else "FAILED")
    return 0 if good else 1


def trace(ue):
    worst = 0
    for spot, ((fx, fy, fz), cams) in SPOTS.items():
        for name, cx, cy, _ in cams:
            d = ue.call(SC, "trace_world", {"start": {"x": cx, "y": cy, "z": fz + EYE}, "end": {"x": fx, "y": fy, "z": fz + 150}})
            dist = math.dist((cx, cy), (fx, fy))
            blocked = d is not None and d < dist - 150
            worst += 1 if blocked else 0
            print("%-8s %-8s %5.0f cm  %s" % (spot, name, dist, "BLOCKED at %.0f" % d if blocked else "clear"))
    print("blocked:", worst)
    return 0


def status(ue):
    found = labelled(ue)
    print("P12_ actors:", [ue.call(AC, "get_label", {"actor": {"refPath": p}}) for p in found], "count", count(ue))
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
    modes = {"--poses": None, "--place": place, "--candles": candles, "--trace": trace, "--status": status, "--remove": remove}
    args = [a for a in sys.argv[1:] if a in modes]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    if args[0] == "--poses":
        sys.exit(write_poses())
    sys.exit(modes[args[0]](UE()))
