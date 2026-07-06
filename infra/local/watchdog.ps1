param(
    [int]$IntervalSeconds = 60,
    [int]$DailyHour = 2,
    [int]$DailyMinute = 15
)

$ErrorActionPreference = "Continue"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$logDir = Join-Path $repoRoot "crawler\artifacts\logs"
$pidFile = Join-Path $logDir "cap2-watchdog.pid"
$heartbeatFile = Join-Path $logDir "cap2-watchdog.heartbeat"
$stateFile = Join-Path $logDir "cap2-watchdog-state.json"
$startStackScript = Join-Path $scriptDir "start_local_stack.ps1"
$dailyScript = Join-Path $repoRoot "crawler\scripts\incremental_daily.ps1"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
"$PID" | Set-Content -Path $pidFile -Encoding utf8

function Read-State {
    if (-not (Test-Path $stateFile)) {
        return @{ last_daily_refresh_date = "" }
    }
    try {
        $state = Get-Content $stateFile -Raw | ConvertFrom-Json
        return @{ last_daily_refresh_date = [string]$state.last_daily_refresh_date }
    }
    catch {
        return @{ last_daily_refresh_date = "" }
    }
}

function Write-State {
    param([hashtable]$State)
    $State | ConvertTo-Json | Set-Content -Path $stateFile -Encoding utf8
}

while ($true) {
    $now = Get-Date
    $stamp = $now.ToString("yyyy-MM-dd HH:mm:ss")
    $stamp | Set-Content -Path $heartbeatFile -Encoding utf8

    try {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $startStackScript | Out-File -FilePath (Join-Path $logDir "cap2-watchdog.log") -Append -Encoding utf8
    }
    catch {
        $_ | Out-File -FilePath (Join-Path $logDir "cap2-watchdog.log") -Append -Encoding utf8
    }

    $state = Read-State
    $today = $now.ToString("yyyy-MM-dd")
    $shouldRunDaily = (
        $state.last_daily_refresh_date -ne $today -and
        (
            $now.Hour -gt $DailyHour -or
            ($now.Hour -eq $DailyHour -and $now.Minute -ge $DailyMinute)
        )
    )

    if ($shouldRunDaily) {
        try {
            "[$stamp] Starting daily refresh" | Out-File -FilePath (Join-Path $logDir "cap2-watchdog.log") -Append -Encoding utf8
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $dailyScript | Out-File -FilePath (Join-Path $logDir "cap2-watchdog.log") -Append -Encoding utf8
            $state.last_daily_refresh_date = $today
            Write-State $state
        }
        catch {
            $_ | Out-File -FilePath (Join-Path $logDir "cap2-watchdog.log") -Append -Encoding utf8
        }
    }

    Start-Sleep -Seconds $IntervalSeconds
}
