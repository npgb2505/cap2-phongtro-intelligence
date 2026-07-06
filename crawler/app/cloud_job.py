from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from app.client import PhongtroHttpClient
from app.config import settings
from app.curated_loader import load_curated_snapshot
from app.curation import CURATED_JSON_RELATIVE_PATH, CURATED_RELATIVE_PATH, SUMMARY_RELATIVE_PATH, CurationPipeline
from app.pipelines.incremental import IncrementalPipeline
from app.s3_upload import upload_files
from app.sources import DEFAULT_SOURCE_NAMES, build_sources
from app.storage import LocalArtifactStore


def main() -> None:
    store = LocalArtifactStore(settings.local_artifact_dir)
    sources = build_sources(_parse_source_names(os.environ.get("PT_SOURCES", "all")))
    result = IncrementalPipeline(store, sources, PhongtroHttpClient()).run(
        city=os.environ.get("PT_CITY", "all"),
        pages=_int_env("PT_PAGES", 3),
        max_detail_pages=_optional_int_env("PT_MAX_DETAIL_PAGES", 20),
        detail_workers=_int_env("PT_DETAIL_WORKERS", settings.detail_worker_count),
    )
    curation = CurationPipeline(store).run(exact_geocode_limit=_int_env("PT_EXACT_GEOCODE_LIMIT", 0))

    curated_csv = store.root / CURATED_RELATIVE_PATH
    database_result = None
    database_url = os.environ.get("PT_DATABASE_URL")
    if database_url:
        database_result = load_curated_snapshot(curated_csv, database_url)

    s3_result: list[str] = []
    s3_bucket = os.environ.get("PT_S3_BUCKET")
    if s3_bucket:
        upload_candidates = [
            *result.artifact_paths,
            str(store.root / CURATED_RELATIVE_PATH),
            str(store.root / CURATED_JSON_RELATIVE_PATH),
            str(store.root / SUMMARY_RELATIVE_PATH),
        ]
        s3_result = upload_files(
            bucket=s3_bucket,
            root=store.root,
            file_paths=upload_candidates,
            prefix=os.environ.get("PT_S3_PREFIX", ""),
        )

    payload = {
        "mode": "cloud_job",
        "sources": [source.name for source in sources],
        "default_sources": DEFAULT_SOURCE_NAMES,
        "incremental": asdict(result),
        "curation": asdict(curation),
        "database": database_result,
        "s3_uploaded": s3_result,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def _parse_source_names(value: str) -> list[str] | None:
    cleaned = value.strip().lower()
    if cleaned in {"", "all", "*"}:
        return None
    return [part.strip() for part in cleaned.split(",") if part.strip()]


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _optional_int_env(name: str, default: int | None) -> int | None:
    value = os.environ.get(name)
    if value in {None, ""}:
        return default
    try:
        return int(value)
    except ValueError:
        return default


if __name__ == "__main__":
    main()
