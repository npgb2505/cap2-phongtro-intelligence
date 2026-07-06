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

function formatCurrency(value: number | null) {
  if (!value || value < 1000) {
    return "Liên hệ";
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} triệu/tháng`;
  }
  return `${value.toLocaleString("vi-VN")} VND`;
}

function formatArea(value: number | null) {
  if (!value) {
    return "Chưa rõ diện tích";
  }
  return `${value.toLocaleString("vi-VN", { maximumFractionDigits: 1 })} m2`;
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

function sourceCounts(items: Listing[]) {
  return items.reduce<Record<string, number>>((acc, item) => {
    acc[item.source_name] = (acc[item.source_name] ?? 0) + 1;
    return acc;
  }, {});
}

export function ListingsExplorer({ initialData }: Props) {
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

  const counts = useMemo(() => sourceCounts(initialData.items), [initialData.items]);
  const sources = useMemo(() => Object.keys(counts).sort(), [counts]);
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
  const locatedCount = useMemo(
    () => initialData.items.filter((item) => item.latitude && item.longitude).length,
    [initialData.items]
  );
  const imageCount = useMemo(
    () => initialData.items.filter((item) => imageUrl(item)).length,
    [initialData.items]
  );

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

  const exactCount = initialData.geocode_summary.exact ?? 0;
  const districtCount = initialData.geocode_summary.district ?? 0;
  const provinceCount = initialData.geocode_summary.province ?? 0;
  const selectedListing = visibleItems.find((item) => item.id === selectedListingId) ?? visibleItems[0] ?? null;
  const markerCount = visibleItems.filter((item) => item.latitude && item.longitude).length;
  const selectedImage = imageUrl(selectedListing);
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
      <header className="topbar">
        <div className="brand-block">
          <span className="status-dot" aria-hidden />
          <div>
            <p>PhongTrọ Intelligence</p>
            <h1>Bản đồ tìm phòng trọ</h1>
          </div>
        </div>
        <div className="topbar-metrics" aria-label="Tổng quan dữ liệu">
          <div>
            <span>Kho tin</span>
            <strong>{initialData.total.toLocaleString("vi-VN")}</strong>
          </div>
          <div>
            <span>Đang lọc</span>
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

      <section className="control-strip" aria-label="Bộ lọc tìm phòng">
        <label className="search-field">
          <span>Tìm kiếm</span>
          <input
            type="search"
            placeholder="Nhập tên đường, quận, tiêu đề..."
            value={searchText}
            onChange={(event) => {
              const nextValue = event.target.value;
              startTransition(() => setSearchText(nextValue));
            }}
          />
        </label>

        <label className="select-field">
          <span>Tỉnh / thành</span>
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
          <span>Quận / huyện</span>
          <select
            value={selectedDistrict}
            onChange={(event) => {
              const nextValue = event.target.value;
              startTransition(() => setSelectedDistrict(nextValue));
            }}
          >
            <option value="all">Tất cả khu vực</option>
            {districts.map((district) => (
              <option key={district} value={district}>
                {formatDistrict(district)}
              </option>
            ))}
          </select>
        </label>

        <label className="select-field">
          <span>Nguồn tin</span>
          <select
            value={selectedSource}
            onChange={(event) => {
              const nextValue = event.target.value;
              startTransition(() => setSelectedSource(nextValue));
            }}
          >
            <option value="all">Tất cả nguồn</option>
            {sources.map((source) => (
              <option key={source} value={source}>
                {sourceLabel(source)} ({counts[source].toLocaleString("vi-VN")})
              </option>
            ))}
          </select>
        </label>

        <label className="select-field">
          <span>Loại phòng</span>
          <select
            value={selectedRoomType}
            onChange={(event) => {
              const nextValue = event.target.value;
              startTransition(() => setSelectedRoomType(nextValue));
            }}
          >
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
          <select
            value={selectedPrecision}
            onChange={(event) => {
              const nextValue = event.target.value;
              startTransition(() => setSelectedPrecision(nextValue));
            }}
          >
            <option value="all">Tất cả tọa độ</option>
            <option value="exact">Sát địa chỉ</option>
            <option value="district">Tâm điểm cấp quận</option>
            <option value="province">Tâm điểm cấp tỉnh</option>
          </select>
        </label>

        <label className="number-field">
          <span>Giá từ</span>
          <input
            type="number"
            min="0"
            step="0.5"
            placeholder="triệu"
            value={minPrice}
            onChange={(event) => setMinPrice(event.target.value)}
          />
        </label>

        <label className="number-field">
          <span>Giá đến</span>
          <input
            type="number"
            min="0"
            step="0.5"
            placeholder="triệu"
            value={maxPrice}
            onChange={(event) => setMaxPrice(event.target.value)}
          />
        </label>

        <label className="number-field">
          <span>Diện tích từ</span>
          <input
            type="number"
            min="0"
            step="1"
            placeholder="m2"
            value={minArea}
            onChange={(event) => setMinArea(event.target.value)}
          />
        </label>

        <label className="number-field">
          <span>Diện tích đến</span>
          <input
            type="number"
            min="0"
            step="1"
            placeholder="m2"
            value={maxArea}
            onChange={(event) => setMaxArea(event.target.value)}
          />
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
            <input
              type="checkbox"
              checked={hasImageOnly}
              onChange={(event) => setHasImageOnly(event.target.checked)}
            />
            <span>Chỉ tin có ảnh</span>
          </label>
          <button type="button" onClick={resetFilters} disabled={!hasActiveFilters}>
            Xóa lọc
          </button>
        </div>
      </section>

      <section className="workspace-grid">
        <aside className="results-panel" aria-label="Danh sách phòng trọ">
          <div className="panel-head">
            <div>
              <p>Kết quả phù hợp</p>
              <h2>{visibleItems.length.toLocaleString("vi-VN")} phòng trọ</h2>
            </div>
            <span>{markerCount.toLocaleString("vi-VN")} điểm</span>
          </div>

          <div className="source-pills" aria-label="Phân bổ nguồn tin">
            {sources.map((source) => (
              <button
                key={source}
                type="button"
                className={`source-pill source-${source} ${selectedSource === source ? "active" : ""}`}
                onClick={() => setSelectedSource(selectedSource === source ? "all" : source)}
              >
                <i />
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
                <div className="listing-thumb">
                  {imageUrl(item) ? (
                    <img src={imageUrl(item) ?? ""} alt={item.title} loading="lazy" />
                  ) : (
                    <span>Chưa có ảnh</span>
                  )}
                </div>
                <div className="listing-card-body">
                  <div className="listing-card-top">
                    <span className={`source-chip source-${item.source_name}`}>{sourceLabel(item.source_name)}</span>
                    <span>{formatDistrict(item.district)}</span>
                  </div>
                  <h3>{item.title}</h3>
                  <p>{item.full_address ?? "Địa chỉ đang được chuẩn hóa"}</p>
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
              <span>{locatedCount.toLocaleString("vi-VN")} tin có tọa độ</span>
              <span>{exactCount.toLocaleString("vi-VN")} tọa độ sát địa chỉ</span>
              <span>{(districtCount + provinceCount).toLocaleString("vi-VN")} tọa độ tham chiếu</span>
            </div>
          </div>

          <div className="map-stage">
            <ListingsMap
              listings={visibleItems}
              selectedListingId={selectedListing?.id ?? null}
              onSelectListing={setSelectedListingId}
            />
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
                    alt={selectedListing.title}
                    onError={(event) => {
                      event.currentTarget.style.display = "none";
                      event.currentTarget.parentElement?.classList.add("image-empty");
                    }}
                  />
                ) : null}
                <div className="image-placeholder">
                  <span>Chưa có ảnh xem trước</span>
                </div>
                <span className={`preview-source source-${selectedListing.source_name}`}>
                  {sourceLabel(selectedListing.source_name)}
                </span>
              </div>

              <div className="preview-content">
                <p className="preview-kicker">Tin đang chọn</p>
                <h2>{selectedListing.title}</h2>
                <strong className="preview-price">{formatCurrency(selectedListing.price_value)}</strong>
                <p className="preview-address">{selectedListing.full_address ?? "Địa chỉ đang được chuẩn hóa"}</p>

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
    </main>
  );
}
