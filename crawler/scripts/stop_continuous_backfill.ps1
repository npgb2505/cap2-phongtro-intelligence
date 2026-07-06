$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$crawlerDir = Split-Path -Parent $scriptDir
$logDir = Join-Path $crawlerDir "artifacts\logs"
$pidFile = Join-Path $logDir "continuous_backfill.pid"

if (-not (Test-Path $pidFile)) {
    Write-Output "continuous_backfill is not running"
    exit 0
}

$targetPid = (Get-Content $pidFile -Raw).Trim()
if (-not $targetPid) {
    Write-Output "continuous_backfill is not running"
    exit 0
}

$targetProcess = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
if (-not $targetProcess) {
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    Write-Output "continuous_backfill is not running"
    exit 0
}

Stop-Process -Id $targetPid -Force
Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue

Write-Output "continuous_backfill stopped"
