"""P16-F0: the read-only survey for Phase 16 (Docs/plans/P16_AUDIO.md section 7, items 1 to 8).

Run with the editor open on L_Monastery, PIE off (Windows Python; from Git Bash prefix MSYS_NO_PATHCONV=1):
    python -I Tools/audio/p16_f0_survey.py [--refresh] [--only state,interactables,bells,areas,floors,bell,warden,config,mcp]

Outputs: Docs/ArtTest/audio/p16_f0.json (all data) and p16_f0_tables.md (the tables for the plan).

READ ONLY. The script never sets, creates, deletes, saves or moves anything: it calls only get_*, find_*, is_*, list_*, search_*,
exists, IsPIERunning, trace_world and describe_toolset. It never starts PIE. The dirty state of L_Monastery and of the never-save list
(p15_level.NEVER_SAVE) is read before and after, and the actor census is compared; the run fails (exit 2) if anything changed.

Each stage caches its result in Saved/p16_f0_scratch/<stage>.json (git-ignored); --refresh ignores the cache. The committed outputs
are always built from a full --refresh run.

If the editor drops the connection or hangs for more than 180 s the script stops ("STOP", exit code 3) and writes nothing.
"""
import argparse
import json
import math
import os
import re
import sys
import time
from collections import Counter, OrderedDict

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Tools", "lighting"))
sys.path.insert(0, os.path.join(ROOT, "Tools", "fx"))
sys.path.insert(0, os.path.join(ROOT, "Tools", "mcp"))
import p14_3_level as L  # noqa: E402  (Ed client, EditorStop, helpers)
import p15_level as P15  # noqa: E402  (NEVER_SAVE)
from p14_3_level import EditorStop, J, R, v3  # noqa: E402

S, A, O, AS, E = L.S, L.A, L.O, L.AS, L.E
BPT = "editor_toolset.toolsets.blueprint.BlueprintTools"
SMT = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
MAP_PKG = L.MAP_PKG
NEVER_SAVE = list(P15.NEVER_SAVE)
SCRATCH = os.path.join(ROOT, "Saved", "p16_f0_scratch")
OUT_DIR = os.path.join(ROOT, "Docs", "ArtTest", "audio")
OUT_JSON = os.path.join(OUT_DIR, "p16_f0.json")
OUT_MD = os.path.join(OUT_DIR, "p16_f0_tables.md")
MAPPFX = "/Game/LastBell/Maps/L_Monastery.L_Monastery:PersistentLevel."
CAPTURE = sys.stdout


def say(msg):
    print(msg, flush=True)


def rr(v, n=1):
    return [round(float(x), n) for x in v]


def rname(x):
    r = R(x)
    return r.rsplit(".", 1)[-1] if r else None


def objname(ref):
    return ref.rsplit(".", 1)[-1] if ref else None


def tags_of(x):
    """GameplayTagContainer / GameplayTag / array of tags as a list of names."""
    if not x:
        return []
    if isinstance(x, dict):
        if "gameplayTags" in x:
            return [t.get("tagName") for t in x["gameplayTags"] if t.get("tagName")]
        if "tagName" in x:
            return [x["tagName"]] if x["tagName"] and x["tagName"] != "None" else []
    if isinstance(x, list):
        out = []
        for t in x:
            out += tags_of(t)
        return out
    return []


# ---------------------------------------------------------------------------------------------- stage cache
class Cache:
    def __init__(self, refresh):
        self.refresh = refresh
        os.makedirs(SCRATCH, exist_ok=True)

    def get(self, name, fn):
        path = os.path.join(SCRATCH, name + ".json")
        if not self.refresh and os.path.exists(path):
            say("cache  %s (%s)" % (name, path))
            return json.load(open(path, encoding="utf-8"))
        t0 = time.time()
        say("stage  %s ..." % name)
        data = fn()
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, indent=1)
        say("stage  %s done in %.0f s" % (name, time.time() - t0))
        return data


# ---------------------------------------------------------------------------------------------- helpers on the editor client
class Ed(L.Ed):
    """p14_3_level.Ed plus the read-only calls this survey needs (nothing here mutates)."""

    def cls(self, ref):
        return R(self.call(O, "get_class", {"instance": {"refPath": R(ref)}}))

    def comps(self, ref):
        return [R(x) for x in self.call(A, "get_components", {"actor": {"refPath": R(ref)}}) or []]

    def xf_full(self, ref):
        loc, rot, sc = self.xform(ref)
        return {"location": rr(loc, 2), "rotation": rr(rot, 3), "scale": rr(sc, 4)}

    def find_cls(self, cls_path):
        return [R(x) for x in self.call(S, "find_actors", {"name": "", "tag": "", "collision_channels": [], "actor_type": {"refPath": cls_path}}) or []]

    def find_name(self, text):
        return [R(x) for x in self.call(S, "find_actors", {"name": text, "tag": "", "collision_channels": []}) or []]

    def find_box(self, lo, hi, channels=None):
        box = {"min": L.vec(lo), "max": L.vec(hi), "isValid": True}
        return [R(x) for x in self.call(S, "find_actors", {"name": "", "tag": "", "collision_channels": channels or [], "bounds": box}) or []]

    def trace_z(self, x, y, z0, z1):
        """Vertical line trace via SceneTools.trace_world (read only). Returns the hit Z or None."""
        d = self.call(S, "trace_world", {"start": L.vec((x, y, z0)), "end": L.vec((x, y, z1))})
        if d is None:
            return None
        return z0 + (d if z1 > z0 else -d)

    def bp_parent(self, class_path):
        """Parent class of a Blueprint generated class (read only); None for a native class."""
        if not class_path or class_path.startswith("/Script/"):
            return None
        bp = class_path[:-2] if class_path.endswith("_C") else class_path
        try:
            return R(self.call(BPT, "get_parent", {"blueprint": {"refPath": bp}}))
        except RuntimeError:
            return None

    def chain(self, class_path, cache):
        if class_path in cache:
            return cache[class_path]
        out = [class_path]
        cur = class_path
        for _ in range(8):
            par = self.bp_parent(cur)
            if not par:
                break
            out.append(par)
            cur = par
        cache[class_path] = out
        return out


def short(cls_path):
    return cls_path.rsplit(".", 1)[-1] if cls_path else None


# ---------------------------------------------------------------------------------------------- state (before / after)
def read_state(ed):
    st = {"pie_running": bool(ed.call(E, "IsPIERunning")), "level": str(ed.call(S, "get_current_level", {})),
          "map_dirty": bool(ed.is_dirty(MAP_PKG)), "never_save_dirty": {}}
    for pkg in NEVER_SAVE:
        st["never_save_dirty"][pkg] = bool(ed.is_dirty(pkg))
    st["actor_count"] = len(ed.find_all())
    return st


def state_clean(st):
    return (not st["pie_running"] and st["level"].startswith(MAP_PKG) and not st["map_dirty"] and not any(st["never_save_dirty"].values()))


# ---------------------------------------------------------------------------------------------- 1. interactables
LB_COMP = {"/Script/LastBell.LBInteractableComponent": "interactable", "/Script/LastBell.LBDialComponent": "dial",
           "/Script/LastBell.LBSequencePuzzleComponent": "sequence"}
SKIP_CLASS_PARTS = ("/Menu/", "BP_LBPlayerController", "BP_LBCharacter", "BP_LBGameMode", "/AI/BP_Warden.", "BP_WardenApparition")
MESH_COMPS = ("/Script/Engine.StaticMeshComponent", "/Script/Engine.InstancedStaticMeshComponent")


def comp_props(ed, ref, kind):
    if kind == "interactable":
        p = ed.props(ref, ["PromptText", "DeniedPromptText", "bEnabled", "RequiredStateTags", "GrantedStateTags", "bSingleUse", "ConsumedStateTag",
                           "bInspectOnInteract", "NoiseLoudness"])
        return {"prompt": p.get("PromptText"), "denied_prompt": p.get("DeniedPromptText"), "enabled": p.get("bEnabled"),
                "required_tags": tags_of(p.get("RequiredStateTags")), "granted_tags": tags_of(p.get("GrantedStateTags")),
                "single_use": p.get("bSingleUse"), "consumed_tag": tags_of(p.get("ConsumedStateTag")), "inspect_on_interact": p.get("bInspectOnInteract"),
                "noise_loudness": round(float(p.get("NoiseLoudness") or 0), 3)}
    if kind == "dial":
        p = ed.props(ref, ["PositionTags", "InitialIndex", "bLocked"])
        return {"position_tags": tags_of(p.get("PositionTags")), "initial_index": p.get("InitialIndex"), "locked": p.get("bLocked")}
    p = ed.props(ref, ["Steps", "SolvedTags"])
    return {"steps": tags_of(p.get("Steps")), "solved_tags": tags_of(p.get("SolvedTags"))}


def stage_interactables(ed):
    classes = [R(x) for x in ed.call(O, "search_subclasses", {"base_class": {"refPath": "/Script/Engine.Actor"}, "class_name": "LastBell"}) or []]
    scan = [c for c in classes if c.startswith("/Game/LastBell/Blueprints/") and not any(s in c for s in SKIP_CLASS_PARTS)]
    say("  %d actor classes under /Game/LastBell/Blueprints to scan (of %d LastBell actor classes)" % (len(scan), len(classes)))
    actors = OrderedDict()
    for c in scan:
        for r in ed.find_cls(c):
            actors.setdefault(r, c)
    say("  %d placed actors of those classes" % len(actors))
    chains = {}
    recs = []
    for i, ref in enumerate(actors):
        comps = ed.comps(ref)
        lb = []
        meshes = []
        for c in comps:
            k = ed.cls(c)
            if k in LB_COMP:
                lb.append((c, LB_COMP[k]))
            elif k in MESH_COMPS and len(meshes) < 12:
                meshes.append(c)
        if not lb:
            continue
        cls = ed.cls(ref)
        rec = {"label": ed.label(ref), "object": objname(ref), "class": short(cls), "class_path": cls,
               "parent_chain": [short(x) for x in ed.chain(cls, chains)] + ["Actor"], "components": {}, "meshes": []}
        rec.update(ed.xf_full(ref))
        b = ed.bounds(ref)
        rec["bounds_min"], rec["bounds_max"] = rr(b[0], 1), rr(b[1], 1)
        for c, kind in lb:
            rec["components"][objname(c)] = dict(kind=kind, **comp_props(ed, c, kind))
        for c in meshes:
            p = ed.props(c, ["staticMesh", "overrideMaterials", "relativeScale3D", "bVisible"])
            rec["meshes"].append({"component": objname(c), "mesh": rname(p.get("staticMesh")), "materials": [rname(m) for m in p.get("overrideMaterials") or []],
                                  "rel_scale": rr(v3(p["relativeScale3D"]), 3), "visible": p.get("bVisible")})
        if "SmallBell" in cls:
            rec["bell_scale_var"] = ed.props(ref, ["bellScale"]).get("bellScale")
        recs.append(rec)
        say("  [%d/%d] %s (%s)" % (i + 1, len(actors), rec["label"], rec["class"]))
    return {"scanned_classes": [short(c) for c in scan], "actors": recs}


# ---------------------------------------------------------------------------------------------- 3. areas (volumes and anchors)
ANCHOR_QUERIES = [("Gate", 40), ("KD_", 60), ("Belfry", 40), ("Tw_Floor", 20), ("TWA_Roof", 10), ("CA_Water", 10), ("Stair_F11", 20), ("Stair_F10", 20)]
# upward traces from head height: is there a roof (the first hit above the point), or open sky? (name, x, y, start z)
ROOF_CHECKS = [("wellhouse centre", 1500, -2000, 100), ("wellhouse N gap", 1500, -1800, 100), ("gate arch", 150, 0, 100), ("gate arch N side", 150, 300, 100),
               ("gatehouse light", 340, 560, 100), ("courtyard", 3000, 0, 100), ("chapel nave", 7500, 0, 100), ("chapel sacristy", 8300, -1250, 100),
               ("passage", 7500, 1800, 100), ("passage W", 6500, 2000, 100), ("passage E", 9200, 1500, 100), ("cloister S walk", 10000, 800, 100),
               ("cloister N walk", 10000, 2700, 100), ("garth", 10800, 1800, 200), ("tower base", 12500, 2000, 100), ("tower stair landing 5", 12835, 2335, 1300),
               ("belfry", 12500, 2000, 2600), ("belfry E side", 12900, 2000, 2600), ("crypt W", 7200, -2350, -500), ("crypt water", 9047, -2280, -500),
               ("crypt E", 11000, -1500, -500)]


def stage_areas(ed):
    out = {"post_process": [], "storm_zones": [], "anchors": {}}
    seen = set()
    for q in ("PP_", "PostProcess_"):
        for r in ed.find_name(q):
            lab = ed.label(r)
            if not lab.startswith(q) or r in seen:
                continue
            seen.add(r)
            p = ed.props(r, ["priority", "blendRadius", "bUnbound", "bEnabled"])
            b = ed.bounds(r)
            rec = {"label": lab, "object": objname(r), "priority": p["priority"], "blend_radius": p["blendRadius"], "unbound": p["bUnbound"],
                   "enabled": p.get("bEnabled")}
            rec.update(ed.xf_full(r))
            rec["bounds_min"], rec["bounds_max"] = rr(b[0], 1), rr(b[1], 1)
            out["post_process"].append(rec)
            say("  PP   %s bounds %s..%s" % (lab, rec["bounds_min"], rec["bounds_max"]))
    for r in ed.find_cls("/Script/LastBell.LBStormZone"):
        lab = ed.label(r)
        p = ed.props(r, ["exposure", "priority"])
        ext = v3(ed.props(r + ".Box", ["boxExtent"])["boxExtent"])
        rec = {"label": lab, "object": objname(r), "exposure": p["exposure"], "priority": p["priority"], "box_extent": rr(ext, 1)}
        rec.update(ed.xf_full(r))
        loc, sc = rec["location"], rec["scale"]
        rec["bounds_min"] = rr([loc[i] - ext[i] * sc[i] for i in range(3)], 1)
        rec["bounds_max"] = rr([loc[i] + ext[i] * sc[i] for i in range(3)], 1)
        out["storm_zones"].append(rec)
        say("  SZN  %s bounds %s..%s exposure %s priority %s" % (lab, rec["bounds_min"], rec["bounds_max"], p["exposure"], p["priority"]))
    for q, cap in ANCHOR_QUERIES:
        lst = []
        for r in ed.find_name(q)[:cap]:
            b = ed.bounds(r)
            lst.append({"label": ed.label(r), "object": objname(r), "bounds_min": rr(b[0], 1), "bounds_max": rr(b[1], 1)})
        out["anchors"][q] = lst
        say("  anchors %r: %d" % (q, len(lst)))
    out["roof_checks"] = []
    for name, x, y, z0 in ROOF_CHECKS:
        up = ed.trace_z(x, y, z0, z0 + 3000.0)
        # Roofs are art meshes with NoCollision in this level, so an upward trace only sees the greybox shells: also list the actors overhead by bounds.
        over = []
        for r in ed.find_box((x - 10, y - 10, z0 + 5), (x + 10, y + 10, z0 + 2500)):
            on = objname(r)
            if on.startswith(NOT_FLOOR_PREFIXES):
                continue
            b = ed.bounds(r)
            if max(b[1][k] - b[0][k] for k in range(3)) > 100000 or b[0][2] < z0 - 1:
                continue
            lab = ed.label(r)
            if lab.startswith(("Ivy_", "FX_", "LFV_", "Light_", "PP_", "SZN_", "RV_", "Crack_", "PCG")):
                continue
            over.append({"label": lab, "bottom_z": round(b[0][2], 1), "top_z": round(b[1][2], 1)})
        over.sort(key=lambda o: o["bottom_z"])
        out["roof_checks"].append({"name": name, "xy": [x, y], "from_z": z0, "first_hit_above_z": None if up is None else round(up, 1),
                                   "clearance_cm": None if up is None else round(up - z0, 1), "overhead_actors": over[:6]})
        say("  roof %-22s from z %6s: trace %s; overhead %s" % (name, z0, "open" if up is None else "z %.1f" % up, [o["label"] for o in over[:3]]))
    return out


# ---------------------------------------------------------------------------------------------- 4. floors
PLAYER_HALF_HEIGHT = 88.0          # BP_LBCharacter CDO CollisionCylinder.capsuleHalfHeight (read live in the stage)
FOOTSTEP_EXTRA = 30.0              # DA_PlayerTuning.FootstepTraceExtraDepth (read live in the stage)
NOT_FLOOR_PREFIXES = ("NavMeshBoundsVolume", "RecastNavMesh", "LBStormZone", "PostProcessVolume", "NiagaraActor", "LocalFogVolume", "PointLight",
                      "SpotLight", "RectLight", "DecalActor", "TriggerVolume", "PCGV", "PCGVolume", "LBAudio", "TargetPoint", "LBWarden", "LBCheckpoint",
                      "Emitter", "SkyLight", "ExponentialHeightFog", "DirectionalLight", "LBStateLightGroup", "LBAmbient", "LBPatrol", "LBSearch")

# (area, floor Z estimate, points). Hand-picked points follow the routes; the Warden markers (patrol, search, spawn) are added from the level.
HAND_POINTS = [
    ("courtyard", 0, [(800, 0), (1500, 300), (2000, -600), (2500, 0), (3000, 800), (3500, -300), (4000, 400), (4500, -800), (5000, 0), (5300, 300),
                      (2200, 1500), (3400, -1600), (4400, 1700), (1000, -1200), (5200, -1500)]),
    ("approach", 0, [(-2800, 100), (-2200, 600), (-1600, -500), (-1000, 200), (-600, -300), (-200, 0), (0, 400), (150, -200)]),
    ("gatehouse", 0, [(340, 560), (340, -145), (400, 300), (250, -300), (330, 100), (350, -500)]),
    ("wellhouse", 0, [(1500, -2000), (1400, -1900), (1600, -2100), (1500, -1850)]),
    ("chapel", 0, [(6300, 0), (6700, -300), (7000, 300), (7500, 0), (7800, -400), (8200, 300), (8600, 0), (8900, -300), (8800, 500), (6500, 500),
                   (7000, -1100), (8300, -1250), (8500, -1100), (6300, -1200)]),
    ("crypt", -600, [(6500, -1100), (6800, -1500), (7200, -2350), (7800, -2350), (8700, -2300), (9550, -2380), (9550, -2200), (10400, -2250),
                     (11000, -2300), (11150, -1500), (10250, -900), (9500, -600), (7700, -300), (6600, -200)]),
    ("cloister_walk", 0, [(9800, 800), (10400, 900), (11000, 800), (11600, 900), (9800, 2700), (10400, 2700), (11000, 2600), (11600, 2700),
                          (9900, 1500), (9900, 2100), (11800, 1500), (11800, 2100)]),
    ("garth", 100, [(10500, 1600), (10800, 1800), (11200, 2000), (10700, 2100), (11000, 1500), (10400, 2000)]),
    ("passage", 0, [(6300, 2000), (6800, 1900), (7300, 1500), (7800, 2100), (8300, 1700), (8800, 2000), (9200, 1500), (9300, 2300), (7000, 2400), (8500, 1200)]),
    ("tower_base", 0, [(12300, 1800), (12600, 2100), (12500, 1700), (12800, 2000)]),
    ("belfry", 2500, [(12200, 1700), (12700, 2300), (12500, 2000), (12300, 2300), (12800, 1700), (12100, 2100)]),
    ("crypt_water", -593, [(9047, -2280), (9550, -2390), (9550, -2200), (10000, -2280), (8900, -2150), (10100, -2400)]),
]
# landing centres (Tw_Landing_01..10 greybox boxes; tops 227, 455, 682, 909, 1136, 1364, 1591, 1818, 2045, 2273 from the level)
LANDING_TOPS = [227, 455, 682, 909, 1136, 1364, 1591, 1818, 2045, 2273]
LANDING_XY = [(12835, 2335), (12835, 1665), (12165, 1665), (12165, 2335), (12835, 2335), (12835, 1665), (12165, 1665), (12165, 2335), (12835, 2335), (12835, 1665)]


def marker_area(loc):
    if loc[2] < -300:
        return "crypt"
    if loc[0] >= 11990:
        return "tower_base"
    if 9460 <= loc[0] <= 12040 and loc[1] > 500:
        return "cloister_walk"
    if 6000 <= loc[0] <= 9100 and loc[1] < 860:
        return "chapel"
    if 6040 <= loc[0] < 9460 and loc[1] >= 900:
        return "passage"
    return "outdoors"


def sample_points(ed):
    pts = []
    counts = Counter()
    for area, z, lst in HAND_POINTS:
        for (x, y) in lst:
            counts[area] += 1
            pts.append({"id": "%s_%02d" % (area, counts[area]), "area": area, "source": "hand", "xy": [x, y], "z_est": z})
    for i, (xy, top) in enumerate(zip(LANDING_XY, LANDING_TOPS)):
        pts.append({"id": "landing_%02d" % (i + 1), "area": "tower_landing", "source": "landing", "xy": list(xy), "z_est": top})
    for i in range(9):
        a, b = LANDING_XY[i], LANDING_XY[i + 1]
        pts.append({"id": "stair_%02d_%02d" % (i + 1, i + 2), "area": "tower_stair", "source": "stair_mid", "xy": [round((a[0] + b[0]) / 2), round((a[1] + b[1]) / 2)],
                    "z_est": round((LANDING_TOPS[i] + LANDING_TOPS[i + 1]) / 2)})
    for cls, tag in (("/Script/LastBell.LBWardenSpawnPoint", "spawn"), ("/Script/LastBell.LBPatrolPoint", "patrol"), ("/Script/LastBell.LBSearchPoint", "search")):
        for r in ed.find_cls(cls):
            loc = ed.xform(r)[0]
            pts.append({"id": "%s_%s" % (tag, ed.label(r)), "area": marker_area(loc), "source": tag, "xy": [round(loc[0]), round(loc[1])], "z_est": round(loc[2])})
    return pts


def mesh_info(ed, comp, cache):
    if comp in cache:
        return cache[comp]
    p = ed.props(comp, ["staticMesh", "overrideMaterials", "bVisible", "bHiddenInGame", "bodyInstance"])
    bi = p.get("bodyInstance") or {}
    mesh = R(p.get("staticMesh"))
    mats = [R(m) for m in p.get("overrideMaterials") or []]
    mat_src = "override"
    if not mats and mesh:
        mat_src = "mesh_default"
        try:
            sl = ed.call(SMT, "get_material_slots", {"mesh": {"refPath": mesh}})
            mats = []
            for i in range(len(sl or [])):
                try:
                    m = R(ed.call(SMT, "get_material", {"mesh": {"refPath": mesh}, "slot": sl[i]}))
                except RuntimeError:
                    m = "slot:" + str(sl[i])
                mats.append(m)
        except RuntimeError:
            mats = []
    phys = []
    for m in mats:
        if m and m.startswith("/"):
            try:
                pm = ed.props(m, ["physMaterial"]).get("physMaterial")
                phys.append(R(pm) if pm and pm != "None" else None)
            except RuntimeError:
                phys.append("unreadable")
        else:
            phys.append(None)
    po = bi.get("physMaterialOverride")
    info = {"mesh": mesh, "materials": mats, "material_source": mat_src, "material_phys": phys, "visible": p.get("bVisible"), "hidden_in_game": p.get("bHiddenInGame"),
            "collision_profile": bi.get("collisionProfileName"), "collision_enabled": bi.get("collisionEnabled"),
            "phys_material_override": None if po in (None, "None") else (R(po) or po)}
    cache[comp] = info
    return info


def pick_hit_actor(ed, x, y, hz, actor_cache):
    """The actor the trace hit: of the collidable actors whose bounds contain the hit point, the one whose top is nearest to it."""
    lo, hi = (x - 0.75, y - 0.75, hz - 0.75), (x + 0.75, y + 0.75, hz + 0.75)
    refs = ed.find_box(lo, hi, ["ObjectTypeQuery1", "ObjectTypeQuery2"])
    cands = []
    for r in refs:
        on = objname(r)
        if on.startswith(NOT_FLOOR_PREFIXES):
            continue
        if r not in actor_cache:
            b = ed.bounds(r)
            actor_cache[r] = {"label": ed.label(r), "object": on, "bmin": rr(b[0], 2), "bmax": rr(b[1], 2)}
        a = actor_cache[r]
        if max(a["bmax"][i] - a["bmin"][i] for i in range(3)) > 100000:
            continue
        if a["bmin"][2] - 0.3 <= hz <= a["bmax"][2] + 0.3 and a["bmin"][0] - 1 <= x <= a["bmax"][0] + 1 and a["bmin"][1] - 1 <= y <= a["bmax"][1] + 1:
            cands.append((abs(a["bmax"][2] - hz), r))
    cands.sort()
    return (cands[0][1] if cands else None), [actor_cache[r]["label"] for _, r in cands]


def process_point(ed, p, actor_cache, comp_cache, comp_of):
    """One sample: probe trace, the exact footstep trace, the hit actor and its component data. Read only."""
    x, y = p["xy"]
    z0 = p["z_est"] + 150.0
    hz = ed.trace_z(x, y, z0, p["z_est"] - 300.0)
    row = dict(p)
    row["probe_hit_z"] = None if hz is None else round(hz, 2)
    if hz is None or z0 - hz < 3.0:
        row["status"] = "no_floor" if hz is None else "start_inside_geometry"
        return row
    # the exact footstep trace: start at the capsule centre, end HalfHeight + extra below it, on the floor the probe found
    s_z = hz + PLAYER_HALF_HEIGHT
    e_z = s_z - (PLAYER_HALF_HEIGHT + FOOTSTEP_EXTRA)
    fz = ed.trace_z(x, y, s_z, e_z)
    row["footstep_hit_z"] = None if fz is None else round(fz, 2)
    row["footstep_hit"] = fz is not None and abs(fz - hz) < 1.0
    r, cands = pick_hit_actor(ed, x, y, hz, actor_cache)
    row["candidates"] = cands
    if not r:
        row["status"] = "hit_actor_not_resolved"
        return row
    a = actor_cache[r]
    row.update({"actor_label": a["label"], "actor_object": a["object"], "actor_bounds_min": a["bmin"], "actor_bounds_max": a["bmax"]})
    if r not in comp_of:
        comps = ed.comps(r)
        meshc = [c for c in comps if ed.cls(c) in MESH_COMPS]
        infos = [(c, mesh_info(ed, c, comp_cache)) for c in meshc[:4]]
        comp_of[r] = {"class": short(ed.cls(r)), "infos": infos}
    cl = comp_of[r]
    coll = [(c, inf) for c, inf in cl["infos"] if inf["collision_enabled"] not in ("NoCollision", None)]
    c, inf = (coll or cl["infos"] or [(None, None)])[0]
    row["actor_class"] = cl["class"]
    if inf:
        row["component"] = objname(c)
        row.update({k: inf[k] for k in ("mesh", "materials", "material_source", "material_phys", "visible", "hidden_in_game", "collision_profile",
                                        "collision_enabled", "phys_material_override")})
        mesh = inf["mesh"] or ""
        row["greybox_or_collision"] = bool(inf["visible"] is False or inf["hidden_in_game"] or mesh.startswith("/Engine/BasicShapes"))
        row["greybox_reason"] = ("hidden shell (bVisible false)" if inf["visible"] is False else "BasicShapes primitive" if mesh.startswith("/Engine/BasicShapes") else
                                 "hidden in game" if inf["hidden_in_game"] else "art mesh")
    row["status"] = "ok"
    return row


def stage_floors(ed):
    global PLAYER_HALF_HEIGHT, FOOTSTEP_EXTRA
    base = "/Game/LastBell/Blueprints/BP_LBCharacter.Default__BP_LBCharacter_C"
    PLAYER_HALF_HEIGHT = float(ed.props(base + ":CollisionCylinder", ["capsuleHalfHeight"])["capsuleHalfHeight"])
    tun = ed.props("/Game/LastBell/Data/DA_PlayerTuning.DA_PlayerTuning", ["bFootstepTraceComplex", "FootstepTraceExtraDepth"])
    FOOTSTEP_EXTRA = float(tun["FootstepTraceExtraDepth"])
    say("  capsule half height %s, extra depth %s, complex %s" % (PLAYER_HALF_HEIGHT, FOOTSTEP_EXTRA, tun["bFootstepTraceComplex"]))
    pts = sample_points(ed)
    say("  %d sample points" % len(pts))
    actor_cache, comp_cache, comp_of = {}, {}, {}
    rows = []
    for i, p in enumerate(pts):
        row = process_point(ed, p, actor_cache, comp_cache, comp_of)
        rows.append(row)
        say("  [%d/%d] %s: %s z %s %s" % (i + 1, len(pts), p["id"], row["status"], row["probe_hit_z"], row.get("actor_label", "")))
    return {"player_half_height": PLAYER_HALF_HEIGHT, "footstep_extra_depth": FOOTSTEP_EXTRA, "footstep_trace_complex": tun["bFootstepTraceComplex"],
            "samples": rows}


# ---------------------------------------------------------------------------------------------- 4b. floors, second pass (reads the first pass; read only)
PRIM_COMPS = ("/Script/Engine.BoxComponent", "/Script/Engine.BrushComponent", "/Script/Engine.SphereComponent", "/Script/Engine.CapsuleComponent")
FLOOR_LABELS = ("Stair_", "Tw_Landing", "TWA_", "Ch_Dais", "Top_Slab", "Garth", "CryptFloor", "Ground_", "KE_Floor", "KA_Floor", "Ch_Floor", "Sa_Floor")


def prim_info(ed, comp):
    p = ed.props(comp, ["bodyInstance"])
    bi = p.get("bodyInstance") or {}
    po = bi.get("physMaterialOverride")
    return {"collision_profile": bi.get("collisionProfileName"), "collision_enabled": bi.get("collisionEnabled"),
            "phys_material_override": None if po in (None, "None") else (R(po) or po)}


VISUAL_FLOOR_WORDS = ("Floor", "Water", "Stair", "Flight", "Landing", "Bed", "Slab", "Dais", "Pave", "Plank", "Deck", "Tile")
VISUAL_SKIP_WORDS = ("Wall", "Pier", "Column", "Pillar", "Arch", "Vault", "Rail", "Lining", "Rub", "Debris", "Cobweb", "Ivy")


def visual_under(ed, x, y, hz, exclude, actor_cache, comp_cache):
    """The visible art actor under the player's feet when the hit actor is a hidden shell or a primitive: its label, mesh and materials.
    A candidate has its top within -4..+10 cm of the hit, or (sloped flights and uneven tiles, whose bounds are taller than the surface) contains the hit point and is named Stair/Flight/Tile."""
    refs = ed.find_box((x - 0.75, y - 0.75, hz - 4.0), (x + 0.75, y + 0.75, hz + 10.0))
    best = None
    for r in refs:
        on = objname(r)
        if r == exclude or on.startswith(NOT_FLOOR_PREFIXES):
            continue
        if r not in actor_cache:
            b = ed.bounds(r)
            actor_cache[r] = {"label": ed.label(r), "object": on, "bmin": rr(b[0], 2), "bmax": rr(b[1], 2)}
        a = actor_cache[r]
        lab = a["label"]
        sx, sy = a["bmax"][0] - a["bmin"][0], a["bmax"][1] - a["bmin"][1]
        if max(sx, sy, a["bmax"][2] - a["bmin"][2]) > 100000 or any(w in lab for w in VISUAL_SKIP_WORDS):
            continue
        sloped = ("Stair" in lab or "Flight" in lab or "Tile" in lab) and a["bmin"][2] - 1 <= hz <= a["bmax"][2] + 1
        if not (hz - 4.0 <= a["bmax"][2] <= hz + 10.0) and not sloped:
            continue
        if not (a["bmin"][0] - 1 <= x <= a["bmax"][0] + 1 and a["bmin"][1] - 1 <= y <= a["bmax"][1] + 1):
            continue
        score = (1 if any(w in lab for w in VISUAL_FLOOR_WORDS) else 0, sx * sy)
        if best is None or score > best[0]:
            best = (score, r)
    if not best:
        return None
    r = best[1]
    a = actor_cache[r]
    for c in ed.comps(r):
        if ed.cls(c) in MESH_COMPS:
            inf = mesh_info(ed, c, comp_cache)
            if inf["visible"]:
                return {"label": a["label"], "mesh": inf["mesh"], "materials": inf["materials"], "collision_enabled": inf["collision_enabled"], "top_z": a["bmax"][2]}
    return {"label": a["label"], "mesh": None, "materials": [], "collision_enabled": None, "top_z": a["bmax"][2]}


def refine_floors(ed, floors):
    rows = [dict(r) for r in floors["samples"]]
    actor_cache, comp_cache, vis_cache, comp_of = {}, {}, {}, {}
    n_retry = n_prim = n_vis = n_reprobe = 0
    global PLAYER_HALF_HEIGHT, FOOTSTEP_EXTRA
    PLAYER_HALF_HEIGHT, FOOTSTEP_EXTRA = float(floors["player_half_height"]), float(floors["footstep_extra_depth"])
    for row in rows:
        if row["area"] == "passage" and row["source"] == "hand" and not (1700 <= row["xy"][1] <= 2300):
            row["area"] = "passage_outside_lane"      # chosen from the wide SZN_Passage box; the real lane is y 1700 to 2300 between PSA_Wall_PS and PSA_Wall_PN
    for k, (x, y) in enumerate([(6300, 2000), (6800, 1850), (7300, 2100), (7800, 2150), (8300, 1800), (8800, 2000), (9200, 1850), (9300, 2200), (7000, 2200), (8500, 2050)]):
        rows.append(process_point(ed, {"id": "passage_lane_%02d" % (k + 1), "area": "passage", "source": "hand", "xy": [x, y], "z_est": 0}, actor_cache, comp_cache, comp_of))
    for i, row in enumerate(rows):
        x, y = row["xy"]
        if row["area"] == "belfry" and row["source"] == "hand" and not (row.get("probe_hit_z") is not None and abs(row["probe_hit_z"] - 2500.0) < 6.0):
            # the first estimate (z 2700) probed from above the bell and the trigger volume; probe again from the belfry floor (z 2500)
            prev = row.get("probe_hit_z")
            row = process_point(ed, dict({k: row[k] for k in ("id", "area", "source", "xy")}, z_est=2500), actor_cache, comp_cache, comp_of)
            row["reprobed_from_first_hit_z"] = prev
            rows[i] = row
            n_reprobe += 1
        if row["status"] == "hit_actor_not_resolved":
            # the object-type filter found nothing: look again without it (props, rubble and foliage may use other object types)
            hz = row["probe_hit_z"]
            refs = ed.find_box((x - 0.75, y - 0.75, hz - 0.75), (x + 0.75, y + 0.75, hz + 0.75))
            best = None
            for r in refs:
                on = objname(r)
                if on.startswith(NOT_FLOOR_PREFIXES):
                    continue
                b = ed.bounds(r)
                if max(b[1][k] - b[0][k] for k in range(3)) > 100000:
                    continue
                if b[0][2] - 0.3 <= hz <= b[1][2] + 0.3 and b[0][0] - 1 <= x <= b[1][0] + 1 and b[0][1] - 1 <= y <= b[1][1] + 1:
                    d = abs(b[1][2] - hz)
                    if best is None or d < best[0]:
                        best = (d, r, b)
            n_retry += 1
            if best:
                r, b = best[1], best[2]
                row.update({"actor_label": ed.label(r), "actor_object": objname(r), "actor_bounds_min": rr(b[0], 2), "actor_bounds_max": rr(b[1], 2), "resolved_by": "unfiltered retry"})
                comps = ed.comps(r)
                row["actor_class"] = short(ed.cls(r))
                meshc = [c for c in comps if ed.cls(c) in MESH_COMPS]
                if meshc:
                    inf = mesh_info(ed, meshc[0], comp_cache)
                    row["component"] = objname(meshc[0])
                    row.update({k: inf[k] for k in ("mesh", "materials", "material_source", "material_phys", "visible", "hidden_in_game", "collision_profile",
                                                    "collision_enabled", "phys_material_override")})
                    row["greybox_or_collision"] = bool(inf["visible"] is False or inf["hidden_in_game"] or (inf["mesh"] or "").startswith("/Engine/BasicShapes"))
                    row["greybox_reason"] = ("hidden shell (bVisible false)" if inf["visible"] is False else "BasicShapes primitive" if (inf["mesh"] or "").startswith("/Engine/BasicShapes")
                                             else "art mesh")
                row["status"] = "ok"
            else:
                row["status"] = "hit_actor_not_resolved"
        if row["status"] == "ok" and "mesh" not in row:
            # a volume or other non-mesh actor was hit: read its primitive's collision
            r = row.get("_ref") or MAPPFX + row["actor_object"]
            infos = []
            for c in ed.comps(r):
                if ed.cls(c) in PRIM_COMPS:
                    infos.append(dict(prim_info(ed, c), component=objname(c)))
            n_prim += 1
            row["volume_components"] = infos
            row["greybox_or_collision"] = False
            row["greybox_reason"] = "non-mesh actor (volume or trigger)"
            row["is_volume_hit"] = True
        if row["status"] == "ok":
            fp = [row["actor_bounds_max"][0] - row["actor_bounds_min"][0], row["actor_bounds_max"][1] - row["actor_bounds_min"][1]]
            height = row["actor_bounds_max"][2] - row["actor_bounds_min"][2]
            lab = row["actor_label"]
            row["is_floor"] = (not row.get("is_volume_hit")) and (min(fp) >= 100 or lab.startswith(FLOOR_LABELS)) and height <= 1200
            if row.get("greybox_or_collision") and row["is_floor"] and "mesh" in row:
                key = (x, y)
                vu = visual_under(ed, x, y, row["probe_hit_z"], MAPPFX + row["actor_object"], actor_cache, comp_cache)
                row["visual_under"] = vu
                n_vis += 1
        if (i + 1) % 20 == 0:
            say("  refined %d/%d" % (i + 1, len(rows)))
    say("  re-probed %d belfry points, retried %d unresolved, read %d volume hits, looked under %d greybox hits" % (n_reprobe, n_retry, n_prim, n_vis))
    out = dict(floors)
    out["samples"] = rows
    return out


def stage_floors2(ed):
    path = os.path.join(SCRATCH, "floors.json")
    return refine_floors(ed, json.load(open(path, encoding="utf-8")))


# ---------------------------------------------------------------------------------------------- 5. great bell
def stage_bell(ed):
    out = {"actors": [], "tower_bell_meshes": []}
    for r in ed.find_cls("/Game/LastBell/Blueprints/Interactables/BP_TagInteractable_GreatBell.BP_TagInteractable_GreatBell_C"):
        b = ed.bounds(r)
        rec = {"label": ed.label(r), "object": objname(r), "class": short(ed.cls(r))}
        rec.update(ed.xf_full(r))
        rec["bounds_min"], rec["bounds_max"] = rr(b[0], 1), rr(b[1], 1)
        rec["bounds_centre"] = rr([(b[0][i] + b[1][i]) / 2 for i in range(3)], 1)
        rec["meshes"] = []
        for c in ed.comps(r):
            if ed.cls(c) in MESH_COMPS:
                p = ed.props(c, ["staticMesh", "overrideMaterials", "bVisible", "relativeLocation", "relativeScale3D"])
                rec["meshes"].append({"component": objname(c), "mesh": rname(p.get("staticMesh")), "visible": p.get("bVisible"),
                                      "rel_location": rr(v3(p["relativeLocation"]), 1), "rel_scale": rr(v3(p["relativeScale3D"]), 3)})
        out["actors"].append(rec)
    for q in ("Tw_Bell", "TWA_Bell", "GreatBell", "BellFrame"):
        for r in ed.find_name(q)[:20]:
            lab = ed.label(r)
            if lab.startswith(q) or q in lab:
                b = ed.bounds(r)
                out["tower_bell_meshes"].append({"label": lab, "object": objname(r), "bounds_min": rr(b[0], 1), "bounds_max": rr(b[1], 1),
                                                 "bounds_centre": rr([(b[0][i] + b[1][i]) / 2 for i in range(3)], 1)})
    return out


# ---------------------------------------------------------------------------------------------- 6. warden
def stage_warden(ed):
    out = {"classes": [], "warden_actors": [], "spawn_points": [], "patrol_points": [], "search_points": [], "apparitions": [], "other_warden_actors": []}
    for c in ed.call(O, "search_subclasses", {"base_class": {"refPath": "/Script/Engine.Actor"}, "class_name": "Warden"}) or []:
        out["classes"].append(R(c))
    chains = {}
    for r in ed.find_cls("/Script/LastBell.LBWarden"):
        cls = ed.cls(r)
        rec = {"label": ed.label(r), "object": objname(r), "class": short(cls), "parent_chain": [short(x) for x in ed.chain(cls, chains)] + ["LBWarden chain (native)"]}
        rec.update(ed.xf_full(r))
        out["warden_actors"].append(rec)
    for key, cls, props in (("spawn_points", "/Script/LastBell.LBWardenSpawnPoint", ["MinStage", "RouteId"]),
                            ("patrol_points", "/Script/LastBell.LBPatrolPoint", ["RouteId", "Order", "WaitSeconds"]),
                            ("search_points", "/Script/LastBell.LBSearchPoint", [])):
        for r in ed.find_cls(cls):
            rec = {"label": ed.label(r), "object": objname(r)}
            rec.update(ed.xf_full(r))
            if props:
                rec["props"] = ed.props(r, props)
            out[key].append(rec)
    for r in ed.find_cls("/Script/LastBell.LBWardenApparition"):
        p = ed.props(r, ["TriggerTag", "ArmDelaySeconds", "Stations", "LookPointHeight", "bUseSkeletalFigure"])
        stations = []
        for st in p.get("Stations") or []:
            stations.append({"location": rr(v3(st["location"]), 1) if isinstance(st.get("location"), dict) else st.get("location"),
                             "walk_path_points": len(st.get("walkPath") or []), "hold_seconds": st.get("holdSeconds"),
                             "lightning_on_hold": st.get("bLightningOnHold")})
        cls = ed.cls(r)
        rec = {"label": ed.label(r), "object": objname(r), "class": short(cls), "trigger_tag": tags_of(p.get("TriggerTag")), "arm_delay_s": p.get("ArmDelaySeconds"),
               "skeletal_figure": p.get("bUseSkeletalFigure"), "look_point_height": p.get("LookPointHeight"), "stations": stations}
        rec.update(ed.xf_full(r))
        out["apparitions"].append(rec)
    for q in ("Silhouette", "Warden"):
        for r in ed.find_name(q)[:30]:
            on = objname(r)
            if on.startswith(("LBWarden", "LBPatrol", "LBSearch", "BP_WardenApparition", "LBWardenSpawn", "LBWardenMarker")) or any(o["object"] == on for o in out["apparitions"] + out["warden_actors"]):
                continue
            if all(o["object"] != on for o in out["other_warden_actors"]):
                rec = {"label": ed.label(r), "object": on}
                rec.update(ed.xf_full(r))
                out["other_warden_actors"].append(rec)
    return out


# ---------------------------------------------------------------------------------------------- 7. audio config now
SOUND_ASSET_CLASSES = [("SoundWave", "/Script/Engine.SoundWave"), ("SoundCue", "/Script/Engine.SoundCue"), ("SoundBase", "/Script/Engine.SoundBase"),
                       ("SoundClass", "/Script/Engine.SoundClass"), ("SoundMix", "/Script/Engine.SoundMix"), ("SoundAttenuation", "/Script/Engine.SoundAttenuation"),
                       ("SoundConcurrency", "/Script/Engine.SoundConcurrency"), ("ReverbEffect", "/Script/Engine.ReverbEffect"),
                       ("PhysicalMaterial", "/Script/PhysicsCore.PhysicalMaterial"), ("SoundSubmix", "/Script/Engine.SoundSubmix"),
                       ("MetaSoundSource", "/Script/MetasoundEngine.MetaSoundSource")]


def read_ini_lines(path, patterns):
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                if any(p in line for p in patterns):
                    out.append("%d: %s" % (n, line.rstrip()))
    except OSError as e:
        out.append("cannot read: %s" % e)
    return out


def stage_config(ed):
    out = {}
    out["engine_ini"] = read_ini_lines(os.path.join(ROOT, "Config", "DefaultEngine.ini"), ["AudioMaxChannels", "PhysicalSurfaces", "AudioDevice", "Audio"])
    out["game_ini_audio"] = read_ini_lines(os.path.join(ROOT, "Config", "DefaultGame.ini"), ["AudioSettings", "LBGameSettings"])
    cnt = {}
    for name, cls in (("AudioVolume", "/Script/Engine.AudioVolume"), ("AmbientSound", "/Script/Engine.AmbientSound"), ("LBAudioZone", "/Script/LastBell.LBAudioZone"),
                      ("LBAmbientEmitter", "/Script/LastBell.LBAmbientEmitter"), ("AudioComponent_actors_none", None)):
        if cls:
            cnt[name] = len(ed.find_cls(cls))
    out["placed_actor_counts"] = cnt
    assets = {}
    for cls, cpath in SOUND_ASSET_CLASSES:
        try:
            r = ed.call(AS, "find_assets", {"folder_path": "/Game/LastBell", "name": "", "asset_type": {"refPath": cpath}, "recursive": True, "tags": {}})
            assets[cls] = [R(x) if isinstance(x, dict) else x for x in (r or [])]
        except RuntimeError as e:
            assets[cls] = "query failed: " + str(e)[:120]
    out["sound_assets_under_game_lastbell"] = assets
    ex = {}
    for p in ("/Game/LastBell/Audio", "/Game/LastBell/Physics", "/Game/LastBell/Data/DA_Audio", "/Game/LastBell/Data/DT_Footsteps"):
        try:
            ex[p] = bool(ed.call(AS, "exists", {"path": p}))
        except RuntimeError as e:
            ex[p] = "query failed: " + str(e)[:80]
    out["exists"] = ex
    try:
        out["lastbell_folders"] = [R(x) if isinstance(x, dict) else x for x in ed.call(AS, "list_folders", {"root_path": "/Game/LastBell"}) or []]
    except RuntimeError as e:
        out["lastbell_folders"] = "query failed: " + str(e)[:80]
    for name in ("SFX_", "MUS_", "SW_", "SC_", "ATT_", "RVB_", "PM_LB"):
        try:
            r = ed.call(AS, "find_assets", {"folder_path": "", "name": name, "recursive": True, "tags": {}})
            out["asset_name_prefix_" + name] = [x for x in (r or []) if "/Game/LastBell" in str(x)][:20]
        except RuntimeError as e:
            out["asset_name_prefix_" + name] = "query failed: " + str(e)[:80]
    return out


# ---------------------------------------------------------------------------------------------- 8. MCP capability probe (describe only)
PROBE_CLASSES = [("AudioVolume", "/Script/Engine.AudioVolume"), ("AmbientSound", "/Script/Engine.AmbientSound"), ("SoundAttenuation", "/Script/Engine.SoundAttenuation"),
                 ("SoundClass", "/Script/Engine.SoundClass"), ("SoundMix", "/Script/Engine.SoundMix"), ("SoundConcurrency", "/Script/Engine.SoundConcurrency"),
                 ("ReverbEffect", "/Script/Engine.ReverbEffect"), ("PhysicalMaterial", "/Script/PhysicsCore.PhysicalMaterial"), ("SoundWave", "/Script/Engine.SoundWave"),
                 ("AudioComponent", "/Script/Engine.AudioComponent")]
KEY_PROPS = ("reverb", "interior", "ambient", "priority", "bEnabled", "attenuation", "falloff", "extent", "decay", "density", "diffusion", "gain", "fade", "volume",
             "parent", "child", "adjuster", "surface", "friction", "maxcount", "resolution", "loop", "sound", "soundclass", "concurrency", "lowpass", "lpf")
AUDIO_WORDS = re.compile(r"sound|audio|wav|reverb|attenuat|concurrenc|submix|metasound|ambient", re.I)
CREATE_WORDS = re.compile(r"^(create|import|add_to_scene|duplicate|move|write_file|load_asset|set_properties|add_component|set_parent)", re.I)


def stage_mcp(ed):
    out = {"toolsets": 0, "tools": 0, "audio_named_tools": [], "creation_tools": [], "classes": {}, "subclasses": {}, "notes": []}
    listing = ed.ue.raw("list_toolsets", {})
    names = [n for n in re.findall(r"^- ([\w\.]+):", listing, re.M) if "." in n]
    out["toolsets"] = len(names)
    for n in names:
        d = None
        for attempt in range(3):
            try:
                d = ed.ue.describe(n)
                break
            except Exception as e:  # noqa: BLE001  (a connection reset on a large reply: read-only, retried on a new session)
                time.sleep(2)
                try:
                    ed.ue = L.UE180()
                except Exception:  # noqa: BLE001
                    pass
                last = e
        if d is None:
            out["notes"].append("describe failed for %s: %s" % (n, str(last)[:80]))
            continue
        for t in d["tools"]:
            tn = t["name"].split(".")[-1]
            desc = (t.get("description") or "").strip().replace("\n", " ")
            out["tools"] += 1
            req = t["inputSchema"].get("required") or []
            sig = "%s.%s(%s)" % (n.split(".")[-1], tn, ", ".join(req))
            if AUDIO_WORDS.search(tn) or AUDIO_WORDS.search(desc[:200]):
                out["audio_named_tools"].append({"tool": sig, "desc": desc[:160]})
            if CREATE_WORDS.search(tn):
                out["creation_tools"].append({"tool": sig, "desc": desc[:140]})
    for label, path in PROBE_CLASSES:
        cdo = path.rsplit(".", 1)[0] + ".Default__" + path.rsplit(".", 1)[1]
        try:
            props = J(ed.call(O, "list_properties", {"instance": {"refPath": cdo}}))
            keys = sorted(props.keys()) if isinstance(props, dict) else [str(x) for x in props or []]
            skip = ("tick", "net", "replic", "role", "guid", "datalayer", "hlod", "tags", "layers", "onTake", "onActor", "onBegin", "onEnd", "onClicked", "onReleased", "onInput",
                    "onDestroyed")
            own = [k for k in keys if not any(w.lower() in k.lower() for w in skip)]
            out["classes"][label] = {"cdo_readable": True, "property_count": len(keys), "key_properties": [k for k in keys if any(w in k.lower() for w in KEY_PROPS)][:60],
                                     "all_properties": own if len(own) <= 90 else own[:90]}
        except RuntimeError as e:
            out["classes"][label] = {"cdo_readable": False, "error": str(e)[:160]}
    for label, base, filt in (("DataAsset subclasses named Sound/Reverb/Physical", "/Script/Engine.DataAsset", "Sound"),
                              ("DataAsset subclasses named Reverb", "/Script/Engine.DataAsset", "Reverb"),
                              ("DataAsset subclasses named PhysicalMaterial", "/Script/Engine.DataAsset", "Physical"),
                              ("Factory subclasses named Sound", "/Script/UnrealEd.Factory", "Sound"),
                              ("Factory subclasses named Reverb", "/Script/UnrealEd.Factory", "Reverb"),
                              ("Factory subclasses named PhysicalMaterial", "/Script/UnrealEd.Factory", "PhysicalMaterial"),
                              ("Actor subclasses named AudioVolume", "/Script/Engine.Actor", "AudioVolume"),
                              ("Actor subclasses named AmbientSound", "/Script/Engine.Actor", "AmbientSound")):
        try:
            out["subclasses"][label] = [R(x) for x in ed.call(O, "search_subclasses", {"base_class": {"refPath": base}, "class_name": filt}) or []][:20]
        except RuntimeError as e:
            out["subclasses"][label] = "query failed: " + str(e)[:100]
    # the unit brush of a volume spawned by add_to_scene_from_class (precedent: P14-3 PP_Chapel, PP_Tower)
    brush = []
    for lab in ("PP_Chapel", "PP_Tower"):
        for r in ed.find(lab):
            b = ed.bounds(r)
            sc = ed.xform(r)[2]
            brush.append({"label": lab, "bounds_size": rr([b[1][i] - b[0][i] for i in range(3)], 1), "scale": rr(sc, 4),
                          "unit_brush_size": rr([(b[1][i] - b[0][i]) / sc[i] for i in range(3)], 1)})
    out["spawned_volume_precedent"] = brush
    # existing assets of the types S1 needs (whole project incl. engine content), as duplication sources; read only
    cand = {}
    for label, path in (("SoundClass", "/Script/Engine.SoundClass"), ("SoundMix", "/Script/Engine.SoundMix"), ("SoundAttenuation", "/Script/Engine.SoundAttenuation"),
                        ("SoundConcurrency", "/Script/Engine.SoundConcurrency"), ("ReverbEffect", "/Script/Engine.ReverbEffect"),
                        ("PhysicalMaterial", "/Script/PhysicsCore.PhysicalMaterial"), ("SoundWave", "/Script/Engine.SoundWave")):
        try:
            r = ed.call(AS, "find_assets", {"folder_path": "", "name": "", "asset_type": {"refPath": path}, "recursive": True, "tags": {}}) or []
            r = [R(x) if isinstance(x, dict) else str(x) for x in r]
            cand[label] = ["%d found" % len(r)] + r[:6]
        except RuntimeError as e:
            cand[label] = "query failed: " + str(e)[:100]
    out["engine_candidates"] = cand
    return out


# ---------------------------------------------------------------------------------------------- analysis: cue proposals (item 1)
# One entry per class. "row" is what goes into DA_Audio.InteractionCues (ActorClass, bIncludeSubclasses true) or "silent" (SilentClasses).
# Cue names are the plan section 3 names; "_01..03" means the numbered variants of that cue.
CUE_PROPOSALS = OrderedDict([
    ("BP_Door_Base_Dungeon", {
        "row": "cue on BP_Door_Base (bIncludeSubclasses, so BP_Door_Base_Dungeon and any later child use it)",
        "interact": "SFX_LB_Door_Wood_Open_01..03", "denied": "SFX_LB_Door_Locked_01..03", "dial_notch": "", "volume": 1.0, "pitch": "0.97-1.03",
        "reason": "All 4 doors are wood: leaf SM_Dungeon_door with MI_Prop_Wood_Weathered backing cubes; none is stone, so SFX_LB_Door_Stone_Open_* has no consumer "
                  "in L_Monastery (keep the recordings for later). Denied fires on Door_ChapelMain (needs State.Item.ChapelKey); the other three have no "
                  "required tags. NoiseLoudness 0.6."}),
    ("BP_DialLever_Crypt", {
        "row": "cue on BP_DialLever (bIncludeSubclasses covers BP_DialLever_Crypt)",
        "interact": "", "denied": "SFX_LB_Generic_Use_01..03", "dial_notch": "SFX_LB_Lever_Notch_01..04", "volume": 1.0, "pitch": "0.97-1.03",
        "reason": "Crypt counterweight levers (prompt 'Move counterweight', 3 notches each, iron arm). The subsystem plays DialNotch on OnDialChanged and "
                  "suppresses the Interact sound when the actor has a dial, so Interact stays empty. Denied (\"It won't move\", bLocked) gets the dull "
                  "generic use sound. NoiseLoudness 0.5."}),
    ("BP_PuzzleCandle", {
        "row": "cue on BP_PuzzleCandle",
        "interact": "SFX_LB_Candle_Light_01..03", "denied": "", "dial_notch": "", "volume": 0.9, "pitch": "0.97-1.03",
        "reason": "4 chapel puzzle candles (prompt 'Light candle', single use, no required tags, NoiseLoudness 0.1). The match/flame whoosh plays at the candle."}),
    ("BP_SequencePuzzle", {
        "row": "silent (SilentClasses)",
        "interact": "", "denied": "", "dial_notch": "", "volume": 0, "pitch": "",
        "reason": "Controller actors with only a ULBSequencePuzzleComponent (no mesh, no interactable). Their sounds come from the puzzle events "
                  "(SmallBellStrike / SmallBellFail / SmallBellSolved in DA_Audio), not from a cue row. SEE FINDING F-1: both placed puzzles (Puzzle_Bells "
                  "and Puzzle_Candles) will play those small-bell sounds."}),
    ("BP_Inspectable_Note", {
        "row": "cue on BP_Inspectable_Note",
        "interact": "SFX_LB_Paper_01..03", "denied": "", "dial_notch": "", "volume": 0.8, "pitch": "0.95-1.05",
        "reason": "6 notes (Gatehouse, Nave, Sacristy, Cloister, Ossuary, Chains); prompt 'Read', bInspectOnInteract, no tags, NoiseLoudness 0. Paper rustle when the "
                  "inspect view opens."}),
    ("BP_RitualMechanism_ChapelBells", {
        "row": "cue on BP_RitualMechanism_ChapelBells",
        "interact": "SFX_LB_Stone_Grind_01..03", "denied": "SFX_LB_Generic_Use_01..03", "dial_notch": "", "volume": 1.0, "pitch": "0.97-1.03",
        "reason": "Altar_Ritual1: a bell wheel (SM_LB_Prop_BellWheel_A) on a stone pedestal at the altar, requires State.Chapel.CandlesSolved, grants State.Ritual.1 "
                  "and State.Warden.Stage.2; NoiseLoudness 1.0. Stone grinding while the altar mechanism turns; the stage-2 bell follows 2 s after the tag (plan 5.3). "
                  "A row holds one sound set, so no layered winch (the plan's 'plus winch if chain-driven' is not expressible in one row)."}),
    ("BP_RitualMechanism_CryptWinch", {
        "row": "cue on BP_RitualMechanism_CryptWinch",
        "interact": "SFX_LB_Winch_01..03", "denied": "SFX_LB_Generic_Use_01..03", "dial_notch": "", "volume": 1.0, "pitch": "0.97-1.03",
        "reason": "Winch_Ritual2: capstan drum SM_LB_Crypt_CapstanDrum_80x50 on a crypt block; chain-driven. Needs State.Item.Crank plus the three dial positions; "
                  "grants State.Ritual.2 and Stage.4; NoiseLoudness 1.0. Ratchet and chain."}),
    ("BP_RitualMechanism_TowerCapstan", {
        "row": "cue on BP_RitualMechanism_TowerCapstan",
        "interact": "SFX_LB_Winch_01..03", "denied": "SFX_LB_Generic_Use_01..03", "dial_notch": "", "volume": 1.0, "pitch": "0.9-1.0",
        "reason": "Mech_Ritual3: the tower capstan (the same capstan drum mesh, wood and iron), requires State.Tower.BellsSolved, grants State.Ritual.3; NoiseLoudness 1.0. "
                  "Same winch recordings, pitched a little lower so it does not sound like the crypt winch."}),
    ("BP_TagInteractable_ChapelKey", {
        "row": "cue on BP_TagInteractable_ChapelKey",
        "interact": "SFX_LB_Key_Pickup_01..02", "denied": "", "dial_notch": "", "volume": 1.0, "pitch": "0.97-1.03",
        "reason": "Key_Chapel (iron key in the well house, prompt 'Take key', grants State.Item.ChapelKey, NoiseLoudness 0.2). Positional at the key."}),
    ("BP_TagInteractable_CryptCrank", {
        "row": "cue on BP_TagInteractable_CryptCrank",
        "interact": "SFX_LB_Key_Pickup_01..02", "denied": "", "dial_notch": "", "volume": 1.0, "pitch": "0.85-0.95",
        "reason": "DEVIATES from the brief (crank -> winch): this actor is the crank PICKUP (Crank_Winch, prompt 'Take crank', grants State.Item.Crank), not the mechanism. "
                  "Picking up a loose iron crank is a metal handling clink, pitched lower than the key. The winch ratchet belongs to BP_RitualMechanism_CryptWinch, which "
                  "consumes the crank. If the owner prefers a ratchet here, change Interact to SFX_LB_Winch_01..03."}),
    ("BP_SmallBell_Cloister", {
        "row": "silent (SilentClasses)",
        "interact": "", "denied": "", "dial_notch": "", "volume": 0, "pitch": "",
        "reason": "The 4 cloister bells are struck through Puzzle_Bells: ULBAudioSubsystem plays SmallBellStrike at the bell whose GrantedStateTags holds the accepted step, "
                  "pitched by SmallBellPitch, and SmallBellFail at the wrong bell. A cue row on the bell would double every strike."}),
    ("BP_TagInteractable_GreatBell", {
        "row": "silent (SilentClasses)",
        "interact": "", "denied": "", "dial_notch": "", "volume": 0, "pitch": "",
        "reason": "Decision: silent. The bell (prompt 'Ring the bell') grants State.Event.Finale; plan 5.3 turns that tag into bell stage 5 x 5 strikes at BellLocation "
                  "with FirstDelay 0, so the audible result of the press is already the great bell, and a second sound from the same actor would smear its attack. Phase 17 "
                  "(ending) may add a rope/clapper layer."}),
])


# ---------------------------------------------------------------------------------------------- analysis: audio zones and volumes (item 3)
# (name, storm-zone label whose box is the base, priority, RoofRain, InteriorWind, Howl, Darkness, RoomTone cue, RoomToneVolume, reverb, exterior vol, exterior LPF Hz,
#  z override (min, max) or None, note)
ZONE_PLAN = [
    ("Chapel", "SZN_Chapel", 1, 0.9, 0.25, 0.0, 0.3, "SFX_LB_Room_Chapel", 0.6, "RVB_LB_Chapel", 0.35, 2500, None,
     "Vaulted nave with a roof (moon slits and one rain opening at x 6500): the rain is a roof patter; some wind through the openings."),
    ("Crypt", "SZN_Crypt", 2, 0.05, 0.05, 0.0, 1.0, "SFX_LB_Room_Crypt", 0.8, "RVB_LB_Crypt", 0.35, 2500, (-1200.0, -20.0),
     "Below ground: almost no rain, a draught only. Top raised from -45 to -20 so it overlaps the chapel box (-40) instead of leaving a 5 cm gap on the stair; "
     "the crypt wins by priority 2 > 1."),
    ("Cloister", "SZN_Cloister", 1, 0.7, 0.5, 0.0, 0.2, "SFX_LB_Room_Cloister", 0.5, "RVB_LB_Cloister", 0.7, 6000, None,
     "Covered walk around an open garth; roof partly collapsed. Contains the garth box, which is overridden by Garth (priority 2)."),
    ("Garth", "SZN_Garth", 2, 0.0, 1.0, 0.0, 0.1, None, 0.0, None, 1.0, 20000, None,
     "The open garden inside the cloister: outdoors in every respect (no room tone, no reverb, full interior wind = outdoor wind). An AudioVolume with "
     "bApplyReverb false and priority 2 cancels the cloister reverb here."),
    ("Passage", "SZN_Passage", 1, 0.0, 0.4, 0.0, 0.6, "SFX_LB_Room_Passage", 0.7, "RVB_LB_Passage", 0.35, 2500, ((6040.0, 1660.0, -40.0), (9460.0, 2340.0, 900.0)),
     "The shortcut passage is a 600 cm wide lane between two 800 cm walls (PSA_Wall_PS at y 1660 to 1700, PSA_Wall_PN at y 2300 to 2340, x 6040 to 9460) with NO roof "
     "(nothing overhead, nothing above in the upward traces): the rain falls in, so RoofRain is 0 and the walls only shelter the wind and add slapback reverb. "
     "SZN_Passage is much wider (y 900 to 2600) than the lane, so the audio box is the lane: y 1660 to 2340, top 900 (walls are 800). "
     "Consider exterior volume 0.7 / 6000 Hz in P16-4 because the lane is open above."),
    ("TowerStair", "SZN_TowerShaft", 3, 0.6, 0.6, 0.35, 0.6, "SFX_LB_Room_Tower", 0.7, "RVB_LB_Tower", 0.35, 2500, None,
     "Tower base and spiral stair (Door_Tower x 12020; landings 1 to 10; top flight reaches the belfry floor at z 2500). Box is the storm shaft (-40 to 2650)."),
    ("Belfry", "SZN_Belfry", 4, 0.8, 1.0, 1.0, 0.3, "SFX_LB_Room_Belfry", 0.5, "RVB_LB_Belfry", 0.7, 6000, (2400.0, 4800.0),
     "Open arches under a roof. The storm zone starts at z 2650 but the belfry FLOOR is z 2500 (TWA_BelfryFloor top), so a player standing there (capsule centre 2588) "
     "would still be in the stair box; the audio box starts at 2400 and has priority 4 > 3, so it takes over on the top flight."),
]
GROUP_NAMES = ["Chapel", "Crypt", "Cloister", "Garth", "Passage", "TowerStair", "Belfry"]
AREA_EXPECTED_ZONE = {"courtyard": "Outdoors", "approach": "Outdoors", "gatehouse": "Outdoors", "wellhouse": "Outdoors", "chapel": "Chapel", "crypt": "Crypt",
                      "crypt_water": "Crypt", "cloister_walk": "Cloister", "garth": "Garth", "passage": "Passage", "tower_base": "TowerStair",
                      "tower_landing": "TowerStair", "tower_stair": "TowerStair", "belfry": "Belfry", "outdoors": "Outdoors", "passage_outside_lane": "Outdoors"}


def build_zone_proposals(areas):
    szn = {z["label"]: z for z in areas["storm_zones"]}
    rows = []
    for (name, base, prio, rr_, iw, howl, dark, tone, tvol, rvb, ext_v, ext_lpf, zov, note) in ZONE_PLAN:
        b = szn[base]
        lo, hi = list(b["bounds_min"]), list(b["bounds_max"])
        if zov and isinstance(zov[0], (int, float)):
            lo[2], hi[2] = zov
        elif zov:
            lo, hi = list(zov[0]), list(zov[1])
        centre = [(lo[i] + hi[i]) / 2.0 for i in range(3)]
        half = [(hi[i] - lo[i]) / 2.0 for i in range(3)]
        rows.append({"name": name, "base_storm_zone": base, "bounds_min": rr(lo, 1), "bounds_max": rr(hi, 1), "location": rr(centre, 1), "box_extent": rr(half, 1),
                     "rotation": [0.0, 0.0, 0.0], "brush_scale_on_200cm_unit": rr([2 * h / 200.0 for h in half], 4), "priority": prio,
                     "RoofRain": rr_, "InteriorWind": iw, "Howl": howl, "Darkness": dark, "RoomTone": tone, "RoomToneVolume": tvol, "ZoneName": name,
                     "reverb_effect": rvb, "bApplyReverb": rvb is not None, "reverb_volume": 0.6 if rvb else 0.0, "reverb_fade_s": 1.0,
                     "exterior_volume": ext_v, "exterior_lpf_hz": ext_lpf, "interior_volume": 1.0, "storm_exposure": b["exposure"], "note": note})
    return rows


def zone_at(rows, p):
    best = None
    for z in rows:
        if all(z["bounds_min"][i] <= p[i] <= z["bounds_max"][i] for i in range(3)):
            if best is None or z["priority"] > best["priority"]:
                best = z
    return best["name"] if best else "Outdoors"


def overlap_report(rows):
    out = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            ov = [min(a["bounds_max"][k], b["bounds_max"][k]) - max(a["bounds_min"][k], b["bounds_min"][k]) for k in range(3)]
            if all(v > 0 for v in ov):
                win = a["name"] if a["priority"] > b["priority"] else b["name"] if b["priority"] > a["priority"] else "AMBIGUOUS"
                out.append({"a": a["name"], "b": b["name"], "overlap_size": rr(ov, 1), "priority_a": a["priority"], "priority_b": b["priority"], "winner": win})
    return out


def check_zone_samples(rows, floors):
    res, bad = Counter(), []
    for s in floors["samples"]:
        if s.get("status") != "ok":
            continue
        centre = [s["xy"][0], s["xy"][1], s["probe_hit_z"] + floors["player_half_height"]]
        got = zone_at(rows, centre)
        want = AREA_EXPECTED_ZONE.get(s["area"], "Outdoors")
        res["match" if got == want else "mismatch"] += 1
        if got != want:
            bad.append({"id": s["id"], "area": s["area"], "centre": rr(centre, 1), "expected": want, "got": got})
    return {"matches": res["match"], "mismatches": res["mismatch"], "details": bad}


# ---------------------------------------------------------------------------------------------- analysis: interactables, bells (items 1, 2, 5)
def dedupe(seq):
    out = []
    for x in seq:
        if not out or out[-1] != x:
            out.append(x)
    return out


def strip_c(name):
    """BP_Foo_C -> BP_Foo (only the generated-class suffix)."""
    return re.sub(r"_C$", "", name or "")


def group_interactables(inter):
    groups = OrderedDict()
    for a in inter["actors"]:
        g = groups.setdefault(strip_c(a["class"]), {"class": strip_c(a["class"]), "parent_chain": dedupe([strip_c(x) for x in a["parent_chain"]]),
                                                              "count": 0, "actors": [], "granted_tags": [], "required_tags": [], "single_use": set(),
                                                              "noise_loudness": set(), "component_kinds": set(), "prompts": set(), "has_dial": False, "has_seq": False})
        g["count"] += 1
        g["actors"].append({"label": a["label"], "location": a["location"], "rotation_yaw": a["rotation"][1]})
        for cn, c in a["components"].items():
            g["component_kinds"].add(c["kind"])
            if c["kind"] == "interactable":
                for t in c["granted_tags"]:
                    if t not in g["granted_tags"]:
                        g["granted_tags"].append(t)
                for t in c["required_tags"]:
                    if t not in g["required_tags"]:
                        g["required_tags"].append(t)
                g["single_use"].add(bool(c["single_use"]))
                g["noise_loudness"].add(c["noise_loudness"])
                g["prompts"].add(c["prompt"])
            elif c["kind"] == "dial":
                g["has_dial"] = True
            else:
                g["has_seq"] = True
    for g in groups.values():
        for k in ("single_use", "noise_loudness", "component_kinds", "prompts"):
            g[k] = sorted(g[k], key=str)
    return groups


def build_small_bells(inter):
    bells = []
    for a in inter["actors"]:
        if "SmallBell" not in a["class"]:
            continue
        step = None
        for c in a["components"].values():
            if c["kind"] == "interactable" and c["granted_tags"]:
                step = c["granted_tags"][0]
        mesh = next((m for m in a["meshes"] if m["component"] == "Bell"), None)
        size = mesh["rel_scale"][0] if mesh else None
        bells.append({"label": a["label"], "object": a["object"], "step_tag": step, "bell_mesh_scale": size, "bell_scale_variable": a.get("bell_scale_var"),
                      "location": a["location"], "bounds_centre": rr([(a["bounds_min"][i] + a["bounds_max"][i]) / 2 for i in range(3)], 1)})
    bells.sort(key=lambda b: b["step_tag"] or "")
    seq = next((a for a in inter["actors"] if a["label"] == "Puzzle_Bells"), None)
    order = None
    if seq:
        order = next(iter(seq["components"].values()))["steps"]
    return {"bells": bells, "SmallBellPitch": {b["step_tag"]: round(1.0 / b["bell_mesh_scale"], 4) for b in bells if b["bell_mesh_scale"]},
            "puzzle_order": order, "d081_sizes": [1.30, 1.15, 1.00, 0.85]}


# ---------------------------------------------------------------------------------------------- analysis: floors (item 4)
def base_name(path):
    return (path or "").rsplit("/", 1)[-1].split(".")[0]


def surface_of_name(name):
    n = base_name(name).lower().replace("slot:", "")
    if "water" in n:
        return "Water"
    if "wood" in n:
        return "Wood"
    if any(k in n for k in ("iron", "metal", "grate", "steel", "bronze")):
        return "Metal"
    if "grass" in n:
        return "Grass"
    if any(k in n for k in ("earth", "soil", "mud", "gravel", "sand")) or re.search(r"(^|_)dirt($|_)", n):
        return "Earth"
    return "Stone"


def effective_materials(row):
    """What the player sees under the feet: the visible art actor's materials when the hit actor is a greybox, else the hit actor's own."""
    vu = row.get("visual_under")
    if vu and vu.get("materials"):
        return [base_name(m) for m in vu["materials"]], vu["label"]
    return [base_name(m) for m in row.get("materials") or []], row.get("actor_label") or ""


def classify_surface(row, water_planes):
    """(surface, reason) for one floor sample, or (None, reason) when the hit is not a floor. Stone is the default (and the engine default row)."""
    if row.get("is_volume_hit"):
        return None, "not a floor: the bounds lookup resolved a volume or trigger (%s); the real blocker is probably the pit bottom, which the lookup cannot see" % row.get("actor_label")
    if not row.get("is_floor"):
        return None, "not a floor: a prop or kerb (%s)" % row.get("actor_label")
    x, y = row["xy"]
    fz = row["probe_hit_z"]
    if row["area"] in ("crypt", "crypt_water"):
        for pl in water_planes:
            if pl["bounds_min"][0] <= x <= pl["bounds_max"][0] and pl["bounds_min"][1] <= y <= pl["bounds_max"][1] and fz <= pl["bounds_max"][2] + 15:
                return "Water", "the player stands under the %s plane (plane z %.0f, floor z %.0f): shallow flood water" % (pl["label"], pl["bounds_max"][2], fz)
    mats, vlabel = effective_materials(row)
    lab = row.get("actor_label") or ""
    if "Earth" in lab and not lab.startswith("Garth"):
        return "Earth", "garden bed actor %s (earth)" % lab
    if lab == "Garth" or "GarthBed" in vlabel:
        return "Grass", "garth lawn: hidden Garth shell over CLA_GarthBed (MI_Cl_GarthEarth soil) carrying the CLA_GarthGrass blades; the grass is what the player walks on"
    primary = mats[0] if mats else lab
    surf = surface_of_name(primary)
    src = "the visible %s" % label_group(vlabel) if row.get("visual_under") else "the hit actor"
    return surf, "%s, first material slot %s%s" % (src, primary, (" (other slots: %s)" % ", ".join(mats[1:])) if len(mats) > 1 else "")


def label_group(label):
    return re.sub(r"(_[A-Za-z]?[0-9]+)+$", "", label or "") or label


def summarize_floors(floors, areas):
    water_planes = [{"label": a["label"], "bounds_min": a["bounds_min"], "bounds_max": a["bounds_max"]} for a in areas["anchors"].get("CA_Water", [])
                    if a["label"].startswith("CA_Water") and "Pit" not in a["label"]]
    rows = floors["samples"]
    for r in rows:
        if r["area"] == "belfry" and r.get("probe_hit_z") is not None and r["probe_hit_z"] < 2400:
            r["area"] = "tower_landing"       # (12800, 1700) lies beside the belfry floor, over landing 10 (top 2273): the stair, not the belfry
    ok = [r for r in rows if r.get("status") == "ok"]
    for r in ok:
        r["surface"], r["surface_reason"] = classify_surface(r, water_planes)
    fl = [r for r in ok if r.get("surface")]
    stats = {"samples": len(rows), "resolved": len(ok), "floor_hits": len(fl), "non_floor_hits": len(ok) - len(fl), "by_status": dict(Counter(r["status"] for r in rows)),
             "footstep_trace_hit": sum(1 for r in ok if r.get("footstep_hit")),
             "greybox_or_collision": sum(1 for r in fl if r.get("greybox_or_collision")),
             "greybox_or_collision_all_resolved": sum(1 for r in ok if r.get("greybox_or_collision")),
             "by_reason": dict(Counter(r.get("greybox_reason") for r in fl)),
             "by_collision_profile": dict(Counter(str(r.get("collision_profile")) for r in fl)),
             "by_surface": dict(Counter(r["surface"] for r in fl)),
             "has_phys_override": sum(1 for r in ok if r.get("phys_material_override")),
             "has_material_phys": sum(1 for r in ok if any(p and p != "unreadable" for p in r.get("material_phys") or []))}
    stats["greybox_fraction"] = round(stats["greybox_or_collision"] / float(len(fl)), 4) if fl else 0.0
    nm = [r for r in fl if r["source"] in ("hand", "landing", "stair_mid")]
    stats["floor_hits_no_markers"] = len(nm)
    stats["greybox_fraction_no_markers"] = round(sum(1 for r in nm if r.get("greybox_or_collision")) / float(len(nm)), 4) if nm else 0.0
    stats["greybox_fraction_all_resolved"] = round(stats["greybox_or_collision_all_resolved"] / float(len(ok)), 4) if ok else 0.0
    stats["method"] = ("A: BodyInstance.PhysMaterialOverride on the placed floor actors, from an area-and-mesh table" if stats["greybox_fraction"] >= 0.8 else
                       "B: physical material on the floor material instances (never on M_LB_Surface)")
    per_area = OrderedDict()
    for r in rows:
        d = per_area.setdefault(r["area"], {"samples": 0, "resolved": 0, "floor_hits": 0, "greybox": 0, "surfaces": Counter()})
        d["samples"] += 1
        if r.get("status") == "ok":
            d["resolved"] += 1
        if r.get("surface"):
            d["floor_hits"] += 1
            d["greybox"] += 1 if r.get("greybox_or_collision") else 0
            d["surfaces"][r["surface"]] += 1
    for d in per_area.values():
        d["surfaces"] = dict(d["surfaces"])
    stats["per_area"] = per_area
    by_actor = OrderedDict()
    by_mat = OrderedDict()
    for r in fl:
        k = label_group(r["actor_label"])
        mats, vlabel = effective_materials(r)
        g = by_actor.setdefault(k, {"group": k, "hits": 0, "areas": set(), "meshes": set(), "materials": set(), "visible_over": set(), "collision": set(), "greybox": set(),
                                    "surfaces": Counter(), "reasons": set()})
        g["hits"] += 1
        g["areas"].add(r["area"])
        g["meshes"].add(base_name(r.get("mesh")))
        g["materials"].update(mats)
        if r.get("visual_under"):
            g["visible_over"].add(label_group(r["visual_under"]["label"]))
        g["collision"].add("%s/%s" % (r.get("collision_profile"), r.get("collision_enabled")))
        g["greybox"].add(r.get("greybox_reason"))
        g["surfaces"][r["surface"]] += 1
        g["reasons"].add(r["surface_reason"])
        for m in mats[:1]:
            mg = by_mat.setdefault(m, {"material": m, "hits": 0, "actors": set(), "areas": set(), "surfaces": Counter(), "reasons": set()})
            mg["hits"] += 1
            mg["actors"].add(label_group(r["actor_label"]))
            mg["areas"].add(r["area"])
            mg["surfaces"][r["surface"]] += 1
            mg["reasons"].add(r["surface_reason"])
    for dct in (by_actor, by_mat):
        for g in dct.values():
            for k, v in list(g.items()):
                if isinstance(v, set):
                    g[k] = sorted(x for x in v if x)
                elif isinstance(v, Counter):
                    g[k] = dict(v)
    return {"stats": stats, "by_actor": list(by_actor.values()), "by_material": list(by_mat.values()), "water_planes": water_planes}


# ---------------------------------------------------------------------------------------------- analysis: MCP capability matrix (item 8)
def capability_matrix(mcp):
    audio_tools = [t["tool"] for t in mcp["audio_named_tools"] if "Sequencer" not in t["tool"]]
    fac = mcp["subclasses"]
    sound_fac = fac.get("Factory subclasses named Sound")
    rows = [
        {"asset": "SoundWave from a WAV file", "create_import_tool": "none",
         "closest": "TextureTools.import_file (images), StaticMeshTools / SkeletalMeshTools.import_file (FBX), DataTable / CurveTable / StringTable.import_file (CSV/JSON), "
                    "AssetTools.write_file (plain text only)",
         "factory_exists": "AudioEditor.SoundFactory / ReimportSoundFactory exist as classes (search_subclasses) but no tool runs a factory",
         "verdict": "IMPOSSIBLE over MCP as far as the tool list goes; use headless Unreal Python (AssetImportTask + SoundFactory, Unreal closed) - the P13 route in MCP_NOTES"},
        {"asset": "SoundClass / SoundMix / SoundAttenuation / SoundConcurrency / ReverbEffect / PhysicalMaterial",
         "create_import_tool": "none for arbitrary UObject assets",
         "closest": "DataAssetTools.create(folder_path, asset_name, asset_type) is for DataAsset subclasses; search_subclasses finds NO DataAsset subclass named Sound*, "
                    "Reverb* or Physical* (these classes derive from UObject), so it is expected to refuse them - NOT tried (it would create). "
                    "AssetTools.duplicate(path, new_path) could clone an existing asset of the type, but find_assets over the whole project including engine content finds NONE of "
                    "SoundClass, SoundMix, SoundAttenuation, SoundConcurrency or ReverbEffect (only two PhysicalMaterial assets: /AnimatorKit/Meshes/PhysMat_PhysCube and /Water/DefaultPhysMat), "
                    "so duplicate has no source for five of the six.",
         "factory_exists": "AudioEditor.SoundClassFactory, SoundMixFactory, SoundAttenuationFactory, SoundConcurrencyFactory, ReverbEffectFactory, UnrealEd.PhysicalMaterialFactoryNew "
                           "exist as classes; no tool drives them",
         "verdict": "S1 should first try DataAssetTools.create with each class (cheap, refusable), then AssetTools.duplicate for PhysicalMaterial only, then headless Python "
                    "(AssetToolsHelpers.create_asset with the factory). Setting properties afterwards works for any loaded asset: ObjectTools.set_properties (JSON string values) and "
                    "get_properties (CDO property lists were readable for all six, see below)."},
        {"asset": "DataAsset of a C++ class (DA_Audio)", "create_import_tool": "DataAssetTools.create",
         "closest": "precedent: DA_StormFX was created with asset_type /Script/LastBell.LBStormFXSettings (Tools/fx/p15_level.py apply_data); fields set with ObjectTools.set_properties, "
                    "soft object refs as {\"refPath\": ...}",
         "factory_exists": "n/a", "verdict": "works (used in P15); DA_Audio is the same call with /Script/LastBell.LBAudioSettings"},
        {"asset": "AudioVolume (brush volume)", "create_import_tool": "SceneTools.add_to_scene_from_class(actor_type /Script/Engine.AudioVolume, name, xform)",
         "closest": "precedent: PP_Chapel and PP_Tower were spawned from /Script/Engine.PostProcessVolume and scaled; both read back a unit brush of 200 x 200 x 200 cm, "
                    "so a box of size S needs scale S / 200 per axis (spawned_volume_precedent). Position with ActorTools.set_actor_transform, folder with SceneTools.set_actor_folder.",
         "factory_exists": "/Script/Engine.AudioVolume is an Actor subclass (search_subclasses)",
         "verdict": "very likely works the same way; NOT spawned here. Properties via ObjectTools.set_properties on the actor (names in classes.AudioVolume.key_properties). "
                    "Check in S1 that the brush is the 200 cm cube and that the reverb struct (`settings`: bApplyReverb, reverbEffect, volume, fadeTime; also `priority`, `bEnabled`) and the interior "
                    "struct (`ambientZoneSettings`: exterior/interior volume and low-pass) persist after a read-back; save only after the spike (the spike is deleted)."},
        {"asset": "AmbientSound actor", "create_import_tool": "SceneTools.add_to_scene_from_class(actor_type /Script/Engine.AmbientSound, ...)  or add_to_scene_from_asset(asset_path of a SoundBase)",
         "closest": "add_to_scene_from_asset is the documented way to place an actor from an asset; for a SoundWave it should create an AmbientSound, but this was not tried",
         "factory_exists": "/Script/Engine.AmbientSound is an Actor subclass", "verdict": "likely works; the sound is set on the Audio component (property names in classes.AmbientSound)"},
    ]
    other = [
        "No console command or CVar setter over MCP (only EditorAppToolset.SearchCVars): lb.Audio.* and au.* commands are typed by the owner in a PIE window (MCP_NOTES P10 item 8).",
        "No tool plays, previews or measures audio: every sound judgement needs the owner (A4 audition page, P16-4 session, P16-6 run-through).",
        "The sandboxed ProgrammaticToolset.execute_tool_script only imports json, math, datetime, copy, re and time: it cannot call the `unreal` Python module, so it is not a route to AssetImportTask.",
        "AssetTools.write_file writes plain text only (under /Game/, plugin Content or Saved/): not a way to copy a WAV into Content.",
        "Tools named for audio found by name or description search across %d tools in %d toolsets: %s" % (mcp["tools"], mcp["toolsets"],
                                                                                                          "none" if not audio_tools else ", ".join(audio_tools)),
    ]
    return {"rows": rows, "other_findings": other}


# ---------------------------------------------------------------------------------------------- markdown
def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in r) + " |")
    return "\n".join(out)


def fmt_v(v, n=0):
    return "(" + ", ".join(("%.*f" % (n, x)) for x in v) + ")"


def build_markdown(R_):
    L_ = []
    a = L_.append
    meta = R_["meta"]
    a("# P16-F0 survey tables (read only)")
    a("")
    a("Generated by `Tools/audio/p16_f0_survey.py` on %s against `%s`. Nothing was set, created, deleted, saved or moved; PIE never ran." % (meta["generated"], meta["level"]))
    a("State before: map dirty %s, never-save list dirty %s, %d actors. State after: map dirty %s, never-save list dirty %s, %d actors." % (
        R_["state_before"]["map_dirty"], any(R_["state_before"]["never_save_dirty"].values()), R_["state_before"]["actor_count"],
        R_["state_after"]["map_dirty"], any(R_["state_after"]["never_save_dirty"].values()), R_["state_after"]["actor_count"]))
    a("")
    # 1
    a("## 1. Interactables (%d actors, %d classes)" % (len(R_["interactables"]["actors"]), len(R_["interactables"]["groups"])))
    a("")
    rows = []
    for g in R_["interactables"]["groups"]:
        prop = R_["interactables"]["cue_proposals"].get(g["class"], {})
        rows.append([g["class"], g["count"], " > ".join(g["parent_chain"][1:]), ", ".join(g["component_kinds"]), ", ".join(g["granted_tags"]) or "-",
                     ", ".join(g["required_tags"]) or "-", ", ".join(str(x) for x in g["single_use"]), ", ".join(str(x) for x in g["noise_loudness"]),
                     prop.get("row", "MISSING")])
    a(md_table(["Class", "n", "Parents", "Components", "Granted tags", "Required tags", "Single use", "NoiseLoudness", "Proposed row"], rows))
    a("")
    a("### Proposed cue rows")
    a("")
    rows = []
    for cls, p in R_["interactables"]["cue_proposals"].items():
        rows.append([cls, p["row"], p["interact"] or "-", p["denied"] or "-", p["dial_notch"] or "-", p["volume"], p["pitch"] or "-", p["reason"]])
    a(md_table(["Class", "Row", "Interact", "Denied", "DialNotch", "Volume", "Pitch", "Reason"], rows))
    a("")
    unm = R_["interactables"]["unmapped_check"]
    a("Coverage check: the 12 classes the P16-1 suite reported as unmapped are %s." % ("ALL covered by a proposal above" if not unm else "MISSING: " + ", ".join(unm)))
    a("")
    a("### Every interactable actor")
    a("")
    rows = []
    for x in R_["interactables"]["actors"]:
        comp = x["components"]
        ic = next((c for c in comp.values() if c["kind"] == "interactable"), None)
        rows.append([x["label"], strip_c(x["class"]), fmt_v(x["location"], 0), "%.0f" % x["rotation"][1], ", ".join(ic["granted_tags"]) if ic else "-",
                     ", ".join(ic["required_tags"]) if ic else "-", ic["single_use"] if ic else "-", ic["noise_loudness"] if ic else "-",
                     "; ".join("%s: %s" % (c["kind"], ", ".join(c.get("steps") or c.get("position_tags") or [])) for c in comp.values() if c["kind"] != "interactable") or "-"])
    a(md_table(["Label", "Class", "Location", "Yaw", "Granted", "Required", "Single use", "Noise", "Dial / sequence data"], rows))
    a("")
    # 2
    sb = R_["small_bells"]
    a("## 2. Small bells")
    a("")
    rows = [[b["label"], b["step_tag"], b["bell_mesh_scale"], b["bell_scale_variable"], fmt_v(b["location"], 0), fmt_v(b["bounds_centre"], 0),
             sb["SmallBellPitch"].get(b["step_tag"])] for b in sb["bells"]]
    a(md_table(["Bell", "Step tag granted", "Size (Bell mesh scale)", "BP variable bellScale", "Actor location", "Bounds centre", "SmallBellPitch (1/size)"], rows))
    a("")
    a("Sizes match D-081 (%s): %s. Puzzle order (Puzzle_Bells): %s. Pitch is a multiplier on `SFX_LB_SmallBell_Strike`; a bigger bell is lower." % (
        sb["d081_sizes"], "yes" if sorted([b["bell_mesh_scale"] for b in sb["bells"]], reverse=True) == sb["d081_sizes"] else "NO - CHECK", " -> ".join(sb["puzzle_order"] or [])))
    a("")
    a("```")
    a("SmallBellPitch = {")
    for k, v in sb["SmallBellPitch"].items():
        a("  %s : %s" % (k, v))
    a("}")
    a("```")
    a("")
    # 3
    ar = R_["areas"]
    a("## 3. Areas")
    a("")
    a("### Post-process volumes")
    a("")
    a(md_table(["Volume", "Min", "Max", "Priority", "Unbound"], [[p["label"], fmt_v(p["bounds_min"]), fmt_v(p["bounds_max"]), p["priority"], p["unbound"]] for p in ar["post_process"]]))
    a("")
    a("### Storm zones (ALBStormZone)")
    a("")
    a(md_table(["Zone", "Min", "Max", "Exposure", "Priority", "Rotation"], [[z["label"], fmt_v(z["bounds_min"]), fmt_v(z["bounds_max"]), round(z["exposure"], 3), z["priority"],
                                                                        fmt_v(z["rotation"])] for z in ar["storm_zones"]]))
    a("")
    a("### Proposed ALBAudioZone (P16-3)")
    a("")
    a(md_table(["Zone", "Location", "Box extent (half)", "Rotation", "Priority", "RoofRain", "InteriorWind", "Howl", "Darkness", "RoomTone", "Volume"],
               [[z["name"], fmt_v(z["location"], 1), fmt_v(z["box_extent"], 1), "(0, 0, 0)", z["priority"], z["RoofRain"], z["InteriorWind"], z["Howl"], z["Darkness"],
                 z["RoomTone"] or "-", z["RoomToneVolume"]] for z in ar["proposed_zones"]]))
    a("")
    a("Outdoors is the default (no actor) and covers the courtyard, the approach and the gate arch; the garth is an explicit Garth zone so it is not part of the cloister.")
    a("")
    a("### Proposed AudioVolume (P16-3, same bounds)")
    a("")
    a(md_table(["Volume", "Location", "Brush scale (200 cm unit)", "Priority", "Reverb", "Reverb volume / fade", "Exterior volume / LPF Hz", "Interior volume"],
               [[z["name"], fmt_v(z["location"], 1), fmt_v(z["brush_scale_on_200cm_unit"], 3), z["priority"], z["reverb_effect"] or "none (bApplyReverb false)",
                 "%s / %s s" % (z["reverb_volume"], z["reverb_fade_s"]) if z["reverb_effect"] else "-", "%s / %s" % (z["exterior_volume"], z["exterior_lpf_hz"]),
                 z["interior_volume"]] for z in ar["proposed_zones"]]))
    a("")
    a("### Why these values")
    a("")
    a(md_table(["Zone", "Base storm zone", "Storm exposure", "Note"], [[z["name"], z["base_storm_zone"], round(z["storm_exposure"], 3), z["note"]] for z in ar["proposed_zones"]]))
    a("")
    a("### Overlaps and ambiguity")
    a("")
    ov = ar["overlaps"]
    a(md_table(["A", "B", "Overlap size", "Priority A / B", "Winner"], [[o["a"], o["b"], fmt_v(o["overlap_size"], 1), "%s / %s" % (o["priority_a"], o["priority_b"]), o["winner"]] for o in ov]) if ov
      else "No overlaps.")
    a("")
    a("Ambiguous overlaps (equal priority): **%d**." % sum(1 for o in ov if o["winner"] == "AMBIGUOUS"))
    zc = ar["zone_sample_check"]
    a("Zone assignment check against the floor samples (capsule centre = floor + %.0f cm): %d match, %d mismatch." % (R_["floors"]["player_half_height"], zc["matches"], zc["mismatches"]))
    if zc["details"]:
        a("")
        a(md_table(["Sample", "Area", "Centre", "Expected", "Got"], [[d["id"], d["area"], fmt_v(d["centre"], 0), d["expected"], d["got"]] for d in zc["details"]]))
    a("")
    a("### Roof checks (upward traces and overhead actors)")
    a("")
    a(md_table(["Point", "XY", "From z", "Upward trace: first hit z", "Actors overhead (bounds lookup, lowest first)"],
               [[r["name"], fmt_v(r["xy"]), r["from_z"], r["first_hit_above_z"] if r["first_hit_above_z"] is not None else "none",
                 ", ".join(o["label"] for o in r["overhead_actors"][:4]) or "none"] for r in ar["roof_checks"]]))
    a("")
    a("### Gatehouse and well house")
    a("")
    for line in ar["enclosure_notes"]:
        a("- " + line)
    a("")
    # 4
    fl = R_["floors"]
    st = fl["summary"]["stats"]
    a("## 4. Floors")
    a("")
    a("Method: for each sample point a probe trace (`SceneTools.trace_world`, from floor estimate + 150 cm down 450 cm) finds the floor; then the footstep trace is repeated "
      "exactly as `ULBFootstepComponent::EmitStep` does it: start at the capsule centre (floor + %.0f cm), end %.0f cm lower (half height + %.0f extra), complex collision %s, "
      "channel Visibility. The hit actor is resolved by bounds (`find_actors` with a 1.5 cm box at the hit point, object types WorldStatic/WorldDynamic, the actor whose bounds "
      "contain the point and whose top is nearest). **This is an approximation**: `trace_world` returns only the distance (no actor, component or physical material, and its "
      "channel is not documented), so the physical material the real trace would return cannot be read; the actor and its component/material data come from the bounds lookup." % (
          fl["player_half_height"], fl["player_half_height"] + fl["footstep_extra_depth"], fl["footstep_extra_depth"], fl["footstep_trace_complex"]))
    a("")
    a("- Samples: %d (%s). Resolved to an actor: %d. Footstep-geometry trace confirmed a floor under the capsule: %d of %d. Of the resolved hits, **%d are floors** and %d are props, kerbs or volumes (listed, not counted)." % (
        st["samples"], ", ".join("%s %d" % (k, v) for k, v in sorted(st["by_status"].items())), st["resolved"], st["footstep_trace_hit"], st["resolved"],
        st["floor_hits"], st["non_floor_hits"]))
    a("- Greybox or collision actors (hidden shell with bVisible false, or an /Engine/BasicShapes primitive; D-068), counted on the floor hits: **%d of %d = %.1f %%** (%s). Counted on every resolved hit it is %.1f %%; counted on the %d hand-picked floor hits only (no Warden-marker points, which crowd the crypt and cloister) it is %.1f %%." % (
        st["greybox_or_collision"], st["floor_hits"], 100 * st["greybox_fraction"], ", ".join("%s %d" % (k, v) for k, v in sorted(st["by_reason"].items())),
        100 * st["greybox_fraction_all_resolved"], st["floor_hits_no_markers"], 100 * st["greybox_fraction_no_markers"]))
    a("- Collision profiles of the floor hits: %s. Placed actors with a PhysMaterialOverride already: %d. Hit materials with a physical material: %d." % (
        ", ".join("%s %d" % (k, v) for k, v in sorted(st["by_collision_profile"].items())), st["has_phys_override"], st["has_material_phys"]))
    a("- **Method rule verdict (plan 7.4, 80 %% threshold): %s.**" % st["method"])
    a("")
    a("### Per area")
    a("")
    a(md_table(["Area", "Samples", "Resolved", "Floor hits", "Greybox/collision", "Proposed surfaces (hits)"],
               [[k, v["samples"], v["resolved"], v["floor_hits"], v["greybox"], ", ".join("%s %d" % (s, n) for s, n in sorted(v["surfaces"].items()))] for k, v in st["per_area"].items()]))
    a("")
    a("### Actor group -> proposed surface (method A: the hit actors that would carry the override)")
    a("")
    a(md_table(["Hit actor group (label prefix)", "Hits", "Areas", "Mesh", "Material(s) underfoot", "Visible art over it", "Collision", "Kind", "Proposed surface", "Reason"],
               [[g["group"], g["hits"], ", ".join(g["areas"]), ", ".join(g["meshes"]), ", ".join(g["materials"]) or "-", ", ".join(g["visible_over"]) or "-",
                 ", ".join(g["collision"]), ", ".join(g["greybox"]), ", ".join("%s %d" % (s, n) for s, n in sorted(g["surfaces"].items())), "; ".join(g["reasons"])[:200]]
                for g in fl["summary"]["by_actor"]]))
    a("")
    a("### Material instance -> proposed surface (method B: the MIs that would carry the physical material)")
    a("")
    a(md_table(["Material", "Hits", "Actor groups", "Areas", "Proposed surface", "Reason"],
               [[g["material"], g["hits"], ", ".join(g["actors"])[:120], ", ".join(g["areas"]), ", ".join("%s %d" % (s, n) for s, n in sorted(g["surfaces"].items())),
                 "; ".join(g["reasons"])[:160]] for g in fl["summary"]["by_material"]]))
    a("")
    a("Water: the crypt flood planes `CA_Water_*` have NoCollision, so the footstep trace never touches them; the floor under them is the hidden `CryptFloor_*` shell. Planes: %s. "
      "Standing in water is therefore a XY-and-height test (floor z <= plane z + 15), and a Water override on the big `CryptFloor_*` shells would make the whole crypt wet: P16-3 needs "
      "either a thin Visibility-blocking box under each pool (outside the pit) or a footstep-side rule. Cobble puddles (`MI_Env_Floor_Puddled*`, a puddle inside the material of the "
      "kit slabs) stay Stone by rule." % (", ".join("%s z %.0f" % (p["label"], p["bounds_max"][2]) for p in fl["summary"]["water_planes"]) or "none found"))
    a("")
    a("### Every sample")
    a("")
    rows = []
    for s in fl["samples"]:
        vu = s.get("visual_under")
        rows.append([s["id"], s["area"], fmt_v(s["xy"]), s.get("probe_hit_z", "-"), s.get("status") + ("" if s.get("is_floor") or s.get("status") != "ok" else "") if s.get("status") != "ok" else ("floor" if s.get("is_floor") else "not floor"),
                     s.get("actor_label", "-"), base_name(s.get("mesh")) or "-", ", ".join(base_name(m) for m in s.get("materials") or []) or "-",
                     (vu["label"] + " " + ",".join(base_name(m) for m in vu["materials"])) if vu else "-", s.get("collision_profile", "-"), s.get("greybox_reason", "-"),
                     s.get("surface") or "-"])
    a(md_table(["Id", "Area", "XY", "Floor z", "Result", "Hit actor", "Mesh", "Material", "Visible art over it", "Collision", "Kind", "Surface"], rows))
    a("")
    # 5
    gb = R_["great_bell"]
    a("## 5. Great bell")
    a("")
    a("- Actor `%s` (%s) at %s; bounds %s .. %s." % (gb["actor"]["label"], gb["actor"]["class"], fmt_v(gb["actor"]["location"], 0), fmt_v(gb["actor"]["bounds_min"], 1),
                                                  fmt_v(gb["actor"]["bounds_max"], 1)))
    a("- **BellLocation = %s** (bounds centre of the bell mesh; the origin is its top at z %.0f). The frame `TWA_BellFrame` is centred at %s; the belfry floor top is z 2500." % (
        fmt_v(gb["bell_location"], 1), gb["actor"]["location"][2], fmt_v(gb["frame_centre"], 0) if gb["frame_centre"] else "n/a"))
    a("")
    # 6
    wd = R_["warden"]
    a("## 6. Warden")
    a("")
    a("- Classes: %s." % ", ".join(c.rsplit(".", 1)[-1] for c in wd["classes"]))
    a("- Placed Warden: %s." % "; ".join("%s (%s, chain %s) at %s" % (w["label"], w["class"], " > ".join(w["parent_chain"][:2]), fmt_v(w["location"], 0)) for w in wd["warden_actors"]))
    a("- Spawn points: %s." % "; ".join("%s %s (MinStage %s, route %s)" % (s["label"], fmt_v(s["location"], 0), s["props"]["MinStage"], s["props"]["RouteId"]) for s in wd["spawn_points"]))
    a("- Patrol points: %d; search points: %d (used as floor samples)." % (len(wd["patrol_points"]), len(wd["search_points"])))
    a("")
    a(md_table(["Apparition", "Class", "Trigger tag", "Arm delay s", "Station location", "Walk path pts", "Skeletal figure"],
               [[p["label"], p["class"], ", ".join(p["trigger_tag"]), p["arm_delay_s"], fmt_v(p["stations"][0]["location"], 0) if p["stations"] else "-",
                 p["stations"][0]["walk_path_points"] if p["stations"] else "-", p["skeletal_figure"]] for p in wd["apparitions"]]))
    a("")
    # 7
    cf = R_["config"]
    a("## 7. Audio config now")
    a("")
    for line in cf["engine_ini"] + cf["game_ini_audio"]:
        a("- `Config`: " + line)
    a("- Placed actors: %s." % ", ".join("%s %d" % (k, v) for k, v in cf["placed_actor_counts"].items()))
    sa = cf["sound_assets_under_game_lastbell"]
    a("- Sound assets under /Game/LastBell: %s." % ("none of any class (" + ", ".join(sa.keys()) + ")" if all(v == [] for v in sa.values()) else json.dumps(sa)))
    a("- Existing: %s." % ", ".join("%s %s" % (k, v) for k, v in cf["exists"].items()))
    a("")
    # 8
    mc = R_["mcp"]
    a("## 8. MCP capability probe (describe only)")
    a("")
    a("Searched %d tools in %d toolsets." % (mc["tools"], mc["toolsets"]))
    a("")
    a(md_table(["Asset", "Create / import tool", "Closest tools and precedent", "Factory class", "Verdict"],
               [[r["asset"], r["create_import_tool"], r["closest"], r["factory_exists"], r["verdict"]] for r in R_["capabilities"]["rows"]]))
    a("")
    for line in R_["capabilities"]["other_findings"]:
        a("- " + line)
    a("")
    a("Property names found on the class default objects (ObjectTools.list_properties, read only):")
    a("")
    for k, v in mc["classes"].items():
        a("- %s: %s" % (k, ("%d properties; non-inherited-noise names: %s" % (v["property_count"], ", ".join(v.get("all_properties") or v["key_properties"]))) if v.get("cdo_readable")
                          else "not readable (%s)" % v.get("error")))
    a("")
    a("Engine assets that could be duplicated as a starting point (AssetTools.find_assets over the whole project, first hits):")
    a("")
    for k, v in mc.get("engine_candidates", {}).items():
        a("- %s: %s" % (k, ", ".join(v) if isinstance(v, list) and v else v))
    a("")
    # findings
    a("## 9. Findings for the lead")
    a("")
    for f in R_["findings"]:
        a("- " + f)
    a("")
    return "\n".join(L_)


# ---------------------------------------------------------------------------------------------- assembly
UNMAPPED_12 = ["BP_PuzzleCandle", "BP_DialLever_Crypt", "BP_Door_Base_Dungeon", "BP_SequencePuzzle", "BP_Inspectable_Note", "BP_RitualMechanism_ChapelBells",
               "BP_RitualMechanism_CryptWinch", "BP_TagInteractable_ChapelKey", "BP_TagInteractable_CryptCrank", "BP_SmallBell_Cloister",
               "BP_RitualMechanism_TowerCapstan", "BP_TagInteractable_GreatBell"]


def enclosure_notes(areas):
    rc = {r["name"]: r for r in areas["roof_checks"]}

    def over(name):
        r = rc.get(name)
        return [] if r is None else [o["label"] for o in r["overhead_actors"]]

    def trace(name):
        r = rc.get(name)
        return "n/a" if r is None else ("open" if r["first_hit_above_z"] is None else "hit at z %.0f" % r["first_hit_above_z"])

    notes = []
    wh_over = over("wellhouse centre") + over("wellhouse N gap")
    notes.append("Well house (KD_Well_W/E/S walls plus pillars KD_Well_N1/N2, x 1275 to 1725, y -2225 to -1775, walls 250 cm high, north side open between the pillars; the chapel "
                 "key lies inside): at head height the upward trace is %s / %s and the actors overhead are %s. Nothing roofs it, so it is open to the sky: **no audio zone** "
                 "(outdoors default)." % (trace("wellhouse centre"), trace("wellhouse N gap"), wh_over or "none"))
    notes.append("Gatehouse: the gate is `KG_GateArch` (x 0 to 300, y -600 to 600, 800 cm high), an arched opening through a wall, with the gatehouse lantern, crates and warm light "
                 "just inside at x 300 to 470 (`Light_Gatehouse_Warm`); there is no separate gatehouse building. Upward traces: under the arch %s, beside it %s, at the lantern %s; "
                 "actors overhead at the lantern: %s. A 300 cm deep archway is shorter than the 1 s reverb fade and the 4 Hz zone check can resolve: **no audio zone**; the approach, "
                 "the arch and the courtyard stay outdoors." % (trace("gate arch"), trace("gate arch N side"), trace("gatehouse light"), over("gatehouse light") or "none"))
    notes.append("Roofs are art meshes with NoCollision, so an upward trace cannot see them; the overhead lists above are bounds lookups. Roofed (something overhead): chapel nave %s, "
                 "sacristy %s, cloister walk %s and %s, tower stair %s, belfry %s; crypt vault %s. NOT roofed (nothing overhead): courtyard, garth, the shortcut passage lane, well house."
                 % (over("chapel nave")[:2], over("chapel sacristy")[:1], over("cloister S walk")[:2], over("cloister N walk")[:2], over("tower stair landing 5")[:2],
                    over("belfry")[:3], over("crypt W")[:1]))
    return notes


def build_findings(R_):
    f = []
    bells = R_["small_bells"]
    f.append("F-1 (decision needed, C++): `ULBAudioSubsystem::NotifyStepAccepted/Failed/Solved` play the SmallBell sounds for ANY `ULBSequencePuzzleComponent`. L_Monastery has two: "
             "`Puzzle_Bells` (the cloister bells, steps State.Tower.Bell.3,1,4,2) and `Puzzle_Candles` (the chapel candles, State.Chapel.Candle.3,1,4,2). As written, lighting a chapel "
             "candle in order strikes a small bell at the candle (pitch 1.0, no SmallBellPitch entry), a wrong candle plays the dissonant SmallBellFail and the solved chapel puzzle "
             "plays SmallBellSolved. Options: (a) gate the strike by `SmallBellPitch.Contains(Step)` and fail/solved by 'all steps are in SmallBellPitch'; (b) a per-puzzle settings "
             "entry; (c) accept it for the candles. The candle's own `Candle_Light` cue still plays from its interactable row.")
    f.append("F-2: the belfry floor is z 2500 (`TWA_BelfryFloor` top), but `SZN_Belfry` starts at z 2650, so a standing player there (capsule centre 2588) is still inside the tower-shaft "
             "box. The proposed audio belfry box starts at z 2400 with priority 4 > 3 (tower stair), overlap z 2400 to 2650.")
    f.append("F-3: `SZN_Chapel` bottom is z -40 and `SZN_Crypt` top is z -45: a 5 cm gap on the crypt stair would fall back to outdoors. The proposed crypt box tops at z -20 (priority 2 > 1).")
    f.append("F-3b: the shortcut passage is NOT roofed and NOT as wide as SZN_Passage: it is a 600 cm lane between walls PSA_Wall_PS (y 1660 to 1700) and PSA_Wall_PN (y 2300 to 2340), "
             "x 6040 to 9460, 800 cm walls, nothing overhead. SZN_Passage (y 900 to 2600, exposure 0.3) spans the walls and the open ground south of them. The audio box is the lane; "
             "RoofRain 0. Worth a look by the lead: exposure 0.3 for an open-top lane may be low (P14 value, not touched here).")
    f.append("F-4: the garth sits inside the cloister box; the proposed `Garth` zone (priority 2, outdoor values, AudioVolume without reverb) cancels the cloister room tone and reverb there.")
    f.append("F-5: all 4 doors are wood (leaf `SM_Dungeon_door`, `MI_Prop_Wood_Weathered` backing); no stone door exists. `SFX_LB_Door_Stone_Open_*` has no consumer in this map.")
    f.append("F-6: the crank (`Crank_Winch`, prompt 'Take crank') is a pickup, not a mechanism; the proposal uses Key_Pickup, not Winch (deviation from the brief, reason in the table).")
    st = R_["floors"]["summary"]["stats"]
    f.append("F-7: floor method verdict: %.1f %% of the %d floor hits (%.1f %% of all %d resolved hits, %.1f %% of the %d hand-picked ones without Warden-marker points) are on greybox "
             "or collision actors (hidden shells and /Engine/BasicShapes cubes), so by the plan's 80 %% rule the method is **%s**. It is borderline: the visible kit slabs (courtyard, "
             "approach, chapel) are real art meshes with MI materials, but they already carry only Stone, and every non-Stone floor (Wood landings, flights and belfry floor; garth Grass; "
             "crypt Water) lies on a hidden shell or has no collision of its own, except the two courtyard garden beds (`Garden_Earth_*`, art meshes with collision, Earth). Caveat: `trace_world` returns only a distance, so actors are found by bounds (an approximation) and "
             "the real physical-material result of the footstep trace cannot be read over MCP; the check needs the `LastBell.Audio` footstep test or a play test."
             % (100 * st["greybox_fraction"], st["floor_hits"], 100 * st["greybox_fraction_all_resolved"], st["resolved"], 100 * st["greybox_fraction_no_markers"],
                st["floor_hits_no_markers"], st["method"]))
    f.append("F-8: MCP cannot import a WAV or create SoundClass, SoundMix, SoundAttenuation, SoundConcurrency, ReverbEffect or PhysicalMaterial assets with any listed tool; "
             "see section 8 for the S1 order of attempts. AudioVolume and AmbientSound actors can be spawned with `add_to_scene_from_class` (precedent: PostProcessVolume, 200 cm unit brush).")
    ex = R_["config"]["exists"]
    f.append("F-9: audio state now: AudioMaxChannels 64 present; no AudioVolume, AmbientSound, ALBAudioZone or ALBAmbientEmitter actors; no sound assets under /Game/LastBell; "
             "`/Game/LastBell/Audio` exists: %s, `DA_Audio` exists: %s (config already points at it)." % (ex.get("/Game/LastBell/Audio"), ex.get("/Game/LastBell/Data/DA_Audio")))
    f.append("F-10: BellLocation (%s) is the centre of the bell mesh; the bell hangs inside `TWA_BellFrame` and the belfry floor is 2500, so the bell is about 250 cm above the floor "
             "and inside the belfry audio box." % fmt_v(R_["great_bell"]["bell_location"], 1))
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="ignore every stage cache")
    ap.add_argument("--only", default="", help="comma list of stages to re-run (others use the cache): interactables,bell,areas,floors,floors2,warden,config,mcp")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()
    stages = ["interactables", "bell", "areas", "floors", "floors2", "warden", "config", "mcp"]
    redo = set(stages) if a.refresh else set(s for s in a.only.split(",") if s)
    try:
        ed = Ed()
        before = read_state(ed)
        say("state before: %s" % json.dumps({k: v for k, v in before.items() if k != "never_save_dirty"}))
        if not state_clean(before):
            say("The editor is not in the expected clean state (PIE off, L_Monastery loaded, nothing dirty): stop. %s" % json.dumps(before))
            sys.exit(2)
        cache = Cache(False)
        data = {}
        fns = {"interactables": stage_interactables, "bell": stage_bell, "areas": stage_areas, "floors": stage_floors, "floors2": stage_floors2, "warden": stage_warden, "config": stage_config,
               "mcp": stage_mcp}
        for s in stages:
            cache.refresh = s in redo
            data[s] = cache.get(s, (lambda f=fns[s]: f(ed)))
        after = read_state(ed)
        say("state after:  %s" % json.dumps({k: v for k, v in after.items() if k != "never_save_dirty"}))
    except EditorStop as e:
        say("STOP: editor problem (%s). Nothing was written." % e)
        sys.exit(3)
    same = (after["actor_count"] == before["actor_count"] and state_clean(after))
    inter = data["interactables"]
    groups = group_interactables(inter)
    gl = list(groups.values())
    for g in gl:
        g["actors"] = g["actors"]
    missing = [c for c in UNMAPPED_12 if c not in CUE_PROPOSALS]
    uncovered = [g["class"] for g in gl if g["class"] not in CUE_PROPOSALS]
    areas = data["areas"]
    proposed = build_zone_proposals(areas)
    floors = data["floors2"]
    summary = summarize_floors(floors, areas)
    floors["summary"] = summary
    areas["proposed_zones"] = proposed
    areas["overlaps"] = overlap_report(proposed)
    areas["zone_sample_check"] = check_zone_samples(proposed, floors)
    areas["enclosure_notes"] = enclosure_notes(areas)
    gb = data["bell"]["actors"][0] if data["bell"]["actors"] else None
    frame = next((m for m in data["bell"]["tower_bell_meshes"] if m["label"] == "TWA_BellFrame"), None)
    mcp = data["mcp"]
    R_ = {
        "meta": {"generated": time.strftime("%Y-%m-%d %H:%M"), "script": "Tools/audio/p16_f0_survey.py", "level": MAP_PKG, "read_only": True,
                 "note": "stages are cached in Saved/p16_f0_scratch; state_before/state_after are read by this invocation"},
        "state_before": before, "state_after": after, "state_unchanged": same,
        "interactables": {"actors": inter["actors"], "groups": gl, "cue_proposals": CUE_PROPOSALS, "unmapped_check": missing, "classes_without_proposal": uncovered,
                          "scanned_classes": inter["scanned_classes"]},
        "small_bells": build_small_bells(inter),
        "areas": areas,
        "floors": floors,
        "great_bell": {"actor": {k: gb[k] for k in ("label", "class", "location", "bounds_min", "bounds_max", "bounds_centre")} if gb else None,
                       "bell_location": gb["bounds_centre"] if gb else None, "frame_centre": frame["bounds_centre"] if frame else None, "tower_bell_meshes": data["bell"]["tower_bell_meshes"]},
        "warden": data["warden"], "config": data["config"], "mcp": mcp, "capabilities": capability_matrix(mcp),
    }
    R_["findings"] = build_findings(R_)
    if not a.no_write:
        os.makedirs(OUT_DIR, exist_ok=True)
        with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
            json.dump(R_, f, indent=1, sort_keys=False)
        with open(OUT_MD, "w", encoding="utf-8", newline="\n") as f:
            f.write(build_markdown(R_))
        say("wrote %s and %s" % (OUT_JSON, OUT_MD))
    say("interactable classes without a proposal: %s; the 12 unmapped classes missing: %s" % (uncovered, missing))
    say("state unchanged: %s" % same)
    sys.exit(0 if same and not missing and not uncovered else 2)


if __name__ == "__main__":
    main()
