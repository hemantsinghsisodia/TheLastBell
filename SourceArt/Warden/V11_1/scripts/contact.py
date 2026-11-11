import bpy,sys,json
from pathlib import Path
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parents[1]
base=R.parent/"warden_art_v11"
bpy.ops.wm.open_mainfile(filepath=str(base/"Warden_Rigged.blend"))
old={i:[v.co.copy() for v in bpy.data.objects[f"SK_Warden_LOD{i}"].data.vertices] for i in range(3)}
bpy.ops.wm.open_mainfile(filepath=str(R/"Warden_Rigged.blend"))
rig=bpy.data.objects["Warden_Rig"]
scene=bpy.context.scene
rows=[]
feedback=R/"reports"/"clearance-vertices.json"
protected=json.loads(feedback.read_text()) if feedback.exists() else {}
for lod in range(3):
    protected_ids=set(protected.get(str(lod),[]))
    ob=bpy.data.objects[f"SK_Warden_LOD{lod}"]
    ob.hide_set(False)
    mesh=ob.data
    changed={v.index for v in mesh.vertices if (old[lod][v.index]-v.co).length>.00001}
    skin=[tuple(f.vertices) for f in mesh.polygons if f.material_index==3 and any(i in changed for i in f.vertices)]
    metal=[tuple(f.vertices) for f in mesh.polygons if f.material_index in (2,5) and any(abs(mesh.vertices[i].co.x)>.30 for i in f.vertices)]
    cloth=[tuple(f.vertices) for f in mesh.polygons if f.material_index==0 and any(abs(mesh.vertices[i].co.x)>.25 and .7<mesh.vertices[i].co.z<1.9 for i in f.vertices)]
    for act in bpy.data.actions:
        rig.animation_data.action=act
        lo,hi=map(int,act.frame_range)
        samples=range(lo*2,hi*2+1) if "--full" in sys.argv else sorted(set([lo*2,hi*2]+list(range(lo*2,hi*2+1,16))))
        collisions=[]
        for frame in samples:
            scene.frame_set(frame//2,subframe=(frame%2)/2)
            posed=ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
            xyz=[v.co.copy() for v in posed.data.vertices]
            surface=BVHTree.FromPolygons(xyz,skin)
            overlaps=[surface.overlap(BVHTree.FromPolygons(xyz,fs)) for fs in (cloth,metal)]
            protected_ids.update(i for result in overlaps for f,_ in result for i in skin[f])
            pairs=[len(result) for result in overlaps]
            if any(pairs):
                collisions.append([frame/2,*pairs])
        rows.append(dict(lod=lod,clip=act.name,samples=len(samples),hits=collisions))
    protected[str(lod)]=sorted(protected_ids)
feedback.write_text(json.dumps(protected))
print(json.dumps(rows))
(R/"reports/pose-check.json").write_text(json.dumps(rows,indent=2))
