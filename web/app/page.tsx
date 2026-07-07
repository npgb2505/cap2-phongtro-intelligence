"use client";

import { useEffect, useState } from "react";

import { ListingsExplorer } from "../components/listings-explorer";
import { emptyMapListings, fetchMapListings } from "../lib/api";
import { ListingMapResponse } from "../lib/types";

export default function HomePage() {
  const [data, setData] = useState<ListingMapResponse>(emptyMapListings);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetchMapListings().then((nextData) => {
      if (!cancelled) {
        setData(nextData);
        setIsLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return <ListingsExplorer initialData={data} isLoading={isLoading} />;
}
