"""villager_clips.py -- shared by p17_villager_prep.py and p17_villager_candle.py (run inside Blender): the hybrid clip `Walk_Candle`.

P17 3.9: no UAL clip is a one-hand walk that shows a candle held out in front (Walk_Carry_Loop is a two-handed tray carry with open palms). So the walk is the plain UAL1 `Walk_Loop`
(legs, torso, the left arm) with the RIGHT ARM (clavicle_r and everything below it, fingers included) held in the pose of UAL2 `Idle_Lantern_Loop` frame 0 (the fist held out at the side,
the pose that clip is made for). The end idle is `Idle_Lantern_Loop` itself, whose frame 0 is that same arm pose, so the walk-to-idle blend does not move the candle.
"""
import bpy


def assign(arm, action):
    arm.animation_data_create()
    arm.animation_data.action = action
    try:
        arm.animation_data.action_slot = action.slots[0]
    except Exception:  # noqa: BLE001
        pass


def find_action(name):
    hits = [a for a in bpy.data.actions if a.name == name or a.name.endswith("|" + name)]
    assert len(hits) == 1, (name, len(hits))
    return hits[0]


def right_arm_names(arm):
    out = set()
    for b in arm.data.bones:
        if b.name == "clavicle_r" or any(p.name == "clavicle_r" for p in b.parent_recursive):
            out.add(b.name)
    return out


def snapshot(arm, scene, action, frame):
    assign(arm, action)
    scene.frame_set(int(frame))
    scene.frame_set(int(frame))
    snap = {}
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        snap[pb.name] = (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy())
    return snap


def build_hybrid(arm, scene, walk, idle, idle_frame, name="Walk_Candle"):
    """A new action named `name` (fake user): walk's pose on every frame of its range, the right arm taken from `idle` at `idle_frame`."""
    right = right_arm_names(arm)
    f0, f1 = int(round(walk.frame_range[0])), int(round(walk.frame_range[1]))
    held = snapshot(arm, scene, idle, idle_frame)
    snaps = {f: snapshot(arm, scene, walk, f) for f in range(f0, f1 + 1)}
    for old in [a for a in bpy.data.actions if a.name == name]:
        bpy.data.actions.remove(old)
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    try:
        slot = act.slots.new(id_type="OBJECT", name=arm.name)
        arm.animation_data.action_slot = slot
    except Exception:  # noqa: BLE001
        pass
    for f in range(f0, f1 + 1):
        for pb in arm.pose.bones:
            loc, rot, sc = (held if pb.name in right else snaps[f])[pb.name]
            pb.location, pb.rotation_quaternion, pb.scale = loc, rot, sc
            pb.keyframe_insert("location", frame=f)
            pb.keyframe_insert("rotation_quaternion", frame=f)
            pb.keyframe_insert("scale", frame=f)
    return act
