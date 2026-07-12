# Huong dan agent doc instruction va lam den khi xong

File nay la instruction van hanh. Agent tiep quan du an phai doc file nay dau tien, sau do doc them `TECHNICAL_PROJECT_OUTLINE.md` va `AGENT_SOUL.md`, roi lam viec den khi co bang chung hoan thanh.

## 1. Thu tu doc bat buoc

Khi bat dau mot phien lam viec moi trong repo nay, doc theo thu tu:

1. `docs/agent-instructions/AGENT_EXECUTION_INSTRUCTIONS.md`
2. `docs/agent-instructions/TECHNICAL_PROJECT_OUTLINE.md`
3. `docs/agent-instructions/AGENT_SOUL.md`
4. `README.md`
5. Cac tai lieu lien quan den nhiem vu:
   - ETL/crawler: `docs/etl-pipeline.md`, `docs/data-inventory.md`, `docs/local-operations.md`
   - Kien truc: `docs/architecture.md`
   - Deploy free: `docs/free-deployment.md`, `docs/online-deploy-status.md`
   - Deploy Supabase/Vercel/GitHub Actions: can tao/cap nhat `docs/supabase-vercel-github-actions.md` hoac tai lieu tuong duong
   - Deploy Neon/Render/Vercel/GitHub chi khi Supabase khong phu hop: `docs/cloud-option-2-neon-render-vercel.md`
   - Deploy GCP chi khi nguoi dung dang ky duoc billing/free trial va xac nhan ro: can tao/cap nhat `docs/gcp-cloud-deployment.md` hoac tai lieu GCP tuong duong
   - Bao cao: `docs/bao-cao/`, `docs/report-assets/README.md`
   - AWS neu duoc yeu cau ro: `docs/cloud-deployment-flow.md`, `infra/aws/README.md`

Khong can doc moi file trong repo neu nhiem vu hep, nhung phai doc du file de khong lam sai kien truc.

## 2. Lenh khoi dau moi phien

Chay cac lenh sau de nam hien trang:

```powershell
pwd
git status --short
Get-ChildItem -Force
rg --files | Select-Object -First 200
```

Neu thay worktree co file modified khong do minh tao:

- Khong revert.
- Khong ghi de neu khong lien quan.
- Neu phai sua cung file, doc ky diff/ngu canh truoc.

## 3. Cach phan loai nhiem vu

Sau khi doc yeu cau nguoi dung, xep vao mot hoac nhieu nhom:

| Nhom | Thu muc/file uu tien |
|---|---|
| Crawler/ETL | `crawler/app/`, `docs/etl-pipeline.md` |
| Data/export | `crawler/artifacts/`, `web/public/data/`, `crawler/app/static_map_export.py` |
| Backend/API | `backend/app/` |
| Frontend/UI | `web/app/`, `web/components/`, `web/lib/` |
| Deploy static/free | `.github/workflows/`, `docs/online-deploy-status.md`, `docs/free-deployment.md` |
| Deploy Supabase/Vercel/GitHub Actions | `sql/schema.sql`, `sql/supabase_views.sql`, `crawler/`, `web/`, `.github/workflows/supabase-etl.yml`, `docs/supabase-vercel-github-actions.md` |
| Deploy Neon/Render/Vercel/GitHub | Chi khi Supabase khong phu hop: `render.neon.yaml`, `render.yaml`, `backend/`, `web/`, `.github/workflows/`, `docs/cloud-option-2-neon-render-vercel.md` |
| Deploy GCP | Chi khi co xac nhan moi: `backend/`, `crawler/`, `web/`, `infra/`, `docs/gcp-cloud-deployment.md` |
| Bao cao/DOCX | `docs/bao-cao/`, `docs/report-assets/` |
| Tai lieu/huong dan | `docs/` |

Voi moi nhom, xac dinh:

- file nguon su that;
- output mong doi;
- lenh verify;
- rui ro chi phi/data/deploy.

## 4. Quy trinh lam viec bat buoc

### Buoc 1: Hieu yeu cau

Viet lai trong dau:

- Nguoi dung muon artifact nao?
- Can sua code, data, docs, hay deploy?
- Ket qua cuoi cung duoc mo/xem/chay o dau?
- Co han che nao: free deploy, Supabase database, Vercel web, GitHub Actions crawler, khong dang ky duoc GCP, khong AWS, bao cao DOCX, giao dien dep, data day du?

Neu co the suy luan an toan, khong hoi lai. Neu khong the tiep tuc neu thieu thong tin song con, hoi ngan gon.

### Buoc 2: Doc ngu canh

Dung `rg` truoc khi mo file:

```powershell
rg -n "keyword" path
rg --files
```

Doc file lien quan bang `Get-Content`, `Select-Object`, hoac cong cu phu hop.

### Buoc 3: Lap checklist ngan

Neu viec co hon mot buoc, tao checklist:

- file nao se tao/sua;
- lenh nao se chay;
- bang chung nao can co.

### Buoc 4: Thuc hien

Nguyen tac:

- Sua file bang patch/editor an toan.
- Khong sua lan man.
- Khong xoa du lieu lon neu chua can.
- Khong dung AWS khi chua duoc xac nhan.
- Khong dung GCP lam mac dinh vi nguoi dung hien khong dang ky duoc GCP free trial.
- Khong tao resource yeu cau the/tra phi neu chua co xac nhan ro.
- Khong public Supabase service role key; key nay chi duoc nam trong GitHub Actions secrets hoac server-side secret.
- Chi de `NEXT_PUBLIC_SUPABASE_URL` va `NEXT_PUBLIC_SUPABASE_ANON_KEY` tren frontend; anon key phai di kem RLS/read-only policy phu hop.
- Neu tao docs moi, dat trong `docs/` va dat ten ro rang.

### Buoc 5: Verify

Chon lenh verify theo nhiem vu.

Frontend:

```powershell
cd web
npm run build
```

Static Pages:

```powershell
cd web
npm run build:pages
```

Backend:

```powershell
cd backend
python -m compileall app
```

Crawler:

```powershell
cd crawler
python -m compileall app
```

Cloud deploy prep Supabase/Vercel/GitHub:

```powershell
git remote -v
git status --short
Get-ChildItem .github\workflows -ErrorAction SilentlyContinue
rg -n "SUPABASE|DATABASE_URL|NEXT_PUBLIC_SUPABASE|service_role|anon" .
```

Neu can Supabase/Vercel, agent khong tu tao account thay nguoi dung khi can login. Chuan bi schema, workflow, env example va docs ro rang, sau do huong dan nguoi dung tao project va dan secrets can thiet.

Data manifest:

```powershell
Get-Content web\public\data\listings-map.json | ConvertFrom-Json | Select-Object total,returned,skipped_rows,dataset_mode
```

Docs Markdown:

- Kiem file ton tai.
- Doc lai dau/cuoi file.
- Kiem link/duong dan chinh.

DOCX:

- Build DOCX.
- Render/kiem layout neu co Word/LibreOffice/Poppler.
- Khong giao file khi bang/anh vo ro rang.

### Buoc 6: Dọn dep

Neu tao render QA, cache, pycache, file tam:

- Xoa neu khong can giao.
- Khong xoa source artifacts/dataset.

### Buoc 7: Bao cao ket qua

Final response can co:

- Da lam gi.
- File nao nam o dau.
- Da verify bang gi.
- Neu con viec tiep, neu ro va ngan.

## 5. Quy tac "lam den khi xong"

"Lam den khi xong" nghia la:

- Khong dung o muc de xuat neu co the tao artifact.
- Khong dung khi moi sua file ma chua verify.
- Khong dung khi output chua dung yeu cau goc.
- Khong doi nguoi dung tu lam cac buoc ma agent co the lam.

Tuy nhien khong duoc lam bua:

- Neu co nguy co ton tien, dung lai xin xac nhan.
- Neu co nguy co xoa du lieu, dung lai xin xac nhan.
- Neu can credential/login khong co, bao ro blocker va dua buoc tiep theo.

## 6. Cac tieu chi rieng cua du an nay

### 6.1. Neu lam ETL/data

Phai kiem:

- record count;
- source count;
- geocode summary;
- skipped rows;
- chunk count;
- field coverage.

Khong duoc chi noi "export thanh cong" neu chua xem output.

### 6.2. Neu lam frontend

Phai giu:

- map-first experience;
- tab dashboard;
- listing detail nhieu truong;
- marker batching;
- geocode precision visibility;
- build Pages khong vo.

### 6.3. Neu lam bao cao

Phai giu:

- noi dung chu yeu la ETL;
- it chia nho vo nghia, uu tien chat luong;
- co code, bang, so lieu, hinh minh hoa;
- anh dung chuong;
- neu DOCX thi render kiem layout.

### 6.4. Neu lam deploy

Mac dinh theo y dinh moi:

- Nguoi dung khong dang ky duoc GCP free trial va dang muon dung Supabase database, nen khong dung GCP lam mac dinh.
- Neu nguoi dung muon cloud co database: uu tien Supabase Free Postgres.
- Neu nguoi dung muon web online: uu tien Vercel Hobby.
- Neu nguoi dung muon crawler nap DB dinh ky: uu tien GitHub Actions manual truoc, schedule sau.
- Neu nguoi dung muon re nhat/on dinh nhat: GitHub Pages/static JSON fallback.
- GCP chi khi sau nay nguoi dung dang ky duoc billing/free trial va xac nhan ro.
- AWS chi khi nguoi dung noi ro.

Neu lam cloud Supabase/Vercel/GitHub, chon cong cu nhu sau:

| Lop | Cong cu | Ghi chu |
|---|---|---|
| Database | Supabase Free Postgres | DB chinh cho `curated_listings`, dashboard views, crawl logs |
| Geo | Supabase Postgres/PostGIS | Bat extension neu can bbox/heatmap/query ban do |
| Data API | Supabase REST/RPC/views | Frontend doc read-only; han che row payload lon |
| Frontend | Vercel Hobby | Deploy Next.js; khong chay crawler nang tren Vercel |
| ETL | GitHub Actions manual/schedule | Chay crawler/export/upsert DB, manual truoc schedule |
| ETL workflow | `.github/workflows/supabase-etl.yml` | Manual `load_existing_csv` hoac `crawl_then_load`, tu apply schema -> load -> apply views/RLS |
| SQL apply CLI | `backend/app/apply_sql.py` | Apply `sql/schema.sql` va `sql/supabase_views.sql` bang `PT_DATABASE_URL` |
| Supabase smoke check | `backend/app/check_supabase_load.py` | Kiem count bang/view sau khi load |
| SQL views | `sql/supabase_views.sql` | Views map/dashboard/RLS, `v_listing_map` tra dung shape frontend |
| Frontend loader | `web/lib/api.ts` | Uu tien Supabase REST, fallback API cu/static chunks |
| Public frontend env | Vercel env | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` |
| Env example | `web/env.vercel.example` | Mau env public cho Vercel, khong chua secret private |
| Private ETL env | GitHub Actions secrets | Mac dinh can `SUPABASE_DB_URL`; `SUPABASE_SERVICE_ROLE_KEY` chi dung neu sau nay goi Supabase API truc tiep |
| Static fallback | GitHub Pages/repo artifacts | Manifest va JSON chunks khi DB pause/gioi han |
| Logs | GitHub Actions logs + Supabase logs | Kiem loi ETL/query |

Thu tu Supabase/Vercel/GitHub bat buoc:

1. Giu GitHub Pages/static JSON hoat dong lam baseline.
2. Tao Supabase project Free va lay project URL, anon key, va Postgres connection string cho `SUPABASE_DB_URL`.
3. Tao SQL schema: `curated_listings`, `crawl_runs`, `source_stats`, indexes, optional PostGIS.
4. Dung `backend/app/apply_sql.py` hoac workflow de apply `sql/schema.sql`, sau do load CSV va apply `sql/supabase_views.sql`.
5. Load compact CSV 3.000-5.000 tin truoc de test schema, field coverage, dashboard query.
6. Tao GitHub Actions workflow manual-only cho load CSV; neu can crawler thi dung input `run_mode=crawl_then_load` voi pages/detail thap.
7. Deploy frontend len Vercel Hobby, set `NEXT_PUBLIC_SUPABASE_URL` va `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
8. Test map/list/dashboard doc Supabase; giu static JSON fallback neu DB pause/gioi han.
9. Chi bat `schedule` sau khi manual workflow on, tan suat thap.
10. Ghi lai URL, Supabase project ref, env vars can set, gioi han free tier va cach pause/tat.

## 7. Bang chung hoan thanh

Truoc khi noi xong, dien ngam bang nay:

| Cau hoi | Phai co |
|---|---|
| Artifact da tao/sua dung chua? | Duong dan file hoac URL |
| Da verify chua? | Lenh build/test/render/count |
| Co anh huong file nguoi dung khong? | Da kiem git status |
| Co ton tien/cloud khong? | Khong, hoac da duoc xac nhan; neu dich vu doi the/tra phi thi phai dung lai |
| Co lo key Supabase khong? | Service role/db URL khong nam trong frontend/repo/public docs |
| Co file tam can don khong? | Da don |
| Co noi dung nao con thieu so voi yeu cau goc? | Neu co thi tiep tuc lam |

Chi final khi tat ca cau hoi deu co cau tra loi tot.

## 8. Neu tiep quan tu agent khac

Lam ngay:

```powershell
git status --short
Get-ChildItem docs\agent-instructions
Get-Content docs\agent-instructions\TECHNICAL_PROJECT_OUTLINE.md
Get-Content docs\agent-instructions\AGENT_SOUL.md
```

Sau do doc summary/lich su neu co, nhung lay repo hien tai lam nguon su that.

## 9. Neu can tao task moi cho agent

Dung format:

```text
Objective:
- ...

Context files:
- docs/agent-instructions/TECHNICAL_PROJECT_OUTLINE.md
- docs/agent-instructions/AGENT_SOUL.md
- ...

Constraints:
- khong dung AWS neu khong co xac nhan
- khong dung GCP lam mac dinh vi nguoi dung khong dang ky duoc free trial
- uu tien Supabase Free + Vercel Hobby + GitHub Actions neu can cloud
- khong public Supabase service role key
- khong revert thay doi cua user
- verify truoc khi final

Definition of Done:
- ...
```

## 10. Ket luan van hanh

Agent phai coi day la du an that, khong phai bai demo nho. Moi thay doi can phuc vu mot trong cac muc tieu:

- du lieu dung hon;
- pipeline on dinh hon;
- giao dien khai thac du lieu tot hon;
- deploy re hon/an toan hon;
- bao cao thuyet phuc hon;
- nguoi dung do ton cong hon.

Neu mot hanh dong khong giup muc tieu nao, khong lam.
