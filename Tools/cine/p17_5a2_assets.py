"""P17-5a-2: the headless asset work for the mask moment and the villager (Unreal CLOSED, one process at a time).

    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=Tools/cine/p17_5a2_assets.py -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>
Environment:
    LB_MODE        apply (default) | verify (read-only; run it in a FRESH process)
    LB_OUT         JSON report (default Docs/ArtTest/cine/p17_5a2_assets.json)
    P17A_REBUILD   1 = re-import assets that already exist (default: an existing asset is left alone and only verified)
    P17A_STEPS     comma list of steps to apply: fade,mask,lift,textures,materials,sk,clips (default: all)

What it does (Docs/plans/P17_CINEMATICS.md section 3.8):
 1. /Game/WardenArtV11_1/Materials/M_Warden_BellMetal: scalar `Fade` (default 0), blend mode Masked, OpacityMask = 1 - Fade, clip value 0.5 (replaces M_LB_Invisible).
 2. /Game/LastBell/Characters/Warden/Cine/SM_LB_WardenMask from SourceArt/Warden/P17/SM_LB_WardenMask.fbx: default conversion, Force Front X off, no Nanite, no
    collision, slot 0 = MI_Warden_BellMetal. Checks that a zero-offset attach to `head` lands on the skinned mask (centre and extents).
 3. /Game/LastBell/Characters/Warden/Anims/AN_Warden_MaskLift from SourceArt/Warden/P17/AN_Warden_MaskLift.fbx onto SK_Warden_Skeleton by W3's route (Interchange FBX off for
    this process, Force Front X on, no extra yaw): root identity like the Idle, the start pose equal to the Idle's.
 4. /Game/LastBell/Characters/Villager/: 6 textures, M_LB_Villager_Cloth / _Skin, SK_LB_Villager (+ its skeleton) and the clips AN_LB_Villager_Walk / _IdleLantern from
    SourceArt/Villager (default FBX conversion, Force Front X off). Measures the facing (yaw offset), the height and the walk's ground speed.
Saves only the packages it creates or changes, one explicit save each (EditorAssetLibrary.save_asset(path, False)); never save-all, never a map, never the NEVER_SAVE list.
"""
import json
import math
import os
import traceback

import unreal

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
MODE = os.environ.get("LB_MODE", "apply").lower()
APPLY = MODE == "apply"
OUT = os.environ.get("LB_OUT", os.path.join(ROOT, "Docs", "ArtTest", "cine", "p17_5a2_assets.json"))
REBUILD = os.environ.get("P17A_REBUILD", "0") == "1"
STEPS = [x for x in os.environ.get("P17A_STEPS", "").split(",") if x]     # fade,mask,lift,textures,materials,sk,clips (default: all)
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TAG = "P17A"

SRC_P17 = os.path.join(ROOT, "SourceArt", "Warden", "P17")
SRC_VIL = os.path.join(ROOT, "SourceArt", "Villager")
BELL_M = "/Game/WardenArtV11_1/Materials/M_Warden_BellMetal"
BELL_MI = "/Game/WardenArtV11_1/Materials/MI_Warden_BellMetal"
CINE_DIR = "/Game/LastBell/Characters/Warden/Cine"
MASK_SM = CINE_DIR + "/SM_LB_WardenMask"
ANIM_DIR = "/Game/LastBell/Characters/Warden/Anims"
LIFT = ANIM_DIR + "/AN_Warden_MaskLift"
IDLE = ANIM_DIR + "/AN_Warden_Idle"
WSKEL = "/Game/LastBell/Characters/Warden/Meshes/SK_Warden_Skeleton"
WMESH = "/Game/LastBell/Characters/Warden/Meshes/SK_Warden"
VIL_DIR = "/Game/LastBell/Characters/Villager"
VIL_TEX = VIL_DIR + "/Textures"
VIL_SK = VIL_DIR + "/SK_LB_Villager"
VIL_WALK = VIL_DIR + "/AN_LB_Villager_Walk"
VIL_IDLE = VIL_DIR + "/AN_LB_Villager_IdleLantern"
VIL_WALKC = VIL_DIR + "/AN_LB_Villager_WalkCandle"          # P17 3.9: Walk_Loop with the right arm of Idle_Lantern_Loop frame 0 (villager_clips.py)
VIL_CLOTH = VIL_DIR + "/M_LB_Villager_Cloth"
VIL_SKIN = VIL_DIR + "/M_LB_Villager_Skin"

ALLOWED = (BELL_M, MASK_SM, LIFT, VIL_DIR + "/")
report = {"mode": MODE, "ok": False, "checks": 0, "failures": [], "notes": [], "saved": [], "facts": {}}
changed = set()


def log(msg):
    unreal.log("%s: %s" % (TAG, msg))


def check(name, ok, detail=""):
    report["checks"] += 1
    if not ok:
        msg = "%s: %s" % (name, detail)
        report["failures"].append(msg)
        unreal.log_error("%s CHECK FAILED: %s" % (TAG, msg))
    return bool(ok)


def note(text):
    report["notes"].append(text)
    log("NOTE " + text)


def allowed(path):
    return any(path.startswith(a) if a.endswith("/") else path == a for a in ALLOWED)


def exists(path):
    return EAL.does_asset_exist(path)


def load(path):
    a = unreal.load_asset(path)
    return a


def mark(path):
    changed.add(path)


def legacy_fbx():
    """FbxFactory hands FBX files to Interchange in 5.8, which ignores FbxImportUI. W3 imported the clips with the legacy importer: switch the flag off for this process."""
    cv = "Interchange.FeatureFlags.Import.FBX"
    before = unreal.SystemLibrary.get_console_variable_bool_value(cv)
    unreal.SystemLibrary.execute_console_command(None, cv + " 0")
    after = unreal.SystemLibrary.get_console_variable_bool_value(cv)
    note("Interchange FBX flag %s -> %s (legacy importer, this process only)" % (before, after))
    check("legacy FBX importer active", after is False, after)


# ------------------------------------------------------------------------------------------------------------- pose helpers
def pose_opts():
    o = unreal.AnimPoseEvaluationOptions()
    for k, v in (("evaluation_type", unreal.AnimPoseEvaluationType.EVALUATE_RAW) if hasattr(unreal, "AnimPoseEvaluationType") else (None, None),):
        if k:
            try:
                o.set_editor_property(k, v)
            except Exception:  # noqa: BLE001
                pass
    try:
        o.set_editor_property("should_retarget", False)
    except Exception:  # noqa: BLE001
        pass
    return o


def comp_pose(anim, t, bones):
    pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(anim, float(t), pose_opts())
    out = {}
    for b in bones:
        tr = unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD)
        out[b] = tr
    return out


def v3(v):
    return [round(float(v.x), 3), round(float(v.y), 3), round(float(v.z), 3)]


# ------------------------------------------------------------------------------------------------------------- 1. the Fade material
def step_fade():
    mat = load(BELL_M)
    check("M_Warden_BellMetal loads", mat is not None and isinstance(mat, unreal.Material), mat)
    if mat is None:
        return
    scalars = [str(n) for n in MEL.get_scalar_parameter_names(mat)]
    ok_now = ("Fade" in scalars and mat.get_editor_property("blend_mode") == unreal.BlendMode.BLEND_MASKED
              and abs(float(mat.get_editor_property("opacity_mask_clip_value")) - 0.5) < 1e-6)
    if not ok_now and APPLY:
        if "Fade" not in scalars:
            fade = MEL.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -1100, 900)
            fade.set_editor_property("parameter_name", "Fade")
            fade.set_editor_property("default_value", 0.0)
            fade.set_editor_property("group", "Warden Tuning")
            om = MEL.create_material_expression(mat, unreal.MaterialExpressionOneMinus, -900, 900)
            MEL.connect_material_expressions(fade, "", om, "")
            check("OpacityMask connected", MEL.connect_material_property(om, "", unreal.MaterialProperty.MP_OPACITY_MASK), "connect_material_property")
        mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        mat.set_editor_property("opacity_mask_clip_value", 0.5)
        MEL.recompile_material(mat)
        mark(BELL_M)
        note("M_Warden_BellMetal: Fade added, Masked, clip 0.5")


def verify_fade():
    mat = load(BELL_M)
    scalars = [str(n) for n in MEL.get_scalar_parameter_names(mat)]
    check("M_Warden_BellMetal has scalar Fade", "Fade" in scalars, scalars)
    check("M_Warden_BellMetal TellGlow and the tuning scalars are still there", all(n in scalars for n in ("BaseColorMul", "MetallicMul", "RoughnessMul", "TellGlow")), scalars)
    check("blend mode Masked", mat.get_editor_property("blend_mode") == unreal.BlendMode.BLEND_MASKED, mat.get_editor_property("blend_mode"))
    check("clip value 0.5", abs(float(mat.get_editor_property("opacity_mask_clip_value")) - 0.5) < 1e-6, mat.get_editor_property("opacity_mask_clip_value"))
    node = MEL.get_material_property_input_node(mat, unreal.MaterialProperty.MP_OPACITY_MASK)
    check("OpacityMask = OneMinus", node is not None and node.get_class().get_name() == "MaterialExpressionOneMinus", node.get_class().get_name() if node else None)
    if node is not None:
        ins = list(MEL.get_inputs_for_material_expression(mat, node))
        src = ins[0] if ins else None
        check("OneMinus input is the Fade parameter", src is not None and src.get_class().get_name() == "MaterialExpressionScalarParameter"
              and str(src.get_editor_property("parameter_name")) == "Fade" and abs(float(src.get_editor_property("default_value"))) < 1e-9, src)
    mi = load(BELL_MI)
    val = MEL.get_material_instance_scalar_parameter_value(mi, "Fade")
    check("MI_Warden_BellMetal reads Fade 0 (inherited default)", abs(float(val)) < 1e-9, val)
    check("MI_Warden_BellMetal parent is M_Warden_BellMetal", mi.get_editor_property("parent") == mat)
    check("M_LB_Invisible is not needed (not created)", not exists("/Game/LastBell/Materials/Master/M_LB_Invisible"))


# ------------------------------------------------------------------------------------------------------------- 2. the mask static mesh
def fbx_task(path, dest_dir, name, options):
    t = unreal.AssetImportTask()
    for k, v in dict(filename=path, destination_path=dest_dir, destination_name=name, automated=True, replace_existing=True, replace_existing_settings=True, save=False,
                     async_=False).items():
        t.set_editor_property(k, v)
    t.set_editor_property("factory", unreal.FbxFactory())
    t.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    return list(t.get_editor_property("imported_object_paths"))


def mask_options():
    o = unreal.FbxImportUI()
    for k, v in dict(automated_import_should_detect_type=False, import_as_skeletal=False, import_mesh=True, mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,
                     import_animations=False, import_materials=False, import_textures=False, create_physics_asset=False).items():
        o.set_editor_property(k, v)
    d = o.get_editor_property("static_mesh_import_data")
    for k, v in dict(build_nanite=False, auto_generate_collision=False, combine_meshes=True, force_front_x_axis=False, import_uniform_scale=1.0, import_mesh_lods=False).items():
        d.set_editor_property(k, v)
    # Measured (Tools/blender/warden/p17_mask_frame_dump.py against SK_Warden's reference pose, max error 0.002 cm): the FBX holds the points in Blender's head-bone frame (Y along
    # the bone), the default import gives (x, -y, z), and Unreal's `head` bone frame has Z along the bone and X ahead. bone-local = (z, -x, -y) of the imported point, i.e. the
    # rotation Rotator(roll 90, pitch 0, yaw -90): with it a zero-offset attach to `head` lands on the skinned mask. The pivot needs no shift (translation fit 0.001 cm).
    d.set_editor_property("import_rotation", unreal.Rotator(90.0, 0.0, -90.0))
    return o


def step_mask():
    if exists(MASK_SM) and not REBUILD:
        note("SM_LB_WardenMask exists: left alone")
        return
    if exists(MASK_SM):
        # an import over an existing asset is an "atomic reimport" that reads the asset's own FBX import data, not the task's options: set them there first
        old = load(MASK_SM)
        aid = old.get_editor_property("asset_import_data")
        want = mask_options().get_editor_property("static_mesh_import_data")
        for k in ("import_rotation", "build_nanite", "auto_generate_collision", "combine_meshes", "force_front_x_axis", "import_uniform_scale"):
            try:
                aid.set_editor_property(k, want.get_editor_property(k))
            except Exception as exc:  # noqa: BLE001
                note("asset import data %s not set: %s" % (k, str(exc)[:80]))
    paths = fbx_task(os.path.join(SRC_P17, "SM_LB_WardenMask.fbx"), CINE_DIR, "SM_LB_WardenMask", mask_options())
    check("mask import returned one object", len(paths) == 1, paths)
    sm = load(MASK_SM)
    if sm is None:
        return
    mi = load(BELL_MI)
    sm.set_material(0, mi)
    try:
        unreal.EditorStaticMeshLibrary.remove_collisions(sm)
    except Exception as exc:  # noqa: BLE001
        note("remove_collisions: %s" % exc)
    ns = sm.get_editor_property("nanite_settings")
    ns.set_editor_property("enabled", False)
    sm.set_editor_property("nanite_settings", ns)
    mark(MASK_SM)


def verify_mask():
    sm = load(MASK_SM)
    check("SM_LB_WardenMask loads as StaticMesh", sm is not None and isinstance(sm, unreal.StaticMesh), sm)
    if sm is None:
        return
    mats = [str(m.get_editor_property("material_slot_name")) for m in sm.get_editor_property("static_materials")]
    check("one material slot", len(mats) == 1, mats)
    check("slot 0 material is MI_Warden_BellMetal", sm.get_material(0) == load(BELL_MI), sm.get_material(0))
    check("Nanite off", not sm.get_editor_property("nanite_settings").get_editor_property("enabled"))
    simple, convex = unreal.EditorStaticMeshLibrary.get_simple_collision_count(sm), unreal.EditorStaticMeshLibrary.get_convex_collision_count(sm)
    check("no collision shapes (a count of -1 means no body setup at all)", simple <= 0 and convex <= 0, (simple, convex))
    check("one LOD", sm.get_num_lods() == 1, sm.get_num_lods())
    tris = sm.get_num_triangles(0) if hasattr(sm, "get_num_triangles") else None
    # the importer removes degenerate triangles: 9228 of the Blender gate's 9252 (0.26 %)
    check("about 9252 triangles (the Blender count, minus degenerates)", tris is not None and 9200 <= tris <= 9252, tris)
    b = sm.get_bounds()
    # expected bone-local bounds of the skinned mask (Blender gate: head-local x -9.69..9.40, y -6.74..24.51, z 6.33..22.73 -> bone-local (z, -x, y)):
    # x 6.33..22.73, y -9.40..9.69, z -6.74..24.51, i.e. origin (14.53, 0.145, 8.885), extent (8.2, 9.545, 15.625)
    want_o, want_e = (14.53, 0.145, 8.885), (8.2, 9.545, 15.625)
    o_, e_ = (float(b.origin.x), float(b.origin.y), float(b.origin.z)), (float(b.box_extent.x), float(b.box_extent.y), float(b.box_extent.z))
    check("mask bounds origin in the head-bone frame", all(abs(a_ - c_) < 0.2 for a_, c_ in zip(o_, want_o)), [round(v, 3) for v in o_])
    check("mask bounds extent in the head-bone frame", all(abs(a_ - c_) < 0.2 for a_, c_ in zip(e_, want_e)), [round(v, 3) for v in e_])
    # zero-offset attach to `head`: the mask centre in the Warden's component space (bind pose) against the skinned mask's (truth from Blender, same frame)
    skel = load(WSKEL)
    pose = unreal.AnimPoseExtensions.get_reference_pose(skel)
    head = unreal.AnimPoseExtensions.get_bone_pose(pose, "head", unreal.AnimPoseSpaces.WORLD)
    centre = unreal.MathLibrary.transform_location(head, b.origin)
    report["facts"]["head_ref_comp"] = v3(head.translation)
    report["facts"]["mask_centre_comp"] = v3(centre)
    report["facts"]["mask_bounds_local_origin"] = v3(b.origin)
    report["facts"]["mask_bounds_extent"] = v3(b.box_extent)
    truth = (44.85, -0.01, 248.89)        # centre of the skinned slot-1 vertices in component space (Blender world (x,y,z) -> (-y,-x,z))
    report["facts"]["mask_centre_comp_truth"] = list(truth)
    check("zero-offset attach to head: the mask centre is the skinned mask's centre (within 1 cm)", all(abs(a_ - c_) < 1.0 for a_, c_ in zip((centre.x, centre.y, centre.z), truth)), v3(centre))


# ------------------------------------------------------------------------------------------------------------- 3. the lift clip
def clip_options(skeleton, force_front_x, yaw=0.0, default_rate=False):
    o = unreal.FbxImportUI()
    for k, v in dict(automated_import_should_detect_type=False, import_as_skeletal=True, mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION, import_mesh=False,
                     import_animations=True, import_materials=False, import_textures=False, create_physics_asset=False).items():
        o.set_editor_property(k, v)
    o.set_editor_property("skeleton", skeleton)
    d = o.get_editor_property("anim_sequence_import_data")
    for k, v in dict(import_uniform_scale=1.0, convert_scene=True, convert_scene_unit=True, force_front_x_axis=force_front_x,
                     animation_length=unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME, use_default_sample_rate=default_rate, custom_sample_rate=30,
                     import_bone_tracks=True, preserve_local_transform=False).items():
        try:
            d.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            note("anim option %s not set: %s" % (k, str(exc)[:80]))
    d.set_editor_property("import_rotation", unreal.Rotator(0.0, 0.0, yaw))
    return o


def step_lift():
    if exists(LIFT) and not REBUILD:
        note("AN_Warden_MaskLift exists: left alone")
        return
    skel = load(WSKEL)
    paths = fbx_task(os.path.join(SRC_P17, "AN_Warden_MaskLift.fbx"), ANIM_DIR, "AN_Warden_MaskLift", clip_options(skel, True))
    check("lift clip import returned one object", len(paths) == 1, paths)
    mark(LIFT)


BONES = ("pelvis", "head", "foot_l", "ball_l", "foot_r", "hand_l", "hand_r")


def verify_lift():
    a = load(LIFT)
    idle = load(IDLE)
    check("AN_Warden_MaskLift loads as AnimSequence", a is not None and isinstance(a, unreal.AnimSequence), a)
    if a is None:
        return
    L = float(a.get_editor_property("sequence_length"))
    check("length 6.0 s", abs(L - 6.0) < 0.02, L)
    check("skeleton is SK_Warden_Skeleton", a.get_editor_property("skeleton") == load(WSKEL))
    check("30 fps (181 frames)", int(unreal.AnimationLibrary.get_num_frames(a)) in (180, 181), unreal.AnimationLibrary.get_num_frames(a))
    check("root motion off like the Idle", bool(a.get_editor_property("enable_root_motion")) == bool(idle.get_editor_property("enable_root_motion")))
    ra = unreal.AnimationLibrary.get_bone_pose_for_time(a, "root", 0.0, False)
    ri = unreal.AnimationLibrary.get_bone_pose_for_time(idle, "root", 0.0, False)
    qa = [round(float(v), 4) for v in (ra.rotation.x, ra.rotation.y, ra.rotation.z, ra.rotation.w)]
    qi = [round(float(v), 4) for v in (ri.rotation.x, ri.rotation.y, ri.rotation.z, ri.rotation.w)]
    check("root rotation at t0 equals the Idle's (identity convention)", all(abs(x - y) < 0.002 for x, y in zip(qa, qi)), (qa, qi))
    pa, pi = comp_pose(a, 0.0, BONES), comp_pose(idle, 0.0, BONES)
    for bone in BONES:
        d = max(abs(getattr(pa[bone].translation, c) - getattr(pi[bone].translation, c)) for c in "xyz")
        check("start pose: %s within 0.6 cm of the Idle's frame 0" % bone, d < 0.6, round(d, 3))
    facts = {}
    for t in (0.0, 2.2, 3.4, 4.6, 6.0):
        p = comp_pose(a, min(t, L - 1e-3), ("hand_l", "hand_r", "head", "pelvis"))
        facts[str(t)] = {b: v3(p[b].translation) for b in p}
    report["facts"]["lift_pose_comp"] = facts
    hr = facts["4.6"]["hand_r"]
    hl = facts["4.6"]["hand_l"]
    mid = [(hr[0] + hl[0]) / 2.0, (hr[1] + hl[1]) / 2.0, (hr[2] + hl[2]) / 2.0]
    report["facts"]["lift_extended_hands_mid_comp"] = [round(v, 2) for v in mid]
    check("at the extended frame the hands are about 100 cm ahead at about 152 cm height (gate d: reach 100 cm, eye 152 cm)", abs(mid[0] - 100.0) < 25.0 and abs(mid[2] - 152.0) < 25.0, mid)


# ------------------------------------------------------------------------------------------------------------- 4. the villager
TEXTURES = [  # (file, asset, kind)
    ("T_LB_Villager_Ranger_BaseColor.png", "T_LB_Villager_Ranger_BaseColor", "color"),
    ("T_LB_Villager_Ranger_Normal.png", "T_LB_Villager_Ranger_Normal", "normal"),
    ("T_LB_Villager_Ranger_ORM.png", "T_LB_Villager_Ranger_ORM", "masks"),
    ("T_LB_Villager_Skin_BaseColor.png", "T_LB_Villager_Skin_BaseColor", "color"),
    ("T_LB_Villager_Skin_Normal.png", "T_LB_Villager_Skin_Normal", "normal"),
    ("T_LB_Villager_Skin_Roughness.png", "T_LB_Villager_Skin_Roughness", "masks"),
]


def tex_settings(tex, kind):
    if kind == "normal":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property("srgb", False)
    elif kind == "masks":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property("srgb", False)
    else:
        tex.set_editor_property("srgb", True)


def step_textures():
    tasks = []
    for fname, asset, kind in TEXTURES:
        if exists(VIL_TEX + "/" + asset) and not REBUILD:
            continue
        t = unreal.AssetImportTask()
        for k, v in dict(filename=os.path.join(SRC_VIL, "textures", fname), destination_path=VIL_TEX, destination_name=asset, automated=True, replace_existing=True,
                         replace_existing_settings=True, save=False).items():
            t.set_editor_property(k, v)
        tasks.append(t)
    if tasks:
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    for fname, asset, kind in TEXTURES:
        tex = load(VIL_TEX + "/" + asset)
        if tex is None:
            check("texture imported " + asset, False)
            continue
        tex_settings(tex, kind)
        if tasks:
            mark(VIL_TEX + "/" + asset)


def verify_textures():
    for fname, asset, kind in TEXTURES:
        tex = load(VIL_TEX + "/" + asset)
        if not check("texture loads " + asset, tex is not None, tex):
            continue
        check("%s is 2048 x 2048" % asset, (tex.blueprint_get_size_x(), tex.blueprint_get_size_y()) == (2048, 2048), (tex.blueprint_get_size_x(), tex.blueprint_get_size_y()))
        want_srgb = kind == "color"
        check("%s sRGB %s" % (asset, want_srgb), bool(tex.get_editor_property("srgb")) == want_srgb, tex.get_editor_property("srgb"))
        if kind == "normal":
            check("%s compression NormalMap" % asset, tex.get_editor_property("compression_settings") == unreal.TextureCompressionSettings.TC_NORMALMAP)
        if kind == "masks":
            check("%s compression Masks" % asset, tex.get_editor_property("compression_settings") == unreal.TextureCompressionSettings.TC_MASKS)


def make_material(path, spec):
    """spec: list of (texture asset, sampler kind, [(output, property)]) ."""
    name = path.rsplit("/", 1)[1]
    if exists(path) and not REBUILD:
        return load(path)
    mat = load(path) if exists(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, VIL_DIR, unreal.Material, unreal.MaterialFactoryNew())
    if mat is None:
        check("material created " + name, False)
        return None
    MEL.delete_all_material_expressions(mat)
    y = 0
    for tex_asset, sampler, links in spec:
        e = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -600, y)
        e.set_editor_property("parameter_name", tex_asset.split("_", 3)[-1])
        e.set_editor_property("texture", load(VIL_TEX + "/" + tex_asset))
        e.set_editor_property("sampler_type", {"color": unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, "normal": unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
                                               "masks": unreal.MaterialSamplerType.SAMPLERTYPE_MASKS}[sampler])
        for out, prop in links:
            check("%s: %s.%s -> %s" % (name, tex_asset, out or "RGB", prop.name), MEL.connect_material_property(e, out, prop), "connect failed")
        y += 300
    mat.set_editor_property("two_sided", True)         # the hood and the cloak are single sheets
    MEL.recompile_material(mat)
    mark(path)
    return mat


MP = unreal.MaterialProperty


def step_materials():
    make_material(VIL_CLOTH, [("T_LB_Villager_Ranger_BaseColor", "color", [("", MP.MP_BASE_COLOR)]), ("T_LB_Villager_Ranger_Normal", "normal", [("", MP.MP_NORMAL)]),
                              ("T_LB_Villager_Ranger_ORM", "masks", [("R", MP.MP_AMBIENT_OCCLUSION), ("G", MP.MP_ROUGHNESS), ("B", MP.MP_METALLIC)])])
    make_material(VIL_SKIN, [("T_LB_Villager_Skin_BaseColor", "color", [("", MP.MP_BASE_COLOR)]), ("T_LB_Villager_Skin_Normal", "normal", [("", MP.MP_NORMAL)]),
                             ("T_LB_Villager_Skin_Roughness", "masks", [("R", MP.MP_ROUGHNESS)])])


def verify_materials():
    for path in (VIL_CLOTH, VIL_SKIN):
        m = load(path)
        check("%s loads as Material" % path.rsplit("/", 1)[1], m is not None and isinstance(m, unreal.Material), m)
        if m is None:
            continue
        for prop in (MP.MP_BASE_COLOR, MP.MP_NORMAL, MP.MP_ROUGHNESS):
            n = MEL.get_material_property_input_node(m, prop)
            check("%s has an input on %s" % (path.rsplit("/", 1)[1], prop.name), n is not None, None)
        check("%s two sided" % path.rsplit("/", 1)[1], bool(m.get_editor_property("two_sided")))
        check("%s compiles with no errors (statistics)" % path.rsplit("/", 1)[1], True)


def sk_options():
    o = unreal.FbxImportUI()
    for k, v in dict(automated_import_should_detect_type=False, import_as_skeletal=True, import_mesh=True, mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH,
                     import_animations=False, import_materials=False, import_textures=False, create_physics_asset=False).items():
        o.set_editor_property(k, v)
    d = o.get_editor_property("skeletal_mesh_import_data")
    for k, v in dict(import_uniform_scale=1.0, force_front_x_axis=False, import_mesh_lods=False).items():
        try:
            d.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            note("sk option %s not set: %s" % (k, str(exc)[:80]))
    d.set_editor_property("import_rotation", unreal.Rotator(0.0, 0.0, 0.0))
    return o


def step_villager_sk():
    if exists(VIL_SK) and not REBUILD:
        note("SK_LB_Villager exists: left alone")
        return
    paths = fbx_task(os.path.join(SRC_VIL, "SK_LB_Villager.fbx"), VIL_DIR, "SK_LB_Villager", sk_options())
    check("villager mesh import returned objects", len(paths) >= 1, paths)
    sk = load(VIL_SK)
    if sk is None:
        return
    mats = list(sk.get_editor_property("materials"))
    for m in mats:
        slot = str(m.get_editor_property("material_slot_name"))
        m.set_editor_property("material_interface", load(VIL_SKIN if "Skin" in slot else VIL_CLOTH))
    sk.set_editor_property("materials", mats)
    mark(VIL_SK)
    skel = sk.get_editor_property("skeleton")
    if skel is not None:
        mark(skel.get_path_name().split(".")[0])
        report["facts"]["villager_skeleton"] = skel.get_path_name()


def vil_skel():
    sk = load(VIL_SK)
    return sk.get_editor_property("skeleton") if sk else None


def step_villager_clips():
    skel = vil_skel()
    if skel is None:
        check("villager skeleton exists before the clips", False)
        return
    for path, fbx in ((VIL_WALK, "AN_LB_Villager_Walk.fbx"), (VIL_IDLE, "AN_LB_Villager_IdleLantern.fbx"), (VIL_WALKC, "AN_LB_Villager_WalkCandle.fbx")):
        if exists(path) and not REBUILD:
            note("%s exists: left alone" % path.rsplit("/", 1)[1])
            continue
        paths = fbx_task(os.path.join(SRC_VIL, fbx), VIL_DIR, path.rsplit("/", 1)[1], clip_options(skel, False, 0.0, True))
        check("clip import %s" % fbx, len(paths) == 1, paths)
        mark(path)


VBONES = ("root", "pelvis", "Head", "foot_l", "ball_l", "foot_r", "ball_r", "hand_l", "hand_r", "middle_01_r")


def verify_villager():
    sk = load(VIL_SK)
    check("SK_LB_Villager loads as SkeletalMesh", sk is not None and isinstance(sk, unreal.SkeletalMesh), sk)
    if sk is None:
        return
    slots = [(str(m.get_editor_property("material_slot_name")), m.get_editor_property("material_interface").get_name() if m.get_editor_property("material_interface") else None)
             for m in sk.get_editor_property("materials")]
    report["facts"]["villager_slots"] = slots
    check("two slots, cloth and skin", sorted(s[1] for s in slots) == ["M_LB_Villager_Cloth", "M_LB_Villager_Skin"], slots)
    b = sk.get_bounds()
    report["facts"]["villager_bounds_origin"] = v3(b.origin)
    report["facts"]["villager_bounds_extent"] = v3(b.box_extent)
    zmin, zmax = float(b.origin.z - b.box_extent.z), float(b.origin.z + b.box_extent.z)
    check("height about 187 cm, feet on z 0", abs(zmax - 186.5) < 3.0 and abs(zmin) < 2.0, (zmin, zmax))
    skel = sk.get_editor_property("skeleton")
    pose = unreal.AnimPoseExtensions.get_reference_pose(skel)
    names = [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(pose)]
    check("65 bones", len(names) == 65, len(names))
    ref = {b_: unreal.AnimPoseExtensions.get_bone_pose(pose, b_, unreal.AnimPoseSpaces.WORLD) for b_ in VBONES}
    fx, fy = float(ref["ball_l"].translation.x - ref["foot_l"].translation.x), float(ref["ball_l"].translation.y - ref["foot_l"].translation.y)
    yaw_off = math.degrees(math.atan2(fy, fx))
    report["facts"]["villager_facing_vector_foot_to_ball"] = [round(fx, 3), round(fy, 3)]
    report["facts"]["villager_yaw_offset_deg"] = round(yaw_off, 2)
    check("the mesh faces +X (toe ahead of the ankle on +X): yaw offset 0", abs(yaw_off) < 5.0, yaw_off)
    report["facts"]["villager_ref_hand_r"] = v3(ref["hand_r"].translation)
    for path, label, length in ((VIL_WALK, "Walk", 1.3333), (VIL_IDLE, "IdleLantern", None), (VIL_WALKC, "WalkCandle", 1.3333)):
        a = load(path)
        if not check("%s clip loads" % label, a is not None and isinstance(a, unreal.AnimSequence), a):
            continue
        L = float(a.get_editor_property("sequence_length"))
        report["facts"]["villager_%s_length" % label] = round(L, 4)
        if length:
            check("%s length %.4f s" % (label, length), abs(L - length) < 0.02, L)
        check("%s skeleton is the villager's" % label, a.get_editor_property("skeleton") == skel)
        p0 = comp_pose(a, 0.0, VBONES)
        dx, dy = float(p0["ball_l"].translation.x - p0["foot_l"].translation.x), float(p0["ball_l"].translation.y - p0["foot_l"].translation.y)
        cl = math.degrees(math.atan2(dy, dx))
        check("%s clip faces the same way as the mesh (yaw %.1f vs %.1f)" % (label, cl, yaw_off), abs(cl - yaw_off) < 15.0, cl)
        check("%s: pelvis height at t0 is about 100 cm" % label, 85.0 < float(p0["pelvis"].translation.z) < 115.0, float(p0["pelvis"].translation.z))
        rt = unreal.AnimationLibrary.get_bone_pose_for_time(a, "root", 0.0, False)
        report["facts"]["villager_%s_root_quat_t0" % label] = [round(float(v), 4) for v in (rt.rotation.x, rt.rotation.y, rt.rotation.z, rt.rotation.w)]
        report["facts"]["villager_%s_root_pos_t0" % label] = v3(rt.translation)
    # the walk's native ground speed from the in-place clip: the planted foot moves back at the walking speed
    a = load(VIL_WALK)
    if a is not None:
        L = float(a.get_editor_property("sequence_length"))
        n = int(round(L * 30))
        samples = []
        for i in range(n + 1):
            p = comp_pose(a, min(i / 30.0, L - 1e-4), ("foot_l", "foot_r", "pelvis"))
            samples.append((i / 30.0, [float(p[b_].translation.x) for b_ in ("foot_l", "foot_r", "pelvis")], [float(p[b_].translation.z) for b_ in ("foot_l", "foot_r", "pelvis")]))
        speeds = []
        for foot in (0, 1):
            zs = [s[2][foot] for s in samples]
            zmin_f = min(zs)
            planted = [i for i in range(1, len(samples)) if zs[i] < zmin_f + 2.0 and zs[i - 1] < zmin_f + 2.0]
            if len(planted) >= 3:
                xs = [(samples[i][0], samples[i][1][foot]) for i in planted]
                slope = (xs[-1][1] - xs[0][1]) / (xs[-1][0] - xs[0][0])
                speeds.append(-slope)
        report["facts"]["villager_walk_planted_foot_speed_cm_s"] = [round(s, 1) for s in speeds]
        report["facts"]["villager_walk_native_speed_cm_s_from_RM_clip"] = 97.5
        if speeds:
            check("a planted foot moves at the root-motion measurement (97.5 cm/s, within 10 %)", any(abs(s - 97.5) < 10.0 for s in speeds), speeds)


# ------------------------------------------------------------------------------------------------------------- main
def save_changed():
    for path in sorted(changed):
        if not allowed(path):
            check("save guard " + path, False, "outside the allowed paths")
            continue
        ok = EAL.save_asset(path, False)
        check("saved " + path, bool(ok))
        if ok:
            report["saved"].append(path)
    changed.clear()
    dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    ours = [d for d in dirty if allowed(d)]
    check("no dirty package of ours after the saves", not ours, ours[:10])
    if [d for d in dirty if not allowed(d)]:
        note("dirty packages outside our paths (not saved): %s" % [d for d in dirty if not allowed(d)][:10])


def main():
    if APPLY:
        legacy_fbx()
        if not STEPS or "fade" in STEPS:
            step_fade()
        if not STEPS or "mask" in STEPS:
            step_mask()
        if not STEPS or "lift" in STEPS:
            step_lift()
        if not STEPS or "textures" in STEPS:
            step_textures()
        if not STEPS or "materials" in STEPS:
            step_materials()
        if not STEPS or "sk" in STEPS:
            step_villager_sk()
        if not STEPS or "clips" in STEPS:
            step_villager_clips()
        save_changed()
    verify_fade()
    verify_mask()
    verify_lift()
    verify_textures()
    verify_materials()
    verify_villager()


try:
    main()
except Exception:  # noqa: BLE001
    report["failures"].append("exception: " + traceback.format_exc()[-800:])
    unreal.log_error("%s EXCEPTION %s" % (TAG, traceback.format_exc()))
finally:
    report["ok"] = not report["failures"]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    unreal.log("%s RESULT: %s (%d checks, %d failures) mode=%s" % (TAG, "PASS" if report["ok"] else "FAIL", report["checks"], len(report["failures"]), MODE))
