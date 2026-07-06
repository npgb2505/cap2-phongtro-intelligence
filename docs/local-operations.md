# Local Crawl Operations

## Verified commands

Run from `D:\UNIVERSITY\Cap2\crawler`:

```powershell
.\.venv\Scripts\python.exe -m app.main bootstrap --city ho-chi-minh --max-pages 1 --max-detail-pages 3
.\.venv\Scripts\python.exe -m app.main bootstrap-resume --city all --page-chunk 1 --max-detail-pages 3
.\.venv\Scripts\python.exe -m app.main incremental --city all --pages 1 --max-detail-pages 5
```

## Convenience scripts

- `crawler\scripts\bootstrap_resume.ps1`
- `crawler\scripts\incremental_daily.ps1`
- `crawler\scripts\start_continuous_backfill.ps1`
- `crawler\scripts\stop_continuous_backfill.ps1`

These scripts assume the crawler virtual environment already exists at `crawler\.venv`.

## Multi-thread crawling

The crawler now supports concurrent detail-page fetches with the `--detail-workers` flag.

Examples:

```powershell
.\.venv\Scripts\python.exe -m app.main bootstrap-resume --city all --page-chunk 5 --max-detail-pages 20 --detail-workers 6
.\.venv\Scripts\python.exe -m app.main incremental --city all --pages 1 --max-detail-pages 20 --detail-workers 6
```

Default worker count is controlled by `PT_DETAIL_WORKER_COUNT` in `.env`.

## Continuous local backfill

To keep the machine crawling continuously:

```powershell
cd D:\UNIVERSITY\Cap2\crawler
.\scripts\start_continuous_backfill.ps1
```

To stop it:

```powershell
.\scripts\stop_continuous_backfill.ps1
```

Runtime health files:

- PID file: `crawler\artifacts\logs\continuous_backfill.pid`
- heartbeat: `crawler\artifacts\logs\continuous_backfill.heartbeat`
- rolling log: `crawler\artifacts\logs\continuous_backfill.log`

## Local automation jobs

The Codex app now has two active local automations:

- `Cap2 Daily Incremental Nationwide`
  - daily at 02:15
  - captures new listings using `incremental`
- `Cap2 Continuous Backfill Watchdog`
  - every 30 minutes
  - calls `start_continuous_backfill.ps1` to ensure the hidden continuous crawler is still alive

The older `Cap2 Bootstrap Resume Nationwide` cron automation is now paused because the machine is already running a dedicated continuous backfill process. This avoids overlapping bootstrap jobs.

## Important state and artifacts

- backfill state: `crawler\artifacts\state\bootstrap_toan-quoc.json`
- nationwide bootstrap JSON: `crawler\artifacts\normalized\toan-quoc\page_*.json`
- nationwide incremental JSON: `crawler\artifacts\normalized\toan-quoc\incremental_latest.json`
- nationwide bootstrap CSV tables: `crawler\artifacts\tabular\toan-quoc\page_*.csv`
- nationwide incremental CSV table: `crawler\artifacts\tabular\toan-quoc\incremental_latest.csv`
- merged master table: `crawler\artifacts\tabular\toan-quoc\listings_all.csv`
- curated serving CSV: `crawler\artifacts\curated\toan-quoc\listings_curated.csv`
- raw HTML snapshots: disabled by default; only written when `PT_SAVE_RAW_HTML=true`

For the end-to-end ETL explanation, see [etl-pipeline.md](/D:/UNIVERSITY/Cap2/docs/etl-pipeline.md).

## Loading curated data into PostgreSQL

From `D:\UNIVERSITY\Cap2\backend`:

```powershell
.\.venv\Scripts\python.exe -m app.load_curated
```

This loader expects `PT_DATABASE_URL` to point at the correct PostgreSQL instance. If you are not using the repo's docker-compose defaults, update `backend\.env` before running the import.

## Current verified backfill state

At the time of verification on 2026-06-29:

- `last_page`: `4156`
- `next_page`: `3`
- `completed`: `false`

This means the resumable nationwide crawl is active and still has a large historical backlog to process over time.
