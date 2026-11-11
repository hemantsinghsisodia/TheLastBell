"""p17_villager_prep.py -- P17-5a-2: the courtyard villager from the CC0 Quaternius packs (Modular Character Outfits - Fantasy, Universal Animation Library 1 and 2).

    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --factory-startup --python Tools/blender/villager/p17_villager_prep.py

Writes SourceArt/Villager/{SK_LB_Villager.fbx, AN_LB_Villager_Walk.fbx, AN_LB_Villager_IdleLantern.fbx, villager_prep.json} (nothing else; the sources in
ExternalAssets/Incoming are only read). Textures are made by Tools/blender/villager/p17_villager_textures.py (Pillow).

 * Male_Ranger (glTF) without Male_Ranger_Acc_Pauldron and Male_Ranger_Arms_Bracer, the other 7 meshes joined into one skinned mesh `SK_LB_Villager`
   (slots M_LB_Villager_Cloth = the Ranger texture, M_LB_Villager_Skin = the arms' skin texture).
 * Same recipe as the Warden's rotated LODs (Tools/blender/warden/p13_export_lods_rotated.py): the character faces -Y in Blender; it is turned +90 deg about Z
   (mesh vertices and bones together) so that the default FBX import (x, y) -> (x, -y) leaves it facing +X in Unreal; centimetres (x100, scene unit .01), then the
   exporter settings of SourceArt/Warden/V11_1w/scripts/export.py except use_armature_deform_only (False: this rig's root/pelvis chain must survive).
 * Clips: UAL1 Walk_Loop and UAL2 Idle_Lantern_Loop (the in-place Standard glb), put on the villager's armature (identical 65 bone names), baked at the
   file's 24 fps. Their root bone does not move. The walk's ground speed is measured from the root-motion variant (UAL1_Standard_RM.glb): the root's travel over one
   Walk_Loop divided by its duration.
"""
import json
import math
import os

import bpy
from mathutils import Matrix

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
IN = os.path.join(ROOT, "ExternalAssets", "Incoming", "villager_quaternius_peasant")
OUTFIT = os.path.join(IN, "extracted", "Modular Character Outfits - Fantasy[Standard]", "Exports", "glTF (Godot-Unreal)", "Outfits", "Male_Ranger.gltf")
UAL1 = os.path.join(IN, "extracted_anim", "Universal Animation Library[Standard]", "Unreal-Godot", "UAL1_Standard.glb")
UAL1_RM = os.path.join(IN, "extracted_anim", "Universal Animation Library[Standard]", "Unreal-Godot", "UAL1_Standard_RM.glb")
UAL2 = os.path.join(IN, "extracted_anim", "Universal Animation Library 2[Standard]", "Unreal-Godot", "UAL2_Standard.glb")
OUT = os.path.join(ROOT, "SourceArt", "Villager")
os.makedirs(OUT, exist_ok=True)
META = {}


def log(*a):
    print("VIL| " + " ".join(str(x) for x in a), flush=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def arm_of():
    return [o for o in bpy.data.objects if o.type == "ARMATURE"][0]


def action(name):
    hits = [a for a in bpy.data.actions if a.name == name or a.name.endswith("|" + name)]
    assert len(hits) == 1, (name, [a.name for a in bpy.data.actions][:40])
    return hits[0]


def assign(arm, act):
    arm.animation_data_create()
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception as exc:  # noqa: BLE001
        log("slot:", exc)


# ----------------------------------------------------------------------------------------------- 1. ground speed from the root-motion variant
reset()
bpy.ops.import_scene.gltf(filepath=UAL1_RM)
arm = arm_of()
act = action("Walk_Loop")
assign(arm, act)
sc = bpy.context.scene
f0, f1 = act.frame_range
pos = []
for f in (f0, f1):
    sc.frame_set(int(f))
    sc.frame_set(int(f))
    pos.append((arm.matrix_world @ arm.pose.bones["root"].matrix).translation.copy())
fps = sc.render.fps
dur = (f1 - f0) / fps
travel = (pos[1] - pos[0]).length
META["walk_rm"] = {"frames": [f0, f1], "fps": fps, "seconds": dur, "root_travel_m": round(travel, 4), "native_speed_cm_s": round(travel * 100.0 / dur, 3),
                   "root_start_m": [round(v, 4) for v in pos[0]], "root_end_m": [round(v, 4) for v in pos[1]]}
log("walk RM:", META["walk_rm"])

# ----------------------------------------------------------------------------------------------- 2. the outfit
reset()
bpy.ops.import_scene.gltf(filepath=OUTFIT)
arm = arm_of()
for o in list(bpy.data.objects):
    if o.name in ("Icosphere", "Male_Ranger_Acc_Pauldron", "Male_Ranger_Arms_Bracer"):
        bpy.data.objects.remove(o, do_unlink=True)
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
log("meshes kept:", [m.name for m in meshes])
assert len(meshes) == 7
cloth = bpy.data.materials.new("M_LB_Villager_Cloth")
skin = bpy.data.materials.new("M_LB_Villager_Skin")
for m in meshes:
    for slot in m.material_slots:
        old = slot.material.name if slot.material else ""
        slot.material = skin if old.startswith("MI_Regular_Male") else cloth
bpy.ops.object.select_all(action="DESELECT")
for m in meshes:
    m.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.join()
villager = bpy.context.view_layer.objects.active
villager.name = "SK_LB_Villager"
villager.data.name = "SK_LB_Villager"
arm.name = "Armature"
tris = sum(len(p.vertices) - 2 for p in villager.data.polygons)
META["mesh"] = {"vertices": len(villager.data.vertices), "triangles": tris, "slots": [s.material.name for s in villager.material_slots], "vertex_groups": len(villager.vertex_groups),
                "height_m": round(max(v.co.z for v in villager.data.vertices) - min(v.co.z for v in villager.data.vertices), 4)}
log("mesh:", META["mesh"])
bones = arm.data.bones
META["facing_before_turn"] = {"ball_l_y": round(bones["ball_l"].head_local.y, 4), "foot_l_y": round(bones["foot_l"].head_local.y, 4),
                              "faces": "-Y" if bones["ball_l"].head_local.y < bones["foot_l"].head_local.y else "+Y"}

# ----------------------------------------------------------------------------------------------- 3. the clips, harvested from the UAL packs
for path in (UAL1, UAL2):
    before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.gltf(filepath=path)
    for name in set(bpy.data.objects.keys()) - before:            # the pack's own armature and mannequin are not needed, the actions stay
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
for a in bpy.data.actions:
    a.use_fake_user = True
walk = action("Walk_Loop")
idle = action("Idle_Lantern_Loop")
META["clips"] = {"Walk_Loop": {"frames": list(walk.frame_range), "fps": bpy.context.scene.render.fps},
                 "Idle_Lantern_Loop": {"frames": list(idle.frame_range), "fps": bpy.context.scene.render.fps}}

# ----------------------------------------------------------------------------------------------- 4. +90 deg turn about Z, centimetres
R = Matrix.Rotation(math.radians(90.0), 4, "Z")
for v in villager.data.vertices:
    v.co = (R @ v.co.to_4d()).to_3d() * 100
villager.data.update()
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
for b in arm.data.edit_bones:
    b.transform(R)
    b.head *= 100
    b.tail *= 100
bpy.ops.object.mode_set(mode="OBJECT")
for act in (walk, idle):                                         # translation keys in cm (bone-local, so the turn does not touch them)
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    if fc.data_path.endswith(".location"):
                        for k in fc.keyframe_points:
                            k.co[1] *= 100
                            k.handle_left[1] *= 100
                            k.handle_right[1] *= 100
                        fc.update()
scene = bpy.context.scene
scene.unit_settings.scale_length = 0.01
bpy.context.view_layer.update()
META["bounds_cm"] = {"z_min": round(min(v.co.z for v in villager.data.vertices), 3), "z_max": round(max(v.co.z for v in villager.data.vertices), 3),
                     "x_min": round(min(v.co.x for v in villager.data.vertices), 3), "x_max": round(max(v.co.x for v in villager.data.vertices), 3)}
b = arm.data.bones
META["facing_after_turn"] = {"ball_l_x": round(b["ball_l"].head_local.x, 3), "foot_l_x": round(b["foot_l"].head_local.x, 3),
                             "faces": "+X" if b["ball_l"].head_local.x > b["foot_l"].head_local.x else "other"}
META["bones"] = {"count": len(b), "hand_r": [round(v, 3) for v in b["hand_r"].head_local], "Head": [round(v, 3) for v in b["Head"].head_local]}
log("after turn:", META["facing_after_turn"], META["bounds_cm"])

settings = dict(use_selection=True, global_scale=1, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Y", axis_up="Z",
                bake_space_transform=False, use_mesh_modifiers=True, mesh_smooth_type="FACE", use_tspace=True, add_leaf_bones=False,
                use_armature_deform_only=False, armature_nodetype="NULL", path_mode="RELATIVE", embed_textures=False)
# mesh + armature, no animation (the pose is the rest pose)
arm.animation_data_clear()
for pb in arm.pose.bones:
    pb.location = (0, 0, 0)
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = (1, 0, 0, 0)
    pb.scale = (1, 1, 1)
scene.frame_set(1)
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True)
villager.select_set(True)
bpy.context.view_layer.objects.active = villager
fn = os.path.join(OUT, "SK_LB_Villager.fbx")
bpy.ops.export_scene.fbx(filepath=fn, object_types={"ARMATURE", "MESH"}, bake_anim=False, **settings)
log("wrote", fn, os.path.getsize(fn))

for label, act in (("Walk", walk), ("IdleLantern", idle)):
    assign(arm, act)
    scene.frame_start = int(round(act.frame_range[0]))
    scene.frame_end = int(round(act.frame_range[1]))
    scene.frame_set(scene.frame_start)
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    fn = os.path.join(OUT, "AN_LB_Villager_%s.fbx" % label)
    bpy.ops.export_scene.fbx(filepath=fn, object_types={"ARMATURE"}, bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
                             bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True, bake_anim_step=1, bake_anim_simplify_factor=0, **settings)
    META["clips"]["Walk_Loop" if label == "Walk" else "Idle_Lantern_Loop"]["export"] = {"frame_start": scene.frame_start, "frame_end": scene.frame_end, "file": os.path.basename(fn)}
    log("wrote", fn, os.path.getsize(fn))

with open(os.path.join(OUT, "villager_prep.json"), "w", encoding="utf-8") as fh:
    json.dump(META, fh, indent=1)
log("DONE")
