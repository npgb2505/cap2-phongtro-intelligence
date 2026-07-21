from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter

from app.deploy_snapshot import (
    DEFAULT_MAX_ROWS,
    DEFAULT_MIN_SOURCE_SHARE,
    DEFAULT_SOURCES,
    build_deploy_snapshot,
)
from app.publication_quality import (
    PublicationAssessment,
    evaluate_publication_quality,
    is_contact_name,
    publication_sort_key,
)

KNOWN_SOURCES = {"phongtro123", "nhatot", "mogi"}
VIETNAM_TIMEZONE = timezone(timedelta(hours=7))
DEFAULT_MIN_QUALITY_SCORE = 68


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
        "contact_name": _string(row.get("contact_name")) if is_contact_name(row.get("contact_name")) else None,
        "contact_phone": _string(row.get("contact_phone")),
        "contact_zalo_url": _string(row.get("contact_zalo_url")),
        "contact_facebook_url": _string(row.get("contact_facebook_url")),
        "amenities_text": _string(row.get("amenities_text")),
        "description_clean": _string(row.get("description_clean")),
        "primary_image_url": _string(row.get("primary_image_url")),
        "canonical_url": row.get("canonical_url") or "",
    }
    return {key: value for key, value in detail.items() if value not in {None, ""}}


def _row_to_listing(
    row: dict[str, str],
    detail_path: str | None = None,
    assessment: PublicationAssessment | None = None,
) -> dict[str, object]:
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
        "publication_quality_score": assessment.score if assessment else None,
        "has_direct_contact": assessment.has_direct_contact if assessment else None,
        "has_contact_name": assessment.has_contact_name if assessment else None,
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
    curated_rows: list[dict[str, str]],
    published_rows: list[dict[str, str]],
    source_counts: Counter[str],
    curated_geocode_summary: Counter[str],
    quality_summary: dict[str, object],
    export_duration_seconds: float,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    deploy_summary = _read_json(source_csv.with_name("deploy_snapshot_summary.json"))
    curation_summary = _read_json(source_csv.with_name("curation_summary.json"))
    run_metadata = deploy_summary or curation_summary
    generated_at = str(run_metadata.get("generated_at") or datetime.now(UTC).isoformat())
    if deploy_summary:
        source_rows = int(
            run_metadata.get("input_rows")
            or run_metadata.get("total_rows")
            or len(curated_rows)
        )
        source_rejected_rows = max(source_rows - len(curated_rows), 0)
        duplicate_rows = 0
        deduplicated_rows = len(curated_rows)
    else:
        source_rows = int(run_metadata.get("source_rows") or len(curated_rows))
        source_rejected_rows = int(
            run_metadata.get("source_rejected_rows")
            or run_metadata.get("skipped_low_quality_rows")
            or 0
        )
        duplicate_rows = int(run_metadata.get("duplicate_source_rows") or 0)
        deduplicated_rows = int(
            run_metadata.get("curated_source_rows")
            or max(source_rows - source_rejected_rows - duplicate_rows, 0)
        )
    transformed_rows = len(curated_rows)
    exact_rows = int(curated_geocode_summary.get("exact", 0))
    located_rows = len(curated_rows) - int(curated_geocode_summary.get("none", 0))
    status_counts = Counter(str(row.get("status") or "active") for row in published_rows)
    quality_qualified_rows = int(quality_summary.get("qualified_rows") or len(published_rows))
    rejected_rows = max(transformed_rows - len(published_rows), 0)
    duration_parts = [run_metadata.get("duration_seconds"), export_duration_seconds]
    duration_seconds = round(sum(float(value) for value in duration_parts if value is not None), 3)
    stage_durations_seconds = {
        "ingest_and_transform": float(run_metadata.get("duration_seconds") or 0),
        "static_export": round(export_duration_seconds, 3),
    }
    published_at = datetime.now(UTC).isoformat()
    pipeline_version = str(run_metadata.get("pipeline_version") or "production-quality-v3")
    dataset_fingerprint = str(run_metadata.get("dataset_fingerprint") or f"{transformed_rows:x}{len(published_rows):x}")
    run_id = str(
        run_metadata.get("run_id")
        or f"etl-{_local_run_date(generated_at).replace('-', '')}-{dataset_fingerprint[:8]}"
    )
    summary = {
        "run_id": run_id,
        "pipeline_version": pipeline_version,
        "run_mode": str(run_metadata.get("run_mode") or "budgeted_source_ingestion"),
        "dataset_fingerprint": dataset_fingerprint,
        "generated_at": generated_at,
        "source_generated_at": run_metadata.get("source_generated_at") or curation_summary.get("generated_at"),
        "status": "success",
        "source_rows": source_rows,
        "source_rejected_rows": source_rejected_rows,
        "deduplicated_rows": deduplicated_rows,
        "duplicate_rows": duplicate_rows,
        "rejected_rows": rejected_rows,
        "curated_rows": transformed_rows,
        "located_rows": located_rows,
        "exact_geocoded_rows": exact_rows,
        "unresolved_geocode_rows": int(curated_geocode_summary.get("none", 0)),
        "quality_qualified_rows": quality_qualified_rows,
        "published_rows": len(published_rows),
        "duration_seconds": duration_seconds,
        "stage_durations_seconds": stage_durations_seconds,
        "published_at": published_at,
        "input_source_counts": dict(run_metadata.get("source_counts") or source_counts),
        "source_counts": dict(source_counts),
        "status_counts": dict(status_counts),
    }
    current_run = {
        "run_id": run_id,
        "pipeline_version": pipeline_version,
        "run_mode": summary["run_mode"],
        "dataset_fingerprint": dataset_fingerprint,
        "date": _local_run_date(generated_at),
        "generated_at": generated_at,
        "status": "success",
        "source_rows": source_rows,
        "deduplicated_rows": deduplicated_rows,
        "curated_rows": transformed_rows,
        "rejected_rows": rejected_rows,
        "located_rows": located_rows,
        "quality_qualified_rows": quality_qualified_rows,
        "published_rows": len(published_rows),
        "duration_seconds": duration_seconds,
        "stage_durations_seconds": stage_durations_seconds,
        "input_source_counts": summary["input_source_counts"],
        "source_generated_at": summary["source_generated_at"],
        "published_at": published_at,
    }
    history_path = source_csv.with_name("etl_run_history.json")
    history_payload = _read_json(history_path)
    previous_runs = history_payload.get("runs")
    history = {
        str(run.get("run_id")): run
        for run in previous_runs
        if isinstance(run, dict) and run.get("run_id")
    } if isinstance(previous_runs, list) else {}
    history[run_id] = current_run
    runs = sorted(history.values(), key=lambda run: str(run.get("generated_at") or ""))[-30:]
    history_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "history_scope": "deployed_production_only",
                "pipeline_version": pipeline_version,
                "runs": runs,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    return summary, runs


def export_static_map(
    *,
    source_csv: Path,
    output_json: Path,
    chunk_size: int,
    detail_chunk_size: int = 500,
    quality_only: bool = False,
    min_quality_score: int = DEFAULT_MIN_QUALITY_SCORE,
    max_rows: int | None = None,
) -> dict[str, object]:
    started_clock = perf_counter()
    with source_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    curated_rows = [row for row in rows if _valid_row(row)]
    assessed_rows = [(row, evaluate_publication_quality(row)) for row in curated_rows]
    core_qualified_rows = [
        (row, assessment)
        for row, assessment in assessed_rows
        if not quality_only or assessment.publishable
    ]
    qualified_rows = [
        (row, assessment)
        for row, assessment in core_qualified_rows
        if not quality_only or assessment.score >= min_quality_score
    ]
    if quality_only:
        qualified_rows.sort(
            key=lambda entry: publication_sort_key(entry[0], entry[1]),
            reverse=True,
        )
    published_rows = qualified_rows[:max_rows] if max_rows and max_rows > 0 else qualified_rows
    skipped_rows = len(rows) - len(published_rows)

    detail_dir = output_json.parent / f"{output_json.stem}-details"
    detail_paths: list[str] = []
    if detail_chunk_size > 0:
        detail_dir.mkdir(parents=True, exist_ok=True)
        for old_chunk in detail_dir.glob("*.json"):
            old_chunk.unlink()
        for index in range(0, len(published_rows), detail_chunk_size):
            detail_chunk = published_rows[index:index + detail_chunk_size]
            detail_name = f"part-{index // detail_chunk_size:03d}.json"
            detail_path = detail_dir / detail_name
            detail_path.write_text(
                json.dumps(
                    {"items": [_row_to_detail(row) for row, _assessment in detail_chunk]},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                encoding="utf-8",
            )
            detail_paths.append(f"{detail_dir.name}/{detail_name}")

    items = []
    for index, (row, assessment) in enumerate(published_rows):
        detail_path = detail_paths[index // detail_chunk_size] if detail_paths else None
        items.append(_row_to_listing(row, detail_path, assessment))
    source_counts = Counter(str(item["source_name"]) for item in items)
    geocode_summary = Counter(str(item.get("geocode_precision") or "none") for item in items)
    curated_geocode_summary = Counter(str(row.get("geocode_precision") or "none") for row in curated_rows)
    available_provinces = sorted({str(item["province"]) for item in items if item.get("province")})
    qualified_source_counts = Counter(str(row.get("source_name") or "unknown") for row, _assessment in qualified_rows)
    quality_summary = {
        "enabled": quality_only,
        "minimum_score": min_quality_score if quality_only else None,
        "input_rows": len(rows),
        "valid_source_rows": len(curated_rows),
        "core_qualified_rows": len(core_qualified_rows),
        "qualified_rows": len(qualified_rows),
        "published_rows": len(published_rows),
        "rejected_invalid_source_rows": len(rows) - len(curated_rows),
        "rejected_core_quality_rows": len(curated_rows) - len(core_qualified_rows),
        "rejected_score_rows": len(core_qualified_rows) - len(qualified_rows),
        "rejected_low_quality_rows": len(curated_rows) - len(qualified_rows),
        "trimmed_rows": len(qualified_rows) - len(published_rows),
        "qualified_source_counts": dict(qualified_source_counts),
        "published_source_counts": dict(source_counts),
        "requirements": [
            "reasonable_price",
            "valid_area",
            "address",
            "canonical_url",
            "useful_content",
            f"publication_quality_score_gte_{min_quality_score}",
        ],
        "ranking_preferences": ["image_and_contact", "direct_contact", "contact_name", "real_image", "active_status", "description"],
    }
    etl_summary, etl_runs = _etl_monitor_payload(
        source_csv=source_csv,
        curated_rows=curated_rows,
        published_rows=[row for row, _assessment in published_rows],
        source_counts=source_counts,
        curated_geocode_summary=curated_geocode_summary,
        quality_summary=quality_summary,
        export_duration_seconds=perf_counter() - started_clock,
    )

    output = {
        "total": len(items),
        "returned": len(items),
        "dataset_version": datetime.now(UTC).isoformat(),
        "available_provinces": available_provinces,
        "geocode_summary": dict(geocode_summary),
        "deploy_source_counts": dict(source_counts),
        "skipped_rows": skipped_rows,
        "quality_summary": quality_summary,
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
    parser.add_argument(
        "--source-csv",
        type=Path,
        default=Path("crawler/artifacts/deploy/listings_deploy.csv"),
    )
    parser.add_argument("--output-json", type=Path, default=Path("web/public/data/listings-map.json"))
    parser.add_argument("--ensure-snapshot", action="store_true")
    parser.add_argument("--chunk-size", type=int, default=0)
    parser.add_argument("--detail-chunk-size", type=int, default=500)
    parser.add_argument("--min-quality-score", type=int, default=DEFAULT_MIN_QUALITY_SCORE)
    parser.add_argument("--max-rows", type=int)
    parser.add_argument("--include-low-quality", action="store_true")
    args = parser.parse_args()

    source_csv = args.source_csv.resolve()
    if args.ensure_snapshot and not source_csv.exists():
        build_deploy_snapshot(
            source_csv=Path("crawler/artifacts/curated/toan-quoc/listings_curated.csv").resolve(),
            output_csv=source_csv,
            summary_json=Path("crawler/artifacts/deploy/deploy_snapshot_summary.json").resolve(),
            sources=DEFAULT_SOURCES,
            max_rows=DEFAULT_MAX_ROWS,
            min_source_share=DEFAULT_MIN_SOURCE_SHARE,
        )

    output = export_static_map(
        source_csv=source_csv,
        output_json=args.output_json.resolve(),
        chunk_size=args.chunk_size,
        detail_chunk_size=args.detail_chunk_size,
        quality_only=not args.include_low_quality,
        min_quality_score=args.min_quality_score,
        max_rows=args.max_rows,
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
                "quality_summary": output.get("quality_summary", {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
