# Deploy Supabase + Vercel + GitHub Actions

Updated: 2026-07-15

Day la huong deploy chinh cua du an, khong dung AWS/GCP credit:

```text
Website nguon
  -> GitHub Actions crawler
  -> transform + data quality gate
  -> Supabase Postgres
  -> Supabase read-only view
  -> Next.js tren Vercel

GitHub Pages
  -> static index + lazy detail chunks
  -> fallback khi Supabase tam dung
```

Tin `expired` duoc giu lai co chu dich. Day la du an ETL, nen lich su ban ghi la du lieu phuc vu phan tich, khong phai loi can xoa.

## 1. Thanh phan su dung

- Supabase: Postgres va REST API cho serving layer.
- Vercel: deploy thu muc `web/`.
- GitHub Actions: nap snapshot day du, crawl dinh ky va upsert.
- GitHub Pages: fallback tinh, khong can database online.

Khong can Render/FastAPI cho luong chinh. Backend trong repo van dung cho local, migration va loader.

## 2. Bao ve chi phi

- Workflow crawl theo lich chi chay mot lan moi tuan.
- Moi lan incremental chi crawl 1 trang va toi da 5 trang chi tiet moi nguon.
- Ngan sach exact geocode mac dinh la 50 truy van moi.
- Ca truy van geocode khong co ket qua cung bi tinh vao ngan sach.
- Khong dung service role key trong frontend.
- Raw HTML va raw snapshots khong nap vao Supabase.

## 3. Tao Supabase project

1. Tao mot Supabase project.
2. Lay Project URL va anon public key trong Project Settings -> API.
3. Lay Postgres connection string trong Project Settings -> Database.
4. Connection string cho loader co dang:

```text
postgresql+psycopg://USER:PASSWORD@HOST:PORT/postgres?sslmode=require
```

Uu tien connection string do Supabase dashboard cung cap. Khong commit password vao repo.

## 4. Them GitHub secret

Vao GitHub repository -> Settings -> Secrets and variables -> Actions -> New repository secret:

```text
Name: SUPABASE_DB_URL
Value: postgresql+psycopg://...
```

Workflow khong can `SUPABASE_SERVICE_ROLE_KEY` vi no ket noi truc tiep bang Postgres URL.

## 5. Nap toan bo snapshot lan dau

Mo Actions -> Supabase ETL -> Run workflow, chon:

```text
run_mode=load_static_snapshot
```

Che do nay:

1. Doc `web/public/data/listings-map.json`.
2. Ghep tat ca index chunks va detail chunks.
3. Tao CSV day du trong runner.
4. Kiem tra toi thieu 50.000 dong.
5. Chan province rac, Zalo hotline, ID trung va toa do lech cap.
6. Upsert vao Supabase.
7. Apply read-only views/RLS.
8. Kiem tra Supabase co toi thieu 1.000 dong sau load.

Day la cach nap toan bo dataset ma khong can commit file CSV 100 MB vao Git.

## 6. Ba che do workflow

File workflow:

```text
.github/workflows/supabase-etl.yml
```

### `load_static_snapshot`

Dung cho lan nap dau hoac khi muon dong bo lai toan bo snapshot dang deploy tren GitHub Pages.

### `load_existing_csv`

Dung de test nhanh voi:

```text
crawler/artifacts/deploy/listings_deploy.csv
```

File nay la snapshot gon, khong phai toan bo du lieu.

### `crawl_then_load`

Dung cho incremental ETL:

```text
crawl -> transform -> validate -> upsert
```

Workflow da co lich:

```yaml
schedule:
  - cron: "17 3 * * 0"
```

Lich tren chay moi Chu Nhat theo UTC. Co the tat lich bang cach xoa block `schedule` ma khong anh huong manual run.

## 7. Data quality gate

Lenh dung trong workflow:

```powershell
cd crawler
python -m app.validate_curated `
  --csv artifacts/curated/toan-quoc/listings_curated.csv `
  --min-rows 1
```

Gate se fail khi:

- So dong thap hon nguong.
- `listing_id` bi trung.
- Status khong thuoc `active`, `expired`, `hidden`.
- Province khong thuoc danh muc hop le.
- Hotline cua website nguon bi gan nham thanh Zalo nguoi dang.
- Chi co latitude hoac longitude, khong co du cap.

## 8. Supabase public access

File:

```text
sql/supabase_views.sql
```

Nguyen tac hien tai:

- RLS bat tren `curated_listings`.
- `anon` va `authenticated` khong duoc SELECT truc tiep bang goc.
- Frontend chi doc `v_listing_map` va dashboard views.
- View map giu `active` va `expired`, loai `hidden`.
- `content_hash` khong duoc expose trong public view.

Kiem tra trong Supabase SQL Editor:

```sql
SELECT COUNT(*) FROM public.curated_listings;
SELECT status, COUNT(*)
FROM public.curated_listings
GROUP BY status
ORDER BY status;

SELECT source_name, COUNT(*)
FROM public.curated_listings
GROUP BY source_name
ORDER BY COUNT(*) DESC;

SELECT COALESCE(geocode_precision, 'none'), COUNT(*)
FROM public.curated_listings
GROUP BY 1
ORDER BY 2 DESC;
```

## 9. Deploy Vercel

1. Import GitHub repository vao Vercel.
2. Dat Root Directory:

```text
web
```

3. Them environment variables:

```text
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-public-key>
NEXT_PUBLIC_SUPABASE_LISTINGS_VIEW=v_listing_map
NEXT_PUBLIC_SUPABASE_PAGE_SIZE=1000
NEXT_PUBLIC_SUPABASE_MAX_ROWS=60000
```

Khong them cac bien sau vao Vercel frontend:

```text
SUPABASE_DB_URL
SUPABASE_SERVICE_ROLE_KEY
Database password
```

4. Deploy va mo URL Vercel.
5. Kiem tra ba tab Ban do du lieu, Phan tich du lieu va Tien trinh ETL.
6. Mo DevTools Network de xac nhan request den `/rest/v1/v_listing_map` tra ve 200.

## 10. Static fallback

Static export khong con tai mo ta va lien he cua moi tin ngay khi vao trang.

```text
listings-map.json
  -> listings-map-chunks/       index nhe cho map/filter/chart
  -> listings-map-details/      chi tai chunk khi mo chi tiet
```

Xuat lai snapshot:

```powershell
cd D:\UNIVERSITY\Cap2
powershell -ExecutionPolicy Bypass -File crawler\scripts\export_static_map.ps1
```

Build GitHub Pages:

```powershell
cd web
$env:GITHUB_PAGES="true"
npm run build:pages
```

## 11. Kiem tra truoc khi push

```powershell
cd D:\UNIVERSITY\Cap2
$env:PYTHONPATH="crawler"
python -m unittest discover -s crawler/tests -v
python -m compileall -q crawler/app backend/app

cd web
npm run lint
npx tsc --noEmit
$env:GITHUB_PAGES="true"
npm run build
```

Tat ca lenh tren phai xanh. `npm audit --omit=dev` phai khong co vulnerability.

## 12. Rollback

Neu Supabase loi:

- Xoa hai bien `NEXT_PUBLIC_SUPABASE_*` tren Vercel va redeploy de frontend dung static fallback.
- Hoac mo truc tiep GitHub Pages.

Neu crawl dinh ky loi:

- Tat `schedule` tam thoi.
- Chay lai `load_static_snapshot` de khoi phuc snapshot da kiem chung.
- Khong xoa bang Supabase; loader dang upsert, khong truncate.

## 13. Definition of Done

- Workflow `load_static_snapshot` xanh.
- Supabase co tren 50.000 ban ghi.
- Public anon khong doc truc tiep duoc `curated_listings`.
- `v_listing_map` doc duoc active + expired va khong co hidden.
- Khong con Zalo hotline chung trong contact.
- Province rac bang 0.
- Vercel hien map, danh sach, lazy detail, dashboard phan tich va so do tien trinh ETL.
- GitHub Pages fallback build xanh.
- Lint, TypeScript, Python tests va dependency audit deu xanh.
