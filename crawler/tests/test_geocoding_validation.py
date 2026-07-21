from __future__ import annotations

import unittest

from app.curation import ExactGeocodeBudget, _is_nominatim_result_acceptable


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


if __name__ == "__main__":
    unittest.main()
