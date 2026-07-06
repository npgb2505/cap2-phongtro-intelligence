$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$logDir = Join-Path $repoRoot "crawler\artifacts\logs"

foreach ($name in @("cap2-backend", "cap2-web", "cap2-watchdog")) {
    $pidFile = Join-Path $logDir "$name.pid"
    if (-not (Test-Path $pidFile)) {
        Write-Output "$name is not running"
        continue
    }

    $rawPid = (Get-Content $pidFile -Raw).Trim()
    $process = if ($rawPid) { Get-Process -Id $rawPid -ErrorAction SilentlyContinue } else { $null }
    if ($process) {
        Stop-Process -Id $rawPid -Force
        Write-Output "$name stopped"
    }
    else {
        Write-Output "$name was not running"
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}
