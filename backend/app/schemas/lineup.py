"""Predicted lineup response schemas."""

from decimal import Decimal

from pydantic import BaseModel


class LineupPlayer(BaseModel):
    player_id: int
    web_name: str
    shirt_url: str | None = None
    position: int  # 1=GK, 2=DEF, 3=MID, 4=FWD
    confidence: str  # "likely", "rotation", "doubt"
    chance_of_playing: int | None = None
    minutes_pct: Decimal | None = None
    form_points: int | None = None
    news: str | None = None
    score: Decimal = Decimal("0")


class PredictedLineup(BaseModel):
    team_id: int
    team_short_name: str
    team_badge_url: str | None = None
    formation: str  # e.g. "4-3-3"
    starters: list[LineupPlayer]
    bench: list[LineupPlayer]
