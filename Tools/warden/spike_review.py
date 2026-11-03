"""spike_review.py -- P12-1 check 5 helper: put the spike figure into the editor world, play its clip, take it away.

    python Tools/warden/spike_review.py --place     # adds a SkeletalMeshActor labelled P12_Spike at (5800, 0, 0)
    python Tools/warden/spike_review.py --remove    # deletes it and confirms it is gone (and the actor count is back)
    python Tools/warden/spike_review.py --status    # reads the actor back (or says there is none)

The editor must be open on L_Monastery; no PIE is running (SceneTools refuses to spawn during PIE; place first, then
start Simulate, take the captures, stop Simulate, then --remove). The actor lives in the editor world only: NEVER save
L_Monastery while it exists. It dirties the map in memory; the lead handles that (do not save the map afterwards either).

Placement: the courtyard, 200 cm in front of the chapel door (door at x ~ 6000, lantern PointLight_2 at (5925, -140, 75)).
The figure faces -X (towards a camera standing west of it): mesh forward is +Y, so yaw +90. Its LEFT (mesh +X)
is then world +Y. Clip: /Game/LastBell/ArtTest/P12/AS_P12_Clip, AnimationSingleNode, looping, playing.

Poses for the capture (the lead runs it, with the owner told first and Unreal in front):
    python Tools/crypt/capture_session.py Tools/warden/poses/p12_spike_poses.json <out_dir> --prefix P12S --mode simulate
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mcp"))
from ue import UE  # noqa: E402

SC = "editor_toolset.toolsets.scene.SceneTools"
AC = "editor_toolset.toolsets.actor.ActorTools"
OB = "editor_toolset.toolsets.object.ObjectTools"
APP = "EditorToolset.EditorAppToolset"

LABEL = "P12_Spike"
MESH = "/Game/LastBell/ArtTest/P12/SK_P12_Spike"
CLIP = "/Game/LastBell/ArtTest/P12/AS_P12_Clip"
LOC = (5800.0, 0.0, 0.0)
YAW = 90.0
EXPECTED_ACTORS = 2980          # census of L_Monastery without temporaries (P11 close-out)


def find(ue):
    out = []
    for a in ue.call(SC, "find_actors", {"name": LABEL, "tag": "", "collision_channels": []}):
        p = a["refPath"] if isinstance(a, dict) else a
        lab = ue.call(AC, "get_label", {"actor": {"refPath": p}})
        if lab == LABEL:
            out.append(p)
    return out


def count(ue):
    return len(ue.call(SC, "find_actors", {"name": "", "tag": "", "collision_channels": []}))


def read_back(ue, actor):
    comp = {"refPath": actor + ".SkeletalMeshComponent0"}
    props = ue.call(OB, "get_properties", {"instance": comp, "properties": ["skeletalMeshAsset", "animationMode", "animationData"]})
    props = json.loads(props) if isinstance(props, str) else props
    tf = ue.call(AC, "get_actor_transform", {"actor": {"refPath": actor}, "worldspace": True})
    try:
        bounds = ue.call(AC, "get_actor_bounds", {"actor": {"refPath": actor}})
    except Exception as e:  # noqa: BLE001
        bounds = "ERR %s" % str(e)[:120]
    return props, tf, bounds


def check(props):
    ad = props["animationData"]
    ok = {
        "mesh": isinstance(props["skeletalMeshAsset"], dict) and props["skeletalMeshAsset"]["refPath"].endswith("SK_P12_Spike.SK_P12_Spike"),
        "mode": props["animationMode"] == "AnimationSingleNode",
        "clip": isinstance(ad["animToPlay"], dict) and ad["animToPlay"]["refPath"].endswith("AS_P12_Clip.AS_P12_Clip"),
        "looping": ad["bSavedLooping"] is True,
        "playing": ad["bSavedPlaying"] is True,
        "rate": ad["savedPlayRate"] == 1,
    }
    return ok


def do_place(ue):
    if ue.call(APP, "IsPIERunning", {}) is True:
        print("PIE/Simulate is running: stop it first (SceneTools cannot spawn during PIE).")
        return 2
    for p in find(ue):
        print("removing leftover", p)
        ue.call(SC, "remove_from_scene", {"actor": {"refPath": p}})
    r = ue.call(SC, "add_to_scene_from_asset", {
        "asset_path": MESH, "name": LABEL,
        "xform": {"location": {"x": LOC[0], "y": LOC[1], "z": LOC[2]}, "rotation": {"pitch": 0, "yaw": YAW, "roll": 0},
                  "scale": {"x": 1, "y": 1, "z": 1}}})
    actor = r["refPath"] if isinstance(r, dict) else r
    print("placed:", actor)
    if ue.call(AC, "get_label", {"actor": {"refPath": actor}}) != LABEL:
        ue.call(AC, "set_label", {"actor": {"refPath": actor}, "label": LABEL})
    comp = {"refPath": actor + ".SkeletalMeshComponent0"}
    ue.call(OB, "set_properties", {"instance": comp, "values": json.dumps({"animationMode": "AnimationSingleNode"})})
    ue.call(OB, "set_properties", {"instance": comp, "values": json.dumps({"animationData": {
        "animToPlay": CLIP + "." + CLIP.rsplit("/", 1)[1], "bSavedLooping": True, "bSavedPlaying": True,
        "savedPosition": 0.0, "savedPlayRate": 1.0}})})
    # always set the transform explicitly (location AND rotation AND scale), then read back
    ue.call(AC, "set_actor_transform", {"actor": {"refPath": actor}, "worldspace": True, "xform": {
        "location": {"x": LOC[0], "y": LOC[1], "z": LOC[2]}, "rotation": {"pitch": 0, "yaw": YAW, "roll": 0},
        "scale": {"x": 1, "y": 1, "z": 1}}})
    props, tf, bounds = read_back(ue, actor)
    ok = check(props)
    print("label:", ue.call(AC, "get_label", {"actor": {"refPath": actor}}))
    print("props:", json.dumps(props))
    print("transform:", json.dumps(tf))
    print("bounds:", json.dumps(bounds))
    print("checks:", ok)
    n = count(ue)
    print("actor count now %d (expected %d + 1 = %d)" % (n, EXPECTED_ACTORS, EXPECTED_ACTORS + 1))
    good = all(ok.values()) and abs(tf["location"]["x"] - LOC[0]) < 0.5 and abs(tf["rotation"]["yaw"] - YAW) < 0.5
    print("PLACE", "OK" if good else "FAILED")
    return 0 if good else 1


def do_remove(ue):
    found = find(ue)
    for p in found:
        print("removing", p, ue.call(SC, "remove_from_scene", {"actor": {"refPath": p}}))
    left = find(ue)
    n = count(ue)
    print("remaining P12_Spike actors: %d; actor count %d (expected %d)" % (len(left), n, EXPECTED_ACTORS))
    good = not left and n == EXPECTED_ACTORS
    print("REMOVE", "OK" if good else "FAILED")
    return 0 if good else 1


def do_status(ue):
    found = find(ue)
    if not found:
        print("no P12_Spike actor; actor count", count(ue))
        return 0
    for p in found:
        props, tf, bounds = read_back(ue, p)
        print(p, json.dumps(props), json.dumps(tf), json.dumps(bounds), check(props))
    return 0


if __name__ == "__main__":
    mode = [a for a in sys.argv[1:] if a in ("--place", "--remove", "--status")]
    if len(mode) != 1:
        print(__doc__)
        sys.exit(2)
    ue = UE()
    sys.exit({"--place": do_place, "--remove": do_remove, "--status": do_status}[mode[0]](ue))
