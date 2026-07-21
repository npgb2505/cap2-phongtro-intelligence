import argparse
import json
from collections.abc import Mapping
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from app.client import PhongtroHttpClient
from app.config import settings
from app.curation import CurationPipeline
from app.pipelines.bootstrap import BootstrapPipeline
from app.pipelines.incremental import IncrementalPipeline
from app.pipelines.source_backfill import run_balanced_backfill
from app.sources import DEFAULT_SOURCE_NAMES, build_sources
from app.storage import LocalArtifactStore


DEFAULT_SOURCES = ",".join(DEFAULT_SOURCE_NAMES)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PhongTro crawler entrypoint")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap")
    bootstrap.add_argument("--city", required=True)
    bootstrap.add_argument("--max-pages", type=int, default=3)
    bootstrap.add_argument("--start-page", type=int, default=1)
    bootstrap.add_argument("--max-detail-pages", type=int, default=None)
    bootstrap.add_argument("--detail-workers", type=int, default=settings.detail_worker_count)
    bootstrap.add_argument("--sources", default=DEFAULT_SOURCES)

    bootstrap_resume = subparsers.add_parser("bootstrap-resume")
    bootstrap_resume.add_argument("--city", required=True)
    bootstrap_resume.add_argument("--page-chunk", type=int, default=5)
    bootstrap_resume.add_argument("--max-detail-pages", type=int, default=10)
    bootstrap_resume.add_argument("--detail-workers", type=int, default=settings.detail_worker_count)
    bootstrap_resume.add_argument("--sources", default=DEFAULT_SOURCES)

    incremental = subparsers.add_parser("incremental")
    incremental.add_argument("--city", required=True)
    incremental.add_argument("--pages", type=int, default=1)
    incremental.add_argument("--max-detail-pages", type=int, default=None)
    incremental.add_argument("--detail-workers", type=int, default=settings.detail_worker_count)
    incremental.add_argument("--sources", default=DEFAULT_SOURCES)

    balanced = subparsers.add_parser("balanced-backfill")
    balanced.add_argument("--city", default="all")
    balanced.add_argument("--sources", default="nhatot,mogi")
    balanced.add_argument("--chunk-pages", type=int, default=100)
    balanced.add_argument("--search-workers", type=int, default=4)
    balanced.add_argument("--max-chunks", type=int, default=None)
    balanced.add_argument("--reset-state", action="store_true")

    curated = subparsers.add_parser("transform-curated")
    curated.add_argument("--exact-geocode-limit", type=int, default=120)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    store = LocalArtifactStore(settings.local_artifact_dir)
    client = PhongtroHttpClient()
    sources = build_sources(_parse_source_names(getattr(args, "sources", DEFAULT_SOURCES)))
    bootstrap_pipeline = BootstrapPipeline(store, sources, client)

    if args.command == "bootstrap":
        result = bootstrap_pipeline.run(
            city=args.city,
            start_page=args.start_page,
            max_pages=args.max_pages,
            max_detail_pages=args.max_detail_pages,
            detail_workers=args.detail_workers,
        )
    elif args.command == "bootstrap-resume":
        result = run_bootstrap_resume(
            pipeline=bootstrap_pipeline,
            state_dir=settings.local_artifact_dir / "state",
            city=args.city,
            page_chunk=args.page_chunk,
            max_detail_pages=args.max_detail_pages,
            detail_workers=args.detail_workers,
        )
    elif args.command == "incremental":
        result = IncrementalPipeline(store, sources, client).run(
            city=args.city,
            pages=args.pages,
            max_detail_pages=args.max_detail_pages,
            detail_workers=args.detail_workers,
        )
    elif args.command == "balanced-backfill":
        result = run_balanced_backfill(
            store=store,
            client=client,
            city=args.city,
            source_names=_parse_source_names(args.sources),
            chunk_pages=args.chunk_pages,
            search_workers=args.search_workers,
            max_chunks=args.max_chunks,
            reset_state=args.reset_state,
        )
    else:
        result = CurationPipeline(store).run(exact_geocode_limit=args.exact_geocode_limit)

    print(json.dumps(_serialize_result(result), indent=2, ensure_ascii=True, default=_json_default))


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _serialize_result(result: object) -> object:
    if hasattr(result, "__dataclass_fields__"):
        return asdict(result)
    if isinstance(result, Mapping):
        return result
    return result


def _parse_source_names(value: str) -> list[str] | None:
    cleaned = value.strip().lower()
    if cleaned in {"", "all", "*"}:
        return None
    return [part.strip() for part in cleaned.split(",") if part.strip()]


def run_bootstrap_resume(
    pipeline: BootstrapPipeline,
    state_dir: Path,
    city: str,
    page_chunk: int,
    max_detail_pages: int | None,
    detail_workers: int,
):
    state_dir.mkdir(parents=True, exist_ok=True)
    scope = "toan-quoc" if city.lower() in {"all", "nationwide", "toan-quoc"} else city
    state_path = state_dir / f"bootstrap_{scope}.json"

    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    else:
        last_page = pipeline.get_last_page(city) or 1
        state = {"city": city, "scope": scope, "next_page": 1, "last_page": last_page, "completed": False}

    if state.get("completed"):
        return {
            "mode": "bootstrap-resume",
            "message": "bootstrap already completed",
            "state_path": str(state_path),
            "state": state,
        }

    remaining = int(state["last_page"]) - int(state["next_page"]) + 1
    max_pages = max(1, min(page_chunk, remaining))

    result = pipeline.run(
        city=city,
        start_page=int(state["next_page"]),
        max_pages=max_pages,
        max_detail_pages=max_detail_pages,
        detail_workers=detail_workers,
    )

    state["next_page"] = int(state["next_page"]) + result.pages_crawled
    state["completed"] = state["next_page"] > int(state["last_page"])
    state["last_run_at"] = datetime.now().isoformat()
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=True), encoding="utf-8")

    return {
        "mode": "bootstrap-resume",
        "result": asdict(result),
        "state_path": str(state_path),
        "state": state,
    }


if __name__ == "__main__":
    main()
