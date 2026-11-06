"""p13_import.py -- P13-3: import the owner's Mixamo downloads (Y Bot + 12 clips) into Unreal through the MCP tools.

    python -I Tools/warden/p13_import.py --import   # preflight, Y Bot, then every clip (re-runnable: finished steps are skipped)
    python -I Tools/warden/p13_import.py --check    # read-back of every asset + the actor count (makes no edits)
    python -I Tools/warden/p13_import.py --save     # save each new package with ONE save_assets call each, is_dirty after

Editor open on L_Monastery, PIE off. Never saves L_Monastery or anything outside /Game/LastBell/Characters/Warden/Retarget.

What it does (plan docs/plans/P13_WARDEN_ANIMATION.md section 5.1, MCP_NOTES "Skeletal meshes and the Warden" 1-3, 14):
  * MX_YBot.fbx -> SK_LB_YBot (+ SK_LB_YBot_Skeleton, SK_LB_YBot_PhysicsAsset, named by the tool).
  * Each clip FBX: import_file with skeleton = SK_LB_YBot_Skeleton under the throwaway mesh name TMP_<Name>. Unreal makes
    two sequences per Mixamo FBX: TMP_<Name>_Anim_mixamo_com (the real clip) and TMP_<Name>_Anim_Take_001 (the FBX's empty
    default take, a different frame count). The real clip is picked by its frame count (keys == the Blender frame count);
    it is moved to AN_YBot_<Name>, the other sequence, the throwaway mesh and its physics asset are deleted.
  * get_referencers returns nothing at all (None) for a package that has never been saved (no registry data), so the
    "no referencers" check is the weaker one possible here: the throwaways can only be referenced by each other.
    Deletes are checked with `exists` afterwards and leftovers are listed.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mcp"))
from ue import UE  # noqa: E402

SK = "editor_toolset.toolsets.skeletal_mesh.SkeletalMeshTools"
AS = "editor_toolset.toolsets.asset.AssetTools"
OB = "editor_toolset.toolsets.object.ObjectTools"
SC = "editor_toolset.toolsets.scene.SceneTools"
APP = "EditorToolset.EditorAppToolset"

FOLDER = "/Game/LastBell/Characters/Warden/Retarget"
SRC = r"C:\Hemant\Prj\Learning\TheLastBell\ExternalAssets\Incoming\mixamo"
MAP = "/Game/LastBell/Maps/L_Monastery"
ACTORS = 2980
YBOT = "SK_LB_YBot"
SKEL = YBOT + "_Skeleton"
PHYS = YBOT + "_PhysicsAsset"

# name (file MX_<name>.fbx) -> frame count from the lead's Blender check (== numberOfSampledKeys in Unreal)
CLIPS = [
    ("MutantWalking", 44), ("ZombieWalk", 122), ("MutantRun", 27), ("ZombieRunning", 25), ("MutantIdle", 122),
    ("CrouchedWalking", 32), ("CrouchingIdle", 76), ("TurnLeft90", 29), ("TurnRight90", 29), ("ZombieAttack", 80),
    ("MutantSwiping", 81), ("LookAround", 135),
]


def ref(name):
    return {"refPath": "%s/%s.%s" % (FOLDER, name, name)}


def pkg(name):
    return "%s/%s" % (FOLDER, name)


def listing(ue):
    return sorted(p.rsplit("/", 1)[1] for p in ue.call(AS, "find_assets", {"folder_path": FOLDER, "name": ""}))


def exists(ue, name):
    return ue.call(AS, "exists", {"path": pkg(name)}) is True


def referencers(ue, name):
    """List, or None when the registry has nothing (an unsaved package returns None, which the client reports as an error)."""
    try:
        return ue.call(AS, "get_referencers", {"asset_path": pkg(name)})
    except RuntimeError as e:
        if "NoneType" in str(e):
            return None
        raise


def actor_count(ue):
    # the connection sometimes resets on this big result (seen once in P13-3): retry on a fresh session
    for attempt in range(3):
        try:
            return len(ue.call(SC, "find_actors", {"name": "", "tag": "", "collision_channels": []}))
        except (ConnectionError, OSError):
            if attempt == 2:
                raise
            ue.__init__()


def anim_info(ue, name):
    d = ue.call(OB, "get_properties", {"instance": ref(name), "properties": [
        "sequenceLength", "numberOfSampledFrames", "numberOfSampledKeys", "skeleton", "bEnableRootMotion", "rateScale"]})
    if isinstance(d, str):
        d = json.loads(d)
    return d


def preflight(ue):
    assert ue.call(APP, "IsPIERunning", {}) is False, "PIE is running"
    cur = ue.call(SC, "get_current_level", {})
    assert cur == MAP, "current level is %s" % cur
    assert ue.call(AS, "is_dirty", {"asset_path": MAP}) is False, "L_Monastery is dirty"
    n = actor_count(ue)
    assert n == ACTORS, "actor count %d, expected %d" % (n, ACTORS)
    if not ue.call(AS, "exists", {"path": FOLDER}):
        assert ue.call(AS, "create_folder", {"path": FOLDER}) is True
    print("preflight ok: PIE off, %s clean, %d actors, folder %s" % (MAP, n, FOLDER))


def ybot_readback(ue):
    m = ref(YBOT)
    bones = ue.call(SK, "get_bone_names", {"mesh": m})
    b = ue.call(SK, "get_bounds", {"mesh": m})
    height = b["boxExtent"]["z"] * 2
    print("Y Bot: %d bones, root=%s, parent of %s=%s" % (len(bones), bones[0], bones[1], ue.call(SK, "get_bone_parent", {"mesh": m, "bone_name": bones[1]})))
    print("  origin", b["origin"], "extent", b["boxExtent"])
    print("  height (2 x extent Z) = %.1f cm; width (2 x extent X, T-pose arms) = %.1f cm" % (height, b["boxExtent"]["x"] * 2))
    print("  skeleton", ue.call(SK, "get_skeleton", {"mesh": m})["refPath"], "physics", ue.call(SK, "get_physics_asset", {"mesh": m})["refPath"])
    assert 150 < height < 220, "Y Bot height %.1f is not about 180 cm (a 100x scale error?)" % height
    return bones


def import_ybot(ue):
    if exists(ue, YBOT):
        print("skip: %s already exists" % YBOT)
    else:
        r = ue.call(SK, "import_file", {"folder_path": FOLDER, "asset_name": YBOT, "source_file": os.path.join(SRC, "MX_YBot.fbx"),
                                        "import_materials": False, "import_textures": False, "import_animations": False,
                                        "create_physics_asset": True})
        print("imported", r)
    for n in (YBOT, SKEL, PHYS):
        assert exists(ue, n), "%s missing" % n
    ybot_readback(ue)


def delete_checked(ue, name, leftovers):
    refs = referencers(ue, name)
    print("  delete %s (referencers: %s)" % (name, "none registered (unsaved package)" if refs is None else refs))
    if refs:
        raise RuntimeError("%s has referencers %s; not deleting" % (name, refs))
    ok = ue.call(AS, "delete", {"path": pkg(name)})
    still = exists(ue, name)
    print("    delete ->", ok, "| still exists:", still)
    if still or ok is not True:
        leftovers.append(name)


def harvest_clip(ue, name, frames, leftovers):
    """Turn whatever TMP_<name>* assets exist into AN_YBot_<name>, delete the rest."""
    tmp = "TMP_" + name
    final = "AN_YBot_" + name
    have = [n for n in listing(ue) if n.startswith(tmp + "_Anim")]
    if not exists(ue, final):
        cands = {}
        for n in have:
            d = anim_info(ue, n)
            cands[n] = d
            print("  candidate %s: length %.4f s, %d keys, %d sampled frames" % (n, d["sequenceLength"], d["numberOfSampledKeys"], d["numberOfSampledFrames"]))
        pick = [n for n, d in cands.items() if d["numberOfSampledKeys"] == frames]
        assert len(pick) == 1, "%s: expected exactly one sequence with %d keys, got %s" % (name, frames, pick)
        assert ue.call(AS, "move", {"path": pkg(pick[0]), "new_path": pkg(final)}) is True, "move failed"
        print("  moved %s -> %s" % (pick[0], final))
        assert exists(ue, final)
        if exists(ue, pick[0]):
            print("  NOTE: old path %s still exists after the move (redirector?)" % pick[0])
            leftovers.append(pick[0])
    for n in listing(ue):
        if n.startswith(tmp + "_Anim"):
            delete_checked(ue, n, leftovers)
    if exists(ue, tmp):
        delete_checked(ue, tmp, leftovers)
    if exists(ue, tmp + "_PhysicsAsset"):
        delete_checked(ue, tmp + "_PhysicsAsset", leftovers)


def import_clip(ue, name, frames, leftovers):
    final, tmp = "AN_YBot_" + name, "TMP_" + name
    print("== %s (expect %d frames)" % (name, frames))
    if not exists(ue, final) and not exists(ue, tmp):
        r = ue.call(SK, "import_file", {"folder_path": FOLDER, "asset_name": tmp, "source_file": os.path.join(SRC, "MX_%s.fbx" % name),
                                        "skeleton": {"refPath": ref(SKEL)["refPath"]}, "import_materials": False,
                                        "import_textures": False, "import_animations": True, "create_physics_asset": True})
        print("  imported", r)
    harvest_clip(ue, name, frames, leftovers)
    d = anim_info(ue, final)
    assert d["skeleton"]["refPath"] == ref(SKEL)["refPath"], "%s is on skeleton %s" % (final, d["skeleton"])
    assert d["numberOfSampledKeys"] == frames, "%s: %d keys, expected %d" % (final, d["numberOfSampledKeys"], frames)
    print("  %s: %.4f s, %d keys (%d sampled frames), root motion %s" % (final, d["sequenceLength"], d["numberOfSampledKeys"], d["numberOfSampledFrames"], d["bEnableRootMotion"]))


def do_import(ue):
    preflight(ue)
    import_ybot(ue)
    leftovers = []
    for name, frames in CLIPS:
        import_clip(ue, name, frames, leftovers)
    print("folder now:", listing(ue))
    stray = [n for n in listing(ue) if n.startswith("TMP_")]
    print("leftover TMP_* assets:", stray if stray else "none")
    print("delete problems:", leftovers if leftovers else "none")
    print("actor count:", actor_count(ue))
    return 1 if stray or leftovers else 0


def do_check(ue):
    print("PIE running:", ue.call(APP, "IsPIERunning", {}), "| level:", ue.call(SC, "get_current_level", {}),
          "| map dirty:", ue.call(AS, "is_dirty", {"asset_path": MAP}))
    names = listing(ue)
    print("assets in folder:", names)
    ybot_readback(ue)
    bad = 0
    print("%-28s %-22s %9s %6s %7s %s" % ("sequence", "skeleton", "length_s", "keys", "expect", "dirty"))
    for name, frames in CLIPS:
        final = "AN_YBot_" + name
        if not exists(ue, final):
            print("%-28s MISSING" % final)
            bad += 1
            continue
        d = anim_info(ue, final)
        sk = d["skeleton"]["refPath"].rsplit("/", 1)[1]
        ok = d["numberOfSampledKeys"] == frames and sk == "%s.%s" % (SKEL, SKEL)
        bad += 0 if ok else 1
        print("%-28s %-22s %9.4f %6d %7d %s %s" % (final, sk, d["sequenceLength"], d["numberOfSampledKeys"], frames,
                                                  ue.call(AS, "is_dirty", {"asset_path": pkg(final)}), "" if ok else "<-- MISMATCH"))
    stray = [n for n in names if n.startswith("TMP_")]
    print("leftover TMP_* assets:", stray if stray else "none")
    n = actor_count(ue)
    print("actor count: %d (expect %d)" % (n, ACTORS))
    return 1 if bad or stray or n != ACTORS else 0


def do_save(ue):
    assert ue.call(APP, "IsPIERunning", {}) is False, "PIE is running"
    todo = [YBOT, SKEL, PHYS] + ["AN_YBot_" + n for n, _ in CLIPS]
    failed = []
    for n in todo:
        if not exists(ue, n):
            print("%-28s MISSING, not saved" % n)
            failed.append(n)
            continue
        r = ue.call(AS, "save_assets", {"asset_paths": [pkg(n)]})
        dirty = ue.call(AS, "is_dirty", {"asset_path": pkg(n)})
        print("%-28s save_assets -> %s | dirty after: %s" % (n, r, dirty))
        if dirty:
            failed.append(n)
    print("map dirty:", ue.call(AS, "is_dirty", {"asset_path": MAP}), "(never saved by this script)")
    print("not saved clean:", failed if failed else "none")
    return 1 if failed else 0


def main():
    mode = [a for a in sys.argv[1:] if a in ("--import", "--check", "--save")]
    if len(mode) != 1:
        print(__doc__)
        return 2
    ue = UE()
    return {"--import": do_import, "--check": do_check, "--save": do_save}[mode[0]](ue)


if __name__ == "__main__":
    sys.exit(main())
