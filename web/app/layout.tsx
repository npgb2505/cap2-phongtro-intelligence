import "./globals.css";
import "leaflet/dist/leaflet.css";

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "PhongTro Intelligence Platform",
  description: "Nationwide rental listings map and search platform"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
