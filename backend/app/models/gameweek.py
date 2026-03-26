"""Gameweek model — GW 1–38."""

from datetime import datetime

from sqlalchemy import Boolean, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Gameweek(Base):
    __tablename__ = "gameweeks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(20))
    deadline_time: Mapped[datetime]
    is_current: Mapped[bool] = mapped_column(Boolean, server_default="false")
    is_next: Mapped[bool] = mapped_column(Boolean, server_default="false")
    is_finished: Mapped[bool] = mapped_column(Boolean, server_default="false")
    is_double: Mapped[bool] = mapped_column(Boolean, server_default="false")
    is_blank: Mapped[bool] = mapped_column(Boolean, server_default="false")
    average_entry_score: Mapped[int | None] = mapped_column(SmallInteger)
    highest_score: Mapped[int | None] = mapped_column(SmallInteger)

    fixtures: Mapped[list["Fixture"]] = relationship(back_populates="gameweek")  # noqa: F821
    gw_stats: Mapped[list["PlayerGWStats"]] = relationship(back_populates="gameweek")  # noqa: F821
    gw_xg: Mapped[list["PlayerGWXG"]] = relationship(back_populates="gameweek")  # noqa: F821
