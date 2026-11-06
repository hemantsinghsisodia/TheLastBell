"""p13_reimport_ybot.py -- P13-4b: re-import the Y Bot and its 12 Mixamo clips so that the Y Bot FACES +X, like the Warden.

HEADLESS, Unreal editor CLOSED (it writes Content), and no other UnrealEditor / UnrealBuildTool process may be running:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=Tools/warden/p13_reimport_ybot.py -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>
Last line printed: P13R_DONE

Why: Mixamo's Y Bot imports facing +Y, the Warden faces +X. The P13-4 retarget (pelvis yaw + a -90 root key) left the arms along the facing axis.
The FBX import rotation (FbxImportUI skeletal_mesh_import_data.import_rotation / anim_sequence_import_data.import_rotation, yaw -90) makes the
source face +X so the retargeter needs no workaround.

Findings that shaped this script (probes, see MCP_NOTES "Animation assets in headless Python"):
  * Importing over an existing mesh name replaces the mesh but keeps the OLD skeleton asset (stale reference pose), and sometimes ignores the new
    rotation. So the old Y Bot assets are deleted first (clips, physics asset, mesh, skeleton, and the IK Rig / Retargeter that point at them) and
    everything is imported fresh under the same names. Deletion is checked with exists().
  * The anim-only import (import_mesh False, FBXIT_ANIMATION, skeleton = SK_LB_YBot_Skeleton) works from Python and produces one sequence named
    <destination>_mixamo_com, which is renamed to AN_YBot_<Name>.
The facing is proven from bone positions before anything is saved; the script stops if it is not +X.
"""
import os
import traceback

import unreal

SRC = r"C:\Hemant\Prj\Learning\TheLastBell\ExternalAssets\Incoming\mixamo"
RET = "/Game/LastBell/Characters/Warden/Retarget"
YAW = float(os.environ.get("P13_YBOT_YAW", "-90"))
YBOT, SKEL, PHYS = "SK_LB_YBot", "SK_LB_YBot_Skeleton", "SK_LB_YBot_PhysicsAsset"
# name -> frame count (keys in Unreal), from the lead's Blender check in P13-3
CLIPS = [("MutantWalking", 44), ("ZombieWalk", 122), ("MutantRun", 27), ("ZombieRunning", 25), ("MutantIdle", 122), ("CrouchedWalking", 32),
         ("CrouchingIdle", 76), ("TurnLeft90", 29), ("TurnRight90", 29), ("ZombieAttack", 80), ("MutantSwiping", 81), ("LookAround", 135)]
EAL = unreal.EditorAssetLibrary


def log(*a):
    print("P13R| " + " ".join(str(x) for x in a))


def ap(n):
    return "%s/%s" % (RET, n)


def exists(n):
    return EAL.does_asset_exist(ap(n))


def run_import(fn, name, opts):
    t = unreal.AssetImportTask()
    t.filename, t.destination_path, t.destination_name = fn, RET, name
    t.replace_existing, t.automated, t.save = True, True, False
    t.factory, t.options = unreal.FbxFactory(), opts
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    return list(t.get_editor_property("imported_object_paths"))


def mesh_opts():
    o = unreal.FbxImportUI()
    o.automated_import_should_detect_type = False
    o.import_mesh = True
    o.import_as_skeletal = True
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    o.original_import_type = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    o.import_materials = False
    o.import_textures = False
    o.import_animations = False
    o.create_physics_asset = True
    o.skeletal_mesh_import_data.set_editor_property("import_rotation", unreal.Rotator(roll=0, pitch=0, yaw=YAW))
    return o


def anim_opts(skel):
    o = unreal.FbxImportUI()
    o.automated_import_should_detect_type = False
    o.import_mesh = False
    o.import_as_skeletal = False
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
    o.original_import_type = unreal.FBXImportType.FBXIT_ANIMATION
    o.import_materials = False
    o.import_textures = False
    o.import_animations = True
    o.create_physics_asset = False
    o.skeleton = skel
    o.anim_sequence_import_data.set_editor_property("import_rotation", unreal.Rotator(roll=0, pitch=0, yaw=YAW))
    return o


def pos(pose, b):
    t = unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD).translation
    return (float(t.x), float(t.y), float(t.z))


def pose_opts():
    o = unreal.AnimPoseEvaluationOptions()
    o.set_editor_property("evaluation_type", unreal.AnimDataEvalType.RAW)
    o.set_editor_property("should_retarget", False)
    o.set_editor_property("extract_root_motion", False)
    o.set_editor_property("incorporate_root_motion_into_pose", False)
    return o


def facing_report(pose, tag):
    """Toes ahead of the feet, head ahead of the neck, left hand on -Y (like the Warden's hand_l), all along +X. Returns the numbers and whether they hold."""
    b = {n: pos(pose, n) for n in ("Hips", "Neck", "Head", "LeftFoot", "LeftToeBase", "RightFoot", "RightToeBase", "LeftHand", "RightHand")}
    toe_l = b["LeftToeBase"][0] - b["LeftFoot"][0]
    toe_r = b["RightToeBase"][0] - b["RightFoot"][0]
    head = b["Head"][0] - b["Neck"][0]
    lat = b["LeftFoot"][1] - b["RightFoot"][1]
    log("%s: LeftToeBase.x - LeftFoot.x = %+.1f | RightToeBase.x - RightFoot.x = %+.1f | Head.x - Neck.x = %+.1f | LeftFoot.y - RightFoot.y = %+.1f "
        "(left is -Y) | LeftHand %s RightHand %s" % (tag, toe_l, toe_r, head, lat, tuple(round(v, 1) for v in b["LeftHand"]), tuple(round(v, 1) for v in b["RightHand"])))
    return toe_l > 3 and toe_r > 3 and head > 0 and lat < 0, b


def main():
    # 1. delete the old Y Bot assets and what depends on them (clips first, skeleton last). RTG_LB_YBot_To_Warden is NOT deleted: delete_asset
    #    reports True but leaves it (something references it); p13_retarget.py rebuilds it in place after this script.
    old = ["IK_LB_YBot"] + ["AN_YBot_" + n for n, _ in CLIPS] + [PHYS, YBOT, SKEL]
    for n in old:
        if exists(n):
            ok = EAL.delete_asset(ap(n))
            log("delete %s -> %s, still exists: %s" % (n, ok, exists(n)))
    left = [n for n in old if exists(n)]
    if left:
        raise RuntimeError("could not delete %s (referenced? see the log); stopping before any import" % left)

    # 2. the mesh, fresh
    paths = run_import(os.path.join(SRC, "MX_YBot.fbx"), YBOT, mesh_opts())
    log("mesh import ->", paths)
    mesh = unreal.load_asset(ap(YBOT))
    skel = mesh.get_editor_property("skeleton")
    if skel.get_path_name() != "%s.%s" % (ap(SKEL), SKEL):
        raise RuntimeError("the new mesh uses skeleton %s, expected %s" % (skel.get_path_name(), SKEL))
    ref = unreal.AnimPoseExtensions.get_reference_pose(skel)
    ok, _ = facing_report(ref, "T-pose (skeleton reference pose)")
    bb = mesh.get_bounds()
    log("mesh bounds extent x=%.1f y=%.1f z=%.1f (arms span along Y when the Y Bot faces X)" % (bb.box_extent.x, bb.box_extent.y, bb.box_extent.z))
    if not ok or bb.box_extent.y < bb.box_extent.x:
        raise RuntimeError("the Y Bot does not face +X after the import (yaw %.1f); nothing saved" % YAW)

    # 3. clips, anim-only onto that skeleton
    bad = []
    po = pose_opts()
    for n, keys in CLIPS:
        tmp = "AN_YBot_" + n
        paths = run_import(os.path.join(SRC, "MX_%s.fbx" % n), tmp, anim_opts(skel))
        cands = [p for p in paths]
        log("clip %s import -> %s" % (n, cands))
        picked = None
        for p in cands:
            a = unreal.load_asset(p)
            k = int(unreal.AnimationLibrary.get_num_keys(a))
            if k == keys:
                picked = p
        if not picked:
            bad.append("%s: no sequence with %d keys in %s" % (n, keys, cands))
            continue
        final = ap(tmp)
        if picked != "%s.%s" % (final, tmp):
            if not EAL.rename_asset(picked.split(".")[0], final):
                bad.append("%s: rename %s -> %s failed" % (n, picked, final))
                continue
        a = unreal.load_asset(final)
        if a is None or a.get_skeleton().get_path_name() != skel.get_path_name():
            bad.append("%s: not on the new skeleton" % n)
            continue
        log("  %s: %.4f s, %d keys, skeleton %s, root motion %s" % (tmp, a.get_play_length(), unreal.AnimationLibrary.get_num_keys(a), a.get_skeleton().get_name(),
                                                                   unreal.AnimationLibrary.is_root_motion_enabled(a)))
        if n == "MutantIdle":
            fr = [facing_report(unreal.AnimPoseExtensions.get_anim_pose_at_frame(a, i, po), "MutantIdle frame %d" % i) for i in (0, 30, 60, 90)]
            if not all(f[0] for f in fr):
                bad.append("MutantIdle facing numbers do not show +X")
    if bad:
        raise RuntimeError("clip import problems, nothing saved: %s" % bad)

    # 4. save everything (the throwaway names never existed on disk)
    for n in [YBOT, SKEL, PHYS] + ["AN_YBot_" + c for c, _ in CLIPS]:
        ok = EAL.save_asset(ap(n), only_if_is_dirty=False)
        log("save %s -> %s" % (n, ok))
        if not ok:
            raise RuntimeError("save failed: " + n)
    stray = [p for p in EAL.list_assets(RET, recursive=False) if "_mixamo_com" in p or "Take_001" in p or "/TMP_" in p]
    log("stray assets in Retarget/: %s" % (stray or "none"))
    log("folder:", sorted(p.rsplit("/", 1)[1].split(".")[0] for p in EAL.list_assets(RET, recursive=False)))


try:
    main()
    log("OK")
except Exception:
    log("FAILED\n" + traceback.format_exc())
log("P13R_DONE")
