# Unreal MCP notes for agents (The Last Bell)

The editor must be open on `C:\Hemant\Prj\Learning\TheLastBell`. Its MCP server is at `http://127.0.0.1:8000/mcp`.
Native MCP tools may be missing from your session. If so, use the helper **`Tools/mcp/ue.py`**:
- CLI: `python ue.py describe <toolset> [tool]` (tool list, or one tool's schema); `python ue.py <toolset> <tool> '<json args>'`.
- Library (preferred): put your script in your own scratch folder and do `sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")`, then `from ue import UE; ue = UE(); ue.call(toolset, tool, args)` (it raises on error).
- If `python` isn't on PATH in Bash, use `C:\Users\heman\AppData\Local\Python\pythoncore-3.14-64\python.exe` from PowerShell, with Windows paths. Write scripts with the Write tool; Bash heredocs with quotes often break.

## Git (IMPORTANT)
Commit ONLY to the currently checked-out `claude/*` branch. Check `git branch --show-current` first. Never switch branches, never merge, never push (see CLAUDE.md).

## Toolsets
- `editor_toolset.toolsets.blueprint.BlueprintTools`: create, compile_blueprint (`warnings_as_errors`), add_variable, write_graph_dsl / read_graph_dsl / get_graph_dsl_docs, get_default_object, list_functions, find_nodes, connect_pins, create_node and more. **Call `get_graph_dsl_docs` before writing graphs.**
- `editor_toolset.toolsets.object.ObjectTools`:
  - `get_properties {instance:{refPath}, properties:[...]}`
  - `set_properties {instance:{refPath}, values:"<JSON STRING>"}`. It refuses to change an array element AND grow the array in one call; split those into two calls.
  - `list_properties`, `search_subclasses`
- `editor_toolset.toolsets.asset.AssetTools`:
  - `find_assets {folder_path, name}`, `exists`, `duplicate {path,new_path}`, `create_folder`
  - `save_assets {asset_paths:[explicit package paths]}` (folder paths don't work)
  - `is_dirty` (pass a package path), `get_referencers`, `get_dependencies`
- `editor_toolset.toolsets.scene.SceneTools`:
  - `find_actors {name:"", tag:"", collision_channels:[]}`, `get_folders`, `get_actors_in_folder`, `set_actor_folder`
  - `add_to_scene_from_class {actor_type, name, xform}`, `add_to_scene_from_asset`, `remove_from_scene`
  - `load_level`, `get_current_level`, `trace_world {start,end}` (returns the distance)
- `editor_toolset.toolsets.actor.ActorTools`: `get_actor_transform`, `set_actor_transform {actor, xform, worldspace}`.
- `EditorToolset.EditorAppToolset`:
  - StartPIE `{options:{bSimulate:false, playMode:"PlayMode_InViewPort", warmupSeconds:N}}`, StopPIE, IsPIERunning
  - CaptureViewport (large base64; pipe it to a file)
- `EditorToolset.LogsToolset`: `GetLogEntries {category:"", pattern:"<regex>", maxEntries:N}`. Always filter; the whole log drops the connection.
- `ConfigSettingsToolset.ConfigSettingsToolset` (project settings), `UMGToolSet.UMGToolSet` (widgets; no widget animations), `editor_toolset.toolsets.material.MaterialTools`.
- `GameplayTagsToolset`: **NEVER write tags with it** (R-18/D-024). Tags are text-edited in `Config/Tags/LBGameplayTags.ini` only while the editor is closed, by the lead.
- The Slate UI automation toolset can't see editor windows, so there's no simulated key input. Use automation tests instead.

## Gotchas
- Object refs are `{"refPath": "/Game/Path/Asset.Asset"}`; BP classes are `/Game/Path/BP_X.BP_X_C`. A BP component template is `<BP>.<BP>_C:<Comp>_GEN_VARIABLE`. A placed actor's component is `<map>.<map>:PersistentLevel.<ActorName>.<Comp>`.
- Template changes do NOT propagate to placed instances that serialized the value; set instances directly.
- `write_graph_dsl` is ADDITIVE (it duplicates events). `read_graph_dsl` may spawn empty `_Event_N` orphans; delete them. Custom events can't take typed params in the DSL. Bind delegates with Create Event plus `set_create_event_function`, or an Assign node.
- Many schemas mark every parameter required; read the schema first. Check every return value.
- BoxExtent: set one axis per call and read it back.
- A headless test run (UnrealEditor-Cmd) holds .umap/.uasset files open, so saving during one fails with "MoveFile". Save first.
- Never check out older commits while the editor is open.
- `ActorTools.set_actor_transform`: always pass location AND rotation AND scale. A partial xform silently resets the missing parts to identity/zero.
- Component edits on placed **Blueprint instances** often don't persist (the call returns True, the read-back or a reload shows the old value). Put per-instance differences in a **child Blueprint** instead (e.g. `BP_TagInteractable_ChapelKey`); if inherited components can't be overridden in the child's defaults through the tools, set them in the child's construction script.
- Collision: `collisionEnabled`/`objectType` and per-channel responses (e.g. Interaction = Ignore) don't persist via `set_properties`; `collisionProfileName` does (e.g. `NoCollision`, `BlockAll`).
- Editor deletes can leave the file on disk (seen with a demo map, its BuiltData and an unreferenced texture). Do not delete `.uasset`/`.umap` by hand; list leftovers and ask the lead.

## Importing meshes (FBX)
- The import options live on the CDO `/Script/UnrealEd.Default__FbxStaticMeshImportData` and are **in memory only**: in every fresh editor session set `vertexColorImportOption = Replace` and `bBuildNanite = true` (false for small/thin meshes) before `StaticMeshTools.import_file` (`import_materials=false, import_textures=false, combine_meshes=true`). `bAutoGenerateCollision=false` keeps only the `UCX_` hulls.
- UE drops material slots no face uses, so assign materials by the slot names that exist. "No smoothing group information" is expected (custom normals). `get_triangle_count` returns the Nanite fallback mesh, not the full mesh.
- Our Blender exports (Tools/blender/kit, Tools/blender/props) already mirror Y for UE; pivots are bottom-left-back (kit) or bottom-centre (props).

## Captures
- `CaptureViewport`: the first frame after `SetCameraTransform` can have stale occlusion; capture twice per pose and keep the second. The connection often resets ("forcibly closed") — retry. The viewport is portrait (761×862).
- Editor helper icons/volume wireframes show in captures; either hide every billboard/sprite/arrow/box/sphere/capsule/brush component, capture, then restore (never save while hidden), or capture during PIE Simulate (no helpers).
- Editor-viewport captures do NOT tick particles or panning materials: capture FX (Niagara, Cascade, fog sheets) in **PIE Simulate**.
- `CaptureAssetImage` returns a placeholder until shaders finish compiling; wait and retry.

## FX and fog
- Niagara: `NiagaraToolset_System.CreateNiagaraSystem` needs a template system (`/Niagara/DefaultAssets/DefaultSystem`; it contains its own "Fountain" emitter — remove it), then `AddEmitter` from `/Niagara/DefaultAssets/Templates/Emitters/*`. Place systems with `add_to_scene_from_asset` (adding a NiagaraActor by class and setting its Asset didn't simulate). Check `GetSystemCompileState` and `GetStackIssues`.
- A **Local Fog Volume is a sphere**: radius = 500 cm × the largest axis scale; non-uniform scale is ignored; `get_actor_bounds` ignores scale. HeightFogFalloff is relative to that radius.
- Engine fog sheets: `/Engine/EngineVolumetrics/Fogsheet/Mesh/S_EV_FogSheet_01` (flat 256×256 plane); stand it up with pitch 90.

## Running tests (a separate process; fine with the editor open)
```
powershell -Command "$l='C:\Hemant\Prj\Learning\TheLastBell\Saved\Logs\<you>.log'; Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' -ArgumentList @('C:\Hemant\Prj\Learning\TheLastBell\TheLastBell.uproject','-ExecCmds=\"Automation RunTests LastBell; Quit\"','-unattended','-nullrhi','-nosplash','-nosound','-NoP4','-log',\"-abslog=$l\") -Wait"
```
Mirror pitfall: robocopy keeps the source file timestamps, so a file restored to an earlier version may NOT be recompiled by UBT. Touch the file after the copy (`(Get-Item f).LastWriteTime = Get-Date`) when you revert and restore.
`InjectInputForAction` bypasses the viewport's ignore-input flag, so input-path tests must also assert `GEngine->GameViewport->IgnoreInput()`.
C++ can't be built in the real project while the editor is open (Live Coding plus the DLL lock). Build and test C++ in the mirror `C:\lbb` (Content is a junction to the real Content), and sync with PowerShell robocopy.

## Framework quick reference
For C++ API names, read `Source/LastBell/`; for architecture, read `Docs/TECHNICAL_DESIGN.md`. The key Blueprints are in `/Game/LastBell/Blueprints/` (Interactables: BP_Door_Base, BP_Lever, BP_TagInteractable, BP_RitualMechanism, BP_TagTrigger, BP_TagVisibility, BP_WardenSilhouette, BP_WardenPlaceholderKill, BP_KillVolume, BP_Inspectable_Note). Data is in `/Game/LastBell/Data/`.

## Floor growth layer, light functions (P7-FIX3 G3)
- `M_LB_Surface` growth layer (`bGapGrowth`, group Growth): wall proximity comes from `MPC_LB_GrowthObstacles` (48 XY boxes, `Ob00..Ob47` = centreX, centreY, halfX, halfY; halfX < 0 = unused), NOT from `DistanceToNearestSurface`: the global distance field returns ~0 in this project (Lumen hardware RT, no GDF), which fills every joint. The DTNS path is kept behind the static switch `bWallUseDistanceField` (default off). Refresh the boxes after moving walls/piers/kerbs: `python Tools/mcp/update_growth_obstacles.py [--dry] [--prefix ...]` (editor open on L_Monastery; ~40 s; add the label prefixes of new structures, e.g. kerbs, arcade, well-head).
- Same-session material A/B: the first recompile of a long-running editor session shifts thumbnail output vs the previously loaded shader (about 6/255 mean on M_LB_Surface); compare two recompiles in the same session, not "before the session" vs "after".
- Light Function materials: `MaterialDomain = "MD_LightFunction"` can be set with `ObjectTools.set_properties` on the material; the output is `MP_EmissiveColor`. Scalar/vector MI parameters work as usual (`MI_LF_*` in /Game/LastBell/Materials/Instances).
- UE drops FBX material slots no face uses (e.g. the arcade column only has MAT_Trim): read `get_material_slots` before `set_material`.

## PCG scatter, helper volumes, sky/fog, night lighting (P7-FIX3 G5/G6)
- PCG: toolset `PCGToolset.PCGToolset`. `SetGraphInstanceParams {pCGVolume:{refPath}, jsonParams:"<JSON string>"}` then `ExecuteGraphInstance {pCGVolume}`; retry up to 3× on a transient error. Graph `/Game/LastBell/PCG/PCG_LB_Overgrowth`, params `PointsPerM2`, `ScaleMin`/`ScaleMax` (vectors), `T1..T4` (family density thresholds). Zone volumes are `PCGV_*` (Generate On Demand); exclusion boxes are actors tagged `LB_PCG_Exclude`. Generated ISM components live on the volume actor: count instances via `perInstanceSMData`. Save the map after executing.
- **Every helper volume must be `collisionProfileName = NoCollision`** (TriggerVolumes, PCG volumes, exclusion brushes). A QueryOnly brush blocks the interaction trace: in G5 the RouteBot could not take the key.
- Sky: the dome is `StaticMeshActor_24` (SM_SkySphere, scale 400) with `MI_Env_NightSky` → engine M_Sky_Panning_Clouds2 (opaque unlit, not bIsSky), so height fog covers it unless `ExponentialHeightFog_1.fogCutoffDistance` excludes it (now 1,000,000). `SkyAtmosphere_1` is hidden (it painted the sky and the distance navy). Change the night look via MI_Env_NightSky, fog inscattering colour and light colours (D-059).
- The scene's blue came from light colours (approach fills, sky light), not the fog or LFVs. Grading: `ColorSaturationShadows` 0.65 on PostProcessVolume_1 (PP_Outdoor_Night), exposure histogram with min = max EV100 1.15.
- Light functions (`lightFunctionMaterial` = `MI_LF_*`) do work on shadowless local lights (G6 flicker check: about 3 % luma change on the lit wall between two captures).
- Luma measurement for lighting targets: Y = 0.2126 R + 0.7152 G + 0.0722 B on 8-bit sRGB ÷ 255, full frame, PIE Simulate, second of two captures; report mean, fraction < 0.02, p99 and max (FIX3 plan B2).
- After an editor restart it may open on L_MainMenu: load L_Monastery before any query. The capture size can also change (766×824 vs 760×808), so crop coordinates shift slightly.

## BP template edits (P8-6b)
- Compiling a Blueprint that has placed instances marks the level dirty, and `SceneTools.load_level` then refuses ("Save the level before loading it"). Writing a component template with `set_properties` dirties the level too.
- `AssetTools.duplicate` returns False while PIE or Simulate is running; stop PIE before duplicating or creating assets.
- Placed instances keep their old component values (mesh, override materials, transform) after a template write and compile, even if they equalled the old template. Treat this as "template edits don't reach placed instances": use dressing actors or NoCollision shells (e.g. `Mech_Shell_*`), or change a shared material instance's default (it propagates to every user that does not override the parameter).
- Never save the map while a template and its placed instance differ: the instance's old value would be serialized as an explicit override. Revert the template (write back, compile, save the BP) first.
- A headless `UnrealEditor-Cmd -ExecCmds="py ..."` did not run the script in this project (the process hung); don't rely on it to inspect the on-disk map.

## Level dressing and lighting (Phase 8)
- Collision on placed StaticMeshActors: set `bodyInstance.collisionProfileName` together with `bUseDefaultCollision=false`, then read both back (setting `collisionProfileName` alone doesn't stick).
- Kit pieces: inner face = mesh-local Y 0; compute yaw/roll from read-back bounds (e.g. the east wall needed yaw −90, not 90). Roof slabs: roll 50 (north), roll 50 + yaw 180 with X offset +1000 (south).
- Animated props: `add_to_scene_from_asset` with a SkeletalMesh gives a SkeletalMeshActor; set `animationMode` AnimationSingleNode + the anim asset + looping/playing and read back. Its first-frame pose can sit lower than the reference pose: measure bounds after setting the animation.
- Wall decals placed with DecalActor came out rotated 90°; fix with roll 90 and check the glyph orientation in a capture. DecalSize is a half-extent.
- Light-pool decals (Translucent, Unlit, emissive) add light on the floor (verified by on/off captures); `Additive` is not allowed in the decal domain.
- Lit-state captures of puzzle candles: in PIE Simulate the PIE-world instances' `Flame`/`FlameLight` visibility can be toggled for a capture (never in the editor world).
- A wide even wash on a ceiling is easier with a RectLight facing up than with a spot (spots made hot ellipses).
- Exposure: post-process volume boundaries change EV100 abruptly; give bounded PP volumes a `BlendRadius` (P8-9d: the 'doorway fog' was an EV jump at the chapel door).
- Shadowless spot lights placed outside a wall light the interior through the wall; light coming through a window needs CastShadows (and Cast Volumetric Shadow) on, and the glass mesh CastShadow off.
- `M_LB_Surface` roughness: use `RoughnessMin`/`RoughnessMax` in an MI to remove an unwanted sheen.
- Grime decals (`M_LB_Decal_Grime`): wall decals rotation (0, yaw, 90) with size (depth, vertical, horizontal); floor decals (-90, yaw, 0) with size (depth, v, u). `MI_Decal_Leaking006_Wall` also needs roll 90.

## Crypt and Phase 9 fix sets (P9)
1. **Visible-false shell (D-068).** The greybox crypt shell keeps its collision but is `bVisible=false`, so navmesh, WalkPaths, RouteBot, Kill_Pit and the Warden routes keep the tested collision. Apply and verify with `python Tools/crypt/place_crypt.py --hide-greybox` / `--verify-greybox` (reads back `bVisible` and collision, runs the trace_world checks). Any gap in the art shows the black `MI_Crypt_Backdrop` box.
2. **`Tools/crypt` scripts** (editor open on L_Monastery; none of them may spawn actors while PIE runs):
   - `place_crypt.py` places the generated layout `Docs/plans/p9_d1_layout.json` (from `gen_crypt_layout.py`): `--cats <names>` (idempotent: removes the category's actors first), `--only <text>` (records whose id contains the text), `--check` (read-back only, makes no edits), `--fix-collision`, `--verify-blockers`, `--skull-offset`. A dress record's `mi_slots` is a per-slot MI override ({slot index: MI name}). `--cats light` places the 16 lights, and `--cats light --check` also reads back lumens, radius, cones, scattering, shadows and `bCastVolumetricShadow` per record.
   - `place_lighting.py` (`greybox`, `fires`, `shafts`, `lfv`, `pp`, `check`) does fires, shaft cards, `LFV_Crypt_Flood` and `PP_Crypt`. `luma_report.py` gives the B2 luma metrics of capture PNGs (mean, fraction < 0.02, p99, central-40 % mean, pool median, `--plaque` contrast). `lane_check_crypt.py` is the lane check (`Docs/ArtTest/crypt/lane_check_p9.md`).
   - `capture_poses.py <poses.json> <out_dir>` flags: `--editor` (editor viewport, about 0.3 s, no PIE), `--double` (keep the second capture), `--raise`, `--light` / `--light-offset F R U` (PIE-only candle proxy `TMP_CaptureLight`; P9-7 used `36 14 -10`), `--suffix`, `--prefix`, `--only a,b`, `--settle S`, `--timeout N`, `--force`, `--log`. Circuit breaker: 2 consecutive poses that fail all their tries abort the run (exit code 3); at most 6 tries per pose. Poses live in `Tools/crypt/poses/` (`p9l_poses.json` for the P9-7 lighting poses).
3. **NoCollision on placed actors:** set both `bodyInstance.collisionProfileName = NoCollision` and `bodyInstance.collisionEnabled` (and `bUseDefaultCollision=false`), then read them back. With only the profile name, the `CA_Lining_*` actors still blocked traces (P9-6a R4; `place_crypt.py --fix-collision`).
4. **Water edge fade (`M_LB_Water`, D1.4).** The masked water planes fade to nothing where the water spreads into a room. Per MI: `SizeXCm`, `SizeYCm` (plane size) and `EdgeFadeXMinCm` / `EdgeFadeXMaxCm` / `EdgeFadeYMinCm` / `EdgeFadeYMaxCm` (0 = off), driven by the plane's UV, dithered with `DitherTemporalAA`. `MI_Crypt_Water_Flood_W` (495 x 390) fades at its low-X end (`EdgeFadeXMinCm` 200), `_Flood_E` (395 x 390) at its high-X end (`EdgeFadeXMaxCm` 200). If a fade ever appears at the wrong end, swap Min and Max in the MI. The ripple normal is subtle by design, so `RippleNormalScale` (default 3) compensates.
5. **Child-BP swaps (D-071, D1.14).** The crypt child Blueprints are `BP_TagInteractable_CryptCrank`, `BP_TagVisibility_CryptGate`, `BP_TagVisibility_CryptRubble`, `BP_RitualMechanism_CryptWinch` (and later the R2 children, item 10 onwards).
   - The construction script sets the mesh and the Interaction Block.
   - The DSL cannot author a call to the parent construction script, so the children copy the parent's body. If the parent's construction script changes, update the children (R-40).
   - InteractComp defaults can't be overridden in a child (the template write doesn't persist). Put values in an instance-editable variable that the child's construction script feeds to the component (the winch's `RequiredTags` goes to `SetRequiredStateTags`).
   - Swap procedure (D-051): dump the instance before and after, keep the label, folder and values; diff shows only the allowed differences; re-dump after save and reload.
6. **Captures.**
   - `CaptureViewport` resets after about 21 s when the editor window is minimized, and fails often when ordinary windows cover it (about one pose in three). Keep the editor visible and uncovered during a capture run; use `--raise` and the circuit breaker, and put poses that still fail on the owner checklist instead of looping.
   - The PIE CPU throttle (`EditorPerformanceSettings.bThrottleCPUWhenNotForeground` false) is set in memory only; set it again after an editor restart.
   - Use `--double` against stale frames after `SetCameraTransform`.
7. **PIE.**
   - SceneTools refuses to spawn actors during PIE. Retarget a PIE-world copy of an existing light instead (the candle proxy was a retargeted copy of `Light_Approach_0`). Never change the editor-world light.
   - `bHidden` / `bVisible` writes don't update the render state of lights in PIE; zero the intensity or move the actor.
   - Asset saves fail during PIE; save after `StopPIE`.
8. **`T_LB_White_Gray`** is a TC_Alpha mask and renders magenta as a base colour. Use a tinted base colour with `Desaturation` 1.0 (plaque candidate B2, `MI_Crypt_PlaqueSlate`). The plaque was later replaced by a readable note (D-073), but the texture fact stands.
9. **Material-instance toolset:** `editor_toolset.toolsets.material_instance.MaterialInstanceTools`; it needs full object paths (`/Game/...Name.Name`).
10. **Replacing a mesh referenced by a BP (D1.28).** `StaticMeshTools.import_file` refuses an existing path, and `AssetTools.delete` nulls the in-memory references. Procedure: point the BP's `SetStaticMesh` pin at `/Engine/BasicShapes/Cube` and compile; delete the mesh; import at the same path; restore the slot MIs; point the pin back and compile; save one package per call.
11. **Components added to a child BP (D1.29).** Placed instances don't pick up template values, so the construction script must set mesh, transform, material and collision. Instance `set_properties` on `relativeLocation` / `relativeScale3D` applies only one axis when the others equal the template's, so set one axis per call.
12. **Saving (D1.27).** Save exactly one package per `save_assets` call and check `is_dirty` after each: the editor deadlocked inside a multi-package save (game thread stuck in `InternalPromptForCheckoutAndSave`, CPU idle, window not responding). If an MCP call hangs for more than about 180 s, stop all editor calls. Recovery: End task (equivalent to Don't Save), then skip the autosave restore.
13. **Simple collision on imported Blender props (D1.27).** A mesh without UCX gets no simple collision, so the interaction trace misses it. Add a 1-hull convex (`StaticMeshTools`); never use complex as simple on moving parts.
14. **Gobos and lighting channels (D1.23, D1.30).** A light is masked by hidden actors (`bHiddenInGame`, `bCastHiddenShadow`, lighting Channel1 only) on spots that use channels 0+1. Simulate ignores `bHiddenInGame`, so gobos show there as bright shapes; judge them in normal Play. Static actors ignore `set_actor_transform` in PIE: to A/B a gobo, toggle `castShadow` on its components.
15. **Volumetric fog stepping (D1.30).** Stepped slabs along spot-light beams come from `bCastVolumetricShadow`, not from the scattering amount. Turn it off on beam lights that pass bars or grates (G1/G2 now do).
