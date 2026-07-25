from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db import get_engine

CURATED_COLUMNS = [
    "listing_id",
    "source_name",
    "source_post_id",
    "canonical_url",
    "title",
    "title_clean",
    "status",
    "room_type",
    "furnishing_level",
    "price_text",
    "price_value",
    "price_per_m2",
    "area_text",
    "area_m2",
    "street_address",
    "ward",
    "district",
    "province",
    "full_address",
    "map_reference_address",
    "latitude",
    "longitude",
    "geocode_precision",
    "geocode_source",
    "geocode_display_name",
    "is_reference_coordinate",
    "address_quality_score",
    "record_completeness_score",
    "posted_at",
    "expired_at",
    "freshness_days",
    "contact_name",
    "contact_phone",
    "contact_zalo_url",
    "contact_facebook_url",
    "image_count",
    "primary_image_url",
    "amenities_text",
    "amenity_count",
    "has_aircon",
    "has_private_wc",
    "has_loft",
    "has_parking",
    "has_security",
    "has_fingerprint_lock",
    "allows_free_hours",
    "has_balcony",
    "has_kitchen",
    "has_fridge",
    "has_washer",
    "description_clean",
    "content_hash",
]


def _curated_table_sql(*, include_geom: bool) -> str:
    geom_column = ",\n    geom GEOGRAPHY(POINT, 4326)" if include_geom else ""
    geom_index = "\nCREATE INDEX IF NOT EXISTS idx_curated_listings_geom ON curated_listings USING GIST(geom);" if include_geom else ""
    return f"""
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
            {geom_column}
        );
        CREATE INDEX IF NOT EXISTS idx_curated_listings_status ON curated_listings(status);
        CREATE INDEX IF NOT EXISTS idx_curated_listings_price ON curated_listings(price_value);
        CREATE INDEX IF NOT EXISTS idx_curated_listings_province_district ON curated_listings(province, district);
        CREATE INDEX IF NOT EXISTS idx_curated_listings_posted_at ON curated_listings(posted_at DESC);
        ALTER TABLE curated_listings ADD COLUMN IF NOT EXISTS source_name TEXT NOT NULL DEFAULT 'unknown';
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'curated_listings'
                  AND column_name = 'price_per_m2'
                  AND (
                      data_type <> 'numeric'
                      OR numeric_precision <> 18
                      OR numeric_scale <> 2
                  )
            ) THEN
                ALTER TABLE curated_listings
                    ALTER COLUMN price_per_m2 TYPE NUMERIC(18,2);
            END IF;
        END
        $$;
        {geom_index}
    """


def _stage_table_sql() -> str:
    return """
        CREATE TEMP TABLE curated_listings_stage (
            listing_id UUID,
            source_name TEXT,
            source_post_id TEXT,
            canonical_url TEXT,
            title TEXT,
            title_clean TEXT,
            status TEXT,
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
            geocode_precision TEXT,
            geocode_source TEXT,
            geocode_display_name TEXT,
            is_reference_coordinate BOOLEAN,
            address_quality_score INTEGER,
            record_completeness_score INTEGER,
            posted_at TIMESTAMPTZ,
            expired_at TIMESTAMPTZ,
            freshness_days INTEGER,
            contact_name TEXT,
            contact_phone TEXT,
            contact_zalo_url TEXT,
            contact_facebook_url TEXT,
            image_count INTEGER,
            primary_image_url TEXT,
            amenities_text TEXT,
            amenity_count INTEGER,
            has_aircon BOOLEAN,
            has_private_wc BOOLEAN,
            has_loft BOOLEAN,
            has_parking BOOLEAN,
            has_security BOOLEAN,
            has_fingerprint_lock BOOLEAN,
            allows_free_hours BOOLEAN,
            has_balcony BOOLEAN,
            has_kitchen BOOLEAN,
            has_fridge BOOLEAN,
            has_washer BOOLEAN,
            description_clean TEXT,
            content_hash TEXT
        ) ON COMMIT DROP
    """


def _build_copy_sql(table_name: str) -> str:
    column_sql = ", ".join(CURATED_COLUMNS)
    return f"COPY {table_name} ({column_sql}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '')"


def _build_upsert_sql(*, include_geom: bool) -> str:
    select_sql = ", ".join(CURATED_COLUMNS)
    stage_defaults = {
        "source_name": "COALESCE(NULLIF(source_name, ''), 'unknown')",
        "source_post_id": "COALESCE(NULLIF(source_post_id, ''), listing_id::text)",
        "status": "COALESCE(NULLIF(status, ''), 'active')",
        "is_reference_coordinate": "COALESCE(is_reference_coordinate, FALSE)",
        "image_count": "COALESCE(image_count, 0)",
        "amenity_count": "COALESCE(amenity_count, 0)",
        "has_aircon": "COALESCE(has_aircon, FALSE)",
        "has_private_wc": "COALESCE(has_private_wc, FALSE)",
        "has_loft": "COALESCE(has_loft, FALSE)",
        "has_parking": "COALESCE(has_parking, FALSE)",
        "has_security": "COALESCE(has_security, FALSE)",
        "has_fingerprint_lock": "COALESCE(has_fingerprint_lock, FALSE)",
        "allows_free_hours": "COALESCE(allows_free_hours, FALSE)",
        "has_balcony": "COALESCE(has_balcony, FALSE)",
        "has_kitchen": "COALESCE(has_kitchen, FALSE)",
        "has_fridge": "COALESCE(has_fridge, FALSE)",
        "has_washer": "COALESCE(has_washer, FALSE)",
    }
    stage_select_sql = ", ".join(
        f"{stage_defaults[column]} AS {column}" if column in stage_defaults else column
        for column in CURATED_COLUMNS
    )
    deduped_cte = f"""
        WITH deduped_stage AS (
            SELECT DISTINCT ON (listing_id)
                {stage_select_sql}
            FROM curated_listings_stage
            ORDER BY
                listing_id,
                posted_at DESC NULLS LAST,
                record_completeness_score DESC NULLS LAST,
                source_post_id DESC
        )
    """
    updates = []
    for column in CURATED_COLUMNS:
        if column == "listing_id":
            continue
        updates.append(f"{column} = EXCLUDED.{column}")
    updates.append("updated_at = NOW()")

    if include_geom:
        updates.append(
            "geom = CASE "
            "WHEN EXCLUDED.latitude IS NOT NULL AND EXCLUDED.longitude IS NOT NULL "
            "THEN ST_SetSRID(ST_MakePoint(EXCLUDED.longitude, EXCLUDED.latitude), 4326)::geography "
            "ELSE NULL END"
        )
        return f"""
        {deduped_cte}
        INSERT INTO curated_listings (
            {select_sql},
            geom
        )
        SELECT
            {select_sql},
            CASE
                WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                THEN ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography
                ELSE NULL
            END AS geom
        FROM deduped_stage
        ON CONFLICT (listing_id) DO UPDATE SET
            {", ".join(updates)}
    """
    return f"""
        {deduped_cte}
        INSERT INTO curated_listings (
            {select_sql}
        )
        SELECT
            {select_sql}
        FROM deduped_stage
        ON CONFLICT (listing_id) DO UPDATE SET
            {", ".join(updates)}
    """


def load_curated_snapshot(csv_path: Path, *, delete_missing: bool = True) -> dict[str, int | str]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing curated CSV: {csv_path}")

    engine = get_engine()
    dbapi_conn = engine.raw_connection()
    inserted_or_updated = 0
    deleted = 0
    staged = 0
    has_postgis = False
    try:
        with dbapi_conn.cursor() as cursor:
            cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_available_extensions WHERE name='postgis')")
            has_postgis = bool(cursor.fetchone()[0])
            if has_postgis:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis")
            cursor.execute(_curated_table_sql(include_geom=has_postgis))
            cursor.execute(_stage_table_sql())

            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                with cursor.copy(_build_copy_sql("curated_listings_stage")) as copy:
                    while chunk := handle.read(1024 * 1024):
                        copy.write(chunk)

            cursor.execute("SELECT COUNT(*) FROM curated_listings_stage")
            staged = int(cursor.fetchone()[0])

            cursor.execute(_build_upsert_sql(include_geom=has_postgis))
            inserted_or_updated = cursor.rowcount if cursor.rowcount != -1 else staged

            if delete_missing:
                cursor.execute(
                    """
                    DELETE FROM curated_listings target
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM curated_listings_stage stage
                        WHERE stage.listing_id = target.listing_id
                    )
                    """
                )
                deleted = cursor.rowcount if cursor.rowcount != -1 else 0
        dbapi_conn.commit()
    except Exception:
        dbapi_conn.rollback()
        raise
    finally:
        dbapi_conn.close()

    return {
        "csv_path": str(csv_path),
        "postgis_enabled": "true" if has_postgis else "false",
        "staged_rows": staged,
        "upserted_rows": inserted_or_updated,
        "deleted_rows": deleted,
    }


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Load curated listing snapshot into PostgreSQL")
    parser.add_argument(
        "--csv",
        type=Path,
        default=settings.listing_dataset_path,
        help="Path to curated CSV snapshot",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Upsert this batch without deleting rows absent from the input CSV.",
    )
    args = parser.parse_args()

    try:
        result = load_curated_snapshot(args.csv.resolve(), delete_missing=not args.keep_existing)
    except SQLAlchemyError as exc:
        raise SystemExit(
            "Could not connect and load curated data into PostgreSQL. "
            "Check PT_DATABASE_URL or backend/.env before retrying."
        ) from exc

    print(result)


if __name__ == "__main__":
    main()
