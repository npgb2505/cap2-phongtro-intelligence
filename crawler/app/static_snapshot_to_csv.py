from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from app.curation import CURATED_COLUMNS

BOOLEAN_COLUMNS = (
    "is_reference_coordinate",
    "has_aircon",
    "has_private_wc",
    "has_loft",
    "has_parking",
    "has_security",
    "has_fingerprint_lock",
    "allows_free_hours",
    "has_balcony",
    "has_kitchen",
    "has_fridge",
    "has_washer",
)


def _read_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(base: Path, value: str) -> Path:
    return Path(value) if Path(value).is_absolute() else base / value


def _content_hash(item: dict[str, Any]) -> str:
    seed = "|".join([
        str(item.get("canonical_url") or ""),
        str(item.get("source_name") or ""),
        str(item.get("source_post_id") or ""),
        str(item.get("id") or ""),
    ])
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _csv_value(value: Any) -> Any:
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _amenity_count(item: dict[str, Any]) -> int:
    existing = item.get("amenity_count")
    if existing not in (None, ""):
        return int(existing)
    text = str(item.get("amenities_text") or "").strip()
    if text:
        return len([part for part in text.split("|") if part.strip()])
    return sum(_as_bool(item.get(column)) for column in BOOLEAN_COLUMNS if column != "is_reference_coordinate")


def static_snapshot_to_csv(manifest_path: Path, output_csv: Path) -> dict[str, object]:
    manifest = _read_payload(manifest_path)
    base = manifest_path.parent
    items: list[dict[str, Any]] = list(manifest.get("items") or [])
    for chunk_path in manifest.get("chunks") or []:
        items.extend(_read_payload(_resolve(base, str(chunk_path))).get("items") or [])

    details: dict[str, dict[str, Any]] = {}
    detail_paths = sorted({str(item.get("detail_path")) for item in items if item.get("detail_path")})
    for detail_path in detail_paths:
        payload = _read_payload(_resolve(base, detail_path))
        for detail in payload.get("items") or []:
            detail_id = str(detail.get("id") or "")
            if detail_id:
                details[detail_id] = detail

    rows: list[dict[str, Any]] = []
    for index_item in items:
        listing_id = str(index_item.get("id") or "")
        merged = {**index_item, **details.get(listing_id, {})}
        merged["listing_id"] = listing_id
        merged["source_name"] = merged.get("source_name") or "unknown"
        merged["source_post_id"] = merged.get("source_post_id") or listing_id
        merged["title_clean"] = merged.get("title") or "Tin phòng trọ"
        merged["title"] = merged.get("title_raw") or merged["title_clean"]
        merged["image_count"] = merged.get("image_count") or 0
        merged["amenity_count"] = _amenity_count(merged)
        for column in BOOLEAN_COLUMNS:
            merged[column] = _as_bool(merged.get(column))
        merged["content_hash"] = _content_hash(merged)
        rows.append({column: _csv_value(merged.get(column)) for column in CURATED_COLUMNS})

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CURATED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "manifest": str(manifest_path),
        "output_csv": str(output_csv),
        "rows": len(rows),
        "detail_chunks": len(detail_paths),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild a loadable curated CSV from the tracked static snapshot")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    result = static_snapshot_to_csv(args.manifest, args.output_csv)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
