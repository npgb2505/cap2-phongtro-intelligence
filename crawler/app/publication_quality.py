from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import urlparse


MIN_MONTHLY_PRICE = 300_000
MAX_MONTHLY_PRICE = 30_000_000
MIN_AREA_M2 = 6
MAX_AREA_M2 = 300
MIN_DESCRIPTION_LENGTH = 80

PLACEHOLDER_IMAGE_MARKERS = (
    "thumb_default",
    "no-image",
    "no_image",
    "placeholder",
    "default-image",
    "default_image",
)
SOCIAL_DOMAINS = ("zalo.me", "facebook.com", "fb.com", "messenger.com")
INVALID_CONTACT_NAMES = {"an danh", "khong ro", "n/a", "none", "unknown"}
LOCATION_CONTACT_PREFIX = re.compile(
    r"^(duong|hem|huyen|ngo|phuong|quan|thanh pho|thi tran|tinh|xa)\b"
)
PHONE_PATTERN = re.compile(r"^0\d{9}$")


@dataclass(frozen=True)
class PublicationAssessment:
    score: int
    publishable: bool
    has_real_image: bool
    has_direct_contact: bool
    has_contact_name: bool
    has_valid_price: bool
    has_valid_area: bool
    has_address: bool
    has_description: bool


def _text(value: object) -> str:
    return " ".join(str(value or "").split())


def _number(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0


def _fold(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", value.lower())
        if unicodedata.category(character) != "Mn"
    )


def _http_url(value: object) -> bool:
    try:
        parsed = urlparse(_text(value))
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname)
    except ValueError:
        return False


def is_public_image_url(value: object) -> bool:
    url = _text(value)
    lowered = url.lower()
    if not _http_url(url) or any(marker in lowered for marker in PLACEHOLDER_IMAGE_MARKERS):
        return False
    try:
        hostname = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    return "." in hostname and not any(
        hostname == domain or hostname.endswith(f".{domain}") for domain in SOCIAL_DOMAINS
    )


def is_direct_contact(row: dict[str, str]) -> bool:
    phone = re.sub(r"\D", "", _text(row.get("contact_phone")))
    if PHONE_PATTERN.fullmatch(phone):
        return True
    for key in ("contact_zalo_url", "contact_facebook_url"):
        value = _text(row.get(key))
        if not _http_url(value):
            continue
        hostname = (urlparse(value).hostname or "").lower().removeprefix("www.")
        if any(hostname == domain or hostname.endswith(f".{domain}") for domain in SOCIAL_DOMAINS):
            return True
    return False


def is_contact_name(value: object) -> bool:
    name = _text(value)
    folded = _fold(name)
    if not 2 <= len(name) <= 80 or not any(character.isalpha() for character in name):
        return False
    return folded not in INVALID_CONTACT_NAMES and not LOCATION_CONTACT_PREFIX.match(folded)


def evaluate_publication_quality(row: dict[str, str]) -> PublicationAssessment:
    has_real_image = is_public_image_url(row.get("primary_image_url")) and _number(row.get("image_count")) >= 1
    has_direct_contact = is_direct_contact(row)
    has_contact_name = is_contact_name(row.get("contact_name"))
    has_valid_price = MIN_MONTHLY_PRICE <= _number(row.get("price_value")) <= MAX_MONTHLY_PRICE
    has_valid_area = MIN_AREA_M2 <= _number(row.get("area_m2")) <= MAX_AREA_M2
    has_location = bool(_text(row.get("province")) and _text(row.get("district")))
    has_address = has_location and bool(_text(row.get("street_address")) or _text(row.get("full_address")))
    description = _text(row.get("description_clean"))
    has_description = len(description) >= MIN_DESCRIPTION_LENGTH
    title = _text(row.get("title_clean")) or _text(row.get("title"))
    has_title = len(title) >= 12
    has_canonical_url = _http_url(row.get("canonical_url"))
    is_active = _text(row.get("status")) in {"", "active"}

    score = 0
    score += 15 if has_real_image else 0
    score += 15 if has_direct_contact else 8 if has_contact_name else 0
    score += 10 if has_valid_price else 0
    score += 8 if has_valid_area else 0
    score += 6 if has_location else 0
    score += 8 if has_address else 0
    score += 12 if has_description else 0
    score += 5 if has_title else 0
    score += 4 if has_canonical_url else 0
    score += 10 if is_active else 0
    score += min(int(_number(row.get("image_count"))), 4)
    score += min(int(_number(row.get("amenity_count"))), 4)
    score += 3 if _text(row.get("geocode_precision")) == "exact" else 0
    if _text(row.get("freshness_days")):
        freshness_days = _number(row.get("freshness_days"))
        score += 5 if 0 <= freshness_days <= 7 else 3 if freshness_days <= 30 else 0

    publishable = all(
        (
            has_real_image,
            has_direct_contact or has_contact_name,
            has_valid_price,
            has_valid_area,
            has_address,
            has_description,
            has_title,
            has_canonical_url,
        )
    )
    return PublicationAssessment(
        score=min(score, 100),
        publishable=publishable,
        has_real_image=has_real_image,
        has_direct_contact=has_direct_contact,
        has_contact_name=has_contact_name,
        has_valid_price=has_valid_price,
        has_valid_area=has_valid_area,
        has_address=has_address,
        has_description=has_description,
    )


def publication_sort_key(
    row: dict[str, str], assessment: PublicationAssessment
) -> tuple[int, int, int, int, int, str]:
    return (
        int(_text(row.get("status")) in {"", "active"}),
        int(assessment.has_direct_contact),
        assessment.score,
        int(_number(row.get("image_count"))),
        int(_number(row.get("record_completeness_score"))),
        _text(row.get("posted_at")),
    )
