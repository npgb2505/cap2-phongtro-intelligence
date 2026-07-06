# AWS Deployment Notes

This Terraform stack provisions the cloud pilot foundation and optional runtime services.

Always keep `dev.tfvars` outside git or use a secrets manager in your CI.

## Cost guard

The current AWS credit budget is 100 USD. Do not run `terraform apply` until:

1. IAM Identity Center user `codex` is assigned to the target AWS account.
2. `aws sts get-caller-identity --profile cap2` succeeds.
3. AWS Billing/Credits has been checked.
4. AWS Budgets alerts have been created.
5. The deploy has explicit user approval.

The first pilot should keep `backend_image_identifier` and `crawler_image_identifier` empty. That creates the foundation only and avoids starting App Runner or the scheduled crawler before they are needed.

After the SSO account assignment exists, configure the local profile:

```powershell
cd D:\UNIVERSITY\Cap2
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra\aws\configure_sso_profile.ps1
```

Before any Terraform apply, run the cost guard:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra\aws\preflight_cost_guard.ps1
```

Terraform also refuses to create the paid RDS resource unless `dev.tfvars` contains the explicit acknowledgement shown below.

## Foundation only

```powershell
cd D:\UNIVERSITY\Cap2\infra\aws
terraform init
terraform plan -var-file="dev.tfvars"
terraform apply -var-file="dev.tfvars"
```

Minimum `dev.tfvars`:

```hcl
db_password = "replace-with-strong-password"
```

After Billing/Credits and Budgets are checked, add:

```hcl
monthly_credit_limit_usd      = 100
paid_deploy_acknowledgement   = "CHECKED_BILLING_BUDGET_APPROVED_100_USD"
```

This creates:

- S3 raw artifact bucket with versioning
- RDS PostgreSQL
- ECR repositories for backend and crawler
- ECS cluster and crawler log group
- Secrets Manager `PT_DATABASE_URL`
- pilot security groups

The crawler image defaults to `python -m app.cloud_job`, which performs:

1. incremental crawl
2. curated transform
3. PostgreSQL upsert through `PT_DATABASE_URL`
4. S3 upload of incremental and curated artifacts through `PT_S3_BUCKET`

## Build and push images

After `terraform apply`, read:

```powershell
terraform output backend_ecr_repository_url
terraform output crawler_ecr_repository_url
```

Build/push:

```powershell
cd D:\UNIVERSITY\Cap2\backend
docker build -t phongtro-backend:dev .
docker tag phongtro-backend:dev <backend_repo_url>:dev
docker push <backend_repo_url>:dev

cd D:\UNIVERSITY\Cap2\crawler
docker build -t phongtro-crawler:dev .
docker tag phongtro-crawler:dev <crawler_repo_url>:dev
docker push <crawler_repo_url>:dev
```

## Enable backend App Runner and scheduled crawler

Set these after images exist:

```hcl
backend_image_identifier = "<backend_repo_url>:dev"
crawler_image_identifier = "<crawler_repo_url>:dev"
backend_cors_origins     = "https://your-frontend.example.com"
```

Then rerun:

```powershell
terraform plan -var-file="dev.tfvars"
terraform apply -var-file="dev.tfvars"
```

Optional hardening before production:

- Replace `db_ingress_cidrs = ["0.0.0.0/0"]` with a restricted CIDR.
- Move RDS into private subnets.
- Add an S3 upload implementation in the crawler before depending on cloud artifact retention.
- Add monitoring alarms for App Runner, ECS task failures, RDS storage, and crawler zero-result runs.
