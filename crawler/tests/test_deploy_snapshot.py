from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from app.deploy_snapshot import build_deploy_snapshot


def row(source: str, index: int, score: int) -> dict[str, str]:
    return {
        "listing_id": f"{source}-{index}",
        "source_name": source,
        "title_clean": f"Phòng trọ chất lượng số {index}",
        "canonical_url": f"https://example.com/{source}/{index}",
        "price_value": "3500000",
        "area_m2": "25",
        "district": "Quận 1",
        "province": "Hồ Chí Minh",
        "full_address": "Quận 1, Hồ Chí Minh",
        "primary_image_url": "https://cdn.example.com/room.jpg",
        "image_count": "1",
        "record_completeness_score": str(score),
        "status": "active",
    }


class DeploySnapshotTests(unittest.TestCase):
    def test_balances_sources_and_redistributes_shortfall(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_csv = root / "curated.csv"
            output_csv = root / "deploy" / "listings_deploy.csv"
            summary_json = output_csv.with_name("deploy_snapshot_summary.json")
            rows = [
                *[row("phongtro123", index, 80 + index) for index in range(5)],
                row("nhatot", 0, 95),
                *[row("mogi", index, 70 + index) for index in range(5)],
            ]
            with source_csv.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)

            summary = build_deploy_snapshot(
                source_csv=source_csv,
                output_csv=output_csv,
                summary_json=summary_json,
                total_rows=6,
            )

            self.assertEqual(summary["total_rows"], 6)
            self.assertEqual(summary["source_counts"], {"phongtro123": 3, "nhatot": 1, "mogi": 2})
            self.assertEqual(summary["selection_strategy"], "balanced-quality-ranked")
            self.assertEqual(json.loads(summary_json.read_text(encoding="utf-8"))["target_rows"], 6)


if __name__ == "__main__":
    unittest.main()
