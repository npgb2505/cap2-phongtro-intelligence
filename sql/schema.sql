CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS crawl_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mode TEXT NOT NULL CHECK (mode IN ('bootstrap', 'incremental', 'reparse')),
    source_name TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'success', 'failed')),
    pages_requested INTEGER NOT NULL DEFAULT 0,
    listings_seen INTEGER NOT NULL DEFAULT 0,
    listings_new INTEGER NOT NULL DEFAULT 0,
    listings_updated INTEGER NOT NULL DEFAULT 0,
    listings_expired INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS raw_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    crawl_run_id UUID REFERENCES crawl_runs(id) ON DELETE SET NULL,
    source_name TEXT NOT NULL,
    snapshot_type TEXT NOT NULL CHECK (snapshot_type IN ('search', 'detail')),
    source_url TEXT NOT NULL,
    source_post_id TEXT,
    storage_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name TEXT NOT NULL,
    source_post_id TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    price_text TEXT,
    price_value BIGINT,
    area_text TEXT,
    area_m2 NUMERIC(10,2),
    room_type TEXT,
    province TEXT,
    district TEXT,
    ward TEXT,
    street_address TEXT,
    full_address TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geom GEOGRAPHY(POINT, 4326),
    geocode_confidence NUMERIC(5,2),
    posted_at TIMESTAMPTZ,
    expired_at TIMESTAMPTZ,
    contact_name TEXT,
    contact_phone TEXT,
    contact_zalo_url TEXT,
    author_joined_at DATE,
    author_listing_count INTEGER,
    image_count INTEGER NOT NULL DEFAULT 0,
    thumbnail_url TEXT,
    content_hash TEXT NOT NULL,
    raw_last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'hidden')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_name, source_post_id)
);

CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(status);
CREATE INDEX IF NOT EXISTS idx_listings_price ON listings(price_value);
CREATE INDEX IF NOT EXISTS idx_listings_province_district ON listings(province, district);
CREATE INDEX IF NOT EXISTS idx_listings_geom ON listings USING GIST(geom);

CREATE TABLE IF NOT EXISTS listing_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    width INTEGER,
    height INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS listing_amenities (
    listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    amenity TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (listing_id, amenity)
);

CREATE TABLE IF NOT EXISTS geocode_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    normalized_address TEXT NOT NULL UNIQUE,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    confidence NUMERIC(5,2),
    provider TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS curated_listings (
    listing_id UUID PRIMARY KEY,
    source_name TEXT NOT NULL DEFAULT 'unknown',
    source_post_id TEXT NOT NULL,
    canonical_url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    title_clean TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'hidden')),
    room_type TEXT,
    furnishing_level TEXT,
    price_text TEXT,
    price_value BIGINT,
    price_per_m2 NUMERIC(18,2),
    area_text TEXT,
    area_m2 NUMERIC(10,2),
    street_address TEXT,
    ward TEXT,
    district TEXT,
    province TEXT,
    full_address TEXT,
    map_reference_address TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geom GEOGRAPHY(POINT, 4326),
    geocode_precision TEXT,
    geocode_source TEXT,
    geocode_display_name TEXT,
    is_reference_coordinate BOOLEAN NOT NULL DEFAULT FALSE,
    address_quality_score INTEGER,
    record_completeness_score INTEGER,
    posted_at TIMESTAMPTZ,
    expired_at TIMESTAMPTZ,
    freshness_days INTEGER,
    contact_name TEXT,
    contact_phone TEXT,
    contact_zalo_url TEXT,
    contact_facebook_url TEXT,
    image_count INTEGER NOT NULL DEFAULT 0,
    primary_image_url TEXT,
    amenities_text TEXT,
    amenity_count INTEGER NOT NULL DEFAULT 0,
    has_aircon BOOLEAN NOT NULL DEFAULT FALSE,
    has_private_wc BOOLEAN NOT NULL DEFAULT FALSE,
    has_loft BOOLEAN NOT NULL DEFAULT FALSE,
    has_parking BOOLEAN NOT NULL DEFAULT FALSE,
    has_security BOOLEAN NOT NULL DEFAULT FALSE,
    has_fingerprint_lock BOOLEAN NOT NULL DEFAULT FALSE,
    allows_free_hours BOOLEAN NOT NULL DEFAULT FALSE,
    has_balcony BOOLEAN NOT NULL DEFAULT FALSE,
    has_kitchen BOOLEAN NOT NULL DEFAULT FALSE,
    has_fridge BOOLEAN NOT NULL DEFAULT FALSE,
    has_washer BOOLEAN NOT NULL DEFAULT FALSE,
    description_clean TEXT,
    content_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_curated_listings_status ON curated_listings(status);
CREATE INDEX IF NOT EXISTS idx_curated_listings_price ON curated_listings(price_value);
CREATE INDEX IF NOT EXISTS idx_curated_listings_province_district ON curated_listings(province, district);
CREATE INDEX IF NOT EXISTS idx_curated_listings_posted_at ON curated_listings(posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_curated_listings_geom ON curated_listings USING GIST(geom);
