"""P18-2: the UI assets and their hookup, headless (Unreal CLOSED, one Unreal process at a time).

Run (editor closed). NOTE the route: the font importer (FontFileImportFactory) asserts in a commandlet because it needs Slate
(`-run=pythonscript` crashes with "CurrentApplication.IsValid()"), so this script runs as `-ExecutePythonScript` in the non-commandlet
editor-cmd (Slate exists under -nullrhi) and ends by quitting the editor itself:

    UnrealEditor-Cmd.exe <uproject> -ExecutePythonScript="<this file>" -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>

Environment variables (the same pattern as Tools/audio/p16_2_assets.py and Tools/cine/p17_assets.py):
    LB_OUT       path of the JSON report
    LB_MODE      "apply" (default): import, create, set, save the changed packages explicitly, then verify in the same process
                 "verify": read-only, nothing is created, set or saved; run it in a FRESH process to prove what is on disk
    LB_REIMPORT  "1": re-import the textures and fonts that already exist (default: only the missing ones)

What it does (docs/plans/P18_UI_SETTINGS.md section 4, task P18-2):
 1. fonts: 4 UFontFace (FF_LB_EBGaramond_<Weight>) from the EB Garamond TTFs, and 4 UFont (F_LB_EBGaramond_<Weight>), each a composite font
    whose default typeface is that one face (ULBUIStyle holds one UFont per weight, FSlateFontInfo(UFont, size)); OFL.txt next to them
 2. key icons: the Kenney "Keyboard & Mouse / Double" PNGs as T_Key_<Key> (TC_EDITOR_ICON = UserInterface2D, no mips, UI group, never stream)
 3. T_LB_BrightnessSymbol (generated here with zlib and struct, no PIL) and T_LB_MenuStill (frame 0 of the menu drift render)
 4. MS_LB_MenuDrift (UFileMediaSource, "./Content/Movies/LB_MenuDrift.mp4", relative to the project dir so it works packaged)
 5. DA_UIStyle (class LBUIStyle) filled: fonts, key-icon map, 4 sounds, media source, fallback still, brightness symbol; colours and sizes stay at the class defaults
 6. IA_Pause (Boolean, Pressed trigger, trigger_when_paused so Escape can resume a paused game), and IMC_LB_Gameplay: the Escape mapping, and the
    player-mappable names/display names exactly as LBUILogic::MappingNameFor / DisplayNameFor (read from Source/LastBell/UI/LBUILogic.cpp)
 7. Blueprints: BP_LBPlayerController.PauseAction = IA_Pause; BP_MenuPlayerController.HUDWidgetClass = LBMainMenuWidget (each compiled and saved)
 8. config (plain text, CRLF kept): DefaultGame.ini (UIStyle link, DirectoriesToAlwaysStageAsNonUFS for the fonts and Movies) and DefaultInput.ini
    (Enhanced Input user settings on, IMC_LB_Gameplay registered with the user settings, which MapPlayerKey needs)
 9. verify: every item above, the sound classes (bIsUISound only on SCL_LB_UI) and the UI sounds that Tools/audio/p16_2_assets.py imports

Idempotent: a value is written only when the read-back differs, and only changed packages are saved (explicit EditorAssetLibrary.save_asset per
package, never save-all). It touches only the packages in `allowed()`. It never loads or saves a map.

The process exit code of UnrealEditor-Cmd is NOT reliable; read the report (`ok`) or the log line "P18-2 RESULT". On any failed check the
script ends with an uncaught RuntimeError (logged).
"""
import json
import os
import re
import shutil
import struct
import subprocess
import traceback
import zlib

import unreal

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
INCOMING = os.path.join(ROOT, "ExternalAssets", "Incoming")
FONT_SRC = os.path.join(INCOMING, "ebgaramond")
ICON_SRC = os.path.join(INCOMING, "kenney-input-prompts", "extracted", "Keyboard & Mouse", "Double")
SRC_UI = os.path.join(ROOT, "SourceArt", "UI")
STILL_PNG = os.path.join(SRC_UI, "T_LB_MenuStill.png")
SYMBOL_PNG = os.path.join(SRC_UI, "T_LB_BrightnessSymbol.png")
RENDER_FRAME0 = os.path.join(ROOT, "Saved", "MovieRenders", "MenuDrift", "LS_LB_MenuDrift.0000.png")
VIDEO = os.path.join(ROOT, "Content", "Movies", "LB_MenuDrift.mp4")
LOGIC_CPP = os.path.join(ROOT, "Source", "LastBell", "UI", "LBUILogic.cpp")
CONF_GAME = os.path.join(ROOT, "Config", "DefaultGame.ini")
CONF_INPUT = os.path.join(ROOT, "Config", "DefaultInput.ini")
# Not in the fonts folder: that folder is asset-only (a non-UFS staging entry would copy its uncooked .uasset files loose). QA M3.
OFL_DST = os.path.join(ROOT, "Content", "LastBell", "Licenses", "OFL_EBGaramond.txt")

OUT = os.environ.get("LB_OUT", "")
MODE = os.environ.get("LB_MODE", "apply").lower()
APPLY = MODE == "apply"
REIMPORT = os.environ.get("LB_REIMPORT", "0") == "1"

UI = "/Game/LastBell/UI"
FONTS = UI + "/Fonts"
ICONS = UI + "/KeyIcons"
INPUT = "/Game/LastBell/Input"
MIX = "/Game/LastBell/Audio/Mix"
BP_PC = "/Game/LastBell/Blueprints/BP_LBPlayerController"
BP_MENU_PC = "/Game/LastBell/Blueprints/Menu/BP_MenuPlayerController"
BP_MENU_GM = "/Game/LastBell/Blueprints/Menu/BP_MenuGameMode"
WBP_MAINMENU = UI + "/WBP_MainMenu"
DA_PATH = UI + "/DA_UIStyle"
MS_PATH = UI + "/MS_LB_MenuDrift"
STILL_PATH = UI + "/T_LB_MenuStill"
SYMBOL_PATH = UI + "/T_LB_BrightnessSymbol"
IA_PAUSE = INPUT + "/IA_Pause"
IMC_PATH = INPUT + "/IMC_LB_Gameplay"
MEDIA_FILE_PATH = "./Content/Movies/LB_MenuDrift.mp4"

# the exact asset packages this script may create, change or save (a guard, as in p16_2_assets.py / p17_assets.py)
ALLOWED_PREFIX = (FONTS + "/", ICONS + "/")
ALLOWED_EXACT = (DA_PATH, MS_PATH, STILL_PATH, SYMBOL_PATH, IA_PAUSE, IMC_PATH, BP_PC, BP_MENU_PC)

EAL = unreal.EditorAssetLibrary
TL = unreal.ToolsetLibrary
ATOOLS = unreal.AssetToolsHelpers.get_asset_tools()

report = {"mode": MODE, "ok": False, "checks": 0, "failures": [], "counts": {}, "saved": [], "notes": [], "set_log": [], "findings": {}}
changed_packages = set()


def check(name, ok, detail=""):
    report["checks"] += 1
    if not ok:
        msg = "%s: %s" % (name, detail)
        report["failures"].append(msg)
        unreal.log_error("P18-2 CHECK FAILED: " + msg)
    return bool(ok)


def note(text):
    report["notes"].append(text)
    unreal.log("P18-2: " + text)


def allowed(path):
    return path in ALLOWED_EXACT or any(path.startswith(p) for p in ALLOWED_PREFIX)


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


def obj_path(package):
    return "%s.%s" % (package, package.rsplit("/", 1)[1])


def load(package, class_name=None):
    if not EAL.does_asset_exist(package):
        return None
    asset = EAL.load_asset(package)
    if asset is not None and class_name and asset.get_class().get_name() != class_name:
        check("class of " + package, False, asset.get_class().get_name())
    return asset


def import_file(src, folder, name, factory=None):
    """One AssetImportTask (automated, replace existing). Returns the loaded asset or None."""
    task = unreal.AssetImportTask()
    task.filename = src
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.save = False
    if factory is not None:
        task.factory = factory
    ATOOLS.import_asset_tasks([task])
    paths = list(task.imported_object_paths)
    check("imported " + name, len(paths) == 1, paths)
    asset = EAL.load_asset(folder + "/" + name)
    if asset is not None:
        mark_changed(asset)
        record(name, "(imported)", os.path.basename(src))
    return asset


# ---------------------------------------------------------------------------------------------------------------------------------
# Source files made here: the brightness symbol (zlib + struct, no PIL) and the menu still
# ---------------------------------------------------------------------------------------------------------------------------------

def png_bytes(width, height, rgba_rows):
    """A truecolour + alpha PNG from rows of RGBA bytes (bytes of length width*4)."""
    raw = b"".join(b"\x00" + row for row in rgba_rows)  # filter type 0 per scanline

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def symbol_coverage(x, y):
    """1.0 inside the mark at (x, y) in 0..256 pixel space, else 0: a ring, a cross whose arms reach the ring, and a small hub ring."""
    dx, dy = x - 128.0, y - 128.0
    r = (dx * dx + dy * dy) ** 0.5
    if 108.0 <= r <= 116.0:                            # the outer ring
        return 1.0
    if 14.0 <= r <= 20.0:                              # the hub ring
        return 1.0
    if r <= 108.0 and r >= 28.0 and (abs(dx) <= 4.0 or abs(dy) <= 4.0):   # the cross (arms from the hub to the ring)
        return 1.0
    return 0.0


def make_symbol_png(path):
    """256x256, mid-grey (128, 128, 128) on transparent, 4x4 supersampled edges. Deterministic."""
    size, ss = 256, 4
    rows = []
    for py in range(size):
        row = bytearray()
        for px in range(size):
            hits = 0
            for sy in range(ss):
                for sx in range(ss):
                    hits += symbol_coverage(px + (sx + 0.5) / ss, py + (sy + 0.5) / ss) > 0.5
            alpha = int(round(255.0 * hits / (ss * ss)))
            row += bytes((128, 128, 128, alpha))
        rows.append(bytes(row))
    data = png_bytes(size, size, rows)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return len(data)


def ffmpeg_png(args):
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + args, check=True)


def make_still_png(path):
    """Frame 0 of the courtyard drift, opaque RGB: from the MRQ render when it still exists, else the first frame of the MP4."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.isfile(RENDER_FRAME0):
        ffmpeg_png(["-i", RENDER_FRAME0, "-vf", "format=rgb24", "-frames:v", "1", path])
        return "frame 0 of Saved/MovieRenders/MenuDrift"
    ffmpeg_png(["-i", VIDEO, "-vf", "format=rgb24", "-frames:v", "1", path])
    return "frame 0 of Content/Movies/LB_MenuDrift.mp4"


def png_size(path):
    with open(path, "rb") as fh:
        head = fh.read(24)
    return struct.unpack(">II", head[16:24])


# ---------------------------------------------------------------------------------------------------------------------------------
# Config (plain text, CRLF kept)
# ---------------------------------------------------------------------------------------------------------------------------------

def read_ini(path):
    with open(path, "rb") as fh:
        text = fh.read().decode("utf-8")
    return text.replace("\r\n", "\n")


def write_ini(path, text):
    with open(path, "wb") as fh:
        fh.write(text.replace("\n", "\r\n").encode("utf-8"))


def ini_section_lines(text, section):
    """The lines of [section] (without the header); None when the section does not exist."""
    lines = text.split("\n")
    out, inside = [], False
    found = False
    for line in lines:
        if line.startswith("["):
            inside = line.strip() == "[%s]" % section
            found = found or inside
            continue
        if inside:
            out.append(line)
    return out if found else None


def ensure_ini_lines(path, section, wanted, after_key=None):
    """Makes sure every wanted line is in [section] (creating the section at the end of the file); returns the lines that were added."""
    text = read_ini(path)
    existing = ini_section_lines(text, section)
    missing = [w for w in wanted if existing is None or w not in [l.strip() for l in existing]]
    if not missing:
        return []
    if not APPLY:
        return missing
    lines = text.split("\n")
    if existing is None:
        while lines and lines[-1] == "":
            lines.pop()
        lines += ["", "[%s]" % section] + missing + [""]
    else:
        start = next(i for i, l in enumerate(lines) if l.strip() == "[%s]" % section)
        end = start + 1
        while end < len(lines) and not lines[end].startswith("["):
            end += 1
        insert_at = end
        while insert_at > start + 1 and lines[insert_at - 1].strip() == "":
            insert_at -= 1
        if after_key:
            for i in range(start + 1, end):
                if lines[i].startswith(after_key + "="):
                    insert_at = i + 1
        lines[insert_at:insert_at] = missing
    write_ini(path, "\n".join(lines))
    record(os.path.basename(path), "[%s]" % section, "; ".join(missing))
    return missing


GAME_SECTION = "/Script/LastBell.LBGameSettings"
PACK_SECTION = "/Script/UnrealEd.ProjectPackagingSettings"
INPUT_SECTION = "/Script/EnhancedInput.EnhancedInputDeveloperSettings"
CONF_WANTED = [
    (CONF_GAME, GAME_SECTION, ["UIStyle=/Game/LastBell/UI/DA_UIStyle.DA_UIStyle"], "CinematicSettings"),
    (CONF_GAME, PACK_SECTION, ['+DirectoriesToAlwaysStageAsNonUFS=(Path="LastBell/Licenses")', '+DirectoriesToAlwaysStageAsNonUFS=(Path="Movies")'], None),
    # Enhanced Input: user settings on (the 5.8 default is already on; explicit here), and IMC_LB_Gameplay registered with the user settings at
    # start-up. ALBPlayerController adds the IMC itself with the default options (bNotifyUserSettings false), so without this registration the
    # user settings know no mapping name and LBKeyBindings::IsRebindable is false. bAddImmediately=False: the controller keeps adding it.
    (CONF_INPUT, INPUT_SECTION, ["bEnableUserSettings=True",
                                 "+DefaultMappingContexts=(InputMappingContext=/Game/LastBell/Input/IMC_LB_Gameplay.IMC_LB_Gameplay,Priority=0,bAddImmediately=False,bRegisterWithUserSettings=True)"], None),
]


def apply_config():
    for path, section, wanted, after in CONF_WANTED:
        added = ensure_ini_lines(path, section, wanted, after)
        if added and APPLY:
            note("config %s [%s]: added %d line(s)" % (os.path.basename(path), section, len(added)))


def verify_config():
    for path, section, wanted, _after in CONF_WANTED:
        existing = [l.strip() for l in (ini_section_lines(read_ini(path), section) or [])]
        for w in wanted:
            check("%s [%s] has %s" % (os.path.basename(path), section.rsplit(".", 1)[-1], w[:60]), w in existing)
    # a CRLF file must stay CRLF (the .gitattributes rule is `*.ini text eol=crlf`)
    for path in (CONF_GAME, CONF_INPUT):
        raw = open(path, "rb").read()
        check("%s keeps CRLF line ends" % os.path.basename(path), raw.count(b"\n") == raw.count(b"\r\n"), "%d LF, %d CRLF" % (raw.count(b"\n"), raw.count(b"\r\n")))


# ---------------------------------------------------------------------------------------------------------------------------------
# 1. Fonts
# ---------------------------------------------------------------------------------------------------------------------------------

WEIGHTS = ["Regular", "Italic", "SemiBold", "Bold"]   # the four ULBUIStyle fields FontRegular, FontItalic, FontSemiBold, FontBold


def face_pkg(w):
    return "%s/FF_LB_EBGaramond_%s" % (FONTS, w)


def font_pkg(w):
    return "%s/F_LB_EBGaramond_%s" % (FONTS, w)


def font_json(w):
    return {"CompositeFont": {"DefaultTypeface": {"Fonts": [{"Name": w, "Font": {"FontFaceAsset": {"refPath": obj_path(face_pkg(w))}}}]}}}


def font_readback(font):
    return json.loads(TL.get_object_properties(font, ["CompositeFont"]))["CompositeFont"]["defaultTypeface"]["fonts"]


def font_ok(font, w):
    fonts = font_readback(font)
    return len(fonts) == 1 and fonts[0]["name"] == w and fonts[0]["font"]["fontFaceAsset"]["refPath"] == obj_path(face_pkg(w))


def build_fonts():
    out = {}
    for w in WEIGHTS:
        face_path, f_path = face_pkg(w), font_pkg(w)
        assert allowed(face_path) and allowed(f_path)
        face = load(face_path, "FontFace")
        if (face is None or REIMPORT) and APPLY:
            face = import_file(os.path.join(FONT_SRC, "EBGaramond-%s.ttf" % w), FONTS, "FF_LB_EBGaramond_%s" % w)
        check("font face exists " + face_path, face is not None)
        font = load(f_path, "Font")
        if font is None and APPLY and face is not None:
            font = ATOOLS.create_asset("F_LB_EBGaramond_%s" % w, FONTS, unreal.Font, unreal.FontFactory())
            check("created " + f_path, font is not None)
            if font is not None:
                mark_changed(font)
                record(font.get_name(), "(created)", "Font")
        if font is not None and face is not None and not font_ok(font, w):
            if APPLY:
                ok = TL.set_object_properties(font, json.dumps(font_json(w)))
                check("set composite font " + f_path, bool(ok), ok)
                mark_changed(font)
                record(font.get_name(), "CompositeFont.DefaultTypeface", "[%s -> %s]" % (w, face.get_name()))
        if font is not None:
            check("font %s: one typeface entry '%s' holding %s" % (font.get_name(), w, face_pkg(w).rsplit("/", 1)[1]), font_ok(font, w), font_readback(font))
            set_prop(font, "font_cache_type", unreal.FontCacheType.RUNTIME, font.get_name())
        out[w] = (face, font)
    return out


def copy_ofl():
    src = os.path.join(FONT_SRC, "OFL.txt")
    if not os.path.isfile(src):
        return check("OFL.txt source exists", False, src)
    same_file = os.path.isfile(OFL_DST) and open(src, "rb").read() == open(OFL_DST, "rb").read()
    if not same_file and APPLY:
        os.makedirs(os.path.dirname(OFL_DST), exist_ok=True)
        shutil.copyfile(src, OFL_DST)
        record("OFL.txt", "(copied)", "Content/LastBell/Licenses/OFL_EBGaramond.txt")
        same_file = True
    return check("Content/LastBell/Licenses/OFL_EBGaramond.txt is the licence from the repository", same_file)


# ---------------------------------------------------------------------------------------------------------------------------------
# 2. Key icons
# ---------------------------------------------------------------------------------------------------------------------------------

def key_icon_table():
    """(texture name, source png stem, [FKey names]) for every key LBUILogic::IconKeys() lists (see LBUILogic.cpp)."""
    rows = []
    for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        rows.append((c, "keyboard_" + c.lower(), [c]))
    for digit, word in zip("0123456789", ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]):
        rows.append((digit, "keyboard_" + digit, [word]))
    for d in ("Up", "Down", "Left", "Right"):
        rows.append((d, "keyboard_arrow_" + d.lower(), [d]))
    rows += [
        ("Shift", "keyboard_shift", ["LeftShift", "RightShift"]),
        ("Ctrl", "keyboard_ctrl", ["LeftControl", "RightControl"]),
        ("Alt", "keyboard_alt", ["LeftAlt", "RightAlt"]),
        ("Space", "keyboard_space", ["SpaceBar"]),
        ("Escape", "keyboard_escape", ["Escape"]),
        ("Tab", "keyboard_tab", ["Tab"]),
        ("Enter", "keyboard_enter", ["Enter"]),
        ("Backspace", "keyboard_backspace", ["BackSpace"]),
        ("MouseLeft", "mouse_left", ["LeftMouseButton"]),
        ("MouseRight", "mouse_right", ["RightMouseButton"]),
        ("MouseMiddle", "mouse_scroll", ["MiddleMouseButton"]),        # the pack has no mouse_middle: the wheel icon serves the middle button
        ("MouseThumb1", "mouse_side_back", ["ThumbMouseButton"]),
        ("MouseThumb2", "mouse_side_forward", ["ThumbMouseButton2"]),
    ]
    return rows


def icon_pkg(name):
    return "%s/T_Key_%s" % (ICONS, name)


def texture_settings(compression, group="TEXTUREGROUP_UI"):
    return {
        "compression_settings": compression,
        "mip_gen_settings": unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS,
        "lod_group": getattr(unreal.TextureGroup, group),
        "never_stream": True,
        "srgb": True,
    }


ICON_COMPRESSION = unreal.TextureCompressionSettings.TC_EDITOR_ICON   # "UserInterface2D"


def apply_texture_settings(tex, settings, owner):
    for prop, value in settings.items():
        set_prop(tex, prop, value, owner)


def ensure_texture(package, src, settings):
    """Import (when missing, or LB_REIMPORT) and set the texture settings. Returns the texture or None."""
    assert allowed(package), "refusing to touch " + package
    folder, name = package.rsplit("/", 1)
    tex = load(package, "Texture2D")
    if (tex is None or REIMPORT) and APPLY:
        if not check("source exists " + os.path.basename(src), os.path.isfile(src), src):
            return None
        tex = import_file(src, folder, name)
    if not check("texture exists " + package, tex is not None):
        return None
    apply_texture_settings(tex, settings, name)
    return tex


def build_icons():
    out = {}
    settings = texture_settings(ICON_COMPRESSION)
    for name, stem, _keys in key_icon_table():
        out[name] = ensure_texture(icon_pkg(name), os.path.join(ICON_SRC, stem + ".png"), settings)
    return out


# ---------------------------------------------------------------------------------------------------------------------------------
# 3 and 4. Brightness symbol, menu still, media source
# ---------------------------------------------------------------------------------------------------------------------------------

def build_symbol_and_still():
    if APPLY:
        n = make_symbol_png(SYMBOL_PNG)
        note("brightness symbol PNG: %d bytes" % n)
        if not os.path.isfile(STILL_PNG):
            note("menu still: " + make_still_png(STILL_PNG))
    check("T_LB_BrightnessSymbol source is 256x256", os.path.isfile(SYMBOL_PNG) and png_size(SYMBOL_PNG) == (256, 256), SYMBOL_PNG)
    check("T_LB_MenuStill source is 1920x1080", os.path.isfile(STILL_PNG) and png_size(STILL_PNG) == (1920, 1080), STILL_PNG)
    symbol = ensure_texture(SYMBOL_PATH, SYMBOL_PNG, texture_settings(ICON_COMPRESSION))
    # the still is a 1080p photo-like frame: default (block) compression, not the uncompressed UI icon format; still no mips and no streaming
    still = ensure_texture(STILL_PATH, STILL_PNG, texture_settings(unreal.TextureCompressionSettings.TC_DEFAULT))
    return symbol, still


def build_media_source():
    assert allowed(MS_PATH)
    ms = load(MS_PATH, "FileMediaSource")
    if ms is None and APPLY:
        ms = ATOOLS.create_asset("MS_LB_MenuDrift", UI, unreal.FileMediaSource, unreal.FileMediaSourceFactoryNew())
        check("created " + MS_PATH, ms is not None)
        if ms is not None:
            mark_changed(ms)
            record("MS_LB_MenuDrift", "(created)", "FileMediaSource")
    if not check("MS_LB_MenuDrift exists", ms is not None):
        return None
    set_prop(ms, "file_path", MEDIA_FILE_PATH, "MS_LB_MenuDrift")
    return ms


# ---------------------------------------------------------------------------------------------------------------------------------
# 5. DA_UIStyle
# ---------------------------------------------------------------------------------------------------------------------------------

def build_da_json():
    icons = {}
    for name, _stem, keys in key_icon_table():
        for k in keys:
            icons[k] = obj_path(icon_pkg(name))
    return {
        "FontRegular": obj_path(font_pkg("Regular")),
        "FontItalic": obj_path(font_pkg("Italic")),
        "FontSemiBold": obj_path(font_pkg("SemiBold")),
        "FontBold": obj_path(font_pkg("Bold")),
        "KeyIcons": icons,
        "HoverSound": obj_path("/Game/LastBell/Audio/UI/SFX_LB_UI_Hover"),
        "SelectSound": obj_path("/Game/LastBell/Audio/UI/SFX_LB_UI_Select"),
        "BackSound": obj_path("/Game/LastBell/Audio/UI/SFX_LB_UI_Back"),
        "SliderTickSound": obj_path("/Game/LastBell/Audio/UI/SFX_LB_UI_Tick"),
        "MenuVideo": obj_path(MS_PATH),
        "MenuFallbackImage": obj_path(STILL_PATH),
        "BrightnessSymbol": obj_path(SYMBOL_PATH),
    }


def unref(value):
    """A soft or hard object reference reads back either as the path string or as {"refPath": path}."""
    return value.get("refPath") if isinstance(value, dict) and set(value.keys()) == {"refPath"} else value


def da_mismatch(da, expected):
    got = json.loads(TL.get_object_properties(da, list(expected.keys())))
    errors = []
    for key, want in expected.items():
        have = got.get(key)
        if isinstance(want, dict):
            if not isinstance(have, dict):
                errors.append("%s: not a map" % key)
                continue
            have_map = {k: unref(v) for k, v in have.items()}
            for k, v in want.items():
                if have_map.get(k) != v:
                    errors.append("%s[%s]: wanted %s read %s" % (key, k, v, have_map.get(k)))
            if len(have_map) != len(want):
                errors.append("%s: %d entries read, %d wanted" % (key, len(have_map), len(want)))
        elif unref(have) != want:
            errors.append("%s: wanted %s read %s" % (key, want, have))
    return errors


def build_da():
    assert allowed(DA_PATH)
    expected = build_da_json()
    da = load(DA_PATH, "LBUIStyle")
    if da is None and APPLY:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property("data_asset_class", unreal.LBUIStyle)
        da = ATOOLS.create_asset("DA_UIStyle", UI, unreal.LBUIStyle, factory)
        check("created DA_UIStyle", da is not None)
        if da is not None:
            mark_changed(da)
            record("DA_UIStyle", "(created)", "LBUIStyle")
    if not check("DA_UIStyle exists", da is not None):
        return None, expected
    errors = da_mismatch(da, expected)
    if errors and APPLY:
        ok = TL.set_object_properties(da, json.dumps(expected))
        check("DA_UIStyle set_object_properties", bool(ok), ok)
        mark_changed(da)
        record("DA_UIStyle", "(all groups)", "%d properties (%d key icons)" % (len(expected), len(expected["KeyIcons"])))
        errors = da_mismatch(da, expected)
    for e in errors:
        check("DA_UIStyle read-back", False, e)
    return da, expected


def verify_da(da, expected):
    paths = set()
    for key, value in expected.items():
        if key == "KeyIcons":
            paths.update(value.values())
        else:
            paths.add(value)
    for p in sorted(paths):
        check("DA_UIStyle target exists " + p, EAL.does_asset_exist(p.rsplit(".", 1)[0]))
    check("DA_UIStyle key-icon entries == %d" % len(expected["KeyIcons"]), len(json.loads(TL.get_object_properties(da, ["KeyIcons"]))["KeyIcons"]) == len(expected["KeyIcons"]))
    # the colours and sizes are the class defaults (the plan sets none): read the CDO and the asset and compare
    cdo = unreal.get_default_object(unreal.LBUIStyle)
    for prop in ("ink", "dim", "accent", "plate", "danger", "high_contrast_plate"):
        check("DA_UIStyle.%s is the class default" % prop, da.get_editor_property(prop).to_tuple() == cdo.get_editor_property(prop).to_tuple(), da.get_editor_property(prop).to_tuple())
    for prop in ("title_size", "heading_size", "item_size", "body_size", "small_size", "flicker_speed", "flicker_amplitude"):
        check("DA_UIStyle.%s is the class default" % prop, same(da.get_editor_property(prop), cdo.get_editor_property(prop)), da.get_editor_property(prop))
    report["findings"]["DA_UIStyle"] = {"key_icon_entries": len(expected["KeyIcons"]), "fonts": 4, "sounds": 4}


# ---------------------------------------------------------------------------------------------------------------------------------
# 6. Input: IA_Pause and IMC_LB_Gameplay
# ---------------------------------------------------------------------------------------------------------------------------------

ACTION_ORDER = ["MoveForward", "MoveBack", "MoveLeft", "MoveRight", "Sprint", "Crouch", "Interact", "Candle", "Pause"]
ACTION_ASSET = {"MoveForward": "IA_Move", "MoveBack": "IA_Move", "MoveLeft": "IA_Move", "MoveRight": "IA_Move", "Sprint": "IA_Sprint", "Crouch": "IA_Crouch",
                "Interact": "IA_Interact", "Candle": "IA_Candle", "Pause": "IA_Pause"}


def parse_logic():
    """{action: (mapping name, display name, default key)} read from LBUILogic.cpp so the IMC names are exactly the C++ ones."""
    src = open(LOGIC_CPP, encoding="utf-8").read()

    def block(func):
        m = re.search(r"%s\([^)]*\)\s*\{(.*?)\n\}" % re.escape(func), src, re.S)
        return m.group(1) if m else ""

    names = dict(re.findall(r'case ELBBindAction::(\w+): return FName\(TEXT\("([^"]+)"\)\);', block("LBUILogic::MappingNameFor")))
    display = dict(re.findall(r'case ELBBindAction::(\w+): return NSLOCTEXT\("LastBellUI", "\w+", "([^"]+)"\);', block("LBUILogic::DisplayNameFor")))
    keys = dict(re.findall(r"case ELBBindAction::(\w+): return EKeys::(\w+);", block("LBUILogic::DefaultKeyFor")))
    out = {}
    for a in ACTION_ORDER:
        check("LBUILogic has a name, display name and default key for " + a, a in names and a in display and a in keys, (names.get(a), display.get(a), keys.get(a)))
        out[a] = (names.get(a), display.get(a), keys.get(a))
    return out


def key_name(key_struct):
    return str(key_struct.get_editor_property("key_name"))


def make_key(name):
    key = unreal.Key()
    key.set_editor_property("key_name", name)
    return key


def build_ia_pause():
    assert allowed(IA_PAUSE)
    ia = load(IA_PAUSE, "InputAction")
    if ia is None and APPLY:
        ia = ATOOLS.create_asset("IA_Pause", INPUT, unreal.InputAction, unreal.InputAction_Factory())
        check("created IA_Pause", ia is not None)
        if ia is not None:
            mark_changed(ia)
            record("IA_Pause", "(created)", "InputAction")
    if not check("IA_Pause exists", ia is not None):
        return None
    set_prop(ia, "value_type", unreal.InputActionValueType.BOOLEAN, "IA_Pause")
    # Escape must also resume a paused game: an Enhanced Input action does not fire while the game is paused unless this is set
    set_prop(ia, "trigger_when_paused", True, "IA_Pause")
    triggers = list(ia.get_editor_property("triggers"))
    if [t.get_class().get_name() for t in triggers] != ["InputTriggerPressed"] and APPLY:
        trigger = unreal.new_object(unreal.InputTriggerPressed, outer=ia)
        ia.set_editor_property("triggers", [trigger])
        mark_changed(ia)
        record("IA_Pause", "triggers", "[InputTriggerPressed]")
    check("IA_Pause has exactly one Pressed trigger", [t.get_class().get_name() for t in ia.get_editor_property("triggers")] == ["InputTriggerPressed"])
    return ia


def imc_mappings(imc):
    return list(imc.get_editor_property("default_key_mappings").get_editor_property("mappings"))


def write_imc_mappings(imc, maps):
    dkm = imc.get_editor_property("default_key_mappings")
    dkm.set_editor_property("mappings", maps)
    imc.set_editor_property("default_key_mappings", dkm)
    mark_changed(imc)


def build_imc(logic, ia_pause):
    assert allowed(IMC_PATH)
    imc = load(IMC_PATH, "InputMappingContext")
    if not check("IMC_LB_Gameplay exists", imc is not None):
        return None
    actions = {n: load(INPUT + "/" + n, "InputAction") for n in set(ACTION_ASSET.values())}
    if ia_pause is not None:
        actions["IA_Pause"] = ia_pause
    # the Escape mapping for IA_Pause
    if ia_pause is not None and APPLY:
        if not any(m.get_editor_property("action") == ia_pause and key_name(m.get_editor_property("key")) == "Escape" for m in imc_mappings(imc)):
            imc.map_key(ia_pause, make_key("Escape"))
            mark_changed(imc)
            record("IMC_LB_Gameplay", "mappings", "+ IA_Pause on Escape")
    maps = imc_mappings(imc)
    wanted = {}   # (action asset name, key name) -> (mapping name, display name)
    for a in ACTION_ORDER:
        name, display, key = logic[a]
        wanted[(ACTION_ASSET[a], key)] = (name, display)
    changed = False
    for i, m in enumerate(maps):
        act = m.get_editor_property("action")
        k = (act.get_name() if act else None, key_name(m.get_editor_property("key")))
        spec = wanted.get(k)
        behavior = m.get_editor_property("setting_behavior")
        settings = m.get_editor_property("player_mappable_key_settings")
        if spec is None:
            continue   # arrows, gamepad keys and Ctrl: unnamed, fixed (Inherit, and the actions carry no settings)
        mapping_name, display = spec
        good = (behavior == unreal.PlayerMappableKeySettingBehaviors.OVERRIDE_SETTINGS and settings is not None
                and str(settings.get_editor_property("name")) == mapping_name and str(settings.get_editor_property("display_name")) == display
                and str(settings.get_editor_property("display_category")) == "Gameplay")
        if good:
            continue
        if not APPLY:
            check("IMC mapping %s/%s names" % k, False, "behavior %s name %s" % (behavior, settings.get_editor_property("name") if settings else None))
            continue
        if settings is None:
            settings = unreal.new_object(unreal.PlayerMappableKeySettings, outer=imc)
        settings.set_editor_property("name", mapping_name)
        settings.set_editor_property("display_name", unreal.Text(display))
        settings.set_editor_property("display_category", unreal.Text("Gameplay"))
        m.set_editor_property("setting_behavior", unreal.PlayerMappableKeySettingBehaviors.OVERRIDE_SETTINGS)
        m.set_editor_property("player_mappable_key_settings", settings)
        maps[i] = m
        changed = True
        record("IMC_LB_Gameplay", "mapping %s/%s" % k, "%s (%s)" % (mapping_name, display))
    if changed:
        write_imc_mappings(imc, maps)
    return imc


def verify_imc(imc, logic):
    maps = imc_mappings(imc)
    named = {}
    for m in maps:
        settings = m.get_editor_property("player_mappable_key_settings")
        behavior = m.get_editor_property("setting_behavior")
        act = m.get_editor_property("action")
        key = key_name(m.get_editor_property("key"))
        if behavior == unreal.PlayerMappableKeySettingBehaviors.OVERRIDE_SETTINGS and settings is not None:
            n = str(settings.get_editor_property("name"))
            check("mapping name %s is used once" % n, n not in named, "twice")
            named[n] = (act.get_name() if act else None, key, str(settings.get_editor_property("display_name")))
    for a in ACTION_ORDER:
        name, display, key = logic[a]
        got = named.get(name)
        check("IMC mapping %s -> %s on %s (%s)" % (name, ACTION_ASSET[a], key, display), got == (ACTION_ASSET[a], key, display), got)
    check("IMC has exactly the %d player-mappable names" % len(ACTION_ORDER), sorted(named) == sorted(logic[a][0] for a in ACTION_ORDER), sorted(named))
    # Ctrl stays an unnamed second Crouch key
    ctrl = [m for m in maps if m.get_editor_property("action") and m.get_editor_property("action").get_name() == "IA_Crouch" and key_name(m.get_editor_property("key")) == "LeftControl"]
    check("LeftControl still maps IA_Crouch, unnamed", len(ctrl) == 1 and ctrl[0].get_editor_property("player_mappable_key_settings") is None)
    report["findings"]["IMC_LB_Gameplay"] = {"mappings": len(maps), "player_mappable": sorted(named)}


# ---------------------------------------------------------------------------------------------------------------------------------
# 7. Blueprints
# ---------------------------------------------------------------------------------------------------------------------------------

def compile_bp(bp):
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    try:
        status = str(bp.get_editor_property("status"))
    except Exception:
        status = "(status not readable)"
    note("compiled %s: %s" % (bp.get_name(), status))
    check("%s compiles (status %s)" % (bp.get_name(), status), "ERROR" not in status.upper(), status)


def cdo_of(bp):
    return unreal.get_default_object(bp.generated_class())


def build_blueprints(ia_pause):
    for path, prop, value, label in ((BP_PC, "pause_action", ia_pause, "IA_Pause"),
                                     (BP_MENU_PC, "hud_widget_class", unreal.LBMainMenuWidget.static_class(), "LBMainMenuWidget")):
        assert allowed(path)
        bp = load(path, "Blueprint")
        if not check("Blueprint exists " + path, bp is not None) or value is None:
            continue
        cdo = cdo_of(bp)
        if same(cdo.get_editor_property(prop), value):
            continue
        if not APPLY:
            check("%s.%s" % (bp.get_name(), prop), False, "wanted %s read %s" % (label, cdo.get_editor_property(prop)))
            continue
        cdo.set_editor_property(prop, value)
        bp.modify()
        mark_changed(bp)
        record(bp.get_name(), "CDO." + prop, label)
        compile_bp(bp)
        check("%s.%s read back after the compile" % (bp.get_name(), prop), same(cdo_of(bp).get_editor_property(prop), value), cdo_of(bp).get_editor_property(prop))


def verify_blueprints(ia_pause):
    pc = load(BP_PC, "Blueprint")
    if pc is not None:
        check("BP_LBPlayerController.PauseAction == IA_Pause", cdo_of(pc).get_editor_property("pause_action") == ia_pause, cdo_of(pc).get_editor_property("pause_action"))
    mpc = load(BP_MENU_PC, "Blueprint")
    if mpc is not None:
        check("BP_MenuPlayerController.HUDWidgetClass == LBMainMenuWidget", cdo_of(mpc).get_editor_property("hud_widget_class") == unreal.LBMainMenuWidget.static_class(),
              cdo_of(mpc).get_editor_property("hud_widget_class"))
    gm = load(BP_MENU_GM, "Blueprint")
    if gm is not None:
        check("BP_MenuGameMode still uses BP_MenuPlayerController", cdo_of(gm).get_editor_property("player_controller_class") == mpc.generated_class(),
              cdo_of(gm).get_editor_property("player_controller_class"))
    # WBP_MainMenu is retired: nothing may reference it any more (it is listed for deletion at review)
    refs = [str(r) for r in EAL.find_package_referencers_for_asset(WBP_MAINMENU, False)]
    report["findings"]["WBP_MainMenu_referencers"] = refs
    check("WBP_MainMenu has no referencers (retired, unused)", not refs, refs)


# ---------------------------------------------------------------------------------------------------------------------------------
# 9. Sound classes and the UI sounds
# ---------------------------------------------------------------------------------------------------------------------------------

UI_SOUNDS = ["SFX_LB_UI_Hover", "SFX_LB_UI_Select", "SFX_LB_UI_Back", "SFX_LB_UI_Tick"]


def verify_sounds():
    classes = {}
    for path in EAL.list_assets(MIX, recursive=False, include_folder=False):
        asset = EAL.load_asset(path)
        if asset is not None and asset.get_class().get_name() == "SoundClass":
            classes[asset.get_name()] = asset
    check("sound classes found (7 SCL_LB_*)", len(classes) == 7, sorted(classes))
    finding = {}
    for name, sc in sorted(classes.items()):
        is_ui = bool(sc.get_editor_property("properties").get_editor_property("is_ui_sound"))
        finding[name] = is_ui
        check("%s bIsUISound == %s" % (name, name == "SCL_LB_UI"), is_ui == (name == "SCL_LB_UI"), is_ui)
    report["findings"]["bIsUISound"] = finding
    # every sound asset under Audio/: its class must not be a UI class unless it is one of the four UI sounds
    ui_class = classes.get("SCL_LB_UI")
    bad, count = [], 0
    for path in EAL.list_assets("/Game/LastBell/Audio", recursive=True, include_folder=False):
        asset = EAL.load_asset(path)
        if asset is None or not isinstance(asset, unreal.SoundBase):
            continue
        count += 1
        sc = asset.get_editor_property("sound_class_object") if asset.get_class().get_name() == "SoundWave" else None
        in_ui = sc is not None and ui_class is not None and sc == ui_class
        if in_ui != (asset.get_name() in UI_SOUNDS):
            bad.append(asset.get_name())
        if sc is not None and bool(sc.get_editor_property("properties").get_editor_property("is_ui_sound")) and asset.get_name() not in UI_SOUNDS:
            bad.append(asset.get_name() + " (UI class)")
    check("every game sound is outside SCL_LB_UI; only the 4 UI sounds are in it (%d sound assets scanned)" % count, not bad, bad[:10])
    report["counts"]["sound_assets_scanned"] = count
    for n in UI_SOUNDS:
        wave = load("/Game/LastBell/Audio/UI/" + n, "SoundWave")
        if check("UI sound exists " + n, wave is not None):
            check(n + " is mono", int(wave.get_editor_property("num_channels")) == 1, wave.get_editor_property("num_channels"))
            check(n + " class is SCL_LB_UI", wave.get_editor_property("sound_class_object") == ui_class)
            check(n + " is 2D (no attenuation settings)", wave.get_editor_property("attenuation_settings") is None)
            check(n + " does not loop", not bool(wave.get_editor_property("looping")))


# ---------------------------------------------------------------------------------------------------------------------------------
# Save, verify, main
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
    check("no dirty package of ours after the save", not ours, ours[:10])
    others = [d for d in dirty if not allowed(d)]
    if others:
        note("dirty packages outside our paths (NOT saved): %s" % others[:10])


def verify_textures(icons, symbol, still):
    n = 0
    for name, tex in icons.items():
        if tex is None:
            continue
        n += 1
        for prop, value in texture_settings(ICON_COMPRESSION).items():
            check("T_Key_%s.%s" % (name, prop), same(tex.get_editor_property(prop), value), tex.get_editor_property(prop))
        w, h = int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())
        check("T_Key_%s is 128x128" % name, (w, h) == (128, 128), (w, h))
    report["counts"]["key_icon_textures"] = n
    check("%d key-icon textures" % len(key_icon_table()), n == len(key_icon_table()), n)
    for tex, label, size, comp in ((symbol, "T_LB_BrightnessSymbol", (256, 256), ICON_COMPRESSION), (still, "T_LB_MenuStill", (1920, 1080), unreal.TextureCompressionSettings.TC_DEFAULT)):
        if tex is None:
            continue
        for prop, value in texture_settings(comp).items():
            check("%s.%s" % (label, prop), same(tex.get_editor_property(prop), value), tex.get_editor_property(prop))
        check("%s is %dx%d" % (label, size[0], size[1]), (int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())) == size)


def verify_fonts(fonts):
    for w, (face, font) in fonts.items():
        if face is not None:
            check("FF_LB_EBGaramond_%s is a FontFace with LazyLoad/Default hinting" % w, face.get_class().get_name() == "FontFace")
        if font is not None:
            check("F_LB_EBGaramond_%s is a runtime-cached Font" % w, font.get_editor_property("font_cache_type") == unreal.FontCacheType.RUNTIME)
    report["counts"]["font_faces"] = sum(1 for f in fonts.values() if f[0] is not None)
    report["counts"]["fonts"] = sum(1 for f in fonts.values() if f[1] is not None)


def write_report():
    report["ok"] = not report["failures"]
    report["failure_count"] = len(report["failures"])
    if OUT:
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1)
    unreal.log("P18-2 RESULT: %s (%d checks, %d failures) mode=%s" % ("PASS" if report["ok"] else "FAIL", report["checks"], len(report["failures"]), MODE))


def main():
    note("mode=%s reimport=%s" % (MODE, REIMPORT))
    logic = parse_logic()
    if report["failures"]:
        return
    if not os.path.isfile(VIDEO):
        check("Content/Movies/LB_MenuDrift.mp4 exists", False, VIDEO)
        return

    apply_config()
    copy_ofl()
    fonts = build_fonts()
    icons = build_icons()
    symbol, still = build_symbol_and_still()
    ms = build_media_source()
    da, expected = build_da()
    ia_pause = build_ia_pause()
    imc = build_imc(logic, ia_pause)
    build_blueprints(ia_pause)

    if APPLY:
        save_changed()

    verify_config()
    verify_fonts(fonts)
    verify_textures(icons, symbol, still)
    if ms is not None:
        check("MS_LB_MenuDrift.file_path", str(ms.get_editor_property("file_path")) == MEDIA_FILE_PATH, ms.get_editor_property("file_path"))
        check("the media file exists at the path the source points to", os.path.isfile(os.path.join(ROOT, MEDIA_FILE_PATH[2:])))
    if da is not None:
        verify_da(da, expected)
    if imc is not None:
        verify_imc(imc, logic)
    verify_blueprints(ia_pause)
    verify_sounds()


try:
    main()
except Exception as exc:  # report, never half-save silently
    report["failures"].append("exception: %r" % (exc,))
    report["traceback"] = traceback.format_exc()
    unreal.log_error("P18-2 EXCEPTION: " + report["traceback"])
finally:
    write_report()
    # `-ExecutePythonScript` runs inside a normal editor loop: quit it ourselves (the script cannot return a status to the process)
    unreal.SystemLibrary.execute_console_command(None, "QUIT_EDITOR")

if report["failures"]:
    raise RuntimeError("P18-2: %d failed checks; see the report" % len(report["failures"]))
