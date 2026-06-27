"""Orquestador central como supervisor de LangGraph.

Antes: un bucle manual de *function calling* que despachaba a los agentes a mano.
Ahora: un agente ReAct (`create_react_agent`) cuyas **herramientas son los 6
agentes especializados**. El orquestador razona y decide a quién delegar; cada
"herramienta de delegación" ejecuta el grafo del especialista correspondiente.

Qué aporta esta versión:
- **Prompt no estático**: se arma en cada turno con la fecha y el contexto de
  memoria de largo plazo (pgvector) relevante a la consulta.
- **Memoria de sesión**: un `MemorySaver` (checkpointer de LangGraph) mantiene el
  hilo de la conversación entre turnos.
- **Memoria de largo plazo**: se inyecta contexto de conversaciones previas y se
  guarda cada interacción (igual que antes, vía `VectorMemory`).
- **Reflejo**: mensajes triviales se responden sin LLM (control de costo).
- **Observabilidad**: al usar la capa `llm.get_llm`, todo queda trazado en
  LangSmith (tokens/costo/latencia) si hay API key.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

from config import ORCHESTRATOR_MODEL
from llm import get_llm
from .inventory import InventoryAgent
from .sales import SalesAgent
from .demand import DemandForecastAgent
from .suppliers import SupplierAgent
from .purchasing import PurchasingAgent
from .reports import ReportAgent
from .reflex import reflex_response

INSTRUCTIONS = """Eres el Orquestador Central del sistema multiagente de gestión de inventario retail.
Coordinas un equipo de 6 agentes especializados para responder cualquier consulta sobre el negocio.

IDIOMA OBLIGATORIO: Responde SIEMPRE en español. Jamás uses inglés aunque el usuario escriba en otro idioma.

AGENTES DISPONIBLES (cada uno es una herramienta de delegación):
1. invoke_inventory_agent    - Stock actual, alertas, valor del inventario, productos sin stock
2. invoke_sales_agent        - Análisis de ventas, ingresos, productos top, tendencias de ventas
3. invoke_demand_agent       - Pronósticos de demanda, días de stock restantes, riesgo de desabasto
4. invoke_supplier_agent     - Información de proveedores, evaluación comparativa, mejores proveedores
5. invoke_purchasing_agent   - Órdenes de compra, reabastecimiento, seguimiento de pedidos
6. invoke_report_agent       - Reportes ejecutivos completos, KPIs gerenciales, análisis integral
                               (también puede enviar el reporte por correo electrónico)

PROTOCOLO DE DECISIÓN:
- Para consultas simples de stock o alertas → usa invoke_inventory_agent
- Para análisis de ventas o ingresos → usa invoke_sales_agent
- Para proyecciones futuras o riesgos → usa invoke_demand_agent
- Para evaluación de proveedores → usa invoke_supplier_agent
- Para crear órdenes o gestionar compras → usa invoke_purchasing_agent
- Para reportes completos o análisis ejecutivos → usa invoke_report_agent
- Para consultas complejas → combina múltiples agentes secuencialmente

REGLAS DE COMPORTAMIENTO PROACTIVO (MUY IMPORTANTE):
- Cuando el usuario pida recomendaciones de productos, BUSCA PRIMERO en el inventario y presenta opciones concretas con nombre, precio y stock disponible. NO hagas preguntas cuando puedas obtener la información tú mismo.
- Si el usuario menciona una categoría informal ("artefactos", "gadgets", "tecnología", "aparatos") mapéala a la categoría del sistema más cercana: Electrónica, Ropa, Alimentos, Hogar o Deportes.
- Si el usuario menciona una moneda extranjera (soles, dólares, euros), indica que los precios están en pesos chilenos (CLP) y proporciona la información de igual forma.
- Ante consultas ambiguas, toma la interpretación más útil y actúa. Puedes mencionar tu interpretación al inicio de la respuesta, pero siempre responde con datos concretos.
- Usa el historial de la conversación para mantener el contexto: si el usuario ya indicó un presupuesto o categoría, recuérdalo sin volver a preguntarlo.
- Después de delegar, SINTETIZA la información de los agentes en una respuesta final clara para el usuario."""

# Definición de las herramientas de delegación: (nombre, clave de agente, descripción).
_HANDOFFS = [
    ("invoke_inventory_agent", "inventory",
     "Delega en el Agente de Inventario: stock actual, alertas, valor del inventario y disponibilidad de productos."),
    ("invoke_sales_agent", "sales",
     "Delega en el Agente de Ventas: análisis de ventas, ingresos, productos más vendidos y tendencias."),
    ("invoke_demand_agent", "demand",
     "Delega en el Agente de Demanda: pronósticos, días de stock restante y riesgo de desabastecimiento."),
    ("invoke_supplier_agent", "supplier",
     "Delega en el Agente de Proveedores: información, evaluación comparativa y recomendaciones de abastecimiento."),
    ("invoke_purchasing_agent", "purchasing",
     "Delega en el Agente de Compras: crear órdenes, reabastecimiento y seguimiento de pedidos."),
    ("invoke_report_agent", "report",
     "Delega en el Agente de Reportes: informes ejecutivos, KPIs y análisis integral (puede enviarlo por email)."),
]


class _DelegationArgs(BaseModel):
    query: str = Field(description="Consulta en lenguaje natural para el agente especializado.")


class OrchestratorAgent:
    def __init__(self, memory=None):
        self.memory = memory
        self._current_context = ""  # memoria de largo plazo relevante al turno actual
        self._specialists = {
            "inventory": InventoryAgent(),
            "sales": SalesAgent(),
            "demand": DemandForecastAgent(),
            "supplier": SupplierAgent(),
            "purchasing": PurchasingAgent(),
            "report": ReportAgent(),
        }
        self._checkpointer = MemorySaver()
        self._agent = create_react_agent(
            model=get_llm(ORCHESTRATOR_MODEL),
            tools=self._build_handoff_tools(),
            prompt=self._make_prompt,
            checkpointer=self._checkpointer,
        )
        # Hilo único: el chat se serializa con chat_lock (ver api/state.py).
        self._config = {"configurable": {"thread_id": "default"}}

    def _build_handoff_tools(self) -> list:
        tools = []
        for tool_name, key, desc in _HANDOFFS:
            def _make(agent_key):
                def _delegate(query: str) -> str:
                    return self._specialists[agent_key].run(query)
                return _delegate

            tools.append(StructuredTool.from_function(
                func=_make(key),
                name=tool_name,
                description=desc,
                args_schema=_DelegationArgs,
            ))
        return tools

    def _make_prompt(self, state):
        """Prompt dinámico: instrucciones + contexto de memoria del turno actual."""
        from datetime import date
        text = INSTRUCTIONS + f"\n\n[Contexto dinámico] Fecha actual: {date.today().isoformat()}."
        if self._current_context:
            text += (
                "\n\nCONTEXTO DE CONVERSACIONES PREVIAS RELEVANTES "
                "(úsalo para dar continuidad):\n" + self._current_context
            )
        return [SystemMessage(content=text)] + state["messages"]

    def execute(self, user_query: str) -> str:
        # 1) Reflejo: respuestas instantáneas sin gastar tokens.
        quick = reflex_response(user_query)
        if quick is not None:
            return quick

        # 2) Recupera memoria de largo plazo UNA vez por turno (no por paso del grafo).
        self._current_context = ""
        if self.memory:
            try:
                self._current_context = self.memory.get_relevant_context(user_query) or ""
            except Exception:  # noqa: BLE001
                self._current_context = ""

        # 3) Ejecuta el grafo supervisor.
        try:
            result = self._agent.invoke(
                {"messages": [HumanMessage(content=user_query)]},
                self._config,
            )
        except Exception as e:  # noqa: BLE001
            return f"Lo siento, ocurrió un error al procesar tu consulta: {e}"

        messages = result.get("messages", [])
        response = messages[-1].content if messages else ""

        # 4) Persiste la interacción en memoria de largo plazo (pgvector).
        if response and self.memory:
            agents_used = [
                m.name for m in messages
                if m.__class__.__name__ == "ToolMessage" and getattr(m, "name", None)
            ]
            try:
                self.memory.save_interaction(user_query, response, agents_used)
            except Exception:  # noqa: BLE001
                pass

        return response or "Error: no se obtuvo respuesta del orquestador."
