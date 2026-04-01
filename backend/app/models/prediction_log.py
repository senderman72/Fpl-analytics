"""Prediction log — stores per-player per-GW predicted vs actual points."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PredictionLog(Base):
    __tablename__ = "prediction_logs"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "gameweek_id",
            "model_version",
            name="uq_predlog_player_gw_ver",
        ),
        Index("idx_predlog_gw", "gameweek_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    gameweek_id: Mapped[int] = mapped_column(ForeignKey("gameweeks.id"))
    predicted_points: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    actual_points: Mapped[int | None] = mapped_column(SmallInteger)
    position: Mapped[int] = mapped_column(SmallInteger)
    model_version: Mapped[str] = mapped_column(String(20), server_default="'v2'")
    created_at: Mapped[datetime] = mapped_column(server_default="now()")

    player: Mapped["Player"] = relationship()  # noqa: F821
    gameweek: Mapped["Gameweek"] = relationship()  # noqa: F821
