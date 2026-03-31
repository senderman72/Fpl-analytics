"""Fixture model — all PL matches."""

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Fixture(Base):
    __tablename__ = "fixtures"
    __table_args__ = (
        Index("idx_fixtures_gw", "gameweek_id"),
        Index("idx_fixtures_home_team", "home_team_id"),
        Index("idx_fixtures_away_team", "away_team_id"),
        Index("idx_fixtures_finished_gw", "finished", "gameweek_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    gameweek_id: Mapped[int | None] = mapped_column(ForeignKey("gameweeks.id"))
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    kickoff_time: Mapped[datetime | None]
    started: Mapped[bool] = mapped_column(Boolean, server_default="false")
    finished: Mapped[bool] = mapped_column(Boolean, server_default="false")
    finished_provisional: Mapped[bool] = mapped_column(Boolean, server_default="false")
    home_goals: Mapped[int | None] = mapped_column(SmallInteger)
    away_goals: Mapped[int | None] = mapped_column(SmallInteger)
    home_difficulty: Mapped[int | None] = mapped_column(SmallInteger)
    away_difficulty: Mapped[int | None] = mapped_column(SmallInteger)

    gameweek: Mapped["Gameweek | None"] = relationship(back_populates="fixtures")  # noqa: F821
    home_team: Mapped["Team"] = relationship(foreign_keys=[home_team_id])  # noqa: F821
    away_team: Mapped["Team"] = relationship(foreign_keys=[away_team_id])  # noqa: F821
