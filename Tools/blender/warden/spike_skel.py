"""spike_skel.py -- P12-1 pipeline spike: a throwaway, deliberately lopsided 290 cm stick figure on the core bones of
the P12-5 joint table, exported as skinned FBX for Unreal. Blender 5.2, headless.

    blender.exe -b --factory-startup --python Tools/blender/warden/spike_skel.py -- [options]

Options (all optional):
    --out PATH            FBX path (default SourceArt/Warden/spike/SK_P12_Spike.fbx)
    --armature-name NAME  name of the armature OBJECT (default Armature)
    --axis-forward A      FBX export axis_forward (default Y)       -- see the P12-1 log for the variants tried
    --axis-up A           FBX export axis_up (default Z)
    --scale-options S     apply_scale_options (default FBX_SCALE_NONE)
    --no-unit-scale       apply_unit_scale=False
    --clip-only           export only the armature + its action (no mesh): the clip-only re-import test
    --tweak               change the geometry (head box 10 cm taller, mask box added): the re-import test
    --clip-name NAME      action name (default Spike_Clip)
    --bones add|remove    skeleton-change test: add = an extra bone `extra_test` under spine_05; remove = drop ik_hand_*

Conventions (plan P12-1 / P12-5): modelled in centimetres (scene unit scale 0.01, 1 BU = 1 cm); the character faces
-Y, its left is +X, Z up; A-pose at 45 degrees. Boxes are rigidly weighted (100 % on one bone). Slots: MAT_Left (all
left-side boxes, incl. the 30 cm hand box) and MAT_Body (everything else, incl. the 25 cm nose). Seedless: no random.
Also writes <out>.json with the bone list and the Blender-side bounds.
"""
import json
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = {"out": os.path.join(ROOT, "SourceArt", "Warden", "spike", "SK_P12_Spike.fbx"), "armature_name": "Armature",
         "axis_forward": "Y", "axis_up": "Z", "scale_options": "FBX_SCALE_NONE", "unit_scale": True,
         "clip_only": False, "tweak": False, "clip_name": "Spike_Clip", "bones": ""}
    i = 0
    while i < len(argv):
        k = argv[i]
        if k == "--out":
            a["out"] = argv[i + 1]; i += 1
        elif k == "--armature-name":
            a["armature_name"] = argv[i + 1]; i += 1
        elif k == "--axis-forward":
            a["axis_forward"] = argv[i + 1]; i += 1
        elif k == "--axis-up":
            a["axis_up"] = argv[i + 1]; i += 1
        elif k == "--scale-options":
            a["scale_options"] = argv[i + 1]; i += 1
        elif k == "--no-unit-scale":
            a["unit_scale"] = False
        elif k == "--clip-only":
            a["clip_only"] = True
        elif k == "--tweak":
            a["tweak"] = True
        elif k == "--bones":
            a["bones"] = argv[i + 1]; i += 1
        elif k == "--clip-name":
            a["clip_name"] = argv[i + 1]; i += 1
        i += 1
    return a


# ---------------------------------------------------------------- skeleton (cm, faces -Y, left = +X)
D = Vector((41, 0, -41)).normalized()           # arm / hand direction in the A-pose (down and out)
HAND = Vector((110, -2, 134))


def finger_pt(t):
    return HAND + D * t


# (name, parent, head, tail) for the CENTRE and LEFT bones; right bones are mirrored (x -> -x, _l -> _r).
CENTRE = [
    ("root", None, (0, 0, 0), (0, 0, 20)),
    ("pelvis", "root", (0, 0, 128), (0, 0, 140)),
    ("spine_01", "pelvis", (0, 0, 140), (0, -1, 155)),
    ("spine_02", "spine_01", (0, -1, 155), (0, -2, 172)),
    ("spine_03", "spine_02", (0, -2, 172), (0, -3, 190)),
    ("spine_04", "spine_03", (0, -3, 190), (0, -4, 208)),
    ("spine_05", "spine_04", (0, -4, 208), (0, -6, 226)),
    ("neck_01", "spine_05", (0, -6, 226), (0, -8, 240)),
    ("neck_02", "neck_01", (0, -8, 240), (0, -10, 254)),
    ("head", "neck_02", (0, -10, 254), (0, -10, 290)),
    ("mask", "head", (0, -18, 272), (0, -28, 272)),
    ("ik_foot_root", "root", (0, 0, 0), (0, 0, 8)),
    ("ik_hand_root", "root", (0, 0, 0), (0, 0, 8)),
]
SIDE = [  # names carry the _l suffix; mirrored automatically
    ("clavicle_l", "spine_05", (5, -3, 214), (28, -2, 216)),
    ("upperarm_l", "clavicle_l", (28, -2, 216), (69, -2, 175)),
    ("lowerarm_l", "upperarm_l", (69, -2, 175), (110, -2, 134)),
    ("hand_l", "lowerarm_l", tuple(HAND), tuple(finger_pt(4))),
    ("index_metacarpal_l", "hand_l", tuple(finger_pt(0)), tuple(finger_pt(9))),
    ("index_01_l", "index_metacarpal_l", tuple(finger_pt(9)), tuple(finger_pt(17))),
    ("index_02_l", "index_01_l", tuple(finger_pt(17)), tuple(finger_pt(24))),
    ("index_03_l", "index_02_l", tuple(finger_pt(24)), tuple(finger_pt(30))),
    ("thigh_l", "pelvis", (13, 0, 124), (14, -2, 70)),
    ("calf_l", "thigh_l", (14, -2, 70), (15, 2, 14)),
    ("foot_l", "calf_l", (15, 2, 14), (15, -14, 3)),
    ("ball_l", "foot_l", (15, -14, 3), (15, -26, 3)),
    ("ik_foot_l", "ik_foot_root", (15, 2, 14), (15, 2, 22)),
    ("ik_hand_l", "ik_hand_root", tuple(HAND), tuple(finger_pt(8))),
]


def mirror_name(n):
    return n[:-2] + "_r" if n.endswith("_l") else n


def mirror_parent(p):
    return p[:-2] + "_r" if p and p.endswith("_l") else p


def mirror_vec(v):
    return (-v[0], v[1], v[2])


def bone_table():
    rows = [(n, p, tuple(h), tuple(t)) for (n, p, h, t) in CENTRE]
    for (n, p, h, t) in SIDE:
        rows.append((n, p, tuple(h), tuple(t)))
    for (n, p, h, t) in SIDE:
        rows.append((mirror_name(n), mirror_parent(p), mirror_vec(h), mirror_vec(t)))
    return rows


# ---------------------------------------------------------------- boxes
def frustum(bm, head, tail, w0, d0, w1, d1, up_hint=None):
    """Tapered box from head to tail: cross-section w0 x d0 at the head, w1 x d1 at the tail."""
    head, tail = Vector(head), Vector(tail)
    ax = (tail - head).normalized()
    ref = Vector((0, 1, 0)) if abs(ax.y) < 0.9 else Vector((1, 0, 0))
    u = ref.cross(ax).normalized()      # width axis
    v = ax.cross(u).normalized()        # depth axis
    ring0 = [head + u * sx * w0 / 2 + v * sy * d0 / 2 for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    ring1 = [tail + u * sx * w1 / 2 + v * sy * d1 / 2 for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    vs = [bm.verts.new(p) for p in ring0 + ring1]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([vs[i] for i in f])
    return vs


def aabb(bm, lo, hi):
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    P = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    vs = [bm.verts.new(p) for p in P]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([vs[i] for i in f])
    return vs


# bone -> (w0, d0, w1, d1) for segment boxes between head and tail. Bones not listed get no box.
SEG = {
    "pelvis": (30, 20, 28, 18), "spine_01": (28, 18, 28, 18), "spine_02": (28, 18, 30, 18),
    "spine_03": (30, 18, 32, 18), "spine_04": (32, 18, 34, 18), "spine_05": (34, 18, 30, 16),
    "neck_01": (12, 12, 10, 10), "neck_02": (10, 10, 12, 12),
    "head": (18, 18, 26, 26),
    "clavicle_l": (7, 7, 8, 8), "upperarm_l": (9, 9, 7, 7), "lowerarm_l": (7, 7, 5, 5),
    "hand_l": (6, 3, 8, 3),
    "index_metacarpal_l": (3, 2, 3, 2), "index_01_l": (2.5, 2, 2.5, 2), "index_02_l": (2.5, 2, 2, 2), "index_03_l": (2, 2, 1.5, 1.5),
    "thigh_l": (16, 16, 11, 11), "calf_l": (11, 11, 7, 7),
}
# bone -> (lo, hi) axis-aligned boxes (left-side values; the mirror flips x). foot / ball sit on the ground (z 0).
AABB = {
    "foot_l": ((10, -14, 0), (20, 6, 14)),
    "ball_l": ((10.5, -26, 0), (19.5, -14, 6)),
}


def build_mesh(rows, tweak):
    """Returns a bmesh with a per-vertex bone assignment dict {vert index: bone name} and per-face slot index
    (0 = MAT_Body, 1 = MAT_Left)."""
    bm = bmesh.new()
    vert_bone = {}
    face_slot = {}
    pos = {n: (Vector(h), Vector(t)) for (n, p, h, t) in rows}

    def put(bone, maker):
        before = len(bm.faces)
        vs = maker()
        bm.verts.index_update(); bm.faces.index_update()
        for v in vs:
            vert_bone[v.index] = bone
        left = bone.endswith("_l")
        bm.faces.ensure_lookup_table()
        for i in range(before, len(bm.faces)):
            face_slot[i] = 1 if left else 0

    for side in ("_l", "_r"):
        for base, (w0, d0, w1, d1) in SEG.items():
            if base.endswith("_l"):
                name = base[:-2] + side
            elif side == "_l":
                name = base
            else:
                continue
            h, t = pos[name]
            put(name, lambda h=h, t=t, w0=w0, d0=d0, w1=w1, d1=d1: frustum(bm, h, t, w0, d0, w1, d1))
        for base, (lo, hi) in AABB.items():
            name = base[:-2] + side
            if side == "_l":
                l, h2 = lo, hi
            else:
                l, h2 = (-hi[0], lo[1], lo[2]), (-lo[0], hi[1], hi[2])
            put(name, lambda l=l, h2=h2: aabb(bm, l, h2))
    # the head, spine etc. were only created once (side "_l" pass, bases without _l); the loop above skips them for _r.

    # lopsided markers
    # 30 cm cube on the LEFT hand only, centred 35 cm out along the hand axis, so it sticks past the fingertips.
    c = HAND + D * 35
    put("hand_l", lambda: aabb(bm, (c.x - 15, c.y - 15, c.z - 15), (c.x + 15, c.y + 15, c.z + 15)))
    # 25 cm nose on the FACE only: head box front face is y = -10 - 13 = -23 at the top; nose runs -Y from there.
    put("head", lambda: aabb(bm, (-3, -48, 265), (3, -22, 273)))
    if tweak:  # re-import test: a visibly different head (10 cm taller) and a new flag box on the mask
        put("head", lambda: aabb(bm, (-14, -14, 290), (14, 12, 300)))
        put("mask", lambda: aabb(bm, (-9, -34, 266), (9, -28, 278)))
    bm.verts.index_update(); bm.faces.index_update()
    # make faces point outwards
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm, vert_bone, face_slot


# ---------------------------------------------------------------- scene building
def new_materials():
    out = {}
    for name, col in (("MAT_Body", (0.45, 0.42, 0.38, 1.0)), ("MAT_Left", (0.75, 0.25, 0.20, 1.0))):
        m = bpy.data.materials.new(name)
        m.diffuse_color = col
        out[name] = m
    return out


def build(args):
    # clean scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 0.01
    sc.unit_settings.length_unit = 'CENTIMETERS'
    sc.render.fps = 30
    rows = bone_table()
    if args["bones"] == "add":
        rows.append(("extra_test", "spine_05", (0, -6, 226), (0, -6, 236)))
    elif args["bones"] == "remove":
        rows = [r for r in rows if not r[0].startswith("ik_hand")]

    # armature
    arm_data = bpy.data.armatures.new("ArmatureData")
    arm_obj = bpy.data.objects.new(args["armature_name"], arm_data)
    sc.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = {}
    for (n, p, h, t) in rows:
        b = arm_data.edit_bones.new(n)
        b.head = Vector(h)
        b.tail = Vector(t)
        # roll: bone X axis towards world +X for vertical-ish bones keeps left/right readable
        eb[n] = b
    for (n, p, h, t) in rows:
        if p:
            eb[n].parent = eb[p]
    bpy.ops.object.mode_set(mode='OBJECT')

    # mesh
    mats = new_materials()
    mesh_obj = None
    if not args["clip_only"]:
        bm, vert_bone, face_slot = build_mesh(rows, args["tweak"])
        me = bpy.data.meshes.new("SK_P12_Spike_Mesh")
        bm.to_mesh(me)
        me.materials.append(mats["MAT_Body"])
        me.materials.append(mats["MAT_Left"])
        for f in me.polygons:
            f.material_index = face_slot.get(f.index, 0)
            f.use_smooth = False
        mesh_obj = bpy.data.objects.new("SK_P12_Spike", me)
        sc.collection.objects.link(mesh_obj)
        for (n, p, h, t) in rows:
            mesh_obj.vertex_groups.new(name=n)
        for vi, bone in vert_bone.items():
            mesh_obj.vertex_groups[bone].add([vi], 1.0, 'REPLACE')
        mesh_obj.parent = arm_obj
        mod = mesh_obj.modifiers.new("Armature", 'ARMATURE')
        mod.object = arm_obj
        bm.free()

    # clip: 2 s at 30 fps, looping (frame 0 == frame 60)
    sc.frame_start, sc.frame_end = 0, 60
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    act = bpy.data.actions.new(args["clip_name"])
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = act

    def rot_local(pb, axis, deg):
        """Rotation about the bone head, about a WORLD axis ('X' = bend forward when positive)."""
        m3 = pb.bone.matrix_local.to_3x3()
        r = Matrix.Rotation(math.radians(deg), 3, axis)
        pb.rotation_quaternion = (m3.inverted() @ r @ m3).to_quaternion()

    plan = {  # bone: (axis, degrees at frame 30)
        "spine_02": ("X", 18), "spine_03": ("X", 18), "spine_04": ("X", 18),
        "neck_01": ("X", 10), "upperarm_l": ("Y", -100), "lowerarm_l": ("Y", -30),
    }
    for frame, k in ((0, 0.0), (30, 1.0), (60, 0.0)):
        sc.frame_set(frame)
        for name, (axis, deg) in plan.items():
            pb = arm_obj.pose.bones[name]
            rot_local(pb, axis, deg * k)
            pb.keyframe_insert("rotation_quaternion", frame=frame)
    for fc in act.fcurves if hasattr(act, "fcurves") else []:
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
    bpy.ops.object.mode_set(mode='OBJECT')
    sc.frame_set(0)
    return arm_obj, mesh_obj, rows


def export(args, arm_obj, mesh_obj):
    bpy.ops.object.select_all(action='DESELECT')
    arm_obj.select_set(True)
    types = {'ARMATURE'}
    if mesh_obj is not None:
        mesh_obj.select_set(True)
        types.add('MESH')
    bpy.context.view_layer.objects.active = arm_obj
    os.makedirs(os.path.dirname(args["out"]), exist_ok=True)
    bpy.ops.export_scene.fbx(
        filepath=args["out"], use_selection=True, object_types=types,
        apply_unit_scale=args["unit_scale"], apply_scale_options=args["scale_options"], global_scale=1.0,
        bake_space_transform=False, axis_forward=args["axis_forward"], axis_up=args["axis_up"],
        add_leaf_bones=False, use_armature_deform_only=False, primary_bone_axis='Y', secondary_bone_axis='X',
        armature_nodetype='NULL', mesh_smooth_type='FACE', use_tspace=True, use_mesh_modifiers=True,
        bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0,
        path_mode='AUTO', use_custom_props=False)


def main():
    args = parse_args()
    arm_obj, mesh_obj, rows = build(args)
    # Blender-side report
    report = {"args": args, "bones": [r[0] for r in rows], "bone_count": len(rows)}
    if mesh_obj is not None:
        vs = [mesh_obj.matrix_world @ v.co for v in mesh_obj.data.vertices]
        lo = [min(v[i] for v in vs) for i in range(3)]
        hi = [max(v[i] for v in vs) for i in range(3)]
        report["bounds_cm"] = {"min": lo, "max": hi, "size": [hi[i] - lo[i] for i in range(3)],
                               "centre": [(hi[i] + lo[i]) / 2 for i in range(3)]}
        report["tris"] = sum(len(p.vertices) - 2 for p in mesh_obj.data.polygons)
    export(args, arm_obj, mesh_obj)
    with open(os.path.splitext(args["out"])[0] + ".json", "w") as fh:
        json.dump(report, fh, indent=1)
    print("SPIKE_OK", args["out"], "bones", len(rows), json.dumps(report.get("bounds_cm", {})))


main()
