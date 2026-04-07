"""Decision support endpoints — buys, captains, chips, differentials."""

import asyncio
import datetime as dt
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cached
from app.core.database import get_session
from app.models.fixture import Fixture
from app.models.gameweek import Gameweek
from app.models.player import Player
from app.models.player_form_cache import PlayerFormCache
from app.models.player_gw_stats import PlayerGWStats
from app.models.player_prices import PlayerPrice
from app.models.team import Team
from app.schemas.common import APIResponse
from app.schemas.decision import (
    BuyCandidate,
    CaptainPick,
    ChipAdvice,
    DifferentialPick,
    OvernightChange,
    OvernightChanges,
    PriceChangeCandidate,
    PriceChangePrediction,
)
from app.services.fpl_urls import shirt_url
from app.services.points_model import predict_upcoming

router = APIRouter(prefix="/decisions", tags=["decisions"])


async def _get_next_gw(session: AsyncSession) -> int | None:
    result = await session.execute(
        select(Gameweek.id).where(Gameweek.is_next == True)  # noqa: E712
    )
    row = result.first()
    return row[0] if row else None


async def _get_fdr_upcoming(
    session: AsyncSession, next_gw: int, horizon: int = 5
) -> tuple[dict[int, Decimal], int]:
    """Get average FDR for each team across the next N unfinished GWs.

    Returns (fdr_map, actual_horizon) where actual_horizon may be < horizon
    at end of season.
    """
    gw_result = await session.execute(
        select(Gameweek.id)
        .where(Gameweek.id >= next_gw, Gameweek.is_finished == False)  # noqa: E712
        .order_by(Gameweek.id)
        .limit(horizon)
    )
    gw_ids = [row[0] for row in gw_result.all()]

    if not gw_ids:
        return {}, 0

    result = await session.execute(
        select(Fixture).where(
            Fixture.gameweek_id.in_(gw_ids),
            Fixture.gameweek_id.isnot(None),
        )
    )
    fixtures = result.scalars().all()

    team_fdrs: dict[int, list[int]] = {}
    for f in fixtures:
        if f.home_difficulty is not None:
            team_fdrs.setdefault(f.home_team_id, []).append(f.home_difficulty)
        if f.away_difficulty is not None:
            team_fdrs.setdefault(f.away_team_id, []).append(f.away_difficulty)

    fdr_map = {
        tid: Decimal(str(round(sum(fdrs) / len(fdrs), 2)))
        for tid, fdrs in team_fdrs.items()
        if fdrs
    }
    return fdr_map, len(gw_ids)


@router.get("/buys", response_model=APIResponse[list[BuyCandidate]])
@cached("decisions:buys", ttl_seconds=300)
async def get_buy_candidates(
    position: int | None = Query(None, ge=1, le=4),
    max_cost: int | None = Query(None, description="Max price in tenths"),
    limit: int = Query(30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> APIResponse[list[BuyCandidate]]:
    stmt = (
        select(Player, Team.short_name, Team.code.label("team_code"), PlayerFormCache)
        .join(Team, Player.team_id == Team.id)
        .join(
            PlayerFormCache,
            (PlayerFormCache.player_id == Player.id) & (PlayerFormCache.gw_window == 6),
        )
        .where(
            Player.status == "a",
            PlayerFormCache.minutes_pct > 50,
            (Player.chance_of_playing_next_round >= 50)
            | (Player.chance_of_playing_next_round.is_(None)),
        )
    )
    if position:
        stmt = stmt.where(Player.position == position)
    if max_cost:
        stmt = stmt.where(Player.now_cost <= max_cost)

    result = await session.execute(stmt)
    rows = result.all()

    next_gw = await _get_next_gw(session)
    fdr_map, actual_horizon = (
        await _get_fdr_upcoming(session, next_gw) if next_gw else ({}, 0)
    )

    # Get predicted points across the horizon
    pred_list = await asyncio.to_thread(predict_upcoming, actual_horizon or 5)
    pred_lookup = {p["player_id"]: p["predicted_points"] for p in pred_list}

    candidates = []
    for player, team_short, team_code, form in rows:
        cost_m = Decimal(player.now_cost) / 10
        ppm = Decimal(form.total_points) / cost_m if cost_m > 0 else Decimal("0")
        candidates.append(
            BuyCandidate(
                player_id=player.id,
                web_name=player.web_name,
                first_name=player.first_name,
                second_name=player.second_name,
                shirt_url=shirt_url(team_code, player.position),
                team_short_name=team_short,
                position=player.position,
                now_cost=player.now_cost,
                form_points=form.total_points,
                pts_per_game=form.pts_per_game,
                xgi_per_90=form.xgi_per_90,
                minutes_pct=form.minutes_pct,
                ppm=round(ppm, 2),
                fdr_next_5=fdr_map.get(player.team_id),
                predicted_points=pred_lookup.get(player.id),
                selected_by_percent=player.selected_by_percent,
                transfers_in_event=player.transfers_in_event,
                recommendation=_buy_recommendation(
                    form, fdr_map.get(player.team_id), player, ppm
                ),
            )
        )

    def rank_score(c: BuyCandidate) -> float:
        xgi = float(c.xgi_per_90)
        ppm = float(c.ppm)
        form = float(c.form_points) / 10
        fdr_penalty = float(c.fdr_next_5 or Decimal("3")) / 5
        return (xgi * 0.4) + (ppm * 0.3) + (form * 0.3) - (fdr_penalty * 0.1)

    candidates.sort(key=rank_score, reverse=True)
    return APIResponse(data=candidates[:limit])


@router.get("/captains", response_model=APIResponse[list[CaptainPick]])
@cached("decisions:captains", ttl_seconds=300)
async def get_captain_picks(
    limit: int = Query(15, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> APIResponse[list[CaptainPick]]:
    next_gw = await _get_next_gw(session)

    stmt = (
        select(Player, Team.short_name, Team.code.label("team_code"), PlayerFormCache)
        .join(Team, Player.team_id == Team.id)
        .join(
            PlayerFormCache,
            (PlayerFormCache.player_id == Player.id) & (PlayerFormCache.gw_window == 6),
        )
        .where(
            Player.status == "a",
            PlayerFormCache.minutes_pct > 50,
            (Player.chance_of_playing_next_round >= 50)
            | (Player.chance_of_playing_next_round.is_(None)),
        )
    )
    result = await session.execute(stmt)
    rows = result.all()

    # Ceiling scores (max in last 10 GWs)
    current_result = await session.execute(
        select(Gameweek.id).where(Gameweek.is_current == True)  # noqa: E712
    )
    current_gw = current_result.scalar()

    ceilings: dict[int, int] = {}
    if current_gw is not None:
        ceiling_result = await session.execute(
            select(
                PlayerGWStats.player_id,
                func.max(PlayerGWStats.total_points),
            )
            .where(PlayerGWStats.gameweek_id > current_gw - 10)
            .group_by(PlayerGWStats.player_id)
        )
        ceilings = {pid: ceil for pid, ceil in ceiling_result.all()}

    # Next GW fixture info
    next_fixtures: dict[int, dict] = {}
    if next_gw:
        fix_result = await session.execute(
            select(Fixture, Gameweek.is_double)
            .outerjoin(Gameweek, Fixture.gameweek_id == Gameweek.id)
            .where(Fixture.gameweek_id == next_gw)
        )
        for fix, is_double in fix_result.all():
            next_fixtures[fix.home_team_id] = {
                "is_home": True,
                "is_double": is_double or False,
            }
            if fix.away_team_id not in next_fixtures:
                next_fixtures[fix.away_team_id] = {
                    "is_home": False,
                    "is_double": is_double or False,
                }

    picks = []
    for player, team_short, team_code, form in rows:
        fi = next_fixtures.get(player.team_id, {})
        picks.append(
            CaptainPick(
                player_id=player.id,
                web_name=player.web_name,
                first_name=player.first_name,
                second_name=player.second_name,
                shirt_url=shirt_url(team_code, player.position),
                team_short_name=team_short,
                position=player.position,
                now_cost=player.now_cost,
                ceiling_score=ceilings.get(player.id, 0),
                bps_avg=form.bps_avg,
                form_points=form.total_points,
                is_home=fi.get("is_home"),
                is_double_gw=fi.get("is_double", False),
                is_penalty_taker=player.is_penalty_taker,
                is_set_piece_taker=player.is_set_piece_taker,
                recommendation=_captain_recommendation(
                    player, form, ceilings.get(player.id, 0), fi
                ),
            )
        )

    def rank_score(c: CaptainPick) -> float:
        return (
            (float(c.ceiling_score) / 20 * 0.4)
            + (float(c.form_points) / 10 * 0.3)
            + (float(c.bps_avg) / 30 * 0.2)
            + (0.05 if c.is_home else 0)
            + (1.0 if c.is_double_gw else 0)
        )

    picks.sort(key=rank_score, reverse=True)
    return APIResponse(data=picks[:limit])


@router.get("/chips", response_model=APIResponse[list[ChipAdvice]])
@cached("decisions:chips", ttl_seconds=600)
async def get_chip_advice(
    session: AsyncSession = Depends(get_session),
) -> APIResponse[list[ChipAdvice]]:
    result = await session.execute(
        select(Gameweek).where(Gameweek.is_finished == False).order_by(Gameweek.id)  # noqa: E712
    )
    gws = result.scalars().all()

    return APIResponse(
        data=[
            ChipAdvice(
                gameweek_id=gw.id,
                name=gw.name,
                is_double=gw.is_double,
                is_blank=gw.is_blank,
                recommendation=(
                    "Bench Boost or Triple Captain candidate"
                    if gw.is_double
                    else "Free Hit candidate"
                    if gw.is_blank
                    else None
                ),
            )
            for gw in gws
        ]
    )


@router.get("/differentials", response_model=APIResponse[list[DifferentialPick]])
@cached("decisions:differentials", ttl_seconds=300)
async def get_differentials(
    max_ownership: Decimal = Query(Decimal("5.0")),
    limit: int = Query(20, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> APIResponse[list[DifferentialPick]]:
    stmt = (
        select(Player, Team.short_name, Team.code.label("team_code"), PlayerFormCache)
        .join(Team, Player.team_id == Team.id)
        .join(
            PlayerFormCache,
            (PlayerFormCache.player_id == Player.id) & (PlayerFormCache.gw_window == 6),
        )
        .where(
            Player.status == "a",
            PlayerFormCache.minutes_pct > 50,
            PlayerFormCache.total_points > 10,
            (Player.chance_of_playing_next_round >= 50)
            | (Player.chance_of_playing_next_round.is_(None)),
        )
    )
    result = await session.execute(stmt)
    rows = result.all()

    prices_result = await session.execute(
        select(PlayerPrice.player_id, PlayerPrice.selected_by_percent)
        .distinct(PlayerPrice.player_id)
        .order_by(PlayerPrice.player_id, PlayerPrice.recorded_at.desc())
    )
    ownership = {pid: pct for pid, pct in prices_result.all()}

    picks = []
    for player, team_short, team_code, form in rows:
        own_pct = ownership.get(player.id, Decimal("0"))
        if own_pct > max_ownership:
            continue
        picks.append(
            DifferentialPick(
                player_id=player.id,
                web_name=player.web_name,
                first_name=player.first_name,
                second_name=player.second_name,
                shirt_url=shirt_url(team_code, player.position),
                team_short_name=team_short,
                position=player.position,
                now_cost=player.now_cost,
                selected_by_percent=own_pct,
                form_points=form.total_points,
                xgi_per_90=form.xgi_per_90,
            )
        )

    picks.sort(key=lambda p: float(p.xgi_per_90), reverse=True)
    return APIResponse(data=picks[:limit])


@router.get("/price-changes", response_model=APIResponse[PriceChangePrediction])
@cached("decisions:prices", ttl_seconds=600)
async def get_price_changes(
    session: AsyncSession = Depends(get_session),
) -> APIResponse[PriceChangePrediction]:
    """Predict which players are likely to rise or fall in price tonight."""

    from app.models.transfer_snapshot import TransferSnapshot
    from app.services.price_change import (
        MIN_NET_FOR_DISPLAY,
        compute_progress,
        compute_target,
        compute_velocity,
    )

    # Fetch players
    stmt = select(Player, Team.short_name, Team.code.label("team_code")).join(
        Team, Player.team_id == Team.id
    )
    result = await session.execute(stmt)
    rows = result.all()

    # Fetch today's transfer snapshots for velocity
    today_start = dt.datetime.now(dt.UTC).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    snap_result = await session.execute(
        select(TransferSnapshot)
        .where(TransferSnapshot.recorded_at >= today_start)
        .order_by(TransferSnapshot.player_id, TransferSnapshot.recorded_at)
    )
    snapshots = snap_result.scalars().all()

    # Build velocity lookup: player_id -> [(net, hours)]
    snap_by_player: dict[int, list[tuple[int, float]]] = {}
    for snap in snapshots:
        hours = snap.recorded_at.hour + snap.recorded_at.minute / 60.0
        snap_by_player.setdefault(snap.player_id, []).append(
            (snap.net_transfers, hours)
        )

    risers: list[PriceChangeCandidate] = []
    fallers: list[PriceChangeCandidate] = []
    changed: list[PriceChangeCandidate] = []
    last_updated: str | None = None

    for player, team_short, team_code in rows:
        net = player.transfers_in_event - player.transfers_out_event
        abs_net = abs(net)
        is_changed = player.cost_change_event != 0

        if abs_net < MIN_NET_FOR_DISPLAY and not is_changed:
            continue

        target = compute_target(player.selected_by_percent)
        progress = compute_progress(net, target)
        velocity = compute_velocity(snap_by_player.get(player.id, []))

        if progress >= 90:
            likelihood = "very_likely"
        elif progress >= 60:
            likelihood = "likely"
        else:
            likelihood = "possible"

        predicted_price = (
            None
            if is_changed
            else player.now_cost + (1 if net > 0 else -1)
        )

        candidate = PriceChangeCandidate(
            player_id=player.id,
            web_name=player.web_name,
            shirt_url=shirt_url(team_code, player.position),
            team_short_name=team_short,
            position=player.position,
            now_cost=player.now_cost,
            selected_by_percent=player.selected_by_percent,
            transfers_in_event=player.transfers_in_event,
            transfers_out_event=player.transfers_out_event,
            net_transfers=net,
            cost_change_event=player.cost_change_event,
            likelihood=likelihood,
            target=target,
            progress=Decimal(str(progress)),
            velocity=velocity,
            already_changed=is_changed,
            predicted_price=predicted_price,
        )

        if is_changed:
            changed.append(candidate)
        elif net > 0:
            risers.append(candidate)
        else:
            fallers.append(candidate)

        if last_updated is None or (
            player.updated_at and player.updated_at.isoformat() > (last_updated or "")
        ):
            last_updated = (
                player.updated_at.isoformat() + "Z"
                if player.updated_at and not player.updated_at.tzinfo
                else player.updated_at.isoformat()
                if player.updated_at
                else None
            )

    risers.sort(key=lambda c: float(c.progress), reverse=True)
    fallers.sort(key=lambda c: float(c.progress), reverse=True)

    return APIResponse(
        data=PriceChangePrediction(
            risers=risers,
            fallers=fallers,
            already_changed=changed,
            last_updated=last_updated,
        )
    )


def _is_snapshot_fresh(snapshot_date: dt.date) -> bool:
    """Check if a snapshot date is recent enough to display (today or yesterday)."""
    today = dt.datetime.now(dt.UTC).date()
    age = (today - snapshot_date).days
    return age <= 1


@router.get(
    "/overnight-changes",
    response_model=APIResponse[OvernightChanges],
)
@cached("decisions:overnight", ttl_seconds=300)
async def get_overnight_changes(
    session: AsyncSession = Depends(get_session),
) -> APIResponse[OvernightChanges]:
    """Compare the two most recent price snapshots to find overnight changes."""
    # Find the two most recent distinct snapshot dates
    dates_result = await session.execute(
        select(PlayerPrice.recorded_at)
        .distinct()
        .order_by(PlayerPrice.recorded_at.desc())
        .limit(2)
    )
    dates = [row[0] for row in dates_result.all()]

    if len(dates) < 2:
        # Not enough data — fall back to current cost_change_event
        return await _overnight_from_cost_change(session)

    latest_date, prev_date = dates[0], dates[1]

    # If snapshots are stale (>1 day old), return empty — don't show old data
    if not _is_snapshot_fresh(latest_date):
        return APIResponse(
            data=OvernightChanges(
                risers=[], fallers=[], date=latest_date.isoformat()
            )
        )

    # Get both snapshots
    latest_result = await session.execute(
        select(PlayerPrice).where(PlayerPrice.recorded_at == latest_date)
    )
    latest_prices = {
        p.player_id: p.cost for p in latest_result.scalars().all()
    }

    prev_result = await session.execute(
        select(PlayerPrice).where(PlayerPrice.recorded_at == prev_date)
    )
    prev_prices = {
        p.player_id: p.cost for p in prev_result.scalars().all()
    }

    if not latest_prices or not prev_prices:
        return APIResponse(
            data=OvernightChanges(
                risers=[], fallers=[], date=latest_date.isoformat()
            )
        )

    # Find changes
    changed_ids = [
        pid
        for pid in latest_prices
        if pid in prev_prices and latest_prices[pid] != prev_prices[pid]
    ]

    if not changed_ids:
        return APIResponse(
            data=OvernightChanges(
                risers=[], fallers=[], date=latest_date.isoformat()
            )
        )

    # Fetch player info for changed players
    player_result = await session.execute(
        select(Player, Team.short_name, Team.code.label("team_code"))
        .join(Team, Player.team_id == Team.id)
        .where(Player.id.in_(changed_ids))
    )

    risers: list[OvernightChange] = []
    fallers: list[OvernightChange] = []

    for player, team_short, team_code in player_result.all():
        old = prev_prices[player.id]
        new = latest_prices[player.id]
        change = new - old
        entry = OvernightChange(
            player_id=player.id,
            web_name=player.web_name,
            shirt_url=shirt_url(team_code, player.position),
            team_short_name=team_short,
            position=player.position,
            old_price=old,
            new_price=new,
            change=change,
        )
        if change > 0:
            risers.append(entry)
        else:
            fallers.append(entry)

    risers.sort(key=lambda c: c.change, reverse=True)
    fallers.sort(key=lambda c: c.change)

    return APIResponse(
        data=OvernightChanges(
            risers=risers, fallers=fallers, date=latest_date.isoformat()
        )
    )


async def _overnight_from_cost_change(
    session: AsyncSession,
) -> APIResponse[OvernightChanges]:
    """Fallback: use cost_change_event when only 1 snapshot exists."""

    result = await session.execute(
        select(Player, Team.short_name, Team.code.label("team_code"))
        .join(Team, Player.team_id == Team.id)
        .where(Player.cost_change_event != 0)
    )

    risers: list[OvernightChange] = []
    fallers: list[OvernightChange] = []

    for player, team_short, team_code in result.all():
        change = player.cost_change_event
        entry = OvernightChange(
            player_id=player.id,
            web_name=player.web_name,
            shirt_url=shirt_url(team_code, player.position),
            team_short_name=team_short,
            position=player.position,
            old_price=player.now_cost - change,
            new_price=player.now_cost,
            change=change,
        )
        if change > 0:
            risers.append(entry)
        else:
            fallers.append(entry)

    risers.sort(key=lambda c: c.change, reverse=True)
    fallers.sort(key=lambda c: c.change)

    return APIResponse(
        data=OvernightChanges(
            risers=risers,
            fallers=fallers,
            date=dt.datetime.now(dt.UTC).date().isoformat(),
        )
    )


def _buy_recommendation(
    form: "PlayerFormCache",  # type: ignore[name-defined]
    fdr: Decimal | None,
    player: "Player",  # type: ignore[name-defined]
    ppm: Decimal,
) -> str:
    """Generate a plain English buy recommendation."""
    parts: list[str] = []

    if fdr is not None and float(fdr) <= 2.5:
        parts.append("easy fixtures ahead")
    elif fdr is not None and float(fdr) >= 3.5:
        parts.append("tough fixtures ahead")

    if form.total_points >= 30:
        parts.append("in great form")
    elif form.total_points >= 20:
        parts.append("decent recent form")

    if float(form.xgi_per_90) >= 0.5:
        parts.append("strong underlying stats")

    if player.transfers_in_event > 10000:
        parts.append("trending transfer target")

    if float(ppm) >= 5:
        parts.append("excellent value for money")

    if player.is_penalty_taker:
        parts.append("penalty taker")

    if not parts:
        parts.append("steady option")

    head = parts[0].capitalize()
    tail = ", ".join(parts[1:])
    return f"{head}, {tail}" if tail else head


def _captain_recommendation(
    player: "Player",  # type: ignore[name-defined]
    form: "PlayerFormCache",  # type: ignore[name-defined]
    ceiling: int,
    fixture_info: dict,
) -> str:
    """Generate a plain English captain recommendation."""
    parts: list[str] = []

    if fixture_info.get("is_double"):
        parts.append("double gameweek — plays twice")
    elif fixture_info.get("is_home"):
        parts.append("home fixture")
    else:
        parts.append("away fixture")

    if ceiling >= 15:
        parts.append(f"ceiling of {ceiling} pts shows explosive potential")
    elif ceiling >= 10:
        parts.append(f"ceiling of {ceiling} pts")

    if form.total_points >= 30:
        parts.append(f"{form.total_points} pts in last 6 GWs")

    if player.is_penalty_taker:
        parts.append("on penalties")

    if player.is_set_piece_taker:
        parts.append("takes set pieces")

    return ". ".join(p.capitalize() if i == 0 else p for i, p in enumerate(parts))
