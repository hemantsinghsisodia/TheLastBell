"""Reshape both distal forearms and palms on the three existing V11 mesh LODs."""
import bpy
import json
import sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent / "warden_art_v11"
sys.path.insert(0, str(BASE / "scripts"))
from common import local_frame, skeleton, digest

def smooth(t):
    u = np.clip(t, 0, 1)
    return u*u*(3-2*u)

def reform(obj, rig, side, ids, cloth, cuff_contact):
    mesh = obj.data
    wrist, across, dorsal, down = local_frame(rig, side)
    axes = np.array([list(across), list(dorsal), list(down)])
    ids = np.array([i for i in ids if (mesh.vertices[i].co.x>0)==(side=="l")])
    coords = np.array([list(mesh.vertices[i].co) for i in ids])
    local = (coords-np.array(wrist)) @ axes.T
    x,y,t = local.T
    step = .01
    stations = np.arange(-.52, .06, step)
    centers=[]
    radii=[]
    for z in stations:
        section = local[np.abs(t-z)<.019,:2]
        if len(section)<4:
            section=local[np.argsort(np.abs(t-z))[:12],:2]
        low, high = np.percentile(section, [2,98], axis=0)
        centers.append((high+low)*.5)
        radii.append(np.maximum((high-low)*.5,.012))
    def interpolate(series,col):
        return np.interp(t,stations,np.asarray(series)[:,col])
    nx=(x-interpolate(centers,0))/interpolate(radii,0)
    ny=(y-interpolate(centers,1))/interpolate(radii,1)
    radius=np.maximum(np.hypot(nx,ny),.1)
    # Build the distal flexor/extensor volume into the long hollow above the cuff.
    # A continuous falloff keeps the elbow and the interior shackle fit.
    belly=smooth((t+.48)/.22)*smooth((-t-.035)/.058)
    dx=belly*nx/radius*(.013+.004*np.exp(-((t+.19)/.08)**2))
    dy=belly*ny/radius*(.012+.004*np.exp(-((t+.22)/.09)**2))
    # Fill longitudinal grooves by moving each radius partway toward its local oval.
    fill=np.clip(1-radius,0,.33)*.6*belly
    dx+=fill*nx/radius*interpolate(radii,0)
    dy+=fill*ny/radius*interpolate(radii,1)
    for j in np.flatnonzero(belly>.001):
        dist=cloth.find_nearest(Vector(coords[j]))[3]
        factor=smooth((dist-.006)/.025)
        dx[j]*=factor
        dy[j]*=factor
    # Reduce the swollen palm pad across its breadth and depth. The broad falloff
    # includes the thumb mound and web, easing into the individual digit roots.
    pad=smooth((t-.010)/.068)*smooth((.263-t)/.087)
    dx-=x*.235*pad
    dy-=y*.36*pad
    for j in np.flatnonzero((np.abs(dx)+np.abs(dy))>0):
        distance=cuff_contact.find(Vector(coords[j]))[2]
        fraction=smooth(distance/.020)
        dx[j]*=fraction
        dy[j]*=fraction
    shift=np.column_stack((dx,dy,np.zeros(len(t)))) @ axes
    for j in np.flatnonzero(np.linalg.norm(shift,axis=1)>1e-7):
        mesh.vertices[int(ids[j])].co=coords[j]+shift[j]
    corrected=local+np.column_stack((dx,dy,np.zeros(len(t))))
    profiles={}
    for label,distance in [("forearm",-.12),("wrist",-.015),("palm",.09)]:
        sl=np.abs(t-distance)<.012
        if not sl.any(): continue
        profiles[label]=[np.round(np.ptp(points[sl,:2],axis=0)*100,2).tolist() for points in (local,corrected)]
    return profiles

bpy.ops.wm.open_mainfile(filepath=str(BASE/"Warden_Rigged.blend"))
rig=bpy.data.objects["Warden_Rig"]
report={"skeleton":digest(skeleton(rig)),"profiles_width_depth_cm":{}}
for lod in range(3):
    ob=bpy.data.objects[f"SK_Warden_LOD{lod}"]
    mesh=ob.data
    cloth=BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices],[list(p.vertices) for p in mesh.polygons if p.material_index==0])
    ids={i for p in mesh.polygons if p.material_index==3 for i in p.vertices}
    # Include nail and scar detail at digit roots in the same continuous warp.
    digits=("thumb_","index_","middle_","ring_","pinky_")
    ids.update(i for p in mesh.polygons if p.material_index==7 for i in p.vertices
               if any(ob.vertex_groups[g.group].name.startswith(digits) for g in mesh.vertices[i].groups))
    skin_faces=[tuple(p.vertices) for p in mesh.polygons if p.material_index==3]
    cuff_faces=[tuple(p.vertices) for p in mesh.polygons if p.material_index==2]
    coords=[v.co.copy() for v in mesh.vertices]
    skin_tree=BVHTree.FromPolygons(coords,skin_faces)
    cuff_tree=BVHTree.FromPolygons(coords,cuff_faces)
    anchors={i for f,_ in skin_tree.overlap(cuff_tree) for i in skin_faces[f]}
    protected=ROOT/"reports"/"clearance-vertices.json"
    if protected.exists():
        anchors.update(json.loads(protected.read_text()).get(str(lod),[]))
    cuff_contact=KDTree(len(anchors))
    for i in anchors:
        cuff_contact.insert(coords[i],i)
    cuff_contact.balance()
    for side in ("l","r"):
        report["profiles_width_depth_cm"][f"lod{lod}_{side}"]=reform(ob,rig,side,ids,cloth,cuff_contact)
    mesh.update()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"Warden_Rigged.blend"),relative_remap=True)
(ROOT/"reports/profiles.json").write_text(json.dumps(report,indent=2))


