$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$logDir = Join-Path $repoRoot "crawler\artifacts\logs"
$pidFile = Join-Path $logDir "cap2-watchdog.pid"
$watchdogScript = Join-Path $scriptDir "watchdog.ps1"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if (Test-Path $pidFile) {
    $rawPid = (Get-Content $pidFile -Raw).Trim()
    if ($rawPid -and (Get-Process -Id $rawPid -ErrorAction SilentlyContinue)) {
        Write-Output "cap2-watchdog already running"
        exit 0
    }
}

Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", $watchdogScript) `
    -WindowStyle Hidden
Write-Output "cap2-watchdog started"
