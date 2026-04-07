"""Predicted lineup service — auto-generate starting XIs for all PL teams."""

import re
from decimal import Decimal
from typing import Any

from app.schemas.lineup import LineupPlayer, PredictedLineup

# Keywords in news that indicate a player won't play
_UNAVAILABLE_PATTERNS = re.compile(
    r"injur|suspend|illness|ban|not available|ruled out",
    re.IGNORECASE,
)

# Valid formations to try (DEF-MID-FWD, GK is always 1)
_FORMATIONS = [
    (4, 4, 2),
    (4, 3, 3),
    (3, 5, 2),
    (3, 4, 3),
    (4, 5, 1),
    (5, 4, 1),
    (5, 3, 2),
]


def _score_player(
    status: str,
    chance: int | None,
    minutes_pct: float,
    form: float,
    news: str | None = None,
) -> float:
    """Score a player's likelihood of starting. Higher = more likely."""
    # Automatic zero for unavailable statuses
    if status in ("u", "i", "s"):
        return 0.0

    # Check news for injury/suspension keywords
    if news and _UNAVAILABLE_PATTERNS.search(news):
        return 0.0

    # Normalize chance_of_playing (0-100 → 0-1)
    cop_norm = (
        (1.0 if status == "a" else 0.0) if chance is None else chance / 100.0
    )

    # Normalize minutes_pct (0-100 → 0-1)
    mins_norm = min(minutes_pct / 100.0, 1.0)

    # Normalize form (roughly 0-15 range → 0-1)
    form_norm = min(form / 15.0, 1.0)

    return 0.4 * cop_norm + 0.4 * mins_norm + 0.2 * form_norm


def _confidence(minutes_pct: Decimal) -> str:
    """Return confidence level based on minutes percentage."""
    pct = float(minutes_pct)
    if pct > 80:
        return "likely"
    if pct >= 50:
        return "rotation"
    return "doubt"


def predict_lineup(
    team_id: int,
    team_short_name: str,
    team_badge_url: str | None,
    players: list[dict[str, Any]],
) -> PredictedLineup:
    """Predict the starting XI for a single team."""
    if not players:
        return PredictedLineup(
            team_id=team_id,
            team_short_name=team_short_name,
            team_badge_url=team_badge_url,
            formation="0-0-0",
            starters=[],
            bench=[],
        )

    # Score all players
    scored: list[tuple[dict, float]] = []
    for p in players:
        s = _score_player(
            status=p.get("status", "a"),
            chance=p.get("chance_of_playing"),
            minutes_pct=float(p.get("minutes_pct") or 0),
            form=float(p.get("form") or 0),
            news=p.get("news"),
        )
        scored.append((p, s))

    # Group by position (skip players with missing position)
    by_pos: dict[int, list[tuple[dict, float]]] = {}
    for p, s in scored:
        pos = p.get("position")
        if pos is None:
            continue
        by_pos.setdefault(pos, []).append((p, s))

    # Sort each position group by score descending
    for pos in by_pos:
        by_pos[pos].sort(key=lambda x: x[1], reverse=True)

    # Find best formation — maximize total score of selected XI
    best_formation = (4, 4, 2)
    best_score = -1.0
    best_xi: list[tuple[dict, float]] = []

    for d, m, f in _FORMATIONS:
        gks = by_pos.get(1, [])[:1]
        defs = by_pos.get(2, [])[:d]
        mids = by_pos.get(3, [])[:m]
        fwds = by_pos.get(4, [])[:f]

        # Check we have enough players
        if (
            len(gks) < 1
            or len(defs) < d
            or len(mids) < m
            or len(fwds) < f
        ):
            continue

        xi = gks + defs + mids + fwds
        total = sum(s for _, s in xi)
        if total > best_score:
            best_score = total
            best_formation = (d, m, f)
            best_xi = xi

    # If no valid formation found, take best 11 by score
    if not best_xi:
        all_sorted = sorted(scored, key=lambda x: x[1], reverse=True)
        best_xi = all_sorted[:11]
        best_formation = (4, 4, 2)  # default label

    xi_ids = {p["player_id"] for p, _ in best_xi}

    # Build LineupPlayer objects
    def _to_lineup_player(p: dict, s: float) -> LineupPlayer:
        mins = p.get("minutes_pct") or Decimal("0")
        return LineupPlayer(
            player_id=p["player_id"],
            web_name=p["web_name"],
            shirt_url=p.get("shirt_url"),
            position=p["position"],
            confidence=_confidence(Decimal(str(mins))),
            chance_of_playing=p.get("chance_of_playing"),
            minutes_pct=Decimal(str(mins)),
            form_points=p.get("form_points"),
            news=p.get("news"),
            score=Decimal(str(round(s, 3))),
        )

    starters = [_to_lineup_player(p, s) for p, s in best_xi]
    # Sort starters by position for pitch display
    starters.sort(key=lambda lp: (lp.position, -float(lp.score)))

    bench_players = [
        (p, s) for p, s in scored if p["player_id"] not in xi_ids
    ]
    bench_players.sort(key=lambda x: x[1], reverse=True)
    bench = [_to_lineup_player(p, s) for p, s in bench_players[:7]]

    d, m, f = best_formation
    return PredictedLineup(
        team_id=team_id,
        team_short_name=team_short_name,
        team_badge_url=team_badge_url,
        formation=f"{d}-{m}-{f}",
        starters=starters,
        bench=bench,
    )
