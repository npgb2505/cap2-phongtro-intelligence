$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$stopScript = Join-Path $scriptDir "stop_local_stack.ps1"
$taskName = "Cap2 Local Stack Watchdog"
$runKeyPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$runValueName = "Cap2LocalStackWatchdog"

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $runKeyPath -Name $runValueName -ErrorAction SilentlyContinue
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $stopScript
Write-Output "Uninstalled scheduled task and HKCU Run fallback: $taskName"
