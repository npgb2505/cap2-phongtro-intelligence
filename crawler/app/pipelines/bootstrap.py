import json
import threading
from concurrent.futures import ThreadPoolExecutor

from app.client import PhongtroHttpClient
from app.config import settings
from app.detail_fetcher import fetch_listing_batch
from app.models import CrawlResult
from app.sources import ListingSource
from app.storage import LocalArtifactStore
from app.tabular_export import export_rows_to_csv, upsert_rows_to_csv


class BootstrapPipeline:
    def __init__(self, store: LocalArtifactStore, sources: list[ListingSource], client: PhongtroHttpClient) -> None:
        self.store = store
        self.sources = sources
        self.client = client
        self._thread_local = threading.local()

    def run(
        self,
        city: str,
        start_page: int,
        max_pages: int,
        max_detail_pages: int | None = None,
        detail_workers: int = 1,
        search_workers: int = 1,
    ) -> CrawlResult:
        artifact_paths: list[str] = []
        discovered_urls = 0
        parsed_listings = 0
        pages_crawled = max_pages
        failed_urls = 0
        source_errors: list[dict[str, str | int]] = []
        scope = self._scope_slug(city)

        for source in self.sources:
            source_payloads: list[dict] = []
            pages = list(range(start_page, start_page + max_pages))
            if search_workers > 1:
                with ThreadPoolExecutor(max_workers=search_workers) as executor:
                    search_results = dict(executor.map(lambda page: (page, self._fetch_search(source, city, page, parallel=True)), pages))
            else:
                search_results = {page: self._fetch_search(source, city, page, parallel=False) for page in pages}

            for page in pages:
                search_url, search_html, search_error = search_results[page]
                if search_error is not None:
                    failed_urls += 1
                    source_errors.append(
                        {
                            "source_name": source.name,
                            "page": page,
                            "url": search_url,
                            "error": f"{type(search_error).__name__}: {search_error}",
                        }
                    )
                    continue
                assert search_html is not None
                if settings.save_raw_html:
                    artifact_paths.append(self.store.write_text(f"raw/search/{source.name}/{scope}/page_{page}.html", search_html))

                direct_parser = getattr(source, "parse_search_payloads", None)
                if direct_parser:
                    discovered_urls_on_page = len(source.parse_search(search_html))
                    discovered_urls += discovered_urls_on_page
                    parsed_payloads = direct_parser(search_html, max_items=max_detail_pages)
                    detail_artifact_paths = []
                    page_failed_urls = 0
                else:
                    detail_urls = source.parse_search(search_html)
                    discovered_urls += len(detail_urls)
                    url_batch = detail_urls[:max_detail_pages] if max_detail_pages is not None else detail_urls
                    parsed_payloads, detail_artifact_paths, page_failed_urls = fetch_listing_batch(
                        urls=url_batch,
                        worker_count=detail_workers,
                        store=self.store,
                        extractor=source,
                        artifact_prefix=f"raw/detail/{source.name}/{scope}/page_{page}",
                        client_factory=PhongtroHttpClient,
                    )
                source_payloads.extend(parsed_payloads)
                artifact_paths.extend([path for path in detail_artifact_paths if path])
                parsed_listings += len(parsed_payloads)
                failed_urls += page_failed_urls

                artifact_paths.append(
                    self.store.write_json(
                        f"normalized/{source.name}/{scope}/page_{page}.json",
                        {"source_name": source.name, "city": city, "page": page, "items": parsed_payloads},
                    )
                )
                artifact_paths.append(
                    export_rows_to_csv(
                        store=self.store,
                        relative_path=f"tabular/{source.name}/{scope}/page_{page}.csv",
                        rows=parsed_payloads,
                    )
                )
            if source_payloads:
                artifact_paths.append(
                    upsert_rows_to_csv(
                        store=self.store,
                        relative_path=f"tabular/{source.name}/{scope}/listings_all.csv",
                        rows=source_payloads,
                    )
                )
                artifact_paths.append(
                    upsert_rows_to_csv(
                        store=self.store,
                        relative_path=f"tabular/{scope}/listings_all.csv",
                        rows=source_payloads,
                    )
                )

        if len(self.sources) > 1:
            artifact_paths.append(
                self.store.write_json(
                    f"normalized/{scope}/sources_latest.json",
                    {"city": city, "sources": [source.name for source in self.sources]},
                )
            )

        manifest = {
            "mode": "bootstrap",
            "city": city,
            "sources": [source.name for source in self.sources],
            "start_page": start_page,
            "max_pages": max_pages,
            "pages_crawled": pages_crawled,
            "failed_urls": failed_urls,
            "source_errors": source_errors,
            "save_raw_html": settings.save_raw_html,
            "artifacts": artifact_paths,
        }
        artifact_paths.append(self.store.write_text("manifests/bootstrap.json", json.dumps(manifest, indent=2)))

        return CrawlResult(
            mode="bootstrap",
            discovered_urls=discovered_urls,
            parsed_listings=parsed_listings,
            failed_urls=failed_urls,
            pages_crawled=pages_crawled,
            artifact_paths=artifact_paths,
        )

    def _fetch_search(
        self,
        source: ListingSource,
        city: str,
        page: int,
        *,
        parallel: bool,
    ) -> tuple[str, str | None, Exception | None]:
        search_url = source.build_search_url(city, page=page, incremental=False)
        try:
            search_fetcher = getattr(source, "fetch_search_text", None)
            if search_fetcher:
                return search_url, search_fetcher(city, page, incremental=False), None
            if parallel:
                client = getattr(self._thread_local, "client", None)
                if client is None:
                    client = PhongtroHttpClient()
                    self._thread_local.client = client
            else:
                client = self.client
            return search_url, client.fetch_text(search_url), None
        except Exception as exc:
            return search_url, None, exc

    def get_last_page(self, city: str) -> int | None:
        last_pages: list[int] = []
        for source in self.sources:
            try:
                html = self.client.fetch_text(source.build_search_url(city, page=1, incremental=False))
            except Exception:
                continue
            last_page = source.extract_last_page(html)
            if last_page:
                last_pages.append(last_page)
        return max(last_pages, default=None)

    def _scope_slug(self, city: str) -> str:
        return "toan-quoc" if city.lower() in {"all", "nationwide", "toan-quoc"} else city
