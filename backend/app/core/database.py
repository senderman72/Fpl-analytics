"""SQLAlchemy engine, session factories, and base model."""

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
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
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _sync_url(url: str) -> str:
    """Ensure the URL uses the psycopg2 driver."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("+asyncpg", "+psycopg2", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


_is_prod = settings.is_production

# Railway internal Postgres doesn't use SSL; external providers (Neon, Supabase) do.
# If the URL already contains sslmode, respect it. Otherwise default to no SSL.
_db_url = settings.database_url
_needs_ssl = "sslmode=" in _db_url or "ssl=" in _db_url
_async_connect_args: dict = {} if _needs_ssl else {"ssl": False}
_sync_connect_args: dict = {} if _needs_ssl else {"sslmode": "disable"}

# --- Async (FastAPI) ---
engine = create_async_engine(
    _async_url(_db_url),
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=5 if _is_prod else 10,
    max_overflow=3 if _is_prod else 5,
    pool_timeout=30,
    pool_recycle=300,
    connect_args=_async_connect_args,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# --- Sync (Celery workers) ---
sync_engine = create_engine(
    _sync_url(_db_url),
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=3,
    max_overflow=2,
    pool_timeout=10,
    pool_recycle=300,
    connect_args=_sync_connect_args,
)

sync_session_factory = sessionmaker(sync_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


async def get_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency that yields an async database session."""
    async with async_session_factory() as session:
        yield session
