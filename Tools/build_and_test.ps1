# Build the editor target and run all LastBell automation tests on the real project.
# Requires the Unreal Editor to be CLOSED (Live Coding / DLL lock). Usage: powershell -ExecutionPolicy Bypass -File Tools\build_and_test.ps1
$ErrorActionPreference = "Continue"
$proj = "C:\Hemant\Prj\Learning\TheLastBell\TheLastBell.uproject"
$ue = "C:\Program Files\Epic Games\UE_5.8"
$t = 0
while ((Get-Process UnrealEditor -ErrorAction SilentlyContinue) -and $t -lt 120) { Start-Sleep 5; $t += 5 }
if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) { "EDITOR STILL RUNNING - abort"; exit 1 }
"== branch: " + (git -C (Split-Path $proj) branch --show-current)
& "$ue\Engine\Build\BatchFiles\Build.bat" TheLastBellEditor Win64 Development "-Project=$proj" -WaitMutex -NoHotReloadFromIDE *> "$env:TEMP\lb_build.log"
"build exit=$LASTEXITCODE"
Select-String -Path "$env:TEMP\lb_build.log" -Pattern "error|warning C|Result:" | Select-Object -Last 6 | ForEach-Object { $_.Line }
if ($LASTEXITCODE -ne 0) { exit 2 }
$l = Join-Path (Split-Path $proj) "Saved\Logs\LBTests_All.log"
$p = Start-Process -FilePath "$ue\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" -ArgumentList @($proj, '-ExecCmds="Automation RunTests LastBell; Quit"', '-unattended', '-nullrhi', '-nosplash', '-nosound', '-NoP4', '-log', "-abslog=$l") -Wait -PassThru
(Select-String -Path $l -Pattern "Result=\{Success\}").Count.ToString() + " tests passed"
Select-String -Path $l -Pattern "Result=\{Fail" | ForEach-Object { "FAIL: " + ($_.Line -replace '^.*Name=', '') }
"invalid tags: " + (Select-String -Path $l -Pattern "Invalid GameplayTag").Count
Select-String -Path $l -Pattern "very large delta" | ForEach-Object { "STALL: " + $_.Line }
