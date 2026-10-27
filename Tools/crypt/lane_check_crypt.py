"""P9-6a lane check for the crypt (editor open on L_Monastery; read-only).

    python lane_check_crypt.py [--out lane_check_p9.md]

1. Every collision-bearing crypt art piece (CA_Pillar_*, CD_SkeletonStake, CD_CageOpen, CD_WinchFrame) must be >= 60 cm (XY AABB distance)
   from every WalkPath segment (SacristyToCrypt, FloodedLedge, CryptToCloister) and >= 150 cm from every crypt AI point (AI/Patrol,
   AI/Search and other AI folders, inside the crypt box).
2. RouteBot approach points of the crank and the winch (actor bounds + 120 cm on the 4 sides, pawn box +-42 cm in XY, Z floor+5..floor+170)
   must not overlap any actor whose collision is not NoCollision/overlap-only.
Appends a section to the markdown file (created if missing). Exit code 1 on any failure of check 1.
"""
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mcp"))
from ue import UE  # noqa: E402

S = "editor_toolset.toolsets.scene.SceneTools"
A = "editor_toolset.toolsets.actor.ActorTools"
O = "editor_toolset.toolsets.object.ObjectTools"
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
BOX = (6150, 11900, -3300, 800)   # crypt XY box
FLOOR = -600.0

u = UE()


def label(a):
    return u.call(A, "get_label", {"actor": a})


def pos(a):
    t = u.call(A, "get_actor_transform", {"actor": a, "worldspace": True})["location"]
    return (t["x"], t["y"], t["z"])


def bounds(a):
    b = u.call(A, "get_actor_bounds", {"actor": a})
    return [b["min"][k] for k in "xyz"], [b["max"][k] for k in "xyz"]


def find_exact(name):
    for a in u.call(S, "find_actors", {"name": name, "tag": "", "collision_channels": []}):
        if label(a) == name:
            return a
    raise RuntimeError("actor not found: " + name)


def folder_points(folder):
    pts = []
    for a in u.call(S, "get_actors_in_folder", {"folder_path": folder, "recursive": True}):
        pts.append((label(a), pos(a)))
    return sorted(pts)


def rect_dist(px, py, mn, mx):
    return math.hypot(max(mn[0] - px, 0, px - mx[0]), max(mn[1] - py, 0, py - mx[1]))


def seg_rect_dist(a, b, mn, mx):
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    n = max(1, int(L / 2))
    best = 1e9
    for s in range(n + 1):
        t = s / n
        best = min(best, rect_dist(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, mn, mx))
    return best


def main():
    out = os.path.join(ROOT, "Docs", "ArtTest", "crypt", "lane_check_p9.md")
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    lines = ["", "## P9-6a lane check (crypt art pieces and RouteBot approaches)", ""]
    ok_all = True

    # ---- 1. collision-bearing pieces vs WalkPaths and AI points
    walk = {}
    for name in ("SacristyToCrypt", "FloodedLedge", "CryptToCloister"):
        walk[name] = [p for _, p in folder_points("WalkPaths/" + name)]
    ai = []
    for fo in ("AI/Patrol", "AI/Search", "AI/Spawn", "AI"):
        try:
            for lbl, p in folder_points(fo):
                if BOX[0] <= p[0] <= BOX[1] and BOX[2] <= p[1] <= BOX[3] and p[2] < -300 and (lbl, p) not in ai:
                    ai.append((lbl, p))
        except Exception:
            pass
    lines += ["WalkPath points: " + ", ".join("%s %d" % (k, len(v)) for k, v in walk.items()) + "; crypt AI points: %d." % len(ai), ""]
    pieces = []
    for pre in ("CA_Pillar_", "CD_SkeletonStake", "CD_CageOpen", "CD_WinchFrame"):
        for a in u.call(S, "find_actors", {"name": pre, "tag": "", "collision_channels": []}):
            l = label(a)
            if l.startswith(pre):
                pieces.append((l,) + tuple(bounds(a)))
    lines += ["| Piece | AABB X | AABB Y | Min dist to WalkPath (cm) | Nearest segment | Min dist to AI point (cm) | Nearest point | Result |",
              "|---|---|---|---|---|---|---|---|"]
    for l, mn, mx in sorted(pieces):
        bw, bn = 1e9, "-"
        for name, pts in walk.items():
            for i in range(len(pts) - 1):
                d = seg_rect_dist(pts[i], pts[i + 1], mn, mx)
                if d < bw:
                    bw, bn = d, "%s %02d-%02d" % (name, i, i + 1)
        ba, an = 1e9, "-"
        for lbl, p in ai:
            d = rect_dist(p[0], p[1], mn, mx)
            if d < ba:
                ba, an = d, lbl
        ok = bw >= 60 and ba >= 150
        ok_all &= ok
        lines.append("| %s | %.0f..%.0f | %.0f..%.0f | %.1f | %s | %.1f | %s | %s |" % (l, mn[0], mx[0], mn[1], mx[1], bw, bn, ba, an,
                                                                                        "PASS" if ok else "FAIL"))
    lines.append("")

    # ---- 2. RouteBot approach points of the crank and winch
    blockers = []
    t0 = time.time()
    for a in u.call(S, "find_actors", {"name": "", "tag": "", "collision_channels": []}):
        try:
            mn, mx = bounds(a)
        except Exception:
            continue
        if mx[0] < BOX[0] or mn[0] > BOX[1] or mx[1] < BOX[2] or mn[1] > BOX[3] or mx[2] < -610 or mn[2] > -420:
            continue
        if max(mx[k] - mn[k] for k in range(3)) > 20000:
            continue
        try:
            c = u.call(A, "get_components", {"actor": a})[0]
            p = u.call(O, "get_properties", {"instance": c, "properties": ["bodyInstance"]})
            p = json.loads(p) if isinstance(p, str) else p
            prof = p["bodyInstance"]["collisionProfileName"]
            en = p["bodyInstance"].get("collisionEnabled")
        except Exception:
            continue
        if prof in ("NoCollision", "OverlapAll", "OverlapAllDynamic", "Trigger") or en == "NoCollision":
            continue
        blockers.append((label(a), mn, mx, prof))
    lines += ["RouteBot approach points (bounds + 120 cm on 4 sides; pawn box +-42 cm XY, Z %.0f..%.0f) against %d collision-bearing actors in the crypt "
              "box (scan %.0f s; first component of each actor)." % (FLOOR + 5, FLOOR + 170, len(blockers), time.time() - t0), "",
              "| Target | Side | Approach point | Overlapping actors | Result |", "|---|---|---|---|---|"]
    for tname in ("Crank_Winch", "Winch_Ritual2"):
        try:
            a = find_exact(tname)
        except Exception:
            lines.append("| %s | - | - | actor not found | FAIL |" % tname)
            ok_all = False
            continue
        mn, mx = bounds(a)
        cx, cy = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2
        for side, pt in (("+X", (mx[0] + 120, cy)), ("-X", (mn[0] - 120, cy)), ("+Y", (cx, mx[1] + 120)), ("-Y", (cx, mn[1] - 120))):
            hit = []
            for l, bmn, bmx, prof in blockers:
                if l == tname:
                    continue
                if (pt[0] + 42 > bmn[0] and pt[0] - 42 < bmx[0] and pt[1] + 42 > bmn[1] and pt[1] - 42 < bmx[1]
                        and FLOOR + 170 > bmn[2] and FLOOR + 5 < bmx[2]):
                    hit.append("%s (%s)" % (l, prof))
            lines.append("| %s (%.0f..%.0f x %.0f..%.0f) | %s | (%.0f, %.0f) | %s | %s |" % (
                tname, mn[0], mx[0], mn[1], mx[1], side, pt[0], pt[1], "; ".join(hit) or "none", "PASS" if not hit else "OVERLAP"))
    lines += ["", "RouteBot tries attempt 0 = in front, 1-2 = the sides, 3 = behind; every OVERLAP row is listed for the lead.", "",
              "**Lane overall (check 1): %s**" % ("PASS" if ok_all else "FAIL"), ""]
    with open(out, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
