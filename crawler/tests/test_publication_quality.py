from __future__ import annotations

import unittest

from app.publication_quality import (
    evaluate_publication_quality,
    is_contact_name,
    publication_sort_key,
)


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

    def test_placeholder_image_is_allowed_but_scores_lower(self) -> None:
        row = complete_row()
        row["primary_image_url"] = "https://phongtro123.com/images/thumb_default.svg"

        assessment = evaluate_publication_quality(row)

        self.assertTrue(assessment.publishable)
        self.assertFalse(assessment.has_real_image)
        self.assertLess(assessment.score, evaluate_publication_quality(complete_row()).score)

    def test_listing_without_contact_is_allowed_when_other_content_is_useful(self) -> None:
        row = complete_row()
        row["contact_phone"] = ""
        row["contact_name"] = ""

        assessment = evaluate_publication_quality(row)

        self.assertTrue(assessment.publishable)
        self.assertFalse(assessment.has_direct_contact)

    def test_listing_without_any_useful_content_is_rejected(self) -> None:
        row = complete_row()
        row["contact_phone"] = ""
        row["contact_name"] = ""
        row["description_clean"] = ""
        row["primary_image_url"] = ""
        row["image_count"] = "0"

        assessment = evaluate_publication_quality(row)

        self.assertFalse(assessment.publishable)

    def test_listing_with_image_and_contact_ranks_before_missing_image(self) -> None:
        complete = complete_row()
        missing_image = complete_row()
        missing_image["primary_image_url"] = ""
        missing_image["image_count"] = "0"

        self.assertGreater(
            publication_sort_key(complete, evaluate_publication_quality(complete)),
            publication_sort_key(missing_image, evaluate_publication_quality(missing_image)),
        )

    def test_location_is_not_treated_as_contact_name(self) -> None:
        self.assertFalse(is_contact_name("huyện Bình Chánh"))
        self.assertFalse(is_contact_name("Phường Tân Bình"))
        self.assertTrue(is_contact_name("Cộng Đồng Nhà Đất"))


if __name__ == "__main__":
    unittest.main()
