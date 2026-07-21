from __future__ import annotations

import unittest

from app.publication_quality import evaluate_publication_quality, is_contact_name


def complete_row() -> dict[str, str]:
    return {
        "title_clean": "Phòng trọ đầy đủ tiện nghi",
        "status": "active",
        "price_value": "3500000",
        "area_m2": "25",
        "street_address": "123 Nguyễn Trãi",
        "district": "Quận 1",
        "province": "Hồ Chí Minh",
        "description_clean": "Mô tả phòng đầy đủ tiện nghi, an ninh, giờ giấc tự do và thuận tiện đi lại. " * 2,
        "canonical_url": "https://example.com/listing-1",
        "primary_image_url": "https://cdn.example.com/room.jpg",
        "image_count": "5",
        "contact_phone": "0901234567",
        "contact_name": "Nguyễn An",
        "amenity_count": "4",
        "geocode_precision": "exact",
        "freshness_days": "2",
    }


class PublicationQualityTests(unittest.TestCase):
    def test_complete_listing_is_publishable(self) -> None:
        assessment = evaluate_publication_quality(complete_row())

        self.assertTrue(assessment.publishable)
        self.assertTrue(assessment.has_real_image)
        self.assertTrue(assessment.has_direct_contact)
        self.assertGreaterEqual(assessment.score, 90)

    def test_placeholder_image_is_rejected(self) -> None:
        row = complete_row()
        row["primary_image_url"] = "https://phongtro123.com/images/thumb_default.svg"

        assessment = evaluate_publication_quality(row)

        self.assertFalse(assessment.publishable)
        self.assertFalse(assessment.has_real_image)

    def test_listing_without_contact_is_rejected(self) -> None:
        row = complete_row()
        row["contact_phone"] = ""
        row["contact_name"] = ""

        assessment = evaluate_publication_quality(row)

        self.assertFalse(assessment.publishable)

    def test_location_is_not_treated_as_contact_name(self) -> None:
        self.assertFalse(is_contact_name("huyện Bình Chánh"))
        self.assertFalse(is_contact_name("Phường Tân Bình"))
        self.assertTrue(is_contact_name("Cộng Đồng Nhà Đất"))


if __name__ == "__main__":
    unittest.main()
