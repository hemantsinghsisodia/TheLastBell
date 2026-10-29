"""tw_roof.py -- SM_LB_Tw_Roof_BrokenSW (T14).

Pivot at the bottom centre at the wall top (world 12500, 2000, 3540).  Pyramid from the eaves square (+-525, z -10) to the apex (0, 0, 1200),
slates (MAT_Slate) 6 thick on battens, timber wall plate, 4 hip rafters 20 x 25, common rafters 12 x 15 at 60 c/c, iron cross finial 90 tall
bent 20 deg toward +x.  The SW quarter is missing (the -x face for y -525..-100 and the -y face for x -525..-100, up to z 860, jagged),
the SW hip snapped at z 600 with its stub hanging, 3 broken common rafters (one hanging to z -300).
Slots: 0 MAT_Slate, 1 MAT_Wood, 2 MAT_Iron.
"""
import math
import random

from tw_common import *  # noqa: F401,F403
from tw_common import K, BK, BP, bmesh, Vector, Matrix, math, random

SL, WD, IR = 0, 1, 2
HALF = 525.0
Z_EAVE, Z_APEX = -10.0, 1200.0
RISE = Z_APEX - Z_EAVE
SLANT = math.hypot(HALF, RISE)
TAN_S = Vector((0.0, HALF / SLANT, RISE / SLANT))       # up the slope (canonical S face)
NRM = Vector((0.0, -RISE / SLANT, HALF / SLANT))        # outward normal (canonical S face)
FACE_ANG = {"S": 0.0, "E": 90.0, "N": 180.0, "W": 270.0}
Z_MISS = 860.0
S_MISS = (Z_MISS - Z_EAVE) / (RISE / SLANT)             # slope distance of the z 860 line
SLATE_L, SLATE_W, PITCH = 30.0, 28.0, 22.0


def half_width(s):
    return HALF * (1.0 - s / SLANT)


def P(u, s, n):
    """Canonical (south face) point: u along the eave, s up the slope from the eave, n outward."""
    return Vector((u, -HALF, Z_EAVE)) + TAN_S * s + NRM * n


def face_mat(face):
    return Matrix.Rotation(math.radians(FACE_ANG[face]), 4, 'Z')


def missing(face, u, s, rng_seed=1113):
    """True where the roof covering is gone (SW quarter).  Canonical u: S face -> world x = u; W face -> world y = -u."""
    if face == "S":
        du = -100.0 + (K.vnoise(s / 55.0, 2.7, rng_seed) - 0.5) * 70.0
        ok_u = u < du
    elif face == "W":
        du = 100.0 + (K.vnoise(s / 55.0, 7.1, rng_seed + 3) - 0.5) * 70.0
        ok_u = u > du
    else:
        return False
    sl = S_MISS + (K.vnoise(u / 45.0, 4.4, rng_seed + 9) - 0.5) * 90.0
    return ok_u and s < sl


def _add_hex(b, vs, mat):
    """Closed hexahedron from 8 vertices (bottom 0..3 ccw, top 4..7)."""
    vv = [b.verts.new(v) for v in vs]
    for idx in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        try:
            f = b.faces.new([vv[i] for i in idx])
            f.material_index = mat
        except ValueError:
            pass


def _slab(b, M, u0, u1, s0, s1, n_lo0, n_lo1, thick, mat):
    """Tilted slab in canonical coordinates: underside n from n_lo0 (at s0) to n_lo1 (at s1), `thick` thick, transformed by M."""
    pts = [P(u0, s0, n_lo0), P(u1, s0, n_lo0), P(u1, s1, n_lo1), P(u0, s1, n_lo1)]
    bot = [M @ p for p in pts]
    top = [M @ (p + NRM * thick) for p in pts]
    _add_hex(b, bot + top, mat)


def slates_and_battens(rng):
    slate = bmesh.new()
    batten = bmesh.new()
    n_slates = 0
    nrows = int(SLANT / PITCH) + 1
    for face in ("S", "E", "N", "W"):
        M = face_mat(face)
        for r in range(nrows):
            s0 = r * PITCH + rng.uniform(-0.4, 0.4)
            s1 = s0 + SLATE_L
            if s0 > SLANT - 6.0:
                break
            s1 = min(s1, SLANT - 2.0)
            smid = (s0 + s1) * 0.5
            hw = half_width(smid) - 3.0
            if hw < 6.0:
                break
            # battens under the slate heads (3 wide, 3 thick), split by the missing zone
            sb = s0 + SLATE_L - 5.0
            if sb < SLANT - 20.0:
                hwb = half_width(sb) - 6.0
                if hwb > 8.0:
                    seg = [(-hwb, hwb)]
                    if face in ("S", "W"):
                        cuts = []
                        # find the u extent that is not missing along the row (sample)
                        us = [-hwb + (2 * hwb) * k / 40.0 for k in range(41)]
                        keep = [not missing(face, u, sb) for u in us]
                        seg, start = [], None
                        for u, kp in zip(us, keep):
                            if kp and start is None:
                                start = u
                            if (not kp) and start is not None:
                                seg.append((start, u))
                                start = None
                        if start is not None:
                            seg.append((start, us[-1]))
                    for (a, c) in seg:
                        if c - a > 4.0:
                            _slab(batten, M, a, c, sb, sb + 3.0, -14.0, -14.0, 3.0, WD)
            # slates: staggered columns
            off = (r % 2) * 0.5
            kmin = int(math.floor(-hw / (SLATE_W + 1.0) - off)) - 1
            kmax = int(math.ceil(hw / (SLATE_W + 1.0) - off)) + 1
            for k in range(kmin, kmax + 1):
                uc = (k + off) * (SLATE_W + 1.0) + rng.uniform(-0.5, 0.5)
                ua, ub = uc - SLATE_W / 2.0 + rng.uniform(-0.8, 0.8), uc + SLATE_W / 2.0 + rng.uniform(-0.8, 0.8)
                ua, ub = max(ua, -hw), min(ub, hw)
                if ub - ua < 9.0:
                    continue
                if missing(face, (ua + ub) * 0.5, smid):
                    continue
                n0 = -6.0 + rng.uniform(-0.5, 0.5)
                ln = (s1 - s0) + rng.uniform(-1.0, 1.0)
                _slab(slate, M, ua, ub, s0, s0 + ln, n0, n0 - 5.0 * ln / SLATE_L, 6.0, SL)
                n_slates += 1
    return slate, batten, n_slates


def common_rafters(rng):
    """Common rafters 12 x 15 at 60 c/c under the battens (n -27..-12); returns (parts, broken list)."""
    parts = []
    for face in ("S", "E", "N", "W"):
        M = face_mat(face)
        for k in range(-8, 9):
            u = 60.0 * k
            if abs(u) < 40.0 or abs(u) > HALF - 40.0:
                continue
            s_a = 30.0
            s_b = SLANT * (1.0 - abs(u) / HALF) - 14.0
            if s_b - s_a < 30.0:
                continue
            p0 = M @ P(u, s_a, -21.5)
            p1 = M @ P(u, s_b, -21.5)
            up = M.to_3x3() @ NRM
            if (face, k) in (("S", -5), ("W", 4), ("W", 7)):                     # the 3 broken rafters, handled below
                continue
            parts.append(beam_between(p0, p1, 12.0, 15.0, WD, up=up, bevel=0.5))
    return parts


def broken_rafters(rng):
    out = []
    M = face_mat("S")
    up = M.to_3x3() @ NRM
    # S face u = -300: snapped at s 520, only the foot part stays; ragged break
    u = -300.0
    p0, p1 = M @ P(u, 30.0, -21.5), M @ P(u, 520.0, -21.5)
    out.append(beam_between(p0, p1, 12.0, 15.0, WD, up=up, bevel=0.5))
    out.append(_splinter(p1, p1 - (p1 - p0).normalized() * 40.0, up, rng))
    # W face: canonical u = 240 (world y -240): the upper half stays, lower half gone
    MW = face_mat("W")
    upw = MW.to_3x3() @ NRM
    u = 240.0
    s_b = SLANT * (1.0 - u / HALF) - 14.0
    q0, q1 = MW @ P(u, 640.0, -21.5), MW @ P(u, s_b, -21.5)
    out.append(beam_between(q0, q1, 12.0, 15.0, WD, up=upw, bevel=0.5))
    out.append(_splinter(q0, q0 + (q1 - q0).normalized() * 40.0, upw, rng))
    # W face: canonical u = 420 (world y -420): foot piece 310 long hinged at the plate, hanging down inside to z -300
    u = 420.0
    foot = MW @ P(u, 30.0, -21.5)
    tip = Vector((foot.x + 14.0, foot.y, foot.z - 290.0))
    out.append(beam_between(foot, tip, 12.0, 15.0, WD, up=(1, 0, 0), bevel=0.5))
    out.append(_splinter(tip, tip - (tip - foot).normalized() * 30.0, (1, 0, 0), rng))
    return out


def _splinter(p_end, p_back, up, rng):
    """Three thin splinters sticking out of a snapped end."""
    parts = []
    d = (p_end - p_back).normalized()
    for k in range(3):
        a = p_end - d * rng.uniform(4.0, 10.0)
        b = p_end + d * rng.uniform(4.0, 14.0)
        off = Vector((rng.uniform(-3, 3), rng.uniform(-3, 3), rng.uniform(-3, 3)))
        parts.append(beam_between(a + off, b + off, rng.uniform(2.0, 4.0), rng.uniform(5.0, 9.0), WD, up=up, bevel=0.2))
    return join(parts)


def hips_and_plate(rng):
    parts = []
    apex = Vector((0.0, 0.0, Z_APEX - 5.0))
    corners = {"NE": (490.0, 490.0), "NW": (-490.0, 490.0), "SE": (490.0, -490.0), "SW": (-490.0, -490.0)}
    for nm, (cx, cy) in corners.items():
        foot = Vector((cx, cy, -2.0))
        if nm != "SW":
            parts.append(beam_between(foot, apex, 20.0, 25.0, WD, up=(0, 0, 1), bevel=0.6))
        else:
            t = (600.0 - foot.z) / (apex.z - foot.z)
            brk = foot.lerp(apex, t)
            parts.append(beam_between(brk, apex, 20.0, 25.0, WD, up=(0, 0, 1), bevel=0.6))        # upper part, snapped at z 600
            parts.append(_splinter(brk, brk - (apex - brk).normalized() * 40.0, (0, 0, 1), rng))
            stub_tip = Vector((foot.x + 70.0, foot.y + 70.0, foot.z - 190.0))
            parts.append(beam_between(foot, stub_tip, 20.0, 25.0, WD, up=(1, -1, 0), bevel=0.6))   # stub hanging from the plate corner
            parts.append(_splinter(stub_tip, stub_tip - (stub_tip - foot).normalized() * 30.0, (1, -1, 0), rng))
    # wall plate ring 15 x 12 on the wall tops (gone over the collapsed SW corner)
    plate = []
    plate.append(timber(-500.0, 500.0, 485.0, 500.0, -2.0, 12.0, WD, 0.5))                    # N side
    plate.append(timber(485.0, 500.0, -500.0, 500.0, -2.0, 12.0, WD, 0.5))                    # E side
    plate.append(timber(-140.0, 500.0, -500.0, -485.0, -2.0, 12.0, WD, 0.5))                  # S side (x -140..500)
    plate.append(timber(-500.0, -485.0, -180.0, 500.0, -2.0, 12.0, WD, 0.5))                  # W side (y -180..500)
    return parts, plate


def finial():
    iron = []
    shaft = K.cylinder(2.6, 82.0, 8, IR)
    iron.append(shaft)
    iron.append(box(-16.0, 16.0, -1.6, 1.6, 52.0, 57.0, IR, 0.3))                             # cross arms
    ball = BP.sphere_z(4.2, 10, 6, IR)
    shift(ball, 0.0, 0.0, 85.8)
    iron.append(ball)
    cone = K.lathe_z([(9.0, 0.0), (4.5, 7.0), (2.6, 12.0)], 8, IR)
    iron.append(cone)
    fin = join(iron)
    free_all(*iron)
    rot(fin, 'Y', 20.0)                                                                        # bent 20 deg toward +x
    shift(fin, 0.0, 0.0, Z_APEX)
    return fin


def build_roof():
    rng = random.Random(1113)
    slate, batten, n = slates_and_battens(rng)
    parts = [slate]
    wood = [batten]
    wood += common_rafters(rng)
    wood += broken_rafters(rng)
    hp, plate = hips_and_plate(rng)
    wood += hp + plate
    iron = [finial()]
    bm = join(parts + wood + iron)
    free_all(*parts, *wood, *iron)
    return TP(PREFIX + "Roof_BrokenSW", bm, ["MAT_Slate", "MAT_Wood", "MAT_Iron"], extra=dict(slates=n),
              note="pivot at the wall-top centre (12500, 2000, 3540); pyramid eaves +-525 at z -10, apex z 1200; %d slates; SW quarter missing "
                   "(-x face y -525..-100, -y face x -525..-100, to z 860); SW hip snapped at z 600; 3 broken common rafters (one hangs to z -300); cross finial bent 20 deg to +x" % n)
