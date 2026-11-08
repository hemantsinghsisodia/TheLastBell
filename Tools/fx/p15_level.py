"""P15-6: the Phase 15 data assets and level work in L_Monastery (Docs/plans/P15_PARTICLES.md section 3, section 8, F0.1 to F0.14).

Run with the editor open on L_Monastery, PIE off (Windows Python, from PowerShell or Git Bash with MSYS_NO_PATHCONV=1):
    python -I Tools/fx/p15_level.py --apply [--resume] [--only data,target,dust,mist,drips,eaves,fires,flames,bpflames,cloth,curtains]
    python -I Tools/fx/p15_level.py --check [--only ...] [--start 3015]
    python -I Tools/fx/p15_level.py --save            (only when the full --check is all PASS and the census is 3065)

--apply is idempotent: every actor is found by its EXACT label (find_actors matches substrings, so the result is filtered) and updated,
or created when missing. --apply never saves. The census at the start must be 3015 (counted like p14_3_level.py --check --start);
--resume skips that guard so a partial run can be continued (a rerun finds what exists and finishes the rest).
--check only reads and prints PASS / FAIL per item (exit code 1 when any FAIL). EYE lines are numbers for the P15-7 look session.
--save saves, one package per save_assets call, each followed by is_dirty: DA_StormFX, DA_StormSettings, BP_LBCharacter (only when
it was changed), then the map. Never save-all. Never saves anything else.

If the editor crashes or a call hangs for more than 180 s the script stops ("STOP", exit code 3). Do not save and do not retry blindly.
"""
import argparse
import copy
import json
import math
import os
import statistics
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Tools", "lighting"))
import p14_3_level as L  # noqa: E402  (the Ed client, helpers and the NEVER_SAVE list)
from p14_3_level import EditorStop, J, R, v3, vec, xf, near, same_rot, diff_json  # noqa: E402

S, A, O, AS, E = L.S, L.A, L.O, L.AS, L.E
NC = "NiagaraToolsets.NiagaraToolset_Component"
SMT = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
BPT = "editor_toolset.toolsets.blueprint.BlueprintTools"
DAT = "editor_toolset.toolsets.data_asset.DataAssetTools"
MAP_PKG = L.MAP_PKG
FOLDER = "FX/Storm"
CENSUS_START = 3015
NEW_ACTORS = 1 + 11 + 2 + 10 + 7 + 10 + 8 + (6 - 5)      # 50: target, dust, mist, drips, eaves, cloth, curtains, fires (+6 -5)
SCRATCH = os.path.join(ROOT, "Saved", "p15_6_scratch")

# ---------------------------------------------------------------------------------------------- asset paths
FXN = "/Game/LastBell/FX/Niagara/"
FXM = "/Game/LastBell/FX/Meshes/"
FXI = "/Game/LastBell/Materials/Instances/FX/"


def obj(pkg):
    return pkg + "." + pkg.rsplit("/", 1)[-1]


NS = {n: obj(FXN + n) for n in ("NS_LB_Rain", "NS_LB_StrikeSparks", "NS_LB_TorchFire", "NS_LB_ShaftDust", "NS_LB_WaterMist", "NS_LB_Drip", "NS_LB_EaveDrips")}
SM = {n: obj(FXM + n) for n in ("SM_LB_FX_BoltCard", "SM_LB_FX_CurtainCard", "SM_LB_Prop_ClothStrip_A", "SM_LB_Prop_ClothStrip_B",
                                "SM_LB_Prop_ClothBanner_A", "SM_LB_Prop_ClothSheet_A")}
MI = {n: obj(FXI + n) for n in ("MI_LB_Bolt", "MI_Flame_Candle", "MI_Cloth_Linen_Dark", "MI_Cloth_Linen_Dark_Sheet", "MI_Cloth_Linen_Red", "MI_LB_RainCurtain")}
FLAME_MESH = "/Game/LastBell/Environments/Props/Procedural/Chapel/SM_LB_Prop_CandleFlame_A.SM_LB_Prop_CandleFlame_A"
DA_FX_PKG = "/Game/LastBell/Data/DA_StormFX"
DA_FX = obj(DA_FX_PKG)
DA_ST_PKG = "/Game/LastBell/Data/DA_StormSettings"
DA_ST = obj(DA_ST_PKG)
BP_CHAR_PKG = "/Game/LastBell/Blueprints/BP_LBCharacter"
BP_CHAR = obj(BP_CHAR_PKG)
BP_CHAR_FLAME = BP_CHAR + "_C:CandleFlame_GEN_VARIABLE"
STRIKE_TAG = "LB_StrikeTarget_Tower"

# ---------------------------------------------------------------------------------------------- Niagara user parameter types
FLOAT = "/Script/Niagara.NiagaraFloat"
BOOL = "/Script/Niagara.NiagaraBool"
V3T = "/Script/CoreUObject.Vector3f"
V2T = "/Script/CoreUObject.Vector2f"
KINDS = {"f": FLOAT, "b": BOOL, "v3": V3T, "v2": V2T}


def payload(kind, val):
    if kind == "f":
        body = {"value": float(val)}
    elif kind == "b":
        body = {"value": -1 if val else 0}
    elif kind == "v3":
        body = {"x": float(val[0]), "y": float(val[1]), "z": float(val[2])}
    else:
        body = {"x": float(val[0]), "y": float(val[1])}
    return {"struct": {"refPath": KINDS[kind]}, "value": body}


def unpack(kind, raw):
    v = raw["value"]["value"] if "value" in raw and isinstance(raw["value"], dict) and "value" in raw["value"] else raw
    if kind == "f":
        return float(v["value"])
    if kind == "b":
        return bool(v["value"])
    if kind == "v3":
        return (float(v["x"]), float(v["y"]), float(v["z"]))
    return (float(v["x"]), float(v["y"]))


# ---------------------------------------------------------------------------------------------- the plan's tables (all values from the plan)
# F0.6: label suffix, centre, rotation (P, Y, R), half-extent, count
DUST = [
    ("Ch_Shaft_Roof", (7271, 122.1, 944), (-38, 35, 0), (600, 120, 120), 120),
    ("Ch_Shaft_S1", (6882.7, -521, 365), (-38, 35, 0), (474.3, 30, 180), 120),
    ("Ch_Shaft_S2", (7882.7, -521, 365), (-38, 35, 0), (474.3, 30, 180), 120),
    ("Ch_Shaft_S3", (8882.7, -521, 365), (-38, 35, 0), (474.3, 30, 180), 120),
    ("SA_Crypt_G1", (8297.9, -2214, -325), (-12, -145, 180), (19.2, 19.2, 224), 80),
    ("SA_Crypt_G2", (9797.9, -2246.5, -325), (-12, -145, 180), (19.2, 19.2, 224), 80),
    ("SA_Crypt_G3", (10982.7, -1562.5, -265.5), (-22.7, -42.9, 180), (55, 55, 192), 80),
    ("SA_Tower_F03", (12638.2, 1636.7, 586.3), (-52, -145, 180), (11, 11, 172), 80),
    ("SA_Tower_F07", (12638.2, 1636.8, 1495.5), (-52, -145, 180), (11, 11, 172), 80),
    ("SA_Tower_F08", (12092.8, 2037, 1803.6), (-52, -145, 180), (11, 11, 64), 80),
    ("SA_Tower_Roof", (12443.3, 1866.8, 3783.5), (-52, -145, 180), (55, 55, 316), 80),
]
# F0.7
MIST = [("W", (9047.5, -2280, -593), (495, 390)), ("E", (10002.5, -2280, -593), (395, 390))]
# F0.8: tag, location, FallHeight, bWater
DRIPS = [
    ("W_9050", (9050, -2280, -105), 488, True), ("W_9200", (9200, -2280, -105), 488, True), ("Pit_9400", (9400, -2280, -105), 545, True),
    ("E_9900", (9900, -2280, -105), 488, True), ("E_10000", (10000, -2280, -105), 488, True),
    ("WC_a", (6450, -1900, -105), 495, False), ("SC_b", (7250, -2350, -105), 495, False), ("NC_a", (10250, -900, -105), 495, False),
    ("Belfry_N_wall", (12600, 2440, 3700.9), 1200.9, False), ("Belfry_NW_corner", (12100, 2400, 3793.1), 1293.1, False),
]
# F0.9: id, start, yaw, LineLength, FallHeight
EAVES = [
    ("CyN", (2200, 1296, 454), 0, 200, 453), ("CyS_A", (4200, -1313, 476), 0, 400, 475), ("CyS_B", (4800, -1313, 476), 0, 200, 475),
    ("ClS", (11380, 1423, 637), 180, 1100, 537), ("ClN1", (10320, 2177, 637), 0, 400, 537), ("ClW", (10323, 1420, 637), 90, 800, 537),
    ("ClE", (11377, 2180, 637), -90, 800, 537),
]
# F0.2: new label, replaces (None = nothing), location, User.Scale
FIRES = [
    ("FX_Torch_Fire_NS", "FX_Torch_Fire", (327, 1600, 250), 1.0),
    ("FX_Crypt_Torch_T1_NS", "FX_Crypt_Torch_T1", (6321, -1100, -380), 1.0),
    ("FX_Crypt_Torch_T2_NS", "FX_Crypt_Torch_T2", (8979, -2700, -380), 1.0),
    ("FX_Crypt_Torch_T3_NS", "FX_Crypt_Torch_T3", (11150, -721, -380), 1.0),
    ("FX_Crypt_Brazier_NS", "FX_Crypt_Brazier", (11000, -2299.1, -459.4), 1.8),
    ("FX_FirePit_Fire", None, (1150, 1650, 25), 1.4),
]
FIRES_STAY = ["FX_FirePit_Smoke", "Light_FirePit_Ember", "L_Crypt_Torch_T1", "L_Crypt_Torch_T2", "L_Crypt_Torch_T3"]
# F0.1: the 22 flame StaticMeshActors
FLAMES_CHAPEL = ["Ch_AltarFlame_N1_F", "Ch_AltarFlame_N2_F", "Ch_AltarFlame_N3_F", "Ch_AltarFlame_S1_F", "Ch_AltarFlame_S2_F", "Ch_AltarFlame_S3_F",
                 "Ch_RitualFlame_1_F", "Ch_RitualFlame_2_F", "Ch_RitualFlame_4_F", "Ch_SillFlame_S2_1_F", "Ch_StatueHolder_Flame_1",
                 "Ch_StatueHolder_Flame_2", "Sa_Flame_2_F"]
FLAMES_CRYPT = ["CD_Candles_Niche_E_CC_Flame", "CD_Candles_Niche_E_WC_Flame", "CD_Candles_Niche_N_SC_Flame", "CD_Candles_Niche_S_FP_Flame",
                "CD_Candles_Niche_S_NC_Flame", "CD_Candles_Puzzle_E_Flame", "CD_Candles_Puzzle_W_Flame", "CD_Candles_Sarc_0_Flame", "CD_Candles_Sarc_1_Flame"]
FLAMES = FLAMES_CHAPEL + FLAMES_CRYPT
PUZZLE_CANDLES = ["Candle_P1", "Candle_P2", "Candle_P3", "Candle_P4"]
# F0.10: id, mesh, top-centre location, rotation (P, Y, R), MI
CLOTH = [
    ("Belfry_W1", "SM_LB_Prop_ClothStrip_A", (12046, 1905, 3180), (0, -90, 0), "MI_Cloth_Linen_Dark"),
    ("Belfry_N2", "SM_LB_Prop_ClothBanner_A", (12595, 2454, 3180), (0, 180, 0), "MI_Cloth_Linen_Red"),
    ("Belfry_E1", "SM_LB_Prop_ClothStrip_B", (12954, 2095, 3180), (0, 90, 0), "MI_Cloth_Linen_Dark"),
    ("Belfry_S2", "SM_LB_Prop_ClothStrip_A", (12405, 1546, 3180), (0, 0, 0), "MI_Cloth_Linen_Dark"),
    ("Slit_F03", "SM_LB_Prop_ClothStrip_B", (12500, 1546, 778.1), (0, 0, 0), "MI_Cloth_Linen_Dark"),
    ("Slit_F07", "SM_LB_Prop_ClothStrip_B", (12500, 1546, 1687.3), (0, 0, 0), "MI_Cloth_Linen_Dark"),
    ("Cloister_N_1", "SM_LB_Prop_ClothBanner_A", (10750, 2256, 555), (0, 0, 0), "MI_Cloth_Linen_Red"),
    ("Cloister_W_1", "SM_LB_Prop_ClothSheet_A", (10244, 1850, 520), (0, 90, 0), "MI_Cloth_Linen_Dark_Sheet"),
    ("Cloister_S_2", "SM_LB_Prop_ClothStrip_A", (11050, 1344, 555), (0, 180, 0), "MI_Cloth_Linen_Dark"),
    ("Gate_Inner", "SM_LB_Prop_ClothStrip_A", (306, 400, 600), (0, -90, 0), "MI_Cloth_Linen_Dark"),
]
CLOTH_WPO = 4000.0
CLOISTER_ARCHES = {"Cloister_N_1": "CLA_Arch_N_1", "Cloister_W_1": "CLA_Arch_W_1", "Cloister_S_2": "CLA_Arch_S_2"}
# F0.11
CURTAINS = [
    ("N_600", (600, 4800, -200), (0, 180, 0)), ("N_2400", (2400, 4800, -200), (0, 180, 0)), ("N_4200", (4200, 4800, -200), (0, 180, 0)),
    ("N_6000", (6000, 4800, -200), (0, 180, 0)), ("N_8000", (8000, 4800, -200), (0, 180, 0)), ("N_11500", (11500, 4800, -200), (0, 180, 0)),
    ("N_14500", (14500, 4800, -200), (0, 180, 0)), ("S_11500", (11500, -4800, -200), (0, 0, 0)),
]
CURTAIN_SCALE = (30, 1, 25)
TARGET = ("FX_StrikeTarget_Tower", (12530.8, 2000.0, 4844.8))
# section 2.2 defaults (the C++ constructor values; DebugBolt -1)
FX_DEFAULTS = {"bRain": True, "RainSpawnRate": 35000.0, "RainBoxHalfXY": 1800.0, "RainSpawnHeight": 2500.0, "RainWindLean": 500.0, "SplashRate": 2500.0,
               "SplashRadius": 1200.0, "MistMinExposure": 0.6, "SkyBoltDistance": 60000.0, "SkyBoltTopHeight": 22000.0, "BoltAspect": 0.35,
               "StrikeSkyHeight": 12000.0, "StrikeSkyOffset": 2500.0, "StrikeWidth": 1400.0, "BoltAtlasCount": 8, "BoltMaxSeconds": 2.5, "BoltPool": 4,
               "DebugBolt": -1}
FX_DEFAULT_VEC2 = {"RainFallSpeed": (1100.0, 1400.0), "SkyBoltLength": (16000.0, 26000.0)}
FX_DEFAULT_CHANCE = {"ambient": 0.6, "scripted": 1.0, "wardenReveal": 0.5, "apparition": 0.5, "debug": 1.0}
STRIKE_TRIGGERS = ("State.Event.CourtyardEntered", "State.Event.TowerTop")
NEVER_SAVE = list(L.NEVER_SAVE) + ["/Game/LastBell/Blueprints/Puzzles/BP_PuzzleCandle"]

results = []


def rec(ok, msg):
    results.append((bool(ok), msg))
    print(("PASS  " if ok else "FAIL  ") + msg, flush=True)
    return bool(ok)


def info(msg):
    print("INFO  " + msg, flush=True)


def eye(msg):
    print("EYE   " + msg, flush=True)


def rnd(v, n=2):
    return [round(float(x), n) for x in v]


def rname(x):
    r = R(x)
    return r.rsplit(".", 1)[-1] if r else None


# ---------------------------------------------------------------------------------------------- the editor client
class Ed(L.Ed):
    """p14_3_level.Ed plus asset spawns, Niagara variables, tags, folders and removal."""

    def get_or_create(self, cls, label, loc, rot=(0, 0, 0), sc=(1, 1, 1), folder=FOLDER):
        # p14_3_level.Ed binds its own FOLDER as the default argument, so pass ours explicitly
        return super().get_or_create(cls, label, loc, rot, sc, folder)

    def spawn_asset(self, asset, label, loc, rot=(0, 0, 0), sc=(1, 1, 1), folder=FOLDER):
        a = self.call(S, "add_to_scene_from_asset", {"asset_path": asset, "name": label, "xform": xf(loc, rot, sc)})
        ref = R(a)
        if not ref:
            raise RuntimeError("spawn of %s (%s) returned %r" % (label, asset, a))
        self.call(A, "set_label", {"actor": {"refPath": ref}, "label": label})
        self._labels[ref] = label
        if folder:
            self.call(S, "set_actor_folder", {"actor": {"refPath": ref}, "folder_path": folder})
        return ref

    def get_or_create_asset(self, asset, label, loc, rot=(0, 0, 0), sc=(1, 1, 1)):
        ref = self.find_one(label)
        if ref:
            return ref, False
        return self.spawn_asset(asset, label, loc, rot, sc), True

    def folder_actors(self, folder=FOLDER):
        try:
            return set(R(x) for x in self.call(S, "get_actors_in_folder", {"folder_path": folder}) or [])
        except RuntimeError:
            return set()

    def nset(self, ref, name, kind, val):
        self.call(NC, "SetVariable", {"component": {"refPath": ref + ".NiagaraComponent0"},
                                      "variable": {"name": name, "type": {"classStructOrEnum": {"refPath": KINDS[kind]}}, "value": payload(kind, val)}})

    def nget(self, ref, name, kind):
        r = self.call(NC, "GetVariable", {"component": {"refPath": ref + ".NiagaraComponent0"},
                                          "var": {"name": name, "type": {"classStructOrEnum": {"refPath": KINDS[kind]}}}})
        return unpack(kind, r)

    def set_axes(self, ref, prop, target, tol=1e-3):
        """Set a vector property one axis per call with a PARTIAL struct ({"y": v}): on placed Blueprint instances a full-vector write applies
        only the first changed axis (P15-6), a partial one applies exactly the axis given. Reads back; returns True when all axes match."""
        for _ in range(3):
            cur = v3(self.props(ref, [prop])[prop])
            if near(cur, target, tol):
                return True
            for i, ax in enumerate("xyz"):
                if abs(cur[i] - target[i]) > tol:
                    self.setp(ref, {prop: {ax: target[i]}})
        return near(v3(self.props(ref, [prop])[prop]), target, tol)

    def tags(self, ref):
        return list(self.props(ref, ["tags"]).get("tags") or [])

    def remove(self, ref):
        return self.call(S, "remove_from_scene", {"actor": {"refPath": ref}})

    def class_of(self, ref):
        return R(self.call(O, "get_class", {"instance": {"refPath": ref}}))


def same_val(kind, a, b, tol=1e-3):
    if kind == "b":
        return bool(a) == bool(b)
    if kind == "f":
        return abs(a - b) <= tol
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def set_uvars(ed, ref, uvars):
    """Write the user parameters and read each back; returns the list of mismatches."""
    bad = []
    for name, kind, val in uvars:
        ed.nset(ref, name, kind, val)
        got = ed.nget(ref, name, kind)
        if not same_val(kind, got, val):
            bad.append((name, val, got))
    return bad


def place_ns(ed, system, label, loc, rot, uvars, sc=(1, 1, 1)):
    ref, created = ed.get_or_create_asset(NS[system], label, loc, rot, sc)
    ed.set_xform(ref, loc, rot, sc)
    asset = R(ed.props(ref + ".NiagaraComponent0", ["asset"]).get("asset"))
    if asset != NS[system]:
        # a NiagaraActor spawned from the asset carries it; if not, SetSystem is the supported call
        ed.call(NC, "SetSystem", {"niagaraComponent": {"refPath": ref + ".NiagaraComponent0"}, "system": {"refPath": NS[system]}, "bResetExistingOverrideParameters": False})
    bad = set_uvars(ed, ref, uvars)
    info("%s %s at %s rot %s%s" % (label, "created" if created else "updated", rnd(loc, 2), rnd(rot, 2), ("  USER-PARAM READ-BACK MISMATCH %s" % bad) if bad else ""))
    return ref


def check_ns(ed, label, system, loc, rot, uvars, folder_set, sc=(1, 1, 1)):
    ref = ed.find_one(label)
    if not ref:
        return rec(False, "%s exists" % label)
    l, r, s = ed.xform(ref)
    asset = R(ed.props(ref + ".NiagaraComponent0", ["asset"]).get("asset"))
    cls = ed.class_of(ref)
    bad = []
    got_s = []
    for name, kind, val in uvars:
        got = ed.nget(ref, name, kind)
        got_s.append((name.replace("User.", ""), got if not isinstance(got, tuple) else tuple(round(x, 3) for x in got)))
        if not same_val(kind, got, val):
            bad.append(name)
    ok = (near(l, loc, 0.01) and same_rot(r, rot) and near(s, sc, 1e-6) and asset == NS[system] and cls == "/Script/Niagara.NiagaraActor"
          and not bad and ref in folder_set)
    return rec(ok, "%s %s loc %s rot %s scale %s asset %s folder %s params %s%s" % (
        label, cls.rsplit(".", 1)[-1], rnd(l, 2), rnd(r, 2), rnd(s, 3), (asset or "None").rsplit(".", 1)[-1], FOLDER if ref in folder_set else "NOT-IN-FOLDER", got_s,
        ("  MISMATCH " + str(bad)) if bad else ""))


def sm_props(ed, ref, names):
    return ed.props(ref + ".StaticMeshComponent0", names)


def mat_name(p):
    if not p.get("overrideMaterials"):
        return None
    return rname(p["overrideMaterials"][0])


# ---------------------------------------------------------------------------------------------- 1. data
def fx_state(ed):
    names = list(FX_DEFAULTS) + list(FX_DEFAULT_VEC2) + ["SkyBoltChance", "RainSystem", "StrikeSparksSystem", "BoltMesh", "BoltMaterial"]
    return ed.props(DA_FX, names)


def apply_data(ed):
    if not ed.call(AS, "exists", {"path": DA_FX_PKG}):
        r = ed.call(DAT, "create", {"folder_path": "/Game/LastBell/Data", "asset_name": "DA_StormFX", "asset_type": {"refPath": "/Script/LastBell.LBStormFXSettings"}})
        info("created DA_StormFX: %s" % (r,))
    else:
        info("DA_StormFX already exists")
    ed.setp(DA_FX, {"RainSystem": {"refPath": NS["NS_LB_Rain"]}, "StrikeSparksSystem": {"refPath": NS["NS_LB_StrikeSparks"]},
                    "BoltMesh": {"refPath": SM["SM_LB_FX_BoltCard"]}, "BoltMaterial": {"refPath": MI["MI_LB_Bolt"]}})
    st = fx_state(ed)
    info("DA_StormFX after the 4 soft refs: RainSystem %s, StrikeSparksSystem %s, BoltMesh %s, BoltMaterial %s" % (
        st["RainSystem"], st["StrikeSparksSystem"], st["BoltMesh"], st["BoltMaterial"]))
    # DA_StormSettings
    os.makedirs(SCRATCH, exist_ok=True)
    p = ed.props(DA_ST, ["FXSettings", "DebugFreezeFlash", "DebugIntensityOverride", "ScriptedStrikes"])
    path = os.path.join(SCRATCH, "strikes_before.json")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(p["ScriptedStrikes"], f, indent=1)
        info("saved the BEFORE ScriptedStrikes array to %s" % path)
    before = json.load(open(path, encoding="utf-8"))
    info("ScriptedStrikes BEFORE (%d entries): %s" % (len(before), json.dumps(before)))
    cur = p["ScriptedStrikes"]
    new = copy.deepcopy(cur)
    for e in new:
        if e["triggerTag"]["tagName"] in STRIKE_TRIGGERS:
            e["strikeTargetTag"] = STRIKE_TAG
    if new != cur:
        ed.setp(DA_ST, {"ScriptedStrikes": new})
    else:
        info("ScriptedStrikes already carry the strike target tag")
    if rname(p["FXSettings"]) != "DA_StormFX":
        ed.setp(DA_ST, {"FXSettings": {"refPath": DA_FX}})
    after = ed.props(DA_ST, ["FXSettings", "ScriptedStrikes"])
    info("DA_StormSettings.FXSettings = %s" % after["FXSettings"])
    info("ScriptedStrikes AFTER (%d entries): %s" % (len(after["ScriptedStrikes"]), json.dumps(after["ScriptedStrikes"])))


def check_data(ed):
    rec(bool(ed.call(AS, "exists", {"path": DA_FX_PKG})), "DA_StormFX exists at %s" % DA_FX_PKG)
    st = fx_state(ed)
    refs = [("RainSystem", NS["NS_LB_Rain"]), ("StrikeSparksSystem", NS["NS_LB_StrikeSparks"]), ("BoltMesh", SM["SM_LB_FX_BoltCard"]), ("BoltMaterial", MI["MI_LB_Bolt"])]
    for k, want in refs:
        rec(R(st[k]) == want, "DA_StormFX.%s -> %s" % (k, R(st[k])))
    bad = {k: (st[k], v) for k, v in FX_DEFAULTS.items() if (st[k] != v if isinstance(v, bool) else abs(float(st[k]) - float(v)) > 1e-4)}
    rec(not bad, "DA_StormFX section 2.2 scalar defaults intact (%d fields; mismatches %s)" % (len(FX_DEFAULTS), bad))
    badv = {k: (st[k], v) for k, v in FX_DEFAULT_VEC2.items() if abs(st[k]["x"] - v[0]) > 1e-3 or abs(st[k]["y"] - v[1]) > 1e-3}
    rec(not badv, "DA_StormFX vector defaults intact (RainFallSpeed %s, SkyBoltLength %s; mismatches %s)" % (st["RainFallSpeed"], st["SkyBoltLength"], badv))
    ch = st["SkyBoltChance"]
    rec(set(ch) == set(FX_DEFAULT_CHANCE) and all(abs(ch[k] - v) < 1e-5 for k, v in FX_DEFAULT_CHANCE.items()), "DA_StormFX.SkyBoltChance %s" % ch)
    rec(st["DebugBolt"] == -1, "DA_StormFX.DebugBolt = %s (must be -1)" % st["DebugBolt"])
    p = ed.props(DA_ST, ["FXSettings", "DebugFreezeFlash", "DebugIntensityOverride", "ScriptedStrikes"])
    rec(R(p["FXSettings"]) == DA_FX, "DA_StormSettings.FXSettings -> %s" % R(p["FXSettings"]))
    rec(p["DebugFreezeFlash"] == -1 and p["DebugIntensityOverride"] == -1, "DA_StormSettings DebugFreezeFlash %s, DebugIntensityOverride %s (must be -1)" % (
        p["DebugFreezeFlash"], p["DebugIntensityOverride"]))
    path = os.path.join(SCRATCH, "strikes_before.json")
    if os.path.exists(path):
        before = json.load(open(path, encoding="utf-8"))
        d = diff_json(before, p["ScriptedStrikes"])
        want = []
        for i, e in enumerate(before):
            if e["triggerTag"]["tagName"] in STRIKE_TRIGGERS:
                want.append("[%d].strikeTargetTag %r != %r" % (i, e["strikeTargetTag"], STRIKE_TAG))
        rec(len(before) == len(p["ScriptedStrikes"]) and sorted(d) == sorted(want) and len(want) == 2,
            "ScriptedStrikes: only the two strikeTargetTag fields differ from before (%d entries; diff %s)" % (len(p["ScriptedStrikes"]), d))
    else:
        info("no strikes_before.json in %s: the field-by-field diff is not possible in this run" % SCRATCH)
        for e in p["ScriptedStrikes"]:
            want = STRIKE_TAG if e["triggerTag"]["tagName"] in STRIKE_TRIGGERS else "None"
            rec(e["strikeTargetTag"] == want, "strike %s strikeTargetTag %s" % (e["triggerTag"]["tagName"], e["strikeTargetTag"]))


# ---------------------------------------------------------------------------------------------- 2. strike target
def apply_target(ed):
    label, loc = TARGET
    ref, created = ed.get_or_create("/Script/Engine.TargetPoint", label, loc)
    ed.set_xform(ref, loc, (0, 0, 0), (1, 1, 1))
    ed.call(S, "set_actor_folder", {"actor": {"refPath": ref}, "folder_path": FOLDER})
    if STRIKE_TAG not in ed.tags(ref):
        ed.call(A, "add_tag", {"actor": {"refPath": ref}, "tag": STRIKE_TAG})
    info("%s %s at %s tags %s" % (label, "created" if created else "updated", loc, ed.tags(ref)))
    report_target(ed)


def report_target(ed):
    roof = ed.find_one("TWA_Roof", must=True)
    b = ed.bounds(roof)
    eye("strike target tip: TWA_Roof bounds min %s max %s; max Z %.2f; target Z %.2f; gap target - roof max Z = %.2f cm (plan: 20 cm above the finial tip)" % (
        rnd(b[0], 1), rnd(b[1], 1), b[1][2], TARGET[1][2], TARGET[1][2] - b[1][2]))
    eye("strike target XY (%.1f, %.1f); TWA_Roof bounds XY centre (%.1f, %.1f)" % (TARGET[1][0], TARGET[1][1], (b[0][0] + b[1][0]) / 2, (b[0][1] + b[1][1]) / 2))


def check_target(ed):
    label, loc = TARGET
    ref = ed.find_one(label)
    if not ref:
        return rec(False, "%s exists" % label)
    l, r, s = ed.xform(ref)
    tags = ed.tags(ref)
    cls = ed.class_of(ref)
    ok_f = ref in ed.folder_actors()
    rec(near(l, loc, 0.01) and STRIKE_TAG in tags and cls == "/Script/Engine.TargetPoint" and ok_f,
        "%s %s loc %s tags %s folder %s" % (label, cls.rsplit(".", 1)[-1], rnd(l, 2), tags, FOLDER if ok_f else "NOT-IN-FOLDER"))
    n = len(ed.find_all(tag=STRIKE_TAG))
    rec(n == 1, "exactly one actor carries the tag %s (%d)" % (STRIKE_TAG, n))
    report_target(ed)


# ---------------------------------------------------------------------------------------------- 3. dust
def dust_vars(row):
    _, _, _, half, count = row
    return [("User.BoxExtent", "v3", half), ("User.Count", "f", count)]


def apply_dust(ed):
    for row in DUST:
        place_ns(ed, "NS_LB_ShaftDust", "FX_Dust_" + row[0], row[1], row[2], dust_vars(row))


def check_dust(ed):
    fs = ed.folder_actors()
    for row in DUST:
        check_ns(ed, "FX_Dust_" + row[0], "NS_LB_ShaftDust", row[1], row[2], dust_vars(row), fs)


# ---------------------------------------------------------------------------------------------- 4. water mist
def apply_mist(ed):
    for tag, loc, ext in MIST:
        place_ns(ed, "NS_LB_WaterMist", "FX_WaterMist_" + tag, loc, (0, 0, 0), [("User.Extent", "v2", ext)])


def check_mist(ed):
    fs = ed.folder_actors()
    for tag, loc, ext in MIST:
        check_ns(ed, "FX_WaterMist_" + tag, "NS_LB_WaterMist", loc, (0, 0, 0), [("User.Extent", "v2", ext)], fs)


# ---------------------------------------------------------------------------------------------- 5. drips
def drip_vars(row):
    return [("User.FallHeight", "f", row[2]), ("User.bWater", "b", row[3])]


def apply_drips(ed):
    for row in DRIPS:
        place_ns(ed, "NS_LB_Drip", "FX_Drip_" + row[0], row[1], (0, 0, 0), drip_vars(row))
    report_drips(ed)


def report_drips(ed):
    cands = {}
    for key in ("CA_Vault", "TWA_Roof"):
        for r in ed.find_all(name=key):
            lab = ed.label(r)
            if lab.startswith(key):
                cands[lab] = r
    bounds = {lab: ed.bounds(r) for lab, r in cands.items()}
    for row in DRIPS:
        tag, loc = row[0], row[1]
        hit = [(lab, b) for lab, b in bounds.items() if b[0][0] - 1 <= loc[0] <= b[1][0] + 1 and b[0][1] - 1 <= loc[1] <= b[1][1] + 1]
        if tag.startswith("Belfry"):
            hit = [(lab, b) for lab, b in hit if lab.startswith("TWA_Roof")]
        else:
            hit = [(lab, b) for lab, b in hit if lab.startswith("CA_Vault")]
        if not hit:
            eye("drip %s at %s: no overhead mesh among %d candidates contains its XY" % (tag, rnd(loc, 1), len(bounds)))
            continue
        for lab, b in hit:
            eye("drip %s at %s: overhead %s bounds Z %.1f..%.1f (XY %s..%s); point Z - mesh min Z = %.1f cm; mesh max Z - point Z = %.1f cm" % (
                tag, rnd(loc, 1), lab, b[0][2], b[1][2], rnd(b[0][:2], 0), rnd(b[1][:2], 0), loc[2] - b[0][2], b[1][2] - loc[2]))


def check_drips(ed):
    fs = ed.folder_actors()
    for row in DRIPS:
        check_ns(ed, "FX_Drip_" + row[0], "NS_LB_Drip", row[1], (0, 0, 0), drip_vars(row), fs)
    report_drips(ed)


# ---------------------------------------------------------------------------------------------- 6. eaves
def eave_vars(row):
    return [("User.LineLength", "f", row[3]), ("User.FallHeight", "f", row[4])]


def apply_eaves(ed):
    for row in EAVES:
        place_ns(ed, "NS_LB_EaveDrips", "FX_EaveDrips_" + row[0], row[1], (0, row[2], 0), eave_vars(row))


def check_eaves(ed):
    fs = ed.folder_actors()
    for row in EAVES:
        check_ns(ed, "FX_EaveDrips_" + row[0], "NS_LB_EaveDrips", row[1], (0, row[2], 0), eave_vars(row), fs)


# ---------------------------------------------------------------------------------------------- 7. fires
def apply_fires(ed):
    for new, old, loc, scale in FIRES:
        ref = place_ns(ed, "NS_LB_TorchFire", new, loc, (0, 0, 0), [("User.Scale", "f", scale)])
        # read back location and User.Scale again, and only then delete the Cascade actor
        l, r, s = ed.xform(ref)
        got = ed.nget(ref, "User.Scale", "f")
        ok = near(l, loc, 0.01) and abs(got - scale) < 1e-3
        info("%s read-back: location %s, User.Scale %s -> %s" % (new, rnd(l, 2), got, "OK" if ok else "MISMATCH (Cascade actor NOT deleted)"))
        if not old or not ok:
            continue
        hits = ed.find(old)
        if not hits:
            info("%s: Cascade actor already gone" % old)
            continue
        if len(hits) > 1:
            raise RuntimeError("label %r exists %d times" % (old, len(hits)))
        cls = ed.class_of(hits[0])
        if cls != "/Script/Engine.Emitter":
            raise RuntimeError("%s is %s, not an Emitter: not deleting" % (old, cls))
        res = ed.remove(hits[0])
        info("deleted Cascade actor %s (%s): %s" % (old, hits[0].rsplit(":", 1)[-1], res))


def check_fires(ed):
    fs = ed.folder_actors()
    for new, old, loc, scale in FIRES:
        check_ns(ed, new, "NS_LB_TorchFire", loc, (0, 0, 0), [("User.Scale", "f", scale)], fs)
        if old:
            rec(not ed.find(old), "Cascade actor %s is gone" % old)
    for lab in FIRES_STAY:
        rec(bool(ed.find(lab)), "%s still exists (point lights, light functions and the smoke wisp stay)" % lab)


# ---------------------------------------------------------------------------------------------- 8. flames (level StaticMeshActors)
def apply_flames(ed):
    for lab in FLAMES:
        ref = ed.find_one(lab, must=True)
        comp = ref + ".StaticMeshComponent0"
        mesh = R(ed.props(comp, ["staticMesh"])["staticMesh"])
        if mesh != FLAME_MESH:
            raise RuntimeError("%s uses mesh %s, not the candle flame mesh: stop" % (lab, mesh))
        ed.setp(comp, {"overrideMaterials": [{"refPath": MI["MI_Flame_Candle"]}]})
        p = sm_props(ed, ref, ["staticMesh", "overrideMaterials"])
        info("%s override %s mesh %s" % (lab, [rname(m) for m in p["overrideMaterials"]], rname(p["staticMesh"])))


def check_flames(ed):
    bad = []
    for lab in FLAMES:
        ref = ed.find_one(lab)
        if not ref:
            bad.append(lab + " (missing)")
            continue
        p = sm_props(ed, ref, ["staticMesh", "overrideMaterials"])
        if not (R(p["staticMesh"]) == FLAME_MESH and len(p["overrideMaterials"]) >= 1 and R(p["overrideMaterials"][0]) == MI["MI_Flame_Candle"]):
            bad.append("%s (mesh %s, override %s)" % (lab, rname(p["staticMesh"]), [rname(m) for m in p["overrideMaterials"]]))
    rec(not bad, "%d flame StaticMeshActors: mesh SM_LB_Prop_CandleFlame_A unchanged, slot-0 override MI_Flame_Candle (failures %s)" % (len(FLAMES), bad))
    # the shared assets must be untouched
    mi = J(ed.call("editor_toolset.toolsets.object.ObjectTools", "get_properties",
                   {"instance": {"refPath": "/Game/LastBell/Materials/Instances/MI_LB_CandleFlame.MI_LB_CandleFlame"}, "properties": ["parent", "vectorParameterValues"]}))
    info("MI_LB_CandleFlame (must be untouched): parent %s vector params %s" % (rname(mi.get("parent")), json.dumps(mi.get("vectorParameterValues"))))


# ---------------------------------------------------------------------------------------------- 9. Blueprint flames
def mesh_zrange(ed, mesh):
    b = J(ed.call(SMT, "get_bounds", {"mesh": {"refPath": mesh}}))
    return v3(b["min"]), v3(b["max"])


def chapel_median_height(ed):
    hs = []
    for lab in FLAMES_CHAPEL:
        b = ed.bounds(ed.find_one(lab, must=True))
        hs.append(b[1][2] - b[0][2])
    return statistics.median(hs), hs


def comp_world_box(mesh_min, mesh_max, rel_loc, rel_scale, frame_t, frame_s):
    """World (or reporting-frame) box of a component with zero rotation under a parent frame (translation, scale)."""
    lo = [frame_t[i] + frame_s[i] * (rel_loc[i] + rel_scale[i] * mesh_min[i]) for i in range(3)]
    hi = [frame_t[i] + frame_s[i] * (rel_loc[i] + rel_scale[i] * mesh_max[i]) for i in range(3)]
    return lo, hi


def bpflame_plan(ed, old_mesh, old_loc, old_scale, frame_t, frame_s, new_mesh_rng, med):
    """New relative scale and Z so that the world height is `med` (a uniform world scale) and the new min Z sits on the old min Z."""
    omin, omax = mesh_zrange(ed, old_mesh)
    old_lo, old_hi = comp_world_box(omin, omax, old_loc, old_scale, frame_t, frame_s)
    nmin, nmax = new_mesh_rng
    s_world = med / (nmax[2] - nmin[2])
    rel_scale = [s_world / frame_s[i] for i in range(3)]
    rel_z = (old_lo[2] - frame_t[2]) / frame_s[2] - rel_scale[2] * nmin[2]
    return old_lo, old_hi, rel_scale, rel_z, s_world


def before_store():
    path = os.path.join(SCRATCH, "bpflames_before.json")
    return path, (json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {})


def apply_bpflames(ed):
    os.makedirs(SCRATCH, exist_ok=True)
    path, store = before_store()
    med, hs = chapel_median_height(ed)
    new_rng = mesh_zrange(ed, FLAME_MESH)
    info("graph check: BP_PuzzleCandle graphs (UserConstructionScript, RefreshLit, TintBand, OnWorldStateChanged, EventGraph) and BP_LBCharacter graphs "
         "(UserConstructionScript, EventGraph) were read with find_nodes/get_node_infos: no node sets the Flame/CandleFlame mesh or material "
         "(RefreshLit only calls SetVisibility on Flame/FlameLight; TintBand sets a Color vector on BandRing only); no C++ references CandleFlame")
    info("chapel flame median world height %.3f cm over %d actors (min %.3f max %.3f); flame mesh local Z %s..%s" % (
        med, len(hs), min(hs), max(hs), new_rng[0][2], new_rng[1][2]))
    # --- the four puzzle candles
    for lab in PUZZLE_CANDLES:
        ref = ed.find_one(lab, must=True)
        loc, rot, sc = ed.xform(ref)
        if not (near(rot, (0, 0, 0), 1e-4) and near(sc, (1, 1, 1), 1e-5)):
            raise RuntimeError("%s has rotation %s scale %s: the plan assumes none" % (lab, rot, sc))
        comp = ref + ".Flame"
        p = ed.props(comp, ["staticMesh", "overrideMaterials", "relativeLocation", "relativeScale3D"])
        if lab not in store:
            store[lab] = {"mesh": R(p["staticMesh"]), "mats": [R(m) for m in p["overrideMaterials"]], "relLoc": v3(p["relativeLocation"]),
                          "relScale": v3(p["relativeScale3D"])}
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                json.dump(store, f, indent=1)
        b0 = store[lab]
        old_lo, old_hi, rel_scale, rel_z, s_world = bpflame_plan(ed, b0["mesh"], b0["relLoc"], b0["relScale"], loc, (1, 1, 1), new_rng, med)
        info("%s before: mesh %s mats %s relLoc %s relScale %s -> world box %s..%s (height %.3f)" % (
            lab, b0["mesh"].rsplit(".", 1)[-1], [m.rsplit(".", 1)[-1] for m in b0["mats"]], rnd(b0["relLoc"], 3), rnd(b0["relScale"], 4), rnd(old_lo, 3), rnd(old_hi, 3),
            old_hi[2] - old_lo[2]))
        attempts = 0
        while attempts < 2:
            attempts += 1
            ed.setp(comp, {"staticMesh": {"refPath": FLAME_MESH}})
            ed.setp(comp, {"overrideMaterials": [{"refPath": MI["MI_Flame_Candle"]}]})
            ed.set_axes(comp, "relativeScale3D", rel_scale, 1e-4)
            ed.set_axes(comp, "relativeLocation", [b0["relLoc"][0], b0["relLoc"][1], rel_z], 1e-3)
            if bpflame_ok(ed, comp, rel_scale, rel_z, b0["relLoc"]):
                break
        else:
            info("%s: the instance edits did not persist after 2 attempts: LEFT AS IT IS and listed" % lab)
    # --- the player's candle (template)
    apply_player_flame(ed, med, new_rng)


def bpflame_ok(ed, comp, rel_scale, rel_z, old_rel_loc):
    p = ed.props(comp, ["staticMesh", "overrideMaterials", "relativeLocation", "relativeScale3D"])
    return (R(p["staticMesh"]) == FLAME_MESH and p["overrideMaterials"] and R(p["overrideMaterials"][0]) == MI["MI_Flame_Candle"]
            and near(v3(p["relativeScale3D"]), rel_scale, 1e-3) and near(v3(p["relativeLocation"]), [old_rel_loc[0], old_rel_loc[1], rel_z], 5e-3))


def player_frame(ed):
    """The reporting frame is the `Candle` scene component; the flame's parent (CandleWax) gives translation and scale (no rotation)."""
    par = R(ed.call(A, "get_parent_component", {"component": {"refPath": BP_CHAR_FLAME}}))
    pp = ed.props(par, ["relativeLocation", "relativeScale3D", "relativeRotation"])
    rot = pp["relativeRotation"]
    if abs(rot["pitch"]) + abs(rot["yaw"]) + abs(rot["roll"]) > 1e-4:
        raise RuntimeError("the flame's parent is rotated: stop")
    gp = R(ed.call(A, "get_parent_component", {"component": {"refPath": par}}))
    if not gp.endswith(":Candle"):
        raise RuntimeError("the flame's grandparent is %s, not Candle: stop" % gp)
    return par, v3(pp["relativeLocation"]), v3(pp["relativeScale3D"])


def apply_player_flame(ed, med, new_rng):
    path, store = before_store()
    key = "BP_LBCharacter.CandleFlame"
    p = ed.props(BP_CHAR_FLAME, ["staticMesh", "overrideMaterials", "relativeLocation", "relativeScale3D"])
    par, ft, fs = player_frame(ed)
    if key not in store:
        store[key] = {"mesh": R(p["staticMesh"]), "mats": [R(m) for m in p["overrideMaterials"]], "relLoc": v3(p["relativeLocation"]),
                      "relScale": v3(p["relativeScale3D"]), "frameT": ft, "frameS": fs}
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(store, f, indent=1)
    b0 = store[key]
    old_lo, old_hi, rel_scale, rel_z, s_world = bpflame_plan(ed, b0["mesh"], b0["relLoc"], b0["relScale"], b0["frameT"], b0["frameS"], new_rng, med)
    info("%s before: mesh %s mats %s relLoc %s relScale %s; parent %s translation %s scale %s -> Candle-space box %s..%s (height %.3f)" % (
        key, b0["mesh"].rsplit(".", 1)[-1], [m.rsplit(".", 1)[-1] for m in b0["mats"]], rnd(b0["relLoc"], 3), rnd(b0["relScale"], 4), par.rsplit(":", 1)[-1],
        rnd(b0["frameT"], 3), rnd(b0["frameS"], 3), rnd(old_lo, 3), rnd(old_hi, 3), old_hi[2] - old_lo[2]))
    info("%s plan: world scale %.4f -> relative scale %s (non-uniform because the parent scale is non-uniform; a uniform relative scale would stretch the flame), relative Z %.4f" % (
        key, s_world, rnd(rel_scale, 4), rel_z))
    if bpflame_ok(ed, BP_CHAR_FLAME, rel_scale, rel_z, b0["relLoc"]):
        info("%s template already carries the new values" % key)
        return
    # baseline compile (clean?) before the edit
    try:
        ed.call(BPT, "compile_blueprint", {"blueprint": {"refPath": BP_CHAR}, "warnings_as_errors": True})
        base = "clean"
    except RuntimeError as e:
        base = "baseline compile reported: " + str(e)[:300]
    info("BP_LBCharacter baseline compile (warnings as errors): %s" % base)
    done = False
    for attempt in (1, 2):
        ed.setp(BP_CHAR_FLAME, {"staticMesh": {"refPath": FLAME_MESH}})
        ed.setp(BP_CHAR_FLAME, {"overrideMaterials": [{"refPath": MI["MI_Flame_Candle"]}]})
        ed.set_axes(BP_CHAR_FLAME, "relativeScale3D", rel_scale, 1e-4)
        ed.set_axes(BP_CHAR_FLAME, "relativeLocation", [b0["relLoc"][0], b0["relLoc"][1], rel_z], 1e-3)
        if bpflame_ok(ed, BP_CHAR_FLAME, rel_scale, rel_z, b0["relLoc"]):
            done = True
            break
        info("BP_LBCharacter template edit attempt %d did not read back" % attempt)
    if not done:
        info("BP_LBCharacter.CandleFlame could not be edited over MCP in 2 attempts: LEFT AS IT IS and listed (restoring the old values)")
        ed.setp(BP_CHAR_FLAME, {"staticMesh": {"refPath": b0["mesh"]}})
        ed.setp(BP_CHAR_FLAME, {"overrideMaterials": [{"refPath": m} for m in b0["mats"]]})
        return
    try:
        ed.call(BPT, "compile_blueprint", {"blueprint": {"refPath": BP_CHAR}, "warnings_as_errors": True})
        info("BP_LBCharacter compile after the edit (warnings as errors): clean")
    except RuntimeError as e:
        info("BP_LBCharacter compile after the edit FAILED: %s" % str(e)[:500])


def check_bpflames(ed):
    path, store = before_store()
    if not store:
        info("no bpflames_before.json in %s: before/after numbers are not available in this run" % SCRATCH)
    med, _ = chapel_median_height(ed)
    new_rng = mesh_zrange(ed, FLAME_MESH)
    h_mesh = new_rng[1][2] - new_rng[0][2]
    for lab in PUZZLE_CANDLES:
        ref = ed.find_one(lab)
        if not ref:
            rec(False, "%s exists" % lab)
            continue
        loc, rot, sc = ed.xform(ref)
        p = ed.props(ref + ".Flame", ["staticMesh", "overrideMaterials", "relativeLocation", "relativeScale3D"])
        rl, rs = v3(p["relativeLocation"]), v3(p["relativeScale3D"])
        lo, hi = comp_world_box(new_rng[0], new_rng[1], rl, rs, loc, (1, 1, 1))
        h = hi[2] - lo[2]
        b0 = store.get(lab)
        ok_mesh = R(p["staticMesh"]) == FLAME_MESH and p["overrideMaterials"] and R(p["overrideMaterials"][0]) == MI["MI_Flame_Candle"]
        ok_h = abs(h - med) <= 0.05 * med
        ok_uni = max(rs) - min(rs) < 1e-4
        ok_z = True
        if b0:
            olo, ohi = comp_world_box(*mesh_zrange(ed, b0["mesh"]), b0["relLoc"], b0["relScale"], loc, (1, 1, 1))
            ok_z = abs(lo[2] - olo[2]) <= 0.5 and near(rl[:2], b0["relLoc"][:2], 1e-3)
            old_s = "before box %s..%s (h %.3f); " % (rnd(olo, 3), rnd(ohi, 3), ohi[2] - olo[2])
        else:
            old_s = ""
        rec(ok_mesh and ok_h and ok_uni and ok_z, "%s.Flame mesh %s mat %s relScale %s relLoc %s; %safter box %s..%s (h %.3f, median %.3f, h/median %.3f)" % (
            lab, rname(p["staticMesh"]), mat_name(p), rnd(rs, 4), rnd(rl, 3), old_s, rnd(lo, 3), rnd(hi, 3), h, med, h / med))
    key = "BP_LBCharacter.CandleFlame"
    p = ed.props(BP_CHAR_FLAME, ["staticMesh", "overrideMaterials", "relativeLocation", "relativeScale3D"])
    par, ft, fs = player_frame(ed)
    rl, rs = v3(p["relativeLocation"]), v3(p["relativeScale3D"])
    lo, hi = comp_world_box(new_rng[0], new_rng[1], rl, rs, ft, fs)
    b0 = store.get(key)
    ok_mesh = R(p["staticMesh"]) == FLAME_MESH and p["overrideMaterials"] and R(p["overrideMaterials"][0]) == MI["MI_Flame_Candle"]
    ok_h = abs((hi[2] - lo[2]) - med) <= 0.05 * med
    ok_z = True
    old_s = ""
    if b0:
        olo, ohi = comp_world_box(*mesh_zrange(ed, b0["mesh"]), b0["relLoc"], b0["relScale"], b0["frameT"], b0["frameS"])
        ok_z = abs(lo[2] - olo[2]) <= 0.5
        old_s = "before Candle-space box %s..%s (h %.3f); " % (rnd(olo, 3), rnd(ohi, 3), ohi[2] - olo[2])
    rec(ok_mesh and ok_h and ok_z, "%s template: mesh %s mat %s relScale %s relLoc %s; %safter Candle-space box %s..%s (h %.3f, median %.3f)" % (
        key, rname(p["staticMesh"]), mat_name(p), rnd(rs, 4), rnd(rl, 3), old_s, rnd(lo, 3), rnd(hi, 3), hi[2] - lo[2], med))
    info("Saint1..4Flame cones of BP_StainedGlassClue_Saints were not touched")


# ---------------------------------------------------------------------------------------------- 10. cloth
def place_sm(ed, mesh, label, loc, rot, sc, mat, extra):
    ref, created = ed.get_or_create_asset(SM[mesh] if mesh in SM else mesh, label, loc, rot, sc)
    ed.set_xform(ref, loc, rot, sc)
    vals = {"bUseDefaultCollision": False, "bodyInstance": {"collisionProfileName": "NoCollision", "collisionEnabled": "NoCollision"}}
    vals.update(extra)
    if mat:
        vals["overrideMaterials"] = [{"refPath": MI[mat]}]
    ed.setp(ref + ".StaticMeshComponent0", vals)
    return ref, created


def apply_cloth(ed):
    for cid, mesh, loc, rot, mat in CLOTH:
        ref, created = place_sm(ed, mesh, "FX_Cloth_" + cid, loc, rot, (1, 1, 1), mat, {"worldPositionOffsetDisableDistance": CLOTH_WPO})
        info("%s %s mesh %s mat %s at %s rot %s" % ("FX_Cloth_" + cid, "created" if created else "updated", mesh, mat, loc, rot))
    report_cloth(ed)


def report_cloth(ed):
    for cid, arch in CLOISTER_ARCHES.items():
        row = [r for r in CLOTH if r[0] == cid][0]
        ref = ed.find_one(arch)
        if not ref:
            eye("cloister cloth %s: arch actor %s not found" % (cid, arch))
            continue
        b = ed.bounds(ref)
        eye("cloister cloth %s top centre %s: arcade mesh %s bounds %s..%s; cloth top Z %.1f vs mesh max Z %.1f (outer ring top; the intrados crown is estimated at about Z 585)" % (
            cid, rnd(row[2], 1), arch, rnd(b[0], 1), rnd(b[1], 1), row[2][2], b[1][2]))


def sm_state(ed, ref):
    p = sm_props(ed, ref, ["staticMesh", "overrideMaterials", "bUseDefaultCollision", "bodyInstance", "worldPositionOffsetDisableDistance", "castShadow", "mobility"])
    return p


def check_cloth(ed):
    fs = ed.folder_actors()
    for cid, mesh, loc, rot, mat in CLOTH:
        lab = "FX_Cloth_" + cid
        ref = ed.find_one(lab)
        if not ref:
            rec(False, "%s exists" % lab)
            continue
        l, r, s = ed.xform(ref)
        p = sm_state(ed, ref)
        bi = p["bodyInstance"]
        ok = (near(l, loc, 0.01) and same_rot(r, rot) and near(s, (1, 1, 1), 1e-6) and R(p["staticMesh"]) == SM[mesh] and mat_name(p) == mat
              and bi["collisionProfileName"] == "NoCollision" and bi["collisionEnabled"] == "NoCollision" and p["bUseDefaultCollision"] is False
              and abs(p["worldPositionOffsetDisableDistance"] - CLOTH_WPO) < 1e-3 and ref in fs)
        rec(ok, "%s loc %s rot %s scale %s mesh %s mat %s collision %s/%s WPO-disable %s castShadow %s mobility %s folder %s" % (
            lab, rnd(l, 2), rnd(r, 2), rnd(s, 3), rname(p["staticMesh"]), mat_name(p), bi["collisionProfileName"], bi["collisionEnabled"],
            p["worldPositionOffsetDisableDistance"], p["castShadow"], p["mobility"], FOLDER if ref in fs else "NOT-IN-FOLDER"))
    report_cloth(ed)


# ---------------------------------------------------------------------------------------------- 11. rain curtains
def apply_curtains(ed):
    slots = ed.call(SMT, "get_material_slots", {"mesh": {"refPath": SM["SM_LB_FX_CurtainCard"]}})
    info("SM_LB_FX_CurtainCard material slots: %s, slot 0 default %s" % (json.dumps(slots), R(ed.call(SMT, "get_material", {"mesh": {"refPath": SM["SM_LB_FX_CurtainCard"]}, "slot_name": slots[0]}))))
    for cid, loc, rot in CURTAINS:
        ref, created = place_sm(ed, "SM_LB_FX_CurtainCard", "FX_RainCurtain_" + cid, loc, rot, CURTAIN_SCALE, None, {"castShadow": False})
        info("%s %s at %s rot %s scale %s" % ("FX_RainCurtain_" + cid, "created" if created else "updated", loc, rot, CURTAIN_SCALE))


def check_curtains(ed):
    fs = ed.folder_actors()
    slots = ed.call(SMT, "get_material_slots", {"mesh": {"refPath": SM["SM_LB_FX_CurtainCard"]}})
    default = R(ed.call(SMT, "get_material", {"mesh": {"refPath": SM["SM_LB_FX_CurtainCard"]}, "slot_name": slots[0]}))
    rec(len(slots) == 1 and default == MI["MI_LB_RainCurtain"], "SM_LB_FX_CurtainCard slots %s, slot 0 default material %s (want MI_LB_RainCurtain)" % (slots, default))
    for cid, loc, rot in CURTAINS:
        lab = "FX_RainCurtain_" + cid
        ref = ed.find_one(lab)
        if not ref:
            rec(False, "%s exists" % lab)
            continue
        l, r, s = ed.xform(ref)
        p = sm_state(ed, ref)
        bi = p["bodyInstance"]
        ok = (near(l, loc, 0.01) and same_rot(r, rot) and near(s, CURTAIN_SCALE, 1e-5) and R(p["staticMesh"]) == SM["SM_LB_FX_CurtainCard"] and not p["overrideMaterials"]
              and bi["collisionProfileName"] == "NoCollision" and bi["collisionEnabled"] == "NoCollision" and p["castShadow"] is False and ref in fs)
        rec(ok, "%s loc %s rot %s scale %s mesh %s override %s collision %s/%s castShadow %s folder %s" % (
            lab, rnd(l, 2), rnd(r, 2), rnd(s, 3), rname(p["staticMesh"]), mat_name(p), bi["collisionProfileName"], bi["collisionEnabled"], p["castShadow"],
            FOLDER if ref in fs else "NOT-IN-FOLDER"))


# ---------------------------------------------------------------------------------------------- census, dirty state, save
def census(ed):
    return len(ed.find_all())


def check_census(ed, start):
    n = census(ed)
    rec(n == start + NEW_ACTORS, "actor census %d (start %d + %d = %d)" % (n, start, NEW_ACTORS, start + NEW_ACTORS))
    fx = len([r for r in ed.folder_actors()])
    info("%d actors in the outliner folder %s (new actors: %d)" % (fx, FOLDER, NEW_ACTORS))
    return n


def check_dirty(ed):
    info("%s is_dirty = %s" % (MAP_PKG, ed.is_dirty(MAP_PKG)))
    for pkg in (DA_FX_PKG, DA_ST_PKG, BP_CHAR_PKG):
        info("%s is_dirty = %s" % (pkg.rsplit("/", 1)[-1], ed.is_dirty(pkg)))
    for pkg in NEVER_SAVE:
        rec(not ed.is_dirty(pkg), "%s is not dirty (never-save list)" % pkg.rsplit("/", 1)[-1])


def do_save(ed, start):
    print("=== save: full check first", flush=True)
    for s in STEPS:
        CHECK[s](ed)
    n = check_census(ed, start)
    check_dirty(ed)
    fails = [m for ok, m in results if not ok]
    if fails or n != start + NEW_ACTORS:
        print("REFUSED: the check is not all PASS or the census is wrong; nothing saved")
        return False
    # the debug fields were verified at -1 by check_data
    order = [DA_FX_PKG, DA_ST_PKG]
    if ed.is_dirty(BP_CHAR_PKG):
        order.append(BP_CHAR_PKG)
    else:
        info("BP_LBCharacter is not dirty: not saved")
    order.append(MAP_PKG)
    for pkg in order:
        r = ed.call(AS, "save_assets", {"asset_paths": [pkg]})
        d = ed.is_dirty(pkg)
        rec(d is False, "saved %s (save_assets -> %s); is_dirty after = %s" % (pkg, r, d))
    for pkg in NEVER_SAVE:
        rec(not ed.is_dirty(pkg), "%s still not dirty" % pkg.rsplit("/", 1)[-1])
    return True


STEPS = ["data", "target", "dust", "mist", "drips", "eaves", "fires", "flames", "bpflames", "cloth", "curtains"]
APPLY = {"data": apply_data, "target": apply_target, "dust": apply_dust, "mist": apply_mist, "drips": apply_drips, "eaves": apply_eaves, "fires": apply_fires,
         "flames": apply_flames, "bpflames": apply_bpflames, "cloth": apply_cloth, "curtains": apply_curtains}
CHECK = {"data": check_data, "target": check_target, "dust": check_dust, "mist": check_mist, "drips": check_drips, "eaves": check_eaves, "fires": check_fires,
         "flames": check_flames, "bpflames": check_bpflames, "cloth": check_cloth, "curtains": check_curtains}


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--apply", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--save", action="store_true")
    ap.add_argument("--only", default="", help="comma list of: " + ",".join(STEPS))
    ap.add_argument("--start", type=int, default=CENSUS_START, help="actor count before P15-6 (F0.14: 3015)")
    ap.add_argument("--resume", action="store_true", help="--apply: skip the census-is-3015 guard (continue a partial run)")
    a = ap.parse_args()
    steps = [s for s in STEPS if not a.only or s in a.only.split(",")]
    bad = [s for s in a.only.split(",") if s and s not in STEPS]
    if bad:
        sys.exit("unknown step(s): %s" % bad)
    try:
        ed = Ed()
        if ed.call(E, "IsPIERunning"):
            sys.exit("PIE is running: stop it first (spawned actors would go to the PIE world)")
        lvl = str(ed.call(S, "get_current_level", {}))
        if not lvl.startswith(MAP_PKG):
            sys.exit("the editor is on %s, not L_Monastery" % lvl)
        dirty0 = ed.is_dirty(MAP_PKG)
        n0 = census(ed)
        info("preflight: PIE off; %s is_dirty = %s; actor census = %d" % (MAP_PKG, dirty0, n0))
        if a.apply:
            if n0 != a.start and not a.resume:
                print("STOP: the census is %d, not %d. Nothing applied. (Use --resume only to continue a run of this script.)" % (n0, a.start))
                sys.exit(2)
            for s in steps:
                print("=== apply %s" % s, flush=True)
                APPLY[s](ed)
            print("=== verifying", flush=True)
            for s in steps:
                print("=== check %s" % s, flush=True)
                CHECK[s](ed)
            info("census after apply: %d (start %d + %d = %d); map is_dirty: %s" % (census(ed), a.start, NEW_ACTORS, a.start + NEW_ACTORS, ed.is_dirty(MAP_PKG)))
        elif a.check:
            for s in steps:
                print("=== check %s" % s, flush=True)
                CHECK[s](ed)
            if not a.only:
                check_census(ed, a.start)
                check_dirty(ed)
        else:
            do_save(ed, a.start)
        info("%d editor calls" % ed.calls)
    except EditorStop as e:
        print("STOP: editor problem (%s). Do NOT save. Restart the editor if it crashed, then run --apply --resume again." % e)
        sys.exit(3)
    fails = [m for ok, m in results if not ok]
    print("\nRESULT: %d PASS, %d FAIL" % (len(results) - len(fails), len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
