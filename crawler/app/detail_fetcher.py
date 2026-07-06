from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from typing import Any

from app.client import PhongtroHttpClient
from app.config import settings
from app.models import ListingRecord
from app.sources import ListingSource
from app.storage import LocalArtifactStore


def fetch_listing_batch(
    *,
    urls: list[str],
    worker_count: int,
    store: LocalArtifactStore,
    extractor: ListingSource,
    artifact_prefix: str,
    client_factory: Callable[[], PhongtroHttpClient],
) -> tuple[list[dict[str, Any]], list[str], int]:
    if not urls:
        return [], [], 0

    if worker_count <= 1:
        payloads: list[dict[str, Any]] = []
        artifact_paths: list[str] = []
        failed_urls = 0
        for index, detail_url in enumerate(urls, start=1):
            try:
                payload, artifact_path = _fetch_one(
                    index=index,
                    detail_url=detail_url,
                    store=store,
                    extractor=extractor,
                    artifact_prefix=artifact_prefix,
                    client_factory=client_factory,
                )
                payloads.append(payload)
                artifact_paths.append(artifact_path)
            except Exception:
                failed_urls += 1
        return payloads, artifact_paths, failed_urls

    payloads_by_index: dict[int, dict[str, Any]] = {}
    artifact_paths_by_index: dict[int, str] = {}
    failed_urls = 0

    with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="detail-crawl") as executor:
        futures = {
            executor.submit(
                _fetch_one,
                index=index,
                detail_url=detail_url,
                store=store,
                extractor=extractor,
                artifact_prefix=artifact_prefix,
                client_factory=client_factory,
            ): index
            for index, detail_url in enumerate(urls, start=1)
        }
        for future in as_completed(futures):
            index = futures[future]
            try:
                payload, artifact_path = future.result()
            except Exception:
                failed_urls += 1
                continue
            payloads_by_index[index] = payload
            artifact_paths_by_index[index] = artifact_path

    ordered_indexes = sorted(payloads_by_index)
    payloads = [payloads_by_index[index] for index in ordered_indexes]
    artifact_paths = [artifact_paths_by_index[index] for index in ordered_indexes]
    return payloads, artifact_paths, failed_urls


def _fetch_one(
    *,
    index: int,
    detail_url: str,
    store: LocalArtifactStore,
    extractor: ListingSource,
    artifact_prefix: str,
    client_factory: Callable[[], PhongtroHttpClient],
) -> tuple[dict[str, Any], str]:
    client = client_factory()
    detail_html = client.fetch_text(detail_url)
    record = extractor.parse_detail(detail_html, detail_url)
    artifact_path = ""
    if settings.save_raw_html:
        artifact_path = store.write_text(f"{artifact_prefix}_{index}.html", detail_html)
    return _to_payload(record, extractor), artifact_path


def _to_payload(record: ListingRecord, extractor: ListingSource) -> dict[str, Any]:
    return {
        **asdict(record),
        "content_hash": extractor.build_content_hash(record),
    }
