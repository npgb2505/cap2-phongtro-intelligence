# Cloud Deployment Flow

This document is the deployment runbook for moving the PhongTro Intelligence Platform from the verified local ETL setup to AWS.

## Current readiness

The project is ready for a controlled cloud pilot, but not a one-click production deployment yet.

Cost guard: the available AWS credit is 100 USD. Do not run `terraform apply` until IAM Identity Center account assignment, Billing/Credits review, and AWS Budget alerts are complete.

Ready now:

- crawler extract/transform flow works locally and writes structured JSON/CSV artifacts
- curated snapshot has been loaded into local PostgreSQL table `public.curated_listings`
- backend can query PostgreSQL first and fall back to curated CSV
- web app builds successfully with `npm run build`
- Dockerfiles exist for backend, crawler, and web
- Terraform pilot stack exists for S3, RDS PostgreSQL, ECR repositories, Secrets Manager, ECS scheduled crawler resources, optional App Runner backend, and CloudWatch logs

Not complete yet:

- crawler Docker image now includes `python -m app.cloud_job` for incremental crawl, curated transform, S3 upload, and RDS load when `PT_S3_BUCKET` and `PT_DATABASE_URL` are set
- web Dockerfile now starts the production Next.js server; Amplify/Vercel is still the simpler first cloud pilot path
- backend has no cloud migration runner; run SQL/schema and `app.load_curated` manually during the pilot
- local PostgreSQL instance does not have PostGIS, so the current imported table has latitude/longitude but no `geom` column
- Terraform CLI was installed and `terraform init -backend=false && terraform validate` passes locally
- AWS CLI v2 is installed and SSO login succeeded for the `cap2` SSO session
- IAM Identity Center currently returns `accountList: []`, so user `codex` still needs an AWS account assignment before deploy

## Target architecture

Use this shape for the first cloud deployment:

```text
Local crawler bootstrap
  -> curated CSV snapshot
  -> one-time load into RDS PostgreSQL

AWS RDS PostgreSQL
  -> public.curated_listings

Backend API
  -> ECS Fargate or App Runner
  -> reads RDS via PT_DATABASE_URL

Web frontend
  -> Amplify Hosting or Vercel
  -> calls NEXT_PUBLIC_API_URL

Daily incremental crawler
  -> ECS Fargate scheduled task
  -> writes latest artifacts to S3
  -> refreshes/upserts RDS
```

## Phase 0: Local release checks

Run these from `D:\UNIVERSITY\Cap2`:

```powershell
backend\.venv\Scripts\python.exe -m compileall backend\app crawler\app
```

```powershell
cd D:\UNIVERSITY\Cap2\web
npm run build
```

Confirm local PostgreSQL has data:

```powershell
$env:PGPASSWORD="123456"
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -p 5432 -d phongtro -c "select count(*) from public.curated_listings;"
```

Expected current count: `44543`.

## Phase 1: Provision AWS foundation

Before provisioning, check billing and create a budget alert in AWS Billing and Cost Management. For the 100 USD credit limit, keep the first pilot small and review the Terraform plan before applying.

Create a Terraform variables file outside git:

```hcl
db_password = "replace-with-strong-password"
```

Run:

```powershell
cd D:\UNIVERSITY\Cap2\infra\aws
terraform init
terraform plan -var-file="dev.tfvars"
terraform apply -var-file="dev.tfvars"
```

The current Terraform only creates the early foundation. Before using it for a serious deployment, add:

- private subnets or an explicit VPC choice
- security groups for backend/crawler to reach RDS
- inbound rules for the backend entrypoint
- Secrets Manager secret for `PT_DATABASE_URL`
- ECR repositories for backend and crawler images
- ECS task definitions and task execution roles
- EventBridge schedule for the crawler task

## Phase 2: Initialize RDS schema

After RDS is created, connect with the endpoint from Terraform:

```powershell
terraform output postgres_endpoint
```

Apply schema:

```powershell
$env:PGPASSWORD="replace-with-rds-password"
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h "<rds-endpoint>" -p 5432 -d phongtro -f D:\UNIVERSITY\Cap2\sql\schema.sql
```

If PostGIS is not available or not enabled, use the Python loader path because it can create `curated_listings` without `geom`.

## Phase 3: Load curated data to RDS

Point backend at RDS:

```powershell
$env:PT_DATABASE_URL="postgresql+psycopg://postgres:<password>@<rds-endpoint>:5432/phongtro"
cd D:\UNIVERSITY\Cap2\backend
.\.venv\Scripts\python.exe -m app.load_curated --csv ..\crawler\artifacts\curated\toan-quoc\listings_curated.csv
```

Verify:

```powershell
$env:PGPASSWORD="<password>"
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h "<rds-endpoint>" -p 5432 -d phongtro -c "select count(*) from public.curated_listings;"
```

## Phase 4: Deploy backend API

Build and push backend image:

```powershell
cd D:\UNIVERSITY\Cap2\backend
docker build -t phongtro-backend:dev .
```

For AWS, create/push to ECR:

```powershell
aws ecr create-repository --repository-name phongtro-backend
aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.ap-southeast-1.amazonaws.com
docker tag phongtro-backend:dev <account-id>.dkr.ecr.ap-southeast-1.amazonaws.com/phongtro-backend:dev
docker push <account-id>.dkr.ecr.ap-southeast-1.amazonaws.com/phongtro-backend:dev
```

Run it on ECS Fargate or App Runner with:

- `PT_APP_ENV=production`
- `PT_APP_DEBUG=false`
- `PT_DATABASE_URL` from Secrets Manager
- `PT_CORS_ORIGINS` containing the frontend URL

Health check path:

```text
/health
```

## Phase 5: Deploy frontend

For the first pilot, use Amplify Hosting or Vercel from the `web` directory.

Set:

```text
NEXT_PUBLIC_API_URL=https://<backend-domain>/api/v1
```

Build command:

```text
npm run build
```

If deploying as a container, update `web/Dockerfile` to run a production Next.js server instead of `npm run dev`.

## Phase 6: Schedule daily crawler

Build crawler image:

```powershell
cd D:\UNIVERSITY\Cap2\crawler
docker build -t phongtro-crawler:dev .
```

The ECS scheduled task command should be:

```text
python -m app.cloud_job
```

The cloud job reads these environment variables:

- `PT_DATABASE_URL`
- `PT_S3_BUCKET`
- `PT_S3_PREFIX`
- `PT_SOURCES`
- `PT_PAGES`
- `PT_MAX_DETAIL_PAGES`
- `PT_DETAIL_WORKERS`
- `PT_EXACT_GEOCODE_LIMIT`

## Phase 7: Operational checks

After deployment, verify:

```sql
select count(*) from public.curated_listings;
select province, count(*) from public.curated_listings group by province order by count(*) desc limit 10;
select max(posted_at), max(updated_at) from public.curated_listings;
```

Check:

- backend `/health` returns `{"status":"ok"}`
- frontend map loads real API data, not fallback data
- crawler CloudWatch logs show `failed_urls=0` or explain failures
- RDS has recent `updated_at` values after each scheduled run
- S3 receives raw/normalized/tabular artifacts once S3 upload is implemented
