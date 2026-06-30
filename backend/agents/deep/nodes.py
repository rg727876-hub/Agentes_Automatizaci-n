"""Nodos del grafo Deep Agent (LangGraph).

Cada nodo es una función pura `(estado) -> parche`: recibe el `DeepAgentState`
y devuelve SOLO los campos que cambió (LangGraph fusiona el parche con los
reducers definidos en `state.py`). Los nodos no mutan el estado en sitio.

Patrón cognitivo:
- `planificar`, `generar`, `evaluar` usan un LLM con salida estructurada
  (`get_llm(...).with_structured_output(Esquema)`): el modelo devuelve un objeto
  Pydantic ya validado, no texto que haya que parsear.
- `recuperar` no usa LLM: consulta el Vector Store (RAG). Como las funciones de
  nodo solo reciben el estado, la instancia de memoria se INYECTA al construir el
  grafo con `functools.partial(recuperar, memory=...)`, manteniendo el nodo puro
  y testeable.

El contador `iteraciones` se incrementa en `planificar` (entrada de cada vuelta
del bucle) devolviendo el parche aditivo `{"iteraciones": 1}`.
"""
from langchain_core.messages import HumanMessage, SystemMessage

from config import AGENT_MODEL
from llm import get_llm

from .prompts import (
    CRITICO_PROMPT,
    GENERADOR_PROMPT,
    PLANIFICADOR_PROMPT,
    mensaje_evaluar,
    mensaje_generar,
    mensaje_planificar,
)
from .schemas import Plan, RespuestaGenerada, VeredictoCritico
from .state import DeepAgentState


def _motivo_reintento(state: DeepAgentState) -> str:
    """Construye el texto de motivo para re-planificar a partir del veredicto
    previo. Vacío en la primera vuelta (cuando aún no hay crítico)."""
    veredicto = state.get("veredicto")
    if not veredicto:
        return ""
    partes = []
    if veredicto.problemas:
        partes.append("Problemas detectados: " + "; ".join(veredicto.problemas))
    if veredicto.consulta_reformulada:
        partes.append(f"Búsqueda sugerida: {veredicto.consulta_reformulada}")
    return "\n".join(partes)


# ---------------------------------------------------------------------------
# Nodo: planificar
# ---------------------------------------------------------------------------
def planificar(state: DeepAgentState, model: str = AGENT_MODEL) -> dict:
    """Descompone la consulta y produce una `consulta_busqueda`.

    Incrementa el freno de seguridad (`iteraciones`) porque es la entrada de cada
    vuelta del bucle (incluida cada re-planificación tras un reintento).
    """
    llm = get_llm(model).with_structured_output(Plan)
    motivo = _motivo_reintento(state)
    messages = [
        SystemMessage(content=PLANIFICADOR_PROMPT),
        HumanMessage(content=mensaje_planificar(state["pregunta"], motivo)),
    ]
    plan: Plan = llm.invoke(messages)
    vuelta = state.get("iteraciones", 0) + 1
    traza = f"[planificar #{vuelta}] búsqueda='{plan.consulta_busqueda}'"
    if motivo:
        traza += " (reintento)"
    return {
        "plan": plan,
        "consulta_busqueda": plan.consulta_busqueda,
        "iteraciones": 1,          # parche aditivo (reducer operator.add)
        "historial": [traza],      # parche de append (reducer operator.add)
    }


# ---------------------------------------------------------------------------
# Nodo: recuperar (RAG sobre el Vector Store)
# ---------------------------------------------------------------------------
def recuperar(state: DeepAgentState, memory, n_results: int = 5) -> dict:
    """Recupera contexto del Vector Store con la `consulta_busqueda` del plan.

    `memory` es una instancia de `VectorMemory`; se inyecta con functools.partial
    al construir el grafo. `search_products` ya es tolerante a fallos (devuelve []).
    """
    consulta = state.get("consulta_busqueda") or state["pregunta"]
    contexto = memory.search_products(consulta, n_results=n_results)
    traza = f"[recuperar] {len(contexto)} fragmento(s) para '{consulta}'"
    return {"contexto": contexto, "historial": [traza]}


# ---------------------------------------------------------------------------
# Nodo: generar
# ---------------------------------------------------------------------------
def generar(state: DeepAgentState, model: str = AGENT_MODEL) -> dict:
    """Redacta la respuesta usando EXCLUSIVAMENTE el contexto recuperado."""
    llm = get_llm(model).with_structured_output(RespuestaGenerada)
    messages = [
        SystemMessage(content=GENERADOR_PROMPT),
        HumanMessage(content=mensaje_generar(state["pregunta"], state["contexto"])),
    ]
    generacion: RespuestaGenerada = llm.invoke(messages)
    traza = (
        f"[generar] suficiente={generacion.informacion_suficiente} "
        f"fuentes={len(generacion.fuentes_usadas)}"
    )
    return {
        "respuesta": generacion.respuesta,
        "generacion": generacion,
        "historial": [traza],
    }


# ---------------------------------------------------------------------------
# Nodo: evaluar (sub-agente crítico)
# ---------------------------------------------------------------------------
def evaluar(state: DeepAgentState, model: str = AGENT_MODEL) -> dict:
    """Audita el groundedness de la respuesta y decide finalizar o reintentar."""
    llm = get_llm(model).with_structured_output(VeredictoCritico)
    generacion = state.get("generacion")
    fuentes = generacion.fuentes_usadas if generacion else []
    messages = [
        SystemMessage(content=CRITICO_PROMPT),
        HumanMessage(content=mensaje_evaluar(
            state["pregunta"], state["contexto"], state["respuesta"], fuentes,
        )),
    ]
    veredicto: VeredictoCritico = llm.invoke(messages)
    traza = (
        f"[evaluar] accion={veredicto.accion} "
        f"fundamentada={veredicto.fundamentada} score={veredicto.puntuacion}"
    )
    return {"veredicto": veredicto, "historial": [traza]}
