"""tw_timber.py -- stair flights, flight rails, landings, shaft base + posts, belfry floor, top rails, partition, louvres,
bell frame and headstock (D1.2 T1 ... T11).  Frames and pivots exactly as the D1 piece tables.
"""
import math
import random

from tw_common import *  # noqa: F401,F403
from tw_common import K, BK, BP, bmesh, Vector, Matrix, math, random

WD, IR = 0, 1
WI = ["MAT_Wood", "MAT_Iron"]
FLIGHT_RISE = 227.27272727272727
FR = FLIGHT_RISE / 14.0                    # tread rise 16.2338
SLOPE = FLIGHT_RISE / 420.0                # 0.5411


def tread_top(i):
    return FR * (i + 1)


def stringer_top(x):
    return FR + SLOPE * x + 8.0


# ============================================================================================== T1 stair flights
def _tread_box(i, ya=1.0, yb=249.0, dz=0.0, x0=None, x1=None):
    top = tread_top(i) + dz
    return timber(30.0 * i - 2.0 if x0 is None else x0, 30.0 * i + 30.0 if x1 is None else x1, ya, yb, top - 6.0, top, WD, 0.5)


def _broken_tread(i, rng):
    """Tread with the wall-side end (y 210..250) gone: three jagged prongs that stop at y <= 209.8."""
    x0, x1 = 30.0 * i - 2.0, 30.0 * i + 30.0
    top = tread_top(i)
    poly = [(x0, 1.0), (x1, 1.0), (x1, 203.0), (x1 - 3.0, 209.8), (x1 - 6.5, 198.0), (x1 - 11.0, 209.5), (x1 - 14.5, 196.0),
            (x1 - 20.0, 209.8), (x1 - 23.5, 199.0), (x1 - 27.0, 205.0), (x0, 200.0)]
    return [prism_xy(poly, top - 6.0, top, WD, 0.4)]


def _split_tread(i, y_split, gap, rng, drop_b):
    """Tread cut lengthwise at y_split: two halves with zig-zag edges and a `gap` wide crack; the second half sits drop_b lower."""
    x0, x1 = 30.0 * i - 2.0, 30.0 * i + 30.0
    top = tread_top(i)
    n = 9
    xs = [x0 + (x1 - x0) * k / (n - 1) for k in range(n)]
    za = [y_split - gap / 2.0 + rng.uniform(-0.9, 0.9) for _ in xs]
    zb = [y_split + gap / 2.0 + rng.uniform(-0.9, 0.9) for _ in xs]
    pa = [(x0, 1.0), (x1, 1.0)] + [(x, y) for x, y in zip(xs[::-1], za[::-1])]
    pb = [(x, y) for x, y in zip(xs, zb)] + [(x1, 249.0), (x0, 249.0)]
    return [prism_xy(pa, top - 6.0, top, WD, 0.3), prism_xy(pb, top - 6.0 - drop_b, top - drop_b, WD, 0.3)]


def build_flight(variant=""):
    seeds = {"": 1101, "Closed": 1101, "BrokenA": 1102, "BrokenB": 1103}
    rng = random.Random(seeds[variant])
    wood, iron = [], []
    for i in range(14):
        if variant == "BrokenA" and i == 6:
            wood += _broken_tread(i, rng)
        elif variant == "BrokenA" and i == 10:
            wood += _split_tread(i, 120.0, 2.4, rng, 0.35)
        elif variant == "BrokenB" and i == 3:
            wood += _broken_tread(i, rng)
        elif variant == "BrokenB" and i == 9:
            wood += _split_tread(i, 80.0, 1.2, rng, 0.25)
        else:
            wood.append(_tread_box(i))
    # stringers: 8 wide x 28 deep, top 8 above the nosing line, x -10 .. 430
    for (ya, yb) in ((0.0, 8.0), (242.0, 250.0)):
        zt0, zt1 = stringer_top(-10.0), stringer_top(430.0)
        if variant == "Closed":
            poly = [(-10.0, 0.0), (430.0, 0.0), (430.0, zt1), (-10.0, zt0)]
        else:
            poly = [(-10.0, zt0 - 28.0), (430.0, zt1 - 28.0), (430.0, zt1), (-10.0, zt0)]
        wood.append(prism_xz(poly, ya, yb, WD, 0.5))
    if variant == "Closed":
        for i in range(14):
            wood.append(timber(30.0 * i, 30.0 * i + 2.0, 8.0, 242.0, 0.0, tread_top(i) - 6.0, WD, 0.3))
    else:
        for x in (60.0, 210.0, 360.0):                    # iron wall brackets under the outer stringer (12 x 6 x 20, tongue 8 into the wall)
            zb = stringer_top(x) - 28.0
            iron.append(box(x - 6.0, x + 6.0, 244.0, 250.0, zb - 20.0, zb, IR, 0.4))
            iron.append(box(x - 6.0, x + 6.0, 250.0, 258.0, zb - 20.0, zb - 14.0, IR, 0.4))
    bm = join(wood + iron)
    free_all(*wood, *iron)
    note = {"": "14 oak treads (6 thick, y 1..249, nosing -2), open risers, 2 stringers 8 x 28, 3 iron brackets",
            "Closed": "as the base flight plus 2-thick riser boards and full-height side panels to z 0 (no brackets)",
            "BrokenA": "tread 6 lacks y 210..250 (3 prongs, max y 209.8); tread 10 split at y 120 (2.4 gap, halves 0.35 apart)",
            "BrokenB": "tread 3 lacks y 210..250 (3 prongs, max y 209.8); tread 9 cracked at y 80 (1.2 gap)"}[variant]
    nm = PREFIX + "StairFlight_250x420" + ("_" + variant if variant else "")
    return TP(nm, bm, WI, note=note)


# ============================================================================================== T2 flight rail
def build_flight_rail():
    rng = random.Random(1104)
    parts = []
    hr_top = lambda x: FR * (x / 30.0 + 1.0) + 98.0
    # inclined handrail 8 wide x 6 tall (top on the D1 line) and mid-rail with its top 50 lower
    for drop, h in ((0.0, 6.0), (50.0, 5.0)):
        poly = [(0.0, hr_top(0.0) - drop - h), (420.0, hr_top(420.0) - drop - h), (420.0, hr_top(420.0) - drop), (0.0, hr_top(0.0) - drop)]
        parts.append(prism_xz(poly, 0.0, 8.0, WD, 0.4))
    for x in (140.0, 280.0):                              # posts 8 x 8 from the stringer top up to the handrail underside
        parts.append(timber(x - 4.0, x + 4.0, 0.0, 8.0, stringer_top(x), hr_top(x) - 6.0, WD, 0.4))
    bm = join(parts)
    free_all(*parts)
    return TP(PREFIX + "FlightRail_420", bm, ["MAT_Wood"], note="flight frame, rail band y 0..8; handrail top = 16.2338 (x/30+1) + 98, mid-rail 50 lower, posts at x 140 / 280")


# ============================================================================================== T3 landing
def _corbel_x(xc_wall, y0, y1):
    """Stone corbel under the x = 250 edge: 40 deep (x 210..250), 30 wide, z -60..-25, ogee underside."""
    poly = [(xc_wall, -25.0), (xc_wall - 40.0, -25.0), (xc_wall - 40.0, -37.0), (xc_wall - 31.0, -47.0), (xc_wall - 16.0, -55.0), (xc_wall, -60.0)]
    return prism_xz(poly, y0, y1, 1, 0.8)


def _corbel_y(yc_wall, x0, x1):
    poly = [(yc_wall, -25.0), (yc_wall - 40.0, -25.0), (yc_wall - 40.0, -37.0), (yc_wall - 31.0, -47.0), (yc_wall - 16.0, -55.0), (yc_wall, -60.0)]
    p = K.prism(poly, 'x', x0, x1, 1)
    K.bevel_all(p, 0.8, 25.0)
    K.bm_set_mat(p, 1)
    return p


def build_landing():
    rng = random.Random(1105)
    parts = []
    for k in range(10):                                   # boards along x, 25 wide, top at z 0
        parts.append(timber(0.0, 250.0, 25.0 * k, 25.0 * (k + 1), -5.0, 0.0, 0, 0.15))
    for y in (30.0, 95.0, 160.0, 225.0):                  # joists 12 x 20 along x
        parts.append(timber(0.0, 250.0, y - 6.0, y + 6.0, -25.0, -5.0, 0, 0.4))
    for yc in (95.0, 160.0):                              # 2 corbels under the x = 250 edge
        parts.append(_corbel_x(250.0, yc - 15.0 + rng.uniform(-3, 3), yc + 15.0 + rng.uniform(-3, 3)))
    for xc in (75.0, 175.0):                              # 2 corbels under the y = 250 edge
        parts.append(_corbel_y(250.0, xc - 15.0, xc + 15.0))
    bm = join(parts)
    free_all(*parts)
    # slot order MAT_Wood, MAT_Masonry: wood index 0 (boards, joists), corbels index 1
    return TP(PREFIX + "Landing_250", bm, ["MAT_Wood", "MAT_Masonry"], note="top z 0; boards z -5..0; joists z -25..-5; corbels z -60..-25 under the x = 250 and y = 250 edges")


# ============================================================================================== T4 shaft base
def _chunk(rng, cx, cy, z_top, size):
    pts = []
    for _ in range(9):
        v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.8, 1.0)))
        if v.length < 0.4:
            v = v.normalized() * 0.6
        pts.append(Vector((cx + v.x * size, cy + v.y * size * 0.8, 0.0)) + Vector((0, 0, v.z * size * 0.6)))
    zmax = max(p.z for p in pts)
    pts = [p + Vector((0, 0, z_top - zmax)) for p in pts]
    return K.hull_from_points(pts, 2, merge_coplanar=False)


def build_shaft_base():
    rng = random.Random(1106)
    # slot order MAT_Masonry, MAT_Trim, MAT_Rubble, MAT_Wood
    wall_a, _c = BK.ashlar_body(420.0, 35.0, 0.0, 430.0, 1106, vary=True)
    wall_b, _c = BK.ashlar_body(350.0, 35.0, 0.0, 430.0, 1116, vary=True)
    parts = []
    n = K.bmesh.new()
    K.bm_append(n, wall_a)
    shift(n, -210.0, 175.0, 0.0)
    parts.append(n)
    s = K.bmesh.new()
    K.bm_append(s, wall_a)
    rot(s, 'Z', 180.0)
    shift(s, 210.0, -175.0, 0.0)
    parts.append(s)
    e = K.bmesh.new()
    K.bm_append(e, wall_b)
    rot(e, 'Z', 90.0)
    shift(e, 210.0, -175.0, 0.0)
    parts.append(e)
    w = K.bmesh.new()
    K.bm_append(w, wall_b)
    rot(w, 'Z', -90.0)
    shift(w, -210.0, 175.0, 0.0)
    parts.append(w)
    free_all(wall_a, wall_b)
    # coping z 430..450, outer faces flush, 3 cm inward overhang
    for (x0, x1, y0, y1) in ((-210, 210, 172, 210), (-210, 210, -210, -172), (172, 210, -172, 172), (-210, -172, -172, 172)):
        parts.append(timber(x0, x1, y0, y1, 430.0, 450.0, 1, 1.0))
    # rubble floor z 0..40 with chunks
    def f(a, b):
        r = math.hypot(a, b) / 175.0
        return 10.0 + 22.0 * K.fbm(a / 38.0, b / 38.0, 1106, 3) + 8.0 * max(0.0, 1.0 - r)
    parts.append(K.hf_solid(-175.0, 175.0, -175.0, 175.0, f, 0.0, 24, 24, ('x', 'y', 'z'), 2, rng))
    for _ in range(16):
        cx, cy = rng.uniform(-155, 155), rng.uniform(-155, 155)
        parts.append(_chunk(rng, cx, cy, min(40.0, f(cx, cy) + rng.uniform(2.0, 8.0)), rng.uniform(9.0, 22.0)))
    # two broken treads lying on the rubble (6 thick, 25 wide)
    for (cx, cy, yaw, ln, tilt, zc) in ((-55.0, -40.0, 28.0, 130.0, 7.0, 25.0), (60.0, 70.0, 112.0, 96.0, -9.0, 27.0)):
        poly = [(-ln / 2, -12.5), (ln / 2 - 4, -12.5), (ln / 2, -4.0), (ln / 2 - 9, 3.0), (ln / 2 - 2, 12.5), (-ln / 2, 12.5)]
        b = K.prism(poly, 'z', -3.0, 3.0, 3)
        K.bevel_all(b, 0.4, 25.0)
        K.bm_set_mat(b, 3)
        rot(b, 'Y', tilt)
        rot(b, 'Z', yaw)
        shift(b, cx, cy, zc)
        parts.append(b)
    bm = join(parts)
    free_all(*parts)
    return TP(PREFIX + "ShaftBase_420x420x450", bm, ["MAT_Masonry", "MAT_Trim", "MAT_Rubble", "MAT_Wood"],
              note="pivot bottom centre; hollow square 420 outer / 35 walls z 0..430 + coping 430..450 (3 cm inward only); rubble floor z 0..40, 2 broken treads; NO collision")


# ============================================================================================== T5 shaft post
def build_shaft_post():
    parts = []
    parts.append(timber(-9.8, 9.8, -9.8, 9.8, 0.0, 2013.0, 0, 0.6))                        # oak post (slightly under the iron bands)
    for z in (670.0, 1340.0):                                                                # iron splice bands (collars), 40 tall
        for (x0, x1, y0, y1) in ((-10, 10, -10, -9.4), (-10, 10, 9.4, 10), (-10, -9.4, -10, 10), (9.4, 10, -10, 10)):
            parts.append(box(x0, x1, y0, y1, z - 20.0, z + 20.0, 1, 0.0))
    parts.append(box(-10.0, 10.0, -10.0, 10.0, 2012.0, 2015.0, 1, 0.3))                      # iron cap plate
    bm = join(parts)
    free_all(*parts)
    return TP(PREFIX + "ShaftPost_20x20x2015", bm, WI, note="pivot bottom centre; oak post 2015 tall with iron splice bands at z 670 / 1340 and an iron cap plate")


# ============================================================================================== T6 belfry floor
def _planks_along_x(rng, x0, x1, y0, y1, hole=None, w_rng=(21.0, 27.0), bevel=0.15):
    out = []
    n = max(1, int(round((y1 - y0) / 24.0)))
    ws = [rng.uniform(*w_rng) for _ in range(n)]
    sc = (y1 - y0) / sum(ws)
    y = y0
    for k in range(n):
        ya, yb = y, y + ws[k] * sc
        y = yb
        if hole and ya < hole[3] and yb > hole[2]:
            if ya < hole[2]:                                   # part of the board outside the hole's y range keeps its full length
                out.append(timber(x0, x1, ya, hole[2], -5.0, 0.0, 0, bevel))
            if yb > hole[3]:
                out.append(timber(x0, x1, hole[3], yb, -5.0, 0.0, 0, bevel))
            ym0, ym1 = max(ya, hole[2]), min(yb, hole[3])
            out.append(timber(x0, hole[0], ym0, ym1, -5.0, 0.0, 0, bevel))
            out.append(timber(hole[1], x1, ym0, ym1, -5.0, 0.0, 0, bevel))
        else:
            out.append(timber(x0, x1, ya, yb, -5.0, 0.0, 0, bevel))
    return out


def build_belfry_floor():
    rng = random.Random(1108)
    wood, iron = [], []
    wood += _planks_along_x(rng, 0.0, 250.0, 0.0, 920.0)
    wood += _planks_along_x(rng, 250.0, 670.0, 670.0, 920.0)
    wood += _planks_along_x(rng, 250.0, 670.0, 250.0, 670.0, hole=(490.0, 520.0, 280.0, 310.0))
    for y in (340.0, 450.0, 560.0):                       # core-top beams 25 x 30 along x
        wood.append(timber(240.0, 680.0, y - 12.5, y + 12.5, -35.0, -5.0, 0, 0.6))
        for xs in (300.0, 640.0):
            iron.append(box(xs - 8.0, xs + 8.0, y - 13.0, y + 13.0, -35.4, -33.0, 1, 0.3))
    wood.append(timber(250.0, 670.0, 250.0, 262.0, -35.0, -5.0, 0, 0.5))          # edge trimmers
    wood.append(timber(658.0, 670.0, 262.0, 670.0, -35.0, -5.0, 0, 0.5))
    for x in (40.0, 125.0, 210.0):                         # W slab joists along y (not in D1: visible from the W-ring flights)
        wood.append(timber(x - 7.0, x + 7.0, 0.0, 920.0, -30.0, -5.0, 0, 0.5))
    for x in (300.0, 400.0, 500.0, 600.0):                 # N slab joists along y
        wood.append(timber(x - 7.0, x + 7.0, 670.0, 920.0, -30.0, -5.0, 0, 0.5))
    # iron straps round the rope hole (below the boards)
    for (x0, x1, y0, y1) in ((486.0, 524.0, 274.0, 280.0), (486.0, 524.0, 310.0, 316.0), (484.0, 490.0, 280.0, 310.0), (520.0, 526.0, 280.0, 310.0)):
        iron.append(box(x0, x1, y0, y1, -7.0, -5.0, 1, 0.2))
    bm = join(wood + iron)
    free_all(*wood, *iron)
    return TP(PREFIX + "BelfryFloor", bm, WI, note="pivot = world (12040, 1540, 2500); boards top z 0; 3 rectangles; rope hole x 490..520, y 280..310")


# ============================================================================================== T7 top rails
def build_top_rail(length):
    parts = []
    n = int(math.ceil((length - 10.0) / 120.0))
    for k in range(n + 1):
        xc = 5.0 + (length - 10.0) * k / n
        parts.append(timber(xc - 5.0, xc + 5.0, -5.0, 5.0, 0.0, 92.0, 0, 0.4))
    parts.append(timber(0.0, length, -4.0, 4.0, 92.0, 98.0, 0, 0.4))                  # handrail, top z 98
    parts.append(timber(5.0, length - 5.0, -3.0, 3.0, 44.0, 50.0, 0, 0.4))            # mid-rail, top z 50
    bm = join(parts)
    free_all(*parts)
    return TP(PREFIX + "TopRail_%d" % int(length), bm, ["MAT_Wood"], note="local x along the rail 0..%d, y -5..5, floor level z 0, handrail top 98, mid-rail top 50" % length)


# ============================================================================================== T8 partition
def build_partition():
    rng = random.Random(1109)
    edges = [0.0, 15.0, 35.0, 55.0, 75.0, 95.0, 115.0, 135.0, 150.0, 170.0, 190.0, 210.0, 230.0, 250.0]
    wood, iron = [], []
    for k in range(len(edges) - 1):
        a, b = edges[k], edges[k + 1]
        if a == 150.0:
            continue                                         # the missing board (x 150..170)
        top = 455.0 if k in (0, 3, 6, 11) else 455.0 - rng.choice((0.0, 6.0, 14.0, 3.0, 22.0))
        z0 = 0.0 if k == 0 else rng.uniform(0.0, 3.0)
        wood.append(timber(a + 0.4, b - 0.4, 0.3, 3.3, z0, top, 0, 0.3))
    for z in (95.0, 350.0):                                  # 2 rails behind the boards
        wood.append(timber(0.0, 250.0, 3.3, 4.0, z - 14.0, z + 14.0, 0, 0.1))
    for z in (95.0, 350.0):                                  # nail heads on the front face
        for a, b in zip(edges, edges[1:]):
            if a == 150.0:
                continue
            for dz in (-8.0, 8.0):
                iron.append(K.lathe_z([(0.0, 0.0), (1.4, 0.0), (1.4, 0.15), (0.6, 0.3), (0.0, 0.3)], 6, 1))
                n = iron[-1]
                rot(n, 'X', 90.0)
                shift(n, (a + b) / 2.0, 0.3, z + dz)
    bm = join(wood + iron)
    free_all(*wood, *iron)
    # nails sit on y 0..0.3 (front), boards 0.3..3.3, rails 3.3..4: total y 0..4
    return TP(PREFIX + "Partition_250x455", bm, WI, note="origin (12290,1790,0) yaw -90; vertical boards (13, board x 150..170 missing), 2 rails, nail heads; y 0..4")


# ============================================================================================== T9 louvres
def build_louvre(broken=False):
    rng = random.Random(1120 if broken else 1119)
    parts = []
    for i in range(9):
        z = 25.0 + 50.0 * i
        if broken and i in (2, 3):
            continue
        ang = -70.0 if (broken and i == 4) else -40.0
        b = K.box(-65.0, 65.0, -15.0, 15.0, -1.5, 1.5, 0, 0.3)
        rot(b, 'X', ang)
        shift(b, 0.0, 15.0 if ang == -40.0 else 12.0, z + (0.0 if ang == -40.0 else -4.0))
        parts.append(b)
    for (xa, xb) in ((-65.0, -59.0), (59.0, 65.0)):          # side cleats 6 wide, full height
        parts.append(timber(xa, xb, 0.0, 30.0, 0.0, 450.0, 0, 0.4))
    bm = join(parts)
    free_all(*parts)
    # pivot bottom centre of the opening on the inner face: x -65..65, y 0..30, z 0..450
    return TP(PREFIX + "Louvre_130x450" + ("_Broken" if broken else ""), bm, ["MAT_Wood"],
              note=("boards 3+4 missing, board 5 hangs at 70 deg; " if broken else "") + "9 boards 130 x 30 x 3 at 40 deg, spaced 50 from z 25, 2 side cleats")


# ============================================================================================== T10 bell frame
def build_bell_frame():
    rng = random.Random(1110)
    wood, iron = [], []
    for sx in (-1, 1):
        for sy in (-1, 1):
            wood.append(timber(sx * 140.0 - 12.5, sx * 140.0 + 12.5, sy * 135.0 - 12.5, sy * 135.0 + 12.5, 0.0, 365.0, 0, 0.8))
    for sy in (-1, 1):
        wood.append(timber(-165.0, 165.0, sy * 135.0 - 12.5, sy * 135.0 + 12.5, 0.0, 20.0, 0, 0.8))            # ground sills
        wood.append(timber(-165.0, 165.0, sy * 135.0 - 12.5, sy * 135.0 + 12.5, 335.0, 365.0, 0, 0.8))         # head sills
    for sx in (-1, 1):
        wood.append(timber(sx * 140.0 - 12.5, sx * 140.0 + 12.5, -135.0, 135.0, 335.0, 365.0, 0, 0.8))         # cross-ties
    for sx in (-1, 1):                                                                                        # braces: post at z 120 -> head sill at x +-60
        for sy in (-1, 1):
            wood.append(beam_between((sx * 140.0, sy * 135.0, 120.0), (sx * 60.0, sy * 135.0, 335.0), 15.0, 15.0, 0, up=(0, 1, 0), bevel=0.5))
    for sy in (-1, 1):
        iron.append(box(-10.0, 10.0, sy * 135.0 - 15.0, sy * 135.0 + 15.0, 365.0, 380.0, 1, 0.8))             # bearing blocks 20 x 30 x 15
        for sx in (-1, 1):                                                                                    # bolts through the post tops
            for dy in (-1, 1):
                b = K.cylinder(2.0, 3.0, 8, 1)
                shift(b, sx * 140.0, sy * 135.0 + dy * 7.0, 365.0)
                iron.append(b)
    for sx in (-1, 1):                                                                                        # iron straps at the post / sill joints
        for sy in (-1, 1):
            iron.append(box(sx * 140.0 - 14.0, sx * 140.0 + 14.0, sy * 135.0 - 13.5, sy * 135.0 + 13.5, 24.0, 28.0, 1, 0.3))
    bm = join(wood + iron)
    free_all(*wood, *iron)
    ucx = [K.box_hull(sx * 140.0 - 12.5, sx * 140.0 + 12.5, sy * 135.0 - 12.5, sy * 135.0 + 12.5, 0.0, 365.0) for sx in (-1, 1) for sy in (-1, 1)]
    return TP(PREFIX + "BellFrame_A", bm, WI, ucx=ucx, note="pivot at the floor point under the bell axis; 4 posts 25 x 25 x 365 at (+-140, +-135); UCX = the 4 posts only")


# ============================================================================================== T11 headstock + wheel
def build_headstock():
    wood, iron = [], []
    wood.append(timber(-17.5, 17.5, -150.0, 150.0, -17.5, 17.5, 0, 1.2))                                      # headstock beam
    for sy in (-1, 1):
        g = K.cylinder(5.5, 24.0, 12, 1)
        rot(g, 'X', -90.0 if sy > 0 else 90.0)                                                                # axis along +-y
        shift(g, 0.0, sy * 146.0, 0.0)
        iron.append(g)
        iron.append(box(-19.5, 19.5, sy * 150.0 - 3.0 - (0 if sy > 0 else 0), sy * 150.0 + 3.0, -19.5, 19.5, 1, 0.8))
    for sy in (-1, 1):                                                                                        # straps down to the bell's canons (U round the beam + tail)
        yc = sy * 40.0
        iron.append(box(-19.5, 19.5, yc - 5.0, yc + 5.0, 17.5, 19.5, 1, 0.3))
        iron.append(box(-19.5, -17.5, yc - 5.0, yc + 5.0, -19.5, 17.5, 1, 0.3))
        iron.append(box(17.5, 19.5, yc - 5.0, yc + 5.0, -19.5, 17.5, 1, 0.3))
        iron.append(box(-19.5, 19.5, yc - 5.0, yc + 5.0, -19.5, -17.5, 1, 0.3))
        iron.append(box(-4.0, 4.0, yc - 4.0, yc + 4.0, -45.0, -19.5, 1, 0.3))
    # bell wheel: Ø260 in the plane y -170, 6 spokes, rim 12 (y) x 10 (radial) with a rope groove
    yw = -170.0
    rp = [(120.0, -6.0), (130.0, -6.0), (130.0, -2.6), (127.0, -2.6), (125.5, 0.0), (127.0, 2.6), (130.0, 2.6), (130.0, 6.0), (120.0, 6.0)]
    rim = K.lathe_z(rp, 48, 0, cap_bottom=False, cap_top=False, closed=True)
    rot(rim, 'X', 90.0)
    shift(rim, 0.0, yw, 0.0)
    wood.append(rim)
    hub = K.cylinder(19.0, 16.0, 16, 0)
    K.bevel_all(hub, 0.8, 25.0)
    rot(hub, 'X', 90.0)
    shift(hub, 0.0, yw + 8.0, 0.0)
    wood.append(hub)
    for k in range(6):
        a = 60.0 * k + 15.0
        sp = K.box(15.0, 121.0, -4.5, 4.5, -5.0, 5.0, 0, 0.5)
        rot(sp, 'Y', 0.0)
        tf(sp, Matrix.Rotation(math.radians(a), 4, 'Y'))
        shift(sp, 0.0, yw, 0.0)
        wood.append(sp)
    for k in range(6):                                                                                       # iron ties where spokes meet the rim
        a = 60.0 * k + 15.0
        t = K.box(112.0, 124.0, -6.4, 6.4, -6.0, 6.0, 1, 0.4)
        tf(t, Matrix.Rotation(math.radians(a), 4, 'Y'))
        shift(t, 0.0, yw, 0.0)
        iron.append(t)
    # rope tail: staple on the rim at 3 o'clock and a short iron chain down to the rope's top eye (rope top is 130 below the axle)
    iron.append(box(126.0, 134.0, yw - 3.0, yw + 3.0, -6.0, 6.0, 1, 0.5))
    for j in range(17):
        z = -4.0 - 7.6 * j
        lk = BP.chain_link(2.6, 0.7, 1.55, 1, 'yz' if j % 2 else 'xz')
        shift(lk, 130.0, yw, z - 4.0)
        iron.append(lk)
    bm = join(wood + iron)
    free_all(*wood, *iron)
    return TP(PREFIX + "BellHeadstock_A", bm, WI, note="pivot at the axle centre; beam 35 x 35 along y -150..150, gudgeons, 2 straps, wheel O260 in plane y -170 (6 spokes, grooved rim), iron staple + 130 cm chain at the rim's 3 o'clock down to the rope top")
