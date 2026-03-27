"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown hooks."""
    settings = get_settings()

    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)

    yield

    from app.core.database import engine

    await engine.dispose()


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="FPL Analytics API",
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )

    # --- Routers ---
    from app.api.decisions import router as decisions_router
    from app.api.gameweeks import router as gameweeks_router
    from app.api.my_team import router as my_team_router
    from app.api.players import router as players_router
    from app.api.predictions import router as predictions_router

    app.include_router(players_router)
    app.include_router(gameweeks_router)
    app.include_router(decisions_router)
    app.include_router(predictions_router)
    app.include_router(my_team_router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
