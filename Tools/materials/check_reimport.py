"""check_reimport.py -- P11-4b/4c: snapshot the 51 masonry meshes in the open Unreal editor, and check them after a Reimport.

    python -I Tools/materials/check_reimport.py --snapshot Docs/ArtTest/materials/p11_reimport_before.json
    python -I Tools/materials/check_reimport.py --check Docs/ArtTest/materials/p11_reimport_before.json [--only SUBSTR]

Uses Tools/mcp/ue.py (the editor must be open, MCP server on http://127.0.0.1:8000/mcp).  READ-ONLY: it calls only
get_asset_tags, get_material_slots, get_material, is_nanite_enabled and is_dirty.  It never saves, imports or reimports.

Mesh list: Tools/materials/p11_reimport_list.json (mesh, package, fbx, old_md5, new_md5).

--check, per mesh, PASS only when all of these hold:
  * the imported FBX is the rebuilt one: AssetImportData FileMD5 == new_md5.  If it still equals old_md5 the result is
    "FAIL not reimported"; if it equals neither, "FAIL FileMD5 matches neither the old nor the new FBX";
  * these tags equal the snapshot: Materials, NaniteEnabled, CollisionPrims, CollisionComplexity, DefaultCollision;
  * the material slot names are equal and in the same order, and each slot's default material is the same;
  * is_nanite_enabled equals the snapshot;
  * StaticMeshTools.get_bounds equals the FBX's dims in its build report within 1 cm per axis.
    (Not the ApproxSize tag: it reads larger than the real mesh and varies, e.g. 435x77x802 for a 400x60x800 wall whose actor bounds were exact.)
  * Vertices is fewer than or equal to the snapshot's.
Whether the package is dirty is printed for information (a fresh Reimport leaves it dirty; the lead saves each mesh alone).
Exit code 1 when any mesh fails.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Tools", "mcp"))
from ue import UE  # noqa: E402

LIST = os.path.join(HERE, "p11_reimport_list.json")
REPORTS = ("SourceArt/Kit/kit_report.json", "SourceArt/Cloister/cloister_report.json", "SourceArt/BellTower/tower_report.json")
ASSET = "editor_toolset.toolsets.asset.AssetTools"
SMESH = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
KEEP = ["AssetImportData", "Materials", "NaniteEnabled", "CollisionPrims", "CollisionComplexity", "DefaultCollision",
        "ApproxSize", "StaticMaterials", "SectionsWithCollision", "Vertices", "Triangles"]
MUST_EQUAL = ["Materials", "NaniteEnabled", "CollisionPrims", "CollisionComplexity", "DefaultCollision"]


def as_json(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return v
    return v


def read_mesh(ue, e):
    pkg = e["package"]
    ref = {"refPath": "%s.%s" % (pkg, pkg.rsplit("/", 1)[1])}
    out = {"mesh": e["mesh"], "package": pkg}
    try:
        tags = as_json(ue.call(ASSET, "get_asset_tags", {"asset_path": pkg}))
        out["tags"] = {k: tags.get(k) for k in KEEP}
        slots = as_json(ue.call(SMESH, "get_material_slots", {"mesh": ref}))
        out["slots"] = list(slots)
        out["default_materials"] = {}
        for s in slots:
            m = as_json(ue.call(SMESH, "get_material", {"mesh": ref, "slot_name": s}))
            out["default_materials"][s] = m.get("refPath") if isinstance(m, dict) else m
        out["nanite"] = as_json(ue.call(SMESH, "is_nanite_enabled", {"mesh": ref}))
        b = as_json(ue.call(SMESH, "get_bounds", {"mesh": ref}))
        out["bounds_size"] = [b["max"][k] - b["min"][k] for k in "xyz"]
        out["dirty"] = as_json(ue.call(ASSET, "is_dirty", {"asset_path": pkg}))
    except Exception as ex:  # keep going: one unreadable mesh must show up as a FAIL, not stop the run
        out["error"] = "%s: %s" % (type(ex).__name__, str(ex)[:300])
    return out


def file_md5(tags):
    """FileMD5 inside the AssetImportData tag (a JSON-ish string), or None."""
    aid = (tags or {}).get("AssetImportData")
    if not aid:
        return None
    try:
        data = json.loads(aid)
        return data[0].get("FileMD5") if isinstance(data, list) and data else None
    except Exception:
        import re
        m = re.search(r'"FileMD5"\s*:\s*"([0-9a-fA-F]{32})"', aid)
        return m.group(1).lower() if m else None


_dims = {}


def report_dims():
    if not _dims:
        for rel in REPORTS:
            with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
                for r in json.load(fh):
                    _dims[r["name"]] = r["dims"]
    return _dims


def check_one(before, now, e):
    """Return a list of failure strings (empty = PASS)."""
    if "error" in now:
        return ["could not read the mesh: " + now["error"]]
    if "error" in before:
        return ["snapshot has no data for this mesh: " + before["error"]]
    md5 = file_md5(now["tags"])
    if md5 == e["old_md5"]:
        return ["not reimported (FileMD5 still equals old_md5 %s)" % md5]
    if e.get("new_md5") is None:
        return ["new_md5 missing in p11_reimport_list.json"]
    fails = []
    if md5 != e["new_md5"]:
        fails.append("FileMD5 %s matches neither the old nor the new FBX (new_md5 %s)" % (md5, e["new_md5"]))
    bt, nt = before["tags"], now["tags"]
    for k in MUST_EQUAL:
        if bt.get(k) != nt.get(k):
            fails.append("%s changed: %r -> %r" % (k, bt.get(k), nt.get(k)))
    if before["slots"] != now["slots"]:
        fails.append("material slots changed: %s -> %s" % (before["slots"], now["slots"]))
    else:
        for s in now["slots"]:
            if before["default_materials"].get(s) != now["default_materials"].get(s):
                fails.append("default material of %s changed: %s -> %s" % (s, before["default_materials"].get(s), now["default_materials"].get(s)))
    if before.get("nanite") != now.get("nanite"):
        fails.append("is_nanite_enabled changed: %s -> %s" % (before.get("nanite"), now.get("nanite")))
    dims = report_dims().get(e["mesh"])
    size = now.get("bounds_size")
    if not dims:
        fails.append("no build report dims for %s" % e["mesh"])
    elif not size:
        fails.append("real bounds unreadable")
    elif any(abs(d - s) > 1.0 for d, s in zip(dims, size)):
        fails.append("real bounds %s differ from the FBX dims %s" % (size, dims))
    try:
        if int(nt.get("Vertices")) > int(bt.get("Vertices")):
            fails.append("Vertices grew: %s -> %s" % (bt.get("Vertices"), nt.get("Vertices")))
    except Exception:
        fails.append("Vertices unreadable: %r / %r" % (bt.get("Vertices"), nt.get("Vertices")))
    return fails


def main():
    argv = sys.argv[1:]
    entries = json.load(open(LIST))
    if "--snapshot" in argv:
        out = os.path.abspath(argv[argv.index("--snapshot") + 1])
        ue = UE()
        snap = {"count": len(entries), "meshes": []}
        for e in entries:
            r = read_mesh(ue, e)
            snap["meshes"].append(r)
            print("%-44s %s" % (e["mesh"], r.get("error") or "slots %s nanite %s FileMD5 %s" % (len(r["slots"]), r["nanite"], file_md5(r["tags"]))))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w") as fh:
            json.dump(snap, fh, indent=1)
        bad = [m["mesh"] for m in snap["meshes"] if "error" in m]
        print("snapshot of %d meshes written to %s; %d unreadable" % (len(entries), out, len(bad)))
        sys.exit(1 if bad else 0)
    if "--check" in argv:
        before_path = os.path.abspath(argv[argv.index("--check") + 1])
        only = argv[argv.index("--only") + 1] if "--only" in argv else None
        before = {m["mesh"]: m for m in json.load(open(before_path))["meshes"]}
        sel = [e for e in entries if not only or only in e["mesh"]]
        if not sel:
            print("no mesh matches --only %r" % only)
            sys.exit(2)
        ue = UE()
        failed = 0
        n_not_re = 0
        for e in sel:
            now = read_mesh(ue, e)
            fails = check_one(before[e["mesh"]], now, e)
            dirty = now.get("dirty")
            if fails:
                failed += 1
                n_not_re += any(f.startswith("not reimported") for f in fails)
            print("%-4s %-44s dirty=%s%s" % ("FAIL" if fails else "PASS", e["mesh"], dirty, ("  " + "; ".join(fails)) if fails else ""))
        print("-" * 100)
        print("%d checked, %d passed, %d failed (%d of them 'not reimported')" % (len(sel), len(sel) - failed, failed, n_not_re))
        sys.exit(1 if failed else 0)
    print(__doc__)
    sys.exit(2)


if __name__ == "__main__":
    main()
