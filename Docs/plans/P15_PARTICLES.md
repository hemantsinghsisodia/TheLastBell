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

   Rain is visible through every roof opening the F0 survey lists (Results, F0.3): the chapel roof hole, the cloister north roof-and-vault hole, the tower's south-west roof collapse into the belfry, and the uncovered parts of the two courtyard walks. "Under the plank roofs" means directly under a plank. The planks cover 40 % of the north walk and 28 % of the south walk, so rain falls through the rest by design.
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
| `SkyBoltDistance` | 60000 cm (F0.5: the sky dome radius is 1,638,400 cm, so the 60000 cap applies) | horizontal distance from the camera |
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
  - Every tick it moves to the camera location (`PlayerCameraManager`). In a world with no player camera manager (PIE Simulate, which the capture tool uses), it follows `GetWorld()->ViewLocationsRenderedLastFrame[0]` when that array isn't empty, and otherwise stays put. This is a public `UWorld` member, so the runtime module needs no editor dependency, and the P15-9 captures get rain. It also gets these user parameters: `User.RainRate`, `User.BoxHalf`, `User.SpawnHeight`, `User.FallMin`, `User.FallMax`, `User.Wind` (FVector), `User.SplashRate`, `User.SplashRadius` and `User.Mist`.
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
- **Strike target:** a `TargetPoint` labelled `FX_StrikeTarget_Tower`, actor tag `LB_StrikeTarget_Tower`, at the tower's highest point: **(12530.8, 2000, 4844.8)** (F0.4). That is 20 cm above the finial tip of `TWA_Roof` (bounds max Z 4824.8). The roof has no collision, so traces only reach the 3540 wall top. The tip X comes from the finial's 20° bend; P15-6 checks it by eye and moves the point within ±15 cm.

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
| `M_LB_Flame` | Translucent, Unlit, additive | colour ramp over UV.y (core (1, 0.95, 0.8) → (1, 0.55, 0.15) → (0.6, 0.12, 0.02)), shape mask from UV, UV distortion by `T_LB_FX_Noise` panning up at `NoiseSpeed`; flicker: emissive × (0.85 + 0.3 × noise(time × `FlickerSpeed` + per-instance random)); static switch `bSprite` (radial mask for particles instead of the mesh UV); WPO sway for meshes: object-space height × 0.15 cm × sin. **Mesh mode (P15-4 note):** `SM_LB_Prop_CandleFlame_A` is a lathed 3 × 3 × 6.5 cm teardrop (`build_props.py` `build_candle_flame`), so the shape is the geometry: the ramp uses the normalised local height h = (LocalPosition.z − ObjectLocalBounds.min.z) ÷ bounds size z, not UV; the edges are softened by emissive × (1 − Fresnel(exponent 2) × 0.7); the noise distortion offsets h | `MI_Flame_Candle` (calm: `NoiseSpeed` 0.6, `FlickerSpeed` 7, `EmissiveStrength` 8, `bSprite` false), `MI_Flame_Torch` (turbulent: 1.4, 11, 12, `bSprite` true) |
| `M_LB_DustMote` | Translucent, Unlit, additive | `T_LB_FX_SoftDot` × (0.55, 0.62, 0.80) × `DustBrightness` 0.6 × (1 + 2 F) × camera fade | `MI_LB_DustMote` |
| `M_LB_Mist` | Translucent, Unlit, depth fade 60 cm | `T_LB_FX_MistPuff` × (0.5, 0.55, 0.62) × (0.06 + 0.5 F) × opacity 0.08 | `MI_LB_Mist`, `MI_LB_WaterMist` |
| `M_LB_RainCurtain` | Translucent, Unlit, two-sided | `T_LB_FX_RainStreak` tiled 6 × 1, panning down 1.2 /s plus wind skew, × (0.02 + 1.6 F); fades out under 3000 cm from the camera | `MI_LB_RainCurtain` |
| `M_LB_Cloth` | Surface, Opaque, Default Lit, two-sided, `Max WPO Displacement` 60 | fabric textures × `Tint`; WPO = `MF_LB_ClothWave` | `MI_Cloth_Linen_Dark` (strips, `AmplitudeCm` 30), `MI_Cloth_Linen_Dark_Sheet` (the sheet, 20), `MI_Cloth_Linen_Red` (the banners, 25; an old faded red, (0.35, 0.08, 0.06)) |

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
  - **Collision:** the placed module's static switch `GPU Collision Type` = "GPU Distance Fields" (S1), **kill on collision**, `Radius Calculation Type` Custom with `Particle Radius` 20 cm (S1 round 2). The particle dies where the distance field has a surface, so a roof stops it. The build recipe (tool calls and payloads) is `Docs/ArtTest/fx/s1/s1_build.md`.
  - **Below the camera:** kill when Z < system Z − 800.
  - **Sprite:** velocity-aligned, material `MI_LB_Rain`, size (0.7, rand 28–42) cm, colour alpha 0.7.
- **Emitter `Splash`.**
  - **Spawn and fall (S1 round 2):**
    - rate `User.SplashRate`, spawned in a disc of radius `User.SplashRadius` around the system XY, at Z = system Z + `User.SpawnHeight`;
    - it falls at the rain speed, rand(`User.FallMin`, `User.FallMax`). The planned 20000 cm/s tunnelled through the 20 cm chapel slab in S1;
    - collision as for `Rain`, with kill on collision **off**.
  - **Pin at first contact.** These modules run after `Collision` and `Solve Forces and Velocity`, in this order, each its own SetParameters module:
    1. `LandPos` = `Landed ? LandPos : Position`;
    2. `Landed` = `Landed || HasCollided`;
    3. `Position` = `Landed ? LandPos : Position`, and `Velocity` = `Landed ? 0 : Velocity`;
    4. `LandAge` = `Landed ? LandAge + Engine.DeltaTime : 0`;
    5. the colour and alpha (0 until `Landed`);
    6. `DataInstance.Alive` = `LandAge <= 0.45`.

    In S1 round 1, splashes left to rest slid off the sloped roofs and fell through. The pin fixed this (0 splash pixels under any roof).
  - **Renderer 1:** a camera-facing crown sprite, `MI_LB_Splash`, SubUV driven by `LandAge` ÷ 0.45, size 6–10 cm.
  - **Renderer 2:** a flat ring with custom facing (0, 0, 1), `MI_LB_Ripple`, size 4 → 22 cm and alpha 0.6 → 0 over `LandAge`. Bind `spriteSizeBinding` and `spriteFacingBinding` to particle attributes (S1 Q5: works).
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

It replaces the five Cascade `Emitter` actors listed in F0.2: `FX_Torch_Fire`, `FX_Crypt_Torch_T1/T2/T3` and `FX_Crypt_Brazier`. The courtyard fire pit has no Cascade fire (only `FX_FirePit_Smoke`, a Niagara smoke wisp), so it gets a new one. The point lights, their light functions and the smoke wisp stay. Placement is in F0.2.

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
  - **Inputs:** `User.FallHeight` cm (F0.8), `User.Interval` (1.5, 4) s, `User.bWater`.
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
| Strike target | `FX_StrikeTarget_Tower` | section 3: (12530.8, 2000, 4844.8) |
| Shaft dust | `FX_Dust_<shaft>`, 11 actors (F0.6) | the F0.6 box: actor location = centre, rotation = box rotation, `User.BoxExtent` = half-extent; `User.Count` 120 (chapel), 80 (crypt and tower) |
| Water mist | `FX_WaterMist_W/E` | F0.7 |
| Drips | `FX_Drip_<tag>`: crypt 8 points (5 over water), belfry 2 | F0.8 points, `User.FallHeight` and `User.bWater` |
| Eave drips | `FX_EaveDrips_<id>`, 6 lines | F0.9 (start point, yaw, `User.LineLength`, `User.FallHeight`) |
| Torches | `NS_LB_TorchFire` actors in place of the five Cascade actors, plus one new at the fire pit | F0.2 |
| Candle flames | slot-0 material override `MI_Flame_Candle` on the 22 flame actors; the Blueprint flames per F0.1 | F0.1; never a never-save Blueprint |
| Cloth | 10 pieces: belfry openings 4, tower stair windows 2, cloister arcade 3, gatehouse arch 1 | F0.10 transforms (pivot = top centre); WPO disable distance 4000; P15-6 checks the arcade top edges by eye (±15 cm) |
| Rain curtains | 8 `FX_RainCurtain_<id>` | F0.11 |

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
- **Plus the occlusion poses** in `Tools/fx/poses/p15_rain.json`, the 9 poses written for S1 (`Docs/plans/P15_S1_RAIN_SPIKE.md` section 4):
  - under the courtyard walk planks, looking up (north and south) and along the north walk floor;
  - the chapel nave, at the roof hole and its floor;
  - the cloister south walk looking into the garth;
  - the cloister north walk at its roof hole;
  - the belfry at the south-west collapse;
  - the mid stair.

  P15-9 adds `cr_tall_ossuary_15m` from `p14_viewpoints.json` to show the crypt has no rain.

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
| R-68 | A candle flame or a fire lives inside a never-save Blueprint | F0 finds it; change only the placed instance's material override or the MI; otherwise leave it and list it. **F0: none is** (F0.1, F0.2) |
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

### F0: read-only survey (2026-11-08, commit e92b465)
`Tools/fx/p15_f0_survey.py` (lighting-vfx, Sonnet high) made about 1900 editor calls. The map was not dirty before or after, PIE never ran, and nothing was set or saved. Full tables: `Docs/ArtTest/fx/p15_f0_tables.md`, raw data in `p15_f0.json`, Niagara tools in `p15_f0_niagara_tools.md`. The lead checked: the commit has the 4 files only, `L_Monastery` is not dirty, and PIE is off. Values below are final unless a line says "check by eye".

**F0.1 Flames (section 8 "Candle flames").**
- **22 level `StaticMeshActor`s** use `SM_LB_Prop_CandleFlame_A`:
  - 13 chapel: `Ch_AltarFlame_N1_F`, `N2_F`, `N3_F`, `S1_F`, `S2_F`, `S3_F`, `Ch_RitualFlame_1_F`, `2_F`, `4_F`, `Ch_SillFlame_S2_1_F`, `Ch_StatueHolder_Flame_1`, `_2`, `Sa_Flame_2_F`;
  - 9 crypt: `CD_Candles_Niche_E_CC_Flame`, `_E_WC_`, `_N_SC_`, `_S_FP_`, `_S_NC_`, `CD_Candles_Puzzle_E_Flame`, `_W_`, `CD_Candles_Sarc_0_Flame`, `_1_`.
- All draw `MI_LB_CandleFlame` from the mesh's default slot 0 (`MAT_Flame`), with no actor overrides. That MI's parent is the engine `EmissiveMeshMaterial`, with one vector `Color` (12, 5, 0.8). Never reparent it.
- **P15-6:** set a slot-0 material override to `MI_Flame_Candle` on each of the 22 actors. The mesh asset stays unchanged.
- The 5 `CD_Candles_Niche_*_Flame` actors are `EmissiveActors` of `SLG_Crypt_Niches` (hidden when it goes Off at `State.Ritual.2`). Hiding works with any material.
- No light group lists a flame as a glow actor: the glow actors are the 6 lanterns of `SLG_Cloister_*` and `SLG_Tower_*` (read 2026-11-08).
- **Blueprint flames.** All are engine `Sphere` meshes with `MI_LB_CandleFlame`, and none has a never-save Blueprint in its chain:
  - the 4 `BP_PuzzleCandle_C` (`Candle_P1…P4`, component `Flame`, relative Z 50.5, scale (0.04, 0.04, 0.065));
  - the player's candle, `BP_LBCharacter.CandleFlame` (relative Z 59, scale (0.5, 0.5, 0.167));
  - the 4 `Saint1…4Flame` cones of `BP_StainedGlassClue_Saints`.
- **P15-6 rule for the Blueprint flames:**
  - The saints' cones stay as they are; they are part of the window art.
  - For the puzzle candles and the player's candle, the agent first reads `BP_PuzzleCandle` and `BP_LBCharacter`, read-only: does any graph set that component's mesh or material at run time?
  - **If not:**
    - the puzzle candles get per-instance overrides: mesh `SM_LB_Prop_CandleFlame_A`, slot 0 `MI_Flame_Candle`, and a scale that gives the chapel flames' world size;
    - the player's candle gets the same on the `BP_LBCharacter` component template, then compile and save `BP_LBCharacter` only.
  - **If a graph does:** leave it and list it.
  - The player's flame is judged by eye in P15-7.

**F0.2 Fires (sections 6.3 and 8 "Torches").**
- The five Cascade `Emitter` actors are plain level actors with rotation (0, 0, 0). No light group or Blueprint references them; `SLG_Crypt_Torches` lists only the three lights, and its only rule is Flicker at `State.Ritual.2`.
- **P15-6:** for each row below:
  1. place a `NiagaraActor` with `add_to_scene_from_asset(NS_LB_TorchFire)`, at the location shown, rotation (0, 0, 0), scale 1;
  2. set `User.Scale`;
  3. read it back;
  4. only then delete the Cascade actor.
- The point lights and light functions stay unchanged.

| New actor | Replaces | Location | `User.Scale` |
|---|---|---|---|
| `FX_Torch_Fire_NS` | `FX_Torch_Fire` (PS_Fire_00, scale 0.7) | (327, 1600, 250) | 1.0 |
| `FX_Crypt_Torch_T1_NS` | `FX_Crypt_Torch_T1` (PS_Fire_00, 0.7) | (6321, −1100, −380) | 1.0 |
| `FX_Crypt_Torch_T2_NS` | `FX_Crypt_Torch_T2` | (8979, −2700, −380) | 1.0 |
| `FX_Crypt_Torch_T3_NS` | `FX_Crypt_Torch_T3` | (11150, −721, −380) | 1.0 |
| `FX_Crypt_Brazier_NS` | `FX_Crypt_Brazier` (PS_Fire_01, 0.5) | (11000, −2299.1, −459.4) | 1.8 |
| `FX_FirePit_Fire` | nothing (new) | (1150, 1650, 25) | 1.4 |

The fire pit is embers with a 400 lm light (`Light_FirePit_Ember`) and the smoke wisp `FX_FirePit_Smoke` (`NS_LB_SmokeWisp`). Both stay. Its fire starts low at 1.4, and P15-7 item 6 sets the final size; 2.2 (section 6.3) is the upper bound.

**F0.3 Roofs and openings (section 1, S1).**
- **Thickness:**
  - courtyard planks: 4 cm, 8 per walk;
  - chapel roof slabs: 20 cm;
  - cloister lean-to panels: 24.3 cm, including the rafters;
  - crypt and cloister vault shells: about 25 cm;
  - the stair-house roof and the tower pyramid are hollow shells.
- Every roof mesh is Nanite, and its distance field comes from the project switch (`r.GenerateMeshDistanceFields` 1, voxel density 0.2, so 5 cm). Only the planks are thinner than a voxel (R-66).
- Every roof piece is NoCollision except the courtyard planks. Those read `collisionEnabled` QueryAndPhysics although the profile string says NoCollision. They are above head height, so there is no gameplay effect; it is noted here only because the plan used to say "NoCollision".
- **Openings where rain must show:**
  - **chapel:** `Ch_Roof_S1` hole, X 6250…6750, Y −643…−193 (roof plane Z 1399…1935);
  - **cloister north:** `CLA_Roof_N_2` hole, X 10850…11270, Y 2180…2775 (Z 640…1046), over the `CLA_Vault_N_E` hole X 10900…11450. The open sky column is X 10900…11270, Y 2260…2775.
  - **tower:** the south-west collapse of `TWA_Roof`, X 11975…12400, Y 1475…1900 (Z 3530…4400), into the belfry;
  - **courtyard walks:** the uncovered parts (planks cover 40 % of the north walk and 28 % of the south walk; rectangles in the tables, T§3).
    - North planks: row 0 (Y 984…1064, Z 647…714) is complete over X 2200…3000. The rest are single planks: `1_2`, `3_2` (Y 1138…1218), `1_3` (Y 1215…1295, the only one at the eave), and `4_1` (X 2800…3000, Y 1061…1141).
    - South planks: rows at Y −1065…−1149 (X 4400…4800), Y −1146…−1230 (X 4200…4400, 4600…5000) and Y −1228…−1312 (X 4200…4600, 4800…5000).
- **Open by design:** the courtyard, the garth (X 10247…11462, Y 1344…2261), the shortcut passage (X 6040…9460, Y 1700…2300) and the approach.
- **Crypt:** ground slabs cover the grates (traces from above stop at Z 0), so no rain reaches the crypt.

**F0.4 Strike target:** (12530.8, 2000, 4844.8), check by eye ±15 cm (section 3). From the tower-reveal pose (600, 0, 170) the line of sight is clear, at pitch 21.1° and yaw 9.5°.

**F0.5 Sky:**
- The `SkySphere` radius is 1,638,400 cm, so `SkyBoltDistance` = 60000.
- Height fog: density 0.035, falloff 0.35, max opacity 0.95, cutoff 1,000,000.
- About 49 % of a bolt's light reaches a ground camera at 60000 cm, but `M_LB_Bolt` has fogging off, so the bolt is not fogged.

**F0.6 Shaft dust boxes (section 8 "Shaft dust").** Actor = `FX_Dust_<shaft>`, location = centre, rotation = box rotation (P, Y, R), `User.BoxExtent` = half-extent.

| Shaft | Centre | Rotation | Half-extent | `User.Count` |
|---|---|---|---|---|
| `Ch_Shaft_Roof` | (7271, 122.1, 944) | (−38, 35, 0) | (600, 120, 120) | 120 |
| `Ch_Shaft_S1` | (6882.7, −521, 365) | (−38, 35, 0) | (474.3, 30, 180) | 120 |
| `Ch_Shaft_S2` | (7882.7, −521, 365) | (−38, 35, 0) | (474.3, 30, 180) | 120 |
| `Ch_Shaft_S3` | (8882.7, −521, 365) | (−38, 35, 0) | (474.3, 30, 180) | 120 |
| `SA_Crypt_G1` | (8297.9, −2214, −325) | (−12, −145, 180) | (19.2, 19.2, 224) | 80 |
| `SA_Crypt_G2` | (9797.9, −2246.5, −325) | (−12, −145, 180) | (19.2, 19.2, 224) | 80 |
| `SA_Crypt_G3` | (10982.7, −1562.5, −265.5) | (−22.7, −42.9, 180) | (55, 55, 192) | 80 |
| `SA_Tower_F03` | (12638.2, 1636.7, 586.3) | (−52, −145, 180) | (11, 11, 172) | 80 |
| `SA_Tower_F07` | (12638.2, 1636.8, 1495.5) | (−52, −145, 180) | (11, 11, 172) | 80 |
| `SA_Tower_F08` | (12092.8, 2037, 1803.6) | (−52, −145, 180) | (11, 11, 64) | 80 |
| `SA_Tower_Roof` | (12443.3, 1866.8, 3783.5) | (−52, −145, 180) | (55, 55, 316) | 80 |

The tower slit shafts are F03, F07 and F08, plus the roof shaft. The thin crypt and tower boxes may read dense at 80; P15-7 item 8 can lower the count.

**F0.7 Water mist.**
- `FX_WaterMist_W` at (9047.5, −2280, −593), `User.Extent` (495, 390), over `CA_Water_W`.
- `FX_WaterMist_E` at (10002.5, −2280, −593), `User.Extent` (395, 390), over `CA_Water_E`.
- `CA_Water_Ledge` (Z −593) and the black still pit `CA_Water_Pit` (Z −650) get no mist.

**F0.8 Drips (`FX_Drip_<tag>`).** The crypt points are on corridor centre lines at Z −105, 5 cm under the visible vault crown (Z −100, P9). The visible vault has no collision; the hidden collision slab is at Z −40. Check by eye that each point sits just under the mesh. The belfry points are under the pyramid slate.

| Tag | Location | `User.FallHeight` | `User.bWater` |
|---|---|---|---|
| `W_9050` | (9050, −2280, −105) | 488 | true |
| `W_9200` | (9200, −2280, −105) | 488 | true |
| `Pit_9400` | (9400, −2280, −105) | 545 | true |
| `E_9900` | (9900, −2280, −105) | 488 | true |
| `E_10000` | (10000, −2280, −105) | 488 | true |
| `WC_a` | (6450, −1900, −105) | 495 | false |
| `SC_b` | (7250, −2350, −105) | 495 | false |
| `NC_a` | (10250, −900, −105) | 495 | false |
| `Belfry_N_wall` | (12600, 2440, 3700.9) | 1200.9 | false |
| `Belfry_NW_corner` | (12100, 2400, 3793.1) | 1293.1 | false |

Every point is at least 111 cm from a WalkPath segment and 146 cm from an AI point.

**F0.9 Eave drips (`FX_EaveDrips_<id>`).**
- **Placement:** the actor sits at the start point. Its yaw points local X along the line, `User.LineLength` is the line length, and `User.FallHeight` is the drop to the ground.
- **Courtyard walks:** water runs off the lower edge of a plank, so the courtyard lines are only where a plank reaches the eave row. Elsewhere the eave is bare rafters.
- **Cloister:** the lean-to panels are continuous, and each line is 3 cm on the garth side of the panel edge. The north line's second panel is left out, because the roof hole leaves only two 90 cm stubs.

| Id | Start | Yaw | `User.LineLength` | `User.FallHeight` |
|---|---|---|---|---|
| `CyN` | (2200, 1296, 454) | 0 | 200 | 453 |
| `CyS_A` | (4200, −1313, 476) | 0 | 400 | 475 |
| `CyS_B` | (4800, −1313, 476) | 0 | 200 | 475 |
| `ClS` | (11380, 1423, 637) | 180 | 1100 | 537 |
| `ClN1` | (10320, 2177, 637) | 0 | 400 | 537 |
| `ClW` | (10323, 1420, 637) | 90 | 800 | 537 |
| `ClE` | (11377, 2180, 637) | −90 | 800 | 537 |

**F0.10 Cloth (`FX_Cloth_<id>`).**
- The pivot is the top centre; yaw turns the cloth's local Y to the wall normal pointing into the room.
- `MI_Cloth_Linen_Red` goes on the two banners and `MI_Cloth_Linen_Dark` on the rest.
- The arcade top edges come from an estimated intrados (about Z 585); check by eye ±15 cm.
- Every piece clears the 60 cm lane and 150 cm AI-point rules, and the belfry pieces are 209 cm or more from the bell frame.

| Id | Mesh | Location (top centre) | Rotation | MI |
|---|---|---|---|---|
| `Belfry_W1` | `SM_LB_Prop_ClothStrip_A` | (12046, 1905, 3180) | (0, −90, 0) | Dark |
| `Belfry_N2` | `SM_LB_Prop_ClothBanner_A` | (12595, 2454, 3180) | (0, 180, 0) | Red |
| `Belfry_E1` | `SM_LB_Prop_ClothStrip_B` | (12954, 2095, 3180) | (0, 90, 0) | Dark |
| `Belfry_S2` | `SM_LB_Prop_ClothStrip_A` | (12405, 1546, 3180) | (0, 0, 0) | Dark |
| `Slit_F03` | `SM_LB_Prop_ClothStrip_B` | (12500, 1546, 778.1) | (0, 0, 0) | Dark |
| `Slit_F07` | `SM_LB_Prop_ClothStrip_B` | (12500, 1546, 1687.3) | (0, 0, 0) | Dark |
| `Cloister_N_1` | `SM_LB_Prop_ClothBanner_A` | (10750, 2256, 555) | (0, 0, 0) | Red |
| `Cloister_W_1` | `SM_LB_Prop_ClothSheet_A` | (10244, 1850, 520) | (0, 90, 0) | Dark_Sheet |
| `Cloister_S_2` | `SM_LB_Prop_ClothStrip_A` | (11050, 1344, 555) | (0, 180, 0) | Dark |
| `Gate_Inner` | `SM_LB_Prop_ClothStrip_A` | (306, 400, 600) | (0, −90, 0) | Dark |

**F0.11 Rain curtains (`FX_RainCurtain_<id>`).**
- `SM_LB_FX_CurtainCard` at scale (30, 1, 25), so 3000 × 2500 cm, with its bottom centre at the location.
- They stand outside the world's backdrop box (`Perim_*` walls, X −3040…13440, Y ±3640, 800 tall).
- Only 4 of the 16 viewpoints see a card; the rest look along walls or are indoors. P15-7 can drop or move cards.

| Id | Location | Rotation |
|---|---|---|
| `N_600` | (600, 4800, −200) | (0, 180, 0) |
| `N_2400` | (2400, 4800, −200) | (0, 180, 0) |
| `N_4200` | (4200, 4800, −200) | (0, 180, 0) |
| `N_6000` | (6000, 4800, −200) | (0, 180, 0) |
| `N_8000` | (8000, 4800, −200) | (0, 180, 0) |
| `N_11500` | (11500, 4800, −200) | (0, 180, 0) |
| `N_14500` | (14500, 4800, −200) | (0, 180, 0) |
| `S_11500` | (11500, −4800, −200) | (0, 0, 0) |

**F0.12 Niagara over MCP (from the tool schemas; nothing was created).**
- **Yes:**
  - add or remove emitters, modules and renderers;
  - set module inputs as literals, enums, linked attributes, dynamic inputs or a single-line HLSL expression;
  - `Kill On Collision`, restitution, friction and rest state;
  - read `Particles.HasCollided` by name;
  - sprite alignment, facing and material;
  - user parameters on the system, and `SetVariable` per component.
- **No:** scratch-pad or custom HLSL modules.
- **Unknown until S1:** the `Collision` module's distance-field mode. The schema lists no mode input, and the library also has a separate zero-input `NiagaraDistanceFieldCollisions` module.

**F0.13 Global distance field:**
- the settings are on: mesh distance fields are generated, `r.AOGlobalDistanceField` is 1, and there are 4 clipmaps;
- Lumen uses hardware ray tracing with `r.Lumen.TraceMeshSDFs` 0, so Lumen does not need the global distance field;
- MCP_NOTES records `DistanceToNearestSurface` reading about 0 in a material;
- nothing yet proves the field holds data at run time. S1 tests it.

**F0.14 Census:**
- 3015 actors at the start of P15-6.
- New actors: the target 1, dust 11, water mist 2, drips 10, eave drips 7, cloth 10, curtains 8, and fires +6 − 5.
- So the P15-6 check expects **3065**.

### S1 round 1: rain occlusion spike (2026-11-08)
- **Build:** commit e289330 (lighting-vfx, Sonnet high). The recipe is in `Docs/ArtTest/fx/s1/s1_build.md`, and `s1_spike.py check` gives 125 PASS. Nothing was saved.
- **Captures:** 9 poses × 4 states (`_onF` fall 20000, `_off1`, `_onS` fall 3000, `_off2`), taken with the owner present. The sheet is `Docs/ArtTest/fx/s1/s1_sheet.png`. `Tools/fx/s1_leak.py` counts white rain-streak pixels and orange splash pixels inside the roofed rectangles, against `_off1`.
- **Q1 rain (kill on collision): A works.**
  - Rain pixels under the roof: 0 in the chapel (both views) and 0 in the cloister south walk.
  - The courtyard planks look clean by eye in the up-views.
  - Rain falls only through the chapel hole and the cloister north hole.
  - The tower stair shows at most one stray streak per frame. Simulate runs at a low frame rate, so a drop can step past a thin surface; `RainRadius` goes from 10 to 20.
- **Q2:** the global distance field holds data at run time.
- **Q3:** yes. The mode is the static switch `GPU Collision Type` = "GPU Distance Fields" on the placed module.
- **Q4: the splash rest does not hold.** The latch turns a splash orange where it first touches, but the particle then moves on.
  - Cloister walk floor: 2287 orange pixels at fall 20000 and 3198 at fall 3000. The splashes slide off the sloped lean-to roofs, then drop through.
  - Chapel up-view: 328 at fall 20000 against 0 at 3000. The fast fall tunnels through the 20 cm slab.
  - **Fix (round 2):** pin each splash where it first touches (`LandPos`, zero velocity, die 0.45 s after landing), and make it fall at rain speed.
- **Q5:** yes. The second renderer draws the flat ring (seen edge-on as the horizontal flare), bound to `Particles.RingSize` and `Particles.SpriteFacing`.
- **Q6:** the global distance field costs almost nothing in a static view. `ProfileGPU` with all 5 spike systems running (16.0 ms frame, editor):
  - `GlobalDistanceFieldUpdate` 0.001 ms and `DistanceFields` 0.045 ms;
  - the Niagara GPU simulation 0.066 ms;
  - translucency 0.244 ms.

  The update cost of a moving camera is measured in P15-10.
- **Tower: no rain gets through the south-west collapse into the belfry.**
  - The hidden collision cube `Tw_Roof` is not the cause: its component has `bVisible` false, so it is not in the scene.
  - The likely cause is that the hollow pyramid `SM_LB_Tw_Roof_BrokenSW` builds a solid mesh distance field, which seals the hole.
  - **Fix (round 2):** build that mesh's distance field as two-sided. If MCP can't set it, a small local rain emitter under the collapse inside the belfry does the job in P15-6.

### S1 round 2 and verdict (2026-11-08)
- **Build:** commit 6db0702, by the agent.
  - The splash pin chain is in section 6.1. Fall is 1250 cm/s and `RainRadius` 20.
  - MCP could not reach `bGenerateDistanceFieldAsIfTwoSided` (`StaticMesh.sourceModels` is not exposed). The owner ticked "Two-Sided Distance Field Generation" on `SM_LB_Tw_Roof_BrokenSW`, LOD 0 build settings, by hand, and applied it without saving.
- **Captures:** 7 poses, `_r2on` and `_r2off`, plus `s1_tw_belfry_sw` (12750, 1700, 2700, 12, 180). That extra pose was added because the round 1 belfry pose looks into the bell, which hides the south-west corner.
- **`s1_leak.py`, inside the roofed rects (round 2 on against off):**

  | Area | Rain pixels | Splash pixels |
  |---|---|---|
  | Chapel, both views | 0 | 0 |
  | Cloister south walk | 0 | 0 |
  | Tower mid stair | 0 | 0 |

  In round 1 the cloister walk had 2287 / 3198 splash pixels and the chapel 328.
- **What shows where it should:**
  - splashes appear only on open ground, under the openings, and on roof tops seen through openings;
  - the cloister north hole shows its rain column and floor splashes;
  - the belfry's south-west corner gets rain and floor splashes through the collapse (479 rain and 231 splash pixels in the new pose).
- **Verdict: approach A passes.** Fallbacks B and C are not needed.
- **The final `NS_LB_Rain`** uses:
  - distance-field kill with a 20 cm radius;
  - splashes pinned at first contact, falling at rain speed;
  - the second renderer for the ring.
- **Cost:** the global distance field update is about 0 ms in a static view (round 1, Q6). The moving-camera cost is measured in P15-10.
- **Carry-over to P15-6: done.** On the owner's "save mesh", the lead saved `SM_LB_Tw_Roof_BrokenSW` (one package) with "Two-Sided Distance Field Generation" on. The saved file carries the flag.
- **Clean-up:**
  - `s1_spike.py remove --yes` deleted the 5 spike actors, the 2 spike assets and the `/Game/LastBell/FX/Spike` folder. `FX_FirePit_Smoke` is untouched.
  - The map stays dirty and unsaved: its contents match the saved file again.

### P15-1, P15-2, P15-3 and the imports (2026-11-08)
- **P15-1 code** (f13b09f, 53a6b67):
  - section 2 is implemented;
  - 13 new tests;
  - the editor build succeeds; the suite has **140 passed and 1 failed**, the failure being `LastBell.Functional.StormFX.Monastery.FXSetup`, expected until P15-6 creates `DA_StormFX`, the link, the strike target and the level actors;
  - no invalid tags.
- **Code fix found by the suite:** `UNiagaraFunctionLibrary::SpawnSystemAtLocation` returns null under `-nullrhi` (engine `CreateNiagaraSystem`: `FApp::CanEverRender()`). So the rain component is now created directly, mirroring the engine function without that guard. The sparks keep `SpawnSystemAtLocation`. The activation check in the tests runs only when rendering is possible.
- **Additions to the spec** (reviewed by the lead):
  - `ULBStormSubsystem::RequestFlashAtTarget`, for `lb.StormFX.Bolt 1`;
  - `IsFlashRunning()` for the bolt-hide rule;
  - `ULBStormFXSubsystem::OverrideSettings` and `Rearm()`, for the tests;
  - the `lb.StormFX.Enabled` CVar lives in the subsystem file.
- **A Game-target compile error predating Phase 15:** `AI/LBWardenAnimInstance.cpp` calls the editor-only `UBlendSpace::GetBlendSpaceData` unguarded (P13). It was flagged to the owner as a separate task, outside Phase 15.
- **P15-2 textures** (9c41155):
  - `Tools/textures/fx/make_fx_textures.py` is deterministic and writes 7 textures to `SourceArt/FX/`;
  - the contact sheet is `Docs/ArtTest/fx/p15_textures_sheet.png`;
  - the cloth fabric is Poly Haven `hessian_230` (CC0), registered.
- **P15-3 meshes** (3a7b300): `Tools/blender/fx/` builds, verifies (6/6 PASS) and renders 4 cloth meshes and 2 cards. The renders are `Docs/ArtTest/fx/p15_cloth_*.png`.
- **Imports** (2be75aa):
  - 17 assets under `/Game/LastBell/FX/`, saved one package at a time;
  - the textures' compression, sRGB and alpha are read back;
  - the meshes have Nanite off and no collision, and the cloth bounds extension is ±60;
  - the cloth faces +Y after Unreal's Y mirror.
- **Still to check:** the cloth's UV V orientation and its front face, with `M_LB_Cloth`, in P15-4.

### P15-4 and P15-5 (2026-11-08)
- **P15-4 materials** (56d9ce0, 9c89dd7):
  - 9 masters, `MF_LB_ClothWave` and 13 MIs; all compile with 0 errors and the MIs read back. Rebuild with `Tools/fx/p15_4_materials.py`. Thumbnails are in `Docs/ArtTest/fx/p15_4/`.
  - **Lead decision:** `M_LB_Rain`, `M_LB_Splash`, `M_LB_Ripple` and `M_LB_RainCurtain` are **Additive**, with every mask in Emissive. With translucent blending, the low bases (0.035 and similar) would have darkened lit backgrounds. Opacity still scales additive output, so it is left unconnected.
  - **Accepted additions:** flame sway scales with the object's size; a sprite teardrop for the torch flame; per-MI `ClothLengthCm` and `ClothWidthCm`; the Dark tint (0.20, 0.18, 0.16) (a P15-7 item); `MI_LB_WaterMist` the same as `MI_LB_Mist`.
  - The mesh slot defaults are set on the 6 FX meshes.
- **P15-5 Niagara** (5d58555): 7 systems, each UpToDate with 0 errors. `Tools/fx/p15_5_niagara.py check` gives 467 PASS (re-run by the lead). The record is `Docs/ArtTest/fx/p15_5_build.md`.
  - **`NS_LB_Rain`:** the nine user parameters match the C++. Rain velocity uses `RandomRangeVector`.
  - **Splash:** the collision radius is **6**, as in S1 round 2 (lead: accepted; 20 would hold splashes 20 cm above the floor).
  - **Drips:** MCP has no event-handler tool, so `NS_LB_Drip` and `NS_LB_EaveDrips` use the fallback. Each drop is one particle pinned at −`FallHeight`, and a visibility tag switches it from the drop renderer to the crown and the ring. The ring shows only with `bWater`.
  - **Sparks:** the light renderer is enabled per particle on every 20th particle.
  - **Not seen running:** Niagara thumbnails aren't supported, so the first look is in P15-6/P15-7. Things to look at:
    - the drip timing;
    - the ground-mist plane;
    - the upright torch flames;
    - the sparks light and how the system completes;
    - the GPU rain count.
