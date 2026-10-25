# Lane check (P7-FIX3 G4)

2D distance (cm) from every collision-enabled new prop and the pre-existing structures near the new routes to the nearest lane segment of the four courtyard routes (CourtyardKey, CourtyardDoor, CourtyardShortcut, CourtyardWellToDoor; rule: >= 60 cm), and to the recess / corridor / trigger rectangles (recesses >= 60 cm, trigger/checkpoint volumes: no overlap).
Method: world-bounds rectangle (conservative) of each actor; the well-head is measured as its real footprint (ring circle R131 + two winch posts) because its bounds rectangle has empty corners. Arcade bays are overhead (bottom Z 300, above the 290 cm Warden capsule) and are listed for completeness only; Rafters, purlins, planks, ivy and branches are NoCollision and not listed.

| Prop | Nearest lane segment | Dist (cm) | Nearest rect | Dist (cm) | Note | OK |
|---|---|---|---|---|---|---|
| Arc_N_3000_BayA | CourtyardShortcut seg3 | 0 | door recess | 2315 | overhead (Z min 300) | yes |
| Plinth_Key | CourtyardKey seg3 | 73 | CP_Courtyard | 2030 | existing; Z 0..70 | yes |
| KD_Well_N1 | CourtyardKey seg2 | 75 | CP_Courtyard | 1741 | existing; Z 0..250 | yes |
| KD_Well_N2 | CourtyardKey seg2 | 75 | CP_Courtyard | 1886 | existing; Z 0..250 | yes |
| Key_Chapel | CourtyardKey seg3 | 93 | CP_Courtyard | 2057 | existing; Z 70..71 | yes |
| KD_WellRub_2 | CourtyardKey seg3 | 108 | CP_Courtyard | 1904 | existing; Z 0..70 | yes |
| Garden_Earth_SE_01 | CourtyardDoor seg2 | 113 | door recess | 1751 |  | yes |
| Garden_Earth_SW_09 | CourtyardDoor seg1 | 113 | CP_Courtyard | 2300 |  | yes |
| Garden_KerbCorner_SE_NW | CourtyardDoor seg2 | 113 | door recess | 2121 |  | yes |
| Garden_KerbCorner_NW_SE | CourtyardShortcut seg1 | 113 | CP_Courtyard | 2670 |  | yes |
| Garden_KerbCorner_SW_NE | CourtyardDoor seg1 | 113 | CP_Courtyard | 2670 |  | yes |
| Garden_Earth_NW_08 | CourtyardShortcut seg1 | 113 | CP_Courtyard | 2300 |  | yes |
| Garden_Kerb_NW_S_07 | CourtyardShortcut seg1 | 131 | CP_Courtyard | 2564 |  | yes |
| Garden_Kerb_SW_N_14 | CourtyardDoor seg1 | 131 | CP_Courtyard | 2564 |  | yes |
| Garden_Kerb_SE_N_09 | CourtyardDoor seg2 | 131 | door recess | 1929 |  | yes |
| KD_WellRub_3 | CourtyardWellToDoor seg0 | 133 | CP_Courtyard | 1909 | existing; Z 0..40 | yes |
| Garden_WellHead ring (circle R131) | CourtyardDoor seg1 | 135 | - | - |  | yes |
| Garden_Kerb_NW_E_18 | CourtyardShortcut seg1 | 137 | CP_Courtyard | 2670 |  | yes |
| Garden_Kerb_SW_E_19 | CourtyardDoor seg1 | 137 | CP_Courtyard | 2670 |  | yes |
| Garden_Kerb_SE_W_18 | CourtyardDoor seg2 | 137 | door recess | 2122 |  | yes |
| Garden_Earth_SE_08 | CourtyardWellToDoor seg2 | 140 | door recess | 585 |  | yes |
| Garden_KerbCorner_SE_SE | CourtyardWellToDoor seg2 | 140 | door recess | 792 |  | yes |
| KD_Pier_S2 | CourtyardWellToDoor seg1 | 150 | door recess | 1931 | existing; Z 0..500 | yes |
| KD_Pier_S3 | CourtyardWellToDoor seg1 | 150 | door recess | 1063 | existing; Z 0..500 | yes |
| Garden_Kerb_SE_E_19 | CourtyardWellToDoor seg2 | 152 | door recess | 665 |  | yes |
| Garden_WellHead winch post W | CourtyardDoor seg1 | 152 | door recess | 2611 |  | yes |
| Garden_WellHead winch post E | CourtyardDoor seg2 | 152 | door recess | 2271 |  | yes |
| KD_Well_E | CourtyardKey seg3 | 155 | CP_Courtyard | 1950 | existing; Z 0..250 | yes |
| KD_Pier_S0 | CourtyardWellToDoor seg0 | 158 | CP_Courtyard | 1662 | existing; Z 0..500 | yes |
| Garden_Lantern | CourtyardDoor seg2 | 160 | door recess | 2439 |  | yes |
| Garden_Bucket | CourtyardShortcut seg1 | 163 | door recess | 2396 |  | yes |
| Garden_Kerb_SE_S_08 | CourtyardWellToDoor seg2 | 167 | door recess | 813 |  | yes |
| Arc_S_2000_BayA | CourtyardWellToDoor seg0 | 170 | CP_Courtyard | 1716 | overhead (Z min 300) | yes |
| Arc_S_3000_BayB | CourtyardWellToDoor seg1 | 170 | door recess | 1985 | overhead (Z min 300) | yes |
| Arc_S_4000_Bay | CourtyardWellToDoor seg1 | 170 | door recess | 1114 | overhead (Z min 300) | yes |
| KD_Pier_S1 | CourtyardWellToDoor seg1 | 170 | CP_Courtyard | 2644 | existing; Z 0..231 | yes |
| KD_Well_W | CourtyardKey seg2 | 175 | CP_Courtyard | 1715 | existing; Z 0..250 | yes |
| Arc_Column_S_2000 | CourtyardWellToDoor seg1 | 180 | CP_Courtyard | 2173 |  | yes |
| Arc_Column_S_3000 | CourtyardWellToDoor seg1 | 180 | door recess | 2442 |  | yes |
| Arc_Column_S_4000 | CourtyardWellToDoor seg1 | 180 | door recess | 1517 |  | yes |
| Roof_S_Post_4050 | CourtyardWellToDoor seg1 | 190 | door recess | 2122 |  | yes |
| Roof_S_Post_4950 | CourtyardWellToDoor seg1 | 190 | door recess | 1446 |  | yes |
| Garden_Kerb_NW_S_06 | CourtyardShortcut seg1 | 193 | CP_Courtyard | 2351 |  | yes |
| Garden_Kerb_SW_N_13 | CourtyardDoor seg1 | 193 | CP_Courtyard | 2351 |  | yes |
| KD_WellRub_5 | CourtyardKey seg3 | 197 | CP_Courtyard | 2181 | existing; Z 0..40 | yes |
| KD_WellRub_4 | CourtyardKey seg2 | 199 | CP_Courtyard | 1646 | existing; Z 0..40 | yes |
| Garden_Earth_SE_09 | CourtyardWellToDoor seg2 | 199 | door recess | 552 |  | yes |
| Arc_Column_N_3000_Fallen | CourtyardShortcut seg3 | 200 | door recess | 2047 |  | yes |
| Rub_Heap_S_2000 | CourtyardWellToDoor seg1 | 200 | CP_Courtyard | 2280 |  | yes |
| Rub_Chunk_S_2000_2 | CourtyardWellToDoor seg1 | 200 | CP_Courtyard | 2411 |  | yes |
| Rub_Heap_S_3000 | CourtyardWellToDoor seg1 | 200 | door recess | 2508 |  | yes |
| Rub_Chunk_S_3000_0 | CourtyardWellToDoor seg1 | 200 | door recess | 2641 |  | yes |
| Rub_Chunk_S_3000_2 | CourtyardWellToDoor seg1 | 200 | door recess | 2657 |  | yes |
| Rub_Chunk_S_2000_1 | CourtyardWellToDoor seg1 | 200 | CP_Courtyard | 2287 |  | yes |
| Rub_Chunk_S_2000_0 | CourtyardWellToDoor seg1 | 210 | CP_Courtyard | 2398 |  | yes |
| Rub_Chunk_S_3000_1 | CourtyardWellToDoor seg1 | 210 | door recess | 2702 |  | yes |
| Rub_Chunk_S_3000_4 | CourtyardWellToDoor seg1 | 211 | door recess | 2657 |  | yes |
| KD_Heap_N | CourtyardKey seg0 | 214 | CP_Courtyard | 200 | existing; Z 0..130 | yes |
| Rub_Chunk_S_2000_4 | CourtyardWellToDoor seg1 | 214 | CP_Courtyard | 2561 |  | yes |
| KD_Well_S | CourtyardKey seg3 | 225 | CP_Courtyard | 2091 | existing; Z 0..250 | yes |
| Rub_Chunk_S_3000_3 | CourtyardWellToDoor seg1 | 226 | CP_Courtyard | 2753 |  | yes |
| Rub_Chunk_S_2000_3 | CourtyardWellToDoor seg1 | 229 | CP_Courtyard | 2316 |  | yes |
| Garden_Kerb_SE_E_20 | CourtyardWellToDoor seg2 | 230 | door recess | 578 |  | yes |
| Rub_Heap_N_3000 | CourtyardShortcut seg4 | 231 | door recess | 1961 |  | yes |
| Garden_Earth_NW_09 | CourtyardShortcut seg1 | 234 | CP_Courtyard | 2302 |  | yes |
| Garden_Earth_SW_08 | CourtyardDoor seg1 | 234 | CP_Courtyard | 2302 |  | yes |
| Garden_Earth_SE_00 | CourtyardDoor seg2 | 234 | door recess | 1761 |  | yes |
| Rub_Chunk_N_3000_4 | CourtyardShortcut seg3 | 240 | door recess | 2248 |  | yes |
| KD_Pier_N2 | CourtyardShortcut seg4 | 243 | door recess | 1958 | existing; Z 0..231 | yes |
| Garden_Kerb_SE_N_10 | CourtyardDoor seg2 | 244 | door recess | 1737 |  | yes |
| Rub_Chunk_N_3000_2 | CourtyardShortcut seg4 | 246 | door recess | 2155 |  | yes |
| Garden_Earth_NW_04 | CourtyardDoor seg0 | 250 | CP_Courtyard | 1800 |  | yes |
| Garden_Earth_NE_00 | CourtyardDoor seg2 | 250 | door recess | 1751 |  | yes |
| Garden_Earth_NE_04 | CourtyardDoor seg3 | 250 | door recess | 1151 |  | yes |
| Garden_Earth_NE_06 | CourtyardDoor seg3 | 250 | door recess | 851 |  | yes |
| Garden_Earth_SE_03 | CourtyardDoor seg3 | 250 | door recess | 1451 |  | yes |
| Garden_Earth_SE_05 | CourtyardDoor seg3 | 250 | door recess | 1151 |  | yes |
| Garden_Earth_SE_07 | CourtyardDoor seg3 | 250 | door recess | 851 |  | yes |
| Garden_KerbCorner_NW_SW | CourtyardDoor seg0 | 250 | CP_Courtyard | 1300 |  | yes |
| Garden_Kerb_NW_S_01 | CourtyardDoor seg0 | 250 | CP_Courtyard | 1330 |  | yes |
| Garden_Kerb_NW_S_02 | CourtyardDoor seg0 | 250 | CP_Courtyard | 1528 |  | yes |
| Garden_Kerb_NW_S_03 | CourtyardDoor seg0 | 250 | CP_Courtyard | 1727 |  | yes |
| Garden_Kerb_NW_S_04 | CourtyardDoor seg0 | 250 | CP_Courtyard | 1926 |  | yes |
| Garden_Kerb_NW_S_05 | CourtyardDoor seg0 | 250 | CP_Courtyard | 2139 |  | yes |
| Garden_KerbCorner_NE_SE | CourtyardDoor seg3 | 250 | door recess | 552 |  | yes |
| Garden_Kerb_NE_S_01 | CourtyardDoor seg2 | 250 | door recess | 1929 |  | yes |
| Garden_Kerb_NE_S_02 | CourtyardDoor seg3 | 250 | door recess | 1737 |  | yes |
| Garden_Kerb_NE_S_03 | CourtyardDoor seg3 | 250 | door recess | 1545 |  | yes |
| Garden_Kerb_NE_S_04 | CourtyardDoor seg3 | 250 | door recess | 1253 |  | yes |
| Garden_Kerb_NE_S_05 | CourtyardDoor seg3 | 250 | door recess | 1061 |  | yes |
| Garden_Kerb_NE_S_06 | CourtyardDoor seg3 | 250 | door recess | 869 |  | yes |
| Garden_Kerb_NE_S_07 | CourtyardDoor seg3 | 250 | door recess | 678 |  | yes |
| Garden_Kerb_NE_S_08 | CourtyardDoor seg3 | 250 | door recess | 582 |  | yes |
| Garden_KerbCorner_SW_NW | CourtyardDoor seg0 | 250 | CP_Courtyard | 1300 |  | yes |
| Garden_Kerb_SW_N_08 | CourtyardDoor seg0 | 250 | CP_Courtyard | 1330 |  | yes |
| Garden_Kerb_SW_N_09 | CourtyardDoor seg0 | 250 | CP_Courtyard | 1528 |  | yes |
| Garden_Kerb_SW_N_10 | CourtyardDoor seg0 | 250 | CP_Courtyard | 1727 |  | yes |
| Garden_Kerb_SW_N_11 | CourtyardDoor seg0 | 250 | CP_Courtyard | 1926 |  | yes |
| Garden_Kerb_SW_N_12 | CourtyardDoor seg0 | 250 | CP_Courtyard | 2139 |  | yes |
| Garden_KerbCorner_SE_NE | CourtyardDoor seg3 | 250 | door recess | 552 |  | yes |
| Garden_Kerb_SE_N_11 | CourtyardDoor seg3 | 250 | door recess | 1545 |  | yes |
| Garden_Kerb_SE_N_12 | CourtyardDoor seg3 | 250 | door recess | 1253 |  | yes |
| Garden_Kerb_SE_N_13 | CourtyardDoor seg3 | 250 | door recess | 1061 |  | yes |
| Garden_Kerb_SE_N_14 | CourtyardDoor seg3 | 250 | door recess | 869 |  | yes |
| Garden_Kerb_SE_N_15 | CourtyardDoor seg3 | 250 | door recess | 678 |  | yes |
| Garden_Kerb_SE_N_16 | CourtyardDoor seg3 | 250 | door recess | 582 |  | yes |
| Garden_Earth_NW_06 | CourtyardDoor seg0 | 250 | CP_Courtyard | 2050 |  | yes |
| Garden_Earth_NE_02 | CourtyardDoor seg3 | 250 | door recess | 1451 |  | yes |
| Garden_Earth_SW_05 | CourtyardDoor seg0 | 250 | CP_Courtyard | 1800 |  | yes |
| Garden_Earth_SW_07 | CourtyardDoor seg0 | 250 | CP_Courtyard | 2050 |  | yes |
| Garden_Earth_NW_00 | CourtyardDoor seg0 | 250 | CP_Courtyard | 1300 |  | yes |
| Garden_Earth_NW_02 | CourtyardDoor seg0 | 250 | CP_Courtyard | 1550 |  | yes |
| Garden_Earth_NE_08 | CourtyardDoor seg3 | 250 | door recess | 552 |  | yes |
| Garden_Earth_SW_01 | CourtyardDoor seg0 | 250 | CP_Courtyard | 1300 |  | yes |
| Garden_Earth_SW_03 | CourtyardDoor seg0 | 250 | CP_Courtyard | 1550 |  | yes |
| KD_WellRub_0 | CourtyardKey seg3 | 253 | CP_Courtyard | 2151 | existing; Z 0..110 | yes |
| Rub_Chunk_N_3000_0 | CourtyardShortcut seg4 | 258 | door recess | 1964 |  | yes |
| Garden_Kerb_SE_S_07 | CourtyardWellToDoor seg2 | 261 | door recess | 889 |  | yes |
| Rub_Chunk_N_3000_1 | CourtyardShortcut seg4 | 264 | door recess | 2147 |  | yes |
| Rub_Heap_N_4000 | CourtyardShortcut seg4 | 276 | door recess | 1586 |  | yes |
| Garden_KerbCorner_NE_SW | CourtyardDoor seg2 | 277 | door recess | 2121 |  | yes |
| KV_Rock_0 | CourtyardKey seg2 | 278 | CP_Courtyard | 1722 | existing; Z 0..53 | yes |
| Rub_Chunk_N_3000_3 | CourtyardShortcut seg3 | 279 | door recess | 2209 |  | yes |
| Garden_Kerb_NW_W_15 | CourtyardDoor seg0 | 280 | CP_Courtyard | 1300 |  | yes |
| Garden_Kerb_NE_E_19 | CourtyardDoor seg3 | 280 | door recess | 556 |  | yes |
| Garden_Kerb_SW_W_17 | CourtyardDoor seg0 | 280 | CP_Courtyard | 1300 |  | yes |
| Garden_Kerb_SE_E_21 | CourtyardDoor seg3 | 280 | door recess | 556 |  | yes |
| Rub_Chunk_N_4000_0 | CourtyardShortcut seg4 | 289 | door recess | 1783 |  | yes |
| Arc_N_4000_BayB | CourtyardShortcut seg4 | 292 | door recess | 1114 | overhead (Z min 300) | yes |
| Rub_Chunk_N_4000_1 | CourtyardShortcut seg4 | 296 | door recess | 1720 |  | yes |
| Garden_KerbCorner_NW_NE | CourtyardShortcut seg2 | 300 | CP_Courtyard | 2711 |  | yes |
| Garden_Kerb_NW_E_19 | CourtyardShortcut seg2 | 300 | CP_Courtyard | 2684 |  | yes |
| Garden_KerbCorner_NE_NW | CourtyardShortcut seg2 | 300 | door recess | 2195 |  | yes |
| Garden_Kerb_NE_W_17 | CourtyardShortcut seg1 | 300 | door recess | 2122 |  | yes |
| Garden_Kerb_NE_W_18 | CourtyardShortcut seg2 | 300 | door recess | 2153 |  | yes |
| Garden_Earth_NE_01 | CourtyardShortcut seg2 | 300 | door recess | 1761 |  | yes |
| KD_Rub_0 | CourtyardKey seg1 | 308 | CP_Courtyard | 1321 | existing; Z 0..110 | yes |
| KD_Rub_2 | CourtyardKey seg1 | 310 | CP_Courtyard | 1127 | existing; Z 0..70 | yes |
| Garden_DeadTree_A | CourtyardDoor seg3 | 310 | door recess | 1088 |  | yes |
| Arc_Column_N_4000 | CourtyardShortcut seg4 | 319 | door recess | 1517 |  | yes |
| Rub_Chunk_N_4000_2 | CourtyardShortcut seg4 | 325 | door recess | 1704 |  | yes |
| Garden_Kerb_NW_N_14 | CourtyardShortcut seg2 | 330 | CP_Courtyard | 2610 |  | yes |
| Garden_Kerb_NE_N_09 | CourtyardShortcut seg2 | 330 | door recess | 1998 |  | yes |
| Rub_Chunk_N_4000_3 | CourtyardShortcut seg4 | 342 | door recess | 1868 |  | yes |
| KD_Rub_5 | CourtyardKey seg1 | 342 | CP_Courtyard | 577 | existing; Z 0..40 | yes |
| Garden_KerbCorner_SW_SW | CourtyardKey seg1 | 343 | CP_Courtyard | 1382 |  | yes |
| Garden_Earth_SW_00 | CourtyardKey seg1 | 343 | CP_Courtyard | 1304 |  | yes |
| Garden_Kerb_SW_W_15 | CourtyardKey seg1 | 349 | CP_Courtyard | 1329 |  | yes |
| Garden_Earth_SW_04 | CourtyardWellToDoor seg1 | 350 | CP_Courtyard | 1803 |  | yes |
| Garden_Earth_SE_04 | CourtyardWellToDoor seg1 | 350 | door recess | 1167 |  | yes |
| Garden_Earth_SE_06 | CourtyardWellToDoor seg1 | 350 | door recess | 873 |  | yes |
| Garden_KerbCorner_SW_SE | CourtyardWellToDoor seg1 | 350 | CP_Courtyard | 2711 |  | yes |
| Garden_Kerb_SW_S_02 | CourtyardWellToDoor seg0 | 350 | CP_Courtyard | 1606 |  | yes |
| Garden_Kerb_SW_S_03 | CourtyardWellToDoor seg1 | 350 | CP_Courtyard | 1805 |  | yes |
| Garden_Kerb_SW_S_04 | CourtyardWellToDoor seg1 | 350 | CP_Courtyard | 2004 |  | yes |
| Garden_Kerb_SW_S_05 | CourtyardWellToDoor seg1 | 350 | CP_Courtyard | 2205 |  | yes |
| Garden_Kerb_SW_S_06 | CourtyardWellToDoor seg1 | 350 | CP_Courtyard | 2407 |  | yes |
| Garden_Kerb_SW_S_07 | CourtyardWellToDoor seg1 | 350 | CP_Courtyard | 2610 |  | yes |
| Garden_KerbCorner_SE_SW | CourtyardWellToDoor seg1 | 350 | door recess | 2195 |  | yes |
| Garden_Kerb_SE_S_01 | CourtyardWellToDoor seg1 | 350 | door recess | 1998 |  | yes |
| Garden_Kerb_SE_S_02 | CourtyardWellToDoor seg1 | 350 | door recess | 1802 |  | yes |
| Garden_Kerb_SE_S_03 | CourtyardWellToDoor seg1 | 350 | door recess | 1608 |  | yes |
| Garden_Kerb_SE_S_04 | CourtyardWellToDoor seg1 | 350 | door recess | 1418 |  | yes |
| Garden_Kerb_SE_S_05 | CourtyardWellToDoor seg1 | 350 | door recess | 1233 |  | yes |
| Garden_Kerb_SE_S_06 | CourtyardWellToDoor seg1 | 350 | door recess | 1055 |  | yes |
| Garden_Earth_SW_02 | CourtyardWellToDoor seg0 | 350 | CP_Courtyard | 1553 |  | yes |
| Garden_Earth_SW_06 | CourtyardWellToDoor seg1 | 350 | CP_Courtyard | 2052 |  | yes |
| Garden_Earth_SE_02 | CourtyardWellToDoor seg1 | 350 | door recess | 1464 |  | yes |
| KD_Pier_N1 | CourtyardShortcut seg3 | 350 | CP_Courtyard | 2620 | existing; Z 0..500 | yes |
| KD_Pier_N3 | CourtyardShortcut seg4 | 351 | door recess | 1063 | existing; Z 0..500 | yes |
| KD_WellRub_1 | CourtyardKey seg3 | 364 | CP_Courtyard | 2358 | existing; Z 0..70 | yes |
| Rub_Chunk_N_4000_4 | CourtyardShortcut seg4 | 365 | door recess | 1767 |  | yes |
| Garden_Kerb_SW_S_01 | CourtyardKey seg1 | 373 | CP_Courtyard | 1411 |  | yes |
| Garden_Kerb_SW_E_18 | CourtyardDoor seg1 | 375 | CP_Courtyard | 2684 |  | yes |
| Garden_Kerb_SE_W_17 | CourtyardDoor seg2 | 375 | door recess | 2153 |  | yes |
| Garden_Kerb_SW_W_16 | CourtyardDoor seg0 | 378 | CP_Courtyard | 1302 |  | yes |
| Garden_Earth_NW_07 | CourtyardShortcut seg1 | 382 | CP_Courtyard | 2052 |  | yes |
| Garden_Earth_NW_03 | CourtyardDoor seg0 | 400 | CP_Courtyard | 1553 |  | yes |
| Arc_N_2000_Bay | CourtyardShortcut seg3 | 400 | CP_Courtyard | 1716 | overhead (Z min 300) | yes |
| Garden_Earth_NW_01 | CourtyardDoor seg0 | 400 | CP_Courtyard | 1304 |  | yes |
| Garden_Earth_NW_05 | CourtyardDoor seg0 | 400 | CP_Courtyard | 1803 |  | yes |
| Garden_Earth_NE_03 | CourtyardDoor seg3 | 400 | door recess | 1464 |  | yes |
| Garden_Earth_NE_05 | CourtyardDoor seg3 | 400 | door recess | 1167 |  | yes |
| Garden_Earth_NE_07 | CourtyardDoor seg3 | 400 | door recess | 873 |  | yes |
| Garden_Earth_NE_09 | CourtyardDoor seg3 | 400 | door recess | 585 |  | yes |
| Garden_Kerb_NE_N_10 | CourtyardShortcut seg4 | 417 | door recess | 1802 |  | yes |
| Garden_Kerb_NW_N_13 | CourtyardShortcut seg2 | 433 | CP_Courtyard | 2407 |  | yes |
| KD_Rub_4 | CourtyardKey seg0 | 441 | CP_Courtyard | 332 | existing; Z 0..110 | yes |
| KD_Rub_1 | CourtyardKey seg1 | 443 | CP_Courtyard | 1060 | existing; Z 0..70 | yes |
| Garden_Kerb_NE_N_11 | CourtyardShortcut seg4 | 444 | door recess | 1608 |  | yes |
| KD_Ruin_1 | CourtyardKey seg1 | 461 | CP_Courtyard | 566 | existing; Z 0..400 | yes |
| Roof_N_Post_2950 | CourtyardShortcut seg3 | 462 | CP_Courtyard | 2726 |  | yes |
| Garden_Kerb_NE_N_12 | CourtyardShortcut seg4 | 470 | door recess | 1418 |  | yes |
| Garden_Kerb_NW_W_16 | CourtyardDoor seg0 | 476 | CP_Courtyard | 1312 |  | yes |
| Garden_Kerb_NE_E_20 | CourtyardDoor seg3 | 476 | door recess | 615 |  | yes |
| Garden_Snag_Trunk | CourtyardDoor seg0 | 497 | CP_Courtyard | 1858 |  | yes |
| Garden_Kerb_NE_N_13 | CourtyardShortcut seg4 | 497 | door recess | 1233 |  | yes |
| KD_Heap_S | CourtyardKey seg1 | 508 | CP_Courtyard | 1151 | existing; Z 0..130 | yes |
| KD_Rub_6 | CourtyardKey seg1 | 513 | CP_Courtyard | 777 | existing; Z 0..70 | yes |
| Garden_Kerb_NE_N_14 | CourtyardShortcut seg4 | 524 | door recess | 1055 |  | yes |
| KD_Ruin_0 | CourtyardKey seg1 | 539 | CP_Courtyard | 894 | existing; Z 0..400 | yes |
| Garden_Kerb_NE_N_15 | CourtyardShortcut seg4 | 551 | door recess | 889 |  | yes |
| KD_Rub_7 | CourtyardKey seg1 | 573 | CP_Courtyard | 902 | existing; Z 0..40 | yes |
| Garden_Kerb_NE_N_16 | CourtyardShortcut seg4 | 578 | door recess | 813 |  | yes |
| Garden_KerbCorner_NE_NE | CourtyardShortcut seg4 | 591 | door recess | 792 |  | yes |
| Garden_Kerb_NE_E_21 | CourtyardShortcut seg4 | 621 | door recess | 725 |  | yes |
| Garden_Kerb_NW_N_12 | CourtyardShortcut seg2 | 639 | CP_Courtyard | 2205 |  | yes |
| Garden_Kerb_NW_W_17 | CourtyardDoor seg0 | 672 | CP_Courtyard | 1352 |  | yes |
| Garden_KerbCorner_NW_NW | CourtyardDoor seg0 | 770 | CP_Courtyard | 1382 |  | yes |
| Garden_Kerb_NW_N_08 | CourtyardDoor seg0 | 770 | CP_Courtyard | 1411 |  | yes |
| Garden_Kerb_NW_N_09 | CourtyardDoor seg0 | 770 | CP_Courtyard | 1606 |  | yes |
| Garden_Kerb_NW_N_10 | CourtyardDoor seg0 | 770 | CP_Courtyard | 1805 |  | yes |
| Garden_Kerb_NW_N_11 | CourtyardDoor seg0 | 770 | CP_Courtyard | 2004 |  | yes |
| KD_Rub_3 | CourtyardKey seg1 | 809 | CP_Courtyard | 1062 | existing; Z 0..40 | yes |
| Arc_Column_N_2000 | CourtyardShortcut seg3 | 880 | CP_Courtyard | 2173 |  | yes |
| KD_Pier_N0 | CourtyardDoor seg0 | 900 | CP_Courtyard | 1662 | existing; Z 0..500 | yes |
| KV_Rock_1 | CourtyardWellToDoor seg1 | 1057 | door recess | 1958 | existing; Z 0..61 | yes |
| Roof_N_Post_2050 | CourtyardDoor seg0 | 1290 | CP_Courtyard | 1916 |  | yes |

Props checked: 212 (excluding 6 overhead). Violations: 0
Minimum lane distance (walk-level props): 73 cm (Plinth_Key)

## G5 addendum (vegetation scatter)
- 914 PCG-scattered instances in 243 ISM components (19 `PCGV_*` volumes) plus 4 hand-placed Searsia actors: all read back as `collisionEnabled = NoCollision` / profile `NoCollision`, so none of them can block a lane (not part of the table above).
- Every scattered instance centre is >= 123 cm from every route centreline (the 240 cm wide `LB_PCG_Exclude` strips keep 120 cm clear); 0 instances inside the plaza box or the well-house interior; instance Z range -3..+3 (nothing landed on kerb tops).
- The 36 exclusion actors are `TriggerVolume`s (overlap-only brushes, no blocking collision) tagged `LB_PCG_Exclude`.
