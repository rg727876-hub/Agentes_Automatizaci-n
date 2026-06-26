"""Router de chat: conversación en lenguaje natural con el orquestador."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.state import get_orchestrator, chat_lock

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
def chat(req: ChatRequest):
    message = (req.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="El mensaje está vacío.")
    orchestrator = get_orchestrator()
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="El sistema aún se está inicializando.")
    with chat_lock:
        try:
            response = orchestrator.execute(message)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"Error del orquestador: {e}")
    return {"response": response}
