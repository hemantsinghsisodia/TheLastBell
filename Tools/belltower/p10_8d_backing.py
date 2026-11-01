"""P10-8d F6 (D1.27): hidden backing plates behind the chapel's kit west front (Unreal MCP).

The owner's bright square lands on the vertical seam at Y 200 / the Z 800 seam of the chapel west front (kit pieces X 6000-6060). Every west-front window is blind, so
a bright square there is the lit nave seen through a hairline gap between kit pieces. Three thin masonry plates inside the 60 cm wall core (X 6028-6032) show stone
instead of the nave if a gap exists. They are invisible otherwise.

Usage (editor open on L_Monastery, PIE stopped; one editor-touching process at a time):
    python p10_8d_backing.py            # idempotent: removes the 3 labels first, places them, reads back bounds / collision / material / shadow / folder
    python p10_8d_backing.py --check    # read-back only (no edits); exit 1 on any FAIL

Each plate: engine Cube (100 cm, centred), MI_Kit_Masonry in slot 0, bodyInstance.collisionProfileName = NoCollision + collisionEnabled = NoCollision with
bUseDefaultCollision false (MCP_NOTES P9 section 3), castShadow true, folder Chapel/Art/WestFrontBacking.
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
E = "EditorToolset.EditorAppToolset"
CUBE = "/Engine/BasicShapes/Cube.Cube"
MI = "/Game/LastBell/Environments/Kit/Materials/MI_Kit_Masonry.MI_Kit_Masonry"
FOLDER = "Chapel/Art/WestFrontBacking"
PLATES = [   # label, location, rotation, scale
    ("KC_WestFront_Backing_0", (6030.0, 0.0, 800.0), (0.0, 0.0, 0.0), (0.04, 15.8, 8.0)),
    ("KC_WestFront_Backing_1", (6030.0, 495.0, 430.0), (0.0, 0.0, 0.0), (0.04, 5.9, 7.4)),
    ("KC_WestFront_Backing_2", (6030.0, -495.0, 430.0), (0.0, 0.0, 0.0), (0.04, 5.9, 7.4)),
]
UE_ = UE()


def call(ts, tool, args=None):
    return UE_.call(ts, tool, args)


def props(inst, names):
    r = call(O, "get_properties", {"instance": inst, "properties": names})
    return json.loads(r) if isinstance(r, str) else r


def find_label(label):
    return [a for a in (call(S, "find_actors", {"name": label, "tag": "", "collision_channels": []}) or []) if call(A, "get_label", {"actor": a}) == label]


def xf(loc, rot, sc):
    return {"location": dict(zip("xyz", loc)), "rotation": {"pitch": rot[0], "yaw": rot[1], "roll": rot[2]}, "scale": dict(zip("xyz", sc))}


def readback(label, loc, rot, sc):
    found = find_label(label)
    if len(found) != 1:
        print("FAIL  %s: %d actors found" % (label, len(found)))
        return False
    a = found[0]
    comp = call(A, "get_components", {"actor": a})[0]
    p = props(comp, ["bUseDefaultCollision", "bodyInstance", "overrideMaterials", "castShadow", "bVisible"])
    bi = p["bodyInstance"]
    b = call(A, "get_actor_bounds", {"actor": a})
    mn, mx = [b["min"][k] for k in "xyz"], [b["max"][k] for k in "xyz"]
    want_mn = [loc[i] - 50.0 * sc[i] for i in range(3)]
    want_mx = [loc[i] + 50.0 * sc[i] for i in range(3)]
    t = call(A, "get_actor_transform", {"actor": a, "worldspace": True})
    gl = [t["location"][k] for k in "xyz"]
    gs = [t["scale"][k] for k in "xyz"]
    mats = [m.get("refPath", "").split("/")[-1].split(".")[0] if isinstance(m, dict) else None for m in p["overrideMaterials"]]
    folder = None
    for x in call(S, "get_actors_in_folder", {"folder_path": FOLDER, "recursive": False}) or []:
        if call(A, "get_label", {"actor": x}) == label:
            folder = FOLDER
    issues = []
    if max(abs(mn[i] - want_mn[i]) for i in range(3)) > 0.5 or max(abs(mx[i] - want_mx[i]) for i in range(3)) > 0.5:
        issues.append("bounds %s..%s want %s..%s" % (mn, mx, want_mn, want_mx))
    if max(abs(gl[i] - loc[i]) for i in range(3)) > 0.1 or max(abs(gs[i] - sc[i]) for i in range(3)) > 1e-3:
        issues.append("transform %s %s" % (gl, gs))
    if bi["collisionProfileName"] != "NoCollision" or bi.get("collisionEnabled") != "NoCollision" or p["bUseDefaultCollision"]:
        issues.append("collision %s enabled %s useDefault %s" % (bi["collisionProfileName"], bi.get("collisionEnabled"), p["bUseDefaultCollision"]))
    if mats[:1] != ["MI_Kit_Masonry"]:
        issues.append("material %s" % mats)
    if not p["castShadow"]:
        issues.append("castShadow false")
    if folder != FOLDER:
        issues.append("folder %s" % folder)
    print("%s  %s: bounds X %.1f..%.1f Y %.1f..%.1f Z %.1f..%.1f; loc %s scale %s; collision %s / %s (useDefault %s); material %s; castShadow %s; visible %s; folder %s%s" % (
        "PASS" if not issues else "FAIL", label, mn[0], mx[0], mn[1], mx[1], mn[2], mx[2], [round(v, 2) for v in gl], [round(v, 3) for v in gs],
        bi["collisionProfileName"], bi.get("collisionEnabled"), p["bUseDefaultCollision"], mats[:1], p["castShadow"], p["bVisible"], folder,
        "" if not issues else " :: " + "; ".join(issues)))
    return not issues


def place():
    for label, loc, rot, sc in PLATES:
        n = 0
        for a in find_label(label):
            call(S, "remove_from_scene", {"actor": a})
            n += 1
        t = xf(loc, rot, sc)
        a = call(S, "add_to_scene_from_asset", {"asset_path": CUBE, "name": label, "xform": t})
        if not a:
            raise RuntimeError("spawn failed for " + label)
        call(A, "set_actor_transform", {"actor": a, "xform": t, "worldspace": True})      # one full transform call (never partial)
        call(A, "set_label", {"actor": a, "label": label})
        call(S, "set_actor_folder", {"actor": a, "folder_path": FOLDER})
        comp = call(A, "get_components", {"actor": a})[0]
        call(O, "set_properties", {"instance": comp, "values": json.dumps({
            "bUseDefaultCollision": False, "bodyInstance": {"collisionProfileName": "NoCollision", "collisionEnabled": "NoCollision"},
            "castShadow": True, "overrideMaterials": [{"refPath": MI}]})})
        print("placed %s (removed %d existing)" % (label, n), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if call(E, "IsPIERunning"):
        sys.exit("PIE is running: stop it first")
    if not str(call(S, "get_current_level")).endswith("L_Monastery"):
        sys.exit("editor is not on L_Monastery")
    if not args.check:
        place()
    ok = all([readback(*p) for p in PLATES])
    print("RESULT", "OK" if ok else "CHECK")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
