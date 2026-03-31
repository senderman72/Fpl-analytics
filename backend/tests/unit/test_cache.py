"""Tests for the Redis caching decorator and invalidation helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.cache import cached, close_redis, init_redis, invalidate_pattern

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_app() -> FastAPI:
    """Build a tiny FastAPI app with cached endpoints for testing."""
    app = FastAPI()

    call_count: dict[str, int] = {"hits": 0}

    @app.get("/items")
    @cached("items:list", ttl_seconds=300)
    async def list_items(limit: int = 10) -> dict:
        call_count["hits"] += 1
        return {"items": ["a", "b"], "call": call_count["hits"]}

    @app.get("/items/{item_id}")
    @cached("items:detail", ttl_seconds=300)
    async def get_item(item_id: int) -> dict:
        call_count["hits"] += 1
        return {"id": item_id, "call": call_count["hits"]}

    # Expose call_count so tests can inspect it
    app.state.call_count = call_count  # type: ignore[attr-defined]
    return app


# ---------------------------------------------------------------------------
# Unit tests — mock Redis
# ---------------------------------------------------------------------------


class TestCachedDecoratorCacheMiss:
    """When Redis has no cached value, the endpoint runs and stores the result."""

    async def test_miss_calls_endpoint_and_stores(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # cache miss

        with patch("app.core.cache._redis", mock_redis):
            app = _build_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/items?limit=5")

            assert resp.status_code == 200
            body = resp.json()
            assert body["items"] == ["a", "b"]
            assert body["call"] == 1

            # Should have called redis.set to store the result
            mock_redis.set.assert_called_once()
            call_args = mock_redis.set.call_args
            assert call_args[1]["ex"] == 300  # TTL


class TestCachedDecoratorCacheHit:
    """When Redis returns cached JSON, the endpoint function is NOT called."""

    async def test_hit_returns_cached_and_skips_endpoint(self) -> None:
        cached_json = '{"items": ["cached"], "call": 0}'
        mock_redis = AsyncMock()
        mock_redis.get.return_value = cached_json

        with patch("app.core.cache._redis", mock_redis):
            app = _build_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/items?limit=5")

            assert resp.status_code == 200
            body = resp.json()
            assert body["items"] == ["cached"]

            # Endpoint was never called
            assert app.state.call_count["hits"] == 0  # type: ignore[attr-defined]

            # Redis.set was NOT called (no need to re-store)
            mock_redis.set.assert_not_called()


class TestCachedDecoratorCacheKeyIncludesParams:
    """Different query params produce different cache keys."""

    async def test_different_params_different_keys(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        with patch("app.core.cache._redis", mock_redis):
            app = _build_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                await c.get("/items?limit=5")
                await c.get("/items?limit=20")

            # Two different cache keys used for get()
            keys_used = [call.args[0] for call in mock_redis.get.call_args_list]
            assert len(keys_used) == 2
            assert keys_used[0] != keys_used[1]


class TestCachedDecoratorPathParams:
    """Path parameters are included in the cache key."""

    async def test_path_params_in_key(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        with patch("app.core.cache._redis", mock_redis):
            app = _build_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                await c.get("/items/1")
                await c.get("/items/2")

            keys_used = [call.args[0] for call in mock_redis.get.call_args_list]
            assert keys_used[0] != keys_used[1]


class TestCachedDecoratorRedisFallthrough:
    """If Redis raises an exception, the endpoint still works (graceful degradation)."""

    async def test_redis_error_falls_through(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = ConnectionError("Redis down")
        mock_redis.set.side_effect = ConnectionError("Redis down")

        with patch("app.core.cache._redis", mock_redis):
            app = _build_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/items?limit=5")

            assert resp.status_code == 200
            body = resp.json()
            assert body["items"] == ["a", "b"]


class TestCachedDecoratorNoRedis:
    """If Redis was never initialized (_redis is None), falls through."""

    async def test_no_redis_falls_through(self) -> None:
        with patch("app.core.cache._redis", None):
            app = _build_app()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/items?limit=5")

            assert resp.status_code == 200
            assert resp.json()["items"] == ["a", "b"]


# ---------------------------------------------------------------------------
# Invalidation tests
# ---------------------------------------------------------------------------


class TestInvalidatePattern:
    """invalidate_pattern uses SCAN + DELETE to clear matching keys."""

    async def test_invalidate_deletes_matching_keys(self) -> None:
        mock_redis = AsyncMock()
        # Simulate SCAN returning some keys
        mock_redis.scan.side_effect = [
            (0, [b"items:list:limit=5", b"items:list:limit=10"]),
        ]

        with patch("app.core.cache._redis", mock_redis):
            await invalidate_pattern("items:*")

        mock_redis.delete.assert_called_once()
        deleted_keys = mock_redis.delete.call_args.args
        assert b"items:list:limit=5" in deleted_keys
        assert b"items:list:limit=10" in deleted_keys

    async def test_invalidate_no_keys_found(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.scan.side_effect = [(0, [])]

        with patch("app.core.cache._redis", mock_redis):
            await invalidate_pattern("nonexistent:*")

        mock_redis.delete.assert_not_called()

    async def test_invalidate_redis_down_no_error(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.scan.side_effect = ConnectionError("Redis down")

        with patch("app.core.cache._redis", mock_redis):
            # Should not raise
            await invalidate_pattern("items:*")

    async def test_invalidate_no_redis_no_error(self) -> None:
        with patch("app.core.cache._redis", None):
            # Should not raise
            await invalidate_pattern("items:*")


# ---------------------------------------------------------------------------
# Lifecycle tests
# ---------------------------------------------------------------------------


class TestRedisLifecycle:
    async def test_init_creates_redis_client(self) -> None:
        with patch("app.core.cache.get_redis") as mock_get:
            mock_client = AsyncMock()
            mock_get.return_value = mock_client

            await init_redis()

            mock_get.assert_called_once()

    async def test_close_shuts_down_client(self) -> None:
        mock_client = AsyncMock()

        with patch("app.core.cache._redis", mock_client):
            await close_redis()

            mock_client.aclose.assert_called_once()
