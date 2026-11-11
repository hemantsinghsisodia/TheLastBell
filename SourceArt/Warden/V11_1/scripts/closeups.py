import bpy
from pathlib import Path
import sys
from mathutils import Vector

R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R.parent/'warden_art_v5_1/scripts'))
from cloth_common import configure_render

def aim(ob,target):
    ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()

bpy.ops.wm.open_mainfile(filepath=str(R/'Warden_Rigged.blend'))
scene=bpy.context.scene
for ob in list(scene.objects):
    if ob.type in ('LIGHT','CAMERA'):
        bpy.data.objects.remove(ob,do_unlink=True)
    elif ob.name.startswith('SK_Warden_LOD'):
        ob.hide_render=ob.name!='SK_Warden_LOD0'
rig=bpy.data.objects['Warden_Rig']
rig.animation_data.action=bpy.data.actions['Warden_Idle']
scene.frame_set(1)
configure_render(scene,24)
scene.render.resolution_x, scene.render.resolution_y=800,960
scene.render.resolution_percentage=100
scene.view_settings.exposure=0
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.12,.12,1)
for pos,energy in [((-3,-4,4),650),((3,-2,2),300),((0,3,4),450)]:
    bpy.ops.object.light_add(type='AREA',location=pos)
    ob=bpy.context.object
    ob.data.energy=energy
    ob.data.size=3
    aim(ob,(0,0,1.5))
bpy.ops.object.camera_add()
cam=bpy.context.object
cam.data.type='ORTHO'
scene.camera=cam
for key,loc,center,size in [
    ('hand',(.9,-1.5,1.2),(.47,-.16,1.12),.70),
    ('opposite-hand',(-.95,-1.55,1.22),(-.47,-.16,1.12),.70),
    ('forearm',(.95,-1.65,1.55),(.48,-.14,1.48),.95),
    ('mask',(.35,-2,2.6),(0,-.5,2.50),.70),
    ('robe',(-.75,-3.8,2),(0,-.09,1.83),1.18),
]:
    if "--context" in sys.argv and key not in ("mask","robe"):
        continue
    cam.location=loc
    cam.data.ortho_scale=size
    aim(cam,center)
    scene.render.filepath=str(R/'previews'/f'v11_1-neutral-{key}.png')
    bpy.ops.render.render(write_still=True)
