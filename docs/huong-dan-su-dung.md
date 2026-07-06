# Huong dan su dung du an Cap2

Cap nhat: 2026-07-06

Tai lieu nay dung de van hanh du an o che do local va chuan bi deploy AWS tiet kiem credit. Muc tieu hien tai la demo on dinh, khong tieu qua muc voi ngan sach AWS credit 100 USD.

## 1. Chay du an local

Mo PowerShell tai:

```powershell
cd D:\UNIVERSITY\Cap2
```

Khoi dong backend va web:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra\local\start_local_stack.ps1
```

Mo app:

- Web: http://127.0.0.1:3000
- Backend health: http://127.0.0.1:8000/health

Dung backend, web va watchdog:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra\local\stop_local_stack.ps1
```

## 2. Kiem tra he thong local

Chay self-audit:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra\local\self_audit.ps1
```

Neu pass, he thong dang dat cac moc chinh:

- backend tra ve health OK
- web tra ve HTTP 200
- API map co du lieu
- curated data co 3 nguon lon tren 1,000 tin
- watchdog/autostart dang hoat dong

## 3. Lam moi du lieu

Chay incremental thu cong:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File crawler\scripts\incremental_daily.ps1
```

Lenh nay se:

1. Crawl du lieu moi tu cac nguon da cau hinh.
2. Tao lai curated CSV.
3. Load lai vao PostgreSQL local neu moi truong local san sang.

## 4. Trang thai du lieu hien tai

Snapshot verified gan nhat:

- Curated CSV: 55,971 dong
- Local PostgreSQL/API: 55,896 dong sau khi loai trung `listing_id`
- Nguon lon dat yeu cau:
  - `phongtro123`: 44,818 dong
  - `nhatot`: 10,028 dong
  - `mogi`: 1,005 dong

Nhu vay yeu cau "toi thieu 3 nguon, moi nguon 1,000+ tin" da dat o local.

## 5. AWS SSO da cau hinh

AWS CLI da cai tai:

```text
C:\Program Files\Amazon\AWSCLIV2\aws.exe
```

Profile SSO local:

```text
cap2
```

SSO start URL:

```text
https://d-90667473bd.awsapps.com/start
```

SSO region:

```text
us-east-1
```

Default deploy region cua project:

```text
ap-southeast-1
```

Login lai SSO khi can:

```powershell
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" sso login --sso-session cap2
```

Kiem tra danh tinh AWS:

```powershell
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" sts get-caller-identity --profile cap2
```

Trang thai hien tai: login SSO thanh cong, nhung user `codex` chua duoc gan vao AWS account nao. Lenh SSO tra ve `accountList: []`, nen chua the check credit, tao budget, hay deploy.

Can lam tren AWS Console:

1. Vao IAM Identity Center.
2. Chon AWS accounts.
3. Chon account can deploy.
4. Assign user `codex`.
5. Gan permission set, tam thoi co the dung `AdministratorAccess` cho pilot do an.
6. Dang nhap lai SSO va chay lai `sts get-caller-identity`.

Sau khi assign xong, chay script nay de tu dong dien `sso_account_id` va `sso_role_name` vao profile `cap2`:

```powershell
cd D:\UNIVERSITY\Cap2
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra\aws\configure_sso_profile.ps1
```

## 6. Quy tac tiet kiem AWS credit 100 USD

Chua chay `terraform apply` khi chua xong 3 viec nay:

1. User `codex` da co account assignment.
2. Billing/Credits da duoc kiem tra trong AWS Console.
3. AWS Budget da duoc tao voi alert som.

Nen tao budget truoc khi deploy:

- Budget monthly: 100 USD hoac thap hon.
- Alert som:
  - 10 USD actual
  - 25 USD forecasted
  - 50 USD actual
  - 80 USD forecasted
- Gui alert ve email cua ban.

Sau khi tao budget, chay guard:

```powershell
cd D:\UNIVERSITY\Cap2
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra\aws\preflight_cost_guard.ps1
```

Neu guard fail thi khong deploy.

Trong AWS Console, vao Billing and Cost Management de xem:

- Credits
- Bills
- Cost Explorer
- Budgets

Tai lieu AWS lien quan:

- AWS Budgets: https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
- Tao cost budget: https://docs.aws.amazon.com/cost-management/latest/userguide/create-cost-budget.html
- Billing dashboard: https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/view-billing-dashboard.html

## 7. Chien luoc deploy tiet kiem

Thu tu an toan:

1. Local demo truoc, khong ton AWS.
2. Neu AWS credit het han, dung huong Render Free + Vercel Hobby trong `docs/free-deployment.md`.
3. Chi deploy AWS khi co budget/payment moi va da chay cost guard.
4. Tao foundation toi thieu: S3, ECR, Secrets Manager, RDS micro.
5. Chua bat App Runner/ECS crawler cho den khi image san sang va can test online.
6. Sau demo, dung hoac destroy resource khong can thiet.

Tai nguyen co kha nang ton tien lien tuc:

- RDS PostgreSQL neu de chay 24/7.
- App Runner backend neu bat service.
- ECS/Fargate crawler khi schedule chay.
- S3 neu luu qua nhieu raw artifact.
- NAT Gateway neu sau nay them private networking.

Project hien tai khong dung NAT Gateway trong Terraform pilot.

## 8. Deploy AWS khi da duoc duyet

Chi chay phan nay sau khi da check credit va budget.

Tao file `D:\UNIVERSITY\Cap2\infra\aws\dev.tfvars`:

```hcl
db_password = "mat-khau-rds-manh"
```

Chi sau khi da check credit va budget, them 2 dong nay vao `dev.tfvars`:

```hcl
monthly_credit_limit_usd    = 100
paid_deploy_acknowledgement = "CHECKED_BILLING_BUDGET_APPROVED_100_USD"
```

Neu chua co 2 dong tren, Terraform se tu choi tao RDS de tranh ton credit ngoai y muon.

Chay plan truoc, chua apply:

```powershell
cd D:\UNIVERSITY\Cap2\infra\aws
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" sts get-caller-identity --profile cap2
powershell.exe -NoProfile -ExecutionPolicy Bypass -File preflight_cost_guard.ps1
terraform plan -var-file="dev.tfvars"
```

Neu plan hop ly va ban dong y, moi chay:

```powershell
terraform apply -var-file="dev.tfvars"
```

Sau demo, neu muon xoa tai nguyen AWS de tranh ton tien:

```powershell
cd D:\UNIVERSITY\Cap2\infra\aws
terraform destroy -var-file="dev.tfvars"
```

Khong xoa neu dang can giu database online.

## 9. Bao cao nhanh cho giang vien

Noi dung co the trinh bay:

- He thong crawl phong tro nhieu nguon.
- ETL gom raw, normalized, curated.
- Backend FastAPI phuc vu search/map API.
- Frontend Next.js hien thi ban do va danh sach tin.
- Du lieu local da co 55k+ tin hop le.
- Co 3 nguon lon dat 1,000+ tin.
- Co watchdog tu khoi dong lai service local.
- Co Terraform AWS pilot, nhung deploy cloud duoc kiem soat theo ngan sach credit 100 USD.
