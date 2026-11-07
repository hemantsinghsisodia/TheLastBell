"""P14-2b: wind sway materials (editor open, MCP). Record of what was run on 2026-11-07; each step ran once.

Usage (Windows python, set MSYS_NO_PATHCONV=1 under Git Bash):
  python p14_2b_wind.py fn                      # create MF_LB_WindSway (empty function must exist: step creates it)
  python p14_2b_wind.py master foliage|masked   # add bWind / WindAmplitudeCm / WindRefHeightCm + WPO + max displacement
  python p14_2b_wind.py mi <MI name> <amp|none> <refHeight|none> [save]
Every save checks that L_Monastery and M_LB_Surface are not dirty. Never calls set_parent.
"""
import sys, json, time
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\lighting")
from p14_lib import *

MAP = "/Game/LastBell/Maps/L_Monastery"
SURF = "/Game/LastBell/Materials/Master/M_LB_Surface"


def guard():
    d1, d2 = dirty(MAP), dirty(SURF)
    print("guard map/surface dirty:", d1, d2)
    assert not d1 and not d2, "STOP: level or surface dirty"


def save(pkg):
    guard()
    print("save", pkg, ue.call(AST, "save_assets", {"asset_paths": [pkg]}), "dirty after:", dirty(pkg))
    guard()


def build_function():
    F = "/Game/LastBell/Materials/Functions/MF_LB_WindSway.MF_LB_WindSway"
    ue.call(MAT, "create_function", {"folder_path": "/Game/LastBell/Materials/Functions", "asset_name": "MF_LB_WindSway"})
    assert exprs(F) == [], exprs(F)
    TWO_PI = 6.283185307179586
    N={}
    def A(name, cls, x, y, **p):
        N[name]=add(F, cls, x, y, **p); return N[name]
    def C(src, dst, pin, out=""):
        conn(N[src], N[dst], pin, out)

    setp(F, {"bExposeToLibrary": True, "libraryCategoriesText": ["LastBell"],
             "description": "Wind sway WPO driven by MPC_LB_Storm (WindStrength, WindPhase, WindDirection). bFlutter false = bend (grass, weeds, ferns, shrubs, pivot per instance); true = ivy flutter along the vertex normal. Exactly (0,0,0) at WindStrength = 0."})

    # inputs / output
    A("amp","FunctionInput",0,0, inputName="WindAmplitudeCm", inputType="FunctionInput_Scalar", previewValue={"x":0,"y":0,"z":0,"w":0}, bUsePreviewValueAsDefault=True, sortPriority=0, desc="Peak sway in cm at WindStrength 1")
    A("ref","FunctionInput",0,150, inputName="WindRefHeightCm", inputType="FunctionInput_Scalar", previewValue={"x":60,"y":0,"z":0,"w":0}, bUsePreviewValueAsDefault=True, sortPriority=1, desc="Local height in cm at which the bend is full")
    A("bfl","FunctionInput",0,300, inputName="bFlutter", inputType="FunctionInput_StaticBool", previewValue={"x":0,"y":0,"z":0,"w":0}, bUsePreviewValueAsDefault=True, sortPriority=2, desc="false = bend, true = ivy flutter")
    A("out","FunctionOutput",2600,300, outputName="WPO")

    # MPC reads
    A("wstr","CollectionParameter",0,500, collection=MPC_REF, parameterName="WindStrength")
    A("wph","CollectionParameter",0,650, collection=MPC_REF, parameterName="WindPhase")
    A("wdir","CollectionParameter",0,800, collection=MPC_REF, parameterName="WindDirection")
    A("psl","PreSkinnedPosition",0,950)

    # ---------------- bend ----------------
    A("b_z","ComponentMask",300,950, r=False,g=False,b=True,a=False); C("psl","b_z","")
    A("b_div","Divide",600,950); C("b_z","b_div","A"); C("ref","b_div","B")
    A("b_h","Saturate",800,950); C("b_div","b_h","")
    A("b_h2","Multiply",1000,950); C("b_h","b_h2","A"); C("b_h","b_h2","B")
    A("b_c0","Constant3Vector",300,1150, constant={"r":0,"g":0,"b":0,"a":1})
    A("b_piv","TransformPosition",600,1150, transformSourceType="TRANSFORMPOSSOURCE_Instance", transformType="TRANSFORMPOSSOURCE_World"); C("b_c0","b_piv","")
    A("b_pxy","ComponentMask",800,1150, r=True,g=True,b=False,a=False); C("b_piv","b_pxy","")
    A("b_k","Constant2Vector",800,1300, r=0.0031, g=0.0047)
    A("b_dot","DotProduct",1000,1150); C("b_pxy","b_dot","A"); C("b_k","b_dot","B")
    A("b_phi","Add",1200,1150); C("wph","b_phi","A"); C("b_dot","b_phi","B")
    A("b_sin1","Sine",1400,1100, period=TWO_PI); C("b_phi","b_sin1","")
    A("b_s1","Multiply",1600,1100, constB=0.6); C("b_sin1","b_s1","A")
    A("b_phi2","Multiply",1400,1250, constB=2.0); C("b_phi","b_phi2","A")
    A("b_phi2b","Add",1550,1250, constB=1.3); C("b_phi2","b_phi2b","A")
    A("b_sin2","Sine",1700,1250, period=TWO_PI); C("b_phi2b","b_sin2","")
    A("b_s2","Multiply",1850,1250, constB=0.4); C("b_sin2","b_s2","A")
    A("b_s","Add",2000,1150); C("b_s1","b_s","A"); C("b_s2","b_s","B")
    A("b_g1","Multiply",2150,1150, constB=0.45); C("b_s","b_g1","A")
    A("b_g","Add",2300,1150, constB=0.55); C("b_g1","b_g","A")
    # scalar = WindStrength * gust * h2 * Amp
    A("b_m1","Multiply",1200,500); C("wstr","b_m1","A"); C("b_g","b_m1","B")
    A("b_m2","Multiply",1400,500); C("b_m1","b_m2","A"); C("b_h2","b_m2","B")
    A("b_m3","Multiply",1600,500); C("b_m2","b_m3","A"); C("amp","b_m3","B")
    A("b_dm","ComponentMask",300,800, r=True,g=True,b=True,a=False); C("wdir","b_dm","")
    A("b_d","Multiply",1800,500); C("b_dm","b_d","A"); C("b_m3","b_d","B")
    A("b_len","Length",2000,500); C("b_d","b_len","")
    A("b_lh","Multiply",2200,500); C("b_len","b_lh","A"); C("b_h","b_lh","B")
    A("b_lz","Multiply",2350,500, constB=-0.25); C("b_lh","b_lz","A")
    A("b_up","Constant3Vector",2350,650, constant={"r":0,"g":0,"b":1,"a":1})
    A("b_zv","Multiply",2500,600); C("b_up","b_zv","A"); C("b_lz","b_zv","B")
    A("b_wpo","Add",2650,500); C("b_d","b_wpo","A"); C("b_zv","b_wpo","B")

    # ---------------- flutter ----------------
    A("f_y","ComponentMask",300,1500, r=False,g=True,b=False,a=False); C("psl","f_y","")
    A("f_div","Divide",600,1500, constB=20.0); C("f_y","f_div","A")
    A("f_a","Saturate",800,1500); C("f_div","f_a","")
    A("f_wp","WorldPosition",300,1700)
    A("f_k","Constant3Vector",600,1800, constant={"r":0.05,"g":0.07,"b":0.03,"a":1})
    A("f_dot","DotProduct",900,1700); C("f_wp","f_dot","A","XYZ"); C("f_k","f_dot","B")
    A("f_p3","Multiply",900,1600, constB=3.0); C("wph","f_p3","A")
    A("f_phi","Add",1100,1650); C("f_p3","f_phi","A"); C("f_dot","f_phi","B")
    A("f_sin","Sine",1300,1650, period=TWO_PI); C("f_phi","f_sin","")
    A("f_n","VertexNormalWS",1300,1850)
    A("f_m1","Multiply",1500,1650); C("wstr","f_m1","A"); C("f_sin","f_m1","B")
    A("f_m2","Multiply",1700,1650); C("f_m1","f_m2","A"); C("f_a","f_m2","B")
    A("f_m3","Multiply",1900,1650); C("f_m2","f_m3","A"); C("amp","f_m3","B")
    A("f_wpo","Multiply",2100,1650); C("f_n","f_wpo","A"); C("f_m3","f_wpo","B")

    # ---------------- select ----------------
    A("sw","StaticSwitch",2800,300); C("bfl","sw","Value"); C("f_wpo","sw","True"); C("b_wpo","sw","False")
    C("sw","out","")
    print(recompile(F))
    print("nodes", len(exprs(F)))
    save("/Game/LastBell/Materials/Functions/MF_LB_WindSway")


WS = ref("/Game/LastBell/Materials/Functions/MF_LB_WindSway.MF_LB_WindSway")


def build_master(pkg, flutter, maxwpo):
    M=pkg+"."+pkg.rsplit("/",1)[1]
    guard()
    before=len(exprs(M)); print(pkg,"nodes before",before, "maxWPO before", props(M,["maxWorldPositionOffsetDisplacement"]))
    assert ue.call(MAT,"get_property_input",{"material":ref(M),"material_property":"MP_WorldPositionOffset"})["expression"] in (None,"None")
    amp=add(M,"ScalarParameter",-1400,1200, parameterName="WindAmplitudeCm", defaultValue=0.0, group="Wind")
    rh =add(M,"ScalarParameter",-1400,1350, parameterName="WindRefHeightCm", defaultValue=60.0, group="Wind")
    sb =add(M,"StaticBool",-1400,1500, value=flutter)
    fc =add(M,"MaterialFunctionCall",-1100,1300); setp(fc,{"materialFunction":WS})
    print("fc inputs", input_names(fc))
    conn(amp,fc,"WindAmplitudeCm"); conn(rh,fc,"WindRefHeightCm"); conn(sb,fc,"bFlutter")
    z =add(M,"Constant3Vector",-1100,1550, constant={"r":0,"g":0,"b":0,"a":1})
    sw =add(M,"StaticSwitchParameter",-800,1350, parameterName="bWind", defaultValue=False, group="Wind")
    conn(fc,sw,"True","WPO"); conn(z,sw,"False")
    ue.call(MAT,"connect_to_output",{"expression":ref(sw),"output_name":"","material_property":"MP_WorldPositionOffset"})
    setp(M,{"maxWorldPositionOffsetDisplacement":maxwpo})
    print("recompile:", recompile(M))
    print("maxWPO after", props(M,["maxWorldPositionOffsetDisplacement"]))
    print("WPO input", ue.call(MAT,"get_property_input",{"material":ref(M),"material_property":"MP_WorldPositionOffset"}))
    print("fc inputs wiring", [(i["input_name"], i["expression"]["refPath"].split("Expression")[-1] if isinstance(i["expression"],dict) else i["expression"]) for i in inputs(M,fc)])
    print("sw wiring", [(i["input_name"], (i["expression"]["refPath"].split("Expression")[-1] if isinstance(i["expression"],dict) else i["expression"]), i["output_name"]) for i in inputs(M,sw)])
    print("sb value", props(sb,["value"]), "nodes after", len(exprs(M)))

D = "/Game/LastBell/Environments/Courtyard/Materials/"
def statics(o):
    out={}
    for n in ["bUseARM","bWind"]:
        try: out[n]=ue.call(MI,"get_static_switch_parameter",{"instance":ref(o),"name":n})
        except Exception as ex: out[n]="ERR "+str(ex)[:80]
    return out
def snap(n):
    p=D+n; return dict(mi_compact(p), statics=statics(objpath(p)))
def run(n, amp, refh):
    guard()
    p=D+n; o=objpath(p)
    b=snap(n); print("BEFORE", n, json.dumps(b))
    t=time.time()
    if amp is not None: print(" amp", ue.call(MI,"set_scalar_parameter",{"instance":ref(o),"name":"WindAmplitudeCm","value":amp}))
    if refh is not None: print(" ref", ue.call(MI,"set_scalar_parameter",{"instance":ref(o),"name":"WindRefHeightCm","value":refh}))
    print(" bWind", ue.call(MI,"set_static_switch_parameter",{"instance":ref(o),"name":"bWind","value":True}), "%.1fs"%(time.time()-t))
    a=snap(n); print("AFTER ", n, json.dumps(a))
    # diff
    for k in ("parent","textures","vectors"): assert a[k]==b[k], (k,a[k],b[k])
    ds={k:(b["scalars"].get(k),a["scalars"].get(k)) for k in set(a["scalars"])|set(b["scalars"]) if a["scalars"].get(k)!=b["scalars"].get(k)}
    print("SCALAR DIFF", ds, "STATIC", b["statics"], "->", a["statics"])
    pass
    return a


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "fn":
        build_function()
    elif what == "master":
        if sys.argv[2] == "foliage":
            build("/Game/LastBell/Materials/Master/M_LB_Foliage", False, 40.0)
        else:
            build("/Game/LastBell/Materials/Master/M_LB_FoliageMasked", True, 6.0)
        save("/Game/LastBell/Materials/Master/" + ("M_LB_Foliage" if sys.argv[2] == "foliage" else "M_LB_FoliageMasked"))
    elif what == "mi":
        n = sys.argv[2]
        amp = float(sys.argv[3]) if sys.argv[3] != "none" else None
        refh = float(sys.argv[4]) if sys.argv[4] != "none" else None
        run(n, amp, refh)
        if len(sys.argv) > 5 and sys.argv[5] == "save":
            save(D + n)
