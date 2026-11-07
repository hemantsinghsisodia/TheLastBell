"""P14 F0: READ-ONLY lighting survey of L_Monastery (Docs/plans/P14_LIGHTING_STORM.md, task F0).

Run (editor open on L_Monastery, PIE off):
    python -I Tools/lighting/p14_f0_survey.py [--resume]

Editor calls used (all read-only): IsPIERunning, get_current_level, is_dirty, find_actors, get_label,
get_actor_transform, get_actor_bounds, get_root_component, get_components, get_properties, find_assets,
get_referencers, get_material_slots, get_material, trace_world. Nothing is written to the level, an asset
or the viewport camera.

Outputs: Docs/ArtTest/lighting/p14_f0_inventory.json (and p14_f0_tables.md via --tables, or at the end).
Cache: Saved/p14_f0_cache.jsonl (one JSON line per finished step; --resume reuses it).
"""
import argparse
import json
import math
import os
import re
import sys
import time
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Tools", "mcp"))
from ue import UE  # noqa: E402

S = "editor_toolset.toolsets.scene.SceneTools"
A = "editor_toolset.toolsets.actor.ActorTools"
O = "editor_toolset.toolsets.object.ObjectTools"
AS = "editor_toolset.toolsets.asset.AssetTools"
SM = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
E = "EditorToolset.EditorAppToolset"
MAP_PKG = "/Game/LastBell/Maps/L_Monastery"
OUT_DIR = os.path.join(ROOT, "Docs", "ArtTest", "lighting")
CACHE = os.path.join(ROOT, "Saved", "p14_f0_cache.jsonl")
POSES = os.path.join(ROOT, "Tools", "materials", "poses", "p11_poses.json")

LIGHT_CLASSES = {"PointLight", "SpotLight", "RectLight", "DirectionalLight", "SkyLight"}
LIGHT_PROPS = ["intensity", "intensityUnits", "lightColor", "attenuationRadius", "sourceRadius", "softSourceRadius",
               "sourceLength", "castShadows", "castVolumetricShadow", "innerConeAngle", "outerConeAngle",
               "volumetricScatteringIntensity", "lightFunctionMaterial", "indirectLightingIntensity", "mobility",
               "bVisible", "bAffectsWorld", "temperature", "bUseTemperature", "lightSourceAngle", "sourceType",
               "lightingChannels", "specularScale", "bUseInverseSquaredFalloff", "lightFalloffExponent"]
SMA_PROPS = ["staticMesh", "overrideMaterials", "mobility", "castShadow", "worldPositionOffsetDisableDistance",
             "bEvaluateWorldPositionOffset", "bVisible", "bHiddenInGame", "shadowCacheInvalidationBehavior"]
ISM_PROPS = SMA_PROPS + ["perInstanceSMData", "instanceStartCullDistance", "instanceEndCullDistance"]
MASTERS = ["M_LB_StainedGlass", "M_LB_StainedGlass_Translucent", "M_LB_LightShaft", "M_LB_Decal_LightPool",
           "M_LB_Decal_Chalk", "M_LB_Foliage", "M_LB_FoliageMasked"]
SKY_ENGINE = "/Engine/EngineSky/M_Sky_Panning_Clouds2"

# Labels the plan names (sections 7.1 and 8). Each must exist exactly once.
PLAN_LIGHTS = {
    "moon": ["DirectionalLight", "Moon_Fill", "SkyLight"],
    "moon_spot": ["Light_Chapel_Moon_S1", "Light_Chapel_Moon_S2", "Light_Chapel_Moon_S3", "Light_Chapel_Moon_Roof",
                  "L_Crypt_Moon_G1", "L_Crypt_Moon_G2", "L_Crypt_Moon_G3",
                  "L_Tw_MoonSlit_F03", "L_Tw_MoonSlit_F07", "L_Tw_MoonSlit_F08"],
    "fill": ["L_Tw_BellFill"],
    "SLG_Chapel_Altar": ["Light_Chapel_Altar_N", "Light_Chapel_Altar_S"],
    "SLG_Chapel_Dais": ["Light_Chapel_Statue", "Light_Chapel_DaisFill"],
    "SLG_Cloister_Bells": ["L_Cl_Bells"],
    "SLG_Cloister_West": ["L_Cl_West"],
    "SLG_Cloister_Entry": ["L_Cl_Entry"],
    "SLG_Tower_Landings": ["L_Tw_Land4", "L_Tw_Land7", "L_Tw_Land10"],
    "SLG_Tower_Bell": ["L_Tw_Bell"],
}
NEW_NAMES = ["SZN_", "SLG_", "RV_", "PP_Chapel", "PP_Tower", "SM_LB_LeakBlocker"]
VIEWPOINTS = ["cy_west_front_15m", "cy_tall_north_15m", "cy_lantern_gate_3m", "ch_tall_east_15m", "ch_candle_altar_3m",
              "ch_sacristy_3m", "cr_tall_ossuary_15m", "cr_chain_chamber", "cr_torch_t1_3m", "cl_tall_north_15m",
              "cl_lantern_bells_3m", "ps_lantern_joints", "tw_mid_stair", "tw_belfry"]
NOT_READABLE = ("could not be read", "not found", "not a valid", "Failed to find", "does not exist", "No such",
                "Could not find", "Invalid")

J = lambda x: json.loads(x) if isinstance(x, str) else x  # noqa: E731


def R(x):
    if isinstance(x, dict):
        x = x.get("refPath")
    if not x or x in ("None", "null"):
        return None
    return x


def short(ref):
    return ref.rsplit(".", 1)[-1].rsplit("/", 1)[-1] if ref else None


def pkg(ref):
    return ref.rsplit(".", 1)[0] if ref and "." in ref.rsplit("/", 1)[-1] else ref


def oname(ref):
    return ref.split("PersistentLevel.", 1)[1] if "PersistentLevel." in ref else ref.rsplit(".", 1)[-1]


def cls_of(ref):
    n = re.sub(r"_\d+$", "", oname(ref))
    return "PCGV" if n.startswith("PCGV_") else n


def v3(d, keys="xyz"):
    return [round(float(d[k]), 1) for k in keys]


def area_of(x, y, z):
    if x >= 6300 and -2950 <= y <= 520 and z < -45:
        return "crypt"
    if 11990 <= x <= 13010 and 1490 <= y <= 2510:
        return "tower"
    if 9460 <= x <= 12040 and 500 <= y <= 3040:
        return "cloister"
    if 6040 <= x < 9460 and 900 <= y <= 2600:
        return "passage"
    if 6000 <= x <= 9100 and -1550 <= y <= 860:
        return "chapel"
    if 300 <= x < 6000 and -2600 <= y <= 2600:
        return "courtyard"
    if x < 300:
        return "approach"
    return "other"


class Survey:
    def __init__(self, resume):
        self.ue = UE()
        self.calls = 0
        self.errors = []
        self.cache = {}
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        if resume and os.path.exists(CACHE):
            for line in open(CACHE, encoding="utf-8"):
                if line.strip():
                    try:
                        d = json.loads(line)
                        self.cache[d["k"]] = d["v"]
                    except Exception:
                        pass
        elif os.path.exists(CACHE):
            os.replace(CACHE, CACHE + ".old")
        self.cf = open(CACHE, "a", encoding="utf-8")
        self.t0 = time.time()

    # ------------------------------------------------------------------ plumbing
    def call(self, ts, tool, args=None):
        last = None
        for _ in range(3):
            try:
                self.calls += 1
                return self.ue.call(ts, tool, args or {})
            except RuntimeError as e:
                msg = str(e)
                if any(s in msg for s in NOT_READABLE):
                    raise
                last = msg[:300]
            except Exception as e:
                last = "%s: %s" % (type(e).__name__, str(e)[:200])
                time.sleep(3)
                try:
                    self.ue = UE()
                except Exception:
                    pass
                continue
            time.sleep(2)
        raise RuntimeError("FAILED %s.%s: %s" % (ts.rsplit(".", 1)[-1], tool, last))

    def try_call(self, ts, tool, args, ctx):
        try:
            return self.call(ts, tool, args)
        except RuntimeError as e:
            self.errors.append({"ctx": ctx, "tool": tool, "error": str(e)[:300]})
            return None

    def getp(self, ref, names):
        """get_properties, dropping names the server says it can't read (up to 12 rounds)."""
        names = list(names)
        for _ in range(12):
            if not names:
                return {}
            try:
                return J(self.call(O, "get_properties", {"instance": {"refPath": ref}, "properties": names}))
            except RuntimeError as e:
                m = re.search(r"could not be read: (.*)$", str(e))
                if not m:
                    self.errors.append({"ctx": ref, "tool": "get_properties", "error": str(e)[:300]})
                    return {}
                bad = [x.strip() for x in m.group(1).replace("'", "").split(",")]
                left = [x for x in names if x not in bad]
                if len(left) == len(names):
                    return {}
                names = left
        return {}

    def step(self, key, fn):
        if key in self.cache:
            return self.cache[key]
        v = fn()
        self.cache[key] = v
        self.cf.write(json.dumps({"k": key, "v": v}) + "\n")
        self.cf.flush()
        return v

    def log(self, msg):
        print("[%6.0fs, %5d calls] %s" % (time.time() - self.t0, self.calls, msg), flush=True)

    def label(self, ref):
        return self.step("label:" + ref, lambda: self.try_call(A, "get_label", {"actor": {"refPath": ref}}, ref))

    def xform(self, ref):
        def f():
            t = self.try_call(A, "get_actor_transform", {"actor": {"refPath": ref}}, ref)
            t = J(t) if t else None
            return {"loc": v3(t["location"]), "rot": v3(t["rotation"], ("pitch", "yaw", "roll")),
                    "scale": v3(t["scale"])} if t else None
        return self.step("xf:" + ref, f)

    def bounds(self, ref):
        def f():
            b = self.try_call(A, "get_actor_bounds", {"actor": {"refPath": ref}}, ref)
            b = J(b) if b else None
            return {"min": v3(b["min"]), "max": v3(b["max"])} if b and b.get("isValid", True) else None
        return self.step("bounds:" + ref, f)

    def trace(self, a, b):
        key = "trace:%s>%s" % (",".join("%.0f" % x for x in a), ",".join("%.0f" % x for x in b))

        def f():
            r = self.try_call(S, "trace_world", {"start": dict(zip("xyz", a)), "end": dict(zip("xyz", b))}, key)
            if isinstance(r, dict):
                r = r.get("returnValue", r.get("distance"))
            return None if r in (None, "None", "null") else float(r)
        return self.step(key, f)

    # ------------------------------------------------------------------ stages
    def header(self):
        return {"pie": self.call(E, "IsPIERunning"), "level": self.call(S, "get_current_level", {}),
                "dirty_before": self.call(AS, "is_dirty", {"asset_path": MAP_PKG}),
                "time": time.strftime("%Y-%m-%d %H:%M:%S")}

    def actors(self):
        found = [x["refPath"] for x in self.call(S, "find_actors", {"name": "", "tag": "", "collision_channels": []})]
        return {"refs": found, "count": len(found), "by_class": dict(Counter(cls_of(r) for r in found).most_common())}

    def light(self, ref):
        def f():
            rec = {"ref": ref, "class": cls_of(ref), "label": self.label(ref), "xf": self.xform(ref)}
            ap = self.getp(ref, ["tags"])
            rec["tags"] = ap.get("tags") or []
            root = R(J(self.try_call(A, "get_root_component", {"actor": {"refPath": ref}}, ref) or "null"))
            rec["component"] = oname(root) if root else None
            p = self.getp(root, LIGHT_PROPS) if root else {}
            if p.get("lightFunctionMaterial") is not None:
                p["lightFunctionMaterial"] = short(R(p["lightFunctionMaterial"]))
            rec["props"] = p
            x, y, z = rec["xf"]["loc"] if rec["xf"] else (0, 0, 0)
            rec["area"] = area_of(x, y, z)
            return rec
        return self.step("light:" + ref, f)

    def bp_lights(self, ref):
        def f():
            comps = J(self.try_call(A, "get_components", {"actor": {"refPath": ref}}, ref) or "[]") or []
            out = []
            for c in comps:
                cr = R(c)
                if cr and re.search(r"Light", oname(cr).rsplit(".", 1)[-1]) and not re.search(r"Arrow|Billboard|Sprite", cr):
                    p = self.getp(cr, ["intensity", "attenuationRadius", "mobility", "castShadows", "bVisible"])
                    if p:
                        out.append({"component": cr.rsplit(".", 1)[-1], "props": p})
            return {"ref": ref, "label": self.label(ref), "class": cls_of(ref), "lights": out} if out else None
        return self.step("bplights:" + ref, f)

    def pp(self, ref):
        def f():
            p = self.getp(ref, ["priority", "blendRadius", "blendWeight", "bUnbound", "bEnabled", "settings", "tags"])
            st = p.pop("settings", {}) or {}
            on = {k[len("bOverride_"):] for k, v in st.items() if k.startswith("bOverride_") and v}
            keep = {}
            for k, v in st.items():
                kk = k[0].upper() + k[1:]
                if kk in on or k in on:
                    keep[k] = v
            return {"ref": ref, "label": self.label(ref), "bounds": self.bounds(ref), "props": p,
                    "overrides": sorted(on), "values": keep}
        return self.step("pp:" + ref, f)

    def sma(self, ref):
        def f():
            p = self.getp(ref + ".StaticMeshComponent0", SMA_PROPS)
            comp = "StaticMeshComponent0"
            if not p.get("staticMesh"):
                root = R(J(self.try_call(A, "get_root_component", {"actor": {"refPath": ref}}, ref) or "null"))
                if root:
                    p = self.getp(root, SMA_PROPS)
                    comp = oname(root).rsplit(".", 1)[-1]
            ov = [short(R(o)) for o in (p.get("overrideMaterials") or [])]
            return {"mesh": short(R(p.get("staticMesh"))), "mesh_ref": R(p.get("staticMesh")), "ov": ov, "comp": comp,
                    "mob": p.get("mobility"), "shadow": p.get("castShadow"),
                    "wpo_dist": p.get("worldPositionOffsetDisableDistance"),
                    "wpo_eval": p.get("bEvaluateWorldPositionOffset"), "vis": p.get("bVisible"),
                    "hig": p.get("bHiddenInGame"), "sci": p.get("shadowCacheInvalidationBehavior")}
        return self.step("sma:" + ref, f)

    def decal(self, ref):
        def f():
            p = self.getp(ref + ".NewDecalComponent", ["decalMaterial", "decalSize"])
            if not p:
                root = R(J(self.try_call(A, "get_root_component", {"actor": {"refPath": ref}}, ref) or "null"))
                p = self.getp(root, ["decalMaterial", "decalSize"]) if root else {}
            return {"mat": short(R(p.get("decalMaterial"))), "size": p.get("decalSize")}
        return self.step("decal:" + ref, f)

    def mi(self, path):
        ref = path if "." in path.rsplit("/", 1)[-1] else path + "." + path.rsplit("/", 1)[-1]

        def f():
            p = self.getp(ref, ["parent", "scalarParameterValues", "textureParameterValues", "vectorParameterValues",
                                "blendMode", "materialDomain", "twoSided", "bUsedWithInstancedStaticMeshes"])
            out = {"path": pkg(ref), "parent": short(R(p.get("parent"))), "parent_path": pkg(R(p.get("parent")))}
            out["scalars"] = {e["parameterInfo"]["name"]: e["parameterValue"] for e in p.get("scalarParameterValues") or []}
            out["vectors"] = {e["parameterInfo"]["name"]: [round(e["parameterValue"].get(c, 0), 4) for c in "rgba"]
                              for e in p.get("vectorParameterValues") or []}
            out["textures"] = {e["parameterInfo"]["name"]: short(R(e["parameterValue"]))
                               for e in p.get("textureParameterValues") or []}
            for k in ("blendMode", "materialDomain", "twoSided"):
                if k in p:
                    out[k] = p[k]
            return out
        return self.step("mi:" + pkg(ref), f)

    def refs_of(self, path):
        return self.step("referencers:" + path, lambda: list(J(self.try_call(AS, "get_referencers",
                                                                             {"asset_path": path}, path) or "[]") or []))

    def mesh_slots(self, mref):
        def f():
            names = J(self.try_call(SM, "get_material_slots", {"mesh": {"refPath": mref}}, mref) or "[]") or []
            names = [n if isinstance(n, str) else (n.get("slotName") or n.get("name")) for n in names]
            out = []
            for n in names:
                m = self.try_call(SM, "get_material", {"mesh": {"refPath": mref}, "slot_name": n}, mref)
                out.append({"slot": n, "default": short(R(J(m) if m else None))})
            return out
        return self.step("slots:" + mref, f)


def run(args):
    sv = Survey(args.resume)
    inv = {"plan": "Docs/plans/P14_LIGHTING_STORM.md (F0)", "tool": "Tools/lighting/p14_f0_survey.py"}
    h = sv.step("header", sv.header)
    if h["pie"]:
        raise SystemExit("PIE is running: stop it first")
    if not str(h["level"]).startswith(MAP_PKG):
        raise SystemExit("current level is %s, not L_Monastery" % h["level"])
    inv["header"] = h
    act = sv.step("actors", sv.actors)
    refs = act["refs"]
    inv["actor_census"] = {"count": act["count"], "method": "SceneTools.find_actors name='' tag=''", "by_class": act["by_class"]}
    sv.log("actors: %d" % act["count"])
    inv["existing_storm_tags"] = sv.step("tags", lambda: {t: len(sv.call(S, "find_actors", {"name": "", "tag": t, "collision_channels": []}))
                                                          for t in ["LB_StormMoon", "LB_StormMoonSpot", "LB_StormFill", "LB_StormSky"]})

    # ---- lights
    lights = [sv.light(r) for r in refs if cls_of(r) in LIGHT_CLASSES]
    inv["lights"] = lights
    sv.log("lights: %d" % len(lights))
    by_label = defaultdict(list)
    for L in lights:
        by_label[L["label"]].append(L)
    chk = {}
    for grp, labs in PLAN_LIGHTS.items():
        for lab in labs:
            hits = by_label.get(lab, [])
            chk[lab] = {"group": grp, "found": len(hits), "class": hits[0]["class"] if hits else None,
                        "mobility": hits[0]["props"].get("mobility") if hits else None,
                        "intensity": hits[0]["props"].get("intensity") if hits else None,
                        "ref": hits[0]["ref"] if hits else None}
    inv["plan_light_check"] = chk
    crypt_pts = [L for L in lights if L["area"] == "crypt" and L["class"] == "PointLight"]
    inv["crypt_torches"] = [{"label": L["label"], "intensity": L["props"].get("intensity"),
                             "radius": L["props"].get("attenuationRadius"), "loc": L["xf"]["loc"],
                             "mobility": L["props"].get("mobility")}
                            for L in crypt_pts if abs((L["props"].get("intensity") or 0) - 250) < 1]
    inv["crypt_niche_candles"] = [{"label": L["label"], "intensity": L["props"].get("intensity"), "loc": L["xf"]["loc"],
                                   "mobility": L["props"].get("mobility")}
                                  for L in crypt_pts if abs((L["props"].get("intensity") or 0) - 90) < 1]

    # ---- lights inside Blueprints (never groupable)
    bp = [r for r in refs if cls_of(r).startswith("BP_") or cls_of(r) in ("SkeletalMeshActor",)]
    inv["blueprint_lights"] = [x for x in (sv.bp_lights(r) for r in bp) if x]
    sv.log("bp lights: %d actors" % len(inv["blueprint_lights"]))

    # ---- post-process volumes
    inv["pp_volumes"] = [sv.pp(r) for r in refs if cls_of(r) == "PostProcessVolume"]
    sv.log("pp volumes: %d" % len(inv["pp_volumes"]))

    # ---- material families (masters -> MIs -> meshes / blueprints)
    fam = {}
    masters = {}
    for m in MASTERS:
        hits = sv.step("find:" + m, lambda m=m: J(sv.call(AS, "find_assets", {"folder_path": "/Game/LastBell", "name": m})))
        exact = [x for x in hits if x.rsplit("/", 1)[-1] == m]
        masters[m] = exact[0] if exact else None
    masters["M_Sky_Panning_Clouds2"] = SKY_ENGINE
    for m, path in masters.items():
        if not path:
            fam[m] = {"error": "master not found"}
            continue
        seen, queue, mis, meshes, bps, other = set(), [path], [], set(), set(), set()
        while queue:
            cur = queue.pop(0)
            for r in sv.refs_of(cur):
                if r in seen:
                    continue
                seen.add(r)
                n = r.rsplit("/", 1)[-1]
                if n.startswith("MI_"):
                    mis.append(r)
                    queue.append(r)
                elif n.startswith("SM_"):
                    meshes.add(r)
                elif n.startswith("BP_"):
                    bps.add(r)
                elif not n.startswith("L_"):
                    other.add(r)
        fam[m] = {"master": path, "mis": [sv.mi(x) for x in mis], "mesh_users": sorted(meshes), "bp_users": sorted(bps),
                  "other_refs": sorted(other)}
        for x in fam[m]["mis"]:
            x["mesh_users"] = sorted(r for r in sv.refs_of(x["path"]) if r.rsplit("/", 1)[-1].startswith("SM_"))
            x["bp_users"] = sorted(r for r in sv.refs_of(x["path"]) if r.rsplit("/", 1)[-1].startswith("BP_"))
            x["in_map"] = any(r.startswith(MAP_PKG) for r in sv.refs_of(x["path"]))
    inv["material_families"] = fam
    sv.log("material families done")

    # ---- decals
    decals = {r: sv.decal(r) for r in refs if cls_of(r) == "DecalActor"}
    sv.log("decals: %d" % len(decals))
    pool_names = {short(x["path"]) for x in fam.get("M_LB_Decal_LightPool", {}).get("mis", [])}
    chalk_names = {short(x["path"]) for x in fam.get("M_LB_Decal_Chalk", {}).get("mis", [])}
    inv["pool_decals"] = []
    inv["chalk_decals"] = []
    for r, d in decals.items():
        if d["mat"] in pool_names or d["mat"] in chalk_names:
            rec = {"label": sv.label(r), "ref": r, "mat": d["mat"], "size": d["size"], "xf": sv.xform(r)}
            (inv["pool_decals"] if d["mat"] in pool_names else inv["chalk_decals"]).append(rec)
    inv["decal_material_counts"] = dict(Counter(d["mat"] for d in decals.values()).most_common())

    # ---- every static mesh actor (one call each)
    smas = [r for r in refs if cls_of(r) == "StaticMeshActor"]
    for i, r in enumerate(smas):
        sv.sma(r)
        if i % 250 == 0:
            sv.log("sma %d/%d" % (i, len(smas)))
    S_ = {r: sv.cache["sma:" + r] for r in smas}
    inv["sma_count"] = len(smas)
    inv["sma_mesh_counts"] = dict(Counter(v["mesh"] for v in S_.values()).most_common())

    # effective material users for the storm-driven families
    def users(family):
        out = []
        mis = {short(x["path"]): x for x in fam.get(family, {}).get("mis", [])}
        if family in ("M_LB_StainedGlass", "M_LB_StainedGlass_Translucent", "M_LB_LightShaft", "M_LB_Foliage",
                      "M_LB_FoliageMasked", "M_Sky_Panning_Clouds2"):
            mesh_paths = set()
            for x in mis.values():
                mesh_paths.update(x["mesh_users"])
            mesh_short = {p.rsplit("/", 1)[-1] for p in mesh_paths}
            for r, v in S_.items():
                hit_ov = [o for o in v["ov"] if o in mis]
                if hit_ov or v["mesh"] in mesh_short or (family == "M_Sky_Panning_Clouds2" and v["mesh"] == "SM_SkySphere"):
                    eff = []
                    slots = sv.mesh_slots(v["mesh_ref"]) if v["mesh_ref"] else []
                    for i, s in enumerate(slots):
                        o = v["ov"][i] if i < len(v["ov"]) else None
                        eff.append(o or s["default"])
                    fam_eff = [e for e in eff if e in mis]
                    if fam_eff:
                        out.append({"ref": r, "label": sv.label(r), "mesh": v["mesh"], "effective": eff,
                                    "family_mis": fam_eff, "xf": sv.xform(r), "mob": v["mob"], "shadow": v["shadow"],
                                    "wpo_dist": v["wpo_dist"], "wpo_eval": v["wpo_eval"]})
        return out

    for famname in ("M_LB_StainedGlass", "M_LB_StainedGlass_Translucent", "M_LB_LightShaft", "M_Sky_Panning_Clouds2"):
        inv.setdefault("users", {})[famname] = users(famname)
        sv.log("users %s: %d" % (famname, len(inv["users"][famname])))
    fol = users("M_LB_Foliage") + users("M_LB_FoliageMasked")
    inv["users"]["foliage_actors"] = fol
    sv.log("foliage actors: %d" % len(fol))
    inv["foliage_actor_mi_counts"] = dict(Counter(m for f in fol for m in f["family_mis"]).most_common())

    # sky chain
    sky = inv["users"]["M_Sky_Panning_Clouds2"]
    chain = []
    if sky:
        cur = sky[0]["effective"][0]
        mi_paths = {short(x["path"]): x for x in fam["M_Sky_Panning_Clouds2"]["mis"]}
        while cur in mi_paths:
            chain.append(mi_paths[cur])
            cur = mi_paths[cur]["parent"]
        chain.append({"path": SKY_ENGINE, "note": "engine material (root)"})
    inv["sky_chain"] = chain

    # glass: is there sky behind each pane? Trace along the thin axis both ways from the pane centre.
    glass = inv["users"]["M_LB_StainedGlass"] + inv["users"]["M_LB_StainedGlass_Translucent"]
    gtest = []
    for g in glass:
        b = sv.bounds(g["ref"])
        if not b:
            continue
        c = [(b["min"][i] + b["max"][i]) / 2 for i in range(3)]
        ext = [b["max"][i] - b["min"][i] for i in range(3)]
        ax = 0 if ext[0] < ext[1] else 1
        res = {}
        for sgn in (1, -1):
            dists = []
            for fz in (-0.3, 0.0, 0.3):
                s = list(c)
                s[2] = c[2] + fz * ext[2]
                s[ax] = c[ax] + sgn * (ext[ax] / 2 + 10)
                e = list(s)
                e[ax] = s[ax] + sgn * 8000
                dists.append(sv.trace(s, e))
            res["+" if sgn > 0 else "-"] = dists
        # sky behind = some sample runs out (None) or reaches > 20 m (the world backdrop at Y +-3600 / X 13400)
        open_side = [k for k, ds in res.items() if any(d is None or d > 2000 for d in ds)]
        gtest.append({"label": g["label"], "mis": g["family_mis"], "center": [round(x) for x in c], "thin_axis": "XY"[ax],
                      "traces": res, "sky_side": open_side, "sky_behind": bool(open_side)})
    inv["glass_sky_test"] = gtest
    bp_glass = []
    for b in fam.get("M_LB_StainedGlass", {}).get("bp_users", []) + fam.get("M_LB_StainedGlass_Translucent", {}).get("bp_users", []):
        bp_glass.append(b)
    for x in fam.get("M_LB_StainedGlass", {}).get("mis", []) + fam.get("M_LB_StainedGlass_Translucent", {}).get("mis", []):
        bp_glass += x["bp_users"]
    inv["glass_bp_users"] = sorted(set(bp_glass))
    sv.log("glass tested: %d" % len(gtest))

    # ---- PCG ISMs
    pcg = []
    for r in refs:
        if cls_of(r) != "PCGV":
            continue

        def f(r=r):
            comps = J(sv.try_call(A, "get_components", {"actor": {"refPath": r}}, r) or "[]") or []
            out = []
            for c in comps:
                cr = R(c)
                if not cr or not re.search(r"ISM|Instanced", cr.rsplit(".", 1)[-1]):
                    continue
                p = sv.getp(cr, ISM_PROPS)
                n = len(p.get("perInstanceSMData") or [])
                out.append({"comp": cr.rsplit(".", 1)[-1], "mesh": short(R(p.get("staticMesh"))),
                            "ov": [short(R(o)) for o in p.get("overrideMaterials") or []], "instances": n,
                            "shadow": p.get("castShadow"), "mob": p.get("mobility"),
                            "wpo_dist": p.get("worldPositionOffsetDisableDistance"),
                            "wpo_eval": p.get("bEvaluateWorldPositionOffset"),
                            "sci": p.get("shadowCacheInvalidationBehavior"),
                            "cull": [p.get("instanceStartCullDistance"), p.get("instanceEndCullDistance")]})
            return {"ref": r, "label": sv.label(r), "isms": out}
        pcg.append(sv.step("pcg:" + r, f))
    inv["pcg_volumes"] = pcg
    allism = [i for v in pcg for i in v["isms"]]
    inv["pcg_summary"] = {"volumes": len(pcg), "ism_components": len(allism), "instances": sum(i["instances"] for i in allism),
                          "by_mesh": dict(Counter(i["mesh"] for i in allism).most_common()),
                          "instances_by_mesh": {m: sum(i["instances"] for i in allism if i["mesh"] == m)
                                                for m in sorted({i["mesh"] for i in allism})},
                          "shadow_casting_components": sum(1 for i in allism if i["shadow"]),
                          "wpo_dist_values": dict(Counter(str(i["wpo_dist"]) for i in allism)),
                          "wpo_eval_values": dict(Counter(str(i["wpo_eval"]) for i in allism)),
                          "sci_values": dict(Counter(str(i["sci"]) for i in allism))}
    sv.log("pcg: %s" % json.dumps(inv["pcg_summary"])[:300])

    # ---- named plant groups (labels by prefix; find_actors matches labels)
    groups = {}
    for pre in ("CLA_Garth", "PSA_Weed_", "Ivy_"):
        hits = sv.step("findlab:" + pre, lambda pre=pre: [x["refPath"] for x in sv.call(S, "find_actors", {"name": pre, "tag": "", "collision_channels": []})])
        recs = []
        for r in hits:
            if cls_of(r) != "StaticMeshActor":
                continue
            v = S_.get(r) or sv.sma(r)
            lab = sv.label(r)
            if not lab or not lab.startswith(pre):
                continue
            recs.append({"label": lab, "mesh": v["mesh"], "ov": v["ov"], "mob": v["mob"], "shadow": v["shadow"],
                         "wpo_dist": v["wpo_dist"], "wpo_eval": v["wpo_eval"],
                         "loc": (sv.xform(r) or {}).get("loc") if pre == "CLA_Garth" else None})
        groups[pre] = recs
        sv.log("%s: %d" % (pre, len(recs)))
    inv["plant_groups"] = {k: {"count": len(v), "mesh_counts": dict(Counter(x["mesh"] for x in v).most_common()),
                               "wpo_dist_values": dict(Counter(str(x["wpo_dist"]) for x in v)),
                               "shadow_true": sum(1 for x in v if x["shadow"]), "items": v} for k, v in groups.items()}
    garth = [x["loc"] for x in groups["CLA_Garth"] if x["loc"] and not (x["mesh"] or "").startswith("SM_LB_Cl_")]
    if garth:
        inv["garth_bounds"] = {"from": len(garth), "x": [min(p[0] for p in garth) - 100, max(p[0] for p in garth) + 100],
                               "y": [min(p[1] for p in garth) - 100, max(p[1] for p in garth) + 100],
                               "rule": "min/max of the CLA_Garth* plant locations (the 6 SM_LB_Cl_* garth structures excluded), +-100 cm",
                               "structures_excluded": [x["label"] for x in groups["CLA_Garth"] if (x["mesh"] or "").startswith("SM_LB_Cl_")]}
    searsia = [r for r, v in S_.items() if v["mesh"] and "Searsia" in v["mesh"]]
    inv["searsia_actors"] = [{"label": sv.label(r), "mesh": S_[r]["mesh"], "wpo_dist": S_[r]["wpo_dist"], "loc": (sv.xform(r) or {}).get("loc")} for r in searsia]

    # ---- flame meshes near the group lights
    flames = [r for r, v in S_.items() if v["mesh"] == "SM_LB_Prop_CandleFlame_A"]
    fl = [{"label": sv.label(r), "ref": r, "loc": (sv.xform(r) or {}).get("loc"), "vis": S_[r]["vis"]} for r in flames]
    inv["flame_meshes"] = fl
    near = {}
    want = [L for L in lights if L["label"] in {n["label"] for n in inv["crypt_niche_candles"]} or
            any(L["label"] in v for k, v in PLAN_LIGHTS.items() if k.startswith("SLG_")) or
            L["label"] in {t["label"] for t in inv["crypt_torches"]}]
    for L in want:
        lp = L["xf"]["loc"]
        near[L["label"]] = sorted([{"flame": f["label"], "dist": round(math.dist(lp, f["loc"]), 1)} for f in fl
                                   if f["loc"] and math.dist(lp, f["loc"]) <= 120], key=lambda d: d["dist"])
    inv["flames_near_group_lights"] = near
    sv.log("flames: %d" % len(fl))

    # ---- lanterns and other emissive props near the group lights (for information)
    lan = [r for r, v in S_.items() if v["mesh"] == "SM_Wooden_Lantern_01"]
    lanterns = [{"label": sv.label(r), "loc": (sv.xform(r) or {}).get("loc")} for r in lan]
    inv["lanterns"] = lanterns
    inv["lanterns_near_group_lights"] = {L["label"]: sorted([{"lantern": x["label"], "dist": round(math.dist(L["xf"]["loc"], x["loc"]), 1)}
                                                             for x in lanterns if x["loc"] and math.dist(L["xf"]["loc"], x["loc"]) <= 150],
                                                            key=lambda d: d["dist"]) for L in want}

    # ---- apparitions
    app = []
    for r in refs:
        if cls_of(r) != "BP_WardenApparition_C":
            continue
        p = sv.step("app:" + r, lambda r=r: sv.getp(r, ["stations", "triggerTag", "bUseSkeletalFigure"]))
        app.append({"label": sv.label(r), "ref": r, "xf": sv.xform(r), "props": p})
    inv["apparitions"] = app

    # ---- name collisions with the plan's new actors
    labels_all = {}
    inv["new_name_collisions"] = {}
    for pre in NEW_NAMES:
        hits = sv.step("findlab:" + pre, lambda pre=pre: [x["refPath"] for x in sv.call(S, "find_actors", {"name": pre, "tag": "", "collision_channels": []})])
        inv["new_name_collisions"][pre] = [sv.label(h) for h in hits if (sv.label(h) or "").startswith(pre)]

    # ---- decal surface points (traces)
    inv["decal_points"] = decal_points(sv, inv, S_)
    # ---- tower reveal pose
    inv["tower_reveal_pose"] = tower_pose(sv)
    # ---- viewpoints
    poses = json.load(open(POSES, encoding="utf-8"))
    poses = poses.get("poses", poses)
    inv["viewpoints"] = {"missing_from_p11_poses": [v for v in VIEWPOINTS if v not in poses],
                         "poses": {v: poses.get(v) for v in VIEWPOINTS},
                         "new": {"tw_base": [12200, 2000, 170, 5, 0], "p14_cy_tower_reveal": [600, 0, 170, 14, 9.5]}}

    inv["header"]["dirty_after"] = sv.call(AS, "is_dirty", {"asset_path": MAP_PKG})
    inv["header"]["calls"] = sv.calls
    inv["header"]["seconds"] = round(time.time() - sv.t0)
    inv["errors"] = sv.errors
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "p14_f0_inventory.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(inv, f, indent=1)
    sv.log("wrote %s (%d errors)" % (out, len(sv.errors)))


def sweep(sv, fixed, var_axis, values, dir_axis, sgn, length):
    """Trace from points along a line; returns [(value, distance or None)]."""
    out = []
    for v in values:
        s = list(fixed)
        s[var_axis] = v
        e = list(s)
        e[dir_axis] = s[dir_axis] + sgn * length
        out.append((v, sv.trace(s, e)))
    return out


def runs(samples, open_test):
    """Contiguous runs of samples where open_test(distance) is true."""
    out, cur = [], None
    for v, d in samples:
        if open_test(d):
            cur = [v, v] if cur is None else [cur[0], v]
        elif cur is not None:
            out.append(cur)
            cur = None
    if cur is not None:
        out.append(cur)
    return out


def decal_points(sv, inv, S_):
    pts = {}
    # 1. Gate sigil: courtyard-side inner face of the gatehouse (faces +X). Find the arch opening at Z 260 first.
    g = sweep(sv, [900, 0, 260], 1, list(range(-1000, 1001, 50)), 0, -1, 1200)
    # the wall face is the common distance (600 = X 300); the arch is the recess behind it (d > 620)
    openings = [r for r in runs(g, lambda d: d is None or d > 620) if r[0] <= 0 <= r[1] or abs((r[0] + r[1]) / 2) < 300]
    arch = min(openings, key=lambda r: abs((r[0] + r[1]) / 2)) if openings else None
    ac = (arch[0] + arch[1]) / 2 if arch else 0.0
    y = ac + 500
    d = sv.trace([900, y, 260], [-300, y, 260])
    pts["RV_Gate_Sigil"] = {"sweep_z260_from_x900_toward_-x": g, "arch_opening_y": arch, "arch_centre_y": ac,
                            "point": [round(900 - d, 1), y, 260] if d is not None else None, "normal": "+X (faces the courtyard)",
                            "trace_dist": d}
    # 2. Well-house tally: the face toward the key route. Route (1250,-300)->(1500,-1550)->(1500,-1850)->(1520,-1950).
    w = sweep(sv, [0, -1500, 140], 0, list(range(1000, 2301, 50)), 1, -1, 1500)
    door = runs(w, lambda d: d is None or d > 600)
    pts["RV_WellHouse_Tally"] = {"sweep_z140_from_y-1500_toward_-y": w, "openings_x": door}
    # 3. Chapel circle: centred on the S2 pool decal, on the floor.
    # the pools fall ~765 cm +X of their lancets (moon yaw 35), so pick the S2 pool by label
    s2 = next((p for p in inv["pool_decals"] if p["label"] == "Ch_Pool_S2" and p["xf"]), None)
    if s2:
        x, y, z = s2["xf"]["loc"]
        dz = sv.trace([x, y, 200], [x, y, -200])
        pts["RV_Chapel_Circle"] = {"pool_decal": s2["label"], "pool_loc": s2["xf"]["loc"], "pool_rot": s2["xf"]["rot"],
                                   "floor_z": round(200 - dz, 1) if dz is not None else None}
    else:
        pts["RV_Chapel_Circle"] = {"error": "no S2 pool decal found (X 7000-8000, Y<0)",
                                   "pools": [(p["label"], p["xf"]["loc"] if p["xf"] else None) for p in inv["pool_decals"]]}
    # 4. Garth drag: from cl_tall_north_15m [10850, 1500, 200, 15, 90], the garth-facing arcade wall straight ahead.
    poses = json.load(open(POSES, encoding="utf-8"))
    cx, cy, cz, cp, cyaw = poses["cl_tall_north_15m"]
    fwd = [math.cos(math.radians(cp)) * math.cos(math.radians(cyaw)), math.cos(math.radians(cp)) * math.sin(math.radians(cyaw)),
           math.sin(math.radians(cp))]
    dc = sv.trace([cx, cy, cz], [cx + fwd[0] * 6000, cy + fwd[1] * 6000, cz + fwd[2] * 6000])
    hit = [round(cx + fwd[0] * dc, 1), round(cy + fwd[1] * dc, 1), round(cz + fwd[2] * dc, 1)] if dc is not None else None
    gs = sweep(sv, [0, cy, 270], 0, list(range(int(cx) - 800, int(cx) + 801, 50)), 1, 1, 4000)
    pts["RV_Garth_Drag"] = {"pose": [cx, cy, cz, cp, cyaw], "view_centre_hit": hit, "view_centre_dist": dc,
                            "sweep_z270_toward_+y": gs}
    # 5. Belfry tally: south wall (faces +Y inside the belfry), between the two south lancets, Z 2850.
    bs = sweep(sv, [0, 1900, 2850], 0, list(range(12000, 13001, 25)), 1, -1, 1500)
    lancets = runs(bs, lambda d: d is None or d > 700)
    pts["RV_Belfry_Tally"] = {"sweep_z2850_from_y1900_toward_-y": bs, "openings_x": lancets}
    return pts


def tower_pose(sv):
    x0, y0, z0, pitch, yaw = 600, 0, 170, 14, 9.5
    tops = {}
    for (x, y) in [(12500, 2000), (12100, 1600), (12900, 1600), (12100, 2400), (12900, 2400)]:
        d = sv.trace([x, y, 12000], [x, y, 0])
        tops["%d,%d" % (x, y)] = round(12000 - d, 1) if d is not None else None
    top_z = max(v for v in tops.values() if v is not None) if any(v is not None for v in tops.values()) else None
    res = {"pose": [x0, y0, z0, pitch, yaw], "top_z_by_vertical_trace": tops, "top_z": top_z}
    if top_z is None:
        return res
    tx, ty, tz = 12500, 2000, top_z - 30
    dx, dy, dz = tx - x0, ty - y0, tz - z0
    hd = math.hypot(dx, dy)
    yaw_t = math.degrees(math.atan2(dy, dx))
    pitch_t = math.degrees(math.atan2(dz, hd))
    # the PIE player camera: 90 deg horizontal FOV; capture frames are portrait (about 760 x 860) or 16:9 at 1920x1080
    out = {}
    for name, w, h in (("portrait_761x862", 761, 862), ("1920x1080", 1920, 1080)):
        hh = 45.0
        vh = math.degrees(math.atan(math.tan(math.radians(hh)) * h / w))
        out[name] = {"h_half_fov": round(hh, 1), "v_half_fov": round(vh, 1),
                     "in_frame": abs(yaw_t - yaw) < hh and abs(pitch_t - pitch) < vh}
    full = math.dist([x0, y0, z0], [tx, ty, tz])
    los = sv.trace([x0, y0, z0], [tx, ty, tz])
    hit_x = None if los is None else x0 + dx * los / full
    res.update({"target": [tx, ty, tz], "yaw_to_top": round(yaw_t, 2), "pitch_to_top": round(pitch_t, 2),
                "offset_from_centre_deg": [round(yaw_t - yaw, 2), round(pitch_t - pitch, 2)], "frames": out,
                "los_trace_dist": los, "los_full_dist": round(full, 1),
                "los_hit_x": None if hit_x is None else round(hit_x, 1),
                "los_clear": los is None or hit_x >= 11990 - 50,
                "los_rule": "clear if the first hit is on the tower itself (west face X 11990)"})
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", action="store_true")
    run(ap.parse_args())
