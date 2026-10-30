"""P10-6b numeric checks (D1.17): bell bounds + traces + glyph texts, inscription Plaque bounds, capstan AABB/clearance. Read-only.
Component world bounds are computed from the mesh's local bounds (StaticMeshTools.get_bounds) and the live relative transforms
(all component rotations are 0; only the actor yaw matters), because the actor-level bounds include editor sprites."""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "mcp"))
from ue import UE  # noqa: E402
import bp_swap  # noqa: E402

S, A, O = bp_swap.S, bp_swap.A, bp_swap.O
SM = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
ue = UE()


def props(obj, names):
    r = ue.call(O, "get_properties", {"instance": obj, "properties": names})
    return json.loads(r) if isinstance(r, str) else r


def comp(actor, name):
    return {"refPath": actor["refPath"] + "." + name}


def world_box(actor, chain):
    """chain = component names from the root-most to the mesh component (each attached to the previous). Returns (min, max)."""
    xf = ue.call(A, "get_actor_transform", {"actor": actor})
    yaw = math.radians(xf["rotation"]["yaw"])
    cy, sy = math.cos(yaw), math.sin(yaw)
    asc = xf["scale"]
    # accumulate in actor-local space (component rotations are 0, so only scale + location compose)
    loc = [0.0, 0.0, 0.0]
    sc = [1.0, 1.0, 1.0]
    for n in chain:
        p = props(comp(actor, n), ["relativeLocation", "relativeScale3D"])
        rl, rs = p["relativeLocation"], p["relativeScale3D"]
        for i, k in enumerate("xyz"):
            loc[i] += sc[i] * rl[k]
            sc[i] *= rs[k]
    mesh = props(comp(actor, chain[-1]), ["staticMesh"])["staticMesh"]["refPath"]
    b = ue.call(SM, "get_bounds", {"mesh": {"refPath": mesh}})
    lo = [loc[i] + sc[i] * b["min"][k] for i, k in enumerate("xyz")]
    hi = [loc[i] + sc[i] * b["max"][k] for i, k in enumerate("xyz")]
    pts = []
    for ix in (lo[0], hi[0]):
        for iy in (lo[1], hi[1]):
            for iz in (lo[2], hi[2]):
                x, y, z = ix * asc["x"], iy * asc["y"], iz * asc["z"]
                pts.append((xf["location"]["x"] + cy * x - sy * y, xf["location"]["y"] + sy * x + cy * y, xf["location"]["z"] + z))
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def fmt(v):
    return "(" + ", ".join("%.1f" % x for x in v) + ")"


def bells():
    print("== bells (Bell component world bounds; trace (11800,Y,160)->(12000,Y,120))")
    for label, y in (("Bell_1", 2200), ("Bell_2", 2320), ("Bell_3", 2440), ("Bell_4", 2560)):
        a = bp_swap.find_exact(ue, label)
        lo, hi = world_box(a, ["BellPivot", "Bell"])
        p = props(a, ["symbolIndex", "bellScale", "bandMaterial", "struckTag"])
        g = props(comp(a, "Glyph"), ["text", "worldSize", "textRenderColor"])
        bd = props(comp(a, "Bell"), ["bodyInstance"])["bodyInstance"]
        d = ue.call(S, "trace_world", {"start": {"x": 11800, "y": y, "z": 160}, "end": {"x": 12000, "y": y, "z": 120}})
        hit = None
        if d is not None:
            t = d / math.sqrt(200 ** 2 + 40 ** 2)
            hit = (11800 + 200 * t, y, 160 - 40 * t)
        print("  %s scale %.2f: Bell bounds min %s max %s | top Z %.1f | trace dist %s hit %s | Glyph %r (SymbolIndex %d) | Bell collision %s/%s" % (
            label, p["bellScale"], fmt(lo), fmt(hi), hi[2], d, fmt(hit) if hit else None, g["text"], p["symbolIndex"], bd["collisionProfileName"], bd["collisionEnabled"]))
        inside = hit and lo[0] - 1 <= hit[0] <= hi[0] + 1 and lo[1] - 1 <= hit[1] <= hi[1] + 1 and lo[2] - 1 <= hit[2] <= hi[2] + 1
        print("     trace hit point inside the Bell bounds: %s" % bool(inside))


def inscription():
    print("== inscription")
    a = bp_swap.find_exact(ue, "Clue_Inscription")
    lo, hi = world_box(a, ["Plaque"])
    e = props(comp(a, "Engraving"), ["relativeLocation", "worldSize", "textRenderColor", "text"])
    p = props(comp(a, "Plaque"), ["relativeLocation", "relativeScale3D", "overrideMaterials", "bodyInstance"])
    print("  Plaque world bounds min %s max %s  (expect X 11990-12000, Y 2230-2530, Z 162.5-237.5, +-1)" % (fmt(lo), fmt(hi)))
    print("  Plaque rel loc %s scale %s mats %s collision %s" % (p["relativeLocation"], p["relativeScale3D"], [m["refPath"].split("/")[-1] for m in p["overrideMaterials"]], p["bodyInstance"]["collisionProfileName"]))
    xf = ue.call(A, "get_actor_transform", {"actor": a})
    ex = e["relativeLocation"]["x"]
    print("  Engraving actor-local x = %.2f (need >= 2.1); world X = %.2f (tablet front face world X %.1f); worldSize %s; text %r" % (
        ex, xf["location"]["x"] - ex * xf["scale"]["x"], lo[0], e["worldSize"], e["text"]))


def capstan():
    print("== capstan (Mech_Ritual3)")
    a = bp_swap.find_exact(ue, "Mech_Ritual3")
    b = ue.call(A, "get_actor_bounds", {"actor": a})
    print("  get_actor_bounds: min %s max %s" % (fmt([b["min"][k] for k in "xyz"]), fmt([b["max"][k] for k in "xyz"])))
    lo1, hi1 = world_box(a, ["Pedestal"])
    lo2, hi2 = world_box(a, ["Pedestal", "Core"])
    print("  analytic Pedestal %s..%s  Core %s..%s" % (fmt(lo1), fmt(hi1), fmt(lo2), fmt(hi2)))
    mn, mx = [b["min"][k] for k in "xyz"], [b["max"][k] for k in "xyz"]
    print("  min X %.1f >= 11711 (Patrol_Cloister_04->05 clearance 11609+102): %s (margin %.1f)" % (mn[0], mn[0] >= 11711, mn[0] - 11711))
    print("  distance from AABB max Y %.1f to the tower door leaf (Y 1950): %.1f ; AABB max X %.1f to the door plane X 12020: %.1f" % (mx[1], 1950 - mx[1], mx[0], 12020 - mx[0]))
    r = props(a, ["ritualTag", "requiredTags", "extraGrantedTags", "turnYaw", "turnDuration"])
    print("  values:", json.dumps(r))


if __name__ == "__main__":
    for step in (sys.argv[1:] or ["bells", "inscription", "capstan"]):
        globals()[step]()
