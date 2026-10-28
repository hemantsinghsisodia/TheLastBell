from h import *
import random, numpy as np
from PIL import Image, ImageDraw
P = "/Game/LastBell/Maps/L_Monastery.L_Monastery:PersistentLevel."
for n in ["StaticMeshActor_750","StaticMeshActor_751","StaticMeshActor_752"]:
    b = call(A,"get_actor_bounds",{"actor":{"refPath":P+n}})
    print(n, b["min"], b["max"])
# directional light
pitch, yaw = -38.0, 35.0
cp,sp,cy,sy = math.cos(math.radians(pitch)),math.sin(math.radians(pitch)),math.cos(math.radians(yaw)),math.sin(math.radians(yaw))
d = np.array([cp*cy,cp*sy,sp]); right = np.array([-sy,cy,0.0]); up = np.array([-sp*cy,-sp*sy,cp])
print("d",d,"right",right,"up",up)
# lancets
YIN = -750.0
res = {}
for s,(gx,top) in {"S1":(6500,862),"S2":(7500,1010),"S3":(8500,1010)}.items():
    c = np.array([gx,-790.5,(450+top)/2.0])
    hx, hz = 70.0,(top-450)/2.0
    corners = [c+np.array([sx*hx,0,sz*hz]) for sx in (-1,1) for sz in (-1,1)]
    t = (YIN+10-c[1])/d[1]
    pos = c + t*d
    ys = [float(np.dot(k-c,right)) for k in corners]; zs=[float(np.dot(k-c,up)) for k in corners]
    w = 0.95*(max(ys)-min(ys)); h = 0.95*(max(zs)-min(zs))
    res[s] = {"c":c.tolist(),"t":t,"pos":pos.tolist(),"w":w,"h":h}
    print(s, "c",c,"t",t,"pos",pos,"w",w,"h",h)
# roof
def ue_axes(pitch,yaw,roll):
    sp,cp=math.sin(math.radians(pitch)),math.cos(math.radians(pitch))
    sy,cy=math.sin(math.radians(yaw)),math.cos(math.radians(yaw))
    sr,cr=math.sin(math.radians(roll)),math.cos(math.radians(roll))
    return (np.array([cp*cy,cp*sy,sp]),np.array([sr*sp*cy-cr*sy,sr*sp*sy+cr*cy,-sr*cp]),np.array([-(cr*sp*cy+sr*sy),cy*sr-cr*sp*sy,cr*cp]))
rng = random.Random(441+7)
Y_TOP,Y_BOT=21.0*14.0,21.0*47.0
rowsy=[Y_TOP+21.0*i for i in range(34)]
left=[250.0+rng.uniform(-30.0,22.0) for _ in range(33)]
right_=[750.0+rng.uniform(-22.0,30.0) for _ in range(33)]
poly=[]
for i in range(33): poly+=[(left[i],rowsy[i]),(left[i],rowsy[i+1]-1.0)]
for i in range(32,-1,-1): poly+=[(right_[i],rowsy[i+1]-1.0),(right_[i],rowsy[i])]
pts=[]; cyh=(Y_TOP+Y_BOT)*0.5
for k in range(20):
    a=2*math.pi*k/20+rng.uniform(-0.08,0.08)
    f=rng.uniform(0.66,1.0) if k%2==0 else rng.uniform(0.86,1.04)
    pts.append((500.0+240.0*f*math.cos(a), cyh+335.0*f*math.sin(a)))
def mask(p):
    im=Image.new("L",(1000,1200),0); ImageDraw.Draw(im).polygon([(x,y) for x,y in p],fill=1); return np.asarray(im,dtype=bool)
m = mask(poly)&mask(pts)
ys_,xs_=np.nonzero(m)   # rows=y, cols=x
xmin,xmax,ymin,ymax = xs_.min(),xs_.max(),ys_.min(),ys_.max()
cx_,cy_ = xs_.mean(), ys_.mean()
print("hole bbox x",xmin,xmax,"y",ymin,ymax,"centroid",cx_,cy_,"area",m.sum())
xa,ya,za = ue_axes(0,180,50)
loc = np.array([7000.0,0,2165.0])
w2 = lambda x,y,z: loc+xa*x+ya*y+za*z
print("pivot check (z=12)", w2(cx_,cy_,12.0), "expected (6496.4,-420.3,1682.8)")
# inner surface z=0
cen0 = w2(cx_,cy_,0.0)
corners=[w2(x,y,0.0) for x in (xmin,xmax) for y in (ymin,ymax)]
t = -10.0/float(np.dot(d,za))
pos = cen0 + t*d
bc = np.mean(corners,axis=0)
ys=[float(np.dot(k-bc,right)) for k in corners]; zs=[float(np.dot(k-bc,up)) for k in corners]
w=0.95*(max(ys)-min(ys)); h=0.95*(max(zs)-min(zs))
# use bbox centre rather than centroid for placement? spec: built the same way (c = opening centre). use bbox centre
bcen = w2((xmin+xmax)/2,(ymin+ymax)/2,0.0)
pos_b = bcen + t*d
print("roof t",t,"pos(centroid)",pos,"pos(bbox centre)",pos_b,"w",w,"h",h)
res["Roof"]={"c":bcen.tolist(),"c_centroid":cen0.tolist(),"t":t,"pos":pos_b.tolist(),"w":w,"h":h,"hole_bbox":[int(xmin),int(xmax),int(ymin),int(ymax)]}
res["_dir"]={"d":d.tolist(),"pitch":pitch,"yaw":yaw}
json.dump(res,open(SCR+r"\geom.json","w"),indent=1)
