"""Prediction accuracy metrics — MAE, RMSE, Pearson r, captain hit rate."""

import logging
from collections import defaultdict
from decimal import Decimal
from math import sqrt

from sqlalchemy import select

from app.core.database import sync_session_factory
from app.models.prediction_log import PredictionLog
from app.schemas.accuracy import (
    AccuracyResponse,
    GWAccuracy,
    PositionAccuracy,
)

logger = logging.getLogger(__name__)

POSITION_NAMES = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}


def compute_accuracy(gw_id: int | None = None) -> AccuracyResponse:
    """Compute accuracy metrics from stored prediction logs."""
    with sync_session_factory() as session:
        stmt = select(PredictionLog).where(
            PredictionLog.actual_points.isnot(None)
        )
        if gw_id is not None:
            stmt = stmt.where(PredictionLog.gameweek_id == gw_id)

        logs = session.execute(stmt).scalars().all()

    if not logs:
        return AccuracyResponse(
            mae=Decimal("0"),
            rmse=Decimal("0"),
            pearson_r=None,
            captain_hit_rate=None,
            total_predictions=0,
            total_gameweeks=0,
            by_position=[],
            per_gameweek=[],
        )

    # Core metrics (actual_points guaranteed non-None by the WHERE filter)
    errors = [
        float(log.predicted_points) - float(log.actual_points or 0)
        for log in logs
    ]
    abs_errors = [abs(e) for e in errors]
    mae = sum(abs_errors) / len(abs_errors)
    rmse = sqrt(sum(e * e for e in errors) / len(errors))

    # Pearson r
    pearson_r = _pearson_r(
        [float(log.predicted_points) for log in logs],
        [float(log.actual_points or 0) for log in logs],
    )

    # Captain hit rate: for each GW, was the top-predicted player
    # also the highest actual scorer among the top-5 predicted?
    gw_groups: dict[int, list[PredictionLog]] = defaultdict(list)
    for log in logs:
        gw_groups[log.gameweek_id].append(log)

    captain_hits = 0
    captain_total = 0
    for _gw, gw_logs in gw_groups.items():
        sorted_by_pred = sorted(
            gw_logs, key=lambda x: float(x.predicted_points), reverse=True
        )
        top5 = sorted_by_pred[:5]
        if not top5:
            continue
        captain_total += 1
        best_captain = top5[0]
        best_actual = max(top5, key=lambda x: x.actual_points or 0)
        if best_captain.player_id == best_actual.player_id:
            captain_hits += 1

    captain_hit_rate = (
        Decimal(str(round(captain_hits / captain_total, 3)))
        if captain_total > 0
        else None
    )

    # By-position breakdown
    pos_errors: dict[int, list[float]] = defaultdict(list)
    for log in logs:
        pos_errors[log.position].append(
            abs(float(log.predicted_points) - float(log.actual_points or 0))
        )

    by_position = [
        PositionAccuracy(
            position=pos,
            position_name=POSITION_NAMES.get(pos, f"POS{pos}"),
            mae=Decimal(str(round(sum(errs) / len(errs), 2))),
            count=len(errs),
        )
        for pos, errs in sorted(pos_errors.items())
    ]

    # Per-GW MAE series
    per_gameweek = [
        GWAccuracy(
            gameweek_id=gw,
            mae=Decimal(
                str(
                    round(
                        sum(
                            abs(
                                float(row.predicted_points)
                                - float(row.actual_points or 0)
                            )
                            for row in gw_logs
                        )
                        / len(gw_logs),
                        2,
                    )
                )
            ),
            count=len(gw_logs),
        )
        for gw, gw_logs in sorted(gw_groups.items())
    ]

    return AccuracyResponse(
        mae=Decimal(str(round(mae, 2))),
        rmse=Decimal(str(round(rmse, 2))),
        pearson_r=(
            Decimal(str(round(pearson_r, 3))) if pearson_r is not None else None
        ),
        captain_hit_rate=captain_hit_rate,
        total_predictions=len(logs),
        total_gameweeks=len(gw_groups),
        by_position=by_position,
        per_gameweek=per_gameweek,
    )


def _pearson_r(x: list[float], y: list[float]) -> float | None:
    """Compute Pearson correlation coefficient. Returns None on failure."""
    n = len(x)
    if n < 2:
        return None
    try:
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        cov = sum(
            (xi - mean_x) * (yi - mean_y)
            for xi, yi in zip(x, y, strict=True)
        )
        std_x = sqrt(sum((xi - mean_x) ** 2 for xi in x))
        std_y = sqrt(sum((yi - mean_y) ** 2 for yi in y))
        if std_x == 0 or std_y == 0:
            return None
        return cov / (std_x * std_y)
    except (ValueError, ZeroDivisionError):
        return None
