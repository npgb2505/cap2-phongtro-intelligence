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
            self.assertEqual(manifest["dataset_version"], "2026-07-15T03:00:00+00:00")
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


if __name__ == "__main__":
    unittest.main()
