"""Capa LLM unificada sobre LangChain.

Único lugar donde se crea el modelo de chat. Centraliza tres cosas:

1. **Modelo** — Gemini expuesto como ChatModel de LangChain
   (`ChatGoogleGenerativeAI`), para que los agentes hablen el lenguaje de
   LangChain/LangGraph y no la API cruda de `google-genai`.
2. **Caché** — `set_llm_cache(InMemoryCache())`: si llega EXACTAMENTE la misma
   petición (mismo prompt + mismas tools), se responde desde memoria sin gastar
   tokens. Es el "responder por reflejo" a nivel LLM → control de costo.
3. **Observabilidad** — activa LangSmith de forma perezosa (no-op sin API key).

El resto del sistema pide su modelo con `get_llm()` y nunca instancia el cliente
a mano.
"""
from functools import lru_cache

from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache
from langchain_google_genai import ChatGoogleGenerativeAI

from config import GEMINI_API_KEY, AGENT_MODEL, LLM_TEMPERATURE, setup_langsmith

_cache_ready = False


def _ensure_cache() -> None:
    global _cache_ready
    if not _cache_ready:
        set_llm_cache(InMemoryCache())
        _cache_ready = True


@lru_cache(maxsize=None)
def get_llm(model: str = AGENT_MODEL, temperature: float = LLM_TEMPERATURE) -> ChatGoogleGenerativeAI:
    """Devuelve un ChatModel de Gemini listo para LangChain/LangGraph.

    Cacheado por (model, temperature): se reutiliza la misma instancia en todo
    el proceso. Activa LangSmith y la caché de respuestas la primera vez.
    """
    setup_langsmith()
    _ensure_cache()
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=GEMINI_API_KEY,
        temperature=temperature,
    )
