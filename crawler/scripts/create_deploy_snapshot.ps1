$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$python = Join-Path $repoRoot "crawler\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Missing crawler virtual environment Python: $python"
}

Push-Location $repoRoot
try {
    & $python -m app.deploy_snapshot `
        --source-csv "crawler\artifacts\curated\toan-quoc\listings_curated.csv" `
        --output-csv "crawler\artifacts\deploy\listings_deploy.csv" `
        --summary-json "crawler\artifacts\deploy\deploy_snapshot_summary.json" `
        --max-rows 60000 `
        --min-source-share 0.24
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
