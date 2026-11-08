"""P15-5: the seven Phase 15 Niagara systems, built over Unreal MCP. Spec: Docs/plans/P15_PARTICLES.md section 6.
Record: Docs/ArtTest/fx/p15_5_build.md. Method: Docs/ArtTest/fx/s1/s1_build.md (the S1 recipe).

Editor must be open (PIE off). The script creates the systems in /Game/LastBell/FX/Niagara/ and never touches an existing asset
(NS_LB_SmokeWisp is not listed here and is never read or written). Nothing is saved by `build`; `save` saves each new system, one package per call.
Python: C:\\Users\\heman\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe -I Tools/fx/p15_5_niagara.py <command>

    build [--only NAME,...]    build or REBUILD each system from scratch (removes all emitters and user variables first), then print the compile report
    check [--only NAME,...]    read everything back, print PASS/FAIL/WARN/INFO lines, exit 1 on any FAIL
    save  [--only NAME,...]    save each new system (one package per call, is_dirty checked after); refuses anything outside the 7 packages
    list                       the systems this script owns

Systems: NS_LB_Rain, NS_LB_StrikeSparks, NS_LB_TorchFire, NS_LB_ShaftDust, NS_LB_WaterMist, NS_LB_Drip, NS_LB_EaveDrips
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
NI = "NiagaraToolsets.NiagaraToolset_Info"
NC = "NiagaraToolsets.NiagaraToolset_Component"
AS = "editor_toolset.toolsets.asset.AssetTools"
OB = "editor_toolset.toolsets.object.ObjectTools"
EA = "EditorToolset.EditorAppToolset"

FOLDER = "/Game/LastBell/FX/Niagara"
MI_DIR = "/Game/LastBell/Materials/Instances/FX/"
TEMPLATE_SYSTEM = "/Niagara/DefaultAssets/DefaultSystem.DefaultSystem"
TEMPLATE_EMITTER = "/Niagara/DefaultAssets/Templates/Emitters/Fountain.Fountain"
MOD = "/Niagara/Modules/"
M_COLLISION = MOD + "Collision/Collision.Collision"
M_BURST = MOD + "Emitter/SpawnBurst_Instantaneous.SpawnBurst_Instantaneous"
M_CURL = MOD + "Update/Forces/V2/CurlNoiseForce.CurlNoiseForce"
M_GRAVITY = MOD + "Update/Forces/GravityForce.GravityForce"
M_DRAG = MOD + "Update/Forces/Drag.Drag"
DI_RANGE_F = "/Niagara/DynamicInputs/UniformRange/V2/RandomRangeFloat.RandomRangeFloat"
DI_RANGE_V = "/Niagara/DynamicInputs/UniformRange/V2/RandomRangeVector.RandomRangeVector"
SPRITE_RENDERER = "/Script/Niagara.NiagaraSpriteRendererProperties"
LIGHT_RENDERER = "/Script/Niagara.NiagaraLightRendererProperties"

FLOAT = "/Script/Niagara.NiagaraFloat"
BOOL = "/Script/Niagara.NiagaraBool"
INT = "/Script/Niagara.NiagaraInt32"
POS = "/Script/Niagara.NiagaraPosition"
V3 = "/Script/CoreUObject.Vector3f"
V2 = "/Script/CoreUObject.Vector2f"
LCOL = "/Script/CoreUObject.LinearColor"
LINKED_S = "/Script/NiagaraEditor.NiagaraExt_StackInputData_Linked"
HLSL_S = "/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression"
ENUM_S = "/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum"
DYN_S = "/Script/NiagaraEditor.NiagaraExt_StackInputData_DynamicInput"

EP, EU, PS, PU = "EmitterSpawnScript", "EmitterUpdateScript", "ParticleSpawnScript", "ParticleUpdateScript"
SU = "SystemUpdateScript"

# ---- plumbing -------------------------------------------------------------------------------------


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


_ed = None


def E():
    global _ed
    if _ed is None:
        _ed = Ed()
    return _ed


def js(r):
    if isinstance(r, (dict, list, bool, int, float)) or r is None:
        return r
    try:
        return json.loads(r)
    except (TypeError, ValueError):
        return r


def ref(p):
    return {"refPath": p}


def T(p):
    return {"classStructOrEnum": {"refPath": p}}


def lit(struct, value):
    return {"struct": {"refPath": struct}, "value": value}


def fl(v):
    return lit(FLOAT, {"value": v})


def bl(v):
    return lit(BOOL, {"value": -1 if v else 0})


def it(v):
    return lit(INT, {"value": v})


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


def dyn(asset):
    return {"struct": {"refPath": DYN_S}, "value": {"dynamicInputAsset": ref(asset)}}


FAILS = []


def step(label, fn, quiet=False):
    """Run one MCP step, print OK/ERR, remember failures."""
    try:
        r = fn()
        if not quiet:
            shown = json.dumps(r.get("value") if isinstance(r, dict) and "value" in r else r)
            print("  OK  ", label, (shown or "")[:100])
        return r
    except Exception as e:  # noqa: BLE001
        print("  ERR ", label, "|", str(e)[:400])
        FAILS.append(label)
        return None


# ---- one Niagara system ---------------------------------------------------------------------------


class Sys:
    def __init__(self, name):
        self.name = name
        self.pkg = FOLDER + "/" + name
        self.obj = self.pkg + "." + name
        self.sys = ref(self.obj)
        self._enum_cache = {}

    # stack references
    def R(self, em="", script="", module="", rend=-1, inputs=()):
        return {"system": self.sys, "emitterName": em, "scriptName": script, "moduleName": module, "rendererIndex": rend, "inputNameStack": list(inputs)}

    def call(self, tool, args, read=False):
        return E().call(NS, tool, args, read=read)

    # inputs
    def setin(self, rf, data):
        return self.call("SetStackInputData", {"stackInputRef": rf, "inputData": data})

    def getin(self, rf):
        return self.call("GetStackInputData", {"stackInputRef": rf}, read=True)

    def inp(self, em, script, module, name, data, label=None):
        """Set one module input; prints OK/ERR."""
        return step("%s %s.%s = %s" % (em, module, name, label or _short(data)), lambda: self.setin(self.R(em, script, module, -1, [name]), data), quiet=True)

    def child(self, em, script, module, name, sub, data):
        """Set an input of a dynamic input sitting on module input `name`."""
        return step("%s %s.%s.%s" % (em, module, name, sub), lambda: self.setin(self.R(em, script, module, -1, [name, sub]), data), quiet=True)

    def enum(self, em, script, module, name, display):
        """Set a static-switch enum input by display name (looked up with UEnum_Info)."""
        def go():
            tp = self.call("GetStackInputTopology", {"stackInputRef": self.R(em, script, module, -1, [name])}, read=True)
            epath = tp["type"]["classStructOrEnum"]["refPath"]
            if epath not in self._enum_cache:
                self._enum_cache[epath] = js(E().call(NI, "UEnum_Info", {"enum": ref(epath)}, read=True))
            info = self._enum_cache[epath]
            hit = [v for v in info["Values"] if v["DisplayName"].lower().startswith(display.lower())]
            if len(hit) != 1:
                raise RuntimeError("enum %s: '%s' matches %s" % (epath, display, [v["DisplayName"] for v in info["Values"]]))
            payload = {"struct": {"refPath": ENUM_S}, "value": {"enum": ref(epath), "enumName": info["Name"] + "::" + hit[0]["Name"], "displayName": hit[0]["DisplayName"]}}
            self.setin(self.R(em, script, module, -1, [name]), payload)
            back = self.getin(self.R(em, script, module, -1, [name]))
            if back["value"]["displayName"] != hit[0]["DisplayName"]:
                raise RuntimeError("read back %s" % back["value"]["displayName"])
            return hit[0]["DisplayName"]
        return step("%s %s.%s = %s" % (em, module, name, display), go, quiet=True)

    # structure
    def emitters(self):
        return [e["emitterName"] for e in self.call("GetSystemSummary", {"system": self.sys}, read=True)["emitters"]]

    def modules(self, em, script):
        return self.call("GetScriptStackTopology", {"scriptRef": self.R(em, script)}, read=True)["modules"]

    def module_names(self, em, script):
        return [m["moduleName"] for m in self.modules(em, script)]

    def add_module(self, em, script, asset):
        r = self.call("AddModule", {"moduleLocationRef": self.R(em, script), "moduleAsset": ref(asset)})
        print("  OK   %s %s += %s" % (em, script, r["moduleName"]))
        return r["moduleName"]

    def remove_module(self, em, script, name):
        if name in self.module_names(em, script):
            step("%s remove %s" % (em, name), lambda: self.call("RemoveModule", {"moduleToRemove": self.R(em, script, name)}), quiet=True)

    def set_params(self, em, script, entries, label=""):
        """One SetParameters module. entries: [(name, type, default literal, HLSL expression or ready payload)]. Returns the module name."""
        params = [{"variable": {"name": n, "type": T(t)}, "defaultValue": d} for n, t, d, _ in entries]
        mn = self.call("AddSetParametersModule", {"moduleLocationRef": self.R(em, script), "parameters": params})["moduleName"]
        print("  OK   %s %s += %s %s" % (em, script, mn, [n for n, _, _, _ in entries] if not label else label))
        for n, _, _, expr in entries:
            data = hlsl(expr) if isinstance(expr, str) else expr
            step("%s %s.%s" % (em, mn, n), lambda n=n, data=data: self.setin(self.R(em, script, mn, -1, [n]), data), quiet=True)
        return mn

    def emitter_data(self, em, vals):
        return step(em + ": SetEmitterData " + json.dumps(vals)[:60], lambda: self.call("SetEmitterData", {"emitter": self.R(em), "emitterData": {"propertyValues": json.dumps(vals)}}), quiet=True)

    def renderer_get(self, em, idx):
        return json.loads(self.call("GetRendererData", {"rendererRef": self.R(em, "", "", idx)}, read=True)["propertyValues"])

    def renderer_set(self, em, idx, vals, label=""):
        return step("%s renderer %d %s" % (em, idx, label), lambda: self.call("SetRendererData", {"renderer": self.R(em, "", "", idx), "rendererData": {"propertyValues": json.dumps(vals)}}), quiet=True)

    def add_renderer(self, em, cls=SPRITE_RENDERER):
        r = self.call("AddRenderer", {"newRendererLocation": self.R(em), "rendererClass": ref(cls)})
        print("  OK   %s renderer += %s index %s" % (em, cls.split(".")[-1], r["rendererIndex"]))
        return r["rendererIndex"]

    def binding(self, em, idx, key, attr, mode="ExplicitParticles"):
        """A copy of renderer binding `key` re-pointed at Particles.<attr> (the S1 payload: only names and the source mode change)."""
        pv = self.renderer_get(em, idx)
        b = copy.deepcopy(pv[key])
        b.update({"rootName": attr, "dataSetName": attr, "cachedDisplayName": "Particles." + attr, "bindingSourceMode": mode})
        b["paramMapVariable"]["name"] = "Particles." + attr
        return b

    # compile
    def compile_state(self):
        return self.call("GetSystemCompileState", {"system": self.sys}, read=True)

    def issues(self):
        return self.call("GetStackIssues", {"system": self.sys}, read=True)

    def fix_collision_order(self, em):
        """Collision must run before SolveForcesAndVelocity: apply the engine's own fix, then verify by topology."""
        mods = self.module_names(em, PU)
        if mods.index("Collision") < mods.index("SolveForcesAndVelocity"):
            return
        self.compile_state()
        iss = self.issues()
        for i in iss["issues"]:
            if i["severity"] == "Error" and i["location"]["emitterName"] == em and i["location"]["moduleName"] == "Collision":
                for f in i["fixes"]:
                    if f["style"] == "Fix":
                        try:
                            self.call("ApplyStackIssueFix", {"system": self.sys, "issueId": i["issueId"], "fixId": f["fixId"]})
                        except RuntimeError as e:  # the fix applies, but the call can still raise 'compile in flight' / unknown issue id
                            print("  INFO ApplyStackIssueFix raised (checked by topology next):", str(e)[:80])
        mods = self.module_names(em, PU)
        ok = mods.index("Collision") < mods.index("SolveForcesAndVelocity")
        print("  %s %s: Collision before SolveForcesAndVelocity: %s" % ("OK  " if ok else "ERR ", em, mods))
        if not ok:
            FAILS.append(em + ": module order")


def _short(d):
    try:
        v = d["value"]
        if "hlslExpression" in v:
            return "HLSL " + v["hlslExpression"]
        if "linkedVariable" in v:
            return "link " + v["linkedVariable"]["name"]
        if "dynamicInputAsset" in v:
            return "DI " + v["dynamicInputAsset"]["refPath"].split("/")[-1].split(".")[0]
        return json.dumps(v)
    except Exception:  # noqa: BLE001
        return str(d)[:60]


# ---- shared builders ------------------------------------------------------------------------------
def FIXED(lo, hi):
    return {"min": dict(zip("xyz", lo)), "max": dict(zip("xyz", hi)), "isValid": True}


def user_var(name, kind, val):
    if kind == "f":
        return {"name": name, "type": T(FLOAT), "defaultValue": fl(float(val))}
    if kind == "b":
        return {"name": name, "type": T(BOOL), "defaultValue": bl(bool(val))}
    if kind == "v3":
        return {"name": name, "type": T(V3), "defaultValue": v3(*[float(x) for x in val])}
    if kind == "v2":
        return {"name": name, "type": T(V2), "defaultValue": v2(*[float(x) for x in val])}
    raise ValueError(kind)


def make_system(S, uvars):
    """Create the system (from DefaultSystem, Fountain removed) or reset an existing one (all emitters and user variables removed)."""
    print("[system]", S.pkg)
    if not E().call(AS, "exists", {"path": S.pkg}, read=True):
        step("CreateNiagaraSystem", lambda: E().call(NS, "CreateNiagaraSystem", {"assetName": S.name, "assetPath": FOLDER, "templateSystem": ref(TEMPLATE_SYSTEM)}))
        if "Fountain" in S.emitters():
            step("RemoveEmitter Fountain", lambda: S.call("RemoveEmitter", {"emitterToRemove": S.R("Fountain")}), quiet=True)
    for em in S.emitters():
        step("RemoveEmitter " + em, lambda em=em: S.call("RemoveEmitter", {"emitterToRemove": S.R(em)}), quiet=True)
    old = S.call("GetUserVariables", {"system": S.sys}, read=True)
    olds = old.get("userVariables", old) if isinstance(old, dict) else old
    if olds:
        rem = [{"name": v["name"], "type": v["type"]} for v in olds]
        step("RemoveUserVariables (%d)" % len(rem), lambda: S.call("RemoveUserVariables", {"system": S.sys, "variablesToRemove": rem}), quiet=True)
    step("AddUserVariables (%d)" % len(uvars), lambda: S.call("AddUserVariables", {"system": S.sys, "variablesToAdd": [user_var(*v) for v in uvars]}), quiet=True)


def add_emitter(S, em, sim, bounds=None, local=False, keep=()):
    """Fountain template emitter; strips GravityForce / Drag / ScaleColor except those in `keep`."""
    step("AddEmitter " + em, lambda: S.call("AddEmitter", {"system": S.sys, "templateEmitter": ref(TEMPLATE_EMITTER), "emitterName": em}), quiet=True)
    vals = {"SimTarget": sim, "bLocalSpace": local, "bDeterminism": False}
    if bounds:
        vals.update({"CalculateBoundsMode": "Fixed", "FixedBounds": FIXED(*bounds)})
    S.emitter_data(em, vals)
    for mn in ("GravityForce", "Drag", "ScaleColor"):
        if mn not in keep:
            S.remove_module(em, PU, mn)


def init_particle(S, em, life, color, size, rotation=None):
    """InitializeParticle. life: float or (min, max). color: (r,g,b,a). size: ('u', s) | ('ru', lo, hi) | ('nu', (x, y)) | ('rnu', (x0, y0), (x1, y1))."""
    m = "InitializeParticle"
    if isinstance(life, tuple):
        S.enum(em, PS, m, "Lifetime Mode", "Random")
        S.inp(em, PS, m, "Lifetime Min", fl(life[0]))
        S.inp(em, PS, m, "Lifetime Max", fl(life[1]))
    else:
        S.enum(em, PS, m, "Lifetime Mode", "Direct Set")
        S.inp(em, PS, m, "Lifetime", fl(life))
    S.enum(em, PS, m, "Color Mode", "Direct Set")
    S.inp(em, PS, m, "Color", col(*color))
    kind = size[0]
    if kind == "u":
        S.enum(em, PS, m, "Sprite Size Mode", "Uniform")
        S.inp(em, PS, m, "Uniform Sprite Size", fl(size[1]))
    elif kind == "ru":
        S.enum(em, PS, m, "Sprite Size Mode", "Random Uniform")
        S.inp(em, PS, m, "Uniform Sprite Size Min", fl(size[1]))
        S.inp(em, PS, m, "Uniform Sprite Size Max", fl(size[2]))
    elif kind == "nu":
        S.enum(em, PS, m, "Sprite Size Mode", "Non-Uniform")
        S.inp(em, PS, m, "Sprite Size", v2(*size[1]))
    elif kind == "rnu":
        S.enum(em, PS, m, "Sprite Size Mode", "Random Non-Uniform")
        S.inp(em, PS, m, "Sprite Size Min", v2(*size[1]))
        S.inp(em, PS, m, "Sprite Size Max", v2(*size[2]))
    if rotation:
        S.enum(em, PS, m, "Sprite Rotation Mode", rotation)


def spawn_rate(S, em, expr_or_link):
    data = linked(expr_or_link, FLOAT) if expr_or_link.startswith("User.") and " " not in expr_or_link else hlsl(expr_or_link)
    S.inp(em, EU, "SpawnRate", "SpawnRate", data)


def shape_box(S, em, size_expr, offset_expr):
    S.enum(em, PS, "ShapeLocation", "Shape Primitive", "Box")
    S.inp(em, PS, "ShapeLocation", "Box Size", hlsl(size_expr))
    S.enum(em, PS, "ShapeLocation", "Offset Mode", "Default")
    S.inp(em, PS, "ShapeLocation", "Offset", hlsl(offset_expr) if isinstance(offset_expr, str) else offset_expr)


def velocity_random_vec(S, em, mn_expr, mx_expr, inp="Velocity", module="AddVelocity"):
    """Input = RandomRangeVector dynamic input with HLSL Minimum / Maximum."""
    S.inp(em, PS, module, inp, dyn(DI_RANGE_V), label="DI RandomRangeVector")
    S.child(em, PS, module, inp, "Minimum", hlsl(mn_expr))
    S.child(em, PS, module, inp, "Maximum", hlsl(mx_expr))


def gpu_collision(S, em, kill, radius_data, rest=False):
    """Collision module, GPU Distance Fields (static switch on the PLACED module), kill, custom radius."""
    if "Collision" not in S.module_names(em, PU):
        S.add_module(em, PU, M_COLLISION)
    S.enum(em, PU, "Collision", "GPU Collision Type", "GPU Distance")
    S.inp(em, PU, "Collision", "Collision Enabled", bl(True))
    S.inp(em, PU, "Collision", "KillOnCollision", bl(kill))
    S.enum(em, PU, "Collision", "Radius Calculation Type", "Custom")
    S.inp(em, PU, "Collision", "Particle Radius", radius_data)
    if rest:
        S.inp(em, PU, "Collision", "Restitution", fl(0.0))
        S.inp(em, PU, "Collision", "Friction", fl(1.0))
        S.inp(em, PU, "Collision", "Enable Rest State", bl(True))
    S.fix_collision_order(em)


# ---- NS_LB_Rain -----------------------------------------------------------------------------------
RAIN_UVARS = [("User.RainRate", "f", 35000), ("User.BoxHalf", "f", 1800), ("User.SpawnHeight", "f", 2500), ("User.FallMin", "f", 1100),
              ("User.FallMax", "f", 1400), ("User.Wind", "v3", (0, 0, 0)), ("User.SplashRate", "f", 2500), ("User.SplashRadius", "f", 1200),
              ("User.Mist", "f", 0)]
RAIN_BOUNDS = ((-4000, -4000, -1000), (4000, 4000, 3000))   # relative to the owner (system) position
RAIN_RADIUS = 20.0
SPLASH_COLLISION_RADIUS = 6.0
LAND_LIFE = 0.45
RING_FROM, RING_TO = 4.0, 22.0
RING_ALPHA = 0.6
ALIVE_RAIN = "DataInstance.Alive && Particles.Position.z > Engine.Owner.Position.z - 800.0"
# 6 of the chain: the pin chain's own rule (die 0.45 s after landing), plus the engine lifetime and a floor kill so a splash that finds no surface cannot fall for ever
ALIVE_SPLASH = "Particles.LandAge <= %g && Particles.Age < Particles.Lifetime && Particles.Position.z > Engine.Owner.Position.z - 800.0" % LAND_LIFE
# the S1 round 2 pin chain (plan 6.1): one SetParameters module per row, appended after Collision and SolveForcesAndVelocity, in this order.
# Row entries: (parameter, type, literal default, expression)
SPLASH_CHAIN = [
    [("Particles.LandPos", POS, v3(0, 0, 0), "Particles.Landed ? Particles.LandPos : Particles.Position")],                       # 1
    [("Particles.Landed", BOOL, bl(False), "Particles.Landed || Particles.HasCollided")],                                         # 2
    [("Particles.Position", POS, v3(0, 0, 0), "Particles.Landed ? Particles.LandPos : Particles.Position"),                       # 3
     ("Particles.Velocity", V3, v3(0, 0, 0), "Particles.Landed ? float3(0, 0, 0) : Particles.Velocity")],
    [("Particles.LandAge", FLOAT, fl(0), "Particles.Landed ? Particles.LandAge + Engine.DeltaTime : 0.0")],                       # 4
    [("Particles.Color", LCOL, col(0, 0, 0, 0), "Particles.Landed ? float4(1.0, 1.0, 1.0, 1.0) : float4(0.0, 0.0, 0.0, 0.0)"),   # 5 colour and alpha (0 until landed); crown and ring have their own attributes
     ("Particles.RingColor", LCOL, col(0, 0, 0, 0),
      "Particles.Landed ? float4(1.0, 1.0, 1.0, %g * (1.0 - saturate(Particles.LandAge / %g))) : float4(0.0, 0.0, 0.0, 0.0)" % (RING_ALPHA, LAND_LIFE)),
     ("Particles.RingSize", V2, v2(RING_FROM, RING_FROM), "float2(1.0, 1.0) * lerp(%g, %g, saturate(Particles.LandAge / %g))" % (RING_FROM, RING_TO, LAND_LIFE)),
     ("Particles.SubImageIndex", FLOAT, fl(0), "min(15.0, floor(Particles.LandAge / %g * 16.0))" % LAND_LIFE)],
    [("DataInstance.Alive", BOOL, bl(True), ALIVE_SPLASH)],                                                                       # 6
]


def build_rain():
    S = Sys("NS_LB_Rain")
    make_system(S, RAIN_UVARS)

    # --- Rain: GPU, fixed bounds
    em = "Rain"
    print("[emitter] Rain")
    add_emitter(S, em, "GPUComputeSim", RAIN_BOUNDS)
    spawn_rate(S, em, "User.RainRate")
    init_particle(S, em, 3.5, (1, 1, 1, 0.7), ("rnu", (0.7, 28.0), (0.7, 42.0)))
    shape_box(S, em, "float3(User.BoxHalf * 2.0, User.BoxHalf * 2.0, 400.0)", "float3(0.0, 0.0, User.SpawnHeight)")
    S.enum(em, PS, "AddVelocity", "Velocity Mode", "Linear")
    velocity_random_vec(S, em, "float3(User.Wind.x, User.Wind.y, User.Wind.z - User.FallMax)", "float3(User.Wind.x, User.Wind.y, User.Wind.z - User.FallMin)")
    gpu_collision(S, em, True, fl(RAIN_RADIUS))
    S.set_params(em, PU, [("DataInstance.Alive", BOOL, bl(True), ALIVE_RAIN)], label="(kill below owner Z - 800)")
    S.renderer_set(em, 0, {"Material": ref(MI_DIR + "MI_LB_Rain.MI_LB_Rain"), "Alignment": "VelocityAligned", "FacingMode": "FaceCamera"}, "MI_LB_Rain")

    # --- Splash: GPU, fixed bounds; falls at rain speed, pinned at first contact (S1 round 2 chain)
    em = "Splash"
    print("[emitter] Splash")
    add_emitter(S, em, "GPUComputeSim", RAIN_BOUNDS)
    spawn_rate(S, em, "User.SplashRate")
    init_particle(S, em, 5.0, (0, 0, 0, 0), ("ru", 6.0, 10.0))
    S.enum(em, PS, "ShapeLocation", "Shape Primitive", "Cylinder")
    S.inp(em, PS, "ShapeLocation", "Cylinder Height", fl(1.0))
    S.inp(em, PS, "ShapeLocation", "Cylinder Radius", linked("User.SplashRadius", FLOAT))
    S.enum(em, PS, "ShapeLocation", "Offset Mode", "Default")
    S.inp(em, PS, "ShapeLocation", "Offset", hlsl("float3(0.0, 0.0, User.SpawnHeight)"))
    S.enum(em, PS, "AddVelocity", "Velocity Mode", "Linear")
    velocity_random_vec(S, em, "float3(0.0, 0.0, -User.FallMax)", "float3(0.0, 0.0, -User.FallMin)")
    S.set_params(em, PS, [("Particles.Landed", BOOL, bl(False), bl(False)), ("Particles.RingSize", V2, v2(RING_FROM, RING_FROM), v2(RING_FROM, RING_FROM)),
                          ("Particles.RingColor", LCOL, col(0, 0, 0, 0), col(0, 0, 0, 0)), ("Particles.SpriteFacing", V3, v3(0, 0, 1), v3(0, 0, 1))],
                 label="(spawn: Landed, RingSize, RingColor, SpriteFacing)")
    S.set_params(em, PS, [("Particles.LandPos", POS, v3(0, 0, 0), "Particles.Position"), ("Particles.LandAge", FLOAT, fl(0), fl(0.0))],
                 label="(spawn: LandPos = Position, LandAge = 0)")
    gpu_collision(S, em, False, fl(SPLASH_COLLISION_RADIUS), rest=True)
    for row in SPLASH_CHAIN:
        S.set_params(em, PU, row)
    S.renderer_set(em, 0, {"Material": ref(MI_DIR + "MI_LB_Splash.MI_LB_Splash"), "Alignment": "Unaligned", "FacingMode": "FaceCamera",
                           "SubImageSize": {"x": 4, "y": 4}, "bSubImageBlend": False,
                           "SubImageIndexBinding": S.binding(em, 0, "SubImageIndexBinding", "SubImageIndex")}, "crown MI_LB_Splash SubUV 4x4")
    idx = S.add_renderer(em)
    S.renderer_set(em, idx, {"Material": ref(MI_DIR + "MI_LB_Ripple.MI_LB_Ripple"), "Alignment": "Unaligned", "FacingMode": "CustomFacingVector",
                             "SpriteFacingBinding": S.binding(em, idx, "SpriteFacingBinding", "SpriteFacing"),
                             "SpriteSizeBinding": S.binding(em, idx, "SpriteSizeBinding", "RingSize"),
                             "ColorBinding": S.binding(em, idx, "ColorBinding", "RingColor")}, "ring MI_LB_Ripple (RingSize, RingColor, SpriteFacing)")

    # --- GroundMist: CPU
    em = "GroundMist"
    print("[emitter] GroundMist")
    add_emitter(S, em, "CPUSim")
    spawn_rate(S, em, "5.0 * User.Mist")
    init_particle(S, em, 6.0, (1, 1, 1, 1), ("ru", 250.0, 450.0), rotation="Random")
    S.enum(em, PS, "ShapeLocation", "Shape Primitive", "Ring")
    S.inp(em, PS, "ShapeLocation", "Ring Radius", fl(2200.0))
    S.inp(em, PS, "ShapeLocation", "Disc Coverage", fl(round(1.0 - 600.0 / 2200.0, 6)))
    S.enum(em, PS, "ShapeLocation", "Offset Mode", "Default")
    S.inp(em, PS, "ShapeLocation", "Offset", dyn(DI_RANGE_V), label="DI RandomRangeVector")
    S.child(em, PS, "ShapeLocation", "Offset", "Minimum", v3(0, 0, -160))
    S.child(em, PS, "ShapeLocation", "Offset", "Maximum", v3(0, 0, -80))
    S.enum(em, PS, "AddVelocity", "Velocity Mode", "Linear")
    S.inp(em, PS, "AddVelocity", "Velocity", hlsl("User.Wind * 0.15"))
    S.set_params(em, PU, [("Particles.Color", LCOL, col(1, 1, 1, 0), "float4(1.0, 1.0, 1.0, sin(3.14159265 * saturate(Particles.NormalizedAge)))")], label="(alpha 0 -> 1 -> 0)")
    S.renderer_set(em, 0, {"Material": ref(MI_DIR + "MI_LB_Mist.MI_LB_Mist"), "Alignment": "Unaligned", "FacingMode": "FaceCamera"}, "MI_LB_Mist")
    return S


# ---- shared helpers for the smaller systems --------------------------------------------------------
def di_float(S, em, script, module, inp, mn, mx):
    """Input = RandomRangeFloat dynamic input; mn / mx are floats or HLSL strings."""
    S.inp(em, script, module, inp, dyn(DI_RANGE_F), label="DI RandomRangeFloat")
    for sub, v in (("Minimum", mn), ("Maximum", mx)):
        S.child(em, script, module, inp, sub, hlsl(v) if isinstance(v, str) else fl(v))


def velocity_linear(S, em, data):
    S.enum(em, PS, "AddVelocity", "Velocity Mode", "Linear")
    S.inp(em, PS, "AddVelocity", "Velocity", hlsl(data) if isinstance(data, str) else data)


def curl(S, em, strength, freq=None):
    mn = S.add_module(em, PU, M_CURL)
    S.inp(em, PU, mn, "Noise Strength", fl(strength))
    if freq:
        S.inp(em, PU, mn, "Noise Frequency", fl(freq))
    return mn


def gravity(S, em, g=-980.0):
    mn = S.add_module(em, PU, M_GRAVITY)
    S.inp(em, PU, mn, "Gravity", v3(0, 0, g))
    return mn


def late_modules(S, em):
    mods = S.module_names(em, PU)
    if "SolveForcesAndVelocity" not in mods:
        return []
    return [m for m in mods[mods.index("SolveForcesAndVelocity") + 1:] if not m.startswith("SetVariables_")]


def move_solve_last(S, em):
    """Forces (Gravity, Curl, Drag) added by AddModule land after SolveForcesAndVelocity and the engine flags it: apply its own Fix until the order is right."""
    for _ in range(6):
        late = late_modules(S, em)
        if not late:
            break
        S.compile_state()
        iss = S.issues()
        fixed = False
        for i in iss["issues"]:
            if i["severity"] == "Error" and i["location"]["emitterName"] == em and i["location"]["moduleName"] in late:
                for f in i["fixes"]:
                    if f["style"] == "Fix":
                        try:
                            S.call("ApplyStackIssueFix", {"system": S.sys, "issueId": i["issueId"], "fixId": f["fixId"]})
                        except RuntimeError as e:  # the fix applies, the call can still raise 'compile in flight' / unknown issue id
                            print("  INFO ApplyStackIssueFix raised (checked by topology next):", str(e)[:70])
                        fixed = True
                        break
                if fixed:
                    break
        if not fixed:
            break
    late = late_modules(S, em)
    print("  %s %s: forces before SolveForcesAndVelocity: %s" % ("OK  " if not late else "ERR ", em, S.module_names(em, PU)))
    if late:
        FAILS.append(em + ": module order " + str(late))


def emitter_state(S, em, behavior=None, duration=None, inactive=None, recalc=None, delay=None):
    m = "EmitterState"
    if behavior:
        S.enum(em, EU, m, "Loop Behavior", behavior)
    if inactive:
        S.enum(em, EU, m, "Inactive Response", inactive)
    if duration is not None:
        if isinstance(duration, tuple):
            di_float(S, em, EU, m, "Loop Duration", duration[0], duration[1])
        else:
            S.inp(em, EU, m, "Loop Duration", fl(duration))
    if recalc is not None:
        S.inp(em, EU, m, "Recalculate Duration Each Loop", bl(recalc))
    if delay is not None:
        S.inp(em, EU, m, "UseLoopDelay", bl(True))
        S.inp(em, EU, m, "Delay First Loop Only", bl(True))
        di_float(S, em, EU, m, "Loop Delay", delay[0], delay[1])


# ---- NS_LB_StrikeSparks ----------------------------------------------------------------------------
SPARKS_UVARS = []
SPARK_COUNT = 70
SPARK_LIGHT_EVERY = 20       # every 20th Particles.UniqueID (float math: integer modulo is not allowed in the ES2 VVM shader) -> 5 % of the sparks carry the light (4 of 70)
SPARK_LIGHT_RADIUS = 400.0
SPARK_LIGHT_COLOR = (20.0, 15.0, 9.0)   # intensity x 20


def build_sparks():
    S = Sys("NS_LB_StrikeSparks")
    make_system(S, SPARKS_UVARS)
    # system: one loop of 1.5 s, then complete (the C++ spawns it with bAutoDestroy = true)
    S.enum("", SU, "SystemState", "Loop Behavior", "Once")
    S.inp("", SU, "SystemState", "Loop Duration", fl(1.5))
    S.enum("", SU, "SystemState", "Inactive Response", "Complete")
    em = "Sparks"
    print("[emitter] Sparks")
    add_emitter(S, em, "CPUSim", keep=("GravityForce",))
    S.remove_module(em, EU, "SpawnRate")
    mb = S.add_module(em, EU, M_BURST)
    S.inp(em, EU, mb, "Spawn Count", it(SPARK_COUNT))
    S.inp(em, EU, mb, "Spawn Time", fl(0.0))
    emitter_state(S, em, behavior="Once", duration=0.25, inactive="Complete")
    init_particle(S, em, (0.4, 0.9), (6.0, 5.4, 4.2, 1.0), ("rnu", (1.0, 4.0), (2.5, 10.0)))
    S.enum(em, PS, "ShapeLocation", "Shape Primitive", "Sphere")
    S.inp(em, PS, "ShapeLocation", "Sphere Radius", fl(1.0))
    S.enum(em, PS, "AddVelocity", "Velocity Mode", "From Point")
    di_float(S, em, PS, "AddVelocity", "Velocity Speed", 400.0, 900.0)
    S.set_params(em, PS, [("Particles.LightEnabled", BOOL, bl(False), "(float(Particles.UniqueID) - %g * floor((float(Particles.UniqueID) + 0.5) / %g)) < 0.5" % (SPARK_LIGHT_EVERY, SPARK_LIGHT_EVERY)),
                          ("Particles.LightRadius", FLOAT, fl(SPARK_LIGHT_RADIUS), fl(SPARK_LIGHT_RADIUS))], label="(light on 1 in %d sparks)" % SPARK_LIGHT_EVERY)
    S.inp(em, PU, "GravityForce", "Gravity", v3(0, 0, -980.0))
    move_solve_last(S, em)
    S.set_params(em, PU, [("Particles.Color", LCOL, col(6, 5.4, 4.2, 1), "float4(6.0, 5.4, 4.2, 1.0 - saturate(Particles.NormalizedAge))"),
                          ("Particles.LightColor", LCOL, col(0, 0, 0, 1),
                           "float4(%g, %g, %g, 1.0) * (1.0 - saturate(Particles.NormalizedAge))" % SPARK_LIGHT_COLOR)], label="(fade, light colour x20)")
    S.renderer_set(em, 0, {"Material": ref(MI_DIR + "MI_Flame_Torch.MI_Flame_Torch"), "Alignment": "VelocityAligned", "FacingMode": "FaceCamera"}, "MI_Flame_Torch")
    li = S.add_renderer(em, LIGHT_RENDERER)
    S.renderer_set(em, li, {"bUseInverseSquaredFalloff": False, "bAffectsTranslucency": False, "RadiusScale": 1.0,
                            "LightRenderingEnabledBinding": S.binding(em, li, "LightRenderingEnabledBinding", "LightEnabled"),
                            "RadiusBinding": S.binding(em, li, "RadiusBinding", "LightRadius"),
                            "ColorBinding": S.binding(em, li, "ColorBinding", "LightColor")}, "light renderer (LightEnabled, LightRadius, LightColor)")
    return S


# ---- NS_LB_TorchFire -------------------------------------------------------------------------------
TORCH_UVARS = [("User.Scale", "f", 1.0), ("User.Wind", "v3", (0, 0, 0))]


def build_torch():
    S = Sys("NS_LB_TorchFire")
    make_system(S, TORCH_UVARS)

    em = "Flames"
    print("[emitter] Flames")
    add_emitter(S, em, "CPUSim")
    spawn_rate(S, em, "14.0 * User.Scale")
    init_particle(S, em, (0.5, 0.8), (1, 1, 1, 1), ("ru", 18.0, 30.0))
    S.enum(em, PS, "ShapeLocation", "Shape Primitive", "Sphere")
    S.inp(em, PS, "ShapeLocation", "Sphere Radius", hlsl("4.0 * User.Scale"))
    velocity_linear(S, em, v3(0, 0, 60))
    S.set_params(em, PS, [("Particles.SpriteSize", V2, v2(24, 24), "Particles.SpriteSize * User.Scale"), ("Particles.SpriteAlignment", V3, v3(0, 0, 1), v3(0, 0, 1))],
                 label="(size x User.Scale, upright axis)")
    curl(S, em, 30.0)
    move_solve_last(S, em)
    S.set_params(em, PU, [("Particles.Color", LCOL, col(1, 1, 1, 1), "float4(1.0, 1.0, 1.0, 1.0 - saturate(Particles.NormalizedAge))")], label="(alpha 1 -> 0)")
    S.renderer_set(em, 0, {"Material": ref(MI_DIR + "MI_Flame_Torch.MI_Flame_Torch"), "Alignment": "CustomAlignment", "FacingMode": "FaceCamera",
                           "SpriteAlignmentBinding": S.binding(em, 0, "SpriteAlignmentBinding", "SpriteAlignment")}, "MI_Flame_Torch sprite, upright billboard")

    em = "Embers"
    print("[emitter] Embers")
    add_emitter(S, em, "CPUSim")
    spawn_rate(S, em, "6.0 * User.Scale")
    init_particle(S, em, (1.0, 2.0), (4.0, 1.8, 0.4, 1.0), ("ru", 0.8, 1.5))
    S.enum(em, PS, "ShapeLocation", "Shape Primitive", "Sphere")
    S.inp(em, PS, "ShapeLocation", "Sphere Radius", hlsl("5.0 * User.Scale"))
    velocity_linear(S, em, "float3(0.0, 0.0, 80.0) + User.Wind * 0.2")
    curl(S, em, 60.0)
    move_solve_last(S, em)
    S.set_params(em, PU, [("Particles.Color", LCOL, col(4, 1.8, 0.4, 1), "float4(4.0, 1.8, 0.4, 1.0 - saturate(Particles.NormalizedAge))")], label="(ember colour, fade)")
    S.renderer_set(em, 0, {"Material": ref(MI_DIR + "MI_Flame_Torch.MI_Flame_Torch"), "Alignment": "Unaligned", "FacingMode": "FaceCamera"}, "MI_Flame_Torch (embers)")

    em = "Smoke"
    print("[emitter] Smoke")
    add_emitter(S, em, "CPUSim")
    spawn_rate(S, em, "3.0")
    init_particle(S, em, (3.0, 4.0), (0.08, 0.08, 0.08, 0.1), ("u", 30.0), rotation="Random")
    S.enum(em, PS, "ShapeLocation", "Shape Primitive", "Sphere")
    S.inp(em, PS, "ShapeLocation", "Sphere Radius", hlsl("6.0 * User.Scale"))
    velocity_linear(S, em, v3(0, 0, 40))
    S.set_params(em, PU, [("Particles.SpriteSize", V2, v2(30, 30), "float2(1.0, 1.0) * lerp(30.0, 120.0, saturate(Particles.NormalizedAge)) * User.Scale"),
                          ("Particles.Color", LCOL, col(0.08, 0.08, 0.08, 0.1), "float4(0.08, 0.08, 0.08, 0.1 * sin(3.14159265 * saturate(Particles.NormalizedAge)))")],
                 label="(size 30 -> 120 x Scale, alpha 0.1 with fade in/out)")
    S.renderer_set(em, 0, {"Material": ref(MI_DIR + "MI_LB_Mist.MI_LB_Mist"), "Alignment": "Unaligned", "FacingMode": "FaceCamera"}, "MI_LB_Mist (smoke)")
    return S


# ---- NS_LB_ShaftDust ------------------------------------------------------------------------------
DUST_UVARS = [("User.BoxExtent", "v3", (100, 30, 100)), ("User.Count", "f", 120)]
DUST_BOUNDS = ((-700, -700, -700), (700, 700, 700))   # local space; covers the largest F0.6 half-extent (600)


def build_dust():
    S = Sys("NS_LB_ShaftDust")
    make_system(S, DUST_UVARS)
    em = "Dust"
    print("[emitter] Dust")
    add_emitter(S, em, "GPUComputeSim", DUST_BOUNDS, local=True, keep=("Drag",))
    spawn_rate(S, em, "User.Count / 10.0")
    init_particle(S, em, (8.0, 12.0), (1, 1, 1, 0), ("ru", 0.3, 0.8))
    S.enum(em, PS, "ShapeLocation", "Shape Primitive", "Box")
    S.inp(em, PS, "ShapeLocation", "Box Size", hlsl("User.BoxExtent * 2.0"))
    S.remove_module(em, PS, "AddVelocity")
    curl(S, em, 20.0)
    S.inp(em, PU, "Drag", "Drag", fl(4.0))
    move_solve_last(S, em)
    S.set_params(em, PU, [("Particles.Color", LCOL, col(1, 1, 1, 0), "float4(1.0, 1.0, 1.0, sin(3.14159265 * saturate(Particles.NormalizedAge)))")], label="(alpha 0 -> 1 -> 0)")
    S.renderer_set(em, 0, {"Material": ref(MI_DIR + "MI_LB_DustMote.MI_LB_DustMote"), "Alignment": "Unaligned", "FacingMode": "FaceCamera"}, "MI_LB_DustMote")
    return S


# ---- NS_LB_WaterMist ------------------------------------------------------------------------------
MIST_UVARS = [("User.Extent", "v2", (400, 390))]


def build_watermist():
    S = Sys("NS_LB_WaterMist")
    make_system(S, MIST_UVARS)
    em = "Mist"
    print("[emitter] Mist")
    add_emitter(S, em, "CPUSim")
    spawn_rate(S, em, "4.0")
    init_particle(S, em, 6.0, (1, 1, 1, 0), ("ru", 150.0, 300.0), rotation="Random")
    shape_box(S, em, "float3(User.Extent.x, User.Extent.y, 60.0)", "float3(0.0, 0.0, 30.0)")
    S.enum(em, PS, "AddVelocity", "Velocity Mode", "Linear")
    velocity_random_vec(S, em, "float3(-5.0, -5.0, 0.0)", "float3(5.0, 5.0, 0.0)")
    S.set_params(em, PU, [("Particles.Color", LCOL, col(1, 1, 1, 0), "float4(1.0, 1.0, 1.0, 0.6 * sin(3.14159265 * saturate(Particles.NormalizedAge)))")], label="(alpha 0 -> 0.6 -> 0)")
    S.renderer_set(em, 0, {"Material": ref(MI_DIR + "MI_LB_WaterMist.MI_LB_WaterMist"), "Alignment": "Unaligned", "FacingMode": "FaceCamera"}, "MI_LB_WaterMist")
    return S


# ---- NS_LB_Drip / NS_LB_EaveDrips (fallback route: no event handlers over MCP) ---------------------
DRIP_CROWN_LIFE = 0.3
DRIP_RING_LIFE = 0.6
DRIP_RING_FROM, DRIP_RING_TO = 2.0, 18.0
DRIP_RING_ALPHA = 0.6
DRIP_CROWN_SIZE = 6.0
DRIP_GRAVITY = -980.0


DRIP_SPAWN = [("Particles.Landed", BOOL, bl(False), bl(False)), ("Particles.LandAge", FLOAT, fl(0), fl(0.0)),
              ("Particles.SpriteFacing", V3, v3(0, 0, 1), v3(0, 0, 1)), ("Particles.VisibilityTag", INT, it(0), it(0)),
              ("Particles.CrownColor", LCOL, col(0, 0, 0, 0), col(0, 0, 0, 0)),
              ("Particles.CrownSize", V2, v2(DRIP_CROWN_SIZE, DRIP_CROWN_SIZE), v2(DRIP_CROWN_SIZE, DRIP_CROWN_SIZE)),
              ("Particles.RingColor", LCOL, col(0, 0, 0, 0), col(0, 0, 0, 0)),
              ("Particles.RingSize", V2, v2(DRIP_RING_FROM, DRIP_RING_FROM), v2(DRIP_RING_FROM, DRIP_RING_FROM))]
# the latch chain, one SetParameters module per row, after GravityForce and SolveForcesAndVelocity. Positions are LOCAL (the emitter is local space):
# the drop is pinned at Z = -User.FallHeight (the same Landed / LandAge pattern as the S1 splash pin).
DRIP_CHAIN = [
    [("Particles.Landed", BOOL, bl(False), "Particles.Landed || Particles.Position.z <= -User.FallHeight")],
    [("Particles.Position", POS, v3(0, 0, 0), "Particles.Landed ? float3(Particles.Position.x, Particles.Position.y, -User.FallHeight) : Particles.Position"),
     ("Particles.Velocity", V3, v3(0, 0, 0), "Particles.Landed ? float3(0.0, 0.0, 0.0) : Particles.Velocity")],
    [("Particles.LandAge", FLOAT, fl(0), "Particles.Landed ? Particles.LandAge + Engine.DeltaTime : 0.0")],
    [("Particles.VisibilityTag", INT, it(0), "Particles.Landed ? 1 : 0"),
     ("Particles.Color", LCOL, col(1, 1, 1, 0), "Particles.Landed ? float4(0.0, 0.0, 0.0, 0.0) : float4(1.0, 1.0, 1.0, 0.5)"),
     ("Particles.CrownColor", LCOL, col(0, 0, 0, 0),
      "(Particles.Landed && Particles.LandAge <= %g) ? float4(1.0, 1.0, 1.0, 1.0) : float4(0.0, 0.0, 0.0, 0.0)" % DRIP_CROWN_LIFE),
     ("Particles.SubImageIndex", FLOAT, fl(0), "min(15.0, floor(Particles.LandAge / %g * 16.0))" % DRIP_CROWN_LIFE),
     ("Particles.RingColor", LCOL, col(0, 0, 0, 0),
      "(Particles.Landed && User.bWater) ? float4(1.0, 1.0, 1.0, %g * (1.0 - saturate(Particles.LandAge / %g))) : float4(0.0, 0.0, 0.0, 0.0)" % (DRIP_RING_ALPHA, DRIP_RING_LIFE)),
     ("Particles.RingSize", V2, v2(DRIP_RING_FROM, DRIP_RING_FROM),
      "float2(1.0, 1.0) * lerp(%g, %g, saturate(Particles.LandAge / %g))" % (DRIP_RING_FROM, DRIP_RING_TO, DRIP_RING_LIFE))],
    [("DataInstance.Alive", BOOL, bl(True), "Particles.LandAge <= (User.bWater ? %g : %g) && Particles.Age < Particles.Lifetime" % (DRIP_RING_LIFE, DRIP_CROWN_LIFE))],
]


def drip_common(S, em):
    S.set_params(em, PS, DRIP_SPAWN, label="(spawn: latch state)")
    gravity(S, em, DRIP_GRAVITY)
    move_solve_last(S, em)
    for row in DRIP_CHAIN:
        S.set_params(em, PU, row)
    # renderer A: the falling drop; B: the crown; C: the ring. A visibility tag (0 falling, 1 landed) switches A against B and C.
    S.renderer_set(em, 0, {"Material": ref(MI_DIR + "MI_LB_Rain.MI_LB_Rain"), "Alignment": "VelocityAligned", "FacingMode": "FaceCamera",
                           "RendererVisibility": 0, "RendererVisibilityTagBinding": S.binding(em, 0, "RendererVisibilityTagBinding", "VisibilityTag")}, "A: falling drop MI_LB_Rain, tag 0")
    ib = S.add_renderer(em)
    S.renderer_set(em, ib, {"Material": ref(MI_DIR + "MI_LB_Splash.MI_LB_Splash"), "Alignment": "Unaligned", "FacingMode": "FaceCamera",
                            "SubImageSize": {"x": 4, "y": 4}, "bSubImageBlend": False, "RendererVisibility": 1,
                            "RendererVisibilityTagBinding": S.binding(em, ib, "RendererVisibilityTagBinding", "VisibilityTag"),
                            "ColorBinding": S.binding(em, ib, "ColorBinding", "CrownColor"), "SpriteSizeBinding": S.binding(em, ib, "SpriteSizeBinding", "CrownSize"),
                            "SubImageIndexBinding": S.binding(em, ib, "SubImageIndexBinding", "SubImageIndex")}, "B: crown MI_LB_Splash SubUV, tag 1")
    ic = S.add_renderer(em)
    S.renderer_set(em, ic, {"Material": ref(MI_DIR + "MI_LB_Ripple.MI_LB_Ripple"), "Alignment": "Unaligned", "FacingMode": "CustomFacingVector", "RendererVisibility": 1,
                            "RendererVisibilityTagBinding": S.binding(em, ic, "RendererVisibilityTagBinding", "VisibilityTag"),
                            "SpriteFacingBinding": S.binding(em, ic, "SpriteFacingBinding", "SpriteFacing"),
                            "SpriteSizeBinding": S.binding(em, ic, "SpriteSizeBinding", "RingSize"),
                            "ColorBinding": S.binding(em, ic, "ColorBinding", "RingColor")}, "C: ring MI_LB_Ripple, tag 1, alpha 0 unless User.bWater")


def build_drip():
    S = Sys("NS_LB_Drip")
    make_system(S, [("User.FallHeight", "f", 500), ("User.Interval", "v2", (1.5, 4.0)), ("User.bWater", "b", False)])
    em = "Drop"
    print("[emitter] Drop")
    add_emitter(S, em, "CPUSim", local=True)
    # one drop per loop; the loop length is random in User.Interval and re-rolled each loop; a random first delay desynchronises the points
    S.remove_module(em, EU, "SpawnRate")
    mb = S.add_module(em, EU, M_BURST)
    S.inp(em, EU, mb, "Spawn Count", it(1))
    S.inp(em, EU, mb, "Spawn Time", fl(0.0))
    emitter_state(S, em, behavior="Infinite", duration=("User.Interval.x", "User.Interval.y"), recalc=True, delay=(0.0, "User.Interval.y"))
    init_particle(S, em, 5.0, (1, 1, 1, 0.5), ("nu", (0.5, 5.0)))
    S.remove_module(em, PS, "ShapeLocation")
    S.remove_module(em, PS, "AddVelocity")
    drip_common(S, em)
    return S


def build_eave():
    S = Sys("NS_LB_EaveDrips")
    make_system(S, [("User.LineLength", "f", 400), ("User.FallHeight", "f", 500), ("User.bWater", "b", False)])
    em = "Drops"
    print("[emitter] Drops")
    add_emitter(S, em, "CPUSim", local=True)
    spawn_rate(S, em, "6.0")
    init_particle(S, em, 5.0, (1, 1, 1, 0.5), ("nu", (0.5, 5.0)))
    shape_box(S, em, "float3(User.LineLength, 0.1, 0.1)", "float3(User.LineLength * 0.5, 0.0, 0.0)")
    S.remove_module(em, PS, "AddVelocity")
    drip_common(S, em)
    return S


# ---- commands -------------------------------------------------------------------------------------
BUILDERS = {"NS_LB_Rain": build_rain, "NS_LB_StrikeSparks": build_sparks, "NS_LB_TorchFire": build_torch, "NS_LB_ShaftDust": build_dust,
            "NS_LB_WaterMist": build_watermist, "NS_LB_Drip": build_drip, "NS_LB_EaveDrips": build_eave}


def report_compile(S):
    cs = S.compile_state()
    print("[compile] %s aggregate=%s errors=%s warnings=%s stale=%s" % (S.name, cs["aggregateStatus"], cs["bHasErrors"], cs["bHasWarnings"], cs["bIsStale"]))
    for s in cs["scripts"]:
        print("    ", s["emitterName"], s["scriptName"].split("::")[-1], s["lastCompileStatus"], s["errorSummary"][:300])
    iss = S.issues()
    print("[issues] %s errors=%d warnings=%d infos=%d" % (S.name, iss["numErrors"], iss["numWarnings"], iss["numInfos"]))
    for i in iss["issues"]:
        if i["severity"] != "Info":
            l = i["location"]
            print("    %s %s %s %s: %s | %s" % (i["severity"], l["emitterName"], l["scriptName"].split("::")[-1], l["moduleName"], i["shortDescription"], i["longDescription"][:300]))
    return cs, iss


def pick(only):
    names = [n.strip() for n in only.split(",")] if only else list(BUILDERS)
    for n in names:
        if n not in BUILDERS:
            sys.exit("unknown system " + n)
    return names


# ---- check ----------------------------------------------------------------------------------------
_fail = 0
_pass = 0


def chk(name, cond, detail=""):
    global _fail, _pass
    if cond:
        _pass += 1
        print("PASS", name, detail)
    else:
        _fail += 1
        print("FAIL", name, detail)


def val(S, em, script, module, name):
    """Stack input value; name is an input name or a [input, child, ...] list (dynamic input children)."""
    names = [name] if isinstance(name, str) else list(name)
    return S.getin(S.R(em, script, module, -1, names))["value"]


def ci(S, em, script, module, name, kind, want, label=None):
    """Check one module input against `want`. kinds: float bool int v2 v3 col link hlsl enum dyn."""
    lab = "%s %s.%s%s" % (S.name.replace("NS_LB_", ""), em + "/" + module if em else module, name if isinstance(name, str) else ".".join(name), "")
    try:
        v = val(S, em, script, module, name)
    except Exception as e:  # noqa: BLE001
        chk(label or lab, False, "read failed: " + str(e)[:120])
        return
    ok, shown = False, str(v)[:120]
    try:
        if kind == "float":
            ok, shown = abs(v["value"] - want) < 1e-4, v["value"]
        elif kind == "bool":
            ok, shown = (v["value"] != 0) == want, bool(v["value"])
        elif kind == "int":
            ok, shown = v["value"] == want, v["value"]
        elif kind == "v2":
            ok, shown = abs(v["x"] - want[0]) < 1e-4 and abs(v["y"] - want[1]) < 1e-4, (v["x"], v["y"])
        elif kind == "v3":
            ok, shown = all(abs(v[k] - w) < 1e-4 for k, w in zip("xyz", want)), (v["x"], v["y"], v["z"])
        elif kind == "col":
            ok, shown = all(abs(v[k] - w) < 1e-4 for k, w in zip("rgba", want)), (v["r"], v["g"], v["b"], v["a"])
        elif kind == "link":
            shown = v["linkedVariable"]["name"]
            ok = shown == want
        elif kind == "hlsl":
            shown = v["hlslExpression"]
            ok = shown == want
        elif kind == "enum":
            shown = v["displayName"]
            ok = shown.lower().startswith(want.lower())
        elif kind == "dyn":
            shown = v["dynamicInputAsset"]["refPath"].split("/")[-1].split(".")[0]
            ok = shown == want
    except (KeyError, TypeError):
        ok = False
    chk(label or lab, ok, "%s (want %s)" % (shown, want) if not ok else str(shown)[:110])


def sp_module(S, em, script, entries):
    """Name of the SetParameters module whose inputs are exactly `entries`, else None."""
    for m in S.modules(em, script):
        if m.get("bIsSetParametersModule") and sorted(i["name"] for i in m["inputs"]) == sorted(entries):
            return m["moduleName"]
    return None


def cp(S, em, script, row):
    """Check one SetParameters row (entries as in the build tables): module exists, each expression or literal reads back."""
    names = [r[0] for r in row]
    mn = sp_module(S, em, script, names)
    chk("%s/%s SetParameters %s present" % (S.name.replace("NS_LB_", ""), em, "+".join(n.split(".")[-1] for n in names)), mn is not None)
    if not mn:
        return None
    for n, _, _, expr in row:
        if isinstance(expr, str):
            ci(S, em, script, mn, n, "hlsl", expr, label="%s/%s %s = %s" % (S.name.replace("NS_LB_", ""), em, n.split(".")[-1], expr[:70]))
        else:
            v = S.getin(S.R(em, script, mn, -1, [n]))["value"]
            chk("%s/%s %s literal" % (S.name.replace("NS_LB_", ""), em, n.split(".")[-1]), v == expr["value"] or all(abs(v[k] - expr["value"][k]) < 1e-4 for k in expr["value"]) if isinstance(v, dict) else False, str(v)[:70])
    return mn


def chk_chain(S, em, script, rows, after):
    """The SetParameters rows appear in this order, all after the module `after` (and nothing else follows them)."""
    mods = S.module_names(em, script)
    pos = []
    for row in rows:
        mn = sp_module(S, em, script, [r[0] for r in row])
        pos.append(mods.index(mn) if mn in mods else -1)
    chk("%s/%s chain order %s" % (S.name.replace("NS_LB_", ""), em, "/".join(r[0][0].split(".")[-1] for r in rows)),
        all(p >= 0 for p in pos) and pos == sorted(pos) and pos[0] > mods.index(after) and mods[-1] == mods[pos[-1]], "positions %s of %d modules" % (pos, len(mods)))


def chk_user_vars(S, want):
    r = S.call("GetUserVariables", {"system": S.sys}, read=True)
    got = {v["name"]: v for v in r["userVariables"]}
    chk(S.name + " user variable count", len(got) == len(want), "%d (want %d): %s" % (len(got), len(want), sorted(got)))
    tmap = {"f": FLOAT, "b": BOOL, "v3": V3, "v2": V2}
    for name, kind, d in want:
        v = got.get(name)
        if not v:
            chk(S.name + " user " + name, False, "missing")
            continue
        typ = v["type"]["classStructOrEnum"]["refPath"]
        dv = v["defaultValue"]["value"]
        if kind == "f":
            okv, shown = abs(dv["value"] - float(d)) < 1e-4, dv["value"]
        elif kind == "b":
            okv, shown = (dv["value"] != 0) == bool(d), bool(dv["value"])
        elif kind == "v3":
            okv, shown = all(abs(dv[k] - float(w)) < 1e-4 for k, w in zip("xyz", d)), (dv["x"], dv["y"], dv["z"])
        else:
            okv, shown = all(abs(dv[k] - float(w)) < 1e-4 for k, w in zip("xy", d)), (dv["x"], dv["y"])
        chk("%s %s %s" % (S.name, name, typ.split(".")[-1]), typ == tmap[kind] and okv, "default %s" % (shown,))


def chk_compile(S, gpu_emitters=(), emitters=()):
    cs = S.compile_state()
    chk(S.name + " compile aggregate UpToDate", cs["aggregateStatus"] == "UpToDate" and not cs["bHasErrors"], "aggregate=%s errors=%s stale=%s" % (cs["aggregateStatus"], cs["bHasErrors"], cs["bIsStale"]))
    bad = [(s["emitterName"], s["scriptName"].split("::")[-1], s["lastCompileStatus"]) for s in cs["scripts"] if s["lastCompileStatus"] != "UpToDate"]
    chk(S.name + " every script UpToDate", not bad, "%d scripts%s" % (len(cs["scripts"]), "; not up to date: %s" % bad if bad else ""))
    for em in gpu_emitters:
        g = [s["lastCompileStatus"] for s in cs["scripts"] if s["emitterName"] == em and s["scriptName"].endswith("ParticleGPUComputeScript")]
        chk("%s/%s GPU compute script compiled" % (S.name, em), g == ["UpToDate"], str(g))
    for em in emitters:
        sc = sorted(s["scriptName"].split("::")[-1] for s in cs["scripts"] if s["emitterName"] == em)
        chk("%s/%s has spawn and update scripts" % (S.name, em), "ParticleSpawnScriptInterpolated" in sc and "ParticleUpdateScript" in sc, str(sc))
    iss = S.issues()
    chk(S.name + " stack issues: 0 errors", iss["numErrors"] == 0, "errors=%d warnings=%d infos=%d" % (iss["numErrors"], iss["numWarnings"], iss["numInfos"]))
    for i in iss["issues"]:
        if i["severity"] == "Warning":
            l = i["location"]
            print("WARN", S.name, l["emitterName"], l["scriptName"].split("::")[-1], l["moduleName"], i["shortDescription"], "|", i["longDescription"][:200])
        elif i["severity"] == "Error":
            print("ERRORISSUE", S.name, i["location"]["emitterName"], i["shortDescription"], "|", i["longDescription"][:200])


def chk_emitter(S, em, sim, local=False, bounds=None):
    summ = S.call("GetEmitterSummary", {"emitterRef": S.R(em)}, read=True)
    chk("%s/%s SimTarget %s" % (S.name, em, sim), summ["simTarget"] == sim, summ["simTarget"])
    pv = json.loads(S.call("GetEmitterData", {"emitterRef": S.R(em)}, read=True)["propertyValues"])
    chk("%s/%s local space %s" % (S.name, em, local), pv["bLocalSpace"] is local)
    if bounds:
        fb = pv["FixedBounds"]
        got = (fb["min"]["x"], fb["min"]["y"], fb["min"]["z"], fb["max"]["x"], fb["max"]["y"], fb["max"]["z"])
        chk("%s/%s fixed bounds %s" % (S.name, em, bounds), pv["CalculateBoundsMode"] == "Fixed" and got == tuple(bounds[0]) + tuple(bounds[1]), "mode=%s %s" % (pv["CalculateBoundsMode"], got))
    else:
        chk("%s/%s dynamic bounds" % (S.name, em), pv["CalculateBoundsMode"] == "Dynamic", pv["CalculateBoundsMode"])


def renderer_count(S, em):
    n = 0
    while True:
        try:
            S.call("GetRendererData", {"rendererRef": S.R(em, "", "", n)}, read=True)
            n += 1
        except RuntimeError:
            return n


def chk_renderers(S, em, specs):
    """specs: list of dict(kind, material, props={}, bind={key: attr}) in renderer-index order."""
    n = renderer_count(S, em)
    chk("%s/%s renderer count %d" % (S.name, em, len(specs)), n == len(specs), str(n))
    for idx, sp in enumerate(specs):
        pv = S.renderer_get(em, idx)
        kind = "sprite" if "SubImageSize" in pv else ("light" if "RadiusScale" in pv else "?")
        tag = "%s/%s renderer %d" % (S.name, em, idx)
        chk("%s is %s" % (tag, sp["kind"]), kind == sp["kind"], kind)
        if sp.get("material"):
            m = pv.get("Material", {}).get("refPath", "")
            chk("%s material %s" % (tag, sp["material"]), m == MI_DIR + sp["material"] + "." + sp["material"], m)
        for k, w in sp.get("props", {}).items():
            g = pv.get(k)
            okp = (abs(g - w) < 1e-4) if isinstance(w, float) and isinstance(g, (int, float)) else (g == w)
            chk("%s %s = %s" % (tag, k, w), okp, str(g))
        for k, attr in sp.get("bind", {}).items():
            b = pv[k]
            chk("%s %s -> Particles.%s" % (tag, k, attr), b["paramMapVariable"]["name"] == "Particles." + attr and b["bindingSourceMode"] == "ExplicitParticles" and b["bBindingExistsOnSource"] is True,
                "%s %s exists=%s" % (b["paramMapVariable"]["name"], b["bindingSourceMode"], b["bBindingExistsOnSource"]))


def chk_collision(S, em, kill, radius, rest=False):
    ci(S, em, PU, "Collision", "GPU Collision Type", "enum", "GPU Distance Fields", "%s/%s collision mode = GPU Distance Fields" % (S.name, em))
    ci(S, em, PU, "Collision", "Collision Enabled", "bool", True, "%s/%s collision enabled" % (S.name, em))
    ci(S, em, PU, "Collision", "KillOnCollision", "bool", kill, "%s/%s kill on collision = %s" % (S.name, em, kill))
    ci(S, em, PU, "Collision", "Radius Calculation Type", "enum", "Custom", "%s/%s collision radius type Custom" % (S.name, em))
    ci(S, em, PU, "Collision", "Particle Radius", "float", radius, "%s/%s collision radius = %g cm" % (S.name, em, radius))
    if rest:
        ci(S, em, PU, "Collision", "Restitution", "float", 0.0, "%s/%s restitution 0" % (S.name, em))
        ci(S, em, PU, "Collision", "Friction", "float", 1.0, "%s/%s friction 1" % (S.name, em))
        ci(S, em, PU, "Collision", "Enable Rest State", "bool", True, "%s/%s rest state on" % (S.name, em))
    mods = S.module_names(em, PU)
    chk("%s/%s Collision runs before SolveForcesAndVelocity" % (S.name, em), mods.index("Collision") < mods.index("SolveForcesAndVelocity"), str(mods[:4]))


def chk_init(S, em, life, color, size, tag):
    m = "InitializeParticle"
    if isinstance(life, tuple):
        ci(S, em, PS, m, "Lifetime Mode", "enum", "Random", tag + " lifetime mode Random")
        ci(S, em, PS, m, "Lifetime Min", "float", life[0], "%s lifetime min %g" % (tag, life[0]))
        ci(S, em, PS, m, "Lifetime Max", "float", life[1], "%s lifetime max %g" % (tag, life[1]))
    else:
        ci(S, em, PS, m, "Lifetime", "float", life, "%s lifetime %g" % (tag, life))
    ci(S, em, PS, m, "Color", "col", color, "%s colour %s" % (tag, color))
    if size[0] == "u":
        ci(S, em, PS, m, "Uniform Sprite Size", "float", size[1], "%s size %g" % (tag, size[1]))
    elif size[0] == "ru":
        ci(S, em, PS, m, "Uniform Sprite Size Min", "float", size[1], "%s size min %g" % (tag, size[1]))
        ci(S, em, PS, m, "Uniform Sprite Size Max", "float", size[2], "%s size max %g" % (tag, size[2]))
    elif size[0] == "nu":
        ci(S, em, PS, m, "Sprite Size", "v2", size[1], "%s size %s" % (tag, size[1]))
    elif size[0] == "rnu":
        ci(S, em, PS, m, "Sprite Size Min", "v2", size[1], "%s size min %s" % (tag, size[1]))
        ci(S, em, PS, m, "Sprite Size Max", "v2", size[2], "%s size max %s" % (tag, size[2]))


def chk_rate(S, em, expr):
    kind = "link" if expr.startswith("User.") and " " not in expr else "hlsl"
    ci(S, em, EU, "SpawnRate", "SpawnRate", kind, expr, "%s/%s spawn rate = %s" % (S.name, em, expr))


def chk_sys(S):
    chk(S.name + " exists", bool(E().call(AS, "exists", {"path": S.pkg}, read=True)))
    chk(S.name + " in " + FOLDER, S.pkg.startswith(FOLDER + "/"))


def check_rain():
    S = Sys("NS_LB_Rain")
    chk_sys(S)
    chk_user_vars(S, RAIN_UVARS)
    chk(S.name + " emitters Rain, Splash, GroundMist", S.emitters() == ["Rain", "Splash", "GroundMist"], str(S.emitters()))
    chk_compile(S, gpu_emitters=("Rain", "Splash"), emitters=("Rain", "Splash", "GroundMist"))
    # --- Rain
    em = "Rain"
    print("-- emitter Rain")
    chk_emitter(S, em, "GPUComputeSim", bounds=RAIN_BOUNDS)
    chk_rate(S, em, "User.RainRate")
    chk_init(S, em, 3.5, (1, 1, 1, 0.7), ("rnu", (0.7, 28.0), (0.7, 42.0)), "Rain")
    ci(S, em, PS, "ShapeLocation", "Shape Primitive", "enum", "Box")
    ci(S, em, PS, "ShapeLocation", "Box Size", "hlsl", "float3(User.BoxHalf * 2.0, User.BoxHalf * 2.0, 400.0)", "Rain box XY +-User.BoxHalf, Z 400 (+-200 jitter)")
    ci(S, em, PS, "ShapeLocation", "Offset", "hlsl", "float3(0.0, 0.0, User.SpawnHeight)", "Rain spawn offset Z = User.SpawnHeight")
    ci(S, em, PS, "AddVelocity", "Velocity Mode", "enum", "Linear")
    ci(S, em, PS, "AddVelocity", "Velocity", "dyn", "RandomRangeVector", "Rain velocity = dynamic input RandomRangeVector")
    ci(S, em, PS, "AddVelocity", ["Velocity", "Minimum"], "hlsl", "float3(User.Wind.x, User.Wind.y, User.Wind.z - User.FallMax)", "Rain velocity min = Wind + (0,0,-FallMax)")
    ci(S, em, PS, "AddVelocity", ["Velocity", "Maximum"], "hlsl", "float3(User.Wind.x, User.Wind.y, User.Wind.z - User.FallMin)", "Rain velocity max = Wind + (0,0,-FallMin)")
    mods = S.module_names(em, PU)
    chk("Rain no gravity / drag / scale-colour", not any(m in mods for m in ("GravityForce", "Drag", "ScaleColor")), str(mods))
    chk_collision(S, em, True, RAIN_RADIUS)
    mn = sp_module(S, em, PU, ["DataInstance.Alive"])
    chk("Rain DataInstance.Alive SetParameters present, last module", mn is not None and S.module_names(em, PU)[-1] == mn, str(mn))
    if mn:
        ci(S, em, PU, mn, "DataInstance.Alive", "hlsl", ALIVE_RAIN, "Rain Alive = kill below Engine.Owner.Position.z - 800")
    chk_renderers(S, em, [dict(kind="sprite", material="MI_LB_Rain", props={"Alignment": "VelocityAligned", "FacingMode": "FaceCamera"})])
    # --- Splash
    em = "Splash"
    print("-- emitter Splash")
    chk_emitter(S, em, "GPUComputeSim", bounds=RAIN_BOUNDS)
    chk_rate(S, em, "User.SplashRate")
    chk_init(S, em, 5.0, (0, 0, 0, 0), ("ru", 6.0, 10.0), "Splash")
    ci(S, em, PS, "ShapeLocation", "Shape Primitive", "enum", "Cylinder")
    ci(S, em, PS, "ShapeLocation", "Cylinder Radius", "link", "User.SplashRadius", "Splash disc radius = User.SplashRadius")
    ci(S, em, PS, "ShapeLocation", "Cylinder Height", "float", 1.0, "Splash disc height 1 cm")
    ci(S, em, PS, "ShapeLocation", "Offset", "hlsl", "float3(0.0, 0.0, User.SpawnHeight)", "Splash spawn offset Z = User.SpawnHeight")
    ci(S, em, PS, "AddVelocity", "Velocity", "dyn", "RandomRangeVector", "Splash velocity = dynamic input RandomRangeVector")
    ci(S, em, PS, "AddVelocity", ["Velocity", "Minimum"], "hlsl", "float3(0.0, 0.0, -User.FallMax)", "Splash falls at rain speed: min (0,0,-FallMax)")
    ci(S, em, PS, "AddVelocity", ["Velocity", "Maximum"], "hlsl", "float3(0.0, 0.0, -User.FallMin)", "Splash falls at rain speed: max (0,0,-FallMin)")
    chk_collision(S, em, False, SPLASH_COLLISION_RADIUS, rest=True)
    mods = S.module_names(em, PU)
    chk("Splash update order before the chain: ParticleState, Collision, SolveForcesAndVelocity", mods[:3] == ["ParticleState", "Collision", "SolveForcesAndVelocity"], str(mods[:3]))
    chk("Splash update stack = 3 built-ins + 6 chain modules", len(mods) == 9, str(len(mods)))
    chk_chain(S, em, PU, SPLASH_CHAIN, "SolveForcesAndVelocity")
    for row in SPLASH_CHAIN:
        cp(S, em, PU, row)
    # spawn latch state
    mods = S.module_names(em, PS)
    chk("Splash spawn stack has the two latch-state modules after AddVelocity", mods[-3] == "AddVelocity" or "AddVelocity" in mods[:-2], str(mods))
    for n, kind, want in (("Particles.Landed", "bool", False), ("Particles.RingSize", "v2", (RING_FROM, RING_FROM)), ("Particles.SpriteFacing", "v3", (0, 0, 1)), ("Particles.RingColor", "col", (0, 0, 0, 0))):
        mn = sp_module(S, em, PS, ["Particles.Landed", "Particles.RingSize", "Particles.RingColor", "Particles.SpriteFacing"])
        ci(S, em, PS, mn, n, kind, want, "Splash spawn %s = %s" % (n.split(".")[-1], want))
    mn = sp_module(S, em, PS, ["Particles.LandPos", "Particles.LandAge"])
    ci(S, em, PS, mn, "Particles.LandPos", "hlsl", "Particles.Position", "Splash spawn LandPos = Particles.Position")
    ci(S, em, PS, mn, "Particles.LandAge", "float", 0.0, "Splash spawn LandAge = 0")
    chk_renderers(S, em, [
        dict(kind="sprite", material="MI_LB_Splash", props={"Alignment": "Unaligned", "FacingMode": "FaceCamera", "SubImageSize": {"x": 4, "y": 4}}, bind={"SubImageIndexBinding": "SubImageIndex"}),
        dict(kind="sprite", material="MI_LB_Ripple", props={"Alignment": "Unaligned", "FacingMode": "CustomFacingVector"},
             bind={"SpriteFacingBinding": "SpriteFacing", "SpriteSizeBinding": "RingSize", "ColorBinding": "RingColor"})])
    # --- GroundMist
    em = "GroundMist"
    print("-- emitter GroundMist")
    chk_emitter(S, em, "CPUSim")
    chk_rate(S, em, "5.0 * User.Mist")
    chk_init(S, em, 6.0, (1, 1, 1, 1), ("ru", 250.0, 450.0), "GroundMist")
    ci(S, em, PS, "InitializeParticle", "Sprite Rotation Mode", "enum", "Random", "GroundMist rotation random")
    ci(S, em, PS, "ShapeLocation", "Shape Primitive", "enum", "Ring")
    ci(S, em, PS, "ShapeLocation", "Ring Radius", "float", 2200.0, "GroundMist ring outer radius 2200")
    ci(S, em, PS, "ShapeLocation", "Disc Coverage", "float", round(1.0 - 600.0 / 2200.0, 6), "GroundMist disc coverage -> inner radius 600")
    ci(S, em, PS, "ShapeLocation", "Offset", "dyn", "RandomRangeVector", "GroundMist offset = RandomRangeVector (Z -120 +-40)")
    ci(S, em, PS, "ShapeLocation", ["Offset", "Minimum"], "v3", (0, 0, -160), "GroundMist offset min (0,0,-160)")
    ci(S, em, PS, "ShapeLocation", ["Offset", "Maximum"], "v3", (0, 0, -80), "GroundMist offset max (0,0,-80)")
    ci(S, em, PS, "AddVelocity", "Velocity", "hlsl", "User.Wind * 0.15", "GroundMist velocity = User.Wind * 0.15")
    cp(S, em, PU, [("Particles.Color", LCOL, None, "float4(1.0, 1.0, 1.0, sin(3.14159265 * saturate(Particles.NormalizedAge)))")])
    chk_renderers(S, em, [dict(kind="sprite", material="MI_LB_Mist", props={"Alignment": "Unaligned", "FacingMode": "FaceCamera"})])


def check_sparks():
    S = Sys("NS_LB_StrikeSparks")
    chk_sys(S)
    chk_user_vars(S, SPARKS_UVARS)
    chk(S.name + " emitters Sparks", S.emitters() == ["Sparks"], str(S.emitters()))
    chk_compile(S, emitters=("Sparks",))
    # completes: system Once / 1.5 s / Complete; emitter Once / Complete, no SpawnRate, one burst of 70
    ci(S, "", SU, "SystemState", "Loop Behavior", "enum", "Once", "Sparks system loop behaviour Once")
    ci(S, "", SU, "SystemState", "Loop Duration", "float", 1.5, "Sparks system loop duration 1.5 s")
    ci(S, "", SU, "SystemState", "Inactive Response", "enum", "Complete", "Sparks system inactive response Complete")
    em = "Sparks"
    chk_emitter(S, em, "CPUSim")
    eu = S.module_names(em, EU)
    chk("Sparks no SpawnRate module (no infinite spawn)", "SpawnRate" not in eu and "SpawnBurst_Instantaneous" in eu, str(eu))
    ci(S, em, EU, "SpawnBurst_Instantaneous", "Spawn Count", "int", SPARK_COUNT, "Sparks burst count 70")
    ci(S, em, EU, "SpawnBurst_Instantaneous", "Spawn Time", "float", 0.0, "Sparks burst at t = 0")
    ci(S, em, EU, "EmitterState", "Loop Behavior", "enum", "Once", "Sparks emitter loop behaviour Once")
    ci(S, em, EU, "EmitterState", "Inactive Response", "enum", "Complete", "Sparks emitter inactive response Complete")
    ci(S, em, EU, "EmitterState", "Loop Duration", "float", 0.25, "Sparks emitter loop duration 0.25 s")
    chk_init(S, em, (0.4, 0.9), (6.0, 5.4, 4.2, 1.0), ("rnu", (1.0, 4.0), (2.5, 10.0)), "Sparks")
    ci(S, em, PS, "ShapeLocation", "Shape Primitive", "enum", "Sphere")
    ci(S, em, PS, "AddVelocity", "Velocity Mode", "enum", "From Point", "Sparks velocity mode From Point (sphere)")
    ci(S, em, PS, "AddVelocity", "Velocity Speed", "dyn", "RandomRangeFloat", "Sparks speed = RandomRangeFloat")
    ci(S, em, PS, "AddVelocity", ["Velocity Speed", "Minimum"], "float", 400.0, "Sparks speed min 400")
    ci(S, em, PS, "AddVelocity", ["Velocity Speed", "Maximum"], "float", 900.0, "Sparks speed max 900")
    ci(S, em, PU, "GravityForce", "Gravity", "v3", (0, 0, -980), "Sparks gravity (0,0,-980)")
    mods = S.module_names(em, PU)
    chk("Sparks GravityForce before SolveForcesAndVelocity", mods.index("GravityForce") < mods.index("SolveForcesAndVelocity"), str(mods))
    expr = "(float(Particles.UniqueID) - %g * floor((float(Particles.UniqueID) + 0.5) / %g)) < 0.5" % (SPARK_LIGHT_EVERY, SPARK_LIGHT_EVERY)
    cp(S, em, PS, [("Particles.LightEnabled", BOOL, None, expr), ("Particles.LightRadius", FLOAT, None, fl(SPARK_LIGHT_RADIUS))])
    chk_renderers(S, em, [
        dict(kind="sprite", material="MI_Flame_Torch", props={"Alignment": "VelocityAligned"}),
        dict(kind="light", props={"bUseInverseSquaredFalloff": False, "bAffectsTranslucency": False},
             bind={"LightRenderingEnabledBinding": "LightEnabled", "RadiusBinding": "LightRadius", "ColorBinding": "LightColor"})])
    print("INFO sparks light renderer method: LightRenderingEnabledBinding -> Particles.LightEnabled (every %dth Particles.UniqueID = 5 %%); radius %g, colour x20" % (SPARK_LIGHT_EVERY, SPARK_LIGHT_RADIUS))


def check_torch():
    S = Sys("NS_LB_TorchFire")
    chk_sys(S)
    chk_user_vars(S, TORCH_UVARS)
    chk(S.name + " emitters Flames, Embers, Smoke", S.emitters() == ["Flames", "Embers", "Smoke"], str(S.emitters()))
    chk_compile(S, emitters=("Flames", "Embers", "Smoke"))
    for em in ("Flames", "Embers", "Smoke"):
        chk_emitter(S, em, "CPUSim")
    em = "Flames"
    print("-- emitter Flames")
    chk_rate(S, em, "14.0 * User.Scale")
    chk_init(S, em, (0.5, 0.8), (1, 1, 1, 1), ("ru", 18.0, 30.0), "Flames")
    ci(S, em, PS, "AddVelocity", "Velocity", "v3", (0, 0, 60), "Flames velocity up 60 cm/s")
    cp(S, em, PS, [("Particles.SpriteSize", V2, None, "Particles.SpriteSize * User.Scale"), ("Particles.SpriteAlignment", V3, None, v3(0, 0, 1))])
    ci(S, em, PU, "CurlNoiseForce", "Noise Strength", "float", 30.0, "Flames curl noise 30")
    cp(S, em, PU, [("Particles.Color", LCOL, None, "float4(1.0, 1.0, 1.0, 1.0 - saturate(Particles.NormalizedAge))")])
    mods = S.module_names(em, PU)
    chk("Flames CurlNoiseForce before SolveForcesAndVelocity", mods.index("CurlNoiseForce") < mods.index("SolveForcesAndVelocity"), str(mods))
    chk_renderers(S, em, [dict(kind="sprite", material="MI_Flame_Torch", props={"Alignment": "CustomAlignment", "FacingMode": "FaceCamera"}, bind={"SpriteAlignmentBinding": "SpriteAlignment"})])
    em = "Embers"
    print("-- emitter Embers")
    chk_rate(S, em, "6.0 * User.Scale")
    chk_init(S, em, (1.0, 2.0), (4.0, 1.8, 0.4, 1.0), ("ru", 0.8, 1.5), "Embers")
    ci(S, em, PS, "AddVelocity", "Velocity", "hlsl", "float3(0.0, 0.0, 80.0) + User.Wind * 0.2", "Embers velocity up 80 + User.Wind * 0.2")
    ci(S, em, PU, "CurlNoiseForce", "Noise Strength", "float", 60.0, "Embers curl noise 60")
    mods = S.module_names(em, PU)
    chk("Embers CurlNoiseForce before SolveForcesAndVelocity", mods.index("CurlNoiseForce") < mods.index("SolveForcesAndVelocity"), str(mods))
    cp(S, em, PU, [("Particles.Color", LCOL, None, "float4(4.0, 1.8, 0.4, 1.0 - saturate(Particles.NormalizedAge))")])
    chk_renderers(S, em, [dict(kind="sprite", material="MI_Flame_Torch", props={"Alignment": "Unaligned", "FacingMode": "FaceCamera"})])
    em = "Smoke"
    print("-- emitter Smoke")
    chk_rate(S, em, "3.0")
    chk_init(S, em, (3.0, 4.0), (0.08, 0.08, 0.08, 0.1), ("u", 30.0), "Smoke")
    ci(S, em, PS, "AddVelocity", "Velocity", "v3", (0, 0, 40), "Smoke velocity up 40 cm/s")
    cp(S, em, PU, [("Particles.SpriteSize", V2, None, "float2(1.0, 1.0) * lerp(30.0, 120.0, saturate(Particles.NormalizedAge)) * User.Scale"),
                   ("Particles.Color", LCOL, None, "float4(0.08, 0.08, 0.08, 0.1 * sin(3.14159265 * saturate(Particles.NormalizedAge)))")])
    chk_renderers(S, em, [dict(kind="sprite", material="MI_LB_Mist", props={"Alignment": "Unaligned", "FacingMode": "FaceCamera"})])


def check_dust():
    S = Sys("NS_LB_ShaftDust")
    chk_sys(S)
    chk_user_vars(S, DUST_UVARS)
    chk(S.name + " emitters Dust", S.emitters() == ["Dust"], str(S.emitters()))
    chk_compile(S, gpu_emitters=("Dust",), emitters=("Dust",))
    em = "Dust"
    chk_emitter(S, em, "GPUComputeSim", local=True, bounds=DUST_BOUNDS)
    chk_rate(S, em, "User.Count / 10.0")
    chk_init(S, em, (8.0, 12.0), (1, 1, 1, 0), ("ru", 0.3, 0.8), "Dust")
    ci(S, em, PS, "ShapeLocation", "Shape Primitive", "enum", "Box")
    ci(S, em, PS, "ShapeLocation", "Box Size", "hlsl", "User.BoxExtent * 2.0", "Dust box size = User.BoxExtent * 2 (BoxExtent is the half-extent)")
    ci(S, em, PU, "CurlNoiseForce", "Noise Strength", "float", 20.0, "Dust curl noise strength 20")
    ci(S, em, PU, "Drag", "Drag", "float", 4.0, "Dust drag 4 (terminal speed 5 cm/s)")
    mods = S.module_names(em, PU)
    chk("Dust forces before SolveForcesAndVelocity", mods.index("CurlNoiseForce") < mods.index("SolveForcesAndVelocity") and mods.index("Drag") < mods.index("SolveForcesAndVelocity"), str(mods))
    cp(S, em, PU, [("Particles.Color", LCOL, None, "float4(1.0, 1.0, 1.0, sin(3.14159265 * saturate(Particles.NormalizedAge)))")])
    chk_renderers(S, em, [dict(kind="sprite", material="MI_LB_DustMote", props={"Alignment": "Unaligned", "FacingMode": "FaceCamera"})])


def check_watermist():
    S = Sys("NS_LB_WaterMist")
    chk_sys(S)
    chk_user_vars(S, MIST_UVARS)
    chk(S.name + " emitters Mist", S.emitters() == ["Mist"], str(S.emitters()))
    chk_compile(S, emitters=("Mist",))
    em = "Mist"
    chk_emitter(S, em, "CPUSim")
    chk_rate(S, em, "4.0")
    chk_init(S, em, 6.0, (1, 1, 1, 0), ("ru", 150.0, 300.0), "WaterMist")
    ci(S, em, PS, "ShapeLocation", "Box Size", "hlsl", "float3(User.Extent.x, User.Extent.y, 60.0)", "WaterMist box = User.Extent x 60 cm high")
    ci(S, em, PS, "ShapeLocation", "Offset", "hlsl", "float3(0.0, 0.0, 30.0)", "WaterMist box lifted 30 cm (Z 0-60)")
    ci(S, em, PS, "AddVelocity", "Velocity", "dyn", "RandomRangeVector", "WaterMist drift = RandomRangeVector +-5 cm/s")
    cp(S, em, PU, [("Particles.Color", LCOL, None, "float4(1.0, 1.0, 1.0, 0.6 * sin(3.14159265 * saturate(Particles.NormalizedAge)))")])
    chk_renderers(S, em, [dict(kind="sprite", material="MI_LB_WaterMist", props={"Alignment": "Unaligned", "FacingMode": "FaceCamera"})])


def check_drip_common(S, em):
    chk_emitter(S, em, "CPUSim", local=True)
    ci(S, em, PS, "InitializeParticle", "Sprite Size", "v2", (0.5, 5.0), "%s falling drop size (0.5, 5) cm" % S.name)
    cp(S, em, PS, DRIP_SPAWN)
    ci(S, em, PU, "GravityForce", "Gravity", "v3", (0, 0, DRIP_GRAVITY), "%s gravity -980" % S.name)
    mods = S.module_names(em, PU)
    chk("%s gravity before SolveForcesAndVelocity, 3 + 5 chain modules" % S.name, mods.index("GravityForce") < mods.index("SolveForcesAndVelocity") and len(mods) == 3 + len(DRIP_CHAIN), str(len(mods)))
    chk_chain(S, em, PU, DRIP_CHAIN, "SolveForcesAndVelocity")
    for row in DRIP_CHAIN:
        cp(S, em, PU, row)
    chk_renderers(S, em, [
        dict(kind="sprite", material="MI_LB_Rain", props={"Alignment": "VelocityAligned", "RendererVisibility": 0}, bind={"RendererVisibilityTagBinding": "VisibilityTag"}),
        dict(kind="sprite", material="MI_LB_Splash", props={"Alignment": "Unaligned", "FacingMode": "FaceCamera", "SubImageSize": {"x": 4, "y": 4}, "RendererVisibility": 1},
             bind={"RendererVisibilityTagBinding": "VisibilityTag", "ColorBinding": "CrownColor", "SpriteSizeBinding": "CrownSize", "SubImageIndexBinding": "SubImageIndex"}),
        dict(kind="sprite", material="MI_LB_Ripple", props={"Alignment": "Unaligned", "FacingMode": "CustomFacingVector", "RendererVisibility": 1},
             bind={"RendererVisibilityTagBinding": "VisibilityTag", "SpriteFacingBinding": "SpriteFacing", "SpriteSizeBinding": "RingSize", "ColorBinding": "RingColor"})])


def check_drip():
    S = Sys("NS_LB_Drip")
    chk_sys(S)
    chk_user_vars(S, [("User.FallHeight", "f", 500), ("User.Interval", "v2", (1.5, 4.0)), ("User.bWater", "b", False)])
    chk(S.name + " emitters Drop", S.emitters() == ["Drop"], str(S.emitters()))
    chk_compile(S, emitters=("Drop",))
    em = "Drop"
    check_drip_common(S, em)
    eu = S.module_names(em, EU)
    chk("Drip no SpawnRate; one burst per loop", "SpawnRate" not in eu and "SpawnBurst_Instantaneous" in eu, str(eu))
    ci(S, em, EU, "SpawnBurst_Instantaneous", "Spawn Count", "int", 1, "Drip burst of 1 drop per loop")
    ci(S, em, EU, "EmitterState", "Loop Behavior", "enum", "Infinite", "Drip emitter loops forever")
    ci(S, em, EU, "EmitterState", "Loop Duration", "dyn", "RandomRangeFloat", "Drip loop duration = RandomRangeFloat")
    ci(S, em, EU, "EmitterState", ["Loop Duration", "Minimum"], "hlsl", "User.Interval.x", "Drip loop duration min = User.Interval.x")
    ci(S, em, EU, "EmitterState", ["Loop Duration", "Maximum"], "hlsl", "User.Interval.y", "Drip loop duration max = User.Interval.y")
    ci(S, em, EU, "EmitterState", "Recalculate Duration Each Loop", "bool", True, "Drip interval re-rolled every loop")
    ci(S, em, EU, "EmitterState", "UseLoopDelay", "bool", True, "Drip random first delay on")
    ci(S, em, EU, "EmitterState", "Delay First Loop Only", "bool", True, "Drip delay applies to the first loop only")
    ci(S, em, EU, "EmitterState", ["Loop Delay", "Maximum"], "hlsl", "User.Interval.y", "Drip first delay max = User.Interval.y")
    ps = S.module_names(em, PS)
    chk("Drip spawns at the system origin (no ShapeLocation / AddVelocity)", "ShapeLocation" not in ps and "AddVelocity" not in ps, str(ps))


def check_eave():
    S = Sys("NS_LB_EaveDrips")
    chk_sys(S)
    chk_user_vars(S, [("User.LineLength", "f", 400), ("User.FallHeight", "f", 500), ("User.bWater", "b", False)])
    chk(S.name + " emitters Drops", S.emitters() == ["Drops"], str(S.emitters()))
    chk_compile(S, emitters=("Drops",))
    em = "Drops"
    check_drip_common(S, em)
    chk_rate(S, em, "6.0")
    ci(S, em, PS, "ShapeLocation", "Box Size", "hlsl", "float3(User.LineLength, 0.1, 0.1)", "Eave drops along local X, length User.LineLength")
    ci(S, em, PS, "ShapeLocation", "Offset", "hlsl", "float3(User.LineLength * 0.5, 0.0, 0.0)", "Eave line starts at the actor (offset = half length)")


CHECKERS = {"NS_LB_Rain": check_rain, "NS_LB_StrikeSparks": check_sparks, "NS_LB_TorchFire": check_torch, "NS_LB_ShaftDust": check_dust,
            "NS_LB_WaterMist": check_watermist, "NS_LB_Drip": check_drip, "NS_LB_EaveDrips": check_eave}


def cmd_check(a):
    E()
    for n in pick(a.only):
        print("== %s check ==" % n)
        try:
            CHECKERS[n]()
        except Exception as e:  # noqa: BLE001
            chk(n + " check ran to the end", False, "%s: %s" % (type(e).__name__, str(e)[:300]))
    for n in pick(a.only):
        print("INFO is_dirty %s %s" % (FOLDER + "/" + n, E().call(AS, "is_dirty", {"asset_path": FOLDER + "/" + n}, read=True)))
    print("RESULT: %d PASS, %d FAIL" % (_pass, _fail))
    return 1 if _fail else 0


def cmd_save(a):
    E()
    if E().call(EA, "IsPIERunning", {}, read=True):
        print("REFUSED: PIE is running")
        return 2
    bad = 0
    for n in pick(a.only):
        pkg = FOLDER + "/" + n
        assert n in BUILDERS and pkg.startswith("/Game/LastBell/FX/Niagara/NS_LB_") and "SmokeWisp" not in pkg
        r = E().call(AS, "save_assets", {"asset_paths": [pkg]})
        d = E().call(AS, "is_dirty", {"asset_path": pkg}, read=True)
        print("save %s -> %s; is_dirty after: %s" % (pkg, r, d))
        bad += 1 if d else 0
    return 1 if bad else 0


def cmd_list(_a):
    for n in BUILDERS:
        print(FOLDER + "/" + n)
    return 0


def cmd_build(a):
    E()
    if E().call(EA, "IsPIERunning", {}, read=True):
        print("REFUSED: PIE is running")
        return 2
    bad = 0
    for n in pick(a.only):
        del FAILS[:]
        print("=" * 20, n)
        S = BUILDERS[n]()
        cs, iss = report_compile(S)
        if FAILS or iss["numErrors"] or cs["bHasErrors"] or cs["aggregateStatus"] != "UpToDate":
            print("BUILD FAILED", n, FAILS)
            bad += 1
        else:
            print("BUILD OK", n, "(nothing saved)")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "check", "save", "list"])
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    return {"build": cmd_build, "check": cmd_check, "save": cmd_save, "list": cmd_list}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
