from functools import lru_cache
import json
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="PT_", extra="ignore")

    app_name: str = "PhongTro Intelligence API"
    app_env: str = "development"
    app_debug: bool = True
    database_enabled: bool = True
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/phongtro"
    cors_origins: str = "http://localhost:3000"
    listing_dataset_path: Path = Path("../crawler/artifacts/curated/toan-quoc/listings_curated.csv")
    listing_map_default_limit: int = 600

    @property
    def cors_origin_list(self) -> list[str]:
        stripped = self.cors_origins.strip()
        if stripped.startswith("["):
            parsed = json.loads(stripped)
            return [str(origin).strip() for origin in parsed if str(origin).strip()]
        return [part.strip() for part in stripped.split(",") if part.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
