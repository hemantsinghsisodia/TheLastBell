# Warm-pool coverage check (P7-FIX3 G6)

Method: each of the 4 courtyard routes (P7-FIX3 §1) is sampled every 100 cm along its polyline (plus the end point); for every sample the XY distance to the nearest warm light is taken. Warm lights: the 6 existing warm pools (`Light_WorkArea_Lantern` does not exist), `Light_WellHead_Warm`, the two grave candles, and the two route lanterns added in G6. Requirement: every sample <= 1500 cm.

| Route | Samples | Max distance (cm) | Worst sample (x, y) | Nearest light | Result |
|---|---|---|---|---|---|
| CourtyardKey | 28 | 1331 | (1270, -398) | Light_Gatehouse_Warm | PASS |
| CourtyardDoor | 58 | 1258 | (4650, 0) | Light_WellHead_Warm | PASS |
| CourtyardShortcut | 69 | 1453 | (5780, 2000) | Light_Route_Lantern_1 | PASS |
| CourtyardWellToDoor | 55 | 1588 | (4700, -1150) | Light_ChapelDoor_Warm | FAIL |

Failing samples (> 1500 cm):

- CourtyardWellToDoor at (4600, -1150): 1568 cm from Light_WellHead_Warm
- CourtyardWellToDoor at (4700, -1150): 1588 cm from Light_ChapelDoor_Warm
- CourtyardWellToDoor at (4800, -1150): 1512 cm from Light_ChapelDoor_Warm

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

Without the two route lanterns the worst stretches were: CourtyardShortcut end (5780, 2000) 2145 cm from Light_ChapelDoor_Warm, CourtyardWellToDoor (4700, -1150) 1588 cm, CourtyardDoor (1850, 0) 1556 cm (22 samples over 1500 cm in total). The lantern positions were chosen by exhaustive search over wall (Y +-2480, X 320/5980) and pier-base candidates; no pair of two lanterns brings every sample under 1500 cm. A third lantern near (4700, -1020) would clear the remaining stretch.
