from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from app.deploy_snapshot import DEFAULT_SOURCES, build_deploy_snapshot


def _string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _int(value: str | None) -> int | None:
    try:
        return int(value) if value not in {None, ""} else None
    except ValueError:
        return None


def _float(value: str | None) -> float | None:
    try:
        return float(value) if value not in {None, ""} else None
    except ValueError:
        return None


def _bool(value: str | None) -> bool:
    return str(value).lower() in {"true", "1", "yes"}


def _row_to_listing(row: dict[str, str]) -> dict[str, object]:
    primary_image_url = _string(row.get("primary_image_url"))
    return {
        "id": row.get("listing_id") or "",
        "source_name": row.get("source_name") or "unknown",
        "source_post_id": row.get("source_post_id") or "",
        "title": row.get("title_clean") or row.get("title") or "",
        "price_value": _int(row.get("price_value")),
        "price_per_m2": _float(row.get("price_per_m2")),
        "area_m2": _float(row.get("area_m2")),
        "street_address": _string(row.get("street_address")),
        "ward": _string(row.get("ward")),
        "full_address": _string(row.get("full_address")),
        "province": _string(row.get("province")),
        "district": _string(row.get("district")),
        "latitude": _float(row.get("latitude")),
        "longitude": _float(row.get("longitude")),
        "geocode_precision": _string(row.get("geocode_precision")),
        "is_reference_coordinate": _bool(row.get("is_reference_coordinate")),
        "room_type": _string(row.get("room_type")),
        "furnishing_level": _string(row.get("furnishing_level")),
        "image_count": _int(row.get("image_count")) or 0,
        "primary_image_url": primary_image_url,
        "amenity_count": _int(row.get("amenity_count")) or 0,
        "record_completeness_score": _int(row.get("record_completeness_score")),
        "thumbnail_url": primary_image_url,
        "canonical_url": row.get("canonical_url") or "",
        "status": row.get("status") or "active",
    }


def export_static_map(*, source_csv: Path, output_json: Path) -> dict[str, object]:
    with source_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    items = [_row_to_listing(row) for row in rows]
    source_counts = Counter(str(item["source_name"]) for item in items)
    geocode_summary = Counter(str(item["geocode_precision"] or "none") for item in items)
    available_provinces = sorted({str(item["province"]) for item in items if item["province"]})

    output = {
        "total": len(items),
        "returned": len(items),
        "available_provinces": available_provinces,
        "geocode_summary": dict(geocode_summary),
        "deploy_source_counts": dict(source_counts),
        "items": items,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Export deploy snapshot as frontend static map JSON.")
    parser.add_argument("--source-csv", type=Path, default=Path("crawler/artifacts/deploy/listings_deploy.csv"))
    parser.add_argument("--output-json", type=Path, default=Path("web/public/data/listings-map.json"))
    parser.add_argument("--ensure-snapshot", action="store_true")
    args = parser.parse_args()

    source_csv = args.source_csv.resolve()
    if args.ensure_snapshot and not source_csv.exists():
        build_deploy_snapshot(
            source_csv=Path("crawler/artifacts/curated/toan-quoc/listings_curated.csv").resolve(),
            output_csv=source_csv,
            summary_json=Path("crawler/artifacts/deploy/deploy_snapshot_summary.json").resolve(),
            sources=DEFAULT_SOURCES,
            per_source=1000,
        )

    output = export_static_map(source_csv=source_csv, output_json=args.output_json.resolve())
    print(
        json.dumps(
            {
                "output_json": str(args.output_json.resolve()),
                "total": output["total"],
                "returned": output["returned"],
                "deploy_source_counts": output["deploy_source_counts"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
