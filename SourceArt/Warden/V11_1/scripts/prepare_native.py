"""Prepare revision-scoped variants of the isolated project's V11 import and review jobs."""
from pathlib import Path
import sys
assert sys.version_info[:3] == (3,14,9)
R=Path(__file__).resolve().parents[1]
scripts=R.parent/"unreal_validation/Scripts"
for name in ("import_warden","materials","update_wool","check","verify_saved","render_warden"):
    source=(scripts/f"{name}_v11.py").read_text(encoding="utf-8")
    source=source.replace("WardenArtV11","WardenArtV11_1").replace("-v11.json","-v11_1.json")
    if name=="import_warden":
        source=source.replace("'warden_art_v11'","'warden_art_v11_1'")
    if name=="render_warden":
        source=source.replace("Previews/V11'","Previews/V11_1'").replace("world,1200,1200","world,800,960")
        start=source.index("    views=[")
        end=source.index("    state=",start)
        source=source[:start]+"""    # Match Blender orthographic cameras in UE's +X-forward centimetre frame.
    component.set_editor_property('projection_type',unreal.CameraProjectionMode.ORTHOGRAPHIC)
    def ue(p):
        return (-100*p[1],-100*p[0],100*p[2])
    cameras=[('hand',(.9,-1.5,1.2),(.47,-.16,1.12),.70),
             ('opposite-hand',(-.95,-1.55,1.22),(-.47,-.16,1.12),.70),
             ('forearm',(.95,-1.65,1.55),(.48,-.14,1.48),.95)]
    views=[(rev+'-'+key,ue(pos),ue(look),scale*100*800/960)
           for rev in ('v11','v11_1') for key,pos,look,scale in cameras]
"""+source[end:]
        start=source.index("                for figure in")
        end=source.index("                capture.set_actor_location",start)
        source=source[:start]+"""                rev='/Game/WardenArtV11_1' if name.startswith('v11_1-') else '/Game/WardenArtV11'
                for figure in actors.get_all_level_actors():
                    if isinstance(figure,unreal.SkeletalMeshActor):
                        c=figure.skeletal_mesh_component
                        c.set_skeletal_mesh_asset(unreal.load_asset(rev+'/Meshes/SK_Warden'))
                        c.override_animation_data(unreal.load_asset(rev+'/Animations/AN_Warden_Idle'),False,False,0.,0.)
                        c.set_update_animation_in_editor(True)
                        c.set_forced_lod(1)
                component.set_editor_property('ortho_width',fov)
"""+source[end:]
        source=source.replace("                component.fov_angle=fov","                report.setdefault('views',{})[name]={'mesh':c.skeletal_mesh_asset.get_path_name(),'position':pos,'look_at':look,'ortho_width_cm':fov}")
    (scripts/f"{name}_v11_1.py").write_text(source,encoding="utf-8")
