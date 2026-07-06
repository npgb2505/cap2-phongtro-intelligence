param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$checks = New-Object System.Collections.Generic.List[object]

function Add-Check {
    param(
        [string]$Name,
        [bool]$Passed,
        [string]$Detail
    )
    $checks.Add([PSCustomObject]@{
        name   = $Name
        passed = $Passed
        detail = $Detail
    }) | Out-Null
}

function Run-CommandCheck {
    param(
        [string]$Name,
        [string]$Command,
        [string]$WorkingDirectory = $repoRoot
    )
    Push-Location $WorkingDirectory
    try {
        $output = Invoke-Expression $Command 2>&1
        Add-Check -Name $Name -Passed ($LASTEXITCODE -eq 0 -or $null -eq $LASTEXITCODE) -Detail (($output | Select-Object -Last 5) -join "`n")
    }
    catch {
        Add-Check -Name $Name -Passed $false -Detail "$_"
    }
    finally {
        Pop-Location
    }
}

Run-CommandCheck -Name "python_compile" -Command "backend\.venv\Scripts\python.exe -m compileall backend\app crawler\app test.py"
if ($Build) {
    Run-CommandCheck -Name "web_build" -Command "npm run build" -WorkingDirectory (Join-Path $repoRoot "web")
}

try {
    $health = Invoke-RestMethod "http://127.0.0.1:8000/health"
    Add-Check -Name "backend_health" -Passed ($health.status -eq "ok") -Detail ($health | ConvertTo-Json -Compress)
}
catch {
    Add-Check -Name "backend_health" -Passed $false -Detail "$_"
}

try {
    $map = Invoke-RestMethod "http://127.0.0.1:8000/api/v1/listings/map?limit=1"
    Add-Check -Name "map_api" -Passed ($map.total -ge 1000 -and $map.returned -eq 1) -Detail "total=$($map.total) returned=$($map.returned)"
}
catch {
    Add-Check -Name "map_api" -Passed $false -Detail "$_"
}

try {
    $web = Invoke-WebRequest "http://127.0.0.1:3000" -UseBasicParsing
    Add-Check -Name "web_http" -Passed ($web.StatusCode -eq 200) -Detail "status=$($web.StatusCode) length=$($web.Content.Length)"
}
catch {
    Add-Check -Name "web_http" -Passed $false -Detail "$_"
}

try {
    $sourceCounts = Import-Csv (Join-Path $repoRoot "crawler\artifacts\curated\toan-quoc\listings_curated.csv") |
        Group-Object source_name |
        Sort-Object Count -Descending |
        Select-Object Name, Count
    $sourceTotal = @($sourceCounts).Count
    $largeSourceTotal = @($sourceCounts | Where-Object { $_.Count -ge 1000 }).Count
    Add-Check -Name "curated_sources" -Passed ($sourceTotal -ge 3 -and $largeSourceTotal -ge 3) -Detail (($sourceCounts | ConvertTo-Json -Compress))
}
catch {
    Add-Check -Name "curated_sources" -Passed $false -Detail "$_"
}

try {
    $deployPath = Join-Path $repoRoot "crawler\artifacts\deploy\listings_deploy.csv"
    $deployCounts = Import-Csv $deployPath |
        Group-Object source_name |
        Sort-Object Count -Descending |
        Select-Object Name, Count
    $deployLargeSourceTotal = @($deployCounts | Where-Object { $_.Count -ge 1000 }).Count
    Add-Check -Name "deploy_snapshot_sources" -Passed ($deployLargeSourceTotal -ge 3) -Detail (($deployCounts | ConvertTo-Json -Compress))
}
catch {
    Add-Check -Name "deploy_snapshot_sources" -Passed $false -Detail "$_"
}

try {
    $runValue = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "Cap2LocalStackWatchdog" -ErrorAction Stop
    Add-Check -Name "autostart" -Passed ($null -ne $runValue.Cap2LocalStackWatchdog) -Detail $runValue.Cap2LocalStackWatchdog
}
catch {
    Add-Check -Name "autostart" -Passed $false -Detail "$_"
}

try {
    $heartbeatPath = Join-Path $repoRoot "crawler\artifacts\logs\cap2-watchdog.heartbeat"
    $heartbeat = Get-Content $heartbeatPath -Raw
    Add-Check -Name "watchdog_heartbeat" -Passed ([bool]$heartbeat.Trim()) -Detail $heartbeat.Trim()
}
catch {
    Add-Check -Name "watchdog_heartbeat" -Passed $false -Detail "$_"
}

$result = [PSCustomObject]@{
    generated_at = (Get-Date).ToString("s")
    passed       = -not [bool]($checks | Where-Object { -not $_.passed })
    checks       = $checks
}

$result | ConvertTo-Json -Depth 5

if (-not $result.passed) {
    exit 1
}
