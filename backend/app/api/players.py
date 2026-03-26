"""Player endpoints."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.fixture import Fixture
from app.models.gameweek import Gameweek
from app.models.player import Player
from app.models.player_form_cache import PlayerFormCache
from app.models.player_gw_stats import PlayerGWStats
from app.models.player_gw_xg import PlayerSeasonXG
from app.models.team import Team
from app.schemas.common import APIResponse
from app.schemas.player import (
    PlayerDetail,
    PlayerFixture,
    PlayerGWHistory,
    PlayerSummary,
)

router = APIRouter(prefix="/players", tags=["players"])


@router.get("", response_model=APIResponse[list[PlayerSummary]])
async def list_players(
    position: int | None = Query(None, ge=1, le=4),
    team_id: int | None = Query(None),
    search: str | None = Query(None, min_length=2),
    sort_by: str = Query(
        "form_points",
        pattern="^(form_points|now_cost|xgi_per_90|pts_per_game|minutes_pct)$",
    ),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> APIResponse[list[PlayerSummary]]:
    stmt = (
        select(Player, Team.short_name, PlayerFormCache)
        .join(Team, Player.team_id == Team.id)
        .outerjoin(
            PlayerFormCache,
            (PlayerFormCache.player_id == Player.id) & (PlayerFormCache.gw_window == 6),
        )
    )

    if position:
        stmt = stmt.where(Player.position == position)
    if team_id:
        stmt = stmt.where(Player.team_id == team_id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(Player.web_name.ilike(pattern), Player.second_name.ilike(pattern))
        )

    result = await session.execute(stmt)
    rows = result.all()

    players = []
    for player, team_short, form in rows:
        players.append(
            PlayerSummary(
                id=player.id,
                web_name=player.web_name,
                first_name=player.first_name,
                second_name=player.second_name,
                team_id=player.team_id,
                team_short_name=team_short,
                position=player.position,
                now_cost=player.now_cost,
                status=player.status,
                chance_of_playing_next_round=player.chance_of_playing_next_round,
                news=player.news,
                is_penalty_taker=player.is_penalty_taker,
                is_set_piece_taker=player.is_set_piece_taker,
                form_points=form.total_points if form else None,
                pts_per_game=form.pts_per_game if form else None,
                xgi_per_90=form.xgi_per_90 if form else None,
                minutes_pct=form.minutes_pct if form else None,
                bps_avg=form.bps_avg if form else None,
                selected_by_percent=player.selected_by_percent,
                transfers_in_event=player.transfers_in_event,
                transfers_out_event=player.transfers_out_event,
                cost_change_event=player.cost_change_event,
            )
        )

    def sort_key(p: PlayerSummary) -> Decimal:
        val = getattr(p, sort_by, None)
        return Decimal(str(val)) if val is not None else Decimal("-999")

    players.sort(key=sort_key, reverse=True)
    total = len(players)
    players = players[offset : offset + limit]

    return APIResponse(
        data=players, meta={"total": total, "limit": limit, "offset": offset}
    )


@router.get("/{player_id}", response_model=APIResponse[PlayerDetail])
async def get_player(
    player_id: int,
    session: AsyncSession = Depends(get_session),
) -> APIResponse[PlayerDetail]:
    result = await session.execute(
        select(Player, Team.short_name)
        .join(Team, Player.team_id == Team.id)
        .where(Player.id == player_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Player not found")
    player, team_short = row

    form_result = await session.execute(
        select(PlayerFormCache).where(
            PlayerFormCache.player_id == player_id, PlayerFormCache.gw_window == 6
        )
    )
    form = form_result.scalars().first()

    xg_result = await session.execute(
        select(PlayerSeasonXG).where(PlayerSeasonXG.player_id == player_id)
    )
    xg = xg_result.scalars().first()

    # Season actuals from GW stats
    from sqlalchemy import func as sa_func

    season_result = await session.execute(
        select(
            sa_func.sum(PlayerGWStats.goals_scored),
            sa_func.sum(PlayerGWStats.assists),
            sa_func.sum(PlayerGWStats.total_points),
        ).where(PlayerGWStats.player_id == player_id)
    )
    season_row = season_result.first()
    s_goals = season_row[0] or 0 if season_row else 0
    s_assists = season_row[1] or 0 if season_row else 0
    s_points = season_row[2] or 0 if season_row else 0

    return APIResponse(
        data=PlayerDetail(
            id=player.id,
            web_name=player.web_name,
            first_name=player.first_name,
            second_name=player.second_name,
            team_id=player.team_id,
            team_short_name=team_short,
            position=player.position,
            now_cost=player.now_cost,
            status=player.status,
            chance_of_playing_next_round=player.chance_of_playing_next_round,
            news=player.news,
            is_penalty_taker=player.is_penalty_taker,
            is_set_piece_taker=player.is_set_piece_taker,
            understat_id=player.understat_id,
            form_points=form.total_points if form else None,
            pts_per_game=form.pts_per_game if form else None,
            xgi_per_90=form.xgi_per_90 if form else None,
            minutes_pct=form.minutes_pct if form else None,
            bps_avg=form.bps_avg if form else None,
            selected_by_percent=player.selected_by_percent,
            transfers_in_event=player.transfers_in_event,
            transfers_out_event=player.transfers_out_event,
            cost_change_event=player.cost_change_event,
            season_xg=xg.xg if xg else None,
            season_xa=xg.xa if xg else None,
            season_xgi=xg.xgi if xg else None,
            season_npxg=xg.npxg if xg else None,
            season_games=xg.games if xg else None,
            season_minutes=xg.minutes if xg else None,
            season_goals=s_goals,
            season_assists=s_assists,
            season_points=s_points,
        )
    )


@router.get("/{player_id}/history", response_model=APIResponse[list[PlayerGWHistory]])
async def get_player_history(
    player_id: int,
    session: AsyncSession = Depends(get_session),
) -> APIResponse[list[PlayerGWHistory]]:
    result = await session.execute(
        select(PlayerGWStats)
        .where(PlayerGWStats.player_id == player_id)
        .order_by(PlayerGWStats.gameweek_id)
    )
    stats = result.scalars().all()
    return APIResponse(
        data=[
            PlayerGWHistory(
                gameweek_id=s.gameweek_id,
                fixture_id=s.fixture_id,
                minutes=s.minutes,
                goals_scored=s.goals_scored,
                assists=s.assists,
                clean_sheets=s.clean_sheets,
                goals_conceded=s.goals_conceded,
                bonus=s.bonus,
                bps=s.bps,
                influence=s.influence,
                creativity=s.creativity,
                threat=s.threat,
                ict_index=s.ict_index,
                total_points=s.total_points,
                transfers_in=s.transfers_in,
                transfers_out=s.transfers_out,
                value=s.value,
            )
            for s in stats
        ]
    )


@router.get("/{player_id}/fixtures", response_model=APIResponse[list[PlayerFixture]])
async def get_player_fixtures(
    player_id: int,
    limit: int = Query(8, ge=1, le=20),
    session: AsyncSession = Depends(get_session),
) -> APIResponse[list[PlayerFixture]]:
    result = await session.execute(select(Player.team_id).where(Player.id == player_id))
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Player not found")
    team_id = row[0]

    result = await session.execute(
        select(Fixture, Gameweek.is_double)
        .outerjoin(Gameweek, Fixture.gameweek_id == Gameweek.id)
        .where(
            Fixture.finished == False,  # noqa: E712
            or_(Fixture.home_team_id == team_id, Fixture.away_team_id == team_id),
        )
        .order_by(Fixture.gameweek_id, Fixture.kickoff_time)
        .limit(limit)
    )
    rows = result.all()

    teams_result = await session.execute(select(Team.id, Team.short_name))
    team_names = {tid: sn for tid, sn in teams_result.all()}

    fixtures = []
    for fixture, is_double in rows:
        is_home = fixture.home_team_id == team_id
        opp_id = fixture.away_team_id if is_home else fixture.home_team_id
        difficulty = fixture.home_difficulty if is_home else fixture.away_difficulty
        fixtures.append(
            PlayerFixture(
                fixture_id=fixture.id,
                gameweek_id=fixture.gameweek_id,
                opponent_team_id=opp_id,
                opponent_short_name=team_names.get(opp_id, "???"),
                is_home=is_home,
                difficulty=difficulty,
                kickoff_time=fixture.kickoff_time.isoformat()
                if fixture.kickoff_time
                else None,
                is_double_gw=is_double or False,
            )
        )
    return APIResponse(data=fixtures)
