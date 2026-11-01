"""P10-4: import the bell tower / cloister FBX, textures and MIs into the editor (editor open on L_Monastery).

Run with the project's Python (see Tools/mcp/MCP_NOTES.md), e.g.
    python import_p10.py textures
    python import_p10.py mis
    python import_p10.py carve            # D1.27 F3: MI_Cl_CarveDirt (before the F1 meshes)
    python import_p10.py meshes [--only substr] [--limit N]
    python import_p10.py check            # read-back of every mesh / MI (writes the JSON state)
    python import_p10.py report           # writes Docs/ArtTest/belltower/p10_4_import_report.md from the state

Rules: never save the map or any pre-existing package; one package per save_assets call; is_dirty is checked
after each save. The script is idempotent (existing assets are skipped, not re-imported).
Editor-side FBX options are set on the CDO before every import (they live in memory only).
"""
import json
import os
import sys
import time

sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE  # noqa: E402

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
SRC_TOWER = ROOT + r"\SourceArt\BellTower"
SRC_CLOISTER = ROOT + r"\SourceArt\Cloister"
INC = ROOT + r"\ExternalAssets\Incoming"
STATE = os.environ.get("P10_STATE", r"C:\Users\heman\AppData\Local\Temp\p10_4_state.json")

G_TOWER = "/Game/LastBell/Environments/BellTower"
G_CLOISTER = "/Game/LastBell/Environments/Cloister"
MESH_TOWER = G_TOWER + "/Meshes"
MESH_CLOISTER = G_CLOISTER + "/Meshes"
TEX = G_TOWER + "/Textures"
MAT = G_TOWER + "/Materials"
MASTER = "/Game/LastBell/Materials/Master/M_LB_Surface.M_LB_Surface"

ASSET = "editor_toolset.toolsets.asset.AssetTools"
OBJ = "editor_toolset.toolsets.object.ObjectTools"
SM = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
MI = "editor_toolset.toolsets.material_instance.MaterialInstanceTools"
TEXT = "editor_toolset.toolsets.texture.TextureTools"
FBXCDO = "/Script/UnrealEd.Default__FbxStaticMeshImportData"

ue = UE()


def ref(path):
    """Full object path from a package path."""
    return {"refPath": path + "." + path.rsplit("/", 1)[1]}


def props(instance, names):
    r = ue.call(OBJ, "get_properties", {"instance": instance, "properties": names})
    return json.loads(r) if isinstance(r, str) else r


def log(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------- save helper
def save(pkg):
    t = time.time()
    ok = ue.call(ASSET, "save_assets", {"asset_paths": [pkg]})
    dirty = ue.call(ASSET, "is_dirty", {"asset_path": pkg})
    log(f"  saved {pkg.rsplit('/', 1)[1]} ok={ok} dirty={dirty} ({time.time() - t:.1f}s)")
    if ok is not True or dirty:
        raise RuntimeError(f"save failed for {pkg}: ok={ok} dirty={dirty}")


# ---------------------------------------------------------------- textures
# (source file, asset name, compression, sRGB, lod group)
TEXTURES = []
for pack, stem, subdir in (("Metal058B", "Metal058B", "ambientcg-Metal058B"), ("Rope003", "Rope003", "ambientcg-Rope003")):
    d = f"{INC}\\{subdir}\\{stem}_2K-JPG\\{stem}_2K-JPG_"
    TEXTURES.append((d + "Color.jpg", f"T_{pack}_BC", "TC_Default", True, "TEXTUREGROUP_World"))
    TEXTURES.append((d + "NormalDX.jpg", f"T_{pack}_N", "TC_Normalmap", False, "TEXTUREGROUP_WorldNormalMap"))
    # RoughnessTex / MetalMaskTex in M_LB_Surface are SAMPLERTYPE_Alpha => TC_Alpha (same as T_Rock_064_R, T_Leaking004_R)
    TEXTURES.append((d + "Roughness.jpg", f"T_{pack}_R", "TC_Alpha", False, "TEXTUREGROUP_WorldSpecular"))
TEXTURES.append((f"{INC}\\ambientcg-Metal058B\\Metal058B_2K-JPG\\Metal058B_2K-JPG_Metalness.jpg", "T_Metal058B_M", "TC_Alpha", False, "TEXTUREGROUP_WorldSpecular"))


def do_textures():
    for src, name, comp, srgb, grp in TEXTURES:
        pkg = f"{TEX}/{name}"
        if ue.call(ASSET, "exists", {"path": pkg}):
            log("exists", name)
        else:
            assert os.path.isfile(src), src
            r = ue.call(TEXT, "import_file", {"folder_path": TEX, "asset_name": name, "source_file": src.replace("\\", "/")})
            log("imported", name, r)
        ue.call(OBJ, "set_properties", {"instance": ref(pkg), "values": json.dumps({"CompressionSettings": comp, "SRGB": srgb, "LODGroup": grp})})
        got = props(ref(pkg), ["CompressionSettings", "SRGB", "LODGroup", "MipGenSettings", "MaxTextureSize"])
        size = ue.call(TEXT, "get_size", {"texture": ref(pkg)})
        log("  ", name, got, size)
        assert got["CompressionSettings"] == comp and got["SRGB"] == srgb and got["LODGroup"] == grp, got
        save(pkg)


# ---------------------------------------------------------------- material instances
BANDS = {"MI_LB_BellBand_I": (0.32, 0.07, 0.05), "MI_LB_BellBand_II": (0.42, 0.30, 0.08),
         "MI_LB_BellBand_III": (0.10, 0.22, 0.17), "MI_LB_BellBand_IV": (0.66, 0.62, 0.52)}
MIS = {
    "MI_LB_BellBronze": {
        "tex": {"BaseColorTex": f"{TEX}/T_Metal058B_BC", "NormalTex": f"{TEX}/T_Metal058B_N",
                "RoughnessTex": f"{TEX}/T_Metal058B_R", "MetalMaskTex": f"{TEX}/T_Metal058B_M"},
        "scalar": {"BrightnessMul": 0.5, "Metallic": 0.9, "RoughnessMin": 0.45, "RoughnessMax": 0.75},
        "vector": {"BaseColorTint": (0.62, 0.45, 0.32)},
        "switch": {"bUseARM": False},
    },
    "MI_LB_Rope": {
        "tex": {"BaseColorTex": f"{TEX}/T_Rope003_BC", "NormalTex": f"{TEX}/T_Rope003_N", "RoughnessTex": f"{TEX}/T_Rope003_R"},
        "scalar": {"BrightnessMul": 1.5, "Metallic": 0.0},
        "vector": {"BaseColorTint": (1.0, 0.88, 0.70)},
        "switch": {"bUseARM": False},
    },
    "MI_LB_Sally": {
        "tex": {}, "scalar": {"RoughnessMin": 0.95, "RoughnessMax": 0.95, "Metallic": 0.0},
        "vector": {"BaseColorTint": (0.42, 0.14, 0.08)}, "switch": {},
    },
}
for _n, _t in BANDS.items():
    MIS[_n] = {"tex": {}, "scalar": {"RoughnessMin": 0.8, "RoughnessMax": 0.8, "Metallic": 0.0}, "vector": {"BaseColorTint": _t}, "switch": {}}


def near(a, b, tol=1e-4):
    return abs(a - b) <= tol


def do_mis(only=None):
    for name, spec in MIS.items():
        if only and only not in name:
            continue
        pkg = f"{MAT}/{name}"
        if not ue.call(ASSET, "exists", {"path": pkg}):
            r = ue.call(MI, "create", {"folder_path": MAT, "asset_name": name, "parent": {"refPath": MASTER}})
            log("created", name, r)
        else:
            log("exists", name)
        inst = ref(pkg)
        for p, tex in spec["tex"].items():
            ue.call(MI, "set_texture_parameter", {"instance": inst, "name": p, "value": ref(tex)})
        for p, v in spec["scalar"].items():
            ue.call(MI, "set_scalar_parameter", {"instance": inst, "name": p, "value": v})
        for p, v in spec["vector"].items():
            ue.call(MI, "set_vector_parameter", {"instance": inst, "name": p, "value": {"r": v[0], "g": v[1], "b": v[2], "a": 1.0}})
        for p, v in spec["switch"].items():
            ue.call(MI, "set_static_switch_parameter", {"instance": inst, "name": p, "value": v})
        # read back
        for p, tex in spec["tex"].items():
            g = ue.call(MI, "get_texture_parameter", {"instance": inst, "name": p})
            gp = g.get("refPath", "") if isinstance(g, dict) else str(g)
            log("  ", name, p, gp)
            assert tex.rsplit("/", 1)[1] in gp, (name, p, g)
        for p, v in spec["scalar"].items():
            g = ue.call(MI, "get_scalar_parameter", {"instance": inst, "name": p})
            log("  ", name, p, g)
            assert near(float(g), v), (name, p, g, v)
        for p, v in spec["vector"].items():
            g = ue.call(MI, "get_vector_parameter", {"instance": inst, "name": p})
            log("  ", name, p, g)
            assert all(near(g[c], x) for c, x in zip("rgb", v)) and near(g["a"], 1.0), (name, p, g, v)
        for p, v in spec["switch"].items():
            g = ue.call(MI, "get_static_switch_parameter", {"instance": inst, "name": p})
            log("  ", name, p, g)
            assert bool(g) == v, (name, p, g)
        save(pkg)


# ---------------------------------------------------------------- meshes
MI_PATH = {
    "Masonry": "/Game/LastBell/Environments/Kit/Materials/MI_Kit_Masonry",
    "Trim": "/Game/LastBell/Environments/Kit/Materials/MI_Kit_Trim",
    "Rubble": "/Game/LastBell/Environments/Kit/Materials/MI_Kit_Rubble",
    "Slate": "/Game/LastBell/Environments/Kit/Materials/MI_Kit_Slate",
    "WoodOld": "/Game/LastBell/Environments/Chapel/Materials/MI_Chapel_Wood_Old",
    "WoodWeathered": "/Game/LastBell/Environments/Courtyard/Materials/MI_Prop_Wood_Weathered",
    "Iron": "/Game/LastBell/Environments/Crypt/Materials/MI_Crypt_Iron",
    "Earth": "/Game/LastBell/Environments/Courtyard/Materials/MI_Prop_Earth",
    "Bronze": MAT + "/MI_LB_BellBronze",
    "Rope": MAT + "/MI_LB_Rope",
    "Sally": MAT + "/MI_LB_Sally",
    "Band": MAT + "/MI_LB_BellBand_III",
    "Carve": G_CLOISTER + "/Materials/MI_Cl_CarveDirt",  # D1.27 F3
}
SLOT_KEY = {"MAT_Masonry": "Masonry", "MAT_Trim": "Trim", "MAT_Rubble": "Rubble", "MAT_Slate": "Slate", "MAT_Iron": "Iron",
            "MAT_Earth": "Earth", "MAT_Bronze": "Bronze", "MAT_Rope": "Rope", "MAT_Sally": "Sally", "MAT_Band": "Band", "MAT_Carve": "Carve"}


def mi_for(mesh, slot):
    if slot == "MAT_Wood":
        if mesh.startswith("SM_LB_Tw_"):
            return MI_PATH["WoodOld"]
        return MI_PATH["WoodWeathered"]  # cloister roofs, stair-house roof, small-bell bracket
    if slot == "MAT_Rubble" and mesh == "SM_LB_Cl_CellDoorFrame_150x270":
        return MI_PATH["WoodWeathered"]  # D1.12 item 4: the C15 back panel (the frame's only MAT_Rubble geometry)
    return MI_PATH[SLOT_KEY[slot]]


NANITE_OFF = {"SM_LB_Tw_Louvre_130x450", "SM_LB_Tw_Louvre_130x450_Broken", "SM_LB_Prop_BellRope_2610",
              "SM_LB_Prop_SmallBell_A", "SM_LB_Prop_SmallBellBracket_A", "SM_LB_Prop_BellPlaque_A", "SM_LB_Prop_InscriptionTablet_A",
              # D1.27 F3: thin small lantern brackets (tablet + slabs stay Nanite)
              "SM_LB_Prop_LanternBracket_R20", "SM_LB_Prop_LanternBracket_R40", "SM_LB_Prop_LanternBracket_R60"}
EXPECT_CONVEX = {"SM_LB_Tw_BellFrame_A": 4, "SM_LB_Prop_GreatBell_A": 1, "SM_LB_Prop_SmallBell_A": 1}


def all_meshes():
    out = []
    for d, g in ((SRC_TOWER, MESH_TOWER), (SRC_CLOISTER, MESH_CLOISTER)):
        for f in sorted(os.listdir(d)):
            if f.lower().endswith(".fbx"):
                out.append((f[:-4], d + "\\" + f, g))
    return out


def convex_count(pkg):
    m = props(ref(pkg), ["BodySetup"])
    b = props(m["BodySetup"], ["AggGeom", "CollisionTraceFlag"])
    a = b["AggGeom"]
    return {k: (len(v) if isinstance(v, list) else v) for k, v in a.items() if isinstance(v, list)}, b["CollisionTraceFlag"]


def do_meshes(only=None, limit=None):
    n = 0
    for name, src, folder in all_meshes():
        if only and only not in name:
            continue
        if limit is not None and n >= limit:
            break
        pkg = f"{folder}/{name}"
        want_nanite = name not in NANITE_OFF
        if ue.call(ASSET, "exists", {"path": pkg}):
            log("exists", name)
        else:
            ue.call(OBJ, "set_properties", {"instance": {"refPath": FBXCDO}, "values": json.dumps(
                {"vertexColorImportOption": "Replace", "bBuildNanite": want_nanite, "bAutoGenerateCollision": False})})
            t = time.time()
            r = ue.call(SM, "import_file", {"folder_path": folder, "asset_name": name, "source_file": src.replace("\\", "/"),
                                           "import_materials": False, "import_textures": False, "combine_meshes": True})
            log("imported", name, f"{time.time() - t:.1f}s", r)
        n += 1
        mesh = ref(pkg)
        # Nanite
        nan = ue.call(SM, "is_nanite_enabled", {"mesh": mesh})
        if bool(nan) != want_nanite:
            ue.call(SM, "set_nanite_enabled", {"mesh": mesh, "enabled": want_nanite})
            nan = ue.call(SM, "is_nanite_enabled", {"mesh": mesh})
        assert bool(nan) == want_nanite, (name, nan)
        # collision
        shapes, flag = convex_count(pkg)
        want = EXPECT_CONVEX.get(name, 0)
        assert shapes.get("convexElems", 0) == want and sum(shapes.values()) == want, (name, shapes, want)
        assert flag == "CTF_UseDefault", (name, flag)
        # slots
        slots = ue.call(SM, "get_material_slots", {"mesh": mesh})
        for s in slots:
            mi = mi_for(name, s)
            ue.call(SM, "set_material", {"mesh": mesh, "slot_name": s, "material": ref(mi)})
            g = ue.call(SM, "get_material", {"mesh": mesh, "slot_name": s})
            gp = g.get("refPath", "") if isinstance(g, dict) else str(g)
            assert gp.startswith(mi + "."), (name, s, gp, mi)
        log(f"  {name}: nanite={nan} convex={shapes.get('convexElems', 0)} flag={flag} slots={slots}")
        save(pkg)


# ---------------------------------------------------------------- D1.27 F3: carve MI
CARVE_MI = G_CLOISTER + "/Materials/MI_Cl_CarveDirt"
CARVE_PARENT = "/Game/LastBell/Environments/Kit/Materials/MI_Kit_Trim"
CARVE_SCALAR = {"BrightnessMul": 0.30, "RoughnessMin": 0.85, "RoughnessMax": 0.95}
CARVE_VECTOR = {"BaseColorTint": (0.20, 0.18, 0.14)}


def do_carve():
    folder, name = CARVE_MI.rsplit("/", 1)
    if not ue.call(ASSET, "exists", {"path": CARVE_MI}):
        r = ue.call(MI, "create", {"folder_path": folder, "asset_name": name, "parent": ref(CARVE_PARENT)})
        log("created", name, r)
    else:
        log("exists", name)
    inst = ref(CARVE_MI)
    for p, v in CARVE_SCALAR.items():
        ue.call(MI, "set_scalar_parameter", {"instance": inst, "name": p, "value": v})
    for p, v in CARVE_VECTOR.items():
        ue.call(MI, "set_vector_parameter", {"instance": inst, "name": p, "value": {"r": v[0], "g": v[1], "b": v[2], "a": 1.0}})
    log("  parent", props(inst, ["Parent"]))
    for p, v in CARVE_SCALAR.items():
        g = ue.call(MI, "get_scalar_parameter", {"instance": inst, "name": p})
        log("  ", name, p, g)
        assert near(float(g), v), (p, g, v)
    for p, v in CARVE_VECTOR.items():
        g = ue.call(MI, "get_vector_parameter", {"instance": inst, "name": p})
        log("  ", name, p, g)
        assert all(near(g[c], x) for c, x in zip("rgb", v)), (p, g, v)
    save(CARVE_MI)


# ---------------------------------------------------------------- check / state
def do_check():
    state = {}
    reports = {}
    for f in (SRC_TOWER + r"\tower_report.json", SRC_CLOISTER + r"\cloister_report.json"):
        for r in json.load(open(f)):
            reports[r["name"]] = r
    for name, src, folder in all_meshes():
        pkg = f"{folder}/{name}"
        mesh = ref(pkg)
        rep = reports[name]
        slots = ue.call(SM, "get_material_slots", {"mesh": mesh})
        assign = {}
        for s in slots:
            g = ue.call(SM, "get_material", {"mesh": mesh, "slot_name": s})
            assign[s] = (g.get("refPath", "") if isinstance(g, dict) else str(g)).split(".")[0].rsplit("/", 1)[1]
        b = ue.call(SM, "get_bounds", {"mesh": mesh})
        dims = [round(b["max"][c] - b["min"][c], 2) for c in "xyz"]
        shapes, flag = convex_count(pkg)
        fb = ue.call(SM, "get_triangle_count", {"mesh": mesh, "lod_index": 0})
        state[name] = {"path": pkg, "nanite": bool(ue.call(SM, "is_nanite_enabled", {"mesh": mesh})), "src_tris": rep["tris"],
                       "fallback_tris": fb, "slots": assign, "dims": dims, "expected_dims": rep["dims"],
                       "bmin": [b["min"][c] for c in "xyz"], "bmax": [b["max"][c] for c in "xyz"],
                       "convex": shapes.get("convexElems", 0), "shapes": shapes, "trace_flag": flag,
                       "dirty": ue.call(ASSET, "is_dirty", {"asset_path": pkg})}
        ok = all(abs(a - e) < 0.1 for a, e in zip(dims, rep["dims"]))
        state[name]["dims_ok"] = ok
        log(name, "nanite" if state[name]["nanite"] else "-", "convex", state[name]["convex"], "dims_ok", ok, assign, "dirty", state[name]["dirty"])
    json.dump(state, open(STATE, "w"), indent=1)
    log("wrote", STATE)


def do_report(out):
    st = json.load(open(STATE))
    L = ["| Mesh | Nanite | Tris (source, Nanite fallback) | Slots -> MI | Simple collision |", "|---|---|---|---|---|"]
    for name, d in st.items():
        slots = ", ".join(f"{k} -> {v}" for k, v in d["slots"].items())
        col = f"{d['convex']} convex" if d["convex"] else "none"
        L.append(f"| `{name}` | {'on' if d['nanite'] else 'off'} | {d['src_tris']} ({d['fallback_tris']}) | {slots} | {col} |")
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    log("wrote", out)


if __name__ == "__main__":
    cmd = sys.argv[1]
    args = sys.argv[2:]
    only = args[args.index("--only") + 1] if "--only" in args else None
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else None
    if cmd == "textures":
        do_textures()
    elif cmd == "mis":
        do_mis(only)
    elif cmd == "carve":
        do_carve()
    elif cmd == "meshes":
        do_meshes(only, limit)
    elif cmd == "check":
        do_check()
    elif cmd == "report":
        do_report(args[0])
    else:
        raise SystemExit(cmd)
