"""P10-2 item 5 (offline): project the tower AABB (X 12000..13000, Y 1500..2500, Z 0..3540) into each survey pose (hFOV 90, 1334x812 capture)
to give the screen coverage the tower WOULD have with nothing in front of it, and which faces face the camera."""
import json, math
poses = json.load(open(r"C:\Hemant\Prj\Learning\TheLastBell\Tools\belltower\poses\p10_survey_poses.json"))
W, H = 1334, 812
f = (W / 2) / math.tan(math.radians(45))
box = (12000, 13000, 1500, 2500, 0, 3540)
def proj(p, cam):
    x, y, z, pitch, yaw = cam
    cp, sp, cy, sy = math.cos(math.radians(pitch)), math.sin(math.radians(pitch)), math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    fwd = (cp * cy, cp * sy, sp); right = (-sy, cy, 0); up = (-sp * cy, -sp * sy, cp)
    v = (p[0] - x, p[1] - y, p[2] - z)
    df = sum(a * b for a, b in zip(v, fwd))
    if df <= 1: return None
    return (W / 2 + f * sum(a * b for a, b in zip(v, right)) / df, H / 2 - f * sum(a * b for a, b in zip(v, up)) / df)
def clipped(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0, x1, y0, y1 = max(0, min(xs)), min(W, max(xs)), max(0, min(ys)), min(H, max(ys))
    return (x0, x1, y0, y1) if x1 > x0 and y1 > y0 else None
rows = []
for n, cam in poses.items():
    x, y, z = cam[:3]
    pts = []
    ok = True
    for X in box[0:2]:
        for Y in box[2:4]:
            for Z in box[4:6]:
                q = proj((X, Y, Z), cam)
                if q is None: ok = False
                else: pts.append(q)
    faces = []
    if x < box[0]: faces.append("W (-X)")
    if x > box[1]: faces.append("E")
    if y < box[2]: faces.append("S (-Y)")
    if y > box[3]: faces.append("N (+Y)")
    # roof visible if camera above 3540
    if z > 3540: faces.append("roof")
    c = clipped(pts) if ok and len(pts) == 8 else None
    if c:
        w = (c[1] - c[0]) / W * 100; h = (c[3] - c[2]) / H * 100; area = (c[1] - c[0]) * (c[3] - c[2]) / (W * H) * 100
        rows.append((n, "%.1f%% x %.1f%%" % (w, h), "%.1f%%" % area, "x %d..%d, y %d..%d" % c, ", ".join(faces)))
    else:
        # partially behind camera or off-screen
        rows.append((n, "off-screen / not in front", "0", "-", ", ".join(faces)))
print("| Pose | Tower bbox width x height (% of frame) | Bbox area | Screen box px | Faces facing the camera |")
print("|---|---|---|---|---|")
for r in rows: print("| %s | %s | %s | %s | %s |" % r)
