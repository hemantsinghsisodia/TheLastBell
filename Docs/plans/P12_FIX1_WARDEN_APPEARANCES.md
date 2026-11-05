# P12 fix set 1: Warden appearances and attack light

**Status: approved by the owner on 2026-11-05 ("go"): option A now with the real walk in Phase 13, and the chase glow. F1 and F2 done (suite 89/89 at F1; d29582f, not yet seen rendered). F3 next.**
Branch: `claude/phase-12-warden-visual`. Parent plan: `P12_WARDEN_VISUAL.md`. Lead plans; every implementer is spawned with `model: "sonnet", effort: "high"` (D-048).

## 1. What the owner asked for, and what's behind it

Owner's playtest, 2026-11-05:

| Owner said | What the project does now | Cause |
|---|---|---|
| Roofline: stand still is fine, but appearing and disappearing shouldn't be instantaneous, and how can it be highlighted? | `BP_WardenSilhouette_C_0` at (6020, 2300, 800) pops on, slides −1000 in Y, pops off after 3 s, whether or not the player is looking | `SetActorHiddenInGame` only. Unlit black on a dark sky, and about 45 px tall at 1080p from the gate (about 60 m) |
| Chapel: easily missed. Appear from the altar rail, then vanish in the nearby room | `BP_WardenSilhouette_C_2` at (9150, 0, 300), behind the east window, 3 s, the moment the altar is used | Its feet are about 1 m above eye level and its head nearly 4 m, while the player is looking down at the mechanism |
| Red light should be more prominent | `TellLight`: 800, radius 160, no shadows, at the `mask` socket, on for the 0.6 s windup | Most likely three things together: the socket has zero offset on `head`, which is inside the hood about 20–40 cm behind the mask, so outward-facing surfaces get little light; radius 160 ends near the chest; 0.6 s is very short. Not yet seen from a capture |
| Hood or body doesn't vanish | Pass | Nothing to do |

"The nearby room" is taken to be the **sacristy**: its doorway (X 8440–8560, Y −750…−810, apex Z 340) is the only room next to the altar end, and the crypt door that the ritual has just opened is inside it, so the beat also shows the player where to go next.

**Finding that shapes the chapel design (measured from the V5.5 master, `Warden_Walk`):**
- Hands move 0.0 cm sideways, 0.2 cm forward and 3.0 cm up and down over the whole clip, and that 3.0 comes from the pelvis lift. Arms and upper body don't animate.
- The foot swings ±21 cm in a smooth back-and-forth, averaging 42.8 cm/s, with no planted phase. Patrol speed is 140 cm/s.
- The robe reaches the floor, so little of this shows.

So a walking figure at 3–8 m would look much like the gliding figure the owner has just objected to in the crypt. Phase 13 has to rework Walk (see section 9).

## 2. Owner's decisions (2026-11-05)

**D1. From the rail to the room: stations now, a real walk in Phase 13.**
- **Now:** it forms at the rail as the player turns around and fades away, then forms inside the sacristy, framed by the doorway against the candlelit wall, and fades away. No walking on screen, so it doesn't depend on animation.
- **Phase 13 (the owner's suggestion):** once Walk is reworked, a real walk from the rail into the sacristy replaces the second station, stooping through the doorway if it needs to. The first station stays. This is in the Phase 13 notes (section 9).
- **Not done:** leaving the whole chapel change until Phase 13. It would save almost nothing, because the rail shares its code and materials with the roofline, and it would keep the easily missed east-window version and the old Blueprint.

**D2. Red glow while it's chasing the player: yes.** The mask glows dull red through the chase and flares at the attack. The attack tell lasts only 0.6 s, so this gives the red far more time on screen, and it tells the player "it has seen me".

## 3. Behaviour

Both beats use one linear sequence:

```
Idle -> (trigger tag added) -> ArmDelay -> for each station: WaitForLook -> FadeIn -> Hold -> FadeOut -> Gap -> Done
```

- **WaitForLook:** hidden until the station's look point is inside the player's view cone with a clear line of sight. This is what makes the beat hard to miss. The player has to turn around to leave the altar, so the rail station can't be skipped by accident.
- **Too close:** if the player is closer than `MinPlayerDistance` while waiting, the station is skipped. During FadeIn or Hold, it goes straight to FadeOut from the current alpha.
- **Facing:** on entering FadeIn the figure turns to face the player's location (yaw only), then stays fixed.
- **One-shot:** after Done it never runs again. If the tag is already present at BeginPlay it goes straight to Done, so a checkpoint reload doesn't repeat it.

| Instance | Trigger | Arm delay | Station | Location (world cm) | Cone | Min distance | In / hold / out / gap (s) |
|---|---|---|---|---|---|---|---|
| `Apparition_Courtyard` | `State.Event.CourtyardEntered` | 0.5 | Roofline | (6020, 1300, 800), confirm at look test (Y 1300, 1800 or 2300) | 30° | 0 | 1.5 / 4.0 / 2.0 / 0 |
| `Apparition_Chapel` | `State.Ritual.1` | 1.5 (the mechanism's turn) | Rail | (8380, −120, 0), confirm at look test (Y −250, −120 or 0) | 30° | 150 | 1.0 / 2.5 / 1.2 / 1.0 |
| | | | Sacristy | (8500, −930, 0) | 30° | 300 | 1.0 / 2.5 / 1.5 / 0 |

Look point: station location + 200 cm in Z. Rail spot: X 8380 keeps the figure 70 cm clear of the rail (X 8450). In the old captures the moon shaft lights the floor by the rail's south half, which is the backdrop the look test is after.

**How it's highlighted (roofline):**
1. It waits until you're looking that way, and stays on longer (7.5 s in total, against 3 s).
2. **A soft moon glow behind it**, as if cloud has thinned behind the figure. It's the strongest fix for a dark shape on a dark sky, and it fades in and out with the figure.
3. **A faint pale mask**, so a small face shows on the dark shape.

Not now: lightning is the best highlight of all, but storm work is Phase 14–15. A sound sting belongs to the audio phase. Both are noted for those phases.

## 4. Code (gameplay-programmer; no editor needed)

New files, following the `LBWardenLogic` pattern (pure logic, unit tested; the actor gathers the facts):

**`Source/LastBell/AI/LBApparitionLogic.h/.cpp`**
- `USTRUCT(BlueprintType) FLBApparitionStation`: `FVector Location`, `float LookConeDegrees = 30`, `float MinPlayerDistance = 0`, `float FadeInSeconds = 1`, `float HoldSeconds = 3`, `float FadeOutSeconds = 1.5`, `float GapAfterSeconds = 0`.
- `enum class ELBApparitionPhase : uint8 { Idle, ArmDelay, WaitForLook, FadeIn, Hold, FadeOut, Gap, Done }`.
- `struct FLBApparitionRun { ELBApparitionPhase Phase; int32 Station; float PhaseTime; float FadeOutFrom; float Alpha; }`.
- `struct FLBApparitionFacts { float DeltaSeconds; bool bLookedAt; float PlayerDistance; }`.
- `void LBApparition::Start(FLBApparitionRun&)`, and `bool LBApparition::Step(FLBApparitionRun&, const TArray<FLBApparitionStation>&, float ArmDelay, const FLBApparitionFacts&)`, which returns true when the run has just entered FadeIn (the actor then moves and turns the figure).
- Alpha: FadeIn `SmoothStep(0, 1, t / In)`; Hold 1; FadeOut `FadeOutFrom * (1 − SmoothStep(0, 1, t / Out))`; otherwise 0. A zero duration completes that phase on the next step.

**`Source/LastBell/AI/LBWardenApparition.h/.cpp`**: `UCLASS(Blueprintable) ALBWardenApparition : AActor`.
- Editable: `FGameplayTag TriggerTag`, `float ArmDelaySeconds`, `TArray<FLBApparitionStation> Stations`, `float LookPointHeight = 200`, `float GlowSizeCm = 0` (0 hides the glow).
- Components: root `USceneComponent`; `UStaticMeshComponent Body` and `UStaticMeshComponent Glow`, both NoCollision, no shadows, no navigation. Meshes and materials are set in the Blueprint (no hard asset references in C++).
- BeginPlay: hide; create one dynamic material instance per slot on Body and Glow; bind `OnStateChanged` and `OnStateReplaced` (same pattern as `ULBWardenBrainComponent`, lines 82–91); if the tag is already present, Done. Tick stays off until triggered.
- Tag added while Idle: `Start`, enable tick.
- `OnStateReplaced` (load or new game): stop and hide; Done if the tag is present, otherwise Idle.
- Tick: read the camera from the first player controller's `PlayerCameraManager`. No camera means `bLookedAt = false` and a large distance. `bLookedAt` = inside the cone, then `LineTraceSingleByChannel(ECC_Visibility)` from the camera to the look point, ignoring self and the pawn; the trace runs only if the cone test passes. Call `Step`. If it returns true, move to the station and set the yaw towards the player. Set scalar `Fade` = Alpha on every dynamic instance. Actor hidden when Alpha is 0. On Done: hide and turn tick off.
- `UFUNCTION(BlueprintPure) float GetAlpha()`, and `ELBApparitionPhase GetPhase()`, for tests.
- EndPlay: unbind.

**Tests**, new `Source/LastBellTests/Tests/LBApparitionTests.cpp`:
- Unit, `LastBell.Warden.Apparition.*`: `WaitsForLook` (alpha stays 0 for 60 s unseen), `FadeTiming` (alpha rises, holds at 1, falls, reaches 0; total time equals the sum within one tick), `TwoStations` (moves on after the gap and enters FadeIn again), `TooCloseSkips`, `TooCloseDuringHoldFadesFromCurrentAlpha`, `DoneIsTerminal`.
- Functional, `LastBell.Functional.Warden.Apparition.*`, in the map the existing Warden functional tests use (`L_Test_Warden`), with the patterns of `LBWardenFunctionalTests` and `LBPuzzleFunctionalTests`. **They spawn their own `ALBWardenApparition`** with `SpawnActorDeferred`, in clear space around the player, so they don't depend on the placed instances (those arrive in F3, and `check_warden.py --bp` checks them):
  - `TwoStationSequence`: add the trigger tag, aim away and check it stays hidden; aim at station 1 and check alpha rises, then falls; aim at station 2 and check the same; check Done, hidden, tick off. Use a tag that exists only for tests (`State.Test.*`), so nothing else in the map reacts, and short fades (0.2 s) to keep the test quick.
  - `TagAlreadyPresentStaysDone`: spawn with the tag already in the world state: stays hidden, Done, and adding other tags does nothing.
  - `StateReplacedMidRunStops`: while in Hold, call `ReplaceState` without the tag: hidden, Idle; add the tag again and check it runs again. Then `ReplaceState` with the tag: hidden, Done.

  The real checkpoint reload is checked in the owner's playtest (section 9).

Build with `Tools/mirror_build_and_test.ps1`. The real project also needs `Tools/build_and_test.ps1` **with Unreal closed**, because this adds a new class. Pass: the old 79 plus the new tests, no `Result={Fail`.

### F1 result (2026-11-05)
`Tools/build_and_test.ps1` on the real project: build succeeded, **89 passed, 0 failed** (the old 79 plus 7 unit and 3 functional apparition tests), log ends `TEST COMPLETE. EXIT CODE: 0`. The extra unit test is `ZeroDurationsComplete`. New tag `State.Test.Apparition`. The lead reviewed the logic and the actor against this section and found nothing to change.

- **Not covered by tests:** a real checkpoint reload (the tests use `ReplaceState`), how the placed instances look, and anything visual. Those are for section 8 and the owner's playtest.
- **Tool problem:** the run finished at 21:41, but `Start-Process -Wait` in the script hadn't returned about 30 minutes later, so its summary lines never printed. The cause wasn't found. Read `Saved/Logs/LBTests_All.log` directly if a run seems to take too long.

## 5. Art (technical-artist)

**Bake:** change `Tools/blender/warden/bake_silhouette.py` to keep **two slots**, `MAT_Body` and `MAT_Mask` (faces that use `M_Warden_BellMetal` in the master), with `--rotz 90`, so the mesh faces +X like `SK_Warden` and yaw means the same on both. Keep the limit of ≤ 8,000 triangles. If the decimation damages the mask, exclude it from the decimation and report.

**Import (changed at F2):** a **new asset**, `/Game/LastBell/Characters/Warden/Meshes/SM_LB_Warden_Apparition`, not a replacement, because `BP_WardenSilhouette` and the map still point at the old mesh and deleting a referenced asset can raise a dialog that freezes the editor. Nanite off, one LOD, no collision. The MIs below are its default slot materials. Facing +X with yaw 0 is checked only from the bounds until the look test.

**Materials** in `/Game/LastBell/Characters/Warden/Materials/`. Leave `M_LB_Silhouette` and `MI_LB_WardenSilhouette` alone, because `BP_WardenPlaceholderKill` still uses them.

| Asset | Settings |
|---|---|
| `M_Warden_Apparition` | Surface, **Masked**, Default Lit, two-sided. Opacity Mask = `DitherTemporalAA` with Alpha Threshold = scalar `Fade` (default 1). Base Color = vector `Color`; Roughness = scalar `Rough` (0.85); Metallic = scalar `Metal` (0); Emissive = vector `Emissive` × `Fade`. Lit, so candle and moon give it form close up instead of a flat black hole |
| `MI_Warden_Apparition_Body` | `Color` (0.012, 0.012, 0.014), `Emissive` 0 |
| `MI_Warden_Apparition_Mask` | `Color` (0.30, 0.22, 0.12), `Rough` 0.6, `Metal` 0.3, `Emissive` (0.02, 0.018, 0.015); tune `Emissive` at the look test to a range of 0–0.08 per channel |
| `M_Warden_ApparitionGlow` | Surface, Translucent, Additive, Unlit, two-sided. Emissive = `RadialGradientExponential` (radius 0.5, density 2) × vector `Color` × scalar `Strength` × scalar `Fade` (default 1) |
| `MI_Warden_ApparitionGlow` | `Color` (0.55, 0.62, 0.80), `Strength` 0.25 (tune at the look test) |

### F2 result (d29582f, 2026-11-05)
`SM_LB_Warden_Apparition`: slots `MAT_Body` and `MAT_Mask`, 7,389 triangles (mask 333, not decimated; a plain decimate cut it to 85 and damaged it), bounds X −83.81…60.88, Y −109.55…66.26, Z 0.25…284.22. Bell metal is only the mask: one island. Materials as in the table, recompiled without errors. `M_Warden_BellMetal` has `TellGlow` (default 0) and `TellGlowColor`; its Emissive wasn't connected before. Tool: `Tools/warden/apply_p12f_art.py`.

- **Warning to watch at the look test:** "nearly zero normals" on the decimated mesh could show as faint shading artefacts.
- **`SM_LB_Warden_Silhouette` reads as dirty** in this session, cause unknown. Don't save it. It goes with the old Blueprint.

## 6. Blueprint and map (unreal-blueprint-engineer, [EDITOR])

The session must be free of temporary actors: `L_Monastery` is saved here, and the session that placed the review figures must not save it. Save the map **before** any `BP_Warden` template edit (section 7), because placed instances keep stale values until a map reload.

1. Create `/Game/LastBell/Blueprints/Interactables/BP_WardenApparition`, parent `ALBWardenApparition`. `Body` = `SM_LB_Warden_Apparition`, location 0, yaw 0, scale 1; its slots take the mesh's default MIs. `Glow` = `/Engine/BasicShapes/Plane`, `MI_Warden_ApparitionGlow`, relative location (−150, 0, 150), pitch 90 so it faces actor +X, scale = `GlowSizeCm` / 100 (set from C++ at BeginPlay).
2. In `L_Monastery`, delete `BP_WardenSilhouette_C_0` and `_C_2`. Place `Apparition_Courtyard` and `Apparition_Chapel` with section 3's values. Courtyard `GlowSizeCm` 1000; Chapel 0. Outliner folder `Gameplay/Warden`.
3. **Don't delete anything in this session (changed at F2):** the undo history can still reference the removed actors, and a delete could raise a dialog that freezes the editor. After a restart, the lead checks `get_referencers` and deletes `BP_WardenSilhouette` and `SM_LB_Warden_Silhouette`, in section 9.
4. Save `L_Monastery` and each new or changed package one at a time. Never save-all. Check the never-save list in the parent plan first.

## 7. Attack light (technical-artist for the material, unreal-blueprint-engineer for `BP_Warden`, [EDITOR])

**What's there now (read by the lead, 2026-11-05, F0b):**
- `TellLight`: 800, **Unitless**, inverse-squared falloff, radius 160, colour (1, 0.078, 0.039), no shadows, volumetric scatter 1, `bVisible` false. Template location (16, 0, 274), which only makes sense under `PlaceholderBody` (0, 0, −110), so it's measured from the floor.
- `BeginPlay`: `K2Node_CallFunction_15` (`BindtoBrain`), then `K2Node_CallFunction_19` (`AttachTellLightToMask`).
- State-changed event (`K2Node_CustomEvent_5`) calls `PlayStateFeedback(NewState)`, which is **empty**.
- Windup event (`K2Node_CustomEvent_6`) calls `PlayWindupTell`, also empty, then `ShowWindupTell(Seconds)`: shows `TellLight` and sets a timer for `EndWindupTell`, which hides it.
- In `LBWardenBrainComponent`, entering `Attack` broadcasts `OnAttackWindup`. Don't rely on the order of that and the state-changed event.

**Light (replaces the "PlaceTellLight" idea, because no runtime attach is needed):**
- Remove the call to `AttachTellLightToMask` from `BeginPlay`, and delete the function. Socket `mask` stays on the skeleton for Phase 13.
- On the `TellLight` template, set relative location **(110, 0, 235)**: about 40 cm in front of the mask at face height, measured from the floor. **Confirm the parent first:** the placed `BP_Warden_C_0`'s `TellLight` must end up at actor location + (110, 0, 125), rotated with the actor. If its parent isn't `PlaceholderBody`, work out the equivalent value and report it.
- Radius 160 → 700. Intensity 800 → 5000 at first, range 3000–10000, Unitless as now. Still no shadows. Tune in section 8.

**Mask glow:**
- `M_Warden_BellMetal`: add scalar `TellGlow` (default 0) and vector `TellGlowColor` (1, 0.06, 0.02). Emissive = `TellGlowColor` × `TellGlow` × 8. Validate only this material. Other materials are untouched.
- `BP_Warden`: variable `MaskGlowMID` (`MaterialInstanceDynamic`) and variable `LastFeedbackState` (`ELBWardenState`, default Dormant).
- New function `SetupMaskGlow`, called from `BeginPlay` after `BindtoBrain`, in the place of the removed call: on `CharacterMesh0`, `GetMaterialIndex("M_Warden_BellMetal")`, `CreateDynamicMaterialInstance` on that index, stored in `MaskGlowMID`. The slot is found by name, never a fixed index.
- New function `SetMaskGlow(Level)`: if `MaskGlowMID` is valid, `SetScalarParameterValue("TellGlow", Level)`.

**Levels:**

| Where | Add |
|---|---|
| `PlayStateFeedback(NewState)` | Store `LastFeedbackState`. Chase: `SetMaskGlow(0.25)`. Attack: leave it alone, because the windup handles it. Any other state: `SetMaskGlow(0)` |
| `ShowWindupTell` | `SetMaskGlow(1)`, as well as showing the light |
| `EndWindupTell` | After hiding the light: `SetMaskGlow(0.25)` if `LastFeedbackState` is Chase, otherwise `SetMaskGlow(0)` |

**AI timings don't change:** the windup stays 0.6 s, `DA_WardenTuning` is untouched. Read graphs with `find_nodes` and `get_node_infos`, never `read_graph_dsl`. `write_graph_dsl` can't extend an existing event, so follow `MCP_NOTES.md` ("Skeletal meshes and the Warden") and P12-8's method in `Tools/warden/apply_p12_warden.py`.

**Checks:** `Tools/warden/check_warden.py`: update the `BP_Warden` and silhouette checks to the new values and add `--bp` checks for `BP_WardenApparition`, both placed instances and all section 3 values. The suite must still pass, including `Functional.Warden.Attack.*`.

## 8. Look test (lead, about 10 minutes of capture, needs the owner)

Tell the owner first: Unreal must stay in front and the PC left alone; offer "wait". Agents don't run the capture tool.

New `Tools/warden/apparition_review.py` (temporary `P12F_` actors, same rules as `read_review.py`; never save the map while they exist), `--poses`, `--place`, `--status`, `--remove`.

| View | Camera (x, y, z, looking at) | What's judged |
|---|---|---|
| Roofline ×3 | (500, 0, 170), at Y 1300 / 1800 / 2300 | Which spot reads best. Mean brightness of the figure against the sky right beside it: figure at most a quarter of the sky's. Glow looks like sky, not like a card. Pale mask visible |
| Rail ×3 | (8720, 0, 195) with the candle proxy, at Y −250 / −120 / 0 | Reads as a solid dark figure, not a flat hole. Backdrop. Rail in front at waist height |
| Sacristy ×2 | (8650, −300, 165) and (8350, −300, 165), at (8500, −930) | Framed by the doorway against the candlelit wall |
| Light ×2 | ossuary and bells 3 m spots from `read_review.py`, `SK_Warden`, temporary light at the new offset with candle proxy | Mask, chest and hands clearly red; floor and nearby wall visibly red |

Corrections allowed without returning to the owner: the values in section 3 (positions only among those listed), glow `Strength`, mask `Emissive`, light intensity and radius within range. **If the figure still looks flat at the rail after tuning, stop and show the owner**, with the full `SK_Warden` shown at that spot for comparison. Send the owner the sheet in any case.

## 9. QA, docs and owner playtest

**Lead, in a restarted session:** `get_referencers`, then delete `BP_WardenSilhouette` and `SM_LB_Warden_Silhouette`. If anything still references them, stop and report.

**qa-reviewer:** suite, `check_warden.py` (all modes), output log, and the failure-mode table below by reading the code and the assets. Report honestly what can't be seen automatically.

**Docs:**
- `DECISIONS.md`: D-092 (the appearances: reason, one-shot look gate, stations rather than walking).
- `RISKS.md`: R-54 (the dithered fade might shimmer on a small distant figure; check in play). R-52 gets the Walk finding.
- `TECHNICAL_DESIGN.md` §8 and line 166 (`ALBWardenApparition`), `GREYBOX_SPEC.md` steps 2 and 7, `LEVEL_DESIGN.md`, `ASSET_REGISTRY.md` where affected, `IMPLEMENTATION_PLAN.md`, `MCP_NOTES.md` (anything new).
- `P12_WARDEN_VISUAL.md`: pointer to this plan. Add to its Phase 13 notes: **Walk must be reworked** (arm swing, upper body, planted feet, natural speed near patrol's 140 cm/s), and **the chapel gets a real walk** from the rail into the sacristy, replacing `Apparition_Chapel`'s second station, stooping through the doorway if it needs to (owner, D1).

**Owner, about 15 minutes:** `scalability 2`, `r.SetRes 1920x1080w`, `stat unit`, Warden on.
1. `lb.NewGame`, enter the courtyard: roofline fades in, holds, fades out, stands out enough?
2. Candle puzzle, altar, turn around: figure at the rail, then in the sacristy? Frightening, and is it clear where to go?
3. Crypt: does the mask glow during the chase? Get caught once: is the red strong enough, and does the reload work without repeating the beats?
4. Still open from the first playtest: feet on the floor, faces the way it moves, crypt `Game:` reading.

Then "PHASE 12 READY FOR YOUR REVIEW". Merge only on "approve and merge".

## 10. Failure modes

| Case | Expected |
|---|---|
| Player never looks at the roofline | Never appears; nothing is blocked |
| Player stares at the rail spot before using the altar | Can't happen at the altar: reach is 200 cm and the rail is behind them. If reached by console, it fades in where they're looking, which is acceptable |
| Player runs at the figure | Fades out from the current alpha at the min distance |
| Player is already at the sacristy door when station 2 is due | Skipped; Done |
| Checkpoint reload after the tag | Stays hidden; no repeat |
| `lb.NewGame` mid-beat | Stops, hidden, returns to Idle |
| `lb.Warden.Enabled 0` | Appearances still play; they aren't the AI, same as the old silhouettes |
| Nothing else may change | Capsule, navigation, AI values, suite tests, `DA_WardenTuning`, every other material |

## 11. Order

| Task | Scope | Owner | Needs | Depends on |
|---|---|---|---|---|
| F0a | D-092, R-54 and the plan updates | lead | Nothing | owner's go |
| F1 | Section 4 | gameplay-programmer | Unreal closed for the real build | F0a |
| F2 | Section 5 | technical-artist [EDITOR] | Unreal open on the new binaries | F1 |
| F3 | Section 6 | unreal-blueprint-engineer [EDITOR] | Clean session | F2 |
| F0b | Read `BP_Warden` and `TellLight`, finish section 7. **Done** | lead | Unreal open | F1 |
| F4 | Section 7 | technical-artist, unreal-blueprint-engineer [EDITOR] | | F0b |
| F5 | Section 8 | lead + owner | Capture session | F4 |
| F6 | Section 9 | qa-reviewer, lead, owner | Playtest | F5 |

Only one editor agent at a time. Each commits on this branch only: no switching, merging or pushing.
