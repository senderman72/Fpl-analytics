"""Points prediction endpoint."""

import asyncio

from fastapi import APIRouter, Query

from app.core.cache import cached
from app.schemas.accuracy import AccuracyResponse
from app.schemas.common import APIResponse
from app.schemas.decision import PredictionOut
from app.services.accuracy import compute_accuracy
from app.services.points_model import (
    get_model_diagnostics,
    predict_gw,
    predict_upcoming,
)

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("/gw/{gw_id}", response_model=APIResponse[list[PredictionOut]])
@cached("predictions:gw", ttl_seconds=7200)
async def get_predictions(
    gw_id: int,
    position: int | None = Query(None, ge=1, le=4),
    limit: int = Query(50, ge=1, le=500),
) -> APIResponse[list[PredictionOut]]:
    """Get predicted points for all players for a given gameweek."""
    predictions = await asyncio.to_thread(predict_gw, gw_id)

    if position:
        predictions = [p for p in predictions if p["position"] == position]

    return APIResponse(
        data=[PredictionOut(**p) for p in predictions[:limit]],
        meta={"gameweek": gw_id, "total": len(predictions)},
    )


@router.get("/upcoming", response_model=APIResponse[list[PredictionOut]])
@cached("predictions:upcoming", ttl_seconds=7200)
async def get_upcoming_predictions(
    horizon: int = Query(5, ge=1, le=10),
    position: int | None = Query(None, ge=1, le=4),
    limit: int = Query(50, ge=1, le=500),
) -> APIResponse[list[PredictionOut]]:
    """Predict points across the next N upcoming gameweeks."""
    predictions = await asyncio.to_thread(predict_upcoming, horizon)

    if position:
        predictions = [p for p in predictions if p["position"] == position]

    actual_horizon = predictions[0]["horizon"] if predictions else horizon
    gw_ids = (
        [gw["gw_id"] for gw in predictions[0]["predicted_per_gw"]]
        if predictions
        else []
    )

    return APIResponse(
        data=[PredictionOut(**p) for p in predictions[:limit]],
        meta={
            "horizon": actual_horizon,
            "gameweek_ids": gw_ids,
            "total": len(predictions),
        },
    )


@router.get("/accuracy", response_model=APIResponse[AccuracyResponse])
@cached("predictions:accuracy", ttl_seconds=3600)
async def get_accuracy(
    gw_id: int | None = Query(None),
) -> APIResponse[AccuracyResponse]:
    """Get prediction accuracy metrics (MAE, RMSE, Pearson r, by position)."""
    result = await asyncio.to_thread(compute_accuracy, gw_id)
    return APIResponse(data=result)


@router.get("/model/diagnostics")
async def model_diagnostics() -> APIResponse[dict | None]:
    """Return model feature weights and hyperparameters for debugging."""
    diag = get_model_diagnostics()
    return APIResponse(data=diag)
