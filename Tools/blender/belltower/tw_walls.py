"""tw_walls.py -- tower wall stage pieces S1 / S2 / S3 (W, N, E, S) incl. the two _BrokenSW pieces (D1.1).

Face frame: local X along the face, local Y 0 = inner face, local Y 40 = outer face, local Z up (stage base = 0).
Slots (kit order): 0 MAT_Masonry, 1 MAT_Trim, 2 MAT_Rubble.
"""
import math
import random

from tw_common import *  # noqa: F401,F403
from tw_common import K, BK, BP, bmesh, Vector, math, random

T = 40.0
MA, TR, RU = 0, 1, 2
SLOTS = ["MAT_Masonry", "MAT_Trim", "MAT_Rubble"]
FACE_L = {"W": 1000.0, "E": 1000.0, "N": 920.0, "S": 920.0}
STAGE_H = {"S1": 800.0, "S2": 1700.0, "S3": 1040.0}
STAGE_Z0 = {"S1": 0.0, "S2": 800.0, "S3": 2500.0}
ORDER = [(s, f) for s in ("S1", "S2", "S3") for f in ("W", "N", "E", "S")]
SEED = {k: 1001 + i for i, k in enumerate(ORDER)}

# slits: (stage, face) -> list of (name, local x centre, local z centre)
SLITS = {
    ("S1", "N"): [("F01", 460.0, 263.6)],
    ("S1", "E"): [("F02", 500.0, 490.9)],
    ("S1", "S"): [("F03", 460.0, 718.1)],
    ("S2", "W"): [("F08", 500.0, 1054.0)],
    ("S2", "N"): [("F05", 460.0, 372.7), ("F09", 460.0, 1281.8)],
    ("S2", "E"): [("F06", 500.0, 600.0), ("F10", 500.0, 1509.1)],
    ("S2", "S"): [("F07", 460.0, 827.3)],
}
LANCET_X = {"W": (405.0, 595.0), "E": (405.0, 595.0), "N": (365.0, 555.0), "S": (365.0, 555.0)}   # centres of x 340-470/530-660 and 300-430/490-620
LANCET_W, LANCET_SILL, LANCET_SPRING = 130.0, 200.0, 650.0
BREAK = {"W": dict(xa=0.0, xb=320.0, za=750.0, zb=1040.0, seed=1003, cornice=(340.0, 1000.0)),
         "S": dict(xa=600.0, xb=920.0, za=1040.0, zb=750.0, seed=1004, cornice=(0.0, 590.0))}


def name_of(stage, face, broken=False):
    return PREFIX + "%s_%s%s" % (stage, face, "_BrokenSW" if broken else "")


# ---------------------------------------------------------------------------------------------- exterior courses
def course_poly(kind):
    if kind == "plinth":
        return [(36.0, 0.0), (50.0, 0.0), (50.0, 50.0), (40.0, 60.0), (36.0, 60.0)]
    if kind == "drip":
        return [(36.0, 410.0), (42.0, 410.0), (48.0, 412.0), (48.0, 424.0), (40.0, 430.0), (36.0, 430.0)]
    if kind == "sill":
        return [(36.0, 1670.0), (44.0, 1670.0), (50.0, 1677.0), (50.0, 1690.0), (40.0, 1700.0), (36.0, 1700.0)]
    if kind == "cornice":
        pts = [(36.0, 980.0), (40.0, 980.0)]
        for k in range(1, 8):
            th = math.radians(90.0 * k / 7.0)
            pts.append((55.0 - 15.0 * math.cos(th), 980.0 + 60.0 * math.sin(th)))
        pts.append((36.0, 1040.0))
        return pts
    raise KeyError(kind)


def course_solids(stage, face, broken=False):
    """Trim courses (slot 1) as separate solids, ends running past the piece ends so they wrap the corners."""
    L = FACE_L[face]
    over = 40.0 if face in ("N", "S") else None      # N/S courses butt the W/E pieces' wall faces (deviation from D1.1: 'by the projection' leaves a 30 cm notch)
    out = []

    def span(kind, proj):
        o = over if over is not None else proj
        return -o, L + o

    if stage == "S1":
        a, b = span("plinth", 10.0)
        cuts = [(448.0, 552.0)] if face == "W" else []
        x = a
        for (c0, c1) in cuts:
            out.append(K.prism(course_poly("plinth"), 'x', x, c0, TR))
            x = c1
        out.append(K.prism(course_poly("plinth"), 'x', x, b, TR))
    if stage == "S2":
        a, b = span("drip", 8.0)
        out.append(K.prism(course_poly("drip"), 'x', a, b, TR))
        a, b = span("sill", 10.0)
        out.append(K.prism(course_poly("sill"), 'x', a, b, TR))
    if stage == "S3":
        a, b = span("cornice", 15.0)
        if broken:
            br = BREAK[face]
            if face == "W":
                a = br["cornice"][0]
            else:
                b = br["cornice"][1]
        out.append(K.prism(course_poly("cornice"), 'x', a, b, TR))
    for s in out:
        if stage != "S3":
            K.bevel_all(s, 0.8, 30.0)
            K.bm_set_mat(s, TR)
    return out


# ---------------------------------------------------------------------------------------------- openings
def slit_polys(cx, cz):
    """Inner (50 x 120) and outer (18 x 100) pointed slit outlines (x, z), same vertex count."""
    n = 8
    zb_o, zb_i = cz - 50.0, cz - 60.0
    outer = K.pointed_light_poly(cx, zb_o, zb_o + 82.0, 18.0, 22.5, n_arc=n)
    inner = K.pointed_light_poly(cx, zb_i, zb_i + 70.0, 50.0, 62.5, n_arc=n)
    return inner, outer


def slit_cutter(cx, cz):
    inner, outer = slit_polys(cx, cz)
    cut = bmesh.new()
    for part in (K.loft_y(inner, -1.5, inner, 0.0, MA, False), K.loft_y(inner, 0.0, outer, T, MA, False),
                 K.loft_y(outer, T, outer, T + 24.0, MA, False)):
        K.bm_append(cut, part)
        part.free()
    return cut


def chamfer_cutters(poly, c, z_floor=None, y_out=T, y_in=0.0):
    """45 degree arris chamfers (c cm) on both faces of a through opening whose outline is poly (x, z)."""
    big = K.offset_poly(poly, c + 1.0)
    if z_floor is not None:
        big = [(x, max(z, z_floor)) if abs(p[1] - z_floor) < 1e-6 else (x, z) for (x, z), p in zip(big, poly)]
    cut = bmesh.new()
    for part in (K.loft_y(poly, y_out - c, big, y_out + 1.0, MA, False), K.loft_y(big, y_in - 1.0, poly, y_in + c, MA, False)):
        K.bm_append(cut, part)
        part.free()
    return cut


def lancet_poly(cx):
    return K.pointed_light_poly(cx, LANCET_SILL, LANCET_SPRING, LANCET_W, LANCET_W, n_arc=10)


def lancet_parts(cx):
    """(cutters, trim extras) for one belfry lancet."""
    poly = lancet_poly(cx)
    cuts = bmesh.new()
    thr = K.prism(poly, 'y', -1.5, T + 24.0, MA)
    K.bm_append(cuts, thr)
    thr.free()
    ch = chamfer_cutters(poly, 6.0, z_floor=LANCET_SILL)
    K.bm_append(cuts, ch)
    ch.free()
    extras = []
    hm = BK.hood_mould(cx, LANCET_SPRING, LANCET_W, 1.0, 4.0, 14.0, LANCET_SPRING - 55.0, T - 3.0, T + 8.0, 1.2, 14)
    sill = BK.sloped_sill(cx, 74.0, LANCET_SILL, 6.0, T - 8.0, T + 9.0, 12.0)
    K.bm_set_mat(hm, TR)
    K.bm_set_mat(sill, TR)
    extras.append(hm)
    extras.append(sill)
    return cuts, extras


def door_poly():
    return [(448.0, -1.0), (448.0, 194.0), (500.0, 228.0), (552.0, 194.0), (552.0, -1.0)]


def door_parts():
    poly = door_poly()
    cuts = bmesh.new()
    thr = K.prism(poly, 'y', -1.5, T + 24.0, MA)
    K.bm_append(cuts, thr)
    thr.free()
    ch = chamfer_cutters(poly, 8.0, z_floor=-1.0)
    K.bm_append(cuts, ch)
    ch.free()
    # hood mould: gabled chevron 15 tall, its lower edge 20 above the head, 8 proud, with label stops
    sl = 34.0 / 52.0
    zi = lambda x: 248.0 - sl * abs(x - 500.0)        # lower edge (head line + 20)
    hp = [(436.0, 160.0), (436.0, zi(436.0) + 15.0), (500.0, 263.0), (564.0, zi(564.0) + 15.0), (564.0, 160.0),
          (551.0, 160.0), (551.0, zi(551.0)), (500.0, 248.0), (449.0, zi(449.0)), (449.0, 160.0)]
    hm = K.prism(hp, 'y', T - 3.0, T + 8.0, TR)
    K.bevel_all(hm, 1.2, 25.0)
    K.bm_set_mat(hm, TR)
    return cuts, [hm]


# ---------------------------------------------------------------------------------------------- broken top (SW collapse)
def break_profile(xa, xb, za, zb, seed, H, nmin=6, nmax=9):
    """Rising/falling stepped break line from (xa, za) to (xb, zb): plateaus joined by near-vertical to 45 degree breaks."""
    rng = random.Random(seed)
    n = rng.randint(nmin, nmax)
    ws = [rng.uniform(0.7, 1.4) for _ in range(n)]
    sc = (xb - xa) / sum(ws)
    xs = [xa]
    for w in ws:
        xs.append(xs[-1] + w * sc)
    hs = []
    for i in range(n):
        t = (i + 0.5) / n
        hs.append(za + (zb - za) * t + (rng.uniform(-34.0, 34.0) if 0 < i < n - 1 else 0.0))
    hs[0], hs[-1] = za + (6.0 if za >= H else 0.0), zb + (6.0 if zb >= H else 0.0)
    ramps = [rng.choice((5.0, 9.0, 16.0, 28.0)) for _ in range(n + 1)]
    nodes = []
    for i in range(n):
        x0, x1 = xs[i], xs[i + 1]
        r = min(ramps[i], 0.4 * (x1 - x0)) if i > 0 else 0.0
        h0 = hs[i]
        h1 = hs[i] + (rng.uniform(-14.0, 14.0) if 0 < i < n - 1 else 0.0)
        nodes.append((x0 + r, h0))
        nodes.append((x1, h1))
    nodes.sort()

    def h(x):
        if x <= nodes[0][0]:
            return nodes[0][1]
        for (xa_, za_), (xb_, zb_) in zip(nodes, nodes[1:]):
            if x <= xb_:
                t = 0.0 if xb_ - xa_ < 1e-6 else (x - xa_) / (xb_ - xa_)
                return za_ * (1 - t) + zb_ * t
        return nodes[-1][1]

    return h, xs, hs


def break_cutter(face, H):
    br = BREAK[face]
    seed = br["seed"]
    h, xs, hs = break_profile(br["xa"], br["xb"], br["za"], br["zb"], seed, H)
    rng = random.Random(seed + 500)
    ytop = H + 40.0
    a0 = -6.0 if face == "W" else br["xa"]
    a1 = br["xb"] if face == "W" else FACE_L[face] + 6.0
    na = max(6, int((a1 - a0) / 8.0))

    def f(x, y):
        xx = min(max(x, br["xa"]), br["xb"])
        yn = (K.vnoise(y / 22.0 + 3.1, x / 70.0, seed) - 0.5) * 12.0
        jit = (K.vnoise(x / 6.0, y / 6.0, seed + 5) - 0.5) * 4.0
        return min(h(xx) + yn + jit, H + 12.0)

    cut = K.hf_solid(a0, a1, -6.0, T + 16.0, f, ytop, na, 8, ('x', 'y', 'z'), RU, rng)
    return cut, (h, xs, hs)


def quoins(L, H, courses, sx):
    """Alternating quoins on the outer corner of a W / E piece (sx = -1 at x = 0, +1 at x = L): along the face 52 / 30, into the wall 24 / 40."""
    out = bmesh.new()
    z = 0.0
    for k, h in enumerate(courses):
        zt = min(H, z + h)
        lx, dy = (52.0, 24.0) if k % 2 == 0 else (30.0, 40.0)
        xa, xb = (0.0, lx) if sx < 0 else (L - lx, L)
        cx = 0.0 if sx < 0 else L
        outer = (lambda e, cx=cx: all(abs(v.co.y - T) < 1e-6 for v in e.verts) or all(abs(v.co.x - cx) < 1e-6 for v in e.verts))
        K.bm_append(out, K.box(xa, xb, T - dy, T, z, zt, TR, 2.0, edge_filter=outer))
        z = zt
    return out


# ---------------------------------------------------------------------------------------------- piece builder
def build_wall(stage, face, broken=False):
    L = FACE_L[face]
    H = STAGE_H[stage]
    seed = SEED[(stage, face)]
    body, courses = BK.ashlar_body(L, T, 0.0, H, seed, vary=True)
    cutters, extras, trim_cut = [], [], bmesh.new()
    note = []
    # ---- openings
    if stage == "S1" and face == "W":
        c, ex = door_parts()
        cutters.append(c)
        extras += ex
        K.bm_append(trim_cut, c)
    for (nm, cx, cz) in SLITS.get((stage, face), []):
        c = slit_cutter(cx, cz)
        cutters.append(c)
        K.bm_append(trim_cut, c)
        note.append("slit %s at x %g z %g" % (nm, cx, cz))
    if stage == "S3":
        for cx in LANCET_X[face]:
            c, ex = lancet_parts(cx)
            cutters.append(c)
            extras += ex
            K.bm_append(trim_cut, c)
    brk = None
    if broken:
        brk, prof = break_cutter(face, H)
        cutters.append(brk)
    # ---- exterior courses (cut by the openings that pass through them)
    cs = course_solids(stage, face, broken)
    if cs:
        cj = join(cs)
        free_all(*cs)
        if len(trim_cut.faces):
            cj2 = K.boolean_diff(cj, trim_cut)
            cj.free()
            cj = cj2
        extras.append(cj)
    # ---- corner quoins on the W / E pieces (they own the outer corners)
    if face in ("W", "E"):
        q = bmesh.new()
        for sx in (-1, 1):
            K.bm_append(q, quoins(L, H, courses, sx))
        if brk is not None:
            q2 = K.boolean_diff(q, brk)
            q.free()
            q = q2
        extras.append(q)
    shell = BK.carve_and_merge(body, cutters, extras)
    free_all(body, trim_cut, *cutters, *extras)
    return TP(name_of(stage, face, broken), shell, SLOTS, note="; ".join(note), extra=dict(seed=seed))
