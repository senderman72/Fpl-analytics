"""Tests for prediction model player filtering — status + chance_of_playing."""

import pytest


class TestPredictionStatusFilter:
    """Verify that the prediction queries include doubtful players
    who have a valid chance_of_playing >= 50."""

    def test_status_filter_includes_doubtful(self) -> None:
        """Players with status 'd' (doubtful) but chance >= 50 should be included."""
        from app.services.points_model import _should_include_player

        # Doubtful but 75% chance — should include
        assert _should_include_player(status="d", chance=75, minutes_pct=80.0) is True

    def test_status_filter_includes_active(self) -> None:
        """Players with status 'a' (active) should always be included."""
        from app.services.points_model import _should_include_player

        assert _should_include_player(status="a", chance=None, minutes_pct=80.0) is True

    def test_status_filter_excludes_unavailable(self) -> None:
        """Players with status 'u' (unavailable) should be excluded."""
        from app.services.points_model import _should_include_player

        assert _should_include_player(status="u", chance=0, minutes_pct=0.0) is False

    def test_status_filter_excludes_injured(self) -> None:
        """Players with status 'i' (injured) should be excluded."""
        from app.services.points_model import _should_include_player

        assert _should_include_player(status="i", chance=0, minutes_pct=50.0) is False

    def test_status_filter_excludes_doubtful_low_chance(self) -> None:
        """Doubtful players with chance < 50 should be excluded."""
        from app.services.points_model import _should_include_player

        assert _should_include_player(status="d", chance=25, minutes_pct=80.0) is False

    def test_status_filter_excludes_low_minutes(self) -> None:
        """Players with < 50% minutes should be excluded regardless of status."""
        from app.services.points_model import _should_include_player

        assert _should_include_player(status="a", chance=None, minutes_pct=30.0) is False

    def test_status_filter_suspended(self) -> None:
        """Players with status 's' (suspended) should be excluded."""
        from app.services.points_model import _should_include_player

        assert _should_include_player(status="s", chance=0, minutes_pct=80.0) is False

    def test_status_filter_doubtful_exactly_50(self) -> None:
        from app.services.points_model import _should_include_player

        assert _should_include_player(status="d", chance=50, minutes_pct=80.0) is True

    def test_status_filter_doubtful_49(self) -> None:
        from app.services.points_model import _should_include_player

        assert _should_include_player(status="d", chance=49, minutes_pct=80.0) is False

    def test_status_filter_doubtful_none_chance(self) -> None:
        """Doubtful with None chance — FPL sometimes has this, treat as excluded."""
        from app.services.points_model import _should_include_player

        assert _should_include_player(status="d", chance=None, minutes_pct=80.0) is False
