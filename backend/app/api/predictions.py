"""Points prediction endpoint."""

from fastapi import APIRouter, Query

from app.schemas.common import APIResponse
from app.schemas.decision import PredictionOut
from app.services.points_model import predict_gw

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("/gw/{gw_id}", response_model=APIResponse[list[PredictionOut]])
async def get_predictions(
    gw_id: int,
    position: int | None = Query(None, ge=1, le=4),
    limit: int = Query(50, ge=1, le=500),
) -> APIResponse[list[PredictionOut]]:
    """Get predicted points for all players for a given gameweek."""
    predictions = predict_gw(gw_id)

    if position:
        predictions = [p for p in predictions if p["position"] == position]

    return APIResponse(
        data=[PredictionOut(**p) for p in predictions[:limit]],
        meta={"gameweek": gw_id, "total": len(predictions)},
    )
