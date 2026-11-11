"""w3_state.py -- P17 W3 read-only state of the Warden assets (headless, Unreal editor CLOSED, nothing is saved).

    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=Tools/warden/w3_state.py -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>
Environment: W3_OUT (JSON path, default Saved/w3_state.json). Last line printed: W3_DONE.
Reads SK_Warden (LODs, vertices, slots, sockets, skeleton, bones + reference pose), the three clips, the project MI_Warden_* values and which V11.1 assets exist.
"""
import json
import os
import traceback

import unreal

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
OUT = os.environ.get("W3_OUT", os.path.join(ROOT, "Saved", "w3_state.json"))
MESH = "/Game/LastBell/Characters/Warden/Meshes/SK_Warden"
ANIMS = "/Game/LastBell/Characters/Warden/Anims/"
MATS = "/Game/LastBell/Characters/Warden/Materials/"
V11 = "/Game/WardenArtV11_1/"
SUB = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)


def log(*a):
    print("W3| " + " ".join(str(x) for x in a))


def r4(v):
    return [round(float(x), 4) for x in v]


def mesh_state(m):
    s = {"lod_count": SUB.get_lod_count(m)}
    s["lod_vertices"] = [SUB.get_num_verts(m, i) for i in range(s["lod_count"])]
    s["lod_sections"] = [SUB.get_num_sections(m, i) for i in range(s["lod_count"])]
    s["slots"] = [{"slot": str(x.get_editor_property("material_slot_name")), "imported": str(x.get_editor_property("imported_material_slot_name")),
                   "material": (x.get_editor_property("material_interface").get_path_name() if x.get_editor_property("material_interface") else None)} for x in m.get_editor_property("materials")]
    s["skeleton"] = m.get_editor_property("skeleton").get_path_name()
    s["physics_asset"] = m.get_editor_property("physics_asset").get_path_name() if m.get_editor_property("physics_asset") else None
    b = m.get_bounds()
    s["bounds_origin"], s["bounds_extent"] = r4([b.origin.x, b.origin.y, b.origin.z]), r4([b.box_extent.x, b.box_extent.y, b.box_extent.z])
    s["mesh_sockets"] = [(str(m.get_socket_by_index(i).get_editor_property("socket_name")), str(m.get_socket_by_index(i).get_editor_property("bone_name")),
                          r4([m.get_socket_by_index(i).get_editor_property("relative_location").x, m.get_socket_by_index(i).get_editor_property("relative_location").y, m.get_socket_by_index(i).get_editor_property("relative_location").z]))
                         for i in range(m.num_sockets())]
    try:
        import editor_toolset.toolsets.skeletal_mesh as smt
        t = smt.SkeletalMeshTools()
        names = list(t.get_bone_names(m))
        s["bone_count"] = len(names)
        s["bone_names"] = names
        s["toolset_methods"] = sorted(x for x in dir(t) if not x.startswith("_"))
    except Exception as e:
        s["toolset"] = "unavailable: " + str(e)[:200]
    return s


def ref_pose(m):
    """Bone reference pose (component space) of the mesh, through the mesh's reference skeleton if the API exposes it."""
    out = {}
    try:
        sk = m.get_editor_property("skeleton")
        for n in ("get_reference_pose", "get_bone_pose", "get_ref_pose"):
            out["has_" + n] = hasattr(sk, n) or hasattr(m, n)
    except Exception as e:
        out["err"] = str(e)[:120]
    return out


def clip_state(path):
    a = unreal.load_asset(path)
    if a is None:
        return None
    d = {"class": a.get_class().get_name()}
    try:
        d["length"] = round(float(a.get_editor_property("sequence_length")), 4)
    except Exception:
        d["length"] = "n/a"
    for k in ("rate_scale", "enable_root_motion", "root_motion_root_lock", "force_root_lock", "loop"):
        try:
            d[k] = str(a.get_editor_property(k))
        except Exception:
            pass
    for fn in ("get_number_of_sampled_keys", "get_number_of_sampled_frames", "get_frame_rate", "get_play_length"):
        try:
            v = getattr(unreal.AnimationLibrary, fn)(a) if hasattr(unreal.AnimationLibrary, fn) else getattr(a, fn)()
            d[fn] = str(v)
        except Exception as e:
            d[fn] = "n/a"
    try:
        d["notifies"] = len(unreal.AnimationLibrary.get_animation_notify_events(a))
    except Exception:
        d["notifies"] = "n/a"
    try:
        d["curves"] = [str(x) for x in unreal.AnimationLibrary.get_animation_curve_names(a, unreal.RawCurveTrackTypes.RCT_FLOAT)]
    except Exception:
        d["curves"] = "n/a"
    try:
        aid = a.get_editor_property("asset_import_data")
        d["source_files"] = list(aid.extract_filenames())
    except Exception:
        pass
    d["skeleton"] = a.get_editor_property("skeleton").get_path_name()
    return d


def mi_state(path):
    a = unreal.load_asset(path)
    if a is None:
        return None
    d = {"class": a.get_class().get_name()}
    if isinstance(a, unreal.MaterialInstance):
        d["parent"] = a.get_editor_property("parent").get_path_name() if a.get_editor_property("parent") else None
        d["scalars"] = {str(p.get_editor_property("parameter_info").get_editor_property("name")): round(float(p.get_editor_property("parameter_value")), 5) for p in a.get_editor_property("scalar_parameter_values")}
        d["vectors"] = {str(p.get_editor_property("parameter_info").get_editor_property("name")): [round(float(p.get_editor_property("parameter_value").get_editor_property(c)), 5) for c in ("r", "g", "b", "a")] for p in a.get_editor_property("vector_parameter_values")}
        d["textures"] = {str(p.get_editor_property("parameter_info").get_editor_property("name")): (p.get_editor_property("parameter_value").get_path_name() if p.get_editor_property("parameter_value") else None) for p in a.get_editor_property("texture_parameter_values")}
    else:
        d["blend_mode"] = str(a.get_editor_property("blend_mode"))
        d["two_sided"] = bool(a.get_editor_property("two_sided"))
        try:
            d["scalar_params"] = [str(n) for n in unreal.MaterialEditingLibrary.get_scalar_parameter_names(a)]
            d["vector_params"] = [str(n) for n in unreal.MaterialEditingLibrary.get_vector_parameter_names(a)]
        except Exception:
            pass
        try:
            d["num_expressions"] = unreal.MaterialEditingLibrary.get_num_material_expressions(a)
        except Exception:
            pass
    return d


def main():
    res = {}
    m = unreal.load_asset(MESH)
    res["mesh"] = mesh_state(m)
    res["ref_pose_api"] = ref_pose(m)
    res["clips"] = {n: clip_state(ANIMS + n + "." + n) for n in ("AN_Warden_Idle", "AN_Warden_Walk", "AN_Warden_DoorwayStoop")}
    res["project_materials"] = {}
    for n in ("MI_Warden_Wool", "MI_Warden_BellMetal", "MI_Warden_RustedIron", "MI_Warden_Skin", "MI_Warden_ChainIron", "M_Warden_Leather", "M_Warden_Wool", "M_Warden_BellMetal", "M_Warden_RustedIron", "M_Warden_Skin", "M_Warden_ChainIron"):
        res["project_materials"][n] = mi_state(MATS + n + "." + n)
    res["v11_1_assets_exist"] = {n: unreal.EditorAssetLibrary.does_asset_exist(V11 + n) for n in ("Materials/MI_Warden_Wool", "Materials/M_Warden_BellMetal", "Materials/M_Warden_DimEyes", "Textures/T_Warden_Wool_BaseColor")}
    res["v11_1_materials"] = {}
    for n in ("MI_Warden_Wool", "M_Warden_Wool", "M_Warden_BellMetal", "M_Warden_RustedIron", "M_Warden_ChainIron", "M_Warden_Skin", "M_Warden_Leather", "M_Warden_DimEyes", "M_Warden_Keratin"):
        if unreal.EditorAssetLibrary.does_asset_exist(V11 + "Materials/" + n):
            res["v11_1_materials"][n] = mi_state(V11 + "Materials/" + n + "." + n)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)
    log("wrote", OUT)


try:
    main()
    log("OK")
except Exception:
    log("FAILED\n" + traceback.format_exc())
log("W3_DONE")
