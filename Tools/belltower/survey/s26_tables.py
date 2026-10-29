"""P10-2 (offline): generate the markdown table fragments used in survey_p10.md from the JSON dumps. Output dir = argv[1]."""
import json, re, sys, os
OUT = sys.argv[1]
B = r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower" + "\\"
D = json.load(open(B + "greybox_p10.json"))
by = {x["label"]: x for x in D}
def box(x):
    b = x["bounds"]; return (b["min"]["x"], b["max"]["x"], b["min"]["y"], b["max"]["y"], b["min"]["z"], b["max"]["z"])
def f(v):
    return ("%.3f" % v).rstrip("0").rstrip(".")
def rng(a, b): return "%s..%s" % (f(a), f(b))
def aabb(b): return "X %s, Y %s, Z %s" % (rng(b[0], b[1]), rng(b[2], b[3]), rng(b[4], b[5]))
def mat(x): return (x.get("materials") or ["(none)"])[0].split("/")[-1].split(".")[0]
def w(name, s): open(os.path.join(OUT, name), "w", encoding="utf-8").write(s)

# ---- cloister + shell table
def table(labels, extra=True):
    s = "| Actor | AABB (cm) | Scale | Material |\n|---|---|---|---|\n"
    for l in labels:
        x = by[l]; t = x["transform"]["scale"]
        s += "| `%s` | %s | %s x %s x %s | %s |\n" % (l, aabb(box(x)), f(t["x"]), f(t["y"]), f(t["z"]), mat(x))
    return s
cl = sorted([x["label"] for x in D if x["folder_query"] == "Cloister"])
w("cloister.md", table(cl))
tw = ["Tw_W_S", "Tw_W_N", "Tw_W_Lintel", "Tw_N", "Tw_S", "Tw_E", "Tw_Roof", "Tw_Core", "Top_Slab_W", "Top_Slab_N", "Top_Rail_E", "Top_Rail_S", "Bell_Beam", "Bell_Chain"]
w("tower_shell.md", table(tw))
pas = ["Passage_S", "Passage_N", "KW_ShortcutDoorway", "KW_ShortcutUpper", "KW_ShortcutTympanum", "Ground_4", "Ground_6"]
w("passage.md", table(pas))

# ---- landings
s = "| Landing | AABB (cm) | Top Z | Underside Z | Corner |\n|---|---|---|---|---|\n"
corner = {1: "NE", 2: "SE", 3: "SW", 4: "NW"}
for n in range(1, 11):
    b = box(by["Tw_Landing_%02d" % n]); c = corner[(n - 1) % 4 + 1]
    s += "| `Tw_Landing_%02d` | X %s, Y %s | %s | %s | %s |\n" % (n, rng(b[0], b[1]), rng(b[2], b[3]), f(b[5]), f(b[4]), c)
w("landings.md", s)

# ---- flights
steps = {}
for x in D:
    m = re.match(r"Stair_F(\d+)_(\d+)$", x["label"])
    if m: steps.setdefault(int(m.group(1)), {})[int(m.group(2))] = x
land = {n: box(by["Tw_Landing_%02d" % n]) for n in range(1, 11)}
rails = {}
for x in D:
    m = re.match(r"Rail_F(\d+)_(\d+)$", x["label"])
    if m: rails.setdefault(int(m.group(1)), {})[int(m.group(2))] = x
ring = {"+X": "N ring (Y 2210..2460), along the core's N face", "-Y": "E ring (X 12710..12960), along the core's E face",
        "-X": "S ring (Y 1540..1790), along the core's S face", "+Y": "W ring (X 12040..12290), along the core's W face"}
s = "| Flight | Heading | Lane | Step 0 AABB | Step 13 AABB | Base Z | Last tread top Z | Before | After |\n|---|---|---|---|---|---|---|---|---|\n"
for fl in range(1, 12):
    a = box(steps[fl][0]); z = box(steps[fl][13])
    cx = (z[0] + z[1]) / 2 - (a[0] + a[1]) / 2; cy = (z[2] + z[3]) / 2 - (a[2] + a[3]) / 2
    d = ("+X" if cx > 0 else "-X") if abs(cx) > abs(cy) else ("+Y" if cy > 0 else "-Y")
    before = "ground, NW pad (Z 0)" if fl == 1 else "`Tw_Landing_%02d` (top %s)" % (fl - 1, f(land[fl - 1][5]))
    after = ("`Tw_Landing_%02d` (top %s)" % (fl, f(land[fl][5]))) if fl <= 10 else "`Top_Slab_W` (top 2500)"
    s += "| F%02d | %s | %s | %s | %s | %s | %s | %s | %s |\n" % (fl, d, ring[d].split(" (")[0], aabb(a), aabb(z), f(a[4]), f(z[5]), before, after)
w("flights.md", s)

# ---- rails
s = "| Flight | Pieces | Piece size (dx x dy x dz) | Plane (face coordinate) | Bottom Z first..last | Top Z first..last |\n|---|---|---|---|---|---|\n"
for fl in range(1, 12):
    bs = [box(rails[fl][i]) for i in sorted(rails[fl])]
    dx, dy, dz = bs[0][1] - bs[0][0], bs[0][3] - bs[0][2], bs[0][5] - bs[0][4]
    plane = ("Y %s..%s" % (f(bs[0][2]), f(bs[0][3]))) if dx > dy else ("X %s..%s" % (f(bs[0][0]), f(bs[0][1])))
    s += "| F%02d | %d | %s x %s x %s | %s | %s..%s | %s..%s |\n" % (fl, len(bs), f(dx), f(dy), f(dz), plane, f(bs[0][4]), f(bs[-1][4]), f(bs[0][5]), f(bs[-1][5]))
w("rails.md", s)

# ---- gameplay actor table
g = json.load(open(B + "gameplay_p10.json"))
s = "| Actor | Class | Folder | World location | Rotation (yaw) | Scale |\n|---|---|---|---|---|---|\n"
for a in g["actors"]:
    t = a["transform"]; l = t["location"]
    s += "| `%s` | %s | %s | (%s, %s, %s) | %s | %s |\n" % (a["label"], a["class"].split(".")[-1], a["folder"], f(l["x"]), f(l["y"]), f(l["z"]), f(t["rotation"]["yaw"]),
          "x".join(f(t["scale"][k]) for k in "xyz"))
w("gameplay_actors.md", s)

# ---- AI
ai = json.load(open(B + "ai_p10.json"))
s = "| Marker | Location (X, Y, Z) | Notes |\n|---|---|---|\n"
for k in ["AI/Patrol", "AI/Search", "AI/Spawn"]:
    for i in ai[k]:
        p = i["props"]; note = ""
        if "routeId" in p: note = "route `%s`" % p["routeId"] + (", order %s, wait %ss" % (p["order"], p["waitSeconds"]) if "order" in p else "") + (", min stage %s" % p["minStage"] if "minStage" in p else "")
        s += "| `%s` | (%s, %s, %s) | %s |\n" % (i["label"], f(i["loc"][0]), f(i["loc"][1]), f(i["loc"][2]), note)
w("ai.md", s)
s = "| WalkPath point | Location | Tags |\n|---|---|---|\n"
for i in ai["WalkPaths/TowerStairs"]:
    s += "| `%s` | (%s, %s, %s) | %s |\n" % (i["label"], f(i["loc"][0]), f(i["loc"][1]), f(i["loc"][2]), ", ".join(i["props"].get("tags", [])))
w("walkpath_tower.md", s)
print("ok")
