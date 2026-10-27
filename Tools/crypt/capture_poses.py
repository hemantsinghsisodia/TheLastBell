"""P9-5 capture helper (editor open, PIE Simulate running).

    python capture_poses.py <poses.json> <out_dir> [--light] [--prefix p9s_] [--log file] [--force] [--editor] [--double]

--editor: capture the editor viewport (no PIE needed; ~0.3 s per capture, reliable; editor helper icons/volume wireframes show).
          PIE Simulate captures run at ~3 fps and mostly time out (P9-6a note below).
--double: take two captures per pose and keep the second (stale occlusion after SetCameraTransform).

poses.json: {"name": [x, y, z, pitch, yaw], ...}. Per pose: optional temp light moved to the camera (the light actor
`TMP_CaptureLight` must exist in the editor world BEFORE StartPIE; it is found in the PIE copy), camera set,
two captures taken (second kept), PNG written to <out_dir>/<prefix><name>.png. Poses whose PNG already exists are skipped
(unless --force). Every MCP call has a 60 s socket timeout and up to 3 retries (5 s wait, new session); a pose that still
fails is logged and skipped. One progress line per pose goes to the log file.
"""
import base64
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mcp"))
import ue as ue_mod  # noqa: E402
from ue import UE  # noqa: E402

_orig_urlopen = urllib.request.urlopen


def _urlopen(req, timeout=None):
    return _orig_urlopen(req, timeout=60)


ue_mod.urllib.request.urlopen = _urlopen

E = "EditorToolset.EditorAppToolset"
S = "editor_toolset.toolsets.scene.SceneTools"
A = "editor_toolset.toolsets.actor.ActorTools"
_UE = [None]
LOG = [None]


def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    if LOG[0]:
        with open(LOG[0], "a") as f:
            f.write(line + "\n")


def call(ts, tool, args=None, tries=6):
    for k in range(tries):
        try:
            if _UE[0] is None:
                _UE[0] = UE()
            return _UE[0].call(ts, tool, args)
        except Exception as e:
            _UE[0] = None
            log("  retry %d %s: %s" % (k + 1, tool, str(e)[:90]))
            if k == tries - 1:
                raise
            time.sleep(1)


def main():
    poses = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    use_light = "--light" in sys.argv
    force = "--force" in sys.argv
    prefix = sys.argv[sys.argv.index("--prefix") + 1] if "--prefix" in sys.argv else ""
    if "--log" in sys.argv:
        LOG[0] = sys.argv[sys.argv.index("--log") + 1]
    os.makedirs(out, exist_ok=True)
    if "--editor" not in sys.argv and not call(E, "IsPIERunning"):
        sys.exit("PIE Simulate is not running")
    light = None
    if use_light:
        found = call(S, "find_actors", {"name": "TMP_CaptureLight", "tag": "", "collision_channels": []})
        if not found:
            sys.exit("TMP_CaptureLight not found in the PIE world")
        light = found[0]
    done = failed = 0
    for name, (x, y, z, pitch, yaw) in poses.items():
        path = os.path.join(out, prefix + name + ".png")
        if os.path.exists(path) and not force:
            log("skip %s (exists)" % name)
            continue
        t0 = time.time()
        try:
            xf = {"location": {"x": x, "y": y, "z": z}, "rotation": {"pitch": pitch, "yaw": yaw, "roll": 0},
                  "scale": {"x": 1, "y": 1, "z": 1}}
            if light:
                call(A, "set_actor_transform", {"actor": light, "xform": {"location": xf["location"],
                     "rotation": {"pitch": 0, "yaw": 0, "roll": 0}, "scale": {"x": 1, "y": 1, "z": 1}}, "worldspace": True})
            call(S, "get_current_level")  # cheap keep-alive
            call(E, "SetCameraTransform", {"transform": xf})
            time.sleep(0.8)
            # CaptureViewport fails (reset after ~19.6 s) on 2 of every 3 calls; the failed calls still render the frame, so
            # the one that succeeds is never the stale first frame. Take that one.
            r = call(E, "CaptureViewport", {"captureTransform": None, "annotations": None})
            if "--double" in sys.argv:
                time.sleep(0.5)
                r = call(E, "CaptureViewport", {"captureTransform": None, "annotations": None})
            with open(path, "wb") as f:
                f.write(base64.b64decode(r["image"]["data"]))
            done += 1
            log("saved %s (%.0fs)" % (name, time.time() - t0))
        except Exception as e:
            failed += 1
            log("FAILED %s: %s" % (name, str(e)[:120]))
    log("finished: %d saved, %d failed" % (done, failed))


if __name__ == "__main__":
    main()
