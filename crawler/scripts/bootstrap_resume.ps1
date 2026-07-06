$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$crawlerDir = Split-Path -Parent $scriptDir

Set-Location $crawlerDir

& ".\.venv\Scripts\python.exe" -m app.main bootstrap-resume --city all --page-chunk 5 --max-detail-pages 10 --detail-workers 6
