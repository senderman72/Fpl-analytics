"""Unit tests for overnight price change staleness logic."""

import datetime as dt

from app.schemas.decision import OvernightChanges


class TestOvernightChangesSchema:
    """Test the OvernightChanges schema."""

    def test_empty_changes(self) -> None:
        oc = OvernightChanges(risers=[], fallers=[], date="2026-04-04")
        assert oc.risers == []
        assert oc.date == "2026-04-04"

    def test_has_changes(self) -> None:
        """Schema should accept valid data."""
        from app.schemas.decision import OvernightChange

        oc = OvernightChanges(
            risers=[
                OvernightChange(
                    player_id=1,
                    web_name="Test",
                    team_short_name="TST",
                    position=2,
                    old_price=50,
                    new_price=51,
                    change=1,
                )
            ],
            fallers=[],
            date="2026-04-04",
        )
        assert len(oc.risers) == 1


class TestIsSnapshotFresh:
    """Test the freshness check for overnight changes."""

    def test_today_is_fresh(self) -> None:
        from app.api.decisions import _is_snapshot_fresh

        today = dt.date.today()
        assert _is_snapshot_fresh(today) is True

    def test_yesterday_is_fresh(self) -> None:
        from app.api.decisions import _is_snapshot_fresh

        yesterday = dt.date.today() - dt.timedelta(days=1)
        assert _is_snapshot_fresh(yesterday) is True

    def test_two_days_ago_is_stale(self) -> None:
        from app.api.decisions import _is_snapshot_fresh

        old = dt.date.today() - dt.timedelta(days=2)
        assert _is_snapshot_fresh(old) is False

    def test_week_ago_is_stale(self) -> None:
        from app.api.decisions import _is_snapshot_fresh

        old = dt.date.today() - dt.timedelta(days=7)
        assert _is_snapshot_fresh(old) is False
