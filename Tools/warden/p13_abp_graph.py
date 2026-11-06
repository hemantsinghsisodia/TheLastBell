"""P13-6: build ABP_Warden's AnimGraph through the Unreal MCP tools (editor open). Spec: Docs/plans/P13_WARDEN_ANIMATION.md section 9.

Usage: python -I p13_abp_graph.py <step> [<step> ...]     steps: create, props, read
  create  wipe every node except Output Pose and place + wire the whole chain (ABP_Warden, or ABP_P13_Spike with env P13_TARGET=spike)
  props   set the node options (bones, spaces, modes, LOD threshold) and read them back
  read    print every node and its connections as a chain; compile (strict) and list log warnings
Idempotent: create deletes the previous graph first.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p13_abp_lib import *  # noqa: E402,F401,F403

DIR = "/Game/LastBell/Characters/Warden/"
TARGET = DIR + ("ABP_P13_Spike.ABP_P13_Spike" if os.environ.get("P13_TARGET") == "spike" else "ABP_Warden.ABP_Warden")
GRAPH = TARGET + ":AnimGraph"

T_BSP_LOC = "Animation|BlendSpaces|BlendspacePlayer'BS_Warden_Locomotion'"
T_BSP_STOOP = "Animation|BlendSpaces|BlendspacePlayer'BS_Warden_Stoop'"
T_BLEND = "Animation|Blends|TwoWayBlend"
T_SLOT = "Animation|Montage|Slot'DefaultSlot'"
T_L2C = "Animation|ConvertSpaces|LocalToComponent"
T_TMB = "Animation|SkeletalControls|Transform(Modify)Bone"
T_IK = "Animation|SkeletalControls|TwoBoneIK"
T_RB = "Animation|Dynamics|RigidBody"
T_C2L = "Animation|ConvertSpaces|ComponentToLocal"


def getter(var):
    return "Variables|Warden|Get" + var


def node_name(path):
    return path.split(".")[-1]


def step_create():
    g = GRAPH
    for p in find_nodes(g, ""):
        if "AnimGraphNode_Root" not in p:
            bp_call("delete_node", {"node": ref(p)})
    root = find_nodes(g, "Output Pose")
    root = root[0] if root else find_nodes(g, "")[0]
    print("root", root)

    N = {}
    N["bsp_loc"] = create_node(g, T_BSP_LOC, -2200, -150)
    N["bsp_stoop"] = create_node(g, T_BSP_STOOP, -2200, 150)
    N["blend"] = create_node(g, T_BLEND, -1900, 0)
    N["slot"] = create_node(g, T_SLOT, -1650, 0)
    N["l2c"] = create_node(g, T_L2C, -1450, 0)
    N["tmb"] = create_node(g, T_TMB, -1200, 0)
    N["ik_l"] = create_node(g, T_IK, -900, 0)
    N["ik_r"] = create_node(g, T_IK, -600, 0)
    N["rb"] = create_node(g, T_RB, -300, 0)
    N["c2l"] = create_node(g, T_C2L, -100, 0)
    N["root"] = root
    for k, v in N.items():
        print(k, v)

    # variable getters
    N["v_gs_loc"] = create_node(g, getter("GroundSpeed"), -2450, -150)
    N["v_gs_stoop"] = create_node(g, getter("GroundSpeed"), -2450, 150)
    N["v_stoop"] = create_node(g, getter("StoopAlpha"), -2150, 330)
    N["v_pelvis"] = create_node(g, getter("PelvisOffset"), -1450, 250)
    N["v_alpha_t"] = create_node(g, getter("FootIKAlpha"), -1450, 350)
    N["v_ikl"] = create_node(g, getter("FootIKLeft"), -1100, 250)
    N["v_alpha_l"] = create_node(g, getter("FootIKAlpha"), -1100, 350)
    N["v_ikr"] = create_node(g, getter("FootIKRight"), -800, 250)
    N["v_alpha_r"] = create_node(g, getter("FootIKAlpha"), -800, 350)
    N["v_phys"] = create_node(g, getter("PhysicsAlpha"), -500, 250)

    # pose chain (output pin 0 -> input pin 0 unless noted)
    connect(N["bsp_loc"], 0, N["blend"], 0)      # A
    connect(N["bsp_stoop"], 0, N["blend"], 1)    # B
    connect(N["blend"], 0, N["slot"], 0)
    connect(N["slot"], 0, N["l2c"], 0)
    connect(N["l2c"], 0, N["tmb"], 0)
    connect(N["tmb"], 0, N["ik_l"], 0)
    connect(N["ik_l"], 0, N["ik_r"], 0)
    connect(N["ik_r"], 0, N["rb"], 0)
    connect(N["rb"], 0, N["c2l"], 0)
    connect(N["c2l"], 0, root, 0)
    # variable bindings (getter output 0 -> named input pin)
    connect(N["v_gs_loc"], 0, N["bsp_loc"], 0)
    connect(N["v_gs_stoop"], 0, N["bsp_stoop"], 0)
    connect(N["v_stoop"], 0, N["blend"], 2)      # Alpha
    connect(N["v_pelvis"], 0, N["tmb"], 2)       # Translation
    connect(N["v_alpha_t"], 0, N["tmb"], 1)      # Alpha
    connect(N["v_ikl"], 0, N["ik_l"], 2)         # EffectorLocation
    connect(N["v_alpha_l"], 0, N["ik_l"], 1)
    connect(N["v_ikr"], 0, N["ik_r"], 2)
    connect(N["v_alpha_r"], 0, N["ik_r"], 1)
    connect(N["v_phys"], 0, N["rb"], 1)          # Alpha
    print("created")


def by_class(cls_fragment):
    """Nodes of the AnimGraph whose object name contains the fragment, sorted by name."""
    return sorted(p for p in find_nodes(GRAPH, "") if cls_fragment in node_name(p))


def set_node(path, node_values):
    r = set_props(path, {"Node": node_values})
    if r not in (None, True, "True", "true") and r:
        print("  set_properties ->", str(r)[:300])


def step_props():
    tmb = by_class("AnimGraphNode_ModifyBone")[0]
    set_node(tmb, {"boneToModify": {"boneName": "pelvis"},
                   "translationMode": "BMM_Additive", "translationSpace": "BCS_ComponentSpace",
                   "rotationMode": "BMM_Ignore", "scaleMode": "BMM_Ignore",
                   "alphaInputType": "Float"})
    iks = by_class("AnimGraphNode_TwoBoneIK")
    assert len(iks) == 2, iks
    for ik, side in zip(iks, ("l", "r")):
        foot, calf = "foot_" + side, "calf_" + side
        set_node(ik, {"iKBone": {"boneName": foot},
                      "effectorLocationSpace": "BCS_BoneSpace",
                      "effectorTarget": {"bUseSocket": False, "boneReference": {"boneName": foot}},
                      "jointTarget": {"bUseSocket": False, "boneReference": {"boneName": calf}},
                      "jointTargetLocationSpace": "BCS_BoneSpace",
                      "alphaInputType": "Float"})
    rb = by_class("AnimGraphNode_RigidBody")[0]
    set_node(rb, {"simulationSpace": "ComponentSpace", "lODThreshold": 1})
    print("props set")


def step_read():
    """Print every node's options and pin connections, compile strictly, list warnings from the log."""
    nodes = find_nodes(GRAPH, "")
    print(len(nodes), "nodes in", GRAPH)
    for n in infos(nodes):
        print("--", node_name(n["node"]["refPath"]), "|", n["type_id"])
        for p in n["input_pins"]:
            conn = [node_name(c["node"]["refPath"]) + "#" + str(c["index_id"]) for c in p["connected_pins"]]
            print("    in ", p["pin_id"]["index_id"], p["name"], "=", p["value"][:50], "<-", conn)
        for p in n["output_pins"]:
            conn = [node_name(c["node"]["refPath"]) + "#" + str(c["index_id"]) for c in p["connected_pins"]]
            print("    out", p["pin_id"]["index_id"], p["name"], "->", conn)
    for frag, props in (("AnimGraphNode_BlendSpacePlayer", ["Node"]), ("AnimGraphNode_Slot", ["Node"]),
                        ("AnimGraphNode_ModifyBone", ["Node"]), ("AnimGraphNode_TwoBoneIK", ["Node"]),
                        ("AnimGraphNode_RigidBody", ["Node"])):
        for p in by_class(frag):
            v = get_props(p, props)
            v = json.loads(v) if isinstance(v, str) else v
            node = v["Node"]
            keep = {k: node[k] for k in node if k in (
                "blendSpace", "slotName", "boneToModify", "translationMode", "translationSpace", "rotationMode", "scaleMode",
                "iKBone", "effectorLocationSpace", "effectorTarget", "jointTarget", "jointTargetLocationSpace",
                "simulationSpace", "lODThreshold", "alphaInputType", "x")}
            print("opts", node_name(p), json.dumps(keep))
    try:
        compile_bp(TARGET, True)
        print("COMPILE (warnings as errors): OK, no errors, no warnings raised")
    except Exception as e:
        print("COMPILE RAISED:", str(e)[:1500])
    r = call("EditorToolset.LogsToolset", "GetLogEntries",
             {"category": "LogBlueprint", "pattern": "ABP_Warden|AnimGraph|\\[Compiler\\]", "maxEntries": 12})
    for line in r:
        print("log:", line[:300])


def step_save():
    pkg = TARGET.split(".")[0]
    print("is_dirty before:", call(AST, "is_dirty", {"asset_path": pkg}))
    print("save_assets:", call(AST, "save_assets", {"asset_paths": [pkg]}))
    print("is_dirty after:", call(AST, "is_dirty", {"asset_path": pkg}))


if __name__ == "__main__":
    for s in sys.argv[1:]:
        globals()["step_" + s]()
