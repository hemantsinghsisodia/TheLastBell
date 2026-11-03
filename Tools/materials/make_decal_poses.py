"""P11-6: review camera poses for the decals, one per decal MI per area, from census_p11.json. Read-only in the editor (trace_world).

    python -I Tools/materials/make_decal_poses.py [--cracks]

Writes Tools/materials/poses/p11_decal_poses.json ({"name": [x, y, z, pitch, yaw]}) and prints which decal each pose looks at.
--cracks writes Tools/materials/poses/p11_crack_poses.json instead, from p11_crack_decals.json.
Chalk and light-pool decals are skipped: chalk is a puzzle clue and neither master has an opacity value to retune.
"""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "Tools", "mcp"))
from ue import UE

S = "editor_toolset.toolsets.scene.SceneTools"
SKIP = ("MI_Decal_ChalkSigil", "MI_Decal_ChalkCircle", "MI_Decal_ChalkTally", "MI_Decal_LightPool_Lancet")
ue = UE()


def clear(a, b):
    r = ue.call(S, "trace_world", {"start": dict(zip("xyz", a)), "end": dict(zip("xyz", b))})
    r = json.loads(r) if isinstance(r, str) and r.strip() else r
    length = math.dist(a, b)
    return length if r in (None, "", "null") else min(float(r), length)


def crack_poses():
    """One view per crack decal from p11_crack_decals.json: straight in front of it at eye height, looking at its centre."""
    cracks = json.load(open(os.path.join(ROOT, "Tools", "materials", "p11_crack_decals.json"), encoding="utf-8"))
    poses = {}
    for a in cracks:
        l, yaw = a["location"], a["rotation"]["yaw"]
        c = (l["x"], l["y"], l["z"])
        f = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw)))
        floor = -600 if c[2] < -100 else (c[2] // 1000) * 1000 if c[2] > 1000 else 0
        eye = c[2] - 60 if a["label"].startswith("Crack_Tw_") and c[2] > 500 else floor + 170
        start = (c[0] - f[0] * 5, c[1] - f[1] * 5, eye)
        want = max(300, a["size"]["y"] * 3)
        d = max(120, min(want, clear(start, (c[0] - f[0] * want, c[1] - f[1] * want, eye)) - 30))
        cam = (c[0] - f[0] * d, c[1] - f[1] * d, eye)
        pitch = math.degrees(math.atan2(c[2] - eye, d))
        name = a["label"].replace("Crack_", "").lower()
        poses[name] = [round(cam[0]), round(cam[1]), round(cam[2]), round(pitch, 1), round(((yaw + 180) % 360) - 180, 1)]
        print("%-22s %s" % (name, poses[name]))
    out = os.path.join(ROOT, "Tools", "materials", "poses", "p11_crack_poses.json")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(poses, fh, indent=1)
    print(len(poses), "poses")


def main():
    if "--cracks" in sys.argv:
        crack_poses()
        return
    census = json.load(open(os.path.join(ROOT, "Docs", "ArtTest", "materials", "census_p11.json"), encoding="utf-8"))
    seen, poses = set(), {}
    for a in sorted(census["decals"], key=lambda d: d["label"]):
        mi = a["material"].split(".")[-1]
        key = (mi, a["area"])
        if mi in SKIP or key in seen:
            continue
        seen.add(key)
        l, r = a["location"], a["rotation"]
        c = (l["x"], l["y"], l["z"])
        floor = -600 if c[2] < -100 else 0
        name = "%s_%s" % (a["area"][:2], mi.replace("MI_", "").replace("Decal_", "").lower())
        if abs(r["pitch"]) < 5:
            yaw = r["yaw"]
            f = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw)))
            eye = floor + 170
            start = (c[0] - f[0] * 5, c[1] - f[1] * 5, eye)
            want = 500 if c[2] - eye > 200 else 320
            d = min(want, clear(start, (c[0] - f[0] * want, c[1] - f[1] * want, eye)) - 30)
            cam = (c[0] - f[0] * d, c[1] - f[1] * d, eye)
            pitch = math.degrees(math.atan2(c[2] - eye, d))
        else:
            eye = max(c[2] + 120, floor + 170)
            best = None
            for k in range(8):
                ang = math.radians(k * 45)
                p = (c[0] + math.cos(ang) * 260, c[1] + math.sin(ang) * 260, eye)
                d = clear((c[0], c[1], eye), p)
                if best is None or d > best[0]:
                    best = (d, ang)
            d = min(260, best[0] - 30)
            cam = (c[0] + math.cos(best[1]) * d, c[1] + math.sin(best[1]) * d, eye)
            yaw = math.degrees(best[1]) + 180
            pitch = -math.degrees(math.atan2(eye - c[2], d))
        poses[name] = [round(cam[0]), round(cam[1]), round(cam[2]), round(pitch, 1), round(((yaw + 180) % 360) - 180, 1)]
        print("%-34s %-26s %s" % (name, a["label"], poses[name]))
    out = os.path.join(ROOT, "Tools", "materials", "poses", "p11_decal_poses.json")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(poses, fh, indent=1)
    print(len(poses), "poses")


if __name__ == "__main__":
    main()
