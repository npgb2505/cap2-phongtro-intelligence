param(
    [int]$ChunkPages = 100,
    [int]$SearchWorkers = 4,
    [int]$MaxChunks = 0,
    [string]$Sources = "nhatot,mogi",
    [switch]$ResetState
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$crawlerDir = Split-Path -Parent $scriptDir
Set-Location $crawlerDir

$arguments = @(
    "-m", "app.main", "balanced-backfill",
    "--city", "all",
    "--sources", $Sources,
    "--chunk-pages", $ChunkPages,
    "--search-workers", $SearchWorkers
)
if ($MaxChunks -gt 0) {
    $arguments += @("--max-chunks", $MaxChunks)
}
if ($ResetState) {
    $arguments += "--reset-state"
}

& ".\.venv\Scripts\python.exe" @arguments
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& ".\.venv\Scripts\python.exe" -m app.main transform-curated --exact-geocode-limit 0
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& "$scriptDir\export_static_map.ps1"
exit $LASTEXITCODE
