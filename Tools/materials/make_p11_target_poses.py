"""P11-8: the earlier phases' brightness and readability views as one pose file. No editor needed.

    python -I Tools/materials/make_p11_target_poses.py

Writes Tools/materials/poses/p11_8_target_poses.json from the poses that carry a target in D-058, Docs/plans/P8_CHAPEL_ART.md, P9_CRYPT_ART.md and
P10_BELLTOWER_ART.md (D1.25). Views already in p11_poses.json are left out (lt_tower_mid = tw_mid_stair, lt_belfry_up_sw = tw_belfry).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
P9 = ["01_stair_foot", "02_landing", "03_WC", "04_SC", "05_ossuary_from_J4", "06_ossuary_across", "07_FP_ledge", "08_CC_from_J6", "09_puzzle_wall", "10_NC_gate", "plaque_2m", "d11_FP_from_W"]
P10_SKIP = {"lt_tower_mid", "lt_belfry_up_sw"}


def load(*parts):
    return json.load(open(os.path.join(ROOT, *parts), encoding="utf-8"))


def main():
    poses = {
        "t7_courtyard_to_chapel": [500, 0, 170, 0, 0],
        "t8_entrance": [6200, 0, 170, 0, 0],
        "t8_midnave": [7300, 0, 170, 0, 0],
        "t8_sacristy": [8250, -900, 170, 0, -45],
        "t8_clue_window": [8750, 300, 170, 16, 90],
        "t8_puzzle_candles": [8300, 420, 180, -13, -40],
    }
    p9 = load("Tools", "crypt", "poses", "p9l_poses.json")
    for k in P9:
        poses["t9_" + k] = p9[k]
    for f in ("p10_7_poses.json", "p10_7c_poses.json"):
        for k, v in load("Tools", "belltower", "poses", f).items():
            if k not in P10_SKIP:
                poses["t10_" + k] = v
    out = os.path.join(HERE, "poses", "p11_8_target_poses.json")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(poses, fh, indent=1)
    print(len(poses), "poses")
    for k, v in poses.items():
        print(k, v)


if __name__ == "__main__":
    main()
