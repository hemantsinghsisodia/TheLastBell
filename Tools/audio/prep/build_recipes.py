"""Authoring script for recipes.json (Phase 16, task A3). recipes.json is the source of truth for the build; this script
is how the recipes were written (slice times were picked from `survey.py` energy/onset listings and spectrograms).

  python -I Tools/audio/prep/build_recipes.py        # rewrites Tools/audio/prep/recipes.json

Per item: layers (source alias, slice t0/t1 in the SOURCE in seconds, gain_db, pitch factor, delay in the output in seconds,
hp/lp, fades, gain_env), optional post (sub, lp, hp, gain_env, tail), optional loop (length, crossfade), target loudness,
channels. See prep_recorded.py for the semantics.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS: list[dict] = []

PEAK = {"mode": "peak", "db": -3.0}
RMS = {"mode": "rms", "db": -24.0}


def L(src, t0=0.0, t1=None, pitch=1.0, gain=0.0, delay=0.0, **kw):
    d = {"src": src, "t0": t0, "t1": t1, "gain_db": gain, "pitch": pitch, "delay": delay}
    d.update(kw)
    return {k: v for k, v in d.items() if v is not None or k == "t1"}


def add(name, group, layers, channels=1, target=PEAK, post=None, loop=None, note="", **kw):
    it = {"name": name, "group": group, "channels": channels, "target": target, "layers": layers, "note": note}
    if post:
        it["post"] = post
    if loop:
        it["loop"] = loop
    it.update(kw)
    ITEMS.append(it)


def numbered(base, n, i):
    return f"{base}_{i:02d}"


# ------------------------------------------------------------------------------------------------ player steps
def kenney_steps(surface, files, sixth_src, max_len=None, fade_out=0.03):
    # Kenney's 5 variants are near-identical waveforms (xcorr 0.93-0.99), so each gets a small pitch offset to spread them
    spread = [1.0, 0.97, 1.03, 0.985, 1.015]
    for i, f in enumerate(files, 1):
        pf = spread[i - 1]
        add(f"SFX_LB_Step_{surface}_{i:02d}", "steps", [L(f, 0.0, None, pitch=pf, hp=60.0)], max_len=max_len, fade_out=fade_out,
            note=f"Kenney {f}" + (f", pitch {100*(pf-1):+.1f} %" if pf != 1.0 else ""))
    add(f"SFX_LB_Step_{surface}_06", "steps", [L(sixth_src, 0.0, None, pitch=0.95, hp=60.0)], max_len=max_len,
        fade_out=fade_out, note=f"6th variant: {sixth_src} pitch-shifted -5 % (Kenney has only 5)")


kenney_steps("Stone", [f"ki:footstep_concrete_{i:03d}" for i in range(5)], "ki:footstep_concrete_002")
kenney_steps("Wood", [f"ki:footstep_wood_{i:03d}" for i in range(5)], "ki:footstep_wood_001")
kenney_steps("Grass", [f"ki:footstep_grass_{i:03d}" for i in range(5)], "ki:footstep_grass_002", max_len=0.6, fade_out=0.08)
# Earth: the 6 darkest (lowest centroid / least energy above 4 kHz) of the 10 RPG-Audio boot steps
for i, f in enumerate(["kr:footstep09", "kr:footstep04", "kr:footstep02", "kr:footstep00", "kr:footstep01", "kr:footstep06"], 1):
    add(f"SFX_LB_Step_Earth_{i:02d}", "steps", [L(f, 0.0, None, hp=60.0)],
        note=f"Kenney RPG {f}: chosen as the dullest (most earth-like) 6 of footstep00..09; confirm by ear")
# Water: puddle steps (531566) + the single splash step 849638
for i, t in enumerate([2.665, 5.435, 6.23, 8.015, 9.295], 1):
    add(f"SFX_LB_Step_Water_{i:02d}", "steps", [L("fs:531566", t, t + 0.5, hp=80.0)], max_len=0.5, note=f"531566 puddle step @ {t}s")
add("SFX_LB_Step_Water_06", "steps", [L("fs:849638", 0.07, 0.36, hp=80.0)], note="849638 step_water (single step, 0.3 s)")
# Metal: 698697 grate steps
for i, t in enumerate([1.505, 3.01, 4.53, 6.025, 7.485, 9.01], 1):
    add(f"SFX_LB_Step_Metal_{i:02d}", "steps", [L("fs:698697", t - 0.03, t + 0.5, hp=80.0)], max_len=0.5, fade_out=0.06,
        note=f"698697 metal step @ {t}s")

# ------------------------------------------------------------------------------------------------ player breath / candle / paper / key
PB = {"hp": 90.0}
for i, (a, b) in enumerate([(2.25, 4.5), (6.2, 8.0), (11.25, 12.8), (20.5, 22.1)], 1):
    add(f"SFX_LB_Breath_Calm_{i:02d}", "player", [L("fs:336532", a, b, **PB)], fade_in=0.08, fade_out=0.15,
        note=f"336532 calm breath @ {a}-{b}s, mono-centred (2D)")
for i, (a, b) in enumerate([(0.33, 1.95), (1.95, 3.55), (3.55, 5.15), (5.15, 6.7)], 1):
    add(f"SFX_LB_Breath_Heavy_{i:02d}", "player", [L("fs:386573", a, b, **PB)], fade_in=0.03, fade_out=0.1,
        note=f"386573 panting, 4 pulses @ {a}-{b}s")
for i, (a, b) in enumerate([(0.5, 2.2), (2.6, 4.4), (13.5, 15.3), (15.5, 17.4)], 1):
    add(f"SFX_LB_Breath_Panic_{i:02d}", "player", [L("fs:831389", a, b, **PB)], fade_in=0.03, fade_out=0.1,
        note=f"831389 exhausted/panicked breathing @ {a}-{b}s")
add("SFX_LB_Breath_Gasp_01", "player", [L("fs:271245", 0.0, 0.58, **PB)], note="271245 gasp (single source)")
add("SFX_LB_Breath_Gasp_02", "player", [L("fs:271245", 0.0, 0.58, pitch=0.93, **PB)], note="271245 pitch -7 % (only one gasp source)")
add("SFX_LB_Breath_Gasp_03", "player", [L("fs:271245", 0.0, 0.58, pitch=1.07, **PB)], note="271245 pitch +7 % (only one gasp source)")

add("SFX_LB_Candle_Light_01", "player", [L("fs:423811", 0.0, 1.0)], note="423811 match strike 03")
add("SFX_LB_Candle_Light_02", "player", [L("fs:237390", 0.0, 0.3), L("fs:386385", 0.1, 0.5, gain=-8.0, delay=0.12)],
    note="237390 match strike (dry, only 0.3 s of sound) + 386385 flame whoosh at -8 dB so it is not a bare click")
add("SFX_LB_Candle_Light_03", "player", [L("fs:398448", 0.0, 0.75)], note="398448 match ignite")
add("SFX_LB_Candle_Out_01", "player", [L("fs:242867", 0.1, 0.8)], note="242867 blow out")
add("SFX_LB_Candle_Out_02", "player", [L("fs:406648", 2.15, 2.9)], note="406648 airy blow out (very quiet source, clean)")
add("SFX_LB_Candle_Out_03", "player", [L("fs:656818", 1.2, 2.3)], note="656818 candle blow")
add("SFX_LB_Candle_Relight", "player", [L("fs:386385", 0.0, 0.6)], note="386385 soft torch ignite whoosh")

add("SFX_LB_Key_Pickup_01", "player", [L("fs:788310", 0.2, 0.85)], note="788310 key pickup")
add("SFX_LB_Key_Pickup_02", "player", [L("fs:248037", 0.38, 1.05)], note="248037 keys pickup")
add("SFX_LB_Paper_01", "player", [L("fs:353125", 0.18, 1.1)], channels=2, note="353125 paper rustle (stereo)")
add("SFX_LB_Paper_02", "player", [L("fs:181774", 0.35, 1.9)], channels=2, fade_out=0.08, note="181774 rustling paper (stereo)")
add("SFX_LB_Paper_03", "player", [L("fs:449127", 5.6, 6.4)], channels=2, fade_out=0.08, note="449127 rustling paper (stereo)")

# ------------------------------------------------------------------------------------------------ interactions
add("SFX_LB_Door_Wood_Open_01", "interact", [L("fs:402464", 0.15, 2.95)], fade_out=0.12, note="402464 wooden door opening")
add("SFX_LB_Door_Wood_Open_02", "interact", [L("fs:273466", 0.0, 3.0)], fade_out=0.12, note="273466 big door creak")
add("SFX_LB_Door_Wood_Open_03", "interact", [L("fs:273466", 1.4, 4.45, pitch=1.05)], fade_out=0.12,
    note="273466 later part, pitch +5 % (two sources give only 2 distinct openings)")
add("SFX_LB_Door_Stone_Open_01", "interact", [L("fs:578491", 0.7, 3.7, hp=40.0)], fade_in=0.02, fade_out=0.2, note="578491 stone door")
add("SFX_LB_Door_Stone_Open_02", "interact", [L("fs:578491", 7.55, 10.5, hp=40.0)], fade_in=0.02, fade_out=0.2, note="578491 stone door")
add("SFX_LB_Door_Stone_Open_03", "interact", [L("fs:833925", 0.2, 3.2, hp=40.0)], fade_in=0.02, fade_out=0.2, note="833925 stone door (noisy source)")
add("SFX_LB_Door_Locked_01", "interact", [L("fs:341303", 0.05, 1.15)], note="341303 door locked")
add("SFX_LB_Door_Locked_02", "interact", [L("fs:235473", 2.3, 3.35)], fade_out=0.08, note="235473 handle rattle #2")
add("SFX_LB_Door_Locked_03", "interact", [L("fs:235473", 3.75, 4.95)], fade_out=0.08, note="235473 handle rattle #3")

add("SFX_LB_Lever_Notch_01", "interact", [L("fs:696746", 0.0, 0.58)], note="696746 lever")
add("SFX_LB_Lever_Notch_02", "interact", [L("fs:835550", 0.04, 0.95)], note="835550 industrial lever")
add("SFX_LB_Lever_Notch_03", "interact", [L("kr:metalClick", 0.0, None)], note="Kenney RPG metalClick")
add("SFX_LB_Lever_Notch_04", "interact", [L("kr:metalLatch", 0.0, None), L("fs:696746", 0.0, 0.5, pitch=1.06, gain=-8.0)],
    note="Kenney RPG metalLatch + 696746 pitch +6 % at -8 dB")

add("SFX_LB_Winch_01", "interact", [L("fs:454148", 0.12, 1.0), L("fs:454148", 1.95, 3.4, delay=0.86)], fade_out=0.12,
    note="454148 two ratchet pulls joined (silent gap removed)")
add("SFX_LB_Winch_02", "interact", [L("fs:491705", 2.0, 5.2, hp=40.0)], fade_out=0.12, note="491705 rope crank take 1")
add("SFX_LB_Winch_03", "interact", [L("fs:491705", 39.0, 42.2, hp=40.0)], fade_out=0.12, note="491705 rope crank take 4")
add("SFX_LB_Stone_Grind_01", "interact", [L("fs:844329", 0.1, 3.3, hp=40.0)], fade_in=0.03, fade_out=0.2, note="844329 slab grind")
add("SFX_LB_Stone_Grind_02", "interact", [L("fs:844329", 5.05, 8.4, hp=40.0)], fade_in=0.03, fade_out=0.2, note="844329 slab grind")
add("SFX_LB_Stone_Grind_03", "interact", [L("fs:844329", 9.8, 13.0, hp=40.0)], fade_in=0.03, fade_out=0.2, note="844329 slab grind")
for i, f in enumerate(["kr:handleSmallLeather", "kr:handleSmallLeather2", "kr:beltHandle1"], 1):
    add(f"SFX_LB_Generic_Use_{i:02d}", "interact", [L(f, 0.0, None)], note=f"Kenney RPG {f}")

# ------------------------------------------------------------------------------------------------ room emitters
add("SFX_LB_Creak_Wood_01", "room", [L("fs:506665", 0.0, 1.19, hp=60.0)], fade_out=0.08, note="506665 single wood creak")
add("SFX_LB_Creak_Wood_02", "room", [L("fs:802595", 0.05, 2.5, hp=60.0)], fade_out=0.12, note="802595 long slow floorboards")
add("SFX_LB_Creak_Wood_03", "room", [L("kr:creak2", 0.0, None, hp=60.0)], fade_out=0.08, note="Kenney RPG creak2 (802595 has only one usable long creak)")
add("SFX_LB_Creak_Wood_04", "room", [L("fs:590171", 0.0, 1.95, hp=60.0)], fade_out=0.12, note="590171 creaking in room")
add("SFX_LB_Creak_Wood_05", "room", [L("fs:402464", 1.05, 2.45, hp=60.0)], fade_out=0.1, note="402464 creak part of the wooden door (second source)")
add("SFX_LB_Chain_Distant_01", "room", [L("fs:167912", 0.0, 1.5)], fade_out=0.12, note="167912 chain dragged, hard reverb")
add("SFX_LB_Chain_Distant_02", "room", [L("fs:167914", 0.0, 1.4)], fade_out=0.12, note="167914 chain dragged, shower reverb")
DIST = {"lp": 2800.0, "hp": 120.0}
add("SFX_LB_Chain_Distant_03", "room", [L("fs:455078", 4.5, 5.45, pitch=0.9, **DIST)], fade_out=0.12,
    post={"tail": {"rt60": 1.4, "wet_db": -9.0, "predelay": 0.03, "lp": 2500.0, "tail_s": 1.0}}, max_len=3.0,
    note="455078 chain drag (Warden-chain source) darkened + long tail to read as distant")
add("SFX_LB_Chain_Distant_04", "room", [L("fs:199282", 9.0, 10.4, pitch=0.9, **DIST)], fade_out=0.12,
    post={"tail": {"rt60": 1.4, "wet_db": -9.0, "predelay": 0.03, "lp": 2500.0, "tail_s": 1.0, "seed": 9}}, max_len=3.0,
    note="199282 chain jangle darkened + long tail to read as distant")

# ------------------------------------------------------------------------------------------------ Warden
SUB = {"freq": 50.0, "gain_db": -12.0}
STEP_ONSETS = [2.14, 2.685, 1.525, 6.88, 8.495]
THUMPS = ["ki:impactSoft_heavy_000", "ki:impactPunch_heavy_001", "ki:impactWood_heavy_003", "ki:impactPunch_heavy_003", "ki:impactSoft_heavy_002"]
EXTRA = [None, None, ("fs:531725", 0.5, 1.0, 250.0), ("fs:339439", 0.55, 1.1, 300.0), ("fs:339439", 1.9, 2.5, 300.0)]
for i in range(5):
    t = STEP_ONSETS[i]
    layers = [L("fs:741627", t - 0.03, t + 0.5, pitch=0.7, hp=50.0),
              L(THUMPS[i], 0.0, None, pitch=0.72, gain=-3.0, delay=0.03 / 0.7, hp=30.0)]
    if EXTRA[i]:
        s, a, b, lp = EXTRA[i]
        layers.append(L(s, a, b, pitch=0.8, gain=-4.0, delay=0.0, hp=25.0, lp=lp))
    add(f"SFX_LB_Warden_Step_{i+1:02d}", "warden", layers, post={"sub": SUB, "lp": 7000.0}, max_len=0.9, fade_out=0.08,
        note="741627 boot step -30 % + Kenney heavy thump" + (f" + {EXTRA[i][0]} sub body (lowpassed)" if EXTRA[i] else "") + " + 50 Hz sub")
for i, (s, a, b, p) in enumerate([("fs:455078", 6.25, 7.55, 0.92), ("fs:455078", 9.98, 11.4, 0.92), ("fs:199282", 20.0, 21.3, 0.92),
                                  ("fs:199282", 48.75, 50.1, 0.88)], 1):
    add(f"SFX_LB_Warden_Chain_{i:02d}", "warden", [L(s, a, b, pitch=p, hp=80.0)], fade_out=0.1, note=f"{s} @ {a}-{b}s, pitch {p}")

# robe: 11 s timeline of cloth pieces + dull drag bed, lowpassed (cloth on stone), looped with a 1 s crossfade
XF = {"fade_in": 0.3, "fade_out": 0.3}
robe = [
    L("fs:19291", 0.45, 1.95, 1.0, 0.0, 0.0, lp=3500.0, **XF),
    L("kr:cloth2", 0.0, None, 0.85, -2.0, 1.4, lp=3500.0, **XF),
    L("fs:19291", 0.45, 1.95, 0.9, -1.0, 2.2, lp=3500.0, reverse=True, **XF),
    L("kr:cloth4", 0.0, None, 0.8, -2.0, 3.9, lp=3500.0, **XF),
    L("fs:19291", 0.45, 1.95, 1.08, -2.0, 4.6, lp=3500.0, **XF),
    L("kr:cloth1", 0.0, None, 0.85, -2.0, 6.2, lp=3500.0, **XF),
    L("fs:19291", 0.45, 1.95, 0.95, -1.0, 6.9, lp=3500.0, reverse=True, **XF),
    L("kr:cloth3", 0.0, None, 0.8, -2.0, 8.5, lp=3500.0, **XF),
    L("fs:19291", 0.45, 1.95, 1.02, -2.0, 9.4, lp=3500.0, **XF),
    L("kr:cloth2", 0.0, None, 0.9, -3.0, 10.9, lp=3500.0, **XF),
    {"synth": "noise", "dur": 12.0, "lo": 150.0, "hi": 1200.0, "gain_db": -46.0, "seed": 3, "delay": 0.0},
]
add("SFX_LB_Warden_Robe", "warden", robe, target=RMS, loop={"length": 10.0, "xf": 1.0}, post={"level": {"win": 0.3, "alpha": 0.9}},
    note="19291 cloth rustle (forward, reversed, pitched) + Kenney cloth1..4 + a dull noise drag bed; 10 s loop")

# breath loops
add("SFX_LB_Warden_Breath_Slow", "warden", [L("fs:574208", 25.0, 33.3, pitch=0.75, hp=40.0, fade_in=0.0, fade_out=0.0)], target=RMS,
    loop={"length": 10.0, "xf": 1.0}, tune={"t0_min": 0.3, "t0_max": 34.0, "src_len": 8.3, "step": 0.1},
    note="574208 monster breath, pitch -25 %, 10 s loop")
add("SFX_LB_Warden_Breath_Fast", "warden", [L("fs:689240", 1.6, 8.85, pitch=0.8, hp=40.0, fade_in=0.0, fade_out=0.0)], target=RMS,
    loop={"length": 8.0, "xf": 1.0}, tune={"t0_min": 0.9, "t0_max": 2.8, "src_len": 7.25, "step": 0.05},
    note="689240 loud snorting breath (early, slower part), pitch -20 %, 8 s loop")
add("SFX_LB_Warden_Breath_Heavy", "warden",
    [L("fs:689240", 3.0, 12.4, pitch=0.8, hp=40.0, fade_in=0.0, fade_out=0.0),
     L("fs:470900", 2.3, 11.4, pitch=0.78, gain=-6.0, hp=40.0, fade_in=0.0, fade_out=0.0, norm=-24.0)], target=RMS,
    loop={"length": 10.0, "xf": 1.5}, tune={"layer": 1, "t0_min": 0.0, "t0_max": 9.0, "src_len": 9.1, "step": 0.1},
    note="689240 loud fast snorting (late, accelerating part, pitch -20 %) over 470900 growling breath (pitch -22 %, -6 dB), 10 s loop")

# ------------------------------------------------------------------------------------------------ Warden voice tells
def tail(rt60, wet=-15.0, tail_s=0.4, pre=0.015):
    return {"rt60": rt60, "wet_db": wet, "tail_s": tail_s, "predelay": pre, "lp": 3200.0}


V = dict(hp=50.0)
add("SFX_LB_Warden_Spotted_01", "voice", [L("fs:132874", 0.25, 1.1, pitch=0.72, norm=-18.0, fade_out=0.1, **V),
                                          L("fs:487513", 0.06, 0.9, pitch=0.75, gain=-4.0, norm=-18.0, fade_out=0.1, **V)],
    post={"sub": SUB, "tail": tail(0.5, -16.0, 0.25)}, max_len=1.45, fade_out=0.08, note="132874 + 487513 roars, -28 %, sub, short room tail")
add("SFX_LB_Warden_Spotted_02", "voice", [L("fs:487513", 0.06, 1.0, pitch=0.72, norm=-18.0, fade_out=0.1, **V),
                                          L("fs:204912", 0.13, 0.9, pitch=0.78, gain=-3.0, norm=-18.0, fade_out=0.1, **V)],
    post={"sub": SUB, "tail": tail(0.5, -16.0, 0.25)}, max_len=1.45, fade_out=0.08, note="487513 + 204912, -26 %, sub, tail")
add("SFX_LB_Warden_Spotted_03", "voice", [L("fs:132874", 0.25, 1.1, pitch=0.66, norm=-18.0, fade_out=0.1, **V),
                                          L("fs:497056", 0.2, 0.95, pitch=0.75, gain=-3.0, norm=-18.0, fade_out=0.1, **V)],
    post={"sub": SUB, "tail": tail(0.5, -16.0, 0.25)}, max_len=1.45, fade_out=0.08, note="132874 -34 % + 497056 -25 %, sub, tail")
add("SFX_LB_Warden_Roar_01", "voice", [L("fs:497056", 0.2, 2.1, pitch=0.75, norm=-18.0, fade_out=0.3, **V),
                                       L("fs:204912", 0.13, 1.9, pitch=0.72, gain=-4.0, norm=-18.0, fade_out=0.3, delay=0.05, **V)],
    post={"sub": SUB, "tail": tail(0.9, -15.0, 0.4)}, max_len=3.0, fade_out=0.15, note="497056 + 204912, -25 %, sub, tail")
add("SFX_LB_Warden_Roar_02", "voice", [L("fs:204912", 0.13, 2.0, pitch=0.72, norm=-18.0, fade_out=0.3, **V),
                                       L("fs:487513", 0.07, 1.9, pitch=0.7, gain=-3.0, norm=-18.0, fade_out=0.3, delay=0.08, **V)],
    post={"sub": SUB, "tail": tail(0.9, -15.0, 0.4)}, max_len=3.0, fade_out=0.15, note="204912 + 487513, -28 %, sub, tail")
add("SFX_LB_Warden_Roar_03", "voice", [L("fs:170454", 0.85, 2.1, pitch=0.78, norm=-18.0, fade_out=0.3, **V),
                                       L("fs:497056", 0.9, 2.9, pitch=0.8, gain=-3.0, norm=-18.0, fade_out=0.3, delay=0.15, **V)],
    post={"sub": SUB, "tail": tail(0.9, -15.0, 0.4)}, max_len=3.0, fade_out=0.15, note="170454 angry beast + 497056, -20 %, sub, tail")

HISS = {"synth": "noise", "dur": 1.2, "lo": 1500.0, "hi": 7000.0, "gain_db": -38.0, "gain_env": [[0.0, -24.0], [1.0, 0.0]], "delay": 0.0}
RISE = [[0.0, -26.0], [0.95, 0.0]]
WSUB = {"freq": 50.0, "gain_db": -14.0}
add("SFX_LB_Warden_Windup_01", "voice", [L("fs:444445", 0.3, 1.15, gain_env=RISE, glide=[0.62, 0.85], norm=-24.0, fade_out=0.02, **V), dict(HISS, seed=11)],
    post={"sub": WSUB, "tail": tail(0.5, -17.0, 0.25)}, max_len=1.5, fade_out=0.05,
    note="444445 demon growl, pitch glide 0.62 -> 0.85 (rising), amplitude rise, noise hiss (-14 dB re growl), tail")
add("SFX_LB_Warden_Windup_02", "voice", [L("fs:389653", 0.14, 0.96, gain_env=RISE, glide=[0.68, 0.9], norm=-24.0, fade_out=0.02, **V),
                                         L("fs:444445", 0.3, 0.9, gain=-4.0, gain_env=RISE, glide=[0.6, 0.8], norm=-24.0, fade_out=0.02, **V)],
    post={"sub": WSUB, "tail": tail(0.5, -17.0, 0.25)}, max_len=1.5, fade_out=0.05,
    note="389653 growl + 444445 growl, rising glide and amplitude, tail")
add("SFX_LB_Warden_Windup_03", "voice", [L("fs:763026", 1.8, 2.9, gain_env=RISE, glide=[0.7, 0.9], norm=-24.0, fade_out=0.02, **V),
                                         L("fs:389653", 0.14, 0.96, gain=-3.0, gain_env=RISE, glide=[0.65, 0.85], norm=-24.0, fade_out=0.02, **V),
                                         dict(HISS, seed=12, gain_db=-40.0)],
    post={"sub": WSUB, "tail": tail(0.5, -17.0, 0.25)}, max_len=1.5, fade_out=0.05,
    note="763026 bear growl + 389653, rising glide and amplitude, hiss, tail")

EXH = dict(lp=5500.0, hp=40.0)
add("SFX_LB_Warden_Exhale_01", "voice", [L("fs:345730", 0.05, 0.9, pitch=0.8, norm=-26.0, fade_out=0.15, **EXH)], post={"tail": tail(0.8, -15.0, 0.5)}, max_len=2.0,
    fade_in=0.02, fade_out=0.15, note="345730 deep exhale -20 %, tail")
add("SFX_LB_Warden_Exhale_02", "voice", [L("fs:615047", 1.35, 2.85, pitch=0.8, norm=-26.0, fade_out=0.2, **EXH)], post={"tail": tail(0.8, -15.0, 0.5)}, max_len=2.4,
    fade_in=0.02, fade_out=0.15, note="615047 exhale -20 %, tail")
add("SFX_LB_Warden_Exhale_03", "voice", [L("fs:615047", 0.3, 1.15, pitch=0.78, norm=-26.0, fade_out=0.15, **EXH),
                                         L("fs:345730", 0.05, 0.9, pitch=0.7, gain=-4.0, norm=-26.0, fade_out=0.15, delay=0.1, **EXH)],
    post={"tail": tail(0.8, -15.0, 0.5)}, max_len=2.2, fade_in=0.02, fade_out=0.15, note="615047 inhale-exhale -22 % + 345730 -30 %, tail")

add("SFX_LB_Warden_Caught_01", "voice", [L("fs:763026", 1.75, 3.55, pitch=0.8, norm=-22.0, fade_out=0.3, **V),
                                         L("fs:170454", 8.4, 9.8, pitch=0.8, gain=-2.0, norm=-22.0, fade_out=0.3, delay=0.15, **V)],
    post={"sub": SUB, "tail": tail(0.9, -14.0, 0.5)}, max_len=3.0, fade_out=0.2, note="763026 bear growl + 170454 beast, -20 %, sub, tail")
add("SFX_LB_Warden_Caught_02", "voice", [L("fs:170454", 10.2, 11.65, pitch=0.78, norm=-22.0, fade_out=0.3, **V),
                                         L("fs:497056", 0.9, 2.4, pitch=0.8, gain=-3.0, norm=-22.0, fade_out=0.3, delay=0.05, **V)],
    post={"sub": SUB, "tail": tail(0.9, -14.0, 0.5)}, max_len=3.0, fade_out=0.2, note="170454 beast + 497056 roar, -20 %, sub, tail")

WH = dict(hp=120.0, lp=7500.0)
add("SFX_LB_Apparition_Whisper_01", "voice", [L("fs:316797", 2.0, 5.0, pitch=0.93, **WH)], post={"tail": tail(1.2, -12.0, 0.8, 0.02)}, max_len=4.0,
    fade_in=0.05, fade_out=0.3, note="316797 ghostly whispers -7 %, tail")
add("SFX_LB_Apparition_Whisper_02", "voice", [L("fs:339827", 1.0, 3.6, pitch=0.95, **WH)], post={"tail": tail(1.2, -12.0, 0.8, 0.02)}, max_len=4.0,
    fade_in=0.05, fade_out=0.3, note="339827 eerie whispers -5 %, tail")
add("SFX_LB_Apparition_Whisper_03", "voice", [L("fs:316797", 9.5, 12.0, pitch=0.92, **WH)], post={"tail": tail(1.2, -12.0, 0.8, 0.02)}, max_len=4.0,
    fade_in=0.05, fade_out=0.3, note="316797 ghostly whispers -8 %, tail")

if __name__ == "__main__":
    out = os.path.join(HERE, "recipes.json")
    with open(out, "w", encoding="utf8", newline="\n") as f:
        json.dump({"version": 1, "items": ITEMS}, f, indent=1)
    print(f"{len(ITEMS)} items -> {out}")
