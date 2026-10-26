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
| Date | Build / where | GPU, scalability, res | GPU total | Key passes | Notes |
|---|---|---|---|---|---|
| 2026-10-25 | P7-FIX2 before trim, PIE editor viewport | RTX 4050 6 GB, Epic, ~1536×864 | **41.1 ms** graphics queue | VolumetricFog 6.17, RenderDeferredLighting 11.87, Lights 3.86, LumenReflections 3.71, TSR 5.60, Post 6.68; compute: LumenScreenProbeGather 12.8, LumenSceneLighting 6.7 | Over budget → P7F-7 trim (D-054) |
| 2026-10-25 | P7-FIX2 after trim (39dfcef + DefaultScalability.ini), PIE new window, courtyard | RTX 4050 6 GB, **High**, 1664×846 (87 % of the window) | **11.38 ms** GPU (graphics queue 11.32) | VolumetricFog 0.26, Fog 0.21, Translucency 0.08, LocalFogVolumes 0.03 (fog+translucency+Niagara ≈ 0.6 ms ≤ 2), RenderDeferredLighting 3.07, Lights 1.35, Post 2.54, TSR 1.84, LumenReflections 1.02; compute: LumenScreenProbeGather 2.11, LumenSceneLighting 0.71 | **Within the dev-floor budget (≤ 16.6 ms)**. VRAM 3.44 / 5.03 GB. Frame 16.67 ms (60 fps cap). Game thread 9.27 ms in PIE (editor + AI logging on). Epic scalability not re-measured after the trim. |
| 2026-10-25 | P7-FIX3 (fefe4f7: arcade, garden, 2248 PCG plants, ivy, 12 warm lights with light functions) | RTX 4050 6 GB, **High**, 1664×846 (87 % of the window), PIE new window, courtyard graveyard/work-area view with the candle lit | **13.11 ms** GPU (graphics queue 12.97 avg / 14.06 max; compute 5.46 async) | RenderDeferredLighting 3.71, Postprocessing 2.68, TSR 2.00, Lights 1.90, Shadow Projection 1.46, Nanite BasePass 1.25, Basepass 1.01, Shadow Depths 0.96, LumenReflections 0.90, Slate UI 0.88, Nanite VisBuffer 0.79, VolumetricFog 0.30, Fog 0.21, Translucent Lighting 0.11, Translucency 0.08, LocalFogVolumes 0.03 (fog+translucency+Niagara ≈ 0.7 ms ≤ 2); compute: LumenScreenProbeGather 2.88, LumenSceneLighting 0.82 | **Within the dev-floor budget (≤ 16.6 ms)**, +1.7 ms vs P7-FIX2 (lights/light functions and shadow passes from grass + structures). VRAM 3.14 / 5.03 GB. Frame 16.67 ms (60 fps cap). Game thread 9.56 ms (PIE, AI logging on). Draws 516, prims 126K. No FIX3 fallback needed. |
| 2026-10-26 | Phase 8 chapel (c646e7e: kit nave, trusses, slate roof, 159 dressing actors, 13 flame meshes, 12 shadowless chapel lights, LFV, decals, animated hanging body) | RTX 4050 6 GB, High, 1920×1080 window, mid-nave (7300, 0, 170) facing the altar | *pending owner measurement* | — | Fallbacks if > 16.6 ms: LFV off, shaft scattering halved, roof-hole spot off (P8 plan §2 P8-8) |
