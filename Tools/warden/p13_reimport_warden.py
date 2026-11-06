"""p13_reimport_warden.py -- P13-4c: re-import the reweighted Warden (SourceArt/Warden/V5_5w2/exports/SK_Warden_LOD0/1/2.fbx) into SK_Warden IN PLACE.

HEADLESS, Unreal editor CLOSED (checked with tasklist before every run), no other UnrealEditor / UnrealBuildTool process:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=Tools/warden/p13_reimport_warden.py -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>
A script can't take arguments, so it reads environment variables:
    P13W_STEP   state   (default) read-only: print and write the state of SK_Warden
                lodimport  SkeletalMeshEditorSubsystem.import_lod(mesh, i, file) for LOD 0, 1, 2          (method A: turns the mesh 90 deg, rejected)
                lod0rot    import_lod(mesh, 0, SK_Warden_LOD0_rot.fbx): witness that the rotated files import like Force Front X
                taskimport AssetImportTask over the existing asset with the stored import options        (method B, LOD0 only)
                reimportlods method B for LOD0, then import_lod for LOD 1 and 2 from the rotated files in P13W_ROT   (the method that works)
    P13W_ROT    folder with SK_Warden_LOD0/1/2_rot.fbx from Tools/blender/warden/p13_export_lods_rotated.py (default SourceArt/Warden/V5_5w2/ue_lod)
    P13W_SRC    folder with the three FBX (default SourceArt/Warden/V5_5w2/exports)
    P13W_OUT    JSON written with the state before and after (default Saved/p13w_<step>.json)
    P13W_DUMP   JSON path: write every LOD's positions and bone weights (after the import, or of the saved asset for step state), for the Blender check; empty = none
    P13W_SAVE   1 = save SK_Warden (ONE save call, only that asset) when the post-state matches the pre-state; anything else = nothing is saved
Last line printed: P13W_DONE
Nothing but SK_Warden is ever saved, and SK_Warden is never deleted.
"""
import json
import os
import traceback

import unreal

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
MESH = "/Game/LastBell/Characters/Warden/Meshes/SK_Warden"
STEP = os.environ.get("P13W_STEP", "state")
SRC = os.environ.get("P13W_SRC", os.path.join(ROOT, "SourceArt", "Warden", "V5_5w2", "exports"))
OUT = os.environ.get("P13W_OUT", os.path.join(ROOT, "Saved", "p13w_%s.json" % STEP))
ROT = os.environ.get("P13W_ROT", os.path.join(ROOT, "SourceArt", "Warden", "V5_5w2", "ue_lod"))
DUMP = os.environ.get("P13W_DUMP", "")
SAVE = os.environ.get("P13W_SAVE", "0") == "1"
SUB = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)


def log(*a):
    print("P13W| " + " ".join(str(x) for x in a))


def vec(v):
    return [round(float(v.x), 4), round(float(v.y), 4), round(float(v.z), 4)]


def state(m):
    """Everything the task wants compared before and after."""
    s = {}
    s["lod_count"] = SUB.get_lod_count(m)
    s["lod_vertices"] = [SUB.get_num_verts(m, i) for i in range(s["lod_count"])]
    s["lod_sections"] = [SUB.get_num_sections(m, i) for i in range(s["lod_count"])]
    s["lod_section_material_slot"] = [[SUB.get_lod_material_slot(m, i, j) for j in range(s["lod_sections"][i])] for i in range(s["lod_count"])]
    s["slots"] = [{"slot": str(x.get_editor_property("material_slot_name")), "imported": str(x.get_editor_property("imported_material_slot_name")),
                   "material": (x.get_editor_property("material_interface").get_path_name() if x.get_editor_property("material_interface") else None)} for x in m.get_editor_property("materials")]
    s["skeleton"] = m.get_editor_property("skeleton").get_path_name() if m.get_editor_property("skeleton") else None
    s["physics_asset"] = m.get_editor_property("physics_asset").get_path_name() if m.get_editor_property("physics_asset") else None
    b = m.get_bounds()
    s["bounds_origin"], s["bounds_extent"] = vec(b.origin), vec(b.box_extent)
    s["mesh_sockets"] = [(str(m.get_socket_by_index(i).get_editor_property("socket_name")), str(m.get_socket_by_index(i).get_editor_property("bone_name")),
                          vec(m.get_socket_by_index(i).get_editor_property("relative_location")), [round(float(x), 4) for x in (m.get_socket_by_index(i).get_editor_property("relative_rotation").pitch,
                          m.get_socket_by_index(i).get_editor_property("relative_rotation").yaw, m.get_socket_by_index(i).get_editor_property("relative_rotation").roll)])
                         for i in range(m.num_sockets())]
    sk = m.get_editor_property("skeleton")
    try:
        s["skeleton_sockets"] = [(str(x.get_editor_property("socket_name")), str(x.get_editor_property("bone_name"))) for x in sk.get_editor_property("sockets")]
    except Exception as e:
        s["skeleton_sockets"] = "unreadable: %s" % str(e)[:80]
    try:
        import editor_toolset.toolsets.skeletal_mesh as smt
        t = smt.SkeletalMeshTools()
        s["toolset_socket_names"] = list(t.get_socket_names(m))
        s["toolset_bone_count"] = len(t.get_bone_names(m))
    except Exception as e:
        s["toolset"] = "unavailable: %s" % str(e)[:80]
    aid = m.get_editor_property("asset_import_data")
    s["source_files"] = list(aid.extract_filenames()) if aid else None
    s["lod_build_settings"] = [str(SUB.get_lod_build_settings(m, i).export_text())[:400] for i in range(s["lod_count"])]
    return s


def stable(s):
    """The part that must be IDENTICAL after a reimport (source file names may change)."""
    d = dict(s)
    for k in ("source_files",):
        d.pop(k, None)
    return d


def import_options(m):
    """FbxImportUI that repeats what the owner imported with (read back from the asset's own import data), onto the existing skeleton."""
    aid = m.get_editor_property("asset_import_data")
    o = unreal.FbxImportUI()
    o.automated_import_should_detect_type = False
    o.import_mesh = True
    o.import_as_skeletal = True
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    o.original_import_type = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    o.import_materials = False
    o.import_textures = False
    o.import_animations = False
    o.create_physics_asset = False
    o.skeleton = m.get_editor_property("skeleton")
    d = o.skeletal_mesh_import_data
    for k in ("import_translation", "import_rotation", "import_uniform_scale", "convert_scene", "convert_scene_unit", "force_front_x_axis", "import_mesh_lo_ds",
              "bake_pivot_in_vertex", "normal_import_method", "normal_generation_method", "transform_vertex_to_absolute", "compute_weighted_normals",
              "vertex_color_import_option", "reorder_material_to_fbx_order"):
        try:
            d.set_editor_property(k, aid.get_editor_property(k))
        except Exception as e:
            log("option %s not copied: %s" % (k, str(e)[:80]))
    return o


def method_lodimport(m, lods, rot=False):
    for i in lods:
        fn = os.path.join(ROT, "SK_Warden_LOD%d_rot.fbx" % i) if rot else os.path.join(SRC, "SK_Warden_LOD%d.fbx" % i)
        keep = SUB.get_lod_build_settings(m, i)      # import_lod resets the build settings (bUseMikkTSpace became True on LOD0); put them back
        r = SUB.import_lod(m, i, fn)
        log("import_lod(%d, %s) -> %s" % (i, fn, r))
        m = unreal.load_asset(MESH)
        SUB.set_lod_build_settings(m, i, keep)


def method_task():
    fn = os.path.join(SRC, "SK_Warden_LOD0.fbx")
    m = unreal.load_asset(MESH)
    t = unreal.AssetImportTask()
    t.filename, t.destination_path, t.destination_name = fn, "/Game/LastBell/Characters/Warden/Meshes", "SK_Warden"
    t.replace_existing, t.replace_existing_settings, t.automated, t.save = True, True, True, False
    t.factory, t.options = unreal.FbxFactory(), import_options(m)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    log("import task ->", list(t.get_editor_property("imported_object_paths")))


def dump_weights(path):
    """Skin weights as the engine holds them: GeometryScript copies each LOD's source model into a DynamicMesh (positions in cm, bone weights by bone index).
    Written as JSON for Tools/blender/warden/p13_check_ue_weights.py. (Exporting the mesh to FBX instead crashes under -nullrhi: SkinnedMeshComponent MeshObject assert.)"""
    m = unreal.load_asset(MESH)
    A, BW, MQ = unreal.GeometryScript_AssetUtils, unreal.GeometryScript_BoneWeights, unreal.GeometryScript_MeshQueries
    out = {"lods": []}
    for i in range(SUB.get_lod_count(m)):
        dm = unreal.DynamicMesh()
        opts = unreal.GeometryScriptCopyMeshFromAssetOptions()
        lod = unreal.GeometryScriptMeshReadLOD()
        lod.set_editor_property("lod_type", unreal.GeometryScriptLODType.SOURCE_MODEL)
        lod.set_editor_property("lod_index", i)
        dm, outcome = A.copy_mesh_from_skeletal_mesh(m, dm, opts, lod)
        assert outcome == unreal.GeometryScriptOutcomePins.SUCCESS, (i, outcome)
        dm, bones = BW.get_all_bones_info(dm)
        names = [str(b.get_editor_property("name")) for b in bones]
        n = MQ.get_num_vertex_i_ds(dm)
        n = n[-1] if isinstance(n, tuple) else n
        pos, wts = [], []
        for vid in range(n):
            ok = MQ.is_valid_vertex_id(dm, vid)
            ok = ok[-1] if isinstance(ok, tuple) else ok
            if not ok:
                pos.append(None)
                wts.append(None)
                continue
            p = MQ.get_vertex_position(dm, vid)
            p = next(x for x in (p if isinstance(p, tuple) else (p,)) if hasattr(x, "x") and hasattr(x, "z"))
            r = BW.get_vertex_bone_weights(dm, vid)
            pos.append([round(float(p.x), 3), round(float(p.y), 3), round(float(p.z), 3)])
            wts.append([[int(w.get_editor_property("bone_index")), round(float(w.get_editor_property("weight")), 4)] for w in r[1]])
        out["lods"].append({"lod": i, "vertices": n, "bones": names, "positions": pos, "weights": wts})
        log("dump LOD%d: %d vertices, %d bones" % (i, n, len(names)))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh)


def main():
    m = unreal.load_asset(MESH)
    assert m is not None, "SK_Warden not found"
    before = state(m)
    log("BEFORE", json.dumps(before)[:1500])
    res = {"step": STEP, "before": before}
    if STEP != "state":
        if STEP == "lodimport":
            method_lodimport(m, (0, 1, 2))
        elif STEP == "taskimport":
            method_task()
        elif STEP == "lod0rot":
            method_lodimport(m, (0,), rot=True)
        elif STEP == "reimportlods":
            method_task()
            method_lodimport(unreal.load_asset(MESH), (1, 2), rot=True)
        else:
            raise RuntimeError("unknown step " + STEP)
        m = unreal.load_asset(MESH)
        after = state(m)
        res["after"] = after
        same = stable(before) == stable(after)
        res["unchanged"] = same
        diffs = {k: (before[k], after[k]) for k in stable(before) if before[k] != after.get(k)}
        res["differences"] = diffs
        log("AFTER", json.dumps(after)[:1500])
        log("UNCHANGED" if same else "DIFFERENT: " + json.dumps(diffs)[:2000])
        if DUMP:
            dump_weights(DUMP)
        if SAVE:
            if not same:
                raise RuntimeError("post-state differs from the pre-state; NOT saving")
            ok = unreal.EditorAssetLibrary.save_asset(MESH, only_if_is_dirty=False)
            log("SAVE SK_Warden ->", ok)
            res["saved"] = ok
    if DUMP and STEP == "state":
        dump_weights(DUMP)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)


try:
    main()
    log("OK")
except Exception:
    log("FAILED\n" + traceback.format_exc())
log("P13W_DONE")
