import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")
from ue import UE
ue = UE()
O = "editor_toolset.toolsets.object.ObjectTools"
g = json.load(open(r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\gameplay_p10.json"))
out = {}
for a in g["actors"]:
    for c in a["components"]:
        if "BoxComponent" in c["class"]:
            ref = {"refPath": a["ref"] + "." + c["name"]}
            r = ue.call(O, "get_properties", {"instance": ref, "properties": ["boxExtent", "bGenerateOverlapEvents"]})
            r = json.loads(r) if isinstance(r, str) else r
            out[a["label"]] = {"center": [a["transform"]["location"][k] for k in "xyz"], "boxExtent": r.get("boxExtent"), "overlap": r.get("bGenerateOverlapEvents"), "profile": c.get("collisionProfile")}
            print(a["label"], out[a["label"]])
json.dump(out, open(r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\triggers_p10.json", "w"), indent=1)
