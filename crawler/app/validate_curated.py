from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

from app.curation import CANONICAL_PROVINCES, CURATABLE_SOURCES, KNOWN_CONTACT_HOTLINES

VALID_STATUSES = {"active", "expired", "hidden"}
VALID_GEOCODE_PRECISIONS = {"", "exact", "street", "district", "province"}


def validate_curated(path: Path, min_rows: int) -> dict[str, object]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    errors: list[str] = []
    if len(rows) < min_rows:
        errors.append(f"row count {len(rows)} is below required minimum {min_rows}")

    ids = [str(row.get("listing_id") or "").strip() for row in rows]
    duplicate_ids = [key for key, count in Counter(ids).items() if key and count > 1]
    if duplicate_ids:
        errors.append(f"duplicate listing_id values: {len(duplicate_ids)}")

    invalid_statuses = sorted({str(row.get("status") or "") for row in rows} - VALID_STATUSES)
    if invalid_statuses:
        errors.append(f"invalid statuses: {invalid_statuses}")

    invalid_sources = sorted({str(row.get("source_name") or "") for row in rows} - CURATABLE_SOURCES)
    if invalid_sources:
        errors.append(f"invalid sources: {invalid_sources[:10]}")

    canonical_provinces = set(CANONICAL_PROVINCES)
    invalid_provinces = sorted({
        str(row.get("province") or "").strip()
        for row in rows
        if str(row.get("province") or "").strip()
        and str(row.get("province") or "").strip() not in canonical_provinces
    })
    if invalid_provinces:
        errors.append(f"invalid provinces: {invalid_provinces[:10]}")

    bad_zalo_rows = 0
    invalid_phone_rows = 0
    for row in rows:
        phone_digits = re.sub(r"\D", "", str(row.get("contact_phone") or ""))
        if phone_digits and not (len(phone_digits) == 10 and phone_digits.startswith("0")):
            invalid_phone_rows += 1
        zalo_url = str(row.get("contact_zalo_url") or "")
        if any(phone in zalo_url for phone in KNOWN_CONTACT_HOTLINES):
            bad_zalo_rows += 1
    if bad_zalo_rows:
        errors.append(f"known site hotline leaked into {bad_zalo_rows} Zalo contacts")
    if invalid_phone_rows:
        errors.append(f"invalid contact phone rows: {invalid_phone_rows}")

    coordinate_mismatches = sum(
        1
        for row in rows
        if bool(str(row.get("latitude") or "").strip()) != bool(str(row.get("longitude") or "").strip())
    )
    if coordinate_mismatches:
        errors.append(f"latitude/longitude mismatch rows: {coordinate_mismatches}")

    invalid_geocode_precisions = sorted({
        str(row.get("geocode_precision") or "").strip()
        for row in rows
        if str(row.get("geocode_precision") or "").strip() not in VALID_GEOCODE_PRECISIONS
    })
    if invalid_geocode_precisions:
        errors.append(f"invalid geocode precisions: {invalid_geocode_precisions}")

    unverified_exact_payload_rows = sum(
        1
        for row in rows
        if str(row.get("geocode_precision") or "").strip() == "exact"
        and "payload" in str(row.get("geocode_source") or "").lower()
        and "verified" not in str(row.get("geocode_source") or "").lower()
    )
    if unverified_exact_payload_rows:
        errors.append(
            f"unverified source payload marked exact: {unverified_exact_payload_rows}"
        )

    result = {
        "status": "ok" if not errors else "failed",
        "rows": len(rows),
        "sources": len({row.get("source_name") for row in rows if row.get("source_name")}),
        "provinces": len({row.get("province") for row in rows if row.get("province")}),
        "duplicate_ids": len(duplicate_ids),
        "invalid_provinces": len(invalid_provinces),
        "invalid_sources": len(invalid_sources),
        "bad_zalo_rows": bad_zalo_rows,
        "invalid_phone_rows": invalid_phone_rows,
        "coordinate_mismatches": coordinate_mismatches,
        "invalid_geocode_precisions": len(invalid_geocode_precisions),
        "unverified_exact_payload_rows": unverified_exact_payload_rows,
        "errors": errors,
    }
    if errors:
        raise RuntimeError(json.dumps(result, ensure_ascii=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate curated listing quality before loading")
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--min-rows", type=int, default=1)
    args = parser.parse_args()
    print(json.dumps(validate_curated(args.csv, args.min_rows), ensure_ascii=False))


if __name__ == "__main__":
    main()
