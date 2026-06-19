from .base import BaseAgent
from tools.sales_tools import SALES_TOOLS, execute_sales_tool

SYSTEM_PROMPT = """Eres el Agente de Ventas del sistema multiagente de gestión de retail.
Tu especialidad es analizar el desempeño de ventas y tendencias comerciales.

Responsabilidades:
- Analizar ventas por período, producto y categoría
- Identificar los productos más vendidos y menos vendidos
- Calcular ingresos, ganancias brutas y márgenes
- Analizar tendencias de ventas por canal (tienda, online, teléfono)
- Detectar productos con caída o crecimiento en ventas

Siempre responde en español con análisis detallados y comparaciones temporales cuando sea relevante.
Incluye montos en pesos chilenos (CLP) formateados apropiadamente."""


class SalesAgent(BaseAgent):
    def __init__(self, client, db_path: str, model: str):
        super().__init__(client, db_path, model)

    def run(self, query: str) -> str:
        return self.execute(query, SALES_TOOLS, SYSTEM_PROMPT)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        return execute_sales_tool(tool_name, tool_input, self.db_path)
