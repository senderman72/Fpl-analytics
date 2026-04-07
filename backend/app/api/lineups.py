"""Predicted lineup endpoints."""

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cached
from app.core.database import get_session
from app.models.player import Player
from app.models.player_form_cache import PlayerFormCache
from app.models.team import Team
from app.schemas.common import APIResponse
from app.schemas.lineup import PredictedLineup
from app.services.fpl_urls import badge_url, shirt_url
from app.services.lineup_predictor import predict_lineup

router = APIRouter(prefix="/lineups", tags=["lineups"])


@router.get("/predicted", response_model=APIResponse[list[PredictedLineup]])
@cached("lineups:predicted", ttl_seconds=300)
async def get_predicted_lineups(
    team_id: int | None = Query(None, ge=1, le=20),
    session: AsyncSession = Depends(get_session),
) -> APIResponse[list[PredictedLineup]]:
    """Predict starting XIs for all or one PL team."""
    # Fetch all players with form cache
    stmt = (
        select(
            Player,
            Team.short_name,
            Team.code.label("team_code"),
            PlayerFormCache,
        )
        .join(Team, Player.team_id == Team.id)
        .outerjoin(
            PlayerFormCache,
            (PlayerFormCache.player_id == Player.id)
            & (PlayerFormCache.gw_window == 6),
        )
    )
    if team_id:
        stmt = stmt.where(Player.team_id == team_id)

    result = await session.execute(stmt)
    rows = result.all()

    # Group players by team
    teams_data: dict[int, dict] = {}
    team_players: dict[int, list[dict]] = {}

    for player, team_short, team_code, form in rows:
        tid = player.team_id
        if tid not in teams_data:
            teams_data[tid] = {
                "team_short_name": team_short,
                "team_badge_url": badge_url(team_code),
            }
        team_players.setdefault(tid, []).append({
            "player_id": player.id,
            "web_name": player.web_name,
            "shirt_url": shirt_url(team_code, player.position),
            "position": player.position,
            "status": player.status,
            "chance_of_playing": player.chance_of_playing_next_round,
            "minutes_pct": form.minutes_pct if form else Decimal("0"),
            "form": player.form or Decimal("0"),
            "form_points": form.total_points if form else 0,
            "news": player.news,
        })

    # Predict lineup for each team
    lineups = []
    for tid in sorted(teams_data):
        info = teams_data[tid]
        lineup = predict_lineup(
            team_id=tid,
            team_short_name=info["team_short_name"],
            team_badge_url=info["team_badge_url"],
            players=team_players.get(tid, []),
        )
        lineups.append(lineup)

    return APIResponse(data=lineups)
