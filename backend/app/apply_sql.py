from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg


def apply_sql_file(sql_path: Path, database_url: str) -> dict[str, str]:
    if not sql_path.exists():
        raise FileNotFoundError(f"Missing SQL file: {sql_path}")

    normalized_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    sql_text = sql_path.read_text(encoding="utf-8")

    with psycopg.connect(normalized_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql_text)

    return {"sql_path": str(sql_path), "status": "applied"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply a SQL file to PostgreSQL/Supabase")
    parser.add_argument("--file", type=Path, required=True, help="Path to a SQL file")
    parser.add_argument(
        "--database-url-env",
        default="PT_DATABASE_URL",
        help="Environment variable containing the database URL",
    )
    args = parser.parse_args()

    database_url = os.getenv(args.database_url_env)
    if not database_url:
        raise SystemExit(f"Missing database URL env var: {args.database_url_env}")

    print(apply_sql_file(args.file.resolve(), database_url))


if __name__ == "__main__":
    main()
