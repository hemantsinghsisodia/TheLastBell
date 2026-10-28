"""pie_gobo_move.py dz : move all 16 PIE-world gobos by dz in Z (PIE only)."""
from h import *
dz = float(sys.argv[1])
for k in ["S1", "S2", "S3", "Roof"]:
    for t in "TBLR":
        a = find_label("Gobo_Moon_%s_%s" % (k, t), world="pie")
        assert len(a) == 1
        loc, rot, sc = tf(a[0])
        call(A, "set_actor_transform", {"actor": a[0], "xform": xf([loc[0], loc[1], loc[2] + dz], rot, sc), "worldspace": True})
print("moved", dz, tf(a[0])[0])
