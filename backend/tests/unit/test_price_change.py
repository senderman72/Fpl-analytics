"""Tests for the price change prediction algorithm."""

from __future__ import annotations

from decimal import Decimal

from app.services.price_change import compute_progress, compute_target, compute_velocity


class TestComputeTarget:
    def test_zero_ownership_returns_floor(self) -> None:
        assert compute_target(Decimal("0")) == 20_000

    def test_low_ownership_returns_floor(self) -> None:
        # 2% * 4500 = 9000 < floor of 20000
        assert compute_target(Decimal("2.0")) == 20_000

    def test_medium_ownership(self) -> None:
        # 10% * 4500 = 45000
        assert compute_target(Decimal("10.0")) == 45_000

    def test_high_ownership(self) -> None:
        # 40% * 4500 = 180000
        assert compute_target(Decimal("40.0")) == 180_000

    def test_very_low_ownership_hits_floor(self) -> None:
        # 0.5% * 4500 = 2250 < floor
        assert compute_target(Decimal("0.5")) == 20_000


class TestComputeProgress:
    def test_exact_target(self) -> None:
        assert compute_progress(45_000, 45_000) == 100.0

    def test_half_target(self) -> None:
        assert compute_progress(22_500, 45_000) == 50.0

    def test_over_target_capped(self) -> None:
        assert compute_progress(90_000, 45_000) == 100.0

    def test_zero_net(self) -> None:
        assert compute_progress(0, 45_000) == 0.0

    def test_negative_net_uses_abs(self) -> None:
        assert compute_progress(-22_500, 45_000) == 50.0

    def test_zero_target_returns_zero(self) -> None:
        assert compute_progress(10_000, 0) == 0.0


class TestComputeVelocity:
    def test_two_snapshots(self) -> None:
        # 20k net increase over 4 hours = 5k/hr
        assert compute_velocity([(10_000, 6.0), (30_000, 10.0)]) == 5_000

    def test_empty_snapshots(self) -> None:
        assert compute_velocity([]) == 0

    def test_single_snapshot(self) -> None:
        assert compute_velocity([(10_000, 6.0)]) == 0

    def test_negative_velocity(self) -> None:
        # Net decreased: -10k over 2 hours = -5k/hr
        assert compute_velocity([(30_000, 8.0), (20_000, 10.0)]) == -5_000

    def test_same_time_returns_zero(self) -> None:
        assert compute_velocity([(10_000, 6.0), (20_000, 6.0)]) == 0
