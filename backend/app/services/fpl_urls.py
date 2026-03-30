"""Shared FPL and Premier League CDN URL helpers."""

FPL_SHIRTS = "https://fantasy.premierleague.com/dist/img/shirts/standard"
PL_CDN = "https://resources.premierleague.com/premierleague"


def shirt_url(team_code: int, position: int) -> str:
    """Return the shirt image URL for a player's team and position."""
    if position == 1:  # GK
        return f"{FPL_SHIRTS}/shirt_{team_code}_1-110.webp"
    return f"{FPL_SHIRTS}/shirt_{team_code}-110.webp"


def badge_url(team_code: int) -> str | None:
    """Return the badge image URL, or None if team_code is falsy."""
    if not team_code:
        return None
    return f"{PL_CDN}/badges/100/t{team_code}.png"
