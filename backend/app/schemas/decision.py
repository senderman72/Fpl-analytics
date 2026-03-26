"""Decision endpoint response schemas."""

from decimal import Decimal

from pydantic import BaseModel


class BuyCandidate(BaseModel):
    player_id: int
    web_name: str
    team_short_name: str
    position: int
    now_cost: int
    form_points: int
    pts_per_game: Decimal
    xgi_per_90: Decimal
    minutes_pct: Decimal
    ppm: Decimal  # points per million
    fdr_next_5: Decimal | None = None


class CaptainPick(BaseModel):
    player_id: int
    web_name: str
    team_short_name: str
    position: int
    now_cost: int
    ceiling_score: int
    bps_avg: Decimal
    form_points: int
    is_home: bool | None = None
    is_double_gw: bool = False
    is_penalty_taker: bool
    is_set_piece_taker: bool
    predicted_points: Decimal | None = None


class ChipAdvice(BaseModel):
    gameweek_id: int
    name: str
    is_double: bool
    is_blank: bool
    avg_squad_fdr: Decimal | None = None
    recommendation: str | None = None


class DifferentialPick(BaseModel):
    player_id: int
    web_name: str
    team_short_name: str
    position: int
    now_cost: int
    selected_by_percent: Decimal
    form_points: int
    xgi_per_90: Decimal


class PredictionOut(BaseModel):
    player_id: int
    web_name: str
    team_short_name: str
    position: int
    predicted_points: Decimal
    now_cost: int
