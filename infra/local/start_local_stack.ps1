$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$logDir = Join-Path $repoRoot "crawler\artifacts\logs"
$backendDir = Join-Path $repoRoot "backend"
$webDir = Join-Path $repoRoot "web"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Test-ProcessFromPidFile {
    param([string]$PidFile)
    if (-not (Test-Path $PidFile)) {
        return $false
    }

    $rawPid = (Get-Content $PidFile -Raw).Trim()
    if (-not $rawPid) {
        return $false
    }

    return [bool](Get-Process -Id $rawPid -ErrorAction SilentlyContinue)
}

function Test-WebServerProcess {
    $connections = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
    foreach ($connection in $connections) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($connection.OwningProcess)" -ErrorAction SilentlyContinue
        if ($process -and $process.CommandLine -and $process.CommandLine.Contains($webDir)) {
            return $true
        }
    }
    return $false
}

function Start-ManagedProcess {
    param(
        [string]$Name,
        [string]$WorkingDirectory,
        [string]$FilePath,
        [string[]]$ArgumentList
    )

    $pidFile = Join-Path $logDir "$Name.pid"
    if (Test-ProcessFromPidFile $pidFile) {
        Write-Output "$Name already running"
        return
    }
    if ($Name -eq "cap2-web" -and (Test-WebServerProcess)) {
        Write-Output "$Name already running on port 3000"
        return
    }

    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    $stdout = Join-Path $logDir "$Name.out.log"
    $stderr = Join-Path $logDir "$Name.err.log"
    $process = Start-Process -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -PassThru
    "$($process.Id)" | Set-Content -Path $pidFile -Encoding utf8
    Write-Output "$Name started with PID $($process.Id)"
}

Start-ManagedProcess `
    -Name "cap2-backend" `
    -WorkingDirectory $backendDir `
    -FilePath (Join-Path $backendDir ".venv\Scripts\python.exe") `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000")

$webBuildId = Join-Path $webDir ".next\BUILD_ID"
if (-not (Test-Path $webBuildId)) {
    Write-Output "web production build not found; running npm run build"
    & npm.cmd run build --prefix $webDir
}

Start-ManagedProcess `
    -Name "cap2-web" `
    -WorkingDirectory $webDir `
    -FilePath "npm.cmd" `
    -ArgumentList @("run", "start", "--", "--hostname", "127.0.0.1", "--port", "3000")
