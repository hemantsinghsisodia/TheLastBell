"""update_growth_obstacles.py -- fills MPC_LB_GrowthObstacles from the structures in the loaded level.

The floor growth layer of M_LB_Surface (bGapGrowth, D-056) needs "distance to the nearest wall/pier/kerb/prop base".
The engine's DistanceToNearestSurface (global distance field) returns 0 in this project (Lumen hardware RT, no GDF), so the
material measures the XY distance to up to 48 boxes stored in the Material Parameter Collection instead.

    python update_growth_obstacles.py [--dry] [--prefix KW_ KG_ ...]    (editor open on L_Monastery)

Each MPC vector is (centreX, centreY, halfX, halfY) in world cm; halfX < 0 = unused slot.  Actors are selected by LABEL prefix, their
world AABB (ActorTools.get_actor_bounds, scale-safe for kit pieces) is taken if it reaches walking height (Z max >= 60, Z min <= 400) and lies in the
courtyard region, nearby boxes are merged (union <= 1.2 x the sum), and the 48 longest boxes are written.  Re-run after moving structures.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ue import UE

AT = "editor_toolset.toolsets.asset.AssetTools"
OT = "editor_toolset.toolsets.object.ObjectTools"
MT = "editor_toolset.toolsets.material.MaterialTools"
SC = "editor_toolset.toolsets.scene.SceneTools"
AC = "editor_toolset.toolsets.actor.ActorTools"
MPC_DIR = "/Game/LastBell/Materials"
MPC_NAME = "MPC_LB_GrowthObstacles"
SLOTS = 48
LEVEL = "/Game/LastBell/Maps/L_Monastery"
PREFIXES = ("KW_", "KG_", "KC_", "KD_", "KA_Cliff", "Chapel_", "Cl_", "KP_Statue", "Arc_", "KK_", "KB_", "KT_", "KR_", "KS_",
            # P7-FIX3 G4: twin-arch arcade (Arc_*: bays + columns), garden kerbs / well-head / trees, roof posts, arcade rubble
            "Garden_WellHead", "Garden_Kerb", "Garden_DeadTree", "Garden_Snag_Trunk", "Roof_N_Post", "Roof_S_Post", "Rub_")
SKIP_PREFIX = ("KD_FountainPost", "KW_Pl", "KG_Pl", "KC_Pl", "KW_Butt", "KG_Butt", "KC_Butt")      # plinth pieces are inside the wall footprint anyway
REGION = (150.0, 6300.0, -2800.0, 2800.0)
MIN_LEN_KEEP = 0.0


def collect(ue, prefixes):
    names = []
    for p in prefixes:                                   # find_actors matches labels by substring; filter by prefix below
        for x in ue.call(SC, "find_actors", {"name": p, "tag": "", "collision_channels": []}):
            n = x["refPath"].split(".")[-1]
            if n not in names:
                names.append(n)
    boxes = []
    for n in names:
        if not n.startswith("StaticMeshActor"):
            continue
        a = {"refPath": LEVEL + "." + LEVEL.rsplit("/", 1)[1] + ":PersistentLevel." + n}
        lab = ue.call(AC, "get_label", {"actor": a})
        if not lab.startswith(tuple(prefixes)) or lab.startswith(SKIP_PREFIX) or lab == "Fountain":
            continue
        b = ue.call(AC, "get_actor_bounds", {"actor": a})
        if not b.get("isValid"):
            continue
        mn, mx = b["min"], b["max"]
        if (mx["z"] < 60 or mn["z"] > 400) and not lab.startswith("Garden_Kerb"):      # kerbs are only 40-45 cm high but outline the beds
            continue
        x0, x1, y0, y1 = mn["x"], mx["x"], mn["y"], mx["y"]
        if x1 < REGION[0] or x0 > REGION[1] or y1 < REGION[2] or y0 > REGION[3] or (x1 - x0) > 9000 or (y1 - y0) > 9000:
            continue
        boxes.append([x0, y0, x1, y1, lab])
    # a kerbed bed is one obstacle: the union of its kerb pieces (label Garden_Kerb[Corner]_<bed>_...); inside it the earth patch covers the floor
    beds = {}
    rest = []
    for b in boxes:
        if b[4].startswith("Garden_Kerb"):
            k = b[4].split("_")[2]
            u = beds.setdefault(k, [b[0], b[1], b[2], b[3], "Garden_Bed_" + k])
            u[0], u[1], u[2], u[3] = min(u[0], b[0]), min(u[1], b[1]), max(u[2], b[2]), max(u[3], b[3])
        else:
            rest.append(b)
    return rest + list(beds.values())


def merge(boxes):
    def area(b):
        return (b[2] - b[0]) * (b[3] - b[1])

    def gap(a, b):
        return max(max(a[0] - b[2], b[0] - a[2], 0), max(a[1] - b[3], b[1] - a[3], 0))

    changed = True
    while changed:
        changed = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                if gap(a, b) <= 25:
                    u = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                    ov = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
                    if area(u) <= 1.2 * (area(a) + area(b) - ov) + 4000:
                        boxes[i] = u + [a[4] + "+"]
                        boxes.pop(j)
                        changed = True
                        break
            if changed:
                break
    boxes.sort(key=lambda b: -max(b[2] - b[0], b[3] - b[1]))
    return boxes


def main():
    args = sys.argv[1:]
    dry = "--dry" in args
    prefixes = PREFIXES
    if "--prefix" in args:
        prefixes = tuple(args[args.index("--prefix") + 1:])
    ue = UE()
    boxes = merge(collect(ue, prefixes))
    print(len(boxes), "merged boxes (max %d written)" % SLOTS)
    for b in boxes[:SLOTS]:
        print([round(v) for v in b[:4]], b[4][:24])
    if dry:
        return
    pkg = MPC_DIR + "/" + MPC_NAME
    ref = {"refPath": pkg + "." + MPC_NAME}
    if not ue.call(AT, "exists", {"path": pkg}):
        ue.call(MT, "create_parameter_collection", {"folder_path": MPC_DIR, "asset_name": MPC_NAME})
    vecs = []
    for i in range(SLOTS):
        if i < len(boxes):
            x0, y0, x1, y1 = boxes[i][:4]
            v = {"r": (x0 + x1) / 2, "g": (y0 + y1) / 2, "b": (x1 - x0) / 2, "a": (y1 - y0) / 2}
        else:
            v = {"r": 0.0, "g": 0.0, "b": -1.0, "a": -1.0}
        vecs.append({"parameterName": "Ob%02d" % i, "defaultValue": v})
    ue.call(OT, "set_properties", {"instance": ref, "values": json.dumps({"vectorParameters": vecs})})
    print(ue.call(OT, "get_properties", {"instance": ref, "properties": ["vectorParameters"]})[:300])
    ue.call(AT, "save_assets", {"asset_paths": [pkg]})
    print("MPC written + saved")


if __name__ == "__main__":
    main()
