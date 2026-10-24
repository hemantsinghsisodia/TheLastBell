# Lane check (P7F-4, 4.1)

2D distance (cm) from every collision-enabled new/swapped prop's world-bounds rectangle to the nearest lane segment (rule: >= 60 cm), and to the recess / corridor / trigger rectangles (recesses >= 60 cm, corridor/trigger/checkpoint volumes: no overlap).

| Prop | Nearest lane | Dist (cm) | Nearest rect | Dist (cm) | OK |
|---|---|---|---|---|---|
| KD_Pier_N2 | L-E gate->shortcut | 268 | door recess (L-B) | 1958 | yes |
| KD_Pier_S1 | L-B well->chapel door | 173 | CP_Courtyard | 2644 | yes |
| KV_Rock_0 | L-A gate->well | 278 | CP_Courtyard | 1722 | yes |
| KV_Rock_1 | L-B well->chapel door | 1906 | door recess (L-B) | 1958 | yes |
| KX_Barrel_0 | L-E gate->shortcut | 2313 | CP_Courtyard | 2072 | yes |
| KX_Barrel_1 | L-E gate->shortcut | 2199 | CP_Courtyard | 1977 | yes |
| KX_Barrel_2 | L-E gate->shortcut | 2267 | CP_Courtyard | 2078 | yes |
| KX_FirePit | L-E gate->shortcut | 1374 | CP_Courtyard | 1460 | yes |
| KX_Log | L-E gate->shortcut | 1031 | CP_Courtyard | 993 | yes |
| KX_Stump | L-E gate->shortcut | 1073 | CP_Courtyard | 1700 | yes |
| KX_Table | L-E gate->shortcut | 2132 | CP_Courtyard | 2262 | yes |
| KY_Cross_S0 | L-E gate->shortcut | 1503 | CP_Courtyard | 2939 | yes |
| KY_Cross_W0 | L-C well->shortcut | 1227 | shortcut recess (L-C) | 1822 | yes |
| KY_Rock_0 | L-C well->shortcut | 1008 | shortcut recess (L-C) | 1315 | yes |
| KY_Stone_A0 | L-E gate->shortcut | 1552 | CP_Courtyard | 2630 | yes |
| KY_Stone_A1 | L-E gate->shortcut | 994 | CP_Courtyard | 2760 | yes |
| KY_Stone_B0 | L-E gate->shortcut | 1469 | shortcut recess (L-C) | 2622 | yes |
| KY_Stone_B1 | L-E gate->shortcut | 959 | shortcut recess (L-C) | 2533 | yes |
| KY_Stone_C0 | L-E gate->shortcut | 1427 | shortcut recess (L-C) | 2220 | yes |
| KY_Stone_C0_Frag | L-E gate->shortcut | 1319 | shortcut recess (L-C) | 2140 | yes |
| KY_Stone_D0 | L-E gate->shortcut | 1039 | CP_Courtyard | 2420 | yes |
| KZ_Cart | L-B well->chapel door | 596 | CP_Courtyard | 2851 | yes |
| KZ_Pillar_Fallen | L-B well->chapel door | 1051 | door recess (L-B) | 2742 | yes |
| Key_Chapel | L-A gate->well | 192 | CP_Courtyard | 2057 | yes |
| Plinth_Key | L-A gate->well | 173 | CP_Courtyard | 2030 | yes |

Props checked: 25. Violations: 0
Minimum lane distance: 173 cm (Plinth_Key)

## Re-run after P7F-4b (anvil, chest, trunk, torch, cage, wheel added)

2D distance (cm) from every collision-enabled new/swapped prop's world-bounds rectangle to the nearest lane segment (rule: >= 60 cm), and to the recess / corridor / trigger rectangles (recesses >= 60 cm, corridor/trigger/checkpoint volumes: no overlap).

| Prop | Nearest lane | Dist (cm) | Nearest rect | Dist (cm) | OK |
|---|---|---|---|---|---|
| KD_Pier_N2 | L-E gate->shortcut | 268 | door recess (L-B) | 1958 | yes |
| KD_Pier_S1 | L-B well->chapel door | 173 | CP_Courtyard | 2644 | yes |
| KV_Rock_0 | L-A gate->well | 278 | CP_Courtyard | 1722 | yes |
| KV_Rock_1 | L-B well->chapel door | 1906 | door recess (L-B) | 1958 | yes |
| KX_Anvil | L-E gate->shortcut | 1763 | CP_Courtyard | 2170 | yes |
| KX_Barrel_0 | L-E gate->shortcut | 2313 | CP_Courtyard | 2072 | yes |
| KX_Barrel_1 | L-E gate->shortcut | 2199 | CP_Courtyard | 1977 | yes |
| KX_Barrel_2 | L-E gate->shortcut | 2267 | CP_Courtyard | 2078 | yes |
| KX_Cage | L-E gate->shortcut | 802 | CP_Courtyard | 643 | yes |
| KX_Chest | L-E gate->shortcut | 2106 | CP_Courtyard | 2395 | yes |
| KX_FirePit | L-E gate->shortcut | 1374 | CP_Courtyard | 1460 | yes |
| KX_Log | L-E gate->shortcut | 1031 | CP_Courtyard | 993 | yes |
| KX_Stump | L-E gate->shortcut | 1073 | CP_Courtyard | 1700 | yes |
| KX_Table | L-E gate->shortcut | 2132 | CP_Courtyard | 2262 | yes |
| KX_Torch | L-E gate->shortcut | 1577 | CP_Courtyard | 1292 | yes |
| KX_Trunk | L-E gate->shortcut | 1830 | CP_Courtyard | 1558 | yes |
| KY_BreakingWheel | L-E gate->shortcut | 1815 | CP_Courtyard | 2577 | yes |
| KY_Cross_S0 | L-E gate->shortcut | 1503 | CP_Courtyard | 2939 | yes |
| KY_Cross_W0 | L-C well->shortcut | 1227 | shortcut recess (L-C) | 1822 | yes |
| KY_Rock_0 | L-C well->shortcut | 1008 | shortcut recess (L-C) | 1315 | yes |
| KY_Stone_A0 | L-E gate->shortcut | 1552 | CP_Courtyard | 2630 | yes |
| KY_Stone_A1 | L-E gate->shortcut | 994 | CP_Courtyard | 2760 | yes |
| KY_Stone_B0 | L-E gate->shortcut | 1469 | shortcut recess (L-C) | 2622 | yes |
| KY_Stone_B1 | L-E gate->shortcut | 959 | shortcut recess (L-C) | 2533 | yes |
| KY_Stone_C0 | L-E gate->shortcut | 1427 | shortcut recess (L-C) | 2220 | yes |
| KY_Stone_C0_Frag | L-E gate->shortcut | 1319 | shortcut recess (L-C) | 2140 | yes |
| KY_Stone_D0 | L-E gate->shortcut | 1039 | CP_Courtyard | 2420 | yes |
| KZ_Cart | L-B well->chapel door | 596 | CP_Courtyard | 2851 | yes |
| KZ_Pillar_Fallen | L-B well->chapel door | 1051 | door recess (L-B) | 2742 | yes |
| Key_Chapel | L-A gate->well | 192 | CP_Courtyard | 2057 | yes |
| Plinth_Key | L-A gate->well | 173 | CP_Courtyard | 2030 | yes |

Props checked: 31. Violations: 0
Minimum lane distance: 173 cm (Plinth_Key)
