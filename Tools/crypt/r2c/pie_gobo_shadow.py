import sys
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\crypt\r1b")
from h import *
v = json.loads(sys.argv[1])
names = ["Gobo_Moon_Roof"] + ["Gobo_Moon_%s_%s" % (k, t) for k in ("S1", "S2", "S3") for t in "TBLR"]
for n in names:
    a = find_label(n, world="pie"); assert len(a) == 1, n
    setp({"refPath": a[0]["refPath"] + ".StaticMeshComponent0"}, v)
print(len(names), props({"refPath": a[0]["refPath"] + ".StaticMeshComponent0"}, list(v.keys())))
