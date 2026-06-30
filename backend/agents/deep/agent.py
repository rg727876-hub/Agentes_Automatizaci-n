"""Fachada del Deep Agent: clase con la misma interfaz que los demás agentes.

Envuelve el grafo cíclico de `graph.py` en una clase `DeepRAGAgent` con el mismo
contrato `.run(query) -> str` que `InventoryAgent`, `SalesAgent`, etc. Así el
orquestador puede delegarle igual que a cualquier especialista (ver `_HANDOFFS`).

Necesita la `VectorMemory` (a diferencia de los otros agentes, que arman sus
tools de negocio): es un agente RAG y su fuente de verdad es el Vector Store.
El orquestador ya recibe la memoria en su `__init__`, así que puede instanciarlo
con `DeepRAGAgent(memory=self.memory)`.

Dos modos de uso:
- `.run(query)`   -> ejecución de extremo a extremo (sin pausa), para el flujo
  de chat normal. Devuelve solo el texto de la respuesta.
- HITL: instancia con `hitl=True` y usa `.graph` directamente para pausar antes
  de `generar`, revisar el contexto y reanudar con el mismo `thread_id`.
"""
import uuid

from config import AGENT_MODEL

from .graph import build_deep_agent, run_deep_agent


class DeepRAGAgent:
    """Agente RAG de razonamiento profundo (plan -> retrieve -> generate -> critique)."""

    def __init__(
        self,
        memory,
        model: str = AGENT_MODEL,
        max_iteraciones: int = 3,
        n_results: int = 5,
        hitl: bool = False,
    ):
        self.memory = memory
        self.max_iteraciones = max_iteraciones
        # En modo chat normal corre de extremo a extremo (sin interrupt). El HITL
        # es opt-in: pausa antes de 'generar' para revisar el contexto recuperado.
        interrupt_before = ("generar",) if hitl else ()
        self.graph = build_deep_agent(
            memory,
            model=model,
            n_results=n_results,
            interrupt_before=interrupt_before,
        )

    def run(self, query: str) -> str:
        """Ejecuta el grafo para una consulta y devuelve el texto de la respuesta.

        Usa un `thread_id` único por llamada: cada consulta es un episodio de
        razonamiento independiente (el bucle de auto-corrección es interno).
        """
        estado = run_deep_agent(
            self.graph,
            query,
            max_iteraciones=self.max_iteraciones,
            thread_id=f"deep-{uuid.uuid4().hex[:8]}",
        )
        return estado.get("respuesta") or (
            "No se pudo generar una respuesta sustentada en el inventario."
        )
