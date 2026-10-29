"""P9 amendment D1: crypt layout generator (lead planning data, no editor needed).

Computes every architecture placement for the crypt from the greybox rock faces (Docs/ArtTest/crypt/survey_p9.md)
and the P9-2 kit measurements, checks that no piece intrudes into an open space, and writes:
  Docs/plans/p9_d1_layout.json          placement list for P9-5/P9-6 (world cm, UE rotator [pitch, yaw, roll])
  Docs/plans/p9_d1_tables.md            the same as tables (referenced from P9_CRYPT_ART.md, amendment D1)
  Docs/ArtTest/crypt/d1_layout_plan.svg top-down plan for review

Run from the repo root:  python Tools/crypt/gen_crypt_layout.py
Deterministic (no randomness except seeded tile yaws). Exit code 1 if an intrusion check fails.
"""
import json
import math
import os
import random
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

FLOOR = -600.0
DUNGEON = "/Game/LastBell/ThirdParty/Fab/Dungeon/Meshes/Props/"
CRYPT = "/Game/LastBell/Environments/Crypt/Meshes/"

# ---- P9-2 measurements (mesh-local bounds, cm) ----
MESH_BOUNDS = {
    "SM_Wall_00": ((-320.6, -77.4, -1.3), (320.6, 77.4, 501.7)),
    "SM_Wall_01": ((-320.6, -77.4, -1.3), (320.6, 77.4, 501.7)),
    "SM_Arch": ((-96.2, -81.5, -0.4), (215.2, 73.6, 502.9)),
    "SM_Pillar": ((-62.1, -70.7, -1.3), (88.3, 75.7, 462.7)),
    "SM_Roof": ((-239.1, -239.1, -295.8), (239.1, 239.1, 2.4)),
    "SM_Ground": ((-120.0, -120.0, -20.0), (120.0, 120.0, 20.0)),
    "SM_Dungeon_toplock": ((-36.8, -35.0, 0.4), (36.5, 38.3, 19.9)),
    "SM_Bars": ((-117.9, -4.3, -0.5), (115.1, 4.3, 235.3)),
    "Plane": ((-50.0, -50.0, 0.0), (50.0, 50.0, 0.0)),
    "Cylinder": ((-50.0, -50.0, -50.0), (50.0, 50.0, 50.0)),
    "Cube": ((-50.0, -50.0, -50.0), (50.0, 50.0, 50.0)),
    # P9-3 pieces (design bounds; P9-5 replaces them with the P9-3 report's measured bounds)
    "SM_LB_Crypt_OssuaryBay_500x599": ((-250.0, -90.0, 0.0), (250.0, 6.0, 599.0)),
    "SM_LB_Crypt_Capital_A": ((-85.0, -85.0, 0.0), (85.0, 85.0, 55.0)),
    "SM_LB_Crypt_Stair40_300": ((0.0, -150.0, 0.0), (1200.0, 150.0, 600.0)),
    "SM_LB_Crypt_Beam_35x45x1120": ((-17.5, -560.0, 0.0), (17.5, 560.0, 45.0)),
    "SM_LB_Crypt_Boards_300x250": ((-150.0, -125.0, 0.0), (150.0, 125.0, 5.0)),
    "SM_LB_Crypt_Boards_300x250_Broken": ((-150.0, -125.0, -60.0), (150.0, 125.0, 5.0)),
    "SM_LB_Crypt_Corbel_A": ((-25.0, 0.0, 0.0), (25.0, 55.0, 45.0)),
}
MEASURED_FROM_P93 = []   # filled below once the dressing bounds are registered


def load_p93_bounds():
    """Replace the design bounds of P9-3 pieces with the measured ones (UE space) from props_report_P9.json."""
    path = os.path.join(ROOT, "SourceArt", "Props", "Procedural", "Crypt", "props_report_P9.json")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for rec in json.load(f):
            MESH_BOUNDS[rec["name"]] = (tuple(rec["min"]), tuple(rec["max"]))
            MEASURED_FROM_P93.append(rec["name"])


WALL_LEN, WALL_HALF, WALL_TOP = 641.2, 320.6, 501.7
PITCH, OVL = 626.0, 15.2          # seamless pitch and overlap (P9-2)
D = 75.0                          # wall centre this far into the rock: stone face 0.5 proud .. 11 behind the collision face
WALL_ZS = 1.194                   # wall top at Z -1.0 (just inside the 40 cm ground slab)
EXT, SHORT = 60.0, 30.0           # run end rules: inside corner +60 (hidden in the perpendicular wall); portal -30 (hidden in the leg)
SX_MIN, ANCHOR_SX = 0.72, 0.80
ARCH_JOINT, ARCH_INNER, ARCH_YC, ARCH_FULL = 215.2, -3.4, -3.95, 437.3
ARCH_ZS = 1.19                    # arch top Z -1.5; crown clear 500 (Z -100); springing 345 (Z -255)
ROOF_Z = -44.0                    # vault pivot (crown); shell top -41.6, under the slab (-40)
ROOF = 478.2
CORRIDOR_EXTRA = 178.0            # corridor-style vault: across scale = (width + 178) / 478.2 (P9-2 test geometry)
BAY_PAD = 20.0                    # corridor bays sharing an edge overlap by this much (total)
OS_PAD = 45.0                     # ossuary bays: overlap per side on every shared edge
ROOM_OVERSIZE = 15.0              # room-style vault edges 15 cm into the walls (walls are recessed up to 11 cm)
PILLAR_AXIS = (13.1, 2.5)
CAPITAL_TOP = -330.0              # vault corners at -44 - 295.8 = -339.8 bury in the abacus (-352..-330)
CAPITAL_H = 55.0

# ---- open spaces at floor level (greybox) ----
OPEN = {
    "L": (6300, 6800, -1400, -800),     # landing
    "WC": (6300, 6600, -2500, -1400),   # west corridor (incl. the SW corner)
    "SC": (6600, 7500, -2500, -2200),   # south corridor
    "OS": (7500, 9000, -2900, -2000),   # ossuary
    "FP": (9000, 10000, -2460, -2100),  # flooded passage (pit X 9300-9800, Y -2300..-2100)
    "CC": (10000, 11500, -2500, -1500), # chain chamber
    "LW": (10000, 10300, -1500, -1100), # loop west
    "LE": (11200, 11500, -1500, -1100), # loop east
    "NC": (10000, 11500, -1100, -700),  # north corridor
    "SS": (6800, 8000, -1300, -900),    # sacristy stair
    "ES": (10500, 10800, -700, 500),    # exit stair
}

# ---- wall runs: (id, axis, face, a, b, open_sign, end_a, end_b, mesh, note) ----
# axis 'x': the run goes along X on the face line y = face; open_sign +1 = the open space is on the +Y side.
# axis 'y': along Y on x = face; open_sign +1 = open on +X. Ends: 'corner' (inside corner), 'portal' (convex corner / opening).
RUNS = [
    ("W6300", "y", 6300, -2500, -800, +1, "corner", "corner", "R011 east face: WC west + landing west"),
    ("N_L", "x", -800, 6300, 6800, -1, "corner", "corner", "R012 south face: landing north"),
    ("E_L_S", "y", 6800, -1400, -1300, -1, "corner", "portal", "R007 west face: landing east, south of J2"),
    ("E_L_N", "y", 6800, -900, -800, -1, "portal", "corner", "R010 west face: landing east, north of J2"),
    ("S_L", "x", -1400, 6600, 6800, +1, "portal", "corner", "R006 north face: landing south, east of J1"),
    ("E_WC", "y", 6600, -2200, -1400, -1, "portal", "portal", "R004/R006 west face: WC east"),
    ("S_WCSC", "x", -2500, 6300, 7500, +1, "corner", "portal", "R002 north face: SW corner + SC south"),
    ("N_SC", "x", -2200, 6600, 7500, -1, "portal", "portal", "R004 south face: SC north"),
    ("W_OS_S", "y", 7500, -2900, -2500, +1, "corner", "portal", "R002 east face: ossuary west, south of J4"),
    ("W_OS_N", "y", 7500, -2200, -2000, +1, "portal", "corner", "R004 east face: ossuary west, north of J4"),
    ("E_OS_S", "y", 9000, -2900, -2460, -1, "corner", "portal", "R001/R003 west face: ossuary east, south of J5"),
    ("E_OS_N", "y", 9000, -2100, -2000, -1, "portal", "corner", "R005 west face: ossuary east, north of J5"),
    ("S_FP", "x", -2460, 9000, 10000, +1, "portal", "portal", "R003 north face: flooded passage south (ledge side)"),
    ("N_FP", "x", -2100, 9000, 10000, -1, "portal", "portal", "R005 south face: flooded passage north (pit side)"),
    ("W_CC_S", "y", 10000, -2500, -2460, +1, "corner", "portal", "R003 east face: chain chamber west, south of J6"),
    ("W_CC", "y", 10000, -2100, -700, +1, "portal", "corner", "R005..R012 east faces: CC west + LW west + NC west"),
    ("S_CC", "x", -2500, 10000, 11500, +1, "corner", "corner", "R001 north face: chain chamber south"),
    ("E_CC", "y", 11500, -2500, -700, -1, "corner", "corner", "R013 west face: CC east + LE east + NC east"),
    ("N_CC", "x", -1500, 10300, 11200, -1, "portal", "portal", "R008 south face: PUZZLE WALL (levers, clue plaque)"),
    ("R008_W", "y", 10300, -1500, -1100, -1, "portal", "portal", "R008 west face: LW east"),
    ("R008_E", "y", 11200, -1500, -1100, +1, "portal", "portal", "R008 east face: LE west"),
    ("S_NC", "x", -1100, 10300, 11200, +1, "portal", "portal", "R008 north face: NC south"),
    ("N_NC_W", "x", -700, 10000, 10500, -1, "corner", "portal", "R014 south face: NC north, west of J11"),
    ("N_NC_E", "x", -700, 10800, 11500, -1, "portal", "corner", "R015 south face: NC north, east of J11"),
    ("W_ES", "y", 10500, -700, 500, +1, "portal", "corner", "R014 east face: exit stair west"),
    ("E_ES", "y", 10800, -700, 500, -1, "portal", "corner", "R015 west face: exit stair east"),
    ("S_SS", "x", -1300, 6800, 8000, +1, "portal", "corner", "R007 north face: sacristy stair south"),
    ("N_SS", "x", -900, 6800, 8000, -1, "portal", "corner", "R010 south face: sacristy stair north"),
]
# Pit walls: sunk (base Z -1100, Z scale 1.0, top -598.3, hidden under the water planes below -593)
PIT_RUNS = [
    ("PIT_N", "x", -2100, 9300, 9800, -1, "corner", "corner", "pit north (Pit_N face)"),
    ("PIT_S", "x", -2300, 9300, 9800, +1, "corner", "corner", "pit south = ledge edge (Pit_S face)"),
    ("PIT_W", "y", 9300, -2300, -2100, +1, "corner", "corner", "pit west (Pit_W face)"),
    ("PIT_E", "y", 9800, -2300, -2100, -1, "corner", "corner", "pit east (Pit_E face)"),
]
# Wall_01 (built-in candle niche on local +Y: x -140..+60, z 110..270, 25 deep) replaces Wall_00 on these pieces:
CANDLE_NICHE_PIECES = {("E_WC", 0), ("N_SC", 0), ("S_FP", 1), ("S_NC", 0), ("E_CC", 1)}

# ---- portals: (id, axis of the opening, plane, o1, o2, rock_sign, note) ----
# axis 'x': the opening spans X on the plane y = plane; rock_sign = side the coplanar walls' rock is on (+1 = +Y).
PORTALS = [
    ("J1", "x", -1400, 6300, 6600, -1, "WC <-> landing"),
    ("J2", "y", 6800, -1300, -900, +1, "landing <-> sacristy stair"),
    ("J3", "y", 6600, -2500, -2200, +1, "WC <-> south corridor"),
    ("J4", "y", 7500, -2500, -2200, -1, "south corridor <-> ossuary"),
    ("J5", "y", 9000, -2460, -2100, +1, "ossuary <-> flooded passage"),
    ("J6", "y", 10000, -2460, -2100, -1, "flooded passage <-> chain chamber"),
    ("J7", "x", -1500, 10000, 10300, +1, "chain chamber <-> loop west"),
    ("J8", "x", -1500, 11200, 11500, +1, "chain chamber <-> loop east"),
    ("J9", "x", -1100, 10000, 10300, -1, "loop west <-> north corridor"),
    ("J10", "x", -1100, 11200, 11500, -1, "loop east <-> north corridor"),
    ("J11", "x", -700, 10500, 10800, +1, "north corridor <-> exit stair (Gate_CryptExit inside)"),
]

# ---- UE rotator -> matrix rows (FRotationMatrix) ----
def rot_rows(p, y, r):
    P, Y, R = (math.radians(v) for v in (p, y, r))
    SP, CP, SY, CY, SR, CR = math.sin(P), math.cos(P), math.sin(Y), math.cos(Y), math.sin(R), math.cos(R)
    return [
        (CP * CY, CP * SY, SP),
        (SR * SP * CY - CR * SY, SR * SP * SY + CR * CY, -SR * CP),
        (-(CR * SP * CY + SR * SY), CY * SR - CR * SP * SY, CR * CP),
    ]


def world_aabb(mesh, loc, rot, scale):
    if mesh not in MESH_BOUNDS:          # pivot-only entries (bounds not measured yet): P9-6a reads them back
        return [round(v, 1) for v in loc], [round(v, 1) for v in loc]
    lo, hi = MESH_BOUNDS[mesh]
    rows = rot_rows(*rot)
    pts = []
    for cx in (lo[0], hi[0]):
        for cy in (lo[1], hi[1]):
            for cz in (lo[2], hi[2]):
                v = (cx * scale[0], cy * scale[1], cz * scale[2])
                w = [loc[k] + v[0] * rows[0][k] + v[1] * rows[1][k] + v[2] * rows[2][k] for k in range(3)]
                pts.append(w)
    mn = [round(min(p[k] for p in pts), 1) for k in range(3)]
    mx = [round(max(p[k] for p in pts), 1) for k in range(3)]
    return mn, mx


def rnd(v, n=2):
    return [round(x, n) for x in v]


placements = []   # dicts: id, cat, mesh, loc, rot, scale, collision, folder, aabb, note
issues = []


def add(pid, cat, mesh, path, loc, rot, scale, collision, folder, note="", check=True, extra=None):
    mn, mx = world_aabb(mesh, loc, rot, scale)
    d = {"id": pid, "cat": cat, "mesh": path + mesh if path else mesh, "loc": rnd(loc), "rot": rnd(rot, 3),
         "scale": rnd(scale, 4), "collision": collision, "folder": folder, "aabb_min": mn, "aabb_max": mx,
         "note": note}
    if extra:
        d.update(extra)
    if cat in ("dress", "lining") and mesh in MESH_BOUNDS:
        # mesh-local bounds: place_crypt.py recomputes the expected world AABB from them and the FINAL rotation (skull facing offsets)
        d["mbounds"] = [list(MESH_BOUNDS[mesh][0]), list(MESH_BOUNDS[mesh][1])]
    placements.append(d)
    return d


load_p93_bounds()

# ---- walls ----
def run_layout(run, zbase, zs, prefix):
    rid, axis, face, a, b, s, ea, eb, note = run
    a2 = a - EXT if ea == "corner" else a + SHORT
    b2 = b + EXT if eb == "corner" else b - SHORT
    L = b2 - a2
    best = None
    for n in {max(1, math.floor(L / PITCH)), max(1, math.ceil(L / PITCH))}:
        sx = (L / n + OVL) / WALL_LEN
        if best is None or abs(math.log(sx)) < abs(math.log(best[1])):
            best = (n, sx)
    n, sx = best
    spans = []
    mode = "pitched"
    if sx < SX_MIN and n == 1:
        length = ANCHOR_SX * WALL_LEN
        if ea == "portal" and eb == "corner":
            lo = a2 - OVL / 2
            spans = [(lo + length / 2, ANCHOR_SX)]
            mode = "anchored at a"
        elif ea == "corner" and eb == "portal":
            hi = b2 + OVL / 2
            spans = [(hi - length / 2, ANCHOR_SX)]
            mode = "anchored at b"
        elif ea == "corner" and eb == "corner":
            spans = [((a2 + b2) / 2, ANCHOR_SX)]
            mode = "centred"
        else:
            spans = [((a2 + b2) / 2, sx)]
            mode = "squashed (both ends at portals)"
    else:
        p = L / n
        spans = [(a2 + p * (i + 0.5), sx) for i in range(n)]
    perp = face - s * D
    if axis == "x":
        yaw = 0.0 if s > 0 else 180.0
    else:
        yaw = -90.0 if s > 0 else 90.0
    out = []
    for i, (c, sxi) in enumerate(spans):
        mesh = "SM_Wall_01" if (rid, i) in CANDLE_NICHE_PIECES else "SM_Wall_00"
        loc = (c, perp, zbase) if axis == "x" else (perp, c, zbase)
        d = add(f"{prefix}_{rid}_{i}", "wall", mesh, DUNGEON, loc, (0.0, yaw, 0.0), (sxi, 1.0, zs), "NoCollision",
                "Crypt/Art/Walls", note=f"{note}; run {a}..{b} ({ea}/{eb}); {mode}",
                extra={"run": rid, "piece": i})
        if mesh == "SM_Wall_01":
            # niche centre: local (-40, +69 face, 190) -> world; base z 110, top 270, 25 deep behind the face
            rows = rot_rows(0.0, yaw, 0.0)
            v = (-40.0 * sxi, 0.0)
            wx = loc[0] + v[0] * rows[0][0] + v[1] * rows[1][0]
            wy = loc[1] + v[0] * rows[0][1] + v[1] * rows[1][1]
            d["niche"] = {"centre_xy_on_face": rnd([wx if axis == "x" else face, wy if axis == "x" else wy]),
                          "base_z": round(zbase + 110 * zs, 1), "top_z": round(zbase + 270 * zs, 1),
                          "width": round(200 * sxi, 1), "depth_behind_face": 25 - 0}
            if axis == "y":
                d["niche"]["centre_xy_on_face"] = rnd([face, wy])
        out.append(d)
    return out


for run in RUNS:
    run_layout(run, FLOOR, WALL_ZS, "CA_Wall")
for run in PIT_RUNS:
    for d in run_layout(run, -1100.0, 1.0, "CA_PitWall"):
        d["cat"] = "pitwall"
        d["folder"] = "Crypt/Art/Walls/Pit"

# ---- portals ----
for pid, axis, plane, o1, o2, r, note in PORTALS:
    w = o2 - o1
    sx = w / ARCH_FULL
    c = (o1 + o2) / 2
    depth_c = plane + r * D
    for side, sgn in (("L", +1), ("R", -1)):
        along = c - sgn * ARCH_JOINT * sx
        if axis == "x":
            loc = (along, depth_c - ARCH_YC, FLOOR)
            yaw = 0.0
        else:
            loc = (depth_c + ARCH_YC, along, FLOOR)
            yaw = 90.0
        add(f"CA_Portal_{pid}_{side}", "portal", "SM_Arch", DUNGEON, loc, (0.0, yaw, 0.0), (sgn * sx, 1.0, ARCH_ZS),
            "NoCollision", "Crypt/Art/Portals",
            note=f"{note}; opening {o1}..{o2} ({w} wide), clear crown Z -100, springing Z -255; legs {round(91.6 * sx, 1)} wide",
            extra={"portal": pid})

# ---- vaults ----
VAULTS = []
# corridor style: across = (width + 178)/478.2, along = pitch/478.2
def corridor(vid, axis, a, b, centre, width):
    L = b - a
    n = max(1, round(L / ROOF))
    p = L / n
    for i in range(n):
        c = a + p * (i + 0.5)
        # P9-5 gap pass: bays that share an edge overlap by BAY_PAD (hairline slits at the crown seams)
        pa = p + BAY_PAD * ((i > 0) + (i < n - 1))
        c2 = c + BAY_PAD * 0.5 * ((i < n - 1) - (i > 0))
        if axis == "x":
            VAULTS.append((f"{vid}_{i}", (c2, centre), (pa / ROOF, (width + CORRIDOR_EXTRA) / ROOF), "corridor"))
        else:
            VAULTS.append((f"{vid}_{i}", (centre, c2), ((width + CORRIDOR_EXTRA) / ROOF, pa / ROOF), "corridor"))

corridor("WC", "y", -2515, -1400, 6450, 300)
corridor("SC", "x", 6600, 7500, -2350, 300)
corridor("FP", "x", 9000, 10000, -2280, 360)
corridor("LW", "y", -1500, -1100, 10150, 300)
corridor("LE", "y", -1500, -1100, 11350, 300)
corridor("NC", "x", 9985, 11515, -900, 400)
# room style: bays end 15 cm into the walls
VAULTS.append(("L_0", (6550, -1100), (530 / ROOF, 630 / ROOF), "room"))
OS_X = [7485, 8000, 8500, 9015]
OS_Y = [-2915, -2510, -1985]
for j in range(2):
    for i in range(3):
        x0, x1, y0, y1 = OS_X[i], OS_X[i + 1], OS_Y[j], OS_Y[j + 1]
        # P9-5 gap pass: the room bays' corners lean inward, leaving a wedge/disc hole over each pier and along the shared
        # edges. Every shared edge overlaps by OS_PAD per side (the displaced corners at Z -339.8 stay inside the abacus).
        if i > 0:
            x0 -= OS_PAD
        if i < 2:
            x1 += OS_PAD
        if j == 0:
            y1 += OS_PAD
        else:
            y0 -= OS_PAD
        VAULTS.append((f"OS_{j}{i}", ((x0 + x1) / 2, (y0 + y1) / 2), ((x1 - x0) / ROOF, (y1 - y0) / ROOF), "room"))
for vid, (x, y), (sx, sy), style in VAULTS:
    add(f"CA_Vault_{vid}", "vault", "SM_Roof", DUNGEON, (x, y, ROOF_Z), (0.0, 0.0, 0.0), (sx, sy, 1.0), "NoCollision",
        "Crypt/Art/Vaults", note=f"{style} style", check=False)

# ---- columns (ossuary) ----
COLUMNS = [("Free_8000", 8000, -2510, "free"), ("Free_8500", 8500, -2510, "free"),
           ("S_8000", 8000, -2900, "engaged"), ("S_8500", 8500, -2900, "engaged"),
           ("N_8000", 8000, -2000, "engaged"), ("N_8500", 8500, -2000, "engaged")]
for cid, x, y, kind in COLUMNS:
    ptop = CAPITAL_TOP - CAPITAL_H
    add(f"CA_Pillar_{cid}", "column", "SM_Pillar", DUNGEON, (x - PILLAR_AXIS[0], y - PILLAR_AXIS[1], ptop - 462.7),
        (0.0, 0.0, 0.0), (1.0, 1.0, 1.0), "BlockAll (mesh hull)", "Crypt/Art/Columns",
        note=f"{kind}; axis ({x}, {y}); top {ptop}, sunk {round(FLOOR - (ptop - 462.7 - 1.3), 1)} cm below the floor", check=False)
    add(f"CA_Capital_{cid}", "column", "SM_LB_Crypt_Capital_A", CRYPT, (x, y, ptop), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0),
        "NoCollision", "Crypt/Art/Columns", note=f"{kind}; abacus top {CAPITAL_TOP}", check=False)

# ---- ossuary niche bays ----
for wall, yface, yaw in (("S", -2900, 0.0), ("N", -2000, 180.0)):
    for i, (x0, x1) in enumerate(((7485, 8000), (8000, 8500), (8500, 9015))):
        add(f"CA_Ossuary_{wall}{i}", "ossuary", "SM_LB_Crypt_OssuaryBay_500x599", CRYPT, ((x0 + x1) / 2, yface, FLOOR),
            (0.0, yaw, 0.0), ((x1 - x0) / 500.0, 1.0, 1.0), "NoCollision", "Crypt/Art/Ossuary",
            note="front face on the collision face line; niches open into the room", check=False)

# ---- floor tiles: global 200 grid, centres on odd hundreds, surface Z -600 ----
# P9-6a R2 step B: every tile yaw 0 (the "rail" lines persisted: they are the border strip of the cobble texture, one per texture repeat)
TILE_SPACES = {"L": (0,), "WC": (0,), "SC": (0,), "OS": (0,), "CC": (0,), "LW": (0,), "LE": (0,), "NC": (0,)}
rng = random.Random(9)
tiles = {}
TILE_MARGIN = 15.0   # P9-5 gap pass: tiles must reach under the recessed wall stone (0.5-11 cm behind the face line)
for sp, yaws in TILE_SPACES.items():
    x0, x1, y0, y1 = OPEN[sp]
    x0, x1, y0, y1 = x0 - TILE_MARGIN, x1 + TILE_MARGIN, y0 - TILE_MARGIN, y1 + TILE_MARGIN
    xs = range(int(math.floor((x0 - 100) / 200.0)), int(math.ceil((x1 - 100) / 200.0)) + 1)
    ys = range(int(math.floor((y0 - 100) / 200.0)), int(math.ceil((y1 - 100) / 200.0)) + 1)
    for i in xs:
        for j in ys:
            cx, cy = 100 + 200 * i, 100 + 200 * j
            ox = min(cx + 100, x1) - max(cx - 100, x0)
            oy = min(cy + 100, y1) - max(cy - 100, y0)
            fx0, fx1, fy0, fy1 = OPEN["FP"]   # no tiles under the flood water: displaced cobbles (MI_Tiles WPO, up to 12 cm) would pierce it
            in_fp = (min(cx + 100, fx1) - max(cx - 100, fx0)) > 20 and (min(cy + 100, fy1) - max(cy - 100, fy0)) > 20
            if ox > 0.5 and oy > 0.5 and (cx, cy) not in tiles and not in_fp:
                tiles[(cx, cy)] = (sp, yaws)
for (cx, cy), (sp, yaws) in sorted(tiles.items()):
    yaw = float(yaws[rng.randrange(len(yaws))])
    add(f"CA_Tile_{sp}_{cx}_{cy}".replace("-", "m"), "tile", "SM_Ground", DUNGEON, (cx, cy, FLOOR), (0.0, yaw, 0.0),
        (1.0, 1.0, 1.0), "NoCollision", "Crypt/Art/Floor", check=False)

# ---- stair flights ----
add("CA_Stair_Sacristy", "stair", "SM_LB_Crypt_Stair40_300", CRYPT, (6800, -1100, FLOOR), (0.0, 0.0, 0.0),
    (1.0, 400 / 300.0, 1.0), "NoCollision", "Crypt/Art/Stairs",
    note="treads match Stair_SacristyDown_00..39 (step n: X 6800+30n..6830+30n, top -600+15(n+1))", check=False)
add("CA_Stair_Exit", "stair", "SM_LB_Crypt_Stair40_300", CRYPT, (10650, -700, FLOOR), (0.0, 90.0, 0.0),
    (1.0, 1.0, 1.0), "NoCollision", "Crypt/Art/Stairs",
    note="treads match Stair_CryptUp_00..39 (step n: Y -700+30n..-670+30n)", check=False)

# ---- flat ashlar soffits over the stair runs under the slab (SM_Wall_00 laid face-down, roll 90) ----
# roll 90: local +Y -> world -Z (a finished face points down), local Z (height) -> world +Y (yaw 0) or -X (yaw 90);
# Y scale 0.25 -> 38.7 thick: lowest point Z -44.0, top Z -5.3 (pivot Z -24.65), under the slab top (0)
SOFFIT_Z = -24.65
add("CA_Soffit_Sacristy", "soffit", "SM_Wall_00", DUNGEON, (7115, -1360 + 1.3 * 520 / 503.0, SOFFIT_Z), (0.0, 0.0, 90.0),
    (570 / WALL_LEN, 0.25, 520 / 503.0), "NoCollision", "Crypt/Art/Ceiling",
    note="covers X 6830..7400 (slab Ground_0 ends at 7400; the shaft above X 7400-8000 stays open), Y -1360..-840", check=False)
add("CA_Soffit_Exit", "soffit", "SM_Wall_00", DUNGEON, (10860 - 1.3 * 420 / 503.0, -385, SOFFIT_Z), (0.0, 90.0, 90.0),
    (570 / WALL_LEN, 0.25, 420 / 503.0), "NoCollision", "Crypt/Art/Ceiling",
    note="covers Y -670..-100 (Ground_3 ends at -100; the shaft above Y -100..500 stays open), X 10440..10860", check=False)

# stone lintels where the soffits meet the open stair shafts (hide the soffit's ragged end and the slab edge face)
if "SM_LB_Crypt_Block_100" not in MEASURED_FROM_P93:
    MESH_BOUNDS["SM_LB_Crypt_Block_100"] = ((-50.0, -50.0, 0.0), (50.0, 50.0, 100.0))
add("CA_Lintel_Sacristy", "soffit", "SM_LB_Crypt_Block_100", CRYPT, (7375, -1100, -45), (0.0, 0.0, 0.0), (0.5, 4.2, 0.44),
    "NoCollision", "Crypt/Art/Ceiling", note="X 7350..7400, Z -45..-1: frames the shaft end under Ground_0's edge", check=False)
add("CA_Lintel_Exit", "soffit", "SM_LB_Crypt_Block_100", CRYPT, (10650, -125, -45), (0.0, 0.0, 0.0), (3.2, 0.5, 0.44),
    "NoCollision", "Crypt/Art/Ceiling", note="Y -150..-100, Z -45..-1: frames the shaft end under Ground_3's edge", check=False)

# ---- P9-6a R4: lining of the greybox slab side faces at the stair-shaft openings ----
# The 40 cm slab faces (Z -40..0) stand 0.5-11 cm proud of the recessed wall stone, so the lit white greybox faces cover the top 40 cm of the
# walls above the open stair shafts (confirmed with ScreenCoordsToWorld from SS1 and ES1: planes y -1300 / y -900 / x 10500 / x 10800).
# Block_100 (pivot bottom-centre): scale along the face = length/100 + 0.04, 0.03 across (3 cm, back on the slab face), Z = (40 + 2)/100;
# top at Z -0.5 (pivot Z -42.5).
LINING = [("Ground_5", "Ym1300", "x", 7700.0, -1300.0, +1, 600.0, "Ground_5 face y -1300 (X 7400..8000), shaft on +Y"),
          ("Ground_6", "Ym900", "x", 7700.0, -900.0, -1, 600.0, "Ground_6 face y -900 (X 7400..8000), shaft on -Y"),
          ("Ground_1", "X10500", "y", 200.0, 10500.0, +1, 600.0, "Ground_1 face x 10500 (Y -100..500), shaft on +X"),
          ("Ground_2", "X10800", "y", 200.0, 10800.0, -1, 600.0, "Ground_2 face x 10800 (Y -100..500), shaft on -X")]
for slab, fid, axis, along, face, s_open, length, note in LINING:
    sc_along, sc_across, sc_z = length / 100.0 + 0.04, 0.03, (40.0 + 2.0) / 100.0
    centre_across = face + s_open * 1.5
    loc = (along, centre_across, -42.5) if axis == "x" else (centre_across, along, -42.5)
    sc = (sc_along, sc_across, sc_z) if axis == "x" else (sc_across, sc_along, sc_z)
    add(f"CA_Lining_{slab}_{fid}", "lining", "SM_LB_Crypt_Block_100", CRYPT, loc, (0.0, 0.0, 0.0), sc, "NoCollision",
        "Crypt/Art/Lining", note=note + "; 3 cm lining, Z -42.5..-0.5", check=False)

# ---- P9-6a F1: stone parapet enclosures around the white greybox railings at the stair-shaft openings ----
# The Rail_* StaticMeshActors (gameplay-adjacent greybox: BlockAll, never moved or changed) show as white strips from the stairs.
# Each enclosure is a NoCollision Block_100 (MI_Crypt_StoneWA, pivot bottom-centre) = the rail's world AABB + 2 cm on each side and on top,
# sunk 1 cm: loc = (cx, cy, minZ - 1), scale = ((dx + 4)/100, (dy + 4)/100, (dz + 3)/100). AABBs read from the editor (all yaw 0).
RAILS = {"Rail_Sac_S": ((7400.0, -1310.0, 0.0), (8000.0, -1300.0, 100.0)),
         "Rail_Sac_N": ((7400.0, -900.0, 0.0), (8000.0, -890.0, 100.0)),
         "Rail_Up_W": ((10490.0, -110.0, 0.0), (10500.0, 500.0, 100.0)),
         "Rail_Up_E": ((10800.0, -110.0, 0.0), (10810.0, 500.0, 100.0)),
         # P9-R1A step 1: the two rails F1 missed (AABBs read from the editor, yaw 0)
         "Rail_Sac_W": ((7390.0, -1310.0, 0.0), (7400.0, -890.0, 100.0)),
         "Rail_Up_S": ((10500.0, -110.0, 0.0), (10800.0, -100.0, 100.0))}
for rname, (rmn, rmx) in RAILS.items():
    add(f"CA_Parapet_{rname}", "lining", "SM_LB_Crypt_Block_100", CRYPT,
        ((rmn[0] + rmx[0]) / 2, (rmn[1] + rmx[1]) / 2, rmn[2] - 1.0), (0.0, 0.0, 0.0),
        ((rmx[0] - rmn[0] + 4) / 100.0, (rmx[1] - rmn[1] + 4) / 100.0, (rmx[2] - rmn[2] + 3) / 100.0), "NoCollision",
        "Crypt/Art/Lining", note=f"stone enclosure of {rname}: AABB +2 cm each side and on top, sunk 1 cm (F1)", check=False)

# ---- P9-R1C step 8: lining of Ground_3's shaft-side end face (white greybox band under the Rail_Up_S parapet, seen in r1_rail_up_s) ----
# Ground_3 AABB (read from the editor): X 10500..10800, Y -3600..-100, Z -40..0; the end face y -100 faces the open shaft (+Y).
# CA_Lintel_Exit (X 10490..10810, Y -150..-100, Z -45..-1) is on the crypt side of that plane, so it does not cover the face.
# 4 cm proud on the shaft side (Y -100..-96), X exactly the slab's (10500..10800), Z from 1 cm below the slab to 1 cm above its top.
add("CA_Lining_Ground3_End", "lining", "SM_LB_Crypt_Block_100", CRYPT, (10650.0, -98.0, -41.0), (0.0, 0.0, 0.0), (3.0, 0.04, 0.42), "NoCollision",
    "Crypt/Art/Lining", note="Ground_3 end face y -100 (X 10500..10800, Z -40..0), shaft on +Y; 4 cm lining Y -100..-96, Z -41..1 (R1-C step 8)", check=False)

# ---- chain chamber timber ceiling ----
BEAM_X =[10300, 10600, 10900, 11200]
for i, bx in enumerate(BEAM_X):
    add(f"CA_CC_Beam_{i}", "ceiling", "SM_LB_Crypt_Beam_35x45x1120", CRYPT, (bx, -2000, -95), (0.0, 0.0, 0.0),
        (1.0, 1.0, 1.0), "NoCollision", "Crypt/Art/Ceiling/ChainChamber", note="Y -2560..-1440, Z -95..-50", check=False)
CORBELS = [(bx, -2500, 0.0) for bx in BEAM_X] + [(10600, -1500, 180.0), (10900, -1500, 180.0)]
for i, (x, y, yaw) in enumerate(CORBELS):
    add(f"CA_CC_Corbel_{i}", "ceiling", "SM_LB_Crypt_Corbel_A", CRYPT, (x, y, -140), (0.0, yaw, 0.0), (1.0, 1.0, 1.0),
        "NoCollision", "Crypt/Art/Ceiling/ChainChamber", note="back plane on the face line, top Z -95 under the beam end", check=False)
BROKEN = {(1, 0), (3, 1), (0, 2)}
GRATE_CELL = (3, 3)
for col in range(5):
    for row in range(4):
        cx, cy = 10150 + 300 * col, -2375 + 250 * row
        if (col, row) == GRATE_CELL:
            continue
        mesh = "SM_LB_Crypt_Boards_300x250_Broken" if (col, row) in BROKEN else "SM_LB_Crypt_Boards_300x250"
        add(f"CA_CC_Boards_{col}{row}", "ceiling", mesh, CRYPT, (cx, cy, -50), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0),
            "NoCollision", "Crypt/Art/Ceiling/ChainChamber", note="boards run along X between beams; Z -50..-45", check=False)
add("CA_CC_Soil", "ceiling", "Plane", "/Engine/BasicShapes/", (10750, -2000, -41), (0.0, 0.0, 180.0), (15.3, 10.3, 1.0),
    "NoCollision", "Crypt/Art/Ceiling/ChainChamber", note="MI_Crypt_Soil; roll 180 so the visible face points down (the plane is one-sided); seen through board gaps and broken boards", check=False)
gx, gy = 10150 + 300 * GRATE_CELL[0], -2375 + 250 * GRATE_CELL[1]
add("CA_CC_Grate", "grate", "SM_Bars", DUNGEON, (gx, gy - 121.5, -55), (0.0, 0.0, 90.0), (1.25, 1.0, 1.03), "NoCollision",
    "Crypt/Art/Ceiling/ChainChamber", note=f"moon grate G3 in cell {GRATE_CELL}: X {gx - 150}..{gx + 150}, Y {gy - 125}..{gy + 125}; laid flat (roll 90)", check=False)
add("CA_CC_GrateSky", "grate", "Plane", "/Engine/BasicShapes/", (gx, gy, -43), (0.0, 0.0, 0.0), (3.0, 2.5, 1.0),
    "NoCollision", "Crypt/Art/Ceiling/ChainChamber", note="MI_Crypt_MoonSky (unlit night sky seen through the grate)", check=False)

# ---- vault moon grates (toplock collar hung upside down from the vault crown) ----
for gid, (x, y) in (("G1", (8250, -2247.5)), ("G2", (9750, -2280))):
    add(f"CA_Grate_{gid}", "grate", "SM_Dungeon_toplock", DUNGEON, (x, y, -42), (0.0, 0.0, 180.0), (1.0, 1.0, 1.0),
        "NoCollision", "Crypt/Art/Grates", note="roll 180: collar hangs Z -42..-62, grating faces down", check=False)
    add(f"CA_GrateSky_{gid}", "grate", "Cylinder", "/Engine/BasicShapes/", (x, y, -45), (0.0, 0.0, 0.0), (0.6, 0.6, 0.005),
        "NoCollision", "Crypt/Art/Grates", note="MI_Crypt_MoonSky disc inside the collar, above the grating", check=False)

# ---- water planes (engine Plane 100x100, pivot centre, UV 0..1) ----
WATER = [
    ("CA_Water_W", (8800, 9295, -2475, -2085), -593.0, "MI_Crypt_Water_Flood_W", {"EdgeFadeXMinCm": 200}),
    ("CA_Water_Ledge", (9295, 9805, -2475, -2302), -593.0, "MI_Crypt_Water_Flood_Ledge", {}),
    ("CA_Water_E", (9805, 10200, -2475, -2085), -593.0, "MI_Crypt_Water_Flood_E", {"EdgeFadeXMaxCm": 200}),
    ("CA_Water_Pit", (9285, 9815, -2315, -2085), -650.0, "MI_Crypt_Water_Pit", {}),
]
for wid, (x0, x1, y0, y1), z, mi, fades in WATER:
    add(wid, "water", "Plane", "/Engine/BasicShapes/", ((x0 + x1) / 2, (y0 + y1) / 2, z), (0.0, 0.0, 0.0),
        ((x1 - x0) / 100.0, (y1 - y0) / 100.0, 1.0), "NoCollision", "Crypt/Art/Water",
        note=f"{mi}; SizeXCm {x1 - x0}, SizeYCm {y1 - y0}; fades {fades or 'none'}", check=False,
        extra={"mi": mi, "size_cm": [x1 - x0, y1 - y0], "fades": fades})

# ---- backdrop safety box (5 thin unlit-black slabs, no top) ----
BACK = [("Bottom", (9000, -1250, -1105), (58.2, 41.2, 0.1)),
        ("West", (6095, -1250, -570), (0.1, 41.2, 10.6)),
        ("East", (11905, -1250, -570), (0.1, 41.2, 10.6)),
        ("South", (9000, -3305, -570), (58.2, 0.1, 10.6)),
        ("North", (9000, 805, -570), (58.2, 0.1, 10.6))]
for bid, loc, sc in BACK:
    add(f"CA_Backdrop_{bid}", "backdrop", "Cube", "/Engine/BasicShapes/", loc, (0.0, 0.0, 0.0), sc, "NoCollision",
        "Crypt/Art/Backdrop", note="MI_Crypt_Backdrop (unlit black); CastShadow off", check=False)


# =====================================================================================================
# DRESSING (P9-6a) and LIGHTS (P9-7). Category "dress" / "decal" / "light". Positions are exact; meshes whose
# facing axis is unknown carry a 'face_yaw' (the world yaw the visible front must face); P9-6a measures each mesh's
# facing offset once (capture) and sets actor yaw = face_yaw + offset.
# =====================================================================================================
SKEL = "/Game/LastBell/ThirdParty/Fab/Dungeon/Meshes/Skeletons/"
CAND = "/Game/LastBell/ThirdParty/Fab/Dungeon/Candles/Meshes/"
CHAPEL = "/Game/LastBell/Environments/Props/Procedural/Chapel/"
PROC = "/Game/LastBell/Environments/Props/Procedural/"
for k, v in {"SM_Skull_00": ((-8.6, -13.8, 0.1), (8.6, 16.2, 22.6)), "SM_Skull_01": ((-7.6, -13.8, 0.1), (7.5, 1.5, 8.3)),
             "SM_Skull_02": ((-8.6, -12.95, 0.0), (8.6, 12.95, 20.4)),
             "SM_Skeleton_Pile_01": ((-42.5, -49.1, 0.0), (42.5, 49.1, 46.2)), "SM_Skeleton_Pile_03": ((-53.3, -42.0, 0.0), (53.3, 42.0, 39.7)),
             "SM_Skeleton_Pile_04": ((-22.8, -43.5, 0.0), (22.8, 43.5, 27.9)), "SM_Skeleton_Pile_00": ((-49.7, -65.3, 0.0), (49.7, 65.3, 46.1)),
             "SM_Skeleton_Pile_05": ((-56.1, -59.8, -4.9), (43.4, 70.7, 241.9)),
             "SM_Skeleton_Arm_00": ((-12.1, -42.2, 0.0), (12.1, 42.2, 8.5)), "SM_Skeleton_Arm_01": ((-31.3, -39.9, 0.0), (31.3, 39.9, 15.2)),
             "SM_Skeleton_Leg_00": ((-27.7, -39.8, 0.0), (27.7, 39.8, 13.9)), "SM_Skeleton_Leg_01": ((-15.7, -32.6, 0.0), (15.7, 32.6, 23.4)),
             "SM_Skeleton_Pelvis": ((-15.8, -12.6, 0.0), (15.8, 12.6, 22.2)),
             "SM_Torture_Devices_Chains": ((-4.6, -5.5, -117.4), (4.6, 5.5, 0.2)),
             "SM_Torture_Devices_Cage_Open": ((-52.4, -74.6, 0.0), (52.4, 74.6, 267.6)),
             "SM_Charcoal_Pit": ((-13.8, -13.8, -0.2), (13.7, 14.7, 25.3)),
             "SM_Torch": ((-7.5, 0.0, -40.6), (7.9, 34.5, 29.7)),
             "SM_LB_Crypt_Block_100": ((-50.0, -50.0, 0.0), (50.0, 50.0, 100.0)),
             "SM_LB_Crypt_Sarcophagus_A": ((-150.0, -60.0, 0.0), (150.0, 60.0, 72.0)),
             "SM_LB_Crypt_Sarcophagus_B": ((-150.0, -60.0, 0.0), (150.0, 60.0, 72.0)),
             "SM_LB_Crypt_BoneBin_200x100x60": ((-100.0, -50.0, 0.0), (100.0, 50.0, 60.0)),
             "SM_LB_Crypt_WinchFrame": ((-130.0, -45.0, 0.0), (130.0, 45.0, 250.0)),
             "SM_LB_Crypt_RootsHang_A": ((-40.0, -40.0, -180.0), (40.0, 40.0, 0.0)),
             "SM_LB_Crypt_RootsHang_B": ((-45.0, -45.0, -240.0), (45.0, 45.0, 0.0)),
             "SM_LB_Crypt_RootsHang_C": ((-30.0, -30.0, -120.0), (30.0, 30.0, 0.0))}.items():
    MESH_BOUNDS[k] = v
MESH_BOUNDS["SM_Candle_Melted_02"] = ((-3.3, -3.5, 0.0), (3.3, 3.5, 15.3))
MESH_BOUNDS["SM_Candle_Melted_05"] = ((-3.3, -3.3, 0.0), (3.3, 3.3, 8.1))
MESH_BOUNDS["SM_Candle_Melted_08"] = ((-6.2, -6.0, 0.0), (6.2, 6.0, 8.3))
MESH_BOUNDS["SM_Candle_Melted_06"] = ((-2.5, -2.5, 0.0), (2.5, 2.5, 2.0))
MESH_BOUNDS["SM_LB_Prop_CandleFlame_A"] = ((-1.0, -1.0, 0.0), (1.0, 1.0, 4.0))
MESH_BOUNDS["Point"] = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
load_p93_bounds()   # measured P9-3 bounds override the design values registered above
drng = random.Random(91)


def to_world(origin, yaw, lx, ly, lz):
    rows = rot_rows(0.0, yaw, 0.0)
    return (origin[0] + lx * rows[0][0] + ly * rows[1][0], origin[1] + lx * rows[0][1] + ly * rows[1][1], origin[2] + lz)


# -- ossuary niche contents: per bay and tier, 17 skulls on the front of the sill + 3 bone piles behind --
SKULLS = [("SM_Skull_00", 0.5), ("SM_Skull_02", 0.35), ("SM_Skull_01", 0.15)]
for d in [p for p in placements if p["cat"] == "ossuary"]:
    yaw = d["rot"][1]
    sxp = d["scale"][0]
    org = d["loc"]
    for t, sill in (("T1", 45.0), ("T2", 185.0)):
        for i in range(17):
            r = drng.random()
            mesh = SKULLS[0][0] if r < 0.5 else SKULLS[1][0] if r < 0.85 else SKULLS[2][0]
            lx = (-160.0 + 20.0 * i + drng.uniform(-2.5, 2.5)) * sxp
            w = to_world(org, yaw, lx, -16.0, sill)
            add(f"CD_{d['id'][3:]}_{t}_Skull{i:02d}", "dress", mesh, SKEL, w, (0.0, yaw, 0.0), (drng.uniform(0.95, 1.05),) * 3,
                "NoCollision", "Crypt/Dressing/Ossuary/Niches", check=False,
                extra={"face_yaw": round(yaw + 90.0 + drng.uniform(-12, 12), 1),
                       "note2": "front of the skull must look out of the niche (world yaw face_yaw)"})
        for k, (pile, lx0) in enumerate((("SM_Skeleton_Pile_01", -110.0), ("SM_Skeleton_Pile_03", 0.0), ("SM_Skeleton_Pile_04", 110.0))):
            w = to_world(org, yaw, lx0 * sxp, -40.0, sill)
            add(f"CD_{d['id'][3:]}_{t}_Pile{k}", "dress", pile, SKEL, w, (0.0, round(drng.uniform(0, 360), 1), 0.0), (0.5, 0.5, 0.5),
                "NoCollision", "Crypt/Dressing/Ossuary/Niches", note="behind the skull row, in the niche back", check=False)

# -- greybox prop replacements (art at the greybox footprint; the greybox keeps its collision, invisible) --
REPL = [("CD_Sarcophagus_0", "SM_LB_Crypt_Sarcophagus_A", (7800, -2750, -600), 0.0, (1, 1, 1), "Prop_Crypt_0 footprint 300x120x70"),
        ("CD_Sarcophagus_1", "SM_LB_Crypt_Sarcophagus_B", (8700, -2750, -600), 180.0, (1, 1, 1), "Prop_Crypt_1 footprint"),
        ("CD_BoneBin_0", "SM_LB_Crypt_BoneBin_200x100x60", (7900, -2150, -600), 0.0, (1, 1, 1), "Prop_Crypt_2 footprint 200x100x60"),
        ("CD_BoneBin_1", "SM_LB_Crypt_BoneBin_200x100x60", (8600, -2150, -600), 180.0, (1, 1, 1), "Prop_Crypt_3 footprint"),
        ("CD_BrazierBlock", "SM_LB_Crypt_Block_100", (11000, -2300, -600), 0.0, (1.6, 1.6, 0.9), "Prop_Crypt_4 footprint 160x160x90"),
        ("CD_TortureSlab", "SM_LB_Crypt_Block_100", (11300, -1700, -600), 0.0, (1.0, 3.0, 0.6), "Prop_Crypt_5 footprint 100x300x60"),
        ("CD_CrankPlinth", "SM_LB_Crypt_Block_100", (8400, -2700, -600), 0.0, (0.5, 0.5, 0.7), "Plinth_Crank footprint 50x50x70")]
for pid, mesh, loc, yaw, sc, note in REPL:
    add(pid, "dress", mesh, CRYPT, loc, (0.0, yaw, 0.0), sc, "NoCollision", "Crypt/Dressing/Props", note=note, check=False)
for i, (x, y) in enumerate(((7900, -2150), (8600, -2150))):
    add(f"CD_BoneBin_{i}_Fill", "dress", "SM_Skeleton_Pile_03", SKEL, (x, y, -570), (0.0, 90.0 * i + 10, 0.0), (0.8, 0.8, 0.8),
        "NoCollision", "Crypt/Dressing/Props", note="fill inside the bin (bin floor at z 30)", check=False)
    for k in range(3):
        sx_ = x - 60 + 60 * k
        if i == 0 and k >= 1:   # P9-6a: Note_Ossuary (BP_Inspectable_Note, X 7885..7915, Y -2167..-2133, Z -540) lies on bin 0: keep it free
            sx_ = (7940, 7975)[k - 1]
        add(f"CD_BoneBin_{i}_Skull{k}", "dress", ("SM_Skull_00", "SM_Skull_02", "SM_Skull_00")[k], SKEL,
            (sx_, y + drng.uniform(-15, 15), -548), (0.0, round(drng.uniform(0, 360), 1), 0.0), (1, 1, 1),
            "NoCollision", "Crypt/Dressing/Props", note="on top of the fill", check=False)
add("CD_Charcoal", "dress", "SM_Charcoal_Pit", DUNGEON, (11000, -2300, -510), (0.0, 0.0, 0.0), (2.0, 2.0, 2.0), "NoCollision",
    "Crypt/Dressing/ChainChamber", note="brazier on the block; F4: SM_Charcoal_Pit has ONE slot (MI_Torch) -> MI_Crypt_Iron on it",
    check=False, extra={"mi_slots": {"0": "MI_Crypt_Iron"}})
add("CD_SlabShackles", "dress", "SM_Torture_Devices_Shackles_01", DUNGEON, (11300, -1640, -540), (0.0, 0.0, 0.0), (1, 1, 1),
    "NoCollision", "Crypt/Dressing/ChainChamber", note="lies flat on the slab top (thin axis vertical: check bounds)", check=False)
add("CD_SlabArm", "dress", "SM_Skeleton_Arm_01", SKEL, (11300, -1770, -540), (0.0, 20.0, 0.0), (1, 1, 1), "NoCollision",
    "Crypt/Dressing/ChainChamber", check=False)

# -- collision-bearing dressing (BlockAll; kept out of every route, >= 150 from AI points) --
add("CD_SkeletonStake", "dress", "SM_Skeleton_Pile_05", SKEL, (7580, -2840, -595), (0.0, 30.0, 0.0), (1, 1, 1), "BlockAll (mesh hull)",
    "Crypt/Dressing/Ossuary", note="skeleton on a stake in the SW corner", check=False)
add("CD_CageOpen", "dress", "SM_Torture_Devices_Cage_Open", DUNGEON, (11200, -2350, -560), (0.0, 15.0, 0.0), (1, 1, 1),
    "BlockAll (mesh hull)", "Crypt/Dressing/ChainChamber", note="hangs from beam 3; bottom 40 above the floor", check=False)
add("CD_WinchFrame", "dress", "SM_LB_Crypt_WinchFrame", CRYPT, (10800, -2120, -600), (0.0, 0.0, 0.0), (1, 1, 1),
    "BlockAll (UCX posts + sole plates)", "Crypt/Dressing/ChainChamber",
    note="south of Winch_Ritual2 (pedestal Y -2050..-1950); drum axis along X at Z -430", check=False)

# -- P9-R1A: the CD_PlaqueFrame record (stone frame around Clue_Diagram) is removed; the clue is now the readable note Note_Chains (D-073)

# -- chains (pivot at the top; 117.6 per segment) --
CHAINS = [("Winch", (10880, -2120), 3, "from beam 2 down into the drum's east end (drum top Z -408)"), ("Cage", (11200, -2350), 2, "into the cage top ring"),
          ("B0", (10300, -2300), 2, "loose"), ("B1", (10600, -1800), 1, "loose"),
          ("B3", (11200, -1900), 2, "loose")]
for cid, (x, y), n, note in CHAINS:
    for k in range(n):
        add(f"CD_Chain_{cid}_{k}", "dress", "SM_Torture_Devices_Chains", DUNGEON, (x, y, -95 - 117.6 * k), (0.0, 37.0 * k, 0.0),
            (1, 1, 1), "NoCollision", "Crypt/Dressing/ChainChamber/Chains", note=note, check=False)

# -- roots (pivot at the top) --
ROOTS = [("CC_0", "SM_LB_Crypt_RootsHang_A", (10150, -1875, -45), "through broken boards 02"),
         ("CC_1", "SM_LB_Crypt_RootsHang_B", (10450, -2375, -45), "through broken boards 10"),
         ("CC_2", "SM_LB_Crypt_RootsHang_A", (11050, -2125, -45), "through broken boards 31"),
         ("FP_0", "SM_LB_Crypt_RootsHang_B", (9620, -2280, -42), "from the vault crown over the pit"),
         ("FP_1", "SM_LB_Crypt_RootsHang_C", (9150, -2280, -42), "from the vault crown, west part"),
         ("WC_0", "SM_LB_Crypt_RootsHang_C", (6450, -1957.5, -42), "from the WC bay seam crown")]
for rid, mesh, loc, note in ROOTS:
    add(f"CD_Roots_{rid}", "dress", mesh, CRYPT, loc, (0.0, round(drng.uniform(0, 360), 1), 0.0), (1, 1, 1), "NoCollision",
        "Crypt/Dressing/Roots", note=note, check=False)

# -- torches (mesh: P9-6a; fire + light: P9-7). SM_Torch projects along local +Y from its back plate at y 0 --
TORCHES = [("T1", (6294, -1100, -400), -90.0, "landing west wall, seen from the stair foot"),
           ("T2", (9006, -2700, -400), 90.0, "ossuary east wall, south of J5: draws the player east"),
           ("T3", (11150, -694, -400), 180.0, "north corridor north wall, by the exit gate")]
for tid, loc, yaw, note in TORCHES:
    add(f"CD_Torch_{tid}", "dress", "SM_Torch", DUNGEON, loc, (0.0, yaw, 0.0), (1, 1, 1), "NoCollision", "Crypt/Dressing/Torches",
        note=note, check=False)

# -- candle clusters (meshes P9-6a; light P9-7 at origin + (0,0,25)) --
CLUSTER = [("SM_Candle_Melted_02", 0, 0), ("SM_Candle_Melted_05", 9, 4), ("SM_Candle_Melted_08", -8, 3), ("SM_Candle_Melted_06", 4, -6)]
clusters = []
for d in [p for p in placements if p.get("niche")]:
    run = next(r for r in RUNS if r[0] == d["run"])
    _, axis, face, _, _, s, _, _, _ = run
    cx, cy = d["niche"]["centre_xy_on_face"]
    if axis == "x":
        org = (cx, face - s * 12.0, d["niche"]["base_z"])
    else:
        org = (face - s * 12.0, cy, d["niche"]["base_z"])
    clusters.append((f"Niche_{d['run']}", org, d["rot"][1], "candle niche in " + d["id"]))
clusters += [("Sarc_0", (7690, -2750, -530), 0.0, "on the sarcophagus lid, west end"),
             ("Sarc_1", (8810, -2750, -530), 0.0, "on the sarcophagus lid, east end"),
             ("Puzzle_W", (10690, -1545, -600), 180.0, "floor, west of the lever row"),
             ("Puzzle_E", (11150, -1545, -600), 180.0, "floor, east of the lever row")]
for cid, org, yaw, note in clusters:
    for k, (mesh, lx, ly) in enumerate(CLUSTER):
        w = to_world(org, yaw, lx, ly, 0.0)
        add(f"CD_Candles_{cid}_{k}", "dress", mesh, CAND, w, (0.0, round(drng.uniform(0, 360), 1), 0.0), (1, 1, 1), "NoCollision",
            "Crypt/Dressing/Candles", note=note, check=False)
    add(f"CD_Candles_{cid}_Flame", "dress", "SM_LB_Prop_CandleFlame_A", CHAPEL, (org[0], org[1], org[2] + 15.6), (0.0, 0.0, 0.0),
        (1, 1, 1), "NoCollision", "Crypt/Dressing/Candles", note="on SM_Candle_Melted_02's wick (copy the P8 flame offset if it differs)",
        check=False)
    add(f"L_Crypt_Candle_{cid}", "light", "Point", "", (org[0], org[1], org[2] + 25.0), (0.0, 0.0, 0.0), (1, 1, 1), "-",
        "Lighting/Crypt", note=note, check=False,
        extra={"light": {"type": "PointLight", "lumens": 40 if cid.startswith("Puzzle") else (67.5 if cid.startswith("Sarc") else 90),   # P9-7 F7 / D1.16 accepted values
                         "radius": 320 if cid.startswith("Puzzle") else (250 if cid.startswith("Sarc") else 280),
                         "color": [255, 147, 70], "shadows": False, "light_function": "MI_LF_Candle", "source_radius": 2}})

# -- fallen timber in the flooded passage (existing P7 props, half under water, north side, off the ledge path) --
add("CD_FP_Planks", "dress", "SM_LB_Prop_RoofPlanks_Broken_200x100x4", PROC, (9150, -2170, -598), (0.0, 25.0, 8.0), (1, 1, 1),
    "NoCollision", "Crypt/Dressing/Flooded", note="half under the water plane (-593)", check=False)
add("CD_FP_Rafter", "dress", "SM_LB_Prop_Rafter_Broken_15x10x260", PROC, (9200, -2150, -596), (80.0, 10.0, 0.0), (1, 1, 1),
    "NoCollision", "Crypt/Dressing/Flooded", note="authored upright; pitch 80 lays it almost flat in the water", check=False)

# -- loose bones on the ossuary floor along the niche walls (NoCollision) --
FLOOR_BONES = [("SM_Skeleton_Pile_04", (7560, -2860), 0.7), ("SM_Skeleton_Arm_00", (8135, -2870), 1.0), ("SM_Skeleton_Leg_01", (8640, -2865), 1.0),
               ("SM_Skeleton_Pelvis", (8960, -2860), 1.0), ("SM_Skull_02", (7570, -2045), 1.0), ("SM_Skeleton_Arm_01", (8140, -2040), 1.0),
               ("SM_Skeleton_Leg_00", (8380, -2035), 1.0), ("SM_Skeleton_Pile_00", (8935, -2050), 0.5)]
for i, (mesh, (x, y), s) in enumerate(FLOOR_BONES):
    add(f"CD_FloorBones_{i}", "dress", mesh, SKEL, (x, y, -600), (0.0, round(drng.uniform(0, 360), 1), 0.0), (s, s, s), "NoCollision",
        "Crypt/Dressing/Ossuary/Floor", check=False)

# -- lights (P9-7) --
for tid, loc, yaw, note in TORCHES:
    w = to_world(loc, yaw, 0.0, 30.0, 45.0)
    add(f"L_Crypt_Torch_{tid}", "light", "Point", "", w, (0.0, 0.0, 0.0), (1, 1, 1), "-", "Lighting/Crypt", note=note, check=False,
        extra={"light": {"type": "PointLight", "lumens": 250, "radius": 350 if tid in ("T1", "T3") else 700, "color": [255, 140, 60], "shadows": False,
                         # F7 (D1.16/D1.17): 250 lm, T1/T3 radius 350 (T2 700); R2-C (D1.25): scattering 1.0 -> 0.5
                         "light_function": "MI_LF_Torch", "source_radius": 4, "volumetric_scattering": 0.5,
                         "fire": "PS_Fire_00 at the torch head, scale copied from the courtyard wall torch"}})
add("L_Crypt_Brazier", "light", "Point", "", (11000, -2300, -440), (0.0, 0.0, 0.0), (1, 1, 1), "-", "Lighting/Crypt", check=False,
    extra={"light": {"type": "PointLight", "lumens": 200, "radius": 650, "color": [255, 110, 40], "shadows": False,
                     "light_function": "MI_LF_Fire", "source_radius": 8, "fire": "PS_Fire_01 in the charcoal pit, scale to fit 55 cm"}})
# Moon shafts. Accepted values: G1 560 / G2 900 lm (D1.16); G3 250 lm, radius 550, shadowless, aimed 40 cm below Note_Chains (R2-C, D1.25).
# R2-C: bCastVolumetricShadow false on all three (it stepped the beam edges) and G1/G2 scattering 1.5 -> 0.8 (0.5 failed the +-15 % pose-mean check).
MOON = {"G1": dict(lumens=560, radius=900, inner=8, outer=20, shadows=True, scatter=0.8),
        "G2": dict(lumens=900, radius=900, inner=8, outer=20, shadows=True, scatter=0.8),
        "G3": dict(lumens=250, radius=550, inner=6, outer=16, shadows=False, scatter=1.5)}
for gid, loc, rot in (("G1", (8250, -2247.5, -50), "moon"), ("G2", (9750, -2280, -50), "moon"), ("G3", (11050, -1625, -46), (-67.3, 137.1, 0.0))):
    m = MOON[gid]
    add(f"L_Crypt_Moon_{gid}", "light", "Point", "", loc, rot if isinstance(rot, tuple) else (-78.0, 0.0, 0.0), (1, 1, 1), "-",
        "Lighting/Crypt", note=("aimed at (10920, -1504, -470): 40 cm below the Note_Chains centre (10920, -1504.15, -430)" if gid == "G3"
                                else "yaw = DirectionalLight_1 yaw (the moon azimuth); pitch -78"), check=False,
        extra={"light": {"type": "SpotLight", "lumens": m["lumens"], "radius": m["radius"], "inner_cone": m["inner"],
                         "outer_cone": m["outer"], "color": [158, 184, 255], "shadows": m["shadows"], "volumetric_scattering": m["scatter"],
                         "volumetric_shadow": False,
                         "tune": "pool centre luma 0.25-0.45 (G1/G2 floor); G3: pool on the note 0.30-0.45, note in the brightest third"}})

# -- decals (P9-6a). Wall decals: rotation (0, yaw, 90), DecalSize (depth, vertical/2, horizontal/2); floor: (-90, yaw, 0) --
def wall_decal(did, mi, run_id, along, zc, vhalf, hhalf, note=""):
    run = next(r for r in RUNS if r[0] == run_id)
    _, axis, face, _, _, s, _, _, _ = run
    if axis == "x":
        loc = (along, face, zc)
        yaw = -90.0 if s > 0 else 90.0
    else:
        loc = (face, along, zc)
        yaw = 180.0 if s > 0 else 0.0
    add(did, "decal", "Point", "", loc, (0.0, yaw, 90.0), (1, 1, 1), "-", "Crypt/Dressing/Decals", note=note, check=False,
        extra={"decal": {"mi": mi, "size": [12.0, vhalf, hhalf], "wall_run": run_id}})


def floor_decal(did, mi, x, y, uhalf, vhalf, yaw=0.0, z=-600.0, note=""):
    add(did, "decal", "Point", "", (x, y, z), (-90.0, yaw, 0.0), (1, 1, 1), "-", "Crypt/Dressing/Decals", note=note, check=False,
        extra={"decal": {"mi": mi, "size": [10.0, vhalf, uhalf]}})


MOULD = [("WC_E", "E_WC", -1800, 370), ("SC_N", "N_SC", 7050, 420), ("SC_S", "S_WCSC", 6950, 500), ("FP_S0", "S_FP", 9250, 250),
         ("FP_S1", "S_FP", 9750, 250), ("FP_N0", "N_FP", 9150, 150), ("FP_N1", "N_FP", 9900, 100), ("CC_S0", "S_CC", 10400, 400),
         ("CC_S1", "S_CC", 11150, 350), ("NC_N", "N_NC_E", 11150, 340), ("L_W", "W6300", -1100, 300)]
for mid, run_id, along, half in MOULD:
    wall_decal(f"CD_Decal_Mould_{mid}", "MI_Decal_Mould", run_id, along, -555.0, 45.0, half, note="rising damp band Z -600..-510")
LEAKS = [("FP_S0", "MI_Decal_Leaking004_Wall", "S_FP", 9150), ("FP_S1", "MI_Decal_Leaking004_Wall", "S_FP", 9560),
         ("FP_N0", "MI_Decal_Leaking004_Wall", "N_FP", 9400), ("FP_N1", "MI_Decal_Leaking004_Wall", "N_FP", 9850),
         ("OS_E", "MI_Decal_Leaking004_Wall", "E_OS_S", -2650), ("CC_E", "MI_Decal_Leaking004_Wall", "E_CC", -2250),
         # P9-6a F3: Leaking006 read as an opaque mustard band in the crypt -> Leaking004 (same size and rotation); 006 is left to the courtyard
         ("WC_W", "MI_Decal_Leaking004_Wall", "W6300", -2000), ("SC_S", "MI_Decal_Leaking004_Wall", "S_WCSC", 7200),
         ("NC_S", "MI_Decal_Leaking004_Wall", "S_NC", 11000)]
for lid, mi, run_id, along in LEAKS:
    wall_decal(f"CD_Decal_Leak_{lid}", mi, run_id, along, -220.0, 210.0, 85.0, note="streaks from Z -10 down to -430")
for tid, loc, yaw, note in TORCHES:
    run_id = {"T1": "W6300", "T2": "E_OS_S", "T3": "N_NC_E"}[tid]
    along = loc[1] if tid in ("T1", "T2") else loc[0]
    wall_decal(f"CD_Decal_Soot_{tid}", "MI_Decal_Soot_A" if tid != "T2" else "MI_Decal_Soot_B", run_id, along, -230.0, 110.0, 45.0,
               note="above the torch flame")
for i, (x, y, u, v) in enumerate(((8700, -2280, 220, 160), (10300, -2280, 220, 160), (8250, -2247.5, 90, 90), (9100, -2400, 120, 80))):
    floor_decal(f"CD_Decal_WaterStain_{i}", "MI_Decal_WaterStain", x, y, u, v, note="wet floor at the water ends / under grate G1")
for i, (x, y) in enumerate(((7560, -2860), (8940, -2860), (7560, -2040), (8940, -2040))):
    floor_decal(f"CD_Decal_Dust_{i}", "MI_Decal_DustDrift", x, y, 110, 110, yaw=[180.0, 270.0, 90.0, 0.0][i],
                note="dense corner of the texture in the room corner")
for cid, org, yaw, note in clusters:
    if cid.startswith("Puzzle"):
        floor_decal(f"CD_Decal_Wax_{cid}", "MI_Decal_WaxDrips", org[0], org[1], 35, 35)
    elif cid.startswith("Sarc"):
        floor_decal(f"CD_Decal_Wax_{cid}", "MI_Decal_WaxDrips", org[0], org[1], 25, 25, z=-530.0, note="on the lid top, depth 5")


# ---- intrusion check: walls (floor level) and portal legs must not enter open spaces ----
def rect_overlap(a, b):
    ox = min(a[1], b[1]) - max(a[0], b[0])
    oy = min(a[3], b[3]) - max(a[2], b[2])
    return ox > 0.5 and oy > 0.5, ox, oy


for d in placements:
    if d["cat"] == "wall":
        run = next(r for r in RUNS if r[0] == d["run"])
        _, axis, face, a, b, s, _, _, _ = run
        x0, y0, _ = d["aabb_min"]
        x1, y1, _ = d["aabb_max"]
        fp = [x0, x1, y0, y1]
        # shrink 3 cm on the open side (the stone face is allowed to sit on the face line)
        if axis == "x":
            if s > 0:
                fp[3] -= 3.0
            else:
                fp[2] += 3.0
        else:
            if s > 0:
                fp[1] -= 3.0
            else:
                fp[0] += 3.0
        for sp, r in OPEN.items():
            hit, ox, oy = rect_overlap(fp, (r[0], r[1], r[2], r[3]))
            if hit:
                issues.append(f"{d['id']} enters {sp} by {round(min(ox, oy), 1)} cm (footprint {rnd(fp, 1)})")
    if d["cat"] == "portal":
        pid = d["portal"]
        _, axis, plane, o1, o2, r, _ = next(p for p in PORTALS if p[0] == pid)
        sx = abs(d["scale"][0])
        legw = 91.6 * sx
        dc = plane + r * D
        legs = []
        for lo, hi in ((o1 - legw, o1), (o2, o2 + legw)):
            if axis == "x":
                legs.append([lo + 0.5, hi - 0.5, dc - 77.5, dc + 77.5])
            else:
                legs.append([dc - 77.5, dc + 77.5, lo + 0.5, hi - 0.5])
        for leg in legs:
            # the leg is allowed 2.5 cm proud of the plane on the open side
            if axis == "x":
                if r > 0:
                    leg[2] += 3.0
                else:
                    leg[3] -= 3.0
            else:
                if r > 0:
                    leg[0] += 3.0
                else:
                    leg[1] -= 3.0
            for sp, rr in OPEN.items():
                hit, ox, oy = rect_overlap(leg, (rr[0], rr[1], rr[2], rr[3]))
                if hit:
                    issues.append(f"{d['id']} leg {rnd(leg, 1)} enters {sp} by {round(min(ox, oy), 1)} cm")

# Columns must keep >= 109 cm (hull half 75 + Warden radius 42 - 8 slack) from AI points and WalkPath points
AI_POINTS = {
    "Patrol_Crypt_01": (8200, -2450), "Patrol_Crypt_02": (8850, -2250), "Search_Crypt_02": (7650, -2250),
    "Search_Crypt_03": (8250, -2650), "Search_Crypt_04": (8925, -2750), "Plinth_Crank": (8400, -2700),
    "FloodedLedge_00": (8750, -2380), "Warden_start": (8920, -2560),
}
for cid, x, y, kind in COLUMNS:
    if kind != "free":
        continue
    for n, (px, py) in AI_POINTS.items():
        dist = math.hypot(px - x, py - y)
        if dist < 150:
            issues.append(f"column {cid} is {round(dist)} cm from {n}")

# ---- outputs ----
os.makedirs(os.path.join(ROOT, "Docs", "plans"), exist_ok=True)
summary = {}
for d in placements:
    summary[d["cat"]] = summary.get(d["cat"], 0) + 1
out = {"generator": "Tools/crypt/gen_crypt_layout.py", "units": "cm, UE world; rot = [pitch, yaw, roll]",
       "measured_bounds_from_p93": sorted(set(MEASURED_FROM_P93)),
       "counts": summary, "issues": issues, "placements": placements}
with open(os.path.join(ROOT, "Docs", "plans", "p9_d1_layout.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)


def fmt(v):
    return "(" + ", ".join(f"{x:g}" for x in v) + ")"


lines = ["# P9 D1 placement tables (generated)", "",
         "Generated by `Tools/crypt/gen_crypt_layout.py` (do not edit by hand; change the generator and re-run). "
         "World cm; rotation = (pitch, yaw, roll); AABB = expected world bounds from the P9-2 mesh bounds (P9-5 read-back tolerance 3 cm). "
         "Machine-readable copy: `Docs/plans/p9_d1_layout.json`.", "",
         "Counts: " + ", ".join(f"{k} {v}" for k, v in summary.items()), ""]
if issues:
    lines += ["**Intrusion issues:**", ""] + [f"- {i}" for i in issues] + [""]
for cat, title in (("wall", "Walls (SM_Wall_00 / SM_Wall_01, NoCollision)"), ("pitwall", "Pit walls (sunk, under the water)"),
                   ("portal", "Portals (SM_Arch pairs, NoCollision)"), ("vault", "Vault bays (SM_Roof, pivot Z -44)"),
                   ("column", "Columns and capitals"), ("ossuary", "Ossuary niche bays"), ("stair", "Stair flights"),
                   ("soffit", "Stair soffits"), ("ceiling", "Chain chamber ceiling"), ("grate", "Moon grates"),
                   ("water", "Water planes"), ("backdrop", "Backdrop safety box")):
    rows = [d for d in placements if d["cat"] == cat]
    if not rows:
        continue
    lines += [f"## {title} ({len(rows)})", "", "| Label | Mesh | Location | Rotation | Scale | AABB min .. max | Note |",
              "|---|---|---|---|---|---|---|"]
    for d in rows:
        note = d["note"]
        if "niche" in d:
            n = d["niche"]
            note += f"; **candle niche** centre on face {fmt(n['centre_xy_on_face'])}, base Z {n['base_z']}, top Z {n['top_z']}, {n['width']} wide, 25 deep"
        lines.append(f"| {d['id']} | {d['mesh'].split('/')[-1]} | {fmt(d['loc'])} | {fmt(d['rot'])} | {fmt(d['scale'])} | "
                     f"{fmt(d['aabb_min'])} .. {fmt(d['aabb_max'])} | {note} |")
    lines.append("")
dress = [d for d in placements if d["cat"] == "dress"]
niche = [d for d in dress if "_Skull" in d["id"] and d["id"].startswith("CD_Ossuary") or "_Pile" in d["id"] and d["id"].startswith("CD_Ossuary")]
other = [d for d in dress if d not in niche]
lines += [f"## Dressing (P9-6a): {len(dress)} actors", "",
          f"Ossuary niche contents: {len(niche)} actors (`CD_Ossuary_<bay>_<T1|T2>_Skull00..16` and `_Pile0..2`), listed only in the JSON. "
          "Skulls carry `face_yaw` (the world yaw the face must look toward); P9-6a measures each skull mesh's facing offset once and sets "
          "actor yaw = face_yaw + offset. Everything else:", "",
          "| Label | Mesh | Location | Rotation | Scale | Collision | Note |", "|---|---|---|---|---|---|---|"]
for d in other:
    lines.append(f"| {d['id']} | {d['mesh'].split('/')[-1]} | {fmt(d['loc'])} | {fmt(d['rot'])} | {fmt(d['scale'])} | {d['collision']} | {d['note']} |")
lines.append("")
lines += ["## Decals (P9-6a)", "", "Wall: rotation (0, yaw, 90), DecalSize = (depth, vertical half, horizontal half); floor: (-90, yaw, 0), "
          "DecalSize = (depth, v half, u half). Yaw makes the decal X point from the room into the wall (verify one per orientation).", "",
          "| Label | MI | Location | Rotation | DecalSize | Note |", "|---|---|---|---|---|---|"]
for d in [p for p in placements if p["cat"] == "decal"]:
    lines.append(f"| {d['id']} | {d['decal']['mi']} | {fmt(d['loc'])} | {fmt(d['rot'])} | {fmt(d['decal']['size'])} | {d['note']} |")
lines.append("")
lines += ["## Lights (P9-7)", "", "| Label | Type | Location | Rotation | Lumens | Radius | Colour | Shadows | Light function / extra | Note |",
          "|---|---|---|---|---|---|---|---|---|---|"]
for d in [p for p in placements if p["cat"] == "light"]:
    L = d["light"]
    extra = L.get("light_function", "")
    if "inner_cone" in L:
        extra = (f"cone {L['inner_cone']}/{L['outer_cone']}; scattering {L['volumetric_scattering']}; "
                 f"volumetric shadow {L.get('volumetric_shadow', False)}; tune: {L['tune']}")
    if "fire" in L:
        extra += f"; {L['fire']}"
    lines.append(f"| {d['id']} | {L['type']} | {fmt(d['loc'])} | {fmt(d['rot'])} | {L['lumens']} | {L['radius']} | {fmt(L['color'])} | "
                 f"{L['shadows']} | {extra} | {d['note']} |")
lines.append("")
tile_rows = [d for d in placements if d["cat"] == "tile"]
lines += [f"## Floor tiles ({len(tile_rows)})", "",
          "SM_Ground, NoCollision, Z -600 (surface), scale 1. Global 200 grid, centres on odd hundreds; yaw seeded (random.Random(9)) "
          "from {0, 180} (SC, OS, CC, NC) or {90, 270} (L, WC, LW, LE). Space: x,y:yaw list.", ""]
by_space = {}
for d in tile_rows:
    sp = d["id"].split("_")[2]
    by_space.setdefault(sp, []).append(f"{d['loc'][0]:g},{d['loc'][1]:g}:{d['rot'][1]:g}")
for sp, lst in by_space.items():
    lines.append(f"- **{sp}** ({len(lst)}): " + " ".join(lst))
lines.append("")
with open(os.path.join(ROOT, "Docs", "plans", "p9_d1_tables.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

# ---- SVG plan ----
X0, X1, Y0, Y1 = 6000, 12000, -3400, 900
S = 0.2
W, H = (X1 - X0) * S, (Y1 - Y0) * S


def sx_(x):
    return (x - X0) * S


def sy_(y):
    return (Y1 - y) * S


svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H + 40:.0f}" viewBox="0 0 {W:.0f} {H + 40:.0f}" '
       f'font-family="sans-serif" font-size="9">', f'<rect width="100%" height="100%" fill="#1b1b1e"/>']
for sp, (x0, x1, y0, y1) in OPEN.items():
    svg.append(f'<rect x="{sx_(x0):.1f}" y="{sy_(y1):.1f}" width="{(x1 - x0) * S:.1f}" height="{(y1 - y0) * S:.1f}" fill="#3a3a40" stroke="#666"/>')
    svg.append(f'<text x="{sx_(x0) + 3:.1f}" y="{sy_(y1) + 11:.1f}" fill="#aaa">{sp}</text>')
colors = {"wall": "#c9b48a", "pitwall": "#7a6a50", "portal": "#e07a3a", "ossuary": "#d4c9a8", "column": "#ffffff",
          "water": "#2a5f7a", "ceiling": "#7a5230", "grate": "#88aaff"}
for d in placements:
    c = colors.get(d["cat"])
    if not c or d["cat"] == "ceiling":
        continue
    mn, mx = d["aabb_min"], d["aabb_max"]
    op = "0.55" if d["cat"] in ("water",) else "0.8"
    svg.append(f'<rect x="{sx_(mn[0]):.1f}" y="{sy_(mx[1]):.1f}" width="{max(1, (mx[0] - mn[0]) * S):.1f}" '
               f'height="{max(1, (mx[1] - mn[1]) * S):.1f}" fill="{c}" fill-opacity="{op}" stroke="#000" stroke-width="0.3"/>')
for n, (px, py) in AI_POINTS.items():
    svg.append(f'<circle cx="{sx_(px):.1f}" cy="{sy_(py):.1f}" r="3" fill="#ff4060"/>')
svg.append(f'<text x="6" y="{H + 16:.0f}" fill="#ddd">P9 D1 crypt plan (top-down, X right, Y up). Sand = walls, orange = portals, white = columns, '
           f'pale = ossuary niche bays, blue = water/grates, red = AI/route points. 1 px = 5 cm.</text>')
svg.append("</svg>")
with open(os.path.join(ROOT, "Docs", "ArtTest", "crypt", "d1_layout_plan.svg"), "w", encoding="utf-8") as f:
    f.write("\n".join(svg))

# ---- PNG plan (same content, for the review; needs Pillow) ----
try:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (int(W), int(H + 40)), (27, 27, 30))
    dr = ImageDraw.Draw(img)

    def box(mn, mx, fill, outline=(0, 0, 0)):
        dr.rectangle([sx_(mn[0]), sy_(mx[1]), sx_(mx[0]), sy_(mn[1])], fill=fill, outline=outline)

    for sp, (x0, x1, y0, y1) in OPEN.items():
        box((x0, y0), (x1, y1), (58, 58, 64), (110, 110, 110))
        dr.text((sx_(x0) + 3, sy_(y1) + 3), sp, fill=(190, 190, 190))
    pal = {"ossuary": (212, 201, 168), "wall": (201, 180, 138), "pitwall": (122, 106, 80), "portal": (224, 122, 58),
           "column": (255, 255, 255), "water": (42, 95, 122), "grate": (136, 170, 255)}
    for cat in ("water", "pitwall", "wall", "ossuary", "portal", "column", "grate"):
        for d in placements:
            if d["cat"] == cat and not (cat == "column" and "Capital" in d["id"]):
                box(d["aabb_min"], d["aabb_max"], pal[cat])
    for n, (px, py) in AI_POINTS.items():
        dr.ellipse([sx_(px) - 3, sy_(py) - 3, sx_(px) + 3, sy_(py) + 3], fill=(255, 64, 96))
    dr.text((6, H + 12), "P9 D1 crypt plan, top-down (X right, Y up), 1 px = 5 cm. Sand walls, orange portals, white columns, "
            "pale ossuary niche bays, blue water/grates, red AI/route points.", fill=(220, 220, 220))
    img.save(os.path.join(ROOT, "Docs", "ArtTest", "crypt", "d1_layout_plan.png"))
except ImportError:
    pass

print("counts:", summary)
print("issues:", len(issues))
for i in issues:
    print("  ", i)
sys.exit(1 if issues else 0)
