from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ListingRecord:
    source_name: str
    source_post_id: str
    canonical_url: str
    title: str
    price_text: str | None = None
    price_value: int | None = None
    area_text: str | None = None
    area_m2: float | None = None
    full_address: str | None = None
    street_address: str | None = None
    ward: str | None = None
    district: str | None = None
    province: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    description: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_zalo_url: str | None = None
    contact_facebook_url: str | None = None
    image_count: int = 0
    posted_at: datetime | None = None
    expired_at: datetime | None = None
    amenities: list[str] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)


@dataclass
class CrawlResult:
    mode: str
    discovered_urls: int
    parsed_listings: int
    failed_urls: int = 0
    pages_crawled: int = 0
    artifact_paths: list[str] = field(default_factory=list)
