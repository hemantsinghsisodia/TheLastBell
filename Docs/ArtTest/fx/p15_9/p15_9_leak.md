# P15-9 leak test (camera rain on vs bRain off; rain columns run in both)

| Pose | Roofed rects | White pixels in rects (on) | Whole-frame white (on) | MAD in rects (/255) | Test MAD <= 1 |
|---|---|---|---|---|---|
| s1_cy_n_up | none (judged by eye) | - | 0 | - | by eye |
| s1_cy_n_floor | none (judged by eye) | - | 0 | - | by eye |
| s1_cy_s_up | none (judged by eye) | - | 0 | - | by eye |
| s1_ch_hole_up | 2 | 0 | 2 | 0.225 | PASS |
| s1_ch_floor | 2 | 0 | 0 | 0.451 | PASS |
| s1_cl_s_walk | 3 | 0 | 0 | 0.086 | PASS |
| s1_cl_n_hole | none (judged by eye) | - | 0 | - | by eye |
| s1_tw_belfry | none (judged by eye) | - | 0 | - | by eye |
| s1_tw_mid_stair | 1 | 317 | 317 | 0.865 | PASS |
| s1_tw_belfry_sw | none (judged by eye) | - | 0 | - | by eye |
