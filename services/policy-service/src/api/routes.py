from fastapi import APIRouter

router = APIRouter()

@router.get("/policies")
async def list_policies():
    return [{"id": "pol-1", "name": "CPU Saturation Playbook", "enabled": True}]

@router.post("/policies")
async def create_policy(policy: dict):
    return {"id": "pol-2", "status": "created"}

@router.put("/policies/{id}")
async def update_policy(id: str, policy: dict):
    return {"id": id, "status": "updated"}

@router.delete("/policies/{id}")
async def delete_policy(id: str):
    return {"id": id, "status": "deleted"}