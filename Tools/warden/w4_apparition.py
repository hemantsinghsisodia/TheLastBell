"""w4_apparition.py -- P17 W4: reimport SM_LB_Warden_Apparition in place from the re-baked FBX (headless, Unreal editor CLOSED).

    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=Tools/warden/w4_apparition.py -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>
Environment: W4_STEP  state (default, read-only) | import | check (read-only)      W4_SAVE 1 = save SM_LB_Warden_Apparition (ONE save), then is-dirty      W4_OUT JSON path
Last line printed: W4_DONE

The FBX is SourceArt/Warden/SM_LB_Warden_Apparition.fbx, baked from SourceArt/Warden/V11_1w by Tools/blender/warden/bake_silhouette.py (--rotz 90).
Import = AssetImportTask over the existing asset with the legacy FBX importer (the Interchange FBX flag is switched off for the process, as in w3_swap_v11_1.py),
no materials/textures, no Nanite, no generated collision, combine meshes, one LOD. Afterwards: Nanite off, simple collision removed, slots MAT_Body / MAT_Mask
on MI_Warden_Apparition_Body / MI_Warden_Apparition_Mask. Nothing else is saved.
"""
import json
import os
import traceback

import unreal

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
STEP = os.environ.get("W4_STEP", "state")
SAVE = os.environ.get("W4_SAVE", "0") == "1"
OUT = os.environ.get("W4_OUT", os.path.join(ROOT, "Saved", "w4_%s.json" % STEP))
FBX = os.path.join(ROOT, "SourceArt", "Warden", "SM_LB_Warden_Apparition.fbx")
FOLDER = "/Game/LastBell/Characters/Warden/Meshes"
PATH = FOLDER + "/SM_LB_Warden_Apparition"
MATS = {"MAT_Body": "/Game/LastBell/Characters/Warden/Materials/MI_Warden_Apparition_Body", "MAT_Mask": "/Game/LastBell/Characters/Warden/Materials/MI_Warden_Apparition_Mask"}
ESL = unreal.EditorStaticMeshLibrary
EAL = unreal.EditorAssetLibrary
res = {"step": STEP}


def log(*a):
    print("W4| " + " ".join(str(x) for x in a))


def state():
    m = unreal.load_asset(PATH + ".SM_LB_Warden_Apparition")
    s = {"slots": [{"slot": str(x.get_editor_property("material_slot_name")), "material": (x.get_editor_property("material_interface").get_path_name() if x.get_editor_property("material_interface") else None)} for x in m.get_editor_property("static_materials")]}
    s["probe"] = [x for x in dir(m) if any(k in x for k in ("lod", "tri", "vert", "section", "collision", "num_"))][:40]
    s["num_lods"] = m.get_num_lods() if hasattr(m, "get_num_lods") else None
    s["num_triangles_lod0"] = m.get_num_triangles(0) if hasattr(m, "get_num_triangles") else None
    s["num_vertices_lod0"] = m.get_num_vertices(0) if hasattr(m, "get_num_vertices") else None
    s["num_sections_lod0"] = m.get_num_sections(0) if hasattr(m, "get_num_sections") else None
    s["lod_count"] = s["num_lods"]
    s["triangles_lod0"] = s["num_triangles_lod0"]
    b = m.get_bounds()
    s["bounds_origin"] = [round(float(v), 2) for v in (b.origin.x, b.origin.y, b.origin.z)]
    s["bounds_extent"] = [round(float(v), 2) for v in (b.box_extent.x, b.box_extent.y, b.box_extent.z)]
    s["nanite"] = bool(m.get_editor_property("nanite_settings").get_editor_property("enabled"))
    try:
        bs0 = m.get_editor_property("body_setup")
        s["simple_collision_shapes"] = len(bs0.get_editor_property("agg_geom").get_editor_property("convex_elems")) + len(bs0.get_editor_property("agg_geom").get_editor_property("box_elems")) + len(bs0.get_editor_property("agg_geom").get_editor_property("sphere_elems")) + len(bs0.get_editor_property("agg_geom").get_editor_property("sphyl_elems"))
    except Exception as e:
        s["simple_collision_shapes"] = "n/a: " + str(e)[:60]
    try:
        s["import_data_class"] = m.get_editor_property("asset_import_data").get_class().get_name()
        s["source_files"] = list(m.get_editor_property("asset_import_data").extract_filenames())
    except Exception as e:
        s["import_data_error"] = str(e)[:100]
    try:
        bs = m.get_editor_property("body_setup")
        s["collision_trace_flag"] = str(bs.get_editor_property("collision_trace_flag"))
    except Exception as e:
        s["collision_trace_flag"] = "n/a"
    return s


def dirty_pkgs():
    return [x.get_name() for x in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]


def step_import():
    cv = "Interchange.FeatureFlags.Import.FBX"
    unreal.SystemLibrary.execute_console_command(None, cv + " 0")
    res["interchange_fbx_flag"] = unreal.SystemLibrary.get_console_variable_bool_value(cv)
    res["before"] = state()
    o = unreal.FbxImportUI()
    for k, v in dict(automated_import_should_detect_type=False, import_as_skeletal=False, mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH, import_mesh=True,
                     import_materials=False, import_textures=False, import_animations=False).items():
        o.set_editor_property(k, v)
    d = o.get_editor_property("static_mesh_import_data")
    for k, v in dict(combine_meshes=True, auto_generate_collision=False, build_nanite=False, import_uniform_scale=1.0, convert_scene=True, convert_scene_unit=True, force_front_x_axis=False).items():
        try:
            d.set_editor_property(k, v)
        except Exception as e:
            log("option %s not set: %s" % (k, str(e)[:80]))
    t = unreal.AssetImportTask()
    for k, v in dict(filename=FBX, destination_path=FOLDER, destination_name="SM_LB_Warden_Apparition", automated=True, replace_existing=True, replace_existing_settings=True, save=False, async_=False).items():
        t.set_editor_property(k, v)
    t.set_editor_property("factory", unreal.FbxFactory())
    t.set_editor_property("options", o)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    log("import ->", list(t.get_editor_property("imported_object_paths")))
    m = unreal.load_asset(PATH + ".SM_LB_Warden_Apparition")
    if state()["simple_collision_shapes"] not in (0, None) and not str(state()["simple_collision_shapes"]).startswith("n/a"):
        ESL.remove_collisions(m)
    ns = m.get_editor_property("nanite_settings")
    if ns.get_editor_property("enabled"):
        ns.set_editor_property("enabled", False)
        m.set_editor_property("nanite_settings", ns)
    slots = list(m.get_editor_property("static_materials"))
    for s in slots:
        n = str(s.get_editor_property("material_slot_name"))
        if n in MATS:
            s.set_editor_property("material_interface", unreal.load_asset(MATS[n] + "." + MATS[n].rsplit("/", 1)[1]))
    m.set_editor_property("static_materials", slots)
    res["after"] = state()
    bad = []
    a, b = res["after"], res["before"]
    if [x["slot"] for x in a["slots"]] != ["MAT_Body", "MAT_Mask"]:
        bad.append("slots %s" % a["slots"])
    for x in a["slots"]:
        want = MATS.get(x["slot"])
        if not x["material"] or want not in x["material"]:
            bad.append("slot %s material %s" % (x["slot"], x["material"]))
    if a["nanite"]:
        bad.append("Nanite on")
    if a["lod_count"] not in (1, None):
        bad.append("LOD count %s" % a["lod_count"])
    if a.get("simple_collision_shapes") not in (0, None) and not str(a.get("simple_collision_shapes")).startswith("n/a"):
        bad.append("collision shapes %s" % a["simple_collision_shapes"])
    if abs(a["bounds_extent"][2] * 2 - 284.4) > 1.5:
        bad.append("height %s" % (a["bounds_extent"][2] * 2))
    if a["triangles_lod0"] is not None and not (6500 <= a["triangles_lod0"] <= 8000):
        bad.append("triangles %s" % a["triangles_lod0"])
    res["problems"] = bad
    log("problems:", bad)
    if SAVE:
        if bad:
            raise RuntimeError("problems; NOT saving: %s" % bad)
        ok = EAL.save_asset(PATH, only_if_is_dirty=False)
        res["saved"] = ok
        res["dirty_packages_after_save"] = dirty_pkgs()
        log("SAVE", PATH, ok, "dirty packages after:", res["dirty_packages_after_save"])


def main():
    if STEP == "state" or STEP == "check":
        res["state"] = state()
        log(json.dumps(res["state"]))
        if STEP == "check":
            res["dirty_packages"] = dirty_pkgs()
    elif STEP == "import":
        step_import()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)


try:
    main()
    log("OK")
except Exception:
    log("FAILED\n" + traceback.format_exc())
log("W4_DONE")
