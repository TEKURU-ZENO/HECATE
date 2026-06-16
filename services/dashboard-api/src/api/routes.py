from fastapi import APIRouter

router = APIRouter()


@router.get("/incidents")
async def list_incidents():
    return [
        {
            "id": "inc-1",
            "incident_code": "HEC-001",
            "title": "Memory Leak",
            "severity": "critical",
            "status": "open",
            "service_name": "payment-service",
            "detected_at": "2026-06-02T12:00:00Z",
        }
    ]


@router.get("/incidents/{id}")
async def get_incident(id: str):
    return {
        "id": id,
        "incident_code": "HEC-001",
        "title": "Memory Leak",
        "severity": "critical",
        "status": "open",
    }


@router.get("/agents")
async def list_agents():
    return [{"id": "ag-1", "agentName": "monitoring-agent", "status": "active", "healthScore": 98}]


@router.get("/agents/status")
async def get_agents_status_summary():
    return {"active_agents": 7, "healthy": True}


@router.get("/metrics/summary")
async def get_metrics_summary():
    return [
        {
            "serviceName": "payment-service",
            "availability": 99.9,
            "errorRate": 0.02,
            "responseTime": 120,
            "status": "healthy",
        }
    ]
