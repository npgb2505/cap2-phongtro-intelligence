export type Listing = {
  id: string;
  source_name: string;
  source_post_id: string;
  title: string;
  price_value: number | null;
  price_per_m2: number | null;
  area_m2: number | null;
  street_address: string | null;
  ward: string | null;
  full_address: string | null;
  province: string | null;
  district: string | null;
  latitude: number | null;
  longitude: number | null;
  geocode_precision: string | null;
  is_reference_coordinate: boolean;
  room_type: string | null;
  furnishing_level: string | null;
  image_count: number;
  primary_image_url: string | null;
  amenity_count: number;
  record_completeness_score: number | null;
  thumbnail_url: string | null;
  canonical_url: string;
  status: "active" | "expired" | "hidden";
};

export type ListingMapResponse = {
  total: number;
  returned: number;
  available_provinces: string[];
  geocode_summary: Record<string, number>;
  items: Listing[];
};
