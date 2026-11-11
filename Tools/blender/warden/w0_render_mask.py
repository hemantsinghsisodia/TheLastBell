"""w0_render_mask.py -- P17 F0b: two neutral-lit head renders of Warden V11.1 LOD0 (Idle frame 1), the BellMetal mask on and with its faces removed.

    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --factory-startup <blend> --python Tools/blender/warden/w0_render_mask.py -- --out <dir> [--prefix p17_f0b] [--exposure 0]

Same camera, lights and grey background as the owner's scripts/closeups.py ("mask" view). Faces are removed in memory only; the blend is never saved.
Extra views (--extra 1): a lower three-quarter camera for the mask-off look.
"""
import os
import sys

import bmesh
import bpy
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = {a[i].lstrip("-"): a[i + 1] for i in range(0, len(a) - 1, 2)}
OUT = opt["out"]
PREFIX = opt.get("prefix", "p17_f0b")
EXPO = float(opt.get("exposure", "0"))
EXTRA = opt.get("extra", "0") == "1"
SAMPLES = int(opt.get("samples", "48"))
os.makedirs(OUT, exist_ok=True)


def aim(ob, target):
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat("-Z", "Y").to_euler()


scene = bpy.context.scene
for ob in list(scene.objects):
    if ob.type in ("LIGHT", "CAMERA"):
        bpy.data.objects.remove(ob, do_unlink=True)
    elif ob.type == "MESH":
        ob.hide_render = ob.name != "SK_Warden_LOD0"       # the file also carries LOD0.001..005 leftovers
rig = bpy.data.objects["Warden_Rig"]
rig.animation_data.action = bpy.data.actions["Warden_Idle"]
scene.frame_set(1)

scene.render.engine = "CYCLES"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.cycles.device = "CPU"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "CUDA"
    prefs.get_devices()
    gpu = [d for d in prefs.devices if d.type == "CUDA"]
    for d in prefs.devices:
        d.use = d.type == "CUDA"
    if gpu:
        scene.cycles.device = "GPU"
except Exception as e:
    print("W0RENDER| GPU not used:", e)
print("W0RENDER| device", scene.cycles.device)
scene.render.resolution_x, scene.render.resolution_y = 800, 960
scene.render.resolution_percentage = 100
scene.view_settings.exposure = EXPO
scene.world.node_tree.nodes["Background"].inputs[0].default_value = (.12, .12, .12, 1)
for pos, energy in [((-3, -4, 4), 650), ((3, -2, 2), 300), ((0, 3, 4), 450)]:
    bpy.ops.object.light_add(type="AREA", location=pos)
    ob = bpy.context.object
    ob.data.energy = energy
    ob.data.size = 3
    aim(ob, (0, 0, 1.5))
bpy.ops.object.camera_add()
cam = bpy.context.object
cam.data.type = "ORTHO"
scene.camera = cam


def shot(name, loc, centre, size):
    cam.location = loc
    cam.data.ortho_scale = size
    aim(cam, centre)
    scene.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print("W0RENDER| wrote", scene.render.filepath)


MASK_VIEW = ((.35, -2, 2.6), (0, -.5, 2.50), .70)
shot("%s_mask_on.png" % PREFIX, *MASK_VIEW)
if EXTRA:
    shot("%s_mask_on_low34.png" % PREFIX, (-.9, -1.9, 2.1), (0, -.45, 2.5), .70)

# remove the mask faces (BellMetal slot) in memory
o = bpy.data.objects["SK_Warden_LOD0"]
mi = next(i for i, s in enumerate(o.material_slots) if "BellMetal" in s.name)
bm = bmesh.new()
bm.from_mesh(o.data)
faces = [f for f in bm.faces if f.material_index == mi]
print("W0RENDER| removing", len(faces), "mask faces")
bmesh.ops.delete(bm, geom=faces, context="FACES")
bm.to_mesh(o.data)
bm.free()
o.data.update()
shot("%s_mask_off.png" % PREFIX, *MASK_VIEW)
if EXTRA:
    shot("%s_mask_off_low34.png" % PREFIX, (-.9, -1.9, 2.1), (0, -.45, 2.5), .70)
