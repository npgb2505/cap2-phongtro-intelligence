"use client";

import { useEffect, useState } from "react";

import { ListingsExplorer } from "../components/listings-explorer";
import { emptyMapListings, fetchMapListings } from "../lib/api";
import { ListingMapResponse } from "../lib/types";

export default function HomePage() {
  const [data, setData] = useState<ListingMapResponse>(emptyMapListings);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchMapListings()
      .then((nextData) => {
        if (!cancelled) {
          setData(nextData);
          setLoadError(null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLoadError("Không thể tải snapshot ETL. Hãy kiểm tra kết nối hoặc cấu hình nguồn dữ liệu.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return <ListingsExplorer initialData={data} isLoading={isLoading} loadError={loadError} />;
}
