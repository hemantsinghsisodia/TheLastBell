"""P17-5a-1: build the two real cinematics headless (Unreal CLOSED). Spec: Docs/plans/P17_CINEMATICS.md sections 3.1, 3.2b (replaces 3.2), 2.1.
Recipes come from the S1 spike (Tools/cine/p17_s1_spike.py, Docs/ArtTest/cine/p17_s1.json "findings").

Run (editor closed, never two at once):
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>
Environment:
    P17_MODE     build | check
    P17_REBUILD  1 = reset LS_LB_Intro and LS_LB_Finale in place and rebuild them (default: build refuses to touch an existing one)
    P17_ONLY     Intro | Finale = build (and save) only that sequence; the other is not touched. Finale = 3.2b (owner revision 2026-11-11)
Build creates /Game/LastBell/Cinematics/LS_LB_Intro and LS_LB_Finale and saves ONLY those two packages (explicit save_asset).
Check runs in a FRESH process, reads everything back and writes Docs/ArtTest/cine/p17_5a_check.json.
Nothing else is saved. No PIE, no MCP.
"""
import glob
import json
import math
import os
import random
import re
import time
import traceback

import unreal

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
CINE_DIR = "/Game/LastBell/Cinematics"
INTRO_PATH = CINE_DIR + "/LS_LB_Intro"
FINALE_PATH = CINE_DIR + "/LS_LB_Finale"
OUT_JSON = os.path.join(ROOT, "Docs", "ArtTest", "cine", "p17_5a_check.json")
BUILD_RECORD = os.path.join(ROOT, "Saved", "p17_5a_build.json")
AUDIO_ROOT = os.path.join(ROOT, "Content", "LastBell", "Audio")

SK_PATH = "/Game/LastBell/Characters/Warden/Meshes/SK_Warden"
SKEL_PATH = "/Game/LastBell/Characters/Warden/Meshes/SK_Warden_Skeleton"
ABP_CLASS_PATH = "/Game/LastBell/Characters/Warden/ABP_Warden.ABP_Warden_C"
APPARITION_BP = "/Game/LastBell/Blueprints/Interactables/BP_WardenApparition"
MASKVIEW_MI = "/Game/LastBell/Materials/PostProcess/MI_LB_PP_MaskView"

FPS = 30
TPS = 24000          # tick resolution
MODE = os.environ.get("P17_MODE", "").lower()
REBUILD = os.environ.get("P17_REBUILD", "0") == "1"
TAG = "P17Seq"
EAL = unreal.EditorAssetLibrary

results = {"mode": MODE, "started": time.strftime("%Y-%m-%d %H:%M:%S"), "calls": 0, "errors": [], "notes": [], "saved": []}


# ================================================================================================================ helpers
def log(msg):
    unreal.log("%s: %s" % (TAG, msg))


def note(text):
    results["notes"].append(text)
    log("NOTE " + text)


def short(v, n=200):
    try:
        t = repr(v)
    except Exception as exc:  # noqa: BLE001
        t = "<repr failed %s>" % exc
    return t if len(t) <= n else t[:n] + "..."


def call(item, label, fn, *a, quiet=False, **k):
    """(ok, value). Logs the call (unless quiet), records errors."""
    results["calls"] += 1
    try:
        v = fn(*a, **k)
        if not quiet:
            log("CALL [%s] %s -> %s" % (item, label, short(v, 160)))
        return True, v
    except Exception as exc:  # noqa: BLE001
        msg = "%s: %s" % (type(exc).__name__, str(exc).strip().replace("\n", " | "))
        unreal.log_warning("%s: CALL FAILED [%s] %s -> %s" % (TAG, item, label, msg))
        results["errors"].append({"item": item, "api": label, "error": msg})
        return False, None


def tk(sec):
    return int(round(sec * TPS))


def fnum(ticks):
    return unreal.FrameNumber(int(ticks))


def en(e):
    return getattr(e, "name", str(e))


def guid_str(g):
    return None if g is None else str(g.to_string())


def clsname(o):
    try:
        return o.get_class().get_name()
    except Exception:  # noqa: BLE001
        return type(o).__name__


def chan_name(c):
    v = getattr(c, "channel_name", None)
    if callable(v):
        v = v()
    return str(v)


INTERP = {"A": unreal.MovieSceneKeyInterpolation.AUTO, "L": unreal.MovieSceneKeyInterpolation.LINEAR}
TU = unreal.MovieSceneTimeUnit.TICK_RESOLUTION


def add_keys(item, label, ch, keys, is_bool=False):
    """keys = [(seconds, value, 'A'|'L')]; exact tick times."""
    n = 0
    for sec, val, mode in keys:
        if is_bool:
            ok, _ = call(item, label, ch.add_key, fnum(tk(sec)), bool(val), 0.0, TU, quiet=True)
        else:
            ok, _ = call(item, label, ch.add_key, fnum(tk(sec)), float(val), 0.0, TU, INTERP[mode], quiet=True)
        n += 1 if ok else 0
    log("KEYS [%s] %s: %d/%d keys added" % (item, label, n, len(keys)))
    return n


_SND = {}


def sound_path(name):
    if name not in _SND:
        hits = glob.glob(os.path.join(AUDIO_ROOT, "**", name + ".uasset"), recursive=True)
        if len(hits) != 1:
            raise RuntimeError("sound %s: %d matches under Content/LastBell/Audio" % (name, len(hits)))
        _SND[name] = "/Game/LastBell/Audio/" + os.path.relpath(hits[0], AUDIO_ROOT).replace("\\", "/")[:-7]
    return _SND[name]


def load_sound(name):
    return unreal.load_asset(sound_path(name))


def audio_end(snd, start, pitch, loop, end, seq_end):
    """Section end: the stated end for loops, else start + duration / pitch (pitch changes the playback length), clamped to the sequence."""
    if end is not None:
        return end
    dur = float(snd.get_editor_property("duration"))
    return min(seq_end, start + dur / pitch)


# ================================================================================================================ read-only facts
def read_mesh_facts():
    """MeshYaw (relative yaw of BP_WardenApparition's skeletal mesh component), its relative location and scale, SK_Warden bounds and head Z."""
    f = {"errors": []}
    try:
        bp = unreal.load_asset(APPARITION_BP)
        cdo = unreal.get_default_object(bp.generated_class())
        comps = []
        for c in cdo.get_components_by_class(unreal.SkeletalMeshComponent):
            rl = c.get_editor_property("relative_location")
            rr = c.get_editor_property("relative_rotation")
            rs = c.get_editor_property("relative_scale3d")
            m = c.get_editor_property("skeletal_mesh_asset")
            comps.append({"name": c.get_name(), "rel_loc": [rl.x, rl.y, rl.z], "rel_rot_pyr": [rr.pitch, rr.yaw, rr.roll], "rel_scale": [rs.x, rs.y, rs.z],
                          "mesh": m.get_name() if m else None})
        f["apparition_skeletal_components"] = comps
        figure = [c for c in comps if c["name"] == "Figure"] or comps
        f["mesh_yaw"] = float(figure[0]["rel_rot_pyr"][1])
        f["mesh_rel_loc"] = figure[0]["rel_loc"]
        f["mesh_rel_scale"] = figure[0]["rel_scale"]
    except Exception as exc:  # noqa: BLE001
        f["errors"].append("apparition CDO: %s" % exc)
        f["mesh_yaw"] = 0.0
    try:
        mesh = unreal.load_asset(SK_PATH)
        b = mesh.get_bounds()
        f["sk_bounds_min_z"] = float(b.origin.z - b.box_extent.z)
        skel = unreal.load_asset(SKEL_PATH)
        pose = unreal.AnimPoseExtensions.get_reference_pose(skel)
        head = unreal.AnimPoseExtensions.get_bone_pose(pose, "head", unreal.AnimPoseSpaces.WORLD)
        f["head_z"] = float(head.translation.z)
    except Exception as exc:  # noqa: BLE001
        f["errors"].append("SK_Warden: %s" % exc)
        f["head_z"] = 239.365074
    return f


# ================================================================================================================ the spec
def single(v, mode="L"):
    return [(0.0, v, mode)]


def xf_channels(lx, ly, lz, rr, rp, ry):
    return {"lx": lx, "ly": ly, "lz": lz, "rr": rr, "rp": rp, "ry": ry}


def fixed_xf(loc, yaw=0.0, pitch=0.0, roll=0.0):
    return xf_channels(single(loc[0]), single(loc[1]), single(loc[2]), single(roll), single(pitch), single(yaw))


CAM_TPL = {"focal": 35.0, "aperture": None, "focus": None, "constrain": False, "pps": False}


def spec_intro():
    cam = {"name": "Cam_Intro", "cls": "CineCameraActor",
           "tpl": {"focal": 30.0, "aperture": 2.8, "focus": 6000.0, "constrain": False, "pps": False},
           "xf": xf_channels(lx=[(13.0, -2800.0, "A"), (27.0, -2800.0, "A")], ly=[(13.0, 0.0, "A"), (27.0, 0.0, "A")],
                             lz=[(13.0, 652.79, "A"), (27.0, 152.79, "A")], rr=[(13.0, 0.0, "A"), (27.0, 0.0, "A")],
                             rp=[(13.0, 6.0, "A"), (27.0, 0.0, "A")], ry=[(13.0, 0.0, "A"), (27.0, 0.0, "A")]),
           "vis": None,
           "comps": [{"comp": "camera_component", "tracks": [{"prop": "CurrentFocalLength", "path": "CurrentFocalLength",
                                                              "keys": [(13.0, 30.0, "A"), (27.0, 28.0, "A")]}]}],
           "audio": []}
    return {"key": "Intro", "path": INTRO_PATH, "end": 29.0,
            "markers": [("skip:1", 0.0), ("card:Intro_1", 0.8), ("card:Intro_2", 3.8), ("card:Intro_3", 6.8), ("card:Intro_4", 9.8),
                        ("strike:LB_StrikeTarget_Tower,1.0", 17.0), ("!tag:State.Event.Arrival", 17.4), ("card:Title", 19.0), ("!lock:None", 27.5)],
            "fade": [(0.0, 1.0), (13.0, 1.0), (15.5, 0.0)],
            "cuts": [{"binding": "Cam_Intro", "start": 13.0, "end": 27.0, "ease_in": 0.0, "ease_out": 1.5}],
            "bindings": [cam], "audio2d": []}


# 3.2b (owner finale revision, 2026-11-11): the figure is in sight about 3.5 s after the ring; playback 0-97.5 s
WARDEN_LOC = [(0.0, (12730.0, 1665.0, 2272.73)), (1.0, (12730.0, 1665.0, 2272.73)), (1.351, (12695.0, 1665.0, 2288.96)),
              (5.382, (12305.0, 1665.0, 2500.0)), (6.655, (12165.0, 1665.0, 2500.0)), (11.519, (12165.0, 2200.0, 2500.0))]
WARDEN_YAW = [(0.0, -180.0), (6.405, -180.0), (6.905, -270.0)]
LANTERN_T0 = 23.5     # the lantern walk starts here (was 76.0 in 3.2)


def spec_finale(facts):
    mesh_yaw = facts["mesh_yaw"]
    # 3.2b: Cam_Mask looks at the head point (12165, 2200, 2739) from (12165, 2420, 2700): pitch = atan2(39, 220), the spec's own numbers
    mask_pitch = math.degrees(math.atan2(39.0, 220.0))
    facts["cam_mask_pitch"] = mask_pitch
    warden = {"name": "WardenFigure", "cls": "SkeletalMeshActor", "tpl": {},
              "xf": xf_channels(lx=[(t, p[0], "L") for t, p in WARDEN_LOC], ly=[(t, p[1], "L") for t, p in WARDEN_LOC],
                                lz=[(t, p[2], "L") for t, p in WARDEN_LOC], rr=single(0.0), rp=single(0.0),
                                ry=[(t, y + mesh_yaw, "L") for t, y in WARDEN_YAW]),
              "vis": [(0.0, False), (1.351, True), (21.5, False)], "comps": [], "audio": []}
    a = warden["audio"]
    for k in range(8):
        t = round(1.0 + 1.36 * k, 3)
        a.append({"sound": "SFX_LB_Step_Wood_0%d" % ((k % 6) + 1), "start": t, "pitch": 0.7})
        if k % 2 == 0:
            a.append({"sound": "SFX_LB_Warden_Chain_0%d" % (((k // 2) % 4) + 1), "start": t})
    a.append({"sound": "SFX_LB_Warden_Breath_Heavy", "start": 1.0, "end": 19.5, "loop": True})

    cam_mask = {"name": "Cam_Mask", "cls": "CineCameraActor", "tpl": {"focal": 35.0, "aperture": None, "focus": None, "constrain": False, "pps": False},
                "xf": fixed_xf((12165.0, 2420.0, 2700.0), yaw=-90.0, pitch=mask_pitch), "vis": None,
                "comps": [{"comp": "camera_component", "tracks": [{"prop": "ManualFocusDistance", "path": "FocusSettings.ManualFocusDistance",
                                                                   "keys": [(13.0, 220.0, "A"), (18.5, 200.0, "A")]}]}], "audio": []}
    cam_wall = {"name": "Cam_WallTop", "cls": "CineCameraActor", "tpl": {"focal": 35.0, "aperture": None, "focus": 6000.0, "constrain": False, "pps": True},
                "xf": fixed_xf((6020.0, 1300.0, 1032.0), yaw=-167.51, pitch=-7.88), "vis": None, "comps": [], "audio": []}

    # Lantern (3.2b: everything of 3.2 shifted so that the walk starts at 23.5 s)
    t0 = LANTERN_T0
    zk, ik = [], []
    for k in range(141):
        t = round(t0 + 0.1 * k, 3)
        u = t - t0
        base_z = 110.88 + (110.53 - 110.88) * u / 14.0
        amp = 3.0 if t <= t0 + 12.5 + 1e-9 else 3.0 * max(0.0, (t0 + 14.0 - t) / 1.5)
        zk.append((t, base_z + amp * math.sin(2 * math.pi * 1.1 * u), "A"))
    rng = random.Random(1717)
    for k in range(205):
        ik.append((t0 + k / 12.0, 600.0 * (1.0 + 0.08 * rng.uniform(-1, 1)), "L"))
    lantern = {"name": "Lantern", "cls": "PointLight", "tpl": {},
               "xf": xf_channels(lx=[(t0, -600.0, "L"), (36.0, 204.0, "A"), (37.5, 250.0, "A")], ly=single(0.0), lz=zk, rr=single(0.0), rp=single(0.0), ry=single(0.0)),
               "vis": [(0.0, False), (t0, True)],
               "comps": [{"comp": "light_component", "tracks": [{"prop": "Intensity", "path": "Intensity", "keys": ik}]}], "audio": []}

    audio2d = [{"sound": "SFX_LB_Step_Metal_02", "start": 19.5, "pitch": 0.55}, {"sound": "SFX_LB_Warden_Chain_02", "start": 19.5, "pitch": 0.7},
               {"sound": "SFX_LB_Warden_Breath_Slow", "start": 19.8, "end": 39.5, "loop": True}]
    markers = [("mark:LB_Cine_FinaleMark,1.2", 0.0), ("lock:Look", 1.3), ("look:LB_Cine_StairTop,1.0", 1.5), ("flash:1.0", 3.6),
               ("look:LB_Cine_Warden,1.0", 9.5), ("lock:Full", 12.0), ("bell:5x1", 33.5), ("mix:on", 37.5), ("card:End_1", 41.5),
               ("card:End_2", 47.5), ("skip:1", 53.5), ("credits:40", 53.5 + 1.0 / FPS), ("!end", 94.5)]
    return {"key": "Finale", "path": FINALE_PATH, "end": 97.5, "markers": markers,
            "fade": [(0.0, 0.0), (19.5, 0.0), (19.8, 1.0), (22.5, 1.0), (24.5, 0.0), (38.5, 0.0), (40.5, 1.0)],
            "cuts": [{"binding": "Cam_Mask", "start": 12.5, "end": 22.5, "ease_in": 0.8, "ease_out": 0.0},
                     {"binding": "Cam_WallTop", "start": 22.5, "end": 97.5, "ease_in": 0.0, "ease_out": 0.0}],
            "bindings": [warden, cam_mask, cam_wall, lantern], "audio2d": audio2d}


MARKER_RE = re.compile(r"^!?(skip:[01]|card:\w+|tag:[A-Za-z0-9_.]+|bell:\d+x\d+|strike:[\w]+(,[0-9.]+)?|flash:[0-9.]+|look:\w+(,[0-9.]+)?|mark:\w+(,[0-9.]+)?|"
                       r"lock:(None|Look|Full)|mix:(on|off)|credits(:\d+)?|end)$")


# ================================================================================================================ BUILD
WORLD = {"w": None, "tried": False}


def get_world(item):
    if WORLD["w"] is not None or WORLD["tried"]:
        return WORLD["w"]
    WORLD["tried"] = True
    for label, fn in (("UnrealEditorSubsystem.get_editor_world()", lambda: unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()),
                      ("EditorLevelLibrary.get_editor_world() [deprecated]", unreal.EditorLevelLibrary.get_editor_world)):
        ok, w = call(item, label, fn)
        if ok and w is not None:
            WORLD["w"] = w
            return w
    return None


def component_binding(item, seq, actor_binding, cls, prop):
    """Child possessable for a component of a spawnable (S1 recipe): spawn through a player in the editor world, add_possessable(<live component>)."""
    world = get_world(item)
    if world is None:
        return None
    ok, res = call(item, "LevelSequencePlayer.create_level_sequence_player", unreal.LevelSequencePlayer.create_level_sequence_player, world, seq,
                   unreal.MovieSceneSequencePlaybackSettings())
    if not ok or res is None:
        return None
    player = res[0] if isinstance(res, (tuple, list)) else res
    call(item, "player.set_playback_position(frame 0, JUMP)", player.set_playback_position,
         unreal.MovieSceneSequencePlaybackParams(frame=unreal.FrameTime(unreal.FrameNumber(0)), position_type=unreal.MovieScenePositionType.FRAME,
                                                  update_method=unreal.UpdatePositionMethod.JUMP))
    ok, bid = call(item, "LevelSequence.get_binding_id(binding)", seq.get_binding_id, actor_binding)
    actor = None
    if ok:
        ok, objs = call(item, "player.get_bound_objects(binding id)", player.get_bound_objects, bid)
        if ok and objs:
            actor = list(objs)[0]
    if actor is None:
        note("component binding %s.%s: the spawnable did not spawn" % (actor_binding.get_name(), prop))
        return None
    live = actor.get_editor_property(prop)
    ok, nb = call(item, "LevelSequence.add_possessable(<live %s of %s>)" % (prop, actor.get_name()), seq.add_possessable, live)
    call(item, "player.stop()", player.stop)
    return nb if ok and nb is not None and nb.is_valid() else None


def reset_sequence(seq):
    for b in list(seq.get_bindings()):
        try:
            b.remove()
        except Exception as exc:  # noqa: BLE001
            note("reset: binding remove failed: %s" % exc)
    for t in list(seq.get_tracks()):
        try:
            seq.remove_track(t)
        except Exception as exc:  # noqa: BLE001
            note("reset: track remove failed: %s" % exc)
    try:
        seq.delete_marked_frames()
    except Exception as exc:  # noqa: BLE001
        note("reset: marked frames: %s" % exc)


def add_spawnable(item, seq, cls):
    return call(item, "LevelSequence.add_spawnable_from_class(%s) [deprecated since 5.5, the only headless route]" % cls.__name__, seq.add_spawnable_from_class, cls)


def set_template(item, cls_name, tpl, binding):
    t = binding.get_object_template()
    if t is None:
        return
    if cls_name == "CineCameraActor":
        comp = t.get_editor_property("camera_component")
        call(item, "CineCameraComponent.set_filmback_preset_by_name('16:9 DSLR')", comp.set_filmback_preset_by_name, "16:9 DSLR")
        call(item, "set current_focal_length", comp.set_editor_property, "current_focal_length", float(tpl["focal"]))
        call(item, "set constrain_aspect_ratio False", comp.set_editor_property, "constrain_aspect_ratio", bool(tpl["constrain"]))
        if tpl.get("aperture") is not None:
            call(item, "set current_aperture", comp.set_editor_property, "current_aperture", float(tpl["aperture"]))
        if tpl.get("focus") is not None:
            fs = comp.get_editor_property("focus_settings")
            fs.set_editor_property("focus_method", unreal.CameraFocusMethod.MANUAL)
            fs.set_editor_property("manual_focus_distance", float(tpl["focus"]))
            call(item, "set focus_settings (MANUAL, %.0f cm)" % tpl["focus"], comp.set_editor_property, "focus_settings", fs)
        if tpl.get("pps"):
            mi = unreal.load_asset(MASKVIEW_MI)
            pps = comp.get_editor_property("post_process_settings")
            wb = pps.get_editor_property("weighted_blendables")
            wb.set_editor_property("array", [unreal.WeightedBlendable(weight=1.0, object=mi)])
            pps.set_editor_property("weighted_blendables", wb)
            call(item, "set post_process_settings.weighted_blendables = [MI_LB_PP_MaskView, 1.0]", comp.set_editor_property, "post_process_settings", pps)
            call(item, "set post_process_blend_weight 1", comp.set_editor_property, "post_process_blend_weight", 1.0)
    elif cls_name == "SkeletalMeshActor":
        smc = t.get_editor_property("skeletal_mesh_component")
        mesh = unreal.load_asset(SK_PATH)
        abp = unreal.load_class(None, ABP_CLASS_PATH)
        call(item, "set_skeletal_mesh_asset(SK_Warden)", smc.set_skeletal_mesh_asset, mesh)
        call(item, "set_animation_mode(ANIMATION_BLUEPRINT)", smc.set_animation_mode, unreal.AnimationMode.ANIMATION_BLUEPRINT)
        call(item, "set_anim_instance_class(ABP_Warden_C)", smc.set_anim_instance_class, abp)
        call(item, "set visibility_based_anim_tick_option ALWAYS_TICK_POSE", smc.set_editor_property, "visibility_based_anim_tick_option",
             unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE)
        call(item, "set_collision_enabled(NO_COLLISION)", smc.set_collision_enabled, unreal.CollisionEnabled.NO_COLLISION)
        call(item, "set_collision_profile_name('NoCollision')", smc.set_collision_profile_name, "NoCollision")
        call(item, "set cast_shadow True", smc.set_editor_property, "cast_shadow", True)
        call(item, "set actor tags [LB_Cine_Warden]", t.set_editor_property, "tags", [unreal.Name("LB_Cine_Warden")])
    elif cls_name == "PointLight":
        lc = t.get_editor_property("light_component")
        call(item, "set intensity_units LUMENS", lc.set_editor_property, "intensity_units", unreal.LightUnits.LUMENS)
        call(item, "set intensity 600", lc.set_editor_property, "intensity", 600.0)
        call(item, "set light_color (255,150,70)", lc.set_editor_property, "light_color", unreal.Color(r=255, g=150, b=70, a=255))
        call(item, "set attenuation_radius 650", lc.set_editor_property, "attenuation_radius", 650.0)
        call(item, "set source_radius 2", lc.set_editor_property, "source_radius", 2.0)
        call(item, "set cast_shadows True", lc.set_editor_property, "cast_shadows", True)


def build_transform(item, spec, binding, end_s):
    ok, track = call(item, "add_track(MovieScene3DTransformTrack)", binding.add_track, unreal.MovieScene3DTransformTrack)
    if not ok:
        return
    ok, sec = call(item, "add_section()", track.add_section)
    if not ok:
        return
    call(item, "set_range_seconds(0,%s)" % end_s, sec.set_range_seconds, 0.0, float(end_s))
    ok, chs = call(item, "get_all_channels()", sec.get_all_channels)
    byname = {chan_name(c): c for c in chs}
    log("transform channels: %s" % sorted(byname))
    order = {"lx": "Location.X", "ly": "Location.Y", "lz": "Location.Z", "rr": "Rotation.X", "rp": "Rotation.Y", "ry": "Rotation.Z"}
    for k, nm in order.items():
        add_keys(item, "transform %s (%s)" % (k, nm), byname[nm], spec["xf"][k])
    for nm in ("Scale.X", "Scale.Y", "Scale.Z"):
        add_keys(item, "transform %s" % nm, byname[nm], [(0.0, 1.0, "L")])


def build_vis(item, vis, binding, end_s):
    ok, track = call(item, "add_track(MovieSceneVisibilityTrack)", binding.add_track, unreal.MovieSceneVisibilityTrack)
    if not ok:
        return
    call(item, "set_property_name_and_path('bHidden')", track.set_property_name_and_path, unreal.Name("bHidden"), "bHidden")
    ok, sec = call(item, "add_section()", track.add_section)
    call(item, "set_range_seconds", sec.set_range_seconds, 0.0, float(end_s))
    ok, chs = call(item, "get_all_channels()", sec.get_all_channels)
    add_keys(item, "visibility (True = visible)", chs[0], [(t, v, "L") for t, v in vis], is_bool=True)


def build_audio_sections(item, track, entries, seq_end):
    """Each entry becomes a section; rows are allocated so no two sections of a row overlap."""
    row_end = []
    for e in entries:
        snd = load_sound(e["sound"])
        pitch = float(e.get("pitch", 1.0))
        loop = bool(e.get("loop", False))
        start = float(e["start"])
        end = audio_end(snd, start, pitch, loop, e.get("end"), seq_end)
        ok, sec = call(item, "add_section() [audio %s]" % e["sound"], track.add_section, quiet=True)
        if not ok:
            continue
        call(item, "set_sound", sec.set_sound, snd, quiet=True)
        call(item, "set_range_seconds(%.4f,%.4f)" % (start, end), sec.set_range_seconds, start, end, quiet=True)
        row = None
        for i, re_ in enumerate(row_end):
            if re_ <= start + 1e-6:
                row = i
                break
        if row is None:
            row = len(row_end)
            row_end.append(0.0)
        row_end[row] = end
        call(item, "set_row_index(%d)" % row, sec.set_row_index, row, quiet=True)
        if loop:
            call(item, "set_looping(True)", sec.set_looping, True, quiet=True)
        ok, chs = call(item, "get_all_channels() [audio]", sec.get_all_channels, quiet=True)
        if ok and pitch != 1.0:
            call(item, "pitch channel set_default(%s)" % pitch, chs[1].set_default, pitch, quiet=True)
        if ok and e.get("vol"):
            add_keys(item, "volume keys %s" % e["sound"], chs[0], e["vol"])
        log("AUDIO [%s] %s start %.3f end %.3f row %d pitch %s loop %s" % (item, e["sound"], start, end, row, pitch, loop))


def build_binding(seq, b, end_s):
    name = b["name"]
    item = name
    cls = getattr(unreal, b["cls"])
    ok, binding = add_spawnable(item, seq, cls)
    if not ok:
        return None
    call(item, "set_name('%s')" % name, binding.set_name, name)
    set_template(item, b["cls"], b["tpl"], binding)
    build_transform(item, b, binding, end_s)
    if b["vis"]:
        build_vis(item, b["vis"], binding, end_s)
    for cg in b["comps"]:
        cb = component_binding(item, seq, binding, cls, cg["comp"])
        if cb is None:
            results["errors"].append({"item": item, "api": "component binding " + cg["comp"], "error": "could not create"})
            continue
        for tr in cg["tracks"]:
            ok, track = call(item, "component add_track(MovieSceneFloatTrack) %s" % tr["path"], cb.add_track, unreal.MovieSceneFloatTrack)
            if not ok:
                continue
            call(item, "set_property_name_and_path(%s, %s)" % (tr["prop"], tr["path"]), track.set_property_name_and_path, unreal.Name(tr["prop"]), tr["path"])
            ok, sec = call(item, "add_section()", track.add_section)
            call(item, "set_range_seconds", sec.set_range_seconds, 0.0, float(end_s))
            ok, chs = call(item, "get_all_channels()", sec.get_all_channels)
            add_keys(item, "property %s" % tr["path"], chs[0], tr["keys"])
    if b["audio"]:
        ok, track = call(item, "add_track(MovieSceneAudioTrack)", binding.add_track, unreal.MovieSceneAudioTrack)
        if ok:
            build_audio_sections(item, track, b["audio"], end_s)
    return binding


def build_sequence(spec, facts):
    path = spec["path"]
    key = spec["key"]
    name = path.rsplit("/", 1)[1]
    exists = EAL.does_asset_exist(path)
    if exists:
        seq = unreal.load_asset(path)
        reset_sequence(seq)
        note("%s existed: reset in place (P17_REBUILD=1)" % name)
    else:
        ok, seq = call(key, "AssetTools.create_asset(%s, LevelSequence)" % name, unreal.AssetToolsHelpers.get_asset_tools().create_asset,
                       name, CINE_DIR, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
        if not ok or seq is None:
            raise RuntimeError("cannot create " + path)
    call(key, "set_display_rate(30/1)", seq.set_display_rate, unreal.FrameRate(30, 1))
    call(key, "set_playback_start_seconds(0)", seq.set_playback_start_seconds, 0.0)
    call(key, "set_playback_end_seconds(%s)" % spec["end"], seq.set_playback_end_seconds, float(spec["end"]))
    tr = seq.get_tick_resolution()
    log("%s: tick resolution %s/%s display %s" % (name, tr.numerator, tr.denominator, seq.get_display_rate().numerator))
    bindings = {}
    for b in spec["bindings"]:
        bindings[b["name"]] = build_binding(seq, b, spec["end"])
    # camera cut: bCanBlend FIRST (the engine strips eases while it is false)
    ok, cut_track = call(key, "add_track(MovieSceneCameraCutTrack)", seq.add_track, unreal.MovieSceneCameraCutTrack)
    lib = getattr(unreal, "LBCineAuthoringLibrary", None)
    if lib is None:
        results["errors"].append({"item": key, "api": "unreal.LBCineAuthoringLibrary", "error": "missing"})
    else:
        call(key, "LBCineAuthoringLibrary.set_camera_cut_track_can_blend(track, True)", lib.set_camera_cut_track_can_blend, cut_track, True)
    sections = []
    for c in spec["cuts"]:
        ok, sec = call(key, "cut add_section() [%s]" % c["binding"], cut_track.add_section)
        call(key, "cut set_range_seconds(%s,%s)" % (c["start"], c["end"]), sec.set_range_seconds, c["start"], c["end"])
        ok, bid = call(key, "get_binding_id(%s)" % c["binding"], seq.get_binding_id, bindings[c["binding"]])
        call(key, "set_camera_binding_id", sec.set_camera_binding_id, bid)
        sections.append((sec, c))
    for sec, c in sections:
        call(key, "set_ease_in_duration(%d ticks)" % tk(c["ease_in"]), sec.set_ease_in_duration, tk(c["ease_in"]))
        call(key, "set_ease_out_duration(%d ticks)" % tk(c["ease_out"]), sec.set_ease_out_duration, tk(c["ease_out"]))
    # fade track, Keep State
    ok, ftrack = call(key, "add_track(MovieSceneFadeTrack)", seq.add_track, unreal.MovieSceneFadeTrack)
    ok, fsec = call(key, "fade add_section()", ftrack.add_section)
    call(key, "fade set_range_seconds", fsec.set_range_seconds, 0.0, float(spec["end"]))
    call(key, "fade set_completion_mode(KEEP_STATE)", fsec.set_completion_mode, unreal.MovieSceneCompletionMode.KEEP_STATE)
    ok, chs = call(key, "fade get_all_channels()", fsec.get_all_channels)
    add_keys(key, "fade", chs[0], [(t, v, "L") for t, v in spec["fade"]])
    # 2D audio on master tracks
    if spec["audio2d"]:
        ok, atrack = call(key, "add_track(MovieSceneAudioTrack) [master]", seq.add_track, unreal.MovieSceneAudioTrack)
        if ok:
            build_audio_sections(key, atrack, spec["audio2d"], spec["end"])
    # markers
    for label, sec_ in spec["markers"]:
        mf = unreal.MovieSceneMarkedFrame()
        mf.set_editor_property("label", label)
        mf.set_editor_property("frame_number", unreal.FrameNumber(int(round(sec_ * FPS))))
        call(key, "add_marked_frame_to_sequence('%s', frame %d)" % (label, round(sec_ * FPS)), seq.add_marked_frame_to_sequence, mf,
             unreal.MovieSceneTimeUnit.DISPLAY_RATE, quiet=True)
    log("%s: %d markers added" % (name, len(spec["markers"])))
    return seq


def do_build():
    facts = read_mesh_facts()
    results["facts"] = facts
    log("FACTS %s" % json.dumps(facts))
    specs = [spec_intro(), spec_finale(facts)]
    only = os.environ.get("P17_ONLY", "").strip()
    if only:     # e.g. P17_ONLY=Finale: build (and save) just that one; the other asset is left untouched
        specs = [sp for sp in specs if sp["key"] == only]
        log("P17_ONLY=%s: building %s" % (only, [sp["key"] for sp in specs]))
    existing = [sp["path"] for sp in specs if EAL.does_asset_exist(sp["path"])]
    if existing and not REBUILD:
        msg = "refusing to overwrite %s (set P17_REBUILD=1 to rebuild)" % existing
        results["errors"].append({"item": "setup", "api": "exists", "error": msg})
        unreal.log_error("%s: %s" % (TAG, msg))
        return
    for spec in specs:
        try:
            build_sequence(spec, facts)
        except Exception:  # noqa: BLE001
            results["errors"].append({"item": spec["key"], "api": "(exception)", "error": traceback.format_exc()})
            unreal.log_error("%s: EXCEPTION %s" % (TAG, traceback.format_exc()))
    for spec in specs:
        ok, saved = call("save", "EditorAssetLibrary.save_asset('%s', only_if_is_dirty=False)" % spec["path"], EAL.save_asset, spec["path"], False)
        if ok and saved:
            results["saved"].append(spec["path"])
    dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    results["dirty_after_save"] = dirty
    log("dirty packages after the saves (NOT saved by this script): %s" % dirty)


# ================================================================================================================ CHECK
checks = []


def chk(seqkey, item, name, got, want, tol=None):
    if tol is not None:
        try:
            ok = abs(float(got) - float(want)) <= tol
        except Exception:  # noqa: BLE001
            ok = False
    else:
        ok = got == want
    checks.append({"seq": seqkey, "item": item, "name": name, "ok": bool(ok), "got": short(got, 140), "want": short(want, 140)})
    if not ok:
        unreal.log_error("%s: CHECK FAILED [%s/%s] %s: got %s want %s" % (TAG, seqkey, item, name, short(got, 140), short(want, 140)))
    return ok


def read_keys(ch):
    out = []
    for k in ch.get_keys():
        t = k.get_time(TU)
        out.append((t.frame_number.value, k.get_value(), k))
    return out


def cmp_keys(seqkey, item, name, ch, want, is_bool=False, interp=True, tol=1e-3):
    """want = [(sec, val, mode)]; compares tick times, values (tolerance) and interpolation (L = LINEAR, A = CUBIC + AUTO tangent)."""
    got = read_keys(ch)
    exp = sorted(((tk(s), v, m) for s, v, m in want), key=lambda x: x[0])
    got = sorted(got, key=lambda x: x[0])
    bad = []
    if len(got) != len(exp):
        bad.append("count %d != %d" % (len(got), len(exp)))
    for (gt, gv, gk), (et, ev, em) in zip(got, exp):
        if gt != et:
            bad.append("time %d != %d" % (gt, et))
            continue
        if is_bool:
            if bool(gv) != bool(ev):
                bad.append("value @%d %s != %s" % (gt, gv, ev))
        else:
            if abs(float(gv) - float(ev)) > tol * max(1.0, abs(ev)):
                bad.append("value @%d %s != %s" % (gt, gv, ev))
            if interp:
                im, tm = en(gk.get_interpolation_mode()).replace("RCIM_", ""), en(gk.get_tangent_mode()).replace("RCTM_", "")
                if em == "L" and im != "LINEAR":
                    bad.append("interp @%d %s (want LINEAR)" % (gt, im))
                if em == "A" and not (im == "CUBIC" and tm == "AUTO"):
                    bad.append("interp @%d %s/%s (want CUBIC/AUTO)" % (gt, im, tm))
    chk(seqkey, item, "%s (%d keys)" % (name, len(exp)), "ok" if not bad else bad[:4], "ok")
    return not bad


def find_tracks(owner, cname):
    return [t for t in owner.get_tracks() if clsname(t) == cname]


def check_template(sk, item, b, binding):
    t = binding.get_object_template()
    chk(sk, item, "template class", clsname(t), b["cls"])
    tpl = b["tpl"]
    if b["cls"] == "CineCameraActor":
        comp = t.get_editor_property("camera_component")
        fb = comp.get_editor_property("filmback")
        chk(sk, item, "filmback 16:9 DSLR (36 x 20.25)", (round(fb.sensor_width, 3), round(fb.sensor_height, 3)), (36.0, 20.25))
        chk(sk, item, "focal length", comp.get_editor_property("current_focal_length"), tpl["focal"], 1e-3)
        chk(sk, item, "constrain_aspect_ratio", comp.get_editor_property("constrain_aspect_ratio"), tpl["constrain"])
        if tpl.get("aperture") is not None:
            chk(sk, item, "aperture", comp.get_editor_property("current_aperture"), tpl["aperture"], 1e-3)
        if tpl.get("focus") is not None:
            fs = comp.get_editor_property("focus_settings")
            chk(sk, item, "focus method / manual distance", (en(fs.get_editor_property("focus_method")), round(fs.get_editor_property("manual_focus_distance"), 3)),
                ("MANUAL", tpl["focus"]))
        if tpl.get("pps"):
            pps = comp.get_editor_property("post_process_settings")
            arr = pps.get_editor_property("weighted_blendables").get_editor_property("array")
            chk(sk, item, "weighted blendables = [MI_LB_PP_MaskView, 1.0]", [(a.get_editor_property("object").get_name() if a.get_editor_property("object") else None,
                                                                          a.get_editor_property("weight")) for a in arr], [("MI_LB_PP_MaskView", 1.0)])
            chk(sk, item, "post_process_blend_weight", comp.get_editor_property("post_process_blend_weight"), 1.0, 1e-6)
    elif b["cls"] == "SkeletalMeshActor":
        smc = t.get_editor_property("skeletal_mesh_component")
        mesh = smc.get_editor_property("skeletal_mesh_asset")
        chk(sk, item, "skeletal mesh", mesh.get_name() if mesh else None, "SK_Warden")
        ac = smc.get_editor_property("anim_class")
        chk(sk, item, "anim class", ac.get_name() if ac else None, "ABP_Warden_C")
        chk(sk, item, "actor tag", [str(x) for x in t.get_editor_property("tags")], ["LB_Cine_Warden"])
        chk(sk, item, "VisibilityBasedAnimTickOption", en(smc.get_editor_property("visibility_based_anim_tick_option")), "ALWAYS_TICK_POSE")
        chk(sk, item, "collision enabled", en(smc.get_collision_enabled()), "NO_COLLISION")
        chk(sk, item, "collision profile", str(smc.get_collision_profile_name()), "NoCollision")
        chk(sk, item, "cast shadow", smc.get_editor_property("cast_shadow"), True)
    elif b["cls"] == "PointLight":
        lc = t.get_editor_property("light_component")
        chk(sk, item, "intensity units", en(lc.get_editor_property("intensity_units")), "LUMENS")
        chk(sk, item, "intensity", lc.get_editor_property("intensity"), 600.0, 1e-3)
        c = lc.get_editor_property("light_color")
        chk(sk, item, "light colour", (c.r, c.g, c.b), (255, 150, 70))
        chk(sk, item, "attenuation radius", lc.get_editor_property("attenuation_radius"), 650.0, 1e-3)
        chk(sk, item, "source radius", lc.get_editor_property("source_radius"), 2.0, 1e-3)
        chk(sk, item, "cast shadows", lc.get_editor_property("cast_shadows"), True)


def check_audio_track(sk, item, track, entries, seq_end, label=""):
    secs = list(track.get_sections())
    chk(sk, item, "%saudio section count" % label, len(secs), len(entries))
    taken = set()
    rows = {}
    for e in entries:
        snd = load_sound(e["sound"])
        pitch = float(e.get("pitch", 1.0))
        loop = bool(e.get("loop", False))
        start = float(e["start"])
        end = audio_end(snd, start, pitch, loop, e.get("end"), seq_end)
        match = None
        for i, s in enumerate(secs):
            if i in taken:
                continue
            ss = s.get_sound()
            if ss and ss.get_name() == e["sound"] and abs(s.get_start_frame_seconds() - start) < 1e-3:
                match = (i, s)
                break
        nm = "%s%s @%.3f" % (label, e["sound"], start)
        chk(sk, item, nm + " present", match is not None, True)
        if match is None:
            continue
        taken.add(match[0])
        s = match[1]
        chk(sk, item, nm + " end (s)", s.get_end_frame_seconds(), end, 2e-3)
        # set_sound copies the asset's own looping flag (MUS_LB_Drone_C is a looping wave), so an entry without "loop" is expected to follow the asset
        chk(sk, item, nm + " looping", bool(s.get_looping()), loop or bool(snd.get_editor_property("looping")))
        chs = s.get_all_channels()
        chk(sk, item, nm + " pitch", chs[1].get_default() if chs[1].has_default() else 1.0, pitch, 1e-4)
        if e.get("vol"):
            cmp_keys(sk, item, nm + " volume keys", chs[0], e["vol"])
        rows.setdefault(s.get_row_index(), []).append((s.get_start_frame_seconds(), s.get_end_frame_seconds()))
    ok_rows = True
    for r, lst in rows.items():
        lst.sort()
        for (a0, a1), (b0, b1) in zip(lst, lst[1:]):
            if b0 < a1 - 1e-3:
                ok_rows = False
    chk(sk, item, "%sno overlapping sections within a row" % label, ok_rows, True)


def check_sequence(spec, facts):
    sk = spec["key"]
    seq = unreal.load_asset(spec["path"])
    chk(sk, "setup", "asset loads as LevelSequence", clsname(seq) if seq else None, "LevelSequence")
    if seq is None:
        return
    dr, tr = seq.get_display_rate(), seq.get_tick_resolution()
    chk(sk, "setup", "display rate", (dr.numerator, dr.denominator), (30, 1))
    chk(sk, "setup", "tick resolution", (tr.numerator, tr.denominator), (24000, 1))
    chk(sk, "setup", "playback range s", (seq.get_playback_start_seconds(), round(seq.get_playback_end_seconds(), 3)), (0.0, spec["end"]))
    spawn_ids = {guid_str(b.get_id()) for b in seq.get_spawnables()}
    poss = {guid_str(b.get_id()): b for b in seq.get_possessables()}
    by_name = {}
    for b in seq.get_bindings():
        by_name.setdefault(b.get_name(), []).append(b)
    chk(sk, "setup", "spawnable names", sorted(n for n, l in by_name.items() if guid_str(l[0].get_id()) in spawn_ids), sorted(b["name"] for b in spec["bindings"]))
    bnd = {}
    # markers
    marks = sorted(((m.get_editor_property("frame_number").value, str(m.get_editor_property("label"))) for m in
                    seq.get_marked_frames_from_sequence(unreal.MovieSceneTimeUnit.DISPLAY_RATE)))
    want = sorted((int(round(s * FPS)), l) for l, s in spec["markers"])
    chk(sk, "markers", "marked frames (label, display frame)", marks, want)
    chk(sk, "markers", "every label parses against the grammar", [l for _, l in marks if not MARKER_RE.match(l)], [])
    # fade
    ftr = find_tracks(seq, "MovieSceneFadeTrack")
    chk(sk, "fade", "one fade track with one section", (len(ftr), len(ftr[0].get_sections()) if ftr else 0), (1, 1))
    if ftr:
        fs = ftr[0].get_sections()[0]
        chk(sk, "fade", "completion mode", en(fs.get_completion_mode()), "KEEP_STATE")
        cmp_keys(sk, "fade", "fade keys", fs.get_all_channels()[0], [(t, v, "L") for t, v in spec["fade"]])
    # camera cut
    cut = find_tracks(seq, "MovieSceneCameraCutTrack")
    chk(sk, "cut", "one camera cut track", len(cut), 1)
    if cut:
        lib = getattr(unreal, "LBCineAuthoringLibrary", None)
        chk(sk, "cut", "bCanBlend (LBCineAuthoringLibrary)", lib.get_camera_cut_track_can_blend(cut[0]) if lib else None, True)
        secs = sorted(cut[0].get_sections(), key=lambda s: s.get_start_frame_seconds())
        chk(sk, "cut", "section count", len(secs), len(spec["cuts"]))
        for s, c in zip(secs, sorted(spec["cuts"], key=lambda c: c["start"])):
            bn = c["binding"]
            chk(sk, "cut", "%s range (s)" % bn, (round(s.get_start_frame_seconds(), 3), round(s.get_end_frame_seconds(), 3)), (c["start"], c["end"]))
            chk(sk, "cut", "%s ease in (ticks)" % bn, s.get_ease_in_duration(), tk(c["ease_in"]))
            chk(sk, "cut", "%s ease out (ticks)" % bn, s.get_ease_out_duration(), tk(c["ease_out"]))
            tgt = guid_str(s.get_camera_binding_id().get_editor_property("guid"))
            chk(sk, "cut", "%s bound to the camera spawnable" % bn, tgt, guid_str(by_name[bn][0].get_id()) if bn in by_name else None)
    # bindings
    for b in spec["bindings"]:
        item = b["name"]
        lst = by_name.get(item)
        chk(sk, item, "binding exists and is a spawnable", bool(lst) and guid_str(lst[0].get_id()) in spawn_ids, True)
        if not lst:
            continue
        bd = lst[0]
        check_template(sk, item, b, bd)
        # transform
        tt = find_tracks(bd, "MovieScene3DTransformTrack")
        chk(sk, item, "transform track count", len(tt), 1)
        if tt:
            chs = {chan_name(c): c for c in tt[0].get_sections()[0].get_all_channels()}
            for k, nm in {"lx": "Location.X", "ly": "Location.Y", "lz": "Location.Z", "rr": "Rotation.X", "rp": "Rotation.Y", "ry": "Rotation.Z"}.items():
                if nm in chs:
                    cmp_keys(sk, item, "transform %s" % nm, chs[nm], b["xf"][k])
                else:
                    chk(sk, item, "channel %s exists" % nm, False, True)
            for nm in ("Scale.X", "Scale.Y", "Scale.Z"):
                cmp_keys(sk, item, "transform %s" % nm, chs[nm], [(0.0, 1.0, "L")])
        # visibility
        vt = find_tracks(bd, "MovieSceneVisibilityTrack")
        chk(sk, item, "visibility track count", len(vt), 1 if b["vis"] else 0)
        if b["vis"] and vt:
            cmp_keys(sk, item, "visibility (True = visible)", vt[0].get_sections()[0].get_all_channels()[0], [(t, v, "L") for t, v in b["vis"]], is_bool=True, interp=False)
        # component tracks
        for cg in b["comps"]:
            kids = [p for p in poss.values() if p.get_parent() and p.get_parent().is_valid() and guid_str(p.get_parent().get_id()) == guid_str(bd.get_id())]
            chk(sk, item, "%s component binding is a child possessable" % cg["comp"], len(kids), 1)
            if kids:
                for tr in cg["tracks"]:
                    ft = find_tracks(kids[0], "MovieSceneFloatTrack")
                    chk(sk, item, "%s float track" % tr["path"], len(ft), len(cg["tracks"]))
                    if ft:
                        chk(sk, item, "%s property name / path" % tr["path"], (str(ft[0].get_property_name()), str(ft[0].get_property_path())), (tr["prop"], tr["path"]))
                        cmp_keys(sk, item, "%s keys" % tr["path"], ft[0].get_sections()[0].get_all_channels()[0], tr["keys"])
        # audio
        if b["audio"]:
            at = find_tracks(bd, "MovieSceneAudioTrack")
            chk(sk, item, "audio track count", len(at), 1)
            if at:
                check_audio_track(sk, item, at[0], b["audio"], spec["end"])
    # 2D audio
    if spec["audio2d"]:
        at = find_tracks(seq, "MovieSceneAudioTrack")
        chk(sk, "audio2d", "master audio track count", len(at), 1)
        if at:
            check_audio_track(sk, "audio2d", at[0], spec["audio2d"], spec["end"], label="2D ")
    # dependencies (for the Mixamo / git-ignore audit, done outside)
    try:
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        deps = ar.get_dependencies(unreal.Name(spec["path"]), unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True))
        results.setdefault("deps", {})[sk] = sorted(str(d) for d in deps if str(d).startswith("/Game"))
    except Exception as exc:  # noqa: BLE001
        note("dependencies of %s: %s" % (sk, exc))


def do_check():
    facts = read_mesh_facts()
    results["facts"] = facts
    log("FACTS %s" % json.dumps(facts))
    for spec in (spec_intro(), spec_finale(facts)):
        try:
            check_sequence(spec, facts)
        except Exception:  # noqa: BLE001
            checks.append({"seq": spec["key"], "item": "exception", "name": "check raised", "ok": False, "got": traceback.format_exc()[-600:], "want": "no exception"})
            unreal.log_error("%s: EXCEPTION %s" % (TAG, traceback.format_exc()))
    bad = [c for c in checks if not c["ok"]]
    out = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "total_checks": len(checks), "passed": len(checks) - len(bad), "failed": len(bad),
           "per_sequence": {k: {"total": len([c for c in checks if c["seq"] == k]), "failed": len([c for c in bad if c["seq"] == k])} for k in ("Intro", "Finale")},
           "facts": facts, "deps": results.get("deps"), "notes": results["notes"], "failures": bad, "checks": checks}
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    log("CHECK done: %d checks, %d failed (%s)" % (len(checks), len(bad), OUT_JSON))
    for c in bad[:30]:
        log("  FAIL [%s/%s] %s: got %s want %s" % (c["seq"], c["item"], c["name"], c["got"], c["want"]))


def main():
    if MODE == "build":
        do_build()
        os.makedirs(os.path.dirname(BUILD_RECORD), exist_ok=True)
        with open(BUILD_RECORD, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=1)
        log("BUILD done: %d calls, %d errors, saved %s" % (results["calls"], len(results["errors"]), results["saved"]))
    elif MODE == "check":
        do_check()
    else:
        unreal.log_error("%s: set P17_MODE=build or P17_MODE=check" % TAG)


try:
    main()
except Exception:  # noqa: BLE001
    unreal.log_error("%s: EXCEPTION %s" % (TAG, traceback.format_exc()))
