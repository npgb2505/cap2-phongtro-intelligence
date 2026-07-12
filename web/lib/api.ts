import { Listing, ListingMapResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL;
const STATIC_DATA_PATH = process.env.NEXT_PUBLIC_STATIC_DATA_PATH;
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL?.replace(/\/$/, "");
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const SUPABASE_VIEW = process.env.NEXT_PUBLIC_SUPABASE_LISTINGS_VIEW ?? "v_listing_map";
const SUPABASE_PAGE_SIZE = clampNumber(process.env.NEXT_PUBLIC_SUPABASE_PAGE_SIZE, 1000, 100, 5000);
const SUPABASE_MAX_ROWS = clampNumber(process.env.NEXT_PUBLIC_SUPABASE_MAX_ROWS, 60000, 1000, 100000);

type SupabaseRow = Record<string, unknown>;

export const emptyMapListings: ListingMapResponse = {
  total: 0,
  returned: 0,
  available_provinces: [],
  geocode_summary: {},
  deploy_source_counts: {},
  skipped_rows: 0,
  items: []
};

function clampNumber(value: string | undefined, fallback: number, min: number, max: number) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.min(max, Math.max(min, Math.floor(parsed)));
}

function staticDataUrl() {
  if (STATIC_DATA_PATH) {
    return STATIC_DATA_PATH;
  }

  if (typeof window !== "undefined") {
    const baseSegment = window.location.pathname.split("/").filter(Boolean)[0];
    return baseSegment ? `/${baseSegment}/data/listings-map.json` : "/data/listings-map.json";
  }

  return "/data/listings-map.json";
}

function dataUrls() {
  const urls = [];
  if (API_URL) {
    urls.push(`${API_URL}/listings/map?limit=900`);
  }
  urls.push(staticDataUrl());
  return Array.from(new Set(urls));
}

function resolveChunkUrl(manifestUrl: string, chunkPath: string) {
  if (/^https?:\/\//.test(chunkPath) || chunkPath.startsWith("/")) {
    return chunkPath;
  }
  const baseUrl = /^https?:\/\//.test(manifestUrl)
    ? manifestUrl
    : new URL(manifestUrl, window.location.origin).toString();
  return new URL(chunkPath, baseUrl).toString();
}

async function fetchJson(url: string): Promise<ListingMapResponse> {
  const response = await fetch(url, {
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`Failed to load listings from ${url}`);
  }

  const payload = (await response.json()) as ListingMapResponse;
  if (!payload.chunks?.length) {
    return payload;
  }

  const chunkResponses = await Promise.all(
    payload.chunks.map(async (chunkPath) => {
      const chunkUrl = resolveChunkUrl(url, chunkPath);
      const chunkResponse = await fetch(chunkUrl, { cache: "no-store" });
      if (!chunkResponse.ok) {
        throw new Error(`Failed to load chunk ${chunkUrl}`);
      }
      return (await chunkResponse.json()) as Pick<ListingMapResponse, "items">;
    })
  );

  const items = chunkResponses.flatMap((chunk) => chunk.items ?? []);
  return {
    ...payload,
    returned: items.length,
    items
  };
}

function hasSupabaseConfig() {
  return Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);
}

function supabaseEndpoint() {
  const params = new URLSearchParams({
    select: "*",
    order: "updated_at.desc.nullslast"
  });
  return `${SUPABASE_URL}/rest/v1/${SUPABASE_VIEW}?${params.toString()}`;
}

function parseContentRange(value: string | null) {
  if (!value) {
    return null;
  }
  const match = value.match(/\/(\d+|\*)$/);
  if (!match || match[1] === "*") {
    return null;
  }
  return Number(match[1]);
}

function stringValue(row: SupabaseRow, key: string) {
  const value = row[key];
  if (value === null || value === undefined || value === "") {
    return null;
  }
  return String(value);
}

function numberValue(row: SupabaseRow, key: string) {
  const value = row[key];
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function booleanValue(row: SupabaseRow, key: string, fallback = false) {
  const value = row[key];
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  if (typeof value === "boolean") {
    return value;
  }
  return String(value).toLowerCase() === "true";
}

function statusValue(row: SupabaseRow): Listing["status"] {
  const status = stringValue(row, "status");
  if (status === "active" || status === "expired" || status === "hidden") {
    return status;
  }
  return "active";
}

function toListing(row: SupabaseRow): Listing {
  const id =
    stringValue(row, "id") ??
    stringValue(row, "listing_id") ??
    stringValue(row, "canonical_url") ??
    `${stringValue(row, "source_name") ?? "supabase"}:${stringValue(row, "source_post_id") ?? stringValue(row, "title") ?? "row"}`;

  return {
    id,
    source_name: stringValue(row, "source_name") ?? "supabase",
    source_post_id: stringValue(row, "source_post_id") ?? id,
    title_raw: stringValue(row, "title_raw"),
    title: stringValue(row, "title") ?? "Tin phòng trọ",
    price_text: stringValue(row, "price_text"),
    price_value: numberValue(row, "price_value"),
    price_per_m2: numberValue(row, "price_per_m2"),
    area_text: stringValue(row, "area_text"),
    area_m2: numberValue(row, "area_m2"),
    street_address: stringValue(row, "street_address"),
    ward: stringValue(row, "ward"),
    full_address: stringValue(row, "full_address"),
    map_reference_address: stringValue(row, "map_reference_address"),
    province: stringValue(row, "province"),
    district: stringValue(row, "district"),
    latitude: numberValue(row, "latitude"),
    longitude: numberValue(row, "longitude"),
    geocode_precision: stringValue(row, "geocode_precision"),
    geocode_source: stringValue(row, "geocode_source"),
    geocode_display_name: stringValue(row, "geocode_display_name"),
    is_reference_coordinate: booleanValue(row, "is_reference_coordinate"),
    address_quality_score: numberValue(row, "address_quality_score"),
    room_type: stringValue(row, "room_type"),
    furnishing_level: stringValue(row, "furnishing_level"),
    image_count: numberValue(row, "image_count") ?? 0,
    primary_image_url: stringValue(row, "primary_image_url"),
    posted_at: stringValue(row, "posted_at"),
    expired_at: stringValue(row, "expired_at"),
    freshness_days: numberValue(row, "freshness_days"),
    contact_name: stringValue(row, "contact_name"),
    contact_phone: stringValue(row, "contact_phone"),
    contact_zalo_url: stringValue(row, "contact_zalo_url"),
    contact_facebook_url: stringValue(row, "contact_facebook_url"),
    amenities_text: stringValue(row, "amenities_text"),
    amenity_count: numberValue(row, "amenity_count") ?? 0,
    has_aircon: booleanValue(row, "has_aircon"),
    has_private_wc: booleanValue(row, "has_private_wc"),
    has_loft: booleanValue(row, "has_loft"),
    has_parking: booleanValue(row, "has_parking"),
    has_security: booleanValue(row, "has_security"),
    has_fingerprint_lock: booleanValue(row, "has_fingerprint_lock"),
    allows_free_hours: booleanValue(row, "allows_free_hours"),
    has_balcony: booleanValue(row, "has_balcony"),
    has_kitchen: booleanValue(row, "has_kitchen"),
    has_fridge: booleanValue(row, "has_fridge"),
    has_washer: booleanValue(row, "has_washer"),
    description_clean: stringValue(row, "description_clean"),
    content_hash: stringValue(row, "content_hash"),
    record_completeness_score: numberValue(row, "record_completeness_score"),
    thumbnail_url: stringValue(row, "thumbnail_url") ?? stringValue(row, "primary_image_url"),
    canonical_url: stringValue(row, "canonical_url") ?? "#",
    status: statusValue(row)
  };
}

function buildResponseFromItems(items: ReturnType<typeof toListing>[], total?: number): ListingMapResponse {
  const geocodeSummary = items.reduce<Record<string, number>>((acc, item) => {
    const key = item.geocode_precision ?? "none";
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});

  const sourceCounts = items.reduce<Record<string, number>>((acc, item) => {
    acc[item.source_name] = (acc[item.source_name] ?? 0) + 1;
    return acc;
  }, {});

  return {
    total: total ?? items.length,
    returned: items.length,
    available_provinces: Array.from(new Set(items.map((item) => item.province).filter(Boolean) as string[])).sort(),
    geocode_summary: geocodeSummary,
    deploy_source_counts: sourceCounts,
    skipped_rows: 0,
    dataset_mode: "supabase-view",
    items
  };
}

async function fetchSupabaseListings(): Promise<ListingMapResponse> {
  if (!hasSupabaseConfig()) {
    throw new Error("Supabase env is not configured");
  }

  const items: ReturnType<typeof toListing>[] = [];
  let total: number | undefined;

  for (let start = 0; start < SUPABASE_MAX_ROWS; start += SUPABASE_PAGE_SIZE) {
    const end = Math.min(start + SUPABASE_PAGE_SIZE - 1, SUPABASE_MAX_ROWS - 1);
    const response = await fetch(supabaseEndpoint(), {
      cache: "no-store",
      headers: {
        apikey: SUPABASE_ANON_KEY as string,
        Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
        Prefer: "count=exact",
        Range: `${start}-${end}`,
        "Range-Unit": "items"
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to load Supabase listings: ${response.status}`);
    }

    total ??= parseContentRange(response.headers.get("content-range")) ?? undefined;
    const rows = (await response.json()) as SupabaseRow[];
    items.push(...rows.map(toListing));

    if (rows.length < SUPABASE_PAGE_SIZE || (total !== undefined && items.length >= total)) {
      break;
    }
  }

  return buildResponseFromItems(items, total);
}

export async function fetchMapListings(): Promise<ListingMapResponse> {
  const errors: unknown[] = [];

  if (hasSupabaseConfig()) {
    try {
      return await fetchSupabaseListings();
    } catch (error) {
      errors.push(error);
    }
  }

  for (const url of dataUrls()) {
    try {
      return await fetchJson(url);
    } catch (error) {
      errors.push(error);
    }
  }

  console.error("Unable to load listings data", errors);
  return emptyMapListings;
}
