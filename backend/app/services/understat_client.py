"""Client for Understat xG data.

Uses the internal POST API at /main/getPlayersStats/ which returns
season-level xG, xA, npxG, xGChain, xGBuildup per player.
"""

from typing import Any

import httpx

UNDERSTAT_BASE = "https://understat.com"
HEADERS = {"X-Requested-With": "XMLHttpRequest"}


async def fetch_league_players(
    league: str = "EPL", season: str = "2025"
) -> list[dict[str, Any]]:
    """Fetch season-level xG stats for all players in a league.

    Returns a list of dicts with keys: id, player_name, team_title,
    games, time, goals, xG, assists, xA, shots, key_passes,
    npg, npxG, xGChain, xGBuildup, position, etc.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{UNDERSTAT_BASE}/main/getPlayersStats/",
            data={"league": league, "season": season},
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(f"Understat API error: {data}")
        return data["players"]
