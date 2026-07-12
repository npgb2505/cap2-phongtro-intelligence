CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE VIEW public.v_listing_map AS
SELECT
    listing_id AS id,
    source_name,
    source_post_id,
    canonical_url,
    title,
    title AS title_raw,
    title_clean,
    status,
    room_type,
    furnishing_level,
    price_text,
    price_value,
    price_per_m2,
    area_text,
    area_m2,
    street_address,
    ward,
    full_address,
    map_reference_address,
    district,
    province,
    latitude,
    longitude,
    geocode_precision,
    geocode_source,
    geocode_display_name,
    is_reference_coordinate,
    address_quality_score,
    record_completeness_score,
    posted_at,
    expired_at,
    freshness_days,
    contact_name,
    contact_phone,
    contact_zalo_url,
    contact_facebook_url,
    image_count,
    primary_image_url,
    primary_image_url AS thumbnail_url,
    amenities_text,
    amenity_count,
    has_aircon,
    has_private_wc,
    has_loft,
    has_parking,
    has_security,
    has_fingerprint_lock,
    allows_free_hours,
    has_balcony,
    has_kitchen,
    has_fridge,
    has_washer,
    description_clean,
    content_hash,
    updated_at
FROM public.curated_listings;

CREATE OR REPLACE VIEW public.v_dashboard_source_stats AS
SELECT
    source_name,
    COUNT(*) AS listing_count,
    COUNT(*) FILTER (WHERE latitude IS NOT NULL AND longitude IS NOT NULL) AS geocoded_count,
    ROUND(AVG(price_value)) AS avg_price,
    ROUND(AVG(area_m2)::numeric, 2) AS avg_area_m2
FROM public.curated_listings
WHERE status = 'active'
GROUP BY source_name;

CREATE OR REPLACE VIEW public.v_dashboard_location_stats AS
SELECT
    province,
    district,
    COUNT(*) AS listing_count,
    ROUND(AVG(price_value)) AS avg_price,
    ROUND(AVG(area_m2)::numeric, 2) AS avg_area_m2,
    COUNT(*) FILTER (WHERE geocode_precision = 'exact') AS exact_geocode_count,
    COUNT(*) FILTER (WHERE geocode_precision = 'district') AS district_geocode_count
FROM public.curated_listings
WHERE status = 'active'
GROUP BY province, district;

ALTER TABLE public.curated_listings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public read active listings" ON public.curated_listings;
DROP POLICY IF EXISTS "public read listings" ON public.curated_listings;

CREATE POLICY "public read listings"
ON public.curated_listings
FOR SELECT
TO anon
USING (true);

GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON public.curated_listings TO anon, authenticated;
GRANT SELECT ON public.v_listing_map TO anon, authenticated;
GRANT SELECT ON public.v_dashboard_source_stats TO anon, authenticated;
GRANT SELECT ON public.v_dashboard_location_stats TO anon, authenticated;
