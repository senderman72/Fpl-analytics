"""add perf indexes for form_cache, prices, transfers

Revision ID: a1b2c3d4e5f6
Revises: f3041b523a82
Create Date: 2026-04-14 15:50:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f3041b523a82'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_form_player_gw", "player_form_cache", ["player_id", "gw_window"],
        unique=False,
    )
    op.create_index(
        "idx_prices_date", "player_prices", ["recorded_at"],
        unique=False,
    )
    op.create_index(
        "idx_transfer_snap_date", "transfer_snapshots", ["recorded_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_transfer_snap_date", table_name="transfer_snapshots")
    op.drop_index("idx_prices_date", table_name="player_prices")
    op.drop_index("idx_form_player_gw", table_name="player_form_cache")
