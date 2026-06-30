"""Aristas condicionales del grafo Deep Agent.

Aquí vive la lógica de enrutado del bucle de auto-corrección: tras `evaluar`, el
grafo decide si REINTENTA (vuelve a `planificar` para re-planificar y reformular
la búsqueda) o FINALIZA (sale a END).

Freno de seguridad: el límite `iteraciones >= max_iteraciones` tiene PRIORIDAD
sobre el crítico. Aunque el crítico pida 'reintentar', si ya se agotaron las
vueltas el grafo sale a END con la mejor respuesta disponible. Esto garantiza
que el bucle no sea infinito ni dependa de que el LLM "decida bien".
"""
from typing import Literal

from .state import DeepAgentState

# Etiquetas de ruta (deben coincidir con el mapa de add_conditional_edges).
REINTENTAR = "reintentar"
FINALIZAR = "finalizar"


def decidir_continuar(state: DeepAgentState) -> Literal["reintentar", "finalizar"]:
    """Arista condicional tras `evaluar`.

    Orden de decisión:
    1. FRENO: si se alcanzó `max_iteraciones`, finaliza (gana sobre el crítico).
    2. CRÍTICO: si el veredicto pide 'reintentar', reintenta.
    3. Por defecto, finaliza.
    """
    if state["iteraciones"] >= state["max_iteraciones"]:
        return FINALIZAR

    veredicto = state.get("veredicto")
    if veredicto is not None and veredicto.accion == "reintentar":
        return REINTENTAR

    return FINALIZAR
