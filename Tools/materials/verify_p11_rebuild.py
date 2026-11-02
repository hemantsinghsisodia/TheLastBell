"""verify_p11_rebuild.py -- P11-4b: compare the 51 rebuilt masonry FBX files with the copies taken before the rebuild.

    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --factory-startup --python Tools/materials/verify_p11_rebuild.py
    optional:  -- --old Saved/p11_old_fbx   --new-root <dir that replaces the repo root for the "fbx" paths>   --only SUBSTR ...

For every entry of Tools/materials/p11_reimport_list.json, the new FBX (the "fbx" path) is imported next to the old copy
(Saved/p11_old_fbx/<file name>) in a clean Blender and compared:
  a. bounds equal within 0.1 cm (min and max, so the pivot convention is the same too);
  b. the same USED material slots in the same order, computed from the faces (Unreal drops a slot no face uses, so a slot
     that appears or vanishes would shift the slot list of the imported mesh);
  c. the same UCX hull count, each hull's bounds within 0.1 cm;
  d. triangles fewer than or equal to before;
  e. no groove line left on masonry faces: the inset-line check of verify_p11_test_walls.py, generalised.  Only vertices of
     polygons in the MAT_Masonry slot are used.  For each of the four horizontal sides of the masonry extent, a vertex that
     sits 0.5..6 cm behind that side's plane (and at least 4 cm from the side's two ends, which skips corner chamfers) is an
     "inset" vertex; inset vertices are binned by Z (extent along the side) and by along-side coordinate (extent in Z), 0.1 cm
     bins.  A bin line longer than 100 cm is listed.  It is informational: real profile (a pilaster step, a jamb, an arch ring,
     whose two sides share a Z) gives such lines too.  A line also present in the old file is reported as 'profile'.
     The same check runs on the old FBX as a sanity test: it finds a long line in most of them.
     In addition, a V-notch check that does not depend on the face plane (this is the pass/fail criterion for grooves): a "notch edge" is an axis-aligned
     edge, between two MAT_Masonry faces, concave, with a face-normal angle of at least 57 degrees, whose two normals bisect
     along a horizontal axis (the face normal of the wall).  That is exactly the cross-section of a modelled V-groove (two
     45 degree flanks) and nothing else on this kit: arch intrados facets meet at small angles, steps meet at 90 degrees
     with normals perpendicular to the face.  More than NOTCH_MAX_CM of notch edges fails.
  f. shading: on flat, axis-aligned MAT_Masonry faces (normal within 0.01 of +-X or +-Y), the share of face area with a corner
     normal deviating more than 3 degrees from the face normal must be at most 1 % per mesh (NORMAL_MAX_PCT).  Without grooves
     a wall face is a few huge triangles, so one tilted chip-rim vertex normal would shade across all of it (the lighting wedges
     seen in the first rebuild).  The old file's share is printed beside the new one.
Only a, b, c, d, f and the V-notch count fail the run (exit code 1); the inset-line listing is printed in full for a human to judge.
"""
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
LIST = os.path.join(HERE, "p11_reimport_list.json")
OLD_DIR = os.path.join(ROOT, "Saved", "p11_old_fbx")

TOL_B = 0.1
MAX_LINE = 100.0
INSET_MIN, INSET_MAX = 0.5, 6.0
END_SKIP = 4.0
NOTCH_MIN_ANGLE = 1.0       # rad (57 deg) between the two face normals
NOTCH_MIN_LEN = 20.0        # cm, edges shorter than this are ignored
NOTCH_MAX_CM = 20.0         # total notch edge length that may remain per mesh
NORMAL_DEG = 3.0            # corner normal deviation that counts as a shading tilt
NORMAL_MAX_PCT = 1.0        # share of flat masonry face area that may be tilted, per mesh
MASONRY = "MAT_Masonry"



def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    old, root, only = OLD_DIR, ROOT, []
    i = 0
    while i < len(argv):
        if argv[i] == "--old":
            old = os.path.abspath(argv[i + 1])
            i += 2
        elif argv[i] == "--new-root":
            root = os.path.abspath(argv[i + 1])
            i += 2
        elif argv[i] == "--only":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                only.append(argv[i])
                i += 1
        else:
            i += 1
    return old, root, only


def ue_coords(ob):
    """World vertex positions as Unreal-space cm (x, -y, z), same convention as verify_kit.py."""
    sc = bpy.context.scene.unit_settings.scale_length * 100.0
    mw = ob.matrix_world
    return [Vector((w.x * sc, -w.y * sc, w.z * sc)) for w in (mw @ v.co for v in ob.data.vertices)]


def bounds(pts):
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def notch_edges(ob, mas_idx):
    """Total length (cm) and count of V-groove edges between MAT_Masonry faces (see the module docstring)."""
    sc = bpy.context.scene.unit_settings.scale_length * 100.0
    mw = ob.matrix_world
    rot = mw.to_3x3()
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    total, count = 0.0, 0
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        f1, f2 = e.link_faces
        if f1.material_index not in mas_idx or f2.material_index not in mas_idx:
            continue
        ln = ((mw @ e.verts[1].co) - (mw @ e.verts[0].co)).length * sc
        if ln < NOTCH_MIN_LEN:
            continue
        try:
            ang = e.calc_face_angle_signed()
        except ValueError:
            continue
        if ang > -NOTCH_MIN_ANGLE:
            continue
        d = (rot @ (e.verts[1].co - e.verts[0].co)).normalized()
        if max(abs(d.x), abs(d.y), abs(d.z)) < 0.999:
            continue
        bis = (rot @ f1.normal) + (rot @ f2.normal)
        if bis.length < 1e-6:
            continue
        bis.normalize()
        if max(abs(bis.x), abs(bis.y)) < 0.98:
            continue
        total += ln
        count += 1
    bm.free()
    return total, count


def flat_shading(ob, mas_idx):
    """(percent of flat masonry face area with a corner normal tilted more than NORMAL_DEG, worst tilt in degrees)."""
    me = ob.data
    rot = ob.matrix_world.to_3x3()
    tot = bad = worst = 0.0
    for p in me.polygons:
        if p.material_index not in mas_idx:
            continue
        fn = (rot @ p.normal).normalized()
        if max(abs(fn.x), abs(fn.y)) < 0.99995:
            continue
        w = max(math.degrees(fn.angle((rot @ me.corner_normals[li].vector).normalized())) for li in p.loop_indices)
        tot += p.area
        worst = max(worst, w)
        if w > NORMAL_DEG:
            bad += p.area
    return (100.0 * bad / tot if tot else 0.0), worst


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    ucx = sorted([o for o in obs if o.name.startswith("UCX_")], key=lambda o: o.name)
    vis = [o for o in obs if not o.name.startswith("UCX_")]
    assert len(vis) == 1, "expected 1 visual mesh in %s, found %d" % (path, len(vis))
    ob = vis[0]
    pts = ue_coords(ob)
    me = ob.data
    names = [m.name.split(".")[0] if m else None for m in me.materials]
    used_idx = sorted({p.material_index for p in me.polygons})
    mas_idx = {i for i, n in enumerate(names) if n == MASONRY}
    mas_verts = sorted({v for p in me.polygons if p.material_index in mas_idx for v in p.vertices})
    return dict(
        obj_name=ob.name, pts=pts, bounds=bounds(pts), slots=names,
        used=[names[i] if i < len(names) else "idx%d" % i for i in used_idx],
        tris=sum(len(p.vertices) - 2 for p in me.polygons),
        ucx_names=[u.name for u in ucx], ucx_bounds=[bounds(ue_coords(u)) for u in ucx],
        mas_pts=[pts[v] for v in mas_verts],
        notch=notch_edges(ob, mas_idx),
        shade=flat_shading(ob, mas_idx),
    )


def long_lines(mpts):
    """All straight inset lines longer than MAX_LINE on the masonry vertices, as (extent, side, kind, coord, lo, hi) tuples,
    plus the longest one's description and the inset vertex count."""
    if not mpts:
        return [], "no masonry faces", 0.0
    mn, mx = bounds(mpts)
    lines, count = [], 0
    # side: (axis index of the face normal, plane value, sign of depth, axis index running along the side)
    sides = [(1, mn.y, +1, 0), (1, mx.y, -1, 0), (0, mn.x, +1, 1), (0, mx.x, -1, 1)]
    for ax, plane, sgn, al in sides:
        lo, hi = (mn.x, mx.x) if al == 0 else (mn.y, mx.y)
        ins = []
        for p in mpts:
            d = (p[ax] - plane) * sgn
            if INSET_MIN < d < INSET_MAX and lo + END_SKIP < p[al] < hi - END_SKIP:
                ins.append(p)
        count += len(ins)
        by_z, by_a = {}, {}
        for p in ins:
            by_z.setdefault(round(p.z, 1), []).append(p[al])
            by_a.setdefault(round(p[al], 1), []).append(p.z)
        side_name = "%s%s" % ("Y" if ax == 1 else "X", "min" if sgn > 0 else "max")
        for z, xs in by_z.items():
            if max(xs) - min(xs) > MAX_LINE:
                lines.append((max(xs) - min(xs), side_name, "h", z, min(xs), max(xs)))
        for a, zs in by_a.items():
            if max(zs) - min(zs) > MAX_LINE:
                lines.append((max(zs) - min(zs), side_name, "v", a, min(zs), max(zs)))
    lines.sort(reverse=True)
    return lines, count


def describe(ln, al_name="XY"):
    ext, side, kind, c, lo, hi = ln
    if kind == "h":
        return "%s horizontal line at Z %.1f, along-side %.1f..%.1f (%.0f cm)" % (side, c, lo, hi, ext)
    return "%s vertical line at along-side %.1f, Z %.1f..%.1f (%.0f cm)" % (side, c, lo, hi, ext)


def in_old(ln, old_lines):
    """True when the same line (side, kind, coordinate within 0.6 cm) exists in the old file and covers it (within 3 cm)."""
    ext, side, kind, c, lo, hi = ln
    return any(o[1] == side and o[2] == kind and abs(o[3] - c) <= 0.6 and o[4] <= lo + 3.0 and o[5] >= hi - 3.0 for o in old_lines)


def main():
    old_dir, root, only = parse_args()
    entries = json.load(open(LIST))
    if only:
        entries = [e for e in entries if any(o in e["mesh"] for o in only)]
    fails, rows, exceptions = [], [], []
    for e in entries:
        mesh = e["mesh"]
        newp = os.path.join(root, e["fbx"])
        oldp = os.path.join(old_dir, os.path.basename(e["fbx"]))
        o = load(oldp)
        n = load(newp)

        def fail(msg, mesh=mesh):
            fails.append("%s: %s" % (mesh, msg))

        # a. bounds + pivot convention
        dmax = 0.0
        for i in range(3):
            for k in (0, 1):
                dmax = max(dmax, abs(n["bounds"][k][i] - o["bounds"][k][i]))
        if dmax > TOL_B:
            fail("bounds differ by %.3f cm: new %s..%s old %s..%s" % (
                dmax, tuple(round(v, 2) for v in n["bounds"][0]), tuple(round(v, 2) for v in n["bounds"][1]),
                tuple(round(v, 2) for v in o["bounds"][0]), tuple(round(v, 2) for v in o["bounds"][1])))
        # b. used slots, same order
        if n["used"] != o["used"]:
            fail("USED SLOTS differ: new %s old %s" % (n["used"], o["used"]))
        if n["slots"] != o["slots"]:
            fail("slot list differs: new %s old %s" % (n["slots"], o["slots"]))
        # c. UCX
        ucx_d = 0.0
        if len(n["ucx_names"]) != len(o["ucx_names"]):
            fail("UCX count %d vs %d" % (len(n["ucx_names"]), len(o["ucx_names"])))
        else:
            for bn, bo in zip(n["ucx_bounds"], o["ucx_bounds"]):
                for i in range(3):
                    for q in (0, 1):
                        ucx_d = max(ucx_d, abs(bn[q][i] - bo[q][i]))
            if ucx_d > TOL_B:
                fail("UCX bounds differ by %.3f cm" % ucx_d)
        if n["ucx_names"] != o["ucx_names"]:
            fail("UCX names differ: %s vs %s" % (n["ucx_names"], o["ucx_names"]))
        # d. triangles
        if n["tris"] > o["tris"]:
            fail("triangles %d > old %d" % (n["tris"], o["tris"]))
        # f. shading
        if n["shade"][0] > NORMAL_MAX_PCT:
            fail("flat masonry faces tilted: %.1f %% of the area has a corner normal over %.0f deg off (worst %.1f deg); limit %.0f %%" % (
                n["shade"][0], NORMAL_DEG, n["shade"][1], NORMAL_MAX_PCT))
        # e. grooves
        nlines, _nin = long_lines(n["mas_pts"])
        olines, _oin = long_lines(o["mas_pts"])
        ln = nlines[0][0] if nlines else 0.0
        lo = olines[0][0] if olines else 0.0
        new_only = [x for x in nlines if not in_old(x, olines)]
        if n["notch"][0] > NOTCH_MAX_CM:
            fail("V-groove edges remain on masonry faces: %.0f cm in %d edges" % n["notch"])
        for x in nlines:
            profile = in_old(x, olines)
            exceptions.append((mesh, x, profile))
            # a line that is not in the old file cannot be a groove (the grooves existed only in the old file); it is listed
            # for a human to judge, and does not fail the run.  The V-notch check above is the pass/fail criterion for grooves.
        rows.append((mesh, o, n, dmax, ucx_d, ln, nlines, lo, olines))

    w = 118
    print("\n" + "=" * w)
    print("%-42s %-14s %-9s %-12s %-8s %-9s %-10s %-12s %s" % ("mesh", "tris o->n", "slots", "UCX n/o", "bnd d", "ucx d", "line n/o", "notch cm n/o", "tilt% n/o (worst deg n/o)"))
    for mesh, o, n, dmax, ucx_d, ln, nlines, lo, olines in rows:
        same = "same" if n["used"] == o["used"] else "DIFF"
        print("%-42s %-14s %-9s %-12s %-8.3f %-9.3f %-10s %-12s %s" % (
            mesh, "%d->%d" % (o["tris"], n["tris"]), same, "%d/%d" % (len(n["ucx_names"]), len(o["ucx_names"])),
            dmax, ucx_d, "%.0f/%.0f" % (ln, lo), "%.0f/%.0f" % (n["notch"][0], o["notch"][0]),
            "%.1f/%.1f (%.1f/%.1f)" % (n["shade"][0], o["shade"][0], n["shade"][1], o["shade"][1])))
    print("-" * w)
    print("used slots (new | old):")
    for mesh, o, n, *_ in rows:
        print("  %-42s %s | %s" % (mesh, ",".join(x.replace("MAT_", "") for x in n["used"]), ",".join(x.replace("MAT_", "") for x in o["used"])))
    tot_o = sum(r[1]["tris"] for r in rows)
    tot_n = sum(r[2]["tris"] for r in rows)
    print("-" * w)
    print("triangle total over %d meshes: old %d -> new %d (%.1f %%)" % (len(rows), tot_o, tot_n, 100.0 * (tot_n - tot_o) / max(tot_o, 1)))
    old_hits = sum(1 for r in rows if r[7] > MAX_LINE)
    old_notch = sum(1 for r in rows if r[1]["notch"][0] > NOTCH_MAX_CM)
    print("groove checks on the OLD files (sanity): inset line > %.0f cm in %d of %d; V-notch edges in %d of %d" % (
        MAX_LINE, old_hits, len(rows), old_notch, len(rows)))
    if exceptions:
        print("-" * w)
        print("long inset lines (> %.0f cm) still in NEW files, per mesh.  'profile' = the same line also exists in the OLD file, so it is" % MAX_LINE)
        print("not a groove (a step, recess or arch ring).  Arch rings give many 'lines' because two vertices at one Z on opposite sides of")
        print("an opening count as one bin.  'NEW-ONLY' lines are not in the old file at that place (an arch ring, a recess whose vertices moved); the V-notch count decides pass/fail.")
        per = {}
        for mesh, x, profile in exceptions:
            per.setdefault(mesh, []).append((x, profile))
        for mesh, xs in per.items():
            prof = [x for x, pr in xs if pr]
            newo = [x for x, pr in xs if not pr]
            print("  %-42s %3d profile, %d NEW-ONLY; longest profile: %s" % (mesh, len(prof), len(newo), describe(prof[0]) if prof else "-"))
            for x in newo:
                print("      NEW-ONLY: " + describe(x))
    if old_hits == 0 or old_notch == 0:
        fails.append("sanity: the groove checks found nothing in any OLD file; the checks are not meaningful")
    print("=" * w)
    if fails:
        print("VERIFY FAILED (%d):" % len(fails))
        for f in fails:
            print("  - " + f)
        sys.exit(1)
    print("VERIFY OK: %d pieces" % len(rows))


if __name__ == "__main__":
    main()
