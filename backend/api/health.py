"""Router de salud: estado del sistema (usado por el health check de App Runner)."""
from fastapi import APIRouter

from config import DATABASE_URL, GEMINI_API_KEY
from api.state import get_state

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    state = get_state()
    return {
        "status": "ok" if state["orchestrator"] is not None else "error",
        "database": bool(DATABASE_URL),
        "gemini": bool(GEMINI_API_KEY),
        "error": state["error"],
    }
