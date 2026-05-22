import json
from google.genai import types
from config import ORCHESTRATOR_MODEL, AGENT_MODEL, MAX_ITERATIONS
from agents.base import convert_tools, _gemini_call
from .inventory import InventoryAgent
from .sales import SalesAgent
from .demand import DemandForecastAgent
from .suppliers import SupplierAgent
from .purchasing import PurchasingAgent
from .reports import ReportAgent

SYSTEM_PROMPT = """Eres el Orquestador Central del sistema multiagente de gestión de inventario retail.
Coordinas un equipo de 6 agentes especializados para responder cualquier consulta sobre el negocio.

AGENTES DISPONIBLES:
1. invoke_inventory_agent    - Stock actual, alertas, valor del inventario, productos sin stock
2. invoke_sales_agent        - Análisis de ventas, ingresos, productos top, tendencias de ventas
3. invoke_demand_agent       - Pronósticos de demanda, días de stock restantes, riesgo de desabasto
4. invoke_supplier_agent     - Información de proveedores, evaluación comparativa, mejores proveedores
5. invoke_purchasing_agent   - Órdenes de compra, reabastecimiento, seguimiento de pedidos
6. invoke_report_agent       - Reportes ejecutivos completos, KPIs gerenciales, análisis integral

PROTOCOLO DE DECISIÓN:
- Para consultas simples de stock o alertas → usa inventory_agent
- Para análisis de ventas o ingresos → usa sales_agent
- Para proyecciones futuras o riesgos → usa demand_agent
- Para evaluación de proveedores → usa supplier_agent
- Para crear órdenes o gestionar compras → usa purchasing_agent
- Para reportes completos o análisis ejecutivos → usa report_agent
- Para consultas complejas → combina múltiples agentes secuencialmente

IMPORTANTE:
- Siempre interpreta la intención real del usuario, no solo las palabras literales
- Cuando combines resultados de múltiples agentes, sintetiza una respuesta unificada y coherente
- Responde siempre en español de manera profesional y orientada a la acción
- Si una consulta requiere múltiples agentes, invócalos en orden lógico y combina los resultados"""

_ORCHESTRATOR_TOOL_DEFS = [
    {
        "name": "invoke_inventory_agent",
        "description": "Invoca al Agente de Inventario para consultas sobre stock actual, alertas de inventario, valor del inventario y disponibilidad de productos.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Consulta para el agente de inventario"}},
            "required": ["query"],
        },
    },
    {
        "name": "invoke_sales_agent",
        "description": "Invoca al Agente de Ventas para análisis de ventas, ingresos, productos más vendidos y tendencias comerciales.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Consulta para el agente de ventas"}},
            "required": ["query"],
        },
    },
    {
        "name": "invoke_demand_agent",
        "description": "Invoca al Agente de Pronóstico de Demanda para proyecciones futuras, días de stock restante y riesgos de desabastecimiento.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Consulta para el agente de demanda"}},
            "required": ["query"],
        },
    },
    {
        "name": "invoke_supplier_agent",
        "description": "Invoca al Agente de Proveedores para información de proveedores, evaluación comparativa y recomendaciones de abastecimiento.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Consulta para el agente de proveedores"}},
            "required": ["query"],
        },
    },
    {
        "name": "invoke_purchasing_agent",
        "description": "Invoca al Agente de Compras para crear órdenes de compra, gestionar reabastecimiento y hacer seguimiento de pedidos.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Consulta para el agente de compras"}},
            "required": ["query"],
        },
    },
    {
        "name": "invoke_report_agent",
        "description": "Invoca al Agente de Reportes para generar informes ejecutivos completos, dashboards y análisis de KPIs del negocio.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Consulta para el agente de reportes"}},
            "required": ["query"],
        },
    },
]


class OrchestratorAgent:
    def __init__(self, client, db_path: str, memory=None):
        self.client = client
        self.db_path = db_path
        self.model = ORCHESTRATOR_MODEL
        self.memory = memory
        self._gemini_tools = convert_tools(_ORCHESTRATOR_TOOL_DEFS)
        self._agents = {
            "invoke_inventory_agent": InventoryAgent(client, db_path, AGENT_MODEL),
            "invoke_sales_agent": SalesAgent(client, db_path, AGENT_MODEL),
            "invoke_demand_agent": DemandForecastAgent(client, db_path, AGENT_MODEL),
            "invoke_supplier_agent": SupplierAgent(client, db_path, AGENT_MODEL),
            "invoke_purchasing_agent": PurchasingAgent(client, db_path, AGENT_MODEL),
            "invoke_report_agent": ReportAgent(client, db_path, AGENT_MODEL),
        }

    def execute(self, user_query: str) -> str:
        # Enriquecer el system prompt con contexto de conversaciones pasadas
        system = SYSTEM_PROMPT
        if self.memory:
            past_context = self.memory.get_relevant_context(user_query)
            if past_context:
                system += (
                    "\n\nCONTEXTO DE CONVERSACIONES PREVIAS RELEVANTES "
                    "(usa esto para dar continuidad):\n" + past_context
                )

        contents = [types.Content(role="user", parts=[types.Part(text=user_query)])]
        final_response = ""
        agents_used = []

        for _ in range(MAX_ITERATIONS):
            response = _gemini_call(
                self.client.models.generate_content,
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    tools=self._gemini_tools,
                ),
            )

            candidate = response.candidates[0]
            parts = candidate.content.parts

            func_calls = [
                p.function_call for p in parts
                if hasattr(p, "function_call") and p.function_call and p.function_call.name
            ]

            if not func_calls:
                for p in parts:
                    if hasattr(p, "text") and p.text:
                        final_response = p.text
                break

            contents.append(candidate.content)

            response_parts = []
            for fc in func_calls:
                agents_used.append(fc.name)
                result = self._dispatch_agent(fc.name, dict(fc.args).get("query", ""))
                response_parts.append(types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name,
                        response={"result": result},
                    )
                ))

            contents.append(types.Content(role="user", parts=response_parts))

        if self.memory and final_response:
            self.memory.save_interaction(user_query, final_response, agents_used)

        return final_response or "Error: Se alcanzó el límite máximo de iteraciones del orquestador."

    def _dispatch_agent(self, tool_name: str, query: str) -> str:
        agent = self._agents.get(tool_name)
        if not agent:
            return json.dumps({"error": f"Agente desconocido: {tool_name}"})
        try:
            return agent.run(query)
        except Exception as e:
            return json.dumps({"error": f"Error en agente {tool_name}: {str(e)}"})
