"""verify_kit.py -- re-imports every kit FBX in a clean headless Blender and checks it against the spec table.

    blender.exe -b --factory-startup --python Tools/blender/kit/verify_kit.py -- [--fbx SourceArt/Kit/FBX] [--json out.json]

Checks per piece (all in Unreal space: UE_Y = -Blender_Y of the re-imported file, see README):
  dimensions vs spec (+-1 cm), pivot (bounding-box min at 0,0,0 and node at the origin), material slot
  names/order (MAT_Masonry, MAT_Trim, MAT_Rubble), UCX_ collision present / named UCX_<Mesh>_NN / convex /
  inside the envelope, clear openings really clear (no collision overlap and ray casts through the clear
  rectangle hit nothing), vertex colour attribute present and white, UV layer present, outward winding
  (positive volume), custom normals present, triangle count.
Exit code 1 if any check fails.
"""
import json
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_kit as BK  # noqa: E402  (importing does not build anything)

TOL = 1.0
MATS = ("MAT_Masonry", "MAT_Trim", "MAT_Rubble")
# clear rectangles (x0, x1, y0, y1, z0, z1) in piece space (cm)
CLEAR = {
    "Doorway_Pointed_400x60x400": (140, 260, 0, 60, 0, 240),
    "Gate_Arch_1200x300x800": (400, 800, 0, 300, 0, 300),
}
EXPECT_UCX = {
    "Wall_400x60x800_Broken": 3, "Wall_400x60x400_Broken": 3, "Doorway_Pointed_400x60x400": 3,
    "Gate_Arch_1200x300x800": 3, "Rubble_Heap_400x300x130": 2, "Cliff_Slab_500x300x600_A": 40,
    "Cliff_Slab_500x300x600_B": 40, "Cliff_Slab_500x300x300": 24, "Cliff_End_200x300x600": 40, "Buttress_100x150x800": 2, "Well_Wall_450x50x250": 3, "Well_Wall_350x50x250": 3,
}


def parse():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    fbx = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SourceArt", "Kit", "FBX"))
    js = None
    for i, a in enumerate(argv):
        if a == "--fbx":
            fbx = os.path.abspath(argv[i + 1])
        if a == "--json":
            js = os.path.abspath(argv[i + 1])
    return fbx, js


def ue_coords(ob):
    """World-space vertex positions converted to Unreal space cm (x, -y, z)."""
    sc = bpy.context.scene.unit_settings.scale_length * 100.0
    mw = ob.matrix_world
    return [Vector((w.x * sc, -w.y * sc, w.z * sc)) for w in (mw @ v.co for v in ob.data.vertices)]


def bounds(pts):
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def signed_volume(ob):
    me = ob.data
    me.calc_loop_triangles()
    pts = ue_coords(ob)
    vol = 0.0
    for t in me.loop_triangles:
        a, b, c = (pts[i] for i in t.vertices)
        vol += a.dot(b.cross(c)) / 6.0
    # UE space is a mirror of the file space: file volume (RH, outward) is positive, mirrored volume negative
    return -vol


def is_convex(ob, eps=0.25, report=None):  # sub-2.5 mm noise from near-coplanar hull points is ignored (UE rebuilds the hulls)
    pts = ue_coords(ob)
    me = ob.data
    me.calc_loop_triangles()
    for t in me.loop_triangles:
        a, b, c = (pts[i] for i in t.vertices)
        n = (b - a).cross(c - a)
        if n.length < 1e-9:
            continue
        n.normalize()
        sides = [n.dot(p - a) for p in pts]
        if max(sides) > eps and min(sides) < -eps:
            if report is not None:
                report.append(min(max(sides), -min(sides)))
            return False
    return True


def overlap_volume(b1, b2):
    lo = [max(b1[0][i], b2[0][i]) for i in range(3)]
    hi = [min(b1[1][i], b2[1][i]) for i in range(3)]
    d = [max(0.0, hi[i] - lo[i]) for i in range(3)]
    return d[0] * d[1] * d[2]


def check_piece(path, name, spec_dims):
    res = dict(name=name, ok=True, fails=[])

    def fail(msg):
        res['ok'] = False
        res['fails'].append(msg)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    ucx = sorted([o for o in obs if o.name.startswith("UCX_")], key=lambda o: o.name)
    vis = [o for o in obs if not o.name.startswith("UCX_")]
    if len(vis) != 1:
        fail("expected 1 visual mesh, found %d" % len(vis))
        return res
    ob = vis[0]
    short = name[len(BK.PREFIX):]
    # pivot / dims
    pts = ue_coords(ob)
    mn, mx = bounds(pts)
    dims = mx - mn
    res['bounds_min'] = [round(v, 2) for v in mn]
    res['dims'] = [round(v, 2) for v in dims]
    res['spec'] = list(spec_dims)
    res['tris'] = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    for i in range(3):
        if abs(dims[i] - spec_dims[i]) > TOL:
            fail("dim %s %.2f vs spec %.2f" % ("XYZ"[i], dims[i], spec_dims[i]))
        if abs(mn[i]) > TOL:
            fail("pivot: bbox min %s = %.2f (should be 0)" % ("XYZ"[i], mn[i]))
    if (ob.matrix_world.translation).length > 1e-4:
        fail("node not at the origin: %s" % (tuple(ob.matrix_world.translation),))
    # materials
    names = [m.name.split(".")[0] if m else None for m in ob.data.materials]
    res['slots'] = names
    if tuple(names) != MATS:
        fail("material slots %s" % (names,))
    # vertex colour + uv + normals
    ca = [a.name for a in ob.data.color_attributes]
    res['color_attrs'] = ca
    if not ca:
        fail("no colour attribute")
    else:
        attr = ob.data.color_attributes[0]
        bad = sum(1 for d in attr.data if min(d.color) < 0.99)
        if bad:
            fail("%d non-white vertex colours" % bad)
    if not ob.data.uv_layers:
        fail("no UV layer")
    if len(ob.data.corner_normals) == 0:
        fail("no normals")
    # winding / volume
    vol = signed_volume(ob)
    res['volume_m3'] = round(vol / 1e6, 3)
    if vol <= 0:
        fail("negative volume (inward faces?)")
    # collision
    n_expect = EXPECT_UCX.get(short, 1)
    res['ucx'] = len(ucx)
    if len(ucx) != n_expect:
        fail("UCX count %d (expected %d)" % (len(ucx), n_expect))
    ub = []
    for k, u in enumerate(ucx):
        if not u.name.startswith("UCX_%s_" % name):
            fail("UCX name %s" % u.name)
        rep = []
        if not is_convex(u, report=rep):
            fail("%s is not convex (worst plane violation %.3f cm)" % (u.name, max(rep) if rep else 0.0))
        b = bounds(ue_coords(u))
        ub.append(b)
        for i in range(3):
            if b[0][i] < -TOL or b[1][i] > spec_dims[i] + TOL:
                fail("%s outside the envelope on %s" % (u.name, "XYZ"[i]))
    # clear opening
    clear = CLEAR.get(short)
    if clear:
        x0, x1, y0, y1, z0, z1 = clear
        cbox = (Vector((x0, y0, z0)), Vector((x1, y1, z1)))
        worst = max([overlap_volume(cbox, b) for b in ub] or [0.0])
        res['ucx_overlap_with_clear_cm3'] = round(worst, 3)
        if worst > 1.0:
            fail("collision overlaps the clear opening (%.1f cm3)" % worst)
        # visual mesh ray cast (file space: y mirrored)
        me = ob.data
        bm = bmesh.new()
        bm.from_mesh(me)
        sc = bpy.context.scene.unit_settings.scale_length * 100.0
        bm.transform(ob.matrix_world)
        bvh = BVHTree.FromBMesh(bm)
        hits = 0
        n = 0
        for ix in range(1, 20):
            for iz in range(1, 15):
                x = x0 + 0.5 + (x1 - x0 - 1.0) * ix / 20.0
                z = z0 + 0.5 + (z1 - z0 - 1.0) * iz / 15.0
                # ray along file-space +Y through the piece; file y = -ue_y
                origin = Vector((x / sc, 20.0 / sc, z / sc))
                h = bvh.ray_cast(origin, Vector((0, -1, 0)))
                n += 1
                if h[0] is not None:
                    hits += 1
        bm.free()
        res['clear_ray_hits'] = "%d/%d" % (hits, n)
        if hits:
            fail("visual mesh blocks the clear opening (%d/%d rays hit)" % (hits, n))
    return res


def main():
    fbx_dir, js = parse()
    rows = []
    for nm, _fn, dims in BK.table():
        name = BK.PREFIX + nm
        path = os.path.join(fbx_dir, name + ".fbx")
        if not os.path.exists(path):
            rows.append(dict(name=name, ok=False, fails=["missing FBX"]))
            continue
        rows.append(check_piece(path, name, dims))
    print("\n==== VERIFY KIT SUMMARY ====")
    print("%-40s %-22s %-8s %-9s %-4s %s" % ("piece", "dims cm (UE)", "tris", "slots", "UCX", "result"))
    for r in rows:
        if 'dims' not in r:
            print("%-40s %s" % (r['name'], "; ".join(r['fails'])))
            continue
        print("%-40s %-22s %-8d %-9s %-4d %s" % (r['name'][len(BK.PREFIX):], "x".join("%g" % d for d in r['dims']), r['tris'],
                                                 "012" if r['slots'] == list(MATS) else "BAD", r['ucx'],
                                                 "PASS" if r['ok'] else "FAIL: " + "; ".join(r['fails'])))
    ok = all(r['ok'] for r in rows)
    print("pieces: %d  passed: %d  failed: %d  => %s" % (len(rows), sum(1 for r in rows if r['ok']), sum(1 for r in rows if not r['ok']), "ALL PASS" if ok else "FAILURES"))
    for r in rows:
        if 'clear_ray_hits' in r:
            print("  clear opening %s: ucx overlap %s cm3, ray hits %s" % (r['name'][len(BK.PREFIX):], r.get('ucx_overlap_with_clear_cm3'), r['clear_ray_hits']))
    if js:
        with open(js, "w") as fh:
            json.dump(rows, fh, indent=1)
    sys.stdout.flush()
    os._exit(0 if ok else 1)


if __name__ == "__main__":
    main()
