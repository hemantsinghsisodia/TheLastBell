"""P18 cleanup (Unreal CLOSED, headless). Deletes the retired WBP_MainMenu, WBP_HUD and WBP_Inspect (replaced by the C++ widgets).

Run: UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>
Env: LB_OUT = JSON report path; LB_MODE = "check" (read-only, default) or "apply" (check, then delete only if every referencer is inside the set).
Same pattern as Tools/cine/p17_9_cleanup.py. Never saves anything; deletion goes through EditorAssetLibrary.delete_asset (per asset).
Also reports which widget classes BP_LBPlayerController and BP_MenuPlayerController use (must be the C++ ones).
"""
import json
import os

import unreal

OUT = os.environ.get("LB_OUT", "")
APPLY = os.environ.get("LB_MODE", "check").lower() == "apply"
EAL = unreal.EditorAssetLibrary
AR = unreal.AssetRegistryHelpers.get_asset_registry()
AR.search_all_assets(True)

UI = "/Game/LastBell/UI"
cand = [UI + "/WBP_MainMenu", UI + "/WBP_HUD", UI + "/WBP_Inspect"]
cset = set(cand)
rep = {"mode": "apply" if APPLY else "check", "missing": [], "outside": {}, "referencers": {}, "controllers": {}, "deleted": [], "failed": [], "ok": False}
opts = unreal.AssetRegistryDependencyOptions()
opts.include_hard_package_references = True
opts.include_soft_package_references = True
opts.include_searchable_names = True
opts.include_hard_management_references = True
opts.include_soft_management_references = True

for p in cand:
    if not EAL.does_asset_exist(p):
        rep["missing"].append(p)
        continue
    refs = sorted(str(r) for r in (AR.get_referencers(p, opts) or []))
    rep["referencers"][p] = refs
    out = [r for r in refs if r not in cset]
    if out:
        rep["outside"][p] = out

for name, path in (("BP_LBPlayerController", "/Game/LastBell/Blueprints/BP_LBPlayerController"),
                   ("BP_MenuPlayerController", "/Game/LastBell/Blueprints/Menu/BP_MenuPlayerController")):
    bp = unreal.load_asset(path)
    cdo = unreal.get_default_object(bp.generated_class()) if bp else None
    rep["controllers"][name] = str(cdo.get_editor_property("hud_widget_class")) if cdo else "NOT LOADED"

hud_ok = "LBHUDWidget" in rep["controllers"].get("BP_LBPlayerController", "")
menu_ok = "LBMainMenuWidget" in rep["controllers"].get("BP_MenuPlayerController", "")
clean = not rep["outside"] and not rep["missing"] and hud_ok and menu_ok
unreal.log("P18-CLEANUP outside=%d missing=%d hud_ok=%s menu_ok=%s controllers=%s" % (len(rep["outside"]), len(rep["missing"]), hud_ok, menu_ok, rep["controllers"]))
if APPLY and clean:
    for p in cand:
        if EAL.delete_asset(p):
            rep["deleted"].append(p)
        else:
            rep["failed"].append(p)
    rep["ok"] = not rep["failed"]
else:
    rep["ok"] = clean and not APPLY
    if APPLY:
        unreal.log_error("P18-CLEANUP NOT deleting: referencers outside the set / controllers not on the C++ widgets")
unreal.log("P18-CLEANUP RESULT ok=%s deleted=%d failed=%d" % (rep["ok"], len(rep["deleted"]), len(rep["failed"])))
if OUT:
    with open(OUT, "w") as f:
        json.dump(rep, f, indent=1)
