from fastapi import APIRouter

router = APIRouter()

@router.get("/rca")
async def get_rca_history():
    return [{"incident_id": "inc-1", "root_cause_service": "payment-service"}]

@router.get("/rca/{incident_id}")
async def get_rca_detail(incident_id: str):
    return {"incident_id": incident_id, "root_cause_service": "payment-service", "confidence": 0.92}

@router.post("/rca/analyze")
async def analyze_incident(payload: dict):
    return {"status": "processing", "incident_id": payload.get("incident_id")}
