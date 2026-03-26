"""Redis connection for caching and pub/sub."""

from redis.asyncio import Redis

from app.core.config import get_settings

settings = get_settings()


def get_redis() -> Redis:  # type: ignore[type-arg]
    """Create a Redis client. Call ``await client.aclose()`` on shutdown."""
    return Redis.from_url(settings.redis_url, decode_responses=True)
