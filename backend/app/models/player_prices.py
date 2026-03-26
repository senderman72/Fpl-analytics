"""Daily price change log."""

import datetime as dt

from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, SmallInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PlayerPrice(Base):
    __tablename__ = "player_prices"
    __table_args__ = (
        UniqueConstraint("player_id", "recorded_at", name="uq_prices_player_date"),
        Index("idx_prices_player", "player_id", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    recorded_at: Mapped[dt.date] = mapped_column(Date)
    cost: Mapped[int] = mapped_column(SmallInteger)
    transfers_in_event: Mapped[int] = mapped_column(Integer, server_default="0")
    transfers_out_event: Mapped[int] = mapped_column(Integer, server_default="0")
    selected_by_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), server_default="0"
    )

    player: Mapped["Player"] = relationship(back_populates="prices")  # noqa: F821
