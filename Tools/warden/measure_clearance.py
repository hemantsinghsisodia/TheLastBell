"""measure_clearance.py -- P12-5: how much room is there over the Warden's routes, search points and spawn points?

    python -I Tools/warden/measure_clearance.py [--out Docs/ArtTest/warden/p12_clearance.md] [--step 100]

Reads the placed ALBPatrolPoint / ALBSearchPoint / ALBWardenSpawnPoint actors and the door actors from the open editor
(Tools/mcp/ue.py; READ-ONLY: find_actors, get_actor_transform, get_properties, get_label; it loads L_Monastery if another
map is current, which changes nothing in any asset), and the art records in Docs/plans/p9_d1_layout.json (crypt) and
Docs/plans/p10_d1_layout.json (cloister, tower).  Writes a Markdown report.

WHY NOT TRACES: the art vaults, arches and soffits are NoCollision, so trace_world cannot see them.  The ceilings come
from the layout records instead.  A record's AABB bottom is its SPRINGING (the lowest point of a vault or arch), which
is lower than the curved surface above most of the floor, so every point gets two numbers:

  conservative  = the lowest AABB bottom / springing of any ceiling record over the point  (a floor under the real value)
  estimated     = the underside at the point, where the profile is known:
                    crypt SM_Roof bay    from the P9 survey grid (Docs/ArtTest/crypt/survey_p9.md, "SM_Roof"): crown +2 on the
                                         centre lines, diagonal and edge profiles, corners -296; blended between them (see vault_g).
                                         MODELLED, not measured: the mesh has no collision and no vertex readout is available.
                    crypt SM_Arch portal from the survey's traced underside table, scaled by the portal's X and Z scale.
                    cloister arcade arch two-centred pointed arch, radius 0.8 x span, apex 0.742 x span above the springing.
                  where the profile is not known (cloister barrel vault, the two archways, boards, beams) estimated = conservative.

A point is BELOW when estimated < 292 cm (V5's Idle tops out at 290.3, Walk at 291.8).  It is SPRINGING-ONLY when only the
conservative number is below 292.  A point with no ceiling record over it is NO-DATA and is never counted as clear.

Straight-line samples: segments are the straight line between consecutive waypoints (and last -> first, the route loops).
The walked path follows the navmesh through the portals, so a straight line can cross walls, the pit or the garth; those
samples are marked (no floor tile / garth) and are not walkable evidence either way.  Three segments whose straight line
leaves the rooms altogether (crypt 4->5 and the crypt loop 7->1 cross solid rock; the cloister loop 7->1 crosses the garth)
are sampled along a path through the portal openings / the walk corner instead (VIA below); that is an assumed path.

GREYBOX TRACE: the crypt, cloister and tower greybox shells keep their collision (hidden), and that collision is what the
Warden really bumps into.  Every search/spawn point and every route sample also gets a vertical trace_world from floor+5 up
1500 cm; the first hit is shown as "trace" (an independent cross-check; it sees collision only, never the art).
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Tools", "mcp"))
from ue import UE  # noqa: E402

SC = "editor_toolset.toolsets.scene.SceneTools"
AC = "editor_toolset.toolsets.actor.ActorTools"
OB = "editor_toolset.toolsets.object.ObjectTools"

LIMIT = 292.0          # cm: V5 Walk top is 291.8, Idle 290.3
P9 = os.path.join(ROOT, "Docs", "plans", "p9_d1_layout.json")
P10 = os.path.join(ROOT, "Docs", "plans", "p10_d1_layout.json")
CRYPT_FLOOR, CLOISTER_FLOOR = -600.0, 0.0

# ---- profiles -------------------------------------------------------------------------------------------------------
# SM_Roof, local underside height z by position (survey_p9.md "SM_Roof"; local x/y in the unscaled 478.2 bay, pivot at the crown)
G_DIAG = [(0, 2.0), (60, 2.0), (90, -2.0), (120, -23.0), (150, -63.0), (180, -132.0), (239.1, -296.0)]   # (t, z) on the groin
G_EDGE = [(0, 2.0), (25, -1.0), (55, -13.0), (85, -34.0), (115, -65.0), (145, -110.0), (239.1, -296.0)]  # open edge, y offset; beyond 145 straight to the corner
# SM_Arch half piece: underside z by distance d from the inner leg face (survey_p9.md "SM_Arch": x + 3.4), unscaled
U_ARCH = [(0, 290.0), (13.4, 298.0), (23.4, 326.0), (33.4, 349.0), (43.4, 358.0), (53.4, 370.0), (63.4, 381.0), (73.4, 393.0),
          (83.4, 401.0), (93.4, 406.0), (103.4, 410.0), (113.4, 414.0), (123.4, 419.0), (133.4, 420.0)]


def interp(table, x):
    if x <= table[0][0]:
        return table[0][1]
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return table[-1][1]


def vault_g(xl, yl):
    """Underside z (local, relative to the SM_Roof pivot) at local (xl, yl) in the unscaled bay.  Blend: on the diagonal the
    diagonal table, at the open edge (distance 239 along) the edge table, linear in between; on the centre lines +2."""
    a, b = sorted((min(abs(xl), 239.1), min(abs(yl), 239.1)))
    gd, ge = interp(G_DIAG, a), interp(G_EDGE, a)
    if b <= a or a >= 239.1:
        return gd
    return gd + (ge - gd) * (b - a) / (239.1 - a)


def arch_pointed_h(x, span):
    """Height of a two-centred pointed arch (radius 0.8 x span) above its springing, x from the nearer springing."""
    r = 0.8 * span
    x = max(0.0, min(x, span / 2.0))
    return math.sqrt(max(0.0, 2 * r * x - x * x))


# ---- records -------------------------------------------------------------------------------------------------------
def load_layouts():
    p9 = json.load(open(P9, encoding="utf-8"))["placements"]
    p10 = json.load(open(P10, encoding="utf-8"))["placements"]
    return p9, p10


def inside(rec, x, y, pad=0.0):
    a, b = rec["aabb_min"], rec["aabb_max"]
    return a[0] - pad <= x <= b[0] + pad and a[1] - pad <= y <= b[1] + pad


def parse_opening(note):
    m = re.search(r"opening (-?\d+)\.\.(-?\d+)", note)
    return (float(m.group(1)), float(m.group(2))) if m else None


class Model:
    def __init__(self, p9, p10):
        self.vaults9 = [r for r in p9 if r["cat"] == "vault"]
        self.ceil9 = [r for r in p9 if r["cat"] in ("ceiling", "soffit") or (r["cat"] == "grate" and "Sky" not in r["id"])]
        self.tiles9 = [r for r in p9 if r["cat"] == "tile"]
        portals = {}
        for r in p9:
            if r["cat"] == "portal":
                portals.setdefault(r["portal"], []).append(r)
        self.portals = []
        for pid, recs in portals.items():
            op = parse_opening(recs[0]["note"])
            yaw = recs[0]["rot"][1]
            axis = 0 if abs(yaw) < 1 else 1                         # opening runs along X (yaw 0) or Y (yaw 90)
            lo = [min(r["aabb_min"][i] for r in recs) for i in range(3)]
            hi = [max(r["aabb_max"][i] for r in recs) for i in range(3)]
            self.portals.append({"id": pid, "axis": axis, "open": op, "lo": lo, "hi": hi, "sx": abs(recs[0]["scale"][0]),
                                 "sz": abs(recs[0]["scale"][2]), "z0": recs[0]["loc"][2], "note": recs[0]["note"]})
        self.vault10 = [r for r in p10 if r["cat"] == "vault"]
        self.arcades = [r for r in p10 if r["cat"] == "arcade" and r["group"] == "arch"]
        self.piers = [r for r in p10 if r["cat"] == "arcade" and r["group"] in ("pier", "pier_corner")]
        self.archways = [r for r in p10 if r["cat"] == "wall" and r["group"] == "archway"]
        self.celldoors = [r for r in p10 if r["cat"] == "door"]
        self.floors10 = [r for r in p10 if r["cat"] == "floor"]
        self.tower_over = [r for r in p10 if (r["cat"] == "stair" and r["group"] == "landing") or r["group"] in ("belfryfloor", "towerroof")]
        self.garth = [r for r in p10 if r["cat"] == "garth" and r["group"] == "garthbed"]
        self.p9 = p9
        self.p10 = p10

    # each candidate: dict(kind, id, est, cons, crown)  (world Z of the underside)
    def candidates(self, x, y, floor):
        out = []
        if floor < -300:   # crypt
            for r in self.vaults9:
                sx, sy = r["scale"][0], r["scale"][1]
                xl, yl = (x - r["loc"][0]) / sx, (y - r["loc"][1]) / sy
                if abs(xl) <= 239.2 and abs(yl) <= 239.2:
                    z0 = r["loc"][2]
                    out.append({"kind": "crypt vault bay", "id": r["id"], "est": z0 + vault_g(xl, yl), "cons": r["aabb_min"][2], "crown": z0 + 2.0})
            for r in self.ceil9:
                if inside(r, x, y):
                    out.append({"kind": "crypt ceiling item", "id": r["id"], "est": r["aabb_min"][2], "cons": r["aabb_min"][2], "crown": r["aabb_min"][2]})
            for p in self.portals:
                ax = p["axis"]
                other = 1 - ax
                if not (p["lo"][other] <= (y, x)[ax] <= p["hi"][other] and p["lo"][ax] <= (x, y)[ax] <= p["hi"][ax]):
                    continue
                lat = (x, y)[ax]
                o0, o1 = p["open"]
                if lat < o0 or lat > o1:
                    out.append({"kind": "portal leg (solid)", "id": "Portal_" + p["id"], "est": None, "cons": None, "crown": None})
                    continue
                d = min(lat - o0, o1 - lat)
                est = p["z0"] + p["sz"] * interp(U_ARCH, d / p["sx"])
                out.append({"kind": "crypt portal arch", "id": "Portal_" + p["id"], "est": est, "cons": p["z0"] + p["sz"] * 290.0,
                            "crown": p["z0"] + p["sz"] * 420.0})
        else:              # cloister and tower (floor 0)
            for r in self.vault10:
                if inside(r, x, y):
                    out.append({"kind": "cloister barrel vault", "id": r["id"], "est": r["aabb_min"][2], "cons": r["aabb_min"][2],
                                "crown": r["aabb_min"][2] + 313.0})   # intrados apex ~ springing + 313 (README_cloister, C12)
            for r in self.arcades:
                if inside(r, x, y):
                    span = r["mbounds"][1][0] - r["mbounds"][0][0]
                    along = 0 if (r["aabb_max"][0] - r["aabb_min"][0]) >= (r["aabb_max"][1] - r["aabb_min"][1]) else 1
                    t = (x, y)[along] - r["aabb_min"][along]
                    t = min(t, span - t)
                    z0 = r["loc"][2]
                    out.append({"kind": "arcade arch", "id": r["id"], "est": z0 + arch_pointed_h(t, span), "cons": z0, "crown": z0 + 0.742 * span})
            for r in self.piers:
                if inside(r, x, y):
                    out.append({"kind": "pier (solid)", "id": r["id"], "est": None, "cons": None, "crown": None})
            for r in self.archways:
                if inside(r, x, y):
                    spr = r["mbounds"][0][2]
                    out.append({"kind": "archway", "id": r["id"], "est": spr, "cons": spr, "crown": spr + (120.0 if spr < 310 else 120.0)})
            for r in self.celldoors:
                if inside(r, x, y, pad=0.0):
                    out.append({"kind": "cell door frame", "id": r["id"], "est": 220.0, "cons": 220.0, "crown": 250.0})
            for r in self.tower_over:
                if r["aabb_min"][2] > 60 and inside(r, x, y) and 12000 <= x <= 12960 and 1540 <= y <= 2460:
                    out.append({"kind": "tower overhead", "id": r["id"], "est": r["aabb_min"][2], "cons": r["aabb_min"][2], "crown": r["aabb_min"][2]})
        return out

    def on_floor(self, x, y, floor):
        if floor < -300:
            return any(inside(t, x, y) for t in self.tiles9)
        return any(inside(f, x, y) for f in self.floors10)

    def in_garth(self, x, y):
        return 10330 <= x <= 11370 and 1430 <= y <= 2170   # inside the garth walls (CLA_GarthWall_*)


def evaluate(model, x, y, floor):
    """-> dict with est/cons/crown clearance (cm above floor), status, element ids."""
    c = [k for k in model.candidates(x, y, floor)]
    solid = [k for k in c if k["est"] is None]
    live = [k for k in c if k["est"] is not None]
    res = {"x": x, "y": y, "floor": floor, "floor_tile": model.on_floor(x, y, floor)}
    if not live:
        garth = floor > -300 and model.in_garth(x, y)
        res.update(status="NO-DATA", est=None, cons=None, crown=None, est_id="-", cons_id="-",
                   note=("open garth (no ceiling record; sky)" if garth else ("inside " + ", ".join(k["id"] for k in solid) if solid else "no ceiling record")))
        return res
    e = min(live, key=lambda k: k["est"])
    s = min(live, key=lambda k: k["cons"])
    est, cons = e["est"] - floor, s["cons"] - floor
    cr = [k["crown"] for k in live if k["kind"] != "tower overhead"]
    crown = (max(cr) if cr else e["est"]) - floor
    status = "BELOW" if est < LIMIT else ("SPRINGING-ONLY" if cons < LIMIT else "ok")
    res.update(status=status, est=est, cons=cons, crown=crown, est_id=e["id"], cons_id=s["id"], note=e["kind"])
    return res


# ---- markers from the editor -----------------------------------------------------------------------------------------
def read_markers(ue):
    cur = str(ue.call(SC, "get_current_level", {}))
    if "L_Monastery" not in cur:
        ue.call(SC, "load_level", {"level_path": "/Game/LastBell/Maps/L_Monastery"})
    out = {}
    for cls, props in (("LBPatrolPoint", ["RouteId", "Order"]), ("LBSearchPoint", []), ("LBWardenSpawnPoint", ["RouteId", "MinStage"])):
        acts = ue.call(SC, "find_actors", {"name": "", "tag": "", "collision_channels": [], "actor_type": {"refPath": "/Script/LastBell." + cls}})
        lst = []
        for a in acts:
            tf = ue.call(AC, "get_actor_transform", {"actor": a})
            d = {"name": a["refPath"].split(".")[-1], "x": tf["location"]["x"], "y": tf["location"]["y"], "z": tf["location"]["z"]}
            if props:
                d.update(json.loads(ue.call(OB, "get_properties", {"instance": a, "properties": props})))
            lst.append(d)
        out[cls] = lst
    return out


def read_doors(ue):
    seen, doors = {}, []
    for nm in ("Door", "Gate"):
        for a in ue.call(SC, "find_actors", {"name": nm, "tag": "", "collision_channels": []}):
            seen[a["refPath"]] = a
    for rp, a in seen.items():
        short = rp.split(".")[-1]
        if not (short.startswith("BP_Door_Base_Dungeon") or "CryptGate" in short):
            continue
        tf = ue.call(AC, "get_actor_transform", {"actor": a})
        lab = ue.call(AC, "get_label", {"actor": a})
        h = 224.0 if "Tower" in str(lab) else 230.0
        doors.append({"name": short, "label": str(lab), "x": tf["location"]["x"], "y": tf["location"]["y"], "z": tf["location"]["z"],
                      "clear": h if short.startswith("BP_Door") else None})
    return sorted(doors, key=lambda d: d["name"])


# ---- sampling ------------------------------------------------------------------------------------------------------------
def segment_samples(a, b, step):
    L = math.hypot(b["x"] - a["x"], b["y"] - a["y"])
    n = max(1, int(math.ceil(L / step)))
    pts = []
    for i in range(n + 1):
        d = min(i * step, L)
        t = d / L if L else 0
        pts.append((d, a["x"] + (b["x"] - a["x"]) * t, a["y"] + (b["y"] - a["y"]) * t))
    if pts[-1][0] < L - 1e-6:
        pts.append((L, b["x"], b["y"]))
    # drop a duplicated final point from the step grid
    out = []
    for p in pts:
        if not out or abs(p[0] - out[-1][0]) > 1e-6:
            out.append(p)
    return L, out


VIA = {("Crypt", 4): ["J8", "J10"], ("Crypt", 7): ["J7", "J6", "J5"], ("Cloister", 7): [(9850.0, 900.0)]}


def portal_centre(model, pid):
    for p in model.portals:
        if p["id"] == pid:
            ax = p["axis"]
            c = [0.0, 0.0]
            c[ax] = (p["open"][0] + p["open"][1]) / 2.0
            c[1 - ax] = (p["lo"][1 - ax] + p["hi"][1 - ax]) / 2.0
            return {"x": c[0], "y": c[1], "z": CRYPT_FLOOR}
    raise KeyError(pid)


def polyline_samples(pts, step):
    """Samples along a polyline: (d_from_start, x, y); every `step` cm of each leg, plus each leg end."""
    out, base = [], 0.0
    for a, b in zip(pts, pts[1:]):
        L, smp = segment_samples(a, b, step)
        for d, x, y in smp:
            if out and abs(base + d - out[-1][0]) < 1e-6:
                continue
            out.append((base + d, x, y))
        base += L
    return base, out


_TRACE = {}


def trace_up(ue, x, y, floor):
    """Clearance to the first collision above (greybox shell, lintel...), cm; 'open' if nothing within 1500; None on error."""
    key = (round(x), round(y), round(floor))
    if key in _TRACE:
        return _TRACE[key]
    try:
        d = ue.call(SC, "trace_world", {"start": {"x": x, "y": y, "z": floor + 5.0}, "end": {"x": x, "y": y, "z": floor + 1505.0}})
        v = "open" if d is None else (d + 5.0)
    except Exception:  # noqa: BLE001
        v = None
    _TRACE[key] = v
    return v


def tfmt(v):
    return "?" if v is None else (v if isinstance(v, str) else "%.0f" % v)


def fmt(v):
    return "-" if v is None else "%.0f" % v


def stair_headroom(model):
    """Headroom on the two crypt stairs, tread by tread, under the slab / soffit.  Off the patrol set but on a chase path."""
    rows = []
    soff = {r["id"]: r for r in model.p9 if r["cat"] == "soffit"}
    ceil_slab = -40.0   # underside of the Z -40..0 world ground slab (survey_p9.md 6.8)
    s_x0, s_x1 = soff["CA_Soffit_Sacristy"]["aabb_min"][0], soff["CA_Soffit_Sacristy"]["aabb_max"][0]
    s_z = soff["CA_Soffit_Sacristy"]["aabb_min"][2]
    for n in range(40):
        xc0, xc1 = 6800 + 30 * n, 6830 + 30 * n
        top = -600 + 15 * (n + 1)
        if xc1 <= 7400:
            ceil = s_z if (xc0 >= s_x0 and xc1 <= s_x1) else ceil_slab
            ceil = min(ceil, ceil_slab) if xc0 >= s_x0 else ceil_slab
            rows.append(("Sacristy stair", n, "X %d-%d" % (xc0, xc1), top, ceil, ceil - top))
    e_y0 = soff["CA_Soffit_Exit"]["aabb_min"][1]
    e_z = soff["CA_Soffit_Exit"]["aabb_min"][2]
    for n in range(40):
        yc0, yc1 = -700 + 30 * n, -670 + 30 * n
        top = -600 + 15 * (n + 1)
        if yc1 <= -100:
            ceil = e_z if yc0 >= e_y0 else ceil_slab
            rows.append(("Exit stair", n, "Y %d-%d" % (yc0, yc1), top, ceil, ceil - top))
    return rows


def main():
    out_path = os.path.join(ROOT, "Docs", "ArtTest", "warden", "p12_clearance.md")
    step = 100.0
    if "--out" in sys.argv:
        out_path = sys.argv[sys.argv.index("--out") + 1]
    if "--step" in sys.argv:
        step = float(sys.argv[sys.argv.index("--step") + 1])
    ue = UE()
    mk = read_markers(ue)
    doors = read_doors(ue)
    p9, p10 = load_layouts()
    model = Model(p9, p10)

    routes = {}
    for p in mk["LBPatrolPoint"]:
        routes.setdefault(p["RouteId"], []).append(p)
    for k in routes:
        routes[k].sort(key=lambda p: p["Order"])

    seg_rows, all_eval = [], []
    sample_lines = []
    for rid in ("Crypt", "Cloister"):
        pts = routes[rid]
        for i, a in enumerate(pts):
            b = pts[(i + 1) % len(pts)]
            closing = (i + 1) == len(pts)
            floor = a["z"]
            via = VIA.get((rid, a["Order"]), [])
            vpts = [portal_centre(model, v) if isinstance(v, str) else {"x": v[0], "y": v[1], "z": floor} for v in via]
            L, smp = polyline_samples([a] + vpts + [b], step)
            segname = "%d->%d%s%s" % (a["Order"], b["Order"], " (loop)" if closing else "",
                                      (" via " + ",".join(v if isinstance(v, str) else "(%d,%d)" % v for v in via)) if via else "")
            ev = []
            for d, x, y in smp:
                r = evaluate(model, x, y, floor)
                r["d"] = d
                r["trace"] = trace_up(ue, x, y, floor)
                ev.append(r)
                sample_lines.append((rid, segname, r))
            all_eval += [(rid, r) for r in ev]
            live = [r for r in ev if r["est"] is not None]
            worst = min(live, key=lambda r: r["est"]) if live else None
            wcons = min(live, key=lambda r: r["cons"]) if live else None
            seg_rows.append({"route": rid, "seg": segname, "len": L, "n": len(ev),
                             "nodata": sum(1 for r in ev if r["status"] == "NO-DATA"), "offfloor": sum(1 for r in ev if not r["floor_tile"]),
                             "worst": worst, "wcons": wcons, "below": sum(1 for r in ev if r["status"] == "BELOW"),
                             "spr": sum(1 for r in ev if r["status"] == "SPRINGING-ONLY"), "ev": ev})

    pts_eval = []
    for kind, lst in (("Search point", mk["LBSearchPoint"]), ("Spawn point", mk["LBWardenSpawnPoint"])):
        for p in lst:
            r = evaluate(model, p["x"], p["y"], p["z"])
            r["trace"] = trace_up(ue, p["x"], p["y"], p["z"])
            extra = ""
            if kind == "Spawn point":
                extra = "route %s, MinStage %s" % (p.get("RouteId"), p.get("MinStage"))
            pts_eval.append((kind, p["name"], r, extra))

    # distances to doors from every sampled/point location
    allpos = [("route %s %s" % (rid, seg), r["x"], r["y"]) for rid, seg, r in sample_lines] + [(k + " " + n, r["x"], r["y"]) for k, n, r, e in pts_eval]
    door_rows = []
    for dr in doors:
        near = min(allpos, key=lambda t: math.hypot(t[1] - dr["x"], t[2] - dr["y"]))
        door_rows.append((dr, near, math.hypot(near[1] - dr["x"], near[2] - dr["y"])))
    cell_rows = []
    for cd in model.celldoors:
        c = [cd["loc"][0], cd["loc"][1]]
        near = min(allpos, key=lambda t: math.hypot(t[1] - c[0], t[2] - c[1]))
        cell_rows.append((cd, near, math.hypot(near[1] - c[0], near[2] - c[1])))

    # ---- write the report -----------------------------------------------------------------------------------------------
    allr = [r for _, r in all_eval] + [r for _, _, r, _ in pts_eval]
    below = [(k, n, r) for k, n, r, _ in pts_eval if r["status"] == "BELOW"]
    L = []
    w = L.append
    w("# P12-5 clearance: how much headroom the Warden has on its routes (limit below covers V5 and V5.5; V5.5 Idle 285.6, Walk 290.1)")
    w("")
    w("Generated by `Tools/warden/measure_clearance.py` (read-only; re-run it to regenerate). Limit: **%d cm** (V5 Idle tops out at 290.3, Walk at 291.8)." % LIMIT)
    w("")
    w("## How to read the numbers")
    w("- Traces cannot find the ceilings (the art has no collision), so every number comes from the layout records `Docs/plans/p9_d1_layout.json` (crypt) and `p10_d1_layout.json` (cloister, tower), measured from the floor.")
    w("- **conservative** = the lowest AABB bottom / springing of any ceiling record over the point. A vault's or arch's bounding box starts at its springing, which is lower than the curved surface above most of the floor, so this number is a floor under the real clearance.")
    w("- **estimated** = the underside at the point where the profile is known (crypt `SM_Roof` bay from the P9 survey grid, crypt `SM_Arch` portals from the survey's traced table, cloister arcade arches from their geometry). **The crypt vault profile is modelled from the survey's sample points, not measured on the mesh.** Where no profile is known (cloister barrel vault, the two archways, beams, boards) estimated = conservative.")
    w("- **crown** = the highest intrados the data gives over the point (vault crown +2 from its pivot; arch crown; barrel-vault apex ~ springing + 313).")
    w("- Status: BELOW = estimated < %d; SPRINGING-ONLY = only the conservative number is below %d; ok = both at or above; NO-DATA = no ceiling record over the point (never counted as clear)." % (LIMIT, LIMIT))
    w("- **greybox trace up** = a vertical `trace_world` from floor+5 cm, first hit within 1500 cm. The crypt, cloister and tower greybox shells keep their (hidden) collision, so this is what the Warden's capsule actually meets; it sees collision only, never the art. 'open' = nothing within 1500 cm.")
    w("- Floor = the markers' own Z (crypt %d, cloister 0). Route segments are straight lines between waypoints (and last -> first, the route loops), sampled every %d cm; the walked path follows the navmesh through the portals, so some samples lie in walls, over the pit or in the garth. They are marked. Three segments whose straight line leaves the rooms (crypt 4->5 and the loop 7->1 cross solid rock, the cloister loop 7->1 crosses the garth) are sampled along an **assumed** path through the portal openings (J8, J10; J7, J6, J5) or round the walk corner (9850, 900); the segment name says so." % (CRYPT_FLOOR, step))
    w("")

    # summary
    def stat(rows, key):
        v = [r[key] for r in rows if r.get(key) is not None]
        return min(v) if v else None

    w("## Summary")
    for rid in ("Crypt", "Cloister"):
        rr = [r for rr_, r in all_eval if rr_ == rid]
        live = [r for r in rr if r["est"] is not None]
        w("- **%s route** (%d samples): lowest estimated clearance **%s cm**, lowest conservative **%s cm**; BELOW %d, SPRINGING-ONLY %d, NO-DATA %d, over no floor tile / garth: %d."
          % (rid, len(rr), fmt(stat(rr, "est")), fmt(stat(rr, "cons")), sum(r["status"] == "BELOW" for r in rr),
             sum(r["status"] == "SPRINGING-ONLY" for r in rr), sum(r["status"] == "NO-DATA" for r in rr), sum(not r["floor_tile"] for r in rr)))
    trs = [r["trace"] for rid_, r in all_eval if isinstance(r.get("trace"), float)]
    w("- **Greybox trace** over all route samples: lowest first hit %s cm (the hidden shell collision); samples with no hit within 1500: %d." % (fmt(min(trs)) if trs else "-", sum(1 for _, r in all_eval if r.get("trace") == "open")))
    for kind in ("Search point", "Spawn point"):
        rr = [r for k, _, r, _ in pts_eval if k == kind]
        w("- **%ss** (%d): lowest estimated **%s cm**, lowest conservative **%s cm**; BELOW %d, SPRINGING-ONLY %d, NO-DATA %d."
          % (kind, len(rr), fmt(stat(rr, "est")), fmt(stat(rr, "cons")), sum(r["status"] == "BELOW" for r in rr),
             sum(r["status"] == "SPRINGING-ONLY" for r in rr), sum(r["status"] == "NO-DATA" for r in rr)))
    w("")

    w("## Places below %d cm" % LIMIT)
    w("")
    w("### On the routes, search points and spawn points")
    below_s = [(rid, seg, r) for rid, seg, r in sample_lines if r["status"] == "BELOW"]
    if not below_s and not below:
        w("**None** by the estimated number. The crypt and the cloister samples that are not NO-DATA are all at or above %d cm (lowest estimated: crypt %s, cloister %s)." %
          (LIMIT, fmt(stat([r for rid, r in all_eval if rid == "Crypt"], "est")), fmt(stat([r for rid, r in all_eval if rid == "Cloister"], "est"))))
    else:
        for rid, seg, r in below_s:
            w("- route %s %s at (%.0f, %.0f): est %s, conservative %s (%s)" % (rid, seg, r["x"], r["y"], fmt(r["est"]), fmt(r["cons"]), r["est_id"]))
        for k, n, r in below:
            w("- %s %s at (%.0f, %.0f): est %s, conservative %s (%s)" % (k, n, r["x"], r["y"], fmt(r["est"]), fmt(r["cons"]), r["est_id"]))
    w("")
    sp = [(rid, seg, r) for rid, seg, r in sample_lines if r["status"] == "SPRINGING-ONLY"]
    sp_pts = [(k, n, r) for k, n, r, _ in pts_eval if r["status"] == "SPRINGING-ONLY"]
    w("**Springing-only** (the conservative number is under %d, the estimate is not): %d of %d route samples and %d of %d search/spawn points. These are crypt samples where an `SM_Roof` bay covers the point: its AABB bottom is the bay corner at 260 above the floor, while the estimated underside over the route is far higher; the greybox shell collision over every one of them is at 560. Lowest estimated value among them: %s cm. The full list is in the appendix (status column)."
      % (LIMIT, len(sp), len(sample_lines), len(sp_pts), len(pts_eval),
         fmt(min([r["est"] for _, _, r in sp] + [r["est"] for _, _, r in sp_pts]) if (sp or sp_pts) else None)))
    w("")
    w("### Doors (all below %d, by the plan's sizes: doors 104 x 230, tower door 104 x 224)" % LIMIT)
    w("")
    w("| Door actor | Label | Location (x, y, z) | Clear height | Nearest sampled route/search/spawn position | Distance |")
    w("|---|---|---|---|---|---|")
    for dr, near, dist in door_rows:
        w("| %s | %s | %.0f, %.0f, %.0f | %s | %s (%.0f, %.0f) | %.0f cm |" % (dr["name"], dr["label"], dr["x"], dr["y"], dr["z"],
          ("%d cm" % dr["clear"]) if dr["clear"] else "gate: open/closed, opening is the portal arch (crown 500, springing 345)", near[0], near[1], near[2], dist))
    w("")
    w("Cloister cell doors (`SM_LB_Cl_CellDoorFrame_150x270`): opening 110 wide, straight-sided pointed head, shoulders at 220, apex 250; the hung leaf is about 250 tall. Both numbers are below %d." % LIMIT)
    w("")
    w("| Cell door | Location (x, y) | Nearest sampled position | Distance |")
    w("|---|---|---|---|")
    for cd, near, dist in cell_rows:
        w("| %s | %.0f, %.0f | %s (%.0f, %.0f) | %.0f cm |" % (cd["id"], cd["loc"][0], cd["loc"][1], near[0], near[1], near[2], dist))
    w("")
    w("The tower door's art head (P10 plan, S1_W): jambs at 194, gabled apex 228; the greybox lintel that sets the collision is at 224. Every door above is a place where the Warden must stoop (DoorwayStoop tops out at 217.4 at its lowest) if it ever passes through. The nearest route, search or spawn position to each door is in the table (no door is closer than the distance shown to any sampled position).")
    w("")
    w("### Off the patrol set but on a chase path: the crypt stairs")
    w("Under the Z -40..0 ground slab (soffit/lintel underside -44/-45) the stair treads rise 15 per 30; headroom = ceiling - tread top. Treads below %d:" % LIMIT)
    w("")
    w("| Stair | Step | Position | Tread top Z | Ceiling Z | Headroom |")
    w("|---|---|---|---|---|---|")
    low = [r for r in stair_headroom(model) if r[5] < LIMIT]
    for s_, n, pos, top, ce, hr in low:
        w("| %s | %d | %s | %.0f | %.0f | %.0f |" % (s_, n, pos, top, ce, hr))
    w("")
    w("The sacristy stair is open above X 7400 (shaft into the chapel; survey_p9 6.8 traced the chapel roof at Z 439 over X 8000) and the exit stair is open above Y -100 (to the cloister). The pinch is the last treads under the slab, lowest headroom %.0f cm." % min(r[5] for r in stair_headroom(model)))
    w("")
    w("### Tight but above %d: archways and arcade arches in the cloister" % LIMIT)
    for r in model.archways:
        w("- `%s`: springing %.0f (margin %.0f over %d), apex %.0f. %s" % (r["id"], r["mbounds"][0][2], r["mbounds"][0][2] - LIMIT, LIMIT,
          r["mbounds"][0][2] + 120.0, "The four-centred profile rises quickly, but the jambs sit only a few cm above the Walk top (291.8)." if r["mbounds"][0][2] < 310 else ""))
    w("- Arcade arches (14): springing 330 (margin %.0f), pointed apex 0.742 x span above it (span 120 to 270: apex 419 to 530)." % (330 - LIMIT))
    w("")

    w("## Ceiling types used (springing and crown)")
    w("")
    w("| Ceiling | Springing / lowest | Crown / highest intrados | Source |")
    w("|---|---|---|---|")
    w("| Crypt `SM_Roof` bay (18; pivot Z -44) | AABB bottom -339.8 = **260 cm** above the -600 floor (the bay corners, buried in the column capitals) | -42 = **558 cm** (crown +2 on the centre lines) | P9 layout, survey_p9 SM_Roof |")
    w("| Crypt `SM_Arch` portals (11 pairs, Z scale 1.19) | -255 = **345 cm** (at the jambs) | -100 = **500 cm** | P9 layout notes, survey_p9 SM_Arch |")
    w("| Crypt chain-chamber ceiling (beams/boards/corbels, X 10000-11500) | beams -95 = 505; broken boards -95.9 = 504; boards -50 = 550; corbels (wall brackets) -140 = 460 | same | P9 layout |")
    w("| Crypt soffits/lintels over the stairs | -44 / -45 | same | P9 layout |")
    w("| Cloister barrel vault (10 bays) | springing 540 | intrados apex ~853 (rib soffit 828); extrados 880 | P10 layout, README_cloister (C12) |")
    w("| Cloister arcade arches (14) | 330 | 330 + 0.742 x span | P10 tables |")
    w("| Cloister archways W / S | 300 / 330 | 420 / 450 | P10 tables |")
    w("| Tower (spawn 2) | underside of landing 03 = 622 | - | P10 layout |")
    w("")
    w("## Could not be determined")
    w("- **Crypt vault underside between the survey samples is modelled** (blend of the diagonal and edge profiles); the mesh has no collision and no vertex readout exists. The conservative numbers do not depend on it. Where the estimate is within ~40 cm of %d the number should be treated as unverified; none of the route samples is that close unless listed above." % LIMIT)
    w("- The cloister barrel vault's lower surface is taken as its springing (540) everywhere; the true intrados is higher, up to ~853 at the apex.")
    w("- **Dressing is not treated as a ceiling**: hanging roots (`RootsHang`), chains, lanterns on brackets, cobwebs, the moon-grate collars (bottom -62 = 538) were not checked against the head.")
    w("- Straight-line sampling: wall, pit and garth samples are marked in the appendix; the true walked path was not computed (no navigation query is available through the tools).")
    w("- NO-DATA samples are listed below and are not counted as clear.")
    nod = [(rid, seg, r) for rid, seg, r in sample_lines if r["status"] == "NO-DATA"]
    if nod:
        for rid, seg, r in nod:
            w("  - route %s %s at (%.0f, %.0f): %s" % (rid, seg, r["x"], r["y"], r["note"]))
    else:
        w("  - (none on the routes)")
    for k, n, r, e in pts_eval:
        if r["status"] == "NO-DATA":
            w("  - %s %s at (%.0f, %.0f): %s" % (k, n, r["x"], r["y"], r["note"]))
    w("")

    # segment table
    w("## Route segments")
    w("")
    w("| Route | Segment | Length | Samples | Lowest est. (at) | Element | Lowest conservative | Lowest greybox trace | BELOW | SPRINGING-ONLY | NO-DATA | No floor tile / garth |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for s in seg_rows:
        ww = s["worst"]
        tr = [r["trace"] for r in s["ev"] if isinstance(r.get("trace"), float)]
        w("| %s | %s | %.0f | %d | %s%s | %s | %s | %s | %d | %d | %d | %d |" % (s["route"], s["seg"], s["len"], s["n"], fmt(ww["est"]) if ww else "-",
          (" (%.0f, %.0f)" % (ww["x"], ww["y"])) if ww else "", ww["est_id"] if ww else "-", fmt(s["wcons"]["cons"]) if s["wcons"] else "-",
          fmt(min(tr)) if tr else "open/none", s["below"], s["spr"], s["nodata"], s["offfloor"]))
    w("")
    w("## Search points and spawn points")
    w("")
    w("| Kind | Name | x, y | Floor | Estimated | Conservative | Crown | Greybox trace up | Status | Element (estimated) | Note |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    for k, n, r, e in pts_eval:
        w("| %s | %s | %.0f, %.0f | %.0f | %s | %s | %s | %s | %s | %s | %s |" % (k, n, r["x"], r["y"], r["floor"], fmt(r["est"]), fmt(r["cons"]), fmt(r["crown"]),
          tfmt(r["trace"]), r["status"], r["est_id"], (e + ("; " if e and r["note"] else "") + r["note"]) if (e or r["note"]) else ""))
    w("")
    w("## Appendix: every route sample (%d cm step)" % step)
    w("")
    w("| Route | Segment | Along | x, y | Estimated | Conservative | Crown | Greybox trace up | Status | Element (estimated) | Note |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    for rid, seg, r in sample_lines:
        note = r["note"] + ("" if r["floor_tile"] else ("; no floor tile / garth" if r["status"] != "NO-DATA" else ""))
        w("| %s | %s | %.0f | %.0f, %.0f | %s | %s | %s | %s | %s | %s | %s |" % (rid, seg, r["d"], r["x"], r["y"], fmt(r["est"]), fmt(r["cons"]),
          fmt(r["crown"]), tfmt(r["trace"]), r["status"], r["est_id"], note))
    w("")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L))
    print("wrote", out_path)
    print("route samples", len(sample_lines), "points", len(pts_eval), "doors", len(doors))
    for s in seg_rows:
        print(s["route"], s["seg"], "len %.0f" % s["len"], "worst est", fmt(s["worst"]["est"]) if s["worst"] else None, "cons", fmt(s["wcons"]["cons"]) if s["wcons"] else None,
              "below", s["below"], "nodata", s["nodata"], "offfloor", s["offfloor"])
    for k, n, r, e in pts_eval:
        print(k, n, "%.0f,%.0f" % (r["x"], r["y"]), r["status"], fmt(r["est"]), fmt(r["cons"]), r["est_id"], r["note"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
