from __future__ import annotations

import unittest

from app.curation import (
    ExactGeocodeBudget,
    _extract_query_road,
    _geocode_district_label,
    _is_nominatim_result_acceptable,
    _median_reference_locations,
    _reference_precision,
)


class NominatimValidationTests(unittest.TestCase):
    def test_accepts_matching_house_number_and_road(self) -> None:
        item = {
            "lat": "10.781",
            "lon": "106.751",
            "category": "place",
            "addresstype": "house",
            "display_name": "219/9, Đường Nguyễn Thị Định, Thành phố Hồ Chí Minh, Việt Nam",
            "address": {
                "house_number": "219/9",
                "road": "Đường Nguyễn Thị Định",
                "city": "Thành phố Hồ Chí Minh",
            },
        }

        self.assertTrue(
            _is_nominatim_result_acceptable(
                item,
                "219/9 Đường Nguyễn Thị Định, Phường Bình Trưng, Quận 2, Hồ Chí Minh, Vietnam",
                "exact",
            )
        )

    def test_rejects_nearby_business_with_different_house_number(self) -> None:
        item = {
            "lat": "10.7976",
            "lon": "106.7446",
            "category": "shop",
            "addresstype": "shop",
            "display_name": "Epicure Vina, 121/20 Nguyễn Hoàng, Thành phố Hồ Chí Minh",
            "address": {
                "house_number": "121/20",
                "road": "Nguyễn Hoàng",
                "city": "Thành phố Hồ Chí Minh",
            },
        }

        self.assertFalse(
            _is_nominatim_result_acceptable(
                item,
                "219/9 Đường Nguyễn Thị Định, Phường Bình Trưng, Quận 2, Hồ Chí Minh, Vietnam",
                "exact",
            )
        )

    def test_accepts_matching_street_without_claiming_exact_house(self) -> None:
        item = {
            "lat": "10.781",
            "lon": "106.751",
            "category": "highway",
            "addresstype": "road",
            "display_name": "Đường Nguyễn Thị Định, Thành phố Thủ Đức, Hồ Chí Minh",
            "address": {
                "road": "Đường Nguyễn Thị Định",
                "city": "Thành phố Thủ Đức",
                "state": "Hồ Chí Minh",
            },
        }

        self.assertTrue(
            _is_nominatim_result_acceptable(
                item,
                "Đường Nguyễn Thị Định, Thành phố Thủ Đức, Hồ Chí Minh, Vietnam",
                "street",
            )
        )

    def test_rejects_different_street_result(self) -> None:
        item = {
            "lat": "10.781",
            "lon": "106.751",
            "category": "highway",
            "addresstype": "road",
            "display_name": "Đường Nguyễn Hoàng, Thành phố Thủ Đức, Hồ Chí Minh",
            "address": {
                "road": "Đường Nguyễn Hoàng",
                "city": "Thành phố Thủ Đức",
                "state": "Hồ Chí Minh",
            },
        }

        self.assertFalse(
            _is_nominatim_result_acceptable(
                item,
                "Đường Nguyễn Thị Định, Thành phố Thủ Đức, Hồ Chí Minh, Vietnam",
                "street",
            )
        )

    def test_rejects_business_as_district_result(self) -> None:
        item = {
            "lat": "10.7976",
            "lon": "106.7446",
            "category": "shop",
            "addresstype": "shop",
            "display_name": "Epicure Vina, Khu phố 2, Thành phố Hồ Chí Minh",
            "address": {"shop": "Epicure Vina", "city": "Thành phố Hồ Chí Minh"},
        }

        self.assertFalse(
            _is_nominatim_result_acceptable(item, "Quận 2, Hồ Chí Minh, Vietnam", "district")
        )

    def test_accepts_matching_administrative_district(self) -> None:
        item = {
            "lat": "10.787",
            "lon": "106.750",
            "category": "boundary",
            "addresstype": "administrative",
            "display_name": "Quận 2, Thành phố Hồ Chí Minh, Việt Nam",
            "address": {"city_district": "Quận 2", "city": "Thành phố Hồ Chí Minh"},
        }

        self.assertTrue(
            _is_nominatim_result_acceptable(item, "Quận 2, Hồ Chí Minh, Vietnam", "district")
        )

    def test_exact_budget_counts_unsuccessful_new_queries(self) -> None:
        budget = ExactGeocodeBudget(limit=2)
        budget.consume_if_new(was_cache_hit=False)
        budget.consume_if_new(was_cache_hit=False)
        self.assertFalse(budget.can_use())

    def test_extracts_road_after_comma_separated_house_number(self) -> None:
        self.assertEqual(
            _extract_query_road("248/52A, Đường Dương Quảng Hàm, Gò Vấp"),
            "Đường Dương Quảng Hàm",
        )

    def test_source_coordinate_is_only_street_precision(self) -> None:
        self.assertEqual(
            _reference_precision("219/9 Đường Nguyễn Thị Định", "Quận 2", "Hồ Chí Minh"),
            "street",
        )

    def test_legacy_district_uses_current_geocode_name(self) -> None:
        self.assertEqual(
            _geocode_district_label("Quận 2", "Hồ Chí Minh"),
            "Thành phố Thủ Đức",
        )
        self.assertEqual(
            _geocode_district_label("Thành Phố Thủ Đức", "Hồ Chí Minh"),
            "Thành phố Thủ Đức",
        )

    def test_reference_index_uses_median_without_random_jitter(self) -> None:
        references = _median_reference_locations(
            {
                "duong-nguyen-thi-dinh": [
                    (10.70, 106.70),
                    (10.72, 106.72),
                    (10.90, 106.90),
                ]
            },
            precision="street",
            source="source_street_index",
            minimum_samples=1,
        )

        reference = references["duong-nguyen-thi-dinh"]
        self.assertEqual(reference.latitude, 10.72)
        self.assertEqual(reference.longitude, 106.72)
        self.assertEqual(reference.precision, "street")


if __name__ == "__main__":
    unittest.main()
