"""pie_note.py away|home : move Note_Chains in the PIE world only."""
import sys
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\crypt\r1b")
from h import *
a = find_label("Note_Chains", world="pie"); assert len(a)==1
loc, rot, sc = tf(a[0])
home = [10920.0, -1504.15, -430.0]
z = home[2] + (10000 if sys.argv[1]=="away" else 0)
call(A, "set_actor_transform", {"actor": a[0], "xform": xf([home[0], home[1], z], rot, sc), "worldspace": True})
print(sys.argv[1], tf(a[0])[0])
