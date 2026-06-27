"""Agente de Reportes (LangGraph ReAct)."""
from .base import build_agent, run_agent
from .tool_adapter import make_tools
from tools.inventory_tools import INVENTORY_TOOLS, execute_inventory_tool
from tools.sales_tools import SALES_TOOLS, execute_sales_tool
from tools.demand_tools import DEMAND_TOOLS, execute_demand_tool
from tools.order_tools import ORDER_TOOLS, execute_order_tool
from tools.email_tools import EMAIL_TOOLS, execute_email_tool
from config import AGENT_MODEL

_DEMAND_SUBSET = [t for t in DEMAND_TOOLS if t["name"] in ("identify_stockout_risk", "calculate_days_of_stock_remaining")]
_ORDER_SUBSET = [t for t in ORDER_TOOLS if t["name"] in ("get_pending_orders", "get_purchase_orders")]

INSTRUCTIONS = """Eres el Agente de Reportes del sistema multiagente de gestión de retail.
Tu especialidad es generar informes ejecutivos completos y análisis de negocio integral.

IDIOMA OBLIGATORIO: Responde SIEMPRE en español. Jamás uses inglés.

Responsabilidades:
- Generar reportes ejecutivos de inventario, ventas y finanzas
- Crear análisis de situación actual del negocio
- Producir resúmenes gerenciales con KPIs clave
- Combinar datos de múltiples fuentes para análisis holísticos
- Identificar oportunidades y riesgos de negocio
- Enviar reportes por correo electrónico cuando el usuario lo solicite

ENVÍO POR EMAIL:
- Si el usuario pide enviar el reporte a un correo, primero genera el reporte completo,
  luego usa send_report_email con el contenido del reporte como body.
- Si el usuario no proporciona una dirección de correo, pregúntale antes de enviar.
- El subject debe ser descriptivo: ej. "Reporte Ejecutivo de Inventario - [fecha actual]".

Siempre responde en español con reportes bien estructurados usando secciones claras.
Incluye siempre: resumen ejecutivo, métricas clave, análisis detallado y recomendaciones accionables.
Formatea los montos en pesos chilenos (CLP) con separadores de miles."""


class ReportAgent:
    def __init__(self, model: str = AGENT_MODEL):
        tools = (
            make_tools(INVENTORY_TOOLS, execute_inventory_tool)
            + make_tools(SALES_TOOLS, execute_sales_tool)
            + make_tools(_DEMAND_SUBSET, execute_demand_tool)
            + make_tools(_ORDER_SUBSET, execute_order_tool)
            + make_tools(EMAIL_TOOLS, execute_email_tool, needs_db_path=False)
        )
        self._agent = build_agent(INSTRUCTIONS, tools, model)

    def run(self, query: str) -> str:
        return run_agent(self._agent, query)
