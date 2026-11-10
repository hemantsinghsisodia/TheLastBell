"""P16-3: the Phase 16 level work in L_Monastery (Docs/plans/P16_AUDIO.md section 2.4, 2.9, 6.5, F0, P16-3 brief).

Run with the editor open on L_Monastery, PIE off (Windows Python, from PowerShell or Git Bash with MSYS_NO_PATHCONV=1):
    python -I Tools/audio/p16_level.py --apply [--resume] [--only zones,volumes,emitters,floors,water,creatures]
    python -I Tools/audio/p16_level.py --check [--only ...] [--start 3054]
    python -I Tools/audio/p16_level.py --save           (only when the full --check is all PASS and the census is 3102)
    python -I Tools/audio/p16_level.py --reload-check   (after --save: reload the map from disk, then run the full --check)

What it places (census 3054 -> 3102, outliner folder "Audio"; 3089 is the end of P16-3, the 13 creature emitters are P16-6 / D-112, step "creatures"):
  7  ALBAudioZone    AUD_Zone_<Name>   (Chapel, Crypt, Cloister, Garth, Passage, TowerStair, Belfry)
  7  AudioVolume     AUD_Vol_<Name>    (same boxes, brush scale = size / 200; reverb RVB_LB_<Area>; Garth without reverb)
  18 ALBAmbientEmitter AUD_Emit_<Kind>_<id>  (10 drips at the P15 F0.8 points, 5 creaks, 3 distant chains)
  3  StaticMeshActor AUD_Water_W / _E / _Ledge (thin hidden boxes under the crypt pools: block Visibility only, PM_LB_Water)
  13 ALBAmbientEmitter AUD_Emit_<Kind>_<id>  (P16-6: 4 bats, 3 owls, 2 howls, 4 rats; step "creatures")
and sets BodyInstance.PhysMaterialOverride on the F0 floor actors (Wood 166, Grass 1, Earth 40).

--apply is idempotent: every actor is found by its EXACT label (find_actors matches substrings, so the result is filtered) and updated, or
created when missing. --apply never saves. The census at the start must be 3054 (--resume skips that guard so a partial run can be continued, and
is needed to add the creatures to a map that already holds the 3089 actors of P16-3).
--check only reads and prints PASS / FAIL per item (exit code 1 when any FAIL).
--save runs the full check first, then saves ONLY /Game/LastBell/Maps/L_Monastery (one package) and checks is_dirty afterwards; it then checks
that the never-save list and every audio asset are still not dirty. Never save-all.

Collision of the water pads: set_properties writes the raw struct without the editor's side effects, so the live component keeps its old
response container; the saved ResponseArray (valid channel NAMES: WorldStatic, Pawn, Visibility, ...) is what UBodyInstance::FixupData turns
into the real container when the map loads. Hence --reload-check (load_level) after --save.

If the editor crashes or a call hangs for more than 180 s the script stops ("STOP", exit code 3). Do not save and do not retry blindly.
"""
import argparse
import json
import math
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Tools", "lighting"))
sys.path.insert(0, os.path.join(ROOT, "Tools", "fx"))
import p14_3_level as L  # noqa: E402  (the Ed client, helpers)
import p15_level as P15  # noqa: E402  (NEVER_SAVE_P158)
from p14_3_level import EditorStop, J, R, v3, vec, xf, near  # noqa: E402

S, A, O, AS, E = L.S, L.A, L.O, L.AS, L.E
MAP_PKG = L.MAP_PKG
FOLDER = "Audio"
CENSUS_START = 3054
NEW_ACTORS = 7 + 7 + 18 + 3 + 13     # 48 -> 3102 (35 -> 3089 after P16-3, +13 creature emitters in P16-6)
NEVER_SAVE = list(P15.NEVER_SAVE_P158)

ZONE_CLASS = "/Script/LastBell.LBAudioZone"
VOL_CLASS = "/Script/Engine.AudioVolume"
EMIT_CLASS = "/Script/LastBell.LBAmbientEmitter"
CUBE = "/Engine/BasicShapes/Cube.Cube"

AUD = "/Game/LastBell/Audio/"


def snd(sub, name):
    return AUD + sub + "/" + name + "." + name


def variants(prefix, n):
    return [snd("Room", "%s_%02d" % (prefix, i)) for i in range(1, n + 1)]


def rvb(area):
    return AUD + "Mix/RVB_LB_%s.RVB_LB_%s" % (area, area)


PM = {n: "/Game/LastBell/Physics/PM_LB_%s.PM_LB_%s" % (n, n) for n in ("Stone", "Wood", "Earth", "Grass", "Water", "Metal")}


# ---------------------------------------------------------------------------------------------- 1/2. the F0 table (zones and AudioVolumes share the boxes)
# name, centre, half extent, priority, RoofRain, InteriorWind, Howl, Darkness, room tone (Room_<x>), tone volume, reverb (RVB_LB_<x>), (exterior volume, exterior LPF Hz)
AREAS = [
    ("Chapel",     (7550.0, -345.0, 1180.0),   (1550.0, 1205.0, 1220.0), 1, 0.90, 0.25, 0.00, 0.3, "Chapel",   0.4, "Chapel",  (0.35, 2500.0)),
    ("Crypt",      (9150.0, -1215.0, -610.0),  (2850.0, 1735.0, 590.0),  2, 0.05, 0.05, 0.00, 1.0, "Crypt",    0.8, "Crypt",    (0.35, 2500.0)),
    ("Cloister",   (10750.0, 1770.0, 730.0),   (1290.0, 1270.0, 770.0),  1, 0.70, 0.50, 0.00, 0.2, "Cloister", 0.5, "Cloister", (0.70, 6000.0)),
    ("Garth",      (10852.5, 1802.5, 730.0),   (607.5, 457.5, 770.0),    2, 0.00, 1.00, 0.00, 0.1, None,       0.0, None,       (1.00, 20000.0)),
    ("Passage",    (7750.0, 2000.0, 430.0),    (1710.0, 340.0, 470.0),   1, 0.00, 0.40, 0.00, 0.6, "Passage",  0.7, "Passage",  (0.35, 2500.0)),
    ("TowerStair", (12500.0, 2000.0, 1305.0),  (510.0, 510.0, 1345.0),   3, 0.60, 0.60, 0.35, 0.6, "Tower",    0.7, "Tower",    (0.35, 2500.0)),
    ("Belfry",     (12500.0, 2000.0, 3600.0),  (510.0, 510.0, 1200.0),   4, 0.80, 1.00, 0.25, 0.3, "Belfry",   0.4, "Belfry",   (0.70, 6000.0)),   # P16-6 owner: Howl 1.0 -> 0.25, tone volume 0.5 -> 0.4 (too loud)
]
REVERB_VOLUME, REVERB_FADE = 0.6, 1.0


def area_dict(a):
    return dict(name=a[0], centre=a[1], half=a[2], prio=a[3], roof=a[4], wind=a[5], howl=a[6], dark=a[7], tone=a[8], tonevol=a[9], rvb=a[10], ext=a[11])


AREA = [area_dict(a) for a in AREAS]


def brush_scale(half):
    return tuple(h * 2.0 / 200.0 for h in half)      # the default AudioVolume brush is a 200 cm cube


# ---------------------------------------------------------------------------------------------- 3. emitters
# P15 F0.8: tag, location, over water
DRIPS = [
    ("W_9050", (9050.0, -2280.0, -105.0), True), ("W_9200", (9200.0, -2280.0, -105.0), True), ("Pit_9400", (9400.0, -2280.0, -105.0), True),
    ("E_9900", (9900.0, -2280.0, -105.0), True), ("E_10000", (10000.0, -2280.0, -105.0), True),
    ("WC_a", (6450.0, -1900.0, -105.0), False), ("SC_b", (7250.0, -2350.0, -105.0), False), ("NC_a", (10250.0, -900.0, -105.0), False),
    ("Belfry_N_wall", (12600.0, 2440.0, 3700.9), False), ("Belfry_NW_corner", (12100.0, 2400.0, 3793.1), False),
]
# creaks: id, location, why. The three tower creaks sit INSIDE the solid shaft core (Tw_Core, x 12290..12710, y 1790..2210, z 0..2500) within 55 cm of
# its axis: >= 155 cm from the nearest core face and >= 285 cm from the stair ring (the walk lane, WP_TowerStairs), so they read as the timber of
# the shaft groaning through the wall. The two belfry creaks sit at roof-beam height (z 3380) in the NE and SW corners, 880 cm above the belfry floor.
CREAKS = [
    ("T1", (12500.0, 2000.0, 650.0), "tower shaft core, level of landing 3"),
    ("T2", (12455.0, 1960.0, 1350.0), "tower shaft core, level of landing 6"),
    ("T3", (12545.0, 2040.0, 2050.0), "tower shaft core, level of landing 9"),
    ("B1", (12900.0, 2400.0, 3380.0), "belfry NE roof-beam joint"),
    ("B2", (12100.0, 1600.0, 3380.0), "belfry SW roof-beam joint"),
]
# distant chains: id, location, why (deep crypt corners, z -300 = mid height under the vault crown at -100)
CHAINS = [
    ("C1", (11450.0, -2450.0, -300.0), "crypt SE corner of the east room"),
    ("C2", (6370.0, -2450.0, -300.0), "crypt SW room, west end"),
    ("C3", (7550.0, -2850.0, -300.0), "crypt south nook, west end"),
]
DRIP_WATER = dict(var=variants("SFX_LB_Drip_Water", 5), imin=1.5, imax=4.0)
DRIP_STONE = dict(var=variants("SFX_LB_Drip_Stone", 5), imin=2.0, imax=6.0)
CREAK = dict(var=variants("SFX_LB_Creak_Wood", 5), imin=8.0, imax=20.0)
CHAIN = dict(var=variants("SFX_LB_Chain_Distant", 4), imin=8.0, imax=18.0)   # P16-5: owner's choice (was 20..45)
DEFAULT_RADIUS = 3000.0
CHAIN_RADIUS = 4000.0
DEF_VOL, DEF_PITCH = (0.7, 1.0), (0.95, 1.05)

EMITTERS = []         # label, location, spec, active radius
for tag, loc, water in DRIPS:
    EMITTERS.append(("AUD_Emit_Drip_" + tag, loc, DRIP_WATER if water else DRIP_STONE, DEFAULT_RADIUS))
for tag, loc, _ in CREAKS:
    EMITTERS.append(("AUD_Emit_Creak_" + tag, loc, CREAK, DEFAULT_RADIUS))
for tag, loc, _ in CHAINS:
    EMITTERS.append(("AUD_Emit_Chain_" + tag, loc, CHAIN, CHAIN_RADIUS))

BELL = (12420.1, 2000.0, 2750.0)
CORE = ((12290.0, 1790.0), (12710.0, 2210.0))     # Tw_Core footprint

# ---------------------------------------------------------------------------------------------- 3b. creature emitters (P16-6, D-112)
# Each coordinate comes from the live geometry (probed over MCP) and is checked by --check; one line of reason each.
BATS = [   # belfry interior x 12040..12960, y 1540..2460, roof underside z 3500 (Tw_Roof); bell (12420, 2000, 2750)
    ("B1", (12250.0, 2250.0, 3430.0), "belfry NW roof beam, 421 cm from the NW corner drip, 744 cm from the bell"),
    ("B2", (12800.0, 1700.0, 3430.0), "belfry SE roof beam, the opposite corner, 835 cm from the bell, 709 cm from the creak B1"),
    ("B3", (12480.0, 2000.0, 3430.0), "belfry ridge over the bell (Bell_Beam, z 3300..3400), 683 cm from the bell, 340 cm from B1"),
    ("T1", (12440.0, 1970.0, 2440.0), "inside the shaft core 60 cm below the belfry floor (z 2500), 67 cm from the axis, 410 cm from the creak T3: bats under the top slab"),
]
OWLS = [
    ("C1", (4550.0, 550.0, 650.0), "crown of the dead tree Garden_DeadTree_A (bounds x 4332..4768, y 310..790, z 0..700), mid-courtyard"),
    ("C2", (3000.0, 3620.0, 810.0), "top of the north perimeter wall Perim_N (y 3600..3640, top z 800), 3440 cm from the tree"),
    ("G1", (10750.0, 2250.0, 640.0), "top of the north garth arcade arch CLA_Arch_N_1 (top z 620), on the garth side (inside the Garth zone, y <= 2260)"),
]
HOWLS = [
    ("NE", (14800.0, 4900.0, 500.0), "north-east, 1360 cm beyond Perim_E (x 13440) and 1260 cm beyond Perim_N (y 3640)"),
    ("SW", (-4400.0, -4900.0, 500.0), "south-west, 1360 cm beyond Perim_W (x -3040) and 1260 cm beyond Perim_S (y -3640)"),
]
RATS = [
    ("R1", (6325.0, -2000.0, -590.0), "west hall, base of the west wall CA_Wall_W6300 (face x 6302); 325 cm from Search_Crypt_09 and _10"),
    ("R2", (7525.0, -1900.0, -590.0), "ossuary hall, base of CA_Wall_W_OS_N (face x 7502); 862 cm from the sacristy lane"),
    ("R3", (10750.0, -2475.0, -590.0), "east crypt south row, base of CA_Wall_S_CC_1 (face y -2498); 509 cm from the flooded ledge lane"),
    ("R4", (9600.0, -2635.0, -590.0), "south niche behind the flooded hall, base of CA_Wall_S_FP_1 (face y -2612); 255 cm from the ledge lane"),
]
BAT = dict(var=variants("SFX_LB_Bat", 6), imin=6.0, imax=15.0)
OWL = dict(var=variants("SFX_LB_Owl", 4), imin=30.0, imax=60.0)
HOWL = dict(var=variants("SFX_LB_Howl", 3), imin=120.0, imax=240.0)
RAT = dict(var=variants("SFX_LB_Rat", 5), imin=15.0, imax=35.0)
BAT_RADIUS, OWL_RADIUS, HOWL_RADIUS, RAT_RADIUS = 2500.0, 6000.0, 15000.0, 2000.0
CREATURES = []        # label, location, spec, active radius
for tag, loc, _ in BATS:
    CREATURES.append(("AUD_Emit_Bat_" + tag, loc, BAT, BAT_RADIUS))
for tag, loc, _ in OWLS:
    CREATURES.append(("AUD_Emit_Owl_" + tag, loc, OWL, OWL_RADIUS))
for tag, loc, _ in HOWLS:
    CREATURES.append(("AUD_Emit_Howl_" + tag, loc, HOWL, HOWL_RADIUS))
for tag, loc, _ in RATS:
    CREATURES.append(("AUD_Emit_Rat_" + tag, loc, RAT, RAT_RADIUS))
BELFRY_INT = ((12040.0, 1540.0), (12960.0, 2460.0))   # inside the Tw_* walls
CRYPT_BOX = ((6300.0, -2950.0, -1200.0), (12000.0, 520.0, -20.0))    # the Crypt zone box
# ---------------------------------------------------------------------------------------------- 4. floors
WOOD = (["Tw_Landing_%02d" % i for i in range(1, 11)] + ["Stair_F%02d_%02d" % (f, s) for f in range(1, 12) for s in range(14)] + ["Top_Slab_N", "Top_Slab_W"])
GRASS = ["Garth"]
EARTH = ["Garden_Earth_%s_%02d" % (q, i) for q in ("NE", "NW", "SE", "SW") for i in range(10)]
FLOOR_GROUPS = [("Wood", WOOD), ("Grass", GRASS), ("Earth", EARTH)]
STONE_SAMPLE = ["Ground_0", "CryptFloor_0", "CryptFloor_1", "CryptFloor_2", "Prop_Crypt_0", "TWA_Landing_01", "Ch_Floor_B1"]
# ---------------------------------------------------------------------------------------------- 5. water pads
PADS = [("AUD_Water_W", "CA_Water_W"), ("AUD_Water_E", "CA_Water_E"), ("AUD_Water_Ledge", "CA_Water_Ledge")]
PAD_THICK, PAD_ABOVE = 2.0, 0.5
# valid collision channel NAMES (engine + Config/DefaultEngine.ini): only Visibility blocks
PAD_RESPONSES = [("WorldStatic", "ECR_Ignore"), ("WorldDynamic", "ECR_Ignore"), ("Pawn", "ECR_Ignore"), ("Visibility", "ECR_Block"), ("Camera", "ECR_Ignore"),
                 ("PhysicsBody", "ECR_Ignore"), ("Vehicle", "ECR_Ignore"), ("Destructible", "ECR_Ignore"), ("Projectile", "ECR_Ignore"),
                 ("Interaction", "ECR_Ignore")]

results = []


def rec(ok, msg):
    results.append((bool(ok), msg))
    print(("PASS  " if ok else "FAIL  ") + msg, flush=True)
    return bool(ok)


def info(msg):
    print("INFO  " + msg, flush=True)


def rnd(v, n=2):
    return [round(float(x), n) for x in v]


def close(a, b, tol=1e-4):
    return abs(float(a) - float(b)) <= tol


# ---------------------------------------------------------------------------------------------- the editor client
class Ed(L.Ed):
    """p14_3_level.Ed plus asset spawns, class lookup and the folder list; the folder is always passed explicitly."""

    def get_or_create(self, cls, label, loc, rot=(0, 0, 0), sc=(1, 1, 1), folder=FOLDER):
        return super().get_or_create(cls, label, loc, rot, sc, folder)

    def spawn_asset(self, asset, label, loc, rot=(0, 0, 0), sc=(1, 1, 1), folder=FOLDER):
        a = self.call(S, "add_to_scene_from_asset", {"asset_path": asset, "name": label, "xform": xf(loc, rot, sc)})
        ref = R(a)
        if not ref:
            raise RuntimeError("spawn of %s (%s) returned %r" % (label, asset, a))
        self.call(A, "set_label", {"actor": {"refPath": ref}, "label": label})
        self._labels[ref] = label
        if folder:
            self.call(S, "set_actor_folder", {"actor": {"refPath": ref}, "folder_path": folder})
        return ref

    def get_or_create_asset(self, asset, label, loc, rot=(0, 0, 0), sc=(1, 1, 1)):
        ref = self.find_one(label)
        if ref:
            return ref, False
        return self.spawn_asset(asset, label, loc, rot, sc), True

    def folder_actors(self, folder=FOLDER):
        try:
            return set(R(x) for x in self.call(S, "get_actors_in_folder", {"folder_path": folder}) or [])
        except RuntimeError:
            return set()

    def class_of(self, ref):
        return R(self.call(O, "get_class", {"instance": {"refPath": ref}}))

    def by_labels(self, key, wanted):
        """{label: ref} for the exact labels in `wanted`, from one substring search on `key`."""
        wanted = set(wanted)
        out = {}
        for r in self.find_all(name=key):
            lab = self.label(r)
            if lab in wanted:
                if lab in out:
                    raise RuntimeError("label %r exists twice" % lab)
                out[lab] = r
        return out


# ---------------------------------------------------------------------------------------------- 1. zones
def apply_zones(ed):
    for a in AREA:
        label = "AUD_Zone_" + a["name"]
        ref, created = ed.get_or_create(ZONE_CLASS, label, a["centre"])
        ed.set_xform(ref, a["centre"], (0, 0, 0), (1, 1, 1))
        vals = {"priority": a["prio"], "roofRain": a["roof"], "interiorWind": a["wind"], "howl": a["howl"], "darkness": a["dark"],
                "zoneName": a["name"]}
        if a["tone"]:
            vals["roomTone"] = {"refPath": snd("Room", "SFX_LB_Room_" + a["tone"])}
        ed.setp(ref, vals)
        ed.setp(ref, {"roomToneVolume": a["tonevol"]})      # P16-5: a float in its own call, read back by --check
        ok = ed.set_vec(ref + ".Box", "boxExtent", a["half"])
        info("%s %s at %s half extent %s%s" % (label, "created" if created else "updated", a["centre"], a["half"], "" if ok else "  (EXTENT READ-BACK MISMATCH)"))


def check_zones(ed):
    fs = ed.folder_actors()
    for a in AREA:
        label = "AUD_Zone_" + a["name"]
        ref = ed.find_one(label)
        if not ref:
            rec(False, "%s exists" % label)
            continue
        loc, rot, sc = ed.xform(ref)
        p = ed.props(ref, ["priority", "roofRain", "interiorWind", "howl", "darkness", "roomTone", "roomToneVolume", "zoneName"])
        ext = v3(ed.props(ref + ".Box", ["boxExtent"])["boxExtent"])
        lo = [loc[i] - ext[i] * sc[i] for i in range(3)]
        hi = [loc[i] + ext[i] * sc[i] for i in range(3)]
        want_lo = [a["centre"][i] - a["half"][i] for i in range(3)]
        want_hi = [a["centre"][i] + a["half"][i] for i in range(3)]
        want_tone = snd("Room", "SFX_LB_Room_" + a["tone"]) if a["tone"] else None
        cls = ed.class_of(ref)
        ok = (near(lo, want_lo, 0.5) and near(hi, want_hi, 0.5) and near(rot, (0, 0, 0), 1e-4) and near(sc, (1, 1, 1), 1e-6)
              and int(p["priority"]) == a["prio"] and close(p["roofRain"], a["roof"]) and close(p["interiorWind"], a["wind"]) and close(p["howl"], a["howl"])
              and close(p["darkness"], a["dark"]) and close(p["roomToneVolume"], a["tonevol"]) and R(p["roomTone"]) == want_tone
              and str(p["zoneName"]) == a["name"] and cls == ZONE_CLASS and ref in fs)
        rec(ok, "%s world box %s..%s prio %s roof %.2f wind %.2f howl %.2f dark %.2f tone %s x%.2f name %s folder %s" % (
            label, rnd(lo, 1), rnd(hi, 1), p["priority"], p["roofRain"], p["interiorWind"], p["howl"], p["darkness"],
            (R(p["roomTone"]) or "None").rsplit(".", 1)[-1], p["roomToneVolume"], p["zoneName"], FOLDER if ref in fs else "NOT-IN-FOLDER"))


# ---------------------------------------------------------------------------------------------- 2. AudioVolumes
def apply_volumes(ed):
    for a in AREA:
        label = "AUD_Vol_" + a["name"]
        sc = brush_scale(a["half"])
        ref, created = ed.get_or_create(VOL_CLASS, label, a["centre"])
        ed.set_xform(ref, a["centre"], (0, 0, 0), sc)
        settings = {"bApplyReverb": a["rvb"] is not None, "volume": REVERB_VOLUME, "fadeTime": REVERB_FADE}
        if a["rvb"]:
            settings["reverbEffect"] = {"refPath": rvb(a["rvb"])}
        ed.setp(ref, {"settings": settings})
        ev, lpf = a["ext"]
        ed.setp(ref, {"ambientZoneSettings": {"exteriorVolume": ev, "exteriorLPF": lpf, "interiorVolume": 1.0}})
        ed.setp(ref, {"priority": a["prio"], "bEnabled": True})
        b = ed.bounds(ref)
        info("%s %s at %s brush scale %s -> bounds %s..%s" % (label, "created" if created else "updated", a["centre"], rnd(sc, 4), rnd(b[0], 1), rnd(b[1], 1)))


def check_volumes(ed):
    fs = ed.folder_actors()
    for a in AREA:
        label = "AUD_Vol_" + a["name"]
        ref = ed.find_one(label)
        if not ref:
            rec(False, "%s exists" % label)
            continue
        loc, rot, sc = ed.xform(ref)
        want_sc = brush_scale(a["half"])
        p = ed.props(ref, ["settings", "ambientZoneSettings", "priority", "bEnabled"])
        st, amb = p["settings"], p["ambientZoneSettings"]
        b = ed.bounds(ref)
        want_lo = [a["centre"][i] - a["half"][i] for i in range(3)]
        want_hi = [a["centre"][i] + a["half"][i] for i in range(3)]
        want_rvb = rvb(a["rvb"]) if a["rvb"] else None
        ev, lpf = a["ext"]
        cls = ed.class_of(ref)
        ok = (near(loc, a["centre"], 0.01) and near(rot, (0, 0, 0), 1e-4) and near(sc, want_sc, 1e-4) and b[2] and near(b[0], want_lo, 0.5) and near(b[1], want_hi, 0.5)
              and bool(st["bApplyReverb"]) == (a["rvb"] is not None) and R(st["reverbEffect"]) == want_rvb and close(st["volume"], REVERB_VOLUME)
              and close(st["fadeTime"], REVERB_FADE) and close(amb["exteriorVolume"], ev) and close(amb["exteriorLPF"], lpf, 0.5) and close(amb["interiorVolume"], 1.0)
              and int(p["priority"]) == a["prio"] and bool(p["bEnabled"]) and cls == VOL_CLASS and ref in fs)
        rec(ok, "%s bounds %s..%s scale %s reverb %s (apply %s vol %.2f fade %.1f) exterior %.2f / %d Hz interior %.1f prio %s enabled %s folder %s" % (
            label, rnd(b[0], 1), rnd(b[1], 1), rnd(sc, 3), (R(st["reverbEffect"]) or "None").rsplit(".", 1)[-1], st["bApplyReverb"], st["volume"], st["fadeTime"],
            amb["exteriorVolume"], amb["exteriorLPF"], amb["interiorVolume"], p["priority"], p["bEnabled"], FOLDER if ref in fs else "NOT-IN-FOLDER"))


# ---------------------------------------------------------------------------------------------- 3. emitters
def apply_emitters(ed):
    apply_emitter_list(ed, EMITTERS)


def apply_creatures(ed):
    apply_emitter_list(ed, CREATURES)


def apply_emitter_list(ed, emitters):
    for label, loc, spec, radius in emitters:
        ref, created = ed.get_or_create(EMIT_CLASS, label, loc)
        ed.set_xform(ref, loc, (0, 0, 0), (1, 1, 1))
        cur = [R(x) for x in ed.props(ref, ["variants"])["variants"]]
        if cur != spec["var"]:
            ed.setp(ref, {"variants": [{"refPath": v} for v in spec["var"]]})
        ed.setp(ref, {"activeRadius": radius})
        ed.setp(ref, {"intervalMin": spec["imin"]})         # P16-5: each float in its own call (read back by --check)
        ed.setp(ref, {"intervalMax": spec["imax"]})
        info("%s %s at %s (%d variants, interval %s..%s s, radius %g)" % (label, "created" if created else "updated", rnd(loc, 1), len(spec["var"]), spec["imin"], spec["imax"], radius))


def check_emitters(ed):
    check_emitter_list(ed, EMITTERS)
    clearance_report(ed)


def check_creatures(ed):
    check_emitter_list(ed, CREATURES)
    creature_clearances(ed)


def check_emitter_list(ed, emitters):
    fs = ed.folder_actors()
    for label, loc, spec, radius in emitters:
        ref = ed.find_one(label)
        if not ref:
            rec(False, "%s exists" % label)
            continue
        l, r, s = ed.xform(ref)
        p = ed.props(ref, ["variants", "loop", "intervalMin", "intervalMax", "volumeRange", "pitchRange", "activeRadius", "loopVolume"])
        got = [R(x) for x in p["variants"]]
        vr, pr = p["volumeRange"], p["pitchRange"]
        ok = (near(l, loc, 0.01) and near(r, (0, 0, 0), 1e-4) and near(s, (1, 1, 1), 1e-6) and got == spec["var"] and R(p["loop"]) is None
              and close(p["intervalMin"], spec["imin"]) and close(p["intervalMax"], spec["imax"]) and close(p["activeRadius"], radius, 0.01)
              and close(vr["x"], DEF_VOL[0]) and close(vr["y"], DEF_VOL[1]) and close(pr["x"], DEF_PITCH[0]) and close(pr["y"], DEF_PITCH[1]) and close(p["loopVolume"], 1.0)
              and ed.class_of(ref) == EMIT_CLASS and ref in fs)
        rec(ok, "%s at %s %d variants (%s..%s) interval %.1f..%.1f radius %g vol %s pitch %s folder %s" % (
            label, rnd(l, 1), len(got), (got[0] if got else "-").rsplit(".", 1)[-1], (got[-1] if got else "-").rsplit(".", 1)[-1], p["intervalMin"], p["intervalMax"],
            p["activeRadius"], rnd([vr["x"], vr["y"]], 2), rnd([pr["x"], pr["y"]], 2), FOLDER if ref in fs else "NOT-IN-FOLDER"))


def seg_dist(p, a, b):
    ab = [b[i] - a[i] for i in range(3)]
    ap = [p[i] - a[i] for i in range(3)]
    d = sum(x * x for x in ab)
    t = 0.0 if d == 0 else max(0.0, min(1.0, sum(ap[i] * ab[i] for i in range(3)) / d))
    return math.dist(p, [a[i] + t * ab[i] for i in range(3)])


def poly_dist(p, pts):
    return min(seg_dist(p, pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def walk_points(ed, prefix):
    """WalkPath TargetPoints with the label prefix, in label order."""
    out = []
    for r in ed.find_all(name=prefix):
        lab = ed.label(r)
        if lab.startswith(prefix):
            out.append((lab, ed.xform(r)[0]))
    return [p for _, p in sorted(out)]


def clearance_report(ed):
    """The creaks and chains must keep away from the walk lanes (WalkPaths) and the AI points; the tower creaks also from the shaft core faces; the belfry ones from the bell."""
    tower = walk_points(ed, "WP_TowerStairs_")
    crypt_lanes = [walk_points(ed, "WP_CryptToCloister_")[:9], walk_points(ed, "WP_SacristyToCrypt_"), walk_points(ed, "WP_FloodedLedge_")]
    ai = []
    for pre in ("Patrol_Crypt_", "Search_Crypt_", "WSpawn_Crypt"):
        for r in ed.find_all(name=pre):
            if ed.label(r).startswith(pre):
                ai.append(ed.xform(r)[0])
    info("clearance inputs: %d WP_TowerStairs points, crypt lanes %s points, %d crypt AI points" % (len(tower), [len(x) for x in crypt_lanes], len(ai)))
    for tag, loc, why in CREAKS:
        lane = poly_dist(loc, tower)
        bell = math.dist(loc, BELL)
        face = min(abs(loc[0] - CORE[0][0]), abs(loc[0] - CORE[1][0]), abs(loc[1] - CORE[0][1]), abs(loc[1] - CORE[1][1])) if tag.startswith("T") else None
        ok = lane >= 150.0 and bell >= 150.0 and (face is None or face >= 150.0)
        rec(ok, "Creak %s %s: lane %.0f cm (>=150), bell %.0f cm (>=150)%s" % (tag, rnd(loc, 1), lane, bell, "" if face is None else ", nearest core face %.0f cm (>=150)" % face))
    for tag, loc, why in CHAINS:
        lane = min(poly_dist(loc, pts) for pts in crypt_lanes if len(pts) > 1)
        aid = min(math.dist(loc, q) for q in ai)
        rec(lane >= 300.0 and aid >= 150.0, "Chain %s %s: walk lane %.0f cm (>=300), nearest AI point %.0f cm (>=150)" % (tag, rnd(loc, 1), lane, aid))


def all_lanes(ed):
    """Every WP_* walk path (WalkPath TargetPoints) grouped by the label prefix without the trailing index, in label order."""
    groups = {}
    for r in ed.find_all(name="WP_"):
        lab = ed.label(r)
        if lab.startswith("WP_"):
            groups.setdefault(re.sub(r"_\d+$", "", lab), []).append((lab, ed.xform(r)[0]))
    return {k: [p for _, p in sorted(v)] for k, v in groups.items()}


def lane_dist(p, pts):
    return math.dist(p, pts[0]) if len(pts) == 1 else poly_dist(p, pts)


def box_dist2d(p, lo, hi):
    dx = max(lo[0] - p[0], 0.0, p[0] - hi[0])
    dy = max(lo[1] - p[1], 0.0, p[1] - hi[1])
    return math.hypot(dx, dy)


def creature_clearances(ed):
    """The geometric promises of the D-112 table, computed from the live level (walk paths, AI points, Perim_* walls) and the constants above."""
    existing = [(lab, loc) for lab, loc, _, _ in EMITTERS]

    def min_existing(p):
        lab, loc = min(existing, key=lambda e: math.dist(p, e[1]))
        return math.dist(p, loc), lab

    def pair_min(items):
        return min(math.dist(a[1], b[1]) for i, a in enumerate(items) for b in items[i + 1:])

    belfry = [(t, l) for t, l, _ in BATS if t.startswith("B")]
    t1 = [l for t, l, _ in BATS if t == "T1"][0]
    for tag, loc in belfry:
        bell, ex = math.dist(loc, BELL), min_existing(loc)
        inside = BELFRY_INT[0][0] <= loc[0] <= BELFRY_INT[1][0] and BELFRY_INT[0][1] <= loc[1] <= BELFRY_INT[1][1]
        rec(3300.0 <= loc[2] <= 3600.0 and bell >= 600.0 and ex[0] >= 400.0 and inside,
            "Bat %s %s: z %.0f (3300..3600), bell %.0f cm (>=600), nearest existing emitter %.0f cm %s (>=400), inside the belfry walls %s" % (tag, rnd(loc, 1), loc[2], bell, ex[0], ex[1], inside))
    rec(pair_min(belfry) >= 300.0, "Bats B1..B3 are %.0f cm apart at the least (>=300)" % pair_min(belfry))
    ex = min_existing(t1)
    face = min(t1[0] - CORE[0][0], CORE[1][0] - t1[0], t1[1] - CORE[0][1], CORE[1][1] - t1[1])
    rec(2400.0 <= t1[2] < 2500.0 and face > 0 and ex[0] >= 400.0,
        "Bat T1 %s: just below the belfry floor (z %.0f < 2500), inside the Tw_Core footprint (%.0f cm from the nearest face), nearest existing emitter %.0f cm %s (>=400)" % (rnd(t1, 1), t1[2], face, ex[0], ex[1]))
    owls = [(t, l) for t, l, _ in OWLS]
    for tag, loc in owls:
        ex = min_existing(loc)
        rec(600.0 <= loc[2] <= 900.0 and ex[0] >= 400.0, "Owl %s %s: z %.0f (600..900), nearest existing emitter %.0f cm (>=400)" % (tag, rnd(loc, 1), loc[2], ex[0]))
    rec(pair_min(owls) >= 1500.0, "Owls are %.0f cm apart at the least (>=1500)" % pair_min(owls))
    pb = [ed.bounds(ed.find_one(n, must=True)) for n in ("Perim_W", "Perim_E", "Perim_S", "Perim_N")]
    lo = (min(b[0][0] for b in pb), min(b[0][1] for b in pb))
    hi = (max(b[1][0] for b in pb), max(b[1][1] for b in pb))
    info("perimeter walls hull x %.0f..%.0f, y %.0f..%.0f" % (lo[0], hi[0], lo[1], hi[1]))
    for tag, loc, _ in HOWLS:
        d = box_dist2d(loc, lo, hi)
        quadrant = (loc[0] > hi[0] and loc[1] > hi[1]) if tag == "NE" else (loc[0] < lo[0] and loc[1] < lo[1])
        rec(d >= 1000.0 and quadrant and loc[2] == 500.0, "Howl %s %s: %.0f cm beyond the perimeter hull (>=1000), %s quadrant %s, z %.0f" % (tag, rnd(loc, 1), d, tag, quadrant, loc[2]))
    lanes = all_lanes(ed)
    ai = []
    for pre in ("Patrol_Crypt_", "Search_Crypt_", "WSpawn_Crypt"):
        for r in ed.find_all(name=pre):
            if ed.label(r).startswith(pre):
                ai.append((ed.label(r), ed.xform(r)[0]))
    info("rat inputs: %d WP_ lanes (%d points), %d crypt AI points" % (len(lanes), sum(len(v) for v in lanes.values()), len(ai)))
    rats = [(t, l) for t, l, _ in RATS]
    for tag, loc in rats:
        lane_n, lane_d = min(((k, lane_dist(loc, v)) for k, v in lanes.items()), key=lambda e: e[1])
        ai_n, ai_d = min(((n, math.dist(loc, q)) for n, q in ai), key=lambda e: e[1])
        ex = min_existing(loc)
        incrypt = all(CRYPT_BOX[0][i] <= loc[i] <= CRYPT_BOX[1][i] for i in range(3))
        rec(loc[2] == -590.0 and lane_d >= 150.0 and ai_d >= 150.0 and ex[0] >= 400.0 and incrypt,
            "Rat %s %s: z %.0f, nearest walk lane %.0f cm %s (>=150), nearest AI point %.0f cm %s (>=150), nearest existing emitter %.0f cm %s (>=400), inside the Crypt zone %s" % (
                tag, rnd(loc, 1), loc[2], lane_d, lane_n, ai_d, ai_n, ex[0], ex[1], incrypt))
    rec(pair_min(rats) >= 1000.0, "Rats are %.0f cm apart at the least (different rooms, >=1000)" % pair_min(rats))


# ---------------------------------------------------------------------------------------------- 4. floors
def comp(ref):
    return ref + ".StaticMeshComponent0"


def pm_of(ed, ref):
    return R(ed.props(comp(ref), ["bodyInstance"])["bodyInstance"].get("physMaterialOverride"))


def floor_refs(ed):
    out = {}
    out.update(ed.by_labels("Tw_Landing_", WOOD))
    out.update(ed.by_labels("Stair_F", WOOD))
    out.update(ed.by_labels("Top_Slab_", WOOD))
    g = ed.find_one("Garth")
    if g:
        out["Garth"] = g
    out.update(ed.by_labels("Garden_Earth_", EARTH))
    return out


def apply_floors(ed):
    refs = floor_refs(ed)
    skipped = []
    for surf, labels in FLOOR_GROUPS:
        n = 0
        for lab in labels:
            ref = refs.get(lab)
            if not ref:
                skipped.append((lab, "actor not found"))
                continue
            try:
                if pm_of(ed, ref) != PM[surf]:
                    ed.setp(comp(ref), {"bodyInstance": {"physMaterialOverride": {"refPath": PM[surf]}}})
                if pm_of(ed, ref) != PM[surf]:
                    skipped.append((lab, "override did not read back"))
                else:
                    n += 1
            except RuntimeError as e:
                skipped.append((lab, str(e)[:120]))
        info("%s: %d of %d actors carry PM_LB_%s" % (surf, n, len(labels), surf))
    for lab, why in skipped:
        info("SKIPPED %s: %s" % (lab, why))


def check_floors(ed):
    refs = floor_refs(ed)
    for surf, labels in FLOOR_GROUPS:
        bad, missing = [], []
        for lab in labels:
            ref = refs.get(lab)
            if not ref:
                missing.append(lab)
                continue
            if pm_of(ed, ref) != PM[surf]:
                bad.append(lab)
        rec(not bad and not missing, "%s: %d actors carry PM_LB_%s (missing %s, wrong %s)" % (surf, len(labels) - len(bad) - len(missing), surf, missing[:5], bad[:5]))
    stone = {}
    for lab in STONE_SAMPLE:
        ref = ed.find_one(lab)
        if ref:
            stone[lab] = pm_of(ed, ref)
    rec(stone and all(v is None for v in stone.values()), "stone floors keep the default (no override): %s" % {k: (v or "None") for k, v in stone.items()})


# ---------------------------------------------------------------------------------------------- 5. water pads
def shell_top(ed, x, y):
    """Top Z of the CryptFloor_* shell that contains (x, y)."""
    best = None
    for i in range(4):
        r = ed.find_one("CryptFloor_%d" % i, must=True)
        b = ed.bounds(r)
        if b[0][0] <= x <= b[1][0] and b[0][1] <= y <= b[1][1]:
            best = b[1][2] if best is None else max(best, b[1][2])
    if best is None:
        raise RuntimeError("no CryptFloor shell under (%s, %s)" % (x, y))
    return best


def pad_plan(ed, src):
    """Centre, scale and Z range of the pad under the pool plane `src`."""
    b = ed.bounds(ed.find_one(src, must=True))
    cx, cy = (b[0][0] + b[1][0]) / 2.0, (b[0][1] + b[1][1]) / 2.0
    sx, sy = b[1][0] - b[0][0], b[1][1] - b[0][1]
    top = shell_top(ed, cx, cy) + PAD_ABOVE
    z0, z1 = top - PAD_THICK, top
    return (cx, cy, (z0 + z1) / 2.0), (sx / 100.0, sy / 100.0, PAD_THICK / 100.0), (z0, z1), (b[0][:2], b[1][:2])


def pad_responses(entries):
    return {e["channel"]: e["response"] for e in entries}


def apply_water(ed):
    for label, src in PADS:
        loc, sc, zr, xy = pad_plan(ed, src)
        ref, created = ed.get_or_create_asset(CUBE, label, loc, (0, 0, 0), sc)
        ed.set_xform(ref, loc, (0, 0, 0), sc)
        c = comp(ref)
        ed.setp(c, {"bHiddenInGame": True, "castShadow": False, "bCastDynamicShadow": False, "bCanEverAffectNavigation": False})
        ed.setp(c, {"bUseDefaultCollision": False})
        ed.setp(c, {"bodyInstance": {"collisionProfileName": "Custom"}})
        ed.setp(c, {"bodyInstance": {"collisionEnabled": "QueryOnly", "objectType": "ECC_WorldStatic"}})
        cur = ed.props(c, ["bodyInstance"])["bodyInstance"]["collisionResponses"]["responseArray"]
        want = [{"channel": ch, "response": rs} for ch, rs in PAD_RESPONSES]
        if cur != want:
            if cur and len(cur) != len(want):
                ed.setp(c, {"bodyInstance": {"collisionResponses": {"responseArray": []}}})     # shrink to empty first (an array may not change element and size in one call)
            ed.setp(c, {"bodyInstance": {"collisionResponses": {"responseArray": want}}})
        ed.setp(c, {"bodyInstance": {"physMaterialOverride": {"refPath": PM["Water"]}}})
        info("%s %s over %s: centre %s scale %s Z %.1f..%.1f XY %s..%s" % (label, "created" if created else "updated", src, rnd(loc, 2), rnd(sc, 4), zr[0], zr[1], rnd(xy[0], 1), rnd(xy[1], 1)))


def check_water(ed):
    fs = ed.folder_actors()
    want_resp = dict(PAD_RESPONSES)
    for label, src in PADS:
        ref = ed.find_one(label)
        if not ref:
            rec(False, "%s exists" % label)
            continue
        loc, sc_want, zr, xy = pad_plan(ed, src)
        l, r, s = ed.xform(ref)
        b = ed.bounds(ref)
        p = ed.props(comp(ref), ["staticMesh", "bHiddenInGame", "castShadow", "bCastDynamicShadow", "bCanEverAffectNavigation", "bUseDefaultCollision", "bodyInstance"])
        bi = p["bodyInstance"]
        resp = pad_responses(bi["collisionResponses"]["responseArray"])
        geo = (near(l, loc, 0.01) and near(r, (0, 0, 0), 1e-4) and near(s, sc_want, 1e-4) and near(b[0][:2], xy[0], 0.2) and near(b[1][:2], xy[1], 0.2)
               and close(b[0][2], zr[0], 0.05) and close(b[1][2], zr[1], 0.05))
        rec(geo and R(p["staticMesh"]) == CUBE, "%s geometry: bounds %s..%s (want XY %s..%s, Z %.1f..%.1f: top = shell top %.1f + %.1f, thickness %.1f) mesh %s" % (
            label, rnd(b[0], 2), rnd(b[1], 2), rnd(xy[0], 1), rnd(xy[1], 1), zr[0], zr[1], zr[1] - PAD_ABOVE, PAD_ABOVE, zr[1] - zr[0], (R(p["staticMesh"]) or "None").rsplit(".", 1)[-1]))
        flags = (bool(p["bHiddenInGame"]) and not p["castShadow"] and not p["bCastDynamicShadow"] and not p["bCanEverAffectNavigation"])
        rec(flags and ref in fs and ed.class_of(ref) == "/Script/Engine.StaticMeshActor",
            "%s flags: hidden in game %s, cast shadow %s/%s, affects navigation %s, folder %s" % (
                label, p["bHiddenInGame"], p["castShadow"], p["bCastDynamicShadow"], p["bCanEverAffectNavigation"], FOLDER if ref in fs else "NOT-IN-FOLDER"))
        col = (not p["bUseDefaultCollision"] and bi["collisionProfileName"] == "Custom" and bi["collisionEnabled"] == "QueryOnly" and bi["objectType"] == "ECC_WorldStatic"
               and resp == want_resp and len(bi["collisionResponses"]["responseArray"]) == len(PAD_RESPONSES))
        rec(col and R(bi["physMaterialOverride"]) == PM["Water"],
            "%s collision: profile %s, %s, object type %s; Visibility %s, Pawn %s, Camera %s, Interaction(GameTraceChannel2) %s, others %s; physical material %s" % (
                label, bi["collisionProfileName"], bi["collisionEnabled"], bi["objectType"], resp.get("Visibility"), resp.get("Pawn"), resp.get("Camera"), resp.get("Interaction"),
                sorted(set(v for k, v in resp.items() if k not in ("Visibility",))), (R(bi["physMaterialOverride"]) or "None").rsplit(".", 1)[-1]))
        rec(resp.get("Pawn") == "ECR_Ignore" and resp.get("Camera") == "ECR_Ignore" and resp.get("Interaction") == "ECR_Ignore" and resp.get("Visibility") == "ECR_Block",
            "%s: the player can walk through it (Pawn ignored) and the footstep trace (Visibility) hits it; interaction and camera traces pass" % label)
    # the pads must not have been mistaken for something else: exactly three AUD_Water_* actors
    n = len([r for r in ed.find_all(name="AUD_Water_") if ed.label(r).startswith("AUD_Water_")])
    rec(n == 3, "exactly three AUD_Water_* actors (%d)" % n)


# ---------------------------------------------------------------------------------------------- census, dirty state, save
def census(ed):
    return len(ed.find_all())


def check_census(ed, start):
    n = census(ed)
    rec(n == start + NEW_ACTORS, "actor census %d (start %d + %d = %d)" % (n, start, NEW_ACTORS, start + NEW_ACTORS))
    fa = ed.folder_actors()
    rec(len(fa) == NEW_ACTORS, "%d actors in the outliner folder %s (expected %d)" % (len(fa), FOLDER, NEW_ACTORS))
    labels = [ed.label(r) for r in fa]
    rec(sum(1 for x in labels if x.startswith("AUD_Zone_")) == 7 and sum(1 for x in labels if x.startswith("AUD_Vol_")) == 7
        and sum(1 for x in labels if x.startswith("AUD_Emit_")) == 31 and sum(1 for x in labels if x.startswith("AUD_Water_")) == 3
        and sum(1 for k in ("Bat", "Owl", "Howl", "Rat") for x in labels if x.startswith("AUD_Emit_%s_" % k)) == 13,
        "folder content: 7 zones, 7 volumes, 31 emitters (18 + 13 creatures: 4 bats, 3 owls, 2 howls, 4 rats), 3 water pads")
    return n


def audio_assets(ed):
    out = []
    for folder in ("/Game/LastBell/Audio", "/Game/LastBell/Physics"):
        out += [R(x) if not isinstance(x, str) else x for x in ed.call(AS, "find_assets", {"folder_path": folder, "name": ""}) or []]
    out += ["/Game/LastBell/Data/DA_Audio", "/Game/LastBell/Data/DT_Footsteps"]
    return sorted(set(x.split(".")[0] for x in out))


def check_dirty(ed):
    info("%s is_dirty = %s" % (MAP_PKG, ed.is_dirty(MAP_PKG)))
    for pkg in NEVER_SAVE:
        rec(not ed.is_dirty(pkg), "%s is not dirty (never-save list)" % pkg.rsplit("/", 1)[-1])
    assets = audio_assets(ed)
    dirty = [a for a in assets if ed.is_dirty(a)]
    rec(not dirty, "%d audio packages (Audio/**, Physics/PM_LB_*, DA_Audio, DT_Footsteps) none dirty %s" % (len(assets), dirty[:5]))


def do_save(ed, start):
    print("=== save: full check first", flush=True)
    for s in STEPS:
        CHECK[s](ed)
    n = check_census(ed, start)
    check_dirty(ed)
    fails = [m for ok, m in results if not ok]
    if fails or n != start + NEW_ACTORS:
        print("REFUSED: the check is not all PASS or the census is wrong; nothing saved")
        return False
    r = ed.call(AS, "save_assets", {"asset_paths": [MAP_PKG]})
    d = ed.is_dirty(MAP_PKG)
    rec(d is False, "saved %s (save_assets -> %s); is_dirty after = %s" % (MAP_PKG, r, d))
    for pkg in NEVER_SAVE:
        rec(not ed.is_dirty(pkg), "%s still not dirty" % pkg.rsplit("/", 1)[-1])
    assets = audio_assets(ed)
    dirty = [a for a in assets if ed.is_dirty(a)]
    rec(not dirty, "%d audio packages still not dirty %s" % (len(assets), dirty[:5]))
    return True


def do_reload_check(ed, start):
    if ed.is_dirty(MAP_PKG):
        print("REFUSED: the map is dirty; save it first (--save)")
        return
    info("load_level %s (reloads the map from disk)" % MAP_PKG)
    ed.call(S, "load_level", {"level_path": MAP_PKG})
    lvl = str(ed.call(S, "get_current_level", {}))
    rec(lvl.startswith(MAP_PKG), "current level after the reload: %s" % lvl)
    for s in STEPS:
        print("=== check %s (after reload)" % s, flush=True)
        CHECK[s](ed)
    check_census(ed, start)
    check_dirty(ed)


STEPS = ["zones", "volumes", "emitters", "floors", "water", "creatures"]
APPLY = {"zones": apply_zones, "volumes": apply_volumes, "emitters": apply_emitters, "floors": apply_floors, "water": apply_water, "creatures": apply_creatures}
CHECK = {"zones": check_zones, "volumes": check_volumes, "emitters": check_emitters, "floors": check_floors, "water": check_water, "creatures": check_creatures}


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--apply", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--save", action="store_true")
    g.add_argument("--reload-check", action="store_true")
    ap.add_argument("--only", default="", help="comma list of: " + ",".join(STEPS))
    ap.add_argument("--start", type=int, default=CENSUS_START, help="actor count before P16-3 (3054); the final state is start + 48 = 3102 (3089 before the P16-6 creatures)")
    ap.add_argument("--resume", action="store_true", help="--apply: skip the census-is-3054 guard (continue a partial run, or add the creatures to the 3089 map)")
    a = ap.parse_args()
    steps = [s for s in STEPS if not a.only or s in a.only.split(",")]
    bad = [s for s in a.only.split(",") if s and s not in STEPS]
    if bad:
        sys.exit("unknown step(s): %s" % bad)
    try:
        ed = Ed()
        if ed.call(E, "IsPIERunning"):
            sys.exit("PIE is running: stop it first (spawned actors would go to the PIE world)")
        lvl = str(ed.call(S, "get_current_level", {}))
        if not lvl.startswith(MAP_PKG):
            sys.exit("the editor is on %s, not L_Monastery" % lvl)
        dirty0 = ed.is_dirty(MAP_PKG)
        n0 = census(ed)
        info("preflight: PIE off; %s is_dirty = %s; actor census = %d" % (MAP_PKG, dirty0, n0))
        if a.apply:
            if n0 != a.start and not a.resume:
                print("STOP: the census is %d, not %d. Nothing applied. (Use --resume only to continue a run of this script.)" % (n0, a.start))
                sys.exit(2)
            for s in steps:
                print("=== apply %s" % s, flush=True)
                APPLY[s](ed)
            print("=== verifying", flush=True)
            for s in steps:
                print("=== check %s" % s, flush=True)
                CHECK[s](ed)
            info("census after apply: %d (start %d + %d = %d); map is_dirty: %s" % (census(ed), a.start, NEW_ACTORS, a.start + NEW_ACTORS, ed.is_dirty(MAP_PKG)))
        elif a.check:
            for s in steps:
                print("=== check %s" % s, flush=True)
                CHECK[s](ed)
            if not a.only:
                check_census(ed, a.start)
                check_dirty(ed)
        elif a.save:
            do_save(ed, a.start)
        else:
            do_reload_check(ed, a.start)
        info("%d editor calls" % ed.calls)
    except EditorStop as e:
        print("STOP: editor problem (%s). Do NOT save. Restart the editor if it crashed, then run --apply --resume again." % e)
        sys.exit(3)
    fails = [m for ok, m in results if not ok]
    print("\nRESULT: %d PASS, %d FAIL" % (len(results) - len(fails), len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
