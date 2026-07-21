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
    "thua thien hue": "Huế",
}

CANONICAL_PROVINCES = (
    "An Giang", "Bà Rịa - Vũng Tàu", "Bắc Giang", "Bắc Kạn", "Bạc Liêu", "Bắc Ninh",
    "Bến Tre", "Bình Định", "Bình Dương", "Bình Phước", "Bình Thuận", "Cà Mau", "Cần Thơ",
    "Cao Bằng", "Đà Nẵng", "Đắk Lắk", "Đắk Nông", "Điện Biên", "Đồng Nai", "Đồng Tháp",
    "Gia Lai", "Hà Giang", "Hà Nam", "Hà Nội", "Hà Tĩnh", "Hải Dương", "Hải Phòng", "Hậu Giang",
    "Hòa Bình", "Hồ Chí Minh", "Huế", "Hưng Yên", "Khánh Hòa", "Kiên Giang", "Kon Tum", "Lai Châu",
    "Lâm Đồng", "Lạng Sơn", "Lào Cai", "Long An", "Nam Định", "Nghệ An", "Ninh Bình", "Ninh Thuận",
    "Phú Thọ", "Phú Yên", "Quảng Bình", "Quảng Nam", "Quảng Ngãi", "Quảng Ninh", "Quảng Trị",
    "Sóc Trăng", "Sơn La", "Tây Ninh", "Thái Bình", "Thái Nguyên", "Thanh Hóa", "Tiền Giang",
    "Trà Vinh", "Tuyên Quang", "Vĩnh Long", "Vĩnh Phúc", "Yên Bái",
)

KNOWN_CONTACT_HOTLINES = {"0909316890"}
CURATABLE_SOURCES = {"phongtro123", "nhatot", "mogi"}
_PROVINCE_LOOKUP: dict[str, str] | None = None

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
        started_at = time.perf_counter()
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
        deduped_rows: list[dict[str, str]] = []
        seen_source_keys: set[str] = set()
        for row in rows:
            source_key = _source_row_key(row)
            if source_key and source_key in seen_source_keys:
                continue
            if source_key:
                seen_source_keys.add(source_key)
            deduped_rows.append(row)
        duplicate_source_rows = len(rows) - len(deduped_rows)
        rows = deduped_rows
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
                "skipped_low_quality_rows": len(source_rows) - len(rows) - duplicate_source_rows,
                "duplicate_source_rows": duplicate_source_rows,
                "total_rows": len(curated_rows),
                "unique_provinces": len({row.get("province") for row in curated_rows if row.get("province")}),
                "geocode_precision_counts": dict(precision_counts),
                "exact_geocode_new_queries": exact_budget.used,
                "cache_entries": len(self.geocoder.cache),
                "duration_seconds": round(time.perf_counter() - started_at, 2),
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
        price_value = _normalize_price_value(row.get("price_value"), row.get("price_text"))
        area_m2 = _normalize_area_m2(row.get("area_m2"), row.get("area_text"))

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
        contact_phone = normalize_phone(row.get("contact_phone"))
        contact_name = normalize_contact_name(row.get("contact_name"))
        contact_zalo_url = normalize_zalo_url(row.get("contact_zalo_url"), contact_phone)
        completeness_score = _compute_completeness_score(
            title=title,
            price_value=price_value,
            area_m2=area_m2,
            address=map_reference_address,
            phone=contact_phone,
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
            "contact_name": contact_name,
            "contact_phone": contact_phone,
            "contact_zalo_url": contact_zalo_url,
            "contact_facebook_url": _clean_text(row.get("contact_facebook_url")),
            "image_count": _normalize_image_count(row.get("image_count"), image_urls),
            "primary_image_url": image_urls[0] if image_urls else None,
            "amenities_text": " | ".join(amenities),
            "amenity_count": len(amenities),
            "description_clean": description,
            "content_hash": self._normalize_content_hash(row),
        }
        curated.update(amenity_flags)
        return curated

    def _normalize_content_hash(self, row: dict[str, str]) -> str:
        content_hash = (row.get("content_hash") or "").strip()
        if content_hash:
            return content_hash

        seed_parts = [
            row.get("canonical_url") or "",
            row.get("source_name") or "",
            row.get("source_post_id") or "",
            row.get("title") or "",
            row.get("posted_at") or "",
        ]
        seed = "|".join(part.strip() for part in seed_parts if part is not None)
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()

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
            was_cache_hit = self.geocoder.is_cached(map_reference_address, "exact")
            exact = self._get_exact_location(map_reference_address)
            exact_budget.consume_if_new(was_cache_hit)
            if exact:
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
        self.pending_writes = 0

    def _load_cache(self) -> dict[str, Any]:
        if not self.cache_path.exists():
            return {}
        return json.loads(self.cache_path.read_text(encoding="utf-8"))

    def is_cached(self, query: str, precision: str) -> bool:
        normalized_query = _clean_text(query)
        return bool(normalized_query and f"v2:{precision}:{normalized_query.lower()}" in self.cache)

    def geocode(self, query: str, precision: str) -> ResolvedLocation | None:
        normalized_query = _clean_text(query)
        if not normalized_query:
            return None

        cache_key = f"v2:{precision}:{normalized_query.lower()}"
        if cache_key in self.cache:
            payload = self.cache[cache_key]
            if payload.get("latitude") is None or payload.get("longitude") is None:
                return None
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
                    "limit": 5,
                    "countrycodes": "vn",
                    "addressdetails": 1,
                },
            )
            response.raise_for_status()
            items = response.json()
        except Exception:
            return None

        time.sleep(1.05)
        accepted = next(
            (item for item in items if _is_nominatim_result_acceptable(item, normalized_query, precision)),
            None,
        )
        if accepted is None:
            self.cache[cache_key] = {"latitude": None, "longitude": None, "precision": None, "source": None, "display_name": None}
            self._mark_dirty()
            return None

        result = ResolvedLocation(
            latitude=_to_float(accepted.get("lat")),
            longitude=_to_float(accepted.get("lon")),
            precision=precision,
            source="nominatim",
            display_name=accepted.get("display_name"),
            was_cache_hit=False,
        )
        self.cache[cache_key] = {
            "latitude": result.latitude,
            "longitude": result.longitude,
            "precision": result.precision,
            "source": result.source,
            "display_name": result.display_name,
        }
        self._mark_dirty()
        return result

    def _mark_dirty(self) -> None:
        self.dirty = True
        self.pending_writes += 1
        if self.pending_writes >= 25:
            self.flush()

    def flush(self) -> None:
        if not self.dirty:
            return
        temp_path = self.cache_path.with_suffix(f"{self.cache_path.suffix}.tmp")
        temp_path.write_text(json.dumps(self.cache, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(self.cache_path)
        self.dirty = False
        self.pending_writes = 0


def _is_nominatim_result_acceptable(item: dict[str, Any], query: str, precision: str) -> bool:
    latitude = _to_float(item.get("lat"))
    longitude = _to_float(item.get("lon"))
    if latitude is None or longitude is None:
        return False
    if not (8.0 <= latitude <= 24.0 and 102.0 <= longitude <= 110.0):
        return False

    address = item.get("address") if isinstance(item.get("address"), dict) else {}
    display_name = _clean_text(item.get("display_name"))
    category = _fold_text(str(item.get("category") or item.get("class") or ""))
    address_type = _fold_text(str(item.get("addresstype") or item.get("type") or ""))
    result_folded = _fold_text(" ".join([display_name, *[str(value) for value in address.values() if value]]))

    if precision == "exact":
        query_house_number = _extract_house_number(query)
        result_house_number = _clean_house_number(address.get("house_number"))
        if not query_house_number or query_house_number != result_house_number:
            return False
        query_road = _extract_query_road(query)
        result_road = _clean_text(
            address.get("road")
            or address.get("pedestrian")
            or address.get("residential")
            or address.get("neighbourhood")
        )
        return bool(query_road and result_road and _road_tokens_match(query_road, result_road))

    allowed_locality_categories = {"boundary", "place"}
    allowed_locality_types = {
        "administrative",
        "borough",
        "city",
        "city district",
        "county",
        "municipality",
        "province",
        "state",
        "state district",
        "suburb",
        "town",
    }
    if category not in allowed_locality_categories and address_type not in allowed_locality_types:
        return False

    query_parts = [_fold_text(part) for part in query.split(",") if _clean_text(part)]
    meaningful_parts = [part for part in query_parts if part and part not in {"vietnam", "viet nam"}]
    if not meaningful_parts:
        return False
    required_matches = 2 if len(meaningful_parts) >= 2 else 1
    return sum(1 for part in meaningful_parts if part in result_folded) >= required_matches


def _extract_house_number(value: str | None) -> str | None:
    first_part = _clean_text(value).split(",", 1)[0]
    match = re.match(r"^\s*([A-Za-z]?\d+[A-Za-z]?(?:[\/-]\d+[A-Za-z]?)+|\d+[A-Za-z]?)\b", first_part)
    return _clean_house_number(match.group(1)) if match else None


def _clean_house_number(value: Any) -> str | None:
    cleaned = re.sub(r"\s+", "", str(value or "")).lower().strip(".,")
    return cleaned or None


def _extract_query_road(value: str) -> str | None:
    first_part = _clean_text(value).split(",", 1)[0]
    house_number = _extract_house_number(first_part)
    if house_number:
        first_part = re.sub(r"^\s*\S+\s+", "", first_part, count=1)
    return _clean_text(first_part) or None


def _road_tokens_match(first: str, second: str) -> bool:
    ignored = {"duong", "pho", "road", "street", "hem", "ngo", "ngach"}
    first_tokens = {token for token in re.findall(r"[a-z0-9]+", _fold_text(first)) if token not in ignored}
    second_tokens = {token for token in re.findall(r"[a-z0-9]+", _fold_text(second)) if token not in ignored}
    if not first_tokens or not second_tokens:
        return False
    return len(first_tokens & second_tokens) / len(first_tokens) >= 0.7


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
    return None


def normalize_contact_name(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if not cleaned or len(cleaned) > 80 or re.search(r"\d", cleaned):
        return None
    folded = _fold_text(cleaned)
    invalid_markers = (
        "cho thue", "phong", "can ho", "noi that", "tien nghi", "trieu", "thang",
        "dien tich", "duong ", "quan ", "gan ", "gia ", "ngay canh", "day du",
    )
    return None if any(marker in folded for marker in invalid_markers) else cleaned


def normalize_zalo_url(value: str | None, contact_phone: str | None) -> str | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    match = re.search(r"zalo\.me/(?:pc\?|share/)?(?:phone=)?(0\d{9,10})", cleaned, flags=re.IGNORECASE)
    if not match:
        return None
    zalo_phone = match.group(1)
    if zalo_phone in KNOWN_CONTACT_HOTLINES:
        return None
    if contact_phone and zalo_phone != contact_phone:
        return None
    return cleaned


def _is_curatable_source_row(row: dict[str, str]) -> bool:
    title = _clean_text(row.get("title"))
    canonical_url = _clean_text(row.get("canonical_url"))
    source_value = _clean_text(row.get("source_name"))
    if not title or not canonical_url or source_value not in CURATABLE_SOURCES:
        return False

    folded_title = _fold_text(title)
    if any(marker in folded_title for marker in BAD_TITLE_MARKERS):
        return False
    if source_value == "nhatot" and re.match(
        r"^(?:minh\s+)?can tim (?:p?tro|nha tro|phong tro|phong|nha thue)\b",
        folded_title,
    ):
        return False
    source_name = re.escape(source_value)
    return re.search(rf"{source_name},\d+,https?://", title, flags=re.IGNORECASE) is None


def _source_row_key(row: dict[str, str]) -> str:
    canonical_url = _clean_text(row.get("canonical_url"))
    if canonical_url:
        return canonical_url.lower().rstrip("/")
    source_name = _clean_text(row.get("source_name"))
    source_post_id = _clean_text(row.get("source_post_id"))
    return f"{source_name}:{source_post_id}" if source_name and source_post_id else ""


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
    if re.match(r"^(duong|ngo|ngach|hem|pho|so|phuong|xa|thi tran)\s+", folded):
        return None
    cleaned = re.sub(r"^(tp\.?|thành phố)\s+", "", cleaned, flags=re.IGNORECASE)
    return _province_lookup().get(_fold_text(cleaned))


def _province_lookup() -> dict[str, str]:
    global _PROVINCE_LOOKUP
    if _PROVINCE_LOOKUP is None:
        _PROVINCE_LOOKUP = {_fold_text(name): name for name in CANONICAL_PROVINCES}
        _PROVINCE_LOOKUP.update(PROVINCE_ALIASES)
        _PROVINCE_LOOKUP.update({
            "ba ria, vung tau": "Bà Rịa - Vũng Tàu",
            "ba ria - vung tau": "Bà Rịa - Vũng Tàu",
            "thua thien hue": "Huế",
            "tp hue": "Huế",
        })
    return _PROVINCE_LOOKUP


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
    return "\n".join([line for line in lines if line and not re.fullmatch(r"[<=>|]{7,}", line)])


def _split_pipe_field(value: str | None) -> list[str]:
    return [_clean_text(part) for part in (value or "").split("|") if _clean_text(part)]


def _to_int(value: Any) -> int | None:
    try:
        cleaned = re.sub(r"[^\d-]", "", str(value))
        return int(cleaned) if cleaned else None
    except Exception:
        return None


def _normalize_image_count(value: Any, image_urls: list[str]) -> int:
    parsed = _to_int(value)
    if parsed is None or parsed < 0 or parsed > 1000:
        return len(image_urls)
    return parsed


def _to_float(value: Any) -> float | None:
    try:
        cleaned = str(value).strip()
        return float(cleaned) if cleaned else None
    except Exception:
        return None


def _normalize_area_m2(raw_area: Any, area_text: str | None) -> float | None:
    parsed = _to_float(raw_area) or _parse_area_text(area_text)
    if parsed is None or parsed <= 0:
        return None
    if parsed > 100000:
        return None
    return parsed


def _normalize_price_value(raw_price: Any, price_text: str | None) -> int | None:
    parsed = _to_int(raw_price) or _parse_price_text(price_text)
    if parsed is None or parsed <= 0:
        return None
    if parsed > 1_000_000_000_000:
        return None
    return parsed


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
