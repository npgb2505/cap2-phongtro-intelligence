from __future__ import annotations

from pathlib import Path

import boto3


def upload_files(
    *,
    bucket: str,
    root: Path,
    file_paths: list[str],
    prefix: str = "",
) -> list[str]:
    client = boto3.client("s3")
    uploaded: list[str] = []
    normalized_prefix = prefix.strip("/")

    for file_path in sorted(set(file_paths)):
        path = Path(file_path)
        if not path.is_absolute():
            path = root / path
        if not path.exists() or not path.is_file():
            continue
        key = path.relative_to(root).as_posix()
        if normalized_prefix:
            key = f"{normalized_prefix}/{key}"
        client.upload_file(str(path), bucket, key)
        uploaded.append(f"s3://{bucket}/{key}")

    return uploaded
