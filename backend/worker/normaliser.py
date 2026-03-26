"""FPL API response → DB model translation.

Maps raw JSON from the FPL API into dicts suitable for
SQLAlchemy upserts on the corresponding tables.
"""

import datetime as dt
from decimal import Decimal
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
        "updated_at": dt.datetime.now(dt.timezone.utc),
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
        "updated_at": dt.datetime.now(dt.timezone.utc),
    }


def normalise_gameweek(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a raw FPL API event object to the gameweeks table columns."""
    return {
        "id": raw["id"],
        "name": raw["name"],
        "deadline_time": dt.datetime.fromisoformat(
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


def normalise_fixture(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a raw FPL API fixture object to the fixtures table columns."""
    kickoff = raw.get("kickoff_time")
    return {
        "id": raw["id"],
        "gameweek_id": raw.get("event"),  # null for postponed
        "home_team_id": raw["team_h"],
        "away_team_id": raw["team_a"],
        "kickoff_time": (
            dt.datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
            if kickoff
            else None
        ),
        "started": raw.get("started") or False,
        "finished": raw.get("finished", False),
        "finished_provisional": raw.get("finished_provisional", False),
        "home_goals": raw.get("team_h_score"),
        "away_goals": raw.get("team_a_score"),
        "home_difficulty": raw.get("team_h_difficulty"),
        "away_difficulty": raw.get("team_a_difficulty"),
    }


def normalise_player_gw(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a player history entry from /element-summary/ to player_gw_stats."""
    return {
        "player_id": raw["element"],
        "gameweek_id": raw["round"],
        "fixture_id": raw["fixture"],
        "minutes": raw["minutes"],
        "goals_scored": raw["goals_scored"],
        "assists": raw["assists"],
        "clean_sheets": raw["clean_sheets"],
        "goals_conceded": raw["goals_conceded"],
        "own_goals": raw["own_goals"],
        "penalties_saved": raw["penalties_saved"],
        "penalties_missed": raw["penalties_missed"],
        "yellow_cards": raw["yellow_cards"],
        "red_cards": raw["red_cards"],
        "saves": raw["saves"],
        "bonus": raw["bonus"],
        "bps": raw["bps"],
        "influence": Decimal(raw["influence"]),
        "creativity": Decimal(raw["creativity"]),
        "threat": Decimal(raw["threat"]),
        "ict_index": Decimal(raw["ict_index"]),
        "total_points": raw["total_points"],
        "transfers_in": raw["transfers_in"],
        "transfers_out": raw["transfers_out"],
        "selected_by_percent": Decimal("0"),  # not in per-GW history
        "value": raw["value"],
    }


def normalise_price_snapshot(
    player_id: int, raw: dict[str, Any]
) -> dict[str, Any]:
    """Map bootstrap player data to a daily player_prices row."""
    return {
        "player_id": player_id,
        "recorded_at": dt.date.today(),
        "cost": raw["now_cost"],
        "transfers_in_event": raw.get("transfers_in_event", 0),
        "transfers_out_event": raw.get("transfers_out_event", 0),
        "selected_by_percent": Decimal(str(raw.get("selected_by_percent", "0"))),
    }
