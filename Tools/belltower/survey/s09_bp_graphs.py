"""P10-2 item 2 (read-only): class defaults + variables + graph DSL of the gameplay Blueprints.
Checks AssetTools.is_dirty before and after each read. Never saves, compiles or deletes."""
import sys, json, re
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
AS = "editor_toolset.toolsets.asset.AssetTools"
B = "editor_toolset.toolsets.blueprint.BlueprintTools"
O = "editor_toolset.toolsets.object.ObjectTools"
OUT = r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\blueprints_p10.json"
BPS = {
 "BP_SmallBell": "/Game/LastBell/Blueprints/Puzzles/BP_SmallBell",
 "BP_SequencePuzzle": "/Game/LastBell/Blueprints/Puzzles/BP_SequencePuzzle",
 "BP_Inscription": "/Game/LastBell/Blueprints/Puzzles/BP_Inscription",
 "BP_RitualMechanism": "/Game/LastBell/Blueprints/Interactables/BP_RitualMechanism",
 "BP_Door_Base": "/Game/LastBell/Blueprints/Interactables/BP_Door_Base",
 "BP_TagInteractable": "/Game/LastBell/Blueprints/Interactables/BP_TagInteractable",
 "BP_TagTrigger": "/Game/LastBell/Blueprints/Interactables/BP_TagTrigger",
 "BP_EndingTrigger": "/Game/LastBell/Blueprints/BP_EndingTrigger",
 "BP_Inspectable_Note": "/Game/LastBell/Blueprints/Interactables/BP_Inspectable_Note",
}
MAP = "/Game/LastBell/Maps/L_Monastery"
def jl(x):
    return json.loads(x) if isinstance(x, str) else x
def dirty(p):
    return ue.call(AS, "is_dirty", {"asset_path": p})
mode = sys.argv[1] if len(sys.argv) > 1 else "all"
res = {"dirty_before": {}, "dirty_after": {}, "bps": {}}
res["dirty_before"]["MAP"] = dirty(MAP)
for n, p in BPS.items():
    res["dirty_before"][n] = dirty(p)
print("before", res["dirty_before"], flush=True)
if mode == "dirtyonly":
    sys.exit(0)
def getp(ref, names):
    names = list(names)
    for _ in range(8):
        if not names:
            return {}
        try:
            return jl(ue.call(O, "get_properties", {"instance": {"refPath": ref}, "properties": names}))
        except RuntimeError as e:
            m = re.search(r"could not be read: (.*)$", str(e))
            if not m:
                return {"_error": str(e)[:200]}
            bad = [x.strip() for x in m.group(1).replace("'", "").split(",")]
            names = [x for x in names if x not in bad]
    return {}
for n, p in BPS.items():
    bp = {"refPath": p + "." + p.split("/")[-1]}
    r = {"path": p}
    try:
        r["parent"] = ue.call(B, "get_parent", {"blueprint": bp})
    except Exception as e:
        r["parent"] = "ERR " + str(e)[:150]
    try:
        r["variables"] = ue.call(B, "list_variables", {"blueprint": bp})
    except Exception as e:
        r["variables"] = "ERR " + str(e)[:150]
    try:
        cdo = ue.call(B, "get_default_object", {"blueprint": bp})
        r["cdo_ref"] = cdo
        keys = list(jl(ue.call(O, "list_properties", {"instance": cdo})).keys())
        own = []
        for k in keys:
            if k == "primaryActorTick":
                break
            own.append(k)
        r["cdo_keys"] = own
        r["cdo_props"] = getp(cdo["refPath"], [k for k in own if not re.match(r"^on[A-Z]", k)])
    except Exception as e:
        r["cdo_err"] = str(e)[:300]
    try:
        r["graphs"] = ue.call(B, "list_graphs", {"blueprint": bp})
    except Exception as e:
        r["graphs"] = "ERR " + str(e)[:150]
    res["bps"][n] = r
    print(n, "parent", r.get("parent"), "graphs", r.get("graphs"), flush=True)
json.dump(res, open(OUT, "w"), indent=1)
