"""P17 S1a: headless Sequencer authoring spike (Unreal CLOSED). The output is an answer, not production content.

Run (editor closed, never two at once):
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>
Mode (environment variable, like Tools/audio/p16_2_assets.py; a --build / --verify argument also works):
    P17_MODE=build   creates /Game/LastBell/ArtTest/P17/LS_P17_Spike (resets it in place when it already exists), fills it with the
                     items a to g of docs/plans/P17_CINEMATICS.md section 8, logs every API call and result, saves that ONE package
                     with an explicit save, writes Saved/p17_s1_build.json (the build record).
    P17_MODE=verify  read-only, run it in a FRESH process (a real reload): loads the asset, reads back every item, compares it with
                     what build intended and writes Docs/ArtTest/cine/p17_s1.json (status per item).

Safety (task rules): the only asset created or saved is LS_P17_Spike (EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)).
No save-all, no PIE, no capture, no MCP. Everything else is read only.
"""
import json
import os
import sys
import time
import traceback

import unreal

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
SEQ_DIR = "/Game/LastBell/ArtTest/P17"
SEQ_NAME = "LS_P17_Spike"
SEQ_PATH = SEQ_DIR + "/" + SEQ_NAME
BUILD_RECORD = os.path.join(ROOT, "Saved", "p17_s1_build.json")
OUT_JSON = os.path.join(ROOT, "Docs", "ArtTest", "cine", "p17_s1.json")

SK_PATH = "/Game/LastBell/Characters/Warden/Meshes/SK_Warden"
SKEL_PATH = "/Game/LastBell/Characters/Warden/Meshes/SK_Warden_Skeleton"
ABP_CLASS_PATH = "/Game/LastBell/Characters/Warden/ABP_Warden.ABP_Warden_C"
ANIM_PRIMARY = "/Game/LastBell/Characters/Warden/Anims/AN_Warden_LookAround"
ANIM_FALLBACK = "/Game/LastBell/Characters/Warden/Anims/AN_Warden_Idle"
SND_MASTER = "/Game/LastBell/Audio/Warden/SFX_LB_Warden_Breath_Slow"
SND_WARDEN = "/Game/LastBell/Audio/Warden/SFX_LB_Warden_Step_01"
CUBE_PATH = "/Engine/BasicShapes/Cube"

FPS = 30
MODE = os.environ.get("P17_MODE", "").lower()
for _a in sys.argv[1:]:
    if _a == "--build":
        MODE = "build"
    elif _a == "--verify":
        MODE = "verify"

TAG = "P17S1"
results = {"mode": MODE, "started": time.strftime("%Y-%m-%d %H:%M:%S"), "calls": [], "errors": [], "notes": []}
EAL = unreal.EditorAssetLibrary


# ---------------------------------------------------------------------------------------------------------------- logging helpers
def log(msg):
    unreal.log("%s: %s" % (TAG, msg))


def short(value, limit=260):
    try:
        text = repr(value)
    except Exception as exc:  # noqa: BLE001
        text = "<repr failed: %s>" % exc
    return text if len(text) <= limit else text[:limit] + "..."


def call(item, label, fn, *args, **kwargs):
    """Call fn, log the API label and the result, record both. Returns (ok, value). Never raises."""
    try:
        value = fn(*args, **kwargs)
        log("CALL [%s] %s -> %s" % (item, label, short(value)))
        results["calls"].append({"item": item, "api": label, "ok": True, "result": short(value, 160)})
        return True, value
    except Exception as exc:  # noqa: BLE001
        msg = "%s: %s" % (type(exc).__name__, str(exc).strip().replace("\n", " | "))
        unreal.log_warning("%s: CALL FAILED [%s] %s -> %s" % (TAG, item, label, msg))
        results["calls"].append({"item": item, "api": label, "ok": False, "error": msg})
        results["errors"].append({"item": item, "api": label, "error": msg})
        return False, None


def note(text):
    results["notes"].append(text)
    log("NOTE " + text)


def first_ok(item, label_fns):
    """Try [(label, thunk), ...] in order; return (ok, value, label) of the first that works and gives a truthy-or-zero value."""
    for label, thunk in label_fns:
        ok, value = call(item, label, thunk)
        if ok and value is not None:
            return True, value, label
    return False, None, None


def ticks_per_sec(seq):
    rate = seq.get_tick_resolution()
    return float(rate.numerator) / float(rate.denominator)


def disp_frame(seconds):
    """Display-rate frame number (30 fps) for a time in seconds."""
    return int(round(seconds * FPS))


def fn_(frame):
    return unreal.FrameNumber(frame)


_GUID_ROUTE = {"fn": None, "label": None}


def guid_str(guid):
    """Content string of an FGuid (the Python repr of the struct only shows its address)."""
    if guid is None:
        return None
    if _GUID_ROUTE["fn"] is None:
        for label, fn in (("Guid.to_string()", lambda g: g.to_string()),
                          ("GuidLibrary.conv_guid_to_string", lambda g: unreal.GuidLibrary.conv_guid_to_string(g)),
                          ("KismetGuidLibrary.conv_guid_to_string", lambda g: unreal.KismetGuidLibrary.conv_guid_to_string(g)),
                          ("SystemLibrary.conv_guid", lambda g: unreal.KismetStringLibrary.conv_guid_to_string(g)),
                          ("Guid a,b,c,d", lambda g: "%08x%08x%08x%08x" % (g.a & 0xffffffff, g.b & 0xffffffff, g.c & 0xffffffff, g.d & 0xffffffff))):
            try:
                val = fn(guid)
                if val and "Struct" not in str(val):
                    _GUID_ROUTE["fn"], _GUID_ROUTE["label"] = fn, label
                    log("guid string route: %s" % label)
                    break
            except Exception:  # noqa: BLE001
                continue
    if _GUID_ROUTE["fn"] is None:
        return str(guid)
    return str(_GUID_ROUTE["fn"](guid))


def clsname(obj):
    try:
        return obj.get_class().get_name()
    except Exception:  # noqa: BLE001
        return type(obj).__name__


def tool_props(obj, names):
    """UToolsetLibrary.get_object_properties -> parsed JSON (the same call ObjectTools uses; sees UPROPERTYs Python hides)."""
    try:
        raw = unreal.ToolsetLibrary.get_object_properties(obj, [unreal.Name(n) for n in names])
        return json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        return {"__error__": str(exc)}


# ---------------------------------------------------------------------------------------------------------------- read-only asset probes
def read_warden_mesh():
    """Slots, bones and the picks. Read only."""
    info = {"slots": [], "bones": [], "slot_pick": None, "head_bone": None, "right_hand_bone": None, "errors": []}
    mesh = unreal.load_asset(SK_PATH)
    if mesh is None:
        info["errors"].append("SK_Warden not found at " + SK_PATH)
        return info, None
    try:
        mats = mesh.get_editor_property("materials")
        for i, m in enumerate(mats):
            slot = str(m.get_editor_property("material_slot_name"))
            mi = m.get_editor_property("material_interface")
            info["slots"].append({"index": i, "slot_name": slot, "material": mi.get_path_name() if mi else None,
                                  "material_name": mi.get_name() if mi else None})
    except Exception as exc:  # noqa: BLE001
        info["errors"].append("materials: %s" % exc)
    skel = unreal.load_asset(SKEL_PATH)
    names = []
    try:
        pose = unreal.AnimPoseExtensions.get_reference_pose(skel)
        names = [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(pose)]
    except Exception as exc:  # noqa: BLE001
        info["errors"].append("bone names (AnimPoseExtensions): %s" % exc)
    if not names:
        try:
            names = [str(n) for n in mesh.get_editor_property("skeleton").get_editor_property("bone_tree")]
        except Exception as exc:  # noqa: BLE001
            info["errors"].append("bone names (bone_tree): %s" % exc)
    info["bones"] = names
    info["bone_count"] = len(names)
    low = {n.lower(): n for n in names}

    # mask slot rule (task): slot name or material name contains "Mask"; else "Bell" or "Metal"; else slot 0
    def find(words):
        for s in info["slots"]:
            hay = ((s["slot_name"] or "") + " " + (s["material_name"] or "")).lower()
            if any(w.lower() in hay for w in words):
                return s
        return None

    pick = find(["Mask"])
    why = "slot or material name contains 'Mask'"
    if pick is None:
        pick = find(["Bell", "Metal"])
        why = "no 'Mask' slot; slot or material name contains 'Bell' or 'Metal'"
    if pick is None and info["slots"]:
        pick = info["slots"][0]
        why = "no Mask/Bell/Metal slot; slot 0"
    if pick:
        info["slot_pick"] = dict(pick, why=why)
    # head / right-hand bone
    for cand in ("head", "Head", "mixamorig:Head"):
        if cand in names:
            info["head_bone"] = cand
            break
    if info["head_bone"] is None:
        c = [n for n in names if n.lower() in ("head", "head_01", "head_00")]
        info["head_bone"] = c[0] if c else None
    for cand in ("hand_r", "Hand_R", "hand_r_01", "RightHand", "mixamorig:RightHand", "right_hand"):
        if cand in names:
            info["right_hand_bone"] = cand
            break
    if info["right_hand_bone"] is None:
        c = [n for n in names if n.lower().startswith("hand") and n.lower().endswith("r")]
        c = c or [n for n in names if "righthand" in n.lower().replace("_", "")]
        info["right_hand_bone"] = c[0] if c else None
    return info, mesh


def pick_anim():
    for path in (ANIM_PRIMARY, ANIM_FALLBACK):
        anim = unreal.load_asset(path)
        if anim is not None:
            return anim, path
    return None, None


# ---------------------------------------------------------------------------------------------------------------- what build intends
SPEC = {
    "display_rate": (30, 1),
    "playback_seconds": (0.0, 10.0),
    "cam": {"focal": 30.0, "ease_in_s": 1.0, "ease_out_s": 1.5, "transform_keys": 2},
    "warden": {"tag": "LB_Cine_Warden", "tick_option": "ALWAYS_TICK_POSE", "anim_class": "ABP_Warden_C", "slot": "DefaultSlot",
               "xform_keys": [(0.0, (0, 0, 0), 0.0), (5.0, (300, 0, 0), 0.0)],
               "vis_keys": [(0.0, True), (8.0, False)],
               "fade_keys": [(2.0, 1.0), (61 / 30.0, 0.0)]},
    "cube": {"scale": 0.2, "att1": (0.0, 4.0), "att2": (4.0, 10.0)},
    "light": {"keys": [(0.0, 0.0), (1.0, 600.0)]},
    "audio": {"master": (SND_MASTER, 1.0), "warden": (SND_WARDEN, 2.0)},
    "fade": [(0.0, 1.0), (1.0, 0.0), (9.5, 1.0)],
    "markers": [("tag:State.Test.A", 1.0), ("!lock:None", 2.0), ("bell:1x1", 3.0)],
}


# ================================================================================================================ BUILD
def api_dump():
    """One log block of Python names on the classes whose API is not in the docs (for the findings)."""
    base = set(dir(unreal.Object))
    for cname in ("MovieSceneComponentMaterialParameterSection", "MovieSceneComponentMaterialTrack", "MovieScene3DAttachSection",
                  "MovieSceneCameraCutTrack", "MovieSceneFadeSection", "MovieSceneAudioTrack", "MovieSceneFloatTrack",
                  "MovieScene3DTransformSection", "MovieSceneSkeletalAnimationSection", "MovieSceneVisibilityTrack"):
        cls = getattr(unreal, cname, None)
        if cls is None:
            log("API-DUMP %s: MISSING from unreal module" % cname)
            continue
        log("API-DUMP %s: %s" % (cname, sorted(n for n in dir(cls) if not n.startswith("_") and n not in base)))


def reset_sequence(seq):
    """Rebuild in place: delete bindings, master tracks and marked frames (delete_asset leaves the asset registered in a commandlet)."""
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
        note("reset: marked frames delete failed: %s" % exc)


def create_or_load_sequence():
    existing = unreal.load_asset(SEQ_PATH) if EAL.does_asset_exist(SEQ_PATH) else None
    if existing is not None:
        note("LS_P17_Spike already exists: reset in place")
        reset_sequence(existing)
        return existing
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    ok, seq = call("setup", "AssetTools.create_asset(LS_P17_Spike, LevelSequence, LevelSequenceFactoryNew)",
                   tools.create_asset, SEQ_NAME, SEQ_DIR, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    return seq if ok else None


def set_defaults(seq):
    call("setup", "LevelSequence.set_display_rate(30/1)", seq.set_display_rate, unreal.FrameRate(30, 1))
    call("setup", "LevelSequence.set_playback_start_seconds(0)", seq.set_playback_start_seconds, 0.0)
    call("setup", "LevelSequence.set_playback_end_seconds(10)", seq.set_playback_end_seconds, 10.0)
    log("tick resolution %s display %s playback %s..%s s" % (seq.get_tick_resolution(), seq.get_display_rate(),
                                                              seq.get_playback_start_seconds(), seq.get_playback_end_seconds()))


def add_spawnable(item, seq, cls):
    """Non-deprecated route first (LevelSequenceEditorSubsystem.add_spawnable_from_class), then the deprecated library function."""
    name = cls.__name__ if hasattr(cls, "__name__") else str(cls)
    subsystem = None
    try:
        subsystem = unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)
    except Exception as exc:  # noqa: BLE001
        log("LevelSequenceEditorSubsystem unavailable: %s" % exc)
    if subsystem is not None:
        ok, b = call(item, "LevelSequenceEditorSubsystem.add_spawnable_from_class(%s)" % name, subsystem.add_spawnable_from_class, seq, cls)
        if ok and b is not None and b.is_valid():
            return True, b
        log("subsystem add_spawnable_from_class gave no valid binding for %s" % name)
    return call(item, "LevelSequence.add_spawnable_from_class(%s) [deprecated since 5.5]" % name, seq.add_spawnable_from_class, cls)


def add_channel_key(item, label, channel, frame, value):
    return call(item, label, channel.add_key, fn_(frame), value)


def build_transform_track(item, seq, binding, keys, default_scale=True):
    """keys = [(seconds, (x,y,z), yaw)]. Returns the track."""
    ok, track = call(item, "MovieSceneBindingProxy.add_track(MovieScene3DTransformTrack)", binding.add_track, unreal.MovieScene3DTransformTrack)
    if not ok:
        return None
    ok, section = call(item, "MovieSceneTrack.add_section()", track.add_section)
    if not ok:
        return None
    call(item, "MovieSceneSection.set_range_seconds(0,10)", section.set_range_seconds, 0.0, 10.0)
    ok, channels = call(item, "MovieSceneSection.get_all_channels()", section.get_all_channels)
    if not ok or len(channels) < 9:
        return track
    log("transform section channels: %d (%s)" % (len(channels), clsname(channels[0])))
    for secs, loc, yaw in keys:
        fr = disp_frame(secs)
        vals = list(loc) + [0.0, 0.0, float(yaw)] + [1.0, 1.0, 1.0]   # loc xyz, rot roll/pitch/yaw, scale xyz
        for idx, v in enumerate(vals):
            add_channel_key(item, "ScriptingChannel[%d].add_key(frame %d, %s)" % (idx, fr, v), channels[idx], fr, float(v))
    return track


def template_of(item, binding):
    ok, tpl = call(item, "MovieSceneBindingProxy.get_object_template()", binding.get_object_template)
    return tpl if ok else None


def build_camera(seq):
    item = "a"
    ok, binding = add_spawnable(item, seq, unreal.CineCameraActor)
    if not ok:
        return None
    call(item, "MovieSceneBindingProxy.set_name('Cam_Spike')", binding.set_name, "Cam_Spike")
    tpl = template_of(item, binding)
    if tpl is not None:
        ok, comp, _lbl = first_ok(item, [("CineCameraActor.get_cine_camera_component()", tpl.get_cine_camera_component),
                                         ("CineCameraActor.get_editor_property('camera_component')", lambda: tpl.get_editor_property("camera_component")),
                                         ("CineCameraActor.get_component_by_class(CineCameraComponent)", lambda: tpl.get_component_by_class(unreal.CineCameraComponent)),
                                         ("Actor.root_component", lambda: tpl.get_editor_property("root_component"))])
        log("camera template components: %s" % short([c.get_name() + ":" + c.get_class().get_name() for c in tpl.get_components_by_class(unreal.ActorComponent)], 400))
        if ok and comp is not None:
            ok1, _ = call(item, "CineCameraComponent.set_filmback_preset_by_name('16:9 DSLR')", comp.set_filmback_preset_by_name, "16:9 DSLR")
            fb = comp.get_editor_property("filmback")
            log("filmback after preset: sensor %s x %s" % (fb.sensor_width, fb.sensor_height))
            results["filmback_after_preset"] = [float(fb.sensor_width), float(fb.sensor_height)]
            call(item, "CineCameraComponent.set_editor_property('current_focal_length', 30)", comp.set_editor_property, "current_focal_length", 30.0)
    build_transform_track("a", seq, binding,
                          [(0.0, (-2800.0, 0.0, 652.79), 0.0), (10.0, (-2800.0, 0.0, 152.79), 0.0)])
    # camera cut
    ok, cut_track = call(item, "LevelSequence.add_track(MovieSceneCameraCutTrack)", seq.add_track, unreal.MovieSceneCameraCutTrack)
    if ok:
        # bCanBlend FIRST: with it false the engine strips eases (RearrangeAllSections removes overlaps and easings; SupportsEasing is None)
        item2 = "a.can_blend"
        lib = getattr(unreal, "LBCineAuthoringLibrary", None)
        if lib is None:
            results["errors"].append({"item": item2, "api": "unreal.LBCineAuthoringLibrary", "error": "unreal.LBCineAuthoringLibrary is missing (editor binaries without the P17-1 helper?)"})
            unreal.log_error("%s: unreal.LBCineAuthoringLibrary is missing" % TAG)
        else:
            call(item2, "LBCineAuthoringLibrary.set_camera_cut_track_can_blend(track, True)", lib.set_camera_cut_track_can_blend, cut_track, True)
            ok_g, got = call(item2, "LBCineAuthoringLibrary.get_camera_cut_track_can_blend(track)", lib.get_camera_cut_track_can_blend, cut_track)
            results["can_blend_after_build"] = got if ok_g else None
        ok, cut = call(item, "MovieSceneTrack.add_section() [camera cut]", cut_track.add_section)
        if ok:
            call(item, "MovieSceneSection.set_range_seconds(0,10) [camera cut]", cut.set_range_seconds, 0.0, 10.0)
            ok, bid = call(item, "LevelSequence.get_binding_id(camera binding)", seq.get_binding_id, binding)
            if ok:
                call(item, "MovieSceneCameraCutSection.set_camera_binding_id(binding id)", cut.set_camera_binding_id, bid)
            tps = ticks_per_sec(seq)
            call(item, "MovieSceneSection.set_ease_in_duration(%d ticks = 1.0 s)" % round(1.0 * tps), cut.set_ease_in_duration, int(round(1.0 * tps)))
            call(item, "MovieSceneSection.set_ease_out_duration(%d ticks = 1.5 s)" % round(1.5 * tps), cut.set_ease_out_duration, int(round(1.5 * tps)))
            results["eases_after_build_ticks"] = [cut.get_ease_in_duration(), cut.get_ease_out_duration()]
            log("eases right after build: in %s out %s ticks" % tuple(results["eases_after_build_ticks"]))
    return binding


def build_warden(seq, mesh_info, mesh):
    binding_ok, binding = add_spawnable("b", seq, unreal.SkeletalMeshActor)
    if not binding_ok:
        return None
    call("b", "MovieSceneBindingProxy.set_name('WardenFigure')", binding.set_name, "WardenFigure")
    tpl = template_of("b", binding)
    abp_class = unreal.load_class(None, ABP_CLASS_PATH)
    log("ABP class: %s" % short(abp_class))
    if tpl is not None:
        smc = tpl.get_editor_property("skeletal_mesh_component")
        log("template skeletal mesh component: %s" % short(smc))
        if smc is not None and mesh is not None:
            first_ok("b", [("SkeletalMeshComponent.set_skeletal_mesh_asset(SK_Warden)", lambda: smc.set_skeletal_mesh_asset(mesh) or True),
                           ("SkeletalMeshComponent.set_editor_property('skeletal_mesh_asset')", lambda: smc.set_editor_property("skeletal_mesh_asset", mesh) or True)])
            call("b", "SkeletalMeshComponent.set_animation_mode(ANIMATION_BLUEPRINT)", smc.set_animation_mode, unreal.AnimationMode.ANIMATION_BLUEPRINT)
            first_ok("b", [("SkeletalMeshComponent.set_anim_instance_class(ABP_Warden_C)", lambda: smc.set_anim_instance_class(abp_class) or True),
                           ("SkeletalMeshComponent.set_editor_property('anim_class')", lambda: smc.set_editor_property("anim_class", abp_class) or True)])
            call("b", "SkeletalMeshComponent.set_editor_property('visibility_based_anim_tick_option', ALWAYS_TICK_POSE)", smc.set_editor_property,
                 "visibility_based_anim_tick_option", unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE)
        call("b", "Actor.set_editor_property('tags', ['LB_Cine_Warden'])", tpl.set_editor_property, "tags", [unreal.Name("LB_Cine_Warden")])
    # b1 transform
    build_transform_track("b1", seq, binding, SPEC["warden"]["xform_keys"])
    # b2 visibility
    item = "b2"
    ok, vtrack = call(item, "MovieSceneBindingProxy.add_track(MovieSceneVisibilityTrack)", binding.add_track, unreal.MovieSceneVisibilityTrack)
    if ok:
        call(item, "MovieScenePropertyTrack.set_property_name_and_path('bHidden','bHidden')", vtrack.set_property_name_and_path, unreal.Name("bHidden"), "bHidden")
        ok, vsec = call(item, "MovieSceneTrack.add_section() [visibility]", vtrack.add_section)
        if ok:
            call(item, "MovieSceneSection.set_range_seconds(0,10) [visibility]", vsec.set_range_seconds, 0.0, 10.0)
            ok, chs = call(item, "MovieSceneSection.get_all_channels() [visibility]", vsec.get_all_channels)
            if ok and chs:
                log("visibility channel class: %s" % clsname(chs[0]))
                for secs, vis in SPEC["warden"]["vis_keys"]:
                    add_channel_key(item, "bool channel.add_key(frame %d, %s)" % (disp_frame(secs), vis), chs[0], disp_frame(secs), vis)
    # b3 skeletal animation
    item = "b3"
    anim, anim_path = pick_anim()
    results["anim_used"] = anim_path
    if anim is None:
        results["errors"].append({"item": item, "api": "load AN_Warden_LookAround / AN_Warden_Idle", "error": "neither animation asset found"})
    else:
        ok, atrack = call(item, "MovieSceneBindingProxy.add_track(MovieSceneSkeletalAnimationTrack)", binding.add_track, unreal.MovieSceneSkeletalAnimationTrack)
        if ok:
            ok, asec = call(item, "MovieSceneTrack.add_section() [skeletal animation]", atrack.add_section)
            if ok:
                params = asec.get_editor_property("params")
                params.set_editor_property("animation", anim)
                params.set_editor_property("slot_name", unreal.Name("DefaultSlot"))
                call(item, "MovieSceneSkeletalAnimationSection.set_editor_property('params', animation + slot_name)", asec.set_editor_property, "params", params)
                length = float(anim.get_editor_property("sequence_length")) if hasattr(anim, "get_editor_property") else 10.0
                results["anim_length_s"] = length
                end = min(10.0, length)
                call(item, "MovieSceneSection.set_range_seconds(0,%.3f) [skeletal animation]" % end, asec.set_range_seconds, 0.0, end)
    # b4 component material parameter track
    build_material_track(seq, binding, mesh_info, tpl)
    return binding


def build_material_track(seq, warden_binding, mesh_info, tpl):
    """b4. The track is meant for the SkeletalMeshComponent binding (a child possessable of the spawnable). Try to make that binding;
    record the route and any failure. Falls back to the actor binding so that the track data itself can still be read back."""
    item = "b4"
    pick = mesh_info.get("slot_pick")
    if not pick:
        results["errors"].append({"item": item, "api": "slot pick", "error": "no material slots read from SK_Warden"})
        return
    results["b4_slot"] = pick
    target = warden_binding
    route = "actor binding (no component binding was possible)"
    comp_binding = make_component_binding(item, seq, warden_binding, tpl, "skeletal_mesh_component", "SkeletalMeshComponent")
    if comp_binding is not None:
        target = comp_binding
        route = "component binding"
    results["b4_route"] = route
    ok, track = call(item, "MovieSceneBindingProxy.add_track(MovieSceneComponentMaterialTrack)", target.add_track, unreal.MovieSceneComponentMaterialTrack)
    if not ok:
        return
    info = unreal.ComponentMaterialInfo()
    info.set_editor_property("material_slot_name", unreal.Name(pick["slot_name"]))
    info.set_editor_property("material_slot_index", int(pick["index"]))
    info.set_editor_property("material_type", unreal.ComponentMaterialType.INDEXED_MATERIAL)
    call(item, "MovieSceneComponentMaterialTrack.set_material_info(slot %s idx %d)" % (pick["slot_name"], pick["index"]), track.set_material_info, info)
    ok, sec = call(item, "MovieSceneTrack.add_section() [component material]", track.add_section)
    if not ok:
        return
    call(item, "MovieSceneSection.set_range_seconds(0,10) [component material]", sec.set_range_seconds, 0.0, 10.0)
    pinfo = unreal.MaterialParameterInfo()
    pinfo.set_editor_property("name", unreal.Name("Fade"))
    tps = ticks_per_sec(seq)
    for secs, v in SPEC["warden"]["fade_keys"]:
        # this UFUNCTION takes the frame in TICK RESOLUTION (a display frame passed here lands at ~0 s: seen in the first build)
        tick = int(round(disp_frame(secs) * tps / FPS))
        call(item, "MovieSceneComponentMaterialParameterSection.add_scalar_parameter_key(Fade, tick %d = display frame %d, %s)" % (tick, disp_frame(secs), v),
             sec.add_scalar_parameter_key, pinfo, fn_(tick), float(v), "", "")


WORLD = {"world": None, "tried": False}


def get_world(item):
    """A world to spawn into. Headless there may be none: try the editor world, then a new blank map (never saved)."""
    if WORLD["world"] is not None or WORLD["tried"]:
        return WORLD["world"]
    WORLD["tried"] = True
    if os.environ.get("P17_EXPERIMENT", "1") == "0":
        note("world experiment disabled by P17_EXPERIMENT=0")
        return None
    for label, fn in (("EditorLevelLibrary.get_editor_world()", unreal.EditorLevelLibrary.get_editor_world),
                      ("EditorLoadingAndSavingUtils.new_blank_map(save_existing_map=False)", lambda: unreal.EditorLoadingAndSavingUtils.new_blank_map(False))):
        ok, w = call(item, label, fn)
        if ok and w is not None:
            WORLD["world"] = w
            return w
    return None


def spawned_actor(item, seq, binding, world, cls):
    """Create a player, evaluate frame 0 so the spawn tracks spawn the spawnables, and return the live actor of this binding."""
    settings = unreal.MovieSceneSequencePlaybackSettings()
    ok, res = call(item, "LevelSequencePlayer.create_level_sequence_player(world, seq, settings)",
                   unreal.LevelSequencePlayer.create_level_sequence_player, world, seq, settings)
    if not ok or res is None:
        return None, None
    player = res[0] if isinstance(res, (tuple, list)) else res
    call(item, "LevelSequencePlayer.set_playback_position(frame 0)", player.set_playback_position,
         unreal.MovieSceneSequencePlaybackParams(frame=unreal.FrameTime(unreal.FrameNumber(0)), position_type=unreal.MovieScenePositionType.FRAME,
                                                  update_method=unreal.UpdatePositionMethod.JUMP))
    found = None
    ok, bid = call(item, "LevelSequence.get_binding_id(binding)", seq.get_binding_id, binding)
    if ok:
        ok, objs = call(item, "MovieSceneSequencePlayer.get_bound_objects(binding id)", player.get_bound_objects, bid)
        if ok and objs:
            found = list(objs)[0]
    if found is None:
        ok, acts = call(item, "GameplayStatics.get_all_actors_of_class(world, %s)" % cls.__name__, unreal.GameplayStatics.get_all_actors_of_class, world, cls)
        if ok and acts:
            found = list(acts)[0]
    log("spawned actor for binding: %s" % short(found))
    return found, player


def make_component_binding(item, seq, actor_binding, tpl, prop, label):
    """Create the child possessable (component binding) of a spawnable, as the Sequencer editor does: spawn the spawnable through a
    level sequence player in a world, then LevelSequence.add_possessable(<live component>). Returns a binding proxy or None."""
    cls = type(tpl)
    # 1. direct on the template component (expected to fail: the template has no world)
    try:
        comp = tpl.get_editor_property(prop)
        ok, newb = call(item, "LevelSequence.add_possessable(<template %s>)" % label, seq.add_possessable, comp)
        if ok and newb is not None and newb.is_valid():
            return newb
        log("add_possessable(template component) gave an invalid binding (expected: the template has no world)")
    except Exception as exc:  # noqa: BLE001
        log("component binding: template has no %s (%s)" % (prop, exc))
    # 2. through a world and a player
    world = get_world(item)
    if world is None:
        note("component binding for %s: no world available headless" % label)
        return None
    actor, player = spawned_actor(item, seq, actor_binding, world, cls)
    if actor is None:
        note("component binding for %s: the spawnable did not spawn" % label)
        return None
    try:
        live_comp = actor.get_editor_property(prop)
    except Exception as exc:  # noqa: BLE001
        note("live actor has no %s: %s" % (prop, exc))
        return None
    ok, newb = call(item, "LevelSequence.add_possessable(<live %s of the spawned actor>)" % label, seq.add_possessable, live_comp)
    try:
        call(item, "LevelSequencePlayer.stop()", player.stop)
    except Exception:  # noqa: BLE001
        pass
    if ok and newb is not None and newb.is_valid():
        try:
            parent = newb.get_parent()
            log("component binding '%s' id=%s parent=%s (spawnable %s)" % (newb.get_name(), guid_str(newb.get_id()),
                                                                           guid_str(parent.get_id()) if parent.is_valid() else None, guid_str(actor_binding.get_id())))
        except Exception as exc:  # noqa: BLE001
            log("parent read failed: %s" % exc)
        return newb
    return None


def build_cube(seq, warden_binding):
    item = "c"
    ok, binding = add_spawnable(item, seq, unreal.StaticMeshActor)
    if not ok:
        return None
    call(item, "MovieSceneBindingProxy.set_name('Cube')", binding.set_name, "Cube")
    tpl = template_of(item, binding)
    cube = unreal.load_asset(CUBE_PATH)
    if tpl is not None and cube is not None:
        smc = tpl.get_editor_property("static_mesh_component")
        call(item, "StaticMeshComponent.set_static_mesh(/Engine/BasicShapes/Cube)", smc.set_static_mesh, cube)
        first_ok(item, [("StaticMeshComponent.set_relative_scale3d(0.2)", lambda: smc.set_relative_scale3d(unreal.Vector(0.2, 0.2, 0.2)) or True),
                        ("Actor.set_actor_scale3d(0.2)", lambda: tpl.set_actor_scale3d(unreal.Vector(0.2, 0.2, 0.2)) or True)])
    ok, track = call(item, "MovieSceneBindingProxy.add_track(MovieScene3DAttachTrack)", binding.add_track, unreal.MovieScene3DAttachTrack)
    if not ok:
        return binding
    ok, wid = call(item, "LevelSequence.get_binding_id(Warden binding)", seq.get_binding_id, warden_binding)
    head = results["mesh_info"].get("head_bone") or "head"
    rhand = results["mesh_info"].get("right_hand_bone") or "hand_r"
    ok1, s1 = call(item, "MovieSceneTrack.add_section() [attach 1]", track.add_section)
    if ok1:
        call(item, "MovieSceneSection.set_range_seconds(0,4) [attach 1]", s1.set_range_seconds, 0.0, 4.0)
        call(item, "MovieScene3DConstraintSection.set_constraint_binding_id(Warden) [attach 1]", s1.set_constraint_binding_id, wid)
        call(item, "MovieScene3DAttachSection.set_editor_property('attach_socket_name', %s)" % head, s1.set_editor_property, "attach_socket_name", unreal.Name(head))
    ok2, s2 = call(item, "MovieSceneTrack.add_section() [attach 2]", track.add_section)
    if ok2:
        call(item, "MovieSceneSection.set_range_seconds(4,10) [attach 2]", s2.set_range_seconds, 4.0, 10.0)
        call(item, "MovieScene3DConstraintSection.set_constraint_binding_id(Warden) [attach 2]", s2.set_constraint_binding_id, wid)
        call(item, "MovieScene3DAttachSection.set_editor_property('attach_socket_name', %s)" % rhand, s2.set_editor_property, "attach_socket_name", unreal.Name(rhand))
        for p in ("attachment_location_rule", "attachment_rotation_rule", "attachment_scale_rule"):
            call(item, "MovieScene3DAttachSection.set_editor_property('%s', KEEP_WORLD)" % p, s2.set_editor_property, p, unreal.AttachmentRule.KEEP_WORLD)
    return binding


def build_light(seq):
    item = "d"
    ok, binding = add_spawnable(item, seq, unreal.PointLight)
    if not ok:
        return None
    call(item, "MovieSceneBindingProxy.set_name('Lantern')", binding.set_name, "Lantern")
    tpl = template_of(item, binding)
    if tpl is not None:
        lc = tpl.get_editor_property("light_component")
        try:
            results["light_unit"] = str(lc.get_editor_property("intensity_units"))
            log("PointLight template intensity_units = %s, intensity = %s" % (results["light_unit"], lc.get_editor_property("intensity")))
        except Exception as exc:  # noqa: BLE001
            note("intensity unit read failed: %s" % exc)
    target = make_component_binding(item, seq, binding, tpl, "light_component", "PointLightComponent")
    results["d_route"] = "component binding" if target is not None else "actor binding (no component binding was possible)"
    target = target if target is not None else binding
    ok, track = call(item, "MovieSceneBindingProxy.add_track(MovieSceneFloatTrack)", target.add_track, unreal.MovieSceneFloatTrack)
    if not ok:
        return binding
    call(item, "MovieScenePropertyTrack.set_property_name_and_path('Intensity','Intensity')", track.set_property_name_and_path, unreal.Name("Intensity"), "Intensity")
    ok, sec = call(item, "MovieSceneTrack.add_section() [intensity]", track.add_section)
    if ok:
        call(item, "MovieSceneSection.set_range_seconds(0,10) [intensity]", sec.set_range_seconds, 0.0, 10.0)
        ok, chs = call(item, "MovieSceneSection.get_all_channels() [intensity]", sec.get_all_channels)
        if ok and chs:
            log("intensity channel class: %s" % clsname(chs[0]))
            for secs, v in SPEC["light"]["keys"]:
                add_channel_key(item, "float channel.add_key(frame %d, %s)" % (disp_frame(secs), v), chs[0], disp_frame(secs), float(v))
    return binding


def build_audio(seq, warden_binding):
    item = "e"
    for sub, path, secs, where in (("e1", SND_MASTER, 1.0, "master"), ("e2", SND_WARDEN, 2.0, "warden")):
        snd = unreal.load_asset(path)
        if snd is None:
            results["errors"].append({"item": sub, "api": "load sound", "error": "not found: " + path})
            continue
        if where == "master":
            ok, track = call(sub, "LevelSequence.add_track(MovieSceneAudioTrack) [master]", seq.add_track, unreal.MovieSceneAudioTrack)
        else:
            ok, track = call(sub, "MovieSceneBindingProxy.add_track(MovieSceneAudioTrack) [Warden]", warden_binding.add_track, unreal.MovieSceneAudioTrack)
        if not ok:
            continue
        ok, sec = call(sub, "MovieSceneTrack.add_section() [audio]", track.add_section)
        if not ok:
            continue
        call(sub, "MovieSceneAudioSection.set_sound(%s)" % snd.get_name(), sec.set_sound, snd)
        ok, dur = call(sub, "SoundBase.get_editor_property('duration')", snd.get_editor_property, "duration")
        dur = float(dur) if ok and dur and dur < 600 else 2.0
        end = min(10.0, secs + dur)
        results.setdefault("audio_durations", {})[sub] = dur
        call(sub, "MovieSceneSection.set_range_seconds(%.3f,%.3f) [audio]" % (secs, end), sec.set_range_seconds, secs, end)


def build_fade(seq):
    item = "f"
    ok, track = call(item, "LevelSequence.add_track(MovieSceneFadeTrack)", seq.add_track, unreal.MovieSceneFadeTrack)
    if not ok:
        return
    ok, sec = call(item, "MovieSceneTrack.add_section() [fade]", track.add_section)
    if not ok:
        return
    call(item, "MovieSceneSection.set_range_seconds(0,10) [fade]", sec.set_range_seconds, 0.0, 10.0)
    ok, chs = call(item, "MovieSceneSection.get_all_channels() [fade]", sec.get_all_channels)
    if ok and chs:
        log("fade channels: %d (%s)" % (len(chs), clsname(chs[0])))
        for secs, v in SPEC["fade"]:
            add_channel_key(item, "fade channel.add_key(frame %d, %s)" % (disp_frame(secs), v), chs[0], disp_frame(secs), float(v))


def build_markers(seq):
    item = "g"
    tps = ticks_per_sec(seq)
    for label, secs in SPEC["markers"]:
        mf = unreal.MovieSceneMarkedFrame()
        mf.set_editor_property("label", label)
        mf.set_editor_property("frame_number", fn_(disp_frame(secs)))
        first_ok(item, [("LevelSequence.add_marked_frame_to_sequence('%s', frame %d, DISPLAY_RATE)" % (label, disp_frame(secs)),
                         lambda mf=mf: seq.add_marked_frame_to_sequence(mf, unreal.MovieSceneTimeUnit.DISPLAY_RATE)),
                        ("LevelSequence.add_marked_frame('%s') [tick resolution]" % label,
                         lambda secs=secs, label=label: seq.add_marked_frame(_mf_ticks(label, secs, tps)))])


def _mf_ticks(label, secs, tps):
    mf = unreal.MovieSceneMarkedFrame()
    mf.set_editor_property("label", label)
    mf.set_editor_property("frame_number", fn_(int(round(secs * tps))))
    return mf


def do_build():
    log("BUILD start")
    results["mesh_info"], mesh = read_warden_mesh()
    log("SK_Warden slots: %s" % json.dumps(results["mesh_info"]["slots"]))
    log("SK_Warden bones (%d): head=%s right_hand=%s; first 40: %s" % (results["mesh_info"].get("bone_count", 0), results["mesh_info"]["head_bone"],
                                                                      results["mesh_info"]["right_hand_bone"], results["mesh_info"]["bones"][:40]))
    log("slot pick: %s" % results["mesh_info"]["slot_pick"])
    api_dump()
    seq = create_or_load_sequence()
    if seq is None:
        results["fatal"] = "could not create LS_P17_Spike"
        return
    set_defaults(seq)
    warden = None
    try:
        build_camera(seq)
    except Exception:  # noqa: BLE001
        results["errors"].append({"item": "a", "api": "(exception)", "error": traceback.format_exc()})
        unreal.log_error("%s: EXCEPTION in camera: %s" % (TAG, traceback.format_exc()))
    try:
        warden = build_warden(seq, results["mesh_info"], mesh)
    except Exception:  # noqa: BLE001
        results["errors"].append({"item": "b", "api": "(exception)", "error": traceback.format_exc()})
        unreal.log_error("%s: EXCEPTION in warden: %s" % (TAG, traceback.format_exc()))
    for name, fn in (("cube", lambda: build_cube(seq, warden)), ("light", lambda: build_light(seq)),
                     ("audio", lambda: build_audio(seq, warden)), ("fade", lambda: build_fade(seq)), ("markers", lambda: build_markers(seq))):
        try:
            fn()
        except Exception:  # noqa: BLE001
            results["errors"].append({"item": name, "api": "(exception)", "error": traceback.format_exc()})
            unreal.log_error("%s: EXCEPTION in %s: %s" % (TAG, name, traceback.format_exc()))
    # the one explicit save of the one package
    ok, saved = call("save", "EditorAssetLibrary.save_asset('%s', only_if_is_dirty=False)" % SEQ_PATH, EAL.save_asset, SEQ_PATH, False)
    results["saved"] = bool(ok and saved)
    dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    results["dirty_after_save"] = dirty
    log("dirty packages after the save (NOT saved by this script): %s" % dirty)
    os.makedirs(os.path.dirname(BUILD_RECORD), exist_ok=True)


# ================================================================================================================ VERIFY
checks = []   # {item, name, ok, got, want}


def chk(item, name, got, want, tol=None):
    if tol is not None:
        try:
            ok = abs(float(got) - float(want)) <= tol
        except Exception:  # noqa: BLE001
            ok = False
    else:
        ok = got == want
    checks.append({"item": item, "name": name, "ok": bool(ok), "got": short(got, 120), "want": short(want, 120)})
    if not ok:
        unreal.log_error("%s: CHECK FAILED [%s] %s: got %s want %s" % (TAG, item, name, short(got, 120), short(want, 120)))
    return ok


def read_channel_keys(seq, ch):
    """[(seconds, value)] for a scripting channel; values are raw."""
    out = []
    for k in ch.get_keys():
        t = k.get_time()
        frame = t.frame_number.value if hasattr(t, "frame_number") else int(t)
        out.append((round(frame / float(FPS), 4), k.get_value()))
    return out


def bindings_by_name(seq):
    d = {}
    for b in seq.get_bindings():
        d[b.get_name()] = b
    return d


def en(e):
    """Name of a Python-wrapped enum value, e.g. ALWAYS_TICK_POSE."""
    return getattr(e, "name", str(e))


def track_cls(track):
    return clsname(track)


def v_tracks(binding):
    return [(track_cls(t), t) for t in binding.get_tracks()]


def find_track(binding_or_seq, clsname_):
    return [t for t in binding_or_seq.get_tracks() if track_cls(t) == clsname_]


def secs_of(sec):
    return (round(sec.get_start_frame_seconds(), 4), round(sec.get_end_frame_seconds(), 4))


def do_verify():
    log("VERIFY start (fresh process)")
    try:
        build_rec = json.load(open(BUILD_RECORD, encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        build_rec = {}
        note("no build record: %s" % exc)
    results["build_record"] = build_rec
    seq = unreal.load_asset(SEQ_PATH)
    if seq is None:
        chk("setup", "LS_P17_Spike loads", None, "LevelSequence")
        return
    chk("setup", "asset class", clsname(seq), "LevelSequence")
    dr = seq.get_display_rate()
    chk("setup", "display rate", (dr.numerator, dr.denominator), SPEC["display_rate"])
    chk("setup", "playback start s", seq.get_playback_start_seconds(), 0.0, 0.001)
    chk("setup", "playback end s", seq.get_playback_end_seconds(), 10.0, 0.001)
    tps = ticks_per_sec(seq)
    results["tick_resolution"] = tps

    spawnable_ids = {guid_str(b.get_id()) for b in seq.get_spawnables()}
    possessable_ids = {guid_str(b.get_id()) for b in seq.get_possessables()}
    binds = {}
    for b in seq.get_bindings():
        binds.setdefault(b.get_name(), []).append(b)
    results["bindings"] = [{"name": b.get_name(), "id": guid_str(b.get_id()), "spawnable": guid_str(b.get_id()) in spawnable_ids,
                            "possessable": guid_str(b.get_id()) in possessable_ids,
                            "class": (clsname(b.get_object_template()) if guid_str(b.get_id()) in spawnable_ids and b.get_object_template() else
                                      str(b.get_possessed_object_class().get_name() if b.get_possessed_object_class() else None)),
                            "tracks": [track_cls(t) for t in b.get_tracks()],
                            "parent": (guid_str(b.get_parent().get_id()) if (b.get_parent() and b.get_parent().is_valid()) else None)} for b in seq.get_bindings()]
    for rec in results["bindings"]:
        log("BINDING %s" % json.dumps(rec))
    results["master_tracks"] = [track_cls(t) for t in seq.get_tracks()]
    log("MASTER TRACKS %s" % results["master_tracks"])

    def one(name):
        lst = binds.get(name)
        return lst[0] if lst else None

    # ---- a
    cam = one("Cam_Spike")
    chk("a", "camera binding exists", cam is not None, True)
    if cam is not None:
        chk("a", "camera is spawnable", guid_str(cam.get_id()) in spawnable_ids, True)
        tpl = cam.get_object_template()
        chk("a", "camera template class", clsname(tpl), "CineCameraActor")
        comp = tpl.get_editor_property("camera_component")
        fb = comp.get_editor_property("filmback")
        chk("a", "filmback sensor width (16:9 DSLR preset = 36.0)", fb.sensor_width, 36.0, 0.01)
        chk("a", "filmback sensor height (16:9 DSLR preset = 20.25)", fb.sensor_height, 20.25, 0.01)
        try:
            results["filmback_preset_name"] = str(comp.get_filmback_preset_name())
        except Exception:  # noqa: BLE001
            pass
        chk("a", "focal length", comp.get_editor_property("current_focal_length"), 30.0, 0.001)
        tts = find_track(cam, "MovieScene3DTransformTrack")
        chk("a", "transform track count", len(tts), 1)
        if tts:
            sec = tts[0].get_sections()[0]
            chs = sec.get_all_channels()
            for idx, nm in ((0, "Location.X"), (1, "Location.Y"), (2, "Location.Z")):
                keys = read_channel_keys(seq, chs[idx])
                chk("a", "camera %s keys" % nm, len(keys), 2)
            z = read_channel_keys(seq, chs[2])
            chk("a", "camera Z keys", [(t, round(v, 2)) for t, v in z], [(0.0, 652.79), (10.0, 152.79)])
        cut_tracks = find_track(seq, "MovieSceneCameraCutTrack")
        chk("a", "camera cut track count", len(cut_tracks), 1)
        if cut_tracks:
            secs_ = cut_tracks[0].get_sections()
            chk("a", "camera cut section count", len(secs_), 1)
            if secs_:
                cs = secs_[0]
                bid = cs.get_camera_binding_id()
                chk("a", "camera cut bound to the camera spawnable", guid_str(bid.get_editor_property("guid")), guid_str(cam.get_id()))
                chk("a", "ease in (s)", cs.get_ease_in_duration() / tps, 1.0, 0.001)
                chk("a", "ease out (s)", cs.get_ease_out_duration() / tps, 1.5, 0.001)
            lib = getattr(unreal, "LBCineAuthoringLibrary", None)
            cb = None
            if lib is not None:
                try:
                    cb = lib.get_camera_cut_track_can_blend(cut_tracks[0])
                except Exception as exc:  # noqa: BLE001
                    note("get_camera_cut_track_can_blend failed: %s" % exc)
            else:
                note("unreal.LBCineAuthoringLibrary is missing")
            results["can_blend_readback"] = cb
            chk("a.can_blend", "camera cut track bCanBlend (LBCineAuthoringLibrary.get_camera_cut_track_can_blend)", cb, True)

    # ---- b
    w = one("WardenFigure")
    chk("b", "warden binding exists", w is not None, True)
    if w is not None:
        chk("b", "warden is spawnable", guid_str(w.get_id()) in spawnable_ids, True)
        tpl = w.get_object_template()
        chk("b", "warden template class", clsname(tpl), "SkeletalMeshActor")
        smc = tpl.get_editor_property("skeletal_mesh_component")
        mesh = smc.get_editor_property("skeletal_mesh_asset") if smc else None
        chk("b", "skeletal mesh asset", mesh.get_name() if mesh else None, "SK_Warden")
        ac = smc.get_editor_property("anim_class") if smc else None
        chk("b", "anim class", ac.get_name() if ac else None, SPEC["warden"]["anim_class"])
        chk("b", "actor tag", [str(t) for t in tpl.get_editor_property("tags")], [SPEC["warden"]["tag"]])
        tick_opt = smc.get_editor_property("visibility_based_anim_tick_option") if smc else None
        chk("b", "VisibilityBasedAnimTickOption", en(tick_opt), "ALWAYS_TICK_POSE")
        # b1
        tts = find_track(w, "MovieScene3DTransformTrack")
        chk("b1", "transform track count", len(tts), 1)
        if tts:
            chs = tts[0].get_sections()[0].get_all_channels()
            kx = read_channel_keys(seq, chs[0])
            chk("b1", "Location.X keys", [(t, round(v, 3)) for t, v in kx], [(0.0, 0.0), (5.0, 300.0)])
            for idx, nm in ((1, "Location.Y"), (2, "Location.Z"), (5, "Rotation.Z (yaw)")):
                kk = read_channel_keys(seq, chs[idx])
                chk("b1", "%s keys" % nm, [(t, round(v, 3)) for t, v in kk], [(0.0, 0.0), (5.0, 0.0)])
        # b2
        vts = find_track(w, "MovieSceneVisibilityTrack")
        chk("b2", "visibility track count", len(vts), 1)
        if vts:
            chk("b2", "visibility property name", str(vts[0].get_property_name()), "bHidden")
            sec = vts[0].get_sections()[0]
            chs = sec.get_all_channels()
            kv = read_channel_keys(seq, chs[0])
            chk("b2", "visibility keys (visible 0-8 s, hidden 8-10 s)", kv, [(0.0, True), (8.0, False)])
        # b3
        ats = find_track(w, "MovieSceneSkeletalAnimationTrack")
        chk("b3", "skeletal animation track count", len(ats), 1)
        if ats:
            secs_ = ats[0].get_sections()
            chk("b3", "skeletal animation section count", len(secs_), 1)
            if secs_:
                params = secs_[0].get_editor_property("params")
                an = params.get_editor_property("animation")
                chk("b3", "animation asset", an.get_name() if an else None, os.path.basename(build_rec.get("anim_used") or ANIM_PRIMARY))
                chk("b3", "slot name", str(params.get_editor_property("slot_name")), "DefaultSlot")
                results["b3_section_s"] = secs_of(secs_[0])
        # b4: component material track may be on the component binding or on the actor binding
        mt_where = None
        mts = find_track(w, "MovieSceneComponentMaterialTrack")
        mt_binding = w
        if mts:
            mt_where = "actor binding"
        else:
            for b in seq.get_bindings():
                if guid_str(b.get_id()) in possessable_ids and b.get_parent() and b.get_parent().is_valid() and guid_str(b.get_parent().get_id()) == guid_str(w.get_id()):
                    mt = find_track(b, "MovieSceneComponentMaterialTrack")
                    if mt:
                        mts, mt_where, mt_binding = mt, "component binding '%s'" % b.get_name(), b
        results["b4_where_readback"] = mt_where
        chk("b4", "component material track exists", len(mts), 1)
        if mts:
            info = mts[0].get_material_info()
            want_slot = (build_rec.get("b4_slot") or {})
            chk("b4", "material slot name", str(info.get_editor_property("material_slot_name")), want_slot.get("slot_name"))
            chk("b4", "material slot index", info.get_editor_property("material_slot_index"), want_slot.get("index"))
            chk("b4", "material type", en(info.get_editor_property("material_type")), "INDEXED_MATERIAL")
            sec = mts[0].get_sections()[0]
            # the parameter name: the section's channels are named after the parameter (no Python reader for the parameter list)
            keys = None
            try:
                ch = sec.get_channel(unreal.Name("Fade"))
                chk("b4", "channel named 'Fade' exists", ch is not None, True)
                if ch is not None:
                    keys = [(t, round(v, 4)) for t, v in read_channel_keys(seq, ch)]
                results["b4_channel_count"] = len(sec.get_all_channels())
                chk("b4", "section has exactly one channel", results["b4_channel_count"], 1)
            except Exception as exc:  # noqa: BLE001
                note("b4 channel-by-name read failed: %s" % exc)
                chk("b4", "channel named 'Fade' exists", None, True)
            try:
                bogus = sec.get_channel(unreal.Name("NoSuchParameter"))
            except Exception:  # noqa: BLE001
                bogus = None
            chk("b4", "negative control: channel 'NoSuchParameter' absent", bogus is None, True)
            want = [(round(t, 4), v) for t, v in SPEC["warden"]["fade_keys"]]
            chk("b4", "Fade keys (time s, value)", keys, want)

    # ---- c
    cube = one("Cube")
    chk("c", "cube binding exists", cube is not None, True)
    if cube is not None:
        chk("c", "cube is spawnable", guid_str(cube.get_id()) in spawnable_ids, True)
        tpl = cube.get_object_template()
        chk("c", "cube template class", clsname(tpl), "StaticMeshActor")
        smc = tpl.get_editor_property("static_mesh_component")
        sm = smc.get_editor_property("static_mesh")
        chk("c", "static mesh", sm.get_name() if sm else None, "Cube")
        scl = smc.get_editor_property("relative_scale3d")
        chk("c", "scale", (round(scl.x, 3), round(scl.y, 3), round(scl.z, 3)), (0.2, 0.2, 0.2))
        ats = find_track(cube, "MovieScene3DAttachTrack")
        chk("c", "attach track count", len(ats), 1)
        if ats:
            secs_ = sorted(ats[0].get_sections(), key=lambda s: s.get_start_frame_seconds())
            chk("c", "attach section count", len(secs_), 2)
            mi = build_rec.get("mesh_info", {})
            want = [(SPEC["cube"]["att1"], mi.get("head_bone")), (SPEC["cube"]["att2"], mi.get("right_hand_bone"))]
            for i, (s, (rng, bone)) in enumerate(zip(secs_, want)):
                sub = "c%d" % (i + 1)
                chk(sub, "range (s)", secs_of(s), rng)
                chk(sub, "attach socket/bone", str(s.get_editor_property("attach_socket_name")), bone)
                tgt = s.get_constraint_binding_id()
                chk(sub, "attached to the Warden binding", guid_str(tgt.get_editor_property("guid")), guid_str(w.get_id()) if w else None)
                rules = [en(s.get_editor_property(p)) for p in ("attachment_location_rule", "attachment_rotation_rule", "attachment_scale_rule")]
                results["attach_rules_%d" % (i + 1)] = rules
                if i == 1:
                    chk(sub, "attachment rules (loc/rot/scale)", rules, ["KEEP_WORLD"] * 3)

    # ---- d
    lt = one("Lantern")
    chk("d", "light binding exists", lt is not None, True)
    if lt is not None:
        chk("d", "light is spawnable", guid_str(lt.get_id()) in spawnable_ids, True)
        chk("d", "light template class", clsname(lt.get_object_template()), "PointLight")
        lc = lt.get_object_template().get_editor_property("light_component")
        results["light_unit_readback"] = str(lc.get_editor_property("intensity_units"))
        # intensity track on the actor binding or on a child possessable
        its = []
        where = None
        cand = [lt] + [b for b in seq.get_bindings() if guid_str(b.get_id()) in possessable_ids and b.get_parent() and b.get_parent().is_valid()
                       and guid_str(b.get_parent().get_id()) == guid_str(lt.get_id())]
        for b in cand:
            f = [t for t in find_track(b, "MovieSceneFloatTrack")]
            if f:
                its, where = f, ("actor binding" if b is lt else "component binding '%s'" % b.get_name())
                break
        results["d_where_readback"] = where
        chk("d", "float track count", len(its), 1)
        if its:
            chk("d", "property name", str(its[0].get_property_name()), "Intensity")
            chs = its[0].get_sections()[0].get_all_channels()
            kk = read_channel_keys(seq, chs[0])
            chk("d", "intensity keys", [(t, round(v, 3)) for t, v in kk], [(0.0, 0.0), (1.0, 600.0)])

    # ---- e
    for sub, where, want_path, want_s in (("e1", "master", SND_MASTER, 1.0), ("e2", "warden", SND_WARDEN, 2.0)):
        tracks = find_track(seq, "MovieSceneAudioTrack") if where == "master" else (find_track(w, "MovieSceneAudioTrack") if w else [])
        chk(sub, "audio track count (%s)" % where, len(tracks), 1)
        if tracks:
            secs_ = tracks[0].get_sections()
            chk(sub, "audio section count", len(secs_), 1)
            if secs_:
                snd = secs_[0].get_sound()
                chk(sub, "sound", snd.get_name() if snd else None, os.path.basename(want_path))
                chk(sub, "start (s)", secs_[0].get_start_frame_seconds(), want_s, 0.001)

    # ---- f
    fts = find_track(seq, "MovieSceneFadeTrack")
    chk("f", "fade track count", len(fts), 1)
    if fts:
        chs = fts[0].get_sections()[0].get_all_channels()
        kk = read_channel_keys(seq, chs[0])
        chk("f", "fade keys", [(t, round(v, 3)) for t, v in kk], [(t, v) for t, v in SPEC["fade"]])

    # ---- g
    marks = []
    for m in seq.get_marked_frames_from_sequence(unreal.MovieSceneTimeUnit.DISPLAY_RATE):
        fnum = m.get_editor_property("frame_number").value
        marks.append({"label": str(m.get_editor_property("label")), "frame": fnum, "seconds": round(fnum / float(FPS), 4)})
    results["marked_frames"] = marks
    for label, secs in SPEC["markers"]:
        found = [m for m in marks if m["label"] == label]
        chk("g", "marker '%s' present" % label, len(found), 1)
        if found:
            chk("g", "marker '%s' frame" % label, found[0]["frame"], disp_frame(secs))
            chk("g", "marker '%s' seconds" % label, found[0]["seconds"], secs, 0.001)
    chk("g", "marked frame count", len(marks), 3)


# ---------------------------------------------------------------------------------------------------------------- verdict + output
MCP_HINTS = {   # item -> Sequencer-toolset tools listed in Docs/ArtTest/cine/p17_f0_tables.md section 1 that cover the item
    "a.can_blend": [],   # no listed tool sets the camera cut track's bCanBlend; the C++ helper ULBCineAuthoringLibrary does
    "b4": ["SequencerTools.get_child_possessables", "SequencerTools.add_track_to_binding", "SequencerTools.rebind_component"],
    "d": ["SequencerTools.get_child_possessables", "SequencerTools.add_track_to_binding", "SequencerTools.rebind_component"],
}

# python API used per item (class.method), for the JSON; filled from the call log by item prefix
FINDINGS = [
    "Run: UnrealEditor-Cmd -run=pythonscript works with the editor closed; build 11 s, verify 9 s (log lines tagged P17S1). Mode by the environment variable P17_MODE=build|verify.",
    "Tick resolution of a new LevelSequence is 24000, display rate set to 30 fps; 1 display frame = 800 ticks.",
    "Time units differ per API: channel.add_key(FrameNumber) and key.get_time() are DISPLAY frames by default; MovieSceneSection.set_ease_in_duration / set_ease_out_duration take TICKS (1.0 s = 24000); "
    "MovieSceneComponentMaterialParameterSection.add_scalar_parameter_key takes a TICK FrameNumber (a display frame passed there landed at ~0 s in the first build); set_range_seconds / get_*_seconds take seconds.",
    "LevelSequence.add_spawnable_from_class is deprecated since 5.5 ('use the Level Sequence Editor Subsystem'), but the subsystem's add_spawnable_from_class returns an invalid binding headless (sequence None). The deprecated function works and logs one DeprecationWarning per call.",
    "The 'Add Marked Frame' / 'Get Marked Frames' tick-resolution variants are deprecated; add_marked_frame_to_sequence(frame, unreal.MovieSceneTimeUnit.DISPLAY_RATE) and get_marked_frames_from_sequence(unreal.MovieSceneTimeUnit.DISPLAY_RATE) work (there is no unreal.SequenceTimeUnit).",
    "CineCameraComponent.set_filmback_preset_by_name('16:9 DSLR') gives sensor 36.0 x 20.25 mm (not 23.76 x 13.365). The camera component of the template is tpl.get_editor_property('camera_component'); tpl.get_cine_camera_component() returns None on a template. Focal length: set_editor_property('current_focal_length', v).",
    "Component bindings (needed for the Component Material Parameter track and the light Intensity track) CAN be scripted headless: the template component gives an invalid binding from add_possessable, but spawning the spawnable through a LevelSequencePlayer in the commandlet's Untitled editor world "
    "(EditorLevelLibrary.get_editor_world, LevelSequencePlayer.create_level_sequence_player, set_playback_position(frame 0, JUMP), player.get_bound_objects(binding id)) and calling LevelSequence.add_possessable(<live component>) creates a child possessable (parent = the spawnable) named SkeletalMeshComponent0 / LightComponent0. Nothing from that world is saved.",
    "Runtime resolution of those two component bindings (and of the attach, material fade, blend) is NOT proven by the read-back; it is what S1b (PIE) has to confirm.",
    "bCanBlend of MovieSceneCameraCutTrack is a plain UPROPERTY(): Python set_editor_property fails ('Failed to find property'), and ToolsetLibrary.set_object_properties / get_object_properties refuse it; no Sequencer MCP tool sets it. "
    "It is scripted through the project's C++ helper: unreal.LBCineAuthoringLibrary.set_camera_cut_track_can_blend(track, True) / get_camera_cut_track_can_blend(track). Call it RIGHT AFTER creating the camera cut track and BEFORE adding its section and eases: with bCanBlend false the engine strips eases (RearrangeAllSections removes overlaps and easings, SupportsEasing returns None).",
    "Component material track: MovieSceneComponentMaterialTrack.set_material_info(ComponentMaterialInfo{material_slot_name, material_slot_index, material_type=INDEXED_MATERIAL}); parameter keys via section.add_scalar_parameter_key(MaterialParameterInfo(name='Fade'), tick FrameNumber, value, '', ''); read back with section.get_channel(Name('Fade')) (the channel is named after the parameter). get_material_info logs a (misleading) deprecation warning.",
    "Visibility track: MovieSceneVisibilityTrack with set_property_name_and_path('bHidden','bHidden'); the bool channel stores VISIBLE semantics (True = visible).",
    "Attach: MovieScene3DAttachSection.set_constraint_binding_id(sequence.get_binding_id(parent binding)); attach_socket_name and attachment_*_rule are editor properties (unreal.AttachmentRule.KEEP_WORLD).",
    "Skeletal animation: section.get_editor_property('params') -> set animation and slot_name -> section.set_editor_property('params', params); set_range_seconds to the clip length (AN_Warden_LookAround is 4.467 s).",
    "PointLight spawnable template: intensity_units is UNITLESS (not lumens) and intensity 5000 by default. The plan's 600 lm Lantern needs intensity_units = LUMENS set on the template component in P17-5a.",
]


ITEM_ORDER = ["setup", "a", "a.can_blend", "b", "b1", "b2", "b3", "b4", "c", "c1", "c2", "d", "e", "e1", "e2", "f", "g"]


def write_output():
    build_rec = results.get("build_record", {})
    items = {}
    for it in ITEM_ORDER:
        its = [c for c in checks if c["item"] == it]
        # parent rows aggregate their sub rows (c = c1 + c2, e = e1 + e2)
        if it == "c":
            its = [c for c in checks if c["item"] in ("c", "c1", "c2")]
        if it == "e":
            its = [c for c in checks if c["item"] in ("e1", "e2")]
        if it == "a":
            its = [c for c in checks if c["item"] in ("a", "a.can_blend")]
        if not its:
            continue
        failed = [c for c in its if not c["ok"]]
        build_calls = [c for c in build_rec.get("calls", []) if c["item"] == it or (it == "c" and c["item"] == "c") or (it == "e" and c["item"] in ("e1", "e2"))]
        apis = []
        for c in build_calls:
            if c["api"] not in apis:
                apis.append(c["api"])
        errs = [c for c in build_calls if not c["ok"]]
        if not failed:
            status = "scripted OK (via ULBCineAuthoringLibrary)" if it == "a" else "scripted OK"
        else:
            status = "needs MCP" if MCP_HINTS.get(it) else "needs manual editor step"
        parts = None
        if it == "a":
            parts = {"camera spawnable, filmback, focal length, transform track": "scripted OK",
                     "camera cut track, section bound to the camera, ease in 1.0 s, ease out 1.5 s": "scripted OK",
                     "camera cut track bCanBlend = true (ULBCineAuthoringLibrary)": "needs manual editor step" if any(c["item"] == "a.can_blend" and not c["ok"] for c in checks) else "scripted OK (via ULBCineAuthoringLibrary)"}
        items[it] = {"status": status, "apis": apis, "values_read_back": [{"check": c["name"], "got": c["got"], "want": c["want"], "ok": c["ok"]} for c in its],
                     "failed_checks": [c["name"] for c in failed], "build_call_errors": [{"api": e["api"], "error": e.get("error")} for e in errs],
                     "mcp_tools_listed": MCP_HINTS.get(it, []), "parts": parts}
    out = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "asset": SEQ_PATH, "items": items,
           "warden_mesh": build_rec.get("mesh_info"), "b4_route_at_build": build_rec.get("b4_route"), "b4_route_readback": results.get("b4_where_readback"),
           "d_route_at_build": build_rec.get("d_route"), "d_route_readback": results.get("d_where_readback"),
           "light_unit": build_rec.get("light_unit"), "light_unit_readback": results.get("light_unit_readback"),
           "anim_used": build_rec.get("anim_used"), "anim_length_s": build_rec.get("anim_length_s"),
           "bindings": results.get("bindings"), "master_tracks": results.get("master_tracks"), "marked_frames": results.get("marked_frames"),
           "can_blend_after_build": build_rec.get("can_blend_after_build"), "can_blend_readback": results.get("can_blend_readback"),
           "build_errors": build_rec.get("errors"), "build_notes": build_rec.get("notes"), "verify_notes": results.get("notes"),
           "check_count": len(checks), "failed_count": len([c for c in checks if not c["ok"]]),
           "findings": FINDINGS,
           "caveat": "scripted OK = read back correctly from the reloaded asset. Nothing here proves runtime behaviour (spawn, blend, attach, material fade): that is S1b."}
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    log("wrote %s" % OUT_JSON)


def main():
    if MODE == "build":
        do_build()
        with open(BUILD_RECORD, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=1)
        log("BUILD done: %d calls, %d errors; saved=%s" % (len(results["calls"]), len(results["errors"]), results.get("saved")))
    elif MODE == "verify":
        do_verify()
        write_output()
        bad = [c for c in checks if not c["ok"]]
        log("VERIFY done: %d checks, %d failed" % (len(checks), len(bad)))
        for c in bad:
            log("  FAIL [%s] %s: got %s want %s" % (c["item"], c["name"], c["got"], c["want"]))
    else:
        unreal.log_error("%s: set P17_MODE=build or P17_MODE=verify (or pass --build / --verify)" % TAG)


try:
    main()
except Exception:  # noqa: BLE001
    unreal.log_error("%s: EXCEPTION %s" % (TAG, traceback.format_exc()))
    if MODE == "verify":
        try:
            write_output()
        except Exception:  # noqa: BLE001
            pass
    if MODE == "build":
        try:
            results["fatal"] = traceback.format_exc()
            with open(BUILD_RECORD, "w", encoding="utf-8") as fh:
                json.dump(results, fh, indent=1)
        except Exception:  # noqa: BLE001
            pass
