"""verify_fx_meshes.py -- re-imports every P15 cloth / FX card FBX in a clean headless Blender and checks it (P15-3).

    blender.exe -b --factory-startup --python Tools/blender/fx/verify_fx_meshes.py -- [--fbx SourceArt/FX] [--json out.json]

Checks per mesh (Unreal space: UE_Y = -Blender_Y of the re-imported file, see Tools/blender/kit/README.md):
  exactly one mesh object, no UCX_ collision, node at the origin with identity rotation/scale, exact slot name;
  bounds vs the plan table (+-1 cm; Y only the 3 cm fold, cards flat), pivot (x centre 0; z max 0 = top centre for the cloth and the
  BoltCard, z min 0 = bottom centre for the CurtainCard);
  UV0 as Unreal reads it (V_unreal = 1 - v_file, Unreal flips V on import): V = 0 along the top edge, V == -z / height for every
  vertex (so it increases downward), U within 0..1 and equal to the column position along the top edge;
  face normals (UE space) point +Y; no degenerate faces; triangle count in the expected band and equal to the build report;
  boundary loops: strips A, banner, sheet and the cards 1; strip B 2 (outer edge + the one hole).
Exit code 1 if any check fails.
"""
import json
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "kit")))
import verify_kit as VK  # noqa: E402  (helpers only)

TOL = 1.0
FOLD = 3.0
P = "SM_LB_"
# name: w, h, pivot ('top'|'bottom'), slot, grid (nx, ny) or None, boundary loops
SPEC = {
    "Prop_ClothStrip_A":  dict(w=35.0,  h=220.0, pivot="top",    slot="MAT_Cloth",   grid=(8, 44),  loops=1),
    "Prop_ClothStrip_B":  dict(w=25.0,  h=160.0, pivot="top",    slot="MAT_Cloth",   grid=(6, 32),  loops=2),
    "Prop_ClothBanner_A": dict(w=110.0, h=240.0, pivot="top",    slot="MAT_Cloth",   grid=(22, 48), loops=1),
    "Prop_ClothSheet_A":  dict(w=170.0, h=140.0, pivot="top",    slot="MAT_Cloth",   grid=(34, 28), loops=1),
    "FX_BoltCard":        dict(w=100.0, h=100.0, pivot="top",    slot="MAT_Bolt",    grid=None,     loops=1),
    "FX_CurtainCard":     dict(w=100.0, h=100.0, pivot="bottom", slot="MAT_Curtain", grid=None,     loops=1),
}


def argv():
    a = sys.argv
    a = a[a.index("--") + 1:] if "--" in a else []
    fbx = os.path.join(ROOT, "SourceArt", "FX")
    js = None
    for i, t in enumerate(a):
        if t == "--fbx":
            fbx = os.path.abspath(a[i + 1])
        if t == "--json":
            js = os.path.abspath(a[i + 1])
    return fbx, js


def boundary_loops(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    adj = {}
    for e in bm.edges:
        if e.is_boundary:
            a, b = e.verts[0].index, e.verts[1].index
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)
    seen, loops = set(), 0
    for s in adj:
        if s in seen:
            continue
        loops += 1
        stack = [s]
        while stack:
            v = stack.pop()
            if v in seen:
                continue
            seen.add(v)
            stack.extend(adj[v] - seen)
    bm.free()
    return loops


def check(path, short, spec, report_rec):
    res = dict(name=P + short, ok=True, fails=[], notes=[])

    def fail(msg):
        res['ok'] = False
        res['fails'].append(msg)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if len(obs) != 1:
        fail("expected exactly 1 mesh object, found %d (%s)" % (len(obs), [o.name for o in obs]))
        return res
    ob = obs[0]
    me = ob.data
    if any(o.name.startswith("UCX_") for o in obs):
        fail("collision mesh present")
    # node
    if (ob.matrix_world.translation.length > 1e-3 or any(abs(s - 1.0) > 1e-4 for s in ob.scale)
            or any(abs(r) > 1e-4 for r in ob.rotation_euler)):
        res['notes'].append("node transform: loc %s rot %s scale %s (importer axis fix, ignored if vertices are right)"
                            % (tuple(round(v, 3) for v in ob.matrix_world.translation), tuple(round(r, 3) for r in ob.rotation_euler), tuple(round(s, 3) for s in ob.scale)))
    # slots
    slots = [m.name if m else None for m in me.materials]
    if slots != [spec['slot']]:
        fail("slots %s, expected [%s]" % (slots, spec['slot']))

    pts = VK.ue_coords(ob)
    mn, mx = VK.bounds(pts)
    dims = mx - mn
    res['dims'] = [round(v, 2) for v in dims]
    res['bounds_min'] = [round(v, 2) for v in mn]
    res['bounds_max'] = [round(v, 2) for v in mx]
    w, h = spec['w'], spec['h']
    cloth = short.startswith("Prop_Cloth")
    if abs(dims.x - w) > TOL:
        fail("width %.2f, expected %.1f" % (dims.x, w))
    if abs(dims.z - h) > TOL:
        fail("height %.2f, expected %.1f" % (dims.z, h))
    if cloth:
        if mx.y > FOLD + 0.5 or mn.y < -FOLD - 0.5:
            fail("Y range %.2f..%.2f exceeds the %.0f cm fold" % (mn.y, mx.y, FOLD))
        if dims.y < 1.5:
            fail("no baked fold: Y range only %.2f cm" % dims.y)
    elif dims.y > 0.01:
        fail("card is not flat: Y range %.3f" % dims.y)
    # pivot
    if abs((mn.x + mx.x) * 0.5) > TOL:
        fail("pivot: X centre %.2f" % ((mn.x + mx.x) * 0.5))
    if spec['pivot'] == "top":
        if abs(mx.z) > TOL:
            fail("pivot: top edge at z %.2f (expected 0, hangs to -%.0f)" % (mx.z, h))
    else:
        if abs(mn.z) > TOL:
            fail("pivot: bottom edge at z %.2f (expected 0)" % mn.z)
    # UV0 (Unreal V = 1 - v_file)
    uvl = me.uv_layers.active
    if uvl is None:
        fail("no UV layer")
    else:
        worst_v = 0.0
        worst_u_top = 0.0
        top_n = 0
        us = []
        ztop = mx.z if spec['pivot'] == "top" else mx.z
        for p in me.polygons:
            for li, vi in zip(p.loop_indices, p.vertices):
                u, vf = uvl.data[li].uv
                vu = 1.0 - vf
                z = pts[vi].z
                if spec['pivot'] == "top":
                    expect_v = (ztop - z) / h
                else:
                    expect_v = (ztop - z) / h
                worst_v = max(worst_v, abs(vu - expect_v))
                us.append(u)
                if abs(z - ztop) < 1e-3:
                    top_n += 1
                    worst_u_top = max(worst_u_top, abs(vu))      # V along the top edge must be 0
        if worst_v > 0.01:
            fail("UV V deviates from the downward ramp by %.4f (V_unreal should be (top - z) / height)" % worst_v)
        if worst_u_top > 1e-3:
            fail("V along the top edge is not 0 (max %.4f)" % worst_u_top)
        if top_n < 2:
            fail("no top-edge vertices found")
        if min(us) < -1e-4 or max(us) > 1 + 1e-4 or abs(min(us)) > 1e-3 or abs(max(us) - 1.0) > 1e-3:
            fail("U range %.4f..%.4f, expected 0..1" % (min(us), max(us)))
        res['notes'].append("UV: V_unreal = 1 - v_file, ramp error %.5f, top-edge V error %.5f, U %.3f..%.3f" % (worst_v, worst_u_top, min(us), max(us)))
    # normals (UE space = (nx, -ny, nz)) and degenerate faces
    me.calc_loop_triangles()
    worst_ny = 1.0
    degenerate = 0
    for p in me.polygons:
        n = p.normal
        ny_ue = -n.y
        worst_ny = min(worst_ny, ny_ue)
        if p.area < 1e-3:
            degenerate += 1
    if cloth:
        if worst_ny <= 0.0:
            fail("a face normal points -Y in UE space (min ny %.3f)" % worst_ny)
    elif worst_ny < 0.999:
        fail("card normal ny %.4f, expected +Y" % worst_ny)
    if degenerate:
        fail("%d degenerate faces" % degenerate)
    res['notes'].append("min face-normal Y (UE space) %.3f" % worst_ny)
    # triangle count
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    res['tris'] = tris
    g = spec['grid']
    if g:
        full = g[0] * g[1] * 2
        if not (0.55 * full <= tris <= full + 4 * g[0]):
            fail("triangle count %d outside the band %d..%d for the %dx%d grid" % (tris, int(0.55 * full), full + 4 * g[0], g[0], g[1]))
    elif tris != 2:
        fail("card should be 2 triangles, has %d" % tris)
    if report_rec and report_rec.get('tris') != tris:
        fail("triangle count %d differs from the build report %s" % (tris, report_rec.get('tris')))
    # boundary loops
    loops = boundary_loops(me)
    res['loops'] = loops
    if loops != spec['loops']:
        fail("boundary loops %d, expected %d" % (loops, spec['loops']))
    return res


def main():
    fbx, js = argv()
    rep_path = os.path.join(fbx, "fx_meshes_report.json")
    report = json.load(open(rep_path)) if os.path.exists(rep_path) else {}
    results = []
    for short, spec in SPEC.items():
        path = os.path.join(fbx, P + short + ".fbx")
        if not os.path.exists(path):
            results.append(dict(name=P + short, ok=False, fails=["FBX missing: " + path], notes=[]))
            continue
        results.append(check(path, short, spec, report.get(P + short)))
    bad = 0
    for r in results:
        print("%-4s %-28s dims %-22s tris %-5s loops %s" % ("PASS" if r['ok'] else "FAIL", r['name'], r.get('dims'), r.get('tris'), r.get('loops')))
        for n in r['notes']:
            print("       . " + n)
        for f in r['fails']:
            print("       ! " + f)
        bad += 0 if r['ok'] else 1
    print("%d/%d meshes pass" % (len(results) - bad, len(results)))
    if js:
        with open(js, "w") as fh:
            json.dump(results, fh, indent=1)
    sys.stdout.flush()
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
