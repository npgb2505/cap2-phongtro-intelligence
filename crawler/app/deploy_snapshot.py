from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from app.publication_quality import evaluate_publication_quality, publication_sort_key


DEFAULT_SOURCES = ("phongtro123", "nhatot", "mogi")
DEFAULT_TOTAL_ROWS = 60_000


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


def build_deploy_snapshot(
    *,
    source_csv: Path,
    output_csv: Path,
    summary_json: Path,
    sources: Iterable[str] = DEFAULT_SOURCES,
    total_rows: int = DEFAULT_TOTAL_ROWS,
) -> dict[str, object]:
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

    available_counts = {source: len(rows) for source, rows in buckets.items()}
    selected_counts = _balanced_counts(buckets, wanted_sources, total_rows)
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

    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_csv": str(source_csv),
        "output_csv": str(output_csv),
        "total_rows": len(selected),
        "target_rows": total_rows,
        "selection_strategy": "balanced-quality-ranked",
        "available_source_counts": available_counts,
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
    parser.add_argument("--total-rows", type=int, default=DEFAULT_TOTAL_ROWS)
    parser.add_argument("--sources", default=",".join(DEFAULT_SOURCES))
    args = parser.parse_args()

    summary = build_deploy_snapshot(
        source_csv=args.source_csv.resolve(),
        output_csv=args.output_csv.resolve(),
        summary_json=args.summary_json.resolve(),
        sources=[source.strip() for source in args.sources.split(",") if source.strip()],
        total_rows=args.total_rows,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
