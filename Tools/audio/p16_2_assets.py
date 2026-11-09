"""P16-2: create every Phase 16 audio asset headless (Unreal CLOSED).

Run (editor closed):
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>
Environment variables:
    LB_OUT       path of the JSON report
    LB_MODE      "apply" (default): import, create, set, save, then verify in the same process
                 "verify": read-only, nothing is created, set or saved; run it in a FRESH process to prove what is on disk
    LB_REIMPORT  "1" re-imports every WAV even when the SoundWave already exists (default: import only the missing ones);
                 any other value except "0" is a REGEX on the sound name: re-import only the matching sounds
                 (P16-5: LB_REIMPORT="^SFX_LB_Thunder_(Near|Strike)_" re-imports the recorded-crack thunder only)

What it does (docs/plans/P16_AUDIO.md, "P16-2 brief"):
 1. imports the 175 WAVs of SourceArt/Audio/Generated and Recorded into /Game/LastBell/Audio/<Folder>/
 2. sets looping, sound class, attenuation, concurrency and volume per SoundWave (cue sheet, section 3)
 3. creates the SoundClasses, SMX_LB_User, 8 attenuation, 4 concurrency and 6 reverb assets (sections 6.1 to 6.4)
 4. creates the 6 PM_LB_* physical materials (SurfaceType1..6)
 5. creates and fills /Game/LastBell/Data/DA_Audio (class LBAudioSettings)
 6. rebuilds the rows of /Game/LastBell/Data/DT_Footsteps
 7. applies the OWNER_CHOICES (below: the P16-4 listening-session values), saves every changed package explicitly, then verifies everything

Idempotent: assets are found or created, a value is written only when it differs, and only changed packages are saved. It touches only
/Game/LastBell/Audio/**, /Game/LastBell/Physics/**, /Game/LastBell/Data/DA_Audio and /Game/LastBell/Data/DT_Footsteps (the guard is
`allowed()`); it loads Blueprint classes to check the class paths but never saves them.

The process exit code of UnrealEditor-Cmd is NOT reliable (a harmless ensure makes it 1); read the report (`ok`) or the log line
"P16-2 RESULT". On any failed check the script ends with an uncaught RuntimeError.
"""
import json
import math
import os
import re
import traceback
import wave as wave_module

import unreal

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
GEN_DIR = os.path.join(ROOT, "SourceArt", "Audio", "Generated")
REC_DIR = os.path.join(ROOT, "SourceArt", "Audio", "Recorded")
OUT = os.environ.get("LB_OUT", "")
MODE = os.environ.get("LB_MODE", "apply").lower()
_REIMPORT_ENV = os.environ.get("LB_REIMPORT", "0")
REIMPORT = _REIMPORT_ENV == "1"
REIMPORT_RE = re.compile(_REIMPORT_ENV) if _REIMPORT_ENV not in ("0", "1", "") else None
APPLY = MODE == "apply"

AUD = "/Game/LastBell/Audio"
MIX = AUD + "/Mix"
PHYS = "/Game/LastBell/Physics"
DATA = "/Game/LastBell/Data"
DA_PATH = DATA + "/DA_Audio"
DT_PATH = DATA + "/DT_Footsteps"
BP_DIR = "/Game/LastBell/Blueprints"

ALLOWED = (AUD + "/", PHYS + "/", DA_PATH, DT_PATH)

EAL = unreal.EditorAssetLibrary
TL = unreal.ToolsetLibrary
ATOOLS = unreal.AssetToolsHelpers.get_asset_tools()

report = {"mode": MODE, "ok": False, "checks": 0, "failures": [], "counts": {}, "saved": [], "notes": [], "set_log": [], "properties": {}}


def check(name, ok, detail=""):
    report["checks"] += 1
    if not ok:
        msg = "%s: %s" % (name, detail)
        report["failures"].append(msg)
        unreal.log_error("P16-2 CHECK FAILED: " + msg)
    return bool(ok)


def note(text):
    report["notes"].append(text)
    unreal.log("P16-2: " + text)


def allowed(path):
    """A package under /Game/LastBell/Audio/ or /Game/LastBell/Physics/, or exactly DA_Audio / DT_Footsteps."""
    return any(path.startswith(a) if a.endswith("/") else path == a for a in ALLOWED)


# ---------------------------------------------------------------------------------------------------------------------------------
# Cue sheet (plan section 3)
# ---------------------------------------------------------------------------------------------------------------------------------

FOLDERS = [  # (regex on the asset name, folder under /Game/LastBell/Audio)
    (r"^SFX_LB_(Rain_|Wind)", "Weather"),
    (r"^SFX_LB_Thunder_", "Thunder"),
    (r"^SFX_LB_(Bell_|SmallBell_)", "Bell"),
    (r"^MUS_LB_", "Music"),
    (r"^SFX_LB_(Room_|Drip_|Creak_|Chain_Distant_)", "Room"),
    (r"^SFX_LB_(Step_|Breath_|Candle_|Key_|Paper_)", "Player"),
    (r"^SFX_LB_(Door_|Lever_|Winch_|Stone_|Generic_)", "Interact"),
    (r"^SFX_LB_(Warden_|Apparition_)", "Warden"),
]

# (regex, sound class key, attenuation asset or None); the first match wins. 2D cues (section 3 "2D") have no attenuation.
SOUND_RULES = [
    (r"^SFX_LB_(Rain_|Wind)", "Ambience", None),
    (r"^SFX_LB_Thunder_", "Ambience", "ATT_LB_Thunder"),
    (r"^SFX_LB_Bell_Stage", "Ambience", "ATT_LB_Bell"),
    (r"^SFX_LB_SmallBell_Solved", "SFX", "ATT_LB_Medium"),
    (r"^SFX_LB_SmallBell_", "SFX", "ATT_LB_Small"),
    (r"^MUS_LB_", "Music", None),
    (r"^SFX_LB_Room_", "Ambience", None),
    (r"^SFX_LB_Drip_", "Ambience", "ATT_LB_Small"),
    (r"^SFX_LB_Creak_", "Ambience", "ATT_LB_Medium"),
    (r"^SFX_LB_Chain_Distant_", "Ambience", "ATT_LB_Large"),
    (r"^SFX_LB_Step_", "SFX", "ATT_LB_Step"),
    (r"^SFX_LB_(Breath_|Candle_|Key_|Paper_)", "SFX", None),
    (r"^SFX_LB_Door_", "SFX", "ATT_LB_Medium"),
    (r"^SFX_LB_Lever_", "SFX", "ATT_LB_Small"),
    (r"^SFX_LB_(Winch_|Stone_Grind_)", "SFX", "ATT_LB_Medium"),
    (r"^SFX_LB_Generic_Use_", "SFX", "ATT_LB_Small"),
    (r"^SFX_LB_Warden_(Spotted|Roar|Windup|Exhale|Caught)_", "Voice", "ATT_LB_WardenTell"),
    (r"^SFX_LB_(Warden_|Apparition_)", "Voice", "ATT_LB_Warden"),
]

CONCURRENCY_RULES = [
    (r"^SFX_LB_(Step_|Warden_Step_)", "CON_LB_Steps"),
    (r"^SFX_LB_Thunder_", "CON_LB_Thunder"),
    (r"^SFX_LB_Drip_", "CON_LB_Drips"),
    (r"^SFX_LB_Warden_(Spotted|Roar|Windup|Caught)_", "CON_LB_Tells"),
]

RECORDED_LOOPS = {"SFX_LB_Warden_Breath_Slow", "SFX_LB_Warden_Breath_Fast", "SFX_LB_Warden_Breath_Heavy", "SFX_LB_Warden_Robe"}


def rule_for(rules, name):
    for rule in rules:
        if re.search(rule[0], name):
            return rule
    return None


def folder_for(name):
    rule = rule_for(FOLDERS, name)
    return AUD + "/" + rule[1] if rule else None


def sound_package(name):
    return "%s/%s" % (folder_for(name), name)


def object_path(package_path):
    return "%s.%s" % (package_path, package_path.rsplit("/", 1)[1])


# ---------------------------------------------------------------------------------------------------------------------------------
# Mix assets (plan sections 6.1 to 6.4)
# ---------------------------------------------------------------------------------------------------------------------------------

CLASS_NAMES = {"Master": "SCL_LB_Master", "SFX": "SCL_LB_SFX", "Ambience": "SCL_LB_Ambience", "Music": "SCL_LB_Music", "Voice": "SCL_LB_Voice", "UI": "SCL_LB_UI"}

# inner = the near distance (sphere inner radius); fall = the falloff distance; natural = Natural Sound distance model;
# omni = non-spatialized radius; absorb = (start cm, end cm, low-pass Hz at the end); occl = (volume, low-pass Hz or None, interpolation s or None)
ATTENUATION = {
    "ATT_LB_Step": dict(inner=200.0, fall=1500.0),
    "ATT_LB_Small": dict(inner=200.0, fall=1500.0),
    "ATT_LB_Medium": dict(inner=400.0, fall=3000.0, absorb=(1000.0, 4000.0, 3000.0)),
    "ATT_LB_Large": dict(inner=800.0, fall=6000.0),
    "ATT_LB_Warden": dict(inner=300.0, fall=3500.0, natural=True, occl=(0.4, 1200.0, 0.3)),
    "ATT_LB_WardenTell": dict(inner=500.0, fall=5000.0, occl=(0.6, None, None)),
    "ATT_LB_Thunder": dict(inner=20000.0, fall=60000.0, omni=3000.0),
    "ATT_LB_Bell": dict(inner=10000.0, fall=120000.0, omni=2000.0),
}

CONCURRENCY = {  # name: (max count, MaxConcurrentResolutionRule member)
    "CON_LB_Steps": (4, "STOP_OLDEST"),
    "CON_LB_Thunder": (2, "STOP_QUIETEST"),
    "CON_LB_Drips": (6, "STOP_FARTHEST_THEN_OLDEST"),
    "CON_LB_Tells": (1, "STOP_OLDEST"),
}

REVERB = {  # name: (decay s, density, diffusion, gain, gainHF)
    "RVB_LB_Chapel": (3.2, 1.0, 0.9, 0.32, 0.6),
    "RVB_LB_Crypt": (2.4, 1.0, 1.0, 0.35, 0.4),
    "RVB_LB_Cloister": (1.6, 0.8, 0.8, 0.25, 0.7),
    "RVB_LB_Passage": (1.2, 0.9, 0.9, 0.28, 0.6),
    "RVB_LB_Tower": (2.8, 0.9, 0.8, 0.30, 0.5),
    "RVB_LB_Belfry": (1.5, 0.7, 0.7, 0.22, 0.7),
}
REVERB_LATE_DELAY = 0.04
REVERB_REFLECTIONS_DELAY = 0.01

PHYS_MATS = {"PM_LB_Stone": 1, "PM_LB_Wood": 2, "PM_LB_Earth": 3, "PM_LB_Grass": 4, "PM_LB_Water": 5, "PM_LB_Metal": 6}

# ---------------------------------------------------------------------------------------------------------------------------------
# OWNER_CHOICES: the owner's values from the P16-4 listening sessions (plan "P16-4: listening session, part 1 / part 2"). They WIN over the
# cue-sheet values (the manifest mix_gain_db), so a fresh run of this script reproduces what the owner approved by ear. Edit only after
# another listening session, and record it in docs/plans/P16_AUDIO.md.
# ---------------------------------------------------------------------------------------------------------------------------------
OWNER_CHOICES = {
    # SoundWave Volume by name regex (first match wins; sounds that match nothing keep the cue-sheet volume = 10^(mix_gain_db / 20))
    "wave_volume": [
        (r"^SFX_LB_Bell_Stage[1-4]$", 1.0),    # was 0.126 / 0.200 / 0.316 / 0.501: stage 1 was inaudible; the files' own filtering carries the distance
        (r"^SFX_LB_Thunder_Far_", 1.0),        # was 0.398 (-8 dB): "fine now" at full volume
        (r"^SFX_LB_Step_", 0.6),               # the 36 player footsteps were too loud at 1.0
        (r"^SFX_LB_Warden_Roar_", 2.0),        # was inaudible under the chase music
    ],
    # SoundClass Properties.volume by class key (CLASS_NAMES): the overall loudness
    "class_volume": {"Master": 0.7},
    # DA_Audio (LBAudioSettings) editor properties; the script writes only these, the other fields are left as they are on disk
    "da_audio": {"rain_out_gain": 0.22, "rain_in_gain": 0.03, "rain_exposure_power": 1.5, "wind_out_gain": 0.08, "wind_min": 0.2},
}

# ---------------------------------------------------------------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------------------------------------------------------------

changed_packages = set()


def mark_changed(obj):
    changed_packages.add(obj.get_outermost().get_name())


def feq(a, b, tol=1e-4):
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


def same(a, b):
    """Loose equality for editor-property values."""
    try:
        if isinstance(b, bool) or isinstance(a, bool):
            return bool(a) == bool(b)
        if isinstance(b, (int, float)):
            return feq(a, b)
        if isinstance(b, unreal.Vector):
            return feq(a.x, b.x) and feq(a.y, b.y) and feq(a.z, b.z)
        if isinstance(b, unreal.Object) or isinstance(a, unreal.Object):
            return a == b
        return str(a) == str(b)
    except Exception:
        return False


def record(owner, prop, value):
    report["set_log"].append("%s.%s = %s" % (owner, prop, value if not isinstance(value, unreal.Object) else value.get_name()))


def set_prop(obj, prop, value, owner=None):
    """set_editor_property only when the value differs; the read-back must match."""
    owner = owner or obj.get_name()
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


def find_or_create(path, asset_class, factory_cls):
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
    asset = ATOOLS.create_asset(name, folder, asset_class, factory_cls() if factory_cls else None)
    check("created " + path, asset is not None)
    if asset is not None:
        mark_changed(asset)
        record(name, "(created)", asset.get_class().get_name())
    return asset


def fmt(value):
    """A report-friendly string (no object addresses)."""
    if isinstance(value, unreal.Vector):
        return "(%g, %g, %g)" % (value.x, value.y, value.z)
    if isinstance(value, float):
        return "%g" % round(value, 6)
    return str(value).split(".")[-1].split(":")[0].rstrip(">") if str(value).startswith("<") else str(value)


def set_from(obj_set):
    return list(obj_set) if obj_set is not None else []


# ---------------------------------------------------------------------------------------------------------------------------------
# 3. Mix assets
# ---------------------------------------------------------------------------------------------------------------------------------

def build_sound_classes():
    assets = {}
    for key, name in CLASS_NAMES.items():
        assets[key] = find_or_create(MIX + "/" + name, unreal.SoundClass, unreal.SoundClassFactory)
    master = assets["Master"]
    if master is None or any(v is None for v in assets.values()):
        return assets
    for key in ("SFX", "Ambience", "Music", "Voice", "UI"):
        child = assets[key]
        set_prop(child, "parent_class", master)
    # The parent's child list must hold every child (the editor graph keeps it in step; check, and add what is missing).
    kids = list(master.get_editor_property("child_classes"))
    missing = [assets[k] for k in ("SFX", "Ambience", "Music", "Voice", "UI") if assets[k] not in kids]
    if missing:
        if APPLY:
            master.set_editor_property("child_classes", kids + missing)
            mark_changed(master)
            record("SCL_LB_Master", "child_classes", "+%d" % len(missing))
        else:
            check("SCL_LB_Master.child_classes", False, "missing %s" % [m.get_name() for m in missing])
    # Volume 1 everywhere except the owner's choices (SCL_LB_Master 0.7). The write goes through the Properties struct and the package is marked
    # changed by hand: an MCP write to a SoundClass's Properties does not dirty the package, but save_asset(only_if_dirty=False) saves it.
    for key, asset in assets.items():
        wanted = OWNER_CHOICES["class_volume"].get(key, 1.0)
        props = asset.get_editor_property("properties")
        if not feq(props.get_editor_property("volume"), wanted) and APPLY:
            props.set_editor_property("volume", wanted)
            asset.set_editor_property("properties", props)
            mark_changed(asset)
            record(asset.get_name(), "properties.volume", wanted)
            props = asset.get_editor_property("properties")
        check("%s volume %g" % (asset.get_name(), wanted), feq(props.get_editor_property("volume"), wanted), props.get_editor_property("volume"))
    return assets


def attenuation_wanted(spec):
    """FSoundAttenuationSettings fields (python names) the spec asks for."""
    w = {
        "attenuate": True,
        "spatialize": True,
        "attenuation_shape": unreal.AttenuationShape.SPHERE,
        "falloff_distance": spec["fall"],
        "attenuation_shape_extents": unreal.Vector(spec["inner"], 0.0, 0.0),
    }
    if spec.get("natural"):
        w["distance_algorithm"] = unreal.AttenuationDistanceModel.NATURAL_SOUND
    if spec.get("omni") is not None:
        w["non_spatialized_radius_start"] = spec["omni"]
    if spec.get("absorb"):
        start, end, hz = spec["absorb"]
        w["attenuate_with_lpf"] = True
        w["lpf_radius_min"] = start
        w["lpf_radius_max"] = end
        w["lpf_frequency_at_max"] = hz
    if spec.get("occl"):
        volume, lpf, interp = spec["occl"]
        w["enable_occlusion"] = True
        w["occlusion_trace_channel"] = unreal.CollisionChannel.ECC_VISIBILITY
        w["occlusion_volume_attenuation"] = volume
        if lpf is not None:
            w["occlusion_low_pass_filter_frequency"] = lpf
        if interp is not None:
            w["occlusion_interpolation_time"] = interp
    return w


def build_attenuation():
    out = {}
    for name, spec in ATTENUATION.items():
        asset = find_or_create(MIX + "/" + name, unreal.SoundAttenuation, unreal.SoundAttenuationFactory)
        out[name] = asset
        if asset is None:
            continue
        settings = asset.get_editor_property("attenuation")
        dirty = False
        for prop, value in attenuation_wanted(spec).items():
            cur = settings.get_editor_property(prop)
            if same(cur, value):
                continue
            if not APPLY:
                check("%s.%s" % (name, prop), False, "wanted %r read %r" % (value, cur))
                continue
            settings.set_editor_property(prop, value)
            dirty = True
            record(name, prop, value)
        if dirty:
            asset.set_editor_property("attenuation", settings)
            mark_changed(asset)
            settings = asset.get_editor_property("attenuation")
            for prop, value in attenuation_wanted(spec).items():
                check("set %s.%s" % (name, prop), same(settings.get_editor_property(prop), value), "wanted %r read %r" % (value, settings.get_editor_property(prop)))
    return out


def build_concurrency():
    out = {}
    for name, (count, rule) in CONCURRENCY.items():
        asset = find_or_create(MIX + "/" + name, unreal.SoundConcurrency, unreal.SoundConcurrencyFactory)
        out[name] = asset
        if asset is None:
            continue
        cfg = asset.get_editor_property("concurrency")
        wanted = {"max_count": count, "resolution_rule": getattr(unreal.MaxConcurrentResolutionRule, rule)}
        dirty = False
        for prop, value in wanted.items():
            cur = cfg.get_editor_property(prop)
            if same(cur, value):
                continue
            if not APPLY:
                check("%s.%s" % (name, prop), False, "wanted %r read %r" % (value, cur))
                continue
            cfg.set_editor_property(prop, value)
            dirty = True
            record(name, prop, value)
        if dirty:
            asset.set_editor_property("concurrency", cfg)
            mark_changed(asset)
            cfg = asset.get_editor_property("concurrency")
            for prop, value in wanted.items():
                check("set %s.%s" % (name, prop), same(cfg.get_editor_property(prop), value), "wanted %r read %r" % (value, cfg.get_editor_property(prop)))
    return out


def build_reverb():
    out = {}
    for name, (decay, density, diffusion, gain, gainhf) in REVERB.items():
        asset = find_or_create(MIX + "/" + name, unreal.ReverbEffect, unreal.ReverbEffectFactory)
        out[name] = asset
        if asset is None:
            continue
        for prop, value in (("decay_time", decay), ("density", density), ("diffusion", diffusion), ("gain", gain), ("gain_hf", gainhf),
                            ("late_delay", REVERB_LATE_DELAY), ("reflections_delay", REVERB_REFLECTIONS_DELAY)):
            set_prop(asset, prop, value, name)
    return out


def build_mix_asset():
    return find_or_create(MIX + "/SMX_LB_User", unreal.SoundMix, unreal.SoundMixFactory)


def build_phys():
    out = {}
    for name, surface in PHYS_MATS.items():
        asset = find_or_create(PHYS + "/" + name, unreal.PhysicalMaterial, unreal.PhysicalMaterialFactoryNew)
        out[name] = asset
        if asset is not None:
            set_prop(asset, "surface_type", getattr(unreal.PhysicalSurface, "SURFACE_TYPE%d" % surface), name)
    return out


# ---------------------------------------------------------------------------------------------------------------------------------
# 1 and 2. WAV import and per-SoundWave properties
# ---------------------------------------------------------------------------------------------------------------------------------

def collect_wavs():
    """Every WAV with its source (generated or recorded), loop flag and mix gain."""
    items = {}
    gen = json.load(open(os.path.join(GEN_DIR, "manifest.json"), encoding="utf-8"))
    for fname in sorted(os.listdir(GEN_DIR)):
        if not fname.lower().endswith(".wav"):
            continue
        name = fname[:-4]
        entry = gen.get(name, {})
        items[name] = dict(path=os.path.join(GEN_DIR, fname), source="generated", loop=bool(entry.get("loop")), gain_db=float(entry.get("mix_gain_db") or 0.0))
    for fname in sorted(os.listdir(REC_DIR)):
        if not fname.lower().endswith(".wav"):
            continue
        name = fname[:-4]
        check("unique name " + name, name not in items)
        items[name] = dict(path=os.path.join(REC_DIR, fname), source="recorded", loop=name in RECORDED_LOOPS, gain_db=0.0)
    return items


def import_sounds(items):
    tasks = []
    for name, info in items.items():
        package = sound_package(name)
        if EAL.does_asset_exist(package) and not REIMPORT and not (REIMPORT_RE and REIMPORT_RE.search(name)):
            continue
        task = unreal.AssetImportTask()
        task.filename = info["path"]
        task.destination_path = folder_for(name)
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.replace_existing_settings = True
        task.save = False
        tasks.append(task)
    note("importing %d of %d WAVs" % (len(tasks), len(items)))
    if tasks:
        ATOOLS.import_asset_tasks(tasks)
        for task in tasks:
            paths = list(task.imported_object_paths)
            check("imported " + task.destination_name, len(paths) == 1, paths)
            asset = EAL.load_asset(sound_package(task.destination_name))
            if asset is not None:
                mark_changed(asset)
    return len(tasks)


def sound_targets(name, info):
    """(class key, attenuation name or None, concurrency name or None, looping, volume) for a sound."""
    cls_rule = rule_for(SOUND_RULES, name)
    con_rule = rule_for(CONCURRENCY_RULES, name)
    volume = 10.0 ** (info["gain_db"] / 20.0) if info["gain_db"] else 1.0
    for pattern, owner_volume in OWNER_CHOICES["wave_volume"]:
        if re.search(pattern, name):
            volume = owner_volume
            break
    return cls_rule[1], cls_rule[2], (con_rule[1] if con_rule else None), info["loop"], volume


def wav_seconds(path):
    with wave_module.open(path, "rb") as w:
        return w.getnframes() / float(w.getframerate())


def wave_concurrency(wave):
    return set_from(wave.get_editor_property("concurrency_set"))


def apply_wave_properties(items, classes, attenuation, concurrency):
    for name, info in items.items():
        wave = EAL.load_asset(sound_package(name))
        if not check("loads sound " + name, wave is not None and wave.get_class().get_name() == "SoundWave", wave):
            continue
        cls_key, att_name, con_name, loop, volume = sound_targets(name, info)
        set_prop(wave, "looping", loop, name)
        set_prop(wave, "sound_class_object", classes[cls_key], name)
        set_prop(wave, "attenuation_settings", attenuation[att_name] if att_name else None, name)
        set_prop(wave, "volume", volume, name)
        want = concurrency[con_name] if con_name else None
        have = wave_concurrency(wave)
        if (have == [want] if want else have == []):
            continue
        if not APPLY:
            check("%s.concurrency_set" % name, False, "wanted %s read %s" % (con_name, [h.get_name() for h in have]))
            continue
        new_set = unreal.Set(unreal.SoundConcurrency)
        if want:
            new_set.add(want)
        wave.set_editor_property("concurrency_set", new_set)
        mark_changed(wave)
        record(name, "concurrency_set", con_name)
        have = wave_concurrency(wave)
        check("set %s.concurrency_set" % name, (have == [want]) if want else have == [], [h.get_name() for h in have])


# ---------------------------------------------------------------------------------------------------------------------------------
# 5. DA_Audio (class LBAudioSettings), written through ToolsetLibrary.set_object_properties (the ObjectTools.set_properties engine)
# ---------------------------------------------------------------------------------------------------------------------------------

def ref(name):
    return {"refPath": object_path(sound_package(name))}


def seq(prefix, count, pad=2):
    return ["%s_%0*d" % (prefix, pad, i) for i in range(1, count + 1)]


def refs(names):
    return [ref(n) for n in names]


def bp_class(rel):
    """Soft class path of a Blueprint under /Game/LastBell/Blueprints (the generated _C class)."""
    base = rel.rsplit("/", 1)[1]
    return {"refPath": "%s/%s.%s_C" % (BP_DIR + "/" + rel.rsplit("/", 1)[0], base, base)}


def build_da_json():
    walls = seq("SFX_LB_Door_Wood_Open", 3)
    locked = seq("SFX_LB_Door_Locked", 3)
    generic = seq("SFX_LB_Generic_Use", 3)
    cues = [
        dict(cls="Interactables/BP_Door_Base", sub=True, interact=walls, denied=locked, dial=[], vol=1.0, pitch=(0.97, 1.03), note="Doors: wood cues; Denied on the chapel door"),
        dict(cls="Puzzles/BP_DialLever", sub=True, interact=[], denied=generic, dial=seq("SFX_LB_Lever_Notch", 4), vol=1.0, pitch=(0.97, 1.03), note="Crypt counterweight levers: a notch per position"),
        dict(cls="Puzzles/BP_PuzzleCandle", sub=True, interact=seq("SFX_LB_Candle_Light", 3), denied=[], dial=[], vol=0.9, pitch=(0.97, 1.03), note="Chapel puzzle candles"),
        dict(cls="Interactables/BP_Inspectable_Note", sub=True, interact=seq("SFX_LB_Paper", 3), denied=[], dial=[], vol=0.8, pitch=(0.95, 1.05), note="Notes: paper rustle"),
        dict(cls="Interactables/BP_RitualMechanism_ChapelBells", sub=True, interact=seq("SFX_LB_Stone_Grind", 3), denied=generic, dial=[], vol=1.0, pitch=(0.97, 1.03), note="Altar mechanism"),
        dict(cls="Interactables/BP_RitualMechanism_CryptWinch", sub=True, interact=seq("SFX_LB_Winch", 3), denied=generic, dial=[], vol=1.0, pitch=(0.97, 1.03), note="Crypt winch"),
        dict(cls="Interactables/BP_RitualMechanism_TowerCapstan", sub=True, interact=seq("SFX_LB_Winch", 3), denied=generic, dial=[], vol=1.0, pitch=(0.9, 1.0), note="Tower capstan: the winch, lower"),
        dict(cls="Interactables/BP_TagInteractable_ChapelKey", sub=True, interact=seq("SFX_LB_Key_Pickup", 2), denied=[], dial=[], vol=1.0, pitch=(0.97, 1.03), note="Chapel key"),
        dict(cls="Interactables/BP_TagInteractable_CryptCrank", sub=True, interact=seq("SFX_LB_Key_Pickup", 2), denied=[], dial=[], vol=1.0, pitch=(0.85, 0.95), note="Crank pickup: key pickup, lower"),
    ]
    silent = ["Interactables/BP_TagInteractable_GreatBell", "Puzzles/BP_SequencePuzzle", "Puzzles/BP_SmallBell_Cloister"]
    beats = [  # FLBAudioSettings::FillPlanDefaults, plan 5.3: tag, stage, strikes, first delay, spacing, drone (0 A, 1 B, 2 C)
        ("State.Ritual.1", 2, 3, 2.0, 4.5, 1),
        ("State.Event.CryptEntered", 1, 0, 0.0, 0.0, 0),
        ("State.Ritual.2", 3, 3, 2.0, 4.5, 2),
        ("State.Ritual.3", 4, 3, 2.0, 4.0, 1),
        ("State.Event.TowerTop", 4, 4, 1.0, 3.5, 2),
        ("State.Event.Finale", 5, 5, 0.0, 5.0, -1),
    ]
    tag_key = lambda t: '(TagName="%s")' % t
    return {
        "Weather": {"rainOut": ref("SFX_LB_Rain_Out"), "rainIn": ref("SFX_LB_Rain_In"), "wind": ref("SFX_LB_Wind"), "windHowl": ref("SFX_LB_Wind_Howl")},
        "Thunder": {
            "near": refs(seq("SFX_LB_Thunder_Near", 4)),
            "mid": refs(seq("SFX_LB_Thunder_Mid", 4)),
            "far": refs(seq("SFX_LB_Thunder_Far", 4)),
            "strikeCrack": refs(seq("SFX_LB_Thunder_Strike", 3)),
        },
        "Bell": {"stage": refs(["SFX_LB_Bell_Stage%d" % i for i in range(1, 6)])},
        "Music": {
            "drones": refs(["MUS_LB_Drone_A", "MUS_LB_Drone_B", "MUS_LB_Drone_C"]),
            "tension": ref("MUS_LB_Tension"),
            "chase": ref("MUS_LB_Chase"),
            "stingSpotted": ref("MUS_LB_Sting_Spotted"),
            "stingCaught": ref("MUS_LB_Sting_Caught"),
            "stingApparition": ref("MUS_LB_Sting_Apparition"),
        },
        "Player": {
            "breathCalm": refs(seq("SFX_LB_Breath_Calm", 4)),
            "breathHeavy": refs(seq("SFX_LB_Breath_Heavy", 4)),
            "breathPanic": refs(seq("SFX_LB_Breath_Panic", 4)),
            "breathGasp": refs(seq("SFX_LB_Breath_Gasp", 3)),
            "candleLight": refs(seq("SFX_LB_Candle_Light", 3)),
            "candleOut": refs(seq("SFX_LB_Candle_Out", 3)),
            "candleRelight": ref("SFX_LB_Candle_Relight"),
        },
        "Warden": {
            "breathSlow": ref("SFX_LB_Warden_Breath_Slow"),
            "breathFast": ref("SFX_LB_Warden_Breath_Fast"),
            "breathHeavy": ref("SFX_LB_Warden_Breath_Heavy"),
            "steps": refs(seq("SFX_LB_Warden_Step", 5)),
            "chains": refs(seq("SFX_LB_Warden_Chain", 4)),
            "robeLoop": ref("SFX_LB_Warden_Robe"),
            "spotted": refs(seq("SFX_LB_Warden_Spotted", 3)),
            "roar": refs(seq("SFX_LB_Warden_Roar", 3)),
            "windup": refs(seq("SFX_LB_Warden_Windup", 3)),
            "exhale": refs(seq("SFX_LB_Warden_Exhale", 3)),
            "caught": refs(seq("SFX_LB_Warden_Caught", 2)),
            "apparitionWhisper": refs(seq("SFX_LB_Apparition_Whisper", 3)),
        },
        "InteractionCues": [
            {
                "actorClass": bp_class(c["cls"]),
                "bIncludeSubclasses": c["sub"],
                "interact": refs(c["interact"]),
                "denied": refs(c["denied"]),
                "dialNotch": refs(c["dial"]),
                "volume": c["vol"],
                "pitch": {"x": c["pitch"][0], "y": c["pitch"][1]},
                "note": c["note"].replace(" ", "_").replace(";", "").replace(":", ""),
            }
            for c in cues
        ],
        "SilentClasses": [bp_class(c) for c in silent],
        "SmallBellPitch": {tag_key("State.Tower.Bell.1"): 0.7692, tag_key("State.Tower.Bell.2"): 0.8696, tag_key("State.Tower.Bell.3"): 1.0, tag_key("State.Tower.Bell.4"): 1.1765},
        "SmallBellStrike": ref("SFX_LB_SmallBell_Strike"),
        "SmallBellFail": ref("SFX_LB_SmallBell_Fail"),
        "SmallBellSolved": ref("SFX_LB_SmallBell_Solved"),
        "BellLocation": {"x": 12420.1, "y": 2000.0, "z": 2750.0},
        "BellBeats": [
            {"trigger": {"tagName": t}, "stage": st, "strikes": sk, "firstDelay": fd, "spacing": sp, "drone": dr}
            for (t, st, sk, fd, sp, dr) in beats
        ],
        "UserMix": {"refPath": object_path(MIX + "/SMX_LB_User")},
        "UserClasses": {k: {"refPath": object_path(MIX + "/" + v)} for k, v in CLASS_NAMES.items()},
        "DebugForceMusicState": -1,
    }


def subset_eq(exp, act, path, errors):
    """exp must be contained in act (JSON values). Numbers by tolerance; map keys case-insensitively; refPath dicts by path."""
    if isinstance(exp, dict):
        if not isinstance(act, dict):
            if set(exp.keys()) == {"refPath"} and isinstance(act, str):
                if act != exp["refPath"]:
                    errors.append("%s: ref %r != %r" % (path, act, exp["refPath"]))
                return
            errors.append("%s: expected an object, read %r" % (path, str(act)[:80]))
            return
        lower = {k.lower(): v for k, v in act.items()}
        for key, value in exp.items():
            if key.lower() not in lower:
                errors.append("%s.%s: missing in read-back" % (path, key))
                continue
            subset_eq(value, lower[key.lower()], "%s.%s" % (path, key), errors)
    elif isinstance(exp, list):
        if not isinstance(act, list) or len(act) != len(exp):
            errors.append("%s: expected %d items, read %s" % (path, len(exp), len(act) if isinstance(act, list) else repr(act)[:60]))
            return
        for i, (e, a) in enumerate(zip(exp, act)):
            subset_eq(e, a, "%s[%d]" % (path, i), errors)
    elif isinstance(exp, bool):
        if bool(act) != exp:
            errors.append("%s: %r != %r" % (path, act, exp))
    elif isinstance(exp, (int, float)):
        if not isinstance(act, (int, float)) or not feq(act, exp, 1e-5):
            errors.append("%s: %r != %r" % (path, act, exp))
    else:
        if str(act) != str(exp):
            errors.append("%s: %r != %r" % (path, act, exp))


def collect_refpaths(node, out):
    if isinstance(node, dict):
        if "refPath" in node:
            out.append(node["refPath"])
        for v in node.values():
            collect_refpaths(v, out)
    elif isinstance(node, list):
        for v in node:
            collect_refpaths(v, out)


def build_da():
    expected = build_da_json()
    da = None
    if EAL.does_asset_exist(DA_PATH):
        da = EAL.load_asset(DA_PATH)
        check("loads DA_Audio", da is not None and da.get_class().get_name() == "LBAudioSettings", da)
    elif APPLY:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property("data_asset_class", unreal.LBAudioSettings)
        da = ATOOLS.create_asset("DA_Audio", DATA, unreal.LBAudioSettings, factory)
        check("created DA_Audio", da is not None)
        if da is not None:
            mark_changed(da)
            record("DA_Audio", "(created)", "LBAudioSettings")
    else:
        check("exists DA_Audio", False, "missing")
    if da is None:
        return None, expected

    def read_back():
        return json.loads(TL.get_object_properties(da, list(expected.keys())))

    errors = []
    subset_eq(expected, read_back(), "DA_Audio", errors)
    if errors and APPLY:
        ok = TL.set_object_properties(da, json.dumps(expected))
        check("DA_Audio set_object_properties", bool(ok), ok)
        mark_changed(da)
        record("DA_Audio", "(all groups)", "%d top-level properties" % len(expected))
        errors = []
        subset_eq(expected, read_back(), "DA_Audio", errors)
    for e in errors:
        check("DA_Audio read-back", False, e)
    for prop, value in OWNER_CHOICES["da_audio"].items():  # owner's tuning; only these fields are touched
        set_prop(da, prop, value, "DA_Audio")
    return da, expected


def verify_da(da, expected):
    paths = []
    collect_refpaths(expected, paths)
    for p in sorted(set(paths)):
        if p.startswith(BP_DIR + "/") and p.endswith("_C"):
            bp = p.rsplit(".", 1)[0]
            cls = EAL.load_blueprint_class(bp)
            check("class path loads " + p, cls is not None)
        else:
            check("asset exists " + p, EAL.does_asset_exist(p.rsplit(".", 1)[0]))
    check("DA_Audio.debug_force_music_state == -1", int(da.get_editor_property("debug_force_music_state")) == -1)
    # Typed read through the Python property names (a second reader than ToolsetLibrary)
    check("DA_Audio.bell_location", same(da.get_editor_property("bell_location"), unreal.Vector(12420.1, 2000.0, 2750.0)))
    check("DA_Audio.bell_beats count", len(da.get_editor_property("bell_beats")) == 6)
    check("DA_Audio.interaction_cues count", len(da.get_editor_property("interaction_cues")) == 9)
    check("DA_Audio.silent_classes count", len(da.get_editor_property("silent_classes")) == 3)
    check("DA_Audio.small_bell_pitch count", len(da.get_editor_property("small_bell_pitch")) == 4)
    check("DA_Audio.user_classes count", len(da.get_editor_property("user_classes")) == 6)
    # C++ defaults of the groups the script does not write
    defaults = {"mix_fade_seconds": 0.75,
                "thunder_jitter": 0.4, "thunder_near_at": 0.75, "thunder_far_below": 0.4, "thunder_distance": 6000.0, "strike_crack_delay": 0.12,
                "ambient_toll_gap_after_beat": 90.0, "ambient_toll_volume": 0.5, "ambient_toll_max_tension": 0.5, "drone_seconds": 45.0,
                "tension_near_distance": 2500.0, "music_min_stage": 3, "stress_chase": 1.0, "stress_near_search": 0.6, "stress_decay": 0.25,
                "darkness_lit": 0.15, "darkness_unlit": 0.55, "candle_out_stress": 0.35, "random_seed": 0}
    for prop, value in defaults.items():
        check("DA_Audio default %s" % prop, feq(da.get_editor_property(prop), value), da.get_editor_property(prop))
    for prop, value in OWNER_CHOICES["da_audio"].items():
        check("DA_Audio owner choice %s = %g" % (prop, value), feq(da.get_editor_property(prop), value), da.get_editor_property(prop))


# ---------------------------------------------------------------------------------------------------------------------------------
# 6. DT_Footsteps
# ---------------------------------------------------------------------------------------------------------------------------------

SURFACES = [  # (row name, surface type enum name, step sound group)
    ("Default", "SurfaceType_Default", "Stone"),
    ("Stone", "SurfaceType1", "Stone"),
    ("Wood", "SurfaceType2", "Wood"),
    ("Earth", "SurfaceType3", "Earth"),
    ("Grass", "SurfaceType4", "Grass"),
    ("Water", "SurfaceType5", "Water"),
    ("Metal", "SurfaceType6", "Metal"),
]


def footstep_rows():
    rows = []
    for row, surface, group in SURFACES:
        variants = [object_path(sound_package(n)) for n in seq("SFX_LB_Step_" + group, 6)]
        rows.append({"Name": row, "SurfaceType": surface, "Sound": variants[0], "Variants": variants, "VolumeMin": 0.8, "VolumeMax": 1.0,
                     "PitchMin": 0.95, "PitchMax": 1.05, "CrouchVolume": 0.5, "SprintVolume": 1.25})
    return rows


def object_string_path(s):
    """The export writes /Script/Engine.SoundWave'/Game/x.x'; the import accepts the bare path. Returns the bare path."""
    m = re.search(r"'([^']*)'", s)
    return m.group(1) if m else s


def normalize_rows(rows):
    out = []
    for r in rows:
        r = dict(r)
        r["Sound"] = object_string_path(r["Sound"])
        r["Variants"] = [object_string_path(v) for v in r["Variants"]]
        out.append(r)
    return out


def dt_matches(dt, wanted):
    current = normalize_rows(json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(dt)))
    if len(current) != len(wanted):
        return False, "%d rows, wanted %d" % (len(current), len(wanted))
    errors = []
    subset_eq(wanted, current, "DT_Footsteps", errors)
    return not errors, "; ".join(errors[:4])


def build_dt():
    wanted = footstep_rows()
    dt = EAL.load_asset(DT_PATH) if EAL.does_asset_exist(DT_PATH) else None
    if not check("loads DT_Footsteps", dt is not None):
        return None
    check("DT_Footsteps row struct is LBFootstepRow", dt.get_class().get_name() == "DataTable" and "LBFootstepRow" in str(unreal.DataTableFunctionLibrary.get_data_table_row_struct(dt)))
    ok, why = dt_matches(dt, wanted)
    if not ok and APPLY:
        filled = unreal.DataTableFunctionLibrary.fill_data_table_from_json_string(dt, json.dumps(wanted))
        check("DT_Footsteps fill_data_table_from_json_string", bool(filled), filled)
        mark_changed(dt)
        record("DT_Footsteps", "rows", ", ".join(r["Name"] for r in wanted))
        ok, why = dt_matches(dt, wanted)
    check("DT_Footsteps rows read back", ok, why)
    names = [str(n) for n in unreal.DataTableFunctionLibrary.get_data_table_row_names(dt)]
    check("DT_Footsteps row names", names == [r["Name"] for r in wanted], names)
    for row in normalize_rows(json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(dt))):
        check("DT_Footsteps %s has 6 variants" % row["Name"], len(row["Variants"]) == 6)
        check("DT_Footsteps %s Sound is variant 01" % row["Name"], row["Sound"] == row["Variants"][0])
        for v in row["Variants"]:
            check("DT_Footsteps variant exists " + v, EAL.does_asset_exist(v.rsplit(".", 1)[0]))
    return dt


# ---------------------------------------------------------------------------------------------------------------------------------
# 7. Save and verify
# ---------------------------------------------------------------------------------------------------------------------------------

def save_changed():
    for package in sorted(changed_packages):
        if not allowed(package):
            check("save guard " + package, False, "outside the allowed paths")
            continue
        ok = EAL.save_asset(package, False)
        check("saved " + package, bool(ok))
        if ok:
            report["saved"].append(package)
    changed_packages.clear()
    dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    ours = [d for d in dirty if allowed(d)]
    check("no dirty package of ours after the save", not ours, ours[:10])
    if [d for d in dirty if not allowed(d)]:
        note("dirty packages outside our paths (not saved): %s" % [d for d in dirty if not allowed(d)][:10])


def count_folders(items):
    expected = {}
    for name in items:
        folder = folder_for(name).rsplit("/", 1)[1]
        expected[folder] = expected.get(folder, 0) + 1
    counts = {}
    for folder in expected:
        listed = EAL.list_assets("%s/%s" % (AUD, folder), recursive=False, include_folder=False)
        counts[folder] = len(listed)
        check("folder %s holds %d assets" % (folder, expected[folder]), len(listed) == expected[folder], len(listed))
    mix_listed = EAL.list_assets(MIX, recursive=False, include_folder=False)
    counts["Mix"] = len(mix_listed)
    check("folder Mix holds 25 assets", len(mix_listed) == 6 + 1 + len(ATTENUATION) + len(CONCURRENCY) + len(REVERB), len(mix_listed))
    phys_listed = EAL.list_assets(PHYS, recursive=False, include_folder=False)
    counts["Physics"] = len(phys_listed)
    check("folder Physics holds 6 assets", len(phys_listed) == 6, len(phys_listed))
    report["counts"] = counts
    report["counts"]["sounds_total"] = sum(counts[f] for f in expected)
    check("175 sounds in total", report["counts"]["sounds_total"] == 175, report["counts"]["sounds_total"])


def verify_all(items, classes, attenuation, concurrency, reverbs, mix, phys):
    """Reads everything back (in a fresh process this proves the saved files)."""
    count_folders(items)
    check("175 WAVs found in SourceArt", len(items) == 175, len(items))
    check("51 generated + 124 recorded", sum(1 for i in items.values() if i["source"] == "generated") == 51 and sum(1 for i in items.values() if i["source"] == "recorded") == 124)
    loops = []
    for name, info in items.items():
        wave = EAL.load_asset(sound_package(name))
        if wave is None:
            check("sound loads " + name, False)
            continue
        cls_key, att_name, con_name, loop, volume = sound_targets(name, info)
        ok = True
        ok &= check("%s looping" % name, bool(wave.get_editor_property("looping")) == loop, wave.get_editor_property("looping"))
        ok &= check("%s sound class" % name, wave.get_editor_property("sound_class_object") == classes[cls_key], wave.get_editor_property("sound_class_object"))
        ok &= check("%s attenuation" % name, wave.get_editor_property("attenuation_settings") == (attenuation[att_name] if att_name else None))
        ok &= check("%s volume" % name, feq(wave.get_editor_property("volume"), volume, 1e-4), wave.get_editor_property("volume"))
        have = wave_concurrency(wave)
        ok &= check("%s concurrency" % name, (have == [concurrency[con_name]]) if con_name else have == [], [h.get_name() for h in have])
        ok &= check("%s duration matches its WAV" % name, abs(float(wave.get_editor_property("duration")) - wav_seconds(info["path"])) < 0.01,
                    "asset %.3f s, WAV %.3f s" % (float(wave.get_editor_property("duration")), wav_seconds(info["path"])))
        if loop:
            loops.append(name)
        report["properties"][name] = dict(cls=CLASS_NAMES[cls_key], att=att_name, con=con_name, loop=loop, volume=round(volume, 6))
    check("loop list: 4 weather + 6 rooms + 3 drones + tension + chase + 3 warden breaths + robe = 19", len(loops) == 19, loops)
    # Mix assets
    master = classes["Master"]
    kids = [k.get_name() for k in master.get_editor_property("child_classes")] if master else []
    check("SCL_LB_Master children", sorted(kids) == sorted(CLASS_NAMES[k] for k in CLASS_NAMES if k != "Master"), kids)
    for key in ("SFX", "Ambience", "Music", "Voice", "UI"):
        c = classes[key]
        check("%s parent is Master" % CLASS_NAMES[key], c is not None and c.get_editor_property("parent_class") == master)
    for name, spec in ATTENUATION.items():
        asset = attenuation[name]
        if asset is None:
            continue
        settings = asset.get_editor_property("attenuation")
        for prop, value in attenuation_wanted(spec).items():
            check("%s.%s" % (name, prop), same(settings.get_editor_property(prop), value), "read %r" % (settings.get_editor_property(prop),))
        report["properties"][name] = {p: fmt(settings.get_editor_property(p)) for p in attenuation_wanted(spec)}
    for name, (count, rule) in CONCURRENCY.items():
        cfg = concurrency[name].get_editor_property("concurrency")
        check("%s max_count" % name, int(cfg.get_editor_property("max_count")) == count, cfg.get_editor_property("max_count"))
        check("%s resolution_rule" % name, cfg.get_editor_property("resolution_rule") == getattr(unreal.MaxConcurrentResolutionRule, rule), cfg.get_editor_property("resolution_rule"))
        report["properties"][name] = dict(max_count=count, rule=rule)
    for name, (decay, density, diffusion, gain, gainhf) in REVERB.items():
        asset = reverbs[name]
        for prop, value in (("decay_time", decay), ("density", density), ("diffusion", diffusion), ("gain", gain), ("gain_hf", gainhf),
                            ("late_delay", REVERB_LATE_DELAY), ("reflections_delay", REVERB_REFLECTIONS_DELAY)):
            check("%s.%s" % (name, prop), feq(asset.get_editor_property(prop), value), asset.get_editor_property(prop))
        report["properties"][name] = dict(decay=decay, density=density, diffusion=diffusion, gain=gain, gain_hf=gainhf)
    check("SMX_LB_User exists", mix is not None and mix.get_class().get_name() == "SoundMix")
    for name, surface in PHYS_MATS.items():
        asset = phys[name]
        check("%s surface_type" % name, asset is not None and asset.get_editor_property("surface_type") == getattr(unreal.PhysicalSurface, "SURFACE_TYPE%d" % surface),
              asset.get_editor_property("surface_type") if asset else None)


def write_report():
    report["ok"] = not report["failures"]
    report["failure_count"] = len(report["failures"])
    if OUT:
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1)
    unreal.log("P16-2 RESULT: %s (%d checks, %d failures) mode=%s" % ("PASS" if report["ok"] else "FAIL", report["checks"], len(report["failures"]), MODE))


def main():
    items = collect_wavs()
    note("mode=%s reimport=%s; %d WAVs found" % (MODE, REIMPORT, len(items)))
    for name in items:
        if not folder_for(name):
            check("folder mapping for " + name, False, "no rule")
        if not rule_for(SOUND_RULES, name):
            check("sound rule for " + name, False, "no rule")
    if report["failures"]:
        return

    classes = build_sound_classes()
    attenuation = build_attenuation()
    concurrency = build_concurrency()
    reverbs = build_reverb()
    mix = build_mix_asset()
    phys = build_phys()
    if report["failures"]:
        return

    if APPLY:
        report["imported"] = import_sounds(items)
        apply_wave_properties(items, classes, attenuation, concurrency)
    da, expected = build_da()
    dt = build_dt()

    if APPLY:
        save_changed()

    verify_all(items, classes, attenuation, concurrency, reverbs, mix, phys)
    if da is not None:
        verify_da(da, expected)
    report["properties"]["DA_Audio"] = {"top_level_properties_written": sorted(expected.keys()), "interaction_cues": len(expected["InteractionCues"]),
                                         "silent_classes": len(expected["SilentClasses"]), "bell_beats": len(expected["BellBeats"])}


try:
    main()
except Exception as exc:  # report, never half-save silently
    report["failures"].append("exception: %r" % (exc,))
    report["traceback"] = traceback.format_exc()
    unreal.log_error("P16-2 EXCEPTION: " + report["traceback"])
finally:
    write_report()

if report["failures"]:
    raise RuntimeError("P16-2: %d failed checks; see the report" % len(report["failures"]))
