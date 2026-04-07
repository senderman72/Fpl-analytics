"""SQLAlchemy engine, session factories, and base model."""

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()


def _async_url(url: str) -> str:
    """Ensure the URL uses the asyncpg driver."""
    if url.startswith("postgresql://"):
        return url.replace(
            "postgresql://", "postgresql+asyncpg://", 1,
        )
    return url


def _sync_url(url: str) -> str:
    """Ensure the URL uses the psycopg2 driver."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("+asyncpg", "+psycopg2", 1)
    if url.startswith("postgresql://"):
        return url.replace(
            "postgresql://", "postgresql+psycopg2://", 1,
        )
    return url


class Base(DeclarativeBase):
    """Base class for all ORM models."""


# --- Async (FastAPI) — deferred to init_db() ---
_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> None:
    """Create the async engine and session factory.

    Must be called inside a running event loop (e.g. FastAPI lifespan).
    """
    global _engine, _async_session_factory
    _engine = create_async_engine(
        _async_url(settings.database_url),
        echo=settings.debug,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=5,
        pool_timeout=30,
        pool_recycle=300,
    )
    _async_session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def close_db() -> None:
    """Dispose of the async engine."""
    global _engine, _async_session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None


def get_engine() -> AsyncEngine:
    """Return the async engine (must call init_db first)."""
    if _engine is None:
        msg = "Database not initialised — call init_db() first"
        raise RuntimeError(msg)
    return _engine


# --- Sync (Celery workers — safe at module level) ---
sync_engine = create_engine(
    _sync_url(settings.database_url),
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=3,
    max_overflow=2,
    pool_timeout=10,
    pool_recycle=300,
)

sync_session_factory = sessionmaker(
    sync_engine, expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency that yields an async database session."""
    if _async_session_factory is None:
        msg = "Database not initialised — call init_db() first"
        raise RuntimeError(msg)
    async with _async_session_factory() as session:
        yield session
