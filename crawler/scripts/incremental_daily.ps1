param(
    [int]$Pages = 3,
    [int]$MaxDetailPages = 20,
    [int]$DetailWorkers = 6,
    [int]$ExactGeocodeLimit = 0,
    [string]$Sources = "all"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$crawlerDir = Split-Path -Parent $scriptDir
$repoRoot = Split-Path -Parent $crawlerDir
$backendDir = Join-Path $repoRoot "backend"
$logDir = Join-Path $crawlerDir "artifacts\logs"
$logFile = Join-Path $logDir "incremental_daily.log"
$curatedCsv = Join-Path $crawlerDir "artifacts\curated\toan-quoc\listings_curated.csv"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $Message"
    Write-Output $line
    Add-Content -Path $logFile -Value $line -Encoding utf8
}

function Write-CommandOutput {
    process {
        $line = "$_"
        Write-Output $line
        Add-Content -Path $logFile -Value $line -Encoding utf8
    }
}

Write-Log "Starting incremental crawl: pages=$Pages max_detail_pages=$MaxDetailPages detail_workers=$DetailWorkers sources=$Sources"
Push-Location $crawlerDir
try {
    & ".\.venv\Scripts\python.exe" -m app.main incremental --city all --pages $Pages --max-detail-pages $MaxDetailPages --detail-workers $DetailWorkers --sources $Sources 2>&1 |
        Write-CommandOutput

    Write-Log "Transforming curated snapshot"
    & ".\.venv\Scripts\python.exe" -m app.main transform-curated --exact-geocode-limit $ExactGeocodeLimit 2>&1 |
        Write-CommandOutput
}
finally {
    Pop-Location
}

if ((Test-Path $backendDir) -and (Test-Path (Join-Path $backendDir ".venv\Scripts\python.exe")) -and (Test-Path $curatedCsv)) {
    Write-Log "Loading curated snapshot into PostgreSQL"
    Push-Location $backendDir
    try {
        & ".\.venv\Scripts\python.exe" -m app.load_curated --csv $curatedCsv 2>&1 |
            Write-CommandOutput
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Log "Skipping PostgreSQL load because backend venv or curated CSV was not found"
}

Write-Log "Daily incremental refresh completed"
