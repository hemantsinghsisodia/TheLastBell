"""convert_cc0.py -- converts the Poly Haven glTF props (P7F-1 downloads) to Unreal-ready FBX.  Plan: P7F-2a.

    blender.exe -b --factory-startup --python Tools/blender/props/convert_cc0.py -- [--src ExternalAssets/Incoming] [--out SourceArt/Props/CC0] [--only wine_barrel_01 ...] [--split-all]

Per model: import the glTF, apply all transforms, scale metres -> centimetres, join / split as the table below says,
PIVOT = BOTTOM-CENTRE (XY centre of the bounds at the origin, min Z = 0), rename to SM_LB_CC0_<CamelName>[_NN],
keep the original material names as slot names (materials are replaced by plain same-named ones so the FBX carries no
texture paths), add ONE `UCX_` box (= bounds) for the "collision" items, export with the kit FBX settings
(kit_lib.export_piece_fbx: axis_forward Y / axis_up Z, cm units, ue_y_flip, mesh_smooth_type OFF) and copy the texture files the
materials use next to the FBX.  Original UV0 is kept; vertex colour "Color" = white.  Writes <out>/cc0_report.json.

Smoothing: faces smooth, edges sharper than 50 degrees hard (the glTF custom normals are not carried; Unreal imports the
exported normals).  CC0 (Poly Haven): textures and models may be committed.
"""
import json
import math
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "kit")))

import bpy
import bmesh
from mathutils import Matrix, Vector

import kit_lib as K

PREFIX = "SM_LB_CC0_"
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SMOOTH_DEG = 50.0

# id -> (CamelName, mode, ucx, decimate_to_tris)
#   mode "join": every mesh object of the glTF becomes ONE mesh.  mode "split": one mesh per object (sorted by object name -> _01, _02 ...).
MODELS = [
    ("wine_barrel_01", "WineBarrel01", "join", True, None),
    ("wooden_bucket_01", "WoodenBucket01", "join", False, None),
    ("wooden_bucket_02", "WoodenBucket02", "join", False, None),
    ("wooden_table_02", "WoodenTable02", "join", True, None),
    ("dead_tree_trunk", "DeadTreeTrunk", "join", True, None),
    ("tree_stump_01", "TreeStump01", "join", True, None),
    ("dry_branches_medium_01", "DryBranchesMedium01", "join", False, None),
    ("weed_plant_02", "WeedPlant02", "split", False, None),
    ("nettle_plant", "NettlePlant", "split", False, None),
    ("fern_02", "Fern02", "split", False, None),
    ("moss_01", "Moss01", "split", False, None),
    ("rusted_spade_01", "RustedSpade01", "join", False, None),
    ("picke_dirty_01", "PickeDirty01", "join", False, None),
    ("wooden_axe", "WoodenAxe", "join", False, None),
    ("wooden_candlestick", "WoodenCandlestick", "join", False, 8000),     # source mesh is 213k tris -> decimate (see report)
    ("rock_moss_set_02", "RockMossSet02", "split", True, None),
]


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    src = os.path.join(ROOT, "ExternalAssets", "Incoming")
    out = os.path.join(ROOT, "SourceArt", "Props", "CC0")
    only, split_all = [], False
    i = 0
    while i < len(argv):
        if argv[i] == "--src":
            src = os.path.abspath(argv[i + 1]); i += 2
        elif argv[i] == "--out":
            out = os.path.abspath(argv[i + 1]); i += 2
        elif argv[i] == "--split-all":
            split_all = True; i += 1          # every glTF object becomes its own mesh (also the plants / moss)
        elif argv[i] == "--only":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                only.append(argv[i]); i += 1
        else:
            i += 1
    return src, out, only, split_all


def mat_images(mat, src_dir):
    """Absolute paths of the image files a glTF-imported material uses."""
    found = []
    if mat is None or not mat.use_nodes:
        return found
    for n in mat.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image:
            p = bpy.path.abspath(n.image.filepath) if n.image.filepath else ""
            if not (p and os.path.exists(p)):
                p = os.path.join(src_dir, "textures", os.path.basename(n.image.name))
            found.append(os.path.normpath(p))
    return found


def import_model(gltf):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=gltf)
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    for o in obs:
        o.data = o.data.copy()                    # unique data, safe to bake transforms in
        me = o.data
        me.transform(o.matrix_world)              # apply location/rotation/scale (incl. importer axis conversion)
        me.transform(Matrix.Scale(100.0, 4))      # metres -> centimetres
        o.parent = None
        o.matrix_world = Matrix.Identity(4)
    return obs


def unify_duplicate_materials(obs, src_dir):
    """'name.001' duplicates that use the same images as 'name' are merged into 'name'."""
    for o in obs:
        for i, m in enumerate(o.data.materials):
            if m is None:
                continue
            base = m.name.rsplit(".", 1)[0] if m.name.rsplit(".", 1)[-1].isdigit() else m.name
            bm_ = bpy.data.materials.get(base)
            if base != m.name and bm_ is not None and sorted(mat_images(m, src_dir)) == sorted(mat_images(bm_, src_dir)):
                o.data.materials[i] = bm_


def decimate(ob, target_tris):
    me = ob.data
    me.calc_loop_triangles()
    n = len(me.loop_triangles)
    if n <= target_tris:
        return n
    md = ob.modifiers.new("dec", 'DECIMATE')
    md.decimate_type = 'COLLAPSE'
    md.ratio = target_tris / n
    md.use_collapse_triangulate = True
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    new = bpy.data.meshes.new_from_object(ev, depsgraph=dg)
    ob.modifiers.remove(md)
    old = ob.data
    ob.data = new
    bpy.data.meshes.remove(old)
    return n


def to_bmesh(objs):
    """Join the objects' meshes (already in cm, world space) into one bmesh, keeping UVs and material indices.
    Returns (bm, slot_material_names)."""
    slots = []
    bm = bmesh.new()
    for o in objs:
        me = o.data
        sl_map = []
        for m in me.materials:
            nm = (m.get("orig", m.name) if m else "MAT_None")
            if nm not in slots:
                slots.append(nm)
            sl_map.append(slots.index(nm))
        tmp = bmesh.new()
        tmp.from_mesh(me)
        uv_src = tmp.loops.layers.uv.active
        for f in tmp.faces:
            f.material_index = sl_map[f.material_index] if f.material_index < len(sl_map) else 0
        if not bm.loops.layers.uv:
            bm.loops.layers.uv.new("UVMap")
        uv_dst = bm.loops.layers.uv[0]
        vmap = {v: bm.verts.new(v.co) for v in tmp.verts}
        for f in tmp.faces:
            try:
                nf = bm.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                continue
            nf.material_index = f.material_index
            if uv_src is not None:
                for ls, ld in zip(f.loops, nf.loops):
                    ld[uv_dst].uv = ls[uv_src].uv
        tmp.free()
    return bm, slots


def seat_pivot(bm):
    mn, mx = K.bm_bounds(bm)
    s = (-(mn[0] + mx[0]) * 0.5, -(mn[1] + mx[1]) * 0.5, -mn[2])
    K.bm_translate(bm, *s)
    return s


def finish(bm):
    bm.normal_update()
    col = bm.loops.layers.color.get("Color") or bm.loops.layers.color.new("Color")
    lim = math.radians(SMOOTH_DEG)
    for f in bm.faces:
        f.smooth = True
        for l in f.loops:
            l[col] = (1.0, 1.0, 1.0, 1.0)
    for e in bm.edges:
        e.smooth = (len(e.link_faces) != 2) or e.calc_face_angle(0.0) <= lim
    return bm


def orientation_hint(bm):
    """Horizontal extent (cm) of the top / bottom 15 % of the height -- tells which end of a tool is the head."""
    mn, mx = K.bm_bounds(bm)
    h = mx[2] - mn[2]

    def ext(sel):
        if not sel:
            return [0.0, 0.0]
        return [round(max(v.co[i] for v in sel) - min(v.co[i] for v in sel), 1) for i in (0, 1)]

    top = [v for v in bm.verts if v.co.z >= mx[2] - 0.15 * h]
    bot = [v for v in bm.verts if v.co.z <= mn[2] + 0.15 * h]
    return dict(top15_xy_extent=ext(top), bottom15_xy_extent=ext(bot))


def run():
    src, out, only, split_all = parse_args()
    t0 = time.time()
    report = []
    for mid, camel, mode, ucx, dec_to in MODELS:
        if only and mid not in only:
            continue
        d = os.path.join(src, "polyhaven-" + mid)
        gl = [f for f in os.listdir(d) if f.endswith(".gltf")] if os.path.isdir(d) else []
        if not gl:
            print("MISSING", mid)
            report.append(dict(id=mid, status="missing"))
            continue
        obs = import_model(os.path.join(d, gl[0]))
        unify_duplicate_materials(obs, d)
        # texture files per material (read before the materials are replaced)
        mat_tex = {}
        for o in obs:
            for m in o.data.materials:
                if m and m.name not in mat_tex:
                    mat_tex[m.name] = mat_images(m, d)
        obs = sorted(obs, key=lambda o: o.name)
        plain = {}                                # original material name -> plain same-named material
        for o in obs:
            for m in o.data.materials:
                if m and "orig" not in m:
                    m["orig"] = m.name
                    m.name = m.name + "__src"
                    pm = bpy.data.materials.new(m["orig"])
                    pm.diffuse_color = (0.5, 0.5, 0.5, 1.0)
                    plain[m["orig"]] = pm
        src_tris = 0
        for o in obs:
            o.data.calc_loop_triangles()
            src_tris += len(o.data.loop_triangles)
        decimated_from = None
        if dec_to:
            for o in obs:
                decimated_from = decimate(o, dec_to)
        groups = []
        if mode == "split":
            groups = [("%s_%02d" % (camel, i + 1), [o]) for i, o in enumerate(obs)]
        elif split_all and len(obs) > 1:
            groups = [("%s_%02d" % (camel, i + 1), [o]) for i, o in enumerate(obs)]
        else:
            groups = [(camel, obs)]
        out_dir = os.path.join(out, camel)
        os.makedirs(out_dir, exist_ok=True)
        K.setup_scene_units()
        used_tex = set()
        for gname, gobs in groups:
            bm, slots = to_bmesh(gobs)
            shift_v = seat_pivot(bm)
            finish(bm)
            name = PREFIX + gname
            # plain same-named materials (no node trees -> no texture paths in the FBX)
            mats = [plain[s] for s in slots]
            mn, mx = K.bm_bounds(bm)
            ucx_list = [K.box_hull(mn[0], mx[0], mn[1], mx[1], mn[2], mx[2])] if ucx else []
            fbx = os.path.join(out_dir, name + ".fbx")
            K.export_piece_fbx(name, bm, ucx_list, fbx, mats)
            texs = sorted({t for s in slots for t in mat_tex.get(s, [])})
            used_tex.update(texs)
            rec = dict(id=mid, mesh=name, status="ok", source_objects=[o.name for o in gobs],
                       min=[round(v, 2) for v in mn], max=[round(v, 2) for v in mx],
                       dims_cm=[round(mx[i] - mn[i], 2) for i in range(3)], tris=K.tri_count(bm), slots=slots,
                       ucx=len(ucx_list), textures=[os.path.basename(t) for t in texs], pivot_shift_cm=[round(v, 2) for v in shift_v],
                       orientation=orientation_hint(bm))
            if decimated_from:
                rec['decimated_from_tris'] = decimated_from
            rec['source_total_tris'] = src_tris
            report.append(rec)
            print("MODEL", json.dumps(rec))
        for t in used_tex:
            if os.path.exists(t):
                shutil.copy2(t, os.path.join(out_dir, os.path.basename(t)))
            else:
                print("WARN texture not found", t)
    os.makedirs(out, exist_ok=True)
    rp = os.path.join(out, "cc0_report.json")
    old = []
    if only and os.path.exists(rp):
        with open(rp) as fh:
            old = [r for r in json.load(fh) if r.get('id') not in only]
    with open(rp, "w") as fh:
        json.dump(old + report, fh, indent=1)
    print("DONE %d records in %.1fs -> %s" % (len(report), time.time() - t0, out))


if __name__ == "__main__":
    run()
