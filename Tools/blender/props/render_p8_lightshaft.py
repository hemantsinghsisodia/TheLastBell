"""render_p8_lightshaft.py -- P8-9a review renders of the two light-shaft cards in context (Workbench).  Writes Docs/ArtTest/props/p8_lightshaft_*.png.

    blender.exe -b --factory-startup --python Tools/blender/props/render_p8_lightshaft.py -- [--blend SourceArt/Props/Procedural/LB_Props_P8_9a.blend]

Context geometry is a proxy (nothing here is exported): a 60 cm wall with the lancet opening, the floor, and for the roof the real
RoofSlab_Broken placed like Ch_Roof_S1, a north wall and the floor.  The shafts are drawn semi-transparent at their real placement
(lancet: bottom-centre at the window plane, local frame == world frame at yaw 0; roof hole: at its recorded pivot, zero rotation).
"""
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "kit")))
sys.path.insert(0, HERE)
import kit_lib as K  # noqa: E402
import render_kit as RK  # noqa: E402
import build_props as BP  # noqa: E402  (imports only; run() is guarded)

ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(ROOT, "Docs", "ArtTest", "props")
BLEND = os.path.join(ROOT, "SourceArt", "Props", "Procedural", "LB_Props_P8_9a.blend")
KIT_BLEND = os.path.join(ROOT, "SourceArt", "Kit", "LB_Kit_P8.blend")


def mat(name, rgba, transparent=False):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = rgba
    m.roughness = 0.9
    return m


def mesh_obj(name, bm, m, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    return ob


def look(cam, loc, target):
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()


def shot(sc, cam, name, loc, target, lens=35.0, hide=()):
    cam.data.lens = lens
    look(cam, loc, target)
    for o in bpy.data.objects:
        o.hide_render = o.name in hide
    sc.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", sc.render.filepath)


def main():
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    sc = bpy.context.scene
    RK.setup_render(sc, 1600, 900)
    sc.display.shading.show_shadows = False
    cam = RK.make_camera(sc)
    shaft_mat = mat("rv_shaft", (0.45, 0.70, 1.0, 0.45))
    stone = mat("rv_stone", (0.55, 0.54, 0.51, 1.0))
    floor_m = mat("rv_floor", (0.33, 0.31, 0.29, 1.0))
    lan = bpy.data.objects["SM_LB_Prop_LightShaft_Lancet"]
    roof = bpy.data.objects["SM_LB_Prop_LightShaft_RoofHole"]
    for o in (lan, roof):
        o.data.materials.clear()
        o.data.materials.append(shaft_mat)
        o.show_transparent = True
    # ---------------------------------------------------------------- lancet context (window plane = local Y 0, wall Y -21..39, sill Z 450 -> local 0)
    lan.location = (0.0, 0.0, 450.0)
    wall = K.box(-600.0, 600.0, -21.0, 39.0, 0.0, 1200.0, 0, 0.0)
    hole = K.prism([(x, z + 450.0) for (x, z) in BP.lancet_poly(140.0, 560.0)], 'y', -40.0, 60.0, 0)
    wall = BP.bool_op(wall, hole, 'DIFFERENCE')
    hole.free()
    w_ob = mesh_obj("ctx_wall", wall, stone)
    fl = K.box(-700.0, 1800.0, -1400.0, 1500.0, -4.0, 0.0, 0, 0.0)
    f_ob = mesh_obj("ctx_floor", fl, floor_m)
    bpy.context.view_layer.update()
    ctx = ("ctx_wall", "ctx_floor")
    hide_roof = (roof.name,)
    shot(sc, cam, "p8_lightshaft_lancet_inside", (-700.0, 2300.0, 800.0), (450.0, 150.0, 300.0), 28.0, hide_roof)
    shot(sc, cam, "p8_lightshaft_lancet_side", (-3200.0, 400.0, 600.0), (400.0, 400.0, 330.0), 30.0, hide_roof)
    shot(sc, cam, "p8_lightshaft_lancet_top", (520.0, 400.0, 3400.0), (520.0, 400.0, 0.0), 28.0, hide_roof)
    d = BP.moon_dir()
    shot(sc, cam, "p8_lightshaft_lancet_axis", Vector((0.0, 0.0, 700.0)) + d * 2600.0, (0.0, 0.0, 700.0), 30.0, hide_roof)
    # ---------------------------------------------------------------- roof context (world frame)
    for nm in ctx:
        bpy.data.objects[nm].hide_render = True
    for nm in ctx:
        bpy.data.objects.remove(bpy.data.objects[nm])
    lan.hide_render = True
    bpy.ops.wm.append(directory=KIT_BLEND + "/Object/", filename="SM_LB_Kit_RoofSlab_1000x1322x20_Broken")
    slab = bpy.data.objects["SM_LB_Kit_RoofSlab_1000x1322x20_Broken"]
    slab.data.materials.clear()
    slab.data.materials.append(mat("rv_slate", (0.20, 0.21, 0.25, 1.0)))
    slab.data.materials.append(mat("rv_wood", (0.34, 0.24, 0.15, 1.0)))
    xa, ya, za = BP.ue_axes(*BP.ROOF_S1_ROT)
    from mathutils import Matrix
    m = Matrix(((xa.x, ya.x, za.x, BP.ROOF_S1_LOC[0]), (xa.y, ya.y, za.y, BP.ROOF_S1_LOC[1]), (xa.z, ya.z, za.z, BP.ROOF_S1_LOC[2]), (0, 0, 0, 1)))
    slab.parent = None
    slab.matrix_world = m
    pv = roof_pivot()
    roof.location = pv
    fl = K.box(5900.0, 9100.0, -900.0, 900.0, -4.0, 0.0, 0, 0.0)
    mesh_obj("ctx_floor2", fl, floor_m)
    nw = K.box(6000.0, 9000.0, 750.0, 810.0, 0.0, 1200.0, 0, 0.0)
    mesh_obj("ctx_nwall", nw, stone)
    sw = K.box(6000.0, 9000.0, -810.0, -750.0, 0.0, 1200.0, 0, 0.0)
    mesh_obj("ctx_swall", sw, stone)
    gw = K.box(5940.0, 6000.0, -810.0, 810.0, 0.0, 1200.0, 0, 0.0)
    mesh_obj("ctx_wwall", gw, stone)
    bpy.context.view_layer.update()
    roof.hide_render = False
    hide_lan = (lan.name,)
    shot(sc, cam, "p8_lightshaft_roof_inside", (5600.0, 600.0, 500.0), (7300.0, -150.0, 900.0), 24.0, hide_lan + ("ctx_wwall",))
    shot(sc, cam, "p8_lightshaft_roof_outside", (7400.0, -5200.0, 1500.0), (7400.0, 0.0, 1100.0), 30.0, hide_lan + ("ctx_swall",))
    shot(sc, cam, "p8_lightshaft_roof_top", (7500.0, 0.0, 9000.0), (7500.0, 0.0, 0.0), 45.0, hide_lan + ("ctx_wwall",))
    shot(sc, cam, "p8_lightshaft_roof_axis", pv + d * 5200.0, pv, 28.0, hide_lan + ("ctx_wwall", "ctx_swall"))


def roof_pivot():
    """World pivot recorded by build_props (props_report_P8_9a.json) -> recomputed here from the same functions."""
    full, _p1, _p2 = BP.roof_hole_outline()
    simp = BP.simplify_closed(full, 16, 10)
    cen = BP.poly_centroid(simp)
    xa, ya, za = BP.ue_axes(*BP.ROOF_S1_ROT)
    return Vector(BP.ROOF_S1_LOC) + xa * cen[0] + ya * cen[1] + za * BP.ROOF_HOLE_Z


if __name__ == "__main__":
    main()
