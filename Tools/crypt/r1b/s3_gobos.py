"""P9-R1B D1.23: delete the 4 MoonRect lights, place 16 hidden shadow-only gobo cubes (4 per outside moon spot), set the spots' lighting channels 0+1 and scattering 0.
Editor world, PIE stopped. Idempotent (removes its own labels first). Usage: python s3_gobos.py [--widen K=cm,...] [--check]
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *  # noqa: F401,F403,E402

D = 150.0
OUTER = 14.0
H = math.ceil((D * math.tan(math.radians(OUTER)) + 15.0) / 5.0) * 5.0
CUBE = "/Engine/BasicShapes/Cube.Cube"
FOLDER = "Lighting/Chapel/Gobos"
SPOTS = {"S1": "Light_Chapel_Moon_S1", "S2": "Light_Chapel_Moon_S2", "S3": "Light_Chapel_Moon_S3", "Roof": "Light_Chapel_Moon_Roof"}
widen = {}
if "--widen" in sys.argv:
    for kv in sys.argv[sys.argv.index("--widen") + 1].split(","):
        k, v = kv.split("=")
        widen[k] = float(v)


def axes(pitch, yaw, roll=0.0):
    cp, sp, cy, sy = math.cos(math.radians(pitch)), math.sin(math.radians(pitch)), math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    d = (cp * cy, cp * sy, sp)
    r = (-sy, cy, 0.0)
    u = (-sp * cy, -sp * sy, cp)
    return d, r, u


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def ue_axes(pitch, yaw, roll):
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    sy, cy = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    sr, cr = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    return ((cp * cy, cp * sy, sp), (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp), (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp))


def corners(key):
    if key == "Roof":
        xa, ya, za = ue_axes(0, 180, 50)
        loc = (7000.0, 0.0, 2165.0)
        xmin, xmax, ymin, ymax = 282, 735, 295, 932   # hole aperture bbox in the slab frame (s1_geom.py), on the slab's inner plane (local z 0)
        return [tuple(loc[i] + xa[i] * x + ya[i] * y for i in range(3)) for x in (xmin, xmax) for y in (ymin, ymax)]
    gx = {"S1": 6500.0, "S2": 7500.0, "S3": 8500.0}[key]
    # full lancet opening (X +-70, Z 450..1010) on the window plane; S1's glass is broken (top 862) but the opening is the full lancet
    return [(gx + sx * 70.0, -790.5, z) for sx in (-1, 1) for z in (450.0, 1010.0)]


def main():
    for lbl in ["Light_Chapel_MoonRect_S1", "Light_Chapel_MoonRect_S2", "Light_Chapel_MoonRect_S3", "Light_Chapel_MoonRect_Roof"]:
        for a in find_label(lbl, world="editor"):
            call(S, "remove_from_scene", {"actor": a})
            print("deleted", lbl)
    report = {}
    for key, slbl in SPOTS.items():
        sp = find_label(slbl, world="editor")
        assert len(sp) == 1
        loc, rot, _ = tf(sp[0])
        d, r, u = axes(rot[0], rot[1])
        L = loc
        ys, zs = [], []
        for c in corners(key):
            v = [c[i] - L[i] for i in range(3)]
            k = D / dot(v, d)
            p = [v[i] * k for i in range(3)]
            ys.append(dot(p, r))
            zs.append(dot(p, u))
        w = widen.get(key, 0.0)
        y0, y1, z0, z1 = min(ys) - 1.5 - w, max(ys) + 1.5 + w, min(zs) - 1.5 - w, max(zs) + 1.5 + w
        pieces = {"T": (-H, H, z1, H), "B": (-H, H, -H, z0), "L": (-H, y0, z0, z1), "R": (y1, H, z0, z1)}
        report[key] = {"aperture": [y0, y1, z0, z1], "H": H, "spot_loc": L, "spot_rot": rot}
        print(key, "aperture y %.1f..%.1f z %.1f..%.1f (%.1f x %.1f cm) H %.0f" % (y0, y1, z0, z1, y1 - y0, z1 - z0, H))
        for tag, (a0, a1, b0, b1) in pieces.items():
            lbl = "Gobo_Moon_%s_%s" % (key, tag)
            for a in find_label(lbl, world="editor"):
                call(S, "remove_from_scene", {"actor": a})
            yc, zc = (a0 + a1) / 2, (b0 + b1) / 2
            ctr = [L[i] + D * d[i] + yc * r[i] + zc * u[i] for i in range(3)]
            sc = (0.02, (a1 - a0) / 100.0, (b1 - b0) / 100.0)
            a = call(S, "add_to_scene_from_asset", {"asset_path": CUBE, "name": lbl, "xform": xf(ctr, rot, sc)})
            call(A, "set_label", {"actor": a, "label": lbl})
            call(S, "set_actor_folder", {"actor": a, "folder_path": FOLDER})
            comp = {"refPath": a["refPath"] + ".StaticMeshComponent0"}
            setp(comp, {"bHiddenInGame": True, "castShadow": True, "bCastHiddenShadow": True, "bAffectDistanceFieldLighting": False,
                        "bAffectDynamicIndirectLighting": False, "bVisibleInRayTracing": False, "bUseDefaultCollision": False,
                        "lightingChannels": {"bChannel0": False, "bChannel1": True, "bChannel2": False},
                        "bodyInstance": {"collisionProfileName": "NoCollision", "collisionEnabled": "NoCollision"}})
            st = props(comp, ["bHiddenInGame", "castShadow", "bCastHiddenShadow", "bAffectDistanceFieldLighting", "bAffectDynamicIndirectLighting",
                              "bVisibleInRayTracing", "lightingChannels", "bodyInstance"])
            gl, gr, gs = tf(a)
            ok = (st["bHiddenInGame"] and st["castShadow"] and st["bCastHiddenShadow"] and not st["bAffectDistanceFieldLighting"]
                  and not st["bAffectDynamicIndirectLighting"] and not st["bVisibleInRayTracing"]
                  and st["lightingChannels"] == {"bChannel0": False, "bChannel1": True, "bChannel2": False}
                  and st["bodyInstance"]["collisionProfileName"] == "NoCollision" and st["bodyInstance"]["collisionEnabled"] == "NoCollision")
            print("  %s ctr %s sc %s -> read loc %s rot %s sc %s flags %s" % (lbl, [round(v, 1) for v in ctr], [round(v, 3) for v in sc],
                  [round(v, 1) for v in gl], [round(v, 2) for v in gr], [round(v, 3) for v in gs], "OK" if ok else "CHECK " + json.dumps(st)))
        comp = {"refPath": sp[0]["refPath"] + ".LightComponent0"}
        setp(comp, {"lightingChannels": {"bChannel0": True, "bChannel1": True, "bChannel2": False}, "volumetricScatteringIntensity": 0.0})
        print("  spot", slbl, props(comp, ["lightingChannels", "volumetricScatteringIntensity", "intensity", "castShadows", "innerConeAngle", "outerConeAngle", "attenuationRadius"]))
    json.dump(report, open(os.path.join(SCR, "gobos.json"), "w"), indent=1)


main()
