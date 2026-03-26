"""Per-player per-GW Understat xG data."""

from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PlayerGWXG(Base):
    __tablename__ = "player_gw_xg"
    __table_args__ = (
        Index("idx_xg_player_gw", "player_id", "gameweek_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    gameweek_id: Mapped[int] = mapped_column(ForeignKey("gameweeks.id"))
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"))
    xg: Mapped[Decimal] = mapped_column(Numeric(5, 2), server_default="0")
    xa: Mapped[Decimal] = mapped_column(Numeric(5, 2), server_default="0")
    xgi: Mapped[Decimal] = mapped_column(Numeric(5, 2), server_default="0")
    npxg: Mapped[Decimal] = mapped_column(Numeric(5, 2), server_default="0")
    shots: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    key_passes: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    shots_in_box: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    xg_chain: Mapped[Decimal] = mapped_column(Numeric(5, 2), server_default="0")
    xg_buildup: Mapped[Decimal] = mapped_column(Numeric(5, 2), server_default="0")

    player: Mapped["Player"] = relationship(back_populates="gw_xg")  # noqa: F821
    gameweek: Mapped["Gameweek"] = relationship(back_populates="gw_xg")  # noqa: F821
    fixture: Mapped["Fixture"] = relationship()  # noqa: F821
