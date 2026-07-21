# PhongTro Intelligence Platform

Production-grade room-rental data platform focused on multi-source room-rental ingestion, normalization, storage, map search, and incremental daily sync.

## Why this repo exists

This project is intentionally designed like a real product:

- `local bootstrap` for the first large crawl to avoid cloud cost spikes
- `GitHub Actions ETL` for safe manual or scheduled updates
- `raw + staging + curated` data layers
- `Supabase Postgres` for the cloud curated database
- `Next.js` static frontend on Render's free global CDN
- no AWS/GCP default path because credits/free-trial signup are unavailable

## Architecture at a glance

```text
Local Bootstrap Crawl
  -> raw JSON / HTML snapshots
  -> normalize + curated CSV
  -> static JSON chunks for fallback

Cloud Update Path
  GitHub Actions manual/schedule
    -> incremental crawler
    -> curated transform
    -> upsert Supabase Postgres

Serving Layer
  Supabase REST/views
    -> v_listing_map
    -> dashboard aggregate views
    -> RLS/read-only policy

Frontend
  Next.js static export on Render
    -> map view
    -> marker popups
    -> sidebar result list
    -> 117,320-row static snapshot split into lazy JSON chunks
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
- Local/bootstrap + incremental crawler flow keeps six diagnostic adapters; production curation publishes the three verified high-yield sources Phongtro123, NhaTot, and Mogi
- Concurrent detail crawling added for faster local backfill
- Map workspace, data-analysis dashboard, and five-layer ETL progress monitor scaffolded
- Docker Compose for local dev scaffolded
- Terraform skeleton for AWS scaffolded as legacy/optional infra
- Local recurring automations created for backfill and daily sync
- Render Static Site blueprint, Supabase SQL views, and manual/scheduled GitHub Actions ETL added

## Delivery strategy

### Phase 1

- Crawl initial nationwide data on local machine
- Store raw snapshots locally
- Normalize and bulk load to PostgreSQL
- Validate geocoding quality

### Phase 2

- Deploy the complete static snapshot to a free Render Static Site
- Keep Supabase optional until a live database is required
- Create a Supabase Free project and load curated data only after checking quota

### Phase 3

- Enable GitHub Actions `crawl_then_load` on a low schedule after manual runs pass
- Detect inserts, updates, expirations
- Add Supabase dashboard views and usage checks

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

The production dataset publishes only `phongtro123`, `nhatot`, and `mogi`. The
remaining adapters are retained for diagnostics, but their current unique yield
is too small to improve the dataset. To fill the two underrepresented sources
with resumable, source-specific checkpoints, run:

```powershell
.\crawler\scripts\balanced_backfill.ps1
```

The command resumes after the highest saved page, crawls NhaTot through its
verified API offset limit, discovers Mogi's archive boundary using empty chunks,
then rebuilds the curated and static map snapshots.

For current verified commands, resumable nationwide crawl, and local automation details, see [docs/local-operations.md](docs/local-operations.md).
For the live field inventory confirmed from the website, see [docs/data-inventory.md](docs/data-inventory.md).
For the current free Render deployment route, see [docs/render-free-deployment.md](docs/render-free-deployment.md).
For the optional Supabase/GitHub Actions cloud data route, see [docs/supabase-vercel-github-actions.md](docs/supabase-vercel-github-actions.md).
For the older cloud deployment readiness check and rollout flow, see [docs/cloud-deployment-flow.md](docs/cloud-deployment-flow.md).
For the latest handover, verified data counts, local URLs, and auto-restart setup, see [docs/handover.md](docs/handover.md).
For a Vietnamese usage guide with AWS credit safeguards, see [docs/huong-dan-su-dung.md](docs/huong-dan-su-dung.md).
For the no-AWS static fallback route, see [docs/free-deployment.md](docs/free-deployment.md).
For the older database-backed fallback with Neon, Render, and Vercel, see [docs/cloud-option-2-neon-render-vercel.md](docs/cloud-option-2-neon-render-vercel.md).
For the current online deployment status, see [docs/online-deploy-status.md](docs/online-deploy-status.md).
For the final Vietnamese completion report, see [docs/bao-cao-hoan-thien.md](docs/bao-cao-hoan-thien.md).

Live free Render deployment:

```text
https://phongtro-intelligence.onrender.com
```

### 4. Frontend

```bash
cd web
npm install
npm run dev
```

## Current low-cost target stack

- `Render Static Site` for the frontend and complete tracked snapshot at zero cost
- `GitHub Actions` for manual/scheduled ETL and database upsert
- `Supabase Free Postgres` as an optional live curated database
- `Supabase views/RLS` for read-only frontend access when the database is enabled

## Legacy AWS target stack

- `Amazon S3` for raw zone and export artifacts
- `Amazon RDS PostgreSQL` for curated serving data
- `Amazon ECS Fargate` for daily incremental crawl jobs
- `Amazon EventBridge Scheduler` for scheduled sync
- `AWS Secrets Manager` for runtime secrets
- `Amazon CloudWatch` for logs and alarms
- `AWS Amplify Hosting` or containerized frontend for web delivery

## Next practical steps

1. Create a Render Blueprint from this repository; `render.yaml` provisions the free static site.
2. Verify the map, filters, analytics dashboard, ETL monitor, and lazy detail loading.
3. Optionally create a Supabase project and add GitHub secret `SUPABASE_DB_URL`.
4. Run `.github/workflows/supabase-etl.yml` with `run_mode=load_static_snapshot` for the first database load.
5. Verify one manual `crawl_then_load` run before relying on the weekly schedule.
