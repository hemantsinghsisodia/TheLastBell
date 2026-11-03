"""P11-7 step 1: lantern glass. One new MI on M_LB_UnlitEmissive assigned to the glass slot of SM_Wooden_Lantern_01.

Spec: Docs/plans/P11_MATERIALS.md, section "P11-7: lantern glass", "Step 1: editor". Run with -I, editor open on
L_Monastery, no PIE (every mode refuses while PIE runs). Exactly one mode per run:
    --snapshot FILE   read-only: the glass slot's material, the mesh's slots, bounds, Nanite state, collision tags, dirty state
    --apply           create MI_LB_LanternGlass_Lit (parent M_LB_UnlitEmissive), Color = (1, 0.549, 0.2196, 1) x 2.0, then
                      StaticMeshTools.set_material on the glass slot ONLY; read back
    --multiplier M    Color = base x M, 1 <= M <= 4 (refuses anything else); the MI must exist
    --check           read back everything; exit 1 on any mismatch (needs the snapshot file, see --snap-file)
    --save            one package per save_assets call, 5 s apart: the MI, then the mesh (never M_LB_Surface, never a master,
                      never L_Monastery, never a Blueprint)
    --restore         puts MI_Wooden_Lantern_01_Glass back on the glass slot; read back. Saves nothing.
    --snap-file FILE  snapshot used by --check (default Docs/ArtTest/materials/p11_7_before.json)

Nothing saves unless --save is given. Exit codes: 0 ok, 1 mismatch or refused, 2 a tool call failed (state unknown:
run --check before anything else; never retry in a loop).
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE  # noqa: E402

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
MI = "editor_toolset.toolsets.material_instance.MaterialInstanceTools"
AS = "editor_toolset.toolsets.asset.AssetTools"
OB = "editor_toolset.toolsets.object.ObjectTools"
SM = "editor_toolset.toolsets.static_mesh.StaticMeshTools"
APP = "EditorToolset.EditorAppToolset"

MESH_PKG = "/Game/LastBell/ArtTest/Props/Wooden_Lantern_01/SM_Wooden_Lantern_01"
OLD_MI_PKG = "/Game/LastBell/ArtTest/Props/Wooden_Lantern_01/MI_Wooden_Lantern_01_Glass"
FRAME_MI_PKG = "/Game/LastBell/ArtTest/Props/Wooden_Lantern_01/MI_Wooden_Lantern_01"
NEW_FOLDER = "/Game/LastBell/Materials/Instances"
NEW_NAME = "MI_LB_LanternGlass_Lit"
NEW_PKG = f"{NEW_FOLDER}/{NEW_NAME}"
MASTER_PKG = "/Game/LastBell/Materials/Master/M_LB_UnlitEmissive"
GLASS_SLOT = "wooden_lantern_01_glass"
FRAME_SLOT = "wooden_lantern_01"
BASE = (1.0, 0.549, 0.2196, 1.0)     # (255, 140, 56) / 255, the lanterns' light colour
DEFAULT_MULT = 2.0
CENSUS = os.path.join(ROOT, "Docs", "ArtTest", "materials", "census_p11.json")
DEFAULT_SNAP = os.path.join(ROOT, "Docs", "ArtTest", "materials", "p11_7_before.json")
PAUSE_S = 5

# Tags that must equal the snapshot. Not Materials/StaticMaterials: the glass slot changes on purpose.
SAME_TAGS = ["AssetImportData", "NaniteEnabled", "CollisionPrims", "CollisionComplexity", "DefaultCollision",
             "ApproxSize", "SectionsWithCollision", "Vertices", "Triangles"]
SAVE_ORDER = [NEW_PKG, MESH_PKG]
NEVER_SAVE = ["/Game/LastBell/Materials/Master/M_LB_Surface", MASTER_PKG, "/Game/LastBell/Maps/L_Monastery"]
WATCH_DIRTY = NEVER_SAVE + [OLD_MI_PKG, FRAME_MI_PKG, "/Game/LastBell/Materials/Master/M_LB_Decal",
                            "/Game/LastBell/Materials/Master/M_LB_Decal_Grime"]


def ref(pkg):
    return {"refPath": f"{pkg}.{pkg.split('/')[-1]}"}


def close(a, b, tol=1e-4):
    return abs(float(a) - float(b)) <= tol


def as_json(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return v
    return v


def short(r):
    """Asset name of a {'refPath': ...} (or None)."""
    if isinstance(r, dict):
        r = r.get("refPath")
    return r.split("/")[-1].split(".")[0] if r else None


def full(r):
    return r.get("refPath") if isinstance(r, dict) else r


def is_dirty(ue, pkg):
    """is_dirty of a package; None if the asset does not exist (the tool errors on a missing asset)."""
    if not ue.call(AS, "exists", {"path": pkg}):
        return None
    return ue.call(AS, "is_dirty", {"asset_path": pkg})


def refuse_if_pie(ue):
    if ue.call(APP, "IsPIERunning", {}):
        print("refused: PIE is running. Nothing was changed.")
        return True
    return False


def vector(ue, pkg, name):
    v = ue.call(MI, "get_vector_parameter", {"instance": ref(pkg), "name": name})
    return (v["r"], v["g"], v["b"], v["a"])


def vector_overridden(ue, pkg, name):
    r = ue.call(OB, "get_properties", {"instance": ref(pkg), "properties": ["vectorParameterValues"]})
    r = as_json(r)
    return any(e["parameterInfo"]["name"] == name for e in r["vectorParameterValues"])


def mesh_state(ue):
    """Everything the snapshot and --check compare."""
    m = ref(MESH_PKG)
    slots = list(as_json(ue.call(SM, "get_material_slots", {"mesh": m})))
    mats = {s: full(as_json(ue.call(SM, "get_material", {"mesh": m, "slot_name": s}))) for s in slots}
    b = as_json(ue.call(SM, "get_bounds", {"mesh": m}))
    tags = as_json(ue.call(AS, "get_asset_tags", {"asset_path": MESH_PKG}))
    return {"slots": slots, "materials": mats,
            "bounds": {"min": [b["min"][k] for k in "xyz"], "max": [b["max"][k] for k in "xyz"]},
            "nanite": as_json(ue.call(SM, "is_nanite_enabled", {"mesh": m})),
            "tags": {k: tags.get(k) for k in SAME_TAGS + ["Materials", "StaticMaterials"]}}


def lantern_overrides(ue, slots):
    """For each of the 18 census lanterns: the override on the glass slot (None = no override)."""
    with open(CENSUS, encoding="utf-8") as f:
        lan = json.load(f)["lanterns"]
    gi = slots.index(GLASS_SLOT)
    out = []
    for L in lan:
        comp = {"refPath": L["path"] + ".StaticMeshComponent0"}
        p = as_json(ue.call(OB, "get_properties", {"instance": comp, "properties": ["staticMesh", "overrideMaterials"]}))
        ov = [full(x) for x in (p.get("overrideMaterials") or [])]
        out.append({"label": L["label"], "mesh": short(p.get("staticMesh")), "n_overrides": len(ov),
                    "glass_override": (ov[gi] if gi < len(ov) else None)})
    return out


# ------------------------------------------------------------------ snapshot
def do_snapshot(ue, path):
    st = mesh_state(ue)
    if GLASS_SLOT not in st["slots"]:
        print(f"REFUSED: slot {GLASS_SLOT} not on the mesh: {st['slots']}")
        return 1
    snap = {"taken": time.strftime("%Y-%m-%d %H:%M:%S"), "note": "values read before P11-7 step 1 changed anything",
            "mesh": MESH_PKG, "glass_slot": GLASS_SLOT, "glass_material_before": st["materials"][GLASS_SLOT], **st}
    snap["new_mi_exists"] = bool(ue.call(AS, "exists", {"path": NEW_PKG}))
    snap["old_mi_exists"] = bool(ue.call(AS, "exists", {"path": OLD_MI_PKG}))
    snap["master_exists"] = bool(ue.call(AS, "exists", {"path": MASTER_PKG}))
    snap["lanterns"] = lantern_overrides(ue, st["slots"])
    snap["dirty_before"] = {p: is_dirty(ue, p) for p in WATCH_DIRTY + SAVE_ORDER}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=1)
    print("snapshot written:", path)
    print("slots:", st["slots"], "| glass slot material:", short(snap["glass_material_before"]))
    print("bounds:", st["bounds"], "| nanite:", st["nanite"])
    print("collision tags:", {k: st["tags"][k] for k in ("CollisionPrims", "CollisionComplexity", "DefaultCollision")})
    print("lanterns read:", len(snap["lanterns"]), "| with a glass override:", sum(1 for x in snap["lanterns"] if x["glass_override"]))
    print("dirty before:", {k.split("/")[-1]: v for k, v in snap["dirty_before"].items()})
    return 0


# ------------------------------------------------------------------ colour
def set_color(ue, mult):
    want = tuple(c * mult for c in BASE[:3]) + (1.0,)
    ue.call(MI, "set_vector_parameter", {"instance": ref(NEW_PKG), "name": "Color", "value": dict(zip("rgba", want))})
    if not vector_overridden(ue, NEW_PKG, "Color"):
        ue.call(MI, "set_parameter_override", {"instance": ref(NEW_PKG), "name": "Color", "override": True})
        ue.call(MI, "set_vector_parameter", {"instance": ref(NEW_PKG), "name": "Color", "value": dict(zip("rgba", want))})
    got = vector(ue, NEW_PKG, "Color")
    ok = all(close(a, b) for a, b in zip(got, want)) and vector_overridden(ue, NEW_PKG, "Color")
    print(f"  Color set x{mult:g}: want ({want[0]:.4f}, {want[1]:.4f}, {want[2]:.4f}, 1) read back "
          f"({got[0]:.4f}, {got[1]:.4f}, {got[2]:.4f}, {got[3]:.4f}) explicit override {vector_overridden(ue, NEW_PKG, 'Color')} "
          f"{'ok' if ok else 'MISMATCH'}", flush=True)
    return ok


def do_apply(ue):
    problems = []
    if not ue.call(AS, "exists", {"path": MASTER_PKG}):
        problems.append("master M_LB_UnlitEmissive missing")
    st = mesh_state(ue)
    if GLASS_SLOT not in st["slots"]:
        problems.append(f"slot {GLASS_SLOT} missing: {st['slots']}")
    else:
        cur = short(st["materials"][GLASS_SLOT])
        if cur not in (short(OLD_MI_PKG), NEW_NAME):
            problems.append(f"glass slot holds {cur}, plan says {short(OLD_MI_PKG)} (or already {NEW_NAME})")
    if problems:
        print("REFUSED, nothing was changed:")
        for p in problems:
            print("  -", p)
        return 1
    if not ue.call(AS, "exists", {"path": NEW_PKG}):
        r = ue.call(MI, "create", {"folder_path": NEW_FOLDER, "asset_name": NEW_NAME, "parent": ref(MASTER_PKG)})
        print(f"  create {NEW_NAME} -> {r}", flush=True)
        if not ue.call(AS, "exists", {"path": NEW_PKG}):
            print(f"STOP: {NEW_NAME} not created.")
            return 1
    else:
        print(f"  {NEW_NAME} already exists, not recreated", flush=True)
    parent = short(as_json(ue.call(OB, "get_properties", {"instance": ref(NEW_PKG), "properties": ["parent"]}))["parent"])
    if parent != "M_LB_UnlitEmissive":
        print(f"STOP: parent reads {parent}")
        return 1
    ok = set_color(ue, DEFAULT_MULT)
    old = short(st["materials"][GLASS_SLOT])
    ue.call(SM, "set_material", {"mesh": ref(MESH_PKG), "slot_name": GLASS_SLOT, "material": ref(NEW_PKG)})
    after = mesh_state(ue)
    new = short(after["materials"][GLASS_SLOT])
    frame_same = after["materials"][FRAME_SLOT] == st["materials"][FRAME_SLOT]
    print(f"  slot {GLASS_SLOT}: {old} -> {new} {'ok' if new == NEW_NAME else 'MISMATCH'}; "
          f"slot {FRAME_SLOT} unchanged: {frame_same}", flush=True)
    ok = ok and new == NEW_NAME and frame_same
    print("apply:", "OK" if ok else "MISMATCH")
    return 0 if ok else 1


def do_multiplier(ue, m):
    if not (1.0 <= m <= 4.0):
        print(f"REFUSED: multiplier {m} is outside 1..4. Nothing was changed.")
        return 1
    if not ue.call(AS, "exists", {"path": NEW_PKG}):
        print(f"REFUSED: {NEW_NAME} does not exist; run --apply first.")
        return 1
    return 0 if set_color(ue, m) else 1


def do_restore(ue):
    if not ue.call(AS, "exists", {"path": OLD_MI_PKG}):
        print(f"REFUSED: {short(OLD_MI_PKG)} does not exist.")
        return 1
    ue.call(SM, "set_material", {"mesh": ref(MESH_PKG), "slot_name": GLASS_SLOT, "material": ref(OLD_MI_PKG)})
    now = short(as_json(ue.call(SM, "get_material", {"mesh": ref(MESH_PKG), "slot_name": GLASS_SLOT})))
    ok = now == short(OLD_MI_PKG)
    print(f"restore: slot {GLASS_SLOT} now {now} {'ok' if ok else 'MISMATCH'} (nothing saved)")
    return 0 if ok else 1


# ------------------------------------------------------------------ check
def do_check(ue, snap_path):
    with open(snap_path, encoding="utf-8") as f:
        snap = json.load(f)
    bad, n_ok = [], 0

    def rec(ok, what, line=None):
        nonlocal n_ok
        if ok:
            n_ok += 1
        else:
            bad.append(what)
        if line:
            print(("ok   " if ok else "FAIL ") + line, flush=True)

    # the MI
    if not ue.call(AS, "exists", {"path": NEW_PKG}):
        rec(False, f"{NEW_NAME} missing", f"{NEW_NAME} missing")
    else:
        p = as_json(ue.call(OB, "get_properties", {"instance": ref(NEW_PKG), "properties": ["parent"]}))
        par = short(p["parent"])
        rec(par == "M_LB_UnlitEmissive", f"parent {par}", f"MI parent = {par}")
        col = vector(ue, NEW_PKG, "Color")
        mult = col[0] / BASE[0]
        ratio_ok = close(col[1], BASE[1] * mult, 1e-3) and close(col[2], BASE[2] * mult, 1e-3) and close(col[3], 1.0)
        rec(ratio_ok and 1.0 - 1e-6 <= mult <= 4.0 + 1e-6 and vector_overridden(ue, NEW_PKG, "Color"),
            f"Color {col} not base x M with 1<=M<=4",
            f"Color = ({col[0]:.4f}, {col[1]:.4f}, {col[2]:.4f}, {col[3]:.4f}) = base x {mult:.4f} (explicit override "
            f"{vector_overridden(ue, NEW_PKG, 'Color')})")
    # the mesh
    st = mesh_state(ue)
    slot_ok = GLASS_SLOT in st["slots"]
    glass = short(st["materials"].get(GLASS_SLOT))
    frame = short(st["materials"].get(FRAME_SLOT))
    rec(glass == NEW_NAME, f"glass slot = {glass}", f"glass slot {GLASS_SLOT} = {glass}")
    rec(frame == short(FRAME_MI_PKG) and st["materials"].get(FRAME_SLOT) == snap["materials"].get(FRAME_SLOT),
        f"frame slot = {frame}", f"frame slot {FRAME_SLOT} = {frame} (as in snapshot: {st['materials'].get(FRAME_SLOT) == snap['materials'].get(FRAME_SLOT)})")
    rec(slot_ok and st["slots"] == snap["slots"], f"slots {st['slots']} vs {snap['slots']}", f"slots equal the snapshot: {st['slots'] == snap['slots']} {st['slots']}")
    bmax = max(abs(a - b) for k in ("min", "max") for a, b in zip(st["bounds"][k], snap["bounds"][k]))
    rec(bmax <= 1e-3, f"bounds differ by {bmax}", f"bounds equal the snapshot (max diff {bmax:.6f} cm)")
    rec(st["nanite"] == snap["nanite"] and st["nanite"] is False, f"nanite {st['nanite']} vs {snap['nanite']}", f"Nanite {st['nanite']} (snapshot {snap['nanite']})")
    diffs = [k for k in SAME_TAGS if st["tags"].get(k) != snap["tags"].get(k)]
    ct = {k: st["tags"].get(k) for k in ("CollisionPrims", "CollisionComplexity", "DefaultCollision")}
    rec(not diffs, f"tags differ: {diffs}", f"collision/import tags equal the snapshot (diffs: {diffs or 'none'}); {ct}")
    # the census actors
    if slot_ok:
        lan = lantern_overrides(ue, st["slots"])
        withov = [x["label"] for x in lan if x["glass_override"]]
        wrongmesh = [x["label"] for x in lan if x["mesh"] != "SM_Wooden_Lantern_01"]
        rec(len(lan) == 18 and not withov and not wrongmesh, f"lanterns: n={len(lan)} override {withov} wrong mesh {wrongmesh}",
            f"census lanterns: {len(lan)} read; glass-slot overrides: {withov or 'none'}; wrong mesh: {wrongmesh or 'none'}")
    # dirty
    dirty = {p.split("/")[-1]: is_dirty(ue, p) for p in WATCH_DIRTY + SAVE_ORDER}
    print("dirty now:", sorted(k for k, v in dirty.items() if v) or "none")
    print(f"CHECK: {n_ok}/{n_ok + len(bad)} items ok" + ("" if not bad else f"; {len(bad)} MISMATCH: " + "; ".join(bad)))
    return 1 if bad else 0


# ------------------------------------------------------------------ save
def do_save(ue):
    dirty_before = {p: is_dirty(ue, p) for p in SAVE_ORDER + NEVER_SAVE}
    print("not saved on purpose:", {p.split("/")[-1]: dirty_before[p] for p in NEVER_SAVE})
    for i, pkg in enumerate(SAVE_ORDER):
        assert pkg not in NEVER_SAVE and "/BP_" not in pkg and "/Master/" not in pkg
        if i:
            time.sleep(PAUSE_S)
        res = ue.call(AS, "save_assets", {"asset_paths": [pkg]})
        dirty = is_dirty(ue, pkg)
        print(f"  save {pkg.split('/')[-1]}: was dirty {dirty_before[pkg]}, returned {res}, is_dirty {dirty}", flush=True)
        if res is not True or dirty is not False:
            print(f"STOP: {pkg} did not save cleanly; later packages were not saved.")
            return 1
    after = {p.split("/")[-1]: is_dirty(ue, p) for p in WATCH_DIRTY}
    print("dirty after save (watch list):", sorted(k for k, v in after.items() if v) or "none")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", metavar="FILE")
    g.add_argument("--multiplier", metavar="M", type=float)
    for m in ("apply", "check", "save", "restore"):
        g.add_argument("--" + m, action="store_true")
    ap.add_argument("--snap-file", default=DEFAULT_SNAP)
    a = ap.parse_args()
    ue = UE()
    try:
        if refuse_if_pie(ue):
            return 1
        if a.snapshot:
            return do_snapshot(ue, a.snapshot)
        if a.apply:
            return do_apply(ue)
        if a.multiplier is not None:
            return do_multiplier(ue, a.multiplier)
        if a.restore:
            return do_restore(ue)
        if a.check:
            return do_check(ue, a.snap_file)
        return do_save(ue)
    except Exception as e:
        print(f"TOOL CALL FAILED: {str(e)[:600]}\nState unknown. Run --check before doing anything else; do not retry in a loop.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
