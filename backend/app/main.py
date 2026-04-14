"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown hooks."""
    settings = get_settings()

    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)

    from app.core.cache import close_redis, init_redis
    from app.core.database import close_db, init_db

    await init_db()
    await init_redis()

    yield

    await close_redis()
    await close_db()


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="FPL Analytics API",
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )

    from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
    from starlette.middleware.gzip import GZipMiddleware
    from starlette.requests import Request
    from starlette.responses import Response

    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint,
        ) -> Response:
            response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            return response

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # --- Routers ---
    from app.api.decisions import router as decisions_router
    from app.api.gameweeks import router as gameweeks_router
    from app.api.lineups import router as lineups_router
    from app.api.my_team import router as my_team_router
    from app.api.players import router as players_router
    from app.api.predictions import router as predictions_router

    app.include_router(players_router)
    app.include_router(gameweeks_router)
    app.include_router(decisions_router)
    app.include_router(predictions_router)
    app.include_router(my_team_router)
    app.include_router(lineups_router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/deep")
    async def health_deep(
        session: AsyncSession = Depends(get_session),
    ) -> dict[str, Any]:
        from app.core.cache import _redis as redis_client
        from app.core.health import (
            check_data_freshness,
            check_db,
            check_heartbeat,
            check_redis,
        )

        db = await check_db(session)

        if redis_client is not None:
            redis_result = await check_redis(redis_client)
            heartbeat = await check_heartbeat(redis_client)
        else:
            redis_result = {"status": "not_initialized"}
            heartbeat = {"status": "not_initialized"}

        freshness = await check_data_freshness(session)

        overall = "ok"
        if db["status"] != "ok" or redis_result["status"] != "ok":
            overall = "degraded"
        if freshness["status"] == "stale":
            overall = "stale_data"

        return {
            "status": overall,
            "checks": {
                "database": db,
                "redis": redis_result,
                "data_freshness": freshness,
                "celery_heartbeat": heartbeat,
            },
        }

    return app


app = create_app()
