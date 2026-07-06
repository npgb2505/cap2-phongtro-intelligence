from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="PT_", extra="ignore")

    source_name: str = "phongtro123"
    base_url: str = "https://phongtro123.com"
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    request_delay_seconds: float = 1.0
    request_timeout_seconds: float = 45.0
    request_max_retries: int = 3
    request_retry_backoff_seconds: float = 2.0
    detail_worker_count: int = 6
    save_raw_html: bool = False
    local_artifact_dir: Path = Path("artifacts")


settings = Settings()
