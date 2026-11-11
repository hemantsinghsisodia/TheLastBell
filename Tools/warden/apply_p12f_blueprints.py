"""P12 fix set 1, F3 + F4: Blueprint work for the Warden's scripted appearances and its attack light.

Spec: Docs/plans/P12_FIX1_WARDEN_APPEARANCES.md, section 6 (BP_WardenApparition and the map swap) and section 7 (BP_Warden).
Run with -I, editor open on L_Monastery, no PIE. Exactly one mode per run. Every step is idempotent and reads each value back.

    --apparition   create BP_WardenApparition (parent LBWardenApparition) if missing; set Body and Glow on the class default
                   object; compile with warnings as errors. Saves nothing.
    --map          place Apparition_Courtyard and Apparition_Chapel (section 3 values, folder Gameplay/Warden), then remove the two
                   old BP_WardenSilhouette_C_0 / _C_2 actors. Checks the actor count is 2980 again. Saves nothing.
    --warden       section 7: TellLight values, remove the AttachTellLightToMask call and function, MaskGlowMID / LastFeedbackState,
                   SetupMaskGlow, SetMaskGlow, the glow levels in PlayStateFeedback / ShowWindupTell / EndWindupTell; compile with
                   warnings as errors. Saves nothing.
    --check        read everything back (read-only)
    --save NAME    one package per call: apparition | map | warden. Never anything else.

Order of the whole task (the plan's rule): --apparition, --save apparition, --map, --save map, THEN --warden, --save warden. The map is
saved exactly once and never again in the session, because after the BP_Warden template write the placed instances are stale.
Exit codes: 0 ok, 1 mismatch or refused, 2 a tool call failed (state unknown: run --check first, never retry in a loop).

P13-7 NOTE: the check_* functions and INSTANCES below now describe the state AFTER the Phase 13 hookup (Tools/warden/apply_p13_hookup.py):
the chapel has one station with a WalkPath, L_Monastery has 12 stoop zones (2992 actors), and BP_Warden's ShowWindupTell, PlayStateFeedback and
EventGraph have the added animation calls. The apply modes (--apparition, --map, --warden) are Phase 12 history: do not rerun them.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE  # noqa: E402

OB = "editor_toolset.toolsets.object.ObjectTools"
AS = "editor_toolset.toolsets.asset.AssetTools"
SC = "editor_toolset.toolsets.scene.SceneTools"
AC = "editor_toolset.toolsets.actor.ActorTools"
BPT = "editor_toolset.toolsets.blueprint.BlueprintTools"
APP = "EditorToolset.EditorAppToolset"

MAP_PKG = "/Game/LastBell/Maps/L_Monastery"
EXPECTED_ACTORS = 2980            # the P12 count (used by the P12 apply modes)
ACTORS_NOW = 2992                 # after P13-7: the same plus the 12 stoop zones
APP_PKG = "/Game/LastBell/Blueprints/Interactables/BP_WardenApparition"
APP_CLASS = "/Script/LastBell.LBWardenApparition"
APP_CDO = APP_PKG + ".Default__BP_WardenApparition_C"
WARDEN_PKG = "/Game/LastBell/Blueprints/AI/BP_Warden"
MESH_APP = "/Game/LastBell/Characters/Warden/Meshes/SM_LB_Warden_Apparition"
MI_DIR = "/Game/LastBell/Characters/Warden/Materials/"
MI_GLOW = MI_DIR + "MI_Warden_ApparitionGlow"
PLANE = "/Engine/BasicShapes/Plane"
FOLDER = "Gameplay/Warden"

# the plan's section 3 table (world cm; station = feet; every duration in seconds)
def station(x, y, z, cone, mind, fin, hold, fout, gap, walk=None, speed=None):
    s = {"location": {"x": x, "y": y, "z": z}, "lookConeDegrees": cone, "minPlayerDistance": mind,
         "fadeInSeconds": fin, "holdSeconds": hold, "fadeOutSeconds": fout, "gapAfterSeconds": gap}
    if walk is not None:                                  # P13: the station's WalkPath and WalkSpeed
        s["walkPath"] = [{"x": a, "y": b, "z": c} for a, b, c in walk]
        s["walkSpeed"] = speed
    return s


# P13-7: the chapel has ONE station (the rail) with a WalkPath into the sacristy; the second station is gone.
INSTANCES = {
    "Apparition_Courtyard": {"tag": "State.Event.CourtyardEntered", "arm": 0.5, "glow": 1000.0, "look": 200.0,
                             "stations": [station(6020, 1300, 800, 30, 0, 1.5, 4.0, 2.0, 0.0)]},
    "Apparition_Chapel": {"tag": "State.Ritual.1", "arm": 1.5, "glow": 0.0, "look": 200.0,
                          "stations": [station(8380, -120, 0, 30, 150, 1.0, 2.5, 1.5, 0.0,
                                               walk=[(8380, -380, 0), (8500, -650, 0), (8500, -1000, 0), (8250, -1100, 0)], speed=110)]},
}
OLD_ACTORS = {"BP_WardenSilhouette_C_0": "Silh_CourtyardWall", "BP_WardenSilhouette_C_2": "Silh_ChapelWindow"}


# ------------------------------------------------------------------ helpers
def rp(path):
    return {"refPath": path}


def pkg_ref(pkg):
    return rp(f"{pkg}.{pkg.split('/')[-1]}")


def as_json(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:  # noqa: BLE001
            return v
    return v


def short(r):
    r = r.get("refPath") if isinstance(r, dict) else r
    return r.split("/")[-1].split(".")[0] if r and r != "None" else None


def close(a, b, tol=1e-3):
    return abs(float(a) - float(b)) <= tol


def same(want, got):
    """Does a value read back equal the wanted one? (refs by path, numbers with a tolerance, dicts key by key, lists in order)"""
    if isinstance(want, dict):
        if "refPath" in want:
            return isinstance(got, dict) and got.get("refPath") == want["refPath"]
        return isinstance(got, dict) and all(k in got and same(v, got[k]) for k, v in want.items())
    if isinstance(want, list):
        return isinstance(got, list) and len(got) == len(want) and all(same(w, g) for w, g in zip(want, got))
    if isinstance(want, bool) or isinstance(want, str):
        return want == got
    return isinstance(got, (int, float)) and not isinstance(got, bool) and close(want, got)


def get1(ue, path, name):
    r = as_json(ue.call(OB, "get_properties", {"instance": rp(path), "properties": [name]}))
    return r[name]


def set_props(ue, path, values):
    ue.call(OB, "set_properties", {"instance": rp(path), "values": json.dumps(values)})


def put(ue, path, values, label):
    """set_properties, read back every key; a vector that did not stick is retried one axis per call. Returns problems."""
    bad = []
    set_props(ue, path, values)
    for k, want in values.items():
        got = get1(ue, path, k)
        if not same(want, got) and isinstance(want, dict) and "refPath" not in want and all(isinstance(x, (int, float)) for x in want.values()):
            cur = dict(got) if isinstance(got, dict) else dict(want)
            for ax in want:
                cur[ax] = want[ax]
                set_props(ue, path, {k: cur})
            got = get1(ue, path, k)
        if not same(want, got):
            bad.append(f"{label}.{k}: wanted {want}, read {got}")
    return bad


def is_dirty(ue, pkg):
    return ue.call(AS, "is_dirty", {"asset_path": pkg}) if ue.call(AS, "exists", {"path": pkg}) else None


def count_actors(ue):
    # this large reply sometimes drops the connection; a second try is enough (as in read_review.count)
    for attempt in range(3):
        try:
            return len(ue.call(SC, "find_actors", {"name": "", "tag": "", "collision_channels": []}))
        except ConnectionResetError:
            if attempt == 2:
                raise
            time.sleep(2)


def inst(actor, comp=None):
    return f"{MAP_PKG}.L_Monastery:PersistentLevel.{actor}" + (f".{comp}" if comp else "")


def preflight(ue, need_clean_map=True):
    if ue.call(APP, "IsPIERunning", {}):
        print("refused: PIE is running. Nothing was changed.")
        return False
    if ue.call(SC, "get_current_level", {}) != MAP_PKG:
        print(f"refused: the current level is not {MAP_PKG}")
        return False
    return True


def compile_bp(ue, pkg):
    """Compile with warnings as errors: any warning or error raises, and is reported here."""
    try:
        ue.call(BPT, "compile_blueprint", {"blueprint": pkg_ref(pkg), "warnings_as_errors": True})
    except Exception as e:  # noqa: BLE001
        print(f"  compile {pkg.split('/')[-1]}: FAILED or has warnings: {str(e)[:900]}", flush=True)
        return False
    print(f"  compile {pkg.split('/')[-1]}: OK (no errors, no warnings; warnings_as_errors on)", flush=True)
    return True


# ------------------------------------------------------------------ BP_WardenApparition (section 6, step 1)
BODY_VALUES = {"staticMesh": pkg_ref(MESH_APP), "relativeLocation": {"x": 0, "y": 0, "z": 0},
               "relativeRotation": {"pitch": 0, "yaw": 0, "roll": 0}, "relativeScale3D": {"x": 1, "y": 1, "z": 1}}
GLOW_VALUES = {"staticMesh": pkg_ref(PLANE), "overrideMaterials": [pkg_ref(MI_GLOW)],
               "relativeLocation": {"x": -150, "y": 0, "z": 150}, "relativeRotation": {"pitch": 90, "yaw": 0, "roll": 0},
               "relativeScale3D": {"x": 1, "y": 1, "z": 1}}


def do_apparition(ue):
    if not ue.call(AS, "exists", {"path": APP_PKG}):
        r = ue.call(BPT, "create", {"folder_path": "/Game/LastBell/Blueprints/Interactables", "asset_name": "BP_WardenApparition",
                                   "asset_type": rp(APP_CLASS)})
        print("  created", r, flush=True)
    else:
        print("  BP_WardenApparition exists", flush=True)
    bad = put(ue, APP_CDO + ":Body", BODY_VALUES, "Body") + put(ue, APP_CDO + ":Glow", GLOW_VALUES, "Glow")
    ok = compile_bp(ue, APP_PKG)
    # compiling can reset what was written: read the class default object again
    for comp, vals in (("Body", BODY_VALUES), ("Glow", GLOW_VALUES)):
        for k, want in vals.items():
            got = get1(ue, APP_CDO + ":" + comp, k)
            if not same(want, got):
                bad.append(f"{comp}.{k} after compile: wanted {want}, read {got}")
    print("apparition:", "OK" if not bad and ok else f"PROBLEMS {bad}; compile {ok}")
    return 0 if not bad and ok else 1


# ------------------------------------------------------------------ the map (section 6, step 2)
def find_new(ue, label):
    out = []
    for a in ue.call(SC, "find_actors", {"name": label, "tag": "", "collision_channels": []}):
        p = a["refPath"] if isinstance(a, dict) else a
        if ue.call(AC, "get_label", {"actor": rp(p)}) == label:
            out.append(p)
    return out


def instance_values(spec):
    return {"TriggerTag": {"tagName": spec["tag"]}, "ArmDelaySeconds": spec["arm"], "LookPointHeight": spec["look"], "GlowSizeCm": spec["glow"]}


def do_map(ue):
    n0 = count_actors(ue)
    print(f"  actor count before: {n0}", flush=True)
    if n0 != EXPECTED_ACTORS and not any(find_new(ue, k) for k in INSTANCES):
        print(f"REFUSED: {n0} actors, expected {EXPECTED_ACTORS} before the swap")
        return 1
    if not ue.call(AS, "exists", {"path": APP_PKG}):
        print("REFUSED: BP_WardenApparition does not exist; run --apparition first")
        return 1
    bad = []
    names = {}
    for label, spec in INSTANCES.items():
        found = find_new(ue, label)
        if len(found) > 1:
            print(f"REFUSED: {len(found)} actors labelled {label}")
            return 1
        if found:
            path = found[0]
            print(f"  {label} exists: {path}", flush=True)
        else:
            first = spec["stations"][0]["location"]
            r = ue.call(SC, "add_to_scene_from_class", {
                "actor_type": rp(APP_PKG + ".BP_WardenApparition_C"), "name": label,
                "xform": {"location": first, "rotation": {"pitch": 0, "yaw": 0, "roll": 0}, "scale": {"x": 1, "y": 1, "z": 1}}})
            path = r["refPath"] if isinstance(r, dict) else r
            print(f"  placed {label}: {path}", flush=True)
        names[label] = path
        ue.call(AC, "set_label", {"actor": rp(path), "label": label})
        ue.call(SC, "set_actor_folder", {"actor": rp(path), "folder_path": FOLDER})
        # location and rotation and scale together (a partial xform resets the rest)
        first = spec["stations"][0]["location"]
        ue.call(AC, "set_actor_transform", {"actor": rp(path), "worldspace": True, "xform": {
            "location": first, "rotation": {"pitch": 0, "yaw": 0, "roll": 0}, "scale": {"x": 1, "y": 1, "z": 1}}})
        bad += put(ue, path, instance_values(spec), label)
        # the array: grow first (one call), then set the elements (a second call)
        want = spec["stations"]
        if not isinstance(get1(ue, path, "Stations"), list) or len(get1(ue, path, "Stations")) != len(want):
            set_props(ue, path, {"Stations": [{} for _ in want]})
        bad += put(ue, path, {"Stations": want}, label)
    # remove the two old silhouettes (by object name; their labels are read first)
    for obj, old_label in OLD_ACTORS.items():
        path = inst(obj)
        try:
            lab = ue.call(AC, "get_label", {"actor": rp(path)})
        except Exception:  # noqa: BLE001
            print(f"  old {obj}: already gone", flush=True)
            continue
        if lab != old_label:
            print(f"REFUSED: {obj} has label {lab!r}, expected {old_label!r}")
            return 1
        print(f"  removing old {obj} ({lab}): {ue.call(SC, 'remove_from_scene', {'actor': rp(path)})}", flush=True)
    n1 = count_actors(ue)
    print(f"  actor count after: {n1} (expected {EXPECTED_ACTORS})", flush=True)
    if n1 != EXPECTED_ACTORS:
        bad.append(f"actor count {n1}")
    print("map:", "OK" if not bad else f"PROBLEMS {bad}")
    return 0 if not bad else 1


# ------------------------------------------------------------------ BP_Warden (section 7)
TELL = WARDEN_PKG + ".BP_Warden_C:TellLight_GEN_VARIABLE"
# new light: about 40 cm in front of the mask at face height. Parent is PlaceholderBody (0, 0, -110), so (110, 0, 235) from the
# floor line is actor + (110, 0, 125). Radius 160 -> 700, intensity 800 -> 5000 (Unitless, no shadows, as before).
TELL_VALUES = {"relativeLocation": {"x": 110, "y": 0, "z": 235}, "attenuationRadius": 700, "intensity": 5000}
TELL_WORLD_OFFSET = (110.0, 0.0, 125.0)
FN_ATTACH, FN_SETUP, FN_SET = "AttachTellLightToMask", "SetupMaskGlow", "SetMaskGlow"
LEVEL_CHASE, LEVEL_FLARE, LEVEL_OFF = 0.25, 1.0, 0.0
# ELBWardenState (LBWardenTypes.h): Dormant 0, Patrol 1, Investigate 2, Suspicious 3, Search 4, Chase 5, Attack 6, Return 7.
# The delegate hands the state over as a byte, and add_variable can't make an enum variable, so LastFeedbackState is a byte.
STATE_CHASE, STATE_ATTACK = 5, 6
SLOT_NAME = "M_Warden_BellMetal"

DSL_SETUP = f'''(fn {FN_SETUP} ()
  ; the slot is found by name, never by a fixed index
  (bind mesh (Variables|Character|GetMesh))
  (bind idx (Rendering|Material|GetMaterialIndex :self mesh :MaterialSlotName "{SLOT_NAME}"))
  (if (>= idx 0)
    (bind mid (Rendering|Material|CreateDynamicMaterialInstance :self mesh :ElementIndex idx))
    (Variables|Default|SetMaskGlowMID mid)))
'''
# the Set Scalar Parameter Value node of the dynamic instance can't be picked in the DSL (the same type id exists for parameter
# collections), so the DSL builds the IsValid skeleton and the node is added with create_node + declaring_class
DSL_SET_SKELETON = f'''(fn {FN_SET} (Level)
  (bind mid (Variables|Default|GetMaskGlowMID))
  (Utilities|IsValid mid
    (:"Is Valid")
    (:"Is Not Valid")))
'''
DSL_FEEDBACK = f'''(fn PlayStateFeedback (NewState)
  ; remember the state for EndWindupTell; Chase = dull red, Attack = left to the windup, anything else = off
  (Variables|Default|SetLastFeedbackState NewState)
  (if (== NewState {STATE_CHASE})
    (CallFunction|{FN_SET} :Level {LEVEL_CHASE})
    (elif (!= NewState {STATE_ATTACK})
      (CallFunction|{FN_SET} :Level {LEVEL_OFF}))))
'''


def wg(name):
    return rp(f"{WARDEN_PKG}.BP_Warden:{name}")


class Graph:
    """Read-only snapshot of one BP_Warden graph (find_nodes + get_node_infos)."""

    def __init__(self, ue, name):
        self.ue, self.name = ue, name
        nodes = ue.call(BPT, "find_nodes", {"graph": wg(name), "title": ""})
        self.infos = ue.call(BPT, "get_node_infos", {"nodes": nodes}) if nodes else []
        self.by = {i["node"]["refPath"]: i for i in self.infos}

    def type(self, suffix):
        return [i for i in self.infos if i["type_id"].endswith(suffix)]

    def pins(self, info, direction):
        return info["output_pins"] if direction == "out" else info["input_pins"]

    def pin(self, info, name, direction):
        for p in self.pins(info, direction):
            if p["name"] == name:
                return p
        raise KeyError(f"{info['type_id']} has no {direction} pin {name!r}")

    def targets(self, info, out_name):
        """[(node info, input pin name)] that an output pin feeds."""
        out = []
        for c in self.pin(info, out_name, "out")["connected_pins"]:
            t = self.by[c["node"]["refPath"]]
            out.append((t, next(p["name"] for p in t["input_pins"] if p["pin_id"]["index_id"] == c["index_id"])))
        return out

    def sources(self, info, in_name):
        """[(node info, output pin name)] feeding an input pin."""
        out = []
        for c in self.pin(info, in_name, "in")["connected_pins"]:
            s = self.by[c["node"]["refPath"]]
            out.append((s, next(p["name"] for p in s["output_pins"] if p["pin_id"]["index_id"] == c["index_id"])))
        return out

    def value(self, info, in_name):
        return self.pin(info, in_name, "in")["value"]


def fn_names(ue):
    return [r["refPath"].split(":")[-1] for r in ue.call(BPT, "list_graphs", {"blueprint": pkg_ref(WARDEN_PKG)})]


def new_node(ue, graph, type_id, x, y, declaring=None):
    args = {"graph": wg(graph), "type_id": type_id, "pos": {"x": x, "y": y}}
    if declaring:
        args["declaring_class"] = rp(declaring)
    n = ue.call(BPT, "create_node", args)
    return ue.call(BPT, "get_node_infos", {"nodes": [n]})[0]


def link(ue, g, out_info, out_name, in_info, in_name):
    ue.call(BPT, "connect_pins", {"output_pin": g.pin(out_info, out_name, "out")["pin_id"], "input_pin": g.pin(in_info, in_name, "in")["pin_id"]})


def set_pin(ue, g, info, name, value):
    ue.call(BPT, "set_pin_value", {"pin": g.pin(info, name, "in")["pin_id"], "value": value})


def step_light(ue):
    bad = put(ue, TELL, TELL_VALUES, "TellLight")
    print("  TellLight template:", "ok" if not bad else bad, flush=True)
    return bad


def step_variables(ue):
    bp = pkg_ref(WARDEN_PKG)
    have = ue.call(BPT, "list_variables", {"blueprint": bp})
    if "MaskGlowMID" not in have:
        ue.call(BPT, "add_object_variable", {"blueprint": bp, "name": "MaskGlowMID", "object_class": rp("/Script/Engine.MaterialInstanceDynamic")})
    if "LastFeedbackState" not in have:
        ue.call(BPT, "add_variable", {"blueprint": bp, "name": "LastFeedbackState", "type_name": "byte"})
    have = ue.call(BPT, "list_variables", {"blueprint": bp})
    bad = [v for v in ("MaskGlowMID", "LastFeedbackState") if v not in have]
    print("  variables:", have, "" if not bad else f"MISSING {bad}", flush=True)
    return bad


def step_set_mask_glow(ue):
    bp = pkg_ref(WARDEN_PKG)
    if FN_SET not in fn_names(ue):
        ue.call(BPT, "add_function_graph", {"blueprint": bp, "graph_name": FN_SET})
    g = Graph(ue, FN_SET)
    entry = g.type("|" + FN_SET)[0]
    if not any(p["name"] == "Level" for p in g.pins(entry, "out")):
        ue.call(BPT, "add_function_param", {"graph": wg(FN_SET), "param_name": "Level", "param_type": "float", "input_param": True})
    if len(g.infos) == 1:
        ue.call(BPT, "write_graph_dsl", {"graph": wg(FN_SET), "code": DSL_SET_SKELETON})
    g = Graph(ue, FN_SET)
    if not g.type("SetScalarParameterValue"):
        setn = new_node(ue, FN_SET, "Rendering|Material|SetScalarParameterValue", 700, 0, "/Script/Engine.MaterialInstanceDynamic")
        g = Graph(ue, FN_SET)
        entry, get, valid = g.type("|" + FN_SET)[0], g.type("|GetMaskGlowMID")[0], g.type("Utilities|IsValid")[0]
        setn = g.by[setn["node"]["refPath"]]
        link(ue, g, valid, "Is Valid", setn, "execute")
        link(ue, g, get, "MaskGlowMID", setn, "self")
        link(ue, g, entry, "Level", setn, "Value")
        set_pin(ue, g, setn, "ParameterName", "TellGlow")
    bad = check_set_mask_glow(ue, Graph(ue, FN_SET))
    print(f"  {FN_SET}:", "ok" if not bad else bad, flush=True)
    return bad


def step_setup_mask_glow(ue):
    if FN_SETUP not in fn_names(ue):
        ue.call(BPT, "add_function_graph", {"blueprint": pkg_ref(WARDEN_PKG), "graph_name": FN_SETUP})
    if len(Graph(ue, FN_SETUP).infos) == 1:
        ue.call(BPT, "write_graph_dsl", {"graph": wg(FN_SETUP), "code": DSL_SETUP})
    bad = check_setup_mask_glow(ue, Graph(ue, FN_SETUP))
    print(f"  {FN_SETUP}:", "ok" if not bad else bad, flush=True)
    return bad


def step_feedback(ue):
    if len(Graph(ue, "PlayStateFeedback").infos) == 1:
        ue.call(BPT, "write_graph_dsl", {"graph": wg("PlayStateFeedback"), "code": DSL_FEEDBACK})
        # the DSL makes the comparison against an integer literal node; put the literal on the byte pin instead (no int-to-byte cast)
        g = Graph(ue, "PlayStateFeedback")
        for op in g.type("Equal(Byte)"):
            src = g.sources(op, "B")
            if src and src[0][0]["type_id"].endswith("MakeLiteralInt"):
                lit = src[0][0]
                value = g.value(lit, "Value")
                ue.call(BPT, "delete_node", {"node": lit["node"]})
                g = Graph(ue, "PlayStateFeedback")
                set_pin(ue, g, g.by[op["node"]["refPath"]], "B", value)
    bad = check_feedback(ue, Graph(ue, "PlayStateFeedback"))
    print("  PlayStateFeedback:", "ok" if not bad else bad, flush=True)
    return bad


def step_show(ue):
    g = Graph(ue, "ShowWindupTell")
    if not g.type("|" + FN_SET):
        vis, timer = g.type("Rendering|SetVisibility")[0], g.type("SetTimerbyFunctionName")[0]
        n = new_node(ue, "ShowWindupTell", "CallFunction|" + FN_SET, 840, 0)
        g = Graph(ue, "ShowWindupTell")
        n = g.by[n["node"]["refPath"]]
        set_pin(ue, g, n, "Level", str(LEVEL_FLARE))
        link(ue, g, g.by[vis["node"]["refPath"]], "then", n, "execute")       # replaces vis -> timer
        link(ue, g, n, "then", g.by[timer["node"]["refPath"]], "execute")
    bad = check_show(ue, Graph(ue, "ShowWindupTell"))
    print("  ShowWindupTell:", "ok" if not bad else bad, flush=True)
    return bad


def step_end(ue):
    g = Graph(ue, "EndWindupTell")
    if not g.type("|" + FN_SET):
        # a half-finished earlier run leaves nodes that were never wired; the original function has only 3 nodes
        for i in g.infos:
            if i["type_id"].endswith(("|GetLastFeedbackState", "Utilities|FlowControl|Branch", "Equal(==)", "Equal(Byte)")):
                ue.call(BPT, "delete_node", {"node": i["node"]})
        g = Graph(ue, "EndWindupTell")
        vis = g.type("Rendering|SetVisibility")[0]
        get = new_node(ue, "EndWindupTell", "Variables|Default|GetLastFeedbackState", 560, 160)
        eq = new_node(ue, "EndWindupTell", "Utilities|Operators|Equal(==)", 840, 160)     # promotable: becomes Byte when A is wired
        br = new_node(ue, "EndWindupTell", "Utilities|FlowControl|Branch", 1040, 0)
        on = new_node(ue, "EndWindupTell", "CallFunction|" + FN_SET, 1300, 0)
        off = new_node(ue, "EndWindupTell", "CallFunction|" + FN_SET, 1300, 160)
        g = Graph(ue, "EndWindupTell")
        get, eq, br, on, off = (g.by[x["node"]["refPath"]] for x in (get, eq, br, on, off))
        link(ue, g, get, "LastFeedbackState", eq, "A")
        g = Graph(ue, "EndWindupTell")
        get, eq, br, on, off = (g.by[x["node"]["refPath"]] for x in (get, eq, br, on, off))
        set_pin(ue, g, eq, "B", str(STATE_CHASE))
        set_pin(ue, g, on, "Level", str(LEVEL_CHASE))
        set_pin(ue, g, off, "Level", str(LEVEL_OFF))
        link(ue, g, g.by[vis["node"]["refPath"]], "then", br, "execute")
        link(ue, g, eq, "ReturnValue", br, "Condition")
        link(ue, g, br, "then", on, "execute")
        link(ue, g, br, "else", off, "execute")
    bad = check_end(ue, Graph(ue, "EndWindupTell"))
    print("  EndWindupTell:", "ok" if not bad else bad, flush=True)
    return bad


def step_begin_play(ue):
    """BeginPlay -> BindtoBrain -> SetupMaskGlow; the AttachTellLightToMask call and function are removed."""
    g = Graph(ue, "EventGraph")
    for c in g.type("|" + FN_ATTACH):
        ue.call(BPT, "delete_node", {"node": c["node"]})
    g = Graph(ue, "EventGraph")
    if not g.type("|" + FN_SETUP):
        begin = g.type("AddEvent|EventBeginPlay")
        if len(begin) != 1:
            return [f"EventGraph has {len(begin)} BeginPlay events"]
        first = [t for t, _ in g.targets(begin[0], "then")]
        if len(first) != 1 or not first[0]["type_id"].endswith("|BindToBrain"):
            return [f"BeginPlay does not lead to BindToBrain as expected: {[f['type_id'] for f in first]}"]
        if g.targets(first[0], "then"):
            return ["BindToBrain already continues somewhere; refusing to splice"]
        n = new_node(ue, "EventGraph", "CallFunction|" + FN_SETUP, 560, 0)
        g = Graph(ue, "EventGraph")
        link(ue, g, g.by[first[0]["node"]["refPath"]], "then", g.by[n["node"]["refPath"]], "execute")
    if FN_ATTACH in fn_names(ue):
        try:
            ue.call(BPT, "remove_function_graph", {"blueprint": pkg_ref(WARDEN_PKG), "graph_name": FN_ATTACH})
        except Exception as e:  # noqa: BLE001
            print(f"  could not delete {FN_ATTACH} ({str(e)[:200]}); it is left in place, uncalled", flush=True)
    gone = FN_ATTACH not in fn_names(ue)
    bad = check_event_graph(ue, Graph(ue, "EventGraph"))
    print(f"  EventGraph (BeginPlay -> BindtoBrain -> {FN_SETUP}); {FN_ATTACH} {'deleted' if gone else 'STILL THERE (uncalled)'}:",
          "ok" if not bad else bad, flush=True)
    return bad


def do_warden(ue):
    # the map must be saved BEFORE the first BP_Warden edit. Once BP_Warden is dirty, the map's dirt comes from these edits (compiling
    # a Blueprint with placed instances dirties the level): it stays unsaved for the rest of the session.
    if ue.call(AS, "is_dirty", {"asset_path": MAP_PKG}) and not ue.call(AS, "is_dirty", {"asset_path": WARDEN_PKG}):
        print("REFUSED: L_Monastery is dirty and BP_Warden is not edited yet. Save the map first (section 6), then start the BP_Warden work.")
        return 1
    bad = step_light(ue) + step_variables(ue)
    for step in (step_set_mask_glow, step_setup_mask_glow, step_feedback, step_show, step_end, step_begin_play):
        bad += step(ue)
    ok = compile_bp(ue, WARDEN_PKG)
    bad += [b + " (after compile)" for b in check_warden_bp(ue, None)]
    print("warden:", "OK" if not bad and ok else f"PROBLEMS {bad}; compile {ok}")
    return 0 if not bad and ok else 1


# ------------------------------------------------------------------ checks (each returns a list of problems; empty = ok)
def _call_levels(g, info):
    """Level values of the SetMaskGlow calls that an exec output feeds."""
    return [float(g.value(t, "Level")) for t, _ in g.targets(info, "then")]


def check_set_mask_glow(ue, g):
    bad = []
    entry, setn = g.type("|" + FN_SET), g.type("SetScalarParameterValue")
    valid, get = g.type("Utilities|IsValid"), g.type("|GetMaskGlowMID")
    if len(entry) != 1 or len(setn) != 1 or len(valid) != 1 or len(get) != 1 or len(g.infos) != 4:
        return [f"{FN_SET}: expected entry, IsValid, GetMaskGlowMID and one SetScalarParameterValue (4 nodes), got {[i['type_id'] for i in g.infos]}"]
    entry, setn, valid, get = entry[0], setn[0], valid[0], get[0]
    if [s[0]["type_id"] for s in g.sources(valid, "exec")] != [entry["type_id"]]:
        bad.append("IsValid is not driven by the function entry")
    if [t[0]["node"]["refPath"] for t in g.targets(valid, "Is Valid")] != [setn["node"]["refPath"]] or g.targets(valid, "Is Not Valid"):
        bad.append("Is Valid must lead to the set node, Is Not Valid to nothing")
    if [s[0]["type_id"] for s in g.sources(valid, "InputObject")] != [get["type_id"]] or [s[0]["type_id"] for s in g.sources(setn, "self")] != [get["type_id"]]:
        bad.append("MaskGlowMID must feed IsValid and the set node's self")
    if [s[1] for s in g.sources(setn, "Value")] != ["Level"]:
        bad.append("Level must feed Value")
    if g.value(setn, "ParameterName") != "TellGlow":
        bad.append(f"ParameterName is {g.value(setn, 'ParameterName')!r}, expected 'TellGlow'")
    if "Material Instance Dynamic" not in g.pin(setn, "self", "in")["type_id"]:
        bad.append("the set node is not the dynamic material instance's")
    return bad


def check_setup_mask_glow(ue, g):
    bad = []
    want = ["|" + FN_SETUP, "|GetMesh", "GetMaterialIndex", "CreateDynamicMaterialInstance", "|SetMaskGlowMID"]
    for w in want:
        if len(g.type(w)) != 1:
            bad.append(f"{FN_SETUP}: expected one {w}, got {len(g.type(w))}")
    if bad:
        return bad
    idx, cdm, setv = g.type("GetMaterialIndex")[0], g.type("CreateDynamicMaterialInstance")[0], g.type("|SetMaskGlowMID")[0]
    if g.value(idx, "MaterialSlotName") != SLOT_NAME:
        bad.append(f"slot name is {g.value(idx, 'MaterialSlotName')!r}, expected {SLOT_NAME!r}")
    if [s[0]["type_id"] for s in g.sources(cdm, "ElementIndex")] != [idx["type_id"]]:
        bad.append("the slot index must come from GetMaterialIndex")
    if [s[0]["type_id"] for s in g.sources(setv, "MaskGlowMID")] != [cdm["type_id"]]:
        bad.append("MaskGlowMID must be set from CreateDynamicMaterialInstance")
    if len(g.type("Utilities|FlowControl|Branch")) != 1 or not [i for i in g.infos if "integer>=integer" in i["type_id"]]:
        bad.append("the index >= 0 guard is missing")
    return bad


def check_feedback(ue, g):
    """PlayStateFeedback after P13-7: entry -> UpdateAnimState(NewState) -> SetLastFeedbackState(NewState) -> the unchanged glow logic."""
    entry, sets, calls = g.type("|PlayStateFeedback"), g.type("|SetLastFeedbackState"), g.type("|" + FN_SET)
    upd = g.type("|UpdateAnimState")
    ne = g.type("NotEqual(Byte)")
    eq = [i for i in g.type("Equal(Byte)") if not i["type_id"].endswith("NotEqual(Byte)")]
    brs = g.type("Utilities|FlowControl|Branch")
    if not (len(entry) == 1 and len(sets) == 1 and len(calls) == 2 and len(eq) == 1 and len(ne) == 1 and len(brs) == 2 and len(upd) == 1 and len(g.infos) == 9):
        return [f"PlayStateFeedback: unexpected nodes (9 expected: the 8 of fix set 1 plus the UpdateAnimState call): {[i['type_id'] for i in g.infos]}"]
    bad = []
    entry, st, eq, ne, upd = entry[0], sets[0], eq[0], ne[0], upd[0]
    if [t[0]["node"]["refPath"] for t in g.targets(entry, "then")] != [upd["node"]["refPath"]] or [s[1] for s in g.sources(upd, "NewState")] != ["NewState"]:
        return ["entry -> UpdateAnimState(NewState) is not wired"]
    if [t[0]["node"]["refPath"] for t in g.targets(upd, "then")] != [st["node"]["refPath"]] or [s[1] for s in g.sources(st, "LastFeedbackState")] != ["NewState"]:
        return ["UpdateAnimState -> SetLastFeedbackState(NewState) is not wired"]
    nxt = [t for t, _ in g.targets(st, "then")]
    if len(nxt) != 1:
        return bad + ["SetLastFeedbackState must lead to the Chase branch"]
    b0 = nxt[0]
    if g.value(eq, "B") != str(STATE_CHASE) or [s[1] for s in g.sources(eq, "A")] != ["NewState"] or [t[0]["node"]["refPath"] for t in g.targets(eq, "ReturnValue")] != [b0["node"]["refPath"]]:
        bad.append(f"first branch must test NewState == {STATE_CHASE} (Chase)")
    if _call_levels(g, b0) != [LEVEL_CHASE]:
        bad.append(f"Chase: expected SetMaskGlow({LEVEL_CHASE}), got {_call_levels(g, b0)}")
    els = [t for t, _ in g.targets(b0, "else")]
    if len(els) != 1 or not els[0]["type_id"].endswith("Branch"):
        return bad + ["else of the Chase branch is not the second branch"]
    b1 = els[0]
    if g.value(ne, "B") != str(STATE_ATTACK) or [s[1] for s in g.sources(ne, "A")] != ["NewState"] or [t[0]["node"]["refPath"] for t in g.targets(ne, "ReturnValue")] != [b1["node"]["refPath"]]:
        bad.append(f"second branch must test NewState != {STATE_ATTACK} (Attack)")
    if _call_levels(g, b1) != [LEVEL_OFF]:
        bad.append(f"other states: expected SetMaskGlow({LEVEL_OFF}), got {_call_levels(g, b1)}")
    if g.targets(b1, "else"):
        bad.append("Attack must do nothing (else of the second branch must be empty)")
    return bad


def check_show(ue, g):
    """ShowWindupTell after P13-7: SetVisibility(true) -> SetMaskGlow(1) -> PlayAttackAnim -> the EndWindupTell timer."""
    vis, calls, timer, play = g.type("Rendering|SetVisibility"), g.type("|" + FN_SET), g.type("SetTimerbyFunctionName"), g.type("|PlayAttackAnim")
    if len(vis) != 1 or len(calls) != 1 or len(timer) != 1 or len(play) != 1 or len(g.infos) != 7:
        return [f"ShowWindupTell: unexpected nodes (7 expected: the 6 of fix set 1 plus the PlayAttackAnim call): {[i['type_id'] for i in g.infos]}"]
    vis, call, timer, play = vis[0], calls[0], timer[0], play[0]
    bad = []
    if g.value(vis, "bNewVisibility") != "true":
        bad.append("the light must be shown (bNewVisibility true)")
    if [t[0]["node"]["refPath"] for t in g.targets(vis, "then")] != [call["node"]["refPath"]]:
        bad.append("SetVisibility must lead to SetMaskGlow")
    if [t[0]["node"]["refPath"] for t in g.targets(call, "then")] != [play["node"]["refPath"]]:
        bad.append("SetMaskGlow must lead to PlayAttackAnim")
    if [t[0]["node"]["refPath"] for t in g.targets(play, "then")] != [timer["node"]["refPath"]]:
        bad.append("PlayAttackAnim must lead to the EndWindupTell timer")
    if float(g.value(call, "Level")) != LEVEL_FLARE:
        bad.append(f"flare level is {g.value(call, 'Level')}, expected {LEVEL_FLARE}")
    if g.value(timer, "FunctionName") != "EndWindupTell":
        bad.append("the timer must call EndWindupTell")
    return bad


def check_end(ue, g):
    vis, calls = g.type("Rendering|SetVisibility"), g.type("|" + FN_SET)
    br, eq, get = g.type("Utilities|FlowControl|Branch"), g.type("Equal(Byte)"), g.type("|GetLastFeedbackState")
    if not (len(vis) == 1 and len(calls) == 2 and len(br) == 1 and len(eq) == 1 and len(get) == 1 and len(g.infos) == 8):
        return [f"EndWindupTell: unexpected nodes (8 expected): {[i['type_id'] for i in g.infos]}"]
    vis, br, eq = vis[0], br[0], eq[0]
    bad = []
    if g.value(vis, "bNewVisibility") != "false":
        bad.append("the light must be hidden (bNewVisibility false)")
    if [t[0]["node"]["refPath"] for t in g.targets(vis, "then")] != [br["node"]["refPath"]]:
        bad.append("SetVisibility must lead to the branch")
    if [s[0]["type_id"] for s in g.sources(eq, "A")] != [get[0]["type_id"]] or g.value(eq, "B") != str(STATE_CHASE):
        bad.append(f"the branch must test LastFeedbackState == {STATE_CHASE} (Chase)")
    if [t[0]["node"]["refPath"] for t in g.targets(eq, "ReturnValue")] != [br["node"]["refPath"]]:
        bad.append("the comparison must drive the branch")
    if _call_levels(g, br) != [LEVEL_CHASE]:
        bad.append(f"Chase: expected SetMaskGlow({LEVEL_CHASE}) after the windup")
    els = [float(g.value(t, "Level")) for t, _ in g.targets(br, "else")]
    if els != [LEVEL_OFF]:
        bad.append(f"otherwise: expected SetMaskGlow({LEVEL_OFF}), got {els}")
    return bad


EVENTS = sorted(["AddEvent|Custom|BindToBrain", "AddEvent|Custom|OnStateChanged_Event", "AddEvent|Custom|OnAttackWindup_Event",
                 "AddEvent|Custom|OnPlayerCaught_Event", "AddEvent|EventBeginPlay", "AddEvent|EventPossessed", "AddEvent|EventEndPlay"])


def _paths(items):
    return [t[0]["node"]["refPath"] for t in items]


def check_event_graph(ue, g):
    """EventGraph after P13-7 (35 nodes): the 29 of fix set 1 plus the StartSearchPauseTimer call, the OnPlayerCaught event, its Assign node and
    its HandlePlayerCaught call, and the matching Unbind node with its Create Event."""
    bad = []
    events = sorted(i["type_id"] for i in g.infos if i["type_id"].startswith("AddEvent|"))
    if events != EVENTS:
        bad.append(f"events {events}")
    if g.type("|" + FN_ATTACH):
        bad.append(f"{FN_ATTACH} is still called")
    setups = g.type("|" + FN_SETUP)
    if len(setups) != 1:
        return bad + [f"{len(setups)} calls of {FN_SETUP}"]
    prev = [s[0] for s in g.sources(setups[0], "execute")]
    chain = False
    if len(prev) == 1 and prev[0]["type_id"].endswith("|BindToBrain"):
        prev2 = [s[0] for s in g.sources(prev[0], "execute")]
        chain = len(prev2) == 1 and prev2[0]["type_id"] == "AddEvent|EventBeginPlay"
    if not chain:
        bad.append(f"BeginPlay -> BindtoBrain -> {FN_SETUP} chain is wrong")
    timers = g.type("|StartSearchPauseTimer")
    if len(timers) != 1 or [t["node"]["refPath"] for t, _ in g.targets(setups[0], "then")] != [timers[0]["node"]["refPath"]] or g.targets(timers[0], "then"):
        bad.append(f"{FN_SETUP} must lead to the one StartSearchPauseTimer call, which ends the BeginPlay chain")
    ev, asg, hand = g.type("AddEvent|Custom|OnPlayerCaught_Event"), g.type("|AssignOnPlayerCaught"), g.type("|HandlePlayerCaught")
    if len(ev) == 1 and len(asg) == 1 and len(hand) == 1:
        ev, asg, hand = ev[0], asg[0], hand[0]
        if [t["node"]["refPath"] for t, _ in g.targets(ev, "OutputDelegate")] != [asg["node"]["refPath"]] or [t["node"]["refPath"] for t, _ in g.targets(ev, "then")] != [hand["node"]["refPath"]]:
            bad.append("OnPlayerCaught_Event must feed the Assign node's Delegate and lead to HandlePlayerCaught")
        if g.targets(hand, "then"):
            bad.append("HandlePlayerCaught must end the handler")
        src = [s[0] for s in g.sources(asg, "self")]
        if len(src) != 1 or not src[0]["type_id"].endswith("GetBrain"):
            bad.append("AssignOnPlayerCaught self must be the brain")
        att, setb = g.type("|AssignOnAttackWindup"), [i for i in g.type("|SetbBrainBound") if g.value(i, "bBrainBound") == "true"]
        if len(att) != 1 or len(setb) != 1 or [t["node"]["refPath"] for t, _ in g.targets(att[0], "then")] != [asg["node"]["refPath"]] \
                or [t["node"]["refPath"] for t, _ in g.targets(asg, "then")] != [setb[0]["node"]["refPath"]]:
            bad.append("bind chain must be AssignOnStateChanged -> AssignOnAttackWindup -> AssignOnPlayerCaught -> SetbBrainBound")
    else:
        bad.append(f"expected one OnPlayerCaught_Event, AssignOnPlayerCaught and HandlePlayerCaught, got {len(ev)}/{len(asg)}/{len(hand)}")
    unb, unb_att = g.type("|UnbindEventfromOnPlayerCaught"), g.type("|UnbindEventfromOnAttackWindup")
    if len(unb) == 1 and len(unb_att) == 1:
        if [t["node"]["refPath"] for t, _ in g.targets(unb_att[0], "then")] != [unb[0]["node"]["refPath"]] or g.targets(unb[0], "then"):
            bad.append("EndPlay must unbind OnAttackWindup then OnPlayerCaught, and end there")
        ce = [s[0] for s in g.sources(unb[0], "Delegate")]
        fn = ue.call(BPT, "get_create_event_function", {"node": ce[0]["node"]}) if len(ce) == 1 else None
        if fn != "OnPlayerCaught_Event":
            bad.append(f"the unbind's Create Event is bound to {fn!r}, expected 'OnPlayerCaught_Event'")
    else:
        bad.append("expected one UnbindEventfromOnPlayerCaught after the OnAttackWindup unbind")
    if len(g.type("|GetbBrainBound")) + len(g.type("|SetbBrainBound")) < 2 or len(g.infos) != 35:
        bad.append(f"bBrainBound logic / node count: {len(g.infos)} nodes (35 expected: the original 28, the {FN_SETUP} call, the search timer call, and 5 for OnPlayerCaught)")
    return bad


def check_tell_light(ue, snap):
    """TellLight template: the three new values, everything else equal to the P12-8 snapshot; the parent is PlaceholderBody."""
    bad = []
    cur = {k: get1(ue, TELL, k) for k in snap["templates"]["TellLight"]}
    for k, v in snap["templates"]["TellLight"].items():
        if k in TELL_VALUES:
            if not same(TELL_VALUES[k], cur[k]):
                bad.append(f"{k}: wanted {TELL_VALUES[k]}, read {cur[k]}")
        elif cur[k] != v:
            bad.append(f"{k} changed: snapshot {v}, now {cur[k]}")
    parent = ue.call(AC, "get_parent_component", {"component": rp(TELL)})
    pname = parent["refPath"].split(":")[-1] if isinstance(parent, dict) else str(parent)
    if pname != "PlaceholderBody_GEN_VARIABLE" and pname != "PlaceholderBody":
        bad.append(f"parent is {pname}, expected PlaceholderBody")
    else:
        pb = WARDEN_PKG + ".BP_Warden_C:PlaceholderBody_GEN_VARIABLE"
        ploc, prot, psc = get1(ue, pb, "relativeLocation"), get1(ue, pb, "relativeRotation"), get1(ue, pb, "relativeScale3D")
        loc = get1(ue, TELL, "relativeLocation")
        trivial = all(abs(prot[k]) < 1e-6 for k in prot) and all(abs(psc[k] - 1) < 1e-6 for k in psc)
        off = (ploc["x"] + loc["x"], ploc["y"] + loc["y"], ploc["z"] + loc["z"])
        if not trivial or any(abs(a - b) > 1e-3 for a, b in zip(off, TELL_WORLD_OFFSET)):
            bad.append(f"offset from the actor root is {off} (parent rotation/scale trivial: {trivial}), expected {TELL_WORLD_OFFSET}")
    return bad


def check_warden_bp(ue, res, snap_path=None):
    """Everything section 7 changes. With res: one PASS/FAIL line per group; without: returns the problems only."""
    snap_path = snap_path or os.path.join(r"C:\Hemant\Prj\Learning\TheLastBell", "Docs", "ArtTest", "warden", "p12_8_before.json")
    with open(snap_path, encoding="utf-8") as f:
        snap = json.load(f)
    groups = [
        ("BP_Warden TellLight: (110, 0, 235) under PlaceholderBody = actor + (110, 0, 125), radius 700, intensity 5000, all else as the snapshot",
         lambda: check_tell_light(ue, snap)),
        ("BP_Warden variables MaskGlowMID and LastFeedbackState exist",
         lambda: [v for v in ("MaskGlowMID", "LastFeedbackState") if v not in ue.call(BPT, "list_variables", {"blueprint": pkg_ref(WARDEN_PKG)})]),
        (f"BP_Warden {FN_SET}: valid MaskGlowMID -> SetScalarParameterValue(TellGlow, Level)", lambda: check_set_mask_glow(ue, Graph(ue, FN_SET))),
        (f"BP_Warden {FN_SETUP}: slot {SLOT_NAME} by name -> dynamic instance -> MaskGlowMID", lambda: check_setup_mask_glow(ue, Graph(ue, FN_SETUP))),
        ("BP_Warden PlayStateFeedback: UpdateAnimState(NewState), then store state; Chase 0.25; Attack nothing; other 0", lambda: check_feedback(ue, Graph(ue, "PlayStateFeedback"))),
        ("BP_Warden ShowWindupTell: light on, glow 1, PlayAttackAnim, then the EndWindupTell timer", lambda: check_show(ue, Graph(ue, "ShowWindupTell"))),
        ("BP_Warden EndWindupTell: light off, glow 0.25 if the last state was Chase, else 0", lambda: check_end(ue, Graph(ue, "EndWindupTell"))),
        (f"BP_Warden EventGraph: BeginPlay -> BindtoBrain -> {FN_SETUP} -> search timer; OnPlayerCaught bound and unbound; no {FN_ATTACH} call; the 7 events once each; 35 nodes",
         lambda: check_event_graph(ue, Graph(ue, "EventGraph"))),
    ]
    allbad = []
    for name, fn in groups:
        try:
            bad = fn()
        except Exception as e:  # noqa: BLE001
            bad = [f"could not be read: {type(e).__name__}: {str(e)[:200]}"]
        allbad += bad
        if res is not None:
            res.check(not bad, name, "; ".join(bad))
    if res is not None:
        still = FN_ATTACH in fn_names(ue)
        print(f"INFO  {FN_ATTACH} function {'is STILL in BP_Warden (uncalled)' if still else 'is deleted'}")
    return allbad


# ------------------------------------------------------------------ checks: the Blueprint and the placed actors (read-only)
def check_apparition_bp(ue, res):
    parent = ue.call(BPT, "get_parent", {"blueprint": pkg_ref(APP_PKG)})
    pp = parent.get("refPath", "") if isinstance(parent, dict) else str(parent)
    res.check(pp.endswith("LBWardenApparition"), "BP_WardenApparition parent is LBWardenApparition", f"got {pp}")
    for comp, vals in (("Body", BODY_VALUES), ("Glow", GLOW_VALUES)):
        bad = []
        for k, want in vals.items():
            got = get1(ue, APP_CDO + ":" + comp, k)
            if not same(want, got):
                bad.append(f"{k}: wanted {want}, read {got}")
        res.check(not bad, f"BP_WardenApparition {comp}: " + ", ".join(f"{k}" for k in vals), "; ".join(bad))
    body_mats = get1(ue, APP_CDO + ":Body", "overrideMaterials")
    res.check(body_mats == [], "BP_WardenApparition Body keeps the mesh's default MIs (no material overrides)", f"got {body_mats}")
    sm = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
    slots = {s: short(ue.call(sm, "get_material", {"mesh": pkg_ref(MESH_APP), "slot_name": s})) for s in ue.call(sm, "get_material_slots", {"mesh": pkg_ref(MESH_APP)})}
    res.check(slots == {"MAT_Body": "MI_Warden_Apparition_Body", "MAT_Mask": "MI_Warden_Apparition_Mask"},
              "SM_LB_Warden_Apparition default slots: MAT_Body, MAT_Mask -> the two apparition MIs", f"got {slots}")
    res.check(is_dirty(ue, APP_PKG) is False, "BP_WardenApparition is saved (not dirty)")


def check_placed(ue, res):
    n = count_actors(ue)
    res.check(n == ACTORS_NOW, f"L_Monastery actor count == {ACTORS_NOW} (2980 + the 12 stoop zones)", f"got {n}")
    in_folder = [a["refPath"] if isinstance(a, dict) else a for a in ue.call(SC, "get_actors_in_folder", {"folder_path": FOLDER})]
    for label, spec in INSTANCES.items():
        found = find_new(ue, label)
        res.check(len(found) == 1, f"{label}: one actor with this label", f"got {found}")
        if len(found) != 1:
            continue
        path = found[0]
        bad = []
        want_loc = spec["stations"][0]["location"]
        t = ue.call(AC, "get_actor_transform", {"actor": rp(path), "worldspace": True})
        if not same({"location": want_loc, "rotation": {"pitch": 0, "yaw": 0, "roll": 0}, "scale": {"x": 1, "y": 1, "z": 1}}, t):
            bad.append(f"transform {t}")
        for k, want in instance_values(spec).items():
            if not same(want, get1(ue, path, k)):
                bad.append(f"{k}: wanted {want}, read {get1(ue, path, k)}")
        got_st = get1(ue, path, "Stations")
        if not same(spec["stations"], got_st):
            bad.append(f"Stations: wanted {spec['stations']}, read {got_st}")
        for comp, vals in (("Body", BODY_VALUES), ("Glow", GLOW_VALUES)):
            for k, want in vals.items():
                got = get1(ue, path + "." + comp, k)
                if not same(want, got):
                    bad.append(f"{comp}.{k}: wanted {want}, read {got}")
        if path not in in_folder:
            bad.append(f"not in the Outliner folder {FOLDER}")
        st = [(s["location"]["x"], s["location"]["y"], s["location"]["z"]) for s in spec["stations"]]
        res.check(not bad, f"{label}: tag {spec['tag']}, arm {spec['arm']} s, glow {spec['glow']:g}, {len(spec['stations'])} station(s) {st}, Body/Glow as the template, folder {FOLDER}",
                  "; ".join(bad))
    # no BP_WardenSilhouette placed any more (find_actors matches labels, so scan the object names and the old labels)
    left = []
    for i in range(0, 16):
        try:
            left.append((f"BP_WardenSilhouette_C_{i}", ue.call(AC, "get_label", {"actor": rp(inst(f"BP_WardenSilhouette_C_{i}"))})))
        except Exception:  # noqa: BLE001
            pass
    for a in ue.call(SC, "find_actors", {"name": "Silh_", "tag": "", "collision_channels": []}):
        left.append(("label Silh_", a))
    res.check(not left, "no BP_WardenSilhouette is placed in L_Monastery", f"found {left}")


def do_check(ue):
    sys.path.insert(0, HERE_WARDEN)
    import check_warden  # noqa: E402
    res = check_warden.Result()
    check_apparition_bp(ue, res)
    check_placed(ue, res)
    check_warden_bp(ue, res)
    print("%d/%d" % (res.passed, res.total))
    return 0 if res.passed == res.total else 1


HERE_WARDEN = os.path.dirname(os.path.abspath(__file__))


# ------------------------------------------------------------------ save (one package per call, explicit)
SAVE_PKGS = {"apparition": APP_PKG, "map": MAP_PKG, "warden": WARDEN_PKG}
# never saved by this script, whatever happens (the task's list); their dirty state is only reported
WATCH = ["/Game/LastBell/Blueprints/Interactables/BP_SmallBell", "/Game/LastBell/Blueprints/Interactables/BP_SequencePuzzle",
         "/Game/LastBell/Blueprints/Interactables/BP_Inscription", "/Game/LastBell/Blueprints/Interactables/BP_RitualMechanism",
         "/Game/LastBell/Blueprints/Interactables/BP_Door_Base", "/Game/LastBell/Blueprints/Interactables/BP_TagInteractable",
         "/Game/LastBell/Blueprints/Interactables/BP_TagTrigger",
         "/Game/LastBell/Blueprints/Interactables/BP_Inspectable_Note", "/Game/LastBell/Blueprints/Interactables/BP_Door_Base_Dungeon",
         "/Game/LastBell/Blueprints/Interactables/BP_RitualMechanism_CryptWinch", "/Game/LastBell/Materials/Master/M_LB_Surface",
         "/Game/LastBell/Characters/Warden/Meshes/SM_LB_Warden_Silhouette", "/Game/LastBell/Data/DA_WardenTuning"]


def do_save(ue, name):
    pkg = SAVE_PKGS[name]
    before = is_dirty(ue, pkg)
    res = ue.call(AS, "save_assets", {"asset_paths": [pkg]})
    after = is_dirty(ue, pkg)
    print(f"  save {pkg.split('/')[-1]}: was dirty {before}, returned {res}, is_dirty now {after}")
    print("  dirty and NOT saved on purpose:", sorted(p.split("/")[-1] for p in WATCH if is_dirty(ue, p)) or "none")
    return 0 if res is True and after is False else 1


# ------------------------------------------------------------------ MAIN
MODES = {"apparition": do_apparition, "map": do_map, "warden": do_warden, "check": do_check}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    for m in ("apparition", "map", "warden", "check"):
        g.add_argument("--" + m, action="store_true")
    g.add_argument("--save", metavar="NAME", choices=["apparition", "map", "warden"])
    a = ap.parse_args()
    ue = UE()
    try:
        if not preflight(ue):
            return 1
        if a.save:
            return do_save(ue, a.save)
        for m in ("apparition", "map", "warden", "check"):
            if getattr(a, m):
                return MODES[m](ue)
    except Exception as e:  # noqa: BLE001
        print(f"TOOL CALL FAILED: {str(e)[:700]}\nState unknown. Run --check before anything else; do not retry in a loop.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
