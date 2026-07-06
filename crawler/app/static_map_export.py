from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from app.deploy_snapshot import DEFAULT_SOURCES, build_deploy_snapshot

KNOWN_SOURCES = {"phongtro123", "nhatot", "mogi", "thuephongtro", "batdongsan", "alonhadat"}


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


def _csv_columns(row: dict[str, str]) -> dict[str, object]:
    return {
        "title_raw": _string(row.get("title")),
        "price_text": _string(row.get("price_text")),
        "area_text": _string(row.get("area_text")),
        "map_reference_address": _string(row.get("map_reference_address")),
        "geocode_source": _string(row.get("geocode_source")),
        "geocode_display_name": _string(row.get("geocode_display_name")),
        "address_quality_score": _int(row.get("address_quality_score")),
        "posted_at": _string(row.get("posted_at")),
        "expired_at": _string(row.get("expired_at")),
        "freshness_days": _int(row.get("freshness_days")),
        "contact_name": _string(row.get("contact_name")),
        "contact_phone": _string(row.get("contact_phone")),
        "contact_zalo_url": _string(row.get("contact_zalo_url")),
        "contact_facebook_url": _string(row.get("contact_facebook_url")),
        "amenities_text": _string(row.get("amenities_text")),
        "has_aircon": _bool(row.get("has_aircon")),
        "has_private_wc": _bool(row.get("has_private_wc")),
        "has_loft": _bool(row.get("has_loft")),
        "has_parking": _bool(row.get("has_parking")),
        "has_security": _bool(row.get("has_security")),
        "has_fingerprint_lock": _bool(row.get("has_fingerprint_lock")),
        "allows_free_hours": _bool(row.get("allows_free_hours")),
        "has_balcony": _bool(row.get("has_balcony")),
        "has_kitchen": _bool(row.get("has_kitchen")),
        "has_fridge": _bool(row.get("has_fridge")),
        "has_washer": _bool(row.get("has_washer")),
        "description_clean": _string(row.get("description_clean")),
        "content_hash": _string(row.get("content_hash")),
    }


def _row_to_listing(row: dict[str, str]) -> dict[str, object]:
    primary_image_url = _string(row.get("primary_image_url"))
    listing = {
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
    listing.update(_csv_columns(row))
    return listing


def _valid_row(row: dict[str, str]) -> bool:
    return bool(row.get("listing_id")) and (row.get("source_name") or "") in KNOWN_SOURCES


def export_static_map(*, source_csv: Path, output_json: Path, chunk_size: int) -> dict[str, object]:
    with source_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    skipped_rows = len([row for row in rows if not _valid_row(row)])
    items = [_row_to_listing(row) for row in rows if _valid_row(row)]
    source_counts = Counter(str(item["source_name"]) for item in items)
    geocode_summary = Counter(str(item["geocode_precision"] or "none") for item in items)
    available_provinces = sorted({str(item["province"]) for item in items if item["province"]})

    output = {
        "total": len(items),
        "returned": len(items),
        "available_provinces": available_provinces,
        "geocode_summary": dict(geocode_summary),
        "deploy_source_counts": dict(source_counts),
        "skipped_rows": skipped_rows,
        "items": items,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    if chunk_size <= 0 or len(items) <= chunk_size:
        output_json.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        return output

    chunk_dir = output_json.parent / f"{output_json.stem}-chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    for old_chunk in chunk_dir.glob("*.json"):
        old_chunk.unlink()

    chunk_paths: list[str] = []
    for index in range(0, len(items), chunk_size):
        chunk = items[index:index + chunk_size]
        chunk_name = f"part-{index // chunk_size:03d}.json"
        chunk_path = chunk_dir / chunk_name
        chunk_path.write_text(json.dumps({"items": chunk}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        chunk_paths.append(f"{chunk_dir.name}/{chunk_name}")

    manifest = dict(output)
    manifest["items"] = []
    manifest["chunks"] = chunk_paths
    manifest["chunk_size"] = chunk_size
    manifest["dataset_mode"] = "chunked-full"
    output_json.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Export deploy snapshot as frontend static map JSON.")
    parser.add_argument("--source-csv", type=Path, default=Path("crawler/artifacts/deploy/listings_deploy.csv"))
    parser.add_argument("--output-json", type=Path, default=Path("web/public/data/listings-map.json"))
    parser.add_argument("--ensure-snapshot", action="store_true")
    parser.add_argument("--chunk-size", type=int, default=0)
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

    output = export_static_map(source_csv=source_csv, output_json=args.output_json.resolve(), chunk_size=args.chunk_size)
    print(
        json.dumps(
            {
                "output_json": str(args.output_json.resolve()),
                "total": output["total"],
                "returned": output["returned"],
                "deploy_source_counts": output["deploy_source_counts"],
                "chunks": len(output.get("chunks", [])),
                "skipped_rows": output.get("skipped_rows", 0),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
