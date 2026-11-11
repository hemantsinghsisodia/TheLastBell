"""P15 F0: READ-ONLY survey of L_Monastery for the particles phase (Docs/plans/P15_PARTICLES.md, task F0).

Run (editor open on L_Monastery, PIE off), with the isolated interpreter:
    python -I Tools/fx/p15_f0_survey.py [--resume] [--stages a,b,c] [--tables]

Read-only calls only: IsPIERunning, get_current_level, is_dirty, find_actors, get_label, get_actor_transform,
get_actor_bounds, get_root_component, get_components, get_properties, find_assets, get_referencers,
get_material_slots, get_material, get_bounds, trace_world, describe_toolset, and the Niagara Get*/Find* tools.
Nothing is spawned, set, deleted, saved or captured; no PIE; no input.

Outputs:
    Docs/ArtTest/fx/p15_f0.json               all raw data
    Docs/ArtTest/fx/p15_f0_tables.md          readable tables (run with --tables, or the last stage)
    Docs/ArtTest/fx/p15_f0_niagara_tools.md   the Niagara toolsets (stage `niagara`)
Cache: Saved/p15_f0_cache.jsonl (one JSON line per finished step; --resume reuses it; Saved/ is git-ignored).
"""
import argparse
import json
import math
import os
import re
import socket
import sys
import time
import urllib.error
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Tools", "mcp"))
import ue as ue_mod  # noqa: E402
from ue import UE  # noqa: E402

S = "editor_toolset.toolsets.scene.SceneTools"
A = "editor_toolset.toolsets.actor.ActorTools"
O = "editor_toolset.toolsets.object.ObjectTools"
AS = "editor_toolset.toolsets.asset.AssetTools"
SM = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
E = "EditorToolset.EditorAppToolset"
MAP_PKG = "/Game/LastBell/Maps/L_Monastery"
OUT_DIR = os.path.join(ROOT, "Docs", "ArtTest", "fx")
OUT_JSON = os.path.join(OUT_DIR, "p15_f0.json")
CACHE = os.path.join(ROOT, "Saved", "p15_f0_cache.jsonl")
TIMEOUT_S = 180

NEVER_SAVE = ["BP_SmallBell", "BP_SequencePuzzle", "BP_Inscription", "BP_RitualMechanism", "BP_Door_Base", "BP_TagInteractable",
              "BP_TagTrigger", "BP_Inspectable_Note", "BP_Door_Base_Dungeon", "BP_RitualMechanism_CryptWinch",
              "BP_WardenApparition"]

J = lambda x: json.loads(x) if isinstance(x, str) else x  # noqa: E731


class EditorStop(Exception):
    pass


class UE180(UE):
    """UE with a 180 s socket timeout."""

    def _post(self, body):
        import urllib.request
        h = dict(ue_mod.HEADERS)
        if self.sid:
            h["Mcp-Session-Id"] = self.sid
        req = urllib.request.Request(self.url, json.dumps(body).encode(), h)
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            self.sid = self.sid or r.headers.get("Mcp-Session-Id")
            raw = r.read().decode("utf-8", "replace").strip()
        if not raw:
            return None
        if not raw.startswith("{"):
            raw = next(line[5:] for line in raw.splitlines() if line.startswith("data:"))
        return json.loads(raw)


def R(x):
    if isinstance(x, dict):
        x = x.get("refPath")
    if not x or x in ("None", "null"):
        return None
    return x


def short(ref):
    return ref.rsplit(".", 1)[-1].rsplit("/", 1)[-1] if ref else None


def oname(ref):
    return ref.split("PersistentLevel.", 1)[1] if "PersistentLevel." in ref else ref.rsplit(".", 1)[-1]


def cls_of(ref):
    return re.sub(r"_\d+$", "", oname(ref).split(".")[0])


def v3(d, keys="xyz"):
    return [round(float(d[k]), 1) for k in keys]


def area_of(x, y, z):
    """Coarse area from world position (same boxes as the P14 survey)."""
    if x >= 6300 and -2950 <= y <= 520 and z < -45:
        return "crypt"
    if 11990 <= x <= 13010 and 1490 <= y <= 2510:
        return "tower"
    if 9460 <= x <= 12040 and 500 <= y <= 3040:
        return "cloister"
    if 6040 <= x < 9460 and 900 <= y <= 2600:
        return "passage"
    if 6000 <= x <= 9100 and -1550 <= y <= 860:
        return "chapel"
    if 300 <= x < 6000 and -2600 <= y <= 2600:
        return "courtyard"
    if x < 300:
        return "approach"
    return "other"


class Survey:
    def __init__(self, resume):
        self.ue = UE180()
        self.calls = 0
        self.errors = []
        self.cache = {}
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        if resume and os.path.exists(CACHE):
            for line in open(CACHE, encoding="utf-8"):
                if line.strip():
                    try:
                        d = json.loads(line)
                        self.cache[d["k"]] = d["v"]
                    except Exception:  # noqa: BLE001
                        pass
        elif os.path.exists(CACHE):
            os.replace(CACHE, CACHE + ".old")
        self.cf = open(CACHE, "a", encoding="utf-8")
        self.t0 = time.time()

    # ------------------------------------------------------------------ plumbing
    def call(self, ts, tool, args=None):
        """One read-only call. Retried on a new session (up to 3 times) on a connection reset or a transient error."""
        last = None
        for attempt in range(3):
            try:
                self.calls += 1
                return self.ue.call(ts, tool, args or {})
            except RuntimeError as e:
                msg = str(e)
                if any(s in msg for s in ("could not be read", "not found", "not a valid", "Failed to find", "does not exist",
                                          "No such", "Could not find", "Invalid", "is required")):
                    raise
                last = msg[:300]
                time.sleep(2)
            except (ConnectionError, TimeoutError, socket.timeout, urllib.error.URLError, OSError) as e:
                last = "%s: %s" % (type(e).__name__, str(e)[:200])
                time.sleep(3)
                try:
                    self.ue = UE180()
                except Exception:  # noqa: BLE001
                    pass
        raise RuntimeError("FAILED %s.%s: %s" % (ts.rsplit(".", 1)[-1], tool, last))

    def try_call(self, ts, tool, args, ctx):
        try:
            return self.call(ts, tool, args)
        except RuntimeError as e:
            self.errors.append({"ctx": ctx, "tool": tool, "error": str(e)[:300]})
            return None

    def getp(self, ref, names):
        names = list(names)
        for _ in range(12):
            if not names:
                return {}
            try:
                return J(self.call(O, "get_properties", {"instance": {"refPath": ref}, "properties": names}))
            except RuntimeError as e:
                m = re.search(r"could not be read: (.*)$", str(e))
                if not m:
                    self.errors.append({"ctx": ref, "tool": "get_properties", "error": str(e)[:300]})
                    return {}
                bad = [x.strip() for x in m.group(1).replace("'", "").split(",")]
                left = [x for x in names if x not in bad]
                if len(left) == len(names):
                    return {}
                names = left
        return {}

    def step(self, key, fn):
        if key in self.cache:
            return self.cache[key]
        v = fn()
        self.cache[key] = v
        self.cf.write(json.dumps({"k": key, "v": v}) + "\n")
        self.cf.flush()
        return v

    def log(self, msg):
        print("[%6.0fs, %5d calls] %s" % (time.time() - self.t0, self.calls, msg), flush=True)

    # ------------------------------------------------------------------ cached primitives
    def find(self, name="", tag=""):
        return self.step("find:%s|%s" % (name, tag), lambda: [x["refPath"] for x in self.call(S, "find_actors", {"name": name, "tag": tag, "collision_channels": []})])

    def label(self, ref):
        return self.step("label:" + ref, lambda: self.try_call(A, "get_label", {"actor": {"refPath": ref}}, ref))

    def xform(self, ref):
        def f():
            t = self.try_call(A, "get_actor_transform", {"actor": {"refPath": ref}}, ref)
            t = J(t) if t else None
            return {"loc": v3(t["location"]), "rot": v3(t["rotation"], ("pitch", "yaw", "roll")), "scale": v3(t["scale"])} if t else None
        return self.step("xf:" + ref, f)

    def bounds(self, ref):
        def f():
            b = self.try_call(A, "get_actor_bounds", {"actor": {"refPath": ref}}, ref)
            b = J(b) if b else None
            return {"min": v3(b["min"]), "max": v3(b["max"])} if b and b.get("isValid", True) else None
        return self.step("bounds:" + ref, f)

    def trace(self, a, b):
        key = "trace:%s>%s" % (",".join("%.1f" % x for x in a), ",".join("%.1f" % x for x in b))

        def f():
            r = self.try_call(S, "trace_world", {"start": dict(zip("xyz", a)), "end": dict(zip("xyz", b))}, key)
            if isinstance(r, dict):
                r = r.get("returnValue", r.get("distance"))
            return None if r in (None, "None", "null") else float(r)
        return self.step(key, f)

    def mesh_bounds(self, mref):
        def f():
            b = self.try_call(SM, "get_bounds", {"mesh": {"refPath": mref}}, mref)
            return J(b) if b else None
        return self.step("meshbounds:" + mref, f)

    def mesh_slots(self, mref):
        def f():
            names = J(self.try_call(SM, "get_material_slots", {"mesh": {"refPath": mref}}, mref) or "[]") or []
            names = [n if isinstance(n, str) else (n.get("slotName") or n.get("name")) for n in names]
            out = []
            for n in names:
                m = self.try_call(SM, "get_material", {"mesh": {"refPath": mref}, "slot_name": n}, mref)
                out.append({"slot": n, "default": short(R(J(m) if m else None))})
            return out
        return self.step("slots:" + mref, f)

    def components(self, ref):
        def f():
            comps = J(self.try_call(A, "get_components", {"actor": {"refPath": ref}}, ref) or "[]") or []
            return [R(c) for c in comps if R(c)]
        return self.step("comps:" + ref, f)

    # ------------------------------------------------------------------ the full static-mesh-actor scan
    def sma(self, ref):
        def f():
            lab = self.label(ref)
            p = self.getp(ref + ".StaticMeshComponent0", ["staticMesh", "overrideMaterials"])
            return {"label": lab, "mesh": short(R(p.get("staticMesh"))), "mesh_ref": R(p.get("staticMesh")),
                    "ov": [short(R(o)) for o in (p.get("overrideMaterials") or [])],
                    "ov_ref": [R(o) for o in (p.get("overrideMaterials") or [])]}
        return self.step("sma:" + ref, f)


# ---------------------------------------------------------------------------------------------------------------
STAGES = []


def stage(fn):
    STAGES.append(fn.__name__)
    return fn


@stage
def census(sv, inv):
    h = sv.step("header", lambda: {"pie": sv.call(E, "IsPIERunning"), "level": sv.call(S, "get_current_level", {}),
                                   "dirty_before": sv.call(AS, "is_dirty", {"asset_path": MAP_PKG}),
                                   "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    if h["pie"]:
        raise SystemExit("PIE is running: stop it first")
    if not str(h["level"]).startswith(MAP_PKG):
        raise SystemExit("current level is %s, not L_Monastery" % h["level"])
    inv["header"] = h
    refs = sv.step("census", lambda: [x["refPath"] for x in sv.call(S, "find_actors", {"name": "", "tag": "", "collision_channels": []})])
    inv["census"] = {"count": len(refs), "method": "SceneTools.find_actors name='' tag=''",
                     "by_class": dict(Counter(cls_of(r) for r in refs).most_common())}
    sv.log("census: %d actors" % len(refs))
    return refs


@stage
def smascan(sv, inv, refs):
    smas = [r for r in refs if cls_of(r) == "StaticMeshActor"]
    for i, r in enumerate(smas):
        sv.sma(r)
        if i % 250 == 0:
            sv.log("sma %d/%d" % (i, len(smas)))
    inv["sma_count"] = len(smas)
    return {r: sv.cache["sma:" + r] for r in smas}


# ---------------------------------------------------------------------------------------------------------------
# geometry helpers
def rot_axes(pitch, yaw, roll):
    """UE FRotator (degrees) to the three world-space axes (X forward, Y right, Z up) of the rotated frame."""
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    sy, cy = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    sr, cr = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    ax = (cp * cy, cp * sy, sp)
    ay = (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp)
    az = (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp)
    return ax, ay, az


def local_to_world(xf, p):
    """xf = {'loc','rot'(pitch,yaw,roll),'scale'}; p = local point (before scale)."""
    ax, ay, az = rot_axes(*xf["rot"])
    s = xf["scale"]
    q = (p[0] * s[0], p[1] * s[1], p[2] * s[2])
    return [round(xf["loc"][i] + q[0] * ax[i] + q[1] * ay[i] + q[2] * az[i], 1) for i in range(3)]


def box_corners(bmin, bmax):
    return [(x, y, z) for x in (bmin[0], bmax[0]) for y in (bmin[1], bmax[1]) for z in (bmin[2], bmax[2])]


def seg_dist(p, a, b):
    ab = [b[i] - a[i] for i in range(3)]
    ap = [p[i] - a[i] for i in range(3)]
    d2 = sum(x * x for x in ab)
    t = 0.0 if d2 == 0 else max(0.0, min(1.0, sum(ap[i] * ab[i] for i in range(3)) / d2))
    c = [a[i] + t * ab[i] for i in range(3)]
    return math.dist(p, c)


def class_to_bp(class_ref):
    """'/Game/X/BP_Y.BP_Y_C' -> '/Game/X/BP_Y.BP_Y'; None for /Script classes."""
    if not class_ref or class_ref.startswith("/Script/"):
        return None
    return re.sub(r"_C$", "", class_ref)


def sma_effective(sv, rec, ov_ref):
    """Per-slot effective material of a static mesh (instance override, else the mesh default)."""
    slots = sv.mesh_slots(rec["mesh_ref"]) if rec.get("mesh_ref") else []
    out = []
    for i, s in enumerate(slots):
        o = short(R(ov_ref[i])) if i < len(ov_ref) and R(ov_ref[i]) else None
        out.append({"slot": s["slot"], "material": o or s["default"], "source": "instance override" if o else "mesh default",
                    "mesh_default": s["default"]})
    return out


LIGHT_LABELS = ["L_Crypt_Torch_T1", "L_Crypt_Torch_T2", "L_Crypt_Torch_T3", "L_Crypt_Brazier", "Light_FirePit_Ember", "Light_WorkArea_Torch"]


def _find_exact(sv, label):
    return [r for r in sv.find(label) if sv.label(r) == label]


@stage
def lanes(sv, inv, refs, SMA):
    """Walk paths, patrol/search/spawn points: positions, for lane-clearance checks of the proposals."""
    out = {"points": []}
    for r in refs:
        c = cls_of(r)
        if c in ("TargetPoint", "LBPatrolPoint", "LBSearchPoint", "LBWardenSpawnPoint", "PlayerStart", "LBCheckpoint"):
            x = sv.xform(r)
            out["points"].append({"ref": r, "class": c, "label": sv.label(r), "loc": x["loc"] if x else None})
    inv["lane_points"] = out["points"]
    sv.log("lane points: %d" % len(out["points"]))
    return out


def lane_report(inv, p, z_band=250.0):
    """Nearest WalkPath segment (3D, by label prefix WP_<name>_NN) and nearest AI point to p."""
    paths = defaultdict(list)
    ai = []
    for q in inv["lane_points"]:
        if not q["loc"] or not q["label"]:
            continue
        m = re.match(r"^WP_(.+)_(\d+)$", q["label"])
        if m:
            paths[m.group(1)].append((int(m.group(2)), q["loc"], q["label"]))
        elif q["class"] in ("LBPatrolPoint", "LBSearchPoint", "LBWardenSpawnPoint") or q["label"].startswith(("Patrol_", "Search_")):
            ai.append((q["label"], q["loc"]))
    best_w = (1e9, None)
    for name, pts in paths.items():
        pts.sort()
        for (i, a, la), (j, b, lb) in zip(pts, pts[1:]):
            d = seg_dist(p, a, b)
            if d < best_w[0]:
                best_w = (d, "%s->%s" % (la, lb))
    best_a = (1e9, None)
    for lab, loc in ai:
        d = math.dist(p, loc)
        if d < best_a[0]:
            best_a = (d, lab)
    return {"walkpath_cm": round(best_w[0], 1), "walkpath_seg": best_w[1], "ai_point_cm": round(best_a[0], 1), "ai_point": best_a[1]}


def bp_chain(sv, class_ref):
    """Blueprint parent chain from a class path, e.g. [BP_PuzzleCandle, /Script/Engine.Actor]."""
    chain = []
    cur = class_ref
    for _ in range(10):
        if not cur:
            break
        if cur.startswith("/Script/"):
            chain.append(cur.rsplit(".", 1)[-1])
            break
        bp = class_to_bp(cur)
        chain.append(short(bp))
        par = sv.step("bpparent:" + bp, lambda bp=bp: R(sv.try_call("editor_toolset.toolsets.blueprint.BlueprintTools", "get_parent", {"blueprint": {"refPath": bp}}, bp)))
        cur = par
    return chain


@stage
def bp_actors(sv, inv, refs, SMA):
    """Every Blueprint-class actor in the level: class, parent chain, never-save flag, components with classes/meshes."""
    out = []
    bps = [r for r in refs if cls_of(r).startswith(("BP_", "BP")) and cls_of(r).endswith("_C")]
    for r in bps:
        def f(r=r):
            cl = R(sv.try_call(O, "get_class", {"instance": {"refPath": r}}, r))
            chain = bp_chain(sv, cl)
            comps = []
            for c in sv.components(r):
                cc = R(sv.try_call(O, "get_class", {"instance": {"refPath": c}}, c))
                rec = {"name": c.rsplit(".", 1)[-1], "class": short(cc)}
                if short(cc) in ("StaticMeshComponent", "InstancedStaticMeshComponent"):
                    p = sv.getp(c, ["staticMesh", "overrideMaterials", "relativeLocation", "bVisible"])
                    rec.update({"mesh": short(R(p.get("staticMesh"))), "mesh_ref": R(p.get("staticMesh")),
                                "ov": [short(R(o)) for o in (p.get("overrideMaterials") or [])],
                                "rel": p.get("relativeLocation"), "visible": p.get("bVisible")})
                comps.append(rec)
            ns = [c for c in chain if re.sub(r"_C$", "", c) in NEVER_SAVE]
            return {"ref": r, "label": sv.label(r), "class": cl, "chain": chain, "never_save_in_chain": ns, "components": comps,
                    "xf": sv.xform(r)}
        out.append(sv.step("bpactor:" + r, f))
    inv["bp_actors"] = out
    sv.log("bp actors: %d" % len(out))
    return out


@stage
def flames(sv, inv, refs, SMA, BPA):
    """Item 1."""
    flame_assets = ["/Game/LastBell/Environments/Props/Procedural/SM_LB_Prop_CandleFlame_A"]
    fa = sv.step("find:CandleFlame_asset", lambda: J(sv.call(AS, "find_assets", {"folder_path": "/Game/LastBell", "name": "CandleFlame"})))
    inv["flame_mesh_assets"] = fa
    refs_of = {}
    for a in fa:
        refs_of[a] = sv.step("referencers:" + a, lambda a=a: list(J(sv.try_call(AS, "get_referencers", {"asset_path": a}, a) or "[]") or []))
    inv["flame_mesh_referencers"] = refs_of
    cand = []
    for r, v in SMA.items():
        lab = v["label"] or ""
        mesh = v["mesh"] or ""
        if "flame" in mesh.lower() or "flame" in lab.lower() or lab.startswith("CD_Candles_") and lab.endswith("_Flame"):
            cand.append(r)
    sm_flames = []
    for r in cand:
        v = SMA[r]
        eff = sma_effective(sv, v, v["ov_ref"])
        pr = sv.getp(r + ".StaticMeshComponent0", ["bVisible", "castShadow", "bHiddenInGame", "mobility"])
        x = sv.xform(r)
        sm_flames.append({"ref": r, "label": v["label"], "mesh": v["mesh"], "loc": x["loc"] if x else None, "rot": x["rot"] if x else None,
                          "scale": x["scale"] if x else None, "area": area_of(*x["loc"]) if x else None, "slots": eff,
                          "visible": pr.get("bVisible"), "cast_shadow": pr.get("castShadow"), "mobility": pr.get("mobility"),
                          "owner": "StaticMeshActor (level instance; no Blueprint)",
                          "material_source": sorted({s["source"] for s in eff}), "never_save_bp": False})
    sm_flames.sort(key=lambda d: (d["area"] or "", d["label"] or ""))
    inv["flames_static_mesh_actors"] = sm_flames
    sv.log("flame mesh actors: %d" % len(sm_flames))
    # Blueprint flames: any BP actor with a component whose mesh or name mentions Flame
    bpf = []
    for a in BPA:
        for c in a["components"]:
            if "flame" in (c.get("name") or "").lower() or "flame" in (c.get("mesh") or "").lower():
                if c["class"] == "PointLightComponent":
                    continue
                bp = class_to_bp(a["class"])
                tmpl = None
                if bp:
                    tref = "%s_C:%s_GEN_VARIABLE" % (bp, c["name"])
                    tp = sv.getp(tref, ["staticMesh", "overrideMaterials", "relativeLocation", "relativeScale3D", "bVisible"])
                    tmpl = {"ref": tref, "mesh": short(R(tp.get("staticMesh"))), "ov": [short(R(o)) for o in (tp.get("overrideMaterials") or [])],
                            "rel": tp.get("relativeLocation"), "visible": tp.get("bVisible")}
                inst_ov = [o for o in (c.get("ov") or []) if o]
                tmpl_ov = [o for o in ((tmpl or {}).get("ov") or []) if o]
                slots = sv.mesh_slots(c["mesh_ref"]) if c.get("mesh_ref") else []
                eff = []
                for i, s in enumerate(slots):
                    io = c["ov"][i] if i < len(c.get("ov") or []) else None
                    to = tmpl["ov"][i] if tmpl and i < len(tmpl["ov"]) else None
                    if io:
                        eff.append({"slot": s["slot"], "material": io, "source": "placed instance override"})
                    elif to:
                        eff.append({"slot": s["slot"], "material": to, "source": "Blueprint component template override"})
                    else:
                        eff.append({"slot": s["slot"], "material": s["default"], "source": "mesh default"})
                bpf.append({"actor": a["label"], "actor_ref": a["ref"], "class": a["class"], "chain": a["chain"],
                            "never_save_in_chain": a["never_save_in_chain"], "component": c["name"], "mesh": c.get("mesh"),
                            "instance_rel_loc": c.get("rel"), "actor_loc": (a["xf"] or {}).get("loc"), "slots": eff, "template": tmpl,
                            "visible": c.get("visible")})
    inv["flames_blueprint_components"] = bpf
    sv.log("blueprint flame components: %d" % len(bpf))
    # Blueprint ASSETS that reference a flame mesh or MI (includes the player's candle, which is not a level actor)
    bp_assets = sorted({r for lst in refs_of.values() for r in lst if "/Blueprints/" in r})
    bpa_out = []
    for bpp in bp_assets:
        asset = "%s.%s" % (bpp, bpp.rsplit("/", 1)[-1])
        cdo = R(sv.try_call("editor_toolset.toolsets.blueprint.BlueprintTools", "get_default_object", {"blueprint": {"refPath": asset}}, asset))
        comps = []
        if cdo:
            for c in J(sv.try_call(A, "get_components", {"actor": {"refPath": cdo}}, cdo) or "[]") or []:
                cr = R(c)
                if not cr:
                    continue
                nm = cr.rsplit(":", 1)[-1]
                p = sv.getp(cr, ["staticMesh", "overrideMaterials", "relativeLocation", "relativeScale3D", "bVisible", "castShadow"])
                if not p:
                    continue
                ov = [short(R(o)) for o in (p.get("overrideMaterials") or [])]
                if "flame" in nm.lower() or "MI_LB_CandleFlame" in ov or "flame" in (short(R(p.get("staticMesh"))) or "").lower():
                    comps.append({"component": nm, "ref": cr, "mesh": short(R(p.get("staticMesh"))), "ov": ov, "rel_loc": p.get("relativeLocation"),
                                  "rel_scale": p.get("relativeScale3D"), "visible": p.get("bVisible"), "cast_shadow": p.get("castShadow")})
        par = sv.try_call("editor_toolset.toolsets.blueprint.BlueprintTools", "get_parent", {"blueprint": {"refPath": asset}}, asset)
        bpa_out.append({"blueprint": bpp, "parent": R(par), "never_save": short(bpp) in NEVER_SAVE, "flame_components": comps})
    inv["flames_blueprint_assets"] = bpa_out
    mi = "/Game/LastBell/Materials/Instances/MI_LB_CandleFlame.MI_LB_CandleFlame"
    p = sv.getp(mi, ["parent", "scalarParameterValues", "vectorParameterValues", "textureParameterValues", "blendMode", "twoSided"])
    inv["mi_lb_candleflame"] = {"path": mi, "parent": R(p.get("parent")), "scalars": {e["parameterInfo"]["name"]: e["parameterValue"] for e in p.get("scalarParameterValues") or []},
                                "vectors": {e["parameterInfo"]["name"]: e["parameterValue"] for e in p.get("vectorParameterValues") or []},
                                "textures": {e["parameterInfo"]["name"]: short(R(e["parameterValue"])) for e in p.get("textureParameterValues") or []}}
    sv.log("flame blueprint assets: %d" % len(bpa_out))
    # other candle props without a flame mesh
    candles = defaultdict(list)
    for r, v in SMA.items():
        lab, mesh = v["label"] or "", v["mesh"] or ""
        if ("candle" in mesh.lower() or "candle" in lab.lower() or "taper" in mesh.lower() or "taper" in lab.lower()) and "flame" not in mesh.lower() and "flame" not in lab.lower():
            candles[mesh].append(r)
    flames_loc = [f["loc"] for f in sm_flames if f["loc"]]
    others = []
    for mesh, rs in candles.items():
        recs = []
        for r in rs:
            x = sv.xform(r)
            if not x:
                continue
            d = min((math.dist(x["loc"], fl) for fl in flames_loc), default=None)
            recs.append({"label": SMA[r]["label"], "loc": x["loc"], "nearest_flame_cm": round(d, 1) if d is not None else None})
        others.append({"mesh": mesh, "count": len(recs), "with_flame_within_40cm": sum(1 for q in recs if q["nearest_flame_cm"] is not None and q["nearest_flame_cm"] <= 40),
                       "items": recs})
    inv["candle_props"] = sorted(others, key=lambda d: -d["count"])
    sv.log("candle prop families: %d" % len(others))


@stage
def fires(sv, inv, refs, SMA, BPA):
    """Item 2."""
    lights = {}
    for lab in LIGHT_LABELS:
        hits = _find_exact(sv, lab)
        lights[lab] = {"found": len(hits), "ref": hits[0] if hits else None, "xf": sv.xform(hits[0]) if hits else None}
    inv["fire_lights"] = lights
    fx = []
    cand = [r for r in refs if cls_of(r) in ("Emitter", "NiagaraActor", "ParticleEventManager") or "Emitter" in cls_of(r) or "Niagara" in cls_of(r)]
    for r in cand:
        def f(r=r):
            cl = R(sv.try_call(O, "get_class", {"instance": {"refPath": r}}, r))
            comps = []
            for c in sv.components(r):
                cc = short(R(sv.try_call(O, "get_class", {"instance": {"refPath": c}}, c)))
                rec = {"name": c.rsplit(".", 1)[-1], "class": cc}
                if cc in ("ParticleSystemComponent", "NiagaraComponent"):
                    rec.update(sv.getp(c, ["template", "asset", "bAutoActivate", "bAutoDestroy", "relativeLocation", "relativeRotation",
                                           "relativeScale3D", "bVisible", "bHiddenInGame"]))
                    for k in ("template", "asset"):
                        if k in rec:
                            rec[k] = R(rec[k])
                comps.append(rec)
            return {"ref": r, "label": sv.label(r), "class": cl, "chain": bp_chain(sv, cl), "xf": sv.xform(r), "components": comps,
                    "tags": sv.getp(r, ["tags"]).get("tags")}
        fx.append(sv.step("fire:" + r, f))
    # Blueprint actors with particle components
    for a in BPA:
        for c in a["components"]:
            if c["class"] in ("ParticleSystemComponent", "NiagaraComponent"):
                fx.append({"ref": a["ref"], "label": a["label"], "class": a["class"], "chain": a["chain"], "xf": a["xf"],
                           "components": [c], "never_save_in_chain": a["never_save_in_chain"]})
    for rec in fx:
        loc = (rec["xf"] or {}).get("loc")
        rec["area"] = area_of(*loc) if loc else None
        best = []
        for lab, L in lights.items():
            if L["xf"] and loc:
                best.append((math.dist(loc, L["xf"]["loc"]), lab))
        best.sort()
        rec["nearest_lights"] = [{"light": lab, "dist_cm": round(d, 1)} for d, lab in best[:3]]
        rec["match"] = best[0][1] if best and best[0][0] <= 200 else None
    inv["fire_actors"] = fx
    # asset-level view: who references the Cascade fire templates
    tmpl = sorted({c["template"] for rec in fx for c in rec["components"] if c.get("template")})
    inv["fire_templates"] = {t: sv.step("referencers:" + t.rsplit(".", 1)[0], lambda t=t: list(J(sv.try_call(AS, "get_referencers", {"asset_path": t.rsplit(".", 1)[0]}, t) or "[]") or [])) for t in tmpl}
    sv.log("fire actors: %d" % len(fx))


VIEWPOINTS = os.path.join(ROOT, "Tools", "lighting", "poses", "p14_viewpoints.json")


def _mesh_local_bounds(sv, mref):
    b = sv.mesh_bounds(mref)
    if not b:
        return None
    return {"min": [b["min"][k] for k in "xyz"], "max": [b["max"][k] for k in "xyz"]}


@stage
def sky(sv, inv, refs, SMA):
    """Item 11: the sky dome, the fog, and SkyBoltDistance."""
    dome = [r for r, v in SMA.items() if v["mesh"] == "SM_SkySphere" or (v["label"] or "") == "SkySphere"]
    out = {"dome_actors": []}
    for r in dome:
        v = SMA[r]
        x = sv.xform(r)
        lb = _mesh_local_bounds(sv, v["mesh_ref"])
        half = max((lb["max"][i] - lb["min"][i]) / 2 for i in range(3))
        radius = half * max(x["scale"])
        out["dome_actors"].append({"ref": r, "label": v["label"], "class": cls_of(r), "mesh": v["mesh"], "mesh_ref": v["mesh_ref"], "mi": v["ov"],
                                   "loc": x["loc"], "rot": x["rot"], "scale": x["scale"], "mesh_local_bounds": lb,
                                   "radius_cm": radius, "props": sv.getp(r + ".StaticMeshComponent0", ["castShadow", "bVisible", "bAffectDynamicIndirectLighting"])})
    fog_refs = [r for r in refs if cls_of(r) == "ExponentialHeightFog"]
    out["fog"] = []
    for r in fog_refs:
        comp = r + ".HeightFogComponent0"
        p = sv.getp(comp, ["fogDensity", "fogHeightFalloff", "fogMaxOpacity", "startDistance", "fogCutoffDistance", "fogInscatteringLuminance",
                           "inscatteringColorCubemap", "directionalInscatteringLuminance", "directionalInscatteringExponent",
                           "bEnableVolumetricFog", "volumetricFogDistance", "volumetricFogExtinctionScale", "volumetricFogScatteringDistribution",
                           "volumetricFogAlbedo", "volumetricFogEmissive", "volumetricFogStartDistance", "volumetricFogNearFadeInDistance",
                           "skyAtmosphereAmbientContributionColorScale", "fogInscatteringColor", "bVisible"])
        out["fog"].append({"ref": r, "label": sv.label(r), "xf": sv.xform(r), "props": p})
    out["local_fog_volumes"] = len([r for r in refs if cls_of(r) == "LocalFogVolume"])
    # SkyBoltDistance
    vp = json.load(open(VIEWPOINTS, encoding="utf-8"))
    radius = out["dome_actors"][0]["radius_cm"] if out["dome_actors"] else None
    centre = out["dome_actors"][0]["loc"] if out["dome_actors"] else [0, 0, 0]
    if radius:
        cap = 60000.0
        prop = min(0.6 * radius, cap)
        worst = 0.0
        for name, pose in vp.items():
            cam = pose[:3]
            for k in range(16):
                a = math.radians(k * 22.5)
                top = [cam[0] + math.cos(a) * prop, cam[1] + math.sin(a) * prop, cam[2] + 22000.0]
                worst = max(worst, math.dist(top, centre))
        out["sky_bolt"] = {"radius_cm": radius, "dome_centre": centre, "rule": "0.6 x radius, capped at 60000", "proposed_distance_cm": prop,
                           "top_height_cm": 22000, "bolt_length_cm": [16000, 26000],
                           "worst_top_point_to_centre_cm": round(worst), "inside_dome_for_all_16_viewpoints_x16_directions": worst < radius,
                           "margin_cm": round(radius - worst)}
        # fog optical depth to the bolt (estimate; UE divides the density and the falloff by 1000 internally)
        f = out["fog"][0]["props"] if out["fog"] else {}
        if f.get("fogDensity") is not None:
            dens = float(f["fogDensity"]) / 1000.0
            fall = max(float(f.get("fogHeightFalloff") or 0), 0.001) / 1000.0
            fz = (out["fog"][0]["xf"] or {}).get("loc", [0, 0, 0])[2]
            t = {}
            for cam_z in (170.0, 2670.0):
                for dist in (3000.0, 20000.0, 60000.0):
                    # integrate density along a ray rising to the bolt's mid height (cam_z + 11000) over horizontal distance dist
                    n = 400
                    z1 = cam_z + 11000.0
                    od = 0.0
                    L = math.hypot(dist, z1 - cam_z)
                    for i in range(n):
                        s = (i + 0.5) / n
                        zz = cam_z + (z1 - cam_z) * s
                        od += dens * 2.0 ** (-fall * (zz - fz)) * (L / n)
                    mo = float(f.get("fogMaxOpacity") if f.get("fogMaxOpacity") is not None else 1.0)
                    tr = max(1.0 - mo, math.exp(-od))
                    t["cam_z%d_dist%d" % (cam_z, dist)] = {"optical_depth": round(od, 4), "transmittance": round(tr, 3)}
            out["fog_estimate"] = {"note": "estimate: density/1000, falloff/1000, exp2 height falloff, ray rising to the bolt mid height; start distance and cutoff ignored; real fog also adds inscattering",
                                   "start_distance": f.get("startDistance"), "cutoff": f.get("fogCutoffDistance"), "samples": t}
    inv["sky"] = out
    sv.log("sky: %s" % json.dumps(out.get("sky_bolt"))[:200])


@stage
def dfsettings(sv, inv, refs, SMA):
    """Item 13 (project side): renderer settings and the distance-field / Lumen / Niagara console variables."""
    res = {}
    names = J(sv.call(O, "list_properties", {"instance": {"refPath": "/Script/Engine.Default__RendererSettings"}}))
    nm = [x if isinstance(x, str) else x.get("name") for x in names]
    want = [n for n in nm if re.search(r"(?i)distance|sdf|lumen|raytrac|nanite|globalillum|dynamicGlobal|reflections|generateMesh", n)]
    res["renderer_settings"] = sv.getp("/Script/Engine.Default__RendererSettings", want)
    cv = {}
    for pat in ["r.GenerateMeshDistanceFields", "r.DistanceFields.", "r.DistanceFieldAO", "r.Lumen.TraceMeshSDFs", "r.Lumen.HardwareRayTracing", "r.Lumen.DiffuseIndirect.Allow",
                "r.Lumen.Reflections.Allow", "r.RayTracing", "r.AOGlobalDistanceField", "r.GlobalDistanceField", "r.LumenScene.GlobalSDF", "fx.Niagara.GpuSimulation",
                "fx.NiagaraAllowGPUParticles", "fx.Niagara.DistanceField", "fx.Niagara.NiagaraDistanceFieldCollision", "fx.Niagara.GlobalDistanceField", "fx.Niagara.Collision"]:
        r = sv.try_call(E, "SearchCVars", {"name": pat}, pat)
        r = J(r) if r else {}
        if isinstance(r, dict):
            for k, v in r.items():
                cv[k] = v.get("value") if isinstance(v, dict) else v
    res["cvars"] = cv
    # a sample of the project's own distance-field relevant per-mesh state is read in the roofs stage
    inv["distance_fields_project"] = res
    sv.log("renderer settings: %s" % json.dumps({k: res["renderer_settings"].get(k) for k in ("bGenerateMeshDistanceFields", "dynamicGlobalIllumination", "reflections", "bUseHardwareRayTracingForLumen", "lumenSoftwareTracingMode")}))


def _sma_where(SMA, pred):
    return [r for r, v in SMA.items() if pred(v)]


@stage
def water(sv, inv, refs, SMA):
    """Item 6."""
    hits = _sma_where(SMA, lambda v: any((o or "").startswith(("MI_Crypt_Water", "M_LB_Water")) or "water" in (o or "").lower() for o in v["ov"])
                      or "water" in (v["label"] or "").lower() or "water" in (v["mesh"] or "").lower())
    out = []
    for r in hits:
        v = SMA[r]
        x = sv.xform(r)
        b = sv.bounds(r)
        out.append({"ref": r, "label": v["label"], "mesh": v["mesh"], "mi": v["ov"], "loc": x["loc"] if x else None, "rot": x["rot"] if x else None,
                    "scale": x["scale"] if x else None, "bounds": b, "surface_z": b["max"][2] if b else None,
                    "props": sv.getp(r + ".StaticMeshComponent0", ["bVisible", "castShadow"]),
                    "mi_params": {o: sv.step("miw:" + o, lambda o=o: _mi_summary(sv, v, o)) for o in v["ov"] if o and o.startswith("MI_Crypt_Water")}})
    inv["water"] = sorted(out, key=lambda d: d["label"] or "")
    sv.log("water actors: %d" % len(out))


def _mi_summary(sv, v, name):
    ref = next((q for q in v["ov_ref"] if q and short(q) == name), None)
    if not ref:
        return None
    p = sv.getp(ref, ["parent", "scalarParameterValues"])
    return {"parent": short(R(p.get("parent"))), "scalars": {e["parameterInfo"]["name"]: e["parameterValue"] for e in p.get("scalarParameterValues") or []}}


@stage
def shafts(sv, inv, refs, SMA):
    """Item 5."""
    hits = _sma_where(SMA, lambda v: any((o or "").startswith("MI_LightShaft") for o in v["ov"]) or "lightshaft" in (v["mesh"] or "").lower()
                      or (v["label"] or "").startswith(("Ch_Shaft", "SA_")))
    out = []
    moon = _find_exact(sv, "Light_Chapel_Moon_S2")
    mrot = sv.xform(moon[0])["rot"] if moon else [-38.0, 35.0, 0.0]
    mdir = rot_axes(*mrot)[0]
    for r in hits:
        v = SMA[r]
        x = sv.xform(r)
        b = sv.bounds(r)
        lb = _mesh_local_bounds(sv, v["mesh_ref"]) if v["mesh_ref"] else None
        rec = {"ref": r, "label": v["label"], "mesh": v["mesh"], "mi": v["ov"], "loc": x["loc"], "rot": x["rot"], "scale": x["scale"], "bounds": b,
               "mesh_local_bounds": lb, "props": sv.getp(r + ".StaticMeshComponent0", ["castShadow", "bVisible", "collisionEnabled"])}
        if lb:
            s = x["scale"]
            half = [(lb["max"][i] - lb["min"][i]) / 2 * abs(s[i]) for i in range(3)]
            cl = [(lb["max"][i] + lb["min"][i]) / 2 for i in range(3)]
            rec["oriented_box"] = {"centre": local_to_world(x, cl), "rotation_pyr": x["rot"], "half_extent_local_axes": [round(h, 1) for h in half]}
            long_ax = max(range(3), key=lambda i: half[i])
            fac = [0.55, 0.55, 0.55]
            fac[long_ax] = 0.8
            rec["proposed_dust_box"] = {"centre": rec["oriented_box"]["centre"], "rotation_pyr": x["rot"],
                                        "half_extent_local_axes": [round(half[i] * fac[i], 1) for i in range(3)],
                                        "rule": "0.55 x the shaft box half-extent across the beam, 0.8 x along its longest axis"}
        lab = v["label"] or ""
        if lab.startswith("Ch_Shaft_S") or lab == "Ch_Shaft_Roof":
            # the lancet/roof-hole cards are axis-aligned prisms along the moon direction: fit an oriented box along it instead of the AABB
            if lab == "Ch_Shaft_Roof":
                start, length, half = x["loc"], 2400.0, None
                centre = [start[i] + mdir[i] * 1200 for i in range(3)]
                half = [600.0, 120.0, 120.0]
                how = "hole top (the card pivot) + 1200 cm along the moon direction; half-extent 600 along the beam, 120 across (the hole is about 500 x 450 cm)"
            else:
                c0 = [x["loc"][0], x["loc"][1], x["loc"][2] + 280.0]
                length = c0[2] / max(-mdir[2], 1e-3)
                centre = [c0[i] + mdir[i] * 0.5 * length for i in range(3)]
                half = [round(0.4 * length, 1), 30.0, 180.0]
                how = ("window glass centre (card pivot + 280 up) to the floor along the moon direction, length %.0f cm; half-extent 0.4 x length along the beam, 30 wide, 180 tall "
                       "(a 140 x 560 lancet seen along the beam is about 80 x 440 across)" % length)
            rec["proposed_dust_box"] = {"centre": [round(q, 1) for q in centre], "rotation_pyr": mrot, "half_extent_local_axes": half, "rule": how,
                                        "beam_dir": [round(q, 4) for q in mdir]}
        out.append(rec)
    inv["shafts"] = sorted(out, key=lambda d: d["label"] or "")
    lt = {}
    for lab in ["L_Crypt_Moon_G1", "L_Crypt_Moon_G2", "L_Crypt_Moon_G3", "L_Tw_MoonSlit_F03", "L_Tw_MoonSlit_F07", "L_Tw_MoonSlit_F08",
                "Light_Chapel_Moon_S1", "Light_Chapel_Moon_S2", "Light_Chapel_Moon_S3", "Light_Chapel_Moon_Roof"]:
        hh = _find_exact(sv, lab)
        lt[lab] = {"ref": hh[0], "xf": sv.xform(hh[0])} if hh else None
    inv["shaft_lights"] = lt
    # nearest shaft card to each light
    near = {}
    for lab, L in lt.items():
        if L and L["xf"]:
            best = sorted((math.dist(L["xf"]["loc"], s["loc"]), s["label"]) for s in out)[:2]
            near[lab] = [{"shaft": n, "dist_cm": round(d, 1)} for d, n in best]
    inv["shaft_nearest_to_lights"] = near
    sv.log("shafts: %d" % len(out))


@stage
def tower_top(sv, inv, refs, SMA):
    """Item 4: highest geometry within X 11990-13010, Y 1490-2510."""
    box = (11990, 13010, 1490, 2510)
    cand = [r for r, v in SMA.items() if re.match(r"^(TW|Tw|Belfry|Bell)", v["label"] or "") or "Tw_" in (v["mesh"] or "") or "Tower" in (v["label"] or "")]
    rows = []
    for r in cand:
        b = sv.bounds(r)
        if not b:
            continue
        if b["max"][0] < box[0] or b["min"][0] > box[1] or b["max"][1] < box[2] or b["min"][1] > box[3]:
            continue
        v = SMA[r]
        pr = sv.getp(r + ".StaticMeshComponent0", ["bVisible", "collisionEnabled"])
        bi = sv.getp(r + ".StaticMeshComponent0", ["bodyInstance"]).get("bodyInstance") or {}
        rows.append({"ref": r, "label": v["label"], "mesh": v["mesh"], "bounds": b, "max_z": b["max"][2], "visible": pr.get("bVisible"),
                     "collision_profile": bi.get("collisionProfileName"), "bUseDefaultCollision": bi.get("bUseDefaultCollision")})
    rows.sort(key=lambda d: -d["max_z"])
    out = {"candidates_considered": len(cand), "in_box": len(rows), "top10": rows[:10]}
    traces = {}
    for (x, y) in [(12500, 2000), (12100, 1600), (12900, 2400), (12530.8, 2000)]:
        d = sv.trace([x, y, 8000], [x, y, 0])
        traces["%.1f,%.1f" % (x, y)] = round(8000 - d, 1) if d is not None else None
    out["vertical_trace_top_z"] = traces
    roof = next((q for q in rows if q["label"] == "TWA_Roof"), None)
    if roof:
        x = sv.xform(roof["ref"])
        lb = _mesh_local_bounds(sv, SMA[roof["ref"]]["mesh_ref"])
        out["roof"] = {"label": "TWA_Roof", "loc": x["loc"], "mesh": roof["mesh"], "mesh_local_bounds": lb,
                       "bounds_max_z": roof["max_z"], "apex_world_z": x["loc"][2] + 1200,
                       "note": "plan: pyramid apex local z 1200 (world 4740), cross finial 90 tall bent 20 deg toward +X from the apex; local max z 1284.8"}
        tip = [round(x["loc"][0] + 90 * math.sin(math.radians(20)), 1), x["loc"][1], round(roof["max_z"], 1)]
        out["finial_tip_estimate"] = tip
        out["proposed_FX_StrikeTarget_Tower"] = [tip[0], tip[1], round(tip[2] + 20, 1)]
        cam = [600, 0, 170]
        tgt = out["proposed_FX_StrikeTarget_Tower"]
        d = sv.trace(cam, tgt)
        full = math.dist(cam, tgt)
        out["los_from_p14_tower_reveal_pose"] = {"trace_dist": d, "full_dist": round(full, 1), "clear": d is None or d >= full - 1,
                                                  "pitch_deg": round(math.degrees(math.atan2(tgt[2] - cam[2], math.hypot(tgt[0] - cam[0], tgt[1] - cam[1]))), 2),
                                                  "yaw_deg": round(math.degrees(math.atan2(tgt[1] - cam[1], tgt[0] - cam[0])), 2)}
    inv["tower_top"] = out
    sv.log("tower top: %s" % json.dumps(out.get("proposed_FX_StrikeTarget_Tower")))


ROOF_RE = re.compile(r"(?i)roof|plank|rafter|purlin|vault|truss|ridge|gable|ceiling|canopy|lean|wallplate|wall_plate")
ROOF_MESH_RE = re.compile(r"(?i)roof|plank|lean|vault|rafter|purlin|truss|slate")
SURFACE_RE = re.compile(r"(?i)roofplanks|roofslab|leanto|stairhouseroof|roof_brokensw|sm_roof$|vault_barrel")
FAM = lambda lab: re.sub(r"_+$", "", re.sub(r"\d+", "#", lab or ""))  # noqa: E731


def _body(sv, ref):
    bi = sv.getp(ref + ".StaticMeshComponent0", ["bodyInstance"]).get("bodyInstance") or {}
    p = sv.getp(ref + ".StaticMeshComponent0", ["collisionEnabled", "bVisible", "castShadow"])
    return {"profile": bi.get("collisionProfileName"), "useDefault": bi.get("bUseDefaultCollision"),
            "collisionEnabled": bi.get("collisionEnabled") or p.get("collisionEnabled"), "visible": p.get("bVisible"), "castShadow": p.get("castShadow")}


@stage
def roofs(sv, inv, refs, SMA):
    """Item 3: roof meshes, thickness, collision, plus a vertical trace test per surface piece."""
    sel = [r for r, v in SMA.items() if ROOF_RE.search(v["label"] or "") or ROOF_MESH_RE.search(v["mesh"] or "")]
    sel = [r for r in sel if not re.match(r"(?i)^(KW_|KC_|KG_|KA_|Perim|Stair_|Rail_|KD_)", SMA[r]["label"] or "")]
    pieces = []
    for r in sel:
        v = SMA[r]
        x = sv.xform(r)
        b = sv.bounds(r)
        lb = _mesh_local_bounds(sv, v["mesh_ref"]) if v["mesh_ref"] else None
        dims = None
        if lb and x:
            dims = sorted(round((lb["max"][i] - lb["min"][i]) * abs(x["scale"][i]), 1) for i in range(3))
        loc = x["loc"] if x else None
        piece = {"ref": r, "label": v["label"], "mesh": v["mesh"], "mi": v["ov"], "area": area_of(*loc) if loc else None, "loc": loc,
                 "rot": x["rot"] if x else None, "scale": x["scale"] if x else None, "bounds": b,
                 "world_z_extent": round(b["max"][2] - b["min"][2], 1) if b else None, "mesh_local_bounds": lb,
                 "dims_cm": dims, "thickness_cm": dims[0] if dims else None, "surface": bool(SURFACE_RE.search(v["mesh"] or "") or SURFACE_RE.search(v["label"] or "")),
                 "collision": _body(sv, r)}
        pieces.append(piece)
    # vertical trace test on every surface piece: does a trace from above stop on the piece?
    for p in pieces:
        if p["surface"] and p["bounds"]:
            cx = (p["bounds"]["min"][0] + p["bounds"]["max"][0]) / 2
            cy = (p["bounds"]["min"][1] + p["bounds"]["max"][1]) / 2
            top = p["bounds"]["max"][2]
            d = sv.trace([cx, cy, top + 300], [cx, cy, top - 3000])
            hit = None if d is None else round(top + 300 - d, 1)
            p["trace_test"] = {"xy": [round(cx), round(cy)], "hit_z": hit, "piece_top_z": round(top, 1),
                               "stops_on_piece": hit is not None and hit >= p["bounds"]["min"][2] - 3}
    # per-mesh distance-field state
    meshes = sorted({p["mesh_ref"] for p in [dict(mesh_ref=SMA[q["ref"]]["mesh_ref"]) for q in pieces if q["surface"]] if p["mesh_ref"]})
    dfprops = None
    mesh_df = {}
    for m in meshes:
        if dfprops is None:
            nm = [x if isinstance(x, str) else x.get("name") for x in J(sv.call(O, "list_properties", {"instance": {"refPath": m}}))]
            dfprops = [n for n in nm if re.search(r"(?i)distance|sdf|nanite", n)]
        def _df(m=m):
            raw = sv.getp(m, dfprops)
            ns = raw.get("naniteSettings") or {}
            return {"bGenerateMeshDistanceField": raw.get("bGenerateMeshDistanceField"), "distanceFieldSelfShadowBias": raw.get("distanceFieldSelfShadowBias"),
                    "nanite_enabled": ns.get("bEnabled"), "nanite_bVoxelNDF": ns.get("bVoxelNDF")}
        mesh_df[m] = sv.step("meshdfc:" + m, _df)
    inv["roof_pieces"] = pieces
    inv["roof_mesh_distance_field"] = {"properties_read": dfprops, "meshes": mesh_df}
    fams = defaultdict(list)
    for p in pieces:
        fams[(p["area"], FAM(p["label"]))].append(p)
    out = []
    for (area, fam), ps in sorted(fams.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        bs = [p["bounds"] for p in ps if p["bounds"]]
        th = [p["thickness_cm"] for p in ps if p["thickness_cm"] is not None]
        zext = [p["world_z_extent"] for p in ps if p["world_z_extent"] is not None]
        out.append({"area": area, "family": fam, "count": len(ps), "meshes": sorted({p["mesh"] for p in ps if p["mesh"]}), "surface": any(p["surface"] for p in ps),
                    "thickness_cm": [min(th), max(th)] if th else None, "world_z_extent_cm": [min(zext), max(zext)] if zext else None,
                    "union_min": [round(min(b["min"][i] for b in bs), 1) for i in range(3)] if bs else None,
                    "union_max": [round(max(b["max"][i] for b in bs), 1) for i in range(3)] if bs else None,
                    "collision_profiles": dict(Counter(str(p["collision"].get("profile")) for p in ps)),
                    "collision_enabled": dict(Counter(str(p["collision"].get("collisionEnabled")) for p in ps)),
                    "visible": dict(Counter(str(p["collision"].get("visible")) for p in ps)),
                    "trace_stops_on_piece": dict(Counter(str(p["trace_test"]["stops_on_piece"]) for p in ps if "trace_test" in p))})
    inv["roof_families"] = out
    sv.log("roof pieces: %d in %d families" % (len(pieces), len(out)))


def _cover(planks, x0, x1, y0, y1, cell=25.0):
    """Uncovered rectangles of [x0,x1]x[y0,y1] given plank AABBs (xy), on a grid; row-merged."""
    nx, ny = int(round((x1 - x0) / cell)), int(round((y1 - y0) / cell))
    grid = [[False] * nx for _ in range(ny)]
    for b in planks:
        for j in range(ny):
            cy = y0 + (j + 0.5) * cell
            if not (b["min"][1] <= cy <= b["max"][1]):
                continue
            for i in range(nx):
                cx = x0 + (i + 0.5) * cell
                if b["min"][0] <= cx <= b["max"][0]:
                    grid[j][i] = True
    covered = sum(sum(1 for c in row if c) for row in grid)
    # greedy rectangles of uncovered cells
    seen = [[False] * nx for _ in range(ny)]
    rects = []
    for j in range(ny):
        for i in range(nx):
            if grid[j][i] or seen[j][i]:
                continue
            i2 = i
            while i2 + 1 < nx and not grid[j][i2 + 1] and not seen[j][i2 + 1]:
                i2 += 1
            j2 = j
            while j2 + 1 < ny and all((not grid[j2 + 1][k]) and not seen[j2 + 1][k] for k in range(i, i2 + 1)):
                j2 += 1
            for jj in range(j, j2 + 1):
                for ii in range(i, i2 + 1):
                    seen[jj][ii] = True
            rects.append([round(x0 + i * cell), round(y0 + j * cell), round(x0 + (i2 + 1) * cell), round(y0 + (j2 + 1) * cell)])
    rects.sort(key=lambda r: -((r[2] - r[0]) * (r[3] - r[1])))
    return {"covered_fraction": round(covered / (nx * ny), 3), "uncovered_rects_xyxy": rects[:12], "n_rects": len(rects)}


@stage
def openings(sv, inv, refs, SMA):
    """Item 3: every roof opening where sky is visible from inside, with XY bounds and Z."""
    pieces = {p["label"]: p for p in inv["roof_pieces"]}
    out = {}
    # (a) courtyard covered walks: gaps between the roof planks
    for tag, label_prefix, (x0, x1, y0, y1) in (("courtyard_north_walk", "Roof_N_Planks", (2000, 3000, 980, 1300)),
                                                ("courtyard_south_walk", "Roof_S_Planks", (4000, 5000, -1350, -920))):
        planks = [p["bounds"] for p in inv["roof_pieces"] if (p["label"] or "").startswith(label_prefix) and p["bounds"]]
        zs = [(b["min"][2], b["max"][2]) for b in planks]
        rec = _cover(planks, x0, x1, y0, y1)
        rec.update({"walk_rect_xyxy": [x0, y0, x1, y1], "planks": len(planks), "plank_z_range": [round(min(z[0] for z in zs), 1), round(max(z[1] for z in zs), 1)] if zs else None,
                    "note": "uncovered = sky visible from the walk (rafters are 15 x 10 cm and ignored)"})
        out[tag] = rec
    # (b) the chapel roof hole: the local hole box of Ch_Roof_S1 (plan P8: x 250..750, slope 300..1000 in the slab's local frame)
    s1 = pieces.get("Ch_Roof_S1")
    if s1:
        x = {"loc": s1["loc"], "rot": s1["rot"], "scale": s1["scale"]}
        corners = [local_to_world(x, (lx, ly, 0)) for lx in (250, 750) for ly in (300, 1000)]
        out["chapel_roof_hole"] = {"slab": "Ch_Roof_S1", "mesh": s1["mesh"], "slab_transform": x,
                                   "hole_local_box": "x 250..750, slope y 300..1000 (P8 plan, ragged)",
                                   "corners_world": corners,
                                   "xy_bounds": [round(min(c[0] for c in corners)), round(min(c[1] for c in corners)), round(max(c[0] for c in corners)), round(max(c[1] for c in corners))],
                                   "z_range": [round(min(c[2] for c in corners)), round(max(c[2] for c in corners))]}
    sh = next((s for s in inv.get("shafts", []) if s["label"] == "Ch_Shaft_Roof"), None)
    if sh:
        out.setdefault("chapel_roof_hole", {})["shaft_card_bounds"] = sh["bounds"]
    # (c) cloister north walk: roof panel CLA_Roof_N_2 (hole panel) and the broken vault bay CLA_Vault_N_E
    n2 = pieces.get("CLA_Roof_N_2")
    if n2:
        x = {"loc": n2["loc"], "rot": n2["rot"], "scale": n2["scale"]}
        corners = [local_to_world(x, (lx, ly, 0)) for lx in (150, 850) for ly in (0, 800)]
        out["cloister_north_roof_hole"] = {"panel": "CLA_Roof_N_2", "mesh": n2["mesh"], "panel_transform": x,
                                           "hole_local_box": "x 150..850, slope y 0..800 (P10 plan, broken battens)", "corners_world": corners,
                                           "xy_bounds": [round(min(c[0] for c in corners)), round(min(c[1] for c in corners)), round(max(c[0] for c in corners)), round(max(c[1] for c in corners))],
                                           "z_range": [round(min(c[2] for c in corners)), round(max(c[2] for c in corners))]}
    v = pieces.get("CLA_Vault_N_E")
    if v:
        out["cloister_north_vault_hole"] = {"vault": "CLA_Vault_N_E", "bounds": v["bounds"], "loc": v["loc"],
                                            "note": "P10: hole x 50..600 along the walk from X 10850 = X 10900..11450; the roof hole X 10853..11287 overlaps it by 387 cm; the open sky column is the overlap in X and the walk width in Y"}
    # (d) tower roof: the collapsed SW quarter
    tr = pieces.get("TWA_Roof")
    if tr:
        x = {"loc": tr["loc"], "rot": tr["rot"], "scale": tr["scale"]}
        corners = [local_to_world(x, (lx, ly, lz)) for lx in (-525, -100) for ly in (-525, -100) for lz in (-10, 860)]
        out["tower_roof_sw_collapse"] = {"roof": "TWA_Roof", "mesh": tr["mesh"], "roof_transform": x,
                                         "missing_local_box": "x -525..-100, y -525..-100, up to local z 860 (P10 plan)", "corners_world": corners,
                                         "xy_bounds": [round(min(c[0] for c in corners)), round(min(c[1] for c in corners)), round(max(c[0] for c in corners)), round(max(c[1] for c in corners))],
                                         "z_range": [round(min(c[2] for c in corners)), round(max(c[2] for c in corners))]}
    # (e) open to the sky by design
    out["open_by_design"] = {
        "cloister_garth": "X 10247..11462, Y 1344..2261 (P14 SZN_Garth box), no roof",
        "shortcut_passage": "X 6040..9460, Y 1700..2300, no roof (P10: 'with no roof, the lane is 6 m wide')",
        "courtyard": "X 300..6000, Y -2500..2500 apart from the two covered walks and the chapel front",
        "approach": "X < 300",
    }
    # (f) crypt grates: is there open sky above them?
    gr = {}
    for lab, (gx, gy) in (("G1", (8250, -2247.5)), ("G2", (9750, -2280)), ("G3", (11050, -1625))):
        d = sv.trace([gx, gy, 6000], [gx, gy, -700])
        gr[lab] = {"xy": [gx, gy], "first_hit_z_from_above": None if d is None else round(6000 - d, 1)}
    out["crypt_grates"] = {"traces": gr, "note": "a hit near Z 0 means a ground slab covers the grate; the sky disc under the grate is a rendered plane"}
    inv["openings"] = out
    sv.log("openings: %s" % list(out.keys()))


EAVE_PANELS = {"S": ("CLA_Roof_S_1", (0, 0, 0), (1000, 0, 0), (0, 1)), "N_1": ("CLA_Roof_N_1", (0, 0, 0), (1000, 0, 0), (0, -1)),
               "N_2": ("CLA_Roof_N_2", (0, 0, 0), (1000, 0, 0), (0, -1)), "W": ("CLA_Roof_W_1", (0, 0, 0), (1000, 0, 0), (1, 0)),
               "E": ("CLA_Roof_E_1", (0, 0, 0), (1000, 0, 0), (-1, 0))}


@stage
def eaves(sv, inv, refs, SMA):
    """Item 8: courtyard walk eaves verified against the roof meshes, and every cloister walk eave line."""
    out = {"courtyard": {}, "cloister": []}
    for tag, pre, claim in (("north", "Roof_N", {"x": [2000, 3000], "y": 1300, "z": 420}), ("south", "Roof_S", {"x": [4000, 5000], "y": -1350, "z": 420})):
        items = [p for p in inv["roof_pieces"] if (p["label"] or "").startswith(pre)]
        purlin = next((p for p in items if (p["label"] or "").endswith("Purlin")), None)
        posts = [p for p in items if "_Post" in (p["label"] or "")]
        planks = [p for p in items if "Planks" in (p["label"] or "") and p["bounds"]]
        rec = {"claim": claim, "purlin": {"label": purlin["label"], "bounds": purlin["bounds"], "loc": purlin["loc"]} if purlin else None,
               "posts": [{"label": q["label"], "loc": q["loc"], "bounds": q["bounds"]} for q in posts],
               "planks": len(planks)}
        if planks:
            bs = [q["bounds"] for q in planks]
            rec["plank_union"] = {"min": [round(min(b["min"][i] for b in bs), 1) for i in range(3)], "max": [round(max(b["max"][i] for b in bs), 1) for i in range(3)]}
            lowest = min(bs, key=lambda b: b["min"][2])
            rec["lowest_plank"] = lowest
        # ground below the eave (outside edge of the purlin, 30 cm further out)
        if purlin and purlin["bounds"]:
            pb = purlin["bounds"]
            yc = (pb["min"][1] + pb["max"][1]) / 2
            outward = 1 if tag == "north" else -1
            gz = {}
            for x in (pb["min"][0] + 100, (pb["min"][0] + pb["max"][0]) / 2, pb["max"][0] - 100):
                d = sv.trace([x, yc + outward * 30, pb["min"][2] - 5], [x, yc + outward * 30, pb["min"][2] - 1500])
                gz["%.0f" % x] = None if d is None else round(pb["min"][2] - 5 - d, 1)
            rec["ground_below_eave"] = gz
            rec["eave_line"] = {"start": [round(pb["min"][0], 1), round(yc, 1), round(pb["max"][2], 1)], "end": [round(pb["max"][0], 1), round(yc, 1), round(pb["max"][2], 1)],
                                "fall_height_cm": round(pb["max"][2] - max(v for v in gz.values() if v is not None), 1) if any(v is not None for v in gz.values()) else None}
        out["courtyard"][tag] = rec
    pieces = {p["label"]: p for p in inv["roof_pieces"]}
    for tag, (lab, a, b, outward) in EAVE_PANELS.items():
        p = pieces.get(lab)
        if not p:
            out["cloister"].append({"walk": tag, "panel": lab, "error": "panel not found"})
            continue
        x = {"loc": p["loc"], "rot": p["rot"], "scale": p["scale"]}
        s, e = local_to_world(x, a), local_to_world(x, b)
        ground = {}
        for nm, pt in (("start", s), ("mid", [(s[i] + e[i]) / 2 for i in range(3)]), ("end", e)):
            px, py = pt[0] + outward[0] * 30, pt[1] + outward[1] * 30
            d = sv.trace([px, py, pt[2] - 5], [px, py, pt[2] - 1500])
            ground[nm] = None if d is None else round(pt[2] - 5 - d, 1)
        gz = [v for v in ground.values() if v is not None]
        out["cloister"].append({"walk": tag, "panel": lab, "mesh": p["mesh"], "start": s, "end": e, "eave_z": s[2], "drip_side_dir_xy": outward,
                                "length_cm": round(math.dist(s, e), 1), "ground_z_by_point": ground,
                                "ground_z": round(max(gz), 1) if gz else None, "fall_height_cm": round(s[2] - max(gz), 1) if gz else None})
    out["cloister_note"] = ("Eave lines are the straight runs of the rectangular lean-to panels (local y = 0, local x 0..1000 x scale). The four valley-cut panels at each corner keep only a triangle, so they add no eave line. "
                            "Drips fall on the garth side of the arcade (the eave is 70 cm beyond the arcade piers).")
    inv["eaves"] = out
    sv.log("eaves: courtyard %s, cloister %d lines" % (list(out["courtyard"].keys()), len(out["cloister"])))


def _vtrace_up(sv, x, y, z0, span=1500.0):
    d = sv.trace([x, y, z0], [x, y, z0 + span])
    return None if d is None else round(z0 + d, 1)


def _vtrace_down(sv, x, y, z0, span=2500.0):
    d = sv.trace([x, y, z0], [x, y, z0 - span])
    return None if d is None else round(z0 - d, 1)


def _box_dist_xy(x, y, b):
    dx = max(b["min"][0] - x, 0, x - b["max"][0])
    dy = max(b["min"][1] - y, 0, y - b["max"][1])
    return math.hypot(dx, dy)


VAULT_CROWN_Z = -100.0   # P9: corridor-style crypt vaults, 'clear crown Z -100' (the greybox shell's flat ceiling is at about -40)


@stage
def drips(sv, inv, refs, SMA):
    """Item 7: 8 crypt drip points (5 over the water) and 2 belfry points, measured with traces.

    The crypt shell keeps its collision (hidden greybox, flat ceiling at about Z -40), but the visible ceiling is the barrel vault whose crown is at
    Z -100 on its centre line, so the points are on the corridor centre lines and at crown - 5.
    """
    out = {"crypt_candidates": [], "belfry_candidates": []}
    water = {w["label"]: w for w in inv.get("water", [])}

    def evaluate(tag, x, y, floor_z, over):
        ceil = _vtrace_up(sv, x, y, max(floor_z, -590.0) + 30)
        rec = {"tag": tag, "xy": [x, y], "over_water": over, "start_z": max(floor_z, -590.0) + 30, "collision_ceiling_hit_z": ceil, "visible_crown_z": VAULT_CROWN_Z}
        if ceil is not None:
            pz = min(ceil, VAULT_CROWN_Z) - 5
            fl = _vtrace_down(sv, x, y, pz)
            rec["point"] = [x, y, pz]
            rec["floor_hit_z"] = fl
            surf = water[over]["surface_z"] if over else fl
            rec["fall_to_surface_cm"] = round(pz - surf, 1) if surf is not None else None
            rec["lane"] = lane_report(inv, (x, y, floor_z + 100))
        return rec

    for lab, xs in (("CA_Water_W", (8900, 9050, 9200)), ("CA_Water_E", (9900, 10000, 10100)), ("CA_Water_Pit", (9400, 9550, 9700))):
        w = water.get(lab)
        if not w:
            continue
        for x in xs:
            out["crypt_candidates"].append(evaluate("%s_%d" % (lab[9:], x), x, -2280, w["surface_z"], lab))
    for tag, x, y in (("WC_a", 6450, -1900), ("WC_b", 6450, -1650), ("SC_a", 6900, -2350), ("SC_b", 7250, -2350), ("NC_a", 10250, -900), ("NC_b", 10750, -900),
                      ("NC_c", 11250, -900), ("LW_a", 10150, -1300), ("LE_a", 11350, -1300)):
        out["crypt_candidates"].append(evaluate(tag, x, y, -595, None))
    ok = lambda c: c.get("point") and c["lane"]["walkpath_cm"] >= 80 and c["lane"]["ai_point_cm"] >= 100  # noqa: E731
    sel_w, per = [], Counter()
    score = lambda c: min(c["lane"]["walkpath_cm"] / 150.0, 1.0) + min(c["lane"]["ai_point_cm"] / 150.0, 1.0)  # noqa: E731
    ranked = sorted((c for c in out["crypt_candidates"] if c["over_water"] and ok(c)), key=lambda c: -score(c))
    for pref in ("CA_Water_W", "CA_Water_E", "CA_Water_Pit", "CA_Water_W", "CA_Water_E", "CA_Water_Pit"):
        c = next((c for c in ranked if c["over_water"] == pref and c not in sel_w and per[pref] < 2), None)
        if c and len(sel_w) < 5:
            sel_w.append(c)
            per[pref] += 1
    sel_d, rooms = [], set()
    for c in sorted((c for c in out["crypt_candidates"] if not c["over_water"] and ok(c)), key=lambda c: -score(c)):
        room = c["tag"].split("_")[0]
        if room not in rooms and len(sel_d) < 3:
            sel_d.append(c)
            rooms.add(room)
    out["crypt_selected"] = [{"point": c["point"], "tag": c["tag"], "over_water": c["over_water"], "collision_ceiling_hit_z": c["collision_ceiling_hit_z"],
                              "fall_height_cm": c["fall_to_surface_cm"], "floor_hit_z": c["floor_hit_z"], "lane": c["lane"]} for c in sel_w + sel_d]
    # belfry: the roof has no collision, so the underside height is analytic from TWA_Roof (square pyramid, eaves at the wall top)
    roof = next((p for p in inv["roof_pieces"] if p["label"] == "TWA_Roof"), None)
    bf = [s for s in SMA.items() if (s[1]["label"] or "") == "TWA_BellFrame"]
    fb = sv.bounds(bf[0][0]) if bf else {"min": [12255, 1850, 2500], "max": [12585, 2150, 2880]}
    if roof:
        cx, cy, base = roof["loc"][0], roof["loc"][1], roof["loc"][2]
        for tag, x, y in (("E_wall", 12930, 2250), ("N_wall", 12600, 2440), ("NW_corner", 12100, 2400), ("W_wall", 12070, 2000), ("S_wall", 12700, 1560)):
            d = max(abs(x - cx), abs(y - cy))
            in_missing = (x - cx) < -100 and (y - cy) < -100
            top = base - 10 + 1210 * (1 - d / 525.0)
            pz = round(top - 25, 1)
            # the hidden greybox roof slab (Tw_Roof, Z 3500-3540, BlockAll) would stop a trace from above, so start the floor trace below it
            fl = _vtrace_down(sv, x, y, 3480.0, span=1500)
            out["belfry_candidates"].append({"tag": tag, "xy": [x, y], "chebyshev_from_axis_cm": round(d), "in_collapsed_SW_quarter": in_missing,
                                             "roof_top_z_analytic": round(top, 1), "point": [x, y, pz], "floor_hit_z": fl,
                                             "fall_height_cm": round(pz - fl, 1) if fl is not None else None,
                                             "dist_to_bell_frame_xy_cm": round(_box_dist_xy(x, y, fb), 1),
                                             "lane": lane_report(inv, (x, y, (fl or 2500) + 100))})
    okb = [c for c in out["belfry_candidates"] if not c["in_collapsed_SW_quarter"] and c["floor_hit_z"] is not None and c["dist_to_bell_frame_xy_cm"] >= 120
           and c["lane"]["walkpath_cm"] >= 100]
    okb.sort(key=lambda c: -min(c["lane"]["walkpath_cm"], c["dist_to_bell_frame_xy_cm"] * 3))
    out["belfry_selected"] = okb[:2]
    out["bell_frame_bounds"] = fb
    inv["drips"] = out
    sv.log("drips: crypt %d selected (%d over water), belfry %d" % (len(out["crypt_selected"]), len(sel_w), len(out["belfry_selected"])))


SLITS = {"F03": ((12500, 1540, 718.1), (0, 1), True), "F07": ((12500, 1540, 1627.3), (0, 1), True), "F08": ((12040, 2000, 1854.0), (1, 0), True),
         "F05": ((12500, 2460, 1172.7), (0, -1), False), "F09": ((12500, 2460, 2081.8), (0, -1), False),
         "F06": ((12960, 2000, 1400.0), (-1, 0), False), "F10": ((12960, 2000, 2309.1), (-1, 0), False)}


def _yaw_for_normal(n):
    """yaw so that the cloth's local +Y (its plane normal) points along the horizontal vector n."""
    return round(math.degrees(math.atan2(-n[0], n[1])), 1)


@stage
def cloth(sv, inv, refs, SMA):
    """Item 9: ten cloth placements."""
    out = {"belfry": [], "slits": [], "cloister": [], "gate": [], "notes": []}
    CL = {"A": ("SM_LB_Prop_ClothStrip_A", 35, 220), "B": ("SM_LB_Prop_ClothStrip_B", 25, 160), "BAN": ("SM_LB_Prop_ClothBanner_A", 110, 240), "SH": ("SM_LB_Prop_ClothSheet_A", 170, 140)}

    def place(group, name, kind, top_xyz, normal, hang, extra=None):
        mesh, w, h = CL[kind]
        pos = [round(top_xyz[0] + 6 * normal[0], 1), round(top_xyz[1] + 6 * normal[1], 1), top_xyz[2]]
        rec = {"id": name, "mesh": mesh, "size_wxh_cm": [w, h], "location": pos, "rotation_pyr": [0, _yaw_for_normal(normal), 0], "scale": [1, 1, 1],
               "normal_into_room": normal, "hangs_from": hang, "bottom_z": round(pos[2] - h, 1),
               "lane": lane_report(inv, (pos[0], pos[1], pos[2] - h / 2))}
        if extra:
            rec.update(extra)
        out[group].append(rec)
        return rec

    # belfry: the 8 louvred lancets (sill z 2700, louvre top 3150, apex 3262.6); inner faces W 12040, E 12960, S 1540, N 2460
    bf_fb = (inv.get("drips") or {}).get("bell_frame_bounds") or {"min": [12255, 1850, 2500], "max": [12585, 2150, 2880]}
    for name, kind, (x, y), normal, face in (("Belfry_W1", "A", (12040, 1905), (1, 0), "TWA_Louvre_W1 on the W face"), ("Belfry_N2", "BAN", (12595, 2460), (0, -1), "TWA_Louvre_N2 on the N face"),
                                           ("Belfry_E1", "B", (12960, 2095), (-1, 0), "TWA_Louvre_E1 on the E face"), ("Belfry_S2", "A", (12405, 1540), (0, 1), "TWA_Louvre_S2 on the S face")):
        r = place("belfry", name, kind, [x, y, 3180], normal, "head of the lancet above %s (arch springs at about Z 3150, apex 3262.6)" % face)
        r["dist_to_bell_frame_xy_cm"] = round(_box_dist_xy(r["location"][0], r["location"][1], bf_fb), 1)
    # stair slits: choose the two with the best lane clearance, moon-spot slits first
    cand = []
    for nm, ((x, y, z), normal, moon) in SLITS.items():
        pos = (x + 6 * normal[0], y + 6 * normal[1], z + 60 - 80)
        cand.append((nm, lane_report(inv, pos), moon))
    out["slit_candidates"] = [{"slit": n, "lane": l, "moon_spot": m} for n, l, m in cand]
    ok = sorted((c for c in cand if c[1]["walkpath_cm"] >= 60), key=lambda c: (not c[2], -c[1]["walkpath_cm"]))
    for nm, l, m in ok[:2]:
        (x, y, z), normal, _ = SLITS[nm]
        place("slits", "Slit_" + nm, "B", [x, y, round(z + 60, 1)], normal, "head of the inner splay of slit %s (splay 50 wide x 120 tall about Z %.0f)" % (nm, z))
    # cloister arcade bays: arch centres from the P10 table; cloth hangs in the arch plane, facing the walk
    BAYS = {"S_1": ((10750, 1350), (0, -1), "CLA_Arch_S_1 (span 220)"), "S_2": ((11050, 1350), (0, -1), "CLA_Arch_S_2 (span 220)"),
            "N_1": ((10750, 2250), (0, 1), "CLA_Arch_N_1 (span 220)"), "N_2": ((11050, 2250), (0, 1), "CLA_Arch_N_2 (span 220)"),
            "W_1": ((10250, 1850), (-1, 0), "CLA_Arch_W_1 (span 220)"), "E_1": ((11450, 1850), (1, 0), "CLA_Arch_E_1 (span 220)")}
    bay_rows = []
    for nm, ((x, y), normal, arch) in BAYS.items():
        bay_rows.append((nm, lane_report(inv, (x + 6 * normal[0], y + 6 * normal[1], 400)), arch))
    out["bay_candidates"] = [{"bay": n, "lane": l} for n, l, a in bay_rows]
    picked, rows = [], set()
    for nm, l, arch in sorted(bay_rows, key=lambda t: -t[1]["walkpath_cm"]):
        if nm[0] not in rows and len(picked) < 3:
            picked.append((nm, arch))
            rows.add(nm[0])
    for (nm, arch), kind, top in zip(picked, ("BAN", "SH", "A"), (555, 520, 555)):
        (x, y), normal, _ = BAYS[nm]
        place("cloister", "Cloister_" + nm, kind, [x, y, top], normal, "intrados of %s (arch rings span Z 330..620; intrados crown estimated at about Z 585, verify in the editor)" % arch)
    # gatehouse arch: the courtyard-facing inner face is X 300; the opening is Y -200..150
    ivy = []
    for r, v in SMA.items():
        if (v["label"] or "").startswith("Ivy_"):
            x = sv.xform(r)
            if x and 150 <= x["loc"][0] <= 450:
                ivy.append({"label": v["label"], "loc": x["loc"]})
    out["gate_ivy_near"] = ivy
    gate = []
    for y in (-330, -270, 230, 270, 330, 400, -400):
        solid = []
        for z in (300, 450, 600):
            d = sv.trace([900, y, z], [-300, y, z])
            solid.append(d is not None and abs(d - 600) < 12)
        near_ivy = min((math.hypot(i["loc"][1] - y, 0) for i in ivy), default=9999)
        gate.append({"y": y, "solid_at_z300_450_600": solid, "dist_to_nearest_ivy_y_cm": round(near_ivy, 1),
                     "lane": lane_report(inv, (306, y, 500))})
    out["gate_candidates"] = gate
    g = next((c for c in gate if all(c["solid_at_z300_450_600"]) and c["dist_to_nearest_ivy_y_cm"] >= 80 and c["lane"]["walkpath_cm"] >= 100), None)
    if g:
        place("gate", "Gate_Inner", "A", [300, g["y"], 600], (1, 0), "wall face beside the gate arch, X 300 (the courtyard side); cloth plane parallel to the wall, 6 cm off the face")
    inv["cloth"] = out
    sv.log("cloth: %d placements" % sum(len(out[k]) for k in ("belfry", "slits", "cloister", "gate")))


@stage
def curtains(sv, inv, refs, SMA):
    """Item 10: eight rain-curtain cards (3000 x 2500, bottom-centre pivot), chosen from a ring of candidates outside the perimeter backdrop walls.

    A card is 'seen' from a viewpoint when its centre is within the 90 degree horizontal FOV, 3000-16000 cm away (the material fades out under 3000),
    and a trace from the camera reaches its top or its upper part. Selection is greedy on the number of distinct viewpoints that see it.
    """
    vp = json.load(open(VIEWPOINTS, encoding="utf-8"))
    perim = {}
    for r, v in SMA.items():
        if (v["label"] or "").startswith("Perim_") or (v["label"] or "") in ("Ground_1", "Ground_2", "Ground_3", "Ground_4", "Ground_5", "Ground_6", "Ground_7"):
            perim[v["label"]] = {"bounds": sv.bounds(r)}
    inv["perimeter"] = perim
    cands = []
    for x in (-1500, 600, 2400, 4200, 6000, 8000, 10000, 11500, 13000, 14500):
        cands.append(("N_%d" % x, (x, 4800), (0, -1)))
        cands.append(("S_%d" % x, (x, -4800), (0, 1)))
    for y in (-2500, 0, 2500):
        cands.append(("W_%d" % y, (-4500, y), (1, 0)))
        cands.append(("E_%d" % y, (15200, y), (-1, 0)))
    evaluated = []
    for nm, (x, y), n in cands:
        yaw = _yaw_for_normal(n)
        bottom = -200.0
        views = []
        for pname, pose in vp.items():
            cx, cy, cz, cp, cyaw = pose
            dx, dy = x - cx, y - cy
            dist = math.hypot(dx, dy)
            ang = abs((math.degrees(math.atan2(dy, dx)) - cyaw + 180) % 360 - 180)
            if ang > 45 or dist < 3000 or dist > 16000:
                continue
            clear = 0
            for zz in (bottom + 2500, bottom + 1900):
                full = math.dist([cx, cy, cz], [x, y, zz])
                d = sv.trace([cx, cy, cz], [x, y, zz])
                if d is None or d >= full - 5:
                    clear += 1
            if clear:
                views.append({"pose": pname, "dist_cm": round(dist), "angle_off_axis_deg": round(ang), "clear_points_of_2": clear})
        evaluated.append({"id": nm, "location_bottom_centre": [x, y, bottom], "rotation_pyr": [0, yaw, 0], "scale_for_3000x2500": [30, 1, 25],
                          "faces_toward": n, "views": views, "n_views": len(views)})
    # greedy pick: most new viewpoints first, cards at least 1800 cm apart (3000 wide, so neighbours overlap), then fill by the number of views
    chosen, seen = [], set()
    pool = sorted(evaluated, key=lambda c: -c["n_views"])
    while len(chosen) < 8 and pool:
        best = max(pool, key=lambda c: (len({v["pose"] for v in c["views"]} - seen), c["n_views"]))
        pool.remove(best)
        if any(math.dist(best["location_bottom_centre"][:2], c["location_bottom_centre"][:2]) < 1800 for c in chosen):
            continue
        chosen.append(best)
        seen |= {v["pose"] for v in best["views"]}
    inv["curtain_candidates"] = [{k: c[k] for k in ("id", "location_bottom_centre", "n_views")} for c in evaluated]
    inv["curtains"] = chosen
    inv["curtain_coverage"] = {"viewpoints_total": len(vp), "viewpoints_seen_by_chosen": sorted(seen), "viewpoints_not_seen": sorted(set(vp) - seen)}
    sv.log("curtains: %s; viewpoints covered %d/%d" % ([(c["id"], c["n_views"]) for c in chosen], len(seen), len(vp)))


NIAGARA_TOOLSETS = ["NiagaraToolsets.NiagaraToolset_Info", "NiagaraToolsets.NiagaraToolset_Component",
                    "NiagaraToolsets.NiagaraToolset_Blueprint", "NiagaraToolsets.NiagaraToolset_System",
                    "NiagaraToolsets.NiagaraToolset_Assets"]


def _type_str(s):
    """Compact type of a JSON-schema property."""
    t = s.get("title")
    if t == "NiagaraExt_StackItemReference":
        return "StackItemRef{system, emitterName, scriptName, moduleName, rendererIndex, inputNameStack[]}"
    if s.get("type") == "object" and "refPath" in (s.get("properties") or {}):
        return "ref " + (t or "object").split(".")[-1]
    if "oneOf" in json.dumps(s)[:4000] and t == "NiagaraToolsetInstancedValue":
        return "NiagaraToolsetInstancedValue{struct, value: one of the allowed value structs}"
    if s.get("type") == "array":
        it = s.get("items") or {}
        return "array of " + (it.get("title") or it.get("type") or "?")
    if s.get("type") == "object" and s.get("properties"):
        return "%s{%s}" % (t or "object", ", ".join(s["properties"].keys()))
    return t or s.get("type") or "?"


def _first_line(text, n=170):
    text = (text or "").replace("\r", "").strip().split("\n\n")[0].replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text if len(text) <= n else text[:n - 3] + "..."


NIAGARA_ANSWERS = """## Capability answers from the schemas (nothing was created)

Evidence below is from the tool schemas above plus three read-only reads: `FindNiagaraScripts name=Collision`, `GetModuleSchemaFromAsset` on `/Niagara/Modules/Collision/Collision` and `GetRendererSchema` for `NiagaraSpriteRendererProperties`.

| Question | Answer | Basis |
|---|---|---|
| Add or remove modules on an emitter stack | **Yes** | `AddModule {moduleLocationRef, moduleAsset}` (asset from `FindNiagaraScripts`), `RemoveModule`, `SetModuleEnabled`, `AddSetParametersModule` (a generated "Set Parameters" module for named attributes), `AddSetParameterEntry`, `RemoveSetParameterEntry`. `AddEmitter` copies an emitter template, `RemoveEmitter` deletes one. |
| Set module inputs | **Yes** for numbers, bools, vectors, colours, enums, linked attributes, dynamic inputs and single-line HLSL expressions | `SetStackInputData {stackInputRef, inputData}`. `inputData` is one of: `Enum` (enum + enumName), `Linked` (a Niagara variable), `HlslExpression` (a single rvalue expression), `DataInterface` (JSON), `DynamicInput` (a dynamic-input script asset), or a literal (`NiagaraFloat`, `NiagaraBool`, `NiagaraInt32`, `NiagaraPosition`, `Vector3f`, `Vector2f`, `Vector4f`, `Quat4f`, `LinearColor`, `Rotator`). Dynamic-input inputs are addressed with `inputNameStack`. |
| Collision module: Distance Field mode | **Not provable from the schemas; the spike must test it.** | The library `Collision` module exposes 27 inputs and 100+ outputs through `GetModuleSchemaFromAsset`, and the text contains no "Distance Field", "Scene Depth" or "Collision Mode". No static-switch pin is listed (the schema has no field for one), and no tool sets a static switch by name. The module folder also holds `NiagaraDistanceFieldCollisions` (usage module, 0 inputs, 0 outputs), which may be the mode itself. S1 must place `Collision` on a GPU emitter and read `GetModuleSchema` / `GetModuleTopology` on the placed module; if the mode is a static switch, `SetStackInputData` with an `Enum` value may reach it, otherwise a headless Python Niagara script is needed (R-65). |
| Kill on collision | **Yes** | Input `Kill On Collision` (NiagaraInt32; edit condition `KillOnCollision`) on `Collision`, set with `SetStackInputData` (int literal). |
| Restitution, friction | **Yes** | Inputs `Restitution`, `Friction`, `Static Friction`, `Friction During a Bounce`, `Particle Mass`, `Particle Radius Scale`, `Max Number Of Collisions`, `Enable Rest State` (all float, bool or int literals). |
| Read "has collided" | **Yes, by name** | `Collision` outputs `Particles.HasCollided` and `Particles.Number Of Collisions` (also `Transient.CollisionIsResting`, `Particles.RestCounter`). A later module reads it with `Linked` input data or `AddSetParametersModule` entries. |
| Add a second renderer | **Yes** | `AddRenderer {newRendererLocation: StackItemRef (emitter), rendererClass}` returns the new index; `RemoveRenderer`. `GetRendererSchema` lists the properties per class. |
| Sprite renderer facing, alignment, material | **Yes** | `SetRendererData {renderer, rendererData: {propertyValues: JSON string}}`. The sprite schema has `material` (ref), `materialUserParamBinding`, `alignment` (Unaligned, VelocityAligned, CustomAlignment, Automatic), `facingMode` (FaceCamera, FaceCameraPlane, CustomFacingVector, FaceCameraPosition, FaceCameraDistanceBlend, Automatic), `subImageSize`, `bSubImageBlend`, `pivotInUVSpace`, `sortMode`, plus attribute bindings (`spriteFacingBinding`, `spriteAlignmentBinding`, `spriteSizeBinding`, `colorBinding`, `subImageIndexBinding`, `normalizedAgeBinding`, `dynamicMaterial*Binding`). The ring's custom facing (0, 0, 1) is `facingMode` CustomFacingVector with `spriteFacingBinding` pointing at an attribute that a module sets to (0, 0, 1) (a `SetParameters` entry or a `Linked`/literal input). |
| Scratch-pad or custom HLSL modules | **No** | No tool creates a scratch-pad script, a custom-HLSL module or any Niagara script asset. The nearest options: `SetStackInputData` with `HlslExpression` (one rvalue, no statements, so no loop), `AddSetParametersModule` for named attributes, `DynamicInput` with an existing library dynamic input, and `GetAvailableDynamicInputs`. The Splash fallback ("march the global distance field in 24 steps") needs a scratch-pad module and so is **not reachable over MCP**; it would be a headless Python Niagara script, or the simplification. `CreateNiagaraSystem` only clones a template system. |
| Set user parameters | **Yes** | Definition: `AddUserVariables {system, variablesToAdd}` (float, bool, int32, position, vector, vector2d, vector4, quat, colour, rotator, enum, data interface, object) and `RemoveUserVariables`. Per component instance: `NiagaraToolset_Component.SetVariable {component, variable}`, `GetVariable`, `GetUserVariables`; `SetSystem {niagaraComponent, system, bResetExistingOverrideParameters}`. At runtime the FX subsystem sets them from C++ (`SetVariableVec3` and so on). |
| Compile state and issues | **Yes** | `GetSystemCompileState`, `GetStackIssues`, `ApplyStackIssueFix`. |
| Placing a system | Not a Niagara tool | `SceneTools.add_to_scene_from_asset` (MCP_NOTES "FX and fog"). `NiagaraToolset_Blueprint.ConstructNiagaraBPWrapperFromSystem` makes a Blueprint actor around a system (it creates an asset; not used by F0). |
"""


@stage
def niagara(sv, inv, refs=None):
    out = ["# P15 F0: Niagara MCP tools",
           "Generated by `Tools/fx/p15_f0_survey.py` (stage `niagara`) from `list_toolsets` and `describe_toolset`. Read-only; no asset was created. "
           "Survey time %s." % time.strftime("%Y-%m-%d %H:%M:%S"), ""]
    lst = sv.ue.raw("list_toolsets", {})
    names = [t for t in re.findall(r"^- ([A-Za-z_]+\.[\w.]+):", lst if isinstance(lst, str) else json.dumps(lst), re.M)]
    nia = [n for n in names if "niagara" in n.lower()]
    inv["niagara_toolsets"] = nia
    out.append("`list_toolsets` toolsets whose name contains Niagara: " + ", ".join("`%s`" % n for n in nia) + ".")
    out.append("")
    tools = {}
    for ts in nia:
        d = sv.step("describe:" + ts, lambda ts=ts: sv.ue.describe(ts))
        out.append("## %s" % ts)
        out.append("")
        out.append("| Tool | Arguments (`*` = required) | Purpose |")
        out.append("|---|---|---|")
        tools[ts] = []
        for t in d["tools"]:
            n = t["name"].split(".")[-1]
            sch = t.get("inputSchema") or {}
            req = set(sch.get("required") or [])
            args = []
            for k, v in (sch.get("properties") or {}).items():
                args.append("`%s%s`: %s" % (k, "*" if k in req else "", _type_str(v).replace("|", "/")))
            out.append("| `%s` | %s | %s |" % (n, "<br>".join(args) or "(none)", _first_line(t.get("description")).replace("|", "/")))
            tools[ts].append({"name": n, "args": {k: _type_str(v) for k, v in (sch.get("properties") or {}).items()},
                              "required": sorted(req), "description": _first_line(t.get("description"), 300)})
        out.append("")
    inv["niagara_tools"] = tools
    # live read-only evidence
    ev = {}
    col = sv.step("niagara:findcollision", lambda: sv.call("NiagaraToolsets.NiagaraToolset_Assets", "FindNiagaraScripts",
                                                           {"folderPath": "", "name": "Collision", "usages": [], "visibilities": [], "moduleUsageBitmask": 0,
                                                            "bRecursive": True, "bIncludeDeprecated": False}))
    ev["collision_scripts"] = [short(x["objectPath"]) if isinstance(x, dict) else str(x) for x in col]

    def colschema():
        r = J(sv.call("NiagaraToolsets.NiagaraToolset_System", "GetModuleSchemaFromAsset", {"moduleAsset": {"refPath": "/Niagara/Modules/Collision/Collision.Collision"}}))
        ins = [{"name": i["name"], "type": short(R(i["type"]["classStructOrEnum"]))} for i in r["inputs"]]
        outs = [o["name"] for o in r["outputs"] if o["name"].startswith(("Particles.", "Transient.CollisionIsResting")) or "Kill" in o["name"]]
        return {"inputs": ins, "outputs_of_interest": outs, "n_outputs": len(r["outputs"])}
    ev["collision_module"] = sv.step("niagara:collisionschema", colschema)
    rs = sv.step("niagara:spriteschema", lambda: sv.call("NiagaraToolsets.NiagaraToolset_System", "GetRendererSchema",
                                                         {"rendererClass": {"refPath": "/Script/Niagara.NiagaraSpriteRendererProperties"}}))
    ev["sprite_renderer_properties"] = list(J(rs["propertySchema"]).keys())
    inv["niagara_evidence"] = ev
    out.append("## Evidence reads")
    out.append("")
    out.append("- `FindNiagaraScripts name=Collision`: %s." % ", ".join("`%s`" % x for x in ev["collision_scripts"]))
    cm = ev["collision_module"]
    out.append("- `/Niagara/Modules/Collision/Collision` inputs (%d): %s." % (len(cm["inputs"]), ", ".join("`%s` (%s)" % (i["name"], i["type"]) for i in cm["inputs"])))
    out.append("- Its outputs of interest (of %d): %s." % (cm["n_outputs"], ", ".join("`%s`" % x for x in cm["outputs_of_interest"])))
    out.append("- `NiagaraSpriteRendererProperties` properties (%d): %s." % (len(ev["sprite_renderer_properties"]), ", ".join("`%s`" % x for x in ev["sprite_renderer_properties"])))
    out.append("")
    out.append(NIAGARA_ANSWERS)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "p15_f0_niagara_tools.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    sv.log("niagara md written (%d toolsets)" % len(nia))


def _tbl(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in r) + " |")
    return out + [""]


def _p(v, n=1):
    if v is None:
        return "-"
    if isinstance(v, (list, tuple)):
        return "(" + ", ".join(_p(x, n) for x in v) + ")"
    if isinstance(v, float):
        return ("%." + str(n) + "f") % v if abs(v - round(v)) > 1e-9 else "%d" % round(v)
    return str(v)


def write_tables(inv):
    h = inv.get("header", {})
    L = ["# P15 F0 survey: tables",
         "Generated by `Tools/fx/p15_f0_survey.py` from `Docs/ArtTest/fx/p15_f0.json` (read-only survey). Survey time %s; level `%s`; PIE off; map dirty before **%s**, after **%s**; %s editor calls in %s s; %d call errors (listed at the end)."
         % (h.get("time"), h.get("level"), h.get("dirty_before"), h.get("dirty_after"), h.get("calls"), h.get("seconds"), len(inv.get("errors", []))),
         "Coordinates are world cm. Rotations are (pitch, yaw, roll). `Proposed value for the plan` lines are the F0 answers; the lead copies them into `P15_PARTICLES.md`.", ""]
    # ------------------------------------------------------------------ 1 flames
    L += ["## 1. Flames", ""]
    fl = inv.get("flames_static_mesh_actors", [])
    L += ["`SM_LB_Prop_CandleFlame_A` and anything named Flame: **%d static-mesh actors**. They are level instances (class `StaticMeshActor`), never inside a Blueprint." % len(fl), ""]
    L += _tbl(["Label", "Area", "Location", "Mesh", "Slot: effective material (source)", "Cast shadow"],
              [(f["label"], f["area"], _p(f["loc"]), f["mesh"], "; ".join("%s: %s (%s)" % (s["slot"], s["material"], s["source"]) for s in f["slots"]), f["cast_shadow"]) for f in fl])
    cnt = Counter((f["area"], tuple(sorted({s["material"] for s in f["slots"]})), tuple(f["material_source"])) for f in fl)
    L += ["Roll-up (area / effective material / source): " + "; ".join("%s / %s / %s x%d" % (a, "+".join(m), "+".join(s), n) for (a, m, s), n in cnt.items()) + ".", ""]
    L += ["### Flame components owned by Blueprints (level instances)", ""]
    L += _tbl(["Actor", "Class chain", "Never-save in chain", "Component", "Mesh", "Effective material per slot (source)", "BP template mesh / override"],
              [(f["actor"], " > ".join(f["chain"]), f["never_save_in_chain"] or "none", f["component"], f["mesh"],
                "; ".join("%s: %s (%s)" % (s["slot"], s["material"], s["source"]) for s in f["slots"]),
                "%s / %s" % ((f["template"] or {}).get("mesh"), (f["template"] or {}).get("ov"))) for f in inv.get("flames_blueprint_components", [])])
    L += ["### Blueprint assets that reference a flame mesh or `MI_LB_CandleFlame`", ""]

    def _rel(c):
        r = c.get("rel_loc")
        return _p([r.get(k) for k in "xyz"]) if isinstance(r, dict) else _p(r)
    L += _tbl(["Blueprint", "Parent", "Never-save", "Flame components in the class default (component: mesh, override, relative location)"],
              [(b["blueprint"], b["parent"], b["never_save"], "; ".join("%s: %s, %s, %s" % (c["component"], c["mesh"], c["ov"], _rel(c)) for c in b["flame_components"])) for b in inv.get("flames_blueprint_assets", [])])
    mi = inv.get("mi_lb_candleflame") or {}
    L += ["`MI_LB_CandleFlame`: parent `%s`; scalars %s; vectors %s; textures %s." % (mi.get("parent"), json.dumps(mi.get("scalars")), json.dumps(mi.get("vectors")), json.dumps(mi.get("textures"))), ""]
    bpa_ns = [a for a in inv.get("bp_actors", []) if a["never_save_in_chain"]]
    ns_flames = [f for f in inv.get("flames_blueprint_components", []) if f["never_save_in_chain"]]
    ns_assets = [b for b in inv.get("flames_blueprint_assets", []) if b["never_save"] and b["flame_components"]]
    L += ["Level Blueprint actors: %d, of which %d have a never-save Blueprint in their chain (%s). **Flames owned by a never-save Blueprint: %s.**" % (
        len(inv.get("bp_actors", [])), len(bpa_ns), ", ".join(sorted({re.sub(r"_C$", "", a["class"].rsplit(".", 1)[-1]) for a in bpa_ns})),
        "NONE" if not (ns_flames or ns_assets) else ", ".join([f["actor"] for f in ns_flames] + [b["blueprint"] for b in ns_assets])), ""]
    L += ["### Candle props without a separate flame mesh nearby", ""]
    L += _tbl(["Mesh", "Count", "With a flame mesh within 40 cm", "Sample"],
              [(q["mesh"], q["count"], q["with_flame_within_40cm"], "; ".join("%s %s" % (i["label"], _p(i["loc"])) for i in q["items"][:3])) for q in inv.get("candle_props", [])])
    L += [("**Proposed value for the plan (section 8, candle flames):** all %d level flame meshes draw one material, `MI_LB_CandleFlame` (parent: the engine's `EmissiveMeshMaterial`, one vector `Color` (12, 5, 0.8); never reparent it on screen), from the mesh default (slot `MAT_Flame` of `SM_LB_Prop_CandleFlame_A`); no actor has an override. One slot edit on the mesh asset (or one override per actor to `MI_Flame_Candle`) therefore covers the 13 chapel and 9 crypt flames. " % len(fl)) +
          "The same MI is also used by the 4 `BP_PuzzleCandle_C` `Flame` components (engine Sphere mesh; the MI is set on the Blueprint template and on each placed instance), by `BP_LBCharacter.CandleFlame` (the player's candle, not a level actor) and by the Saint*Flame cones of `BP_StainedGlassClue_Saints`. "
          "None of those Blueprints is on the never-save list (chains: `BP_PuzzleCandle > Actor`, `BP_LBCharacter > LBCharacter`, `BP_StainedGlassClue > Actor`). MCP_NOTES warns that component edits on placed Blueprint instances often do not persist, so change the shared MI parameters or the mesh slot instead of the instances. "
          "Melted-candle props with no flame (`SM_Candle_Melted_03/07/09`, the candlesticks) need no change.", ""]
    # ------------------------------------------------------------------ 2 fires
    L += ["## 2. Fire actors (Cascade and Niagara components)", ""]
    L += _tbl(["Label", "Class (chain)", "Template / asset", "Location", "Scale", "Component", "Matched light (cm)"],
              [(f["label"], " > ".join(f.get("chain") or [f.get("class") or ""]), "; ".join(short(str(cc.get("template") or cc.get("asset")).split(".")[0]) for cc in f["components"] if cc.get("template") or cc.get("asset")),
                _p((f["xf"] or {}).get("loc")), _p((f["xf"] or {}).get("scale")),
                "; ".join(cc["name"] for cc in f["components"] if cc.get("class") in ("ParticleSystemComponent", "NiagaraComponent")),
                "%s (%s)" % (f.get("match"), f["nearest_lights"][0]["dist_cm"] if f["nearest_lights"] else "-")) for f in inv.get("fire_actors", [])])
    L += _tbl(["Point light", "Found", "Location"], [(k, v["found"], _p((v["xf"] or {}).get("loc"))) for k, v in inv.get("fire_lights", {}).items()])
    L += ["Cascade template referencers: " + json.dumps(inv.get("fire_templates")), "",
          "**Proposed value for the plan (sections 6.3 and 8):** 5 Cascade `Emitter` actors, all plain level actors (no Blueprint): `FX_Torch_Fire` (work-area torch, PS_Fire_00, scale 0.7, (327, 1600, 250), light `Light_WorkArea_Torch` 22 cm away), "
          "`FX_Crypt_Torch_T1/T2/T3` (PS_Fire_00, scale 0.7, Z -380, lights 25 cm away) and `FX_Crypt_Brazier` (PS_Fire_01, scale 0.5, (11000, -2299.1, -459.4), light 19 cm away). "
          "**The courtyard fire pit has no Cascade fire:** `FX_FirePit_Smoke` is a `NiagaraActor` using the existing `NS_LB_SmokeWisp` at (1150, 1650, 25), 5 cm from `Light_FirePit_Ember`. The plan's 'replace the Cascade component on the fire pit' becomes 'add `NS_LB_TorchFire` (User.Scale 2.2) at the fire pit and keep or retire the smoke wisp'. "
          "No fire sits in a never-save Blueprint. The Fab Blueprints `BP_Flame_00/01` reference the Cascade templates but are not placed.", ""]
    # ------------------------------------------------------------------ 3 roofs
    L += ["## 3. Roofs and openings", ""]
    L += _tbl(["Area", "Family (label pattern)", "Count", "Meshes", "Surface piece?", "Smallest local dim x scale, cm", "AABB Z extent, cm", "Union bounds min", "Union bounds max", "collisionEnabled", "Vertical trace stops on piece"],
              [(f["area"], f["family"], f["count"], ", ".join(f["meshes"]), f["surface"], _p(f["thickness_cm"]), _p(f["world_z_extent_cm"]), _p(f["union_min"], 0), _p(f["union_max"], 0),
                json.dumps(f.get("collision_enabled") or f["collision_profiles"]), json.dumps(f["trace_stops_on_piece"])) for f in inv.get("roof_families", [])])
    L += ["Reading the table: 'smallest local dim x scale' is the piece thickness for flat pieces (planks 4, slab 20, lean-to panels 24.3 including the 15 cm rafters below the slates). "
          "For the vaults, the stair-house roof and the tower roof it is the whole piece (a vault is a hollow shell about 25 cm thick per the P10 plan; the pyramid roof is a hollow shell of slate on rafters), so it is not a thickness. "
          "The `collisionEnabled` column is the reliable one: the courtyard planks read `QueryAndPhysics` although the profile string reads NoCollision. "
          "The 'vertical trace' column can be the hidden greybox below the piece (crypt vaults and `Tw_Roof`); only the courtyard planks stand alone in open air.", ""]
    d = inv.get("roof_mesh_distance_field", {})
    L += ["Distance-field state of the roof surface meshes (all have `bGenerateMeshDistanceField` false = no per-mesh override, so the project switch `r.GenerateMeshDistanceFields` = 1 applies; all are Nanite):", ""]
    L += _tbl(["Mesh", "bGenerateMeshDistanceField", "distanceFieldSelfShadowBias", "Nanite", "Nanite bVoxelNDF"],
              [(k.rsplit("/", 1)[-1].split(".")[0], v.get("bGenerateMeshDistanceField"), v.get("distanceFieldSelfShadowBias"), v.get("nanite_enabled"), v.get("nanite_bVoxelNDF")) for k, v in (d.get("meshes") or {}).items()])
    L += ["### Openings (sky visible from inside)", ""]
    op = inv.get("openings", {})
    for k in ("courtyard_north_walk", "courtyard_south_walk"):
        o = op.get(k)
        if o:
            L += ["- **%s**: walk rectangle (X0, Y0, X1, Y1) %s; %d planks (Z %s); planks cover %.0f %% of it. Uncovered rectangles, largest first: %s." % (k, o["walk_rect_xyxy"], o["planks"], o["plank_z_range"], 100 * o["covered_fraction"], o["uncovered_rects_xyxy"])]
    for k in ("chapel_roof_hole", "cloister_north_roof_hole", "cloister_north_vault_hole", "tower_roof_sw_collapse"):
        o = op.get(k)
        if o:
            L += ["- **%s**: %s" % (k, json.dumps({a: b for a, b in o.items() if a != "corners_world"}))]
    L += ["- **open by design**: " + json.dumps(op.get("open_by_design")), "- **crypt grates** (G1, G2, G3): " + json.dumps(op.get("crypt_grates")), ""]
    L += ["**Proposed value for the plan (section 1 acceptance, S1 poses):** "
          "thin roofs: courtyard planks 4 cm (two meshes, 16 planks; the intact ones block traces: 5 of 8 on each walk), chapel slabs 20 cm, cloister lean-to panels 24.3 cm including rafters, crypt and cloister vault shells about 25 cm, stair-house roof and tower pyramid hollow shells. "
          "The project DF voxel density is 0.2 (`distanceFieldVoxelDensity`, `r.DistanceFields.DefaultVoxelDensity`), i.e. one voxel per 5 cm, so only the 4 cm planks are thinner than a voxel: they are the leak risk of R-66. "
          "Roof openings to test in S1 (rain must show there and nowhere under the roofs): the chapel hole X 6250..6750, Y -643..-193 (slab plane Z 1399..1935); the cloister N hole X 10850..11270, Y 2180..2775 (roof plane Z 640..1046) over the vault hole X 10900..11450; the tower SW collapse X 11975..12400, Y 1475..1900 (Z 3530..4400); the gaps in the two courtyard walk roofs (rectangles above); "
          "and the open garth and passage. The crypt moon grates are sealed from above by ground slabs (a trace from Z 6000 stops at Z 0), so no rain enters the crypt.", ""]
    # ------------------------------------------------------------------ 4 tower top
    t = inv.get("tower_top", {})
    L += ["## 4. Tower top", "Geometry in X 11990-13010, Y 1490-2510, highest first:", ""]
    L += _tbl(["Label", "Mesh", "Max Z", "Visible", "Collision profile"], [(q["label"], q["mesh"], q["max_z"], q["visible"], q["collision_profile"]) for q in t.get("top10", [])])
    L += ["Vertical traces from Z 8000 (collision only; the roof pieces have none): %s." % json.dumps(t.get("vertical_trace_top_z")), "Roof: %s" % json.dumps(t.get("roof")),
          "Line of sight from the P14 tower-reveal pose (600, 0, 170): %s." % json.dumps(t.get("los_from_p14_tower_reveal_pose")),
          "**Proposed value for the plan (section 3):** the highest geometry is the roof finial (`TWA_Roof`, bounds max Z %s), not the 3540 wall top that the P14 traces saw (the roof has no collision). `FX_StrikeTarget_Tower` = **%s** (finial tip estimate %s plus 20 cm; the tip X comes from the plan's 20 degree bend, so check it by eye in P15-6, +/- 15 cm). The camera at the tower-reveal pose sees it at pitch %s, yaw %s with a clear line." % (
              (t.get("roof") or {}).get("bounds_max_z"), t.get("proposed_FX_StrikeTarget_Tower"), t.get("finial_tip_estimate"),
              (t.get("los_from_p14_tower_reveal_pose") or {}).get("pitch_deg"), (t.get("los_from_p14_tower_reveal_pose") or {}).get("yaw_deg")), ""]
    # ------------------------------------------------------------------ 5 shafts
    L += ["## 5. Moonlight shafts", ""]
    L += _tbl(["Label", "Mesh", "MI", "Location", "Rotation", "Scale", "World bounds min", "World bounds max"],
              [(s["label"], s["mesh"], ",".join(x for x in s["mi"] if x), _p(s["loc"]), _p(s["rot"]), _p(s["scale"], 2), _p((s["bounds"] or {}).get("min"), 0), _p((s["bounds"] or {}).get("max"), 0)) for s in inv.get("shafts", [])])
    L += ["Proposed dust boxes (oriented box: centre, rotation of the box, half-extent along the box's own X, Y, Z):", ""]
    L += _tbl(["Shaft", "Centre", "Rotation (P, Y, R)", "Half-extent (X, Y, Z)", "Rule"],
              [(s["label"], _p((s.get("proposed_dust_box") or {}).get("centre")), _p((s.get("proposed_dust_box") or {}).get("rotation_pyr")), _p((s.get("proposed_dust_box") or {}).get("half_extent_local_axes")),
                (s.get("proposed_dust_box") or {}).get("rule", "")) for s in inv.get("shafts", [])])
    L += ["Nearest shaft card to each moon light: " + json.dumps(inv.get("shaft_nearest_to_lights")), "",
          "**Proposed value for the plan (sections 6.4 and 8):** 11 shaft actors: `Ch_Shaft_S1/S2/S3/Roof` (users of `MI_LightShaft_Window` and `_Roof`), `SA_Crypt_G1/G2/G3` and `SA_Tower_F03/F07/F08` plus `SA_Tower_Roof` (users of `MI_LightShaft_Crypt`; engine Cylinder cards). The plan's list of tower slit shafts becomes F03, F07, F08 and the roof shaft. "
          "Dust boxes as in the table; the chapel boxes follow the moon direction of `Light_Chapel_Moon_S2`; the cylinder cards are fitted at 0.55 x radius and 0.8 x half-length. The crypt and tower cylinders are thin (radius 8 to 100 cm), so `User.Count` 80 is dense there; scale it by the box volume if it looks heavy.", ""]
    # ------------------------------------------------------------------ 6 water
    L += ["## 6. Crypt water", ""]
    L += _tbl(["Label", "Mesh", "MI", "Location", "Scale", "Bounds min", "Bounds max", "Surface Z"],
              [(w["label"], w["mesh"], ",".join(x for x in w["mi"] if x), _p(w["loc"]), _p(w["scale"], 2), _p((w["bounds"] or {}).get("min")), _p((w["bounds"] or {}).get("max")), w["surface_z"]) for w in inv.get("water", [])])
    L += ["**Proposed value for the plan (sections 6.5 and 8):** `FX_WaterMist_W` at (9047.5, -2280, -593), `User.Extent` (495, 390) over `CA_Water_W` (`MI_Crypt_Water_Flood_W`); `FX_WaterMist_E` at (10002.5, -2280, -593), `User.Extent` (395, 390) over `CA_Water_E` (`MI_Crypt_Water_Flood_E`). "
          "Two more water planes exist: `CA_Water_Ledge` (`MI_Crypt_Water_Flood_Ledge`, X 9295..9805, Y -2475..-2302, Z -593) and `CA_Water_Pit` (`MI_Crypt_Water_Pit`, X 9285..9815, Y -2315..-2085, Z -650); the pit is the black still water. Mist Z 0..60 above the surface: -593..-533.", ""]
    # ------------------------------------------------------------------ 7 drips
    dr = inv.get("drips", {})
    L += ["## 7. Drip points", "### Crypt (selected, 5 over the water)", ""]
    L += _tbl(["Tag", "Over water", "Point XYZ (crown - 5)", "Collision ceiling Z (hidden shell)", "Fall height to floor / water cm", "Floor hit Z", "Nearest WalkPath seg cm", "Nearest AI point cm"],
              [(s["tag"], s["over_water"], _p(s["point"]), s["collision_ceiling_hit_z"], s["fall_height_cm"], s["floor_hit_z"], "%s (%s)" % (s["lane"]["walkpath_cm"], s["lane"]["walkpath_seg"]), "%s (%s)" % (s["lane"]["ai_point_cm"], s["lane"]["ai_point"])) for s in dr.get("crypt_selected", [])])
    L += ["### Belfry (selected)", ""]
    L += _tbl(["Tag", "Point XYZ (under the roof slate)", "Roof top Z (analytic)", "Floor hit Z", "Fall height cm", "Dist to bell frame cm", "Nearest WalkPath seg cm"],
              [(s["tag"], _p(s["point"]), s["roof_top_z_analytic"], s["floor_hit_z"], s["fall_height_cm"], s["dist_to_bell_frame_xy_cm"], "%s (%s)" % (s["lane"]["walkpath_cm"], s["lane"]["walkpath_seg"])) for s in dr.get("belfry_selected", [])])
    L += ["Candidates evaluated: crypt %d, belfry %d." % (len(dr.get("crypt_candidates", [])), len(dr.get("belfry_candidates", []))), "",
          "**Proposed value for the plan (sections 6.6 and 8):** the 8 crypt points and 2 belfry points above, with `User.FallHeight` = the 'fall height' column. Method: the crypt shell collision (a hidden flat slab at Z -40) is above the visible barrel vault, whose crown is at Z -100 on a corridor centre line (P9 portal table), so each point is on a corridor centre line at Z -105 (axes: Y -2280 for the flooded passage, X 6450 for the west corridor, Y -2350, Y -900). "
          "The visible vault is a mesh (`SM_Roof`) with no collision, so check the point against the mesh by eye; an off-axis point would sit lower. The belfry roof has no collision either: the points are under the pyramid slate computed from `TWA_Roof` (square pyramid, eaves at Z 3530 on the wall top, apex 4740), and the floor trace starts below the hidden greybox roof slab (Z 3500..3540). Lanes: every point is at least 80 cm from a WalkPath segment and 100 cm from an AI point (distances in the table).", ""]
    # ------------------------------------------------------------------ 8 eaves
    ev = inv.get("eaves", {})
    L += ["## 8. Eaves", "### Courtyard covered walks (verified against the meshes)", ""]
    for k, v in (ev.get("courtyard") or {}).items():
        pu = v.get("purlin") or {}
        L += ["- **%s walk**: claim X %s, Y %s, Z %s. Actual purlin `%s` bounds %s..%s (centre Y %s). Planks: %s, union %s..%s, lowest plank edge Z %s. Ground below the eave (3 samples): %s. Eave line: %s." % (
            k, v["claim"]["x"], v["claim"]["y"], v["claim"]["z"], pu.get("label"), _p((pu.get("bounds") or {}).get("min")), _p((pu.get("bounds") or {}).get("max")), (pu.get("loc") or [None, None])[1],
            v.get("planks"), _p((v.get("plank_union") or {}).get("min")), _p((v.get("plank_union") or {}).get("max")), (v.get("lowest_plank") or {}).get("min", [None, None, None])[2], json.dumps(v.get("ground_below_eave")), json.dumps(v.get("eave_line")))]
    L += ["", "### Cloister walk eave lines", ""]
    L += _tbl(["Walk", "Panel", "Start", "End", "Length cm", "Eave Z", "Drip side (xy)", "Ground Z below", "Fall height cm"],
              [(e["walk"], e["panel"], _p(e.get("start")), _p(e.get("end")), e.get("length_cm"), e.get("eave_z"), _p(e.get("drip_side_dir_xy")), e.get("ground_z"), e.get("fall_height_cm")) for e in ev.get("cloister", [])])
    L += [ev.get("cloister_note", ""), "",
          "**Proposed value for the plan (section 8):** the courtyard eaves are confirmed: north purlin X 2000..3000, Y 1300 (1292.5..1307.5), Z 420..435; south purlin X 4000..5000, Y -1350, Z 420..435. Use Z 435 (the purlin top; the plank edges sit 20 to 90 cm higher). Ground below is Z 0.7, so `User.FallHeight` 434. "
          "Cloister eave lines (garth side, Z 640, ground Z 100, `User.FallHeight` 540): S (11380, 1420)->(10280, 1420); N (10320, 2180)->(11360, 2180) as two panels; W (10320, 1420)->(10320, 2220); E (11380, 2180)->(11380, 1380). The N line runs under the roof hole N_2 (hole X 10850..11270), where the roof is open, so leave out X 10850..11270 of the N eave drips.", ""]
    # ------------------------------------------------------------------ 9 cloth
    cl = inv.get("cloth", {})
    L += ["## 9. Cloth hanging points (pivot = top centre, hangs down; yaw makes the cloth plane's local Y the wall normal pointing into the room)", ""]
    rows = []
    for g in ("belfry", "slits", "cloister", "gate"):
        for r in cl.get(g, []):
            rows.append((r["id"], r["mesh"].replace("SM_LB_Prop_", ""), _p(r["location"]), _p(r["rotation_pyr"]), r["bottom_z"], r["hangs_from"], "%s / %s" % (r["lane"]["walkpath_cm"], r["lane"]["ai_point_cm"]), r.get("dist_to_bell_frame_xy_cm", "")))
    L += _tbl(["Id", "Mesh", "Location (top centre)", "Rotation (P, Y, R)", "Bottom Z", "Hangs from", "WalkPath / AI point cm", "Bell frame cm"], rows)
    L += ["Slit candidates (lane clearance of the cloth centre): " + json.dumps(cl.get("slit_candidates")), "", "Arcade bay candidates: " + json.dumps(cl.get("bay_candidates")), "",
          "Gate candidates (Y; solid wall at Z 300, 450, 600; distance to the nearest ivy card in Y): " + json.dumps([{k: c[k] for k in ("y", "solid_at_z300_450_600", "dist_to_nearest_ivy_y_cm")} for c in cl.get("gate_candidates", [])]), "",
          "**Proposed value for the plan (section 8, cloth):** the 10 placements in the table (4 belfry, 2 stair slits, 3 arcade bays, 1 gate). The belfry cloths hang 6 cm inside the lancet heads (arch springs at about Z 3150) at Z 3180, more than 200 cm from the bell frame and 580 cm or more from any lane. "
          "The stair-slit cloths hang from the head of the inner splay of F03 and F07 (the two slits with moon spots and the best lane clearance, 160 cm); F08 is equal (159 cm). "
          "The arcade cloths hang in the arch plane (Y 1350 or 2250, X 10250) facing the walk; the arch intrados crown (about Z 585) is estimated from the arch ring bounds, so check the top edge by eye (+/- 15 cm). "
          "The gate cloth is on the courtyard face of the gate wall (X 300), 400 cm from the arch axis, 80 cm or more from the ivy cards. All placements clear the 60 cm WalkPath and 150 cm AI-point rules.", ""]
    # ------------------------------------------------------------------ 10 curtains
    L += ["## 10. Rain curtain cards (3000 x 2500, scale (30, 1, 25) on a 100 cm card, bottom-centre pivot, ground assumed Z 0 so bottom Z -200)", ""]
    L += _tbl(["Id", "Bottom-centre XYZ", "Rotation (P, Y, R)", "Viewpoints that see it", "Which"],
              [(q["id"], _p(q["location_bottom_centre"]), _p(q["rotation_pyr"]), q["n_views"], ", ".join(v["pose"] for v in q["views"])) for q in inv.get("curtains", [])])
    cc = inv.get("curtain_coverage", {})
    L += ["Viewpoints covered by the chosen set: %s of %s; not seen by any chosen card: %s." % (len(cc.get("viewpoints_seen_by_chosen", [])), cc.get("viewpoints_total"), cc.get("viewpoints_not_seen")),
          "Perimeter backdrop walls (800 tall): " + json.dumps({k: v["bounds"] for k, v in (inv.get("perimeter") or {}).items() if k.startswith("Perim")}), "",
          "**Proposed value for the plan (sections 6.7 and 8):** the chosen cards above. The world is a box (`Perim_W` X -3040, `Perim_E` X 13400, `Perim_N` Y 3600, `Perim_S` Y -3600; 800 tall), so cards must stand outside it: 1500 to 3000 cm beyond the courtyard wall (Y 2500) is inside the box. The proposal puts them at |Y| 4800 and X -4500 / 15200. "
          "A card is seen only when it is 3000 cm or more from the camera and within the 90 degree FOV, so the viewpoints that look along the walls (gate, interiors, crypt) never see a curtain; the coverage line shows which ones do.", ""]
    # ------------------------------------------------------------------ 11 sky
    sk = inv.get("sky", {})
    L += ["## 11. Sky", ""]
    for d in sk.get("dome_actors", []):
        L += ["Dome `%s` (%s, mesh %s, MI %s): location %s, scale %s, mesh local bounds %s, **radius %.0f cm**." % (d["label"], d["class"], d["mesh"], d["mi"], _p(d["loc"]), _p(d["scale"]), d["mesh_local_bounds"], d["radius_cm"]), ""]
    sb = sk.get("sky_bolt") or {}
    L += ["Sky bolt check: 0.6 x radius = %.0f cm, capped at 60000 -> **%.0f cm**. Worst bolt top (16 viewpoints x 16 directions, +22000 cm up) is %s cm from the dome centre, %s cm inside the dome." % (0.6 * sb.get("radius_cm", 0), sb.get("proposed_distance_cm", 0), sb.get("worst_top_point_to_centre_cm"), sb.get("margin_cm")), ""]
    for f in sk.get("fog", []):
        L += ["Fog `%s` at %s: %s" % (f["label"], _p((f["xf"] or {}).get("loc")), json.dumps(f["props"])), ""]
    fe = sk.get("fog_estimate") or {}
    L += ["Fog estimate: " + json.dumps(fe), "Local fog volumes in the level: %s (ground level; they do not reach the sky)." % sk.get("local_fog_volumes"), "",
          "**Proposed value for the plan (section 2.2):** `SkyBoltDistance` = **60000 cm** (the cap; 0.6 x radius would be 983040). The dome (`SkySphere`, `SM_SkySphere` at scale 400) has a radius of 1638400 cm, so a bolt at 60000 cm and 22000 cm up is deep inside it. "
          "Fog: `ExponentialHeightFog` density 0.035, height falloff 0.35, max opacity 0.95, start distance 0, cutoff 1000000 (so it does fog everything up to the dome). By the estimate above a ray to a bolt 60000 cm away keeps about 49 % of the light from a ground-level camera (68 % from the belfry), with inscattering tint (0.026, 0.030, 0.038); a bolt material with Apply Fogging off ignores the fog, so the bolt is not hidden. "
          "Volumetric fog reaches only 3000 cm. `SkyAtmosphere_1` is hidden (MCP_NOTES).", ""]
    # ------------------------------------------------------------------ 12 niagara
    L += ["## 12. Niagara MCP tools", "See `Docs/ArtTest/fx/p15_f0_niagara_tools.md` (tool list, argument schemas and the capability answers). Toolsets: " + ", ".join(inv.get("niagara_toolsets", [])), ""]
    # ------------------------------------------------------------------ 13 DF
    dfp = inv.get("distance_fields_project", {})
    rs = dfp.get("renderer_settings", {})
    cv = dfp.get("cvars", {})
    L += ["## 13. Distance fields", "Renderer settings (`/Script/Engine.Default__RendererSettings`): " + json.dumps(rs), "",
          "Selected console variables: " + json.dumps({k: cv.get(k) for k in ("r.GenerateMeshDistanceFields", "r.DistanceFields.DefaultVoxelDensity", "r.DistanceFields.MaxPerMeshResolution", "r.DistanceFieldAO", "r.AOGlobalDistanceField", "r.AOGlobalDistanceField.NumClipmaps",
                                                                                    "r.Lumen.HardwareRayTracing", "r.Lumen.TraceMeshSDFs", "r.Lumen.TraceMeshSDFs.Allow", "r.LumenScene.GlobalSDF.ClipmapExtent", "fx.NiagaraAllowGPUParticles", "fx.Niagara.Collision.CPUEnabled")}), "",
          "**Proposed value for the plan (R-66, R-69):** mesh distance fields are generated (`bGenerateMeshDistanceFields` true, `r.GenerateMeshDistanceFields` 1), voxel density 0.2 (5 cm). The global distance field cvars are on (`r.AOGlobalDistanceField` 1, 4 clipmaps, `r.DistanceFieldAO` 1; the Movable SkyLight casts shadows, which uses it). Lumen runs with hardware ray tracing (`bUseHardwareRayTracingForLumen` true, `r.Lumen.TraceMeshSDFs` 0), "
          "so Lumen itself does not ask for the global SDF, and MCP_NOTES records `DistanceToNearestSurface` returning about 0 here. Nothing in the settings proves that the GDF holds real data at runtime; S1 must test it (a Niagara GPU emitter that uses the field normally forces it on). No per-mesh DF override exists on any roof mesh. The `fx.*` cvars found are `fx.NiagaraAllowGPUParticles` 1 and `fx.Niagara.Collision.CPUEnabled` 1.", ""]
    # ------------------------------------------------------------------ 14 census
    c = inv.get("census", {})
    L += ["## 14. Census", "**%s actors** in the editor world (`find_actors` with an empty name and tag, the P14-3 method; P14's final count was also 3015). **Proposed value for the plan:** P15-6 start = %s; the final check expects %s plus the new actors (about 55: 1 target, 11 dust, 2 water mist, 10 drips, 7 eave drips, 10 cloth, 8 curtains)." % (c.get("count"), c.get("count"), c.get("count")), ""]
    L += _tbl(["Class", "Count"], list(c.get("by_class", {}).items())[:40])
    if inv.get("errors"):
        L += ["## Call errors", ""]
        L += _tbl(["Context", "Tool", "Error"], [(e["ctx"].rsplit("/", 1)[-1], e["tool"], e["error"][:200]) for e in inv["errors"]])
        L += ["The `Saint1..4Flame` entries are templates of `BP_StainedGlassClue_Saints`: the components are declared in the parent `BP_StainedGlassClue`, so the `_Saints_C:..._GEN_VARIABLE` path does not exist. The parent's own templates are read in the 'Blueprint assets' table.", ""]
    with open(os.path.join(OUT_DIR, "p15_f0_tables.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L))
    print("wrote tables")


ORDER = ["lanes", "bp_actors", "flames", "fires", "sky", "dfsettings", "water", "shafts", "tower_top", "roofs", "openings", "eaves", "drips", "cloth", "curtains", "niagara"]
DEPS = {"flames": ["bp_actors"], "fires": ["bp_actors"], "openings": ["shafts", "roofs"], "eaves": ["roofs"], "drips": ["lanes", "water", "roofs"],
        "cloth": ["lanes", "drips"], "curtains": [], "tower_top": [], "roofs": []}


def run_stages(args):
    global CACHE
    if args.cache:
        CACHE = os.path.join(ROOT, "Saved", args.cache)
    sv = Survey(args.resume)
    inv = {"plan": "Docs/plans/P15_PARTICLES.md (F0)", "tool": "Tools/fx/p15_f0_survey.py"}
    want = [x for x in args.stages.split(",") if x]
    if want == ["niagara"]:
        niagara(sv, inv)
        return sv, inv
    refs = census(sv, inv)
    SMA = smascan(sv, inv, refs)
    run = set(want or ORDER)
    for s in list(run):
        run.update(DEPS.get(s, []))
        for d in DEPS.get(s, []):
            run.update(DEPS.get(d, []))
    BPA = None
    for name in ORDER:
        if name not in run:
            continue
        fn = globals()[name]
        if name == "bp_actors":
            BPA = fn(sv, inv, refs, SMA)
        elif name in ("flames", "fires"):
            fn(sv, inv, refs, SMA, BPA)
        elif name == "niagara":
            fn(sv, inv)
        else:
            fn(sv, inv, refs, SMA)
    inv["header"]["dirty_after"] = sv.call(AS, "is_dirty", {"asset_path": MAP_PKG})
    inv["header"]["calls"] = sv.calls
    inv["header"]["seconds"] = round(time.time() - sv.t0)
    inv["errors"] = sv.errors
    inv["sma_summary"] = {"count": len(SMA), "top_meshes": dict(Counter(v["mesh"] for v in SMA.values()).most_common(25))}
    os.makedirs(OUT_DIR, exist_ok=True)
    if not want:
        with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
            json.dump(inv, f, indent=1)
        sv.log("wrote %s (%d call errors); map dirty before=%s after=%s" % (OUT_JSON, len(sv.errors), inv["header"]["dirty_before"], inv["header"]["dirty_after"]))
        write_tables(inv)
    return sv, inv


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--stages", default="", help="comma list; empty = every stage and write the outputs")
    ap.add_argument("--cache", default="", help="cache file name under Saved/ (default p15_f0_cache.jsonl)")
    ap.add_argument("--tables", action="store_true", help="only rebuild p15_f0_tables.md from p15_f0.json (no editor contact)")
    a = ap.parse_args()
    if a.tables:
        write_tables(json.load(open(OUT_JSON, encoding="utf-8")))
    else:
        run_stages(a)
