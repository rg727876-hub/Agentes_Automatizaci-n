"""Ensamblaje del grafo Deep Agent (LangGraph).

Cablea los nodos y la arista condicional en un `StateGraph` cíclico y lo compila
con un checkpointer (`InMemorySaver`) para habilitar persistencia local y
Human-in-the-loop (HITL).

Topología:

    START -> planificar -> recuperar -> generar -> evaluar
                  ^_______________________________________|
                          decidir_continuar:
                            - "reintentar" -> planificar
                            - "finalizar"  -> END

HITL: por defecto `interrupt_before=("generar",)`: el grafo se PAUSA tras
recuperar el contexto y antes de redactar, para que un humano revise/edite qué
contexto se usará antes de gastar tokens. Como hay checkpointer, el estado se
conserva y la ejecución se reanuda invocando de nuevo con el mismo `thread_id`
(opcionalmente tras editar el estado con `update_state`).
"""
from functools import partial
from typing import Sequence

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph

from config import AGENT_MODEL

from .edges import FINALIZAR, REINTENTAR, decidir_continuar
from .nodes import evaluar, generar, planificar, recuperar
from .schemas import Plan, RespuestaGenerada, VeredictoCritico
from .state import DeepAgentState, estado_inicial

# El Estado guarda objetos Pydantic (Plan/RespuestaGenerada/VeredictoCritico). El
# serializador del checkpointer los trata como tipos "no registrados" y, por
# defecto, los deserializa con un aviso de deprecación (será bloqueado en el
# futuro). Registramos explícitamente nuestros esquemas en el allowlist para
# conservar el tipado en el Estado sin warnings y de forma a prueba de futuro.
# (Verificado: no bloquea los tipos internos de LangGraph, ya cubiertos por
# SAFE_MSGPACK_TYPES.)
_ALLOWED_MSGPACK = [
    (cls.__module__, cls.__qualname__)
    for cls in (Plan, RespuestaGenerada, VeredictoCritico)
]


def _make_checkpointer() -> InMemorySaver:
    """InMemorySaver con un serde que reconoce nuestros esquemas Pydantic."""
    serde = JsonPlusSerializer(allowed_msgpack_modules=_ALLOWED_MSGPACK)
    return InMemorySaver(serde=serde)


def build_deep_agent(
    memory,
    model: str = AGENT_MODEL,
    n_results: int = 5,
    interrupt_before: Sequence[str] = ("generar",),
    checkpointer=None,
):
    """Construye y compila el grafo Deep Agent.

    Args:
        memory: instancia de `VectorMemory` (se inyecta en el nodo `recuperar`).
        model: modelo de chat para los nodos LLM (planificar/generar/evaluar).
        n_results: nº de fragmentos a recuperar del Vector Store por vuelta.
        interrupt_before: nodos ante los que pausar para HITL. Por defecto
            `("generar",)`. Pasa `()` para correr de extremo a extremo sin pausa.
        checkpointer: checkpointer de LangGraph. Por defecto, un `InMemorySaver`
            con el serde configurado para reconocer nuestros esquemas Pydantic
            (persistencia local en memoria de proceso, requisito para HITL). Si
            pasas tu propio checkpointer persistente (Postgres/Redis), recuerda
            configurar su serde con `allowed_msgpack_modules=_ALLOWED_MSGPACK`.

    Returns:
        El grafo compilado. Invócalo con un `config={"configurable":
        {"thread_id": ...}}` para que el checkpointer rastree la sesión.
    """
    builder = StateGraph(DeepAgentState)

    # Nodos. `recuperar` no es LLM: se le inyecta la memoria con partial para
    # mantenerlo puro (las funciones de nodo solo reciben el estado).
    builder.add_node("planificar", partial(planificar, model=model))
    builder.add_node("recuperar", partial(recuperar, memory=memory, n_results=n_results))
    builder.add_node("generar", partial(generar, model=model))
    builder.add_node("evaluar", partial(evaluar, model=model))

    # Flujo lineal del ciclo.
    builder.add_edge(START, "planificar")
    builder.add_edge("planificar", "recuperar")
    builder.add_edge("recuperar", "generar")
    builder.add_edge("generar", "evaluar")

    # Arista condicional: bucle de auto-corrección con freno de seguridad.
    builder.add_conditional_edges(
        "evaluar",
        decidir_continuar,
        {REINTENTAR: "planificar", FINALIZAR: END},
    )

    return builder.compile(
        checkpointer=checkpointer or _make_checkpointer(),
        interrupt_before=list(interrupt_before),
    )


def run_deep_agent(
    graph,
    pregunta: str,
    max_iteraciones: int = 3,
    thread_id: str = "default",
) -> DeepAgentState:
    """Ejecuta el grafo para una consulta y devuelve el estado final.

    Si el grafo se compiló con `interrupt_before`, esta llamada se detendrá en el
    punto de pausa: el estado devuelto será el del checkpoint y habrá nodos
    pendientes (`graph.get_state(config).next`). Para reanudar tras revisar,
    invoca `graph.invoke(None, config=...)` con el mismo `thread_id`.
    """
    config = {"configurable": {"thread_id": thread_id}}
    estado = estado_inicial(pregunta, max_iteraciones=max_iteraciones)
    return graph.invoke(estado, config=config)
