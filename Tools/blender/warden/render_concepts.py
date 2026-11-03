"""render_concepts.py -- P12-3: renders and sheets for the three Warden concept blockouts.

Render (Blender, Cycles CPU only -- D-053: Unreal is open on a 6 GB card):
    blender.exe -b --factory-startup --python Tools/blender/warden/render_concepts.py -- [--only a b c] [--rows 1 2 3 4 5]
                [--views name ...] [--quick] [--out SourceArt/Warden/concepts/renders]
Sheets (plain Python + Pillow, no Blender):
    python Tools/blender/warden/render_concepts.py --sheet [--src SourceArt/Warden/concepts/renders]

Per concept (1024 x 1024, 64 samples, denoised, black background):
  row 1  front / three-quarter / side, neutral soft light
  row 2  pure black silhouette on mid grey, same three angles
  row 3  the same angles lit by a warm candle (2700 K, 2.5 m in front, 120 cm high) with a cold rim light from behind
  row 4  scale: beside a 180 cm human proxy; standing in a 104 x 230 door frame
  row 5  mask close-up, front and three-quarter, in the candle light and in neutral light
The light rig is camera relative: the candle is where the player stands (the camera sits just behind it).
"""
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SRC = os.path.join(ROOT, "SourceArt", "Warden", "concepts")
RENDERS = os.path.join(SRC, "renders")
DOCS = os.path.join(ROOT, "Docs", "ArtTest", "warden")
REPORT = os.path.join(DOCS, "p12_concepts_report.json")

NAMES = {"a": "A The Penitent", "b": "B The Bell-Bearer", "c": "C The Veiled Saint"}
AZ = {"front": 0.0, "3q": 38.0, "side": 90.0}
FIG_TARGET = (0.0, -4.0, 130.0)
CANDLE_DIST = 250.0        # from the figure origin, along the camera direction
CANDLE_Z = 120.0
EYE_Z = 165.0              # the player's eye height


# ----------------------------------------------------------------------------------------------------------------------
def render_main():
    import bpy
    import numpy as np
    from mathutils import Matrix, Vector

    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"only": ["a", "b", "c"], "rows": [1, 2, 3, 4, 5], "views": [], "quick": False, "out": RENDERS, "samples": 64, "size": 1024,
            "candle": 1.0}
    i = 0
    while i < len(argv):
        k = argv[i]
        if k in ("--only", "--rows", "--views"):
            key = k[2:]
            vals = []
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                vals.append(int(argv[i]) if key == "rows" else argv[i].lower())
                i += 1
            opts[key] = vals
            continue
        if k == "--quick":
            opts["quick"] = True
        elif k == "--out":
            opts["out"] = os.path.abspath(argv[i + 1])
            i += 1
        elif k == "--samples":
            opts["samples"] = int(argv[i + 1])
            i += 1
        elif k == "--size":
            opts["size"] = int(argv[i + 1])
            i += 1
        elif k == "--candle":
            opts["candle"] = float(argv[i + 1])
            i += 1
        i += 1
    if opts["quick"]:
        opts["samples"] = min(opts["samples"], 24)
        opts["size"] = min(opts["size"], 512)

    report = json.load(open(REPORT)) if os.path.exists(REPORT) else {}

    def setup_render(sc):
        sc.render.engine = "CYCLES"
        sc.cycles.device = "CPU"
        sc.cycles.samples = opts["samples"]
        sc.cycles.use_adaptive_sampling = True
        sc.cycles.use_denoising = True
        try:
            sc.cycles.denoiser = "OPENIMAGEDENOISE"
            sc.cycles.denoising_use_gpu = False
        except Exception:
            pass
        sc.cycles.max_bounces = 6
        sc.render.resolution_x = opts["size"]
        sc.render.resolution_y = opts["size"]
        sc.render.resolution_percentage = 100
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.color_mode = "RGB"
        sc.render.threads_mode = "FIXED"
        sc.render.threads = 12
        sc.render.film_transparent = False
        try:
            sc.view_settings.view_transform = "Standard"
            sc.view_settings.look = "None"
        except Exception as e:
            print("view transform:", e)
        sc.view_settings.exposure = 0.0

    def set_world(sc, colour):
        w = sc.world or bpy.data.worlds.new("W")
        sc.world = w
        if not w.use_nodes:
            w.use_nodes = True
        bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
        bg.inputs["Color"].default_value = (colour[0], colour[1], colour[2], 1.0)
        bg.inputs["Strength"].default_value = 1.0

    def dirvec(az):
        a = math.radians(az)
        return Vector((math.sin(a), -math.cos(a), 0.0))

    def add_cam(sc, pos, target, lens=85.0):
        cd = bpy.data.cameras.new("cam")
        cd.lens = lens
        cd.clip_start = 5.0
        cd.clip_end = 5000.0
        co = bpy.data.objects.new("cam", cd)
        sc.collection.objects.link(co)
        co.location = pos
        d = Vector(target) - Vector(pos)
        co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        sc.camera = co
        return co

    def mk_mat(name, col, rough=0.8, metal=0.0):
        m = bpy.data.materials.new(name)
        if not m.use_nodes:
            m.use_nodes = True
        b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = (col[0], col[1], col[2], 1)
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = metal
        return m

    def add_light(sc, kind, pos, target, power, colour, size=1.0, spot=None):
        ld = bpy.data.lights.new(kind, kind)
        ld.energy = power
        ld.color = colour
        if kind == "AREA":
            ld.shape = "SQUARE"
            ld.size = size
        elif kind == "POINT":
            ld.shadow_soft_size = size
        elif kind == "SPOT":
            ld.shadow_soft_size = size
            ld.spot_size = math.radians(spot or 60)
            ld.spot_blend = 0.5
        lo = bpy.data.objects.new(kind, ld)
        sc.collection.objects.link(lo)
        lo.location = pos
        d = Vector(target) - Vector(pos)
        lo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        return lo

    TEMP = []

    def temp(ob):
        TEMP.append(ob)
        return ob

    def cleanup():
        for ob in TEMP:
            try:
                data = ob.data
                bpy.data.objects.remove(ob, do_unlink=True)
                if data is not None and data.users == 0:
                    if isinstance(data, bpy.types.Light):
                        bpy.data.lights.remove(data)
                    elif isinstance(data, bpy.types.Camera):
                        bpy.data.cameras.remove(data)
                    elif isinstance(data, bpy.types.Mesh):
                        bpy.data.meshes.remove(data)
            except Exception:
                pass
        TEMP.clear()

    S = 1.0e4        # lights are specified in "metre" watts and scaled: the scene is in centimetres
    CANDLE_COL = (1.0, 0.40, 0.10)
    COLD_COL = (0.62, 0.74, 1.0)

    def floor(sc, col=(0.05, 0.047, 0.045)):
        bpy.ops.mesh.primitive_circle_add(vertices=64, radius=900, fill_type="NGON", location=(0, 0, -0.05))
        o = bpy.context.active_object
        o.data.materials.append(mk_mat("floor", col, 0.9))
        temp(o)
        return o

    def rig_neutral(sc, az, strength=1.0):
        d = dirvec(az)
        t = Vector(FIG_TARGET)

        def at(deg, elev, dist):
            a = math.radians(az + deg)
            e = math.radians(elev)
            return Vector((math.sin(a) * math.cos(e) * dist, -math.cos(a) * math.cos(e) * dist, math.sin(e) * dist + 130))
        temp(add_light(sc, "AREA", at(-40, 40, 520), t, 900 * S * strength, (1.0, 0.97, 0.92), 320))
        temp(add_light(sc, "AREA", at(65, 15, 520), t, 260 * S * strength, (0.86, 0.9, 1.0), 320))
        temp(add_light(sc, "AREA", at(180 - 30, 35, 520), t, 520 * S * strength, (0.8, 0.88, 1.0), 260))
        temp(add_light(sc, "AREA", at(0, 80, 500), t, 220 * S * strength, (1.0, 1.0, 1.0), 300))

    def rig_candle(sc, az, strength=1.0):
        d = dirvec(az)
        cp = d * CANDLE_DIST
        cp.z = CANDLE_Z
        temp(add_light(sc, "POINT", cp, Vector(FIG_TARGET), opts["candle"] * 130.0 * S * strength, CANDLE_COL, 1.2))
        # cold rim light from behind, both sides, aimed at the upper body
        for deg in (-32, 32):
            a = math.radians(az + 180 + deg)
            rp = Vector((math.sin(a) * 230, -math.cos(a) * 230, 270))
            temp(add_light(sc, "SPOT", rp, Vector((0, -20, 190)), 150 * S * strength, COLD_COL, 14, spot=55))

    def silhouette_on(sc, on):
        vl = bpy.context.view_layer
        if on:
            if "sil_black" not in bpy.data.materials:
                m = bpy.data.materials.new("sil_black")
                if not m.use_nodes:
                    m.use_nodes = True
                nt = m.node_tree
                for n in list(nt.nodes):
                    nt.nodes.remove(n)
                em = nt.nodes.new("ShaderNodeEmission")
                em.inputs["Color"].default_value = (0, 0, 0, 1)
                em.inputs["Strength"].default_value = 0.0
                out = nt.nodes.new("ShaderNodeOutputMaterial")
                nt.links.new(em.outputs[0], out.inputs[0])
            vl.material_override = bpy.data.materials["sil_black"]
        else:
            vl.material_override = None

    def do_render(sc, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        sc.render.filepath = path
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        dt = time.time() - t0
        print("RENDERED", os.path.basename(path), "%.1fs" % dt)
        return dt

    def human_proxy(x, y):
        parts = []
        mat = mk_mat("human", (0.22, 0.22, 0.24), 0.8)

        def prim(kind, loc, scale, rot=(0, 0, 0)):
            if kind == "sphere":
                bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1, location=loc)
            else:
                bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=1, depth=1, location=loc)
            o = bpy.context.active_object
            o.scale = scale
            o.rotation_euler = rot
            o.data.materials.append(mat)
            bpy.ops.object.shade_smooth()
            temp(o)
            parts.append(o)
        # 180 cm: feet 0, head top 180
        for sx in (-1, 1):
            prim("cyl", (x + 10 * sx, y, 46), (6.5, 6.5, 92))              # legs
            prim("cyl", (x + 25 * sx, y, 112), (4.8, 4.8, 66))                # arms
        prim("cyl", (x, y, 120), (17, 11, 62))                           # torso
        prim("sphere", (x, y, 152), (19, 12, 14))                         # shoulders
        prim("cyl", (x, y, 164), (5, 5, 10))                             # neck
        prim("sphere", (x, y, 172), (9, 10.5, 12))                        # head
        return parts

    def door_frame(sc, y0=6.0, thick=20.0):
        mat = mk_mat("wall", (0.16, 0.15, 0.14), 0.9)
        trim = mk_mat("trim", (0.30, 0.28, 0.25), 0.8)

        def box(c, s, m):
            bpy.ops.mesh.primitive_cube_add(size=1, location=c)
            o = bpy.context.active_object
            o.scale = s
            o.data.materials.append(m)
            temp(o)
        yc = y0 + thick / 2
        W, Hh = 104.0, 230.0
        wall_w, wall_h = 220.0, 330.0
        box((-(W / 2 + wall_w / 2), yc, wall_h / 2), (wall_w, thick, wall_h), mat)
        box(((W / 2 + wall_w / 2), yc, wall_h / 2), (wall_w, thick, wall_h), mat)
        box((0, yc, Hh + (wall_h - Hh) / 2), (W, thick, wall_h - Hh), mat)
        # plain trim
        box((-(W / 2 + 4), yc - 2, Hh / 2), (8, thick + 4, Hh + 8), trim)
        box(((W / 2 + 4), yc - 2, Hh / 2), (8, thick + 4, Hh + 8), trim)
        box((0, yc - 2, Hh + 4), (W + 16, thick + 4, 8), trim)

    # ------------------------------------------------------------------------------------------------------------------
    for ck in opts["only"]:
        blend = os.path.join(SRC, "concept_%s.blend" % ck)
        bpy.ops.wm.open_mainfile(filepath=blend)
        sc = bpy.context.scene
        setup_render(sc)
        rep = report.get(ck, {})
        mw = rep.get("mask_centre_world", [0, -60, 232])
        mask_pos = Vector(mw)
        out_dir = os.path.join(opts["out"], ck)
        total = 0.0

        def want(row, name):
            if row not in opts["rows"]:
                return False
            return not opts["views"] or name in opts["views"]

        # ---- row 1: neutral
        for nm, az in AZ.items():
            name = "r1_%s" % nm
            if not want(1, name):
                continue
            set_world(sc, (0, 0, 0))
            floor(sc)
            rig_neutral(sc, az)
            pos = Vector(FIG_TARGET) + dirvec(az) * 700
            temp(add_cam(sc, pos, FIG_TARGET))
            total += do_render(sc, os.path.join(out_dir, name + ".png"))
            cleanup()
        # ---- row 2: silhouettes
        for nm, az in AZ.items():
            name = "r2_%s" % nm
            if not want(2, name):
                continue
            set_world(sc, (0.214, 0.214, 0.214))
            silhouette_on(sc, True)
            pos = Vector(FIG_TARGET) + dirvec(az) * 700
            temp(add_cam(sc, pos, FIG_TARGET))
            total += do_render(sc, os.path.join(out_dir, name + ".png"))
            cleanup()
            silhouette_on(sc, False)
        # ---- row 3: candle
        for nm, az in AZ.items():
            name = "r3_%s" % nm
            if not want(3, name):
                continue
            set_world(sc, (0, 0, 0))
            floor(sc)
            rig_candle(sc, az)
            pos = Vector(FIG_TARGET) + dirvec(az) * 700
            temp(add_cam(sc, pos, FIG_TARGET))
            total += do_render(sc, os.path.join(out_dir, name + ".png"))
            cleanup()
        # ---- row 4: scale
        if want(4, "r4_human"):
            set_world(sc, (0, 0, 0))
            floor(sc, (0.08, 0.075, 0.07))
            rig_neutral(sc, 0.0)
            human_proxy(112.0, -14.0)
            temp(add_cam(sc, (50, -820, 125), (50, 0, 125)))
            total += do_render(sc, os.path.join(out_dir, "r4_human.png"))
            cleanup()
        if want(4, "r4_door"):
            set_world(sc, (0, 0, 0))
            floor(sc, (0.08, 0.075, 0.07))
            rig_neutral(sc, 0.0)
            door_frame(sc)
            temp(add_cam(sc, (0, -820, 150), (0, 0, 150)))
            total += do_render(sc, os.path.join(out_dir, "r4_door.png"))
            cleanup()
        # ---- row 5: mask close-ups (candle, then neutral)
        for light in ("candle", "neutral"):
            for nm, az in (("front", 0.0), ("3q", 38.0)):
                name = "r5_%s_%s" % (nm, light)
                if not want(5, name):
                    continue
                set_world(sc, (0, 0, 0))
                floor(sc)
                if light == "candle":
                    rig_candle(sc, az)
                else:
                    rig_neutral(sc, az)
                d = dirvec(az)
                pos = Vector((mask_pos.x, mask_pos.y, 0)) + d * 205
                pos.z = EYE_Z
                tgt = mask_pos + Vector((0, 0, 8))
                temp(add_cam(sc, pos, tgt, lens=85.0))
                total += do_render(sc, os.path.join(out_dir, name + ".png"))
                cleanup()
        print("TOTAL_RENDER_TIME", ck, "%.1fs" % total)


# ----------------------------------------------------------------------------------------------------------------------
def sheet_main():
    from PIL import Image, ImageDraw, ImageFont
    argv = sys.argv[1:]
    src = RENDERS
    if "--src" in argv:
        src = os.path.abspath(argv[argv.index("--src") + 1])
    os.makedirs(DOCS, exist_ok=True)

    def font(sz):
        for f in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
            try:
                return ImageFont.truetype(f, sz)
            except Exception:
                continue
        return ImageFont.load_default()

    ROWS = [
        ("1  Neutral soft light:  front / three-quarter / side", ["r1_front", "r1_3q", "r1_side"], "fig"),
        ("2  Silhouette:  the same three angles", ["r2_front", "r2_3q", "r2_side"], "fig"),
        ("3  Candle 2700 K, 2.5 m in front, 120 cm high, cold rim from behind", ["r3_front", "r3_3q", "r3_side"], "fig"),
        ("4  Scale:  beside a 180 cm human  /  in a 104 x 230 door frame", ["r4_human", "r4_door"], "wide"),
        ("5a  Mask close-up, candle light:  front / three-quarter", ["r5_front_candle", "r5_3q_candle"], "close"),
        ("5b  Mask close-up, neutral light:  front / three-quarter", ["r5_front_neutral", "r5_3q_neutral"], "close"),
    ]
    # crops of the 1024 square render, (left, top, right, bottom) in units of the image size
    CROP = {"fig": (0.205, 0.0, 0.795, 1.0), "wide": (0.12, 0.0, 0.88, 1.0), "close": (0.12, 0.06, 0.88, 0.94)}

    def load(ck, nm, kind):
        p = os.path.join(src, ck, nm + ".png")
        if not os.path.exists(p):
            return None
        im = Image.open(p).convert("RGB")
        w, h = im.size
        l, t, r, b = CROP[kind]
        return im.crop((int(l * w), int(t * h), int(r * w), int(b * h)))

    def build(cks, col_w, gap, label_h, title_h, outpath, fonts):
        ftitle, frow = fonts
        rows_img = []
        for rt, names, kind in ROWS:
            per = []
            for ck in cks:
                ims = [load(ck, n, kind) for n in names]
                ims = [im for im in ims if im is not None]
                if not ims:
                    per.append(None)
                    continue
                cw = (col_w - gap * (len(names) - 1)) // len(names)
                scaled = []
                for im in ims:
                    sc_ = cw / im.size[0]
                    scaled.append(im.resize((cw, int(im.size[1] * sc_)), Image.LANCZOS))
                per.append(scaled)
            rows_img.append((rt, per))
        # row heights
        heights = []
        for rt, per in rows_img:
            heights.append(max([max(i.size[1] for i in p) for p in per if p] or [0]))
        ncol = len(cks)
        W = ncol * col_w + (ncol + 1) * gap * 2
        H = title_h + sum(heights) + len(ROWS) * (label_h + gap) + gap * 2
        sheet = Image.new("RGB", (W, H), (10, 10, 10))
        d = ImageDraw.Draw(sheet)
        for ci, ck in enumerate(cks):
            x0 = gap * 2 + ci * (col_w + gap * 2)
            d.text((x0, title_h // 4), NAMES[ck], fill=(235, 225, 200), font=ftitle)
        y = title_h
        for (rt, per), hrow in zip(rows_img, heights):
            d.text((gap * 2, y + 2), rt, fill=(170, 160, 140), font=frow)
            y += label_h
            for ci, p in enumerate(per):
                if not p:
                    continue
                x = gap * 2 + ci * (col_w + gap * 2)
                for im in p:
                    sheet.paste(im, (x, y))
                    x += im.size[0] + gap
            y += hrow + gap
        sheet.save(outpath, optimize=True)
        print("SHEET", outpath, sheet.size)

    build(["a", "b", "c"], 760, 8, 30, 64, os.path.join(DOCS, "p12_concepts.png"), (font(40), font(20)))
    for ck in ("a", "b", "c"):
        build([ck], 1900, 12, 44, 80, os.path.join(DOCS, "p12_concept_%s.png" % ck), (font(56), font(32)))


if __name__ == "__main__":
    try:
        import bpy  # noqa: F401
        HAVE_BPY = True
    except ImportError:
        HAVE_BPY = False
    if HAVE_BPY:
        render_main()
    else:
        sheet_main()
