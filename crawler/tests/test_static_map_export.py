from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from app.static_map_export import export_static_map
from app.static_snapshot_to_csv import static_snapshot_to_csv


class StaticMapExportTests(unittest.TestCase):
    def test_splits_lightweight_index_from_lazy_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "curated.csv"
            output = root / "data" / "listings-map.json"
            rows = [
                {
                    "listing_id": f"listing-{index}",
                    "source_name": "mogi",
                    "source_post_id": str(index),
                    "title_clean": f"Phòng số {index}",
                    "canonical_url": f"https://example.com/{index}",
                    "province": "Hà Nội",
                    "description_clean": "Mô tả dài chỉ tải khi mở chi tiết",
                    "contact_phone": "0987654321",
                    "status": "expired" if index == 2 else "active",
                }
                for index in range(3)
            ]
            with source.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            (source.parent / "curation_summary.json").write_text(json.dumps({
                "generated_at": "2026-07-15T03:00:00+00:00",
                "source_rows": 5,
                "duplicate_source_rows": 1,
                "skipped_low_quality_rows": 1,
                "duration_seconds": 12.5,
            }), encoding="utf-8")

            manifest = export_static_map(
                source_csv=source,
                output_json=output,
                chunk_size=2,
                detail_chunk_size=1,
            )

            self.assertEqual(manifest["dataset_mode"], "chunked-index-with-lazy-details")
            self.assertTrue(manifest["dataset_version"])
            self.assertEqual(len(manifest["chunks"]), 2)
            self.assertEqual(manifest["etl_summary"]["source_rows"], 5)
            self.assertEqual(manifest["etl_summary"]["published_rows"], 3)
            self.assertEqual(manifest["etl_runs"][0]["date"], "2026-07-15")
            index_payload = json.loads((output.parent / manifest["chunks"][0]).read_text(encoding="utf-8"))
            first = index_payload["items"][0]
            self.assertNotIn("description_clean", first)
            self.assertNotIn("contact_phone", first)
            self.assertIn("detail_path", first)

            detail_payload = json.loads((output.parent / first["detail_path"]).read_text(encoding="utf-8"))
            detail = detail_payload["items"][0]
            self.assertEqual(detail["description_clean"], "Mô tả dài chỉ tải khi mở chi tiết")
            self.assertEqual(detail["contact_phone"], "0987654321")
            self.assertNotIn("content_hash", detail)

            rebuilt_csv = root / "rebuilt.csv"
            conversion = static_snapshot_to_csv(output, rebuilt_csv)
            self.assertEqual(conversion["rows"], 3)
            with rebuilt_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                rebuilt = list(csv.DictReader(handle))
            self.assertEqual(rebuilt[2]["status"], "expired")
            self.assertEqual(rebuilt[0]["description_clean"], "Mô tả dài chỉ tải khi mở chi tiết")
            self.assertEqual(len(rebuilt[0]["content_hash"]), 64)

    def test_quality_gate_allows_missing_images_and_keeps_best_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "curated.csv"
            output = root / "data" / "listings-map.json"
            base = {
                "source_name": "phongtro123",
                "title_clean": "Phòng trọ đầy đủ tiện nghi",
                "price_value": "3500000",
                "area_m2": "25",
                "street_address": "123 Nguyễn Trãi",
                "district": "Quận 1",
                "province": "Hồ Chí Minh",
                "description_clean": "Mô tả đầy đủ về phòng, tiện ích và điều kiện thuê. " * 3,
                "canonical_url": "https://example.com/listing",
                "primary_image_url": "https://cdn.example.com/room.jpg",
                "image_count": "4",
                "record_completeness_score": "100",
                "amenity_count": "4",
                "geocode_precision": "exact",
            }
            rows = [
                {
                    **base,
                    "listing_id": "active-direct",
                    "status": "active",
                    "contact_phone": "0901234567",
                    "contact_name": "Nguyễn An",
                },
                {
                    **base,
                    "listing_id": "active-name",
                    "status": "active",
                    "contact_phone": "",
                    "contact_name": "Nhà Đẹp",
                },
                {
                    **base,
                    "listing_id": "placeholder",
                    "status": "active",
                    "contact_phone": "0909999999",
                    "contact_name": "Lê Bình",
                    "primary_image_url": "https://phongtro123.com/images/thumb_default.svg",
                },
            ]
            with source.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)

            manifest = export_static_map(
                source_csv=source,
                output_json=output,
                chunk_size=2,
                detail_chunk_size=1,
                quality_only=True,
                max_rows=1,
            )

            self.assertEqual(manifest["total"], 1)
            self.assertEqual(manifest["quality_summary"]["qualified_rows"], 3)
            self.assertEqual(manifest["quality_summary"]["rejected_low_quality_rows"], 0)
            self.assertEqual(manifest["quality_summary"]["trimmed_rows"], 2)
            self.assertEqual(manifest["items"][0]["id"], "active-direct")
            self.assertTrue(manifest["items"][0]["has_direct_contact"])


if __name__ == "__main__":
    unittest.main()
