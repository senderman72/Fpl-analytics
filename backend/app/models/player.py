"""Player model — all FPL elements."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Player(Base):
    __tablename__ = "players"
    __table_args__ = (
        Index("idx_players_status", "status"),
        Index("idx_players_team_position", "team_id", "position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    code: Mapped[int] = mapped_column(Integer, server_default="0")
    understat_id: Mapped[int | None] = mapped_column()
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    web_name: Mapped[str] = mapped_column(String(80))
    first_name: Mapped[str] = mapped_column(String(80))
    second_name: Mapped[str] = mapped_column(String(80))
    position: Mapped[int] = mapped_column(SmallInteger)
    now_cost: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(String(1), server_default="a")
    chance_of_playing_next_round: Mapped[int | None] = mapped_column(SmallInteger)
    news: Mapped[str | None] = mapped_column(Text)
    is_penalty_taker: Mapped[bool] = mapped_column(Boolean, server_default="false")
    is_set_piece_taker: Mapped[bool] = mapped_column(Boolean, server_default="false")
    selected_by_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), server_default="0"
    )
    ep_next: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    form: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    points_per_game: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    transfers_in_event: Mapped[int] = mapped_column(Integer, server_default="0")
    transfers_out_event: Mapped[int] = mapped_column(Integer, server_default="0")
    cost_change_event: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(server_default="now()")

    team: Mapped["Team"] = relationship(back_populates="players")  # noqa: F821
    gw_stats: Mapped[list["PlayerGWStats"]] = relationship(back_populates="player")  # noqa: F821
    season_xg: Mapped[list["PlayerSeasonXG"]] = relationship(back_populates="player")  # noqa: F821
    prices: Mapped[list["PlayerPrice"]] = relationship(back_populates="player")  # noqa: F821
    form_cache: Mapped[list["PlayerFormCache"]] = relationship(back_populates="player")  # noqa: F821
