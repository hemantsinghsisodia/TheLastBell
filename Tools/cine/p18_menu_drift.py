"""P18-S1 part 1: build LS_LB_MenuDrift headless (Unreal CLOSED), the 40 s looping camera move for the menu video (Docs/plans/P18_UI_SETTINGS.md section 3).
Reuses the helpers of Tools/cine/p17_sequences.py (spawnable CineCamera, camera template, camera-cut track with bCanBlend, key readers, check helpers).

Run (editor closed, never two at once; the Warden\\output\\unreal_validation process is another project):
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>
Environment:
    P18_MODE     build | check
    P18_REBUILD  1 = reset LS_LB_MenuDrift in place and rebuild it (default: build refuses to touch an existing one)
Build creates /Game/LastBell/Cinematics/LS_LB_MenuDrift and saves ONLY that package. Check runs in a FRESH process and writes
Docs/ArtTest/cine/p18_menu_drift_check.json. Nothing is rendered or captured; no PIE, no MCP.

THE SHOT (pose reasoning in Docs/ArtTest/cine/p18_menu_drift.md): one CineCamera on the approach axis, the line the player walks and Cam_Intro already uses (x -2800, y 0), looking +X over the
gatehouse at the tower. The camera dollies 400 cm along +X and pans 6 deg from 0 to 20 s, and the same move mirrored back from 20 to 40 s. Every key has an AUTO tangent and
the keys at 0, 20 and 40 s are extrema or end keys, so the tangents there are flat (zero speed at 0, 20 and 40 s): the loop has no seam and the turn at 20 s is soft.
"""
import json
import math
import os
import sys
import time
import traceback

os.environ["P17_MODE"] = "lib"          # p17_sequences does nothing at import in this mode (its helpers only)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unreal  # noqa: E402
import p17_sequences as P  # noqa: E402

MODE = os.environ.get("P18_MODE", "").lower()
REBUILD = os.environ.get("P18_REBUILD", "0") == "1"
ROOT = P.ROOT
SEQ_PATH = P.CINE_DIR + "/LS_LB_MenuDrift"
SEQ_KEY = "MenuDrift"
END_S = 40.0
HALF_S = 20.0
OUT_JSON = os.path.join(ROOT, "Docs", "ArtTest", "cine", "p18_menu_drift_check.json")
BUILD_RECORD = os.path.join(ROOT, "Saved", "p18_menu_drift_build.json")
TAG = "P18Menu"

# ---- the pose. Units cm and degrees; UE rotation: yaw + is to the right, pitch + is up.
CAM_X0, CAM_X1 = -2800.0, -2400.0        # dolly 400 cm toward the gate
CAM_Y, CAM_Z = 0.0, 560.0
CAM_YAW0, CAM_YAW1 = 1.0, 7.0            # pan 6 deg to the right
CAM_PITCH = 6.0
FOCAL, APERTURE, FOCUS = 35.0, 2.8, 6000.0
# ---- landmarks for the framing check (F0 survey, Saved/p17_f0_scratch/gate.json, bell.json, tower.json; Docs/TECHNICAL_DESIGN strike target)
GATE_TOP_CENTRE = (0.0, 0.0, 800.0)                  # KG_GateArch bounds X 0..300, Y -600..600, Z 0..800 (the face toward the camera is X 0)
GATE_TOP_LEFT, GATE_TOP_RIGHT = (0.0, -600.0, 800.0), (0.0, 600.0, 800.0)
TOWER_DECK = (12165.0, 2000.0, 2500.0)               # Top_Slab_W centre, the belfry floor
TOWER_BELL = (12420.0, 2000.0, 2860.0)               # BP_TagInteractable_GreatBell top
TOWER_FINIAL = (12530.8, 2000.0, 4824.8)             # TWA_Roof finial tip (the strike target is 20 cm above)
FILMBACK = (36.0, 20.25)                             # 16:9 DSLR


def cam_spec():
    xs = [(0.0, CAM_X0, "A"), (HALF_S, CAM_X1, "A"), (END_S, CAM_X0, "A")]
    ys = [(0.0, CAM_YAW0, "A"), (HALF_S, CAM_YAW1, "A"), (END_S, CAM_YAW0, "A")]
    cam = {"name": "Cam_MenuDrift", "cls": "CineCameraActor",
           "tpl": {"focal": FOCAL, "aperture": APERTURE, "focus": FOCUS, "constrain": False, "pps": False},
           "xf": P.xf_channels(lx=xs, ly=P.single(CAM_Y), lz=P.single(CAM_Z), rr=P.single(0.0), rp=P.single(CAM_PITCH), ry=ys),
           "vis": None, "comps": [], "audio": []}
    return {"key": SEQ_KEY, "path": SEQ_PATH, "end": END_S, "markers": [], "fade": None,
            "cuts": [{"binding": "Cam_MenuDrift", "start": 0.0, "end": END_S, "ease_in": 0.0, "ease_out": 0.0}],
            "bindings": [cam], "audio2d": []}


def log(msg):
    unreal.log("%s: %s" % (TAG, msg))


# ================================================================================================================ BUILD
def build(spec):
    key, path = spec["key"], spec["path"]
    name = path.rsplit("/", 1)[1]
    if P.EAL.does_asset_exist(path):
        seq = unreal.load_asset(path)
        P.reset_sequence(seq)
        P.note("%s existed: reset in place (P18_REBUILD=1)" % name)
    else:
        ok, seq = P.call(key, "AssetTools.create_asset(%s, LevelSequence)" % name, unreal.AssetToolsHelpers.get_asset_tools().create_asset,
                         name, P.CINE_DIR, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
        if not ok or seq is None:
            raise RuntimeError("cannot create " + path)
    P.call(key, "set_display_rate(30/1)", seq.set_display_rate, unreal.FrameRate(30, 1))
    P.call(key, "set_playback_start_seconds(0)", seq.set_playback_start_seconds, 0.0)
    P.call(key, "set_playback_end_seconds(%s)" % END_S, seq.set_playback_end_seconds, END_S)
    tr = seq.get_tick_resolution()
    log("%s: tick resolution %s/%s display %s" % (name, tr.numerator, tr.denominator, seq.get_display_rate().numerator))
    bindings = {}
    for b in spec["bindings"]:
        bindings[b["name"]] = P.build_binding(seq, b, END_S)
    # camera cut: bCanBlend FIRST (the engine strips eases while it is false), one section 0..40 s
    ok, cut_track = P.call(key, "add_track(MovieSceneCameraCutTrack)", seq.add_track, unreal.MovieSceneCameraCutTrack)
    lib = getattr(unreal, "LBCineAuthoringLibrary", None)
    if lib is None:
        P.results["errors"].append({"item": key, "api": "unreal.LBCineAuthoringLibrary", "error": "missing"})
    else:
        P.call(key, "LBCineAuthoringLibrary.set_camera_cut_track_can_blend(track, True)", lib.set_camera_cut_track_can_blend, cut_track, True)
    for c in spec["cuts"]:
        ok, sec = P.call(key, "cut add_section() [%s]" % c["binding"], cut_track.add_section)
        P.call(key, "cut set_range_seconds(%s,%s)" % (c["start"], c["end"]), sec.set_range_seconds, c["start"], c["end"])
        ok, bid = P.call(key, "get_binding_id(%s)" % c["binding"], seq.get_binding_id, bindings[c["binding"]])
        P.call(key, "set_camera_binding_id", sec.set_camera_binding_id, bid)
        P.call(key, "set_ease_in_duration(0)", sec.set_ease_in_duration, 0)
        P.call(key, "set_ease_out_duration(0)", sec.set_ease_out_duration, 0)
    return seq


def do_build():
    spec = cam_spec()
    if P.EAL.does_asset_exist(SEQ_PATH) and not REBUILD:
        msg = "refusing to overwrite %s (set P18_REBUILD=1 to rebuild)" % SEQ_PATH
        P.results["errors"].append({"item": "setup", "api": "exists", "error": msg})
        unreal.log_error("%s: %s" % (TAG, msg))
        return
    try:
        build(spec)
    except Exception:  # noqa: BLE001
        P.results["errors"].append({"item": SEQ_KEY, "api": "(exception)", "error": traceback.format_exc()})
        unreal.log_error("%s: EXCEPTION %s" % (TAG, traceback.format_exc()))
    unreal.SystemLibrary.collect_garbage()
    ok, saved = P.call("save", "EditorAssetLibrary.save_asset('%s', only_if_is_dirty=False)" % SEQ_PATH, P.EAL.save_asset, SEQ_PATH, False)
    if ok and saved:
        P.results["saved"].append(SEQ_PATH)
    dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    P.results["dirty_after_save"] = dirty
    log("dirty packages after the save (NOT saved by this script): %s" % dirty)


# ================================================================================================================ CHECK
def pose_at(t):
    """(x, y, z, yaw, pitch) of the camera at time t (cubic Hermite with zero end tangents on each half: the smoothstep the AUTO keys give)."""
    u = t / HALF_S if t <= HALF_S else (END_S - t) / HALF_S
    s = u * u * (3.0 - 2.0 * u)
    return (CAM_X0 + (CAM_X1 - CAM_X0) * s, CAM_Y, CAM_Z, CAM_YAW0 + (CAM_YAW1 - CAM_YAW0) * s, CAM_PITCH)


def project(pose, pt):
    """(azimuth, elevation, distance) of pt relative to the camera axis in degrees (positive right / up), for yaw and pitch only (roll 0)."""
    x, y, z, yaw, pitch = pose
    dx, dy, dz = pt[0] - x, pt[1] - y, pt[2] - z
    h = math.hypot(dx, dy)
    az = math.degrees(math.atan2(dy, dx)) - yaw
    el = math.degrees(math.atan2(dz, h)) - pitch
    return az, el, math.sqrt(dx * dx + dy * dy + dz * dz)


def check(spec):
    sk = SEQ_KEY
    seq = unreal.load_asset(SEQ_PATH)
    P.chk(sk, "setup", "asset loads as LevelSequence", P.clsname(seq) if seq else None, "LevelSequence")
    if seq is None:
        return
    dr, tr = seq.get_display_rate(), seq.get_tick_resolution()
    P.chk(sk, "setup", "display rate", (dr.numerator, dr.denominator), (30, 1))
    P.chk(sk, "setup", "tick resolution", (tr.numerator, tr.denominator), (24000, 1))
    P.chk(sk, "setup", "playback range s (40 s = 1200 frames at 30 fps)", (seq.get_playback_start_seconds(), round(seq.get_playback_end_seconds(), 3)), (0.0, END_S))
    spawn_ids = {P.guid_str(b.get_id()) for b in seq.get_spawnables()}
    by_name = {}
    for b in seq.get_bindings():
        by_name.setdefault(b.get_name(), []).append(b)
    P.chk(sk, "setup", "binding names (one camera, nothing else: no characters, no lights)", sorted(by_name), ["Cam_MenuDrift"])
    P.chk(sk, "setup", "possessable count (no component bindings)", len(seq.get_possessables()), 0)
    P.chk(sk, "setup", "master tracks: only the camera cut", sorted(P.clsname(t) for t in seq.get_tracks()), ["MovieSceneCameraCutTrack"])
    P.chk(sk, "markers", "no marked frames", len(seq.get_marked_frames_from_sequence(unreal.MovieSceneTimeUnit.DISPLAY_RATE)), 0)
    # camera cut
    cut = P.find_tracks(seq, "MovieSceneCameraCutTrack")
    if cut:
        lib = getattr(unreal, "LBCineAuthoringLibrary", None)
        P.chk(sk, "cut", "bCanBlend (LBCineAuthoringLibrary)", lib.get_camera_cut_track_can_blend(cut[0]) if lib else None, True)
        secs = cut[0].get_sections()
        P.chk(sk, "cut", "one section", len(secs), 1)
        if secs:
            s = secs[0]
            P.chk(sk, "cut", "range (s)", (round(s.get_start_frame_seconds(), 3), round(s.get_end_frame_seconds(), 3)), (0.0, END_S))
            P.chk(sk, "cut", "ease in / out (ticks)", (s.get_ease_in_duration(), s.get_ease_out_duration()), (0, 0))
            tgt = P.guid_str(s.get_camera_binding_id().get_editor_property("guid"))
            P.chk(sk, "cut", "bound to the camera spawnable", tgt, P.guid_str(by_name["Cam_MenuDrift"][0].get_id()) if "Cam_MenuDrift" in by_name else None)
    # the camera
    b = spec["bindings"][0]
    item = b["name"]
    lst = by_name.get(item)
    P.chk(sk, item, "binding exists and is a spawnable", bool(lst) and P.guid_str(lst[0].get_id()) in spawn_ids, True)
    if not lst:
        return
    bd = lst[0]
    P.check_template(sk, item, b, bd)
    tt = P.find_tracks(bd, "MovieScene3DTransformTrack")
    P.chk(sk, item, "transform track count", len(tt), 1)
    flat = {}
    if tt:
        chs = {P.chan_name(c): c for c in tt[0].get_sections()[0].get_all_channels()}
        for k, nm in {"lx": "Location.X", "ly": "Location.Y", "lz": "Location.Z", "rr": "Rotation.X", "rp": "Rotation.Y", "ry": "Rotation.Z"}.items():
            P.cmp_keys(sk, item, "transform %s" % nm, chs[nm], b["xf"][k])
        for nm in ("Scale.X", "Scale.Y", "Scale.Z"):
            P.cmp_keys(sk, item, "transform %s" % nm, chs[nm], [(0.0, 1.0, "L")])
        # seam: the keys at 0 and 40 s are equal, and the tangents at 0, 20 and 40 s are flat
        for nm in ("Location.X", "Rotation.Z"):
            ks = P.read_keys(chs[nm])
            vals = [v for _, v, _ in ks]
            P.chk(sk, item, "%s: first key equals last key (seamless loop)" % nm, abs(vals[0] - vals[-1]), 0.0, 1e-6)
            tangents = []
            for _, _, key in ks:
                tans = {}
                for an in ("get_arrive_tangent", "get_leave_tangent"):
                    fn = getattr(key, an, None)
                    tans[an] = None if fn is None else round(float(fn()), 6)
                tangents.append(tans)
            flat[nm] = tangents
            tv = [t for d in tangents for t in d.values() if t is not None]
            P.chk(sk, item, "%s: arrive and leave tangents of the three keys are readable (6 values)" % nm, len(tv), 6)
            P.chk(sk, item, "%s: all six tangents are flat (max |tangent|)" % nm, max([abs(t) for t in tv] or [1.0]), 0.0, 1e-4)
    # analytic framing (the cached F0 survey; a live trace waits for the editor): every landmark inside the frustum over the first half (the second is the mirror),
    # and the line to the belfry deck and the bell passes over the gate crown (z 800 at X 0) with a margin
    half_h = math.degrees(math.atan(FILMBACK[0] / 2.0 / FOCAL))
    half_v = math.degrees(math.atan(FILMBACK[1] / 2.0 / FOCAL))
    rows = []
    for t in (0.0, 5.0, 10.0, 15.0, 20.0):
        pose = pose_at(t)
        row = {"t": t, "pose": [round(v, 2) for v in pose]}
        for nm, pt in (("gate_top_centre", GATE_TOP_CENTRE), ("gate_top_left", GATE_TOP_LEFT), ("gate_top_right", GATE_TOP_RIGHT),
                       ("tower_deck", TOWER_DECK), ("tower_bell", TOWER_BELL), ("tower_finial", TOWER_FINIAL)):
            az, el, dist = project(pose, pt)
            row[nm] = {"az": round(az, 2), "el": round(el, 2), "dist": round(dist)}
            P.chk(sk, "frame", "%s in frame at t=%.0f s (az %.1f of +-%.1f, el %.1f of +-%.1f)" % (nm, t, az, half_h, el, half_v),
                  abs(az) < half_h - 2.0 and abs(el) < half_v - 1.0, True)
        for nm, pt in (("tower_deck", TOWER_DECK), ("tower_bell", TOWER_BELL)):
            f = (0.0 - pose[0]) / (pt[0] - pose[0])
            z_at_gate = pose[2] + (pt[2] - pose[2]) * f
            row["line_z_at_gate_plane_to_" + nm] = round(z_at_gate, 1)
            P.chk(sk, "frame", "line to %s clears the gate crown (z 800) by >= 40 cm at t=%.0f s" % (nm, t), z_at_gate - 800.0 >= 40.0, True)
        rows.append(row)
    P.results["framing"] = rows
    P.results["tangents"] = flat
    P.results["half_fov"] = {"h": round(half_h, 2), "v": round(half_v, 2)}
    # dependencies: a bare camera spawnable depends on nothing under /Game
    try:
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        deps = ar.get_dependencies(unreal.Name(SEQ_PATH), unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True))
        dl = sorted(str(d) for d in deps if str(d).startswith("/Game"))
        P.results["deps"] = dl
        P.chk(sk, "deps", "no /Game dependencies (nothing under /Game/LastBell/ArtTest/, no Wooden_Lantern, no Mixamo)", dl, [])
    except Exception as exc:  # noqa: BLE001
        P.note("dependencies: %s" % exc)


def do_check():
    spec = cam_spec()
    try:
        check(spec)
    except Exception:  # noqa: BLE001
        P.checks.append({"seq": SEQ_KEY, "item": "exception", "name": "check raised", "ok": False, "got": traceback.format_exc()[-600:], "want": "no exception"})
        unreal.log_error("%s: EXCEPTION %s" % (TAG, traceback.format_exc()))
    bad = [c for c in P.checks if not c["ok"]]
    out = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "total_checks": len(P.checks), "passed": len(P.checks) - len(bad), "failed": len(bad),
           "pose": {"x": [CAM_X0, CAM_X1], "y": CAM_Y, "z": CAM_Z, "yaw": [CAM_YAW0, CAM_YAW1], "pitch": CAM_PITCH, "focal": FOCAL, "aperture": APERTURE, "focus": FOCUS},
           "half_fov_deg": P.results.get("half_fov"), "framing": P.results.get("framing"), "tangents": P.results.get("tangents"), "deps": P.results.get("deps"),
           "notes": P.results["notes"], "failures": bad, "checks": P.checks}
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    log("CHECK done: %d checks, %d failed (%s)" % (len(P.checks), len(bad), OUT_JSON))
    for c in bad[:30]:
        log("  FAIL [%s/%s] %s: got %s want %s" % (c["seq"], c["item"], c["name"], c["got"], c["want"]))


def main():
    if MODE == "build":
        do_build()
        os.makedirs(os.path.dirname(BUILD_RECORD), exist_ok=True)
        with open(BUILD_RECORD, "w", encoding="utf-8") as fh:
            json.dump(P.results, fh, indent=1)
        log("BUILD done: %d calls, %d errors, saved %s" % (P.results["calls"], len(P.results["errors"]), P.results["saved"]))
    elif MODE == "check":
        do_check()
    else:
        unreal.log_error("%s: set P18_MODE=build or P18_MODE=check" % TAG)


try:
    main()
except Exception:  # noqa: BLE001
    unreal.log_error("%s: EXCEPTION %s" % (TAG, traceback.format_exc()))
