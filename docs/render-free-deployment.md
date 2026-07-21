# Deploy mien phi tren Render

Updated: 2026-07-21

## Kien truc duoc chon

```text
GitHub repository
  -> Render Static Site (frontend + static JSON snapshot)
  -> GitHub Actions (ETL theo lich / chay thu cong)
       -> Supabase Free (tuy chon, chi can khi muon database song)
```

Ban public khong can FastAPI hay Render Web Service. Next.js duoc export thanh HTML/CSS/JavaScript va phuc vu tren CDN cua Render. Cach nay khong co cold start, khong can the thanh toan va khong tieu AWS/GCP credit.

## Du lieu duoc dua len

- 20,000 tin tot nhat trong snapshot da qua quality gate.
- 4 index chunks de tai danh sach va ban do.
- 40 detail chunks chi tai khi nguoi dung mo chi tiet.
- 2 nguon du thong tin de xuat ban: Phongtro123 va NhaTot.
- Moi tin bat buoc co anh that, lien he, gia, dien tich, dia chi, mo ta va link goc.
- Dashboard phan tich va dashboard tien trinh ETL dung chung snapshot.

## Trien khai bang Blueprint

1. Push nhanh `main` len GitHub.
2. Mo `https://dashboard.render.com/blueprints`.
3. Chon **New Blueprint Instance** va ket noi repository `npgb2505/cap2-phongtro-intelligence`.
4. Render se doc `render.yaml` va tao Static Site `phongtro-intelligence`.
5. Chon **Apply**. Khong tao database, disk hoac paid instance.
6. Cho cac buoc `npm ci`, `lint`, `validate:data`, `next build` hoan tat.

`render.yaml` da cau hinh:

```yaml
runtime: static
buildCommand: cd web && npm ci && npm run lint && npm run validate:data && npm run build
staticPublishPath: ./web/out
```

## Kiem tra sau deploy

Mo URL `https://<ten-site>.onrender.com` va xac nhan:

1. Tong snapshot hien 20,000 tin.
2. Bo loc tinh thanh bat buoc truoc khi chon quan huyen.
3. Tim duong chi loc sau khi nguoi dung ngung go.
4. Ban do hien marker khi di chuyen den TP.HCM, Da Nang va Ha Noi.
5. Tab Phan tich hien nhieu loai bieu do va loai gia tren 30 trieu khoi thong ke.
6. Tab Tien trinh ETL hien so do 5 lop.
7. Mo mot tin de kiem tra mo ta, lien he, Google Maps va nut tin goc.
8. Thu lai tren dien thoai; trang khong duoc tran ngang.

## Cap nhat du lieu

Static Site tu deploy lai sau moi commit vao `main`. De dua snapshot moi len:

```powershell
cd D:\UNIVERSITY\Cap2
.\crawler\scripts\export_static_map.ps1
git add web\public\data
git commit -m "Refresh rental listing snapshot"
git push origin main
```

GitHub Actions `Supabase ETL` van co the crawl theo lich va day vao Supabase. Neu chua tao Supabase, hay de workflow o che do thu cong; website Render van hoat dong day du bang snapshot tinh.

## Gioi han chi phi

- Khong tao Render Postgres hay paid Web Service.
- Khong can AWS, GCP, Vercel hoac domain rieng.
- Dung Render Static Site va GitHub Actions trong gioi han mien phi.
- Theo doi bang Render bandwidth va GitHub Actions minutes; snapshot lon nen moi lan deploy se truyen lai nhieu du lieu.
