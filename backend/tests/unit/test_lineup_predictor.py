"""Unit tests for lineup prediction service."""

from decimal import Decimal

import pytest

from app.schemas.lineup import LineupPlayer, PredictedLineup


def _player(
    pid: int,
    name: str,
    position: int,
    chance: int | None = None,
    minutes_pct: float = 90.0,
    form: float = 5.0,
    status: str = "a",
    news: str | None = None,
) -> dict:
    """Build a player dict for the predictor."""
    return {
        "player_id": pid,
        "web_name": name,
        "shirt_url": None,
        "position": position,
        "chance_of_playing": chance,
        "minutes_pct": Decimal(str(minutes_pct)),
        "form_points": int(form * 6),
        "form": Decimal(str(form)),
        "status": status,
        "news": news,
    }


def _squad(count_per_pos: dict[int, int] | None = None) -> list[dict]:
    """Build a standard squad. Default: 2 GK, 5 DEF, 5 MID, 3 FWD."""
    counts = count_per_pos or {1: 2, 2: 5, 3: 5, 4: 3}
    players = []
    pid = 1
    for pos, count in sorted(counts.items()):
        pos_names = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
        for i in range(count):
            players.append(
                _player(pid, f"{pos_names[pos]}{i+1}", pos, minutes_pct=90 - i * 10)
            )
            pid += 1
    return players


class TestSchemas:
    def test_lineup_player_construction(self) -> None:
        lp = LineupPlayer(
            player_id=1,
            web_name="Test",
            position=2,
            confidence="likely",
        )
        assert lp.confidence == "likely"

    def test_predicted_lineup_construction(self) -> None:
        pl = PredictedLineup(
            team_id=1,
            team_short_name="TST",
            formation="4-4-2",
            starters=[],
            bench=[],
        )
        assert pl.formation == "4-4-2"


class TestScorePlayer:
    def test_active_none_chance_treated_as_100(self) -> None:
        from app.services.lineup_predictor import _score_player

        score = _score_player(status="a", chance=None, minutes_pct=90.0, form=5.0)
        assert score > 0

    def test_unavailable_gets_zero(self) -> None:
        from app.services.lineup_predictor import _score_player

        score = _score_player(status="u", chance=0, minutes_pct=90.0, form=5.0)
        assert score == 0

    def test_injured_news_gets_zero(self) -> None:
        from app.services.lineup_predictor import _score_player

        score = _score_player(
            status="d", chance=50, minutes_pct=90.0, form=5.0, news="Knee injury"
        )
        assert score == 0

    def test_suspended_news_gets_zero(self) -> None:
        from app.services.lineup_predictor import _score_player

        score = _score_player(
            status="a", chance=None, minutes_pct=90.0, form=5.0, news="Suspended"
        )
        assert score == 0

    def test_higher_minutes_scores_higher(self) -> None:
        from app.services.lineup_predictor import _score_player

        high = _score_player(status="a", chance=None, minutes_pct=95.0, form=5.0)
        low = _score_player(status="a", chance=None, minutes_pct=30.0, form=5.0)
        assert high > low

    def test_higher_form_scores_higher(self) -> None:
        from app.services.lineup_predictor import _score_player

        high = _score_player(status="a", chance=None, minutes_pct=90.0, form=10.0)
        low = _score_player(status="a", chance=None, minutes_pct=90.0, form=1.0)
        assert high > low


class TestConfidence:
    def test_likely(self) -> None:
        from app.services.lineup_predictor import _confidence

        assert _confidence(Decimal("85")) == "likely"

    def test_rotation(self) -> None:
        from app.services.lineup_predictor import _confidence

        assert _confidence(Decimal("65")) == "rotation"

    def test_doubt(self) -> None:
        from app.services.lineup_predictor import _confidence

        assert _confidence(Decimal("30")) == "doubt"

    def test_zero(self) -> None:
        from app.services.lineup_predictor import _confidence

        assert _confidence(Decimal("0")) == "doubt"

    def test_boundary_80(self) -> None:
        from app.services.lineup_predictor import _confidence

        assert _confidence(Decimal("80")) == "rotation"

    def test_boundary_81(self) -> None:
        from app.services.lineup_predictor import _confidence

        assert _confidence(Decimal("81")) == "likely"

    def test_boundary_50(self) -> None:
        from app.services.lineup_predictor import _confidence

        assert _confidence(Decimal("50")) == "rotation"


class TestPredictLineup:
    def test_returns_11_starters(self) -> None:
        from app.services.lineup_predictor import predict_lineup

        result = predict_lineup(1, "TST", None, _squad())
        assert len(result.starters) == 11

    def test_bench_has_remaining(self) -> None:
        from app.services.lineup_predictor import predict_lineup

        squad = _squad()
        result = predict_lineup(1, "TST", None, squad)
        assert len(result.bench) == len(squad) - 11

    def test_formation_is_valid(self) -> None:
        from app.services.lineup_predictor import predict_lineup

        result = predict_lineup(1, "TST", None, _squad())
        parts = result.formation.split("-")
        assert len(parts) >= 2
        total = sum(int(p) for p in parts)
        assert total == 10  # outfield only, GK implicit

    def test_exactly_one_gk_starts(self) -> None:
        from app.services.lineup_predictor import predict_lineup

        result = predict_lineup(1, "TST", None, _squad())
        gks = [p for p in result.starters if p.position == 1]
        assert len(gks) == 1

    def test_injured_player_benched(self) -> None:
        from app.services.lineup_predictor import predict_lineup

        squad = _squad()
        # Injure the best DEF
        squad[2]["news"] = "Knee injury - expected back in 3 weeks"
        squad[2]["status"] = "i"
        squad[2]["chance_of_playing"] = 0
        result = predict_lineup(1, "TST", None, squad)
        injured_ids = {squad[2]["player_id"]}
        starter_ids = {p.player_id for p in result.starters}
        assert not injured_ids.intersection(starter_ids)

    def test_empty_squad_returns_empty(self) -> None:
        from app.services.lineup_predictor import predict_lineup

        result = predict_lineup(1, "TST", None, [])
        assert result.starters == []
        assert result.formation == "0-0-0"
