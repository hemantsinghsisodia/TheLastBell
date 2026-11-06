"""p13_export_lods_rotated.py -- P13-4c re-import helper: the 3 LOD FBX of SourceArt/Warden/V5_5w2/Warden_Rigged.blend, turned +90 deg about Z in the Blender frame.

    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --factory-startup --python Tools/blender/warden/p13_export_lods_rotated.py -- [--blend FILE] [--out DIR]

Why: SK_Warden was imported by the owner with "Force Front X Axis" (FBX import data: force_front_x_axis True). SkeletalMeshEditorSubsystem.import_lod
(Python) ignores that option, so a LOD imported with it comes in turned 90 deg: measured, bounds origin (-7.5, -15.5) -> (15.5, -7.5) after
import_lod of the unrotated LOD0. Force Front X is "default import, then yaw -90 in the Unreal frame", which is a +90 deg turn about Z in the
Blender frame: (x, y) -> (-y, x) before the default (x, y) -> (x, -y). This script applies that turn to the mesh vertices and the bones (head, tail and
roll) and then runs the owner's export (scripts/export.py: centimetres, FBX_SCALE_UNITS, -Y forward, tspace, no leaf bones) unchanged.
Never saves the blend. Default out: SourceArt/Warden/V5_5w2/ue_lod (files SK_Warden_LOD0/1/2_rot.fbx).
"""
import math
import os
import sys

import bpy
from mathutils import Matrix

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = {a[i].lstrip("-"): a[i + 1] for i in range(0, len(a) - 1, 2)}
BLEND = opt.get("blend", os.path.join(ROOT, "SourceArt", "Warden", "V5_5w2", "Warden_Rigged.blend"))
OUT = opt.get("out", os.path.join(ROOT, "SourceArt", "Warden", "V5_5w2", "ue_lod"))
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene
arm = bpy.data.objects["Warden_Rig"]
if arm.animation_data:
    arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.location = (0, 0, 0)
    pb.rotation_euler = (0, 0, 0)
    pb.rotation_quaternion = (1, 0, 0, 0)
    pb.scale = (1, 1, 1)
scene.frame_set(1)
R = Matrix.Rotation(math.radians(90.0), 4, "Z")
for i in range(3):
    obj = bpy.data.objects["SK_Warden_LOD%d" % i]
    for v in obj.data.vertices:
        v.co = (R @ v.co.to_4d()).to_3d() * 100
    obj.data.update()
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
for bone in arm.data.edit_bones:
    bone.transform(R)       # head, tail and roll
    bone.head *= 100
    bone.tail *= 100
bpy.ops.object.mode_set(mode="OBJECT")
scene.unit_settings.scale_length = .01
scene.frame_set(1)
bpy.context.view_layer.update()
arm.name = "Armature"
settings = dict(use_selection=True, global_scale=1, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Y", axis_up="Z",
                bake_space_transform=False, use_mesh_modifiers=True, mesh_smooth_type="FACE", use_tspace=True, add_leaf_bones=False,
                use_armature_deform_only=True, armature_nodetype="NULL", path_mode="RELATIVE", embed_textures=False)
for i in range(3):
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    obj = bpy.data.objects["SK_Warden_LOD%d" % i]
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    fn = os.path.join(OUT, "SK_Warden_LOD%d_rot.fbx" % i)
    bpy.ops.export_scene.fbx(filepath=fn, object_types={"ARMATURE", "MESH"}, bake_anim=False, **settings)
    print("ROTEXPORT| wrote", fn, os.path.getsize(fn))
