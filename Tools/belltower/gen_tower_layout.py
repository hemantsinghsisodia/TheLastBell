"""P10-L: cloister + bell tower layout generator (amendment D1.1-D1.4, D1.6 (Mech 3 position), D1.7, D1.8, D1.9).

Pure Python, no Unreal Editor, no Blender. Reads the P10-2 survey data (Docs/ArtTest/belltower/*.json) and writes:
  Docs/plans/p10_d1_layout.json             one record per actor (placements), plus hide_greybox, pieces, lights plan, checks
  Docs/plans/p10_d1_tables.md               the same as tables (do not edit by hand)
  Docs/ArtTest/belltower/d1_layout_plan.png top view: cloister + passage + tower (footprints, WalkPaths, AI points, lights)
  Docs/ArtTest/belltower/d1_tower_section.png vertical section + unrolled stair profile of the tower

Run from anywhere:  python Tools/belltower/gen_tower_layout.py
Deterministic (seeded). Exit code 0 only when every D1.9 check passes.
Optional flag --n-roof-fix applies the proposed fix for the N-walk collapse panel (see check D1-N1 in the output).
"""
import heapq
import json
import math
import os
import random
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SURVEY = os.path.join(ROOT, "Docs", "ArtTest", "belltower")
N_ROOF_FIX = "--n-roof-fix" in sys.argv

# ------------------------------------------------------------------------------------------------ paths
TWM = "/Game/LastBell/Environments/BellTower/Meshes/"
CLM = "/Game/LastBell/Environments/Cloister/Meshes/"
KIT = "/Game/LastBell/Environments/Kit/"
PROC = "/Game/LastBell/Environments/Props/Procedural/"
CHAPEL = "/Game/LastBell/Environments/Props/Procedural/Chapel/"
IVY = "/Game/LastBell/Environments/Props/Procedural/Ivy/"
CC0 = "/Game/LastBell/Environments/Props/CC0/"
DUNGEON = "/Game/LastBell/ThirdParty/Fab/Dungeon/Meshes/Props/"
ARTTEST = "/Game/LastBell/ArtTest/Props/"
ENGINE = "/Engine/BasicShapes/"

MI_PATHS = {   # existing MIs (materials_list_p10.json); new P10-4 MIs live in the BellTower materials folder (assumed path)
    "MI_Kit_Masonry": "/Game/LastBell/Environments/Kit/Materials/MI_Kit_Masonry",
    "MI_Kit_Trim": "/Game/LastBell/Environments/Kit/Materials/MI_Kit_Trim",
    "MI_Kit_Rubble": "/Game/LastBell/Environments/Kit/Materials/MI_Kit_Rubble",
    "MI_Kit_Slate": "/Game/LastBell/Environments/Kit/Materials/MI_Kit_Slate",
    "MI_Kit_Floor": "/Game/LastBell/Environments/Kit/Materials/MI_Kit_Floor",
    "MI_Chapel_Wood_Old": "/Game/LastBell/Environments/Chapel/Materials/MI_Chapel_Wood_Old",
    "MI_Chapel_Floor_Dirty": "/Game/LastBell/Environments/Chapel/Materials/MI_Chapel_Floor_Dirty",
    "MI_Chapel_Floor_Puddled": "/Game/LastBell/Environments/Chapel/Materials/MI_Chapel_Floor_Puddled",
    "MI_Prop_Wood_Weathered": "/Game/LastBell/Environments/Courtyard/Materials/MI_Prop_Wood_Weathered",
    "MI_Prop_Earth": "/Game/LastBell/Environments/Courtyard/Materials/MI_Prop_Earth",
    "MI_Crypt_Iron": "/Game/LastBell/Environments/Crypt/Materials/MI_Crypt_Iron",
    "MI_Decal_Mould": "/Game/LastBell/Materials/Instances/MI_Decal_Mould",
    "MI_Decal_Leaking004_Wall": "/Game/LastBell/Environments/Crypt/Materials/MI_Decal_Leaking004_Wall",
    "MI_Cobweb_Dungeon": "/Game/LastBell/Materials/Instances/MI_Cobweb_Dungeon",
    "MI_LB_BellBronze": "/Game/LastBell/Environments/BellTower/Materials/MI_LB_BellBronze",
    "MI_LB_Rope": "/Game/LastBell/Environments/BellTower/Materials/MI_LB_Rope",
    "MI_LB_Sally": "/Game/LastBell/Environments/BellTower/Materials/MI_LB_Sally",
    "MI_LB_BellBand_I": "/Game/LastBell/Environments/BellTower/Materials/MI_LB_BellBand_I",
    "MI_LB_BellBand_II": "/Game/LastBell/Environments/BellTower/Materials/MI_LB_BellBand_II",
    "MI_LB_BellBand_III": "/Game/LastBell/Environments/BellTower/Materials/MI_LB_BellBand_III",
    "MI_LB_BellBand_IV": "/Game/LastBell/Environments/BellTower/Materials/MI_LB_BellBand_IV",
}
SLOT_MI = {   # D1.5 slot mapping
    "MAT_Masonry": "MI_Kit_Masonry", "MAT_Trim": "MI_Kit_Trim", "MAT_Rubble": "MI_Kit_Rubble",
    "MAT_Iron": "MI_Crypt_Iron", "MAT_Slate": "MI_Kit_Slate", "MAT_Earth": "MI_Prop_Earth",
    "MAT_Bronze": "MI_LB_BellBronze", "MAT_Rope": "MI_LB_Rope", "MAT_Sally": "MI_LB_Sally", "MAT_Band": "MI_LB_BellBand_III",
}
WOOD_TOWER, WOOD_CLOISTER = "MI_Chapel_Wood_Old", "MI_Prop_Wood_Weathered"


# ------------------------------------------------------------------------------------------------ math helpers
def rot_rows(p, y, r):
    """UE FRotationMatrix rows (local X, Y, Z axes in world)."""
    P, Y, R = (math.radians(v) for v in (p, y, r))
    SP, CP, SY, CY, SR, CR = math.sin(P), math.cos(P), math.sin(Y), math.cos(Y), math.sin(R), math.cos(R)
    return [
        (CP * CY, CP * SY, SP),
        (SR * SP * CY - CR * SY, SR * SP * SY + CR * CY, -SR * CP),
        (-(CR * SP * CY + SR * SY), CY * SR - CR * SP * SY, CR * CP),
    ]


def rot_from_rows(X, Y, Z):
    """FMatrix::Rotator(): rotator [pitch, yaw, roll] from orthonormal axis rows."""
    pitch = math.degrees(math.atan2(X[2], math.hypot(X[0], X[1])))
    yaw = math.degrees(math.atan2(X[1], X[0]))
    sy = (-math.sin(math.radians(yaw)), math.cos(math.radians(yaw)), 0.0)
    roll = math.degrees(math.atan2(sum(a * b for a, b in zip(Z, sy)), sum(a * b for a, b in zip(Y, sy))))
    return [pitch, yaw, roll]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def xf_point(loc, rot, scale, v):
    rows = rot_rows(*rot)
    s = (v[0] * scale[0], v[1] * scale[1], v[2] * scale[2])
    return tuple(loc[k] + s[0] * rows[0][k] + s[1] * rows[1][k] + s[2] * rows[2][k] for k in range(3))


def world_aabb(mb, loc, rot, scale):
    lo, hi = mb
    pts = [xf_point(loc, rot, scale, (cx, cy, cz)) for cx in (lo[0], hi[0]) for cy in (lo[1], hi[1]) for cz in (lo[2], hi[2])]
    return [min(p[k] for p in pts) for k in range(3)], [max(p[k] for p in pts) for k in range(3)]


def rnd(v, n=3):
    return [round(float(x), n) for x in v]


def frame_pt(origin, yaw, x, y):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return (origin[0] + x * c - y * s, origin[1] + x * s + y * c)


def rect_gap(px, py, mn, mx):
    """distance from a point to an XY rectangle (0 inside)."""
    return math.hypot(max(mn[0] - px, 0, px - mx[0]), max(mn[1] - py, 0, py - mx[1]))


def seg_rect_dist(a, b, mn, mx, step=2.0):
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    n = max(1, int(L / step))
    best = 1e9
    for s in range(n + 1):
        t = s / n
        best = min(best, rect_gap(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, mn, mx))
    return best


# ------------------------------------------------------------------------------------------------ survey data
with open(os.path.join(SURVEY, "greybox_p10.json"), encoding="utf-8") as f:
    GREYBOX = {g["label"]: g for g in json.load(f)}
with open(os.path.join(SURVEY, "kit_p10.json"), encoding="utf-8") as f:
    KITJ = json.load(f)
with open(os.path.join(SURVEY, "ai_p10.json"), encoding="utf-8") as f:
    AIJ = json.load(f)
with open(os.path.join(ROOT, "Docs", "ArtTest", "props_ue", "import_report.json"), encoding="utf-8") as f:
    PROPS_UE = {r["mesh"]: r for r in json.load(f)}


def gb(label):
    b = GREYBOX[label]["bounds"]
    return [b["min"]["x"], b["min"]["y"], b["min"]["z"]], [b["max"]["x"], b["max"]["y"], b["max"]["z"]]


def kit_bounds(path):
    k = KITJ[path]["bounds"]
    return ((k["min"]["x"], k["min"]["y"], k["min"]["z"]), (k["max"]["x"], k["max"]["y"], k["max"]["z"]))


def kit_slots(path):
    return list(KITJ[path]["slots"].keys())


# ------------------------------------------------------------------------------------------------ piece registry
PIECES = {}     # name -> dict(path, mbounds, slots, seed, pivot, ucx, note)  (new Blender pieces; bounds from the D1 piece tables)
EST_BOUNDS = set()


def piece(name, folder, mb, slots, seed, pivot, ucx="none", note=""):
    PIECES[name] = {"path": folder + name + "." + name, "mbounds": [list(mb[0]), list(mb[1])], "slots": slots, "seed": seed,
                    "pivot": pivot, "ucx": ucx, "note": note}
    return PIECES[name]["path"]


EXISTING = {}   # full object path -> (mbounds, slots)


def existing(path_prefix, name, mb=None, slots=None, est=False):
    full = path_prefix + name + "." + name
    if full in KITJ:
        mb = kit_bounds(full)
        slots = kit_slots(full)
    elif name in PROPS_UE:
        r = PROPS_UE[name]
        mb = (tuple(r["min"]), tuple(r["max"]))
        slots = slots or list(r.get("slots", []))
    if mb is None:
        raise KeyError(full)
    if est:
        EST_BOUNDS.add(full)
    EXISTING[full] = (mb, slots or [])
    return full


def mbounds_of(path):
    for name, p in PIECES.items():
        if p["path"] == path:
            return tuple(map(tuple, p["mbounds"]))
    return EXISTING[path][0]


RECS = []
ISSUES = []
WARNS = []


def add(rid, cat, group, mesh, loc, rot, scale, collision, folder, mi=None, note="", extras=None, lane_zlo=None):
    mb = mbounds_of(mesh)
    mn, mx = world_aabb(mb, loc, rot, scale)
    d = {"id": rid, "cat": cat, "group": group, "mesh": mesh, "loc": rnd(loc), "rot": rnd(rot, 4), "scale": rnd(scale, 5),
         "collision": collision, "folder": folder, "mbounds": [list(mb[0]), list(mb[1])], "aabb_min": rnd(mn, 2),
         "aabb_max": rnd(mx, 2), "mi_slots": mi or {}, "extras": extras or {}, "note": note}
    if mesh in EST_BOUNDS:
        d["extras"]["mbounds_estimated"] = True
    if lane_zlo is not None:
        d["lane_zlo"] = lane_zlo
    RECS.append(d)
    return d


def mi_for(slots, wood=WOOD_TOWER, overrides=None):
    out = {}
    for s in slots:
        out[s] = wood if s == "MAT_Wood" else SLOT_MI[s]
    if overrides:
        out.update(overrides)
    return out


# ------------------------------------------------------------------------------------------------ constants
RISE_F = 2500.0 / 11.0          # flight rise (227.2727)
RISE_T = 2500.0 / 154.0         # tread rise (16.2338)
CUBE = ENGINE + "Cube.Cube"
EXISTING[CUBE] = (((-50.0, -50.0, -50.0), (50.0, 50.0, 50.0)), [])

# lane / AI data -------------------------------------------------------------------------------------
PATROL = [(p["label"], tuple(p["loc"])) for p in sorted(AIJ["AI/Patrol"], key=lambda q: q["props"]["order"])]
SEARCH = [(p["label"], tuple(p["loc"])) for p in AIJ["AI/Search"]]
SPAWN = [(p["label"], tuple(p["loc"])) for p in AIJ["AI/Spawn"] if p["label"] in ("WSpawn_Cloister", "WSpawn_Tower")]
WP_TOWER = [(p["label"], tuple(p["loc"])) for p in AIJ["WalkPaths/TowerStairs"]]
WP_CRYPT = [(p["label"], tuple(p["loc"])) for p in AIJ["WalkPaths/CryptToCloister"]]
MECH3_LOC = (11780.0, 1760.0, 50.0)     # D1.0/D1.6: Mech_Ritual3 moved here by P10-6b


# =====================================================================================================
# D1.1 / D1.2  TOWER
# =====================================================================================================
TW_FACES = {   # face -> (origin XY of local (0,0), yaw, length)  (D1.1 table)
    "W": ((12040.0, 1500.0), 90.0, 1000.0),
    "E": ((12960.0, 2500.0), -90.0, 1000.0),
    "N": ((12040.0, 2460.0), 0.0, 920.0),
    "S": ((12960.0, 1540.0), 180.0, 920.0),
}
STAGES = [("S1", 0.0, 800.0, 10.0), ("S2", 800.0, 1700.0, 10.0), ("S3", 2500.0, 1040.0, 15.0)]   # name, z0, height, max course projection
OPENINGS = {
    ("S1", "W"): "Door Y 1948-2052 (x 448-552), jambs z 0-194 (8 cm chamfers), gabled head apex z 228 at x 500, hood mould 8 proud 15 tall 20 above the head",
    ("S1", "N"): "Slit F01 at x 460, z 263.6", ("S1", "E"): "Slit F02 at x 500, z 490.9", ("S1", "S"): "Slit F03 at x 460, z 718.1",
    ("S2", "W"): "Slit F08 at x 500, z 1054.0 (world 1854)", ("S2", "N"): "Slits F05 / F09 at x 460, z 372.7 / 1281.8",
    ("S2", "E"): "Slits F06 / F10 at x 500, z 600.0 / 1509.1", ("S2", "S"): "Slit F07 at x 460, z 827.3",
}
COURSES = ("Plinth z 0-60 proj 10 (interrupted at the W door Y 1948-2052)", "Drip z 1210-1230 proj 8", "Belfry sill z 2470-2500 proj 10",
           "Cornice z 3480-3540 proj 15 (absent over the SW collapse)")
LANCETS = {"W": (405.0, 595.0), "E": (405.0, 595.0), "N": (365.0, 555.0), "S": (365.0, 555.0)}   # centres of x 340-470 / 530-660 and 300-430 / 490-620

# ---- pieces (mbounds from the D1 piece tables; wall pieces include the exterior-course projections)
WALL_MB = {}
for si, (stg, z0, H, proj) in enumerate(STAGES):
    for fi, face in enumerate("WNES"):
        L = TW_FACES[face][2]
        name = f"SM_LB_Tw_{stg}_{face}" + ("_BrokenSW" if stg == "S3" and face in "WS" else "")
        slots = ["MAT_Masonry", "MAT_Trim"] + (["MAT_Rubble"] if "Broken" in name else [])
        note = f"face {face}, stage {stg} z {z0:g}-{z0 + H:g}; " + OPENINGS.get((stg, face), "two belfry lancets (130 clear, sill z 200, apex z 762.6)")
        if "Broken" in name:
            note += "; wall top is a jagged stepped break (stepped_profile seed %d, 6-9 steps)" % (1003 if face == "W" else 1004)
        piece(name, TWM, ((-proj, 0.0, 0.0), (L + proj, 40.0 + proj, H)), slots, 1001 + si * 4 + fi,
              "local (0,0,0) = inner face start, z 0 = stage base; local x along the face, y 0 = inner face / 40 = outer face", "none", note)
        WALL_MB[(stg, face)] = name

P_FLIGHT = piece("SM_LB_Tw_StairFlight_250x420", TWM, ((-10.0, 0.0, -10.0), (430.0, 258.0, 257.0)), ["MAT_Wood", "MAT_Iron"], 1101,
                 "flight frame: x along the climb 0-420 (tread i at 30i..30i+30), y core side 0 -> wall side 250, z 0 = flight base", "none",
                 "14 oak treads 6 thick (tops 16.2338(i+1)), open risers, 2 stringers, 3 wall brackets")
P_FLIGHT_C = piece("SM_LB_Tw_StairFlight_250x420_Closed", TWM, ((-10.0, 0.0, 0.0), (430.0, 258.0, 257.0)), ["MAT_Wood", "MAT_Iron"], 1101,
                   "flight frame", "none", "T1 plus riser boards and side panels down to z 0 (F01 only)")
P_FLIGHT_A = piece("SM_LB_Tw_StairFlight_250x420_BrokenA", TWM, ((-10.0, 0.0, -10.0), (430.0, 258.0, 257.0)), ["MAT_Wood", "MAT_Iron"], 1102,
                   "flight frame", "none", "tread 6 lacks y 210-250, tread 10 split at y 120 (F03, F09)")
P_FLIGHT_B = piece("SM_LB_Tw_StairFlight_250x420_BrokenB", TWM, ((-10.0, 0.0, -10.0), (430.0, 258.0, 257.0)), ["MAT_Wood", "MAT_Iron"], 1103,
                   "flight frame", "none", "tread 3 lacks y 210-250, tread 9 cracked at y 80 (F06)")
P_RAIL = piece("SM_LB_Tw_FlightRail_420", TWM, ((0.0, 0.0, 58.2), (420.0, 10.0, 341.5)), ["MAT_Wood"], 1104,
               "flight frame; rail band y 0-10 (envelope of the 8-wide posts and handrail)", "none",
               "posts 8x8 at x 140 and 280, handrail top z = 16.2338(x/30+1)+98, mid-rail 50 lower")
P_LANDING = piece("SM_LB_Tw_Landing_250", TWM, ((0.0, 0.0, -60.0), (250.0, 250.0, 0.0)), ["MAT_Wood", "MAT_Masonry"], 1105,
                  "top-surface min corner (top z = 0); x 0-250, y 0-250; x = 250 and y = 250 are the wall sides", "none",
                  "boards 5 thick, 4 joists, 2+2 stone corbels (z -60..-25) at the wall sides")
P_SHAFTBASE = piece("SM_LB_Tw_ShaftBase_420x420x450", TWM, ((-210.0, -210.0, 0.0), (210.0, 210.0, 450.0)),
                    ["MAT_Masonry", "MAT_Trim", "MAT_Rubble", "MAT_Wood"], 1106, "bottom centre", "none (the invisible Tw_Core collides)",
                    "hollow square 420 outer, 35 thick walls, Z 0-450, coping z 430-450 projecting 3 inward only, rubble floor z 0-40")
P_POST = piece("SM_LB_Tw_ShaftPost_20x20x2015", TWM, ((-10.0, -10.0, 0.0), (10.0, 10.0, 2015.0)), ["MAT_Wood", "MAT_Iron"], 1107,
               "bottom centre", "none", "oak post with iron splice plates at z 670 and 1340 and a cap plate")
P_BELFRYFLOOR = piece("SM_LB_Tw_BelfryFloor", TWM, ((0.0, 0.0, -35.0), (680.0, 920.0, 0.0)), ["MAT_Wood", "MAT_Iron"], 1108,
                      "local (0,0,0) = world (12040, 1540, 2500), top at z 0",
                      "none", "W slab x0-250 y0-920, N slab x250-670 y670-920, core top x250-670 y250-670, rope hole x490-520 y280-310, beams to x 680")
P_TOPRAIL_670 = piece("SM_LB_Tw_TopRail_670", TWM, ((0.0, -5.0, 0.0), (670.0, 5.0, 98.0)), ["MAT_Wood"], None,
                      "rail start on its centre line at floor level; x along the rail", "none", "posts 10x10 every <= 120, handrail top 98, mid-rail top 50")
P_TOPRAIL_420 = piece("SM_LB_Tw_TopRail_420", TWM, ((0.0, -5.0, 0.0), (420.0, 5.0, 98.0)), ["MAT_Wood"], None,
                      "rail start on its centre line at floor level; x along the rail", "none", "as _670")
P_PARTITION = piece("SM_LB_Tw_Partition_250x455", TWM, ((0.0, 0.0, 0.0), (250.0, 4.0, 455.0)), ["MAT_Wood", "MAT_Iron"], 1109,
                    "min corner; x 250 wide, y thickness 0-4, z 455", "none", "vertical boards, 2 rails, one board missing at x 150-170")
P_LOUVRE = piece("SM_LB_Tw_Louvre_130x450", TWM, ((-65.0, 0.0, 0.0), (65.0, 30.0, 450.0)), ["MAT_Wood"], None,
                 "bottom centre of the opening on the inner face (local y 0)", "none", "nine 130x30x3 boards sloping 40 deg, spaced 50 from z 25, two side cleats")
P_LOUVRE_B = piece("SM_LB_Tw_Louvre_130x450_Broken", TWM, ((-65.0, 0.0, 0.0), (65.0, 30.0, 450.0)), ["MAT_Wood"], None,
                   "as the intact louvre", "none", "boards 3 and 4 missing, board 5 hangs at 70 deg")
P_BELLFRAME = piece("SM_LB_Tw_BellFrame_A", TWM, ((-165.0, -147.5, 0.0), (165.0, 147.5, 380.0)), ["MAT_Wood", "MAT_Iron"], 1110,
                    "floor point under the bell axis", "4 boxes (the posts only)",
                    "4 oak posts 25x25 z 0-365 at (+-140, +-135); sills x -165..165; head sills z 335-365; cross-ties; braces; bearing blocks to z 380")
P_HEADSTOCK = piece("SM_LB_Tw_BellHeadstock_A", TWM, ((-130.0, -175.0, -130.0), (130.0, 165.0, 130.0)), ["MAT_Wood", "MAT_Iron"], 1111,
                    "axle centre", "none", "headstock 35x35 along y -150..150, gudgeons, straps, bell wheel O 260 in the plane y -170 (6 spokes)")
P_GREATBELL = piece("SM_LB_Prop_GreatBell_A", TWM, ((-105.0, -105.0, -220.0), (105.0, 105.0, 0.0)), ["MAT_Bronze", "MAT_Iron"], 1112,
                    "crown top centre, the bell hangs along -z", "1 convex hull of the outer profile",
                    "lathe: canons z 0..-20, crown O110 at -20, shoulder O130 at -35, waist O150 at -120, sound bow O196 at -200, lip O210 at -220; crack on -x, V-chip")
P_ROPE = piece("SM_LB_Prop_BellRope_2610", TWM, ((-6.5, -6.5, -2610.0), (6.5, 6.5, 0.0)), ["MAT_Rope", "MAT_Sally"], None,
               "top", "none", "O 3.5 rope z 0..-2610 with 2 cm sway, sally O 9 x 100 at z -2410..-2510")
P_ROOF = piece("SM_LB_Tw_Roof_BrokenSW", TWM, ((-525.0, -525.0, -300.0), (525.0, 525.0, 1292.0)), ["MAT_Slate", "MAT_Wood", "MAT_Iron"], 1113,
               "bottom centre at the wall top: world (12500, 2000, 3540)", "none",
               "pyramid eaves +-525 at z -10 to apex z 1200, cross finial 90 tall bent 20 deg toward +x; SW quarter missing (-x face y -525..-100, -y face x -525..-100, up to z 860); hanging rafter to z -300")

P_FLOORSLAB = existing(KIT, "SM_LB_Kit_Floor_Slab_1000x1000x40")


def tw_face_record(rid, face, piece_name, x, z0, group, folder, cat="tower", extras=None, note="", mi=None, collision="NoCollision", scale=(1, 1, 1)):
    org, yaw, _ = TW_FACES[face]
    xy = frame_pt(org, yaw, x, 0.0)
    return add(rid, cat, group, PIECES[piece_name]["path"], (xy[0], xy[1], z0), (0.0, yaw, 0.0), scale, collision, folder, mi=mi, note=note,
               extras=extras)


# ---- shell wall pieces (12)
for (stg, face), name in WALL_MB.items():
    z0 = next(s[1] for s in STAGES if s[0] == stg)
    p = PIECES[name]
    tw_face_record(f"TWA_{stg}_{face}", face, name, 0.0, z0, "shell", "BellTower/Art/Shell", mi=mi_for(p["slots"]),
                   note=p["note"], extras={"stage": stg, "face_frame": face, "seed": p["seed"], "courses": list(COURSES),
                                            "lancets_x": list(LANCETS[face]) if stg == "S3" else None,
                                            "break_seed": (1003 if face == "W" else 1004) if "Broken" in name else None})

# ---- floor
add("TWA_Floor", "floor", "floor", P_FLOORSLAB, (12000.0, 1540.0, -38.5), (0, 0, 0), (0.96, 0.92, 1.0), "NoCollision", "BellTower/Art/Floor",
    mi={"MAT_Masonry": "MI_Chapel_Floor_Dirty"}, note="tower floor, also covers the door threshold (X 12000-12960, Y 1540-2460)")

# ---- flights, rails (T1, T2)
RINGS = [("N", (12290.0, 2210.0), 0.0), ("E", (12710.0, 2210.0), -90.0), ("S", (12710.0, 1790.0), 180.0), ("W", (12290.0, 1790.0), 90.0)]
FLIGHT_MESH = {1: P_FLIGHT_C, 3: P_FLIGHT_A, 9: P_FLIGHT_A, 6: P_FLIGHT_B}
FLIGHTS = {}
for k in range(1, 12):
    ring, org, yaw = RINGS[(k - 1) % 4]
    base = (k - 1) * RISE_F
    mesh = FLIGHT_MESH.get(k, P_FLIGHT)
    FLIGHTS[k] = (ring, org, yaw, base)
    add(f"TWA_Flight_F{k:02d}", "stair", "flight", mesh, (org[0], org[1], base), (0.0, yaw, 0.0), (1, 1, 1), "NoCollision", "BellTower/Art/Stairs",
        mi=mi_for(["MAT_Wood", "MAT_Iron"]), note=f"{ring} ring, base Z {base:.3f}; treads top = base + 16.2338 (i+1)",
        extras={"ring": ring, "heading": {"N": "+X", "E": "-Y", "S": "-X", "W": "+Y"}[ring], "base_z": round(base, 4)})
    add(f"TWA_FlightRail_F{k:02d}", "stair", "flightrail", P_RAIL, (org[0], org[1], base), (0.0, yaw, 0.0), (1, 1, 1),
        "NoCollision", "BellTower/Art/Rails", mi=mi_for(["MAT_Wood"]), note="inner balustrade on the rail plane, 10 cm outside the core face",
        extras={"ring": ring})

# ---- landings (T3)
LAND_CORNER = {1: ("NE", (12710.0, 2210.0), 0.0), 2: ("SE", (12710.0, 1790.0), -90.0), 3: ("SW", (12290.0, 1790.0), 180.0), 0: ("NW", (12290.0, 2210.0), 90.0)}
LANDINGS = {}
for n in range(1, 11):
    corner, pt, yaw = LAND_CORNER[n % 4]
    top = n * RISE_F
    LANDINGS[n] = (corner, pt, yaw, top)
    add(f"TWA_Landing_{n:02d}", "stair", "landing", P_LANDING, (pt[0], pt[1], top), (0.0, yaw, 0.0), (1, 1, 1), "NoCollision",
        "BellTower/Art/Landings", mi=mi_for(["MAT_Wood", "MAT_Masonry"]), note=f"{corner} corner, top Z {top:.3f}", extras={"corner": corner})

# ---- shaft base, posts, belfry floor, top rails, partition
add("TWA_ShaftBase", "tower", "shaftbase", P_SHAFTBASE, (12500.0, 2000.0, 0.0), (0, 0, 0), (1, 1, 1), "NoCollision", "BellTower/Art/Shaft",
    mi=mi_for(PIECES["SM_LB_Tw_ShaftBase_420x420x450"]["slots"]), note="stone shaft base over the invisible core, outer faces on the core faces (Z 0-450)")
for cname, (cx, cy) in (("SW", (12290.0, 1790.0)), ("SE", (12710.0, 1790.0)), ("NE", (12710.0, 2210.0)), ("NW", (12290.0, 2210.0))):
    add(f"TWA_ShaftPost_{cname}", "tower", "shaftpost", P_POST, (cx, cy, 450.0), (0, 0, 0), (1, 1, 1), "NoCollision", "BellTower/Art/Shaft",
        mi=mi_for(["MAT_Wood", "MAT_Iron"]), note="oak post on the core corner, Z 450-2465")
add("TWA_BelfryFloor", "tower", "belfryfloor", P_BELFRYFLOOR, (12040.0, 1540.0, 2500.0), (0, 0, 0), (1, 1, 1), "NoCollision", "BellTower/Art/Belfry",
    mi=mi_for(["MAT_Wood", "MAT_Iron"]), note="belfry floor boards over the W slab, N slab and core top; rope hole X 12530-12560, Y 1820-1850")
add("TWA_TopRail_670", "tower", "toprail", P_TOPRAIL_670, (12700.0, 1790.0, 2500.0), (0.0, 90.0, 0.0), (1, 1, 1), "NoCollision", "BellTower/Art/Belfry",
    mi=mi_for(["MAT_Wood"]), note="runs Y 1790 -> 2460 along the core E edge")
add("TWA_TopRail_420", "tower", "toprail", P_TOPRAIL_420, (12290.0, 1800.0, 2500.0), (0, 0, 0), (1, 1, 1), "NoCollision", "BellTower/Art/Belfry",
    mi=mi_for(["MAT_Wood"]), note="runs X 12290 -> 12710 along the core S edge")
add("TWA_Partition", "tower", "partition", P_PARTITION, (12290.0, 1790.0, 0.0), (0.0, -90.0, 0.0), (1, 1, 1), "NoCollision", "BellTower/Art/Shaft",
    mi=mi_for(["MAT_Wood", "MAT_Iron"]), note="board partition closing the ground ring under F02/F03; local x runs Y 1790 -> 1540, y 0-4 -> X 12290-12294")

# ---- louvres (T9) at the eight belfry lancets
for face in "WNES":
    for j, xc in enumerate(LANCETS[face]):
        broken = (face == "N" and j == 0) or (face == "E" and j == 1)
        name = "SM_LB_Tw_Louvre_130x450_Broken" if broken else "SM_LB_Tw_Louvre_130x450"
        tw_face_record(f"TWA_Louvre_{face}{j + 1}", face, name, xc, 2700.0, "louvre", "BellTower/Art/Belfry", mi=mi_for(["MAT_Wood"]),
                       note=f"lancet centred x {xc:g} on the {face} face, sill z 200 (world 2700)", extras={"face_frame": face, "lancet_x": xc})

# ---- bell frame, headstock, great bell (via BP), rope, roof
add("TWA_BellFrame", "tower", "bellframe", P_BELLFRAME, (12420.0, 2000.0, 2500.0), (0, 0, 0), (1, 1, 1), "BlockAll (4 post UCX)", "BellTower/Art/Belfry",
    mi=mi_for(["MAT_Wood", "MAT_Iron"]), note="oak bell frame over the core top and W slab")
add("TWA_Headstock", "tower", "headstock", P_HEADSTOCK, (12420.0, 2000.0, 2880.0), (0, 0, 0), (1, 1, 1), "NoCollision", "BellTower/Art/Belfry",
    mi=mi_for(["MAT_Wood", "MAT_Iron"]), note="axle along Y at Z 2880; bell wheel in the plane Y 1830")
add("TWA_GreatBell", "gameplay", "greatbell", P_GREATBELL, (12420.0, 2000.0, 2860.0), (0, 0, 0), (1, 1, 1), "BlockAll (convex hull)", "Gameplay/BellTower",
    mi=mi_for(["MAT_Bronze", "MAT_Iron"]),
    note="REFERENCE ONLY: placed through BP_TagInteractable_GreatBell (D1.6.5): Mesh rel (0,0,94) scale 0.4 under root scale 2.5 -> world scale 1; "
         "expected bounds X 12315-12525, Y 1895-2105, Z 2640-2860", extras={"via_bp": "BP_TagInteractable_GreatBell", "skip_place": True})
add("TWA_BellRope", "tower", "rope", P_ROPE, (12550.0, 1830.0, 2750.0), (0, 0, 0), (1, 1, 1), "NoCollision", "BellTower/Art/Belfry",
    mi=mi_for(["MAT_Rope", "MAT_Sally"]), note="rope in the wheel plane, through the floor hole, Z 2750 down to 140; sally at Z 340-240")
add("TWA_Roof", "roof", "towerroof", P_ROOF, (12500.0, 2000.0, 3540.0), (0, 0, 0), (1, 1, 1), "NoCollision", "BellTower/Art/Roof",
    mi=mi_for(["MAT_Slate", "MAT_Wood", "MAT_Iron"]), note="steep pyramidal slate roof, apex Z 4740, SW quarter collapsed")

# ---- hidden collision blocks (D1.0), tower and cloister
BLOCKS = [   # id, min, max, folder, why
    ("Tw_Block_UnderStair", (12290, 1540, 0), (12300, 1790, 454.5), "BellTower/Blocks", "closes the ground ring under F02/F03 (A2)"),
    ("Tw_Block_BrokenTread_F03", (12500, 1540, 568.2), (12530, 1580, 768.2), "BellTower/Blocks", "over the missing end of F03 tread 6"),
    ("Tw_Block_BrokenTread_F06", (12920, 2090, 1201.3), (12960, 2120, 1401.3), "BellTower/Blocks", "over the missing end of F06 tread 3"),
    ("Tw_Block_BrokenTread_F09", (12470, 2420, 1931.8), (12500, 2460, 2131.8), "BellTower/Blocks", "over the missing end of F09 tread 6"),
    ("Cl_Block_PierSW", (10210, 1310, 0), (10260, 1390, 330), "Cloister/Blocks", "corner-pier extension"),
    ("Cl_Block_PierSE", (11440, 1310, 0), (11490, 1390, 330), "Cloister/Blocks", "corner-pier extension"),
    ("Cl_Block_PierNW", (10210, 2210, 0), (10260, 2290, 330), "Cloister/Blocks", "corner-pier extension"),
    ("Cl_Block_PierNE", (11440, 2210, 0), (11490, 2290, 330), "Cloister/Blocks", "corner-pier extension"),
]
for bid, bmn, bmx, bfolder, why in BLOCKS:
    c = [(bmn[k] + bmx[k]) / 2.0 for k in range(3)]
    sc = [(bmx[k] - bmn[k]) / 100.0 for k in range(3)]
    add(bid, "block", "block", CUBE, c, (0, 0, 0), sc, "hidden-block", bfolder, note=why + " (BlockAll, not visible, engine cube)",
        extras={"visible": False, "target_min": list(bmn), "target_max": list(bmx)})


# =====================================================================================================
# D1.3  CLOISTER, PASSAGE, STAIR-HOUSE
# =====================================================================================================
MASONRY2 = ["MAT_Masonry", "MAT_Trim"]
for nm, sd in (("A", 1201), ("B", 1202)):
    piece(f"SM_LB_Cl_Wall40_400x1300_{nm}", CLM, ((0.0, -6.0, 0.0), (400.0, 40.0, 1300.0)), MASONRY2, sd,
          "bottom-left-back; local x along the face, y 0 = inner face, 40 = outer; drip course z 1210-1230 proj 6 on the inner face", "none", "C1")
piece("SM_LB_Cl_Wall40_100x1300", CLM, ((0.0, -6.0, 0.0), (100.0, 40.0, 1300.0)), MASONRY2, 1203, "as C1", "none", "C1 (used only when a run is < 300 long)")
for nm, sd in (("A", 1204), ("B", 1205)):
    piece(f"SM_LB_Cl_Wall40_400x800_{nm}", CLM, ((0.0, 0.0, 0.0), (400.0, 40.0, 800.0)), MASONRY2, sd, "as C1", "none", "C2 passage, no drip course")
piece("SM_LB_Cl_Wall40_100x800", CLM, ((0.0, 0.0, 0.0), (100.0, 40.0, 800.0)), MASONRY2, 1206, "as C1", "none", "C2")
piece("SM_LB_Cl_Wall40_400x450", CLM, ((0.0, 0.0, 0.0), (400.0, 40.0, 450.0)), MASONRY2, 1207, "as C1", "none", "C3 stair-house")
piece("SM_LB_Cl_Wall40_100x450", CLM, ((0.0, 0.0, 0.0), (100.0, 40.0, 450.0)), MASONRY2, 1208, "as C1", "none", "C3")
piece("SM_LB_Cl_Archway_500x40x1300", CLM, ((0.0, -6.0, 0.0), (500.0, 40.0, 1300.0)), MASONRY2, 1209,
      "bottom-left-back; local y 0 on the cloister side", "none", "C4 four-centred arch, springing z 300 at x 0 and 500, apex z 420, voussoir ring MAT_Trim, drip course on the cloister face")
piece("SM_LB_Cl_Archway_300x40x1300", CLM, ((0.0, -6.0, 0.0), (300.0, 40.0, 1300.0)), MASONRY2, 1210, "as C4", "none", "C5 springing z 330, apex z 450")
piece("SM_LB_Cl_Pier_80x80x640", CLM, ((-48.0, -48.0, 0.0), (48.0, 48.0, 620.0)), MASONRY2, 1211, "bottom centre", "none",
      "C6: shaft z 25-300, base moulding z 0-25 (+4), bell capital z 300-330 (+8), wall block to z 600, coping z 600-620 (+5); the table gives the top at z 620 although the name says 640")
piece("SM_LB_Cl_PierCorner_130x80x640", CLM, ((-73.0, -48.0, 0.0), (73.0, 48.0, 620.0)), MASONRY2, 1212, "bottom centre of the 130x80 plan", "none", "C7")
for span, sd in ((120, 1213), (170, 1214), (220, 1215), (270, 1216)):
    piece(f"SM_LB_Cl_ArcadeArch_{span}x80", CLM, ((0.0, -45.0, 0.0), (float(span), 45.0, 290.0)), MASONRY2, sd,
          "local (0,0,0) = left springing point on the pier line; x 0..span, y -40..40 (+5 coping), z 0..290 (world 330-620)", "none",
          "C8 two-centred pointed arch, radius 0.8 span, voussoir ring MAT_Trim, spandrel to z 270, coping z 270-290 (+5)")
piece("SM_LB_Cl_GarthWall_1100x100", CLM, ((0.0, -4.0, 0.0), (1100.0, 30.0, 100.0)), MASONRY2, 1217,
      "local y 0 = face toward the walk; body to y +15 (garth side); coping z 88-100 spans y -4..+30", "none", "C9")
piece("SM_LB_Cl_GarthWall_800x100", CLM, ((0.0, -4.0, 0.0), (800.0, 30.0, 100.0)), MASONRY2, 1218, "as C9", "none", "C9")
piece("SM_LB_Cl_GarthBed_1100x800", CLM, ((0.0, 0.0, -4.0), (1100.0, 800.0, 10.0)), ["MAT_Earth"], 1219, "min corner, z 0 = garth top", "none",
      "C10 earth surface with 2-10 cm mounds and six shallow grave hollows (bed-local centres in extras.hollows)")
piece("SM_LB_Cl_GraveSlab_200x80", CLM, ((-100.0, -40.0, 0.0), (100.0, 40.0, 8.0)), ["MAT_Masonry"], 1220,
      "bottom centre (ASSUMED: C11 gives no pivot, D1 convention for props)", "none", "C11 slab 200x80x8 with chamfers and a worn cross relief")
piece("SM_LB_Cl_GraveCross_60", CLM, ((-18.0, -4.0, 0.0), (18.0, 4.0, 60.0)), ["MAT_Masonry"], 1221, "bottom centre (ASSUMED)", "none", "C11 small stone cross 60 tall, 8 thick (arm span assumed 36)")
piece("SM_LB_Cl_GarthCross_350", CLM, ((-60.0, -60.0, 0.0), (60.0, 60.0, 350.0)), ["MAT_Masonry"], 1222, "bottom centre (ASSUMED)", "none",
      "C11 stepped base 120x120x20 + 90x90x20, chamfered shaft 24x24 to z 290, cross head 90 wide")
for nm, mb, sd, nt in (("830x640", (640.0, 830.0), 1225, "Barrel"), ("770x640", (640.0, 770.0), 1226, "Barrel"), ("770x640_Broken", (640.0, 770.0), 1227, "Barrel"),
                       ("770x980", (980.0, 770.0), 1228, "Barrel"), ("570x980", (980.0, 570.0), 1229, "Barrel")):
    piece(f"SM_LB_Cl_Vault_Barrel_{nm}", CLM, ((0.0, 0.0, 0.0), (mb[0], mb[1], 365.0)), MASONRY2, sd,
          "min corner at the springing level; name = span x length; local x along the walk (length), y across (span)", "none",
          "C12 four-centred barrel, soffit rise 340 (+25 shell), transverse ribs at x 0, L/2, L" + ("; hole x 50-600 and snapped mid rib" if "Broken" in nm else ""))
for nm, sz, sd in (("770x830", (770.0, 830.0), 1232), ("570x830", (570.0, 830.0), 1233), ("770x770", (770.0, 770.0), 1234), ("570x770", (570.0, 770.0), 1235)):
    piece(f"SM_LB_Cl_Vault_Groin_{nm}", CLM, ((0.0, 0.0, 0.0), (sz[0], sz[1], 365.0)), MASONRY2, sd,
          "min corner at the springing level; local x span x, y span y", "none", "C13 groin = two perpendicular barrels clipped to the square, diagonal and wall ribs")
piece("SM_LB_Cl_LeanTo_1000x1050", CLM, ((0.0, 0.0, -15.0), (1000.0, 1050.0, 9.0)), ["MAT_Slate", "MAT_Wood"], 1236,
      "eaves-line start; local x along the eaves, y up the slope in the panel plane, z the panel normal", "none", "C14 slates 6 on battens, rafters 12x15 at 60 c/c below")
piece("SM_LB_Cl_LeanTo_1000x1050_Hole", CLM, ((0.0, 0.0, -95.0), (1000.0, 1050.0, 9.0)), ["MAT_Slate", "MAT_Wood"], 1237, "as C14", "none",
      "C14 hole over x 150-850, y 0-800, broken battens, 3 snapped rafters (two stubs hanging 40-80)")
piece("SM_LB_Cl_CellDoorFrame_150x270", CLM, ((0.0, -8.0, 0.0), (150.0, 4.0, 270.0)), ["MAT_Masonry", "MAT_Rubble"], 1238,
      "bottom-left; local y 0 = wall face, frame projects to y -8", "none", "C15 surround 150x270, 20 jambs, straight-sided pointed head (shoulders z 220, apex 250), 110x250 opening, back panel at y +2")
piece("SM_LB_Cl_StairHouseGable_380x40x650", CLM, ((0.0, 0.0, 0.0), (380.0, 40.0, 650.0)), MASONRY2, 1239, "as the wall pieces (inner face at local y 0)", "none",
      "C16 triangular top from z 450 at the ends to 650 at the centre")
piece("SM_LB_Cl_StairHouseRoof_420x640", CLM, ((0.0, 0.0, 0.0), (420.0, 640.0, 208.0)), ["MAT_Slate", "MAT_Wood"], 1240, "min corner at the eaves level",
      "none", "C17 pitched roof, ridge along local y at x 210 z 200, 20 overhangs")
piece("SM_LB_Prop_SmallBell_A", CLM, ((-12.0, -12.0, -28.0), (12.0, 12.0, 4.0)), ["MAT_Bronze", "MAT_Iron", "MAT_Band"], 1301, "crown top, hangs along -z",
      "1 convex hull", "M1 lathe: lip O24 at -28, sound bow O22 at -25, waist O16 at -14, crown O10 at -3; loop z 0..4; painted band z -8..-5 (MAT_Band)")
piece("SM_LB_Prop_SmallBellBracket_A", CLM, ((0.0, -10.0, -25.0), (34.0, 10.0, 22.0)), ["MAT_Iron", "MAT_Wood"], 1302,
      "back face of the wall plate at the arm axis height, local +x out of the wall", "none", "M2")
piece("SM_LB_Prop_BellPlaque_A", CLM, ((0.0, -17.0, -17.0), (4.0, 17.0, 17.0)), ["MAT_Trim"], 1303, "back centre, front faces +x", "none", "M3 plaque 4x34x34")
piece("SM_LB_Prop_InscriptionTablet_A", CLM, ((0.0, -60.0, -15.0), (4.0, 60.0, 15.0)), ["MAT_Trim"], 1304, "back centre, front faces +x", "none",
      "M4 tablet 4x120x30 (x 2.5 root scale = 10x300x75)")

# ------------------------------------------------------------------ wall runs
RUNFR = {   # face-frame type -> yaw
    "S": 180.0, "N": 0.0, "W": 90.0, "E": -90.0}


def gbc(label, hi, axis):
    mn, mx = gb(label)
    return (mx if hi else mn)[axis]


# id, frame type, origin XY, length, height tag, folder, group, face check (axis, expected, source), prefix
RUNS = [
    ("S_W", "S", (10500.0, 540.0), 1040.0, 1300, "Cloister/Art/Walls", (1, gbc("Cl_S1", True, 1), "Cl_S1 max Y")),
    ("S_E", "S", (12040.0, 540.0), 1240.0, 1300, "Cloister/Art/Walls", (1, gbc("Cl_S2", True, 1), "Cl_S2 max Y")),
    ("N", "N", (9460.0, 3000.0), 2580.0, 1300, "Cloister/Art/Walls", (1, gbc("Cl_N", False, 1), "Cl_N min Y")),
    ("W_S", "W", (9500.0, 540.0), 1210.0, 1300, "Cloister/Art/Walls", (0, gbc("Cl_W_S", True, 0), "Cl_W_S max X")),
    ("W_N", "W", (9500.0, 2250.0), 750.0, 1300, "Cloister/Art/Walls", (0, gbc("Cl_W_N", True, 0), "Cl_W_N max X")),
    ("E_S", "E", (12000.0, 1500.0), 960.0, 1300, "Cloister/Art/Walls", (0, gbc("Cl_E_S", False, 0), "Cl_E_S min X")),
    ("E_N", "E", (12000.0, 3000.0), 500.0, 1300, "Cloister/Art/Walls", (0, gbc("Cl_E_N", False, 0), "Cl_E_N min X")),
    ("PS", "S", (9460.0, 1700.0), 3420.0, 800, "Courtyard/Passage", (1, gbc("Passage_S", True, 1), "Passage_S max Y")),
    ("PN", "N", (6040.0, 2300.0), 3420.0, 800, "Courtyard/Passage", (1, gbc("Passage_N", False, 1), "Passage_N min Y")),
    ("SH_W", "W", (10500.0, -100.0), 600.0, 450, "Cloister/Art/StairHouse", (0, 10500.0, "Rail_Up_W max X (P9 F1)")),
    ("SH_E", "E", (10800.0, 500.0), 600.0, 450, "Cloister/Art/StairHouse", (0, 10800.0, "Rail_Up_E min X (P9 F1)")),
]
PREFIX_OF = {"Courtyard/Passage": "PSA", "Cloister/Art/StairHouse": "SHA", "Cloister/Art/Walls": "CLA"}
RUN_RECS = {}
for rid, ft, org, L, H, folder, fchk in RUNS:
    yaw = RUNFR[ft]
    n = 1 if L < 300 else int(math.floor(L / 400.0 + 0.5))
    if L < 300:
        names = [f"SM_LB_Cl_Wall40_100x{H}"]
        sx = L / 100.0
    else:
        names = [f"SM_LB_Cl_Wall40_400x{H}_A", f"SM_LB_Cl_Wall40_400x{H}_B"] if H != 450 else ["SM_LB_Cl_Wall40_400x450"]
        sx = L / (400.0 * n)
    RUN_RECS[rid] = []
    for i in range(n):
        nm = names[i % len(names)]
        xy = frame_pt(org, yaw, i * L / n, 0.0)
        d = add(f"{PREFIX_OF[folder]}_Wall_{rid}_{i}", "wall", "wallpiece", PIECES[nm]["path"], (xy[0], xy[1], 0.0), (0.0, yaw, 0.0), (sx, 1.0, 1.0),
                "NoCollision", folder, mi=mi_for(PIECES[nm]["slots"]),
                note=f"run {rid}: {n} x 400 pieces scaled x{sx:.4f}, frame {ft} origin {org}, length {L:g}",
                extras={"run": rid, "piece": i, "frame": ft, "frame_origin": list(org), "face_check": list(fchk)})
        RUN_RECS[rid].append(d)

# archways
add("CLA_Archway_W", "wall", "archway", PIECES["SM_LB_Cl_Archway_500x40x1300"]["path"], (9500.0, 1750.0, 0.0), (0.0, 90.0, 0.0), (1, 1, 1), "NoCollision",
    "Cloister/Art/Walls", mi=mi_for(MASONRY2), note="W archway Y 1750-2250 (greybox opening 500 x 400), W-type frame at X 9500, local y 0 on the cloister side",
    extras={"run": "W_ARCH", "frame": "W", "face_check": [0, gbc("Cl_W_S", True, 0), "Cl_W_S max X"]}, lane_zlo=300.0)
add("CLA_Archway_S", "wall", "archway", PIECES["SM_LB_Cl_Archway_300x40x1300"]["path"], (10800.0, 540.0, 0.0), (0.0, 180.0, 0.0), (1, 1, 1), "NoCollision",
    "Cloister/Art/Walls", mi=mi_for(MASONRY2), note="S archway X 10500-10800 over the crypt exit, S-type frame at Y 540",
    extras={"run": "S_ARCH", "frame": "S", "face_check": [1, gbc("Cl_S1", True, 1), "Cl_S1 max Y"]}, lane_zlo=330.0)

# stair-house gable and roof
add("SHA_Gable_S", "wall", "wallpiece", PIECES["SM_LB_Cl_StairHouseGable_380x40x650"]["path"], (10840.0, -100.0, 0.0), (0.0, 180.0, 0.0), (1, 1, 1), "NoCollision",
    "Cloister/Art/StairHouse", mi=mi_for(MASONRY2), note="south gable X 10460-10840, Y -140..-100, inner face at Y -100",
    extras={"run": "SH_GABLE", "frame": "S", "face_check": [1, -100.0, "Rail_Up_S max Y (P9 F1)"]})
add("SHA_Roof", "roof", "stairhouseroof", PIECES["SM_LB_Cl_StairHouseRoof_420x640"]["path"], (10440.0, -140.0, 450.0), (0, 0, 0), (1, 1, 1), "NoCollision",
    "Cloister/Art/StairHouse", mi=mi_for(["MAT_Slate", "MAT_Wood"], wood=WOOD_CLOISTER), note="slate roof over the stair trench, Y -140..500, abuts the cloister S wall")

# ------------------------------------------------------------------ arcade
PIER_SRC = {"S1": (10600.0, 1350.0), "S2": (10900.0, 1350.0), "S3": (11200.0, 1350.0), "N1": (10600.0, 2250.0), "N2": (10900.0, 2250.0), "N3": (11200.0, 2250.0),
            "W0": (10250.0, 1700.0), "W1": (10250.0, 2000.0), "E0": (11450.0, 1700.0), "E1": (11450.0, 2000.0)}
for pid, (px, py) in PIER_SRC.items():
    add(f"CLA_Pier_{pid}", "arcade", "pier", PIECES["SM_LB_Cl_Pier_80x80x640"]["path"], (px, py, 0.0), (0, 0, 0), (1, 1, 1), "NoCollision", "Cloister/Art/Arcade",
        mi=mi_for(MASONRY2), note=f"over greybox Arc_{pid}", extras={"greybox": f"Arc_{pid}"})
for cid, (px, py) in (("SW", (10275.0, 1350.0)), ("SE", (11425.0, 1350.0)), ("NW", (10275.0, 2250.0)), ("NE", (11425.0, 2250.0))):
    add(f"CLA_PierCorner_{cid}", "arcade", "pier_corner", PIECES["SM_LB_Cl_PierCorner_130x80x640"]["path"], (px, py, 0.0), (0, 0, 0), (1, 1, 1), "NoCollision",
        "Cloister/Art/Arcade", mi=mi_for(MASONRY2),
        note=f"corner compound pier over Arc_{ 'S' if cid[0] == 'S' else 'N'}{0 if cid[1] == 'W' else 4} + Cl_Block_Pier{cid}")
ARCH_X = [(220, 10340.0), (220, 10640.0), (220, 10940.0), (120, 11240.0)]
for row, y in (("S", 1350.0), ("N", 2250.0)):
    for i, (span, x) in enumerate(ARCH_X):
        add(f"CLA_Arch_{row}_{i}", "arcade", "arch", PIECES[f"SM_LB_Cl_ArcadeArch_{span}x80"]["path"], (x, y, 330.0), (0, 0, 0), (1, 1, 1), "NoCollision",
            "Cloister/Art/Arcade", mi=mi_for(MASONRY2), note=f"{row} row, left springing X {x:g}, span {span}")
for col, x in (("W", 10250.0), ("E", 11450.0)):
    for i, (span, y) in enumerate(((270, 1390.0), (220, 1740.0), (170, 2040.0))):
        add(f"CLA_Arch_{col}_{i}", "arcade", "arch", PIECES[f"SM_LB_Cl_ArcadeArch_{span}x80"]["path"], (x, y, 330.0), (0.0, 90.0, 0.0), (1, 1, 1), "NoCollision",
            "Cloister/Art/Arcade", mi=mi_for(MASONRY2), note=f"{col} column, left springing Y {y:g}, span {span}")

# ------------------------------------------------------------------ garth
for gid, mesh, org, yaw in (("S", "1100", (10300.0, 1400.0), 0.0), ("N", "1100", (11400.0, 2200.0), 180.0), ("W", "800", (10300.0, 2200.0), -90.0),
                            ("E", "800", (11400.0, 1400.0), 90.0)):
    add(f"CLA_GarthWall_{gid}", "garth", "garthwall", PIECES[f"SM_LB_Cl_GarthWall_{mesh}x100"]["path"], (org[0], org[1], 0.0), (0.0, yaw, 0.0), (1, 1, 1), "NoCollision",
        "Cloister/Art/Garth", mi=mi_for(MASONRY2), note="retaining wall flush with the Garth block, top exactly Z 100 (Note_Cloister rests on the S coping)")
GRAVES = [(10500.0, 1600.0), (10500.0, 2000.0), (10700.0, 1650.0), (11000.0, 2000.0), (11200.0, 1600.0), (11200.0, 1950.0)]
add("CLA_GarthBed", "garth", "garthbed", PIECES["SM_LB_Cl_GarthBed_1100x800"]["path"], (10300.0, 1400.0, 100.0), (0, 0, 0), (1, 1, 1), "NoCollision",
    "Cloister/Art/Garth", mi={"MAT_Earth": "MI_Prop_Earth"}, note="earth surface on the Garth top (Z 100)",
    extras={"hollows_bed_local": [[gx - 10300.0, gy - 1400.0] for gx, gy in GRAVES]})
jit = random.Random(1223)
SLAB_ROT = []
for i, (gx, gy) in enumerate(GRAVES):
    rot = (0.0, round(jit.uniform(-4.0, 4.0), 2), round(jit.choice((-1.0, 1.0)) * jit.uniform(1.0, 3.0), 2))
    SLAB_ROT.append(rot)
    add(f"CLA_GraveSlab_{i}", "garth", "graveslab", PIECES["SM_LB_Cl_GraveSlab_200x80"]["path"], (gx, gy, 100.0), rot, (1, 1, 1), "NoCollision",
        "Cloister/Art/Garth", mi=mi_for(["MAT_Masonry"]), note="grave slab, yaw 0 +-4 deg and 1-3 deg roll (seed 1223)")
for i, (gx, gy) in enumerate(((10450.0, 1500.0), (11250.0, 1500.0), (10450.0, 2100.0), (11250.0, 2100.0))):
    add(f"CLA_GraveCross_{i}", "garth", "gravecross", PIECES["SM_LB_Cl_GraveCross_60"]["path"], (gx, gy, 100.0), (0.0, 0.0, 0.0), (1, 1, 1), "NoCollision",
        "Cloister/Art/Garth", mi=mi_for(["MAT_Masonry"]), note="small stone cross")
add("CLA_GarthCross", "garth", "garthcross", PIECES["SM_LB_Cl_GarthCross_350"]["path"], (10850.0, 1800.0, 100.0), (0.0, 15.0, 0.0), (1, 1, 1), "NoCollision",
    "Cloister/Art/Garth", mi=mi_for(["MAT_Masonry"]), note="3.5 m stone cross, yaw 15")

# ------------------------------------------------------------------ vaults
VAULT_BAYS = [   # id, piece, min-corner location, yaw, note
    ("S_W", "Barrel_830x640", (10210.0, 510.0, 560.0), 0.0, "S walk west"),
    ("S_E", "Barrel_830x640", (10850.0, 510.0, 560.0), 0.0, "S walk east"),
    ("N_W", "Barrel_770x640", (10210.0, 2260.0, 560.0), 0.0, "N walk west"),
    ("N_E", "Barrel_770x640_Broken", (10850.0, 2260.0, 560.0), 0.0, "N walk east: the collapse"),
    ("W", "Barrel_770x980", (10240.0, 1310.0, 560.0), 90.0, "W walk: local x -> +Y (1310-2290), local y -> -X (10240 -> 9470)"),
    ("E", "Barrel_570x980", (12030.0, 1310.0, 560.0), 90.0, "E walk: local y -> -X (12030 -> 11460)"),
    ("SW", "Groin_770x830", (9470.0, 510.0, 560.0), 0.0, "SW corner"),
    ("SE", "Groin_570x830", (11460.0, 510.0, 560.0), 0.0, "SE corner"),
    ("NW", "Groin_770x770", (9470.0, 2260.0, 560.0), 0.0, "NW corner"),
    ("NE", "Groin_570x770", (11460.0, 2260.0, 560.0), 0.0, "NE corner"),
]
for vid, pn, loc, yaw, note in VAULT_BAYS:
    nm = f"SM_LB_Cl_Vault_{pn}"
    add(f"CLA_Vault_{vid}", "vault", "vaultbay", PIECES[nm]["path"], loc, (0.0, yaw, 0.0), (1, 1, 1), "NoCollision", "Cloister/Art/Vaults",
        mi=mi_for(MASONRY2), note=note + "; springing Z 560, crown Z 900", extras={"kind": "groin" if "Groin" in pn else "barrel"})

# ------------------------------------------------------------------ corbels (under every rib end on the outer walls; top Z 560)
KIT_CORBEL = existing(KIT, "SM_LB_Kit_Corbel_40x60x60")
CORBEL_RIBS = {   # outer wall frame -> (frame type, origin, list of world coordinates along the wall)
    "S": ("S", (12040.0, 540.0), 0, [10210.0, 10530.0, 10850.0, 11170.0, 11490.0]),
    "N": ("N", (9460.0, 3000.0), 0, [10210.0, 10530.0, 10850.0, 11170.0, 11490.0]),
    "W": ("W", (9500.0, 540.0), 1, [1310.0, 1800.0, 2290.0]),
    "E": ("E", (12000.0, 3000.0), 1, [1310.0, 1800.0, 2290.0]),
}
for wl, (ft, org, ax, coords) in CORBEL_RIBS.items():
    yaw = RUNFR[ft]
    for j, c in enumerate(coords):
        xf = {"S": org[0] - c, "N": c - org[0], "W": c - org[1], "E": org[1] - c}[ft]
        xy = frame_pt(org, yaw, xf - 20.0, -60.0)
        add(f"CLA_Corbel_{wl}_{j}", "wall", "corbel", KIT_CORBEL, (xy[0], xy[1], 500.0), (0.0, yaw, 0.0), (1, 1, 1), "NoCollision", "Cloister/Art/Corbels",
            mi=mi_for(["MAT_Trim"]), note=f"under the rib end at {('X' if ax == 0 else 'Y')} {c:g} on the {wl} wall, top Z 560 (kit corbel: free end local y 0, back local y 60)")
for cid, (cx, cy, sx_, sy_) in (("SW", (9500.0, 540.0, 1, 1)), ("SE", (12000.0, 540.0, -1, 1)), ("NW", (9500.0, 3000.0, 1, -1)), ("NE", (12000.0, 3000.0, -1, -1))):
    # diagonal rib springer in the inner corner; mesh local +y (back) points into the corner
    psi = math.degrees(math.atan2(sx_, -sy_))
    ox, oy = frame_pt((cx, cy), psi, -20.0, -60.0)   # placeholder, corrected below
    c, s = math.cos(math.radians(psi)), math.sin(math.radians(psi))
    # back-face centre (local 20, 60) must land on the corner
    org = (cx - (20.0 * c - 60.0 * s), cy - (20.0 * s + 60.0 * c))
    add(f"CLA_Corbel_{cid}", "wall", "corbel", KIT_CORBEL, (org[0], org[1], 500.0), (0.0, psi, 0.0), (1, 1, 1), "NoCollision", "Cloister/Art/Corbels",
        mi=mi_for(["MAT_Trim"]), note=f"diagonal rib springer in the {cid} inner corner, top Z 560")

# ------------------------------------------------------------------ roofs (C14), rotators from the eaves and top lines
LEAN = PIECES["SM_LB_Cl_LeanTo_1000x1050"]["path"]
LEAN_H = PIECES["SM_LB_Cl_LeanTo_1000x1050_Hole"]["path"]
EAVES_Z, TOP_Z = 640.0, 1200.0
ROOF_WALKS = {   # walk -> (eaves line coord, top line coord, run start, run end, axis of the line, h)
    "S": dict(eaves=1420.0, top=540.0, a=12000.0, b=9500.0, line_axis=1),   # panels start at X 12000 and run to 9500 (-X)
    "N": dict(eaves=2180.0, top=3000.0, a=9500.0, b=12000.0, line_axis=1),
    "W": dict(eaves=10320.0, top=9500.0, a=540.0, b=3000.0, line_axis=0),
    "E": dict(eaves=11380.0, top=12000.0, a=3000.0, b=540.0, line_axis=0),
}
ROOF_PANELS = {}
for walk, w in ROOF_WALKS.items():
    h = abs(w["top"] - w["eaves"])
    Ls = math.hypot(h, TOP_Z - EAVES_Z)
    run = w["b"] - w["a"]                       # signed
    sgn = 1.0 if run > 0 else -1.0
    ax = w["line_axis"]
    # x direction along the eaves (world), y direction up the slope (world)
    xd = [0.0, 0.0, 0.0]
    xd[1 - ax] = sgn
    yd = [0.0, 0.0, 0.0]
    yd[ax] = (w["top"] - w["eaves"]) / Ls
    yd[2] = (TOP_Z - EAVES_Z) / Ls
    zd = cross(xd, yd)
    assert zd[2] > 0, f"roof panel normal points down for walk {walk}"
    rot = rot_from_rows(tuple(xd), tuple(yd), tuple(zd))
    widths = [abs(run) / 3.0] * 3
    if walk == "N" and N_ROOF_FIX:
        widths = [1333.3333, 833.3333, 333.3333]   # proposed fix: the middle (hole) panel starts at X 10833 as D1.3 states
    pos = 0.0
    for j, wd in enumerate(widths):
        sx = wd / 1000.0
        sy = Ls / 1050.0
        org = [0.0, 0.0, EAVES_Z]
        org[ax] = w["eaves"]
        org[1 - ax] = w["a"] + sgn * pos
        mesh = LEAN_H if (walk == "N" and j == 1) else LEAN
        d = add(f"CLA_Roof_{walk}_{j}", "roof", "roofpanel", mesh, org, rot, (sx, sy, 1.0), "NoCollision", "Cloister/Art/Roofs",
                mi=mi_for(["MAT_Slate", "MAT_Wood"], wood=WOOD_CLOISTER),
                note=f"{walk} walk panel {j}: eaves line {'Y' if ax == 1 else 'X'} {w['eaves']:g} at Z 640, top line {w['top']:g} at Z 1200, slope length {Ls:.1f}",
                extras={"walk": walk, "eaves": w["eaves"], "top": w["top"], "slope_len": round(Ls, 3), "x_dir": [round(v, 4) for v in xd],
                        "y_dir": [round(v, 5) for v in yd], "run_from": w["a"] + sgn * pos, "run_to": w["a"] + sgn * (pos + wd), "line_axis": ax,
                        "hole": mesh == LEAN_H})
        ROOF_PANELS.setdefault(walk, []).append(d)
        pos += wd

# ------------------------------------------------------------------ floors
FLOORS = [("S", (9500, 540, 12000, 1310), "MI_Chapel_Floor_Dirty"), ("W", (9500, 1310, 10210, 2290), "MI_Chapel_Floor_Dirty"),
          ("E", (11490, 1310, 12000, 2290), "MI_Chapel_Floor_Dirty"), ("N1", (9500, 2290, 10850, 3000), "MI_Chapel_Floor_Dirty"),
          ("N2", (10850, 2290, 11490, 3000), "MI_Chapel_Floor_Puddled"), ("N3", (11490, 2290, 12000, 3000), "MI_Chapel_Floor_Dirty")]
for fid, (x0, y0, x1, y1), mi in FLOORS:
    add(f"CLA_Floor_{fid}", "floor", "floor", P_FLOORSLAB, (float(x0), float(y0), -38.5), (0, 0, 0), ((x1 - x0) / 1000.0, (y1 - y0) / 1000.0, 1.0), "NoCollision",
        "Cloister/Art/Floors", mi={"MAT_Masonry": mi}, note=f"X {x0}-{x1}, Y {y0}-{y1}")
GROUND_MI = {"Ground_1": "MI_Kit_Floor", "Ground_2": "MI_Kit_Floor", "Ground_4": "MI_Kit_Floor", "Ground_6": "MI_Kit_Floor"}

# ------------------------------------------------------------------ cell doors (C15) + leaves
FRAME = PIECES["SM_LB_Cl_CellDoorFrame_150x270"]["path"]
LEAF = existing(DUNGEON, "SM_Dungeon_door")
CELLS = [("N9900", "N", (9900.0, 3000.0), 0.0), ("N10500", "N", (10500.0, 3000.0), 0.0), ("N11100", "N", (11100.0, 3000.0), 0.0),
         ("W900", "W", (9500.0, 900.0), 90.0), ("W2700", "W", (9500.0, 2700.0), 90.0)]
for cid, wl, (wx, wy), yaw in CELLS:
    org = frame_pt((wx, wy), yaw, -75.0, 0.0)
    add(f"CLA_CellDoor_{cid}", "door", "celldoor", FRAME, (org[0], org[1], 0.0), (0.0, yaw, 0.0), (1, 1, 1), "NoCollision", "Cloister/Art/CellDoors",
        mi=mi_for(["MAT_Masonry", "MAT_Rubble"]), note=f"{wl} wall, centred at ({wx:g}, {wy:g}); frame projects 8 into the walk")
    # leaf: SM_Dungeon_door (x 2.4..15.8 thick, y -43.3..52.6, z 0.5..182.7), scale (0.5, 1.15, 1.2), back 1 cm in front of the back panel (y +2 -> +1)
    lyaw = yaw - 90.0
    lx_centre = (-43.3 + 52.6) / 2.0 * 1.15
    lo = frame_pt((wx, wy), yaw, 0.0, 0.0)
    pos_ = frame_pt((wx, wy), yaw, -lx_centre + 0.0, 1.0 + 2.4 * 0.5)
    rot_ = [0.0, lyaw, 0.0]
    note_ = "SM_Dungeon_door leaf scale (0.5, 1.15, 1.2), back 1 cm in front of the back panel"
    if cid == "N11100":
        rot_ = [0.0, lyaw + 8.0, 4.0]
        note_ += "; under the collapse: hangs by one hinge (roll 4, yaw +8)"
    add(f"CLA_CellLeaf_{cid}", "doorleaf", "cellleaf", LEAF, (pos_[0], pos_[1], -0.6), rot_, (0.5, 1.15, 1.2), "NoCollision", "Cloister/Art/CellDoors",
        note=note_, extras={"frame_yaw": yaw})


# =====================================================================================================
# D1.4 / D1.6  MECHANISM 3 AND GAMEPLAY REFERENCES (not placed by P10-5: the child Blueprints own them)
# =====================================================================================================
EXISTING["Point"] = (((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)), [])
add("GP_Mech_Ritual3", "gameplay", "mech3", CUBE, (MECH3_LOC[0], MECH3_LOC[1], 67.5), (0, 0, 0), (1.1, 1.1, 1.35), "BlockAll (BP pedestal + drum)", "Gameplay/Cloister",
    note="REFERENCE ONLY (lane-check proxy): Mech_Ritual3 after the D-081 move to (11780, 1760, 50): 110 x 110 footprint, Z 0-135; BP_RitualMechanism_TowerCapstan "
         "swaps the actor in P10-6b", extras={"via_bp": "BP_RitualMechanism_TowerCapstan", "skip_place": True, "actor_loc": list(MECH3_LOC)})
add("GP_Clue_Inscription", "gameplay", "inscription", PIECES["SM_LB_Prop_InscriptionTablet_A"]["path"], (12000.0, 2380.0, 200.0), (0.0, 180.0, 0.0), (2.5, 2.5, 2.5),
    "BlockAllDynamic", "Gameplay/Cloister", mi=mi_for(["MAT_Trim"]),
    note="REFERENCE ONLY: tablet back flush on the tower wall X 12000, world 10 x 300 x 75. NB D1.6.2 says the Plaque keeps the parent's relative transform (0,0,0): "
         "that puts the back at X 11995 and the front at 11985 (5 cm off the wall); the BP needs Plaque rel X -2 for flush",
    extras={"via_bp": "BP_Inscription_Cloister", "skip_place": True, "actor_loc": [11995.0, 2380.0, 200.0], "plaque_rel_x_for_flush": -2.0})
BELL_Y = [2200.0, 2320.0, 2440.0, 2560.0]
BELL_SCALE = [1.30, 1.15, 1.00, 0.85]
BELL_BAND = ["MI_LB_BellBand_I", "MI_LB_BellBand_II", "MI_LB_BellBand_III", "MI_LB_BellBand_IV"]
for i in range(4):
    y = BELL_Y[i]
    add(f"GP_Bell_{i + 1}_Bracket", "gameplay", "bell", PIECES["SM_LB_Prop_SmallBellBracket_A"]["path"], (12000.0, y, 145.0), (0.0, 180.0, 0.0), (1, 1, 1), "NoCollision",
        "Gameplay/Cloister", mi=mi_for(["MAT_Iron", "MAT_Wood"], wood=WOOD_CLOISTER), note="REFERENCE ONLY (BP_SmallBell_Cloister Post): plate back on the wall",
        extras={"via_bp": "BP_SmallBell_Cloister", "skip_place": True})
    add(f"GP_Bell_{i + 1}", "gameplay", "bell", PIECES["SM_LB_Prop_SmallBell_A"]["path"], (11975.0, y, 138.0), (0, 0, 0), (BELL_SCALE[i],) * 3, "BlockAllDynamic",
        "Gameplay/Cloister", mi=mi_for(["MAT_Bronze", "MAT_Iron"], overrides={"MAT_Band": BELL_BAND[i]}),
        note=f"REFERENCE ONLY: Bell_{i + 1}, BellScale {BELL_SCALE[i]}, band {BELL_BAND[i]}; BellPivot (11975, {y:g}, 140), crown top Z 138",
        extras={"via_bp": "BP_SmallBell_Cloister", "skip_place": True})
    add(f"GP_Bell_{i + 1}_Plaque", "gameplay", "bell", PIECES["SM_LB_Prop_BellPlaque_A"]["path"], (12000.0, y, 87.0), (0.0, 180.0, 0.0), (1, 1, 1), "NoCollision",
        "Gameplay/Cloister", mi=mi_for(["MAT_Trim"]), note="REFERENCE ONLY (BP_SmallBell_Cloister Plate)", extras={"via_bp": "BP_SmallBell_Cloister", "skip_place": True})


# =====================================================================================================
# D1.7  DRESSING (NoCollision unless stated)
# =====================================================================================================
def chain_run(rid, start, end, folder, note):
    """Chain segments (mesh hangs along -z from its top) laid end to end from start to end."""
    d = [end[k] - start[k] for k in range(3)]
    Ltot = math.sqrt(sum(c * c for c in d))
    n = max(1, int(math.ceil(Ltot / 117.6)))
    dirv = unit(d)
    zr = tuple(-c for c in dirv)                      # local +Z must point opposite to the run (local -Z hangs toward the run)
    ref = (1.0, 0.0, 0.0) if abs(dirv[0]) < 0.9 else (0.0, 1.0, 0.0)
    xr = unit(cross(ref, zr))
    yr = cross(zr, xr)
    rot = rot_from_rows(xr, yr, zr)
    out = []
    for i in range(n):
        s0 = Ltot * i / n
        loc = tuple(start[k] + dirv[k] * s0 for k in range(3))
        out.append(add(f"{rid}_{i}", "dress", "chain", CHAIN, loc, rot, (1.0, 1.0, Ltot / (n * 117.4)), "NoCollision", folder,
                       note=note + f" (segment {i + 1}/{n}, run length {Ltot:.1f})", extras={"run_from": list(start), "run_to": list(end)}))
    return out


CHAIN = existing(DUNGEON, "SM_Torture_Devices_Chains")
HOLDER = existing(DUNGEON, "SM_Dungeon_chain_holder")
add("CLA_Mech3_Eyelet", "dress", "mech3chain", HOLDER, (11995.0, 1800.0, 140.0), (0.0, 180.0, 0.0), (1, 1, 1), "NoCollision", "Cloister/Dressing/Mech3",
    note="iron wall eyelet at the tower wall (chain holder, +x out of the wall)")
chain_run("CLA_Mech3_Chain_A", (11810.0, 1760.0, 110.0), (11995.0, 1800.0, 140.0), "Cloister/Dressing/Mech3", "chain from the capstan drum to the wall eyelet")
chain_run("CLA_Mech3_Chain_B", (11995.0, 1800.0, 140.0), (11995.0, 1935.0, 120.0), "Cloister/Dressing/Mech3", "chain along the wall to the latch box")
add("CLA_Mech3_LatchBox", "dress", "mech3chain", CUBE, (11995.0, 1935.0, 120.0), (0, 0, 0), (0.08, 0.20, 0.30), "NoCollision", "Cloister/Dressing/Mech3",
    mi={"0": "MI_Crypt_Iron"}, note="iron box 8 deep x 20 wide x 30 tall on the wall beside the door (D1.7 lists 20 x 8 x 30; depth taken as 8)")

# ---- collapse rubble (N walk east bay)
HEAP = existing(KIT, "SM_LB_Kit_Rubble_Heap_400x300x130")
CH_S = existing(KIT, "SM_LB_Kit_Rubble_Chunk_S")
CH_M = existing(KIT, "SM_LB_Kit_Rubble_Chunk_M")
CH_L = existing(KIT, "SM_LB_Kit_Rubble_Chunk_L")
heap = add("CLA_Collapse_Heap", "dress", "collapse", HEAP, (11050.0, 2295.0, 0.0), (0, 0, 0), (0.8, 0.7, 0.5), "BlockAll", "Cloister/Dressing/Collapse",
           mi=mi_for(["MAT_Rubble"]), note="rubble heap, target world AABB X 11050-11370, Y 2295-2505, Z 0-65 (kit pivot = min corner)",
           extras={"target_min": [11050.0, 2295.0, 0.0], "target_max": [11370.0, 2505.0, 65.0]})
rr = random.Random(1401)
REG = (11000.0, 2300.0, 11450.0, 2500.0)
AI_KEEP = {"Search_Cloister_14": (10850.0, 2500.0), "Search_Cloister_12": (11350.0, 2850.0), "Patrol_Cloister_03": (10850.0, 2750.0)}
counters = {"rubble": 0, "voussoir": 0}
for mesh, grp, count in ((CH_M, "rubble", 3), (CH_S, "rubble", 2), (CH_L, "rubble", 1), (CH_S, "voussoir", 4)):
    for _k in range(count):
        for _try in range(400):
            s = rr.uniform(0.55, 0.95)
            yaw = rr.uniform(0.0, 360.0)
            cx, cy = rr.uniform(REG[0], REG[2]), rr.uniform(REG[1], REG[3])
            mb = mbounds_of(mesh)
            mn, mx = world_aabb(mb, (cx, cy, 0.0), (0.0, yaw, 0.0), (s, s, s))
            if mn[0] < REG[0] or mx[0] > REG[2] or mn[1] < REG[1] or mx[1] > REG[3]:
                continue
            if any(rect_gap(px, py, mn, mx) < 120.0 for px, py in AI_KEEP.values()):
                continue
            break
        else:
            raise RuntimeError("could not place a collapse chunk")
        slots = ["MAT_Rubble"] if mesh == CH_M else ["MAT_Trim", "MAT_Rubble"]
        cid = counters[grp]
        counters[grp] += 1
        add(f"CLA_Collapse_{grp.capitalize()}_{cid}", "dress", "collapse", mesh, (cx, cy, 0.0), (0.0, yaw, 0.0), (s, s, s),
            "NoCollision", "Cloister/Dressing/Collapse", mi=mi_for(slots),
            note=("kit rubble chunk" if grp == "rubble" else "vault voussoir chunk (kit chunk with MAT_Trim)") + " inside X 11000-11450, Y 2300-2500")
RAFTER = existing(PROC, "SM_LB_Prop_Rafter_Broken_15x10x260")
lean_p = math.degrees(math.asin(40.0 / 260.0))
add("CLA_Collapse_Rafter", "dress", "collapse", RAFTER, (11300.0, 2330.0, 0.0), (lean_p, 90.0, 0.0), (1, 1, 1), "NoCollision", "Cloister/Dressing/Collapse",
    mi=mi_for(["MAT_Wood"], wood=WOOD_CLOISTER),
    note=f"broken rafter leaning from the floor (11300, 2330) toward the arcade line Y 2290; a 260 rafter cannot reach the arcade wall top Z 620, "
         f"so it rests against the arcade face at Z {260 * math.cos(math.radians(lean_p)):.0f} (D1 note)")

# ---- derive-from-AABB helper (rafter debris in the bell chamber)
def fit_to_aabb(mb, rot, tmin, tmax):
    rows = rot_rows(*rot)
    scale = [1.0, 1.0, 1.0]
    wax = []
    for k in range(3):                                  # local axis k -> world axis (largest abs component of row k)
        w = max(range(3), key=lambda a: abs(rows[k][a]))
        wax.append((w, 1.0 if rows[k][w] > 0 else -1.0))
        ext = mb[1][k] - mb[0][k]
        scale[k] = (tmax[w] - tmin[w]) / ext
    loc = [0.0, 0.0, 0.0]
    for k in range(3):
        w, sg = wax[k]
        a, b = mb[0][k] * scale[k] * sg, mb[1][k] * scale[k] * sg
        lo_local = min(a, b)
        loc[w] = tmin[w] - lo_local
    return tuple(loc), tuple(scale)


tgt_min, tgt_max = (12045.0, 2190.0, 2500.0), (12060.0, 2450.0, 2515.0)
loc_, sc_ = fit_to_aabb(mbounds_of(RAFTER), (0.0, 0.0, 90.0), tgt_min, tgt_max)
add("TWA_Debris_Rafter", "dress", "chamberdebris", RAFTER, loc_, (0.0, 0.0, 90.0), sc_, "NoCollision", "BellTower/Art/Dressing",
    mi=mi_for(["MAT_Wood"]), note="broken rafter lying along the W wall in the NW corner of the W slab; derived from the target AABB (cross-section scaled to fit 15 x 15)",
    extras={"target_min": list(tgt_min), "target_max": list(tgt_max)})
for k in range(4):
    sx_, sy_, sz_ = 0.55, 0.9, 0.4          # chunk S 60x50x40 -> 33 x 45 x 16
    y0 = 2255.0 + 48.0 * k
    add(f"TWA_Debris_Chunk_{k}", "dress", "chamberdebris", CH_S, (12045.0, y0, 2500.0), (0, 0, 0), (sx_, sy_, sz_), "NoCollision", "BellTower/Art/Dressing",
        mi=mi_for(["MAT_Trim", "MAT_Rubble"]), note="kit rubble chunk, 16 tall, within 35 of the W wall (X 12045-12078)")

# ---- cells
STOOL = existing(ARTTEST + "Wooden_Stool_01/", "SM_Wooden_Stool_01")
BUCKET = existing(CC0 + "WoodenBucket01/", "SM_LB_CC0_WoodenBucket01")
add("CLA_Cell_Stool", "dress", "cell", STOOL, (9532.0, 2650.0, 0.0), (0.0, 20.0, 0.0), (1, 1, 1), "NoCollision", "Cloister/Dressing/Cells", note="stool by the W-wall cell door at Y 2700")
add("CLA_Cell_Bucket", "dress", "cell", BUCKET, (9530.0, 2748.0, 0.0), (0, 0, 0), (1, 1, 1), "NoCollision", "Cloister/Dressing/Cells", note="bucket by the W-wall cell door at Y 2700")

# ---- grime decals on the outer walls (Z 0-200)
DECAL_DEFS = [   # wall, along, MI, horizontal half
    ("S", 10100.0, "MI_Decal_Mould", 140.0), ("S", 11400.0, "MI_Decal_Leaking004_Wall", 90.0), ("N", 10200.0, "MI_Decal_Mould", 140.0),
    ("N", 11600.0, "MI_Decal_Leaking004_Wall", 90.0), ("W", 1300.0, "MI_Decal_Mould", 150.0), ("W", 2500.0, "MI_Decal_Mould", 120.0),
    ("E", 800.0, "MI_Decal_Mould", 140.0), ("E", 2800.0, "MI_Decal_Leaking004_Wall", 90.0)]
WALL_FACE = {"S": (1, 540.0, -90.0), "N": (1, 3000.0, 90.0), "W": (0, 9500.0, 180.0), "E": (0, 12000.0, 0.0)}   # axis of the face coordinate, coordinate, yaw into the wall
for i, (wl, along, mi, hh) in enumerate(DECAL_DEFS):
    ax, face, yaw = WALL_FACE[wl]
    loc = (along, face, 100.0) if ax == 1 else (face, along, 100.0)
    add(f"CLA_Decal_{wl}{i}", "dress", "decal", "Point", loc, (0.0, yaw, 90.0), (1, 1, 1), "-", "Cloister/Dressing/Decals", mi={"0": mi},
        note=f"{'damp/mould' if 'Mould' in mi else 'leak streaks'} on the {wl} wall inner face, Z 0-200",
        extras={"decal": {"mi": mi, "size": [12.0, 100.0, hh], "wall": wl}})

# ---- ivy on the garth-facing arcade wall (cards: back at local y 0 on the wall, leaves out to +y)
IVY_C = existing(IVY, "SM_LB_Prop_Ivy_Creep_400x200_Dead", mb=((-200.0, 0.0, 0.0), (200.0, 25.0, 200.0)), slots=["Ivy"], est=True)
for i, (x, y, yaw, note) in enumerate(((10900.0, 1391.0, 0.0, "S row"), (11000.0, 2209.0, 180.0, "N row"), (10291.0, 1850.0, -90.0, "W column"),
                                       (11409.0, 1850.0, 90.0, "E column"))):
    add(f"CLA_Ivy_{i}", "dress", "ivy", IVY_C, (x, y, 400.0), (0.0, yaw, 0.0), (1, 1, 1), "NoCollision", "Cloister/Dressing/Ivy",
        note=f"dead ivy card on the garth-facing arcade wall, {note}, Z 400-600")

# ---- lanterns (every D1.8 light that is a lantern) with an iron bracket
LANTERN = existing(ARTTEST + "Wooden_Lantern_01/", "SM_Wooden_Lantern_01")
LANTERNS = [("CLA_Lantern_Bells", "CLA", (11960.0, 2380.0, 320.0), (12000.0, 180.0), "above the inscription"),
            ("CLA_Lantern_Door", "CLA", (11960.0, 1880.0, 300.0), (12000.0, 180.0), "beside the tower door"),
            ("SHA_Lantern_Entry", "SHA", (10520.0, 300.0, 300.0), (10500.0, 0.0), "stair-house lantern"),
            ("PSA_Lantern", "PSA", (9380.0, 2240.0, 300.0), (2300.0, -90.0), "passage, cloister end")]
for lid, pre, (lx, ly, lz), (wallc, byaw), note in LANTERNS:
    folder = {"CLA": "Cloister/Dressing/Lanterns", "SHA": "Cloister/Art/StairHouse", "PSA": "Courtyard/Passage"}[pre]
    add(lid, "dress", "lantern", LANTERN, (lx, ly, lz - 26.0), (0, 0, 0), (1, 1, 1), "NoCollision", folder, note=note + "; hangs at the light position (centre of the lantern)")
    bx, by = (wallc, ly) if byaw in (180.0, 0.0) else (lx, wallc)
    add(lid.replace("Lantern", "LanternBracket"), "dress", "lantern", HOLDER, (bx, by, lz + 30.0), (0.0, byaw, 0.0), (1, 1, 1), "NoCollision", folder,
        note="iron bracket on the wall above the lantern (chain holder, +x out of the wall)")

# ---- tower dressing
ROPE_COIL = existing(DUNGEON, "SM_Torture_Devices_Rope_00")
add("TWA_RopeCoil", "dress", "towerdress", ROPE_COIL, (12307.0, 2000.0, 450.0), (0.0, 90.0, 0.0), (1, 1, 1), "NoCollision", "BellTower/Art/Dressing",
    note="coil of rope on the shaft base's top rim (W side), inside the 35-thick rim")
SLATES = existing(CHAPEL, "SM_LB_Prop_SlateShards_A", mb=((-60.0, -45.0, 0.0), (60.0, 45.0, 8.0)), slots=["MAT_Slate"], est=True)
top10 = LANDINGS[10][3]
for k, (sx, sy, syaw) in enumerate(((12760.0, 1575.0, 0.0), (12830.0, 1575.0, 8.0), (12898.0, 1575.0, -6.0), (12933.0, 1700.0, 90.0))):
    add(f"TWA_Slates_{k}", "dress", "towerdress", SLATES, (sx, sy, top10), (0.0, syaw, 0.0), (0.5, 0.5, 1.0), "NoCollision", "BellTower/Art/Dressing",
        mi=mi_for(["MAT_Slate"]), note="broken slates on landing 10, within 30 of the walls")
COBWEB = existing(CHAPEL, "SM_LB_Prop_Cobweb_Corner_A", mb=((-60.0, -60.0, 0.0), (60.0, 60.0, 120.0)), slots=["MAT_Cobweb"], est=True)
WALLCORNER = {"NE": ((12960.0, 2460.0), 180.0), "SE": ((12960.0, 1540.0), 90.0), "SW": ((12040.0, 1540.0), 0.0), "NW": ((12040.0, 2460.0), -90.0)}
for k, n in enumerate((2, 3, 4, 6, 7, 8)):
    corner, pt, yaw, top = LANDINGS[n]
    (cx, cy), cyaw = WALLCORNER[corner]
    c, s = math.cos(math.radians(cyaw)), math.sin(math.radians(cyaw))
    org = (cx - (-60.0 * c - (-60.0) * s), cy - (-60.0 * s + (-60.0) * c))
    add(f"TWA_Cobweb_{n:02d}", "dress", "towerdress", COBWEB, (org[0], org[1], top + 150.0 + 35.0 * (k % 3)), (0.0, cyaw, 0.0), (1, 1, 1), "NoCollision",
        "BellTower/Art/Dressing", mi={"MAT_Cobweb": "MI_Cobweb_Dungeon"}, note=f"cobweb card in the {corner} wall corner above landing {n} (Z top+{150 + 35 * (k % 3)})")

# ---- passage weeds (20, within 40 of the wall bases)
wrng = random.Random(1402)
for i in range(20):
    nm = f"SM_LB_CC0_WeedPlant02_{1 + (i % 5):02d}"
    mesh = existing(CC0 + "WeedPlant02/", nm)
    south = i % 2 == 0
    x = wrng.uniform(6120.0, 9400.0)
    d = wrng.uniform(16.0, 24.0)
    y = 1700.0 + d if south else 2300.0 - d
    add(f"PSA_Weed_{i:02d}", "dress", "weed", mesh, (x, y, 0.0), (0.0, wrng.uniform(0, 360), 0.0), (1, 1, 1), "NoCollision", "Courtyard/Passage",
        note=f"weed at the base of the passage {'S' if south else 'N'} wall ({d:.0f} from the face)")

# ---- garth vegetation (seed 1224): 40 grass, 12 nettles, 8 ferns, keep 50 clear of the cross base, slabs and Note_Cloister
grng = random.Random(1224)
GR = (10320.0, 1420.0, 11380.0, 2180.0)


def rot_rect_dist(px, py, cx, cy, yaw, hx, hy):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    lx, ly = (px - cx) * c + (py - cy) * s, -(px - cx) * s + (py - cy) * c
    return math.hypot(max(abs(lx) - hx, 0.0), max(abs(ly) - hy, 0.0))


GRASS = [existing(CC0 + "GrassMedium02/", f"SM_LB_CC0_GrassMedium02_{i:02d}", mb=((-25.0, -25.0, 0.0), (25.0, 25.0, 35.0)), slots=["grass"], est=True) for i in range(1, 6)]
NETTLE = [existing(CC0 + "NettlePlant/", f"SM_LB_CC0_NettlePlant_{i:02d}") for i in range(1, 7)]
FERN = [existing(CC0 + "Fern02/", f"SM_LB_CC0_Fern02_{i:02d}") for i in range(1, 5)]
for kind, lst, count in (("Grass", GRASS, 40), ("Nettle", NETTLE, 12), ("Fern", FERN, 8)):
    for k in range(count):
        mesh = lst[grng.randrange(len(lst))]
        mb = mbounds_of(mesh)
        rad = 0.5 * max(mb[1][0] - mb[0][0], mb[1][1] - mb[0][1])
        for _try in range(400):
            x, y = grng.uniform(GR[0], GR[2]), grng.uniform(GR[1], GR[3])
            if x - rad < GR[0] or x + rad > GR[2] or y - rad < GR[1] or y + rad > GR[3]:
                continue
            ok = rot_rect_dist(x, y, 10850.0, 1800.0, 15.0, 60.0, 60.0) - rad >= 50.0
            ok = ok and math.hypot(x - 10750.0, y - 1425.0) - rad >= 50.0 + 20.0
            for i2, (gx, gy) in enumerate(GRAVES):
                ok = ok and rot_rect_dist(x, y, gx, gy, SLAB_ROT[i2][1], 100.0, 40.0) - rad >= 50.0
            for (gx, gy) in ((10450.0, 1500.0), (11250.0, 1500.0), (10450.0, 2100.0), (11250.0, 2100.0)):
                ok = ok and math.hypot(x - gx, y - gy) - rad >= 50.0
            if ok:
                break
        else:
            raise RuntimeError("garth vegetation: no spot")
        add(f"CLA_Garth{kind}_{k:02d}", "dress", "garthveg", mesh, (x, y, 100.0 + grng.uniform(0.0, 5.0)), (0.0, grng.uniform(0.0, 360.0), 0.0), (1, 1, 1), "NoCollision",
            "Cloister/Dressing/Garth", note="garth vegetation (seed 1224)")


# =====================================================================================================
# D1.8  LIGHTS
# =====================================================================================================
def light(lid, loc, lm, radius, temp=None, color=None, folder="Lighting/Cloister", note=""):
    ex = {"light": {"type": "PointLight", "lumens": lm, "radius": radius, "shadows": False}}
    if temp:
        ex["light"]["temperature_K"] = temp
    if color:
        ex["light"]["color_linear"] = list(color)
    add(lid, "light", "light", "Point", loc, (0, 0, 0), (1, 1, 1), "-", folder, note=note, extras=ex)


light("L_Cl_Bells", (11960.0, 2380.0, 320.0), 250, 600, 2200, note="lantern above the inscription")
light("L_Cl_Door", (11960.0, 1880.0, 300.0), 200, 500, 2200, note="lantern beside the tower door")
light("L_Cl_Entry", (10520.0, 300.0, 300.0), 150, 450, 2200, note="stair-house lantern")
light("L_Cl_West", (9560.0, 2000.0, 320.0), 150, 450, 2200, note="W walk, at the passage arch")
light("L_Cl_Cell", (9900.0, 2970.0, 30.0), 60, 200, 1900, note="candle cluster at the N-wall door at X 9900 (30 from the wall), Z 30")
light("L_Ps_Lantern", (9380.0, 2240.0, 300.0), 150, 500, 2200, folder="Lighting/Cloister", note="passage, cloister end")
light("L_Tw_Base", (12060.0, 1880.0, 260.0), 150, 450, 2200, folder="Lighting/BellTower", note="tower base")
for n in (4, 7, 10):
    corner, pt, yaw, top = LANDINGS[n]
    cx = pt[0] + (125.0 if corner in ("NE", "SE") else -125.0)
    cy = pt[1] + (125.0 if corner in ("NE", "NW") else -125.0)
    light(f"L_Tw_Land{n}", (cx, cy, top + 30.0), 100, 350, 2200, folder="Lighting/BellTower", note=f"30 above the {corner} landing-{n} top (landing centre)")
light("L_Tw_Bell", (12290.0, 1865.0, 2700.0), 150, 500, 2200, folder="Lighting/BellTower", note="on the bell frame post")
light("L_Tw_BellFill", (12500.0, 2300.0, 3300.0), 120, 900, None, (0.75, 0.80, 0.92), folder="Lighting/BellTower", note="moon fill")
LIGHTS_PLAN = {
    "delete": [f"Light_Cloister_{i}" for i in range(8)] + [f"Light_Tower_{i}" for i in range(6)] + ["Light_TowerBell", "Light_TowerTop_0", "Light_Courtyard_7"],
    "keep_and_tune": {f"Light_TowerExt_{i}": "tune to 200-400 lm so the W face reads against the sky from the gate" for i in range(3)},
    "fog": {"id": "LFV_Tower", "box_min": [12040, 1540, 0], "box_max": [12960, 2460, 3500], "note": "extinction low enough that slit and roof moonbeams read as shafts; P10-7 tunes it"},
    "moon": "keep DirectionalLight (pitch -38, yaw 35)",
}


# =====================================================================================================
# D1.0  greybox hide list, ground materials
# =====================================================================================================
HIDE_FOLDERS = ("Cloister", "BellTower", "BellTower/Stairs", "BellTower/Railings")
HIDE = sorted(g["label"] for g in GREYBOX.values() if g["folder_query"] in HIDE_FOLDERS or g["label"] in ("Passage_S", "Passage_N"))
KEEP_VISIBLE = sorted(g["label"] for g in GREYBOX.values() if g["label"] not in HIDE)


# =====================================================================================================
# D1.9  CHECKS
# =====================================================================================================
CHECKS = []      # (group, name, ok, detail)
WARNINGS = []    # (name, detail)


def chk(group, name, ok, detail):
    CHECKS.append((group, name, bool(ok), detail))


def rec_by_id(rid):
    return next(r for r in RECS if r["id"] == rid)


# ---- 1. treads and landings -----------------------------------------------------------------------
worst_dz, worst_xy, worst_dz_id = 0.0, 0.0, ""
RISE_T_D1 = 16.2338
for k in range(1, 12):
    fr = rec_by_id(f"TWA_Flight_F{k:02d}")
    for i in range(14):
        top = RISE_T_D1 * (i + 1)
        mb = ((30.0 * i - 2.0, 1.0, top - 6.0), (30.0 * i + 30.0, 249.0, top))
        mn, mx = world_aabb(mb, fr["loc"], fr["rot"], fr["scale"])
        gmn, gmx = gb(f"Stair_F{k:02d}_{i:02d}")
        dz = abs(mx[2] - gmx[2])
        if dz > worst_dz:
            worst_dz, worst_dz_id = dz, f"Stair_F{k:02d}_{i:02d}"
        excess = max(gmn[0] - mn[0], mx[0] - gmx[0], gmn[1] - mn[1], mx[1] - gmx[1])
        worst_xy = max(worst_xy, excess)
chk("1 treads", "154 tread tops vs greybox step tops", worst_dz <= 1.0, f"worst dz {worst_dz:.4f} cm ({worst_dz_id}); limit 1.0")
chk("1 treads", "tread footprint vs greybox step footprint (nosing 2 allowed)", worst_xy <= 2.01, f"worst overhang beyond the greybox step {worst_xy:.3f} cm; limit 2.0 (nosing)")
worst_lz, worst_lxy, worst_l_id = 0.0, 0.0, ""
for n in range(1, 11):
    lr = rec_by_id(f"TWA_Landing_{n:02d}")
    gmn, gmx = gb(f"Tw_Landing_{n:02d}")
    dz = abs(lr["aabb_max"][2] - gmx[2])
    dxy = max(abs(lr["aabb_min"][0] - gmn[0]), abs(lr["aabb_min"][1] - gmn[1]), abs(lr["aabb_max"][0] - gmx[0]), abs(lr["aabb_max"][1] - gmx[1]))
    if dz > worst_lz:
        worst_lz, worst_l_id = dz, lr["id"]
    worst_lxy = max(worst_lxy, dxy)
chk("1 treads", "10 landing tops vs greybox landing tops", worst_lz <= 1.0, f"worst dz {worst_lz:.4f} cm ({worst_l_id}); limit 1.0")
chk("1 treads", "10 landing footprints vs greybox", worst_lxy <= 0.5, f"worst XY deviation {worst_lxy:.3f} cm; limit 0.5")

# ---- 2. lanes ---------------------------------------------------------------------------------------
FLUSH_TOL = 8.5
FLUSH_OBST = []
for lbl, g in GREYBOX.items():
    if g["folder_query"] in ("Cloister", "BellTower") or lbl in ("Passage_S", "Passage_N", "Tw_Core"):
        mn, mx = gb(lbl)
        FLUSH_OBST.append((lbl, mn[0], mn[1], mx[0], mx[1]))
FLUSH_OBST += [("CornerPierSW", 10210, 1310, 10340, 1390), ("CornerPierSE", 11360, 1310, 11490, 1390), ("CornerPierNW", 10210, 2210, 10340, 2290),
               ("CornerPierNE", 11360, 2210, 11490, 2290), ("TowerWallW", 12000, 1500, 12040, 2500), ("TowerWallE", 12960, 1500, 13000, 2500),
               ("TowerWallN", 12040, 2460, 12960, 2500), ("TowerWallS", 12040, 1500, 12960, 1540), ("ClWallS", 9460, 500, 12040, 540),
               ("ClWallW", 9460, 500, 9500, 3040), ("ClWallE", 12000, 500, 12040, 3040), ("ClWallN", 9460, 3000, 12040, 3040)]
FLUSH_EXEMPT_CATS = {"floor", "vault", "roof"}
FLUSH_EXEMPT_GROUPS = {"flight", "landing", "flightrail", "decal", "light"}
NEVER_FLUSH = {"shaftpost", "block", "collapse", "mech3", "bell"}


def lane_candidates():
    out = []
    for r in RECS:
        if r["cat"] in FLUSH_EXEMPT_CATS or r["group"] in FLUSH_EXEMPT_GROUPS or r["mesh"] == "Point":
            continue
        zlo = r.get("lane_zlo", r["aabb_min"][2])
        zhi = r["aabb_max"][2]
        fl = None
        if r["group"] not in NEVER_FLUSH:
            for (nm, x0, y0, x1, y1) in FLUSH_OBST:
                if (r["aabb_min"][0] >= x0 - FLUSH_TOL and r["aabb_max"][0] <= x1 + FLUSH_TOL and r["aabb_min"][1] >= y0 - FLUSH_TOL
                        and r["aabb_max"][1] <= y1 + FLUSH_TOL):
                    fl = nm
                    break
        if fl:
            continue
        out.append((r["id"], (r["aabb_min"][0], r["aabb_min"][1]), (r["aabb_max"][0], r["aabb_max"][1]), zlo, zhi))
    return out


LANE_RECS = lane_candidates()


def lane_min(samples, band, radius):
    """samples: list of (x, y, floor_z). Returns (min clearance, record id) over the band-relevant, non-exempt records."""
    best, who = 1e9, "-"
    for rid, mn, mx, zlo, zhi in LANE_RECS:
        for (x, y, fz) in samples:
            if zlo < fz + band and zhi > fz + 10.0:
                d = rect_gap(x, y, mn, mx) - radius
                if d < best:
                    best, who = d, rid
    return best, who


def seg_samples(a, b, step=5.0):
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    n = max(1, int(L / step))
    return [(a[0] + (b[0] - a[0]) * t / n, a[1] + (b[1] - a[1]) * t / n, a[2] + (b[2] - a[2]) * t / n) for t in range(n + 1)]


LANE_ROWS = []
# WalkPath TowerStairs (player, walk line, head 200)
worst_t = (1e9, "", "")
for i in range(len(WP_TOWER) - 1):
    (la, a), (lb, b) = WP_TOWER[i], WP_TOWER[i + 1]
    c, who = lane_min(seg_samples(a, b), 200.0, 0.0)
    LANE_ROWS.append((f"{la}->{lb}", "WalkPath TowerStairs", c, who))
    worst_t = min(worst_t, (c, f"{la}->{lb}", who))
chk("2 lanes", "WalkPath TowerStairs 00..24 (24 segments, walk line, head 200)", worst_t[0] >= 60.0, f"worst clearance {worst_t[0]:.1f} cm at {worst_t[1]} vs {worst_t[2]}; limit 60")
(la, a), (lb, b) = WP_CRYPT[9], WP_CRYPT[10]
c, who = lane_min(seg_samples(a, b), 200.0, 0.0)
LANE_ROWS.append((f"{la}->{lb}", "WalkPath CryptToCloister", c, who))
chk("2 lanes", "WalkPath CryptToCloister 09->10", c >= 60.0, f"clearance {c:.1f} cm vs {who}; limit 60")

# Warden agent (radius 42, height band 300): patrol route incl. the wrap-around, routed around the greybox collision
WRAD = 42.0
BAND_W = 300.0
BASE_OBST = []
for lbl, g in GREYBOX.items():
    if g["folder_query"] in ("Cloister", "BellTower") and g["folder_query"] != "":
        mn, mx = gb(lbl)
        if mn[2] < BAND_W and lbl not in ("Tw_Roof",) and not lbl.startswith("Tw_Landing") and not lbl.startswith("Top_") and not lbl.startswith("Bell_"):
            BASE_OBST.append((mn[0], mn[1], mx[0], mx[1]))
NEW_COLL = []
for r in RECS:
    if (r["group"] in ("block", "mech3", "bell") or r["id"] == "CLA_Collapse_Heap") and r["aabb_min"][2] < BAND_W:
        NEW_COLL.append((r["id"], r["aabb_min"][0], r["aabb_min"][1], r["aabb_max"][0], r["aabb_max"][1]))
CLEAR_NEED = 60.0


def seg_hits_rect(a, b, r):
    x0, y0, x1, y1 = r[0] + 1e-6, r[1] + 1e-6, r[2] - 1e-6, r[3] - 1e-6
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if abs(p) < 1e-12:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                if t > t1:
                    return False
                t0 = max(t0, t)
            else:
                if t < t0:
                    return False
                t1 = min(t1, t)
    return t0 < t1 - 1e-9


def route(a, b, base_infl, new_infl):
    rects = [(x0 - base_infl, y0 - base_infl, x1 + base_infl, y1 + base_infl) for (x0, y0, x1, y1) in BASE_OBST]
    rects += [(x0 - new_infl, y0 - new_infl, x1 + new_infl, y1 + new_infl) for (_, x0, y0, x1, y1) in NEW_COLL]
    nodes = [a[:2], b[:2]]
    for (x0, y0, x1, y1) in rects:
        nodes += [(x0 - 0.01, y0 - 0.01), (x1 + 0.01, y0 - 0.01), (x1 + 0.01, y1 + 0.01), (x0 - 0.01, y1 + 0.01)]
    n = len(nodes)
    dist = [1e18] * n
    prev = [-1] * n
    dist[0] = 0.0
    pq = [(0.0, 0)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        if u == 1:
            break
        for v in range(n):
            if v == u:
                continue
            pu, pv = nodes[u], nodes[v]
            if any(seg_hits_rect(pu, pv, r) for r in rects):
                continue
            nd = d + math.hypot(pu[0] - pv[0], pu[1] - pv[1])
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    if dist[1] > 1e17:
        return None, None
    path, u = [], 1
    while u != -1:
        path.append(nodes[u])
        u = prev[u]
    return path[::-1], dist[1]


def polyline_samples(path, step=5.0):
    out = []
    for i in range(len(path) - 1):
        out += seg_samples((path[i][0], path[i][1], 0.0), (path[i + 1][0], path[i + 1][1], 0.0), step)
    return out


PATROL_ROWS = []
PATROL_PATHS = {}
worst_p = (1e9, "", "")
for i in range(len(PATROL)):
    la, a = PATROL[i]
    lb, b = PATROL[(i + 1) % len(PATROL)]
    straight = math.hypot(b[0] - a[0], b[1] - a[1])
    blocked = any(seg_hits_rect(a[:2], b[:2], (x0 - WRAD, y0 - WRAD, x1 + WRAD, y1 + WRAD)) for (x0, y0, x1, y1) in BASE_OBST)
    if blocked:
        path, L = route(a, b, WRAD, WRAD + CLEAR_NEED)
    else:
        path, L = [a[:2], b[:2]], straight
    if path is None:
        PATROL_ROWS.append((f"{la}->{lb}", straight, None, -1.0, "no route"))
        worst_p = min(worst_p, (-1.0, f"{la}->{lb}", "no route"))
        continue
    PATROL_PATHS[f"{la}->{lb}"] = path
    c, who = lane_min(polyline_samples(path), BAND_W, WRAD)
    detour = L - straight
    PATROL_ROWS.append((f"{la}->{lb}", straight, L, c, who))
    worst_p = min(worst_p, (c, f"{la}->{lb}", who))
chk("2 lanes", "Patrol_Cloister route 01..07 + wrap-around 07->01 (Warden radius 42, routed around the greybox, new colliders kept 60 off)",
    worst_p[0] >= CLEAR_NEED, f"worst clearance {worst_p[0]:.1f} cm at {worst_p[1]} vs {worst_p[2]}; limit 60")
# straight-line numbers for the new colliders (what the lead's method gives)
STRAIGHT_ROWS = []
for i in range(len(PATROL)):
    la, a = PATROL[i]
    lb, b = PATROL[(i + 1) % len(PATROL)]
    if i == len(PATROL) - 1:
        continue          # the wrap segment is not a straight line (it crosses the garth block)
    best = (1e9, "")
    for (cid, x0, y0, x1, y1) in NEW_COLL:
        d = seg_rect_dist(a, b, (x0, y0), (x1, y1)) - WRAD
        best = min(best, (d, cid))
    STRAIGHT_ROWS.append((f"{la}->{lb}", best[0], best[1]))

pt_rows = []
worst_s = (1e9, "", "")
for lbl, p in SEARCH:
    c, who = lane_min([(p[0], p[1], 0.0)], BAND_W, WRAD)
    pt_rows.append((lbl, c, who))
    worst_s = min(worst_s, (c, lbl, who))
chk("2 lanes", "Search_Cloister_01..14 points (radius 42)", worst_s[0] >= CLEAR_NEED, f"worst clearance {worst_s[0]:.1f} cm at {worst_s[1]} vs {worst_s[2]}; limit 60")
worst_w = (1e9, "", "")
for lbl, p in SPAWN:
    c, who = lane_min([(p[0], p[1], 0.0)], BAND_W, WRAD)
    pt_rows.append((lbl, c, who))
    worst_w = min(worst_w, (c, lbl, who))
chk("2 lanes", "WSpawn_Cloister and WSpawn_Tower (radius 42)", worst_w[0] >= CLEAR_NEED, f"worst clearance {worst_w[0]:.1f} cm at {worst_w[1]} vs {worst_w[2]}; limit 60")
# D1.7 explicit keep-clear distances (collapse debris vs 3 AI points, 120)
kc = 1e9
for r in RECS:
    if r["group"] == "collapse":
        for nm, (px, py) in AI_KEEP.items():
            kc = min(kc, rect_gap(px, py, (r["aabb_min"][0], r["aabb_min"][1]), (r["aabb_max"][0], r["aabb_max"][1])))
chk("2 lanes", "D1.7 collapse debris >= 120 from Search_Cloister_14/_12 and Patrol_Cloister_03", kc >= 120.0, f"closest {kc:.1f} cm")
# chamber debris >= 120 from WP_TowerStairs_22/23/24
kc2 = 1e9
for r in RECS:
    if r["group"] == "chamberdebris":
        for nm, p in WP_TOWER[22:25]:
            kc2 = min(kc2, rect_gap(p[0], p[1], (r["aabb_min"][0], r["aabb_min"][1]), (r["aabb_max"][0], r["aabb_max"][1])))
chk("2 lanes", "D1.2 chamber debris >= 120 from WP_TowerStairs_22/23/24", kc2 >= 120.0, f"closest {kc2:.1f} cm")
# Mech_Ritual3 vs Patrol 04->05 (D1.6: >= 60 + 42)
m3 = rec_by_id("GP_Mech_Ritual3")
dm = seg_rect_dist(PATROL[3][1], PATROL[4][1], (m3["aabb_min"][0], m3["aabb_min"][1]), (m3["aabb_max"][0], m3["aabb_max"][1]))
chk("2 lanes", "Mech_Ritual3 footprint 110x110 at (11780, 1760) vs Patrol_Cloister_04->05 (>= 102)", dm >= 102.0, f"distance {dm:.1f} cm (clearance {dm - 42:.1f})")
# the collapse heap vs patrol 03->04
hp = rec_by_id("CLA_Collapse_Heap")
dh = seg_rect_dist(PATROL[2][1], PATROL[3][1], (hp["aabb_min"][0], hp["aabb_min"][1]), (hp["aabb_max"][0], hp["aabb_max"][1]))
chk("2 lanes", "BlockAll rubble heap vs Patrol_Cloister_03->04 (>= 102)", dh >= 102.0, f"distance {dh:.1f} cm (clearance {dh - 42:.1f})")

# ---- 3. faces and shell -----------------------------------------------------------------------------
TW_FACE_CHECK = {"W": (0, gbc("Tw_W_S", True, 0)), "E": (0, gbc("Tw_E", False, 0)), "N": (1, gbc("Tw_N", False, 1)), "S": (1, gbc("Tw_S", True, 1))}
worst_f, worst_f_id, nface = -1.0, "", 0
for r in RECS:
    fc = r["extras"].get("face_check")
    if fc is None and r["group"] == "shell":
        ax, val = TW_FACE_CHECK[r["extras"]["face_frame"]]
        fc = [ax, val, "tower greybox inner face"]
    if fc is None:
        continue
    p = xf_point(r["loc"], r["rot"], r["scale"], (0.0, 0.0, 0.0))
    dev = abs(p[fc[0]] - fc[1])
    nface += 1
    if dev > worst_f:
        worst_f, worst_f_id = dev, r["id"]
chk("3 faces", f"{nface} wall-piece inner faces vs greybox faces", worst_f <= 0.5, f"worst deviation {worst_f:.3f} cm ({worst_f_id}); limit 0.5")
SHELL = ((12000.0, 1500.0, -40.0), (13000.0, 2500.0, 3540.0))
bad = []
for r in RECS:
    if r["group"] in ("towerroof", "greatbell"):
        continue
    if not (r["folder"].startswith("BellTower/Art") or r["id"].startswith("TWA_")) or r["cat"] in ("block",):
        continue
    if r["group"] == "shell":
        mb = ((0.0, 0.0, 0.0), (TW_FACES[r["extras"]["face_frame"]][2], 40.0, PIECES[r["mesh"].split("/")[-1].split(".")[0]]["mbounds"][1][2]))
        mn, mx = world_aabb(mb, r["loc"], r["rot"], r["scale"])
    else:
        mn, mx = r["aabb_min"], r["aabb_max"]
    if any(mn[k] < SHELL[0][k] - 0.5 or mx[k] > SHELL[1][k] + 0.5 for k in range(3)):
        bad.append(f"{r['id']} {rnd(mn, 1)}..{rnd(mx, 1)}")
chk("3 faces", "tower pieces inside the shell AABB (X 12000-13000, Y 1500-2500, Z <= 3540) except courses and the roof", not bad, "all inside" if not bad else "; ".join(bad))

# ---- 4. rails and posts -----------------------------------------------------------------------------
worst_r, worst_r_id = -1.0, ""
for k in range(1, 12):
    ring = FLIGHTS[k][0]
    ax = 1 if ring in ("N", "S") else 0
    rr_ = rec_by_id(f"TWA_FlightRail_F{k:02d}")
    glo, ghi = 1e9, -1e9
    for j in range(7):
        mn, mx = gb(f"Rail_F{k:02d}_{j:02d}")
        glo, ghi = min(glo, mn[ax]), max(ghi, mx[ax])
    dev = max(abs(rr_["aabb_min"][ax] - glo), abs(rr_["aabb_max"][ax] - ghi))
    if dev > worst_r:
        worst_r, worst_r_id = dev, rr_["id"]
chk("4 rails", "11 rail bands on the greybox rail planes", worst_r <= 0.5, f"worst deviation {worst_r:.3f} cm ({worst_r_id}); limit 0.5")
cmn, cmx = gb("Tw_Core")
bad = []
for r in RECS:
    if r["group"] == "shaftpost":
        for k2 in (0, 1):
            if r["aabb_min"][k2] < cmn[k2] - 10.5 or r["aabb_max"][k2] > cmx[k2] + 10.5:
                bad.append(r["id"])
chk("4 rails", "4 shaft posts inside the 10 cm rail band + core", not bad, "all inside" if not bad else ", ".join(bad))

# ---- 5. vault overlaps ------------------------------------------------------------------------------
vs = [r for r in RECS if r["group"] == "vaultbay"]
worst_v, worst_v_pair, cnt_ov = 0.0, "", 0
for i in range(len(vs)):
    for j in range(i + 1, len(vs)):
        a, b = vs[i], vs[j]
        ox = min(a["aabb_max"][0], b["aabb_max"][0]) - max(a["aabb_min"][0], b["aabb_min"][0])
        oy = min(a["aabb_max"][1], b["aabb_max"][1]) - max(a["aabb_min"][1], b["aabb_min"][1])
        if ox > 0.5 and oy > 0.5:
            cnt_ov += 1
            if min(ox, oy) > worst_v:
                worst_v, worst_v_pair = min(ox, oy), f"{a['id']}/{b['id']} ({ox:.0f} x {oy:.0f})"
chk("5 vaults", "no two vault bays overlap by more than their 30 cm tuck", worst_v <= 30.5, f"{cnt_ov} overlapping pairs, worst min-dimension {worst_v:.1f} cm {worst_v_pair}; limit 30")

# ---- 6. counts ---------------------------------------------------------------------------------------
def n_group(g):
    return sum(1 for r in RECS if r["group"] == g)


COUNTS = [("Flights", n_group("flight"), 11), ("Landings", n_group("landing"), 10), ("Flight rails", n_group("flightrail"), 11), ("Louvres", n_group("louvre"), 8),
          ("Piers (row + column)", n_group("pier"), 10), ("Piers (corner)", n_group("pier_corner"), 4), ("Arches", n_group("arch"), 14),
          ("Vault bays", n_group("vaultbay"), 10), ("Roof panels", n_group("roofpanel"), 12), ("Hidden blocks", n_group("block"), 8), ("Cell doors", n_group("celldoor"), 5)]
for nm, got, want in COUNTS:
    chk("6 counts", f"{nm}", got == want, f"{got} (expected {want})")

# ---- derived-value assertions ----------------------------------------------------------------------
heap = rec_by_id("CLA_Collapse_Heap")
tgt = heap["extras"]
dev = max(abs(heap["aabb_min"][k] - tgt["target_min"][k]) for k in range(3)) + max(abs(heap["aabb_max"][k] - tgt["target_max"][k]) for k in range(3))
chk("7 derived", "rubble heap AABB = target X 11050-11370, Y 2295-2505, Z 0-65", dev <= 1.0, f"sum of deviations {dev:.3f} cm")
raf = rec_by_id("TWA_Debris_Rafter")
tgt = raf["extras"]
dev = max(abs(raf["aabb_min"][k] - tgt["target_min"][k]) for k in range(3)) + max(abs(raf["aabb_max"][k] - tgt["target_max"][k]) for k in range(3))
chk("7 derived", "chamber rafter AABB = target X 12045-12060, Y 2190-2450, Z 2500-2515", dev <= 1.0, f"sum of deviations {dev:.3f} cm; scale {raf['scale']}")
bad = []
for r in RECS:
    if r["group"] == "block":
        d = max(abs(r["aabb_min"][k] - r["extras"]["target_min"][k]) for k in range(3)) + max(abs(r["aabb_max"][k] - r["extras"]["target_max"][k]) for k in range(3))
        if d > 0.2:
            bad.append(r["id"])
chk("7 derived", "8 hidden blocks equal their D1.0 extents", not bad, "ok" if not bad else ", ".join(bad))
gbell = rec_by_id("TWA_GreatBell")
exp = ((12315.0, 1895.0, 2640.0), (12525.0, 2105.0, 2860.0))
dev = max(abs(gbell["aabb_min"][k] - exp[0][k]) for k in range(3)) + max(abs(gbell["aabb_max"][k] - exp[1][k]) for k in range(3))
chk("7 derived", "great bell world bounds = X 12315-12525, Y 1895-2105, Z 2640-2860", dev <= 1.0, f"sum of deviations {dev:.3f} cm")
ins = rec_by_id("GP_Clue_Inscription")
dev = max(abs(ins["aabb_min"][0] - 11990.0), abs(ins["aabb_max"][0] - 12000.0), abs(ins["aabb_min"][1] - 2230.0), abs(ins["aabb_max"][1] - 2530.0),
          abs(ins["aabb_min"][2] - 162.5), abs(ins["aabb_max"][2] - 237.5))
chk("7 derived", "inscription tablet 10 x 300 x 75, flush on X 12000 (with the Plaque shifted -2 local, see D1 note)", dev <= 0.5, f"deviation {dev:.3f} cm")
# roof panel corners on the eaves and top lines
worst_c, worst_c_id = 0.0, ""
for walk, lst in ROOF_PANELS.items():
    w = ROOF_WALKS[walk]
    ax = w["line_axis"]
    for d in lst:
        for (lx, ly, line, zt) in ((0.0, 0.0, w["eaves"], EAVES_Z), (1000.0, 0.0, w["eaves"], EAVES_Z), (0.0, 1050.0, w["top"], TOP_Z), (1000.0, 1050.0, w["top"], TOP_Z)):
            p = xf_point(d["loc"], d["rot"], d["scale"], (lx, ly, 0.0))
            dev = max(abs(p[ax] - line), abs(p[2] - zt))
            if dev > worst_c:
                worst_c, worst_c_id = dev, d["id"]
chk("7 derived", "12 roof panels: transformed corners on the eaves (Z 640) and top (Z 1200) lines", worst_c <= 1.0, f"worst corner deviation {worst_c:.4f} cm ({worst_c_id}); limit 1.0")
# roof run coverage: panels tile the run without gaps
bad = []
for walk, lst in ROOF_PANELS.items():
    cov = sorted((min(d["extras"]["run_from"], d["extras"]["run_to"]), max(d["extras"]["run_from"], d["extras"]["run_to"])) for d in lst)
    for i in range(len(cov) - 1):
        if abs(cov[i][1] - cov[i + 1][0]) > 0.01:
            bad.append(walk)
chk("7 derived", "roof panels tile each walk's run (3 per walk)", not bad, "ok" if not bad else str(bad))
# floors do not overlap
fl = [r for r in RECS if r["id"].startswith("CLA_Floor_")]
bad = []
for i in range(len(fl)):
    for j in range(i + 1, len(fl)):
        a, b = fl[i], fl[j]
        ox = min(a["aabb_max"][0], b["aabb_max"][0]) - max(a["aabb_min"][0], b["aabb_min"][0])
        oy = min(a["aabb_max"][1], b["aabb_max"][1]) - max(a["aabb_min"][1], b["aabb_min"][1])
        if ox > 0.5 and oy > 0.5:
            bad.append(f"{a['id']}/{b['id']}")
chk("7 derived", "cloister floor slabs do not overlap", not bad, "ok" if not bad else ", ".join(bad))
# unique ids
ids = [r["id"] for r in RECS]
chk("7 derived", "record ids unique", len(ids) == len(set(ids)), f"{len(ids)} records")
# greybox hide list
chk("7 derived", "hide list = 278 folder actors + Passage_S/N", len(HIDE) == 280, f"{len(HIDE)} actors")

# ---- D1 consistency notes (WARN, not failures) -------------------------------------------------------
# N-walk hole panel vs the broken vault bay
hole = next(d for d in ROOF_PANELS["N"] if d["extras"]["hole"])
x0 = min(hole["extras"]["run_from"], hole["extras"]["run_to"])
sxh = hole["scale"][0]
hx0, hx1 = x0 + 150.0 * sxh, x0 + 850.0 * sxh
vault = rec_by_id("CLA_Vault_N_E")
vx0, vx1 = vault["aabb_min"][0], vault["aabb_max"][0]
ov = max(0.0, min(hx1, vx1) - max(hx0, vx0))
WARNINGS.append(("D1-N1 N-walk roof hole vs broken vault",
                 f"the middle N panel spans X {x0:.0f}-{x0 + 1000 * sxh:.0f}; its hole is X {hx0:.0f}-{hx1:.0f}; the broken vault bay is X {vx0:.0f}-{vx1:.0f}; overlap {ov:.0f} of "
                 f"{hx1 - hx0:.0f}. D1.3 states the middle panel is X 10833-11667 (hole 10958-11541), which only holds for a run X 10000-12500, not 9500-12000. "
                 + ("(--n-roof-fix applied.)" if N_ROOF_FIX else "Proposed fix: run the generator with --n-roof-fix (panels 9500-10833, 10833-11667, 11667-12000 with x-scale 1.3333 / 0.8333 / 0.3333).")))
# rope vs the shaft base inner wall
rope = rec_by_id("TWA_BellRope")
sb = rec_by_id("TWA_ShaftBase")
inner_y0 = sb["aabb_min"][1] + 35.0
gap = rope["loc"][1] - inner_y0
WARNINGS.append(("D1-T1 bell rope vs the shaft base",
                 f"the rope hangs at Y {rope['loc'][1]:.0f}, only {gap:.0f} cm inside the shaft base's S inner wall (Y {inner_y0:.0f}); the sally (O 9, r 4.5) plus 2 cm sway "
                 f"needs 6.5, so it can clip the inner wall by {max(0.0, 6.5 - gap):.1f} cm in Z 240-340. Proposed: make the shaft base inner opening 5 cm wider on that wall or move the "
                 f"rope to Y 1835 (a 5 cm nudge that also stays in the floor hole Y 1820-1850)."))
# inscription flush
WARNINGS.append(("D1-B1 inscription tablet flush",
                 "D1.6.2 keeps the parent Plaque's relative transform (0,0,0), but the parent Plaque is a centred cube (back at X 11990..12000 -> centre 11995) whereas "
                 "M4 has its pivot at the back centre: back at X 11995, front at 11985, a 5 cm gap to the wall. Proposed: Plaque relative X = -2 (local, x2.5 root scale = 5 cm)."))
# rafter lean
WARNINGS.append(("D1-D1 collapse rafter lean",
                 "D1.7: 'one rafter leaning from the floor (11300, 2330) up to the arcade wall top' is not reachable with a 260 cm rafter (the arcade wall top is Z 620); "
                 "implemented as leaning against the arcade face (Y 2290), top at Z 258."))
# pier height naming
WARNINGS.append(("D1-P1 pier piece name",
                 "C6/C7 are named ...x640 but the table puts the coping top at z 620 (and arches end at world 620); mbounds use 620. P10-3b should either keep 620 and drop 640 "
                 "from the name or confirm the 20 cm block."))
WARNINGS.append(("D1-C1 C11 pivots",
                 "C11 (GraveSlab, GraveCross, GarthCross) gives no pivot; the generator assumes bottom centre (positions in D1.3 are centres)."))
WARNINGS.append(("D1-L1 lantern list",
                 "D1.7 'every light position that says lantern': implemented for L_Cl_Bells, L_Cl_Door, L_Cl_Entry and L_Ps_Lantern; L_Cl_West and L_Tw_Base are 2200 K "
                 "lights without the word 'lantern' and get no mesh."))
WARNINGS.append(("D1-M1 cell leaf height",
                 "the Dungeon door leaf at scale (0.5, 1.15, 1.2) is 110 x 219 cm in a 110 x 250 cm opening: 31 cm of the dark back panel shows above the leaf."))


# =====================================================================================================
# more D1 consistency notes that need the full record set
# =====================================================================================================
WARNINGS.append(("D1-G1 Note_Cloister vs the garth bed",
                 "the S coping (top Z 100, spans Y 1396-1430) and CLA_GarthBed (origin Y 1400, mounds up to Z 110) overlap in plan for Y 1400-1430, where Note_Cloister "
                 "(10750, 1425, 100.25) lies: a 2-10 cm mound would bury the note. Proposed: the bed mesh stays flat (<= 0.2) within 35 of the S edge, or starts at y 35."))
WARNINGS.append(("D1-T2 L_Tw_Bell inside the frame post",
                 "L_Tw_Bell (12290, 1865, 2700) is inside the SW post of the bell frame (X 12267.5-12292.5, Y 1852.5-1877.5, Z 2500-2865); shadowless so it does not matter, "
                 "but P10-7 may want it 15 cm off the post face."))

# =====================================================================================================
# OUTPUTS
# =====================================================================================================
ALL_OK = all(ok for _, _, ok, _ in CHECKS)
SUMMARY_CAT = {}
SUMMARY_GROUP = {}
for r in RECS:
    SUMMARY_CAT[r["cat"]] = SUMMARY_CAT.get(r["cat"], 0) + 1
    SUMMARY_GROUP[r["group"]] = SUMMARY_GROUP.get(r["group"], 0) + 1

out_json = {
    "generator": "Tools/belltower/gen_tower_layout.py", "units": "cm, UE world; rot = [pitch, yaw, roll]; mbounds = mesh-local [min, max]",
    "n_roof_fix_applied": N_ROOF_FIX, "all_checks_pass": ALL_OK, "counts": SUMMARY_CAT, "group_counts": SUMMARY_GROUP,
    "checks": [{"group": g, "name": n, "ok": ok, "detail": d} for g, n, ok, d in CHECKS],
    "warnings": [{"id": n, "detail": d} for n, d in WARNINGS],
    "mi_paths": MI_PATHS, "slot_mi": SLOT_MI, "wood": {"tower": WOOD_TOWER, "cloister": WOOD_CLOISTER},
    "pieces": PIECES,
    "existing_meshes": {p: {"mbounds": [list(v[0][0]), list(v[0][1])], "slots": v[1], "estimated": p in EST_BOUNDS} for p, v in EXISTING.items()},
    "hide_greybox": HIDE, "keep_visible": KEEP_VISIBLE, "ground_materials": {k: MI_PATHS[v] for k, v in GROUND_MI.items()},
    "lights_plan": LIGHTS_PLAN,
    "mech_ritual3_target": {"loc": list(MECH3_LOC), "yaw": 0.0, "footprint_used_for_clearance": [110, 110]},
    "placements": RECS,
}
os.makedirs(os.path.join(ROOT, "Docs", "plans"), exist_ok=True)
os.makedirs(SURVEY, exist_ok=True)
with open(os.path.join(ROOT, "Docs", "plans", "p10_d1_layout.json"), "w", encoding="utf-8") as f:
    json.dump(out_json, f, indent=1)


def fmt(v, n=2):
    return "(" + ", ".join(f"{round(float(x), n):g}" for x in v) + ")"


def short(m):
    return m.split("/")[-1].split(".")[0]


MD = ["# P10 D1 placement tables (generated)", "",
      "Generated by `Tools/belltower/gen_tower_layout.py` (do not edit by hand; change the generator, re-run it, and commit the generator with its outputs). "
      "World cm; rotation = (pitch, yaw, roll); AABB = expected world bounds from the mesh-local bounds in the D1 piece tables (P10-5 read-back tolerance 3 cm). "
      "Machine-readable copy: `Docs/plans/p10_d1_layout.json` (key `placements`).", "",
      "Records tagged `REFERENCE ONLY` (`extras.skip_place`) are placed by the child Blueprints in P10-6b, not by P10-5; they are in the layout for the lane check and the expected bounds.", "",
      "Counts by category: " + ", ".join(f"{k} {v}" for k, v in sorted(SUMMARY_CAT.items())) + f"; {len(RECS)} records.", "",
      "## Checks (D1.9)", "", "| Group | Check | Result | Numbers |", "|---|---|---|---|"]
for g, n, ok, d in CHECKS:
    MD.append(f"| {g} | {n} | {'PASS' if ok else '**FAIL**'} | {d} |")
MD += ["", f"**Overall: {'PASS' if ALL_OK else 'FAIL'}**" + (" (N-walk roof fix applied)" if N_ROOF_FIX else ""), "", "## D1 consistency notes (not failures)", ""]
for n, d in WARNINGS:
    MD.append(f"- **{n}**: {d}")
MD += ["", "## Lane clearances", "",
       "Clearance = distance from the sampled walk line (or the routed Warden path) to the nearest non-exempt record footprint inside the height band, minus the Warden radius 42 for Warden points/paths. "
       "Exempt: floors, vaults and roofs above Z 300, balustrades, decals, and records flush (<= 8.5) with a greybox collision face.", "",
       "| Path / point | Kind | Min clearance (cm) | Nearest record |", "|---|---|---|---|"]
for nm, kind, c, who in LANE_ROWS:
    if c < 200 or nm.startswith("WP_CryptToCloister"):
        MD.append(f"| {nm} | {kind} | {c:.1f} | {who} |")
MD.append(f"| (the other {sum(1 for x in LANE_ROWS if x[2] >= 200 and not x[0].startswith('WP_Crypt'))} TowerStairs segments have > 200) | | | |")
for nm, straight, L, c, who in PATROL_ROWS:
    MD.append(f"| {nm} | Patrol (straight {straight:.0f}" + (f", routed {L:.0f}" if L and abs(L - straight) > 1 else "") + f") | {c:.1f} | {who} |")
for nm, c, who in pt_rows:
    MD.append(f"| {nm} | AI point | {c:.1f} | {who} |")
MD += ["", "Straight-line distance of the patrol segments to the new colliders (blocks, heap, Mech_Ritual3, bells), minus 42:", ""]
for nm, d, who in STRAIGHT_ROWS:
    MD.append(f"- {nm}: {d:.1f} ({who})")
MD += ["", "## Greybox (D1.0)", "",
       f"`hide_greybox` in the JSON lists {len(HIDE)} actors to set not visible (collision unchanged): the {len(HIDE) - 2} actors of the folders Cloister (23), BellTower (24), "
       "BellTower/Stairs (154), BellTower/Railings (77), plus `Passage_S` and `Passage_N`. Kept visible: " + ", ".join(KEEP_VISIBLE) + ".", "",
       "Ground slabs `Ground_1`, `Ground_2`, `Ground_4`, `Ground_6` get `MI_Kit_Floor` (`ground_materials`).", ""]
MD += ["## Pieces (new Blender pieces; mbounds from the D1 tables)", "", "| Piece | Folder | mbounds min | mbounds max | Slots | Seed | UCX | Pivot / note |", "|---|---|---|---|---|---|---|---|"]
for nm, p in PIECES.items():
    MD.append(f"| {nm} | {p['path'].rsplit('/', 1)[0].split('Environments/')[-1]} | {fmt(p['mbounds'][0], 1)} | {fmt(p['mbounds'][1], 1)} | {', '.join(p['slots'])} | "
              f"{p['seed'] if p['seed'] is not None else '-'} | {p['ucx']} | {p['pivot']}; {p['note']} |")
MD.append("")

SECTIONS = [
    ("Hidden collision blocks (8)", lambda r: r["group"] == "block"),
    ("Tower shell wall pieces (12)", lambda r: r["group"] == "shell"),
    ("Tower floor", lambda r: r["id"] == "TWA_Floor"),
    ("Stair flights (11)", lambda r: r["group"] == "flight"),
    ("Flight rails (11)", lambda r: r["group"] == "flightrail"),
    ("Landings (10)", lambda r: r["group"] == "landing"),
    ("Shaft base, posts, partition", lambda r: r["group"] in ("shaftbase", "shaftpost", "partition")),
    ("Belfry: floor, top rails, louvres (8), bell frame, headstock, rope, roof", lambda r: r["group"] in ("belfryfloor", "toprail", "louvre", "bellframe", "headstock", "rope", "towerroof")),
    ("Cloister, passage and stair-house wall pieces and archways", lambda r: r["group"] in ("wallpiece", "archway") and r["id"].split("_")[1] == "Wall" or r["group"] == "archway" or r["id"] == "SHA_Gable_S"),
    ("Arcade: piers (10), corner piers (4), arches (14)", lambda r: r["group"] in ("pier", "pier_corner", "arch")),
    ("Garth", lambda r: r["cat"] == "garth"),
    ("Vault bays (10)", lambda r: r["group"] == "vaultbay"),
    ("Corbels", lambda r: r["group"] == "corbel"),
    ("Roof panels (12) and the stair-house roof", lambda r: r["group"] in ("roofpanel", "stairhouseroof")),
    ("Cloister floors", lambda r: r["id"].startswith("CLA_Floor_")),
    ("Cell doors (5) and leaves (5)", lambda r: r["group"] in ("celldoor", "cellleaf")),
    ("Gameplay references (placed by the child Blueprints)", lambda r: r["cat"] == "gameplay"),
]
done = set()
for title, flt in SECTIONS:
    rows = [r for r in RECS if flt(r) and r["id"] not in done]
    if not rows:
        continue
    done.update(r["id"] for r in rows)
    MD += [f"## {title} ({len(rows)})", "", "| Label | Mesh | Location | Rotation | Scale | AABB min .. max | Collision | Note |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        MD.append(f"| {r['id']} | {short(r['mesh'])} | {fmt(r['loc'])} | {fmt(r['rot'])} | {fmt(r['scale'], 4)} | {fmt(r['aabb_min'], 1)} .. {fmt(r['aabb_max'], 1)} | "
                  f"{r['collision']} | {r['note']} |")
    MD.append("")
dress = [r for r in RECS if r["id"] not in done and r["cat"] not in ("light",)]
big = [r for r in dress if r["group"] in ("garthveg", "weed")]
rest = [r for r in dress if r not in big]
MD += [f"## Dressing ({len(rest)} listed here, plus {len(big)} garth vegetation and passage weeds listed in the JSON only)", "",
       "| Label | Mesh | Location | Rotation | Scale | Collision | Note |", "|---|---|---|---|---|---|---|"]
for r in rest:
    MD.append(f"| {r['id']} | {short(r['mesh'])} | {fmt(r['loc'])} | {fmt(r['rot'])} | {fmt(r['scale'], 4)} | {r['collision']} | {r['note']} |")
MD += ["", "Garth vegetation (seed 1224): " + str(sum(1 for r in big if r['group'] == 'garthveg')) + " actors `CLA_GarthGrass_00..39`, `CLA_GarthNettle_00..11`, `CLA_GarthFern_00..07` "
       "(Z 100-105, inside X 10320-11380, Y 1420-2180, >= 50 clear of the cross base, slabs, small crosses and Note_Cloister). Passage weeds (seed 1402): 20 actors `PSA_Weed_00..19` "
       "within 24 of the passage wall bases.", ""]
MD += ["## Lights (D1.8)", "", "Delete: " + ", ".join(LIGHTS_PLAN["delete"]) + ". Keep and tune `Light_TowerExt_0..2` to 200-400 lm. Fog volume `LFV_Tower` X 12040-12960, Y 1540-2460, Z 0-3500. "
       "All new lights are PointLights, shadowless.", "",
       "| Label | Location | Lumens | Radius | Colour | Note |", "|---|---|---|---|---|---|"]
for r in RECS:
    if r["cat"] == "light":
        L = r["extras"]["light"]
        col = f"{L['temperature_K']} K" if "temperature_K" in L else "linear " + fmt(L["color_linear"])
        MD.append(f"| {r['id']} | {fmt(r['loc'])} | {L['lumens']} | {L['radius']} | {col} | {r['note']} |")
MD.append("")
with open(os.path.join(ROOT, "Docs", "plans", "p10_d1_tables.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(MD))


# =====================================================================================================
# PLAN IMAGES (PIL)
# =====================================================================================================
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:      # the checks and the JSON/tables are the deliverable; the images need Pillow
    Image = None


def _font(sz):
    for nm in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nm, sz)
        except Exception:
            pass
    return ImageFont.load_default()


def draw_plan():
    S = 0.36
    X0, X1, Y0, Y1 = 5900.0, 13100.0, -350.0, 3150.0
    W, H = int((X1 - X0) * S), int((Y1 - Y0) * S)
    INSET = 920
    pad_top, pad_bot = 70, 170
    img = Image.new("RGB", (W + INSET + 40, H + pad_top + pad_bot), (24, 24, 28))
    dr = ImageDraw.Draw(img, "RGBA")
    f8, f10, f12, f16 = _font(11), _font(13), _font(16), _font(22)

    def px(x):
        return (x - X0) * S

    def py(y):
        return pad_top + (Y1 - y) * S

    def rect(mn, mx, fill=None, outline=None, width=1):
        dr.rectangle([px(mn[0]), py(mx[1]), px(mx[0]), py(mn[1])], fill=fill, outline=outline, width=width)

    def label(x, y, t, fill=(220, 220, 220), f=f10):
        dr.text((px(x), py(y)), t, fill=fill, font=f)

    # greybox collision footprints
    for lbl, g in GREYBOX.items():
        if g["folder_query"] in ("Cloister", "BellTower") or lbl in ("Passage_S", "Passage_N"):
            if lbl.startswith("Tw_Landing") or lbl.startswith("Top_") or lbl.startswith("Bell_") or lbl == "Tw_Roof":
                continue
            mn, mx = gb(lbl)
            rect(mn, mx, fill=(58, 58, 66), outline=(110, 110, 124))
    # floors
    for r in RECS:
        if r["cat"] == "floor":
            rect(r["aabb_min"], r["aabb_max"], fill=(34, 46, 40), outline=(60, 80, 66))
    # roof panels and vaults (outline only)
    for r in RECS:
        if r["group"] == "roofpanel":
            rect(r["aabb_min"], r["aabb_max"], outline=(150, 100, 70))
        if r["group"] == "vaultbay":
            rect(r["aabb_min"], r["aabb_max"], outline=(100, 140, 230))
    # art footprints
    PAL = {"wallpiece": (190, 164, 118), "archway": (230, 180, 90), "shell": (170, 146, 108), "pier": (240, 240, 240), "pier_corner": (240, 240, 240),
           "arch": (200, 200, 210), "garthwall": (130, 170, 110), "garthbed": (60, 90, 52), "graveslab": (170, 170, 175), "gravecross": (170, 170, 175),
           "garthcross": (230, 230, 235), "celldoor": (255, 140, 60), "cellleaf": (255, 140, 60), "stairhouseroof": (150, 100, 70)}
    for r in RECS:
        c = PAL.get(r["group"])
        if c and r["group"] not in ("stairhouseroof",):
            rect(r["aabb_min"], r["aabb_max"], fill=c + (230,), outline=(0, 0, 0, 160))
    for r in RECS:
        if r["group"] in ("flight",):
            rect(r["aabb_min"], r["aabb_max"], outline=(240, 150, 50, 255))
        if r["group"] == "landing":
            rect(r["aabb_min"], r["aabb_max"], outline=(250, 220, 100, 255))
        if r["group"] in ("shaftbase",):
            rect(r["aabb_min"], r["aabb_max"], outline=(240, 240, 240, 255), width=2)
        if r["group"] == "shaftpost":
            rect(r["aabb_min"], r["aabb_max"], fill=(120, 200, 120, 255))
        if r["group"] == "block":
            rect(r["aabb_min"], r["aabb_max"], fill=(230, 40, 40, 220))
        if r["group"] == "collapse" and r["id"] == "CLA_Collapse_Heap":
            rect(r["aabb_min"], r["aabb_max"], fill=(170, 110, 90, 200), outline=(255, 90, 60))
        elif r["group"] == "collapse":
            rect(r["aabb_min"], r["aabb_max"], outline=(190, 150, 120, 200))
        if r["cat"] == "gameplay":
            rect(r["aabb_min"], r["aabb_max"], outline=(255, 90, 230, 255), width=2)
        if r["cat"] == "dress" and r["group"] in ("lantern", "cell", "mech3chain", "chain", "ivy", "chamberdebris", "towerdress"):
            cx, cy = (r["aabb_min"][0] + r["aabb_max"][0]) / 2, (r["aabb_min"][1] + r["aabb_max"][1]) / 2
            dr.ellipse([px(cx) - 2, py(cy) - 2, px(cx) + 2, py(cy) + 2], fill=(235, 235, 120, 255))
    # WalkPaths and AI points
    wp = [(p[0], p[1]) for _, p in WP_TOWER]
    dr.line([(px(x), py(y)) for x, y in wp], fill=(0, 210, 235, 255), width=2)
    for x, y in wp:
        dr.ellipse([px(x) - 2.5, py(y) - 2.5, px(x) + 2.5, py(y) + 2.5], fill=(0, 210, 235, 255))
    cc = [(p[0], p[1]) for _, p in WP_CRYPT[7:]]
    dr.line([(px(x), py(y)) for x, y in cc], fill=(0, 210, 235, 255), width=2)
    for k, (nm, a) in enumerate(PATROL):
        path = PATROL_PATHS[f"{nm}->{PATROL[(k + 1) % len(PATROL)][0]}"]
        dr.line([(px(x), py(y)) for x, y in path], fill=(255, 80, 80, 255), width=2)
    for k, (nm, a) in enumerate(PATROL):
        dr.ellipse([px(a[0]) - 5, py(a[1]) - 5, px(a[0]) + 5, py(a[1]) + 5], fill=(255, 80, 80, 255), outline=(255, 255, 255))
        dr.text((px(a[0]) + 7, py(a[1]) - 14), f"P{k + 1}", fill=(255, 150, 150), font=f10)
    for nm, a in SEARCH:
        dr.ellipse([px(a[0]) - 3, py(a[1]) - 3, px(a[0]) + 3, py(a[1]) + 3], fill=(255, 170, 0, 255))
        dr.text((px(a[0]) + 4, py(a[1]) + 1), nm[-2:], fill=(255, 190, 80), font=f8)
    for nm, a in SPAWN:
        dr.polygon([(px(a[0]), py(a[1]) - 7), (px(a[0]) - 6, py(a[1]) + 5), (px(a[0]) + 6, py(a[1]) + 5)], fill=(230, 80, 255, 255))
        dr.text((px(a[0]) + 8, py(a[1]) - 6), nm, fill=(230, 130, 255), font=f8)
    # lights
    for r in RECS:
        if r["cat"] == "light":
            L = r["extras"]["light"]
            rr_ = min(L["radius"], 600) * S
            cx, cy = px(r["loc"][0]), py(r["loc"][1])
            dr.ellipse([cx - rr_, cy - rr_, cx + rr_, cy + rr_], outline=(255, 225, 120, 90))
            dr.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(255, 235, 120, 255), outline=(0, 0, 0))
            dr.text((cx + 6, cy - 12), r["id"][2:], fill=(255, 235, 150), font=f8)
    # area labels
    label(6200, 2420, "PASSAGE (600 wide, X 6040-9460)", f=f12)
    label(9650, 3080, "CLOISTER (inner X 9500-12000, Y 540-3000)", f=f12)
    label(12100, 3080, "BELL TOWER", f=f12)
    label(10240, 20, "STAIR-HOUSE (trench X 10500-10800)", f=f10)
    label(10700, 1790, "GARTH", fill=(160, 200, 140), f=f12)
    label(11640, 1735, "Mech3", fill=(255, 130, 240), f=f10)
    label(11110, 2390, "collapse", fill=(255, 140, 100), f=f10)
    label(6020, 2120, "Door_Shortcut", fill=(200, 200, 200), f=f8)
    dr.text((10, 6), "P10 D1 layout plan: cloister + passage + tower, top view (X right, Y up), 1 px = %.1f cm. Generated by gen_tower_layout.py" % (1 / S), fill=(240, 240, 240), font=f16)
    dr.text((10, 38), "Grey = hidden greybox collision. Sand = wall pieces, white = piers/arches, green = garth, blue outline = vault bays, brown outline = roof panels, orange outline = flights, "
                      "yellow outline = landings, red fill = hidden blocks, magenta = gameplay references.", fill=(190, 190, 190), font=f10)
    ly = H + pad_top + 10
    dr.text((10, ly), "Cyan = WalkPaths (TowerStairs, CryptToCloister 07..10). Red = Patrol_Cloister route P1..P7 (07->01 wrap-around is the routed detour around the garth and the new blocks). "
                      "Orange dots = Search_Cloister_xx. Magenta triangles = WSpawn. Yellow rings = new lights (radius capped at 600).", fill=(190, 190, 190), font=f10)
    dr.text((10, ly + 18), "Clearance results (D1.9 check 2): see p10_d1_tables.md. Worst: Mech_Ritual3 vs Patrol_Cloister_04->05 = %.1f cm, vs Search_Cloister_06 = %.1f cm (limit 60 after the Warden radius 42)."
            % (PATROL_ROWS[3][3], dict((n, c) for n, c, _ in pt_rows)["Search_Cloister_06"]), fill=(190, 190, 190), font=f10)

    # ---- tower inset (0.9 px/cm)
    S2 = 0.9
    ox, oy = W + 25, pad_top + 20

    def qx(x):
        return ox + (x - 12000.0) * S2

    def qy(y):
        return oy + (2500.0 - y) * S2

    def qrect(mn, mx, fill=None, outline=None, width=1):
        dr.rectangle([qx(mn[0]), qy(mx[1]), qx(mx[0]), qy(mn[1])], fill=fill, outline=outline, width=width)

    dr.text((ox, pad_top - 24), "BELL TOWER plan (all levels overlaid)", fill=(240, 240, 240), font=f12)
    qrect((12000, 1500), (13000, 2500), fill=(40, 40, 46), outline=(160, 140, 100), width=3)
    qrect((12040, 1540), (12960, 2460), outline=(90, 90, 100))
    qrect((12290, 1790), (12710, 2210), fill=(60, 60, 68), outline=(180, 180, 190))
    for k in range(1, 12):
        r = rec_by_id(f"TWA_Flight_F{k:02d}")
        qrect(r["aabb_min"], r["aabb_max"], outline=(240, 150, 50))
        cx, cy = (r["aabb_min"][0] + r["aabb_max"][0]) / 2, (r["aabb_min"][1] + r["aabb_max"][1]) / 2
        head = FLIGHTS[k][0]
        d = {"N": (1, 0), "E": (0, -1), "S": (-1, 0), "W": (0, 1)}[head]
        dr.line([(qx(cx - 120 * d[0]), qy(cy - 120 * d[1])), (qx(cx + 120 * d[0]), qy(cy + 120 * d[1]))], fill=(255, 190, 90), width=2)
        dr.polygon([(qx(cx + 120 * d[0]), qy(cy + 120 * d[1])), (qx(cx + 80 * d[0] - 18 * d[1]), qy(cy + 80 * d[1] + 18 * d[0])),
                    (qx(cx + 80 * d[0] + 18 * d[1]), qy(cy + 80 * d[1] - 18 * d[0]))], fill=(255, 190, 90))
        dr.text((qx(cx) - 10, qy(cy) + 6), f"F{k:02d}", fill=(255, 210, 140), font=f10)
    for n in range(1, 11):
        r = rec_by_id(f"TWA_Landing_{n:02d}")
        qrect(r["aabb_min"], r["aabb_max"], outline=(250, 220, 100))
        cx, cy = (r["aabb_min"][0] + r["aabb_max"][0]) / 2, (r["aabb_min"][1] + r["aabb_max"][1]) / 2
        dr.text((qx(cx) - 8 + (n % 3) * 9 - 9, qy(cy) - 22 + (n // 4) * 13), f"L{n}", fill=(250, 230, 120), font=f8)
    for r in RECS:
        if r["group"] == "shaftpost":
            qrect(r["aabb_min"], r["aabb_max"], fill=(120, 210, 120))
        if r["group"] == "block":
            if r["id"].startswith("Tw_"):
                qrect(r["aabb_min"], r["aabb_max"], fill=(230, 40, 40))
        if r["group"] in ("bellframe",):
            qrect(r["aabb_min"], r["aabb_max"], outline=(120, 170, 255), width=2)
        if r["group"] == "partition":
            qrect(r["aabb_min"], (r["aabb_max"][0] + 3, r["aabb_max"][1]), fill=(200, 160, 100))
        if r["group"] == "louvre":
            qrect(r["aabb_min"], r["aabb_max"], fill=(120, 170, 255))
        if r["group"] == "rope":
            dr.ellipse([qx(12550) - 3, qy(1830) - 3, qx(12550) + 3, qy(1830) + 3], fill=(255, 120, 120))
        if r["group"] == "greatbell":
            qrect(r["aabb_min"], r["aabb_max"], outline=(255, 90, 230), width=2)
        if r["group"] == "chamberdebris":
            qrect(r["aabb_min"], r["aabb_max"], fill=(190, 150, 110))
    qrect((12530, 1820), (12560, 1850), outline=(255, 120, 120))
    # door
    qrect((12000, 1948), (12040, 2052), fill=(24, 24, 28), outline=(255, 255, 255))
    dr.text((qx(12044), qy(2070)), "door", fill=(255, 255, 255), font=f8)
    wpl = [(qx(p[0]), qy(p[1])) for _, p in WP_TOWER]
    dr.line(wpl, fill=(0, 210, 235), width=2)
    for i, (x, y) in enumerate(wpl):
        dr.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(0, 210, 235))
        dr.text((x + 4, y - 11), str(i), fill=(120, 230, 245), font=f8)
    for nm, a in SPAWN:
        if nm == "WSpawn_Tower":
            dr.polygon([(qx(a[0]), qy(a[1]) - 8), (qx(a[0]) - 7, qy(a[1]) + 6), (qx(a[0]) + 7, qy(a[1]) + 6)], fill=(230, 80, 255))
    for r in RECS:
        if r["cat"] == "light" and r["id"].startswith("L_Tw"):
            dr.ellipse([qx(r["loc"][0]) - 4, qy(r["loc"][1]) - 4, qx(r["loc"][0]) + 4, qy(r["loc"][1]) + 4], fill=(255, 235, 120), outline=(0, 0, 0))
    ty = qy(1500) + 14
    for i, t in enumerate(("Tower plan: orange = flights with climb arrows (F01 N ring +X, counter-clockwise), yellow = landings L1..L10, green = shaft posts on the core corners,",
                           "red = hidden BlockAll (under-stair and 3 broken-tread blocks), blue = louvres / bell frame, pink = great bell footprint, cyan = WalkPath 00..24",
                           "(numbers), magenta triangle = WSpawn_Tower. Core (grey, X 12290-12710) is the invisible collision; the shaft base covers its faces up to Z 450.")):
        dr.text((ox, ty + 15 * i), t, fill=(190, 190, 190), font=f8)
    img.save(os.path.join(SURVEY, "d1_layout_plan.png"))


def draw_section():
    S = 0.2
    Zmin, Zmax = -80.0, 4880.0
    HEADER, FOOT = 90, 100
    HH = int((Zmax - Zmin) * S)
    WA = 300
    # unrolled stair profile geometry ------------------------------------------------------------------
    segs = []     # (kind, s0, s1, z0, z1, label)
    s = 0.0
    segs.append(("ground", s, s + 300.0, 0.0, 0.0, "door -> NW pad"))
    s += 300.0
    tread_pos = []      # (k, i, s_from, s_to, top)
    land_pos = {}
    for k in range(1, 12):
        base = FLIGHTS[k][3]
        for i in range(14):
            tread_pos.append((k, i, s + 30.0 * i, s + 30.0 * i + 30.0, base + RISE_T * (i + 1)))
        s += 420.0
        if k < 11:
            land_pos[k] = (s, s + 250.0, LANDINGS[k][3])
            s += 250.0
    s_end = s + 250.0
    WC = int(s_end * S) + 60
    GAP = 40
    Wtot = 40 + WA + GAP + WA + GAP + WC + 40
    img = Image.new("RGB", (Wtot, HH + HEADER + FOOT), (24, 24, 28))
    dr = ImageDraw.Draw(img, "RGBA")
    f8, f10, f12, f16 = _font(11), _font(13), _font(16), _font(22)

    def pz(z):
        return HEADER + (Zmax - z) * S

    dr.text((10, 6), "P10 D1 tower section: vertical sections A (Y=2000, looking +Y) and B (X=12500, looking -X), and the unrolled stair profile along the WalkPath (right)", fill=(240, 240, 240), font=f16)
    dr.text((10, 38), "Shared Z axis (1 px = 5 cm). Grey = shell walls with slit/door openings, orange = stairs, yellow = landings, green = shaft posts, red = hidden blocks, "
                      "blue = bell frame / headstock / bell, brown = roof.", fill=(190, 190, 190), font=f10)
    dr.text((10, 58), "Z ticks every 500 cm. Stage joints at 800 and 2500; courses: plinth 0-60, drip 1210-1230, belfry sill 2470-2500, cornice 3480-3540. Roof apex 4740, cross to 4830.", fill=(190, 190, 190), font=f10)
    for z in range(0, 4881, 500):
        dr.line([(0, pz(z)), (Wtot, pz(z))], fill=(46, 46, 52))
        dr.text((2, pz(z) - 12), str(z), fill=(140, 140, 150), font=f8)

    def panel(x0, horiz_lo, horiz_hi, ranges_mode):
        """returns a function mapping a world horizontal coordinate to a pixel x"""
        return lambda u: x0 + (u - horiz_lo) * S

    # ---------- panel A: section Y=2000, horizontal = X (12000..13000) ----------
    ax0 = 40 + 20
    ha = lambda u: ax0 + (u - 11950.0) * S
    # panel B: section X=12500, horizontal = Y (1500..2500), W (low Y) to the left
    bx0 = 40 + WA + GAP + 20
    hb = lambda u: bx0 + (u - 1450.0) * S

    def shell_panel(h, lo, hi, slits, door, name):
        """walls as two columns at lo..lo+40 and hi-40..hi, with gaps"""
        for (a, b) in ((lo, lo + 40.0), (hi - 40.0, hi)):
            dr.rectangle([h(a), pz(3540.0), h(b), pz(0.0)], fill=(96, 96, 104), outline=(150, 150, 160))
        for (side, z, hh) in slits:                   # side 0 = lo wall, 1 = hi wall
            a = (lo, lo + 40.0) if side == 0 else (hi - 40.0, hi)
            dr.rectangle([h(a[0]), pz(z + hh / 2.0), h(a[1]), pz(z - hh / 2.0)], fill=(24, 24, 28), outline=(250, 220, 110))
        if door:
            dr.rectangle([h(lo), pz(228.0), h(lo + 40.0), pz(0.0)], fill=(24, 24, 28), outline=(250, 220, 110))
        # stage joints and courses
        for z in (800.0, 2500.0):
            dr.line([(h(lo - 14), pz(z)), (h(hi + 14), pz(z))], fill=(60, 60, 70))
        for z0, z1, pr in ((0, 60, 10), (1210, 1230, 8), (2470, 2500, 10), (3480, 3540, 15)):
            dr.rectangle([h(lo - pr), pz(z1), h(lo), pz(z0)], fill=(150, 130, 100))
            dr.rectangle([h(hi), pz(z1), h(hi + pr), pz(z0)], fill=(150, 130, 100))
        dr.text((h(lo), pz(4880) + 0), name, fill=(240, 240, 240), font=f12)

    # A: slits at Y=2000 plane: W wall (side 0): F08 z 1854; E wall (side 1): F02 490.9, F06 600?? (S1_E slit F02 z 490.9; S2_E F06 z 600+800? see table: world = z0 + z)
    slitsA = [(0, 1854.0, 120.0), (1, 490.9, 120.0), (1, 800.0 + 600.0, 120.0), (1, 800.0 + 1509.1, 120.0)]
    shell_panel(ha, 12000.0, 13000.0, slitsA, True, "A: Y=2000, looking +Y")
    # B: N wall (side 1, Y 2460-2500): F01 263.6, F05 800+372.7, F09 800+1281.8; S wall (side 0): F03 718.1, F07 800+827.3
    slitsB = [(1, 263.6, 120.0), (1, 800.0 + 372.7, 120.0), (1, 800.0 + 1281.8, 120.0), (0, 718.1, 120.0), (0, 800.0 + 827.3, 120.0)]
    shell_panel(hb, 1500.0, 2500.0, slitsB, False, "B: X=12500, looking -X")

    def common(h, lo_i, hi_i, which):
        # ground, floors
        dr.rectangle([h(lo_i), pz(0.0), h(hi_i), pz(-38.5)], fill=(70, 66, 60))
        # core outline (hidden collision)
        c0, c1 = (12290.0, 12710.0) if which == "A" else (1790.0, 2210.0)
        dr.rectangle([h(c0), pz(2500.0), h(c1), pz(0.0)], outline=(90, 90, 100))
        # shaft base walls
        for (a, b) in ((c0, c0 + 35.0), (c1 - 35.0, c1)):
            dr.rectangle([h(a), pz(450.0), h(b), pz(0.0)], fill=(150, 150, 140), outline=(0, 0, 0))
        dr.rectangle([h(c0 + 35.0), pz(40.0), h(c1 - 35.0), pz(0.0)], fill=(100, 84, 70))
        # posts at the corners (projected)
        for a in (c0 - 10.0, c1 - 10.0):
            dr.rectangle([h(a), pz(2465.0), h(a + 20.0), pz(450.0)], fill=(90, 190, 90, 200))
        # landings projected: those on the side walls
        for n in range(1, 11):
            r = rec_by_id(f"TWA_Landing_{n:02d}")
            k0, k1 = (0, 0) if which == "A" else (1, 1)
            dr.rectangle([h(r["aabb_min"][k0]), pz(r["aabb_max"][2]), h(r["aabb_max"][k0]), pz(r["aabb_min"][2] + 20.0)], fill=(250, 220, 100, 120), outline=(250, 220, 100))
        # belfry floor at 2500
        if which == "A":
            dr.rectangle([h(12040.0), pz(2500.0), h(12720.0), pz(2465.0)], fill=(200, 160, 100))
            fr = rec_by_id("TWA_BellFrame")
            ax_ = lambda x: h(x)
            dr.rectangle([ax_(12255.0), pz(2520.0), ax_(12585.0), pz(2500.0)], fill=(120, 150, 255))
            for xx in (12280.0, 12560.0):
                dr.rectangle([ax_(xx - 12.5), pz(2865.0), ax_(xx + 12.5), pz(2520.0)], fill=(120, 150, 255))
            dr.rectangle([ax_(12255.0), pz(2865.0), ax_(12585.0), pz(2835.0)], fill=(120, 150, 255))
            dr.rectangle([ax_(12290.0), pz(2897.0), ax_(12550.0), pz(2863.0)], fill=(150, 120, 90))
            dr.ellipse([ax_(12420.0 - 130.0), pz(3010.0), ax_(12420.0 + 130.0), pz(2750.0)], outline=(150, 120, 90))
            # great bell profile (lathe)
            prof = [(0, 0), (6, 0), (6, -20), (55, -20), (65, -35), (75, -120), (98, -200), (105, -220)]
            pts = [(12420.0 + x, 2860.0 + z) for x, z in prof] + [(12420.0 - x, 2860.0 + z) for x, z in reversed(prof)]
            dr.polygon([(ax_(x), pz(z)) for x, z in pts], fill=(160, 120, 70), outline=(255, 200, 120))
            dr.line([(ax_(12550.0), pz(2750.0)), (ax_(12550.0), pz(140.0))], fill=(230, 190, 120), width=2)
            dr.text((ax_(12430.0), pz(2640.0) + 4), "great bell", fill=(255, 210, 140), font=f8)
        else:
            dr.rectangle([h(1540.0), pz(2500.0), h(2460.0), pz(2465.0)], fill=(200, 160, 100))
            dr.rectangle([h(1852.5), pz(2520.0), h(2147.5), pz(2500.0)], fill=(120, 150, 255))
            for yy in (1865.0, 2135.0):
                dr.rectangle([h(yy - 12.5), pz(2865.0), h(yy + 12.5), pz(2520.0)], fill=(120, 150, 255))
            dr.rectangle([h(1825.0), pz(2897.0), h(2165.0), pz(2863.0)], fill=(150, 120, 90))
            dr.ellipse([h(1830.0 - 5.0), pz(3010.0), h(1830.0 + 5.0), pz(2750.0)], outline=(150, 120, 90))
            prof = [(0, 0), (6, 0), (6, -20), (55, -20), (65, -35), (75, -120), (98, -200), (105, -220)]
            pts = [(2000.0 + x, 2860.0 + z) for x, z in prof] + [(2000.0 - x, 2860.0 + z) for x, z in reversed(prof)]
            dr.polygon([(h(x), pz(z)) for x, z in pts], fill=(160, 120, 70), outline=(255, 200, 120))
            dr.line([(h(1830.0), pz(2750.0)), (h(1830.0), pz(140.0))], fill=(230, 190, 120), width=2)
        # roof (pyramid, eaves +-525 about the centre)
        cx = 12500.0 if which == "A" else 2000.0
        dr.polygon([(h(cx - 525.0), pz(3530.0)), (h(cx), pz(4740.0)), (h(cx + 525.0), pz(3530.0)), (h(cx + 525.0), pz(3540.0)), (h(cx - 525.0), pz(3540.0))],
                   fill=(110, 80, 60, 200), outline=(200, 150, 110))
        dr.line([(h(cx), pz(4740.0)), (h(cx + 31.0), pz(4830.0))], fill=(220, 220, 230), width=2)
        # SW collapse window (dashed outline) on the -x / low-Y side
        dr.line([(h(cx - 525.0), pz(3530.0)), (h(cx - 100.0), pz(3530.0 + 860.0 * 0 + 0))], fill=(255, 90, 90), width=1)
        dr.text((h(cx - 520.0), pz(4300.0)), "SW quarter collapsed" if which == "A" else "(SW quarter off this plane)", fill=(255, 130, 110), font=f8)
        # belfry lancets outline on the far wall (A: N wall, B: W wall)
        if which == "A":
            for (a, b) in ((300.0, 430.0), (490.0, 620.0)):
                x0_, x1_ = 12040.0 + a, 12040.0 + b
                dr.line([(h(x0_), pz(2700.0)), (h(x0_), pz(3000.0)), (h((x0_ + x1_) / 2), pz(3262.6)), (h(x1_), pz(3000.0)), (h(x1_), pz(2700.0)), (h(x0_), pz(2700.0))],
                        fill=(120, 170, 255), width=1)
        else:
            for (a, b) in ((340.0, 470.0), (530.0, 660.0)):
                y0_, y1_ = 1500.0 + a, 1500.0 + b
                dr.line([(h(y0_), pz(2700.0)), (h(y0_), pz(3000.0)), (h((y0_ + y1_) / 2), pz(3262.6)), (h(y1_), pz(3000.0)), (h(y1_), pz(2700.0)), (h(y0_), pz(2700.0))],
                        fill=(120, 170, 255), width=1)

    common(ha, 12000.0, 13000.0, "A")
    common(hb, 1500.0, 2500.0, "B")
    # ---------- panel C: unrolled stair profile ----------
    cx0 = 40 + WA + GAP + WA + GAP
    hc = lambda sv: cx0 + sv * S
    dr.text((cx0, pz(4880.0)), "C: unrolled stair profile along the WalkPath (s = distance along the lane centre)", fill=(240, 240, 240), font=f12)
    dr.rectangle([hc(0.0), pz(0.0), hc(s_end), pz(-38.5)], fill=(70, 66, 60))
    for (k, i, s0_, s1_, top) in tread_pos:
        dr.rectangle([hc(s0_), pz(top), hc(s1_), pz(top - 24.0)], fill=(230, 140, 50), outline=(40, 20, 0))
    for k, (s0_, s1_, top) in land_pos.items():
        dr.rectangle([hc(s0_), pz(top), hc(s1_), pz(top - 40.0)], fill=(250, 220, 100), outline=(60, 50, 0))
        dr.text((hc(s0_) + 6, pz(top) - 14), f"L{k}", fill=(250, 230, 120), font=f8)
    s_cur = 300.0
    for k in range(1, 12):
        base = FLIGHTS[k][3]
        dr.text((hc(s_cur + 120), pz(base + 200.0) - 16), f"F{k:02d} {FLIGHTS[k][0]}", fill=(255, 210, 140), font=f8)
        # handrail line
        dr.line([(hc(s_cur), pz(base + RISE_T + 98.0)), (hc(s_cur + 420.0), pz(base + RISE_T * 15 + 98.0))], fill=(190, 150, 90), width=1)
        s_cur += 420.0 + 250.0
    # broken treads + hidden blocks
    for (k, i, ztop, nm) in ((3, 6, 568.2, "block F03"), (6, 3, 1201.3, "block F06"), (9, 6, 1931.8, "block F09")):
        s0_ = 300.0 + (k - 1) * 670.0 + 30.0 * i
        dr.rectangle([hc(s0_), pz(ztop + 200.0), hc(s0_ + 30.0), pz(ztop)], fill=(230, 40, 40, 200))
        dr.text((hc(s0_) - 14, pz(ztop + 200.0) - 13), nm, fill=(255, 120, 110), font=f8)
    # posts at the landings (corner posts Z 450-2465)
    for n, (corner, pt, yaw, top) in LANDINGS.items():
        if top + 5.0 >= 450.0:
            s0_ = land_pos[n][0] + 125.0
            dr.line([(hc(s0_), pz(2465.0)), (hc(s0_), pz(450.0))], fill=(90, 190, 90, 150), width=2)
    dr.text((hc(land_pos[2][0]) - 4, pz(2480.0) - 14), "shaft posts Z 450-2465 (one per core corner, beside the landings)", fill=(130, 220, 130), font=f8)
    # shaft base
    dr.rectangle([hc(0.0), pz(450.0), hc(300.0), pz(0.0)], outline=(220, 220, 210))
    dr.text((hc(6), pz(450.0) - 14), "shaft base Z 0-450", fill=(220, 220, 210), font=f8)
    # slits
    for (kf, zz) in ((1, 263.6), (2, 490.9), (3, 718.1), (5, 1172.7), (6, 1336.4), (7, 1627.3), (8, 1854.0), (9, 2081.8), (10, 2309.1)):
        s0_ = 300.0 + (kf - 1) * 670.0 + 210.0
        dr.polygon([(hc(s0_), pz(zz) - 6), (hc(s0_) + 4, pz(zz)), (hc(s0_), pz(zz) + 6), (hc(s0_) - 4, pz(zz))], fill=(255, 235, 110))
    # belfry floor
    dr.rectangle([hc(s_end - 250.0), pz(2500.0), hc(s_end), pz(2465.0)], fill=(200, 160, 100))
    dr.text((hc(s_end - 250.0), pz(2500.0) - 14), "belfry floor Z 2500", fill=(230, 200, 140), font=f8)
    # ticks
    for z in (0, 500, 1000, 1500, 2000, 2500):
        dr.line([(hc(0.0), pz(z)), (hc(s_end), pz(z))], fill=(52, 52, 60))
    img.save(os.path.join(SURVEY, "d1_tower_section.png"))


if Image is not None:
    draw_plan()
    draw_section()
else:
    print("Pillow missing: plan images not written")

# =====================================================================================================
# CONSOLE REPORT
# =====================================================================================================
print("Records:", len(RECS), "| by category:", ", ".join(f"{k} {v}" for k, v in sorted(SUMMARY_CAT.items())))
print("%-10s %-4s %s" % ("RESULT", "GRP", "CHECK"))
for g, n, ok, d in CHECKS:
    print(("PASS" if ok else "FAIL").ljust(6), g.ljust(10), n)
    print("          ", d)
if WARNINGS:
    print("\nD1 notes (not failures):")
    for n, d in WARNINGS:
        print(" -", n)
print("\nOVERALL:", "PASS" if ALL_OK else "FAIL")
sys.exit(0 if ALL_OK else 1)
