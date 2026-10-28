"""ed_set.py '{"Label": {props...}, ...}' : set LightComponent0 props on EDITOR-world actors by label."""
from h import *
spec = json.loads(sys.argv[1])
for lbl, v in spec.items():
    acts = find_label(lbl, world="editor")
    assert len(acts) == 1, (lbl, acts)
    comp = {"refPath": acts[0]["refPath"] + ".LightComponent0"}
    setp(comp, v)
    print(lbl, props(comp, list(v.keys())))
