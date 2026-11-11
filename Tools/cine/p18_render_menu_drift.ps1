# P18-S1: render LS_LB_MenuDrift (L_Monastery) with Movie Render Queue from the command line: a 1920x1080 PNG sequence in Saved\MovieRenders\MenuDrift\.
#
# THIS OPENS A GAME WINDOW (UnrealEditor-Cmd -game -windowed) and loads the GPU for several minutes. Run it only with the owner present and the editor CLOSED.
#
#   powershell -ExecutionPolicy Bypass -File Tools\cine\p18_render_menu_drift.ps1            # the full 1200 frames (40 s at 30 fps)
#   powershell -ExecutionPolicy Bypass -File Tools\cine\p18_render_menu_drift.ps1 -Test      # first 90 frames (3 s) into Saved\MovieRenders\MenuDrift_test\: look at them first
#   -Temporal 4      temporal samples per frame (default 1 = TSR; 4 or more = AA method None + accumulation: slower, smoother)
#   -Cinematic       the engine's cinematic quality overrides (sg.*=4, view distance 50, shadow distance 10): heavier; the dev GPU has 6 GB
#   -ManifestOnly    write the queue manifest and stop (no window, no render)
#
# What it does:
#  1. refuses to run while UnrealEditor is running;
#  2. writes the queue manifest Saved\MovieRenderPipeline\QueueManifest.utxt with Tools\cine\p18_mrq_manifest.py (headless, -nullrhi; the Movie Render Queue plugin is not
#     enabled in the .uproject, so it is enabled for these two processes only with -EnablePlugins=MovieRenderPipeline: no project file changes);
#  3. launches the render exactly as the editor's own "new process" executor does (Engine\Plugins\MovieScene\MovieRenderPipeline\...\MoviePipelineNewProcessExecutor.cpp):
#     -game, -windowed, -MoviePipelineConfig=<manifest>, the MoviePipelineGameMode (no pawn, no HUD, none of the project's gameplay). The first map is /Engine/Maps/Entry (the
#     editor passes a map name that does not exist, which falls back to the project's default map, L_MainMenu); the executor then loads the job's map, L_Monastery;
#  4. waits, then counts the PNGs and prints the time per frame.
# Then run Tools\cine\p18_encode_menu_drift.ps1. Nothing here is committed: the frames and the manifest are under Saved\ (git-ignored).
param(
    [switch]$Test,
    [int]$TestFrames = 90,
    [int]$Temporal = 1,
    [switch]$Cinematic,
    [switch]$ManifestOnly
)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$ue = "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
$proj = Join-Path $root "TheLastBell.uproject"
$logs = Join-Path $root "Saved\Logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null

if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) { throw "UnrealEditor is running: close it first (the render needs the project and the GPU to itself)." }
if (Get-Process UnrealEditor-Cmd -ErrorAction SilentlyContinue) { throw "UnrealEditor-Cmd is running: wait for it to finish." }
if (-not (Test-Path $ue)) { throw "not found: $ue" }
if (-not (Test-Path (Join-Path $root "Content\LastBell\Cinematics\LS_LB_MenuDrift.uasset"))) { throw "LS_LB_MenuDrift.uasset is missing (Tools\cine\p18_menu_drift.py builds it)." }

$outName = if ($Test) { "MenuDrift_test" } else { "MenuDrift" }
$outDir = Join-Path $root ("Saved\MovieRenders\" + $outName)
$expected = if ($Test) { $TestFrames } else { 1200 }
if (Test-Path $outDir) { Get-ChildItem $outDir -Filter *.png -ErrorAction SilentlyContinue | Remove-Item -Force }   # only this script's own output folder
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

# --- 2. the manifest
$env:P18_MRQ_OUT = $outDir
$env:P18_MRQ_END_FRAME = if ($Test) { "$TestFrames" } else { "0" }
$env:P18_MRQ_TEMPORAL = "$Temporal"
$env:P18_MRQ_CINEMATIC = if ($Cinematic) { "1" } else { "0" }
$mlog = Join-Path $logs "p18_mrq_manifest.log"
$script = Join-Path $root "Tools\cine\p18_mrq_manifest.py"
Write-Host "[1/2] writing the queue manifest ($mlog)"
$p = Start-Process -FilePath $ue -ArgumentList @("`"$proj`"", "-run=pythonscript", "-script=`"$script`"", "-EnablePlugins=MovieRenderPipeline", "-unattended", "-nullrhi", "-nosplash", "-nosound", "-NoP4", "-log", "-abslog=`"$mlog`"") -Wait -PassThru -WindowStyle Hidden
$done = Select-String -Path $mlog -Pattern "P18Mrq: DONE (\d+) settings applied, (\d+) errors" | Select-Object -Last 1
if (-not $done) { throw "the manifest step did not finish; read $mlog" }
Write-Host $done.Line.Substring($done.Line.IndexOf("P18Mrq"))
if ($done.Matches[0].Groups[2].Value -ne "0") { throw "the manifest step reported errors; read Saved\MovieRenderPipeline\p18_manifest_report.json" }
if (-not (Test-Path (Join-Path $root "Saved\MovieRenderPipeline\QueueManifest.utxt"))) { throw "no manifest written" }
if ($ManifestOnly) { Write-Host "manifest only: done."; exit 0 }

# --- 3. the render
$rlog = Join-Path $logs "p18_menu_render.log"
$ueArgs = @(
    "`"$proj`"",
    "/Engine/Maps/Entry?game=/Script/MovieRenderPipelineCore.MoviePipelineGameMode",
    "-game", "-windowed", "-ResX=1920", "-ResY=1080", "-nohmd", "-NoLoadingScreen", "-nosplash", "-nosound", "-NoP4", "-unattended",
    "-EnablePlugins=MovieRenderPipeline",
    # The project's cinematic subsystem plays LS_LB_Intro on the first tick of L_Monastery ("New Game") and starts with a black camera fade, which made the first test render black.
    # lb.Cine.Enabled 0 must be in force before the map's BeginPlay, hence the device-profile CVar (applied at start-up) and ExecCmds (run before the executor loads the map).
    "-dpcvars=lb.Cine.Enabled=0",
    "-ExecCmds=`"lb.Cine.Enabled 0`"",
    "-MoviePipelineConfig=`"MovieRenderPipeline/QueueManifest.utxt`"",
    "-forcelogflush", "-log", "-abslog=`"$rlog`""
)
Write-Host "[2/2] rendering $expected frames into $outDir (log: $rlog)"
Write-Host ("      " + $ue + " " + ($ueArgs -join " "))
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$p = Start-Process -FilePath $ue -ArgumentList $ueArgs -PassThru
while (-not $p.HasExited) {
    Start-Sleep -Seconds 15
    $n = (Get-ChildItem $outDir -Filter *.png -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host ("      {0:mm\:ss}  {1}/{2} frames" -f $sw.Elapsed, $n, $expected)
}
$p.WaitForExit()
$sw.Stop()
$n = (Get-ChildItem $outDir -Filter *.png -ErrorAction SilentlyContinue | Measure-Object).Count
Write-Host ("exit code {0}; {1} PNG files in {2}; {3:mm\:ss} elapsed" -f $p.ExitCode, $n, $outDir, $sw.Elapsed)
if ($n -gt 0) { Write-Host ("about {0:N2} s per frame including start-up" -f ($sw.Elapsed.TotalSeconds / $n)) }
# --- checks on the log and the frames
$bad = $false
if (Test-Path $rlog) {
    $cine = Select-String -CaseSensitive -Path $rlog -Pattern "LogLB: Cine: (play |.* will start)" | Select-Object -First 3
    if ($cine) { Write-Warning "the project's cinematic subsystem started a cinematic during the render (black fade, wrong camera): lb.Cine.Enabled 0 did not take effect."; $cine | ForEach-Object { Write-Warning $_.Line }; $bad = $true }
    $crash = Select-String -Path $rlog -Pattern "Critical error|Unhandled Exception" | Select-Object -First 1
    if ($crash) { Write-Warning ("the render process crashed: " + $crash.Line + " (if all frames are on disk this may be a shutdown crash, see Docs\ArtTest\cine\p18_menu_drift.md)") }
}
$pngs = Get-ChildItem $outDir -Filter *.png -ErrorAction SilentlyContinue
if ($pngs.Count -gt 1 -and (($pngs | Select-Object -ExpandProperty Length -Unique | Measure-Object).Count -eq 1)) { Write-Warning "every PNG has the same size ($($pngs[0].Length) bytes): the frames are blank (black)."; $bad = $true }
if ($n -ne $expected) { Write-Warning "expected $expected frames, found $n. Read $rlog (look for LogMovieRenderPipeline lines and errors)." ; exit 2 }
$next = "Tools\cine\p18_encode_menu_drift.ps1"
if ($Test) { $next += " -Test" }
if ($bad) { exit 3 }
Write-Host "done. Next: $next"
