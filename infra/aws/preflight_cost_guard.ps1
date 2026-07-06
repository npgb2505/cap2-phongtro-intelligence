param(
    [string]$Profile = "cap2",
    [decimal]$MaxMonthlyBudgetUsd = 100,
    [decimal]$WarnActualCostUsd = 10,
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

Write-Host "Checking AWS identity with profile '$Profile'..."
$identityJson = & $AwsExe sts get-caller-identity --profile $Profile
if ($LASTEXITCODE -ne 0) {
    throw "AWS identity check failed. Run infra\aws\configure_sso_profile.ps1 after assigning user 'codex' to an AWS account."
}

$identity = $identityJson | ConvertFrom-Json
Write-Host "Account: $($identity.Account)"
Write-Host "ARN: $($identity.Arn)"

$today = Get-Date
$start = Get-Date -Year $today.Year -Month $today.Month -Day 1
$end = $today.AddDays(1)
$timePeriod = "Start=$($start.ToString('yyyy-MM-dd')),End=$($end.ToString('yyyy-MM-dd'))"

Write-Host "Checking current month unblended cost..."
$costJson = & $AwsExe ce get-cost-and-usage `
    --time-period $timePeriod `
    --granularity MONTHLY `
    --metrics UnblendedCost `
    --profile $Profile `
    --region us-east-1

if ($LASTEXITCODE -ne 0) {
    throw "Unable to read Cost Explorer data. Check Billing permissions before deploy."
}

$cost = $costJson | ConvertFrom-Json
$amountText = $cost.ResultsByTime[0].Total.UnblendedCost.Amount
$currency = $cost.ResultsByTime[0].Total.UnblendedCost.Unit
$amount = [decimal]$amountText
Write-Host ("Current month unblended cost: {0:N4} {1}" -f $amount, $currency)

if ($amount -ge $WarnActualCostUsd) {
    throw "Current cost is already >= $WarnActualCostUsd USD. Review Billing before deploy."
}

Write-Host "Checking AWS Budgets..."
$budgetsJson = & $AwsExe budgets describe-budgets --account-id $identity.Account --profile $Profile --region us-east-1
if ($LASTEXITCODE -ne 0) {
    throw "Unable to read AWS Budgets. Create/check a budget in AWS Billing before deploy."
}

$budgets = ($budgetsJson | ConvertFrom-Json).Budgets
if (-not $budgets -or $budgets.Count -eq 0) {
    throw "No AWS Budget found. Create a monthly cost budget with alerts before deploy."
}

$matchingBudget = $budgets | Where-Object {
    $_.BudgetType -eq "COST" -and
    $_.TimeUnit -eq "MONTHLY" -and
    $_.BudgetLimit.Unit -eq "USD" -and
    ([decimal]$_.BudgetLimit.Amount) -le $MaxMonthlyBudgetUsd
} | Select-Object -First 1

if (-not $matchingBudget) {
    throw "No monthly COST budget <= $MaxMonthlyBudgetUsd USD found. Create one before deploy."
}

Write-Host "Budget guard found: $($matchingBudget.BudgetName) <= $($matchingBudget.BudgetLimit.Amount) USD/month"
Write-Host "PASS: AWS cost preflight is safe to continue to terraform plan."
