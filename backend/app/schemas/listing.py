from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class ListingSummary(BaseModel):
    id: UUID
    source_name: str = "unknown"
    source_post_id: str
    title: str
    price_value: int | None = None
    price_per_m2: float | None = None
    area_m2: float | None = None
    street_address: str | None = None
    ward: str | None = None
    full_address: str | None = None
    province: str | None = None
    district: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    geocode_precision: str | None = None
    is_reference_coordinate: bool = False
    room_type: str | None = None
    furnishing_level: str | None = None
    image_count: int = 0
    primary_image_url: str | None = None
    amenity_count: int = 0
    record_completeness_score: int | None = None
    thumbnail_url: str | None = None
    canonical_url: str
    status: Literal["active", "expired", "hidden"]


class ListingDetail(ListingSummary):
    description: str | None = None
    posted_at: datetime | None = None
    expired_at: datetime | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_zalo_url: str | None = None
    contact_facebook_url: str | None = None
    geocode_source: str | None = None
    geocode_display_name: str | None = None
    address_quality_score: int | None = None
    freshness_days: int | None = None
    amenities: list[str] = []
    image_urls: list[str] = []


class ListingMapResponse(BaseModel):
    total: int
    returned: int
    available_provinces: list[str]
    geocode_summary: dict[str, int]
    items: list[ListingSummary]
