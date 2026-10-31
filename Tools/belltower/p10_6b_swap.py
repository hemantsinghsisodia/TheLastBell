"""P10-6b child-Blueprint swaps (D1.17 sections 1-6). Unreal MCP; editor open on L_Monastery, PIE stopped.

Usage:
    python p10_6b_swap.py bells            # Bell_1..4 -> BP_SmallBell_Cloister
    python p10_6b_swap.py inscription      # Clue_Inscription -> BP_Inscription_Cloister
    python p10_6b_swap.py capstan          # Mech_Ritual3 -> BP_RitualMechanism_TowerCapstan at (11780, 1760, 50)
    python p10_6b_swap.py doors            # Door_Tower (scale z 1.036), Door_Shortcut -> BP_Door_Base_Dungeon
    python p10_6b_swap.py note             # Note_Cloister BodyText
    python p10_6b_swap.py <step> --dry     # print what would be set, edit nothing
Per swap (D-051 / MCP_NOTES 5): dump `<label>_before.json` (already in Docs/ArtTest/belltower/p10_6b), spawn the child at the
transform, set the instance values listed in the step and read each back, delete the old actor, apply the SAME label and folder,
dump `<label>_after.json` and print the diff against `_before`. Old component meshes / material overrides are never copied.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "mcp"))
from ue import UE  # noqa: E402
import bp_swap  # noqa: E402

S, A, O = bp_swap.S, bp_swap.A, bp_swap.O
OUT = os.path.join(HERE, "..", "..", "Docs", "ArtTest", "belltower", "p10_6b")
BP = "/Game/LastBell/Blueprints/"
BAND = "/Game/LastBell/Environments/BellTower/Materials/MI_LB_BellBand_%s.MI_LB_BellBand_%s"
COMMENT = {"Bell_1": ("I", 1.30), "Bell_2": ("II", 1.15), "Bell_3": ("III", 1.00), "Bell_4": ("IV", 0.85)}

# InteractComp values copied from the old instance (D1.17 s0 copy rule). The tag fields are also re-fed by the construction scripts.
IC_KEYS = ["promptText", "bEnabled", "deniedPromptText", "requiredStateTags", "grantedStateTags", "bSingleUse", "consumedStateTag",
           "bInspectOnInteract", "noiseLoudness"]

DRY = "--dry" in sys.argv
ue = UE()


def load_before(label):
    return json.load(open(os.path.join(OUT, label + "_before.json")))


def cref(actor, comp):
    return {"refPath": actor["refPath"] + "." + comp}


def get(obj, names):
    r = ue.call(O, "get_properties", {"instance": obj, "properties": names})
    return json.loads(r) if isinstance(r, str) else r


def set_read(obj, values, tag):
    """set_properties then read each key back; returns the list of mismatches."""
    ue.call(O, "set_properties", {"instance": obj, "values": json.dumps(values)})
    back = get(obj, list(values.keys()))
    bad = []
    for k, v in values.items():
        if not _close(v, back.get(k)):
            bad.append((k, v, back.get(k)))
    print("  %-34s set %s: %s" % (tag, ",".join(values), "OK" if not bad else "MISMATCH %s" % bad), flush=True)
    return bad


def _close(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return all(k in b and _close(v, b[k]) for k, v in a.items())
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) < 1e-4
    return a == b


def ic_values(before):
    p = before["components"]["InteractComp"]["props"]
    return {k: p[k] for k in IC_KEYS if k in p}


def swap(label, child_class, actor_vals, xform=None, ic=True, extra_comp=None):
    before = load_before(label)
    xf = xform or before["transform"]
    print("== swap %s -> %s at %s" % (label, child_class.split("/")[-1], json.dumps(xf)), flush=True)
    if DRY:
        print("  actor values:", json.dumps(actor_vals)[:400])
        return None
    old = bp_swap.find_exact(ue, label)
    folder = before["folder"]
    new = ue.call(S, "add_to_scene_from_class", {"actor_type": {"refPath": child_class + "_C"}, "name": "", "xform": xf})
    if not new:
        raise RuntimeError("spawn failed for " + label)
    ue.call(A, "set_actor_transform", {"actor": new, "xform": xf, "worldspace": True})   # full transform, never partial
    bad = []
    if actor_vals:
        bad += set_read(new, actor_vals, "actor")
    if ic:
        bad += set_read(cref(new, "InteractComp"), ic_values(before), "InteractComp")
    for comp, vals in (extra_comp or {}).items():
        bad += set_read(cref(new, comp), vals, comp)
    if bad:
        print("  !! read-back mismatches on the NEW actor; old actor left in place, new actor", new["refPath"], "kept for inspection")
        raise RuntimeError("read-back mismatch for %s: %s" % (label, bad))
    ue.call(S, "remove_from_scene", {"actor": old})
    ue.call(A, "set_label", {"actor": new, "label": label})
    ue.call(S, "set_actor_folder", {"actor": new, "folder_path": folder})
    if bp_swap.find_exact(ue, label)["refPath"] != new["refPath"]:
        raise RuntimeError("label %s does not resolve to the new actor" % label)
    d = bp_swap.dump_actor(ue, label)
    json.dump(d, open(os.path.join(OUT, label + "_after.json"), "w"), indent=1)
    bp_swap.cmd_diff(os.path.join(OUT, label + "_before.json"), os.path.join(OUT, label + "_after.json"))
    return new


def tagc(*tags):
    return {"gameplayTags": [{"tagName": t} for t in tags]}


def do_bells():
    for label, (numeral, scale) in COMMENT.items():
        b = load_before(label)["actor"]
        vals = {k: b[k] for k in ("struckTag", "symbolIndex", "swingDegrees", "swingDuration")}
        vals["bellScale"] = scale
        vals["bandMaterial"] = {"refPath": BAND % (numeral, numeral)}
        swap(label, BP + "Puzzles/BP_SmallBell_Cloister.BP_SmallBell_Cloister", vals)


def do_inscription():
    b = load_before("Clue_Inscription")
    swap("Clue_Inscription", BP + "Interactables/BP_Inscription_Cloister.BP_Inscription_Cloister", {"text": b["actor"]["text"]}, ic=False)


def do_capstan():
    b = load_before("Mech_Ritual3")["actor"]
    vals = {k: b[k] for k in ("ritualTag", "extraGrantedTags", "turnYaw", "turnDuration")}
    vals["requiredTags"] = tagc("State.Tower.BellsSolved")
    xf = {"location": {"x": 11780, "y": 1760, "z": 50}, "rotation": {"pitch": 0, "yaw": 0, "roll": 0}, "scale": {"x": 1, "y": 1, "z": 1}}
    swap("Mech_Ritual3", BP + "Interactables/BP_RitualMechanism_TowerCapstan.BP_RitualMechanism_TowerCapstan", vals, xform=xf)


def do_doors():
    for label, scale in (("Door_Tower", {"x": 1, "y": 1, "z": 1.036}), ("Door_Shortcut", {"x": 1, "y": 1.18, "z": 1.30})):   # P10-6d (D1.19)
        before = load_before(label)
        b = before["actor"]
        vals = {k: b[k] for k in ("openStateTag", "autoOpenTag", "openYaw", "openDuration", "bInteractable")}   # openSign is not settable (read-only var, value 1 = old value; the diff verifies it)
        xf = dict(before["transform"])
        xf["scale"] = scale
        swap(label, BP + "Interactables/BP_Door_Base_Dungeon.BP_Door_Base_Dungeon", vals, xform=xf)


NOTE = ("The great bell rang again tonight, and no hand was on the rope. Brother Anselm says the four small bells beside the tower "
        "door still answer to the old order of the dead, and that the order is cut in the stone above them. Strike them as the dead "
        "recall, and the tower will open. I will not go up. God forgive whoever does.")


def do_note():
    print("== Note_Cloister BodyText")
    if DRY:
        return
    a = bp_swap.find_exact(ue, "Note_Cloister")
    print("  before:", get(a, ["displayName", "bodyText"]))
    set_read(a, {"bodyText": NOTE}, "actor")
    back = get(a, ["displayName", "bodyText"])
    print("  after: displayName=%r bodyText==NOTE: %s" % (back["displayName"], back["bodyText"] == NOTE))
    d = bp_swap.dump_actor(ue, "Note_Cloister")
    json.dump(d, open(os.path.join(OUT, "Note_Cloister_after.json"), "w"), indent=1)
    bp_swap.cmd_diff(os.path.join(OUT, "Note_Cloister_before.json"), os.path.join(OUT, "Note_Cloister_after.json"))


def do_greatbell():
    """D1.18 decision 1: Mesh is the ROOT of BP_TagInteractable, so the child is placed at (12420, 2000, 2860), scale 1 (T12 pivot = crown top)."""
    before = load_before("Bell")
    b = before["actor"]
    vals = {k: b[k] for k in ("useStateTag", "bHideOnUse", "bInspectable")}
    ip = before["components"]["InspectableComp"]["props"]
    insp = {k: ip[k] for k in ("displayName", "bodyText", "bKeepOnClose", "bAutoFaceCamera", "initialInspectRotation") if k in ip}
    xf = {"location": {"x": 12420, "y": 2000, "z": 2860}, "rotation": {"pitch": 0, "yaw": 0, "roll": 0}, "scale": {"x": 1, "y": 1, "z": 1}}
    swap("Bell", BP + "Interactables/BP_TagInteractable_GreatBell.BP_TagInteractable_GreatBell", vals, xform=xf, extra_comp={"InspectableComp": insp})


def do_capstan2():
    """D1.18 decision 2: Mech_Ritual3 moves again to (11790, 1780, 50), yaw 90 (no other value changes). Edits the actor in place."""
    print("== move Mech_Ritual3 -> (11790, 1780, 50) yaw 90")
    if DRY:
        return
    a = bp_swap.find_exact(ue, "Mech_Ritual3")
    xf = {"location": {"x": 11790, "y": 1780, "z": 50}, "rotation": {"pitch": 0, "yaw": 90, "roll": 0}, "scale": {"x": 1, "y": 1, "z": 1}}
    ue.call(A, "set_actor_transform", {"actor": a, "xform": xf, "worldspace": True})
    print("  transform now:", ue.call(A, "get_actor_transform", {"actor": a}))


STEPS = {"greatbell": do_greatbell, "capstan2": do_capstan2, "bells": do_bells, "inscription": do_inscription, "capstan": do_capstan, "doors": do_doors, "note": do_note}

if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else ""
    if step not in STEPS:
        print(__doc__)
        sys.exit(2)
    lvl = ue.call(S, "get_current_level", {})
    assert lvl == "/Game/LastBell/Maps/L_Monastery", lvl
    assert ue.call("EditorToolset.EditorAppToolset", "IsPIERunning", {}) in (False, "false"), "PIE is running"
    STEPS[step]()
