"""Per-player season-level Understat xG data.

Stores season totals from Understat's getPlayersStats API.
Per-90 metrics are computed from these totals.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PlayerSeasonXG(Base):
    __tablename__ = "player_season_xg"
    __table_args__ = (
        UniqueConstraint("player_id", "season", name="uq_xg_player_season"),
    )

    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), primary_key=True)
    season: Mapped[str] = mapped_column(String(4), primary_key=True)  # e.g. "2025"
    understat_id: Mapped[int] = mapped_column()
    games: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    minutes: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    xg: Mapped[Decimal] = mapped_column(Numeric(7, 2), server_default="0")
    xa: Mapped[Decimal] = mapped_column(Numeric(7, 2), server_default="0")
    xgi: Mapped[Decimal] = mapped_column(Numeric(7, 2), server_default="0")
    npxg: Mapped[Decimal] = mapped_column(Numeric(7, 2), server_default="0")
    shots: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    key_passes: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    xg_chain: Mapped[Decimal] = mapped_column(Numeric(7, 2), server_default="0")
    xg_buildup: Mapped[Decimal] = mapped_column(Numeric(7, 2), server_default="0")
    updated_at: Mapped[datetime] = mapped_column(server_default="now()")

    player: Mapped["Player"] = relationship(back_populates="season_xg")  # noqa: F821
