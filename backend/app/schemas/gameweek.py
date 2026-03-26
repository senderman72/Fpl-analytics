"""Gameweek and fixture response schemas."""

from pydantic import BaseModel


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
    kickoff_time: str | None
    started: bool
    finished: bool
    home_goals: int | None
    away_goals: int | None
    home_difficulty: int | None
    away_difficulty: int | None
