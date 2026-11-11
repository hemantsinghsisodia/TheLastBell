"""p17_villager_candle.py -- P17 3.9: the villager carries the player's candle. Contact sheet and the numbers for the sequence (read-only; the sources are never changed).

    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --factory-startup --python Tools/blender/villager/p17_villager_candle.py -- [options]
      --walk NAME        UAL action for the walk (default Walk_Loop) or "Walk_Candle" (default): Walk_Loop with the right arm of --idle's frame 0 (villager_clips.py)
      --idle NAME        action for the end idle (default Idle_Lantern_Loop; UAL2)
      --grip F           the grip point = wrist + F * (middle knuckle - wrist)  (default 0.55)
      --scratch DIR      panels and the sheet meta go here (default: a temp dir)
      --final            write Docs/ArtTest/cine/p17_villager_candle.png and p17_villager_candle.json (otherwise only the scratch dir)

The candle is the player's (BP_LBCharacter's `Candle` component, read from the CDO): the wax is the engine cylinder at scale (0.03, 0.03, 0.12) (3 cm wide, 12 cm tall) centred 7 cm below the
component origin, the flame is SM_LB_Prop_CandleFlame_A (0..6.5 cm tall, 3 x 2.9 cm) scaled 0.7 with its base 0.92 cm below the origin (on top of the wax), and the light sits at the origin.
It is held upright in the right hand: the wax's centre is the grip point, and the candle is rigidly attached to `hand_r` with the hand's orientation at the frame where the candle
is closest to vertical over the whole cycle (the walk and the idle each get their own attach offset; Sequencer keys the offset across the blend).
Blender frame: metres, the villager faces -Y, its right hand is on the -X side. Clips are at 24 fps.
"""
import json
import math
import os
import subprocess
import sys
import tempfile

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import villager_clips as VC  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
IN = os.path.join(ROOT, "ExternalAssets", "Incoming", "villager_quaternius_peasant")
OUTFIT = os.path.join(IN, "extracted", "Modular Character Outfits - Fantasy[Standard]", "Exports", "glTF (Godot-Unreal)", "Outfits", "Male_Ranger.gltf")
UAL = {"UAL1": os.path.join(IN, "extracted_anim", "Universal Animation Library[Standard]", "Unreal-Godot", "UAL1_Standard.glb"),
       "UAL2": os.path.join(IN, "extracted_anim", "Universal Animation Library 2[Standard]", "Unreal-Godot", "UAL2_Standard.glb")}
PY = r"C:\Users\heman\AppData\Local\Python\pythoncore-3.14-64\python.exe"
CINE = os.path.join(ROOT, "Docs", "ArtTest", "cine")

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OPT = {}
i_ = 0
while i_ < len(a):
    if a[i_] in ("--final", "--candidates"):
        OPT[a[i_].lstrip("-")] = True
        i_ += 1
    else:
        OPT[a[i_].lstrip("-")] = a[i_ + 1]
        i_ += 2
WALK = OPT.get("walk", "Walk_Candle")
IDLE = OPT.get("idle", "Idle_Lantern_Loop")
GRIP = float(OPT.get("grip", 0.55))
SCRATCH = OPT.get("scratch") or tempfile.mkdtemp(prefix="p17cd_")
os.makedirs(SCRATCH, exist_ok=True)
PANEL = 440

# the player's candle, in the candle component's frame (cm -> m)
WAX_CENTRE_Z, WAX_R, WAX_H = -0.07, 0.015, 0.12
FLAME_BASE_Z, FLAME_SCALE = -0.0092, 0.7
FLAME_H, FLAME_RX, FLAME_RY = 0.065, 0.015, 0.01427


def log(*x):
    print("VCD| " + " ".join(str(v) for v in x), flush=True)


def act(name):
    hits = [a_ for a_ in bpy.data.actions if a_.name == name or a_.name.endswith("|" + name)]
    assert len(hits) == 1, (name, len(hits))
    return hits[0]


def assign(arm, action):
    arm.animation_data_create()
    arm.animation_data.action = action
    try:
        arm.animation_data.action_slot = action.slots[0]
    except Exception:  # noqa: BLE001
        pass


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=OUTFIT)
arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
for o in list(bpy.data.objects):
    if o.name in ("Icosphere", "Male_Ranger_Acc_Pauldron", "Male_Ranger_Arms_Bracer"):
        bpy.data.objects.remove(o, do_unlink=True)
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
cloth = bpy.data.materials.new("Cloth")
cloth.diffuse_color = (0.30, 0.22, 0.15, 1)
skin = bpy.data.materials.new("Skin")
skin.diffuse_color = (0.62, 0.42, 0.32, 1)
for m in meshes:
    for slot in m.material_slots:
        slot.material = skin if (slot.material and slot.material.name.startswith("MI_Regular_Male")) else cloth
bpy.ops.object.select_all(action="DESELECT")
for m in meshes:
    m.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.join()
body = bpy.context.view_layer.objects.active
body.name = "Villager"
for k, path in UAL.items():
    before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.gltf(filepath=path)
    for n in set(bpy.data.objects.keys()) - before:
        bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
for a_ in bpy.data.actions:
    a_.use_fake_user = True
scene = bpy.context.scene
scene.render.fps = 24
PB = arm.pose.bones


def set_frame(action, f):
    assign(arm, action)
    scene.frame_set(int(f))
    scene.frame_set(int(f))
    bpy.context.view_layer.update()


def bone_world(name):
    return arm.matrix_world @ PB[name].matrix


def grip_world():
    h, m = bone_world("hand_r"), bone_world("middle_01_r")
    return h.translation + GRIP * (m.translation - h.translation)


# ---- the candle objects (metres), at the candle origin O
mat_wax = bpy.data.materials.new("Wax")
mat_wax.diffuse_color = (0.90, 0.82, 0.62, 1)
mat_flame = bpy.data.materials.new("Flame")
mat_flame.diffuse_color = (1.0, 0.55, 0.05, 1)
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=WAX_R, radius2=WAX_R, depth=WAX_H)
wax_me = bpy.data.meshes.new("Wax")
bm.to_mesh(wax_me)
bm.free()
wax = bpy.data.objects.new("Wax", wax_me)
wax.data.materials.append(mat_wax)
bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=1.0)
fl_me = bpy.data.meshes.new("Flame")
bm.to_mesh(fl_me)
bm.free()
flame = bpy.data.objects.new("Flame", fl_me)
flame.scale = (FLAME_RX * FLAME_SCALE / 0.7 * 0.7, FLAME_RY * FLAME_SCALE, FLAME_H * FLAME_SCALE / 2)
flame.data.materials.append(mat_flame)
for o in (wax, flame):
    scene.collection.objects.link(o)


def place_candle(O):
    """O: a 4x4 world matrix of the candle component (upright when its rotation is the identity)."""
    wax.matrix_world = O @ Matrix.Translation((0, 0, WAX_CENTRE_Z))
    # the flame mesh: base at FLAME_BASE_Z, height FLAME_H * scale; an ellipsoid centred half-way
    flame.matrix_world = O @ Matrix.Translation((0, 0, FLAME_BASE_Z + FLAME_H * FLAME_SCALE / 2)) @ Matrix.Diagonal((1, 1, 1, 1))
    flame.scale = (FLAME_RX * FLAME_SCALE, FLAME_RY * FLAME_SCALE, FLAME_H * FLAME_SCALE / 2)


# ---- choose the attach offset of one clip: the candle is upright at the frame whose hand orientation is the best compromise over the cycle
def analyse(action):
    f0, f1 = int(action.frame_range[0]), int(action.frame_range[1])
    frames = list(range(f0, f1))
    Rs = []
    for f in frames:
        set_frame(action, f)
        Rs.append(np.array(bone_world("hand_r"))[:3, :3])
    # u = the hand-frame direction that is closest to world up on average (the candle's axis in the hand)
    u = np.mean([R.T @ np.array([0, 0, 1.0]) for R in Rs], axis=0)
    u /= np.linalg.norm(u)
    tilts = [math.degrees(math.acos(max(-1.0, min(1.0, float((R @ u)[2]))))) for R in Rs]
    f_ref = frames[int(np.argmin(tilts))]
    return frames, f_ref, tilts, u


def rel_for(action, f_ref):
    """The candle's world matrix at f_ref (origin so that the wax centre is the grip point, upright), expressed in the hand's frame."""
    set_frame(action, f_ref)
    g = grip_world()
    O = Matrix.Translation(g + Vector((0, 0, -WAX_CENTRE_Z)))        # the wax centre (origin + WAX_CENTRE_Z) is the grip point
    H = bone_world("hand_r")
    return H.inverted() @ O


results = {"grip_fraction": GRIP}
clips = {}
if WALK == "Walk_Candle":
    VC.build_hybrid(arm, scene, act("Walk_Loop"), act(IDLE), 0, "Walk_Candle")
SHARED = None
for label, name in (("idle", IDLE), ("walk", WALK)):       # the idle first: its arm pose is the one the walk holds, so one offset serves both
    action = act(name)
    frames, f_ref, tilts, u = analyse(action)
    if SHARED is None:
        SHARED = rel_for(action, f_ref)
    REL = SHARED
    # tilt of the candle's up axis over the cycle with this REL
    tl = []
    for f in frames:
        set_frame(action, f)
        up = (bone_world("hand_r") @ REL).to_3x3() @ Vector((0, 0, 1))
        tl.append(math.degrees(math.acos(max(-1.0, min(1.0, up.z)))))
    clips[label] = dict(action=action, name=name, frames=frames, f_ref=f_ref, REL=REL)
    results[label] = {"action": name, "frames": len(frames), "seconds": round(len(frames) / 24.0, 3), "reference_frame": f_ref, "tilt_deg_max": round(max(tl), 2), "tilt_deg_mean": round(sum(tl) / len(tl), 2),
                      "rel_in_hand_bone_frame": {"location_cm": [round(v * 100, 3) for v in REL.translation], "rotation_euler_deg": [round(math.degrees(v), 2) for v in REL.to_euler()]},
                      "up_axis_in_hand_frame": [round(float(v), 4) for v in u]}
    log(label, results[label])


# ---- clearance: the candle against the body, excluding the right hand and fingers (they hold it)
def clearance(label, frames):
    from mathutils.bvhtree import BVHTree
    hand_groups = {g.index for g in body.vertex_groups if g.name.endswith("_r") and any(k in g.name for k in ("hand", "index", "middle", "ring", "pinky", "thumb"))}
    out = {}
    worst = 9.0
    for f in frames[:: max(1, len(frames) // 8)]:
        set_frame(clips[label]["action"], f)
        place_candle(bone_world("hand_r") @ clips[label]["REL"])
        dg = bpy.context.evaluated_depsgraph_get()
        ev = body.evaluated_get(dg)
        me = ev.to_mesh()
        verts = [v.co.copy() for v in me.vertices]
        skip = {v.index for v in body.data.vertices if any(g.group in hand_groups and g.weight > 0.3 for g in v.groups)}
        tris = []
        for p in me.polygons:
            pv = list(p.vertices)
            if any(v in skip for v in pv):
                continue
            for k in range(1, len(pv) - 1):
                tris.append((pv[0], pv[k], pv[k + 1]))
        tree = BVHTree.FromPolygons(verts, tris, epsilon=0.0)
        md = 9.0
        for o in (wax, flame):
            for v in o.data.vertices:
                hit = tree.find_nearest(o.matrix_world @ v.co)
                if hit[0] is not None:
                    md = min(md, hit[3])
        worst = min(worst, md)
        ev.to_mesh_clear()
    return round(worst * 100, 2)


for label in ("walk", "idle"):
    results[label]["min_distance_to_body_cm"] = clearance(label, clips[label]["frames"])
    log(label, "min distance candle -> body (hands excluded) cm:", results[label]["min_distance_to_body_cm"])

# ---- the panels
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = scene.render.resolution_y = PANEL
scene.render.film_transparent = False
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_cavity = False
scene.world = bpy.data.worlds.new("W")
scene.world.color = (0.05, 0.05, 0.06)
cam_d = bpy.data.cameras.new("Cam")
cam_d.type = "ORTHO"
cam = bpy.data.objects.new("Cam", cam_d)
scene.collection.objects.link(cam)
scene.camera = cam


def shoot(path, loc, tgt, ortho):
    cam_d.ortho_scale = ortho
    cam.location = loc
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


walk_frames = clips["walk"]["frames"]
n = len(walk_frames)
picks = [("walk 0%", walk_frames[0], "walk"), ("walk 25%", walk_frames[n // 4], "walk"), ("walk 50%", walk_frames[n // 2], "walk"), ("walk 75%", walk_frames[(3 * n) // 4], "walk"),
         ("end idle", clips["idle"]["frames"][0], "idle")]
panels = []
for label, f, kind in picks:
    set_frame(clips[kind]["action"], f)
    place_candle(bone_world("hand_r") @ clips[kind]["REL"])
    c = (bone_world("hand_r") @ clips[kind]["REL"]).translation
    rows = (("front", Vector((0, -8, 0.95)), Vector((0, 0, 0.95)), 2.2), ("side", Vector((-8, 0, 0.95)), Vector((0, 0, 0.95)), 2.2),
            ("hand front", c + Vector((0, -3, 0.02)), c + Vector((0, 0, 0.02)), 0.5), ("hand side", c + Vector((-3, 0, 0.02)), c + Vector((0, 0, 0.02)), 0.5))
    for view, loc, tgt, ortho in rows:
        fp = os.path.join(SCRATCH, "%s_%s.png" % (label.replace(" ", "_").replace("%", "p"), view.replace(" ", "_")))
        shoot(fp, loc, tgt, ortho)
        panels.append(dict(label=label, frame=int(f), view=view, path=fp, action=clips[kind]["name"]))
meta = dict(panels=panels, panel=PANEL, out=os.path.join(CINE, "p17_villager_candle.png") if OPT.get("final") else os.path.join(SCRATCH, "sheet.png"),
            title="Villager with the player's candle: %s (4 frames) and %s (end idle). Rows: front, side, right hand front, right hand side. Candle 3 x 12 cm, flame 4.6 cm." % (WALK, IDLE))
mp = os.path.join(SCRATCH, "sheet_meta.json")
json.dump(meta, open(mp, "w"))
r = subprocess.run([PY, "-I", os.path.join(ROOT, "Tools", "blender", "villager", "p17_villager_candle_compose.py"), mp], capture_output=True, text=True)
log("compose", r.returncode, r.stdout.strip()[:200], r.stderr.strip()[:400])
results["candle"] = {"wax": {"mesh": "/Engine/BasicShapes/Cylinder", "scale": [0.03, 0.03, 0.12], "centre_z_cm": -7.0, "material": "MI_LB_CandleWax"},
                     "flame": {"mesh": "SM_LB_Prop_CandleFlame_A", "scale": 0.7, "origin_z_cm": -0.92, "material": "MI_Flame_Candle_Player"}, "light_origin_cm": [0, 0, 0]}
results["sheet"] = meta["out"]
if OPT.get("final"):
    json.dump(results, open(os.path.join(CINE, "p17_villager_candle.json"), "w"), indent=1)
log("DONE", meta["out"])
