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

import bpy
from mathutils import Vector

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
    "FirePit_A": dict(dims=(135.0, 135.0, 27.0), tol=12.0, slots=["MAT_Stone", "MAT_Charred"], ucx=1),  # O110 stone-centre circle + 25-35 cm stones
}


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
    # pivot: XY centre at 0, min Z at 0
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
    if vol <= 0:
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
        path = os.path.join(fbx_dir, P + short + ".fbx")
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
        if 'flat_centre_z' in r:
            print("  key ledge flat centre Z range: %s" % r['flat_centre_z'])
    if js:
        with open(js, "w") as fh:
            json.dump(rows, fh, indent=1)
    sys.stdout.flush()
    os._exit(0 if ok else 1)


if __name__ == "__main__":
    main()
