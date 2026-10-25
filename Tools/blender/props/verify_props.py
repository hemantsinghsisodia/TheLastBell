"""verify_props.py -- re-imports every procedural prop FBX in a clean headless Blender and checks it (P7F-2b).

    blender.exe -b --factory-startup --python Tools/blender/props/verify_props.py -- [--fbx SourceArt/Props/Procedural] [--json out.json]

Checks per piece (Unreal space: UE_Y = -Blender_Y of the re-imported file, see Tools/blender/kit/README.md):
  pivot bottom-centre (XY bounds centre at 0, min Z at 0, +-1 cm, node at the origin), dimensions vs the plan table
  (+-1 cm unless a tolerance is given), exact slot names/order, UCX count / naming UCX_<Mesh>_NN / convex / inside the
  visual bounds (+-1 cm; the key UCX is the one deliberate exception and must be exactly 17 x 7 x 12 cm, Z 0..12),
  vertex colour attribute present and white, UV layer, normals, positive volume, key-ledge flat centre at Z 70.
Exit code 1 if any check fails.
"""
import json
import os
import sys

import math

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "kit")))
import verify_kit as VK  # noqa: E402  (helpers only; importing builds nothing)

TOL = 1.0
P = "SM_LB_Prop_"
# name: dict(dims=(x, y, z) with None = unchecked, tol, slots, ucx)
SPEC = {
    "Key_Chapel": dict(dims=(15.6, 5.2, None), zmax=3.0, slots=["MAT_Iron"], ucx=1, ucx_env=(17.0, 7.0, 12.0)),
    "KeyLedge_50x50x70": dict(dims=(54.0, 54.0, 70.0), slots=["MAT_Trim"], ucx=1, ucx_env=(50.0, 50.0, 70.0)),
    "Gravestone_A": dict(dims=(60.0, 14.0, 95.0), slots=["MAT_Stone"], ucx=1),
    "Gravestone_B": dict(dims=(55.0, 14.0, 85.0), slots=["MAT_Stone"], ucx=1),
    "Gravestone_C": dict(dims=(60.0, 14.0, 45.0), slots=["MAT_Stone"], ucx=1),
    "Gravestone_C_Frag": dict(dims=(50.0, 14.0, 30.0), slots=["MAT_Stone"], ucx=1),
    "Gravestone_D": dict(dims=(35.0, 20.0, 45.0), slots=["MAT_Stone"], ucx=1),
    "StoneCross_A": dict(dims=(55.0, 30.0, 150.0), slots=["MAT_Stone"], ucx=3),     # Y 30 = base block; the cross itself is 18 deep
    "WoodCross_A": dict(dims=(55.0, 11.2, 120.0), slots=["MAT_Wood", "MAT_Rope"], ucx=2),   # Y 11.2 = rope rings (r 5 + tube)
    "GraveMound_A": dict(dims=(200.0, 90.0, 22.0), slots=["MAT_Earth"], ucx=0),
    "HandCart_A": dict(dims=(280.0, 140.0, 100.0), slots=["MAT_Wood", "MAT_Iron"], ucx=3),  # 170 bed + 110 shafts; wheels/axle set the width
    "FirePit_A": dict(dims=(125.0, 125.0, 31.0), tol=5.0, slots=["MAT_Stone", "MAT_Charred"], ucx=1),  # O110 stone-centre circle + 25-35 cm stones
    # ---- P7-FIX3 G2a ----
    "WellHead_A": dict(dims=(358.0, 258.0, 230.0), tol=2.5, slots=["MAT_Stone", "MAT_Wood", "MAT_Rope", "MAT_Iron", "MAT_Water"], ucx=10),  # ring O260, posts at +-152, cranks to +-179
    "TimberPost_20x20x420": dict(dims=(20.0, 20.0, 420.0), slots=["MAT_Wood"], ucx=1),
    "Purlin_15x15x1000": dict(dims=(15.0, 15.0, 1000.0), slots=["MAT_Wood"], ucx=0),
    "Rafter_15x10x420": dict(dims=(15.0, 10.0, 420.0), slots=["MAT_Wood"], ucx=0),
    "Rafter_Broken_15x10x260": dict(dims=(15.0, 10.0, 260.0), slots=["MAT_Wood"], ucx=0),
    "RoofPlanks_200x100x4": dict(dims=(200.0, 100.0, 4.0), slots=["MAT_Wood"], ucx=0),
    "RoofPlanks_Broken_200x100x4": dict(dims=(200.0, 100.0, 4.0), slots=["MAT_Wood"], ucx=0),
    "EarthPatch_400x400x15": dict(dims=(400.0, 400.0, 15.0), slots=["MAT_Earth"], ucx=1),
    "DeadTree_A": dict(dims=(None, None, 700.0), slots=["MAT_Bark"], ucx=1),              # 650-750 cm target, built to 700
}
# ---- P8-3 chapel props (plan section 2 P8-3 + amendment C1) ----
SPEC.update({
    "Truss_ArchBraced_1500": dict(dims=(26.2, 1500.0, 1265.0), tol=1.5, slots=["MAT_Wood"], ucx=0, struct="truss"),          # 25 thick + pegs, +-750 across, apex 1265 (world 2165)
    "Pew_A": dict(dims=(55.0, 250.0, 95.0), slots=["MAT_Wood"], ucx=2, struct="pew"),
    "Pew_Broken": dict(dims=(55.0, 250.0, 95.0), slots=["MAT_Wood"], ucx=3),
    "AltarRail_600x40x100": dict(dims=(40.0, 600.0, 100.0), slots=["MAT_Wood"], ucx=1),
    "Lectern_A": dict(dims=(56.0, 56.0, 125.0), slots=["MAT_Trim", "MAT_Wood"], ucx=2),
    "Altar_A": dict(dims=(104.0, 300.0, 101.0), slots=["MAT_Trim"], ucx=2, struct="altar"),
    "MechShell_Cyl": dict(dims=(84.0, 84.0, 51.0), slots=["MAT_Trim"], ucx=0, struct="shell_cyl"),
    "MechShell_Cube": dict(dims=(17.0, 17.0, 17.0), slots=["MAT_Trim"], ucx=0),
    "SlateShards_A": dict(dims=(120.0, 90.0, None), slots=["MAT_Slate"], ucx=0),
    "CrossFinial_A": dict(dims=(60.0, 25.0, 130.0), slots=["MAT_Trim"], ucx=0),
    "Backdrop_Plane_800x850": dict(dims=(0.0, 800.0, 850.0), slots=["MAT_Backdrop"], ucx=0, open_mesh=True, struct="backdrop"),
    "Glass_Lancet_140x560": dict(dims=(140.0, 1.0, 560.0), slots=["MAT_Glass"], ucx=0, uv01=True),
    "Glass_Lancet_Broken": dict(dims=(140.0, 1.0, None), zmax=450.0, slots=["MAT_Glass"], ucx=0, uv01=True),
    "Glass_East": dict(dims=(300.0, 1.0, None), zmax=540.0, slots=["MAT_Glass"], ucx=0, uv01=True),
    "Glass_Clue_Ext": dict(dims=(100.0, 1.0, 220.2), slots=["MAT_Glass"], ucx=0, uv01=True),
    "Cobweb_Corner_A": dict(dims=(120.0, 120.0, 120.0), slots=["MAT_Cobweb"], ucx=0, open_mesh=True, uv01=True),
    "Cobweb_Hang_A": dict(dims=(150.0, 12.0, 80.0), slots=["MAT_Cobweb"], ucx=0, open_mesh=True, uv01=True),
    "PricketStand_Small_10x30": dict(dims=(10.0, 10.0, 30.0), tol=0.5, slots=["MAT_Iron"], ucx=1, ucx_env=(10.0, 10.0, 30.0)),
    "PricketStand_150": dict(dims=(42.0, 39.0, 150.0), slots=["MAT_Iron"], ucx=1),
    "CandleFlame_A": dict(dims=(3.0, 3.0, 6.5), tol=0.5, slots=["MAT_Flame"], ucx=0),
})
for _shape, _w, _h in (("Climb", 300.0, 450.0), ("Patch", 200.0, 300.0), ("Hang", 150.0, 600.0), ("Creep", 400.0, 200.0)):
    for _kind in ("Green", "Dead"):
        SPEC["Ivy_%s_%gx%g_%s" % (_shape, _w, _h, _kind)] = dict(dims=(_w, None, _h), ymax=25.0, slots=["MAT_Leaf", "MAT_Stem"], ucx=0,
                                                                 wall_pivot=True, open_mesh=True, subdir="Ivy")


def parse():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    fbx = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SourceArt", "Props", "Procedural"))
    js = None
    for i, a in enumerate(argv):
        if a == "--fbx":
            fbx = os.path.abspath(argv[i + 1])
        if a == "--json":
            js = os.path.abspath(argv[i + 1])
    return fbx, js


def _bvh(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.transform(ob.matrix_world)
    return BVHTree.FromBMesh(bm), bm


def _ray(bvh, x, y, z, d):
    """Ray in Unreal-space cm (file y = -ue y); d = (dx, dy, dz) in UE space.  Returns the hit (x, y, z) in UE cm or None."""
    sc = bpy.context.scene.unit_settings.scale_length * 100.0
    h = bvh.ray_cast(Vector((x / sc, -y / sc, z / sc)), Vector((d[0], -d[1], d[2])))
    if h[0] is None:
        return None
    return (h[0].x * sc, -h[0].y * sc, h[0].z * sc)


def structural(short, spec, ob, ucx, fail, res):
    """Geometry checks that the bounds cannot show (arch brace, roof plane, seat height, altar core and hole...)."""
    kind = spec.get('struct')
    if not kind:
        return
    bvh, bm = _bvh(ob)
    notes = []
    if kind == "truss":
        zt = lambda y: 1265.0 - (965.0 / 810.0) * abs(y)
        for y in (-600.0, -400.0, 400.0, 600.0):                       # rafter top faces on the roof plane (through (+-810, 300) and (0, 1265))
            h = _ray(bvh, 0.0, y, 1400.0, (0, 0, -1))
            ok = h is not None and abs(h[2] - zt(y)) < 1.6
            notes.append("rafter top Y%+d: %s (plane %.1f)" % (y, "%.1f" % h[2] if h else None, zt(y)))
            if not ok:
                fail("rafter top at Y %g is %s, roof plane %.1f" % (y, h and round(h[2], 1), zt(y)))
        for sg in (-1, 1):                                              # arch brace intrados: circle r 783.9 around (-sg 78.9, 50)
            for y in (300.0, 500.0):
                yy = sg * y
                h = _ray(bvh, 0.0, yy, 0.0, (0, 0, 1))
                zi = 50.0 + math.sqrt(783.9 ** 2 - (yy + sg * 78.9) ** 2)
                ok = h is not None and abs(h[2] - zi) < 1.6
                notes.append("brace intrados Y%+d: %s (r=783.9 circle %.1f)" % (yy, "%.1f" % h[2] if h else None, zi))
                if not ok:
                    fail("arch brace intrados at Y %g is %s, expected %.1f" % (yy, h and round(h[2], 1), zi))
        h = _ray(bvh, 0.0, 200.0, 990.0, (0, 0, -1))                    # collar top
        notes.append("collar top: %s (850)" % (("%.1f" % h[2]) if h else None))
        if h is None or abs(h[2] - 850.0) > 1.0:
            fail("collar top %s expected 850" % (h and round(h[2], 1)))
    elif kind == "pew":
        for x in (-20.0, -10.0, 0.0, 10.0, 20.0):                     # seat top Z 45 over X -20..20 (note sits on it)
            h = _ray(bvh, x, -87.0, 200.0, (0, 0, -1))
            notes.append("seat top X%+d: %s" % (x, ("%.2f" % h[2]) if h else None))
            if h is None or not (44.4 <= h[2] <= 45.05):
                fail("seat top at X %g is %s (expected 45)" % (x, h and round(h[2], 2)))
        h = _ray(bvh, -24.5, 0.0, 200.0, (0, 0, -1))
        notes.append("back top: %s (95)" % (("%.2f" % h[2]) if h else None))
        if h is None or h[2] < 94.4:
            fail("back top %s expected 95" % (h and round(h[2], 2)))
    elif kind == "altar":
        # hollow core + O84 hole: a vertical ray through the centre must pass the whole altar; the wings carry the only collision
        for (x, y) in ((0.0, 0.0), (30.0, 0.0), (-30.0, 20.0), (0.0, -35.0)):
            h = _ray(bvh, x, y, 150.0, (0, 0, -1))
            notes.append("centre ray (%g,%g): %s" % (x, y, h))
            if h is not None:
                fail("vertical ray at (%g, %g) hits the altar at Z %.1f (hole / core must be open)" % (x, y, h[2]))
        h = _ray(bvh, -49.0, 0.0, 50.0, (0, 0, 1))                      # inside the core, looking up: mensa underside at Z 91
        notes.append("core ceiling: %s (91)" % (("%.1f" % h[2]) if h else None))
        if h is None or abs(h[2] - 91.0) > 1.5:
            fail("core ceiling %s expected 91" % (h and round(h[2], 1)))
        h = _ray(bvh, -200.0, 0.0, 60.0, (1, 0, 0))                     # front face of the centre panel at X -52
        notes.append("front panel face: %s (-52)" % (("%.1f" % h[0]) if h else None))
        if h is None or abs(h[0] + 52.0) > 1.0:
            fail("centre front face %s expected -52" % (h and round(h[0], 1)))
        for u in ucx:                                                   # UCX only on the wings: |Y| >= 53.5
            ys = [p.y for p in VK.ue_coords(u)]
            if min(abs(v) for v in ys) < 53.5 or min(ys) * max(ys) > 0 and False:
                fail("%s reaches the centre (Y %.1f..%.1f)" % (u.name, min(ys), max(ys)))
            if min(ys) < 0 < max(ys):
                fail("%s spans Y = 0" % u.name)
    elif kind == "shell_cyl":
        h = _ray(bvh, 0.0, 0.0, -10.0, (0, 0, 1))                        # open bottom: first hit is the cap underside at Z 50
        notes.append("cap underside: %s" % (("%.1f" % h[2]) if h else None))
        if h is None or abs(h[2] - 50.0) > 1.0:
            fail("shell cap underside %s expected 50 (open bottom, 1 cm wall)" % (h and round(h[2], 1)))
    elif kind == "backdrop":
        n = ob.data.polygons[0].normal
        notes.append("normal %.2f %.2f %.2f" % (n.x, n.y, n.z))
        if n.x > -0.9:
            fail("backdrop normal %s should face -X" % (tuple(round(v, 2) for v in n),))
    bm.free()
    res['struct'] = notes


def uv_in_unit(ob, fail, res):
    uvs = ob.data.uv_layers.active.data
    us = [d.uv[0] for d in uvs]
    vs = [d.uv[1] for d in uvs]
    res['uv'] = [round(min(us), 3), round(max(us), 3), round(min(vs), 3), round(max(vs), 3)]
    if min(us) < -0.001 or max(us) > 1.001 or min(vs) < -0.001 or max(vs) > 1.001:
        fail("UVs outside 0..1: %s" % res['uv'])
    if max(us) - min(us) < 0.45 or max(vs) - min(vs) < 0.45:
        fail("UV span too small: %s" % res['uv'])


def check(path, short, spec):
    name = P + short
    res = dict(name=name, ok=True, fails=[])

    def fail(m):
        res['ok'] = False
        res['fails'].append(m)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    ucx = sorted([o for o in obs if o.name.startswith("UCX_")], key=lambda o: o.name)
    vis = [o for o in obs if not o.name.startswith("UCX_")]
    if len(vis) != 1:
        fail("expected 1 visual mesh, found %d" % len(vis))
        return res
    ob = vis[0]
    pts = VK.ue_coords(ob)
    mn, mx = VK.bounds(pts)
    dims = mx - mn
    res['dims'] = [round(v, 2) for v in dims]
    res['bounds_min'] = [round(v, 2) for v in mn]
    res['tris'] = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    # pivot: XY centre at 0, min Z at 0 (ivy cards: X centre at 0, back plane at Y 0)
    if spec.get('wall_pivot'):
        if abs((mn[0] + mx[0]) * 0.5) > TOL:
            fail("pivot: X centre %.2f (should be 0)" % ((mn[0] + mx[0]) * 0.5))
        if abs(mn.y) > TOL:
            fail("pivot: back plane Y min %.2f (should be 0)" % mn.y)
        if dims.y > spec['ymax'] + 0.01:
            fail("depth Y %.2f > %.1f" % (dims.y, spec['ymax']))
    else:
        for i, ax in enumerate("XY"):
            c = (mn[i] + mx[i]) * 0.5
            if abs(c) > TOL:
                fail("pivot: %s centre %.2f (should be 0)" % (ax, c))
    if abs(mn.z) > TOL:
        fail("pivot: min Z %.2f (should be 0)" % mn.z)
    if ob.matrix_world.translation.length > 1e-4:
        fail("node not at the origin")
    # dimensions
    tol = spec.get('tol', TOL)
    for i, v in enumerate(spec['dims']):
        if v is not None and abs(dims[i] - v) > tol:
            fail("dim %s %.2f vs %.2f" % ("XYZ"[i], dims[i], v))
    if 'zmax' in spec and dims.z > spec['zmax']:
        fail("dim Z %.2f > %.2f" % (dims.z, spec['zmax']))
    # slots
    names = [m.name.split(".")[0] if m else None for m in ob.data.materials]
    res['slots'] = names
    if names != spec['slots']:
        fail("slots %s expected %s" % (names, spec['slots']))
    # vertex colour / uv / normals
    ca = [a.name for a in ob.data.color_attributes]
    if not ca:
        fail("no colour attribute")
    else:
        bad = sum(1 for d in ob.data.color_attributes[0].data if min(d.color) < 0.99)
        if bad:
            fail("%d non-white vertex colours" % bad)
    if not ob.data.uv_layers:
        fail("no UV layer")
    if len(ob.data.corner_normals) == 0:
        fail("no normals")
    vol = VK.signed_volume(ob)
    res['volume_cm3'] = round(vol, 1)
    if vol <= 0 and not spec.get('open_mesh'):
        fail("non-positive volume (%.1f)" % vol)
    # collision
    res['ucx'] = len(ucx)
    if len(ucx) != spec['ucx']:
        fail("UCX count %d expected %d" % (len(ucx), spec['ucx']))
    for k, u in enumerate(ucx):
        if u.name != "UCX_%s_%02d" % (name, k):
            fail("UCX name %s" % u.name)
        rep = []
        if not VK.is_convex(u, report=rep):
            fail("%s not convex" % u.name)
        b0, b1 = VK.bounds(VK.ue_coords(u))
        env = spec.get('ucx_env')
        if env:
            ex = (env[0] / 2, env[1] / 2)
            want0 = Vector((-ex[0], -ex[1], 0.0))
            want1 = Vector((ex[0], ex[1], env[2]))
            if any(abs(b0[i] - want0[i]) > TOL or abs(b1[i] - want1[i]) > TOL for i in range(3)):
                fail("%s bounds %s..%s differ from the required envelope %s" % (u.name, tuple(round(v, 2) for v in b0), tuple(round(v, 2) for v in b1), env))
        else:
            for i in range(3):
                if b0[i] < mn[i] - TOL or b1[i] > mx[i] + TOL:
                    fail("%s outside the visual bounds on %s" % (u.name, "XYZ"[i]))
    structural(short, spec, ob, ucx, fail, res)
    if spec.get('uv01'):
        uv_in_unit(ob, fail, res)
    # ledge: flat 22 x 22 centre exactly at Z 70
    if short.startswith("KeyLedge"):
        zs = [p.z for p in pts if abs(p.x) <= 10.5 and abs(p.y) <= 10.5 and p.z > 60.0]
        res['flat_centre_z'] = [round(min(zs), 3), round(max(zs), 3)] if zs else None
        if not zs or min(zs) < 69.98 or max(zs) > 70.02:
            fail("flat centre not at Z 70: %s" % res['flat_centre_z'])
    return res


def main():
    fbx_dir, js = parse()
    rows = []
    for short, spec in SPEC.items():
        path = os.path.join(fbx_dir, spec.get('subdir', ''), P + short + ".fbx")
        if not os.path.exists(path):
            rows.append(dict(name=P + short, ok=False, fails=["missing FBX"]))
            continue
        rows.append(check(path, short, spec))
    print("\n==== VERIFY PROPS SUMMARY ====")
    print("%-26s %-22s %-7s %-22s %-4s %s" % ("piece", "dims cm (UE)", "tris", "slots", "UCX", "result"))
    for r in rows:
        if 'dims' not in r:
            print("%-26s %s" % (r['name'][len(P):], "; ".join(r['fails'])))
            continue
        print("%-26s %-22s %-7d %-22s %-4d %s" % (r['name'][len(P):], "x".join("%g" % d for d in r['dims']), r['tris'],
                                                  ",".join(s.replace("MAT_", "") for s in r['slots']), r['ucx'],
                                                  "PASS" if r['ok'] else "FAIL: " + "; ".join(r['fails'])))
    ok = all(r['ok'] for r in rows)
    print("pieces: %d  passed: %d  failed: %d  => %s" % (len(rows), sum(1 for r in rows if r['ok']), sum(1 for r in rows if not r['ok']), "ALL PASS" if ok else "FAILURES"))
    for r in rows:
        if r.get('struct'):
            print("  %s: %s" % (r['name'][len(P):], "; ".join(r['struct'])))
    for r in rows:
        if 'flat_centre_z' in r:
            print("  key ledge flat centre Z range: %s" % r['flat_centre_z'])
    if js:
        with open(js, "w") as fh:
            json.dump(rows, fh, indent=1)
    sys.stdout.flush()
    os._exit(0 if ok else 1)


if __name__ == "__main__":
    main()
