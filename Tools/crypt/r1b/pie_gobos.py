"""pie_gobos.py '<json props>' : set StaticMeshComponent0 props on all 16 PIE-world gobo actors."""
from h import *
v = json.loads(sys.argv[1])
n = 0
for k in ["S1", "S2", "S3", "Roof"]:
    for t in "TBLR":
        a = find_label("Gobo_Moon_%s_%s" % (k, t), world="pie")
        assert len(a) == 1, (k, t, a)
        comp = {"refPath": a[0]["refPath"] + ".StaticMeshComponent0"}
        setp(comp, v)
        n += 1
print(n, props({"refPath": a[0]["refPath"] + ".StaticMeshComponent0"}, list(v.keys())))
