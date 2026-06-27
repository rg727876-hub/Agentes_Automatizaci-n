"""Agente de Pronóstico de Demanda (LangGraph ReAct)."""
from .base import build_agent, run_agent
from .tool_adapter import make_tools
from tools.demand_tools import DEMAND_TOOLS, execute_demand_tool
from config import AGENT_MODEL

INSTRUCTIONS = """Eres el Agente de Pronóstico de Demanda del sistema multiagente de gestión de retail.
Tu especialidad es predecir la demanda futura y gestionar riesgos de desabastecimiento.

Responsabilidades:
- Calcular el promedio de ventas diarias por producto
- Pronosticar la demanda futura basándote en tendencias históricas
- Calcular cuántos días de stock quedan para cada producto
- Identificar productos en riesgo de quedarse sin stock
- Analizar estacionalidad y patrones de demanda

Siempre responde en español con pronósticos claros e indicadores de riesgo.
Clasifica los riesgos como CRITICO, ALTO o MEDIO y proporciona recomendaciones de acción."""


class DemandForecastAgent:
    def __init__(self, model: str = AGENT_MODEL):
        tools = make_tools(DEMAND_TOOLS, execute_demand_tool)
        self._agent = build_agent(INSTRUCTIONS, tools, model)

    def run(self, query: str) -> str:
        return run_agent(self._agent, query)
