"""reimport_skeletal.py -- the safe "re-import over the same name" for a SKELETAL mesh through the MCP tools (P12-1).

`SkeletalMeshTools.import_file` REFUSES an existing asset ("already exists"), and there is no reimport tool, so the
mesh is replaced by: record -> delete the mesh -> import at the same path with the EXISTING skeleton -> restore.
The skeleton, the physics asset and the animations are separate assets and are not touched. What the delete loses
(and this script restores): the physics-asset assignment, the mesh-owned sockets (with their local transforms) and the
material-slot assignments. What it ALSO loses and the CALLER must restore: every reference to the mesh in other
assets/actors (a Blueprint's skeletalMeshAsset, a placed SkeletalMeshActor) -- AssetTools.delete nulls them.

    python Tools/warden/reimport_skeletal.py <mesh_path> <fbx> <skeleton_path> [--dry]
      mesh_path / skeleton_path: e.g. Game/LastBell/ArtTest/P12/SK_P12_Spike  (no leading slash needed; Git Bash
      rewrites a leading /Game); fbx: a Windows path.

Save afterwards, ONE package per save_assets call: the mesh, then (if their references changed) the others.
Never run it on a mesh that a saved, protected Blueprint references until you have a plan to re-point that Blueprint.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mcp"))
from ue import UE  # noqa: E402

SK = "editor_toolset.toolsets.skeletal_mesh.SkeletalMeshTools"
AS = "editor_toolset.toolsets.asset.AssetTools"


def norm(p):
    p = p.replace("\\", "/")
    return p if p.startswith("/") else "/" + p


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    mesh_path, fbx, skel_path = norm(args[0]), args[1], norm(args[2])
    folder, name = mesh_path.rsplit("/", 1)
    ue = UE()
    mesh = {"refPath": "%s.%s" % (mesh_path, name)}
    skel = {"refPath": "%s.%s" % (skel_path, skel_path.rsplit("/", 1)[1])}

    # 1. record
    slots = ue.call(SK, "get_material_slots", {"mesh": mesh})
    mats = {}
    for s in slots:
        try:
            mats[s] = ue.call(SK, "get_material", {"mesh": mesh, "slot_name": s})["refPath"]
        except Exception:
            pass
    sockets = {}
    for s in ue.call(SK, "get_socket_names", {"mesh": mesh}):
        sockets[s] = {"bone": ue.call(SK, "get_socket_bone", {"mesh": mesh, "socket_name": s}),
                      "tf": ue.call(SK, "get_socket_transform", {"mesh": mesh, "socket_name": s})}
    try:
        pa = ue.call(SK, "get_physics_asset", {"mesh": mesh})
    except Exception:
        pa = None
    print("recorded: slots", slots, "materials", mats, "sockets", list(sockets), "physics asset", pa)
    if dry:
        return 0

    # 2. delete + import at the same path with the existing skeleton (animations / physics asset NOT re-created)
    assert ue.call(AS, "delete", {"path": mesh_path}) is True, "delete failed"
    r = ue.call(SK, "import_file", {"folder_path": folder, "asset_name": name, "source_file": fbx, "skeleton": skel,
                                    "import_materials": False, "import_textures": False,
                                    "import_animations": False, "create_physics_asset": False})
    print("imported:", r)
    got = ue.call(SK, "get_skeleton", {"mesh": mesh})
    assert got["refPath"] == skel["refPath"], "mesh is on a different skeleton: %s" % got

    # 3. restore
    new_slots = ue.call(SK, "get_material_slots", {"mesh": mesh})
    if pa:
        ue.call(SK, "assign_physics_asset", {"mesh": mesh, "physics_asset": pa})
    for s, d in sockets.items():
        ue.call(SK, "add_socket", {"mesh": mesh, "socket_name": s, "bone_name": d["bone"]})
        ue.call(SK, "set_socket_transform", {"mesh": mesh, "socket_name": s, "transform": d["tf"]})
    for s, m in mats.items():
        if s in new_slots:
            ue.call(SK, "set_material", {"mesh": mesh, "slot_name": s, "material": {"refPath": m}})
        else:
            print("WARNING: slot %s no longer exists in the new mesh (was %s)" % (s, m))
    for s in new_slots:
        if s not in slots:
            print("NOTE: new slot", s, "has no material yet")
    print("restored: slots", new_slots, "sockets", ue.call(SK, "get_socket_names", {"mesh": mesh}),
          "physics asset", ue.call(SK, "get_physics_asset", {"mesh": mesh}),
          "bounds", ue.call(SK, "get_bounds", {"mesh": mesh}))
    print("NOW: re-point every reference to the mesh (Blueprints, placed actors), then save the mesh (one package per call).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
