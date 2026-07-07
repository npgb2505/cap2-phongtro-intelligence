import { ListingMapResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL;
const STATIC_DATA_PATH = process.env.NEXT_PUBLIC_STATIC_DATA_PATH;

export const emptyMapListings: ListingMapResponse = {
  total: 0,
  returned: 0,
  available_provinces: [],
  geocode_summary: {},
  deploy_source_counts: {},
  skipped_rows: 0,
  items: []
};

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
  const urls = [staticDataUrl()];
  if (API_URL) {
    urls.push(`${API_URL}/listings/map?limit=900`);
  }
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

export async function fetchMapListings(): Promise<ListingMapResponse> {
  const errors: unknown[] = [];

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
