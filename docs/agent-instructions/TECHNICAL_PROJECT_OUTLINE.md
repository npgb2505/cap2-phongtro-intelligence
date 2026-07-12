# Suon ky thuat hoan chinh - PhongTro Intelligence Platform

Tai lieu nay la ban do ky thuat chi tiet cho du an ETL du lieu phong tro. Agent moi khi tiep quan du an phai doc file nay de hieu muc tieu, kien truc, du lieu, pipeline, frontend, deploy va cac tieu chi hoan thanh.

## 1. Muc tieu san pham

Du an xay dung mot nen tang du lieu phong tro theo huong ETL thuc te:

- Thu thap tin phong tro tu nhieu nguon web.
- Giu lai cang nhieu truong thong tin cang tot de phuc vu phan tich.
- Chuan hoa du lieu tho thanh dataset co cau truc.
- Lam giau toa do de hien thi ban do.
- Xuat du lieu thanh static JSON chunks de deploy mien phi/gan mien phi.
- Hien thi tren giao dien Next.js co ban do, danh sach tin, chi tiet tin va dashboard phan tich.
- Bao cao du an theo huong ETL, co so lieu, hinh anh, code minh hoa va ket qua kiem thu.

Gia tri chinh cua du an khong nam o viec "crawl ve that nhieu HTML", ma nam o kha nang bien du lieu ban cau truc, nhieu loi va khong dong nhat thanh mot san pham phan tich co the su dung.

## 2. Hien trang da biet

Ten du an: `PhongTro Intelligence Platform`

Thu muc goc: `D:\UNIVERSITY\Cap2`

Repo chinh gom:

```text
backend/     FastAPI service va loader du lieu curated
crawler/     ETL crawler, transform, geocoding, static export
docs/        Tai lieu ky thuat, bao cao, huong dan deploy
infra/       Docker Compose, Terraform/AWS skeleton
sql/         Schema database
web/         Next.js frontend, ban do, dashboard
```

Trang GitHub Pages static da duoc dung lam huong deploy khong dung AWS credit:

```text
https://npgb2505.github.io/cap2-phongtro-intelligence/
```

Huong cloud/free duoc uu tien sau cap nhat 2026-07-12:

```text
Primary no-GCP/no-AWS path
  -> Supabase Free Postgres cho curated_listings va dashboard views
  -> Vercel Hobby cho Next.js frontend
  -> GitHub Actions manual/schedule cho crawler ETL va upsert Supabase
  -> GitHub repository artifacts hoac release assets cho static JSON fallback
  -> Secrets nam trong GitHub Actions va Vercel
```

Ly do chon Supabase + Vercel + GitHub Actions lam mac dinh:

- Nguoi dung khong dang ky duoc GCP free trial.
- AWS credit da het nen khong dung AWS lam mac dinh.
- Van de chinh cua du an la database va nap du lieu vao database, dung Supabase la dung tam.
- Supabase Free co Postgres, API tu dong, PostGIS co the bat bang extension va phu hop dashboard/map.
- Vercel Hobby phu hop deploy Next.js frontend, khong nen dung de chay crawler nang.
- GitHub Actions co manual trigger va schedule, phu hop chay ETL roi upsert vao Supabase.
- Khong can backend FastAPI rieng trong giai doan dau; neu can logic phuc tap co the them sau.

Nguon pricing/docs can tham chieu khi deploy that:

- Supabase pricing: https://supabase.com/pricing
- Supabase billing: https://supabase.com/docs/guides/platform/billing-on-supabase
- Supabase free project pausing: https://supabase.com/docs/guides/platform/free-project-pausing
- Vercel Hobby plan: https://vercel.com/docs/plans/hobby
- GitHub Actions billing: https://docs.github.com/billing/managing-billing-for-github-actions/about-billing-for-github-actions
- GitHub Actions schedule: https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions#onschedule
- GitHub Pages docs: https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages

So lieu static export da xac nhan:

| Chi so | Gia tri |
|---|---:|
| Tong tin hop le | 56.061 |
| Tin tra ve online | 56.061 |
| JSON chunks | 12 |
| Dong CSV bi loai khi export | 1 |
| Tin co marker ban do | 55.919 |
| Tin chua co toa do | 142 |

Phan bo nguon du lieu:

| Nguon | So tin |
|---|---:|
| phongtro123 | 44.851 |
| nhatot | 10.065 |
| mogi | 1.005 |
| thuephongtro | 84 |
| batdongsan | 35 |
| alonhadat | 21 |

Tom tat geocode:

| Muc geocode | So tin | Y nghia |
|---|---:|---|
| exact | 10.098 | Toa do gan sat dia chi |
| district | 45.819 | Toa do tham chieu cap quan/huyen |
| province | 2 | Toa do tham chieu cap tinh/thanh |
| none | 142 | Chua dinh vi |

## 3. Kien truc tong quan

Kien truc hien tai co the hieu theo cac lop:

```text
Source websites / APIs
  -> Extract adapters
  -> Normalized JSON / tabular CSV
  -> Curated dataset
  -> Geocoding + quality scoring
  -> Static export manifest + JSON chunks
  -> Next.js GitHub Pages frontend
  -> Map, listing explorer, dashboard
```

Khi chay local day du hon:

```text
Crawler
  -> raw / normalized artifacts
  -> curated CSV
  -> optional PostgreSQL load
  -> FastAPI backend
  -> Next.js frontend
```

Khi deploy mien phi/gan mien phi:

```text
Curated CSV
  -> crawler/app/static_map_export.py
  -> web/public/data/listings-map.json
  -> web/public/data/listings-map-chunks/part-000.json ... part-011.json
  -> GitHub Pages
  -> frontend doc static JSON
```

Khi deploy cloud/free khong dung GCP:

```text
GitHub Actions schedule/manual
  -> crawler ETL/export nhe
  -> curated CSV/JSON
  -> upsert Supabase Postgres
  -> Supabase read-only API / SQL views
  -> Vercel Hobby Next.js frontend
  -> GitHub Pages static fallback neu can
```

## 4. Cac thanh phan ky thuat

### 4.1. Crawler

Thu muc chinh:

```text
crawler/app/
```

Vai tro:

- Lay search pages va detail pages.
- Chay adapter theo tung nguon.
- Tao normalized records.
- Tao tabular CSV.
- Chay bootstrap va incremental.
- Static export du lieu cho frontend.

File quan trong:

| File | Vai tro |
|---|---|
| `crawler/app/main.py` | CLI entrypoint cho bootstrap, incremental, transform/export |
| `crawler/app/pipelines/bootstrap.py` | Flow crawl ban dau |
| `crawler/app/pipelines/incremental.py` | Flow crawl cap nhat |
| `crawler/app/detail_fetcher.py` | Lay detail page dong thoi |
| `crawler/app/sources.py` | Dang ky nguon va adapter |
| `crawler/app/models.py` | Model du lieu trung gian |
| `crawler/app/tabular_export.py` | Xuat CSV |
| `crawler/app/curation.py` | Chuan hoa/curated dataset |
| `crawler/app/static_map_export.py` | Tao manifest va JSON chunks cho frontend |

Nguon dang ho tro:

- `phongtro123`
- `nhatot`
- `mogi`
- `thuephongtro`
- `batdongsan`
- `alonhadat`

### 4.2. Backend

Thu muc chinh:

```text
backend/app/
```

Vai tro:

- FastAPI service.
- Health endpoint.
- Listing API.
- Loader curated data vao database local/cloud.

File quan trong:

| File | Vai tro |
|---|---|
| `sql/schema.sql` | Schema PostgreSQL/PostGIS nen tang |
| `sql/supabase_views.sql` | Views/RLS mau cho Supabase frontend read-only |
| `backend/app/main.py` | FastAPI app |
| `backend/app/config.py` | Cau hinh runtime |
| `backend/app/db.py` | Ket noi database |
| `backend/app/apply_sql.py` | Apply SQL schema/views vao Supabase/Postgres |
| `backend/app/load_curated.py` | Nap curated data |
| `backend/app/check_supabase_load.py` | Kiem tra row count va views sau khi load Supabase |
| `backend/app/api/routes/listings.py` | API listing/map |
| `backend/app/services/listing_service.py` | Logic truy van listing |

Backend FastAPI la thanh phan tuy chon sau nay, khong phai mac dinh. Voi huong Supabase, frontend Next.js tren Vercel co the doc Supabase read-only API/views truc tiep bang anon key va RLS phu hop; GitHub Actions mac dinh dung `SUPABASE_DB_URL` de apply SQL va upsert du lieu. Service role key chi can sau nay neu viet job goi Supabase API truc tiep. Neu can logic server-side phuc tap, luc do moi them FastAPI hoac Vercel API routes.

### 4.3. Frontend

Thu muc chinh:

```text
web/
```

Vai tro:

- Next.js frontend.
- Doc static manifest va chunks.
- Hien thi ban do Leaflet.
- Hien thi danh sach tin, chi tiet tin, bo loc.
- Dashboard phan tich KPI va bieu do.

File quan trong:

| File | Vai tro |
|---|---|
| `web/app/page.tsx` | Trang chinh |
| `web/components/listings-explorer.tsx` | UI map/list/dashboard chinh |
| `web/components/listings-map.tsx` | Thanh phan ban do |
| `web/lib/api.ts` | Uu tien fetch Supabase REST view, fallback FastAPI/static manifest va chunks |
| `web/lib/types.ts` | Kieu du lieu |
| `web/env.vercel.example` | Mau env public cho Vercel/Supabase |
| `web/public/data/listings-map.json` | Manifest static |
| `web/public/data/listings-map-chunks/` | Full dataset chia chunk |

Cac hang so frontend quan trong:

```ts
const RESULT_BATCH_SIZE = 500;
const INITIAL_MAP_MARKER_LIMIT = 1500;
const MAP_MARKER_BATCH_SIZE = 1500;
```

Ly do: dataset lon, khong nen ve toan bo marker ngay lan dau.

## 5. Luong ETL chi tiet

### 5.1. Extract

Muc tieu:

- Lay du lieu tu search result pages, detail pages, JSON APIs.
- Giu `source_name` tren moi ban ghi.
- Giu URL goc va ID nguon de truy vet.

Du lieu dau vao:

- HTML search pages.
- HTML detail pages.
- JSON API response.
- Mobile/map API encoded response.

Output mong doi:

- Normalized JSON theo nguon.
- CSV theo nguon.
- Merged CSV toan quoc.

### 5.2. Transform

Muc tieu:

- Chuan hoa gia ve VND.
- Chuan hoa dien tich ve m2.
- Tach dia chi thanh street/ward/district/province.
- Nhan dien room type, furnishing, amenities.
- Tao content hash.
- Tinh record completeness score.

Truong can giu:

| Nhom | Truong tieu bieu |
|---|---|
| Dinh danh | `listing_id`, `source_name`, `source_post_id`, `canonical_url`, `content_hash` |
| Noi dung | `title`, `title_raw`, `description_clean`, `status` |
| Gia | `price_text`, `price_value`, `price_per_m2` |
| Dien tich | `area_text`, `area_m2` |
| Dia chi | `street_address`, `ward`, `district`, `province`, `full_address` |
| Toa do | `latitude`, `longitude`, `geocode_precision`, `geocode_source`, `geocode_display_name` |
| Lien he | `contact_name`, `contact_phone`, `contact_zalo_url`, `contact_facebook_url` |
| Anh | `image_count`, `primary_image_url`, `thumbnail_url` |
| Tien ich | `has_aircon`, `has_private_wc`, `has_loft`, `has_parking`, `has_security`, `has_kitchen`, `has_fridge`, `has_washer` |
| Chat luong | `record_completeness_score`, `address_quality_score`, `is_reference_coordinate` |

### 5.3. Geocoding

Muc tieu:

- Chuyen dia chi thanh `latitude` va `longitude`.
- Neu khong co dia chi chi tiet, fallback ve toa do quan/huyen hoac tinh/thanh.
- Khong danh dong moi toa do la chinh xac.

Phan loai:

| Precision | Y nghia |
|---|---|
| `exact` | Gan sat dia chi |
| `district` | Toa do tham chieu quan/huyen |
| `province` | Toa do tham chieu tinh/thanh |
| `none` | Chua co toa do |

Frontend va bao cao phai luon dien giai `district`/`province` la toa do tham chieu, khong phai vi tri nha chinh xac.

### 5.4. Load/Serving

Ba huong load:

1. Local/backend:
   - Load vao PostgreSQL.
   - FastAPI query.
   - Phu hop mo rong backend.

2. Supabase cloud:
   - Load/upsert vao Supabase Postgres.
   - Tao views/RPC cho map va dashboard.
   - Frontend Vercel doc bang anon key read-only hoac API route.
   - Phu hop huong deploy chinh vi van co database that.

3. Free static:
   - Export manifest + chunks.
   - Deploy GitHub Pages.
   - Phu hop khi khong dung AWS credit.

Manifest static can co:

```json
{
  "total": 56061,
  "returned": 56061,
  "geocode_summary": {},
  "deploy_source_counts": {},
  "skipped_rows": 1,
  "chunks": [
    "listings-map-chunks/part-000.json"
  ],
  "chunk_size": 5000,
  "dataset_mode": "chunked-full"
}
```

## 6. Huong deploy

### 6.1. Huong uu tien: Supabase + Vercel + GitHub Actions

Dung khi:

- Nguoi dung khong dang ky duoc GCP free trial.
- Can cloud online nhung van free/near-free va tranh AWS.
- Can database Postgres that de frontend/dashboard query.
- Van de chinh la ETL nap du lieu vao database, khong phai van hanh backend rieng.

Stack de xuat:

| Lop | Cong cu | Vai tro |
|---|---|---|
| Frontend | Vercel Hobby | Host Next.js dashboard/map |
| Database | Supabase Free Postgres | Luu `curated_listings`, dashboard aggregates, crawl logs |
| Geospatial | Supabase Postgres + PostGIS extension | Query toa do, bounding box, heatmap neu can |
| Data API | Supabase REST/RPC/views | Frontend doc read-only bang anon key/RLS |
| ETL batch | GitHub Actions manual/schedule | Chay crawler/export/upsert Supabase |
| ETL workflow | `.github/workflows/supabase-etl.yml` | Manual workflow co 2 che do, tu apply schema -> load -> apply views/RLS |
| Supabase smoke check | `backend/app/check_supabase_load.py` | Kiem row count cua `curated_listings` va `v_listing_map` sau khi load |
| Supabase SQL | `sql/supabase_views.sql` | Views map/dashboard/RLS, `v_listing_map` tra dung shape frontend |
| Static artifacts | GitHub repo/release artifacts | Luu manifest va JSON chunks |
| Secrets | GitHub Actions secrets + Vercel env | GitHub Actions luu `SUPABASE_DB_URL`; Vercel chi luu `NEXT_PUBLIC_SUPABASE_URL` va anon key |
| Logs | GitHub Actions logs + Supabase logs | Debug ETL/query |
| Fallback | GitHub Pages static | Demo khi Supabase bi pause/gioi han |

Thu tu deploy an toan:

1. Giu GitHub Pages/static JSON la baseline an toan de demo du lieu.
2. Tao Supabase project Free va bat extension can thiet, toi thieu `postgis` neu query ban do nang.
3. Tao schema `curated_listings`, `crawl_runs`, `source_stats`, va views/RPC cho map/dashboard; workflow co the apply `sql/schema.sql` va `sql/supabase_views.sql` tu dong.
4. Load compact CSV truoc, vi du 3.000-5.000 tin, de test schema, RLS, dashboard.
5. Tao GitHub Actions workflow manual-only de load CSV co san; neu can crawl thi dung mode `crawl_then_load` voi pages/detail thap.
6. Deploy frontend len Vercel Hobby, dat `NEXT_PUBLIC_SUPABASE_URL` va `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
7. Test frontend query Supabase, dashboard, map marker va fallback static JSON.
8. Chi bat `schedule` sau khi manual job on, bat dau tan suat thap.
9. Khi Supabase gan gioi han Free, giam truong text lon, dung aggregate views, hoac quay ve static chunks cho ban do.

Ranh gioi chi phi:

- Supabase Free co gioi han database/storage/egress va co the pause sau thoi gian khong hoat dong; khong load raw HTML/anh vao DB.
- Service role key chi nam trong GitHub Actions secrets, khong bao gio dua vao frontend/Vercel public env.
- Frontend chi dung anon key va RLS read-only; neu can ghi/sua du lieu phai qua workflow hoac server-side protected route.
- Vercel Hobby dung cho personal/small-scale project; tranh chay crawler hoac job nang tren Vercel.
- GitHub Actions schedule nen chay job nhe, khong crawl qua lon lien tuc.

### 6.2. Huong fallback re nhat: GitHub Pages

Dung khi:

- Nguoi dung khong muon ton AWS credit.
- Nguoi dung khong dang ky duoc GCP hoac muon tam dung cloud DB.
- Chi can demo giao dien + dataset static.
- Chap nhan khong co backend query server-side.

Thanh phan:

- `.github/workflows/pages.yml`
- `web/public/data/listings-map.json`
- `web/public/data/listings-map-chunks/`
- `NEXT_PUBLIC_STATIC_DATA_PATH`
- `GITHUB_PAGES=true`

### 6.3. Huong GCP

Dung khi:

- Chi khi sau nay nguoi dung dang ky duoc GCP free trial hoac co billing chu dong.
- Muon Cloud Run/Cloud SQL/Cloud Scheduler de lam kien truc cloud managed.
- Phai co budget alert truoc khi tao resource chay lien tuc.

Can doc:

- `docs/gcp-cloud-deployment.md` neu da duoc tao.
- Pricing Google Cloud chinh thuc truoc khi deploy that.

### 6.4. Huong Neon/Render

Chi dung neu Supabase khong phu hop hoac nguoi dung doi:

- Neon Free Postgres thay Supabase database.
- Render Free Web Service chay FastAPI backend.
- Vercel/GitHub Pages frontend.

Can doc:

- `docs/cloud-option-2-neon-render-vercel.md`
- `render.yaml`
- `render.neon.yaml`

### 6.5. Huong AWS

Chi dung khi nguoi dung xac nhan co credit va muon dung AWS:

- S3 cho raw artifacts.
- RDS PostgreSQL.
- ECS Fargate crawler jobs.
- EventBridge Scheduler.
- Secrets Manager.
- CloudWatch.

Can doc:

- `infra/aws/README.md`
- `docs/cloud-deployment-flow.md`
- `docs/free-deployment.md`

Mac dinh hien tai:

- Neu nguoi dung noi Supabase database + Vercel web + GitHub Actions crawl: uu tien dung stack nay.
- Neu nguoi dung noi free/near-free va khong dang ky duoc GCP: mac dinh la Supabase + Vercel + GitHub Actions.
- Neu nguoi dung chi can demo re nhat: uu tien GitHub Pages static fallback.
- Backend FastAPI/Render chi la tuy chon, khong phai mac dinh.
- GCP chi khi nguoi dung dang ky duoc free trial/billing va xac nhan ro.
- Khong dung AWS neu khong co lenh ro rang.

## 7. Tai lieu bao cao

Thu muc:

```text
docs/bao-cao/
```

Da co:

- Chuong 1: Mo dau.
- Chuong 2: Co so ly thuyet.
- Chuong 3: Phan tich yeu cau va du lieu.
- Chuong 4: Thiet ke he thong.
- Chuong 5: Trien khai pipeline ETL.
- Chuong 6: Giao dien va dashboard.
- Chuong 7: Danh gia ket qua va kiem thu.
- Chuong 8: Ket luan va huong phat trien.
- Ban tong hop: `Bao_cao_ETL_phong_tro_hoan_chinh.docx`.

Anh bao cao:

```text
docs/report-assets/
```

Nguyen tac bo tri anh:

- Chuong 2: ly thuyet, chat luong du lieu.
- Chuong 4: kien truc he thong, serving layer.
- Chuong 5: transform, geocoding, load/static export.
- Chuong 6: dashboard/giao dien.
- Chuong 7: bieu do danh gia ket qua.
- Chuong 8: tong ket va huong phat trien.

## 8. Cac lenh kiem tra quan trong

Frontend:

```powershell
cd web
npm install
npm run build
```

GitHub Pages build:

```powershell
cd web
npm run build:pages
```

Backend local:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload --port 8000
```

Crawler smoke test:

```powershell
cd crawler
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
python -m app.main bootstrap --city all --max-pages 1 --max-detail-pages 2 --sources all
```

Static export:

```powershell
cd crawler
python -m app.static_map_export
```

Doc/report build scripts:

```powershell
python docs\bao-cao\build_chuong1_docx.py
python docs\bao-cao\build_chuong2_docx.py
python docs\bao-cao\build_chuong378_docx.py
python docs\bao-cao\build_chuong456_docx.py
```

## 9. Tieu chi hoan thanh mot nhiem vu

Mot nhiem vu chi duoc xem la xong khi co bang chung:

- File da duoc tao/sua dung noi dung yeu cau.
- Lenh build/test lien quan da chay duoc hoac neu khong chay duoc thi neu ro ly do.
- Khong lam mat thay doi cua nguoi dung.
- Khong revert file khong lien quan.
- Neu la frontend, phai kiem tra UI bang build hoac browser/screenshot khi co the.
- Neu la DOCX, phai render/kiem layout khi co cong cu.
- Neu la data/export, phai kiem count, schema, manifest va file output.
- Neu la deploy, phai co URL/health check/status code hoac huong dan tiep theo cu the.

## 10. Ranh gioi can can than

- Khong tu y dung AWS neu nguoi dung dang lo credit.
- Khong tao GCP Cloud SQL/Cloud Run Job vi nguoi dung hien khong dang ky duoc GCP free trial; chi quay lai GCP khi co xac nhan moi.
- Khong dua Supabase service role key vao frontend hoac repo.
- Khong dung Render Postgres free lam DB chinh vi gioi han 30 ngay; neu khong dung Supabase thi moi can Neon Free.
- Khong xoa artifacts du lieu lon neu chua xac nhan.
- Khong sua cac file dang co thay doi cua nguoi dung neu khong can.
- Khong dua ra ket luan "xong" neu chua co bang chung.
- Khong chi viet ke hoach; neu nguoi dung yeu cau lam, phai lam den khi co deliverable.
- Khong de bao cao/DOCX co anh sai chuong hoac bang bi vo layout.

## 11. Huong phat trien uu tien

Thu tu uu tien neu tiep tuc mo rong:

1. On dinh data quality va dedupe lien nguon.
2. Cai thien geocoding exact cho tin co dia chi chi tiet.
3. Toi uu frontend khi dataset tang len tren 100k tin.
4. Them server-side query bang PostgreSQL/PostGIS.
5. Them incremental crawl hang ngay co log va canh bao.
6. Them dashboard nang cao: price heatmap, khu vuc noi bat, so sanh quan/huyen.
7. Them test parser cho tung nguon de bat loi khi DOM/API thay doi.
