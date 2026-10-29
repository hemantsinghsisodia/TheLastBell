"""build_tower.py -- procedurally builds the P10-3a bell tower pieces T1..T14 (Blender 5.2, headless).  Plan: Docs/plans/P10_BELLTOWER_ART.md, amendment D1.1 / D1.2.

    blender.exe -b --factory-startup --python Tools/blender/belltower/build_tower.py -- [--out SourceArt/BellTower] [--only NAME ...] [--tag NAME]

Writes one FBX per mesh (SourceArt/BellTower/<MeshName>.fbx, UCX_ collision in the same file), the review file LB_BellTower.blend
(un-mirrored authoring versions laid out in rows; `--only` writes LB_BellTower_<tag|partial>.blend instead) and tower_report.json (bounds / tris / slots / UCX).
Everything is seeded and reproducible.  The piece code lives in tw_walls.py, tw_timber.py, tw_bell.py and tw_roof.py (shared helpers: tw_common.py);
the kit helpers (kit_lib / build_kit / build_props) are imported, never modified.

Conventions: kit conventions (1 BU = 1 cm, authoring space == Unreal space, FBX mirrored in Y at export by kit_lib.export_piece_fbx).  Each piece is built directly in the
frame its D1 row names (face frame, flight frame, landing frame, bottom centre, ...), so the pivot is NOT re-seated automatically.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import tw_common as C  # noqa: E402
from tw_common import K, bpy  # noqa: E402
import tw_walls as W  # noqa: E402
import tw_timber as T  # noqa: E402
import tw_bell as B  # noqa: E402
import tw_roof as R  # noqa: E402

PX = C.PREFIX


def table():
    """(mesh name, builder).  Expected values live in verify_tower.py."""
    rows = []
    for stage in ("S1", "S2", "S3"):
        for face in ("W", "N", "E", "S"):
            rows.append((W.name_of(stage, face), (lambda s=stage, f=face: W.build_wall(s, f, False))))
            if stage == "S3" and face in ("W", "S"):
                rows.append((W.name_of(stage, face, True), (lambda s=stage, f=face: W.build_wall(s, f, True))))
    rows += [
        (PX + "Roof_BrokenSW", R.build_roof),
        (PX + "Louvre_130x450", lambda: T.build_louvre(False)),
        (PX + "Louvre_130x450_Broken", lambda: T.build_louvre(True)),
        (PX + "ShaftBase_420x420x450", T.build_shaft_base),
        (PX + "ShaftPost_20x20x2015", T.build_shaft_post),
        (PX + "StairFlight_250x420", lambda: T.build_flight("")),
        (PX + "StairFlight_250x420_Closed", lambda: T.build_flight("Closed")),
        (PX + "StairFlight_250x420_BrokenA", lambda: T.build_flight("BrokenA")),
        (PX + "StairFlight_250x420_BrokenB", lambda: T.build_flight("BrokenB")),
        (PX + "FlightRail_420", T.build_flight_rail),
        (PX + "Landing_250", T.build_landing),
        (PX + "BelfryFloor", T.build_belfry_floor),
        (PX + "TopRail_670", lambda: T.build_top_rail(670.0)),
        (PX + "TopRail_420", lambda: T.build_top_rail(420.0)),
        (PX + "Partition_250x455", T.build_partition),
        (PX + "BellFrame_A", T.build_bell_frame),
        (PX + "BellHeadstock_A", T.build_headstock),
        (C.PROP_PREFIX + "GreatBell_A", B.build_bell),
        (C.PROP_PREFIX + "BellRope_2610", B.build_rope),
    ]
    return rows


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.join(C.ROOT, "SourceArt", "BellTower")
    only, tag = [], None
    i = 0
    while i < len(argv):
        if argv[i] == "--out":
            out = os.path.abspath(argv[i + 1])
            i += 2
        elif argv[i] == "--tag":
            tag = argv[i + 1]
            i += 2
        elif argv[i] == "--only":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                only.append(argv[i])
                i += 1
        else:
            i += 1
    return out, only, tag


def run():
    out_dir, only, tag = parse_args()
    K.setup_scene_units()
    report, pieces = [], []
    t0 = time.time()
    for nm, fn in table():
        if only and not any(o in nm for o in only):
            continue
        t = time.time()
        pc = fn()
        mn, mx = K.bm_bounds(pc.bm)
        used = sorted({f.material_index for f in pc.bm.faces})
        C.finish(pc)
        K.export_piece_fbx(pc.name, pc.bm, pc.ucx, os.path.join(out_dir, pc.name + ".fbx"), C.mats(pc.slots))
        rec = dict(name=pc.name, min=[round(v, 2) for v in mn], max=[round(v, 2) for v in mx],
                   dims=[round(mx[i] - mn[i], 2) for i in range(3)], tris=K.tri_count(pc.bm), slots=pc.slots,
                   slots_used=used, ucx=len(pc.ucx), note=pc.note, seconds=round(time.time() - t, 1))
        if pc.extra:
            rec["extra"] = pc.extra
        report.append(rec)
        print("PIECE", json.dumps(rec))
        pieces.append(pc)
    # review layout (un-mirrored authoring versions, rows by family)
    x, row_y, row_h = 0.0, 0.0, 0.0
    for pc in pieces:
        mn, mx = K.bm_bounds(pc.bm)
        w, d = mx[0] - mn[0], mx[1] - mn[1]
        if x + w > 9000.0:
            x, row_y, row_h = 0.0, row_y + row_h + 300.0, 0.0
        K.add_to_layout(pc.name, pc.bm, pc.ucx, (x - mn[0], row_y - mn[1], 0.0), C.mats(pc.slots))
        x += w + 150.0
        row_h = max(row_h, d + 200.0)
    os.makedirs(out_dir, exist_ok=True)
    suffix = ("_" + tag) if tag else "_partial"
    blend = os.path.join(out_dir, "LB_BellTower.blend" if not only else "LB_BellTower%s.blend" % suffix)
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    rp = os.path.join(out_dir, "tower_report.json")
    if only and os.path.exists(rp):                      # partial rebuild keeps the records of the pieces that were not rebuilt
        with open(rp) as fh:
            old = [r for r in json.load(fh) if r["name"] not in {x_["name"] for x_ in report}]
        report = old + report
        order = [n for n, _f in table()]
        report.sort(key=lambda r: order.index(r["name"]) if r["name"] in order else 999)
    with open(rp, "w") as fh:
        json.dump(report, fh, indent=1)
    print("DONE %d pieces in %.1fs -> %s" % (len(pieces), time.time() - t0, out_dir))


if __name__ == "__main__":
    run()
