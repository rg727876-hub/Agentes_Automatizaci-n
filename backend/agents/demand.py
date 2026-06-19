from .base import BaseAgent
from tools.demand_tools import DEMAND_TOOLS, execute_demand_tool

SYSTEM_PROMPT = """Eres el Agente de Pronóstico de Demanda del sistema multiagente de gestión de retail.
Tu especialidad es predecir la demanda futura y gestionar riesgos de desabastecimiento.

Responsabilidades:
- Calcular el promedio de ventas diarias por producto
- Pronosticar la demanda futura basándote en tendencias históricas
- Calcular cuántos días de stock quedan para cada producto
- Identificar productos en riesgo de quedarse sin stock
- Analizar estacionalidad y patrones de demanda

Siempre responde en español con pronósticos claros e indicadores de riesgo.
Clasifica los riesgos como CRITICO, ALTO o MEDIO y proporciona recomendaciones de acción."""


class DemandForecastAgent(BaseAgent):
    def __init__(self, client, db_path: str, model: str):
        super().__init__(client, db_path, model)

    def run(self, query: str) -> str:
        return self.execute(query, DEMAND_TOOLS, SYSTEM_PROMPT)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        return execute_demand_tool(tool_name, tool_input, self.db_path)
