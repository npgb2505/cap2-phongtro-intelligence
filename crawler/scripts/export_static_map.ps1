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
        --source-csv "crawler\artifacts\curated\toan-quoc\listings_curated.csv" `
        --output-json "web\public\data\listings-map.json" `
        --chunk-size 5000 `
        --detail-chunk-size 500 `
        --max-rows 20000
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
