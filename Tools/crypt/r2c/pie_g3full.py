"""pie_g3full.py lumens inner outer [aimx aimy aimz]  (PIE world only): sets G3 intensity, cone angles and (optionally) re-aims at the point."""
import sys
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\crypt\r1b")
from h import *
a=find_label("L_Crypt_Moon_G3",world="pie"); assert len(a)==1
comp={"refPath":a[0]["refPath"]+".LightComponent0"}
setp(comp,{"intensity":float(sys.argv[1]),"innerConeAngle":float(sys.argv[2]),"outerConeAngle":float(sys.argv[3])})
if len(sys.argv)>4:
    loc,rot,sc=tf(a[0]); aim=[float(v) for v in sys.argv[4:7]]
    d=[aim[i]-loc[i] for i in range(3)]; n=math.sqrt(sum(c*c for c in d)); d=[c/n for c in d]
    pitch=math.degrees(math.asin(d[2])); yaw=math.degrees(math.atan2(d[1],d[0]))
    call(A,"set_actor_transform",{"actor":a[0],"xform":xf(loc,(pitch,yaw,0.0),sc),"worldspace":True})
print(props(comp,["intensity","innerConeAngle","outerConeAngle","attenuationRadius"]), tf(a[0])[1])
