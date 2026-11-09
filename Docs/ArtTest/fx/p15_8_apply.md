# P15-8 record: look-session apply, player flame, drips, rain columns (2026-11-09)
Spec: `Docs/plans/P15_8_APPLY.md`. The editor work was done by lighting-vfx (Sonnet, high effort). The agent was cut off after it started the final `--save` run; the lead watched that run finish and wrote this record. The full output of the save run (check + saves) is in `p15_8_save_check.log`.

| Spec section | Result | Read-backs and notes |
|---|---|---|
| §1 `DA_StormFX` | PASS | RainSpawnRate 50000, SplashRate 1600, SkyBoltDistance 30000, SkyBoltTopHeight 30000, SkyBoltChance Ambient 0.9 (others unchanged), DebugBolt −1. `DA_StormSettings`: FXSettings → DA_StormFX, both debug fields −1, not dirty, so not saved |
| §2 MIs | PASS | `MI_LB_Rain` RainBase 0.25; `MI_LB_Splash` SplashBase 0.18; `MI_LB_Ripple` RippleBase 0.2; `MI_LB_WaterMist` 0.28 / 0.26; `MI_Flame_Torch` EmissiveStrength 7; `MI_Cloth_Linen_Dark` AmplitudeCm 18. Set with `set_scalar_parameter` only; the `p15_4_materials.py` MI table now holds the same values |
| §3 player flame | PASS | `M_LB_Flame` rebuilt with `rnd = lerp(rnd, FixedSeed, UseFixedSeed)` (defaults 0.37 / 0); compiles clean; `MI_Flame_Candle` / `MI_Flame_Torch` keep their parameters and parent. New `MI_Flame_Candle_Player` (parent given at creation; UseFixedSeed 1). `BP_LBCharacter.CandleFlame`: that MI, relative scale (23.3333, 23.3333, 5.83333) = world 0.7, 4.55 cm tall, location and mesh unchanged; compiles clean with warnings as errors |
| §4 drips | PASS | Edited in place (`p15_5_niagara.py drips8`; `build` now refuses `NS_LB_Rain`, `NS_LB_Drip` and `NS_LB_EaveDrips` when they exist). Literals: falling drop sprite size (1, 14), colour alpha 1, spawn `CrownSize` (10, 10), spawn `RingSize` (3, 3). Inside HLSL expressions: the update-chain colour alpha 0.5 → 1, `RingSize` `lerp(3, 26, ...)`. Eave spawn rate `User.LineLength * 0.04`. `NS_LB_Drip` `User.Interval` default (0.8, 2.5). Both systems UpToDate, 0 errors, check 152 PASS. The placed overrides survived (`--check --only drips,eaves` 17 PASS, nothing re-applied) |
| §5 rain columns | PASS | `NS_LB_RainColumn`: parameterised `build_rain`, no GroundMist, Rain sprite (1.4, 36)–(1.4, 54), column defaults; UpToDate, 0 errors, check 113 PASS. `FX_RainColumn_Chapel` / `_Cloister` / `_Belfry` placed in `FX/Storm` with the five table parameters read back (the spec text said "six"; its table lists five). `NS_LB_Rain` not touched |
| §6 level | PASS | Deleted the 8 curtains and 6 cloth; the 4 kept cloth read `bHidden` false; fire `User.Scale` 0.7 (5 torches), 1.3 (brazier), 1.4 (fire pit). Curtain assets kept, unused, not saved. `p15_level.py` describes the final state (new steps `columns`, `mis`, `assets`) |
| Checks | PASS | `p15_level.py --check` (inside `--save`): **157 PASS, 0 FAIL, census 3054**. `p15_5_niagara.py check`: 458 PASS, 1 FAIL: `NS_LB_Rain` `GetSystemCompileState` times out after 120 s (three runs). The asset is not dirty and was not touched; its other content checks pass (129). Watch the camera rain in P15-9 and in the suite (`RainFollowsCamera`, `FXSetup`) |
| §7 saves | PASS | One package per call, each `is_dirty` False afterwards: `NS_LB_RainColumn`, `NS_LB_EaveDrips`, `NS_LB_Drip`, `M_LB_Flame`, `MI_Flame_Candle_Player`, `MI_LB_Rain`, `MI_LB_Splash`, `MI_LB_Ripple`, `MI_LB_WaterMist`, `MI_Flame_Torch`, `MI_Cloth_Linen_Dark`, `BP_LBCharacter`, `DA_StormFX`, `L_Monastery`. Not dirty afterwards: the 14 never-save packages, `NS_LB_Rain`, `MI_LB_RainCurtain`, `MI_LB_Mist` |

## Column floor (EYE; judged in P15-9)
- **Chapel (6500, −418, 0):** `Ch_Floor_B1` max Z 1.5 (gap +1.5) and `Ground_0` max Z 0. A debris prop `Ch_RoofPlanks_1` (Z 0.4–25.1) lies under the opening: the splashes may land on it.
- **Cloister (11085, 2517.5, 0):** `CLA_Floor_N2` max Z 1.5 (gap +1.5) and `Ground_2` max Z 0.
- **Belfry (12187.5, 1687.5, 2500):** `TWA_BelfryFloor` max Z 2500.0 (gap 0).

## For the owner in P15-9
- **Rain columns:** they read as rain under the chapel hole, the cloister north-walk hole and the belfry collapse.
- **Drips:** the roof-edge and crypt drips are visible.
- **Player's flame:** it no longer vibrates when moving, at 4.55 cm.
- **Camera rain:** it still runs, given the `NS_LB_Rain` compile-state timeout.
