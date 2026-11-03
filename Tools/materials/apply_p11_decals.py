"""P11-6 step 2: decal retune, crack textures, six courtyard leaks and 39 crack decals.

Spec: Docs/plans/P11_MATERIALS.md, section "P11-6: decals", "Step 2: editor". Run with -I, editor open on
L_Monastery, no PIE. Exactly one mode per run:
    --snapshot FILE   read-only: before-values of everything this script changes, written as JSON
    --textures        import the 8 new textures and copy the settings of the reference texture; read back + get_size
    --mis             create MI_Decal_Crack_{A,B,C}; retune the 7 existing MIs (old value must match the plan, else refuse)
    --leaks           the six courtyard Decal_Leak_* actors: rotation (0, yaw, 90), decalSize (12, 200, 50), Z 600
    --cracks          the 39 crack decals of Tools/materials/p11_crack_decals.json (idempotent by label)
    --check           read back everything; exit 1 on any mismatch
    --save            one package per save_assets call, 5 s apart, L_Monastery last (never M_LB_Surface, never a Blueprint)

Nothing saves unless --save is given. Exit codes: 0 ok, 1 mismatch or refused, 2 a tool call failed (state
unknown: run --check before anything else; never retry in a loop).
"""
import argparse
import json
import os
import struct
import sys
import time

sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE  # noqa: E402

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
MI = "editor_toolset.toolsets.material_instance.MaterialInstanceTools"
AS = "editor_toolset.toolsets.asset.AssetTools"
OB = "editor_toolset.toolsets.object.ObjectTools"
SC = "editor_toolset.toolsets.scene.SceneTools"
AC = "editor_toolset.toolsets.actor.ActorTools"
TX = "editor_toolset.toolsets.texture.TextureTools"
APP = "EditorToolset.EditorAppToolset"

MAP_PKG = "/Game/LastBell/Maps/L_Monastery"
MASTER = "/Game/LastBell/Materials/Master/M_LB_Decal"
INST = "/Game/LastBell/Materials/Instances"
MAT_TEX = "/Game/LastBell/Materials/Textures"
CHAPEL_TEX = "/Game/LastBell/Environments/Chapel/Textures"
REF_OPACITY = "/Game/LastBell/ArtTest/Decals/Leaking006/T_Leaking006_Opacity"
REF_NORMAL = "/Game/LastBell/ArtTest/Decals/Leaking006/T_Leaking006_N"
REF_SOOT = f"{CHAPEL_TEX}/T_LB_Decal_Soot_A"
GEN_MAT = os.path.join(ROOT, "ExternalAssets", "Generated", "materials")
GEN_CHAPEL = os.path.join(ROOT, "ExternalAssets", "Generated", "chapel")
CRACK_JSON = os.path.join(ROOT, "Tools", "materials", "p11_crack_decals.json")
CRACK_FOLDER = "Dressing/Decals/Cracks"
PAUSE_S = 5

# name, folder, source png, reference texture whose settings are copied
TEXTURES = (
    [(f"T_LB_Decal_Crack_{s}_Opacity", MAT_TEX, os.path.join(GEN_MAT, f"T_LB_Decal_Crack_{s}_Opacity.png"), REF_OPACITY) for s in "ABC"]
    + [(f"T_LB_Decal_Crack_{s}_N", MAT_TEX, os.path.join(GEN_MAT, f"T_LB_Decal_Crack_{s}_N.png"), REF_NORMAL) for s in "ABC"]
    + [(f"T_LB_Decal_SootSoft_{s}", CHAPEL_TEX, os.path.join(GEN_CHAPEL, f"T_LB_Decal_SootSoft_{s}.png"), REF_SOOT) for s in "AB"]
)
COPY_PROPS = ["compressionSettings", "sRGB", "lODGroup", "addressX", "addressY", "virtualTextureStreaming", "mipGenSettings",
              "filter", "neverStream", "bFlipGreenChannel", "compressionNoAlpha", "maxTextureSize", "lODBias",
              "bNormalizeNormals", "powerOfTwoMode", "mipLoadOptions"]

# New MIs: parent M_LB_Decal, every value an explicit override.
CRACK_SCALARS = {"OpacityStrength": 1.0, "OpacityContrast": 1.0, "NormalStrength": 1.0, "RoughnessScale": 0.9,
                 "DarkenStrength": 0.35, "DepthFade": 0.3, "EdgeFadeU": 0.03, "EdgeFadeV": 0.03, "DecalHalfDepthCm": 12.0}
CRACK_TINT = (0.030, 0.027, 0.024, 1.0)
NEW_MIS = [f"MI_Decal_Crack_{s}" for s in "ABC"]

ENV = "/Game/LastBell/Environments"
# Retune: (name, package, {scalar: (old, new)}, {texture param: (old asset, new asset)}). Old = effective value now.
RETUNE = [
    ("MI_Decal_Leaking006_Wall", f"{ENV}/Courtyard/Materials/MI_Decal_Leaking006_Wall",
     {"OpacityStrength": (1.6, 0.85), "OpacityContrast": (1.5, 1.1), "DarkenStrength": (0.3, 0.2),
      "EdgeFadeU": (0.12, 0.22), "EdgeFadeV": (0.06, 0.14)}, {}),
    ("MI_Chapel_DampStreak", f"{ENV}/Chapel/Materials/MI_Chapel_DampStreak",
     {"OpacityStrength": (1.6, 0.6), "OpacityContrast": (1.5, 1.0), "DarkenStrength": (0.3, 0.18),
      "EdgeFadeU": (0.12, 0.25), "EdgeFadeV": (0.06, 0.14)}, {}),
    ("MI_Decal_Leaking004_Wall", f"{ENV}/Crypt/Materials/MI_Decal_Leaking004_Wall",
     {"OpacityStrength": (1.6, 0.75), "OpacityContrast": (1.5, 1.0), "DarkenStrength": (0.3, 0.2),
      "EdgeFadeU": (0.12, 0.22), "EdgeFadeV": (0.06, 0.16)}, {}),
    ("MI_Decal_Soot_A", f"{INST}/MI_Decal_Soot_A", {"Opacity": (1.0, 0.8)},
     {"GrimeTex": ("T_LB_Decal_Soot_A", "T_LB_Decal_SootSoft_A")}),
    ("MI_Decal_Soot_B", f"{INST}/MI_Decal_Soot_B", {"Opacity": (1.0, 0.8)},
     {"GrimeTex": ("T_LB_Decal_Soot_B", "T_LB_Decal_SootSoft_B")}),
    ("MI_Decal_DustDrift", f"{INST}/MI_Decal_DustDrift", {"Opacity": (1.0, 0.75)}, {}),
    ("MI_Sa_Decal_DustDrift_Strong", f"{ENV}/Chapel/Materials/MI_Sa_Decal_DustDrift_Strong", {"Opacity": (2.0, 1.4)}, {}),
]
# Values that must NOT change on DampStreak (read back in --check).
DAMP_KEEP = {"RoughnessScale": 0.35}
DAMP_TINT = (0.12, 0.15, 0.11, 1.0)
PARENT_UNCHANGED = f"/Game/LastBell/ArtTest/Decals/Leaking006/MI_Leaking006"

# The six courtyard leaks: label -> (x, y, yaw) as read before this change.
LEAKS = {"Decal_Leak_N0": (1300.0, 2500.0, 90.0), "Decal_Leak_N1": (2900.0, 2500.0, 90.0),
         "Decal_Leak_N2": (5300.0, 2500.0, 90.0), "Decal_Leak_S0": (2500.0, -2500.0, -90.0),
         "Decal_Leak_S1": (4300.0, -2500.0, -90.0), "Decal_Leak_E0": (6000.0, -1600.0, 0.0)}
LEAK_Z, LEAK_ROLL, LEAK_SIZE = 600.0, 90.0, (12.0, 200.0, 50.0)

# Packages in the order they are saved. L_Monastery is last.
SAVE_ORDER = ([f"{MAT_TEX}/{n}" for n, f, s, r in TEXTURES if f == MAT_TEX]
              + [f"{CHAPEL_TEX}/{n}" for n, f, s, r in TEXTURES if f == CHAPEL_TEX]
              + [f"{INST}/{n}" for n in NEW_MIS] + [p for n, p, a, b in RETUNE] + [MAP_PKG])
NEVER_SAVE = ["/Game/LastBell/Materials/Master/M_LB_Surface"]
WATCH_DIRTY = NEVER_SAVE + [MASTER, "/Game/LastBell/Materials/Master/M_LB_Decal_Grime", PARENT_UNCHANGED,
                            REF_OPACITY, REF_NORMAL, "/Game/LastBell/Blueprints/Interactables/BP_Door_Base_Dungeon",
                            "/Game/LastBell/Blueprints/Interactables/BP_RitualMechanism_CryptWinch"]


def ref(pkg):
    return {"refPath": f"{pkg}.{pkg.split('/')[-1]}"}


def close(a, b, tol=1e-4):
    return abs(float(a) - float(b)) <= tol


def ang_diff(a, b):
    return (a - b + 180.0) % 360.0 - 180.0


def props(ue, obj, names):
    r = ue.call(OB, "get_properties", {"instance": obj, "properties": names})
    return json.loads(r) if isinstance(r, str) else r


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"not a PNG: {path}")
    w, h = struct.unpack(">II", head[16:24])
    return w, h


def asset_name(r):
    return (r or {}).get("refPath", "").split("/")[-1].split(".")[0] if r else None


def tex_param(ue, pkg, name):
    return asset_name(ue.call(MI, "get_texture_parameter", {"instance": ref(pkg), "name": name}))


def overridden(ue, pkg):
    p = props(ue, ref(pkg), ["scalarParameterValues", "vectorParameterValues", "textureParameterValues"])
    out = set()
    for k in ("scalarParameterValues", "vectorParameterValues", "textureParameterValues"):
        for e in p[k]:
            out.add(e["parameterInfo"]["name"])
    return out


def scalar(ue, pkg, name):
    return float(ue.call(MI, "get_scalar_parameter", {"instance": ref(pkg), "name": name}))


def vector(ue, pkg, name):
    v = ue.call(MI, "get_vector_parameter", {"instance": ref(pkg), "name": name})
    return (v["r"], v["g"], v["b"], v["a"])


def actors_by_prefix(ue, prefix):
    """label -> actor ref for every actor whose label starts with prefix."""
    out = {}
    for a in ue.call(SC, "find_actors", {"name": prefix, "tag": "", "collision_channels": []}) or []:
        lbl = ue.call(AC, "get_label", {"actor": a})
        if lbl.startswith(prefix):
            out[lbl] = a
    return out


def refuse_if_pie(ue):
    if ue.call(APP, "IsPIERunning", {}):
        print("refused: PIE is running. Nothing was changed.")
        return True
    return False


def set_scalar_explicit(ue, pkg, name, value):
    """Set a scalar and make sure it is an explicit override on this instance."""
    ue.call(MI, "set_scalar_parameter", {"instance": ref(pkg), "name": name, "value": value})
    if name not in overridden(ue, pkg):
        ue.call(MI, "set_parameter_override", {"instance": ref(pkg), "name": name, "override": True})
        ue.call(MI, "set_scalar_parameter", {"instance": ref(pkg), "name": name, "value": value})
    return close(scalar(ue, pkg, name), value) and name in overridden(ue, pkg)


# ------------------------------------------------------------------ snapshot
def do_snapshot(ue, path):
    snap = {"taken": time.strftime("%Y-%m-%d %H:%M:%S"), "note": "values read before P11-6 step 2 changed anything"}
    snap["textures_exist"] = {n: bool(ue.call(AS, "exists", {"path": f"{f}/{n}"})) for n, f, s, r in TEXTURES}
    snap["new_mis_exist"] = {n: bool(ue.call(AS, "exists", {"path": f"{INST}/{n}"})) for n in NEW_MIS}
    snap["reference_textures"] = {}
    for r in (REF_OPACITY, REF_NORMAL, REF_SOOT):
        snap["reference_textures"][r.split("/")[-1]] = props(ue, ref(r), COPY_PROPS)
    snap["retune"] = {}
    for name, pkg, scal, texs in RETUNE:
        allp = ["OpacityStrength", "RoughnessScale", "NormalStrength", "OpacityContrast", "EdgeFadeU", "EdgeFadeV", "DepthFade",
                "DarkenStrength", "DecalHalfDepthCm"] if "Leaking" in name or "Damp" in name else ["Opacity", "Roughness"]
        row = {"package": pkg, "effective": {k: scalar(ue, pkg, k) for k in allp},
               "tint": vector(ue, pkg, "BaseColorTint"), "overridden": sorted(overridden(ue, pkg)),
               "parent": props(ue, ref(pkg), ["parent"])["parent"]}
        if texs:
            row["textures"] = {k: tex_param(ue, pkg, k) for k in texs}
        snap["retune"][name] = row
    snap["leaks"] = {}
    for lbl, a in actors_by_prefix(ue, "Decal_Leak_").items():
        if lbl not in LEAKS:
            continue
        t = ue.call(AC, "get_actor_transform", {"actor": a, "worldspace": True})
        p = props(ue, {"refPath": a["refPath"] + ".NewDecalComponent"}, ["decalSize", "decalMaterial", "sortOrder"])
        snap["leaks"][lbl] = {"actor": a["refPath"], "transform": t, **p}
    snap["crack_actors_present"] = sorted(actors_by_prefix(ue, "Crack_"))
    snap["dirty_before"] = {p: ue.call(AS, "is_dirty", {"asset_path": p}) for p in WATCH_DIRTY + [MAP_PKG]}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=1)
    print("snapshot written:", path)
    print("leaks read:", len(snap["leaks"]), "| crack actors already present:", len(snap["crack_actors_present"]))
    print("dirty before:", {k.split("/")[-1]: v for k, v in snap["dirty_before"].items()})
    return 0


# ------------------------------------------------------------------ textures
def do_textures(ue):
    refs = {}
    for r in (REF_OPACITY, REF_NORMAL, REF_SOOT):
        refs[r] = props(ue, ref(r), COPY_PROPS)
    bad = 0
    for name, folder, src, rpath in TEXTURES:
        pkg = f"{folder}/{name}"
        if not os.path.isfile(src):
            print(f"STOP: source missing {src}")
            return 1
        if ue.call(AS, "exists", {"path": pkg}):
            print(f"  {name}: already in the project, import skipped", flush=True)
        else:
            r = ue.call(TX, "import_file", {"folder_path": folder, "asset_name": name, "source_file": src})
            print(f"  {name}: import_file -> {r}", flush=True)
            if not ue.call(AS, "exists", {"path": pkg}):
                print(f"STOP: {name} does not exist after import; later textures were not imported.")
                return 1
        want = refs[rpath]
        ue.call(OB, "set_properties", {"instance": ref(pkg), "values": json.dumps(want)})
        got = props(ue, ref(pkg), COPY_PROPS)
        diffs = [k for k in COPY_PROPS if got.get(k) != want.get(k)]
        size = ue.call(TX, "get_size", {"texture": ref(pkg)})
        w, h = png_size(src)
        size_ok = int(size["x"]) == w and int(size["y"]) == h
        print(f"  {name}: size {int(size['x'])}x{int(size['y'])} (png {w}x{h}) {'ok' if size_ok else 'MISMATCH'}; "
              f"{got['compressionSettings']} sRGB={got['sRGB']} {got['lODGroup']} {got['addressX']}/{got['addressY']} "
              f"maxSize={got['maxTextureSize']}; settings diffs vs {rpath.split('/')[-1]}: {diffs or 'none'}", flush=True)
        bad += (0 if size_ok and not diffs else 1)
        time.sleep(0.5)
    print("textures:", "OK" if not bad else f"{bad} PROBLEM(S)")
    return 1 if bad else 0


# ------------------------------------------------------------------ MIs
def do_mis(ue):
    # 1. validate every old value before changing anything
    problems = []
    plan = []
    for name, pkg, scal, texs in RETUNE:
        if not ue.call(AS, "exists", {"path": pkg}):
            problems.append(f"{name}: asset missing")
            continue
        for k, (old, new) in scal.items():
            cur = scalar(ue, pkg, k)
            if close(cur, new) or close(cur, old):
                plan.append((name, pkg, k, cur, new))
            else:
                problems.append(f"{name}.{k}: reads {cur:.4f}, plan says old {old}, new {new}")
        for k, (old, new) in texs.items():
            cur = tex_param(ue, pkg, k)
            if cur in (old, new):
                plan.append((name, pkg, k, cur, new))
            else:
                problems.append(f"{name}.{k}: reads {cur}, plan says old {old}, new {new}")
    for _, folder, _, _ in TEXTURES:
        pass
    for tn in ["T_LB_Decal_SootSoft_A", "T_LB_Decal_SootSoft_B"] + [f"T_LB_Decal_Crack_{s}_{k}" for s in "ABC" for k in ("Opacity", "N")]:
        f = CHAPEL_TEX if "Soot" in tn else MAT_TEX
        if not ue.call(AS, "exists", {"path": f"{f}/{tn}"}):
            problems.append(f"texture {tn} missing: run --textures first")
    if not ue.call(AS, "exists", {"path": MASTER}):
        problems.append("master M_LB_Decal missing")
    if problems:
        print("REFUSED, nothing was changed:")
        for p in problems:
            print("  -", p)
        return 1
    print(f"validated {len(plan)} values; old values match the plan (or already new)", flush=True)

    log = []
    # 2. new crack MIs
    for i, n in enumerate(NEW_MIS):
        pkg = f"{INST}/{n}"
        s = n[-1]
        if not ue.call(AS, "exists", {"path": pkg}):
            r = ue.call(MI, "create", {"folder_path": INST, "asset_name": n, "parent": ref(MASTER)})
            print(f"  create {n} -> {r}", flush=True)
            if not ue.call(AS, "exists", {"path": pkg}):
                print(f"STOP: {n} not created")
                return 1
        ok = True
        for k, (tn, folder) in {"OpacityTex": (f"T_LB_Decal_Crack_{s}_Opacity", MAT_TEX), "NormalTex": (f"T_LB_Decal_Crack_{s}_N", MAT_TEX)}.items():
            ue.call(MI, "set_texture_parameter", {"instance": ref(pkg), "name": k, "value": ref(f"{folder}/{tn}")})
            ok &= tex_param(ue, pkg, k) == tn
        ue.call(MI, "set_vector_parameter", {"instance": ref(pkg), "name": "BaseColorTint",
                                             "value": dict(zip("rgba", CRACK_TINT))})
        ok &= all(close(a, b) for a, b in zip(vector(ue, pkg, "BaseColorTint"), CRACK_TINT))
        for k, v in CRACK_SCALARS.items():
            ok &= set_scalar_explicit(ue, pkg, k, v)
        log.append((n, ok))
        print(f"  {n}: parameters set and read back {'ok' if ok else 'MISMATCH'}", flush=True)
        time.sleep(0.5)
    # 3. retune in order (Wall first, then its child DampStreak)
    for name, pkg, scal, texs in RETUNE:
        ok = True
        for k, (old, new) in scal.items():
            before = scalar(ue, pkg, k)
            good = set_scalar_explicit(ue, pkg, k, new)
            ok &= good
            print(f"  {name}.{k}: {before:.4f} -> {scalar(ue, pkg, k):.4f} (plan {old} -> {new}) {'' if good else 'MISMATCH'}", flush=True)
        for k, (old, new) in texs.items():
            before = tex_param(ue, pkg, k)
            ue.call(MI, "set_texture_parameter", {"instance": ref(pkg), "name": k, "value": ref(f"{CHAPEL_TEX}/{new}")})
            after = tex_param(ue, pkg, k)
            good = after == new
            ok &= good
            print(f"  {name}.{k}: {before} -> {after} {'' if good else 'MISMATCH'}", flush=True)
        log.append((name, ok))
        time.sleep(0.5)
    bad = [n for n, ok in log if not ok]
    print("mis:", "OK" if not bad else "MISMATCH on " + ", ".join(bad))
    return 1 if bad else 0


# ------------------------------------------------------------------ leaks
def do_leaks(ue):
    found = actors_by_prefix(ue, "Decal_Leak_")
    missing = [l for l in LEAKS if l not in found]
    if missing:
        print("REFUSED: missing", missing)
        return 1
    bad = 0
    for lbl, (x, y, yaw) in LEAKS.items():
        a = found[lbl]
        xf = {"location": {"x": x, "y": y, "z": LEAK_Z}, "rotation": {"pitch": 0.0, "yaw": yaw, "roll": LEAK_ROLL},
              "scale": {"x": 1.0, "y": 1.0, "z": 1.0}}
        ue.call(AC, "set_actor_transform", {"actor": a, "xform": xf, "worldspace": True})
        comp = {"refPath": a["refPath"] + ".NewDecalComponent"}
        ue.call(OB, "set_properties", {"instance": comp, "values": json.dumps(
            {"decalSize": {"x": LEAK_SIZE[0], "y": LEAK_SIZE[1], "z": LEAK_SIZE[2]}})})
        issues = leak_issues(ue, lbl, a)
        t = ue.call(AC, "get_actor_transform", {"actor": a, "worldspace": True})
        print(f"  {lbl}: loc ({t['location']['x']:.2f}, {t['location']['y']:.2f}, {t['location']['z']:.2f}) rot "
              f"({t['rotation']['pitch']:.2f}, {t['rotation']['yaw']:.2f}, {t['rotation']['roll']:.2f}) "
              f"{'ok' if not issues else 'MISMATCH ' + '; '.join(issues)}", flush=True)
        bad += bool(issues)
    print("leaks:", "OK" if not bad else f"{bad} MISMATCH")
    return 1 if bad else 0


def leak_issues(ue, lbl, a):
    x, y, yaw = LEAKS[lbl]
    t = ue.call(AC, "get_actor_transform", {"actor": a, "worldspace": True})
    L, R, S = t["location"], t["rotation"], t["scale"]
    issues = []
    if max(abs(L["x"] - x), abs(L["y"] - y), abs(L["z"] - LEAK_Z)) > 0.1:
        issues.append("location")
    if max(abs(ang_diff(R["pitch"], 0.0)), abs(ang_diff(R["yaw"], yaw)), abs(ang_diff(R["roll"], LEAK_ROLL))) > 0.1:
        issues.append("rotation")
    if max(abs(S["x"] - 1), abs(S["y"] - 1), abs(S["z"] - 1)) > 1e-4:
        issues.append("scale")
    p = props(ue, {"refPath": a["refPath"] + ".NewDecalComponent"}, ["decalSize", "decalMaterial"])
    sz = p["decalSize"]
    if max(abs(sz["x"] - LEAK_SIZE[0]), abs(sz["y"] - LEAK_SIZE[1]), abs(sz["z"] - LEAK_SIZE[2])) > 0.01:
        issues.append("decalSize")
    if asset_name(p["decalMaterial"]) != "MI_Decal_Leaking006_Wall":
        issues.append("material")
    return issues


# ------------------------------------------------------------------ cracks
def load_cracks():
    with open(CRACK_JSON, encoding="utf-8") as f:
        d = json.load(f)
    if len(d) != 39 or len({r["label"] for r in d}) != 39:
        raise SystemExit(f"{CRACK_JSON}: expected 39 unique labels, got {len(d)}")
    return d


def crack_xf(r):
    return {"location": r["location"], "rotation": r["rotation"], "scale": {"x": 1.0, "y": 1.0, "z": 1.0}}


def crack_issues(ue, r, a):
    issues = []
    t = ue.call(AC, "get_actor_transform", {"actor": a, "worldspace": True})
    L, R, S = t["location"], t["rotation"], t["scale"]
    w = r["location"]
    if max(abs(L["x"] - w["x"]), abs(L["y"] - w["y"]), abs(L["z"] - w["z"])) > 0.1:
        issues.append("location")
    wr = r["rotation"]
    if max(abs(ang_diff(R["pitch"], wr["pitch"])), abs(ang_diff(R["yaw"], wr["yaw"])), abs(ang_diff(R["roll"], wr["roll"]))) > 0.1:
        issues.append("rotation")
    if max(abs(S["x"] - 1), abs(S["y"] - 1), abs(S["z"] - 1)) > 1e-4:
        issues.append("scale")
    p = props(ue, {"refPath": a["refPath"] + ".NewDecalComponent"}, ["decalSize", "decalMaterial", "sortOrder"])
    sz, e = p["decalSize"], r["size"]
    if max(abs(sz["x"] - e["x"]), abs(sz["y"] - e["y"]), abs(sz["z"] - e["z"])) > 0.01:
        issues.append("decalSize")
    if asset_name(p["decalMaterial"]) != r["mi"]:
        issues.append("material")
    if int(p["sortOrder"]) != 1:
        issues.append("sortOrder")
    return issues


def do_cracks(ue):
    recs = load_cracks()
    for n in NEW_MIS:
        if not ue.call(AS, "exists", {"path": f"{INST}/{n}"}):
            print(f"REFUSED: {n} missing; run --mis first")
            return 1
    existing = actors_by_prefix(ue, "Crack_")
    placed, left_out = 0, []
    for i, r in enumerate(recs):
        lbl = r["label"]
        try:
            a = existing.get(lbl)
            if a is None:
                a = ue.call(SC, "add_to_scene_from_class", {"actor_type": {"refPath": "/Script/Engine.DecalActor"},
                                                            "name": lbl, "xform": crack_xf(r)})
                if not a:
                    raise RuntimeError("spawn returned nothing")
                a = a if isinstance(a, dict) else {"refPath": a}
            ue.call(AC, "set_actor_transform", {"actor": a, "xform": crack_xf(r), "worldspace": True})
            ue.call(AC, "set_label", {"actor": a, "label": lbl})
            ue.call(SC, "set_actor_folder", {"actor": a, "folder_path": CRACK_FOLDER})
            comp = {"refPath": a["refPath"] + ".NewDecalComponent"}
            ue.call(OB, "set_properties", {"instance": comp, "values": json.dumps({
                "decalMaterial": ref(f"{INST}/{r['mi']}"),
                "decalSize": {"x": r["size"]["x"], "y": r["size"]["y"], "z": r["size"]["z"]},
                "sortOrder": 1})})
            issues = crack_issues(ue, r, a)
        except Exception as e:
            left_out.append((lbl, "tool error: " + str(e)[:200]))
            print(f"  [{i + 1:2}/39] {lbl}: FAILED {str(e)[:200]}", flush=True)
            if len(left_out) >= 3:
                print("STOP: 3 failures; remaining cracks were not attempted. State is partial: run --check.")
                return 2
            continue
        if issues:
            left_out.append((lbl, "read-back mismatch: " + ", ".join(issues)))
            print(f"  [{i + 1:2}/39] {lbl}: MISMATCH {issues}", flush=True)
        else:
            placed += 1
            print(f"  [{i + 1:2}/39] {lbl}: ok ({r['mi'][-1]})", flush=True)
    print(f"cracks placed and read back: {placed}/39; left out or mismatched: {left_out or 'none'}")
    return 0 if placed == 39 else 1


# ------------------------------------------------------------------ check
def do_check(ue):
    bad = []
    n_ok = 0

    def rec(ok, what):
        nonlocal n_ok
        if ok:
            n_ok += 1
        else:
            bad.append(what)

    # textures
    refs = {r: props(ue, ref(r), COPY_PROPS) for r in (REF_OPACITY, REF_NORMAL, REF_SOOT)}
    t_ok = 0
    for name, folder, src, rpath in TEXTURES:
        pkg = f"{folder}/{name}"
        if not ue.call(AS, "exists", {"path": pkg}):
            rec(False, f"texture {name} missing")
            continue
        got = props(ue, ref(pkg), COPY_PROPS)
        diffs = [k for k in COPY_PROPS if got.get(k) != refs[rpath].get(k)]
        size = ue.call(TX, "get_size", {"texture": ref(pkg)})
        w, h = png_size(src)
        ok = not diffs and (int(size["x"]), int(size["y"])) == (w, h)
        t_ok += ok
        rec(ok, f"texture {name}: diffs {diffs} size {size} vs {(w, h)}")
    print(f"textures: {t_ok}/{len(TEXTURES)} exist with the reference settings and PNG size")

    # new MIs
    m_ok = 0
    for n in NEW_MIS:
        pkg = f"{INST}/{n}"
        s = n[-1]
        if not ue.call(AS, "exists", {"path": pkg}):
            rec(False, f"MI {n} missing")
            continue
        issues = []
        pr = props(ue, ref(pkg), ["parent"])["parent"]
        if asset_name(pr) != "M_LB_Decal":
            issues.append(f"parent {asset_name(pr)}")
        ov = overridden(ue, pkg)
        for k, v in CRACK_SCALARS.items():
            if not close(scalar(ue, pkg, k), v):
                issues.append(f"{k}={scalar(ue, pkg, k)}")
            if k not in ov:
                issues.append(f"{k} not an explicit override")
        if not all(close(a, b) for a, b in zip(vector(ue, pkg, "BaseColorTint"), CRACK_TINT)):
            issues.append("BaseColorTint")
        if tex_param(ue, pkg, "OpacityTex") != f"T_LB_Decal_Crack_{s}_Opacity":
            issues.append("OpacityTex")
        if tex_param(ue, pkg, "NormalTex") != f"T_LB_Decal_Crack_{s}_N":
            issues.append("NormalTex")
        for k in ("BaseColorTex", "RoughnessTex"):   # get_texture_parameter returns the effective (default) texture
            if k in ov:
                issues.append(f"{k} overridden (should stay master default)")
        m_ok += not issues
        rec(not issues, f"MI {n}: {issues}")
    print(f"new MIs: {m_ok}/3 as specified")

    # retuned MIs
    r_ok = 0
    for name, pkg, scal, texs in RETUNE:
        issues = []
        ov = overridden(ue, pkg)
        for k, (old, new) in scal.items():
            v = scalar(ue, pkg, k)
            if not close(v, new):
                issues.append(f"{k}={v} want {new}")
            if k not in ov:
                issues.append(f"{k} not explicit")
        for k, (old, new) in texs.items():
            if tex_param(ue, pkg, k) != new:
                issues.append(f"{k}={tex_param(ue, pkg, k)} want {new}")
        if name == "MI_Chapel_DampStreak":
            for k, v in DAMP_KEEP.items():
                if not close(scalar(ue, pkg, k), v):
                    issues.append(f"{k} changed to {scalar(ue, pkg, k)}")
            if not all(close(a, b) for a, b in zip(vector(ue, pkg, "BaseColorTint"), DAMP_TINT)):
                issues.append("BaseColorTint changed")
        r_ok += not issues
        rec(not issues, f"retune {name}: {issues}")
    print(f"retuned MIs: {r_ok}/{len(RETUNE)} at the new values (explicit overrides)")

    # leaks
    found = actors_by_prefix(ue, "Decal_Leak_")
    l_ok = 0
    for lbl in LEAKS:
        if lbl not in found:
            rec(False, f"leak {lbl} missing")
            continue
        iss = leak_issues(ue, lbl, found[lbl])
        l_ok += not iss
        rec(not iss, f"leak {lbl}: {iss}")
    print(f"leaks: {l_ok}/6 at Z {LEAK_Z:g}, roll {LEAK_ROLL:g}, size {LEAK_SIZE}")

    # cracks
    recs = load_cracks()
    present = actors_by_prefix(ue, "Crack_")
    c_ok = 0
    for r in recs:
        a = present.get(r["label"])
        if a is None:
            rec(False, f"crack {r['label']} missing")
            continue
        iss = crack_issues(ue, r, a)
        folder_ok = True
        c_ok += (not iss) and folder_ok
        rec(not iss, f"crack {r['label']}: {iss}")
    extra = sorted(set(present) - {r["label"] for r in recs})
    rec(not extra, f"unexpected Crack_ actors: {extra}")
    print(f"cracks: {c_ok}/39 at the listed transform, size, MI and sortOrder 1; actors labelled Crack_*: {len(present)}; unexpected: {extra or 'none'}")
    inf = ue.call(SC, "get_actors_in_folder", {"folder_path": CRACK_FOLDER})
    rec(len(inf) == 39, f"folder {CRACK_FOLDER} holds {len(inf)} actors, expected 39")
    print(f"folder {CRACK_FOLDER}: {len(inf)} actors")

    dirty = {p.split("/")[-1]: ue.call(AS, "is_dirty", {"asset_path": p}) for p in WATCH_DIRTY + SAVE_ORDER}
    print("dirty now:", sorted(k for k, v in dirty.items() if v) or "none")
    total = n_ok + len(bad)
    print(f"CHECK: {n_ok}/{total} items ok" + ("" if not bad else f"; {len(bad)} MISMATCH:"))
    for b in bad:
        print("  -", b)
    return 1 if bad else 0


# ------------------------------------------------------------------ save
def do_save(ue):
    dirty_before = {p: ue.call(AS, "is_dirty", {"asset_path": p}) for p in SAVE_ORDER + NEVER_SAVE}
    print("not saved on purpose:", {p.split("/")[-1]: dirty_before[p] for p in NEVER_SAVE})
    for i, pkg in enumerate(SAVE_ORDER):
        assert pkg not in NEVER_SAVE and "/BP_" not in pkg
        if i:
            time.sleep(PAUSE_S)
        res = ue.call(AS, "save_assets", {"asset_paths": [pkg]})
        dirty = ue.call(AS, "is_dirty", {"asset_path": pkg})
        print(f"  save {pkg.split('/')[-1]}: was dirty {dirty_before[pkg]}, returned {res}, is_dirty {dirty}", flush=True)
        if res is not True or dirty is not False:
            print(f"STOP: {pkg} did not save cleanly; later packages were not saved.")
            return 1
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", metavar="FILE")
    for m in ("textures", "mis", "leaks", "cracks", "check", "save"):
        g.add_argument("--" + m, action="store_true")
    a = ap.parse_args()
    ue = UE()
    try:
        if refuse_if_pie(ue):
            return 1
        if a.snapshot:
            return do_snapshot(ue, a.snapshot)
        if a.textures:
            return do_textures(ue)
        if a.mis:
            return do_mis(ue)
        if a.leaks:
            return do_leaks(ue)
        if a.cracks:
            return do_cracks(ue)
        if a.check:
            return do_check(ue)
        return do_save(ue)
    except Exception as e:
        print(f"TOOL CALL FAILED: {str(e)[:600]}\nState unknown. Run --check before doing anything else; do not retry in a loop.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
