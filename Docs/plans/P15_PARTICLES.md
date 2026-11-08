# Phase 15: particles, the storm's rain, bolts, flames, mist, dust and cloth

Branch `claude/phase-15-particles` (from `main` at 88debbd). Lead: Opus. Implementers: Sonnet with high effort (D-048). This file is the spec and the plan. Open values marked **F0** are filled in from the F0 survey before the task that needs them starts, the same way as in Phase 14.

## 0. Owner choices (2026-11-08)
| Topic | Choice |
|---|---|
| Rain | **Constant heavy rain** outdoors from the start: a downpour. It does not build with the story; the lightning and wind still do. |
| Lightning bolts | **Sky bolts plus tower strikes.** Most flashes draw a branching bolt in the clouds. The scripted strikes, at the first look at the tower and at the tower top, hit the top of the bell tower. |
| Flames | **Animated candles plus Niagara torches.** Candle flames get an animated flame material. Torches, the brazier and the fire pit move to Niagara fire with embers and smoke. |
| Cloth | **Wind-driven material:** static torn-cloth meshes that ripple and whip through a material driven by the storm wind. |
| Rain occlusion | **Approach A, with a spike first.** The rain follows the camera, and drops die where the distance fields put a roof. Falls back to C (a baked roof map), then B (rain boxes placed by hand). |
| Ripples | As rings where splashes land. Not in `M_LB_Surface`, which is never saved. |

Not in this phase: audio and thunder (Phase 16); the finale beat (Phase 17); scalability menus (Phase 18); any change to `M_LB_Surface`, to gameplay or to AI.

## 1. Outcome and acceptance
**What the player sees:**
- **Rain:** a constant downpour outdoors, leaning with the wind. It is bright for an instant in every flash ("rain sheets in lightning"), with distant rain curtains around the courtyard and the garth.
- **Splashes and ripple rings** on open ground and roofs near the player.
- **No rain under any roof.** It does come through the open sky and through any roof hole.
- **Drips** in the crypt, the belfry and along the eaves of the covered walks.
- **Bolts:** branching bolts in the clouds on most flashes, flickering with double and triple pulses. Scripted strikes hit the bell tower's top, with sparks.
- **Flames:** candle flames that flicker, sway and lick. Niagara fire on the torches, the brazier and the fire pit.
- **Dust and mist:** dust motes in the moonlight shafts that brighten with lightning. Low mist outdoors and over the crypt water.
- **Cloth:** torn cloth that whips in the belfry, the tower stair windows and the cloister arcade.

**Acceptance:**
1. The owner approves the viewpoint set and a storm run-through (P15-9).
2. **No rain inside.** In the occlusion viewpoints (section 10), no rain particle is visible under:
   - the covered walks' plank roofs;
   - the chapel nave;
   - the cloister walks;
   - the tower interior;
   - the crypt.

   Rain is visible through every roof opening the F0 survey lists.
3. **Performance** (section 11, at a matched story state):
   - GPU ≤ 16.6 ms at the six spots;
   - GPU added by Phase 15 within each spot's budget;
   - game thread added ≤ 0.3 ms, measured as `lb.StormFX.Enabled` 1 minus 0 in the same session.
4. **Tests:** the suite grows from 128 with the section 12 tests; everything passes on the real project build with the editor closed.
5. **Saving:** none of the never-save packages is saved. These are `M_LB_Surface` and the Blueprints `BP_SmallBell`, `BP_SequencePuzzle`, `BP_Inscription`, `BP_RitualMechanism`, `BP_Door_Base`, `BP_TagInteractable`, `BP_TagTrigger`, `BP_EndingTrigger`, `BP_Inspectable_Note`, `BP_Door_Base_Dungeon`, `BP_RitualMechanism_CryptWinch` and `BP_WardenApparition`. `DA_StormSettings` and `DA_StormFX` are never saved with a debug field other than −1.

## 2. Architecture (C++, gameplay-programmer, Unreal closed for the real build)
Folder `Source/LastBell/Storm/`. Composition, no hard asset references: the assets come through soft pointers in data assets (CLAUDE.md).

### 2.1 Changes to the storm (P14 code)
- **`LBStormTypes.h`:**
  - `FLBStormStrike` gets `UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Storm|Bolt") FName StrikeTargetTag;` Doc comment: "When set, every strike of this beat draws a bolt to the first actor carrying this actor tag; its flash direction points at it."
  - New `USTRUCT(BlueprintType) FLBLightningStrikeInfo`, fields (all `BlueprintReadOnly`):
    - `float Brightness`
    - `ELBFlashReason Reason`
    - `ELBFlashProfile Profile` (resolved, never Auto)
    - `FVector Direction` (unit vector toward the bright patch)
    - `bool bHasTarget`
    - `FVector TargetLocation`
- **`LBStormSubsystem.h/.cpp`:**
  - New delegate `DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLBLightningStrikeSignature, const FLBLightningStrikeInfo&, Info)` and `UPROPERTY(BlueprintAssignable) FLBLightningStrikeSignature OnLightningStrike;`. It is broadcast in `StartDueFlashes` **right after** `OnLightningFlash`, for the same flash.
  - **`OnLightningFlash` stays exactly as it is** (the Phase 16 thunder hook).
  - `FFlashInstance` gains `ELBFlashProfile Profile` (the resolved one) and `TWeakObjectPtr<AActor> Target`.
  - `QueueFlash(...)` gains a last parameter `AActor* Target = nullptr`.
  - `FireStrike` resolves `StrikeTargetTag` once per strike index: the first actor with that tag, via `TActorIterator<AActor>` in the subsystem's world, cached in a `TMap<int32, TWeakObjectPtr<AActor>>`. A tag set but not found logs one Warning per index.
  - With a target, the strike's flash direction is `(Target − Camera).GetSafeNormal()`, or `(Target − TargetXY at Z 0)` when there is no camera.
- **`LBStormSettings.h`:** `UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "FX") TSoftObjectPtr<ULBStormFXSettings> FXSettings;`. `FillPlanTagDefaults()` sets `StrikeTargetTag = "LB_StrikeTarget_Tower"` on the `State.Event.CourtyardEntered` and `State.Event.TowerTop` strikes. The asset is set by hand in P15-6.

### 2.2 New: `ULBStormFXSettings` (`LBStormFXSettings.h/.cpp`, `UPrimaryDataAsset`), asset `/Game/LastBell/Data/DA_StormFX`
Every value has the default listed here. Each value has its own `Category`, `ClampMin` and units.

| Field | Default | Meaning |
|---|---|---|
| `RainSystem` | soft `UNiagaraSystem` | `NS_LB_Rain` (section 6.1) |
| `StrikeSparksSystem` | soft `UNiagaraSystem` | `NS_LB_StrikeSparks` |
| `BoltMesh` | soft `UStaticMesh` | `SM_LB_FX_BoltCard` (section 7.2) |
| `BoltMaterial` | soft `UMaterialInterface` | `MI_LB_Bolt` |
| `bRain` | true | rain on or off |
| `RainSpawnRate` | 35000 /s | user param `User.RainRate` |
| `RainBoxHalfXY` | 1800 cm | user param `User.BoxHalf` |
| `RainSpawnHeight` | 2500 cm above the camera | user param `User.SpawnHeight` |
| `RainFallSpeed` | (1100, 1400) cm/s | `User.FallMin`, `User.FallMax` |
| `RainWindLean` | 500 cm/s | `User.Wind` = `WindDirection` × `WindStrength` × lean |
| `SplashRate` | 2500 /s | `User.SplashRate` |
| `SplashRadius` | 1200 cm | `User.SplashRadius` |
| `MistMinExposure` | 0.6 | `User.Mist` = smoothstep(min − 0.1, min + 0.1, `GetPlayerExposure()`), eased at 1 /s |
| `SkyBoltChance` | Ambient 0.6, Scripted 1.0, WardenReveal 0.5, Apparition 0.5, Debug 1.0 | `TMap<ELBFlashReason, float>`. A targeted strike always draws its bolt. |
| `SkyBoltDistance` | **F0** (inside the sky dome; default 60000 cm) | horizontal distance from the camera |
| `SkyBoltTopHeight` | 22000 cm above the camera | top of the bolt |
| `SkyBoltLength` | (16000, 26000) cm | random per bolt |
| `BoltAspect` | 0.35 | width ÷ length |
| `StrikeSkyHeight` | 12000 cm above the target | bolt start (plus `StrikeSkyOffset` × −Direction horizontally) |
| `StrikeSkyOffset` | 2500 cm | |
| `StrikeWidth` | 1400 cm | card width for a tower strike |
| `BoltAtlasCount` | 8 | cells in `T_LB_FX_Bolts` (4 × 2) |
| `BoltMaxSeconds` | 2.5 s | a bolt is hidden at flash end (F < 0.01 and not `IsFlashBusy` for this flash) or after this |
| `BoltPool` | 4 | bolt actors kept |
| `DebugBolt` | −1 | −1 none, 0 a sky bolt, 1 a tower strike, held while ≥ 0 (for captures, with `DebugFreezeFlash`). **Never saved other than −1.** |

### 2.3 New: `ULBStormFXSubsystem` (`LBStormFXSubsystem.h/.cpp`, `UTickableWorldSubsystem`, Game and PIE only)
- **Activation.**
  - `Initialize` calls `Collection.InitializeDependency<ULBStormSubsystem>()`.
  - Activation is lazy, in `Tick`. On the first tick where `ULBStormSubsystem::IsActive()` is true, it loads `Storm->GetSettings()->FXSettings`, then binds `OnLightningStrike`.
  - It is active only if the settings load **and** `lb.StormFX.Enabled` is 1. That CVar is non-shipping, default 1; in Shipping the subsystem is always enabled.
  - It deactivates when the storm deactivates or the CVar goes to 0: the rain component is destroyed and the bolts are hidden. `IsTickable()` is true while it is active or still waiting for the storm's first active tick. Once the world has begun play and the storm is still inactive after one tick, the FX subsystem stops ticking for good, as on `L_MainMenu` and the test maps.
- **Rain.**
  - One `UNiagaraComponent` from `RainSystem` (`UNiagaraFunctionLibrary::SpawnSystemAtLocation`, `bAutoDestroy` false, pooling none).
  - Every tick it moves to the camera location (`PlayerCameraManager`) and gets these user parameters: `User.RainRate`, `User.BoxHalf`, `User.SpawnHeight`, `User.FallMin`, `User.FallMax`, `User.Wind` (FVector), `User.SplashRate`, `User.SplashRadius` and `User.Mist`.
  - `bRain` false means zero rates.
- **Bolts.**
  - `ALBLightningBolt` (`LBLightningBolt.h/.cpp`): an actor whose root is a `UStaticMeshComponent`, with no collision, no shadows, and `bRenderCustomDepth` false. `SetBolt(FTransform, int32 AtlasIndex)` makes a dynamic material instance from `BoltMaterial` once and sets the scalar `AtlasIndex`.
  - The subsystem keeps a pool of `BoltPool` bolt actors.
  - **On `OnLightningStrike`:**
    - With `bHasTarget`, it places a strike bolt with `StrikeBoltTransform` and spawns `StrikeSparksSystem` at the target.
    - Otherwise it rolls `SkyBoltChance[Reason]` with its own `FRandomStream`, seeded from the storm settings' `RandomSeed`, and places a sky bolt with `SkyBoltTransform`.
  - The brightness is **not** written by C++. `M_LB_Bolt` reads `MPC_LB_Storm.LightningFlash`, so the bolt flickers with the pulses and is invisible at F = 0.
  - A bolt is hidden after its flash or after `BoltMaxSeconds`.
- **Console** (non-shipping, `LBConsoleCommands.cpp`):
  - `lb.StormFX.Enabled 0|1`;
  - `lb.StormFX.Bolt [0|1]`: 0 for a sky bolt, 1 for a tower strike, together with a debug flash.
- **`DebugBolt` ≥ 0** keeps one bolt shown every frame (captures).

### 2.4 New: `LBStormFXLogic` (pure functions, unit tested; `LBStormFXLogic.h/.cpp`)
- `FTransform SkyBoltTransform(const FVector& Camera, const FVector& Direction, float Distance, float TopHeight, float Length, float Aspect)`:
  - horizontal direction d = normalised (Direction.X, Direction.Y), or (1, 0) when that is zero;
  - top = Camera + d × Distance + (0, 0, TopHeight);
  - the card's local −Z runs down from the top;
  - yaw so the card faces the camera (its normal is the horizontal camera-to-bolt direction);
  - scale (Length × Aspect ÷ 100, 1, Length ÷ 100), for a 100 cm card mesh.
- `FTransform StrikeBoltTransform(const FVector& Start, const FVector& End, const FVector& Camera, float Width)`:
  - the card's up axis is Start − End and its length |Start − End|, pivot at the top (Start);
  - the card rotates around its axis to face the camera.
- `FVector RainWind(const FVector& WindDirection, float WindStrength, float Lean)` = WindDirection.GetSafeNormal2D() × WindStrength × Lean.
- `float MistAmount(float Exposure, float MinExposure)` = smoothstep(Min − 0.1, Min + 0.1, Exposure).
- `bool RollBolt(float Chance, float Roll)` = Roll < Chance.

### 2.5 Tests: see section 12.

## 3. Data (P15-6 sets these in the editor)
- `DA_StormFX` with the section 2.2 defaults; its asset fields point to the section 5–7 assets.
- `DA_StormSettings.FXSettings` → `DA_StormFX`.
- `DA_StormSettings.ScriptedStrikes`: `StrikeTargetTag = LB_StrikeTarget_Tower` on the `State.Event.CourtyardEntered` and `State.Event.TowerTop` entries. Nothing else changes; read back the whole array.
- **Strike target:** a `TargetPoint` labelled `FX_StrikeTarget_Tower`, actor tag `LB_StrikeTarget_Tower`, at the tower's highest point (**F0**: vertical traces put the top collision at Z 3540 near (12500, 2000); place it 20 cm above the traced top of the finial or roof apex).

## 4. Textures (technical-artist; procedural; no licensed art)
A script `Tools/textures/fx/make_fx_textures.py` (numpy + PIL, seeded, deterministic) writes PNGs to `SourceArt/FX/` (LFS). They are imported into `/Game/LastBell/FX/Textures/` with the listed settings.

| Texture | Size | Content | Import |
|---|---|---|---|
| `T_LB_FX_RainStreak` | 64 × 512 | soft vertical streak: Gaussian across, tapered at both ends, alpha only (white RGB) | TC_Default, sRGB off, alpha |
| `T_LB_FX_Splash` | 1024² | 4 × 4 SubUV frames of a crown splash: ring of 8–12 droplets rising and falling, frame 0 small → frame 15 faded | TC_Default, sRGB on, alpha |
| `T_LB_FX_Ripple` | 256² | one thin soft ring (radius 0.42, width 0.03) plus a faint inner ring; normal-like luminance | TC_Default, sRGB off, alpha |
| `T_LB_FX_Bolts` | 2048 × 1024 | 4 × 2 cells, one branching bolt each: a random-walk main channel from the top centre to the bottom, 2–5 branches, glow falloff; seeds 101–108 | TC_Default, sRGB on, alpha |
| `T_LB_FX_Noise` | 512² | tileable fbm Perlin, R = 4 octaves, G = an offset copy, B = Voronoi | TC_Masks, sRGB off |
| `T_LB_FX_SoftDot` | 64² | Gaussian dot | TC_Alpha |
| `T_LB_FX_MistPuff` | 256² | soft fbm blob, radial falloff | TC_Alpha |

Cloth textures: **asset-curator** finds one CC0 2K fabric (coarse linen or burlap: BaseColor, Normal GL or DX, Roughness) on ambientCG or Poly Haven through `3d-assets-local`. It confirms CC0 with `get_asset`, downloads it to `ExternalAssets/Incoming/<id>/`, adds a row to `Docs/ASSET_REGISTRY.md`, and imports it to `/Game/LastBell/FX/Textures/Cloth/` (normal map as TC_Normalmap).

## 5. Materials (technical-artist; `/Game/LastBell/Materials/FX/`, MIs in `/Game/LastBell/Materials/Instances/FX/`)
All the FX masters read `MPC_LB_Storm` where they say so. **Never `set_parent` an MI on screen** (MCP_NOTES storm item 1). New masters only, so `M_LB_Surface` is untouched.

| Master | Domain / blend / shading | Key graph | MIs |
|---|---|---|---|
| `M_LB_Rain` | Surface, Translucent, Unlit, `Apply Fogging` on, `Responsive AA` on | colour (0.55, 0.60, 0.70) × (`RainBase` 0.035 + `RainFlash` 1.4 × `LightningFlash`) × streak alpha × `ParticleColor`; depth fade 30 cm; camera fade 0→1 over 40–120 cm | `MI_LB_Rain` |
| `M_LB_Splash` | Translucent, Unlit | SubUV 4 × 4 crown, colour as rain, × (0.08 + 1.2 F) | `MI_LB_Splash` |
| `M_LB_Ripple` | Translucent, Unlit | `T_LB_FX_Ripple` × alpha over life, × (0.05 + 1.0 F); depth fade 4 cm | `MI_LB_Ripple` |
| `M_LB_Bolt` | Translucent, Unlit, additive, `Apply Fogging` off, two-sided, `Disable Depth Test` off | atlas cell from scalar `AtlasIndex` (4 × 2), colour `FlashTint` × `BoltGain` 40 × F (MPC `LightningFlash`, so the bolt flickers with the pulses and is 0 at rest) | `MI_LB_Bolt` |
| `M_LB_Flame` | Translucent, Unlit, additive | colour ramp over UV.y (core (1, 0.95, 0.8) → (1, 0.55, 0.15) → (0.6, 0.12, 0.02)), shape mask from UV, UV distortion by `T_LB_FX_Noise` panning up at `NoiseSpeed`; flicker: emissive × (0.85 + 0.3 × noise(time × `FlickerSpeed` + per-instance random)); static switch `bSprite` (radial mask for particles instead of the mesh UV); WPO sway for meshes: object-space height × 0.15 cm × sin | `MI_Flame_Candle` (calm: `NoiseSpeed` 0.6, `FlickerSpeed` 7, `EmissiveStrength` 8, `bSprite` false), `MI_Flame_Torch` (turbulent: 1.4, 11, 12, `bSprite` true) |
| `M_LB_DustMote` | Translucent, Unlit, additive | `T_LB_FX_SoftDot` × (0.55, 0.62, 0.80) × `DustBrightness` 0.6 × (1 + 2 F) × camera fade | `MI_LB_DustMote` |
| `M_LB_Mist` | Translucent, Unlit, depth fade 60 cm | `T_LB_FX_MistPuff` × (0.5, 0.55, 0.62) × (0.06 + 0.5 F) × opacity 0.08 | `MI_LB_Mist`, `MI_LB_WaterMist` |
| `M_LB_RainCurtain` | Translucent, Unlit, two-sided | `T_LB_FX_RainStreak` tiled 6 × 1, panning down 1.2 /s plus wind skew, × (0.02 + 1.6 F); fades out under 3000 cm from the camera | `MI_LB_RainCurtain` |
| `M_LB_Cloth` | Surface, Opaque, Default Lit, two-sided, `Max WPO Displacement` 60 | fabric textures × `Tint`; WPO = `MF_LB_ClothWave` | `MI_Cloth_Linen_Dark`, `MI_Cloth_Linen_Red` (an old faded red, (0.35, 0.08, 0.06)) |

**`MF_LB_ClothWave`** (`/Game/LastBell/Materials/Functions/`):
- **Inputs:** `AmplitudeCm` (35), `WavelengthCm` (120), `PhaseScale` (2.5), `WhipAmount` (0.25).
- **Pinning:** v = UV0.y (0 at the pinned top edge); pin = v^1.5.
- **Travelling wave:** φ = `WindPhase` × `PhaseScale` − (v × length ÷ `WavelengthCm`) × 2π, with length the mesh height (an input).
- **Offset:**
  - main = `WindDirection` × `WindStrength` × (0.6 + 0.4 sin φ) × pin × `AmplitudeCm`;
  - flap = `VertexNormalWS` × sin(3φ + world X × 0.01) × `WhipAmount` × `WindStrength` × pin × `AmplitudeCm`;
  - WPO = main + flap.
- **Neutral:** at `WindStrength` 0 the WPO is exactly 0.

Every `Sine` node has `period` 2π (MCP_NOTES storm item 6).

## 6. Niagara systems (lighting-vfx; `/Game/LastBell/FX/Niagara/`)
How to build them over MCP: MCP_NOTES "FX and fog" (`NiagaraToolset_System.CreateNiagaraSystem` from `/Niagara/DefaultAssets/DefaultSystem` with its Fountain emitter removed, `AddEmitter` from the templates, `GetSystemCompileState`, `GetStackIssues`). **The S1 spike decides how far MCP can go.** Anything it can't build is listed, and either a headless Unreal Python script builds it or it is simplified. The method is recorded in MCP_NOTES.

### 6.1 `NS_LB_Rain` (GPU sim, fixed bounds ±4000 cm, one system attached to the camera by the FX subsystem)
- **Emitter `Rain`.**
  - **Spawn:** rate `User.RainRate`, in a box with XY ±`User.BoxHalf` at Z = system Z + `User.SpawnHeight`, jittered ±200.
  - **Velocity and lifetime:** (0, 0, −rand(`User.FallMin`, `User.FallMax`)) + `User.Wind`; lifetime 3.5 s; drag 0.
  - **Collision:** module mode **Distance Field** (GPU), **kill on collision**. The particle dies where the distance field has a surface, so a roof stops it.
  - **Below the camera:** kill when Z < system Z − 800.
  - **Sprite:** velocity-aligned, material `MI_LB_Rain`, size (0.7, rand 28–42) cm, colour alpha 0.7.
- **Emitter `Splash`.**
  - **Spawn and fall:** rate `User.SplashRate` in a disc of radius `User.SplashRadius` around the system XY, at Z = system Z + `User.SpawnHeight`. Velocity (0, 0, −20000) cm/s, so the drop falls almost at once; Distance Field collision with restitution 0 and friction 1, so it **rests on the first surface**.
  - **Visibility:** alpha = 0 until `Collision.HasCollided` (the module's collided attribute), then 1.
  - **After landing:** the particle lives 0.45 s.
  - **Renderer 1:** a camera-facing crown sprite, `MI_LB_Splash`, SubUV over the post-collision age, size 6–10 cm.
  - **Renderer 2:** a flat ring with custom facing (0, 0, 1), `MI_LB_Ripple`, size 4 → 22 cm over the age, alpha 0.6 → 0.
  - **Fallback if the collided attribute can't be read over MCP:** a scratch-pad module that marches the global distance field down from the spawn point (24 steps, 0.5 × distance) and places the splash at the surface, also killing it if the march upward hits a surface first. This is the C approach in miniature.
- **Emitter `GroundMist`.**
  - **Spawn:** rate 5 × `User.Mist` /s, in a ring of radius 600–2200 cm around the camera, at Z = system Z − 120 ± 40.
  - **Motion and size:** lifetime 6 s, velocity `User.Wind` × 0.15, size 250–450 cm, rotation random.
  - **Appearance:** `MI_LB_Mist`, alpha 0 → 1 → 0 over life.

### 6.2 `NS_LB_StrikeSparks` (CPU, burst)
- One burst of 70 spark particles: sphere velocity 400–900 cm/s, gravity −980, lifetime 0.4–0.9 s, size 1–2.5 cm.
- Velocity-aligned sprites using `MI_Flame_Torch`, with colour (1, 0.9, 0.7) × 6.
- A light renderer on 5 % of the particles (radius 400, intensity × 20) for a brief glow.
- The system destroys itself after 1.5 s.

### 6.3 `NS_LB_TorchFire` (CPU; one per torch, brazier or fire pit; `User.Scale` 1 for a torch, 1.8 for the brazier, 2.2 for the fire pit)
| Emitter | Spawn | Life | Size | Motion | Material |
|---|---|---|---|---|---|
| `Flames` | 14 /s × Scale | 0.5–0.8 s | 18–30 cm × Scale | up 60 cm/s, curl noise 30 | `MI_Flame_Torch` (sprite), alpha 1 → 0 |
| `Embers` | 6 /s | 1–2 s | 0.8–1.5 cm | up 80 cm/s + curl noise 60 + `User.Wind` × 0.2 | `MI_Flame_Torch`, colour (1, 0.45, 0.1) × 4 |
| `Smoke` | 3 /s | 3–4 s | 30 → 120 cm | up 40 cm/s | `MI_LB_Mist`, colour (0.08, 0.08, 0.08), alpha 0.1 |

It replaces the Cascade `PS_Fire_00` and `PS_Fire_01` components on the fire actors listed by F0 (crypt torches T1–T3, `L_Crypt_Brazier`, the courtyard fire pit and the courtyard work-area torch). The point lights and their light functions stay.

### 6.4 `NS_LB_ShaftDust` (GPU; one per moonlight shaft)
- **User parameters:** `User.BoxExtent` (FVector) and `User.Count` (default 120).
- **Spawn:** keep `User.Count` alive (spawn rate count ÷ 10 /s), in an oriented box set by the system transform and `User.BoxExtent`.
- **Motion:** lifetime 8–12 s, curl-noise velocity 3–6 cm/s.
- **Appearance:** size 0.3–0.8 cm, `MI_LB_DustMote`, alpha 0 → 1 → 0.
- **Placed in:** every chapel, crypt and tower shaft (section 8 table).

### 6.5 `NS_LB_WaterMist` (CPU; one per crypt water plane)
- `User.Extent` (FVector2D).
- Spawn 4 /s over the plane, at Z 0–60 cm above it.
- Lifetime 6 s, size 150–300 cm, drift 5 cm/s.
- `MI_LB_WaterMist`, alpha 0 → 0.6 → 0.

### 6.6 `NS_LB_Drip` and `NS_LB_EaveDrips` (CPU)
- **`NS_LB_Drip`** (one drip point):
  - **Inputs:** `User.FallHeight` cm (F0), `User.Interval` (1.5, 4) s, `User.bWater`.
  - **The drop:** spawned at the system origin, falls under gravity.
  - **The splash:** when its Z ≤ origin − `FallHeight`, an event spawns a 6-droplet splash burst (`MI_LB_Splash`, 0.3 s), plus a ripple ring (`MI_LB_Ripple`, 2 → 18 cm) when `User.bWater`.
- **`NS_LB_EaveDrips`:** the same, spawned along a line of `User.LineLength` cm (local X) at 6 /s, with the drops falling `User.FallHeight`. This is the edge of a covered walk roof.

### 6.7 Distant rain curtains (static meshes, not Niagara)
- A plane `SM_LB_FX_CurtainCard` (a 100 × 100 cm card, pivot at the bottom centre, from Blender), with `MI_LB_RainCurtain`.
- 8 cards are placed in the level (section 8): 3000 cm wide, 2500 cm tall, outside the courtyard walls and the garth.
- No collision, no shadows.

## 7. Meshes (technical-artist, headless Blender, `Tools/blender/fx/build_fx_meshes.py`; FBX to `SourceArt/FX/`, imported to `/Game/LastBell/FX/Meshes/`)
### 7.1 Cloth (two-sided single sheet; UV0 V = 0 at the pinned top edge; pivot at the top centre; no collision; Nanite off, since WPO cloth on Nanite is not needed)
| Mesh | Size (W × H cm) | Grid | Shape |
|---|---|---|---|
| `SM_LB_Prop_ClothStrip_A` | 35 × 220 | 8 × 44 | torn jagged bottom (seeded) |
| `SM_LB_Prop_ClothStrip_B` | 25 × 160 | 6 × 32 | torn bottom, one hole |
| `SM_LB_Prop_ClothBanner_A` | 110 × 240 | 22 × 48 | ragged bottom, one side tear |
| `SM_LB_Prop_ClothSheet_A` | 170 × 140 | 34 × 28 | ragged bottom and corner |

- A mild baked fold: a sine in Y, 3 cm.
- The MIs set `AmplitudeCm` per mesh: strips 30, banner 25, sheet 20.
- Renders: `Docs/ArtTest/fx/p15_cloth_*.png`.

### 7.2 FX cards
- `SM_LB_FX_BoltCard`: a 100 × 100 cm plane in XZ, pivot at the top centre, extending −Z, normal +Y.
- `SM_LB_FX_CurtainCard`: a 100 × 100 cm plane, pivot at the bottom centre.

## 8. Level work (lighting-vfx [EDITOR], P15-6; `L_Monastery` saved once at the end after a census)
A script `Tools/fx/p15_level.py --apply/--check` (idempotent; finds actors by exact label; never saves), in the style of `p14_3_level.py`. All new actors go in the folder `FX/Storm`.

| What | Actors | Values |
|---|---|---|
| Strike target | `FX_StrikeTarget_Tower` | section 3, **F0** Z |
| Shaft dust | `FX_Dust_<shaft>` for `Ch_Shaft_S1/S2/S3/_Roof`, the crypt shafts and the tower slit shafts (**F0** list) | the transform and `User.BoxExtent` match each shaft card's beam (**F0**); `User.Count` 120 (chapel), 80 (crypt and tower) |
| Water mist | `FX_WaterMist_W/E` | over `MI_Crypt_Water_Flood_W/E` planes (**F0** bounds) |
| Drips | `FX_Drip_*`: crypt 8 points (5 over water), belfry 2 | **F0** points and fall heights |
| Eave drips | `FX_EaveDrips_N` at the courtyard north walk eave (X 2000…3000, Y 1300, Z 420), `FX_EaveDrips_S` at the south walk (X 4000…5000, Y −1350, Z 420), plus the cloister walk eaves (**F0**) | `User.LineLength` per eave, `User.FallHeight` = eave Z − ground Z |
| Torches | replace the Cascade component on each **F0** fire actor with `NS_LB_TorchFire` (same transform, `User.Scale` per section 6.3) | if a fire is inside a never-save Blueprint, leave it and list it |
| Candle flames | swap the material on the **F0** flame meshes (`SM_LB_Prop_CandleFlame_A` users, `CD_Candles_*_Flame`, puzzle-candle flames) to `MI_Flame_Candle` | through the placed actor's material override only; never a never-save Blueprint |
| Cloth | 10 pieces: belfry openings 4, tower stair windows 2, cloister arcade 3, gatehouse arch 1 | **F0** transforms (top edge flush under the hanging point, ±2 cm); WPO disable distance 4000 |
| Rain curtains | 8 `FX_RainCurtain_*` | **F0**: outside the courtyard walls and the garth, facing in, 3000 × 2500 cm, bottom at ground Z − 200 |

Then:
- the census (start + the number of new actors);
- `--check` all PASS;
- one save;
- the suite.

## 9. Look session (owner + lead, P15-7, about 30 minutes)
Live in Play, with the lead changing `DA_StormFX` and MI parameters in memory over MCP:
1. Rain density and lean: `RainSpawnRate` 25k, 35k or 50k; `RainWindLean`.
2. Rain brightness at rest and in a flash: `RainBase`, `RainFlash`.
3. Splash and ripple size and rate.
4. Sky bolt frequency: `SkyBoltChance` Ambient 0.3, 0.6 or 0.9. The bolt size and distance.
5. A tower strike: `lb.StormFX.Bolt 1`.
6. Flames: the candle calm against the torch turbulence.
7. Cloth amplitude.
8. Dust and mist strength.

The values chosen are saved in P15-8.

## 10. Viewpoints (owner approval, P15-9)
- **The 16 poses of `Tools/lighting/poses/p14_viewpoints.json`**, at rest with `DebugFreezeFlash` 0.
- **Plus the storm moments at flash 0.8 with `DebugBolt`:**
  - `p14_cy_tower_reveal` with a tower strike;
  - `cy_west_front_15m` with a sky bolt;
  - `cl_tall_north_15m` with a sky bolt.
- **Plus the occlusion poses** (new file `Tools/fx/poses/p15_rain.json`, **F0** coordinates):
  - under the courtyard north walk roof looking out;
  - the chapel nave looking up at the roof;
  - the cloister walk looking into the garth;
  - every cloister and chapel roof opening;
  - the tower stair at a window;
  - the belfry looking out;
  - the crypt ossuary.

The rain checks are by eye and by a difference test: at a roofed spot, a capture with rain against one with `bRain` off. The mean absolute difference must be ≤ 1/255 inside the roofed part of the frame.

Then the storm run-through in Play (as in P14-6).

## 11. Performance (owner readings, P15-10)
- **The six spots of P14 section 11** (`BugItGo` lines) at a **matched story state**: a fresh Play with no state tags, all readings in one session.
- **Two readings per spot:** `lb.StormFX.Enabled 1` and `0`, each after 30 s of settle, with `stat unit` and `stat gpu`.
- **Pass:**
  - GPU ≤ 16.6 ms;
  - the GPU added (1 minus 0) within the spot's budget: courtyard ≤ 1.8, cloister ≤ 1.5, belfry ≤ 1.5, chapel ≤ 0.8, ossuary ≤ 0.8, mid-stair ≤ 0.8 ms;
  - the game thread added ≤ 0.3 ms.
- **If a spot fails, go down this ladder, re-measuring after each step:**
  1. `RainSpawnRate` −30 %;
  2. `SplashRate` −50 %;
  3. `RainBoxHalfXY` 1800 → 1400;
  4. the `GroundMist` emitter off;
  5. dust counts halved;
  6. torch smoke off.

## 12. Tests (gameplay-programmer, P15-1; `Source/LastBellTests/Tests/LBStormFXTests.cpp` and `LBStormFXFunctionalTests.cpp`)
- **Unit tests:**
  - `LastBell.StormFX.Logic.SkyBoltTransform`: the top position, facing the camera, the scale.
  - `.StrikeBoltTransform`: the card spans Start → End within 1 cm and faces the camera.
  - `.RainWind`
  - `.MistAmount`
  - `.RollBolt`
- **Functional tests** (PIE, test map with a spawned tagged moon, as the P14 tests do):
  - `LastBell.Functional.StormFX.ActivatesWithStorm`: active with the storm, inactive without it.
  - `.RainFollowsCamera`: the rain component is within 1 cm of the camera after a tick.
  - `.TargetedStrikeDrawsBoltToTarget`: a strike with a `StrikeTargetTag` actor puts a visible bolt whose bottom is within 5 cm of the target, and `OnLightningStrike` carries the target.
  - `.SkyBoltOnAmbientFlash`: with chance 1.
  - `.BoltHidesAfterFlash`
  - `.DisabledByCVar`
  - `.StrikeInfoMatchesFlash`: `OnLightningFlash` and `OnLightningStrike` fire together, and the brightness and reason are equal.
  - `.Monastery.FXSetup`, on the real level:
    - `DA_StormFX` is linked and loads;
    - `FX_StrikeTarget_Tower` is unique;
    - both target strikes resolve;
    - the rain component exists after BeginPlay;
    - both debug fields are −1.
- **The existing 128 still pass.** The P14 storm tests must not change behaviour, since `OnLightningFlash` is untouched.

## 13. Tasks
| Task | Scope | Owner | Needs | Depends on |
|---|---|---|---|---|
| P15-0 | Plan approval; D-103 (scope and owner choices), D-104 (rain occlusion A, fallbacks C, B), D-105 (FX subsystem); R-65…R-69; `IMPLEMENTATION_PLAN.md` Phase 15 table | lead + owner | — | — |
| F0 | Read-only survey. **Flames:** every flame mesh and its material, and whether a never-save Blueprint owns it. **Fire actors:** their Cascade components and transforms. **Roofs:** thin roofs, their thickness, and every roof opening with its bounds. **Tower:** the top (traces). **Shafts:** actors and beam boxes. **Crypt water:** plane bounds. **Ceilings:** heights for the drips. **Eaves:** the cloister walk eaves. **Cloth:** hanging points. **Curtains:** spots. **Sky:** the dome radius, for `SkyBoltDistance`. **MCP:** the Niagara toolset tool list (`describe_toolset`). **GDF:** whether the global distance field is built with this project's settings. Output: `Docs/ArtTest/fx/p15_f0.json` + `p15_f0_tables.md`; this plan's F0 values are filled from it. | lead [EDITOR read-only] | Unreal open | P15-0 |
| S1 | **Rain occlusion spike.** A minimal `NS_LB_Rain_Spike` (GPU sprites, distance-field collision kill, splash rest test), built over MCP, placed by hand at: the courtyard north walk; the chapel nave; a cloister walk; a cloister roof opening (F0); the tower stair. Captures from below and outside (owner present). **Verdict:** does A stop rain under every roof, including the 4 cm planks? Can MCP build the emitters (collision mode, attribute read, two renderers, scratch pad)? If thin roofs leak: test hidden **rain-blocker** boxes under them (`bRenderInMainPass` off, still in the distance field); then the C fallback. The spike assets are deleted afterwards, and the verdict goes into this plan before P15-4. | lighting-vfx [EDITOR]; captures by the lead with the owner | Unreal open | F0 |
| P15-1 | Sections 2 and 12: code, console commands, tests | gameplay-programmer | **Unreal closed** for the real build | P15-0 |
| P15-2 | Section 4: textures; the cloth fabric (asset-curator) | technical-artist + asset-curator | — (import: Unreal open) | P15-0 |
| P15-3 | Section 7: Blender meshes and import | technical-artist | Blender headless; import with Unreal open | P15-0 |
| P15-4 | Section 5: materials and MIs | technical-artist [EDITOR] | | P15-2 |
| P15-5 | Section 6: Niagara systems (per the S1 verdict) | lighting-vfx [EDITOR] | | S1, P15-4 |
| P15-6 | Sections 3 and 8: data assets and level work | lighting-vfx [EDITOR] | | P15-1, P15-3, P15-5 |
| P15-7 | Look session (section 9) | lead + **owner** | Unreal in front | P15-6 |
| P15-8 | Apply the choices, save | lighting-vfx [EDITOR] | | P15-7 |
| P15-9 | Viewpoints, occlusion checks, run-through (section 10) | lead + **owner** | Unreal in front | P15-8 |
| P15-10 | Performance (section 11) | **owner** + performance-engineer | | P15-9 |
| P15-11 | QA, docs (TECHNICAL_DESIGN "Particles", MCP_NOTES, PERFORMANCE_BUDGET, RISKS, ASSET_REGISTRY), the full suite with the editor closed; "PHASE 15 READY FOR YOUR REVIEW" | qa-reviewer, docs agent, lead | Unreal closed for the suite | all |

One editor agent at a time. Each agent commits on this branch only, stages by path, and never switches, merges or pushes. Captures are run only by the lead with the owner present (`capture_session.py`, `--fg-wait 180`).

## 14. Risks (added to `RISKS.md` at P15-0)
| Id | Risk | Mitigation |
|---|---|---|
| R-65 | MCP can't build the Niagara emitters this needs (collision mode, attribute reads, a second renderer, scratch pads) | S1 tests it first; a headless Python Niagara script; otherwise simplify the effect and record it |
| R-66 | Thin roofs (4 cm planks) are missing from the global distance field, so rain leaks under them | S1; hidden rain-blocker boxes in the distance field; fallback C (baked roof map) |
| R-67 | Rain overdraw costs GPU; the chapel and the cloister have the least headroom | Thin sprites, a distance fade, the section 11 ladder; rain is outdoors only |
| R-68 | A candle flame or a fire lives inside a never-save Blueprint | F0 finds it; change only the placed instance's material override or the MI; otherwise leave it and list it |
| R-69 | The global distance field update for Niagara collision costs GPU with hardware-ray-traced Lumen | Measured in S1 and P15-10; fallback C needs no distance field |

## 15. Not in this phase
- Thunder and all audio (Phase 16; `OnLightningFlash` and `OnLightningStrike` are the hooks).
- The finale's bell and strike beat (Phase 17).
- Water surface rain ripples inside `M_LB_Surface` puddles (it is never saved).
- Chaos cloth.
- Rain droplets on the camera lens.
- Wet footprints.
- Any change to gameplay, AI or audio.

## Results
