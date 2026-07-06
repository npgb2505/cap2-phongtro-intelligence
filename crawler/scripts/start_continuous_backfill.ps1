$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runnerPath = Join-Path $scriptDir "continuous_backfill.ps1"
$crawlerDir = Split-Path -Parent $scriptDir
$logDir = Join-Path $crawlerDir "artifacts\logs"
$pidFile = Join-Path $logDir "continuous_backfill.pid"

Set-Location $crawlerDir

if (Test-Path $pidFile) {
    $existingPid = (Get-Content $pidFile -Raw).Trim()
    if ($existingPid) {
        $existingProcess = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
        if ($existingProcess) {
            Write-Output "continuous_backfill is already running"
            exit 0
        }
    }
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
Start-Process -FilePath "pwsh" -ArgumentList @("-NoProfile", "-WindowStyle", "Hidden", "-File", $runnerPath) -WindowStyle Hidden
Write-Output "continuous_backfill started"
