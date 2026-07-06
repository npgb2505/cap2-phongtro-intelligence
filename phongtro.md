# PhongTro Intelligence Platform

Tài liệu định hướng cũ đã được thay bằng bộ scaffold production trong repo này.

Điểm khởi đầu nên đọc theo thứ tự:

1. [README.md](/D:/UNIVERSITY/Cap2/README.md)
2. [docs/architecture.md](/D:/UNIVERSITY/Cap2/docs/architecture.md)
3. [infra/docker-compose.yml](/D:/UNIVERSITY/Cap2/infra/docker-compose.yml)
4. [backend/app/main.py](/D:/UNIVERSITY/Cap2/backend/app/main.py)
5. [crawler/app/main.py](/D:/UNIVERSITY/Cap2/crawler/app/main.py)
6. [web/app/page.tsx](/D:/UNIVERSITY/Cap2/web/app/page.tsx)

Hướng kiến trúc hiện tại:

- Bootstrap crawler bằng local để lấy dữ liệu khởi tạo, giảm chi phí cloud.
- Đồng bộ raw data lên S3 và dữ liệu chuẩn hóa lên PostgreSQL.
- Chạy incremental crawl hằng ngày trên AWS bằng EventBridge + ECS Fargate.
- Phục vụ API tra cứu bằng FastAPI.
- Hiển thị frontend tìm kiếm theo bản đồ bằng Next.js + Leaflet.

Repo này được scaffold như một dự án thật để tiếp tục triển khai dần, không còn là bản mô tả môn học.
