# Online Deploy Status

Updated: 2026-07-12

## Repository

GitHub private repo:

```text
https://github.com/npgb2505/cap2-phongtro-intelligence
```

Default branch:

```text
main
```

Latest pushed commit:

```text
8543556 Prepare free Render and Vercel deployment
```

## Current state

Completed:

- Local Git repo was repaired by backing up the broken `.git` directory.
- Fresh Git repo was initialized.
- Private GitHub repo was created and pushed.
- Supabase/Vercel/GitHub Actions route is now the primary cloud route.
- Supabase guide is present in `docs/supabase-vercel-github-actions.md`.
- Supabase SQL views/RLS sample is present in `sql/supabase_views.sql`.
- GitHub Actions Supabase ETL workflow is present in `.github/workflows/supabase-etl.yml`.
- Frontend loader in `web/lib/api.ts` now tries Supabase first, then legacy API, then static JSON.
- Render Blueprint config is present in `render.yaml` as a legacy fallback.
- Backend Render Dockerfile is present in `backend/Dockerfile.render` as a legacy fallback.
- Legacy compact deploy CSV is present in `crawler/artifacts/deploy/listings_deploy.csv`.
- Legacy compact deploy CSV has 3,000 rows: 1,000 each from `phongtro123`, `nhatot`, and `mogi`.
- Local cloud-mode backend test passed with `PT_DATABASE_ENABLED=false`.
- Web production build passed.
- Local self-audit passed.
- GitHub Pages static deployment is live and verified.

Waiting:

- Supabase project must be created by the user.
- GitHub secret `SUPABASE_DB_URL` must be added before running `.github/workflows/supabase-etl.yml`.
- Supabase SQL is applied automatically by the workflow in order: `sql/schema.sql`, load CSV, then `sql/supabase_views.sql`.
- Vercel frontend import must be configured with `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- The older Neon Postgres + Render API + Vercel frontend route remains documented in `docs/cloud-option-2-neon-render-vercel.md`.

GitHub Pages fallback:

- A static frontend deploy path has been added so the project can go online without Render/Vercel login.
- Static JSON data lives at `web/public/data/listings-map.json`.
- Full online data now uses a small manifest plus chunk files under `web/public/data/listings-map-chunks/`.
- The full static export contains 56,061 valid listings and 52 source fields from the curated CSV; one malformed CSV row is skipped during export.
- GitHub Actions workflow lives at `.github/workflows/pages.yml`.
- Frontend is now redesigned as a map-first rental workspace: source filters, source-colored markers, listing sidebar, and visible marker count.
- Live Pages URL:

```text
https://npgb2505.github.io/cap2-phongtro-intelligence/
```

## Primary Supabase/Vercel/GitHub Actions cloud path

Use:

```text
docs/supabase-vercel-github-actions.md
```

Key files:

```text
sql/schema.sql
sql/supabase_views.sql
backend/app/apply_sql.py
backend/app/load_curated.py
backend/app/check_supabase_load.py
.github/workflows/supabase-etl.yml
web/lib/api.ts
web/env.vercel.example
```

Safe rollout:

1. Create Supabase Free project.
2. Add GitHub secret:

```text
SUPABASE_DB_URL=postgresql+psycopg://...
```

3. Run workflow `Supabase ETL` with:

```text
run_mode=load_existing_csv
csv_path=crawler/artifacts/deploy/listings_deploy.csv
```

4. The workflow applies `sql/schema.sql`, loads CSV, applies `sql/supabase_views.sql`, then runs `backend/app/check_supabase_load.py`.
5. Deploy `web/` to Vercel with:

```text
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-public-key>
NEXT_PUBLIC_SUPABASE_LISTINGS_VIEW=v_listing_map
NEXT_PUBLIC_SUPABASE_PAGE_SIZE=1000
NEXT_PUBLIC_SUPABASE_MAX_ROWS=60000
```

6. Only after this path works, test `run_mode=crawl_then_load` with small values.

Verified:

```text
HTML status: 200
JSON manifest total: 56061
JSON manifest returned: 56061
chunks: 12
phongtro123: 44851
nhatot: 10065
mogi: 1005
thuephongtro: 84
batdongsan: 35
alonhadat: 21
```

## GitHub Pages static deploy

The static deploy uses:

```text
GITHUB_PAGES=true
NEXT_PUBLIC_STATIC_DATA_PATH=/cap2-phongtro-intelligence/data/listings-map.json
```

It builds `web/out` using `npm run build:pages` and deploys it through GitHub Actions.

It has already been enabled through the GitHub Pages API with `build_type=workflow`. If it ever needs to be reconfigured manually:

1. Open repo settings:

```text
https://github.com/npgb2505/cap2-phongtro-intelligence/settings/pages
```

2. Set Source to:

```text
GitHub Actions
```

3. Trigger the workflow:

```text
https://github.com/npgb2505/cap2-phongtro-intelligence/actions/workflows/pages.yml
```

Click `Run workflow` on branch `main`.

## Legacy Render backend dashboard steps

1. Open Render:

```text
https://dashboard.render.com/blueprints/new
```

2. Log in.
3. Connect GitHub account `npgb2505` if prompted.
4. Select repo:

```text
npgb2505/cap2-phongtro-intelligence
```

5. Render should detect `render.yaml`.
6. Confirm service:

```text
cap2-phongtro-api
```

7. Confirm plan:

```text
Free
```

8. Apply/create Blueprint.
9. After deploy, test:

```text
https://<render-service>.onrender.com/health
https://<render-service>.onrender.com/api/v1/listings/map?limit=5
```

Expected health:

```json
{"status":"ok","environment":"production"}
```

## Legacy Vercel frontend through Render API

1. Open Vercel import:

```text
https://vercel.com/new
```

2. Import repo:

```text
npgb2505/cap2-phongtro-intelligence
```

3. Set Root Directory:

```text
web
```

4. Add environment variable:

```text
NEXT_PUBLIC_API_URL=https://<render-service>.onrender.com/api/v1
```

5. Deploy.
6. After Vercel gives the frontend URL, update Render env var:

```text
PT_CORS_ORIGINS=https://<your-vercel-app>.vercel.app
```
