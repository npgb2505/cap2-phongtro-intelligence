from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from app.deploy_snapshot import DEFAULT_SOURCES, build_deploy_snapshot

KNOWN_SOURCES = {"phongtro123", "nhatot", "mogi"}
VIETNAM_TIMEZONE = timezone(timedelta(hours=7))


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


def _detail_columns(row: dict[str, str]) -> dict[str, object]:
    detail = {
        "title_raw": _string(row.get("title")),
        "price_text": _string(row.get("price_text")),
        "price_per_m2": _float(row.get("price_per_m2")),
        "area_text": _string(row.get("area_text")),
        "map_reference_address": _string(row.get("map_reference_address")),
        "geocode_source": _string(row.get("geocode_source")),
        "geocode_display_name": _string(row.get("geocode_display_name")),
        "address_quality_score": _int(row.get("address_quality_score")),
        "ward": _string(row.get("ward")),
        "furnishing_level": _string(row.get("furnishing_level")),
        "posted_at": _string(row.get("posted_at")),
        "expired_at": _string(row.get("expired_at")),
        "freshness_days": _int(row.get("freshness_days")),
        "contact_name": _string(row.get("contact_name")),
        "contact_phone": _string(row.get("contact_phone")),
        "contact_zalo_url": _string(row.get("contact_zalo_url")),
        "contact_facebook_url": _string(row.get("contact_facebook_url")),
        "amenities_text": _string(row.get("amenities_text")),
        "description_clean": _string(row.get("description_clean")),
        "primary_image_url": _string(row.get("primary_image_url")),
        "canonical_url": row.get("canonical_url") or "",
    }
    return {key: value for key, value in detail.items() if value not in {None, ""}}


def _row_to_listing(row: dict[str, str], detail_path: str | None = None) -> dict[str, object]:
    primary_image_url = _string(row.get("primary_image_url"))
    listing = {
        "id": row.get("listing_id") or "",
        "source_name": row.get("source_name") or "unknown",
        "title": row.get("title_clean") or row.get("title") or "",
        "price_value": _int(row.get("price_value")),
        "area_m2": _float(row.get("area_m2")),
        "street_address": _string(row.get("street_address")),
        "full_address": _string(row.get("full_address")),
        "province": _string(row.get("province")),
        "district": _string(row.get("district")),
        "latitude": _float(row.get("latitude")),
        "longitude": _float(row.get("longitude")),
        "geocode_precision": _string(row.get("geocode_precision")),
        "is_reference_coordinate": _bool(row.get("is_reference_coordinate")),
        "room_type": _string(row.get("room_type")),
        "image_count": _int(row.get("image_count")) or 0,
        "record_completeness_score": _int(row.get("record_completeness_score")),
        "thumbnail_url": primary_image_url,
        "status": row.get("status") or "active",
    }
    for key in (
        "has_aircon", "has_private_wc", "has_loft", "has_parking", "has_security",
        "has_fingerprint_lock", "allows_free_hours", "has_balcony", "has_kitchen",
        "has_fridge", "has_washer",
    ):
        if _bool(row.get(key)):
            listing[key] = True
    if detail_path:
        listing["detail_path"] = detail_path
    return {key: value for key, value in listing.items() if value not in {None, ""}}


def _row_to_detail(row: dict[str, str]) -> dict[str, object]:
    detail = {"id": row.get("listing_id") or ""}
    detail.update(_detail_columns(row))
    return detail


def _valid_row(row: dict[str, str]) -> bool:
    return bool(row.get("listing_id")) and (row.get("source_name") or "") in KNOWN_SOURCES


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _local_run_date(generated_at: str) -> str:
    try:
        parsed = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(VIETNAM_TIMEZONE).date().isoformat()
    except ValueError:
        return datetime.now(VIETNAM_TIMEZONE).date().isoformat()


def _etl_monitor_payload(
    *,
    source_csv: Path,
    output_json: Path,
    valid_rows: list[dict[str, str]],
    source_counts: Counter[str],
    geocode_summary: Counter[str],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    curation_summary = _read_json(source_csv.with_name("curation_summary.json"))
    generated_at = str(curation_summary.get("generated_at") or datetime.now(UTC).isoformat())
    source_rows = int(curation_summary.get("source_rows") or len(valid_rows))
    duplicate_rows = int(curation_summary.get("duplicate_source_rows") or 0)
    rejected_rows = int(curation_summary.get("skipped_low_quality_rows") or 0)
    exact_rows = int(geocode_summary.get("exact", 0))
    located_rows = len(valid_rows) - int(geocode_summary.get("none", 0))
    status_counts = Counter(str(row.get("status") or "active") for row in valid_rows)
    summary = {
        "generated_at": generated_at,
        "status": "success",
        "source_rows": source_rows,
        "deduplicated_rows": max(source_rows - duplicate_rows, 0),
        "duplicate_rows": duplicate_rows,
        "rejected_rows": rejected_rows,
        "curated_rows": len(valid_rows),
        "located_rows": located_rows,
        "exact_geocoded_rows": exact_rows,
        "unresolved_geocode_rows": int(geocode_summary.get("none", 0)),
        "published_rows": len(valid_rows),
        "duration_seconds": curation_summary.get("duration_seconds"),
        "source_counts": dict(source_counts),
        "status_counts": dict(status_counts),
    }
    current_run = {
        "date": _local_run_date(generated_at),
        "generated_at": generated_at,
        "status": "success",
        "source_rows": source_rows,
        "curated_rows": len(valid_rows),
        "rejected_rows": duplicate_rows + rejected_rows,
        "located_rows": located_rows,
        "published_rows": len(valid_rows),
        "duration_seconds": curation_summary.get("duration_seconds"),
    }
    previous_manifest = _read_json(output_json)
    previous_runs = previous_manifest.get("etl_runs")
    history = {
        str(run.get("date")): run
        for run in previous_runs if isinstance(run, dict) and run.get("date")
    } if isinstance(previous_runs, list) else {}
    history[current_run["date"]] = current_run
    runs = [history[key] for key in sorted(history)][-30:]
    return summary, runs


def export_static_map(
    *,
    source_csv: Path,
    output_json: Path,
    chunk_size: int,
    detail_chunk_size: int = 500,
) -> dict[str, object]:
    with source_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    skipped_rows = len([row for row in rows if not _valid_row(row)])
    valid_rows = [row for row in rows if _valid_row(row)]

    detail_dir = output_json.parent / f"{output_json.stem}-details"
    detail_paths: list[str] = []
    if detail_chunk_size > 0:
        detail_dir.mkdir(parents=True, exist_ok=True)
        for old_chunk in detail_dir.glob("*.json"):
            old_chunk.unlink()
        for index in range(0, len(valid_rows), detail_chunk_size):
            detail_chunk = valid_rows[index:index + detail_chunk_size]
            detail_name = f"part-{index // detail_chunk_size:03d}.json"
            detail_path = detail_dir / detail_name
            detail_path.write_text(
                json.dumps({"items": [_row_to_detail(row) for row in detail_chunk]}, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            detail_paths.append(f"{detail_dir.name}/{detail_name}")

    items = []
    for index, row in enumerate(valid_rows):
        detail_path = detail_paths[index // detail_chunk_size] if detail_paths else None
        items.append(_row_to_listing(row, detail_path))
    source_counts = Counter(str(item["source_name"]) for item in items)
    geocode_summary = Counter(str(item.get("geocode_precision") or "none") for item in items)
    available_provinces = sorted({str(item["province"]) for item in items if item.get("province")})
    etl_summary, etl_runs = _etl_monitor_payload(
        source_csv=source_csv,
        output_json=output_json,
        valid_rows=valid_rows,
        source_counts=source_counts,
        geocode_summary=geocode_summary,
    )

    output = {
        "total": len(items),
        "returned": len(items),
        "available_provinces": available_provinces,
        "geocode_summary": dict(geocode_summary),
        "deploy_source_counts": dict(source_counts),
        "skipped_rows": skipped_rows,
        "etl_summary": etl_summary,
        "etl_runs": etl_runs,
        "detail_chunk_size": detail_chunk_size if detail_paths else None,
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
    manifest["dataset_mode"] = "chunked-index-with-lazy-details"
    output_json.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Export deploy snapshot as frontend static map JSON.")
    parser.add_argument("--source-csv", type=Path, default=Path("crawler/artifacts/deploy/listings_deploy.csv"))
    parser.add_argument("--output-json", type=Path, default=Path("web/public/data/listings-map.json"))
    parser.add_argument("--ensure-snapshot", action="store_true")
    parser.add_argument("--chunk-size", type=int, default=0)
    parser.add_argument("--detail-chunk-size", type=int, default=500)
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

    output = export_static_map(
        source_csv=source_csv,
        output_json=args.output_json.resolve(),
        chunk_size=args.chunk_size,
        detail_chunk_size=args.detail_chunk_size,
    )
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
