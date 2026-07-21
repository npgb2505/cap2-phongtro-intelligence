from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Iterable

from app.publication_quality import evaluate_publication_quality, publication_sort_key


DEFAULT_SOURCES = ("phongtro123", "nhatot", "mogi")
DEFAULT_MAX_ROWS = 60_000
DEFAULT_MIN_SOURCE_SHARE = 0.24


def _score(row: dict[str, str]) -> tuple[int, int, int, int, int, int, int, str]:
    assessment = evaluate_publication_quality(row)
    return publication_sort_key(row, assessment)


def _balanced_counts(
    buckets: dict[str, list[dict[str, str]]],
    sources: tuple[str, ...],
    total_rows: int,
) -> dict[str, int]:
    if total_rows <= 0:
        raise ValueError("total_rows must be positive")
    if not sources:
        raise ValueError("At least one source is required")
    missing_sources = [source for source in sources if not buckets[source]]
    if missing_sources:
        raise ValueError(f"Sources have no rows: {', '.join(missing_sources)}")
    available_rows = sum(len(buckets[source]) for source in sources)
    if available_rows < total_rows:
        raise ValueError(f"Only {available_rows} rows are available, need {total_rows}")

    target_per_source = total_rows // len(sources)
    selected_counts = {
        source: min(target_per_source, len(buckets[source]))
        for source in sources
    }
    remaining = total_rows - sum(selected_counts.values())
    while remaining > 0:
        available_sources = [
            source for source in sources
            if selected_counts[source] < len(buckets[source])
        ]
        if not available_sources:
            break
        share = max(1, remaining // len(available_sources))
        for source in available_sources:
            room = len(buckets[source]) - selected_counts[source]
            taken = min(share, room, remaining)
            selected_counts[source] += taken
            remaining -= taken
            if remaining == 0:
                break
    return selected_counts


def _derived_total_rows(
    buckets: dict[str, list[dict[str, str]]],
    sources: tuple[str, ...],
    max_rows: int,
    min_source_share: float,
) -> int:
    if not 0 < min_source_share <= 1 / len(sources):
        raise ValueError("min_source_share must be positive and no greater than an equal source share")
    minority_rows = min(len(buckets[source]) for source in sources)
    return min(max_rows, sum(len(buckets[source]) for source in sources), int(minority_rows / min_source_share))


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.name


def build_deploy_snapshot(
    *,
    source_csv: Path,
    output_csv: Path,
    summary_json: Path,
    sources: Iterable[str] = DEFAULT_SOURCES,
    total_rows: int | None = None,
    max_rows: int = DEFAULT_MAX_ROWS,
    min_source_share: float = DEFAULT_MIN_SOURCE_SHARE,
) -> dict[str, object]:
    started_clock = perf_counter()
    wanted_sources = tuple(sources)
    buckets: dict[str, list[dict[str, str]]] = {source: [] for source in wanted_sources}

    with source_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {source_csv}")
        fieldnames = reader.fieldnames
        for row in reader:
            source_name = row.get("source_name") or ""
            if source_name in buckets:
                buckets[source_name].append(row)

    derived_total_rows = (
        total_rows
        if total_rows is not None
        else _derived_total_rows(buckets, wanted_sources, max_rows, min_source_share)
    )
    selected_counts = _balanced_counts(buckets, wanted_sources, derived_total_rows)
    selected: list[dict[str, str]] = []
    counts: Counter[str] = Counter()
    for source_name in wanted_sources:
        rows = sorted(buckets[source_name], key=_score, reverse=True)
        chosen = rows[:selected_counts[source_name]]
        selected.extend(chosen)
        counts[source_name] = len(chosen)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected)

    fingerprint = hashlib.sha256()
    for row in selected:
        fingerprint.update((row.get("listing_id") or row.get("canonical_url") or "").encode("utf-8"))
    dataset_fingerprint = fingerprint.hexdigest()[:16]
    generated_at = datetime.now(UTC)
    summary = {
        "run_id": f"etl-{generated_at:%Y%m%dT%H%M%SZ}-{dataset_fingerprint[:8]}",
        "pipeline_version": "production-quality-v3",
        "run_mode": "budgeted_source_ingestion",
        "generated_at": generated_at.isoformat(),
        "source_generated_at": generated_at.isoformat(),
        "source_csv": _display_path(source_csv),
        "output_csv": _display_path(output_csv),
        "source_rows": len(selected),
        "input_rows": len(selected),
        "source_rejected_rows": 0,
        "duplicate_source_rows": 0,
        "curated_source_rows": len(selected),
        "total_rows": len(selected),
        "target_rows": derived_total_rows,
        "max_rows": max_rows,
        "min_source_share": min_source_share,
        "selection_strategy": "budgeted-source-balance-quality-ranked",
        "dataset_fingerprint": dataset_fingerprint,
        "duration_seconds": round(perf_counter() - started_clock, 3),
        "source_counts": dict(counts),
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a small deploy CSV snapshot for free hosting.")
    parser.add_argument(
        "--source-csv",
        type=Path,
        default=Path("crawler/artifacts/curated/toan-quoc/listings_curated.csv"),
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("crawler/artifacts/deploy/listings_deploy.csv"),
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=Path("crawler/artifacts/deploy/deploy_snapshot_summary.json"),
    )
    parser.add_argument("--total-rows", type=int)
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS)
    parser.add_argument("--min-source-share", type=float, default=DEFAULT_MIN_SOURCE_SHARE)
    parser.add_argument("--sources", default=",".join(DEFAULT_SOURCES))
    args = parser.parse_args()

    summary = build_deploy_snapshot(
        source_csv=args.source_csv.resolve(),
        output_csv=args.output_csv.resolve(),
        summary_json=args.summary_json.resolve(),
        sources=[source.strip() for source in args.sources.split(",") if source.strip()],
        total_rows=args.total_rows,
        max_rows=args.max_rows,
        min_source_share=args.min_source_share,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
