"""Celery task definitions for FPL data ingestion."""

import asyncio
import logging

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert

from app.core.database import sync_session_factory
from app.models.fixture import Fixture
from app.models.gameweek import Gameweek
from app.models.player import Player
from app.models.player_gw_stats import PlayerGWStats
from app.models.player_prices import PlayerPrice
from app.models.team import Team
from app.services.fpl_client import (
    fetch_bootstrap,
    fetch_fixtures,
    fetch_player_summary,
)
from worker.celery_app import celery_app
from worker.normaliser import (
    normalise_fixture,
    normalise_gameweek,
    normalise_player,
    normalise_player_gw,
    normalise_price_snapshot,
    normalise_team,
)

logger = logging.getLogger(__name__)


@celery_app.task(name="worker.tasks.sync_bootstrap")
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
            set_={c.name: c for c in stmt.excluded if c.name != "id"},
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
    return counts


@celery_app.task(name="worker.tasks.sync_fixtures")
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
    return {"fixtures": len(fixtures)}


@celery_app.task(name="worker.tasks.sync_player_history")
def sync_player_history() -> dict[str, int]:
    """Fetch GW history for active players and upsert into player_gw_stats.

    Only fetches players with total_points > 0 (from bootstrap data) to
    avoid wasting API calls on players who never played.
    Rate-limited to 1 req/s to avoid FPL API IP bans.
    """
    from app.core.rate_limiter import fpl_limiter

    # Get bootstrap data to filter to active players only
    data = asyncio.run(fetch_bootstrap())
    active_ids = [
        p["id"] for p in data["elements"] if p.get("total_points", 0) > 0
    ]
    logger.info(
        "sync_player_history: %d active players (of %d total)",
        len(active_ids), len(data["elements"]),
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
                logger.warning("Failed to fetch summary for player %d", pid)
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
            min(i + batch_size, len(active_ids)), len(active_ids), total,
        )

    logger.info(
        "sync_player_history complete: %d rows, %d failed fetches",
        total, failed,
    )
    return {"player_gw_stats": total, "failed": failed}


@celery_app.task(name="worker.tasks.sync_price_snapshot")
def sync_price_snapshot() -> dict[str, int]:
    """Take a daily price snapshot from /bootstrap-static/ for all players."""
    data = asyncio.run(fetch_bootstrap())

    rows = [
        normalise_price_snapshot(p["id"], p)
        for p in data["elements"]
    ]

    with sync_session_factory() as session:
        stmt = insert(PlayerPrice).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["player_id", "recorded_at"],
            set_={c.name: c for c in stmt.excluded if c.name != "id"},
        )
        session.execute(stmt)
        session.commit()

    logger.info("sync_price_snapshot complete: %d rows", len(rows))
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
