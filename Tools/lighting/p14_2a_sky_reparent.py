"""P14-2a: reparent MI_NightStormSky to M_LB_StormSky with the editor CLOSED (headless, no rendering).

Why headless: the MCP MaterialInstanceTools.set_parent call on this MI, while the level's sky (its child MI_Env_NightSky) was
being drawn, crashed the editor (render-thread assertion "UniformExpressionCache should be up to date", 2026-11-07).
With -nullrhi nothing is drawn, so that check can't fire.

Run (editor closed):
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>
It writes the before/after overrides to the JSON path in the environment variable LB_OUT and saves only MI_NightStormSky
(and MI_Env_NightSky only if the reparent marked it dirty).
"""
import json
import os

import unreal

MI_PARENT = "/Game/LastBell/ArtTest/Sky/MI_NightStormSky"
MI_CHILD = "/Game/LastBell/Environments/Courtyard/Materials/MI_Env_NightSky"
NEW_PARENT = "/Game/LastBell/Environments/Sky/M_LB_StormSky"
OUT = os.environ.get("LB_OUT", "")


def overrides(mi):
    def name(v):
        return str(v.get_editor_property("parameter_info").get_editor_property("name"))

    sc = {name(v): round(float(v.get_editor_property("parameter_value")), 6) for v in mi.get_editor_property("scalar_parameter_values")}
    vc = {}
    for v in mi.get_editor_property("vector_parameter_values"):
        c = v.get_editor_property("parameter_value")
        vc[name(v)] = [round(c.r, 6), round(c.g, 6), round(c.b, 6), round(c.a, 6)]
    tx = {}
    for v in mi.get_editor_property("texture_parameter_values"):
        t = v.get_editor_property("parameter_value")
        tx[name(v)] = t.get_path_name() if t else None
    parent = mi.get_editor_property("parent")
    return {"parent": parent.get_path_name() if parent else None, "scalars": sc, "vectors": vc, "textures": tx}


def pkg_dirty(asset):
    name = asset.get_outermost().get_name()
    return any(p.get_name() == name for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())


result = {"ok": False}
try:
    mi = unreal.EditorAssetLibrary.load_asset(MI_PARENT)
    child = unreal.EditorAssetLibrary.load_asset(MI_CHILD)
    new_parent = unreal.EditorAssetLibrary.load_asset(NEW_PARENT)
    result["loaded"] = {"mi": bool(mi), "child": bool(child), "new_parent": bool(new_parent)}
    if not (mi and child and new_parent):
        raise RuntimeError("an asset failed to load")

    result["before"] = {"MI_NightStormSky": overrides(mi), "MI_Env_NightSky": overrides(child)}

    unreal.MaterialEditingLibrary.set_material_instance_parent(mi, new_parent)
    unreal.MaterialEditingLibrary.update_material_instance(mi)

    result["after"] = {"MI_NightStormSky": overrides(mi), "MI_Env_NightSky": overrides(child)}
    result["dirty"] = {"MI_NightStormSky": pkg_dirty(mi), "MI_Env_NightSky": pkg_dirty(child)}

    b, a = result["before"], result["after"]
    same_child = b["MI_Env_NightSky"] == a["MI_Env_NightSky"]
    same_mi = {k: b["MI_NightStormSky"][k] == a["MI_NightStormSky"][k] for k in ("scalars", "vectors", "textures")}
    result["checks"] = {
        "mi_parent_is_storm_sky": a["MI_NightStormSky"]["parent"] == new_parent.get_path_name(),
        "mi_overrides_unchanged": all(same_mi.values()),
        "child_unchanged": same_child,
    }
    if all(result["checks"].values()):
        result["saved_mi"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(mi, False))
        if result["dirty"]["MI_Env_NightSky"]:
            result["saved_child"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(child, False))
        result["ok"] = result["saved_mi"]
    else:
        result["saved_mi"] = False
        result["note"] = "a check failed: nothing saved"
except Exception as e:  # report, never half-save
    result["error"] = repr(e)

if OUT:
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1, sort_keys=True)
unreal.log("P14_2A_SKY_REPARENT " + json.dumps(result, sort_keys=True))
