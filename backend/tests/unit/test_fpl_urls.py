"""Tests for shared FPL URL utilities."""

from app.services.fpl_urls import badge_url, shirt_url


class TestShirtUrl:
    def test_goalkeeper_url_includes_gk_suffix(self) -> None:
        url = shirt_url(team_code=6, position=1)
        assert url.endswith("/shirt_6_1-110.webp")

    def test_outfield_url_has_no_gk_suffix(self) -> None:
        url = shirt_url(team_code=6, position=2)
        assert url.endswith("/shirt_6-110.webp")

    def test_all_outfield_positions_same_format(self) -> None:
        for pos in (2, 3, 4):
            url = shirt_url(team_code=14, position=pos)
            assert "/shirt_14-110.webp" in url

    def test_url_starts_with_fpl_domain(self) -> None:
        url = shirt_url(team_code=1, position=3)
        assert url.startswith("https://fantasy.premierleague.com/")


class TestBadgeUrl:
    def test_valid_team_code_returns_png_url(self) -> None:
        url = badge_url(team_code=14)
        assert url == "https://resources.premierleague.com/premierleague/badges/100/t14.png"

    def test_zero_team_code_returns_none(self) -> None:
        assert badge_url(team_code=0) is None

    def test_url_contains_team_code(self) -> None:
        url = badge_url(team_code=91)
        assert url is not None
        assert "t91.png" in url
