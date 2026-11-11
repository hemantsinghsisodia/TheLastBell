"""P17-2: create DA_Cinematics and SMX_LB_CineFade headless (Unreal CLOSED).

Run (editor closed, one Unreal process at a time):
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>
Environment variables (the same pattern as Tools/audio/p16_2_assets.py):
    LB_OUT   path of the JSON report
    LB_MODE  "apply" (default): create or update, save the changed packages explicitly, then verify in the same process
             "verify": read-only, nothing is created, set or saved; run it in a FRESH process to prove what is on disk

What it does (docs/plans/P17_CINEMATICS.md sections 2.2, 3.1, 3.3, 4 and 6):
 1. /Game/LastBell/Audio/Mix/SMX_LB_CineFade (SoundMix): SoundClassEffects for SCL_LB_Ambience, SCL_LB_SFX, SCL_LB_Voice and SCL_LB_Music (owner 2026-11-11: the
    TowerTop drone fades with everything else at mix:on) at
    VolumeAdjuster 0.0, FadeInTime 4.0, FadeOutTime 1.0, Duration -1, EQ off.
 2. /Game/LastBell/Data/DA_Cinematics (class /Script/LastBell.LBCinematicSettings): the two Cinematics rows (with FailSafeMarkers), the
    seven Cards, the Credits (Docs/plans/p17_credits.json, made by Tools/cine/make_credits.py), every number and tag of section 2.2 and
    CineFadeMix = the soft path of SMX_LB_CineFade. The Sequence pointers are soft paths to LS_LB_Intro / LS_LB_Finale, which P17-5a
    creates later; a soft path to a missing asset is fine.

Idempotent: a value is written only when the read-back differs, and only changed packages are saved. It touches ONLY those two packages
(the guard is `allowed()`); the save is explicit per package (EditorAssetLibrary.save_asset(path, False)), never save-all. It never
loads or saves DA_Audio, DA_StormSettings, DA_StormFX, any map or LS_P17_Spike.

The process exit code of UnrealEditor-Cmd is NOT reliable; read the report (`ok`) or the log line "P17-2 RESULT". On any failed check the
script ends with an uncaught RuntimeError.
"""
import json
import os
import re
import traceback

import unreal

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
CREDITS_JSON = os.path.join(ROOT, "Docs", "plans", "p17_credits.json")
OUT = os.environ.get("LB_OUT", "")
MODE = os.environ.get("LB_MODE", "apply").lower()
APPLY = MODE == "apply"

DATA = "/Game/LastBell/Data"
DA_PATH = DATA + "/DA_Cinematics"
MIX_DIR = "/Game/LastBell/Audio/Mix"
SMX_PATH = MIX_DIR + "/SMX_LB_CineFade"
SEQ_DIR = "/Game/LastBell/Cinematics"
ALLOWED = (DA_PATH, SMX_PATH)

EAL = unreal.EditorAssetLibrary
TL = unreal.ToolsetLibrary
ATOOLS = unreal.AssetToolsHelpers.get_asset_tools()

report = {"mode": MODE, "ok": False, "checks": 0, "failures": [], "counts": {}, "saved": [], "notes": [], "set_log": [], "readback": {}}
changed_packages = set()


def check(name, ok, detail=""):
    report["checks"] += 1
    if not ok:
        msg = "%s: %s" % (name, detail)
        report["failures"].append(msg)
        unreal.log_error("P17-2 CHECK FAILED: " + msg)
    return bool(ok)


def note(text):
    report["notes"].append(text)
    unreal.log("P17-2: " + text)


def allowed(path):
    return path in ALLOWED


def mark_changed(obj):
    changed_packages.add(obj.get_outermost().get_name())


def record(owner, prop, value):
    report["set_log"].append("%s.%s = %s" % (owner, prop, value if not isinstance(value, unreal.Object) else value.get_name()))


def feq(a, b, tol=1e-4):
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


def same(a, b):
    try:
        if isinstance(b, bool) or isinstance(a, bool):
            return bool(a) == bool(b)
        if isinstance(b, (int, float)):
            return feq(a, b)
        if isinstance(b, unreal.Object) or isinstance(a, unreal.Object):
            return a == b
        return str(a) == str(b)
    except Exception:
        return False


def set_prop(obj, prop, value, owner):
    """set_editor_property only when the value differs; the read-back must match."""
    cur = obj.get_editor_property(prop)
    if same(cur, value):
        return True
    if not APPLY:
        return check("%s.%s" % (owner, prop), False, "wanted %r read %r" % (value, cur))
    obj.set_editor_property(prop, value)
    mark_changed(obj)
    record(owner, prop, value)
    now = obj.get_editor_property(prop)
    return check("set %s.%s" % (owner, prop), same(now, value), "wanted %r read %r" % (value, now))


def find_or_create(path, asset_class, factory):
    """Loads the asset at path, or creates it (apply mode). Returns the asset or None."""
    assert allowed(path), "refusing to touch %s" % path
    if EAL.does_asset_exist(path):
        asset = EAL.load_asset(path)
        check("loads " + path, asset is not None)
        return asset
    if not APPLY:
        check("exists " + path, False, "missing")
        return None
    folder, name = path.rsplit("/", 1)
    asset = ATOOLS.create_asset(name, folder, asset_class, factory)
    check("created " + path, asset is not None)
    if asset is not None:
        mark_changed(asset)
        record(name, "(created)", asset.get_class().get_name())
    return asset


def object_path(package_path):
    return "%s.%s" % (package_path, package_path.rsplit("/", 1)[1])


# ---------------------------------------------------------------------------------------------------------------------------------
# JSON read-back comparison (ToolsetLibrary.get_object_properties vs what was written)
# ---------------------------------------------------------------------------------------------------------------------------------

ENUM_KEYS = {"trigger", "style", "initiallock", "bellswingaxis"}  # compared without case and without an "EName::" prefix


def text_of(act):
    """A string from an FText / FName / path read-back (a plain string, or an object with the text in a known key)."""
    if act is None:
        return ""
    if isinstance(act, dict):
        for key in ("sourceString", "SourceString", "text", "Text", "value", "Value", "displayString", "DisplayString", "refPath", "tagName"):
            if key in act:
                return str(act[key])
        return json.dumps(act, sort_keys=True)
    return str(act)


def norm_enum(x):
    return text_of(x).split("::")[-1].strip().lower()


def deref(s):
    """/Script/Engine.SoundMix'/Game/x.x' -> /Game/x.x"""
    m = re.search(r"'([^']*)'", s)
    return m.group(1) if m else s


def subset_eq(exp, act, path, errors):
    """exp must be contained in act. Numbers by tolerance; map and member keys case-insensitively; enums loosely; texts exactly."""
    key = path.rsplit(".", 1)[-1].split("[")[0].lower()
    if isinstance(exp, dict):
        if set(exp.keys()) == {"refPath"}:
            got = deref(text_of(act))
            if got != exp["refPath"]:
                errors.append("%s: ref %r != %r" % (path, got, exp["refPath"]))
            return
        if not isinstance(act, dict):
            errors.append("%s: expected an object, read %r" % (path, str(act)[:80]))
            return
        lower = {k.lower(): v for k, v in act.items()}
        for k, value in exp.items():
            if k.lower() not in lower:
                errors.append("%s.%s: missing in read-back (keys %s)" % (path, k, sorted(lower.keys())[:12]))
                continue
            subset_eq(value, lower[k.lower()], "%s.%s" % (path, k), errors)
    elif isinstance(exp, list):
        if not isinstance(act, list) or len(act) != len(exp):
            errors.append("%s: expected %d items, read %s" % (path, len(exp), len(act) if isinstance(act, list) else repr(act)[:60]))
            return
        for i, (e, a) in enumerate(zip(exp, act)):
            subset_eq(e, a, "%s[%d]" % (path, i), errors)
    elif isinstance(exp, bool):
        got = act if isinstance(act, bool) else str(act).strip().lower() in ("true", "1")
        if got != exp:
            errors.append("%s: %r != %r" % (path, act, exp))
    elif isinstance(exp, (int, float)):
        try:
            ok = feq(act, exp, 1e-5)
        except Exception:
            ok = False
        if not ok:
            errors.append("%s: %r != %r" % (path, act, exp))
    else:
        if key in ENUM_KEYS:
            ok = norm_enum(act) == norm_enum(exp)
        elif exp == "":
            ok = text_of(act) in ("", "None")
        else:
            ok = text_of(act) == str(exp)
        if not ok:
            errors.append("%s: %r != %r" % (path, act, exp))


# ---------------------------------------------------------------------------------------------------------------------------------
# Data (plan sections 2.2, 3.1, 3.3)
# ---------------------------------------------------------------------------------------------------------------------------------

CARDS = [  # (id, text, style, hold seconds, fade seconds): plan 3.1 (Intro_1 as the owner changed it) and 3.3
    ("Intro_1", "For forty years, no one has come back from the monastery on the ridge.", "Line", 2.4, 0.3),
    ("Intro_2", "Its great bell fell silent the night the brothers vanished.", "Line", 2.4, 0.3),
    ("Intro_3", "Tonight, the whole village heard it ring.", "Line", 2.4, 0.3),
    ("Intro_4", "Someone has to go up.", "Line", 2.4, 0.3),
    ("Title", "THE LAST BELL", "Title", 3.5, 0.8),
    ("End_1", "The bell rings for you.", "Line", 3.5, 0.8),
    ("End_2", "THE LAST BELL", "Title", 4.0, 0.8),
]

SCALARS = [  # (python property, JSON property, value)
    ("credits_seconds", "CreditsSeconds", 40.0),
    ("skip_hold_seconds", "SkipHoldSeconds", 1.0),
    ("mark_seconds", "MarkSeconds", 1.5),
    ("look_assist_seconds", "LookAssistSeconds", 1.5),
    ("bell_swing_kick_degrees", "BellSwingKickDegrees", 6.0),
    ("bell_swing_max_degrees", "BellSwingMaxDegrees", 16.0),
    ("bell_swing_period_seconds", "BellSwingPeriodSeconds", 2.6),
    ("bell_swing_damping_per_second", "BellSwingDampingPerSecond", 0.25),
]


def load_credits():
    lines = json.load(open(CREDITS_JSON, encoding="utf-8"))
    check("credits file is a non-empty list", isinstance(lines, list) and len(lines) > 0, CREDITS_JSON)
    for i, line in enumerate(lines):
        check("credits[%d] style" % i, line.get("style") in ("Heading", "Name", "Small", "Gap"), line)
        check("credits[%d] text" % i, isinstance(line.get("text"), str))
    return [{"style": l["style"], "text": l["text"]} for l in lines]


def tag(name):
    return {"tagName": name}


def seq_value(name, variant):
    path = object_path(SEQ_DIR + "/" + name)
    return {"refPath": path} if variant == "ref" else path


def build_expected(credits, seq_variant="ref"):
    return {
        "Cinematics": [
            {"id": "Intro", "sequence": seq_value("LS_LB_Intro", seq_variant), "trigger": "NewGame",
             "blockingTag": tag("State.Event.Arrival"), "initialLock": "Full", "bStartBlack": True, "bSkippableAtStart": True,
             "failSafeMarkers": ["!tag:State.Event.Arrival"]},
            {"id": "Finale", "sequence": seq_value("LS_LB_Finale", seq_variant), "trigger": "TagAdded", "triggerTag": tag("State.Event.Finale"),
             "initialLock": "Full", "bStartBlack": False, "bSkippableAtStart": False,
             "grantOnStart": {"gameplayTags": [tag("State.Warden.Stage.6")]}, "failSafeMarkers": ["!end"]},
        ],
        "Cards": {cid: {"text": text, "style": style, "holdSeconds": hold, "fadeSeconds": fade} for (cid, text, style, hold, fade) in CARDS},
        "Credits": credits,
        "CreditsSeconds": 40.0,
        "SkipHoldSeconds": 1.0,
        "SkipPromptText": "Hold E to skip",
        "MarkSeconds": 1.5,
        "LookAssistSeconds": 1.5,
        "BellActorTag": "LB_Cine_Bell",
        "BellComponentName": "Mesh",
        "BellHeadstockTag": "LB_Cine_BellHeadstock",
        "BellRopeTag": "LB_Cine_BellRope",
        "BellSwingAxis": "Pitch",
        "BellSwingKickDegrees": 6.0,
        "BellSwingMaxDegrees": 16.0,
        "BellSwingPeriodSeconds": 2.6,
        "BellSwingDampingPerSecond": 0.25,
        "CineFadeMix": {"refPath": object_path(SMX_PATH)},
    }


# ---------------------------------------------------------------------------------------------------------------------------------
# SMX_LB_CineFade
# ---------------------------------------------------------------------------------------------------------------------------------

CLASS_PATHS = [MIX_DIR + "/SCL_LB_Ambience", MIX_DIR + "/SCL_LB_SFX", MIX_DIR + "/SCL_LB_Voice", MIX_DIR + "/SCL_LB_Music"]


def effects_state(mix, classes):
    """(ok, detail): exactly the four class effects, each at VolumeAdjuster 0.0 (and pitch 1.0)."""
    cur = list(mix.get_editor_property("sound_class_effects"))
    if len(cur) != len(classes):
        return False, "%d class effects, wanted %d" % (len(cur), len(classes))
    by_class = {}
    for adj in cur:
        cls = adj.get_editor_property("sound_class_object")
        by_class[cls.get_name() if cls else "None"] = (float(adj.get_editor_property("volume_adjuster")), float(adj.get_editor_property("pitch_adjuster")))
    problems = []
    for cls in classes:
        got = by_class.get(cls.get_name())
        if got is None:
            problems.append("%s missing" % cls.get_name())
        elif not (feq(got[0], 0.0) and feq(got[1], 1.0)):
            problems.append("%s volume %g pitch %g" % (cls.get_name(), got[0], got[1]))
    return not problems, "; ".join(problems) or str(by_class)


def build_mix():
    classes = []
    for path in CLASS_PATHS:
        asset = EAL.load_asset(path) if EAL.does_asset_exist(path) else None
        check("loads " + path, asset is not None and asset.get_class().get_name() == "SoundClass", asset)
        classes.append(asset)
    if any(c is None for c in classes):
        return None, classes
    mix = find_or_create(SMX_PATH, unreal.SoundMix, unreal.SoundMixFactory())
    if mix is None:
        return None, classes
    check("SMX_LB_CineFade is a SoundMix", mix.get_class().get_name() == "SoundMix", mix.get_class().get_name())

    ok, detail = effects_state(mix, classes)
    if not ok and APPLY:
        try:
            wanted = []
            for cls in classes:
                adj = unreal.SoundClassAdjuster()
                adj.set_editor_property("sound_class_object", cls)
                adj.set_editor_property("volume_adjuster", 0.0)
                adj.set_editor_property("pitch_adjuster", 1.0)
                adj.set_editor_property("apply_to_children", False)
                adj.set_editor_property("voice_center_channel_volume_adjuster", 1.0)
                wanted.append(adj)
            mix.set_editor_property("sound_class_effects", wanted)
            note("SoundClassEffects written through unreal.SoundClassAdjuster")
        except Exception as exc:  # fall back to the ToolsetLibrary JSON engine
            note("typed SoundClassAdjuster write failed (%r); using ToolsetLibrary JSON" % (exc,))
            effects = [{"soundClassObject": {"refPath": object_path(p)}, "volumeAdjuster": 0.0, "pitchAdjuster": 1.0,
                        "bApplyToChildren": False, "voiceCenterChannelVolumeAdjuster": 1.0} for p in CLASS_PATHS]
            check("SMX set_object_properties", bool(TL.set_object_properties(mix, json.dumps({"SoundClassEffects": effects}))))
        mark_changed(mix)
        record("SMX_LB_CineFade", "sound_class_effects", "%d effects at volume 0.0" % len(CLASS_PATHS))
        ok, detail = effects_state(mix, classes)
    check("SMX_LB_CineFade class effects", ok, detail)

    set_prop(mix, "fade_in_time", 4.0, "SMX_LB_CineFade")
    set_prop(mix, "fade_out_time", 1.0, "SMX_LB_CineFade")
    set_prop(mix, "duration", -1.0, "SMX_LB_CineFade")
    set_prop(mix, "apply_eq", False, "SMX_LB_CineFade")
    return mix, classes


def verify_mix(mix, classes):
    if mix is None:
        return
    ok, detail = effects_state(mix, classes)
    check("verify SMX effects", ok, detail)
    check("verify SMX fade_in_time == 4.0", feq(mix.get_editor_property("fade_in_time"), 4.0), mix.get_editor_property("fade_in_time"))
    check("verify SMX fade_out_time == 1.0", feq(mix.get_editor_property("fade_out_time"), 1.0), mix.get_editor_property("fade_out_time"))
    check("verify SMX duration == -1", feq(mix.get_editor_property("duration"), -1.0), mix.get_editor_property("duration"))
    check("verify SMX apply_eq == False", not bool(mix.get_editor_property("apply_eq")), mix.get_editor_property("apply_eq"))
    report["readback"]["SMX_LB_CineFade"] = {
        "effects": [(a.get_editor_property("sound_class_object").get_name(), float(a.get_editor_property("volume_adjuster")), float(a.get_editor_property("pitch_adjuster")))
                    for a in mix.get_editor_property("sound_class_effects")],
        "fade_in_time": float(mix.get_editor_property("fade_in_time")), "fade_out_time": float(mix.get_editor_property("fade_out_time")),
        "duration": float(mix.get_editor_property("duration")), "apply_eq": bool(mix.get_editor_property("apply_eq"))}


# ---------------------------------------------------------------------------------------------------------------------------------
# DA_Cinematics
# ---------------------------------------------------------------------------------------------------------------------------------

def read_back(da, names):
    return json.loads(TL.get_object_properties(da, list(names)))


def build_da(credits):
    da = None
    if EAL.does_asset_exist(DA_PATH):
        da = EAL.load_asset(DA_PATH)
        check("loads DA_Cinematics", da is not None and da.get_class().get_name() == "LBCinematicSettings", da)
    elif APPLY:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property("data_asset_class", unreal.LBCinematicSettings)
        da = ATOOLS.create_asset("DA_Cinematics", DATA, unreal.LBCinematicSettings, factory)
        check("created DA_Cinematics", da is not None)
        if da is not None:
            mark_changed(da)
            record("DA_Cinematics", "(created)", "LBCinematicSettings")
    else:
        check("exists DA_Cinematics", False, "missing")
    if da is None:
        return None, build_expected(credits)

    chosen = "ref"
    expected = build_expected(credits, chosen)
    names = list(expected.keys())
    errors = []
    subset_eq(expected, read_back(da, names), "DA_Cinematics", errors)
    if errors and APPLY:
        # Variant 1: Sequence as {"refPath": ...}. If only the Sequence fields differ afterwards, variant 2 writes them as bare path strings.
        ok = TL.set_object_properties(da, json.dumps(expected))
        check("DA_Cinematics set_object_properties", bool(ok), ok)
        mark_changed(da)
        record("DA_Cinematics", "(all groups)", "%d top-level properties" % len(expected))
        errors = []
        subset_eq(expected, read_back(da, names), "DA_Cinematics", errors)
        if errors and all(".sequence" in e.lower() for e in errors):
            note("Sequence soft paths did not read back as refPath (%s); retrying as bare path strings" % errors[:2])
            chosen = "str"
            expected = build_expected(credits, chosen)
            ok = TL.set_object_properties(da, json.dumps({"Cinematics": expected["Cinematics"]}))
            check("DA_Cinematics Cinematics (bare sequence paths)", bool(ok), ok)
            errors = []
            subset_eq(expected, read_back(da, names), "DA_Cinematics", errors)
            if errors:
                chosen = "ref"
                expected = build_expected(credits, chosen)
    for e in errors:
        check("DA_Cinematics read-back", False, e)
    return da, expected


def verify_da(da, expected, credits):
    names = list(expected.keys())
    rb = read_back(da, names)
    errors = []
    subset_eq(expected, rb, "DA_Cinematics", errors)
    for e in errors:
        check("verify DA_Cinematics JSON read-back", False, e)
    check("verify DA_Cinematics JSON read-back (every field)", not errors, errors[:3])
    report["readback"]["DA_Cinematics"] = {
        "Cinematics": rb.get("Cinematics"), "Cards": rb.get("Cards"), "CineFadeMix": rb.get("CineFadeMix"),
        "scalars": {k: rb.get(k) for k in ("CreditsSeconds", "SkipHoldSeconds", "SkipPromptText", "MarkSeconds", "LookAssistSeconds", "BellActorTag",
                                           "BellComponentName", "BellHeadstockTag", "BellRopeTag", "BellSwingAxis", "BellSwingKickDegrees",
                                           "BellSwingMaxDegrees", "BellSwingPeriodSeconds", "BellSwingDampingPerSecond")},
        "credits_first_3": (rb.get("Credits") or [])[:3]}

    # The rows the plan leaves empty are empty
    rows = rb.get("Cinematics") or []
    if len(rows) == 2:
        for row, label in ((rows[0], "Intro"), (rows[1], "Finale")):
            lower = {k.lower(): v for k, v in row.items()}
            if label == "Intro":
                check("Intro triggerTag empty", text_of(lower.get("triggertag")) in ("", "None"), lower.get("triggertag"))
                grant = lower.get("grantonstart")
                tags = (grant or {}).get("gameplayTags", []) if isinstance(grant, dict) else []
                check("Intro grantOnStart empty", not tags, grant)
            else:
                check("Finale blockingTag empty", text_of(lower.get("blockingtag")) in ("", "None"), lower.get("blockingtag"))

    # Typed second reader (Python property names) for counts and plain numbers
    n_cin, n_cards, n_cred = len(rb.get("Cinematics") or []), len(rb.get("Cards") or {}), len(rb.get("Credits") or [])
    check("DA_Cinematics.Cinematics count == 2", n_cin == 2, n_cin)
    check("DA_Cinematics.Cards count == 7", n_cards == 7, n_cards)
    check("DA_Cinematics.Credits count == %d" % len(credits), n_cred == len(credits), n_cred)
    report["counts"] = {"cinematics": n_cin, "cards": n_cards, "credits": n_cred}
    try:  # the typed reader agrees (a failure of the reader itself is only noted: the JSON read-back above is the proof)
        t_cin, t_cards, t_cred = len(da.get_editor_property("cinematics")), len(da.get_editor_property("cards")), len(da.get_editor_property("credits"))
        check("typed counts (cinematics, cards, credits) agree", (t_cin, t_cards, t_cred) == (2, 7, len(credits)), (t_cin, t_cards, t_cred))
    except Exception as exc:
        note("typed count read failed (%r); the JSON counts above stand" % (exc,))
    for prop, _json_name, value in SCALARS:
        check("DA_Cinematics.%s == %g" % (prop, value), feq(da.get_editor_property(prop), value), da.get_editor_property(prop))
    check("DA_Cinematics.skip_prompt_text", str(da.get_editor_property("skip_prompt_text")) == "Hold E to skip", da.get_editor_property("skip_prompt_text"))
    for prop, value in (("bell_actor_tag", "LB_Cine_Bell"), ("bell_component_name", "Mesh"), ("bell_headstock_tag", "LB_Cine_BellHeadstock"),
                        ("bell_rope_tag", "LB_Cine_BellRope")):
        check("DA_Cinematics.%s == %s" % (prop, value), str(da.get_editor_property(prop)) == value, da.get_editor_property(prop))
    axis = str(da.get_editor_property("bell_swing_axis"))
    check("DA_Cinematics.bell_swing_axis is Pitch", "PITCH" in axis.upper() and "ROLL" not in axis.upper(), axis)
    report["readback"]["typed_cine_fade_mix"] = str(da.get_editor_property("cine_fade_mix"))  # informational; the JSON read-back above checks the path
    # The soft mix path resolves to the asset
    check("SMX_LB_CineFade exists", EAL.does_asset_exist(SMX_PATH))
    # Cards: the six texts of plan 3.1 / 3.3, by id (read as JSON; the keys lose the first capital)
    cards_json = {k.lower(): v for k, v in (rb.get("Cards") or {}).items()}
    for cid, text, style, hold, fade in CARDS:
        row = {k.lower(): v for k, v in (cards_json.get(cid.lower()) or {}).items()}
        check("card %s text" % cid, text_of(row.get("text")) == text, row.get("text"))
        check("card %s style" % cid, norm_enum(row.get("style")) == style.lower(), row.get("style"))
        check("card %s hold" % cid, feq(row.get("holdseconds", -1), hold), row.get("holdseconds"))
        check("card %s fade" % cid, feq(row.get("fadeseconds", -1), fade), row.get("fadeseconds"))
    # Credits: first and last line, and the order of every line
    rb_credits = rb.get("Credits") or []
    for i, (want, got) in enumerate(zip(credits, rb_credits)):
        g = {k.lower(): v for k, v in got.items()}
        text_wrong = want["style"] != "Gap" and text_of(g.get("text")) != want["text"]
        if norm_enum(g.get("style")) != want["style"].lower() or text_wrong:
            check("credits[%d]" % i, False, "wanted %r read %r" % (want, got))
            break
    else:
        check("credits all %d lines in order" % len(credits), len(rb_credits) == len(credits), len(rb_credits))


# ---------------------------------------------------------------------------------------------------------------------------------
# Save and main
# ---------------------------------------------------------------------------------------------------------------------------------

def save_changed():
    for package in sorted(changed_packages):
        if not allowed(package):
            check("save guard " + package, False, "outside the allowed packages")
            continue
        ok = EAL.save_asset(package, False)
        check("saved " + package, bool(ok))
        if ok:
            report["saved"].append(package)
    changed_packages.clear()
    dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    ours = [d for d in dirty if allowed(d)]
    check("no dirty package of ours after the save", not ours, ours)
    others = [d for d in dirty if not allowed(d)]
    if others:
        note("dirty packages outside our two (not saved): %s" % others[:10])


def write_report():
    report["ok"] = not report["failures"]
    report["failure_count"] = len(report["failures"])
    if OUT:
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1)
    unreal.log("P17-2 RESULT: %s (%d checks, %d failures) mode=%s" % ("PASS" if report["ok"] else "FAIL", report["checks"], len(report["failures"]), MODE))


def main():
    credits = load_credits()
    note("mode=%s; %d credit lines, %d cards" % (MODE, len(credits), len(CARDS)))
    if report["failures"]:
        return
    mix, classes = build_mix()
    if report["failures"]:
        return
    da, expected = build_da(credits)
    if APPLY:
        save_changed()
    verify_mix(mix, classes)
    if da is not None:
        verify_da(da, expected, credits)


try:
    main()
except Exception as exc:  # report, never half-save silently
    report["failures"].append("exception: %r" % (exc,))
    report["traceback"] = traceback.format_exc()
    unreal.log_error("P17-2 EXCEPTION: " + report["traceback"])
finally:
    write_report()

if report["failures"]:
    raise RuntimeError("P17-2: %d failed checks; see the report" % len(report["failures"]))
