"""Materialised form window cache — rolling 4/6/10 GW stats."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PlayerFormCache(Base):
    __tablename__ = "player_form_cache"
    __table_args__ = (
        Index("idx_form_player", "player_id"),
    )

    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"), primary_key=True
    )
    gw_window: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    total_points: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    pts_per_game: Mapped[Decimal] = mapped_column(Numeric(4, 2), server_default="0")
    pts_per_90: Mapped[Decimal] = mapped_column(Numeric(4, 2), server_default="0")
    xgi_per_90: Mapped[Decimal] = mapped_column(Numeric(5, 2), server_default="0")
    goals: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    assists: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    bonus: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    bps_avg: Mapped[Decimal] = mapped_column(Numeric(5, 1), server_default="0")
    minutes_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), server_default="0")
    clean_sheets: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(server_default="now()")

    player: Mapped["Player"] = relationship(back_populates="form_cache")  # noqa: F821
