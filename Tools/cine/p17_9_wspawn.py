"""P17-9: delete the unused WSpawn_Tower (LBWardenSpawnPoint, MinStage 6) from L_Monastery, headless (Unreal CLOSED). One explicit save of the map.

Env: LB_OUT = JSON report; LB_MODE = "check" (default, read-only) or "apply" (delete, then one save of the map, then a census).
The census (EditorActorSubsystem.get_all_level_actors counts 3096 here, the MCP census 3103) must drop by exactly 1. Refuses to delete anything but one actor labelled WSpawn_Tower of class LBWardenSpawnPoint near (12165, 1665, 0), MinStage 6.
"""
import json
import os

import unreal

OUT = os.environ.get("LB_OUT", "")
APPLY = os.environ.get("LB_MODE", "check").lower() == "apply"
MAP = "/Game/LastBell/Maps/L_Monastery"
rep = {"mode": "apply" if APPLY else "check", "ok": False}

unreal.EditorLoadingAndSavingUtils.load_map(MAP)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = list(eas.get_all_level_actors())
rep["census_before"] = len(actors)
hits = [a for a in actors if a.get_actor_label() == "WSpawn_Tower"]
rep["hits"] = len(hits)
rep["spawn_points"] = sorted((a.get_actor_label(), a.get_class().get_name()) for a in actors if a.get_class().get_name() == "LBWardenSpawnPoint")
if len(hits) == 1:
    a = hits[0]
    loc = a.get_actor_location()
    rep["class"] = a.get_class().get_name()
    rep["loc"] = [loc.x, loc.y, loc.z]
    rep["min_stage"] = a.get_editor_property("min_stage")
    good = (rep["class"] == "LBWardenSpawnPoint" and abs(loc.x - 12165) < 1 and abs(loc.y - 1665) < 1 and abs(loc.z) < 1 and rep["min_stage"] == 6)
    rep["matches"] = good
    if APPLY and good:
        rep["destroyed"] = bool(eas.destroy_actor(a))
        rep["census_after"] = len(list(eas.get_all_level_actors()))
        if rep["destroyed"] and rep["census_after"] == rep["census_before"] - 1:
            rep["saved"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
            rep["ok"] = rep["saved"]
    else:
        rep["ok"] = good and not APPLY
unreal.log("P17-9 WSPAWN RESULT %s" % json.dumps(rep))
if OUT:
    with open(OUT, "w") as f:
        json.dump(rep, f, indent=1)
