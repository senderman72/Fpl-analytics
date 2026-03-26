"""Team model — 20 Premier League teams."""

from datetime import datetime

from sqlalchemy import SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(80))
    short_name: Mapped[str] = mapped_column(String(10))
    strength_overall_home: Mapped[int] = mapped_column(SmallInteger)
    strength_overall_away: Mapped[int] = mapped_column(SmallInteger)
    strength_attack_home: Mapped[int] = mapped_column(SmallInteger)
    strength_attack_away: Mapped[int] = mapped_column(SmallInteger)
    strength_defence_home: Mapped[int] = mapped_column(SmallInteger)
    strength_defence_away: Mapped[int] = mapped_column(SmallInteger)
    updated_at: Mapped[datetime] = mapped_column(server_default="now()")

    players: Mapped[list["Player"]] = relationship(back_populates="team")  # noqa: F821
