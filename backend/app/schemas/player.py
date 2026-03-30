"""Player-related response schemas."""

from decimal import Decimal

from pydantic import BaseModel


class PlayerSummary(BaseModel):
    id: int
    web_name: str
    first_name: str
    second_name: str
    team_id: int
    team_short_name: str | None = None
    position: int
    shirt_url: str | None = None
    team_badge_url: str | None = None
    now_cost: int
    status: str
    chance_of_playing_next_round: int | None
    news: str | None
    is_penalty_taker: bool
    is_set_piece_taker: bool
    # Form cache (6 GW window)
    form_points: int | None = None
    pts_per_game: Decimal | None = None
    xgi_per_90: Decimal | None = None
    minutes_pct: Decimal | None = None
    bps_avg: Decimal | None = None
    # Ownership + transfers
    selected_by_percent: Decimal | None = None
    transfers_in_event: int | None = None
    transfers_out_event: int | None = None
    cost_change_event: int | None = None


class PlayerDetail(PlayerSummary):
    understat_id: int | None
    # Season xG
    season_xg: Decimal | None = None
    season_xa: Decimal | None = None
    season_xgi: Decimal | None = None
    season_npxg: Decimal | None = None
    season_games: int | None = None
    season_minutes: int | None = None
    # Season actuals (for expected vs actual comparison)
    season_goals: int | None = None
    season_assists: int | None = None
    season_points: int | None = None


class PlayerGWHistory(BaseModel):
    gameweek_id: int
    fixture_id: int | None
    minutes: int
    goals_scored: int
    assists: int
    clean_sheets: int
    goals_conceded: int
    bonus: int
    bps: int
    influence: Decimal
    creativity: Decimal
    threat: Decimal
    ict_index: Decimal
    total_points: int
    transfers_in: int
    transfers_out: int
    value: int


class PlayerFixture(BaseModel):
    fixture_id: int
    gameweek_id: int | None
    opponent_team_id: int
    opponent_short_name: str
    is_home: bool
    difficulty: int | None
    kickoff_time: str | None
    is_double_gw: bool = False


class PlayerIdName(BaseModel):
    id: int
    first_name: str
    second_name: str
