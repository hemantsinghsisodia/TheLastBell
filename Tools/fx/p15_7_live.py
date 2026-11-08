"""P15-7 look session: live tuning in PIE over MCP. Never saves anything.

    python -I Tools/fx/p15_7_live.py state
    python -I Tools/fx/p15_7_live.py fx RainSpawnRate=25000 RainWindLean=500
    python -I Tools/fx/p15_7_live.py mi MI_LB_Rain RainBase=0.05 RainFlash=1.4
    python -I Tools/fx/p15_7_live.py user FX_Dust_Ch_Shaft_S1 User.Count f 60      (the PIE copy of a placed Niagara actor)
    python -I Tools/fx/p15_7_live.py pawn
    python -I Tools/fx/p15_7_live.py tp X Y Z

DA_StormFX writes take effect on the next tick (the FX subsystem pushes changed rain values every tick). MI writes are immediate.
Both leave the assets dirty in memory: P15-8 saves the chosen values deliberately; otherwise choose Don't Save on close.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import p15_level as P  # noqa: E402

O, A, S, E = P.L.O, P.L.A, P.L.S, P.L.E
MI_TS = "editor_toolset.toolsets.material_instance.MaterialInstanceTools"
FX_FIELDS = ["bRain", "RainSpawnRate", "RainBoxHalfXY", "RainSpawnHeight", "RainFallSpeed", "RainWindLean", "SplashRate", "SplashRadius",
             "MistMinExposure", "SkyBoltChance", "SkyBoltDistance", "SkyBoltTopHeight", "SkyBoltLength", "BoltAspect", "StrikeSkyHeight",
             "StrikeSkyOffset", "StrikeWidth", "BoltMaxSeconds", "DebugBolt"]
MIS = ["MI_LB_Rain", "MI_LB_Splash", "MI_LB_Ripple", "MI_LB_Bolt", "MI_Flame_Candle", "MI_Flame_Torch", "MI_LB_DustMote", "MI_LB_Mist",
       "MI_LB_WaterMist", "MI_LB_RainCurtain", "MI_Cloth_Linen_Dark", "MI_Cloth_Linen_Dark_Sheet", "MI_Cloth_Linen_Red"]
MI_DIR = "/Game/LastBell/Materials/Instances/FX/"


def mi_obj(name):
    return MI_DIR + name + "." + name


def mi_scalars(ed, name):
    r = ed.call(O, "get_properties", {"instance": {"refPath": mi_obj(name)}, "properties": ["scalarParameterValues"]})
    r = json.loads(r) if isinstance(r, str) else r
    return {p["parameterInfo"]["name"]: round(p["parameterValue"], 4) for p in r.get("scalarParameterValues", [])}


def pie_pawn(ed):
    hits = [x for x in ed.find_all(name="BP_LBCharacter") if "UEDPIE" in x]
    return hits[0] if hits else None


def pie_actor(ed, label):
    """The PIE copy of an editor actor: same object name, in the UEDPIE_0_ map package."""
    ref = ed.find_one(label, must=True)
    return ref.replace("/Game/LastBell/Maps/L_Monastery.", "/Game/LastBell/Maps/UEDPIE_0_L_Monastery.")


def val(s):
    try:
        return json.loads(s)
    except ValueError:
        return s


def main():
    ed = P.Ed()
    cmd, args = sys.argv[1], sys.argv[2:]
    print("PIE running:", ed.call(E, "IsPIERunning", {}))
    if cmd == "state":
        st = ed.props(P.DA_FX, FX_FIELDS)
        for k in FX_FIELDS:
            print("  DA_StormFX.%-17s %s" % (k, st.get(k)))
        for m in MIS:
            print("  %-26s %s" % (m, mi_scalars(ed, m)))
        pw = pie_pawn(ed)
        if pw:
            print("  pawn", pw, ed.xform(pw))
    elif cmd == "fx":
        values = {k: val(v) for k, v in (a.split("=", 1) for a in args)}
        ed.setp(P.DA_FX, values)
        st = ed.props(P.DA_FX, list(values))
        for k in values:
            print("  set DA_StormFX.%s = %s -> reads %s" % (k, values[k], st.get(k)))
    elif cmd == "mi":
        name = args[0]
        for a in args[1:]:
            k, v = a.split("=", 1)
            ed.call(MI_TS, "set_scalar_parameter", {"instance": {"refPath": mi_obj(name)}, "name": k, "value": float(v)})
        print("  %s now %s" % (name, mi_scalars(ed, name)))
    elif cmd == "user":
        label, name, kind, v = args[0], args[1], args[2], val(args[3])
        ref = pie_actor(ed, label)
        ed.nset(ref, name, kind, v)
        print("  %s %s = %s -> reads %s" % (label, name, v, ed.nget(ref, name, kind)))
    elif cmd == "pawn":
        pw = pie_pawn(ed)
        print("  pawn", pw, ed.xform(pw) if pw else None)
    elif cmd == "tp":
        pw = pie_pawn(ed)
        if not pw:
            raise SystemExit("no PIE pawn")
        loc, rot, sc = ed.xform(pw)
        new = [float(x) for x in args[:3]]
        ed.set_xform(pw, new, rot, sc)
        print("  pawn moved from %s to %s -> reads %s" % (P.rnd(loc, 1), new, P.rnd(ed.xform(pw)[0], 1)))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
