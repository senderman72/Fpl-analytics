"""Celery task definitions for FPL data ingestion."""

import asyncio
import datetime as dt
import logging
from decimal import Decimal

import httpx
from sqlalchemy import func, update
from sqlalchemy.dialects.postgresql import insert

from app.core.cache import sync_invalidate_pattern
from app.core.database import sync_session_factory
from app.models.fixture import Fixture
from app.models.gameweek import Gameweek
from app.models.player import Player
from app.models.player_form_cache import PlayerFormCache
from app.models.player_gw_stats import PlayerGWStats
from app.models.player_gw_xg import PlayerSeasonXG
from app.models.player_prices import PlayerPrice
from app.models.team import Team
from app.models.transfer_snapshot import TransferSnapshot
from app.services.fpl_client import (
    fetch_bootstrap,
    fetch_fixtures,
    fetch_live_gw,
    fetch_player_summary,
)
from app.services.understat_client import fetch_league_players
from worker.celery_app import celery_app
from worker.normaliser import (
    match_understat_to_fpl,
    normalise_fixture,
    normalise_gameweek,
    normalise_player,
    normalise_player_gw,
    normalise_price_snapshot,
    normalise_team,
    normalise_transfer_snapshot,
    normalise_understat_season,
)

logger = logging.getLogger(__name__)

# Exception types that warrant automatic task retry
_API_RETRYABLE = (httpx.HTTPStatusError, httpx.TimeoutException, OSError)
_DB_RETRYABLE = (Exception,)


@celery_app.task(
    name="worker.tasks.sync_bootstrap",
    autoretry_for=_API_RETRYABLE,
    max_retries=3,
    retry_backoff=60,
    retry_backoff_max=300,
    retry_jitter=True,
)
def sync_bootstrap() -> dict[str, int]:
    """Fetch /bootstrap-static/ and upsert teams, players, and gameweeks."""
    data = asyncio.run(fetch_bootstrap())

    teams = [normalise_team(t) for t in data["teams"]]
    players = [normalise_player(p) for p in data["elements"]]
    gameweeks = [normalise_gameweek(gw) for gw in data["events"]]

    with sync_session_factory() as session:
        stmt = insert(Team).values(teams)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={c.name: c for c in stmt.excluded if c.name != "id"},
        )
        session.execute(stmt)

        stmt = insert(Gameweek).values(gameweeks)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                c.name: c
                for c in stmt.excluded
                if c.name not in ("id", "is_double", "is_blank")
            },
        )
        session.execute(stmt)

        stmt = insert(Player).values(players)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={c.name: c for c in stmt.excluded if c.name != "id"},
        )
        session.execute(stmt)

        session.commit()

    counts = {
        "teams": len(teams),
        "players": len(players),
        "gameweeks": len(gameweeks),
    }
    logger.info("sync_bootstrap complete: %s", counts)

    sync_invalidate_pattern("players:*")
    sync_invalidate_pattern("gameweeks:*")
    sync_invalidate_pattern("decisions:*")

    warm_caches.delay()

    return counts


@celery_app.task(
    name="worker.tasks.sync_transfer_counts",
    autoretry_for=_API_RETRYABLE,
    max_retries=3,
    retry_backoff=60,
    retry_backoff_max=300,
    retry_jitter=True,
)
def sync_transfer_counts() -> dict[str, int]:
    """Lightweight bootstrap sync: update transfer counts + snapshot velocity."""
    data = asyncio.run(fetch_bootstrap())
    now = dt.datetime.now(dt.UTC)
    snapshot_rows: list[dict] = []

    with sync_session_factory() as session:
        for raw in data["elements"]:
            tin = raw.get("transfers_in_event", 0)
            tout = raw.get("transfers_out_event", 0)
            net = tin - tout

            session.execute(
                update(Player)
                .where(Player.id == raw["id"])
                .values(
                    transfers_in_event=tin,
                    transfers_out_event=tout,
                    selected_by_percent=Decimal(
                        str(raw.get("selected_by_percent", "0"))
                    ),
                    cost_change_event=raw.get("cost_change_event", 0),
                )
            )

            if abs(net) >= 500:
                snapshot_rows.append(
                    normalise_transfer_snapshot(raw["id"], tin, tout, now)
                )

        if snapshot_rows:
            stmt = insert(TransferSnapshot).values(snapshot_rows)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_transfer_snap_player_ts",
                set_={c.name: c for c in stmt.excluded if c.name != "id"},
            )
            session.execute(stmt)

        session.commit()

    sync_invalidate_pattern("decisions:prices*")

    logger.info(
        "sync_transfer_counts complete: %d players, %d snapshots",
        len(data["elements"]),
        len(snapshot_rows),
    )
    return {"players_updated": len(data["elements"]), "snapshots": len(snapshot_rows)}


@celery_app.task(
    name="worker.tasks.sync_fixtures",
    autoretry_for=_API_RETRYABLE,
    max_retries=3,
    retry_backoff=60,
    retry_backoff_max=300,
    retry_jitter=True,
)
def sync_fixtures() -> dict[str, int]:
    """Fetch /fixtures/ and upsert all fixtures. Then detect DGW/BGW."""
    raw_fixtures = asyncio.run(fetch_fixtures())
    fixtures = [normalise_fixture(f) for f in raw_fixtures]

    with sync_session_factory() as session:
        stmt = insert(Fixture).values(fixtures)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={c.name: c for c in stmt.excluded if c.name != "id"},
        )
        session.execute(stmt)
        session.commit()

    # Detect DGW/BGW after fixtures are stored
    _detect_dgw_bgw()

    logger.info("sync_fixtures complete: %d fixtures", len(fixtures))

    sync_invalidate_pattern("fixtures:*")
    sync_invalidate_pattern("decisions:*")
    sync_invalidate_pattern("predictions:*")

    return {"fixtures": len(fixtures)}


@celery_app.task(
    name="worker.tasks.sync_player_history",
    autoretry_for=_API_RETRYABLE,
    max_retries=3,
    retry_backoff=60,
    retry_backoff_max=300,
    retry_jitter=True,
)
def sync_player_history() -> dict[str, int]:
    """Fetch GW history for active players and upsert into player_gw_stats.

    Only fetches players with total_points > 0 (from bootstrap data) to
    avoid wasting API calls on players who never played.
    Rate-limited to 1 req/s to avoid FPL API IP bans.
    """
    from app.core.rate_limiter import fpl_limiter

    # Get bootstrap data to filter to active players only
    data = asyncio.run(fetch_bootstrap())
    active_ids = [p["id"] for p in data["elements"] if p.get("total_points", 0) > 0]
    logger.info(
        "sync_player_history: %d active players (of %d total)",
        len(active_ids),
        len(data["elements"]),
    )

    total = 0
    batch_size = 50
    failed = 0

    for i in range(0, len(active_ids), batch_size):
        batch_ids = active_ids[i : i + batch_size]
        all_rows: list[dict] = []

        for pid in batch_ids:
            fpl_limiter.wait()  # 1 req/s
            try:
                summary = asyncio.run(fetch_player_summary(pid))
            except Exception:
                logger.warning(
                    "Failed to fetch summary for player %d", pid, exc_info=True
                )
                failed += 1
                continue

            for entry in summary.get("history", []):
                all_rows.append(normalise_player_gw(entry))

        if not all_rows:
            continue

        with sync_session_factory() as session:
            stmt = insert(PlayerGWStats).values(all_rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["player_id", "gameweek_id", "fixture_id"],
                set_={c.name: c for c in stmt.excluded if c.name != "id"},
            )
            session.execute(stmt)
            session.commit()

        total += len(all_rows)
        logger.info(
            "sync_player_history: %d/%d players done, %d rows so far",
            min(i + batch_size, len(active_ids)),
            len(active_ids),
            total,
        )

    logger.info(
        "sync_player_history complete: %d rows, %d failed fetches",
        total,
        failed,
    )

    sync_invalidate_pattern("players:history:*")
    sync_invalidate_pattern("players:detail:*")

    return {"player_gw_stats": total, "failed": failed}


@celery_app.task(
    name="worker.tasks.sync_price_snapshot",
    autoretry_for=_API_RETRYABLE,
    max_retries=3,
    retry_backoff=60,
    retry_backoff_max=300,
    retry_jitter=True,
)
def sync_price_snapshot() -> dict[str, int]:
    """Take a daily price snapshot from /bootstrap-static/ for all players."""
    data = asyncio.run(fetch_bootstrap())

    rows = [normalise_price_snapshot(p["id"], p) for p in data["elements"]]

    with sync_session_factory() as session:
        stmt = insert(PlayerPrice).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["player_id", "recorded_at"],
            set_={c.name: c for c in stmt.excluded if c.name != "id"},
        )
        session.execute(stmt)
        session.commit()

    logger.info("sync_price_snapshot complete: %d rows", len(rows))

    sync_invalidate_pattern("decisions:prices:*")

    return {"player_prices": len(rows)}


def _detect_dgw_bgw() -> None:
    """Scan fixtures to set is_double and is_blank flags on gameweeks.

    A gameweek is_double if ANY team has 2+ fixtures in it.
    A gameweek is_blank if ANY team has 0 fixtures in it.
    """
    from collections import Counter

    with sync_session_factory() as session:
        fixtures = (
            session.query(
                Fixture.gameweek_id, Fixture.home_team_id, Fixture.away_team_id
            )
            .filter(Fixture.gameweek_id.isnot(None))
            .all()
        )
        all_team_ids = {t_id for (t_id,) in session.query(Team.id).all()}
        all_gw_ids = [gw_id for (gw_id,) in session.query(Gameweek.id).all()]

        # Count appearances per team per GW
        gw_team_counts: dict[int, Counter[int]] = {}
        for gw_id, home_id, away_id in fixtures:
            counter = gw_team_counts.setdefault(gw_id, Counter())
            counter[home_id] += 1
            counter[away_id] += 1

        for gw_id in all_gw_ids:
            counts = gw_team_counts.get(gw_id, Counter())
            has_double = any(c > 1 for c in counts.values())
            has_blank = len(counts) < len(all_team_ids)

            session.execute(
                update(Gameweek)
                .where(Gameweek.id == gw_id)
                .values(is_double=has_double, is_blank=has_blank)
            )

        session.commit()
        logger.info("DGW/BGW detection complete for %d gameweeks", len(all_gw_ids))


@celery_app.task(
    name="worker.tasks.sync_understat",
    autoretry_for=_API_RETRYABLE,
    max_retries=3,
    retry_backoff=60,
    retry_backoff_max=300,
    retry_jitter=True,
)
def sync_understat(season: str = "2025") -> dict[str, int]:
    """Fetch Understat season xG stats and match to FPL players.

    Uses fuzzy name matching to link Understat → FPL player IDs,
    then stores season-level xG data and updates understat_id on players.
    """
    understat_players = asyncio.run(fetch_league_players(season=season))

    # Build FPL player lookup with team short names
    with sync_session_factory() as session:
        fpl_data = (
            session.query(
                Player.id,
                Player.web_name,
                Player.first_name,
                Player.second_name,
                Team.short_name,
            )
            .join(Team, Player.team_id == Team.id)
            .all()
        )
        fpl_players = [
            {
                "id": pid,
                "web_name": wn,
                "first_name": fn,
                "second_name": sn,
                "team_short_name": tsn,
            }
            for pid, wn, fn, sn, tsn in fpl_data
        ]

    # Match Understat → FPL
    fpl_to_understat = match_understat_to_fpl(understat_players, fpl_players)

    # Build a lookup: understat_id → raw data
    us_by_id = {int(p["id"]): p for p in understat_players}

    # Normalise and upsert
    rows = []
    for fpl_id, us_id in fpl_to_understat.items():
        raw = us_by_id[us_id]
        rows.append(normalise_understat_season(raw, fpl_id, season))

    with sync_session_factory() as session:
        if rows:
            stmt = insert(PlayerSeasonXG).values(rows)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_xg_player_season",
                set_={
                    c.name: c
                    for c in stmt.excluded
                    if c.name not in ("player_id", "season")
                },
            )
            session.execute(stmt)

        # Also update understat_id on the players table
        for fpl_id, us_id in fpl_to_understat.items():
            session.execute(
                update(Player).where(Player.id == fpl_id).values(understat_id=us_id)
            )

        session.commit()

    logger.info(
        "sync_understat complete: %d xG rows, %d players matched",
        len(rows),
        len(fpl_to_understat),
    )

    sync_invalidate_pattern("predictions:*")
    sync_invalidate_pattern("decisions:*")
    sync_invalidate_pattern("players:detail:*")

    return {"player_season_xg": len(rows), "matched": len(fpl_to_understat)}


@celery_app.task(
    name="worker.tasks.recompute_form_cache",
    autoretry_for=_DB_RETRYABLE,
    max_retries=2,
    retry_backoff=30,
    retry_jitter=True,
)
def recompute_form_cache() -> dict[str, int]:
    """Recompute rolling form windows (4, 6, 10 GWs) for all players.

    Reads from player_gw_stats and player_season_xg, writes to player_form_cache.
    """

    with sync_session_factory() as session:
        # Get current GW
        current_gw = (
            session.query(Gameweek.id)
            .filter(Gameweek.is_current == True)  # noqa: E712
            .scalar()
        )
        if current_gw is None:
            # Fallback to latest finished GW
            current_gw = (
                session.query(func.max(Gameweek.id))
                .filter(Gameweek.is_finished == True)  # noqa: E712
                .scalar()
            )
        if current_gw is None:
            logger.warning("No finished gameweeks found, skipping form cache")
            return {"form_rows": 0}

        # Get all player IDs that have stats
        player_ids = [
            pid for (pid,) in session.query(PlayerGWStats.player_id).distinct().all()
        ]

        # Get season xG per-90 for each player
        season_xg: dict[int, Decimal] = {}
        for row in session.query(PlayerSeasonXG).all():
            if row.minutes and row.minutes > 0:
                season_xg[row.player_id] = row.xgi / (Decimal(row.minutes) / 90)
            else:
                season_xg[row.player_id] = Decimal("0")

        all_rows = []
        for window in (4, 6, 10):
            gw_start = max(1, current_gw - window + 1)

            for pid in player_ids:
                stats = (
                    session.query(PlayerGWStats)
                    .filter(
                        PlayerGWStats.player_id == pid,
                        PlayerGWStats.gameweek_id >= gw_start,
                        PlayerGWStats.gameweek_id <= current_gw,
                    )
                    .all()
                )
                if not stats:
                    continue

                total_pts = sum(s.total_points for s in stats)
                total_mins = sum(s.minutes for s in stats)
                games_started = sum(1 for s in stats if s.minutes > 0)
                total_goals = sum(s.goals_scored for s in stats)
                total_assists = sum(s.assists for s in stats)
                total_bonus = sum(s.bonus for s in stats)
                total_bps = sum(s.bps for s in stats)
                total_cs = sum(s.clean_sheets for s in stats)
                total_ict = sum(float(s.ict_index) for s in stats)
                total_threat = sum(float(s.threat) for s in stats)
                total_creativity = sum(float(s.creativity) for s in stats)
                total_saves = sum(s.saves for s in stats)
                total_gc = sum(s.goals_conceded for s in stats)

                pts_per_game = (
                    Decimal(total_pts) / games_started
                    if games_started
                    else Decimal("0")
                )
                pts_per_90 = (
                    Decimal(total_pts) / (Decimal(total_mins) / 90)
                    if total_mins > 0
                    else Decimal("0")
                )
                bps_avg = (
                    Decimal(total_bps) / games_started
                    if games_started
                    else Decimal("0")
                )
                ict_avg = (
                    Decimal(str(total_ict / games_started))
                    if games_started
                    else Decimal("0")
                )
                threat_avg = (
                    Decimal(str(total_threat / games_started))
                    if games_started
                    else Decimal("0")
                )
                creativity_avg = (
                    Decimal(str(total_creativity / games_started))
                    if games_started
                    else Decimal("0")
                )
                saves_avg = (
                    Decimal(str(total_saves / games_started))
                    if games_started
                    else Decimal("0")
                )
                goals_conceded_avg = (
                    Decimal(str(total_gc / games_started))
                    if games_started
                    else Decimal("0")
                )
                available_mins = window * 90
                mins_pct = (
                    Decimal(total_mins) / Decimal(available_mins) * 100
                    if available_mins
                    else Decimal("0")
                )

                all_rows.append(
                    {
                        "player_id": pid,
                        "gw_window": window,
                        "total_points": total_pts,
                        "pts_per_game": round(pts_per_game, 2),
                        "pts_per_90": round(pts_per_90, 2),
                        "xgi_per_90": round(season_xg.get(pid, Decimal("0")), 2),
                        "goals": total_goals,
                        "assists": total_assists,
                        "bonus": total_bonus,
                        "bps_avg": round(bps_avg, 1),
                        "minutes_pct": round(mins_pct, 2),
                        "clean_sheets": total_cs,
                        "ict_avg": round(ict_avg, 1),
                        "threat_avg": round(threat_avg, 1),
                        "creativity_avg": round(creativity_avg, 1),
                        "saves_avg": round(saves_avg, 1),
                        "goals_conceded_avg": round(goals_conceded_avg, 1),
                    }
                )

        # Delete all then insert fresh — ensures stale players are removed
        session.query(PlayerFormCache).delete()

        if all_rows:
            stmt = insert(PlayerFormCache).values(all_rows)
            session.execute(stmt)

        session.commit()

    logger.info("recompute_form_cache complete: %d rows", len(all_rows))

    sync_invalidate_pattern("players:*")
    sync_invalidate_pattern("predictions:*")
    sync_invalidate_pattern("decisions:*")

    warm_caches.delay()

    return {"form_rows": len(all_rows)}


@celery_app.task(
    name="worker.tasks.backfill_actuals",
    autoretry_for=_DB_RETRYABLE,
    max_retries=2,
    retry_backoff=30,
    retry_jitter=True,
)
def backfill_actuals() -> dict[str, int]:
    """Fill actual_points on PredictionLog rows from finished gameweeks."""
    from app.models.prediction_log import PredictionLog

    with sync_session_factory() as session:
        # Find prediction logs missing actual points for finished GWs
        logs = (
            session.query(PredictionLog)
            .join(Gameweek, PredictionLog.gameweek_id == Gameweek.id)
            .filter(
                PredictionLog.actual_points.is_(None),
                Gameweek.is_finished == True,  # noqa: E712
            )
            .all()
        )

        if not logs:
            logger.info("backfill_actuals: no rows to backfill")
            return {"backfilled": 0}

        # Collect (player_id, gw_id) pairs to look up
        keys = {(log.player_id, log.gameweek_id) for log in logs}

        # Sum total_points per (player_id, gw_id) — handles DGWs
        from sqlalchemy import func as sa_func

        actuals = (
            session.query(
                PlayerGWStats.player_id,
                PlayerGWStats.gameweek_id,
                sa_func.sum(PlayerGWStats.total_points).label("total"),
            )
            .filter(
                sa_func.tuple_(
                    PlayerGWStats.player_id, PlayerGWStats.gameweek_id
                ).in_(keys)
            )
            .group_by(PlayerGWStats.player_id, PlayerGWStats.gameweek_id)
            .all()
        )

        actual_map = {(r.player_id, r.gameweek_id): r.total for r in actuals}

        filled = 0
        for log in logs:
            pts = actual_map.get((log.player_id, log.gameweek_id))
            if pts is not None:
                log.actual_points = pts
                filled += 1

        session.commit()

    logger.info("backfill_actuals: filled %d/%d rows", filled, len(logs))

    sync_invalidate_pattern("predictions:accuracy*")

    return {"backfilled": filled}


@celery_app.task(
    name="worker.tasks.run_predictions",
    autoretry_for=_DB_RETRYABLE,
    max_retries=2,
    retry_backoff=30,
    retry_jitter=True,
)
def run_predictions() -> dict[str, int]:
    """Train model and store predictions for the next unfinished GW."""
    from app.services.points_model import (
        predict_gw,
        store_prediction_logs,
        train_model,
    )

    train_model()

    with sync_session_factory() as session:
        next_gw = (
            session.query(Gameweek.id)
            .filter(Gameweek.is_finished == False)  # noqa: E712
            .order_by(Gameweek.id)
            .first()
        )

    if not next_gw:
        logger.warning("run_predictions: no upcoming GW found")
        return {"predictions": 0}

    gw_id = next_gw[0]
    predictions = predict_gw(gw_id)
    stored = store_prediction_logs(predictions, gw_id)

    sync_invalidate_pattern("predictions:*")

    logger.info("run_predictions: GW %d, %d predictions stored", gw_id, stored)
    return {"gw_id": gw_id, "predictions": stored}


@celery_app.task(
    name="worker.tasks.sync_live_gw",
    autoretry_for=_API_RETRYABLE,
    max_retries=3,
    retry_backoff=30,
    retry_backoff_max=120,
    retry_jitter=True,
)
def sync_live_gw() -> dict[str, object]:
    """Fetch live scores for the current GW and cache in Redis.

    Only runs when a GW is in progress (is_current and not finished).
    Stores the raw FPL API response in Redis with a 45s TTL so the
    ``/live/{gw_id}`` endpoint can serve from cache.
    """
    import json

    import redis as sync_redis

    from app.core.config import get_settings

    with sync_session_factory() as session:
        current = (
            session.query(Gameweek.id, Gameweek.is_finished)
            .filter(Gameweek.is_current == True)  # noqa: E712
            .first()
        )

    if current is None or current.is_finished:
        return {"status": "skipped", "reason": "no active GW"}

    gw_id = current.id
    live_data = asyncio.run(fetch_live_gw(gw_id))

    settings = get_settings()
    client = None
    try:
        client = sync_redis.from_url(
            settings.redis_url, decode_responses=True,
        )
        client.set(
            f"live:gw:{gw_id}",
            json.dumps(live_data),
            ex=45,
        )
    except Exception:
        logger.warning(
            "sync_live_gw: Redis store failed for GW %d",
            gw_id,
            exc_info=True,
        )
    finally:
        if client is not None:
            client.close()

    player_count = len(live_data.get("elements", []))
    logger.info(
        "sync_live_gw: cached GW %d (%d players)",
        gw_id,
        player_count,
    )
    return {"gw_id": gw_id, "players": player_count}


@celery_app.task(name="worker.tasks.heartbeat")
def heartbeat() -> dict[str, str]:
    """Write a timestamp to Redis to prove beat + worker are running."""
    import redis as sync_redis

    from app.core.config import get_settings

    settings = get_settings()
    client = sync_redis.from_url(settings.redis_url, decode_responses=True)
    try:
        client.set(
            "celery:heartbeat",
            dt.datetime.now(dt.UTC).isoformat(),
            ex=300,
        )
    finally:
        client.close()
    return {"status": "ok"}


@celery_app.task(
    name="worker.tasks.warm_caches",
    autoretry_for=_DB_RETRYABLE,
    max_retries=2,
    retry_backoff=30,
    retry_jitter=True,
)
def warm_caches() -> dict[str, int]:
    """Hit key API endpoints to pre-populate Redis cache after data sync.

    Called as the final step after data sync tasks complete.
    Uses INTERNAL_API_URL (defaults to http://localhost:8000).
    """
    import httpx

    from app.core.config import get_settings

    base = get_settings().internal_api_url.rstrip("/")

    endpoints = [
        "/gameweeks",
        "/fixtures",
        "/players?sort_by=form_points&limit=50",
        "/players/ids",
        "/decisions/buys?limit=30",
        "/decisions/captains?limit=10",
        "/decisions/chips",
        "/decisions/differentials?limit=20",
        "/decisions/price-changes",
        "/predictions/upcoming?horizon=5&limit=50",
    ]

    warmed = 0
    with httpx.Client(timeout=30.0) as client:
        for path in endpoints:
            try:
                resp = client.get(f"{base}{path}")
                if resp.status_code == 200:
                    warmed += 1
                else:
                    logger.warning("Cache warm failed %s: %d", path, resp.status_code)
            except Exception:
                logger.warning("Cache warm error for %s", path, exc_info=True)

    logger.info("warm_caches complete: %d/%d endpoints", warmed, len(endpoints))
    return {"warmed": warmed, "total": len(endpoints)}
