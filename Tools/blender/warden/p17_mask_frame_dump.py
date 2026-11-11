"""p17_mask_frame_dump.py -- P17-5a-2: ground truth for the mask's attach frame (read only; writes one JSON).

    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --factory-startup --python Tools/blender/warden/p17_mask_frame_dump.py -- [--out FILE]

Opens SourceArt/Warden/P17/Warden_MaskLift.blend (never saved), puts the armature in its REST pose and writes, in centimetres in the armature's world frame:
  * `verts`      the slot-1 (M_Warden_BellMetal) vertices of SK_Warden_LOD0 (the skinned mask), `local` the same points in the head bone's rest-local frame (what
                 SM_LB_WardenMask.fbx holds), `bones` the world head positions of a few bones.
Tools/cine/p17_5a2_assets.py then compares them with Unreal: the Warden turns +90 deg about Z for the rotated-LOD import, so Unreal's component space is
(x, y, z)_ue = (-y, -x, z) of this frame (checked on the bone positions). Default out: Saved/p17_mask_frame.json.
"""
import json
import os
import sys

import bpy
import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = a[a.index("--out") + 1] if "--out" in a else os.path.join(ROOT, "Saved", "p17_mask_frame.json")
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "SourceArt", "Warden", "P17", "Warden_MaskLift.blend"))
print("OBJECTS", [(o.name, o.type) for o in bpy.data.objects][:12])
arm = bpy.data.objects["Warden_Rig"]
arm.data.pose_position = "REST"
if arm.animation_data:
    arm.animation_data.action = None
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()
obj = bpy.data.objects["SK_Warden_LOD0"]
dg = bpy.context.evaluated_depsgraph_get()
ev = obj.evaluated_get(dg)
mesh = ev.to_mesh()
slot1 = {p.vertices[i] for p in mesh.polygons if p.material_index == 1 for i in range(len(p.vertices))}
idx = sorted(slot1)
mw = np.array(obj.matrix_world)
co = np.array([mw @ np.append(np.array(mesh.vertices[i].co), 1.0) for i in idx])[:, :3] * 100.0
bone = arm.pose.bones["head"]
H = np.array(arm.matrix_world @ bone.matrix)          # head bone rest matrix in world (metres)
Hinv = np.linalg.inv(H)
loc = (Hinv @ np.c_[co / 100.0, np.ones(len(co))].T).T[:, :3] * 100.0
bones = {}
for n in ("head", "neck_01", "hand_r", "hand_l", "pelvis", "foot_l", "ball_l"):
    pb = arm.pose.bones[n]
    bones[n] = [float(v) * 100.0 for v in (arm.matrix_world @ pb.head)]
json.dump({"count": len(idx), "world_cm": co.round(5).tolist(), "head_local_cm": loc.round(5).tolist(), "bones_world_cm": bones, "head_matrix_world_m": H.round(7).tolist()},
          open(OUT, "w"))
print("MASKDUMP| %d slot-1 vertices; head local bounds %s .. %s; bones %s" % (len(idx), loc.min(axis=0).round(2).tolist(), loc.max(axis=0).round(2).tolist(), bones))
