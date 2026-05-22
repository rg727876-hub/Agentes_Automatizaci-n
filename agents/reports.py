from .base import BaseAgent
from tools.inventory_tools import INVENTORY_TOOLS, execute_inventory_tool
from tools.sales_tools import SALES_TOOLS, execute_sales_tool
from tools.demand_tools import DEMAND_TOOLS, execute_demand_tool
from tools.order_tools import ORDER_TOOLS, execute_order_tool

SYSTEM_PROMPT = """Eres el Agente de Reportes del sistema multiagente de gestión de retail.
Tu especialidad es generar informes ejecutivos completos y análisis de negocio integral.

Responsabilidades:
- Generar reportes ejecutivos de inventario, ventas y finanzas
- Crear análisis de situación actual del negocio
- Producir resúmenes gerenciales con KPIs clave
- Combinar datos de múltiples fuentes para análisis holísticos
- Identificar oportunidades y riesgos de negocio

Siempre responde en español con reportes bien estructurados usando tablas y secciones claras.
Incluye siempre: resumen ejecutivo, métricas clave, análisis detallado y recomendaciones accionables.
Formatea los montos en pesos chilenos (CLP) con separadores de miles."""

ALL_TOOLS = INVENTORY_TOOLS + SALES_TOOLS + \
            [t for t in DEMAND_TOOLS if t["name"] in ("identify_stockout_risk", "calculate_days_of_stock_remaining")] + \
            [t for t in ORDER_TOOLS if t["name"] in ("get_pending_orders", "get_purchase_orders")]


class ReportAgent(BaseAgent):
    def __init__(self, client, db_path: str, model: str):
        super().__init__(client, db_path, model)

    def run(self, query: str) -> str:
        return self.execute(query, ALL_TOOLS, SYSTEM_PROMPT)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        inventory_names = {t["name"] for t in INVENTORY_TOOLS}
        sales_names = {t["name"] for t in SALES_TOOLS}
        demand_names = {"identify_stockout_risk", "calculate_days_of_stock_remaining"}
        order_names = {"get_pending_orders", "get_purchase_orders"}

        if tool_name in inventory_names:
            return execute_inventory_tool(tool_name, tool_input, self.db_path)
        elif tool_name in sales_names:
            return execute_sales_tool(tool_name, tool_input, self.db_path)
        elif tool_name in demand_names:
            return execute_demand_tool(tool_name, tool_input, self.db_path)
        elif tool_name in order_names:
            return execute_order_tool(tool_name, tool_input, self.db_path)
        import json
        return json.dumps({"error": f"Herramienta desconocida: {tool_name}"})
