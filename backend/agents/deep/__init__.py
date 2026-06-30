"""Deep Agent: grafo RAG cíclico con auto-corrección (LangGraph).

Subpaquete que implementa un agente de razonamiento profundo sobre el patrón
"Deep Agent": planificación explícita + recuperación (RAG sobre el Vector Store)
+ generación + verificación interna (sub-agente crítico de *groundedness*), con
un bucle de auto-corrección controlado por un freno de seguridad en el Estado.

Topología del grafo (se ensambla en `graph.py`):

    START -> planificar -> recuperar -> generar -> evaluar --(condicional)--> END
                  ^________________________________________________|
                          (reintentar: re-planificar y reformular)

Piezas del subpaquete:
- `schemas.py`  : esquemas Pydantic de salida estructurada (`.with_structured_output`).
- `state.py`    : Estado central (`TypedDict`) con reducers y freno anti-bucle.
- `prompts.py`  : prompts de sistema (planificador/generador/crítico) + builders.
- `nodes.py`    : nodos (planificar/recuperar/generar/evaluar) como funciones puras.
- `edges.py`    : arista condicional del bucle (con freno de seguridad).
- `graph.py`    : ensamblaje y compilación del StateGraph (checkpointer + HITL).
"""
from .agent import DeepRAGAgent
from .edges import decidir_continuar
from .graph import build_deep_agent, run_deep_agent
from .nodes import evaluar, generar, planificar, recuperar
from .prompts import (
    CRITICO_PROMPT,
    GENERADOR_PROMPT,
    PLANIFICADOR_PROMPT,
    mensaje_evaluar,
    mensaje_generar,
    mensaje_planificar,
)
from .schemas import Plan, RespuestaGenerada, VeredictoCritico
from .state import DeepAgentState, estado_inicial

__all__ = [
    # schemas
    "Plan",
    "RespuestaGenerada",
    "VeredictoCritico",
    # state
    "DeepAgentState",
    "estado_inicial",
    # prompts
    "PLANIFICADOR_PROMPT",
    "GENERADOR_PROMPT",
    "CRITICO_PROMPT",
    "mensaje_planificar",
    "mensaje_generar",
    "mensaje_evaluar",
    # nodos / aristas
    "planificar",
    "recuperar",
    "generar",
    "evaluar",
    "decidir_continuar",
    # grafo
    "build_deep_agent",
    "run_deep_agent",
    # fachada
    "DeepRAGAgent",
]
