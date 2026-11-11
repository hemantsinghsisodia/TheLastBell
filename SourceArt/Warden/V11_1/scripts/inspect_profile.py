import sys,bpy,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[1]
V=R.parent/'warden_art_v11'
sys.path.insert(0,str(V/'scripts'))
from common import local_frame
bpy.ops.wm.open_mainfile(filepath=str(V/'Warden_Rigged.blend'))
o=bpy.data.objects['SK_Warden_LOD0'];a=bpy.data.objects['Warden_Rig']
print('shapes',o.data.shape_keys, 'custom normals',o.data.has_custom_normals)
print('slots', [m.name for m in o.data.materials])
print('images',[(i.name,bool(i.packed_file)) for i in bpy.data.images][:30])
W,X,B,D=local_frame(a,'l')
print('W',W,'elbow',a.data.bones['lowerarm_l'].head_local)
for mat in [3,2]:
 ids={i for p in o.data.polygons if p.material_index==mat for i in p.vertices if o.data.vertices[i].co.x>.1}
 vs=np.array([list(o.data.vertices[i].co) for i in ids])
 z=(vs-W[:])@np.array([X[:],B[:],D[:]]).T
 for t in np.arange(-.59,.29,.015):
    sel=z[(abs(z[:,2]-t)<.0076)]
    if len(sel)>3:print(mat, round(t*100,1),len(sel),'minmaxX/B',np.round(np.r_[sel[:,:2].min(axis=0),sel[:,:2].max(axis=0)]*100,1))
for bn in ['hand_l','middle_01_l','index_01_l','thumb_01_l','pinky_01_l']:
 p=a.data.bones[bn].head_local-W; print(bn,[round(100*p.dot(axis),1) for axis in (X,B,D)])
