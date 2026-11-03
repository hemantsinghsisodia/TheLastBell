"""P11-6: snap the hand-written crack decal list to the walls and check it. Read-only in the editor (trace_world).

    python -I Tools/materials/make_crack_placements.py [--crowns | --leaks]

Writes Tools/materials/p11_crack_decals.json: [{"label", "mi", "location", "rotation", "size", "plane", "note"}].
size = (depth, vertical, horizontal), half-extents in cm, rotation (0, yaw, roll) with roll 90 = texture upright (MCP_NOTES).
Forward = (cos yaw, sin yaw) points into the wall.

Checks for every decal: the centre finds a surface within REACH of the anchor; at least 6 of the 9 probes (centre, corners, edge middles)
hit within the decal's depth, so it lies on a wall and not over a void (entries with a plane skip this); it stays at least KEEP_CM from
every clue, numeral and tablet, and outside the no-go wall zones. Exit 0 when all pass, 1 otherwise.

--crowns prints the height of the first wall above each arch opening instead (the list's Z values come from this).
--leaks checks the wall height behind the six courtyard leak decals.
"""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "Tools", "mcp"))
from ue import UE

S = "editor_toolset.toolsets.scene.SceneTools"
OUT = os.path.join(ROOT, "Tools", "materials", "p11_crack_decals.json")
REACH = 150
KEEP_CM = 200
DEPTH = 12
ue = UE()

# Clues, numerals and tablets: no crack within KEEP_CM of these (decal rectangle to point).
KEEP = {
    "Memorial tablet": (11995, 2380, 200),
    "Bell_1 plaque": (11983, 2200, 90), "Bell_2 plaque": (11983, 2320, 90), "Bell_3 plaque": (11983, 2440, 90), "Bell_4 plaque": (11983, 2560, 90),
    "Stained glass clue": (8750, 747, 300),
    "Chalk sigil altar": (8848, 0, 80), "Chalk sigil wall": (8960, 0, 180), "Chalk tally": (8700, -1500, 140),
    "Altar_Ritual1": (8900, 0, 80),
    "Note_Chains": (10920, -1504, -430), "Note_Gatehouse": (230, -145, 46), "Note_Nave": (7100, 238, 45), "Note_Sacristy": (8300, -1450, 81),
    "Note_Ossuary": (7900, -2150, -540), "Note_Cloister": (10750, 1425, 100),
    "Lever_A": (11040, -1503, -500), "Lever_B": (10920, -1503, -500), "Lever_C": (10800, -1503, -500),
    "Crank_Winch": (8400, -2700, -530), "Winch_Ritual2": (10800, -2000, -550), "Mech_Ritual3": (11790, 1780, 50),
    "Key_Chapel": (1500, -2050, 70),
    "Grave Anselm": (10500, 1600, 100), "Grave Tomas": (10700, 1650, 100), "Grave Edwin": (11000, 2000, 100), "Grave Osric": (11200, 1950, 100),
}
# Whole wall stretches that hold a clue: (axis, plane, tolerance, lo, hi) on the other axis.
NO_GO = [
    ("y", 754, 60, 8000, 9000, "clue bay of the chapel north wall"),
    ("x", 12000, 60, 1950, 2800, "bell wall of the cloister"),
    ("y", -1504, 60, 10600, 11200, "lever wall of the crypt"),
]

# label, MI letter, anchor (x, y, z), yaw, vertical half, horizontal half, roll, why[, plane]
# A and C textures are square, so vertical half = horizontal half. B is 1024x2048, so vertical half = 2 x horizontal half.
# B is thickest at the bottom of the texture: roll 90 starts at an arch crown and climbs; roll 270 starts at the top and runs down.
# plane = where no trace can find the surface: "bounds" (the mesh has no collision, its face comes from get_actor_bounds) or
# "decal" (the same wall plane as an existing crypt decal). Those skip the probes and must be checked in a capture.
L = [
    # Courtyard: arcade crowns, the standing part of the broken bays, curtain wall beside its broken panels, gate and chapel front
    ("Crack_Co_ArcN_Crown",   "C", (2500, 920, 650), 90, 45, 45, 90, "crown of the intact north bay, garth side"),
    ("Crack_Co_ArcS_Crown",   "C", (4500, -920, 650), -90, 45, 45, 270, "crown of the intact south bay, garth side"),
    ("Crack_Co_ArcN_BrokenA", "A", (3170, 920, 630), 90, 70, 70, 90, "standing stub of the north bay 3000"),
    ("Crack_Co_ArcN_BrokenB", "A", (4830, 920, 630), 90, 70, 70, 270, "standing stub of the north bay 4000"),
    ("Crack_Co_ArcS_BrokenA", "A", (2170, -920, 630), -90, 70, 70, 75, "standing stub of the south bay 2000"),
    ("Crack_Co_ArcS_BrokenB", "A", (3830, -920, 630), -90, 70, 70, 255, "standing stub of the south bay 3000"),
    ("Crack_Co_WallN_05",     "B", (2200, 2500, 400), 90, 240, 120, 90, "curtain wall west of the broken panel N_05"),
    ("Crack_Co_WallN_10",     "A", (4840, 2500, 430), 90, 170, 170, 110, "curtain wall east of the broken panel N_10"),
    ("Crack_Co_WallS_03",     "A", (2020, -2500, 430), -90, 170, 170, 75, "curtain wall east of the broken panel S_03"),
    ("Crack_Co_WallS_08",     "B", (3410, -2500, 400), -90, 240, 120, 90, "curtain wall west of the broken panel S_08"),
    ("Crack_Co_GateCrown",    "B", (300, 0, 720), 180, 80, 40, 90, "crown of the gate arch, courtyard side", "bounds"),
    ("Crack_Co_FrontCrown",   "B", (6000, 0, 490), 0, 120, 60, 90, "above the chapel door, outside"),
    # Chapel and sacristy
    ("Crack_Ch_S_HoleW",      "A", (6210, -754, 620), -90, 150, 150, 80, "west of the broken lancet"),
    ("Crack_Ch_S_HoleE",      "B", (6800, -754, 500), -90, 210, 105, 90, "east of the broken lancet"),
    ("Crack_Ch_DoorCrown",    "C", (6056, 0, 440), 180, 60, 60, 90, "above the main door, inside"),
    ("Crack_Ch_N_Base",       "C", (7000, 754, 95), 90, 60, 60, 270, "base of the north wall"),
    ("Crack_Ch_S_Base",       "C", (8000, -754, 95), -90, 60, 60, 90, "base of the south wall"),
    ("Crack_Ch_E_Base",       "C", (8964, -640, 95), 0, 60, 60, 90, "base of the east wall, south corner"),
    ("Crack_Ch_N_High",       "A", (7000, 754, 830), 90, 170, 170, 100, "high on the north wall between the soot marks"),
    ("Crack_Sa_E_Base",       "C", (8964, -1200, 95), 0, 55, 55, 270, "base of the sacristy east wall"),
    # Cloister
    ("Crack_Cl_N_CollapseW",  "A", (10640, 3000, 430), 90, 170, 170, 80, "north wall west of the vault collapse"),
    ("Crack_Cl_N_CollapseE",  "B", (11260, 3000, 400), 90, 230, 115, 90, "north wall east of the vault collapse"),
    ("Crack_Cl_N_Base",       "C", (10150, 3000, 95), 90, 60, 60, 90, "base of the north wall"),
    ("Crack_Cl_W_Base",       "C", (9500, 1000, 95), 180, 60, 60, 270, "base of the west wall"),
    ("Crack_Cl_ArchW_Crown",  "B", (9500, 2000, 560), 180, 120, 60, 90, "crown of the west archway, inside"),
    ("Crack_Cl_ArchS_Crown",  "B", (10650, 546, 455), -90, 120, 60, 90, "crown of the south archway, inside", "bounds"),
    ("Crack_Cl_ArcN_Crown",   "C", (11050, 2205, 585), 90, 40, 40, 90, "arcade arch under the vault collapse, garth side", "bounds"),
    ("Crack_Cl_ArcS_Crown",   "C", (10750, 1395, 585), -90, 40, 40, 270, "south arcade arch, garth side", "bounds"),
    # Crypt: on wall runs that already carry decals (the art walls have no collision; the greybox shell behind them does)
    ("Crack_Cr_WC_W",         "A", (6300, -1750, -400), 180, 120, 120, 80, "west corridor, west wall", "decal"),
    ("Crack_Cr_SC_S",         "A", (6900, -2500, -400), -90, 120, 120, 255, "south corridor, south wall", "decal"),
    ("Crack_Cr_FP_S",         "B", (9360, -2460, -400), -90, 170, 85, 90, "flooded pit, south wall between the leaks", "decal"),
    ("Crack_Cr_FP_N",         "A", (9625, -2100, -400), 90, 110, 110, 100, "flooded pit, north wall between the leaks", "decal"),
    ("Crack_Cr_CC_S",         "A", (10700, -2500, -400), -90, 130, 130, 80, "winch chamber, south wall", "decal"),
    ("Crack_Cr_NC_N",         "C", (11150, -700, -420), 90, 70, 70, 90, "north chamber, north wall", "decal"),
    # Tower: around the broken south-west corner, and two on the shaft
    ("Crack_Tw_SW_A",         "A", (12300, 1540, 2900), -90, 170, 170, 80, "south wall beside the broken corner"),
    ("Crack_Tw_SW_B",         "B", (12040, 1800, 2900), 180, 230, 115, 90, "west wall beside the broken corner"),
    ("Crack_Tw_E_Base",       "C", (12960, 2000, 95), 0, 60, 60, 90, "base of the east wall"),
    ("Crack_Tw_E_Mid",        "A", (12960, 2200, 850), 0, 150, 150, 100, "east wall, lower stair"),
    ("Crack_Tw_N_Mid",        "B", (12500, 2460, 1550), 90, 200, 100, 270, "north wall, upper stair"),
]
LEAKS = {"Decal_Leak_N0": (1300, 2500, 90), "Decal_Leak_N1": (2900, 2500, 90), "Decal_Leak_N2": (5300, 2500, 90),
         "Decal_Leak_S0": (2500, -2500, -90), "Decal_Leak_S1": (4300, -2500, -90), "Decal_Leak_E0": (6000, -1600, 0)}


def trace(a, b):
    r = ue.call(S, "trace_world", {"start": dict(zip("xyz", a)), "end": dict(zip("xyz", b))})
    r = json.loads(r) if isinstance(r, str) and r.strip() else r
    return None if r in (None, "", "null") else float(r)


def basis(yaw):
    f = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw)))
    return f, (-f[1], f[0])


def surface(p, f, reach=REACH):
    """Signed distance from p along f to the first surface, starting reach before p; None if nothing is hit."""
    start = (p[0] - f[0] * reach, p[1] - f[1] * reach, p[2])
    end = (p[0] + f[0] * reach, p[1] + f[1] * reach, p[2])
    d = trace(start, end)
    return None if d is None else d - reach


def dist_rect(pt, c, r, vh, hh):
    dx, dy, dz = pt[0] - c[0], pt[1] - c[1], pt[2] - c[2]
    along = dx * r[0] + dy * r[1]
    normal = math.hypot(dx, dy) ** 2 - along ** 2
    u = max(0.0, abs(along) - hh)
    v = max(0.0, abs(dz) - vh)
    return math.sqrt(max(normal, 0.0) + u * u + v * v)


def crowns():
    """First height with wall in front at the middle of each opening, scanning upward in 20 cm steps."""
    spots = [("Gate", (300, 0), 0), ("FrontDoor", (6000, 0), 0), ("DoorInside", (6056, 0), 180), ("Sacristy", (8036, -1100), 180),
             ("ArcN2000", (2500, 920), 90), ("ArcS4000", (4500, -920), -90), ("ArchW", (9500, 2000), 180), ("ArchS", (10650, 540), -90)]
    for name, xy, yaw in spots:
        f, _ = basis(yaw)
        hits = []
        for k in range(0, 80):
            z = 60 + k * 20
            d = surface((xy[0], xy[1], z), f, 200)
            hits.append((z, None if d is None else round(d)))
        first = next(((z, d) for z, d in hits if d is not None and abs(d) < 120), None)
        last = next(((z, d) for z, d in reversed(hits) if d is not None and abs(d) < 120), None)
        print("%-11s first wall %s  last wall %s" % (name, first, last))


def leaks():
    """The six courtyard leaks move up to start under the coping: the wall must exist from Z 400 to 790 and end before 830."""
    for name, (x, y, yaw) in LEAKS.items():
        f, _ = basis(yaw)
        print("%-15s %s" % (name, " ".join("%d:%s" % (z, surface((x, y, z), f, 80)) for z in (400, 600, 790, 830))))


def main():
    if "--crowns" in sys.argv:
        crowns()
        return 0
    if "--leaks" in sys.argv:
        leaks()
        return 0
    out, bad = [], 0
    for rec in L:
        label, letter, a, yaw, vh, hh, roll, why = rec[:8]
        plane = rec[8] if len(rec) > 8 else ""
        f, r = basis(yaw)
        issues = []
        if plane:
            c, d0, ok = a, 0.0, -1
        else:
            d0 = surface(a, f)
            if d0 is None:
                print("%-24s NO SURFACE" % label)
                bad += 1
                continue
            c = (a[0] + f[0] * d0, a[1] + f[1] * d0, a[2])
            ok = 0
            for du, dv in ((0, 0), (-1, -1), (1, -1), (-1, 1), (1, 1), (0, -1), (0, 1), (-1, 0), (1, 0)):
                p = (c[0] + r[0] * du * hh * 0.85, c[1] + r[1] * du * hh * 0.85, c[2] + dv * vh * 0.85)
                d = surface(p, f, 60)
                if d is not None and abs(d) <= DEPTH:
                    ok += 1
            if ok < 6:
                issues.append("only %d/9 probes on the wall" % ok)
        if letter == "B" and abs(vh - 2 * hh) > 0.01:
            issues.append("B must be 2:1")
        if letter != "B" and vh != hh:
            issues.append("%s must be square" % letter)
        near = sorted((dist_rect(p, c, r, vh, hh), n) for n, p in KEEP.items())[0]
        if near[0] < KEEP_CM:
            issues.append("%d cm from %s" % (near[0], near[1]))
        for axis, pl, tol, lo, hi, why_no in NO_GO:
            at, other = (c[1], c[0]) if axis == "y" else (c[0], c[1])
            if abs(at - pl) <= tol and other + hh > lo and other - hh < hi:
                issues.append("on the %s" % why_no)
        bad += bool(issues)
        print("%-24s %s (%6.0f,%6.0f,%5.0f) d0 %+4.0f probes %-6s nearest %4.0f %-18s %s" % (label, letter, c[0], c[1], c[2], d0, plane or "%d/9" % ok, near[0], near[1], "; ".join(issues)))
        out.append({"label": label, "mi": "MI_Decal_Crack_" + letter,
                    "location": {"x": round(c[0], 1), "y": round(c[1], 1), "z": round(c[2], 1)},
                    "rotation": {"pitch": 0, "yaw": yaw, "roll": roll},
                    "size": {"x": DEPTH, "y": vh, "z": hh}, "plane": plane, "note": why})
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1)
    print("%d decals, %d with issues" % (len(out), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
