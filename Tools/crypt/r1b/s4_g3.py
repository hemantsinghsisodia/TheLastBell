"""R1-B step 2: re-aim L_Crypt_Moon_G3 at Note_Chains, re-orient SA_Crypt_G3. usage: s4_g3.py [lumens]  (editor world)"""
from h import *
import math
lm = float(sys.argv[1]) if len(sys.argv) > 1 else None
def unit(v):
    n = math.sqrt(sum(c * c for c in v)); return [c / n for c in v]
def aim_dir(rot):
    p, y = math.radians(rot[0]), math.radians(rot[1]); return [math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p)]
def cyl_rot(d, flip=False):
    h = math.hypot(d[0], d[1]); return [math.degrees(math.atan2(-h, d[2])), math.degrees(math.atan2(d[1], d[0])) if h > 1e-9 else 0.0, 180.0 if flip else 0.0]
sp = find_label("L_Crypt_Moon_G3", world="editor")[0]
loc, rot, sc = tf(sp)
print("G3 before", loc, rot)
call(A, "set_actor_transform", {"actor": sp, "xform": xf(loc, (-65.3, 137.3, 0.0), sc), "worldspace": True})
comp = {"refPath": sp["refPath"] + ".LightComponent0"}
v = {"attenuationRadius": 550.0}
if lm: v["intensity"] = lm
setp(comp, v)
print("G3 after", tf(sp), props(comp, ["attenuationRadius", "intensity", "castShadows", "innerConeAngle", "outerConeAngle"]))
d = unit(aim_dir((-65.3, 137.3, 0)))
st = [loc[i] + d[i] * 15 for i in range(3)]
far = [loc[i] + d[i] * 1200 for i in range(3)]
dist = call(S, "trace_world", {"start": dict(zip("xyz", st)), "end": dict(zip("xyz", far))})
length = 15 + float(dist)
hit = [loc[i] + d[i] * length for i in range(3)]
print("trace dist", dist, "length", length, "hit", [round(x, 1) for x in hit], "note at (10920,-1504,-430)")
sa = find_label("SA_Crypt_G3", world="editor")[0]
o_loc, o_rot, o_sc = tf(sa)
ctr = [loc[i] + d[i] * length * 0.5 for i in range(3)]
rr = cyl_rot(d, False)
nsc = (2.0, 2.0, length / 100.0)
call(A, "set_actor_transform", {"actor": sa, "xform": xf(ctr, rr, nsc), "worldspace": True})
print("SA old", [round(x, 1) for x in o_loc], [round(x, 2) for x in o_rot], [round(x, 3) for x in o_sc])
print("SA new", [round(x, 1) for x in tf(sa)[0]], [round(x, 2) for x in tf(sa)[1]], [round(x, 3) for x in tf(sa)[2]])
