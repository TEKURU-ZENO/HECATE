import os
import yaml
import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from ..hecate_db import get_db_connection

router = APIRouter()
log = structlog.get_logger()


class EvaluatePayload(BaseModel):
    action: str
    service_name: str
    service_type: str = "service"
    cluster: str = "cluster-aws-primary"
    traffic: str = "normal"
    replicas: int = 1


@router.get("/policies")
async def get_policies():
    conn, use_pg = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM policies")
    rows = cursor.fetchall()
    res = [dict(row) for row in rows]
    conn.close()
    return res


@router.get("/policies/match")
async def match_policy(incident_title: str):
    conn, use_pg = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM policies WHERE enabled = 1")
    rows = cursor.fetchall()
    conn.close()

    # Simple matching logic based on incident details
    matched_action = "restart_pod"  # default action
    matched_policy_id = "pol-001"

    for row in rows:
        policy = dict(row)
        action_def = policy.get("action_definition")
        cond = policy.get("condition_expression").lower()

        # Match "OOMKilled" or similar memory keywords for restart
        if "oomkilled" in cond and "memory" in incident_title.lower():
            matched_action = action_def
            matched_policy_id = policy.get("id")
            break
        # Match "cpu" for scale
        elif "cpu" in cond and "cpu" in incident_title.lower():
            matched_action = action_def
            matched_policy_id = policy.get("id")
            break

    return {"action": matched_action, "policy_id": matched_policy_id}


@router.post("/policies/evaluate")
async def evaluate_policy(payload: EvaluatePayload):
    # Find policies/policy-rules.yaml relative to HECATE repository root
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    rules_path = os.path.join(ROOT_DIR, "policies", "policy-rules.yaml")
    
    if os.path.exists(rules_path):
        try:
            with open(rules_path, "r") as f:
                data = yaml.safe_load(f)
            policies = data.get("policies", [])
        except Exception as e:
            log.error("policy.yaml_load_failed", error=str(e))
            policies = []
    else:
        policies = []

    for pol in policies:
        # Match criteria check
        match_criteria = pol.get("match", {})
        matches_all = True
        for k, v in match_criteria.items():
            payload_val = getattr(payload, k, None)
            if payload_val is None or str(payload_val).lower() != str(v).lower():
                matches_all = False
                break
        
        if not matches_all:
            continue

        # Condition criteria check
        cond_criteria = pol.get("condition", {})
        condition_satisfied = True
        for k, v in cond_criteria.items():
            payload_val = getattr(payload, k, None)
            if payload_val is None:
                condition_satisfied = False
                break
            
            # Numeric evaluation like '>5'
            if str(v).startswith(">"):
                try:
                    limit = int(str(v)[1:])
                    if not (int(payload_val) > limit):
                        condition_satisfied = False
                        break
                except Exception:
                    condition_satisfied = False
                    break
            elif str(v).startswith("<"):
                try:
                    limit = int(str(v)[1:])
                    if not (int(payload_val) < limit):
                        condition_satisfied = False
                        break
                except Exception:
                    condition_satisfied = False
                    break
            else:
                # String matching (substring or exact)
                if str(v).lower() not in str(payload_val).lower():
                    condition_satisfied = False
                    break
                    
        if condition_satisfied:
            effect = pol.get("effect", "approve")
            log.info("policy.evaluated", policy_id=pol.get("id"), effect=effect, service=payload.service_name)
            return {"status": "evaluated", "effect": effect, "policy_id": pol.get("id")}

    return {"status": "evaluated", "effect": "approve", "policy_id": "none"}
