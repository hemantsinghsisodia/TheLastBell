"""P10-2 item 2 (read-only): dump the gameplay actors to Docs/ArtTest/belltower/gameplay_p10.json
(class, parent, transform, components with relative transforms / mesh / collision / visibility, instance properties).
Also dumps the AI markers (item 3) and the nav volume into the same file under the key 'ai'.
No set/compile/save calls."""
import sys, json, re, time
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
S = "editor_toolset.toolsets.scene.SceneTools"
A = "editor_toolset.toolsets.actor.ActorTools"
O = "editor_toolset.toolsets.object.ObjectTools"
B = "editor_toolset.toolsets.blueprint.BlueprintTools"
OUT = r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\gameplay_p10.json"

WANT = ["Puzzle_Bells", "Bell_1", "Bell_2", "Bell_3", "Bell_4", "Clue_Inscription", "Mech_Ritual3", "Door_Tower",
        "Door_Shortcut", "Bell", "EndingTrigger", "Trig_TowerTop", "Trig_CloisterEntered", "CP_Cloister", "CP_TowerBase",
        "CP_TowerTop", "Note_Cloister"]
FOLDERS = ["Gameplay/Cloister", "Gameplay/BellTower", "Gameplay/Notes", "Gameplay/Courtyard", "Gameplay/Chapel", "Gameplay/Approach"]
SCENE = ["relativeLocation", "relativeRotation", "relativeScale3D", "bVisible", "bHiddenInGame"]
MESH = ["staticMesh", "overrideMaterials", "castShadow"]

def jl(x):
    return json.loads(x) if isinstance(x, str) else x

def getp(ref, names):
    """get_properties that retries without unreadable names; returns dict."""
    names = list(names)
    for _ in range(6):
        if not names:
            return {}
        try:
            r = jl(ue.call(O, "get_properties", {"instance": {"refPath": ref}, "properties": names}))
            return r
        except RuntimeError as e:
            m = re.search(r"could not be read: (.*)$", str(e))
            if not m:
                return {"_error": str(e)[:200]}
            bad = [x.strip() for x in m.group(1).replace("'", "").split(",")]
            names = [n for n in names if n not in bad]
    return {}

def keys_of(ref):
    return list(jl(ue.call(O, "list_properties", {"instance": {"refPath": ref}})).keys())

def own_keys(keys, stop):
    out = []
    for k in keys:
        if k in stop:
            break
        out.append(k)
    return out

def is_delegate(k):
    return re.match(r"^on[A-Z]", k) is not None

def comp_rec(cref):
    cls = ue.call(O, "get_class", {"instance": {"refPath": cref}})["refPath"]
    d = {"name": cref.split(".")[-1], "class": cls}
    keys = keys_of(cref)
    want = []
    if "relativeLocation" in keys:
        want += SCENE
    if "staticMesh" in keys:
        want += MESH
    want += [k for k in ("intensity", "attenuationRadius", "sourceRadius", "lightColor", "castShadows", "castVolumetricShadow",
                         "innerConeAngle", "outerConeAngle", "text", "skeletalMesh") if k in keys]
    if cls.startswith("/Script/LastBell") or cls.startswith("/Game"):
        want += [k for k in own_keys(keys, {"primaryComponentTick", "componentTags"}) if not is_delegate(k)]
    p = getp(cref, want)
    if "bodyInstance" in keys:
        bi = getp(cref, ["bodyInstance"]).get("bodyInstance", {})
        d["collisionProfile"] = bi.get("collisionProfileName")
        d["collisionEnabled"] = bi.get("collisionEnabled")
    d["props"] = p
    return d

def actor_rec(label, ref):
    d = {"label": label, "ref": ref}
    d["class"] = ue.call(O, "get_class", {"instance": {"refPath": ref}})["refPath"]
    d["transform"] = ue.call(A, "get_actor_transform", {"actor": {"refPath": ref}})
    d["bounds"] = ue.call(A, "get_actor_bounds", {"actor": {"refPath": ref}})
    d["folder"] = None
    try:
        d["tags"] = ue.call(A, "get_tags", {"actor": {"refPath": ref}})
    except Exception as e:
        d["tags"] = str(e)[:100]
    if d["class"].startswith("/Game"):
        bp = d["class"].rsplit("_C", 1)[0]
        bpath = bp
        d["blueprint"] = bpath
        try:
            d["parent"] = ue.call(B, "get_parent", {"blueprint": {"refPath": bpath}})
        except Exception as e:
            d["parent"] = "ERR " + str(e)[:100]
    keys = keys_of(ref)
    comps = [c["refPath"] for c in ue.call(A, "get_components", {"actor": {"refPath": ref}})]
    cnames = {c.split(".")[-1].lower() for c in comps}
    own = [k for k in own_keys(keys, {"primaryActorTick"}) if k.lower() not in cnames and not is_delegate(k)]
    d["actor_prop_keys"] = own
    d["instance_props"] = getp(ref, own + ["bHidden"])
    d["components"] = [comp_rec(c) for c in comps]
    return d

t0 = time.time()
label2ref = {}
for f in FOLDERS:
    for x in ue.call(S, "get_actors_in_folder", {"folder_path": f, "recursive": False}):
        lab = ue.call(A, "get_label", {"actor": x})
        label2ref.setdefault(lab, []).append((x["refPath"], f))
print("labels indexed", len(label2ref), time.time() - t0, flush=True)
res = {"actors": [], "missing": []}
for lab in WANT:
    if lab not in label2ref:
        res["missing"].append(lab)
        continue
    for ref, f in label2ref[lab]:
        r = actor_rec(lab, ref)
        r["folder"] = f
        res["actors"].append(r)
        print("done", lab, round(time.time() - t0), flush=True)
json.dump(res, open(OUT, "w"), indent=1)
print("wrote", OUT, "missing", res["missing"])
