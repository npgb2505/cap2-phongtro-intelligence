from app.client import PhongtroHttpClient
from app.config import settings
from app.detail_fetcher import fetch_listing_batch
from app.models import CrawlResult
from app.sources import ListingSource
from app.storage import LocalArtifactStore
from app.tabular_export import export_rows_to_csv, upsert_rows_to_csv


class IncrementalPipeline:
    def __init__(self, store: LocalArtifactStore, sources: list[ListingSource], client: PhongtroHttpClient) -> None:
        self.store = store
        self.sources = sources
        self.client = client

    def run(
        self,
        city: str,
        pages: int = 1,
        max_detail_pages: int | None = None,
        detail_workers: int = 1,
    ) -> CrawlResult:
        parsed_payloads = []
        artifact_paths: list[str] = []
        discovered_urls = 0
        failed_urls = 0
        source_errors: list[dict[str, str | int]] = []
        scope = self._scope_slug(city)

        for source in self.sources:
            source_payloads = []
            for page in range(1, pages + 1):
                search_url = source.build_search_url(city, page=page, incremental=True)
                try:
                    search_fetcher = getattr(source, "fetch_search_text", None)
                    if search_fetcher:
                        search_html = search_fetcher(city, page, incremental=True)
                    else:
                        search_html = self.client.fetch_text(search_url)
                except Exception as exc:
                    failed_urls += 1
                    source_errors.append(
                        {
                            "source_name": source.name,
                            "page": page,
                            "url": search_url,
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
                    continue
                if settings.save_raw_html:
                    artifact_paths.append(self.store.write_text(f"raw/search/{source.name}/{scope}/incremental_page_{page}.html", search_html))
                direct_parser = getattr(source, "parse_search_payloads", None)
                if direct_parser:
                    discovered_urls_on_page = len(source.parse_search(search_html))
                    discovered_urls += discovered_urls_on_page
                    page_payloads = direct_parser(search_html, max_items=max_detail_pages)
                    detail_artifact_paths = []
                    page_failed_urls = 0
                else:
                    detail_urls = source.parse_search(search_html)
                    discovered_urls += len(detail_urls)
                    url_batch = detail_urls[:max_detail_pages] if max_detail_pages is not None else detail_urls
                    page_payloads, detail_artifact_paths, page_failed_urls = fetch_listing_batch(
                        urls=url_batch,
                        worker_count=detail_workers,
                        store=self.store,
                        extractor=source,
                        artifact_prefix=f"raw/detail/{source.name}/{scope}/incremental_page_{page}",
                        client_factory=PhongtroHttpClient,
                    )
                parsed_payloads.extend(page_payloads)
                source_payloads.extend(page_payloads)
                artifact_paths.extend([path for path in detail_artifact_paths if path])
                failed_urls += page_failed_urls
            if source_payloads:
                artifact_paths.append(
                    export_rows_to_csv(
                        store=self.store,
                        relative_path=f"tabular/{source.name}/{scope}/incremental_latest.csv",
                        rows=source_payloads,
                    )
                )

        artifact_paths.append(self.store.write_json(
            f"normalized/{scope}/incremental_latest.json",
            {
                "city": city,
                "mode": "incremental",
                "sources": [source.name for source in self.sources],
                "source_errors": source_errors,
                "items": parsed_payloads,
            },
        ))
        artifact_paths.append(
            export_rows_to_csv(
                store=self.store,
                relative_path=f"tabular/{scope}/incremental_latest.csv",
                rows=parsed_payloads,
            )
        )
        artifact_paths.append(
            upsert_rows_to_csv(
                store=self.store,
                relative_path=f"tabular/{scope}/listings_all.csv",
                rows=parsed_payloads,
            )
        )

        return CrawlResult(
            mode="incremental",
            discovered_urls=discovered_urls,
            parsed_listings=len(parsed_payloads),
            failed_urls=failed_urls,
            pages_crawled=pages,
            artifact_paths=artifact_paths,
        )

    def _scope_slug(self, city: str) -> str:
        return "toan-quoc" if city.lower() in {"all", "nationwide", "toan-quoc"} else city
