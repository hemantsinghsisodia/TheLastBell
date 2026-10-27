
## P9-6a lane check (crypt art pieces and RouteBot approaches)

WalkPath points: SacristyToCrypt 8, FloodedLedge 6, CryptToCloister 11; crypt AI points: 24.

| Piece | AABB X | AABB Y | Min dist to WalkPath (cm) | Nearest segment | Min dist to AI point (cm) | Nearest point | Result |
|---|---|---|---|---|---|---|---|
| CA_Pillar_Free_8000 | 7925..8075 | -2583..-2437 | 677.2 | FloodedLedge 00-01 | 124.8 | Patrol_Crypt_01 | FAIL |
| CA_Pillar_Free_8500 | 8425..8575 | -2583..-2437 | 183.8 | FloodedLedge 00-01 | 187.1 | Search_Crypt_03 | PASS |
| CA_Pillar_N_8000 | 7925..8075 | -2073..-1927 | 741.3 | FloodedLedge 00-01 | 326.8 | Search_Crypt_02 | PASS |
| CA_Pillar_N_8500 | 8425..8575 | -2073..-1927 | 353.1 | FloodedLedge 00-01 | 326.8 | Patrol_Crypt_02 | PASS |
| CA_Pillar_S_8000 | 7925..8075 | -2973..-2827 | 809.3 | FloodedLedge 00-01 | 248.6 | Search_Crypt_03 | PASS |
| CA_Pillar_S_8500 | 8425..8575 | -2973..-2827 | 479.8 | FloodedLedge 00-01 | 248.6 | Search_Crypt_03 | PASS |
| CD_CageOpen | 11130..11270 | -2436..-2264 | 266.1 | CryptToCloister 00-01 | 586.1 | Patrol_Crypt_04 | PASS |
| CD_SkeletonStake | 7495..7649 | -2922..-2756 | 1163.6 | FloodedLedge 00-01 | 506.5 | Search_Crypt_02 | PASS |
| CD_WinchFrame | 10670..10930 | -2165..-2075 | 163.7 | CryptToCloister 00-01 | 170.1 | Search_Crypt_13 | PASS |

RouteBot approach points (bounds + 120 cm on 4 sides; pawn box +-42 cm XY, Z -595..-430) against 125 collision-bearing actors in the crypt box (scan 1108 s; first component of each actor).

| Target | Side | Approach point | Overlapping actors | Result |
|---|---|---|---|---|
| Crank_Winch (8388..8412 x -2712..-2688) | +X | (8532, -2700) | Prop_Crypt_1 (BlockAll) | OVERLAP |
| Crank_Winch (8388..8412 x -2712..-2688) | -X | (8268, -2700) | none | PASS |
| Crank_Winch (8388..8412 x -2712..-2688) | +Y | (8400, -2568) | CA_Pillar_Free_8500 (BlockAll) | OVERLAP |
| Crank_Winch (8388..8412 x -2712..-2688) | -Y | (8400, -2832) | CA_Pillar_S_8500 (BlockAll) | OVERLAP |
| Winch_Ritual2 (10750..10850 x -2050..-1950) | +X | (10970, -2000) | none | PASS |
| Winch_Ritual2 (10750..10850 x -2050..-1950) | -X | (10630, -2000) | none | PASS |
| Winch_Ritual2 (10750..10850 x -2050..-1950) | +Y | (10800, -1830) | CP_Crypt_Mech2 (Custom) | OVERLAP |
| Winch_Ritual2 (10750..10850 x -2050..-1950) | -Y | (10800, -2170) | CD_WinchFrame (BlockAll) | OVERLAP |

RouteBot tries attempt 0 = in front, 1-2 = the sides, 3 = behind; every OVERLAP row is listed for the lead.

**Lane overall (check 1): FAIL**

