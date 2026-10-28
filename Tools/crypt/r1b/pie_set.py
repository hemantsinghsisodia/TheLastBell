"""usage: pie_set.py '{"Light_Chapel_MoonRect_S1": 123, ...}'  sets intensity on the PIE copies (by label); label 'spots0' zeroes the 4 moon spots."""
from h import *
spec = json.loads(sys.argv[1])
if spec.pop("spots0", False):
    for l in ["Light_Chapel_Moon_S1","Light_Chapel_Moon_S2","Light_Chapel_Moon_S3","Light_Chapel_Moon_Roof"]:
        spec[l] = 0.0
for lbl, v in spec.items():
    acts = find_label(lbl, world="pie")
    assert len(acts) == 1, (lbl, acts)
    comp = {"refPath": acts[0]["refPath"] + ".LightComponent0"}
    setp(comp, {"intensity": v})
    print(lbl, acts[0]["refPath"].split(":")[-1], props(comp, ["intensity"]))
