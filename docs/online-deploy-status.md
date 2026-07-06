# Online Deploy Status

Updated: 2026-07-06

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
- Render Blueprint config is present in `render.yaml`.
- Backend Render Dockerfile is present in `backend/Dockerfile.render`.
- Deploy CSV is present in `crawler/artifacts/deploy/listings_deploy.csv`.
- Deploy CSV has 3,000 rows: 1,000 each from `phongtro123`, `nhatot`, and `mogi`.
- Local cloud-mode backend test passed with `PT_DATABASE_ENABLED=false`.
- Web production build passed.
- Local self-audit passed.
- GitHub Pages static deployment is live and verified.

Waiting:

- Render dashboard login is still required.
- Render GitHub connection must allow repo `cap2-phongtro-intelligence`.
- After backend deploy, Vercel frontend import must be configured with the Render API URL.

GitHub Pages fallback:

- A static frontend deploy path has been added so the project can go online without Render/Vercel login.
- Static JSON data lives at `web/public/data/listings-map.json`.
- GitHub Actions workflow lives at `.github/workflows/pages.yml`.
- Live Pages URL:

```text
https://npgb2505.github.io/cap2-phongtro-intelligence/
```

Verified:

```text
HTML status: 200
JSON total: 3000
JSON returned: 3000
phongtro123: 1000
nhatot: 1000
mogi: 1000
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

## Render backend dashboard steps

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

## Vercel frontend dashboard steps

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
