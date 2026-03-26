"""Simple rate limiter for outbound API requests.

Enforces a minimum interval between requests per source.
Thread-safe via threading.Lock for use in Celery workers.
"""

import threading
import time


class RateLimiter:
    """Enforces a minimum delay between calls to ``wait()``."""

    def __init__(self, min_interval: float) -> None:
        self._min_interval = min_interval
        self._last_call = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        """Block until enough time has passed since the last call."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()


# Pre-configured limiters per source
fpl_limiter = RateLimiter(min_interval=1.0)  # 1 req/s for FPL API
understat_limiter = RateLimiter(min_interval=1.0)  # 1 req/s for Understat
fbref_limiter = RateLimiter(min_interval=3.0)  # 1 req/3s for FBref
