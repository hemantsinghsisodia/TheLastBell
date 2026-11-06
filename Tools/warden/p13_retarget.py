"""p13_retarget.py -- P13-4: retarget the Mixamo clips onto the Warden, measure them, build blend spaces, montages, the anim set and the ABPs.

HEADLESS, Unreal editor CLOSED (it writes Content). Run with the real project:

    $env:P13_STEPS = "rigs,rtg,batch,measure"      # any subset, in this order; default = all
    UnrealEditor-Cmd.exe C:\\Hemant\\Prj\\Learning\\TheLastBell\\TheLastBell.uproject -run=pythonscript `
        -script=C:\\Hemant\\Prj\\Learning\\TheLastBell\\Tools\\warden\\p13_retarget.py -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>

The commandlet exits by itself when the script ends (the last line it prints is P13_RETARGET_DONE). It can crash inside python311.dll while
shutting down, AFTER the script has finished and saved; that is harmless (every save is checked before the final line).

Steps (each safe to rerun: what exists and verifies is skipped, what doesn't is rebuilt):
    rigs     IK_LB_YBot, IK_LB_Warden            (Retarget/)
    rtg      RTG_LB_YBot_To_Warden               (Retarget/)
    batch    12 x AN_YBot_<Name> -> AN_Warden_<Name>   (Anims/)
    measure  Docs/ArtTest/warden/p13_clips.json + p13_clips_summary.txt
    blend    BS_Warden_Locomotion, BS_Warden_Stoop
    montage  AM_Warden_Attack, AM_Warden_TurnLeft90, AM_Warden_TurnRight90, AM_Warden_LookAround
    animset  /Game/LastBell/Data/DA_WardenAnimSet
    abp      ABP_Warden, ABP_P13_Spike (created, class defaults set, compiled; no graph)
    verify   read everything back
Never touches SK_Warden, its skeleton or physics asset, AN_Warden_Idle/Walk/DoorwayStoop, BP_Warden or any map.
"""
import json
import math
import os
import traceback

import unreal

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
RET = "/Game/LastBell/Characters/Warden/Retarget"
ANI = "/Game/LastBell/Characters/Warden/Anims"
MESH = "/Game/LastBell/Characters/Warden/Meshes"
WARDEN = "/Game/LastBell/Characters/Warden"
DATA = "/Game/LastBell/Data"
SK_W = MESH + "/SK_Warden"
SKEL_W = MESH + "/SK_Warden_Skeleton"
SK_Y = RET + "/SK_LB_YBot"
OUT_DIR = os.path.join(ROOT, "Docs", "ArtTest", "warden")
OUT_JSON = os.path.join(OUT_DIR, "p13_clips.json")
OUT_TXT = os.path.join(OUT_DIR, "p13_clips_summary.txt")

CLIPS = ["MutantWalking", "ZombieWalk", "MutantRun", "ZombieRunning", "MutantIdle", "CrouchedWalking", "CrouchingIdle",
         "TurnLeft90", "TurnRight90", "ZombieAttack", "MutantSwiping", "LookAround"]
EXISTING_KEEP = ["AN_Warden_Idle", "AN_Warden_Walk", "AN_Warden_DoorwayStoop"]  # never touched

# default picks (task P13-4): the contact sheet (P13-5) may change them
PICK_WALK, PICK_RUN, PICK_ATTACK = "MutantWalking", "MutantRun", "ZombieAttack"
PICK_IDLE, PICK_STOOP_IDLE, PICK_STOOP_WALK = "MutantIdle", "CrouchingIdle", "CrouchedWalking"
WINDUP = 0.6
PATROL_SPEED, CHASE_SPEED, MAX_SPEED = 140.0, 420.0, 450.0
STRETCH_FLAG = 1.02
# Facing fix. Mixamo's Y Bot imports facing +Y (hip line along X); the Warden faces +X (hip line along Y), like AN_Warden_Walk. The retargeter copies
# global-space deltas, so without a fix every stride comes out sideways. Fix: the TARGET retarget pose is yawed POSE_YAW so the Warden "faces +Y" like
# the source, the retarget runs, and every AN_Warden_* then gets a constant ROOT_YAW key on the (otherwise identity) 'root' bone to turn it back to +X.
POSE_YAW = float(os.environ.get("P13_POSE_YAW", "90"))
ROOT_YAW = -POSE_YAW
ROOT_BONE = "root"

AT = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
SRC, TGT = unreal.RetargetSourceOrTarget.SOURCE, unreal.RetargetSourceOrTarget.TARGET


def log(*a):
    print("P13| " + " ".join(str(x) for x in a))


def ap(folder, name):
    return "%s/%s" % (folder, name)


def exists(path):
    return EAL.does_asset_exist(path)


def load(path):
    return unreal.load_asset(path)


def delete(path):
    ok = EAL.delete_asset(path)
    log("  deleted %s -> %s (still exists: %s)" % (path, ok, exists(path)))
    return ok


def save(path):
    ok = EAL.save_asset(path, only_if_is_dirty=False)
    log("  save %s -> %s" % (path, ok))
    if not ok:
        raise RuntimeError("save failed: " + path)
    return ok


def create(name, folder, cls, factory):
    """The asset at folder/name: the existing one if there is one (EditorAssetLibrary.delete_asset leaves it registered in a commandlet, so a
    rebuild reuses and resets it in place), otherwise a new one from the factory."""
    if exists(ap(folder, name)):
        a = load(ap(folder, name))
        if a is None:
            raise RuntimeError("exists but does not load: %s/%s" % (folder, name))
        log("  reusing existing %s/%s for an in-place rebuild" % (folder, name))
        return a
    a = AT.create_asset(name, folder, cls, factory)
    if a is None:
        raise RuntimeError("create_asset returned None: %s/%s" % (folder, name))
    return a


def names(seq_or_list):
    return [str(n) for n in seq_or_list]


def jprops(obj, props):
    return json.loads(unreal.ToolsetLibrary.get_object_properties(obj, props))


def jset(obj, d):
    ok = unreal.ToolsetLibrary.set_object_properties(obj, json.dumps(d))
    if not ok:
        raise RuntimeError("set_object_properties returned False: %s" % json.dumps(d)[:300])
    return ok


def ref(path):
    """JSON object reference for ToolsetLibrary: /Game/X/Name -> {"refPath": "/Game/X/Name.Name"}"""
    return {"refPath": "%s.%s" % (path, path.rsplit("/", 1)[1])}


# ----------------------------------------------------------------------------------------------------------------------
# bone helpers
# ----------------------------------------------------------------------------------------------------------------------
_PATH_CACHE = {}


def bone_path_to_root(seq_path, bone):
    key = (seq_path, bone)
    if key not in _PATH_CACHE:
        _PATH_CACHE[key] = names(unreal.AnimationLibrary.find_bone_path_to_root(load(seq_path), bone))
    return _PATH_CACHE[key]


def chain_bones(ctrl, chain, seq_path):
    """Every bone from the chain's end up to its start (inclusive), via the parent path of an animation on that skeleton."""
    start = str(ctrl.get_retarget_chain_start_bone(chain))
    end = str(ctrl.get_retarget_chain_end_bone(chain))
    out = []
    for b in bone_path_to_root(seq_path, end):  # end ... root
        out.append(b)
        if b.lower() == start.lower():
            return out
    return out + ["<start %s not an ancestor of end %s>" % (start, end)]


# ----------------------------------------------------------------------------------------------------------------------
# step: rigs
# ----------------------------------------------------------------------------------------------------------------------
REQUIRED_CHAINS = ["Spine", "Neck", "Head", "LeftArm", "RightArm", "LeftLeg", "RightLeg"]
RIGS = [
    # name, mesh path, retarget root, an animation on that skeleton (for the parent path), forbid chain/robe bones
    ("IK_LB_YBot", SK_Y, "Hips", RET + "/AN_YBot_MutantIdle", False),
    ("IK_LB_Warden", SK_W, "pelvis", ANI + "/AN_Warden_Idle", True),
]


def rig_problems(name, mesh_path, root, seq_path, forbid):
    """[] when the saved rig is what we want."""
    path = ap(RET, name)
    if not exists(path):
        return ["missing"]
    rig = load(path)
    c = unreal.IKRigController.get_controller(rig)
    probs = []
    m = c.get_skeletal_mesh()
    if m is None or m.get_path_name() != load(mesh_path).get_path_name():
        probs.append("preview mesh is %s" % (m.get_path_name() if m else None))
    if str(c.get_retarget_root()).lower() != root.lower():
        probs.append("retarget root is %s" % c.get_retarget_root())
    chains = [str(ch.get_editor_property("chain_name")) for ch in c.get_retarget_chains()]
    for r in REQUIRED_CHAINS:
        if r not in chains:
            probs.append("chain %s missing" % r)
    if forbid:
        for ch in chains:
            for b in chain_bones(c, ch, seq_path):
                if b.startswith("chain_") or b.startswith("robe_") or b.startswith("<"):
                    probs.append("chain %s contains %s" % (ch, b))
    return probs


def build_rig(name, mesh_path, root, seq_path, forbid):
    path = ap(RET, name)
    probs = rig_problems(name, mesh_path, root, seq_path, forbid)
    if not probs:
        log("skip %s: exists and verifies" % name)
        return
    if exists(path):
        log("rebuild %s in place: %s" % (name, probs))
    rig = create(name, RET, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    c = unreal.IKRigController.get_controller(rig)
    log("  set_skeletal_mesh(%s) -> %s" % (mesh_path, c.set_skeletal_mesh(load(mesh_path))))
    log("  apply_auto_generated_retarget_definition -> %s" % c.apply_auto_generated_retarget_definition())
    if str(c.get_retarget_root()).lower() != root.lower():
        log("  retarget root was %s, set_retarget_root(%s) -> %s" % (c.get_retarget_root(), root, c.set_retarget_root(root)))
    save(path)
    probs = rig_problems(name, mesh_path, root, seq_path, forbid)
    if probs:
        raise RuntimeError("%s still has problems after the build: %s" % (name, probs))


def report_rig(name, seq_path):
    rig = load(ap(RET, name))
    c = unreal.IKRigController.get_controller(rig)
    log("RIG %s: mesh=%s retarget_root=%s solvers=%d" % (name, c.get_skeletal_mesh().get_name(), c.get_retarget_root(), c.get_num_solvers()))
    for ch in c.get_retarget_chains():
        cn = str(ch.get_editor_property("chain_name"))
        bs = chain_bones(c, cn, seq_path)
        log("   chain %-14s %s -> %s  goal=%s  bones(end..start)=%s" % (cn, c.get_retarget_chain_start_bone(cn), c.get_retarget_chain_end_bone(cn),
                                                                    ch.get_editor_property("ik_goal_name"), bs))


def step_rigs():
    for r in RIGS:
        build_rig(*r)
    for name, mesh, root, seq, forbid in RIGS:
        report_rig(name, seq)
    # the plan's hard rule: no chain_* / robe_* bone in any Warden chain (rig_problems checks it and raised if not)
    log("rule check: no Warden chain contains a chain_* or robe_* bone -> OK (verified by rig_problems)")


# ----------------------------------------------------------------------------------------------------------------------
# step: rtg
# ----------------------------------------------------------------------------------------------------------------------
RTG = "RTG_LB_YBot_To_Warden"


def rtg_report():
    rtg = load(ap(RET, RTG))
    c = unreal.IKRetargeterController.get_controller(rtg)
    src, tgt = c.get_ik_rig(SRC), c.get_ik_rig(TGT)
    log("RTG %s: source rig=%s target rig=%s ops=%d" % (RTG, src.get_name() if src else None, tgt.get_name() if tgt else None, c.get_num_retarget_ops()))
    for i in range(c.get_num_retarget_ops()):
        log("   op[%d] %s enabled=%s" % (i, c.get_op_name(i), c.get_retarget_op_enabled(i)))
    log("   target pelvis retarget-pose rotation offset: %s (yaw %.2f)" % (c.get_rotation_offset_for_retarget_pose_bone("pelvis", TGT), quat_yaw_deg(c.get_rotation_offset_for_retarget_pose_bone("pelvis", TGT))))
    tc = unreal.IKRigController.get_controller(tgt)
    mapping = []
    for ch in tc.get_retarget_chains():
        cn = str(ch.get_editor_property("chain_name"))
        mapping.append((cn, str(c.get_source_chain(cn))))
    log("   chain mapping (target <- source): " + ", ".join("%s<-%s" % m for m in mapping))
    unmapped = [t for t, s in mapping if s in ("None", "")]
    log("   unmapped target chains: %s" % unmapped)
    try:
        pose = c.get_current_retarget_pose(TGT)
        log("   current target retarget pose: %s" % c.get_current_retarget_pose_name(TGT))
        txt = pose.export_text()
        log("   target pose export_text (%d chars): %s" % (len(txt), txt[:900]))
    except Exception as e:  # noqa: BLE001
        log("   retarget pose read failed: %r" % (e,))
    return mapping, unmapped


def op_index(c, name):
    for i in range(c.get_num_retarget_ops()):
        if str(c.get_op_name(i)) == name:
            return i
    return -1


def quat_yaw_deg(q):
    return float(q.rotator().yaw)


def rtg_ok():
    if not exists(ap(RET, RTG)):
        return False
    c = unreal.IKRetargeterController.get_controller(load(ap(RET, RTG)))
    src, tgt = c.get_ik_rig(SRC), c.get_ik_rig(TGT)
    if not src or not tgt or src.get_name() != "IK_LB_YBot" or tgt.get_name() != "IK_LB_Warden":
        return False
    for r in REQUIRED_CHAINS:
        if str(c.get_source_chain(r)) in ("None", ""):
            return False
    i = op_index(c, "Root Motion")
    if i < 0 or c.get_retarget_op_enabled(i):
        return False  # the Root Motion op copies Hips onto 'root'; the clips are in place, so it stays off
    if abs(quat_yaw_deg(c.get_rotation_offset_for_retarget_pose_bone("pelvis", TGT)) - POSE_YAW) > 10.0:
        return False
    return c.get_num_retarget_ops() > 0


def step_rtg():
    path = ap(RET, RTG)
    if rtg_ok():
        log("skip %s: exists and verifies" % RTG)
    else:
        rtg = create(RTG, RET, unreal.IKRetargeter, unreal.IKRetargetFactory())
        c = unreal.IKRetargeterController.get_controller(rtg)
        c.remove_all_ops()
        for who in (SRC, TGT):
            c.reset_retarget_pose(c.get_current_retarget_pose_name(who), [], who)
        ik_y, ik_w = load(ap(RET, "IK_LB_YBot")), load(ap(RET, "IK_LB_Warden"))
        c.set_ik_rig(SRC, ik_y)
        c.set_ik_rig(TGT, ik_w)
        c.set_preview_mesh(SRC, load(SK_Y))
        c.set_preview_mesh(TGT, load(SK_W))
        c.add_default_ops()
        c.assign_ik_rig_to_all_ops(TGT, ik_w)
        c.auto_map_chains(unreal.AutoMapChainType.EXACT, True)
        # Root Motion op off (see ROOT_BONE note); facing fix: yaw the target pelvis in the retarget pose BEFORE the auto-align
        i = op_index(c, "Root Motion")
        if i >= 0:
            log("  Root Motion op index %d: set_retarget_op_enabled(False) -> %s" % (i, c.set_retarget_op_enabled(i, False)))
        # the auto-align also sets the pelvis offset (it overwrites a yaw set before it), so: align first, then yaw the pelvis on top of that offset
        c.auto_align_all_bones(TGT, unreal.RetargetAutoAlignMethod.CHAIN_TO_CHAIN)
        e = c.get_rotation_offset_for_retarget_pose_bone("pelvis", TGT)
        comp = unreal.MathLibrary.compose_rotators(e.rotator(), unreal.Rotator(roll=0.0, pitch=0.0, yaw=POSE_YAW))
        log("  pelvis offset after auto-align %s ; composed with yaw %.1f -> %s" % (e.rotator(), POSE_YAW, comp))
        c.set_rotation_offset_for_retarget_pose_bone("pelvis", comp.quaternion(), TGT)
        save(path)
        if not rtg_ok():
            rtg_report()
            raise RuntimeError("retargeter does not verify after the build")
    rtg_report()


# ----------------------------------------------------------------------------------------------------------------------
# step: batch
# ----------------------------------------------------------------------------------------------------------------------
def seq_stats(path):
    s = load(path)
    return {"length": float(s.get_play_length()), "frames": int(unreal.AnimationLibrary.get_num_frames(s)),
            "skeleton": s.get_skeleton().get_path_name()}


def batch_ok(n):
    src, dst = ap(RET, "AN_YBot_" + n), ap(ANI, "AN_Warden_" + n)
    if not exists(dst):
        return False
    a, b = seq_stats(src), seq_stats(dst)
    if not (b["skeleton"].endswith("SK_Warden_Skeleton.SK_Warden_Skeleton") and abs(a["length"] - b["length"]) < 0.01 and a["frames"] == b["frames"]):
        return False
    s = load(dst)
    for fi in (0, b["frames"] // 2, b["frames"]):
        t = unreal.AnimationLibrary.get_bone_pose_for_frame(s, ROOT_BONE, fi, False)
        yaw = float(t.rotation.rotator().yaw)
        if abs(((yaw - ROOT_YAW + 180.0) % 360.0) - 180.0) > 0.5 or abs(t.translation.x) + abs(t.translation.y) + abs(t.translation.z) > 0.01:
            return False
    return True


def fix_root(path, nframes):
    """Constant yaw key ROOT_YAW on the 'root' bone (identity before: the Root Motion op is off). Refuses to touch a root track that is not identity."""
    s = load(path)
    for fi in range(nframes + 1):
        t = unreal.AnimationLibrary.get_bone_pose_for_frame(s, ROOT_BONE, fi, False)
        r = t.rotation
        if abs(t.translation.x) + abs(t.translation.y) + abs(t.translation.z) > 0.01 or abs(r.x) + abs(r.y) + abs(r.z) > 0.001:
            raise RuntimeError("%s: root track is not identity at frame %d (%s, %s); not overwriting" % (path, fi, t.translation, r.rotator()))
    q = unreal.Rotator(roll=0.0, pitch=0.0, yaw=ROOT_YAW).quaternion()
    n = nframes + 1
    ok = s.controller.set_bone_track_keys(ROOT_BONE, [unreal.Vector(0, 0, 0)] * n, [q] * n, [unreal.Vector(1, 1, 1)] * n)
    log("  %s: root yaw %.1f key x%d -> %s" % (path.rsplit("/", 1)[1], ROOT_YAW, n, ok))
    if not ok:
        raise RuntimeError("set_bone_track_keys failed on " + path)


def step_batch():
    todo = []
    for n in CLIPS:
        if batch_ok(n):
            log("skip AN_Warden_%s: exists and verifies" % n)
        else:
            if exists(ap(ANI, "AN_Warden_" + n)):
                log("rebuild AN_Warden_%s (overwrite)" % n)
            todo.append(n)
    if todo:
        inp = unreal.IKRetargetBatchOperationInputs()
        inp.set_editor_property("assets_to_retarget", [EAL.find_asset_data(ap(RET, "AN_YBot_" + n)) for n in todo])
        inp.set_editor_property("source_mesh", load(SK_Y))
        inp.set_editor_property("target_mesh", load(SK_W))
        inp.set_editor_property("ik_retarget_asset", load(ap(RET, RTG)))
        inp.set_editor_property("search", "AN_YBot_")
        inp.set_editor_property("replace", "AN_Warden_")
        inp.set_editor_property("target_path", ANI)
        inp.set_editor_property("use_source_path", False)
        inp.set_editor_property("include_referenced_assets", False)
        inp.set_editor_property("overwrite_existing_files", True)
        res = unreal.IKRetargetBatchOperation.run_batch_retarget(inp)
        log("run_batch_retarget returned %d assets: %s" % (len(res), [str(r.asset_name) for r in res]))
        for n in todo:
            p = ap(ANI, "AN_Warden_" + n)
            if not exists(p):
                raise RuntimeError("batch did not create " + p)
            fix_root(p, seq_stats(p)["frames"])
            save(p)
    bad = []
    for n in CLIPS:
        p = ap(ANI, "AN_Warden_" + n)
        st = seq_stats(p)
        ok = batch_ok(n)
        log("  AN_Warden_%-16s skeleton=%s length=%.4f s frames=%d root_motion=%s %s" % (
            n, st["skeleton"].rsplit(".", 1)[1], st["length"], st["frames"], unreal.AnimationLibrary.is_root_motion_enabled(load(p)), "" if ok else "<-- MISMATCH"))
        if not ok:
            bad.append(n)
    for k in EXISTING_KEEP:
        log("  untouched: %s exists=%s" % (k, exists(ap(ANI, k))))
    if bad:
        raise RuntimeError("batch verify failed for %s" % bad)


# ----------------------------------------------------------------------------------------------------------------------
# step: measure
# ----------------------------------------------------------------------------------------------------------------------
MB = ["pelvis", "head", "thigh_l", "thigh_r", "calf_l", "calf_r", "foot_l", "foot_r", "upperarm_l", "upperarm_r",
      "lowerarm_l", "lowerarm_r", "hand_l", "hand_r"]
LIMBS = {"arm_l": ("upperarm_l", "lowerarm_l", "hand_l"), "arm_r": ("upperarm_r", "lowerarm_r", "hand_r"),
         "leg_l": ("thigh_l", "calf_l", "foot_l"), "leg_r": ("thigh_r", "calf_r", "foot_r")}


def _opts():
    o = unreal.AnimPoseEvaluationOptions()
    o.set_editor_property("evaluation_type", unreal.AnimDataEvalType.RAW)
    o.set_editor_property("should_retarget", False)
    o.set_editor_property("extract_root_motion", False)
    o.set_editor_property("incorporate_root_motion_into_pose", False)
    return o


def _v(t):
    return (float(t.translation.x), float(t.translation.y), float(t.translation.z))


def _d(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def ref_positions():
    pose = unreal.AnimPoseExtensions.get_reference_pose(load(SKEL_W))
    return {b: _v(unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD)) for b in MB}


def eval_frames(seq):
    n = int(unreal.AnimationLibrary.get_num_frames(seq))
    o = _opts()
    out = []
    for i in range(n + 1):
        pose = unreal.AnimPoseExtensions.get_anim_pose_at_frame(seq, i, o)
        out.append({b: _v(unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD)) for b in MB})
    return n, out


def facing(fr):
    """Unit forward vector in XY from the hip line (right = thigh_r - thigh_l; UE: forward X, right Y)."""
    r = (fr["thigh_r"][0] - fr["thigh_l"][0], fr["thigh_r"][1] - fr["thigh_l"][1])
    m = math.hypot(*r) or 1.0
    return (r[1] / m, -r[0] / m)


def measure_clip(n, ref):
    path = ap(ANI, "AN_Warden_" + n)
    seq = load(path)
    length = float(seq.get_play_length())
    nf, fr = eval_frames(seq)
    dt = length / nf
    fw = [facing(f) for f in fr]
    yaw = []
    prev = None
    for f in fw:
        a = math.degrees(math.atan2(f[1], f[0]))
        if prev is not None:
            while a - prev > 180:
                a -= 360
            while a - prev < -180:
                a += 360
        yaw.append(a)
        prev = a
    # natural speed: planted (= lower of the two) foot's average backward speed along the facing, component space
    sp = {"l": [], "r": []}
    for i in range(nf):
        for s, o in (("l", "r"), ("r", "l")):
            lo_i = fr[i]["foot_" + s][2] < fr[i]["foot_" + o][2]
            lo_j = fr[i + 1]["foot_" + s][2] < fr[i + 1]["foot_" + o][2]
            if lo_i and lo_j:
                dx = fr[i + 1]["foot_" + s][0] - fr[i]["foot_" + s][0]
                dy = fr[i + 1]["foot_" + s][1] - fr[i]["foot_" + s][1]
                sp[s].append(-(dx * fw[i][0] + dy * fw[i][1]) / dt)
    mean = lambda xs: (sum(xs) / len(xs)) if xs else None  # noqa: E731
    sl, sr = mean(sp["l"]), mean(sp["r"])
    both = [v for v in (sl, sr) if v is not None]
    nat = (sum(both) / len(both)) if both else None
    # axis along which the feet travel (principal axis of both feet's XY motion about their own means), degrees from +X, -90..90
    sxx = sxy = syy = 0.0
    for foot in ("foot_l", "foot_r"):
        mx = sum(f[foot][0] for f in fr) / len(fr)
        my = sum(f[foot][1] for f in fr) / len(fr)
        for f in fr:
            dx, dy = f[foot][0] - mx, f[foot][1] - my
            sxx, sxy, syy = sxx + dx * dx, sxy + dx * dy, syy + dy * dy
    stride_axis = math.degrees(0.5 * math.atan2(2 * sxy, sxx - syy))
    # extents
    head_top = max(f["head"][2] for f in fr)
    foot_low = min(min(f["foot_l"][2], f["foot_r"][2]) for f in fr)
    p0, p1 = fr[0]["pelvis"], fr[-1]["pelvis"]
    drift_end = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    drift_max = max(math.hypot(f["pelvis"][0] - p0[0], f["pelvis"][1] - p0[1]) for f in fr)
    # hit time: hand_l / hand_r furthest forward of the pelvis along the per-frame facing
    reach = []
    reach_origin = []
    for i, f in enumerate(fr):
        best, best_o = -1e9, -1e9
        for h in ("hand_l", "hand_r"):
            best = max(best, (f[h][0] - f["pelvis"][0]) * fw[i][0] + (f[h][1] - f["pelvis"][1]) * fw[i][1])
            best_o = max(best_o, f[h][0] * fw[0][0] + f[h][1] * fw[0][1])
        reach.append(best)
        reach_origin.append(best_o)
    sh_yaw = []
    prev = None
    for f in fr:
        rx, ry = f["upperarm_r"][0] - f["upperarm_l"][0], f["upperarm_r"][1] - f["upperarm_l"][1]
        a = math.degrees(math.atan2(-rx, ry))  # facing (ry, -rx) as in facing()
        if prev is not None:
            while a - prev > 180:
                a -= 360
            while a - prev < -180:
                a += 360
        sh_yaw.append(a)
        prev = a
    ih = max(range(len(reach)), key=lambda i: reach[i])
    io = max(range(len(reach_origin)), key=lambda i: reach_origin[i])
    # stretch
    stretch = {}
    flagged = []
    for limb, (a, b, c) in LIMBS.items():
        rab, rbc = _d(ref[a], ref[b]), _d(ref[b], ref[c])
        ref_len = rab + rbc
        reach_ratio = max(_d(f[a], f[c]) for f in fr) / ref_len
        seg_ratio = max(max(_d(f[a], f[b]) / rab, _d(f[b], f[c]) / rbc) for f in fr)
        stretch[limb] = {"max_reach_over_ref_length": round(reach_ratio, 4), "max_segment_over_ref": round(seg_ratio, 4), "ref_length_cm": round(ref_len, 2)}
        if reach_ratio > STRETCH_FLAG or seg_ratio > STRETCH_FLAG:
            flagged.append(limb)
    return {
        "asset": path, "length_s": round(length, 4), "frames": nf, "fps": round(nf / length, 3),
        "natural_speed_cm_s": None if nat is None else round(nat, 2),
        "natural_speed_left_cm_s": None if sl is None else round(sl, 2), "natural_speed_right_cm_s": None if sr is None else round(sr, 2),
        "planted_samples_left": len(sp["l"]), "planted_samples_right": len(sp["r"]),
        "head_top_z_cm": round(head_top, 2), "head_top_plus_50_cm": round(head_top + 50.0, 2),
        "lowest_foot_z_cm": round(foot_low, 2),
        "pelvis_z_min_max_cm": [round(min(f["pelvis"][2] for f in fr), 2), round(max(f["pelvis"][2] for f in fr), 2)],
        "pelvis_drift_end_cm": round(drift_end, 2), "pelvis_drift_max_cm": round(drift_max, 2),
        "foot_travel_axis_deg_from_plus_x": round(stride_axis, 1),
        "facing_yaw_f0_deg": round(yaw[0], 2), "facing_yaw_last_deg": round(yaw[-1], 2),
        "total_yaw_deg": round(yaw[-1] - yaw[0], 2), "max_abs_yaw_from_f0_deg": round(max(abs(y - yaw[0]) for y in yaw), 2),
        "hit_time_s": round(ih * dt, 4), "hit_frame": ih, "hit_forward_of_pelvis_cm": round(reach[ih], 2),
        "hit_time_from_origin_s": round(io * dt, 4), "hit_frame_from_origin": io,
        "stretch": stretch, "stretch_flagged": flagged,
        "forward_reach_per_frame_cm": [round(x, 1) for x in reach],
        "shoulder_yaw_per_frame_deg": [round(x, 1) for x in sh_yaw],
    }


def step_measure():
    ref = ref_positions()
    res = {}
    for n in CLIPS:
        r = measure_clip(n, ref)
        res[n] = r
        log("measured %s: len %.3f s nat %s head+50 %.1f foot_low %.1f drift %.1f yaw %.1f hit %.3f s stretch flags %s" % (
            n, r["length_s"], r["natural_speed_cm_s"], r["head_top_plus_50_cm"], r["lowest_foot_z_cm"], r["pelvis_drift_end_cm"], r["total_yaw_deg"], r["hit_time_s"], r["stretch_flagged"]))
    # existing clips for comparison (read only)
    cmp_ = {}
    for k in ("AN_Warden_Idle", "AN_Warden_Walk", "AN_Warden_DoorwayStoop"):
        try:
            seq = load(ap(ANI, k))
            nf, fr = eval_frames(seq)
            cmp_[k] = {"length_s": round(float(seq.get_play_length()), 3), "head_top_z_cm": round(max(f["head"][2] for f in fr), 2),
                       "lowest_foot_z_cm": round(min(min(f["foot_l"][2], f["foot_r"][2]) for f in fr), 2)}
        except Exception as e:  # noqa: BLE001
            cmp_[k] = {"error": repr(e)}
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump({"note": "P13-4 measurements, component space (cm), headless; see Tools/warden/p13_retarget.py", "clips": res, "existing_clips_for_comparison": cmp_}, fh, indent=2)
    lines = ["P13-4 clip measurements (cm, seconds, degrees). natural = planted foot backward speed along the hip-line facing.", ""]
    hdr = "%-17s %6s %5s %8s %8s %9s %8s %8s %8s %8s %7s %5s  %s" % ("clip", "len_s", "fr", "natural", "head+50", "foot_low", "drift_e", "drift_mx", "yaw_tot", "hit_s", "yaw_f0", "axis", "stretch (max reach/ref | max seg/ref)")
    lines.append(hdr)
    for n in CLIPS:
        r = res[n]
        st = " ".join("%s %.3f|%.3f" % (k, v["max_reach_over_ref_length"], v["max_segment_over_ref"]) for k, v in r["stretch"].items())
        lines.append("%-17s %6.3f %5d %8s %8.1f %9.1f %8.1f %8.1f %8.1f %8.3f %7.1f %5.0f  %s%s" % (
            n, r["length_s"], r["frames"], "-" if r["natural_speed_cm_s"] is None else "%.1f" % r["natural_speed_cm_s"], r["head_top_plus_50_cm"],
            r["lowest_foot_z_cm"], r["pelvis_drift_end_cm"], r["pelvis_drift_max_cm"], r["total_yaw_deg"], r["hit_time_s"], r["facing_yaw_f0_deg"], r["foot_travel_axis_deg_from_plus_x"], st,
            ("   STRETCH: " + ",".join(r["stretch_flagged"])) if r["stretch_flagged"] else ""))
    lines.append("")
    lines.append("existing clips (comparison): " + json.dumps(cmp_))
    with open(OUT_TXT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    for l in lines:
        log(l)
    log("wrote %s and %s" % (OUT_JSON, OUT_TXT))


# ----------------------------------------------------------------------------------------------------------------------
# steps: blend, montage, animset, abp, verify
# ----------------------------------------------------------------------------------------------------------------------
BS_LOCO, BS_STOOP = "BS_Warden_Locomotion", "BS_Warden_Stoop"
AM_ATTACK, AM_TL, AM_TR, AM_LOOK = "AM_Warden_Attack", "AM_Warden_TurnLeft90", "AM_Warden_TurnRight90", "AM_Warden_LookAround"
DA_NAME = "DA_WardenAnimSet"
ABP_NAME, ABP_SPIKE = "ABP_Warden", "ABP_P13_Spike"
SLOT = "DefaultSlot"
SMOOTH_S = 0.3
STOOP_RUN_RATE_CAP = 2.0
LOOK_TRIM_S = 2.0
# (montage, source clip pick, blend in, blend out, trim)
MONTAGES = [
    (AM_ATTACK, PICK_ATTACK, 0.15, 0.25, None),
    (AM_TL, "TurnLeft90", 0.2, 0.2, None),
    (AM_TR, "TurnRight90", 0.2, 0.2, None),
    (AM_LOOK, "LookAround", 0.3, 0.3, LOOK_TRIM_S),
]


def load_meas():
    with open(OUT_JSON, "r", encoding="utf-8") as fh:
        return json.load(fh)["clips"]


def clip_ref(n):
    return ref(ap(ANI, "AN_Warden_" + n))


def rate_scale(speed, nat, cap=None):
    r = speed / nat
    return round(min(r, cap) if cap else r, 4)


def blend_plan(meas):
    """(blend space name, [(clip, speed, rate scale)]) from the measured natural speeds (plan section 6)."""
    wn, rn, sn = meas[PICK_WALK]["natural_speed_cm_s"], meas[PICK_RUN]["natural_speed_cm_s"], meas[PICK_STOOP_WALK]["natural_speed_cm_s"]
    for who, v in ((PICK_WALK, wn), (PICK_RUN, rn), (PICK_STOOP_WALK, sn)):
        if not v or v < 20:
            raise RuntimeError("natural speed of %s is %s: not usable" % (who, v))
    return [
        (BS_LOCO, [(PICK_IDLE, 0.0, 1.0), (PICK_WALK, PATROL_SPEED, rate_scale(PATROL_SPEED, wn)), (PICK_RUN, CHASE_SPEED, rate_scale(CHASE_SPEED, rn))]),
        (BS_STOOP, [(PICK_STOOP_IDLE, 0.0, 1.0), (PICK_STOOP_WALK, PATROL_SPEED, rate_scale(PATROL_SPEED, sn)),
                    (PICK_STOOP_WALK, CHASE_SPEED, rate_scale(CHASE_SPEED, sn, STOOP_RUN_RATE_CAP))]),
    ]


def lower_keys(d):
    return {k.lower(): v for k, v in d.items()}


def read_blend(path):
    bs = load(path)
    return bs, lower_keys(jprops(bs, ["blendParameters", "interpolationParam", "sampleData", "bLoop", "axisToScaleAnimation"]))


def blend_problems(name, samples):
    path = ap(ANI, name)
    if not exists(path):
        return ["missing"]
    bs, d = read_blend(path)
    probs = []
    if not bs.get_skeleton().get_path_name().endswith("SK_Warden_Skeleton.SK_Warden_Skeleton"):
        probs.append("skeleton %s" % bs.get_skeleton().get_name())
    p0 = d["blendparameters"][0]
    if p0["displayName"] != "Speed" or abs(p0["min"]) > 1e-6 or abs(p0["max"] - MAX_SPEED) > 1e-6:
        probs.append("axis %s" % p0)
    ip = d["interpolationparam"][0]
    if abs(ip["interpolationTime"] - SMOOTH_S) > 1e-6:
        probs.append("smoothing %s" % ip)
    if not d["bloop"]:
        probs.append("bLoop false")
    sd = d["sampledata"]
    if len(sd) != len(samples):
        probs.append("%d samples, expected %d" % (len(sd), len(samples)))
    else:
        for got, (clip, spd, rs) in zip(sd, samples):
            if not got["animation"]["refPath"].endswith("AN_Warden_%s.AN_Warden_%s" % (clip, clip)) or abs(got["sampleValue"]["x"] - spd) > 1e-3 \
                    or abs(got["rateScale"] - rs) > 1e-3:
                probs.append("sample %s != %s" % (got, (clip, spd, rs)))
    return probs


def build_blend(name, samples):
    path = ap(ANI, name)
    probs = blend_problems(name, samples)
    if not probs:
        log("skip %s: exists and verifies" % name)
        return
    if exists(path):
        log("rebuild %s in place: %s" % (name, probs))
    f = unreal.BlendSpaceFactory1D()
    f.set_editor_property("target_skeleton", load(SKEL_W))
    bs = create(name, ANI, unreal.BlendSpace1D, f)
    jset(bs, {
        "blendParameters": [
            {"displayName": "Speed", "min": 0.0, "max": MAX_SPEED, "gridNum": 9, "bSnapToGrid": False, "bWrapInput": False},
            {"displayName": "None", "min": 0.0, "max": 100.0, "gridNum": 4, "bSnapToGrid": False, "bWrapInput": False},
            {"displayName": "None", "min": 0.0, "max": 100.0, "gridNum": 4, "bSnapToGrid": False, "bWrapInput": False}],
        "interpolationParam": [
            {"interpolationTime": SMOOTH_S, "dampingRatio": 1.0, "maxSpeed": 0.0, "interpolationType": "BSIT_SpringDamper"},
            {"interpolationTime": 0.0, "dampingRatio": 1.0, "maxSpeed": 0.0, "interpolationType": "BSIT_SpringDamper"},
            {"interpolationTime": 0.0, "dampingRatio": 1.0, "maxSpeed": 0.0, "interpolationType": "BSIT_SpringDamper"}],
        "bLoop": True,
    })
    jset(bs, {"sampleData": [{"animation": clip_ref(c), "sampleValue": {"x": spd, "y": 0.0, "z": 0.0}, "rateScale": rs} for c, spd, rs in samples]})
    bs.set_preview_skeletal_mesh(load(SK_W))
    save(path)
    probs = blend_problems(name, samples)
    if probs:
        raise RuntimeError("%s does not verify after the build: %s" % (name, probs))


def step_blend():
    meas = load_meas()
    for name, samples in blend_plan(meas):
        build_blend(name, samples)
        _, d = read_blend(ap(ANI, name))
        log("BLENDSPACE %s: axis %s, smoothing %s, loop %s" % (name, d["blendparameters"][0], d["interpolationparam"][0], d["bloop"]))
        for got in d["sampledata"]:
            log("   sample %-28s at %6.1f  rate scale %.4f" % (got["animation"]["refPath"].rsplit("/", 1)[1].split(".")[0], got["sampleValue"]["x"], got["rateScale"]))


def montage_expect(clip, trim):
    length = float(load(ap(ANI, "AN_Warden_" + clip)).get_play_length())
    return min(length, trim) if trim else length


def read_montage(path):
    am = load(path)
    return am, lower_keys(jprops(am, ["blendIn", "blendOut", "slotAnimTracks"]))


def montage_problems(name, clip, bi, bo, trim):
    path = ap(ANI, name)
    if not exists(path):
        return ["missing"]
    am, d = read_montage(path)
    probs = []
    if not am.get_skeleton().get_path_name().endswith("SK_Warden_Skeleton.SK_Warden_Skeleton"):
        probs.append("skeleton %s" % am.get_skeleton().get_name())
    if abs(d["blendin"]["blendTime"] - bi) > 1e-4 or abs(d["blendout"]["blendTime"] - bo) > 1e-4:
        probs.append("blend %s / %s" % (d["blendin"], d["blendout"]))
    tr = d["slotanimtracks"]
    if len(tr) != 1 or tr[0]["slotName"] != SLOT:
        probs.append("slots %s" % [t["slotName"] for t in tr])
    else:
        segs = tr[0]["animTrack"]["animSegments"]
        if len(segs) != 1 or not segs[0]["animReference"]["refPath"].endswith("AN_Warden_%s.AN_Warden_%s" % (clip, clip)):
            probs.append("segments %s" % segs)
        elif abs(segs[0]["cachedPlayLength"] - float(load(ap(ANI, "AN_Warden_" + clip)).get_play_length())) > 1e-3:
            # CachedPlayLength is the length of the referenced clip, not of the trimmed segment (else: "out-of-sync" warning on load)
            probs.append("cachedPlayLength %.4f != clip length" % segs[0]["cachedPlayLength"])
    exp = montage_expect(clip, trim)
    if abs(float(am.get_play_length()) - exp) > 0.02:
        probs.append("length %.4f, expected %.4f" % (am.get_play_length(), exp))
    return probs


def build_montage(name, clip, bi, bo, trim):
    path = ap(ANI, name)
    probs = montage_problems(name, clip, bi, bo, trim)
    if not probs:
        log("skip %s: exists and verifies" % name)
        return
    if exists(path):
        log("rebuild %s in place: %s" % (name, probs))
    src = load(ap(ANI, "AN_Warden_" + clip))
    f = unreal.AnimMontageFactory()
    f.set_editor_property("target_skeleton", load(SKEL_W))
    f.set_editor_property("source_animation", src)
    am = create(name, ANI, unreal.AnimMontage, f)
    end = montage_expect(clip, trim)
    jset(am, {"slotAnimTracks": [{"slotName": SLOT, "animTrack": {"animSegments": [{
        "cachedPlayLength": float(src.get_play_length()), "animReference": clip_ref(clip), "startPos": 0.0, "animStartTime": 0.0, "animEndTime": end,
        "animPlayRate": 1.0, "loopingCount": 1}]}}]})
    jset(am, {"blendIn": {"blendTime": bi}, "blendOut": {"blendTime": bo}})
    # the montage's cached SequenceLength is only recomputed when the package is saved (a trimmed segment still reads the old length before that)
    log("  %s play length before the save: %.4f s (expected %.4f)" % (name, am.get_play_length(), end))
    am.set_preview_skeletal_mesh(load(SK_W))
    save(path)
    log("  %s play length after the save: %.4f s" % (name, am.get_play_length()))
    probs = montage_problems(name, clip, bi, bo, trim)
    if probs:
        raise RuntimeError("%s does not verify after the build: %s" % (name, probs))


def step_montage():
    for name, clip, bi, bo, trim in MONTAGES:
        build_montage(name, clip, bi, bo, trim)
        am, d = read_montage(ap(ANI, name))
        seg = d["slotanimtracks"][0]["animTrack"]["animSegments"][0]
        log("MONTAGE %s: clip AN_Warden_%s, slot %s, length %.4f s (source %.4f), blend in %.2f out %.2f, segment %.3f..%.3f" % (
            name, clip, d["slotanimtracks"][0]["slotName"], am.get_play_length(), load(ap(ANI, "AN_Warden_" + clip)).get_play_length(),
            d["blendin"]["blendTime"], d["blendout"]["blendTime"], seg["animStartTime"], seg["animEndTime"]))


def attack_numbers(meas):
    hit = float(meas[PICK_ATTACK]["hit_time_s"])
    rate = min(max(hit / WINDUP, 0.8), 2.5) if hit > 0 and WINDUP > 0 else 1.0  # LBWardenAnim::AttackPlayRate
    return hit, round(rate, 4)


def anim_set_class():
    return getattr(unreal, "LBWardenAnimSet", None) or unreal.load_class(None, "/Script/LastBell.LBWardenAnimSet")


def da_problems(meas):
    path = ap(DATA, DA_NAME)
    if not exists(path):
        return ["missing"]
    da = load(path)
    d = lower_keys(jprops(da, ["attack", "turnLeft90", "turnRight90", "lookAround", "attackPlayRate", "attackHitTime"]))
    hit, rate = attack_numbers(meas)
    probs = []
    for key, mont in (("attack", AM_ATTACK), ("turnleft90", AM_TL), ("turnright90", AM_TR), ("lookaround", AM_LOOK)):
        got = d[key]["refPath"] if isinstance(d[key], dict) else d[key]
        if not str(got).endswith("%s.%s" % (mont, mont)):
            probs.append("%s = %s" % (key, got))
    if abs(d["attackplayrate"] - rate) > 1e-3 or abs(d["attackhittime"] - hit) > 1e-3:
        probs.append("rate/hit %s/%s, expected %s/%s" % (d["attackplayrate"], d["attackhittime"], rate, hit))
    return probs


def step_animset():
    meas = load_meas()
    probs = da_problems(meas)
    path = ap(DATA, DA_NAME)
    if not probs:
        log("skip %s: exists and verifies" % DA_NAME)
    else:
        if exists(path):
            log("rebuild %s in place: %s" % (DA_NAME, probs))
        cls = anim_set_class()
        f = unreal.DataAssetFactory()
        f.set_editor_property("data_asset_class", cls)
        da = create(DA_NAME, DATA, cls, f)
        hit, rate = attack_numbers(meas)
        jset(da, {"attack": ref(ap(ANI, AM_ATTACK)), "turnLeft90": ref(ap(ANI, AM_TL)), "turnRight90": ref(ap(ANI, AM_TR)),
                  "lookAround": ref(ap(ANI, AM_LOOK)), "attackPlayRate": rate, "attackHitTime": hit})
        save(path)
        probs = da_problems(meas)
        if probs:
            raise RuntimeError("%s does not verify after the build: %s" % (DA_NAME, probs))
    hit, rate = attack_numbers(meas)
    log("ANIMSET %s: attack hit time %.4f s (clip %s), AttackPlayRate = clamp(%.4f / %.1f, 0.8, 2.5) = %.4f" % (DA_NAME, hit, PICK_ATTACK, hit, WINDUP, rate))
    log("   all fields: %s" % unreal.ToolsetLibrary.get_object_properties(load(path), [
        "attack", "turnLeft90", "turnRight90", "lookAround", "attackPlayRate", "attackHitTime", "turnPlayRate", "turnTriggerDegrees", "turnCooldownSeconds",
        "stoopEaseRate", "footTraceUp", "footTraceDown", "footIKInterpSpeed", "maxPelvisDrop", "physicsMaxDistance"]))


def abp_state(path):
    abp = load(path)
    gc = abp.generated_class()
    cdo = unreal.get_default_object(gc) if gc else None
    anim_set = cdo.get_editor_property("anim_set") if cdo else None
    return abp, gc, anim_set


def abp_status(abp):
    try:
        return abp.get_editor_property("status")
    except Exception:  # noqa: BLE001
        return getattr(abp, "status", "?")


def abp_problems(name, want_set):
    path = ap(WARDEN, name)
    if not exists(path):
        return ["missing"]
    abp, gc, anim_set = abp_state(path)
    if gc is None:
        return ["no generated class (not compiled?)"]
    probs = []
    parent = abp.get_blueprint_parent_class()
    if parent is None or not parent.get_path_name().endswith("LBWardenAnimInstance"):
        probs.append("parent class %s" % (parent.get_path_name() if parent else None))
    ts = abp.get_editor_property("target_skeleton")
    if ts is None or not ts.get_path_name().endswith("SK_Warden_Skeleton.SK_Warden_Skeleton"):
        probs.append("target skeleton %s" % (ts.get_path_name() if ts else None))
    got = anim_set.get_path_name() if anim_set else None
    if want_set and (got is None or not got.endswith("%s.%s" % (DA_NAME, DA_NAME))):
        probs.append("class default AnimSet = %s" % got)
    if not want_set and got is not None:
        probs.append("class default AnimSet unexpectedly %s" % got)
    return probs


def build_abp(name, want_set):
    path = ap(WARDEN, name)
    probs = abp_problems(name, want_set)
    if not probs:
        log("skip %s: exists and verifies" % name)
        return
    if exists(path) and probs != ["no generated class (not compiled?)"]:
        raise RuntimeError("%s exists but does not verify (%s); not rebuilding an Animation Blueprint in place: remove it by hand" % (name, probs))
    if exists(path):
        abp = load(path)
    else:
        f = unreal.AnimBlueprintFactory()
        f.set_editor_property("parent_class", unreal.load_class(None, "/Script/LastBell.LBWardenAnimInstance"))
        f.set_editor_property("target_skeleton", load(SKEL_W))
        log("  factory ParentClass/TargetSkeleton read back: %s" % unreal.ToolsetLibrary.get_object_properties(f, ["ParentClass", "TargetSkeleton"]))
        abp = create(name, WARDEN, unreal.AnimBlueprint, f)
    unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    log("  %s compiled (1st), status=%s" % (name, abp_status(abp)))
    if want_set:
        cdo = unreal.get_default_object(abp.generated_class())
        cdo.set_editor_property("anim_set", load(ap(DATA, DA_NAME)))
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
        log("  %s class default AnimSet set; compiled (2nd), status=%s" % (name, abp_status(abp)))
    save(path)
    probs = abp_problems(name, want_set)
    if probs:
        raise RuntimeError("%s does not verify after the build: %s" % (name, probs))


def step_abp():
    build_abp(ABP_NAME, True)
    build_abp(ABP_SPIKE, False)
    for n in (ABP_NAME, ABP_SPIKE):
        abp, gc, anim_set = abp_state(ap(WARDEN, n))
        log("ABP %s: parent %s, target skeleton %s, generated class %s, class default AnimSet %s, status %s, anim graphs %d" % (
            n, abp.get_blueprint_parent_class().get_name(), abp.get_editor_property("target_skeleton").get_name(), gc.get_name(),
            anim_set.get_name() if anim_set else None, abp_status(abp), len(abp.get_animation_graphs())))


def step_verify():
    meas = load_meas()
    bad = []
    for name, mesh, root, seq, forbid in RIGS:
        p = rig_problems(name, mesh, root, seq, forbid)
        log("verify rig %s: %s" % (name, p or "ok"))
        bad += p
    ok = rtg_ok()
    log("verify rtg: %s" % ("ok" if ok else "PROBLEM"))
    if not ok:
        bad.append("rtg")
    rtg_report()
    for n in CLIPS:
        ok = batch_ok(n)
        log("verify AN_Warden_%s: %s" % (n, "ok" if ok else "PROBLEM"))
        if not ok:
            bad.append(n)
    for name, samples in blend_plan(meas):
        p = blend_problems(name, samples)
        log("verify %s: %s" % (name, p or "ok"))
        bad += p
    for name, clip, bi, bo, trim in MONTAGES:
        p = montage_problems(name, clip, bi, bo, trim)
        log("verify %s: %s" % (name, p or "ok"))
        bad += p
    p = da_problems(meas)
    log("verify %s: %s" % (DA_NAME, p or "ok"))
    bad += p
    for n, want in ((ABP_NAME, True), (ABP_SPIKE, False)):
        p = abp_problems(n, want)
        log("verify %s: %s" % (n, p or "ok"))
        bad += p
    for k in EXISTING_KEEP:
        log("untouched check: %s exists=%s" % (k, exists(ap(ANI, k))))
    if bad:
        raise RuntimeError("verify found problems: %s" % bad)


# ----------------------------------------------------------------------------------------------------------------------
STEPS = ["rigs", "rtg", "batch", "measure", "blend", "montage", "animset", "abp", "verify"]
FUNCS = {"rigs": step_rigs, "rtg": step_rtg, "batch": step_batch, "measure": step_measure, "blend": step_blend, "montage": step_montage,
         "animset": step_animset, "abp": step_abp, "verify": step_verify}


def main():
    want = os.environ.get("P13_STEPS", "all")
    steps = STEPS if want == "all" else [s.strip() for s in want.split(",") if s.strip()]
    failed = []
    for s in steps:
        if s not in FUNCS:
            log("step %s: not implemented in this version" % s)
            continue
        log("==== step %s ====" % s)
        try:
            FUNCS[s]()
            log("step %s: OK" % s)
        except Exception:  # noqa: BLE001
            log("step %s: FAILED\n%s" % (s, traceback.format_exc()))
            failed.append(s)
            break  # later steps depend on this one
    log("failed steps: %s" % (failed if failed else "none"))
    log("P13_RETARGET_DONE")


main()
