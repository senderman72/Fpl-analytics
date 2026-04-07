"""Gameweek and fixture endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cached
from app.core.database import get_session
from app.models.fixture import Fixture
from app.models.gameweek import Gameweek
from app.models.player import Player
from app.models.team import Team
from app.schemas.common import APIResponse
from app.schemas.gameweek import (
    FixtureOut,
    GameweekOut,
    LiveFixture,
    LiveGWResponse,
    LivePlayerScore,
)
from app.services.fpl_client import fetch_live_gw
from app.services.fpl_urls import PL_CDN, shirt_url

logger = logging.getLogger(__name__)

router = APIRouter(tags=["gameweeks"])


@router.get("/gameweeks", response_model=APIResponse[list[GameweekOut]])
@cached("gameweeks:list", ttl_seconds=300)
async def list_gameweeks(
    session: AsyncSession = Depends(get_session),
) -> APIResponse[list[GameweekOut]]:
    result = await session.execute(select(Gameweek).order_by(Gameweek.id))
    gws = result.scalars().all()
    return APIResponse(
        data=[
            GameweekOut(
                id=gw.id,
                name=gw.name,
                deadline_time=gw.deadline_time.isoformat()
                + ("" if gw.deadline_time.tzinfo else "Z"),
                is_current=gw.is_current,
                is_next=gw.is_next,
                is_finished=gw.is_finished,
                is_double=gw.is_double,
                is_blank=gw.is_blank,
                average_entry_score=gw.average_entry_score,
                highest_score=gw.highest_score,
            )
            for gw in gws
        ]
    )


@router.get("/fixtures", response_model=APIResponse[list[FixtureOut]])
@cached("fixtures:list", ttl_seconds=300)
async def list_fixtures(
    gameweek_id: int | None = Query(None),
    team_id: int | None = Query(None),
    finished: bool | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> APIResponse[list[FixtureOut]]:
    stmt = select(Fixture).order_by(Fixture.gameweek_id, Fixture.kickoff_time)

    if gameweek_id is not None:
        stmt = stmt.where(Fixture.gameweek_id == gameweek_id)
    if team_id is not None:
        stmt = stmt.where(
            or_(Fixture.home_team_id == team_id, Fixture.away_team_id == team_id)
        )
    if finished is not None:
        stmt = stmt.where(Fixture.finished == finished)

    result = await session.execute(stmt)
    fixtures = result.scalars().all()

    teams_result = await session.execute(select(Team.id, Team.short_name, Team.code))
    team_info = {tid: (sn, code) for tid, sn, code in teams_result.all()}

    pl_cdn = PL_CDN

    return APIResponse(
        data=[
            FixtureOut(
                id=f.id,
                gameweek_id=f.gameweek_id,
                home_team_id=f.home_team_id,
                away_team_id=f.away_team_id,
                home_short_name=team_info.get(f.home_team_id, (None, None))[0],
                away_short_name=team_info.get(f.away_team_id, (None, None))[0],
                home_badge_url=(
                    f"{pl_cdn}/badges/100/t{team_info[f.home_team_id][1]}.png"
                    if f.home_team_id in team_info and team_info[f.home_team_id][1]
                    else None
                ),
                away_badge_url=(
                    f"{pl_cdn}/badges/100/t{team_info[f.away_team_id][1]}.png"
                    if f.away_team_id in team_info and team_info[f.away_team_id][1]
                    else None
                ),
                kickoff_time=f.kickoff_time.isoformat() if f.kickoff_time else None,
                started=f.started,
                finished=f.finished,
                home_goals=f.home_goals,
                away_goals=f.away_goals,
                home_difficulty=f.home_difficulty,
                away_difficulty=f.away_difficulty,
            )
            for f in fixtures
        ]
    )


@router.get("/live/{gw_id}", response_model=APIResponse[LiveGWResponse])
async def get_live_gw(
    gw_id: int,
    session: AsyncSession = Depends(get_session),
) -> APIResponse[LiveGWResponse]:
    """Fetch live scores for an active gameweek.

    Reads from Redis cache (populated by ``sync_live_gw`` Celery task)
    when available, falling back to a direct FPL API call.
    """
    teams_result = await session.execute(
        select(Team.id, Team.short_name, Team.code),
    )
    team_map = {
        tid: (sn, code) for tid, sn, code in teams_result.all()
    }

    players_result = await session.execute(
        select(
            Player.id, Player.web_name, Player.team_id, Player.position,
        ),
    )
    player_map = {
        pid: (wn, tid, pos)
        for pid, wn, tid, pos in players_result.all()
    }

    fix_result = await session.execute(
        select(Fixture).where(Fixture.gameweek_id == gw_id),
    )
    db_fixtures = fix_result.scalars().all()

    pl_cdn = PL_CDN
    fixtures = []
    for f in db_fixtures:
        home_info = team_map.get(f.home_team_id, ("???", 0))
        away_info = team_map.get(f.away_team_id, ("???", 0))
        elapsed = 90 if f.finished else 0 if not f.started else 45
        fixtures.append(
            LiveFixture(
                fixture_id=f.id,
                home_team_short=home_info[0],
                away_team_short=away_info[0],
                home_badge_url=(
                    f"{pl_cdn}/badges/100/t{home_info[1]}.png"
                    if home_info[1]
                    else None
                ),
                away_badge_url=(
                    f"{pl_cdn}/badges/100/t{away_info[1]}.png"
                    if away_info[1]
                    else None
                ),
                home_goals=f.home_goals or 0,
                away_goals=f.away_goals or 0,
                started=f.started,
                finished=f.finished,
                minutes=elapsed,
            )
        )

    # Live player data — try Redis cache, fall back to FPL API
    live_data = await _get_live_data(gw_id)

    players: list[LivePlayerScore] = []
    for elem in live_data.get("elements", []):
        pid = elem["id"]
        stats = elem.get("stats", {})
        p_info = player_map.get(pid)
        if not p_info:
            continue
        web_name, team_id, position = p_info
        t_info = team_map.get(team_id, ("???", 0))
        total_pts = stats.get("total_points", 0)
        if stats.get("minutes", 0) == 0 and total_pts == 0:
            continue
        players.append(
            LivePlayerScore(
                player_id=pid,
                web_name=web_name,
                shirt_url=shirt_url(t_info[1], position),
                minutes=stats.get("minutes", 0),
                goals_scored=stats.get("goals_scored", 0),
                assists=stats.get("assists", 0),
                bonus=stats.get("bonus", 0),
                bps=stats.get("bps", 0),
                total_points=total_pts,
            )
        )

    players.sort(key=lambda p: p.total_points, reverse=True)

    return APIResponse(
        data=LiveGWResponse(
            gameweek_id=gw_id, fixtures=fixtures, players=players,
        ),
    )


async def _get_live_data(gw_id: int) -> dict[str, Any]:
    """Read live GW data from Redis cache, falling back to FPL API."""
    from app.core.cache import _redis

    if _redis is not None:
        try:
            cached = await _redis.get(f"live:gw:{gw_id}")
            if cached is not None:
                import json

                return json.loads(cached)
        except Exception:
            logger.warning(
                "Redis GET failed for live:gw:%d", gw_id,
            )

    try:
        return await fetch_live_gw(gw_id)
    except Exception:
        logger.warning(
            "FPL API live fetch failed for GW %d",
            gw_id,
            exc_info=True,
        )
        return {"elements": []}
