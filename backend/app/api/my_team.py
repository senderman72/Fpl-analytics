"""My Team endpoint — fetch and enrich a manager's squad."""

import asyncio
import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cached
from app.core.database import get_session
from app.models.fixture import Fixture
from app.models.gameweek import Gameweek
from app.models.player import Player
from app.models.player_form_cache import PlayerFormCache
from app.models.team import Team
from app.schemas.common import APIResponse
from app.schemas.my_team import FixturePreview, MyTeamPick, MyTeamResponse
from app.schemas.transfer import TransferPlan
from app.services.fpl_client import fetch_manager_info, fetch_manager_picks
from app.services.fpl_urls import shirt_url
from app.services.points_model import predict_upcoming
from app.services.transfer_engine import suggest_transfers

logger = logging.getLogger(__name__)

router = APIRouter(tags=["my-team"])


@router.get("/my-team/{manager_id}", response_model=APIResponse[MyTeamResponse])
async def get_my_team(
    manager_id: int,
    session: AsyncSession = Depends(get_session),
) -> APIResponse[MyTeamResponse]:
    """Fetch a manager's squad and enrich with form, predictions, and fixtures."""
    # 1. Get manager info from FPL API
    try:
        manager = await fetch_manager_info(manager_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Manager not found") from exc

    current_event = manager.get("current_event")
    if not current_event:
        raise HTTPException(status_code=400, detail="No active gameweek")

    # 2. Get picks for current/latest GW
    try:
        picks_data = await fetch_manager_picks(manager_id, current_event)
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail="Picks not found for this gameweek",
        ) from exc

    picks = picks_data.get("picks", [])
    entry_history = picks_data.get("entry_history", {})

    player_ids = [p["element"] for p in picks]

    # 3. Look up players in our DB
    result = await session.execute(
        select(Player, Team.short_name, Team.code.label("team_code"), PlayerFormCache)
        .join(Team, Player.team_id == Team.id)
        .outerjoin(
            PlayerFormCache,
            (PlayerFormCache.player_id == Player.id) & (PlayerFormCache.gw_window == 6),
        )
        .where(Player.id.in_(player_ids))
    )
    rows = result.all()
    player_map = {p.id: (p, ts, tc, f) for p, ts, tc, f in rows}

    # 4. Get predictions
    pred_list = await asyncio.to_thread(predict_upcoming, 1)
    pred_lookup = {p["player_id"]: p["predicted_points"] for p in pred_list}

    # 5. Get upcoming fixtures for all teams
    next_gw_result = await session.execute(
        select(Gameweek.id).where(Gameweek.is_next == True).limit(1)  # noqa: E712
    )
    next_gw = next_gw_result.scalar()

    team_fixtures: dict[int, list[FixturePreview]] = {}
    if next_gw:
        # Get team short names
        teams_result = await session.execute(select(Team.id, Team.short_name))
        team_names = {tid: sn for tid, sn in teams_result.all()}

        fix_result = await session.execute(
            select(Fixture)
            .where(
                Fixture.gameweek_id >= next_gw,
                Fixture.gameweek_id <= next_gw + 2,
                Fixture.gameweek_id.isnot(None),
            )
            .order_by(Fixture.gameweek_id)
        )
        for f in fix_result.scalars().all():
            # Home team perspective
            team_fixtures.setdefault(f.home_team_id, []).append(
                FixturePreview(
                    opponent=team_names.get(f.away_team_id, "???"),
                    difficulty=f.home_difficulty or 3,
                    is_home=True,
                )
            )
            # Away team perspective
            team_fixtures.setdefault(f.away_team_id, []).append(
                FixturePreview(
                    opponent=team_names.get(f.home_team_id, "???"),
                    difficulty=f.away_difficulty or 3,
                    is_home=False,
                )
            )

    # 6. Build response
    starting: list[MyTeamPick] = []
    bench: list[MyTeamPick] = []
    total_predicted = Decimal("0")

    for pick in picks:
        pid = pick["element"]
        db_data = player_map.get(pid)

        if db_data:
            player, team_short, team_code, form = db_data
            predicted = pred_lookup.get(pid)
            team_pick = MyTeamPick(
                player_id=pid,
                web_name=player.web_name,
                shirt_url=shirt_url(team_code, player.position),
                team_short_name=team_short,
                position=player.position,
                slot=pick["position"],
                is_captain=pick["is_captain"],
                is_vice_captain=pick["is_vice_captain"],
                multiplier=pick["multiplier"],
                now_cost=player.now_cost,
                form_points=form.total_points if form else None,
                predicted_points=predicted,
                fixtures=team_fixtures.get(player.team_id, [])[:3],
            )
        else:
            # Player not in our DB — minimal info
            team_pick = MyTeamPick(
                player_id=pid,
                web_name=f"Player {pid}",
                position=pick.get("element_type", 4),
                team_short_name="???",
                shirt_url=None,
                slot=pick["position"],
                is_captain=pick["is_captain"],
                is_vice_captain=pick["is_vice_captain"],
                multiplier=pick["multiplier"],
                now_cost=0,
            )
            predicted = None

        if pick["position"] <= 11:
            starting.append(team_pick)
            if predicted:
                pts = Decimal(str(predicted)) * pick["multiplier"]
                total_predicted += pts
        else:
            bench.append(team_pick)

    # Get team name from leagues
    team_name = "My Team"
    for league in manager.get("leagues", {}).get("classic", []):
        if league.get("entry_can_admin"):
            team_name = league.get("name", team_name)
            break

    # Try player name fields
    first = manager.get("player_first_name", "")
    last = manager.get("player_last_name", "")
    mgr_name = f"{first} {last}".strip() or "Unknown"

    # Entry name from summary
    team_name = manager.get("name", team_name)

    return APIResponse(
        data=MyTeamResponse(
            manager_name=mgr_name,
            team_name=team_name,
            overall_rank=manager.get("summary_overall_rank", 0),
            overall_points=manager.get("summary_overall_points", 0),
            gameweek_points=entry_history.get("points", 0),
            gameweek_id=current_event,
            next_gameweek_id=next_gw or 0,
            bank=entry_history.get("bank", 0),
            team_value=entry_history.get("value", 0),
            starting=starting,
            bench=bench,
            total_predicted=round(total_predicted, 1),
        )
    )


@router.get(
    "/my-team/{manager_id}/transfers",
    response_model=APIResponse[TransferPlan],
)
@cached("my-team:transfers", ttl_seconds=1800)
async def get_transfer_suggestions(
    manager_id: int = Path(..., ge=1, le=100_000_000),
    session: AsyncSession = Depends(get_session),
) -> APIResponse[TransferPlan]:
    """Suggest optimal transfers for a manager's squad."""
    # 1. Fetch squad from FPL API
    try:
        manager = await fetch_manager_info(manager_id)
    except Exception as exc:
        raise HTTPException(
            status_code=404, detail="Manager not found"
        ) from exc

    current_event = manager.get("current_event")
    if not current_event:
        raise HTTPException(status_code=400, detail="No active gameweek")

    try:
        picks_data = await fetch_manager_picks(manager_id, current_event)
    except Exception as exc:
        raise HTTPException(
            status_code=404, detail="Picks not found"
        ) from exc

    picks = picks_data.get("picks", [])
    entry_history = picks_data.get("entry_history", {})
    bank = entry_history.get("bank", 0)
    free_transfers = entry_history.get("event_transfers", 0)
    # FPL API doesn't expose remaining FTs directly; estimate from transfers made
    # Managers get 1 FT per GW (max 5 banked). If 0 made, assume 1 available.
    free_transfers_remaining = max(1, 2 - free_transfers)
    player_ids = [p["element"] for p in picks]

    # 2. Look up squad players in DB
    result = await session.execute(
        select(
            Player, Team.short_name, Team.code.label("team_code"),
            PlayerFormCache,
        )
        .join(Team, Player.team_id == Team.id)
        .outerjoin(
            PlayerFormCache,
            (PlayerFormCache.player_id == Player.id)
            & (PlayerFormCache.gw_window == 6),
        )
        .where(Player.id.in_(player_ids))
    )
    rows = result.all()
    player_map = {p.id: (p, ts, tc, f) for p, ts, tc, f in rows}

    # 3. Get predictions for all players (next 5 GWs)
    pred_list = await asyncio.to_thread(predict_upcoming, 5)
    pred_lookup = {
        p["player_id"]: p["predicted_points"] for p in pred_list
    }

    # 4. Get upcoming fixtures
    next_gw_result = await session.execute(
        select(Gameweek.id)
        .where(Gameweek.is_next == True)  # noqa: E712
        .limit(1)
    )
    next_gw = next_gw_result.scalar()

    team_fixtures: dict[int, list[FixturePreview]] = {}
    if next_gw:
        teams_result = await session.execute(
            select(Team.id, Team.short_name)
        )
        team_names = {tid: sn for tid, sn in teams_result.all()}

        fix_result = await session.execute(
            select(Fixture).where(
                Fixture.gameweek_id >= next_gw,
                Fixture.gameweek_id <= next_gw + 4,
                Fixture.gameweek_id.isnot(None),
            )
        )
        for f in fix_result.scalars().all():
            team_fixtures.setdefault(f.home_team_id, []).append(
                FixturePreview(
                    opponent=team_names.get(f.away_team_id, "???"),
                    difficulty=f.home_difficulty or 3,
                    is_home=True,
                )
            )
            team_fixtures.setdefault(f.away_team_id, []).append(
                FixturePreview(
                    opponent=team_names.get(f.home_team_id, "???"),
                    difficulty=f.away_difficulty or 3,
                    is_home=False,
                )
            )

    # 5. Build squad dicts for engine
    squad: list[dict] = []
    missing_ids: list[int] = []
    for pick in picks:
        pid = pick["element"]
        db_data = player_map.get(pid)
        if not db_data:
            missing_ids.append(pid)
            continue
        player, team_short, team_code, _form = db_data
        squad.append({
            "player_id": pid,
            "web_name": player.web_name,
            "shirt_url": shirt_url(team_code, player.position),
            "team_short_name": team_short,
            "position": player.position,
            "now_cost": player.now_cost,
            "predicted_points": pred_lookup.get(pid, Decimal("0")),
            "fixtures": team_fixtures.get(player.team_id, [])[:5],
        })

    if missing_ids:
        logger.warning(
            "Transfer suggestions: %d squad players not in DB: %s",
            len(missing_ids),
            missing_ids,
        )

    # 6. Build candidate pool — all active players with predictions
    all_result = await session.execute(
        select(
            Player, Team.short_name, Team.code.label("team_code"),
        )
        .join(Team, Player.team_id == Team.id)
        .where(Player.status.in_({"a", "d"}))
    )
    candidates: list[dict] = []
    for player, team_short, team_code in all_result.all():
        pred = pred_lookup.get(player.id)
        if not pred:
            continue
        candidates.append({
            "player_id": player.id,
            "web_name": player.web_name,
            "shirt_url": shirt_url(team_code, player.position),
            "team_short_name": team_short,
            "position": player.position,
            "now_cost": player.now_cost,
            "predicted_points": pred,
            "fixtures": team_fixtures.get(player.team_id, [])[:5],
        })

    # 7. Run engine
    suggestions = await asyncio.to_thread(
        suggest_transfers,
        squad=squad,
        bank=bank,
        candidates=candidates,
        free_transfers=free_transfers_remaining,
    )

    return APIResponse(
        data=TransferPlan(
            suggestions=suggestions,
            bank=bank,
            free_transfers=free_transfers_remaining,
        )
    )
