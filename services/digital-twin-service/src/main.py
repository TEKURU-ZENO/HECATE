import os
import json
import uuid
import time
import structlog
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import settings
from .hecate_db import get_db_connection

log = structlog.get_logger()
app = FastAPI(
    title=settings.title,
    description="HECATE Digital Twin Service — models clusters, simulates plans, and calibrates predictions.",
    version=settings.version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()

# Default virtual infrastructure twin state
DEFAULT_STATE = {
    "clusters": {
        "cluster-aws-primary": {
            "cloud": "aws",
            "region": "us-east-1",
            "status": "healthy",
            "services": {
                "gateway": {"cpu": 30.0, "mem": 45.0, "replicas": 3, "version": "v1.2.0"},
                "order-service": {"cpu": 40.0, "mem": 50.0, "replicas": 2, "version": "v1.2.0"},
                "payment-service": {"cpu": 93.0, "mem": 88.0, "replicas": 4, "version": "v1.2.1-buggy"},
                "payment-db": {"cpu": 45.0, "mem": 70.0, "replicas": 1, "version": "postgres-14"}
            }
        },
        "cluster-gcp-secondary": {
            "cloud": "gcp",
            "region": "us-central1",
            "status": "healthy",
            "services": {
                "payment-cache": {"cpu": 20.0, "mem": 30.0, "replicas": 2, "version": "redis-6"}
            }
        },
        "cluster-azure-recovery": {
            "cloud": "azure",
            "region": "eastus",
            "status": "healthy",
            "services": {}
        }
    },
    "traffic_peak": False,
    "last_updated": time.time()
}

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(CURRENT_DIR, "twin_state.json")
CALIBRATION_FILE = os.path.join(CURRENT_DIR, "calibration.json")

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_STATE

def save_state(state: dict):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log.error("twin.save_state_failed", error=str(e))

def load_calibration() -> dict:
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"accuracy": 0.95, "total_calibrations": 0}

def save_calibration(cal: dict):
    try:
        with open(CALIBRATION_FILE, "w") as f:
            json.dump(cal, f, indent=2)
    except Exception as e:
        log.error("twin.save_calibration_failed", error=str(e))


class StateUpdatePayload(BaseModel):
    service: str
    properties: dict
    cluster: str = "cluster-aws-primary"

class SimulatePayload(BaseModel):
    service: str
    incident_id: str
    incident_type: str
    metrics: dict = {}

class CalibratePayload(BaseModel):
    incident_id: str
    playbook_sequence: str
    actual_mttr: float

class DeliverySimulatePayload(BaseModel):
    service: str
    strategy: str
    version: str

@router.post("/twin/simulate/delivery")
async def simulate_delivery_strategy(payload: DeliverySimulatePayload):
    strategy = payload.strategy.lower()
    service = payload.service
    
    if strategy == "canary":
        blast_radius = 0.05
        success_probability = 0.95
        confidence = 0.90
    elif strategy == "blue-green" or strategy == "blue_green":
        blast_radius = 0.20
        success_probability = 0.85
        confidence = 0.80
    else: # rolling
        blast_radius = 0.12
        success_probability = 0.90
        confidence = 0.85
        
    safety_score = float(round(0.4 * success_probability + 0.3 * (1.0 - blast_radius) + 0.3 * confidence, 3))
    
    log.info("twin.delivery_simulation_completed", service=service, strategy=strategy, safety_score=safety_score)
    
    return {
        "service": service,
        "strategy": strategy,
        "version": payload.version,
        "blast_radius": blast_radius,
        "success_probability": success_probability,
        "confidence": confidence,
        "safety_score": safety_score,
        "status": "approved" if safety_score > 0.80 else "warning"
    }

@router.get("/twin/data")
async def get_twin_data():
    state = load_state()
    cal = load_calibration()
    return {"state": state, "calibration": cal}

@router.post("/twin/state")
async def update_twin_state(payload: StateUpdatePayload):
    state = load_state()
    cls = payload.cluster
    svc = payload.service
    if cls in state["clusters"]:
        if svc in state["clusters"][cls]["services"]:
            state["clusters"][cls]["services"][svc].update(payload.properties)
        else:
            state["clusters"][cls]["services"][svc] = payload.properties
        state["last_updated"] = time.time()
        save_state(state)
        log.info("twin.state_updated", service=svc, cluster=cls, props=payload.properties)
        return {"status": "success", "message": f"State updated for {svc} on {cls}"}
    return {"status": "error", "message": f"Cluster {cls} not found"}

@router.post("/twin/state/reset")
async def reset_twin_state():
    save_state(DEFAULT_STATE)
    log.info("twin.state_reset")
    return {"status": "success", "message": "Digital Twin state reset to default"}

@router.post("/twin/simulate")
async def simulate_plan_sequences(payload: SimulatePayload):
    state = load_state()
    cal = load_calibration()
    
    # Calculate Telemetry Completeness: check if we got expected metrics (cpu_usage, memory_usage)
    metrics_received = list(payload.metrics.keys())
    expected = ["cpu_usage", "memory_usage"]
    found = [m for m in expected if m in metrics_received]
    telemetry_completeness = float(len(found)) / float(len(expected)) if expected else 1.0
    if telemetry_completeness == 0.0:
        telemetry_completeness = 0.5  # base fallback completeness
        
    # Calculate Topology Freshness: base 1.0, drops slightly if state is old
    age = time.time() - state.get("last_updated", time.time())
    topology_freshness = max(0.7, min(1.0, 1.0 - (age / 86400.0))) # decay over a day
    
    calibration_accuracy = cal.get("accuracy", 0.95)
    
    # Final confidence score
    confidence = float(calibration_accuracy * telemetry_completeness * topology_freshness)
    
    # Find service current state in virtual clusters
    target_service = payload.service
    current_replicas = 2
    for cls_name, cls_val in state["clusters"].items():
        if target_service in cls_val.get("services", {}):
            current_replicas = cls_val["services"][target_service].get("replicas", 2)
            break
            
    # Helper configurations for playbooks simulation
    # Action specs: (success_rate, mttr, cost, blast_radius)
    playbook_specs = {
        "restart_pod": (0.75, 12.0, 0.0, 0.1),
        "scale_deployment": (0.90, 15.0, 10.0, 0.0),
        "migrate_service": (0.60, 25.0, 5.0, 0.4),
        "rollback_release": (0.85, 18.0, 0.0, 0.2)
    }
    
    candidates = [
        ["restart_pod"],
        ["scale_deployment"],
        ["migrate_service"],
        ["rollback_release"],
        ["scale_deployment", "restart_pod"],
        ["restart_pod", "scale_deployment"],
        ["migrate_service", "restart_pod"],
        ["rollback_release", "scale_deployment"]
    ]
    
    simulations = []
    
    for seq in candidates:
        # For a sequence of actions:
        # Success = P(A) + (1-P(A))*P(B)
        # MTTR = MTTR(A) + (1-P(A))*MTTR(B)
        # Cost = Cost(A) + Cost(B)
        # BlastRadius = max(BlastRadius(A), BlastRadius(B))
        
        p_success = 0.0
        projected_mttr = 0.0
        projected_cost = 0.0
        projected_blast = 0.0
        
        for i, act in enumerate(seq):
            spec = playbook_specs[act]
            act_p, act_mttr, act_cost, act_blast = spec
            
            # Adjust scaling success if replicas are already high
            if act == "scale_deployment" and current_replicas >= 5:
                act_p = 0.40  # capacity limits
                act_cost = 25.0
                
            if i == 0:
                p_success = act_p
                projected_mttr = act_mttr
                projected_cost = act_cost
                projected_blast = act_blast
            else:
                prev_fail = 1.0 - p_success
                p_success = p_success + prev_fail * act_p
                projected_mttr = projected_mttr + prev_fail * act_mttr
                projected_cost = projected_cost + act_cost
                projected_blast = max(projected_blast, act_blast)
                
        # Calculate Twin Score:
        # S = 0.35 * Success + 0.20 * (1 - Outage) + 0.15 * (1 - Cost) - (0.10 * BlastRadius) + 0.20 * Confidence
        # Normalize Outage (MTTR) relative to a max of 50s
        outage_factor = max(0.0, min(1.0, projected_mttr / 50.0))
        cost_factor = max(0.0, min(1.0, projected_cost / 30.0))
        
        score = (
            0.35 * p_success +
            0.20 * (1.0 - outage_factor) +
            0.15 * (1.0 - cost_factor) -
            0.10 * projected_blast +
            0.20 * confidence
        )
        
        simulations.append({
            "playbook_sequence": " -> ".join(seq),
            "predicted_mttr": float(round(projected_mttr, 2)),
            "predicted_cost": float(round(projected_cost, 2)),
            "predicted_blast_radius": float(round(projected_blast, 2)),
            "success_probability": float(round(p_success, 2)),
            "confidence": float(round(confidence, 2)),
            "score": float(round(score, 3))
        })
        
    # Sort simulations by highest score descending
    simulations.sort(key=lambda x: x["score"], reverse=True)
    
    # Save best simulation prediction to twin_memory table in database
    best_sim = simulations[0]
    try:
        conn, use_pg = get_db_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO twin_memory (
                id, incident_id, service_name, playbook_sequence,
                predicted_mttr, predicted_cost, predicted_blast_radius, prediction_error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        # Save a new record
        cursor.execute(query, (
            str(uuid.uuid4()),
            payload.incident_id,
            payload.service,
            best_sim["playbook_sequence"],
            best_sim["predicted_mttr"],
            best_sim["predicted_cost"],
            best_sim["predicted_blast_radius"],
            0.0 # set initial error to 0
        ))
        conn.commit()
        conn.close()
    except Exception as dbe:
        log.error("twin.failed_to_log_simulation_memory", error=str(dbe))
        
    log.info("twin.simulation_completed", service=payload.service, best_playbook=best_sim["playbook_sequence"], score=best_sim["score"])
    
    return {
        "incident_id": payload.incident_id,
        "service": payload.service,
        "telemetry_completeness": telemetry_completeness,
        "topology_freshness": topology_freshness,
        "calibration_accuracy": calibration_accuracy,
        "confidence": confidence,
        "simulations": simulations
    }

@router.post("/twin/calibrate")
async def calibrate_twin(payload: CalibratePayload):
    cal = load_calibration()
    
    # Look up the last logged simulation prediction for this incident
    conn, use_pg = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, predicted_mttr FROM twin_memory WHERE incident_id = ? ORDER BY created_at DESC LIMIT 1",
        (payload.incident_id,)
    )
    row = cursor.fetchone()
    
    predicted_mttr = 15.0
    record_id = None
    if row:
        record_id = row[0]
        predicted_mttr = row[1]
        
    # Calculate error
    prediction_error = abs(payload.actual_mttr - predicted_mttr)
    
    # Calibrate twin accuracy using Temporal Difference step
    # calibration_accuracy = max(0.1, min(1.0, calibration_accuracy - alpha * (prediction_error / max(1.0, actual_mttr))))
    alpha = settings.calibration_alpha
    current_acc = cal.get("accuracy", 0.95)
    normalized_err = prediction_error / max(1.0, payload.actual_mttr)
    new_acc = max(0.5, min(1.0, current_acc - alpha * (normalized_err - 0.05)))
    
    cal["accuracy"] = float(round(new_acc, 3))
    cal["total_calibrations"] = cal.get("total_calibrations", 0) + 1
    save_calibration(cal)
    
    # Update DB record with reality metrics and error
    if record_id:
        cursor.execute(
            "UPDATE twin_memory SET actual_mttr = ?, prediction_error = ? WHERE id = ?",
            (payload.actual_mttr, float(round(prediction_error, 2)), record_id)
        )
        conn.commit()
    conn.close()
    
    log.info("twin.calibrated", incident_id=payload.incident_id, error=prediction_error, new_accuracy=new_acc)
    return {
        "status": "success",
        "incident_id": payload.incident_id,
        "predicted_mttr": predicted_mttr,
        "actual_mttr": payload.actual_mttr,
        "prediction_error": prediction_error,
        "new_calibration_accuracy": cal["accuracy"]
    }

@router.get("/twin/history")
async def get_twin_history():
    conn, use_pg = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM twin_memory ORDER BY created_at DESC LIMIT 50")
    rows = cursor.fetchall()
    res = [dict(row) for row in rows]
    conn.close()
    return res

app.include_router(router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    cal = load_calibration()
    return {"status": "healthy", "service": "digital-twin-service", "version": settings.version, "mode": "mock", "accuracy": cal["accuracy"]}

@app.on_event("startup")
async def startup_event():
    log.info("digital_twin_service.started", version=settings.version)


# HECATE Production Edition Standardized Health & Readiness Probes
@app.get("/ready")
async def ready_check_probe():
    # Standard readiness probe
    return {"status": "ready", "service": "digital-twin-service"}

@app.get("/live")
async def live_check_probe():
    # Standard liveness probe
    return {"status": "live", "service": "digital-twin-service"}

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app)
except Exception:
    @app.get("/metrics")
    async def metrics_endpoint_probe():
        return 'hecate_service_up{service="digital-twin-service"} 1.0\n'
