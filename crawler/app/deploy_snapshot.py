from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Iterable


DEFAULT_SOURCES = ("phongtro123", "nhatot", "mogi")


def _score(row: dict[str, str]) -> tuple[int, str]:
    try:
        completeness = int(row.get("record_completeness_score") or 0)
    except ValueError:
        completeness = 0
    return completeness, row.get("posted_at") or ""


def build_deploy_snapshot(
    *,
    source_csv: Path,
    output_csv: Path,
    summary_json: Path,
    sources: Iterable[str] = DEFAULT_SOURCES,
    per_source: int = 1000,
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

    selected: list[dict[str, str]] = []
    counts: Counter[str] = Counter()
    for source_name in wanted_sources:
        rows = sorted(buckets[source_name], key=_score, reverse=True)
        if len(rows) < per_source:
            raise ValueError(f"Source {source_name} only has {len(rows)} rows, need {per_source}")
        chosen = rows[:per_source]
        selected.extend(chosen)
        counts[source_name] = len(chosen)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected)

    summary = {
        "source_csv": str(source_csv),
        "output_csv": str(output_csv),
        "total_rows": len(selected),
        "per_source_target": per_source,
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
    parser.add_argument("--per-source", type=int, default=1000)
    parser.add_argument("--sources", default=",".join(DEFAULT_SOURCES))
    args = parser.parse_args()

    summary = build_deploy_snapshot(
        source_csv=args.source_csv.resolve(),
        output_csv=args.output_csv.resolve(),
        summary_json=args.summary_json.resolve(),
        sources=[source.strip() for source in args.sources.split(",") if source.strip()],
        per_source=args.per_source,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
