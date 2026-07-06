from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.storage import LocalArtifactStore

TABLE_COLUMNS = [
    "source_name",
    "source_post_id",
    "canonical_url",
    "title",
    "price_text",
    "price_value",
    "area_text",
    "area_m2",
    "street_address",
    "ward",
    "district",
    "province",
    "full_address",
    "latitude",
    "longitude",
    "description",
    "contact_name",
    "contact_phone",
    "contact_zalo_url",
    "contact_facebook_url",
    "image_count",
    "amenities_text",
    "image_urls_text",
    "posted_at",
    "expired_at",
    "content_hash",
]

BAD_TITLE_MARKERS = [
    "vui lòng xác minh không phải robot",
    "vui long xac minh khong phai robot",
    "captcha",
    "access denied",
]


def export_rows_to_csv(
    *,
    store: LocalArtifactStore,
    relative_path: str,
    rows: list[dict[str, Any]],
) -> str:
    flattened_rows = [_flatten_row(row) for row in rows]
    flattened_rows = [row for row in flattened_rows if _is_valid_listing_row(row)]
    return store.write_csv(relative_path, flattened_rows, TABLE_COLUMNS)


def upsert_rows_to_csv(
    *,
    store: LocalArtifactStore,
    relative_path: str,
    rows: list[dict[str, Any]],
) -> str:
    target = store.root / relative_path
    existing_by_key: dict[str, dict[str, Any]] = {}

    if target.exists():
        with target.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                row = _normalize_table_row(row)
                key = _row_key(row)
                if key:
                    existing_by_key[key] = row

    for row in rows:
        flattened = _flatten_row(row)
        if not _is_valid_listing_row(flattened):
            continue
        key = _row_key(flattened)
        if key:
            existing_by_key[key] = flattened

    merged_rows = sorted(
        existing_by_key.values(),
        key=lambda row: (row.get("posted_at") or "", row.get("source_post_id") or ""),
        reverse=True,
    )
    return store.write_csv(relative_path, merged_rows, TABLE_COLUMNS)


def _flatten_row(row: dict[str, Any]) -> dict[str, Any]:
    output = dict(row)
    output["source_name"] = output.get("source_name") or _infer_source_name(output.get("canonical_url"))
    output["amenities_text"] = " | ".join(row.get("amenities", []))
    output["image_urls_text"] = " | ".join(row.get("image_urls", []))
    output["posted_at"] = _to_text(row.get("posted_at"))
    output["expired_at"] = _to_text(row.get("expired_at"))
    return output


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime | date):
        return value.isoformat()
    return str(value)


def _row_key(row: dict[str, Any]) -> str:
    source_name = str(row.get("source_name") or _infer_source_name(row.get("canonical_url"))).strip()
    source_post_id = str(row.get("source_post_id") or "").strip()
    canonical_url = str(row.get("canonical_url") or "").strip()
    if source_post_id:
        return f"{source_name}:{source_post_id}"
    return canonical_url


def _normalize_table_row(row: dict[str, Any]) -> dict[str, Any]:
    output = dict(row)
    output["source_name"] = output.get("source_name") or _infer_source_name(output.get("canonical_url"))
    return output


def _infer_source_name(canonical_url: Any) -> str:
    value = str(canonical_url or "").lower()
    if "phongtro123.com" in value:
        return "phongtro123"
    if "alonhadat.com.vn" in value:
        return "alonhadat"
    if "thuephongtro.com" in value:
        return "thuephongtro"
    if "nhatot.com" in value:
        return "nhatot"
    if "batdongsan.com.vn" in value:
        return "batdongsan"
    return "unknown"


def _is_valid_listing_row(row: dict[str, Any]) -> bool:
    title = str(row.get("title") or "").strip()
    canonical_url = str(row.get("canonical_url") or "").strip()
    if not title or not canonical_url:
        return False

    folded_title = _fold_text(title)
    return not any(marker in folded_title for marker in BAD_TITLE_MARKERS)


def _fold_text(value: str) -> str:
    text = value.lower()
    replacements = {
        "à": "a", "á": "a", "ạ": "a", "ả": "a", "ã": "a", "ă": "a", "ằ": "a", "ắ": "a", "ặ": "a", "ẳ": "a", "ẵ": "a",
        "â": "a", "ầ": "a", "ấ": "a", "ậ": "a", "ẩ": "a", "ẫ": "a", "đ": "d",
        "è": "e", "é": "e", "ẹ": "e", "ẻ": "e", "ẽ": "e", "ê": "e", "ề": "e", "ế": "e", "ệ": "e", "ể": "e", "ễ": "e",
        "ì": "i", "í": "i", "ị": "i", "ỉ": "i", "ĩ": "i",
        "ò": "o", "ó": "o", "ọ": "o", "ỏ": "o", "õ": "o", "ô": "o", "ồ": "o", "ố": "o", "ộ": "o", "ổ": "o", "ỗ": "o",
        "ơ": "o", "ờ": "o", "ớ": "o", "ợ": "o", "ở": "o", "ỡ": "o",
        "ù": "u", "ú": "u", "ụ": "u", "ủ": "u", "ũ": "u", "ư": "u", "ừ": "u", "ứ": "u", "ự": "u", "ử": "u", "ữ": "u",
        "ỳ": "y", "ý": "y", "ỵ": "y", "ỷ": "y", "ỹ": "y",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text
