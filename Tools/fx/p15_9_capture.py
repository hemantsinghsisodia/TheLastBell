"""P15-9 workaround: capture poses in PIE Simulate with the camera rain at the capture camera.

In Simulate the world still has PlayerController_0 (no pawn) and its PlayerCameraManager, parked at the start, and
ULBStormFXSubsystem::GetViewLocation prefers that camera manager over the rendered view, so the rain stays at the start.
This driver moves the PIE PlayerController to each pose's camera location (the camera manager follows its view target), waits,
then runs Tools/crypt/capture_session.py for that one pose. PIE Simulate must already be running (Tools/lighting/pie_pp.py start).
The owner must be at the PC with Unreal in front (capture_session rule).

    python -I Tools/fx/p15_9_capture.py <poses.json> <suffix> [--only a,b] [--wait 4]
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import p15_level as P  # noqa: E402

OUT = os.path.join(ROOT, "Docs", "ArtTest", "fx", "p15_9")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("poses")
    ap.add_argument("suffix")
    ap.add_argument("--only", default="")
    ap.add_argument("--wait", type=float, default=4.0)
    a = ap.parse_args()
    poses = json.load(open(a.poses, encoding="utf-8"))
    names = [n for n in a.only.split(",") if n] or list(poses)
    ed = P.Ed()
    if not ed.call(P.L.E, "IsPIERunning", {}):
        raise SystemExit("PIE Simulate is not running")
    pcs = [x for x in ed.find_all(name="PlayerController") if "UEDPIE" in x]
    if len(pcs) != 1:
        raise SystemExit("PIE PlayerController: %d found" % len(pcs))
    pc = pcs[0]
    missing = []
    for n in names:
        x, y, z = poses[n][:3]
        ed.set_xform(pc, (x, y, z), (0, 0, 0), (1, 1, 1))
        got = ed.xform(pc)[0]
        print("%s: controller at %s" % (n, P.rnd(got, 1)), flush=True)
        time.sleep(a.wait)
        r = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "Tools", "crypt", "capture_session.py"), a.poses, OUT, "--prefix", "p15_9_",
                            "--suffix", a.suffix, "--only", n, "--force", "--fg-wait", "180", "--max-wait", "900"],
                           capture_output=True, text=True, cwd=ROOT)
        lines = [l for l in (r.stdout + r.stderr).splitlines() if "saved" in l or "MISSING" in l or "missing" in l]
        print("   ", " | ".join(lines) or ("exit %d" % r.returncode), flush=True)
        if r.returncode != 0:
            missing.append(n)
    print("done; missing:", ",".join(missing) or "none")


if __name__ == "__main__":
    main()
