"""Per-player per-GW FPL stats."""

from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PlayerGWStats(Base):
    __tablename__ = "player_gw_stats"
    __table_args__ = (
        Index("idx_pgw_player_gw", "player_id", "gameweek_id"),
        Index("idx_pgw_gw", "gameweek_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    gameweek_id: Mapped[int] = mapped_column(ForeignKey("gameweeks.id"))
    fixture_id: Mapped[int | None] = mapped_column(ForeignKey("fixtures.id"))
    minutes: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    goals_scored: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    assists: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    clean_sheets: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    goals_conceded: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    own_goals: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    penalties_saved: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    penalties_missed: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    yellow_cards: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    red_cards: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    saves: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    bonus: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    bps: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    influence: Mapped[Decimal] = mapped_column(Numeric(6, 1), server_default="0")
    creativity: Mapped[Decimal] = mapped_column(Numeric(6, 1), server_default="0")
    threat: Mapped[Decimal] = mapped_column(Numeric(6, 1), server_default="0")
    ict_index: Mapped[Decimal] = mapped_column(Numeric(6, 1), server_default="0")
    total_points: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    transfers_in: Mapped[int] = mapped_column(Integer, server_default="0")
    transfers_out: Mapped[int] = mapped_column(Integer, server_default="0")
    selected_by_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), server_default="0"
    )
    value: Mapped[int] = mapped_column(SmallInteger, server_default="0")

    player: Mapped["Player"] = relationship(back_populates="gw_stats")  # noqa: F821
    gameweek: Mapped["Gameweek"] = relationship(back_populates="gw_stats")  # noqa: F821
    fixture: Mapped["Fixture | None"] = relationship()  # noqa: F821
