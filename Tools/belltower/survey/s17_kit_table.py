"""Offline: kit_p10.json -> markdown table rows (stdout)."""
import json, sys
d = json.load(open(r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\kit_p10.json"))
def short(p): return p.split("/")[-1].split(".")[0] if p else "-"
rows = []
for p, r in sorted(d.items()):
    if "err" in r: rows.append((p, "ERR " + r["err"])); continue
    b = r["bounds"]; mn, mx = b["min"], b["max"]
    sz = (mx["x"] - mn["x"], mx["y"] - mn["y"], mx["z"] - mn["z"])
    name = short(p)
    folder = p.split("/")
    grp = "Kit" if "/Kit/" in p else "Crypt" if "/Crypt/" in p else "Procedural" if "Procedural" in p else "CC0" if "CC0" in p else "ArtTest" if "ArtTest" in p else "Dungeon" if "Dungeon" in p else "Fab-other"
    slots = ", ".join("%s>%s" % (k, short(v)) for k, v in r["slots"].items())
    ucx = r.get("ucx_convex", 0) + r.get("ucx_box", 0)
    rows.append((grp, name, "%.0f..%.0f, %.0f..%.0f, %.0f..%.0f" % (mn["x"], mx["x"], mn["y"], mx["y"], mn["z"], mx["z"]), "%.0f x %.0f x %.0f" % sz, slots, "Y" if r["nanite"] else "-", r["tris"], "%d (%s)" % (ucx, (r.get("collisionTraceFlag") or "").replace("CTF_", ""))))
cur = None
for r in rows:
    if len(r) == 2: print(r); continue
    if r[0] != cur:
        cur = r[0]; print("\n### " + cur)
        print("| Mesh | Bounds (mesh-local) | Size X x Y x Z | Slots > MI | Nanite | Tris | UCX (trace flag) |")
        print("|---|---|---|---|---|---|---|")
    print("| %s | %s | %s | %s | %s | %s | %s |" % r[1:])
