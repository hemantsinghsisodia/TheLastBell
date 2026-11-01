"""P11-2a: READ-ONLY census of what is placed in L_Monastery (stone and weathering planning).

Run (editor open on the project, PIE off):
    python -I Tools/materials/census_p11.py [--resume] [--limit N] [--out-dir DIR] [--cache FILE]

Editor calls used (all read-only): find_actors, get_label, get_actor_transform, get_actor_bounds,
get_root_component, get_components, get_properties, get_material_slots, get_material, find_assets,
get_scalar_parameter, get_texture_parameter, get_static_switch_parameter, list_parameters,
is_dirty, IsPIERunning, GetCameraTransform, GetVisibleActors and ONE write: SetCameraTransform
(viewport camera only, restored in a finally block). Nothing else mutates the level or any asset.

Outputs: Docs/ArtTest/materials/census_p11.json and census_p11.md; groove data is joined from
Tools/materials/grooved_meshes.json (written separately by hand from the Blender scripts).
Cache: Saved/p11_census_cache.jsonl (one JSON line per actor / mesh / MI, flushed per line).
"""
import argparse
import datetime
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
MI = "editor_toolset.toolsets.material_instance.MaterialInstanceTools"
E = "EditorToolset.EditorAppToolset"

MAP_PKG = "/Game/LastBell/Maps/L_Monastery"
MASTER_PKG = "/Game/LastBell/Materials/Master/M_LB_Surface"
SKIP_CLASSES = {"TargetPoint", "TriggerVolume", "LBSearchPoint", "LBPatrolPoint", "LocalFogVolume", "LBCheckpoint",
                "Emitter", "PostProcessVolume", "LBWardenSpawnPoint", "WorldSettings", "Brush", "PlayerStart",
                "SkyAtmosphere", "SkyLight", "ExponentialHeightFog", "DirectionalLight"}
LIGHT_CLASSES = {"PointLight", "SpotLight", "RectLight"}
SWITCHES = ["bGapGrowth", "bPuddles", "bTopDust", "bUseARM", "bWallUseDistanceField", "bWorldAlignedUV"]
EFF_SCALARS = ["WorldTileSizeCm", "UVScale", "MacroStrength", "NormalStrength", "Wetness"]
IGNORE_COMP = re.compile(r"Arrow|Billboard|Sprite", re.I)
ISM_RE = re.compile(r"InstancedStaticMesh|HierarchicalInstanced|(^|_)ISM(_|$)")
NOT_READABLE = ("could not be read", "not found", "not a valid", "Failed to find", "does not exist", "No such",
                "Could not find")


class Abort(Exception):
    pass


class ToolErr(Exception):
    """Deterministic tool-level failure (the server answered): not retried, not counted as a dead editor."""


J = lambda x: json.loads(x) if isinstance(x, str) else x  # noqa: E731


def R(x):
    """Normalise a reference (dict / string / None) to a plain path string or None."""
    if isinstance(x, dict):
        x = x.get("refPath")
    if not x or x in ("None", "null"):
        return None
    return x


def pkg_of(ref):
    return ref.rsplit(".", 1)[0] if ref and "." in ref.rsplit("/", 1)[-1] else ref


def short(ref):
    return ref.rsplit(".", 1)[-1] if ref else None


def asset_ref(pkg):
    return pkg + "." + pkg.rsplit("/", 1)[-1] if "." not in pkg.rsplit("/", 1)[-1] else pkg


def cls_of(ref):
    n = ref.split("PersistentLevel.", 1)[1] if "PersistentLevel." in ref else ref.rsplit(".", 1)[-1]
    n = re.sub(r"_\d+$", "", n)
    return "PCGV" if n.startswith("PCGV_") else n


def area_of(loc):
    x, y, z = loc["x"], loc["y"], loc["z"]
    if x >= 6300 and -2950 <= y <= 520 and z < -45:
        return "crypt"
    if 11990 <= x <= 13010 and 1490 <= y <= 2510:
        return "tower"
    if 9460 <= x <= 12040 and 500 <= y <= 3040:
        return "cloister"
    if 6040 <= x < 9460 and 1400 <= y <= 2600:
        return "passage"
    if 6000 <= x <= 9100 and -1500 <= y <= 850:
        return "chapel"
    if 300 <= x < 6000 and -2600 <= y <= 2600:
        return "courtyard"
    if x < 300:
        return "approach"
    return "other"


def extract_refs(o, out):
    if isinstance(o, str):
        if "PersistentLevel." in o:
            out.append(o)
    elif isinstance(o, dict):
        if "refPath" in o and isinstance(o["refPath"], str):
            out.append(o["refPath"])
        else:
            for v in o.values():
                extract_refs(v, out)
    elif isinstance(o, list):
        for v in o:
            extract_refs(v, out)
    return out


class Census:
    def __init__(self, args):
        self.args = args
        self.ue = UE()
        self.consec_fail = 0
        self.calls = 0
        self.errors = []
        self.cache = {}
        if os.path.exists(args.cache) and args.resume:
            with open(args.cache, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            d = json.loads(line)
                            self.cache[d["key"]] = d["val"]
                        except Exception:
                            pass
        elif os.path.exists(args.cache):
            os.replace(args.cache, args.cache + ".old")
        os.makedirs(os.path.dirname(args.cache), exist_ok=True)
        self.cf = open(args.cache, "a", encoding="utf-8")

    # ---------------------------------------------------------------- calls
    def call(self, toolset, tool, args=None, ctx=""):
        last = None
        for attempt in range(3):
            try:
                self.calls += 1
                r = self.ue.call(toolset, tool, args or {})
                self.consec_fail = 0
                return r
            except RuntimeError as e:
                msg = str(e)
                if any(s in msg for s in NOT_READABLE):
                    self.consec_fail = 0
                    raise ToolErr(msg[:300])
                last = msg[:300]
            except Exception as e:  # transport (editor busy / connection reset)
                last = "%s: %s" % (type(e).__name__, str(e)[:200])
                try:
                    time.sleep(5)
                    self.ue = UE()
                except Exception:
                    pass
                continue
            time.sleep(5)
        self.consec_fail += 1
        if self.consec_fail >= 10:
            raise Abort("10 consecutive failures; the editor is probably gone")
        raise ToolErr("FAILED: [%s.%s] %s" % (toolset.rsplit(".", 1)[-1], tool, last or ""))

    def fail(self, ctx, what, e):
        """Record a call that failed after retries (deterministic 'not readable' answers are not errors)."""
        if str(e).startswith("FAILED"):
            self.errors.append({"actor": ctx, "call": what, "error": str(e)[:300]})

    def put(self, key, val):
        self.cache[key] = val
        self.cf.write(json.dumps({"key": key, "val": val}) + "\n")
        self.cf.flush()

    def pie_check(self):
        if self.call(E, "IsPIERunning"):
            raise Abort("PIE is running")

    # ------------------------------------------------------------ stage 1
    def stage1(self):
        k = "__stage1__"
        if k in self.cache:
            return self.cache[k]
        found = [x["refPath"] for x in self.call(S, "find_actors", {"name": "", "tag": "", "collision_channels": []})]
        cam0 = J(self.call(E, "GetCameraTransform"))
        vis, cam_ok, cam_note = [], None, None
        try:
            self.call(E, "SetCameraTransform", {"transform": {"location": {"x": 8000, "y": 0, "z": 30000},
                                                              "rotation": {"pitch": -90, "yaw": 0, "roll": 0},
                                                              "scale": {"x": 1, "y": 1, "z": 1}}})
            time.sleep(2.0)
            vis = extract_refs(J(self.call(E, "GetVisibleActors")), [])
        except Exception as e:
            cam_note = "visible-set failed: %s" % e
        finally:
            try:
                sc = cam0.get("scale") or {"x": 1, "y": 1, "z": 1}
                self.call(E, "SetCameraTransform", {"transform": {"location": cam0["location"],
                                                                  "rotation": cam0["rotation"], "scale": sc}})
                time.sleep(0.5)
                cam1 = J(self.call(E, "GetCameraTransform"))
                d = math.dist([cam0["location"][a] for a in "xyz"], [cam1["location"][a] for a in "xyz"])
                dr = max(abs(cam0["rotation"][a] - cam1["rotation"][a]) for a in ("pitch", "yaw", "roll"))
                cam_ok = d <= 1.0 and dr <= 0.5
                cam_note = (cam_note or "") + " camera restore: moved %.4f cm, rotation delta %.4f deg" % (d, dr)
            except Exception as e:
                cam_note = (cam_note or "") + " CAMERA RESTORE FAILED: %s (saved %s)" % (e, json.dumps(cam0))
        vis = list(dict.fromkeys(vis))
        fs = set(found)
        only_vis = [v for v in vis if v not in fs]
        union = found + only_vis
        val = {"found": found, "visible_count": len(vis), "only_visible": only_vis, "union": union,
               "camera_restored": cam_ok, "camera_note": cam_note, "camera_saved": cam0}
        self.put(k, val)
        return val

    # ------------------------------------------------------------ stage 2
    def comp_mesh(self, cref, ctx):
        try:
            p = J(self.call(O, "get_properties", {"instance": {"refPath": cref},
                                                  "properties": ["staticMesh", "overrideMaterials"]}, ctx))
        except ToolErr as e:
            if str(e).startswith("FAILED"):
                raise
            return None
        mesh = R(p.get("staticMesh"))
        if not mesh:
            return None
        return {"mesh": mesh, "overrides": [R(x) for x in (p.get("overrideMaterials") or [])]}

    def process_actor(self, ref):
        cls = cls_of(ref)
        rec = {"ref": ref, "cls": cls, "errs": []}
        ctx = ref.split("PersistentLevel.")[-1]
        a = {"actor": {"refPath": ref}}

        def safe(fn, what):
            try:
                return fn()
            except ToolErr as e:
                rec["errs"].append({"call": what, "error": str(e)[:300]})
                return None

        rec["label"] = safe(lambda: self.call(A, "get_label", a, ctx), "get_label")
        xf = safe(lambda: J(self.call(A, "get_actor_transform", a, ctx)), "get_actor_transform")
        if not xf:
            return None
        rec["location"], rec["rotation"], rec["scale"] = xf["location"], xf["rotation"], xf["scale"]
        rec["area"] = area_of(xf["location"])
        if cls == "StaticMeshActor":
            rec["kind"] = "sma"
            m = safe(lambda: self.comp_mesh(ref + ".StaticMeshComponent0", ctx), "StaticMeshComponent0")
            if m is None:
                root = safe(lambda: R(J(self.call(A, "get_root_component", a, ctx))), "get_root_component")
                m = safe(lambda: self.comp_mesh(root, ctx), "root mesh") if root else None
            rec["mesh"], rec["overrides"] = (m["mesh"], m["overrides"]) if m else (None, [])
            meshes = [rec["mesh"]] if rec["mesh"] else []
        elif cls == "DecalActor":
            rec["kind"] = "decal"
            root = safe(lambda: R(J(self.call(A, "get_root_component", a, ctx))), "get_root_component")
            p = safe(lambda: J(self.call(O, "get_properties", {"instance": {"refPath": root},
                                                               "properties": ["decalMaterial", "decalSize"]}, ctx)),
                     "decal props") if root else None
            p = p or {}
            rec["material"] = R(p.get("decalMaterial"))
            ds = p.get("decalSize") or {}
            rec["decal_size"] = ds
            sc = rec["scale"]
            rec["world_size"] = {k: ds[k] * sc[k] for k in "xyz"} if ds else None
            meshes = []
        elif cls in LIGHT_CLASSES:
            rec["kind"] = "light"
            props = ["intensity", "attenuationRadius", "castShadows", "lightFunctionMaterial"]
            p = safe(lambda: J(self.call(O, "get_properties", {"instance": {"refPath": ref + ".LightComponent0"},
                                                               "properties": props}, ctx)), "light props") or {}
            rec["intensity"], rec["attenuation_radius"] = p.get("intensity"), p.get("attenuationRadius")
            rec["cast_shadows"], rec["light_function"] = p.get("castShadows"), R(p.get("lightFunctionMaterial"))
            meshes = []
        else:
            rec["kind"] = "other"
            comps = safe(lambda: J(self.call(A, "get_components", a, ctx)), "get_components") or []
            rec["components"] = []
            for c in comps:
                cref = R(c)
                cname = cref.rsplit(".", 1)[-1]
                if IGNORE_COMP.search(cname):
                    continue
                m = safe(lambda: self.comp_mesh(cref, ctx), "comp " + cname)
                if m:
                    m.update({"component": cname, "is_ism": bool(ISM_RE.search(cname) or "InstancedStaticMesh" in cref),
                              "instances": None})
                    rec["components"].append(m)
            meshes = [c["mesh"] for c in rec["components"]]
        if any("lantern" in short(m).lower() and "bracket" not in short(m).lower() for m in meshes):
            rec["bounds"] = safe(lambda: J(self.call(A, "get_actor_bounds", a, ctx)), "get_actor_bounds")
        return rec

    def pick_limit(self, refs, n):
        by = defaultdict(list)
        for r in refs:
            if cls_of(r) not in SKIP_CLASSES:
                by[cls_of(r)].append(r)
        want = [r for r in refs if r.endswith("DecalActor_1") or "BP_Inscription_Cloister_C_0" in r]
        i = 0
        while len(want) < n and any(len(v) > i for v in by.values()):
            for v in by.values():
                if len(v) > i and v[i] not in want and len(want) < n:
                    want.append(v[i])
            i += 1
        return want

    # ------------------------------------------------------------ stage 3
    def mesh_info(self, mref):
        k = "mesh:" + mref
        if k in self.cache:
            return self.cache[k]
        names = J(self.call(SM, "get_material_slots", {"mesh": {"refPath": mref}}, short(mref)))
        names = [n if isinstance(n, str) else (n.get("slotName") or n.get("name")) for n in names]
        defaults = []
        for n in names:
            try:
                defaults.append(R(J(self.call(SM, "get_material", {"mesh": {"refPath": mref}, "slot_name": n}, mref))))
            except ToolErr as e:
                self.fail(short(mref), "get_material " + str(n), e)
                defaults.append(None)
        val = {"slots": names, "defaults": defaults}
        self.put(k, val)
        return val

    # ------------------------------------------------------------ stage 4
    def mi_info(self, ref):
        """Own overrides + parent of one material interface (cached by package path)."""
        k = "mi:" + pkg_of(ref)
        if k in self.cache:
            return self.cache[k]
        val = {"path": pkg_of(ref), "name": short(ref), "parent": None, "is_instance": False}
        try:
            p = J(self.call(O, "get_properties", {"instance": {"refPath": ref}, "properties": [
                "parent", "scalarParameterValues", "textureParameterValues", "vectorParameterValues"]}, ref))
            val["is_instance"] = True
            val["parent"] = R(p.get("parent"))
            val["scalars"] = {e["parameterInfo"]["name"]: e["parameterValue"] for e in p.get("scalarParameterValues") or []}
            val["textures"] = {e["parameterInfo"]["name"]: R(e["parameterValue"]) for e in p.get("textureParameterValues") or []}
            val["vectors"] = {e["parameterInfo"]["name"]: [e["parameterValue"].get(c) for c in "rgba"]
                              for e in p.get("vectorParameterValues") or []}
        except ToolErr as e:
            if str(e).startswith("FAILED"):
                val["error"] = str(e)
                self.fail(short(ref), "mi_info", e)
        self.put(k, val)
        return val

    def chain(self, ref):
        out, seen = [], set()
        while ref and pkg_of(ref) not in seen:
            seen.add(pkg_of(ref))
            info = self.mi_info(ref)
            out.append(info)
            ref = info["parent"]
        return out

    def surface_effective(self, mi_ref, master_params):
        k = "eff:" + pkg_of(mi_ref)
        if k in self.cache:
            return self.cache[k]
        inst = {"instance": {"refPath": mi_ref}}
        eff = {"switches": {}, "scalars": {}, "textures": {}}
        for s in SWITCHES:
            try:
                eff["switches"][s] = J(self.call(MI, "get_static_switch_parameter", dict(inst, name=s), mi_ref))
            except ToolErr as e:
                self.fail(short(mi_ref), "switch " + s, e)
                eff["switches"][s] = None
        for s in EFF_SCALARS:
            try:
                eff["scalars"][s] = J(self.call(MI, "get_scalar_parameter", dict(inst, name=s), mi_ref))
            except ToolErr as e:
                self.fail(short(mi_ref), "scalar " + s, e)
                eff["scalars"][s] = None
        for t in master_params.get("textures", []):
            try:
                eff["textures"][t] = R(J(self.call(MI, "get_texture_parameter", dict(inst, name=t), mi_ref)))
            except ToolErr as e:
                self.fail(short(mi_ref), "texture " + t, e)
                eff["textures"][t] = None
        self.put(k, eff)
        return eff


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)


def dist_point_box(p, b):
    d = 0.0
    for a in "xyz":
        lo, hi = b["min"][a], b["max"][a]
        v = max(lo - p[a], 0.0, p[a] - hi)
        d += v * v
    return math.sqrt(d)


AREAS = ["approach", "courtyard", "chapel", "passage", "cloister", "tower", "crypt", "other"]
GROOVED = ("full", "vertical_only", "horizontal_only")


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return out


def per_area(d):
    return ", ".join("%s %d" % (a, d[a]) for a in AREAS if d.get(a)) or "-"


def write_md(o, path):
    L = []
    c = o["counts"]
    L.append("# P11-2a census of `L_Monastery`" + ("  (TEST RUN, limit %d)" % o["limit"] if o.get("limit") else ""))
    L.append("")
    L.append("Generated %s by `Tools/materials/census_p11.py` (read-only). Areas: actor location, first match wins." % o["generated"])
    L.append("")
    L.append("## 1. Counts")
    L.append("")
    L.append("find_actors **%d**, visible (top-down camera) **%d**, union **%d**; only in the visible set: %d. "
             "Actors read in detail: %d (classes in the skip list are counted only, so `by area` excludes them). "
             "Editor calls in the final pass: %d (cached results reused; the first full pass took 12475)." % (c["find_actors"], c["visible"], c["union"], len(c["only_visible"]), c["actors_read"], c["calls"]))
    L.append("")
    if c["only_visible"]:
        L.append("Only in the visible set: " + ", ".join(p.split("PersistentLevel.")[-1] for p in c["only_visible"][:40]))
        L.append("")
    L += table(["Class", "Count", "Skipped (count only)"],
               [(k, v, "yes" if k in c["skipped_by_class"] else "") for k, v in c["by_class"].items()])
    L.append("")
    L += table(["Area", "Actors read"], [(a, c["by_area"].get(a, 0)) for a in AREAS])
    L.append("")
    ol = c["other_area_labels"]
    L.append("`other` area: %d actors. Labels: %s" % (len(ol), ", ".join(ol[:80]) + (" ..." if len(ol) > 80 else "") if ol else "none"))
    L.append("")
    L.append("## 2. Grooved meshes (from `Tools/materials/grooved_meshes.json`)")
    L.append("")
    mc = o["mesh_counts"]
    gl = [m for m in mc if m["groove"] != "none"]
    L += table(["Mesh", "Groove", "Placed", "Actors", "Hidden", "Per area", "Source"],
               [(m["mesh"], m["groove"], m["placed"], m["actors"], m.get("hidden", 0), per_area(m["by_area"]), (m["groove_source"] or "")[:100]) for m in gl])
    L.append("")
    byg = Counter(m["groove"] for m in mc)
    ga = defaultdict(int)
    for m in mc:
        ga[m["groove"]] += m["actors"]
    gm_n = sum(1 for m in mc if m["groove"] in GROOVED)
    L.append("Distinct meshes by groove type: " + ", ".join("%s %d (%d actors, summed over meshes)" % (k, v, ga[k]) for k, v in sorted(byg.items())) + ".")
    gmesh = {m["mesh"] for m in mc if m["groove"] in GROOVED}
    gact = {r["path"] for r in o["static_mesh_actors"] if short(r["mesh"]) in gmesh}
    gact |= {r["actor_path"] for r in o["component_meshes"] if short(r["mesh"]) in gmesh}
    L.append("**Grooved (full / vertical_only / horizontal_only): %d distinct meshes placed, %d placements, %d distinct actors.** "
             "Full-length source text for every mesh is in `grooved_meshes.json` (`parts` lists body vs cap where they differ; caps and copings are vertical_only)." % (
                 gm_n, sum(m["placed"] for m in mc if m["groove"] in GROOVED), len(gact)))
    o["counts"]["grooved_distinct_meshes"], o["counts"]["grooved_distinct_actors"] = gm_n, len(gact)
    L.append("")
    L.append("## 3. `M_LB_Surface` material instances (placed)")
    L.append("")
    sm = o["surface_mis"]
    placed = [m for m in sm if m["actors"]]
    rows = []
    for m in placed:
        e = m.get("effective", {})
        bc = (e.get("textures") or {}).get("BaseColorTex")
        rows.append((m["name"], m["chain"][1]["name"] if len(m["chain"]) > 1 else "M_LB_Surface", short(bc) if bc else "-",
                     (e.get("switches") or {}).get("bWorldAlignedUV"), (e.get("scalars") or {}).get("WorldTileSizeCm"),
                     ", ".join(m["slots_filled"]), m["actors"], m.get("hidden_actors", 0), per_area(m["by_area"])))
    L += table(["MI", "Parent", "BaseColorTex", "bWorldAlignedUV", "WorldTileSizeCm", "Slots", "Actors", "of them hidden", "Per area"], rows)
    L.append("")
    L.append("%d surface MIs exist, %d are placed (actors counted once per MI). Other placed MIs (root is not M_LB_Surface):" % (len(sm), len(placed)))
    L.append("")
    L += table(["MI", "Root", "Mesh actors", "of them hidden", "Decal actors"],
               [(m["name"], short(m["root"]), m["mesh_actors"], m.get("mesh_hidden_actors", 0), m["decal_actors"]) for m in o["other_mis"]])
    L.append("")
    L.append("## 4. Textures per placed surface MI")
    L.append("")
    tex = defaultdict(lambda: {"params": set(), "mis": []})
    for m in placed:
        for pn, t in ((m.get("effective") or {}).get("textures") or {}).items():
            if t and (pn == "BaseColorTex" or "medieval_blocks" in t.lower()):
                tex[short(t)]["params"].add(pn)
                tex[short(t)]["mis"].append("%s (%d)" % (m["name"], m["actors"]))
    rows = []
    for t, d in sorted(tex.items(), key=lambda kv: -len(kv[1]["mis"])):
        judge = "painted block joints (stated in the plan)" if t in ("T_Medieval_Blocks_03", "T_Medieval_Blocks_03_BC") else (
            "same set as T_Medieval_Blocks_03, check by eye" if t.startswith("T_Medieval_Blocks_03") else "check by eye")
        rows.append((t, ", ".join(sorted(d["params"])), len(d["mis"]), ", ".join(d["mis"][:12]) + (" ..." if len(d["mis"]) > 12 else ""), judge))
    L += table(["Texture", "Param", "MIs", "MIs (actors)", "Painted joints?"], rows)
    L.append("")
    L.append("## 5. Decals")
    L.append("")
    L.append("Total decal actors: **%d**." % len(o["decals"]))
    L.append("")
    L += table(["Decal MI", "Count", "Per area"], [(d["material"], d["count"], per_area(d["by_area"])) for d in o["decal_counts"]])
    L.append("")
    L.append("## 6. Lanterns")
    L.append("")
    lan = o["lanterns"]
    flag = [x for x in lan if not x["has_light_within_60cm"]]
    L.append("Lantern placements: **%d**; with no light within 60 cm: **%d**. Distance is light location to the closest point of the "
             "lantern actor's bounds (0 if inside)." % (len(lan), len(flag)))
    L.append("")
    gl_names = sorted({g["material"] for x in lan for g in x["glass_slot_materials"] if g["material"]})
    for gn in gl_names:
        mi = next((m for m in o["surface_mis"] if m["name"] == gn), None)
        if mi:
            L.append("Glass material `%s`: chain %s; root M_LB_Surface; BaseColorTex %s; own overrides: %s." % (
                gn, " > ".join(c["name"] for c in mi["chain"]), short((mi.get("effective") or {}).get("textures", {}).get("BaseColorTex") or "-"),
                json.dumps(mi.get("own"))[:300]))
    L.append("")
    L += table(["Label", "Area", "Mesh", "Glass material (slot)", "Nearest light", "Distance cm", "Flag"],
               [(x["label"], x["area"], x["mesh"], "; ".join("%s (%s)" % (g["material"], g["slot"]) for g in x["glass_slot_materials"]),
                 x["nearest_light"], x["nearest_light_distance_cm"], "NO LIGHT <= 60 cm" if not x["has_light_within_60cm"] else "")
                for x in lan])
    L.append("")
    L.append("## 7. Errors and surprises")
    L.append("")
    er = o["errors"]
    L.append("Errors: **%d** (%.2f %% of %d actors read)." % (len(er), 100.0 * len(er) / max(1, c["actors_read"]), c["actors_read"]))
    for e in er[:60]:
        L.append("- %s: %s: %s" % (e["actor"], e["call"], e["error"]))
    L.append("")
    L.append("- Map dirty before / after: %s / %s. PIE running after: %s. Camera: %s" % (
        c["map_dirty_before"], c["map_dirty_after"], c["pie_running_after"], c["camera"]["note"]))
    zone = lambda l: 11990 <= l["x"] <= 12040 and 1490 <= l["y"] <= 2510       # in the tower AND cloister rules; tower wins
    ov = ([r["label"] for r in o["static_mesh_actors"] if zone(r["location"])] + [r["actor_label"] for r in o["component_meshes"] if zone(r["location"])]
          + [r["label"] for r in o["decals"] if zone(r["location"])] + [r["label"] for r in o["lights"] if zone(r["location"])])
    L.append("- Area rules overlap: %d placements sit at X 11990-12040, Y 1490-2510, which matches both `tower` and `cloister`; first match gives `tower` "
             "(e.g. the BP_Inscription_Cloister tablet at X 11995). Labels: %s" % (len(ov), ", ".join(sorted(set(ov))[:25])))
    hid = [r for r in o["static_mesh_actors"] if r.get("hidden")]
    if hid:
        hc = Counter(re.sub(r"[_\d]+$", "", r["label"]) + " (" + short(r["mesh"]) + ", " + r["area"] + ")" for r in hid)
        L.append("- StaticMeshActors hidden in game (bVisible false or bHiddenInGame): **%d** of %d. Largest groups: %s" % (
            len(hid), len(o["static_mesh_actors"]), "; ".join("%s x%d" % kv for kv in hc.most_common(12))))
        hg = [r for r in hid if any("WorldGridMaterial" in (s["effective"] or "") for s in r["slots"])]
        L.append("- Of those, %d use the engine `WorldGridMaterial`; visible StaticMeshActors on `WorldGridMaterial`: %d." % (
            len(hg), sum(1 for r in o["static_mesh_actors"] if not r.get("hidden") and any("WorldGridMaterial" in (s["effective"] or "") for s in r["slots"]))))
    odd = [m["name"] for m in o["other_mis"] if m["name"].startswith("MID_") or ":" in m["path"]]
    if odd:
        L.append("- Dynamic / non-asset materials found in level overrides: " + ", ".join(odd))
    un = [m["mesh"] for m in mc if m["groove"] in ("unmapped", "unknown")]
    if un:
        L.append("- Meshes with groove `unmapped` / `unknown`: " + ", ".join(un))
    nomesh = [r["label"] for r in o["static_mesh_actors"] if not r["slots"]]
    if nomesh:
        L.append("- StaticMeshActors whose mesh has no material slots: " + ", ".join(nomesh[:30]))
    nomat = sorted({"%s:%s" % (r["label"], s["slot"]) for r in o["static_mesh_actors"] for s in r["slots"] if not s["effective"]})
    if nomat:
        L.append("- Slots with no effective material: " + ", ".join(nomat[:30]))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--cache", default=None)
    args = ap.parse_args()
    if args.cache is None:
        args.cache = os.path.join(ROOT, "Saved", "p11_census_cache_test.jsonl" if args.limit else "p11_census_cache.jsonl")
    if args.out_dir is None:
        args.out_dir = os.path.join(ROOT, "Saved", "p11_test_out") if args.limit else os.path.join(ROOT, "Docs", "ArtTest", "materials")
    os.makedirs(args.out_dir, exist_ok=True)
    cs = Census(args)
    t0 = time.time()
    try:
        # ---- stage 0
        cs.pie_check()
        dirty0 = cs.call(AS, "is_dirty", {"asset_path": MAP_PKG})
        print("preflight: PIE off, map dirty =", dirty0, flush=True)
        if dirty0:
            print("WARNING: map is dirty before the census (not caused by this script)", flush=True)
        # ---- stage 1
        st1 = cs.stage1()
        print("stage1: find_actors=%d visible=%d only_visible=%d union=%d | %s" % (
            len(st1["found"]), st1["visible_count"], len(st1["only_visible"]), len(st1["union"]), st1["camera_note"]), flush=True)
        refs = st1["union"]
        if args.limit:
            refs = cs.pick_limit(refs, args.limit)
        by_class = Counter(cls_of(r) for r in st1["union"])
        skipped = Counter(cls_of(r) for r in st1["union"] if cls_of(r) in SKIP_CLASSES)
        # ---- stage 2
        recs, todo = [], [r for r in refs if cls_of(r) not in SKIP_CLASSES]
        print("stage2: %d actors to read (%d cached)" % (len(todo), sum(1 for r in todo if "a:" + r in cs.cache)), flush=True)
        for i, ref in enumerate(todo, 1):
            if i % 100 == 0:
                print("  %d/%d actors, %d calls, %.0f s, %d errors" % (i, len(todo), cs.calls, time.time() - t0, len(cs.errors)), flush=True)
            if i % 200 == 0:
                cs.pie_check()
            k = "a:" + ref
            if k in cs.cache:
                recs.append(cs.cache[k])
                continue
            rec = cs.process_actor(ref)
            if rec is None:
                continue
            cs.put(k, rec)
            recs.append(rec)
        # ---- stage 3
        mesh_refs = set()
        for r in recs:
            if r["kind"] == "sma" and r.get("mesh"):
                mesh_refs.add(r["mesh"])
            for c in r.get("components", []):
                mesh_refs.add(c["mesh"])
        minfo = {}
        for m in sorted(mesh_refs):
            try:
                minfo[m] = cs.mesh_info(m)
            except ToolErr as e:
                cs.fail(short(m), "mesh_info", e)
                minfo[m] = {"slots": [], "defaults": []}
        print("stage3: %d unique meshes" % len(minfo), flush=True)

        def slots_for(mesh, overrides):
            mi = minfo[mesh]
            out = []
            for i, name in enumerate(mi["slots"]):
                ov = overrides[i] if i < len(overrides) else None
                out.append({"slot": name, "default": mi["defaults"][i], "override": ov, "effective": ov or mi["defaults"][i]})
            return out

        # ---- stage 2b: StaticMeshActor visibility (bVisible / bHiddenInGame on the mesh component), cached
        for r in recs:
            if r["kind"] != "sma" or not r.get("mesh"):
                continue
            vk = "vis:" + r["ref"]
            if vk not in cs.cache:
                try:
                    p = J(cs.call(O, "get_properties", {"instance": {"refPath": r["ref"] + ".StaticMeshComponent0"},
                                                        "properties": ["bVisible", "bHiddenInGame"]}, r["label"]))
                    cs.put(vk, {"visible": p.get("bVisible"), "hidden_in_game": p.get("bHiddenInGame")})
                except ToolErr as e:
                    cs.fail(r["label"], "visibility", e)
                    cs.cache[vk] = {"visible": None, "hidden_in_game": None}
            v = cs.cache[vk]
            r["hidden"] = bool(v["visible"] is False or v["hidden_in_game"])
        placements = []  # one per mesh placement (SMA, or component of other actor)
        sma_out, comp_out = [], []
        for r in recs:
            if r["kind"] == "sma" and r.get("mesh"):
                sl = slots_for(r["mesh"], r["overrides"])
                sma_out.append({"label": r["label"], "path": r["ref"], "mesh": r["mesh"], "slots": sl,
                                "location": r["location"], "rotation": r["rotation"], "scale": r["scale"], "area": r["area"],
                                "hidden": r["hidden"]})
                placements.append((r, r["mesh"], sl, "sma"))
            for c in r.get("components", []):
                sl = slots_for(c["mesh"], c["overrides"])
                comp_out.append({"actor_label": r["label"], "actor_path": r["ref"], "actor_class": r["cls"],
                                 "component": c["component"], "mesh": c["mesh"], "is_ism": c["is_ism"],
                                 "instances": None, "slots": sl, "location": r["location"], "area": r["area"]})
                placements.append((r, c["mesh"], sl, "ism" if c["is_ism"] else "comp"))
        # ---- stage 4
        mi_pkgs = {}
        try:
            found = cs.call(AS, "find_assets", {"folder_path": "/Game/LastBell", "name": "",
                                                "asset_type": "/Script/Engine.MaterialInstanceConstant",
                                                "recursive": True, "tags": []})
            for x in found:
                x = R(x) if not isinstance(x, str) else x
                if x:
                    mi_pkgs[pkg_of(x)] = asset_ref(x)
        except ToolErr as e:
            cs.errors.append({"actor": "", "call": "find_assets", "error": str(e)})
        n_found_assets = len(mi_pkgs)
        used = set()
        for r, mesh, sl, _ in placements:
            for s in sl:
                for key in ("effective", "default", "override"):
                    if s[key]:
                        used.add(s[key])
        for r in recs:
            if r["kind"] == "decal" and r.get("material"):
                used.add(r["material"])
        for u in used:
            mi_pkgs.setdefault(pkg_of(u), u)
        print("stage4: %d MI assets from find_assets, %d total incl. seen in level" % (n_found_assets, len(mi_pkgs)), flush=True)
        master_params = {"textures": [], "all": None}
        try:
            lp = J(cs.call(MI, "list_parameters", {"material": {"refPath": asset_ref(MASTER_PKG)}}, "M_LB_Surface"))
            master_params["all"] = lp
            txt = []

            def walk(o):
                if isinstance(o, dict):
                    nm = o.get("name") or o.get("parameterName")
                    ty = str(o.get("type") or o.get("parameterType") or "")
                    if nm and "texture" in ty.lower():
                        txt.append(nm)
                    for v in o.values():
                        walk(v)
                elif isinstance(o, list):
                    for v in o:
                        walk(v)
            walk(lp)
            master_params["textures"] = sorted(set(txt))
        except ToolErr as e:
            cs.errors.append({"actor": "", "call": "list_parameters", "error": str(e)})
        if not master_params["textures"]:
            master_params["textures"] = ["BaseColorTex", "NormalTex", "ARMTex", "RoughnessTex", "AOTex", "MacroTex"]
            master_params["textures_fallback"] = True
        mis = {}
        for n, (pkg, ref) in enumerate(sorted(mi_pkgs.items()), 1):
            ch = cs.chain(ref)
            root = ch[-1]["path"] if ch else pkg
            mis[pkg] = {"name": short(ref), "path": pkg, "chain": [{"name": c["name"], "path": c["path"]} for c in ch],
                        "root": root, "own": {"scalars": ch[0].get("scalars", {}), "textures": ch[0].get("textures", {}),
                                              "vectors": ch[0].get("vectors", {})} if ch else {}}
            if root == MASTER_PKG:
                mis[pkg]["effective"] = cs.surface_effective(ref, master_params)
            if n % 50 == 0:
                print("  MI %d/%d" % (n, len(mi_pkgs)), flush=True)
        # actor counts per MI
        mi_actors = defaultdict(lambda: defaultdict(set))   # pkg -> area -> actor refs (mesh placements)
        mi_slots = defaultdict(set)
        mi_hidden = defaultdict(set)
        for r, mesh, sl, _ in placements:
            for s in sl:
                if s["effective"]:
                    p = pkg_of(s["effective"])
                    mi_actors[p][r["area"]].add(r["ref"])
                    if r.get("hidden"):
                        mi_hidden[p].add(r["ref"])
                    mi_slots[p].add(s["slot"])
        dec_actors = defaultdict(lambda: defaultdict(set))
        for r in recs:
            if r["kind"] == "decal" and r.get("material"):
                dec_actors[pkg_of(r["material"])][r["area"]].add(r["ref"])

        def counts(d):
            return {a: len(v) for a, v in sorted(d.items())}

        surface_mis, other_mis = [], []
        for pkg, m in mis.items():
            ac = mi_actors.get(pkg, {})
            total = len(set().union(*ac.values())) if ac else 0
            if m["root"] == MASTER_PKG:
                m = dict(m, actors=total, hidden_actors=len(mi_hidden.get(pkg, ())), by_area=counts(ac),
                         slots_filled=sorted(mi_slots.get(pkg, [])))
                surface_mis.append(m)
            elif total or pkg in dec_actors:
                da = dec_actors.get(pkg, {})
                other_mis.append({"name": m["name"], "path": pkg, "root": m["root"], "mesh_actors": total,
                                  "mesh_hidden_actors": len(mi_hidden.get(pkg, ())), "mesh_by_area": counts(ac), "decal_actors": len(set().union(*da.values())) if da else 0,
                                  "decal_by_area": counts(da)})
        surface_mis.sort(key=lambda m: (-m["actors"], m["name"]))
        other_mis.sort(key=lambda m: -(m["mesh_actors"] + m["decal_actors"]))
        # ---- grooves + mesh counts
        gpath = os.path.join(ROOT, "Tools", "materials", "grooved_meshes.json")
        gm, prules = {}, []
        if os.path.exists(gpath):
            with open(gpath, encoding="utf-8") as f:
                gj = json.load(f)
            gm, prules = gj.get("meshes", {}), gj.get("prefix_rules", [])
        mc = {}
        for r, mesh, sl, kind in placements:
            e = mc.setdefault(mesh, {"mesh": short(mesh), "path": pkg_of(mesh), "placed": 0, "sma": 0, "comp": 0, "ism": 0,
                                     "by_area": Counter(), "actors": set(), "hidden": 0})
            e["placed"] += 1
            e["hidden"] += 1 if r.get("hidden") else 0
            e[kind] += 1
            e["by_area"][r["area"]] += 1
            e["actors"].add(r["ref"])
        mesh_counts = []
        for mesh, e in sorted(mc.items(), key=lambda kv: -kv[1]["placed"]):
            nm = e["mesh"]
            g = gm.get(nm) or next((r for r in prules if nm.startswith(r["prefix"])), None)
            if g:
                groove, gsrc = g["groove"], g.get("source")
            elif nm.startswith("SM_LB_") and (mesh.startswith("/Game/LastBell/Environments/") and "CC0" not in nm):
                groove, gsrc = "unmapped", None
            else:
                groove, gsrc = "none", "not_procedural"
            mesh_counts.append({"mesh": nm, "path": e["path"], "placed": e["placed"], "sma": e["sma"], "comp": e["comp"],
                                "ism": e["ism"], "hidden": e["hidden"], "actors": len(e["actors"]), "by_area": dict(sorted(e["by_area"].items())),
                                "groove": groove, "groove_source": gsrc})
        # ---- decals / lights / lanterns
        decals = [{"label": r["label"], "path": r["ref"], "material": r.get("material"), "decal_size": r.get("decal_size"),
                   "world_size": r.get("world_size"), "location": r["location"], "rotation": r["rotation"],
                   "scale": r["scale"], "area": r["area"]} for r in recs if r["kind"] == "decal"]
        dcnt = defaultdict(Counter)
        for d in decals:
            dcnt[pkg_of(d["material"]) if d["material"] else None][d["area"]] += 1
        decal_counts = [{"material": k.rsplit("/", 1)[-1] if k else None, "path": k, "count": sum(v.values()), "by_area": dict(sorted(v.items()))}
                        for k, v in sorted(dcnt.items(), key=lambda kv: -sum(kv[1].values()))]
        lights = [{"label": r["label"], "path": r["ref"], "class": r["cls"], "location": r["location"], "rotation": r["rotation"],
                   "intensity": r.get("intensity"), "attenuation_radius": r.get("attenuation_radius"),
                   "cast_shadows": r.get("cast_shadows"), "light_function": r.get("light_function"), "area": r["area"]}
                  for r in recs if r["kind"] == "light"]
        lanterns = []
        for r, mesh, sl, kind in placements:
            nm = short(mesh)
            if "lantern" not in nm.lower() or "bracket" in nm.lower():
                continue
            glass = [s for s in sl if "glass" in (s["slot"] or "").lower()]
            b = r.get("bounds")
            near, nd = None, None
            if b and b.get("isValid", True):
                for L in lights:
                    d = dist_point_box(L["location"], b)
                    if nd is None or d < nd:
                        near, nd = L, d
            lanterns.append({"label": r["label"], "path": r["ref"], "actor_class": r["cls"], "mesh": nm, "kind": kind,
                             "area": r["area"], "location": r["location"], "bounds": b,
                             "bounds_scope": "actor" if kind != "sma" else "mesh_actor",
                             "glass_slot_materials": [{"slot": s["slot"], "material": short(s["effective"]) if s["effective"] else None,
                                                       "path": s["effective"]} for s in (glass or sl)],
                             "all_slots_listed": not glass,
                             "nearest_light": near["label"] if near else None,
                             "nearest_light_path": near["path"] if near else None,
                             "nearest_light_distance_cm": round(nd, 1) if nd is not None else None,
                             "has_light_within_60cm": (nd is not None and nd <= 60.0)})
        # ---- stage 7
        dirty1 = cs.call(AS, "is_dirty", {"asset_path": MAP_PKG})
        pie1 = cs.call(E, "IsPIERunning")
        print("postflight: map dirty =", dirty1, " PIE running =", pie1, flush=True)
        errs = list(cs.errors)
        for r in recs:
            for e in r["errs"]:
                errs.append({"actor": r.get("label") or r["ref"], "call": e["call"], "error": e["error"]})
        by_area = Counter(r["area"] for r in recs)
        out = {
            "generated": datetime.datetime.now().isoformat(timespec="seconds"), "map": MAP_PKG,
            "limit": args.limit or None,
            "counts": {"find_actors": len(st1["found"]), "visible": st1["visible_count"], "union": len(st1["union"]),
                       "only_visible": st1["only_visible"], "by_class": dict(sorted(by_class.items(), key=lambda kv: -kv[1])),
                       "by_area": dict(sorted(by_area.items())), "skipped_by_class": dict(skipped),
                       "actors_read": len(recs), "calls": cs.calls,
                       "other_area_labels": [r["label"] for r in recs if r["area"] == "other"],
                       "camera": {"restored": st1["camera_restored"], "note": st1["camera_note"], "saved": st1["camera_saved"]},
                       "map_dirty_before": dirty0, "map_dirty_after": dirty1, "pie_running_after": pie1},
            "static_mesh_actors": sma_out, "component_meshes": comp_out, "mesh_counts": mesh_counts,
            "surface_mis": surface_mis, "other_mis": other_mis, "decals": decals, "decal_counts": decal_counts,
            "lights": lights, "lanterns": lanterns, "master_parameters": master_params, "errors": errs,
        }
        write_md(out, os.path.join(args.out_dir, "census_p11.md"))      # also adds the grooved totals to out["counts"]
        write_json(os.path.join(args.out_dir, "census_p11.json"), out)
        print("done in %.0f s: %d actors read, %d calls, %d errors (%.2f %%)" % (
            time.time() - t0, len(recs), cs.calls, len(errs), 100.0 * len(errs) / max(1, len(recs))), flush=True)
    except Abort as e:
        print("ABORT:", e, "(cache kept; re-run with --resume)", flush=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
