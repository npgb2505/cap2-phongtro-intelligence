# Bao cao hoan thien du an Cap2

Ngay cap nhat: 2026-07-07

## 1. Thong tin demo

Live demo mien phi, khong dung AWS:

```text
https://npgb2505.github.io/cap2-phongtro-intelligence/
```

Static JSON public:

```text
https://npgb2505.github.io/cap2-phongtro-intelligence/data/listings-map.json
```

GitHub repo private:

```text
https://github.com/npgb2505/cap2-phongtro-intelligence
```

## 2. Ket qua chinh

Du an da hoan thien theo huong:

- Crawl va chuan hoa du lieu phong tro nhieu nguon.
- Dat yeu cau it nhat 3 nguon, moi nguon co tu 1,000 tin tro len.
- Co backend FastAPI chay local voi PostgreSQL/CSV fallback.
- Co frontend Next.js hien thi ban do va danh sach tin.
- Giao dien da duoc thiet ke lai theo huong map-first workspace, co filter nguon va marker mau theo nguon phong tro.
- Co local watchdog tu khoi dong lai backend/web khi dung.
- Co pipeline lam moi du lieu hang ngay o local.
- Co self-audit de tu review tinh trang he thong.
- Co ban deploy online mien phi bang GitHub Pages.
- Co cau hinh Render/Vercel du phong neu sau nay can backend online that.
- Khong tao AWS resource vi AWS credit da het han.

## 3. So lieu du lieu

Snapshot local day du:

| Chi so | Gia tri |
| --- | ---: |
| Curated CSV | 55,971 dong |
| Local PostgreSQL/API | 55,896 dong |
| Geocoded/reference-mapped | 55,837 dong |
| Unique province values | 53 |

Nguon trong curated CSV:

| Nguon | So tin |
| --- | ---: |
| phongtro123 | 44,818 |
| nhatot | 10,028 |
| mogi | 1,005 |
| thuephongtro | 84 |
| batdongsan | 35 |
| alonhadat | 1 |

Deploy snapshot online:

| Nguon | So tin |
| --- | ---: |
| phongtro123 | 1,000 |
| nhatot | 1,000 |
| mogi | 1,000 |

Tong deploy snapshot:

```text
3000 tin
```

## 4. Kien truc

```text
Crawler
  -> raw / normalized artifacts
  -> tabular CSV
  -> curated CSV
  -> deploy snapshot CSV
  -> static JSON for GitHub Pages

Backend local
  -> FastAPI
  -> PostgreSQL first
  -> CSV fallback

Frontend
  -> Next.js
  -> Leaflet map
  -> listing sidebar
  -> static JSON mode for GitHub Pages

Online free deploy
  -> GitHub Actions
  -> Next static export
  -> GitHub Pages
```

## 5. Cach chay local

Mo PowerShell tai:

```powershell
cd D:\UNIVERSITY\Cap2
```

Start local stack:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra\local\start_local_stack.ps1
```

Mo:

```text
http://127.0.0.1:3000
```

Backend health:

```text
http://127.0.0.1:8000/health
```

Stop:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra\local\stop_local_stack.ps1
```

## 6. Tu dong chay lai khi dung

Watchdog local:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra\local\start_watchdog.ps1
```

Autostart da duoc cai bang HKCU Run:

```text
HKCU:\Software\Microsoft\Windows\CurrentVersion\Run\Cap2LocalStackWatchdog
```

Watchdog lam cac viec:

- Giu backend va web dang chay.
- Ghi heartbeat vao `crawler/artifacts/logs/cap2-watchdog.heartbeat`.
- Chay daily refresh sau 02:15 neu hom do chua chay.

## 7. Lam moi du lieu

Chay incremental:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File crawler\scripts\incremental_daily.ps1
```

Tao deploy snapshot nho cho online:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File crawler\scripts\create_deploy_snapshot.ps1
```

Tao static JSON cho GitHub Pages:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File crawler\scripts\export_static_map.ps1
```

Push len GitHub se tu kich hoat GitHub Pages workflow.

## 8. Deploy online mien phi

Deploy hien tai dung GitHub Pages:

```text
https://npgb2505.github.io/cap2-phongtro-intelligence/
```

Workflow:

```text
.github/workflows/pages.yml
```

Workflow da chay thanh cong:

```text
Deploy GitHub Pages: success
```

Static build dung:

```text
GITHUB_PAGES=true
NEXT_PUBLIC_STATIC_DATA_PATH=/cap2-phongtro-intelligence/data/listings-map.json
```

Ly do chon GitHub Pages:

- Khong ton AWS credit.
- Khong can database cloud.
- Khong can Render/Vercel login de demo.
- Du cho demo ban do va dataset da chuan hoa.

## 9. Kiem thu da chay

Self-audit local:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra\local\self_audit.ps1
```

Ket qua gan nhat:

```text
passed=true
backend health OK
map API total=55896
web HTTP 200
curated sources: phongtro123=44818, nhatot=10028, mogi=1005
deploy snapshot: phongtro123=1000, nhatot=1000, mogi=1000
autostart OK
watchdog heartbeat OK
```

Frontend static build:

```powershell
cd D:\UNIVERSITY\Cap2\web
$env:GITHUB_PAGES="true"
$env:NEXT_PUBLIC_STATIC_DATA_PATH="/cap2-phongtro-intelligence/data/listings-map.json"
npm run build:pages
```

Ket qua:

```text
Compiled successfully
Static export successfully generated
```

Live URL check:

```text
HTML status: 200
JSON total: 3000
JSON returned: 3000
phongtro123: 1000
nhatot: 1000
mogi: 1000
```

## 10. AWS status

Khong deploy AWS vi credit da het han. Repo van co Terraform va AWS cost guard neu sau nay can dung lai.

Da them guard:

- `infra/aws/preflight_cost_guard.ps1`
- `infra/aws/configure_sso_profile.ps1`
- Terraform yeu cau `paid_deploy_acknowledgement` truoc khi tao RDS.

## 11. Gioi han hien tai

- GitHub Pages la static deploy, nen khong co backend query dong tren server.
- Du lieu online la snapshot 3,000 tin, khong phai toan bo 55,971 tin.
- Neu muon API online that, co the tiep tuc huong Render Free backend da chuan bi san trong `render.yaml`, nhung can dang nhap Render dashboard.
- Render Free co cold start va gioi han free tier, nen GitHub Pages van la huong an toan nhat cho demo.

## 12. Ket luan

Du an da co ban local day du va ban online mien phi:

- Local: day du 55k+ tin, backend + web + watchdog + audit.
- Online: GitHub Pages chay that, co 3,000 tin tu 3 nguon lon.
- Tai lieu van hanh va deploy da duoc cap nhat.
- Khong phat sinh chi phi AWS.
