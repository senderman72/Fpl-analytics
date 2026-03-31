"""Price change prediction algorithm.

Based on the FPL price change mechanism:
- Prices change at ~01:30 UTC daily
- Target threshold scales with ownership percentage
- A player can only change once per day, up to 3 times per gameweek
"""

from decimal import Decimal

# Tunable constants
FLOOR_TARGET: int = 20_000  # Minimum net transfers needed regardless of ownership
BASE_PER_PCT: int = 4_500  # Net transfers needed per 1% ownership
MIN_NET_FOR_DISPLAY: int = 5_000  # Don't show players below this threshold


def compute_target(selected_by_percent: Decimal) -> int:
    """Compute the net transfer target for a price change."""
    scaled = int(float(selected_by_percent) * BASE_PER_PCT)
    return max(FLOOR_TARGET, scaled)


def compute_progress(net_transfers: int, target: int) -> float:
    """Compute progress percentage toward price change (0-100)."""
    if target <= 0:
        return 0.0
    return min(100.0, round(abs(net_transfers) / target * 100, 1))


def compute_velocity(
    snapshots: list[tuple[int, float]],
) -> int:
    """Compute net transfers per hour from snapshot pairs.

    Each snapshot is (net_transfers, hours_since_midnight).
    """
    if len(snapshots) < 2:
        return 0
    latest_net, latest_hours = snapshots[-1]
    earliest_net, earliest_hours = snapshots[0]
    hours_diff = latest_hours - earliest_hours
    if hours_diff <= 0:
        return 0
    return int((latest_net - earliest_net) / hours_diff)
