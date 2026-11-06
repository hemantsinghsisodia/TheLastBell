"""P13-6 follow-up: robe and chain physics on SK_Warden_PhysicsAsset (editor open, PhysicsToolsets.PhysicsAssetToolset).

Usage: python -I p13_physics.py <step> [...]    steps: before, edit, after
  before  write Docs/ArtTest/warden/p13_physics_before.json (bodies, shapes, modes, constraints)
  edit    add the missing chain bodies and their constraints, set modes and limits
  after   write Docs/ArtTest/warden/p13_physics_after.json and print a summary
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p13_abp_lib import *  # noqa: E402,F401,F403

PA = "/Game/LastBell/Characters/Warden/Meshes/SK_Warden_PhysicsAsset.SK_Warden_PhysicsAsset"
PT = "PhysicsToolsets.PhysicsAssetToolset"
OUT = r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\warden"


def pcall(tool, **kw):
    kw["physicsAsset"] = ref(PA)
    return call(PT, tool, kw)


def snapshot():
    names = pcall("GetBodyNames")
    bodies = {}
    for n in names:
        bodies[n] = {"mode": pcall("GetBodyPhysicsMode", boneName=n),
                     "massScale": pcall("GetBodyMassScale", boneName=n),
                     "shapes": pcall("GetBodyShapes", boneName=n)}
    return {"asset": PA, "bodyNames": names, "bodies": bodies, "constraints": pcall("GetConstraints")}


def step_before():
    s = snapshot()
    json.dump(s, open(os.path.join(OUT, "p13_physics_before.json"), "w"), indent=1)
    print("bodies", len(s["bodyNames"]), "constraints", len(s["constraints"]))
    for n, b in s["bodies"].items():
        sh = b["shapes"]
        print(f"{n:16} {b['mode']:10} " + "; ".join(
            f"{x['shapeType']} c=({x['center']['x']:.1f},{x['center']['y']:.1f},{x['center']['z']:.1f}) "
            f"r=({x['rotation']['pitch']:.0f},{x['rotation']['yaw']:.0f},{x['rotation']['roll']:.0f}) R={x['radius']:.2f} L={x['length']:.2f}"
            for x in sh))
    for c in s["constraints"]:
        print("C", c["bone1Name"], "->", c["bone2Name"], c["swing1Motion"], c["swing1LimitDegrees"], c["swing2Motion"],
              c["swing2LimitDegrees"], c["twistMotion"], c["twistLimitDegrees"])


# Capsule axis is bone-local +Z on both sides (child offset is (0,0,+L)); rotation (0,-90,0) is what every chain body carries.
# Link lengths from the reference pose (p13_bone_probe.json): chain_l 17.5 cm, chain_r 2.5 cm, chain_neck 1.88 cm. The left
# capsules (24 cm for a 35 cm body spacing) do not fit the 5 cm spacing of the right chain, so right and neck capsules are
# sized from the spacing: radius 2.38 as the existing ones, total height = spacing, centred half-way.
R = 2.38
CHAINS = [  # (body, parent body, spacing in cm to the next body)
    ("chain_r_00", "lowerarm_r", 5.0), ("chain_r_02", "chain_r_00", 5.0), ("chain_r_04", "chain_r_02", 5.0),
    ("chain_r_06", "chain_r_04", 5.0), ("chain_r_08", "chain_r_06", 5.0), ("chain_r_10", "chain_r_08", 5.0),
    ("chain_neck_01", "neck_01", 7.5), ("chain_neck_05", "chain_neck_01", 7.5),
    ("chain_neck_09", "chain_neck_05", 7.5), ("chain_neck_13", "chain_neck_09", 7.5),
]
SWING, TWIST = 30.0, 10.0


def is_sim(name):
    return name.startswith("chain_") or name.startswith("robe_")


def step_edit():
    names = pcall("GetBodyNames")
    cons = {(c["bone1Name"], c["bone2Name"]) for c in pcall("GetConstraints")}
    for body, parent, spacing in CHAINS:
        if body not in names:
            pcall("AddBody", boneName=body)
            print("AddBody", body)
        L = max(spacing - 2 * R, 0.1)
        pcall("SetCapsule", boneName=body, shapeName="None", center={"x": 0, "y": 0, "z": spacing / 2},
              rotation={"pitch": 0, "yaw": -90, "roll": 0}, radius=R, length=L)
        # make the chain link to the previous body: drop a wrong existing parent, add the right one
        for (c1, c2) in sorted(cons):
            if c1 == body and c2 != parent:
                pcall("RemoveConstraint", bone1Name=c1, bone2Name=c2)
                cons.discard((c1, c2))
                print("RemoveConstraint", c1, "->", c2)
        if (body, parent) not in cons:
            pcall("AddConstraint", bone1Name=body, bone2Name=parent)
            cons.add((body, parent))
            print("AddConstraint", body, "->", parent)
    names = pcall("GetBodyNames")
    for n in names:
        pcall("SetBodyPhysicsMode", boneName=n, mode="Simulated" if is_sim(n) else "Kinematic")
    for c in pcall("GetConstraints"):
        if is_sim(c["bone1Name"]):
            info = dict(c)
            info.update(swing1Motion="Limited", swing1LimitDegrees=SWING, swing2Motion="Limited", swing2LimitDegrees=SWING,
                        twistMotion="Limited", twistLimitDegrees=TWIST)
            pcall("SetConstraintLimits", info=info)
    print("edit done")


def body_setups():
    """bone name -> (setup object path, physicsType, linearDamping, angularDamping); the toolset has no damping setter, so ObjectTools."""
    out = {}
    for i in range(0, 120):
        p = f"{PA}:SkeletalBodySetup_{i}"
        try:
            v = get_props(p, ["boneName", "physicsType", "defaultInstance"])
        except Exception:
            continue
        v = json.loads(v) if isinstance(v, str) else v
        di = v["defaultInstance"]
        out[v["boneName"]] = (p, v["physicsType"], di["linearDamping"], di["angularDamping"])
    return out


def step_damping(lin=0.6, ang=1.0):
    for bone, (p, _t, _l, _a) in body_setups().items():
        if is_sim(bone):
            set_props(p, {"defaultInstance": {"linearDamping": lin, "angularDamping": ang}})
    bs = body_setups()
    bad = [b for b, v in bs.items() if is_sim(b) and (round(v[2], 3), round(v[3], 3)) != (lin, ang)]
    print("damping set on", sum(1 for b in bs if is_sim(b)), "sim bodies; wrong:", bad)


def step_after():
    s = snapshot()
    bs = body_setups()
    s["setupPhysicsType"] = {b: v[1] for b, v in bs.items()}
    s["damping"] = {b: {"linear": v[2], "angular": v[3]} for b, v in bs.items()}
    print("setup physicsType (sim):", sorted({v[1] for b, v in bs.items() if is_sim(b)}),
          " (other):", sorted({v[1] for b, v in bs.items() if not is_sim(b)}))
    print("damping sim:", sorted({(round(v[2], 3), round(v[3], 3)) for b, v in bs.items() if is_sim(b)}),
          " other:", sorted({(round(v[2], 3), round(v[3], 3)) for b, v in bs.items() if not is_sim(b)}))
    json.dump(s, open(os.path.join(OUT, "p13_physics_after.json"), "w"), indent=1)
    before = json.load(open(os.path.join(OUT, "p13_physics_before.json")))
    modes = [b["mode"] for b in s["bodies"].values()]
    print("bodies", len(s["bodyNames"]), "(before", len(before["bodyNames"]), ")  simulated", modes.count("Simulated"),
          "kinematic", modes.count("Kinematic"), "other", len(modes) - modes.count("Simulated") - modes.count("Kinematic"))
    print("new bodies", sorted(set(s["bodyNames"]) - set(before["bodyNames"])))
    key = lambda c: (c["bone1Name"], c["bone2Name"])
    bc = {key(c): c for c in before["constraints"]}
    ac = {key(c): c for c in s["constraints"]}
    print("constraints", len(ac), "(before", len(bc), ")")
    print("new constraints", sorted(set(ac) - set(bc)))
    print("removed constraints", sorted(set(bc) - set(ac)))
    changed = [k for k in ac if k in bc and ac[k] != bc[k]]
    print("limit changes on", len(changed), "constraints; non-sim changed:", [k for k in changed if not is_sim(k[0])])
    print("sim constraints not 30/10:", [k for k in ac if is_sim(k[0]) and (
        ac[k]["swing1LimitDegrees"], ac[k]["swing2LimitDegrees"], ac[k]["twistLimitDegrees"]) != (SWING, SWING, TWIST)])
    print("sim-body without constraint:", [n for n in s["bodyNames"] if is_sim(n) and not any(k[0] == n for k in ac)])
    print("shape counts != 1:", [n for n, b in s["bodies"].items() if len(b["shapes"]) != 1])
    for n in ("chain_r_00", "chain_r_04", "chain_r_10", "chain_neck_01", "chain_neck_05", "chain_neck_13"):
        sh = s["bodies"][n]["shapes"][0]
        print(" ", n, s["bodies"][n]["mode"], "R", round(sh["radius"], 2), "L", round(sh["length"], 2), "cz", round(sh["center"]["z"], 2))


def step_save():
    pkg = PA.split(".")[0]
    print("is_dirty before:", call(AST, "is_dirty", {"asset_path": pkg}))
    print("save_assets:", call(AST, "save_assets", {"asset_paths": [pkg]}))
    print("is_dirty after:", call(AST, "is_dirty", {"asset_path": pkg}))


if __name__ == "__main__":
    for s in sys.argv[1:]:
        globals()["step_" + s]()
