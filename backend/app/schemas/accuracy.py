"""Accuracy metrics response schemas."""

from decimal import Decimal

from pydantic import BaseModel


class PositionAccuracy(BaseModel):
    position: int
    position_name: str
    mae: Decimal
    count: int


class GWAccuracy(BaseModel):
    gameweek_id: int
    mae: Decimal
    count: int


class AccuracyResponse(BaseModel):
    mae: Decimal
    rmse: Decimal
    pearson_r: Decimal | None = None
    captain_hit_rate: Decimal | None = None
    total_predictions: int
    total_gameweeks: int
    by_position: list[PositionAccuracy]
    per_gameweek: list[GWAccuracy]
