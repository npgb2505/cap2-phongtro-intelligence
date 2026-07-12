# Free/Near-Free Deployment Guide

Updated: 2026-07-06

This path avoids AWS completely. It is designed for project demo delivery after the AWS credit expired.

## Chosen architecture

This document describes the cheapest CSV/static fallback. If you want the current database-backed cloud setup with Supabase Postgres, Vercel frontend, and GitHub Actions ETL, use:

```text
docs/supabase-vercel-github-actions.md
```

The older Neon/Render/Vercel route is still documented as a fallback:

```text
docs/cloud-option-2-neon-render-vercel.md
```

```text
Supabase Free Postgres
  -> curated_listings database
  -> read-only views for map/dashboard

GitHub Actions
  -> manual load_existing_csv
  -> optional crawl_then_load after manual test passes

Vercel Hobby
  -> Next.js frontend
  -> reads Supabase by NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY
```

No-login fallback:

```text
GitHub Pages
  -> static-exported Next.js frontend
  -> reads web/public/data/listings-map.json
  -> no backend required
```

Why this route:

- no AWS resource is created
- Supabase is the preferred managed PostgreSQL option when a cloud database is needed
- a verified deploy CSV with 3 sources x 1,000 listings is shipped with the backend image
- the app remains easy to demo online

Tradeoff: Supabase Free has size/egress limits and may pause inactive projects, so GitHub Pages/static JSON remains the safest demo fallback.

## Current verified data

- API/local loaded rows: 55,896
- Curated CSV rows: 55,971
- Deploy CSV rows: 3,000
- Sources with 1,000+ listings:
  - `phongtro123`: 44,818
  - `nhatot`: 10,028
  - `mogi`: 1,005
- Deploy CSV sources:
  - `phongtro123`: 1,000
  - `nhatot`: 1,000
  - `mogi`: 1,000

## Current database path: Supabase Free

Use [docs/supabase-vercel-github-actions.md](/D:/UNIVERSITY/Cap2/docs/supabase-vercel-github-actions.md) for the full flow. Key files:

- `sql/schema.sql`
- `sql/supabase_views.sql`
- `.github/workflows/supabase-etl.yml`
- `web/lib/api.ts`
- `web/env.vercel.example`

Start with the compact CSV:

```text
crawler/artifacts/deploy/listings_deploy.csv
```

Then load the full curated CSV only after checking Supabase free-tier usage:

```text
crawler/artifacts/curated/toan-quoc/listings_curated.csv
```

## Legacy backend: Render Free

Files added for Render:

- `render.yaml`
- `backend/Dockerfile.render`
- `.dockerignore`
- `crawler/app/deploy_snapshot.py`
- `crawler/scripts/create_deploy_snapshot.ps1`

The Render backend uses:

```text
PT_DATABASE_ENABLED=false
PT_LISTING_DATASET_PATH=/app/data/listings_curated.csv
```

That means the backend reads the bundled deploy CSV and does not connect to any paid/free-expiring cloud database.

Regenerate the deploy CSV after a data refresh:

```powershell
cd D:\UNIVERSITY\Cap2
powershell.exe -NoProfile -ExecutionPolicy Bypass -File crawler\scripts\create_deploy_snapshot.ps1
```

The generated files are:

```text
crawler/artifacts/deploy/listings_deploy.csv
crawler/artifacts/deploy/deploy_snapshot_summary.json
```

## Prepare GitHub repo

Render and Vercel both expect a Git repository. The current local `.git` folder is incomplete, so if `git status` says `fatal: not a git repository`, create a fresh Git repo before deploying:

```powershell
cd D:\UNIVERSITY\Cap2
Rename-Item .git .git.broken -ErrorAction SilentlyContinue
git init
git add .
git status --short
git commit -m "Prepare free Render and Vercel deployment"
git branch -M main
git remote add origin https://github.com/<your-user>/<your-repo>.git
git push -u origin main
```

The `.gitignore` keeps raw crawler artifacts and the 94 MiB full curated CSV out of Git while allowing:

```text
crawler/artifacts/deploy/listings_deploy.csv
crawler/artifacts/deploy/deploy_snapshot_summary.json
```

The deploy CSV is intentionally much smaller than the full 94 MiB curated CSV to avoid GitHub's single-file limit and keep Render builds faster.

Deploy steps:

1. Push this repo to GitHub.
2. Open Render Dashboard.
3. Create a new Blueprint from the GitHub repo.
4. Confirm the `cap2-phongtro-api` service uses `plan: free`.
5. Wait for deploy to finish.
6. Test:

```text
https://<render-service>.onrender.com/health
https://<render-service>.onrender.com/api/v1/listings/map?limit=5
```

Expected health:

```json
{"status":"ok","environment":"production"}
```

## Frontend: Vercel Hobby

Deploy steps:

1. Open Vercel Dashboard.
2. Import the same GitHub repo.
3. Set Root Directory to:

```text
web
```

4. Set environment variable:

```text
NEXT_PUBLIC_API_URL=https://<render-service>.onrender.com/api/v1
```

5. Deploy.

After Vercel gives a URL, update Render env var:

```text
PT_CORS_ORIGINS=https://<your-vercel-app>.vercel.app
```

For the fastest first deploy, `render.yaml` currently uses `PT_CORS_ORIGINS=*`. Tighten it to the Vercel URL after the final frontend URL exists.

## Local verification before pushing

From repo root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra\local\self_audit.ps1
```

Build backend image locally if Docker Desktop is available:

```powershell
docker build -f backend\Dockerfile.render -t cap2-phongtro-api:render .
docker run --rm -p 8000:8000 cap2-phongtro-api:render
```

Then test:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/listings/map?limit=5"
```

Build frontend:

```powershell
cd D:\UNIVERSITY\Cap2\web
npm run build
```

## Cost notes

Official docs checked on 2026-07-06:

- Render Free web services spin down after 15 minutes without inbound traffic and wake on the next request.
- Render Free web services have ephemeral filesystems, so this deploy bundles the compact deploy CSV into the image instead of writing runtime data.
- Render Free Postgres expires after 30 days, so this plan intentionally avoids Render Postgres.
- Vercel Hobby is free for personal projects.
- Railway Hobby is not free; it has a monthly subscription. Do not use Railway for the zero-cost path.
- Supabase Free has a 500 MB database limit, but it is not needed for this route.

Official references:

- Render Free: https://render.com/docs/free
- Render Blueprint spec: https://render.com/docs/blueprint-spec
- Vercel Hobby: https://vercel.com/docs/plans/hobby
- Supabase pricing: https://supabase.com/pricing
- Railway pricing: https://docs.railway.com/pricing/plans
