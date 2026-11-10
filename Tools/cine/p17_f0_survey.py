"""P17-F0: the read-only survey for Phase 17 (Docs/plans/P17_CINEMATICS.md section 7, items 1 to 5 and 7; item 6 (Warden slots, bones) is ON HOLD).

Run with the editor open on L_Monastery, PIE off (Windows Python; from Git Bash prefix MSYS_NO_PATHCONV=1):
    python -I Tools/cine/p17_f0_survey.py [--refresh] [--only helpers,mcp,spawn,gate,wall,bell,tower,sight,notes]

Outputs (default --out Docs/ArtTest/cine): p17_f0.json (all data) and p17_f0_tables.md (readable tables and the proposals).

READ ONLY. The script calls only get_*, find_*, is_*, list_*, describe_toolset, IsPIERunning and trace_world. It never sets, creates,
deletes, saves, loads or moves anything, never starts PIE and never takes a capture. The dirty state of L_Monastery and of the never-save
list (p15_level.NEVER_SAVE) is read before and after, and the actor census is compared; the run fails (exit 2) if anything changed.

TRACES. SceneTools.trace_world returns only the distance to the first blocking hit (channel not documented). The level's visible art is mostly
NoCollision; the collision is the hidden greybox (D-068), so every trace sees greybox collision only. In this level the BP_TagTrigger boxes
(Trig_CourtyardEntered, Trig_TowerTop, ...) DO block trace_world (a down trace from above Trig_CourtyardEntered returns its top, z 300; a trace
that starts inside one returns 0), so the Tracer below detects such helper volumes once (stage "helpers") and steps through them. A real wall
hidden inside a helper volume's box would be missed: the number of volume skips is recorded.

Each stage caches its result in Saved/p17_f0_scratch/<stage>.json (git-ignored); --refresh ignores the cache. The committed outputs were built from one
full --refresh run, then the stages gate, wall and proposals were re-run with --only after two fixes (a jitter correction of the passage measurements and extra proposal
information); every other stage is from that same session. If the editor drops the connection or hangs for more than 180 s the script stops ("STOP", exit 3) and writes nothing.
"""
import argparse
import json
import math
import os
import re
import sys
import time
from collections import OrderedDict

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Tools", "lighting"))
sys.path.insert(0, os.path.join(ROOT, "Tools", "fx"))
sys.path.insert(0, os.path.join(ROOT, "Tools", "mcp"))
import p14_3_level as L  # noqa: E402  (Ed client, EditorStop, helpers)
import p15_level as P15  # noqa: E402  (NEVER_SAVE)
from p14_3_level import EditorStop, J, R, v3  # noqa: E402

S, A, O, AS, E = L.S, L.A, L.O, L.AS, L.E
MAP_PKG = L.MAP_PKG
NEVER_SAVE = list(P15.NEVER_SAVE)
SCRATCH = os.path.join(ROOT, "Saved", "p17_f0_scratch")
MAPPFX = "/Game/LastBell/Maps/L_Monastery.L_Monastery:PersistentLevel."
CHAR_CDO = "/Game/LastBell/Blueprints/BP_LBCharacter.Default__BP_LBCharacter_C"
RO_TOOLS = ("trace_world", "list_properties", "describe_toolset", "list_toolsets", "get_class")


def say(msg):
    print(msg, flush=True)


def rr(v, n=1):
    return [round(float(x), n) for x in v]


def objname(ref):
    return ref.rsplit(".", 1)[-1] if ref else None


def short(cls_path):
    return cls_path.rsplit(".", 1)[-1] if cls_path else None


def sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def norm(a):
    return math.sqrt(sum(x * x for x in a))


def dist3(a, b):
    return norm(sub(a, b))


def dist2(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def yaw_pitch(frm, to):
    dx, dy, dz = to[0] - frm[0], to[1] - frm[1], to[2] - frm[2]
    return math.degrees(math.atan2(dy, dx)), math.degrees(math.atan2(dz, math.hypot(dx, dy)))


# ---------------------------------------------------------------------------------------------- stage cache
class Cache:
    def __init__(self, refresh):
        self.refresh = refresh
        os.makedirs(SCRATCH, exist_ok=True)

    def get(self, name, fn):
        path = os.path.join(SCRATCH, name + ".json")
        if not self.refresh and os.path.exists(path):
            say("cache  %s" % name)
            return json.load(open(path, encoding="utf-8"))
        t0 = time.time()
        say("stage  %s ..." % name)
        data = fn()
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, indent=1)
        say("stage  %s done in %.0f s" % (name, time.time() - t0))
        return data


# ---------------------------------------------------------------------------------------------- editor client (read only)
class Ed(L.Ed):
    def call(self, ts, tool, args=None):
        """p14_3_level.Ed.call, but trace_world and the other read-only tools also retry on a connection reset."""
        try:
            return super().call(ts, tool, args)
        except EditorStop as e:
            if tool in RO_TOOLS and "ConnectionResetError" in str(e):
                for attempt in range(3):
                    say("NOTE  connection reset on %s; retry %d/3 (read only)" % (tool, attempt + 1))
                    time.sleep(2)
                    try:
                        self.ue = L.UE180()
                        return self.ue.call(ts, tool, args or {})
                    except Exception as e2:  # noqa: BLE001
                        last = e2
                raise EditorStop("%s: %s" % (tool, last))
            raise

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

    def find_tag(self, tag):
        return [R(x) for x in self.call(S, "find_actors", {"name": "", "tag": tag, "collision_channels": []}) or []]

    def find_box(self, lo, hi):
        box = {"min": L.vec(lo), "max": L.vec(hi), "isValid": True}
        return [R(x) for x in self.call(S, "find_actors", {"name": "", "tag": "", "collision_channels": [], "bounds": box}) or []]

    def props_safe(self, ref, names):
        """get_properties one name at a time (an unreadable name must not hide the others)."""
        out = {}
        for n in names:
            try:
                out.update(self.props(ref, [n]))
            except RuntimeError:
                out[n] = "<unreadable>"
        return out

    def raw_trace(self, a, b):
        return self.call(S, "trace_world", {"start": L.vec(a), "end": L.vec(b)})


# ---------------------------------------------------------------------------------------------- helper-aware tracer
HELPER_CLASSES = [
    ("BP_TagTrigger", "/Game/LastBell/Blueprints/Interactables/BP_TagTrigger.BP_TagTrigger_C"),
    ("LBCheckpoint", "/Script/LastBell.LBCheckpoint"),
    ("TriggerVolume", "/Script/Engine.TriggerVolume"),
    ("BP_KillVolume", "/Game/LastBell/Blueprints/Interactables/BP_KillVolume.BP_KillVolume_C"),
    ("BP_EndingTrigger", "/Game/LastBell/Blueprints/BP_EndingTrigger.BP_EndingTrigger_C"),
    ("LBAudioZone", "/Script/LastBell.LBAudioZone"),
    ("AudioVolume", "/Script/Engine.AudioVolume"),
    ("PostProcessVolume", "/Script/Engine.PostProcessVolume"),
    ("LBStormZone", "/Script/LastBell.LBStormZone"),
    ("PCGVolume", "/Script/PCG.PCGVolume"),
]
NOT_SOLID_PREFIXES = ("NavMeshBoundsVolume", "RecastNavMesh", "LBStormZone", "PostProcessVolume", "NiagaraActor", "LocalFogVolume", "PointLight", "SpotLight",
                      "RectLight", "DecalActor", "TriggerVolume", "PCGV", "PCGVolume", "PCGWorld", "LBAudio", "AudioVolume", "TargetPoint", "LBWarden", "LBCheckpoint",
                      "Emitter", "SkyLight", "ExponentialHeightFog", "DirectionalLight", "LBStateLightGroup", "LBAmbient", "LBPatrol", "LBSearch", "BP_TagTrigger",
                      "BP_EndingTrigger", "BP_KillVolume", "WorldSettings", "SkySphere", "Brush", "BuoyancyManager", "DefaultPhysicsVolume", "GameplayDebugger",
                      "AbstractNavData", "Actor_", "SkyAtmosphere", "VolumetricCloud")


class Tracer:
    """trace_world with the blocking helper volumes (Tracer.boxes) stepped through. trace(a, b) returns the distance from a of the first non-helper hit, or None."""

    def __init__(self, ed, boxes):
        self.ed = ed
        self.boxes = boxes          # list of {"label", "lo", "hi"}
        self.n_raw = 0
        self.n_skip = 0

    def raw(self, a, b):
        self.n_raw += 1
        return self.ed.raw_trace(a, b)

    def _inside(self, p):
        for bx in self.boxes:
            if all(bx["lo"][i] + 0.05 < p[i] < bx["hi"][i] - 0.05 for i in range(3)):
                return bx
        return None

    def _entering(self, p, u):
        """The helper box whose face the ray enters at the hit point p (p within 0.8 cm of the box and one more centimetre along the ray is inside it), or None.
        A hit on the OUTSIDE of a box the ray is leaving (e.g. a slab top coincident with a trigger's bottom face) is a real hit."""
        for bx in self.boxes:
            if all(bx["lo"][i] - 0.8 <= p[i] <= bx["hi"][i] + 0.8 for i in range(3)):
                q = [p[i] + u[i] * 1.0 for i in range(3)]
                if all(bx["lo"][i] + 0.05 < q[i] < bx["hi"][i] - 0.05 for i in range(3)):
                    return bx
        return None

    @staticmethod
    def _seg(a, u, lo, hi):
        """(t_in, t_out) of the ray a + t u through the box lo..hi, or None."""
        tmin, tmax = -1e18, 1e18
        for i in range(3):
            if abs(u[i]) < 1e-9:
                if not (lo[i] <= a[i] <= hi[i]):
                    return None
                continue
            t1, t2 = (lo[i] - a[i]) / u[i], (hi[i] - a[i]) / u[i]
            if t1 > t2:
                t1, t2 = t2, t1
            tmin, tmax = max(tmin, t1), min(tmax, t2)
        return None if tmax < tmin else (tmin, tmax)

    def _through(self, a, u, bx, t_in, total):
        """The ray is inside the blocking helper box bx from t_in. Returns ("hit", t) if a real solid (a box-like collision actor recorded in bx["solids"], including one
        flush with the box face the ray leaves through) is met inside it or at its exit face, else ("free", t_out + 0.02)."""
        seg = self._seg(a, u, bx["lo"], bx["hi"])
        t_out = seg[1] if seg else t_in
        best = None
        for so in bx.get("solids", []):
            sg = self._seg(a, u, so["lo"], so["hi"])
            if sg is None or sg[1] < t_in - 0.05:
                continue
            entry = max(sg[0], t_in)
            if entry <= t_out + 0.05 and entry <= total and (best is None or entry < best):
                best = entry
        if best is not None:
            return "hit", best
        return "free", t_out + 0.02

    JITTER = (0.37, 0.29, 0.13)    # both ends are shifted by this: a ray lying exactly in a helper volume's face plane (integer coordinates) returns inconsistent hits

    def trace(self, a, b):
        a = [a[i] + self.JITTER[i] for i in range(3)]
        b = [b[i] + self.JITTER[i] for i in range(3)]
        d = sub(b, a)
        total = norm(d)
        if total < 1e-6:
            return None
        u = [x / total for x in d]
        t0 = 0.0
        for _ in range(12):
            cur = [a[i] + u[i] * t0 for i in range(3)]
            bx = self._inside(cur)
            t_in = t0
            if bx is None:
                dd = self.raw(cur, b)
                if dd is None:
                    return None
                t = t0 + dd
                p = [a[i] + u[i] * t for i in range(3)]
                bx = self._entering(p, u)
                if bx is None:
                    return t
                t_in = t
            self.n_skip += 1
            kind, tv = self._through(a, u, bx, t_in, total)
            if kind == "hit":
                return tv
            t0 = tv
            if t0 >= total:
                return None
        return None

    def down(self, x, y, z0, depth=600.0):
        t = self.trace((x, y, z0), (x, y, z0 - depth))
        return None if t is None else z0 + self.JITTER[2] - t

    def up(self, x, y, z0, height=1500.0):
        t = self.trace((x, y, z0), (x, y, z0 + height))
        return None if t is None else z0 + self.JITTER[2] + t


def make_tracer(ed, helpers):
    boxes = [{"label": h["label"], "lo": h["lo"], "hi": h["hi"], "solids": h.get("solids", [])} for h in helpers["actors"] if h["blocks_trace"]]
    return Tracer(ed, boxes)


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


# ---------------------------------------------------------------------------------------------- stage helpers (which volumes block trace_world)
def stage_helpers(ed):
    out = {"actors": [], "note": "helper-volume classes; blocks_trace = a 80 cm down trace from 60 cm above the actor's bounds top at its XY centre hits at 60 cm"}
    seen = set()
    for name, path in HELPER_CLASSES:
        try:
            refs = ed.find_cls(path)
        except RuntimeError as e:
            say("  %-18s class not available (%s)" % (name, str(e)[:60]))
            out.setdefault("unavailable_classes", []).append(name)
            continue
        say("  %-18s %d actors" % (name, len(refs)))
        for r in refs:
            if r in seen:
                continue
            seen.add(r)
            b = ed.bounds(r)
            lo, hi = rr(b[0], 2), rr(b[1], 2)
            size = [hi[i] - lo[i] for i in range(3)]
            rec = {"label": ed.label(r), "object": objname(r), "class": name, "lo": lo, "hi": hi, "blocks_trace": False, "test_distance": None}
            if max(size) > 0.5 and b[2]:
                cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
                d = ed.raw_trace((cx, cy, hi[2] + 60.0), (cx, cy, hi[2] - 20.0))
                rec["test_distance"] = None if d is None else round(d, 2)
                rec["blocks_trace"] = d is not None and abs(d - 60.0) < 0.8
            out["actors"].append(rec)
    out["blocking"] = [h["label"] for h in out["actors"] if h["blocks_trace"]]
    # real collision geometry touching or inside each blocking volume (so the tracer can tell a hit on the volume from a hit on the floor or wall flush with it).
    # Only box-like shapes are recorded (an /Engine/BasicShapes Cube or a kit floor slab); their AABB is their shape.
    for h in out["actors"]:
        if not h["blocks_trace"]:
            continue
        h["solids"] = []
        h["solids_ignored_non_box"] = []
        for r in ed.find_box([x - 1.0 for x in h["lo"]], [x + 1.0 for x in h["hi"]]):
            on = objname(r)
            if on.startswith(NOT_SOLID_PREFIXES) or ed.label(r) == h["label"]:
                continue
            b = ed.bounds(r)
            lo2, hi2 = rr(b[0], 2), rr(b[1], 2)
            if max(hi2[i] - lo2[i] for i in range(3)) > 100000:
                continue
            mc = mesh_collision(ed, r)
            if not mc or mc.get("collision_enabled") != "QueryAndPhysics":
                continue
            box_like = (mc.get("mesh") == "Cube") or ("Floor_Slab" in (mc.get("mesh") or ""))
            rec2 = {"label": ed.label(r), "lo": lo2, "hi": hi2, "mesh": mc.get("mesh")}
            (h["solids"] if box_like else h["solids_ignored_non_box"]).append(rec2)
        say("  %s: %d box-like solids, %d non-box collision actors ignored" % (h["label"], len(h["solids"]), len(h["solids_ignored_non_box"])))
    out["blocking_by_class"] = {}
    for h in out["actors"]:
        k = out["blocking_by_class"].setdefault(h["class"], {"tested": 0, "blocking": 0})
        k["tested"] += 1
        k["blocking"] += 1 if h["blocks_trace"] else 0
    say("  blocking helper volumes: %d of %d (%s)" % (len(out["blocking"]), len(out["actors"]), out["blocking_by_class"]))
    return out


# ---------------------------------------------------------------------------------------------- item 1: MCP
MCP_KEYWORDS = re.compile(r"sequencer|levelsequence|level sequence|moviescene|movie|cinematic|widget|umg|python", re.I)
CAPABILITY_NAME_RE = {
    "a_level_sequence": re.compile(r"sequence|binding|track|section|spawnable|keyframe|camera", re.I),
    "b_python": re.compile(r"python|exec|script|console|run_command|eval", re.I),
    "c_umg": re.compile(r"widget|umg|slot|designer", re.I),
}


def stage_mcp(ed):
    out = {"toolsets": [], "matching": {}, "all_tool_counts": {}}
    listing = ed.ue.raw("list_toolsets", {})
    entries = re.findall(r"^- ([\w\.]+):\s*(.*(?:\n(?!- [\w\.]+:).*)*)", listing, re.M)
    say("  %d toolsets listed" % len(entries))
    for name, desc in entries:
        desc1 = " ".join(desc.split())
        rec = {"name": name, "description": desc1[:240]}
        out["toolsets"].append(name)
        d = None
        for attempt in range(3):
            try:
                d = ed.ue.describe(name)
                break
            except Exception as e:  # noqa: BLE001
                time.sleep(2)
                try:
                    ed.ue = L.UE180()
                except Exception:  # noqa: BLE001
                    pass
                last = e
        if d is None:
            rec["error"] = str(last)[:120]
            out["all_tool_counts"][name] = None
            continue
        tools = []
        for t in d["tools"]:
            tn = t["name"].split(".")[-1]
            td = " ".join((t.get("description") or "").split())
            first = re.split(r"(?<=[.:])\s", td, maxsplit=1)[0][:150]
            tools.append({"name": tn, "purpose": first, "required": t["inputSchema"].get("required") or []})
        out["all_tool_counts"][name] = len(tools)
        if MCP_KEYWORDS.search(name) or MCP_KEYWORDS.search(desc1):
            rec["tools"] = tools
            out["matching"][name] = rec
        else:
            # any toolset: record tools whose NAME suggests python/exec (capability b) so nothing is missed
            hits = [t for t in tools if PY_TOOL_RE.search(t["name"])]
            if hits:
                rec["tools"] = hits
                rec["only_name_matches"] = True
                out["matching"][name] = rec
        say("  %-60s %3d tools%s" % (name, len(tools), "  [matches]" if name in out["matching"] else ""))
    return out


PY_TOOL_RE = re.compile(r"python|console|run_?command|execute_tool_script|exec_?script|run_?script", re.I)


def mcp_answers(mcp):
    """Capability answers (a) Level Sequences, (b) arbitrary editor Python, (c) UMG widgets, derived from the recorded tool lists."""
    m = mcp["matching"]
    seq = [k for k in m if "sequencer" in k.lower()]
    seq_tools = sorted({t["name"] for k in seq for t in m[k].get("tools", [])})
    umg = [k for k in m if "umg" in k.lower()]
    umg_tools = sorted({t["name"] for k in umg for t in m[k].get("tools", [])})
    py = {k: [t["name"] for t in v.get("tools", []) if PY_TOOL_RE.search(t["name"])] for k, v in m.items()}
    py = {k: v for k, v in py.items() if v}
    key = ["create_level_sequence", "open_sequence", "close_sequence", "set_display_rate", "set_playback_range", "set_tick_resolution", "add_spawnable_from_class",
           "add_spawnable_from_instance", "create_camera", "add_actors", "add_track_to_binding", "add_track_to_sequence", "add_section", "set_section_range", "set_section_ease_in",
           "set_section_ease_out", "set_camera_cut_binding", "add_marked_frame", "add_event_trigger_section", "set_section_animation", "play", "set_playhead_frame"]
    ui_anim = [n for n in umg_tools if re.search(r"anim", n, re.I)]
    return {"sequencer_toolsets": seq, "sequencer_tool_count": len(seq_tools), "sequencer_key_tools_present": [n for n in key if n in seq_tools],
            "sequencer_key_tools_missing": [n for n in key if n not in seq_tools], "umg_toolsets": umg, "umg_tool_count": len(umg_tools), "umg_tools": umg_tools,
            "umg_animation_tools": ui_anim, "python_candidates": py}


# ---------------------------------------------------------------------------------------------- item 2: spawn and player
def stage_spawn(ed, tr):
    out = {}
    ps = []
    for r in ed.find_cls("/Script/Engine.PlayerStart"):
        rec = {"label": ed.label(r), "object": objname(r), "class": short(ed.cls(r))}
        rec.update(ed.xf_full(r))
        cap = [c for c in ed.comps(r) if ed.cls(c) == "/Script/Engine.CapsuleComponent"]
        if cap:
            p = ed.props(cap[0], ["capsuleRadius", "capsuleHalfHeight"])
            rec["start_capsule"] = {"radius": p["capsuleRadius"], "half_height": p["capsuleHalfHeight"]}
        ps.append(rec)
    out["player_starts"] = ps
    # CP_Approach
    cps = ed.find("CP_Approach")
    cpr = {}
    if cps:
        r = cps[0]
        cpr = {"label": "CP_Approach", "object": objname(r), "class": short(ed.cls(r))}
        cpr.update(ed.xf_full(r))
        trig = [c for c in ed.comps(r) if c.endswith(".Trigger")]
        if trig:
            p = ed.props(trig[0], ["boxExtent", "relativeLocation", "relativeRotation", "relativeScale3D"])
            ext = v3(p["boxExtent"])
            cpr["box_extent"] = rr(ext, 2)
            cpr["trigger_rel_location"] = rr(v3(p["relativeLocation"]), 2)
            cpr["trigger_rel_scale"] = rr(v3(p["relativeScale3D"]), 3)
            root = R(ed.call(A, "get_root_component", {"actor": {"refPath": r}}))
            cpr["trigger_is_root"] = (root == trig[0])
            # for the root component the relative transform already is the world transform (MCP_NOTES P10 item 6); otherwise it is an offset from the actor (actor rotation 0 here)
            centre = cpr["trigger_rel_location"] if cpr["trigger_is_root"] else [cpr["location"][i] + cpr["trigger_rel_location"][i] for i in range(3)]
            sc = cpr["trigger_rel_scale"]
            half = [ext[i] * sc[i] * (cpr["scale"][i] if not cpr["trigger_is_root"] else 1.0) for i in range(3)]
            cpr["box_world_centre"] = rr(centre, 2)
            cpr["box_world_min"] = rr([centre[i] - half[i] for i in range(3)], 2)
            cpr["box_world_max"] = rr([centre[i] + half[i] for i in range(3)], 2)
        b = ed.bounds(r)
        cpr["actor_bounds_min"], cpr["actor_bounds_max"] = rr(b[0], 2), rr(b[1], 2)
    out["cp_approach"] = cpr
    # BP_LBCharacter CDO
    cdo = {}
    p = ed.props(CHAR_CDO + ":CollisionCylinder", ["capsuleRadius", "capsuleHalfHeight"])
    cdo["capsule_radius"], cdo["capsule_half_height"] = p["capsuleRadius"], p["capsuleHalfHeight"]
    cdo["BaseEyeHeight"] = ed.props(CHAR_CDO, ["BaseEyeHeight"])["BaseEyeHeight"]
    cam = CHAR_CDO + ":FirstPersonCamera"
    cp = ed.props(cam, ["relativeLocation", "relativeRotation", "bUsePawnControlRotation"])
    cdo["camera_component"] = "FirstPersonCamera"
    cdo["camera_rel_location"] = rr(v3(cp["relativeLocation"]), 3)
    cdo["camera_use_pawn_control_rotation"] = cp["bUsePawnControlRotation"]
    try:
        cdo["camera_attach_parent"] = R(ed.call(A, "get_parent_component", {"component": {"refPath": cam}}))
    except RuntimeError as e:
        cdo["camera_attach_parent"] = None
        cdo["camera_attach_parent_error"] = str(e)[:160]
    cdo["camera_attach_parent_source"] = ("C++ Source/LastBell/Character/LBCharacter.cpp line 51: FirstPersonCamera->SetupAttachment(GetCapsuleComponent()), "
                                         "SetRelativeLocation(0,0,64); LBCameraFeelComponent sets eye above feet = StandingHalfHeight + the camera's BaseRelativeLocation.Z "
                                         "(= capsule half height + 64 when standing) plus head bob / landing dip, converted to a capsule-relative Z")
    out["character_cdo"] = cdo
    # floor and eye
    ps0 = ps[0]
    x, y, z = ps0["location"][0], ps0["location"][1], ps0["location"][2]
    floor = tr.down(x, y, z + 50.0, 400.0)
    hh, bz, rz = cdo["capsule_half_height"], cdo["BaseEyeHeight"], cdo["camera_rel_location"][2]
    out["spawn"] = {"player_start_label": ps0["label"], "xy": [x, y], "player_start_z": z, "floor_z": None if floor is None else round(floor, 2),
                    "yaw": ps0["rotation"][1], "pitch": ps0["rotation"][0], "roll": ps0["rotation"][2],
                    "eye_z_camera_component": None if floor is None else round(floor + hh + rz, 2),
                    "eye_z_base_eye_height": None if floor is None else round(floor + hh + bz, 2),
                    "eye_z_plan_formula_floor_plus_BaseEyeHeight": None if floor is None else round(floor + bz, 2),
                    "pawn_capsule_centre_when_settled_z": None if floor is None else round(floor + hh, 2),
                    "pawn_capsule_centre_at_start_z": z,
                    "eye_z_unsettled_at_start": z + rz,
                    "camera_uses": "the FirstPersonCamera component (capsule centre + 64); BaseEyeHeight (64) is relative to the capsule centre too (APawn::GetPawnViewLocation, used by AI perception), so both give floor + half height + 64"}
    if cpr.get("box_world_min"):
        mn, mx = cpr["box_world_min"], cpr["box_world_max"]
        out["spawn"]["player_start_inside_cp_approach_box_xy"] = bool(mn[0] <= x <= mx[0] and mn[1] <= y <= mx[1])
        out["spawn"]["player_start_inside_cp_approach_box_xyz"] = bool(mn[0] <= x <= mx[0] and mn[1] <= y <= mx[1] and mn[2] <= z <= mx[2])
    return out


# ---------------------------------------------------------------------------------------------- item 3: gatehouse passage
def mesh_collision(ed, ref):
    """(mesh, collisionEnabled, profile) of the first mesh component with a body, or Nones."""
    for c in ed.comps(ref):
        k = ed.cls(c)
        if k in ("/Script/Engine.StaticMeshComponent", "/Script/Engine.InstancedStaticMeshComponent", "/Script/Engine.SkeletalMeshComponent"):
            p = ed.props_safe(c, ["staticMesh", "bodyInstance", "bVisible"])
            bi = p.get("bodyInstance") if isinstance(p.get("bodyInstance"), dict) else {}
            sm = p.get("staticMesh")
            return {"component": objname(c), "mesh": short(R(sm)) if isinstance(sm, dict) else None, "collision_enabled": bi.get("collisionEnabled"),
                    "profile": bi.get("collisionProfileName"), "visible": p.get("bVisible")}
    for c in ed.comps(ref):
        if ed.cls(c) == "/Script/Engine.BoxComponent":
            p = ed.props_safe(c, ["bodyInstance"])
            bi = p.get("bodyInstance") if isinstance(p.get("bodyInstance"), dict) else {}
            return {"component": objname(c), "mesh": None, "collision_enabled": bi.get("collisionEnabled"), "profile": bi.get("collisionProfileName"), "visible": None,
                    "note": "box component (no mesh)"}
    return None


def stage_gate(ed, tr):
    out = {}
    refs = ed.find_box((-600, -500, -5000), (600, 500, 5000))
    rows = []
    for r in refs:
        b = ed.bounds(r)
        lo, hi = rr(b[0], 1), rr(b[1], 1)
        cls = short(ed.cls(r))
        rec = {"label": ed.label(r), "object": objname(r), "class": cls, "bounds_min": lo, "bounds_max": hi}
        rec["no_spatial_bounds"] = max(hi[i] - lo[i] for i in range(3)) < 0.5
        if cls in ("StaticMeshActor",) or cls.endswith("_C"):
            mc = mesh_collision(ed, r)
            if mc:
                rec["collision"] = mc
        rows.append(rec)
    out["actors"] = rows
    say("  %d actors in the gatehouse box (%d with real bounds)" % (len(rows), sum(1 for r in rows if not r["no_spatial_bounds"])))
    # floor
    out["floor_traces"] = []
    for x in (-400, -200, 0, 200, 400):
        z = tr.down(x, 0, 400.0, 800.0)
        out["floor_traces"].append({"x": x, "y": 0, "floor_z": None if z is None else round(z, 2)})
    # centreline: free span between the passage's side walls at several X (horizontal traces at z 110 from y 0)
    spans = []
    for x in (50, 150, 250):
        left = tr.trace((x, 0, 110), (x, -900, 110))
        right = tr.trace((x, 0, 110), (x, 900, 110))
        jy = Tracer.JITTER[1]           # the traces start at y = 0 + jitter, so the wall faces are at jy -/+ the hit distance
        spans.append({"x": x, "hit_minus_y": None if left is None else round(left, 1), "hit_plus_y": None if right is None else round(right, 1),
                      "free_y_min": None if left is None else round(jy - left, 1), "free_y_max": None if right is None else round(jy + right, 1)})
    out["spans"] = spans
    ys = [(s["free_y_min"] + s["free_y_max"]) / 2 for s in spans if s["free_y_min"] is not None and s["free_y_max"] is not None]
    out["centreline_y"] = round(round((sum(ys) / len(ys)) * 2.0) / 2.0, 1) if ys else 0.0       # to the nearest 0.5 cm
    # roof: upward traces from z 110, three Y lanes, X -100..400 in 20 cm steps then 5 cm refinement of the two ends
    fz = out["floor_traces"][2]["floor_z"] or 0.0
    z0 = fz + 110.0

    def roof_at(x):
        hs = []
        for y in (-100.0, 0.0, 100.0):
            h = tr.up(x, y, z0, 1500.0)
            hs.append(None if h is None else round(h, 1))
        return hs

    cols = OrderedDict()
    for x in range(-100, 401, 20):
        cols[x] = roof_at(float(x))
    covered = [x for x, hs in cols.items() if all(h is not None for h in hs)]
    out["roof_scan"] = [{"x": x, "hit_z_at_y_minus100_0_plus100": hs} for x, hs in cols.items()]
    if covered:
        lo_x, hi_x = min(covered), max(covered)
        # refine the outer end (lowest X): look between the last uncovered X below and lo_x
        def refine(x_unc, x_cov):
            for _ in range(7):
                mid = (x_unc + x_cov) / 2.0
                if all(h is not None for h in roof_at(mid)):
                    x_cov = mid
                else:
                    x_unc = mid
            return x_cov
        below = [x for x in cols if x < lo_x]
        above = [x for x in cols if x > hi_x]
        # the rays run at x + jitter, so the true edge is the converged x plus the jitter; rounded to the nearest 0.5 cm
        jx = Tracer.JITTER[0]
        lo_ref = round((refine(max(below), lo_x) if below else lo_x) + jx, 0)
        hi_ref = round((refine(min(above), hi_x) if above else hi_x) + jx, 0)
        out["roof"] = {"found": True, "x_min": lo_ref, "x_max": hi_ref, "method": "upward traces from floor+110 at Y -100/0/+100 (20 cm steps, 7 bisections at each end); "
                       "only greybox/collision geometry and blocking helper volumes (stepped through) can be seen",
                       "hit_z_centre_lane": [cols[x][1] for x in covered][:1] + [min(cols[x][1] for x in covered), max(cols[x][1] for x in covered)]}
    else:
        out["roof"] = {"found": False}
    # art actors overhead: bounds that cover Y -100..100 and sit above z0
    over = []
    for r in rows:
        if r["no_spatial_bounds"]:
            continue
        lo, hi = r["bounds_min"], r["bounds_max"]
        if lo[1] <= -100 and hi[1] >= 100 and hi[2] > z0 + 100 and lo[0] < 450 and hi[0] > -100 and max(hi[i] - lo[i] for i in range(3)) < 100000:
            if r["object"].startswith(NOT_SOLID_PREFIXES):
                continue
            over.append({"label": r["label"], "x": [lo[0], hi[0]], "z": [lo[2], hi[2]]})
    out["overhead_art_by_bounds"] = over
    # lantern points
    if out["roof"]["found"]:
        rx0, rx1 = out["roof"]["x_min"], out["roof"]["x_max"]
        src = "roofed passage (upward traces)"
    else:
        arch = next((r for r in rows if r["label"] == "KG_GateArch"), None)
        rx0, rx1 = (arch["bounds_min"][0], arch["bounds_max"][0]) if arch else (0.0, 300.0)
        src = "gate arch bounds (no roof found)"
    cy = out["centreline_y"]
    pts = {}
    for name, x in (("start", rx0 + 50.0), ("stop", rx1 - 50.0)):
        z = tr.down(x, cy, z0 + 100.0, 600.0)
        pts[name] = {"x": round(x, 1), "y": cy, "floor_z": None if z is None else round(z, 2), "z": None if z is None else round(z + 110.0, 2)}
    out["lantern"] = {"source": src, "x_outer_end": rx0, "x_courtyard_end": rx1, "start": pts["start"], "stop": pts["stop"],
                      "mid_x": round((rx0 + rx1) / 2, 1), "floor_z": fz}
    say("  centreline y %s; roof %s; lantern %s -> %s" % (cy, out["roof"].get("x_min"), pts["start"], pts["stop"]))
    return out


# ---------------------------------------------------------------------------------------------- item 4a: wall top, strikes, ending trigger
MOUTH_Y = (-100.0, 0.0, 100.0)
MOUTH_DZ = (50.0, 150.0, 250.0)


def stage_wall(ed, tr, gate):
    out = {}
    app = ed.find("Apparition_Courtyard")
    st = {}
    if app:
        r = app[0]
        p = ed.props(r, ["Stations", "TriggerTag"])
        stations = []
        for s in p.get("Stations") or []:
            stations.append({"location": rr(v3(s["location"]), 1), "walk_path_points": len(s.get("walkPath") or []), "hold_seconds": s.get("holdSeconds"),
                             "walk_speed": s.get("walkSpeed")})
        st = {"label": "Apparition_Courtyard", "object": objname(r), "class": short(ed.cls(r))}
        st.update(ed.xf_full(r))
        st["stations"] = stations
    out["apparition"] = st
    sx, sy = (st["stations"][0]["location"][0], st["stations"][0]["location"][1]) if st.get("stations") else (6020.0, 1300.0)
    top = tr.down(sx, sy, 1500.0, 2500.0)
    out["wall_top"] = {"xy": [sx, sy], "trace_from_z": 1500.0, "top_z": None if top is None else round(top, 2)}
    art = []
    for r in ed.find_box((sx - 5, sy - 5, -200), (sx + 5, sy + 5, 1500)):
        if objname(r).startswith(NOT_SOLID_PREFIXES):
            continue
        b = ed.bounds(r)
        lo, hi = rr(b[0], 1), rr(b[1], 1)
        if max(hi[i] - lo[i] for i in range(3)) > 100000:
            continue
        rec = {"label": ed.label(r), "class": short(ed.cls(r)), "bounds_min": lo, "bounds_max": hi}
        mc = mesh_collision(ed, r)
        if mc:
            rec["collision"] = mc
        art.append(rec)
    out["art_at_xy"] = art
    eye = [sx, sy, (top or 0.0) + 232.0]
    out["wall_top_eye"] = rr(eye, 2)
    # mouth rays
    lan = gate["lantern"]
    mx = lan["stop"]["x"] + 50.0
    cy = gate["centreline_y"]
    fz = lan["floor_z"]
    rays = []
    for dy in MOUTH_Y:
        for dz in MOUTH_DZ:
            tgt = [mx, cy + dy, fz + dz]
            d = tr.trace(eye, tgt)
            ln = dist3(eye, tgt)
            rays.append({"target": rr(tgt, 1), "length": round(ln, 1), "hit_distance": None if d is None else round(d, 1),
                         "visible": bool(d is None or d >= ln - 5.0)})
    out["mouth_rays"] = rays
    out["mouth_visible"] = sum(1 for r in rays if r["visible"])
    mid_x = gate["lantern"]["mid_x"]
    aim = [mid_x, cy, 200.0]
    yw, pt = yaw_pitch(eye, aim)
    out["aim"] = {"target": rr(aim, 1), "yaw_deg": round(yw, 2), "pitch_deg": round(pt, 2), "distance": round(dist3(eye, aim), 1)}
    out["mouth_x"] = mx
    # strike targets
    da = "/Game/LastBell/Data/DA_StormSettings.DA_StormSettings"
    ss = ed.props(da, ["scriptedStrikes"]).get("scriptedStrikes") or []
    strikes = []
    tags = []
    for s in ss:
        tg = s.get("strikeTargetTag")
        tg = tg if tg and tg != "None" else None
        strikes.append({"trigger_tag": (s.get("triggerTag") or {}).get("tagName"), "delay": s.get("delay"), "count": s.get("count"), "spacing": s.get("spacing"),
                        "profile": s.get("profile"), "look_gate": s.get("bLookGate"), "strike_target_tag": tg})
        if tg and tg not in tags:
            tags.append(tg)
    out["scripted_strikes"] = strikes
    out["strike_tags"] = tags
    out["strike_targets"] = {}
    for tg in tags:
        lst = []
        for r in ed.find_tag(tg):
            lst.append({"label": ed.label(r), "object": objname(r), "class": short(ed.cls(r)), "location": ed.xf_full(r)["location"]})
        out["strike_targets"][tg] = lst
    out["strike_target_tower_count"] = len(out["strike_targets"].get("LB_StrikeTarget_Tower", []))
    # extra: any other labelled StrikeTarget actors and their tags (get_tags is slow, so only for labels that mention it)
    extra = []
    for r in ed.find_name("StrikeTarget"):
        extra.append({"label": ed.label(r), "tags": ed.call(A, "get_tags", {"actor": {"refPath": r}})})
    out["labelled_strike_target_actors"] = extra
    # ending trigger
    et = ed.find("EndingTrigger")
    ent = {}
    if et:
        r = et[0]
        ent = {"label": "EndingTrigger", "object": objname(r), "class": short(ed.cls(r)), "class_path": ed.cls(r)}
        ent.update(ed.xf_full(r))
        ent["EndingSeconds"] = ed.props(r, ["endingSeconds"]).get("endingSeconds")
        b = ed.bounds(r)
        ent["bounds_min"], ent["bounds_max"] = rr(b[0], 1), rr(b[1], 1)
        ent["tags"] = ed.call(A, "get_tags", {"actor": {"refPath": r}})
    out["ending_trigger"] = ent
    return out


# ---------------------------------------------------------------------------------------------- item 4b: bell
def rot_mat(pitch, yaw, roll):
    """UE FRotator (degrees) as a 3x3 matrix whose columns are the rotated X, Y, Z axes."""
    p, y, r = math.radians(pitch), math.radians(yaw), math.radians(roll)
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
    x_axis = [cp * cy, cp * sy, sp]
    y_axis = [sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp]
    z_axis = [-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp]
    return x_axis, y_axis, z_axis


def stage_bell(ed):
    out = {}
    b = ed.find("Bell")
    rec = {}
    if b:
        r = b[0]
        rec = {"label": "Bell", "object": objname(r), "class": short(ed.cls(r)), "class_path": ed.cls(r)}
        rec.update(ed.xf_full(r))
        bb = ed.bounds(r)
        rec["bounds_min"], rec["bounds_max"] = rr(bb[0], 1), rr(bb[1], 1)
        rec["tags"] = ed.call(A, "get_tags", {"actor": {"refPath": r}})
        rec["use_state_tag"] = ed.props(r, ["useStateTag"]).get("useStateTag")
        rec["root_component"] = R(ed.call(A, "get_root_component", {"actor": {"refPath": r}}))
        comps = []
        for c in ed.comps(r):
            k = ed.cls(c)
            crec = {"name": objname(c), "class": short(k)}
            if k in ("/Script/Engine.StaticMeshComponent",):
                p = ed.props(c, ["mobility", "relativeLocation", "relativeRotation", "relativeScale3D", "staticMesh", "bodyInstance", "bVisible"])
                crec["mobility"] = p["mobility"]
                crec["relative_location"] = rr(v3(p["relativeLocation"]), 2)
                crec["relative_rotation"] = rr([p["relativeRotation"][k2] for k2 in ("pitch", "yaw", "roll")], 3)
                crec["relative_scale"] = rr(v3(p["relativeScale3D"]), 3)
                crec["mesh"] = R(p["staticMesh"])
                bi = p.get("bodyInstance") or {}
                crec["collision_enabled"], crec["collision_profile"] = bi.get("collisionEnabled"), bi.get("collisionProfileName")
                crec["visible"] = p.get("bVisible")
                try:
                    par = ed.call(A, "get_parent_component", {"component": {"refPath": c}})
                    crec["attach_parent"] = R(par)
                except RuntimeError as e:
                    crec["attach_parent"] = None
                    crec["attach_parent_error"] = str(e)[:100]
                crec["is_root"] = (R(c) == rec["root_component"])
                # for the root component the relative transform already is the world transform (MCP_NOTES P10 item 6)
                crec["world_location"] = crec["relative_location"] if crec["is_root"] else None
            comps.append(crec)
        rec["components"] = comps
    out["bell_actor"] = rec
    parts = []
    for q in ("Headstock", "BellFrame", "BellWheel", "Bell_Beam", "TWA_Bell", "Bell_Chain"):
        for r in ed.find_name(q):
            lab = ed.label(r)
            if any(p["label"] == lab for p in parts):
                continue
            bb = ed.bounds(r)
            row = {"label": lab, "object": objname(r), "class": short(ed.cls(r))}
            row.update(ed.xf_full(r))
            row["bounds_min"], row["bounds_max"] = rr(bb[0], 1), rr(bb[1], 1)
            row["size"] = rr([bb[1][i] - bb[0][i] for i in range(3)], 1)
            mc = mesh_collision(ed, r)
            if mc:
                row["mesh_and_collision"] = mc
            parts.append(row)
    out["bell_parts"] = parts
    # the axle
    head = next((p for p in parts if p["label"] == "TWA_Headstock"), None)
    rope = next((p for p in parts if p["label"] == "TWA_BellRope"), None)
    ax = {}
    if head and rec:
        pitch, yaw, roll = head["rotation"]
        xa, ya, za = rot_mat(pitch, yaw, roll)
        sx, sy, _ = head["size"]
        # the headstock is the long beam carrying the wheel: its long horizontal bounds axis is the axle. With rotation 0 the bounds are in world axes.
        long_world = "Y" if sy >= sx else "X"
        axle_world = [0.0, 1.0, 0.0] if long_world == "Y" else [1.0, 0.0, 0.0]
        comp = next((c for c in rec["components"] if c.get("mobility")), None)
        crot = comp["relative_rotation"] if comp else [0, 0, 0]
        cx, cy_, cz = rot_mat(*crot)           # component local axes in world space (the component is the root: relative = world)
        local = [sum(axle_world[i] * a[i] for i in range(3)) for a in (cx, cy_, cz)]    # axle expressed in the component's local axes (rotation matrix is orthonormal)
        along = ["X", "Y", "Z"][max(range(3), key=lambda i: abs(local[i]))]
        ax = {"headstock_rotation": head["rotation"], "headstock_size_xyz": head["size"], "long_horizontal_axis_world": long_world,
              "wheel_hint": ("TWA_BellRope bounds centre x %.0f, y %.0f: the rope hangs from the wheel rim at the east end (headstock bounds x max %.0f)" % (
                  (rope["bounds_min"][0] + rope["bounds_max"][0]) / 2, (rope["bounds_min"][1] + rope["bounds_max"][1]) / 2, head["bounds_max"][0])) if rope else None,
              "bell_component_rotation": crot, "axle_in_component_local_axes": [round(x, 3) for x in local], "axle_local_axis": along,
              "swing_axis": "Pitch" if along == "Y" else ("Roll" if along == "X" else "Yaw (unexpected)"),
              "wheel_disc_evidence": "headstock extents X %.1f, Z %.1f (equal: the wheel disc lies in the XZ plane, diameter about %.0f) and Y %.1f (the beam through it)" % (
                  head["size"][0], head["size"][2], head["size"][0], head["size"][1]),
              "headstock_centre": rr([(head["bounds_min"][i] + head["bounds_max"][i]) / 2 for i in range(3)], 1),
              "reasoning": ("The headstock (rotation %s) is %.0f (X) by %.0f (Y) by %.0f (Z): the X and Z extents match (the wheel disc, in the XZ plane) and the beam through it is the "
                            "long horizontal axis, world %s, so the axle runs along %s; the rope hangs from the wheel rim at the end of that beam. The bell component's rotation is %s, "
                            "so its local %s axis is the axle. Rotation about local Y is Pitch (about X it would be Roll), hence the bell swings in %s." % (
                                head["rotation"], head["size"][0], head["size"][1], head["size"][2], long_world, long_world, crot, along,
                                "Pitch" if along == "Y" else ("Roll" if along == "X" else "?")))}
    out["axle"] = ax
    return out


# ---------------------------------------------------------------------------------------------- item 4c: tower top
TOWER_NAMES = ["Top_Slab_W", "Top_Slab_N", "Top_Rail_E", "Top_Rail_S", "Trig_TowerTop", "CP_TowerTop", "Tw_Core", "Tw_Landing_06", "Tw_Landing_07",
               "Tw_Landing_08", "Tw_Landing_09", "Tw_Landing_10"]


def actor_rec(ed, r, with_class=True):
    b = ed.bounds(r)
    rec = {"label": ed.label(r), "object": objname(r), "bounds_min": rr(b[0], 2), "bounds_max": rr(b[1], 2)}
    if with_class:
        rec["class"] = short(ed.cls(r))
    rec["top_z"] = rec["bounds_max"][2]
    rec["centre"] = rr([(b[0][i] + b[1][i]) / 2 for i in range(3)], 2)
    return rec


def stage_tower(ed, tr):
    out = {"named": [], "steps": {}, "waypoints": [], "wspawn_tower": None}
    for n in TOWER_NAMES:
        hits = ed.find(n)
        if not hits:
            out["named"].append({"label": n, "missing": True})
        for r in hits:
            rec = actor_rec(ed, r)
            if n in ("Top_Slab_W", "Top_Slab_N", "Top_Rail_E", "Top_Rail_S", "Tw_Core") or n.startswith("Tw_Landing"):
                mc = mesh_collision(ed, r)
                if mc:
                    rec["collision"] = mc
            out["named"].append(rec)
    for fl in ("F09", "F10", "F11"):
        prefix = "Stair_%s_" % fl
        lst = []
        for r in ed.find_name(prefix):
            lab = ed.label(r)
            if lab.startswith(prefix):
                lst.append(actor_rec(ed, r, with_class=False))
        lst.sort(key=lambda s: s["label"])
        out["steps"][fl] = lst
        say("  %s: %d steps" % (fl, len(lst)))
    for i in range(25):
        lab = "WP_TowerStairs_%02d" % i
        hits = ed.find(lab)
        if not hits:
            out["waypoints"].append({"label": lab, "missing": True})
            continue
        r = hits[0]
        loc = ed.xf_full(r)["location"]
        z = tr.down(loc[0], loc[1], loc[2] + 100.0, 400.0)
        out["waypoints"].append({"label": lab, "class": short(ed.cls(r)), "location": loc, "floor_z_under": None if z is None else round(z, 2)})
    ws = ed.find("WSpawn_Tower")
    if ws:
        out["wspawn_tower"] = {"label": "WSpawn_Tower", "class": short(ed.cls(ws[0])), **ed.xf_full(ws[0])}
    return out


# ---------------------------------------------------------------------------------------------- item 5: sight lines
MARKS = [("M1", 12165.0, 2300.0), ("M2", 12165.0, 2380.0), ("M3", 12230.0, 2300.0)]
CLEAR_HEIGHTS = (20.0, 90.0, 170.0)
CLEAR_DIRS = 16
CLEAR_LEN = 300.0
CLEAR_PASS = 102.0
RAY_DZ = (200.0, 245.0, 290.0)
RAY_LAT = (-30.0, 0.0, 30.0)
SAMPLE_STEP = 50.0


def ident(ed, p, cache):
    """The actors whose bounds contain the hit point (a tiny find_actors box), smallest first: the likely hit actor first. Read only."""
    refs = ed.find_box((p[0] - 1.0, p[1] - 1.0, p[2] - 1.0), (p[0] + 1.0, p[1] + 1.0, p[2] + 1.0))
    c = []
    for r in refs:
        on = objname(r)
        if on.startswith(NOT_SOLID_PREFIXES):
            continue
        if r not in cache:
            b = ed.bounds(r)
            cache[r] = {"label": ed.label(r), "lo": rr(b[0], 2), "hi": rr(b[1], 2)}
        a = cache[r]
        size = [a["hi"][i] - a["lo"][i] for i in range(3)]
        if max(size) > 100000:
            continue
        if all(a["lo"][i] - 1.5 <= p[i] <= a["hi"][i] + 1.5 for i in range(3)):
            c.append((size[0] * size[1] * size[2], a["label"]))
    c.sort()
    return [x[1] for x in c[:3]]


def build_samples(tower, tr):
    wp = {w["label"]: w for w in tower["waypoints"]}
    pts = []
    for i in range(14, 25):
        w = wp["WP_TowerStairs_%02d" % i]
        pts.append((w["label"], w["location"]))
    samples = []
    acc = 0.0
    for k in range(len(pts) - 1):
        (la, a), (lb, b) = pts[k], pts[k + 1]
        seg = dist2(a, b)
        n = max(1, int(math.floor(seg / SAMPLE_STEP + 1e-6)))
        for j in range(n):
            t = (j * SAMPLE_STEP) / seg if seg > 0 else 0.0
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            zi = a[2] + (b[2] - a[2]) * t
            samples.append({"id": "%s+%03d" % (la.replace("WP_TowerStairs_", "WP"), round(j * SAMPLE_STEP)), "kind": "path", "segment": "%s->%s" % (la, lb),
                            "xy": [round(x, 1), round(y, 1)], "z_interp": round(zi, 1), "path_s": round(acc + j * SAMPLE_STEP, 1)})
        acc += seg
    last = pts[-1]
    samples.append({"id": last[0].replace("WP_TowerStairs_", "WP") + "+end", "kind": "path", "segment": "end", "xy": [round(last[1][0], 1), round(last[1][1], 1)],
                    "z_interp": round(last[1][2], 1), "path_s": round(acc, 1)})
    for r in tower["named"]:
        if r.get("label", "").startswith("Tw_Landing_") and not r.get("missing"):
            c = r["centre"]
            samples.append({"id": r["label"].replace("Tw_Landing_", "Land"), "kind": "landing", "segment": r["label"], "xy": [c[0], c[1]], "z_interp": r["top_z"], "top_z_bounds": r["top_z"]})
    for s in samples:
        z0 = s["z_interp"]
        if s["kind"] == "landing":
            s["z"] = s["z_interp"]          # centre of bounds XY, top Z of the bounds (task spec)
            s["z_source"] = "bounds top"
        else:
            z = tr.down(s["xy"][0], s["xy"][1], z0 + 120.0, 400.0)
            s["z"] = None if z is None else round(z, 2)
            s["z_source"] = "down trace from interpolated z + 120"
    return samples


def stage_sight(ed, tr, tower, cache_obj):
    out = {"marks": {}, "samples": [], "rays": {}}
    cdo = ed.props(CHAR_CDO + ":CollisionCylinder", ["capsuleRadius", "capsuleHalfHeight"])
    hh = float(cdo["capsuleHalfHeight"])
    rz = v3(ed.props(CHAR_CDO + ":FirstPersonCamera", ["relativeLocation"])["relativeLocation"])[2]
    eye_off = hh + rz
    out["eye_offset_above_floor"] = eye_off
    out["capsule_radius"] = float(cdo["capsuleRadius"])
    samples = build_samples(tower, tr)
    out["samples"] = samples
    say("  %d samples (%d on the path, %d landings)" % (len(samples), sum(1 for s in samples if s["kind"] == "path"), sum(1 for s in samples if s["kind"] == "landing")))
    ident_cache = {}
    bell_centre = [12420.0, 2000.0, 2750.0]
    for name, mx, my in MARKS:
        fl = tr.down(mx, my, 2560.0, 300.0)
        rec = {"x": mx, "y": my, "floor_z": None if fl is None else round(fl, 2)}
        fz = fl if fl is not None else 2500.0
        eye = [mx, my, fz + eye_off]
        rec["eye"] = rr(eye, 2)
        # clearance
        hits = []
        for hgt in CLEAR_HEIGHTS:
            for k in range(CLEAR_DIRS):
                ang = math.radians(360.0 / CLEAR_DIRS * k)
                end = [mx + math.cos(ang) * CLEAR_LEN, my + math.sin(ang) * CLEAR_LEN, fz + hgt]
                d = tr.trace([mx, my, fz + hgt], end)
                hits.append({"height": hgt, "angle_deg": round(math.degrees(ang), 1), "distance": None if d is None else round(d, 1)})
        valid = [h for h in hits if h["distance"] is not None]
        rec["clearance_hits"] = hits
        if valid:
            m = min(valid, key=lambda h: h["distance"])
            rec["clearance_min"] = m["distance"]
            rec["clearance_min_at"] = {"height": m["height"], "angle_deg": m["angle_deg"]}
            ang = math.radians(m["angle_deg"])
            pt = [mx + math.cos(ang) * m["distance"], my + math.sin(ang) * m["distance"], fz + m["height"]]
            rec["clearance_min_hit_point"] = rr(pt, 1)
            rec["clearance_min_hit_actors"] = ident(ed, pt, ident_cache)
            per_h = {}
            for hgt in CLEAR_HEIGHTS:
                hv = [h for h in valid if h["height"] == hgt]
                if hv:
                    mh = min(hv, key=lambda h: h["distance"])
                    a2 = math.radians(mh["angle_deg"])
                    pt2 = [mx + math.cos(a2) * mh["distance"], my + math.sin(a2) * mh["distance"], fz + hgt]
                    per_h[str(int(hgt))] = {"min": mh["distance"], "angle_deg": mh["angle_deg"], "hit_actors": ident(ed, pt2, ident_cache)}
            rec["clearance_per_height"] = per_h
        else:
            rec["clearance_min"] = None
        rec["clearance_pass_102"] = bool(rec["clearance_min"] is None or rec["clearance_min"] >= CLEAR_PASS)
        rec["clearance_pass_94_capsule34"] = bool(rec["clearance_min"] is None or rec["clearance_min"] >= 34.0 + 60.0)
        # can the traces hit the bell? a ray from the mark side toward the bell centre at z 2750 and one along +Y into the bell from outside its frame
        bd = tr.trace([mx, my, 2750.0], bell_centre)
        rec["to_bell_centre"] = {"expected_distance_to_centre": round(dist3([mx, my, 2750.0], bell_centre), 1), "first_hit_distance": None if bd is None else round(bd, 1)}
        if bd is not None:
            u = sub(bell_centre, [mx, my, 2750.0])
            n = norm(u)
            pt = [mx + u[0] / n * bd, my + u[1] / n * bd, 2750.0 + u[2] / n * bd]
            rec["to_bell_centre"]["hit_point"] = rr(pt, 1)
            rec["to_bell_centre"]["hit_actors"] = ident(ed, pt, ident_cache)
        out["marks"][name] = rec
        say("  %s: floor %s eye z %.1f clearance min %s (%s)" % (name, rec["floor_z"], eye[2], rec["clearance_min"], rec.get("clearance_min_hit_actors")))
    # bell hull check from outside the frame: along +Y at x 12420, z 2760, from y 1700 (frame bounds y 1850..2150, bell 1895..2105)
    bh = tr.trace([12420.0, 1700.0, 2760.0], [12420.0, 2000.0, 2760.0])
    bh_rec = {"ray": "from (12420, 1700, 2760) toward the bell centre (12420, 2000, 2760)", "first_hit_distance": None if bh is None else round(bh, 1)}
    if bh is not None:
        pt = [12420.0, 1700.0 + bh, 2760.0]
        bh_rec["hit_point"] = rr(pt, 1)
        bh_rec["hit_actors"] = ident(ed, pt, ident_cache)
    out["bell_hull_probe"] = bh_rec
    # visibility
    partial_path = os.path.join(SCRATCH, "sight_partial.json")
    done = json.load(open(partial_path, encoding="utf-8")) if os.path.exists(partial_path) and not cache_obj.refresh else {}
    for name, mx, my in MARKS:
        eye = out["marks"][name]["eye"]
        rows = done.setdefault(name, {})
        for si, s in enumerate(samples):
            if s["id"] in rows:
                continue
            if s["z"] is None:
                rows[s["id"]] = {"skipped": "no floor"}
                continue
            sx, sy, sz = s["xy"][0], s["xy"][1], s["z"]
            dx, dy = sx - eye[0], sy - eye[1]
            hd = math.hypot(dx, dy)
            if hd < 1e-6:
                px, py = 0.0, 1.0
            else:
                px, py = -dy / hd, dx / hd
            bits = ""
            tgts = []
            for dz in RAY_DZ:
                for lat in RAY_LAT:
                    tgt = [sx + px * lat, sy + py * lat, sz + dz]
                    d = tr.trace(eye, tgt)
                    ln = dist3(eye, tgt)
                    vis = d is None or d >= ln - 5.0
                    bits += "1" if vis else "0"
                    tgts.append(vis)
            rows[s["id"]] = {"visible_rays": sum(tgts), "fraction": round(sum(tgts) / 9.0, 3), "bits": bits, "horizontal_distance": round(hd, 1),
                             "drop": round(eye[2] - (sz + 245.0), 1), "sample_z": sz}
            if si % 5 == 4:
                json.dump(done, open(partial_path, "w", encoding="utf-8"), indent=1)
                say("   %s sample %d/%d (%s) fraction %.2f  [raw traces so far %d, volume skips %d]" % (name, si + 1, len(samples), s["id"], rows[s["id"]]["fraction"], tr.n_raw, tr.n_skip))
        json.dump(done, open(partial_path, "w", encoding="utf-8"), indent=1)
    out["rays"] = done
    out["trace_counts"] = {"raw": tr.n_raw, "volume_skips": tr.n_skip}
    return out


# ---------------------------------------------------------------------------------------------- proposals
def analyse_sight(sight, tower):
    res = {"marks": {}, "rule": {}}
    for name, mx, my in MARKS:
        rows = sight["rays"][name]
        vis = [(sid, r) for sid, r in rows.items() if r.get("fraction") is not None and r["fraction"] >= 0.6]
        tot = sum(r.get("fraction", 0.0) for r in rows.values())
        res["marks"][name] = {"visible_count": len(vis), "total_fraction": round(tot, 3), "sample_count": len(rows)}
    ordered = sorted(res["marks"].items(), key=lambda kv: (-kv[1]["visible_count"], -kv[1]["total_fraction"]))
    chosen = ordered[0][0]
    res["rule"]["chosen_mark"] = chosen
    res["rule"]["ranking"] = [(k, v["visible_count"], v["total_fraction"]) for k, v in ordered]
    res["rule"]["chosen_clearance_pass_102"] = sight["marks"][chosen]["clearance_pass_102"]
    ok = [(k, v) for k, v in ordered if sight["marks"][k]["clearance_pass_102"]]
    res["rule"]["best_mark_among_clearance_pass"] = ok[0][0] if ok else None

    def pick(mark, lo_cm, hi_cm, nominal_cm):
        rows = sight["rays"][mark]
        sm = {s["id"]: s for s in sight["samples"]}
        cands = []
        for sid, r in rows.items():
            if r.get("fraction") is None or r["fraction"] < 0.6:
                continue
            if lo_cm <= r["drop"] <= hi_cm:
                cands.append((-r["fraction"], abs(r["drop"] - nominal_cm), sid))
        cands.sort()
        if not cands:
            return None
        sid = cands[0][2]
        r, s = rows[sid], sm[sid]
        return {"sample": sid, "xy": s["xy"], "sample_z": s["z"], "drop_cm": r["drop"], "horizontal_distance_cm": r["horizontal_distance"], "fraction": r["fraction"],
                "n_candidates": len(cands), "candidates": [{"sample": c[2], "fraction": -c[0], "drop": rows[c[2]]["drop"]} for c in cands[:6]]}

    def both(mark):
        return {"G1": pick(mark, 600.0, 1500.0, 1000.0), "G2": pick(mark, 300.0, 600.0, 450.0)}

    res["rule"]["glimpses_chosen_mark"] = both(chosen)
    res["rule"]["glimpses_by_mark"] = {k: both(k) for k in res["marks"]}
    return res


def walk_path(tower, stop, top_xy_choices, tr):
    steps = [s for s in tower["steps"]["F11"]]
    pts = [(s["label"], [s["centre"][0], s["centre"][1], s["top_z"]]) for s in steps]
    out = {}
    for key, top in top_xy_choices.items():
        segs = []
        poly = list(pts)
        poly.append(("CINE_StairTop (%s)" % key, [top[0], top[1], 2500.0]))
        poly.append(("stop point", [stop[0], stop[1], stop[2]]))
        total3 = total2 = 0.0
        for i in range(len(poly) - 1):
            a, b = poly[i], poly[i + 1]
            d3, d2 = dist3(a[1], b[1]), dist2(a[1], b[1])
            total3 += d3
            total2 += d2
            segs.append({"from": a[0], "to": b[0], "length_3d": round(d3, 1), "length_xy": round(d2, 1)})
        out[key] = {"segments": segs, "length_3d": round(total3, 1), "length_xy": round(total2, 1), "first_step": poly[0][0], "start_z": round(poly[0][1][2], 1)}
    return out


def lane_check(ed, tr, a, b, fz):
    """9 traces along the XY segment a->b: the centreline and +-42 cm sideways at floor + 20 / 110 / 200. Hits are identified by bounds."""
    ux, uy = (b[0] - a[0]), (b[1] - a[1])
    ln = math.hypot(ux, uy)
    ux, uy = ux / ln, uy / ln
    px, py = -uy, ux
    lane = []
    for side in (0.0, 42.0, -42.0):
        for h in (20.0, 110.0, 200.0):
            s_pt = [a[0] + px * side, a[1] + py * side, fz + h]
            e_pt = [b[0] + px * side, b[1] + py * side, fz + h]
            d = tr.trace(s_pt, e_pt)
            L0 = dist3(s_pt, e_pt)
            lane.append({"side_cm": side, "height_above_floor": h, "length": round(L0, 1), "hit_distance": None if d is None else round(d, 1), "clear": bool(d is None or d >= L0 - 0.5)})
    ident_cache = {}
    for l in lane:
        if not l["clear"]:
            s_pt = [a[0] + px * l["side_cm"], a[1] + py * l["side_cm"], fz + l["height_above_floor"]]
            pt3 = [s_pt[0] + ux * l["hit_distance"], s_pt[1] + uy * l["hit_distance"], s_pt[2]]
            l["hit_point"] = rr(pt3, 1)
            l["hit_actors"] = ident(ed, pt3, ident_cache)
    return lane


def stage_proposals(ed, tr, tower, sight):
    an = analyse_sight(sight, tower)
    ch = an["rule"]["chosen_mark"]
    mk = sight["marks"][ch]
    eye = mk["eye"]
    fz = mk["floor_z"] if mk["floor_z"] is not None else 2500.0
    wp = {w["label"]: w for w in tower["waypoints"]}
    named = {n["label"]: n for n in tower["named"] if not n.get("missing")}
    s13 = next((s for s in tower["steps"]["F11"] if s["label"] == "Stair_F11_13"), None)
    cand = OrderedDict()
    if s13:
        cand["A_top_step_Stair_F11_13_centre"] = [s13["centre"][0], s13["centre"][1]]
    w23 = wp.get("WP_TowerStairs_23")
    if w23 and not w23.get("missing"):
        cand["B_slab_arrival_WP_TowerStairs_23"] = [w23["location"][0], w23["location"][1]]
    out = {"analysis": an, "chosen_mark": ch, "mark_eye": eye, "stair_top_candidates": {}}
    sm = {x["id"]: x for x in sight["samples"]}
    rows_ch = sight["rays"][ch]
    out["visible_samples_chosen_mark"] = [{"sample": sid, "xy": sm[sid]["xy"], "sample_z": sm[sid]["z"], "fraction": r["fraction"], "drop_cm": r["drop"], "horizontal_cm": r["horizontal_distance"]}
                                          for sid, r in rows_ch.items() if r.get("fraction") is not None and r["fraction"] >= 0.6]
    best = {}
    for mark in sight["rays"]:
        for gname, lo_cm, hi_cm in (("G1", 600.0, 1500.0), ("G2", 300.0, 600.0)):
            c = [(r["fraction"], sid, r["drop"]) for sid, r in sight["rays"][mark].items() if r.get("fraction") is not None and lo_cm <= r["drop"] <= hi_cm]
            c.sort(reverse=True)
            best.setdefault(mark, {})[gname] = {"samples_in_drop_range": len(c), "best": ({"sample": c[0][1], "fraction": c[0][0], "drop_cm": c[0][2]} if c else None)}
    out["best_below_threshold_info"] = best
    drops = [r["drop"] for r in rows_ch.values() if r.get("drop") is not None]
    out["chosen_mark_drop_range_of_all_samples_cm"] = [min(drops), max(drops)] if drops else None
    ws = tower.get("wspawn_tower")
    out["Snd_Base"] = {"xy": ws["location"][:2], "z": 100.0, "source": "WSpawn_Tower XY at Z 100"} if ws else None
    g2 = an["rule"]["glimpses_chosen_mark"]["G2"]
    out["Snd_Mid"] = {"xy": g2["xy"], "z": g2["sample_z"], "source": "G2 sample point (%s)" % g2["sample"]} if g2 else None
    for key, xy in cand.items():
        floor_top = tr.down(xy[0], xy[1], 2700.0, 400.0)
        top = [xy[0], xy[1], (floor_top if floor_top is not None else 2500.0) + 230.0]
        yw, pt = yaw_pitch(eye, top)
        dxy = [top[0] - eye[0], top[1] - eye[1]]
        n = math.hypot(*dxy)
        stop = [eye[0] + dxy[0] / n * 100.0, eye[1] + dxy[1] / n * 100.0, fz]
        lane = lane_check(ed, tr, [top[0], top[1]], [stop[0], stop[1]], fz)
        # the figure comes up the last step first: the short leg from the top step's centre to CINE_StairTop is checked the same way
        approach = lane_check(ed, tr, [s13["centre"][0], s13["centre"][1]], [top[0], top[1]], fz) if (s13 and dist2(s13["centre"], top) > 1.0) else []
        out["stair_top_candidates"][key] = {"CINE_StairTop": rr(top, 2), "floor_z_there": None if floor_top is None else round(floor_top, 2), "mark_yaw_deg": round(yw, 2),
                                            "mark_pitch_deg": round(pt, 2), "horizontal_distance_mark_to_top": round(n, 1), "stop_point": rr(stop, 2), "lane": lane,
                                            "lane_clear": all(l["clear"] for l in lane), "approach_lane_from_top_step": approach,
                                            "approach_lane_clear": all(l["clear"] for l in approach) if approach else None}
    paths = {}
    for key, v in out["stair_top_candidates"].items():
        paths.update({key: walk_path(tower, v["stop_point"], {key: v["CINE_StairTop"]}, tr)[key]})
    out["walk_path"] = paths
    return out


# ---------------------------------------------------------------------------------------------- item 7: notes
NOTE_LABELS = ["Note_Gatehouse", "Note_Nave", "Note_Sacristy", "Note_Ossuary", "Note_Chains", "Note_Cloister"]


def stage_notes(ed):
    out = {"notes": [], "class_path": "/Game/LastBell/Blueprints/Interactables/BP_Inspectable_Note.BP_Inspectable_Note_C"}
    allnotes = ed.find_cls(out["class_path"])
    out["placed_note_count"] = len(allnotes)
    for lab in NOTE_LABELS:
        hits = ed.find(lab)
        if not hits:
            out["notes"].append({"label": lab, "missing": True})
            continue
        r = hits[0]
        p = ed.props(r, ["displayName", "bodyText"])
        rec = {"label": lab, "object": objname(r), "display_name": p.get("displayName"), "body_text": p.get("bodyText"), "found_on": "actor properties displayName / bodyText"}
        rec.update(ed.xf_full(r))
        comp = [c for c in ed.comps(r) if c.endswith(".InspectableComp")]
        if comp:
            cp = ed.props(comp[0], ["displayName", "bodyText"])
            rec["inspectable_comp_display_name"] = cp.get("displayName")
            rec["inspectable_comp_body_text"] = cp.get("bodyText")
        out["notes"].append(rec)
    out["extra_labels_not_in_the_six"] = [ed.label(r) for r in allnotes if ed.label(r) not in NOTE_LABELS]
    return out


# ---------------------------------------------------------------------------------------------- markdown
def fv(v, n=0):
    if v is None:
        return "-"
    return "(" + ", ".join(("%.*f" % (n, x)) for x in v) + ")"


def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in r) + " |")
    return "\n".join(out)


def build_markdown(D):
    L_ = []
    a = L_.append
    a("# P17 F0: read-only cinematics survey")
    a("")
    a("Generated by `Tools/cine/p17_f0_survey.py` on %s. Level `%s`, PIE off. **Nothing was set, created, deleted, saved, loaded or captured.** Item 6 of plan section 7 (Warden slots, bones, mask socket) is ON HOLD and skipped; F0b (Blender) is not part of this run." % (
        D["meta"]["generated"], MAP_PKG))
    a("")
    a("**Read this about every trace result.** `SceneTools.trace_world` returns only the distance to the first blocking hit; the level's visible art is mostly NoCollision, "
      "the collision is the hidden greybox (D-068). So every trace sees **greybox collision only** (the open-riser art stairs and rails are not seen, which makes the visibility numbers conservative). "
      "In addition, the `BP_TagTrigger` boxes block `trace_world` (a down trace over `Trig_CourtyardEntered` returns its top at z 300): the survey detected %d blocking helper volumes (%s) and steps through them "
      "(%d volume skips counted in this run). A real wall hidden inside a helper volume's box would be missed." % (
          len(D["helpers"]["blocking"]), ", ".join(D["helpers"]["blocking"]), D["sight"]["trace_counts"]["volume_skips"]))
    a("")
    # safety
    sb, sa = D["state_before"], D["state_after"]
    a("## 0. Safety checks")
    a("")
    a(md_table(["Check", "Before", "After"], [
        ["PIE running", sb["pie_running"], sa["pie_running"]],
        ["Current level", sb["level"], sa["level"]],
        ["L_Monastery dirty", sb["map_dirty"], sa["map_dirty"]],
        ["Never-save packages dirty (%d checked)" % len(sb["never_save_dirty"]), any(sb["never_save_dirty"].values()), any(sa["never_save_dirty"].values())],
        ["Actor census", sb["actor_count"], sa["actor_count"]]]))
    a("")
    a("Unchanged: **%s**." % D["state_unchanged"])
    a("")
    # 1 mcp
    mc, ans = D["mcp"], D["mcp_answers"]
    a("## 1. MCP toolsets")
    a("")
    a("%d toolsets: %s." % (len(mc["toolsets"]), ", ".join("`%s`" % t for t in mc["toolsets"])))
    a("")
    a("**Capability answers**")
    a("")
    a("- (a) Create/edit Level Sequences: **%s.** Toolsets %s with %d tool names. Present: %s. Missing from the checklist: %s." % (
        "YES" if ans["sequencer_tool_count"] else "NO", ", ".join("`%s`" % t.split(".")[-1] for t in ans["sequencer_toolsets"]), ans["sequencer_tool_count"],
        ", ".join(ans["sequencer_key_tools_present"]), ", ".join(ans["sequencer_key_tools_missing"]) or "none"))
    a("- (b) Arbitrary editor Python: **%s.** %s" % (ans["python_verdict"], ans["python_text"]))
    a("- (c) Author UMG widgets: **%s.** `UMGToolSet.UMGToolSet` with %d tools (create/compile widget blueprints, add/move/wrap/remove widgets, bind events; widget animation tools: %s)." % (
        "YES" if ans["umg_tool_count"] else "NO", ans["umg_tool_count"], ", ".join(ans["umg_animation_tools"]) or "none"))
    a("")
    full = [k for k in mc["matching"] if re.search(r"sequencer|umg|programmatic|slate", k, re.I)]
    other = [k for k in mc["matching"] if k not in full]
    for name in full:
        rec = mc["matching"][name]
        a("### `%s` (%d tools)" % (name, len(rec.get("tools", []))))
        a("")
        a(rec["description"])
        a("")
        a(md_table(["Tool", "Purpose (first sentence)"], [[t["name"], t["purpose"]] for t in rec.get("tools", [])]))
        a("")
    if other:
        a("Other toolsets whose name or description matched the keywords (Sequencer, LevelSequence, MovieScene, Movie, Cinematic, Widget, UMG, Python) but are not cinematics tools: %s." % "; ".join(
            "`%s` (%d tools)" % (k, mc["all_tool_counts"].get(k) or 0) for k in other))
        a("")
    a("Tool count per toolset: " + ", ".join("%s %s" % (k.split(".")[-1], v) for k, v in mc["all_tool_counts"].items()) + ".")
    a("")
    # 2 spawn
    sp = D["spawn"]
    s = sp["spawn"]
    cdo = sp["character_cdo"]
    cpr = sp["cp_approach"]
    a("## 2. Spawn and player")
    a("")
    a(md_table(["PlayerStart", "Location", "Rotation (P, Y, R)", "Start capsule"], [[p["label"], fv(p["location"], 1), fv(p["rotation"], 2), json.dumps(p.get("start_capsule"))] for p in sp["player_starts"]]))
    a("")
    a("`CP_Approach` (%s): location %s, Trigger box extent %s (scale %s), world box %s .. %s; actor bounds %s .. %s. **PlayerStart inside the box: XY %s, XYZ %s.**" % (
        cpr.get("class"), fv(cpr.get("location"), 1), fv(cpr.get("box_extent"), 1), fv(cpr.get("trigger_rel_scale"), 2), fv(cpr.get("box_world_min"), 1), fv(cpr.get("box_world_max"), 1),
        fv(cpr.get("actor_bounds_min"), 1), fv(cpr.get("actor_bounds_max"), 1), s.get("player_start_inside_cp_approach_box_xy"), s.get("player_start_inside_cp_approach_box_xyz")))
    a("")
    a("`BP_LBCharacter` class default object: capsule radius **%s**, half height **%s**, `BaseEyeHeight` **%s**, camera component `%s` relative location %s, attach parent: %s. (`%s`)" % (
        cdo["capsule_radius"], cdo["capsule_half_height"], cdo["BaseEyeHeight"], cdo["camera_component"], fv(cdo["camera_rel_location"], 2), cdo.get("camera_attach_parent") or "not readable over MCP",
        cdo["camera_attach_parent_source"]))
    a("")
    a("**Eye at spawn**")
    a("")
    a(md_table(["Quantity", "Value"], [
        ["PlayerStart XY, Z", "(%s, %s, %s)" % (s["xy"][0], s["xy"][1], s["player_start_z"])],
        ["Floor Z under the PlayerStart (down trace)", s["floor_z"]],
        ["Spawn yaw / pitch / roll", "%s / %s / %s" % (s["yaw"], s["pitch"], s["roll"])],
        ["Capsule centre when settled on the floor (floor + half height)", s["pawn_capsule_centre_when_settled_z"]],
        ["**Eye Z = floor + half height + camera rel Z (the camera component)**", "**%s**" % s["eye_z_camera_component"]],
        ["Eye Z = floor + half height + BaseEyeHeight", s["eye_z_base_eye_height"]],
        ["Plan formula `floor + BaseEyeHeight` (WRONG: BaseEyeHeight is measured from the capsule centre)", s["eye_z_plan_formula_floor_plus_BaseEyeHeight"]],
        ["Eye Z if the pawn were still at the PlayerStart Z (capsule centre %s)" % s["pawn_capsule_centre_at_start_z"], s["eye_z_unsettled_at_start"]]]))
    a("")
    a("The camera uses: %s. **Spawn eye = (%s, %s, %s), yaw %s, pitch 0.**" % (s["camera_uses"], s["xy"][0], s["xy"][1], s["eye_z_camera_component"], s["yaw"]))
    a("")
    # 3 gatehouse
    g = D["gate"]
    a("## 3. Gatehouse passage")
    a("")
    a("Actors whose bounds intersect X -600..600, Y -500..500 (%d returned, the %d with real bounds listed). Collision is the first mesh (or box) component's `collisionEnabled` and profile." % (len(g["actors"]), len(g["actors"]) - sum(1 for r in g["actors"] if r["no_spatial_bounds"])))
    a("")
    rows = []
    nonspatial = [r for r in g["actors"] if r["no_spatial_bounds"]]
    for r in sorted([r for r in g["actors"] if not r["no_spatial_bounds"]], key=lambda r: r["label"]):
        c = r.get("collision") or {}
        rows.append([r["label"], r["class"], fv(r["bounds_min"], 0), fv(r["bounds_max"], 0), (c.get("collision_enabled") or "-") + (" / " + c["profile"] if c.get("profile") else ""), c.get("mesh") or "-"])
    a(md_table(["Label", "Class", "Bounds min", "Bounds max", "Collision", "Mesh"], rows))
    a("")
    from collections import Counter as _C
    a("Zero-size (non-spatial) actors also listed by the bounds query: %d (%s)." % (len(nonspatial), ", ".join("%s x%d" % kv for kv in sorted(_C(r["class"] for r in nonspatial).items()))))
    a("")
    a("**Passage floor Z** (down traces on Y 0 from z 400): " + ", ".join("X %d: %s" % (f["x"], f["floor_z"]) for f in g["floor_traces"]) + ".")
    a("")
    a("**Centreline** (horizontal traces from Y 0 at Z 110 to both sides): " + "; ".join("X %d free Y %s .. %s" % (sp_["x"], sp_["free_y_min"], sp_["free_y_max"]) for sp_ in g["spans"]) + " -> centreline Y **%s**." % g["centreline_y"])
    a("")
    rf = g["roof"]
    if rf.get("found"):
        a("**Roofed part of the passage** (upward traces from floor + 110, Y -100/0/+100): X **%s .. %s** (the `KG_GateArch` vault, %s cm long). Hit heights: centre lane %s, lowest %s, highest %s. Overhead art by bounds covering Y -100..100: %s." % (
            rf["x_min"], rf["x_max"], round(rf["x_max"] - rf["x_min"], 1), rf["hit_z_centre_lane"][0], rf["hit_z_centre_lane"][1], rf["hit_z_centre_lane"][2],
            ", ".join("%s (x %s..%s, z %s..%s)" % (o["label"], o["x"][0], o["x"][1], o["z"][0], o["z"][1]) for o in g["overhead_art_by_bounds"]) or "none"))
    else:
        a("**No roof found over the passage.** Overhead art by bounds: %s." % (", ".join(o["label"] for o in g["overhead_art_by_bounds"]) or "none"))
    a("")
    ln = g["lantern"]
    a("**Lantern points** (source: %s): start = 50 cm inside the outer (-X) end: **(%s, %s, %s)** (floor %s); stop = 50 cm inside the courtyard (+X) end: **(%s, %s, %s)** (floor %s). Floor + 110." % (
        ln["source"], ln["start"]["x"], ln["start"]["y"], ln["start"]["z"], ln["start"]["floor_z"], ln["stop"]["x"], ln["stop"]["y"], ln["stop"]["z"], ln["stop"]["floor_z"]))
    a("")
    a("Roof scan (hit Z at Y -100 / 0 / +100; `-` = no hit):")
    a("")
    a(md_table(["X", "Y -100", "Y 0", "Y +100"], [[r["x"]] + [("-" if h is None else h) for h in r["hit_z_at_y_minus100_0_plus100"]] for r in g["roof_scan"]]))
    a("")
    # 4 wall etc
    w = D["wall"]
    a("## 4. Wall top, strike targets, bell, tower top, EndingTrigger")
    a("")
    ap = w["apparition"]
    a("### Wall top")
    a("")
    a("`Apparition_Courtyard` (%s) at %s; first station location %s (hold %s s, walk path points %s). Down trace from (%s, %s, 1500): **wall top Z = %s**. Art actors at that XY by bounds: %s." % (
        ap.get("class"), fv(ap.get("location"), 1), fv(ap["stations"][0]["location"], 1) if ap.get("stations") else "-", ap["stations"][0]["hold_seconds"] if ap.get("stations") else "-",
        ap["stations"][0]["walk_path_points"] if ap.get("stations") else "-", w["wall_top"]["xy"][0], w["wall_top"]["xy"][1], w["wall_top"]["top_z"],
        "; ".join("%s %s %s..%s%s" % (x["label"], x["class"], fv(x["bounds_min"], 0), fv(x["bounds_max"], 0), (" [" + str(x["collision"].get("collision_enabled")) + "]") if x.get("collision") else "") for x in w["art_at_xy"]) or "none"))
    a("")
    a("**Wall-top eye = %s** (wall top + 232)." % fv(w["wall_top_eye"], 1))
    a("")
    a("Passage courtyard-side mouth at X = %s (stop point X + 50), 9 rays (Y -100/0/+100, Z floor + 50/150/250): **%d of 9 visible** from the wall-top eye." % (w["mouth_x"], w["mouth_visible"]))
    a("")
    a(md_table(["Target", "Ray length", "First hit distance", "Visible"], [[fv(r["target"], 1), r["length"], r["hit_distance"] if r["hit_distance"] is not None else "none", r["visible"]] for r in w["mouth_rays"]]))
    a("")
    a("Aim at the passage centre %s: **yaw %s deg, pitch %s deg** (UE convention, distance %s cm)." % (fv(w["aim"]["target"], 1), w["aim"]["yaw_deg"], w["aim"]["pitch_deg"], w["aim"]["distance"]))
    a("")
    a("### Strike targets")
    a("")
    a(md_table(["Trigger tag", "Delay", "Count", "Spacing", "Profile", "Look gate", "StrikeTargetTag"], [[x["trigger_tag"], round(x["delay"], 2), x["count"], round(x["spacing"], 2), x["profile"], x["look_gate"], x["strike_target_tag"] or "None"] for x in w["scripted_strikes"]]))
    a("")
    for tg, lst in w["strike_targets"].items():
        a("- Tag `%s`: %d actor(s): %s." % (tg, len(lst), "; ".join("%s (%s) at %s" % (x["label"], x["class"], fv(x["location"], 1)) for x in lst) or "none"))
    a("- `LB_StrikeTarget_Tower` exists exactly once: **%s**. Other actors with a label containing `StrikeTarget`: %s." % (w["strike_target_tower_count"] == 1, "; ".join("%s tags %s" % (x["label"], x["tags"]) for x in w["labelled_strike_target_actors"]) or "none"))
    a("")
    a("(Actor tags are only searchable by exact name over MCP, so 'starting `LB_StrikeTarget_`' is covered through the tags `DA_StormSettings.scriptedStrikes` uses plus a label search.)")
    a("")
    # bell
    bl = D["bell"]
    ba = bl["bell_actor"]
    a("### The bell")
    a("")
    a("Actor `Bell` (`%s`) at %s, bounds %s .. %s, `useStateTag` %s, tags %s. Root component: `%s`." % (ba["class"], fv(ba["location"], 1), fv(ba["bounds_min"], 1), fv(ba["bounds_max"], 1), (ba["use_state_tag"] or {}).get("tagName"), ba["tags"], objname(ba["root_component"])))
    a("")
    a(md_table(["Component", "Class", "Mobility", "Rel. location", "Rel. rotation", "Rel. scale", "Attach parent", "World location", "Collision", "Mesh"], [
        [c["name"], c["class"], c.get("mobility", "-"), fv(c.get("relative_location"), 1), fv(c.get("relative_rotation"), 2), fv(c.get("relative_scale"), 3),
         (objname(c.get("attach_parent")) if c.get("attach_parent") else ("none (root)" if c.get("is_root") else "-")) if "mobility" in c else "-", fv(c.get("world_location"), 1),
         "%s / %s" % (c.get("collision_enabled"), c.get("collision_profile")) if "mobility" in c else "-", objname(c.get("mesh")) if c.get("mesh") else "-"] for c in ba["components"]]))
    a("")
    a("Bell frame, headstock, wheel (search names `Headstock`, `BellFrame`, `BellWheel`, `Bell_Beam`, `TWA_Bell`, `Bell_Chain`):")
    a("")
    a(md_table(["Label", "Class", "Mesh", "Location", "Rotation", "Scale", "Bounds min", "Bounds max", "Size"], [
        [p["label"], p["class"], (p.get("mesh_and_collision") or {}).get("mesh") or "-", fv(p["location"], 1), fv(p["rotation"], 2), fv(p["scale"], 3), fv(p["bounds_min"], 1), fv(p["bounds_max"], 1), fv(p["size"], 1)] for p in bl["bell_parts"]]))
    a("")
    ax = bl["axle"]
    a("**Swing axis: `%s`** (axle along the bell mesh component's local %s). %s" % (ax.get("swing_axis"), ax.get("axle_local_axis"), ax.get("reasoning")))
    a("")
    a("- Rope hint: %s." % ax.get("wheel_hint"))
    a("")
    # tower top
    tw = D["tower"]
    a("### Tower top")
    a("")
    a(md_table(["Label", "Class", "Bounds min", "Bounds max", "Top Z", "Collision"], [
        ([r["label"], "MISSING", "-", "-", "-", "-"] if r.get("missing") else
         [r["label"], r["class"], fv(r["bounds_min"], 1), fv(r["bounds_max"], 1), r["top_z"], ((r.get("collision") or {}).get("collision_enabled") or "-")]) for r in tw["named"]]))
    a("")
    for fl in ("F09", "F10", "F11"):
        a("**Stair_%s_*** (%d steps)" % (fl, len(tw["steps"][fl])))
        a("")
        a(md_table(["Label", "Bounds min", "Bounds max", "Top Z", "Centre XY"], [[r["label"], fv(r["bounds_min"], 1), fv(r["bounds_max"], 1), r["top_z"], fv(r["centre"][:2], 1)] for r in tw["steps"][fl]]))
        a("")
    a("**WalkPath points `WP_TowerStairs_00..24`**")
    a("")
    a(md_table(["Label", "Class", "Location", "Floor Z under (down trace)"], [([r["label"], "MISSING", "-", "-"] if r.get("missing") else [r["label"], r["class"], fv(r["location"], 1), r["floor_z_under"]]) for r in tw["waypoints"]]))
    a("")
    if tw.get("wspawn_tower"):
        a("`WSpawn_Tower` (%s) at %s." % (tw["wspawn_tower"]["class"], fv(tw["wspawn_tower"]["location"], 1)))
        a("")
    et = w["ending_trigger"]
    a("### EndingTrigger")
    a("")
    a("`EndingTrigger` class `%s` at %s, bounds %s .. %s, tags %s, **EndingSeconds = %s**. (Not touched.)" % (et.get("class_path"), fv(et.get("location"), 1), fv(et.get("bounds_min"), 1), fv(et.get("bounds_max"), 1), et.get("tags"), et.get("EndingSeconds")))
    a("")
    # 5 sight
    sg = D["sight"]
    pr = D["proposals"]
    an = pr["analysis"]
    a("## 5. Sight lines")
    a("")
    a("Eye = floor + capsule half height + camera rel Z = floor + %s. Capsule radius %s. Traces see greybox collision only (conservative: the open-riser art stairs and rails do not occlude here, the greybox boxes do)." % (sg["eye_offset_above_floor"], sg["capsule_radius"]))
    a("")
    a("### Mark candidates: floor and clearance")
    a("")
    a("Clearance = the minimum distance to a hit from the capsule axis over 16 directions at floor + 20 / 90 / 170 (trace length 300). PASS if >= 102 (60 cm beyond the plan's radius 42); the real capsule radius is %s, so the equivalent bar would be %s." % (sg["capsule_radius"], sg["capsule_radius"] + 60))
    a("")
    rows = []
    for name, mx, my in MARKS:
        m = sg["marks"][name]
        rows.append([name, "(%s, %s)" % (mx, my), m["floor_z"], fv(m["eye"], 1), m["clearance_min"], json.dumps(m.get("clearance_min_at")), ", ".join(m.get("clearance_min_hit_actors") or []) or "-",
                     "PASS" if m["clearance_pass_102"] else "FAIL", "PASS" if m["clearance_pass_94_capsule34"] else "FAIL"])
    a(md_table(["Mark", "XY", "Floor Z", "Eye", "Min clearance cm", "At", "Nearest hit actor(s)", "PASS >= 102", "PASS >= 94"], rows))
    a("")
    for name, mx, my in MARKS:
        m = sg["marks"][name]
        a("- %s nearest hit per height: %s. Ray to the bell centre at Z 2750 (expected %s): first hit at %s -> %s." % (
            name, "; ".join("z+%s: %s cm at %s deg -> %s" % (h, v["min"], v["angle_deg"], ", ".join(v["hit_actors"]) or "?") for h, v in (m.get("clearance_per_height") or {}).items()) or "no hits within 300",
            m["to_bell_centre"]["expected_distance_to_centre"], m["to_bell_centre"]["first_hit_distance"], ", ".join(m["to_bell_centre"].get("hit_actors") or []) or "?"))
    bh = sg["bell_hull_probe"]
    a("- Bell hull probe (%s): first hit at %s cm, point %s, actors %s." % (bh["ray"], bh["first_hit_distance"], fv(bh.get("hit_point"), 1), ", ".join(bh.get("hit_actors") or []) or "?"))
    a("")
    a("### Visible samples per mark (fraction >= 0.6)")
    a("")
    a(md_table(["Mark", "Visible samples", "Total fraction (all %d samples)" % len(sg["samples"]), "Clearance"], [[k, v["visible_count"], v["total_fraction"], "PASS" if sg["marks"][k]["clearance_pass_102"] else "FAIL"] for k, v in an["marks"].items()]))
    a("")
    rl = an["rule"]
    a("Rule: most samples with fraction >= 0.6, tie -> larger total fraction. Ranking: %s. **Chosen mark: %s** (clearance %s). Best mark among those passing clearance: %s." % (
        "; ".join("%s: %d samples, total %s" % tuple(x) for x in rl["ranking"]), rl["chosen_mark"], "PASS" if rl["chosen_clearance_pass_102"] else "FAIL", rl["best_mark_among_clearance_pass"]))
    a("")
    a("### Glimpse proposals (lead rule, fraction >= 0.6; drop = eye Z - (sample Z + 245))")
    a("")
    rows = []
    for mark in an["marks"]:
        gg = rl["glimpses_by_mark"][mark]
        for k in ("G1", "G2"):
            x = gg[k]
            rows.append([mark + (" (chosen)" if mark == rl["chosen_mark"] else ""), k, "none" if not x else "%s at %s, sample Z %s" % (x["sample"], fv(x["xy"], 1), x["sample_z"]),
                         "-" if not x else "%s (%.1f m)" % (x["drop_cm"], x["drop_cm"] / 100.0), "-" if not x else x["horizontal_distance_cm"], "-" if not x else x["fraction"],
                         "-" if not x else x["n_candidates"]])
    a(md_table(["Mark", "Glimpse", "Sample", "Drop cm", "Horizontal cm", "Fraction", "Candidates"], rows))
    a("")
    gc = rl["glimpses_chosen_mark"]
    a("**G1 (drop 6..15 m, nearest 10 m on ties): %s. G2 (drop 3..6 m, nearest 4.5 m on ties): %s.**" % (
        "none" if not gc["G1"] else "%s at %s, Z %s, drop %s, fraction %s" % (gc["G1"]["sample"], fv(gc["G1"]["xy"], 1), gc["G1"]["sample_z"], gc["G1"]["drop_cm"], gc["G1"]["fraction"]),
        "none" if not gc["G2"] else "%s at %s, Z %s, drop %s, fraction %s" % (gc["G2"]["sample"], fv(gc["G2"]["xy"], 1), gc["G2"]["sample_z"], gc["G2"]["drop_cm"], gc["G2"]["fraction"])))
    a("")
    for k in ("G1", "G2"):
        if gc[k]:
            a("- %s top candidates: %s" % (k, ", ".join("%s (f %s, drop %s)" % (c["sample"], c["fraction"], c["drop"]) for c in gc[k]["candidates"])))
    a("")
    vs = pr["visible_samples_chosen_mark"]
    a("Samples with fraction >= 0.6 from the chosen mark %s (%d): %s. Drop range over all %d samples: %s cm." % (
        pr["chosen_mark"], len(vs), "; ".join("%s (f %s, drop %s, %s cm away)" % (v["sample"], v["fraction"], v["drop_cm"], v["horizontal_cm"]) for v in vs),
        len(sg["samples"]), pr["chosen_mark_drop_range_of_all_samples_cm"]))
    a("")
    a("For information only (they do NOT qualify, the 0.6 bar is not relaxed): the best sample inside each drop range regardless of fraction.")
    a("")
    rows = []
    for mark, gg in pr["best_below_threshold_info"].items():
        for gname in ("G1", "G2"):
            x = gg[gname]
            rows.append([mark, gname + (" (6..15 m)" if gname == "G1" else " (3..6 m)"), x["samples_in_drop_range"], "none in range" if not x["best"] else "%s: fraction %s, drop %s" % (x["best"]["sample"], x["best"]["fraction"], x["best"]["drop_cm"])])
    a(md_table(["Mark", "Range", "Samples in range", "Best sample"], rows))
    a("")
    a("### CINE_StairTop, stop point, lane and walk path (chosen mark %s, eye %s)" % (pr["chosen_mark"], fv(pr["mark_eye"], 1)))
    a("")
    a("Two readings of 'the F11 arrival point' are computed. **B** is the plan's nominal (12165, 1665, 2730) = `WP_TowerStairs_23`, where the flight arrives on the slab and the mark's yaw is -90; **A** is the centre of the top step `Stair_F11_13` (= `WP_TowerStairs_22`).")
    a("")
    rows = []
    for key, v in pr["stair_top_candidates"].items():
        rows.append([key, fv(v["CINE_StairTop"], 1), v["floor_z_there"], "%s / %s" % (v["mark_yaw_deg"], v["mark_pitch_deg"]), v["horizontal_distance_mark_to_top"], fv(v["stop_point"], 1), "CLEAR" if v["lane_clear"] else "HIT",
                     pr["walk_path"][key]["length_3d"], pr["walk_path"][key]["length_xy"]])
    a(md_table(["Reading", "CINE_StairTop (floor + 230)", "Floor Z", "Mark yaw / pitch", "Mark to top (XY cm)", "Stop point (100 cm in front of the eye, floor Z)", "Lane (9 traces)", "Walk path 3D cm", "Walk path XY cm"], rows))
    a("")
    for key, v in pr["stair_top_candidates"].items():
        bad = [l for l in v["lane"] if not l["clear"]]
        ap_ = v.get("approach_lane_from_top_step") or []
        apbad = [l for l in ap_ if not l["clear"]]
        a("- %s approach leg (top step centre -> CINE_StairTop, 9 traces): %s" % (key, "not needed (same XY)" if not ap_ else ("all clear" if not apbad else "; ".join(
            "side %s h+%s hit at %s of %s (%s)" % (l["side_cm"], l["height_above_floor"], l["hit_distance"], l["length"], ", ".join(l.get("hit_actors") or [])) for l in apbad))))
        a("- %s lane: %s" % (key, "all 9 traces clear (centreline and +-42 cm, floor + 20/110/200)" if not bad else "; ".join("side %s h+%s hit at %s of %s (%s)" % (l["side_cm"], l["height_above_floor"], l["hit_distance"], l["length"], ", ".join(l.get("hit_actors") or [])) for l in bad)))
    a("")
    for key, p in pr["walk_path"].items():
        a("**Walk path %s** from `%s` (top Z %s): %s cm in 3D, %s cm in XY." % (key, p["first_step"], p["start_z"], p["length_3d"], p["length_xy"]))
        a("")
        a(md_table(["From", "To", "Length 3D", "Length XY"], [[s["from"], s["to"], s["length_3d"], s["length_xy"]] for s in p["segments"]]))
        a("")
    a("Sound anchors: `Snd_Base` = %s; `Snd_Mid` = %s." % ("n/a" if not pr["Snd_Base"] else "%s at Z %s (%s)" % (fv(pr["Snd_Base"]["xy"], 1), pr["Snd_Base"]["z"], pr["Snd_Base"]["source"]),
                                                         "none" if not pr["Snd_Mid"] else "%s at Z %s (%s)" % (fv(pr["Snd_Mid"]["xy"], 1), pr["Snd_Mid"]["z"], pr["Snd_Mid"]["source"])))
    a("")
    a("### Samples")
    a("")
    a(md_table(["Id", "Kind", "XY", "Z", "Z source"], [[s["id"], s["kind"], fv(s["xy"], 1), s["z"], s["z_source"]] for s in sg["samples"]]))
    a("")
    for name, mx, my in MARKS:
        a("#### %s: fraction per sample (bits = 9 rays: height +200/+245/+290 x lateral -30/0/+30)" % name)
        a("")
        rows = []
        for s in sg["samples"]:
            r = sg["rays"][name].get(s["id"], {})
            rows.append([s["id"], fv(s["xy"], 0), s["z"], r.get("horizontal_distance", "-"), r.get("drop", "-"), r.get("fraction", "-"), r.get("bits", "-")])
        a(md_table(["Sample", "XY", "Z", "Horizontal cm", "Drop cm", "Fraction", "Bits"], rows))
        a("")
    # 7 notes
    nt = D["notes"]
    a("## 7. The six notes (verbatim)")
    a("")
    same = all(n.get("display_name") == n.get("inspectable_comp_display_name") and n.get("body_text") == n.get("inspectable_comp_body_text") for n in nt["notes"] if not n.get("missing"))
    a("Found on the actor (`displayName`, `bodyText`; the `InspectableComp` component holds %s copies). %d `BP_Inspectable_Note_C` actors are placed; labels outside the six: %s." % (
        "identical" if same else "DIFFERENT", nt["placed_note_count"], nt["extra_labels_not_in_the_six"] or "none"))
    a("")
    for n in nt["notes"]:
        if n.get("missing"):
            a("### %s: MISSING" % n["label"])
            continue
        a("### %s at %s" % (n["label"], fv(n["location"], 0)))
        a("")
        a("- DisplayName: %s" % json.dumps(n["display_name"], ensure_ascii=False))
        a("- BodyText: %s" % json.dumps(n["body_text"], ensure_ascii=False))
        a("")
    # findings
    a("## 8. Findings / contradictions with the plan's nominal values")
    a("")
    for f in D["findings"]:
        a("- " + f)
    a("")
    return "\n".join(L_)


def build_findings(D):
    f = []
    sp = D["spawn"]
    s = sp["spawn"]
    cdo = sp["character_cdo"]
    f.append("MCP DOES have Sequencer authoring: `animation_toolset.toolsets.sequencer.SequencerTools` (create_level_sequence, add_spawnable_from_class, create_camera, add_track_to_binding, add_section, "
             "set_camera_cut_binding, add_marked_frame, add_event_trigger_section ...) plus the keyframing, Control Rig, import/export, conditions, custom-binding and outliner toolsets, and "
             "`UMGToolSet` (no widget-animation tool). There is no general editor Python (only the sandboxed `ProgrammaticToolset.execute_tool_script`). Plan section 8 (S1 headless Python spike) "
             "can be replaced or shortened by an MCP spike; the lead should decide.")
    f.append("Capsule radius is **%s**, not 42 (half height %s). The clearance bar of 102 cm is computed as asked; with the real radius the equivalent bar is %s." % (cdo["capsule_radius"], cdo["capsule_half_height"], cdo["capsule_radius"] + 60))
    f.append("`BaseEyeHeight` (%s) is measured from the capsule centre, so the spawn eye is floor + %s + %s = **%s**, not floor + BaseEyeHeight (%s). Plan 3.1 'floor Z + BaseEyeHeight' for `Cam_Intro` pose B "
             "must read floor + %s (floor under the PlayerStart is %s, not 0)." % (
                 cdo["BaseEyeHeight"], cdo["capsule_half_height"], cdo["camera_rel_location"][2], s["eye_z_camera_component"], s["eye_z_plan_formula_floor_plus_BaseEyeHeight"], 152, s["floor_z"]))
    if s.get("player_start_inside_cp_approach_box_xy") is False:
        f.append("The PlayerStart %s is **outside** the `CP_Approach` Trigger box in XY (box %s .. %s); the box starts 50 cm east of the spawn." % (
            fv([s["xy"][0], s["xy"][1], s["player_start_z"]], 0), fv(sp["cp_approach"].get("box_world_min"), 0), fv(sp["cp_approach"].get("box_world_max"), 0)))
    bell = D["bell"]["bell_actor"]
    mesh = next((c for c in bell["components"] if "mobility" in c), None)
    if mesh and mesh["mobility"] != "Movable":
        f.append("The bell mesh component `%s` is %s (the plan needs Movable)." % (mesh["name"], mesh["mobility"]))
    elif mesh:
        f.append("The bell mesh component `%s` is **already Movable** in the placed instance (plan section 5 says P17-5b must set it); it is the actor's root component, collision `%s / %s`, so its relative "
                 "transform is the world transform." % (mesh["name"], mesh.get("collision_enabled"), mesh.get("collision_profile")))
    ax = D["bell"]["axle"]
    if ax:
        hc = ax.get("headstock_centre")
        f.append("Pivot: the bell component origin is z %s (the bell's top); the headstock axle is at about z %s (headstock bounds centre), i.e. ~%s cm above the component origin. A pitch applied to the "
                 "component rotates about its own origin, not about the axle; `FBellPendulum` should account for the offset (or the pivot should be moved to the axle)." % (
                     bell["location"][2], hc[2] if hc else "?", round((hc[2] - bell["location"][2]), 0) if hc else "?"))
    f.append("`Bell_Beam` (cube, scale 0.8x2x1 at z 3350) and `Bell_Chain` (cube 10x10x550 at z 3025) are invisible BlockAll greybox cubes; `TWA_Headstock` and `TWA_BellRope` are NoCollision art, "
             "`TWA_BellFrame` blocks. None of them moves when the bell mesh component swings.")
    tcg = next((a_ for a_ in D["gate"]["actors"] if a_["label"] == "Trig_CourtyardEntered"), None)
    f.append("Blocking helper volumes: %s. `trace_world` stops at the BP_TagTrigger boxes (and `Kill_Pit`) although `Trig_CourtyardEntered` reads collision %s; a plain trace through the gate "
             "passage or around the tower top meets a trigger volume. The survey steps through them (using the recorded box-like solids flush with them); in-game it matters only for traces "
             "on a channel those boxes block (the channel `trace_world` uses is not documented)." % (", ".join(D["helpers"]["blocking"]), ((tcg or {}).get("collision") or {}).get("collision_enabled", "?") + " / " + str(((tcg or {}).get("collision") or {}).get("profile", "?"))))
    pr = D["proposals"]
    gc = pr["analysis"]["rule"]["glimpses_chosen_mark"]
    if not gc["G1"] or not gc["G2"]:
        f.append("Glimpse rule: %s on the chosen mark %s (plan 3.2: a missing glimpse becomes sound-only). From the belfry floor the lower stair flights are hidden by the belfry floor and the core; only "
                 "flight F11 (its upper half) and the top slab are visible, and every visible sample has a drop of at most %s cm (drop = eye Z minus sample Z + 245). No sample qualifies for G1 or G2 on any mark." % (
                     "; ".join(k + " none" for k in ("G1", "G2") if not gc[k]), pr["chosen_mark"], max([v["drop_cm"] for v in pr["visible_samples_chosen_mark"]] or [0])))
    wp = pr["walk_path"]
    ka, kb = [k for k in wp if k.startswith("A_")], [k for k in wp if k.startswith("B_")]
    if ka and kb:
        f.append("Walk path from `Stair_F11_00`: reading A (top step) %s cm = %.1f s at 110 cm/s, reading B (slab arrival, the plan's nominal CINE_StairTop) %s cm = %.1f s. The plan's nominal arrival 64.0 "
                 "(55.0 + 9.0 s) matches A; with B the figure arrives at about %.1f s. Lane to the stop point: A %s, B %s." % (
                     wp[ka[0]]["length_3d"], wp[ka[0]]["length_3d"] / 110.0, wp[kb[0]]["length_3d"], wp[kb[0]]["length_3d"] / 110.0, 55.0 + wp[kb[0]]["length_3d"] / 110.0,
                     "CLEAR" if pr["stair_top_candidates"][ka[0]]["lane_clear"] else "BLOCKED (rail / flight / bell frame)", "CLEAR" if pr["stair_top_candidates"][kb[0]]["lane_clear"] else "BLOCKED"))
    if D["wall"]["mouth_visible"] != 9:
        f.append("Only %d of 9 passage-mouth rays are visible from the wall-top eye." % D["wall"]["mouth_visible"])
    m2 = D["sight"]["marks"].get("M2")
    if m2 and not m2["clearance_pass_102"]:
        f.append("M2 fails the clearance bar: %s cm to %s (the north wall, Y 2460, is 80 cm away)." % (m2["clearance_min"], ", ".join(m2.get("clearance_min_hit_actors") or [])))
    f.append("The six notes (section 7) against the intro cards of plan 3.1: no hard contradiction. Points for the lead: (1) `Note_Gatehouse` is a traveller who 'came up the cliff path at dusk' and "
             "wrote 'by the gate', while Intro_1 says no one has climbed to the monastery for forty years, so that note has to be older than forty years (it carries no date); (2) the same note says "
             "the bell has 'no rope and no clapper' but the belfry has `TWA_BellRope` hanging from the wheel (art, NoCollision); (3) `Note_Cloister` ('The great bell rang again tonight, and no hand was on "
             "the rope') describes an earlier ringing (the brothers were still there), so it fits Intro_2 (silent since they vanished) and Intro_3 (rung again tonight);")
    return f


# ---------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="ignore every stage cache")
    ap.add_argument("--only", default="", help="comma list of stages to re-run (others use the cache): helpers,mcp,spawn,gate,wall,bell,tower,sight,proposals,notes")
    ap.add_argument("--out", default=os.path.join(ROOT, "Docs", "ArtTest", "cine"), help="output folder")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--stop-after", default="", help="debug: stop (exit 0, nothing written) after this stage")
    a = ap.parse_args()
    stages = ["helpers", "mcp", "spawn", "gate", "wall", "bell", "tower", "sight", "proposals", "notes"]
    redo = set(stages) if a.refresh else set(s for s in a.only.split(",") if s)
    try:
        ed = Ed()
        before = read_state(ed)
        say("state before: %s" % json.dumps({k: v for k, v in before.items() if k != "never_save_dirty"}))
        if not state_clean(before):
            say("The editor is not in the expected clean state (PIE off, L_Monastery loaded, nothing dirty): stop. %s" % json.dumps(before))
            sys.exit(2)
        cache = Cache(False)
        if a.refresh or "sight" in redo:
            try:
                os.remove(os.path.join(SCRATCH, "sight_partial.json"))
            except OSError:
                pass
        data = {}

        def run(name, fn):
            cache.refresh = name in redo
            data[name] = cache.get(name, fn)
            if a.stop_after == name:
                say("stopped after %s (--stop-after); nothing written" % name)
                sys.exit(0)

        run("helpers", lambda: stage_helpers(ed))
        tr = make_tracer(ed, data["helpers"])
        run("mcp", lambda: stage_mcp(ed))
        run("spawn", lambda: stage_spawn(ed, tr))
        run("gate", lambda: stage_gate(ed, tr))
        run("wall", lambda: stage_wall(ed, tr, data["gate"]))
        run("bell", lambda: stage_bell(ed))
        run("tower", lambda: stage_tower(ed, tr))
        cache.refresh = "sight" in redo
        run("sight", lambda: stage_sight(ed, tr, data["tower"], cache))
        run("proposals", lambda: stage_proposals(ed, tr, data["tower"], data["sight"]))
        run("notes", lambda: stage_notes(ed))
        after = read_state(ed)
        say("state after:  %s" % json.dumps({k: v for k, v in after.items() if k != "never_save_dirty"}))
    except EditorStop as e:
        say("STOP: editor problem (%s). Nothing was written." % e)
        sys.exit(3)
    same = (after["actor_count"] == before["actor_count"] and state_clean(after) and before["actor_count"] == after["actor_count"])
    ans = mcp_answers(data["mcp"])
    ans["python_verdict"], ans["python_text"] = python_verdict(data["mcp"])
    D = {"meta": {"generated": time.strftime("%Y-%m-%d %H:%M"), "script": "Tools/cine/p17_f0_survey.py", "level": MAP_PKG, "read_only": True,
                  "note": "stages are cached in Saved/p17_f0_scratch; state_before/state_after are read by this invocation; traces see greybox collision only"},
         "state_before": before, "state_after": after, "state_unchanged": same, "helpers": data["helpers"], "mcp": data["mcp"], "mcp_answers": ans,
         "spawn": data["spawn"], "gate": data["gate"], "wall": data["wall"], "bell": data["bell"], "tower": data["tower"], "sight": data["sight"],
         "proposals": data["proposals"], "notes": data["notes"]}
    D["findings"] = build_findings(D)
    if not a.no_write:
        os.makedirs(a.out, exist_ok=True)
        with open(os.path.join(a.out, "p17_f0.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(D, f, indent=1)
        with open(os.path.join(a.out, "p17_f0_tables.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(build_markdown(D))
        say("wrote %s" % a.out)
    say("state unchanged: %s" % same)
    sys.exit(0 if same else 2)


def python_verdict(mcp):
    cands = {}
    for name, rec in mcp["matching"].items():
        for t in rec.get("tools", []):
            if PY_TOOL_RE.search(t["name"]):
                cands.setdefault(name, []).append(t["name"])
    if not cands:
        return "NO", "No tool whose name suggests Python, exec, script or console execution was found."
    txt = "; ".join("`%s`: %s" % (k.split(".")[-1], ", ".join(v)) for k, v in cands.items())
    prog = [k for k in cands if "programmatic" in k.lower()]
    if prog:
        return "NO (only a sandboxed tool-orchestration script)", ("`ProgrammaticToolset.execute_tool_script` runs a small sandboxed Python script that may import only math, time, re, json, datetime, copy and "
                                                                  "call other registered tools via execute_tool(); it is not general editor Python (no `unreal` module). Candidates found: " + txt + ".")
    return "UNCLEAR", "Candidates: " + txt


if __name__ == "__main__":
    main()
