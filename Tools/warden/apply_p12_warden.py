"""P12-8: wire the owner's Warden V5.5 into BP_Warden and BP_WardenSilhouette (replaces the cone-and-cube placeholder).

Spec: Docs/plans/P12_WARDEN_VISUAL.md, "P12-8 and P12-9: changes from the sections below" (the live values) and "P12-8: wire it
in". Run with -I, editor open on L_Monastery, no PIE (every mode refuses while PIE runs). Exactly one mode per run:
    --snapshot FILE   read-only: every value --apply changes, on the Blueprint templates AND on the placed instances in the
                      current level, plus the socket list, the EventGraph nodes, the capsule, the tuning asset and dirty states
    --apply           1. socket `mask` on bone `head` of SK_Warden (zero offset)
                      2. BP_Warden CharacterMesh0: SK_Warden, single-node AN_Warden_Idle looping + playing, location (0,0,-110),
                         yaw 0, NoCollision; each placeholder part: no mesh, hidden, NoCollision (TellLight untouched)
                      3. BP_Warden EventGraph: one function AttachTellLightToMask (AttachToComponent TellLight -> CharacterMesh0,
                         socket `mask`, SnapToTarget) called once from BeginPlay after BindtoBrain; compile with warnings visible
                      4. BP_WardenSilhouette: Body = SM_LB_Warden_Silhouette, (0,0,0), scale 1, yaw +90, MI_LB_WardenSilhouette kept;
                         Head: no mesh, hidden; compile
                      Steps are idempotent; each value is read back and compared. A value that did not stick is reported (exit 1).
    --check           read back everything and compare with the plan and the snapshot; exit 1 on any mismatch
    --save            one package per save_assets call, 5 s apart: SK_Warden, BP_Warden, BP_WardenSilhouette (never a map, never any
                      other Blueprint, never M_LB_Surface, never a material)
    --restore         puts the snapshot values back on the templates, removes the socket and the graph additions. Saves nothing.
    --snap-file FILE  snapshot used by --check / --restore (default Docs/ArtTest/warden/p12_8_before.json)

Nothing saves unless --save is given. Exit codes: 0 ok, 1 mismatch or refused, 2 a tool call failed (state unknown: run --check
before anything else; never retry in a loop).
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE  # noqa: E402

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
OB = "editor_toolset.toolsets.object.ObjectTools"
AS = "editor_toolset.toolsets.asset.AssetTools"
SK = "editor_toolset.toolsets.skeletal_mesh.SkeletalMeshTools"
BPT = "editor_toolset.toolsets.blueprint.BlueprintTools"
SC = "editor_toolset.toolsets.scene.SceneTools"
APP = "EditorToolset.EditorAppToolset"

MESH_PKG = "/Game/LastBell/Characters/Warden/Meshes/SK_Warden"
ANIM_PKG = "/Game/LastBell/Characters/Warden/Anims/AN_Warden_Idle"
SIL_MESH_PKG = "/Game/LastBell/Characters/Warden/Meshes/SM_LB_Warden_Silhouette"
SIL_MI = "/Game/LastBell/Materials/Instances/MI_LB_WardenSilhouette.MI_LB_WardenSilhouette"
WARDEN_PKG = "/Game/LastBell/Blueprints/AI/BP_Warden"
SIL_PKG = "/Game/LastBell/Blueprints/Interactables/BP_WardenSilhouette"
TUNING_PKG = "/Game/LastBell/Data/DA_WardenTuning"
MAP_PKG = "/Game/LastBell/Maps/L_Monastery"
SOCKET = "mask"
BONE = "head"
FN_NAME = "AttachTellLightToMask"

# Templates. CharacterMesh0 is inherited from ACharacter: it is reached through the class default object.
CM0 = WARDEN_PKG + ".Default__BP_Warden_C:CharacterMesh0"
CAPSULE = WARDEN_PKG + ".Default__BP_Warden_C:CollisionCylinder"
CDO = WARDEN_PKG + ".Default__BP_Warden_C"
PARTS = ["Robe", "Shoulders", "Neck", "Head", "ArmLeft", "ArmRight", "Mask", "MaskCrack"]
SIL_CDO = SIL_PKG + ".Default__BP_WardenSilhouette_C"


def tmpl_w(name):       # a component the Blueprint itself added
    return f"{WARDEN_PKG}.BP_Warden_C:{name}_GEN_VARIABLE"


def tmpl_s(name):
    return f"{SIL_PKG}.BP_WardenSilhouette_C:{name}_GEN_VARIABLE"


def inst(actor, comp=None):
    return f"{MAP_PKG}.L_Monastery:PersistentLevel.{actor}" + (f".{comp}" if comp else "")


WARDEN_INSTANCES = ["BP_Warden_C_0"]
SIL_INSTANCES = ["BP_WardenSilhouette_C_2", "BP_WardenSilhouette_C_0"]

# Properties read for the snapshot (a property the object does not have reads as "n/a").
CM_PROPS = ["skeletalMeshAsset", "animationMode", "animationData", "relativeLocation", "relativeRotation", "relativeScale3D",
            "bVisible", "bHiddenInGame", "castShadow", "bCastHiddenShadow", "bOwnerNoSee", "bRenderInMainPass",
            "visibilityBasedAnimTickOption", "boundsScale", "bUseAttachParentBound", "overrideMaterials", "bodyInstance"]
PART_PROPS = ["staticMesh", "bVisible", "bHiddenInGame", "relativeLocation", "relativeRotation", "relativeScale3D", "castShadow",
              "overrideMaterials", "bodyInstance"]
BODY_PROPS = ["bVisible", "bHiddenInGame", "relativeLocation", "relativeRotation", "relativeScale3D"]
LIGHT_PROPS = ["intensity", "lightColor", "attenuationRadius", "castShadows", "bVisible", "bHiddenInGame", "relativeLocation",
               "relativeRotation", "relativeScale3D", "intensityUnits", "sourceRadius", "softSourceRadius", "bAffectsWorld",
               "temperature", "bUseTemperature", "indirectLightingIntensity", "volumetricScatteringIntensity",
               "bCastVolumetricShadow", "lightingChannels", "mobility", "bUseInverseSquaredFalloff", "lightFalloffExponent",
               "castTranslucentShadows", "bAutoActivate"]
SIL_ACTOR_PROPS = ["TriggerTag", "VisibleSeconds", "MoveOffset"]

DEFAULT_SNAP = os.path.join(ROOT, "Docs", "ArtTest", "warden", "p12_8_before.json")
PAUSE_S = 5
SAVE_ORDER = [MESH_PKG, WARDEN_PKG, SIL_PKG]
NEVER_SAVE = ["/Game/LastBell/Materials/Master/M_LB_Surface", MAP_PKG, "/Game/LastBell/Maps/L_Test_Warden"]
WATCH_DIRTY = NEVER_SAVE + ["/Game/LastBell/Characters/Warden/Meshes/SK_Warden_Skeleton",
                            "/Game/LastBell/Characters/Warden/Meshes/SK_Warden_PhysicsAsset", ANIM_PKG, SIL_MESH_PKG, TUNING_PKG,
                            "/Game/LastBell/Characters/Warden/Materials/MI_Warden_Wool",
                            "/Game/LastBell/Characters/Warden/Materials/MI_Warden_Skin", SIL_MI.split(".")[0]]


# ------------------------------------------------------------------ helpers
def rp(path):
    return {"refPath": path}


def pkg_ref(pkg):
    return rp(f"{pkg}.{pkg.split('/')[-1]}")


def as_json(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return v
    return v


def full(r):
    return r.get("refPath") if isinstance(r, dict) else r


def short(r):
    r = full(r)
    return r.split("/")[-1].split(".")[0] if r and r != "None" else None


def close(a, b, tol=1e-3):
    return abs(float(a) - float(b)) <= tol


def vec_close(v, w, tol=1e-3):
    return all(close(v[k], w[k], tol) for k in "xyz")


def rot_close(v, w, tol=1e-3):
    return all(close(v[k], w[k], tol) for k in ("pitch", "yaw", "roll"))


def is_dirty(ue, pkg):
    if not ue.call(AS, "exists", {"path": pkg}):
        return None
    return ue.call(AS, "is_dirty", {"asset_path": pkg})


def refuse_if_pie(ue):
    if ue.call(APP, "IsPIERunning", {}):
        print("refused: PIE is running. Nothing was changed.")
        return True
    return False


def get1(ue, path, name):
    """One property of one object; the string 'n/a' when the object does not have it."""
    try:
        r = as_json(ue.call(OB, "get_properties", {"instance": rp(path), "properties": [name]}))
        return r[name]
    except Exception as e:  # noqa: BLE001
        if "could not be read" in str(e) or "not valid" in str(e):
            return "n/a"
        raise


def read_props(ue, path, props):
    out = {}
    for p in props:
        v = get1(ue, path, p)
        if p == "bodyInstance" and isinstance(v, dict):
            v = {k: v.get(k) for k in ("collisionProfileName", "collisionEnabled", "objectType")}
        out[p] = v
    return out


def set_props(ue, path, values):
    ue.call(OB, "set_properties", {"instance": rp(path), "values": json.dumps(values)})


def body_profile(ue, path):
    v = get1(ue, path, "bodyInstance")
    return v.get("collisionProfileName") if isinstance(v, dict) else None


def level_ok(ue):
    return ue.call(SC, "get_current_level", {}) == MAP_PKG


# ------------------------------------------------------------------ graph helpers
def graph_ref(bp_pkg, graph):
    name = bp_pkg.split("/")[-1]
    return rp(f"{bp_pkg}.{name}:{graph}")


def graph_nodes(ue, bp_pkg, graph):
    """[(title, node ref path)] of every node of a graph (find_nodes with an empty title matches all)."""
    try:
        r = ue.call(BPT, "find_nodes", {"graph": graph_ref(bp_pkg, graph), "title": ""})
    except Exception:  # noqa: BLE001
        return None
    return r


def list_graph_names(ue, bp_pkg):
    return [full(g).split(":")[-1] for g in ue.call(BPT, "list_graphs", {"blueprint": pkg_ref(bp_pkg)})]


# ------------------------------------------------------------------ snapshot
def tuning_values(ue):
    """Every property of the tuning data asset (the asset must stay untouched)."""
    path = TUNING_PKG + ".DA_WardenTuning"
    names = sorted(as_json(ue.call(OB, "list_properties", {"instance": rp(path)})).keys())
    return {p: get1(ue, path, p) for p in names}


def do_snapshot(ue, path):
    if not level_ok(ue):
        print(f"REFUSED: the current level is not {MAP_PKG}")
        return 1
    snap = {"taken": time.strftime("%Y-%m-%d %H:%M:%S"), "note": "values read before P12-8 changed anything"}
    snap["templates"] = {"CharacterMesh0": read_props(ue, CM0, CM_PROPS)}
    snap["templates"]["PlaceholderBody"] = read_props(ue, tmpl_w("PlaceholderBody"), BODY_PROPS)
    for n in PARTS:
        snap["templates"][n] = read_props(ue, tmpl_w(n), PART_PROPS)
    snap["templates"]["TellLight"] = read_props(ue, tmpl_w("TellLight"), LIGHT_PROPS)
    snap["silhouette_templates"] = {n: read_props(ue, tmpl_s(n), PART_PROPS) for n in ("Body", "Head")}
    snap["silhouette_defaults"] = read_props(ue, SIL_CDO, SIL_ACTOR_PROPS)
    snap["capsule"] = read_props(ue, CAPSULE, ["capsuleRadius", "capsuleHalfHeight"])
    snap["tuning_asset"] = tuning_values(ue)
    snap["sockets"] = ue.call(SK, "get_socket_names", {"mesh": pkg_ref(MESH_PKG)})
    snap["graphs"] = {"warden": list_graph_names(ue, WARDEN_PKG), "silhouette": list_graph_names(ue, SIL_PKG)}
    snap["eventgraph_dsl"] = ue.call(BPT, "read_graph_dsl", {"graph": graph_ref(WARDEN_PKG, "EventGraph")})
    snap["instances"] = {}
    for a in WARDEN_INSTANCES:
        d = {"CharacterMesh0": read_props(ue, inst(a, "CharacterMesh0"), CM_PROPS),
             "TellLight": read_props(ue, inst(a, "TellLight"), LIGHT_PROPS)}
        for n in PARTS:
            d[n] = read_props(ue, inst(a, n), PART_PROPS)
        snap["instances"][a] = d
    for a in SIL_INSTANCES:
        d = {n: read_props(ue, inst(a, n), PART_PROPS) for n in ("Body", "Head")}
        d["actor"] = read_props(ue, inst(a), SIL_ACTOR_PROPS)
        snap["instances"][a] = d
    snap["actor_count_note"] = "count is taken separately in the report (find_actors cannot count 2980 cheaply)"
    snap["dirty_before"] = {p: is_dirty(ue, p) for p in WATCH_DIRTY + SAVE_ORDER}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=1)
    cm = snap["templates"]["CharacterMesh0"]
    print("snapshot written:", path)
    print("CharacterMesh0 before: mesh", short(cm["skeletalMeshAsset"]), "| mode", cm["animationMode"], "| loc", cm["relativeLocation"],
          "| rot", cm["relativeRotation"], "| profile", cm["bodyInstance"])
    print("parts (mesh, visible, hidden, profile):",
          {n: (short(snap["templates"][n]["staticMesh"]), snap["templates"][n]["bVisible"], snap["templates"][n]["bHiddenInGame"],
               (snap["templates"][n]["bodyInstance"] or {}).get("collisionProfileName")) for n in PARTS})
    print("TellLight:", {k: snap["templates"]["TellLight"][k] for k in ("intensity", "castShadows", "bVisible", "relativeLocation")})
    print("sockets:", snap["sockets"], "| graphs:", snap["graphs"])
    print("capsule:", snap["capsule"], "| tuning asset:", snap["tuning_asset"])
    print("dirty before:", {k.split("/")[-1]: v for k, v in snap["dirty_before"].items()})
    return 0


# ------------------------------------------------------------------ the plan (live values, "P12-8 values for V5.5")
CM0_VALUES = {"skeletalMeshAsset": pkg_ref(MESH_PKG), "animationMode": "AnimationSingleNode",
              "animationData": {"animToPlay": pkg_ref(ANIM_PKG), "bSavedLooping": True, "bSavedPlaying": True},
              "relativeLocation": {"x": 0, "y": 0, "z": -110}, "relativeRotation": {"pitch": 0, "yaw": 0, "roll": 0}}
CM0_PROFILE = "NoCollision"
PART_VALUES = {"staticMesh": None, "bVisible": False, "bHiddenInGame": True}
PART_PROFILE = "NoCollision"
SIL_BODY_VALUES = {"staticMesh": pkg_ref(SIL_MESH_PKG), "relativeLocation": {"x": 0, "y": 0, "z": 0},
                   "relativeRotation": {"pitch": 0, "yaw": 90, "roll": 0}, "relativeScale3D": {"x": 1, "y": 1, "z": 1}}
SIL_HEAD_VALUES = PART_VALUES


def same(want, got):
    """Does a value read back equal the wanted one? (refs by path, None as 'None', numbers with a tolerance)"""
    if want is None:
        return got in (None, "None") or (isinstance(got, dict) and not got.get("refPath"))
    if isinstance(want, dict):
        if "refPath" in want:
            return isinstance(got, dict) and got.get("refPath") == want["refPath"]
        return isinstance(got, dict) and all(same(v, got.get(k)) for k, v in want.items())
    if isinstance(want, (bool, str)):
        return want == got
    return isinstance(got, (int, float)) and close(want, got)


def apply_values(ue, path, values, profile, label):
    """set_properties, read back, retry a vector one axis per call (MCP_NOTES 11). Returns a list of problems."""
    bad = []
    set_props(ue, path, values)
    for k, want in values.items():
        got = get1(ue, path, k)
        if not same(want, got) and isinstance(want, dict) and "refPath" not in want and all(isinstance(x, (int, float)) for x in want.values()):
            cur = dict(got) if isinstance(got, dict) else dict(want)
            for ax in want:                       # one axis per call, read back each time
                cur[ax] = want[ax]
                set_props(ue, path, {k: cur})
            got = get1(ue, path, k)
        if not same(want, got):
            bad.append(f"{label}.{k}: wanted {want}, read {got}")
    if profile:
        set_props(ue, path, {"bodyInstance": {"collisionProfileName": profile}})
        got = body_profile(ue, path)
        if got != profile:
            bad.append(f"{label}.collisionProfileName: wanted {profile}, read {got}")
    return bad


# ------------------------------------------------------------------ graph helpers (read-only except where named)
def graph_infos(ue, bp_pkg, graph):
    nodes = ue.call(BPT, "find_nodes", {"graph": graph_ref(bp_pkg, graph), "title": ""})
    return ue.call(BPT, "get_node_infos", {"nodes": nodes}) if nodes else []


def nodes_of(infos, suffix):
    return [i for i in infos if i["type_id"].endswith(suffix)]


def connected(infos_all, info, pin_name, direction):
    pins = info["output_pins"] if direction == "out" else info["input_pins"]
    out = []
    for p in pins:
        if p["name"] == pin_name:
            out += [c["node"]["refPath"] for c in p["connected_pins"]]
    return out


def pin(info, name, direction):
    for p in (info["output_pins"] if direction == "out" else info["input_pins"]):
        if p["name"] == name:
            return p
    return None


# ------------------------------------------------------------------ apply
def step_socket(ue):
    m = pkg_ref(MESH_PKG)
    names = ue.call(SK, "get_socket_names", {"mesh": m})
    if SOCKET not in names:
        ue.call(SK, "add_socket", {"mesh": m, "socket_name": SOCKET, "bone_name": BONE})
    bone = ue.call(SK, "get_socket_bone", {"mesh": m, "socket_name": SOCKET})
    t = ue.call(SK, "get_socket_transform", {"mesh": m, "socket_name": SOCKET})
    ok = bone == BONE and vec_close(t["location"], {"x": 0, "y": 0, "z": 0}) and rot_close(t["rotation"], {"pitch": 0, "yaw": 0, "roll": 0}) \
        and vec_close(t["scale"], {"x": 1, "y": 1, "z": 1})
    print(f"  socket {SOCKET} on bone {bone}, zero offset {'ok' if ok else 'MISMATCH'} (sockets: {ue.call(SK, 'get_socket_names', {'mesh': m})})", flush=True)
    return [] if ok else ["socket"]


def step_templates(ue):
    bad = apply_values(ue, CM0, CM0_VALUES, CM0_PROFILE, "BP_Warden.CharacterMesh0")
    for n in PARTS:
        bad += apply_values(ue, tmpl_w(n), PART_VALUES, PART_PROFILE, f"BP_Warden.{n}")
    print("  BP_Warden templates:", "ok" if not bad else bad, flush=True)
    return bad


def compile_bp(ue, pkg):
    """Compile with warnings visible: warnings_as_errors raises on any warning or error."""
    try:
        ue.call(BPT, "compile_blueprint", {"blueprint": pkg_ref(pkg), "warnings_as_errors": True})
    except Exception as e:  # noqa: BLE001
        print(f"  compile {pkg.split('/')[-1]}: FAILED or has warnings: {str(e)[:900]}", flush=True)
        return False
    print(f"  compile {pkg.split('/')[-1]}: ok (no errors, no warnings)", flush=True)
    return True


def step_graph(ue):
    """AttachTellLightToMask function (one AttachComponentToComponent node) + one call node after BindtoBrain on BeginPlay."""
    bad = []
    if FN_NAME not in list_graph_names(ue, WARDEN_PKG):
        ue.call(BPT, "add_function_graph", {"blueprint": pkg_ref(WARDEN_PKG), "graph_name": FN_NAME})
    fn = graph_infos(ue, WARDEN_PKG, FN_NAME)
    if not nodes_of(fn, "AttachComponentToComponent"):
        code = (f"(fn {FN_NAME} ()\n  (Transformation|AttachComponentToComponent\n    (Variables|Default|GetTellLight)\n"
                f"    (Variables|Character|GetMesh)\n    :SocketName \"{SOCKET}\"\n    :LocationRule \"SnapToTarget\"\n"
                "    :RotationRule \"SnapToTarget\"\n    :ScaleRule \"SnapToTarget\"\n    :bWeldSimulatedBodies false))\n")
        ue.call(BPT, "write_graph_dsl", {"graph": graph_ref(WARDEN_PKG, FN_NAME), "code": code})
        fn = graph_infos(ue, WARDEN_PKG, FN_NAME)
    if len(nodes_of(fn, "AttachComponentToComponent")) != 1:
        bad.append(f"{FN_NAME}: {len(nodes_of(fn, 'AttachComponentToComponent'))} attach nodes")
    eg = graph_infos(ue, WARDEN_PKG, "EventGraph")
    calls = nodes_of(eg, "|" + FN_NAME)
    if not calls:
        begin = nodes_of(eg, "AddEvent|EventBeginPlay")
        if len(begin) != 1:
            return bad + [f"EventGraph has {len(begin)} BeginPlay events"]
        first = connected(eg, begin[0], "then", "out")
        bind = [i for i in eg if i["node"]["refPath"] in first]
        if len(bind) != 1 or not bind[0]["type_id"].endswith("|BindToBrain"):
            return bad + [f"BeginPlay does not lead to BindToBrain as expected: {first}"]
        bind = bind[0]
        if connected(eg, bind, "then", "out"):
            return bad + ["BindToBrain already continues somewhere; refusing to splice"]
        n = ue.call(BPT, "create_node", {"graph": graph_ref(WARDEN_PKG, "EventGraph"), "type_id": "CallFunction|AttachTellLighttoMask",
                                         "pos": {"x": 560, "y": 0}})
        out_pin = pin(bind, "then", "out")["pin_id"]
        in_info = ue.call(BPT, "get_node_infos", {"nodes": [n]})[0]
        ue.call(BPT, "connect_pins", {"output_pin": out_pin, "input_pin": pin(in_info, "execute", "in")["pin_id"]})
    eg = graph_infos(ue, WARDEN_PKG, "EventGraph")
    calls = nodes_of(eg, "|" + FN_NAME)
    if len(calls) != 1:
        bad.append(f"EventGraph has {len(calls)} calls of {FN_NAME}")
    print("  graph:", "ok" if not bad else bad, flush=True)
    return bad


def step_silhouette(ue):
    bad = apply_values(ue, tmpl_s("Body"), SIL_BODY_VALUES, None, "BP_WardenSilhouette.Body")
    bad += apply_values(ue, tmpl_s("Head"), SIL_HEAD_VALUES, None, "BP_WardenSilhouette.Head")
    print("  BP_WardenSilhouette templates:", "ok" if not bad else bad, flush=True)
    return bad


def step_instances(ue):
    """Make the placed instances of the CURRENT level equal the new templates (only where they differ). Never saves."""
    bad = []
    for a in WARDEN_INSTANCES:
        bad += apply_values(ue, inst(a, "CharacterMesh0"), CM0_VALUES, CM0_PROFILE, f"{a}.CharacterMesh0")
        for n in PARTS:
            bad += apply_values(ue, inst(a, n), PART_VALUES, PART_PROFILE, f"{a}.{n}")
    for a in SIL_INSTANCES:
        bad += apply_values(ue, inst(a, "Body"), SIL_BODY_VALUES, None, f"{a}.Body")
        bad += apply_values(ue, inst(a, "Head"), SIL_HEAD_VALUES, None, f"{a}.Head")
    print("  placed instances (in memory, current level):", "ok" if not bad else bad, flush=True)
    return bad


def do_apply(ue, snap_path):
    if not level_ok(ue):
        print(f"REFUSED: the current level is not {MAP_PKG}")
        return 1
    if not os.path.exists(snap_path):
        print(f"REFUSED: no snapshot at {snap_path}; run --snapshot first")
        return 1
    for pkg in (MESH_PKG, ANIM_PKG, SIL_MESH_PKG, WARDEN_PKG, SIL_PKG):
        if not ue.call(AS, "exists", {"path": pkg}):
            print(f"REFUSED: {pkg} does not exist")
            return 1
    bad = []
    bad += step_socket(ue)
    bad += step_templates(ue)
    bad += step_graph(ue)
    ok_w = compile_bp(ue, WARDEN_PKG)
    bad += step_silhouette(ue)
    ok_s = compile_bp(ue, SIL_PKG)
    # compiling can reset what was just written: read the templates again
    bad += [b + " (after compile)" for b in verify_templates(ue)]
    bad += step_instances(ue)
    print("apply:", "OK" if not bad and ok_w and ok_s else f"PROBLEMS {bad}; compile warden {ok_w}, silhouette {ok_s}")
    return 0 if not bad and ok_w and ok_s else 1


def verify_templates(ue):
    bad = []
    for path, vals, prof, label in [(CM0, CM0_VALUES, CM0_PROFILE, "CharacterMesh0")] + \
            [(tmpl_w(n), PART_VALUES, PART_PROFILE, n) for n in PARTS] + \
            [(tmpl_s("Body"), SIL_BODY_VALUES, None, "Silhouette.Body"), (tmpl_s("Head"), SIL_HEAD_VALUES, None, "Silhouette.Head")]:
        for k, want in vals.items():
            got = get1(ue, path, k)
            if not same(want, got):
                bad.append(f"{label}.{k}: wanted {want}, read {got}")
        if prof and body_profile(ue, path) != prof:
            bad.append(f"{label}.collisionProfileName: read {body_profile(ue, path)}")
    return bad


# ------------------------------------------------------------------ check (the full list lives in check_warden.py --bp)
def do_check(ue, snap_path):
    sys.path.insert(0, os.path.join(ROOT, "Tools", "warden"))
    import check_warden  # noqa: E402
    res = check_warden.Result()
    check_warden.check_bp(ue, res, None, snap_path)
    print("%d/%d" % (res.passed, res.total))
    return 0 if res.passed == res.total else 1


# ------------------------------------------------------------------ save
def do_save(ue):
    dirty_before = {p: is_dirty(ue, p) for p in SAVE_ORDER + NEVER_SAVE}
    print("not saved on purpose:", {p.split("/")[-1]: dirty_before[p] for p in NEVER_SAVE})
    for i, pkg in enumerate(SAVE_ORDER):
        assert pkg not in NEVER_SAVE and "/Master/" not in pkg and "/Maps/" not in pkg
        if i:
            time.sleep(PAUSE_S)
        res = ue.call(AS, "save_assets", {"asset_paths": [pkg]})
        dirty = is_dirty(ue, pkg)
        print(f"  save {pkg.split('/')[-1]}: was dirty {dirty_before[pkg]}, returned {res}, is_dirty {dirty}", flush=True)
        if res is not True or dirty is not False:
            print(f"STOP: {pkg} did not save cleanly; later packages were not saved.")
            return 1
    after = {p.split("/")[-1]: is_dirty(ue, p) for p in WATCH_DIRTY}
    print("dirty after save (watch list):", sorted(k for k, v in after.items() if v) or "none")
    return 0


# ------------------------------------------------------------------ restore
def snap_values(rec, keys):
    return {k: rec[k] for k in keys if k in rec and rec[k] != "n/a"}


def do_restore(ue, snap_path):
    with open(snap_path, encoding="utf-8") as f:
        snap = json.load(f)
    bad = []
    # 1. graph: call node first, then the function
    eg = graph_infos(ue, WARDEN_PKG, "EventGraph")
    for c in nodes_of(eg, "|" + FN_NAME):
        ue.call(BPT, "delete_node", {"node": c["node"]})
    if FN_NAME in list_graph_names(ue, WARDEN_PKG):
        ue.call(BPT, "remove_function_graph", {"blueprint": pkg_ref(WARDEN_PKG), "graph_name": FN_NAME})
    # 2. templates and instances
    def put(path, rec, keys):
        v = snap_values(rec, keys)
        prof = (rec.get("bodyInstance") or {}).get("collisionProfileName") if isinstance(rec.get("bodyInstance"), dict) else None
        set_props(ue, path, v)
        if prof:
            set_props(ue, path, {"bodyInstance": {"collisionProfileName": prof}})
    cm_keys = ["skeletalMeshAsset", "animationMode", "animationData", "relativeLocation", "relativeRotation"]
    put(CM0, snap["templates"]["CharacterMesh0"], cm_keys)
    for n in PARTS:
        put(tmpl_w(n), snap["templates"][n], ["staticMesh", "bVisible", "bHiddenInGame"])
    sil_keys = ["staticMesh", "relativeLocation", "relativeRotation", "relativeScale3D", "bVisible", "bHiddenInGame"]
    for n in ("Body", "Head"):
        put(tmpl_s(n), snap["silhouette_templates"][n], sil_keys)
    for a, d in snap["instances"].items():
        if a in WARDEN_INSTANCES:
            put(inst(a, "CharacterMesh0"), d["CharacterMesh0"], cm_keys)
            for n in PARTS:
                put(inst(a, n), d[n], ["staticMesh", "bVisible", "bHiddenInGame"])
        else:
            for n in ("Body", "Head"):
                put(inst(a, n), d[n], sil_keys)
    compile_bp(ue, WARDEN_PKG)
    compile_bp(ue, SIL_PKG)
    # 3. socket
    if SOCKET in ue.call(SK, "get_socket_names", {"mesh": pkg_ref(MESH_PKG)}):
        ue.call(SK, "remove_socket", {"mesh": pkg_ref(MESH_PKG), "socket_name": SOCKET})
    print("restore: socket now", ue.call(SK, "get_socket_names", {"mesh": pkg_ref(MESH_PKG)}),
          "| graphs", list_graph_names(ue, WARDEN_PKG), "(nothing saved; run the snapshot check to see the rest)")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", metavar="FILE")
    for m in ("apply", "check", "save", "restore"):
        g.add_argument("--" + m, action="store_true")
    ap.add_argument("--snap-file", default=DEFAULT_SNAP)
    a = ap.parse_args()
    ue = UE()
    try:
        if refuse_if_pie(ue):
            return 1
        if a.snapshot:
            return do_snapshot(ue, a.snapshot)
        if a.apply:
            return do_apply(ue, a.snap_file)
        if a.restore:
            return do_restore(ue, a.snap_file)
        if a.check:
            return do_check(ue, a.snap_file)
        return do_save(ue)
    except Exception as e:  # noqa: BLE001
        print(f"TOOL CALL FAILED: {str(e)[:600]}\nState unknown. Run --check before doing anything else; do not retry in a loop.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
