import bpy,sys
from pathlib import Path
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parents[1];V=R.parent/'warden_art_v11';sys.path.insert(0,str(V/'scripts'))
from common import local_frame
for n in (V,R):
 bpy.ops.wm.open_mainfile(filepath=str(n/'Warden_Rigged.blend'));a=bpy.data.objects['Warden_Rig']
 for l in range(3):
  o=bpy.data.objects[f'SK_Warden_LOD{l}'];m=o.data;co=[v.co.copy() for v in m.vertices]
  polys=[[tuple(p.vertices) for p in m.polygons if p.material_index==s] for s in (3,2,5)]
  trees=[BVHTree.FromPolygons(co,p) for p in polys];w,x,b,d=local_frame(a,'l')
  for num in (1,2):
   pairs=trees[0].overlap(trees[num]);ids={i for face,_ in pairs for i in polys[0][face] if co[i].x>.25}
   if ids:print(n.name,l,num,len(pairs),min((co[i]-w).dot(d) for i in ids),max((co[i]-w).dot(d) for i in ids))
