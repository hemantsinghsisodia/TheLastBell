"""P10-2 item 1 (offline): analyse greybox_p10.json -> stair/landing/rail/top/touch tables as markdown on stdout (and analysis json)."""
import json, re, itertools, sys
D = json.load(open(r"C:\Hemant\Prj\Learning\TheLastBell\Docs\ArtTest\belltower\greybox_p10.json"))
by = {x["label"]: x for x in D}
def box(x):
    b = x["bounds"]; return (b["min"]["x"], b["max"]["x"], b["min"]["y"], b["max"]["y"], b["min"]["z"], b["max"]["z"])
def overlap(a, b):
    dx = min(a[1], b[1]) - max(a[0], b[0]); dy = min(a[3], b[3]) - max(a[2], b[2]); dz = min(a[5], b[5]) - max(a[4], b[4])
    return dx, dy, dz
steps = {}
for x in D:
    m = re.match(r"Stair_F(\d+)_(\d+)$", x["label"])
    if m: steps.setdefault(int(m.group(1)), {})[int(m.group(2))] = x
land = {int(re.search(r"(\d+)$", x["label"]).group(1)): x for x in D if x["label"].startswith("Tw_Landing_")}
rails = {}
for x in D:
    m = re.match(r"Rail_F(\d+)_(\d+)$", x["label"])
    if m: rails.setdefault(int(m.group(1)), {})[int(m.group(2))] = x
def axis(f):
    a = box(steps[f][0]); z = box(steps[f][13])
    cx0 = (a[0] + a[1]) / 2; cx1 = (z[0] + z[1]) / 2; cy0 = (a[2] + a[3]) / 2; cy1 = (z[2] + z[3]) / 2
    if abs(cx1 - cx0) > abs(cy1 - cy0): return "+X" if cx1 > cx0 else "-X"
    return "+Y" if cy1 > cy0 else "-Y"
out = []
out.append("| Flight | Dir | Lane (X x Y) | Step 0 AABB | Step 13 AABB | Base Z | Top Z (step 13) | Run measured | Rise measured | Lands on |")
out.append("|---|---|---|---|---|---|---|---|---|---|")
rows = []
for f in sorted(steps):
    s = steps[f]; a = box(s[0]); z = box(s[13])
    d = axis(f)
    runs = set(); rises = set()
    for i in range(1, 14):
        p = box(s[i - 1]); q = box(s[i])
        if d in ("+X", "-X"): runs.add(round(abs((q[0] + q[1]) / 2 - (p[0] + p[1]) / 2), 3))
        else: runs.add(round(abs((q[2] + q[3]) / 2 - (p[2] + p[3]) / 2), 3))
        rises.add(round(q[5] - p[5], 3))
    widths = set()
    for i in range(14):
        q = box(s[i])
        widths.add(round((q[3] - q[2]) if d in ("+X", "-X") else (q[1] - q[0]), 3))
        # run (depth)
    depths = set(round((box(s[i])[1] - box(s[i])[0]) if d in ("+X", "-X") else (box(s[i])[3] - box(s[i])[2]), 3) for i in range(14))
    bases = set(round(box(s[i])[4], 3) for i in range(14))
    lane = "X %g..%g, Y %g..%g" % (min(box(s[i])[0] for i in s), max(box(s[i])[1] for i in s), min(box(s[i])[2] for i in s), max(box(s[i])[3] for i in s))
    ln = f  # landing after flight f is Landing_f (f<=10)
    rows.append((f, d, lane, a, z, bases, depths, widths, runs, rises))
    out.append("| F%02d | %s | %s | X %g..%g Y %g..%g Z %.3f..%.3f | X %g..%g Y %g..%g Z %.3f..%.3f | %s | %.3f | %s | %s | %s |" % (
        f, d, lane, a[0], a[1], a[2], a[3], a[4], a[5], z[0], z[1], z[2], z[3], z[4], z[5], sorted(bases), z[5], sorted(runs), sorted(rises),
        ("Landing_%02d" % f) if f in land else "top slab (Z 2500)"))
print("\n".join(out))
print()
print("step depths/widths per flight (run depth, lane width):")
for r in rows: print(" F%02d depth %s width %s base %s" % (r[0], sorted(r[6]), sorted(r[7]), sorted(r[5])))
print()
print("Landings:")
for n in sorted(land):
    b = box(land[n]); print(" Tw_Landing_%02d X %g..%g Y %g..%g Z %.3f..%.3f (thick %.3f)" % (n, b[0], b[1], b[2], b[3], b[4], b[5], b[5] - b[4]))
print()
# landing before/after per flight
print("Landing before / after each flight (top Z):")
for f in sorted(steps):
    before = ("ground NW corner (Z 0)" if f == 1 else "Landing_%02d top %.3f" % (f - 1, box(land[f - 1])[5]))
    after = ("Landing_%02d top %.3f" % (f, box(land[f])[5])) if f in land else "Top_Slab_W top 2500"
    z = box(steps[f][13])
    print(" F%02d before: %s | after: %s | last step top %.3f" % (f, before, after, z[5]))
print()
print("Rails per flight:")
for f in sorted(rails):
    r = rails[f]; bs = [box(r[i]) for i in sorted(r)]
    d = axis(f)
    sizes = set((round(b[1]-b[0],2), round(b[3]-b[2],2), round(b[5]-b[4],2)) for b in bs)
    plane = ("Y %g..%g" % (bs[0][2], bs[0][3])) if d in ("+X", "-X") else ("X %g..%g" % (bs[0][0], bs[0][1]))
    print(" F%02d n=%d size(dx,dy,dz)=%s plane %s bottomZ %.2f..%.2f topZ %.2f..%.2f" % (f, len(r), sorted(sizes), plane, bs[0][4], bs[-1][4], bs[0][5], bs[-1][5]))
# rail bottom = tread top of step 2i?
bad = 0
for f in rails:
    for i in rails[f]:
        rb = box(rails[f][i])[4]; st = box(steps[f][2 * i])[5]
        if abs(rb - st) > 0.01: bad += 1
print("rails whose bottom != top of tread 2i:", bad)
print()
# overlaps: rails vs steps
ov = []
for f in rails:
    for i in rails[f]:
        r = box(rails[f][i])
        for j in steps[f]:
            o = overlap(r, box(steps[f][j]))
            if o[0] > 0.01 and o[1] > 0.01 and o[2] > 0.01: ov.append((rails[f][i]["label"], steps[f][j]["label"], tuple(round(v, 2) for v in o)))
print("rail/step volume overlaps:", len(ov), ov[:6])
# core / wall touch
core = box(by["Tw_Core"])
print("core", core)
# every step vs core and walls: gaps
walls = {k: box(by[k]) for k in ["Tw_W_S", "Tw_W_N", "Tw_N", "Tw_S", "Tw_E", "Tw_Core"]}
mn = {}
for f in steps:
    for i, s in steps[f].items():
        b = box(s)
        for k, w in walls.items():
            dx = max(w[0] - b[1], b[0] - w[1], 0); dy = max(w[2] - b[3], b[2] - w[3], 0); dz = max(w[4] - b[5], b[4] - w[5], 0)
            gap = (dx**2 + dy**2 + dz**2) ** 0.5
            mn.setdefault((f, k), []).append(gap)
print("min gap flight->wall/core (should be 0 where touching):")
for f in sorted(steps):
    print(" F%02d " % f + "  ".join("%s %.2f" % (k, min(mn[(f, k)])) for k in walls))
# steps vs steps overlap between flights; landings vs steps
print("landing vs step volume overlaps:")
for n in land:
    lb = box(land[n])
    for f in steps:
        for i, s in steps[f].items():
            o = overlap(lb, box(s))
            if o[0] > 0.01 and o[1] > 0.01 and o[2] > 0.01: print("  ", land[n]["label"], s["label"], tuple(round(v, 2) for v in o))
print("step vs step (other flights) overlaps:")
n = 0
for f, g in itertools.combinations(sorted(steps), 2):
    for a in steps[f].values():
        for b in steps[g].values():
            o = overlap(box(a), box(b))
            if o[0] > 0.01 and o[1] > 0.01 and o[2] > 0.01:
                n += 1
                if n < 6: print("  ", a["label"], b["label"], o)
print(" total", n)
# landing floating? bottoms
print("landing underside Z:", {n: round(box(land[n])[4], 2) for n in sorted(land)})
# landing support: landing n sits at corner; is it under the next flight's start? check what's directly below (any box overlapping XY with Z below)
print("what supports each landing (boxes whose top ~ landing bottom within 0.01 and XY overlap):")
allb = [(x["label"], box(x)) for x in D if x["folder_query"].startswith("BellTower")]
for n in sorted(land):
    lb = box(land[n]); sup = []
    for lab, b in allb:
        if lab == land[n]["label"]: continue
        o = overlap(lb, b)
        if o[0] > 0.01 and o[1] > 0.01 and abs(b[5] - lb[4]) < 0.05: sup.append(lab)
    print("  ", land[n]["label"], sup or "NOTHING (cavity below, ground at 0)")
