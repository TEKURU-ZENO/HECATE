from fastapi import APIRouter
from ..hecate_db import get_db_connection
import structlog

router = APIRouter()
log = structlog.get_logger()

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