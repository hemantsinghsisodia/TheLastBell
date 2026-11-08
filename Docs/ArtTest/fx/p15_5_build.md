# P15-5: Niagara systems (build record)

Built 2026-11-08 by `Tools/fx/p15_5_niagara.py` (`build`, `check`, `save`) over Unreal MCP. Spec: `Docs/plans/P15_PARTICLES.md` section 6 (6.1 to 6.6). Editor open on `L_Monastery`, PIE never started, no actor placed, no viewport capture. The seven systems are saved, one package per call, `is_dirty` False after each. The map, `M_LB_Surface`, `MPC_LB_Storm`, every Blueprint, every material and MI, and `NS_LB_SmokeWisp` were not touched (`is_dirty` False before and after).

## 1. Method
The S1 recipe (`Docs/ArtTest/fx/s1/s1_build.md`) carried over unchanged: `CreateNiagaraSystem` from `/Niagara/DefaultAssets/DefaultSystem` with `Fountain` removed; `AddEmitter` from the `Fountain` template and the modules it does not need removed; user variables with `Vector3f`/`Vector2f` value structs; module inputs with `SetStackInputData` (literal, linked, HLSL, enum by `UEnum_Info`, dynamic input); `AddSetParametersModule` for every per-particle rule, one module per row; the `Collision` module's static switch `GPU Collision Type` on the placed module; `ApplyStackIssueFix` for the module order; `SetRendererData` with a binding copied from the default and re-pointed. `build` removes every emitter and user variable of an existing system first, so each run rebuilds from scratch (`NS_LB_Rain` was rebuilt three times and `NS_LB_StrikeSparks` and `NS_LB_Drip` twice; every run ended `BUILD OK` except the first sparks build, below). New facts are in `Tools/mcp/MCP_NOTES.md` ("Niagara systems over MCP").

The one compile error met on the way (`NS_LB_StrikeSparks`, first build) was integer modulo (`Integer modulo/remainder is not an allowed operation on ES 2`); `GetSystemCompileState` showed only "Error" and the text came from the log. It was fixed with float math, and the system rebuilt clean.

## 2. The systems
All in `/Game/LastBell/FX/Niagara/`. Materials are the P15-4 MIs in `/Game/LastBell/Materials/Instances/FX/`. `GetStackIssues`: 0 errors and 0 warnings on every system (the infos are the engine's version-upgrade notes for `ShapeLocation`, `ParticleState` and so on).

| System | Emitter (sim) | User parameters (type, default) | Renderers |
|---|---|---|---|
| `NS_LB_Rain` | `Rain` (GPU, fixed bounds), `Splash` (GPU, fixed bounds), `GroundMist` (CPU) | `RainRate` 35000, `BoxHalf` 1800, `SpawnHeight` 2500, `FallMin` 1100, `FallMax` 1400, `SplashRate` 2500, `SplashRadius` 1200, `Mist` 0 (all float); `Wind` Vector3f (0,0,0) | Rain: 1 sprite `MI_LB_Rain` velocity-aligned. Splash: 2 sprites, crown `MI_LB_Splash` (SubUV 4x4, `SubImageIndex`) and ring `MI_LB_Ripple` (custom facing `SpriteFacing`, `RingSize`, `RingColor`). GroundMist: 1 sprite `MI_LB_Mist` |
| `NS_LB_StrikeSparks` | `Sparks` (CPU) | none | sprite `MI_Flame_Torch` velocity-aligned, light renderer |
| `NS_LB_TorchFire` | `Flames`, `Embers`, `Smoke` (CPU) | `Scale` float 1; `Wind` Vector3f (0,0,0) | `MI_Flame_Torch` (flames: upright billboard; embers), `MI_LB_Mist` (smoke) |
| `NS_LB_ShaftDust` | `Dust` (GPU, local space, fixed bounds) | `BoxExtent` Vector3f (100,30,100), `Count` float 120 | `MI_LB_DustMote` |
| `NS_LB_WaterMist` | `Mist` (CPU) | `Extent` Vector2f (400,390) | `MI_LB_WaterMist` |
| `NS_LB_Drip` | `Drop` (CPU, local space) | `FallHeight` float 500, `Interval` Vector2f (1.5,4), `bWater` bool false | A falling drop `MI_LB_Rain`, B crown `MI_LB_Splash`, C ring `MI_LB_Ripple` |
| `NS_LB_EaveDrips` | `Drops` (CPU, local space) | `LineLength` float 400, `FallHeight` float 500, `bWater` bool false | same A, B, C |

### NS_LB_Rain, what the C++ sets
Names and types match the task table exactly (`Wind` is `Vector3f`, the rest `NiagaraFloat`).
- **Fixed bounds:** both GPU emitters ±4000 cm in X and Y, Z -1000 to +3000, relative to the owner (the box ±1800, the splash disc 1200, the spawn height 2500 + jitter 200 and the kill depth -800 all fit inside).
- **Rain:** box XY `BoxHalf*2` x Z 400 (jitter ±200), offset `(0,0,SpawnHeight)`. **Velocity = `RandomRangeVector` dynamic input** (not an HLSL expression), Minimum `(Wind.x, Wind.y, Wind.z - FallMax)`, Maximum `(Wind.x, Wind.y, Wind.z - FallMin)`, so the fall speed is random per drop and the wind is added. Lifetime 3.5, no drag, no gravity. `Collision`: `GPU Collision Type` GPU Distance Fields, kill on collision, `Radius Calculation Type` Custom, radius 20. Kill below the camera: SetParameters `DataInstance.Alive = DataInstance.Alive && Particles.Position.z > Engine.Owner.Position.z - 800.0` (the `DataInstance.Alive &&` keeps the collision's kill). Sprite size Random Non-Uniform (0.7, 28) to (0.7, 42), colour (1,1,1,0.7), `MI_LB_Rain`, velocity-aligned.
- **Splash:** spawns in a 1 cm high cylinder (a disc) of radius `SplashRadius` at `SpawnHeight`, velocity `RandomRangeVector` `(0,0,-FallMax)` to `(0,0,-FallMin)`. Collision as the rain but kill off, radius 6, restitution 0, friction 1, rest state on. Update stack, in order: `ParticleState`, `Collision`, `SolveForcesAndVelocity`, then the S1 round 2 chain, one SetParameters module each: 1 `LandPos`, 2 `Landed`, 3 `Position` + `Velocity`, 4 `LandAge`, 5 colours and sizes (below), 6 `DataInstance.Alive`. The two spawn modules set `Landed` false, `RingSize`, `RingColor` 0, `SpriteFacing` (0,0,1), `LandPos = Particles.Position`, `LandAge` 0. Step 5 sets `Particles.Color` (crown, alpha 0 until landed), `Particles.RingColor` (alpha 0.6 to 0 over `LandAge` 0.45, 0 until landed), `Particles.RingSize` (4 to 22 over `LandAge` 0.45) and `Particles.SubImageIndex = min(15, floor(LandAge / 0.45 * 16))`. Crown size 6 to 10 (Random Uniform sprite size). The ring has its own size and colour attributes, bound on renderer 2, so the crown and the ring differ.
- **GroundMist:** rate `5 * User.Mist`, Ring/Disc shape, outer radius 2200, `Disc Coverage` 0.727273 (inner radius 600), offset `RandomRangeVector` Z -160 to -80 (that is -120 ±40), lifetime 6, velocity `User.Wind * 0.15`, size Random Uniform 250 to 450, random rotation, colour alpha `sin(pi * NormalizedAge)` (0 to 1 to 0), `MI_LB_Mist`.

## 3. Drip route: the fallback (no event handlers over MCP)
The 46 tools of `NiagaraToolset_System` (and the Component, Info, Assets and Blueprint toolsets) have no tool that adds an event handler script or a Generate/Receive Location Event. The F0 survey said the same ("No: scratch-pad or custom HLSL modules"; events were not listed). So the fallback of the task is built, for both systems:
- **One particle per drop**, emitter in local space, so `Position.z` is the local Z. It starts at the origin with zero velocity and falls under `GravityForce` (0,0,-980).
- **The latch** (the S1 pattern), five SetParameters modules after `GravityForce` and `SolveForcesAndVelocity`, plus a spawn module: `Landed = Landed || Position.z <= -User.FallHeight`; `Position = Landed ? (x, y, -User.FallHeight) : Position` and `Velocity = Landed ? 0 : Velocity`; `LandAge = Landed ? LandAge + DeltaTime : 0`; then the visibility tag, colours and sizes; then `DataInstance.Alive = LandAge <= (User.bWater ? 0.6 : 0.3) && Age < Lifetime`.
- **Visibility tag:** `Particles.VisibilityTag` is 0 while falling and 1 once landed. Renderer A (falling drop, `MI_LB_Rain`, velocity-aligned, size (0.5, 5)) has `RendererVisibility` 0; renderers B (crown `MI_LB_Splash`, SubUV 4x4 over 0.3 s, size 6) and C (ring `MI_LB_Ripple`, 2 to 18 cm over 0.6 s, alpha 0.6 to 0) have `RendererVisibility` 1. The ring's colour alpha is 0 unless `User.bWater`, so the ring shows only on water. The crown has its own colour and size attributes (`CrownColor`, `CrownSize`), bound on renderer B.
- **The "6-droplet burst" is the crown SubUV** (the 4x4 crown frames), as the task allows.
- **`NS_LB_Drip` interval:** a burst loop, not a rate. `SpawnBurst_Instantaneous` (1 drop at t = 0), `EmitterState` Loop Behavior Infinite, `Loop Duration` = `RandomRangeFloat(User.Interval.x, User.Interval.y)` with `Recalculate Duration Each Loop` true (a new random gap after each drop), plus a random first delay `RandomRangeFloat(0, Interval.y)` with `Delay First Loop Only` true, so several drip points do not start in step.
- **`NS_LB_EaveDrips`:** rate 6 per second, in a thin box along local X (`LineLength` x 0.1 x 0.1, offset `LineLength / 2`), so the line starts at the actor and runs along its +X. It also has `User.FallHeight` (F0.9 needs it) and `User.bWater` (default false).

## 4. Sparks: the light renderer method
`NS_LB_StrikeSparks` has two renderers: the sprites and a `NiagaraLightRendererProperties` renderer. The 5 % rule is the light renderer's own per-particle option: `LightRenderingEnabledBinding` is bound to `Particles.LightEnabled` (bool), set at spawn to true for every 20th `Particles.UniqueID` (4 of the 70 sparks). `RadiusBinding` -> `Particles.LightRadius` (400), `ColorBinding` -> `Particles.LightColor` ((20, 15, 9), the spark colour x 20, fading with age), `bUseInverseSquaredFalloff` false, `bAffectsTranslucency` false. No visibility tag is used. The UniqueID test uses float math, because integer modulo does not compile for the Vector VM (`ES 2`).
The system completes: system `SystemState` Loop Behavior Once, Loop Duration 1.5, Inactive Response Complete; the emitter is Once / Complete, with a single burst of 70 at t = 0 and no `SpawnRate` module.

## 5. Deviations from the plan and the task text
1. **Splash collision radius is 6 cm, not 20.** The plan says "collision as for rain"; the S1 round 2 build that passed (0 splash pixels under any roof) used radius 6 on the splash and 20 on the rain only. With 20 the pinned splash would sit 20 cm above the floor. The constant is `SPLASH_COLLISION_RADIUS` in the script, one line to change. If the splash tunnels a thin roof, raise it.
2. **Splash spawn shape is a Cylinder of height 1 cm,** not Ring/Disc, because its axis (Z) is certain. `GroundMist` uses Ring/Disc; its plane (XY) is assumed from the Niagara defaults and was not seen run.
3. **Splash `DataInstance.Alive`** is `LandAge <= 0.45 && Age < Lifetime && Position.z > Engine.Owner.Position.z - 800`, not only `LandAge <= 0.45`: in S1 a splash that never found a surface would live for ever.
4. **Splash step 5** also carries `RingColor`, `RingSize` and `SubImageIndex` (they read only `Landed` and `LandAge`, which earlier modules wrote, so one module is right).
5. **Sparks:** sprite size is Random Non-Uniform width 1 to 2.5, length 4 to 10 (a velocity-aligned sprite needs a length; the plan says 1 to 2.5). Sphere velocity is `From Point` on a 1 cm sphere. The fade is `alpha = 1 - NormalizedAge`.
6. **TorchFire:** `Scale` multiplies the flame rate and size and the ember rate; the smoke size and all three emitters' spawn radius (4, 5, 6 cm x Scale) also scale. Smoke alpha is `0.1 * sin(pi * age)` (the plan only says 0.1; a hard pop looks wrong). The flames are upright billboards (`CustomAlignment` with the world +Z axis) so they stay vertical when the camera pitches.
7. **ShaftDust:** `BoxExtent` is the half-extent (F0.6), so the box is `BoxExtent * 2`. Motion is `CurlNoiseForce` 20 with `Drag` 4 (terminal speed about 5 cm/s). Local-space fixed bounds ±700 cm cover the largest F0.6 half-extent (600).
8. **WaterMist:** `User.Extent` is the full plane size (495 x 390 for the west pool). Drift is random ±5 cm/s in X and Y (`RandomRangeVector`), not one fixed direction.
9. **Drips:** the fallback above. Defaults `FallHeight` 500, `bWater` false; the placing task sets them per point (F0.8, F0.9).
10. **Rain velocity** uses a dynamic input rather than an HLSL expression, as the task allowed; both read the `User` parameters.

## 6. Not seen at run time (needs the P15-6 / P15-7 Simulate captures)
- `CaptureAssetImage` is refused for Niagara systems ("Asset type does not support image capture", all 7). **Visual check deferred to the P15-6/P15-7 Simulate captures.** Nothing here has been seen to run: the compile state, the module stacks and the read-backs are what was validated.
- Specific things to look at: the drip loop timing (random interval, first delay) and that a drip lands at `-FallHeight`; the ring and crown only after landing; the GroundMist ring plane and inner radius; the flame billboard staying upright; the light on the sparks; the sparks system freeing itself (`bAutoDestroy`); GPU particle counts of the rain at 35000 /s (allocation is automatic); the cost with `stat gpu`.

## 7. `check` output (exit 0)
```
﻿== NS_LB_Rain check ==
PASS NS_LB_Rain exists 
PASS NS_LB_Rain in /Game/LastBell/FX/Niagara 
PASS NS_LB_Rain user variable count 9 (want 9): ['User.BoxHalf', 'User.FallMax', 'User.FallMin', 'User.Mist', 'User.RainRate', 'User.SpawnHeight', 'User.SplashRadius', 'User.SplashRate', 'User.Wind']
PASS NS_LB_Rain User.RainRate NiagaraFloat default 35000
PASS NS_LB_Rain User.BoxHalf NiagaraFloat default 1800
PASS NS_LB_Rain User.SpawnHeight NiagaraFloat default 2500
PASS NS_LB_Rain User.FallMin NiagaraFloat default 1100
PASS NS_LB_Rain User.FallMax NiagaraFloat default 1400
PASS NS_LB_Rain User.Wind Vector3f default (0, 0, 0)
PASS NS_LB_Rain User.SplashRate NiagaraFloat default 2500
PASS NS_LB_Rain User.SplashRadius NiagaraFloat default 1200
PASS NS_LB_Rain User.Mist NiagaraFloat default 0
PASS NS_LB_Rain emitters Rain, Splash, GroundMist ['Rain', 'Splash', 'GroundMist']
PASS NS_LB_Rain compile aggregate UpToDate aggregate=UpToDate errors=False stale=False
PASS NS_LB_Rain every script UpToDate 10 scripts
PASS NS_LB_Rain/Rain GPU compute script compiled ['UpToDate']
PASS NS_LB_Rain/Splash GPU compute script compiled ['UpToDate']
PASS NS_LB_Rain/Rain has spawn and update scripts ['ParticleGPUComputeScript', 'ParticleSpawnScriptInterpolated', 'ParticleUpdateScript']
PASS NS_LB_Rain/Splash has spawn and update scripts ['ParticleGPUComputeScript', 'ParticleSpawnScriptInterpolated', 'ParticleUpdateScript']
PASS NS_LB_Rain/GroundMist has spawn and update scripts ['ParticleSpawnScriptInterpolated', 'ParticleUpdateScript']
PASS NS_LB_Rain stack issues: 0 errors errors=0 warnings=0 infos=6
-- emitter Rain
PASS NS_LB_Rain/Rain SimTarget GPUComputeSim GPUComputeSim
PASS NS_LB_Rain/Rain local space False 
PASS NS_LB_Rain/Rain fixed bounds ((-4000, -4000, -1000), (4000, 4000, 3000)) mode=Fixed (-4000, -4000, -1000, 4000, 4000, 3000)
PASS NS_LB_Rain/Rain spawn rate = User.RainRate User.RainRate
PASS Rain lifetime 3.5 3.5
PASS Rain colour (1, 1, 1, 0.7) (1, 1, 1, 0.699999988079071)
PASS Rain size min (0.7, 28.0) (0.699999988079071, 28)
PASS Rain size max (0.7, 42.0) (0.699999988079071, 42)
PASS Rain Rain/ShapeLocation.Shape Primitive Box / Plane
PASS Rain box XY +-User.BoxHalf, Z 400 (+-200 jitter) float3(User.BoxHalf * 2.0, User.BoxHalf * 2.0, 400.0)
PASS Rain spawn offset Z = User.SpawnHeight float3(0.0, 0.0, User.SpawnHeight)
PASS Rain Rain/AddVelocity.Velocity Mode Linear
PASS Rain velocity = dynamic input RandomRangeVector RandomRangeVector
PASS Rain velocity min = Wind + (0,0,-FallMax) float3(User.Wind.x, User.Wind.y, User.Wind.z - User.FallMax)
PASS Rain velocity max = Wind + (0,0,-FallMin) float3(User.Wind.x, User.Wind.y, User.Wind.z - User.FallMin)
PASS Rain no gravity / drag / scale-colour ['ParticleState', 'Collision', 'SolveForcesAndVelocity', 'SetVariables_A7678D6F490188407C61D0B933833BDA']
PASS NS_LB_Rain/Rain collision mode = GPU Distance Fields GPU Distance Fields
PASS NS_LB_Rain/Rain collision enabled True
PASS NS_LB_Rain/Rain kill on collision = True True
PASS NS_LB_Rain/Rain collision radius type Custom Custom
PASS NS_LB_Rain/Rain collision radius = 20 cm 20
PASS NS_LB_Rain/Rain Collision runs before SolveForcesAndVelocity ['ParticleState', 'Collision', 'SolveForcesAndVelocity', 'SetVariables_A7678D6F490188407C61D0B933833BDA']
PASS Rain DataInstance.Alive SetParameters present, last module SetVariables_A7678D6F490188407C61D0B933833BDA
PASS Rain Alive = kill below Engine.Owner.Position.z - 800 DataInstance.Alive && Particles.Position.z > Engine.Owner.Position.z - 800.0
PASS NS_LB_Rain/Rain renderer count 1 1
PASS NS_LB_Rain/Rain renderer 0 is sprite sprite
PASS NS_LB_Rain/Rain renderer 0 material MI_LB_Rain /Game/LastBell/Materials/Instances/FX/MI_LB_Rain.MI_LB_Rain
PASS NS_LB_Rain/Rain renderer 0 Alignment = VelocityAligned VelocityAligned
PASS NS_LB_Rain/Rain renderer 0 FacingMode = FaceCamera FaceCamera
-- emitter Splash
PASS NS_LB_Rain/Splash SimTarget GPUComputeSim GPUComputeSim
PASS NS_LB_Rain/Splash local space False 
PASS NS_LB_Rain/Splash fixed bounds ((-4000, -4000, -1000), (4000, 4000, 3000)) mode=Fixed (-4000, -4000, -1000, 4000, 4000, 3000)
PASS NS_LB_Rain/Splash spawn rate = User.SplashRate User.SplashRate
PASS Splash lifetime 5 5
PASS Splash colour (0, 0, 0, 0) (0, 0, 0, 0)
PASS Splash size min 6 6
PASS Splash size max 10 10
PASS Rain Splash/ShapeLocation.Shape Primitive Cylinder
PASS Splash disc radius = User.SplashRadius User.SplashRadius
PASS Splash disc height 1 cm 1
PASS Splash spawn offset Z = User.SpawnHeight float3(0.0, 0.0, User.SpawnHeight)
PASS Splash velocity = dynamic input RandomRangeVector RandomRangeVector
PASS Splash falls at rain speed: min (0,0,-FallMax) float3(0.0, 0.0, -User.FallMax)
PASS Splash falls at rain speed: max (0,0,-FallMin) float3(0.0, 0.0, -User.FallMin)
PASS NS_LB_Rain/Splash collision mode = GPU Distance Fields GPU Distance Fields
PASS NS_LB_Rain/Splash collision enabled True
PASS NS_LB_Rain/Splash kill on collision = False False
PASS NS_LB_Rain/Splash collision radius type Custom Custom
PASS NS_LB_Rain/Splash collision radius = 6 cm 6
PASS NS_LB_Rain/Splash restitution 0 0
PASS NS_LB_Rain/Splash friction 1 1
PASS NS_LB_Rain/Splash rest state on True
PASS NS_LB_Rain/Splash Collision runs before SolveForcesAndVelocity ['ParticleState', 'Collision', 'SolveForcesAndVelocity', 'SetVariables_B1E903F24326EBA62680228397F89B07']
PASS Splash update order before the chain: ParticleState, Collision, SolveForcesAndVelocity ['ParticleState', 'Collision', 'SolveForcesAndVelocity']
PASS Splash update stack = 3 built-ins + 6 chain modules 9
PASS Rain/Splash chain order LandPos/Landed/Position/LandAge/Color/Alive positions [3, 4, 5, 6, 7, 8] of 9 modules
PASS Rain/Splash SetParameters LandPos present 
PASS Rain/Splash LandPos = Particles.Landed ? Particles.LandPos : Particles.Position Particles.Landed ? Particles.LandPos : Particles.Position
PASS Rain/Splash SetParameters Landed present 
PASS Rain/Splash Landed = Particles.Landed || Particles.HasCollided Particles.Landed || Particles.HasCollided
PASS Rain/Splash SetParameters Position+Velocity present 
PASS Rain/Splash Position = Particles.Landed ? Particles.LandPos : Particles.Position Particles.Landed ? Particles.LandPos : Particles.Position
PASS Rain/Splash Velocity = Particles.Landed ? float3(0, 0, 0) : Particles.Velocity Particles.Landed ? float3(0, 0, 0) : Particles.Velocity
PASS Rain/Splash SetParameters LandAge present 
PASS Rain/Splash LandAge = Particles.Landed ? Particles.LandAge + Engine.DeltaTime : 0.0 Particles.Landed ? Particles.LandAge + Engine.DeltaTime : 0.0
PASS Rain/Splash SetParameters Color+RingColor+RingSize+SubImageIndex present 
PASS Rain/Splash Color = Particles.Landed ? float4(1.0, 1.0, 1.0, 1.0) : float4(0.0, 0.0, 0.0,  Particles.Landed ? float4(1.0, 1.0, 1.0, 1.0) : float4(0.0, 0.0, 0.0, 0.0)
PASS Rain/Splash RingColor = Particles.Landed ? float4(1.0, 1.0, 1.0, 0.6 * (1.0 - saturate(Particl Particles.Landed ? float4(1.0, 1.0, 1.0, 0.6 * (1.0 - saturate(Particles.LandAge / 0.45))) : float4(0.0, 0.0, 
PASS Rain/Splash RingSize = float2(1.0, 1.0) * lerp(4, 22, saturate(Particles.LandAge / 0.45)) float2(1.0, 1.0) * lerp(4, 22, saturate(Particles.LandAge / 0.45))
PASS Rain/Splash SubImageIndex = min(15.0, floor(Particles.LandAge / 0.45 * 16.0)) min(15.0, floor(Particles.LandAge / 0.45 * 16.0))
PASS Rain/Splash SetParameters Alive present 
PASS Rain/Splash Alive = Particles.LandAge <= 0.45 && Particles.Age < Particles.Lifetime && Par Particles.LandAge <= 0.45 && Particles.Age < Particles.Lifetime && Particles.Position.z > Engine.Owner.Positio
PASS Splash spawn stack has the two latch-state modules after AddVelocity ['InitializeParticle', 'ShapeLocation', 'AddVelocity', 'SetVariables_269368E74F2B74A6E145EBA3C1EBBDAD', 'SetVariables_3B821F734C418D0B1922A7BB15F5C617']
PASS Splash spawn Landed = False False
PASS Splash spawn RingSize = (4.0, 4.0) (4, 4)
PASS Splash spawn SpriteFacing = (0, 0, 1) (0, 0, 1)
PASS Splash spawn RingColor = (0, 0, 0, 0) (0, 0, 0, 0)
PASS Splash spawn LandPos = Particles.Position Particles.Position
PASS Splash spawn LandAge = 0 0
PASS NS_LB_Rain/Splash renderer count 2 2
PASS NS_LB_Rain/Splash renderer 0 is sprite sprite
PASS NS_LB_Rain/Splash renderer 0 material MI_LB_Splash /Game/LastBell/Materials/Instances/FX/MI_LB_Splash.MI_LB_Splash
PASS NS_LB_Rain/Splash renderer 0 Alignment = Unaligned Unaligned
PASS NS_LB_Rain/Splash renderer 0 FacingMode = FaceCamera FaceCamera
PASS NS_LB_Rain/Splash renderer 0 SubImageSize = {'x': 4, 'y': 4} {'x': 4, 'y': 4}
PASS NS_LB_Rain/Splash renderer 0 SubImageIndexBinding -> Particles.SubImageIndex Particles.SubImageIndex ExplicitParticles exists=True
PASS NS_LB_Rain/Splash renderer 1 is sprite sprite
PASS NS_LB_Rain/Splash renderer 1 material MI_LB_Ripple /Game/LastBell/Materials/Instances/FX/MI_LB_Ripple.MI_LB_Ripple
PASS NS_LB_Rain/Splash renderer 1 Alignment = Unaligned Unaligned
PASS NS_LB_Rain/Splash renderer 1 FacingMode = CustomFacingVector CustomFacingVector
PASS NS_LB_Rain/Splash renderer 1 SpriteFacingBinding -> Particles.SpriteFacing Particles.SpriteFacing ExplicitParticles exists=True
PASS NS_LB_Rain/Splash renderer 1 SpriteSizeBinding -> Particles.RingSize Particles.RingSize ExplicitParticles exists=True
PASS NS_LB_Rain/Splash renderer 1 ColorBinding -> Particles.RingColor Particles.RingColor ExplicitParticles exists=True
-- emitter GroundMist
PASS NS_LB_Rain/GroundMist SimTarget CPUSim CPUSim
PASS NS_LB_Rain/GroundMist local space False 
PASS NS_LB_Rain/GroundMist dynamic bounds Dynamic
PASS NS_LB_Rain/GroundMist spawn rate = 5.0 * User.Mist 5.0 * User.Mist
PASS GroundMist lifetime 6 6
PASS GroundMist colour (1, 1, 1, 1) (1, 1, 1, 1)
PASS GroundMist size min 250 250
PASS GroundMist size max 450 450
PASS GroundMist rotation random Random
PASS Rain GroundMist/ShapeLocation.Shape Primitive Ring / Disc
PASS GroundMist ring outer radius 2200 2200
PASS GroundMist disc coverage -> inner radius 600 0.7272729873657227
PASS GroundMist offset = RandomRangeVector (Z -120 +-40) RandomRangeVector
PASS GroundMist offset min (0,0,-160) (0, 0, -160)
PASS GroundMist offset max (0,0,-80) (0, 0, -80)
PASS GroundMist velocity = User.Wind * 0.15 User.Wind * 0.15
PASS Rain/GroundMist SetParameters Color present 
PASS Rain/GroundMist Color = float4(1.0, 1.0, 1.0, sin(3.14159265 * saturate(Particles.NormalizedAg float4(1.0, 1.0, 1.0, sin(3.14159265 * saturate(Particles.NormalizedAge)))
PASS NS_LB_Rain/GroundMist renderer count 1 1
PASS NS_LB_Rain/GroundMist renderer 0 is sprite sprite
PASS NS_LB_Rain/GroundMist renderer 0 material MI_LB_Mist /Game/LastBell/Materials/Instances/FX/MI_LB_Mist.MI_LB_Mist
PASS NS_LB_Rain/GroundMist renderer 0 Alignment = Unaligned Unaligned
PASS NS_LB_Rain/GroundMist renderer 0 FacingMode = FaceCamera FaceCamera
== NS_LB_StrikeSparks check ==
PASS NS_LB_StrikeSparks exists 
PASS NS_LB_StrikeSparks in /Game/LastBell/FX/Niagara 
PASS NS_LB_StrikeSparks user variable count 0 (want 0): []
PASS NS_LB_StrikeSparks emitters Sparks ['Sparks']
PASS NS_LB_StrikeSparks compile aggregate UpToDate aggregate=UpToDate errors=False stale=False
PASS NS_LB_StrikeSparks every script UpToDate 4 scripts
PASS NS_LB_StrikeSparks/Sparks has spawn and update scripts ['ParticleSpawnScriptInterpolated', 'ParticleUpdateScript']
PASS NS_LB_StrikeSparks stack issues: 0 errors errors=0 warnings=0 infos=2
PASS Sparks system loop behaviour Once Once
PASS Sparks system loop duration 1.5 s 1.5
PASS Sparks system inactive response Complete Complete (Let Emitters Finish then Kill The System)
PASS NS_LB_StrikeSparks/Sparks SimTarget CPUSim CPUSim
PASS NS_LB_StrikeSparks/Sparks local space False 
PASS NS_LB_StrikeSparks/Sparks dynamic bounds Dynamic
PASS Sparks no SpawnRate module (no infinite spawn) ['EmitterState', 'SpawnBurst_Instantaneous']
PASS Sparks burst count 70 70
PASS Sparks burst at t = 0 0
PASS Sparks emitter loop behaviour Once Once
PASS Sparks emitter inactive response Complete Complete (Let Particles Finish then Kill Emitter)
PASS Sparks emitter loop duration 0.25 s 0.25
PASS Sparks lifetime mode Random Random
PASS Sparks lifetime min 0.4 0.4000000059604645
PASS Sparks lifetime max 0.9 0.8999999761581421
PASS Sparks colour (6.0, 5.4, 4.2, 1.0) (6, 5.400000095367432, 4.199999809265137, 1)
PASS Sparks size min (1.0, 4.0) (1, 4)
PASS Sparks size max (2.5, 10.0) (2.5, 10)
PASS StrikeSparks Sparks/ShapeLocation.Shape Primitive Sphere
PASS Sparks velocity mode From Point (sphere) From Point
PASS Sparks speed = RandomRangeFloat RandomRangeFloat
PASS Sparks speed min 400 400
PASS Sparks speed max 900 900
PASS Sparks gravity (0,0,-980) (0, 0, -980)
PASS Sparks GravityForce before SolveForcesAndVelocity ['ParticleState', 'GravityForce', 'SolveForcesAndVelocity', 'SetVariables_CD9243244D4CFCDBEFA257ACE9D52689']
PASS StrikeSparks/Sparks SetParameters LightEnabled+LightRadius present 
PASS StrikeSparks/Sparks LightEnabled = (float(Particles.UniqueID) - 20 * floor((float(Particles.UniqueID) + 0 (float(Particles.UniqueID) - 20 * floor((float(Particles.UniqueID) + 0.5) / 20)) < 0.5
PASS StrikeSparks/Sparks LightRadius literal {'value': 400}
PASS NS_LB_StrikeSparks/Sparks renderer count 2 2
PASS NS_LB_StrikeSparks/Sparks renderer 0 is sprite sprite
PASS NS_LB_StrikeSparks/Sparks renderer 0 material MI_Flame_Torch /Game/LastBell/Materials/Instances/FX/MI_Flame_Torch.MI_Flame_Torch
PASS NS_LB_StrikeSparks/Sparks renderer 0 Alignment = VelocityAligned VelocityAligned
PASS NS_LB_StrikeSparks/Sparks renderer 1 is light light
PASS NS_LB_StrikeSparks/Sparks renderer 1 bUseInverseSquaredFalloff = False False
PASS NS_LB_StrikeSparks/Sparks renderer 1 bAffectsTranslucency = False False
PASS NS_LB_StrikeSparks/Sparks renderer 1 LightRenderingEnabledBinding -> Particles.LightEnabled Particles.LightEnabled ExplicitParticles exists=True
PASS NS_LB_StrikeSparks/Sparks renderer 1 RadiusBinding -> Particles.LightRadius Particles.LightRadius ExplicitParticles exists=True
PASS NS_LB_StrikeSparks/Sparks renderer 1 ColorBinding -> Particles.LightColor Particles.LightColor ExplicitParticles exists=True
INFO sparks light renderer method: LightRenderingEnabledBinding -> Particles.LightEnabled (every 20th Particles.UniqueID = 5 %); radius 400, colour x20
== NS_LB_TorchFire check ==
PASS NS_LB_TorchFire exists 
PASS NS_LB_TorchFire in /Game/LastBell/FX/Niagara 
PASS NS_LB_TorchFire user variable count 2 (want 2): ['User.Scale', 'User.Wind']
PASS NS_LB_TorchFire User.Scale NiagaraFloat default 1
PASS NS_LB_TorchFire User.Wind Vector3f default (0, 0, 0)
PASS NS_LB_TorchFire emitters Flames, Embers, Smoke ['Flames', 'Embers', 'Smoke']
PASS NS_LB_TorchFire compile aggregate UpToDate aggregate=UpToDate errors=False stale=False
PASS NS_LB_TorchFire every script UpToDate 8 scripts
PASS NS_LB_TorchFire/Flames has spawn and update scripts ['ParticleSpawnScriptInterpolated', 'ParticleUpdateScript']
PASS NS_LB_TorchFire/Embers has spawn and update scripts ['ParticleSpawnScriptInterpolated', 'ParticleUpdateScript']
PASS NS_LB_TorchFire/Smoke has spawn and update scripts ['ParticleSpawnScriptInterpolated', 'ParticleUpdateScript']
PASS NS_LB_TorchFire stack issues: 0 errors errors=0 warnings=0 infos=6
PASS NS_LB_TorchFire/Flames SimTarget CPUSim CPUSim
PASS NS_LB_TorchFire/Flames local space False 
PASS NS_LB_TorchFire/Flames dynamic bounds Dynamic
PASS NS_LB_TorchFire/Embers SimTarget CPUSim CPUSim
PASS NS_LB_TorchFire/Embers local space False 
PASS NS_LB_TorchFire/Embers dynamic bounds Dynamic
PASS NS_LB_TorchFire/Smoke SimTarget CPUSim CPUSim
PASS NS_LB_TorchFire/Smoke local space False 
PASS NS_LB_TorchFire/Smoke dynamic bounds Dynamic
-- emitter Flames
PASS NS_LB_TorchFire/Flames spawn rate = 14.0 * User.Scale 14.0 * User.Scale
PASS Flames lifetime mode Random Random
PASS Flames lifetime min 0.5 0.5
PASS Flames lifetime max 0.8 0.800000011920929
PASS Flames colour (1, 1, 1, 1) (1, 1, 1, 1)
PASS Flames size min 18 18
PASS Flames size max 30 30
PASS Flames velocity up 60 cm/s (0, 0, 60)
PASS TorchFire/Flames SetParameters SpriteSize+SpriteAlignment present 
PASS TorchFire/Flames SpriteSize = Particles.SpriteSize * User.Scale Particles.SpriteSize * User.Scale
PASS TorchFire/Flames SpriteAlignment literal {'x': 0, 'y': 0, 'z': 1}
PASS Flames curl noise 30 30
PASS TorchFire/Flames SetParameters Color present 
PASS TorchFire/Flames Color = float4(1.0, 1.0, 1.0, 1.0 - saturate(Particles.NormalizedAge)) float4(1.0, 1.0, 1.0, 1.0 - saturate(Particles.NormalizedAge))
PASS Flames CurlNoiseForce before SolveForcesAndVelocity ['ParticleState', 'CurlNoiseForce', 'SolveForcesAndVelocity', 'SetVariables_211AA330457A2D26DC74E2A702DA68B5']
PASS NS_LB_TorchFire/Flames renderer count 1 1
PASS NS_LB_TorchFire/Flames renderer 0 is sprite sprite
PASS NS_LB_TorchFire/Flames renderer 0 material MI_Flame_Torch /Game/LastBell/Materials/Instances/FX/MI_Flame_Torch.MI_Flame_Torch
PASS NS_LB_TorchFire/Flames renderer 0 Alignment = CustomAlignment CustomAlignment
PASS NS_LB_TorchFire/Flames renderer 0 FacingMode = FaceCamera FaceCamera
PASS NS_LB_TorchFire/Flames renderer 0 SpriteAlignmentBinding -> Particles.SpriteAlignment Particles.SpriteAlignment ExplicitParticles exists=True
-- emitter Embers
PASS NS_LB_TorchFire/Embers spawn rate = 6.0 * User.Scale 6.0 * User.Scale
PASS Embers lifetime mode Random Random
PASS Embers lifetime min 1 1
PASS Embers lifetime max 2 2
PASS Embers colour (4.0, 1.8, 0.4, 1.0) (4, 1.7999999523162842, 0.4000000059604645, 1)
PASS Embers size min 0.8 0.800000011920929
PASS Embers size max 1.5 1.5
PASS Embers velocity up 80 + User.Wind * 0.2 float3(0.0, 0.0, 80.0) + User.Wind * 0.2
PASS Embers curl noise 60 60
PASS Embers CurlNoiseForce before SolveForcesAndVelocity ['ParticleState', 'CurlNoiseForce', 'SolveForcesAndVelocity', 'SetVariables_1CF5557C4A48D15ABDFDFF9A1574A948']
PASS TorchFire/Embers SetParameters Color present 
PASS TorchFire/Embers Color = float4(4.0, 1.8, 0.4, 1.0 - saturate(Particles.NormalizedAge)) float4(4.0, 1.8, 0.4, 1.0 - saturate(Particles.NormalizedAge))
PASS NS_LB_TorchFire/Embers renderer count 1 1
PASS NS_LB_TorchFire/Embers renderer 0 is sprite sprite
PASS NS_LB_TorchFire/Embers renderer 0 material MI_Flame_Torch /Game/LastBell/Materials/Instances/FX/MI_Flame_Torch.MI_Flame_Torch
PASS NS_LB_TorchFire/Embers renderer 0 Alignment = Unaligned Unaligned
PASS NS_LB_TorchFire/Embers renderer 0 FacingMode = FaceCamera FaceCamera
-- emitter Smoke
PASS NS_LB_TorchFire/Smoke spawn rate = 3.0 3.0
PASS Smoke lifetime mode Random Random
PASS Smoke lifetime min 3 3
PASS Smoke lifetime max 4 4
PASS Smoke colour (0.08, 0.08, 0.08, 0.1) (0.07999999821186066, 0.07999999821186066, 0.07999999821186066, 0.10000000149011612)
PASS Smoke size 30 30
PASS Smoke velocity up 40 cm/s (0, 0, 40)
PASS TorchFire/Smoke SetParameters SpriteSize+Color present 
PASS TorchFire/Smoke SpriteSize = float2(1.0, 1.0) * lerp(30.0, 120.0, saturate(Particles.NormalizedAge) float2(1.0, 1.0) * lerp(30.0, 120.0, saturate(Particles.NormalizedAge)) * User.Scale
PASS TorchFire/Smoke Color = float4(0.08, 0.08, 0.08, 0.1 * sin(3.14159265 * saturate(Particles.Nor float4(0.08, 0.08, 0.08, 0.1 * sin(3.14159265 * saturate(Particles.NormalizedAge)))
PASS NS_LB_TorchFire/Smoke renderer count 1 1
PASS NS_LB_TorchFire/Smoke renderer 0 is sprite sprite
PASS NS_LB_TorchFire/Smoke renderer 0 material MI_LB_Mist /Game/LastBell/Materials/Instances/FX/MI_LB_Mist.MI_LB_Mist
PASS NS_LB_TorchFire/Smoke renderer 0 Alignment = Unaligned Unaligned
PASS NS_LB_TorchFire/Smoke renderer 0 FacingMode = FaceCamera FaceCamera
== NS_LB_ShaftDust check ==
PASS NS_LB_ShaftDust exists 
PASS NS_LB_ShaftDust in /Game/LastBell/FX/Niagara 
PASS NS_LB_ShaftDust user variable count 2 (want 2): ['User.BoxExtent', 'User.Count']
PASS NS_LB_ShaftDust User.BoxExtent Vector3f default (100, 30, 100)
PASS NS_LB_ShaftDust User.Count NiagaraFloat default 120
PASS NS_LB_ShaftDust emitters Dust ['Dust']
PASS NS_LB_ShaftDust compile aggregate UpToDate aggregate=UpToDate errors=False stale=False
PASS NS_LB_ShaftDust every script UpToDate 5 scripts
PASS NS_LB_ShaftDust/Dust GPU compute script compiled ['UpToDate']
PASS NS_LB_ShaftDust/Dust has spawn and update scripts ['ParticleGPUComputeScript', 'ParticleSpawnScriptInterpolated', 'ParticleUpdateScript']
PASS NS_LB_ShaftDust stack issues: 0 errors errors=0 warnings=0 infos=3
PASS NS_LB_ShaftDust/Dust SimTarget GPUComputeSim GPUComputeSim
PASS NS_LB_ShaftDust/Dust local space True 
PASS NS_LB_ShaftDust/Dust fixed bounds ((-700, -700, -700), (700, 700, 700)) mode=Fixed (-700, -700, -700, 700, 700, 700)
PASS NS_LB_ShaftDust/Dust spawn rate = User.Count / 10.0 User.Count / 10.0
PASS Dust lifetime mode Random Random
PASS Dust lifetime min 8 8
PASS Dust lifetime max 12 12
PASS Dust colour (1, 1, 1, 0) (1, 1, 1, 0)
PASS Dust size min 0.3 0.30000001192092896
PASS Dust size max 0.8 0.800000011920929
PASS ShaftDust Dust/ShapeLocation.Shape Primitive Box / Plane
PASS Dust box size = User.BoxExtent * 2 (BoxExtent is the half-extent) User.BoxExtent * 2.0
PASS Dust curl noise strength 20 20
PASS Dust drag 4 (terminal speed 5 cm/s) 4
PASS Dust forces before SolveForcesAndVelocity ['ParticleState', 'Drag', 'CurlNoiseForce', 'SolveForcesAndVelocity', 'SetVariables_E59AE0C14EF5A8FB6C7D788B8F548820']
PASS ShaftDust/Dust SetParameters Color present 
PASS ShaftDust/Dust Color = float4(1.0, 1.0, 1.0, sin(3.14159265 * saturate(Particles.NormalizedAg float4(1.0, 1.0, 1.0, sin(3.14159265 * saturate(Particles.NormalizedAge)))
PASS NS_LB_ShaftDust/Dust renderer count 1 1
PASS NS_LB_ShaftDust/Dust renderer 0 is sprite sprite
PASS NS_LB_ShaftDust/Dust renderer 0 material MI_LB_DustMote /Game/LastBell/Materials/Instances/FX/MI_LB_DustMote.MI_LB_DustMote
PASS NS_LB_ShaftDust/Dust renderer 0 Alignment = Unaligned Unaligned
PASS NS_LB_ShaftDust/Dust renderer 0 FacingMode = FaceCamera FaceCamera
== NS_LB_WaterMist check ==
PASS NS_LB_WaterMist exists 
PASS NS_LB_WaterMist in /Game/LastBell/FX/Niagara 
PASS NS_LB_WaterMist user variable count 1 (want 1): ['User.Extent']
PASS NS_LB_WaterMist User.Extent Vector2f default (400, 390)
PASS NS_LB_WaterMist emitters Mist ['Mist']
PASS NS_LB_WaterMist compile aggregate UpToDate aggregate=UpToDate errors=False stale=False
PASS NS_LB_WaterMist every script UpToDate 4 scripts
PASS NS_LB_WaterMist/Mist has spawn and update scripts ['ParticleSpawnScriptInterpolated', 'ParticleUpdateScript']
PASS NS_LB_WaterMist stack issues: 0 errors errors=0 warnings=0 infos=2
PASS NS_LB_WaterMist/Mist SimTarget CPUSim CPUSim
PASS NS_LB_WaterMist/Mist local space False 
PASS NS_LB_WaterMist/Mist dynamic bounds Dynamic
PASS NS_LB_WaterMist/Mist spawn rate = 4.0 4.0
PASS WaterMist lifetime 6 6
PASS WaterMist colour (1, 1, 1, 0) (1, 1, 1, 0)
PASS WaterMist size min 150 150
PASS WaterMist size max 300 300
PASS WaterMist box = User.Extent x 60 cm high float3(User.Extent.x, User.Extent.y, 60.0)
PASS WaterMist box lifted 30 cm (Z 0-60) float3(0.0, 0.0, 30.0)
PASS WaterMist drift = RandomRangeVector +-5 cm/s RandomRangeVector
PASS WaterMist/Mist SetParameters Color present 
PASS WaterMist/Mist Color = float4(1.0, 1.0, 1.0, 0.6 * sin(3.14159265 * saturate(Particles.Normal float4(1.0, 1.0, 1.0, 0.6 * sin(3.14159265 * saturate(Particles.NormalizedAge)))
PASS NS_LB_WaterMist/Mist renderer count 1 1
PASS NS_LB_WaterMist/Mist renderer 0 is sprite sprite
PASS NS_LB_WaterMist/Mist renderer 0 material MI_LB_WaterMist /Game/LastBell/Materials/Instances/FX/MI_LB_WaterMist.MI_LB_WaterMist
PASS NS_LB_WaterMist/Mist renderer 0 Alignment = Unaligned Unaligned
PASS NS_LB_WaterMist/Mist renderer 0 FacingMode = FaceCamera FaceCamera
== NS_LB_Drip check ==
PASS NS_LB_Drip exists 
PASS NS_LB_Drip in /Game/LastBell/FX/Niagara 
PASS NS_LB_Drip user variable count 3 (want 3): ['User.FallHeight', 'User.Interval', 'User.bWater']
PASS NS_LB_Drip User.FallHeight NiagaraFloat default 500
PASS NS_LB_Drip User.Interval Vector2f default (1.5, 4)
PASS NS_LB_Drip User.bWater NiagaraBool default False
PASS NS_LB_Drip emitters Drop ['Drop']
PASS NS_LB_Drip compile aggregate UpToDate aggregate=UpToDate errors=False stale=False
PASS NS_LB_Drip every script UpToDate 4 scripts
PASS NS_LB_Drip/Drop has spawn and update scripts ['ParticleSpawnScriptInterpolated', 'ParticleUpdateScript']
PASS NS_LB_Drip stack issues: 0 errors errors=0 warnings=0 infos=1
PASS NS_LB_Drip/Drop SimTarget CPUSim CPUSim
PASS NS_LB_Drip/Drop local space True 
PASS NS_LB_Drip/Drop dynamic bounds Dynamic
PASS NS_LB_Drip falling drop size (0.5, 5) cm (0.5, 5)
PASS Drip/Drop SetParameters Landed+LandAge+SpriteFacing+VisibilityTag+CrownColor+CrownSize+RingColor+RingSize present 
PASS Drip/Drop Landed literal {'value': 0}
PASS Drip/Drop LandAge literal {'value': 0}
PASS Drip/Drop SpriteFacing literal {'x': 0, 'y': 0, 'z': 1}
PASS Drip/Drop VisibilityTag literal {'value': 0}
PASS Drip/Drop CrownColor literal {'r': 0, 'g': 0, 'b': 0, 'a': 0}
PASS Drip/Drop CrownSize literal {'x': 6, 'y': 6}
PASS Drip/Drop RingColor literal {'r': 0, 'g': 0, 'b': 0, 'a': 0}
PASS Drip/Drop RingSize literal {'x': 2, 'y': 2}
PASS NS_LB_Drip gravity -980 (0, 0, -980)
PASS NS_LB_Drip gravity before SolveForcesAndVelocity, 3 + 5 chain modules 8
PASS Drip/Drop chain order Landed/Position/LandAge/VisibilityTag/Alive positions [3, 4, 5, 6, 7] of 8 modules
PASS Drip/Drop SetParameters Landed present 
PASS Drip/Drop Landed = Particles.Landed || Particles.Position.z <= -User.FallHeight Particles.Landed || Particles.Position.z <= -User.FallHeight
PASS Drip/Drop SetParameters Position+Velocity present 
PASS Drip/Drop Position = Particles.Landed ? float3(Particles.Position.x, Particles.Position.y,  Particles.Landed ? float3(Particles.Position.x, Particles.Position.y, -User.FallHeight) : Particles.Position
PASS Drip/Drop Velocity = Particles.Landed ? float3(0.0, 0.0, 0.0) : Particles.Velocity Particles.Landed ? float3(0.0, 0.0, 0.0) : Particles.Velocity
PASS Drip/Drop SetParameters LandAge present 
PASS Drip/Drop LandAge = Particles.Landed ? Particles.LandAge + Engine.DeltaTime : 0.0 Particles.Landed ? Particles.LandAge + Engine.DeltaTime : 0.0
PASS Drip/Drop SetParameters VisibilityTag+Color+CrownColor+SubImageIndex+RingColor+RingSize present 
PASS Drip/Drop VisibilityTag = Particles.Landed ? 1 : 0 Particles.Landed ? 1 : 0
PASS Drip/Drop Color = Particles.Landed ? float4(0.0, 0.0, 0.0, 0.0) : float4(1.0, 1.0, 1.0,  Particles.Landed ? float4(0.0, 0.0, 0.0, 0.0) : float4(1.0, 1.0, 1.0, 0.5)
PASS Drip/Drop CrownColor = (Particles.Landed && Particles.LandAge <= 0.3) ? float4(1.0, 1.0, 1.0, (Particles.Landed && Particles.LandAge <= 0.3) ? float4(1.0, 1.0, 1.0, 1.0) : float4(0.0, 0.0, 0.0, 0.0)
PASS Drip/Drop SubImageIndex = min(15.0, floor(Particles.LandAge / 0.3 * 16.0)) min(15.0, floor(Particles.LandAge / 0.3 * 16.0))
PASS Drip/Drop RingColor = (Particles.Landed && User.bWater) ? float4(1.0, 1.0, 1.0, 0.6 * (1.0 - (Particles.Landed && User.bWater) ? float4(1.0, 1.0, 1.0, 0.6 * (1.0 - saturate(Particles.LandAge / 0.6))) : f
PASS Drip/Drop RingSize = float2(1.0, 1.0) * lerp(2, 18, saturate(Particles.LandAge / 0.6)) float2(1.0, 1.0) * lerp(2, 18, saturate(Particles.LandAge / 0.6))
PASS Drip/Drop SetParameters Alive present 
PASS Drip/Drop Alive = Particles.LandAge <= (User.bWater ? 0.6 : 0.3) && Particles.Age < Part Particles.LandAge <= (User.bWater ? 0.6 : 0.3) && Particles.Age < Particles.Lifetime
PASS NS_LB_Drip/Drop renderer count 3 3
PASS NS_LB_Drip/Drop renderer 0 is sprite sprite
PASS NS_LB_Drip/Drop renderer 0 material MI_LB_Rain /Game/LastBell/Materials/Instances/FX/MI_LB_Rain.MI_LB_Rain
PASS NS_LB_Drip/Drop renderer 0 Alignment = VelocityAligned VelocityAligned
PASS NS_LB_Drip/Drop renderer 0 RendererVisibility = 0 0
PASS NS_LB_Drip/Drop renderer 0 RendererVisibilityTagBinding -> Particles.VisibilityTag Particles.VisibilityTag ExplicitParticles exists=True
PASS NS_LB_Drip/Drop renderer 1 is sprite sprite
PASS NS_LB_Drip/Drop renderer 1 material MI_LB_Splash /Game/LastBell/Materials/Instances/FX/MI_LB_Splash.MI_LB_Splash
PASS NS_LB_Drip/Drop renderer 1 Alignment = Unaligned Unaligned
PASS NS_LB_Drip/Drop renderer 1 FacingMode = FaceCamera FaceCamera
PASS NS_LB_Drip/Drop renderer 1 SubImageSize = {'x': 4, 'y': 4} {'x': 4, 'y': 4}
PASS NS_LB_Drip/Drop renderer 1 RendererVisibility = 1 1
PASS NS_LB_Drip/Drop renderer 1 RendererVisibilityTagBinding -> Particles.VisibilityTag Particles.VisibilityTag ExplicitParticles exists=True
PASS NS_LB_Drip/Drop renderer 1 ColorBinding -> Particles.CrownColor Particles.CrownColor ExplicitParticles exists=True
PASS NS_LB_Drip/Drop renderer 1 SpriteSizeBinding -> Particles.CrownSize Particles.CrownSize ExplicitParticles exists=True
PASS NS_LB_Drip/Drop renderer 1 SubImageIndexBinding -> Particles.SubImageIndex Particles.SubImageIndex ExplicitParticles exists=True
PASS NS_LB_Drip/Drop renderer 2 is sprite sprite
PASS NS_LB_Drip/Drop renderer 2 material MI_LB_Ripple /Game/LastBell/Materials/Instances/FX/MI_LB_Ripple.MI_LB_Ripple
PASS NS_LB_Drip/Drop renderer 2 Alignment = Unaligned Unaligned
PASS NS_LB_Drip/Drop renderer 2 FacingMode = CustomFacingVector CustomFacingVector
PASS NS_LB_Drip/Drop renderer 2 RendererVisibility = 1 1
PASS NS_LB_Drip/Drop renderer 2 RendererVisibilityTagBinding -> Particles.VisibilityTag Particles.VisibilityTag ExplicitParticles exists=True
PASS NS_LB_Drip/Drop renderer 2 SpriteFacingBinding -> Particles.SpriteFacing Particles.SpriteFacing ExplicitParticles exists=True
PASS NS_LB_Drip/Drop renderer 2 SpriteSizeBinding -> Particles.RingSize Particles.RingSize ExplicitParticles exists=True
PASS NS_LB_Drip/Drop renderer 2 ColorBinding -> Particles.RingColor Particles.RingColor ExplicitParticles exists=True
PASS Drip no SpawnRate; one burst per loop ['EmitterState', 'SpawnBurst_Instantaneous']
PASS Drip burst of 1 drop per loop 1
PASS Drip emitter loops forever Infinite
PASS Drip loop duration = RandomRangeFloat RandomRangeFloat
PASS Drip loop duration min = User.Interval.x User.Interval.x
PASS Drip loop duration max = User.Interval.y User.Interval.y
PASS Drip interval re-rolled every loop True
PASS Drip random first delay on True
PASS Drip delay applies to the first loop only True
PASS Drip first delay max = User.Interval.y User.Interval.y
PASS Drip spawns at the system origin (no ShapeLocation / AddVelocity) ['InitializeParticle', 'SetVariables_FFEF25534E6FCE3DD4147AA89DAE095F']
== NS_LB_EaveDrips check ==
PASS NS_LB_EaveDrips exists 
PASS NS_LB_EaveDrips in /Game/LastBell/FX/Niagara 
PASS NS_LB_EaveDrips user variable count 3 (want 3): ['User.FallHeight', 'User.LineLength', 'User.bWater']
PASS NS_LB_EaveDrips User.LineLength NiagaraFloat default 400
PASS NS_LB_EaveDrips User.FallHeight NiagaraFloat default 500
PASS NS_LB_EaveDrips User.bWater NiagaraBool default False
PASS NS_LB_EaveDrips emitters Drops ['Drops']
PASS NS_LB_EaveDrips compile aggregate UpToDate aggregate=UpToDate errors=False stale=False
PASS NS_LB_EaveDrips every script UpToDate 4 scripts
PASS NS_LB_EaveDrips/Drops has spawn and update scripts ['ParticleSpawnScriptInterpolated', 'ParticleUpdateScript']
PASS NS_LB_EaveDrips stack issues: 0 errors errors=0 warnings=0 infos=2
PASS NS_LB_EaveDrips/Drops SimTarget CPUSim CPUSim
PASS NS_LB_EaveDrips/Drops local space True 
PASS NS_LB_EaveDrips/Drops dynamic bounds Dynamic
PASS NS_LB_EaveDrips falling drop size (0.5, 5) cm (0.5, 5)
PASS EaveDrips/Drops SetParameters Landed+LandAge+SpriteFacing+VisibilityTag+CrownColor+CrownSize+RingColor+RingSize present 
PASS EaveDrips/Drops Landed literal {'value': 0}
PASS EaveDrips/Drops LandAge literal {'value': 0}
PASS EaveDrips/Drops SpriteFacing literal {'x': 0, 'y': 0, 'z': 1}
PASS EaveDrips/Drops VisibilityTag literal {'value': 0}
PASS EaveDrips/Drops CrownColor literal {'r': 0, 'g': 0, 'b': 0, 'a': 0}
PASS EaveDrips/Drops CrownSize literal {'x': 6, 'y': 6}
PASS EaveDrips/Drops RingColor literal {'r': 0, 'g': 0, 'b': 0, 'a': 0}
PASS EaveDrips/Drops RingSize literal {'x': 2, 'y': 2}
PASS NS_LB_EaveDrips gravity -980 (0, 0, -980)
PASS NS_LB_EaveDrips gravity before SolveForcesAndVelocity, 3 + 5 chain modules 8
PASS EaveDrips/Drops chain order Landed/Position/LandAge/VisibilityTag/Alive positions [3, 4, 5, 6, 7] of 8 modules
PASS EaveDrips/Drops SetParameters Landed present 
PASS EaveDrips/Drops Landed = Particles.Landed || Particles.Position.z <= -User.FallHeight Particles.Landed || Particles.Position.z <= -User.FallHeight
PASS EaveDrips/Drops SetParameters Position+Velocity present 
PASS EaveDrips/Drops Position = Particles.Landed ? float3(Particles.Position.x, Particles.Position.y,  Particles.Landed ? float3(Particles.Position.x, Particles.Position.y, -User.FallHeight) : Particles.Position
PASS EaveDrips/Drops Velocity = Particles.Landed ? float3(0.0, 0.0, 0.0) : Particles.Velocity Particles.Landed ? float3(0.0, 0.0, 0.0) : Particles.Velocity
PASS EaveDrips/Drops SetParameters LandAge present 
PASS EaveDrips/Drops LandAge = Particles.Landed ? Particles.LandAge + Engine.DeltaTime : 0.0 Particles.Landed ? Particles.LandAge + Engine.DeltaTime : 0.0
PASS EaveDrips/Drops SetParameters VisibilityTag+Color+CrownColor+SubImageIndex+RingColor+RingSize present 
PASS EaveDrips/Drops VisibilityTag = Particles.Landed ? 1 : 0 Particles.Landed ? 1 : 0
PASS EaveDrips/Drops Color = Particles.Landed ? float4(0.0, 0.0, 0.0, 0.0) : float4(1.0, 1.0, 1.0,  Particles.Landed ? float4(0.0, 0.0, 0.0, 0.0) : float4(1.0, 1.0, 1.0, 0.5)
PASS EaveDrips/Drops CrownColor = (Particles.Landed && Particles.LandAge <= 0.3) ? float4(1.0, 1.0, 1.0, (Particles.Landed && Particles.LandAge <= 0.3) ? float4(1.0, 1.0, 1.0, 1.0) : float4(0.0, 0.0, 0.0, 0.0)
PASS EaveDrips/Drops SubImageIndex = min(15.0, floor(Particles.LandAge / 0.3 * 16.0)) min(15.0, floor(Particles.LandAge / 0.3 * 16.0))
PASS EaveDrips/Drops RingColor = (Particles.Landed && User.bWater) ? float4(1.0, 1.0, 1.0, 0.6 * (1.0 - (Particles.Landed && User.bWater) ? float4(1.0, 1.0, 1.0, 0.6 * (1.0 - saturate(Particles.LandAge / 0.6))) : f
PASS EaveDrips/Drops RingSize = float2(1.0, 1.0) * lerp(2, 18, saturate(Particles.LandAge / 0.6)) float2(1.0, 1.0) * lerp(2, 18, saturate(Particles.LandAge / 0.6))
PASS EaveDrips/Drops SetParameters Alive present 
PASS EaveDrips/Drops Alive = Particles.LandAge <= (User.bWater ? 0.6 : 0.3) && Particles.Age < Part Particles.LandAge <= (User.bWater ? 0.6 : 0.3) && Particles.Age < Particles.Lifetime
PASS NS_LB_EaveDrips/Drops renderer count 3 3
PASS NS_LB_EaveDrips/Drops renderer 0 is sprite sprite
PASS NS_LB_EaveDrips/Drops renderer 0 material MI_LB_Rain /Game/LastBell/Materials/Instances/FX/MI_LB_Rain.MI_LB_Rain
PASS NS_LB_EaveDrips/Drops renderer 0 Alignment = VelocityAligned VelocityAligned
PASS NS_LB_EaveDrips/Drops renderer 0 RendererVisibility = 0 0
PASS NS_LB_EaveDrips/Drops renderer 0 RendererVisibilityTagBinding -> Particles.VisibilityTag Particles.VisibilityTag ExplicitParticles exists=True
PASS NS_LB_EaveDrips/Drops renderer 1 is sprite sprite
PASS NS_LB_EaveDrips/Drops renderer 1 material MI_LB_Splash /Game/LastBell/Materials/Instances/FX/MI_LB_Splash.MI_LB_Splash
PASS NS_LB_EaveDrips/Drops renderer 1 Alignment = Unaligned Unaligned
PASS NS_LB_EaveDrips/Drops renderer 1 FacingMode = FaceCamera FaceCamera
PASS NS_LB_EaveDrips/Drops renderer 1 SubImageSize = {'x': 4, 'y': 4} {'x': 4, 'y': 4}
PASS NS_LB_EaveDrips/Drops renderer 1 RendererVisibility = 1 1
PASS NS_LB_EaveDrips/Drops renderer 1 RendererVisibilityTagBinding -> Particles.VisibilityTag Particles.VisibilityTag ExplicitParticles exists=True
PASS NS_LB_EaveDrips/Drops renderer 1 ColorBinding -> Particles.CrownColor Particles.CrownColor ExplicitParticles exists=True
PASS NS_LB_EaveDrips/Drops renderer 1 SpriteSizeBinding -> Particles.CrownSize Particles.CrownSize ExplicitParticles exists=True
PASS NS_LB_EaveDrips/Drops renderer 1 SubImageIndexBinding -> Particles.SubImageIndex Particles.SubImageIndex ExplicitParticles exists=True
PASS NS_LB_EaveDrips/Drops renderer 2 is sprite sprite
PASS NS_LB_EaveDrips/Drops renderer 2 material MI_LB_Ripple /Game/LastBell/Materials/Instances/FX/MI_LB_Ripple.MI_LB_Ripple
PASS NS_LB_EaveDrips/Drops renderer 2 Alignment = Unaligned Unaligned
PASS NS_LB_EaveDrips/Drops renderer 2 FacingMode = CustomFacingVector CustomFacingVector
PASS NS_LB_EaveDrips/Drops renderer 2 RendererVisibility = 1 1
PASS NS_LB_EaveDrips/Drops renderer 2 RendererVisibilityTagBinding -> Particles.VisibilityTag Particles.VisibilityTag ExplicitParticles exists=True
PASS NS_LB_EaveDrips/Drops renderer 2 SpriteFacingBinding -> Particles.SpriteFacing Particles.SpriteFacing ExplicitParticles exists=True
PASS NS_LB_EaveDrips/Drops renderer 2 SpriteSizeBinding -> Particles.RingSize Particles.RingSize ExplicitParticles exists=True
PASS NS_LB_EaveDrips/Drops renderer 2 ColorBinding -> Particles.RingColor Particles.RingColor ExplicitParticles exists=True
PASS NS_LB_EaveDrips/Drops spawn rate = 6.0 6.0
PASS Eave drops along local X, length User.LineLength float3(User.LineLength, 0.1, 0.1)
PASS Eave line starts at the actor (offset = half length) float3(User.LineLength * 0.5, 0.0, 0.0)
INFO is_dirty /Game/LastBell/FX/Niagara/NS_LB_Rain False
INFO is_dirty /Game/LastBell/FX/Niagara/NS_LB_StrikeSparks False
INFO is_dirty /Game/LastBell/FX/Niagara/NS_LB_TorchFire False
INFO is_dirty /Game/LastBell/FX/Niagara/NS_LB_ShaftDust False
INFO is_dirty /Game/LastBell/FX/Niagara/NS_LB_WaterMist False
INFO is_dirty /Game/LastBell/FX/Niagara/NS_LB_Drip False
INFO is_dirty /Game/LastBell/FX/Niagara/NS_LB_EaveDrips False
RESULT: 467 PASS, 0 FAIL
```
