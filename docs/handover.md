# Cap2 Handover

Last verified: 2026-07-06

## What is complete locally

- Nationwide bootstrap state is complete: `crawler/artifacts/state/bootstrap_toan-quoc.json`.
- Curated serving snapshot is regenerated: `crawler/artifacts/curated/toan-quoc/listings_curated.csv`.
- PostgreSQL local load succeeds through `backend/app/load_curated.py`.
- Backend is running at `http://127.0.0.1:8000`.
- Web is running at `http://127.0.0.1:3000`.
- Local watchdog is running and writing `crawler/artifacts/logs/cap2-watchdog.heartbeat`.
- Codex automations are active for daily refresh and local watchdog.
- Per-user Windows autostart is installed through `HKCU:\Software\Microsoft\Windows\CurrentVersion\Run\Cap2LocalStackWatchdog`.

## Current verified data

Curated snapshot:

- Source rows read: 56,041
- Low-quality/captcha rows skipped: 70
- Curated rows written: 55,971
- Rows loaded into local PostgreSQL/API: 55,896 after `listing_id` de-duplication
- Geocoded/reference-mapped rows: 55,837
- Unique province values after cleanup: 53

Source counts in curated CSV:

| Source | Rows |
| --- | ---: |
| phongtro123 | 44,818 |
| nhatot | 10,028 |
| mogi | 1,005 |
| thuephongtro | 84 |
| batdongsan | 35 |
| alonhadat | 1 |

This satisfies the stronger target of at least 3 sources with 1,000+ listings each: `phongtro123`, `nhatot`, and `mogi`. `alonhadat` is currently captcha-limited, so its robot pages are intentionally filtered from curated output.

## Run locally

Start backend and web:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra\local\start_local_stack.ps1
```

The web process uses `next start` and runs `npm run build` automatically if `.next/BUILD_ID` is missing.

Stop backend, web, and watchdog:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra\local\stop_local_stack.ps1
```

Run a full daily refresh manually:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File crawler\scripts\incremental_daily.ps1
```

That command runs:

1. incremental crawler for all configured sources
2. curated transform
3. PostgreSQL load when `backend\.venv` and DB are available

## Auto-restart setup

Start the self-healing watchdog now:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra\local\start_watchdog.ps1
```

Install it as a Windows Scheduled Task at logon:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra\local\install_watchdog_task.ps1
```

The watchdog:

- keeps backend and web running
- writes heartbeat to `crawler/artifacts/logs/cap2-watchdog.heartbeat`
- runs daily refresh after 02:15 if it has not run today
- records PID files in `crawler/artifacts/logs`
- can be installed without admin rights; if Scheduled Task registration is denied, it uses the HKCU Run fallback

Run self-audit:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra\local\self_audit.ps1
```

## Health checks

Backend:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Map API:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/listings/map?limit=5"
```

Web:

```powershell
Invoke-WebRequest http://127.0.0.1:3000 -UseBasicParsing
```

## AWS auth and deploy status

Local deployment is running and verified. AWS infrastructure code now includes the cloud pilot foundation, ECR repositories, Secrets Manager DB URL, optional App Runner backend, and optional scheduled ECS crawler. The crawler Docker image defaults to `python -m app.cloud_job`, which runs incremental crawl, curated transform, optional S3 upload, and optional PostgreSQL/RDS load. Terraform v1.15.7 was installed and `terraform init -backend=false && terraform validate` passes for `infra/aws`.

AWS CLI v2 is installed at `C:\Program Files\Amazon\AWSCLIV2\aws.exe`. The local SSO profile `cap2` is configured with:

- SSO start URL: `https://d-90667473bd.awsapps.com/start`
- SSO region: `us-east-1`
- default project region: `ap-southeast-1`

SSO browser login succeeded on 2026-07-06, but AWS returned `accountList: []`. That means the IAM Identity Center user `codex` is not assigned to an AWS account/permission set yet. Full AWS deployment is not claimed complete because Terraform cannot safely apply until that account assignment exists and billing/credit checks are done.

Because the available AWS credit is 100 USD, do not run `terraform apply` until:

1. user `codex` has an account assignment
2. Billing/Credits has been checked in AWS Console
3. AWS Budget alerts have been created
4. the user explicitly approves the deploy

Cost guard scripts were added:

- `infra\aws\configure_sso_profile.ps1` logs in to SSO, lists assigned accounts/roles, and writes `sso_account_id` / `sso_role_name` into profile `cap2`.
- `infra\aws\preflight_cost_guard.ps1` checks `sts get-caller-identity`, current month Cost Explorer data, and the existence of a monthly AWS Budget <= 100 USD.

Terraform now refuses to create the paid RDS resource unless `dev.tfvars` includes:

```hcl
monthly_credit_limit_usd    = 100
paid_deploy_acknowledgement = "CHECKED_BILLING_BUDGET_APPROVED_100_USD"
```

Production-ready next AWS steps:

1. Assign IAM Identity Center user `codex` to the AWS account with a pilot permission set.
2. Verify `aws sts get-caller-identity --profile cap2`.
3. Check AWS Credits/Billing and create budget alerts.
4. Run `terraform plan -var-file="dev.tfvars"` and review cost-impacting resources.
5. Apply `infra/aws` with `db_password` only after approval.
6. Push backend/crawler images to the Terraform-created ECR repositories.
7. Re-apply Terraform with `backend_image_identifier` and `crawler_image_identifier` only when ready to run online services.
8. Deploy web through Amplify/Vercel or the production Dockerfile.
9. Point the frontend at the App Runner backend URL and verify public map loading.

The current `web/Dockerfile` is production-oriented and runs `next start`.

For Vietnamese operating instructions, see [huong-dan-su-dung.md](/D:/UNIVERSITY/Cap2/docs/huong-dan-su-dung.md).

## No-AWS free deployment route

Because the AWS credit has expired, the current recommended online demo path is:

- Render Free Web Service for the FastAPI backend
- Vercel Hobby for the Next.js frontend
- no cloud database
- bundled compact deploy CSV inside the backend Docker image

Files added for this path:

- `render.yaml`
- `backend/Dockerfile.render`
- `.dockerignore`
- `crawler\app\deploy_snapshot.py`
- `crawler\scripts\create_deploy_snapshot.ps1`
- `docs/free-deployment.md`

The backend runs with `PT_DATABASE_ENABLED=false` and reads `/app/data/listings_curated.csv`, which is copied from `crawler/artifacts/deploy/listings_deploy.csv` at Docker build time. The deploy snapshot has 3,000 rows: 1,000 each from `phongtro123`, `nhatot`, and `mogi`. This avoids Render Postgres and its 30-day Free database expiration while keeping the deploy artifact small enough for GitHub/Render.
