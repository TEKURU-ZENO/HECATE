import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..engines.trend_forecast import fit_and_predict

router = APIRouter()
log = structlog.get_logger()


class ForecastRequest(BaseModel):
    service: str
    metric: str
    values: list[float]


@router.post("/forecast")
async def get_forecast(request: ForecastRequest):
    log.info(
        "forecasting_service.request_received",
        service=request.service,
        metric=request.metric,
        count=len(request.values),
    )

    if not request.values:
        raise HTTPException(status_code=400, detail="Values list cannot be empty")

    # Determine threshold based on metric name
    metric_lower = request.metric.lower()
    if "cpu" in metric_lower:
        threshold = 90.0
    elif "memory" in metric_lower or "mem" in metric_lower:
        threshold = 85.0
    else:
        threshold = 80.0

    try:
        res = fit_and_predict(request.values, threshold=threshold)
        log.info(
            "forecasting_service.prediction_completed",
            service=request.service,
            metric=request.metric,
            predicted=res["predicted_value"],
            confidence=res["confidence"],
            lead_time=res["lead_time_seconds"],
        )
        return res
    except Exception as e:
        log.error("forecasting_service.failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Forecasting calculation failed: {str(e)}")
