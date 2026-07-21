import hashlib
import json
import re
from datetime import UTC, datetime
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from bs4 import BeautifulSoup

from app.models import ListingRecord


class Phongtro123Extractor:
    def parse_search(self, html: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        urls: list[str] = []
        for link in soup.select("a[href]"):
            href = link.get("href", "")
            if href.endswith(".html") and (re.search(r"pr\d+\.html$", href) or "/tinh-thanh/" in href):
                urls.append(urljoin(base_url, href))
        return sorted(set(urls))

    def extract_last_page(self, html: str) -> int | None:
        matches = re.findall(r"[?&]page=(\d+)", html)
        if not matches:
            return None
        return max(int(value) for value in matches)

    def parse_detail(self, html: str, url: str) -> ListingRecord:
        soup = BeautifulSoup(html, "html.parser")
        all_text = soup.get_text(" ", strip=True)
        table_rows = self._extract_table_rows(soup)
        json_ld = self._extract_json_ld(soup)

        title = self._text(soup.select_one("h1")) or "Untitled listing"
        source_post_id = self._extract_post_id(url, html)
        price_text = self._find_text_like(all_text, r"(\d+[.,]?\d*\s*triệu/tháng)")
        area_text = self._extract_area_text(all_text)

        amenities = self._extract_amenities(soup)
        image_urls = self._extract_image_urls(soup, json_ld)

        contact_phone = self._extract_phone(soup, html)
        # Page-wide Zalo links include Phongtro123's own support hotline. Only
        # accept a link from the listing contact block and validate it below.
        contact_zalo_url = self._validated_zalo_url(
            self._extract_contact_href(soup, "zalo.me"),
            contact_phone,
        )
        contact_facebook_url = self._extract_contact_href(soup, "facebook.com")
        full_address = table_rows.get("Địa chỉ") or table_rows.get("Dia chi") or self._extract_address_from_map(soup)
        province = self._normalize_region_name(table_rows.get("Tỉnh thành") or table_rows.get("Tinh thanh"))
        district = self._normalize_region_name(table_rows.get("Quận huyện") or table_rows.get("Quan huyen"))
        street_address, ward, normalized_district, normalized_province = self._split_address_parts(full_address, district, province)
        contact_name = self._extract_contact_name(soup, json_ld)
        description = self._extract_description(soup)
        posted_at = self._parse_datetime(table_rows.get("Ngày đăng") or table_rows.get("Ngay dang"))
        expired_at = self._parse_datetime(table_rows.get("Ngày hết hạn") or table_rows.get("Ngay het han"))

        return ListingRecord(
            source_name="phongtro123",
            source_post_id=source_post_id,
            canonical_url=self._attr(soup.select_one('link[rel="canonical"]'), "href") or url,
            title=title,
            price_text=price_text,
            price_value=self._parse_price(price_text),
            area_text=area_text,
            area_m2=self._parse_area(area_text),
            full_address=full_address,
            street_address=street_address,
            ward=ward,
            district=normalized_district,
            province=normalized_province,
            description=description,
            amenities=sorted(set(amenities))[:20],
            image_urls=sorted(set(image_urls)),
            contact_name=contact_name,
            contact_phone=contact_phone,
            contact_zalo_url=contact_zalo_url,
            contact_facebook_url=contact_facebook_url,
            image_count=len(sorted(set(image_urls))),
            posted_at=posted_at or datetime.now(UTC),
            expired_at=expired_at,
        )

    def build_content_hash(self, listing: ListingRecord) -> str:
        parts = [
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

    def _extract_post_id(self, url: str, html: str) -> str:
        match = re.search(r"pr(\d+)\.html", url) or re.search(r"#(\d{4,})", html)
        if match:
            return match.group(1)
        return hashlib.md5(url.encode("utf-8")).hexdigest()[:12]

    def _extract_phone(self, soup: BeautifulSoup, html: str) -> str | None:
        tel_links = [
            link.get("href", "").replace("tel:", "").replace(" ", "").strip()
            for link in soup.select('a[href^="tel:"]')
        ]
        for candidate in tel_links:
            if re.fullmatch(r"0\d{9,10}", candidate) and candidate != "0909316890":
                return candidate
        for candidate in re.findall(r"0\d{9,10}", html):
            if candidate != "0909316890":
                return candidate
        return None

    def _extract_contact_name(self, soup: BeautifulSoup, json_ld: list[dict]) -> str | None:
        for item in json_ld:
            author = item.get("author")
            if isinstance(author, dict) and author.get("name"):
                return str(author["name"]).strip()
        contact_heading = soup.find(lambda tag: tag.name in {"h2", "h3"} and "Thông tin liên hệ" in tag.get_text(" ", strip=True))
        if contact_heading:
            for sibling in contact_heading.find_all_next(limit=10):
                text = sibling.get_text(" ", strip=True)
                if text and "Đang hoạt động" not in text and not re.search(r"0\d{9,10}", text):
                    return text
        return None

    def _extract_description(self, soup: BeautifulSoup) -> str | None:
        description_heading = soup.find(lambda tag: tag.name in {"h2", "h3"} and "Thông tin mô tả" in tag.get_text(" ", strip=True))
        if not description_heading:
            paragraphs = [node.get_text(" ", strip=True) for node in soup.select("p")[:10]]
            return "\n".join([value for value in paragraphs if value]) or None

        values: list[str] = []
        for sibling in description_heading.find_all_next():
            if sibling.name in {"h1", "h2"} and sibling is not description_heading:
                break
            if sibling.name == "p":
                text = sibling.get_text(" ", strip=True)
                if text:
                    values.append(text)
        return "\n".join(values) or None

    def _extract_area_text(self, text: str) -> str | None:
        matches = re.finditer(r"(\d+(?:[.,]\d+)?)\s*m(?:\s*2|\s*²)", text, flags=re.IGNORECASE)
        for match in matches:
            value = match.group(1)
            numeric = float(value.replace(",", "."))
            if 5 <= numeric <= 500:
                return f"{value} m2"
        return None

    def _extract_amenities(self, soup: BeautifulSoup) -> list[str]:
        heading = soup.find(lambda tag: tag.name in {"h2", "h3"} and "Nổi bật" in tag.get_text(" ", strip=True))
        if not heading:
            return []

        values: list[str] = []
        for sibling in heading.find_all_next():
            if sibling.name in {"h1", "h2"} and sibling is not heading:
                break
            text = sibling.get_text(" ", strip=True)
            if text and len(text) < 40:
                values.append(text)
        return values

    def _extract_image_urls(self, soup: BeautifulSoup, json_ld: list[dict]) -> list[str]:
        image_urls: list[str] = []
        for meta in soup.select('meta[property="og:image"]'):
            value = meta.get("content", "").strip()
            if value:
                image_urls.append(value)

        for item in json_ld:
            image_value = item.get("image")
            if isinstance(image_value, str):
                image_urls.append(image_value)

        if not image_urls:
            image_urls.extend(
                [
                    img.get("src", "")
                    for img in soup.select("img[src]")
                    if "static123.com" in img.get("src", "")
                ][:10]
            )
        return sorted(set(image_urls))

    def _extract_table_rows(self, soup: BeautifulSoup) -> dict[str, str]:
        rows: dict[str, str] = {}
        for row in soup.select("table tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                key = cells[0].get_text(" ", strip=True).rstrip(":")
                value = cells[1].get_text(" ", strip=True)
                if key and value:
                    rows[key] = value
        return rows

    def _extract_json_ld(self, soup: BeautifulSoup) -> list[dict]:
        items: list[dict] = []
        for node in soup.select('script[type="application/ld+json"]'):
            raw = node.string or node.get_text(strip=True)
            if not raw:
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                items.append(value)
            elif isinstance(value, list):
                items.extend([item for item in value if isinstance(item, dict)])
        return items

    def _extract_first_href(self, soup: BeautifulSoup, needle: str) -> str | None:
        link = soup.find("a", href=lambda href: href and needle in href)
        return link.get("href") if link else None

    def _validated_zalo_url(self, value: str | None, contact_phone: str | None) -> str | None:
        if not value:
            return None
        match = re.search(r"zalo\.me/(?:pc\?|share/)?(?:phone=)?(0\d{9,10})", value, flags=re.IGNORECASE)
        if not match:
            return None
        zalo_phone = match.group(1)
        if zalo_phone == "0909316890":
            return None
        if contact_phone and zalo_phone != contact_phone:
            return None
        return value

    def _extract_contact_href(self, soup: BeautifulSoup, needle: str) -> str | None:
        contact_heading = soup.find(lambda tag: tag.name in {"h2", "h3"} and "Thông tin liên hệ" in tag.get_text(" ", strip=True))
        if not contact_heading:
            return None
        for sibling in contact_heading.find_all_next(limit=20):
            href_tag = sibling if getattr(sibling, "name", None) == "a" else sibling.find("a", href=True)
            if href_tag and needle in href_tag.get("href", ""):
                return href_tag.get("href")
        return None

    def _extract_address_from_map(self, soup: BeautifulSoup) -> str | None:
        iframe = soup.find("iframe", src=lambda src: src and "google.com/maps/embed" in src)
        if not iframe:
            return None
        query = parse_qs(urlparse(iframe.get("src", "")).query)
        values = query.get("q")
        return unquote(values[0]) if values else None

    def _split_address_parts(
        self,
        full_address: str | None,
        district: str | None,
        province: str | None,
    ) -> tuple[str | None, str | None, str | None, str | None]:
        if not full_address:
            return None, None, district, province

        parts = [part.strip() for part in full_address.split(",") if part.strip()]
        street_address = parts[0] if parts else full_address.strip()
        ward = None
        normalized_district = district
        normalized_province = province

        for part in parts[1:]:
            lowered = part.lower()
            if ward is None and any(token in lowered for token in ["phường", "xa ", "xã ", "thị trấn", "thị xã"]):
                ward = part
                continue
            if normalized_district is None and any(token in lowered for token in ["quận", "huyện", "thành phố", "tp."]):
                normalized_district = part
                continue
            if normalized_province is None:
                normalized_province = part

        return street_address, ward, normalized_district, normalized_province

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        match = re.search(r"(\d{2})/(\d{2})/(\d{4})", value)
        if not match:
            return None
        date_part = f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
        time_match = re.search(r"(\d{2}):(\d{2})", value)
        time_part = f"{time_match.group(1)}:{time_match.group(2)}:00" if time_match else "00:00:00"
        return datetime.fromisoformat(f"{date_part}T{time_part}+07:00")

    def _normalize_region_name(self, value: str | None) -> str | None:
        if not value:
            return None
        return re.sub(r"^Cho thuê phòng trọ\s+", "", value).strip()

    def _attr(self, node, name: str) -> str | None:
        return node.get(name) if node else None

    def _parse_price(self, value: str | None) -> int | None:
        if not value:
            return None
        match = re.search(r"(\d+[.,]?\d*)", value)
        if not match:
            return None
        normalized = float(match.group(1).replace(",", "."))
        if "triệu" in value:
            return int(normalized * 1_000_000)
        if "k" in value.lower():
            return int(normalized * 1_000)
        return int(normalized)

    def _parse_area(self, value: str | None) -> float | None:
        if not value:
            return None
        match = re.search(r"(\d+[.,]?\d*)", value)
        return float(match.group(1).replace(",", ".")) if match else None

    def _text(self, node) -> str | None:
        return node.get_text(" ", strip=True) if node else None

    def _find_text_like(self, text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        return match.group(1) if match else None
