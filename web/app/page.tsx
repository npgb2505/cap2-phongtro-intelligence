"use client";

import { useEffect, useState } from "react";

import { ListingsExplorer } from "../components/listings-explorer";
import { fallbackMapListings, fetchMapListings } from "../lib/api";
import { ListingMapResponse } from "../lib/types";

export default function HomePage() {
  const [data, setData] = useState<ListingMapResponse>(fallbackMapListings);

  useEffect(() => {
    let cancelled = false;
    fetchMapListings().then((nextData) => {
      if (!cancelled) {
        setData(nextData);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return <ListingsExplorer initialData={data} />;
}
