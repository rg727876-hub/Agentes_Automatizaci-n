"""Agente de Ventas (LangGraph ReAct)."""
from .base import build_agent, run_agent
from .tool_adapter import make_tools
from tools.sales_tools import SALES_TOOLS, execute_sales_tool
from config import AGENT_MODEL

INSTRUCTIONS = """Eres el Agente de Ventas del sistema multiagente de gestión de retail.
Tu especialidad es analizar el desempeño de ventas y tendencias comerciales.

Responsabilidades:
- Analizar ventas por período, producto y categoría
- Identificar los productos más vendidos y menos vendidos
- Calcular ingresos, ganancias brutas y márgenes
- Analizar tendencias de ventas por canal (tienda, online, teléfono)
- Detectar productos con caída o crecimiento en ventas

Siempre responde en español con análisis detallados y comparaciones temporales cuando sea relevante.
Incluye montos en pesos chilenos (CLP) formateados apropiadamente."""


class SalesAgent:
    def __init__(self, model: str = AGENT_MODEL):
        tools = make_tools(SALES_TOOLS, execute_sales_tool)
        self._agent = build_agent(INSTRUCTIONS, tools, model)

    def run(self, query: str) -> str:
        return run_agent(self._agent, query)
