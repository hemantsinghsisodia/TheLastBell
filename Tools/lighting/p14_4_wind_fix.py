"""P14-4 wind fix (editor open, MCP, no PIE). Record of what was run on 2026-11-07. Spec: Docs/plans/P14_4_WIND_FIX.md.

Usage (Windows python -I; set MSYS_NO_PATHCONV=1 under Git Bash):
  python p14_4_wind_fix.py pre      # read-only: PIE/dirty state, the bend branch wiring, node count
  python p14_4_wind_fix.py fn       # add 4 nodes, rewire b_div.A, update the input description, recompile fn + both masters
  python p14_4_wind_fix.py savefn   # save MF_LB_WindSway, then the masters only if dirty
  python p14_4_wind_fix.py mis      # set the new WindAmplitudeCm / WindRefHeightCm on the 8 MIs (before/after diff each)
  python p14_4_wind_fix.py savemis  # save the 8 MIs, one package per call
  python p14_4_wind_fix.py check    # PASS/FAIL for the graph wiring and the 8 MI values
Every save checks PIE is off and that L_Monastery / M_LB_Surface are not dirty. Never calls set_parent.
"""
import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\lighting")
from p14_lib import *

MAP = "/Game/LastBell/Maps/L_Monastery"
SURF = "/Game/LastBell/Materials/Master/M_LB_Surface"
FPKG = "/Game/LastBell/Materials/Functions/MF_LB_WindSway"
F = FPKG + ".MF_LB_WindSway"
MASTERS = ["/Game/LastBell/Materials/Master/M_LB_Foliage", "/Game/LastBell/Materials/Master/M_LB_FoliageMasked"]
D = "/Game/LastBell/Environments/Courtyard/Materials/"
APP = "EditorToolset.EditorAppToolset"

# name: (amp, refHeight or None = untouched)
# P14-5 (owner's P14-4 choices): the amplitudes are the owner's tuned storm-strength values (were 30/18/12/18/14/12/4/4 in f9261e6);
# WindRefHeightCm is unchanged. `mis` / `check` use these values.
MIS = {
    "MI_Foliage_GrassMedium02": (38.0, 60.0),   # P14-5: was 30
    "MI_Foliage_NettlePlant": (24.0, 45.0),     # P14-5: was 18
    "MI_Foliage_WeedPlant02": (16.0, 30.0),     # P14-5: was 12
    "MI_Foliage_Fern02": (24.0, 45.0),          # P14-5: was 18
    "MI_Foliage_WildRooibos": (18.0, 60.0),     # P14-5: was 14
    "MI_Foliage_SearsiaLucida": (16.0, 150.0),  # P14-5: was 12
    "MI_Ivy_Green": (5.0, None),                # P14-5: was 4
    "MI_Ivy_Dead": (5.0, None),                 # P14-5: was 4
}
OLD = {  # for the diff report only
    "MI_Foliage_GrassMedium02": (16.0, 90.0), "MI_Foliage_NettlePlant": (9.0, 70.0), "MI_Foliage_WeedPlant02": (6.0, 30.0),
    "MI_Foliage_Fern02": (10.0, 60.0), "MI_Foliage_WildRooibos": (7.0, 80.0), "MI_Foliage_SearsiaLucida": (5.0, 200.0),
    "MI_Ivy_Green": (2.0, None), "MI_Ivy_Dead": (2.0, None),
}


def pie():
    return ue.call(APP, "IsPIERunning", {})


def guard():
    p, d1, d2 = pie(), dirty(MAP), dirty(SURF)
    print("guard PIE/map/surface dirty:", p, d1, d2)
    assert not p, "STOP: PIE is running"
    assert not d1 and not d2, "STOP: level or surface dirty"


def save(pkg):
    guard()
    r = ue.call(AST, "save_assets", {"asset_paths": [pkg]})
    print("save", pkg, r, "dirty after:", dirty(pkg))
    guard()


def find(suffix):
    m = [e for e in exprs(F) if e.endswith(":" + suffix)]
    assert len(m) == 1, (suffix, m)
    return m[0]


def wiring(e, m=F):
    out = []
    for i in inputs(m, e):
        x = i["expression"]
        out.append((i["input_name"], short(x["refPath"]) if isinstance(x, dict) else x, i["output_name"]))
    return out


def read_bend():
    names = {"b_z": "MaterialExpressionComponentMask_1", "b_div": "MaterialExpressionDivide_0", "b_h": "MaterialExpressionSaturate_0"}
    for k, v in names.items():
        e = find(v)
        print(k, short(e), wiring(e))
    z = find(names["b_z"])
    print("b_z mask", props(z, ["r", "g", "b", "a"]))
    ref_in = find("MaterialExpressionFunctionInput_1")
    print("FunctionInput_1", props(ref_in, ["inputName", "description"]) if True else "")
    print("node count", len(exprs(F)))


def build_fn():
    guard()
    before = len(exprs(F))
    print("nodes before", before)
    assert before == 53, before
    b_z = find("MaterialExpressionComponentMask_1")
    b_div = find("MaterialExpressionDivide_0")
    ref_in = find("MaterialExpressionFunctionInput_1")
    assert jl(props(ref_in, ["inputName"]))["inputName"] == "WindRefHeightCm"
    assert [w[1] for w in wiring(b_div)] == ["ComponentMask_1", "FunctionInput_1"], wiring(b_div)
    print("-- before"); read_bend()
    up = add(F, "Constant3Vector", 300, 1000, constant={"r": 0, "g": 0, "b": 1, "a": 1})
    tr = add(F, "Transform", 450, 1000)
    print("transform props before set:", props(tr, ["transformSourceType", "transformType"]))
    setp(tr, {"transformSourceType": "TRANSFORMSOURCE_Instance", "transformType": "TRANSFORM_World"})
    print("transform props:", props(tr, ["transformSourceType", "transformType"]))
    conn(up, tr, "")
    ln = add(F, "Length", 600, 1000)
    conn(tr, ln, "")
    mul = add(F, "Multiply", 500, 950)
    conn(b_z, mul, "A")
    conn(ln, mul, "B")
    conn(mul, b_div, "A")  # replaces the old A link
    setp(ref_in, {"description": "World height in cm (after the actor or instance scale) at which the bend is full"})
    print("-- after")
    print("up", short(up), props(up, ["constant"]))
    print("transform", short(tr), wiring(tr))
    print("length", short(ln), wiring(ln))
    print("mul", short(mul), wiring(mul))
    print("b_div", wiring(b_div))
    n = len(exprs(F))
    print("node count", n, "(before + 4 =", before + 4, ")")
    assert n == before + 4
    print("FunctionInput_1", props(ref_in, ["inputName", "description"]))
    print("recompile fn:", recompile(F))
    for m in MASTERS:
        mo = m + "." + m.rsplit("/", 1)[1]
        print("recompile", m, recompile(mo))
        print("  dirty:", dirty(m))
    print("fn dirty:", dirty(FPKG))


def save_fn():
    save(FPKG)
    for m in MASTERS:
        if dirty(m):
            save(m)
        else:
            print("master not dirty, no save:", m)


def statics(o):
    out = {}
    for n in ["bUseARM", "bWind"]:
        try:
            out[n] = ue.call(MI, "get_static_switch_parameter", {"instance": ref(o), "name": n})
        except Exception as ex:
            out[n] = "ERR " + str(ex)[:80]
    return out


def snap(n):
    p = D + n
    return dict(mi_compact(p), statics=statics(objpath(p)))


def run_mi(n):
    guard()
    amp, refh = MIS[n]
    o = objpath(D + n)
    b = snap(n)
    print("BEFORE", n, json.dumps(b))
    print(" amp", ue.call(MI, "set_scalar_parameter", {"instance": ref(o), "name": "WindAmplitudeCm", "value": amp}))
    if refh is not None:
        print(" ref", ue.call(MI, "set_scalar_parameter", {"instance": ref(o), "name": "WindRefHeightCm", "value": refh}))
    a = snap(n)
    print("AFTER ", n, json.dumps(a))
    for k in ("parent", "textures", "vectors", "statics"):
        assert a[k] == b[k], (k, a[k], b[k])
    ds = {k: (b["scalars"].get(k), a["scalars"].get(k)) for k in set(a["scalars"]) | set(b["scalars"]) if a["scalars"].get(k) != b["scalars"].get(k)}
    print("SCALAR DIFF", n, ds)
    allowed = {"WindAmplitudeCm", "WindRefHeightCm"}
    assert set(ds) <= allowed, ds
    print("dirty:", dirty(D + n))


def check():
    ok = True

    def P(name, cond, info=""):
        nonlocal ok
        ok = ok and bool(cond)
        print("PASS" if cond else "FAIL", name, info)
    es = exprs(F)
    P("node count 57", len(es) == 57, len(es))
    b_div = find("MaterialExpressionDivide_0")
    w = wiring(b_div)
    P("b_div.A = Multiply", w[0][0] == "A" and w[0][1].startswith("Multiply"), w)
    P("b_div.B = FunctionInput_1 (WindRefHeightCm)", w[1][1] == "FunctionInput_1", w)
    mul = [e for e in es if e.endswith(":" + w[0][1].replace("", "")) or short(e) == w[0][1]][0]
    mw = wiring(mul)
    P("Multiply.A = ComponentMask_1 (b_z)", mw[0][1] == "ComponentMask_1", mw)
    P("Multiply.B = Length", mw[1][1].startswith("Length"), mw)
    ln = [e for e in es if short(e) == mw[1][1]][0]
    lw = wiring(ln)
    P("Length.in = Transform", lw[0][1].startswith("Transform") and not lw[0][1].startswith("TransformPosition"), lw)
    tr = [e for e in es if short(e) == lw[0][1]][0]
    tw = wiring(tr)
    tp = jl(props(tr, ["transformSourceType", "transformType"]))
    P("Transform in = Constant3Vector", tw[0][1].startswith("Constant3Vector"), tw)
    P("Transform Instance -> World", tp.get("transformSourceType") == "TRANSFORMSOURCE_Instance" and tp.get("transformType") == "TRANSFORM_World", tp)
    cv = [e for e in es if short(e) == tw[0][1]][0]
    c = jl(props(cv, ["constant"]))["constant"]
    P("up vector (0,0,1)", (c["r"], c["g"], c["b"]) == (0, 0, 1), c)
    d = jl(props(find("MaterialExpressionFunctionInput_1"), ["description"]))["description"]
    P("WindRefHeightCm description", d == "World height in cm (after the actor or instance scale) at which the bend is full", d)
    for n, (amp, refh) in MIS.items():
        s = mi_compact(D + n)["scalars"]
        P(n + " WindAmplitudeCm", s.get("WindAmplitudeCm") == amp, s.get("WindAmplitudeCm"))
        if refh is not None:
            P(n + " WindRefHeightCm", s.get("WindRefHeightCm") == refh, s.get("WindRefHeightCm"))
        else:
            P(n + " WindRefHeightCm untouched (no override)", "WindRefHeightCm" not in s, s.get("WindRefHeightCm"))
        st = statics(objpath(D + n))
        P(n + " bWind true", st.get("bWind") is True or (isinstance(st.get("bWind"), dict)), st)
    print("OVERALL", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    w = sys.argv[1]
    if w == "pre":
        guard(); read_bend()
    elif w == "fn":
        build_fn()
    elif w == "savefn":
        save_fn()
    elif w == "mis":
        for n in MIS:
            run_mi(n)
    elif w == "savemis":
        for n in MIS:
            if dirty(D + n):
                save(D + n)
            else:
                print("not dirty, no save", n)
    elif w == "check":
        check()
