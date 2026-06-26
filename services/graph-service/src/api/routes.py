from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from ..graph_client import BaseGraphClient

router = APIRouter()

# Global graph client reference that main.py will configure
graph_client: Optional[BaseGraphClient] = None


def get_client() -> BaseGraphClient:
    global graph_client
    if graph_client is None:
        raise HTTPException(status_code=500, detail="Graph client not initialized")
    return graph_client


class TopologyItem(BaseModel):
    service: str
    depends_on: List[str] = []


class NodePayload(BaseModel):
    label: str
    id: str
    properties: dict = {}


class RelationshipPayload(BaseModel):
    from_label: str
    from_key: str
    to_label: str
    to_key: str
    rel_type: str
    properties: dict = {}


@router.post("/initialize")
async def initialize_topology(topology: List[TopologyItem], client: BaseGraphClient = Depends(get_client)):
    client.initialize_topology([item.model_dump() if hasattr(item, "model_dump") else item.dict() for item in topology])
    return {"status": "success", "message": "Topology seeded"}


@router.post("/node")
async def create_node(payload: NodePayload, client: BaseGraphClient = Depends(get_client)):
    client.create_or_update_node(payload.label, payload.id, payload.properties)
    return {"status": "success", "message": f"Node {payload.id} synced"}


@router.post("/relationship")
async def create_relationship(payload: RelationshipPayload, client: BaseGraphClient = Depends(get_client)):
    client.create_relationship(
        payload.from_label,
        payload.from_key,
        payload.to_label,
        payload.to_key,
        payload.rel_type,
        payload.properties
    )
    return {"status": "success", "message": "Relationship created"}


@router.get("/rca")
async def get_rca(service: str, client: BaseGraphClient = Depends(get_client)):
    return client.get_rca_root_cause(service)


@router.get("/recommendations")
async def get_recommendations(service: str, incident_type: str, client: BaseGraphClient = Depends(get_client)):
    return client.get_neighbor_recommendations(service, incident_type)


@router.get("/data")
async def get_data(client: BaseGraphClient = Depends(get_client)):
    return client.get_graph_data()


class QueryPayload(BaseModel):
    query: str
    parameters: Optional[dict] = {}


@router.post("/query")
async def run_query(payload: QueryPayload, client: BaseGraphClient = Depends(get_client)):
    results = client.run_raw_query(payload.query, payload.parameters)
    return {"status": "success", "data": results}


@router.post("/archive")
async def trigger_archive(days: int = 30, client: BaseGraphClient = Depends(get_client)):
    client.archive_old_nodes(days)
    return {"status": "success", "message": f"Purged historical elements older than {days} days"}


@router.post("/clear")
async def clear_graph(client: BaseGraphClient = Depends(get_client)):
    client.clear_all()
    return {"status": "success", "message": "Graph database cleared"}
