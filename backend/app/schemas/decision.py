"""Decision endpoint response schemas."""

from decimal import Decimal

from pydantic import BaseModel


class BuyCandidate(BaseModel):
    player_id: int
    web_name: str
    shirt_url: str | None = None
    team_short_name: str
    position: int
    now_cost: int
    form_points: int
    pts_per_game: Decimal
    xgi_per_90: Decimal
    minutes_pct: Decimal
    ppm: Decimal
    fdr_next_5: Decimal | None = None
    predicted_points: Decimal | None = None
    selected_by_percent: Decimal | None = None
    transfers_in_event: int | None = None
    recommendation: str = ""


class CaptainPick(BaseModel):
    player_id: int
    web_name: str
    shirt_url: str | None = None
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
    recommendation: str = ""


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
    shirt_url: str | None = None
    team_short_name: str
    position: int
    now_cost: int
    selected_by_percent: Decimal
    form_points: int
    xgi_per_90: Decimal


class PriceChangeCandidate(BaseModel):
    player_id: int
    web_name: str
    shirt_url: str | None = None
    team_short_name: str
    position: int
    now_cost: int
    selected_by_percent: Decimal | None = None
    transfers_in_event: int
    transfers_out_event: int
    net_transfers: int
    cost_change_event: int
    likelihood: str  # "very_likely", "likely", "possible"


class PriceChangePrediction(BaseModel):
    risers: list[PriceChangeCandidate]
    fallers: list[PriceChangeCandidate]


class GWPrediction(BaseModel):
    gw_id: int
    predicted_points: Decimal


class PredictionOut(BaseModel):
    player_id: int
    web_name: str
    shirt_url: str | None = None
    team_short_name: str
    position: int
    predicted_points: Decimal
    predicted_per_gw: list[GWPrediction] = []
    horizon: int = 1
    now_cost: int
