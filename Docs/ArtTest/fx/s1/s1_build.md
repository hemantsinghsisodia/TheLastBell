# P15 S1: build record (rain occlusion spike) and the MCP recipe for P15-5

Built 2026-11-08 by `Tools/fx/s1_spike.py build` and `place` (editor open on `L_Monastery`, PIE off, nothing captured, nothing saved). Spec: `Docs/plans/P15_S1_RAIN_SPIKE.md` section 2. This file is the method record: every call that worked has its exact tool and payload shape, every failure has its error text. **Not yet tested at run time:** whether rain is stopped by roofs, whether the latch behaves, whether the second renderer draws. That needs the section 3 capture session (human, Unreal in front).

## 1. Answers to the build questions

| Q | Answer |
|---|---|
| **Q3** Can MCP set the Collision module to distance-field mode? | **Yes, by section 2.3 step 1.** The mode is the static switch **`GPU Collision Type`** (enum `/Niagara/Enums/ENiagara_GPUCollisionType`) on the **placed** module. It is not in `GetModuleSchemaFromAsset` (F0.12 was right that the asset schema hides it); it appears in `GetModuleTopology` of the placed module with `bIsStaticSwitch: true`. `SetStackInputData` with an `Enum` value sets it, and `GetStackInputData` reads back `GPU Distance Fields`. Steps 2 to 4 were not needed (see section 4). |
| **Q4** Latch built? | **Yes, built and compiled** (CPU scripts and GPU compute script, both emitters). Attribute read: **`Particles.HasCollided`** (an output of `Collision`) is read inside the HLSL expression `Particles.Landed || Particles.HasCollided` of a SetParameters module that runs after `Collision`. The latch attribute is `Particles.Landed` (bool, set false at spawn). Whether `HasCollided` is still true on a frame after the hit, and whether 20000 cm/s tunnels, is a run-time question for the captures. |
| **Q5** Second sprite renderer with custom facing and its own size attribute? | **Yes, built and read back.** `AddRenderer` (sprite) gave renderer index 1; `SetRendererData` set `FacingMode` `CustomFacingVector`, `SpriteFacingBinding` `Particles.SpriteFacing` (explicit) and `SpriteSizeBinding` `Particles.RingSize` (explicit). Both bindings read back `bBindingExistsOnSource: true`. Drawing is untested. |

## 2. What was built

- **Material:** `DefaultSpriteMaterial` is `BLEND_Additive` (not Translucent), so spec 2.1 step 3 applied: created **`/Game/LastBell/FX/Spike/M_LB_Spike_Unlit`** (Translucent, Unlit, two-sided, `bUsedWithNiagaraSprites` true). Emissive = `ParticleColor.RGB` x `RadialGradientExponential`; Opacity = `ParticleColor.A` x the same gradient (4 nodes: ParticleColor, MaterialFunctionCall, 2 Multiply). `MaterialTools.recompile` raised nothing.
- **System:** `/Game/LastBell/FX/Spike/NS_LB_Rain_Spike` from `/Niagara/DefaultAssets/DefaultSystem`, `Fountain` removed, 7 user variables (section 2.2 table).
- **Template emitter used for both `Rain` and `Splash`:** `/Niagara/DefaultAssets/Templates/Emitters/Fountain` (has SpawnRate, ShapeLocation, AddVelocity; I removed GravityForce, Drag, ScaleColor). Probed alternatives: `Minimal` and `SingleLoopingParticle`/`SimpleSpriteBurst`/`RecycleParticlesInView` have no SpawnRate (they use bursts or nothing); `HangingParticulates` and `BlowingParticles` have SpawnRate but more modules to strip.
- **Collision radius:** `Radius Calculation Type` = `Custom` (`ENiagaraCollisionRadiusOptions::NewEnumerator3`), which reveals the input **`Particle Radius`** (cm). Rain: linked to `User.RainRadius` (10). Splash: literal 6. No sprite-size x scale mapping was needed.
- **Compile state (final):** `GetSystemCompileState` aggregate `UpToDate`, no errors, no warnings, not stale; all 8 scripts `UpToDate`, including `ParticleGPUComputeScript` of both emitters. `GetStackIssues`: **0 errors, 0 warnings, 4 infos** (version-upgrade notes for ShapeLocation and ParticleState). Two problems on the way, both fixed: an Error "module has unmet dependencies, post-dependency SolveForcesAndVelocity" (section 3, item 14) and a Warning "Materials might not render correctly ... usage flags" (the material lacked `bUsedWithNiagaraSprites`).
- **Actors (editor world, folder `FX/Spike`, rotation 0, scale 1):** `S1_Spike_CyN` (2500, 1150, 0), `S1_Spike_CyS` (4500, -1150, 0), `S1_Spike_Chapel` (7000, 0, 0), `S1_Spike_Cloister` (10900, 1800, 0), `S1_Spike_Tower` (12500, 2000, 2500). Object names are `NiagaraActor_0, _2, _3, _4, _5` (`_1` is the existing `FX_FirePit_Smoke`). The component is `<actor>.NiagaraComponent0`. Variables read back equal the section 2.4 table (see the `check` output, section 6).
- **Scripts tested:** `build` twice (idempotent: second run changed nothing structural), and once from scratch on a throwaway copy (`S1_TEST_SUFFIX=_T1`, a test-only env var; the copy was deleted: `AssetTools.delete` returned True and `exists` is False for both). `place` twice (second run: 5 found). `set --world editor` with `--off`, with scales 0.5 and 2, fall 3000, radius 12, then restored to the section 2.4 values (read back); `set --world pie` with PIE off: `REFUSED ... (nothing was changed)`, exit 2. `blockers` with no flag refuses (exit 2); `blockers --dry-run` prints the 7 planned cubes; `remove --dry-run` lists 5 actors and 2 assets; `remove` without `--yes` refuses (exit 2). `blockers --apply` and `remove --yes` were never run. `s1_diff.py` was tested on two PNGs from `Docs/ArtTest/lighting/after/` in a scratch directory; its outputs were deleted.

## 3. MCP recipe (exact tool, arguments, payload shapes)

Calls are `UE().call(toolset, tool, args)` from `Tools/mcp/ue.py`. Toolsets: `NS` = `NiagaraToolsets.NiagaraToolset_System`, `NC` = `NiagaraToolsets.NiagaraToolset_Component`, `NI` = `NiagaraToolsets.NiagaraToolset_Info`. `R(...)` below is the stack reference
`{"system": {"refPath": SYS}, "emitterName": "", "scriptName": "", "moduleName": "", "rendererIndex": -1, "inputNameStack": []}`; every field is required by the schema (use `""`, `-1`, `[]` for the ones you don't need). `SYS` = `/Game/LastBell/FX/Spike/NS_LB_Rain_Spike.NS_LB_Rain_Spike`. Script names: `EmitterUpdateScript`, `ParticleSpawnScript`, `ParticleUpdateScript` (the compile report names them `ENiagaraScriptUsage::...`).

1. **Create the system.** `NS.CreateNiagaraSystem {assetName, assetPath: "/Game/LastBell/FX/Spike", templateSystem: {refPath: "/Niagara/DefaultAssets/DefaultSystem.DefaultSystem"}}` returns the refPath. Then `NS.RemoveEmitter {emitterToRemove: R(emitterName="Fountain")}` (returns null).
2. **Add an emitter.** `NS.AddEmitter {system: {refPath}, templateEmitter: {refPath: "/Niagara/DefaultAssets/Templates/Emitters/Fountain.Fountain"}, emitterName: "Rain"}` returns the topology (modules and inputs; the `simTarget` is `CPUSim` until you change it).
3. **Emitter properties.** `NS.SetEmitterData {emitter: R(emitterName), emitterData: {propertyValues: json.dumps({"SimTarget": "GPUComputeSim", "bLocalSpace": false, "bDeterminism": false, "CalculateBoundsMode": "Fixed", "FixedBounds": {"min": {"x":-1500,"y":-1500,"z":-3000}, "max": {"x":1500,"y":1500,"z":5500}, "isValid": true}})}}`. Keys are PascalCase; a partial blob is fine; `NS.GetEmitterData {emitterRef}` returns the blob in `propertyValues` (a JSON string) for the read-back.
4. **User variables.** `NS.AddUserVariables {system, variablesToAdd: [{name: "User.RainRate", type: {classStructOrEnum: {refPath: "/Script/Niagara.NiagaraFloat"}}, defaultValue: {struct: {refPath: "/Script/Niagara.NiagaraFloat"}, value: {value: 1000}}}, ...]}`. **Vector3: type AND value struct must both be `/Script/CoreUObject.Vector3f`** with `value: {x, y, z}`. Using the value struct `/Script/CoreUObject.Vector` (which the schema's list names) was accepted silently and stored (0, 0, 0). Read back with `NS.GetUserVariables {system}`.
5. **Set a module input** (`NS.SetStackInputData {stackInputRef: R(emitterName, scriptName, moduleName, -1, [inputName]), inputData}`; it returns the stored value, `GetStackInputData` reads it). `inputData` shapes, all `{struct: {refPath: S}, value: V}`:
   - float: `S=/Script/Niagara.NiagaraFloat`, `V={value: 5}`. bool: `S=/Script/Niagara.NiagaraBool`, `V={value: -1}` for true and `0` for false. int: `NiagaraInt32`.
   - Vector2: `S=/Script/CoreUObject.Vector2f`, `V={x, y}`. Vector3: `Vector3f`. Colour: `/Script/CoreUObject.LinearColor`, `V={r, g, b, a}`.
   - Linked: `S=/Script/NiagaraEditor.NiagaraExt_StackInputData_Linked`, `V={linkedVariable: {name: "User.BoxSize", type: {classStructOrEnum: {refPath: "/Script/CoreUObject.Vector3f"}}}}`.
   - HLSL: `S=/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression`, `V={hlslExpression: "float3(0, 0, -User.RainFall)"}`. `User.X` names work directly in the expression.
   - Enum: `S=/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum`, `V={enum: {refPath: <enum asset>}, enumName: "ENiagara_LifetimeMode::NewEnumerator0", displayName: "Direct Set"}`. **`enumName` is `<EnumName>::NewEnumeratorN` (qualified, with the internal name).** Look the values up with `NI.UEnum_Info {enum: {refPath}}`: it returns a JSON string `{Name, Values: [{Name, Value, DisplayName}]}`. The enum asset path for an input comes from the topology's `type.classStructOrEnum.refPath` (it can sit in a subfolder, for example `/Niagara/Enums/Location/ENiagara_LocationShapes.ENiagara_LocationShapes`, `/Niagara/Enums/Transforms/ENiagara_OffsetMode...`, `/Niagara/Enums/Utility/ENiagara_VelocityMode...`).
   - Setting a static switch can reveal other inputs (`Lifetime Mode` Direct Set reveals `Lifetime`; `Sprite Size Mode` Non-Uniform reveals `Sprite Size`; `Velocity Mode` Linear reveals `Velocity`; `Shape Primitive` Box / Plane reveals `Box Size`; `Offset Mode` Default reveals `Offset`; `Radius Calculation Type` Custom reveals `Particle Radius`). Set the switch first, then the input.
6. **Module inputs actually used (names are exact).**

   | Where | Input | Value (Rain / Splash) |
   |---|---|---|
   | `EmitterUpdateScript` / `SpawnRate` | `SpawnRate` | Linked `User.RainRate` / `User.SplashRate` |
   | `ParticleSpawnScript` / `InitializeParticle` | `Lifetime Mode`, `Lifetime` | Direct Set (`NewEnumerator0`), 5 / 4 |
   | | `Sprite Size Mode`, `Sprite Size` | Non-Uniform (`ENiagara_SizeScaleMode::NewEnumerator4`), Vector2f (2.5, 50) / (12, 12) |
   | | `Color` | LinearColor (2.5, 2.8, 3.2, 1) (Color Mode was already Direct Set) |
   | `ParticleSpawnScript` / `ShapeLocation` | `Shape Primitive` | Box / Plane (`ENiagara_LocationShapes::NewEnumerator2`); `Box / Plane Mode` was already Box |
   | | `Box Size`, `Offset Mode`, `Offset` | Linked `User.BoxSize` (Vector3f); Default (`NewEnumerator0`); Linked `User.SpawnOffset` |
   | `ParticleSpawnScript` / `AddVelocity` | `Velocity Mode`, `Velocity` | Linear (`ENiagara_VelocityMode::NewEnumerator0`); HLSL `float3(0, 0, -User.RainFall)` / `-User.SplashFall` |
   | `ParticleUpdateScript` / `Collision` | `GPU Collision Type` | GPU Distance Fields (`ENiagara_GPUCollisionType::NewEnumerator2`; the others: `NewEnumerator1` GPU Depth Buffer, `3` Analytical Planes, `4` GPU Ray Traces) |
   | | `Collision Enabled` | true |
   | | `KillOnCollision` | true / false (a NiagaraBool; the asset schema calls it `Kill On Collision`, NiagaraInt32; on the placed module use `KillOnCollision` with a bool) |
   | | `Radius Calculation Type`, `Particle Radius` | Custom (`ENiagaraCollisionRadiusOptions::NewEnumerator3`); Linked `User.RainRadius` / float 6 |
   | | Splash only: `Restitution`, `Friction`, `Enable Rest State` | 0, 1, true |

7. **Remove a module.** `NS.RemoveModule {moduleToRemove: R(emitterName, "ParticleUpdateScript", "GravityForce")}` (also `Drag`, `ScaleColor`); returns null.
8. **Add a module.** `NS.AddModule {moduleLocationRef: R(emitterName, "ParticleUpdateScript"), moduleAsset: {refPath: "/Niagara/Modules/Collision/Collision.Collision"}}` returns the placed module's topology (64 inputs for Collision). **It appends at the END of the stack.** `NS.GetScriptStackTopology {scriptRef: R(emitterName, "ParticleUpdateScript")}` lists `modules` in execution order.
9. **Order fix.** After step 8, `NS.GetStackIssues {system}` has an **Error** "The module has unmet dependencies. The following post-dependency is not met: SolveForcesAndVelocity" (Collision must run before it) with a fix `{fixId, style: "Fix", description: "Move module Collision Before SolveForcesAndVelocity"}`. `NS.ApplyStackIssueFix {system, issueId, fixId}` applies it, **but the call itself can raise** (`Cannot collect stack issues while a compile is in flight` or `No stack issue with IssueId '...' was found`, because the issue ids change after the recompile). Treat the raise as non-fatal and verify with the topology: it read `['ParticleState', 'Collision', 'SolveForcesAndVelocity']` afterwards, in both emitters, in the script run and in the interactive run.
10. **SetParameters module (the latch).** `NS.AddSetParametersModule {moduleLocationRef: R(emitterName, "ParticleSpawnScript"), parameters: [{variable: {name: "Particles.Landed", type: {classStructOrEnum: {refPath: "/Script/Niagara.NiagaraBool"}}}, defaultValue: {struct, value}}, ...]}` returns the module topology; the engine names it **`SetVariables_<GUID>`** (new GUID each time; find it again by its input names, `bIsSetParametersModule` true in the topology). Types used: `NiagaraBool`, `Vector2f`, `Vector3f`, `LinearColor`. The `defaultValue` can only be a literal. To give an entry an expression, **call `SetStackInputData` afterwards** with `stackInputRef: R(emitterName, script, "SetVariables_<GUID>", -1, ["Particles.Landed"])` and the HLSL payload (step 5). It appends at the end of the stack.
    - The latch uses **two** modules in `ParticleUpdateScript`: `Particles.Landed` = `Particles.Landed || Particles.HasCollided`, then `Particles.Color` = `Particles.Landed ? float4(5.0, 1.4, 0.2, 1.0) : float4(0.0, 0.0, 0.0, 0.0)`. One module with two entries would have the Color expression read last frame's `Landed`. Final order: `ParticleState, Collision, SolveForcesAndVelocity, SetVariables_<Landed>, SetVariables_<Color>`; nothing after the Color module.
11. **Renderer 0.** `NS.SetRendererData {renderer: R(emitterName, rendererIndex=0), rendererData: {propertyValues: json.dumps({"Material": {"refPath": MAT}, "Alignment": "VelocityAligned", "FacingMode": "FaceCamera"})}}`. Keys are PascalCase in the blob; `Alignment`: `Unaligned | VelocityAligned | CustomAlignment | Automatic`; `FacingMode`: `FaceCamera | FaceCameraPlane | CustomFacingVector | FaceCameraPosition | FaceCameraDistanceBlend | Automatic`. Read back with `NS.GetRendererData {rendererRef}` (blob in `propertyValues`). Note `GetRendererSchema` returns lowerCamelCase names, `GetRendererData` / `SetRendererData` use PascalCase.
12. **Second renderer + attribute bindings.** `NS.AddRenderer {newRendererLocation: R(emitterName), rendererClass: {refPath: "/Script/Niagara.NiagaraSpriteRendererProperties"}}` returns `{rendererIndex: 1, rendererClass}`. Then `SetRendererData` for index 1 with `FacingMode` `CustomFacingVector`, `Alignment` `Unaligned`, `Material`, and the two bindings. **Binding payload:** read the renderer first (`GetRendererData`), deep-copy the default `SpriteSizeBinding` and change only `rootName: "RingSize"`, `dataSetName: "RingSize"`, `cachedDisplayName: "Particles.RingSize"`, `paramMapVariable.name: "Particles.RingSize"`, `bindingSourceMode: "ExplicitParticles"` (keep its `typeDefHandle.registeredTypeIndex`: 103 is Vector2f, 104 Vector3f). `SpriteFacingBinding` already defaults to `Particles.SpriteFacing` (`ImplicitFromSource`); set `bindingSourceMode: "ExplicitParticles"` to make it explicit. `bBindingExistsOnSource` reads false right after the write and true after the next compile or refresh: re-read before you judge it.
13. **Compile and issues.** `NS.GetSystemCompileState {system}` waits for a compile in flight and returns `aggregateStatus`, `bHasErrors`, `bIsStale`, and one entry per script (`ParticleSpawnScriptInterpolated`, `ParticleUpdateScript`, `ParticleGPUComputeScript` per GPU emitter). `NS.GetStackIssues {system}` returns `numErrors/numWarnings/numInfos` and the issues. **Either can raise `Cannot collect stack issues while a compile is in flight` right after an edit**; the script (class `Ed`) sleeps 1.5 s and repeats it up to 40 times. A `bIsStale` true flag cleared by itself within seconds.
14. **Place and set per instance.** `SceneTools.add_to_scene_from_asset {asset_path: "/Game/LastBell/FX/Spike/NS_LB_Rain_Spike", name: label, xform}` returns `{refPath: ...NiagaraActor_N}` (the `name` argument becomes the label, the object name is `NiagaraActor_N`; the script still calls `ActorTools.set_label {actor, label}`, `SceneTools.set_actor_folder {actor, folder_path: "FX/Spike"}`, `ActorTools.set_actor_transform {actor, xform, worldspace: true}`). The Niagara component is `<actor refPath>.NiagaraComponent0` (also from `ActorTools.get_components`). `NC.SetVariable {component, variable: {name: "User.RainRate", type: {classStructOrEnum: {refPath}}, value: {struct: {refPath}, value: V}}}` and `NC.GetVariable {component, var: {name, type}}` (returns `{value: {struct, value}, name, type}`) both take the `User.` prefix; **`NC.GetUserVariables` returns the names without it** (`RainRate`).
15. **Material (section 2.1).** `MaterialTools.create_material {folder_path, asset_name}`; then `ObjectTools.set_properties {instance, values: json.dumps({"blendMode": "BLEND_Translucent"})}` and the same for `twoSided` true, `shadingModel` `MSM_Unlit` (reads back; `shadingModels` is unreadable) and `bUsedWithNiagaraSprites` true (without it the sprite renderer raises the warning above). Graph: `add_expression` for `MaterialExpressionParticleColor`, `MaterialExpressionMaterialFunctionCall` (set `materialFunction` to `/Engine/Functions/Engine_MaterialFunctions01/Gradient/RadialGradientExponential.RadialGradientExponential`: inputs `UVs, CenterPosition, Radius, Density, Invert Density`, defaults are fine), two `MaterialExpressionMultiply`; `connect_expressions` (`ParticleColor` output `RGB` into Multiply A, output `A` into the second Multiply A, the function into both B), `connect_to_output` `MP_EmissiveColor` and `MP_Opacity`, `recompile`.
16. **Reading modules.** `NS.GetModuleTopology {moduleRef}` lists inputs with `bIsStaticSwitch`, `bIsVisible`, `bIsEditable`, `bIsDynamic`; `NS.GetModuleInputValues {moduleRef}` gives all values (large for ShapeLocation: filter by name in the script). `NS.GetEmitterTopology` shows renderer classes de-duplicated (two sprite renderers list as one class): count renderers with `GetRendererData` per index instead.
17. **Toolbox traps.** Git Bash rewrites `/Niagara/...` and `/Game/...` arguments on the command line (set `MSYS_NO_PATHCONV=1` or keep the paths inside Python). `ue.py describe` once raised `ConnectionResetError`; a second call worked (read-only calls are safe to repeat). `GetStackIssues` after an edit sometimes needs a `GetSystemCompileState` first, and then still a retry.

## 4. Q3 attempts, in the order of section 2.3

1. **Placed module's own inputs: SUCCESS.** `AddModule(Collision)` returned 64 inputs; `GetModuleTopology` on the placed module lists the static switches `GPU Collision Type` (enum `ENiagara_GPUCollisionType`: `NewEnumerator1` GPU Depth Buffer, `NewEnumerator2` GPU Distance Fields, `NewEnumerator3` Analytical Planes, `NewEnumerator4` GPU Ray Traces (Experimental)), `Z Depth Query Type`, `Radius Calculation Type`, `Method for Calculating Particle Radius`. `UEnum_Info` on the enum path gave the values; `SetStackInputData` with the Enum payload returned `GPU Distance Fields`; `GetStackInputData` read it back (both emitters). Default was GPU Depth Buffer (`NewEnumerator1`).
2. **Zero-input module `NiagaraDistanceFieldCollisions`: tried on a throwaway GPU `Probe` emitter (since removed).** `AddModule` accepted it (0 inputs, 0 outputs; `GetModuleSchema` returns `inputs: [], outputs: []`); it was appended after `SolveForcesAndVelocity`. I did not learn what it does: while it existed, `GetStackIssues` kept answering "compile in flight" for more than 30 s, so I have no issue list for it. After `RemoveEmitter Probe` the system compiled normally again. It is not needed, since step 1 works.
3. **Existing distance-field emitters: not needed, searched anyway.** `AssetTools.find_assets` for Collision, Rain, Splash and Spark under `/Niagara`, `/Engine` and `/Game/LastBell/ThirdParty` found 35 assets: only Niagara modules, functions, enums and structs (`/Niagara/Modules/Collision/*`: `AlignParticlesWithCollisionPlane`, `AnalyticalCollisionQuery`, `Collision`, `CollisionLinearImpulse`, `CollisionQuery`, `CollisionQueryAndResponse`, `CollisionRest`, `DebugCollisionEvents`, `NiagaraDistanceFieldCollisions`, `PBD_IntraParticleCollision`) and engine texture/material noise. No `NiagaraEmitter` or `NiagaraSystem` asset matched.
4. **Not reached** ("distance-field mode not reachable over MCP" does not apply).

## 5. Latch, second renderer and binding (what exists)

- Splash `ParticleSpawnScript`: `SetVariables_21E3B4794C67212C2EB0C890A8C5B292` sets `Particles.Landed` false, `Particles.RingSize` (30, 30), `Particles.SpriteFacing` (0, 0, 1). The GUIDs are specific to this session's asset; look the names up again.
- Splash `ParticleUpdateScript`: `Collision`, `SolveForcesAndVelocity`, then `SetVariables_70CAB2DE...` (`Particles.Landed`) and `SetVariables_CCDCCEBA...` (`Particles.Color`). Nothing else writes `Particles.Color`.
- Renderer 0 (Splash): sprite, `Unaligned`, `FaceCamera`, `M_LB_Spike_Unlit`. Renderer 1: sprite, `Unaligned`, `CustomFacingVector`, facing binding `Particles.SpriteFacing`, size binding `Particles.RingSize` (both `ExplicitParticles`), same material. Rain renderer 0: `VelocityAligned`, `FaceCamera`.
- Risks to read in the captures: a pre-landing splash is invisible only because its colour is (0, 0, 0, 0) and the material is Translucent with Opacity = colour alpha. The initial colour (2.5, 2.8, 3.2, 1) is overwritten in the first Update pass, so no frame should show it; renderer 1 shows the 30 cm ring at the landing point at full size from the first landed frame (no size animation in the spike).

## 6. Map and save state

- **Nothing was saved.** `AssetTools.is_dirty` is True for `/Game/LastBell/Maps/L_Monastery` (the spike actors dirtied it, as expected), `/Game/LastBell/FX/Spike/M_LB_Spike_Unlit` and `/Game/LastBell/FX/Spike/NS_LB_Rain_Spike` (neither has ever been saved). `git status` shows no changed `.uasset` or `.umap`.
- If Unreal closes before the spike is removed, choose **Don't Save**.
- Every actor is at its section 2.4 values (the last `set --world editor` was the restore).

## 7. `check` output (final run, exit 0)

```
== s1_spike check ==
PASS material exists 
PASS material Translucent BLEND_Translucent
PASS material two-sided 
PASS material Unlit MSM_Unlit
PASS material usage flag bUsedWithNiagaraSprites 
PASS material MP_EmissiveColor wired MaterialExpressionMultiply_0
PASS material MP_Opacity wired MaterialExpressionMultiply_1
PASS system exists 
PASS emitters Rain and Splash only ['Rain', 'Splash']
PASS user var User.RainRate 1000
PASS user var User.SplashRate 200
PASS user var User.BoxSize (1400, 1100, 10)
PASS user var User.SpawnOffset (0, 0, 1000)
PASS user var User.RainFall 1250
PASS user var User.SplashFall 20000
PASS user var User.RainRadius 10
-- emitter Rain
PASS Rain SimTarget GPUComputeSim GPUComputeSim
PASS Rain local space off 
PASS Rain determinism off 
PASS Rain fixed bounds 
PASS Rain spawn rate linked to User.RainRate
PASS Rain lifetime {'value': 5}
PASS Rain sprite size {'x': 2.5, 'y': 50}
PASS Rain colour {'r': 2.5, 'g': 2.799999952316284, 'b': 3.200000047683716, 'a': 1}
PASS Rain shape Box / Plane Box / Plane
PASS Rain box size linked to User.BoxSize
PASS Rain offset linked to User.SpawnOffset
PASS Rain velocity HLSL {'hlslExpression': 'float3(0, 0, -User.RainFall)'}
PASS Rain no gravity/drag/scale-colour ['ParticleState', 'Collision', 'SolveForcesAndVelocity']
PASS Rain Collision before SolveForcesAndVelocity ['ParticleState', 'Collision', 'SolveForcesAndVelocity']
PASS Rain collision mode = GPU Distance Fields (Q3) GPU Distance Fields
PASS Rain collision enabled {'value': -1}
PASS Rain kill on collision = True {'value': -1}
PASS Rain radius type Custom Custom
PASS Rain particle radius linked to User.RainRadius
PASS Rain renderer 0 VelocityAligned FaceCamera
-- emitter Splash
PASS Splash SimTarget GPUComputeSim GPUComputeSim
PASS Splash local space off 
PASS Splash determinism off 
PASS Splash fixed bounds 
PASS Splash spawn rate linked to User.SplashRate
PASS Splash lifetime {'value': 4}
PASS Splash sprite size {'x': 12, 'y': 12}
PASS Splash colour {'r': 2.5, 'g': 2.799999952316284, 'b': 3.200000047683716, 'a': 1}
PASS Splash shape Box / Plane Box / Plane
PASS Splash box size linked to User.BoxSize
PASS Splash offset linked to User.SpawnOffset
PASS Splash velocity HLSL {'hlslExpression': 'float3(0, 0, -User.SplashFall)'}
PASS Splash no gravity/drag/scale-colour ['ParticleState', 'Collision', 'SolveForcesAndVelocity', 'SetVariables_70CAB2DE4BF939FD77028195D560881E', 'SetVariables_CCDCCEBA48680B8A4AE54CAE8549FA9F']
PASS Splash Collision before SolveForcesAndVelocity ['ParticleState', 'Collision', 'SolveForcesAndVelocity', 'SetVariables_70CAB2DE4BF939FD77028195D560881E', 'SetVariables_CCDCCEBA48680B8A4AE54CAE8549FA9F']
PASS Splash collision mode = GPU Distance Fields (Q3) GPU Distance Fields
PASS Splash collision enabled {'value': -1}
PASS Splash kill on collision = False {'value': 0}
PASS Splash radius type Custom Custom
PASS Splash particle radius cm {'value': 6}
PASS Splash restitution 0 {'value': 0}
PASS Splash friction 1 {'value': 1}
PASS Splash rest state on {'value': -1}
PASS Splash renderer 0 Unaligned FaceCamera
-- Splash latch and renderer 1
PASS latch spawn module present SetVariables_21E3B4794C67212C2EB0C890A8C5B292
PASS latch spawn Landed false, RingSize (30,30), SpriteFacing (0,0,1) {'Particles.Landed': {'value': 0}, 'Particles.RingSize': {'x': 30, 'y': 30}, 'Particles.SpriteFacing': {'x': 0, 'y': 0, 'z': 1}}
PASS latch update modules present SetVariables_70CAB2DE4BF939FD77028195D560881E SetVariables_CCDCCEBA48680B8A4AE54CAE8549FA9F
PASS latch order: Collision < Landed < Color ['ParticleState', 'Collision', 'SolveForcesAndVelocity', 'SetVariables_70CAB2DE4BF939FD77028195D560881E', 'SetVariables_CCDCCEBA48680B8A4AE54CAE8549FA9F']
PASS latch Landed expression 
PASS latch Color expression 
PASS no other module after Color latch ['ParticleState', 'Collision', 'SolveForcesAndVelocity', 'SetVariables_70CAB2DE4BF939FD77028195D560881E', 'SetVariables_CCDCCEBA48680B8A4AE54CAE8549FA9F']
PASS renderer 1 custom facing CustomFacingVector
PASS renderer 1 facing binding Particles.SpriteFacing ExplicitParticles
PASS renderer 1 size binding Particles.RingSize ExplicitParticles
-- compile
PASS compile aggregate UpToDate UpToDate
PASS Rain GPU compute script compiled ['UpToDate']
PASS Rain all scripts UpToDate [('ParticleSpawnScriptInterpolated', 'UpToDate'), ('ParticleUpdateScript', 'UpToDate'), ('ParticleGPUComputeScript', 'UpToDate')]
PASS Splash GPU compute script compiled ['UpToDate']
PASS Splash all scripts UpToDate [('ParticleSpawnScriptInterpolated', 'UpToDate'), ('ParticleUpdateScript', 'UpToDate'), ('ParticleGPUComputeScript', 'UpToDate')]
PASS stack issues: no errors errors=0 warnings=0 infos=4
-- actors
PASS S1_Spike_CyN exactly one editor-world actor ['/Game/LastBell/Maps/L_Monastery.L_Monastery:PersistentLevel.NiagaraActor_0']
PASS S1_Spike_CyN in folder FX/Spike 
PASS S1_Spike_CyN transform loc {'x': 2500, 'y': 1150, 'z': 0} rot {'pitch': 0, 'yaw': 0, 'roll': 0} scale {'x': 1, 'y': 1, 'z': 1}
PASS S1_Spike_CyN User.RainRate 1540 (want 1540.0)
PASS S1_Spike_CyN User.SplashRate 200 (want 200.0)
PASS S1_Spike_CyN User.BoxSize (1400, 1100, 10) (want (1400.0, 1100.0, 10.0))
PASS S1_Spike_CyN User.SpawnOffset (0, 0, 1000) (want (0.0, 0.0, 1000.0))
PASS S1_Spike_CyN User.RainFall 1250 (want 1250.0)
PASS S1_Spike_CyN User.SplashFall 20000 (want 20000.0)
PASS S1_Spike_CyN User.RainRadius 10 (want 10.0)
PASS S1_Spike_CyS exactly one editor-world actor ['/Game/LastBell/Maps/L_Monastery.L_Monastery:PersistentLevel.NiagaraActor_2']
PASS S1_Spike_CyS in folder FX/Spike 
PASS S1_Spike_CyS transform loc {'x': 4500, 'y': -1150, 'z': 0} rot {'pitch': 0, 'yaw': 0, 'roll': 0} scale {'x': 1, 'y': 1, 'z': 1}
PASS S1_Spike_CyS User.RainRate 1260 (want 1260.0)
PASS S1_Spike_CyS User.SplashRate 200 (want 200.0)
PASS S1_Spike_CyS User.BoxSize (1400, 900, 10) (want (1400.0, 900.0, 10.0))
PASS S1_Spike_CyS User.SpawnOffset (0, 0, 1000) (want (0.0, 0.0, 1000.0))
PASS S1_Spike_CyS User.RainFall 1250 (want 1250.0)
PASS S1_Spike_CyS User.SplashFall 20000 (want 20000.0)
PASS S1_Spike_CyS User.RainRadius 10 (want 10.0)
PASS S1_Spike_Chapel exactly one editor-world actor ['/Game/LastBell/Maps/L_Monastery.L_Monastery:PersistentLevel.NiagaraActor_3']
PASS S1_Spike_Chapel in folder FX/Spike 
PASS S1_Spike_Chapel transform loc {'x': 7000, 'y': 0, 'z': 0} rot {'pitch': 0, 'yaw': 0, 'roll': 0} scale {'x': 1, 'y': 1, 'z': 1}
PASS S1_Spike_Chapel User.RainRate 2520 (want 2520.0)
PASS S1_Spike_Chapel User.SplashRate 300 (want 300.0)
PASS S1_Spike_Chapel User.BoxSize (1800, 1400, 10) (want (1800.0, 1400.0, 10.0))
PASS S1_Spike_Chapel User.SpawnOffset (0, 0, 2500) (want (0.0, 0.0, 2500.0))
PASS S1_Spike_Chapel User.RainFall 1250 (want 1250.0)
PASS S1_Spike_Chapel User.SplashFall 20000 (want 20000.0)
PASS S1_Spike_Chapel User.RainRadius 10 (want 10.0)
PASS S1_Spike_Cloister exactly one editor-world actor ['/Game/LastBell/Maps/L_Monastery.L_Monastery:PersistentLevel.NiagaraActor_4']
PASS S1_Spike_Cloister in folder FX/Spike 
PASS S1_Spike_Cloister transform loc {'x': 10900, 'y': 1800, 'z': 0} rot {'pitch': 0, 'yaw': 0, 'roll': 0} scale {'x': 1, 'y': 1, 'z': 1}
PASS S1_Spike_Cloister User.RainRate 2640 (want 2640.0)
PASS S1_Spike_Cloister User.SplashRate 300 (want 300.0)
PASS S1_Spike_Cloister User.BoxSize (1200, 2200, 10) (want (1200.0, 2200.0, 10.0))
PASS S1_Spike_Cloister User.SpawnOffset (0, 0, 1500) (want (0.0, 0.0, 1500.0))
PASS S1_Spike_Cloister User.RainFall 1250 (want 1250.0)
PASS S1_Spike_Cloister User.SplashFall 20000 (want 20000.0)
PASS S1_Spike_Cloister User.RainRadius 10 (want 10.0)
PASS S1_Spike_Tower exactly one editor-world actor ['/Game/LastBell/Maps/L_Monastery.L_Monastery:PersistentLevel.NiagaraActor_5']
PASS S1_Spike_Tower in folder FX/Spike 
PASS S1_Spike_Tower transform loc {'x': 12500, 'y': 2000, 'z': 2500} rot {'pitch': 0, 'yaw': 0, 'roll': 0} scale {'x': 1, 'y': 1, 'z': 1}
PASS S1_Spike_Tower User.RainRate 920 (want 920.0)
PASS S1_Spike_Tower User.SplashRate 150 (want 150.0)
PASS S1_Spike_Tower User.BoxSize (960, 960, 10) (want (960.0, 960.0, 10.0))
PASS S1_Spike_Tower User.SpawnOffset (0, 0, 2600) (want (0.0, 0.0, 2600.0))
PASS S1_Spike_Tower User.RainFall 1250 (want 1250.0)
PASS S1_Spike_Tower User.SplashFall 20000 (want 20000.0)
PASS S1_Spike_Tower User.RainRadius 10 (want 10.0)
-- dirty state (INFO; dirty is expected, nothing may be saved)
INFO is_dirty /Game/LastBell/Maps/L_Monastery True
INFO is_dirty /Game/LastBell/FX/Spike/M_LB_Spike_Unlit True
INFO is_dirty /Game/LastBell/FX/Spike/NS_LB_Rain_Spike True
RESULT: all PASS
```

## 8. Round 2 build (2026-11-08; spec `Docs/plans/P15_S1_RAIN_SPIKE.md` section 8.1; editor open, PIE off, nothing captured, nothing saved)

Round 1 showed that splashes latch orange at first contact and then keep moving (slide off sloped roofs, tunnel through the 20 cm slab at 20000 cm/s), and that no rain reaches the belfry. Round 2 pins each splash and tries to make the tower roof's distance field two-sided. Script: `s1_spike.py pin` (Splash emitter only), `set`, `check`.

### 8.1 Pin chain (Splash emitter only; Rain, the material and the system defaults are untouched)

New Particle Spawn module (appended after the round 1 spawn module `SetVariables_21E3...`): `Particles.LandPos` (type `/Script/Niagara.NiagaraPosition`) = `Particles.Position`, `Particles.LandAge` (float) = 0.

Particle Update, read back with `GetScriptStackTopology` (execution order). One SetParameters module per row, because a module that reads a value another entry of the same module writes would see last frame's value:

| # | Module (this session's GUID, abbreviated) | Entries (HLSL) |
|---|---|---|
| 1 | `ParticleState` | built in |
| 2 | `Collision` | GPU Distance Fields, kill off, radius 6, restitution 0, friction 1, rest state on |
| 3 | `SolveForcesAndVelocity` | built in |
| 4 | `SetVariables_79FF...` | `Particles.LandPos` = `Particles.Landed ? Particles.LandPos : Particles.Position` (runs BEFORE the Landed update, so it captures the first post-collision position) |
| 5 | `SetVariables_464E...` | `Particles.Landed` = `Particles.Landed \|\| Particles.HasCollided` |
| 6 | `SetVariables_90B6...` | `Particles.Position` = `Particles.Landed ? Particles.LandPos : Particles.Position`; `Particles.Velocity` = `Particles.Landed ? float3(0, 0, 0) : Particles.Velocity` |
| 7 | `SetVariables_D61F...` | `Particles.LandAge` = `Particles.Landed ? Particles.LandAge + Engine.DeltaTime : 0.0` |
| 8 | `SetVariables_0851...` | `Particles.Color` = `Particles.Landed ? float4(5.0, 1.4, 0.2, 1.0) : float4(0.0, 0.0, 0.0, 0.0)` |
| 9 | `SetVariables_C2D4...` | `DataInstance.Alive` = `Particles.LandAge <= 0.45` |

Why this holds a splash still: the pin modules run after `Solve Forces and Velocity` (every SetParameters module appends at the end of the stack), so `Position` is re-pinned to `LandPos` after the integration, and `Velocity` is zeroed after it, so the next frame's Collision and Solve start from zero velocity. The first contact frame itself integrates normally (Landed is still false when Solve runs), so `LandPos` should be the post-Solve position of that frame (expected from the order, to be confirmed in the captures).

Compile after the build: `GetSystemCompileState` aggregate `UpToDate`, no errors, no warnings, not stale; all 8 scripts `UpToDate`, including `ParticleGPUComputeScript` of both emitters. `GetStackIssues`: 0 errors, 0 warnings, 4 infos (the same version-upgrade notes as round 1).

New recipe facts (add to section 3):
- **No MoveModule tool.** `AddSetParametersModule` only appends, so putting a module before an existing one means removing the tail and re-adding it in order. `s1_spike.py pin` does that: it compares the modules after `SolveForcesAndVelocity` with `UPDATE_CHAIN` (by their input names), removes every SetParameters module of the tail if they differ, re-adds the six in order, then sets each expression. Run twice, the second run changes nothing structural (the modules match, only the expressions are re-set). The round 1 `Landed` and `Color` modules were removed and re-created: the GUIDs of section 5 no longer exist.
- **Position type.** `/Script/Niagara.NiagaraPosition` for `Particles.LandPos` and `Particles.Position`, with a `Vector3f` literal default, was accepted by `AddSetParametersModule`. `Particles.Velocity` is `Vector3f`. `DataInstance.Alive` (bool) is accepted as a SetParameters entry and compiles on CPU and GPU.
- Engine attribute names compile in the HLSL expressions: `Engine.DeltaTime`, `Particles.HasCollided`, `Particles.LandPos`.

### 8.2 Tower roof distance field: NO MCP ROUTE (step skipped)

Goal: set `bGenerateDistanceFieldAsIfTwoSided` true in LOD 0 build settings of `/Game/LastBell/Environments/BellTower/Meshes/SM_LB_Tw_Roof_BrokenSW`. Tried, in this order:
1. **StaticMeshTools** (`editor_toolset.toolsets.static_mesh.StaticMeshTools`): 17 tools (Nanite, collision, LODs, thresholds, materials, bounds, counts, import). None touches build settings or distance fields.
2. **ObjectTools** on the mesh: `list_properties` lists 32 properties of `StaticMesh`; `sourceModels` is not among them (the build settings live in `StaticMesh.SourceModels[0].BuildSettings`). `get_properties` for `sourceModels`, `SourceModels`, `sourceModels[0]`, `sourceModels[0].buildSettings`, `sourceModels.0`, `buildSettings`, `bGenerateDistanceFieldAsIfTwoSided`, `distanceFieldReplacementMesh`: all raise `GetObjectProperties on '...SM_LB_Tw_Roof_BrokenSW' (StaticMesh): the following properties could not be read: <name>`. `set_properties` with `{"sourceModels": [{"buildSettings": {"bGenerateDistanceFieldAsIfTwoSided": true}}]}` (and `SourceModels`) raises `SetObjectProperties on '...' (StaticMesh): the following properties could not be set: sourceModels`. The structs `/Script/Engine.StaticMeshSourceModel` and `/Script/Engine.MeshBuildSettings` do list the field (`list_properties` on the struct paths), but there is no object to address them through.
3. **Editor subsystems:** `EditorAppToolset` has no console-command or Python tool (only `SearchCVars` to look cvars up); `ProgrammaticToolset.execute_tool_script` runs a sandbox (modules `re, math, json, time, copy, datetime`) that can only call the same registered tools; `AssetTools` has `read_file` and `write_file` for text files only. No route.
4. `bGenerateMeshDistanceField` (exposed) reads false on this mesh; it is ignored when the project setting "Generate Mesh Distance Fields" is on, and says nothing about two-sided.

Result: the flag was NOT set and the mesh was NOT touched (`AssetTools.is_dirty` False before and after the attempts). `s1_spike.py check` prints a SKIP line for it. Consequence for the plan: set the flag by hand in the Static Mesh Editor (LOD 0 > Build Settings > "Two-Sided Distance Field Generation", then save the mesh), or use the P15-6 fallback, a small local rain emitter under the collapse inside the belfry.

### 8.3 Actors

`s1_spike.py set --world editor --splash-fall 1250 --radius 20`: all five actors read back `SplashFall=1250`, `RainRadius=20` (rain rates, splash rates, box sizes and offsets unchanged). The system's own user-variable defaults stay 20000 and 10: the actor values are the round 2 setting, and `check` now expects 1250 and 20 on the actors (`ACTOR_SPLASH_FALL`, `ACTOR_RADIUS`).

### 8.4 `check` (round 2)

137 PASS, 0 FAIL, 1 SKIP, exit 0. New lines: `pin spawn module present`, `pin spawn LandPos = Particles.Position`, `pin spawn LandAge = 0`, `pin chain: 6 SetParameters modules after Solve, exact order`, seven `pin update <name> = <expression>` lines, `order: LandPos captured BEFORE Landed is updated`, `order: all pin modules after Collision and Solve`, `order: Alive is the last module`, `order: Position/Velocity pin after Landed, before LandAge`, and the actor lines `SplashFall 1250`, `RainRadius 20`. The SKIP line: `SKIP tower mesh bGenerateDistanceFieldAsIfTwoSided: no MCP route`.

Save state after round 2: `AssetTools.is_dirty` is True for `/Game/LastBell/Maps/L_Monastery`, `/Game/LastBell/FX/Spike/NS_LB_Rain_Spike` and `/Game/LastBell/FX/Spike/M_LB_Spike_Unlit`, False for `SM_LB_Tw_Roof_BrokenSW`. Nothing was saved.
