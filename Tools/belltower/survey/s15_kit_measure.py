"""P10-2 item 4 (read-only): measure reusable meshes (bounds, slots->MI, Nanite, tris, UCX count/collision flag).
Writes Docs/ArtTest/belltower/kit_p10.json. Resumable: skips meshes already in the file."""
import sys, json, os, time
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
SM = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
O = "editor_toolset.toolsets.object.ObjectTools"
OUT = r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\kit_p10.json"
ALL = json.load(open(r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\meshes_list_p10.json"))
def sel(p):
    n = p.split("/")[-1]
    if "/Environments/Kit/" in p: return True
    if "/Environments/Crypt/Meshes/" in p: return True
    if "/Props/Procedural/" in p:
        if any(k in n for k in ("Ivy", "Gravestone", "GraveMound", "Cobweb", "StoneCross", "WoodCross", "HandCart", "EarthPatch", "Key", "Pew", "Altar", "Lectern", "Glass", "Backdrop", "MechShell", "Cross", "SlateShards", "FirePit", "DeadTree", "CandleFlame")):
            return False
        return True
    if "/Props/CC0/" in p:
        return any(k in n for k in ("Candleholders", "Statue", "Candlestick", "Bucket", "WineBarrel", "WoodenTable", "TreeStump", "Spade", "Axe", "PickeDirty"))
    if "/ArtTest/Props/" in p: return any(k in n for k in ("Lantern", "Crate", "Stool", "Root_Cluster"))
    if "/ThirdParty/Fab/Dungeon/" in p:
        return not any(k in n for k in ("Skeleton", "Skull", "Bread", "Bowl", "Cup", "Cutlery", "Jug", "Mug", "Pitcher", "Plate", "Pouch", "Bottle", "Scribe", "Dungeon_bowl"))
    if "/ThirdParty/Fab/" in p: return True
    return False
paths = [p for p in ALL if sel(p)]
paths = [p if "." in p.split("/")[-1] else p + "." + p.split("/")[-1] for p in paths]
try: res = json.load(open(OUT))
except Exception: res = {}
print("to measure", len(paths), "already", len(res), flush=True)
t0 = time.time()
def jl(x): return json.loads(x) if isinstance(x, str) else x
for i, p in enumerate(paths):
    if p in res and "err" not in res[p]: continue
    m = {"refPath": p}; r = {}
    try:
        r["bounds"] = ue.call(SM, "get_bounds", {"mesh": m})
        slots = ue.call(SM, "get_material_slots", {"mesh": m}); r["slots"] = {}
        for s in slots:
            try: r["slots"][s] = (ue.call(SM, "get_material", {"mesh": m, "slot_name": s}) or {}).get("refPath")
            except Exception as e: r["slots"][s] = "ERR"
        r["nanite"] = ue.call(SM, "is_nanite_enabled", {"mesh": m})
        r["tris"] = ue.call(SM, "get_triangle_count", {"mesh": m, "lod_index": 0})
        bs = jl(ue.call(O, "get_properties", {"instance": m, "properties": ["bodySetup"]}))["bodySetup"]
        if isinstance(bs, dict):
            g = jl(ue.call(O, "get_properties", {"instance": bs, "properties": ["aggGeom", "collisionTraceFlag"]}))
            ag = g.get("aggGeom", {})
            r["ucx_convex"] = len(ag.get("convexElems", [])); r["ucx_box"] = len(ag.get("boxElems", []))
            r["ucx_sphere"] = len(ag.get("sphereElems", [])); r["ucx_sphyl"] = len(ag.get("sphylElems", []))
            r["collisionTraceFlag"] = g.get("collisionTraceFlag")
    except Exception as e:
        r["err"] = str(e)[:200]
    res[p] = r
    if i % 10 == 0:
        print(i, len(paths), round(time.time() - t0), flush=True)
        json.dump(res, open(OUT, "w"), indent=0)
json.dump(res, open(OUT, "w"), indent=0)
print("done", len(res), round(time.time() - t0))
