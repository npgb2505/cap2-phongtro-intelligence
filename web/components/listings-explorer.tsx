"use client";

import dynamic from "next/dynamic";
import { startTransition, useDeferredValue, useState } from "react";

import { formatDistrict, formatPrecision } from "../lib/format";
import { ListingMapResponse } from "../lib/types";

const ListingsMap = dynamic(() => import("./listings-map").then((module) => module.ListingsMap), {
  ssr: false
});

type Props = {
  initialData: ListingMapResponse;
};

function formatCurrency(value: number | null) {
  if (!value) {
    return "Lien he";
  }
  return `${value.toLocaleString("vi-VN")} VND`;
}

export function ListingsExplorer({ initialData }: Props) {
  const [selectedProvince, setSelectedProvince] = useState<string>("all");
  const [searchText, setSearchText] = useState("");
  const [selectedListingId, setSelectedListingId] = useState<string | null>(initialData.items[0]?.id ?? null);
  const deferredSearch = useDeferredValue(searchText);

  const keyword = deferredSearch.trim().toLowerCase();
  const visibleItems = initialData.items.filter((item) => {
    const matchesProvince = selectedProvince === "all" || item.province === selectedProvince;
    const haystack = `${item.title} ${item.full_address ?? ""} ${item.district ?? ""} ${item.room_type ?? ""}`.toLowerCase();
    const matchesKeyword = !keyword || haystack.includes(keyword);
    return matchesProvince && matchesKeyword;
  });

  const exactCount = initialData.geocode_summary.exact ?? 0;
  const districtCount = initialData.geocode_summary.district ?? 0;
  const provinceCount = initialData.geocode_summary.province ?? 0;
  const selectedListing = visibleItems.find((item) => item.id === selectedListingId) ?? visibleItems[0] ?? null;

  return (
    <main className="shell">
      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">Curated nationwide rental intelligence</span>
          <h1>Map-first explorer with cleaned ETL, reference geocoding, and better field quality than the source feed.</h1>
          <p>
            Datasets are transformed from the local nationwide crawl, then each listing is placed on a reference map
            using exact address geocoding when available and ward or district fallback when not.
          </p>
          <div className="hero-actions">
            <input
              className="search-input"
              type="search"
              placeholder="Tim theo tieu de, duong, quan, room type..."
              value={searchText}
              onChange={(event) => {
                const nextValue = event.target.value;
                startTransition(() => setSearchText(nextValue));
              }}
            />
            <select
              className="province-select"
              value={selectedProvince}
              onChange={(event) => {
                const nextValue = event.target.value;
                startTransition(() => setSelectedProvince(nextValue));
              }}
            >
              <option value="all">Tat ca tinh thanh</option>
              {initialData.available_provinces.map((province) => (
                <option key={province} value={province}>
                  {province}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="hero-card">
          <div className="stat-grid">
            <article className="stat-tile">
              <span>Total crawled</span>
              <strong>{initialData.total.toLocaleString("vi-VN")}</strong>
            </article>
            <article className="stat-tile">
              <span>Loaded in demo</span>
              <strong>{initialData.returned.toLocaleString("vi-VN")}</strong>
            </article>
            <article className="stat-tile">
              <span>Exact geocoded</span>
              <strong>{exactCount.toLocaleString("vi-VN")}</strong>
            </article>
            <article className="stat-tile">
              <span>Reference centroid</span>
              <strong>{(districtCount + provinceCount).toLocaleString("vi-VN")}</strong>
            </article>
          </div>
          <div className="legend">
            <span className="legend-item exact">Exact</span>
            <span className="legend-item district">District reference</span>
            <span className="legend-item province">Province reference</span>
          </div>
        </div>
      </section>

      <section className="workspace">
        <aside className="sidebar">
          <div className="sidebar-header">
            <h2>Curated Listings</h2>
            <span>{visibleItems.length} ket qua dang hien</span>
          </div>
          <div className="listing-list">
            {visibleItems.map((item) => (
              <article
                key={item.id}
                className={`listing-card ${item.id === selectedListing?.id ? "selected" : ""}`}
                onClick={() => setSelectedListingId(item.id)}
              >
                <div className="listing-meta">
                  <span>{formatDistrict(item.district)}</span>
                  <span>{item.area_m2 ? `${item.area_m2} m2` : "No area"}</span>
                </div>
                <h3>{item.title}</h3>
                <p>{item.full_address ?? "Address pending normalization"}</p>
                <div className="listing-tags">
                  <span>{item.room_type ?? "khac"}</span>
                  <span>{item.furnishing_level ?? "unknown"}</span>
                  <span>{formatPrecision(item.geocode_precision)}</span>
                </div>
                <div className="listing-footer">
                  <strong>{formatCurrency(item.price_value)}</strong>
                  <span>{item.record_completeness_score ?? 0}/100</span>
                </div>
              </article>
            ))}
          </div>
        </aside>

        <section className="map-panel">
          <div className="map-detail">
            <div>
              <span className="detail-kicker">Selected listing</span>
              <h2>{selectedListing?.title ?? "Chon mot listing"}</h2>
              <p>{selectedListing?.full_address ?? "Map dang hien thi cac toa do tham khao tu curated ETL."}</p>
            </div>
            {selectedListing ? (
              <div className="detail-grid">
                <div>
                  <span>Gia</span>
                  <strong>{formatCurrency(selectedListing.price_value)}</strong>
                </div>
                <div>
                  <span>Dinh vi</span>
                  <strong>{formatPrecision(selectedListing.geocode_precision)}</strong>
                </div>
                <div>
                  <span>Noi that</span>
                  <strong>{selectedListing.furnishing_level ?? "unknown"}</strong>
                </div>
                <div>
                  <span>Tien ich</span>
                  <strong>{selectedListing.amenity_count}</strong>
                </div>
              </div>
            ) : null}
          </div>

          <ListingsMap
            listings={visibleItems}
            selectedListingId={selectedListing?.id ?? null}
            onSelectListing={setSelectedListingId}
          />
        </section>
      </section>
    </main>
  );
}
