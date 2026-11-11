# P18-S1: encode the menu-drift PNG sequence (Tools\cine\p18_render_menu_drift.ps1) into Content\Movies\LB_MenuDrift.mp4 with ffmpeg.
# H.264 (libx264) High profile, CRF 18, 30 fps, yuv420p, BT.709, +faststart, no audio. 1920x1080, 1200 frames = 40.000 s.
#
#   powershell -ExecutionPolicy Bypass -File Tools\cine\p18_encode_menu_drift.ps1            # Saved\MovieRenders\MenuDrift\*.png -> Content\Movies\LB_MenuDrift.mp4
#   powershell -ExecutionPolicy Bypass -File Tools\cine\p18_encode_menu_drift.ps1 -Test      # Saved\MovieRenders\MenuDrift_test\*.png -> Saved\MovieRenders\LB_MenuDrift_test.mp4 (nothing in Content)
#
# The frame sequence must be contiguous from 0000 (the check below stops otherwise). Loop: frame 1199 is one step before the pose of frame 0 (the camera path is mirrored about 20 s
# with flat tangents at 0, 20 and 40 s), so played in a loop the picture continues with no step in the camera. Rain and clouds are not looped (they are stochastic); at the
# camera speed (at most 30 cm/s) and 40 s length that is not noticeable, but a lightning flash that straddles the join would be: look at the first and last second.
param(
    [switch]$Test,
    [string]$Dir = "",
    [string]$Out = ""
)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { throw "ffmpeg is not on PATH." }
if ($Dir -eq "") { $Dir = Join-Path $root ("Saved\MovieRenders\" + $(if ($Test) { "MenuDrift_test" } else { "MenuDrift" })) }
if ($Out -eq "") { $Out = if ($Test) { Join-Path $root "Saved\MovieRenders\LB_MenuDrift_test.mp4" } else { Join-Path $root "Content\Movies\LB_MenuDrift.mp4" } }
if (-not (Test-Path $Dir)) { throw "no frame folder: $Dir (run Tools\cine\p18_render_menu_drift.ps1 first)" }

$files = Get-ChildItem $Dir -Filter *.png | Sort-Object Name
if ($files.Count -eq 0) { throw "no PNG files in $Dir" }
# name pattern: <prefix><digits>.png, e.g. LS_LB_MenuDrift.0000.png
if ($files[0].Name -notmatch '^(.*?)(\d+)\.png$') { throw "cannot read the frame number in $($files[0].Name)" }
$prefix = $Matches[1]; $pad = $Matches[2].Length; $first = [int]$Matches[2]
$last = 0
if ($files[-1].Name -match '^(.*?)(\d+)\.png$') { $last = [int]$Matches[2] }
Write-Host ("{0} frames, {1} .. {2}, pattern {3}%0{4}d.png" -f $files.Count, $first, $last, $prefix, $pad)
if ($first -ne 0) { throw "the sequence starts at frame $first, not 0" }
if (($last - $first + 1) -ne $files.Count) { throw "the sequence has gaps ($($files.Count) files for frames $first..$last)" }
if ($files.Count -gt 1 -and (($files | Select-Object -ExpandProperty Length -Unique | Measure-Object).Count -eq 1)) { throw "every PNG has the same size ($($files[0].Length) bytes): the frames are blank (black). Not encoding." }
$expected = if ($Test) { $files.Count } else { 1200 }
if ($files.Count -ne $expected) { throw "expected $expected frames, found $($files.Count) (use -Test for a partial run)" }

New-Item -ItemType Directory -Force -Path (Split-Path $Out) | Out-Null
$pattern = Join-Path $Dir ($prefix + "%0" + $pad + "d.png")
$vf = "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p"
& ffmpeg -y -hide_banner -loglevel warning -framerate 30 -start_number 0 -i $pattern `
    -vf $vf -c:v libx264 -preset slow -crf 18 -profile:v high -level 4.1 -pix_fmt yuv420p `
    -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv `
    -r 30 -g 30 -movflags +faststart -an $Out
if ($LASTEXITCODE -ne 0) { throw "ffmpeg failed ($LASTEXITCODE)" }

# verify
$probe = & ffprobe -v error -select_streams v:0 -count_frames -show_entries stream=codec_name,profile,pix_fmt,width,height,r_frame_rate,nb_read_frames,duration -of default=nw=1 $Out
$probe | ForEach-Object { Write-Host $_ }
$size = (Get-Item $Out).Length
Write-Host ("{0}: {1:N1} MB" -f $Out, ($size / 1MB))
$txt = $probe -join "`n"
if ($txt -notmatch "nb_read_frames=$($files.Count)") { Write-Warning "the encoded frame count differs from the PNG count" }
