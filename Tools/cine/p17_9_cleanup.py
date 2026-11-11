"""P17-9 cleanup (Unreal CLOSED, headless). Deletes the old V5.5 Warden materials/textures, BP_EndingTrigger and WBP_Ending.

Run: UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>
Env: LB_OUT = JSON report path; LB_MODE = "check" (read-only, default) or "apply" (check, then delete only if every referencer is inside the set).
Never saves anything; deletion goes through EditorAssetLibrary.delete_asset (per asset).
"""
import json
import os

import unreal

OUT = os.environ.get("LB_OUT", "")
APPLY = os.environ.get("LB_MODE", "check").lower() == "apply"
W = "/Game/LastBell/Characters/Warden"
OLD_M = ["Wool", "BellMetal", "RustedIron", "Skin", "Leather", "ChainIron"]
OLD_MI = ["Wool", "BellMetal", "RustedIron", "Skin", "ChainIron"]
KEEP = [W + "/Materials/" + n for n in ("M_Warden_Apparition", "M_Warden_ApparitionGlow", "MI_Warden_Apparition_Body",
                                         "MI_Warden_Apparition_Mask", "MI_Warden_ApparitionGlow")]
EAL = unreal.EditorAssetLibrary
AR = unreal.AssetRegistryHelpers.get_asset_registry()
AR.search_all_assets(True)

cand = [W + "/Materials/M_Warden_" + n for n in OLD_M] + [W + "/Materials/MI_Warden_" + n for n in OLD_MI]
tex = [str(p).split(".")[0] for p in EAL.list_assets(W + "/Textures", recursive=False, include_folder=False)]
cand += tex
cand += ["/Game/LastBell/Blueprints/BP_EndingTrigger", "/Game/LastBell/UI/WBP_Ending"]
cset = set(cand)

rep = {"mode": "apply" if APPLY else "check", "candidates": len(cand), "textures": len(tex), "missing": [], "outside": {}, "keep_deps_in_set": {},
       "deleted": [], "failed": [], "ok": False, "refs_in_set": 0}
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
    refs = AR.get_referencers(p, opts) or []
    rep["refs_in_set"] = rep.get("refs_in_set", 0) + len([r for r in refs if str(r) in cset])
    out = sorted(str(r) for r in refs if str(r) not in cset)
    if out:
        rep["outside"][p] = out
for k in KEEP:
    if not EAL.does_asset_exist(k):
        rep["missing"].append(k)
        continue
    deps = AR.get_dependencies(k, opts) or []
    bad = sorted(str(d) for d in deps if str(d) in cset)
    if bad:
        rep["keep_deps_in_set"][k] = bad
clean = rep["refs_in_set"] >= 11 and not rep["outside"] and not rep["keep_deps_in_set"] and not rep["missing"] and len(tex) == 20
unreal.log("P17-9 candidates=%d textures=%d outside=%d keepdeps=%d missing=%d" % (len(cand), len(tex), len(rep["outside"]), len(rep["keep_deps_in_set"]), len(rep["missing"])))
if APPLY and clean:
    # MIs first, then the masters, then textures, then the ending pair
    order = [p for p in cand if "/MI_" in p] + [p for p in cand if "/M_" in p] + tex + cand[-2:]
    for p in order:
        if EAL.delete_asset(p):
            rep["deleted"].append(p)
        else:
            rep["failed"].append(p)
    rep["ok"] = not rep["failed"]
else:
    rep["ok"] = clean and not APPLY
    if APPLY:
        unreal.log_error("P17-9 NOT deleting: referencers outside the set / unexpected state")
unreal.log("P17-9 RESULT ok=%s deleted=%d failed=%d" % (rep["ok"], len(rep["deleted"]), len(rep["failed"])))
if OUT:
    with open(OUT, "w") as f:
        json.dump(rep, f, indent=1)
