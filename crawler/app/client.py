from __future__ import annotations

import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings


class PhongtroHttpClient:
    def __init__(self) -> None:
        self._last_request_at = 0.0

    def fetch_text(self, url: str) -> str:
        last_error: Exception | None = None
        for attempt in range(1, settings.request_max_retries + 1):
            self._throttle()
            request = Request(
                url,
                headers={
                    "User-Agent": settings.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                },
            )
            try:
                with urlopen(request, timeout=settings.request_timeout_seconds) as response:
                    return response.read().decode("utf-8", errors="ignore")
            except (TimeoutError, URLError, HTTPError) as exc:
                last_error = exc
                if attempt >= settings.request_max_retries:
                    break
                time.sleep(settings.request_retry_backoff_seconds * attempt)
        assert last_error is not None
        raise last_error

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        wait_for = settings.request_delay_seconds - elapsed
        if wait_for > 0:
            time.sleep(wait_for)
        self._last_request_at = time.monotonic()
