# Online Deploy Status

Updated: 2026-07-21

## Selected production path

```text
GitHub main
  -> Render Static Site (free)
       -> Next.js static export
       -> complete tracked JSON snapshot

GitHub Actions
  -> weekly/manual crawler and ETL
       -> Supabase Free when configured
```

The public website does not depend on a paid server or database. Supabase is optional; without it, the application reads the complete static snapshot deployed with the frontend.

## Verified release snapshot

```text
Index rows:              117,320
Detail rows:             117,320
Index chunks:                 24
Lazy detail chunks:          235
Source provinces:             53
ETL runs in manifest:          1
Production sources:            3
```

## Release checks

- ESLint: passed.
- Static-data integrity validator: passed.
- Crawler test suite: 19 passed.
- Next.js production static export: passed.
- Desktop static build: map, analysis dashboard, and ETL monitor verified.
- No tracked environment file or credential detected.
- Largest public data file is under 5 MiB; no file approaches GitHub's 100 MiB limit.

## Public deployment

Status: live and verified.

Public URL: `https://phongtro-intelligence.onrender.com`

```text
Blueprint: phongtro-intelligence
Blueprint ID: exs-d9fjrmurnols73c4j8ng
Service type: Static Site
Service ID: srv-d9fjrsgk1i2s73b01qfg
Initial live commit: e382e9d
```

The public deployment was verified with 117,320 snapshot rows, 117,201 rows after the default outlier rule, 3,891 map clusters, all analytics charts, the five-layer ETL monitor, no console warnings/errors, and no horizontal overflow at a mobile viewport.

Deployment instructions: [render-free-deployment.md](render-free-deployment.md).

## Optional live database

To enable Supabase later:

1. Create a Supabase Free project.
2. Add GitHub secret `SUPABASE_DB_URL`.
3. Run workflow `Supabase ETL` with `run_mode=load_static_snapshot`.
4. Verify the load before enabling weekly `crawl_then_load` runs.

The Render site stays available when Supabase is absent, paused, or at its free-tier limit.
