# THE LAST BELL — Performance Budget

## Hardware tiers
| Tier | Hardware | Target |
|---|---|---|
| **Reference (release target)** | RTX 3070 / 4070-class, 8–12 GB VRAM, 8-core CPU, 16–32 GB RAM | 60 fps at 1440p output with TSR (about 67% screen percentage), High preset |
| **Dev floor (current dev machine)** | RTX 4050 Laptop, **6 GB VRAM**, 16 GB RAM | 60 fps at 1080p with TSR (about 67%), Medium/High mix; 30 fps acceptable in editor PIE |
| Minimum (later) | Defined in Phase 20 | 30–45 fps at 1080p, Low preset |

The dev machine is below the "high-end" target, so quality decisions above Medium must be checked on reference hardware or inferred carefully. This is tracked in RISKS.md (R-01).

## Frame budget (reference tier, 16.6 ms)
| Bucket | Budget |
|---|---|
| Game thread | ≤ 8 ms (AI ≤ 0.5 ms, animation ≤ 1 ms) |
| Render thread / RHI | ≤ 8 ms |
| GPU total | ≤ 15 ms |
| ↳ Lumen GI + reflections | ≤ 4.5 ms |
| ↳ Shadows (VSM) | ≤ 2.5 ms |
| ↳ Base pass + Nanite | ≤ 3.5 ms |
| ↳ Translucency + fog + Niagara | ≤ 2 ms |
| ↳ Post + TSR | ≤ 1.5 ms |

## Memory
VRAM is 5 GB on the dev floor, leaving headroom out of 6 GB: texture streaming pool about 2,000 MB at High and about 1,200 MB at Medium. Hero textures are 4K at most, standard ones 2K, decals 1–2K. Virtual Textures are only used where measured to help.

## Rendering decisions to measure (not assume)
- Lumen hardware RT versus software on the 4050: decided in Phase 7.
- VSM page pool and the cost of many shadow-casting local lights (candles): candle lights are mostly non-shadow-casting.
- Volumetric fog grid resolution versus quality.

## Measurement practice
At each art, VFX and AI milestone: `stat unit`, `stat gpu`, `profilegpu`, and an Insights trace (`-trace=default,gpu`) at the fixed camera bookmarks named in TEST_PLAN.md. Results are logged in this file under "Measurements".

## Measurements
_None yet (Phase 0)._
