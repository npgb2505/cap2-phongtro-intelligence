import { ListingMapResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const STATIC_DATA_PATH = process.env.NEXT_PUBLIC_STATIC_DATA_PATH;

export const fallbackMapListings: ListingMapResponse = {
  total: 2,
  returned: 2,
  available_provinces: ["Ho Chi Minh"],
  geocode_summary: { district: 2 },
  items: [
    {
      id: "fallback-1",
      source_name: "fallback",
      source_post_id: "708737",
      title: "Phong tro Quan 11 - giap Quan 10",
      price_value: 4500000,
      price_per_m2: 300000,
      area_m2: 15,
      street_address: "49/10 Duong Au Co",
      ward: "Phuong Hoa Binh",
      full_address: "49/10 Duong Au Co, Phuong Hoa Binh, Ho Chi Minh",
      province: "Ho Chi Minh",
      district: "Quan 11",
      latitude: 10.7672,
      longitude: 106.6417,
      geocode_precision: "district",
      is_reference_coordinate: true,
      room_type: "phong_tro",
      furnishing_level: "full",
      image_count: 0,
      primary_image_url: null,
      amenity_count: 4,
      record_completeness_score: 82,
      thumbnail_url: null,
      canonical_url: "https://phongtro123.com/",
      status: "active"
    },
    {
      id: "fallback-2",
      source_name: "fallback",
      source_post_id: "702592",
      title: "Ky tuc xa Quan 5",
      price_value: 1300000,
      price_per_m2: 65000,
      area_m2: 20,
      street_address: "Nguyen Trai",
      ward: null,
      full_address: "Nguyen Trai, Quan 5, Ho Chi Minh",
      province: "Ho Chi Minh",
      district: "Quan 5",
      latitude: 10.7585,
      longitude: 106.6811,
      geocode_precision: "district",
      is_reference_coordinate: true,
      room_type: "o_ghep",
      furnishing_level: "partial",
      image_count: 0,
      primary_image_url: null,
      amenity_count: 2,
      record_completeness_score: 75,
      thumbnail_url: null,
      canonical_url: "https://phongtro123.com/",
      status: "active"
    }
  ]
};

function dataUrl() {
  return STATIC_DATA_PATH || `${API_URL}/listings/map?limit=900`;
}

export async function fetchMapListings(): Promise<ListingMapResponse> {
  try {
    const response = await fetch(dataUrl(), {
      cache: "no-store"
    });
    if (!response.ok) {
      throw new Error("Failed to load listings");
    }
    return (await response.json()) as ListingMapResponse;
  } catch {
    return fallbackMapListings;
  }
}
