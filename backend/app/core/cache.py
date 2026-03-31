"""Redis response caching for FastAPI endpoints.

Provides a ``cached()`` decorator that transparently caches JSON responses
in Redis, and ``invalidate_pattern()`` to clear keys matching a glob.

All Redis operations are wrapped in try/except so the application degrades
gracefully to uncached behaviour if Redis is unavailable.
"""

from __future__ import annotations

import functools
import inspect
import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from fastapi import Request, Response
from fastapi.encoders import jsonable_encoder
from redis.asyncio import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_redis: Redis | None = None  # type: ignore[type-arg]


def get_redis() -> Redis:  # type: ignore[type-arg]
    """Create a Redis client. Call ``await client.aclose()`` on shutdown."""
    settings = get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=True)


async def init_redis() -> None:
    """Initialise the module-level Redis client (call on app startup)."""
    global _redis
    _redis = get_redis()


async def close_redis() -> None:
    """Close the module-level Redis client (call on app shutdown)."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def _build_cache_key(prefix: str, request: Request) -> str:
    """Build a deterministic cache key from prefix + path params + query params."""
    parts = [prefix]

    # Include path params (e.g., item_id=5)
    if request.path_params:
        path_str = "&".join(
            f"{k}={v}" for k, v in sorted(request.path_params.items())
        )
        parts.append(path_str)

    # Include query params (e.g., limit=10&offset=0)
    if request.query_params:
        query_str = str(request.query_params)
        parts.append(query_str)

    return ":".join(parts)


def cached(prefix: str, ttl_seconds: int) -> Callable:
    """Decorator that caches FastAPI endpoint JSON responses in Redis.

    Usage::

        @router.get("/items")
        @cached("items:list", ttl_seconds=3600)
        async def list_items(request: Request, ...) -> ...:
            ...

    The decorator automatically injects a ``request: Request`` dependency
    if the wrapped function doesn't already declare one, via FastAPI's
    dependency injection.
    """

    def decorator(func: Callable) -> Callable:
        # Check at decoration time whether the original function has a request param
        _orig_sig = inspect.signature(func)
        _orig_has_request = any(
            p.annotation is Request or p.name == "request"
            for p in _orig_sig.parameters.values()
        )

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract the Request object from kwargs (FastAPI injects it)
            request: Request | None = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            # Build clean kwargs for the original function (strip injected request)
            if not _orig_has_request and "request" in kwargs:
                call_kwargs = {k: v for k, v in kwargs.items() if k != "request"}
            else:
                call_kwargs = kwargs

            if _redis is None or request is None:
                return await func(*args, **call_kwargs)

            cache_key = _build_cache_key(prefix, request)

            # Try cache hit
            try:
                cached_data = await _redis.get(cache_key)
                if cached_data is not None:
                    return Response(
                        content=cached_data,
                        media_type="application/json",
                    )
            except Exception:
                logger.warning("Redis GET failed for key %s", cache_key, exc_info=True)

            # Cache miss — call endpoint
            result = await func(*args, **call_kwargs)

            # Store in cache
            try:
                json_str = json.dumps(jsonable_encoder(result))
                await _redis.set(cache_key, json_str, ex=ttl_seconds)
            except Exception:
                logger.warning("Redis SET failed for key %s", cache_key, exc_info=True)

            return result

        # Ensure FastAPI injects Request into the wrapper
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        has_request = any(
            p.annotation is Request or p.name == "request" for p in params
        )
        if not has_request:
            params.insert(
                0,
                inspect.Parameter(
                    "request",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=Request,
                ),
            )
            wrapper.__signature__ = sig.replace(parameters=params)  # type: ignore[attr-defined]

        return wrapper

    return decorator


async def invalidate_pattern(pattern: str) -> None:
    """Delete all Redis keys matching *pattern* (glob-style).

    Uses SCAN to avoid blocking Redis on large keyspaces.
    """
    if _redis is None:
        return

    try:
        cursor = 0
        keys_to_delete: list[bytes] = []
        while True:
            cursor, keys = await _redis.scan(cursor=cursor, match=pattern, count=200)
            keys_to_delete.extend(keys)
            if cursor == 0:
                break

        if keys_to_delete:
            await _redis.delete(*keys_to_delete)
            logger.info("Invalidated %d keys matching %s", len(keys_to_delete), pattern)
    except Exception:
        logger.warning("Redis invalidation failed for %s", pattern, exc_info=True)


def sync_invalidate_pattern(pattern: str) -> None:
    """Synchronous cache invalidation for use in Celery tasks.

    Creates a throwaway sync Redis client to delete matching keys.
    """
    import redis as sync_redis

    settings = get_settings()
    try:
        client = sync_redis.from_url(settings.redis_url, decode_responses=False)
        cursor = 0
        keys_to_delete: list[bytes] = []
        while True:
            cursor, keys = client.scan(cursor=cursor, match=pattern, count=200)
            keys_to_delete.extend(keys)
            if cursor == 0:
                break

        if keys_to_delete:
            client.delete(*keys_to_delete)
            logger.info(
                "Sync-invalidated %d keys matching %s", len(keys_to_delete), pattern
            )
        client.close()
    except Exception:
        logger.warning("Sync Redis invalidation failed for %s", pattern, exc_info=True)
