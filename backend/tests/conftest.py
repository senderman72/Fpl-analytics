"""Shared pytest fixtures."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import close_db, init_db
from app.main import app


def _db_reachable() -> bool:
    """Check if PostgreSQL is reachable (sync probe)."""
    from app.core.config import get_settings

    url = get_settings().database_url
    if not url:
        return False
    try:
        import asyncio

        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(url)

        async def _probe() -> bool:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            return True

        return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            _probe()
        )
    except Exception:
        return False


_HAS_DB = _db_reachable()

requires_db = pytest.mark.skipif(not _HAS_DB, reason="PostgreSQL not reachable")


@pytest_asyncio.fixture
async def client() -> AsyncClient:  # type: ignore[misc]
    """Async HTTP client with DB initialised in the same loop."""
    if not _HAS_DB:
        pytest.skip("PostgreSQL not reachable")
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test",
    ) as ac:
        yield ac  # type: ignore[misc]
    await close_db()
