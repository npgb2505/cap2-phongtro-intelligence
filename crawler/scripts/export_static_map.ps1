$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$python = Join-Path $repoRoot "crawler\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Missing crawler virtual environment Python: $python"
}

Push-Location $repoRoot
try {
    & $python -m app.static_map_export `
        --source-csv "crawler\artifacts\deploy\listings_deploy.csv" `
        --output-json "web\public\data\listings-map.json" `
        --ensure-snapshot
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
