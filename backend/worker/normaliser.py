"""FPL API response → DB model translation.

Maps the raw JSON from /bootstrap-static/ into dicts suitable for
SQLAlchemy upserts on the teams, players, and gameweeks tables.
"""

from datetime import datetime, timezone
from typing import Any


def normalise_team(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a raw FPL API team object to the teams table columns."""
    return {
        "id": raw["id"],
        "name": raw["name"],
        "short_name": raw["short_name"],
        "strength_overall_home": raw["strength_overall_home"],
        "strength_overall_away": raw["strength_overall_away"],
        "strength_attack_home": raw["strength_attack_home"],
        "strength_attack_away": raw["strength_attack_away"],
        "strength_defence_home": raw["strength_defence_home"],
        "strength_defence_away": raw["strength_defence_away"],
        "updated_at": datetime.now(timezone.utc),
    }


def normalise_player(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a raw FPL API element object to the players table columns."""
    return {
        "id": raw["id"],
        "team_id": raw["team"],
        "web_name": raw["web_name"],
        "first_name": raw["first_name"],
        "second_name": raw["second_name"],
        "position": raw["element_type"],  # 1=GK, 2=DEF, 3=MID, 4=FWD
        "now_cost": raw["now_cost"],
        "status": raw["status"],
        "chance_of_playing_next_round": raw.get("chance_of_playing_next_round"),
        "news": raw.get("news") or None,
        "is_penalty_taker": _is_penalty_taker(raw),
        "is_set_piece_taker": _is_set_piece_taker(raw),
        "updated_at": datetime.now(timezone.utc),
    }


def normalise_gameweek(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a raw FPL API event object to the gameweeks table columns."""
    return {
        "id": raw["id"],
        "name": raw["name"],
        "deadline_time": datetime.fromisoformat(
            raw["deadline_time"].replace("Z", "+00:00")
        ),
        "is_current": raw.get("is_current", False),
        "is_next": raw.get("is_next", False),
        "is_finished": raw.get("finished", False),
        "average_entry_score": raw.get("average_entry_score"),
        "highest_score": raw.get("highest_score"),
    }


def _is_penalty_taker(raw: dict[str, Any]) -> bool:
    """Infer penalty taker status from FPL API fields."""
    order = raw.get("penalties_order")
    return order is not None and order == 1


def _is_set_piece_taker(raw: dict[str, Any]) -> bool:
    """Infer set piece taker status from FPL API fields."""
    order = raw.get("corners_and_indirect_freekicks_order")
    fk_order = raw.get("direct_freekicks_order")
    return (order is not None and order == 1) or (
        fk_order is not None and fk_order == 1
    )
