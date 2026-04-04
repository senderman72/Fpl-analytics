"""Transfer suggestion engine — finds optimal sell/buy swaps for a squad."""

from decimal import Decimal
from typing import Any

from app.schemas.transfer import TransferSuggestion

HIT_PENALTY = Decimal("4")
MAX_SUGGESTIONS = 5
MAX_SELL_PER_POSITION = 1
MAX_SELL_TOTAL = 3


def suggest_transfers(
    squad: list[dict[str, Any]],
    bank: int,
    candidates: list[dict[str, Any]],
    free_transfers: int = 1,
) -> list[TransferSuggestion]:
    """Find optimal transfer suggestions for a squad.

    Args:
        squad: List of squad player dicts with player_id, web_name, position,
               now_cost, predicted_points, shirt_url, team_short_name, fixtures.
        bank: Available budget in tenths (e.g., 15 = £1.5m).
        candidates: List of replacement candidate dicts (same shape as squad).
        free_transfers: Number of free transfers available (default 1).

    Returns:
        Sorted list of TransferSuggestion, best first, capped at 5.
    """
    if not squad:
        return []

    squad_ids = {p["player_id"] for p in squad}

    # Group squad by position, find underperformers
    by_position: dict[int, list[dict]] = {}
    for p in squad:
        by_position.setdefault(p["position"], []).append(p)

    sell_candidates: list[dict] = []
    for _pos, players in by_position.items():
        sorted_by_pts = sorted(
            players, key=lambda p: float(p["predicted_points"] or 0)
        )
        # Bottom 1 per position as sell candidate
        for p in sorted_by_pts[:MAX_SELL_PER_POSITION]:
            sell_candidates.append(p)

    # Sort all sell candidates by predicted points (worst first)
    sell_candidates.sort(key=lambda p: float(p["predicted_points"] or 0))
    sell_candidates = sell_candidates[:MAX_SELL_TOTAL]

    # Filter out squad players from candidates
    available = [c for c in candidates if c["player_id"] not in squad_ids]

    # Group candidates by position
    cand_by_pos: dict[int, list[dict]] = {}
    for c in available:
        cand_by_pos.setdefault(c["position"], []).append(c)

    # Sort each position group by predicted points descending
    for pos in cand_by_pos:
        cand_by_pos[pos].sort(
            key=lambda c: float(c["predicted_points"] or 0), reverse=True
        )

    # Generate all valid swaps
    swaps: list[tuple[dict, dict, Decimal]] = []
    for sell in sell_candidates:
        sell_pts = Decimal(str(sell["predicted_points"] or 0))
        sell_cost = sell["now_cost"]
        budget = sell_cost + bank

        pos_candidates = cand_by_pos.get(sell["position"], [])
        for buy in pos_candidates[:10]:  # top 10 per position
            buy_pts = Decimal(str(buy["predicted_points"] or 0))
            buy_cost = buy["now_cost"]

            # Budget check
            if buy_cost > budget:
                continue

            pts_gain = buy_pts - sell_pts
            if pts_gain <= 0:
                continue

            swaps.append((sell, buy, pts_gain))

    if not swaps:
        return []

    # Score and rank — apply hit penalty for transfers beyond free_transfers
    # Sort by points gain first to determine transfer order
    swaps.sort(key=lambda s: s[2], reverse=True)

    suggestions: list[TransferSuggestion] = []
    used_sell_ids: set[int] = set()
    used_buy_ids: set[int] = set()

    for sell, buy, pts_gain in swaps:
        if sell["player_id"] in used_sell_ids:
            continue
        if buy["player_id"] in used_buy_ids:
            continue

        transfer_num = len(suggestions) + 1
        hit = (
            HIT_PENALTY if transfer_num > free_transfers else Decimal("0")
        )
        score = pts_gain - hit

        if score <= 0 and transfer_num > free_transfers:
            continue

        suggestions.append(
            TransferSuggestion(
                sell_player_id=sell["player_id"],
                sell_web_name=sell["web_name"],
                sell_shirt_url=sell.get("shirt_url"),
                sell_team_short=sell["team_short_name"],
                sell_predicted_pts=Decimal(
                    str(sell["predicted_points"] or 0)
                ),
                sell_fixtures=sell.get("fixtures", []),
                buy_player_id=buy["player_id"],
                buy_web_name=buy["web_name"],
                buy_shirt_url=buy.get("shirt_url"),
                buy_team_short=buy["team_short_name"],
                buy_now_cost=buy["now_cost"],
                buy_predicted_pts=Decimal(
                    str(buy["predicted_points"] or 0)
                ),
                buy_fixtures=buy.get("fixtures", []),
                points_gain=round(pts_gain, 1),
                price_diff=buy["now_cost"] - sell["now_cost"],
                score=round(score, 1),
                reasoning=_build_reasoning(sell, buy, pts_gain),
            )
        )

        used_sell_ids.add(sell["player_id"])
        used_buy_ids.add(buy["player_id"])

        if len(suggestions) >= MAX_SUGGESTIONS:
            break

    return suggestions


def _build_reasoning(
    sell: dict[str, Any],
    buy: dict[str, Any],
    pts_gain: Decimal,
) -> str:
    """Generate a one-sentence English explanation for the transfer."""
    parts: list[str] = []

    parts.append(
        f"{buy['web_name']} is predicted {pts_gain:.1f} more points"
        f" than {sell['web_name']} over the next 5 GWs"
    )

    price_diff = buy["now_cost"] - sell["now_cost"]
    if price_diff < 0:
        parts.append(f"and saves £{abs(price_diff) / 10:.1f}m")
    elif price_diff > 0:
        parts.append(f"for an extra £{price_diff / 10:.1f}m")

    return ". ".join(parts) + "."
