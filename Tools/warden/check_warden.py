"""check_warden.py -- P12-4: read-only check of the owner's Warden Art V5 as imported into this project.

    python -I Tools/warden/check_warden.py [--validation PATH]

Uses Tools/mcp/ue.py (the editor must be open, MCP server on http://127.0.0.1:8000/mcp).  READ-ONLY: it calls only
get_* / list_* / exists / is_dirty tools.  It never saves, imports, moves or edits anything.

Expected values come from the owner's report C:\\Hemant\\Prj\\Learning\\Warden\\output\\unreal_validation\\Reports\\validation-v5.json
(read-only for us; override with --validation).  Prints one PASS/FAIL line per check and "n/n"; exit code 1 on any FAIL.

Checks (all under /Game/LastBell/Characters/Warden/):
  mesh      SK_Warden: 110 bones, first bone `root`; height 290 +/- 1 (bounds Z size); 3 LODs, vertices per LOD and 6 sections
            per LOD as in the report; each of the 6 slots has its expected material (SLOT_MATERIAL: since P12-7 round 1 four
            slots hold new MIs, Leather its parent and Wool its MI); physics asset and skeleton assigned.
  textures  the 20 textures: size, sRGB and compression settings equal to the report.
  clips     AN_Warden_Idle 4 s, Walk 2 s, DoorwayStoop 3 s (+/- 0.01), all on SK_Warden_Skeleton (the mesh's skeleton).
  wool      MI_Warden_Wool: Weave Scale 109.94, Detail Strength 0.5, Wetness 0.15, Cloth Brightness 0.25 (P12-7 round 1; the report's
            own value is 0.4 and is checked against REPORT_WOOL).
  place     nothing left under /Game/WardenArtV5, and no dependency of a Warden asset points there.
Informational (not counted): texture memory estimate from the Format and Dimensions tags.

A later task (P12-8) adds a `--bp` mode that checks BP_Warden's use of the mesh; it plugs in at CHECK_GROUPS below.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Tools", "mcp"))
from ue import UE  # noqa: E402

AS = "editor_toolset.toolsets.asset.AssetTools"
OB = "editor_toolset.toolsets.object.ObjectTools"
SK = "editor_toolset.toolsets.skeletal_mesh.SkeletalMeshTools"
TX = "editor_toolset.toolsets.texture.TextureTools"
MI = "editor_toolset.toolsets.material_instance.MaterialInstanceTools"

BASE = "/Game/LastBell/Characters/Warden"
OLD = "/Game/WardenArtV5"
DEFAULT_VALIDATION = r"C:\Hemant\Prj\Learning\Warden\output\unreal_validation\Reports\validation-v5.json"
CLIPS = {"AN_Warden_Idle": 4.0, "AN_Warden_Walk": 2.0, "AN_Warden_DoorwayStoop": 3.0}
WOOL = {"Weave Scale": 109.94, "Detail Strength": 0.5, "Wetness": 0.15, "Cloth Brightness": 0.25}   # Cloth Brightness: P12-7 round 1
REPORT_WOOL = dict(WOOL, **{"Cloth Brightness": 0.4})   # what the owner's report has
# slot name -> material the slot must hold (P12-7 round 1: four MIs on the Warden parents, Leather unchanged)
SLOT_MATERIAL = {"M_Warden_Wool": "MI_Warden_Wool", "M_Warden_BellMetal": "MI_Warden_BellMetal",
                 "M_Warden_RustedIron": "MI_Warden_RustedIron", "M_Warden_Skin": "MI_Warden_Skin",
                 "M_Warden_Leather": "M_Warden_Leather", "M_Warden_ChainIron": "MI_Warden_ChainIron"}
# bytes per pixel of the GPU formats this project's textures use (informational memory estimate only)
BPP = {"DXT1": 0.5, "DXT5": 1.0, "BC4": 0.5, "BC5": 1.0, "BC7": 1.0, "BGRA8": 4.0, "G8": 1.0}


def ref(path):
    return {"refPath": "%s.%s" % (path, path.rsplit("/", 1)[1])}


def js(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return v
    return v


class Result:
    def __init__(self):
        self.passed = 0
        self.total = 0

    def check(self, ok, name, detail=""):
        self.total += 1
        self.passed += 1 if ok else 0
        print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  -- " + detail) if detail else ""))
        return ok


def guard(res, name, fn):
    """Run one check group; an exception counts as one FAIL, not a crash."""
    try:
        fn()
    except Exception as ex:  # noqa: BLE001
        res.check(False, name + " (could not be read)", "%s: %s" % (type(ex).__name__, str(ex)[:300]))


def tex_enum(s):
    """'<TextureCompressionSettings.TC_NORMALMAP: 1>' (report) or 'TC_Normalmap' (editor) -> 'TC_NORMALMAP' upper-cased."""
    s = str(s)
    if "." in s and ":" in s:
        s = s.split(".", 1)[1].split(":", 1)[0]
    return s.strip(">").upper()


def check_mesh(ue, res, rep):
    m = rep["mesh"]
    mesh = ref(BASE + "/Meshes/SK_Warden")
    bones = ue.call(SK, "get_bone_names", {"mesh": mesh})
    res.check(len(bones) == m["bone_count"], "bones == %d" % m["bone_count"], "got %d" % len(bones))
    res.check(bones and bones[0] == m["root"], "first bone is `%s`" % m["root"], "got %r" % (bones[:1],))
    b = ue.call(SK, "get_bounds", {"mesh": mesh})
    height = 2 * b["boxExtent"]["z"]
    res.check(abs(height - 290.0) <= 1.0, "height 290 +/- 1", "bounds Z size %.2f (origin z %.2f)" % (height, b["origin"]["z"]))
    lods = ue.call(SK, "get_lod_count", {"mesh": mesh})
    res.check(lods == m["lod_count"], "LOD count == %d" % m["lod_count"], "got %d" % lods)
    for i in range(m["lod_count"]):
        v = ue.call(SK, "get_vertex_count", {"mesh": mesh, "lod_index": i})
        s = ue.call(SK, "get_section_count", {"mesh": mesh, "lod_index": i})
        res.check(v == m["lod_vertices"][i] and s == m["sections"][i],
                  "LOD%d vertices %d, sections %d" % (i, m["lod_vertices"][i], m["sections"][i]), "got %d / %d" % (v, s))
    slots = ue.call(SK, "get_material_slots", {"mesh": mesh})
    res.check(len(slots) == 6, "6 material slots", "got %s" % slots)
    for slot in slots:
        want_path = BASE + "/Materials/" + SLOT_MATERIAL.get(slot, "?")
        got = ue.call(SK, "get_material", {"mesh": mesh, "slot_name": slot})
        got = got.get("refPath", "") if isinstance(got, dict) else str(got)
        res.check(got.split(".")[0] == want_path, "slot %s -> %s" % (slot, want_path.rsplit("/", 1)[1]), "got %s" % got)
    pa = ue.call(SK, "get_physics_asset", {"mesh": mesh})
    pa = pa.get("refPath", "") if isinstance(pa, dict) else str(pa)
    res.check(pa.split(".")[0] == BASE + "/Meshes/SK_Warden_PhysicsAsset", "physics asset assigned", "got %s" % pa)
    sk = ue.call(SK, "get_skeleton", {"mesh": mesh})
    sk = sk.get("refPath", "") if isinstance(sk, dict) else str(sk)
    res.check(sk.split(".")[0] == BASE + "/Meshes/SK_Warden_Skeleton", "skeleton is SK_Warden_Skeleton", "got %s" % sk)


def check_textures(ue, res, rep):
    texs = rep["textures"]
    res.check(len(texs) == 20, "20 textures in the report", "got %d" % len(texs))
    found = ue.call(AS, "find_assets", {"folder_path": BASE + "/Textures", "name": ""})
    res.check(len(found) == 20, "20 textures in %s/Textures" % BASE, "got %d" % len(found))
    total = 0.0
    for t in texs:
        path = BASE + "/Textures/" + t["name"]
        r = ref(path)
        props = js(ue.call(OB, "get_properties", {"instance": r, "properties": ["SRGB", "CompressionSettings"]}))
        size = ue.call(TX, "get_size", {"texture": r})
        want_comp = tex_enum(t["compression"])
        got_comp = tex_enum(props["CompressionSettings"])
        ok = (props["SRGB"] == t["srgb"] and got_comp == want_comp
              and [size["x"], size["y"]] == t["size"])
        res.check(ok, t["name"], "size %dx%d sRGB %s %s (want %dx%d sRGB %s %s)" % (
            size["x"], size["y"], props["SRGB"], got_comp, t["size"][0], t["size"][1], t["srgb"], want_comp))
        tags = ue.call(AS, "get_asset_tags", {"asset_path": path})
        fmt = str(tags.get("Format", "?"))
        bpp = BPP.get(fmt.replace("PF_", ""), None)
        if bpp:
            total += size["x"] * size["y"] * bpp * 4.0 / 3.0  # full mip chain
    print("INFO  texture memory estimate (all mips, GPU format from the Format tag): %.1f MiB" % (total / 1048576.0))


def check_clips(ue, res, rep):
    mesh_skel = ue.call(SK, "get_skeleton", {"mesh": ref(BASE + "/Meshes/SK_Warden")})
    mesh_skel = (mesh_skel.get("refPath", "") if isinstance(mesh_skel, dict) else str(mesh_skel)).split(".")[0]
    for name, secs in CLIPS.items():
        r = ref(BASE + "/Anims/" + name)
        p = js(ue.call(OB, "get_properties", {"instance": r, "properties": ["Skeleton", "SequenceLength"]}))
        sk = p["Skeleton"].get("refPath", "").split(".")[0] if isinstance(p["Skeleton"], dict) else str(p["Skeleton"])
        res.check(abs(p["SequenceLength"] - secs) <= 0.01 and sk == mesh_skel,
                  "%s %g s on the mesh's skeleton" % (name, secs), "length %.3f, skeleton %s" % (p["SequenceLength"], sk))


def check_wool(ue, res, rep):
    mi = ref(BASE + "/Materials/MI_Warden_Wool")
    for k, want in WOOL.items():
        got = ue.call(MI, "get_scalar_parameter", {"instance": mi, "name": k})
        res.check(abs(got - want) <= 0.005 + 1e-9 * abs(want), "MI_Warden_Wool %s == %g" % (k, want), "got %.6g" % got)
    # the report's own numbers must agree with the constants above (so a changed report is noticed)
    for k, want in REPORT_WOOL.items():
        rv = rep["wool_parameters"][k]
        res.check(abs(rv - want) <= 0.005, "report wool %s == %g" % (k, want), "report has %.6g" % rv)


def check_place(ue, res, rep):
    res.check(not ue.call(AS, "exists", {"path": OLD}), "%s is gone from the editor" % OLD)
    res.check(not os.path.exists(os.path.join(ROOT, "Content", "WardenArtV5")), "Content/WardenArtV5 is gone from disk")
    assets = ue.call(AS, "find_assets", {"folder_path": BASE, "name": ""})
    res.check(len(assets) >= 33, ">= 33 assets under %s" % BASE, "got %d" % len(assets))
    bad = []
    for a in assets:
        for d in ue.call(AS, "get_dependencies", {"asset_path": a}):
            if OLD in d:
                bad.append("%s -> %s" % (a, d))
    res.check(not bad, "no dependency points at %s" % OLD, "; ".join(bad[:3]))


# (name, function).  P12-8 appends ("blueprint", check_bp) here when run with --bp.
CHECK_GROUPS = [("mesh", check_mesh), ("textures", check_textures), ("clips", check_clips),
                ("wool", check_wool), ("place", check_place)]


def main():
    path = DEFAULT_VALIDATION
    if "--validation" in sys.argv:
        path = sys.argv[sys.argv.index("--validation") + 1]
    with open(path, "r", encoding="utf-8") as f:
        rep = json.load(f)
    ue = UE()
    res = Result()
    for name, fn in CHECK_GROUPS:
        guard(res, name, lambda fn=fn: fn(ue, res, rep))
    print("%d/%d" % (res.passed, res.total))
    return 0 if res.passed == res.total else 1


if __name__ == "__main__":
    sys.exit(main())
