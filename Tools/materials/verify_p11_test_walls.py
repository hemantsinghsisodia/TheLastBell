"""verify_p11_test_walls.py -- P11-3b: compare the no-groove FBX files with the kit originals (clean Blender, headless).

    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --factory-startup --python Tools/materials/verify_p11_test_walls.py

Per pair: bounds (0.1 cm), pivot offset, material slot names and order, UCX count and bounds, vertex counts, and a
geometric "no long groove line" check.  Exit code 1 on any failure.

No-groove check: take the vertices of the masonry body that are inset 0.5..6 cm behind the front face (Y 0) or the back
face (Y = T) in Unreal space, bin them by Z (0.1 cm) and by X (0.1 cm) and measure the straight-line extent of each bin.
Any bin line longer than 100 cm fails.  Zones excluded: the wall cap course (Z >= H - 25, its chamfers are real profile)
and the plinth chamfer (Z >= 54).  The same check is run on the originals as a sanity test: it must find at least one
long line there (otherwise the check would be meaningless).
"""
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
ORIG_DIR = os.path.join(ROOT, "SourceArt", "Kit", "FBX")
NEW_DIR = os.path.join(ROOT, "SourceArt", "P11")

PAIRS = [  # (original mesh, new mesh, kind, thickness T, body top Z for the groove check)
    ("SM_LB_Kit_Wall_400x60x800_A", "SM_LB_P11_NoGroove_Wall_400x60x800_A", "wall", 60.0, 775.0),
    ("SM_LB_Kit_Wall_400x60x800_B", "SM_LB_P11_NoGroove_Wall_400x60x800_B", "wall", 60.0, 775.0),
    ("SM_LB_Kit_Wall_100x60x800", "SM_LB_P11_NoGroove_Wall_100x60x800", "wall", 60.0, 775.0),
    ("SM_LB_Kit_Trim_Plinth_400x80x60", "SM_LB_P11_NoGroove_Plinth_400x80x60", "plinth", 80.0, 54.0),
    ("SM_LB_Kit_Trim_Plinth_100x80x60", "SM_LB_P11_NoGroove_Plinth_100x80x60", "plinth", 80.0, 54.0),
]
TOL_B = 0.1
MAX_LINE = 100.0
INSET_MIN, INSET_MAX = 0.5, 6.0


def ue_coords(ob):
    """World vertex positions as Unreal-space cm (x, -y, z), same convention as verify_kit.py."""
    sc = bpy.context.scene.unit_settings.scale_length * 100.0
    mw = ob.matrix_world
    return [Vector((w.x * sc, -w.y * sc, w.z * sc)) for w in (mw @ v.co for v in ob.data.vertices)]


def bounds(pts):
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    ucx = sorted([o for o in obs if o.name.startswith("UCX_")], key=lambda o: o.name)
    vis = [o for o in obs if not o.name.startswith("UCX_")]
    assert len(vis) == 1, "expected 1 visual mesh in %s, found %d" % (path, len(vis))
    ob = vis[0]
    pts = ue_coords(ob)
    data = dict(
        obj_name=ob.name, mesh_name=ob.data.name,
        pts=pts, bounds=bounds(pts),
        slots=[m.name.split(".")[0] if m else None for m in ob.data.materials],
        slots_used=sorted({p.material_index for p in ob.data.polygons}),
        verts=len(ob.data.vertices),
        tris=sum(len(p.vertices) - 2 for p in ob.data.polygons),
        ucx_names=[u.name for u in ucx], ucx_bounds=[bounds(ue_coords(u)) for u in ucx],
    )
    return data


def long_lines(pts, T, ztop):
    """Return (longest line cm, description) of inset vertices binned by Z (extent in X) and by X (extent in Z)."""
    inset = []
    for p in pts:
        if p.z >= ztop:
            continue
        d = min(p.y, T - p.y)
        if INSET_MIN < d < INSET_MAX:
            inset.append(p)
    by_z, by_x = {}, {}
    for p in inset:
        by_z.setdefault(round(p.z, 1), []).append(p.x)
        by_x.setdefault(round(p.x, 1), []).append(p.z)
    best, desc = 0.0, "none"
    for z, xs in by_z.items():
        ext = max(xs) - min(xs)
        if ext > best:
            best, desc = ext, "horizontal line at Z %.1f, X %.1f..%.1f" % (z, min(xs), max(xs))
    for x, zs in by_x.items():
        ext = max(zs) - min(zs)
        if ext > best:
            best, desc = ext, "vertical line at X %.1f, Z %.1f..%.1f" % (x, min(zs), max(zs))
    return best, desc, len(inset)


def main():
    fails = []
    rows = []
    for orig_n, new_n, kind, T, ztop in PAIRS:
        o = load(os.path.join(ORIG_DIR, orig_n + ".fbx"))
        n = load(os.path.join(NEW_DIR, new_n + ".fbx"))

        def fail(msg):
            fails.append("%s: %s" % (new_n, msg))

        # names follow the new mesh name
        if n["obj_name"] != new_n:
            fail("object name %s" % n["obj_name"])
        if n["mesh_name"] != new_n and not n["mesh_name"].startswith(new_n):
            fail("mesh data name %s" % n["mesh_name"])
        for k, u in enumerate(n["ucx_names"]):
            if u != "UCX_%s_%02d" % (new_n, k):
                fail("UCX name %s" % u)
        # bounds + pivot
        for i in range(3):
            if abs(n["bounds"][0][i] - o["bounds"][0][i]) > TOL_B:
                fail("bounds min %s %.3f vs %.3f" % ("XYZ"[i], n["bounds"][0][i], o["bounds"][0][i]))
            if abs(n["bounds"][1][i] - o["bounds"][1][i]) > TOL_B:
                fail("bounds max %s %.3f vs %.3f" % ("XYZ"[i], n["bounds"][1][i], o["bounds"][1][i]))
            if abs(n["bounds"][0][i]) > TOL_B:
                fail("pivot: bbox min %s = %.3f (should be 0)" % ("XYZ"[i], n["bounds"][0][i]))
        # slots
        if n["slots"] != o["slots"]:
            fail("slots %s vs %s" % (n["slots"], o["slots"]))
        # UCX
        if len(n["ucx_names"]) != len(o["ucx_names"]):
            fail("UCX count %d vs %d" % (len(n["ucx_names"]), len(o["ucx_names"])))
        else:
            for k, (bn, bo) in enumerate(zip(n["ucx_bounds"], o["ucx_bounds"])):
                for i in range(3):
                    if abs(bn[0][i] - bo[0][i]) > TOL_B or abs(bn[1][i] - bo[1][i]) > TOL_B:
                        fail("UCX %d bounds differ on %s" % (k, "XYZ"[i]))
        # vertex count: fewer than the original.  A piece whose original has no joints (nothing to remove) can be equal.
        if n["verts"] > o["verts"]:
            fail("vertices %d > original %d" % (n["verts"], o["verts"]))
        # geometric no-groove check
        ln, ld, ninset = long_lines(n["pts"], T, ztop)
        lo, lod, oinset = long_lines(o["pts"], T, ztop)
        if ln > MAX_LINE:
            fail("long inset line %.1f cm remains (%s)" % (ln, ld))
        rows.append((new_n, o, n, ln, ld, ninset, lo, lod, oinset))

    print("\n" + "=" * 118)
    print("%-40s %-9s %-9s %-14s %-14s %-12s %-10s" % ("mesh", "verts o", "verts n", "tris o->n", "slots used n", "UCX n/o", "line n/o"))
    for new_n, o, n, ln, ld, ninset, lo, lod, oinset in rows:
        print("%-40s %-9d %-9d %-14s %-14s %-12s %-10s" % (
            new_n, o["verts"], n["verts"], "%d->%d" % (o["tris"], n["tris"]), str(n["slots_used"]),
            "%d/%d" % (len(n["ucx_names"]), len(o["ucx_names"])), "%.0f/%.0f" % (ln, lo)))
    print("-" * 118)
    for new_n, o, n, ln, ld, ninset, lo, lod, oinset in rows:
        bmn, bmx = n["bounds"]
        print(new_n)
        print("   bounds n min %s max %s | o min %s max %s" % (
            tuple(round(v, 2) for v in bmn), tuple(round(v, 2) for v in bmx),
            tuple(round(v, 2) for v in o["bounds"][0]), tuple(round(v, 2) for v in o["bounds"][1])))
        print("   slots n %s (used %s) | o %s (used %s)" % (n["slots"], n["slots_used"], o["slots"], o["slots_used"]))
        print("   inset verts n %d, longest line %.1f (%s) | o %d, longest %.1f (%s)" % (ninset, ln, ld, oinset, lo, lod))
        print("   UCX n %s" % n["ucx_names"])
        print("   UCX bounds n/o:", [(tuple(round(v, 1) for v in a[1]), tuple(round(v, 1) for v in b[1])) for a, b in zip(n["ucx_bounds"], o["ucx_bounds"])])
    # sanity: the check must detect grooves in at least one original
    if not any(r[6] > MAX_LINE for r in rows):
        fails.append("sanity: the groove check found no long line in any ORIGINAL; the check is not meaningful")
    print("=" * 118)
    if fails:
        print("VERIFY FAILED (%d):" % len(fails))
        for f in fails:
            print("  - " + f)
        sys.exit(1)
    print("VERIFY OK: %d pieces" % len(rows))


if __name__ == "__main__":
    main()
