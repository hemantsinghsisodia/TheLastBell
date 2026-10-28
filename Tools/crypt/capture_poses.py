"""P9-5 / P9-7 capture helper (editor open, PIE Simulate running).

    python capture_poses.py <poses.json> <out_dir> [--light] [--light-offset F R U] [--prefix p9s_] [--suffix _c]
                            [--only a,b] [--log file] [--force] [--editor] [--double] [--raise] [--timeout N]

--editor: capture the editor viewport (no PIE needed; ~0.3 s per capture, reliable; editor helper icons/volume wireframes show).
          PIE Simulate captures run at ~3 fps and mostly time out unless EditorPerformanceSettings.bThrottleCPUWhenNotForeground
          is false (in memory only) AND the editor window is not minimised/covered (see --raise).
--timeout N: socket timeout in seconds per MCP call (default 60); use ~4 to fail fast on the ~19 s CaptureViewport resets.
--double: take two captures per pose and keep the second (stale occlusion after SetCameraTransform).
--raise (P9-7 D1.14 0a): while a pose is captured, a daemon thread runs every 0.2 s over the visible top-level windows whose
          title ends with "Unreal Editor": an iconic window gets ShowWindow(SW_SHOWNOACTIVATE = 4), then
          SetWindowPos(h, HWND_TOP, 0,0,0,0, SWP_NOSIZE|SWP_NOMOVE|SWP_NOACTIVATE = 0x13). It never activates/focuses the editor.
--light: move the temp light `TMP_CaptureLight` (PIE world only) with the camera. Without --light-offset it sits at the camera.
--light-offset F R U: the light goes to camera + F*forward + R*right + U*up (camera yaw/pitch; UE axes: forward = (cp cy, cp sy, sp),
          right = (-sy, cy, 0), up = (-sp cy, -sp sy, cp)). The P9-7 candle proxy uses `--light-offset 36 14 -10`.
--suffix S: appended to the file name (before .png), e.g. _c for the candle proxy variant.
--only a,b: capture only these pose names.
--settle S: seconds to wait after SetCameraTransform before the first capture (default 0.8).
Circuit breaker (P9-7, after the PC crash): if 2 consecutive poses fail all their tries the whole run aborts (exit code 3) after a
cheap editor check (get_current_level, IsPIERunning, window iconic/visible). Do not continue; wait 60 s and make at most ONE more
single-pose test; if that fails too, stop and report with the log.
Retry cap (P9-7): at most MAX_TRIES (6) failed attempts per pose, in one pass. A pose that is still missing is logged as MISSING
and not retried. The temp light is searched in the PIE world only (a refPath containing "UEDPIE"); the script never spawns it.

poses.json: {"name": [x, y, z, pitch, yaw], ...}. Per pose: optional temp light moved, camera set, one or two captures taken (second
kept), PNG written to <out_dir>/<prefix><name><suffix>.png. Poses whose PNG already exists are skipped (unless --force).
One progress line per pose goes to the log file.
"""
import base64
import ctypes
import json
import math
import os
import sys
import threading
import time
import urllib.request
from ctypes import wintypes

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mcp"))
import ue as ue_mod  # noqa: E402
from ue import UE  # noqa: E402

_orig_urlopen = urllib.request.urlopen


TIMEOUT = [60]   # --timeout N: socket timeout per MCP call (a successful capture returns in ~0.3 s, a failing one is closed by the server after ~19 s)
MAX_TRIES = 6    # P9-7 D1.14 0a: failed attempts allowed per pose in one pass


def _urlopen(req, timeout=None):
    return _orig_urlopen(req, timeout=TIMEOUT[0])


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


class Raiser:
    """Keeps the (non-activating) editor window(s) un-minimised and on top while a pose is captured (D1.14 0a)."""

    def __init__(self):
        self.stop = threading.Event()
        self.th = None
        self.u32 = ctypes.windll.user32
        self.was_iconic = set()   # editor windows that were minimised when the run started: re-minimised at the end (SW_SHOWMINNOACTIVE = 7)

    def _windows(self):
        u32, hw = self.u32, []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def cb(h, _l):
            n = u32.GetWindowTextLengthW(h)
            if n and u32.IsWindowVisible(h):
                b = ctypes.create_unicode_buffer(n + 1)
                u32.GetWindowTextW(h, b, n + 1)
                if b.value.endswith("Unreal Editor"):
                    hw.append(h)
            return True

        u32.EnumWindows(cb, 0)
        return hw

    def _run(self):
        hw = self._windows()
        while not self.stop.is_set():
            for h in hw:
                if self.u32.IsIconic(h):
                    self.u32.ShowWindow(h, 4)                       # SW_SHOWNOACTIVATE
                self.u32.SetWindowPos(h, 0, 0, 0, 0, 0, 0x13)       # HWND_TOP, NOSIZE|NOMOVE|NOACTIVATE
            self.stop.wait(0.2)

    def start(self):
        if self.th and self.th.is_alive():
            return
        self.was_iconic = {h for h in self._windows() if self.u32.IsIconic(h)}
        self.stop.clear()
        self.th = threading.Thread(target=self._run, daemon=True)
        self.th.start()

    def end(self, final=False):
        """final=True: stop and re-minimise the windows that were minimised at the start (owner's desktop left as it was)."""
        self.stop.set()
        if self.th:
            self.th.join(1.0)
            self.th = None
        if final:
            for h in self.was_iconic:
                self.u32.ShowWindow(h, 7)


def call(ts, tool, args=None, tries=3):
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


def light_pos(x, y, z, pitch, yaw, off):
    f, r, u = off
    cp, sp, cy, sy = math.cos(math.radians(pitch)), math.sin(math.radians(pitch)), math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    fwd = (cp * cy, cp * sy, sp)
    right = (-sy, cy, 0.0)
    up = (-sp * cy, -sp * sy, cp)
    return {"x": x + f * fwd[0] + r * right[0] + u * up[0],
            "y": y + f * fwd[1] + r * right[1] + u * up[1],
            "z": z + f * fwd[2] + r * right[2] + u * up[2]}


def find_pie_light():
    found = call(S, "find_actors", {"name": "TMP_CaptureLight", "tag": "", "collision_channels": []}) or []
    pie = [a for a in found if "UEDPIE" in a.get("refPath", "")]
    return pie[0] if pie else None


def editor_check(raiser):
    try:
        _UE[0] = None
        log("  check: level %s, PIE running %s" % (call(S, "get_current_level", tries=1), call(E, "IsPIERunning", tries=1)))
    except Exception as e:
        log("  check: MCP calls failing: %s" % str(e)[:100])
    try:
        u32 = ctypes.windll.user32
        r = raiser or Raiser()
        rects = {}
        for h in r._windows():
            rc = wintypes.RECT()
            u32.GetWindowRect(h, ctypes.byref(rc))
            rects[h] = (rc.left, rc.top, rc.right, rc.bottom)
            log("  check: editor window %s iconic=%s rect=%s" % (h, bool(u32.IsIconic(h)), rects[h]))
        # any visible WS_EX_TOPMOST window (not the editor) overlapping an editor rect?
        found = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def cb(h, _l):
            if h in rects or not u32.IsWindowVisible(h) or u32.IsIconic(h):
                return True
            if u32.GetWindowLongW(h, -20) & 0x8:   # GWL_EXSTYLE & WS_EX_TOPMOST
                rc = wintypes.RECT()
                u32.GetWindowRect(h, ctypes.byref(rc))
                for e in rects.values():
                    if rc.left < e[2] and rc.right > e[0] and rc.top < e[3] and rc.bottom > e[1] and (rc.right - rc.left) > 50 and (rc.bottom - rc.top) > 50:
                        n = u32.GetWindowTextLengthW(h)
                        b = ctypes.create_unicode_buffer(n + 1)
                        u32.GetWindowTextW(h, b, n + 1)
                        found.append("%s '%s' %s" % (h, b.value, (rc.left, rc.top, rc.right, rc.bottom)))
                        break
            return True

        u32.EnumWindows(cb, 0)
        log("  check: topmost windows over the editor rect: %s" % (found or "none"))
    except Exception as e:
        log("  check: window query failed %s" % e)


def main():
    argv = sys.argv
    poses = json.load(open(argv[1]))
    out = argv[2]
    use_light = "--light" in argv or "--light-offset" in argv
    force = "--force" in argv
    prefix = argv[argv.index("--prefix") + 1] if "--prefix" in argv else ""
    suffix = argv[argv.index("--suffix") + 1] if "--suffix" in argv else ""
    off = (0.0, 0.0, 0.0)
    if "--light-offset" in argv:
        i = argv.index("--light-offset")
        off = tuple(float(v) for v in argv[i + 1:i + 4])
    if "--only" in argv:
        keep = set(argv[argv.index("--only") + 1].split(","))
        poses = {k: v for k, v in poses.items() if k in keep}
    if "--timeout" in argv:
        TIMEOUT[0] = float(argv[argv.index("--timeout") + 1])
    if "--log" in argv:
        LOG[0] = argv[argv.index("--log") + 1]
    raiser = Raiser() if "--raise" in argv else None
    os.makedirs(out, exist_ok=True)
    if "--editor" not in argv and not call(E, "IsPIERunning"):
        sys.exit("PIE Simulate is not running")
    light = None
    if use_light:
        light = find_pie_light()
        if not light:
            sys.exit("TMP_CaptureLight not found in the PIE world (refPath must contain UEDPIE)")
    settle = float(argv[argv.index("--settle") + 1]) if "--settle" in argv else 0.8
    done = failed = 0
    consec = 0
    if raiser:
        raiser.start()   # runs for the WHOLE run (every capture call and every retry), stopped and re-minimised at the end
    for name, (x, y, z, pitch, yaw) in poses.items():
        path = os.path.join(out, prefix + name + suffix + ".png")
        if os.path.exists(path) and not force:
            log("skip %s (exists)" % name)
            continue
        t0 = time.time()
        fails = 0
        r = None
        want = 2 if "--double" in argv else 1
        got = 0
        xf = {"location": {"x": x, "y": y, "z": z}, "rotation": {"pitch": pitch, "yaw": yaw, "roll": 0},
              "scale": {"x": 1, "y": 1, "z": 1}}
        try:
            while got < want and fails < MAX_TRIES:
                try:
                    if light:
                        call(A, "set_actor_transform", {"actor": light, "xform": {"location": light_pos(x, y, z, pitch, yaw, off),
                             "rotation": {"pitch": 0, "yaw": 0, "roll": 0}, "scale": {"x": 1, "y": 1, "z": 1}}, "worldspace": True}, tries=1)
                    call(E, "SetCameraTransform", {"transform": xf}, tries=1)
                    time.sleep(settle if got == 0 else 0.5)
                    r = call(E, "CaptureViewport", {"captureTransform": None, "annotations": None}, tries=1)
                    got += 1
                except Exception as e:
                    fails += 1
                    _UE[0] = None
                    log("  attempt failed %d/%d %s: %s" % (fails, MAX_TRIES, name, str(e)[:100]))
                    time.sleep(1)
            if got >= want and r is not None:
                with open(path, "wb") as f:
                    f.write(base64.b64decode(r["image"]["data"]))
                done += 1
                consec = 0
                log("saved %s (%.0fs, %d failed attempts)" % (name, time.time() - t0, fails))
            else:
                failed += 1
                consec += 1
                log("MISSING %s: %d failed attempts (cap %d), not retried" % (name, fails, MAX_TRIES))
                if consec >= 2:
                    log("CIRCUIT BREAKER: 2 consecutive poses failed all tries; aborting the run")
                    editor_check(raiser)
                    if raiser:
                        raiser.end(final=True)
                    sys.exit(3)
        finally:
            pass
    if raiser:
        raiser.end(final=True)
    log("finished: %d saved, %d missing" % (done, failed))


if __name__ == "__main__":
    main()
