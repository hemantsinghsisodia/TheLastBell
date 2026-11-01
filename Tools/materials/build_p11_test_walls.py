"""build_p11_test_walls.py -- P11-3b: no-groove copies of five kit pieces for the wall comparison test.

    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --factory-startup --python Tools/materials/build_p11_test_walls.py

The kit walls carry modelled V-grooves (horizontal course joints, vertical block joints, weathered recesses).
These copies use the SAME builders, sizes and seeds (read from build_kit.table()), but K.relief_cutters is wrapped
so every call gets h_grooves=False, vertical=False, recess_prob=0.0.  Chips stay.  Neither kit file is edited and
build_kit's __main__ is not run.  Output: SourceArt/P11/<MeshName>.fbx (UCX_ hulls included, same export path as the kit).

Note: skipping the groove branches consumes fewer random numbers inside relief_cutters, so the chip positions are
not identical to the originals (same count, same size range, different corner picks).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Tools", "blender", "kit"))

import bpy  # noqa: E402
import kit_lib as K  # noqa: E402
import build_kit as BK  # noqa: E402

OUT_DIR = os.path.join(ROOT, "SourceArt", "P11")
NEW_PREFIX = "SM_LB_P11_NoGroove_"

# original table key -> new mesh name
TARGETS = {
    "Wall_400x60x800_A": NEW_PREFIX + "Wall_400x60x800_A",
    "Wall_400x60x800_B": NEW_PREFIX + "Wall_400x60x800_B",
    "Wall_100x60x800": NEW_PREFIX + "Wall_100x60x800",
    "Trim_Plinth_400x80x60": NEW_PREFIX + "Plinth_400x80x60",
    "Trim_Plinth_100x80x60": NEW_PREFIX + "Plinth_100x80x60",
}

# ---- the override: build_kit calls K.relief_cutters (attribute lookup at call time), so this reaches every caller
_orig = K.relief_cutters
CALLS = {"n": 0}


def _no_grooves(*a, **kw):
    CALLS["n"] += 1
    kw.update(h_grooves=False, vertical=False, recess_prob=0.0)
    return _orig(*a, **kw)


K.relief_cutters = _no_grooves


def main():
    K.setup_scene_units()
    K.get_materials()
    table = {nm: fn for nm, fn, _dims in BK.table()}
    report = []
    for key, new_name in TARGETS.items():
        # builders compute names as PREFIX + <key>; swap the prefix, then fix the plinth names (kit key says Trim_Plinth)
        BK.PREFIX = NEW_PREFIX
        pc = table[key]()
        BK.PREFIX = "SM_LB_Kit_"
        pc.name = new_name
        mn, mx = K.bm_bounds(pc.bm)
        K.finalize(pc.bm, smooth_deg=getattr(pc, 'smooth', 30.0))
        path = os.path.join(OUT_DIR, new_name + ".fbx")
        K.export_piece_fbx(pc.name, pc.bm, pc.ucx, path, BK.mats_for(pc.slots))
        used = sorted({f.material_index for f in pc.bm.faces})
        rec = dict(name=pc.name, source=key, min=[round(v, 2) for v in mn], max=[round(v, 2) for v in mx],
                   dims=[round(mx[i] - mn[i], 2) for i in range(3)], spec=list(pc.dims), tris=K.tri_count(pc.bm),
                   verts=len(pc.bm.verts), slots_used=used, ucx=len(pc.ucx))
        report.append(rec)
        print("PIECE", json.dumps(rec))
    print("relief_cutters wrapper calls:", CALLS["n"])
    print("DONE %d pieces -> %s" % (len(report), OUT_DIR))


if __name__ == "__main__":
    main()
