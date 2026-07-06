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

Waiting:

- Render dashboard login is still required.
- Render GitHub connection must allow repo `cap2-phongtro-intelligence`.
- After backend deploy, Vercel frontend import must be configured with the Render API URL.

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

