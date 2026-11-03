"""P11-7: review poses for the lit lantern glass. Read-only in the editor (trace_world).

    python -I Tools/materials/make_lantern_poses.py

Writes Tools/materials/poses/p11_lantern_poses.json ({"name": [x, y, z, pitch, yaw]}). Every pose looks straight at the lantern's glass (centre
of the frame), so lantern_report.py can read the middle of the image. Prints the free distance from each camera to the lantern: a pose
whose line of sight is blocked is reported, and it is moved by hand here rather than accepted.
"""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "Tools", "mcp"))
from ue import UE

S = "editor_toolset.toolsets.scene.SceneTools"
OUT = os.path.join(ROOT, "Tools", "materials", "poses", "p11_lantern_poses.json")
GLASS_Z = 25  # middle of the glass above the actor origin (mesh bounds Z -1 to 52)
EYE = 170
ue = UE()

# name, lantern location, camera (x, y) at about the wanted distance; floor under the camera
L = [
    ("co_chapeldoor_10m", (5925, -140, 1), (4925, -140), 0),
    ("co_gate_10m", (350, 560, 40.5), (1350, 560), 0),
    ("co_route1_10m", (4400, 2478, 181), (4400, 1478), 0),
    ("co_garden_10m", (3400, -112, 73), (2400, -112), 0),
    ("cl_bells_10m", (11960, 2380, 278), (10960, 2380), 0),
    ("cl_west_7m", (9480, 2000, 278), (10150, 2000), 0),
    ("ps_lantern_10m", (9380, 2240, 258), (8380, 2240), 0),
    ("tw_base_3m", (12060, 1880, 218), (12350, 1880), 0),
    ("co_gate_3m", (350, 560, 40.5), (650, 560), 0),
    ("co_route1_3m", (4400, 2478, 181), (4400, 2178), 0),
    ("cl_bells_3m", (11960, 2380, 278), (11660, 2380), 0),
    ("co_gate_close", (350, 560, 40.5), (450, 500), 0),
]


def trace(a, b):
    r = ue.call(S, "trace_world", {"start": dict(zip("xyz", a)), "end": dict(zip("xyz", b))})
    r = json.loads(r) if isinstance(r, str) and r.strip() else r
    return None if r in (None, "", "null") else float(r)


def main():
    poses, blocked = {}, 0
    for name, lamp, cam_xy, floor in L:
        target = (lamp[0], lamp[1], lamp[2] + GLASS_Z)
        cam = (cam_xy[0], cam_xy[1], floor + EYE)
        dx, dy, dz = target[0] - cam[0], target[1] - cam[1], target[2] - cam[2]
        flat = math.hypot(dx, dy)
        dist = math.hypot(flat, dz)
        hit = trace(cam, target)
        ok = hit is None or hit >= dist - 40
        blocked += not ok
        poses[name] = [cam[0], cam[1], cam[2], round(math.degrees(math.atan2(dz, flat)), 1), round(math.degrees(math.atan2(dy, dx)), 1)]
        print("%-20s %s dist %5.0f hit %s %s" % (name, poses[name], dist, "none" if hit is None else "%.0f" % hit, "" if ok else "BLOCKED"))
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(poses, fh, indent=1)
    print(len(poses), "poses,", blocked, "blocked")
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
