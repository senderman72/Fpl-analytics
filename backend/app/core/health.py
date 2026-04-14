"""Deep health check logic."""

import datetime as dt
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player import Player


async def check_db(session: AsyncSession) -> dict[str, Any]:
    """Check DB connectivity and return basic stats."""
    try:
        await session.execute(text("SELECT 1"))
        player_count = await session.scalar(select(func.count(Player.id)))
        latest_update = await session.scalar(
            select(func.max(Player.updated_at))
        )
        return {
            "status": "ok",
            "player_count": player_count,
            "latest_player_update": (
                latest_update.isoformat() if latest_update else None
            ),
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


async def check_redis(redis_client: Redis) -> dict[str, Any]:
    """Check Redis connectivity."""
    try:
        pong = await redis_client.ping()
        return {"status": "ok" if pong else "error"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


async def check_data_freshness(session: AsyncSession) -> dict[str, Any]:
    """Check whether data has been updated recently."""
    now = dt.datetime.now(dt.UTC)
    stale_threshold = now - dt.timedelta(hours=6)

    latest_update = await session.scalar(
        select(func.max(Player.updated_at))
    )

    is_stale = latest_update is None or latest_update < stale_threshold
    hours_ago = (
        round((now - latest_update).total_seconds() / 3600, 1)
        if latest_update
        else None
    )

    return {
        "status": "stale" if is_stale else "ok",
        "last_sync_hours_ago": hours_ago,
        "stale_threshold_hours": 6,
    }


async def check_heartbeat(redis_client: Redis) -> dict[str, Any]:
    """Check the Celery heartbeat key written by the heartbeat task."""
    try:
        val = await redis_client.get("celery:heartbeat")
        if val is None:
            return {"status": "unknown", "detail": "no heartbeat recorded"}
        ts = dt.datetime.fromisoformat(val)
        age_seconds = (dt.datetime.now(dt.UTC) - ts).total_seconds()
        return {
            "status": "ok" if age_seconds < 300 else "stale",
            "last_heartbeat_seconds_ago": round(age_seconds),
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}
