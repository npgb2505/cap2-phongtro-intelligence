from __future__ import annotations

import argparse
import json

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db import get_engine


def check_supabase_load(min_rows: int) -> dict[str, int | str]:
    engine = get_engine()
    with engine.connect() as connection:
        listing_count = int(connection.execute(text("SELECT COUNT(*) FROM public.curated_listings")).scalar_one())
        view_count = int(connection.execute(text("SELECT COUNT(*) FROM public.v_listing_map")).scalar_one())
        geocoded_count = int(
            connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM public.v_listing_map
                    WHERE latitude IS NOT NULL
                      AND longitude IS NOT NULL
                    """
                )
            ).scalar_one()
        )
        source_count = int(
            connection.execute(
                text(
                    """
                    SELECT COUNT(DISTINCT source_name)
                    FROM public.curated_listings
                    """
                )
            ).scalar_one()
        )
        hidden_view_count = int(
            connection.execute(text("SELECT COUNT(*) FROM public.v_listing_map WHERE status = 'hidden'")).scalar_one()
        )
        bad_zalo_count = int(
            connection.execute(
                text("SELECT COUNT(*) FROM public.v_listing_map WHERE contact_zalo_url LIKE '%0909316890%'")
            ).scalar_one()
        )

    if listing_count < min_rows:
        raise RuntimeError(f"curated_listings has {listing_count} rows, expected at least {min_rows}")
    if view_count < min_rows:
        raise RuntimeError(f"v_listing_map has {view_count} rows, expected at least {min_rows}")
    if source_count < 1:
        raise RuntimeError("curated_listings has no recognized source")
    if geocoded_count < 1:
        raise RuntimeError("v_listing_map has no geocoded rows")
    if hidden_view_count:
        raise RuntimeError(f"v_listing_map exposes {hidden_view_count} hidden rows")
    if bad_zalo_count:
        raise RuntimeError(f"v_listing_map exposes {bad_zalo_count} rows with the source-site Zalo hotline")

    return {
        "status": "ok",
        "curated_listings_rows": listing_count,
        "v_listing_map_rows": view_count,
        "geocoded_rows": geocoded_count,
        "source_count": source_count,
        "hidden_view_rows": hidden_view_count,
        "bad_zalo_rows": bad_zalo_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Supabase curated listings load and read views")
    parser.add_argument("--min-rows", type=int, default=1, help="Minimum expected row count")
    args = parser.parse_args()

    try:
        result = check_supabase_load(args.min_rows)
    except SQLAlchemyError as exc:
        raise SystemExit("Could not query Supabase. Check PT_DATABASE_URL and SQL setup.") from exc

    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
