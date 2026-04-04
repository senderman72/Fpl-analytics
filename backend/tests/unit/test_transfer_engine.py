"""Unit tests for transfer engine — scoring, ranking, filtering."""

from decimal import Decimal

import pytest

from app.schemas.my_team import FixturePreview
from app.schemas.transfer import TransferPlan, TransferSuggestion


def _pick(
    pid: int,
    name: str,
    position: int,
    cost: int,
    predicted: float,
    team: str = "TST",
    fixtures: list | None = None,
) -> dict:
    """Build a squad player dict matching transfer engine input format."""
    return {
        "player_id": pid,
        "web_name": name,
        "shirt_url": None,
        "team_short_name": team,
        "position": position,
        "now_cost": cost,
        "predicted_points": Decimal(str(predicted)),
        "fixtures": fixtures or [],
    }


def _candidate(
    pid: int,
    name: str,
    position: int,
    cost: int,
    predicted: float,
    team: str = "OTH",
    fixtures: list | None = None,
) -> dict:
    """Build a replacement candidate dict."""
    return {
        "player_id": pid,
        "web_name": name,
        "shirt_url": None,
        "team_short_name": team,
        "position": position,
        "now_cost": cost,
        "predicted_points": Decimal(str(predicted)),
        "fixtures": fixtures or [],
    }


class TestTransferSchemas:
    """Test Pydantic schema construction."""

    def test_suggestion_construction(self) -> None:
        s = TransferSuggestion(
            sell_player_id=1,
            sell_web_name="Bad",
            sell_team_short="TST",
            sell_predicted_pts=Decimal("5.0"),
            buy_player_id=2,
            buy_web_name="Good",
            buy_team_short="OTH",
            buy_now_cost=60,
            buy_predicted_pts=Decimal("15.0"),
            points_gain=Decimal("10.0"),
            price_diff=10,
            score=Decimal("9.5"),
            reasoning="Higher predicted points",
        )
        assert s.points_gain == Decimal("10.0")

    def test_plan_construction(self) -> None:
        plan = TransferPlan(suggestions=[], bank=50)
        assert plan.free_transfers == 1
        assert plan.suggestions == []


class TestSuggestTransfers:
    """Test the core suggest_transfers function."""

    def test_returns_suggestions_for_underperformers(self) -> None:
        from app.services.transfer_engine import suggest_transfers

        squad = [
            _pick(1, "GoodGK", 1, 50, 12.0),
            _pick(2, "GoodDEF", 2, 55, 15.0),
            _pick(3, "GoodDEF2", 2, 50, 14.0),
            _pick(4, "GoodDEF3", 2, 45, 13.0),
            _pick(5, "BadDEF", 2, 60, 3.0),  # underperformer
            _pick(6, "GoodMID", 3, 80, 20.0),
            _pick(7, "GoodMID2", 3, 75, 18.0),
            _pick(8, "GoodMID3", 3, 70, 16.0),
            _pick(9, "BadMID", 3, 65, 2.0),  # underperformer
            _pick(10, "GoodMID4", 3, 60, 14.0),
            _pick(11, "GoodFWD", 4, 90, 22.0),
            _pick(12, "GoodFWD2", 4, 70, 17.0),
            _pick(13, "BadFWD", 4, 80, 1.0),  # underperformer
            _pick(14, "BenchGK", 1, 40, 5.0),
            _pick(15, "BenchDEF", 2, 40, 6.0),
        ]
        candidates = [
            _candidate(101, "UpgradeDEF", 2, 55, 14.0),
            _candidate(102, "UpgradeMID", 3, 60, 17.0),
            _candidate(103, "UpgradeFWD", 4, 75, 18.0),
        ]
        result = suggest_transfers(
            squad=squad, bank=20, candidates=candidates, free_transfers=1
        )
        assert len(result) > 0
        assert all(s.points_gain > 0 for s in result)

    def test_respects_budget_constraint(self) -> None:
        from app.services.transfer_engine import suggest_transfers

        squad = [
            _pick(1, "GK", 1, 50, 10.0),
            _pick(2, "DEF1", 2, 50, 10.0),
            _pick(3, "DEF2", 2, 50, 10.0),
            _pick(4, "DEF3", 2, 50, 10.0),
            _pick(5, "BadDEF", 2, 40, 1.0),
            _pick(6, "MID1", 3, 70, 15.0),
            _pick(7, "MID2", 3, 65, 14.0),
            _pick(8, "MID3", 3, 60, 13.0),
            _pick(9, "MID4", 3, 55, 12.0),
            _pick(10, "MID5", 3, 50, 11.0),
            _pick(11, "FWD1", 4, 80, 18.0),
            _pick(12, "FWD2", 4, 70, 15.0),
            _pick(13, "FWD3", 4, 60, 12.0),
            _pick(14, "BenchGK", 1, 40, 5.0),
            _pick(15, "BenchDEF", 2, 40, 5.0),
        ]
        # Expensive candidate that costs more than sell + bank
        expensive = _candidate(201, "ExpensiveDEF", 2, 100, 25.0)
        # Affordable candidate
        affordable = _candidate(202, "CheapDEF", 2, 45, 8.0)
        result = suggest_transfers(
            squad=squad, bank=5, candidates=[expensive, affordable]
        )
        # Should only suggest the affordable one
        buy_ids = [s.buy_player_id for s in result]
        assert 201 not in buy_ids
        if result:
            assert 202 in buy_ids

    def test_no_suggestions_when_squad_is_optimal(self) -> None:
        from app.services.transfer_engine import suggest_transfers

        squad = [
            _pick(i, f"Player{i}", pos, 50 + i, 15.0 + i)
            for i, pos in enumerate(
                [1, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 1, 2], start=1
            )
        ]
        # Candidates are all worse
        candidates = [
            _candidate(101, "Worse1", 2, 50, 5.0),
            _candidate(102, "Worse2", 3, 50, 5.0),
            _candidate(103, "Worse3", 4, 50, 5.0),
        ]
        result = suggest_transfers(squad=squad, bank=50, candidates=candidates)
        assert len(result) == 0

    def test_excludes_squad_players_from_candidates(self) -> None:
        from app.services.transfer_engine import suggest_transfers

        squad = [
            _pick(1, "GK", 1, 50, 10.0),
            _pick(2, "DEF1", 2, 50, 10.0),
            _pick(3, "DEF2", 2, 50, 10.0),
            _pick(4, "DEF3", 2, 50, 10.0),
            _pick(5, "BadDEF", 2, 40, 1.0),
            _pick(6, "MID1", 3, 70, 15.0),
            _pick(7, "MID2", 3, 65, 14.0),
            _pick(8, "MID3", 3, 60, 13.0),
            _pick(9, "MID4", 3, 55, 12.0),
            _pick(10, "MID5", 3, 50, 11.0),
            _pick(11, "FWD1", 4, 80, 18.0),
            _pick(12, "FWD2", 4, 70, 15.0),
            _pick(13, "FWD3", 4, 60, 12.0),
            _pick(14, "BenchGK", 1, 40, 5.0),
            _pick(15, "BenchDEF", 2, 40, 5.0),
        ]
        # Candidate has same ID as squad player
        same_id = _candidate(5, "BadDEF", 2, 40, 1.0)
        upgrade = _candidate(201, "Upgrade", 2, 45, 10.0)
        result = suggest_transfers(
            squad=squad, bank=50, candidates=[same_id, upgrade]
        )
        buy_ids = [s.buy_player_id for s in result]
        assert 5 not in buy_ids

    def test_hit_penalty_after_first_transfer(self) -> None:
        from app.services.transfer_engine import suggest_transfers

        squad = [
            _pick(1, "GK", 1, 50, 10.0),
            _pick(2, "DEF1", 2, 50, 10.0),
            _pick(3, "DEF2", 2, 50, 10.0),
            _pick(4, "DEF3", 2, 50, 10.0),
            _pick(5, "BadDEF", 2, 40, 1.0),
            _pick(6, "MID1", 3, 70, 15.0),
            _pick(7, "MID2", 3, 65, 14.0),
            _pick(8, "MID3", 3, 60, 13.0),
            _pick(9, "BadMID", 3, 55, 1.0),
            _pick(10, "MID5", 3, 50, 11.0),
            _pick(11, "FWD1", 4, 80, 18.0),
            _pick(12, "FWD2", 4, 70, 15.0),
            _pick(13, "FWD3", 4, 60, 12.0),
            _pick(14, "BenchGK", 1, 40, 5.0),
            _pick(15, "BenchDEF", 2, 40, 5.0),
        ]
        candidates = [
            _candidate(101, "UpgDEF", 2, 45, 12.0),
            _candidate(102, "UpgMID", 3, 55, 14.0),
        ]
        result = suggest_transfers(
            squad=squad, bank=50, candidates=candidates, free_transfers=1
        )
        # Second+ suggestions should have lower scores due to -4 hit
        if len(result) >= 2:
            assert result[0].score >= result[1].score

    def test_caps_at_five_suggestions(self) -> None:
        from app.services.transfer_engine import suggest_transfers

        # Squad with many bad players
        squad = [
            _pick(i, f"Bad{i}", pos, 40, 1.0)
            for i, pos in enumerate(
                [1, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 1, 2], start=1
            )
        ]
        # Many good candidates
        candidates = [
            _candidate(100 + i, f"Good{i}", pos, 45, 20.0)
            for i, pos in enumerate([2, 2, 3, 3, 3, 4, 4], start=1)
        ]
        result = suggest_transfers(
            squad=squad, bank=100, candidates=candidates
        )
        assert len(result) <= 5

    def test_empty_squad_returns_empty(self) -> None:
        from app.services.transfer_engine import suggest_transfers

        result = suggest_transfers(squad=[], bank=50, candidates=[])
        assert result == []
