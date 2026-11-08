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
For C++ API names, read `Source/LastBell/`; for architecture, read `Docs/TECHNICAL_DESIGN.md`. The key Blueprints are in `/Game/LastBell/Blueprints/` (Interactables: BP_Door_Base, BP_Lever, BP_TagInteractable, BP_RitualMechanism, BP_TagTrigger, BP_TagVisibility, BP_WardenApparition, BP_KillVolume, BP_Inspectable_Note). Data is in `/Game/LastBell/Data/`.

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

## Bell tower and cloister (P10)
1. **Foreground captures (D1.22).**
   - While the Unreal Editor is not the foreground window, every viewport call resets after about 19 s, including `SetCameraTransform`, not only `CaptureViewport`.
   - While the editor is throttled in the background, `CaptureEditorImage` returns a stale frame.
   - So a capture run needs the owner: they bring Unreal to the front and leave the PC alone.
   - Use `Tools/crypt/capture_session.py`. It waits for the foreground before each attempt and restores the throttle.
2. **Slow first frames (D1.22).** The first views of new material permutations took up to 60 s each. Use `--timeout 15 --settle 3` (the `capture_session.py` defaults).
3. **PIE Simulate for lighting judgement (D1.24).**
   - Simulate captures show no editor sprites and give the true exposure, so judge lighting and luma only on them.
   - Use `capture_session.py --mode simulate --luma <json> [--plaque <pose>]`.
   - Use editor-mode captures (`--mode editor --suffix _ed`) for geometry and dressing only.
4. **`capture_session.py` reference** (`python Tools/crypt/capture_session.py <poses.json> <out_dir> --prefix P [options]`).
   - Options: `--suffix S` (default none), `--mode simulate|editor` (default simulate), `--only a,b`, `--force`, `--max-wait 3600`, `--fg-wait 1800`, `--attempts 5`, `--timeout 15`, `--settle 3`, `--log-dir DIR` (default `Saved\Logs\captures`), `--luma JSON_OUT`, `--plaque POSE`, `--dry-run` (prints the plan and the command lines; never imports `ue` or contacts the editor).
   - Poses whose PNG exists are skipped unless `--force`. Each attempt runs `capture_poses.py --double --raise --force` on the poses not yet captured in this session; the circuit breaker (exit 3 of `capture_poses.py`) rests 60 s and allows one single-pose test, and a second trip stops the session.
   - Exit codes: 0 every pose captured in this session (or nothing to capture); 1 some missing (`missing: a,b,...`); 2 the editor never became the foreground window (no captures taken); 3 editor mode and PIE is running (nothing changed); 4 unknown pose name in `--only`.
   - The throttle is restored to the value read at the start; PIE is stopped only if the session started it.
   - Status: validated live in P10-8d (F7: 15/15 poses; re-capture 5/5; PIE stopped and the throttle restored to its original value both times). Expect 1-4 failed attempts per pose on slow frames; the tool retries them.
5. **`set_properties` `values` is a JSON string** (`json.dumps({...})`), not an object. This applies to every `ObjectTools.set_properties` call.
6. **Root-component world box (D1.21).**
   - For an actor's root component, `relativeLocation` / `relativeRotation` / `relativeScale3D` already are the world transform.
   - When composing a component's world box from the parent chain, never apply the root's relative transform on top of the actor transform.
   - In P10-6a the double-counted root put the capstan chain start about 50 cm above the drum. The fix is in `Tools/belltower/p10_6b_checks.world_box`; reuse that function.
7. **Light component paths.** `<map>.<map>:PersistentLevel.<Actor>.LightComponent0` covers point, spot and directional lights. Sky light: `.SkyLightComponent0`; height fog: `.HeightFogComponent0`.
8. **No console or CVar setter over MCP** (only `SearchCVars`). `r.*` settings, `scalability` and `stat` commands are typed by the owner in a PIE window.
9. **`Tools/belltower` scripts** (editor on `L_Monastery`, no PIE, one editor-touching process at a time):
   - `gen_tower_layout.py`: the generator. It writes `Docs/plans/p10_d1_layout.json` and `p10_d1_tables.md` (never hand-edit them) and runs 54 checks, including the lane checks.
   - `place_tower.py`:
     - `--cats` (the order `block wall tower stair arcade vault roof floor garth door doorleaf dress`), `--only`, `--check`, `--fix-collision`;
     - `--hide-greybox` / `--verify-greybox`, `--ground`, `--perim`.
   - `place_lighting_p10.py`: `greybox | lights | lfv | pp | shafts | check`. `lights` places point and spot records; `check` gave 55/55 after P10-8d (51/51 after P10-7b).
   - `bp_swap.py`: the dump and diff for child-BP swaps (D-071 procedure).
   - `p10_6a_checks.py` (dressing checks, 29 lines; it logs about 29 harmless `staticMesh could not be read` warnings, because it asks non-mesh components for `staticMesh`) and `p10_6b_checks.py` (the swap readouts and `world_box`).
   - `import_p10.py` (the P10-4 imports).
   - Pose files: `Tools/belltower/poses/`.
10. **Moon beams through openings (D1.24).**
    - The courtyard moon travels along d = (0.6455, 0.4520, −0.6157) (`DirectionalLight` pitch −38, yaw 35). Only openings that face it get a beam: here the S and W faces and the SW roof collapse.
    - **Pattern:** a shadowed `SpotLight` 150–200 cm back along −d from the opening's inner centre, rotation (−38, 35, 0), with `bCastVolumetricShadow` and scattering 0.8.
    - **Shaft card:** an engine `Cylinder` with `MI_LightShaft_Crypt`, NoCollision and no shadow. It runs from the opening + 5·d, traced along d.
    - Implementation: `place_lighting_p10.py shafts`.
11. **Door leaves in pointed or gabled openings (D1.19).** Check both faces for light wedges at the leaf's top corners. `Door_Shortcut` needed leaf scale Z 1.30.
12. **Lighting a dark interior (D1.24).** If a wall 40 cm from a lantern glows saturated orange, the lantern is too strong. Fix it in lumens, not in exposure. Raise exposure only for the walk floors (`PP_Cloister` EV100 0.65).
13. **Carved text from Blender (P10-8d).** Authoring coordinates equal Unreal's numerically, but Unreal is left-handed, so the in-game picture is the mirror of Blender's native view.
    - Build text cutters pre-mirrored (`UE_VIEW = True` in `build_cloister.py`) and judge them in the mirrored review camera.
    - The in-game capture is the final proof. A 256 px `CaptureAssetImage` thumbnail is too small to read letters.
14. **Readable carved inscriptions (P10-8d, as in P9).**
    - Never put an inscription on a block-textured kit MI: the mortar grid and grain hide the letters.
    - Use a flat-tinted dressed-stone MI (`MI_Cl_TabletStone`, from `MI_Crypt_PlaqueSlate`) with dark groove faces (`MI_Cl_CarveDirt`, `BrightnessMul` 0.10).
    - `luma_report.py --plaque` is not a valid gate for dark-on-light carving; judge by eye.
15. **Moon spots at openings (P10-8d).**
    - Put the spot just inside the opening (opening + 10·d), not outside. An outside spot whose cone is wider than the slit paints a hot disc on the exterior stone that shows from far away.
    - Don't add a second shadowed moon source where the directional moon already enters; it gives double shadow sets.
16. **Shadowless lights outside a wall** light the whole interior through it (`Light_TowerExt_0..2`, removed in P10-8d). An exterior silhouette light needs shadows, or a radius that can't reach inside.
17. **`place_tower.py` leaves stale actors.** `--cats` / `--only` remove only the labels present in the layout, so an actor whose record was dropped from the layout stays in the level. Remove it explicitly (P10-8d: `CLA_LanternBracket_West`).

## Materials and surface work (Phase 11)
1. **Reimport can add collision.** A Content Browser Reimport gives an Interchange-imported mesh (`InterchangeAssetImportData`; the 29 cloister and tower meshes, which have no collision by design) a generated convex hull that fills arch and door openings. Kit meshes (`FbxStaticMeshImportData`, with UCX) don't have this problem.
   - Run `StaticMeshTools.remove_collisions` before saving, and check with `Tools/materials/check_reimport.py`.
   - Reimport also marks `L_Monastery` dirty, even though no actor changes.
2. **`ApproxSize` isn't a size.** The tag reads larger than the mesh and varies between builds (435x77x802 for a 400x60x800 wall). Use `StaticMeshTools.get_bounds`.
3. **`SelectAssets` doesn't work** for selecting in the Content Browser (no effect, or a timeout). The owner's search box takes `Name==A OR Name==B`.
4. **Compare captures at one size.** The viewport changes with the editor window and restarts (1331x808 and 1335x862 in this phase). `brightness_report_p11.py` fits the images first.
5. **Judge decals in PIE Simulate.** Editor-mode captures draw each decal's icon over its centre.
6. **Wall decals need roll 90:** rotation (0, yaw, 90) and DecalSize (depth, vertical half, horizontal half); forward (cos yaw, sin yaw) goes into the wall. Without the roll, the texture lies on its side and stretches into strands (D-087).
7. **Small decals lose thin lines in the mips.** Scale the decal instead of only raising its opacity.
8. **`M_LB_Decal` `OpacityTex` samples Alpha,** so the texture needs TC_Alpha, as `T_Leaking006_Opacity` has.
9. **Traces miss the crypt's art walls,** which have no collision. Take the plane from an existing decal on that wall (`"decal"` entries in `make_crack_placements.py`).
10. **A bright emissive needs a saturated hue.** The tonemapper desaturates bright colours, so a glowing pane needs a more saturated base hue than its light (D-088).
11. **Measure only the glowing pixels.** A wide luma window around lantern glass also measures the lit wall behind it and gives a false "over" (`lantern_report.py --half 3`).
12. **`BrightnessMul` moves the screen less than the sum suggests.** A linear ×1.15 was expected to add about 6.5 % to the display mean; it added 2 to 6 % (D-088).
13. **Git Bash rewrites `/Game/...` arguments** into `C:/Program Files/Git/Game/...`, which shows up as `DoesAssetExist` errors in the log. Keep these paths inside Python scripts.
14. **Stopping `capture_session.py` by force leaves the throttle off.** Set `bThrottleCPUWhenNotForeground` back to true on `/Script/UnrealEd.Default__EditorPerformanceSettings`, and stop PIE if it's running.
15. **Which areas have check scripts.** The crypt, cloister and tower do, but `Tools/crypt/place_lighting.py` has no `check` mode (use `place_crypt.py --cats light --check`). The chapel and courtyard have none, so compare them with a census (`census_p11.py`), which doesn't record light colour, scattering or cone angle.

## Skeletal meshes and the Warden (Phase 12)
1. **Import route (`SkeletalMeshTools.import_file`).** Works from a Blender FBX: unit scale 0.01, modelled in cm, armature object named `Armature`, `axis_forward='Y'`, `axis_up='Z'`, `add_leaf_bones=False`, `use_armature_deform_only=False`. Blender −Y becomes mesh +Y; +X stays +X. Settings: `Docs/plans/P12_WARDEN_VISUAL.md` P12-1.
2. **It can't import LODs,** and a direct re-import over an existing name is refused. A re-import is delete, import with `skeleton` set, then restore the physics asset, sockets, slot materials and every reference (`Tools/warden/reimport_skeletal.py`).
3. **Clips:** a clip-only FBX is refused ("produced no assets"). Import a clip with a mesh under a throwaway name, move `<name>_Anim`, delete the throwaway.
4. **`BlueprintTools.create` with an unsupported class opens a modal dialog that freezes the editor and every MCP call.** `/Script/Engine.AnimBlueprint` does this. Animation Blueprints, IK Rigs and Retargeters need an owner UI step.
5. **Inherited components:** set `CharacterMesh0` on the class default object, `BP_Warden.Default__BP_Warden_C:CharacterMesh0`. No `_GEN_VARIABLE` path exists for it. Blueprint-added components use `<BP>.<BP>_C:<Name>_GEN_VARIABLE`.
6. **`read_graph_dsl` leaves empty `_Event_N` orphans and marks the Blueprint dirty.** Use `find_nodes`, `get_node_infos` and `get_node_type_pins` to read. `write_graph_dsl` can't extend an existing event, so add a function and `create_node` + `connect_pins` a call.
7. **Stale instances in the session that edited a template.** Placed instances can show old values until the map reloads; don't save the map from that session. Verifying from disk: a separate headless editor over the mirror project (`check_warden.py --disk`).
8. **Materials on skeletal meshes:** assigning an MI whose parent lacks `bUsedWithSkeletalMesh` makes the editor set the flag and recompile the master. `M_LB_Surface` lacks it, so never use its MIs here.
9. **Metal in the dark:** a fully metallic mask has no diffuse, so one small candle shows almost nothing. Lowering metallic (`MetallicMul` 0.35) did what brightness alone couldn't.
10. **Copying between projects.** Assets from another UE project with the same engine build can be copied as files, with TheLastBell closed, at their original `/Game` paths, then moved in the editor, which fixes references (`Tools/warden/copy_v5_5.py`). Check first that the set is self-contained, and compare hashes.
11. **A physics asset with a dangling preview mesh** opens on a cube and offers to delete every body as unmatched: choose Cancel. Setting the Preview Mesh in that editor and saving fixes it. No tool can set it. That editor also rewrites `Config/DefaultEditor.ini`; restore the file.
12. **`AnimationSingleNode` on a template:** `animationMode` first, then `animationData` with `animToPlay`, `bSavedLooping`, `bSavedPlaying`, `savedPosition`, `savedPlayRate`.

13. **`find_actors` matches labels,** not object names. Find an actor such as `BP_WardenSilhouette_C_2` by its object path, and read its label first.
14. **`AssetTools.delete` can return True and still leave the asset:** `exists` stays True and it reads as dirty (P12 fix set 1). Check `exists` afterwards. Remove the files only with Unreal closed, after `get_referencers` is empty, with `git rm`; never save the half-deleted asset.
15. **`add_variable` can't make enum variables.** Use a byte and compare with literals (`ELBWardenState`: Chase 5, Attack 6), and record it: reordering the enum breaks those silently.
16. **`SetScalarParameterValue` on a dynamic material instance** shares its node type with the parameter-collection version. Add it with `create_node` and `declaring_class` `MaterialInstanceDynamic`.
17. **Static mesh import into a new name** avoids replacing a mesh that a Blueprint and a map still use. Swap the users, restart the editor, then delete the old one.
18. **Captures need Unreal in front, and only the owner can do that.** Give `capture_session.py` `--fg-wait 180`, so the owner can reply "go" and then click Unreal. Simulate shows hidden actors such as the moon gobos (D-074) as bright marks.
19. **`Tools/build_and_test.ps1` can hang after the tests end** (`Start-Process -Wait`): if `Saved/Logs/LBTests_All.log` ends with `TEST COMPLETE`, read the result from it and stop the script.


## Animation assets in headless Python (Phase 13)
Script: `Tools/warden/p13_retarget.py` (steps `rigs, rtg, batch, measure, blend, montage, animset, abp, verify`, each safe to rerun). All of it ran with the real editor closed.
1. **Route that works:** `UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<py> -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>`. It runs in 10 to 50 s and exits by itself after the script (`LogPythonScriptCommandlet: ... executed successfully`). `-ExecutePythonScript=` was not needed. A script can't take arguments, so the script reads an environment variable (`$env:P13_STEPS='rtg,batch'`). One probe that created unsaved temp assets crashed inside `python311.dll` during shutdown, after the script had finished; saves made before the last print are fine.
2. **Names in 5.8:** the IK Retargeter is an op stack (`add_default_ops()` gives Pelvis Motion, FK Chains, Run IK Rig, Root Motion, Remap Curves). The old `chain_settings` / `root_settings` properties are deprecated.
3. **IK Rig:** `create_asset(name, folder, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())`, then `c = unreal.IKRigController.get_controller(rig)`, `c.set_skeletal_mesh(mesh)`, `c.apply_auto_generated_retarget_definition()` (True for Mixamo and for the Unreal-mannequin names; it sets the retarget root and the spine, neck, head, clavicle, arm, finger and leg chains, with `LeftFootIK`, `RightFootIK`, `LeftHandIK` and `RightHandIK` goals but no solver). `get_retarget_chains()` returns `BoneChain` structs: `chain_name`, `ik_goal_name`; start and end bones come from `get_retarget_chain_start_bone(name)` / `..._end_bone`. Bones outside the template (the Warden's `chain_*` and `robe_*`) land in no chain.
4. **Retargeter:** `create_asset(name, folder, unreal.IKRetargeter, unreal.IKRetargetFactory())`, `c = unreal.IKRetargeterController.get_controller(rtg)`, `c.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE/TARGET, rig)`, `c.set_preview_mesh(...)`, `c.add_default_ops()`, `c.assign_ik_rig_to_all_ops(TARGET, rig)`, `c.auto_map_chains(unreal.AutoMapChainType.EXACT, True)`, `c.auto_align_all_bones(TARGET, unreal.RetargetAutoAlignMethod.CHAIN_TO_CHAIN)`. Read back with `get_source_chain(target_chain)`, `get_op_name(i)`, `get_retarget_op_enabled(i)`, `set_retarget_op_enabled(i, False)`, `get_rotation_offset_for_retarget_pose_bone(bone, TARGET)` (a Quat), `get_current_retarget_pose(TARGET).export_text()`.
5. **Retarget gotchas (P13-4):**
   - The auto-align also sets the target pelvis offset (it overwrites a yaw set before it) and aligns the target chains to the source's GLOBAL directions, so both skeletons must face the same way BEFORE the align. P13-4 skipped that (Y Bot +Y, Warden +X, a pelvis yaw and a -90 `root` key afterwards): the arms came out along the facing axis, shoulder-high, and the torso leaned. That workaround is withdrawn.
   - The Root Motion op copies the source's Hips onto the target `root` bone. Mixamo has no root above Hips, so `root` ended up carrying the body motion. The clips are in place: turn that op off.
   - **Facing fix (P13-4b): import the Y Bot rotated.** `Tools/warden/p13_reimport_ybot.py`: `FbxImportUI.skeletal_mesh_import_data.import_rotation = Rotator(0,0,-90)` for the mesh and `anim_sequence_import_data.import_rotation` the same for the clips, through `AssetImportTask(factory=FbxFactory)`. Check the facing from numbers: toe bone x minus foot bone x > 0, head x minus neck x > 0, LeftHand y < 0 (like the Warden's `hand_l`).
   - **Importing over an existing mesh name does not take the new rotation reliably and keeps the OLD skeleton asset (stale reference pose).** Delete the old mesh, physics asset and skeleton (and the clips and IK Rig that use them) first, then import fresh under the same names. `EAL.delete_asset` does remove saved files when nothing references them; the retargeter asset stayed (reported True, `exists` still True), so it is rebuilt in place.
   - **Anim-only import works from Python:** `import_mesh=False`, `mesh_type_to_import=FBXIT_ANIMATION`, `skeleton=<skeleton>`, one sequence named `<destination>_mixamo_com` (rename it with `EAL.rename_asset`); the empty `Take_001` sequence is created in memory only and is never saved if you don't save it.
6. **Batch retarget:** `inp = unreal.IKRetargetBatchOperationInputs()`; `assets_to_retarget` takes `AssetData` (`EditorAssetLibrary.find_asset_data(path)`), not loaded objects; set `source_mesh`, `target_mesh`, `ik_retarget_asset`, `search`/`replace` (`AN_YBot_` to `AN_Warden_`), `target_path`, `use_source_path=False`, `include_referenced_assets=False`, `overwrite_existing_files=True`; then `unreal.IKRetargetBatchOperation.run_batch_retarget(inp)`. "No animation curves found" warnings are harmless.
7. **`EditorAssetLibrary.delete_asset` returns True but the asset stays registered** in a commandlet (the same as MCP item 14 above), so `create_asset` then fails with "already exists". A rebuild loads the asset and resets it in place.
8. **Blend spaces:** `BlendSpace1D` shows NO Python properties. Use `unreal.ToolsetLibrary.get_object_properties(obj, [names])` / `set_object_properties(obj, json_string)` (the same calls as `ObjectTools`). Factory: `BlendSpaceFactory1D` with `set_editor_property('target_skeleton', skel)`. Keys: `blendParameters` (3 entries: `displayName`, `min`, `max`, `gridNum`, ...), `interpolationParam` (3 entries: `interpolationTime`, `dampingRatio`, `maxSpeed`, `interpolationType`, default `BSIT_SpringDamper`), `bLoop`, `sampleData` (`animation {refPath}`, `sampleValue {x,y,z}`, `rateScale` 0.01..64). Duplicate samples of one clip at two positions are accepted. `set_preview_skeletal_mesh(mesh)` works.
9. **Montages:** `AnimMontageFactory` with `target_skeleton` and `source_animation` makes one `DefaultSlot` segment. Set `blendIn` / `blendOut` (`{"blendTime": x}`) and `slotAnimTracks` through `set_object_properties`. To trim: `animEndTime` = the trim, but `cachedPlayLength` stays the LENGTH OF THE REFERENCED CLIP (setting it to the trim gives "segment out-of-sync" on load). The montage's `get_play_length()` / `sequence_length` still read the old value until the package is saved; after the save (and in a fresh process) it is the trimmed length.
10. **Data asset of a C++ class:** `f = unreal.DataAssetFactory(); f.set_editor_property('data_asset_class', unreal.LBWardenAnimSet)`, `create_asset(name, folder, unreal.LBWardenAnimSet, f)`, then `set_object_properties` with `{"attack": {"refPath": "/Game/X/AM_X.AM_X"}, "attackPlayRate": 1.1}`.
11. **Animation Blueprint without a dialog:** `f = unreal.AnimBlueprintFactory(); f.set_editor_property('parent_class', unreal.load_class(None, '/Script/LastBell.LBWardenAnimInstance')); f.set_editor_property('target_skeleton', skel)` (read back with `ToolsetLibrary.get_object_properties(f, ["ParentClass","TargetSkeleton"])`), `create_asset(name, folder, unreal.AnimBlueprint, f)`, `unreal.BlueprintEditorLibrary.compile_blueprint(abp)` (an empty graph compiles `BS_UP_TO_DATE` with no warnings), class default: `unreal.get_default_object(abp.generated_class()).set_editor_property('anim_set', da)`, compile again, save. Read back: `abp.get_blueprint_parent_class()`, `abp.get_editor_property('target_skeleton')`, `abp.get_animation_graphs()`. This is the BlueprintTools.create dialog problem (item 4 of the Phase 12 section) solved for Animation Blueprints.
12. **Measuring a clip:** `opts = unreal.AnimPoseEvaluationOptions()` (RAW, `should_retarget` False, root motion off), `pose = unreal.AnimPoseExtensions.get_anim_pose_at_frame(seq, i, opts)`, `unreal.AnimPoseExtensions.get_bone_pose(pose, 'foot_l', unreal.AnimPoseSpaces.WORLD)` (WORLD = component space). Frames: `unreal.AnimationLibrary.get_num_frames(seq)`; there are frames + 1 keys. `get_bone_pose_for_frame(seq, bone, frame, False)` gives the local track value. `AnimationLibrary.find_bone_path_to_root(seq, bone)` gives the parent chain.

## Animation Blueprint graph and physics asset through MCP (Phase 13, P13-6)
Scripts: `Tools/warden/p13_abp_graph.py` (steps `create props read save`; `P13_TARGET=spike` aims it at the spike), `p13_physics.py` (`before edit damping after save`), helpers in `p13_abp_lib.py`. The editor must be open.
1. **The AnimGraph can be built with `BlueprintTools`.** `list_graphs` / `get_graph(bp, "AnimGraph")` gives the graph; Output Pose is the `AnimGraphNode_Root_0` that `find_nodes(graph, "")` returns. `find_node_types` with a filter such as `Animation|` lists the anim node types.
2. **Type ids used:**
   - `Animation|BlendSpaces|BlendspacePlayer'BS_Warden_Locomotion'`: the typed form places the player with its blend space already set. The untyped `...|BlendspacePlayer` has no asset and fails the compile.
   - `Animation|Blends|TwoWayBlend`
   - `Animation|Montage|Slot'DefaultSlot'`
   - `Animation|ConvertSpaces|LocalToComponent` and `ComponentToLocal`
   - `Animation|SkeletalControls|Transform(Modify)Bone`
   - `Animation|SkeletalControls|TwoBoneIK`
   - `Animation|Dynamics|RigidBody`
   - Variable getters: `Variables|Warden|Get<Variable>`.
3. **Conversion nodes are not added automatically.** `connect_pins` does not insert Local to Component or Component to Local: place them yourself between the local-space and component-space nodes.
4. **Wiring:** `create_node(graph, type_id, pos)` returns the node; `connect_pins(output_pin, input_pin)` takes `{node, direction, index_id}`; pin indexes come from `get_node_type_pins`. A getter wired to a pin binds the variable (Alpha pins are on by default, `alphaInputType` Float).
5. **Node options:** `ObjectTools.set_properties(node, {"Node": {...}})` (`values` as a JSON string) and `get_properties(node, ["Node"])`. Names are camelCase struct fields: `boneToModify.boneName`, `translationMode` (`BMM_Additive`), `translationSpace` (`BCS_ComponentSpace`), `iKBone`, `effectorLocationSpace`, `effectorTarget.boneReference.boneName`, `jointTarget...`, `jointTargetLocationSpace`, `simulationSpace`, `lODThreshold`. Read each back.
6. **Compile result:** `compile_blueprint` returns None when clean and raises (`failed to compile. Compile Errors: [...]`) on an error; with `warnings_as_errors` true it also raises on warnings. A deliberately broken node proved it. An unconnected stray node is not compiled, so it proves nothing. The log lines are `LogBlueprint: Error: ... [Compiler] ...`.
7. **Two Bone IK joint target:** Parent Bone Space with location (0,0,0) puts the pole at the hip. Use Bone Space on the calf so the pole is the animated knee.
8. **Physics asset (`PhysicsToolsets.PhysicsAssetToolset`):**
   - `GetBodyNames`, `GetBodyShapes`, `GetBodyPhysicsMode`, `GetConstraints` read everything; `AddBody`, `SetCapsule`, `AddConstraint (child, parent)`, `RemoveConstraint`, `SetBodyPhysicsMode`, `SetConstraintLimits` edit it.
   - `SetCapsule`'s long axis is the capsule's local Z; the shapes here are all named "None".
   - A new body is empty until `SetCapsule`. To re-parent a chain body, `RemoveConstraint` then `AddConstraint`.
   - No tool for body or constraint damping, per-pair collision disabling, or constraint reference frames. Body damping is reachable through ObjectTools: the body setups are sub-objects `<PA>:SkeletalBodySetup_<N>` (find the bone by reading `boneName`), set `{"defaultInstance": {"linearDamping": x, "angularDamping": y}}`. Constraint templates are `<PA>:PhysicsConstraintTemplate_<N>`. The array properties on the asset itself can't be read.
   - Probing 120 setup names takes a few minutes, so do it once per script.
9. **Bone lengths for capsule sizing** (no MCP tool for bone transforms): a read-only headless script, `Tools/warden/p13_bone_probe.py`, ran with the editor open (`UnrealEditor-Cmd -run=pythonscript`, exit 0, saves nothing), using `AnimPoseExtensions.get_reference_pose(skeleton)` + `get_bone_pose(..., LOCAL)`.

## Blend spaces built by script need the editor once (Phase 13)
A blend space whose `sampleData` is set through properties or Python reads back fine, but has **no runtime data** (0 segments): only `UBlendSpace::ResampleData()` builds it, and that isn't reachable from Python. The Blend Space editor calls it when it opens. In game such a blend space returns nothing, so the graph outputs the reference pose while montages still play (P13: the Warden glided frozen).
- **Fix:** open the blend space in its editor and save. Then check with `LastBell.Functional.Warden.Anim.LocomotionMovesTheFeet`, or with `lb.Warden.AnimDebug 1`, which logs "runtime data: N segments".
- **Side effect:** opening that editor rewrites `Config/DefaultEditor.ini`'s preview-scene profiles. Restore it with `git checkout -- Config/DefaultEditor.ini`.

## Storm materials (Phase 14)
1. **`MaterialInstanceTools.set_parent` on an MI that is on screen crashes the editor.** Reparenting `MI_NightStormSky` (its child `MI_Env_NightSky` was drawing the level's sky) hit a render-thread assertion, "UniformExpressionCache should be up to date" (2026-11-07, P14-2a). The cause (read in `material_instance.py` of the EditorToolset plugin, 2026-11-07): `set_parent` calls `set_material_instance_parent` and only `_refresh_editor`, without `update_material_instance`, while `_set_parameter` (the scalar, vector, texture and static-switch setters) calls `update_material_instance` and, for a static switch, also flushes `recompile_material` on the base material. Never reparent an MI used by the open level or by a child MI the level uses. Do it with Unreal closed: `Tools/lighting/p14_2a_sky_reparent.py` (`-run=pythonscript`, `-nullrhi`) uses `MaterialEditingLibrary.set_material_instance_parent` + `update_material_instance`, reads every override back before and after, and saves only that one package.
2. **Package dirty state in headless Python:** `unreal.Package` has no `is_dirty()`. Use `unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()` and compare package names.
3. **Material graphs over MCP (P14-2a, `Tools/lighting/p14_lib.py`).**
   - `MaterialTools.add_expression` takes `/Script/Engine.MaterialExpression<Class>`; set the fields afterwards with `ObjectTools.set_properties` (`parameterName`, `collection`, `constB`, `constExponent`, `r/g/b/a` of a mask, `inputName`/`inputType`/`previewValue`/`bUsePreviewValueAsDefault` of a function input, `bExposeToLibrary` of the function).
   - A `MaterialFunctionCall`'s pins appear as soon as `set_properties {"materialFunction": {"refPath": ...}}` is applied: `input_names` then lists them, and `connect_expressions` can use the function's output name (`Mul`).
   - Pins with an empty name (Saturate, OneMinus, ComponentMask, FunctionOutput) are connected with `to_input_name = ""`. An unconnected Multiply or Add input keeps its `constA` / `constB`, so a constant can be set instead of a node.
   - `connect_to_output` replaces the old link, so an edit that wraps the final emissive is: add the new Multiply, wire the old last node into A, then `connect_to_output` the new one.
   - `get_properties` on an MI returns a JSON **string** (`json.loads` it). Names: `parent`, `scalarParameterValues`, `vectorParameterValues`, `textureParameterValues` (not `staticParametersRuntime`). `AssetTools.find_assets` returns package-path strings.
   - `MaterialInstanceTools.set_texture_parameter` takes the texture as `value`, like the scalar and vector setters. `set_scalar_parameter` creates an explicit override even when the value equals the parent's.
   - `ObjectTools.get_properties` on a Material can't read `shadingModels`; on a decal master the decal blend mode isn't readable either.
   - `MaterialTools.recompile` raises on a shader error and prints nothing otherwise; no tool gives instruction counts.
4. **Data asset of a C++ class (P14-2a).**
   - `DataAssetTools.create {folder_path, asset_name, asset_type: {refPath: "/Script/LastBell/..."}}`.
   - MCP has no tool that calls a UFUNCTION, so a CallInEditor function such as `ULBStormSettings::FillPlanTagDefaults` can't be run. Fill the arrays with `set_properties` instead: `FGameplayTag` is `{"tagName": "State.Ritual.1"}`, and enum arrays take their names (`["Double","Triple"]`). Read them back.
   - A config class default object is reachable as `/Script/LastBell.Default__LBGameSettings`: a `set_properties` of a soft pointer (`{"refPath": ...}`) works in memory.
5. **`Config/DefaultGame.ini` has CRLF line endings.** Edit it as bytes (`open(p, "rb")`, replace, `"wb"`), never with a text-mode write.
6. **Wind materials (P14-2b, `Tools/lighting/p14_2b_wind.py`).**
   - **Material function with a static bool:** a `FunctionInput` with `inputType` `FunctionInput_StaticBool` feeds the `Value` pin of a (non-parameter) `StaticSwitch`; the caller wires a `StaticBool` expression (`value`) into the call node's input. `MaterialExpressionPreSkinnedPosition` is the "Pre-Skinned Local Position" node.
   - **`TransformPosition`** takes `transformSourceType` / `transformType` as `TRANSFORMPOSSOURCE_Instance` and `TRANSFORMPOSSOURCE_World`. The `Sine` node's `period` defaults to 1 (it computes sin(2 pi x / period)), so set `period` to 2 pi for a plain sin(x).
   - **Static switches on an MI** are not in `scalarParameterValues` and the `mi_compact` helper does not show them: read them with `MaterialInstanceTools.get_static_switch_parameter {instance, name}` (it also reports an inherited default). Setting `bWind` on an MI took about 1.6 s per MI and left the level clean.
   - **Argument names differ by tool:** `AssetTools.exists {path}`, `is_dirty {asset_path}`, `get_referencers {asset_path}`, `MaterialTools.list_expression_classes {material_or_function, search}` (`search` is required, `""` lists all), `get_property_input {material, material_property}`.
   - **A scratch folder shared between sessions can shadow the standard library:** a stray `types.py` there broke `import urllib` for scripts that put the folder first on `sys.path`. Keep your scripts in a fresh subfolder.
7. **WPO disable distance (P14-3, `Tools/lighting/p14_wpo_distance.py`).** `--apply` sets `WorldPositionOffsetDisableDistance` 4000 on every `StaticMeshActor` whose effective material (override, else the mesh's default slot) is one of the nine foliage MIs (249 actors) and on every PCG ISM component (312); it scans first and stops if the counts differ. `--check` reads 4000 on every target. **Regenerating a `PCGV_*` volume (`ExecuteGraphInstance`) rebuilds its ISM components and resets the distance to 0: rerun `p14_wpo_distance.py --apply` afterwards.** A scan makes about 2500 read calls (10 to 15 minutes with the editor in the background).
8. **Level script `Tools/lighting/p14_3_level.py` (P14-3):** `--apply [--only tags,zones,pp,groups,decals,apparitions]` is idempotent (exact-label find or create), `--check` prints PASS/FAIL per item. It never saves.
9. **A large `find_actors` reply can reset the connection (P14-3).** The empty-name census (3000 refs) failed 3 times in about 12 runs with `ConnectionResetError` while the editor stayed alive and answered the next call. `p14_3_level.Ed.call` repeats a read-only call up to 3 times on a new session and never repeats a mutation.
10. **Placed-instance array write (P14-3).** `ObjectTools.set_properties {"stations": [...]}` on a placed `BP_WardenApparition` instance (a C++ struct array) persists and reads back identical except for the changed field; keep the whole array from `get_properties` and change one field. Property names on `ALBStateLightGroup` are camelCase (`lights`, `emissiveActors`, `glowActors`, `rules[].requiredTag.tagName`, `mode`); an enum reads back as its name.
11. **`MaterialExpressionTransform` and the unscaled `PreSkinnedPosition` (P14-4 wind fix, `Tools/lighting/p14_4_wind_fix.py`).**
   - `add_expression` class `Transform` (`/Script/Engine.MaterialExpressionTransform`). It defaults to `TRANSFORMSOURCE_Tangent` / `TRANSFORM_World`. `set_properties` with `transformSourceType` = `TRANSFORMSOURCE_Instance` and `transformType` = `TRANSFORM_World` worked and read back. This is the vector version (w = 0); `TransformPosition` (item 6) uses the `TRANSFORMPOSSOURCE_*` names.
   - The world Z scale of an instance is `Length(Transform(Instance -> World, (0, 0, 1)))`.
   - **`PreSkinnedPosition` is unscaled:** it is the mesh-local position, so for world heights multiply by the instance Z scale (the plants are placed 1 to 4.8x).
   - `connect_expressions` onto an already-linked input (the Divide's A) replaces the old link.
   - A function input's text is the property `description` (the 14-2b `desc=` argument did not set it).

## Lighting sessions (Phase 14)
1. **Candle proxy for captures.** `Tools/crypt/capture_session.py ... --light-offset F R U` (simulate mode only) passes `--light --light-offset F R U` to `capture_poses.py`, so a light follows the camera at camera + F forward + R right + U up. The P14-5 proxy used `--light-offset 36 14 -10`.
   - PIE must already be running, and `TMP_CaptureLight` must exist in the PIE world: run `Tools/lighting/pie_proxy.py` first. It retargets the PIE copy of `Light_Approach_0` with the values of `DA_PlayerTuning` (10 cd, radius 600, 1900 K, no shadows). The caller keeps PIE running; the light vanishes when PIE stops and nothing is saved.
2. **`Tools/lighting/pie_pp.py`** changes post-process values on the PIE-world copies only (it refuses a refPath without `UEDPIE`, reads every write back, and saves nothing):
   - `start` and `stop` (PIE Simulate), `read` (the PIE-world volumes' exposure and grade fields);
   - `ev [volume] EV` (min = max EV100; the volume defaults to `PP_Chapel`, and any area volume works: `PP_Outdoor_Night`, `PP_Crypt`, `PP_Cloister`, `PP_Chapel`, `PP_Tower`);
   - `grade A|B|C` on `PostProcess_Exposure` (B and C also clear the per-area shadow-saturation overrides, A puts them back). The originals are recorded in `Saved/p14_4_pie_pp_originals.json` on the first grade call: delete that file after StopPIE.
3. **Measuring a capture set.**
   - `Tools/lighting/area_targets.py <dir> <prefix> [--suffix S] [--chapel-target MEAN] [--json out.json]`: per pose the mean luma and the central-40 % mean; per area the mean over its **wide** poses against the mean target, and every pose against the floor.
   - `Tools/lighting/compare_sets.py <before_dir> <before_prefix> <after_dir> <after_prefix> [--sheet out.png] [--json out.json] [--limit 2.0] [--mask pose:x0,y0,x1,y1]`: the mean absolute difference per pose (in 8-bit units, PASS at 2 or less) and before/after sheets.
4. **Live tuning in PIE works.** `MaterialInstanceTools.set_scalar_parameter` and field writes on `DA_StormSettings` over MCP take effect immediately, with no crash (P14-4: the wind values, `DebugFreezeFlash` 0 and 0.8 for captures). They leave the assets dirty in memory: save them deliberately (one package per call) or choose Don't Save on close, and put the debug fields back to −1 first. This does not change item 1 of "Storm materials": still never `set_parent` an MI that is on screen.
5. **`lb.Warden.Enabled` is a global CVar.** It persists across PIE sessions until it is changed (P14-B: after the owner's closing `lb.Warden.Enabled 0`, the Warden stayed disabled until `lb.Warden.Enabled 1` or an editor restart).
6. **Owner console commands during Simulate go to the PIE world.** A script can wait for a marker such as `Cmd: lb.State.Dump` in `Saved/Logs/TheLastBell.log` before it captures (P14-5b: the owner typed `lb.State.Add <tag>`, then `lb.State.Dump`).
7. **Performance readings must be taken at a matched story state.** The game thread depends on it (P14-7): at the start state it is about 11 ms at every spot, at the late indoor states about 8 ms, with the storm off as well. Compare readings only at the same objective on screen, settle 30 s or more, and start each with `lb.Warden.Enabled 0`. An unsettled scene reads wrong (the void P14-B courtyard reading: 66.4K prims, game thread 25.06 ms).

## FX materials over MCP (Phase 15, P15-4)
1. **`MaterialTools.recompile` does report graph errors**, not only shader errors. A deliberately wrong `samplerType` (Normal on an sRGB-off texture) raised `Material failed to compile: (Node TextureSampleParameter2D) Sampler type is Normal, should be Linear Color for ...`; a clean graph returns None. Set `samplerType` explicitly with the texture: sRGB-off TC_Default = `SAMPLERTYPE_LinearColor`, sRGB on = `SAMPLERTYPE_Color`, TC_Masks = `SAMPLERTYPE_Masks`, TC_Alpha (G8) = `SAMPLERTYPE_Alpha`, TC_Normalmap = `SAMPLERTYPE_Normal`. Still no instruction counts over MCP.
2. **Pin names:** `ParticleColor` outputs `RGB R G B A RGBA`; `DepthFade` inputs `Opacity`, `FadeDistance`; `TextureSampleParameterSubUV` (parameter version of the SubUV node, property `bBlend`) takes `UVs`; `ObjectLocalBounds` outputs `Half Extents`, `Extents` (full), `Min`, `Max` (local space); `ObjectBounds` has one unnamed output (world full size); `LocalPosition` outputs `XYZ XY Z`; `PixelDepth` has one output. Unary nodes (Saturate, Floor, Frac, ComponentMask, Sine) take `to_input_name = ""`. The linear interpolate class is `LinearInterpolate`, the dot product is `DotProduct`.
3. **A static switch used in several places:** one `StaticBoolParameter` (`value`, outputs the bool) feeding the `Value` pin of several plain `StaticSwitch` nodes; never several `StaticSwitchParameter` nodes with the same name. On an MI, `set_static_switch_parameter` and `get_static_switch_parameter` accept that name.
4. **MI previews:** `CaptureAssetImage` of an MI of a translucent or additive master draws a plane; after any master recompile the placeholder (a bare checker, 48518 bytes for a 256 px plane) lasts 30 to 90 s, so wait and retry. A material function can't be captured ("Asset type does not support image capture"). An additive material that multiplies a storm value of 0 shows only the checker, which is correct but looks like a placeholder: judge it with the factor forced to 1 for one capture, then rebuild.
5. **New packages are autosaved into `Saved/Autosaves`** while you work (the log shows `Generating thumbnails ... Autosaves`); that is not a save of the content file. `git status` shows the new `.uasset` only after `save_assets` (one package per call; 29 packages took 0.2 s each in P15-4).
