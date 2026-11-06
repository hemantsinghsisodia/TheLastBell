"""P13-7: hook the animated Warden up (Docs/plans/P13_WARDEN_ANIMATION.md, sections 7 and 11).

Run with -I, editor open on L_Monastery, no PIE. Exactly one mode per run. Every step is idempotent and reads each value back.
The order matters, because placed instances keep stale template values until a map reload:

    --preflight     PIE off, L_Monastery loaded and clean, 2980 actors; reports what is dirty. Changes nothing.
    --material      M_Warden_Apparition: bUsedWithSkeletalMesh on, recompile, shader log check. (M_LB_Surface is never touched.)
    --apparition    BP_WardenApparition class default `Figure`: SK_Warden, Animation Blueprint ABP_Warden_C, the slot-matched override
                    materials, NoCollision, no shadow, hidden. Compile with warnings as errors.
    --map           L_Monastery: Apparition_Chapel (skeletal figure, one station, WalkPath, WalkSpeed, the Figure values written on the
                    instance too), Apparition_Courtyard read back, the 12 ALBWardenStoopZone actors (section 7's F0 table). 2980 -> 2992.
    --warden        BP_Warden (after the map save): CharacterMesh0 anim mode / class / tick option / update-rate optimisation, ShowWindupTell
                    -> PlayAttack, BindtoBrain -> OnPlayerCaught handler, PlayStateFeedback (Dormant -> StopAllMontages, bInSearch),
                    CheckSearchPause on a looping 0.25 s timer from BeginPlay. Compile with warnings as errors.
    --check         read everything back (read-only)
    --save NAME     one package per call: material | apparition | map | warden. Never anything else.

Order of the whole task: --preflight, --material, --save material, --apparition, --save apparition, --map, --save map (once, never
again), then --warden, --save warden.
Exit codes: 0 ok, 1 mismatch or refused, 2 a tool call failed (state unknown: run --check first, never retry in a loop).
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
sys.path.insert(0, HERE)
from ue import UE  # noqa: E402
import apply_p12f_blueprints as apf  # noqa: E402  (helpers: put, get1, same, Graph, new_node, link, set_pin, find_new, ...)
from apply_p12f_blueprints import (  # noqa: E402
    OB, AS, SC, AC, BPT, APP, MAP_PKG, WARDEN_PKG, APP_PKG, APP_CDO, rp, pkg_ref, same, get1, set_props, put, is_dirty, count_actors,
    find_new, compile_bp, inst, Graph, new_node, link, set_pin, fn_names, wg, close)

MT = "editor_toolset.toolsets.material.MaterialTools"
LG = "EditorToolset.LogsToolset"
SK = "editor_toolset.toolsets.skeletal_mesh.SkeletalMeshTools"

CH = "/Game/LastBell/Characters/Warden"
MESH_PKG = CH + "/Meshes/SK_Warden"
ABP_CLASS = CH + "/ABP_Warden.ABP_Warden_C"
MAT_PKG = CH + "/Materials/M_Warden_Apparition"
MI_BODY = CH + "/Materials/MI_Warden_Apparition_Body"
MI_MASK = CH + "/Materials/MI_Warden_Apparition_Mask"
BELL_SLOT = "M_Warden_BellMetal"
SURFACE_PKG = "/Game/LastBell/Materials/Master/M_LB_Surface"
EXPECTED_BEFORE = 2980
STOOP_COUNT = 12
EXPECTED_AFTER = EXPECTED_BEFORE + STOOP_COUNT
STOOP_FOLDER = "Gameplay/Warden/StoopZones"
STOOP_CLASS = "/Script/LastBell.LBWardenStoopZone"


def V(x, y, z):
    return {"x": x, "y": y, "z": z}


# ------------------------------------------------------------------ preflight
def do_preflight(ue):
    n = count_actors(ue)
    dirty = {p.split("/")[-1]: is_dirty(ue, p) for p in (
        MAP_PKG, "/Game/LastBell/Maps/L_Test_Warden", WARDEN_PKG, APP_PKG, MAT_PKG, SURFACE_PKG, CH + "/ABP_Warden", CH + "/ABP_P13_Spike",
        CH + "/Meshes/SK_Warden_PhysicsAsset", CH + "/Meshes/SK_Warden", "/Game/LastBell/Data/DA_WardenTuning", "/Game/LastBell/Data/DA_WardenAnimSet")}
    print("  actors:", n, "| dirty:", sorted(k for k, v in dirty.items() if v), "| clean:", sorted(k for k, v in dirty.items() if v is False))
    ok = n == EXPECTED_BEFORE and dirty["L_Monastery"] is False
    print("preflight:", "OK (PIE off, L_Monastery clean, %d actors)" % n if ok else "NOT OK")
    return 0 if ok else 1


# ------------------------------------------------------------------ M_Warden_Apparition
def shader_errors(ue):
    """Log lines about this material or shader failures (an empty list is good)."""
    r = ue.call(LG, "GetLogEntries", {"category": "", "pattern": r"(?i)(M_Warden_Apparition.*(error|fail))|((error|fail).*M_Warden_Apparition)|(\[Compiler\].*error)|Shader.*(error|failed)", "maxEntries": 40})
    return r if isinstance(r, list) else ([r] if r else [])


def do_material(ue):
    m = pkg_ref(MAT_PKG)
    bad = put(ue, MAT_PKG + "." + MAT_PKG.split("/")[-1], {"bUsedWithSkeletalMesh": True}, "M_Warden_Apparition")
    try:
        ue.call(MT, "recompile", {"material_or_function": m})
        print("  recompile: ok (the tool raises on a shader failure)", flush=True)
    except Exception as e:  # noqa: BLE001
        print("  recompile FAILED:", str(e)[:600])
        return 1
    flag = get1(ue, MAT_PKG + "." + MAT_PKG.split("/")[-1], "bUsedWithSkeletalMesh")
    errs = shader_errors(ue)
    print("  flag after recompile:", flag, "| shader error lines in the log:", errs if errs else "none")
    print("  M_LB_Surface dirty (must stay False):", is_dirty(ue, SURFACE_PKG))
    ok = not bad and flag is True and not errs and is_dirty(ue, SURFACE_PKG) is False
    print("material:", "OK" if ok else f"PROBLEMS {bad} {errs}")
    return 0 if ok else 1


# ------------------------------------------------------------------ BP_WardenApparition Figure
def figure_values(ue):
    slots = ue.call(SK, "get_material_slots", {"mesh": pkg_ref(MESH_PKG)})
    mats = [pkg_ref(MI_MASK if s == BELL_SLOT else MI_BODY) for s in slots]       # matched by slot name, never by index
    return slots, {"skeletalMeshAsset": pkg_ref(MESH_PKG), "animationMode": "AnimationBlueprint", "animClass": rp(ABP_CLASS),
                   "overrideMaterials": mats, "bVisible": False, "castShadow": False}


def figure_extra(ue, path):
    """collision, read back: profile and enabled must both be NoCollision."""
    bi = get1(ue, path, "bodyInstance")
    return [] if isinstance(bi, dict) and bi.get("collisionProfileName") == "NoCollision" and bi.get("collisionEnabled") == "NoCollision" \
        else [f"collision {bi.get('collisionProfileName') if isinstance(bi, dict) else bi}"]


def write_figure(ue, path, label):
    """Mesh first (it sizes the slot list), then the animation, then the materials in a second call."""
    slots, vals = figure_values(ue)
    bad = []
    first = {k: vals[k] for k in ("skeletalMeshAsset", "animationMode", "animClass", "bVisible", "castShadow")}
    bad += put(ue, path, first, label)
    bad += put(ue, path, {"overrideMaterials": vals["overrideMaterials"]}, label)
    bad += figure_extra(ue, path)
    return bad


def do_apparition(ue):
    bad = write_figure(ue, APP_CDO + ":Figure", "Figure")
    ok = compile_bp(ue, APP_PKG)
    slots, vals = figure_values(ue)
    for k, want in vals.items():                            # compiling can reset what was written
        got = get1(ue, APP_CDO + ":Figure", k)
        if not same(want, got):
            bad.append(f"Figure.{k} after compile: wanted {want}, read {got}")
    bad += figure_extra(ue, APP_CDO + ":Figure")
    print("  slots:", slots)
    print("apparition:", "OK" if not bad and ok else f"PROBLEMS {bad}; compile {ok}")
    return 0 if not bad and ok else 1


# ------------------------------------------------------------------ the map
CHAPEL = "Apparition_Chapel"
COURTYARD = "Apparition_Courtyard"
CHAPEL_STATION = {"location": V(8380, -120, 0), "lookConeDegrees": 30, "minPlayerDistance": 150, "fadeInSeconds": 1.0, "holdSeconds": 2.5,
                  "fadeOutSeconds": 1.5, "gapAfterSeconds": 0,
                  "walkPath": [V(8380, -380, 0), V(8500, -650, 0), V(8500, -1000, 0), V(8250, -1100, 0)], "walkSpeed": 110}

# section 7, F0 table: (label, centre, half-extents, StoopAmount). World-aligned, rotation 0.
STOOP_ZONES = [
    ("SZ_Door_Sacristy", V(8020, -1100, 150), V(150, 100, 150), 1.0),
    ("SZ_Door_ChapelMain", V(6020, 0, 150), V(150, 100, 150), 1.0),
    ("SZ_Door_Shortcut", V(6020, 2000, 150), V(150, 100, 150), 1.0),
    ("SZ_Door_Tower", V(12020, 2009, 150), V(150, 100, 150), 1.0),
    ("SZ_Cell_N9900", V(9900, 3000, 150), V(100, 150, 150), 1.0),
    ("SZ_Cell_N10500", V(10500, 3000, 150), V(100, 150, 150), 1.0),
    ("SZ_Cell_N11100", V(11100, 3000, 150), V(100, 150, 150), 1.0),
    ("SZ_Cell_W900", V(9500, 900, 150), V(150, 100, 150), 1.0),
    ("SZ_Cell_W2700", V(9500, 2700, 150), V(150, 100, 150), 1.0),
    ("SZ_Stair_Sacristy", V(7290, -1100, -285), V(140, 150, 185), 0.7),
    ("SZ_Stair_Exit", V(10650, -170, -290), V(150, 150, 190), 0.7),
    ("SZ_Chapel_SacristyDoorway", V(8500, -780, 150), V(80, 150, 150), 0.6),
]
ZERO_ROT = {"pitch": 0, "yaw": 0, "roll": 0}
ONE = V(1, 1, 1)


def chapel_path(ue):
    found = find_new(ue, CHAPEL)
    return found[0] if len(found) == 1 else None


def set_chapel(ue, path):
    """bUseSkeletalFigure, the Figure values, and the one station with its WalkPath. Arrays are grown in a call of their own."""
    bad = put(ue, path, {"bUseSkeletalFigure": True}, CHAPEL)
    bad += write_figure(ue, path + ".Figure", CHAPEL + ".Figure")
    # one station: shrink / grow first (empty element), then its walk path grown (empty points), then every value
    cur = get1(ue, path, "Stations")
    if isinstance(cur, list) and len(cur) > 1:
        set_props(ue, path, {"Stations": cur[:1]})      # shrink with the first element unchanged (a changed element is refused)
    elif not isinstance(cur, list) or len(cur) < 1:
        set_props(ue, path, {"Stations": [{}]})
    cur = get1(ue, path, "Stations")
    n = len(cur[0].get("walkPath", [])) if isinstance(cur, list) and cur and isinstance(cur[0], dict) else 0
    if n != len(CHAPEL_STATION["walkPath"]):
        set_props(ue, path, {"Stations": [{"walkPath": [V(0, 0, 0) for _ in CHAPEL_STATION["walkPath"]]}]})
    bad += put(ue, path, {"Stations": [CHAPEL_STATION]}, CHAPEL)
    return bad


def stoop_find(ue, label):
    return find_new(ue, label)


def place_stoop(ue, label, c, h, amount):
    found = stoop_find(ue, label)
    if len(found) > 1:
        return None, [f"{len(found)} actors labelled {label}"]
    if found:
        path = found[0]
    else:
        r = ue.call(SC, "add_to_scene_from_class", {"actor_type": rp(STOOP_CLASS), "name": label,
                                                    "xform": {"location": c, "rotation": ZERO_ROT, "scale": ONE}})
        path = r["refPath"] if isinstance(r, dict) else r
    ue.call(AC, "set_label", {"actor": rp(path), "label": label})
    ue.call(SC, "set_actor_folder", {"actor": rp(path), "folder_path": STOOP_FOLDER})
    ue.call(AC, "set_actor_transform", {"actor": rp(path), "worldspace": True, "xform": {"location": c, "rotation": ZERO_ROT, "scale": ONE}})
    bad = put(ue, path, {"StoopAmount": amount}, label)
    box = path + ".Box"
    cur = get1(ue, box, "boxExtent")
    for ax in ("x", "y", "z"):                          # one axis per call, each read back
        if abs(cur[ax] - h[ax]) > 1e-3:
            set_props(ue, box, {"boxExtent": dict(cur, **{ax: h[ax]})})
            cur = get1(ue, box, "boxExtent")
    return path, bad + check_zone(ue, path, label, c, h, amount)


def check_zone(ue, path, label, c, h, amount):
    bad = []
    t = ue.call(AC, "get_actor_transform", {"actor": rp(path), "worldspace": True})
    if not same({"location": c, "rotation": ZERO_ROT, "scale": ONE}, t):
        bad.append(f"{label} transform {t}")
    if not same(amount, get1(ue, path, "StoopAmount")):
        bad.append(f"{label} StoopAmount {get1(ue, path, 'StoopAmount')}")
    ext = get1(ue, path + ".Box", "boxExtent")
    if not same(h, ext):
        bad.append(f"{label} BoxExtent {ext}")
    if ue.call(AC, "get_label", {"actor": rp(path)}) != label:
        bad.append(f"{label} label")
    if path not in [a["refPath"] if isinstance(a, dict) else a for a in ue.call(SC, "get_actors_in_folder", {"folder_path": STOOP_FOLDER})]:
        bad.append(f"{label} not in folder {STOOP_FOLDER}")
    return bad


def do_map(ue):
    n0 = count_actors(ue)
    print(f"  actor count before: {n0}", flush=True)
    placed = [l for l, *_ in STOOP_ZONES if stoop_find(ue, l)]
    if n0 != EXPECTED_BEFORE + len(placed):
        print(f"REFUSED: {n0} actors with {len(placed)} stoop zones already placed; expected {EXPECTED_BEFORE + len(placed)}")
        return 1
    if is_dirty(ue, APP_PKG):
        print("REFUSED: BP_WardenApparition is dirty; save it first (--save apparition)")
        return 1
    bad = []
    path = chapel_path(ue)
    if not path:
        print("REFUSED: Apparition_Chapel not found exactly once")
        return 1
    bad += set_chapel(ue, path)
    print("  chapel done:", path, flush=True)
    for label, c, h, amount in STOOP_ZONES:
        zpath, b = place_stoop(ue, label, c, h, amount)
        print(f"  {label}: {'ok' if not b else b}", flush=True)
        bad += b
    n1 = count_actors(ue)
    print(f"  actor count after: {n1} (expected {EXPECTED_AFTER})", flush=True)
    if n1 != EXPECTED_AFTER:
        bad.append(f"actor count {n1}")
    bad += check_map_instances(ue)
    print("map:", "OK" if not bad else f"PROBLEMS {bad}")
    return 0 if not bad else 1


def check_map_instances(ue):
    """Read back the two apparitions (the chapel as changed, the courtyard as it was)."""
    bad = []
    path = chapel_path(ue)
    if not path:
        return ["Apparition_Chapel missing"]
    st = get1(ue, path, "Stations")
    if not same([CHAPEL_STATION], st):
        bad.append(f"chapel Stations: {st}")
    if get1(ue, path, "bUseSkeletalFigure") is not True:
        bad.append("chapel bUseSkeletalFigure")
    slots, vals = figure_values(ue)
    for k, want in vals.items():
        got = get1(ue, path + ".Figure", k)
        if not same(want, got):
            bad.append(f"chapel Figure.{k}: wanted {want}, read {got}")
    bad += figure_extra(ue, path + ".Figure")
    cy = find_new(ue, COURTYARD)
    if len(cy) != 1:
        bad.append("courtyard not found once")
    else:
        spec = apf.INSTANCES[COURTYARD]
        for k, want in apf.instance_values(spec).items():
            if not same(want, get1(ue, cy[0], k)):
                bad.append(f"courtyard {k}")
        if not same(spec["stations"], get1(ue, cy[0], "Stations")):
            bad.append("courtyard Stations changed")
        if get1(ue, cy[0], "bUseSkeletalFigure") is not False:
            bad.append("courtyard bUseSkeletalFigure must stay false")
    return bad

# ------------------------------------------------------------------ BP_Warden (section 11, step 1)
CM0 = WARDEN_PKG + ".Default__BP_Warden_C:CharacterMesh0"
CM0_VALUES = {"animationMode": "AnimationBlueprint", "animClass": rp(ABP_CLASS),
              "visibilityBasedAnimTickOption": "OnlyTickMontagesWhenNotRendered", "bEnableUpdateRateOptimizations": True}
# ELBWardenState (LBWardenTypes.h): Dormant 0, Search 4 (byte literals; add_variable can't make enum variables, MCP_NOTES item 15).
STATE_DORMANT, STATE_SEARCH = 0, 4
STOP_BLEND = 0.2
LOOK_TICK, LOOK_SPEED, LOOK_AFTER = 0.25, 10.0, 0.5
NEW_VARS = {"bInSearch": "bool", "SearchStillSeconds": "float", "bLookedThisPause": "bool"}

# The anim instance of the mesh is reached the same way everywhere: GetMesh -> GetAnimInstance -> Cast to LBWardenAnimInstance.
CAST_AND = '''(bind mesh (Variables|Character|GetMesh))
  (bind anim (Components|SkeletalMesh|GetAnimInstance :self mesh))
  (bind warden (Utilities|Casting|CastToLBWardenAnimInstance :Object anim)
    (:then
      {call})
    (:CastFailed))'''

FUNCTIONS = {
    # name: (params [(name, type)], dsl)
    "PlayAttackAnim": ([], '''(fn PlayAttackAnim ()
  ; ShowWindupTell calls this: the attack montage starts with the windup (the montage's play rate puts the reach at the end of it)
  %s)
''' % CAST_AND.format(call="(Warden|PlayAttack :self warden)")),
    "HandlePlayerCaught": ([], '''(fn HandlePlayerCaught ()
  ; OnPlayerCaught: the brain keeps running for about 1.5 s after the catch, so stop the Warden walking, then hold the grab pose
  (bind move (Variables|Character|GetCharacterMovement))
  (Pawn|Components|CharacterMovement|DisableMovement :self move)
  %s)
''' % CAST_AND.format(call="(Warden|HoldCatchPose :self warden)")),
    "UpdateAnimState": ([("NewState", "byte")], f'''(fn UpdateAnimState (NewState)
  ; bInSearch feeds CheckSearchPause; Dormant ({STATE_DORMANT}) cuts every montage over {STOP_BLEND} s (a null montage stops them all)
  (Variables|Default|SetInSearch (== NewState {STATE_SEARCH}))
  (if (== NewState {STATE_DORMANT})
    (bind mesh (Variables|Character|GetMesh))
    (bind anim (Components|SkeletalMesh|GetAnimInstance :self mesh))
    (Animation|Montage|MontageStop :self anim :InBlendOutTime {STOP_BLEND})))
'''),
    "StartSearchPauseTimer": ([], f'''(fn StartSearchPauseTimer ()
  ; BeginPlay starts this once: CheckSearchPause runs every {LOOK_TICK} s for the life of the actor
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "CheckSearchPause" :Time {LOOK_TICK} :bLooping true))
'''),
    "CheckSearchPause": ([], f'''(fn CheckSearchPause ()
  ; While the Warden stands still in Search, count {LOOK_TICK} s per tick. At {LOOK_AFTER} s play one look-around per pause.
  ; Moving (2D speed >= {LOOK_SPEED:g}) or leaving Search resets the count and the once-per-pause flag.
  (bind speed (Math|Vector|VectorLengthXY :A (Transformation|GetVelocity)))
  (if (and (Variables|Default|GetInSearch) (< speed {LOOK_SPEED}))
    (Variables|Default|SetSearchStillSeconds (+ (Variables|Default|GetSearchStillSeconds) {LOOK_TICK}))
    (if (and (>= (Variables|Default|GetSearchStillSeconds) {LOOK_AFTER}) (not (Variables|Default|GetLookedThisPause)))
      (Variables|Default|SetLookedThisPause true)
      {CAST_AND.format(call="(Warden|PlayLookAround :self warden)")})
    (else
      (Variables|Default|SetSearchStillSeconds 0.0)
      (Variables|Default|SetLookedThisPause false))))
'''),
}


def step_mesh(ue):
    bad = put(ue, CM0, CM0_VALUES, "CharacterMesh0")
    print("  CharacterMesh0 template:", "ok" if not bad else bad, flush=True)
    return bad


def step_new_variables(ue):
    bp = pkg_ref(WARDEN_PKG)
    have = ue.call(BPT, "list_variables", {"blueprint": bp})
    for name, typ in NEW_VARS.items():
        if name not in have:
            ue.call(BPT, "add_variable", {"blueprint": bp, "name": name, "type_name": typ})
    have = ue.call(BPT, "list_variables", {"blueprint": bp})
    bad = [v for v in NEW_VARS if v not in have]
    print("  variables:", have, "" if not bad else f"MISSING {bad}", flush=True)
    return bad


def fix_byte_literals(ue, name):
    """The DSL compares a byte against an integer literal node; put the literal on the byte pin instead (no int-to-byte cast)."""
    g = Graph(ue, name)
    for op in g.type("Equal(Byte)"):
        src = g.sources(op, "B")
        if src and src[0][0]["type_id"].endswith("MakeLiteralInt"):
            lit = src[0][0]
            value = g.value(lit, "Value")
            ue.call(BPT, "delete_node", {"node": lit["node"]})
            g = Graph(ue, name)
            set_pin(ue, g, g.by[op["node"]["refPath"]], "B", value)
            g = Graph(ue, name)


def step_functions(ue):
    bp = pkg_ref(WARDEN_PKG)
    bad = []
    for name, (params, dsl) in FUNCTIONS.items():
        if name not in fn_names(ue):
            ue.call(BPT, "add_function_graph", {"blueprint": bp, "graph_name": name})
        g = Graph(ue, name)
        entry = g.type("|" + name)[0]
        for pname, ptype in params:
            if not any(p["name"] == pname for p in g.pins(entry, "out")):
                ue.call(BPT, "add_function_param", {"graph": wg(name), "param_name": pname, "param_type": ptype, "input_param": True})
        if len(Graph(ue, name).infos) == 1:
            ue.call(BPT, "write_graph_dsl", {"graph": wg(name), "code": dsl})
            fix_byte_literals(ue, name)
        b = CHECKS[name](ue, Graph(ue, name))
        print(f"  {name}:", "ok" if not b else b, flush=True)
        bad += b
    return bad


def step_show(ue):
    """ShowWindupTell: SetVisibility -> SetMaskGlow(1) -> PlayAttackAnim -> EndWindupTell timer."""
    g = Graph(ue, "ShowWindupTell")
    if not g.type("|PlayAttackAnim"):
        glow, timer = g.type("|SetMaskGlow")[0], g.type("SetTimerbyFunctionName")[0]
        n = new_node(ue, "ShowWindupTell", "CallFunction|PlayAttackAnim", 1080, 0)
        g = Graph(ue, "ShowWindupTell")
        n = g.by[n["node"]["refPath"]]
        link(ue, g, g.by[glow["node"]["refPath"]], "then", n, "execute")       # replaces glow -> timer
        link(ue, g, n, "then", g.by[timer["node"]["refPath"]], "execute")
    bad = check_show(ue, Graph(ue, "ShowWindupTell"))
    print("  ShowWindupTell:", "ok" if not bad else bad, flush=True)
    return bad


def step_feedback(ue):
    """PlayStateFeedback: entry -> UpdateAnimState(NewState) -> (the existing LastFeedbackState and glow logic, unchanged)."""
    g = Graph(ue, "PlayStateFeedback")
    if not g.type("|UpdateAnimState"):
        entry, setlast = g.type("|PlayStateFeedback")[0], g.type("|SetLastFeedbackState")[0]
        n = new_node(ue, "PlayStateFeedback", "CallFunction|UpdateAnimState", 220, 0)
        g = Graph(ue, "PlayStateFeedback")
        n = g.by[n["node"]["refPath"]]
        entry, setlast = g.by[entry["node"]["refPath"]], g.by[setlast["node"]["refPath"]]
        link(ue, g, entry, "then", n, "execute")                                # replaces entry -> SetLastFeedbackState
        link(ue, g, entry, "NewState", n, "NewState")
        link(ue, g, n, "then", setlast, "execute")
    bad = check_feedback(ue, Graph(ue, "PlayStateFeedback"))
    print("  PlayStateFeedback:", "ok" if not bad else bad, flush=True)
    return bad


def first_or_new(ue, g, graph, suffix, type_id, x, y):
    """The one existing node of this type in the graph, or a new one. Returns a fresh snapshot and the node's info in it."""
    found = g.type(suffix)
    if len(found) > 1:
        raise RuntimeError(f"{len(found)} nodes of type {suffix} in {graph}")
    if found:
        return g, found[0]
    n = new_node(ue, graph, type_id, x, y)
    g = Graph(ue, graph)
    return g, g.by[n["node"]["refPath"]]


def linked(g, out_info, out_name, in_info, in_name):
    return any(t["node"]["refPath"] == in_info["node"]["refPath"] and n == in_name for t, n in g.targets(out_info, out_name))


def ensure_link(ue, graph, a, a_pin, b, b_pin):
    """Connect once (nodes are looked up by path in a fresh snapshot, so this is safe to rerun)."""
    g = Graph(ue, graph)
    ai, bi = g.by[a["node"]["refPath"]], g.by[b["node"]["refPath"]]
    if not linked(g, ai, a_pin, bi, b_pin):
        link(ue, g, ai, a_pin, bi, b_pin)


def step_event_graph(ue):
    """EventGraph: BeginPlay -> BindToBrain -> SetupMaskGlow -> StartSearchPauseTimer.
    BindToBrain: ... AssignOnAttackWindup -> AssignOnPlayerCaught(OnPlayerCaught_Event -> HandlePlayerCaught) -> SetbBrainBound.
    EndPlay: ... UnbindEventfromOnAttackWindup -> UnbindEventfromOnPlayerCaught(CreateEvent OnPlayerCaught_Event).
    Every node is looked up first and every link made only if missing, so a half-finished run is completed by the next one."""
    E = "EventGraph"
    g = Graph(ue, E)
    setup = g.type("|SetupMaskGlow")[0]
    g, timer = first_or_new(ue, g, E, "|StartSearchPauseTimer", "CallFunction|StartSearchPauseTimer", 800, 0)
    ensure_link(ue, E, setup, "then", timer, "execute")
    # bind
    g = Graph(ue, E)
    att = g.type("|AssignOnAttackWindup")[0]
    brain = [i for i in g.type("LastBell|Warden|GetBrain") if g.targets(i, "ReturnValue") and any(t["type_id"].endswith("|AssignOnStateChanged") for t, _ in g.targets(i, "ReturnValue"))][0]
    setb = [i for i in g.type("|SetbBrainBound") if g.pin(i, "bBrainBound", "in")["value"] == "true"][0]
    g, ev = first_or_new(ue, g, E, "AddEvent|Custom|OnPlayerCaught_Event", "AddEvent|Custom|OnPlayerCaught_Event", 0, 1400)
    g, asg = first_or_new(ue, g, E, "|AssignOnPlayerCaught", "LastBell|Warden|AssignOnPlayerCaught", 1400, 400)
    g, call = first_or_new(ue, g, E, "|HandlePlayerCaught", "CallFunction|HandlePlayerCaught", 700, 1400)
    nxt = [t["node"]["refPath"] for t, _ in g.targets(g.by[att["node"]["refPath"]], "then")]
    if nxt not in ([setb["node"]["refPath"]], [asg["node"]["refPath"]]):
        return [f"AssignOnAttackWindup leads to {nxt}, not SetbBrainBound; refusing to splice"]
    ensure_link(ue, E, att, "then", asg, "execute")                              # replaces att -> SetbBrainBound
    ensure_link(ue, E, brain, "ReturnValue", asg, "self")
    ensure_link(ue, E, ev, "OutputDelegate", asg, "Delegate")
    ensure_link(ue, E, asg, "then", setb, "execute")
    ensure_link(ue, E, ev, "then", call, "execute")
    # creating an Assign node also creates its own custom event (OnPlayerCaught_Event_0), wired to it; wiring ours in its place
    # leaves that one loose. Delete every unconnected copy.
    for o in [i for i in Graph(ue, E).infos if i["type_id"].startswith("AddEvent|Custom|OnPlayerCaught_Event_")]:
        if not any(p["connected_pins"] for p in o["output_pins"]):
            ue.call(BPT, "delete_node", {"node": o["node"]})
    # unbind (EndPlay)
    g = Graph(ue, E)
    unb_att = g.type("|UnbindEventfromOnAttackWindup")[0]
    unb_brain = g.sources(unb_att, "self")[0][0]
    g, unb = first_or_new(ue, g, E, "|UnbindEventfromOnPlayerCaught", "LastBell|Warden|UnbindEventfromOnPlayerCaught", 2300, 700)
    ces = [i for i in g.type("EventDispatchers|CreateEvent") if not g.sources(unb_att, "Delegate")[0][0]["node"]["refPath"] == i["node"]["refPath"]]
    ces = [i for i in ces if i["node"]["refPath"] not in [s[0]["node"]["refPath"] for x in g.type("|UnbindEventfromOnStateChanged") for s in g.sources(x, "Delegate")]]
    if len(ces) > 1:
        return [f"{len(ces)} loose CreateEvent nodes"]
    if ces:
        ce = ces[0]
    else:
        n = new_node(ue, E, "EventDispatchers|CreateEvent", 2000, 900)
        g = Graph(ue, E)
        ce = g.by[n["node"]["refPath"]]
    ensure_link(ue, E, unb_att, "then", unb, "execute")
    ensure_link(ue, E, unb_brain, "ReturnValue", unb, "self")
    ensure_link(ue, E, ce, "OutputDelegate", unb, "Delegate")                   # the Create Event needs its delegate pin wired first
    if ue.call(BPT, "get_create_event_function", {"node": ce["node"]}) != "OnPlayerCaught_Event":
        ue.call(BPT, "set_create_event_function", {"node": ce["node"], "function_name": "OnPlayerCaught_Event"})
    bad = check_event_graph(ue, Graph(ue, E))
    print("  EventGraph:", "ok" if not bad else bad, flush=True)
    return bad


def do_warden(ue):
    # the map must be saved BEFORE the first BP_Warden edit (compiling a Blueprint with placed instances dirties the level)
    if is_dirty(ue, MAP_PKG) and not is_dirty(ue, WARDEN_PKG):
        print("REFUSED: L_Monastery is dirty and BP_Warden is not edited yet. Save the map first, then start the BP_Warden work.")
        return 1
    if is_dirty(ue, WARDEN_PKG) is None:
        print("REFUSED: BP_Warden not found")
        return 1
    bad = step_mesh(ue) + step_new_variables(ue) + step_functions(ue)
    for step in (step_show, step_feedback, step_event_graph):
        bad += step(ue)
    ok = compile_bp(ue, WARDEN_PKG)
    bad += [b + " (after compile)" for b in check_all_bp(ue)]
    print("warden:", "OK" if not bad and ok else f"PROBLEMS {bad}; compile {ok}")
    return 0 if not bad and ok else 1


# ------------------------------------------------------------------ checks (each returns a list of problems; empty = ok)
check_show, check_feedback, check_event_graph = apf.check_show, apf.check_feedback, apf.check_event_graph


def P(items):
    """node paths of [(info, pin name)]"""
    return [i[0]["node"]["refPath"] for i in items]


def tgt(g, info, pin):
    return [t["node"]["refPath"] for t, _ in g.targets(info, pin)]


def lit(g, info, pin):
    """The number that feeds a pin: a MakeLiteral* node's value, or the pin's own default."""
    src = g.sources(info, pin)
    if src and "MakeLiteral" in src[0][0]["type_id"]:
        return float(g.value(src[0][0], "Value"))
    return float(g.value(info, pin)) if not src else None


def check_cast_chain(g, prev, prev_pin, final_suffix, label):
    """prev -> Cast to LBWardenAnimInstance (Object <- GetAnimInstance <- GetMesh) -> the final call on the cast result; nothing after it."""
    casts, gms, gai, fin = g.type("CastToLBWardenAnimInstance"), g.type("|GetMesh"), g.type("GetAnimInstance"), g.type(final_suffix)
    if not (len(casts) == len(gms) == len(gai) == len(fin) == 1):
        return [f"{label}: expected one GetMesh, GetAnimInstance, cast and {final_suffix}, got {len(gms)}/{len(gai)}/{len(casts)}/{len(fin)}"]
    cast, gm, ga, fin = casts[0], gms[0], gai[0], fin[0]
    bad = []
    if tgt(g, prev, prev_pin) != [cast["node"]["refPath"]]:
        bad.append(f"{label}: the cast is not entered from {prev['type_id'].split('|')[-1]}.{prev_pin}")
    if P(g.sources(ga, "self")) != [gm["node"]["refPath"]] or P(g.sources(cast, "Object")) != [ga["node"]["refPath"]]:
        bad.append(f"{label}: the cast's Object must be GetMesh -> GetAnimInstance")
    if tgt(g, cast, "then") != [fin["node"]["refPath"]]:
        bad.append(f"{label}: the cast must lead to {final_suffix}")
    s = g.sources(fin, "self")
    if len(s) != 1 or s[0][0]["node"]["refPath"] != cast["node"]["refPath"] or not s[0][1].startswith("AsLBWarden"):
        bad.append(f"{label}: {final_suffix} self must be the cast result")
    if g.targets(cast, "CastFailed") or g.targets(fin, "then"):
        bad.append(f"{label}: CastFailed and the end of the chain must be empty")
    return bad


def check_play_attack_anim(ue, g):
    if len(g.infos) != 5:
        return [f"PlayAttackAnim: 5 nodes expected, got {[i['type_id'] for i in g.infos]}"]
    return check_cast_chain(g, g.type("|PlayAttackAnim")[0], "then", "Warden|PlayAttack", "PlayAttackAnim")


def check_handle_player_caught(ue, g):
    dm, gcm = g.type("DisableMovement"), g.type("|GetCharacterMovement")
    if len(g.infos) != 7 or len(dm) != 1 or len(gcm) != 1:
        return [f"HandlePlayerCaught: 7 nodes (entry, GetCharacterMovement, DisableMovement, GetMesh, GetAnimInstance, cast, HoldCatchPose) expected, got {[i['type_id'] for i in g.infos]}"]
    bad = []
    dm, gcm = dm[0], gcm[0]
    if tgt(g, g.type("|HandlePlayerCaught")[0], "then") != [dm["node"]["refPath"]] or P(g.sources(dm, "self")) != [gcm["node"]["refPath"]]:
        bad.append("HandlePlayerCaught: entry -> DisableMovement(GetCharacterMovement) is not wired")
    return bad + check_cast_chain(g, dm, "then", "Warden|HoldCatchPose", "HandlePlayerCaught")


def check_update_anim_state(ue, g):
    entry, setv, br, stop = g.type("|UpdateAnimState"), g.type("|SetbInSearch"), g.type("Utilities|FlowControl|Branch"), g.type("Montage_Stop")
    eqs, gai, gm = g.type("Equal(Byte)"), g.type("GetAnimInstance"), g.type("|GetMesh")
    if not (len(entry) == len(setv) == len(br) == len(stop) == len(gai) == len(gm) == 1 and len(eqs) == 2 and len(g.infos) == 8):
        return [f"UpdateAnimState: unexpected nodes (8 expected): {[i['type_id'] for i in g.infos]}"]
    entry, setv, br, stop, gai, gm = entry[0], setv[0], br[0], stop[0], gai[0], gm[0]
    bad = []
    if not any(p["name"] == "NewState" and "Byte" in p["type_id"] for p in entry["output_pins"]):
        bad.append("UpdateAnimState needs a byte input NewState")
    by_b = {g.value(e, "B"): e for e in eqs}
    if set(by_b) != {str(STATE_SEARCH), str(STATE_DORMANT)}:
        return bad + [f"the two comparisons must be against {STATE_SEARCH} (Search) and {STATE_DORMANT} (Dormant), got {sorted(by_b)}"]
    e_search, e_dormant = by_b[str(STATE_SEARCH)], by_b[str(STATE_DORMANT)]
    for e in (e_search, e_dormant):
        if [s[1] for s in g.sources(e, "A")] != ["NewState"]:
            bad.append("each comparison must read NewState")
    if tgt(g, entry, "then") != [setv["node"]["refPath"]] or P(g.sources(setv, "bInSearch")) != [e_search["node"]["refPath"]]:
        bad.append("entry -> SetbInSearch(NewState == 4) is not wired")
    if tgt(g, setv, "then") != [br["node"]["refPath"]] or P(g.sources(br, "Condition")) != [e_dormant["node"]["refPath"]]:
        bad.append("SetbInSearch -> Branch(NewState == 0) is not wired")
    if tgt(g, br, "then") != [stop["node"]["refPath"]] or g.targets(br, "else") or g.targets(stop, "then"):
        bad.append("Dormant must lead to Montage Stop and nothing else")
    if P(g.sources(stop, "self")) != [gai["node"]["refPath"]] or P(g.sources(gai, "self")) != [gm["node"]["refPath"]]:
        bad.append("Montage Stop self must be GetMesh -> GetAnimInstance")
    if g.sources(stop, "Montage"):
        bad.append("Montage Stop must have no montage connected (null stops all)")
    if abs(float(g.value(stop, "InBlendOutTime")) - STOP_BLEND) > 1e-6:
        bad.append(f"blend out time is {g.value(stop, 'InBlendOutTime')}, expected {STOP_BLEND}")
    return bad


def check_start_timer(ue, g):
    entry, timer, me = g.type("|StartSearchPauseTimer"), g.type("SetTimerbyFunctionName"), g.type("Self-Reference")
    if not (len(entry) == len(timer) == len(me) == 1 and len(g.infos) == 3):
        return [f"StartSearchPauseTimer: 3 nodes expected, got {[i['type_id'] for i in g.infos]}"]
    entry, timer, me = entry[0], timer[0], me[0]
    bad = []
    if tgt(g, entry, "then") != [timer["node"]["refPath"]] or P(g.sources(timer, "Object")) != [me["node"]["refPath"]]:
        bad.append("entry -> timer on self is not wired")
    if g.value(timer, "FunctionName") != "CheckSearchPause":
        bad.append(f"timer function is {g.value(timer, 'FunctionName')!r}")
    if abs(float(g.value(timer, "Time")) - LOOK_TICK) > 1e-6 or g.value(timer, "bLooping") != "true":
        bad.append(f"timer must loop every {LOOK_TICK} s: Time {g.value(timer, 'Time')}, bLooping {g.value(timer, 'bLooping')}")
    return bad


def check_check_search_pause(ue, g):
    brs, sets_s, sets_l = g.type("Utilities|FlowControl|Branch"), g.type("|SetSearchStillSeconds"), g.type("|SetbLookedThisPause")
    if not (len(brs) == 2 and len(sets_s) == 2 and len(sets_l) == 2 and len(g.infos) == 26):
        return [f"CheckSearchPause: unexpected nodes (26 expected): {[i['type_id'] for i in g.infos]}"]
    entry = g.type("|CheckSearchPause")[0]
    bad = []
    vel, vxy, lt, ge = g.type("Transformation|GetVelocity"), g.type("VectorLengthXY"), g.type("float<float"), g.type("float>=float")
    add, ands, nots = g.type("float+float"), g.type("ANDBoolean"), g.type("NOTBoolean")
    gin, glook, gstill = g.type("|GetbInSearch"), g.type("|GetbLookedThisPause"), g.type("|GetSearchStillSeconds")
    if not (len(vel) == len(vxy) == len(lt) == len(ge) == len(add) == len(nots) == len(gin) == len(glook) == 1 and len(ands) == 2 and len(gstill) == 2):
        return ["CheckSearchPause: the condition nodes are not as expected"]
    vel, vxy, lt, ge, add, nots, gin, glook = vel[0], vxy[0], lt[0], ge[0], add[0], nots[0], gin[0], glook[0]
    b1 = [b for b in brs if tgt(g, entry, "then") == [b["node"]["refPath"]]]
    if len(b1) != 1:
        return ["entry must lead to the first branch"]
    b1 = b1[0]
    b2 = [b for b in brs if b is not b1][0]
    # the first condition: InSearch AND (2D speed < 10)
    c1 = g.sources(b1, "Condition")
    if len(c1) != 1 or c1[0][0]["type_id"] != ands[0]["type_id"]:
        return ["the first branch must be driven by an AND"]
    and1 = c1[0][0]
    if sorted(P(g.sources(and1, "A")) + P(g.sources(and1, "B"))) != sorted([gin["node"]["refPath"], lt["node"]["refPath"]]):
        bad.append("first condition must be (bInSearch AND speed < limit)")
    if P(g.sources(lt, "A")) != [vxy["node"]["refPath"]] or P(g.sources(vxy, "A")) != [vel["node"]["refPath"]] or abs(lit(g, lt, "B") - LOOK_SPEED) > 1e-6:
        bad.append(f"speed must be VectorLengthXY(GetVelocity) < {LOOK_SPEED:g}")
    # still: Branch1.then -> SetSearchStillSeconds(StillSeconds + 0.25) -> Branch2
    st_add = [x for x in sets_s if P(g.sources(x, "SearchStillSeconds")) == [add["node"]["refPath"]]]
    st_zero = [x for x in sets_s if x not in st_add]
    if len(st_add) != 1 or len(st_zero) != 1 or tgt(g, b1, "then") != [st_add[0]["node"]["refPath"]] or tgt(g, b1, "else") != [st_zero[0]["node"]["refPath"]]:
        return bad + ["first branch: true -> SetSearchStillSeconds(+step), false -> SetSearchStillSeconds(0)"]
    st_add, st_zero = st_add[0], st_zero[0]
    if abs(lit(g, add, "B") - LOOK_TICK) > 1e-6 or g.sources(add, "A")[0][0]["type_id"] != gstill[0]["type_id"]:
        bad.append(f"the count must add {LOOK_TICK} to SearchStillSeconds")
    if lit(g, st_zero, "SearchStillSeconds") != 0.0:
        bad.append("the reset must set SearchStillSeconds to 0")
    if tgt(g, st_add, "then") != [b2["node"]["refPath"]]:
        bad.append("the count must lead to the second branch")
    # second: (StillSeconds >= 0.5) AND NOT LookedThisPause
    c2 = g.sources(b2, "Condition")
    if len(c2) != 1 or c2[0][0]["type_id"] != ands[0]["type_id"] or c2[0][0]["node"]["refPath"] == and1["node"]["refPath"]:
        return bad + ["the second branch must be driven by the second AND"]
    and2 = c2[0][0]
    if sorted(P(g.sources(and2, "A")) + P(g.sources(and2, "B"))) != sorted([ge["node"]["refPath"], nots["node"]["refPath"]]):
        bad.append("second condition must be (SearchStillSeconds >= 0.5 AND NOT bLookedThisPause)")
    if g.sources(ge, "A")[0][0]["type_id"] != gstill[0]["type_id"] or abs(lit(g, ge, "B") - LOOK_AFTER) > 1e-6:
        bad.append(f"threshold must be SearchStillSeconds >= {LOOK_AFTER}")
    if P(g.sources(nots, "A")) != [glook["node"]["refPath"]]:
        bad.append("NOT must read bLookedThisPause")
    look_true = [x for x in sets_l if g.value(x, "bLookedThisPause") == "true"]
    look_false = [x for x in sets_l if g.value(x, "bLookedThisPause") == "false"]
    if len(look_true) != 1 or len(look_false) != 1:
        return bad + ["one SetbLookedThisPause(true) and one (false) expected"]
    if tgt(g, b2, "then") != [look_true[0]["node"]["refPath"]] or g.targets(b2, "else"):
        bad.append("second branch: true -> SetbLookedThisPause(true); false -> nothing")
    bad += check_cast_chain(g, look_true[0], "then", "Warden|PlayLookAround", "CheckSearchPause")
    if tgt(g, st_zero, "then") != [look_false[0]["node"]["refPath"]] or g.targets(look_false[0], "then"):
        bad.append("reset: SetSearchStillSeconds(0) -> SetbLookedThisPause(false), and stop")
    return bad


CHECKS = {"PlayAttackAnim": check_play_attack_anim, "HandlePlayerCaught": check_handle_player_caught, "UpdateAnimState": check_update_anim_state,
          "StartSearchPauseTimer": check_start_timer, "CheckSearchPause": check_check_search_pause}


def check_apparition_figure(ue):
    """BP_WardenApparition class default Figure, as saved."""
    slots, vals = figure_values(ue)
    bad = []
    for k, want in vals.items():
        got = get1(ue, APP_CDO + ":Figure", k)
        if not same(want, got):
            bad.append(f"{k}: wanted {want}, read {got}")
    bad += figure_extra(ue, APP_CDO + ":Figure")
    mats = get1(ue, APP_CDO + ":Figure", "overrideMaterials")
    by_slot = dict(zip(slots, [m["refPath"].split("/")[-1].split(".")[0] if isinstance(m, dict) else m for m in mats]))
    want_slot = {s: ("MI_Warden_Apparition_Mask" if s == BELL_SLOT else "MI_Warden_Apparition_Body") for s in slots}
    if by_slot != want_slot:
        bad.append(f"slot -> material {by_slot}")
    return bad


def check_chapel_and_zones(ue):
    bad = check_map_instances(ue)
    n = count_actors(ue)
    if n != EXPECTED_AFTER:
        bad.append(f"actor count {n}, expected {EXPECTED_AFTER}")
    for label, c, h, amount in STOOP_ZONES:
        found = find_new(ue, label)
        if len(found) != 1:
            bad.append(f"{label}: {len(found)} actors")
            continue
        bad += check_zone(ue, found[0], label, c, h, amount)
        if ue.call(SC, "get_actors_in_folder", {"folder_path": STOOP_FOLDER}) is None:
            bad.append("stoop folder empty")
    extra = [a for a in ue.call(SC, "get_actors_in_folder", {"folder_path": STOOP_FOLDER})]
    if len(extra) != STOOP_COUNT:
        bad.append(f"{len(extra)} actors in {STOOP_FOLDER}, expected {STOOP_COUNT}")
    return bad


def check_abp_anim_set(ue):
    abp = ue.call(BPT, "get_default_object", {"blueprint": pkg_ref(CH + "/ABP_Warden")})
    path = abp["refPath"] if isinstance(abp, dict) else abp
    got = get1(ue, path, "AnimSet")
    want = rp("/Game/LastBell/Data/DA_WardenAnimSet.DA_WardenAnimSet")
    return [] if same(want, got) else [f"ABP_Warden AnimSet is {got}"]


def check_p13_bp(ue, res):
    """The P13-7 groups: material, apparition Figure, chapel and stoop zones (in the open map), BP_Warden mesh and graphs."""
    def grp(name, fn):
        try:
            bad = fn()
        except Exception as e:  # noqa: BLE001
            bad = [f"could not be read: {type(e).__name__}: {str(e)[:200]}"]
        res.check(not bad, name, "; ".join(bad))

    mp = MAT_PKG + "." + MAT_PKG.split("/")[-1]
    grp("M_Warden_Apparition: bUsedWithSkeletalMesh is on, and the package is saved", lambda: (
        [] if get1(ue, mp, "bUsedWithSkeletalMesh") is True and is_dirty(ue, MAT_PKG) is False else ["flag off or package dirty"]))
    grp("M_LB_Surface is not dirty (never touched)", lambda: [] if is_dirty(ue, SURFACE_PKG) is False else ["dirty"])
    grp("BP_WardenApparition Figure: SK_Warden, Animation Blueprint ABP_Warden_C, Mask MI on M_Warden_BellMetal and Body MI on the other 5 slots (by name), "
        "hidden, no shadow, NoCollision; the package is saved",
        lambda: check_apparition_figure(ue) + ([] if is_dirty(ue, APP_PKG) is False else ["BP_WardenApparition is dirty"]))
    grp("BP_Warden CharacterMesh0 template: SK_Warden, Animation Blueprint ABP_Warden_C, OnlyTickMontagesWhenNotRendered, update-rate optimisation on",
        lambda: [f"{k}: wanted {w}, read {get1(ue, CM0, k)}" for k, w in dict(CM0_VALUES, skeletalMeshAsset=pkg_ref(MESH_PKG)).items() if not same(w, get1(ue, CM0, k))])
    grp("ABP_Warden class default AnimSet is DA_WardenAnimSet", lambda: check_abp_anim_set(ue))
    grp("BP_Warden variables bInSearch, SearchStillSeconds, bLookedThisPause exist",
        lambda: [v for v in NEW_VARS if v not in ue.call(BPT, "list_variables", {"blueprint": pkg_ref(WARDEN_PKG)})])
    descr = {"PlayAttackAnim": "GetMesh -> GetAnimInstance -> cast -> PlayAttack",
             "HandlePlayerCaught": "GetCharacterMovement -> DisableMovement, then cast -> HoldCatchPose",
             "UpdateAnimState": "bInSearch = (NewState == 4); on Dormant (0) Montage Stop with no montage, blend out 0.2",
             "StartSearchPauseTimer": "SetTimer CheckSearchPause on self, 0.25 s, looping",
             "CheckSearchPause": "InSearch and speed < 10: +0.25; at 0.5 and not yet looked: bLookedThisPause = true and cast -> PlayLookAround; otherwise reset both"}
    for name, d in descr.items():
        grp(f"BP_Warden {name}: {d}", lambda name=name: CHECKS[name](ue, Graph(ue, name)))
    if ue.call(SC, "get_current_level", {}) == MAP_PKG:
        grp("L_Monastery (open): Apparition_Chapel skeletal figure, one station with WalkPath and speed 110, the Figure values on the instance, "
            "Apparition_Courtyard unchanged, the 12 stoop zones exactly as section 7, folder Gameplay/Warden/StoopZones, 2992 actors",
            lambda: check_chapel_and_zones(ue))


class Collect:
    """Result-compatible collector: remembers the failures instead of printing PASS/FAIL lines."""

    def __init__(self):
        self.bad = []

    def check(self, ok, name, detail=""):
        if not ok:
            self.bad.append(f"{name}: {detail}")
        return ok


def check_all_bp(ue):
    """Every BP_Warden / BP_WardenApparition check (P12 fix set 1 groups as updated, plus the P13-7 groups). Returns the problems."""
    c = Collect()
    apf.check_warden_bp(ue, c)
    check_p13_bp(ue, c)
    return c.bad


def do_check(ue):
    import check_warden  # noqa: E402
    res = check_warden.Result()
    apf.check_apparition_bp(ue, res)
    apf.check_placed(ue, res)
    apf.check_warden_bp(ue, res)
    check_p13_bp(ue, res)
    print("%d/%d" % (res.passed, res.total))
    return 0 if res.passed == res.total else 1


# ------------------------------------------------------------------ save (one package per call, explicit)
SAVE_PKGS = {"material": MAT_PKG, "apparition": APP_PKG, "map": MAP_PKG, "warden": WARDEN_PKG}
# never saved by this script; their dirty state is only reported
WATCH = apf.WATCH + [CH + "/ABP_Warden", CH + "/ABP_P13_Spike", CH + "/Meshes/SK_Warden_PhysicsAsset", "/Game/LastBell/Data/DA_WardenAnimSet",
                     "/Game/LastBell/Maps/L_Test_Warden"]


def do_save(ue, name):
    pkg = SAVE_PKGS[name]
    before = is_dirty(ue, pkg)
    res = ue.call(AS, "save_assets", {"asset_paths": [pkg]})
    after = is_dirty(ue, pkg)
    print(f"  save {pkg.split('/')[-1]}: was dirty {before}, returned {res}, is_dirty now {after}")
    print("  dirty and NOT saved on purpose:", sorted(p.split("/")[-1] for p in WATCH if is_dirty(ue, p)) or "none")
    return 0 if res is True and after is False else 1


# ------------------------------------------------------------------ MAIN
MODE_NAMES = ["preflight", "material", "apparition", "map", "warden", "check"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    for m in MODE_NAMES:
        g.add_argument("--" + m, action="store_true")
    g.add_argument("--save", metavar="NAME", choices=list(SAVE_PKGS))
    a = ap.parse_args()
    ue = UE()
    try:
        if ue.call(APP, "IsPIERunning", {}):
            print("refused: PIE is running. Nothing was changed.")
            return 1
        if ue.call(SC, "get_current_level", {}) != MAP_PKG:
            print(f"refused: the current level is not {MAP_PKG}")
            return 1
        if a.save:
            return do_save(ue, a.save)
        for m in MODE_NAMES:
            if getattr(a, m):
                return globals()["do_" + m](ue)
    except Exception as e:  # noqa: BLE001
        print(f"TOOL CALL FAILED: {str(e)[:700]}\nState unknown. Run --check before anything else; do not retry in a loop.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
