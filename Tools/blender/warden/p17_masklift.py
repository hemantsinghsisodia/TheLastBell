"""p17_masklift.py -- P17-3 (Blender part): SM_LB_WardenMask and the hand-keyed AN_Warden_MaskLift for the Warden V11_1w.

    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --factory-startup --python Tools/blender/warden/p17_masklift.py -- [options]

      --scratch DIR     write sheet panels, the contact sheet and the gate JSON here (default: a temp dir; nothing in the repo is touched)
      --final           write the deliverables: SourceArt/Warden/P17/{Warden_MaskLift.blend, SM_LB_WardenMask.fbx, AN_Warden_MaskLift.fbx},
                        Docs/ArtTest/cine/{p17_masklift_gates.json, p17_masklift_contact.png}
      --nosheet         skip the renders
      --lean DEG        total forward lean at the extended frame (default 32)
      --reach CM        horizontal distance of the mask centre from the root at the extended frame (default 100)

Source is always SourceArt/Warden/V11_1w/Warden_Rigged.blend, opened and never saved. The P17 blend is written with save_as(copy=True).
Unreal is not touched.

Conventions (Blender frame: the Warden faces -Y, its right is -X, Z is up, metres; the clip is 30 fps, frame 1 = t 0 like the Idle):
  * mask bind frame = the blend's rest frame; T(t) maps it to the world at time t (the head pose until the grip, then the carried mask).
  * SM_LB_WardenMask vertices are written in the *head bone's rest-local* coordinates (cm). The +90 deg Z turn of the rotated LODs
    (p13_export_lods_rotated.py) turns the mesh and the bones together, so it cancels in bone-local coordinates: a static mesh imported with
    the default FBX conversion and attached to `head` at a zero offset sits exactly on the skinned mask (verified by --verify, see verify_mask()).
  * clip: same export recipe as SourceArt/Warden/V11_1w/scripts/export.py (root yaw key, cm, FBX_SCALE_UNITS, -Y/Z axes, bake all bones).
"""
import json
import math
import os
import subprocess
import sys
import tempfile

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
SRC_BLEND = os.path.join(ROOT, "SourceArt", "Warden", "V11_1w", "Warden_Rigged.blend")
P17_DIR = os.path.join(ROOT, "SourceArt", "Warden", "P17")
P17_BLEND = os.path.join(P17_DIR, "Warden_MaskLift.blend")
MASK_FBX = os.path.join(P17_DIR, "SM_LB_WardenMask.fbx")
CLIP_FBX = os.path.join(P17_DIR, "AN_Warden_MaskLift.fbx")
CINE_DIR = os.path.join(ROOT, "Docs", "ArtTest", "cine")
PY = r"C:\Users\heman\AppData\Local\Python\pythoncore-3.14-64\python.exe"
ACTION = "Warden_MaskLift"
MASK_NAME = "SM_LB_WardenMask"
FPS = 30
F0 = 1                      # frame of t = 0 (the Idle starts at frame 1 too)
DUR = 6.0
FN = F0 + int(DUR * FPS)    # 181

# beats (seconds), 3.7 / 4.1
T_RISE, T_GRIP0, T_GRIP, T_LIFT, T_EXT, T_END = 1.5, 1.5, 2.2, 3.4, 4.6, 6.0
T_MID = 4.0
LIFT_FWD, LIFT_UP = 0.20, 0.15      # 25.0 cm total
EYE_Z = 1.52

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OPT = {}
i_ = 0
while i_ < len(a):
    if a[i_] in ("--final", "--nosheet", "--verify", "--export"):
        OPT[a[i_].lstrip("-")] = True
        i_ += 1
    else:
        OPT[a[i_].lstrip("-")] = a[i_ + 1]
        i_ += 2
FINAL = bool(OPT.get("final"))
LEAN = float(OPT.get("lean", 32.0))
REACH = float(OPT.get("reach", 100.0)) / 100.0
SCRATCH = OPT.get("scratch") or tempfile.mkdtemp(prefix="p17ml_")
os.makedirs(SCRATCH, exist_ok=True)


def log(*x):
    print("P17ML| " + " ".join(str(v) for v in x), flush=True)


def fr(t):
    return F0 + t * FPS


def smoother(x):
    x = max(0.0, min(1.0, x))
    return x * x * x * (x * (6 * x - 15) + 10)


def E(t0, t1, t):
    return smoother((t - t0) / (t1 - t0))


def lerp(a_, b_, w):
    return a_ + (b_ - a_) * w


def vlerp(a_, b_, w):
    return a_ + (b_ - a_) * w


# ---------------------------------------------------------------------------------------------------------------------
# scene
# ---------------------------------------------------------------------------------------------------------------------
def import_fbx_fresh(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    return bpy.context.scene


def clip_info(path):
    sc = import_fbx_fresh(path)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    act = arm.animation_data.action
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    mw = arm.matrix_world
    sc.frame_set(f0)
    pos0 = {pb.name: (mw @ pb.head).copy() for pb in arm.pose.bones}
    roots = []
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        m = arm.pose.bones["root"].matrix_basis
        roots.append((m.translation.copy(), m.to_quaternion()))
    return dict(frames=(f0, f1), n_frames=f1 - f0 + 1, bones=len(arm.pose.bones), pos0=pos0, roots=roots, unit_to_cm=33.13 / (arm.data.bones['head'].length * mw.to_scale()[0]),       # the head bone is 33.13 cm long
                world_scale=mw.to_scale()[0], fps=sc.render.fps)


def verify():
    out = {}
    tmp = os.path.join(SCRATCH, "verify")
    os.makedirs(tmp, exist_ok=True)
    subprocess.run([bpy.app.binary_path, "-b", "--factory-startup", "--python", os.path.join(ROOT, "Tools", "blender", "warden", "p13_export_lods_rotated.py"), "--",
                    "--blend", P17_BLEND, "--out", tmp], check=True, capture_output=True)
    lodfbx = os.path.join(tmp, "SK_Warden_LOD0_rot.fbx")
    # ---- mask reconstruction: the rotated LOD0 as the skeletal import, the mask FBX attached to the head at the bind transform
    import_fbx_fresh(lodfbx)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    lod = next(o for o in bpy.data.objects if o.type == "MESH")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=MASK_FBX)
    mask = next(o for o in bpy.data.objects if o not in before and o.type == "MESH")
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    head = arm.data.bones["head"]
    kscale = 1.0 if head.length > 5 else 0.01          # mask vertices are in cm; bone-local units are cm when the head bone is ~33 long
    M0 = mask.matrix_world.copy()
    sc0 = M0.to_scale()[0]
    ident_err = max(abs(M0[i][j] / sc0 - (1.0 if i == j else 0.0)) for i in range(3) for j in range(3))
    from mathutils import kdtree
    slot1 = sorted({v for p in lod.data.polygons if p.material_index == 1 for v in p.vertices})
    lw = lod.matrix_world
    pts = [lw @ lod.data.vertices[i].co for i in slot1]
    kd = kdtree.KDTree(len(pts))
    for i, p in enumerate(pts):
        kd.insert(p, i)
    kd.balance()
    Mh = arm.matrix_world @ head.matrix_local
    world_cm = lw.to_scale()[0] * (1.0 if lod.data.vertices[0].co.length > 5 else 100.0)
    ds = []
    for v in mask.data.vertices:
        w = Mh @ (v.co * kscale)
        ds.append(kd.find(w)[2])
    # unit of the distance: world units; convert to cm with the LOD0 height (290 cm)
    zs = [p.z for p in pts]
    height_world = max((lw @ vv.co).z for vv in lod.data.vertices)
    cm_per_unit = 290.0 / height_world
    slots = [m.name for m in mask.data.materials]
    raw = open(MASK_FBX, "rb").read()
    slots_in_file = "M_Warden_BellMetal" if b"M_Warden_BellMetal\x00\x01Material" in raw else "NOT FOUND"
    out["mask_reconstruction"] = dict(
        vertices=len(mask.data.vertices), triangles=sum(len(p.vertices) - 2 for p in mask.data.polygons), slot_names_after_blender_import=slots, material_slot_name_in_fbx=slots_in_file, material_slot_count=len(slots),
        skinned_mask_vertices=len(slot1), max_dist_cm=round(max(ds) * cm_per_unit, 5), mean_dist_cm=round(sum(ds) / len(ds) * cm_per_unit, 5), limit_cm=0.1,
        passed=max(ds) * cm_per_unit <= 0.1, imported_mask_object_matrix_is_pure_scale=bool(ident_err < 1e-5), imported_mask_object_scale=round(sc0, 5),
        mask_bounds_head_local_cm=[[round(min(v.co[i] for v in mask.data.vertices), 2) for i in range(3)], [round(max(v.co[i] for v in mask.data.vertices), 2) for i in range(3)]],
        method="rotated LOD0 (p13_export_lods_rotated.py on Warden_MaskLift.blend) imported with Blender defaults; the mask FBX imported the same way, its vertices placed at the head bone's rest matrix; nearest skinned slot-1 vertex")
    # ---- (b) root and the start pose against the Idle FBX
    idle = clip_info(os.path.join(ROOT, "SourceArt", "Warden", "V11_1w", "exports", "AN_Warden_Idle.fbx"))
    lift = clip_info(CLIP_FBX)
    cm = lift["unit_to_cm"]
    dpos = max((lift["pos0"][n] - idle["pos0"][n]).length for n in idle["pos0"])
    r_i, r_l = idle["roots"][0], lift["roots"][0]
    rootloc = max(max((r[0] - r_i[0]).length for r in lift["roots"]), 0.0)
    rootrot = max(math.degrees(r[1].rotation_difference(r_i[1]).angle) for r in lift["roots"])
    idle_root_spread = max(math.degrees(r[1].rotation_difference(r_i[1]).angle) for r in idle["roots"])
    out["b_root"] = dict(
        passed=bool(rootloc * cm < 0.001 and rootrot < 0.01 and lift["bones"] == idle["bones"]),
        root_location_max_diff_vs_idle_frame0_cm=round(rootloc * cm, 5), root_rotation_max_diff_deg=round(rootrot, 5), idle_root_rotation_spread_deg=round(idle_root_spread, 5),
        root_quaternion_wxyz=[round(c, 5) for c in r_l[1]], bones_in_fbx=lift["bones"], idle_bones=idle["bones"],
        method="both FBX imported with Blender defaults; the clip's root pose-bone matrix_basis at every frame against the Idle's first frame")
    out["start_pose"] = dict(max_bone_head_diff_vs_idle_frame0_cm=round(dpos * cm, 4), bones_compared=len(idle["pos0"]), passed=bool(dpos * cm < 0.05))
    out["clip_fbx"] = dict(frames=lift["frames"], n_frames=lift["n_frames"], duration_s=round((lift["n_frames"] - 1) / 30.0, 3), fps_in_file=lift["fps"], bones=lift["bones"])
    gp = OPT.get("gates")
    if gp:
        g = json.load(open(gp, encoding="utf-8")) if os.path.exists(gp) else {}
        g.update(out)
        json.dump(g, open(gp, "w", encoding="utf-8"), indent=1)
    print("VERIFY|" + json.dumps(out, indent=1))


if OPT.get("verify"):
    verify()
    sys.exit(0)


bpy.ops.wm.open_mainfile(filepath=P17_BLEND if OPT.get("export") else SRC_BLEND)
scene = bpy.context.scene
scene.render.fps = FPS
rig = bpy.data.objects["Warden_Rig"]
lod0 = bpy.data.objects["SK_Warden_LOD0"]
PB = rig.pose.bones
RB = rig.data.bones

# Idle frame 1 pose (the start pose of the clip), as matrix_basis per bone
rig.animation_data.action = bpy.data.actions["Warden_Idle"]
scene.frame_set(1)
bpy.context.view_layer.update()
IDLE = {pb.name: pb.matrix_basis.copy() for pb in PB}
IDLE_POSE = {pb.name: pb.matrix.copy() for pb in PB}
rig.animation_data.action = None
for pb in PB:
    pb.matrix_basis = IDLE[pb.name]
bpy.context.view_layer.update()

REST = {b.name: b.matrix_local.copy() for b in RB}


def head_pose():
    return PB["head"].matrix.copy()


# ---------------------------------------------------------------------------------------------------------------------
# the mask (bind frame)
# ---------------------------------------------------------------------------------------------------------------------
me0 = lod0.data
MASK_FACES = [p for p in me0.polygons if p.material_index == 1]
MASK_VIDX = sorted({v for p in MASK_FACES for v in p.vertices})
MASK_BIND = [me0.vertices[i].co.copy() for i in MASK_VIDX]
H_REST = REST["head"]
H_REST_INV = H_REST.inverted()
xs = [v.x for v in MASK_BIND]
BB_MIN = Vector((min(v.x for v in MASK_BIND), min(v.y for v in MASK_BIND), min(v.z for v in MASK_BIND)))
BB_MAX = Vector((max(v.x for v in MASK_BIND), max(v.y for v in MASK_BIND), max(v.z for v in MASK_BIND)))
C_B = (BB_MIN + BB_MAX) * 0.5                      # mask centre in the bind frame
xmin, xmax = BB_MIN.x, BB_MAX.x
RIM_R = sum((v for v in MASK_BIND if v.x < xmin + 0.003), Vector()) / sum(1 for v in MASK_BIND if v.x < xmin + 0.003)    # Warden's right = -X
RIM_L = sum((v for v in MASK_BIND if v.x > xmax - 0.003), Vector()) / sum(1 for v in MASK_BIND if v.x > xmax - 0.003)
log("mask bbox", tuple(round(c * 100, 1) for c in BB_MIN), tuple(round(c * 100, 1) for c in BB_MAX), "centre", tuple(round(c * 100, 1) for c in C_B))
log("rim R", tuple(round(c * 100, 1) for c in RIM_R), "rim L", tuple(round(c * 100, 1) for c in RIM_L))


def mask_mesh_object(name, world_bind=True):
    """Triangulated mask-only mesh. world_bind: vertices in the bind frame (metres); else head-rest-local, centimetres."""
    bm = bmesh.new()
    bm.from_mesh(me0)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != 1], context="FACES")
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    for f in bm.faces:
        f.material_index = 0
    if not world_bind:
        for v in bm.verts:
            v.co = (H_REST_INV @ v.co) * 100.0
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(bpy.data.materials["M_Warden_BellMetal"])
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    return ob


# ---------------------------------------------------------------------------------------------------------------------
# arm geometry (rest)
# ---------------------------------------------------------------------------------------------------------------------
def fingers(side):
    return {"index": ["index_01_" + side, "index_02_" + side, "index_03_" + side],
            "middle": ["middle_01_" + side, "middle_02_" + side, "middle_03_" + side],
            "ring": ["ring_01_" + side, "ring_02_" + side, "ring_03_" + side],
            "pinky": ["pinky_01_" + side, "pinky_02_" + side, "pinky_03_" + side],
            "thumb": ["thumb_01_" + side, "thumb_02_" + side, "thumb_03_" + side]}


class Arm:
    def __init__(self, side):
        self.side = side
        self.n_up, self.n_lo, self.n_ha, self.n_cl = "upperarm_" + side, "lowerarm_" + side, "hand_" + side, "clavicle_" + side
        Ru, Rl, Rh = REST[self.n_up], REST[self.n_lo], REST[self.n_ha]
        self.Ru3, self.Rl3, self.Rh3 = Ru.to_3x3(), Rl.to_3x3(), Rh.to_3x3()
        self.Rrel_l = (Ru.inverted() @ Rl).to_3x3()           # lower relative to upper (rest)
        self.Rrel_h = (Rl.inverted() @ Rh).to_3x3()
        self.Tl = (Ru.inverted() @ Rl).translation.copy()      # elbow in upper-local
        self.Th = (Rl.inverted() @ Rh).translation.copy()      # wrist in lower-local
        yu = self.Ru3 @ Vector((0, 1, 0))
        yl = self.Rl3 @ Vector((0, 1, 0))
        # hinge: positive flexion takes the upper direction onto the lower direction about this axis
        dir_u_rest = (Rl.translation - Ru.translation).normalized()
        dir_l_rest = (Rh.translation - Rl.translation).normalized()
        self.bend_rest = dir_u_rest.angle(dir_l_rest)
        hw = dir_u_rest.cross(dir_l_rest).normalized()
        self.hu = self.Ru3.inverted() @ hw
        self.hl = self.Rrel_l.inverted() @ self.hu
        # palm centre: halfway from the wrist to the middle knuckle, on the palm surface
        n_rest_world = Vector((0, 1, 0))                      # relaxed fingers curl towards +Y in the rest/Idle pose (checked in probe)
        self.pal_n_local = (self.Rh3.inverted() @ n_rest_world)
        self.pal_n_local -= Vector((0, 1, 0)) * self.pal_n_local.dot(Vector((0, 1, 0)))
        self.pal_n_local.normalize()
        mk = REST["middle_01_" + side].translation
        self.pcl = self.Rh3.inverted() @ ((mk - Rh.translation) * 0.5) + self.pal_n_local * 0.02
        # hand-local frame (a, y, b): b = palm normal, y = fingers, a = y x b (thumb side)
        yv = Vector((0, 1, 0))
        av = yv.cross(self.pal_n_local)
        self.Aloc = Matrix((av, yv, self.pal_n_local)).transposed().to_3x3()      # columns a, y, b
        self.L1 = self.Tl.length
        self.L2 = self.Th.length
        self.fing = fingers(side)

    def palm_world(self, pose=True):
        pb = PB[self.n_ha]
        return pb.head + pb.matrix.to_3x3() @ self.pcl

    def hand_basis_for(self, f_world, n_world):
        """3x3 world orientation of the hand bone with the fingers along f and the palm normal along n."""
        f = f_world.normalized()
        n = (n_world - f * n_world.dot(f)).normalized()
        av = f.cross(n)
        return Matrix((av, f, n)).transposed().to_3x3() @ self.Aloc.inverted()


ARMS = {"r": Arm("r"), "l": Arm("l")}


def frame_from(y, x_hint):
    y = y.normalized()
    x = x_hint - y * x_hint.dot(y)
    if x.length < 1e-6:
        x = y.orthogonal()
    x.normalize()
    z = x.cross(y)
    return Matrix((x, y, z)).transposed().to_3x3()          # columns x, y, z


def rot_about(axis, ang):
    return Matrix.Rotation(ang, 3, axis.normalized())


def twist_angle(R3, axis_local=Vector((0, 1, 0))):
    q = R3.to_quaternion()
    v = Vector((q.x, q.y, q.z))
    return 2.0 * math.atan2(v.dot(axis_local), q.w)


def set_rot3(pb, R3):
    pb.matrix_basis = R3.to_4x4()


SOLVE_LOG = {}


def solve_arm(arm, W, Rh_t, pole, tw_share=0.5, twist_override=None, rel_override=None):
    """Place upperarm, lowerarm and hand: wrist at W (clamped to the reach), hand orientation Rh_t (3x3, world)."""
    pbU, pbL, pbH, pbC = PB[arm.n_up], PB[arm.n_lo], PB[arm.n_ha], PB[arm.n_cl]
    S = pbU.head.copy()
    aL, bL = arm.L1, arm.L2
    v = W - S
    d = v.length
    dmax = (aL + bL) * 0.997
    clamped = 0.0
    if d > dmax:
        clamped = d - dmax
        d = dmax
        W = S + v.normalized() * d
    u = (W - S).normalized()
    cosA = max(-1.0, min(1.0, (aL * aL + d * d - bL * bL) / (2 * aL * d)))
    A = math.acos(cosA)
    p = pole - u * pole.dot(u)
    if p.length < 1e-6:
        p = u.orthogonal()
    p.normalize()
    dirU = u * math.cos(A) + p * math.sin(A)
    E_ = S + dirU * aL
    dirL = (W - E_).normalized()
    nhat = -(u.cross(p)).normalized()
    # upper: local hinge axis -> world n
    Au = frame_from(arm.Tl, arm.hu)
    Bu = frame_from(dirU, nhat)
    Ru = Bu @ Au.transposed()
    # lower: pure hinge from the upper, then the wrist-offset correction
    bend_now = dirU.angle(dirL)
    dphi = bend_now - arm.bend_rest
    Rl_h = Ru @ arm.Rrel_l @ rot_about(arm.hl, dphi)
    Q = (Rl_h @ arm.Th.normalized()).rotation_difference(dirL).to_matrix()
    Rl_h = Q @ Rl_h
    # forearm twist: the lower frame that carries the wanted hand orientation, shared between the elbow and the wrist
    F0_ = Rh_t @ arm.Rrel_h.inverted()
    tau = twist_angle(Rl_h.inverted() @ F0_, arm.Th.normalized())
    tau = (tau + math.pi) % (2 * math.pi) - math.pi
    applied = tw_share * tau if twist_override is None else twist_override
    Rl = Rl_h @ rot_about(arm.Th.normalized(), applied)       # about the elbow-to-wrist axis, so the wrist does not move
    # basis (rotation only): R_pose = R_parent_pose @ Rrel @ basis
    pbU.matrix_basis = ((pbC.matrix.to_3x3() @ (REST[arm.n_cl].inverted() @ REST[arm.n_up]).to_3x3()).inverted() @ Ru).to_4x4()
    Rrel_l = (REST[arm.n_up].inverted() @ REST[arm.n_lo]).to_3x3()
    pbL.matrix_basis = ((Ru @ Rrel_l).inverted() @ Rl).to_4x4()
    Rrel_h = (REST[arm.n_lo].inverted() @ REST[arm.n_ha]).to_3x3()
    if rel_override is not None:
        Rh_t = Rl @ Rrel_h @ rel_override.to_matrix()
    pbH.matrix_basis = ((Rl @ Rrel_h).inverted() @ Rh_t).to_4x4()
    SOLVE_LOG[arm.side] = dict(clamped=clamped, tau=math.degrees(tau), bend=math.degrees(bend_now), applied=applied,
                               rel_q=((Rl @ Rrel_h).inverted() @ Rh_t).to_quaternion())
    return clamped


# finger curl axes: found by test (the curl moves the fingertip towards the palm normal)
CURL = {}


def find_curl_axes():
    for side, arm in ARMS.items():
        for fname, chain in arm.fing.items():
            best = None
            for ax in ("X", "Z"):
                for sg in (1, -1):
                    for n in chain:
                        PB[n].matrix_basis = IDLE[n] @ Matrix.Rotation(sg * 0.5, 4, ax)
                    bpy.context.view_layer.update()
                    tip = PB[chain[-1]].tail.copy()
                    for n in chain:
                        PB[n].matrix_basis = IDLE[n]
                    bpy.context.view_layer.update()
                    base = PB[chain[-1]].tail.copy()
                    pn = (PB[arm.n_ha].matrix.to_3x3() @ arm.pal_n_local)
                    score = (tip - base).dot(pn)
                    if best is None or score > best[0]:
                        best = (score, ax, sg)
            CURL[(side, fname)] = (best[1], best[2])
    log("curl axes", {"%s_%s" % k: v for k, v in CURL.items()})


FIN_ANG = {"index": (40, 62, 42), "middle": (42, 65, 45), "ring": (44, 66, 46), "pinky": (46, 66, 48), "thumb": (18, 34, 30)}
FIN_SCALE = 1.0


def apply_fingers(side, curl):
    arm = ARMS[side]
    for fname, chain in arm.fing.items():
        ax, sg = CURL[(side, fname)]
        for n, deg in zip(chain, FIN_ANG[fname]):
            ang = math.radians(deg) * curl * sg
            PB[n].matrix_basis = IDLE[n] @ Matrix.Rotation(ang, 4, ax)


# ---------------------------------------------------------------------------------------------------------------------
# the motion
# ---------------------------------------------------------------------------------------------------------------------
LEAN_SPLIT = {"spine_01": 0.20, "spine_02": 0.27, "spine_03": 0.27, "neck_01": 0.16, "head": 0.10}      # fractions of the total lean
SETTLE_LEAN = 1.6        # deg, added after the extended frame
SETTLE_DOWN = 0.015      # m, the mask settles this far down
HAND_OFF = {"r": Vector((-0.035, -0.052, -0.030)), "l": Vector((0.035, -0.052, -0.030))}     # palm centre from the rim point, bind axes
POLE = {"r": Vector((-0.55, 0.35, -0.75)), "l": Vector((0.55, 0.35, -0.75))}          # elbow direction at the rims: out and down
POLE0 = {"r": Vector((-0.30, 0.90, 0.10)), "l": Vector((0.30, 0.90, 0.10))}          # at the start: back (the shoulder-to-wrist line never lines up with it on the way up)
PALM_N = {"r": Vector((0.75, 0.66, 0.0)), "l": Vector((-0.75, 0.66, 0.0))}                 # palm normal at the rim, bind axes
FINGER_DIR = {"r": Vector((0.10, -0.55, 1.0)), "l": Vector((-0.10, -0.55, 1.0))}           # fingers up, a little forward
HEAD_Z_CTRL = None
ENDDATA = {}          # per side: (applied forearm twist, wrist-relative orientation) at the end of the rise

T_GRIP_M = None       # mask transform at the grip (Matrix 4x4)
Q_GRIP = None


def mask_T(t, grip_T, c_lift, q_lift, c_ext):
    """Rigid transform bind -> world of the mask at time t."""
    if t <= T_GRIP:
        return grip_T
    cg = grip_T @ C_B
    qg = grip_T.to_quaternion()
    disp = Vector((0, -LIFT_FWD, LIFT_UP))
    if t <= T_LIFT:
        w = E(T_GRIP, T_LIFT, t)
        c = cg + disp * w
        q = qg
    elif t <= T_EXT:
        u = (t - T_LIFT) / (T_EXT - T_LIFT)
        wy = smoother(min(1.0, u * 1.3))
        wz = smoother(u)
        c = Vector((lerp(c_lift.x, c_ext.x, wz), lerp(c_lift.y, c_ext.y, wy), lerp(c_lift.z, c_ext.z, wz)))
        q = q_lift.slerp(Quaternion(), smoother(u))
    else:
        s = E(T_EXT, T_EXT + 1.0, t)
        c = c_ext + Vector((0, 0, -SETTLE_DOWN)) * s
        q = Quaternion()
    R = q.to_matrix()
    # world = R @ p_bind + (c - R @ C_B)
    M = R.to_4x4()
    M.translation = c - R @ C_B
    return M


def lean_total(t):
    return math.radians(LEAN) * E(T_LIFT, T_EXT, t) + math.radians(SETTLE_LEAN) * E(T_EXT, T_EXT + 1.0, t)


def pose_frame(t, ctx):
    """Set every pose bone for time t. ctx holds the mask trajectory constants."""
    for pb in PB:
        pb.matrix_basis = IDLE[pb.name]
    tot = lean_total(t)
    for n, share in LEAN_SPLIT.items():
        q = Quaternion((1, 0, 0), tot * share) @ IDLE[n].to_quaternion()
        m = q.to_matrix().to_4x4()
        m.translation = IDLE[n].translation
        PB[n].matrix_basis = m
    bpy.context.view_layer.update()
    T = mask_T(t, ctx["grip_T"], ctx["c_lift"], ctx["q_lift"], ctx["c_ext"])
    for side, arm in ARMS.items():
        rise = E(0.0, T_RISE, t) if side == "r" else E(0.12, T_RISE, t)
        press = E(T_GRIP0, T_GRIP, t)
        rim = RIM_R if side == "r" else RIM_L
        off = HAND_OFF[side]
        inward = Vector((1, 0, 0)) if side == "r" else Vector((-1, 0, 0))
        off_now = off + (inward * 0.004 + Vector((0, 0.010, 0))) * press          # presses 1 cm in and 0.4 cm towards the face
        p_bind = rim + off_now
        f_b = FINGER_DIR[side].normalized()
        n_b = PALM_N[side]
        Rt_end = arm.hand_basis_for(T.to_3x3() @ f_b, T.to_3x3() @ n_b)
        if t < T_GRIP0 + 1e-9:
            p_end = T @ p_bind
            s_ = rise
            P0 = ctx["start_palm"][side]
            P3 = p_end
            outv = Vector((-1, 0, 0)) if side == "r" else Vector((1, 0, 0))
            P1 = P0 + outv * 0.14 + Vector((0, -0.22, 0.55))
            P2 = P3 + outv * 0.28 + Vector((0, -0.18, -0.20))
            om = 1 - s_
            palm = om ** 3 * P0 + 3 * om * om * s_ * P1 + 3 * om * s_ * s_ * P2 + s_ ** 3 * P3
            Rt = ctx["start_R"][side].to_quaternion().slerp(Rt_end.to_quaternion(), s_).to_matrix()
        else:
            palm = T @ p_bind
            Rt = Rt_end
        # wrist from the palm centre
        W = palm - Rt @ arm.pcl
        pole_now = POLE0[side].lerp(POLE[side], smoother(rise)) if t < T_GRIP0 else POLE[side]
        if t < T_GRIP0 - 1e-9 and ENDDATA:
            # while rising, the twist and the wrist bend are eased towards their values at the rims (no swing/twist flips on the way)
            sq = rise
            solve_arm(arm, W, Rt, pole_now, twist_override=ENDDATA[side][0] * smoother(sq), rel_override=Quaternion().slerp(ENDDATA[side][1], smoother(sq)))
        else:
            solve_arm(arm, W, Rt, POLE[side])
        beta = 1.0 - smoother(t / 0.5)            # the first half second blends from the Idle arm pose, so frame 0 is exactly the Idle
        if beta > 0.0:
            for n in (arm.n_up, arm.n_lo, arm.n_ha):
                q = PB[n].matrix_basis.to_quaternion().slerp(IDLE[n].to_quaternion(), beta)
                m = q.to_matrix().to_4x4()
                m.translation = IDLE[n].translation
                PB[n].matrix_basis = m
        bpy.context.view_layer.update()
    # fingers: slightly spread while approaching, then curling onto the rims; a little tighter when settling
    for side in ("r", "l"):
        c_open = -0.15 * E(0.0, T_RISE, t)
        curl = lerp(c_open, 1.0, E(T_GRIP0, T_GRIP, t)) + 0.12 * E(T_EXT, T_EXT + 1.0, t)
        apply_fingers(side, curl)
    bpy.context.view_layer.update()


# ---------------------------------------------------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------------------------------------------------
MOVED = (["spine_01", "spine_02", "spine_03", "neck_01", "head"]
         + ["upperarm_r", "lowerarm_r", "hand_r", "upperarm_l", "lowerarm_l", "hand_l"]
         + [n for s in ("r", "l") for ch in fingers(s).values() for n in ch])


def key_bone(pb, f):
    pb.keyframe_insert(data_path="location", frame=f)
    if pb.rotation_mode == "QUATERNION":
        pb.keyframe_insert(data_path="rotation_quaternion", frame=f)
    else:
        pb.keyframe_insert(data_path="rotation_euler", frame=f)


def build():
    find_curl_axes()
    # starting palms and hand orientations (the Idle)
    for pb in PB:
        pb.matrix_basis = IDLE[pb.name]
    bpy.context.view_layer.update()
    ctx = {"start_palm": {s: ARMS[s].palm_world() for s in ARMS}, "start_R": {s: PB[ARMS[s].n_ha].matrix.to_3x3() for s in ARMS}}
    # the mask transform at the grip is the head pose (the head is untouched until the lift)
    grip_T = head_pose() @ H_REST_INV
    ctx["grip_T"] = grip_T
    cg = grip_T @ C_B
    c_lift = cg + Vector((0, -LIFT_FWD, LIFT_UP))
    ctx["c_lift"] = c_lift
    ctx["q_lift"] = grip_T.to_quaternion()
    # end position: the mask centre REACH metres from the root, at eye height
    ctx["c_ext"] = Vector((0.0, -REACH, EYE_Z))
    log("grip centre", tuple(round(c * 100, 1) for c in cg), "lift centre", tuple(round(c * 100, 1) for c in c_lift), "ext centre", tuple(round(c * 100, 1) for c in ctx["c_ext"]))
    pose_frame(T_GRIP0, ctx)              # prepass: the arm pose at the rims, read back as the target of the rise
    for side in ARMS:
        ENDDATA[side] = (SOLVE_LOG[side]["applied"], SOLVE_LOG[side]["rel_q"].copy())
    act = bpy.data.actions.new(ACTION)
    act.use_fake_user = True
    rig.animation_data.action = act
    # the Idle values, held, for every bone at the first and last frame
    for pb in PB:
        pb.matrix_basis = IDLE[pb.name]
    for pb in PB:
        key_bone(pb, F0)
    logs = []
    for f in range(F0, FN + 1):
        t = (f - F0) / FPS
        pose_frame(t, ctx)
        for n in MOVED:
            key_bone(PB[n], f)
        logs.append((t, dict(SOLVE_LOG)))
        if OPT.get("debug"):
            log("dbg", f, round(t, 2), {k: (round(v['tau'], 1), round(v['bend'], 1)) for k, v in SOLVE_LOG.items()})
    for pb in PB:
        if pb.name not in MOVED:
            pb.matrix_basis = IDLE[pb.name]
            key_bone(pb, FN)
    # root: same convention as AN_Warden_Idle's export (a constant yaw about the bone axis); keyed in the export step (build_root_key)
    return act, ctx, logs


def build_root_key(act):
    """The exact recipe of V11_1w/scripts/export.py for the root: quaternion mode, yaw +90 deg about the bone's local axis of world Z."""
    root = PB["root"]
    root.rotation_mode = "QUATERNION"
    for f in range(F0, FN + 1):
        scene.frame_set(f)
        axis = root.bone.matrix_local.to_3x3().inverted() @ Vector((0, 0, 1))
        root.rotation_quaternion = Quaternion(axis, math.pi / 2)
        root.keyframe_insert(data_path="rotation_quaternion", frame=f)


# ---------------------------------------------------------------------------------------------------------------------
# measurement
# ---------------------------------------------------------------------------------------------------------------------
def set_frame(f):
    scene.frame_set(int(round(f)))
    bpy.context.view_layer.update()


def carried_helper(ctx, grip_f):
    """A copy of the mask in the bind frame, parented to hand_r from the grip frame with Keep World (like Unreal's attach), and one on the head before."""
    ob = mask_mesh_object("MaskCarryHelper", world_bind=True)
    set_frame(grip_f)
    hand = PB["hand_r"]
    Pw = rig.matrix_world @ hand.matrix @ Matrix.Translation((0, hand.bone.length, 0))     # bone parent origin is the tail
    ob.parent = rig
    ob.parent_type = "BONE"
    ob.parent_bone = "hand_r"
    ob.matrix_parent_inverse = Pw.inverted() @ ctx["grip_T"]
    return ob


def mask_world_pts(ob, pts):
    return [ob.matrix_world @ p for p in pts]


def measure(ctx, act):
    res = {}
    f_grip, f_lift, f_ext, f_mid, f_end = [int(round(fr(t))) for t in (T_GRIP, T_LIFT, T_EXT, T_MID, T_END)]
    helper = carried_helper(ctx, f_grip)
    dg = bpy.context.evaluated_depsgraph_get
    # (a) grip contact
    set_frame(f_grip)
    wr = {}
    for s, rim in (("r", RIM_R), ("l", RIM_L)):
        arm = ARMS[s]
        rim_w = ctx["grip_T"] @ rim
        wr[s] = dict(palm_cm=round((arm.palm_world() - rim_w).length * 100, 2), hand_bone_cm=round((PB[arm.n_ha].head - rim_w).length * 100, 2),
                     nearest_fingertip_cm=round(min((PB[ch[-1]].tail - rim_w).length for ch in arm.fing.values()) * 100, 2))
    res["a_grip_contact"] = dict(frame=f_grip, t=T_GRIP, limit_cm=8.0, right=wr["r"], left=wr["l"],
                                 passed=all(wr[s]["palm_cm"] <= 8.0 and wr[s]["hand_bone_cm"] <= 8.0 + 4.0 for s in wr) and all(wr[s]["palm_cm"] <= 8.0 for s in wr))
    # carried mask vs design over the carry; left palm vs left rim carried by the right-hand helper
    dev_c, dev_l = [], []
    cen = {}
    for f in range(f_grip, FN + 1):
        set_frame(f)
        M = helper.matrix_world
        cw = M @ C_B
        cen[f] = cw.copy()
        t = (f - F0) / FPS
        Td = mask_T(t, ctx["grip_T"], ctx["c_lift"], ctx["q_lift"], ctx["c_ext"])
        dev_c.append((cw - Td @ C_B).length)
        rimL_w = M @ RIM_L
        dev_l.append((ARMS["l"].palm_world() - rimL_w).length)
    res["carry"] = dict(helper_vs_design_max_cm=round(max(dev_c) * 100, 3),
                        left_palm_to_left_rim_cm=dict(at_grip=round(dev_l[0] * 100, 2), min=round(min(dev_l) * 100, 2), max=round(max(dev_l) * 100, 2)),
                        note="helper = mask copy parented to hand_r at the grip frame (Keep World); left palm vs the carried left rim point")
    # (d) reach
    c_ext = cen[f_ext]
    reach = math.hypot(c_ext.x - PB["root"].head.x, c_ext.y - PB["root"].head.y)
    set_frame(f_ext)
    res["d_reach"] = dict(frame=f_ext, t=T_EXT, mask_centre_cm=[round(c * 100, 1) for c in c_ext], mask_centre_height_cm=round(c_ext.z * 100, 1),
                          horizontal_reach_cm=round(reach * 100, 1), stop_distance_cm=round(reach * 100 - 20, 1),
                          reach_at_end_cm=round(math.hypot(cen[f_end].x, cen[f_end].y) * 100, 1), height_at_end_cm=round(cen[f_end].z * 100, 1))
    # lifted
    c_l = cen[f_lift]
    c_g = cen[f_grip]
    res["lifted"] = dict(frame=f_lift, t=T_LIFT, displacement_from_grip_cm=round((c_l - c_g).length * 100, 1), forward_cm=round(-(c_l.y - c_g.y) * 100, 1), up_cm=round((c_l.z - c_g.z) * 100, 1))
    # arm solver diagnostics: forearm twist and elbow bend by time, clamping (arm too short)
    return res, helper, cen


def arm_stats(ctx):
    """Sweep the clip and report clamping, wrist error, twists, elbow bend, feet drift and finger ranges from the keyed action."""
    out = {"clamped_max_cm": 0.0, "wrist_err_max_cm": 0.0}
    feet0 = None
    drift = 0.0
    tw = {"r": [], "l": []}
    bend = {"r": [], "l": []}
    for f in range(F0, FN + 1):
        set_frame(f)
        feet = {n: PB[n].head.copy() for n in ("foot_l", "foot_r", "ball_l", "ball_r", "pelvis")}
        if feet0 is None:
            feet0 = feet
        for n in feet:
            drift = max(drift, (feet[n] - feet0[n]).length)
        for s, arm in ARMS.items():
            pu, pl, ph = PB[arm.n_up], PB[arm.n_lo], PB[arm.n_ha]
            Ru, Rl, Rh = pu.matrix.to_3x3(), pl.matrix.to_3x3(), ph.matrix.to_3x3()
            bend[s].append(math.degrees((pl.head - pu.head).angle(ph.head - pl.head)))
            rel = (Rl @ arm.Rrel_h).inverted() @ Rh
            tw[s].append(math.degrees(twist_angle(rel, Vector((0, 1, 0)))))
    out["feet_pelvis_max_drift_cm"] = round(drift * 100, 4)
    out["elbow_interior_bend_deg"] = {s: [round(min(v), 1), round(max(v), 1)] for s, v in bend.items()}
    out["wrist_twist_deg_range"] = {s: [round(min(v), 1), round(max(v), 1)] for s, v in tw.items()}
    return out


# ---------------------------------------------------------------------------------------------------------------------
# renders (Workbench, orthographic, front and side) and the contact sheet
# ---------------------------------------------------------------------------------------------------------------------
PANEL = 560
ZC, SCALE = 1.62, 3.5


def setup_render():
    for ob in list(bpy.data.objects):
        if ob.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(ob, do_unlink=True)
        elif ob.type == "MESH":
            ob.hide_render = True
            ob.hide_viewport = True
    cols = {"M_Warden_Wool": (.22, .22, .26, 1), "M_Warden_BellMetal": (.95, .8, .25, 1), "M_Warden_RustedIron": (.5, .3, .2, 1), "M_Warden_Skin": (.85, .62, .5, 1),
            "M_Warden_Leather": (.35, .2, .1, 1), "M_Warden_ChainIron": (.55, .55, .6, 1), "M_Warden_DimEyes": (1, 0, 0, 1), "M_Warden_Keratin": (.9, .9, .8, 1)}
    for m in bpy.data.materials:
        if m.name in cols:
            m.diffuse_color = cols[m.name]
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    sh.type = "SOLID"
    sh.light = "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_cavity = False
    scene.render.resolution_x = scene.render.resolution_y = PANEL
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    cam = bpy.data.objects.new("p17cam", bpy.data.cameras.new("p17cam"))
    scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = SCALE
    scene.camera = cam
    body = lod0.copy()
    body.data = lod0.data.copy()
    scene.collection.objects.link(body)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in (1, 5)], context="FACES")     # no mask (rendered separately) and no chains (physics-driven in Unreal)
    bm.to_mesh(body.data)
    bm.free()
    body.hide_render = False
    body.hide_viewport = False
    pm = mask_mesh_object("MaskRender", world_bind=True)
    pm.hide_render = False
    return cam, body, pm


def render_panels(cam, pm, helper, ctx, frames, prefix, outdir):
    paths = []
    f_grip = int(round(fr(T_GRIP)))
    for label, f in frames:
        set_frame(f)
        if f < f_grip:
            pm.matrix_world = PB["head"].matrix @ H_REST_INV
        else:
            hand = PB["hand_r"]
            pm.matrix_world = rig.matrix_world @ hand.matrix @ Matrix.Translation((0, hand.bone.length, 0)) @ helper.matrix_parent_inverse
        for view in ("front", "side"):
            if view == "front":
                loc, tgt = (0, -8, ZC), (0, 0, ZC)
            else:
                loc, tgt = (-8, -0.35, ZC), (0, -0.35, ZC)
            cam.location = loc
            cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
            fp = os.path.join(outdir, "%s_%s_%s.png" % (prefix, label, view))
            scene.render.filepath = fp
            bpy.ops.render.render(write_still=True)
            paths.append((label, f, view, fp))
    return paths


def make_sheet(paths, out_png, meta_extra):
    meta = dict(panels=[dict(label=l, frame=f, t=round((f - F0) / FPS, 2), view=v, path=p) for l, f, v, p in paths], out=out_png, zc=ZC, scale=SCALE, panel=PANEL, **meta_extra)
    mp = os.path.join(os.path.dirname(paths[0][3]), "sheet_meta.json")
    with open(mp, "w") as fh:
        json.dump(meta, fh)
    comp = os.path.join(ROOT, "Tools", "blender", "warden", "p17_sheet_compose.py")
    r = subprocess.run([PY, "-I", comp, mp], capture_output=True, text=True)
    log("compose", r.returncode, r.stdout.strip()[:200], r.stderr.strip()[:400])


# ---------------------------------------------------------------------------------------------------------------------
# clearance: forearm/hand skin against the rest of the body
# ---------------------------------------------------------------------------------------------------------------------
def clearance(ctx, frames):
    """Skin (slot 3) of the forearms (rest z 1.25..1.78) and the hands (below 1.25) against the wool (hood, cape, robe): minimum distance and the number of vertices within 1 cm."""
    from mathutils.bvhtree import BVHTree
    skin_idx = {v for p in lod0.data.polygons if p.material_index == 3 for v in p.vertices}
    zr = {i: lod0.data.vertices[i].co.z for i in skin_idx}
    groups = {"forearm": [i for i in skin_idx if 1.25 <= zr[i] < 1.78], "hand": [i for i in skin_idx if zr[i] < 1.25]}
    res = {}
    for label, f in frames:
        set_frame(f)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = lod0.evaluated_get(dg)
        me = ev.to_mesh()
        verts = [v.co.copy() for v in me.vertices]
        tris = []
        for p in me.polygons:
            if p.material_index == 0:          # wool: hood, cape, robe
                pv = list(p.vertices)
                for k in range(1, len(pv) - 1):
                    tris.append((pv[0], pv[k], pv[k + 1]))
        body = BVHTree.FromPolygons(verts, tris, epsilon=0.0)
        entry = dict(frame=f, t=round((f - F0) / FPS, 2))
        for g, idx in groups.items():
            mind, n1, n05 = 9.0, 0, 0
            for i in idx:
                hit = body.find_nearest(verts[i])
                if hit[0] is not None:
                    mind = min(mind, hit[3])
                    n1 += hit[3] < 0.01
                    n05 += hit[3] < 0.005
            entry[g] = dict(verts=len(idx), min_dist_cm=round(mind * 100, 2), within_1cm=n1, within_0_5cm=n05)
        res[label] = entry
        ev.to_mesh_clear()
    return res


def closeups(cam, pm, helper):
    """Development aid: close orthographic views of the hands and the mask at the grip and lifted frames."""
    cam.data.ortho_scale = 1.1
    for label, t in (("grip", T_GRIP), ("lifted", T_LIFT), ("ext", T_EXT)):
        f = int(round(fr(t)))
        set_frame(f)
        hand = PB["hand_r"]
        pm.matrix_world = rig.matrix_world @ hand.matrix @ Matrix.Translation((0, hand.bone.length, 0)) @ helper.matrix_parent_inverse
        c = pm.matrix_world @ C_B
        for view, d in (("front", Vector((0, -1, 0))), ("side", Vector((-1, 0, 0))), ("three", Vector((-0.7, -0.7, 0.35)))):
            cam.location = c + d.normalized() * 6
            cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
            scene.render.resolution_x = scene.render.resolution_y = 700
            scene.render.filepath = os.path.join(SCRATCH, "close_%s_%s.png" % (label, view))
            bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------------------------------------------------------------
# blend, exports
# ---------------------------------------------------------------------------------------------------------------------
def save_blend():
    """P17 copy: the three LODs, the rig and the owner's three clips plus the new clip. The leftover LOD copies and the extra rigs of the V11.1 file are dropped (the export scripts never use them)."""
    keep = {"Warden_Rig", "SK_Warden_LOD0", "SK_Warden_LOD1", "SK_Warden_LOD2"}
    for ob in list(bpy.data.objects):
        if ob.name not in keep:
            bpy.data.objects.remove(ob, do_unlink=True)
    rig.animation_data.action = bpy.data.actions[ACTION]
    scene.frame_start, scene.frame_end = F0, FN
    scene.frame_set(F0)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    os.makedirs(P17_DIR, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=P17_BLEND, copy=True)
    log("saved", P17_BLEND, os.path.getsize(P17_BLEND))


EXPORT_SETTINGS = dict(use_selection=True, global_scale=1, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Y", axis_up="Z",
                       bake_space_transform=False, use_mesh_modifiers=True, mesh_smooth_type="FACE", use_tspace=True, add_leaf_bones=False,
                       use_armature_deform_only=True, armature_nodetype="NULL", path_mode="RELATIVE", embed_textures=False)


def export_all():
    """Run on the saved P17 blend: the mask FBX (head-local, cm) and the clip FBX, with the recipe of V11_1w/scripts/export.py."""
    act = bpy.data.actions[ACTION]
    mask = mask_mesh_object(MASK_NAME, world_bind=False)          # head-rest-local centimetres, built before any unit change
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for bone in rig.data.edit_bones:
        bone.head *= 100
        bone.tail *= 100
    bpy.ops.object.mode_set(mode="OBJECT")
    for action in bpy.data.actions:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        if curve.data_path.endswith(".location"):
                            for key in curve.keyframe_points:
                                key.co[1] *= 100
                                key.handle_left[1] *= 100
                                key.handle_right[1] *= 100
                            curve.update()
    scene.unit_settings.scale_length = .01
    # mask
    bpy.ops.object.select_all(action="DESELECT")
    mask.select_set(True)
    bpy.context.view_layer.objects.active = mask
    bpy.ops.export_scene.fbx(filepath=MASK_FBX, object_types={"MESH"}, bake_anim=False, **EXPORT_SETTINGS)
    log("mask fbx", MASK_FBX, os.path.getsize(MASK_FBX))
    # clip
    rig.name = "Armature"
    rig.animation_data.action = act
    build_root_key(act)               # as export.py does, in memory only: the blend itself never carries the +90 deg root yaw
    scene.frame_start, scene.frame_end = int(act.frame_range[0]), int(act.frame_range[1])
    scene.frame_set(scene.frame_start)
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(filepath=CLIP_FBX, object_types={"ARMATURE"}, bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
                             bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True, bake_anim_step=1, bake_anim_simplify_factor=0, **EXPORT_SETTINGS)
    log("clip fbx", CLIP_FBX, os.path.getsize(CLIP_FBX), "frames", scene.frame_start, scene.frame_end)


# ---------------------------------------------------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------------------------------------------------
def write_gates(res, sheet):
    a_ = res["a_grip_contact"]
    a_["passed"] = bool(a_["right"]["palm_cm"] <= 8.0 and a_["left"]["palm_cm"] <= 8.0)
    a_["rule"] = "palm centre (halfway from the wrist to the middle knuckle, on the palm surface) within 8 cm of each rim point; the nearest fingertip is listed too"

    def mark(t):
        f = int(round(fr(t)))
        return dict(t=t, blender_frame=f, clip_frame_0based=f - F0)
    g = dict(task="P17-3 Blender part", clip="AN_Warden_MaskLift", source="SourceArt/Warden/P17/Warden_MaskLift.blend (copy of V11_1w)",
             length=dict(seconds=DUR, fps=FPS, blender_frames=[F0, FN], clip_frames=FN - F0 + 1),
             beats=dict(rise_to_rims=[0.0, T_RISE], grip_curl=[T_GRIP0, T_GRIP], lift=[T_GRIP, T_LIFT], lean_and_extend=[T_LIFT, T_EXT], hold_settle=[T_EXT, T_END]),
             grip=mark(T_GRIP), lifted=mark(T_LIFT), extended=mark(T_EXT), mid_lean=mark(T_MID), end=mark(T_END),
             params=dict(lean_deg=LEAN, settle_lean_deg=SETTLE_LEAN, settle_down_cm=SETTLE_DOWN * 100, lift_forward_cm=LIFT_FWD * 100, lift_up_cm=LIFT_UP * 100,
                         eye_height_cm=EYE_Z * 100, target_reach_cm=REACH * 100),
             a_grip_contact=a_, b_root="pending (run --verify)",
             c_clearance=dict(contact_sheet=os.path.relpath(sheet, ROOT).replace("\\", "/"), numeric=res["clearance"],
                              note="numeric = skin vertices of the forearms and hands against the wool (hood, cape, robe) on the 6 sheet frames; frame 0 (Idle) is the baseline. The verdict needs the owner's eyes"),
             d_reach=res["d_reach"], lifted_check=res["lifted"], carry=res["carry"], arm_stats=res["arm_stats"], forearm_twist_deg_max=res["solver_forearm_twist_total_deg_max"])
    gp = os.path.join(CINE_DIR, "p17_masklift_gates.json")
    os.makedirs(CINE_DIR, exist_ok=True)
    json.dump(g, open(gp, "w", encoding="utf-8"), indent=1)
    log("gates", gp)


def main():
    if OPT.get("export"):
        export_all()
        return
    act, ctx, logs = build()
    if FINAL:
        save_blend()
    res, helper, cen = measure(ctx, act)
    res["arm_stats"] = arm_stats(ctx)
    res["arm_stats"]["clamped_max_cm"] = round(max((l[1][s]["clamped"] for l in logs for s in l[1]), default=0) * 100, 2)
    res["solver_forearm_twist_total_deg_max"] = {s: round(max(abs(l[1][s]["tau"]) for l in logs), 1) for s in ("r", "l")}
    marks = [("0", 0.0), ("grip", T_GRIP), ("lifted", T_LIFT), ("mid-lean", T_MID), ("extended", T_EXT), ("end", T_END)]
    f_marks = [(l, int(round(fr(t)))) for l, t in marks]
    res["clearance"] = clearance(ctx, f_marks)
    print("RESULT|" + json.dumps(res, indent=1))
    sheet = os.path.join(CINE_DIR, "p17_masklift_contact.png") if FINAL else os.path.join(SCRATCH, "sheet.png")
    if not OPT.get("nosheet"):
        cam, body, pm = setup_render()
        paths = render_panels(cam, pm, helper, ctx, f_marks, "p", SCRATCH)
        make_sheet(paths, sheet, {})
        if OPT.get("closeup"):
            closeups(cam, pm, helper)
        if OPT.get("extra"):
            ex = [("t0.5", int(fr(0.5))), ("t0.9", int(fr(0.9))), ("t1.3", int(fr(1.3))), ("t1.5", int(fr(1.5))), ("t2.8", int(fr(2.8))), ("t5.3", int(fr(5.3)))]
            make_sheet(render_panels(cam, pm, helper, ctx, ex, "x", SCRATCH), os.path.join(SCRATCH, "sheet_extra.png"), {})
    if FINAL:
        write_gates(res, sheet)


main()
