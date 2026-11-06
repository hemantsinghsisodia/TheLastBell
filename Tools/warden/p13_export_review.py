"""p13_export_review.py -- P13-5: export the 12 AN_Warden_<Name> Mixamo clips to FBX with the Warden mesh, for the Blender contact sheet.

HEADLESS, Unreal editor CLOSED, READ-ONLY on Content (nothing is saved; the preview mesh is only set in memory if a clip has none):
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=Tools/warden/p13_export_review.py -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>
Writes SourceArt/Warden/P13_review/AN_Warden_<Name>.fbx (animation + armature only: the preview-mesh export asserts without a renderer); the Warden mesh comes from the P12 source SourceArt/Warden/V5_5/exports/SK_Warden_LOD0.fbx. (Exporting the mesh or the preview mesh from Unreal asserts under -nullrhi, in the material-bake path.) Last line printed: P13_EXPORT_DONE
"""
import os
import traceback

import unreal

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
OUT = os.path.join(ROOT, "SourceArt", "Warden", "P13_review")
ANI = "/Game/LastBell/Characters/Warden/Anims"
SK_W = "/Game/LastBell/Characters/Warden/Meshes/SK_Warden"
CLIPS = ["MutantWalking", "ZombieWalk", "MutantRun", "ZombieRunning", "MutantIdle", "CrouchedWalking", "CrouchingIdle",
         "TurnLeft90", "TurnRight90", "ZombieAttack", "MutantSwiping", "LookAround"]


def log(*a):
    print("P13X| " + " ".join(str(x) for x in a))


def main():
    os.makedirs(OUT, exist_ok=True)
    opt = unreal.FbxExportOption()
    log("FbxExportOption props:", [m for m in dir(opt) if not m.startswith("_") and not callable(getattr(opt, m, None))])
    for k, v in (("ascii", False), ("export_local_time", True), ("export_morph_targets", False), ("vertex_color", False),
                 ("level_of_detail", False), ("collision", False), ("force_front_x_axis", False), ("map_skeletal_motion_to_root", False)):
        try:
            opt.set_editor_property(k, v)
        except Exception as e:  # noqa: BLE001
            log("  option %s not set: %r" % (k, e))
    mesh = unreal.load_asset(SK_W)
    failed = []
    for n in CLIPS:
        path = "%s/AN_Warden_%s" % (ANI, n)
        seq = unreal.load_asset(path)
        pm = seq.get_editor_property("preview_skeletal_mesh") if hasattr(seq, "preview_skeletal_mesh") else None
        try:
            pm = seq.get_preview_mesh()
        except Exception:  # noqa: BLE001
            pass
        log("%s preview mesh before: %s" % (n, pm.get_name() if pm else None))
        if pm is None or pm.get_path_name() != mesh.get_path_name():
            seq.set_preview_skeletal_mesh(mesh)  # in memory only: never saved by this script
        fn = os.path.join(OUT, "AN_Warden_%s.fbx" % n)
        if os.path.exists(fn):
            os.remove(fn)
        task = unreal.AssetExportTask()
        task.set_editor_property("object", seq)
        task.set_editor_property("filename", fn)
        task.set_editor_property("exporter", unreal.AnimSequenceExporterFBX())
        task.set_editor_property("automated", True)
        task.set_editor_property("prompt", False)
        task.set_editor_property("replace_identical", True)
        task.set_editor_property("options", opt)
        ok = unreal.Exporter.run_asset_export_task(task)
        size = os.path.getsize(fn) if os.path.exists(fn) else 0
        log("export %s -> %s, %d bytes" % (n, ok, size))
        if not ok or size < 1000:
            failed.append(n)
    log("failed exports: %s" % (failed or "none"))
    log("P13_EXPORT_DONE")


try:
    main()
except Exception:  # noqa: BLE001
    log("FAILED\n" + traceback.format_exc())
    log("P13_EXPORT_DONE")
