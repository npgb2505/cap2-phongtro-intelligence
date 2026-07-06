$ErrorActionPreference = "Continue"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$crawlerDir = Split-Path -Parent $scriptDir
$logDir = Join-Path $crawlerDir "artifacts\logs"
$logFile = Join-Path $logDir "continuous_backfill.log"
$pidFile = Join-Path $logDir "continuous_backfill.pid"
$heartbeatFile = Join-Path $logDir "continuous_backfill.heartbeat"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
Set-Location $crawlerDir
"$PID" | Set-Content -Path $pidFile -Encoding utf8

while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $logFile -Value "[$timestamp] Starting bootstrap-resume batch"
    $timestamp | Set-Content -Path $heartbeatFile -Encoding utf8

    try {
        $output = & ".\.venv\Scripts\python.exe" -m app.main bootstrap-resume --city all --page-chunk 5 --max-detail-pages 20 --detail-workers 6 2>&1
        $output | Out-File -FilePath $logFile -Append -Encoding utf8
    } catch {
        $_ | Out-File -FilePath $logFile -Append -Encoding utf8
    }

    $statePath = Join-Path $crawlerDir "artifacts\state\bootstrap_toan-quoc.json"
    if (Test-Path $statePath) {
        try {
            $state = Get-Content $statePath -Raw | ConvertFrom-Json
            if ($state.completed -eq $true) {
                $doneTimestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
                Add-Content -Path $logFile -Value "[$doneTimestamp] Bootstrap completed; sleeping for 6 hours before re-check."
                $doneTimestamp | Set-Content -Path $heartbeatFile -Encoding utf8
                Start-Sleep -Seconds 21600
                continue
            }
        } catch {
            $_ | Out-File -FilePath $logFile -Append -Encoding utf8
        }
    }

    Start-Sleep -Seconds 5
}
