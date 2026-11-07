# Phase 14: Lighting and the storm's light: plan

**Status:** approved by the owner on 2026-11-07 ("go"). P14-0 done (D-096, D-097, D-098; R-59…R-63).

**Branch:** `claude/phase-14-lighting-storm`, from `main` (f13721b).

**Rules:**
- D-048 applies. The lead plans in Opus 5.5 at xhigh. Every implementer is spawned with `model: "sonnet", effort: "high"`.
- The owner is told before any capture over about 15 minutes. Agents never run the capture tool and never operate the desktop.
- The repo is public: no non-redistributable asset is committed (D-094, D-095). This phase brings in no external asset.

## 1. Goal and the owner's choices (2026-11-07)
**Goal:** make the night feel like a storm, and finish the lighting:
- lightning lights the sky and, through the windows, the interiors;
- the wind moves the plants;
- the storm grows with the story;
- some lights die as the rituals are completed;
- every area meets a readability floor and an agreed colour grade, at a measured frame cost.

**The owner's choices:**

| Question | Choice |
|---|---|
| Phase 14 scope | **Lighting plus the storm's light and motion.** Phase 15 gets the particles: rain, splashes, drips, dust, candle-flame effects, cloth |
| Storm arc | **Builds with the story:** strong at the arrival, quieter indoors, rising through the cloister, peaking at the tower top and the finale |
| Lightning | **Atmosphere, scripted beats, and reveals.** Flashes can briefly reveal the Warden or hidden details |
| Story-driven light changes | **Yes, a small set:** 2–3 changes per mechanism, restored correctly after a checkpoint load |

## 2. Exit conditions
1. **Storm arc:** storm strength follows the table in section 5.2, and lightning comes more often as it rises. Shown by tests and the owner's playtest.
2. **Flash coverage:** a flash lights the following:
   - the cloud dome, with a bright patch that moves from flash to flash;
   - everything the moon lights;
   - the interiors, through the chapel lancets and roof hole, the crypt grates and the tower slits;
   - the stained glass, the light shafts and the chapel's light pools.
   
   A sealed room does not light up. At `cr_torch_t1_3m`, a crypt corridor with no opening in view, mean luma changes by less than 10 % during a frozen flash at 0.8.
3. **Reveals:**
   - a strike when the player first looks at the tower after entering the courtyard;
   - a strike after each ritual;
   - strikes at the tower top and at the finale;
   - a flash when the Warden is in view in an exposed space;
   - the two apparitions appear with a flash;
   - five chalk markings that are visible only during flashes, never carrying puzzle information.
4. **Wind:** the courtyard, garth and passage plants and the ivy sway with gusts that follow the storm. Nothing visibly pops at the sway cut-off distance (owner).
5. **Story light changes:** the changes in section 8 happen live, with a guttering fade, and are correct after a checkpoint load. Every critical-path viewpoint keeps its readability floor (section 9.3).
6. **Lighting pass:**
   - each post-process volume covers only its own area;
   - the owner's chosen grade is applied everywhere;
   - each area's exposure meets its target (section 9.3);
   - no Lumen noise or light leak blocks the owner's approval (R-09);
   - R-31 is closed by a measurement.
7. **Viewpoints:** the owner approves the 19 viewpoints in section 10.
8. **Performance:**
   - GPU ≤ 16.6 ms at High at the six standard spots (section 11), with the storm at full strength and the wind on;
   - against the P14-B baseline, storm and wind add no more than 0.6 ms of GPU and 0.3 ms of game thread at any spot.
9. **Tests:** the suite passes, with the new tests in section 12.
10. **Approval:** the owner approves the phase.

## 3. What's there now (facts; research 2026-11-07)
### World state and story
`ULBWorldStateSubsystem` is a GameInstance subsystem.
- **Delegates:** `OnStateChanged(Tag, bAdded)` fires per tag. `ReplaceState` and `ResetState` fire only `OnStateReplaced`; a checkpoint load calls `ReplaceState` before `OpenLevel`.
- **Matching:** exact, so a parent tag doesn't match its children.

**Story tags, in order:**
1. `State.Event.CourtyardEntered`, with Stage.1
2. `State.Chapel.CandlesSolved`
3. `State.Ritual.1`, with Stage.2
4. `State.Event.CryptEntered`, with Stage.3
5. `State.Ritual.2`, with Stage.4
6. `State.Event.CloisterEntered`, with Stage.5
7. `State.Tower.BellsSolved`
8. `State.Ritual.3`
9. `State.Event.TowerTop`
10. `State.Event.Finale`

**Stage.6 is never granted** (finding; out of scope, section 15).

### Lights
| Light | Settings |
|---|---|
| Moon: actor label `DirectionalLight` (`DirectionalLight_1`) | 0.9 lux, (0.745, 0.804, 0.922), rotation (−38, 35, 0), shadowed |
| `Moon_Fill` | 0.06 lux, shadowless (it must not flash: it would light the interiors) |
| `SkyLight` | 0.28 |

**Moonlight entry spots:**
- Chapel: `Light_Chapel_Moon_S1/S2/S3`, 9100 lm, and `Light_Chapel_Moon_Roof`, 15000 lm. Shadowed, with gobos.
- Crypt grates: `L_Crypt_Moon_G1`, 560 lm, shadowed; `G2`, 900 lm, shadowed; `G3`, 250 lm, shadowless.
- Tower slits: `L_Tw_MoonSlit_F03/F07/F08`, 600 lm, shadowed.
- Belfry fill: `L_Tw_BellFill`, 200 lm, moon colour.

**Other lights:** the warm lights are listed in `census_p11.json` (59 lights).

### Post-process
Every volume uses a fixed exposure: histogram metering with min = max EV100.

| Volume | EV100 | Other | Bounds and priority |
|---|---|---|---|
| `PostProcess_Exposure` | 3 | — | Unbound |
| `PP_Outdoor_Night` | 1.15 | satShadows 0.65 | to X 5500, priority 1 |
| `PP_Crypt` | 0.2 | bloom 0.27 | — |
| `PP_Cloister` | 0.65 | satShadows 0.65 | [6000, −450, −40]..[13100, 3200, 4200], priority 1 |

There is no chapel or tower volume. **The `PP_Cloister` box covers the chapel nave (Y ≥ −450).** That is the likely cause of the nave's luma rise from 0.10 (P8) to 0.20 (P11), which was never traced.

### Sky
- The `SkySphere` actor uses `MI_Env_NightSky`, a child of `MI_NightStormSky`, whose root is the engine's `/Engine/EngineSky/M_Sky_Panning_Clouds2` (opaque unlit).
- No volumetric clouds (D-046).

### Materials the storm can drive
- `M_LB_StainedGlass` and `_Translucent` (`EmissiveIntensity`, `Tint`): lancet MIs `MI_Glass_Lancet_A/_B`; `MI_Glass_East` (translucent); `MI_Glass_Clue_Saints`, a puzzle clue.
- `M_LB_LightShaft`: `MI_LightShaft_Window`, `_Roof`, `_Crypt`.
- `M_LB_Decal_LightPool`: `MI_Decal_LightPool_Lancet`.
- `M_LB_Decal_Chalk`: the existing textures `T_LB_Decal_ChalkSigil`, `_ChalkTally`, `_ChalkCircle` and `_DragMarks`.

### Foliage
**PCG plants:** 2248 instances in 312 ISM components on 19 `PCGV_*` volumes, with `M_LB_Foliage` MIs:
- `MI_Foliage_GrassMedium02`, `_NettlePlant`, `_WeedPlant02`, `_Fern02`, `_WildRooibos`, `_SearsiaLucida`, `_Moss01`;
- grass taller than 60 cm casts shadows.

**Other plants:**
- 175 `CLA_Garth*` and 32 `PSA_Weed_*` static-mesh actors;
- 32 ivy card actors on `M_LB_FoliageMasked` (`MI_Ivy_Green`, `MI_Ivy_Dead`), with stems on `M_LB_Surface`.

Neither foliage master has world position offset (WPO).

### Player candle
`ULBCandleComponent` sets its light's intensity every tick, so outside writes are overwritten. **This phase never touches the player candle.**

### Performance
P11-8 GPU at High, with headroom to 16.6 ms in brackets:

| Spot | GPU ms |
|---|---|
| Chapel mid-nave | 14.96 (1.64) |
| Cloister bells | 14.73 |
| Crypt ossuary | 14.13 |
| Belfry | 12.89 |
| Tower mid-stair | 12.71 |
| Courtyard garth | 12.27 |

The exact P11 camera poses were never recorded; section 11 fixes them from now on.

### No storm code or assets yet
There is no `MPC_LB_Wind`, no storm tag and no storm code. `MPC_LB_GrowthObstacles` is the only material parameter collection (MPC).

## 4. Architecture (C++ owns the storm; content stays in data)
New folder `Source/LastBell/Storm/`. The design rules apply: composition, subsystems, gameplay tags for state, no hard asset references in C++.

| Unit | Kind | Purpose |
|---|---|---|
| `LBStormLogic.h/.cpp` | pure functions (namespace `LBStormLogic`) | The maths: story intensity, flash envelopes, schedule intervals, wind, exposure, reveal decision, light-rule choice and flicker. Unit tested |
| `ULBStormSettings` (`LBStormSettings.h/.cpp`) | `UPrimaryDataAsset` → `/Game/LastBell/Data/DA_StormSettings` | Every number in section 5, plus the MPC as a soft pointer |
| `ULBStormSubsystem` (`LBStormSubsystem.h/.cpp`) | `UTickableWorldSubsystem` | The storm controller (section 5) |
| `ALBStormZone` (`LBStormZone.h/.cpp`) | `AActor` with a `UBoxComponent` (no collision) | How exposed a space is to the sky, 0–1; registers with the subsystem the way the stoop zones do |
| `ALBStateLightGroup` (`LBStateLightGroup.h/.cpp`) | `AActor` | Dims, kills or flickers listed lights from the story tags (section 8) |

**Settings lookup:**
- `ULBGameSettings` (`Systems/LBGameSettings.h`) gets `UPROPERTY(Config, EditAnywhere) TSoftObjectPtr<ULBStormSettings> StormSettings`.
- `Config/DefaultGame.ini` `[/Script/LastBell.LBGameSettings]` gets `StormSettings=/Game/LastBell/Data/DA_StormSettings.DA_StormSettings`.
- The subsystem loads it synchronously in `OnWorldBeginPlay`. If it's missing, the subsystem logs one warning and stays inactive.

**Activation:**
- `ShouldCreateSubsystem` is true only for Game and PIE worlds.
- In `OnWorldBeginPlay` the subsystem looks for an `ADirectionalLight` with the actor tag `LB_StormMoon`.
  - If there is none, it stays inactive: no ticking, no MPC writes. So `L_MainMenu` and the test maps without a tagged moon are unaffected.
  - If there are several, it logs a warning and uses the first.
- Enums: `ELBFlashProfile` { Sheet, Double, Triple, Auto }; `ELBFlashReason` { Ambient, Scripted, WardenReveal, Apparition, Debug }; `ELBLightStateMode` { On, Dim, Off, Flicker }.
- `RefreshLinkedLights()` (BlueprintCallable) rescans; tests use it.

**Linked lights** are found by actor tag at BeginPlay, with their base intensity recorded:

| Tag | Flash rule (F = flash value 0–1) |
|---|---|
| `LB_StormMoon` | intensity = base + `FlashLux` × F (the moon) |
| `LB_StormMoonSpot` | intensity = base × (1 + `SpotFlashGain` × F) |
| `LB_StormFill` | intensity = base × (1 + `FillFlashGain` × F) |
| `LB_StormSky` | intensity = base × (1 + `SkyFlashGain` × F) (the SkyLight) |

- Intensities are written only while a flash is running, and once more when it ends, so the render state isn't dirtied every frame.
- A linked light that disappears (streaming) is skipped, never dereferenced.

**MPC `/Game/LastBell/Materials/MPC_LB_Storm`.** It replaces the planned `MPC_LB_Wind` (D-096). The subsystem writes these every frame:

| Kind | Name | Meaning |
|---|---|---|
| Scalar | `StormIntensity` | 0–1 |
| Scalar | `LightningFlash` | F |
| Scalar | `WindStrength` | 0–1 |
| Scalar | `WindPhase` | radians, wrapped at 100 × 2π |
| Scalar | `PlayerExposure` | 0–1; used from Phase 15 on |
| Scalar | `DomeFlashGain`, `DomeFlashAdd`, `GlassFlashGain`, `ShaftFlashGain`, `PoolFlashGain`, `RevealGain`, `RevealEmissive` | copied from the settings each frame, so a live edit of the data asset shows at once |
| Vector | `WindDirection` | xyz, w unused |
| Vector | `FlashDirection` | unit vector toward the bright patch in the clouds |
| Vector | `FlashTint` | (0.75, 0.82, 1.0, 1) |

**Interface:**
- `RequestFlash(float Brightness, float DelaySeconds, ELBFlashReason Reason, ELBFlashProfile Profile = Auto)` (BlueprintCallable). The reasons are Ambient, Scripted, WardenReveal, Apparition and Debug.
- `GetStormIntensity()`, `GetExposureAt(FVector)`, `GetPlayerExposure()` (BlueprintPure).
- `OnLightningFlash(float Brightness, ELBFlashReason Reason)`, a dynamic multicast delegate fired at each flash's first pulse. Phase 16 hangs thunder on it.

**Console** (non-shipping, `Systems/LBConsoleCommands.cpp`):
- `lb.Storm.Flash [brightness=1] [profile=-1]`: profile −1 is random; 0 sheet, 1 double, 2 triple.
- `lb.Storm.Intensity <0..1 | -1>`: override, or clear with −1.
- `lb.Storm.Freeze <0..1 | -1>`: holds F at the value and pauses the schedule.
- CVar `lb.Storm.Enabled`, default 1. At 0 there are no flashes, the wind is 0 and F is 0.
- CVar `lb.Storm.Debug`, default 0. At 1 it puts on screen: intensity, target, seconds to the next flash, wind, player exposure, and the last reveal decision with its reason.

**Live tuning:**
- `DA_StormSettings` is read through its pointer every frame. An edit in the Details panel or through MCP `set_properties` during PIE shows immediately.
- `DebugFreezeFlash` (default −1) and `DebugIntensityOverride` (default −1) on the asset do the same as the console commands. That lets the lead freeze a flash for captures over MCP, which has no console.
- **Never save the asset with either one ≠ −1.** The QA check reads them.

## 5. The storm (numbers are `DA_StormSettings` defaults; field names in `code` font)
### 5.1 Exposure zones
**Exposure at a point** is the `Exposure` of the highest-`Priority` zone that contains it; on a tie, the lowest `Exposure` wins. With no zone it is `DefaultExposure` = 1.0, the open sky. The exposure is used for:
- the reveal rule;
- `PlayerExposure`, which the subsystem samples every 0.25 s at the camera location.

**Zones placed in P14-3** (bounds in cm):

| Actor | X | Y | Z | Exposure | Priority |
|---|---|---|---|---|---|
| `SZN_Chapel` | 6000 … 9100 | −1550 … 860 | −40 … 2400 | 0.35 | 1 |
| `SZN_Crypt` | 6300 … 12000 | −2950 … 520 | −1200 … −45 | 0.0 | 2 |
| `SZN_Passage` | 6040 … 9460 | 900 … 2600 | −40 … 1200 | 0.3 | 1 |
| `SZN_Cloister` | 9460 … 12040 | 500 … 3040 | −40 … 1500 | 0.6 | 1 |
| `SZN_Garth` | 10245 … 11460 | 1345 … 2260 | −40 … 1500 | 1.0 | 2 |
| `SZN_TowerShaft` | 11990 … 13010 | 1490 … 2510 | −40 … 2650 | 0.25 | 3 |
| `SZN_Belfry` | 11990 … 13010 | 1490 … 2510 | 2650 … 4800 | 0.85 | 3 |

`SZN_Garth`'s bounds are the min/max X and Y of the 175 `CLA_Garth*` plant locations, each extended by 100 cm (F0: plants X 10347–11362, Y 1444–2161). Not counted: the 6 garth structures with the same prefix (`CLA_GarthWall_N/S/E/W`, `CLA_GarthCross`, `CLA_GarthBed`); with them the box would be X 10200–11500, Y 1300–2300, which reaches under the walk roofs (eaves at Y 2180).

### 5.2 Story intensity
**Target:** the `Intensity` of the last `StoryIntensity` entry whose tag is present. With none present it is `DefaultIntensity` 0.55.

| # | Tag | Intensity |
|---|---|---|
| 1 | `State.Event.CourtyardEntered` | 0.60 |
| 2 | `State.Ritual.1` | 0.55 |
| 3 | `State.Event.CryptEntered` | 0.50 |
| 4 | `State.Ritual.2` | 0.65 |
| 5 | `State.Event.CloisterEntered` | 0.80 |
| 6 | `State.Ritual.3` | 0.90 |
| 7 | `State.Event.TowerTop` | 1.00 |
| 8 | `State.Event.Finale` | 1.00 |

**Response:**
- The live intensity moves toward the target at `IntensityRatePerSecond` 0.02, so 0.5 → 1.0 takes 25 s.
- `OnStateReplaced` and BeginPlay **snap** to the target.
- `DebugIntensityOverride` or the console override replaces the target and snaps.

### 5.3 Lightning schedule
**Interval to the next ambient flash:** uniform in [lerp(`MinIntervalLow` 30, `MinIntervalHigh` 6, I), lerp(`MaxIntervalLow` 60, `MaxIntervalHigh` 14, I)] s, where I is the live intensity.
- The first flash after BeginPlay waits × `FirstFlashScale` 0.5.
- Any flash, whatever its source, is kept at least `MinGapSeconds` 2.5 after the previous one ended. A request that arrives inside the gap waits for it.
- The one exception is the strikes of one scripted sequence (section 5.6 b): they follow their own `Spacing`, start to start, and the gap applies only before the first strike and after the last.
- Ambient flashes are not scheduled while a scripted sequence or a reveal is pending or running. The ambient timer restarts when the sequence ends.

**Each ambient flash:**
- Profile: Sheet with weight 0.5, Double 0.35, Triple 0.15.
- Brightness: lerp(`BrightnessMin` 0.55, 1, random) × lerp(`BrightnessFloorLow` 0.7, 1, I).
- Direction: random azimuth 0–360°, elevation uniform 15–35°.
- `FRandomStream` seeded by `RandomSeed`. 0 means seed from the time; tests set 1401.

**Envelope (`LBStormLogic::EvaluateFlash`).** Each pulse starts at s and has peak p, attack A, hold H and decay τ. For u = t − s:

| u | v(u) |
|---|---|
| u < 0 | 0 |
| u < A | u / A |
| u < A + H | 1 |
| otherwise | exp(−(u − A − H) / τ) |

- F(t) = min(1, Brightness × max over pulses of p × v).
- The flash ends when t > last s + A + H + 5.3 τ (v < 0.005).

| Profile | Pulses (start s, peak p) | A / H / τ (s) |
|---|---|---|
| Sheet | (0, 1.0) | 0.08 / 0.10 / 0.25 |
| Double | (0, 0.55), (g, 1.0) | 0.03 / 0.04 / 0.12 |
| Triple | (0, 0.5), (g1, 1.0), (g1 + g2, 0.7) | 0.03 / 0.04 / 0.12 |

The gaps g, g1 and g2 are uniform in [`GapMin` 0.07, `GapMax` 0.16].

### 5.4 Flash output (defaults = preset B, chosen in P14-4)
| Field | A, subtle | **B, strong** | C, blinding |
|---|---|---|---|
| `FlashLux` (moon +lux) | 4 | **8** | 16 |
| `SpotFlashGain` | 1.5 | **3** | 6 |
| `FillFlashGain` | 0.75 | **1.5** | 3 |
| `SkyFlashGain` | 0.3 | **0.6** | 1.0 |
| `DomeFlashGain` | 3 | **6** | 10 |
| `DomeFlashAdd` | 0.03 | **0.05** | 0.08 |
| `GlassFlashGain` | 1.2 | **2.5** | 4 |
| `ShaftFlashGain` | 1.5 | **3** | 5 |
| `PoolFlashGain` | 1.2 | **2.5** | 4 |
| `RevealGain` / `RevealEmissive` | 4 / 2 | **4 / 3** | 4 / 4 |

**Fallback:** if Lumen's lagging bounce light looks like a smear after the flash (R-59), set `SkyFlashGain` to 0 and keep the direct light.

### 5.5 Wind
**Inputs:** I is the live intensity and t is game time.
- Base = lerp(`WindBaseLow` 0.2, `WindBaseHigh` 0.65, I).
- Gust = lerp(`GustLow` 0.15, `GustHigh` 0.4, I) × max(0, 2 × `FMath::PerlinNoise1D`(t × `GustFrequency` 0.12)).

**Outputs:**
- `WindStrength` = clamp(Base + Gust, 0, 1).
- `WindPhase` += dt × lerp(`PhaseSpeedLow` 1.2, `PhaseSpeedHigh` 2.4, `WindStrength`) rad/s, wrapped at 100 × 2π. The material only uses whole-number multiples of the phase, so the wrap never shows.
- `WindDirection` = normalised `WindDirection` (0.87, 0.5, 0), blowing from the west-south-west.

The wind is global: indoor foliage is negligible.

### 5.6 Reveals
**(a) Warden reveal** (`LBStormLogic::ShouldReveal`), checked at `RevealCheckHz` 5. All of these must hold:
- `bRevealEnabled`;
- intensity ≥ `RevealMinIntensity` 0.4;
- an `ALBWarden` exists and isn't `IsDormantPresentation()`;
- the head point (actor location + (0, 0, `WardenHeadOffsetZ` 140)) is between `RevealMinDistance` 800 and `RevealMaxDistance` 4000 cm from the camera;
- the head point is within `RevealConeDegrees` 30 of the camera's forward;
- a visibility line trace (`ECC_Visibility`) from the camera to the head point is clear, ignoring the player pawn and the Warden;
- `GetExposureAt(Warden location)` ≥ `RevealMinExposure` 0.5;
- at least `RevealCooldownSeconds` 30 have passed since the last reveal;
- no flash is running or pending.

**Result:** a `WardenReveal` flash with brightness 1, profile Double, after a delay uniform in [0.3, 0.9] s. The `FlashDirection` is the camera-to-Warden direction, flattened, then raised 20°.

Only the cloister walk (0.6) and the garth (1.0) pass the exposure test, which is where the hunt happens.

**(b) Scripted strikes** (`ScriptedStrikes`, `FLBStormStrike`):
- They fire only on `OnStateChanged` with the tag added. They never fire from BeginPlay or `OnStateReplaced`, so a reload doesn't repeat them, and no new tags are needed.

| Trigger tag | Delay (s) | Count | Spacing (s) | Brightness | Look gate |
|---|---|---|---|---|---|
| `State.Event.CourtyardEntered` | 0.4 after the look | 2 | 1.6 | 1.0 | **yes:** `LookTarget` (12500, 2000, 3800), cone 20°, `LookTimeout` 90 s; if never looked at, it doesn't fire; `FlashDirection` toward the target |
| `State.Ritual.1` | 1.2 | 1 | — | 1.0 | no |
| `State.Ritual.2` | 1.2 | 1 | — | 1.0 | no |
| `State.Ritual.3` | 1.2 | 1 | — | 1.0 | no |
| `State.Event.TowerTop` | 2.0 | 3 | 2.5 | 1.0 | no |
| `State.Event.Finale` | 0.3 | 2 | 0.8 | 1.0 | no |

Strikes use profile Double, with Triple for TowerTop's second strike.

**(c) Apparitions:**
- `FLBApparitionStation` gets `bool bLightningOnHold = false`.
- When a station enters Hold, `ALBWardenApparition` calls `RequestFlash(1.0, 0.15, Apparition, Double)` on the storm subsystem, if one exists.
- It is set on both placed apparitions in P14-3: the courtyard roofline, and the chapel rail, which the S3 lancet lights.

**(d) Lightning-only chalk markings:**
- A new deferred-decal master `M_LB_Decal_LightningReveal`: a duplicate of `M_LB_Decal_Chalk` with Opacity × saturate(`LightningFlash` × `RevealGain`) and Emissive = chalk colour × `FlashTint` × `LightningFlash` × `RevealEmissive`. It is invisible when F = 0.
- They are atmosphere only. **No puzzle information may depend on them**: the accessibility rule.
- They reuse the existing chalk textures.

| Actor | Texture (MI) | Where (fixed by F0) | Size (cm) |
|---|---|---|---|
| `RV_Gate_Sigil` | `T_LB_Decal_ChalkSigil` (`MI_Reveal_Sigil`) | Gatehouse inner face, courtyard side, 500 cm from the arch centre toward +Y, centre Z 260 | 220 × 220 |
| `RV_WellHouse_Tally` | `_ChalkTally` (`MI_Reveal_Tally`) | Well-house outer wall facing the key route, centre Z 140 | 120 × 80 |
| `RV_Chapel_Circle` | `_ChalkCircle` (`MI_Reveal_Circle`) | Chapel floor, centred on the S2 lancet light pool decal | Ø 180 |
| `RV_Garth_Drag` | `_DragMarks` (`MI_Reveal_Drag`) | The garth-facing wall nearest the `cl_tall_north_15m` view centre, Z 240–300 | 220 × 60 |
| `RV_Belfry_Tally` | `_ChalkTally` (`MI_Reveal_Tally`) | Belfry south wall beside the two south lancets, centre Z 2850 | 100 × 100 |

**Exact placements (F0).** These follow the wall-decal rule in `MCP_NOTES` (Materials item 6): rotation (0, yaw, 90), where forward (cos yaw, sin yaw) points into the wall. Floor decals use rotation (−90, yaw, 0). `DecalSize` is a half-extent (depth, vertical, horizontal).

| Actor | Location | Rotation | `DecalSize` | How the surface was found |
|---|---|---|---|---|
| `RV_Gate_Sigil` | (300, 500, 260) | (0, 180, 90) | (10, 110, 110) | A trace sweep at Z 260 finds the inner wall face at X 300 and the arch recess at Y −175 … 175 (centre 0). Buttresses stand at Y ±650, and the decal ends at Y 610. `KP_Lantern_Gate` (350, 560, 40…113) sits below the decal's bottom at Z 150. |
| `RV_WellHouse_Tally` | (1350, −1775, 140) | (0, −90, 90) | (10, 40, 60) | A sweep at Z 140 finds the north face at Y −1775: walls at X 1275–1425 and 1575–1725, door at X 1425–1575. The decal goes on the west pier, away from `KP_Lantern_Well` and the ivy. |
| `RV_Chapel_Circle` | (8265, −255, 0.5) | (−90, 0, 0) | (10, 90, 90) | The centre of `Ch_Pool_S2`. The pools fall about 765 cm +X of their lancets, so the S2 pool is at X 8265. |
| `RV_Garth_Drag` | (10750, 3000, 270) | (0, 90, 90) | (20, 30, 110) | The inner face of the north walk wall (`CLA_Wall_N_2/_3`, face Y 2994–3000). It faces the garth through the arcade bay between the piers at X 10600 and 10900. The art walls have no collision, so the face comes from the P10 layout tables, and the depth is 20 to cover the relief. |
| `RV_Belfry_Tally` | (12200, 1540, 2850) | (0, −90, 90) | (15, 50, 50) | The inner face of `TWA_S3_S` (Y 1540, P10 layout). The south lancets are clear at X 12340–12470 and 12530–12660, sill Z 2700. **The pier between them is only 60 cm wide**, so the tally goes 140 cm west of them. It is in the `tw_belfry` view (yaw −116° from the pose, 10° below centre). |

P14-3 checks every placement in a PIE Simulate capture with `lb.Storm.Freeze 0.8` typed by the owner. The art surfaces in the cloister and tower have no collision, so their planes come from the layout, not from a trace.

## 6. Materials (technical-artist, [EDITOR], P14-2)
**Rules for every material in this task:**
- Read the graph before editing.
- Compile, and check that there are no errors and no warnings.
- Do a thumbnail and a capture check.
- One package per save; never save-all.
- **`M_LB_Surface` is never opened for writing or saved.**

**Shared flash function.** `MF_LB_StormFlash` (`/Game/LastBell/Materials/Functions/`):
- Inputs: `Gain` (scalar), `Response` (scalar, default 1).
- Output: `Mul` = 1 + Gain × `LightningFlash` (MPC) × Response.
- It is used by all the flash edits below.

1. **Sky.**
   - Duplicate `/Engine/EngineSky/M_Sky_Panning_Clouds2` to `/Game/LastBell/Environments/Sky/M_LB_StormSky`.
   - Then: final emissive = original emissive × (1 + `DomeFlashGain` × F × Hot) + `FlashTint` × F × Hot × `DomeFlashAdd`, where Hot = 0.3 + 0.7 × saturate(dot(−CameraVector, `FlashDirection`))⁶.
   - Reparent `MI_NightStormSky` to `M_LB_StormSky`. Read back every parameter override of `MI_NightStormSky` and `MI_Env_NightSky` before and after; they must match.
   - With F = 0 the sky must look unchanged. The lead checks this at the start of P14-4 with the owner present: a capture against the F0 capture, mean absolute difference ≤ 2/255.
2. **Glass.**
   - In `M_LB_StainedGlass` and `_Translucent`, multiply the emissive by `MF_LB_StormFlash(GlassFlashGain, FlashResponse)`. `FlashResponse` is a new scalar, default 1.
   - Set it to 0 on `MI_Glass_Clue_Saints` (puzzle clue glass stays stable) and on any glass MI that F0 finds with no sky behind it.
   - **F0 result:** `MI_Glass_Lancet_B` gets 0. Its only user, `Ch_Glass_Clue_Ext`, faces the passage building, and every outward trace hits at 8.6 m.
   - These keep 1, because the sky is behind them (an outward trace is open, or runs more than 20 m to the backdrop): `MI_Glass_Lancet_A` (`Ch_Glass_N1`, `_N2`, `_S2`, `_S3`), `MI_Glass_Broken` (`Ch_Glass_S1`) and `MI_Glass_East` (`Ch_Glass_E`).
   - `MI_Glass_Clue_Saints` is used only by `BP_StainedGlassClue_Saints`.
3. **Shafts.** `M_LB_LightShaft`: Intensity × `MF_LB_StormFlash(ShaftFlashGain, FlashResponse)`, with `FlashResponse` 1 on all three MIs.
4. **Light pools.** `M_LB_Decal_LightPool`: emissive × `MF_LB_StormFlash(PoolFlashGain, 1)`.
5. **Reveal decals.** `M_LB_Decal_LightningReveal` as in section 5.6(d), with four MIs: `MI_Reveal_Sigil`, `_Tally`, `_Circle`, `_Drag`.
6. **Wind sway.** `MF_LB_WindSway` (`/Game/LastBell/Materials/Functions/`), two modes chosen by a static bool input `bFlutter`.
   - **Bend** (grass, weeds, ferns, shrubs):
     - h = saturate(`PreSkinnedPosition`.z × S / `WindRefHeightCm`), where S = length(Transform(Instance → World, vector (0, 0, 1))) is the instance's world Z scale. `WindRefHeightCm` is a **world** height in cm (after the actor or instance scale). P14-4 wind fix, D-100: `PreSkinnedPosition` is the unscaled mesh-local position, and the plants are placed scaled 1 to 4.8×.
     - Pivot = `TransformPosition(Instance&Particle → World, 0)`.
     - φ = `WindPhase` + dot(Pivot.xy, (0.0031, 0.0047)).
     - s = 0.6·sin φ + 0.4·sin(2φ + 1.3).
     - d = `WindDirection` × `WindStrength` × (0.55 + 0.45 s) × h² × `WindAmplitudeCm`.
     - WPO = d + (0, 0, −0.25 × |d| × h).
   - **Flutter** (ivy leaves):
     - a = saturate(PreSkinnedLocalPosition.y / 20). The wall side is at local Y 0.
     - φ = 3 × `WindPhase` + dot(WorldPosition, (0.05, 0.07, 0.03)).
     - WPO = VertexNormalWS × `WindStrength` × sin φ × a × `WindAmplitudeCm`.
7. **Foliage masters.** In `M_LB_Foliage` and `M_LB_FoliageMasked`:
   - add a static switch `bWind` (default false) feeding `MF_LB_WindSway` into WPO;
   - add scalars `WindAmplitudeCm` and `WindRefHeightCm`;
   - Max WPO displacement: 40 cm (Foliage), 6 cm (Masked).
8. **Foliage MIs:**

Values marked "P14-4 wind fix" replace the P14-2 plan values (shown as old → new); `WindRefHeightCm` is a world height in cm.

| MI | `bWind` | `WindAmplitudeCm` | `WindRefHeightCm` (world cm) |
|---|---|---|---|
| `MI_Foliage_GrassMedium02` | on | 16 → **30** (P14-4 wind fix) | 90 → **60** (P14-4 wind fix) |
| `MI_Foliage_NettlePlant` | on | 9 → **18** (P14-4 wind fix) | 70 → **45** (P14-4 wind fix) |
| `MI_Foliage_WeedPlant02` | on | 6 → **12** (P14-4 wind fix) | 30 (unchanged) |
| `MI_Foliage_Fern02` | on | 10 → **18** (P14-4 wind fix) | 60 → **45** (P14-4 wind fix) |
| `MI_Foliage_WildRooibos` | on | 7 → **14** (P14-4 wind fix) | 80 → **60** (P14-4 wind fix) |
| `MI_Foliage_SearsiaLucida` | on | 5 → **12** (P14-4 wind fix) | 200 → **150** (P14-4 wind fix) |
| `MI_Foliage_Moss01` | off | — | — |
| `MI_Ivy_Green`, `MI_Ivy_Dead` | on (Flutter) | 2.0 → **4** (P14-4 wind fix) | — |

   - Any other `M_LB_Foliage` MI that F0 finds (for example on the `CLA_Garth*` plants) gets amplitude 6 and height 60, listed in the report.
   - **F0 result:** there is none. The two masters have exactly the nine MIs above, and the `CLA_Garth*`, `PSA_Weed_*` and searsia actors use them through their meshes' default slots.
   - The dead tree and its snag stay static: their bark is on `M_LB_Surface` (D-060).
9. **Assets.**
   - `MPC_LB_Storm`: the parameters from section 4, with defaults of 0 and the direction (0.87, 0.5, 0).
   - `DA_StormSettings`: every default in section 5, the MPC soft pointer, and `RandomSeed` 0.
   - Then `DefaultGame.ini` gets the settings path. The P14-1 code reads it.

## 7. Level work (lighting-vfx, [EDITOR], P14-3; `L_Monastery` is saved once at the end, after a census)
1. **Link tags** (actor `Tags`):
   - `LB_StormMoon`: on `DirectionalLight` (`DirectionalLight_1`).
   - `LB_StormMoonSpot`: on `Light_Chapel_Moon_S1/S2/S3/_Roof`, `L_Crypt_Moon_G1/G2/G3` and `L_Tw_MoonSlit_F03/F07/F08`.
   - `LB_StormFill`: on `L_Tw_BellFill`.
   - `LB_StormSky`: on `SkyLight`.
   - `Moon_Fill` gets no tag.
   - **F0:** each of these labels exists exactly once. All 62 placed lights are **Movable**, so no mobility change is needed. No actor carries a storm tag yet.
2. **Zones:** the seven `ALBStormZone` actors from section 5.1.
3. **Post-process restructure:**

| Volume | Change |
|---|---|
| `PP_Cloister` | Shrink to X 6040 … 12040, Y 900 … 3200, Z −40 … 4200; values unchanged |
| `PP_Chapel` (new) | X 6000 … 9100, Y −1550 … 860, Z −40 … 2400; priority 2; blend 200; fixed EV100 **0.65**, the value the nave shows today, so nothing changes until the P14-4 choice |
| `PP_Tower` (new) | X 11990 … 13010, Y 1490 … 2510, Z −40 … 5000; priority 3; blend 200; fixed EV100 **0.65**, the value the tower shows today |
| `PP_Crypt`, `PP_Outdoor_Night`, `PostProcess_Exposure` | Unchanged |

   - The new volumes copy `PP_Cloister`'s metering mode and its satShadows 0.65.
   - **F0:**
     - `PP_Cloister` and `PP_Outdoor_Night` override only `AutoExposureMin/MaxBrightness` and `ColorSaturationShadows`. They don't override `AutoExposureMethod`, so the project default applies. The new volumes do the same: they set min = max EV100 and satShadows 0.65 (0.65, 0.65, 0.65, 1), and nothing else.
     - `PP_Crypt` alone overrides the method (`AEM_Histogram`).
     - No volume overrides `LumenFinalGatherQuality`.
     - Priorities and blends today: unbound `PostProcess_Exposure` 0 / 100; `PP_Outdoor_Night`, `PP_Crypt` and `PP_Cloister` 1, with blend 500, 300 and 300.
   - The agent reads back every volume's bounds, priority and exposure fields.
   - The visual check comes at the start of P14-4, with the owner present: the 19 viewpoints against the F0 set. The mean absolute difference must be ≤ 2/255, except in the chapel south aisle and the sacristy (Y < −450), which today get EV 3. That difference is shown to the owner, not hidden.
4. **State light groups:** the actors in section 8.
5. **Reveal decals:** the five `RV_*` from section 5.6(d), each `DecalComponent` sized as listed.
6. **Apparitions:** `bLightningOnHold` = true on the station of `Apparition_Courtyard`, and on station 0 of `Apparition_Chapel`.
7. **WPO distance:**
   - Set `WorldPositionOffsetDisableDistance` = 4000 on all 312 PCG ISM components and on the static-mesh components of the `CLA_Garth*`, `PSA_Weed_*`, searsia and ivy actors.
   - **F0:** select by material, not by label. The target set is every `StaticMeshActor` whose effective material (override, or the mesh default) is one of the nine foliage MIs: **249 actors**.
     - That is the 175 `CLA_Garth*` plants (including `CLA_GarthShrub_0/1`), the 32 `PSA_Weed_*`, the 4 `Garden_Searsia_*` and **32 ivy actors**.
     - Only 26 of the ivy actors are labelled `Ivy_*`.
     - Today every target has distance 0 (never disabled) and `bEvaluateWorldPositionOffset` true.
     - 80 of the 312 ISM components cast shadows, and every ISM uses shadow-cache invalidation `Auto`.
   - Script it: `Tools/lighting/p14_wpo_distance.py`, with `--apply`, `--check`.
   - Regenerating the PCG volumes resets it; the script note goes into `MCP_NOTES.md`.
8. **Final check:** census the actor count, which must be the F0 count + 23 (7 zones + 9 groups + 2 PP volumes + 5 decals). **F0 count: 2992**, from `find_actors` with an empty name and tag. So the target is **3015**, counted the same way. Then save `L_Monastery` once, and run `--check`.

## 8. Story-driven light changes (`ALBStateLightGroup`)
**Properties:**
- `TArray<TObjectPtr<ALight>> Lights`: placed light actors only. Never a Blueprint light, a puzzle-candle `FlameLight`, the Warden's `TellLight` or the player candle.
- `TArray<TObjectPtr<AActor>> EmissiveActors`: hidden when the mode is Off. These are flame or glow meshes.
- `TArray<FLBLightStateRule> Rules`: in story order; **the last rule whose tag is present wins**. With none present, the mode is On at scale 1.
- `float FadeSeconds` 1.5.

`FLBLightStateRule` fields: `RequiredTag`; `Mode` (On, Dim, Off, Flicker); `IntensityScale` (Dim and Flicker), `FlickerAmount`, `FlickerSpeed`.

**Behaviour:**
- **Base intensities:** recorded per light component at BeginPlay.
- **Instant apply:** BeginPlay and `OnStateReplaced` apply the rule instantly, so a checkpoint load is correct.
- **Live change:** a change through `OnStateChanged` fades over `FadeSeconds`, multiplied by a gutter noise of 0.6 + 0.4 × Perlin(t × 9).
- **Flicker:** scale × (1 − Amount × (0.5 + 0.5 × Perlin(t × Speed + seed))), with the seed from the light's name hash.
- **Ticking:** the actor ticks only while fading or in Flicker.
- **Validation:** a light listed in two groups is an error, logged at BeginPlay and caught by the setup test.

**The changes** (the light labels come from the census; F0 confirms them):

| Group | Lights | Rules (tag → mode) | Seen when |
|---|---|---|---|
| `SLG_Chapel_Altar` | `Light_Chapel_Altar_N`, `_S` | `State.Ritual.1` → Flicker, scale 0.25, amount 0.45, speed 7 | Live, at the altar |
| `SLG_Chapel_Dais` | `Light_Chapel_Statue`, `Light_Chapel_DaisFill` | `State.Ritual.1` → Off | Live |
| `SLG_Crypt_Torches` | `L_Crypt_Torch_T1`, `_T2`, `_T3` (F0) | `State.Ritual.2` → Flicker, scale 0.6, amount 0.45, speed 9 | On the way out |
| `SLG_Crypt_Niches` | `L_Crypt_Candle_Niche_E_WC`, `_N_SC`, `_S_FP`, `_E_CC`, `_S_NC` (90 lm). Emissive actors: `CD_Candles_Niche_E_WC_Flame`, `_N_SC_Flame`, `_S_FP_Flame`, `_E_CC_Flame`, `_S_NC_Flame`, each 9 cm from its light (F0) | `State.Ritual.2` → Off | On the way out |
| `SLG_Cloister_Bells` | `L_Cl_Bells` | `State.Event.CloisterEntered` → Flicker, scale 0.85, amount 0.3, speed 5 | During the hunt |
| `SLG_Cloister_West` | `L_Cl_West` | `CloisterEntered` → Flicker (0.85, 0.3, 5); `State.Ritual.3` → Off | Hunt, then behind you |
| `SLG_Cloister_Entry` | `L_Cl_Entry` | `State.Ritual.3` → Off | Behind you |
| `SLG_Tower_Landings` | `L_Tw_Land4/7/10` | `State.Ritual.3` → Flicker, scale 0.9, amount 0.2, speed 4 | Climbing |
| `SLG_Tower_Bell` | `L_Tw_Bell` | `State.Event.TowerTop` → Flicker, scale 0.8, amount 0.5, speed 8 | At the top |

**F0 findings for the groups:**
- Every listed light exists once and is Movable.
- No flame mesh sits near the torches. Their fire is the Cascade emitters, which stay on in Flicker.
- The altar candles (`Ch_AltarFlame_N1…S3_F`, 46–49 cm) stay visible in Flicker.
- **Lantern glass (open, for the owner).** Seven groups are lantern lights: `L_Cl_Bells`, `_West`, `_Entry`, `L_Tw_Land4/7/10` and `L_Tw_Bell`. Each has its `SM_Wooden_Lantern_01` 42 cm away, and since P11-7 the lantern's glass glows through the mesh-default slot material `MI_LB_LanternGlass_Lit` (unlit emissive `Color`).
  - Hiding a lantern for Off would remove the whole lantern.
  - Leaving it would keep the glass glowing beside a dead light: `L_Cl_West` and `L_Cl_Entry` after Ritual 3. In Flicker the glass stays steady while the light flickers.
  - The decision is recorded in the F0 result: the glass follows the light (section 8.1).

### 8.1 Glow actors (P14-1b, D-099)
**Goal.** A lantern's glowing glass dims, flickers and goes dark together with the light it belongs to. Nothing else about the group changes.

**Code (gameplay-programmer; `Source/LastBell/Storm/LBStateLightGroup.h/.cpp`):**
1. **New properties,** in category "Light Group":
   - `TArray<TObjectPtr<AActor>> GlowActors`;
   - `FName GlowParameter = TEXT("Color")`, the vector parameter to scale.
2. **BeginPlay, after the base intensities are recorded:**
   - For each glow actor, go through every `UMeshComponent` on it and every material index.
   - Keep the indices whose material reports the vector parameter: `UMaterialInterface::GetVectorParameterValue(FHashedMaterialParameterInfo(GlowParameter), Value)` returns true.
   - For each kept slot, call `CreateDynamicMaterialInstance(Index, Material)` and record the MID with its base value.
   - Pair the glow actor with the nearest light in `Lights` (distance between actor locations, measured once at BeginPlay).
   - If a glow actor has no such slot, log one warning naming the actor and the parameter, and skip it.
3. **Every time the group writes a light's intensity** (instant apply, fade, flicker), scale the paired glow slots:
   - s = current intensity ÷ that light's base intensity, clamped to [0, 1]; s = 0 when the base is 0.
   - Value = (base.R × s, base.G × s, base.B × s, base.A).
   - So Off gives black glass, Dim gives the dim scale, Flicker flickers with its own light, and On gives the base value.
4. **Instant apply** on BeginPlay and `OnStateReplaced` sets the glass too, so a checkpoint load is right on the first frame.
5. **Validation:** a glow actor listed in two groups is an error, logged at BeginPlay like a duplicated light.
6. **No other changes:**
   - The tick rule (only while fading or flickering) is unchanged.
   - `EmissiveActors` still hide on Off; the two lists are independent.
   - There are no hard asset references in game code.

**Tests:**
- **New functional test `LastBell.Functional.Storm.StateLightGroupDrivesGlow`** (`L_Test_Warden`). Setup: spawn a point light (Movable, 300 lm) and a `StaticMeshActor` with `/Game/LastBell/ArtTest/Props/Wooden_Lantern_01/SM_Wooden_Lantern_01`, loaded by path in the test only, 40 cm away. Its glass slot defaults to `MI_LB_LanternGlass_Lit` (`M_LB_UnlitEmissive`, `Color`). Then spawn a group with `Lights` = [light], `GlowActors` = [lantern] and one rule `State.Ritual.2` → Off. The test checks:
  1. without the tag, the glass MID `Color` equals the MI's base value (within 1 %);
  2. after `ULBWorldStateSubsystem::AddState(State.Ritual.2)` and the fade (1.5 s + 0.5 s), `Color` RGB ≤ 1 % of base;
  3. after `ReplaceState` without the tag, the value is back to base on the next frame;
  4. with a Flicker rule (scale 0.8, amount 0.5, speed 8), every sample over 2 s lies within [base × 0.4, base × 0.8], and the samples are not all equal.
- **Extend `Monastery.StormSetup`:** every group's `GlowActors` resolve at least one glow slot, and no glow actor is in two groups.

**Level assignment (P14-3).** Each glow actor is the lantern 42 cm from its group's light (F0):

| Group | `GlowActors` |
|---|---|
| `SLG_Cloister_Bells` | `CLA_Lantern_Bells` |
| `SLG_Cloister_West` | `CLA_Lantern_West` |
| `SLG_Cloister_Entry` | `SHA_Lantern_Entry` |
| `SLG_Tower_Landings` | `TWA_Lantern_Land4`, `TWA_Lantern_Land7`, `TWA_Lantern_Land10` |
| `SLG_Tower_Bell` | `TWA_Lantern_Bell` |

The chapel and crypt groups get no glow actors: their flames are separate meshes in `EmissiveActors`, or Cascade fires.

**Acceptance:**
- the real-project build is clean;
- the full suite passes, except the expected `Monastery.StormSetup` failure until P14-3;
- in P14-5, the owner sees the west and entry lanterns dark after `State.Ritual.3`.

**Readability fallback:** if a critical-path viewpoint fails its floor (section 9.3) after its change, change that group's Off to Dim at scale 0.3, or a Flicker scale to +0.2. Then record it in DECISIONS.

## 9. Lighting pass
### 9.1 Look session (owner and lead, P14-4)
**1. Flash preset (live in PIE).**
- The owner stands at three spots and fires `lb.Storm.Flash` a few times: `cy_west_front_15m`, `ch_tall_east_15m` and `cl_tall_north_15m`.
- Meanwhile the lead switches `DA_StormSettings` between presets A, B and C (section 5.4) over MCP.
- The owner picks one, or asks for values in between.
- The lead checks the Lumen smear (R-59).

**2. Chapel exposure.** Three captures each of `ch_tall_east_15m` and `ch_sacristy_3m`:
- EV100 0.65 (today's nave);
- 1.6 (middle);
- 3.0 (the P8 look).

The owner picks one value for the whole chapel.

**3. Grade.** Six viewpoints (`cy_west_front_15m`, `ch_tall_east_15m`, `cr_tall_ossuary_15m`, `cl_tall_north_15m`, `tw_mid_stair`, `tw_belfry`) × three grades, on the PIE-world `PostProcess_Exposure`. Never saved in this step.

| Setting | A, current | B, storm teal | C, bleak |
|---|---|---|---|
| ColorSaturation (RGBY) | unchanged | (0.92, 0.95, 1.0, 0.85) | (1, 1, 1, 0.70) |
| ColorContrast (Y) | unchanged | 1.06 | 1.10 |
| ColorGammaShadows | unchanged | (0.97, 1.0, 1.06, 1) | (0.98, 1.0, 1.03, 1) |
| ColorGainHighlights | unchanged | (1.04, 1.0, 0.94, 1) | (1.06, 1.0, 0.92, 1) |
| FilmGrainIntensity | 0 | 0.18 | 0.25 |
| VignetteIntensity | unchanged | 0.45 | 0.55 |

For B and C, the per-area satShadows overrides are cleared, because the grade lives on the global volume only.

**4. Wind.** The owner watches the courtyard and the garth in PIE at intensity 0.6 and 1.0 (`lb.Storm.Intensity`). Too much, too little, or right; plus any pop at 40 m.

**5. R-31.** A capture from `p14_cy_tower_reveal` [600, 0, 170, 14, 9.5]; F0 confirms the tower top is in the frame.
- **F0:** vertical traces put the tower's top collision at Z 3540. The top centre is 0.0° right of the view centre and 1.5° above it, inside a 90° frame at both 16:9 and the portrait capture.
- The line-of-sight trace first hits at 11 995 cm, at the tower's west face (X ≈ 11 990), so nothing stands in between.
- R-31 closes if the tower's median luma ≤ the median luma of the surrounding sky.
- Otherwise the cause is reported, with no fix in this phase without a decision.

### 9.2 Apply (lighting-vfx, P14-5)
Apply the chosen preset, chapel EV and grade, then save `DA_StormSettings` and `L_Monastery` once each.

**R-09** (noise and leaks), from the viewpoint captures. Fix only what blocks approval, in this order:
1. That area volume's `LumenFinalGatherQuality` 1 → 1.5 (re-measure the GPU);
2. a hidden-in-game, shadow-only blocker at a leak, `SM_LB_LeakBlocker`: a kit cube with `bHiddenInGame`, `CastShadow`, lighting channel 0;
3. otherwise report it.

### 9.3 Exposure targets and readability floor
**Method:**
- Captures in PIE Simulate, run by the lead with the owner present, at the section 10 viewpoints.
- Before them, the lead sets `DebugFreezeFlash` 0 on `DA_StormSettings` (no flash) over MCP.
- They use the player candle proxy (`capture_poses.py --light`) and are written to `Docs/ArtTest/lighting/`.
- Metrics from `Tools/crypt/luma_report.py`:
  - **mean:** mean luma;
  - **central:** the central 40 % mean.

| Area | Mean luma target | Central-40 % floor |
|---|---|---|
| Courtyard | 0.04 – 0.07 (D-058) | ≥ 0.025 |
| Chapel | set by the P14-4 choice (the value at the chosen EV) ± 20 % | ≥ 0.030 |
| Crypt | 0.025 – 0.05 | ≥ 0.020 (the candle leads) |
| Cloister | 0.04 – 0.07 | ≥ 0.025 |
| Tower | 0.035 – 0.06 | ≥ 0.025 |

**Adjustments:**
- Exposure is adjusted only through the area's EV100, in steps of 0.25.
- After the story changes: the same captures again, with the tags added. MCP has no console, so **the owner types** `lb.State.Add <tag>` in the Output Log's Cmd box when the lead asks, between capture batches: `State.Ritual.1`, then `State.Ritual.2`, then `State.Event.CloisterEntered` and `State.Ritual.3`, then `State.Event.TowerTop`.
- Each floor must still hold; otherwise apply the section 8 fallback.

## 10. Viewpoints for the owner's approval (P14-6)
Pose format: [x, y, z, pitch, yaw]. The file is `Tools/lighting/poses/p14_viewpoints.json`; the names come from `p11_poses.json` unless new.

| Area | Viewpoints |
|---|---|
| Courtyard | `cy_west_front_15m`, `cy_tall_north_15m`, `cy_lantern_gate_3m` |
| Chapel | `ch_tall_east_15m`, `ch_candle_altar_3m`, `ch_sacristy_3m` |
| Crypt | `cr_tall_ossuary_15m`, `cr_chain_chamber`, `cr_torch_t1_3m` |
| Cloister | `cl_tall_north_15m`, `cl_lantern_bells_3m`, `ps_lantern_joints` |
| Tower | `tw_mid_stair`, `tw_belfry`, new `tw_base` [12200, 2000, 170, 5, 0] |
| Storm moments (`DebugFreezeFlash` 0.8) | `p14_cy_tower_reveal`, `ch_tall_east_15m`, `cl_tall_north_15m`, `tw_belfry` |

**Capture:** 19 images, about 12 minutes, with the owner present and Unreal in front.

**Pose file:** `Tools/lighting/poses/p14_viewpoints.json`, 16 unique poses: the 14 from `p11_poses.json`, `tw_base` and `p14_cy_tower_reveal`.
- The four storm moments reuse four of these poses with the flash frozen.
- So the P14-B "before" set has 16 images: PIE Simulate, no candle proxy, the same method as the P11 captures. It is taken with `capture_session.py --prefix p14b_` into `Docs/ArtTest/lighting/before/`.

**Then a PIE run-through of the storm beats (owner, about 15 minutes):**
1. Arrival: look at the tower.
2. `lb.State.Add State.Ritual.1` at the altar: the strike, the light changes, the apparition flash.
3. Crypt `State.Ritual.2`.
4. Cloister `State.Event.CloisterEntered`, then the Warden reveal in the garth.
5. `State.Ritual.3`.
6. `State.Event.TowerTop`.

## 11. Performance (owner; standard spots fixed from now on)
Each spot is reached in PIE with `BugItGo X Y Z Pitch Yaw Roll`.

| Spot | `BugItGo` |
|---|---|
| Courtyard | `BugItGo 4500 0 170 12 0 0` |
| Chapel | `BugItGo 7400 0 170 15 0 0` |
| Crypt ossuary | `BugItGo 7400 -2350 -440 8 0 0` |
| Cloister bells | `BugItGo 11700 2380 170 5 0 0` |
| Tower mid-stair | `BugItGo 12835 1665 1534 10 180 0` |
| Belfry | `BugItGo 12500 2150 2670 25 -135 0` |

**Readings:** at each spot, `scalability 2`, `r.SetRes 1920x1080w`, `stat unit` and `stat gpu`, with a screenshot (`shot showui`) per reading.
- Every reading, P14-B and P14-7 alike, starts with `lb.Warden.Enabled 0`, so the Warden can't end a reading.
- The owner types `lb.Warden.Enabled 1` afterwards.
- The editor already runs at High (F0: every `sg.*` is 2 and `sg.ResolutionQuality` is 87), so `scalability 2` changes nothing there.

- **P14-B (baseline, before any change):** one reading per spot. About 10 minutes, in the F0 session.
- **P14-7:**
  - one reading per spot with `lb.Storm.Intensity 1` (flashes running) and the wind on;
  - at the courtyard and the chapel, a second reading with `lb.Storm.Enabled 0`;
  - about 15 minutes.

**Pass:** GPU ≤ 16.6 ms; each spot's GPU ≤ its P14-B value + 0.6 ms; and each spot's game thread ≤ its P14-B value + 0.3 ms.

**If the courtyard fails** (wind WPO and VSM, R-60), go down this ladder, re-measuring after each step:
1. `ShadowCacheInvalidationBehavior` = Rigid on the shadow-casting `GrassMedium02` ISM components;
2. disable distance 4000 → 2500;
3. cast shadows off on `GrassMedium02`.

The performance-engineer reads the screenshots and logs, and writes the `PERFORMANCE_BUDGET.md` rows.

## 12. Tests (gameplay-programmer, P14-1; the suite grows from 112)
**Unit tests** (`Source/LastBellTests/Tests/LBStormTests.cpp`, `LB_TEST_FLAGS`, prefix `LastBell.Storm.`):
1. `Logic.StoryIntensity`: the last present entry wins; no entry gives the default; tags out of order still give the highest-index present entry.
2. `Logic.FlashEnvelope`:
   - Sheet values at t = 0, 0.04, 0.12, 0.43 and the end;
   - Double has 2 peaks, and the maximum ≤ 1 × brightness;
   - every profile ends at its formula time;
   - F ≥ 0 everywhere.
3. `Logic.Schedule`: the interval bounds at I = 0, 0.5 and 1; seed 1401 gives the same sequence twice; the minimum gap is respected.
4. `Logic.Wind`: strength in [0, 1]; the mean over 60 s rises with I; the phase is continuous across the wrap (no step > 0.1 rad at 60 fps).
5. `Logic.Exposure`: highest priority wins; ties take the lowest exposure; no zone gives the default.
6. `Logic.RevealRule`: each condition false on its own gives no reveal; all true gives a reveal.
7. `Logic.LightRules`: the last present rule wins; none gives On ×1; Off gives 0; Dim gives the scale; Flicker stays within [scale × (1 − amount), scale].

**Functional tests** (PIE, `LastBell.Functional.Storm.`; `L_Test_Warden` unless stated):
1. `FlashDrivesLightsAndMPC`:
   - spawn a tagged directional light and spot, then `RefreshLinkedLights()`, then `RequestFlash(1, 0, Debug, Sheet)`;
   - at the peak, the moon ≥ base + 0.9 × `FlashLux`, the spot ≥ base × (1 + 0.9 × gain), and MPC `LightningFlash` ≥ 0.9;
   - 2 s later, all are back within 1 %.
2. `IntensityFollowsStory`: adding `State.Ritual.2` moves the target to 0.65 and the intensity rises at 0.02/s; `ReplaceState` with `CloisterEntered` snaps to 0.8.
3. `ScriptedStrikeOnTagOnly`: adding `State.Ritual.1` flashes within 1.2 + 0.3 s; `ReplaceState` containing it gives no flash in 3 s.
4. `WardenRevealFlash`:
   - a zone at exposure 1 and a visible Warden 2000 cm ahead, with the stage forced to 3, gives a reveal within 1.5 s;
   - the same behind a wall gives none in 3 s;
   - a second reveal is blocked inside the cooldown.
5. `StateLightGroupFollowsTags`:
   - an added tag gives 0 after the fade;
   - `ReplaceState` without the tag restores the base instantly;
   - with the tag present at BeginPlay, the light is off on the first frame.
6. `ApparitionHoldRequestsFlash`: an apparition with `bLightningOnHold` flashes on entering Hold.
7. `Monastery.StormSetup` (`L_Monastery`):
   - exactly one `LB_StormMoon`;
   - 10 `LB_StormMoonSpot`, 1 `LB_StormFill`, 1 `LB_StormSky`;
   - 7 zones;
   - 9 light groups, each light valid and in one group only;
   - `DA_StormSettings` loads with both debug fields at −1;
   - the MPC has every parameter;
   - both apparitions have `bLightningOnHold`.

## 13. Tasks
| Task | Scope | Owner | Needs | Depends on |
|---|---|---|---|---|
| P14-0 | Plan approval; D-096 (storm), D-097 (light changes), D-098 (lighting pass method); R-59…R-63; `IMPLEMENTATION_PLAN.md` Phase 14 table; Phase 15 listed as particles | lead + owner | — | — |
| F0 | Survey: dump every light, PP volume, sky MI chain and its parameters, glass, shaft and pool actors with their MIs, foliage MIs, the ISM count and WPO settings, `CLA_Garth*` bounds, flame meshes near the group lights, the five decal surface points (trace), the torch and niche light labels, and the tower-reveal pose check. Output `Docs/ArtTest/lighting/p14_f0_inventory.json` + `p14_f0_tables.md`; this plan's open values are filled from it | lead [EDITOR read-only] | Unreal open | P14-0 |
| P14-B | Baseline readings at the six spots (section 11), plus the "before" capture set: the 19 section 10 viewpoints, run by the lead with the owner present | **owner**, about 25 min in all (readings 10, captures about 12) | Unreal in front | P14-0 (same session as F0) |
| P14-1 | Section 4, 5 and 8 code, console commands, `ULBGameSettings` field, the apparition flag, section 12 tests | gameplay-programmer | **Unreal closed** for the real build | P14-0 |
| P14-1b | Section 8.1 glow actors (D-099) and their tests | gameplay-programmer | **Unreal closed** for the real build | F0 |
| P14-2 | Section 6 materials and assets | technical-artist [EDITOR] | Unreal open | P14-1 (needs the classes), F0 |
| P14-3 | Section 7 level work, plus the section 8.1 glow actors | lighting-vfx [EDITOR] | Unreal open | P14-1b, P14-2 |
| P14-4 | Look session (section 9.1) | lead + **owner**, about 30 min (captures about 12 min) | Unreal in front | P14-3 |
| P14-5 | Apply the choices, exposure targets, story-change readability captures, R-09 fixes | lighting-vfx [EDITOR]; captures with the owner | | P14-4 |
| P14-6 | Viewpoint approval and storm run-through (section 10) | **owner** (about 30 min) | | P14-5 |
| P14-7 | Performance (section 11), report | **owner** + performance-engineer | | P14-6 |
| P14-8 | QA (qa-reviewer), docs (TECHNICAL_DESIGN "Storm and light", MCP_NOTES, PERFORMANCE_BUDGET, RISKS), the full suite, playtest; "PHASE 14 READY FOR YOUR REVIEW" | qa-reviewer, lead, owner | Unreal closed for the suite | all |

One editor agent at a time. Each agent commits on this branch only and never switches, merges or pushes.

## 14. Risks (added to `RISKS.md` at P14-0)
| Id | Risk | Mitigation |
|---|---|---|
| R-59 | Lumen's bounce light lags the flash, so the flash smears or lingers | The direct light carries the flash; `SkyFlashGain` → 0 fallback; judged live in P14-4 |
| R-60 | Wind WPO costs GPU through VSM invalidation by shadow-casting grass (D-060 estimated +0.3–1.5 ms) | 40 m disable distance; the section 11 ladder; measured against P14-B |
| R-61 | Story light changes make critical paths unreadable | Readability floors measured after each change; the Dim fallback |
| R-62 | The Warden reveal flash makes stealth easier | Only in exposed spaces, 30 s cooldown, the `bRevealEnabled` switch; judged in the owner's playtest |
| R-63 | The exposure restructure changes looks the owner already approved (chapel nave 0.20 against the P8 0.10) | No change until the owner picks in P14-4; before and after captures |

**Updates:** R-09 is closed by P14-5/P14-6. R-31 is updated: its lights are gone, and it closes by the P14-4 measurement.

## 15. Not in this phase
- **Phase 15 (particles):** rain, splashes, drips, puddle ripples, dust and mist particles, visible lightning bolts (Niagara), candle-flame effects, cloth (tower cloth, banners).
- **Phase 16:** thunder and all audio. `OnLightningFlash` is the hook.
- **Not done here:**
  - Granting `State.Warden.Stage.6` and the tower Warden spawn: a Phase 17 (finale) question, reported to the owner.
  - Dead-tree twig sway: it would need a new bark master.
  - Player-candle snuff beats.
  - Scalability menus (Phase 18).
  - Any change to AI timing or behaviour.

## Results

### P14-1 result (da7d195, 2026-11-07)
**Built:**
- `Source/LastBell/Storm/`: `LBStormTypes.h`, `LBStormLogic`, `ULBStormSettings`, `ULBStormSubsystem`, `ALBStormZone`, `ALBStateLightGroup`;
- the apparition's `bLightningOnHold`;
- `ULBGameSettings::StormSettings`;
- `lb.Storm.Flash`, `lb.Storm.Intensity` and `lb.Storm.Freeze`, plus the CVars `lb.Storm.Enabled` and `lb.Storm.Debug`.

**Real-project suite:** 125 passed, 1 failed, 0 invalid tags. The failure is `Functional.Storm.Monastery.StormSetup`, expected red until P14-2 and P14-3; its messages list what's missing.

**Notes for the editor tasks:**
- **Tag arrays:** `StoryIntensity` and `ScriptedStrikes` are empty by default. Call `FillPlanTagDefaults()` (CallInEditor) when creating `DA_StormSettings`, then add the `StormSettings=` line to `DefaultGame.ini`.
- **Light mobility:** `SetIntensity` does nothing on a **Static** light. F0 must report the mobility of every tagged and grouped light. Any Static one is made Movable in P14-3, recorded, and its cost checked.
- **Sky light:** handled as a `USkyLightComponent`, because `ASkyLight` isn't an `ALight`.
- **Look gate:** a view-cone check only, with no trace, so the tower itself can't block it. Accepted.
- **`WardenRevealFlash`:** runs with `lb.Warden.Enabled 0` and `SetDormantPresentation(false)`, on its own floor and wall. Accepted: it isolates the rule from the brain.
- **Monastery tests:** once the storm is active in `L_Monastery` (after P14-3), the existing Monastery tests run with ambient flashes. That's harmless, but watch it.

### F0 result (survey, 2026-11-07)
**Method.** `Tools/lighting/p14_f0_survey.py` made 4506 read-only editor calls in 25 minutes (the editor was in the background, about 0.33 s per call). `L_Monastery` was clean before and after, with 0 call errors.
- Raw data: `Docs/ArtTest/lighting/p14_f0_inventory.json`.
- Tables: `p14_f0_tables.md`, from `Tools/lighting/p14_f0_tables.py`.
- The values it fixed are written into sections 5.1, 5.6(d), 6, 7, 8, 9.1, 10 and 11 above, each marked "F0".

**Facts:**
- **Actors:** 2992, so the P14-3 target is 3015. No storm tags exist yet, and none of the new labels (`SZN_`, `SLG_`, `RV_`, `PP_Chapel`, `PP_Tower`) is taken.
- **Lights:** 62 placed, all **Movable**. Every label the plan names exists exactly once. The only Blueprint lights are the 4 puzzle-candle `FlameLight`s and the Warden's `TellLight`, and none of them is grouped.
- **Post-process:** as in section 3, with the details in section 7.3.
- **Sky:** `SkySphere` → `MI_Env_NightSky` → `MI_NightStormSky` → `M_Sky_Panning_Clouds2`. Both MIs' overrides are listed in the tables, for the P14-2 read-back.
- **Glass:** 7 actors on 4 MIs, plus `BP_StainedGlassClue_Saints`. `FlashResponse` is 0 on `MI_Glass_Clue_Saints` and `MI_Glass_Lancet_B` and 1 on the rest (section 6.2).
- **Shafts:** 11 actors.
  - The chapel has 3 `MI_LightShaft_Window` shafts and 1 `MI_LightShaft_Roof` shaft.
  - The crypt and tower have 7 `Cylinder` cards on `MI_LightShaft_Crypt`, a child of `MI_LightShaft_Roof`.
  - P14-2 sets `FlashResponse` 1 explicitly on all three MIs.
- **Pools and chalk:** 4 pool decals on `MI_Decal_LightPool_Lancet` (`Ch_Pool_S1/S2/S3/Roof`), and 4 existing chalk decals.
- **Foliage:**
  - 9 MIs, and no others.
  - 249 placed actors on them.
  - The PCG has 312 ISM components with 2248 instances, 80 of them shadow-casting.
  - WPO disable distance is 0 everywhere (section 7.7).
- **Garth zone:** X 10245–11460, Y 1345–2260, from the 175 plants.
- **Apparitions:** `Apparition_Courtyard` and `Apparition_Chapel` have one station each; `bLightningOnHold` is false on both.
- **Tower reveal pose:** confirmed (section 9.1).
- **Viewpoints:** all 14 named poses exist; the pose file is written (section 10).
- **Editor scalability:** already High.

**Lantern glass in the light groups (section 8): decided 2026-11-07.** Of the three options offered, the owner chose **"glass follows the light"** (D-099). The other two were hiding the lantern for Off, or using Dim 0.3 instead of Off on lantern groups.
- This adds task **P14-1b**: the `GlowActors` addition to `ALBStateLightGroup`.
- It runs before P14-3, with Unreal closed for the build. The spec is in section 8.1.

### P14-B result (owner's readings, 2026-11-07)
**Method.** Section 11, on c626dd7 (no level change since Phase 13): PIE new window, High, render 1671x853 (87 %), `stat unit` + `stat gpu`, player candle in view.
- The log confirms the Warden stayed dormant for all six readings; it switched to Patrol only at `lb.Warden.Enabled 1`.
- The owner played through between readings (two `lb.NewGame`), so each spot was read in that spot's own story state.
- Screenshots: `Docs/ArtTest/lighting/perf/p14b_perf_1..6_*.png`, plus `p14b_perf_1b_courtyard_reread.png`.
- The objective on screen is listed per reading. The storm follows the story, so P14-7 reads each spot at the same objective.

| Spot | Objective on screen | GPU (ms) | Graphics avg / max | Compute avg | Game (ms) | Frame (ms) | Draws | Prims | VRAM (GB) |
|---|---|---|---|---|---|---|---|---|---|
| Courtyard (re-read, **baseline**) | Find a way to turn the winch | **13.12** | 13.16 / 14.02 | 4.66 | 13.30 | 16.67 | 745 | 336.9K | 4.03 / 4.97 |
| Courtyard (first reading, void) | Find a way into the chapel | 11.78 | 11.76 / 13.27 | 4.25 | 25.06 | 22.80 | 708 | 66.4K | 3.37 / 5.03 |
| Chapel | Light the candles in the order of the saints | **14.49** | 14.21 / 14.91 | 4.81 | 13.04 | 16.70 | 667 | 343.7K | 3.84 / 4.97 |
| Crypt ossuary | Find a way to turn the winch | **13.10** | 13.12 / 14.03 | 4.96 | 8.34 | 16.67 | 464 | 148.6K | 3.42 / 5.03 |
| Cloister bells | Strike the bells in the inscribed order | **12.86** | 12.65 / 13.25 | 5.73 | 8.06 | 16.67 | 280 | 57.2K | 3.48 / 5.03 |
| Tower mid-stair | Climb the bell tower | **12.21** | 11.88 / 12.34 | 5.65 | 8.31 | 16.67 | 436 | 63.5K | 3.48 / 5.03 |
| Belfry | Ring the bell | **11.55** | 11.17 / 11.98 | 5.49 | 8.02 | 16.67 | 225 | 26.0K | 3.50 / 5.03 |

- **Key passes, chapel:** RenderDeferredLighting 4.26, Lights 3.12, Postprocessing 2.74, TSR 2.07, Shadow Depths 1.27, Nanite BasePass 1.11, Shadow Projection 1.00; compute LumenScreenProbeGather 2.40.
- **Key passes, courtyard:** RenderDeferredLighting 3.08, Postprocessing 2.32, Lights 1.94, TSR 1.72, Shadow Depths 1.22, Shadow Projection 1.14, Nanite BasePass 1.09, VolumetricFog 0.23; compute LumenScreenProbeGather 1.97.
- **P14-7 limits** (section 11: GPU baseline + 0.6 ms and never over 16.6; game thread baseline + 0.3 ms):

  | Spot | GPU limit (ms) | Game-thread limit (ms) |
  |---|---|---|
  | Courtyard | 13.72 | 13.60 |
  | Chapel | 15.09 | 13.34 |
  | Crypt ossuary | 13.70 | 8.64 |
  | Cloister bells | 13.46 | 8.36 |
  | Tower mid-stair | 12.81 | 8.61 |
  | Belfry | 12.15 | 8.32 |

  The smallest headroom to 16.6 ms is the chapel's, 2.11 ms.
- **The first courtyard reading is void.** It was the session's first reading: game thread 25.06 ms, frame 22.80, and only 66.4K prims against 336.9K a few minutes later. The scene hadn't settled. The owner re-read the spot (render 1664x846, the window a few pixels smaller), and that re-read is the courtyard baseline.
- **Warden CVar after the re-read:** the owner's closing command was `lb.Warden.Enabled 0`, so the Warden stays disabled until `lb.Warden.Enabled 1` or an editor restart. The "before" capture set ran in that state.

**"Before" capture set (2026-11-07):** `capture_session.py --prefix p14b_ --mode simulate --fg-wait 180`, no candle proxy.
- Result: 16 of 16 saved, 0 missing, render 1331x808. Files are in `Docs/ArtTest/lighting/before/`, with luma in `p14b_luma.json`.
- Timing: the tool waited 1248 s for the editor to come to the front, then captured all 16 in about 6 minutes. 18 attempts failed and were retried, the most (4) at `tw_belfry`.
- Lead review:
  - every view is framed as named;
  - `p14_cy_tower_reveal` shows the tower roof and its window above the chapel gable, dark against the clouds (the R-31 target);
  - `tw_base` frames the tower-base wall at close range. It is kept for before/after comparability: the lantern's light on that wall still measures the group state.
- Luma means range from 0.012 (`cr_tall_ossuary_15m`, 91 % of pixels below 0.02) to 0.214 (`cy_lantern_gate_3m`). They are the reference for P14-6/P14-7.
- **Also on screen:** "PROFILING WITH AI LOGGING ON!", the editor's usual AI-logging note. It was on in the earlier readings too, so they stay comparable.

### P14-1b result (glow actors, D-099, 2026-11-07)
**Built (`Source/LastBell/Storm/`):**
- `ALBStateLightGroup::GlowActors` and `GlowParameter` (default `Color`), as in section 8.1.
- `LBStormLogic::ScaleGlow(Base, Current, BaseIntensity)`, the pure scaling maths.
- At BeginPlay, after the base intensities are recorded:
  - every `UMeshComponent` slot on a glow actor whose material reports the vector parameter gets its own dynamic instance (`CreateDynamicMaterialInstance`);
  - the glow actor is paired with the nearest light of the group, by actor location, measured once.
- `WriteScale` also writes the paired slots, so instant apply (BeginPlay, `OnStateReplaced`), fade and flicker all drive the glass.
- Nothing else changed: the tick rule, `EmissiveActors` and the lights' behaviour are as before.

**Warnings (`LogLB`):**
- A glow actor with no matching slot, or in a group with no valid light, logs one warning naming the group and the actor, and is skipped.
- A glow actor listed in two groups logs a warning at BeginPlay, like a duplicated light.
- A null entry in `GlowActors` is skipped silently.

**Tests, real-project suite via `Tools/build_and_test.ps1`: 127 passed, 1 failed, 0 invalid tags.**
- The build is clean, with no warnings in the touched files.
- The failure is `Functional.Storm.Monastery.StormSetup`. It is expected, and stays red until P14-2 and P14-3.
- New tests:
  - `LastBell.Storm.Logic.ScaleGlow`: On, Off, Dim 0.3, base 0, current above base, alpha kept.
  - `LastBell.Functional.Storm.StateLightGroupDrivesGlow`, on `L_Test_Warden`, with the real `SM_Wooden_Lantern_01` (Static component) and its glass slot 1 (`MI_LB_LanternGlass_Lit`, base Color 1.7, 0.765, 0.17, 1.0):
    - the glass equals its base without the tag;
    - after Ritual.2 and the 2 s wait it is black;
    - after `ReplaceState` without the tag it is back at base on the next frame;
    - in an instant Flicker (0.8, 0.5, 8) it stayed within [0.4, 0.8] of the base over 121 samples, with the brightest channel ranging 0.683 to 1.290 of a 1.7 base.
- `Monastery.StormSetup` now also checks that every group's `GlowActors` entries resolve at least one glow slot and that no glow actor is in two groups. It is a no-op while there are no groups.

**Not validated:** nothing in the real `L_Monastery` is checked (no glow actors are assigned there yet). Whether the glass really goes dark beside a dead light is for P14-3 and P14-5, by eye.

**Notes for P14-3:**
- Assign `GlowActors` from the table in section 8.1 (`CLA_Lantern_Bells`, `_West`, `SHA_Lantern_Entry`, `TWA_Lantern_Land4/7/10`, `TWA_Lantern_Bell`).
- Leave `GlowParameter` at `Color`.
- Each glow actor must be nearer to its own group's light than to any other light of that group. Pairing is per group, so the lantern 42 cm from the group's light is right.
- Every slot of a glow actor whose material has `Color` is driven, not only the first. The test only inspects slot 1 (the first such slot of `SM_Wooden_Lantern_01`); I did not check whether other lantern slots also have `Color`.
- The group makes the dynamic instances at runtime only (PIE and game). Nothing is saved to the level.
- A glow actor's component can stay Static: `CreateDynamicMaterialInstance` works on it at runtime.
- In the test, `SpawnActorDeferred` has already registered a `StaticMeshActor`'s component. To set a mesh on a Static component, unregister it, call `SetStaticMesh`, then register it again.

### P14-2a result (materials and assets, 2026-11-07)
**Made (no level change; no captures, no PIE; `L_Monastery`, `M_LB_Surface` and every listed Blueprint stayed clean):**
- `MPC_LB_Storm`: the 12 scalars (default 0) and `WindDirection` (0.87, 0.5, 0, 0), `FlashDirection` (0, 0, 1, 0), `FlashTint` (0.75, 0.82, 1, 1). Every name matches the `P...` constants in `LBStormSubsystem.cpp` exactly (checked one by one); there was no difference.
- `MF_LB_StormFlash` (exposed to the library, category LastBell): `Mul` = 1 + `Gain` x MPC `LightningFlash` x `Response` (`Response` defaults to 1).
- `DA_StormSettings` (class `ULBStormSettings`).
- `M_LB_StormSky`: the engine sky material with the emissive formula of 6.1.
- Glass: `FlashResponse` and the flash multiplier in both glass masters. Shafts: `FlashResponse` and the multiplier on `Intensity`. Pools: the multiplier on the emissive.
- `M_LB_Decal_LightningReveal` and `MI_Reveal_Sigil`, `_Tally`, `_Circle`, `_Drag`.
- `Config/DefaultGame.ini`: `StormSettings=/Game/LastBell/Data/DA_StormSettings.DA_StormSettings` under `[/Script/LastBell.LBGameSettings]` (CRLF kept, no BOM, no second header).

**`DA_StormSettings`:**
- All 63 numeric and bool fields were read back and compared with section 5 (preset B): **0 mismatches**. `RandomSeed` 0, `DebugFreezeFlash` and `DebugIntensityOverride` -1, `Collection` = `MPC_LB_Storm`, `FlashTint` and `WindDirection` as in 5.4 and 5.5.
- **The arrays were set by hand, not by `FillPlanTagDefaults`:** MCP has no tool that calls a UFUNCTION. They mirror the function's code: 8 `StoryIntensity` steps (section 5.2); 6 `ScriptedStrikes` (5.6b), with spacing 0 for the single strikes. CourtyardEntered has the look gate (`LookTarget` (12500, 2000, 3800), cone 20, timeout 90). TowerTop has `ProfileOverrides` Double, Triple, Double. Read back before the save and again after the editor restart.
- The `ULBGameSettings` default object: set in memory through MCP first (it works, read back); after the editor restart it read `StormSettings` from the ini. So P14-3 needs no restart.

**Sky.**
- Emissive = original x (1 + `DomeFlashGain` x F x Hot) + `FlashTint`.rgb x F x Hot x `DomeFlashAdd`, with Hot = 0.3 + 0.7 x saturate(dot(-CameraVector, `FlashDirection`.xyz))^6. The original emissive is `Multiply_1` (`Multiply_34` x 1.5); the new nodes wrap it.
- **F = 0:** F x Hot = 0, so the first factor is exactly 1 (gain x 0 + 1) and the added term is exactly 0 (tint x 0 x `DomeFlashAdd`). The emissive equals the original bit for bit; Hot is finite for every input.
- `MI_NightStormSky` and `MI_Env_NightSky`, before and after the reparent (identical):

| MI | Parent before -> after | Overrides |
|---|---|---|
| `MI_NightStormSky` | `M_Sky_Panning_Clouds2` -> `M_LB_StormSky` | 8 scalars (Stars brightness 0, Cloud opacity 1, Cloud speed 0.02, NoisePower1 1.2, NoisePower2 5, Sun brightness 6, Sun Radius 0.004, Horizon Falloff 1.5), 6 vectors (Overall Color, Cloud color, Zenith Color, Horizon color, Sun color, Light direction): **same** |
| `MI_Env_NightSky` | `MI_NightStormSky` (unchanged) | 4 scalars (Cloud opacity 1, NoisePower2 2, Sun brightness 2, Sun Radius 0.02), 4 vectors (Cloud color, Horizon color, Zenith Color, Overall Color 0.45): **same**; not dirty, not saved |

**Deviation: the editor crashed on `set_parent`.**
- `MaterialInstanceTools.set_parent` on `MI_NightStormSky` crashed the editor (render-thread assertion "UniformExpressionCache should be up to date, RenderProxy=MI_Env_NightSky Material=M_LB_StormSky"). `MI_Env_NightSky`, a child of that MI, draws the level's sky.
- Only what had been saved survived (`MPC_LB_Storm`, `MF_LB_StormFlash`, `DA_StormSettings`, `M_LB_StormSky`, the ini). The lead did the reparent headless with the editor closed (`Tools/lighting/p14_2a_sky_reparent.py`) and read back every override before and after. The rule is in `MCP_NOTES` (Storm materials, item 1): never reparent an MI the level uses over MCP.
- After the restart I re-verified every pre-crash asset (MPC defaults, the function graph, the DA fields, the sky graph and both sky MIs) before going on.

**Glass.** In `M_LB_StainedGlass` (opaque) and `M_LB_StainedGlass_Translucent`, the final emissive node (`Multiply_3` and `Multiply_1`) is multiplied by `MF_LB_StormFlash(Gain = MPC GlassFlashGain, Response = scalar FlashResponse, default 1, group Storm)`.
- **F = 0:** `Mul` = 1 + Gain x 0 x Response = 1 exactly, so the emissive is unchanged.

| MI | `FlashResponse` after | Other overrides (EmissiveIntensity or GlassOpacity, Tint, GlassTex, parent) |
|---|---|---|
| `MI_Glass_Clue_Saints` | **0** (override) | unchanged: 5.5, (0.85, 0.9, 1, 1), T_LB_StainedGlass_Clue |
| `MI_Glass_Lancet_B` | **0** (override) | unchanged: 5.5, same tint, T_LB_StainedGlass_Lancet_B |
| `MI_Glass_Lancet_A` | 1 (inherited, no override) | unchanged: 5.5 |
| `MI_Glass_Broken` | 1 (inherited) | unchanged: 2 |
| `MI_Glass_East` | 1 (inherited) | unchanged: GlassOpacity 0.3 |

**Shafts.** In `M_LB_LightShaft`, the `Intensity` parameter now goes through `Intensity` x `MF_LB_StormFlash(ShaftFlashGain, FlashResponse)` before it reaches the colour x intensity multiply (it feeds nothing else). **F = 0:** x 1. `FlashResponse` = 1 is an explicit override on `MI_LightShaft_Roof`, `_Window` and `_Crypt`; `Intensity` 0.04 / 0.04 / 0.02 and `EdgePower` 2.5 (`_Crypt` inherits it from `_Roof`, as before) are unchanged, and so are Color and the parents.

**Pools.** In `M_LB_Decal_LightPool`, the final emissive (`Multiply_3`) x `MF_LB_StormFlash(PoolFlashGain, 1)`. The opacity is untouched. **F = 0:** x 1.

**Reveal decals.** `M_LB_Decal_LightningReveal` is a duplicate of `M_LB_Decal_Chalk` (blend mode Translucent, domain DeferredDecal, kept).
- Opacity = (ChalkTex alpha x `Opacity` 0.9) x saturate(F x `RevealGain`).
- Emissive = chalk colour (0.82, 0.80, 0.75) x `FlashTint`.rgb x F x `RevealEmissive`. The original chalk has no emissive, so this is new.
- **F = 0:** the opacity is exactly 0 (a decal at 0 opacity writes nothing) and the emissive is 0, so the decal is invisible.
- The 4 MIs set `ChalkTex` to the table's textures. `MI_Reveal_Drag` also has `Opacity` 1, from the existing `MI_Decal_DragMarks`, which sits on `M_LB_Decal_Grime`; that master's `Roughness` 0.95 and `BaseColorTint` don't exist on the reveal master, so they were not copied. The other three use the default 0.9, like the chalk MIs.

**Compile and checks.**
- Every master and the function recompiled with no error; the output log has no new Error or Warning (only the harmless `GetObjectProperties ... could not be read` lines from my own probes).
- **Shader instruction counts are not measured:** no MCP tool gives them. The additions are about 10 to 20 scalar ALU instructions in the sky pixel shader, and one multiply plus a few constants elsewhere.
- **Memory:** no texture was added, so no VRAM impact. The new assets are 1 MPC, 1 function, 1 data asset, 1 sky master, 1 reveal master and 4 small MIs.
- Thumbnails (`CaptureAssetImage`) of `MI_Glass_Lancet_A`, `MI_Env_NightSky` and `MI_Reveal_Sigil` look as expected (stained colours; dark night sky; invisible reveal). They are not a before/after proof: no capture was taken, and the F = 0 neutrality rests on the construction above. The lead's sky capture (mean difference <= 2/255) is still to do.

**For P14-2b and P14-3.**
- 2b: the MPC already holds `WindStrength`, `WindPhase` and `WindDirection`. `MF_LB_WindSway` reads them with `CollectionParameter`, like `MF_LB_StormFlash` reads `LightningFlash`. A `MaterialFunctionCall` gets its pins once its `materialFunction` is set (`MCP_NOTES`, Storm materials, item 3). `Tools/lighting/p14_lib.py` has the helpers (`add`, `conn`, `flash_node`, `dump_graph`).
- 3: `DA_StormSettings` and the ini line exist, so the subsystem finds its data. The placed shafts and pools already use the new master versions; the reveal decal actors take `MI_Reveal_*` from `/Game/LastBell/Materials/Instances/`. Don't reparent any MI over MCP.
- The MPC defaults are 0, including the gains. Until the subsystem is active, F = 0 and every flash term is 1, so the level looks as before. In P14-4 the subsystem writes the gains every frame; its warning "lacks one or more storm parameters" would show a wrong name.

### P14-2b result (wind sway materials, 2026-11-07)
**Made (materials only; `L_Monastery` and `M_LB_Surface` stayed clean before every save and at the end; no captures, no PIE, no `set_parent`):**
- `/Game/LastBell/Materials/Functions/MF_LB_WindSway` (exposed to the library, category LastBell). Inputs `WindAmplitudeCm`, `WindRefHeightCm` (default 60) and the static bool `bFlutter` (default false, feeds a Static Switch inside); output `WPO`. Built exactly as 6.6:
  - **Bend:** `Saturate(PreSkinnedPosition.z / WindRefHeightCm)`, pivot `TransformPosition(Instance -> World, 0)` per instance, phase `WindPhase + dot(Pivot.xy, (0.0031, 0.0047))`, s = 0.6 sin(phi) + 0.4 sin(2 phi + 1.3), d = `WindDirection`.xyz x `WindStrength` x (0.55 + 0.45 s) x h^2 x amplitude, WPO = d + (0, 0, -0.25 |d| h).
  - **Flutter:** `Saturate(PreSkinnedPosition.y / 20)`, phase 3 `WindPhase` + dot(absolute world position, (0.05, 0.07, 0.03)), WPO = `VertexNormalWS` x `WindStrength` x sin x a x amplitude.
  - All `Sine` nodes have `period` 2 pi (the node's default period of 1 would be sin(2 pi x)).
- `M_LB_Foliage` and `M_LB_FoliageMasked`: scalars `WindAmplitudeCm` (0) and `WindRefHeightCm` (60), group Wind; `StaticSwitchParameter bWind` (default false), True = `MF_LB_WindSway` with a `StaticBool` into `bFlutter` (**false** in `M_LB_Foliage`, **true** in `M_LB_FoliageMasked`), False = `Constant3Vector` (0, 0, 0); the switch feeds World Position Offset.
- 8 MIs set (table below); `MI_Foliage_Moss01` untouched. F0's list is complete: `get_referencers` finds exactly 7 MIs on `M_LB_Foliage` and 2 on `M_LB_FoliageMasked`, so there is no extra MI for the amplitude-6 / height-60 rule.

| Master | What fed WPO before | Max World Position Offset Displacement before -> after | Compile |
|---|---|---|---|
| `M_LB_Foliage` (opaque) | nothing (the pin was unconnected) | 0 -> **40** (read back 40) | `recompile` returned with no error; no new log Error or Warning |
| `M_LB_FoliageMasked` | nothing | 0 -> **6** (read back 6) | same |

With `bWind` false the WPO input is a constant zero, so the default permutation evaluates to the same output as before (zero offset). I did not confirm that the compiler drops a constant-zero WPO like an unconnected pin (it normally does), and no instruction counts are measured (no MCP tool gives them); P14-7 would show any cost on the non-wind foliage.

**MI read-back, before and after** (every texture, vector and the parent were compared by script and are identical; the static switch `bUseARM` was read too and is unchanged: true on the 7 foliage MIs, false on the ivy):

| MI | `bWind` | `WindAmplitudeCm` | `WindRefHeightCm` | Other overrides (unchanged) |
|---|---|---|---|---|
| `MI_Foliage_GrassMedium02` | false -> **true** | none -> **16** | none -> **90** | Desaturation 0.45, 3 textures |
| `MI_Foliage_NettlePlant` | false -> true | none -> 9 | none -> 70 | 3 textures |
| `MI_Foliage_WeedPlant02` | false -> true | none -> 6 | none -> 30 | 3 textures |
| `MI_Foliage_Fern02` | false -> true | none -> 10 | none -> 60 | 3 textures |
| `MI_Foliage_WildRooibos` | false -> true | none -> 7 | none -> 80 | Desaturation 0.45, 3 textures |
| `MI_Foliage_SearsiaLucida` | false -> true | none -> 5 | none -> 200 | BrightnessMul 0.6, 3 textures |
| `MI_Foliage_Moss01` | false (not touched) | none | none | 3 textures; read again at the end, identical |
| `MI_Ivy_Green` | false -> true (flutter) | none -> 2.0 | no override | Desaturation 0.35, BaseColorTint (0.55, 0.62, 0.45, 1), 4 textures |
| `MI_Ivy_Dead` | false -> true (flutter) | none -> 2.0 | no override | Desaturation 0.2, 4 textures |

**Neutrality at `WindStrength` = 0 (the MPC default; the storm subsystem is inactive in the editor).**
- Bend: the scalar `WindStrength` x gust x h^2 x amplitude is exactly 0, so d = `WindDirection` x 0 = (0, 0, 0); `length(0)` = 0, so the sag term is 0. WPO = (0, 0, 0). The gust factor (0.55 + 0.45 s) is bounded in [0.1, 1], and the pivot, phase and sin are all finite, so no NaN can enter.
- Flutter: `VertexNormalWS` x 0 x sin x a x amplitude = (0, 0, 0).
- On every MI that does not override `bWind` (Moss01) the switch is false and WPO is the constant zero. On the 8 MIs that do, the amplitude is a finite number, so the result above holds. Not verified by capture.

**Checks.**
- Thumbnails (`CaptureAssetImage`) of `MI_Foliage_GrassMedium02` and `MI_Ivy_Green` render (grass blades on the preview sphere, cut-out ivy leaves with the same tint), not placeholders, so both `bWind` permutations compiled. They are not a before/after proof.
- Log after the work: no new Error or Warning. The only extra lines are two of my own probes (`GetObjectProperties ... could not be read`, and a path that Git Bash rewrote).
- Memory: no texture added, so no VRAM impact. New: 1 function. Each of the 8 MIs now has one more static permutation (`bWind` true), so a few more compiled shaders per MI, no runtime memory beyond the shader code.
- **Not validated:** no capture, no PIE; the look of the sway is judged in P14-4 and P14-5, the GPU cost is measured in P14-7.

**Notes for P14-3.**
- **WPO is now enabled on these materials, so P14-3 must set the WPO disable distance from section 7.7 on the 249 actors and the 312 ISM components.** Until then, once the storm is active, the wind would cost vertex-shader time at every distance (and Nanite WPO, if a component evaluates it).
- Nanite: both masters have `bUsedWithNanite` true. Whether Nanite evaluates WPO for these meshes depends on the project setting and the per-component "evaluate WPO" flag; check it when applying 7.7, and read the sway in a capture before trusting it.
- The plan's single-instance pivot: a non-instanced actor gets its actor origin as the pivot, so two actors of the same mesh at nearby positions sway out of step by their world position, which is the intent.
- The dead tree and its snag stay static (bark on `M_LB_Surface`, D-060).

### P14-3 result (level work, 2026-11-07)
**Scripts:** `Tools/lighting/p14_3_level.py` (`--apply [--only tags,zones,pp,groups,decals,apparitions]`, `--check`) and `Tools/lighting/p14_wpo_distance.py` (`--apply [--dry]`, `--check`). Both are idempotent (exact-label find or create) and never save. `L_Monastery` was saved once, at the end, in one `save_assets` call with only the map package (it returned True; `is_dirty` false afterwards). `git status` shows `L_Monastery.umap` as the only changed content file; no other `.uasset` changed.

**Census (`find_actors`, empty name and tag):** before 2992 (= F0), after 3015 = 2992 + 23 (7 zones + 9 groups + 2 PP volumes + 5 decals), and again 3015 after the save. The map was `is_dirty` false at the start, true after the edits, false after the save. The 13 never-save packages (`M_LB_Surface` and the 12 Blueprints on the list, including `BP_WardenApparition`) read not dirty before and after the save.

**Final checks after the save:** `p14_3_level.py --check` 62 PASS, 0 FAIL; `p14_wpo_distance.py --check` 5 PASS, 0 FAIL.

**1. Link tags** (all tags were empty before; each actor now has just its one tag): `LB_StormMoon` on `DirectionalLight` (object `DirectionalLight_1`); `LB_StormMoonSpot` on the 10 spots; `LB_StormFill` on `L_Tw_BellFill`; `LB_StormSky` on `SkyLight`. `find_actors` by tag returns 1 / 10 / 1 / 1; `Moon_Fill` has no storm tag. PIE log of `StormSetup`: "Storm: active with 13 linked lights" (1 + 10 + 1 + 1).

**2. Zones.** Class `LBStormZone`, folder `Lighting/Storm`, location = box centre, rotation 0, scale 1, `Box` extent = half size. Read-back world box (location ± extent) matches the table to 0.0 cm, and `get_actor_bounds` returns the same box. Exposure and priority as in 5.1 (float32 rounding only: 0.35 reads 0.3499999940).

| Zone | Location | Box extent | Exposure | Priority |
|---|---|---|---|---|
| `SZN_Chapel` | 7550, −345, 1180 | 1550, 1205, 1220 | 0.35 | 1 |
| `SZN_Crypt` | 9150, −1215, −622.5 | 2850, 1735, 577.5 | 0 | 2 |
| `SZN_Passage` | 7750, 1750, 580 | 1710, 850, 620 | 0.3 | 1 |
| `SZN_Cloister` | 10750, 1770, 730 | 1290, 1270, 770 | 0.6 | 1 |
| `SZN_Garth` | 10852.5, 1802.5, 730 | 607.5, 457.5, 770 | 1 | 2 |
| `SZN_TowerShaft` | 12500, 2000, 1305 | 510, 510, 1345 | 0.25 | 3 |
| `SZN_Belfry` | 12500, 2000, 3725 | 510, 510, 1075 | 0.85 | 3 |

**3. Post-process.** `PP_Cloister` before: location (9550, 1375, 2080), scale (35.5, 18.25, 21.2), bounds X 6000…13100, Y −450…3200, Z −40…4200, priority 1, blend 300, overrides `AutoExposureMin/MaxBrightness` 0.65 and `ColorSaturationShadows` (0.65, 0.65, 0.65, 1), no method override. The brush is a 200 cm unit cube centred on the actor (bounds centre = location, bounds / scale = 200 on every axis), so the new transform follows from the target boxes. Only location and scale were changed; rotation, priority, blend and every value are unchanged.

| Volume | Location | Scale | Bounds read back | Priority / blend | Overrides |
|---|---|---|---|---|---|
| `PP_Cloister` (shrunk) | 9040, 2050, 2080 | 30, 11.5, 21.2 | X 6040…12040, Y 900…3200, Z −40…4200 | 1 / 300 | the same three, values unchanged |
| `PP_Chapel` (new) | 7550, −345, 1180 | 15.5, 12.05, 12.2 | X 6000…9100, Y −1550…860, Z −40…2400 | 2 / 200 | `AutoExposureMin/MaxBrightness` 0.65 and `ColorSaturationShadows` (0.65, 0.65, 0.65, 1), nothing else |
| `PP_Tower` (new) | 12500, 2000, 2480 | 5.1, 5.1, 25.2 | X 11990…13010, Y 1490…2510, Z −40…5000 | 3 / 200 | the same three |

New volumes: not unbound, enabled, blend weight 1, brush collision profile `NoCollision`, method not overridden (it reads `AEM_Histogram`, the struct default, like `PP_Cloister`). `PP_Crypt` (prio 1, blend 300, EV 0.2, bloom and method overridden, bounds as before), `PP_Outdoor_Night` (prio 1, blend 500, EV 1.15, satShadows 0.65, bounds as before) and `PostProcess_Exposure` (unbound, prio 0, blend 100, EV 3) read back identical to the values read before the first change.

**4. State light groups** (folder `Lighting/Storm`, location = mean of the group's light locations, `FadeSeconds` 1.5, `GlowParameter` `Color`). Every light, emissive actor and glow actor was found exactly once by label. Rules read back in table order with the right tags; Off rules read the defaults (scale 1, amount 0.4, speed 6).

| Group | Lights | Emissive / glow actors | Rules read back |
|---|---|---|---|
| `SLG_Chapel_Altar` | `Light_Chapel_Altar_N`, `_S` | none | Ritual.1: Flicker 0.25 / 0.45 / 7 |
| `SLG_Chapel_Dais` | `Light_Chapel_Statue`, `Light_Chapel_DaisFill` | none | Ritual.1: Off |
| `SLG_Crypt_Torches` | `L_Crypt_Torch_T1/T2/T3` | none | Ritual.2: Flicker 0.6 / 0.45 / 9 |
| `SLG_Crypt_Niches` | the 5 `L_Crypt_Candle_Niche_*` | emissive: the 5 `CD_Candles_Niche_*_Flame` | Ritual.2: Off |
| `SLG_Cloister_Bells` | `L_Cl_Bells` | glow `CLA_Lantern_Bells` | CloisterEntered: Flicker 0.85 / 0.3 / 5 |
| `SLG_Cloister_West` | `L_Cl_West` | glow `CLA_Lantern_West` | CloisterEntered: Flicker 0.85 / 0.3 / 5; Ritual.3: Off |
| `SLG_Cloister_Entry` | `L_Cl_Entry` | glow `SHA_Lantern_Entry` | Ritual.3: Off |
| `SLG_Tower_Landings` | `L_Tw_Land4/7/10` | glow `TWA_Lantern_Land4/7/10` | Ritual.3: Flicker 0.9 / 0.2 / 4 |
| `SLG_Tower_Bell` | `L_Tw_Bell` | glow `TWA_Lantern_Bell` | TowerTop: Flicker 0.8 / 0.5 / 8 |

19 distinct lights and 7 distinct glow actors: no light and no glow actor is in two groups. Each lantern is 41.9 cm from its own group light (the other lights of `SLG_Tower_Landings` are over 1000 cm away), so the BeginPlay pairing picks the right light. `StormSetup` (below) also confirms that every glow actor resolves a `Color` slot.

**5. Reveal decals** (`DecalActor`, folder `Lighting/Storm`, scale 1, the `MI_Reveal_*` from `/Game/LastBell/Materials/Instances/`). Transform, `DecalSize` and material read back exactly as the 5.6(d) table. Rotations were compared as quaternions (the editor reads yaw −90 with pitch `-0`).

| Actor | Location | Rotation | `DecalSize` | MI |
|---|---|---|---|---|
| `RV_Gate_Sigil` | 300, 500, 260 | 0, 180, 90 | 10, 110, 110 | `MI_Reveal_Sigil` |
| `RV_WellHouse_Tally` | 1350, −1775, 140 | 0, −90, 90 | 10, 40, 60 | `MI_Reveal_Tally` |
| `RV_Chapel_Circle` | 8265, −255, 0.5 | −90, 0, 0 | 10, 90, 90 | `MI_Reveal_Circle` |
| `RV_Garth_Drag` | 10750, 3000, 270 | 0, 90, 90 | 20, 30, 110 | `MI_Reveal_Drag` |
| `RV_Belfry_Tally` | 12200, 1540, 2850 | 0, −90, 90 | 15, 50, 50 | `MI_Reveal_Tally` |

**6. Apparitions.** Placed instances only (`Apparition_Courtyard` = `BP_WardenApparition_C_0`, `Apparition_Chapel` = `BP_WardenApparition_C_1`); the Blueprint was not touched or saved. `Stations` (1 station each) was read, written back whole with only `bLightningOnHold` set to true, and read back: a field-by-field diff against the saved "before" JSON shows that flag as the only difference. Courtyard: location (6020, 1300, 800), look cone 30, fade in 1.5, hold 4, fade out 2, no walk path, walk speed 110. Chapel: location (8380, −120, 0), look cone 30, min player distance 150, fade in 1, hold 2.5, fade out 1.5, walk path (8380, −380, 0), (8500, −650, 0), (8500, −1000, 0), (8250, −1100, 0), walk speed 110. All identical to before.

**7. WPO distance 4000.** The scan (3653 read calls, about 20 minutes) printed the counts before any write: **249 static-mesh actors and 312 ISM components on 19 `PCGV_*` volumes, exactly the F0 numbers.** The 249 are the same actor set as F0's `foliage_actors` (0 only in F0, 0 only live). Effective-material slots by MI: GrassMedium02 90, WildRooibos 54, Fern02 41, WeedPlant02 32, NettlePlant 30, Ivy_Dead 22, SearsiaLucida 18, Ivy_Green 10 (no actor used `MI_Foliage_Moss01`). All 561 distances were 0 before, and no other `StaticMeshActor` had one set. After `--apply`, and again after the save, `--check` reads 4000 on all 249 and all 312. `--check` uses the target list that `--apply` wrote (`Saved/p14_wpo_targets.json`); `--rescan` scans the level again. `bEvaluateWorldPositionOffset` was not changed. `MCP_NOTES.md` (Storm materials, items 7 to 10) records that regenerating a `PCGV_*` volume resets the distance, so `--apply` must be rerun.

**Tests (real project, headless `UnrealEditor-Cmd`, the editor stayed open and untouched meanwhile):** `Saved/Logs/LBTests_P14_3.log` has **128 `Result={Success}` and 0 `Result={Fail`**, exit code 0, "TEST COMPLETE". `LastBell.Functional.Storm.Monastery.StormSetup` passes. So do `RouteBot.Monastery`, `WalkPath.Monastery`, `Warden.Monastery.StagesRelocateTheWarden` and `Warden.MonasteryReachability`, which now run with the storm active. The only `Error:` line in the log is `HttpListener unable to bind to 127.0.0.1:8000`, because the open editor holds that port.

**Deviations.**
- **Three `ConnectionResetError`s** on the large empty-name `find_actors` reply (3000 refs) in about 12 runs, in the `pp`, `decals` and `apparitions` steps. The editor stayed alive and answered the next call each time (process responding, no new crash report), and no mutation was in flight. I did not treat these as a crash or a hang. I re-ran the idempotent step after each, then made `Ed.call` repeat a read-only call up to 3 times on a new session (never a mutation). The map was not saved until every check was clean.
- New actors are in the folder `Lighting/Storm`; the plan did not name one. No existing actor was moved.
- `p14_wpo_distance.py --check` reads the cached target list unless `--rescan` is given (a rescan takes about 20 minutes).

**For the lead and the owner to check by eye (not validated here; no capture, PIE or synthetic input was used):**
- **Decal placement** under a frozen flash (`lb.Storm.Freeze 0.8`, PIE Simulate). All five are invisible at F = 0.
- **Exposure against F0:** the chapel south aisle and the sacristy (Y < −450) change from EV 3 (`PostProcess_Exposure`) to EV 0.65 now that `PP_Chapel` covers the whole nave. This is expected and is to be shown to the owner (P14-4). `PP_Cloister` no longer covers the nave; the tower is covered by `PP_Tower` (same 0.65), so only the chapel should change. The 200 cm blend radius on the new volumes softens the borders.
- **Lanterns dark after `State.Ritual.3`** (`L_Cl_West`, `L_Cl_Entry`): the glass follows the light only at runtime, and so far only the functional test has shown it, never the real level.
- **Wind:** the sway itself, any pop at 4000 cm, and the GPU cost (R-60) are for P14-4 and P14-7.
- The PIE log line "Storm: active with 13 linked lights, 0 zones" is printed before the zones' own BeginPlay register them. `StormSetup` confirms the 7 zones exist, but nothing has yet tested `GetExposureAt` in `L_Monastery` itself.

### P14-3 decal check (lead + owner, PIE Simulate, 2026-11-07)

`DA_StormSettings.DebugFreezeFlash` set to 0.8 in memory through MCP (never saved; set back to −1 right after and read back), then `capture_session.py --mode simulate --fg-wait 180` on `Tools/lighting/poses/p14_3_decals.json`: 6/6 poses in about 4 minutes. Images in `Docs/ArtTest/lighting/decals/p14_3_*.png`. The placements are exactly as the 5.6(d) table; what they look like is for P14-4:

| Decal | Result | For P14-4 |
|---|---|---|
| `RV_Gate_Sigil` | On the flat inner wall beside the arch, above `KP_Lantern_Gate`. Reads clearly. | Brightness only. |
| `RV_WellHouse_Tally` | On the west pier, readable, but the top of the marks runs into the pier's broken top, and the leaning stone shard crosses the second group. | Lower it about 25 cm (centre Z 140 → 115). |
| `RV_Chapel_Circle` | On the floor, centred on the S2 pool as planned. Under the flash the pool and its shaft go almost white, so the chalk inside the pool loses contrast; only the arcs outside it read. | Move it off the pool, or lower the pool's flash response. Owner's call. |
| `RV_Garth_Drag` | On the north-walk wall between the two doorways, seen through the bay. The roofed walk gets no flash light, so the wall stays black and the marks glow alone in the dark (the wall shows only when the image is brightened 6×). | Keep it as an eerie glowing smear, or move it to a wall the flash lights. Owner's call. |
| `RV_Belfry_Tally` | On the flat south wall west of the lancets. Reads clearly. | None. **Correction to 5.6(d):** from the `tw_belfry` pose the bell hides it (it falls on the bell's silhouette); it shows once the player walks round the bell. |

### P14-4 wind fix result (2026-11-07)
Spec: `Docs/plans/P14_4_WIND_FIX.md` (owner "go", D-100). Script: `Tools/lighting/p14_4_wind_fix.py` (`pre`, `fn`, `savefn`, `mis`, `savemis`, `check`). No PIE, no captures, no `set_parent`; `L_Monastery`, `M_LB_Surface` and `DA_StormSettings` were not saved.

**Change 1, `MF_LB_WindSway` (bend branch only).** h = saturate(`PreSkinnedPosition`.z × S / `WindRefHeightCm`), S = length(Transform(Instance → World, (0, 0, 1))).
- Nodes 53 → 57. Added: `Constant3Vector_4` (0, 0, 1, 1), `Transform_0` (`transformSourceType` read back `TRANSFORMSOURCE_Instance`, `transformType` `TRANSFORM_World`; the node defaulted to Tangent → World), `Length_2` (input `Transform_0`), `Multiply_17` (A = `ComponentMask_1` = the B channel of `PreSkinnedPosition`, B = `Length_2`).
- Rewire: `Divide_0` A was `ComponentMask_1`, now `Multiply_17`; B stays `FunctionInput_1` (`WindRefHeightCm`). The flutter branch is untouched. The `WindRefHeightCm` input description now reads "World height in cm (after the actor or instance scale) at which the bend is full".
- `MaterialTools.recompile` returned with no error for `MF_LB_WindSway`, `M_LB_Foliage` and `M_LB_FoliageMasked`. No new Error or Warning lines about these assets in the log (the only matches are older ones: the "could not be read" property warning of the 14-2b session and the Git Bash path-mangling errors).

**Change 2, MI values** (only `WindAmplitudeCm` and `WindRefHeightCm` changed; parent, every texture and vector override, `bUseARM` and `bWind` read identical before and after by script):

| MI | `WindAmplitudeCm` | `WindRefHeightCm` |
|---|---|---|
| `MI_Foliage_GrassMedium02` | 16 → 30 | 90 → 60 |
| `MI_Foliage_NettlePlant` | 9 → 18 | 70 → 45 |
| `MI_Foliage_WeedPlant02` | 6 → 12 | 30 (unchanged, override rewritten with the same value) |
| `MI_Foliage_Fern02` | 10 → 18 | 60 → 45 |
| `MI_Foliage_WildRooibos` | 7 → 14 | 80 → 60 |
| `MI_Foliage_SearsiaLucida` | 5 → 12 | 200 → 150 |
| `MI_Ivy_Green`, `MI_Ivy_Dead` | 2 → 4 | no override (left) |

**Saves** (one package per call, `is_dirty` false after each; PIE off and `L_Monastery` / `M_LB_Surface` clean before and after each): `MF_LB_WindSway`, `M_LB_Foliage`, `M_LB_FoliageMasked` (both masters were dirty after the recompile), then the 8 MIs. `p14_4_wind_fix.py check`: OVERALL PASS (graph wiring and the 8 MI values).

**Not validated: the sway itself (lead's captures and the owner's live check).** Expected, not measured: the grass peak lean is about 30 cm plus 0.25 × 30 sag, under the 40 cm cap of `M_LB_Foliage`; ivy 4 cm is under the 6 cm cap of `M_LB_FoliageMasked`. No shader instruction count was taken (no tool gives one).
