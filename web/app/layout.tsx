import "./globals.css";
import "leaflet/dist/leaflet.css";

import type { Metadata, Viewport } from "next";
import { Be_Vietnam_Pro } from "next/font/google";

const beVietnamPro = Be_Vietnam_Pro({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-app",
  display: "swap"
});

export const metadata: Metadata = {
  title: "PhongTro Intelligence | Bản đồ và phân tích phòng trọ",
  description:
    "Khám phá, so sánh và phân tích dữ liệu phòng trọ đã chuẩn hóa từ nhiều nguồn trên toàn quốc.",
  applicationName: "PhongTro Intelligence",
  keywords: ["phòng trọ", "bản đồ phòng trọ", "phân tích giá thuê", "ETL", "Việt Nam"],
  openGraph: {
    title: "PhongTro Intelligence",
    description: "Bản đồ và dashboard phân tích hơn 117 nghìn tin phòng trọ.",
    locale: "vi_VN",
    type: "website"
  }
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#edf7ff",
  colorScheme: "light"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi">
      <body className={beVietnamPro.variable}>{children}</body>
    </html>
  );
}
