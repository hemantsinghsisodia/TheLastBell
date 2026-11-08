"""P15 S1 rain occlusion spike (throwaway). Spec: Docs/plans/P15_S1_RAIN_SPIKE.md. Record: Docs/ArtTest/fx/s1/s1_build.md.

Editor must be open on L_Monastery. Nothing here ever saves an asset or the map; the spike lives in memory only.
Python: C:\\Users\\heman\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe -I Tools/fx/s1_spike.py <command>

    build                       2.1-2.3: material M_LB_Spike_Unlit, system NS_LB_Rain_Spike (emitters Rain and Splash), Q3 distance-field mode
    place                       2.4: the 5 S1_Spike_* actors (folder FX/Spike), transforms and user variables
    check                       read everything back, print PASS/FAIL/WARN/INFO lines, exit 1 on any FAIL
    set --world pie|editor [--rain-scale K] [--splash-scale K] [--splash-fall F] [--radius CM] [--off]
                                set the user variables on the five spike components of that world and read them back
    blockers --apply|--remove [--dry-run]   6.2 hidden blocker boxes under the plank rows (--apply is for the lead only)
    remove [--dry-run|--yes]    delete the 5 actors, any blockers and the /Game/LastBell/FX/Spike/ assets (the lead runs it after the verdict)

All rules: idempotent, finds actors by exact label, reads back every write, never saves.
"""
import argparse
import copy
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Tools", "mcp"))
from ue import UE  # noqa: E402

# ---- toolsets and paths -------------------------------------------------------------------------
NS = "NiagaraToolsets.NiagaraToolset_System"
NC = "NiagaraToolsets.NiagaraToolset_Component"
NI = "NiagaraToolsets.NiagaraToolset_Info"
SC = "editor_toolset.toolsets.scene.SceneTools"
AC = "editor_toolset.toolsets.actor.ActorTools"
OB = "editor_toolset.toolsets.object.ObjectTools"
AS = "editor_toolset.toolsets.asset.AssetTools"
MT = "editor_toolset.toolsets.material.MaterialTools"
EA = "EditorToolset.EditorAppToolset"

FOLDER = "/Game/LastBell/FX/Spike"
SUF = os.environ.get("S1_TEST_SUFFIX", "")  # test only: build a throwaway copy of the assets under another name (default: none)
MAT_NAME = "M_LB_Spike_Unlit" + SUF
SYS_NAME = "NS_LB_Rain_Spike" + SUF
MAT_PKG = FOLDER + "/" + MAT_NAME
MAT_OBJ = MAT_PKG + "." + MAT_NAME
SYS_PKG = FOLDER + "/" + SYS_NAME
SYS_OBJ = SYS_PKG + "." + SYS_NAME
SYS = {"refPath": SYS_OBJ}
OUTLINER = "FX/Spike"
TEMPLATE_SYSTEM = "/Niagara/DefaultAssets/DefaultSystem.DefaultSystem"
TEMPLATE_EMITTER = "/Niagara/DefaultAssets/Templates/Emitters/Fountain.Fountain"
GRADIENT_FN = "/Engine/Functions/Engine_MaterialFunctions01/Gradient/RadialGradientExponential.RadialGradientExponential"
COLLISION_MODULE = "/Niagara/Modules/Collision/Collision.Collision"
DF_MODULE = "/Niagara/Modules/Collision/NiagaraDistanceFieldCollisions.NiagaraDistanceFieldCollisions"

FLOAT = "/Script/Niagara.NiagaraFloat"
BOOL = "/Script/Niagara.NiagaraBool"
V3 = "/Script/CoreUObject.Vector3f"
V2 = "/Script/CoreUObject.Vector2f"
LCOL = "/Script/CoreUObject.LinearColor"
ENUMS = "/Niagara/Enums/"
LINKED_S = "/Script/NiagaraEditor.NiagaraExt_StackInputData_Linked"
HLSL_S = "/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression"
ENUM_S = "/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum"

EP, EU, PS, PU = "EmitterSpawnScript", "EmitterUpdateScript", "ParticleSpawnScript", "ParticleUpdateScript"

# section 2.2 user parameters (name, kind, default)
USER_VARS = [("User.RainRate", "f", 1000.0), ("User.SplashRate", "f", 200.0), ("User.BoxSize", "v", (1400.0, 1100.0, 10.0)),
             ("User.SpawnOffset", "v", (0.0, 0.0, 1000.0)), ("User.RainFall", "f", 1250.0), ("User.SplashFall", "f", 20000.0),
             ("User.RainRadius", "f", 10.0)]
FIXED_BOUNDS = {"min": {"x": -1500, "y": -1500, "z": -3000}, "max": {"x": 1500, "y": 1500, "z": 5500}, "isValid": True}

# section 2.2 per-emitter spec
EMITTERS = {
    "Rain": dict(rate="User.RainRate", fall="User.RainFall", life=5.0, size=(2.5, 50.0), kill=True,
                 radius=("link", "User.RainRadius"), align="VelocityAligned"),
    "Splash": dict(rate="User.SplashRate", fall="User.SplashFall", life=4.0, size=(12.0, 12.0), kill=False,
                   radius=("fixed", 6.0), align="Unaligned"),
}
COLOR = (2.5, 2.8, 3.2, 1.0)

# section 2.4 placement: label -> (location, BoxSize, SpawnOffset, RainRate, SplashRate)
ROWS = [
    ("S1_Spike_CyN", (2500, 1150, 0), (1400, 1100, 10), (0, 0, 1000), 1540, 200),
    ("S1_Spike_CyS", (4500, -1150, 0), (1400, 900, 10), (0, 0, 1000), 1260, 200),
    ("S1_Spike_Chapel", (7000, 0, 0), (1800, 1400, 10), (0, 0, 2500), 2520, 300),
    ("S1_Spike_Cloister", (10900, 1800, 0), (1200, 2200, 10), (0, 0, 1500), 2640, 300),
    ("S1_Spike_Tower", (12500, 2000, 2500), (960, 960, 10), (0, 0, 2600), 920, 150),
]
LABELS = [r[0] for r in ROWS]

# ---- MCP plumbing -----------------------------------------------------------------------------


class Ed:
    """UE wrapper: waits out 'compile in flight', repeats READ-ONLY calls after a connection reset (never a mutation)."""

    def __init__(self):
        self.ue = UE()

    def call(self, ts, tool, args=None, read=False):
        flights = 0
        resets = 0
        while True:
            try:
                return self.ue.call(ts, tool, args)
            except RuntimeError as e:
                if "in flight" in str(e) and flights < 40:
                    flights += 1
                    time.sleep(1.5)
                    continue
                raise
            except (ConnectionError, OSError):
                if read and resets < 3:
                    resets += 1
                    time.sleep(1.0)
                    self.ue = UE()
                    continue
                raise


ed = None


def E():
    global ed
    if ed is None:
        ed = Ed()
    return ed


def js(r):
    if isinstance(r, (dict, list, bool, int, float)) or r is None:
        return r
    try:
        return json.loads(r)
    except (TypeError, ValueError):
        return r


def ref(p):
    return {"refPath": p}


def R(em="", script="", module="", rend=-1, inputs=()):
    """StackItemRef."""
    return {"system": SYS, "emitterName": em, "scriptName": script, "moduleName": module, "rendererIndex": rend, "inputNameStack": list(inputs)}


def T(p):
    return {"classStructOrEnum": {"refPath": p}}


# StackInput / variable value payloads
def lit(struct, value):
    return {"struct": {"refPath": struct}, "value": value}


def fl(v):
    return lit(FLOAT, {"value": v})


def bl(v):
    return lit(BOOL, {"value": -1 if v else 0})


def v2(x, y):
    return lit(V2, {"x": x, "y": y})


def v3(x, y, z):
    return lit(V3, {"x": x, "y": y, "z": z})


def col(r, g, b, a):
    return lit(LCOL, {"r": r, "g": g, "b": b, "a": a})


def linked(name, typ):
    return {"struct": {"refPath": LINKED_S}, "value": {"linkedVariable": {"name": name, "type": T(typ)}}}


def hlsl(s):
    return {"struct": {"refPath": HLSL_S}, "value": {"hlslExpression": s}}


def enum(path, enum_name, display):
    return {"struct": {"refPath": ENUM_S}, "value": {"enum": {"refPath": path}, "enumName": enum_name, "displayName": display}}


def setin(rf, data):
    return E().call(NS, "SetStackInputData", {"stackInputRef": rf, "inputData": data})


def getin(rf):
    return E().call(NS, "GetStackInputData", {"stackInputRef": rf}, read=True)


# ---- build log ----------------------------------------------------------------------------------
FAILS = []


def step(label, fn):
    """Run one MCP step, print OK/ERR, remember failures."""
    try:
        r = fn()
        shown = json.dumps(r.get("value") if isinstance(r, dict) and "value" in r else r)
        print("  OK  ", label, (shown or "")[:110])
        return r
    except Exception as e:  # noqa: BLE001
        print("  ERR ", label, "|", str(e)[:400])
        FAILS.append(label)
        return None


# ---- Niagara helpers ----------------------------------------------------------------------------


def wait_compiled():
    return E().call(NS, "GetSystemCompileState", {"system": SYS}, read=True)


def emitters():
    return [e["emitterName"] for e in E().call(NS, "GetSystemSummary", {"system": SYS}, read=True)["emitters"]]


def modules(em, script):
    return E().call(NS, "GetScriptStackTopology", {"scriptRef": R(em, script)}, read=True)["modules"]


def module_names(em, script):
    return [m["moduleName"] for m in modules(em, script)]


def setparams_module(em, script, names):
    """Name of the SetParameters module whose inputs are exactly `names`, else None."""
    for m in modules(em, script):
        if m.get("bIsSetParametersModule") and sorted(i["name"] for i in m["inputs"]) == sorted(names):
            return m["moduleName"]
    return None


def ensure_setparams(em, script, entries):
    """entries: [(name, type, default payload)]. Returns the module name (the engine generates SetVariables_<GUID>)."""
    mn = setparams_module(em, script, [e[0] for e in entries])
    if mn:
        return mn
    params = [{"variable": {"name": n, "type": T(t)}, "defaultValue": d} for n, t, d in entries]
    return E().call(NS, "AddSetParametersModule", {"moduleLocationRef": R(em, script), "parameters": params})["moduleName"]


def user_var_payload(name, kind, val):
    if kind == "f":
        return {"name": name, "type": T(FLOAT), "defaultValue": fl(val)}
    return {"name": name, "type": T(V3), "defaultValue": v3(*val)}


# ---- 2.1 material -------------------------------------------------------------------------------


def build_material():
    print("[2.1] material")
    pr = js(E().call(OB, "get_properties", {"instance": ref("/Niagara/DefaultAssets/DefaultSpriteMaterial.DefaultSpriteMaterial"),
                                            "properties": ["blendMode", "twoSided"]}, read=True))
    print("  INFO DefaultSpriteMaterial:", pr, "-> blend mode is not Translucent: create M_LB_Spike_Unlit (spec 2.1 step 3)")
    if not E().call(AS, "exists", {"path": MAT_PKG}, read=True):
        step("create_material", lambda: E().call(MT, "create_material", {"folder_path": FOLDER, "asset_name": MAT_NAME}))
    m = ref(MAT_OBJ)
    for k, v in [("blendMode", "BLEND_Translucent"), ("twoSided", True), ("shadingModel", "MSM_Unlit"), ("bUsedWithNiagaraSprites", True)]:
        step("material." + k, lambda k=k, v=v: E().call(OB, "set_properties", {"instance": m, "values": json.dumps({k: v})}))
    ex = E().call(MT, "get_expressions", {"material_or_function": m}, read=True)
    if not ex:
        def add(cls, x, y):
            return E().call(MT, "add_expression", {"material_or_function": m, "expression_class": ref("/Script/Engine.MaterialExpression" + cls), "x": x, "y": y})["refPath"]

        def con(src, out, dst, inp):
            E().call(MT, "connect_expressions", {"from_expression": ref(src), "from_output_name": out, "to_expression": ref(dst), "to_input_name": inp})
        pc, fc = add("ParticleColor", -600, 0), add("MaterialFunctionCall", -600, 200)
        E().call(OB, "set_properties", {"instance": ref(fc), "values": json.dumps({"materialFunction": ref(GRADIENT_FN)})})
        m1, m2 = add("Multiply", -300, 0), add("Multiply", -300, 200)
        con(pc, "RGB", m1, "A")
        con(fc, "", m1, "B")
        con(pc, "A", m2, "A")
        con(fc, "", m2, "B")
        for e, prop in [(m1, "MP_EmissiveColor"), (m2, "MP_Opacity")]:
            E().call(MT, "connect_to_output", {"expression": ref(e), "output_name": "", "material_property": prop})
        print("  OK   graph built (ParticleColor x RadialGradientExponential -> Emissive and Opacity)")
    elif len(ex) != 4:
        FAILS.append("material graph has %d expressions, expected 4: delete the material and rerun" % len(ex))
        print("  ERR  material graph has", len(ex), "expressions")
    step("material recompile", lambda: E().call(MT, "recompile", {"material_or_function": m}))


# ---- 2.2/2.3 system -----------------------------------------------------------------------------


def configure_collision(em, spec):
    """Collision module: place, ensure order, set the distance-field mode (Q3), kill, radius, restitution, friction, rest."""
    if "Collision" not in module_names(em, PU):
        step(em + ": AddModule Collision", lambda: E().call(NS, "AddModule", {"moduleLocationRef": R(em, PU), "moduleAsset": ref(COLLISION_MODULE)})["moduleName"])
    cref = lambda n: R(em, PU, "Collision", -1, [n])  # noqa: E731

    # Q3 step 1: the PLACED module exposes the static switch 'GPU Collision Type' (an enum); pick the 'Distance Field' value by display name
    q3 = {"ok": False}
    try:
        topo = E().call(NS, "GetModuleTopology", {"moduleRef": R(em, PU, "Collision")}, read=True)
        cand = [i for i in topo["inputs"] if i["name"] == "GPU Collision Type"]
        if not cand:
            raise RuntimeError("placed Collision module has no 'GPU Collision Type' input")
        epath = cand[0]["type"]["classStructOrEnum"]["refPath"]
        info = js(E().call(NI, "UEnum_Info", {"enum": ref(epath)}, read=True))
        df = [v for v in info["Values"] if "distance" in v["DisplayName"].lower()]
        if len(df) != 1:
            raise RuntimeError("expected one 'Distance' enumerator, found %s" % [v["DisplayName"] for v in info["Values"]])
        ename = info["Name"] + "::" + df[0]["Name"]
        res = setin(cref("GPU Collision Type"), enum(epath, ename, df[0]["DisplayName"]))
        back = getin(cref("GPU Collision Type"))
        q3["ok"] = back["value"]["enumName"] == ename
        print("  %s %s: GPU Collision Type static switch=%s, set %s, read back %s" % ("OK  " if q3["ok"] else "ERR ", em, cand[0]["bIsStaticSwitch"], ename, back["value"]["displayName"]))
        if not q3["ok"]:
            FAILS.append(em + ": distance-field mode read-back mismatch " + json.dumps(res)[:100])
    except Exception as e:  # noqa: BLE001
        print("  ERR  %s: Q3 step 1 failed: %s" % (em, str(e)[:300]))
        q3_fallback(em)
        FAILS.append(em + ": distance-field mode not set (Q3)")

    step(em + ": Radius Calculation Type = Custom", lambda: setin(cref("Radius Calculation Type"), enum(
        ENUMS + "ENiagaraCollisionRadiusOptions.ENiagaraCollisionRadiusOptions", "ENiagaraCollisionRadiusOptions::NewEnumerator3", "Custom")))
    kind, val = spec["radius"]
    step(em + ": Particle Radius", lambda: setin(cref("Particle Radius"), linked(val, FLOAT) if kind == "link" else fl(val)))
    step(em + ": Collision Enabled", lambda: setin(cref("Collision Enabled"), bl(True)))
    step(em + ": KillOnCollision", lambda: setin(cref("KillOnCollision"), bl(spec["kill"])))
    if not spec["kill"]:
        step(em + ": Restitution 0", lambda: setin(cref("Restitution"), fl(0.0)))
        step(em + ": Friction 1", lambda: setin(cref("Friction"), fl(1.0)))
        step(em + ": Enable Rest State", lambda: setin(cref("Enable Rest State"), bl(True)))

    # the engine reports 'post-dependency SolveForcesAndVelocity not met' (Collision must come BEFORE it) and offers a Fix
    mods = module_names(em, PU)
    if mods.index("Collision") > mods.index("SolveForcesAndVelocity"):
        wait_compiled()
        iss = E().call(NS, "GetStackIssues", {"system": SYS}, read=True)
        for i in iss["issues"]:
            if i["severity"] == "Error" and i["location"]["emitterName"] == em and i["location"]["moduleName"] == "Collision":
                for f in i["fixes"]:
                    if f["style"] == "Fix":
                        try:
                            E().call(NS, "ApplyStackIssueFix", {"system": SYS, "issueId": i["issueId"], "fixId": f["fixId"]})
                        except RuntimeError as e:  # the fix applies, but this call can still raise 'compile in flight'
                            print("  INFO ApplyStackIssueFix raised (checked by topology next):", str(e)[:80])
        mods = module_names(em, PU)
        ok = mods.index("Collision") < mods.index("SolveForcesAndVelocity")
        print("  %s %s: Collision moved before SolveForcesAndVelocity: %s" % ("OK  " if ok else "ERR ", em, mods))
        if not ok:
            FAILS.append(em + ": module order")


def q3_fallback(em):
    """Section 2.3 steps 2-4, only reached if step 1 failed."""
    print("  [Q3 step 2] NiagaraDistanceFieldCollisions (zero-input module)")
    try:
        r = E().call(NS, "AddModule", {"moduleLocationRef": R(em, PU), "moduleAsset": ref(DF_MODULE)})
        print("    added", r["moduleName"], "inputs", len(r["inputs"]), "order", module_names(em, PU))
    except Exception as e:  # noqa: BLE001
        print("    ERR", str(e)[:200])
    print("  [Q3 step 3] assets named Collision/Rain/Splash/Spark under /Niagara, /Engine, /Game/LastBell/ThirdParty")
    for folder in ["/Niagara", "/Engine", "/Game/LastBell/ThirdParty"]:
        for nm in ["Collision", "Rain", "Splash", "Spark"]:
            try:
                for p in E().call(AS, "find_assets", {"folder_path": folder, "name": nm}, read=True):
                    print("    ", p)
            except Exception as e:  # noqa: BLE001
                print("    ERR", folder, nm, str(e)[:100])
    print("  [Q3 step 4] distance-field mode not reachable over MCP: stop and report to the lead")


def configure_emitter(em, spec):
    print("[2.2] emitter", em)
    vals = {"SimTarget": "GPUComputeSim", "bLocalSpace": False, "bDeterminism": False, "CalculateBoundsMode": "Fixed", "FixedBounds": FIXED_BOUNDS}
    step(em + ": SetEmitterData", lambda: E().call(NS, "SetEmitterData", {"emitter": R(em), "emitterData": {"propertyValues": json.dumps(vals)}}))
    step(em + ": Spawn Rate", lambda: setin(R(em, EU, "SpawnRate", -1, ["SpawnRate"]), linked(spec["rate"], FLOAT)))

    ip = lambda n: R(em, PS, "InitializeParticle", -1, [n])  # noqa: E731
    step(em + ": Lifetime Mode Direct Set", lambda: setin(ip("Lifetime Mode"), enum(ENUMS + "ENiagara_LifetimeMode.ENiagara_LifetimeMode", "ENiagara_LifetimeMode::NewEnumerator0", "Direct Set")))
    step(em + ": Lifetime", lambda: setin(ip("Lifetime"), fl(spec["life"])))
    step(em + ": Sprite Size Mode Non-Uniform", lambda: setin(ip("Sprite Size Mode"), enum(ENUMS + "ENiagara_SizeScaleMode.ENiagara_SizeScaleMode", "ENiagara_SizeScaleMode::NewEnumerator4", "Non-Uniform")))
    step(em + ": Sprite Size", lambda: setin(ip("Sprite Size"), v2(*spec["size"])))
    step(em + ": Color", lambda: setin(ip("Color"), col(*COLOR)))

    sl = lambda n: R(em, PS, "ShapeLocation", -1, [n])  # noqa: E731
    step(em + ": Shape Primitive Box/Plane", lambda: setin(sl("Shape Primitive"), enum(ENUMS + "Location/ENiagara_LocationShapes.ENiagara_LocationShapes", "ENiagara_LocationShapes::NewEnumerator2", "Box / Plane")))
    step(em + ": Box Size <- User.BoxSize", lambda: setin(sl("Box Size"), linked("User.BoxSize", V3)))
    step(em + ": Offset Mode Default", lambda: setin(sl("Offset Mode"), enum(ENUMS + "Transforms/ENiagara_OffsetMode.ENiagara_OffsetMode", "ENiagara_OffsetMode::NewEnumerator0", "Default")))
    step(em + ": Offset <- User.SpawnOffset", lambda: setin(sl("Offset"), linked("User.SpawnOffset", V3)))
    av = lambda n: R(em, PS, "AddVelocity", -1, [n])  # noqa: E731
    step(em + ": Velocity Mode Linear", lambda: setin(av("Velocity Mode"), enum(ENUMS + "Utility/ENiagara_VelocityMode.ENiagara_VelocityMode", "ENiagara_VelocityMode::NewEnumerator0", "Linear")))
    step(em + ": Velocity", lambda: setin(av("Velocity"), hlsl("float3(0, 0, -%s)" % spec["fall"])))

    for mn in ["GravityForce", "Drag", "ScaleColor"]:
        if mn in module_names(em, PU):
            step(em + ": RemoveModule " + mn, lambda mn=mn: E().call(NS, "RemoveModule", {"moduleToRemove": R(em, PU, mn)}))
    configure_collision(em, spec)

    rr = R(em, "", "", 0)
    step(em + ": renderer 0", lambda: E().call(NS, "SetRendererData", {"renderer": rr, "rendererData": {"propertyValues": json.dumps(
        {"Material": ref(MAT_OBJ), "Alignment": spec["align"], "FacingMode": "FaceCamera"})}}))


def build_latch():
    em = "Splash"
    print("[2.2] Splash latch and renderer 1")
    c = lambda n, t, d: (n, t, d)  # noqa: E731
    mn = ensure_setparams(em, PS, [c("Particles.Landed", BOOL, bl(False)), c("Particles.RingSize", V2, v2(30, 30)), c("Particles.SpriteFacing", V3, v3(0, 0, 1))])
    print("  OK   spawn SetParameters module:", mn)
    ml = ensure_setparams(em, PU, [c("Particles.Landed", BOOL, bl(False))])
    step("latch: Particles.Landed = Landed || HasCollided", lambda: setin(R(em, PU, ml, -1, ["Particles.Landed"]), hlsl("Particles.Landed || Particles.HasCollided")))
    mc = ensure_setparams(em, PU, [c("Particles.Color", LCOL, col(0, 0, 0, 0))])
    step("latch: Particles.Color = Landed ? orange : 0", lambda: setin(R(em, PU, mc, -1, ["Particles.Color"]), hlsl(
        "Particles.Landed ? float4(5.0, 1.4, 0.2, 1.0) : float4(0.0, 0.0, 0.0, 0.0)")))
    print("  INFO update order:", module_names(em, PU))

    # renderer 1: a second sprite renderer, custom facing, size bound to Particles.RingSize
    r1 = R(em, "", "", 1)
    try:
        E().call(NS, "GetRendererData", {"rendererRef": r1}, read=True)
    except RuntimeError:
        step("AddRenderer (sprite)", lambda: E().call(NS, "AddRenderer", {"newRendererLocation": R(em), "rendererClass": ref("/Script/Niagara.NiagaraSpriteRendererProperties")}))
    pv = json.loads(E().call(NS, "GetRendererData", {"rendererRef": r1}, read=True)["propertyValues"])
    size_b = copy.deepcopy(pv["SpriteSizeBinding"])
    size_b.update({"rootName": "RingSize", "dataSetName": "RingSize", "cachedDisplayName": "Particles.RingSize", "bindingSourceMode": "ExplicitParticles"})
    size_b["paramMapVariable"]["name"] = "Particles.RingSize"
    face_b = copy.deepcopy(pv["SpriteFacingBinding"])
    face_b["bindingSourceMode"] = "ExplicitParticles"
    vals = {"Material": ref(MAT_OBJ), "Alignment": "Unaligned", "FacingMode": "CustomFacingVector", "SpriteSizeBinding": size_b, "SpriteFacingBinding": face_b}
    step("renderer 1 (custom facing, RingSize)", lambda: E().call(NS, "SetRendererData", {"renderer": r1, "rendererData": {"propertyValues": json.dumps(vals)}}))


def build_system():
    print("[2.2] system", SYS_PKG)
    if not E().call(AS, "exists", {"path": SYS_PKG}, read=True):
        step("CreateNiagaraSystem", lambda: E().call(NS, "CreateNiagaraSystem", {"assetName": SYS_NAME, "assetPath": FOLDER, "templateSystem": ref(TEMPLATE_SYSTEM)}))
    ems = emitters()
    if "Fountain" in ems:
        step("RemoveEmitter Fountain", lambda: E().call(NS, "RemoveEmitter", {"emitterToRemove": R("Fountain")}))
    step("AddUserVariables", lambda: E().call(NS, "AddUserVariables", {"system": SYS, "variablesToAdd": [user_var_payload(*v) for v in USER_VARS]}))
    for em in EMITTERS:
        if em not in emitters():
            step("AddEmitter " + em + " (template Fountain)", lambda em=em: E().call(NS, "AddEmitter", {"system": SYS, "templateEmitter": ref(TEMPLATE_EMITTER), "emitterName": em}))
    for em, spec in EMITTERS.items():
        configure_emitter(em, spec)
    build_latch()


def report_compile():
    cs = wait_compiled()
    print("[done] compile aggregate=%s errors=%s warnings=%s stale=%s" % (cs["aggregateStatus"], cs["bHasErrors"], cs["bHasWarnings"], cs["bIsStale"]))
    for s in cs["scripts"]:
        print("   ", s["emitterName"], s["scriptName"].split("::")[-1], s["lastCompileStatus"], s["errorSummary"][:150])
    iss = E().call(NS, "GetStackIssues", {"system": SYS}, read=True)
    print("[done] stack issues: errors=%d warnings=%d infos=%d" % (iss["numErrors"], iss["numWarnings"], iss["numInfos"]))
    for i in iss["issues"]:
        if i["severity"] != "Info":
            l = i["location"]
            print("   %s %s %s %s: %s | %s" % (i["severity"], l["emitterName"], l["scriptName"].split("::")[-1], l["moduleName"], i["shortDescription"], i["longDescription"][:200]))
    return cs, iss


def cmd_build(_a):
    E()
    build_material()
    build_system()
    cs, iss = report_compile()
    if iss["numErrors"] or cs["bHasErrors"] or cs["aggregateStatus"] != "UpToDate":
        FAILS.append("compile or stack errors")
    if FAILS:
        print("BUILD FAILED:", FAILS)
        return 1
    print("BUILD OK (nothing saved; assets are dirty in memory)")
    return 0


# ---- 2.4 actors ---------------------------------------------------------------------------------


def actor_label(rp):
    lab = js(E().call(AC, "get_label", {"actor": ref(rp)}, read=True))
    lab = lab.get("label", lab) if isinstance(lab, dict) else lab
    return str(lab).strip('"')


def find_actors(label, world):
    """Exact-label actors in 'editor' or 'pie' world. find_actors matches labels loosely, so compare exactly."""
    found = js(E().call(SC, "find_actors", {"name": label, "tag": "", "collision_channels": []}, read=True) or "[]")
    out = []
    for a in found:
        rp = a.get("refPath", "") if isinstance(a, dict) else str(a)
        if ("UEDPIE" in rp) != (world == "pie"):
            continue
        if actor_label(rp) == label:
            out.append(rp)
    return out


def niagara_component(actor_ref):
    comps = E().call(AC, "get_components", {"actor": ref(actor_ref)}, read=True)
    hit = [c["refPath"] for c in comps if c["refPath"].endswith(".NiagaraComponent0")]
    if len(hit) != 1:
        raise RuntimeError("no single NiagaraComponent0 on %s: %s" % (actor_ref, comps))
    return {"refPath": hit[0]}


def setvar(comp, name, kind, val):
    typ, payload = (FLOAT, fl(val)) if kind == "f" else (V3, v3(*val))
    E().call(NC, "SetVariable", {"component": comp, "variable": {"name": name, "type": T(typ), "value": payload}})


def getvar(comp, name, kind):
    r = E().call(NC, "GetVariable", {"component": comp, "var": {"name": name, "type": T(FLOAT if kind == "f" else V3)}}, read=True)
    v = r["value"]["value"]
    return v["value"] if kind == "f" else (v["x"], v["y"], v["z"])


def close(a, b):
    if isinstance(a, tuple):
        return all(abs(x - y) < 1e-3 for x, y in zip(a, b))
    return abs(a - b) < 1e-3


def row_values(row):
    label, loc, box, off, rain, splash = row
    return {"User.RainRate": ("f", float(rain)), "User.SplashRate": ("f", float(splash)), "User.BoxSize": ("v", tuple(map(float, box))),
            "User.SpawnOffset": ("v", tuple(map(float, off))), "User.RainFall": ("f", 1250.0), "User.SplashFall": ("f", 20000.0), "User.RainRadius": ("f", 10.0)}


def pie_running():
    return bool(js(E().call(EA, "IsPIERunning", {}, read=True)))


def cmd_place(_a):
    E()
    if pie_running():
        print("REFUSED: PIE is running (SceneTools cannot spawn during PIE)")
        return 2
    bad = 0
    for row in ROWS:
        label, loc, *_ = row
        hit = find_actors(label, "editor")
        if len(hit) > 1:
            print("FAIL", label, "has", len(hit), "actors:", hit)
            bad += 1
            continue
        xf = {"location": dict(zip("xyz", map(float, loc))), "rotation": {"pitch": 0, "yaw": 0, "roll": 0}, "scale": {"x": 1, "y": 1, "z": 1}}
        if not hit:
            rp = E().call(SC, "add_to_scene_from_asset", {"asset_path": SYS_PKG, "name": label, "xform": xf})["refPath"]
            print("  created", label, rp)
        else:
            rp = hit[0]
            print("  found  ", label, rp)
        E().call(AC, "set_label", {"actor": ref(rp), "label": label})
        E().call(SC, "set_actor_folder", {"actor": ref(rp), "folder_path": OUTLINER})
        E().call(AC, "set_actor_transform", {"actor": ref(rp), "xform": xf, "worldspace": True})
        comp = niagara_component(rp)
        for name, (kind, val) in row_values(row).items():
            setvar(comp, name, kind, val)
            got = getvar(comp, name, kind)
            if not close(got, val):
                print("FAIL", label, name, "wrote", val, "read", got)
                bad += 1
        print("  set    ", label, "variables read back")
    print("PLACE", "FAILED" if bad else "OK", "(map is dirty in memory; do not save)")
    return 1 if bad else 0


# ---- check --------------------------------------------------------------------------------------
_fail = 0


def chk(name, cond, detail=""):
    global _fail
    if cond:
        print("PASS", name, detail)
    else:
        _fail += 1
        print("FAIL", name, detail)


def check_material():
    m = ref(MAT_OBJ)
    chk("material exists", bool(E().call(AS, "exists", {"path": MAT_PKG}, read=True)))
    pr = js(E().call(OB, "get_properties", {"instance": m, "properties": ["blendMode", "twoSided", "shadingModel", "bUsedWithNiagaraSprites"]}, read=True))
    chk("material Translucent", pr["blendMode"] == "BLEND_Translucent", pr["blendMode"])
    chk("material two-sided", pr["twoSided"] is True)
    chk("material Unlit", pr["shadingModel"] == "MSM_Unlit", pr["shadingModel"])
    chk("material usage flag bUsedWithNiagaraSprites", pr["bUsedWithNiagaraSprites"] is True)
    for prop in ["MP_EmissiveColor", "MP_Opacity"]:
        g = E().call(MT, "get_property_input", {"material": m, "material_property": prop}, read=True)
        chk("material " + prop + " wired", bool(g.get("expression")), (g.get("expression") or {}).get("refPath", "").split(":")[-1])


def lv(rf):
    return getin(rf)["value"]


def chk_linked(name, rf, want):
    v = lv(rf)
    got = v.get("linkedVariable", {}).get("name") if isinstance(v, dict) else None
    chk(name, got == want, "linked to %s" % got)


def chk_float(name, rf, want):
    v = lv(rf)
    chk(name, isinstance(v, dict) and "value" in v and abs(v["value"] - want) < 1e-4, str(v))


def chk_bool(name, rf, want):
    v = lv(rf)
    chk(name, isinstance(v, dict) and (v.get("value") != 0) == want, str(v))


def chk_enum(name, rf, display):
    v = lv(rf)
    chk(name, isinstance(v, dict) and v.get("displayName") == display, str(v.get("displayName") if isinstance(v, dict) else v))


def check_emitter(em, spec):
    print("-- emitter", em)
    pv = json.loads(E().call(NS, "GetEmitterData", {"emitterRef": R(em)}, read=True)["propertyValues"])
    chk(em + " SimTarget GPUComputeSim", pv["SimTarget"] == "GPUComputeSim", pv["SimTarget"])
    chk(em + " local space off", pv["bLocalSpace"] is False)
    chk(em + " determinism off", pv["bDeterminism"] is False)
    fb = pv["FixedBounds"]
    chk(em + " fixed bounds", pv["CalculateBoundsMode"] == "Fixed" and (fb["min"]["x"], fb["min"]["y"], fb["min"]["z"], fb["max"]["x"], fb["max"]["y"], fb["max"]["z"]) == (-1500, -1500, -3000, 1500, 1500, 5500))
    chk_linked(em + " spawn rate", R(em, EU, "SpawnRate", -1, ["SpawnRate"]), spec["rate"])
    ip = lambda n: R(em, PS, "InitializeParticle", -1, [n])  # noqa: E731
    chk_float(em + " lifetime", ip("Lifetime"), spec["life"])
    sz = lv(ip("Sprite Size"))
    chk(em + " sprite size", abs(sz["x"] - spec["size"][0]) < 1e-4 and abs(sz["y"] - spec["size"][1]) < 1e-4, str(sz))
    cl = lv(ip("Color"))
    chk(em + " colour", all(abs(cl[k] - v) < 1e-4 for k, v in zip("rgba", COLOR)), str(cl))
    sl = lambda n: R(em, PS, "ShapeLocation", -1, [n])  # noqa: E731
    chk_enum(em + " shape Box / Plane", sl("Shape Primitive"), "Box / Plane")
    chk_linked(em + " box size", sl("Box Size"), "User.BoxSize")
    chk_linked(em + " offset", sl("Offset"), "User.SpawnOffset")
    hv = lv(R(em, PS, "AddVelocity", -1, ["Velocity"]))
    chk(em + " velocity HLSL", hv.get("hlslExpression") == "float3(0, 0, -%s)" % spec["fall"], str(hv))
    pu = module_names(em, PU)
    chk(em + " no gravity/drag/scale-colour", not ({"GravityForce", "Drag", "ScaleColor"} & set(pu)), str(pu))
    chk(em + " Collision before SolveForcesAndVelocity", "Collision" in pu and pu.index("Collision") < pu.index("SolveForcesAndVelocity"), str(pu))
    cr = lambda n: R(em, PU, "Collision", -1, [n])  # noqa: E731
    gm = lv(cr("GPU Collision Type"))
    chk(em + " collision mode = GPU Distance Fields (Q3)", gm.get("displayName") == "GPU Distance Fields", gm.get("displayName"))
    chk_bool(em + " collision enabled", cr("Collision Enabled"), True)
    chk_bool(em + " kill on collision = %s" % spec["kill"], cr("KillOnCollision"), spec["kill"])
    chk_enum(em + " radius type Custom", cr("Radius Calculation Type"), "Custom")
    kind, val = spec["radius"]
    if kind == "link":
        chk_linked(em + " particle radius", cr("Particle Radius"), val)
    else:
        chk_float(em + " particle radius cm", cr("Particle Radius"), val)
    if not spec["kill"]:
        chk_float(em + " restitution 0", cr("Restitution"), 0.0)
        chk_float(em + " friction 1", cr("Friction"), 1.0)
        chk_bool(em + " rest state on", cr("Enable Rest State"), True)
    r0 = json.loads(E().call(NS, "GetRendererData", {"rendererRef": R(em, "", "", 0)}, read=True)["propertyValues"])
    chk(em + " renderer 0", r0["Alignment"] == spec["align"] and r0["FacingMode"] == "FaceCamera" and r0["Material"]["refPath"] == MAT_OBJ, "%s %s" % (r0["Alignment"], r0["FacingMode"]))


def check_latch():
    em = "Splash"
    print("-- Splash latch and renderer 1")
    ms = setparams_module(em, PS, ["Particles.Landed", "Particles.RingSize", "Particles.SpriteFacing"])
    chk("latch spawn module present", ms is not None, str(ms))
    if ms:
        vals = {i["name"]: i["value"]["value"] for i in E().call(NS, "GetModuleInputValues", {"moduleRef": R(em, PS, ms)}, read=True)["inputs"]}
        chk("latch spawn Landed false, RingSize (30,30), SpriteFacing (0,0,1)", vals["Particles.Landed"]["value"] == 0 and (vals["Particles.RingSize"]["x"], vals["Particles.RingSize"]["y"]) == (30, 30)
            and (vals["Particles.SpriteFacing"]["x"], vals["Particles.SpriteFacing"]["y"], vals["Particles.SpriteFacing"]["z"]) == (0, 0, 1), str(vals))
    pu = module_names(em, PU)
    ml, mc = setparams_module(em, PU, ["Particles.Landed"]), setparams_module(em, PU, ["Particles.Color"])
    chk("latch update modules present", bool(ml and mc), "%s %s" % (ml, mc))
    if ml and mc:
        chk("latch order: Collision < Landed < Color", pu.index("Collision") < pu.index(ml) < pu.index(mc), str(pu))
        chk("latch Landed expression", lv(R(em, PU, ml, -1, ["Particles.Landed"])).get("hlslExpression") == "Particles.Landed || Particles.HasCollided")
        chk("latch Color expression", lv(R(em, PU, mc, -1, ["Particles.Color"])).get("hlslExpression") == "Particles.Landed ? float4(5.0, 1.4, 0.2, 1.0) : float4(0.0, 0.0, 0.0, 0.0)")
        chk("no other module after Color latch", pu[-1] == mc, str(pu))
    pv = json.loads(E().call(NS, "GetRendererData", {"rendererRef": R(em, "", "", 1)}, read=True)["propertyValues"])
    chk("renderer 1 custom facing", pv["FacingMode"] == "CustomFacingVector" and pv["Material"]["refPath"] == MAT_OBJ, pv["FacingMode"])
    chk("renderer 1 facing binding Particles.SpriteFacing", pv["SpriteFacingBinding"]["paramMapVariable"]["name"] == "Particles.SpriteFacing" and pv["SpriteFacingBinding"]["bBindingExistsOnSource"], pv["SpriteFacingBinding"]["bindingSourceMode"])
    chk("renderer 1 size binding Particles.RingSize", pv["SpriteSizeBinding"]["paramMapVariable"]["name"] == "Particles.RingSize" and pv["SpriteSizeBinding"]["bBindingExistsOnSource"], pv["SpriteSizeBinding"]["bindingSourceMode"])


def check_system():
    chk("system exists", bool(E().call(AS, "exists", {"path": SYS_PKG}, read=True)))
    ems = emitters()
    chk("emitters Rain and Splash only", sorted(ems) == ["Rain", "Splash"], str(ems))
    uv = {v["name"]: v for v in E().call(NS, "GetUserVariables", {"system": SYS}, read=True)["userVariables"]}
    for name, kind, val in USER_VARS:
        v = uv.get(name)
        got = None
        if v:
            d = v["defaultValue"]["value"]
            got = d["value"] if kind == "f" else (d["x"], d["y"], d["z"])
        chk("user var " + name, v is not None and close(got, val if kind == "f" else tuple(val)), str(got))
    for em, spec in EMITTERS.items():
        if em in ems:
            check_emitter(em, spec)
    if "Splash" in ems:
        check_latch()
    print("-- compile")
    cs = wait_compiled()
    chk("compile aggregate UpToDate", cs["aggregateStatus"] == "UpToDate" and not cs["bHasErrors"], cs["aggregateStatus"])
    for em in EMITTERS:
        sc = [s for s in cs["scripts"] if s["emitterName"] == em]
        gpu = [s for s in sc if "GPUCompute" in s["scriptName"]]
        chk(em + " GPU compute script compiled", len(gpu) == 1 and gpu[0]["lastCompileStatus"] == "UpToDate", str([s["lastCompileStatus"] for s in gpu]))
        chk(em + " all scripts UpToDate", bool(sc) and all(s["lastCompileStatus"] == "UpToDate" for s in sc), str([(s["scriptName"].split("::")[-1], s["lastCompileStatus"]) for s in sc]))
    iss = E().call(NS, "GetStackIssues", {"system": SYS}, read=True)
    chk("stack issues: no errors", iss["numErrors"] == 0, "errors=%d warnings=%d infos=%d" % (iss["numErrors"], iss["numWarnings"], iss["numInfos"]))
    for i in iss["issues"]:
        if i["severity"] == "Warning":
            print("WARN", i["location"]["emitterName"], i["shortDescription"], "|", i["longDescription"][:160])


def check_actors():
    print("-- actors")
    in_folder = [a["refPath"] for a in js(E().call(SC, "get_actors_in_folder", {"folder_path": OUTLINER, "recursive": False}, read=True))]
    for row in ROWS:
        label, loc = row[0], row[1]
        hit = find_actors(label, "editor")
        chk(label + " exactly one editor-world actor", len(hit) == 1, str(hit))
        if len(hit) != 1:
            continue
        rp = hit[0]
        chk(label + " in folder " + OUTLINER, rp in in_folder)
        xf = js(E().call(AC, "get_actor_transform", {"actor": ref(rp)}, read=True))
        l, r, s = xf["location"], xf["rotation"], xf["scale"]
        chk(label + " transform", all(abs(l[k] - v) < 0.01 for k, v in zip("xyz", loc)) and all(abs(r[k]) < 0.01 for k in ("pitch", "yaw", "roll")) and all(abs(s[k] - 1) < 1e-4 for k in "xyz"), "loc %s rot %s scale %s" % (l, r, s))
        comp = niagara_component(rp)
        for name, (kind, val) in row_values(row).items():
            got = getvar(comp, name, kind)
            chk(label + " " + name, close(got, val), "%s (want %s)" % (got, val))


def cmd_check(_a):
    E()
    print("== s1_spike check ==")
    check_material()
    check_system()
    check_actors()
    print("-- dirty state (INFO; dirty is expected, nothing may be saved)")
    for p in ["/Game/LastBell/Maps/L_Monastery", MAT_PKG, SYS_PKG]:
        print("INFO is_dirty", p, E().call(AS, "is_dirty", {"asset_path": p}, read=True))
    print("RESULT:", "FAIL (%d)" % _fail if _fail else "all PASS")
    return 1 if _fail else 0


# ---- set ----------------------------------------------------------------------------------------


def cmd_set(a):
    E()
    if a.world == "pie" and not pie_running():
        print("REFUSED: --world pie but PIE is not running (nothing was changed)")
        return 2
    if a.world == "editor" and pie_running():
        print("NOTE: PIE is running; --world editor still only touches editor-world actors")
    bad = 0
    for row in ROWS:
        label = row[0]
        hit = find_actors(label, a.world)
        if len(hit) != 1:
            print("REFUSED: %d %s-world actors labelled %s (need exactly 1)" % (len(hit), a.world, label))
            return 2
        rp = hit[0]
        if (a.world == "pie") != ("UEDPIE" in rp):
            print("REFUSED: world mismatch for", rp)
            return 2
        comp = niagara_component(rp)
        want = {}
        if a.off:
            want["User.RainRate"], want["User.SplashRate"] = ("f", 0.0), ("f", 0.0)
        else:
            if a.rain_scale is not None:
                want["User.RainRate"] = ("f", row[4] * a.rain_scale)
            if a.splash_scale is not None:
                want["User.SplashRate"] = ("f", row[5] * a.splash_scale)
        if a.splash_fall is not None:
            want["User.SplashFall"] = ("f", a.splash_fall)
        if a.radius is not None:
            want["User.RainRadius"] = ("f", a.radius)
        for name, (kind, val) in want.items():
            setvar(comp, name, kind, val)
        shown = []
        for name in ["User.RainRate", "User.SplashRate", "User.SplashFall", "User.RainRadius"]:
            got = getvar(comp, name, "f")
            shown.append("%s=%g" % (name[5:], got))
            if name in want and not close(got, want[name][1]):
                bad += 1
                print("MISMATCH", label, name, "wrote", want[name][1], "read", got)
        print("%-18s [%s] %s" % (label, a.world, "  ".join(shown)))
    print("SET", "FAILED (read-back mismatch)" if bad else "OK")
    return 1 if bad else 0


# ---- blockers (6.2; --apply is for the lead only) -----------------------------------------------


def plank_rows():
    """Plank rows from the F0 survey: {walk: {row: (x0, y0, x1, y1, lowest_z)}}. Row = the second index of Roof_<N|S>_Planks_<col>_<row>."""
    d = json.load(open(os.path.join(ROOT, "Docs", "ArtTest", "fx", "p15_f0.json"), encoding="utf-8"))
    rows = {}
    for p in d["roof_pieces"]:
        lab = p.get("label", "")
        if lab.startswith("Roof_") and "_Planks_" in lab:
            walk = lab.split("_")[1]
            row = lab.split("_")[-1]
            b = p["bounds"]
            x0, y0, z0 = b["min"]
            x1, y1, _ = b["max"]
            cur = rows.setdefault(walk, {}).get(row)
            rows[walk][row] = (x0, y0, x1, y1, z0) if cur is None else (min(cur[0], x0), min(cur[1], y0), max(cur[2], x1), max(cur[3], y1), min(cur[4], z0))
    return rows


def blocker_plan():
    plan = []
    for walk, rs in sorted(plank_rows().items()):
        for row, (x0, y0, x1, y1, z0) in sorted(rs.items()):
            top = z0 - 5.0
            plan.append(dict(label="S1_Block_%s%s" % (walk, row), loc=((x0 + x1) / 2, (y0 + y1) / 2, top - 20.0), scale=((x1 - x0) / 100.0, (y1 - y0) / 100.0, 0.4)))
    return plan


def cmd_blockers(a):
    plan = blocker_plan()
    for b in plan:
        print("%-14s loc (%.1f, %.1f, %.1f)  scale (%.3f, %.3f, %.2f)  [40 cm thick, top 5 cm under the row's lowest plank edge]" % (b["label"], *b["loc"], *b["scale"]))
    if a.dry_run:
        print("DRY RUN: nothing changed")
        return 0
    E()
    if a.apply:
        for b in plan:
            hit = find_actors(b["label"], "editor")
            xf = {"location": dict(zip("xyz", b["loc"])), "rotation": {"pitch": 0, "yaw": 0, "roll": 0}, "scale": dict(zip("xyz", b["scale"]))}
            rp = hit[0] if hit else E().call(SC, "add_to_scene_from_asset", {"asset_path": "/Engine/BasicShapes/Cube", "name": b["label"], "xform": xf})["refPath"]
            E().call(AC, "set_label", {"actor": ref(rp), "label": b["label"]})
            E().call(SC, "set_actor_folder", {"actor": ref(rp), "folder_path": OUTLINER})
            E().call(AC, "set_actor_transform", {"actor": ref(rp), "xform": xf, "worldspace": True})
            comp = [c["refPath"] for c in E().call(AC, "get_components", {"actor": ref(rp)}, read=True) if c["refPath"].endswith("StaticMeshComponent0")][0]
            vals = {"bRenderInMainPass": False, "bRenderInDepthPass": False, "bVisibleInRayTracing": False, "bAffectDistanceFieldLighting": True, "castShadow": False,
                    "bodyInstance": {"collisionProfileName": "NoCollision"}}
            E().call(OB, "set_properties", {"instance": ref(comp), "values": json.dumps(vals)})
            back = js(E().call(OB, "get_properties", {"instance": ref(comp), "properties": ["bRenderInMainPass", "bRenderInDepthPass", "bVisibleInRayTracing", "bAffectDistanceFieldLighting", "castShadow"]}, read=True))
            print("  placed", b["label"], back)
        return 0
    if a.remove:
        n = 0
        for b in plan:
            for rp in find_actors(b["label"], "editor"):
                E().call(SC, "remove_from_scene", {"actor": ref(rp)})
                n += 1
        print("removed", n, "blocker actors")
        return 0
    print("REFUSED: give --apply, --remove or --dry-run")
    return 2


# ---- remove (the lead runs it after the verdict) -------------------------------------------------


def cmd_remove(a):
    E()
    labels = LABELS + [b["label"] for b in blocker_plan()]
    actors = [(l, rp) for l in labels for rp in find_actors(l, "editor")]
    assets = [p for p in (MAT_PKG, SYS_PKG) if E().call(AS, "exists", {"path": p}, read=True)]
    print("would delete %d actors:" % len(actors))
    for l, rp in actors:
        print("   ", l, rp)
    print("would delete %d assets: %s (then the folder %s)" % (len(assets), assets, FOLDER))
    if a.dry_run:
        print("DRY RUN: nothing changed")
        return 0
    if not a.yes:
        print("REFUSED: pass --yes to delete (or --dry-run to list)")
        return 2
    if pie_running():
        print("REFUSED: PIE is running")
        return 2
    for l, rp in actors:
        print("  remove_from_scene", l, E().call(SC, "remove_from_scene", {"actor": ref(rp)}))
    for p in assets:
        print("  delete", p, E().call(AS, "delete", {"path": p}), "exists afterwards:", E().call(AS, "exists", {"path": p}, read=True))
    print("  delete folder", FOLDER, E().call(AS, "delete", {"path": FOLDER}))
    print("The map stays dirty and is not saved.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build").set_defaults(fn=cmd_build)
    sub.add_parser("place").set_defaults(fn=cmd_place)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    s = sub.add_parser("set")
    s.add_argument("--world", choices=["pie", "editor"], required=True)
    s.add_argument("--rain-scale", type=float)
    s.add_argument("--splash-scale", type=float)
    s.add_argument("--splash-fall", type=float)
    s.add_argument("--radius", type=float)
    s.add_argument("--off", action="store_true")
    s.set_defaults(fn=cmd_set)
    b = sub.add_parser("blockers")
    g = b.add_mutually_exclusive_group()
    g.add_argument("--apply", action="store_true")
    g.add_argument("--remove", action="store_true")
    b.add_argument("--dry-run", action="store_true")
    b.set_defaults(fn=cmd_blockers)
    r = sub.add_parser("remove")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--yes", action="store_true")
    r.set_defaults(fn=cmd_remove)
    a = ap.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
