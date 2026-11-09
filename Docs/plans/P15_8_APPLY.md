# P15-8: apply the look-session choices, rain columns, drips, player flame

Owner's "go": 2026-11-09. Source of every value: `P15_PARTICLES.md` Results "P15-7: look session". One editor agent (lighting-vfx, Sonnet, high effort). Unreal open on `L_Monastery`, PIE off. The editor was restarted after P15-7, so **nothing from the session is in memory**: every value is set here.

## 0. Rules
- **Process rules** (all from CLAUDE.md):
  - read `Tools/mcp/MCP_NOTES.md` first;
  - check every result;
  - never start PIE, never run captures;
  - never `MaterialInstanceTools.set_parent`, never `read_graph_dsl`;
  - never save `M_LB_Surface` or any never-save Blueprint (list in CLAUDE.md / `p15_level.NEVER_SAVE`);
  - commit only on `claude/phase-15-particles`, staging by path; never push.
- **Explicit saves only**, one package per `save_assets` call, then `is_dirty` false. The packages to save are listed in §7; save nothing else.
- **In-place edits only for assets the level references** (`NS_LB_Drip`, `NS_LB_EaveDrips`, the MIs, `M_LB_Flame`, `DA_StormFX`). **Never** call `p15_5_niagara.make_system` / `build_*` on `NS_LB_Drip` or `NS_LB_EaveDrips`: it removes and re-adds the user variables, which can drop the placed actors' overrides. Edit their module inputs and renderer properties in place. `M_LB_Flame` may be rebuilt with `p15_4_materials.py`, which keeps the asset and recreates its expressions, as P15-4 did.

## 1. Data: `DA_StormFX` (`/Game/LastBell/Data/DA_StormFX`)
| Field | Value | Now |
|---|---|---|
| `RainSpawnRate` | **50000** | 35000 |
| `SplashRate` | **1600** | 2500 |
| `SkyBoltDistance` | **30000** | 60000 |
| `SkyBoltTopHeight` | **30000** | 22000 |
| `SkyBoltChance` | Ambient **0.9**; Scripted 1.0, WardenReveal 0.5, Apparition 0.5, Debug 1.0 unchanged | Ambient 0.6 |
| `DebugBolt` | −1 (read back) | −1 |

All other fields unchanged; read the whole set back. `DA_StormSettings` is not changed. Read its `DebugFreezeFlash`, `DebugIntensityOverride` (−1) and `FXSettings` (→ `DA_StormFX`), and save it only if `is_dirty` says so.

## 2. Material instances (`/Game/LastBell/Materials/Instances/FX/`, `set_scalar_parameter` only)
| MI | Parameter | Value | Now |
|---|---|---|---|
| `MI_LB_Rain` | `RainBase` | **0.25** | 0.035 |
| `MI_LB_Splash` | `SplashBase` | **0.18** | 0.08 |
| `MI_LB_Ripple` | `RippleBase` | **0.2** | 0.05 |
| `MI_LB_WaterMist` | `MistBase`, `MistOpacity` | **0.28, 0.26** | 0.06, 0.08 |
| `MI_Flame_Torch` | `EmissiveStrength` | **7** | 12 |
| `MI_Cloth_Linen_Dark` | `AmplitudeCm` | **18** | 30 |

`MI_LB_RainCurtain`, `MI_LB_Mist`, `MI_Flame_Candle` and the other MIs are not touched.

## 3. Player flame: no vibration (cause: `M_LB_Flame`'s mesh random hashes `ObjectPositionWS`, so a moving flame gets a new random every frame)
1. **`M_LB_Flame`** (`Tools/fx/p15_4_materials.py` `m_flame`):
   - after `rnd = sw(rnd_s, rnd_m)`, insert `rnd = lerp(rnd, FixedSeed, UseFixedSeed)`;
   - two new scalar parameters in group `Flicker`: `UseFixedSeed` default **0** and `FixedSeed` default **0.37**;
   - everything else stays identical.

   Rebuild only this master: `python -I Tools/fx/p15_4_materials.py flame`, or the script's equivalent step name. Then:
   - compile: 0 errors;
   - read back `MI_Flame_Candle` and `MI_Flame_Torch`: their parameters unchanged, and their parent still `M_LB_Flame`;
   - save `M_LB_Flame`.
2. **New MI `MI_Flame_Candle_Player`** in `/Game/LastBell/Materials/Instances/FX/`:
   - created with `MaterialInstanceTools.create` with its parent `M_LB_Flame` given at creation (the P15-4 `make_mis` call); this is not a reparent;
   - scalars `NoiseSpeed` 0.6, `FlickerSpeed` 7, `EmissiveStrength` 8, `UseFixedSeed` **1**, `FixedSeed` 0.37;
   - static switch `bSprite` false.

   Add it to the `p15_4_materials.py` MI table so a rebuild recreates it. Save it.
3. **`BP_LBCharacter.CandleFlame`** (component template; the method P15-6 used):
   - slot-0 material `MI_Flame_Candle_Player`;
   - relative scale **(23.3333, 23.3333, 5.83333)** (world scale 0.7, 4.55 cm tall; set one axis per write, see MCP_NOTES);
   - relative location unchanged (0, 0, 50.6667): the mesh pivot is at its base, so the flame stays on the wick;
   - mesh unchanged (`SM_LB_Prop_CandleFlame_A`).

   Compile with `warnings_as_errors` (no new errors or warnings) and save `BP_LBCharacter`.

## 4. Drips: visible (in-place edits of `NS_LB_EaveDrips` and `NS_LB_Drip`, emitter `Drops`)
| Setting | Now | New |
|---|---|---|
| Eave spawn rate | 6 /s | HLSL expression **`User.LineLength * 0.04`** (4 drops per metre per second: `ClS` 1100 cm gives 44 /s) |
| Falling drop, renderer A size | (0.5, 5) cm | **(1.0, 14)** cm (both systems) |
| Falling drop colour alpha | read it | **1.0** (both systems; RGB unchanged) |
| Crown (renderer B, `CrownSize`) | 6 cm | **10 cm** (both systems) |
| Ring (renderer C, `RingSize`) | 2 → 18 cm | **3 → 26 cm** (both systems; the ring still shows only with `User.bWater`) |
| `NS_LB_Drip` user default `User.Interval` | (1.5, 4) s | **(0.8, 2.5)** s (no placed actor overrides it; P15-6 left it at the default) |

Where a size or colour is set by a SetParameters HLSL expression rather than a literal, change the constant inside the expression; record which it was. After the edits:
- `GetSystemCompileState` is UpToDate with 0 errors and `GetStackIssues` shows none new;
- update `p15_5_niagara.py check` so its expectations match the new values, and run it: all PASS;
- save `NS_LB_EaveDrips` and `NS_LB_Drip`.

**Then run `p15_level.py --check --only drips,eaves`.** The placed actors' `User.FallHeight`, `User.LineLength` and `User.bWater` overrides must still read back. If any were lost, re-apply them with `--apply --resume --only drips,eaves` and report it.

## 5. Rain columns: new system `NS_LB_RainColumn` plus 3 placed actors
**The system** (`/Game/LastBell/FX/Niagara/NS_LB_RainColumn`, a new asset, so building from scratch is safe):
- **How to build:** parameterize `p15_5_niagara.py build_rain` (name, rain sprite size, GroundMist on or off) and add a builder and a check for `NS_LB_RainColumn`. `NS_LB_Rain` must stay byte-for-byte the same: don't rebuild or save it.
- **Same as `NS_LB_Rain`:** both GPU emitters `Rain` and `Splash`, the distance-field collision (rain radius 20, kill; splash radius 6, the pin chain), and the fixed bounds ±4000 / Z −1000…+3000.
- **Differences:**
  - **no `GroundMist` emitter**;
  - the `Rain` sprite size is Random Non-Uniform **(1.4, 36) to (1.4, 54)**, not (0.7, 28) to (0.7, 42);
  - user variable defaults:
    - `RainRate` 6000, `BoxHalf` 300, `SpawnHeight` 2000;
    - `FallMin` 1100, `FallMax` 1400;
    - `Wind` (0, 0, 0) (`Vector3f`);
    - `SplashRate` 400, `SplashRadius` 270, `Mist` 0.

  Keep all nine user variables so the names match `NS_LB_Rain`.
- Compile: UpToDate, 0 errors. Save.

**Placed actors** (`add_to_scene_from_asset`, folder `FX/Storm`, rotation 0, scale 1; location = the opening's centre XY at the floor Z). Set all six user parameters below on each actor and read them back.

| Label | Location | `RainRate` | `BoxHalf` | `SpawnHeight` | `SplashRate` | `SplashRadius` | Opening (F0.3) |
|---|---|---|---|---|---|---|---|
| `FX_RainColumn_Chapel` | (6500, −418, 0) | 7000 | 300 | 2050 | 400 | 270 | `Ch_Roof_S1` hole X 6250…6750, Y −643…−193, roof Z 1399…1935 |
| `FX_RainColumn_Cloister` | (11085, 2517.5, 0) | 7400 | 310 | 1150 | 420 | 280 | open sky X 10900…11270, Y 2260…2775, roof hole Z 640…1046 |
| `FX_RainColumn_Belfry` | (12187.5, 1687.5, 2500) | 5200 | 260 | 2000 | 300 | 235 | `TWA_Roof` collapse X 11975…12400, Y 1475…1900, Z 3530…4400 |

- **Density:** about 5 times the open rain (50000 /s over 36 × 36 m = 38.6 per m² per s, so a column gets about 193 per m² per s). Drops that land on the roof outside the hole die there through the distance-field kill.
- **Floor Z:**
  - Chapel and cloister: 0, from the pawn's Z of 91.7 and 90.2 in P15-7.
  - Belfry: 2500, from F0.8 (`Belfry_N_wall` 3700.9 − 1200.9).

  Report as EYE lines, for each column: the max Z of the floor mesh actor whose XY bounds contain the location (the highest one below the opening), and the gap. Do not move a column on that basis; the lead judges in P15-9.

## 6. Level edits (`Tools/fx/p15_level.py` updated to the P15-8 final state)
Update the script's tables so `--apply` / `--check` describe the final level:
- **Delete** (if present; `--check` fails if any still exists):
  - the 8 curtain actors `FX_RainCurtain_N_600`, `_N_2400`, `_N_4200`, `_N_6000`, `_N_8000`, `_N_11500`, `_N_14500`, `_S_11500`;
  - the 6 cloth actors `FX_Cloth_Belfry_N2`, `FX_Cloth_Cloister_N_1`, `FX_Cloth_Cloister_W_1`, `FX_Cloth_Belfry_W1`, `FX_Cloth_Belfry_E1`, `FX_Cloth_Belfry_S2`.
- **Cloth that stays** (unchanged values, `bHidden` false): `FX_Cloth_Slit_F03`, `FX_Cloth_Slit_F07`, `FX_Cloth_Cloister_S_2`, `FX_Cloth_Gate_Inner`. The assets `SM_LB_FX_CurtainCard`, `M_LB_RainCurtain` and `MI_LB_RainCurtain` stay in the project, unused, and are not saved.
- **Fires `User.Scale`:** `FX_Torch_Fire_NS`, `FX_Crypt_Torch_T1_NS`, `_T2_NS` and `_T3_NS` **0.7**; `FX_Crypt_Brazier_NS` **1.3**; `FX_FirePit_Fire` stays **1.4**.
- **New step `columns`** (§5).
- **New check steps:**
  - `mis`: the §2 values and the §3 MI;
  - `assets`: the §3 material parameters, the §4 values via read-back, and `NS_LB_RainColumn` exists.
- **`data` check:** the §1 values replace the §2.2 defaults for the five changed fields.
- **Census:** `CENSUS_START` stays 3015. New actors = 1 + 11 + 2 + 10 + 7 + **4** cloth + **0** curtains + 1 (fires 6 − 5) + **3** columns = **39**, so the target is **3054**. Before P15-8 the census is 3065.

## 7. Save (only when `p15_level.py --check` and `p15_5_niagara.py check` are all PASS and the census is 3054)
These packages, one per call, each followed by `is_dirty` = false:
- the Niagara systems `NS_LB_RainColumn`, `NS_LB_EaveDrips`, `NS_LB_Drip`;
- `M_LB_Flame`, `MI_Flame_Candle_Player`;
- the §2 MIs `MI_LB_Rain`, `MI_LB_Splash`, `MI_LB_Ripple`, `MI_LB_WaterMist`, `MI_Flame_Torch`, `MI_Cloth_Linen_Dark`;
- `BP_LBCharacter`, `DA_StormFX`, `DA_StormSettings` (only if dirty), then `/Game/LastBell/Maps/L_Monastery`.

Afterwards:
- read `is_dirty` on the never-save list and on `NS_LB_Rain`: all false;
- report anything else that reads dirty, and don't save it.

## 8. Record and commit
- **Record:** `Docs/ArtTest/fx/p15_8_apply.md`, covering:
  - per step: done, PASS or FAIL;
  - the before and after values;
  - how each drip size or colour was set (literal or expression);
  - the column floor EYE lines;
  - the check summaries, the census and the saved packages.
- **`Tools/mcp/MCP_NOTES.md`:** add any new learning.
- **Commit:** the scripts, the record, the notes, and the saved content files that `git status` shows (never `Config/DefaultEditor.ini`). End with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- **Out of scope:** the suite, which needs Unreal closed; the lead runs it.

## 9. Acceptance (agent)
- `p15_level.py --check`: all PASS, census 3054.
- `p15_5_niagara.py check`: all PASS, `NS_LB_RainColumn` included.
- `M_LB_Flame` compiles; `BP_LBCharacter` compiles clean.
- Every §7 package is saved and not dirty; nothing else is saved.
- **Seen at run time only in P15-9 (owner):**
  - the columns read as rain under the three openings;
  - the drips are visible;
  - the player flame no longer vibrates at 4.55 cm.
