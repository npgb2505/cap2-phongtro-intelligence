from __future__ import annotations

import hashlib
import json
import re
import base64
import gzip
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from dataclasses import asdict
from dataclasses import dataclass
from datetime import UTC, datetime, timezone, timedelta
from typing import Protocol
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.extractors.phongtro123 import Phongtro123Extractor
from app.models import ListingRecord

# Sources kept in the production dataset. The other adapters remain available for
# diagnostics, but their current yield is too small or repetitive to publish.
DEFAULT_SOURCE_NAMES = ["phongtro123", "nhatot", "mogi"]


class ListingSource(Protocol):
    name: str
    base_url: str

    def build_search_url(self, city: str, page: int, *, incremental: bool) -> str:
        ...

    def parse_search(self, html: str) -> list[str]:
        ...

    def parse_search_payloads(self, html: str, *, max_items: int | None = None) -> list[dict]:
        ...

    def parse_detail(self, html: str, url: str) -> ListingRecord:
        ...

    def build_content_hash(self, listing: ListingRecord) -> str:
        ...

    def extract_last_page(self, html: str) -> int | None:
        ...


@dataclass(frozen=True)
class SourceDefinition:
    name: str
    base_url: str
    search_all_path: str
    search_city_path: str
    detail_url_patterns: tuple[str, ...]
    incremental_query: str = ""


class Phongtro123Source:
    name = "phongtro123"
    base_url = "https://phongtro123.com"

    def __init__(self) -> None:
        self.extractor = Phongtro123Extractor()

    def build_search_url(self, city: str, page: int, *, incremental: bool) -> str:
        orderby = "orderby=moi-nhat&" if incremental else ""
        if city.lower() in {"all", "nationwide", "toan-quoc"}:
            return f"{self.base_url}?{orderby}page={page}"
        return f"{self.base_url}/tinh-thanh/{city}?{orderby}page={page}"

    def parse_search(self, html: str) -> list[str]:
        return self.extractor.parse_search(html, self.base_url)

    def parse_detail(self, html: str, url: str) -> ListingRecord:
        record = self.extractor.parse_detail(html, url)
        record.source_name = self.name
        return record

    def build_content_hash(self, listing: ListingRecord) -> str:
        return self.extractor.build_content_hash(listing)

    def extract_last_page(self, html: str) -> int | None:
        return self.extractor.extract_last_page(html)


class GenericRentalSource:
    def __init__(self, definition: SourceDefinition) -> None:
        self.definition = definition
        self.name = definition.name
        self.base_url = definition.base_url

    def build_search_url(self, city: str, page: int, *, incremental: bool) -> str:
        path = self.definition.search_all_path
        if city.lower() not in {"all", "nationwide", "toan-quoc"}:
            path = self.definition.search_city_path.format(city=city)
        joiner = "&" if "?" in path else "?"
        query = f"{joiner}page={page}"
        if incremental and self.definition.incremental_query:
            query += f"&{self.definition.incremental_query}"
        return urljoin(self.base_url, path + query)

    def parse_search(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        urls: list[str] = []
        for link in soup.select("a[href]"):
            href = link.get("href", "").strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            absolute = urljoin(self.base_url, href)
            if self._looks_like_detail_url(absolute):
                urls.append(absolute.split("#", 1)[0])
        return sorted(set(urls))

    def parse_detail(self, html: str, url: str) -> ListingRecord:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        json_ld = _extract_json_ld(soup)
        title = _first_text(
            _meta(soup, "og:title"),
            _json_ld_value(json_ld, "name"),
            _text(soup.select_one("h1")),
            _text(soup.select_one("title")),
            "Untitled listing",
        )
        description = _first_text(
            _meta(soup, "og:description"),
            _meta_name(soup, "description"),
            _json_ld_value(json_ld, "description"),
            _longest_paragraph(soup),
        )
        canonical_url = _attr(soup.select_one('link[rel="canonical"]'), "href") or url
        price_text = _first_text(
            _json_ld_value(json_ld, "priceRange"),
            _find_text(text, r"(\d+[.,]?\d*\s*(?:triệu|tr|k|nghìn|đồng|vnd)(?:/tháng)?)"),
        )
        area_text = _find_text(text, r"(\d+(?:[.,]\d+)?)\s*m(?:2|²)")
        full_address = _extract_address(json_ld, text)
        street_address, ward, district, province = _split_address(full_address)
        image_urls = _extract_images(soup, json_ld)
        contact_phone = _find_text(text, r"((?:\+?84|0)\d[\d\s.-]{7,12}\d)")

        return ListingRecord(
            source_name=self.name,
            source_post_id=self._extract_post_id(url, html),
            canonical_url=canonical_url,
            title=title,
            price_text=price_text,
            price_value=_parse_price(price_text),
            area_text=f"{area_text} m2" if area_text else None,
            area_m2=_parse_float(area_text),
            full_address=full_address,
            street_address=street_address,
            ward=ward,
            district=district,
            province=province,
            description=description,
            contact_phone=_normalize_phone(contact_phone),
            image_count=len(image_urls),
            posted_at=_extract_datetime(json_ld) or datetime.now(UTC),
            amenities=_extract_amenities(text),
            image_urls=image_urls,
        )

    def build_content_hash(self, listing: ListingRecord) -> str:
        parts = [
            listing.source_name,
            listing.source_post_id,
            listing.title,
            listing.price_text or "",
            listing.area_text or "",
            listing.full_address or "",
            listing.description or "",
            ",".join(listing.amenities),
            ",".join(listing.image_urls),
            listing.contact_phone or "",
        ]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()

    def extract_last_page(self, html: str) -> int | None:
        matches = re.findall(r"[?&]page=(\d+)", html)
        return max([int(value) for value in matches], default=None)

    def _looks_like_detail_url(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.netloc and parsed.netloc != urlparse(self.base_url).netloc:
            return False
        lowered = parsed.path.lower()
        return any(re.search(pattern, lowered) for pattern in self.definition.detail_url_patterns)

    def _extract_post_id(self, url: str, html: str) -> str:
        patterns = [
            r"(?:pr|post|tin|listing|ad)[-/]?(\d{5,})",
            r"[-_/](\d{6,})(?:\.html|/)?$",
            r'"(?:productID|ad_id|listing_id|id)"\s*:\s*"?(\d{5,})"?',
        ]
        for pattern in patterns:
            match = re.search(pattern, url, flags=re.IGNORECASE) or re.search(pattern, html, flags=re.IGNORECASE)
            if match:
                return match.group(1)
        return hashlib.md5(url.encode("utf-8")).hexdigest()[:12]


class NhaTotApiSource:
    name = "nhatot"
    base_url = "https://gateway.chotot.com"
    page_size = 20

    def build_search_url(self, city: str, page: int, *, incremental: bool) -> str:
        offset = max(0, page - 1) * self.page_size
        return f"{self.base_url}/v1/public/ad-listing?cg=1050&limit={self.page_size}&o={offset}"

    def parse_search(self, html: str) -> list[str]:
        payload = json.loads(html)
        return [self._canonical_url(ad) for ad in payload.get("ads", []) if isinstance(ad, dict)]

    def parse_search_payloads(self, html: str, *, max_items: int | None = None) -> list[dict]:
        payload = json.loads(html)
        ads = [ad for ad in payload.get("ads", []) if isinstance(ad, dict)]
        if max_items is not None:
            ads = ads[:max_items]
        return [_record_to_payload(self._ad_to_record(ad), self) for ad in ads]

    def parse_detail(self, html: str, url: str) -> ListingRecord:
        payload = json.loads(html)
        ads = [ad for ad in payload.get("ads", []) if isinstance(ad, dict)]
        if not ads:
            raise ValueError(f"NhaTot API response has no ads for {url}")
        return self._ad_to_record(ads[0])

    def build_content_hash(self, listing: ListingRecord) -> str:
        parts = [
            listing.source_name,
            listing.source_post_id,
            listing.title,
            listing.price_text or "",
            listing.area_text or "",
            listing.full_address or "",
            listing.description or "",
            ",".join(listing.image_urls),
            listing.contact_name or "",
        ]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()

    def extract_last_page(self, html: str) -> int | None:
        payload = json.loads(html)
        total = payload.get("total")
        if not isinstance(total, int) or total <= 0:
            return None
        return (total + self.page_size - 1) // self.page_size

    def _ad_to_record(self, ad: dict) -> ListingRecord:
        source_post_id = str(ad.get("list_id") or ad.get("ad_id") or "")
        title = str(ad.get("subject") or "Untitled listing").strip()
        street_address = ", ".join(
            str(part).strip()
            for part in [ad.get("street_number"), ad.get("street_name")]
            if part
        ) or None
        ward = _clean_optional(ad.get("ward_name_v3") or ad.get("ward_name"))
        district = _clean_optional(ad.get("area_name"))
        province = _clean_optional(ad.get("region_name_v3") or ad.get("region_name"))
        full_address = ", ".join(part for part in [street_address, ward, district, province] if part)
        image_urls = [str(url) for url in ad.get("images") or [] if url]
        if ad.get("image"):
            image_urls.insert(0, str(ad["image"]))
        posted_at = _datetime_from_millis(ad.get("list_time"))

        return ListingRecord(
            source_name=self.name,
            source_post_id=source_post_id or hashlib.md5(json.dumps(ad, sort_keys=True).encode("utf-8")).hexdigest()[:12],
            canonical_url=self._canonical_url(ad),
            title=title,
            price_text=_clean_optional(ad.get("price_string")),
            price_value=_to_int(ad.get("price")),
            area_text=f"{ad.get('size')} m2" if ad.get("size") else None,
            area_m2=_parse_float(str(ad.get("size"))) if ad.get("size") else None,
            full_address=full_address or None,
            street_address=street_address,
            ward=ward,
            district=district,
            province=province,
            latitude=_parse_float(str(ad.get("latitude"))) if ad.get("latitude") else None,
            longitude=_parse_float(str(ad.get("longitude"))) if ad.get("longitude") else None,
            description=_clean_optional(ad.get("body")),
            contact_name=_clean_optional(ad.get("account_name") or ad.get("full_name")),
            image_count=_to_int(ad.get("number_of_images")) or len(set(image_urls)),
            posted_at=posted_at,
            amenities=_extract_amenities(str(ad.get("body") or "")),
            image_urls=sorted(set(image_urls)),
        )

    def _canonical_url(self, ad: dict) -> str:
        post_id = str(ad.get("list_id") or ad.get("ad_id") or "")
        slug = _slugify(str(ad.get("subject") or "tin-dang"))
        return f"https://www.nhatot.com/{slug}-{post_id}.htm"


class MogiSource:
    name = "mogi"
    base_url = "https://mogi.vn"

    def build_search_url(self, city: str, page: int, *, incremental: bool) -> str:
        if city.lower() in {"ho-chi-minh", "hcm", "tp-hcm", "sai-gon"}:
            path = "/ho-chi-minh/thue-phong-tro-nha-tro"
        else:
            path = "/thue-phong-tro-nha-tro"
        query = f"?cp={page}" if page > 1 else ""
        return f"{self.base_url}{path}{query}"

    def parse_search(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        urls: list[str] = []
        for link in soup.select("ul.props a.link-overlay[href]"):
            href = link.get("href", "").strip()
            if href:
                urls.append(urljoin(self.base_url, href).split("#", 1)[0])
        return sorted(set(urls))

    def parse_search_payloads(self, html: str, *, max_items: int | None = None) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("ul.props > li")
        if max_items is not None:
            cards = cards[:max_items]
        records = [record for card in cards if (record := self._card_to_record(card)) is not None]
        return [_record_to_payload(record, self) for record in records]

    def parse_detail(self, html: str, url: str) -> ListingRecord:
        soup = BeautifulSoup(html, "html.parser")
        title = _first_text(
            _text(soup.select_one("h1")),
            _meta(soup, "og:title"),
            _text(soup.select_one("title")),
            "Untitled listing",
        )
        description = _first_text(
            _meta(soup, "og:description"),
            _meta_name(soup, "description"),
            _longest_paragraph(soup),
        )
        full_address = _first_text(
            _text(soup.select_one(".address")),
            _text(soup.select_one(".prop-addr")),
        ) or None
        street_address, ward, district, province = _split_address(full_address)
        price_text = _first_text(_text(soup.select_one(".price")), _find_text(soup.get_text(" ", strip=True), r"(\d+[.,]?\d*\s*(?:triệu|tr|nghìn|k)(?:\s+\d+\s*nghìn)?)"))
        area_text = _find_text(soup.get_text(" ", strip=True), r"(\d+(?:[.,]\d+)?)\s*m(?:2|²)")
        image_urls = _extract_images(soup, [])
        return ListingRecord(
            source_name=self.name,
            source_post_id=self._extract_post_id(url),
            canonical_url=url,
            title=title,
            price_text=price_text,
            price_value=_parse_price(price_text),
            area_text=f"{area_text} m2" if area_text else None,
            area_m2=_parse_float(area_text),
            full_address=full_address,
            street_address=street_address,
            ward=ward,
            district=district,
            province=province,
            description=description,
            image_count=len(image_urls),
            posted_at=_parse_date_text(_clean_optional(_text(soup.select_one(".prop-created")))) or datetime.now(UTC),
            amenities=_extract_amenities(description or title),
            image_urls=image_urls,
        )

    def build_content_hash(self, listing: ListingRecord) -> str:
        parts = [
            listing.source_name,
            listing.source_post_id,
            listing.title,
            listing.price_text or "",
            listing.area_text or "",
            listing.full_address or "",
            ",".join(listing.image_urls),
        ]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()

    def extract_last_page(self, html: str) -> int | None:
        matches = re.findall(r"[?&]cp=(\d+)", html)
        return max([int(value) for value in matches], default=None)

    def _card_to_record(self, card) -> ListingRecord | None:
        link = card.select_one("a.link-overlay[href]")
        if not link:
            return None
        canonical_url = urljoin(self.base_url, link.get("href", "").strip()).split("#", 1)[0]
        title = _first_text(_text(link.select_one(".prop-title")), _text(card.select_one(".prop-title")))
        if not title:
            return None

        address = _clean_optional(_text(card.select_one(".prop-addr")))
        district, province = self._split_card_address(address)
        area_text = self._extract_card_area(card)
        price_text = _clean_optional(_text(card.select_one(".price")))
        image_urls = self._extract_card_images(card)

        return ListingRecord(
            source_name=self.name,
            source_post_id=self._extract_post_id(canonical_url),
            canonical_url=canonical_url,
            title=title,
            price_text=price_text,
            price_value=self._parse_mogi_price(price_text),
            area_text=area_text,
            area_m2=_parse_area_text(area_text),
            full_address=address,
            district=district,
            province=province,
            image_count=len(image_urls),
            posted_at=_parse_date_text(_clean_optional(_text(card.select_one(".prop-created")))) or datetime.now(UTC),
            amenities=_extract_amenities(title),
            image_urls=image_urls,
        )

    def _extract_post_id(self, url: str) -> str:
        match = re.search(r"id(\d+)", url)
        return match.group(1) if match else hashlib.md5(url.encode("utf-8")).hexdigest()[:12]

    def _split_card_address(self, value: str | None) -> tuple[str | None, str | None]:
        if not value:
            return None, None
        parts = [part.strip() for part in value.split(",") if part.strip()]
        district = parts[0] if parts else None
        province = parts[-1] if len(parts) > 1 else None
        province_aliases = {"tphcm": "Hồ Chí Minh", "tp.hcm": "Hồ Chí Minh", "hcm": "Hồ Chí Minh"}
        if province:
            province = province_aliases.get(_fold_text(province), province)
        return district, province

    def _extract_card_area(self, card) -> str | None:
        for node in card.select(".prop-attr li"):
            text = node.get_text(" ", strip=True)
            if "m" in text.lower():
                value = _find_text(text, r"(\d+(?:[.,]\d+)?)\s*m")
                return f"{value} m2" if value else None
        return None

    def _extract_card_images(self, card) -> list[str]:
        urls: list[str] = []
        for img in card.select("img"):
            for attr in ["data-src", "src"]:
                value = img.get(attr, "").strip()
                if value and not value.startswith("data:"):
                    urls.append(value)
            srcset = img.get("srcset", "")
            if srcset:
                first = srcset.split(",", 1)[0].strip().split(" ", 1)[0]
                if first:
                    urls.append(first)
        return sorted(set(urls))

    def _parse_mogi_price(self, value: str | None) -> int | None:
        if not value:
            return None
        folded = _fold_text(value)
        millions = re.search(r"(\d+(?:[.,]\d+)?)\s*trieu", folded)
        thousands = re.search(r"(\d+(?:[.,]\d+)?)\s*nghin", folded)
        total = 0
        if millions:
            total += int(float(millions.group(1).replace(",", ".")) * 1_000_000)
        if thousands:
            total += int(float(thousands.group(1).replace(",", ".")) * 1_000)
        if total:
            return total
        return _parse_price(value)


def build_sources(source_names: list[str] | None = None) -> list[ListingSource]:
    registry: dict[str, ListingSource] = {
        "phongtro123": Phongtro123Source(),
        "alonhadat": GenericRentalSource(
            SourceDefinition(
                name="alonhadat",
                base_url="https://alonhadat.com.vn",
                search_all_path="/nha-dat/cho-thue/phong-tro-nha-tro.html",
                search_city_path="/nha-dat/cho-thue/phong-tro-nha-tro.html",
                detail_url_patterns=(r"/.+-\d{6,}\.html$",),
            )
        ),
        "thuephongtro": GenericRentalSource(
            SourceDefinition(
                name="thuephongtro",
                base_url="https://thuephongtro.com",
                search_all_path="/cho-thue-phong-tro",
                search_city_path="/cho-thue-phong-tro-{city}",
                detail_url_patterns=(r"/(?!cho-thue-|tim-nguoi-|tin-da-luu|dang-|tai-khoan|hop-thu|blog|kinh-nghiem).+-\d{5,}\.html$",),
            )
        ),
        "nhatot": NhaTotApiSource(),
        "batdongsan": BatDongSanApiSource(),
        "mogi": MogiSource(),
    }
    requested = source_names or DEFAULT_SOURCE_NAMES
    unknown = [name for name in requested if name not in registry]
    if unknown:
        raise ValueError(f"Unknown source(s): {', '.join(unknown)}. Available: {', '.join(registry)}")
    return [registry[name] for name in requested]


def _extract_json_ld(soup: BeautifulSoup) -> list[dict]:
    values: list[dict] = []
    for node in soup.select('script[type="application/ld+json"]'):
        raw = node.string or node.get_text(strip=True)
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            values.append(payload)
        elif isinstance(payload, list):
            values.extend(item for item in payload if isinstance(item, dict))
    return values


def _json_ld_value(items: list[dict], key: str) -> str | None:
    for item in items:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_address(items: list[dict], text: str) -> str | None:
    for item in items:
        address = item.get("address")
        if isinstance(address, dict):
            parts = [address.get("streetAddress"), address.get("addressLocality"), address.get("addressRegion")]
            value = ", ".join(str(part).strip() for part in parts if part)
            if value:
                return value
        if isinstance(address, str) and address.strip():
            return address.strip()
    return _find_text(text, r"(?:Địa chỉ|Dia chi)\s*:?\s*([^|]{10,160})")


def _split_address(value: str | None) -> tuple[str | None, str | None, str | None, str | None]:
    if not value:
        return None, None, None, None
    parts = [part.strip() for part in value.split(",") if part.strip()]
    street = parts[0] if parts else None
    ward = None
    district = None
    province = None
    for part in parts[1:]:
        lowered = part.lower()
        if ward is None and any(token in lowered for token in ["phường", "xã", "p."]):
            ward = part
        elif district is None and any(token in lowered for token in ["quận", "huyện", "tp", "thành phố"]):
            district = part
        elif province is None:
            province = part
    return street, ward, district, province


def _extract_images(soup: BeautifulSoup, items: list[dict]) -> list[str]:
    urls = [_meta(soup, "og:image")]
    for item in items:
        image = item.get("image")
        if isinstance(image, str):
            urls.append(image)
        elif isinstance(image, list):
            urls.extend(str(value) for value in image if value)
    urls.extend(img.get("src", "") for img in soup.select("img[src]")[:20])
    return sorted({url for url in urls if url and not url.startswith("data:")})


def _extract_amenities(text: str) -> list[str]:
    keywords = ["máy lạnh", "điều hòa", "gác", "wc riêng", "ban công", "bếp", "tủ lạnh", "máy giặt", "giữ xe", "camera", "an ninh"]
    folded = text.lower()
    return [keyword for keyword in keywords if keyword in folded]


def _extract_datetime(items: list[dict]) -> datetime | None:
    value = _json_ld_value(items, "datePublished") or _json_ld_value(items, "datePosted")
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _first_text(*values: str | None) -> str:
    for value in values:
        if value and value.strip():
            return re.sub(r"\s+", " ", value).strip()
    return ""


def _text(node) -> str | None:
    return node.get_text(" ", strip=True) if node else None


def _attr(node, name: str) -> str | None:
    return node.get(name) if node else None


def _meta(soup: BeautifulSoup, property_name: str) -> str | None:
    return _attr(soup.select_one(f'meta[property="{property_name}"]'), "content")


def _meta_name(soup: BeautifulSoup, name: str) -> str | None:
    return _attr(soup.select_one(f'meta[name="{name}"]'), "content")


def _longest_paragraph(soup: BeautifulSoup) -> str | None:
    paragraphs = [node.get_text(" ", strip=True) for node in soup.select("p")]
    return max(paragraphs, key=len, default=None)


def _find_text(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else None


def _parse_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def _parse_price(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"(\d+(?:[.,]\d+)?)", value)
    if not match:
        return None
    amount = float(match.group(1).replace(",", "."))
    folded = value.lower()
    if "triệu" in folded or re.search(r"\btr\b", folded):
        return int(amount * 1_000_000)
    if "k" in folded or "nghìn" in folded:
        return int(amount * 1_000)
    return int(amount)


def _parse_area_text(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"(\d+(?:[.,]\d+)?)", value)
    return _parse_float(match.group(1)) if match else None


def _parse_date_text(value: str | None) -> datetime | None:
    if not value:
        return None
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})", value)
    if not match:
        return None
    return datetime.fromisoformat(f"{match.group(3)}-{match.group(2)}-{match.group(1)}T00:00:00+07:00")


def _normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D+", "", value)
    if len(digits) == 11 and digits.startswith("84"):
        return f"0{digits[2:]}"
    return digits or None


def _record_to_payload(record: ListingRecord, source: ListingSource) -> dict:
    return {
        **asdict(record),
        "content_hash": source.build_content_hash(record),
    }


def _clean_optional(value: object) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def _to_int(value: object) -> int | None:
    try:
        return int(value) if value not in {None, ""} else None
    except (TypeError, ValueError):
        return None


def _datetime_from_millis(value: object) -> datetime | None:
    numeric = _to_int(value)
    if numeric is None:
        return None
    return datetime.fromtimestamp(numeric / 1000, tz=UTC)


def _slugify(value: str) -> str:
    text = value.lower()
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
        text = text.replace(src, dst)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:90] or "tin-dang"


def _fold_text(value: str) -> str:
    text = (value or "").lower()
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
        text = text.replace(src, dst)
    return re.sub(r"\s+", " ", text).strip()


class BatDongSanApiSource:
    name = "batdongsan"
    base_url = "https://apimap.batdongsan.com.vn"
    page_size = 20

    def build_search_url(self, city: str, page: int, *, incremental: bool) -> str:
        return f"{self.base_url}/api/p_sync?page={page}&cate=0&ptype=49"

    def fetch_search_text(self, city: str, page: int, *, incremental: bool) -> str:
        payload = {
            "ptype": "49",
            "cate": "0",
            "city": self._city_code(city),
            "dist": "0",
            "maxarea": "0",
            "minarea": "0",
            "maxprice": "0",
            "minprice": "0",
            "ward": "-1",
            "street": "-1",
            "room": "-1",
            "direct": "-1",
            "projectid": "-1",
            "sort": "0",
            "page": str(page),
            "searchType": "0",
            "client": "android",
            "m": "list",
            "pagesize": str(self.page_size),
        }
        body = urlencode(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}/api/p_sync",
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "http://batdongsan.com.vn",
                "Accept": "application/json",
                "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 10; Pixel Build/QP1A)",
                "Host": "apimap.batdongsan.com.vn",
                "Connection": "Keep-Alive",
                "Accept-Encoding": "gzip",
                "Content-Length": str(len(body)),
            },
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            raw = response.read()
            if response.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            raw_text = raw.decode("ascii", errors="ignore")
        return self._decode_payload(raw_text)

    def parse_search(self, html: str) -> list[str]:
        payload = json.loads(html)
        return [self._canonical_url(item) for item in payload.get("data", []) if isinstance(item, dict)]

    def parse_search_payloads(self, html: str, *, max_items: int | None = None) -> list[dict]:
        payload = json.loads(html)
        items = [item for item in payload.get("data", []) if isinstance(item, dict)]
        if max_items is not None:
            items = items[:max_items]
        return [_record_to_payload(self._item_to_record(item), self) for item in items]

    def parse_detail(self, html: str, url: str) -> ListingRecord:
        payload = json.loads(html)
        items = [item for item in payload.get("data", []) if isinstance(item, dict)]
        if not items:
            raise ValueError(f"BatDongSan API response has no listings for {url}")
        return self._item_to_record(items[0])

    def build_content_hash(self, listing: ListingRecord) -> str:
        parts = [
            listing.source_name,
            listing.source_post_id,
            listing.title,
            listing.price_text or "",
            listing.area_text or "",
            listing.full_address or "",
            listing.description or "",
            ",".join(listing.image_urls),
        ]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()

    def extract_last_page(self, html: str) -> int | None:
        return None

    def _item_to_record(self, item: dict) -> ListingRecord:
        source_post_id = str(item.get("id") or "")
        address = _clean_optional(item.get("address"))
        district, province = self._split_location(address)
        price_text = _clean_optional(item.get("price"))
        area_text = _clean_optional(item.get("area"))
        image_url = _clean_optional(item.get("avatar"))

        return ListingRecord(
            source_name=self.name,
            source_post_id=source_post_id or hashlib.md5(json.dumps(item, sort_keys=True).encode("utf-8")).hexdigest()[:12],
            canonical_url=self._canonical_url(item),
            title=_clean_optional(item.get("title")) or "Untitled listing",
            price_text=price_text,
            price_value=_parse_price(price_text),
            area_text=area_text,
            area_m2=_parse_area_text(area_text),
            full_address=address,
            district=district,
            province=province,
            latitude=_parse_float(str(item.get("lat"))) if item.get("lat") else None,
            longitude=_parse_float(str(item.get("lon"))) if item.get("lon") else None,
            description=_clean_optional(item.get("title")),
            image_count=1 if image_url else 0,
            posted_at=_parse_date_text(_clean_optional(item.get("date"))) or datetime.now(UTC),
            image_urls=[image_url] if image_url else [],
        )

    def _canonical_url(self, item: dict) -> str:
        post_id = str(item.get("id") or "")
        slug = _slugify(str(item.get("title") or "tin-dang"))
        return f"https://batdongsan.com.vn/cho-thue-nha-tro-phong-tro/{slug}-pr{post_id}"

    def _decode_payload(self, value: str) -> str:
        decoded = base64.b64decode(value)
        swapped = bytes(((byte & 0x0F) << 4) | (byte >> 4) for byte in decoded)
        return swapped.decode("latin1")

    def _city_code(self, city: str) -> str:
        normalized = city.strip().lower()
        if normalized in {"all", "nationwide", "toan-quoc", ""}:
            return ""
        aliases = {
            "ha-noi": "HN",
            "hanoi": "HN",
            "hn": "HN",
            "ho-chi-minh": "SG",
            "hcm": "SG",
            "tp-hcm": "SG",
            "sai-gon": "SG",
            "da-nang": "DDN",
            "binh-duong": "BD",
        }
        return aliases.get(normalized, city.upper())

    def _split_location(self, address: str | None) -> tuple[str | None, str | None]:
        if not address:
            return None, None
        parts = [part.strip() for part in re.split(r"\s+-\s+", address) if part.strip()]
        if len(parts) >= 2:
            return parts[0], parts[-1]
        return None, address
