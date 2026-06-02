from fastapi import APIRouter

router = APIRouter()

@router.get("/anomalies")
async def get_anomalies():
    return [{"id": "anom-1", "service": "payment-service", "severity": "high"}]

@router.get("/anomalies/{id}")
async def get_anomaly(id: str):
    return {"id": id, "service": "payment-service", "severity": "high"}

@router.post("/anomalies/detect")
async def force_detect_anomaly(payload: dict):
    return {"status": "triggered", "anomalies_detected": 0}