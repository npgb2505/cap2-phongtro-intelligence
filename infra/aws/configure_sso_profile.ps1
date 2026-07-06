param(
    [string]$Profile = "cap2",
    [string]$SsoSession = "cap2",
    [string]$StartUrl = "https://d-90667473bd.awsapps.com/start",
    [string]$SsoRegion = "us-east-1",
    [string]$Region = "ap-southeast-1",
    [string]$AccountId = "",
    [string]$RoleName = "",
    [string]$AwsExe = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $AwsExe)) {
    $cmd = Get-Command aws -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "AWS CLI was not found. Install AWS CLI v2 first."
    }
    $AwsExe = $cmd.Source
}

$awsDir = Join-Path $env:USERPROFILE ".aws"
$configPath = Join-Path $awsDir "config"
New-Item -ItemType Directory -Force -Path $awsDir | Out-Null

function Remove-IniBlock {
    param(
        [string]$Text,
        [string]$Header
    )
    $escaped = [regex]::Escape($Header)
    return ($Text -replace "(?ms)^\[$escaped\]\r?\n.*?(?=^\[|\z)", "").TrimEnd()
}

function Read-SsoToken {
    param([string]$ExpectedStartUrl)

    $cacheDir = Join-Path $env:USERPROFILE ".aws\sso\cache"
    if (-not (Test-Path $cacheDir)) {
        return $null
    }

    $matches = @()
    Get-ChildItem $cacheDir -Filter "*.json" | Sort-Object LastWriteTime -Descending | ForEach-Object {
        try {
            $json = Get-Content $_.FullName -Raw | ConvertFrom-Json
            if ($json.startUrl -eq $ExpectedStartUrl -and $json.accessToken) {
                $matches += $json.accessToken
            }
        } catch {
        }
    }

    if ($matches.Count -eq 0) {
        return $null
    }
    return $matches[0]
}

$existing = if (Test-Path $configPath) { Get-Content $configPath -Raw } else { "" }
$clean = Remove-IniBlock -Text $existing -Header "profile $Profile"
$clean = Remove-IniBlock -Text $clean -Header "sso-session $SsoSession"

$baseBlock = @"
[profile $Profile]
sso_session = $SsoSession
region = $Region
output = json

[sso-session $SsoSession]
sso_start_url = $StartUrl
sso_region = $SsoRegion
sso_registration_scopes = sso:account:access
"@

($clean.TrimEnd() + "`r`n`r`n" + $baseBlock.Trim() + "`r`n") | Set-Content -Path $configPath -Encoding ascii

Write-Host "Logging in to AWS SSO session '$SsoSession'..."
& $AwsExe sso login --sso-session $SsoSession
if ($LASTEXITCODE -ne 0) {
    throw "AWS SSO login failed."
}

$token = Read-SsoToken -ExpectedStartUrl $StartUrl
if (-not $token) {
    throw "No SSO token found after login."
}

$accountsJson = & $AwsExe sso list-accounts --access-token $token --region $SsoRegion
if ($LASTEXITCODE -ne 0) {
    throw "Unable to list SSO accounts."
}

$accounts = ($accountsJson | ConvertFrom-Json).accountList
if (-not $accounts -or $accounts.Count -eq 0) {
    throw "SSO login works, but this user has no AWS account assignment. In IAM Identity Center, assign user 'codex' to the target AWS account and permission set, then run this script again."
}

if ($AccountId) {
    $selectedAccount = $accounts | Where-Object { $_.accountId -eq $AccountId } | Select-Object -First 1
    if (-not $selectedAccount) {
        throw "Requested account '$AccountId' was not found in SSO assignments."
    }
} else {
    $selectedAccount = $accounts | Select-Object -First 1
}

$rolesJson = & $AwsExe sso list-account-roles --access-token $token --account-id $selectedAccount.accountId --region $SsoRegion
if ($LASTEXITCODE -ne 0) {
    throw "Unable to list SSO roles for account $($selectedAccount.accountId)."
}

$roles = ($rolesJson | ConvertFrom-Json).roleList
if (-not $roles -or $roles.Count -eq 0) {
    throw "No SSO roles are assigned for account $($selectedAccount.accountId)."
}

if ($RoleName) {
    $selectedRole = $roles | Where-Object { $_.roleName -eq $RoleName } | Select-Object -First 1
    if (-not $selectedRole) {
        throw "Requested role '$RoleName' was not found for account $($selectedAccount.accountId)."
    }
} else {
    $selectedRole = ($roles | Where-Object { $_.roleName -eq "AdministratorAccess" } | Select-Object -First 1)
    if (-not $selectedRole) {
        $selectedRole = $roles | Select-Object -First 1
    }
}

$finalBlock = @"
[profile $Profile]
sso_session = $SsoSession
sso_account_id = $($selectedAccount.accountId)
sso_role_name = $($selectedRole.roleName)
region = $Region
output = json

[sso-session $SsoSession]
sso_start_url = $StartUrl
sso_region = $SsoRegion
sso_registration_scopes = sso:account:access
"@

$existing = if (Test-Path $configPath) { Get-Content $configPath -Raw } else { "" }
$clean = Remove-IniBlock -Text $existing -Header "profile $Profile"
$clean = Remove-IniBlock -Text $clean -Header "sso-session $SsoSession"
($clean.TrimEnd() + "`r`n`r`n" + $finalBlock.Trim() + "`r`n") | Set-Content -Path $configPath -Encoding ascii

Write-Host "Configured AWS profile '$Profile' for account $($selectedAccount.accountId) and role $($selectedRole.roleName)."
& $AwsExe sts get-caller-identity --profile $Profile
if ($LASTEXITCODE -ne 0) {
    throw "Profile was written, but sts get-caller-identity failed."
}

