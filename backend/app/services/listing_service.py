from __future__ import annotations

import csv
import re
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from uuid import UUID, uuid5, NAMESPACE_URL

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db import get_engine
from app.schemas.listing import ListingDetail, ListingMapResponse, ListingSummary


DISTRICT_ALIASES = {
    "quan 1": "Quận 1",
    "quan 2": "Quận 2",
    "quan 3": "Quận 3",
    "quan 4": "Quận 4",
    "quan 5": "Quận 5",
    "quan 6": "Quận 6",
    "quan 7": "Quận 7",
    "quan 8": "Quận 8",
    "quan 9": "Quận 9",
    "quan 10": "Quận 10",
    "quan 11": "Quận 11",
    "quan 12": "Quận 12",
    "go vap": "Gò Vấp",
    "binh thanh": "Bình Thạnh",
    "tan binh": "Tân Bình",
    "tan phu": "Tân Phú",
    "phu nhuan": "Phú Nhuận",
    "huyen hoc mon": "Huyện Hóc Môn",
    "huyen nha be": "Huyện Nhà Bè",
    "huyen cu chi": "Huyện Củ Chi",
    "huyen binh chanh": "Huyện Bình Chánh",
    "thanh pho da lat": "Thành phố Đà Lạt",
    "thanh pho hue": "Thành phố Huế",
    "thanh pho vung tau": "Thành phố Vũng Tàu",
    "thanh pho thuan an": "Thành phố Thuận An",
    "thanh pho di an": "Thành phố Dĩ An",
}


class ListingService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.dataset_path = Path(self.settings.listing_dataset_path)
        self.engine = get_engine() if self.settings.database_enabled else None

    def list_map(
        self,
        min_price: int | None = None,
        max_price: int | None = None,
        province: str | None = None,
        limit: int | None = None,
    ) -> ListingMapResponse:
        db_response = self._list_map_from_database(
            min_price=min_price,
            max_price=max_price,
            province=province,
            limit=limit,
        )
        if db_response is not None:
            return db_response

        items = self._load_listings_from_csv()
        if province:
            items = [item for item in items if item.province and item.province.lower() == province.lower()]
        if min_price is not None:
            items = [item for item in items if item.price_value is not None and item.price_value >= min_price]
        if max_price is not None:
            items = [item for item in items if item.price_value is not None and item.price_value <= max_price]

        matched_total = len(items)
        capped_items = items[: (limit or self.settings.listing_map_default_limit)]
        available_provinces = sorted({item.province for item in self._load_listings_from_csv() if item.province})
        geocode_summary: dict[str, int] = {}
        for item in items:
            key = item.geocode_precision or "none"
            geocode_summary[key] = geocode_summary.get(key, 0) + 1

        return ListingMapResponse(
            total=matched_total,
            returned=len(capped_items),
            available_provinces=available_provinces,
            geocode_summary=geocode_summary,
            items=[ListingSummary.model_validate(item.model_dump()) for item in capped_items],
        )

    def get_by_id(self, listing_id: UUID) -> ListingDetail | None:
        db_item = self._get_by_id_from_database(listing_id)
        if db_item is not None:
            return db_item

        for item in self._load_listings_from_csv():
            if item.id == listing_id:
                return item
        return None

    @lru_cache(maxsize=1)
    def _load_listings_from_csv(self) -> list[ListingDetail]:
        if not self.dataset_path.exists():
            return self._fallback_listings()

        with self.dataset_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            listings = [self._row_to_listing(row) for row in reader]
        listings.sort(
            key=lambda item: (item.posted_at or datetime.min.replace(tzinfo=UTC), item.record_completeness_score or 0),
            reverse=True,
        )
        return listings

    def _list_map_from_database(
        self,
        *,
        min_price: int | None,
        max_price: int | None,
        province: str | None,
        limit: int | None,
    ) -> ListingMapResponse | None:
        filters_sql, params = self._build_filters(min_price=min_price, max_price=max_price, province=province)
        requested_limit = limit or self.settings.listing_map_default_limit
        if self.engine is None:
            return None

        try:
            with self.engine.connect() as connection:
                total = connection.execute(
                    text(f"SELECT COUNT(*) FROM curated_listings WHERE 1=1 {filters_sql}"),
                    params,
                ).scalar_one()
                if total == 0:
                    return None

                available_provinces = [
                    row[0]
                    for row in connection.execute(
                        text(
                            """
                            SELECT DISTINCT province
                            FROM curated_listings
                            WHERE province IS NOT NULL AND province <> ''
                            ORDER BY province
                            """
                        )
                    ).fetchall()
                ]
                geocode_summary_rows = connection.execute(
                    text(
                        f"""
                        SELECT COALESCE(geocode_precision, 'none') AS precision, COUNT(*) AS total
                        FROM curated_listings
                        WHERE 1=1 {filters_sql}
                        GROUP BY COALESCE(geocode_precision, 'none')
                        """
                    ),
                    params,
                ).fetchall()
                listing_rows = connection.execute(
                    text(
                        f"""
                        SELECT {self._base_select_columns()}
                        FROM curated_listings
                        WHERE 1=1 {filters_sql}
                        ORDER BY posted_at DESC NULLS LAST, record_completeness_score DESC NULLS LAST
                        LIMIT :limit
                        """
                    ),
                    {**params, "limit": requested_limit},
                ).mappings().all()
        except SQLAlchemyError:
            return None

        items = [ListingSummary.model_validate(self._row_to_listing(dict(row)).model_dump()) for row in listing_rows]
        geocode_summary = {str(row.precision): int(row.total) for row in geocode_summary_rows}
        return ListingMapResponse(
            total=int(total),
            returned=len(items),
            available_provinces=available_provinces,
            geocode_summary=geocode_summary,
            items=items,
        )

    def _get_by_id_from_database(self, listing_id: UUID) -> ListingDetail | None:
        if self.engine is None:
            return None

        try:
            with self.engine.connect() as connection:
                row = connection.execute(
                    text(
                        f"""
                        SELECT {self._base_select_columns()}
                        FROM curated_listings
                        WHERE listing_id = :listing_id
                        """
                    ),
                    {"listing_id": listing_id},
                ).mappings().first()
        except SQLAlchemyError:
            return None

        if row is None:
            return None
        return self._row_to_listing(dict(row))

    def _build_filters(
        self,
        *,
        min_price: int | None,
        max_price: int | None,
        province: str | None,
    ) -> tuple[str, dict[str, object]]:
        clauses: list[str] = []
        params: dict[str, object] = {}

        if province:
            clauses.append("AND LOWER(province) = LOWER(:province)")
            params["province"] = province
        if min_price is not None:
            clauses.append("AND price_value IS NOT NULL AND price_value >= :min_price")
            params["min_price"] = min_price
        if max_price is not None:
            clauses.append("AND price_value IS NOT NULL AND price_value <= :max_price")
            params["max_price"] = max_price

        return " ".join(clauses), params

    def _base_select_columns(self) -> str:
        return """
            listing_id,
            source_name,
            source_post_id,
            canonical_url,
            title,
            title_clean,
            price_value,
            price_per_m2,
            area_m2,
            street_address,
            ward,
            full_address,
            province,
            district,
            latitude,
            longitude,
            geocode_precision,
            is_reference_coordinate,
            room_type,
            furnishing_level,
            image_count,
            primary_image_url,
            amenity_count,
            record_completeness_score,
            status,
            description_clean,
            posted_at,
            expired_at,
            contact_name,
            contact_phone,
            contact_zalo_url,
            contact_facebook_url,
            geocode_source,
            geocode_display_name,
            address_quality_score,
            freshness_days,
            amenities_text
        """

    def _row_to_listing(self, row: dict[str, str]) -> ListingDetail:
        canonical_url = str(row.get("canonical_url") or "")
        listing_uuid = row.get("listing_id") or uuid5(
            NAMESPACE_URL,
            canonical_url
            or f"{row.get('source_name') or 'unknown'}:{row.get('source_post_id') or row.get('title') or 'listing'}",
        )
        amenities = self._split_pipe_field(self._stringify(row.get("amenities_text")))
        image_urls = [value for value in [self._stringify(row.get("primary_image_url"))] if value]
        street_address = self._normalize_address_text(row.get("street_address"))
        ward = self._normalize_ward(row.get("ward"))
        district = self._normalize_district(row.get("district"))
        province = self._normalize_province(row.get("province"))
        full_address = self._normalize_full_address(
            row.get("full_address"),
            street_address=street_address,
            ward=ward,
            district=district,
            province=province,
        )
        return ListingDetail(
            id=listing_uuid,
            source_name=self._stringify(row.get("source_name")) or "unknown",
            source_post_id=self._stringify(row.get("source_post_id")) or "",
            title=self._stringify(row.get("title_clean")) or self._stringify(row.get("title")) or "",
            price_value=self._to_int(row.get("price_value")),
            price_per_m2=self._to_float(row.get("price_per_m2")),
            area_m2=self._to_float(row.get("area_m2")),
            street_address=street_address,
            ward=ward,
            full_address=full_address,
            province=province,
            district=district,
            latitude=self._to_float(row.get("latitude")),
            longitude=self._to_float(row.get("longitude")),
            geocode_precision=self._stringify(row.get("geocode_precision")) or None,
            is_reference_coordinate=self._to_bool(row.get("is_reference_coordinate")),
            room_type=self._stringify(row.get("room_type")) or None,
            furnishing_level=self._stringify(row.get("furnishing_level")) or None,
            image_count=self._to_int(row.get("image_count")) or 0,
            primary_image_url=self._stringify(row.get("primary_image_url")) or None,
            amenity_count=self._to_int(row.get("amenity_count")) or len(amenities),
            record_completeness_score=self._to_int(row.get("record_completeness_score")),
            thumbnail_url=self._stringify(row.get("primary_image_url")) or None,
            canonical_url=canonical_url,
            status=(self._stringify(row.get("status")) or "active"),
            description=self._stringify(row.get("description_clean")) or None,
            posted_at=self._to_datetime(row.get("posted_at")),
            expired_at=self._to_datetime(row.get("expired_at")),
            contact_name=self._stringify(row.get("contact_name")) or None,
            contact_phone=self._stringify(row.get("contact_phone")) or None,
            contact_zalo_url=self._stringify(row.get("contact_zalo_url")) or None,
            contact_facebook_url=self._stringify(row.get("contact_facebook_url")) or None,
            geocode_source=self._stringify(row.get("geocode_source")) or None,
            geocode_display_name=self._stringify(row.get("geocode_display_name")) or None,
            address_quality_score=self._to_int(row.get("address_quality_score")),
            freshness_days=self._to_int(row.get("freshness_days")),
            amenities=amenities,
            image_urls=image_urls,
        )

    def _fallback_listings(self) -> list[ListingDetail]:
        demo_now = datetime.now(UTC)
        return [
            ListingDetail(
                id=uuid5(NAMESPACE_URL, "https://phongtro123.com/fallback-1"),
                source_name="fallback",
                source_post_id="fallback-1",
                title="Studio tham khảo Quận 3",
                price_value=7000000,
                price_per_m2=175000,
                area_m2=40,
                street_address="Đường Huỳnh Tịnh Của",
                ward="Phường Nhiêu Lộc",
                full_address="Đường Huỳnh Tịnh Của, Phường Nhiêu Lộc, Quận 3, Hồ Chí Minh",
                province="Hồ Chí Minh",
                district="Quận 3",
                latitude=10.7876,
                longitude=106.6898,
                geocode_precision="district",
                is_reference_coordinate=True,
                room_type="studio",
                furnishing_level="full",
                image_count=1,
                primary_image_url=None,
                amenity_count=4,
                record_completeness_score=88,
                thumbnail_url=None,
                canonical_url="https://phongtro123.com/",
                status="active",
                description="Fallback data while curated export has not been generated.",
                posted_at=demo_now,
                expired_at=None,
                contact_name="Demo owner",
                contact_phone="0900000000",
                contact_zalo_url=None,
                contact_facebook_url=None,
                geocode_source="fallback",
                geocode_display_name="Quận 3, Hồ Chí Minh, Vietnam",
                address_quality_score=80,
                freshness_days=0,
                amenities=["Máy lạnh", "Bãi xe"],
                image_urls=[],
            )
        ]

    def _split_pipe_field(self, value: str | None) -> list[str]:
        return [part.strip() for part in (value or "").split("|") if part.strip()]

    def _stringify(self, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return str(value)

    def _to_int(self, value: str | None) -> int | None:
        try:
            return int(value) if value not in {None, ""} else None
        except ValueError:
            return None

    def _to_float(self, value: str | None) -> float | None:
        try:
            return float(value) if value not in {None, ""} else None
        except ValueError:
            return None

    def _to_datetime(self, value: object) -> datetime | None:
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

    def _to_bool(self, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).lower() in {"true", "1", "yes"}

    def _normalize_full_address(
        self,
        value: str | None,
        *,
        street_address: str | None,
        ward: str | None,
        district: str | None,
        province: str | None,
    ) -> str | None:
        rebuilt: list[str] = []
        for part in [street_address, ward, district, province]:
            normalized = self._normalize_address_text(part)
            if normalized and normalized not in rebuilt:
                rebuilt.append(normalized)
        if rebuilt:
            return ", ".join(rebuilt)

        parts = [self._normalize_address_text(part) for part in (value or "").split(",") if self._normalize_address_text(part)]
        deduped: list[str] = []
        for part in parts:
            if part and part not in deduped:
                deduped.append(part)
        return ", ".join(deduped) if deduped else None

    def _normalize_province(self, value: str | None) -> str | None:
        cleaned = self._normalize_address_text(value)
        if not cleaned:
            return None
        if cleaned == "Bà Rịa, Vũng Tàu":
            return "Bà Rịa - Vũng Tàu"
        return cleaned

    def _normalize_district(self, value: str | None) -> str | None:
        cleaned = self._normalize_address_text(value)
        if not cleaned:
            return None
        alias = DISTRICT_ALIASES.get(self._fold_text(cleaned))
        if alias:
            return alias
        cleaned = re.sub(r"^Quan\s+(\d+)$", r"Quận \1", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^Huyen\s+", "Huyện ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^Thanh Pho\s+", "Thành phố ", cleaned, flags=re.IGNORECASE)
        return cleaned

    def _normalize_ward(self, value: str | None) -> str | None:
        cleaned = self._normalize_address_text(value)
        if not cleaned:
            return None
        cleaned = re.sub(r"^Phuong\s+", "Phường ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^Xa\s+", "Xã ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^P\.?\s*(\d+)$", r"Phường \1", cleaned, flags=re.IGNORECASE)
        return cleaned

    def _normalize_address_text(self, value: str | None) -> str | None:
        if not value:
            return None
        cleaned = re.sub(r"\s+", " ", value).strip(" ,")
        if not cleaned:
            return None
        return cleaned

    def _fold_text(self, value: str) -> str:
        lowered = value.lower()
        replacements = {
            "à": "a", "á": "a", "ạ": "a", "ả": "a", "ã": "a", "ă": "a", "ằ": "a", "ắ": "a", "ặ": "a", "ẳ": "a", "ẵ": "a",
            "â": "a", "ầ": "a", "ấ": "a", "ậ": "a", "ẩ": "a", "ẫ": "a", "đ": "d",
            "è": "e", "é": "e", "ẹ": "e", "ẻ": "e", "ẽ": "e", "ê": "e", "ề": "e", "ế": "e", "ệ": "e", "ể": "e", "ễ": "e",
            "ì": "i", "í": "i", "ị": "i", "ỉ": "i", "ĩ": "i",
            "ò": "o", "ó": "o", "ọ": "o", "ỏ": "o", "õ": "o", "ô": "o", "ồ": "o", "ố": "o", "ộ": "o", "ổ": "o", "ỗ": "o",
            "ơ": "o", "ờ": "o", "ớ": "o", "ợ": "o", "ở": "o", "ỡ": "o",
            "ù": "u", "ú": "u", "ụ": "u", "ủ": "u", "ũ": "u", "ư": "u", "ừ": "u", "ứ": "u", "ự": "u", "ử": "u", "ữ": "u",
            "ỳ": "y", "ý": "y", "ỵ": "y", "ỷ": "y", "ỹ": "y",
        }
        for src, dst in replacements.items():
            lowered = lowered.replace(src, dst)
        return lowered
