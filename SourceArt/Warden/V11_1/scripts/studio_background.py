from pathlib import Path
R=Path(__file__).resolve().parents[1]
s=R.parent/'unreal_validation/Scripts/render_warden_v11_1.py'
code=s.read_text()
start="    report['lights']=[]"
studio="""    # A mid-grey backing gives a readable outline for dark fingers and iron.
    studio_path='/Game/WardenArtV11_1/Preview'
    mat_name='M_ReviewBackdrop'
    mat_path=studio_path+'/'+mat_name
    mat=unreal.load_asset(mat_path) if unreal.EditorAssetLibrary.does_asset_exist(mat_path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(mat_name,studio_path,unreal.Material,unreal.MaterialFactoryNew())
    mat.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    edit=unreal.MaterialEditingLibrary
    edit.delete_all_material_expressions(mat)
    tone=edit.create_material_expression(mat,unreal.MaterialExpressionConstant3Vector,-200,0)
    tone.set_editor_property('constant',unreal.LinearColor(2.8,2.8,2.8,1))
    assert edit.connect_material_property(tone,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    edit.recompile_material(mat)
    assert unreal.EditorAssetLibrary.save_loaded_asset(mat,False)
    label='Neutral inspection backdrop'
    backdrop=next((a for a in actors.get_all_level_actors() if a.get_actor_label()==label),None)
    if backdrop is None:
        backdrop=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(-140,0,160))
        backdrop.set_actor_label(label)
    sm=backdrop.static_mesh_component
    sm.set_mobility(unreal.ComponentMobility.MOVABLE)
    sm.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    sm.set_material(0,mat)
    sm.set_editor_property('cast_shadow',False)
    backdrop.set_actor_scale3d(unreal.Vector(.025,18,18))
"""
if studio not in code:
    code=code.replace(start,studio+start)
    code=code.replace("light.set_intensity(45. if warm else 18.)","light.set_intensity(45. if warm else 24.)\n            light.set_light_color(unreal.LinearColor(1.,.98,.96,1.) if warm else unreal.LinearColor(.9,.95,1.,1.))")
    code=code.replace("set_intensity(15.)","set_intensity(23.)").replace("LinearColor(1.,.9,.75,1.)","LinearColor(.98,.98,1.,1.)").replace("'intensity':15.","'intensity':23.")
    s.write_text(code)

