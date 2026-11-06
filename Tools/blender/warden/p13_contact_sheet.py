"""p13_contact_sheet.py -- P13-5: contact sheets of the 12 retargeted Warden clips (UE exports in SourceArt/Warden/P13_review).

    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --factory-startup --python Tools/blender/warden/p13_contact_sheet.py -- [options]
      --clips all|A,B,..   clip names without the AN_Warden_ prefix (default all)
      --out DIR            default Docs/ArtTest/warden
      --tmp DIR            panel PNGs + meta.json (default <out>/_panels, deleted afterwards unless --keep)
      --python EXE         a Python with Pillow, used to draw labels and height lines and to assemble the sheets (default: the Python 3.14 install)
      --samples N          Cycles samples per panel (default 24)
      --res N              panel size in px (default 560)
      --keep               keep the panel PNGs
      --rest               show the armature's rest pose instead of the animation (checks the mesh/armature assembly)

Never saves a .blend. Nothing is read from or written to Unreal.

What it builds per clip (a fresh empty scene each time):
  * the animation FBX from Unreal (armature only; since P13-4b there is no root key) and the Warden mesh from the P12 source FBX
    (SourceArt/Warden/V5_5/exports/SK_Warden_LOD0.fbx; the Unreal preview-mesh export asserts under -nullrhi). The mesh is parented to the clip's
    armature and turned +90 deg about Z, which maps the mesh's Blender authoring frame onto the frame the Unreal-exported skeleton uses (the bone
    rest positions match; checked in the probe, see the report). In that frame the Warden faces +X and its left side is +Y (Y is mirrored by the
    FBX handedness conversion).
  * flat grey on every slot, a lighter grey on the mask (slot M_Warden_BellMetal), a floor at Z 0 and two backdrop walls with a 50 cm grid, three
    suns (key, fill, rim) + a little world light, Cycles on CPU.
  * orthographic cameras: FRONT looks at the mask from +X (the side it faces), SIDE looks from -Y so the Warden faces image-right.
  * frames at 0, 25, 50 and 75 % of the clip, 8 panels per clip. The height lines (red 220 cm, blue 290 cm) are exact in orthographic view and are
    drawn by the composer.
"""
import json
import math
import os
import subprocess
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
REVIEW = os.path.join(ROOT, "SourceArt", "Warden", "P13_review")
MESH_FBX = os.path.join(ROOT, "SourceArt", "Warden", "V5_5", "exports", "SK_Warden_LOD0.fbx")
COMPOSER = os.path.join(ROOT, "Tools", "blender", "warden", "p13_sheet_compose.py")
PY = r"C:\Users\heman\AppData\Local\Python\pythoncore-3.14-64\python.exe"
CLIPS = ["MutantWalking", "ZombieWalk", "MutantRun", "ZombieRunning", "MutantIdle", "CrouchedWalking", "CrouchingIdle",
         "TurnLeft90", "TurnRight90", "ZombieAttack", "MutantSwiping", "LookAround"]
PCTS = [0, 25, 50, 75]
ZC, SCALE = 1.6, 3.4  # camera centre height (m) and orthographic scale (m): frames Z -0.1 .. 3.3
MASK_SLOT = "M_Warden_BellMetal"


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = {"clips": "all", "out": os.path.join(ROOT, "Docs", "ArtTest", "warden"), "tmp": None, "python": PY, "samples": 24, "res": 560, "keep": False, "rest": False}
    i = 0
    while i < len(a):
        if a[i] in ("--keep", "--rest"):
            o[a[i].lstrip("-")] = True
            i += 1
        else:
            o[a[i].lstrip("-")] = a[i + 1]
            i += 2
    o["samples"], o["res"] = int(o["samples"]), int(o["res"])
    o["tmp"] = o["tmp"] or os.path.join(o["out"], "_panels")
    return o


def log(*a):
    print("SHEET| " + " ".join(str(x) for x in a), flush=True)


def mat(name, rgb, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bs.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1)
    bs.inputs["Roughness"].default_value = rough
    return m


def grid_mesh(name, origin, u, v, size, step, width, rgb):
    """Thin-quad grid on the plane origin + a*u + b*v, a,b in [-size/2, size/2]; lines every `step` metres."""
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    n = int(size / step)
    for i in range(-n // 2, n // 2 + 1):
        t = i * step
        for (d1, d2) in ((u, v), (v, u)):
            p0 = origin + d1 * t - d2 * size / 2
            p1 = origin + d1 * t + d2 * size / 2
            w = d1 * width / 2
            vs = [bm.verts.new(p0 - w), bm.verts.new(p0 + w), bm.verts.new(p1 + w), bm.verts.new(p1 - w)]
            bm.faces.new(vs)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat(name + "_mat", rgb, 1.0))
    return ob


def plane(name, origin, u, v, size, rgb):
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    s = size / 2
    bm.faces.new([bm.verts.new(origin + u * -s + v * -s), bm.verts.new(origin + u * s + v * -s),
                  bm.verts.new(origin + u * s + v * s), bm.verts.new(origin + u * -s + v * s)])
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat(name + "_mat", rgb, 1.0))
    return ob


def sun(name, loc, strength, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, "SUN")
    ld.energy = strength
    ld.color = color
    ld.angle = math.radians(25)
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    c = ob.constraints.new("TRACK_TO")
    c.target = TARGET
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    return ob


def camera(name, loc):
    cd = bpy.data.cameras.new(name)
    cd.type = "ORTHO"
    cd.ortho_scale = SCALE
    cd.clip_end = 100
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    c = ob.constraints.new("TRACK_TO")
    c.target = TARGET
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    return ob


def build_scene(clip, res, samples):
    global TARGET
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.62, 0.64, 0.68, 1)
    bg.inputs["Strength"].default_value = 0.55
    sc.world = w
    TARGET = bpy.data.objects.new("target", None)
    sc.collection.objects.link(TARGET)
    TARGET.location = (0, 0, ZC)

    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=MESH_FBX)
    mesh_objs = set(bpy.data.objects) - before
    mesh = next(o for o in mesh_objs if o.type == "MESH")
    old_arm = next(o for o in mesh_objs if o.type == "ARMATURE")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(REVIEW, "AN_Warden_%s.fbx" % clip))
    arm = next(o for o in set(bpy.data.objects) - before if o.type == "ARMATURE")
    # the Unreal armature has no 'root' bone (the root node is the armature object, carrying the root yaw key): the mesh groups are all pelvis and below
    mesh.parent = None
    mesh.parent = arm
    mesh.matrix_parent_inverse = Matrix.Identity(4)
    mesh.location = (0, 0, 0)
    mesh.rotation_euler = (0, 0, math.radians(90))
    mesh.scale = (1, 1, 1)
    for m in mesh.modifiers:
        if m.type == "ARMATURE":
            m.object = arm
    bpy.data.objects.remove(old_arm, do_unlink=True)

    body = mat("body_grey", (0.32, 0.32, 0.34), 0.85)
    mask = mat("mask_light", (0.88, 0.86, 0.8), 0.6)
    slots = list(mesh.data.materials)
    for i, m in enumerate(slots):
        mesh.data.materials[i] = mask if (m is not None and m.name.split(".")[0] == MASK_SLOT) else body
    log("clip %s: mesh slots now %s" % (clip, [m.name for m in mesh.data.materials]))

    plane("floor", Vector((0, 0, 0)), Vector((1, 0, 0)), Vector((0, 1, 0)), 10, (0.50, 0.50, 0.50))
    grid_mesh("floor_grid", Vector((0, 0, 0.002)), Vector((1, 0, 0)), Vector((0, 1, 0)), 10, 0.5, 0.012, (0.26, 0.26, 0.26))
    # backdrop walls: behind the front view (x = -2.5, facing +X) and behind the side view (y = +2.5, facing -Y)
    plane("wall_x", Vector((-2.5, 0, 2.5)), Vector((0, 1, 0)), Vector((0, 0, 1)), 10, (0.60, 0.60, 0.60))
    grid_mesh("wall_x_grid", Vector((-2.498, 0, 2.5)), Vector((0, 1, 0)), Vector((0, 0, 1)), 10, 0.5, 0.012, (0.36, 0.36, 0.36))
    plane("wall_y", Vector((0, 2.5, 2.5)), Vector((1, 0, 0)), Vector((0, 0, 1)), 10, (0.60, 0.60, 0.60))
    grid_mesh("wall_y_grid", Vector((0, 2.498, 2.5)), Vector((1, 0, 0)), Vector((0, 0, 1)), 10, 0.5, 0.012, (0.36, 0.36, 0.36))
    sun("key", (4, 3, 5), 3.2, (1.0, 0.97, 0.92))
    sun("fill", (3, -4, 2.5), 1.3, (0.85, 0.9, 1.0))
    sun("rim", (-3, 0, 4), 2.2, (1, 1, 1))
    cams = {"FRONT": camera("cam_front", (6, 0, ZC)), "SIDE": camera("cam_side", (0, -6, ZC))}
    return sc, arm, cams


def main():
    o = args()
    clips = CLIPS if o["clips"] == "all" else o["clips"].split(",")
    os.makedirs(o["tmp"], exist_ok=True)
    meta = {"out": o["out"], "res": o["res"], "scale": SCALE, "zc": ZC, "pcts": PCTS, "clips": []}
    for clip in clips:
        sc, arm, cams = build_scene(clip, o["res"], o["samples"])
        if o["rest"]:
            arm.data.pose_position = "REST"
        act = arm.animation_data.action
        f0, f1 = act.frame_range
        sc.frame_start, sc.frame_end = int(f0), int(f1)
        fps = sc.render.fps
        length = (f1 - f0) / fps
        log("clip %s: action %s frames %d..%d (%.3f s at %d fps)" % (clip, act.name, f0, f1, length, fps))
        panels = []
        for view, cam in cams.items():
            sc.camera = cam
            for pct in PCTS:
                fr = int(round(f0 + (f1 - f0) * pct / 100.0))
                sc.frame_set(fr)
                fn = os.path.join(o["tmp"], "%s_%s_%03d.png" % (clip, view, pct))
                sc.render.filepath = fn
                bpy.ops.render.render(write_still=True)
                panels.append({"view": view, "pct": pct, "frame": fr, "t": round((fr - f0) / fps, 3), "file": fn})
                log("  rendered %s %s %d%% (frame %d)" % (clip, view, pct, fr))
        meta["clips"].append({"name": clip, "length_s": round(length, 3), "panels": panels})
    mp = os.path.join(o["tmp"], "meta.json")
    with open(mp, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
    cmd = [o["python"], "-I", COMPOSER, mp] + (["--keep"] if o["keep"] else [])
    log("composing:", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    log(r.stdout.strip())
    if r.returncode:
        log("composer failed:", r.stderr.strip())
        sys.exit(1)
    log("SHEET_DONE")


main()
