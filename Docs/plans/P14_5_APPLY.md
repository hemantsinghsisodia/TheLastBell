# P14-5: apply the P14-4 choices, exposure targets, story-change readability

Owner approval: "go", 2026-11-08. Branch `claude/phase-14-lighting-storm`. Parent plan: `Docs/plans/P14_LIGHTING_STORM.md` (sections 9.2, 9.3, 8, 10; the P14-4 results and choices at its end).
Parts: **A** (lighting-vfx agent, Sonnet high, editor), **B** (lead + owner, captures), **C** (lighting-vfx agent: write the final EVs and any fallbacks). Each part ends with a report; B and C are planned in detail here but start only after A is reviewed.

## Part A: apply and save the choices (agent)

### A1. `DA_StormSettings` (`/Game/LastBell/Data/DA_StormSettings`)
Read every field first and print them. Then set exactly these four (camelCase over MCP):

| Field | Saved now | Set to |
|---|---|---|
| `phaseSpeedHigh` | 2.4 | **6.5** |
| `windBaseHigh` | 0.65 | **0.8** |
| `gustHigh` | 0.4 | **0.5** |
| `gustFrequency` | 0.12 | **0.2** |

Before saving, assert these read back exactly (they are preset B, the owner's choice, and the debug fields): `flashLux` 8, `spotFlashGain` 3, `fillFlashGain` 1.5, `skyFlashGain` 0.6, `domeFlashGain` 6, `domeFlashAdd` 0.05, `glassFlashGain` 2.5, `shaftFlashGain` 3, `poolFlashGain` 2.5, `revealGain` 4, `revealEmissive` 3, `debugFreezeFlash` −1, `debugIntensityOverride` −1, `phaseSpeedLow` 1.2, `windBaseLow` 0.2, `gustLow` 0.15. If any differs, set it to the value listed here (the lead's live session may have left it in memory) and report it. Every other field must equal what you printed at the start. Save the package (one call), `is_dirty` false after.

### A2. Wind amplitudes on 8 MIs (`/Game/LastBell/Environments/Courtyard/Materials/`)
`MaterialInstanceTools.set_scalar_parameter` `WindAmplitudeCm` only (**never `set_parent`**, never a static switch):

| MI | Saved (f9261e6) | Set to |
|---|---|---|
| `MI_Foliage_GrassMedium02` | 30 | **38** |
| `MI_Foliage_NettlePlant` | 18 | **24** |
| `MI_Foliage_WeedPlant02` | 12 | **16** |
| `MI_Foliage_Fern02` | 18 | **24** |
| `MI_Foliage_WildRooibos` | 14 | **18** |
| `MI_Foliage_SearsiaLucida` | 12 | **16** |
| `MI_Ivy_Green` | 4 | **5** |
| `MI_Ivy_Dead` | 4 | **5** |

`WindRefHeightCm` stays (60, 45, 30, 45, 60, 150; ivy none). Before/after diff per MI: parent, textures, vectors, all scalars, `bUseARM` and `bWind`: only `WindAmplitudeCm` may change. Save each MI (one call each), `is_dirty` false after.

### A3. `L_Monastery` (saved **once**, at the end of A3)
Census first (`find_actors` empty name, editor world only): expect **3015**, and 3015 again before the save.

1. **`PP_Chapel`:** `settings.autoExposureMinBrightness` = `autoExposureMaxBrightness` = **1.6** (both overrides stay true).
2. **Grade B on `PostProcess_Exposure`** (the unbound global volume): set these `settings` fields with their `bOverride_*` true:
   - `colorSaturation` (0.92, 0.95, 1.0, 0.85)
   - `colorContrast` (1, 1, 1, 1.06)
   - `colorGammaShadows` (0.97, 1.0, 1.06, 1)
   - `colorGainHighlights` (1.04, 1.0, 0.94, 1)
   - `filmGrainIntensity` 0.18
   - `vignetteIntensity` 0.45

   Vectors are `{"x","y","z","w"}`. Nothing else on that volume changes (its EV 3 stays).
3. **Clear the per-area shadow saturation:** `bOverride_ColorSaturationShadows` = **false** on `PP_Outdoor_Night`, `PP_Cloister`, `PP_Chapel`, `PP_Tower` (leave the stored value). `PP_Crypt` and `PostProcess_Exposure` have no such override: confirm it stays false.
4. **`RV_WellHouse_Tally`:** location (1350, −1775, **115**) (was Z 140). Rotation (0, −90, 90) and `DecalSize` (10, 40, 60) unchanged.
5. **`RV_Chapel_Circle`:** location (**8150, −91**, 0.5) (was 8265, −255). Rotation (−90, 0, 0) and `DecalSize` (10, 90, 90) unchanged. Why there: the S2 pool decal (`Ch_Pool_S2`, centre (8265, −255), yaw 35, `DecalSize` 15 × 80 × 360) is a 720 × 160 cm stripe along (0.819, 0.574); the new centre is 200 cm off its centreline toward the aisle (half-width 80 + circle radius 90 + 30), beside its middle, clear of `Ch_Pew_S4` (X ≤ 7934) and the altar rail.

Read back every changed field and every volume's EV, priority, blend and override set (all five area volumes and `PostProcess_Exposure`). `L_Monastery` must be the only dirty level package; save it once; `is_dirty` false after; census 3015.

### A4. Scripts (so no older script reverts or fails on the new state)
- **New `Tools/lighting/p14_5_apply.py`** with `--apply` (A1–A3, idempotent, never saves; the saves are separate explicit calls) and `--check` (PASS/FAIL per item above; exit 1 on any FAIL).
- **`Tools/lighting/p14_3_level.py`:** make it match the new state.
  - `PP_Chapel` EV 1.6, while `PP_Tower` stays 0.65. The new volumes can no longer share one `PP_EV`, so give each volume its own EV.
  - `ColorSaturationShadows` is no longer an override on `PP_Cloister`, `PP_Outdoor_Night` and the two new volumes, so the expected override set becomes the two EV overrides only.
  - The `RV_WellHouse_Tally` and `RV_Chapel_Circle` rows of `DECALS` take the new values.
  - Add a comment "P14-5 (owner's P14-4 choices)" at each change.
  - Then run `p14_3_level.py --check`: all PASS.
- **`Tools/lighting/p14_4_wind_fix.py`:** the expected amplitudes in `check` become the A2 values (comment "P14-5"). Then run `check`: all PASS.
- **Do not touch** `Tools/crypt/capture_session.py`, `Tools/crypt/capture_poses.py`, `Tools/lighting/pie_pp.py` or any `Tools/lighting/pie_*.py` (the lead edits these for Part B).

### A5. Tests
After the saves, run the headless suite with the editor open (the P14-3 command; log `Saved/Logs/LBTests_P14_5a.log`): expect **128** `Result={Success}`, 0 `Result={Fail`. The only allowed `Error:` is the HttpListener port line.

### A6. Records and commit
- Plan `Docs/plans/P14_LIGHTING_STORM.md`: a "### P14-5a result (2026-11-08)" subsection with every read-back.
- `MCP_NOTES.md` only for a genuinely new lesson.
- Commit by path on the current branch. Commit: the DA, the 8 MIs, the map, the scripts and the plan. Sonnet trailer. Never switch, merge or push.

### Rules for Part A
- Editor open on `L_Monastery`, PIE off. Check `IsPIERunning` before each save; never start PIE/Simulate, never capture, no synthetic input.
- One package per save call, never save-all. Never save `M_LB_Surface` or the Blueprints `BP_SmallBell`, `BP_SequencePuzzle`, `BP_Inscription`, `BP_RitualMechanism`, `BP_Door_Base`, `BP_TagInteractable`, `BP_TagTrigger`, `BP_EndingTrigger`, `BP_Inspectable_Note`, `BP_Door_Base_Dungeon`, `BP_RitualMechanism_CryptWinch`, `BP_WardenApparition`.
- If `M_LB_Surface` or any of those Blueprints is dirty at any point: STOP, report.
- On a hang over 180 s or a crash: STOP, no retried mutations, no saves, report the step.

## Part B: exposure targets and story-change readability (lead + owner)
Method (parent plan 9.3):
- PIE Simulate started by the lead, kept running across batches.
- `DebugFreezeFlash` 0 (no flash) in memory.
- The candle proxy: the PIE copy of `Light_Approach_0` retargeted as `TMP_CaptureLight`, with `DA_PlayerTuning`'s `CandleIntensity`, `CandleAttenuationRadius` and `CandleTemperature`, Candelas, no shadows, `--light-offset 36 14 -10`.
- The 16 poses of `Tools/lighting/poses/p14_viewpoints.json`, written to `Docs/ArtTest/lighting/p14_5/`.
- Metrics from `Tools/crypt/luma_report.py`: mean and central-40 %.

**Targets:**

| Area | Viewpoints | Volume (EV now) | Mean target | Central-40 % floor |
|---|---|---|---|---|
| Courtyard | `cy_west_front_15m`, `cy_tall_north_15m`, `cy_lantern_gate_3m`, `p14_cy_tower_reveal` | `PP_Outdoor_Night` (1.15) | 0.04 – 0.07 | ≥ 0.025 |
| Chapel | `ch_tall_east_15m`, `ch_candle_altar_3m`, `ch_sacristy_3m` | `PP_Chapel` (1.6) | the first B1 value at EV 1.6 ± 20 % (owner's choice) | ≥ 0.030 |
| Crypt | `cr_tall_ossuary_15m`, `cr_chain_chamber`, `cr_torch_t1_3m` | `PP_Crypt` (0.2) | 0.025 – 0.05 | ≥ 0.020 |
| Cloister | `cl_tall_north_15m`, `cl_lantern_bells_3m`, `ps_lantern_joints` | `PP_Cloister` (0.65) | 0.04 – 0.07 | ≥ 0.025 |
| Tower | `tw_mid_stair`, `tw_belfry`, `tw_base` | `PP_Tower` (0.65) | 0.035 – 0.06 | ≥ 0.025 |

**Owner's decision (2026-11-08):** the area's mean target applies to the mean over its **wide views only**:
- Courtyard: `cy_west_front_15m`, `cy_tall_north_15m`, `p14_cy_tower_reveal`.
- Chapel: `ch_tall_east_15m`.
- Crypt: `cr_tall_ossuary_15m`.
- Cloister: `cl_tall_north_15m`.
- Tower: `tw_mid_stair`, `tw_belfry`.

The lantern close-ups only need the floor; the floor applies to **every** viewpoint. Averaged over every view, the lantern close-ups put the courtyard, cloister and tower about 2× above target. Meeting that would mean about 1 stop darker overall, which would undo the look the owner already approved. The tool is `Tools/lighting/area_targets.py`.

**B1. Baseline:** capture the 16 poses and compute the metrics.
**B2. Exposure loop:**
- Change only an area's EV, on the PIE-world volume (`pie_pp.py ev <volume> <EV>`), in steps of 0.25. Keep EV min = max.
- Re-capture only that area's poses. At most 3 rounds per area.
- If an area can't meet both its mean and its floor, stop and report the trade-off to the owner. Don't go past ±1.0 EV from today's value without asking.
**B3. Story changes:** between capture batches the owner types into the Output Log Cmd box, and after each the affected poses are re-captured:

| After the owner types | Groups that change (section 8) | Re-capture |
|---|---|---|
| `lb.State.Add State.Ritual.1` | `SLG_Chapel_Altar` flicker 0.25, `SLG_Chapel_Dais` off | the 3 chapel poses |
| `lb.State.Add State.Ritual.2` | `SLG_Crypt_Torches` flicker 0.6, `SLG_Crypt_Niches` off | the 3 crypt poses |
| `lb.State.Add State.Event.CloisterEntered`, then `lb.State.Add State.Ritual.3` | Cloister bells / west flicker 0.85, then west and entry off, tower landings flicker 0.9 | the 3 cloister poses + `tw_mid_stair`, `tw_base` |
| `lb.State.Add State.Event.TowerTop` | `SLG_Tower_Bell` flicker 0.8 | `tw_belfry` |

- Each pose's floor must still hold. If it fails, the section 8 fallback applies: that group's Off becomes Dim at scale 0.3, or the Flicker scale goes up by 0.2. Try it on the PIE-world group first and re-capture.
- The lead also checks by eye that the lantern glass of `CLA_Lantern_West` and `SHA_Lantern_Entry` is dark after `State.Ritual.3` (D-099 acceptance).

**B4. R-09** (noise and light leaks): from the B captures, list only what blocks approval. The fixes, in order, are 9.2 item 1 or 2. Otherwise report.

Output: `Docs/ArtTest/lighting/p14_5/` (PNGs plus `luma_*.json`) and a results table in the parent plan, "### P14-5b result".

## Part C: write the final values (agent, after B is reviewed)
- Set the final per-area EVs from B on the editor-world volumes.
- Apply any section 8 fallback that B confirmed to the editor-world `SLG_*` rule, and record it in DECISIONS.
- Apply any R-09 fix B listed.
- Update `p14_5_apply.py`'s expected values and `p14_3_level.py`, then run both `--check`s.
- Save `L_Monastery` once and run the suite (128).
- Commit, and add "### P14-5c result" to the parent plan.
The exact values come from B and are written into a short Part C table in this file before the agent starts.
