"""Player endpoints."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cached
from app.core.database import get_session
from app.models.fixture import Fixture
from app.models.gameweek import Gameweek
from app.models.player import Player
from app.models.player_form_cache import PlayerFormCache
from app.models.player_gw_stats import PlayerGWStats
from app.models.player_gw_xg import PlayerSeasonXG
from app.models.team import Team
from app.schemas.common import APIResponse
from app.schemas.compare import PlayerComparison
from app.schemas.player import (
    PlayerDetail,
    PlayerFixture,
    PlayerGWHistory,
    PlayerIdName,
    PlayerSummary,
)
from app.services.fpl_urls import badge_url, shirt_url

router = APIRouter(prefix="/players", tags=["players"])


def _parse_compare_ids(ids_str: str) -> list[int]:
    """Parse and validate comma-separated player IDs for comparison."""
    if not ids_str or not ids_str.strip():
        msg = "ids parameter is required"
        raise ValueError(msg)
    try:
        raw = [int(x.strip()) for x in ids_str.split(",") if x.strip()]
    except ValueError:
        msg = "ids must be comma-separated integers"
        raise ValueError(msg) from None
    unique = list(dict.fromkeys(raw))  # deduplicate, preserve order
    if any(pid <= 0 for pid in unique):
        msg = "Player IDs must be positive integers"
        raise ValueError(msg)
    if len(unique) < 2 or len(unique) > 5:
        msg = "Provide 2 to 5 player IDs"
        raise ValueError(msg)
    return unique


@router.get("", response_model=APIResponse[list[PlayerSummary]])
@cached("players:list", ttl_seconds=300)
async def list_players(
    position: int | None = Query(None, ge=1, le=4),
    team_id: int | None = Query(None),
    search: str | None = Query(None, min_length=2, max_length=100),
    sort_by: str = Query(
        "form_points",
        pattern="^(form_points|now_cost|xgi_per_90|pts_per_game|minutes_pct)$",
    ),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> APIResponse[list[PlayerSummary]]:
    stmt = (
        select(Player, Team.short_name, Team.code.label("team_code"), PlayerFormCache)
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
    for player, team_short, team_code, form in rows:
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
                shirt_url=shirt_url(team_code, player.position),
                team_badge_url=badge_url(team_code),
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
        if val is None:
            return Decimal("-999")
        try:
            return Decimal(str(val))
        except Exception:
            return Decimal("-999")

    players.sort(key=sort_key, reverse=True)
    total = len(players)
    players = players[offset : offset + limit]

    return APIResponse(
        data=players, meta={"total": total, "limit": limit, "offset": offset}
    )


@router.get("/compare", response_model=APIResponse[list[PlayerComparison]])
@cached("players:compare", ttl_seconds=900)
async def compare_players(
    ids: str = Query(
        ..., max_length=50, description="Comma-separated player IDs (2-5)"
    ),
    session: AsyncSession = Depends(get_session),
) -> APIResponse[list[PlayerComparison]]:
    """Compare 2-5 players side by side with form, xG, fixtures, predictions."""
    try:
        player_ids = _parse_compare_ids(ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Fetch players with team + form cache
    result = await session.execute(
        select(Player, Team.short_name, Team.code.label("team_code"), PlayerFormCache)
        .join(Team, Player.team_id == Team.id)
        .outerjoin(
            PlayerFormCache,
            (PlayerFormCache.player_id == Player.id)
            & (PlayerFormCache.gw_window == 6),
        )
        .where(Player.id.in_(player_ids))
    )
    rows = result.all()

    if not rows:
        raise HTTPException(status_code=404, detail="No players found")

    # Season xG lookup
    xg_result = await session.execute(
        select(PlayerSeasonXG).where(PlayerSeasonXG.player_id.in_(player_ids))
    )
    xg_map = {xg.player_id: xg for xg in xg_result.scalars().all()}

    # Upcoming fixture difficulty per team
    next_gw_result = await session.execute(
        select(Gameweek.id)
        .where(Gameweek.is_finished == False)  # noqa: E712
        .order_by(Gameweek.id)
        .limit(1)
    )
    next_gw = next_gw_result.scalar()

    fdr_map: dict[int, tuple[Decimal, int]] = {}
    if next_gw:
        upcoming_gw_ids = list(range(next_gw, next_gw + 5))
        fix_result = await session.execute(
            select(Fixture).where(
                Fixture.gameweek_id.in_(upcoming_gw_ids),
                Fixture.finished == False,  # noqa: E712
            )
        )
        # Compute avg FDR per team
        team_fdrs: dict[int, list[int]] = {}
        for fix in fix_result.scalars().all():
            if fix.home_difficulty is not None:
                team_fdrs.setdefault(fix.home_team_id, []).append(
                    fix.home_difficulty
                )
            if fix.away_difficulty is not None:
                team_fdrs.setdefault(fix.away_team_id, []).append(
                    fix.away_difficulty
                )
        for tid, fdrs in team_fdrs.items():
            fdr_map[tid] = (
                Decimal(str(round(sum(fdrs) / len(fdrs), 2))),
                len(fdrs),
            )

    comparisons = []
    for player, team_short, team_code, form in rows:
        xg = xg_map.get(player.id)
        fdr_data = fdr_map.get(player.team_id)

        comparisons.append(
            PlayerComparison(
                id=player.id,
                web_name=player.web_name,
                first_name=player.first_name,
                second_name=player.second_name,
                team_short_name=team_short,
                position=player.position,
                shirt_url=shirt_url(team_code, player.position),
                team_badge_url=badge_url(team_code),
                now_cost=player.now_cost,
                selected_by_percent=player.selected_by_percent,
                form_points=form.total_points if form else None,
                pts_per_game=form.pts_per_game if form else None,
                xgi_per_90=form.xgi_per_90 if form else None,
                minutes_pct=form.minutes_pct if form else None,
                bps_avg=form.bps_avg if form else None,
                clean_sheets=form.clean_sheets if form else None,
                goals=form.goals if form else None,
                assists=form.assists if form else None,
                season_xg=xg.xg if xg else None,
                season_xa=xg.xa if xg else None,
                season_xgi=xg.xgi if xg else None,
                fdr_next_5=fdr_data[0] if fdr_data else None,
                fixture_count=fdr_data[1] if fdr_data else 0,
                ep_next=player.ep_next,
            )
        )

    # Preserve request order
    id_order = {pid: i for i, pid in enumerate(player_ids)}
    comparisons.sort(key=lambda c: id_order.get(c.id, 999))

    return APIResponse(data=comparisons)


@router.get("/ids", response_model=APIResponse[list[PlayerIdName]])
@cached("players:ids", ttl_seconds=86400)
async def list_player_ids(
    session: AsyncSession = Depends(get_session),
) -> APIResponse[list[PlayerIdName]]:
    """Lightweight endpoint returning all active player IDs and names (for sitemap)."""
    result = await session.execute(
        select(Player.id, Player.first_name, Player.second_name).where(
            Player.status != "u"
        )
    )
    return APIResponse(
        data=[
            PlayerIdName(id=pid, first_name=fn, second_name=sn)
            for pid, fn, sn in result.all()
        ]
    )


@router.get("/{player_id}", response_model=APIResponse[PlayerDetail])
@cached("players:detail", ttl_seconds=300)
async def get_player(
    player_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
) -> APIResponse[PlayerDetail]:
    result = await session.execute(
        select(Player, Team.short_name, Team.code.label("team_code"))
        .join(Team, Player.team_id == Team.id)
        .where(Player.id == player_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Player not found")
    player, team_short, team_code = row

    form_result = await session.execute(
        select(PlayerFormCache).where(
            PlayerFormCache.player_id == player_id,
            PlayerFormCache.gw_window == 6,
        )
    )
    form = form_result.scalars().first()

    xg_result = await session.execute(
        select(PlayerSeasonXG).where(PlayerSeasonXG.player_id == player_id)
    )
    xg = xg_result.scalars().first()

    season_result = await session.execute(
        select(
            func.sum(PlayerGWStats.goals_scored),
            func.sum(PlayerGWStats.assists),
            func.sum(PlayerGWStats.total_points),
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
            shirt_url=shirt_url(team_code, player.position),
            team_badge_url=badge_url(team_code),
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
@cached("players:history", ttl_seconds=300)
async def get_player_history(
    player_id: int = Path(..., ge=1),
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
@cached("players:fixtures", ttl_seconds=300)
async def get_player_fixtures(
    player_id: int = Path(..., ge=1),
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
            or_(
                Fixture.home_team_id == team_id,
                Fixture.away_team_id == team_id,
            ),
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
