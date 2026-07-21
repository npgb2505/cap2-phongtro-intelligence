"use client";

/* Listing images come from heterogeneous crawler sources and cannot share a stable Next Image loader. */
/* eslint-disable @next/next/no-img-element */

import dynamic from "next/dynamic";
import {
  BarChart3,
  Building2,
  ChevronDown,
  Clock3,
  ExternalLink,
  Filter,
  Link2,
  MapPinOff,
  MapPinned,
  MessageCircle,
  PanelRightOpen,
  Phone,
  RotateCcw,
  Search,
  Workflow,
  X
} from "lucide-react";
import { startTransition, useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  Pie,
  PieChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import { formatDistrict } from "../lib/format";
import { fetchListingDetails } from "../lib/api";
import { EtlMonitor } from "./etl-monitor";
import {
  buildMapLocationGroups,
  listingAddressLevel,
  locationLevelCounts,
  MAP_LOCATION_LABELS,
  MapLocationLevel
} from "../lib/map-locations";
import { Listing, ListingMapResponse } from "../lib/types";

const ListingsMap = dynamic(() => import("./listings-map").then((module) => module.ListingsMap), {
  ssr: false
});

type Props = {
  initialData: ListingMapResponse;
  isLoading?: boolean;
  loadError?: string | null;
};

type TabKey = "search" | "dashboard" | "monitor";

type AmenityKey =
  | "has_aircon"
  | "has_private_wc"
  | "has_loft"
  | "has_parking"
  | "has_security"
  | "has_fingerprint_lock"
  | "allows_free_hours"
  | "has_balcony"
  | "has_kitchen"
  | "has_fridge"
  | "has_washer";

const RESULT_BATCH_SIZE = 60;
const SEARCH_DEBOUNCE_MS = 450;
const MAX_REASONABLE_MONTHLY_PRICE = 30_000_000;
const CHART_COLORS = ["#2563eb", "#0891b2", "#4f46e5", "#0ea5e9", "#60a5fa", "#14b8a6"];
const CHART_TOOLTIP_STYLE = {
  border: "1px solid rgba(77, 119, 171, 0.28)",
  borderRadius: 8,
  background: "rgba(248, 252, 255, 0.96)",
  boxShadow: "0 12px 32px rgba(31, 79, 137, 0.14)",
  color: "#18324f",
  fontSize: 12
};

const PROVINCE_GROUPS: Array<{ name: string; aliases: string[] }> = [
  { name: "Hà Nội", aliases: ["Hà Nội"] },
  { name: "Huế", aliases: ["Huế", "Thừa Thiên Huế"] },
  { name: "Cao Bằng", aliases: ["Cao Bằng"] },
  { name: "Điện Biên", aliases: ["Điện Biên"] },
  { name: "Hà Tĩnh", aliases: ["Hà Tĩnh"] },
  { name: "Lai Châu", aliases: ["Lai Châu"] },
  { name: "Lạng Sơn", aliases: ["Lạng Sơn"] },
  { name: "Nghệ An", aliases: ["Nghệ An"] },
  { name: "Quảng Ninh", aliases: ["Quảng Ninh"] },
  { name: "Sơn La", aliases: ["Sơn La"] },
  { name: "Thanh Hóa", aliases: ["Thanh Hóa"] },
  { name: "Tuyên Quang", aliases: ["Tuyên Quang", "Hà Giang"] },
  { name: "Lào Cai", aliases: ["Lào Cai", "Yên Bái"] },
  { name: "Thái Nguyên", aliases: ["Thái Nguyên", "Bắc Kạn"] },
  { name: "Phú Thọ", aliases: ["Phú Thọ", "Vĩnh Phúc", "Hòa Bình"] },
  { name: "Bắc Ninh", aliases: ["Bắc Ninh", "Bắc Giang"] },
  { name: "Hưng Yên", aliases: ["Hưng Yên", "Thái Bình"] },
  { name: "Hải Phòng", aliases: ["Hải Phòng", "Hải Dương"] },
  { name: "Ninh Bình", aliases: ["Ninh Bình", "Hà Nam", "Nam Định"] },
  { name: "Quảng Trị", aliases: ["Quảng Trị", "Quảng Bình"] },
  { name: "Đà Nẵng", aliases: ["Đà Nẵng", "Quảng Nam"] },
  { name: "Quảng Ngãi", aliases: ["Quảng Ngãi", "Kon Tum"] },
  { name: "Gia Lai", aliases: ["Gia Lai", "Bình Định"] },
  { name: "Khánh Hòa", aliases: ["Khánh Hòa", "Ninh Thuận"] },
  { name: "Lâm Đồng", aliases: ["Lâm Đồng", "Đắk Nông", "Bình Thuận"] },
  { name: "Đắk Lắk", aliases: ["Đắk Lắk", "Phú Yên"] },
  { name: "Hồ Chí Minh", aliases: ["Hồ Chí Minh", "TPHCM", "Bình Dương", "Bà Rịa - Vũng Tàu", "Bà Rịa, Vũng Tàu"] },
  { name: "Đồng Nai", aliases: ["Đồng Nai", "Bình Phước"] },
  { name: "Tây Ninh", aliases: ["Tây Ninh", "Long An"] },
  { name: "Cần Thơ", aliases: ["Cần Thơ", "Sóc Trăng", "Hậu Giang"] },
  { name: "Vĩnh Long", aliases: ["Vĩnh Long", "Bến Tre", "Trà Vinh"] },
  { name: "Đồng Tháp", aliases: ["Đồng Tháp", "Tiền Giang"] },
  { name: "Cà Mau", aliases: ["Cà Mau", "Bạc Liêu"] },
  { name: "An Giang", aliases: ["An Giang", "Kiên Giang"] }
];
const CURRENT_PROVINCES = PROVINCE_GROUPS
  .map((group) => group.name)
  .sort((first, second) => first.localeCompare(second, "vi", { sensitivity: "base" }));

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
  { value: "area_desc", label: "Diện tích lớn trước" }
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

const AMENITY_FLAGS: Array<{ key: AmenityKey; label: string }> = [
  { key: "has_aircon", label: "Máy lạnh" },
  { key: "has_private_wc", label: "WC riêng" },
  { key: "has_loft", label: "Gác lửng" },
  { key: "has_parking", label: "Giữ xe" },
  { key: "has_security", label: "An ninh" },
  { key: "has_fingerprint_lock", label: "Khóa vân tay" },
  { key: "allows_free_hours", label: "Giờ giấc tự do" },
  { key: "has_balcony", label: "Ban công" },
  { key: "has_kitchen", label: "Bếp" },
  { key: "has_fridge", label: "Tủ lạnh" },
  { key: "has_washer", label: "Máy giặt" }
];

function normalizeProvinceName(value: string) {
  return value
    .normalize("NFC")
    .trim()
    .replace(/^(tỉnh|thành phố|tp\.?)[\s:]+/i, "")
    .replace(/[.,-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLocaleLowerCase("vi-VN");
}

const PROVINCE_ALIAS_LOOKUP = new Map(
  PROVINCE_GROUPS.flatMap((group) => group.aliases.map((alias) => [normalizeProvinceName(alias), group.name] as const))
);

function canonicalProvince(value: string | null | undefined) {
  if (!value) {
    return null;
  }
  return PROVINCE_ALIAS_LOOKUP.get(normalizeProvinceName(value)) ?? null;
}

function cleanDisplayText(value: string | null | undefined) {
  return (value ?? "").replace(/[\u2014\u2013]/g, "-");
}

function cleanDescriptionText(value: string | null | undefined) {
  return cleanDisplayText(value)
    .replace(/https?:\/\/\S+/gi, "")
    .replace(/\b[a-f0-9]{64}\b/gi, "")
    .replace(/(?:^|\s)@(?:phongtro123|nhatot|mogi|thuephongtro|batdongsan|alonhadat)[,\s][\s\S]*$/i, "")
    .replace(/(?:phongtro123|nhatot|mogi|thuephongtro|batdongsan|alonhadat),\d+,[\s\S]*$/i, "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function mapLocationLabel(item: Listing, mappedLevel?: MapLocationLevel) {
  const level = mappedLevel ?? listingAddressLevel(item);
  return level ? MAP_LOCATION_LABELS[level] : "Chưa có vị trí";
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

function formatDisplayDate(value: string | null | undefined) {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("vi-VN").format(date);
}

function googleMapsSearchUrl(item: Listing) {
  const query = item.full_address || item.street_address || [item.district, item.province].filter(Boolean).join(", ");
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query || "Việt Nam")}`;
}

function phoneUrl(value: string | null | undefined) {
  const normalized = (value ?? "").replace(/[^\d+]/g, "");
  return /^0\d{9}$/.test(normalized) ? `tel:${normalized}` : null;
}

function socialContactUrl(value: string | null | undefined, allowedDomains: string[]) {
  if (!value) {
    return null;
  }

  try {
    const url = new URL(value);
    const hostname = url.hostname.toLowerCase().replace(/^www\./, "");
    const matchesDomain = allowedDomains.some(
      (domain) => hostname === domain || hostname.endsWith(`.${domain}`),
    );

    return (url.protocol === "https:" || url.protocol === "http:") && matchesDomain ? url.toString() : null;
  } catch {
    return null;
  }
}

function zaloUrl(value: string | null | undefined) {
  return socialContactUrl(value, ["zalo.me"]);
}

function facebookUrl(value: string | null | undefined) {
  return socialContactUrl(value, ["facebook.com", "fb.com", "messenger.com"]);
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

function formatNullable(value: string | number | boolean | null | undefined) {
  if (value === null || value === undefined || value === "") {
    return "Chưa có";
  }
  if (typeof value === "boolean") {
    return value ? "Có" : "Không";
  }
  if (typeof value === "number") {
    return value.toLocaleString("vi-VN", { maximumFractionDigits: 2 });
  }
  return cleanDisplayText(value);
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
  const candidate = item?.primary_image_url || item?.thumbnail_url || null;
  return candidate && /^https?:\/\//i.test(candidate) && !/(?:thumb_default|no[-_]image|placeholder|default[-_]image)/i.test(candidate)
    ? candidate
    : null;
}

function compareRecommendedListings(a: Listing, b: Listing) {
  const activeDelta = Number(b.status === "active") - Number(a.status === "active");
  if (activeDelta !== 0) {
    return activeDelta;
  }
  const directContactDelta = Number(Boolean(b.has_direct_contact)) - Number(Boolean(a.has_direct_contact));
  if (directContactDelta !== 0) {
    return directContactDelta;
  }
  const qualityDelta = (b.publication_quality_score ?? 0) - (a.publication_quality_score ?? 0);
  if (qualityDelta !== 0) {
    return qualityDelta;
  }
  const contactNameDelta = Number(Boolean(b.has_contact_name)) - Number(Boolean(a.has_contact_name));
  if (contactNameDelta !== 0) {
    return contactNameDelta;
  }
  return (
    (b.record_completeness_score ?? 0) - (a.record_completeness_score ?? 0) ||
    (b.image_count ?? 0) - (a.image_count ?? 0)
  );
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

function DebouncedSearchField({ value, onDebouncedChange }: { value: string; onDebouncedChange: (value: string) => void }) {
  const [draft, setDraft] = useState(value);

  useEffect(() => {
    setDraft(value);
  }, [value]);

  useEffect(() => {
    if (draft === value) {
      return;
    }
    const timeoutId = window.setTimeout(() => onDebouncedChange(draft), SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timeoutId);
  }, [draft, onDebouncedChange, value]);

  return (
    <label className="search-field">
      <span><Search size={14} strokeWidth={1.9} aria-hidden /> Tìm kiếm</span>
      <div className="input-with-icon">
        <Search size={17} strokeWidth={1.9} aria-hidden />
        <input
          type="search"
          placeholder="Tên đường, quận, tiêu đề"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
      </div>
    </label>
  );
}

function DetailGrid({ title, rows }: { title: string; rows: Array<[string, string | number | boolean | null | undefined]> }) {
  return (
    <section className="detail-section">
      <h3>{title}</h3>
      <div className="detail-grid">
        {rows.map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{formatNullable(value)}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

export function ListingsExplorer({ initialData, isLoading = false, loadError = null }: Props) {
  const [activeTab, setActiveTab] = useState<TabKey>("search");
  const [selectedProvince, setSelectedProvince] = useState<string>("all");
  const [selectedDistrict, setSelectedDistrict] = useState<string>("all");
  const [selectedRoomType, setSelectedRoomType] = useState<string>("all");
  const [selectedAmenities, setSelectedAmenities] = useState<AmenityKey[]>([]);
  const [hasImageOnly, setHasImageOnly] = useState(false);
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [minArea, setMinArea] = useState("");
  const [maxArea, setMaxArea] = useState("");
  const [sortBy, setSortBy] = useState<(typeof SORT_OPTIONS)[number]["value"]>("recommended");
  const [searchText, setSearchText] = useState("");
  const [resultLimit, setResultLimit] = useState(RESULT_BATCH_SIZE);
  const [selectedListingId, setSelectedListingId] = useState<string | null>(initialData.items[0]?.id ?? null);
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailedListing, setDetailedListing] = useState<Listing | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const priceOutlierCount = useMemo(
    () => initialData.items.filter((item) => (item.price_value ?? 0) > MAX_REASONABLE_MONTHLY_PRICE).length,
    [initialData.items]
  );
  const extremePriceOutlierCount = useMemo(
    () => initialData.items.filter((item) => (item.price_value ?? 0) >= 1_000_000_000).length,
    [initialData.items]
  );
  const roomTypes = useMemo(
    () => Array.from(new Set(initialData.items.map((item) => item.room_type).filter(Boolean) as string[])).sort(),
    [initialData.items]
  );
  const districts = useMemo(() => {
    if (selectedProvince === "all") {
      return [];
    }
    const provinceFiltered = initialData.items.filter(
      (item) => canonicalProvince(item.province) === selectedProvince
    );
    return Array.from(new Set(provinceFiltered.map((item) => item.district).filter(Boolean) as string[])).sort(
      (a, b) => formatDistrict(a).localeCompare(formatDistrict(b), "vi")
    );
  }, [initialData.items, selectedProvince]);

  const parsedMinPrice = minPrice ? Number(minPrice) * 1_000_000 : null;
  const parsedMaxPrice = maxPrice ? Number(maxPrice) * 1_000_000 : null;
  const parsedMinArea = minArea ? Number(minArea) : null;
  const parsedMaxArea = maxArea ? Number(maxArea) : null;

  const visibleItems = useMemo(() => {
    const keyword = searchText.trim().toLowerCase();
    return initialData.items
      .filter((item) => {
        const matchesProvince = selectedProvince === "all" || canonicalProvince(item.province) === selectedProvince;
        const matchesDistrict = selectedDistrict === "all" || item.district === selectedDistrict;
        const matchesRoomType = selectedRoomType === "all" || item.room_type === selectedRoomType;
        const matchesAmenities = selectedAmenities.every((amenity) => Boolean(item[amenity]));
        const matchesImage = !hasImageOnly || Boolean(imageUrl(item));
        const matchesReasonablePrice = item.price_value === null || item.price_value <= MAX_REASONABLE_MONTHLY_PRICE;
        const matchesMinPrice = parsedMinPrice === null || (item.price_value !== null && item.price_value >= parsedMinPrice);
        const matchesMaxPrice = parsedMaxPrice === null || (item.price_value !== null && item.price_value <= parsedMaxPrice);
        const matchesMinArea = parsedMinArea === null || (item.area_m2 !== null && item.area_m2 >= parsedMinArea);
        const matchesMaxArea = parsedMaxArea === null || (item.area_m2 !== null && item.area_m2 <= parsedMaxArea);
        const haystack = `${item.title} ${item.full_address ?? ""} ${item.street_address ?? ""} ${item.district ?? ""} ${item.ward ?? ""} ${item.room_type ?? ""}`.toLowerCase();
        const matchesKeyword = !keyword || haystack.includes(keyword);
        return (
          matchesProvince &&
          matchesDistrict &&
          matchesRoomType &&
          matchesAmenities &&
          matchesImage &&
          matchesReasonablePrice &&
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
        return compareRecommendedListings(a, b);
      });
  }, [
    hasImageOnly,
    initialData.items,
    parsedMaxArea,
    parsedMaxPrice,
    parsedMinArea,
    parsedMinPrice,
    selectedAmenities,
    selectedDistrict,
    selectedProvince,
    selectedRoomType,
    searchText,
    sortBy
  ]);

  const selectedListingBase = visibleItems.find((item) => item.id === selectedListingId) ?? visibleItems[0] ?? null;
  const selectedListing = detailedListing?.id === selectedListingBase?.id ? detailedListing : selectedListingBase;
  const selectedZaloUrl = zaloUrl(selectedListing?.contact_zalo_url);
  const selectedFacebookUrl = facebookUrl(selectedListing?.contact_facebook_url);

  useEffect(() => {
    let cancelled = false;
    if (!selectedListingBase) {
      setDetailedListing(null);
      return;
    }
    setDetailLoading(true);
    fetchListingDetails(selectedListingBase)
      .then((listing) => {
        if (!cancelled) {
          setDetailedListing(listing);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setDetailLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedListingBase]);
  const selectedImage = imageUrl(selectedListing);
  const displayedItems = visibleItems.slice(0, resultLimit);
  const selectedLatitude = selectedListing?.latitude ?? null;
  const selectedLongitude = selectedListing?.longitude ?? null;
  const selectedFocusCoordinate = useMemo<[number, number] | null>(() =>
    selectedLatitude !== null && selectedLongitude !== null
      ? [selectedLatitude, selectedLongitude]
      : null,
  [selectedLatitude, selectedLongitude]);
  const mapGroups = useMemo(() => buildMapLocationGroups(visibleItems), [visibleItems]);
  const mapLevelCounts = useMemo(() => locationLevelCounts(mapGroups), [mapGroups]);
  const mapGroupByListingId = useMemo(() => {
    const lookup = new Map<string, (typeof mapGroups)[number]>();
    for (const group of mapGroups) {
      for (const listingId of group.listingIds) {
        lookup.set(listingId, group);
      }
    }
    return lookup;
  }, [mapGroups]);
  const selectedMapGroup = selectedListing ? mapGroupByListingId.get(selectedListing.id) ?? null : null;
  const markerCount = mapGroups.length;
  const locatedListingCount = Object.values(mapLevelCounts).reduce((total, count) => total + count, 0);
  const imageCount = visibleItems.filter((item) => imageUrl(item)).length;
  const priceValues = visibleItems.map((item) => item.price_value).filter((value): value is number => Boolean(value && value > 1000));
  const areaValues = visibleItems.map((item) => item.area_m2).filter((value): value is number => Boolean(value && value > 0));
  const avgPrice = average(priceValues);
  const medianPrice = median(priceValues);
  const avgArea = average(areaValues);
  const sourceChart = topChartItems(countBy(visibleItems, (item) => item.source_name), 5, sourceLabel);
  const roomChart = topChartItems(countBy(visibleItems, (item) => item.room_type ?? "khac"), 6, roomTypeLabel);
  const provinceChart = topChartItems(countBy(visibleItems, (item) => canonicalProvince(item.province)), 8);
  const districtChart = topChartItems(countBy(visibleItems, (item) => item.district), 10, formatDistrict);
  const priceChart = bucketCounts(visibleItems, PRICE_BUCKETS, (item) => item.price_value);
  const areaChart = bucketCounts(visibleItems, AREA_BUCKETS, (item) => item.area_m2);
  const topDistrict = districtChart[0]?.label ?? "Chưa có";
  const amenityChart = AMENITY_FLAGS.map((flag) => ({
    label: flag.label,
    value: visibleItems.filter((item) => Boolean(item[flag.key])).length
  })).sort((a, b) => b.value - a.value);
  const amenityRadarData = amenityChart.slice(0, 8).map((item) => ({
    label: item.label,
    coverage: visibleItems.length ? Number(((item.value / visibleItems.length) * 100).toFixed(1)) : 0
  }));
  const scatterData = visibleItems
    .filter(
      (item) =>
        item.area_m2 !== null &&
        item.area_m2 > 0 &&
        item.area_m2 <= 150 &&
        item.price_value !== null &&
        item.price_value >= 500_000 &&
        item.price_value <= 30_000_000
    )
    .slice(0, 700)
    .map((item) => ({
      area: item.area_m2,
      price: Number(((item.price_value ?? 0) / 1_000_000).toFixed(2)),
      title: cleanDisplayText(item.title)
    }));
  const provinceStoryData = provinceChart.map((province) => {
    const matchingItems = visibleItems.filter((item) => canonicalProvince(item.province) === province.label);
    const provincePrices = matchingItems
      .map((item) => item.price_value)
      .filter((value): value is number => Boolean(value && value > 1000));
    return {
      label: province.label,
      value: province.value,
      averagePrice: Number((((average(provincePrices) ?? 0) / 1_000_000)).toFixed(1))
    };
  });
  const imageCoverage = visibleItems.length ? (imageCount / visibleItems.length) * 100 : 0;
  const markerCoverage = visibleItems.length ? (locatedListingCount / visibleItems.length) * 100 : 0;
  const statusChart = [
    { label: "Đang hoạt động", value: visibleItems.filter((item) => item.status === "active").length },
    { label: "Dữ liệu lịch sử", value: visibleItems.filter((item) => item.status === "expired").length },
    { label: "Đã ẩn", value: visibleItems.filter((item) => item.status === "hidden").length }
  ].filter((item) => item.value > 0);
  const geocodeChart = (["exact", "street", "district", "province"] as MapLocationLevel[]).map((level) => ({
    label: MAP_LOCATION_LABELS[level],
    value: mapLevelCounts[level]
  }));
  const hasActiveFilters =
    selectedProvince !== "all" ||
    selectedDistrict !== "all" ||
    selectedRoomType !== "all" ||
    selectedAmenities.length > 0 ||
    hasImageOnly ||
    minPrice ||
    maxPrice ||
    minArea ||
    maxArea ||
    searchText;
  const activeFilterCount = [
    selectedProvince !== "all",
    selectedDistrict !== "all",
    selectedRoomType !== "all",
    hasImageOnly,
    Boolean(minPrice),
    Boolean(maxPrice),
    Boolean(minArea),
    Boolean(maxArea),
    Boolean(searchText)
  ].filter(Boolean).length + selectedAmenities.length;

  function resetFilters() {
    setSelectedProvince("all");
    setSelectedDistrict("all");
    setSelectedRoomType("all");
    setSelectedAmenities([]);
    setHasImageOnly(false);
    setMinPrice("");
    setMaxPrice("");
    setMinArea("");
    setMaxArea("");
    setSearchText("");
    setSortBy("recommended");
    setResultLimit(RESULT_BATCH_SIZE);
  }

  function toggleAmenity(key: AmenityKey) {
    setSelectedAmenities((current) =>
      current.includes(key) ? current.filter((amenity) => amenity !== key) : [...current, key]
    );
  }

  function selectListing(listingId: string) {
    setSelectedListingId(listingId);
    setDetailOpen(true);
  }

  return (
    <main className={`app-shell view-${activeTab}`}>
      <header className="app-header">
        <div className="brand-block">
          <span className="brand-mark" aria-hidden><Building2 size={22} strokeWidth={1.9} /></span>
          <div>
            <p>PhongTrọ Intelligence</p>
            <h1>Rental data observatory</h1>
          </div>
        </div>

        <nav className="tab-nav" aria-label="Chuyển chế độ xem">
          <button className={activeTab === "search" ? "active" : ""} type="button" aria-pressed={activeTab === "search"} onClick={() => setActiveTab("search")}>
            <MapPinned size={17} strokeWidth={1.9} aria-hidden />
            <span className="tab-label-full">Bản đồ dữ liệu</span><span className="tab-label-short">Bản đồ</span>
          </button>
          <button className={activeTab === "dashboard" ? "active" : ""} type="button" aria-pressed={activeTab === "dashboard"} onClick={() => setActiveTab("dashboard")}>
            <BarChart3 size={17} strokeWidth={1.9} aria-hidden />
            <span className="tab-label-full">Phân tích dữ liệu</span><span className="tab-label-short">Phân tích</span>
          </button>
          <button className={activeTab === "monitor" ? "active" : ""} type="button" aria-pressed={activeTab === "monitor"} onClick={() => setActiveTab("monitor")}>
            <Workflow size={17} strokeWidth={1.9} aria-hidden />
            <span className="tab-label-full">Tiến trình ETL</span><span className="tab-label-short">ETL</span>
          </button>
        </nav>

      </header>

      {activeTab !== "monitor" ? <section className={`filter-strip ${filtersExpanded ? "expanded" : ""}`} aria-label="Bộ lọc dữ liệu">
        <div className="filter-primary">
          <DebouncedSearchField value={searchText} onDebouncedChange={setSearchText} />

          <label className="select-field province-field">
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
            <option value="all">Tất cả tỉnh thành</option>
            {CURRENT_PROVINCES.map((province) => (
              <option key={province} value={province}>
                {province}
              </option>
            ))}
          </select>
          </label>

          <label className="select-field district-field">
          <span>Quận huyện</span>
          <select
            value={selectedDistrict}
            disabled={selectedProvince === "all"}
            onChange={(event) => startTransition(() => setSelectedDistrict(event.target.value))}
          >
            <option value="all">{selectedProvince === "all" ? "Chọn tỉnh thành trước" : "Tất cả quận huyện"}</option>
            {districts.map((district) => (
              <option key={district} value={district}>
                {formatDistrict(district)}
              </option>
            ))}
          </select>
          </label>

          <label className="select-field room-field">
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

          <button
            className={`filter-toggle-button ${filtersExpanded ? "active" : ""}`}
            type="button"
            aria-expanded={filtersExpanded}
            onClick={() => setFiltersExpanded((current) => !current)}
          >
            <Filter size={17} strokeWidth={1.9} aria-hidden />
            Bộ lọc
            {activeFilterCount ? <span>{activeFilterCount}</span> : null}
          </button>

          <button className="reset-filter-button" type="button" onClick={resetFilters} disabled={!hasActiveFilters}>
            <RotateCcw size={16} strokeWidth={1.9} aria-hidden />
            <span>Xóa lọc</span>
          </button>
        </div>

        <div className="filter-secondary">

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
          </div>
        </div>

        <fieldset className="amenity-filter-field">
          <legend>Tiện ích cần có</legend>
          <div className="amenity-filter-options">
            {AMENITY_FLAGS.map((flag) => (
              <label className={selectedAmenities.includes(flag.key) ? "selected" : ""} key={flag.key}>
                <input
                  type="checkbox"
                  checked={selectedAmenities.includes(flag.key)}
                  onChange={() => toggleAmenity(flag.key)}
                />
                <span>{flag.label}</span>
              </label>
            ))}
          </div>
        </fieldset>
      </section> : null}

      {isLoading ? (
        <section className="loading-banner" aria-live="polite">
          <strong>Đang dựng snapshot ETL</strong>
          <span>Hệ thống đang ghép các index dữ liệu và chuẩn bị lớp bản đồ.</span>
        </section>
      ) : null}

      {loadError ? (
        <section className="loading-banner error-banner" role="alert">
          <strong>Không tải được dữ liệu</strong>
          <span>{loadError}</span>
        </section>
      ) : null}

      {activeTab === "search" ? (
        <section className="search-layout">
          <aside className="results-panel" aria-label="Danh sách phòng trọ">
            <div className="panel-head">
              <div>
                <p>Kho dữ liệu</p>
                <h2>{visibleItems.length.toLocaleString("vi-VN")} bản ghi</h2>
              </div>
            </div>

            <div className="listing-list">
              {displayedItems.map((item) => (
                <article
                  key={item.id}
                  className={`listing-card source-border-${item.source_name} ${item.id === selectedListing?.id ? "selected" : ""}`}
                  role="button"
                  tabIndex={0}
                  aria-pressed={item.id === selectedListing?.id}
                  onClick={() => selectListing(item.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      selectListing(item.id);
                    }
                  }}
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
                      <span>{mapLocationLabel(item, mapGroupByListingId.get(item.id)?.level)}</span>
                    </div>
                    <div className="listing-footer">
                      <strong>{formatCurrency(item.price_value)}</strong>
                      <span>{item.status === "active" ? "Còn hiệu lực" : "Dữ liệu lịch sử"}</span>
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
              {visibleItems.length > displayedItems.length ? (
                <button
                  className="load-more-button"
                  type="button"
                  onClick={() => setResultLimit((current) => current + RESULT_BATCH_SIZE)}
                >
                  <ChevronDown size={17} strokeWidth={1.9} aria-hidden />
                  Tải thêm {Math.min(RESULT_BATCH_SIZE, visibleItems.length - displayedItems.length).toLocaleString("vi-VN")} tin
                </button>
              ) : null}
            </div>
          </aside>

          <section className="map-workspace">
            <div className="map-toolbar">
              <div>
                <p>Không gian địa lý</p>
                <h2>{selectedListing ? formatDistrict(selectedListing.district) : "Chọn một tin để xem chi tiết"}</h2>
              </div>
              <div className="toolbar-facts">
                {!detailOpen && selectedListing ? (
                  <button className="open-detail-button" type="button" onClick={() => setDetailOpen(true)}>
                    <PanelRightOpen size={15} strokeWidth={1.9} aria-hidden />
                    Xem bản ghi
                  </button>
                ) : null}
              </div>
            </div>

            <div className="map-stage">
              <ListingsMap
                groups={mapGroups}
                selectedListingId={selectedListing?.id ?? null}
                focusCoordinate={selectedFocusCoordinate}
                onSelectListing={selectListing}
              />
              {selectedListing && (!selectedMapGroup || selectedMapGroup.level !== "exact") ? (
                <div className="map-quality-notice" role="status">
                  <MapPinOff size={16} strokeWidth={1.9} aria-hidden />
                  {!selectedMapGroup
                    ? "Tin đang chọn chưa có đủ dữ liệu để đặt lên bản đồ."
                    : selectedMapGroup.level === "street"
                      ? "Tin này chỉ xác định được tuyến đường; vùng nét đứt thể hiện phạm vi ước lượng, không phải số nhà chính xác."
                      : selectedMapGroup.level === "district"
                        ? "Tin này chỉ có tọa độ cấp quận; vùng nét đứt thể hiện phạm vi ước lượng quanh trung tâm quận huyện."
                        : "Tin này chỉ có tọa độ cấp tỉnh; vùng nét đứt thể hiện phạm vi ước lượng quanh trung tâm tỉnh thành."}
                </div>
              ) : null}
              <div className="map-legend" aria-label="Chú giải bản đồ">
                {(["exact", "street", "district", "province"] as MapLocationLevel[]).map((level) => (
                  <span key={level} className={`location-${level}`}>
                    <i />
                    {MAP_LOCATION_LABELS[level]}
                  </span>
                ))}
              </div>
            </div>
          </section>

          <aside className={`preview-panel ${detailOpen ? "open" : "closed"}`} aria-label="Xem nhanh tin đang chọn" aria-hidden={!detailOpen}>
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
                  <div className="preview-heading-row">
                    <p className="preview-kicker">Bản ghi đang chọn</p>
                    <button className="close-detail-button" type="button" aria-label="Đóng chi tiết" onClick={() => setDetailOpen(false)}>
                      <X size={18} strokeWidth={1.9} aria-hidden />
                    </button>
                  </div>
                  <h2>{cleanDisplayText(selectedListing.title)}</h2>
                  <strong className="preview-price">{formatCurrency(selectedListing.price_value)}</strong>
                  <p className="preview-address">{cleanDisplayText(selectedListing.full_address) || "Địa chỉ đang được chuẩn hóa"}</p>

                  {detailLoading ? <div className="detail-loading" role="status">Đang tải chi tiết bản ghi</div> : null}

                  <section className="preview-contact" aria-label="Thông tin người đăng">
                    <div>
                      <span>Người đăng</span>
                      <strong>{selectedListing.contact_name || "Chưa công khai"}</strong>
                    </div>
                    <div>
                      <span>Điện thoại</span>
                      {phoneUrl(selectedListing.contact_phone) ? (
                        <a href={phoneUrl(selectedListing.contact_phone) ?? undefined}>{selectedListing.contact_phone}</a>
                      ) : (
                        <strong>Chưa công khai</strong>
                      )}
                    </div>
                    <div className="contact-links">
                      {phoneUrl(selectedListing.contact_phone) ? (
                        <a href={phoneUrl(selectedListing.contact_phone) ?? undefined} aria-label="Gọi cho người đăng">
                          <Phone size={15} strokeWidth={1.9} aria-hidden /> Gọi
                        </a>
                      ) : null}
                      {selectedZaloUrl ? (
                        <a href={selectedZaloUrl} target="_blank" rel="noreferrer">
                          <MessageCircle size={15} strokeWidth={1.9} aria-hidden /> Zalo
                        </a>
                      ) : null}
                      {selectedFacebookUrl ? (
                        <a href={selectedFacebookUrl} target="_blank" rel="noreferrer">
                          <Link2 size={15} strokeWidth={1.9} aria-hidden /> Facebook
                        </a>
                      ) : null}
                    </div>
                  </section>

                  <section className="detail-section description-section">
                    <h3>Mô tả tin</h3>
                    <p className="description-text">{cleanDescriptionText(selectedListing.description_clean) || "Chưa có mô tả"}</p>
                  </section>

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
                      <strong>{mapLocationLabel(selectedListing, selectedMapGroup?.level)}</strong>
                    </div>
                  </div>

                  <DetailGrid
                    title="Khu vực"
                    rows={[
                      ["Tỉnh thành", canonicalProvince(selectedListing.province) ?? selectedListing.province],
                      ["Quận huyện", formatDistrict(selectedListing.district)],
                      ["Phường xã", selectedListing.ward],
                      ["Đường", selectedListing.street_address]
                    ]}
                  />

                  <p className="posted-date">Đăng ngày {formatDisplayDate(selectedListing.posted_at) || "chưa rõ"}</p>

                  <section className="detail-section">
                    <h3>Tiện ích</h3>
                    <div className="amenity-grid">
                      {AMENITY_FLAGS.filter((flag) => selectedListing[flag.key]).map((flag) => (
                        <span className="active" key={flag.key}>
                          {flag.label}
                        </span>
                      ))}
                    </div>
                    {AMENITY_FLAGS.some((flag) => selectedListing[flag.key]) ? null : <p>Chưa có thông tin tiện ích.</p>}
                  </section>

                  <div className="preview-actions">
                    <a className="secondary-link" href={googleMapsSearchUrl(selectedListing)} target="_blank" rel="noreferrer">
                      <MapPinned size={17} strokeWidth={1.9} aria-hidden />
                      Kiểm tra trên Google Maps
                    </a>
                    <a className="primary-link" href={selectedListing.canonical_url} target="_blank" rel="noreferrer">
                      Mở tin gốc
                      <ExternalLink size={17} strokeWidth={1.9} aria-hidden />
                    </a>
                  </div>
                </div>
              </>
            ) : (
              <div className="empty-preview">
                <strong>Chưa có bản ghi được chọn</strong>
                <p>Chi tiết dữ liệu sẽ xuất hiện tại đây.</p>
              </div>
            )}
          </aside>
        </section>
      ) : activeTab === "dashboard" ? (
        <section className="dashboard-view" aria-label="Dashboard phân tích phòng trọ">
          <div className="dashboard-hero">
            <div>
              <p>ETL intelligence</p>
              <h2>Từ dữ liệu thô đến tín hiệu thị trường có thể kiểm chứng</h2>
              <span className="dashboard-intro">Dữ liệu đa nguồn giữ nguyên vòng đời bản ghi để phục vụ phân tích lịch sử.</span>
            </div>
            <div className="dashboard-summary">
              <span>Khu vực nổi bật: {topDistrict}</span>
              <span>Giá trung vị: {formatShortCurrency(medianPrice)}</span>
              <span>Bao phủ ảnh: {formatPercent(imageCoverage)}</span>
              <span><Clock3 size={14} strokeWidth={1.9} aria-hidden /> {statusChart.find((item) => item.label === "Dữ liệu lịch sử")?.value.toLocaleString("vi-VN") ?? 0} bản ghi lịch sử</span>
            </div>
          </div>

          <div className="kpi-grid">
            <article className="kpi-card">
              <span>Bản ghi phân tích</span>
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
              <strong>{formatPercent(imageCoverage)}</strong>
              <p>{imageCount.toLocaleString("vi-VN")} tin có ảnh</p>
            </article>
            <article className="kpi-card">
              <span>Bao phủ vị trí</span>
              <strong>{formatPercent(markerCoverage)}</strong>
              <p>
                {locatedListingCount.toLocaleString("vi-VN")} tin quy về {markerCount.toLocaleString("vi-VN")} cụm
              </p>
            </article>
          </div>

          <div className="dashboard-grid">
            <article className="analytics-panel chart-span-7 data-story-panel">
              <div className="panel-title">
                <div>
                  <span>Vòng đời dữ liệu</span>
                  <h3>Dữ liệu gồm tin hiện hành và lịch sử</h3>
                </div>
                <strong>{visibleItems.length.toLocaleString("vi-VN")}</strong>
              </div>
              <div className="chart-canvas chart-canvas-compact">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={statusChart} layout="vertical" margin={{ top: 6, right: 24, left: 16, bottom: 2 }}>
                    <CartesianGrid horizontal={false} stroke="rgba(80, 122, 171, 0.13)" />
                    <XAxis type="number" tickLine={false} axisLine={false} tick={{ fill: "#607089", fontSize: 11 }} />
                    <YAxis type="category" dataKey="label" width={112} tickLine={false} axisLine={false} tick={{ fill: "#31445f", fontSize: 11 }} />
                    <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
                    <Bar dataKey="value" name="Bản ghi" radius={[0, 7, 7, 0]} fill="#176bda" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </article>

            <article className="analytics-panel chart-span-5 data-story-panel">
              <div className="panel-title">
                <div>
                  <span>Độ chính xác không gian</span>
                  <h3>Cấp định vị sau chuẩn hóa</h3>
                </div>
              </div>
              <div className="chart-canvas chart-canvas-compact">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={geocodeChart} dataKey="value" nameKey="label" innerRadius={48} outerRadius={76} paddingAngle={2}>
                      {geocodeChart.map((item, index) => <Cell key={item.label} fill={CHART_COLORS[index % CHART_COLORS.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
                    <Legend verticalAlign="middle" align="right" layout="vertical" iconType="circle" wrapperStyle={{ fontSize: 11, color: "#607089" }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </article>

            <article className="analytics-panel chart-span-8">
              <div className="panel-title">
                <h3>Phân bổ giá thuê</h3>
                <span>{priceValues.length.toLocaleString("vi-VN")} tin có giá</span>
              </div>
              <div className="chart-canvas chart-canvas-tall">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={priceChart} margin={{ top: 18, right: 18, left: 0, bottom: 4 }}>
                    <CartesianGrid vertical={false} stroke="rgba(80, 122, 171, 0.16)" />
                    <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: "#5e6e83", fontSize: 11 }} />
                    <YAxis tickLine={false} axisLine={false} tick={{ fill: "#5e6e83", fontSize: 11 }} width={54} />
                    <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
                    <Area type="monotone" dataKey="value" name="Số tin" stroke="#2563eb" strokeWidth={3} fill="#8ec5ff" fillOpacity={0.34} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </article>

            <article className="analytics-panel chart-span-4">
              <div className="panel-title">
                <h3>Cơ cấu loại phòng</h3>
                <span>{roomChart.length} nhóm</span>
              </div>
              <div className="chart-canvas chart-canvas-tall">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={roomChart} dataKey="value" nameKey="label" innerRadius={54} outerRadius={82} paddingAngle={2}>
                      {roomChart.map((item, index) => <Cell key={item.label} fill={CHART_COLORS[index % CHART_COLORS.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
                    <Legend verticalAlign="bottom" iconType="circle" wrapperStyle={{ fontSize: 11, color: "#5e6e83" }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </article>

            <article className="analytics-panel chart-span-6">
              <div className="panel-title">
                <h3>Giá theo diện tích</h3>
                <span>Mẫu {scatterData.length.toLocaleString("vi-VN")} tin</span>
              </div>
              <div className="chart-canvas">
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 18, right: 24, left: 0, bottom: 8 }}>
                    <CartesianGrid stroke="rgba(80, 122, 171, 0.16)" />
                    <XAxis type="number" dataKey="area" name="Diện tích" unit=" m2" tickLine={false} axisLine={false} tick={{ fill: "#5e6e83", fontSize: 11 }} />
                    <YAxis type="number" dataKey="price" name="Giá" unit=" tr" tickLine={false} axisLine={false} tick={{ fill: "#5e6e83", fontSize: 11 }} width={48} />
                    <Tooltip cursor={{ strokeDasharray: "4 4" }} contentStyle={CHART_TOOLTIP_STYLE} />
                    <Scatter name="Phòng trọ" data={scatterData} fill="#0891b2" fillOpacity={0.48} />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            </article>

            <article className="analytics-panel chart-span-6">
              <div className="panel-title">
                <h3>Dấu chân tiện ích</h3>
                <span>Tỷ lệ bao phủ</span>
              </div>
              <div className="chart-canvas">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={amenityRadarData} outerRadius="72%">
                    <PolarGrid stroke="rgba(80, 122, 171, 0.2)" />
                    <PolarAngleAxis dataKey="label" tick={{ fill: "#5e6e83", fontSize: 11 }} />
                    <Radar name="Tỷ lệ có tiện ích (%)" dataKey="coverage" stroke="#4f46e5" strokeWidth={2} fill="#60a5fa" fillOpacity={0.25} />
                    <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </article>

            <article className="analytics-panel chart-span-8">
              <div className="panel-title">
                <h3>Nguồn cung và mặt bằng giá theo tỉnh</h3>
                <span>Top {provinceStoryData.length} tỉnh thành</span>
              </div>
              <div className="chart-canvas chart-canvas-tall">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={provinceStoryData} margin={{ top: 18, right: 8, left: 0, bottom: 8 }}>
                    <CartesianGrid vertical={false} stroke="rgba(80, 122, 171, 0.16)" />
                    <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: "#5e6e83", fontSize: 11 }} />
                    <YAxis yAxisId="count" tickLine={false} axisLine={false} tick={{ fill: "#5e6e83", fontSize: 11 }} width={54} />
                    <YAxis yAxisId="price" orientation="right" tickLine={false} axisLine={false} tick={{ fill: "#5e6e83", fontSize: 11 }} width={46} unit=" tr" />
                    <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
                    <Legend verticalAlign="top" iconType="circle" wrapperStyle={{ fontSize: 11, color: "#5e6e83" }} />
                    <Bar yAxisId="count" dataKey="value" name="Số tin" fill="#7db8f5" radius={[6, 6, 0, 0]} />
                    <Line yAxisId="price" type="monotone" dataKey="averagePrice" name="Giá TB (triệu)" stroke="#4f46e5" strokeWidth={3} dot={{ r: 3, fill: "#4f46e5" }} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </article>

            <article className="analytics-panel chart-span-4">
              <div className="panel-title">
                <h3>Đóng góp dữ liệu</h3>
                <span>Theo nguồn crawl</span>
              </div>
              <div className="chart-canvas chart-canvas-tall">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={sourceChart} dataKey="value" nameKey="label" innerRadius={56} outerRadius={84} paddingAngle={3}>
                      {sourceChart.map((item, index) => <Cell key={item.label} fill={CHART_COLORS[index % CHART_COLORS.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
                    <Legend verticalAlign="bottom" iconType="circle" wrapperStyle={{ fontSize: 11, color: "#5e6e83" }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </article>

            <article className="analytics-panel chart-span-6">
              <div className="panel-title">
                <h3>Quận huyện tập trung nguồn cung</h3>
                <span>Top 10 khu vực</span>
              </div>
              <div className="chart-canvas chart-canvas-wide">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={districtChart} layout="vertical" margin={{ top: 14, right: 24, left: 12, bottom: 4 }}>
                    <CartesianGrid horizontal={false} stroke="rgba(80, 122, 171, 0.16)" />
                    <XAxis type="number" tickLine={false} axisLine={false} tick={{ fill: "#5e6e83", fontSize: 11 }} />
                    <YAxis type="category" dataKey="label" width={124} tickLine={false} axisLine={false} tick={{ fill: "#5e6e83", fontSize: 11 }} />
                    <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
                    <Bar dataKey="value" name="Số tin" fill="#2563eb" radius={[0, 6, 6, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </article>

            <article className="analytics-panel chart-span-6">
              <div className="panel-title">
                <h3>Không gian sống phổ biến</h3>
                <span>{areaValues.length.toLocaleString("vi-VN")} tin có diện tích</span>
              </div>
              <div className="chart-canvas chart-canvas-wide">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={areaChart} margin={{ top: 18, right: 18, left: 0, bottom: 4 }}>
                    <CartesianGrid vertical={false} stroke="rgba(80, 122, 171, 0.16)" />
                    <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: "#5e6e83", fontSize: 11 }} />
                    <YAxis tickLine={false} axisLine={false} tick={{ fill: "#5e6e83", fontSize: 11 }} width={54} />
                    <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
                    <Bar dataKey="value" name="Số tin" fill="#14b8a6" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </article>

            <article className="analytics-panel chart-span-12 insight-panel">
              <div className="panel-title">
                <h3>Kết luận từ lát cắt hiện tại</h3>
                <span>Tự tính theo bộ lọc</span>
              </div>
              <div className="insight-list">
                <p>
                  Nguồn cung tập trung mạnh nhất tại <strong>{topDistrict}</strong>, chiếm {districtChart[0] ? formatPercent((districtChart[0].value / Math.max(visibleItems.length, 1)) * 100) : "0%"} tập đang xem.
                </p>
                <p>
                  Giá trung vị là <strong>{formatShortCurrency(medianPrice)}</strong>, trong khi giá trung bình ở mức {formatShortCurrency(avgPrice)}. Chênh lệch này cho thấy ảnh hưởng của nhóm phòng giá cao.
                </p>
                <p>
                  Nhóm tiện ích nổi bật nhất là <strong>{amenityChart[0]?.label ?? "chưa xác định"}</strong>, xuất hiện trong {amenityChart[0] ? formatPercent((amenityChart[0].value / Math.max(visibleItems.length, 1)) * 100) : "0%"} số tin.
                </p>
                <p>
                  Đã loại <strong>{priceOutlierCount.toLocaleString("vi-VN")} tin trên 30 triệu/tháng</strong> trước khi tính toán. Trong đó {extremePriceOutlierCount.toLocaleString("vi-VN")} tin vượt 1 tỷ, chủ yếu do sai đơn vị hoặc tin bán, sang nhượng lọt vào dữ liệu thuê.
                </p>
              </div>
            </article>
          </div>
        </section>
      ) : (
        <EtlMonitor data={initialData} />
      )}
    </main>
  );
}
