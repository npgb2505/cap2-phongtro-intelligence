# PhongTro Intelligence Platform

Production-grade room-rental data platform focused on multi-source room-rental ingestion, normalization, storage, map search, and incremental daily sync.

## Why this repo exists

This project is intentionally designed like a real product:

- `local bootstrap` for the first large crawl to save AWS credits
- `incremental cloud sync` for daily updates only
- `raw + staging + curated` data layers
- `FastAPI` for serving search and map endpoints
- `Next.js` map frontend where each listing is a marker
- `AWS-first` deployment model using the user's available credits

## Architecture at a glance

```text
Local Bootstrap Crawl
  -> raw JSON / HTML snapshots
  -> upload to S3
  -> normalize + load into PostgreSQL

Daily Incremental Sync
  EventBridge Scheduler
    -> ECS Fargate crawler
    -> detect new / updated / expired listings
    -> write raw snapshots to S3
    -> upsert curated tables in PostgreSQL

Serving Layer
  FastAPI
    -> filter/search endpoints
    -> map bbox endpoint
    -> listing detail endpoint

Frontend
  Next.js
    -> map view
    -> marker popups
    -> sidebar result list
```

## Repo layout

```text
backend/     FastAPI service
crawler/     local bootstrap and incremental ingestion jobs
docs/        architecture and delivery documentation
infra/       docker compose and AWS Terraform skeleton
sql/         database schema and seed data
web/         Next.js map frontend
```

## Current implementation status

- Production-oriented repo scaffold created
- Domain model and SQL schema defined
- FastAPI endpoints scaffolded
- Local/bootstrap + incremental crawler flow supports Phongtro123, Alonhadat, ThuePhongTro, NhaTot, BatDongSan, and Mogi source adapters
- Concurrent detail crawling added for faster local backfill
- Map-based frontend scaffolded
- Docker Compose for local dev scaffolded
- Terraform skeleton for AWS scaffolded
- Local recurring automations created for backfill and daily sync

## Delivery strategy

### Phase 1

- Crawl initial nationwide data on local machine
- Store raw snapshots locally
- Normalize and bulk load to PostgreSQL
- Validate geocoding quality

### Phase 2

- Upload raw artifacts to S3
- Deploy database and API
- Deploy Next.js map frontend

### Phase 3

- Enable daily incremental crawl on AWS
- Detect inserts, updates, expirations
- Add monitoring and alerts

## Local development

### 1. Start local services

```bash
docker compose -f infra/docker-compose.yml up -d
```

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload --port 8000
```

To load the curated nationwide snapshot into PostgreSQL:

```bash
cd backend
.venv\Scripts\python.exe -m app.load_curated
```

If your machine is using a local PostgreSQL service instead of the repo's default Docker credentials, set `PT_DATABASE_URL` in `backend/.env` first.

### 3. Crawler bootstrap

```bash
cd crawler
python -m venv .venv
.venv\Scripts\activate
pip install -e .
python -m app.main bootstrap --city "ho-chi-minh" --max-pages 3 --sources all
```

For cloud/scheduled execution, the crawler image runs:

```bash
python -m app.cloud_job
```

This performs incremental crawl, curated transform, optional S3 upload, and optional PostgreSQL load when the relevant `PT_*` environment variables are present.

Use `--sources phongtro123`, `--sources alonhadat`, or a comma-separated list to run a subset. The merged ETL table is written to `crawler/artifacts/tabular/toan-quoc/listings_all.csv`, while per-source QA tables are written under `crawler/artifacts/tabular/{source}/...`.

For current verified commands, resumable nationwide crawl, and local automation details, see [docs/local-operations.md](/D:/UNIVERSITY/Cap2/docs/local-operations.md).
For the live field inventory confirmed from the website, see [docs/data-inventory.md](/D:/UNIVERSITY/Cap2/docs/data-inventory.md).
For the cloud deployment readiness check and rollout flow, see [docs/cloud-deployment-flow.md](/D:/UNIVERSITY/Cap2/docs/cloud-deployment-flow.md).
For the latest handover, verified data counts, local URLs, and auto-restart setup, see [docs/handover.md](/D:/UNIVERSITY/Cap2/docs/handover.md).
For a Vietnamese usage guide with AWS credit safeguards, see [docs/huong-dan-su-dung.md](/D:/UNIVERSITY/Cap2/docs/huong-dan-su-dung.md).
For the current no-AWS free/near-free deployment route, see [docs/free-deployment.md](/D:/UNIVERSITY/Cap2/docs/free-deployment.md).
For the current GitHub/Render/Vercel deployment status, see [docs/online-deploy-status.md](/D:/UNIVERSITY/Cap2/docs/online-deploy-status.md).

### 4. Frontend

```bash
cd web
npm install
npm run dev
```

## AWS target stack

- `Amazon S3` for raw zone and export artifacts
- `Amazon RDS PostgreSQL` for curated serving data
- `Amazon ECS Fargate` for daily incremental crawl jobs
- `Amazon EventBridge Scheduler` for scheduled sync
- `AWS Secrets Manager` for runtime secrets
- `Amazon CloudWatch` for logs and alarms
- `AWS Amplify Hosting` or containerized frontend for web delivery

## Next practical steps

1. Bulk-run the nationwide backfill until the historical queue is exhausted.
2. Implement S3 upload for crawler artifacts.
3. Wire incremental crawler completion to PostgreSQL upsert/load.
4. Expand Terraform from foundation resources into deployable ECS/App Runner services.
5. Add Amazon Location geocoding and caching for map markers.
