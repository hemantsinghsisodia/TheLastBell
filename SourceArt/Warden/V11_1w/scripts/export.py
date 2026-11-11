"""Export a temporary centimetre-coordinate copy; leave the metre-based blend intact."""
import bpy, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Warden_Rigged.blend'))
scene=bpy.context.scene; arm=bpy.data.objects['Warden_Rig']
arm.animation_data.action=None
for pb in arm.pose.bones:
    pb.location=(0,0,0); pb.rotation_euler=(0,0,0); pb.rotation_quaternion=(1,0,0,0); pb.scale=(1,1,1)
scene.frame_set(1)
only_clip=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--clip=')),None)
for i in range(3):
    obj=bpy.data.objects[f'SK_Warden_LOD{i}']
    for vertex in obj.data.vertices: vertex.co*=100
    obj.data.update()
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); bpy.context.view_layer.objects.active=arm
bpy.ops.object.mode_set(mode='EDIT')
for bone in arm.data.edit_bones: bone.head*=100; bone.tail*=100
bpy.ops.object.mode_set(mode='OBJECT')
for action in bpy.data.actions:
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    if curve.data_path.endswith('.location'):
                        for key in curve.keyframe_points:
                            key.co[1]*=100; key.handle_left[1]*=100; key.handle_right[1]*=100
                        curve.update()
scene.unit_settings.scale_length=.01
scene.frame_set(1); bpy.context.view_layer.update()
arm.name='Armature'
settings=dict(use_selection=True,global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
              axis_forward='-Y',axis_up='Z',bake_space_transform=False,use_mesh_modifiers=True,
              mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,use_armature_deform_only=True,
              armature_nodetype='NULL',path_mode='RELATIVE',embed_textures=False)
for i in ([] if only_clip else range(3)):
    bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True)
    obj=bpy.data.objects[f'SK_Warden_LOD{i}']; obj.hide_set(False); obj.select_set(True); bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(ROOT/f'exports/SK_Warden_LOD{i}.fbx'),object_types={'ARMATURE','MESH'},bake_anim=False,**settings)
for label in ([only_clip] if only_clip else ['Idle','Walk','DoorwayStoop']):
    action=bpy.data.actions['Warden_'+label]; arm.animation_data.action=action
    # Animation-only FBX import omits Force Front X conversion in this engine.
    from mathutils import Quaternion,Vector
    import math
    root=arm.pose.bones['root']
    root.rotation_mode='QUATERNION'
    for f in range(int(action.frame_range[0]),int(action.frame_range[1])+1):
        scene.frame_set(f)
        axis=root.bone.matrix_local.to_3x3().inverted()@Vector((0,0,1))
        root.rotation_quaternion=Quaternion(axis,math.pi/2)
        root.keyframe_insert(data_path='rotation_quaternion',frame=f)

    scene.frame_start=int(action.frame_range[0]); scene.frame_end=int(action.frame_range[1]); scene.frame_set(scene.frame_start)
    bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); bpy.context.view_layer.objects.active=arm
    bpy.ops.export_scene.fbx(filepath=str(ROOT/f'exports/AN_Warden_{label}.fbx'),object_types={'ARMATURE'},bake_anim=True,
                            bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,
                            bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0,**settings)
