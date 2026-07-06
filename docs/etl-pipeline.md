# ETL Pipeline

This crawler now follows a structured ETL flow instead of a raw-HTML-first workflow.

## 1. Extract

Input sources:

- search result pages from Phongtro123
- search result pages from Alonhadat
- search result pages from ThuePhongTro
- JSON listing API from NhaTot / ChoTot
- encoded JSON listing API from BatDongSan's mobile map service
- search result cards from Mogi
- detail pages for each listing URL discovered from search results

What happens in extract:

- fetch search page HTML
- parse listing detail URLs
- fetch detail page HTML concurrently with `--detail-workers`
- pass detail HTML into the source-specific extractor
- keep `source_name` on every row so downstream tables can trace provenance

Relevant code:

- `crawler/app/client.py`
- `crawler/app/pipelines/bootstrap.py`
- `crawler/app/pipelines/incremental.py`
- `crawler/app/detail_fetcher.py`
- `crawler/app/sources.py`

## 2. Transform

The transform step converts each source detail page into a normalized listing record.

Current structured fields include:

- listing identity:
  - `source_name`
  - `source_post_id`
  - `canonical_url`
  - `content_hash`
- main listing data:
  - `title`
  - `price_text`
  - `price_value`
  - `area_text`
  - `area_m2`
  - `description`
- structured address:
  - `street_address`
  - `ward`
  - `district`
  - `province`
  - `full_address`
- contact data:
  - `contact_name`
  - `contact_phone`
  - `contact_zalo_url`
  - `contact_facebook_url`
- media and features:
  - `image_count`
  - `image_urls`
  - `amenities`
- lifecycle:
  - `posted_at`
  - `expired_at`

Transform rules:

- split `full_address` into street / ward / district / province when possible
- convert human-readable price into integer VND
- convert area text into numeric square meters
- flatten amenities and image URLs for CSV output
- compute `content_hash` for dedupe/change tracking

Relevant code:

- `crawler/app/extractors/phongtro123.py`
- `crawler/app/sources.py`
- `crawler/app/models.py`
- `crawler/app/tabular_export.py`

## 3. Output

Primary outputs:

- normalized JSON:
  - `crawler/artifacts/normalized/{source}/toan-quoc/page_*.json`
  - `crawler/artifacts/normalized/toan-quoc/incremental_latest.json`
- tabular CSV:
  - `crawler/artifacts/tabular/{source}/toan-quoc/page_*.csv`
  - `crawler/artifacts/tabular/{source}/toan-quoc/listings_all.csv`
  - `crawler/artifacts/tabular/toan-quoc/incremental_latest.csv`
  - `crawler/artifacts/tabular/toan-quoc/listings_all.csv`

Output policy:

- per-source CSV files are useful for source QA
- `tabular/toan-quoc/listings_all.csv` is the merged multi-source table
- JSON remains as normalized ETL output for downstream loading
- raw HTML is disabled by default

To re-enable raw HTML snapshots:

```powershell
PT_SAVE_RAW_HTML=true
```

## 4. Continuous backfill behavior

The hidden background crawler repeatedly runs:

```powershell
python -m app.main bootstrap-resume --city all --page-chunk 5 --max-detail-pages 20 --detail-workers 6
```

By default, bootstrap and incremental jobs run all configured sources:

```powershell
python -m app.main bootstrap --city all --max-pages 1 --max-detail-pages 2 --sources all
```

To limit a run to one or more sources:

```powershell
python -m app.main incremental --city all --pages 1 --max-detail-pages 5 --sources phongtro123,alonhadat,nhatot,batdongsan
```

Each loop:

1. Reads current state from `crawler/artifacts/state/bootstrap_toan-quoc.json`
2. Crawls the next chunk of pages
3. Writes normalized JSON + CSV outputs
4. Upserts records into each per-source table and the merged `crawler/artifacts/tabular/toan-quoc/listings_all.csv`
5. Advances `next_page`

## 5. When the crawl is finished

When `completed=true` in the bootstrap state file:

- historical backfill is complete
- the machine can continue relying on daily incremental runs
- `listings_all.csv` will contain the merged table built from all processed pages
