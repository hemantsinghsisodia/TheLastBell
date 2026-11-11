"""P18-3: points BP_LBPlayerController.HUDWidgetClass at the C++ HUD (ULBHUDWidget), headless (Unreal CLOSED, one Unreal process at a time).

Run (editor closed), the same route as Tools/ui/p18_2_assets.py (-ExecutePythonScript in the non-commandlet editor-cmd, which quits itself):

    UnrealEditor-Cmd.exe <uproject> -ExecutePythonScript="<this file>" -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>

Environment variables:
    LB_OUT   path of the JSON report (default Saved/Logs/p18_3_assets.json)
    LB_MODE  "apply" (default): set, compile and save BP_LBPlayerController explicitly, then verify in the same process
             "verify": read-only; run it in a FRESH process to prove what is on disk

Only BP_LBPlayerController is touched (one explicit EditorAssetLibrary.save_asset, never save-all). WBP_HUD and WBP_Inspect were left in place, unused (deleted later by Tools/ui/p18_cleanup.py):
the script reports their referencers so the review can delete them. The process exit code is NOT reliable; read the report (`ok`) or the log
line "P18-3 RESULT".
"""
import json
import os
import traceback

import unreal

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
OUT = os.environ.get("LB_OUT", os.path.join(ROOT, "Saved", "Logs", "p18_3_assets.json"))
APPLY = os.environ.get("LB_MODE", "apply").lower() == "apply"
EAL = unreal.EditorAssetLibrary

BP_PC = "/Game/LastBell/Blueprints/BP_LBPlayerController"
WBP_HUD = "/Game/LastBell/UI/WBP_HUD"
WBP_INSPECT = "/Game/LastBell/UI/WBP_Inspect"

report = {"mode": "apply" if APPLY else "verify", "checks": 0, "failures": [], "notes": [], "saved": [], "findings": {}}


def check(name, ok, detail=""):
    report["checks"] += 1
    if not ok:
        report["failures"].append("%s %s" % (name, detail))
        unreal.log_error("P18-3 CHECK FAILED: %s %s" % (name, detail))
    return bool(ok)


def cdo_of(bp):
    return unreal.get_default_object(bp.generated_class())


def main():
    bp = EAL.load_asset(BP_PC)
    if not check("BP_LBPlayerController exists", bp is not None):
        return
    wanted = unreal.LBHUDWidget.static_class()
    current = cdo_of(bp).get_editor_property("hud_widget_class")
    if current != wanted:
        if not APPLY:
            check("BP_LBPlayerController.HUDWidgetClass == LBHUDWidget", False, "read %s" % current)
        else:
            cdo_of(bp).set_editor_property("hud_widget_class", wanted)
            bp.modify()
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
            status = str(bp.get_editor_property("status")) if True else ""
            report["notes"].append("compiled BP_LBPlayerController: " + status)
            check("BP_LBPlayerController compiles", "ERROR" not in status.upper(), status)
            ok = EAL.save_asset(BP_PC, False)
            check("saved " + BP_PC, bool(ok))
            if ok:
                report["saved"].append(BP_PC)
    check("BP_LBPlayerController.HUDWidgetClass == LBHUDWidget (read back)", cdo_of(bp).get_editor_property("hud_widget_class") == wanted,
          cdo_of(bp).get_editor_property("hud_widget_class"))
    # the pause action from P18-2 must have survived
    check("BP_LBPlayerController.PauseAction is still set", cdo_of(bp).get_editor_property("pause_action") is not None)

    for path in (WBP_HUD, WBP_INSPECT):
        refs = [str(r) for r in EAL.find_package_referencers_for_asset(path, False)]
        report["findings"][path.rsplit("/", 1)[1] + "_referencers"] = refs
        report["notes"].append("%s referencers: %s" % (path, refs))

    dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    ours = [d for d in dirty if d == BP_PC]
    check("BP_LBPlayerController is not dirty after the save", not ours, ours)
    others = [d for d in dirty if d != BP_PC]
    if others:
        report["notes"].append("dirty packages outside ours (NOT saved): %s" % others[:10])


try:
    main()
except Exception as exc:
    report["failures"].append("exception: %r" % (exc,))
    report["traceback"] = traceback.format_exc()
    unreal.log_error("P18-3 EXCEPTION: " + report["traceback"])
finally:
    report["ok"] = not report["failures"]
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    unreal.log("P18-3 RESULT: %s (%d checks, %d failures) mode=%s" % ("PASS" if report["ok"] else "FAIL", report["checks"], len(report["failures"]), report["mode"]))
    unreal.SystemLibrary.execute_console_command(None, "QUIT_EDITOR")
