<div align="center">

# PhongTro Intelligence

### Multi-source rental data platform for Vietnam

From public listing ingestion to quality-controlled geospatial analytics—delivered as a fast, cost-free web product.

[![Live](https://img.shields.io/badge/LIVE-Open%20product-1677ff?style=for-the-badge)](https://phongtro-intelligence.onrender.com)
![Listings](https://img.shields.io/badge/QUALITY--GATED-53%2C397%20listings-0f766e?style=for-the-badge)
![Sources](https://img.shields.io/badge/SOURCES-3-f59e0b?style=for-the-badge)
![Tests](https://img.shields.io/badge/TESTS-29%20passed-22c55e?style=for-the-badge)

[Live demo](https://phongtro-intelligence.onrender.com) · [Vietnamese documentation](README.vi.md) · [Architecture](docs/architecture.md) · [Operations](docs/local-operations.md)

</div>

---

## What this project does

PhongTro Intelligence turns fragmented rental listings into a traceable analytical product:

1. crawls three verified public room-rental sources;
2. stores source-level snapshots for reproducibility;
3. normalizes prices, areas, addresses, contacts and amenities;
4. deduplicates records and assigns stable identities;
5. standardizes location references and geospatial precision;
6. applies a reproducible score-based quality gate;
7. publishes chunked data for the map, dashboard and ETL observatory.

The production website works without a paid cloud account or always-on backend. A complete quality-gated snapshot is deployed with the Next.js static frontend on Render, while PostgreSQL/PostGIS, FastAPI and Supabase remain available as optional live-serving paths.

## Live product

### Search 53,397 listings on an interactive map

![Live PhongTro Intelligence map with 53,397 quality-gated listings](docs/readme-assets/web-map-live.png)

The map combines a searchable listing panel, province/district filters, price and area ranges, room type, amenities, source traceability and four levels of geospatial precision.

### Analytics and pipeline observability

| Market analytics | Six-stage ETL monitor |
|---|---|
| Median price, room area, supply, amenities, sources and spatial quality | Input, normalization, geocoding, quality rejection and publication history |
| ![Live analytics dashboard](docs/readme-assets/web-analytics-live.png) | ![Live ETL observability screen](docs/readme-assets/web-etl-live.png) |

## Current verified production snapshot

| Metric | Verified value |
|---|---:|
| Input rows | 58,595 |
| Published listings | **53,397** |
| Quality-gate retention | **91.1%** |
| Rejected by quality rules | 5,198 |
| Listings with images | 53,394 |
| Listings with contact data | 34,032 |
| Located listings | 53,387 |
| Provinces represented | 39 |
| Index / lazy-detail chunks | 11 / 107 |
| Production run | `etl-20260721T121656Z-d3cd1939` |
| Pipeline version | `production-quality-v3` |

Published source contribution:

| Source | Listings |
|---|---:|
| Phongtro123 | 22,264 |
| Mogi | 18,040 |
| NhaTot | 13,093 |

## System architecture

The diagram below was created and exported with **Excalidraw MCP**.

![PhongTro Intelligence architecture](docs/readme-assets/architecture-overview.png)

[Open the editable Excalidraw source](docs/readme-assets/architecture-overview.excalidraw)

The serving strategy deliberately supports two paths:

- **Default free path:** quality-gated JSON chunks → Next.js static export → Render.
- **Optional live path:** PostgreSQL/PostGIS or Supabase → FastAPI/REST → Next.js.

## Production ETL flow

![Six-stage production ETL flow](docs/readme-assets/etl-production-flow.png)

[Open the editable ETL diagram](docs/readme-assets/etl-production-flow.excalidraw)

The quality gate rejected 971 records missing core fields and 4,227 records scoring below 68. Ten additional records could not be mapped to a usable location reference. No quota-based row trimming is applied to the published snapshot.

## Engineering highlights

- **Multi-source ingestion:** dedicated adapters for Phongtro123, NhaTot and Mogi, with diagnostic adapters retained separately.
- **Reproducible data:** canonical URLs, source post IDs, content hashes and run fingerprints.
- **Quality-aware publication:** deterministic field checks plus a minimum completeness score.
- **Incremental operation:** resumable source checkpoints and scheduled/manual GitHub Actions workflows.
- **Geospatial semantics:** location precision distinguishes house address, street, district center and province center.
- **Static-data performance:** compact index chunks load first; record details are fetched lazily from 107 detail chunks.
- **Resilient serving:** Supabase and FastAPI can be enabled without making the public demo depend on them.
- **Observable pipeline:** the web interface exposes stage counts, retention, rejected records, source contribution and verified run history.

## Technology stack

| Layer | Technologies |
|---|---|
| Crawling | Python 3.11+, HTTPX, BeautifulSoup, lxml, Tenacity |
| Transformation | Python, Pydantic, deterministic quality scoring |
| Storage | JSON snapshots, PostgreSQL 16, PostGIS, optional MinIO |
| API | FastAPI, SQLAlchemy, psycopg |
| Frontend | Next.js 15, React 19, TypeScript |
| Visualization | Leaflet, React Leaflet, Recharts |
| Orchestration | PowerShell runbooks, GitHub Actions |
| Deployment | Render Static Site, optional Supabase |

## Repository structure

```text
backend/                 FastAPI and PostgreSQL serving path
crawler/                 source adapters, ETL and publication jobs
docs/
  readme-assets/         live screenshots and editable Excalidraw diagrams
  bao-cao/               Vietnamese academic report artifacts
infra/                   Docker Compose and optional cloud infrastructure
sql/                     PostGIS schema and Supabase views
web/                     Next.js map, analytics and ETL observatory
.github/workflows/       manual and scheduled ETL
```

## Run locally

### 1. Infrastructure

```bash
docker compose -f infra/docker-compose.yml up -d
```

### 2. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```powershell
cd web
npm install
npm run dev
```

Open <http://localhost:3000>.

### 4. Crawler

```powershell
cd crawler
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m app.main bootstrap --city "ho-chi-minh" --max-pages 3 --sources all
```

For the resumable three-source backfill:

```powershell
.\crawler\scripts\balanced_backfill.ps1
```

## Validation

The current repository was verified with:

```bash
cd crawler
python -m pytest -q                 # 29 passed

cd ../web
npm run validate:data              # 53,397 index/detail rows
npm run lint                       # passed
npm run build                      # production build passed

cd ..
docker compose -f infra/docker-compose.yml config --quiet
```

## Deployment model

```text
GitHub main
  └─ Render Static Site
       ├─ Next.js static export
       └─ complete quality-gated JSON snapshot

GitHub Actions
  ├─ manual or scheduled crawl
  ├─ curated transformation
  ├─ static snapshot publication
  └─ optional Supabase upsert
```

The live site does not require AWS, GCP, Azure or a paid database. Legacy AWS Terraform is kept only as an optional architecture exercise and is not the default deployment route.

## Responsible data use

This is an academic data-engineering project built from publicly visible rental listings. Source identity and canonical URLs are retained for traceability. The project should be operated with conservative crawl rates and in accordance with source terms and robots policies. Contact information must not be repurposed for unsolicited outreach or redistributed as a standalone dataset.

## Documentation

- [Current online deployment status](docs/online-deploy-status.md)
- [Local operations and resumable jobs](docs/local-operations.md)
- [Data inventory](docs/data-inventory.md)
- [ETL design](docs/etl-pipeline.md)
- [Architecture](docs/architecture.md)
- [Vietnamese completion report](docs/bao-cao-hoan-thien.md)
- [Render deployment guide](docs/render-free-deployment.md)

## License

Code is released under the [MIT License](LICENSE). Source listing content remains the property of its respective publishers.
