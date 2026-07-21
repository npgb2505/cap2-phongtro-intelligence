from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.pipelines.source_backfill import _next_existing_page
from app.sources import DEFAULT_SOURCE_NAMES, build_sources


class SourceBackfillTests(unittest.TestCase):
    def test_default_sources_exclude_low_yield_adapters(self) -> None:
        self.assertEqual(DEFAULT_SOURCE_NAMES, ["phongtro123", "nhatot", "mogi"])
        self.assertEqual([source.name for source in build_sources()], DEFAULT_SOURCE_NAMES)

    def test_resume_starts_after_highest_source_page(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            page_dir = Path(temp_dir) / "tabular" / "mogi" / "toan-quoc"
            page_dir.mkdir(parents=True)
            (page_dir / "page_2.csv").touch()
            (page_dir / "page_17.csv").touch()
            (page_dir / "incremental_page_99.csv").touch()

            self.assertEqual(_next_existing_page(Path(temp_dir), "mogi", "toan-quoc"), 18)


if __name__ == "__main__":
    unittest.main()
