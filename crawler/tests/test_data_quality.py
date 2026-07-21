from __future__ import annotations

import unittest

from bs4 import BeautifulSoup

from app.curation import (
    _is_curatable_source_row,
    _clean_multiline_text,
    _normalize_province,
    _source_row_key,
    normalize_contact_name,
    normalize_phone,
    normalize_zalo_url,
)
from app.extractors.phongtro123 import Phongtro123Extractor


class ProvinceNormalizationTests(unittest.TestCase):
    def test_accepts_only_canonical_province_values(self) -> None:
        self.assertEqual(_normalize_province("TP. Hồ Chí Minh"), "Hồ Chí Minh")
        self.assertEqual(_normalize_province("Thừa Thiên Huế"), "Huế")
        self.assertEqual(_normalize_province("Bà Rịa, Vũng Tàu"), "Bà Rịa - Vũng Tàu")

    def test_rejects_description_fragments_as_provinces(self) -> None:
        self.assertIsNone(_normalize_province("Full Như Ảnh. Dịch Vụ: Điện"))
        self.assertIsNone(_normalize_province("Máy Giặt"))
        self.assertIsNone(_normalize_province("Hà Nội đường Nguyễn Trãi giá 4 triệu"))

    def test_source_key_normalizes_duplicate_urls(self) -> None:
        first = {"canonical_url": "https://example.com/listing/"}
        second = {"canonical_url": "https://example.com/listing"}
        self.assertEqual(_source_row_key(first), _source_row_key(second))


class ContactNormalizationTests(unittest.TestCase):
    def test_removes_conflict_like_separators_from_descriptions(self) -> None:
        self.assertEqual(_clean_multiline_text("Dòng một\n=======\nDòng hai"), "Dòng một\nDòng hai")

    def test_rejects_short_or_shifted_phone_values(self) -> None:
        self.assertIsNone(normalize_phone("1"))
        self.assertIsNone(normalize_phone("2021-05-13T09:31:00+07:00"))

    def test_rejects_description_fragments_as_contact_names(self) -> None:
        self.assertIsNone(normalize_contact_name("Nội Thất Đầy Đủ"))
        self.assertIsNone(normalize_contact_name("9 TRIỆU - CC CAO CẤP"))
        self.assertEqual(normalize_contact_name("Kim Anh"), "Kim Anh")

    def test_rejects_shifted_source_rows(self) -> None:
        self.assertFalse(_is_curatable_source_row({
            "source_name": "phongtro123",
            "title": "PHÒNG CAO CẤP phongtro123,586294,https://phongtro123.com/x",
            "canonical_url": "https://phongtro123.com/x",
        }))

    def test_rejects_nhatot_room_wanted_posts(self) -> None:
        self.assertFalse(_is_curatable_source_row({
            "source_name": "nhatot",
            "title": "Cần tìm ptro riêng chủ",
            "canonical_url": "https://www.nhatot.com/can-tim-phong-123.htm",
        }))
        self.assertTrue(_is_curatable_source_row({
            "source_name": "nhatot",
            "title": "Cần tìm nữ ở ghép phòng đầy đủ nội thất",
            "canonical_url": "https://www.nhatot.com/tim-nguoi-o-ghep-456.htm",
        }))
        self.assertFalse(_is_curatable_source_row({
            "source_name": "Địa chỉ: Quận Thủ Đức",
            "title": "Phòng trọ hợp lệ",
            "canonical_url": "https://example.com/x",
        }))

    def test_rejects_site_hotline_and_mismatched_zalo(self) -> None:
        self.assertIsNone(normalize_zalo_url("https://zalo.me/0909316890", "0987654321"))
        self.assertIsNone(normalize_zalo_url("https://zalo.me/0911111111", "0987654321"))

    def test_accepts_zalo_matching_the_listing_phone(self) -> None:
        url = "https://zalo.me/0987654321"
        self.assertEqual(normalize_zalo_url(url, "0987654321"), url)
        self.assertEqual(
            Phongtro123Extractor._validated_zalo_url(None, url, "0987654321"),
            url,
        )

    def test_phone_fallback_skips_the_source_site_hotline(self) -> None:
        soup = BeautifulSoup("<html></html>", "html.parser")
        html = "Hotline 0909316890 - lien he nguoi dang 0987654321"
        self.assertEqual(
            Phongtro123Extractor._extract_phone(None, soup, html),
            "0987654321",
        )


if __name__ == "__main__":
    unittest.main()
