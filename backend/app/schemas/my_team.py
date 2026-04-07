"""My Team response schemas."""

from decimal import Decimal

from pydantic import BaseModel


class FixturePreview(BaseModel):
    opponent: str
    difficulty: int
    is_home: bool


class MyTeamPick(BaseModel):
    player_id: int
    web_name: str
    shirt_url: str | None = None
    team_short_name: str
    position: int  # element_type: 1=GK, 2=DEF, 3=MID, 4=FWD
    slot: int  # 1-11 starting, 12-15 bench
    is_captain: bool
    is_vice_captain: bool
    multiplier: int
    now_cost: int
    form_points: int | None = None
    predicted_points: Decimal | None = None
    fixtures: list[FixturePreview] = []


class MyTeamResponse(BaseModel):
    manager_name: str
    team_name: str
    overall_rank: int
    overall_points: int
    gameweek_points: int
    gameweek_id: int = 0
    next_gameweek_id: int = 0
    bank: int  # in tenths
    team_value: int  # in tenths
    starting: list[MyTeamPick]
    bench: list[MyTeamPick]
    total_predicted: Decimal
