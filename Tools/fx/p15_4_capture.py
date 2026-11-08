"""Capture asset thumbnails to Docs/ArtTest/fx/p15_4/<name>.png (editor open)."""
import sys, base64, time
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\fx")
from p15_mat_lib import *
OUT = r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\fx\p15_4"
for a in sys.argv[1:]:
    name = a.rsplit("/", 1)[-1]
    for attempt in range(4):
        r = ue.raw("call_tool", {"toolset_name": "EditorToolset.EditorAppToolset", "tool_name": "CaptureAssetImage", "arguments": {"assetPath": a}})
        data = base64.b64decode(r["returnValue"]["data"])
        if attempt == 3 or len(data) > 0:
            pass
        open(OUT + "\\" + name + ".png", "wb").write(data)
        print(name, len(data), "bytes try", attempt)
        break
