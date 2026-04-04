"""Unit tests for player comparison schema and id parsing."""

from decimal import Decimal

import pytest

from app.schemas.compare import PlayerComparison


class TestPlayerComparisonSchema:
    """Test PlayerComparison Pydantic model."""

    def test_full_construction(self) -> None:
        pc = PlayerComparison(
            id=1,
            web_name="Salah",
            first_name="Mohamed",
            second_name="Salah",
            team_short_name="LIV",
            position=3,
            shirt_url="https://example.com/shirt.webp",
            team_badge_url="https://example.com/badge.png",
            now_cost=130,
            selected_by_percent=Decimal("35.2"),
            form_points=42,
            pts_per_game=Decimal("7.0"),
            xgi_per_90=Decimal("0.85"),
            minutes_pct=Decimal("92.5"),
            bps_avg=Decimal("28.0"),
            clean_sheets=1,
            goals=5,
            assists=3,
            season_xg=Decimal("15.2"),
            season_xa=Decimal("8.1"),
            season_xgi=Decimal("23.3"),
            fdr_next_5=Decimal("2.8"),
            fixture_count=5,
            predicted_points=Decimal("32.5"),
            ep_next=Decimal("6.2"),
        )
        assert pc.id == 1
        assert pc.web_name == "Salah"
        assert pc.position == 3
        assert pc.fdr_next_5 == Decimal("2.8")

    def test_minimal_construction(self) -> None:
        """Players with no form cache or xG data should still work."""
        pc = PlayerComparison(
            id=999,
            web_name="Unknown",
            first_name="Test",
            second_name="Player",
            team_short_name="TST",
            position=4,
            now_cost=45,
        )
        assert pc.form_points is None
        assert pc.season_xg is None
        assert pc.fdr_next_5 is None
        assert pc.ep_next is None
        assert pc.fixture_count == 0


class TestParseCompareIds:
    """Test the id parsing helper."""

    def test_valid_ids(self) -> None:
        from app.api.players import _parse_compare_ids

        assert _parse_compare_ids("1,2,3") == [1, 2, 3]

    def test_two_ids(self) -> None:
        from app.api.players import _parse_compare_ids

        assert _parse_compare_ids("10,20") == [10, 20]

    def test_five_ids(self) -> None:
        from app.api.players import _parse_compare_ids

        assert _parse_compare_ids("1,2,3,4,5") == [1, 2, 3, 4, 5]

    def test_too_few_ids_raises(self) -> None:
        from app.api.players import _parse_compare_ids

        with pytest.raises(ValueError, match="2 to 5"):
            _parse_compare_ids("1")

    def test_too_many_ids_raises(self) -> None:
        from app.api.players import _parse_compare_ids

        with pytest.raises(ValueError, match="2 to 5"):
            _parse_compare_ids("1,2,3,4,5,6")

    def test_invalid_format_raises(self) -> None:
        from app.api.players import _parse_compare_ids

        with pytest.raises(ValueError):
            _parse_compare_ids("abc,def")

    def test_empty_string_raises(self) -> None:
        from app.api.players import _parse_compare_ids

        with pytest.raises(ValueError):
            _parse_compare_ids("")

    def test_negative_ids_raises(self) -> None:
        from app.api.players import _parse_compare_ids

        with pytest.raises(ValueError, match="positive"):
            _parse_compare_ids("-1,2")

    def test_zero_id_raises(self) -> None:
        from app.api.players import _parse_compare_ids

        with pytest.raises(ValueError, match="positive"):
            _parse_compare_ids("0,1,2")

    def test_deduplicates(self) -> None:
        from app.api.players import _parse_compare_ids

        assert _parse_compare_ids("1,1,2") == [1, 2]
