# Sync Source/Config/.uproject into the mirror C:\lbb (Content is a junction), build there, run all LastBell tests.
# Safe while the editor is open on the real project. Usage: powershell -ExecutionPolicy Bypass -File Tools\mirror_build_and_test.ps1 [TestFilter]
param([string]$Filter = "LastBell")
$ErrorActionPreference = "Continue"
$real = "C:\Hemant\Prj\Learning\TheLastBell"; $m = "C:\lbb"; $ue = "C:\Program Files\Epic Games\UE_5.8"
robocopy "$real\Source" "$m\Source" /MIR /NFL /NDL /NJH /NJS | Out-Null
robocopy "$real\Config" "$m\Config" /MIR /NFL /NDL /NJH /NJS | Out-Null
Copy-Item "$real\TheLastBell.uproject" "$m\TheLastBell.uproject" -Force
# robocopy keeps timestamps; touch changed sources so UBT recompiles them
git -C $real diff --name-only HEAD -- Source | ForEach-Object { $f = Join-Path $m $_; if (Test-Path $f) { (Get-Item $f).LastWriteTime = Get-Date } }
& "$ue\Engine\Build\BatchFiles\Build.bat" TheLastBellEditor Win64 Development "-Project=$m\TheLastBell.uproject" -WaitMutex -NoHotReloadFromIDE *> "$env:TEMP\lbb_build.log"
"build exit=$LASTEXITCODE"
Select-String -Path "$env:TEMP\lbb_build.log" -Pattern "error|warning C|Result:" | Select-Object -Last 6 | ForEach-Object { $_.Line }
if ($LASTEXITCODE -ne 0) { exit 2 }
$l = "$m\Saved\Logs\mirror_tests.log"
$p = Start-Process -FilePath "$ue\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" -ArgumentList @("$m\TheLastBell.uproject", "-ExecCmds=`"Automation RunTests $Filter; Quit`"", '-unattended', '-nullrhi', '-nosplash', '-nosound', '-NoP4', '-log', "-abslog=$l") -Wait -PassThru
(Select-String -Path $l -Pattern "Result=\{Success\}").Count.ToString() + " tests passed"
Select-String -Path $l -Pattern "Result=\{Fail" | ForEach-Object { "FAIL: " + ($_.Line -replace '^.*Name=', '') }
Select-String -Path $l -Pattern "LogAutomationController: Error: (?!Test Completed)" | Select-Object -First 8 | ForEach-Object { $_.Line -replace '^.*Error: ', 'ERR: ' }
