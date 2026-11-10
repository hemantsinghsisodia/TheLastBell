"""Objective checks, spectrogram contact sheets and the audition page for the recorded cues (Phase 16, task A3).

  python -I Tools/audio/prep/report_recorded.py            # checks + Docs/ArtTest/audio/rec_<group>.png + audition_recorded.md
  python -I Tools/audio/prep/report_recorded.py --checks   # checks only

Checks per WAV: 48 kHz / 16-bit / expected channel count, no clipped samples (|s| < 32767), peak <= -1 dBFS, DC < 0.001, first/last sample
at ~0 (no boundary click), no internal click (largest sample jump vs the 99.9th percentile jump), loudness within 1 dB of target
(one-shots: peak -3 dBFS; loops: RMS -24 dBFS), loop seam (first 0.5 s vs last 0.5 s level step < 0.5 dB, wrap click ratio < 8).
Also compares the variant counts with the cue sheet (docs/plans/P16_AUDIO.md section 3).
"""
from __future__ import annotations

import json
import os
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np
from PIL import Image, ImageDraw

import prep_lib as L
from survey import spectrogram_img

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT_DIR = os.path.join(ROOT, "SourceArt", "Audio", "Recorded")
DOC_DIR = os.path.join(ROOT, "Docs", "ArtTest", "audio")

# cue sheet section 3 (Src K / F / K/F / F/K rows): name prefix -> variant count
EXPECTED = {
    "SFX_LB_Creak_Wood_": 5, "SFX_LB_Chain_Distant_": 4,
    "SFX_LB_Step_Stone_": 6, "SFX_LB_Step_Wood_": 6, "SFX_LB_Step_Earth_": 6, "SFX_LB_Step_Grass_": 6, "SFX_LB_Step_Water_": 6,
    "SFX_LB_Step_Metal_": 6, "SFX_LB_Breath_Calm_": 4, "SFX_LB_Breath_Heavy_": 4, "SFX_LB_Breath_Panic_": 4, "SFX_LB_Breath_Gasp_": 3,
    "SFX_LB_Candle_Light_": 3, "SFX_LB_Candle_Out_": 3, "SFX_LB_Candle_Relight": 1,
    "SFX_LB_Door_Wood_Open_": 3, "SFX_LB_Door_Stone_Open_": 3, "SFX_LB_Door_Locked_": 3, "SFX_LB_Lever_Notch_": 4, "SFX_LB_Winch_": 3,
    "SFX_LB_Stone_Grind_": 3, "SFX_LB_Key_Pickup_": 2, "SFX_LB_Paper_": 3, "SFX_LB_Generic_Use_": 3,
    "SFX_LB_Warden_Breath_": 3, "SFX_LB_Warden_Step_": 5, "SFX_LB_Warden_Chain_": 4, "SFX_LB_Warden_Robe": 1,
    "SFX_LB_Warden_Spotted_": 3, "SFX_LB_Warden_Roar_": 3, "SFX_LB_Warden_Windup_": 3, "SFX_LB_Warden_Exhale_": 3,
    "SFX_LB_Warden_Caught_": 2, "SFX_LB_Apparition_Whisper_": 3,
    "SFX_LB_Bat_": 6, "SFX_LB_Owl_": 4, "SFX_LB_Howl_": 3, "SFX_LB_Rat_": 5,  # P16-6 creature ambience (D-112)
}

GROUPS = [
    ("steps", "Player footsteps (36)"),
    ("player", "Player breath, candle, key, paper (33)"),
    ("interact", "Doors, levers, winch, stone grind, generic use (28)"),
    ("room", "Room emitters: wood creaks, distant chains (9)"),
    ("warden", "Warden: steps, chains, robe, breath loops (13)"),
    ("voice", "Warden voice tells and apparition whispers (17)"),
    ("creatures", "Creatures: bats, owls, far howls, rats (18; P16-6, D-112)"),
]

LISTEN = {
    "Step_Stone": "Dull, short concrete thud (Kenney is very bass-heavy; may feel muffled on speakers). Six should not sound like a machine gun. 06 is a -5 % copy of 03.",
    "Step_Wood": "Hollow wood tap, very short. 06 is a -5 % pitched copy of 02.",
    "Step_Earth": "Dirt/gravel-ish boot step. Chosen by spectrum from RPG footstep00..09: confirm it reads as earth, not wood.",
    "Step_Grass": "Soft crunch/brush, about 0.15 s. 06 is a -5 % pitched copy of 03.",
    "Step_Water": "Splashy puddle step. 06 (849638) is a single drier step; check the six sit together.",
    "Step_Metal": "Boot on a grate: ringing clank, 0.5 s. All six from one recording; check the ring does not smear at sprint cadence.",
    "Breath_Calm": "Quiet slow breath through the nose/mouth, noise floor is audible when boosted: listen for hiss. One voice for all four.",
    "Breath_Heavy": "Fast panting, 4 pulses each. Should feel like exertion, not comedy.",
    "Breath_Panic": "Exhausted, ragged gasps. Distinct from Heavy by raggedness, not volume.",
    "Breath_Gasp": "Sharp inhale (candle going out). 02/03 are +-7 % pitch copies of 01: only one source recording.",
    "Candle_Light": "Match strike / ignite: dry scrape then a small flame. Short.",
    "Candle_Out": "Soft blow and a puff: airy, not a spit. 02 is a very quiet source boosted 40 dB.",
    "Candle_Relight": "Soft flame whoosh.",
    "Door_Wood": "Heavy wooden door creaking open, 2.8-3 s. 03 is the same recording as 02 shifted +5 %.",
    "Door_Stone": "Continuous heavy stone grinding with rumble. Fade-out is 0.2 s: check the ending is not abrupt.",
    "Door_Locked": "Handle rattle / lock refusal. 01 single short rattle, 02-03 multi-rattle.",
    "Lever_Notch": "Mechanical click/clunk. 03/04 are Kenney metal click/latch (04 layered with a lever).",
    "Winch": "Ratchet / rope crank. 01 is metal ratchet, 02-03 are wooden crank takes.",
    "Stone_Grind": "Slab scrape: continuous rough grind, 3 s.",
    "Key_Pickup": "Jingle of keys, bright. 2D.",
    "Paper": "Rustle of a note, stereo, 2D.",
    "Generic_Use": "Short leather/belt handling tick (fallback interaction).",
    "Creak_Wood": "Single wood creak. 05 is cut from a door recording, 03 is a pitch -6 % tail.",
    "Chain_Distant": "01-02 original reverberant chain drags; 03-04 are darkened and given a long tail to read as far away.",
    "Warden_Step": "Heavy boot + thump + 50 Hz sub, pitched down 30 %. Should feel big but not slap-like.",
    "Warden_Chain": "Heavy chain drag clank, pitched down 8-12 %.",
    "Warden_Robe": "10 s loop of dull cloth rubbing, no obvious repeat; check the loop wrap near 10 s.",
    "Warden_Breath": "Loop wrap (seam): listen across the end-to-start join. Slow = patrol, Fast = investigate, Heavy = chase.",
    "Warden_Spotted": "Short (under 1.5 s), sharp, readable roar bark: the tell. Should be unmistakable but not cartoonish.",
    "Warden_Roar": "2.9-3 s low roar (cut at 3 s with a fade). Layered, sub, room tail.",
    "Warden_Windup": "Rising growl and hiss, 1.2-1.5 s: should say 'attack is coming'.",
    "Warden_Exhale": "Soft, long exhale: relief/loss of the player. Quiet and low.",
    "Warden_Caught": "Brutal 2.3-2.8 s growl/roar.",
    "Apparition_Whisper": "Ghostly whispers with a tail; check they are not intelligible words.",
    "Bat_": "01-03 squeaks (chirp trains from one close-up recording, 03 pitched down 15 %), 04-05 startled flurries (wing flutter plus chirps or colony swarm, at most 2.4 s), 06 a wing-flutter burst. Very high and quick: they should read as small and far up in the roof beams, never as a shriek.",
    "Owl_": "Distant hoots (low-passed at 5 kHz, short tail). 01 single hoot, 02 a short-then-long phrase, 03-04 the second owl. Check the hoot is soft and far, not a bird in the room.",
    "Howl_": "Far-off howls (low-passed at 3 kHz, 3 s synthetic tail, slow fades). 01 and 03 solitary wolf, 02 coyote. They must sound like something beyond the walls, not a dog next door.",
    "Rat_": "01-03 squeaks (one, two, three baby), 04 a scurry of claw taps, 05 scratching. Small and dry; listen for hiss in 03 and 05.",
}

WEAK = {
    "SFX_LB_Breath_Gasp_02": "pitch copy (only one gasp recording)",
    "SFX_LB_Breath_Gasp_03": "pitch copy (only one gasp recording)",
    "SFX_LB_Step_Stone_06": "-5 % pitch copy of 03 (Kenney has 5)", "SFX_LB_Step_Wood_06": "-5 % pitch copy of 02 (Kenney has 5)",
    "SFX_LB_Step_Grass_06": "-5 % pitch copy of 03 (Kenney has 5)",
    "SFX_LB_Door_Wood_Open_03": "pitch copy of another slice of the same recording",
    "SFX_LB_Creak_Wood_03": "pitch copy of the tail of 02's recording",
    "SFX_LB_Candle_Light_02": "strike source is only 0.3 s long; flame whoosh layered on",
}


FAM_WEAK = {
    "Step_Wood": "weakest set: Kenney wood steps are only ~0.08 s of low thump with almost no top end, and the 5 originals are near-identical (spread +-3 % pitch)",
    "Step_Stone": "Kenney concrete: very short and bass-heavy; originals near-identical (spread +-3 % pitch)",
    "Step_Grass": "Kenney grass: originals near-identical (spread +-3 % pitch)",
    "Step_Earth": "surface not labelled in the pack: picked by spectrum, needs an ear check",
    "Breath_Heavy": "four slices of one panting loop: pulses are similar",
    "Breath_Calm": "very quiet source, noise floor boosted about 25 dB",
    "Warden_Chain": "chain drags can sound rhythmic (pulses about every 0.25 s in 03/04)",
    "Chain_Distant": "03/04 reuse the Warden chain recordings with a darkened, long-tail treatment",
    "Warden_Breath": "check the loop wrap and that it reads as a creature, not a person",
    "Bat_": "the three squeaks are one recording (a bat in a duct) so they share a voice; flurry sources are caves and a vintage tape transfer, not a belfry; 05 has the tape hiss spectrally gated (can sound slightly watery)",
    "Owl_": "03/04 come from a field recording with its noise spectrally gated (can sound slightly watery); 867131 was rejected (ke-wick sweeps, not hoots)",
    "Howl_": "howls are 7-10 s long; 02 is a coyote, not a wolf; the tail is synthetic",
    "Rat_": "no clean recording of a rat running on stone exists in the CC0 set: 04 is a creature scurry (not a rat), 05 is a rat gnawing wood",
}


def group_of(name: str, items) -> str:
    for it in items:
        if it["name"] == name:
            return it["group"]
    return "?"


def check_wav(path: str, item: dict):
    problems = []
    with wave.open(path, "rb") as w:
        ok_fmt = w.getframerate() == 48000 and w.getsampwidth() == 2
        ch = w.getnchannels()
        raw = w.readframes(w.getnframes())
    q = np.frombuffer(raw, dtype="<i2").reshape(-1, ch)
    x = q.astype(np.float64) / 32768.0
    if not ok_fmt:
        problems.append("not 48k/16-bit")
    if ch != item["channels"]:
        problems.append(f"channels {ch} != {item['channels']}")
    clipped = int((np.abs(q) >= 32767).sum())
    if clipped:
        problems.append(f"{clipped} clipped samples")
    pk = L.peak(x)
    if L.db(pk) > -1.0:
        problems.append(f"peak {L.db(pk):.2f} dBFS > -1")
    dc = L.dc_offset(x)
    if dc >= 0.001:
        problems.append(f"DC {dc:.4f}")
    loop = "loop" in item
    m = {"len": len(x) / 48000, "ch": ch, "peak": L.db(pk), "rms": L.db(L.rms(x)), "dc": dc, "loop": loop}
    if loop:
        step, click = L.seam_metrics(x)
        m["seam"] = step
        m["seam_click"] = click
        if step >= 0.5:
            problems.append(f"loop seam step {step:.2f} dB")
        if click >= 8.0:
            problems.append(f"loop wrap click ratio {click:.1f}")
        if abs(m["rms"] - item["target"]["db"]) > 1.0:
            problems.append(f"RMS {m['rms']:.2f} vs {item['target']['db']}")
    else:
        edge = max(abs(x[0]).max(), abs(x[-1]).max())
        if edge > 0.003:
            problems.append(f"boundary sample {edge:.4f}")
        if abs(m["peak"] - item["target"]["db"]) > 1.0:
            problems.append(f"peak {m['peak']:.2f} vs {item['target']['db']}")
    m["step_ratio"] = L.max_step_ratio(x)
    if m["step_ratio"] > 40.0 and not loop:
        problems.append(f"possible internal click (step ratio {m['step_ratio']:.0f})")
    return m, problems


def contact_sheet(group: str, names, metas, path: str) -> None:
    cols, tw, th_lab, th_sp = 3, 440, 15, 80
    rows = (len(names) + cols - 1) // cols
    img = Image.new("RGB", (cols * tw, rows * (th_lab + th_sp + 4)), (18, 18, 22))
    d = ImageDraw.Draw(img)
    for i, n in enumerate(names):
        x = L.read_wav(os.path.join(OUT_DIR, n + ".wav"))
        cx, cy = (i % cols) * tw, (i // cols) * (th_lab + th_sp + 4)
        m = metas[n]
        d.text((cx + 4, cy + 1), f"{n.replace('SFX_LB_', '')}  {m['len']:.2f}s  pk {m['peak']:.1f}  rms {m['rms']:.1f}", fill=(255, 255, 255))
        img.paste(spectrogram_img(x, tw - 6, th_sp, 12000.0).convert("RGB"), (cx + 3, cy + th_lab))
    img.save(path)


def fam(name: str) -> str:
    for k in sorted(LISTEN, key=len, reverse=True):
        if k in name:
            return k
    return ""


def main() -> int:
    items = json.load(open(os.path.join(HERE, "recipes.json"), encoding="utf8"))["items"]
    by_name = {it["name"]: it for it in items}
    metas, fails = {}, []
    for it in items:
        p = os.path.join(OUT_DIR, it["name"] + ".wav")
        if not os.path.exists(p):
            fails.append((it["name"], ["missing file"]))
            continue
        m, pr = check_wav(p, it)
        metas[it["name"]] = m
        if pr:
            fails.append((it["name"], pr))
    for pre, cnt in EXPECTED.items():
        got = [n for n in by_name if n.startswith(pre)]
        if len(got) != cnt:
            fails.append((pre, [f"variant count {len(got)} != cue sheet {cnt}"]))
    # extra checks on the output folder
    extra = [f for f in os.listdir(OUT_DIR) if f.endswith(".wav") and f[:-4] not in by_name]
    if extra:
        fails.append(("folder", [f"unexpected files {extra}"]))
    print(f"{len(metas)} files checked, {len(fails)} problem items")
    for n, pr in fails:
        print("  FAIL", n, "; ".join(pr))
    rms_loops = [(n, m) for n, m in metas.items() if m["loop"]]
    for n, m in rms_loops:
        print(f"  loop {n}: {m['len']:.1f}s rms {m['rms']:.2f} peak {m['peak']:.2f} seam {m['seam']:.2f} dB click {m['seam_click']:.2f}")
    print("  worst DC:", max(m["dc"] for m in metas.values()), " worst peak:", max(m["peak"] for m in metas.values()),
          " max step ratio:", max((m["step_ratio"], n) for n, m in metas.items()))
    if "--checks" in sys.argv:
        return 1 if fails else 0

    man = json.load(open(os.path.join(OUT_DIR, "manifest.json"), encoding="utf8"))
    md = ["# Recorded audio: audition (A3)\n",
          "Built by `Tools/audio/prep/prep_recorded.py` from `Tools/audio/prep/recipes.json` (CC0 Freesound and Kenney sources, see `Docs/ASSET_REGISTRY.md`); "
          "objective checks by `Tools/audio/prep/report_recorded.py`. WAVs are 48 kHz 16-bit in `SourceArt/Audio/Recorded/`: mono for 3D sounds "
          "(player breath is mono-centred 2D, paper is stereo 2D). One-shots are normalised to a -3 dBFS peak, loops to -24 dBFS RMS; level balance is the mix's job.\n",
          "Turn the volume down before the Warden roars, spotted, caught and windup files. For each cue decide **keep**, **redo** (say what to change) or **replace**.\n",
          "**Columns.** *Src* = Freesound id (plain number) or Kenney file (`ki:` Impact, `kr:` RPG). *Peak* / *RMS* are measured on the written file. "
          "*Seam* (loops) = level step between the first and last 0.5 s (target < 0.5 dB).\n"]
    for gk, title in GROUPS:
        names = [it["name"] for it in items if it["group"] == gk]
        path = os.path.join(DOC_DIR, f"rec_{gk}.png")
        contact_sheet(gk, names, metas, path)
        md.append(f"\n## {title}\n")
        md.append(f"![spectrograms](rec_{gk}.png)\n")
        md.append("| File | Len | Ch | Peak | RMS | Src | What to listen for | Weak / note | Keep / redo / replace |")
        md.append("|---|---|---|---|---|---|---|---|---|")
        seen = set()
        for n in names:
            m, it = metas[n], by_name[n]
            srcs = ", ".join(sorted({l["src"].split(":", 1)[1] if l["src"].startswith("fs:") else l["src"]
                                     for l in it["layers"] if "src" in l}))
            if any("synth" in l for l in it["layers"]):
                srcs += ", noise bed (synth)"
            loop = f" loop, seam {m['seam']:.2f} dB" if m["loop"] else ""
            weak = WEAK.get(n, "")
            first = fam(n) not in seen
            seen.add(fam(n))
            if FAM_WEAK.get(fam(n)) and first:
                weak = (weak + "; " if weak else "") + FAM_WEAK[fam(n)] + " (applies to the whole set)"
            if man.get(n, {}).get("src_clipped_samples", 0) > 0:
                weak = (weak + "; " if weak else "") + f"source has {man[n]['src_clipped_samples']} clipped samples in the slice"
            md.append(f"| [{n}](../../../SourceArt/Audio/Recorded/{n}.wav) | {m['len']:.2f} s{loop} | {m['ch']} | {m['peak']:.1f} | {m['rms']:.1f} | {srcs} | "
                      f"{LISTEN.get(fam(n), '') if first else 'as above'} | {weak} | |")
    with open(os.path.join(DOC_DIR, "audition_recorded.md"), "w", encoding="utf8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    print("wrote sheets and audition_recorded.md")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
