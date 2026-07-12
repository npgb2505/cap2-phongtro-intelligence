# Deploy Supabase + Vercel + GitHub Actions

Updated: 2026-07-12

Tai lieu nay la huong deploy chinh moi cho du an sau khi khong dung duoc AWS credit va khong dang ky duoc GCP free trial.

Muc tieu:

- Supabase lam database Postgres chinh.
- Vercel deploy frontend Next.js.
- GitHub Actions chay crawler/ETL va upsert du lieu vao Supabase.
- GitHub Pages/static JSON van la fallback khi Supabase bi pause/gioi han.

Kien truc:

```text
Source websites
  -> GitHub Actions crawler/ETL
  -> curated CSV
  -> backend/app/load_curated.py
  -> Supabase Postgres curated_listings
  -> Supabase views/RPC read-only
  -> Vercel Next.js frontend
```

## 1. Ly do chon stack nay

Huong nay phu hop nhat voi bai ETL hien tai vi diem kho khong nam o viec van hanh backend rieng, ma nam o:

- Co database cloud de luu `curated_listings`.
- Co job dinh ky de nap du lieu moi.
- Co frontend online doc du lieu va ve dashboard/map.

Supabase giai quyet database va API doc du lieu. Vercel giai quyet frontend. GitHub Actions giai quyet crawler/ETL. FastAPI/Render chi can dung sau nay neu Supabase views/RPC khong du.

## 2. Gioi han free tier can nho

Theo pricing/docs hien tai:

- Supabase Free co 500 MB database size, 5 GB egress, 1 GB file storage, va free projects co the pause sau 1 tuan khong hoat dong.
- Vercel Hobby free cho personal/small-scale projects, co gioi han usage hang thang va khong phu hop chay crawler nang.
- GitHub Actions co the chay `workflow_dispatch` va `schedule`; voi public repo, standard GitHub-hosted runners duoc tinh free theo docs billing hien tai.

Nguon chinh thuc:

- Supabase pricing: https://supabase.com/pricing
- Supabase billing: https://supabase.com/docs/guides/platform/billing-on-supabase
- Supabase project pausing: https://supabase.com/docs/guides/platform/free-project-pausing
- Vercel Hobby: https://vercel.com/docs/plans/hobby
- GitHub Actions billing: https://docs.github.com/billing/managing-billing-for-github-actions/about-billing-for-github-actions
- GitHub Actions schedule: https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions#onschedule

## 3. Supabase project setup

1. Tao Supabase project Free.
2. Vao Project Settings -> API, lay:
   - Project URL.
   - anon public key.
3. Vao Project Settings -> Database, lay connection string Postgres.
4. Neu dung SQLAlchemy/psycopg trong repo nay, connection string nen co dang:

```text
postgresql+psycopg://USER:PASSWORD@HOST:PORT/postgres?sslmode=require
```

Dung pooler/session string neu Supabase khuyen nghi cho external clients.

## 4. Secrets bat buoc

GitHub Actions secret bat buoc cho workflow hien tai:

```text
SUPABASE_DB_URL=postgresql+psycopg://...
```

`SUPABASE_URL` va `SUPABASE_SERVICE_ROLE_KEY` chi can them sau neu viet job goi Supabase API truc tiep. Workflow hien tai apply SQL va load CSV bang Postgres connection string, nen khong can service role key.

Vercel environment variables:

```text
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-public-key>
```

Tuyet doi khong dua cac gia tri sau vao frontend, repo, README public, screenshot, hoac bien `NEXT_PUBLIC_*`:

```text
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_DB_URL
Database password
```

## 5. Schema toi thieu

Repo da co:

```text
sql/schema.sql
sql/supabase_views.sql
backend/app/load_curated.py
backend/app/apply_sql.py
backend/app/check_supabase_load.py
.github/workflows/supabase-etl.yml
web/lib/api.ts
web/env.vercel.example
```

Loader hien co co the tao `curated_listings` va upsert CSV.
`backend/app/apply_sql.py` co the apply `sql/schema.sql` va `sql/supabase_views.sql` bang `PT_DATABASE_URL`.
`backend/app/check_supabase_load.py` kiem tra count cua bang va views sau khi workflow load xong.
Frontend loader hien co uu tien Supabase neu co `NEXT_PUBLIC_SUPABASE_URL` va `NEXT_PUBLIC_SUPABASE_ANON_KEY`, sau do fallback ve API cu hoac static JSON.

Trong Supabase SQL Editor, chay toi thieu:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

Sau do co 2 cach:

1. Chay `sql/schema.sql` trong SQL Editor.
2. Hoac de `backend/app/load_curated.py` tao bang `curated_listings` khi load CSV lan dau.

Sau khi `curated_listings` ton tai, chay:

```sql
-- Noi dung nam trong sql/supabase_views.sql
```

File nay tao views read-only cho frontend:

```sql
CREATE OR REPLACE VIEW public.v_listing_map AS
SELECT
  listing_id AS id,
  source_name,
  source_post_id,
  canonical_url,
  title,
  title AS title_raw,
  status,
  room_type,
  furnishing_level,
  price_text,
  price_value,
  price_per_m2,
  area_text,
  area_m2,
  street_address,
  ward,
  full_address,
  map_reference_address,
  district,
  province,
  latitude,
  longitude,
  geocode_precision,
  geocode_source,
  geocode_display_name,
  is_reference_coordinate,
  address_quality_score,
  record_completeness_score,
  image_count,
  primary_image_url,
  primary_image_url AS thumbnail_url,
  amenities_text,
  amenity_count,
  description_clean,
  updated_at
FROM public.curated_listings;

CREATE OR REPLACE VIEW public.v_dashboard_source_stats AS
SELECT
  source_name,
  COUNT(*) AS listing_count,
  COUNT(*) FILTER (WHERE latitude IS NOT NULL AND longitude IS NOT NULL) AS geocoded_count,
  ROUND(AVG(price_value)) AS avg_price,
  ROUND(AVG(area_m2)::numeric, 2) AS avg_area_m2
FROM public.curated_listings
WHERE status = 'active'
GROUP BY source_name;

GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON public.curated_listings TO anon, authenticated;
GRANT SELECT ON public.v_listing_map TO anon, authenticated;
GRANT SELECT ON public.v_dashboard_source_stats TO anon, authenticated;
GRANT SELECT ON public.v_dashboard_location_stats TO anon, authenticated;
```

## 6. RLS va public read

Khuyen nghi:

- Bat RLS tren bang goc neu frontend doc truc tiep.
- Tot hon: frontend doc views/RPC read-only, chi expose truong can hien thi.
- Service role key bo qua RLS nen chi dung trong GitHub Actions.

Policy don gian cho doc public bang goc:

```sql
ALTER TABLE public.curated_listings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public read listings"
ON public.curated_listings
FOR SELECT
TO anon
USING (true);

GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON public.curated_listings TO anon, authenticated;
GRANT SELECT ON public.v_listing_map TO anon, authenticated;
```

Neu muon chat hon, khong cho frontend doc bang goc; tao RPC/view rieng va chi grant SELECT tren view. Neu chi muon hien tin dang con active, doi policy/view ve `status = 'active'`.

## 7. Load local truoc khi dua len Actions

Test compact CSV truoc:

```powershell
cd D:\UNIVERSITY\Cap2\backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .

$env:PT_DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST:PORT/postgres?sslmode=require"
python -m app.load_curated --csv ..\crawler\artifacts\deploy\listings_deploy.csv
```

Neu compact CSV on, moi load full curated:

```powershell
$env:PT_DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST:PORT/postgres?sslmode=require"
python -m app.load_curated --csv ..\crawler\artifacts\curated\toan-quoc\listings_curated.csv
```

Kiem tra trong Supabase SQL Editor:

```sql
SELECT COUNT(*) FROM public.curated_listings;
SELECT source_name, COUNT(*) FROM public.curated_listings GROUP BY source_name ORDER BY COUNT(*) DESC;
SELECT COALESCE(geocode_precision, 'none'), COUNT(*) FROM public.curated_listings GROUP BY 1 ORDER BY 2 DESC;
```

## 8. GitHub Actions workflow mau

Repo da co workflow manual-only:

```text
.github/workflows/supabase-etl.yml
```

Workflow co 2 che do:

- `load_existing_csv`: mac dinh, load CSV co san, an toan nhat de test Supabase.
- `crawl_then_load`: chay incremental crawler nho, transform curated, roi load CSV moi vao Supabase.

No co noi dung tuong duong:

```yaml
name: Supabase ETL

on:
  workflow_dispatch:
    inputs:
      run_mode:
        description: "Use load_existing_csv for safe deploy, or crawl_then_load for incremental crawl before loading"
        required: true
        default: "load_existing_csv"
      csv_path:
        description: "Curated CSV path"
        required: false
        default: "crawler/artifacts/deploy/listings_deploy.csv"
      city:
        required: false
        default: "all"
      pages:
        required: false
        default: "1"
      max_detail_pages:
        required: false
        default: "5"
      sources:
        required: false
        default: "phongtro123,nhatot,mogi"
      exact_geocode_limit:
        required: false
        default: "0"

concurrency:
  group: supabase-etl
  cancel-in-progress: false

jobs:
  load:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Check required Supabase secret
        env:
          SUPABASE_DB_URL: ${{ secrets.SUPABASE_DB_URL }}
        run: |
          if [ -z "$SUPABASE_DB_URL" ]; then
            echo "Missing GitHub Actions secret: SUPABASE_DB_URL"
            exit 1
          fi

      - name: Install backend
        working-directory: backend
        run: pip install -e .

      - name: Apply base Supabase schema
        working-directory: backend
        env:
          PT_DATABASE_URL: ${{ secrets.SUPABASE_DB_URL }}
        run: python -m app.apply_sql --file ../sql/schema.sql

      - name: Install crawler
        if: ${{ inputs.run_mode == 'crawl_then_load' }}
        working-directory: crawler
        run: pip install -e .

      - name: Run incremental crawler
        if: ${{ inputs.run_mode == 'crawl_then_load' }}
        working-directory: crawler
        run: python -m app.main incremental --city "${{ inputs.city }}" --pages "${{ inputs.pages }}" --max-detail-pages "${{ inputs.max_detail_pages }}" --sources "${{ inputs.sources }}"

      - name: Build curated dataset
        if: ${{ inputs.run_mode == 'crawl_then_load' }}
        working-directory: crawler
        run: python -m app.main transform-curated --exact-geocode-limit "${{ inputs.exact_geocode_limit }}"

      - name: Load curated CSV into Supabase
        working-directory: backend
        env:
          PT_DATABASE_URL: ${{ secrets.SUPABASE_DB_URL }}
        run: |
          if [ "${{ inputs.run_mode }}" = "crawl_then_load" ]; then
            python -m app.load_curated --csv ../crawler/artifacts/curated/toan-quoc/listings_curated.csv
          else
            python -m app.load_curated --csv ../${{ inputs.csv_path }}
          fi

      - name: Apply Supabase views and RLS
        working-directory: backend
        env:
          PT_DATABASE_URL: ${{ secrets.SUPABASE_DB_URL }}
        run: python -m app.apply_sql --file ../sql/supabase_views.sql

      - name: Verify Supabase load
        working-directory: backend
        env:
          PT_DATABASE_URL: ${{ secrets.SUPABASE_DB_URL }}
        run: python -m app.check_supabase_load --min-rows 1
```

Sau khi workflow manual chay on moi them schedule:

```yaml
on:
  workflow_dispatch:
  schedule:
    - cron: "0 19 * * *"
```

Gio tren GitHub Actions la UTC. `0 19 * * *` tuong duong khoang 02:00 sang gio Viet Nam.

## 9. Vercel deploy

1. Import repo vao Vercel.
2. Root Directory:

```text
web
```

3. Set env:

```text
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-public-key>
NEXT_PUBLIC_SUPABASE_LISTINGS_VIEW=v_listing_map
NEXT_PUBLIC_SUPABASE_PAGE_SIZE=1000
NEXT_PUBLIC_SUPABASE_MAX_ROWS=60000
```

4. Deploy.

`web/lib/api.ts` hien uu tien doc Supabase REST API khi co env tren. Neu Supabase loi/pause hoac chua set env, frontend se fallback ve `NEXT_PUBLIC_API_URL` cu hoac static JSON chunks. Nguyen tac:

- Dashboard query aggregate views.
- Map query `v_listing_map` co paging/limit.
- Detail doc tu `v_listing_map` vi view da expose cac truong chinh ma UI can.
- Neu Supabase loi/pause, fallback ve static JSON chunks.

## 10. Chien luoc giu trong 500 MB

Nen luu:

- ID, source, URL.
- Title, gia, dien tich.
- Dia chi da chuan hoa.
- Toa do va geocode precision.
- Amenity booleans.
- Score chat luong.
- Anh dai dien URL.

Han che hoac cat ngan:

- `description_clean` qua dai.
- Raw HTML.
- Full image arrays.
- Raw snapshots.
- Log chi tiet cua moi request.

Raw artifacts nen de local, GitHub artifacts, hoac release assets; khong day het vao Supabase Free.

## 11. Definition of Done cho huong nay

Huong Supabase/Vercel/GitHub Actions chi xem la xong khi co bang chung:

- Supabase co bang `curated_listings`.
- Load compact CSV thanh cong va co count trong SQL.
- RLS/policy hoac views read-only da duoc cau hinh.
- GitHub Actions manual workflow chay xanh it nhat mot lan.
- Workflow smoke check `python -m app.check_supabase_load --min-rows 1` tra ve `status=ok`.
- Vercel deploy frontend thanh cong.
- Frontend doc duoc Supabase hoac fallback static JSON.
- Khong co `SUPABASE_SERVICE_ROLE_KEY` trong repo/frontend/public env.
- Da ghi lai URL Vercel, Supabase project ref, env vars can set, va lenh rollback/fallback.
