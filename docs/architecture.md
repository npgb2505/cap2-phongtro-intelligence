# Architecture

## Product goals

The platform is optimized for data acquisition and reliable retrieval rather than academic-only analysis.

Core outcomes:

- ingest as many listing fields as possible from Phongtro123
- preserve raw evidence for replay and auditing
- support incremental daily refresh
- expose listings on an interactive nationwide map
- keep infrastructure lean enough to fit AWS credits

## Source survey findings

From the current Phongtro123 pages, the platform can extract at least:

- listing title
- canonical URL
- source post id
- price text and normalized price
- area text and normalized area
- district and province
- full address
- description paragraphs
- posted date
- expiration date
- image count and image URLs
- amenity badges
- contact name
- contact phone
- Zalo link
- author profile hints such as join date and listing count
- breadcrumb metadata
- JSON-LD metadata
- map embed URL
- related listings for local context

## Architecture decisions

### Bootstrap locally first

The first crawl is large and exploratory. Running it locally reduces AWS cost and allows frequent parser iteration.

### Cloud only for incremental sync

After the initial load, AWS runs only incremental daily sync. That makes credit usage predictable.

### Raw, staging, curated layers

We keep:

- `raw` for exact snapshots and replayability
- `staging` for parser and normalization work
- `curated` for serving the app and analytics later

### Geo-first serving model

Listings are primarily consumed on a map. The curated model therefore stores geometry as a first-class field.

## Service design

### Crawler

Responsibilities:

- fetch search pages and detail pages
- parse structured fields
- persist raw artifacts
- emit normalized listing payloads
- detect inserts, updates, and expirations

Modes:

- `bootstrap`
- `incremental`
- `reparse`

### API

Responsibilities:

- list listings by bbox
- filter by province, district, price range, area range, amenities
- fetch listing details
- expose health and sync metadata

### Frontend

Responsibilities:

- render clustered markers
- show sidebar results
- render detail popup/cards
- support filter-driven map exploration

## Data model summary

Main tables:

- `listings`
- `listing_images`
- `listing_amenities`
- `listing_contacts`
- `crawl_runs`
- `crawl_observations`
- `raw_snapshots`
- `geocode_cache`

## Incremental strategy

We treat a listing as:

- `new` when source post id not found
- `updated` when content hash changed
- `expired` when source marks it expired or it disappears across enough consecutive syncs
- `seen` when unchanged but still active

Hash inputs:

- title
- price
- area
- address
- description
- amenities
- contact info
- image URL set

## Cost control

- bootstrap runs local only
- incremental sync once per day by default
- raw snapshots compressed before upload
- image binaries not mirrored in v1, only URLs and metadata
- bbox queries backed by spatial indexes

## Security and governance

- secrets loaded from environment or AWS Secrets Manager
- crawler user agents and rate limit configured centrally
- each crawl run logged with run id and status
- raw snapshots retained for debugging parser drift
