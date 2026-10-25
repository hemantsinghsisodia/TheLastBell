# Warm-pool coverage check (P7-FIX3 G6)

Method: each of the 4 courtyard routes (P7-FIX3 §1) is sampled every 100 cm along its polyline (plus the end point); for every sample the XY distance to the nearest warm light is taken. Warm lights: the 6 existing warm pools (`Light_WorkArea_Lantern` does not exist), `Light_WellHead_Warm`, the two grave candles, and the three route lanterns added in G6/G6b. Requirement: every sample <= 1500 cm.

| Route | Samples | Max distance (cm) | Worst sample (x, y) | Nearest light | Result |
|---|---|---|---|---|---|
| CourtyardKey | 28 | 1331 | (1270, -398) | Light_Gatehouse_Warm | PASS |
| CourtyardDoor | 58 | 1258 | (4650, 0) | Light_WellHead_Warm | PASS |
| CourtyardShortcut | 69 | 1453 | (5780, 2000) | Light_Route_Lantern_1 | PASS |
| CourtyardWellToDoor | 55 | 1154 | (2800, -1150) | Light_Well_Warm | PASS |

Failing samples (> 1500 cm):

- none

Warm light positions used (XY, cm):

- Light_Gatehouse_Warm (345, 560)
- Light_ChapelDoor_Warm (5925, -140)
- Light_Well_Warm (1780, -1690)
- Light_KeyLedge_Warm (1450, -2100)
- Light_FirePit_Ember (1150, 1650)
- Light_WorkArea_Torch (349, 1600)
- Light_WellHead_Warm (3400, -140)
- Light_Grave_Candle_A0 (2412, 2028)
- Light_Grave_Candle_B1 (3288, 1526)
- Light_Route_Lantern_1 (4400, 2454)
- Light_Route_Lantern_2 (2000, 859)
- Light_Route_Lantern_3 (4925, -1350)

History: with the 9 base warm lights 22 samples were over 1500 cm (worst: CourtyardShortcut end (5780, 2000) 2145 cm). G6 added Light_Route_Lantern_1 (north wall, (4400, 2454)) and _2 (pier base, (2000, 859)): 3 samples still failed on CourtyardWellToDoor at X 4600-4800, Y -1150 (worst 1588 cm). G6b (B3) added Light_Route_Lantern_3 on the -X face of Roof_S_Post_4950 at (4925, -1350, 191.5) and all four routes pass.
