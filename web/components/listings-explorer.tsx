"use client";

import dynamic from "next/dynamic";
import { startTransition, useDeferredValue, useMemo, useState } from "react";

import { formatDistrict, formatPrecision } from "../lib/format";
import { Listing, ListingMapResponse } from "../lib/types";

const ListingsMap = dynamic(() => import("./listings-map").then((module) => module.ListingsMap), {
  ssr: false
});

type Props = {
  initialData: ListingMapResponse;
};

const SOURCE_LABELS: Record<string, string> = {
  phongtro123: "Phongtro123",
  nhatot: "NhaTot",
  mogi: "Mogi",
  fallback: "Fallback"
};

function formatCurrency(value: number | null) {
  if (!value) {
    return "Lien he";
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} tr/thang`;
  }
  return `${value.toLocaleString("vi-VN")} VND`;
}

function sourceLabel(sourceName: string) {
  return SOURCE_LABELS[sourceName] ?? sourceName;
}

function sourceCounts(items: Listing[]) {
  return items.reduce<Record<string, number>>((acc, item) => {
    acc[item.source_name] = (acc[item.source_name] ?? 0) + 1;
    return acc;
  }, {});
}

export function ListingsExplorer({ initialData }: Props) {
  const [selectedProvince, setSelectedProvince] = useState<string>("all");
  const [selectedSource, setSelectedSource] = useState<string>("all");
  const [searchText, setSearchText] = useState("");
  const [selectedListingId, setSelectedListingId] = useState<string | null>(initialData.items[0]?.id ?? null);
  const deferredSearch = useDeferredValue(searchText);

  const counts = useMemo(() => sourceCounts(initialData.items), [initialData.items]);
  const sources = useMemo(() => Object.keys(counts).sort(), [counts]);
  const locatedCount = useMemo(
    () => initialData.items.filter((item) => item.latitude && item.longitude).length,
    [initialData.items]
  );

  const keyword = deferredSearch.trim().toLowerCase();
  const visibleItems = initialData.items.filter((item) => {
    const matchesProvince = selectedProvince === "all" || item.province === selectedProvince;
    const matchesSource = selectedSource === "all" || item.source_name === selectedSource;
    const haystack = `${item.title} ${item.full_address ?? ""} ${item.district ?? ""} ${item.room_type ?? ""} ${item.source_name}`.toLowerCase();
    const matchesKeyword = !keyword || haystack.includes(keyword);
    return matchesProvince && matchesSource && matchesKeyword;
  });

  const exactCount = initialData.geocode_summary.exact ?? 0;
  const districtCount = initialData.geocode_summary.district ?? 0;
  const provinceCount = initialData.geocode_summary.province ?? 0;
  const selectedListing = visibleItems.find((item) => item.id === selectedListingId) ?? visibleItems[0] ?? null;
  const markerCount = visibleItems.filter((item) => item.latitude && item.longitude).length;

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <span className="status-dot" aria-hidden />
          <div>
            <p>PhongTro Intelligence</p>
            <h1>Rental map workspace</h1>
          </div>
        </div>
        <div className="topbar-metrics" aria-label="Dataset summary">
          <div>
            <span>Dataset</span>
            <strong>{initialData.total.toLocaleString("vi-VN")}</strong>
          </div>
          <div>
            <span>Dang hien</span>
            <strong>{visibleItems.length.toLocaleString("vi-VN")}</strong>
          </div>
          <div>
            <span>Marker</span>
            <strong>{markerCount.toLocaleString("vi-VN")}</strong>
          </div>
        </div>
      </header>

      <section className="control-strip" aria-label="Filters and quality indicators">
        <label className="search-field">
          <span>Tim kiem</span>
          <input
            type="search"
            placeholder="Nhap ten duong, quan, tieu de..."
            value={searchText}
            onChange={(event) => {
              const nextValue = event.target.value;
              startTransition(() => setSearchText(nextValue));
            }}
          />
        </label>

        <label className="select-field">
          <span>Tinh thanh</span>
          <select
            value={selectedProvince}
            onChange={(event) => {
              const nextValue = event.target.value;
              startTransition(() => setSelectedProvince(nextValue));
            }}
          >
            <option value="all">Tat ca</option>
            {initialData.available_provinces.map((province) => (
              <option key={province} value={province}>
                {province}
              </option>
            ))}
          </select>
        </label>

        <label className="select-field">
          <span>Nguon</span>
          <select
            value={selectedSource}
            onChange={(event) => {
              const nextValue = event.target.value;
              startTransition(() => setSelectedSource(nextValue));
            }}
          >
            <option value="all">Tat ca nguon</option>
            {sources.map((source) => (
              <option key={source} value={source}>
                {sourceLabel(source)} ({counts[source].toLocaleString("vi-VN")})
              </option>
            ))}
          </select>
        </label>

        <div className="quality-row">
          <div>
            <span>Toa do</span>
            <strong>{locatedCount.toLocaleString("vi-VN")}</strong>
          </div>
          <div>
            <span>Exact</span>
            <strong>{exactCount.toLocaleString("vi-VN")}</strong>
          </div>
          <div>
            <span>Reference</span>
            <strong>{(districtCount + provinceCount).toLocaleString("vi-VN")}</strong>
          </div>
        </div>
      </section>

      <section className="workspace-grid">
        <aside className="results-panel" aria-label="Listings">
          <div className="panel-head">
            <div>
              <p>Ket qua</p>
              <h2>{visibleItems.length.toLocaleString("vi-VN")} phong tro</h2>
            </div>
            <span>{markerCount.toLocaleString("vi-VN")} diem tren ban do</span>
          </div>

          <div className="source-pills" aria-label="Source distribution">
            {sources.map((source) => (
              <button
                key={source}
                type="button"
                className={`source-pill source-${source} ${selectedSource === source ? "active" : ""}`}
                onClick={() => setSelectedSource(selectedSource === source ? "all" : source)}
              >
                <span />
                {sourceLabel(source)}
                <strong>{counts[source].toLocaleString("vi-VN")}</strong>
              </button>
            ))}
          </div>

          <div className="listing-list">
            {visibleItems.map((item) => (
              <article
                key={item.id}
                className={`listing-card source-border-${item.source_name} ${item.id === selectedListing?.id ? "selected" : ""}`}
                onClick={() => setSelectedListingId(item.id)}
              >
                <div className="listing-card-top">
                  <span className={`source-chip source-${item.source_name}`}>{sourceLabel(item.source_name)}</span>
                  <span>{formatDistrict(item.district)}</span>
                </div>
                <h3>{item.title}</h3>
                <p>{item.full_address ?? "Address pending normalization"}</p>
                <div className="listing-tags">
                  <span>{item.area_m2 ? `${item.area_m2} m2` : "No area"}</span>
                  <span>{item.room_type ?? "khac"}</span>
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

        <section className="map-workspace">
          <div className="map-toolbar">
            <div>
              <p>Dang chon</p>
              <h2>{selectedListing?.title ?? "Chon mot phong tro tren ban do"}</h2>
            </div>
            <div className="toolbar-facts">
              <span>{selectedListing ? formatCurrency(selectedListing.price_value) : "Gia dang cap nhat"}</span>
              <span>{selectedListing ? formatPrecision(selectedListing.geocode_precision) : "Dinh vi"}</span>
              <span>{selectedListing?.amenity_count ?? 0} tien ich</span>
            </div>
          </div>

          <div className="map-stage">
            <ListingsMap
              listings={visibleItems}
              selectedListingId={selectedListing?.id ?? null}
              onSelectListing={setSelectedListingId}
            />
            <div className="map-legend" aria-label="Map legend">
              {sources.map((source) => (
                <span key={source} className={`source-${source}`}>
                  <i />
                  {sourceLabel(source)}
                </span>
              ))}
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}
