"""Estado compartido del servidor y ciclo de vida (lifespan).

Centraliza la inicialización pesada (base de datos, memoria vectorial y
orquestador) en un único lugar para que los routers la consuman vía
`get_orchestrator()` / `get_memory()`. Reemplaza el patrón anterior de variables
globales en `app.py` + `@app.on_event("startup")` por un `lifespan` moderno.
"""
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from google import genai

from config import GEMINI_API_KEY, DATABASE_URL, DB_PATH, ENABLE_ALERT_MONITOR
from database import setup_database, get_connection
from agents import OrchestratorAgent
from memory import VectorMemory

# Estado global del servidor (orquestador + memoria, compartidos por los routers).
_state = {"orchestrator": None, "memory": None, "client": None, "error": None}

# El orquestador guarda historial de sesión: serializamos el chat (1 a la vez).
chat_lock = threading.Lock()


def _load_products_for_index() -> list:
    conn = get_connection(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT p.id, p.sku, p.name, p.category, p.unit_price, i.quantity "
            "FROM products p JOIN inventory i ON p.id = i.product_id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def init_system() -> None:
    """Inicializa base de datos, memoria vectorial y orquestador una sola vez."""
    if not GEMINI_API_KEY:
        raise RuntimeError("Falta GEMINI_API_KEY en el .env")
    if not DATABASE_URL:
        raise RuntimeError("Falta DATABASE_URL en el .env")

    setup_database(DB_PATH)

    client = genai.Client(api_key=GEMINI_API_KEY)

    memory = VectorMemory(client)
    memory.index_products(_load_products_for_index())

    # El orquestador ya no necesita el cliente genai: crea su propio LLM vía la
    # capa LangChain (llm.get_llm). El cliente genai se mantiene solo para los
    # embeddings de la memoria vectorial.
    orchestrator = OrchestratorAgent(memory=memory)

    _state["client"] = client
    _state["memory"] = memory
    _state["orchestrator"] = orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    # El arranque no debe tumbar el servidor: si la BD o Gemini fallan, igual
    # servimos el frontend y reportamos el problema en /api/health.
    try:
        init_system()
        _state["error"] = None
        if ENABLE_ALERT_MONITOR:
            from tools.alert_monitor import start_background_monitor
            start_background_monitor(DB_PATH)
    except Exception as e:  # noqa: BLE001
        _state["error"] = str(e)
        print(f"[ARRANQUE] No se pudo inicializar el sistema: {e}")
    yield


# ----------------------------------------------------------------------------
# Accesores que usan los routers
# ----------------------------------------------------------------------------
def get_state() -> dict:
    return _state


def get_orchestrator():
    return _state["orchestrator"]


def get_memory():
    return _state["memory"]
