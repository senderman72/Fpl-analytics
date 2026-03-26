"""Celery task definitions for FPL data ingestion."""

import asyncio
import logging

from sqlalchemy.dialects.postgresql import insert

from app.core.database import sync_session_factory
from app.models.gameweek import Gameweek
from app.models.player import Player
from app.models.team import Team
from app.services.fpl_client import fetch_bootstrap
from worker.celery_app import celery_app
from worker.normaliser import normalise_gameweek, normalise_player, normalise_team

logger = logging.getLogger(__name__)


@celery_app.task(name="worker.tasks.sync_bootstrap")
def sync_bootstrap() -> dict[str, int]:
    """Fetch /bootstrap-static/ and upsert teams, players, and gameweeks.

    Uses INSERT ... ON CONFLICT DO UPDATE so re-runs are idempotent.
    Returns counts of upserted rows.
    """
    data = asyncio.run(fetch_bootstrap())

    teams = [normalise_team(t) for t in data["teams"]]
    players = [normalise_player(p) for p in data["elements"]]
    gameweeks = [normalise_gameweek(gw) for gw in data["events"]]

    with sync_session_factory() as session:
        # Upsert teams
        stmt = insert(Team).values(teams)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={c.name: c for c in stmt.excluded if c.name != "id"},
        )
        session.execute(stmt)

        # Upsert gameweeks
        stmt = insert(Gameweek).values(gameweeks)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={c.name: c for c in stmt.excluded if c.name != "id"},
        )
        session.execute(stmt)

        # Upsert players (depends on teams existing)
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
