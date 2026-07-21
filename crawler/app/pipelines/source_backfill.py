from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from app.client import PhongtroHttpClient
from app.pipelines.bootstrap import BootstrapPipeline
from app.sources import build_sources
from app.storage import LocalArtifactStore


BALANCED_SOURCE_LIMITS = {
    # NhaTot accepts offsets through 19,980 although `total` is capped at 10,000.
    "nhatot": 1000,
    # Mogi has roughly 3,900 populated archive pages; the empty-chunk guard
    # discovers the moving end without trusting its local pagination window.
    "mogi": 5000,
}


def run_balanced_backfill(
    *,
    store: LocalArtifactStore,
    client: PhongtroHttpClient,
    city: str = "all",
    source_names: list[str] | None = None,
    chunk_pages: int = 100,
    search_workers: int = 4,
    max_chunks: int | None = None,
    reset_state: bool = False,
) -> dict:
    if chunk_pages < 1:
        raise ValueError("chunk_pages must be at least 1")
    if search_workers < 1:
        raise ValueError("search_workers must be at least 1")
    if max_chunks is not None and max_chunks < 1:
        raise ValueError("max_chunks must be at least 1")

    requested = source_names or list(BALANCED_SOURCE_LIMITS)
    unsupported = [name for name in requested if name not in BALANCED_SOURCE_LIMITS]
    if unsupported:
        raise ValueError(
            "Balanced backfill only supports sources with verified deep pagination: "
            f"{', '.join(BALANCED_SOURCE_LIMITS)}. Unsupported: {', '.join(unsupported)}"
        )

    scope = _scope_slug(city)
    state_path = store.root / "state" / f"balanced_backfill_{scope}.json"
    if reset_state and state_path.exists():
        state_path.unlink()
    state = _load_state(state_path, store.root, scope, requested)

    chunks_run = 0
    parsed_listings = 0
    discovered_urls = 0
    failed_urls = 0
    source_results: dict[str, dict] = {}

    for source_name in requested:
        source_state = state["sources"][source_name]
        source_results[source_name] = {
            "start_page": source_state["next_page"],
            "end_page": source_state["next_page"] - 1,
            "parsed_listings": 0,
            "failed_urls": 0,
            "completed": bool(source_state.get("completed")),
        }
        if source_state.get("completed"):
            continue

        source = build_sources([source_name])[0]
        pipeline = BootstrapPipeline(store, [source], client)
        while source_state["next_page"] <= source_state["max_page"]:
            if max_chunks is not None and chunks_run >= max_chunks:
                break

            start_page = int(source_state["next_page"])
            page_count = min(chunk_pages, int(source_state["max_page"]) - start_page + 1)
            result = pipeline.run(
                city=city,
                start_page=start_page,
                max_pages=page_count,
                max_detail_pages=None,
                detail_workers=1,
                search_workers=search_workers,
            )
            chunks_run += 1
            parsed_listings += result.parsed_listings
            discovered_urls += result.discovered_urls
            failed_urls += result.failed_urls

            source_state["next_page"] = start_page + page_count
            source_state["last_page_attempted"] = start_page + page_count - 1
            source_state["last_chunk_rows"] = result.parsed_listings
            source_state["updated_at"] = datetime.now(UTC).isoformat()
            source_state["empty_chunks"] = int(source_state.get("empty_chunks", 0)) + 1 if result.parsed_listings == 0 else 0
            if source_state["empty_chunks"] >= 1 or source_state["next_page"] > source_state["max_page"]:
                source_state["completed"] = True

            current_result = source_results[source_name]
            current_result["end_page"] = source_state["last_page_attempted"]
            current_result["parsed_listings"] += result.parsed_listings
            current_result["failed_urls"] += result.failed_urls
            current_result["completed"] = source_state["completed"]
            _write_state(state_path, state)

            if source_state["completed"]:
                break

        if max_chunks is not None and chunks_run >= max_chunks:
            break

    return {
        "mode": "balanced-backfill",
        "city": city,
        "sources": requested,
        "chunks_run": chunks_run,
        "search_workers": search_workers,
        "parsed_listings": parsed_listings,
        "discovered_urls": discovered_urls,
        "failed_urls": failed_urls,
        "state_path": str(state_path),
        "source_results": source_results,
        "completed": all(state["sources"][name].get("completed") for name in requested),
    }


def _load_state(state_path: Path, artifact_root: Path, scope: str, source_names: list[str]) -> dict:
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    else:
        state = {"version": 1, "scope": scope, "sources": {}}

    for source_name in source_names:
        if source_name not in state["sources"]:
            state["sources"][source_name] = {
                "next_page": _next_existing_page(artifact_root, source_name, scope),
                "max_page": BALANCED_SOURCE_LIMITS[source_name],
                "empty_chunks": 0,
                "completed": False,
            }
    return state


def _next_existing_page(artifact_root: Path, source_name: str, scope: str) -> int:
    page_dir = artifact_root / "tabular" / source_name / scope
    pages: list[int] = []
    if page_dir.exists():
        for path in page_dir.glob("page_*.csv"):
            match = re.fullmatch(r"page_(\d+)", path.stem)
            if match:
                pages.append(int(match.group(1)))
    return max(pages, default=0) + 1


def _write_state(state_path: Path, state: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(UTC).isoformat()
    state_path.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")


def _scope_slug(city: str) -> str:
    return "toan-quoc" if city.lower() in {"all", "nationwide", "toan-quoc"} else city
