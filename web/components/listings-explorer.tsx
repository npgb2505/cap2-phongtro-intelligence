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

type TabKey = "search" | "dashboard";

type ChartItem = {
  label: string;
  value: number;
  detail?: string;
};

const SOURCE_LABELS: Record<string, string> = {
  phongtro123: "Phongtro123",
  nhatot: "NhaTot",
  mogi: "Mogi",
  fallback: "Fallback"
};

const ROOM_TYPE_LABELS: Record<string, string> = {
  phong_tro: "Phòng trọ",
  studio: "Studio",
  o_ghep: "Ở ghép",
  can_ho_mini: "Căn hộ mini",
  nha_nguyen_can: "Nhà nguyên căn",
  khac: "Khác"
};

const FURNISHING_LABELS: Record<string, string> = {
  full: "Đầy đủ nội thất",
  partial: "Một phần nội thất",
  none: "Không nội thất",
  unknown: "Chưa rõ nội thất"
};

const SORT_OPTIONS = [
  { value: "recommended", label: "Gợi ý tốt nhất" },
  { value: "price_asc", label: "Giá thấp trước" },
  { value: "price_desc", label: "Giá cao trước" },
  { value: "area_desc", label: "Diện tích lớn trước" },
  { value: "score_desc", label: "Tin đầy đủ nhất" }
] as const;

const PRICE_BUCKETS = [
  { label: "Dưới 2 triệu", min: 0, max: 2_000_000 },
  { label: "2 đến 4 triệu", min: 2_000_000, max: 4_000_000 },
  { label: "4 đến 6 triệu", min: 4_000_000, max: 6_000_000 },
  { label: "6 đến 8 triệu", min: 6_000_000, max: 8_000_000 },
  { label: "Trên 8 triệu", min: 8_000_000, max: Number.POSITIVE_INFINITY }
];

const AREA_BUCKETS = [
  { label: "Dưới 20 m2", min: 0, max: 20 },
  { label: "20 đến 30 m2", min: 20, max: 30 },
  { label: "30 đến 50 m2", min: 30, max: 50 },
  { label: "Trên 50 m2", min: 50, max: Number.POSITIVE_INFINITY }
];

function cleanDisplayText(value: string | null | undefined) {
  return (value ?? "").replace(/[\u2014\u2013]/g, "-");
}

function formatCurrency(value: number | null) {
  if (!value || value < 1000) {
    return "Liên hệ";
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} triệu/tháng`;
  }
  return `${value.toLocaleString("vi-VN")} VND`;
}

function formatShortCurrency(value: number | null) {
  if (!value) {
    return "Chưa có";
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} tr`;
  }
  return value.toLocaleString("vi-VN");
}

function formatArea(value: number | null) {
  if (!value) {
    return "Chưa rõ diện tích";
  }
  return `${value.toLocaleString("vi-VN", { maximumFractionDigits: 1 })} m2`;
}

function formatPercent(value: number) {
  return `${value.toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%`;
}

function sourceLabel(sourceName: string) {
  return SOURCE_LABELS[sourceName] ?? sourceName;
}

function roomTypeLabel(value: string | null) {
  if (!value) {
    return "Khác";
  }
  return ROOM_TYPE_LABELS[value] ?? value;
}

function furnishingLabel(value: string | null) {
  if (!value) {
    return "Chưa rõ nội thất";
  }
  return FURNISHING_LABELS[value] ?? value;
}

function imageUrl(item: Listing | null) {
  return item?.primary_image_url || item?.thumbnail_url || null;
}

function countBy(items: Listing[], getKey: (item: Listing) => string | null | undefined) {
  return items.reduce<Record<string, number>>((acc, item) => {
    const key = getKey(item);
    if (!key) {
      return acc;
    }
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});
}

function topChartItems(counts: Record<string, number>, limit: number, labeler: (key: string) => string = (key) => key) {
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([label, value]) => ({ label: labeler(label), value }));
}

function average(values: number[]) {
  if (!values.length) {
    return null;
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function median(values: number[]) {
  if (!values.length) {
    return null;
  }
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  if (sorted.length % 2) {
    return sorted[middle];
  }
  return (sorted[middle - 1] + sorted[middle]) / 2;
}

function bucketCounts(items: Listing[], buckets: { label: string; min: number; max: number }[], getValue: (item: Listing) => number | null) {
  return buckets.map((bucket) => ({
    label: bucket.label,
    value: items.filter((item) => {
      const value = getValue(item);
      return value !== null && value >= bucket.min && value < bucket.max;
    }).length
  }));
}

function ChartList({ items, total }: { items: ChartItem[]; total: number }) {
  const maxValue = Math.max(...items.map((item) => item.value), 1);

  return (
    <div className="chart-list">
      {items.map((item) => {
        const width = Math.max(4, (item.value / maxValue) * 100);
        const percent = total ? (item.value / total) * 100 : 0;
        return (
          <div className="chart-row" key={item.label}>
            <div className="chart-row-head">
              <span>{item.label}</span>
              <strong>{item.value.toLocaleString("vi-VN")}</strong>
            </div>
            <div className="chart-track" aria-hidden>
              <span style={{ width: `${width}%` }} />
            </div>
            <p>{item.detail ?? formatPercent(percent)}</p>
          </div>
        );
      })}
    </div>
  );
}

export function ListingsExplorer({ initialData }: Props) {
  const [activeTab, setActiveTab] = useState<TabKey>("search");
  const [selectedProvince, setSelectedProvince] = useState<string>("all");
  const [selectedDistrict, setSelectedDistrict] = useState<string>("all");
  const [selectedSource, setSelectedSource] = useState<string>("all");
  const [selectedRoomType, setSelectedRoomType] = useState<string>("all");
  const [selectedPrecision, setSelectedPrecision] = useState<string>("all");
  const [hasImageOnly, setHasImageOnly] = useState(false);
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [minArea, setMinArea] = useState("");
  const [maxArea, setMaxArea] = useState("");
  const [sortBy, setSortBy] = useState<(typeof SORT_OPTIONS)[number]["value"]>("recommended");
  const [searchText, setSearchText] = useState("");
  const [selectedListingId, setSelectedListingId] = useState<string | null>(initialData.items[0]?.id ?? null);
  const deferredSearch = useDeferredValue(searchText);

  const sourceTotals = useMemo(() => countBy(initialData.items, (item) => item.source_name), [initialData.items]);
  const sources = useMemo(() => Object.keys(sourceTotals).sort(), [sourceTotals]);
  const roomTypes = useMemo(
    () => Array.from(new Set(initialData.items.map((item) => item.room_type).filter(Boolean) as string[])).sort(),
    [initialData.items]
  );
  const districts = useMemo(() => {
    const provinceFiltered = initialData.items.filter(
      (item) => selectedProvince === "all" || item.province === selectedProvince
    );
    return Array.from(new Set(provinceFiltered.map((item) => item.district).filter(Boolean) as string[])).sort(
      (a, b) => formatDistrict(a).localeCompare(formatDistrict(b), "vi")
    );
  }, [initialData.items, selectedProvince]);

  const parsedMinPrice = minPrice ? Number(minPrice) * 1_000_000 : null;
  const parsedMaxPrice = maxPrice ? Number(maxPrice) * 1_000_000 : null;
  const parsedMinArea = minArea ? Number(minArea) : null;
  const parsedMaxArea = maxArea ? Number(maxArea) : null;

  const keyword = deferredSearch.trim().toLowerCase();
  const visibleItems = initialData.items
    .filter((item) => {
      const matchesProvince = selectedProvince === "all" || item.province === selectedProvince;
      const matchesDistrict = selectedDistrict === "all" || item.district === selectedDistrict;
      const matchesSource = selectedSource === "all" || item.source_name === selectedSource;
      const matchesRoomType = selectedRoomType === "all" || item.room_type === selectedRoomType;
      const matchesPrecision = selectedPrecision === "all" || item.geocode_precision === selectedPrecision;
      const matchesImage = !hasImageOnly || Boolean(imageUrl(item));
      const matchesMinPrice = parsedMinPrice === null || (item.price_value !== null && item.price_value >= parsedMinPrice);
      const matchesMaxPrice = parsedMaxPrice === null || (item.price_value !== null && item.price_value <= parsedMaxPrice);
      const matchesMinArea = parsedMinArea === null || (item.area_m2 !== null && item.area_m2 >= parsedMinArea);
      const matchesMaxArea = parsedMaxArea === null || (item.area_m2 !== null && item.area_m2 <= parsedMaxArea);
      const haystack = `${item.title} ${item.full_address ?? ""} ${item.district ?? ""} ${item.ward ?? ""} ${item.room_type ?? ""} ${item.source_name}`.toLowerCase();
      const matchesKeyword = !keyword || haystack.includes(keyword);
      return (
        matchesProvince &&
        matchesDistrict &&
        matchesSource &&
        matchesRoomType &&
        matchesPrecision &&
        matchesImage &&
        matchesMinPrice &&
        matchesMaxPrice &&
        matchesMinArea &&
        matchesMaxArea &&
        matchesKeyword
      );
    })
    .sort((a, b) => {
      if (sortBy === "price_asc") {
        return (a.price_value ?? Number.MAX_SAFE_INTEGER) - (b.price_value ?? Number.MAX_SAFE_INTEGER);
      }
      if (sortBy === "price_desc") {
        return (b.price_value ?? 0) - (a.price_value ?? 0);
      }
      if (sortBy === "area_desc") {
        return (b.area_m2 ?? 0) - (a.area_m2 ?? 0);
      }
      if (sortBy === "score_desc") {
        return (b.record_completeness_score ?? 0) - (a.record_completeness_score ?? 0);
      }
      return (b.record_completeness_score ?? 0) - (a.record_completeness_score ?? 0) || (b.image_count ?? 0) - (a.image_count ?? 0);
    });

  const selectedListing = visibleItems.find((item) => item.id === selectedListingId) ?? visibleItems[0] ?? null;
  const selectedImage = imageUrl(selectedListing);
  const markerCount = visibleItems.filter((item) => item.latitude && item.longitude).length;
  const imageCount = visibleItems.filter((item) => imageUrl(item)).length;
  const exactCount = visibleItems.filter((item) => item.geocode_precision === "exact").length;
  const referenceCount = visibleItems.filter((item) => item.geocode_precision === "district" || item.geocode_precision === "province").length;
  const priceValues = visibleItems.map((item) => item.price_value).filter((value): value is number => Boolean(value && value > 1000));
  const areaValues = visibleItems.map((item) => item.area_m2).filter((value): value is number => Boolean(value && value > 0));
  const avgPrice = average(priceValues);
  const medianPrice = median(priceValues);
  const avgArea = average(areaValues);
  const avgScore = average(
    visibleItems
      .map((item) => item.record_completeness_score)
      .filter((value): value is number => value !== null && value !== undefined)
  );
  const sourceChart = topChartItems(countBy(visibleItems, (item) => item.source_name), 5, sourceLabel);
  const roomChart = topChartItems(countBy(visibleItems, (item) => item.room_type ?? "khac"), 6, roomTypeLabel);
  const provinceChart = topChartItems(countBy(visibleItems, (item) => item.province), 8);
  const districtChart = topChartItems(countBy(visibleItems, (item) => item.district), 10, formatDistrict);
  const priceChart = bucketCounts(visibleItems, PRICE_BUCKETS, (item) => item.price_value);
  const areaChart = bucketCounts(visibleItems, AREA_BUCKETS, (item) => item.area_m2);
  const precisionChart = [
    { label: "Sát địa chỉ", value: exactCount },
    { label: "Tâm điểm quận", value: visibleItems.filter((item) => item.geocode_precision === "district").length },
    { label: "Tâm điểm tỉnh", value: visibleItems.filter((item) => item.geocode_precision === "province").length },
    { label: "Chưa định vị", value: visibleItems.filter((item) => !item.latitude || !item.longitude).length }
  ];
  const topDistrict = districtChart[0]?.label ?? "Chưa có";
  const hasActiveFilters =
    selectedProvince !== "all" ||
    selectedDistrict !== "all" ||
    selectedSource !== "all" ||
    selectedRoomType !== "all" ||
    selectedPrecision !== "all" ||
    hasImageOnly ||
    minPrice ||
    maxPrice ||
    minArea ||
    maxArea ||
    searchText;

  function resetFilters() {
    setSelectedProvince("all");
    setSelectedDistrict("all");
    setSelectedSource("all");
    setSelectedRoomType("all");
    setSelectedPrecision("all");
    setHasImageOnly(false);
    setMinPrice("");
    setMaxPrice("");
    setMinArea("");
    setMaxArea("");
    setSearchText("");
    setSortBy("recommended");
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="brand-block">
          <span className="brand-mark" aria-hidden>PT</span>
          <div>
            <p>PhongTrọ Intelligence</p>
            <h1>Nền tảng bản đồ phòng trọ</h1>
          </div>
        </div>

        <nav className="tab-nav" aria-label="Chuyển chế độ xem">
          <button className={activeTab === "search" ? "active" : ""} type="button" onClick={() => setActiveTab("search")}>
            Tìm phòng
          </button>
          <button className={activeTab === "dashboard" ? "active" : ""} type="button" onClick={() => setActiveTab("dashboard")}>
            Dashboard phân tích
          </button>
        </nav>

        <div className="header-metrics" aria-label="Tổng quan nhanh">
          <div>
            <span>Kho tin</span>
            <strong>{initialData.total.toLocaleString("vi-VN")}</strong>
          </div>
          <div>
            <span>Đang xem</span>
            <strong>{visibleItems.length.toLocaleString("vi-VN")}</strong>
          </div>
          <div>
            <span>Có ảnh</span>
            <strong>{imageCount.toLocaleString("vi-VN")}</strong>
          </div>
          <div>
            <span>Điểm bản đồ</span>
            <strong>{markerCount.toLocaleString("vi-VN")}</strong>
          </div>
        </div>
      </header>

      <section className="filter-strip" aria-label="Bộ lọc dữ liệu">
        <label className="search-field">
          <span>Tìm kiếm</span>
          <input
            type="search"
            placeholder="Tên đường, quận, tiêu đề"
            value={searchText}
            onChange={(event) => {
              const nextValue = event.target.value;
              startTransition(() => setSearchText(nextValue));
            }}
          />
        </label>

        <label className="select-field">
          <span>Tỉnh thành</span>
          <select
            value={selectedProvince}
            onChange={(event) => {
              const nextValue = event.target.value;
              startTransition(() => {
                setSelectedProvince(nextValue);
                setSelectedDistrict("all");
              });
            }}
          >
            <option value="all">Tất cả</option>
            {initialData.available_provinces.map((province) => (
              <option key={province} value={province}>
                {province}
              </option>
            ))}
          </select>
        </label>

        <label className="select-field">
          <span>Quận huyện</span>
          <select value={selectedDistrict} onChange={(event) => startTransition(() => setSelectedDistrict(event.target.value))}>
            <option value="all">Tất cả khu vực</option>
            {districts.map((district) => (
              <option key={district} value={district}>
                {formatDistrict(district)}
              </option>
            ))}
          </select>
        </label>

        <label className="select-field">
          <span>Nguồn</span>
          <select value={selectedSource} onChange={(event) => startTransition(() => setSelectedSource(event.target.value))}>
            <option value="all">Tất cả nguồn</option>
            {sources.map((source) => (
              <option key={source} value={source}>
                {sourceLabel(source)}
              </option>
            ))}
          </select>
        </label>

        <label className="select-field">
          <span>Loại phòng</span>
          <select value={selectedRoomType} onChange={(event) => startTransition(() => setSelectedRoomType(event.target.value))}>
            <option value="all">Tất cả loại phòng</option>
            {roomTypes.map((roomType) => (
              <option key={roomType} value={roomType}>
                {roomTypeLabel(roomType)}
              </option>
            ))}
          </select>
        </label>

        <label className="select-field">
          <span>Định vị</span>
          <select value={selectedPrecision} onChange={(event) => startTransition(() => setSelectedPrecision(event.target.value))}>
            <option value="all">Tất cả tọa độ</option>
            <option value="exact">Sát địa chỉ</option>
            <option value="district">Tâm điểm cấp quận</option>
            <option value="province">Tâm điểm cấp tỉnh</option>
          </select>
        </label>

        <label className="number-field">
          <span>Giá từ</span>
          <input type="number" min="0" step="0.5" placeholder="triệu" value={minPrice} onChange={(event) => setMinPrice(event.target.value)} />
        </label>

        <label className="number-field">
          <span>Giá đến</span>
          <input type="number" min="0" step="0.5" placeholder="triệu" value={maxPrice} onChange={(event) => setMaxPrice(event.target.value)} />
        </label>

        <label className="number-field">
          <span>DT từ</span>
          <input type="number" min="0" step="1" placeholder="m2" value={minArea} onChange={(event) => setMinArea(event.target.value)} />
        </label>

        <label className="number-field">
          <span>DT đến</span>
          <input type="number" min="0" step="1" placeholder="m2" value={maxArea} onChange={(event) => setMaxArea(event.target.value)} />
        </label>

        <label className="select-field">
          <span>Sắp xếp</span>
          <select value={sortBy} onChange={(event) => setSortBy(event.target.value as typeof sortBy)}>
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <div className="filter-actions">
          <label className="toggle-field">
            <input type="checkbox" checked={hasImageOnly} onChange={(event) => setHasImageOnly(event.target.checked)} />
            <span>Có ảnh</span>
          </label>
          <button type="button" onClick={resetFilters} disabled={!hasActiveFilters}>
            Xóa lọc
          </button>
        </div>
      </section>

      {activeTab === "search" ? (
        <section className="search-layout">
          <aside className="results-panel" aria-label="Danh sách phòng trọ">
            <div className="panel-head">
              <div>
                <p>Kết quả</p>
                <h2>{visibleItems.length.toLocaleString("vi-VN")} phòng trọ</h2>
              </div>
              <span>{markerCount.toLocaleString("vi-VN")} điểm</span>
            </div>

            <div className="source-pills" aria-label="Nguồn dữ liệu">
              {sources.map((source) => (
                <button
                  key={source}
                  type="button"
                  className={`source-pill source-${source} ${selectedSource === source ? "active" : ""}`}
                  onClick={() => setSelectedSource(selectedSource === source ? "all" : source)}
                >
                  <i />
                  {sourceLabel(source)}
                  <strong>{sourceTotals[source].toLocaleString("vi-VN")}</strong>
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
                  <div className="listing-thumb">
                    {imageUrl(item) ? <img src={imageUrl(item) ?? ""} alt={cleanDisplayText(item.title)} loading="lazy" /> : <span>Chưa có ảnh</span>}
                  </div>
                  <div className="listing-card-body">
                    <div className="listing-card-top">
                      <span className={`source-chip source-${item.source_name}`}>{sourceLabel(item.source_name)}</span>
                      <span>{formatDistrict(item.district)}</span>
                    </div>
                    <h3>{cleanDisplayText(item.title)}</h3>
                    <p>{cleanDisplayText(item.full_address) || "Địa chỉ đang được chuẩn hóa"}</p>
                    <div className="listing-tags">
                      <span>{formatArea(item.area_m2)}</span>
                      <span>{roomTypeLabel(item.room_type)}</span>
                      <span>{formatPrecision(item.geocode_precision)}</span>
                    </div>
                    <div className="listing-footer">
                      <strong>{formatCurrency(item.price_value)}</strong>
                      <span>{item.image_count} ảnh</span>
                    </div>
                  </div>
                </article>
              ))}
              {visibleItems.length === 0 ? (
                <div className="empty-state">
                  <strong>Chưa có tin phù hợp</strong>
                  <p>Thử nới khoảng giá, diện tích hoặc đổi khu vực để xem thêm phòng.</p>
                </div>
              ) : null}
            </div>
          </aside>

          <section className="map-workspace">
            <div className="map-toolbar">
              <div>
                <p>Bản đồ phòng trọ</p>
                <h2>{selectedListing ? formatDistrict(selectedListing.district) : "Chọn một tin để xem chi tiết"}</h2>
              </div>
              <div className="toolbar-facts">
                <span>{markerCount.toLocaleString("vi-VN")} tin có tọa độ</span>
                <span>{exactCount.toLocaleString("vi-VN")} tọa độ sát địa chỉ</span>
                <span>{referenceCount.toLocaleString("vi-VN")} tọa độ tham chiếu</span>
              </div>
            </div>

            <div className="map-stage">
              <ListingsMap listings={visibleItems} selectedListingId={selectedListing?.id ?? null} onSelectListing={setSelectedListingId} />
              <div className="map-legend" aria-label="Chú giải bản đồ">
                {sources.map((source) => (
                  <span key={source} className={`source-${source}`}>
                    <i />
                    {sourceLabel(source)}
                  </span>
                ))}
              </div>
            </div>
          </section>

          <aside className="preview-panel" aria-label="Xem nhanh tin đang chọn">
            {selectedListing ? (
              <>
                <div className={`preview-media ${selectedImage ? "" : "image-empty"}`}>
                  {selectedImage ? (
                    <img
                      src={selectedImage}
                      alt={cleanDisplayText(selectedListing.title)}
                      onError={(event) => {
                        event.currentTarget.style.display = "none";
                        event.currentTarget.parentElement?.classList.add("image-empty");
                      }}
                    />
                  ) : null}
                  <div className="image-placeholder">
                    <span>Chưa có ảnh xem trước</span>
                  </div>
                  <span className={`preview-source source-${selectedListing.source_name}`}>{sourceLabel(selectedListing.source_name)}</span>
                </div>

                <div className="preview-content">
                  <p className="preview-kicker">Tin đang chọn</p>
                  <h2>{cleanDisplayText(selectedListing.title)}</h2>
                  <strong className="preview-price">{formatCurrency(selectedListing.price_value)}</strong>
                  <p className="preview-address">{cleanDisplayText(selectedListing.full_address) || "Địa chỉ đang được chuẩn hóa"}</p>

                  <div className="preview-facts">
                    <div>
                      <span>Diện tích</span>
                      <strong>{formatArea(selectedListing.area_m2)}</strong>
                    </div>
                    <div>
                      <span>Loại phòng</span>
                      <strong>{roomTypeLabel(selectedListing.room_type)}</strong>
                    </div>
                    <div>
                      <span>Nội thất</span>
                      <strong>{furnishingLabel(selectedListing.furnishing_level)}</strong>
                    </div>
                    <div>
                      <span>Định vị</span>
                      <strong>{formatPrecision(selectedListing.geocode_precision)}</strong>
                    </div>
                  </div>

                  <div className="preview-tags">
                    <span>{selectedListing.image_count} ảnh</span>
                    <span>{selectedListing.amenity_count} tiện ích</span>
                    <span>{selectedListing.record_completeness_score ?? 0}/100 độ đầy đủ</span>
                  </div>

                  <a className="primary-link" href={selectedListing.canonical_url} target="_blank" rel="noreferrer">
                    Mở tin gốc
                  </a>
                </div>
              </>
            ) : (
              <div className="empty-preview">
                <strong>Chọn một tin để xem ảnh và chi tiết</strong>
                <p>Bạn có thể bấm vào thẻ tin bên trái hoặc marker trên bản đồ.</p>
              </div>
            )}
          </aside>
        </section>
      ) : (
        <section className="dashboard-view" aria-label="Dashboard phân tích phòng trọ">
          <div className="dashboard-hero">
            <div>
              <p>Dashboard phân tích</p>
              <h2>Đọc nhanh thị trường phòng trọ theo bộ lọc hiện tại</h2>
            </div>
            <div className="dashboard-summary">
              <span>Khu vực nổi bật: {topDistrict}</span>
              <span>Giá trung vị: {formatShortCurrency(medianPrice)}</span>
              <span>Độ đầy đủ TB: {avgScore ? `${avgScore.toLocaleString("vi-VN", { maximumFractionDigits: 1 })}/100` : "Chưa có"}</span>
            </div>
          </div>

          <div className="kpi-grid">
            <article className="kpi-card">
              <span>Tin đang phân tích</span>
              <strong>{visibleItems.length.toLocaleString("vi-VN")}</strong>
              <p>{formatPercent(initialData.total ? (visibleItems.length / initialData.total) * 100 : 0)} của snapshot online</p>
            </article>
            <article className="kpi-card">
              <span>Giá trung bình</span>
              <strong>{formatShortCurrency(avgPrice)}</strong>
              <p>Trung vị {formatShortCurrency(medianPrice)}</p>
            </article>
            <article className="kpi-card">
              <span>Diện tích TB</span>
              <strong>{avgArea ? `${avgArea.toLocaleString("vi-VN", { maximumFractionDigits: 1 })} m2` : "Chưa có"}</strong>
              <p>{areaValues.length.toLocaleString("vi-VN")} tin có diện tích</p>
            </article>
            <article className="kpi-card">
              <span>Ảnh tin đăng</span>
              <strong>{formatPercent(visibleItems.length ? (imageCount / visibleItems.length) * 100 : 0)}</strong>
              <p>{imageCount.toLocaleString("vi-VN")} tin có ảnh</p>
            </article>
            <article className="kpi-card">
              <span>Tọa độ bản đồ</span>
              <strong>{formatPercent(visibleItems.length ? (markerCount / visibleItems.length) * 100 : 0)}</strong>
              <p>{exactCount.toLocaleString("vi-VN")} tin sát địa chỉ</p>
            </article>
          </div>

          <div className="dashboard-grid">
            <article className="analytics-panel wide-panel">
              <div className="panel-title">
                <h3>Phân bổ giá thuê</h3>
                <span>{priceValues.length.toLocaleString("vi-VN")} tin có giá</span>
              </div>
              <ChartList items={priceChart} total={visibleItems.length} />
            </article>

            <article className="analytics-panel">
              <div className="panel-title">
                <h3>Nguồn dữ liệu</h3>
                <span>Theo bộ lọc</span>
              </div>
              <ChartList items={sourceChart} total={visibleItems.length} />
            </article>

            <article className="analytics-panel">
              <div className="panel-title">
                <h3>Loại phòng</h3>
                <span>Cơ cấu sản phẩm</span>
              </div>
              <ChartList items={roomChart} total={visibleItems.length} />
            </article>

            <article className="analytics-panel">
              <div className="panel-title">
                <h3>Diện tích</h3>
                <span>Nhóm diện tích</span>
              </div>
              <ChartList items={areaChart} total={visibleItems.length} />
            </article>

            <article className="analytics-panel">
              <div className="panel-title">
                <h3>Chất lượng tọa độ</h3>
                <span>Độ tin cậy bản đồ</span>
              </div>
              <ChartList items={precisionChart} total={visibleItems.length} />
            </article>

            <article className="analytics-panel">
              <div className="panel-title">
                <h3>Tỉnh thành nổi bật</h3>
                <span>Top khu vực</span>
              </div>
              <ChartList items={provinceChart} total={visibleItems.length} />
            </article>

            <article className="analytics-panel wide-panel">
              <div className="panel-title">
                <h3>Quận huyện có nhiều tin</h3>
                <span>Top 10 theo số lượng</span>
              </div>
              <ChartList items={districtChart} total={visibleItems.length} />
            </article>
          </div>
        </section>
      )}
    </main>
  );
}
