"""Player comparison response schemas."""

from decimal import Decimal

from pydantic import BaseModel


class PlayerComparison(BaseModel):
    id: int
    web_name: str
    first_name: str
    second_name: str
    team_short_name: str
    position: int
    shirt_url: str | None = None
    team_badge_url: str | None = None
    now_cost: int
    selected_by_percent: Decimal | None = None
    # Form (6-GW window)
    form_points: int | None = None
    pts_per_game: Decimal | None = None
    xgi_per_90: Decimal | None = None
    minutes_pct: Decimal | None = None
    bps_avg: Decimal | None = None
    clean_sheets: int | None = None
    goals: int | None = None
    assists: int | None = None
    # Season xG
    season_xg: Decimal | None = None
    season_xa: Decimal | None = None
    season_xgi: Decimal | None = None
    # Fixtures
    fdr_next_5: Decimal | None = None
    fixture_count: int = 0
    # FPL prediction signal
    ep_next: Decimal | None = None
