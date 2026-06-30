"""Estado central del grafo Deep Agent (LangGraph).

`DeepAgentState` es el `TypedDict` compartido que fluye por todos los nodos del
grafo. LangGraph NO reemplaza el estado completo en cada paso: cada nodo devuelve
un **parche parcial** (un dict con solo los campos que cambió) y LangGraph los
**fusiona** sobre el estado con la función *reducer* de cada campo.

Reducers usados aquí:

- Campos `Annotated[..., operator.add]` -> se **acumulan**:
    * `iteraciones`  : freno de seguridad. Cada vuelta del bucle suma el parche
                       `{"iteraciones": 1}`; nunca se asigna a mano.
    * `historial`    : traza de auto-corrección. Cada nodo añade líneas con el
                       parche `{"historial": ["..."]}` (append, no sobrescribe).

- Campos SIN anotación -> reducer por defecto (**sobrescribir**): en cada
  re-planificación, `plan`, `consulta_busqueda`, `contexto`, `respuesta` y
  `veredicto` se reemplazan con el intento más reciente.

El freno anti-bucle vive en el Estado (`iteraciones` vs `max_iteraciones`) y lo
consulta la arista condicional (`edges.py`) para forzar la salida hacia END aunque
el crítico siga pidiendo reintentar.
"""
from __future__ import annotations

import operator
from typing import Annotated, List, Optional

from typing_extensions import TypedDict

from .schemas import Plan, RespuestaGenerada, VeredictoCritico


class DeepAgentState(TypedDict):
    # --- Entrada ---
    pregunta: str  # consulta original del usuario (no se modifica)

    # --- Nodo: planificar ---
    plan: Optional[Plan]            # descomposición de la consulta
    consulta_busqueda: str          # consulta optimizada para el retriever

    # --- Nodo: recuperar (RAG sobre el Vector Store) ---
    # list[dict] con la forma de VectorMemory.search_products():
    # {"document": str, "metadata": {...}, "relevance": float}
    contexto: List[dict]

    # --- Nodo: generar ---
    respuesta: str                          # texto de la respuesta del intento actual
    generacion: Optional[RespuestaGenerada]  # salida estructurada completa del generador

    # --- Nodo: evaluar (sub-agente crítico) ---
    veredicto: Optional[VeredictoCritico]   # juicio de groundedness + decisión

    # --- Freno de seguridad / control del bucle ---
    iteraciones: Annotated[int, operator.add]  # acumulado por reducer (parche {"iteraciones": 1})
    max_iteraciones: int                       # tope; lo fija la entrada del grafo

    # --- Traza de auto-corrección (reducer de append) ---
    historial: Annotated[List[str], operator.add]


def estado_inicial(pregunta: str, max_iteraciones: int = 3) -> DeepAgentState:
    """Construye el Estado inicial para invocar el grafo.

    Inicializa los acumuladores (`iteraciones=0`, `historial=[]`) y los campos
    aún vacíos, de modo que los reducers tengan una base sobre la que fusionar.
    """
    return DeepAgentState(
        pregunta=pregunta,
        plan=None,
        consulta_busqueda="",
        contexto=[],
        respuesta="",
        generacion=None,
        veredicto=None,
        iteraciones=0,
        max_iteraciones=max_iteraciones,
        historial=[],
    )
