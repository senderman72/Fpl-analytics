"""FPL API response → DB model translation.

Maps raw JSON from the FPL API into dicts suitable for
SQLAlchemy upserts on the corresponding tables.
"""

import datetime as dt
import logging
from decimal import Decimal
from typing import Any

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


def normalise_team(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a raw FPL API team object to the teams table columns."""
    return {
        "id": raw["id"],
        "code": raw["code"],
        "name": raw["name"],
        "short_name": raw["short_name"],
        "strength_overall_home": raw["strength_overall_home"],
        "strength_overall_away": raw["strength_overall_away"],
        "strength_attack_home": raw["strength_attack_home"],
        "strength_attack_away": raw["strength_attack_away"],
        "strength_defence_home": raw["strength_defence_home"],
        "strength_defence_away": raw["strength_defence_away"],
        "updated_at": dt.datetime.now(dt.UTC),
    }


def normalise_player(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a raw FPL API element object to the players table columns."""
    return {
        "id": raw["id"],
        "code": raw["code"],
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
        "selected_by_percent": Decimal(str(raw.get("selected_by_percent", "0"))),
        "transfers_in_event": raw.get("transfers_in_event", 0),
        "transfers_out_event": raw.get("transfers_out_event", 0),
        "cost_change_event": raw.get("cost_change_event", 0),
        "updated_at": dt.datetime.now(dt.UTC),
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


def normalise_price_snapshot(player_id: int, raw: dict[str, Any]) -> dict[str, Any]:
    """Map bootstrap player data to a daily player_prices row."""
    return {
        "player_id": player_id,
        "recorded_at": dt.date.today(),
        "cost": raw["now_cost"],
        "transfers_in_event": raw.get("transfers_in_event", 0),
        "transfers_out_event": raw.get("transfers_out_event", 0),
        "selected_by_percent": Decimal(str(raw.get("selected_by_percent", "0"))),
    }


# --- Understat matching and normalisation ---

# Map Understat team names to FPL short names
UNDERSTAT_TEAM_MAP: dict[str, str] = {
    "Arsenal": "ARS",
    "Aston Villa": "AVL",
    "Bournemouth": "BOU",
    "Brentford": "BRE",
    "Brighton": "BHA",
    "Burnley": "BUR",
    "Chelsea": "CHE",
    "Crystal Palace": "CRY",
    "Everton": "EVE",
    "Fulham": "FUL",
    "Ipswich": "IPS",
    "Leicester": "LEI",
    "Liverpool": "LIV",
    "Manchester City": "MCI",
    "Manchester United": "MUN",
    "Newcastle United": "NEW",
    "Nottingham Forest": "NFO",
    "Southampton": "SOU",
    "Tottenham": "TOT",
    "West Ham": "WHU",
    "Wolverhampton Wanderers": "WOL",
    "Wolves": "WOL",
}


def match_understat_to_fpl(
    understat_players: list[dict[str, Any]],
    fpl_players: list[dict[str, Any]],
) -> dict[int, int]:
    """Match Understat players to FPL player IDs using fuzzy name matching.

    Args:
        understat_players: Understat API dicts (id, player_name, team_title)
        fpl_players: FPL dicts (id, web_name, first/second_name, team_short_name)

    Returns:
        Dict mapping FPL player_id to Understat player_id
    """
    # Group FPL players by team short name for faster matching
    fpl_by_team: dict[str, list[dict]] = {}
    for p in fpl_players:
        fpl_by_team.setdefault(p["team_short_name"], []).append(p)

    matched: dict[int, int] = {}
    unmatched: list[str] = []

    for us_player in understat_players:
        us_name = us_player["player_name"]
        us_team = us_player["team_title"]
        us_id = int(us_player["id"])

        # Understat may list multiple teams (e.g. "Arsenal,Crystal Palace")
        # Try each team until we find a match
        team_names = [t.strip() for t in us_team.split(",")]
        fpl_team_codes = [
            UNDERSTAT_TEAM_MAP[t] for t in team_names if t in UNDERSTAT_TEAM_MAP
        ]

        if not fpl_team_codes:
            unmatched.append(f"{us_name} ({us_team}) - unknown team")
            continue

        # Gather candidates from all possible teams
        candidates = []
        for code in fpl_team_codes:
            candidates.extend(fpl_by_team.get(code, []))

        if not candidates:
            unmatched.append(f"{us_name} ({us_team}) - no FPL players")
            continue

        # Try matching against web_name, full name, and last name
        best_score: float = 0
        best_fpl = None
        us_last = us_name.split()[-1]
        for fpl_p in candidates:
            # Score against web_name (e.g. "Salah" vs "M.Salah")
            score_web = fuzz.ratio(us_last, fpl_p["web_name"])
            # Score against full name
            full_name = f"{fpl_p['first_name']} {fpl_p['second_name']}"
            score_full = fuzz.ratio(us_name, full_name)
            # Partial ratio catches "Bruno Guimarães" vs "Bruno G."
            score_partial = fuzz.partial_ratio(us_name, full_name)
            score = max(score_web, score_full, score_partial)
            if score > best_score:
                best_score = score
                best_fpl = fpl_p

        if best_fpl and best_score > 65:
            matched[best_fpl["id"]] = us_id
        else:
            unmatched.append(
                f"{us_name} ({us_team}) - best match: "
                f"{best_fpl['web_name'] if best_fpl else '?'} ({best_score})"
            )

    if unmatched:
        logger.warning(
            "Understat: %d unmatched players:\n  %s",
            len(unmatched),
            "\n  ".join(unmatched[:20]),
        )
    logger.info(
        "Understat matching: %d matched, %d unmatched",
        len(matched),
        len(unmatched),
    )
    return matched


def normalise_understat_season(
    raw: dict[str, Any], fpl_player_id: int, season: str
) -> dict[str, Any]:
    """Map Understat season stats to player_season_xg row."""
    xg = Decimal(raw["xG"])
    xa = Decimal(raw["xA"])
    return {
        "player_id": fpl_player_id,
        "season": season,
        "understat_id": int(raw["id"]),
        "games": int(raw["games"]),
        "minutes": int(raw["time"]),
        "xg": xg,
        "xa": xa,
        "xgi": xg + xa,
        "npxg": Decimal(raw["npxG"]),
        "shots": int(raw["shots"]),
        "key_passes": int(raw["key_passes"]),
        "xg_chain": Decimal(raw["xGChain"]),
        "xg_buildup": Decimal(raw["xGBuildup"]),
        "updated_at": dt.datetime.now(dt.UTC),
    }
