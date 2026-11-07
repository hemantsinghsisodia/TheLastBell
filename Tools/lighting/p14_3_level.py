"""P14-3: the storm's level work in L_Monastery (Docs/plans/P14_LIGHTING_STORM.md section 7).

Run with the editor open on L_Monastery, PIE off:
    python -I Tools/lighting/p14_3_level.py --apply [--only tags,zones,pp,groups,decals,apparitions]
    python -I Tools/lighting/p14_3_level.py --check [--only ...] [--start 2992]

--apply is idempotent: every actor is found by its EXACT label (find_actors matches substrings, so the result is filtered) and
updated, or created when missing. Nothing is ever saved by this script: the map is saved once, by hand, after the census.
--check only reads and prints PASS / FAIL per item (exit code 1 when any FAIL).

If the editor crashes or a call hangs for more than 180 s the script stops ("STOP", exit code 3). Do not save and do not retry
blindly: restart the editor, then --apply again (it finishes whatever is missing).
Work order in --apply: tags, zones, pp, groups, decals, apparitions (WPO distance is Tools/lighting/p14_wpo_distance.py).
"""
import argparse
import copy
import json
import math
import os
import socket
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Tools", "mcp"))
import ue as ue_mod  # noqa: E402
from ue import UE  # noqa: E402

S = "editor_toolset.toolsets.scene.SceneTools"
A = "editor_toolset.toolsets.actor.ActorTools"
O = "editor_toolset.toolsets.object.ObjectTools"
AS = "editor_toolset.toolsets.asset.AssetTools"
E = "EditorToolset.EditorAppToolset"
MAP_PKG = "/Game/LastBell/Maps/L_Monastery"
MAP_OBJ = MAP_PKG + ".L_Monastery"
FOLDER = "Lighting/Storm"
CENSUS_START = 2992        # F0 count; the target is start + 23
NEW_ACTORS = 7 + 9 + 2 + 5
TIMEOUT_S = 180


# ---------------------------------------------------------------------------------------------- editor client
class EditorStop(Exception):
    """The editor hung, crashed or dropped the connection: stop, do not save."""


class UE180(UE):
    """UE with a 180 s socket timeout (the stock helper waits 600 s)."""

    def _post(self, body):
        h = dict(ue_mod.HEADERS)
        if self.sid:
            h["Mcp-Session-Id"] = self.sid
        req = urllib.request.Request(self.url, json.dumps(body).encode(), h)
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            self.sid = self.sid or r.headers.get("Mcp-Session-Id")
            raw = r.read().decode("utf-8", "replace").strip()
        if not raw:
            return None
        if not raw.startswith("{"):
            raw = next(line[5:] for line in raw.splitlines() if line.startswith("data:"))
        return json.loads(raw)


def J(x):
    return json.loads(x) if isinstance(x, str) else x


def R(x):
    """refPath of a reference value (dict or string), or None."""
    if isinstance(x, dict):
        x = x.get("refPath")
    if not x or x in ("None", "null"):
        return None
    return x


def v3(d):
    return [float(d[k]) for k in "xyz"]


def vec(v):
    return {"x": v[0], "y": v[1], "z": v[2]}


def xf(loc, rot=(0, 0, 0), sc=(1, 1, 1)):
    return {"location": vec(loc), "rotation": {"pitch": rot[0], "yaw": rot[1], "roll": rot[2]}, "scale": vec(sc)}


def near(a, b, tol):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def rot_quat(p, y, r):
    """UE FRotator (degrees) to FQuat (x, y, z, w)."""
    sp, cp = math.sin(math.radians(p) / 2), math.cos(math.radians(p) / 2)
    sy, cy = math.sin(math.radians(y) / 2), math.cos(math.radians(y) / 2)
    sr, cr = math.sin(math.radians(r) / 2), math.cos(math.radians(r) / 2)
    return (cr * sp * sy - sr * cp * cy, -cr * sp * cy - sr * cp * sy, cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy)


def same_rot(a, b, tol=1e-5):
    qa, qb = rot_quat(*a), rot_quat(*b)
    return abs(sum(x * y for x, y in zip(qa, qb))) > 1 - tol


class Ed:
    def __init__(self):
        try:
            self.ue = UE180()
        except Exception as e:  # noqa: BLE001
            raise EditorStop("cannot connect to the editor: %s" % e)
        self.calls = 0
        self._labels = {}

    def call(self, ts, tool, args=None):
        self.calls += 1
        readonly = tool.startswith(("get_", "find_", "is_", "IsPIE"))
        try:
            return self.ue.call(ts, tool, args or {})
        except ConnectionResetError as e:
            # Seen in P14-3 on the large find_actors reply (3000 refs) with the editor alive and answering the next call: a read-only
            # call is repeated (up to 3 times, each on a new session); a mutation is never repeated.
            last = e
            if readonly:
                for attempt in range(3):
                    print("NOTE  connection reset on %s.%s; retry %d/3 of this read-only call on a new session" % (ts.rsplit(".", 1)[-1], tool, attempt + 1), flush=True)
                    time.sleep(2)
                    try:
                        self.ue = UE180()
                        return self.ue.call(ts, tool, args or {})
                    except ConnectionResetError as e2:
                        last = e2
                    except (TimeoutError, socket.timeout, urllib.error.URLError, ConnectionError, OSError) as e3:
                        last = e3
                        break
            raise EditorStop("%s.%s: %s: %s" % (ts.rsplit(".", 1)[-1], tool, type(last).__name__, last))
        except (TimeoutError, socket.timeout, urllib.error.URLError, ConnectionError, OSError) as e:
            raise EditorStop("%s.%s: %s: %s" % (ts.rsplit(".", 1)[-1], tool, type(e).__name__, e))

    # ---- generic
    def props(self, ref, names):
        return J(self.call(O, "get_properties", {"instance": {"refPath": R(ref)}, "properties": list(names)}))

    def setp(self, ref, values):
        return self.call(O, "set_properties", {"instance": {"refPath": R(ref)}, "values": json.dumps(values)})

    def label(self, ref):
        ref = R(ref)
        if ref not in self._labels:
            self._labels[ref] = self.call(A, "get_label", {"actor": {"refPath": ref}})
        return self._labels[ref]

    def find_all(self, name="", tag=""):
        return [R(x) for x in self.call(S, "find_actors", {"name": name, "tag": tag, "collision_channels": []}) or []]

    def find(self, label):
        """Exact-label matches (find_actors is a case-insensitive substring match)."""
        return [r for r in self.find_all(name=label) if self.label(r) == label]

    def find_one(self, label, must=False):
        hits = self.find(label)
        if len(hits) > 1:
            raise RuntimeError("label %r exists %d times" % (label, len(hits)))
        if must and not hits:
            raise RuntimeError("label %r not found" % label)
        return hits[0] if hits else None

    def xform(self, ref):
        t = J(self.call(A, "get_actor_transform", {"actor": {"refPath": R(ref)}, "worldspace": True}))
        return v3(t["location"]), [float(t["rotation"][k]) for k in ("pitch", "yaw", "roll")], v3(t["scale"])

    def set_xform(self, ref, loc, rot, sc):
        self.call(A, "set_actor_transform", {"actor": {"refPath": R(ref)}, "xform": xf(loc, rot, sc), "worldspace": True})

    def bounds(self, ref):
        b = J(self.call(A, "get_actor_bounds", {"actor": {"refPath": R(ref)}}))
        return v3(b["min"]), v3(b["max"]), b.get("isValid", True)

    def spawn(self, cls, label, loc, rot=(0, 0, 0), sc=(1, 1, 1), folder=FOLDER):
        a = self.call(S, "add_to_scene_from_class", {"actor_type": {"refPath": cls}, "name": label, "xform": xf(loc, rot, sc)})
        ref = R(a)
        if not ref:
            raise RuntimeError("spawn of %s (%s) returned %r" % (label, cls, a))
        self.call(A, "set_label", {"actor": {"refPath": ref}, "label": label})
        self._labels[ref] = label
        if folder:
            self.call(S, "set_actor_folder", {"actor": {"refPath": ref}, "folder_path": folder})
        return ref

    def get_or_create(self, cls, label, loc, rot=(0, 0, 0), sc=(1, 1, 1), folder=FOLDER):
        ref = self.find_one(label)
        if ref:
            return ref, False
        return self.spawn(cls, label, loc, rot, sc, folder), True

    def set_vec(self, ref, prop, target, tol=1e-3):
        """Set a vector property one axis per call (an instance write with several changed axes can drop all but one)."""
        for _ in range(3):
            cur = v3(self.props(ref, [prop])[prop])
            if near(cur, target, tol):
                return True
            for i, ax in enumerate("xyz"):
                if abs(cur[i] - target[i]) > tol:
                    v = list(cur)
                    v[i] = target[i]
                    self.setp(ref, {prop: vec(v)})
                    cur = v
        return near(v3(self.props(ref, [prop])[prop]), target, tol)

    def is_dirty(self, pkg):
        return bool(self.call(AS, "is_dirty", {"asset_path": pkg}))


# ---------------------------------------------------------------------------------------------- the plan's tables
TAGS = {
    "LB_StormMoon": ["DirectionalLight"],
    "LB_StormMoonSpot": ["Light_Chapel_Moon_S1", "Light_Chapel_Moon_S2", "Light_Chapel_Moon_S3", "Light_Chapel_Moon_Roof",
                         "L_Crypt_Moon_G1", "L_Crypt_Moon_G2", "L_Crypt_Moon_G3",
                         "L_Tw_MoonSlit_F03", "L_Tw_MoonSlit_F07", "L_Tw_MoonSlit_F08"],
    "LB_StormFill": ["L_Tw_BellFill"],
    "LB_StormSky": ["SkyLight"],
}
NO_STORM_TAG = ["Moon_Fill"]

# label: (X, Y, Z min/max boxes, exposure, priority) -- plan section 5.1
ZONES = [
    ("SZN_Chapel", (6000, 9100), (-1550, 860), (-40, 2400), 0.35, 1),
    ("SZN_Crypt", (6300, 12000), (-2950, 520), (-1200, -45), 0.0, 2),
    ("SZN_Passage", (6040, 9460), (900, 2600), (-40, 1200), 0.3, 1),
    ("SZN_Cloister", (9460, 12040), (500, 3040), (-40, 1500), 0.6, 1),
    ("SZN_Garth", (10245, 11460), (1345, 2260), (-40, 1500), 1.0, 2),
    ("SZN_TowerShaft", (11990, 13010), (1490, 2510), (-40, 2650), 0.25, 3),
    ("SZN_Belfry", (11990, 13010), (1490, 2510), (2650, 4800), 0.85, 3),
]
ZONE_CLASS = "/Script/LastBell.LBStormZone"
GROUP_CLASS = "/Script/LastBell.LBStateLightGroup"

# Post-process (section 7.3). Boxes in cm.
PP_CLOISTER = {"label": "PP_Cloister", "box": ((6040, 12040), (900, 3200), (-40, 4200)), "ev": 0.65}
# P14-5 (owner's P14-4 choices): each volume has its own EV (PP_Chapel 1.6, PP_Tower stays 0.65); the shared PP_EV is gone.
PP_NEW = [
    {"label": "PP_Chapel", "box": ((6000, 9100), (-1550, 860), (-40, 2400)), "priority": 2.0, "blend": 200.0, "ev": 1.6},
    {"label": "PP_Tower", "box": ((11990, 13010), (1490, 2510), (-40, 5000)), "priority": 3.0, "blend": 200.0, "ev": 0.65},
]
# P14-5 (owner's P14-4 choices): the shadow saturation (grade) is no longer a per-area override on PP_Cloister, PP_Outdoor_Night,
# PP_Chapel and PP_Tower; the global grade B lives on PostProcess_Exposure (Tools/lighting/p14_5_apply.py). Two EV overrides only.
PP_OVERRIDES = {"AutoExposureMinBrightness", "AutoExposureMaxBrightness"}
PP_EV = 0.65
PP_SAT = (0.65, 0.65, 0.65, 1.0)   # the STORED colorSaturationShadows value, left in place (only bOverride_ColorSaturationShadows is false now)
# P14-5: grade B on the unbound global volume PostProcess_Exposure (override set only; the values are checked by p14_5_apply.py --check)
PP_EXPOSURE_OVERRIDES = PP_OVERRIDES | {"ColorSaturation", "ColorContrast", "ColorGammaShadows", "ColorGainHighlights",
                                         "FilmGrainIntensity", "VignetteIntensity"}
# read in this session before any change (F0 agrees)
PP_BEFORE = {
    "PP_Cloister": {"priority": 1.0, "blend": 300.0, "unbound": False, "overrides": PP_OVERRIDES, "ev": PP_EV, "sat": PP_SAT},
    "PP_Crypt": {"priority": 1.0, "blend": 300.0, "unbound": False,
                 "overrides": {"BloomIntensity", "AutoExposureMethod", "AutoExposureMinBrightness", "AutoExposureMaxBrightness"},
                 "ev": 0.2, "sat": (1, 1, 1, 1), "box": ((6150, 11900), (-3300, 800), (-1150, -40)), "xform": ((9025, -1250, -595), (28.75, 20.5, 5.55))},
    "PP_Outdoor_Night": {"priority": 1.0, "blend": 500.0, "unbound": False, "overrides": PP_OVERRIDES, "ev": 1.15, "sat": PP_SAT,
                         "box": ((-3315, 5500), (-2700, 2700), (-100, 3900)), "xform": ((1092.5, 0, 1900), (44.075, 27, 20))},
    "PostProcess_Exposure": {"priority": 0.0, "blend": 100.0, "unbound": True,
                             "overrides": PP_EXPOSURE_OVERRIDES, "ev": 3.0, "sat": (1, 1, 1, 1),  # P14-5: grade B overrides added
                             "box": ((5100, 5300), (-100, 100), (400, 600)), "xform": ((5200, 0, 500), (1, 1, 1))},
}

# Groups (section 8, 8.1). rule = (tag, mode, scale, amount, speed); Off rules use the defaults.
GROUPS = [
    {"label": "SLG_Chapel_Altar", "lights": ["Light_Chapel_Altar_N", "Light_Chapel_Altar_S"], "emissive": [], "glow": [],
     "rules": [("State.Ritual.1", "Flicker", 0.25, 0.45, 7.0)]},
    {"label": "SLG_Chapel_Dais", "lights": ["Light_Chapel_Statue", "Light_Chapel_DaisFill"], "emissive": [], "glow": [],
     "rules": [("State.Ritual.1", "Off")]},
    {"label": "SLG_Crypt_Torches", "lights": ["L_Crypt_Torch_T1", "L_Crypt_Torch_T2", "L_Crypt_Torch_T3"], "emissive": [], "glow": [],
     "rules": [("State.Ritual.2", "Flicker", 0.6, 0.45, 9.0)]},
    {"label": "SLG_Crypt_Niches",
     "lights": ["L_Crypt_Candle_Niche_E_WC", "L_Crypt_Candle_Niche_N_SC", "L_Crypt_Candle_Niche_S_FP", "L_Crypt_Candle_Niche_E_CC", "L_Crypt_Candle_Niche_S_NC"],
     "emissive": ["CD_Candles_Niche_E_WC_Flame", "CD_Candles_Niche_N_SC_Flame", "CD_Candles_Niche_S_FP_Flame", "CD_Candles_Niche_E_CC_Flame", "CD_Candles_Niche_S_NC_Flame"],
     "glow": [], "rules": [("State.Ritual.2", "Off")]},
    {"label": "SLG_Cloister_Bells", "lights": ["L_Cl_Bells"], "emissive": [], "glow": ["CLA_Lantern_Bells"],
     "rules": [("State.Event.CloisterEntered", "Flicker", 0.85, 0.3, 5.0)]},
    {"label": "SLG_Cloister_West", "lights": ["L_Cl_West"], "emissive": [], "glow": ["CLA_Lantern_West"],
     "rules": [("State.Event.CloisterEntered", "Flicker", 0.85, 0.3, 5.0), ("State.Ritual.3", "Off")]},
    {"label": "SLG_Cloister_Entry", "lights": ["L_Cl_Entry"], "emissive": [], "glow": ["SHA_Lantern_Entry"],
     "rules": [("State.Ritual.3", "Off")]},
    {"label": "SLG_Tower_Landings", "lights": ["L_Tw_Land4", "L_Tw_Land7", "L_Tw_Land10"], "emissive": [],
     "glow": ["TWA_Lantern_Land4", "TWA_Lantern_Land7", "TWA_Lantern_Land10"],
     "rules": [("State.Ritual.3", "Flicker", 0.9, 0.2, 4.0)]},
    {"label": "SLG_Tower_Bell", "lights": ["L_Tw_Bell"], "emissive": [], "glow": ["TWA_Lantern_Bell"],
     "rules": [("State.Event.TowerTop", "Flicker", 0.8, 0.5, 8.0)]},
]
RULE_DEFAULTS = (1.0, 0.4, 6.0)
FADE_SECONDS = 1.5
INST = "/Game/LastBell/Materials/Instances/"
# label: (location, rotation, DecalSize half-extent (depth, vertical, horizontal), MI) -- section 5.6(d)
DECALS = [
    ("RV_Gate_Sigil", (300, 500, 260), (0, 180, 90), (10, 110, 110), "MI_Reveal_Sigil"),
    ("RV_WellHouse_Tally", (1350, -1775, 115), (0, -90, 90), (10, 40, 60), "MI_Reveal_Tally"),   # P14-5 (owner's P14-4 choices): Z 140 -> 115
    # P14-5 (owner's P14-4 choices): (8265, -255) -> (8150, -91), 200 cm off the S2 pool stripe's centreline toward the aisle
    ("RV_Chapel_Circle", (8150, -91, 0.5), (-90, 0, 0), (10, 90, 90), "MI_Reveal_Circle"),
    ("RV_Garth_Drag", (10750, 3000, 270), (0, 90, 90), (20, 30, 110), "MI_Reveal_Drag"),
    ("RV_Belfry_Tally", (12200, 1540, 2850), (0, -90, 90), (15, 50, 50), "MI_Reveal_Tally"),
]
APPARITIONS = [("Apparition_Courtyard", "BP_WardenApparition_C_0"), ("Apparition_Chapel", "BP_WardenApparition_C_1")]
NEVER_SAVE = ["/Game/LastBell/Materials/Master/M_LB_Surface",
              "/Game/LastBell/Blueprints/Puzzles/BP_SmallBell", "/Game/LastBell/Blueprints/Puzzles/BP_SequencePuzzle",
              "/Game/LastBell/Blueprints/Puzzles/BP_Inscription", "/Game/LastBell/Blueprints/Interactables/BP_RitualMechanism",
              "/Game/LastBell/Blueprints/Interactables/BP_Door_Base", "/Game/LastBell/Blueprints/Interactables/BP_TagInteractable",
              "/Game/LastBell/Blueprints/Interactables/BP_TagTrigger", "/Game/LastBell/Blueprints/BP_EndingTrigger",
              "/Game/LastBell/Blueprints/Interactables/BP_Inspectable_Note", "/Game/LastBell/Blueprints/Interactables/BP_Door_Base_Dungeon",
              "/Game/LastBell/Blueprints/Interactables/BP_RitualMechanism_CryptWinch", "/Game/LastBell/Blueprints/Interactables/BP_WardenApparition"]

results = []


def rec(ok, msg):
    results.append((bool(ok), msg))
    print(("PASS  " if ok else "FAIL  ") + msg, flush=True)
    return bool(ok)


def info(msg):
    print("INFO  " + msg, flush=True)


# ---------------------------------------------------------------------------------------------- 1. tags
def apply_tags(ed):
    for tag, labels in TAGS.items():
        for lab in labels:
            ref = ed.find_one(lab, must=True)
            cur = list(ed.props(ref, ["tags"]).get("tags") or [])
            if tag in cur:
                info("%s already has %s (tags %s)" % (lab, tag, cur))
                continue
            new = cur + [tag]
            ed.setp(ref, {"tags": new})
            got = list(ed.props(ref, ["tags"]).get("tags") or [])
            info("%s tags %s -> %s" % (lab, cur, got))


def check_tags(ed):
    for tag, labels in TAGS.items():
        got = sorted(ed.label(r) for r in ed.find_all(tag=tag))
        rec(got == sorted(labels), "tag %s on %d actors %s (expected %d)" % (tag, len(got), got if len(got) <= 3 else "[...]", len(labels)))
    for lab in NO_STORM_TAG:
        ref = ed.find_one(lab, must=True)
        tags = list(ed.props(ref, ["tags"]).get("tags") or [])
        rec(not any(t in TAGS for t in tags), "%s carries no storm tag (tags %s)" % (lab, tags))
    ref = ed.find_one("DirectionalLight", must=True)
    rec(ref.endswith("DirectionalLight_1"), "label DirectionalLight is %s" % ref.rsplit(".", 1)[-1])


# ---------------------------------------------------------------------------------------------- 2. zones
def zone_target(z):
    _, xr, yr, zr, ex, pr = z
    centre = [(xr[0] + xr[1]) / 2.0, (yr[0] + yr[1]) / 2.0, (zr[0] + zr[1]) / 2.0]
    half = [(xr[1] - xr[0]) / 2.0, (yr[1] - yr[0]) / 2.0, (zr[1] - zr[0]) / 2.0]
    return centre, half


def apply_zones(ed):
    for z in ZONES:
        label = z[0]
        centre, half = zone_target(z)
        ref, created = ed.get_or_create(ZONE_CLASS, label, centre)
        ed.set_xform(ref, centre, (0, 0, 0), (1, 1, 1))
        ed.setp(ref, {"exposure": z[4], "priority": z[5]})
        ok = ed.set_vec(ref + ".Box", "boxExtent", half)
        info("%s %s at %s extent %s%s" % (label, "created" if created else "updated", centre, half, "" if ok else "  (EXTENT READ-BACK MISMATCH)"))


def check_zones(ed):
    for z in ZONES:
        label = z[0]
        centre, half = zone_target(z)
        ref = ed.find_one(label)
        if not ref:
            rec(False, "%s exists" % label)
            continue
        loc, rot, sc = ed.xform(ref)
        p = ed.props(ref, ["exposure", "priority"])
        ext = v3(ed.props(ref + ".Box", ["boxExtent"])["boxExtent"])
        lo = [loc[i] - ext[i] * sc[i] for i in range(3)]
        hi = [loc[i] + ext[i] * sc[i] for i in range(3)]
        want_lo = [centre[i] - half[i] for i in range(3)]
        want_hi = [centre[i] + half[i] for i in range(3)]
        cls = ed.call(O, "get_class", {"instance": {"refPath": ref}})
        okb = near(lo, want_lo, 1.0) and near(hi, want_hi, 1.0)
        rec(okb and near(rot, (0, 0, 0), 1e-4) and near(sc, (1, 1, 1), 1e-6) and abs(p["exposure"] - z[4]) < 1e-5 and int(p["priority"]) == z[5]
            and "LBStormZone" in json.dumps(cls),
            "%s world box %s..%s (want %s..%s) rot %s scale %s exposure %s priority %s" % (
                label, [round(v, 2) for v in lo], [round(v, 2) for v in hi], want_lo, want_hi, [round(v, 3) for v in rot], sc, p["exposure"], p["priority"]))
        try:
            b = ed.bounds(ref)
            info("%s get_actor_bounds %s..%s valid=%s" % (label, [round(v, 1) for v in b[0]], [round(v, 1) for v in b[1]], b[2]))
        except RuntimeError as e:
            info("%s get_actor_bounds failed: %s" % (label, str(e)[:100]))


# ---------------------------------------------------------------------------------------------- 3. post-process
def pp_state(ed, ref):
    p = ed.props(ref, ["priority", "blendRadius", "blendWeight", "bUnbound", "bEnabled", "settings"])
    st = p.pop("settings")
    on = sorted(k[len("bOverride_"):] for k, v in st.items() if k.startswith("bOverride_") and v)
    loc, rot, sc = ed.xform(ref)
    b = ed.bounds(ref)
    cs = st["colorSaturationShadows"]
    return {"props": p, "overrides": on, "ev_min": st["autoExposureMinBrightness"], "ev_max": st["autoExposureMaxBrightness"],
            "sat": [cs[c] for c in "xyzw"] if "x" in cs else [cs["r"], cs["g"], cs["b"], cs["a"]], "loc": loc, "rot": rot, "scale": sc,
            "bmin": b[0], "bmax": b[1], "method": st.get("autoExposureMethod")}


def box_to_xform(box, unit):
    centre = [(b[0] + b[1]) / 2.0 for b in box]
    scale = [(b[1] - b[0]) / unit[i] for i, b in enumerate(box)]
    return centre, scale


def apply_pp(ed):
    # PP_Cloister: location and scale only
    ref = ed.find_one(PP_CLOISTER["label"], must=True)
    s0 = pp_state(ed, ref)
    info("PP_Cloister before: %s" % json.dumps(s0))
    unit = [(s0["bmax"][i] - s0["bmin"][i]) / s0["scale"][i] for i in range(3)]
    centre0 = [(s0["bmax"][i] + s0["bmin"][i]) / 2.0 for i in range(3)]
    if not near(centre0, s0["loc"], 0.5):
        raise RuntimeError("PP_Cloister brush is not centred on the actor (bounds centre %s, location %s): stop" % (centre0, s0["loc"]))
    info("PP_Cloister unit brush size %s (bounds / scale), brush centred on the actor" % [round(u, 3) for u in unit])
    centre, scale = box_to_xform(PP_CLOISTER["box"], unit)
    ed.set_xform(ref, centre, s0["rot"], scale)
    # the two new volumes: the same unit brush as PP_Cloister
    for n in PP_NEW:
        c, sc = box_to_xform(n["box"], unit)
        r2, created = ed.get_or_create("/Script/Engine.PostProcessVolume", n["label"], c)
        ed.set_xform(r2, c, (0, 0, 0), sc)
        ed.setp(r2, {"bUnbound": False, "blendRadius": n["blend"], "priority": n["priority"], "blendWeight": 1.0, "bEnabled": True})
        # P14-5 (owner's P14-4 choices): own EV per volume; no ColorSaturationShadows override (the global grade B replaces it)
        ed.setp(r2, {"settings": {"bOverride_AutoExposureMinBrightness": True, "bOverride_AutoExposureMaxBrightness": True,
                                  "autoExposureMinBrightness": n["ev"], "autoExposureMaxBrightness": n["ev"],
                                  "bOverride_ColorSaturationShadows": False}})
        info("%s %s at %s scale %s" % (n["label"], "created" if created else "updated", [round(v, 2) for v in c], [round(v, 4) for v in sc]))
    s1 = pp_state(ed, ref)
    info("PP_Cloister after: %s" % json.dumps(s1))


def check_pp(ed):
    def box_ok(s, box):
        return near(s["bmin"], [b[0] for b in box], 1.0) and near(s["bmax"], [b[1] for b in box], 1.0)

    def fmt(s):
        return "bounds %s..%s prio %s blend %s unbound %s enabled %s overrides %s ev %s/%s sat %s method %s" % (
            [round(v, 1) for v in s["bmin"]], [round(v, 1) for v in s["bmax"]], s["props"]["priority"], s["props"]["blendRadius"], s["props"]["bUnbound"],
            s["props"].get("bEnabled"), s["overrides"], round(s["ev_min"], 4), round(s["ev_max"], 4), [round(v, 4) for v in s["sat"]], s["method"])

    # shrunk and new volumes
    # P14-5: each row carries its own EV (PP_Chapel 1.6)
    want_rows = [("PP_Cloister", PP_CLOISTER["box"], 1.0, 300.0, PP_CLOISTER["ev"])] + [(n["label"], n["box"], n["priority"], n["blend"], n["ev"]) for n in PP_NEW]
    for label, box, prio, blend, ev in want_rows:
        ref = ed.find_one(label)
        if not ref:
            rec(False, "%s exists" % label)
            continue
        s = pp_state(ed, ref)
        ok = (box_ok(s, box) and abs(s["props"]["priority"] - prio) < 1e-5 and abs(s["props"]["blendRadius"] - blend) < 1e-3 and s["props"]["bUnbound"] is False
              and set(s["overrides"]) == PP_OVERRIDES and abs(s["ev_min"] - ev) < 1e-5 and abs(s["ev_max"] - ev) < 1e-5
              and near(s["sat"], PP_SAT, 1e-5) and near(s["rot"], (0, 0, 0), 1e-4))   # sat = the stored value, no longer an override (P14-5)
        rec(ok, "%s: %s" % (label, fmt(s)))
        if label != "PP_Cloister":
            rec(s["props"]["bEnabled"] is True and "AutoExposureMethod" not in s["overrides"], "%s overrides only the two EV overrides (no method override; P14-5)" % label)
            root = R(J(ed.call(A, "get_root_component", {"actor": {"refPath": ref}})))
            body = ed.props(root, ["bodyInstance"])["bodyInstance"]
            rec(body.get("collisionProfileName") == "NoCollision", "%s brush collision profile %s (helper volumes are NoCollision)" % (label, body.get("collisionProfileName")))
    # untouched volumes
    for label in ("PP_Crypt", "PP_Outdoor_Night", "PostProcess_Exposure"):
        ref = ed.find_one(label)
        if not ref:
            rec(False, "%s exists" % label)
            continue
        w = PP_BEFORE[label]
        s = pp_state(ed, ref)
        ok = (abs(s["props"]["priority"] - w["priority"]) < 1e-5 and abs(s["props"]["blendRadius"] - w["blend"]) < 1e-3 and s["props"]["bUnbound"] == w["unbound"]
              and set(s["overrides"]) == set(w["overrides"]) and abs(s["ev_min"] - w["ev"]) < 1e-5 and abs(s["ev_max"] - w["ev"]) < 1e-5 and near(s["sat"], w["sat"], 1e-5)
              and near(s["loc"], w["xform"][0], 1e-3) and near(s["scale"], w["xform"][1], 1e-4)
              and (w["unbound"] or box_ok(s, w["box"])))
        rec(ok, "%s untouched: %s" % (label, fmt(s)))


# ---------------------------------------------------------------------------------------------- 4. groups
def mode_norm(m):
    return str(m).split("::")[-1].strip().lower()


def rule_json(r):
    d = {"requiredTag": {"tagName": r[0]}, "mode": r[1]}
    if r[1] != "Off":
        d.update({"intensityScale": r[2], "flickerAmount": r[3], "flickerSpeed": r[4]})
    return d


def group_refs(ed, g):
    return ([ed.find_one(x, must=True) for x in g["lights"]], [ed.find_one(x, must=True) for x in g["emissive"]], [ed.find_one(x, must=True) for x in g["glow"]])


def apply_groups(ed):
    for g in GROUPS:
        lights, emissive, glow = group_refs(ed, g)
        locs = [ed.xform(r)[0] for r in lights]
        mean = [sum(p[i] for p in locs) / len(locs) for i in range(3)]
        ref, created = ed.get_or_create(GROUP_CLASS, g["label"], mean)
        ed.set_xform(ref, mean, (0, 0, 0), (1, 1, 1))
        ed.setp(ref, {"lights": [{"refPath": r} for r in lights]})
        if emissive or ed.props(ref, ["emissiveActors"])["emissiveActors"]:
            ed.setp(ref, {"emissiveActors": [{"refPath": r} for r in emissive]})
        if glow or ed.props(ref, ["glowActors"])["glowActors"]:
            ed.setp(ref, {"glowActors": [{"refPath": r} for r in glow]})
        ed.setp(ref, {"rules": [rule_json(r) for r in g["rules"]]})
        ed.setp(ref, {"fadeSeconds": FADE_SECONDS})
        info("%s %s at %s: %d lights, %d emissive, %d glow, %d rules" % (g["label"], "created" if created else "updated", [round(v, 1) for v in mean],
                                                                          len(lights), len(emissive), len(glow), len(g["rules"])))


def check_groups(ed):
    seen_light, seen_glow = {}, {}
    found = 0
    for g in GROUPS:
        ref = ed.find_one(g["label"])
        if not ref:
            rec(False, "%s exists" % g["label"])
            continue
        found += 1
        p = ed.props(ref, ["lights", "emissiveActors", "glowActors", "glowParameter", "rules", "fadeSeconds"])
        lights = [ed.label(R(x)) for x in p["lights"] if R(x)]
        emissive = [ed.label(R(x)) for x in p["emissiveActors"] if R(x)]
        glow = [ed.label(R(x)) for x in p["glowActors"] if R(x)]
        nulls = sum(1 for k in ("lights", "emissiveActors", "glowActors") for x in p[k] if not R(x))
        for l in lights:
            seen_light.setdefault(l, []).append(g["label"])
        for l in glow:
            seen_glow.setdefault(l, []).append(g["label"])
        # rules
        rules_ok = len(p["rules"]) == len(g["rules"])
        got_rules = []
        if rules_ok:
            for want, got in zip(g["rules"], p["rules"]):
                tag = (got["requiredTag"] or {}).get("tagName")
                w = want if len(want) == 5 else (want[0], want[1]) + RULE_DEFAULTS
                one = (tag == want[0] and mode_norm(got["mode"]) == want[1].lower()
                       and abs(got["intensityScale"] - w[2]) < 1e-4 and abs(got["flickerAmount"] - w[3]) < 1e-4 and abs(got["flickerSpeed"] - w[4]) < 1e-4)
                got_rules.append((tag, mode_norm(got["mode"]), round(got["intensityScale"], 3), round(got["flickerAmount"], 3), round(got["flickerSpeed"], 3)))
                rules_ok &= one
        loc, rot, sc = ed.xform(ref)
        lloc = [ed.xform(ed.find_one(x, must=True))[0] for x in g["lights"]]
        mean = [sum(pp[i] for pp in lloc) / len(lloc) for i in range(3)]
        ok = (lights == g["lights"] and emissive == g["emissive"] and glow == g["glow"] and nulls == 0 and rules_ok
              and abs(p["fadeSeconds"] - FADE_SECONDS) < 1e-5 and p["glowParameter"] == "Color" and near(loc, mean, 0.05) and near(rot, (0, 0, 0), 1e-4) and near(sc, (1, 1, 1), 1e-6))
        rec(ok, "%s lights %s emissive %s glow %s rules %s fade %s param %s loc %s (mean %s)" % (
            g["label"], lights, emissive, glow, got_rules, p["fadeSeconds"], p["glowParameter"], [round(v, 1) for v in loc], [round(v, 1) for v in mean]))
        # lantern distances (the pairing at BeginPlay is the nearest light of the group)
        for gl in g["glow"]:
            gp = ed.xform(ed.find_one(gl, must=True))[0]
            d = sorted((math.dist(gp, ed.xform(ed.find_one(l, must=True))[0]), l) for l in g["lights"])
            info("  glow %s nearest group light %s at %.1f cm%s" % (gl, d[0][1], d[0][0], "" if len(d) < 2 else " (next %.1f)" % d[1][0]))
    rec(found == 9, "9 light groups present (%d)" % found)
    dup_l = {k: v for k, v in seen_light.items() if len(v) > 1}
    dup_g = {k: v for k, v in seen_glow.items() if len(v) > 1}
    rec(not dup_l, "no light is in two groups (%d distinct lights; duplicates %s)" % (len(seen_light), dup_l))
    rec(not dup_g, "no glow actor is in two groups (%d distinct; duplicates %s)" % (len(seen_glow), dup_g))
    all_group_actors = [x for g in GROUPS for x in g["lights"]]
    rec(len(all_group_actors) == len(set(all_group_actors)), "the plan table itself lists no light twice (%d entries)" % len(all_group_actors))
    # the group classes
    n = len([r for r in ed.find_all(name="SLG_") if ed.label(r).startswith("SLG_")])
    rec(n == 9, "%d actors labelled SLG_* (want 9)" % n)


# ---------------------------------------------------------------------------------------------- 5. decals
def decal_comp(ed, ref):
    return ref + ".NewDecalComponent"


def apply_decals(ed):
    for label, loc, rot, size, mi in DECALS:
        ref, created = ed.get_or_create("/Script/Engine.DecalActor", label, loc, rot)
        ed.set_xform(ref, loc, rot, (1, 1, 1))
        ed.setp(decal_comp(ed, ref), {"decalMaterial": {"refPath": "%s%s.%s" % (INST, mi, mi)}, "decalSize": vec(size)})
        info("%s %s at %s rot %s size %s %s" % (label, "created" if created else "updated", loc, rot, size, mi))


def check_decals(ed):
    for label, loc, rot, size, mi in DECALS:
        ref = ed.find_one(label)
        if not ref:
            rec(False, "%s exists" % label)
            continue
        l, r, s = ed.xform(ref)
        p = ed.props(decal_comp(ed, ref), ["decalMaterial", "decalSize"])
        mat = (R(p["decalMaterial"]) or "").rsplit(".", 1)[-1]
        sz = v3(p["decalSize"])
        ok = near(l, loc, 0.01) and same_rot(r, rot) and near(s, (1, 1, 1), 1e-6) and near(sz, size, 0.01) and mat == mi
        rec(ok, "%s loc %s rot %s scale %s size %s material %s" % (label, [round(v, 2) for v in l], [round(v, 2) for v in r], s, [round(v, 2) for v in sz], mat))
    n = len([r for r in ed.find_all(name="RV_") if ed.label(r).startswith("RV_")])
    rec(n == 5, "%d actors labelled RV_* (want 5)" % n)


# ---------------------------------------------------------------------------------------------- 6. apparitions
def app_ref(ed, label, objname):
    ref = ed.find_one(label, must=True)
    if not ref.endswith(":PersistentLevel." + objname):
        raise RuntimeError("label %s is %s, not %s" % (label, ref, objname))
    return ref


BEFORE_DIR = os.path.join(ROOT, "Saved", "p14_3_scratch")


def apply_apparitions(ed):
    os.makedirs(BEFORE_DIR, exist_ok=True)
    for label, objname in APPARITIONS:
        ref = app_ref(ed, label, objname)
        st = ed.props(ref, ["stations"])["stations"]
        path = os.path.join(BEFORE_DIR, "stations_before_%s.json" % label)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                json.dump(st, f, indent=1)
        info("%s stations before: %s" % (label, json.dumps(st)))
        if st[0].get("bLightningOnHold") is True:
            info("%s station 0 already has bLightningOnHold" % label)
            continue
        new = copy.deepcopy(st)
        new[0]["bLightningOnHold"] = True
        ed.setp(ref, {"stations": new})
        after = ed.props(ref, ["stations"])["stations"]
        info("%s stations after:  %s" % (label, json.dumps(after)))


def diff_json(a, b, path=""):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append("%s.%s only in %s" % (path, k, "after" if k in b else "before"))
            else:
                out += diff_json(a[k], b[k], "%s.%s" % (path, k))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append("%s length %d != %d" % (path, len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff_json(x, y, "%s[%d]" % (path, i))
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        if abs(a - b) > 1e-9:
            out.append("%s %r != %r" % (path, a, b))
    elif a != b:
        out.append("%s %r != %r" % (path, a, b))
    return out


def check_apparitions(ed):
    for label, objname in APPARITIONS:
        ref = app_ref(ed, label, objname)
        st = ed.props(ref, ["stations"])["stations"]
        path = os.path.join(BEFORE_DIR, "stations_before_%s.json" % label)
        flag = st[0].get("bLightningOnHold")
        rec(flag is True, "%s (%s) station 0 bLightningOnHold = %s (%d station(s))" % (label, objname, flag, len(st)))
        if os.path.exists(path):
            before = json.load(open(path, encoding="utf-8"))
            d = diff_json(before, st)
            rec(d == ["[0].bLightningOnHold False != True"] or d == [], "%s: every other station field identical to before (diff: %s)" % (label, d))
            walk = st[0].get("walkPath")
            info("%s walkPath %d points, walkSpeed %s, holdSeconds %s, lookCone %s, location %s" % (
                label, len(walk or []), st[0].get("walkSpeed"), st[0].get("holdSeconds"), st[0].get("lookConeDegrees"), st[0].get("location")))
        else:
            info("%s: no before-file in %s; field-by-field proof not possible in this run" % (label, BEFORE_DIR))


# ---------------------------------------------------------------------------------------------- census and dirty state
def check_census(ed, start):
    n = len(ed.find_all())
    rec(n == start + NEW_ACTORS, "actor census %d (start %d + %d = %d)" % (n, start, NEW_ACTORS, start + NEW_ACTORS))


def check_dirty(ed, expect_map_dirty):
    d = ed.is_dirty(MAP_PKG)
    info("%s is_dirty = %s" % (MAP_PKG, d))
    if expect_map_dirty is not None:
        rec(d == expect_map_dirty, "%s is_dirty is %s (expected %s)" % (MAP_PKG, d, expect_map_dirty))
    for pkg in NEVER_SAVE:
        rec(not ed.is_dirty(pkg), "%s is not dirty" % pkg.rsplit("/", 1)[-1])


STEPS = ["tags", "zones", "pp", "groups", "decals", "apparitions"]
APPLY = {"tags": apply_tags, "zones": apply_zones, "pp": apply_pp, "groups": apply_groups, "decals": apply_decals, "apparitions": apply_apparitions}
CHECK = {"tags": check_tags, "zones": check_zones, "pp": check_pp, "groups": check_groups, "decals": check_decals, "apparitions": check_apparitions}


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--apply", action="store_true")
    g.add_argument("--check", action="store_true")
    ap.add_argument("--only", default="", help="comma list of: " + ",".join(STEPS))
    ap.add_argument("--start", type=int, default=CENSUS_START, help="actor count before P14-3 (F0: 2992)")
    ap.add_argument("--map-dirty", choices=["true", "false"], default=None, help="--check: expected is_dirty of the map")
    ap.add_argument("--no-census", action="store_true")
    a = ap.parse_args()
    steps = [s for s in STEPS if not a.only or s in a.only.split(",")]
    try:
        ed = Ed()
        if ed.call(E, "IsPIERunning"):
            sys.exit("PIE is running: stop it first (spawned actors would go to the PIE world)")
        lvl = str(ed.call(S, "get_current_level", {}))
        if not lvl.startswith(MAP_PKG):
            sys.exit("the editor is on %s, not L_Monastery" % lvl)
        if a.apply:
            n0 = len(ed.find_all())
            info("actor census before apply: %d; map is_dirty: %s" % (n0, ed.is_dirty(MAP_PKG)))
            for s in steps:
                print("=== apply %s" % s, flush=True)
                APPLY[s](ed)
            print("=== verifying", flush=True)
            for s in steps:
                print("=== check %s" % s, flush=True)
                CHECK[s](ed)
            info("census after apply: %d (start %d + %d = %d); map is_dirty: %s" % (len(ed.find_all()), a.start, NEW_ACTORS, a.start + NEW_ACTORS, ed.is_dirty(MAP_PKG)))
        else:
            for s in steps:
                print("=== check %s" % s, flush=True)
                CHECK[s](ed)
            if not a.only and not a.no_census:
                check_census(ed, a.start)
                check_dirty(ed, None if a.map_dirty is None else a.map_dirty == "true")
        info("%d editor calls" % ed.calls)
    except EditorStop as e:
        print("STOP: editor problem (%s). Do NOT save. Restart the editor if it crashed, then run --apply again." % e)
        sys.exit(3)
    fails = [m for ok, m in results if not ok]
    print("\nRESULT: %d PASS, %d FAIL" % (len(results) - len(fails), len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
