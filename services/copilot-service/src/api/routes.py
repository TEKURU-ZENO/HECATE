import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import Settings
from ..rag_engine import RagEngine
from ..vector_store import VectorStore

router = APIRouter()
log = structlog.get_logger()

# Shared instances managed by FastAPI dependency injection
settings_instance = Settings()
vector_store_instance = VectorStore(index_refresh_interval=settings_instance.index_refresh_interval)
rag_engine_instance = RagEngine(settings_instance, vector_store_instance)


class ChatRequest(BaseModel):
    message: str
    session_id: str = None


@router.post("/chat")
async def chat(req: ChatRequest):
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    log.info("copilot_service.chat_request_received", message=message, session_id=req.session_id)

    try:
        response, sources, mode = await rag_engine_instance.generate_response(message)
        log.info("copilot_service.chat_response_generated", mode=mode, sources_count=len(sources))
        return {"response": response, "sources": sources, "mode": mode}
    except Exception as e:
        log.error("copilot_service.chat_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to generate response: {e}")
