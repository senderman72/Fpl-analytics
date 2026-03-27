"""Gameweek and fixture response schemas."""

from pydantic import BaseModel


class LivePlayerScore(BaseModel):
    player_id: int
    web_name: str
    shirt_url: str
    minutes: int
    goals_scored: int
    assists: int
    bonus: int
    bps: int
    total_points: int


class LiveFixture(BaseModel):
    fixture_id: int
    home_team_short: str
    away_team_short: str
    home_badge_url: str | None = None
    away_badge_url: str | None = None
    home_goals: int
    away_goals: int
    started: bool
    finished: bool
    minutes: int


class LiveGWResponse(BaseModel):
    gameweek_id: int
    fixtures: list[LiveFixture]
    players: list[LivePlayerScore]


class GameweekOut(BaseModel):
    id: int
    name: str
    deadline_time: str
    is_current: bool
    is_next: bool
    is_finished: bool
    is_double: bool
    is_blank: bool
    average_entry_score: int | None
    highest_score: int | None


class FixtureOut(BaseModel):
    id: int
    gameweek_id: int | None
    home_team_id: int
    away_team_id: int
    home_short_name: str | None = None
    away_short_name: str | None = None
    home_badge_url: str | None = None
    away_badge_url: str | None = None
    kickoff_time: str | None
    started: bool
    finished: bool
    home_goals: int | None
    away_goals: int | None
    home_difficulty: int | None
    away_difficulty: int | None
