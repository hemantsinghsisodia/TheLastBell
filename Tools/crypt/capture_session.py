"""P10-8a (D1.26): replaces the lead's scratch wrappers (p10_6e_run_slow.py editor captures, p10_7_run.py PIE Simulate captures plus luma).

Runs one foreground-resilient capture session: waits for the Unreal Editor to be the foreground window, turns the editor CPU throttle off
(in memory only), optionally starts PIE Simulate, runs Tools/crypt/capture_poses.py as a subprocess in attempts, restores everything,
then optionally runs Tools/crypt/luma_report.py as a subprocess. Neither script is imported.

    python Tools/crypt/capture_session.py <poses.json> <out_dir> --prefix P [--suffix S] [--mode simulate|editor]
           [--only a,b] [--force] [--max-wait 3600] [--fg-wait 1800] [--attempts 5] [--timeout 15] [--settle 3]
           [--log-dir DIR] [--luma JSON_OUT] [--plaque POSE] [--dry-run]

Positional: poses.json = {"name": [x, y, z, pitch, yaw], ...}; out_dir gets <prefix><pose><suffix>.png per pose.
Flags (defaults):
    --prefix P      file-name prefix (required).
    --suffix S      file-name suffix before .png ("").
    --mode          simulate (default: PIE Simulate, started and stopped by the session if it was not running) or editor
                    (editor viewport, no PIE; geometry and dressing only, editor sprites show).
    --only a,b      only these poses (default: every pose in the JSON, in file order). An unknown name exits 4.
    --force         also re-capture poses whose PNG already exists (default: they are skipped).
    --max-wait 3600 seconds to wait for the editor to come to the front before the session starts.
    --fg-wait 1800  seconds to wait for the foreground before each attempt.
    --attempts 5    maximum capture_poses.py runs.
    --timeout 15    per-MCP-call socket timeout passed to capture_poses.py (slow first frames of new materials).
    --settle 3      seconds after SetCameraTransform before the first capture, passed to capture_poses.py.
    --log-dir DIR   capture_poses.py logs, cap_<prefix><attempt>.log (default <project>\\Saved\\Logs\\captures).
    --luma JSON_OUT run luma_report.py --json JSON_OUT on every file written in this session and print the end of its output.
    --plaque POSE   run luma_report.py --plaque on that pose's file (if it exists).
    --light-offset F R U  (P14-5) candle proxy: passes --light --light-offset F R U to capture_poses.py; simulate mode only, and
                    TMP_CaptureLight must already exist in the PIE world (Tools/lighting/pie_proxy.py, PIE kept running by the caller).
    --dry-run       print the mode, the remaining poses, the attempt-0 capture_poses.py command line and the luma command lines;
                    exit 0 without importing ue or contacting the editor.

Exit codes: 0 every pose was captured in this session; 1 some are missing (prints "missing: a,b,..."); 2 the editor never became the
foreground window (no captures taken); 3 editor mode and PIE is running (stop it first; nothing was changed); 4 unknown pose name in --only.
Nothing remaining to capture (all skipped) also exits 0.

Safety: the throttle (EditorPerformanceSettings.bThrottleCPUWhenNotForeground) is restored to the value read at the start, and PIE is
stopped only if this session started it, in a finally block. The capture_poses.py circuit breaker (exit code 3) rests 60 s, then
allows one single-pose attempt; a second trip stops the session. The owner must bring Unreal to the front and leave the PC alone
(MCP_NOTES "Bell tower and cloister (P10)" item 1). This tool must not be run by agents without the owner at the PC.
"""
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CRYPT = os.path.join(ROOT, "Tools", "crypt")
CAPTURE_POSES = os.path.join(CRYPT, "capture_poses.py")
LUMA_REPORT = os.path.join(CRYPT, "luma_report.py")

O = "editor_toolset.toolsets.object.ObjectTools"
E = "EditorToolset.EditorAppToolset"
CDO = {"refPath": "/Script/UnrealEd.Default__EditorPerformanceSettings"}
THROTTLE = "bThrottleCPUWhenNotForeground"


def fg_title():
    import ctypes
    u32 = ctypes.windll.user32
    h = u32.GetForegroundWindow()
    n = u32.GetWindowTextLengthW(h)
    b = ctypes.create_unicode_buffer(n + 1)
    u32.GetWindowTextW(h, b, n + 1)
    return b.value


def wait_fg(limit):
    t = time.time()
    while not fg_title().endswith("Unreal Editor"):
        if time.time() - t > limit:
            return False
        time.sleep(2)
    return True


def out_path(out_dir, prefix, name, suffix):
    return os.path.join(out_dir, prefix + name + suffix + ".png")


def captured_this_session(path, t_start):
    return os.path.exists(path) and os.path.getmtime(path) >= t_start


def capture_cmd(args, poses_json, only, attempt, log_dir):
    cmd = [sys.executable, CAPTURE_POSES, poses_json, args.out_dir, "--double", "--raise", "--force",
           "--timeout", str(args.timeout), "--settle", str(args.settle), "--prefix", args.prefix]
    if args.suffix:
        cmd += ["--suffix", args.suffix]
    cmd += ["--only", ",".join(only), "--log", os.path.join(log_dir, "cap_%s%d.log" % (args.prefix, attempt))]
    if args.mode == "editor":
        cmd.append("--editor")
    if getattr(args, "light_offset", None):
        # P14-5: candle proxy (TMP_CaptureLight must already exist in the PIE world: Tools/lighting/pie_proxy.py)
        cmd += ["--light", "--light-offset"] + [str(v) for v in args.light_offset]
    return cmd


def luma_cmds(args, files):
    cmds = []
    if args.luma:
        cmds.append([sys.executable, LUMA_REPORT, "--json", args.luma] + files)
    if args.plaque:
        cmds.append([sys.executable, LUMA_REPORT, "--plaque", out_path(args.out_dir, args.prefix, args.plaque, args.suffix)])
    return cmds


def main():
    ap = argparse.ArgumentParser(description="Foreground-resilient capture session (P10-8a, D1.26). See the module docstring.")
    ap.add_argument("poses_json")
    ap.add_argument("out_dir")
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--suffix", default="")
    ap.add_argument("--mode", choices=["simulate", "editor"], default="simulate")
    ap.add_argument("--only", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--max-wait", type=float, default=3600)
    ap.add_argument("--fg-wait", type=float, default=1800)
    ap.add_argument("--attempts", type=int, default=5)
    ap.add_argument("--timeout", type=float, default=15)
    ap.add_argument("--settle", type=float, default=3)
    ap.add_argument("--log-dir", default=os.path.join(ROOT, "Saved", "Logs", "captures"))
    ap.add_argument("--luma", default="", metavar="JSON_OUT")
    ap.add_argument("--plaque", default="", metavar="POSE")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--light-offset", nargs=3, type=float, default=None, metavar=("F", "R", "U"),
                    help="P14-5: pass --light --light-offset F R U to capture_poses.py (simulate mode; the PIE world needs "
                         "TMP_CaptureLight, see Tools/lighting/pie_proxy.py)")
    args = ap.parse_args()
    if args.light_offset and args.mode != "simulate":
        print("--light-offset needs --mode simulate")
        sys.exit(4)

    # 1. pose list
    t_start = time.time()
    with open(args.poses_json) as f:
        all_poses = list(json.load(f))
    if args.only:
        want = [n for n in args.only.split(",") if n]
        unknown = [n for n in want if n not in all_poses]
        if unknown:
            print("unknown poses in --only: %s" % ", ".join(unknown))
            sys.exit(4)
        names = [n for n in all_poses if n in want]
    else:
        names = all_poses
    poses = []
    for n in names:
        if not args.force and os.path.exists(out_path(args.out_dir, args.prefix, n, args.suffix)):
            print("skipped (exists): %s" % n)
        else:
            poses.append(n)
    if not poses:
        print("nothing to capture: every selected pose already has a file (use --force to re-capture)")
        sys.exit(0)

    # 2. dry run (no ue import, no editor)
    if args.dry_run:
        print("mode: %s" % args.mode)
        print("remaining poses (%d): %s" % (len(poses), ", ".join(poses)))
        print("attempt 0 command: %s" % subprocess.list2cmdline(capture_cmd(args, args.poses_json, poses, 0, args.log_dir)))
        files = [out_path(args.out_dir, args.prefix, n, args.suffix) for n in poses]
        for c in luma_cmds(args, files):
            print("luma command: %s" % subprocess.list2cmdline(c))
        sys.exit(0)

    os.makedirs(args.log_dir, exist_ok=True)

    # 3. foreground
    t0 = time.time()
    if not wait_fg(args.max_wait):
        print("Unreal Editor never became the foreground window (last: %r); no captures taken" % fg_title())
        sys.exit(2)
    print("editor in foreground after %.0f s" % (time.time() - t0), flush=True)
    time.sleep(3)

    sys.path.insert(0, os.path.join(ROOT, "Tools", "mcp"))
    from ue import UE  # lazy: dry-run never reaches this
    ue = UE()

    # 4. editor mode: PIE must not be running
    if args.mode == "editor" and ue.call(E, "IsPIERunning"):
        print("PIE is running; stop it before an editor-mode session")
        sys.exit(3)

    # 5. throttle
    def read_throttle():
        r = ue.call(O, "get_properties", {"instance": CDO, "properties": [THROTTLE]})
        if isinstance(r, str):
            r = json.loads(r)
        return r.get(THROTTLE) if isinstance(r, dict) else r

    original = read_throttle()
    if not isinstance(original, bool):
        print("warning: could not read %s (got %r); will restore True" % (THROTTLE, original))
        original = True
    print("throttle original: %s" % original, flush=True)
    ue.call(O, "set_properties", {"instance": CDO, "values": json.dumps({THROTTLE: False})})

    # 6. session
    started = False
    single = False   # circuit breaker: next attempt is a single-pose test
    try:
        if args.mode == "simulate":
            if not ue.call(E, "IsPIERunning"):
                ue.call(E, "StartPIE", {"options": {"bSimulate": True, "playMode": "PlayMode_InViewPort", "warmupSeconds": 5}})
                started = True
            t = time.time()
            while not ue.call(E, "IsPIERunning"):
                if time.time() - t > 120:
                    raise RuntimeError("PIE Simulate did not start")
                time.sleep(2)
            print("PIE Simulate running", flush=True)
            time.sleep(8)
        for attempt in range(args.attempts):
            paths = {n: out_path(args.out_dir, args.prefix, n, args.suffix) for n in poses}
            remaining = [n for n in poses if not captured_this_session(paths[n], t_start)]
            if not remaining:
                break
            if not wait_fg(args.fg_wait):
                print("lost the foreground for %.0f s; stopping" % args.fg_wait, flush=True)
                break
            time.sleep(3)
            only = remaining[:1] if single else remaining
            r = subprocess.run(capture_cmd(args, args.poses_json, only, attempt, args.log_dir),
                               cwd=ROOT, capture_output=True, text=True)
            lines = [ln for ln in r.stdout.splitlines()
                     if any(k in ln.lower() for k in ("saved", "missing", "finished", "abort"))]
            if lines:
                print("\n".join(lines[-60:]), flush=True)
            else:
                print((r.stdout[-800:] + r.stderr[-800:]), flush=True)
            if r.returncode == 3:
                if single:
                    print("breaker tripped twice; stopping", flush=True)
                    break
                print("breaker tripped; resting 60 s", flush=True)
                time.sleep(60)
                single = True
                continue
            if single:
                if captured_this_session(paths[only[0]], t_start):
                    single = False
                else:
                    print("breaker tripped twice; stopping", flush=True)
                    break
    finally:
        try:
            if started and ue.call(E, "IsPIERunning"):
                ue.call(E, "StopPIE")
                print("PIE stopped", flush=True)
        except Exception as e:
            print("StopPIE error:", e, flush=True)
        try:
            ue.call(O, "set_properties", {"instance": CDO, "values": json.dumps({THROTTLE: original})})
            print("throttle restored (original %s): %s" % (original, ue.call(O, "get_properties", {"instance": CDO, "properties": [THROTTLE]})))
        except Exception as e:
            print("throttle restore error:", e, flush=True)

    # 7. luma
    written = [out_path(args.out_dir, args.prefix, n, args.suffix) for n in poses]
    written = [p for p in written if captured_this_session(p, t_start)]
    if args.luma and written:
        cmds = luma_cmds(argparse.Namespace(luma=args.luma, plaque="", out_dir=args.out_dir, prefix=args.prefix, suffix=args.suffix), written)
        r = subprocess.run(cmds[0], cwd=ROOT, capture_output=True, text=True)
        print(r.stdout[-6000:], r.stderr[-1000:], flush=True)
    if args.plaque:
        pf = out_path(args.out_dir, args.prefix, args.plaque, args.suffix)
        if os.path.exists(pf):
            r = subprocess.run([sys.executable, LUMA_REPORT, "--plaque", pf], cwd=ROOT, capture_output=True, text=True)
            print("PLAQUE:", r.stdout[-1500:], r.stderr[-500:], flush=True)

    # 8. exit code
    missing = [n for n in poses if not captured_this_session(out_path(args.out_dir, args.prefix, n, args.suffix), t_start)]
    if missing:
        print("missing: %s" % ",".join(missing))
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
