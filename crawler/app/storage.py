import csv
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any


class LocalArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def write_json(self, relative_path: str, payload: Any) -> str:
        target = self.root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=self._json_default), encoding="utf-8")
        return str(target)

    def write_text(self, relative_path: str, content: str) -> str:
        target = self.root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target)

    def write_csv(self, relative_path: str, rows: list[dict[str, Any]], fieldnames: list[str]) -> str:
        target = self.root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        return str(target)

    def _json_default(self, value: object) -> str:
        if isinstance(value, datetime | date):
            return value.isoformat()
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
