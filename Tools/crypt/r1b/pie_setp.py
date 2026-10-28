"""pie_setp.py <label> '<json props>' : set arbitrary light-component props on the PIE copy."""
from h import *
acts = find_label(sys.argv[1], world="pie")
assert len(acts) == 1
comp = {"refPath": acts[0]["refPath"] + ".LightComponent0"}
v = json.loads(sys.argv[2])
setp(comp, v)
print(sys.argv[1], props(comp, list(v.keys())))
