"""w3_swap_v11_1.py -- P17 W3: the V11.1 Warden swap, clips and materials (headless, Unreal editor CLOSED, one process at a time).

    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=Tools/warden/w3_swap_v11_1.py -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>
Environment:
    W3_STEP   state (default, read-only) | clips | materials | check (read-only)
    W3_SAVE   1 = save the packages the step names, ONE explicit save each, then report is-dirty; anything else = nothing is saved
    W3_OUT    JSON written with the result (default Saved/w3_<step>.json)
Last line printed: W3_DONE

The mesh itself is reimported by Tools/warden/p13_reimport_warden.py (P13W_STEP=rotlods, P13W_EXPECT_SLOTS=8). This script:
  clips      AN_Warden_Idle / Walk / DoorwayStoop: AssetImportTask over the existing assets from SourceArt/Warden/V11_1w/exports with the owner's clip options
             (scene/unit conversion, scale 1, custom sample rate 30, exported duration, existing skeleton). Checks length, skeleton, no stray assets,
             the root bone's local rotation at frame 0 (the constant -90 deg yaw key convention must not change).
  materials  on the copied V11.1 native materials (Content/WardenArtV11_1, see w3_copy_materials.py): the project's tuning (apply_p12_materials.py: BaseColorMul / MetallicMul /
             RoughnessMul on M_Warden_BellMetal, BaseColorMul on RustedIron and ChainIron, instances with the table values, Wool Cloth Brightness 0.25;
             apply_p12f_art.py: TellGlow + TellGlowColor on M_Warden_BellMetal, Emissive = TellGlowColor x TellGlow x 8), then slots 0-7 of SK_Warden by name.
  check      8 slots and their materials, the mask socket, skeleton, TellGlow, the parameters, the clips.
Never saves a map or anything outside the named packages.
"""
import json
import os
import traceback

import unreal

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
STEP = os.environ.get("W3_STEP", "state")
SAVE = os.environ.get("W3_SAVE", "0") == "1"
OUT = os.environ.get("W3_OUT", os.path.join(ROOT, "Saved", "w3_%s.json" % STEP))
MESH = "/Game/LastBell/Characters/Warden/Meshes/SK_Warden"
SKEL = "/Game/LastBell/Characters/Warden/Meshes/SK_Warden_Skeleton"
ANIMS = "/Game/LastBell/Characters/Warden/Anims"
V11 = "/Game/WardenArtV11_1/Materials"
FBX = os.path.join(ROOT, "SourceArt", "Warden", "V11_1w", "exports")
GROUP = "Warden Tuning"
ANIM_YAW = float(os.environ.get("W3_ANIM_YAW", "0"))
CLIPS = {"AN_Warden_Idle": ("Idle", 4.0), "AN_Warden_Walk": ("Walk", 2.0), "AN_Warden_DoorwayStoop": ("DoorwayStoop", 3.0)}
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
SLOT_MATERIAL = {"M_Warden_Wool": "MI_Warden_Wool", "M_Warden_BellMetal": "MI_Warden_BellMetal", "M_Warden_RustedIron": "MI_Warden_RustedIron", "M_Warden_Skin": "MI_Warden_Skin",
                 "M_Warden_Leather": "M_Warden_Leather", "M_Warden_ChainIron": "MI_Warden_ChainIron", "M_Warden_DimEyes": "M_Warden_DimEyes", "M_Warden_Keratin": "M_Warden_Keratin"}
SLOT_ORDER = list(SLOT_MATERIAL)
# parent -> [(parameter, material property)]
PARENT_PARAMS = {"M_Warden_BellMetal": [("BaseColorMul", unreal.MaterialProperty.MP_BASE_COLOR), ("MetallicMul", unreal.MaterialProperty.MP_METALLIC), ("RoughnessMul", unreal.MaterialProperty.MP_ROUGHNESS)],
                 "M_Warden_RustedIron": [("BaseColorMul", unreal.MaterialProperty.MP_BASE_COLOR)],
                 "M_Warden_ChainIron": [("BaseColorMul", unreal.MaterialProperty.MP_BASE_COLOR)]}
NEW_MIS = {"MI_Warden_BellMetal": ("M_Warden_BellMetal", {"BaseColorMul": 1.6, "MetallicMul": 0.35, "RoughnessMul": 0.85}),
           "MI_Warden_Skin": ("M_Warden_Skin", {"Skin Brightness": 0.12}),
           "MI_Warden_RustedIron": ("M_Warden_RustedIron", {"BaseColorMul": 0.6}),
           "MI_Warden_ChainIron": ("M_Warden_ChainIron", {"BaseColorMul": 0.5})}
WOOL_MI, CLOTH = "MI_Warden_Wool", 0.25
TELL = {"TellGlow": 0.0}
TELL_COLOR = (1.0, 0.06, 0.02)
TELL_BRIGHTNESS = 8.0
res = {"step": STEP, "save": SAVE}


def log(*a):
    print("W3| " + " ".join(str(x) for x in a))


def load(p):
    o = unreal.load_asset(p + "." + p.rsplit("/", 1)[1])
    assert o is not None, "missing " + p
    return o


def dirty(o):
    """Is the asset's package among the editor's dirty content packages?"""
    try:
        pn = o.get_package().get_name()
        return pn in [x.get_name() for x in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    except Exception as e:
        return "unknown: " + str(e)[:60]


def save(path, report):
    """ONE explicit save per package, then is_dirty."""
    o = load(path)
    ok = EAL.save_asset(path, only_if_is_dirty=False)
    d = dirty(load(path))
    report.append({"package": path, "saved": ok, "dirty_after": d})
    log("SAVE", path, ok, "dirty after:", d)
    if not ok:
        raise RuntimeError("save failed: " + path)


# ------------------------------------------------------------------------------------------------ clips
def root_rot(a):
    """Local rotation of `root` at time 0 and the hand position (local) at time 0, as a fingerprint of the clip."""
    out = {}
    try:
        t = unreal.AnimationLibrary.get_bone_pose_for_time(a, "root", 0.0, False)
        out["root_quat_t0"] = [round(float(v), 5) for v in (t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w)]
        out["root_pos_t0"] = [round(float(v), 3) for v in (t.translation.x, t.translation.y, t.translation.z)]
        for b in ("hand_l", "hand_r", "head", "pelvis", "thigh_l"):
            h = unreal.AnimationLibrary.get_bone_pose_for_time(a, b, 0.0, False)
            out[b + "_quat_t0"] = [round(float(v), 4) for v in (h.rotation.x, h.rotation.y, h.rotation.z, h.rotation.w)]
    except Exception as e:
        out["error"] = str(e)[:150]
    # component-space positions (cm) at two times: the facing and the pose in the mesh's frame
    try:
        comp = {}
        for tm in (0.0, 1.0):
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(a, tm, unreal.AnimPoseEvaluationOptions())
            comp[str(tm)] = {b: [round(float(v), 2) for v in (lambda tr: (tr.translation.x, tr.translation.y, tr.translation.z))(unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD))]
                             for b in ("pelvis", "head", "foot_l", "ball_l", "foot_r", "hand_l", "hand_r", "lowerarm_l", "upperarm_l")}
        out["component_pos"] = comp
    except Exception as e:
        out["component_error"] = str(e)[:200]
    return out


def clip_info(name):
    a = load(ANIMS + "/" + name)
    d = {"length": round(float(a.get_editor_property("sequence_length")), 4), "skeleton": a.get_editor_property("skeleton").get_path_name(), "dirty": dirty(a)}
    try:
        d["num_frames"] = int(unreal.AnimationLibrary.get_num_frames(a))
    except Exception:
        d["num_frames"] = "n/a"
    try:
        d["notifies"] = len(unreal.AnimationLibrary.get_animation_notify_events(a))
    except Exception:
        d["notifies"] = "n/a"
    d["rate_scale"] = float(a.get_editor_property("rate_scale"))
    d["root_motion"] = bool(a.get_editor_property("enable_root_motion"))
    d.update(root_rot(a))
    try:
        d["source_files"] = list(a.get_editor_property("asset_import_data").extract_filenames())
    except Exception:
        pass
    return d


def anim_options(skeleton):
    o = unreal.FbxImportUI()
    for k, v in dict(automated_import_should_detect_type=False, import_as_skeletal=True, mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION, import_mesh=False,
                     import_animations=True, import_materials=False, import_textures=False, create_physics_asset=False).items():
        o.set_editor_property(k, v)
    o.set_editor_property("skeleton", skeleton)
    d = o.get_editor_property("anim_sequence_import_data")
    for k, v in dict(import_uniform_scale=1.0, convert_scene=True, convert_scene_unit=True, force_front_x_axis=True,
                     animation_length=unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME, use_default_sample_rate=False, custom_sample_rate=30,
                     import_bone_tracks=True, preserve_local_transform=False).items():
        try:
            d.set_editor_property(k, v)
        except Exception as e:
            log("anim option %s not set: %s" % (k, str(e)[:80]))
    # Facing: with the animation-only importer Force Front X is not applied (the FBX carries the root correction for it), so the clip came in turned -90 deg yaw
    # against SK_Warden (measured by component-space bone positions: head +X -> -Y). The old clips are imported so that `root` is the identity at t0 and the head leads on +X.
    d.set_editor_property("import_rotation", unreal.Rotator(0.0, 0.0, ANIM_YAW))
    return o


def legacy_fbx():
    """FbxFactory hands FBX files to Interchange in 5.8, which ignores FbxImportUI (no Force Front X, no import rotation). The owner's native clips were imported with the
    legacy importer: switch the Interchange FBX feature flag off for this process (in memory only)."""
    cv = "Interchange.FeatureFlags.Import.FBX"
    try:
        res["interchange_fbx_before"] = unreal.SystemLibrary.get_console_variable_bool_value(cv)
        unreal.SystemLibrary.execute_console_command(None, cv + " 0")
        res["interchange_fbx_after"] = unreal.SystemLibrary.get_console_variable_bool_value(cv)
    except Exception as e:
        res["interchange_fbx_error"] = str(e)[:200]
    log("Interchange FBX flag:", res.get("interchange_fbx_before"), "->", res.get("interchange_fbx_after"), res.get("interchange_fbx_error", ""))


def step_clips():
    legacy_fbx()
    skeleton = load(SKEL)
    before = {n: clip_info(n) for n in CLIPS}
    listing_before = sorted(EAL.list_assets(ANIMS, recursive=False, include_folder=False))
    res["before"] = before
    imp = unreal.AssetToolsHelpers.get_asset_tools()
    for name, (label, length) in CLIPS.items():
        t = unreal.AssetImportTask()
        for k, v in dict(filename=os.path.join(FBX, "AN_Warden_%s.fbx" % label), destination_path=ANIMS, destination_name=name, automated=True, replace_existing=True,
                         replace_existing_settings=True, save=False, async_=False).items():
            t.set_editor_property(k, v)
        t.set_editor_property("factory", unreal.FbxFactory())
        t.set_editor_property("options", anim_options(skeleton))
        imp.import_asset_tasks([t])
        log("import", name, "->", list(t.get_editor_property("imported_object_paths")))
    after = {n: clip_info(n) for n in CLIPS}
    listing_after = sorted(EAL.list_assets(ANIMS, recursive=False, include_folder=False))
    res["after"] = after
    res["new_assets_in_Anims"] = sorted(set(listing_after) - set(listing_before))
    res["missing_assets_in_Anims"] = sorted(set(listing_before) - set(listing_after))
    bad = []
    for n, (label, length) in CLIPS.items():
        if abs(after[n]["length"] - length) > 0.01:
            bad.append("%s length %s" % (n, after[n]["length"]))
        if after[n]["skeleton"] != before[n]["skeleton"]:
            bad.append("%s skeleton %s" % (n, after[n]["skeleton"]))
        for t in ("0.0", "1.0"):
            for bone in ("pelvis", "head", "foot_l", "ball_l", "foot_r"):          # bones whose motion did not change in V11.1 (W0): must sit where they sat
                ob, nb = before[n]["component_pos"][t][bone], after[n]["component_pos"][t][bone]
                if max(abs(x - y) for x, y in zip(ob, nb)) > 0.6:
                    bad.append("%s t=%s %s moved %s -> %s (facing/convention)" % (n, t, bone, ob, nb))
        if after[n].get("root_quat_t0") != before[n].get("root_quat_t0"):
            bad.append("%s root yaw key changed: %s -> %s" % (n, before[n].get("root_quat_t0"), after[n].get("root_quat_t0")))
        if after[n]["rate_scale"] != before[n]["rate_scale"] or after[n]["root_motion"] != before[n]["root_motion"]:
            bad.append("%s rate/root motion changed" % n)
        if "FBX" not in json.dumps(after[n].get("source_files")).upper():
            bad.append("%s source file not updated" % n)
    if res["new_assets_in_Anims"] or res["missing_assets_in_Anims"]:
        bad.append("asset list changed: +%s -%s" % (res["new_assets_in_Anims"], res["missing_assets_in_Anims"]))
    res["problems"] = bad
    log("clips problems:", bad)
    if SAVE:
        if bad:
            raise RuntimeError("problems; NOT saving: %s" % bad)
        sv = []
        for n in CLIPS:
            save(ANIMS + "/" + n, sv)
        res["saves"] = sv


# ------------------------------------------------------------------------------------------------ materials
def find_param(mat, name):
    return name in [str(n) for n in MEL.get_scalar_parameter_names(mat)] or name in [str(n) for n in MEL.get_vector_parameter_names(mat)]


def add_scalar(mat, name, default, x, y):
    e = MEL.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("default_value", float(default))
    e.set_editor_property("group", GROUP)
    return e


def add_vector(mat, name, rgb, x, y):
    e = MEL.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, x, y)
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("default_value", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
    e.set_editor_property("group", GROUP)
    return e


def add_parent_params(name, report):
    mat = load(V11 + "/" + name)
    for pname, prop in PARENT_PARAMS[name]:
        if find_param(mat, pname):
            report.append("%s.%s already exists" % (name, pname))
            continue
        feeder = MEL.get_material_property_input_node(mat, prop)
        out = MEL.get_material_property_input_node_output_name(mat, prop)
        assert feeder is not None, "%s: %s is not connected" % (name, prop)
        mul = MEL.create_material_expression(mat, unreal.MaterialExpressionMultiply, 600, 0)
        sp = add_scalar(mat, pname, 1.0, 300, 200)
        assert MEL.connect_material_expressions(feeder, out, mul, "A"), "connect feeder"
        assert MEL.connect_material_expressions(sp, "", mul, "B"), "connect scalar"
        assert MEL.connect_material_property(mul, "", prop), "connect output"
        report.append("%s: %s x %s (feeder %s.%s)" % (name, prop, pname, feeder.get_name(), out))
    MEL.recompile_material(mat)


def add_tell(report):
    mat = load(V11 + "/M_Warden_BellMetal")
    if find_param(mat, "TellGlow") and find_param(mat, "TellGlowColor"):
        report.append("TellGlow already exists")
        return
    prop = unreal.MaterialProperty.MP_EMISSIVE_COLOR
    old = MEL.get_material_property_input_node(mat, prop)
    old_out = MEL.get_material_property_input_node_output_name(mat, prop) if old else ""
    tg = add_scalar(mat, "TellGlow", TELL["TellGlow"], -1200, 1060)
    tc = add_vector(mat, "TellGlowColor", TELL_COLOR, -1200, 900)
    m1 = MEL.create_material_expression(mat, unreal.MaterialExpressionMultiply, -900, 900)
    m2 = MEL.create_material_expression(mat, unreal.MaterialExpressionMultiply, -750, 900)
    m2.set_editor_property("const_b", TELL_BRIGHTNESS)
    assert MEL.connect_material_expressions(tc, "", m1, "A")
    assert MEL.connect_material_expressions(tg, "", m1, "B")
    assert MEL.connect_material_expressions(m1, "", m2, "A")
    final = m2
    if old is not None:
        add = MEL.create_material_expression(mat, unreal.MaterialExpressionAdd, -600, 900)
        assert MEL.connect_material_expressions(old, old_out, add, "A")
        assert MEL.connect_material_expressions(m2, "", add, "B")
        final = add
    assert MEL.connect_material_property(final, "", prop)
    MEL.recompile_material(mat)
    report.append("M_Warden_BellMetal: TellGlow, TellGlowColor added; emissive %s" % ("added to old feeder " + old.get_name() if old is not None else "was not connected"))


def set_scalar(mi, k, v):
    """Scalar override on a MaterialInstanceConstant. MaterialEditingLibrary.set_material_instance_scalar_parameter_value returns False here for every parameter
    (also for ones the instance's parent has had from the start), so the override list is written directly; the value is read back."""
    info = unreal.MaterialParameterInfo()
    info.set_editor_property("name", k)
    info.set_editor_property("association", unreal.MaterialParameterAssociation.GLOBAL_PARAMETER)
    info.set_editor_property("index", -1)
    pv = unreal.ScalarParameterValue()
    pv.set_editor_property("parameter_info", info)
    pv.set_editor_property("parameter_value", float(v))
    cur = [x for x in mi.get_editor_property("scalar_parameter_values") if str(x.get_editor_property("parameter_info").get_editor_property("name")) != k]
    mi.set_editor_property("scalar_parameter_values", cur + [pv])
    MEL.update_material_instance(mi)
    got = scalars(mi).get(k)
    assert got is not None and abs(got - float(v)) < 1e-4, "%s.%s reads %s, want %s" % (mi.get_name(), k, got, v)


def make_mi(name, parent, values, report):
    path = V11 + "/" + name
    if EAL.does_asset_exist(path):
        mi = load(path)
    else:
        mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, V11, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    assert mi is not None, "could not create " + name
    MEL.set_material_instance_parent(mi, load(V11 + "/" + parent))
    for k, v in values.items():
        set_scalar(mi, k, v)
    MEL.update_material_instance(mi)
    report.append("%s (parent %s) %s" % (name, parent, values))
    return mi


def assign_slots(report):
    m = load(MESH)
    slots = list(m.get_editor_property("materials"))
    for s in slots:
        n = str(s.get_editor_property("material_slot_name"))
        want = SLOT_MATERIAL[n]
        s.set_editor_property("material_interface", load(V11 + "/" + want))
    m.set_editor_property("materials", slots)
    m.modify()
    for s in m.get_editor_property("materials"):
        report.append("%s -> %s" % (s.get_editor_property("material_slot_name"), s.get_editor_property("material_interface").get_path_name()))


def step_materials():
    rep = []
    for p in ("M_Warden_BellMetal", "M_Warden_RustedIron", "M_Warden_ChainIron"):
        add_parent_params(p, rep)
    add_tell(rep)
    for n, (par, vals) in NEW_MIS.items():
        make_mi(n, par, vals, rep)
    wool = load(V11 + "/" + WOOL_MI)
    rep.append("MI_Warden_Wool Cloth Brightness before %s" % [(str(p.get_editor_property("parameter_info").get_editor_property("name")), p.get_editor_property("parameter_value")) for p in wool.get_editor_property("scalar_parameter_values")])
    set_scalar(wool, "Cloth Brightness", CLOTH)
    assign_slots(rep)
    res["materials_log"] = rep
    for r in rep:
        log(r)
    if SAVE:
        sv = []
        for p in ("M_Warden_BellMetal", "M_Warden_RustedIron", "M_Warden_ChainIron"):
            save(V11 + "/" + p, sv)
        for n in list(NEW_MIS) + [WOOL_MI]:
            save(V11 + "/" + n, sv)
        save(MESH, sv)
        res["saves"] = sv


# ------------------------------------------------------------------------------------------------ check
def scalars(mi):
    return {str(p.get_editor_property("parameter_info").get_editor_property("name")): round(float(p.get_editor_property("parameter_value")), 5) for p in mi.get_editor_property("scalar_parameter_values")}


def step_check():
    bad, ok = [], []
    m = load(MESH)
    slots = [str(s.get_editor_property("material_slot_name")) for s in m.get_editor_property("materials")]
    (ok if slots == SLOT_ORDER else bad).append("slots %s" % slots)
    sub = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    secs = [sub.get_num_sections(m, i) for i in range(sub.get_lod_count(m))]
    (ok if secs == [8, 8, 8] else bad).append("sections per LOD %s" % secs)
    res["lod_vertices"] = [sub.get_num_verts(m, i) for i in range(sub.get_lod_count(m))]
    for s in m.get_editor_property("materials"):
        n = str(s.get_editor_property("material_slot_name"))
        mi = s.get_editor_property("material_interface")
        want = "%s/%s.%s" % (V11, SLOT_MATERIAL[n], SLOT_MATERIAL[n])
        (ok if mi is not None and mi.get_path_name() == want else bad).append("slot %s material %s" % (n, mi.get_path_name() if mi else None))
    socks = [(str(m.get_socket_by_index(i).get_editor_property("socket_name")), str(m.get_socket_by_index(i).get_editor_property("bone_name"))) for i in range(m.num_sockets())]
    (ok if socks == [("mask", "head")] else bad).append("sockets %s" % socks)
    import editor_toolset.toolsets.skeletal_mesh as smt
    bones = list(smt.SkeletalMeshTools().get_bone_names(m))
    (ok if len(bones) == 110 and bones[0] == "root" else bad).append("bones %d first %s" % (len(bones), bones[0]))
    (ok if m.get_editor_property("skeleton").get_path_name().endswith("SK_Warden_Skeleton.SK_Warden_Skeleton") else bad).append("skeleton")
    (ok if m.get_editor_property("physics_asset") and m.get_editor_property("physics_asset").get_path_name().endswith("SK_Warden_PhysicsAsset.SK_Warden_PhysicsAsset") else bad).append("physics asset")
    b = m.get_bounds()
    h = 2 * float(b.box_extent.z)
    (ok if abs(h - 290) <= 1.0 else bad).append("height %.2f" % h)
    bell = load(V11 + "/M_Warden_BellMetal")
    names = [str(n) for n in MEL.get_scalar_parameter_names(bell)] + [str(n) for n in MEL.get_vector_parameter_names(bell)]
    for want in ("TellGlow", "TellGlowColor", "BaseColorMul", "MetallicMul", "RoughnessMul"):
        (ok if want in names else bad).append("M_Warden_BellMetal has %s" % want)
    mib = load(V11 + "/MI_Warden_BellMetal")
    (ok if mib.get_editor_property("parent").get_path_name().endswith("/M_Warden_BellMetal.M_Warden_BellMetal") and abs(scalars(mib).get("BaseColorMul", 0) - 1.6) < 1e-4 else bad).append("MI_Warden_BellMetal %s" % scalars(mib))
    w = scalars(load(V11 + "/" + WOOL_MI))
    (ok if abs(w.get("Cloth Brightness", -1) - CLOTH) < 1e-4 else bad).append("MI_Warden_Wool %s" % w)
    sk = scalars(load(V11 + "/MI_Warden_Skin"))
    (ok if abs(sk.get("Skin Brightness", -1) - 0.12) < 1e-4 else bad).append("MI_Warden_Skin %s" % sk)
    for n in CLIPS:
        c = clip_info(n)
        (ok if abs(c["length"] - CLIPS[n][1]) < 0.01 and c["skeleton"].endswith("SK_Warden_Skeleton.SK_Warden_Skeleton") else bad).append("clip %s %s" % (n, c))
    # nothing involved is dirty
    dirty_list = {p: dirty(load(p)) for p in [MESH] + [V11 + "/" + n for n in ("M_Warden_BellMetal", "M_Warden_RustedIron", "M_Warden_ChainIron", "MI_Warden_BellMetal", "MI_Warden_Skin", "MI_Warden_RustedIron", "MI_Warden_ChainIron", "MI_Warden_Wool")] + [ANIMS + "/" + n for n in CLIPS]}
    res["dirty"] = dirty_list
    for p, d in dirty_list.items():
        if d is not False:
            bad.append("dirty: %s %s" % (p, d))
    res["ok"], res["bad"] = ok, bad
    for x in ok:
        log("PASS", x[:200])
    for x in bad:
        log("FAIL", x[:300])
    log("CHECK %d/%d" % (len(ok), len(ok) + len(bad)))


def main():
    if STEP == "state":
        for n in ("AN_Warden_Idle", "AN_Warden_Walk", "AN_Warden_DoorwayStoop", "AN_Warden_MutantWalking", "AN_Warden_ZombieWalk", "AN_Warden_LookAround"):
            try:
                res.setdefault("clips_state", {})[n] = clip_info(n)
                log("state", n, json.dumps(res["clips_state"][n])[:700])
            except Exception as e:
                log("state", n, "failed", str(e)[:100])
    {"state": lambda: None, "clips": step_clips, "materials": step_materials, "check": step_check}[STEP]()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)


try:
    main()
    log("OK")
except Exception:
    log("FAILED\n" + traceback.format_exc())
    try:
        res["failed"] = traceback.format_exc()
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1, default=str)
    except Exception:
        pass
log("W3_DONE")
