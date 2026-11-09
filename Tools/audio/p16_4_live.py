"""P16-4 listening session: live tuning over MCP while the owner plays (PIE). Never saves anything.

    python -I Tools/audio/p16_4_live.py state                         DA_Audio key fields, class volumes, PIE pawn
    python -I Tools/audio/p16_4_live.py da Field=value [...]          set DA_Audio fields (JSON values; applied next tick)
    python -I Tools/audio/p16_4_live.py cls <Master|SFX|Ambience|Music|Voice|UI> <volume>   SoundClass volume
    python -I Tools/audio/p16_4_live.py wave <AssetName> <volume>     SoundWave volume (e.g. SFX_LB_Bell_Stage1)
    python -I Tools/audio/p16_4_live.py zone <ZoneName> Field=value   ALBAudioZone field on the PIE copy and the editor actor
    python -I Tools/audio/p16_4_live.py pawn | tp X Y Z

Edits to assets leave them dirty in memory: P16-5 saves the chosen values deliberately; otherwise choose Don't Save on close.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Tools", "fx"))
import p15_level as P  # noqa: E402

O, A, S, E = P.L.O, P.L.A, P.L.S, P.L.E
DA = "/Game/LastBell/Data/DA_Audio.DA_Audio"
MIX = "/Game/LastBell/Audio/Mix/"
FIELDS = ["RainOutGain", "RainInGain", "RainExposurePower", "WindOutGain", "WindMin", "ThunderDelay", "ThunderNearAt", "ThunderFarBelow",
          "ThunderDistance", "bAmbientTolls", "AmbientTollInterval", "AmbientTollVolume", "DroneSeconds", "TensionNearDistance", "TensionLevels",
          "ChaseLevel", "MusicMinStage", "StressNearSearch", "DarknessLit", "DarknessUnlit", "CandleOutStress", "BreathInterval",
          "DebugForceMusicState"]
WAVE_DIRS = ["Weather", "Thunder", "Bell", "Music", "Room", "Player", "Interact", "Warden"]


def val(s):
    try:
        return json.loads(s)
    except ValueError:
        return s


def scl(name):
    n = "SCL_LB_" + name
    return MIX + n + "." + n


def wave_ref(ed, name):
    # AssetTools.exists reports assets as missing while PIE runs (MCP_NOTES P15-9 item 4): probe with get_properties instead
    for d in WAVE_DIRS:
        p = "/Game/LastBell/Audio/%s/%s.%s" % (d, name, name)
        try:
            ed.props(p, ["Volume"])
            return p
        except RuntimeError:
            continue
    raise SystemExit("no SoundWave named %s" % name)


def pie_pawn(ed):
    hits = [x for x in ed.find_all(name="BP_LBCharacter") if "UEDPIE" in x]
    return hits[0] if hits else None


def main():
    ed = P.Ed()
    cmd, args = sys.argv[1], sys.argv[2:]
    print("PIE running:", ed.call(E, "IsPIERunning", {}))
    if cmd == "state":
        st = ed.props(DA, FIELDS)
        for k in FIELDS:
            print("  DA_Audio.%-22s %s" % (k, st.get(k)))
        for c in ["Master", "SFX", "Ambience", "Music", "Voice", "UI"]:
            print("  SCL_LB_%-9s %s" % (c, ed.props(scl(c), ["Properties"]).get("Properties", {}).get("volume")))
        pw = pie_pawn(ed)
        if pw:
            print("  pawn", P.rnd(ed.xform(pw)[0], 1))
    elif cmd == "da":
        values = {k: val(v) for k, v in (a.split("=", 1) for a in args)}
        ed.setp(DA, values)
        st = ed.props(DA, list(values))
        for k in values:
            print("  DA_Audio.%s = %s -> reads %s" % (k, values[k], st.get(k)))
    elif cmd == "cls":
        ref = scl(args[0])
        ed.setp(ref, {"Properties": {"volume": float(args[1])}})
        print("  SCL_LB_%s volume -> %s" % (args[0], ed.props(ref, ["Properties"]).get("Properties", {}).get("volume")))
    elif cmd == "wave":
        ref = wave_ref(ed, args[0])
        ed.setp(ref, {"Volume": float(args[1])})
        print("  %s Volume -> %s" % (args[0], ed.props(ref, ["Volume"]).get("Volume")))
    elif cmd == "zone":
        label = "AUD_Zone_" + args[0]
        ref = ed.find_one(label, must=True)
        values = {k: val(v) for k, v in (a.split("=", 1) for a in args[1:])}
        for target in (ref, ref.replace("/Game/LastBell/Maps/L_Monastery.", "/Game/LastBell/Maps/UEDPIE_0_L_Monastery.")):
            try:
                ed.setp(target, values)
                print("  %s %s -> %s" % ("PIE" if "UEDPIE" in target else "editor", label, ed.props(target, list(values))))
            except RuntimeError as e:
                print("  %s %s: %s" % ("PIE" if "UEDPIE" in target else "editor", label, str(e)[:120]))
    elif cmd == "pawn":
        pw = pie_pawn(ed)
        print("  pawn", P.rnd(ed.xform(pw)[0], 1) if pw else None)
    elif cmd == "tp":
        pw = pie_pawn(ed)
        if not pw:
            raise SystemExit("no PIE pawn")
        loc, rot, sc = ed.xform(pw)
        ed.set_xform(pw, [float(x) for x in args[:3]], rot, sc)
        print("  pawn moved to", P.rnd(ed.xform(pw)[0], 1))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
