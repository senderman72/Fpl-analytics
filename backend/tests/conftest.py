"""Shared pytest fixtures."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import close_db, init_db
from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncClient:  # type: ignore[misc]
    """Async HTTP client with DB initialised in the same loop."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test",
    ) as ac:
        yield ac  # type: ignore[misc]
    await close_db()
