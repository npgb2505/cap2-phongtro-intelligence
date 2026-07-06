from __future__ import annotations

import csv
import hashlib
import json
import re
import time
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from app.storage import LocalArtifactStore

SOURCE_RELATIVE_PATH = "tabular/toan-quoc/listings_all.csv"
CURATED_RELATIVE_PATH = "curated/toan-quoc/listings_curated.csv"
CURATED_JSON_RELATIVE_PATH = "curated/toan-quoc/listings_curated.json"
SUMMARY_RELATIVE_PATH = "curated/toan-quoc/curation_summary.json"
GEOCODE_CACHE_RELATIVE_PATH = "geocoding/nominatim_cache.json"

CURATED_COLUMNS = [
    "listing_id",
    "source_name",
    "source_post_id",
    "canonical_url",
    "title",
    "title_clean",
    "status",
    "room_type",
    "furnishing_level",
    "price_text",
    "price_value",
    "price_per_m2",
    "area_text",
    "area_m2",
    "street_address",
    "ward",
    "district",
    "province",
    "full_address",
    "map_reference_address",
    "latitude",
    "longitude",
    "geocode_precision",
    "geocode_source",
    "geocode_display_name",
    "is_reference_coordinate",
    "address_quality_score",
    "record_completeness_score",
    "posted_at",
    "expired_at",
    "freshness_days",
    "contact_name",
    "contact_phone",
    "contact_zalo_url",
    "contact_facebook_url",
    "image_count",
    "primary_image_url",
    "amenities_text",
    "amenity_count",
    "has_aircon",
    "has_private_wc",
    "has_loft",
    "has_parking",
    "has_security",
    "has_fingerprint_lock",
    "allows_free_hours",
    "has_balcony",
    "has_kitchen",
    "has_fridge",
    "has_washer",
    "description_clean",
    "content_hash",
]

PROVINCE_ALIASES = {
    "hcm": "Hồ Chí Minh",
    "tp hcm": "Hồ Chí Minh",
    "tp.hcm": "Hồ Chí Minh",
    "tp ho chi minh": "Hồ Chí Minh",
    "thanh pho ho chi minh": "Hồ Chí Minh",
    "sai gon": "Hồ Chí Minh",
    "ha noi": "Hà Nội",
    "thu do ha noi": "Hà Nội",
    "tp ha noi": "Hà Nội",
    "da nang": "Đà Nẵng",
    "tp da nang": "Đà Nẵng",
    "ba ria vung tau": "Bà Rịa - Vũng Tàu",
}

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
    "binh tan": "Bình Tân",
    "thu duc": "Thủ Đức",
    "huyen nha be": "Huyện Nhà Bè",
    "huyen binh chanh": "Huyện Bình Chánh",
    "huyen hoc mon": "Huyện Hóc Môn",
    "huyen cu chi": "Huyện Củ Chi",
    "huyen can gio": "Huyện Cần Giờ",
    "huyen thanh tri": "Huyện Thanh Trì",
    "huyen dong anh": "Huyện Đông Anh",
    "huyen gia lam": "Huyện Gia Lâm",
    "cau giay": "Cầu Giấy",
    "tay ho": "Tây Hồ",
    "ha dong": "Quận Hà Đông",
    "dong da": "Quận Đống Đa",
    "hoang mai": "Quận Hoàng Mai",
    "bac tu liem": "Quận Bắc Từ Liêm",
    "nam tu liem": "Quận Nam Từ Liêm",
    "hai ba trung": "Quận Hai Bà Trưng",
    "ba dinh": "Quận Ba Đình",
    "long bien": "Quận Long Biên",
    "hai chau": "Quận Hải Châu",
    "thanh khe": "Quận Thanh Khê",
    "lien chieu": "Quận Liên Chiểu",
    "cam le": "Quận Cẩm Lệ",
    "ninh kieu": "Quận Ninh Kiều",
    "thanh pho di an": "Thành phố Dĩ An",
}

DISTRICT_TO_PROVINCE_ALIASES = {
    "quan 1": "Hồ Chí Minh",
    "quan 2": "Hồ Chí Minh",
    "quan 3": "Hồ Chí Minh",
    "quan 4": "Hồ Chí Minh",
    "quan 5": "Hồ Chí Minh",
    "quan 6": "Hồ Chí Minh",
    "quan 7": "Hồ Chí Minh",
    "quan 8": "Hồ Chí Minh",
    "quan 9": "Hồ Chí Minh",
    "quan 10": "Hồ Chí Minh",
    "quan 11": "Hồ Chí Minh",
    "quan 12": "Hồ Chí Minh",
    "go vap": "Hồ Chí Minh",
    "binh thanh": "Hồ Chí Minh",
    "binh chanh": "Hồ Chí Minh",
    "tan binh": "Hồ Chí Minh",
    "tan phu": "Hồ Chí Minh",
    "phu nhuan": "Hồ Chí Minh",
    "binh tan": "Hồ Chí Minh",
    "thu duc": "Hồ Chí Minh",
    "nha be": "Hồ Chí Minh",
    "hoc mon": "Hồ Chí Minh",
    "cu chi": "Hồ Chí Minh",
    "can gio": "Hồ Chí Minh",
    "huyen nha be": "Hồ Chí Minh",
    "huyen binh chanh": "Hồ Chí Minh",
    "huyen hoc mon": "Hồ Chí Minh",
    "huyen cu chi": "Hồ Chí Minh",
    "huyen can gio": "Hồ Chí Minh",
    "cau giay": "Hà Nội",
    "tay ho": "Hà Nội",
    "ha dong": "Hà Nội",
    "dong da": "Hà Nội",
    "hoang mai": "Hà Nội",
    "thanh xuan": "Hà Nội",
    "bac tu liem": "Hà Nội",
    "nam tu liem": "Hà Nội",
    "hai ba trung": "Hà Nội",
    "ba dinh": "Hà Nội",
    "long bien": "Hà Nội",
    "thuan an": "Bình Dương",
    "tan uyen": "Bình Dương",
    "di an": "Bình Dương",
}

DISTRICT_PATTERNS = [
    r"quận\s*\d+",
    r"quan\s*\d+",
    r"q\.?\s*\d+",
    r"huyện\s+[a-zà-ỹ0-9]+(?:\s+[a-zà-ỹ0-9]+){0,3}",
    r"huyen\s+[a-zà-ỹ0-9]+(?:\s+[a-zà-ỹ0-9]+){0,3}",
    r"thành phố\s+[a-zà-ỹ0-9]+(?:\s+[a-zà-ỹ0-9]+){0,3}",
    r"thanh pho\s+[a-zà-ỹ0-9]+(?:\s+[a-zà-ỹ0-9]+){0,3}",
    r"tp\.?\s+[a-zà-ỹ0-9]+(?:\s+[a-zà-ỹ0-9]+){0,3}",
    r"thị xã\s+[a-zà-ỹ0-9]+(?:\s+[a-zà-ỹ0-9]+){0,3}",
    r"thi xa\s+[a-zà-ỹ0-9]+(?:\s+[a-zà-ỹ0-9]+){0,3}",
    r"thị trấn\s+[a-zà-ỹ0-9]+(?:\s+[a-zà-ỹ0-9]+){0,3}",
    r"tp thủ đức",
    r"thủ đức",
    r"tan binh",
    r"tân bình",
    r"gò vấp",
    r"go vap",
    r"bình thạnh",
    r"binh thanh",
    r"phú nhuận",
    r"phu nhuan",
    r"tây hồ",
    r"tay ho",
    r"cầu giấy",
    r"cau giay",
]

WARD_PATTERNS = [
    r"phường\s+[a-zà-ỹ0-9]+(?:\s+[a-zà-ỹ0-9]+){0,3}",
    r"phuong\s+[a-zà-ỹ0-9]+(?:\s+[a-zà-ỹ0-9]+){0,3}",
    r"p\.?\s*\d+",
    r"xã\s+[a-zà-ỹ0-9]+(?:\s+[a-zà-ỹ0-9]+){0,3}",
    r"xa\s+[a-zà-ỹ0-9]+(?:\s+[a-zà-ỹ0-9]+){0,3}",
    r"thị trấn\s+[a-zà-ỹ0-9]+(?:\s+[a-zà-ỹ0-9]+){0,3}",
]

AMENITY_RULES = {
    "has_aircon": ["máy lạnh", "may lanh", "điều hòa", "dieu hoa"],
    "has_private_wc": ["wc riêng", "toilet riêng", "vệ sinh riêng", "ve sinh rieng", "nhà vệ sinh riêng"],
    "has_loft": ["gác", "gac", "gác lửng", "gac lung"],
    "has_parking": ["để xe", "de xe", "hầm để xe", "ham de xe", "giữ xe", "giu xe"],
    "has_security": ["bảo vệ", "bao ve", "camera", "an ninh"],
    "has_fingerprint_lock": ["vân tay", "van tay", "khóa từ", "khoa tu"],
    "allows_free_hours": ["giờ giấc tự do", "gio giac tu do", "24/7", "không chung chủ", "khong chung chu"],
    "has_balcony": ["ban công", "ban cong"],
    "has_kitchen": ["kệ bếp", "ke bep", "bếp", "bep"],
    "has_fridge": ["tủ lạnh", "tu lanh"],
    "has_washer": ["máy giặt", "may giat", "máy sấy", "may say"],
}

ROOM_TYPE_RULES = [
    ("o_ghep", ["ở ghép", "o ghep", "ký túc xá", "ky tuc xa", "dorm", "share"]),
    ("can_ho_mini", ["căn hộ mini", "can ho mini", "ccmn", "chung cư mini"]),
    ("studio", ["studio"]),
    ("phong_tro", ["phòng trọ", "phong tro"]),
    ("nha_nguyen_can", ["nhà nguyên căn", "nha nguyen can"]),
]

FURNISHING_RULES = [
    ("full", ["full nội thất", "full noi that", "đầy đủ nội thất", "day du noi that", "nội thất đầy đủ"]),
    ("partial", ["cơ bản", "co ban", "có sẵn máy lạnh", "có máy lạnh", "máy lạnh"]),
    ("empty", ["không nội thất", "khong noi that", "trống", "nha trong"]),
]

BAD_TITLE_MARKERS = [
    "vui lòng xác minh không phải robot",
    "vui long xac minh khong phai robot",
    "captcha",
    "access denied",
]


@dataclass
class CurationResult:
    source_path: str
    curated_csv_path: str
    curated_json_path: str
    summary_path: str
    total_rows: int
    exact_geocoded_rows: int
    reference_mapped_rows: int
    unique_provinces: int


class CurationPipeline:
    def __init__(self, store: LocalArtifactStore) -> None:
        self.store = store
        self.geocoder = NominatimGeocoder(store.root / GEOCODE_CACHE_RELATIVE_PATH)
        self.address_parts_cache: dict[tuple[str, str, str, str, str, str, str], AddressParts] = {}
        self.exact_location_cache: dict[str, ResolvedLocation | None] = {}
        self.locality_location_cache: dict[str, ResolvedLocation | None] = {}
        self.province_location_cache: dict[str, ResolvedLocation | None] = {}

    def run(self, exact_geocode_limit: int = 120) -> CurationResult:
        source_path = self.store.root / SOURCE_RELATIVE_PATH
        if not source_path.exists():
            raise FileNotFoundError(f"Missing source dataset: {source_path}")

        source_rows = self._read_csv(source_path)
        rows = [row for row in source_rows if _is_curatable_source_row(row)]
        rows.sort(
            key=lambda row: (
                _parse_datetime(row.get("posted_at")) or datetime.min.replace(tzinfo=UTC),
                _to_int(row.get("image_count")) or 0,
                _to_int(row.get("price_value")) or 0,
            ),
            reverse=True,
        )
        exact_budget = ExactGeocodeBudget(limit=exact_geocode_limit)
        curated_rows = [self._curate_row(row, exact_budget) for row in rows]
        curated_rows.sort(
            key=lambda row: (
                _parse_datetime(row.get("posted_at")) or datetime.min.replace(tzinfo=UTC),
                row.get("listing_id") or "",
            ),
            reverse=True,
        )
        self.geocoder.flush()

        curated_csv_path = self.store.write_csv(CURATED_RELATIVE_PATH, curated_rows, CURATED_COLUMNS)
        curated_json_path = self.store.write_json(
            CURATED_JSON_RELATIVE_PATH,
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "total": len(curated_rows),
                "items": curated_rows[:1500],
            },
        )

        precision_counts = Counter(row.get("geocode_precision") or "none" for row in curated_rows)
        summary_path = self.store.write_json(
            SUMMARY_RELATIVE_PATH,
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "source_path": str(source_path),
                "curated_csv_path": curated_csv_path,
                "curated_json_path": curated_json_path,
                "source_rows": len(source_rows),
                "skipped_low_quality_rows": len(source_rows) - len(rows),
                "total_rows": len(curated_rows),
                "unique_provinces": len({row.get("province") for row in curated_rows if row.get("province")}),
                "geocode_precision_counts": dict(precision_counts),
                "exact_geocode_new_queries": exact_budget.used,
                "cache_entries": len(self.geocoder.cache),
            },
        )

        return CurationResult(
            source_path=str(source_path),
            curated_csv_path=curated_csv_path,
            curated_json_path=curated_json_path,
            summary_path=summary_path,
            total_rows=len(curated_rows),
            exact_geocoded_rows=precision_counts.get("exact", 0),
            reference_mapped_rows=len([row for row in curated_rows if row.get("latitude") and row.get("longitude")]),
            unique_provinces=len({row.get("province") for row in curated_rows if row.get("province")}),
        )

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def _curate_row(self, row: dict[str, str], exact_budget: "ExactGeocodeBudget") -> dict[str, Any]:
        title = _clean_text(row.get("title"))
        description = _clean_multiline_text(row.get("description"))
        amenities = _split_pipe_field(row.get("amenities_text"))
        image_urls = _split_pipe_field(row.get("image_urls_text"))
        price_value = _to_int(row.get("price_value")) or _parse_price_text(row.get("price_text"))
        area_m2 = _to_float(row.get("area_m2")) or _parse_area_text(row.get("area_text"))

        full_address = _clean_address_text(row.get("full_address"))
        province = _normalize_province(row.get("province"))
        district = _normalize_district(row.get("district"))
        ward = _normalize_ward(row.get("ward"))
        street_address = _clean_address_text(row.get("street_address"))

        address_parts = self._get_address_parts(
            full_address=full_address,
            street_address=street_address,
            ward=ward,
            district=district,
            province=province,
            title=title,
            description=description,
        )
        map_reference_address = ", ".join(
            [part for part in [address_parts.street_address, address_parts.ward, address_parts.district, address_parts.province, "Vietnam"] if part]
        )

        source_latitude = _to_float(row.get("latitude"))
        source_longitude = _to_float(row.get("longitude"))
        if source_latitude is not None and source_longitude is not None:
            location = ResolvedLocation(
                source_latitude,
                source_longitude,
                "exact",
                f"{row.get('source_name') or 'source'}_payload",
                map_reference_address or full_address,
                True,
            )
        else:
            location = self._resolve_location(
                source_post_id=row.get("source_post_id", ""),
                map_reference_address=map_reference_address,
                street_address=address_parts.street_address,
                district=address_parts.district,
                province=address_parts.province,
                exact_budget=exact_budget,
            )

        posted_at = _normalize_datetime_text(row.get("posted_at"))
        expired_at = _normalize_datetime_text(row.get("expired_at"))
        status = _compute_status(expired_at)
        completeness_score = _compute_completeness_score(
            title=title,
            price_value=price_value,
            area_m2=area_m2,
            address=map_reference_address,
            phone=row.get("contact_phone"),
            image_count=_to_int(row.get("image_count")),
            description=description,
        )
        amenity_flags = derive_amenity_flags(amenities, title, description)

        curated = {
            "listing_id": str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    row.get("canonical_url")
                    or f"{row.get('source_name') or 'unknown'}:{row.get('source_post_id') or title}",
                )
            ),
            "source_name": (row.get("source_name") or "unknown").strip(),
            "source_post_id": (row.get("source_post_id") or "").strip(),
            "canonical_url": (row.get("canonical_url") or "").strip(),
            "title": (row.get("title") or "").strip(),
            "title_clean": title,
            "status": status,
            "room_type": infer_room_type(title, description),
            "furnishing_level": infer_furnishing_level(amenities, title, description),
            "price_text": _clean_text(row.get("price_text")),
            "price_value": price_value,
            "price_per_m2": round(price_value / area_m2, 2) if price_value and area_m2 else None,
            "area_text": _clean_text(row.get("area_text")),
            "area_m2": area_m2,
            "street_address": address_parts.street_address,
            "ward": address_parts.ward,
            "district": address_parts.district,
            "province": address_parts.province,
            "full_address": full_address,
            "map_reference_address": map_reference_address,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "geocode_precision": location.precision,
            "geocode_source": location.source,
            "geocode_display_name": location.display_name,
            "is_reference_coordinate": location.precision != "exact" if location.precision else False,
            "address_quality_score": compute_address_quality(address_parts),
            "record_completeness_score": completeness_score,
            "posted_at": posted_at,
            "expired_at": expired_at,
            "freshness_days": _compute_freshness_days(posted_at),
            "contact_name": _clean_text(row.get("contact_name")),
            "contact_phone": normalize_phone(row.get("contact_phone")),
            "contact_zalo_url": _clean_text(row.get("contact_zalo_url")),
            "contact_facebook_url": _clean_text(row.get("contact_facebook_url")),
            "image_count": _to_int(row.get("image_count")) or len(image_urls),
            "primary_image_url": image_urls[0] if image_urls else None,
            "amenities_text": " | ".join(amenities),
            "amenity_count": len(amenities),
            "description_clean": description,
            "content_hash": (row.get("content_hash") or "").strip(),
        }
        curated.update(amenity_flags)
        return curated

    def _get_address_parts(
        self,
        *,
        full_address: str | None,
        street_address: str | None,
        ward: str | None,
        district: str | None,
        province: str | None,
        title: str,
        description: str,
    ) -> "AddressParts":
        cache_key = (
            full_address or "",
            street_address or "",
            ward or "",
            district or "",
            province or "",
            title,
            description,
        )
        cached = self.address_parts_cache.get(cache_key)
        if cached:
            return cached

        address_parts = split_address(
            full_address=full_address,
            street_address=street_address,
            ward=ward,
            district=district,
            province=province,
            title=title,
            description=description,
        )
        self.address_parts_cache[cache_key] = address_parts
        return address_parts

    def _resolve_location(
        self,
        *,
        source_post_id: str,
        map_reference_address: str,
        street_address: str | None,
        district: str | None,
        province: str | None,
        exact_budget: "ExactGeocodeBudget",
    ) -> "ResolvedLocation":
        if (
            map_reference_address
            and district
            and province
            and exact_budget.can_use()
            and _is_exact_geocode_eligible(street_address, map_reference_address)
        ):
            exact = self._get_exact_location(map_reference_address)
            if exact:
                exact_budget.consume_if_new(exact.was_cache_hit)
                return exact

        locality_query = ", ".join([part for part in [district, province, "Vietnam"] if part])
        if locality_query:
            locality = self._get_locality_location(locality_query)
            if locality:
                return locality.with_jitter(source_post_id, amplitude=0.0045)

        if province:
            province_result = self._get_province_location(f"{province}, Vietnam")
            if province_result:
                return province_result.with_jitter(source_post_id, amplitude=0.09)

        return ResolvedLocation(None, None, None, None, None, False)

    def _get_exact_location(self, query: str) -> "ResolvedLocation | None":
        if query not in self.exact_location_cache:
            self.exact_location_cache[query] = self.geocoder.geocode(query, precision="exact")
        return self.exact_location_cache[query]

    def _get_locality_location(self, query: str) -> "ResolvedLocation | None":
        if query not in self.locality_location_cache:
            self.locality_location_cache[query] = self.geocoder.geocode(query, precision="district")
        return self.locality_location_cache[query]

    def _get_province_location(self, query: str) -> "ResolvedLocation | None":
        if query not in self.province_location_cache:
            self.province_location_cache[query] = self.geocoder.geocode(query, precision="province")
        return self.province_location_cache[query]


@dataclass
class ExactGeocodeBudget:
    limit: int
    used: int = 0

    def can_use(self) -> bool:
        return self.used < self.limit

    def consume_if_new(self, was_cache_hit: bool) -> None:
        if not was_cache_hit:
            self.used += 1


@dataclass
class AddressParts:
    street_address: str | None
    ward: str | None
    district: str | None
    province: str | None


@dataclass
class ResolvedLocation:
    latitude: float | None
    longitude: float | None
    precision: str | None
    source: str | None
    display_name: str | None
    was_cache_hit: bool

    def with_jitter(self, key: str, amplitude: float) -> "ResolvedLocation":
        if self.latitude is None or self.longitude is None:
            return self
        seed = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)
        lat_offset = (((seed % 1000) / 1000) - 0.5) * amplitude
        lon_offset = ((((seed // 1000) % 1000) / 1000) - 0.5) * amplitude
        return ResolvedLocation(
            latitude=round(self.latitude + lat_offset, 7),
            longitude=round(self.longitude + lon_offset, 7),
            precision=self.precision,
            source=self.source,
            display_name=self.display_name,
            was_cache_hit=self.was_cache_hit,
        )


class NominatimGeocoder:
    def __init__(self, cache_path: Path) -> None:
        self.cache_path = cache_path
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache = self._load_cache()
        self.client = httpx.Client(
            timeout=8.0,
            headers={
                "User-Agent": "PhongTroCap2/0.1 (educational ETL demo)",
                "Accept-Language": "vi,en",
            },
        )
        self.dirty = False

    def _load_cache(self) -> dict[str, Any]:
        if not self.cache_path.exists():
            return {}
        return json.loads(self.cache_path.read_text(encoding="utf-8"))

    def geocode(self, query: str, precision: str) -> ResolvedLocation | None:
        normalized_query = _clean_text(query)
        if not normalized_query:
            return None

        cache_key = f"{precision}:{normalized_query.lower()}"
        if cache_key in self.cache:
            payload = self.cache[cache_key]
            return ResolvedLocation(
                latitude=payload.get("latitude"),
                longitude=payload.get("longitude"),
                precision=payload.get("precision"),
                source=payload.get("source"),
                display_name=payload.get("display_name"),
                was_cache_hit=True,
            )

        try:
            response = self.client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": normalized_query,
                    "format": "jsonv2",
                    "limit": 1,
                    "countrycodes": "vn",
                    "addressdetails": 1,
                },
            )
            response.raise_for_status()
            items = response.json()
        except Exception:
            return None

        time.sleep(1.05)
        if not items:
            self.cache[cache_key] = {"latitude": None, "longitude": None, "precision": None, "source": None, "display_name": None}
            self.dirty = True
            return None

        first = items[0]
        result = ResolvedLocation(
            latitude=_to_float(first.get("lat")),
            longitude=_to_float(first.get("lon")),
            precision=precision,
            source="nominatim",
            display_name=first.get("display_name"),
            was_cache_hit=False,
        )
        self.cache[cache_key] = {
            "latitude": result.latitude,
            "longitude": result.longitude,
            "precision": result.precision,
            "source": result.source,
            "display_name": result.display_name,
        }
        self.dirty = True
        return result

    def flush(self) -> None:
        if not self.dirty:
            return
        self.cache_path.write_text(json.dumps(self.cache, ensure_ascii=False, indent=2), encoding="utf-8")
        self.dirty = False


def split_address(
    *,
    full_address: str | None,
    street_address: str | None,
    ward: str | None,
    district: str | None,
    province: str | None,
    title: str,
    description: str,
) -> AddressParts:
    parts = [_clean_address_text(part) for part in (full_address or "").split(",") if _clean_address_text(part)]
    candidate_street = street_address or (parts[0] if parts else None)
    candidate_ward = ward
    candidate_district = district
    candidate_province = province

    for part in parts[1:]:
        lowered = _fold_text(part)
        if candidate_ward is None and any(re.search(pattern, lowered) for pattern in WARD_PATTERNS):
            candidate_ward = _normalize_ward(part)
            continue
        if candidate_district is None and any(re.search(pattern, lowered) for pattern in DISTRICT_PATTERNS):
            candidate_district = _normalize_district(part)
            continue
        if candidate_province is None:
            candidate_province = _normalize_province(part)

    if candidate_ward is None:
        candidate_ward = _normalize_ward(_extract_match(full_address or "", WARD_PATTERNS))
    if candidate_district is None:
        candidate_district = _normalize_district(_extract_match(full_address or "", DISTRICT_PATTERNS))
    if candidate_district is None:
        candidate_district = _normalize_district(_extract_match(f"{title} {description}", DISTRICT_PATTERNS))
    if candidate_province is None:
        candidate_province = _normalize_province(_extract_province_from_text(full_address or ""))
    if candidate_province is None:
        candidate_province = _normalize_province(_extract_province_from_text(f"{title} {description}"))

    if candidate_district and candidate_province and _fold_locality_name(candidate_district) == _fold_locality_name(candidate_province):
        candidate_district = None

    inferred_province = _province_for_district_name(candidate_province)
    if inferred_province:
        if candidate_district is None:
            candidate_district = _normalize_district(candidate_province)
        candidate_province = inferred_province

    if candidate_street and candidate_district and _fold_text(candidate_street) == _fold_text(candidate_district):
        candidate_street = None

    return AddressParts(
        street_address=candidate_street,
        ward=candidate_ward,
        district=candidate_district,
        province=candidate_province,
    )


def compute_address_quality(parts: AddressParts) -> int:
    score = 0
    if parts.street_address:
        score += 40
    if parts.ward:
        score += 20
    if parts.district:
        score += 20
    if parts.province:
        score += 20
    return score


def infer_room_type(title: str, description: str) -> str:
    haystack = _fold_text(f"{title} {description}")
    for room_type, keywords in ROOM_TYPE_RULES:
        if any(keyword in haystack for keyword in keywords):
            return room_type
    return "khac"


def infer_furnishing_level(amenities: list[str], title: str, description: str) -> str:
    haystack = _fold_text(" ".join(amenities) + " " + title + " " + description)
    for level, keywords in FURNISHING_RULES:
        if any(keyword in haystack for keyword in keywords):
            return level
    return "unknown"


def derive_amenity_flags(amenities: list[str], title: str, description: str) -> dict[str, bool]:
    haystack = _fold_text(" ".join(amenities) + " " + title + " " + description)
    return {field: any(keyword in haystack for keyword in keywords) for field, keywords in AMENITY_RULES.items()}


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D+", "", value)
    if len(digits) == 10 and digits.startswith("0"):
        return digits
    if len(digits) == 11 and digits.startswith("84"):
        return f"0{digits[2:]}"
    return digits or None


def _is_curatable_source_row(row: dict[str, str]) -> bool:
    title = _clean_text(row.get("title"))
    canonical_url = _clean_text(row.get("canonical_url"))
    if not title or not canonical_url:
        return False

    folded_title = _fold_text(title)
    return not any(marker in folded_title for marker in BAD_TITLE_MARKERS)


def _normalize_province(value: str | None) -> str | None:
    cleaned = _clean_address_text(value)
    if not cleaned:
        return None
    cleaned = re.split(r"\bXem\s+Bản\s+Đồ\b", cleaned, maxsplit=1, flags=re.IGNORECASE)[0].strip(" ,.-")
    cleaned = re.split(r"\bXem\s+Ban\s+Do\b", cleaned, maxsplit=1, flags=re.IGNORECASE)[0].strip(" ,.-")
    cleaned = re.split(r"\b\d+(?:[.,]\d+)?\s*(?:Triệu|Trieu|Nghìn|Nghin|K|VND|Đồng|Dong)\b", cleaned, maxsplit=1, flags=re.IGNORECASE)[0].strip(" ,.-")
    if not cleaned:
        return None
    folded = _fold_text(cleaned)
    if folded.startswith("ho chi minh"):
        return "Hồ Chí Minh"
    if folded.startswith("ha noi"):
        return "Hà Nội"
    if folded.startswith("da nang"):
        return "Đà Nẵng"
    if folded.startswith("binh duong"):
        return "Bình Dương"
    if re.match(r"^(duong|ngo|ngach|hem|pho|so|phuong|xa|thi tran)\s+", folded):
        return None
    alias = PROVINCE_ALIASES.get(folded)
    if alias:
        return alias
    cleaned = re.sub(r"^(tp\.?|thành phố)\s+", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip().title().replace("Hồ Chí Minh", "Hồ Chí Minh").replace("Đà Nẵng", "Đà Nẵng")


def _normalize_district(value: str | None) -> str | None:
    cleaned = _clean_address_text(value)
    if not cleaned:
        return None
    cleaned = re.sub(r"^Cho thuê [^,]*?\b(quận|huyện|thành phố|tp\.?)", lambda m: m.group(1), cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^Cho thue [^,]*?\b(quan|huyen|thanh pho|tp\.?)", lambda m: m.group(1), cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^Q\.?\s*(\d+)$", r"Quận \1", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^Quan\s*(\d+)$", r"Quận \1", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^Quận\s*0*(\d+)$", r"Quận \1", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^Huyen\s+", "Huyện ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^Thanh Pho\s+", "Thành phố ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^Tp\.?\s*", "TP. ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-")
    alias = DISTRICT_ALIASES.get(_fold_text(cleaned))
    if alias:
        return alias
    if re.match(r"^(quận|huyện|thành phố|tp\.|thị xã|thị trấn|thủ đức)", _fold_text(cleaned)):
        return _smart_title(cleaned)
    match = _extract_match(cleaned, DISTRICT_PATTERNS)
    matched_clean = _smart_title(match) if match else _smart_title(cleaned)
    alias = DISTRICT_ALIASES.get(_fold_text(matched_clean))
    return alias or matched_clean


def _normalize_ward(value: str | None) -> str | None:
    cleaned = _clean_address_text(value)
    if not cleaned:
        return None
    cleaned = re.sub(r"^P\.?\s*(\d+)$", r"Phường \1", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^Phuong\s+", "Phường ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^Xa\s+", "Xã ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-")
    match = _extract_match(cleaned, WARD_PATTERNS)
    return _smart_title(match) if match else _smart_title(cleaned)


def _clean_address_text(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    cleaned = re.sub(r"\s*-\s*", ", ", cleaned)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    cleaned = re.sub(r",(\S)", r", \1", cleaned)
    return cleaned.strip(" ,")


def _clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("\ufeff", " ")).strip()


def _clean_multiline_text(value: str | None) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in (value or "").splitlines()]
    return "\n".join([line for line in lines if line])


def _split_pipe_field(value: str | None) -> list[str]:
    return [_clean_text(part) for part in (value or "").split("|") if _clean_text(part)]


def _to_int(value: Any) -> int | None:
    try:
        cleaned = re.sub(r"[^\d-]", "", str(value))
        return int(cleaned) if cleaned else None
    except Exception:
        return None


def _to_float(value: Any) -> float | None:
    try:
        cleaned = str(value).strip()
        return float(cleaned) if cleaned else None
    except Exception:
        return None


def _parse_price_text(value: str | None) -> int | None:
    text = _fold_text(value or "")
    match = re.search(r"(\d+(?:[.,]\d+)?)", text)
    if not match:
        return None
    numeric = float(match.group(1).replace(",", "."))
    if "trieu" in text:
        return int(numeric * 1_000_000)
    if "k" in text:
        return int(numeric * 1_000)
    return int(numeric)


def _parse_area_text(value: str | None) -> float | None:
    match = re.search(r"(\d+(?:[.,]\d+)?)", value or "")
    return float(match.group(1).replace(",", ".")) if match else None


def _normalize_datetime_text(value: str | None) -> str | None:
    parsed = _parse_datetime(value)
    return parsed.isoformat() if parsed else None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _compute_status(expired_at: str | None) -> str:
    expired = _parse_datetime(expired_at)
    if expired and expired < datetime.now(UTC):
        return "expired"
    return "active"


def _compute_freshness_days(posted_at: str | None) -> int | None:
    posted = _parse_datetime(posted_at)
    if not posted:
        return None
    return max(0, (datetime.now(UTC) - posted.astimezone(UTC)).days)


def _compute_completeness_score(
    *,
    title: str,
    price_value: int | None,
    area_m2: float | None,
    address: str,
    phone: str | None,
    image_count: int | None,
    description: str,
) -> int:
    score = 0
    if title:
        score += 15
    if price_value:
        score += 15
    if area_m2:
        score += 10
    if address:
        score += 20
    if phone:
        score += 10
    if image_count and image_count > 0:
        score += 15
    if len(description) >= 80:
        score += 15
    return score


def _is_exact_geocode_eligible(street_address: str | None, map_reference_address: str) -> bool:
    street = _clean_text(street_address)
    query = _clean_text(map_reference_address)
    if not street or not query:
        return False
    if not re.search(r"\d", street):
        return False
    vague_street_tokens = ["đường", "duong", "street", "road"]
    folded_street = _fold_text(street)
    if folded_street in vague_street_tokens:
        return False
    return True


def _extract_match(text: str, patterns: list[str]) -> str | None:
    source = _clean_text(text)
    lowered = source.lower()
    for pattern in patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            return source[match.start() : match.end()]
    return None


def _prefer_richer_text(current: str | None, candidate: str | None) -> str | None:
    if not candidate:
        return current
    if not current:
        return candidate
    current_score = _text_richness_score(current)
    candidate_score = _text_richness_score(candidate)
    if candidate_score > current_score:
        return candidate
    return current


def _text_richness_score(value: str) -> tuple[int, int]:
    return (
        sum(1 for char in value if ord(char) > 127),
        len(value),
    )


def _smart_title(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    if not cleaned:
        return cleaned
    parts = cleaned.split(" ")
    lowered = [part.lower() for part in parts]
    acronyms = {"tp.", "tp", "q.", "p."}
    titled = []
    for part, lower in zip(parts, lowered, strict=False):
        if lower in acronyms:
            titled.append(part.upper() if "." in part else part.capitalize())
            continue
        if lower.isdigit():
            titled.append(lower)
            continue
        titled.append(lower[0].upper() + lower[1:] if lower else lower)
    return " ".join(titled)


def _extract_province_from_text(text: str) -> str | None:
    folded = _fold_text(text)
    for alias, canonical in PROVINCE_ALIASES.items():
        if alias in folded:
            return canonical
    match = re.search(r"(hồ chí minh|ha noi|hà nội|đà nẵng|da nang|bình dương|cần thơ|đồng nai|khánh hòa|khánh hoà|hải phòng)", folded)
    return match.group(1) if match else None


def _fold_text(value: str) -> str:
    text = (value or "").lower()
    replacements = {
        "à": "a",
        "á": "a",
        "ạ": "a",
        "ả": "a",
        "ã": "a",
        "ă": "a",
        "ằ": "a",
        "ắ": "a",
        "ặ": "a",
        "ẳ": "a",
        "ẵ": "a",
        "â": "a",
        "ầ": "a",
        "ấ": "a",
        "ậ": "a",
        "ẩ": "a",
        "ẫ": "a",
        "đ": "d",
        "è": "e",
        "é": "e",
        "ẹ": "e",
        "ẻ": "e",
        "ẽ": "e",
        "ê": "e",
        "ề": "e",
        "ế": "e",
        "ệ": "e",
        "ể": "e",
        "ễ": "e",
        "ì": "i",
        "í": "i",
        "ị": "i",
        "ỉ": "i",
        "ĩ": "i",
        "ò": "o",
        "ó": "o",
        "ọ": "o",
        "ỏ": "o",
        "õ": "o",
        "ô": "o",
        "ồ": "o",
        "ố": "o",
        "ộ": "o",
        "ổ": "o",
        "ỗ": "o",
        "ơ": "o",
        "ờ": "o",
        "ớ": "o",
        "ợ": "o",
        "ở": "o",
        "ỡ": "o",
        "ù": "u",
        "ú": "u",
        "ụ": "u",
        "ủ": "u",
        "ũ": "u",
        "ư": "u",
        "ừ": "u",
        "ứ": "u",
        "ự": "u",
        "ử": "u",
        "ữ": "u",
        "ỳ": "y",
        "ý": "y",
        "ỵ": "y",
        "ỷ": "y",
        "ỹ": "y",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return re.sub(r"\s+", " ", text).strip()


def _fold_locality_name(value: str) -> str:
    folded = _fold_text(value)
    folded = re.sub(r"^(tp\.?|thanh pho|quận|quan|huyện|huyen|thị xã|thi xa|thị trấn|thi tran)\s+", "", folded)
    folded = re.sub(r"[^a-z0-9\s]", " ", folded)
    return re.sub(r"\s+", " ", folded).strip()


def _province_for_district_name(value: str | None) -> str | None:
    if not value:
        return None
    folded = _fold_locality_name(value)
    return DISTRICT_TO_PROVINCE_ALIASES.get(folded) or DISTRICT_TO_PROVINCE_ALIASES.get(_fold_text(value))
