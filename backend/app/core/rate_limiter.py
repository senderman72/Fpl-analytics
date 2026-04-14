"""Distributed rate limiter for outbound API requests.

Uses Redis to coordinate across multiple Celery worker processes,
ensuring the aggregate request rate stays within limits. Falls back
to a local sleep-based limiter if Redis is unavailable.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DistributedRateLimiter:
    """Redis-backed rate limiter using a simple token approach.

    All Celery worker processes share the same Redis key, ensuring
    the aggregate request rate stays within limits.
    """

    def __init__(self, key: str, min_interval: float) -> None:
        self._key = f"ratelimit:{key}"
        self._min_interval = min_interval
        self._min_interval_ms = int(min_interval * 1000)

    def _get_redis(self) -> Any:
        """Lazily connect to Redis; return None if unavailable."""
        try:
            import redis as sync_redis

            from app.core.config import get_settings

            settings = get_settings()
            return sync_redis.from_url(
                settings.redis_url, decode_responses=True
            )
        except Exception:
            return None

    def wait(self) -> None:
        """Block until the rate limit allows a new request."""
        client = self._get_redis()
        if client is None:
            # Fallback: local sleep when Redis is unavailable
            time.sleep(self._min_interval)
            return

        try:
            while True:
                now_ms = int(time.time() * 1000)
                last: str | None = client.get(self._key)
                if last is None or (now_ms - int(last)) >= self._min_interval_ms:
                    client.set(
                        self._key, str(now_ms), px=self._min_interval_ms * 2
                    )
                    return
                sleep_ms = self._min_interval_ms - (now_ms - int(last))
                if sleep_ms > 0:
                    time.sleep(sleep_ms / 1000)
        except Exception:
            logger.warning(
                "Redis rate limiter failed, falling back to local sleep",
                exc_info=True,
            )
            time.sleep(self._min_interval)
        finally:
            client.close()


# Pre-configured limiters per source
fpl_limiter = DistributedRateLimiter(key="fpl", min_interval=1.0)
understat_limiter = DistributedRateLimiter(key="understat", min_interval=1.0)
