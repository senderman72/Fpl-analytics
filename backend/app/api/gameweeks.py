"""Gameweek and fixture endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.fixture import Fixture
from app.models.gameweek import Gameweek
from app.models.team import Team
from app.schemas.common import APIResponse
from app.schemas.gameweek import FixtureOut, GameweekOut

router = APIRouter(tags=["gameweeks"])


@router.get("/gameweeks", response_model=APIResponse[list[GameweekOut]])
async def list_gameweeks(
    session: AsyncSession = Depends(get_session),
) -> APIResponse[list[GameweekOut]]:
    result = await session.execute(select(Gameweek).order_by(Gameweek.id))
    gws = result.scalars().all()
    return APIResponse(
        data=[
            GameweekOut(
                id=gw.id, name=gw.name,
                deadline_time=gw.deadline_time.isoformat(),
                is_current=gw.is_current, is_next=gw.is_next,
                is_finished=gw.is_finished, is_double=gw.is_double,
                is_blank=gw.is_blank,
                average_entry_score=gw.average_entry_score,
                highest_score=gw.highest_score,
            )
            for gw in gws
        ]
    )


@router.get("/fixtures", response_model=APIResponse[list[FixtureOut]])
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

    teams_result = await session.execute(select(Team.id, Team.short_name))
    team_names = {tid: sn for tid, sn in teams_result.all()}

    return APIResponse(
        data=[
            FixtureOut(
                id=f.id, gameweek_id=f.gameweek_id,
                home_team_id=f.home_team_id, away_team_id=f.away_team_id,
                home_short_name=team_names.get(f.home_team_id),
                away_short_name=team_names.get(f.away_team_id),
                kickoff_time=f.kickoff_time.isoformat() if f.kickoff_time else None,
                started=f.started, finished=f.finished,
                home_goals=f.home_goals, away_goals=f.away_goals,
                home_difficulty=f.home_difficulty, away_difficulty=f.away_difficulty,
            )
            for f in fixtures
        ]
    )
