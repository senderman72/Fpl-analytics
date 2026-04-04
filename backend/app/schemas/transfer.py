"""Transfer suggestion response schemas."""

from decimal import Decimal

from pydantic import BaseModel

from app.schemas.my_team import FixturePreview


class TransferSuggestion(BaseModel):
    sell_player_id: int
    sell_web_name: str
    sell_shirt_url: str | None = None
    sell_team_short: str
    sell_predicted_pts: Decimal
    sell_fixtures: list[FixturePreview] = []
    buy_player_id: int
    buy_web_name: str
    buy_shirt_url: str | None = None
    buy_team_short: str
    buy_now_cost: int
    buy_predicted_pts: Decimal
    buy_fixtures: list[FixturePreview] = []
    points_gain: Decimal
    price_diff: int  # buy cost - sell cost (negative = saves money)
    score: Decimal
    reasoning: str


class TransferPlan(BaseModel):
    suggestions: list[TransferSuggestion]
    free_transfers: int = 1
    bank: int  # in tenths
