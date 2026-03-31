"""Intra-day transfer activity snapshots for velocity tracking."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TransferSnapshot(Base):
    __tablename__ = "transfer_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "player_id", "recorded_at", name="uq_transfer_snap_player_ts"
        ),
        Index("idx_transfer_snap_player", "player_id", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    transfers_in_event: Mapped[int] = mapped_column(Integer, server_default="0")
    transfers_out_event: Mapped[int] = mapped_column(Integer, server_default="0")
    net_transfers: Mapped[int] = mapped_column(Integer, server_default="0")

    player: Mapped["Player"] = relationship()  # noqa: F821
