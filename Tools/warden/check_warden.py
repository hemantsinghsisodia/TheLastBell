"""check_warden.py -- P12-4 (V5), updated for the owner's Warden V5.5 (D-091): read-only check of the Warden as imported.

    python -I Tools/warden/check_warden.py [--validation PATH]

Uses Tools/mcp/ue.py (the editor must be open, MCP server on http://127.0.0.1:8000/mcp).  READ-ONLY: it calls only
get_* / list_* / exists / is_dirty tools.  It never saves, imports, moves or edits anything.

Expected values come from the owner's report C:\\Hemant\\Prj\\Learning\\Warden\\output\\unreal_validation\\Reports\\validation-v5_1.json
(read-only for us; override with --validation; the owner wrote no validation report for V5.5, so this is the newest one: its
bone count, root, texture list and wool values still hold) plus MESH_V5_5 below, which holds what Unreal itself reports for
the V5.5 mesh (the report's LOD vertex counts are the V5.1 mesh's).  Prints one PASS/FAIL line per check and "n/n"; exit code
1 on any FAIL.

Checks (all under /Game/LastBell/Characters/Warden/):
  mesh      SK_Warden: 110 bones, first bone `root`; height 290 +/- 1 (bounds Z size); 3 LODs, vertices per LOD (MESH_V5_5:
            75,603 / 45,003 / 22,347; V5 had 65,983 / 39,159 / 24,080) and 6 sections per LOD; each of the 6 slots has its expected material (SLOT_MATERIAL: since P12-7 round 1 four
            slots hold new MIs, Leather its parent and Wool its MI); physics asset and skeleton assigned.
  textures  the 20 textures (V5.1 sets, plus the V5.4 skin set): size, sRGB and compression settings equal to the report.
  clips     AN_Warden_Idle 4 s, Walk 2 s, DoorwayStoop 3 s (+/- 0.01), all on SK_Warden_Skeleton (the mesh's skeleton).
  wool      MI_Warden_Wool: Weave Scale 109.94, Detail Strength 0.5, Wetness 0.15, Cloth Brightness 0.25 (P12-7 round 1; the report's
            own value is 0.4 and is checked against REPORT_WOOL).
  skin      MI_Warden_Skin: parent M_Warden_Skin, `Skin Brightness` 0.12 (the V5.4 parent has that scalar, default 0.14; V5's
            round 1 used a `BaseColorMul` of 0.55 that V5.5 does not have).
  place     nothing left under the four temporary V5.5 folders /Game/WardenArtV5, _1, _4, _5 (editor and disk), and no dependency
            of a Warden asset points there.
Informational (not counted): texture memory estimate from the Format and Dimensions tags; the skeleton's and the physics
asset's preview-mesh tags (the physics asset's still names the old /Game/WardenArtV5 mesh: no tool can write it).

`--disk` (P12-8, updated for fix set 1) loads L_Monastery and L_Test_Warden from disk in a separate headless process (mirror project) and checks
the placed Warden (V5.5 art, TellLight 5000 / 700 / (110, 0, 235)) and, in L_Monastery, both BP_WardenApparition instances with every section 3
value and no BP_WardenSilhouette, as saved. `--bp` (P12-8, updated for fix set 1) runs only the Blueprint group (check_bp, below): BP_Warden uses the
V5.5 art; capsule and DA_WardenTuning are unchanged against Docs/ArtTest/warden/p12_8_before.json; BP_WardenApparition and the two placed
instances (F3); the attack light, mask glow and graph wiring of BP_Warden (F4, the checks live in apply_p12f_blueprints.py). The old
BP_WardenSilhouette Blueprint and SM_LB_Warden_Silhouette still exist (deleted after a restart) and are not required to be gone. Still read-only.
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
OLD_FOLDERS = ["WardenArtV5", "WardenArtV5_1", "WardenArtV5_4", "WardenArtV5_5"]   # the owner's version folders, copied in as temporary paths
# What Unreal reports for the owner's V5.5 mesh (step 1 of "Bringing in V5.5", read with SkeletalMeshTools). The owner's
# validation-v5_1.json has 73303 / 45065 / 22517 (the V5.1 mesh); V5 had 65983 / 39159 / 24080.
MESH_V5_5 = {"lod_vertices": [75603, 45003, 22347], "sections": [6, 6, 6]}
SKIN_BRIGHTNESS = 0.12
# The one dependency allowed to name a temporary folder: the physics asset's editor-only preview-mesh soft reference still
# names the owner's V5 path /Game/WardenArtV5/Meshes/SK_Warden (their mesh now lives at V5_5 and was moved). No MCP tool can
# write PhysicsAsset's PreviewSkeletalMesh (not an exposed property; assign_physics_asset does not set it). It is editor-only
# data, not used at runtime. Reported to the lead; fixed by opening the physics asset once in the Physics Asset Editor.
KNOWN_DANGLING = set()  # the owner re-saved the physics asset with the new preview mesh (2026-11-05)
DEFAULT_VALIDATION = r"C:\Hemant\Prj\Learning\Warden\output\unreal_validation\Reports\validation-v5_1.json"
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
    m = dict(rep["mesh"], **MESH_V5_5)
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


def check_skin(ue, res, rep):
    mi = ref(BASE + "/Materials/MI_Warden_Skin")
    par = js(ue.call(OB, "get_properties", {"instance": mi, "properties": ["parent"]}))["parent"]
    par = (par.get("refPath", "") if isinstance(par, dict) else str(par)).split(".")[0]
    res.check(par == BASE + "/Materials/M_Warden_Skin", "MI_Warden_Skin parent is M_Warden_Skin", "got %s" % par)
    got = ue.call(MI, "get_scalar_parameter", {"instance": mi, "name": "Skin Brightness"})
    res.check(abs(got - SKIN_BRIGHTNESS) <= 1e-4, "MI_Warden_Skin Skin Brightness == %g" % SKIN_BRIGHTNESS, "got %.6g" % got)


def check_place(ue, res, rep):
    for f in OLD_FOLDERS:
        res.check(not ue.call(AS, "exists", {"path": "/Game/" + f}), "/Game/%s is gone from the editor" % f)
    for f in OLD_FOLDERS:
        res.check(not os.path.exists(os.path.join(ROOT, "Content", f)), "Content/%s is gone from disk" % f)
    assets = ue.call(AS, "find_assets", {"folder_path": BASE, "name": ""})
    res.check(len(assets) >= 38, ">= 38 assets under %s (33 owner assets, 4 tuned MIs, the silhouette)" % BASE, "got %d" % len(assets))
    for a in assets:
        if "Redirector" in str(ue.call(AS, "get_asset_class", {"asset_path": a})):
            res.check(False, "no redirector under %s" % BASE, a)
    bad = []
    for a in assets:
        for d in ue.call(AS, "get_dependencies", {"asset_path": a}):
            if OLD in d:      # also matches _1, _4, _5
                if (a, d) in KNOWN_DANGLING:
                    print("INFO  known exemption (preview mesh, editor-only): %s -> %s" % (a, d))
                else:
                    bad.append("%s -> %s" % (a, d))
    res.check(not bad, "no dependency points at %s*" % OLD, "; ".join(bad[:3]))
    for n, label in (("SK_Warden_Skeleton", "skeleton"), ("SK_Warden_PhysicsAsset", "physics asset")):
        try:
            tag = ue.call(AS, "get_asset_tags", {"asset_path": BASE + "/Meshes/" + n}).get("PreviewSkeletalMesh", "?")
        except Exception as ex:  # noqa: BLE001
            tag = "unreadable (%s)" % str(ex)[:80]
        print("INFO  %s preview mesh tag: %s" % (label, tag))


def check_bp(ue, res, rep, snap_path=None):
    """--bp: BP_Warden uses the V5.5 art; capsule and tuning are unchanged; the attack light and mask glow (P12 fix set 1, F4); the new
    BP_WardenApparition and both placed instances (F3).
    Read-only (find_nodes / get_node_infos / get_properties only; never read_graph_dsl, which spawns orphan events).
    Expected values are the plans': apply_p12_warden.py (art), apply_p12f_blueprints.py (appearances, light); 'unchanged' means equal to
    Docs/ArtTest/warden/p12_8_before.json. A Blueprint property can't be read after a reload from here, so this reads the in-memory state.
    The old BP_WardenSilhouette Blueprint and SM_LB_Warden_Silhouette still exist (deleted later, after a restart): they are not required
    to be gone, but no BP_WardenSilhouette may be placed in the map."""
    sys.path.insert(0, HERE)
    import apply_p12_warden as ap  # noqa: E402
    import apply_p12f_blueprints as apf  # noqa: E402
    snap_path = snap_path or ap.DEFAULT_SNAP
    with open(snap_path, "r", encoding="utf-8") as f:
        snap = json.load(f)

    # --- socket
    m = ap.pkg_ref(ap.MESH_PKG)
    names = ue.call(ap.SK, "get_socket_names", {"mesh": m})
    ok = ap.SOCKET in names
    bone = ue.call(ap.SK, "get_socket_bone", {"mesh": m, "socket_name": ap.SOCKET}) if ok else None
    t = ue.call(ap.SK, "get_socket_transform", {"mesh": m, "socket_name": ap.SOCKET}) if ok else None
    zero = ok and ap.vec_close(t["location"], {"x": 0, "y": 0, "z": 0}) and ap.rot_close(t["rotation"], {"pitch": 0, "yaw": 0, "roll": 0})
    res.check(ok and bone == ap.BONE and zero, "SK_Warden socket `mask` on bone `head`, zero offset", "sockets %s, bone %s, transform %s" % (names, bone, t))

    # --- CharacterMesh0 (template)
    cm = ap.read_props(ue, ap.CM0, ap.CM_PROPS)
    ad = cm["animationData"] if isinstance(cm["animationData"], dict) else {}
    res.check(ap.same(ap.CM0_VALUES["skeletalMeshAsset"], cm["skeletalMeshAsset"]), "CharacterMesh0 mesh is SK_Warden", "got %s" % ap.short(cm["skeletalMeshAsset"]))
    res.check(cm["animationMode"] == "AnimationSingleNode", "CharacterMesh0 animation mode is single node", "got %s" % cm["animationMode"])
    res.check(ap.same(ap.CM0_VALUES["animationData"]["animToPlay"], ad.get("animToPlay")), "CharacterMesh0 clip is AN_Warden_Idle", "got %s" % ap.short(ad.get("animToPlay")))
    res.check(ad.get("bSavedLooping") is True, "CharacterMesh0 looping", "got %s" % ad.get("bSavedLooping"))
    res.check(ad.get("bSavedPlaying") is True, "CharacterMesh0 playing", "got %s" % ad.get("bSavedPlaying"))
    res.check(ap.vec_close(cm["relativeLocation"], {"x": 0, "y": 0, "z": -110}), "CharacterMesh0 location (0, 0, -110)", "got %s" % cm["relativeLocation"])
    res.check(ap.rot_close(cm["relativeRotation"], {"pitch": 0, "yaw": 0, "roll": 0}), "CharacterMesh0 yaw 0 (pitch 0, roll 0)", "got %s" % cm["relativeRotation"])
    bi = cm["bodyInstance"] if isinstance(cm["bodyInstance"], dict) else {}
    res.check(bi.get("collisionProfileName") == "NoCollision" and bi.get("collisionEnabled") == "NoCollision",
              "CharacterMesh0 collision NoCollision (profile and enabled)", "got %s" % bi)

    # --- placeholder parts
    for n in ap.PARTS:
        p = ap.read_props(ue, ap.tmpl_w(n), ap.PART_PROPS)
        b = p["bodyInstance"] if isinstance(p["bodyInstance"], dict) else {}
        res.check(p["staticMesh"] in (None, "None") and p["bVisible"] is False and p["bHiddenInGame"] is True
                  and b.get("collisionProfileName") == "NoCollision",
                  "%s: no mesh, hidden, NoCollision" % n, "mesh %s visible %s hiddenInGame %s profile %s" % (
                      ap.short(p["staticMesh"]), p["bVisible"], p["bHiddenInGame"], b.get("collisionProfileName")))

    # --- P12 fix set 1: the appearances (F3) and the attack light + mask glow (F4)
    apf.check_apparition_bp(ue, res)
    if ap.level_ok(ue):
        apf.check_placed(ue, res)
    apf.check_warden_bp(ue, res, snap_path)
    tl = ap.read_props(ue, ap.inst("BP_Warden_C_0", "TellLight"), ["intensity", "attenuationRadius", "relativeLocation"]) if ap.level_ok(ue) else None
    if tl:
        print("INFO  placed BP_Warden_C_0 TellLight in the open L_Monastery (in memory): intensity %s, radius %s, location %s "
              "(stale values here are expected in the session that edited the template; --disk reads the saved map)" % (
                  tl["intensity"], tl["attenuationRadius"], tl["relativeLocation"]))

    # --- capsule and tuning (read from BP_Warden and DA_WardenTuning)
    cap = ap.read_props(ue, ap.CAPSULE, ["capsuleRadius", "capsuleHalfHeight"])
    res.check(close(cap["capsuleRadius"], 42) and close(cap["capsuleHalfHeight"], 110), "BP_Warden capsule 42 / 110", "got %s" % cap)
    tun = ap.tuning_values(ue)
    res.check(tun == snap["tuning_asset"] and close(tun["capsuleRadius"], 42) and close(tun["capsuleHalfHeight"], 110),
              "DA_WardenTuning: all %d values equal the snapshot, capsule 42 / 110" % len(tun), "differs: %s" % [k for k in tun if tun[k] != snap["tuning_asset"].get(k)])

    # --- placed BP_Warden in the open level (in memory): INFO only (stale after a template write; --disk checks the saved map)
    if ap.level_ok(ue):
        bad = []
        for a in ap.WARDEN_INSTANCES:
            c = ap.read_props(ue, ap.inst(a, "CharacterMesh0"), ap.CM_PROPS)
            ci = c["bodyInstance"] if isinstance(c["bodyInstance"], dict) else {}
            if not (ap.same(ap.CM0_VALUES["skeletalMeshAsset"], c["skeletalMeshAsset"]) and c["animationMode"] == "AnimationSingleNode"
                    and ap.same(ap.CM0_VALUES["animationData"]["animToPlay"], (c["animationData"] or {}).get("animToPlay"))
                    and ap.rot_close(c["relativeRotation"], {"pitch": 0, "yaw": 0, "roll": 0})
                    and ap.vec_close(c["relativeLocation"], {"x": 0, "y": 0, "z": -110}) and ci.get("collisionProfileName") == "NoCollision"):
                bad.append(a + ".CharacterMesh0")
            for n in ap.PARTS:
                p = ap.read_props(ue, ap.inst(a, n), ["staticMesh", "bVisible", "bHiddenInGame"])
                if not (p["staticMesh"] in (None, "None") and p["bVisible"] is False and p["bHiddenInGame"] is True):
                    bad.append("%s.%s" % (a, n))
        print("INFO  placed BP_Warden_C_0 in the open L_Monastery (in memory): %s" % (
            "matches the templates" if not bad else "STALE in memory (parts / clip differ from the templates): %s" % bad))

    # --- nothing that must stay clean is dirty
    for pkg in ("/Game/LastBell/Materials/Master/M_LB_Surface", ap.TUNING_PKG, ap.SIL_MI.split(".")[0], ap.ANIM_PKG):
        res.check(ap.is_dirty(ue, pkg) is False, "%s is not dirty" % pkg.rsplit("/", 1)[1])
    print("INFO  SM_LB_Warden_Silhouette dirty: %s (known: it reads as dirty since F2; never saved; deleted after a restart)" % ap.is_dirty(ue, ap.SIL_MESH_PKG))


MIRROR = r"C:\lbb\TheLastBell.uproject"          # the mirror project (Content is a junction to the real Content)
UE_CMD = r"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
DISK_LOG_DIR = os.path.join(ROOT, "Saved", "Logs")
GETALL = ["StaticMeshComponent StaticMesh", "StaticMeshComponent bVisible", "StaticMeshComponent bHiddenInGame",
          "StaticMeshComponent RelativeLocation", "StaticMeshComponent RelativeRotation", "StaticMeshComponent RelativeScale3D",
          "SkeletalMeshComponent SkeletalMeshAsset", "SkeletalMeshComponent AnimationMode", "SkeletalMeshComponent AnimationData",
          "SkeletalMeshComponent RelativeLocation", "SkeletalMeshComponent RelativeRotation", "SkeletalMeshComponent BodyInstance",
          "PointLightComponent bVisible", "PointLightComponent Intensity", "PointLightComponent AttenuationRadius",
          "PointLightComponent RelativeLocation",
          "LBWardenApparition TriggerTag", "LBWardenApparition ArmDelaySeconds", "LBWardenApparition GlowSizeCm",
          "LBWardenApparition Stations"]


def read_map_from_disk(map_name, timeout_s=150):
    """Load a map from disk in a separate headless editor process (the mirror project) and read the placed Warden and silhouette
    components with the `getall` console command. Returns {(object path after PersistentLevel., property): raw value text}.
    The process is started and stopped by this function (it does not exit on its own after `Quit` in this mode); the real editor
    is not touched. This is how the saved state is checked, because the open editor's placed instances can be stale."""
    import re
    import subprocess
    import time
    log = os.path.join(DISK_LOG_DIR, "check_warden_disk_%s.log" % map_name)
    if os.path.exists(log):
        os.remove(log)
    cmds = ",".join(["getall " + g for g in GETALL] + ["Quit"])
    cmdline = '"%s" "%s" /Game/LastBell/Maps/%s -ExecCmds="%s" -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=%s' % (
        UE_CMD, MIRROR, map_name, cmds, log)
    p = subprocess.Popen(cmdline)
    t0 = time.time()
    try:
        while time.time() - t0 < timeout_s:
            time.sleep(3)
            if p.poll() is not None:
                break
            if os.path.exists(log):
                with open(log, "r", encoding="utf-8", errors="replace") as f:
                    if "Cmd: Quit" in f.read():
                        time.sleep(3)
                        break
    finally:
        if p.poll() is None:
            p.kill()
    out = {}
    pat = re.compile(r"\]\d+\) \w+ \S+?PersistentLevel\.(\S+)\.(\w+) =[ ]?(.*)$")
    pat_bp = re.compile(r"\]\d+\) \w+ \S+?(BP_Warden|BP_WardenSilhouette)_C:(\w+)_GEN_VARIABLE\.(\w+) = (.*)$")
    pat_item = re.compile(r"\]\s*\d+: (.*)$")   # array elements follow an empty "Prop =" line as "<tab>0: (...)"
    last = None
    with open(log, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            mi = pat_item.search(line)
            if mi and last is not None:
                out[last] = (out[last] + chr(10) + mi.group(1).strip()).strip()
                continue
            last = None
            m = pat.search(line)
            if m and ("BP_Warden" in m.group(1)):
                out[(m.group(1), m.group(2))] = m.group(3).strip()
                if not m.group(3).strip():
                    last = (m.group(1), m.group(2))
            m = pat_bp.search(line)
            if m:
                out[("template:%s.%s" % (m.group(1), m.group(2)), m.group(3))] = m.group(4).strip()
    return out


def _vec(s):
    import re
    return [float(x) for x in re.findall(r"=(-?[\d.]+)", s)]


def _nums(s):
    import re
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?(?:e[-+]?\d+)?", s or "")]


# the text export leaves out a struct member that equals its default, so parse by name over these defaults
STATION_DEFAULTS = {"LookConeDegrees": 30.0, "MinPlayerDistance": 0.0, "FadeInSeconds": 1.0, "HoldSeconds": 3.0, "FadeOutSeconds": 1.5, "GapAfterSeconds": 0.0,
                    "X": 0.0, "Y": 0.0, "Z": 0.0}


def _stations_match(text, want):
    import re
    lines = [l for l in (text or "").splitlines() if l.strip()]
    if len(lines) != len(want):
        return False
    for line, w in zip(lines, want):
        d = dict(STATION_DEFAULTS)
        d.update({k: float(v) for k, v in re.findall(r"(\w+)=(-?\d+(?:\.\d+)?)", line)})
        exp = {"X": w["location"]["x"], "Y": w["location"]["y"], "Z": w["location"]["z"], "LookConeDegrees": w["lookConeDegrees"],
               "MinPlayerDistance": w["minPlayerDistance"], "FadeInSeconds": w["fadeInSeconds"], "HoldSeconds": w["holdSeconds"],
               "FadeOutSeconds": w["fadeOutSeconds"], "GapAfterSeconds": w["gapAfterSeconds"]}
        if any(abs(d[k] - v) > 1e-3 for k, v in exp.items()):
            return False
    return True


def check_disk(ue, res, rep, snap_path=None):
    """--disk: the SAVED assets, read by a fresh process. Placed BP_Warden_C_0 (L_Monastery, L_Test_Warden): mesh, clip, looping/playing,
    location, yaw, collision, hidden parts, and (fix set 1) TellLight 5000 / radius 700 / (110, 0, 235), off. L_Monastery: both
    BP_WardenApparition instances with every section 3 value, and no BP_WardenSilhouette."""
    sys.path.insert(0, HERE)
    import apply_p12f_blueprints as apf  # noqa: E402
    for map_name in ("L_Monastery", "L_Test_Warden"):
        v = read_map_from_disk(map_name)
        k = lambda comp, prop, a="BP_Warden_C_0": v.get(("%s.%s" % (a, comp), prop))  # noqa: E731
        ad = k("CharacterMesh0", "AnimationData") or ""
        bi = k("CharacterMesh0", "BodyInstance") or ""
        res.check("SK_Warden" in (k("CharacterMesh0", "SkeletalMeshAsset") or "") and k("CharacterMesh0", "AnimationMode") == "AnimationSingleNode",
                  "%s from disk: BP_Warden_C_0 CharacterMesh0 mesh SK_Warden, single-node" % map_name,
                  "mesh %s mode %s" % (k("CharacterMesh0", "SkeletalMeshAsset"), k("CharacterMesh0", "AnimationMode")))
        res.check("AN_Warden_Idle" in ad and "bSavedLooping=True" in ad and "bSavedPlaying=True" in ad,
                  "%s from disk: clip AN_Warden_Idle, looping, playing" % map_name, ad)
        loc, rot = _vec(k("CharacterMesh0", "RelativeLocation") or ""), _vec(k("CharacterMesh0", "RelativeRotation") or "")
        res.check(loc == [0, 0, -110] and rot == [0, 0, 0], "%s from disk: CharacterMesh0 location (0,0,-110), yaw 0" % map_name, "loc %s rot %s" % (loc, rot))
        res.check("CollisionEnabled=NoCollision" in bi, "%s from disk: CharacterMesh0 collision NoCollision" % map_name, bi[:160])
        bad = [n for n in PARTS_ALL if not (k(n, "StaticMesh") == "None" and k(n, "bVisible") == "False" and k(n, "bHiddenInGame") == "True")]
        res.check(not bad, "%s from disk: the 8 placeholder parts have no mesh and are hidden" % map_name, "differ: %s" % bad)
        tl_loc = _vec(k("TellLight", "RelativeLocation") or "")
        res.check(k("TellLight", "bVisible") == "False" and (k("TellLight", "Intensity") or "").startswith("5000")
                  and (k("TellLight", "AttenuationRadius") or "").startswith("700") and tl_loc == [110, 0, 235],
                  "%s from disk: placed TellLight off, intensity 5000, radius 700, location (110, 0, 235) (the template values reached the saved instance)" % map_name,
                  "visible %s intensity %s radius %s location %s" % (k("TellLight", "bVisible"), k("TellLight", "Intensity"),
                                                                   k("TellLight", "AttenuationRadius"), k("TellLight", "RelativeLocation")))
        if map_name != "L_Monastery":
            continue
        for label, spec in apf.INSTANCES.items():
            a = {"Apparition_Courtyard": "BP_WardenApparition_C_0", "Apparition_Chapel": "BP_WardenApparition_C_1"}[label]
            actor = lambda prop, a=a: v.get((a, prop))  # noqa: E731
            st_ok = _stations_match(actor("Stations"), spec["stations"])
            body, glow = (lambda p, a=a: v.get(("%s.Body" % a, p))), (lambda p, a=a: v.get(("%s.Glow" % a, p)))  # noqa: E731
            ok = (spec["tag"] in (actor("TriggerTag") or "") and abs((_nums(actor("ArmDelaySeconds")) or [-1])[0] - spec["arm"]) < 1e-3
                  and abs((_nums(actor("GlowSizeCm")) or [-1])[0] - spec["glow"]) < 1e-3 and st_ok
                  and "SM_LB_Warden_Apparition" in (body("StaticMesh") or "") and "Plane" in (glow("StaticMesh") or "")
                  and _vec(glow("RelativeLocation") or "") == [-150, 0, 150])
            res.check(ok, "%s from disk: %s tag %s, arm %s s, glow %g, stations %s, Body SM_LB_Warden_Apparition, Glow Plane at (-150, 0, 150)" % (
                map_name, label, spec["tag"], spec["arm"], spec["glow"], [(s["location"]["x"], s["location"]["y"], s["location"]["z"]) for s in spec["stations"]]),
                "tag %s arm %s glow %s stations %s body %s glow mesh %s glow loc %s" % (
                    actor("TriggerTag"), actor("ArmDelaySeconds"), actor("GlowSizeCm"), actor("Stations"), body("StaticMesh"), glow("StaticMesh"), glow("RelativeLocation")))
        left = sorted({key[0] for key in v if "BP_WardenSilhouette" in key[0] and not key[0].startswith("template:")})
        res.check(not left, "%s from disk: no BP_WardenSilhouette is placed" % map_name, "found %s" % left)


PARTS_ALL = ["Robe", "Shoulders", "Neck", "Head", "ArmLeft", "ArmRight", "Mask", "MaskCrack"]

# (name, function).  `--bp` runs only ("blueprint", check_bp); `--disk` only ("disk", check_disk); the other groups are the default run.
CHECK_GROUPS = [("mesh", check_mesh), ("textures", check_textures), ("clips", check_clips),
                ("wool", check_wool), ("skin", check_skin), ("place", check_place)]
BP_GROUPS = [("blueprint", check_bp)]


def close(a, b, tol=1e-3):
    return abs(float(a) - float(b)) <= tol


def main():
    path = DEFAULT_VALIDATION
    if "--validation" in sys.argv:
        path = sys.argv[sys.argv.index("--validation") + 1]
    groups = CHECK_GROUPS
    if "--bp" in sys.argv:
        groups = BP_GROUPS      # BP_Warden / BP_WardenSilhouette only; the Blueprint checks need no validation report
    if "--disk" in sys.argv:
        groups = [("disk", check_disk)]   # the saved assets, read by a fresh headless process (about 1 minute per map)
    with open(path, "r", encoding="utf-8") as f:
        rep = json.load(f)
    ue = UE()
    res = Result()
    for name, fn in groups:
        guard(res, name, lambda fn=fn: fn(ue, res, rep))
    print("%d/%d" % (res.passed, res.total))
    return 0 if res.passed == res.total else 1


if __name__ == "__main__":
    sys.exit(main())
